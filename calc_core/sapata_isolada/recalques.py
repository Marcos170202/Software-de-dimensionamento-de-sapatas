"""
recalques.py
------------
Análise de recalques de sapatas isoladas, com o método selecionado
automaticamente em função do SUBSTRATO de cada camada:

    GRANULAR : recalque imediato (elástico) + Schmertmann (1978)
    COESIVO  : recalque imediato (não drenado) + adensamento primário (Terzaghi)
               + compressão secundária (opcional) + evolução no tempo
    ROCHA    : desprezível

Referências
-----------
ABNT NBR 6122:2019, itens 6.2 e 7 (deslocamentos e sua verificação)
Terzaghi (1943); Schmertmann, Hartman & Brown (1978)
Perloff (1975) / Bowles (1996) - fatores de influência I_w
Skempton & MacDonald (1956); Burland & Wroth (1974) - limites de distorção
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from .geotecnia import (PerfilGeotecnico, TipoSubstrato,
                        acrescimo_tensao_2v1h, acrescimo_tensao_centro)

# --------------------------------------------------------------------------- #
#  Fatores de influência I_w (recalque elástico de área retangular)
#  Chave: L/B  ->  (centro flexível, canto flexível, médio flexível, rígido)
# --------------------------------------------------------------------------- #
TABELA_IW = {
    1.0: (1.12, 0.56, 0.95, 0.82),
    1.5: (1.36, 0.68, 1.15, 1.06),
    2.0: (1.53, 0.77, 1.30, 1.20),
    3.0: (1.78, 0.89, 1.52, 1.42),
    5.0: (2.10, 1.05, 1.83, 1.70),
    10.0: (2.54, 1.27, 2.25, 2.10),
}
_INDICE_IW = {"centro": 0, "canto": 1, "medio": 2, "rigido": 3}


def fator_influencia_iw(razao_LB: float, condicao: str = "rigido") -> float:
    """Interpola I_w da tabela de Perloff/Bowles."""
    if condicao not in _INDICE_IW:
        raise ValueError(f"Condição inválida: {condicao}")
    i = _INDICE_IW[condicao]
    chaves = sorted(TABELA_IW)
    r = max(chaves[0], min(chaves[-1], razao_LB))
    for k0, k1 in zip(chaves, chaves[1:]):
        if k0 <= r <= k1:
            t = (r - k0) / (k1 - k0)
            return TABELA_IW[k0][i] + t * (TABELA_IW[k1][i] - TABELA_IW[k0][i])
    return TABELA_IW[chaves[-1]][i]


# --------------------------------------------------------------------------- #
#  Recalque imediato (elástico)
# --------------------------------------------------------------------------- #
def recalque_elastico(q_liq: float, B: float, L: float, Es: float,
                      nu: float = 0.30, condicao: str = "rigido") -> float:
    """
    Recalque imediato [m] em semiespaço elástico homogêneo:

        rho = q_liq * B * (1 - nu^2) * I_w / E_s
    """
    if Es <= 0:
        raise ValueError("Módulo de deformabilidade nulo ou negativo.")
    Iw = fator_influencia_iw(max(L, B) / min(L, B), condicao)
    return q_liq * min(B, L) * (1.0 - nu ** 2) * Iw / Es


# --------------------------------------------------------------------------- #
#  Adensamento primário (Terzaghi)
# --------------------------------------------------------------------------- #
def recalque_adensamento(H: float, e0: float, Cc: float, Cs: float,
                         sigma_v0: float, delta_sigma: float,
                         sigma_vm: Optional[float] = None) -> float:
    """
    Recalque por adensamento primário [m] de uma subcamada de espessura H.

        NA  :  rho = H*Cc/(1+e0) * log10((s'0 + ds)/s'0)
        PA  :  rho = H*Cs/(1+e0) * log10((s'0 + ds)/s'0)          (s'f <= s'vm)
        PA* :  rho = H*Cs/(1+e0)*log10(s'vm/s'0)
                   + H*Cc/(1+e0)*log10(s'f/s'vm)                  (s'f  > s'vm)
    """
    if sigma_v0 <= 0 or delta_sigma <= 0:
        return 0.0
    sigma_f = sigma_v0 + delta_sigma
    svm = sigma_vm if sigma_vm is not None else sigma_v0
    svm = max(svm, sigma_v0)
    fator = H / (1.0 + e0)

    if svm <= sigma_v0 * (1.0 + 1e-9):                       # normalmente adensada
        return fator * Cc * math.log10(sigma_f / sigma_v0)
    if sigma_f <= svm:                                        # trecho de recompressão
        return fator * Cs * math.log10(sigma_f / sigma_v0)
    return (fator * Cs * math.log10(svm / sigma_v0)
            + fator * Cc * math.log10(sigma_f / svm))


def recalque_secundario(H: float, e0: float, C_alpha: float,
                        t_final_anos: float, t_primario_anos: float) -> float:
    """Compressão secundária [m]: rho = H*C_alpha/(1+e0) * log10(t/t_p)."""
    if C_alpha is None or t_final_anos <= t_primario_anos:
        return 0.0
    return H * C_alpha / (1.0 + e0) * math.log10(t_final_anos / t_primario_anos)


# --------------------------------------------------------------------------- #
#  Evolução do adensamento no tempo
# --------------------------------------------------------------------------- #
def fator_tempo(U: float) -> float:
    """Fator tempo T_v a partir do grau de adensamento U (0 a 1)."""
    U = min(max(U, 0.0), 0.999)
    if U <= 0.60:
        return math.pi / 4.0 * U ** 2
    return 1.781 - 0.933 * math.log10(100.0 * (1.0 - U))


def grau_adensamento(Tv: float) -> float:
    """Grau de adensamento médio U a partir do fator tempo T_v."""
    if Tv <= 0:
        return 0.0
    U = 2.0 * math.sqrt(Tv / math.pi)
    if U <= 0.60:
        return U
    return 1.0 - 10.0 ** (-(Tv + 0.085) / 0.933)


def tempo_para_grau(U: float, cv: float, Hd: float) -> float:
    """Tempo [anos] para atingir o grau de adensamento U. cv em m2/ano."""
    if cv <= 0 or Hd <= 0:
        return math.inf
    return fator_tempo(U) * Hd ** 2 / cv


# --------------------------------------------------------------------------- #
#  Schmertmann (1978) - areias
# --------------------------------------------------------------------------- #
def recalque_schmertmann(perfil: PerfilGeotecnico, q_liq: float, B: float,
                         L: float, z_base: float, t_anos: float = 10.0,
                         n_fatias: int = 40) -> dict:
    """
    Recalque em solo granular pelo método do fator de deformação de Schmertmann:

        rho = C1 * C2 * q_liq * SUM( Iz * dz / Es )
        C1 = 1 - 0,5 * (s'v0 / q_liq)   >= 0,5   (embutimento)
        C2 = 1 + 0,2 * log10(t / 0,1)            (fluência / creep)
    """
    razao = max(L, B) / min(L, B)
    B_ref = min(B, L)
    if razao < 1.5:                       # sapata quadrada / axissimétrica
        z_pico, z_final, Iz_sup = 0.5 * B_ref, 2.0 * B_ref, 0.10
    elif razao >= 10.0:                   # sapata corrida
        z_pico, z_final, Iz_sup = 1.0 * B_ref, 4.0 * B_ref, 0.20
    else:                                 # interpolação linear
        t = (razao - 1.5) / (10.0 - 1.5)
        z_pico = (0.5 + 0.5 * t) * B_ref
        z_final = (2.0 + 2.0 * t) * B_ref
        Iz_sup = 0.10 + 0.10 * t

    sigma_v0_base = perfil.tensao_vertical_efetiva(z_base)
    if q_liq <= 0:
        return {"recalque": 0.0, "C1": 1.0, "C2": 1.0, "Izp": 0.0}

    sigma_pico = perfil.tensao_vertical_efetiva(z_base + z_pico)
    Izp = 0.5 + 0.1 * math.sqrt(q_liq / max(sigma_pico, 1.0))

    C1 = max(0.5, 1.0 - 0.5 * sigma_v0_base / q_liq)
    C2 = 1.0 + 0.2 * math.log10(max(t_anos, 0.1) / 0.1)

    dz = z_final / n_fatias
    soma = 0.0
    for i in range(n_fatias):
        z_local = (i + 0.5) * dz
        if z_local <= z_pico:
            Iz = Iz_sup + (Izp - Iz_sup) * (z_local / z_pico)
        else:
            Iz = Izp * (z_final - z_local) / (z_final - z_pico)
        camada = perfil.camada_em(z_base + z_local)
        if camada.tipo is TipoSubstrato.ROCHA:
            continue
        Es = camada.modulo_deformabilidade_opcional()
        if Es is None:      # camada sem parâmetro elástico (p.ex. argila com Cc)
            continue
        soma += Iz * dz / Es

    return {"recalque": C1 * C2 * q_liq * soma, "C1": C1, "C2": C2,
            "Izp": Izp, "z_influencia": z_final}


# --------------------------------------------------------------------------- #
#  Análise integrada por substrato
# --------------------------------------------------------------------------- #
@dataclass
class ParcelaRecalque:
    camada: str
    tipo: str
    z_topo: float
    z_base: float
    sigma_v0: float
    delta_sigma: float
    recalque_mm: float
    metodo: str
    observacao: str = ""


@dataclass
class ResultadoRecalque:
    q_liquido: float
    recalque_total_mm: float
    recalque_imediato_mm: float
    recalque_adensamento_mm: float
    recalque_secundario_mm: float
    recalque_elastico_global_mm: float
    recalque_schmertmann_mm: Optional[float]
    profundidade_influencia: float
    parcelas: list[ParcelaRecalque] = field(default_factory=list)
    tempos: list[tuple[str, float, float]] = field(default_factory=list)
    limite_mm: float = 25.0
    aprovado: bool = True
    alertas: list[str] = field(default_factory=list)


class AnaliseRecalque:
    """
    Calcula os recalques da sapata percorrendo o perfil geotécnico abaixo da
    cota de assentamento e aplicando, em cada subcamada, o modelo adequado ao
    substrato encontrado.
    """

    def __init__(self, perfil: PerfilGeotecnico, a: float, b: float,
                 z_base: float, q_servico: float,
                 espessura_fatia: float = 0.50,
                 profundidade_influencia: Optional[float] = None,
                 limite_recalque_mm: float = 25.0,
                 vida_util_anos: float = 50.0,
                 usar_boussinesq: bool = True) -> None:
        self.perfil = perfil
        self.a, self.b = a, b
        self.B = min(a, b)
        self.L = max(a, b)
        self.z_base = z_base
        self.q_servico = q_servico            # tensão total na base [kPa]
        self.dz = espessura_fatia
        self.limite_mm = limite_recalque_mm
        self.vida_util = vida_util_anos
        self.usar_boussinesq = usar_boussinesq
        # bulbo de tensões: 2B (usual) limitado pelo perfil disponível
        self.z_influencia = profundidade_influencia or 2.0 * self.B

    # ------------------------------------------------------------------ útil
    @property
    def q_liquido(self) -> float:
        """
        Tensão líquida [kPa]: desconta a tensão geostática removida na
        escavação (alívio), conforme prática da NBR 6122.
        """
        return max(0.0, self.q_servico - self.perfil.tensao_vertical_efetiva(self.z_base))

    def _delta_sigma(self, z_abaixo_base: float) -> float:
        """Δσ [kPa] na fatia, com z medido a partir da BASE da sapata.

        [pratica: PC-BOUSSINESQ-NEWMARK-canto-retangulo]

        O ramo 2V:1H (`usar_boussinesq=False`) NÃO pode ser exposto na UI,
        ligado por default nem usado em memorial: medido contra Boussinesq,
        entrega 0,748 do recalque, sistematicamente do lado inseguro. Fica
        onde está, inalcançável na prática, até decisão humana — não criar um
        segundo caminho para ele.

        A expressão do 2V:1H era reescrita à mão aqui; agora chama
        `acrescimo_tensao_2v1h`, para que uma correção futura na fórmula não
        possa alcançar só uma das duas cópias.
        """
        if self.usar_boussinesq:
            return acrescimo_tensao_centro(self.q_liquido, self.a, self.b, z_abaixo_base)
        return acrescimo_tensao_2v1h(self.q_liquido, self.a, self.b, z_abaixo_base)

    # -------------------------------------------------------------- execução
    def executar(self) -> ResultadoRecalque:
        alertas: list[str] = []
        parcelas: list[ParcelaRecalque] = []
        tempos: list[tuple[str, float, float]] = []

        imediato = 0.0
        adensamento = 0.0
        secundario = 0.0

        z_max_perfil = self.perfil.profundidade_total
        z_fim = min(self.z_base + self.z_influencia, z_max_perfil)
        if z_fim <= self.z_base + 1e-6:
            alertas.append("Perfil geotécnico não cobre a profundidade da base "
                           "da sapata; recalques não avaliados.")
            return ResultadoRecalque(self.q_liquido, 0, 0, 0, 0, 0, None,
                                     self.z_influencia, alertas=alertas)
        if self.z_base + self.z_influencia > z_max_perfil + 1e-6:
            alertas.append(f"Sondagem termina em {z_max_perfil:.2f} m, antes do "
                           f"bulbo de tensões (2B = {self.z_influencia:.2f} m "
                           "abaixo da base). Recalques podem estar subestimados.")

        n = max(1, int(math.ceil((z_fim - self.z_base) / self.dz)))
        dz = (z_fim - self.z_base) / n

        for i in range(n):
            z0 = self.z_base + i * dz
            z1 = z0 + dz
            zm = 0.5 * (z0 + z1)
            camada = self.perfil.camada_em(zm)
            s_v0 = self.perfil.tensao_vertical_efetiva(zm)
            ds = self._delta_sigma(zm - self.z_base)

            if camada.tipo is TipoSubstrato.ROCHA:
                parcelas.append(ParcelaRecalque(camada.nome, camada.tipo.value,
                                                z0, z1, s_v0, ds, 0.0,
                                                "desprezível (rocha)"))
                continue

            if camada.tipo is TipoSubstrato.COESIVO:
                if camada.Cc is None or camada.e0 is None:
                    alertas.append(f"Camada coesiva '{camada.nome}' sem Cc/e0; "
                                   "usado modelo elástico como aproximação.")
                    Es = camada.modulo_deformabilidade()
                    rho = ds * dz / Es
                    metodo = "elástico (dados de adensamento ausentes)"
                    imediato += rho
                else:
                    svm = camada.OCR * s_v0
                    rho = recalque_adensamento(dz, camada.e0, camada.Cc,
                                               camada.indice_recompressao(),
                                               s_v0, ds, svm)
                    metodo = ("adensamento primário - "
                              + ("NA" if camada.OCR <= 1.0 else f"PA (OCR={camada.OCR:g})"))
                    adensamento += rho
                    if camada.C_alpha:
                        Hd = (camada.espessura / 2.0 if camada.drenagem_dupla
                              else camada.espessura)
                        tp = tempo_para_grau(0.95, camada.cv or 1.0, Hd)
                        rho_sec = recalque_secundario(dz, camada.e0, camada.C_alpha,
                                                      self.vida_util, max(tp, 0.1))
                        secundario += rho_sec
            else:
                Es = camada.modulo_deformabilidade()
                rho = ds * dz / Es      # deformação confinada equivalente
                metodo = "elástico por fatias (granular)"
                imediato += rho
                if camada.tipo is TipoSubstrato.ATERRO:
                    alertas.append(f"Camada '{camada.nome}' é aterro: verificar "
                                   "compactação e possibilidade de colapso.")

            parcelas.append(ParcelaRecalque(camada.nome, camada.tipo.value, z0, z1,
                                            s_v0, ds, rho * 1000.0, metodo))

        # --- tempos de adensamento por camada coesiva -------------------------
        for z0, z1, c in self.perfil.limites():
            if c.tipo is not TipoSubstrato.COESIVO or not c.cv:
                continue
            if z1 <= self.z_base or z0 >= z_fim:
                continue
            Hd = c.espessura / 2.0 if c.drenagem_dupla else c.espessura
            tempos.append((c.nome,
                           tempo_para_grau(0.50, c.cv, Hd),
                           tempo_para_grau(0.90, c.cv, Hd)))

        # --- estimativas globais de referência --------------------------------
        Es_eq = self._modulo_equivalente(z_fim)
        elastico_global = (recalque_elastico(self.q_liquido, self.B, self.L,
                                             Es_eq, 0.30, "rigido")
                           if Es_eq else 0.0)

        schmertmann = None
        if self._predominante(z_fim) is TipoSubstrato.GRANULAR:
            schmertmann = recalque_schmertmann(self.perfil, self.q_liquido,
                                               self.B, self.L, self.z_base,
                                               self.vida_util)["recalque"] * 1000.0

        total = (imediato + adensamento + secundario) * 1000.0
        resultado = ResultadoRecalque(
            q_liquido=self.q_liquido,
            recalque_total_mm=total,
            recalque_imediato_mm=imediato * 1000.0,
            recalque_adensamento_mm=adensamento * 1000.0,
            recalque_secundario_mm=secundario * 1000.0,
            recalque_elastico_global_mm=elastico_global * 1000.0,
            recalque_schmertmann_mm=schmertmann,
            profundidade_influencia=z_fim - self.z_base,
            parcelas=parcelas,
            tempos=tempos,
            limite_mm=self.limite_mm,
            aprovado=total <= self.limite_mm,
            alertas=alertas,
        )
        if not resultado.aprovado:
            resultado.alertas.append(
                f"Recalque total estimado ({total:.1f} mm) superior ao limite "
                f"adotado ({self.limite_mm:.0f} mm). Reavaliar geometria, cota de "
                "assentamento ou tipo de fundação (NBR 6122, item 6.2).")
        return resultado

    # ------------------------------------------------------------------ aux
    def _modulo_equivalente(self, z_fim: float) -> Optional[float]:
        """Módulo ponderado (média harmônica por espessura) no bulbo."""
        soma_h, soma = 0.0, 0.0
        for z0, z1, c in self.perfil.limites():
            zi, zf = max(z0, self.z_base), min(z1, z_fim)
            if zf <= zi or c.tipo is TipoSubstrato.ROCHA:
                continue
            Es = c.modulo_deformabilidade_opcional()
            if Es is None:
                continue
            soma_h += (zf - zi)
            soma += (zf - zi) / Es
        return soma_h / soma if soma > 0 else None

    def _predominante(self, z_fim: float) -> TipoSubstrato:
        acumulado: dict[TipoSubstrato, float] = {}
        for z0, z1, c in self.perfil.limites():
            zi, zf = max(z0, self.z_base), min(z1, z_fim)
            if zf > zi:
                acumulado[c.tipo] = acumulado.get(c.tipo, 0.0) + (zf - zi)
        return max(acumulado, key=acumulado.get) if acumulado else TipoSubstrato.GRANULAR


# --------------------------------------------------------------------------- #
#  Limites usuais de deslocamento (referência para o projetista)
# --------------------------------------------------------------------------- #
LIMITES_RECALQUE_MM = {
    "sapata isolada em areia": 25.0,     # Skempton & MacDonald
    "sapata isolada em argila": 40.0,
    "radier em areia": 50.0,
    "radier em argila": 65.0,
}

DISTORCAO_ANGULAR_LIMITE = {
    "danos estruturais": 1 / 150,
    "fissuras em paredes": 1 / 300,
    "estruturas sensíveis": 1 / 500,
}
