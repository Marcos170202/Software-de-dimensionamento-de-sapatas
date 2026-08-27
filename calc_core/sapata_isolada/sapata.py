"""
sapata.py
---------
Dimensionamento geotécnico e estrutural de SAPATA ISOLADA conforme
ABNT NBR 6118:2023 e ABNT NBR 6122:2019.

Roteiro implementado
--------------------
Passo 1 - Dimensionamento geotécnico (planta)      -> _dimensionar_planta
Passo 2 - Definição geométrica tridimensional      -> _definir_altura
Passo 3 - Verificações estruturais no ELU (punção) -> _verificar_puncao
Passo 4 - Dimensionamento à flexão (armaduras)     -> _dimensionar_flexao
Passo 5 - Detalhamento (ancoragem, bitolas, esp.)  -> _detalhar
Extra   - Análise de recalques por substrato       -> _analisar_recalques
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Sequence

from .acoes import (Combinacao, Esforcos, Pilar, TipoCombinacao, filtrar)
from .bielas import ResultadoBielas, bielas_sapata
from .geotecnia import Solo
from .materiais import (BITOLAS_COMERCIAIS, Aco, Concreto, area_barra,
                        comprimento_ancoragem_basico, massa_linear)
from .momentos import momento_unitario
from .recalques import AnaliseRecalque, ResultadoRecalque
from .grelha import ResultadoGrelha, resolver_grelha
from .rigidez import (Classificacao, ReacaoDiscretizada, classificar,
                      kv_por_tensao_admissivel, reacao_base_elastica)

KPA = 1000.0  # MPa -> kPa


# --------------------------------------------------------------------------- #
#  Imposições do projetista
# --------------------------------------------------------------------------- #
@dataclass
class GeometriaImposta:
    """
    Geometria fixada pelo projetista. Com ela a rotina deixa de dimensionar e
    passa a VERIFICAR: nenhuma dimensão é alterada, e cada verificação que não
    fecha vira um alerta explícito no resultado.
    """

    a: float
    b: float
    h: float
    h0: Optional[float] = None      # None -> adota max(h0_min ; h/3)


@dataclass
class ArmaduraImposta:
    """
    Arranjo de armadura fixado pelo projetista, por direção.

    Informe `n_barras` OU `espacamento`; se os dois vierem, vale `n_barras`.
    """

    phi_mm: float
    n_barras: Optional[int] = None
    espacamento: Optional[float] = None

    def quantidade(self, largura_util: float) -> int:
        if self.n_barras:
            return max(2, int(self.n_barras))
        if self.espacamento and self.espacamento > 0:
            return max(2, int(math.floor(largura_util / self.espacamento)) + 1)
        raise ValueError("Armadura imposta sem número de barras nem espaçamento.")


# --------------------------------------------------------------------------- #
#  Opções de projeto
# --------------------------------------------------------------------------- #
@dataclass
class OpcoesProjeto:
    modulo_dim: float = 0.05          # múltiplo para arredondar dimensões [m]
    dim_minima: float = 0.60          # menor dimensão em planta admitida [m]
    h_minima: float = 0.30            # altura total mínima [m]
    h0_minima: float = 0.20           # altura mínima da aba (borda) [m]
    # balanço livre mínimo POR LADO, nas dimensões não travadas pelo projetista
    # [m]. Critério de projeto, não granularidade de desenho: sem balanço não
    # há sapata (nem momento no balanço, nem domínio de validade de 22.6.1, que
    # pressupõe (a - a_p)/2 > 0). Vinha embutido como 2·modulo_dim, misturando
    # os dois conceitos; o padrão 0,05 m reproduz exatamente o valor anterior.
    balanco_minimo: float = 0.05
    peso_proprio_estimado: float = 0.05   # 5% de Nk na 1a iteração
    folga_topo: float = 0.05          # folga do bloco superior além do pilar [m]
    inclinacao_max_graus: float = 30.0
    espacamento_max: float = 0.20     # NBR 6118, 20.1 (armadura principal)
    espacamento_min: float = 0.10
    fator_armadura_minima: float = 1.0   # 1,0 = rho_min integral (conservador)
    travar_a: Optional[float] = None  # trava a dimensão em X [m]
    travar_b: Optional[float] = None  # trava a dimensão em Y [m]
    boa_aderencia: bool = True
    ganchos_nas_pontas: bool = True
    area_comprimida_minima: float = 2.0 / 3.0
    considerar_excentricidade_puncao: bool = True
    bitolas: Sequence[float] = BITOLAS_COMERCIAIS
    max_iteracoes: int = 80
    verificar_recalque: bool = True
    limite_recalque_mm: float = 25.0
    vida_util_anos: float = 50.0
    # --- imposições: quando presentes, a rotina verifica em vez de dimensionar
    geometria_imposta: Optional[GeometriaImposta] = None
    armaduras_impostas: dict = field(default_factory=dict)   # "X"/"Y" -> ArmaduraImposta
    # --- reação do solo: "rigido" (linear), "elastico" (Winkler discretizado)
    #     "grelha" (barras em X e Y ligadas, sobre molas) ou "envoltoria"
    modelo_reacao: str = "rigido"
    divisoes_grelha: int = 14
    # --- armadura de sapata RÍGIDA: "bielas" (Blévot), "flexao" ou "envoltoria".
    #     Sapata flexível usa sempre flexão: o modelo de bielas não se aplica.
    modelo_armadura_rigida: str = "bielas"
    coef_braco_bielas: float = 1.0
    theta_minimo_biela: float = 45.0
    kv: Optional[float] = None            # coef. de reação vertical [kN/m³]
    recalque_referencia_kv: float = 0.010  # usado se kv não for informado


# --------------------------------------------------------------------------- #
#  Estruturas de resultado
# --------------------------------------------------------------------------- #
@dataclass
class EstadoTensao:
    combinacao: str
    N_total: float
    Mx_base: float
    My_base: float
    ex: float
    ey: float
    sigma_max: float
    sigma_min: float
    sigma_media: float
    dentro_nucleo: bool
    area_comprimida: float
    metodo: str
    limite: float
    ok: bool


@dataclass
class VerificacaoEstabilidade:
    combinacao: str
    fs_deslizamento: float
    fs_tombamento_x: float
    fs_tombamento_y: float
    ok: bool


@dataclass
class VerificacaoPuncao:
    combinacao: str
    contorno: str
    tau_sd: float
    tau_rd: float
    aproveitamento: float
    ok: bool
    observacao: str = ""


@dataclass
class ArmaduraDirecao:
    direcao: str
    Md: float
    d: float
    As_calc: float          # [m2]
    As_min: float           # [m2]
    As_adot: float          # [m2]
    x_d: float
    phi_mm: float
    n_barras: int
    espacamento: float
    As_efetiva: float
    lb_necessario: float
    lb_disponivel: float
    ancoragem_ok: bool
    dominio_ok: bool
    # --- detalhamento da barra (para quadro de ferros e desenho)
    comprimento_reto: float = 0.0     # trecho horizontal [m]
    gancho: float = 0.0               # dobra a 90° em cada extremidade [m]
    comprimento_barra: float = 0.0    # comprimento de corte [m]
    peso_total: float = 0.0           # [kg]
    imposta: bool = False             # arranjo fixado pelo projetista
    modelo: str = "flexao"            # origem do A_s: "flexao" ou "bielas"
    As_flexao: float = 0.0            # comparação entre os dois modelos [m²]
    As_bielas: float = 0.0
    as_suficiente: bool = True        # A_s efetiva >= A_s necessária
    espacamento_ok: bool = True       # dentro dos limites da NBR 6118, 20.1


@dataclass
class ResultadoSapata:
    a: float
    b: float
    h: float
    h0: float
    d: float
    volume_concreto: float
    peso_proprio: float
    inclinacao_graus: float
    rigida: bool
    tensoes: list[EstadoTensao] = field(default_factory=list)
    estabilidade: list[VerificacaoEstabilidade] = field(default_factory=list)
    puncao: list[VerificacaoPuncao] = field(default_factory=list)
    armaduras: list[ArmaduraDirecao] = field(default_factory=list)
    ancoragem_arranque: dict = field(default_factory=dict)
    recalques: Optional[ResultadoRecalque] = None
    alertas: list[str] = field(default_factory=list)
    convergiu: bool = True
    modo_verificacao: bool = False    # geometria imposta pelo projetista
    reprovacoes: list[str] = field(default_factory=list)
    classificacao: Optional[Classificacao] = None
    reacoes: dict = field(default_factory=dict)   # "X"/"Y" -> ReacaoDiscretizada
    grelha: Optional[ResultadoGrelha] = None
    modelo_reacao: str = "rigido"
    bielas: dict = field(default_factory=dict)   # "X"/"Y" -> ResultadoBielas

    @property
    def aprovado(self) -> bool:
        return (all(t.ok for t in self.tensoes)
                and all(e.ok for e in self.estabilidade)
                and all(p.ok for p in self.puncao)
                and all(a.dominio_ok and a.ancoragem_ok and a.as_suficiente
                        and a.espacamento_ok for a in self.armaduras)
                and self.rigida
                and (self.recalques is None or self.recalques.aprovado)
                and self.convergiu)

    def para_dicionario(self) -> dict:
        from dataclasses import asdict
        return asdict(self)


# --------------------------------------------------------------------------- #
#  Classe principal
# --------------------------------------------------------------------------- #
class Sapata:
    """
    Sapata isolada rígida de concreto armado.

    Exemplo
    -------
    >>> s = Sapata(pilar, solo, concreto, aco, combinacoes, cobrimento=0.05)
    >>> r = s.dimensionar()
    """

    def __init__(self, pilar: Pilar, solo: Solo, concreto: Concreto, aco: Aco,
                 combinacoes: Sequence[Combinacao], cobrimento: float = 0.05,
                 opcoes: Optional[OpcoesProjeto] = None) -> None:
        self.pilar = pilar
        self.solo = solo
        self.concreto = concreto
        self.aco = aco
        self.combinacoes = list(combinacoes)
        self.cobrimento = cobrimento          # NBR 6118, Tab. 7.2 (CAA III -> 4,5 cm)
        self.op = opcoes or OpcoesProjeto()

        self.combs_els = filtrar(self.combinacoes, TipoCombinacao.ELS_RARA)
        self.combs_elu = filtrar(self.combinacoes, TipoCombinacao.ELU)
        self.combs_qp = filtrar(self.combinacoes, TipoCombinacao.ELS_QP)
        if not self.combs_els or not self.combs_elu:
            raise ValueError("São necessárias combinações ELS-rara e ELU.")

        # geometria (definida no dimensionamento)
        self.a = self.b = self.h = self.h0 = 0.0
        self.phi_estimado_mm = 12.5
        self.reacoes: dict = {}
        self.grelha: Optional[ResultadoGrelha] = None
        self.bielas: dict = {}
        self.classificacao: Optional[Classificacao] = None
        self.alertas: list[str] = []

    # ===================================================================== #
    #  PASSO 1 - Dimensionamento geotécnico (planta)
    # ===================================================================== #
    def _arredondar(self, valor: float) -> float:
        m = self.op.modulo_dim
        return round(math.ceil(valor / m - 1e-9) * m, 4)

    def _planta_para_area(self, area: float) -> tuple[float, float]:
        """
        Dimensões em planta para uma área necessária, com BALANÇOS IGUAIS
        (sapata homotética): a - ap = b - bp, resolvendo

            (ap + c)(bp + c) = A   ->   c² + (ap + bp)·c + ap·bp - A = 0

        Se uma das dimensões estiver travada, a outra é obtida diretamente.

        Piso de balanço: carga pequena com pilar grande faz a área necessária
        cair dentro da própria seção do pilar (c = 0) e a sapata degeneraria em
        a = ap. Sem balanço não há sapata — nem momento no balanço, nem
        classificação de 22.6.1 (que pressupõe (a - ap)/2 > 0). As dimensões
        livres recebem, por isso, o balanço mínimo `OpcoesProjeto.balanco_minimo`
        POR LADO — critério de projeto, com nome próprio, e não a granularidade
        de desenho `modulo_dim` (com o padrão 0,05 m os dois coincidem, e a
        saída é idêntica à da versão anterior).
        Dimensão TRAVADA pelo projetista não é corrigida em silêncio: se ela
        não couber, `rigidez.classificar` levanta ValueError com a mensagem
        explícita.
        """
        ap, bp = self.pilar.ap, self.pilar.bp
        folga = 2.0 * self.op.balanco_minimo    # um balanço mínimo de cada lado

        def livre(dim_pilar: float, valor: float) -> float:
            return max(self.op.dim_minima, self._arredondar(valor),
                       self._arredondar(dim_pilar + folga))

        if self.op.travar_a:
            a = self.op.travar_a
            return a, livre(bp, area / a)
        if self.op.travar_b:
            b = self.op.travar_b
            return livre(ap, area / b), b

        disc = (ap + bp) ** 2 - 4.0 * (ap * bp - area)
        c = max((-(ap + bp) + math.sqrt(max(disc, 0.0))) / 2.0, 0.0)
        return livre(ap, ap + c), livre(bp, bp + c)

    def _planta_inicial(self) -> tuple[float, float]:
        """
        Área inicial com N_k acrescido do peso próprio estimado
        (5% a 10% de N_k - prática consagrada de pré-dimensionamento).
        """
        Nk = max(c.esforcos.N for c in self.combs_els)
        area = Nk * (1.0 + self.op.peso_proprio_estimado) / self.solo.sigma_adm
        return self._planta_para_area(area)

    # ---------------------------------------------------------------- volumes
    def _geometria_volumes(self, a: float, b: float, h: float, h0: float) -> dict:
        at = min(a, self.pilar.ap + 2.0 * self.op.folga_topo)
        bt = min(b, self.pilar.bp + 2.0 * self.op.folga_topo)
        A1, A2 = a * b, at * bt
        v_tronco = (h - h0) / 3.0 * (A1 + A2 + math.sqrt(A1 * A2))
        v_conc = A1 * h0 + v_tronco
        v_prisma = A1 * self.solo.hf
        v_pilar = self.pilar.area * max(0.0, self.solo.hf - h)
        v_solo = max(0.0, v_prisma - v_conc - v_pilar)
        balanco = max((a - at) / 2.0, (b - bt) / 2.0)
        inclin = math.degrees(math.atan2(h - h0, balanco)) if balanco > 0 else 90.0
        return {"at": at, "bt": bt, "v_concreto": v_conc, "v_solo": v_solo,
                "inclinacao": inclin}

    def _peso_proprio(self, a: float, b: float, h: float, h0: float) -> float:
        g = self._geometria_volumes(a, b, h, h0)
        return (self.concreto.peso_especifico * g["v_concreto"]
                + self.solo.gamma_solo * g["v_solo"])

    # ---------------------------------------------------------------- tensões
    def _estado_tensao(self, comb: Combinacao, a: float, b: float, h: float,
                       h0: float, incluir_peso: bool = True) -> EstadoTensao:
        """
        Tensões nos vértices sob flexão oblíqua composta.

        Momentos na BASE: Mx,base = Mx + Hy*h ; My,base = My + Hx*h
        Excentricidades:  e_x = My,base / N ; e_y = Mx,base / N
        Núcleo central de inércia (retângulo):  6*e_x/a + 6*e_y/b <= 1
        """
        e = comb.esforcos
        pp = self._peso_proprio(a, b, h, h0) if incluir_peso else 0.0
        N = e.N + pp
        Mx = e.Mx + e.Hy * h
        My = e.My + e.Hx * h
        A = a * b

        if N <= 1e-6:
            return EstadoTensao(comb.nome, N, Mx, My, math.inf, math.inf,
                                math.inf, 0.0, 0.0, False, 0.0,
                                "TRAÇÃO / levantamento", self.solo.sigma_adm, False)

        ex, ey = abs(My) / N, abs(Mx) / N
        k = 6.0 * ex / a + 6.0 * ey / b
        sigma_media = N / A

        if k <= 1.0 + 1e-9:
            smax = sigma_media * (1.0 + k)
            smin = sigma_media * (1.0 - k)
            area_c, metodo, dentro = A, "seção integralmente comprimida", True
            limite = self.solo.sigma_adm
        else:
            dentro = False
            limite = self.solo.sigma_adm * self.solo.coef_sigma_max_excentrico
            if 6.0 * ey / b < 0.02:                      # flexão praticamente uniaxial
                braco = a / 2.0 - ex
                if braco <= 0:
                    return EstadoTensao(comb.nome, N, Mx, My, ex, ey, math.inf, 0.0,
                                        sigma_media, False, 0.0,
                                        "resultante fora da base", limite, False)
                smax = 2.0 * N / (3.0 * b * braco)
                area_c = 3.0 * braco * b
                metodo = "parcialmente comprimida - diagrama triangular (uniaxial X)"
            elif 6.0 * ex / a < 0.02:
                braco = b / 2.0 - ey
                if braco <= 0:
                    return EstadoTensao(comb.nome, N, Mx, My, ex, ey, math.inf, 0.0,
                                        sigma_media, False, 0.0,
                                        "resultante fora da base", limite, False)
                smax = 2.0 * N / (3.0 * a * braco)
                area_c = 3.0 * braco * a
                metodo = "parcialmente comprimida - diagrama triangular (uniaxial Y)"
            else:                                         # flexão oblíqua
                a_ef, b_ef = a - 2.0 * ex, b - 2.0 * ey
                if a_ef <= 0 or b_ef <= 0:
                    return EstadoTensao(comb.nome, N, Mx, My, ex, ey, math.inf, 0.0,
                                        sigma_media, False, 0.0,
                                        "resultante fora da base", limite, False)
                smax = N / (a_ef * b_ef)
                area_c = a_ef * b_ef
                metodo = "parcialmente comprimida - área efetiva de Meyerhof"
            smin = 0.0

        ok = (smax <= limite * (1.0 + 1e-6)
              and sigma_media <= self.solo.sigma_adm * (1.0 + 1e-6)
              and area_c >= self.op.area_comprimida_minima * A - 1e-9)
        return EstadoTensao(comb.nome, N, Mx, My, ex, ey, smax, smin, sigma_media,
                            dentro, area_c, metodo, limite, ok)

    def _dimensionar_planta(self) -> None:
        """
        Ajusta a e b até que TODAS as combinações de serviço satisfaçam:
            sigma_média <= sigma_adm
            sigma_máx   <= sigma_adm            (resultante no núcleo central)
            sigma_máx   <= 1,2 * sigma_adm      (seção parcialmente comprimida)
            área comprimida >= fração mínima da base
        A área é primeiro corrigida pela tensão MÉDIA (efeito de N + peso
        próprio real) mantendo a homotetia; em seguida, se ainda houver
        violação da tensão de pico, cresce-se na direção da maior
        excentricidade relativa.
        """
        a, b = self._planta_inicial()
        h, h0 = self._alturas(a, b)
        m = self.op.modulo_dim

        for _ in range(self.op.max_iteracoes):
            estados = [self._estado_tensao(c, a, b, h, h0) for c in self.combs_els]
            if all(t.ok for t in estados):
                self.a, self.b = a, b
                return

            # (i) correção pela tensão média -> nova área homotética
            pior_media = max(estados, key=lambda t: t.sigma_media)
            if pior_media.sigma_media > self.solo.sigma_adm:
                area_req = pior_media.N_total / self.solo.sigma_adm
                a_n, b_n = self._planta_para_area(area_req)
                if a_n > a + 1e-9 or b_n > b + 1e-9:
                    a, b = max(a, a_n), max(b, b_n)
                    h, h0 = self._alturas(a, b)
                    continue

            # (ii) correção pela tensão de pico / área comprimida
            pior = max(estados, key=lambda t: t.sigma_max / max(t.limite, 1e-9))
            if self.op.travar_a:
                b = round(b + m, 4)
            elif self.op.travar_b:
                a = round(a + m, 4)
            elif pior.ex / a >= pior.ey / b:
                a = round(a + m, 4)
            else:
                b = round(b + m, 4)
            h, h0 = self._alturas(a, b)

        self.a, self.b = a, b
        self.alertas.append("Não houve convergência do dimensionamento em planta; "
                            "revise sigma_adm, esforços ou trave dimensões.")

    # ===================================================================== #
    #  PASSO 2 - Geometria tridimensional
    # ===================================================================== #
    def _alturas(self, a: float, b: float, h_forcada: Optional[float] = None
                 ) -> tuple[float, float]:
        """
        Condição de sapata RÍGIDA, verificada nas duas direções:
            h >= (a - ap)/3   e   h >= (b - bp)/3
        Ref.: ABNT NBR 6118:2023, item 22.6.1, p. 191. [rule: NBR6118-22.6.1-rigidez]

        Implementação canônica do critério: `rigidez.classificar`, que devolve
        h_necessario/rigida_nbr. Aqui ele só é consumido para pré-dimensionar a
        altura; a classificação que vale no memorial vem de `classificar`.

        Altura da aba: h0 >= max(h/3 ; h0_min) - prática de projeto para garantir
        ancoragem e cobrimento das barras na borda, sem item normativo próprio.
        """
        h_rigida = max((a - self.pilar.ap) / 3.0, (b - self.pilar.bp) / 3.0)
        h = h_forcada if h_forcada else max(self.op.h_minima,
                                            self._arredondar(h_rigida))
        h0 = max(self.op.h0_minima, self._arredondar(h / 3.0))
        h0 = min(h0, h)
        return h, h0

    def _altura_util(self, h: float, phi_mm: float) -> tuple[float, float, float]:
        """Alturas úteis d_x (camada inferior) e d_y (camada superior)."""
        phi = phi_mm / 1000.0
        dx = h - self.cobrimento - phi / 2.0
        dy = h - self.cobrimento - 1.5 * phi
        return dx, dy, 0.5 * (dx + dy)

    # ===================================================================== #
    #  PASSO 3 - Punção e compressão diagonal (NBR 6118, item 19.5)
    # ===================================================================== #
    @staticmethod
    def _coef_K(c1_c2: float) -> float:
        """Coeficiente K da NBR 6118, Tab. 19.2 (momento transferido)."""
        tab = {0.5: 0.45, 1.0: 0.60, 2.0: 0.70, 3.0: 0.80}
        ch = sorted(tab)
        r = max(ch[0], min(ch[-1], c1_c2))
        for k0, k1 in zip(ch, ch[1:]):
            if k0 <= r <= k1:
                t = (r - k0) / (k1 - k0)
                return tab[k0] + t * (tab[k1] - tab[k0])
        return tab[ch[-1]]

    def _verificar_puncao(self, a: float, b: float, h: float, d: float,
                          rho: float) -> list[VerificacaoPuncao]:
        c = self.concreto
        ap, bp = self.pilar.ap, self.pilar.bp
        u0 = self.pilar.perimetro
        verificacoes: list[VerificacaoPuncao] = []

        # --- Contorno C: esmagamento das bielas (19.5.3.1) --------------------
        tau_rd2 = 0.27 * c.alpha_v * c.fcd * KPA      # kPa
        for comb in self.combs_elu:
            Fsd = comb.esforcos.N
            if Fsd <= 0:
                continue
            tau_sd = Fsd / (u0 * d)
            verificacoes.append(VerificacaoPuncao(
                comb.nome, "C (face do pilar) - compressão diagonal",
                tau_sd, tau_rd2, tau_sd / tau_rd2, tau_sd <= tau_rd2))

        # --- Contorno C' a 2d: tração diagonal (19.5.3.2) ---------------------
        # [rule: NBR6118-19.5.3.2-tauRd1]  ke=(1+sqrt(20/d))<=2, com d em CM
        # (p. 168). Versão anterior usava d em mm (d*1000) e não aplicava o
        # teto de 2 — as duas coisas subestimavam ke e, portanto, tau_Rd1
        # (resistência), tornando a verificação mais conservadora que a
        # norma exige, não insegura, mas com números errados no memorial.
        cabe = (a - ap) / 2.0 >= 2.0 * d and (b - bp) / 2.0 >= 2.0 * d
        d_cm = d * 100.0
        ke = min(2.0, 1.0 + math.sqrt(20.0 / d_cm))
        tau_rd1 = (0.13 * ke
                   * (100.0 * rho * c.fck) ** (1.0 / 3.0)) * KPA   # kPa

        flexivel = bool(self.classificacao and not self.classificacao.rigida_nbr)
        if not cabe:
            nota = ("Contorno C' externo à sapata: a ruptura se dá por "
                    "compressão diagonal (NBR 6118, 22.6.2). Verificado o "
                    "cisalhamento como laje.")
            if flexivel:
                nota = ("Sapata flexível (22.6.2.3-b) exigiria punção em C', mas o "
                        "contorno cai fora da base — governa o cisalhamento.")
            verificacoes.append(VerificacaoPuncao(
                "-", "C' (2d)", 0.0, tau_rd1, 0.0, True, nota))
            verificacoes.extend(self._verificar_cisalhamento(a, b, d, rho))
            return verificacoes

        u1 = u0 + 4.0 * math.pi * d
        area_int = ap * bp + 4.0 * d * (ap + bp) + 4.0 * math.pi * d ** 2
        c1, c2 = self.pilar.c1_c2
        K = self._coef_K(c1 / c2)
        Wp = (c1 ** 2 / 2.0 + c1 * c2 + 4.0 * c2 * d
              + 16.0 * d ** 2 + 2.0 * math.pi * d * c1)

        for comb in self.combs_elu:
            e = comb.esforcos
            Fsd = e.N
            if Fsd <= 0:
                continue
            sigma_d = Fsd / (a * b)
            Fsd_ef = max(0.0, Fsd - sigma_d * area_int)
            tau_sd = Fsd_ef / (u1 * d)
            obs = ("obrigatória para sapata flexível (22.6.2.3-b)" if flexivel
                   else "informativa: em sapata rígida governa a compressão "
                        "diagonal (22.6.2)")
            obs += " ; reação do solo interna a C' descontada"
            if self.op.considerar_excentricidade_puncao:
                Msd = max(abs(e.Mx + e.Hy * h), abs(e.My + e.Hx * h))
                tau_sd += K * Msd / (Wp * d)
                obs += " ; efeito de momento incluído (K da Tab. 19.2)"
            verificacoes.append(VerificacaoPuncao(
                comb.nome, "C' (a 2d da face) - tração diagonal",
                tau_sd, tau_rd1, tau_sd / tau_rd1, tau_sd <= tau_rd1, obs))
        return verificacoes

    def _verificar_cisalhamento(self, a: float, b: float, d: float,
                                rho: float) -> list[VerificacaoPuncao]:
        """
        Cisalhamento como laje sem armadura transversal (NBR 6118, 19.4.1),
        seção de referência a uma distância d da face do pilar.
            V_Rd1 = [tau_Rd * k * (1,2 + 40*rho1)] * b_w * d
            tau_Rd = 0,25 * f_ctd
        """
        out: list[VerificacaoPuncao] = []
        tau_rd = 0.25 * self.concreto.fctd * KPA
        k = max(1.0, 1.6 - d)
        vrd1 = tau_rd * k * (1.2 + 40.0 * rho) * d      # kN/m (por metro de largura)

        for direcao, dim, dim_p, larg in (("X", a, self.pilar.ap, b),
                                          ("Y", b, self.pilar.bp, a)):
            balanco = (dim - dim_p) / 2.0
            trecho = balanco - d
            if trecho <= 0:
                out.append(VerificacaoPuncao(
                    "-", f"cisalhamento dir. {direcao} [kN/m]", 0.0, vrd1, 0.0, True,
                    "seção de referência fora do balanço - não crítica"))
                continue
            for comb in self.combs_elu:
                Fsd = comb.esforcos.N
                if Fsd <= 0:
                    continue
                sigma_d = Fsd / (a * b)
                vsd = sigma_d * trecho                   # kN/m
                out.append(VerificacaoPuncao(
                    comb.nome, f"cisalhamento dir. {direcao} - seção a d da face [kN/m]",
                    vsd, vrd1, vsd / vrd1, vsd <= vrd1))
        return out

    # ===================================================================== #
    #  PASSO 4 - Flexão
    # ===================================================================== #
    def _momento_balanco(self, comb: Combinacao, a: float, b: float, h: float,
                         direcao: str) -> float:
        """
        Momento fletor de cálculo na seção de referência (face do pilar),
        integrando o diagrama real de pressões do solo na faixa de borda mais
        solicitada. A seção de referência na face do pilar é prática de
        engenharia consagrada, não item normativo específico: a NBR 6118:2023,
        22.6, não define a posição dessa seção. Decisão de engenharia.

        O cálculo por unidade de largura fica em `momentos.momento_unitario`,
        compartilhado com o mapa de isovalores para que os dois não divirjam.
        O peso próprio não entra: ele é equilibrado diretamente pelo solo sob a
        própria sapata e não produz flexão no balanço.
        """
        e = comb.esforcos
        mx = e.Mx + e.Hy * h
        my = e.My + e.Hx * h
        largura = b if direcao == "X" else a
        return momento_unitario(e.N, mx, my, a, b, self.pilar.ap, self.pilar.bp,
                                direcao) * largura

    def _momento_projeto(self, direcao: str, m_linear: float) -> float:
        """
        Momento adotado no dimensionamento, conforme o modelo de reação.

        O modelo elástico costuma dar momento MENOR que o linear em sapata
        flexível, porque a pressão se concentra sob o pilar. Como k_v carrega
        incerteza grande, o padrão continua sendo o linear (conservador) e a
        envoltória fica disponível para quem quiser o pior dos dois.
        """
        modelo = self.op.modelo_reacao
        if modelo == "rigido":
            return m_linear
        largura = self.b if direcao == "X" else self.a
        if modelo == "grelha" and self.grelha:
            m = (self.grelha.mx_face if direcao == "X"
                 else self.grelha.my_face) * largura
            return m
        r = self.reacoes.get(direcao)
        if not r:
            return m_linear
        m_elastico = r.momento_face * largura
        if modelo == "envoltoria":
            candidatos = [m_linear, m_elastico]
            if self.grelha:
                candidatos.append((self.grelha.mx_face if direcao == "X"
                                   else self.grelha.my_face) * largura)
            return max(candidatos)
        return m_elastico

    def _armadura_flexao_simples(self, Md: float, bw: float, d: float
                                 ) -> tuple[float, float, bool]:
        """
        Flexão simples com diagrama retangular (NBR 6118, 17.2.2):
            M_d = alpha_c * f_cd * b_w * (lambda*x) * (d - lambda*x/2)
        Retorna (As [m2], x/d, dominio_ok).
        """
        if Md <= 0:
            return 0.0, 0.0, True
        fcd = self.concreto.fcd * KPA
        fyd = self.aco.fyd * KPA
        ac, lam = self.concreto.alpha_c, self.concreto.lambda_x

        A = ac * fcd * bw * lam
        disc = (A * d) ** 2 - 2.0 * A * lam * Md
        if disc < 0:
            return math.inf, math.inf, False
        x = (A * d - math.sqrt(disc)) / (A * lam)
        z = d - lam * x / 2.0
        As = Md / (z * fyd)
        return As, x / d, (x / d) <= self.concreto.csi_limite

    # ===================================================================== #
    #  PASSO 5 - Detalhamento
    # ===================================================================== #
    def _arranjo_imposto(self, direcao: str, largura: float
                         ) -> Optional[tuple[float, int, float, float]]:
        """Arranjo fixado pelo projetista, se houver, para esta direção."""
        imp = self.op.armaduras_impostas.get(direcao)
        if imp is None:
            return None
        util = largura - 2.0 * self.cobrimento
        n = imp.quantidade(util)
        s = util / (n - 1) if n > 1 else util
        return imp.phi_mm, n, s, n * area_barra(imp.phi_mm)

    def _escolher_bitola(self, As_nec: float, largura: float
                         ) -> tuple[float, int, float, float]:
        """Seleciona bitola, número de barras e espaçamento (NBR 6118, 20.1)."""
        util = largura - 2.0 * self.cobrimento
        melhor = None
        for phi in self.op.bitolas:
            Ab = area_barra(phi)
            n = max(2, math.ceil(As_nec / Ab))
            s = util / (n - 1) if n > 1 else util
            if s < self.op.espacamento_min:
                continue                        # barras muito próximas -> sobe bitola
            if s > self.op.espacamento_max:      # adensa até o espaçamento máximo
                n = max(n, math.floor(util / self.op.espacamento_max) + 1)
                s = util / (n - 1) if n > 1 else util
            melhor = (phi, n, s, n * Ab)
            break
        if melhor is None:
            phi = self.op.bitolas[-1]
            Ab = area_barra(phi)
            n = max(2, math.ceil(As_nec / Ab))
            melhor = (phi, n, util / max(n - 1, 1), n * Ab)
            self.alertas.append("Espaçamento mínimo não atendido nem com a maior "
                                "bitola: considerar duas camadas ou aumentar a sapata.")
        return melhor

    def _ancoragem(self, phi_mm: float, As_calc: float, As_ef: float,
                   com_gancho: bool) -> float:
        """l_b,nec = alpha * l_b * As,calc/As,ef >= l_b,min (NBR 6118, 9.4.2.5)."""
        lb = comprimento_ancoragem_basico(phi_mm, self.concreto, self.aco,
                                          self.op.boa_aderencia)
        alpha = 0.7 if com_gancho else 1.0
        lb_min = max(0.3 * lb, 10.0 * phi_mm / 1000.0, 0.10)
        razao = As_calc / As_ef if As_ef > 0 else 1.0
        return max(alpha * lb * razao, lb_min)

    # ===================================================================== #
    #  Estabilidade global — FS global sobre combinações características.
    #  NÃO há item da NBR 6122:2022 que prescreva esta rota para deslizamento e
    #  tombamento de fundação rasa; §6.2.1.1.2, único item aplicável, usa
    #  coeficientes parciais sobre valores de cálculo. FS = 1,5 é prática
    #  consagrada, sem respaldo normativo direto, sob decisão de engenharia
    #  pendente.
    #  [rule: NBR6122-6.2.1.1.2-tracao-deslizamento-tombamento — PENDENTE_HUMANO]
    # ===================================================================== #
    def _verificar_estabilidade(self) -> list[VerificacaoEstabilidade]:
        out = []
        for comb in self.combs_els:
            e = comb.esforcos
            N = e.N + self._peso_proprio(self.a, self.b, self.h, self.h0)
            H = e.resultante_horizontal()
            # deslizamento: FS = (N*tan(delta) + c'*A) / H
            resist = N * math.tan(self.solo.atrito_base_rad) + self.solo.coesao * self.a * self.b
            fs_desl = resist / H if H > 1e-6 else math.inf
            # tombamento em torno das arestas
            mx = abs(e.Mx + e.Hy * self.h)
            my = abs(e.My + e.Hx * self.h)
            fs_tx = (N * self.a / 2.0) / my if my > 1e-6 else math.inf
            fs_ty = (N * self.b / 2.0) / mx if mx > 1e-6 else math.inf
            ok = (fs_desl >= self.solo.fs_deslizamento
                  and fs_tx >= self.solo.fs_tombamento
                  and fs_ty >= self.solo.fs_tombamento)
            out.append(VerificacaoEstabilidade(comb.nome, fs_desl, fs_tx, fs_ty, ok))
        return out

    # ===================================================================== #
    #  Rigidez e reação do solo
    # ===================================================================== #
    def _kv(self) -> float:
        """Coeficiente de reação vertical adotado [kN/m³]."""
        if self.op.kv:
            return self.op.kv
        return kv_por_tensao_admissivel(self.solo.sigma_adm,
                                        self.op.recalque_referencia_kv)

    def _comb_elu_governante(self) -> Combinacao:
        return max(self.combs_elu,
                   key=lambda c: max(self._momento_balanco(c, self.a, self.b,
                                                           self.h, "X"),
                                     self._momento_balanco(c, self.a, self.b,
                                                           self.h, "Y")))

    def _resolver_bielas(self, dx: float, dy: float) -> dict:
        """Modelo de bielas para a combinação última de maior carga axial."""
        combs = [c for c in self.combs_elu if c.esforcos.N > 0]
        if not combs:
            return {}
        melhor = {}
        for comb in combs:
            e = comb.esforcos
            r = bielas_sapata(e.N, e.Mx + e.Hy * self.h, e.My + e.Hx * self.h,
                              self.a, self.b, self.pilar.ap, self.pilar.bp,
                              dx, dy, self.concreto, self.aco,
                              self.op.coef_braco_bielas,
                              self.op.theta_minimo_biela)
            for direcao, val in r.items():
                if direcao not in melhor or val.T > melhor[direcao].T:
                    melhor[direcao] = val
        return melhor

    def _resolver_grelha(self) -> Optional[ResultadoGrelha]:
        """Resolve a sapata como grelha, para a combinação última governante."""
        if self.op.modelo_reacao == "rigido" and not self.op.divisoes_grelha:
            return None
        comb = self._comb_elu_governante()
        e = comb.esforcos
        if e.N <= 0:
            return None
        try:
            g = resolver_grelha(e.N, e.Mx + e.Hy * self.h, e.My + e.Hx * self.h,
                                self.a, self.b, self.pilar.ap, self.pilar.bp,
                                self.h, self.h0, self.concreto.Ecs, self._kv(),
                                divisoes=self.op.divisoes_grelha)
        except ValueError as erro:
            self.alertas.append(f"Grelha não pôde ser resolvida: {erro}")
            return None
        if abs(g.equilibrio - 1.0) > 0.02:
            self.alertas.append(
                f"Grelha fora de equilíbrio ({g.equilibrio:.3f}): resultado "
                "não confiável, reveja o refinamento.")
        for a in g.alertas:
            self.alertas.append(a)
        return g

    def _discretizar_reacao(self) -> dict:
        """
        Resolve cada direção como faixa sobre base elástica, para comparar a
        distribuição real de pressões com a linear do modelo rígido.
        """
        comb = self._comb_elu_governante()
        e = comb.esforcos
        if e.N <= 0:
            return {}
        mx = e.Mx + e.Hy * self.h
        my = e.My + e.Hx * self.h
        kv = self._kv()
        saida = {}
        for direcao, dim, largura, dim_p, momento in (
                ("X", self.a, self.b, self.pilar.ap, my),
                ("Y", self.b, self.a, self.pilar.bp, mx)):
            try:
                r = reacao_base_elastica(e.N, momento, dim, largura, dim_p,
                                         self.h, self.h0,
                                         self.concreto.Ecs, kv)
            except ValueError as erro:
                self.alertas.append(f"Reação discretizada na direção {direcao} "
                                    f"não pôde ser resolvida: {erro}")
                continue
            r.direcao = direcao
            saida[direcao] = r
        return saida

    # ===================================================================== #
    #  Recalques
    # ===================================================================== #
    def _analisar_recalques(self) -> Optional[ResultadoRecalque]:
        if not self.op.verificar_recalque or self.solo.perfil is None:
            if self.op.verificar_recalque and self.solo.perfil is None:
                self.alertas.append("Perfil geotécnico não informado: análise de "
                                    "recalques não executada.")
            return None
        combs = self.combs_qp or self.combs_els
        Nqp = max(c.esforcos.N for c in combs)
        pp = self._peso_proprio(self.a, self.b, self.h, self.h0)
        q = (Nqp + pp) / (self.a * self.b)
        analise = AnaliseRecalque(self.solo.perfil, self.a, self.b, self.solo.hf, q,
                                  limite_recalque_mm=self.op.limite_recalque_mm,
                                  vida_util_anos=self.op.vida_util_anos)
        return analise.executar()

    # ===================================================================== #
    #  Orquestração
    # ===================================================================== #
    def _avaliar(self, a: float, b: float, h: float, h0: float):
        """
        Uma passada de flexão + punção para a geometria dada.

        A classificação é refeita aqui porque muda com a altura, e é ela que
        decide se a punção em C' é obrigatória (22.6.2.3-b) ou informativa
        (22.6.2.2-b).
        """
        self.classificacao = classificar(a, b, h, h0, self.pilar.ap,
                                         self.pilar.bp, self.concreto.Ecs,
                                         self._kv())
        phi = self.phi_estimado_mm
        dx, dy, d = self._altura_util(h, phi)
        if d <= 0.05:
            return None, False, [], False, d
        self.bielas = (self._resolver_bielas(dx, dy)
                       if (self.classificacao.rigida_nbr
                           and self.op.modelo_armadura_rigida != "flexao")
                       else {})
        armaduras, ok_flexao, rho_x, rho_y = self._ciclo_flexao(a, b, h, dx, dy)
        # NBR 6118, 19.5.3.2, p. 168: rho = sqrt(rho_x*rho_y) <= 0,02 — teto
        # que faltava aqui (sem ele, tau_Rd1 seria superestimado em sapatas
        # muito armadas, o que é o sentido inseguro do erro).
        rho = min(0.02, math.sqrt(max(rho_x, 1e-6) * max(rho_y, 1e-6)))
        puncao = self._verificar_puncao(a, b, h, d, rho)
        return armaduras, ok_flexao, puncao, all(p.ok for p in puncao), d

    def dimensionar(self) -> ResultadoSapata:
        """
        Sem geometria imposta, procura a menor sapata que atende a tudo.
        Com geometria imposta, apenas verifica e relata o que não fecha.
        """
        self.alertas = []
        imposta = self.op.geometria_imposta
        modo_verificacao = imposta is not None

        if modo_verificacao:
            self.a, self.b = imposta.a, imposta.b
            self.h = imposta.h
            self.h0 = (imposta.h0 if imposta.h0
                       else max(self.op.h0_minima, self._arredondar(imposta.h / 3.0)))
            self.h0 = min(self.h0, self.h)
            # duas passadas: a primeira fixa a bitola estimada usada na altura útil
            for _ in range(2):
                armaduras, _, puncao, _, _ = self._avaliar(
                    self.a, self.b, self.h, self.h0)
                if armaduras is None:
                    self.alertas.append(
                        "Altura útil nula ou negativa: reveja h e o cobrimento.")
                    armaduras, puncao = [], []
                    break
            convergiu = True
        else:
            self._dimensionar_planta()
            self.h, self.h0 = self._alturas(self.a, self.b)
            armaduras, puncao, convergiu = [], [], False
            for _ in range(self.op.max_iteracoes):
                armaduras, ok_flexao, puncao, ok_puncao, _ = self._avaliar(
                    self.a, self.b, self.h, self.h0)
                if armaduras is not None and ok_flexao and ok_puncao:
                    convergiu = True
                    break
                self.h = self._arredondar(self.h + self.op.modulo_dim)
                self.h, self.h0 = self._alturas(self.a, self.b, self.h)
            if not convergiu:
                self.alertas.append(
                    "Altura não convergiu nas verificações de ELU; revise fck, "
                    "dimensões em planta ou o pilar.")

        a, b, h, h0 = self.a, self.b, self.h, self.h0

        # a classificação já foi refeita em _avaliar para a geometria final
        self.reacoes = self._discretizar_reacao()
        self.grelha = self._resolver_grelha()
        if self.op.modelo_reacao != "rigido" and (self.reacoes or self.grelha):
            # o modelo mudou os momentos: refaz flexão e punção uma vez
            armaduras, _, puncao, _, _ = self._avaliar(a, b, h, h0)
        for obs in self.classificacao.observacoes:
            self.alertas.append(obs)
        for bl in self.bielas.values():
            for al in bl.alertas:
                if al not in self.alertas:
                    self.alertas.append(al)

        _, _, d = self._altura_util(h, self.phi_estimado_mm)
        geo = self._geometria_volumes(a, b, h, h0)
        if geo["inclinacao"] > self.op.inclinacao_max_graus:
            self.alertas.append(
                f"Inclinação das faces superiores = {geo['inclinacao']:.1f}° > "
                f"{self.op.inclinacao_max_graus:.0f}°: será necessária forma na "
                "face inclinada (ou aumentar h0).")

        rigida = self.classificacao.rigida_nbr

        tensoes = [self._estado_tensao(c, a, b, h, h0) for c in self.combs_els]
        estabilidade = self._verificar_estabilidade()
        ancoragem_arranque = self._ancoragem_pilar(h)
        recalques = self._analisar_recalques()

        resultado = ResultadoSapata(
            a=a, b=b, h=h, h0=h0, d=d,
            volume_concreto=geo["v_concreto"],
            peso_proprio=self._peso_proprio(a, b, h, h0),
            inclinacao_graus=geo["inclinacao"],
            rigida=rigida, tensoes=tensoes, estabilidade=estabilidade,
            puncao=puncao, armaduras=armaduras or [],
            ancoragem_arranque=ancoragem_arranque, recalques=recalques,
            alertas=self.alertas, convergiu=convergiu,
            modo_verificacao=modo_verificacao,
            classificacao=self.classificacao, reacoes=self.reacoes,
            grelha=self.grelha, modelo_reacao=self.op.modelo_reacao,
            bielas=self.bielas)
        resultado.reprovacoes = self._listar_reprovacoes(resultado)
        return resultado

    @staticmethod
    def _listar_reprovacoes(res: ResultadoSapata) -> list[str]:
        """Resumo objetivo do que não atendeu, para avisar o projetista."""
        falhas: list[str] = []
        piores = [t for t in res.tensoes if not t.ok]
        if piores:
            pior = max(piores, key=lambda t: t.sigma_max if math.isfinite(t.sigma_max)
                       else 1e9)
            falhas.append(
                f"Tensão no solo: σ_máx = {pior.sigma_max:.0f} kPa contra "
                f"{pior.limite:.0f} kPa admitidos ({pior.combinacao}).")
        for e in res.estabilidade:
            if not e.ok:
                falhas.append(
                    f"Estabilidade em {e.combinacao}: FS deslizamento "
                    f"{e.fs_deslizamento:.2f}, tombamento "
                    f"{min(e.fs_tombamento_x, e.fs_tombamento_y):.2f}.")
                break
        for p in res.puncao:
            if not p.ok:
                falhas.append(
                    f"{p.contorno}: solicitante {p.tau_sd:.1f} contra resistente "
                    f"{p.tau_rd:.1f} (aproveitamento {p.aproveitamento:.2f}).")
        # sapata flexível não é reprovação: é outro caminho de verificação
        # (NBR 6118, 22.6.2.3-b), que exige punção — já coberta acima.
        for ar in res.armaduras:
            if not ar.as_suficiente:
                falhas.append(
                    f"Armadura na direção {ar.direcao}: {ar.As_efetiva*1e4:.2f} cm² "
                    f"efetivos contra {ar.As_adot*1e4:.2f} cm² necessários.")
            if not ar.dominio_ok:
                falhas.append(
                    f"Direção {ar.direcao}: x/d = {ar.x_d:.3f} acima do limite de "
                    "ductilidade — aumente a altura ou o f_ck.")
            if not ar.espacamento_ok:
                falhas.append(
                    f"Direção {ar.direcao}: espaçamento de {ar.espacamento*100:.1f} cm "
                    "fora dos limites.")
            if not ar.ancoragem_ok:
                falhas.append(
                    f"Direção {ar.direcao}: ancoragem exige "
                    f"{ar.lb_necessario*100:.0f} cm e há "
                    f"{ar.lb_disponivel*100:.0f} cm.")
        if res.ancoragem_arranque and not res.ancoragem_arranque.get("ok", True):
            falhas.append("Ancoragem dos arranques do pilar insuficiente.")
        if res.recalques and not res.recalques.aprovado:
            falhas.append(
                f"Recalque estimado {res.recalques.recalque_total_mm:.1f} mm "
                f"acima do limite de {res.recalques.limite_mm:.0f} mm.")
        if not res.convergiu:
            falhas.append("O dimensionamento automático não convergiu.")
        return falhas

    # ------------------------------------------------------------------ ciclo
    def _ciclo_flexao(self, a: float, b: float, h: float, dx: float, dy: float):
        """Dimensiona a armadura nas duas direções e devolve as taxas.

        Ref.: ABNT NBR 6118:2023, itens 22.6.2.2-a) e 22.6.2.3-a), p. 192.
        [rule: NBR6118-22.6.2.2a-flexao-duas-direcoes]

        REGRA DE PROIBIÇÃO: as duas direções são dimensionadas
        INCONDICIONALMENTE — o laço abaixo percorre ("X", ...) e ("Y", ...) sem
        nenhuma condição de entrada, e cada direção recebe o momento no próprio
        balanço, a própria armadura mínima integral e o próprio arranjo de
        barras. É PROIBIDO introduzir aqui redutor, teto ou dispensa de
        armadura numa direção dita "secundária", assim como qualquer
        classificação uni/bidirecional da sapata a partir da razão entre lados.
        As duas alíneas citadas são incondicionais quanto às duas direções, e o
        piso de 20 % de 20.1/Tabela 19.1 é MÍNIMO DE LAJE, nunca uma redução da
        armadura calculada de sapata.

        Protegido por tests/test_flexao_duas_direcoes_nbr_22_6_2.py.
        """
        armaduras: list[ArmaduraDirecao] = []
        ok_total = True
        taxas = {}

        for direcao, d_ef, dim, dim_p, largura in (
                ("X", dx, a, self.pilar.ap, b),
                ("Y", dy, b, self.pilar.bp, a)):
            Md = max((self._momento_balanco(c, a, b, h, direcao)
                      for c in self.combs_elu), default=0.0)
            Md = self._momento_projeto(direcao, Md)
            As, xd, dominio_ok = self._armadura_flexao_simples(Md, largura, d_ef)
            As_flexao = As if math.isfinite(As) else 0.0

            # sapata rígida: a NBR 6118, 22.6.3, admite bielas e tirantes,
            # que representa melhor o funcionamento da peça rígida
            biela = self.bielas.get(direcao)
            As_bielas = biela.As if biela else 0.0
            modelo_as = "flexao"
            if biela:
                if self.op.modelo_armadura_rigida == "bielas":
                    As, modelo_as = As_bielas, "bielas"
                elif self.op.modelo_armadura_rigida == "envoltoria":
                    As = max(As_flexao, As_bielas)
                    modelo_as = ("bielas" if As_bielas >= As_flexao else "flexao")
            # armadura mínima - NBR 6118, 19.3.3.2 / Tab. 17.3
            As_min = (self.op.fator_armadura_minima
                      * self.concreto.rho_min_flexao * largura * h)
            As_adot = max(As if math.isfinite(As) else 0.0, As_min)
            arranjo = self._arranjo_imposto(direcao, largura)
            imposta = arranjo is not None
            phi, n, s, As_ef = arranjo or self._escolher_bitola(As_adot, largura)

            as_suficiente = As_ef >= As_adot * 0.99
            espacamento_ok = (self.op.espacamento_min - 1e-6 <= s
                              <= self.op.espacamento_max + 1e-6)
            if imposta and not as_suficiente:
                self.alertas.append(
                    f"Direção {direcao}: armadura imposta {n} Ø {phi:.1f} mm "
                    f"fornece {As_ef*1e4:.2f} cm², abaixo dos "
                    f"{As_adot*1e4:.2f} cm² necessários.")
            if imposta and not espacamento_ok:
                self.alertas.append(
                    f"Direção {direcao}: espaçamento de {s*100:.1f} cm fora dos "
                    f"limites adotados ({self.op.espacamento_min*100:.0f} a "
                    f"{self.op.espacamento_max*100:.0f} cm).")

            L = (dim - dim_p) / 2.0
            lb_nec = self._ancoragem(phi, As_adot, As_ef, self.op.ganchos_nas_pontas)
            # comprimento reto disponível entre a seção de referência (face do
            # pilar) e a extremidade da barra, descontado o cobrimento lateral
            lb_disp = max(0.0, L - self.cobrimento)

            # geometria de corte da barra: trecho reto + dobra a 90° nas pontas,
            # limitada pela altura da aba (NBR 6118, 9.4.2.3)
            reto = dim - 2.0 * self.cobrimento
            gancho = max(10.0 * phi / 1000.0,
                         min(self.h0 - 2.0 * self.cobrimento, 20.0 * phi / 1000.0))
            gancho = max(0.0, gancho)
            comp = reto + 2.0 * gancho
            peso = comp * n * massa_linear(phi)

            armaduras.append(ArmaduraDirecao(
                direcao=direcao, Md=Md, d=d_ef, As_calc=As if math.isfinite(As) else 0.0,
                As_min=As_min, As_adot=As_adot, x_d=xd if math.isfinite(xd) else 0.0,
                phi_mm=phi, n_barras=n, espacamento=s, As_efetiva=As_ef,
                lb_necessario=lb_nec, lb_disponivel=lb_disp,
                ancoragem_ok=lb_nec <= lb_disp + 1e-6, dominio_ok=dominio_ok,
                comprimento_reto=reto, gancho=gancho, comprimento_barra=comp,
                peso_total=peso, imposta=imposta, as_suficiente=as_suficiente,
                espacamento_ok=espacamento_ok, modelo=modelo_as,
                As_flexao=As_flexao, As_bielas=As_bielas))
            taxas[direcao] = As_ef / (largura * d_ef) if d_ef > 0 else 0.0
            ok_total = ok_total and dominio_ok and as_suficiente

        # atualiza a bitola estimada para o próximo ciclo (altura útil)
        self.phi_estimado_mm = max(ar.phi_mm for ar in armaduras)
        return armaduras, ok_total, taxas["X"], taxas["Y"]

    def _ancoragem_pilar(self, h: float) -> dict:
        """Ancoragem das barras de arranque do pilar dentro da sapata."""
        phi = self.pilar.phi_arranque_mm
        lb = comprimento_ancoragem_basico(phi, self.concreto, self.aco,
                                          self.op.boa_aderencia)
        lb_min = max(0.6 * lb, 10.0 * phi / 1000.0, 0.10)   # compressão: alpha = 1,0
        lb_nec = max(lb * self.pilar.as_calc_efetiva, lb_min)
        disponivel = h - self.cobrimento
        ok = lb_nec <= disponivel + 1e-6
        if not ok:
            self.alertas.append(
                f"Ancoragem do arranque (phi {phi:.1f} mm) exige {lb_nec*100:.0f} cm "
                f"e há {disponivel*100:.0f} cm: prever dobra a 90° na base ou "
                "aumentar a altura da sapata.")
        return {"phi_mm": phi, "lb_basico": lb, "lb_necessario": lb_nec,
                "disponivel": disponivel, "ok": ok,
                "observacao": "Dobra a 90° na base permite reduzir a projeção reta "
                              "(NBR 6118, 9.4.2.5)."}
