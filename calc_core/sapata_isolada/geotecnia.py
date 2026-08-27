"""
geotecnia.py
------------
Parâmetros de projeto do solo, perfil estratigráfico (substrato), tensões
geostáticas e propagação de tensões no maciço.

Referências: ABNT NBR 6122:2019 (Projeto e execução de fundações),
NBR 6484 (SPT), Boussinesq (1885) / Newmark (1935).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

GAMMA_AGUA = 9.81  # kN/m3


class TipoSubstrato(Enum):
    """Comportamento predominante da camada quanto à deformabilidade."""

    GRANULAR = "granular"    # areias/pedregulhos -> recalque imediato (elástico)
    COESIVO = "coesivo"      # argilas saturadas  -> adensamento primário + secundário
    ROCHA = "rocha"          # recalque desprezível
    ATERRO = "aterro"        # tratado como granular, com alerta


@dataclass
class Camada:
    """
    Camada do perfil geotécnico (uma linha da sondagem interpretada).

    Parâmetros de deformabilidade
    -----------------------------
    GRANULAR : E_s [kPa] (ou nspt + correlação), nu
    COESIVO  : Cc, Cs, e0, OCR (ou sigma_vm), cv [m2/ano], C_alpha
    """

    nome: str
    espessura: float                          # [m]
    tipo: TipoSubstrato = TipoSubstrato.GRANULAR
    gamma_nat: float = 18.0                   # [kN/m3] acima do N.A.
    gamma_sat: float = 20.0                   # [kN/m3] abaixo do N.A.

    # --- resistência (estabilidade / capacidade de carga)
    phi: float = 30.0                         # ângulo de atrito efetivo [graus]
    coesao: float = 0.0                       # coesão efetiva [kPa]
    nspt: Optional[float] = None              # N_SPT médio da camada

    # --- deformabilidade: solos granulares
    Es: Optional[float] = None                # módulo de deformabilidade [kPa]
    nu: float = 0.30                          # coeficiente de Poisson

    # --- deformabilidade: solos coesivos
    Cc: Optional[float] = None                # índice de compressão
    Cs: Optional[float] = None                # índice de recompressão (~Cc/6)
    e0: Optional[float] = None                # índice de vazios inicial
    OCR: float = 1.0                          # razão de sobreadensamento
    cv: Optional[float] = None                # coef. de adensamento [m2/ano]
    C_alpha: Optional[float] = None           # coef. de compressão secundária
    drenagem_dupla: bool = True

    # --- correlação SPT -> Es (indicativa; NÃO substitui ensaio)
    k_spt_MPa: float = 3.5                    # Es[MPa] ~ k * N (areias)

    def gamma(self, abaixo_na: bool) -> float:
        return self.gamma_sat if abaixo_na else self.gamma_nat

    def modulo_deformabilidade(self) -> float:
        """Es [kPa] - do valor informado ou da correlação com o SPT."""
        if self.Es is not None:
            return self.Es
        if self.nspt is not None:
            return self.k_spt_MPa * self.nspt * 1000.0
        raise ValueError(f"Camada '{self.nome}': informe Es ou nspt.")

    def modulo_deformabilidade_opcional(self) -> Optional[float]:
        """Como modulo_deformabilidade(), mas devolve None se faltarem dados."""
        try:
            return self.modulo_deformabilidade()
        except ValueError:
            return None

    def indice_recompressao(self) -> float:
        if self.Cs is not None:
            return self.Cs
        if self.Cc is not None:
            return self.Cc / 6.0     # relação usual Cs ~ Cc/5 a Cc/10
        raise ValueError(f"Camada '{self.nome}': informe Cc/Cs.")


@dataclass
class PerfilGeotecnico:
    """
    Perfil estratigráfico a partir da superfície do terreno (z = 0, para baixo).

    nivel_agua : profundidade do N.A. [m] a partir da superfície (None = ausente)
    """

    camadas: list[Camada] = field(default_factory=list)
    nivel_agua: Optional[float] = None

    # ------------------------------------------------------------------ acesso
    @property
    def profundidade_total(self) -> float:
        return sum(c.espessura for c in self.camadas)

    def limites(self) -> list[tuple[float, float, Camada]]:
        """Lista de (z_topo, z_base, camada)."""
        z = 0.0
        out = []
        for c in self.camadas:
            out.append((z, z + c.espessura, c))
            z += c.espessura
        return out

    def camada_em(self, z: float) -> Camada:
        for z0, z1, c in self.limites():
            if z0 <= z < z1 or (abs(z - z1) < 1e-9 and c is self.camadas[-1]):
                return c
        if self.camadas:
            return self.camadas[-1]
        raise ValueError("Perfil geotécnico vazio.")

    # --------------------------------------------------- tensões geostáticas
    def tensao_vertical_total(self, z: float) -> float:
        """sigma_v [kPa] na profundidade z."""
        na = self.nivel_agua if self.nivel_agua is not None else math.inf
        sigma = 0.0
        restante = z
        for z0, z1, c in self.limites():
            if restante <= 0:
                break
            dz = min(z1, z) - z0
            if dz <= 0:
                continue
            # separa o trecho acima e abaixo do N.A.
            z_seco = max(0.0, min(z1, z, na) - z0)
            z_sub = max(0.0, dz - z_seco)
            sigma += z_seco * c.gamma_nat + z_sub * c.gamma_sat
            restante -= dz
        return sigma

    def poropressao(self, z: float) -> float:
        if self.nivel_agua is None or z <= self.nivel_agua:
            return 0.0
        return (z - self.nivel_agua) * GAMMA_AGUA

    def tensao_vertical_efetiva(self, z: float) -> float:
        """sigma'_v0 [kPa] na profundidade z."""
        return max(0.0, self.tensao_vertical_total(z) - self.poropressao(z))

    def tensao_pre_adensamento(self, z: float) -> float:
        """sigma'_vm [kPa] = OCR * sigma'_v0."""
        return self.camada_em(z).OCR * self.tensao_vertical_efetiva(z)


# --------------------------------------------------------------------------- #
#  Propagação de tensões
#
#  MÉTODOS NÃO NORMATIVOS. A NBR 6122:2022 não prescreve método de propagação
#  de tensão em profundidade. As duas soluções abaixo estão registradas em
#  `ruleset.yaml > praticas_consagradas` e se citam com `[pratica: <id>]`,
#  JAMAIS com `[rule: <id>]` — não há item normativo a apontar.
#
#  Namespace (REQ-PROP-08): 'a' e 'b' são dimensões EM PLANTA da sapata [m] e
#  'z' é profundidade GEOTÉCNICA medida A PARTIR DA BASE da sapata, para baixo
#  — não confundir com o 'b' de largura de seção nem com braço/altura do
#  domínio estrutural.
# --------------------------------------------------------------------------- #
FONTE_BOUSSINESQ = "boussinesq"
FONTE_2V1H = "2v1h"

ROTULO_FONTE = {
    FONTE_BOUSSINESQ: "Boussinesq/Newmark (método não normativo)",
    FONTE_2V1H: "Espraiamento 2V:1H — 26,57° (método não normativo)",
}

AVISO_NAO_NORMATIVO = (
    "Propagação de tensão em profundidade — método não normativo. A NBR "
    "6122:2022 não prescreve método de espraiamento. Valores informativos.")

AVISO_MEIO_HOMOGENEO = (
    "As camadas são exibidas com suas propriedades reais; o campo de tensões "
    "é calculado em meio homogêneo e NÃO representa o contraste de rigidez "
    "entre camadas.")


def _validar_dominio_propagacao(q: float, a: float, b: float, z: float) -> None:
    """Guarda de domínio comum às duas soluções de propagação.

    [pratica: PC-BOUSSINESQ-NEWMARK-canto-retangulo]
    [pratica: PC-ESPRAIAMENTO-2V1H]

    Exige z >= 0 com origem NA BASE da sapata (para baixo), a > 0, b > 0 e
    q >= 0. Erro de sinal na origem do eixo é o defeito mais provável no
    wiring e, sem esta guarda, não aparece como exceção: aparece como tensão
    plausível (z < 0 devolvia q no Boussinesq e 4q no 2V:1H).
    """
    if not (z >= 0.0):
        raise ValueError(
            f"z = {z} m: profundidade deve ser >= 0, medida a partir da BASE "
            "da sapata, para baixo (origem do eixo é a base, não a superfície "
            "do terreno).")
    if not (a > 0.0) or not (b > 0.0):
        raise ValueError(
            f"dimensões em planta inválidas: a = {a} m, b = {b} m (exige-se "
            "a > 0 e b > 0).")
    if not (q >= 0.0):
        raise ValueError(
            f"q = {q} kPa: a pressão aplicada deve ser >= 0 (usar a pressão "
            "LÍQUIDA na base, não a total).")


def influencia_canto_retangulo(m: float, n: float) -> float:
    """
    Fator de influência de Newmark para o CANTO de área retangular
    uniformemente carregada (solução de Boussinesq).

    [pratica: PC-BOUSSINESQ-NEWMARK-canto-retangulo]

        m = B / z ,  n = L / z

    ATENÇÃO: B e L são as dimensões DO RETÂNGULO CUJO CANTO está sobre a
    vertical do ponto analisado — NÃO as dimensões inteiras da sapata. Sob o
    centro de uma sapata a x b usa-se a superposição de quatro quadrantes,
    isto é, m = (a/2)/z e n = (b/2)/z (ver `acrescimo_tensao_centro`). Passar
    a largura inteira subestima Δσ.

    Método não normativo; a aprovação se apoia em verificação matemática
    própria (integração numérica da solução de carga pontual), não em
    autoridade bibliográfica. Valor de referência: I(1,1) = 0,17522.
    """
    if m < 0 or n < 0:
        raise ValueError(f"m = {m}, n = {n}: exige-se m >= 0 e n >= 0 "
                         "(razões entre dimensão do retângulo e profundidade).")
    if m == 0 or n == 0:
        return 0.0
    m2n2 = m * m + n * n
    num = 2.0 * m * n * math.sqrt(m2n2 + 1.0)
    den1 = m2n2 + 1.0 + (m * n) ** 2
    termo1 = (num / den1) * ((m2n2 + 2.0) / (m2n2 + 1.0))
    den2 = m2n2 + 1.0 - (m * n) ** 2
    # atan2 resolve automaticamente o acréscimo de pi quando den2 < 0
    termo2 = math.atan2(num, den2)
    return (termo1 + termo2) / (4.0 * math.pi)


def acrescimo_tensao_centro(q: float, a: float, b: float, z: float) -> float:
    """
    Acréscimo de tensão vertical [kPa] sob o CENTRO de uma sapata retangular
    a x b, à profundidade z abaixo da base (superposição de 4 quadrantes).

    [pratica: PC-BOUSSINESQ-NEWMARK-canto-retangulo]

        Δσ_z(z) = 4 · q · I(a/2z, b/2z)

    q é a pressão LÍQUIDA na base [kPa] (ver `tensao_liquida_na_base`); z é
    medido a partir da BASE da sapata, para baixo. Método não normativo,
    informativo — não é critério de aceitação de projeto.

    Hipóteses (nenhuma delas verificada aqui): meio semi-infinito homogêneo,
    isótropo, elástico-linear, sem peso, carregado por pressão uniforme em
    área flexível. Solo estratificado e sapata rígida NÃO são representados.

    Levanta ValueError se z < 0, a <= 0, b <= 0 ou q < 0.
    """
    _validar_dominio_propagacao(q, a, b, z)
    if z <= 1e-6:
        return q
    return 4.0 * q * influencia_canto_retangulo((a / 2.0) / z, (b / 2.0) / z)


def acrescimo_tensao_2v1h(q: float, a: float, b: float, z: float) -> float:
    """
    Acréscimo de tensão vertical [kPa] pelo espraiamento simplificado 2V:1H.

    [pratica: PC-ESPRAIAMENTO-2V1H]

        Δσ_z(z) = q · (a·b) / ((a+z)·(b+z))

    Convenção: 2 na vertical para 1 na horizontal (alargamento de z/2 por
    lado, arctan(0,5) = 26,57° com a vertical), com a resultante distribuída
    uniformemente sobre a área alargada — donde o equilíbrio vertical exato
    Δσ_z(z)·(a+z)·(b+z) = q·a·b. q é a pressão LÍQUIDA na base [kPa]; z é
    medido a partir da BASE da sapata, para baixo.

    USO RESTRITO (ruleset: APROVADA_COM_USO_RESTRITO): apenas VISUALIZAÇÃO e
    COMPARAÇÃO com Boussinesq, sempre rotulado como não normativo. PROIBIDO
    alimentar recalque (subestima Δσ na faixa rasa e produz recalque ~25 %
    menor, do lado inseguro), verificar camada subjacente, adotar ângulo
    variável por camada, ou dimensionar lastro de rachão / camada de reforço
    (efeito de contraste de rigidez, que este modelo de meio homogêneo não
    capta; a NBR 6122:2022 §1 exclui melhoramento do solo do seu escopo).

    Levanta ValueError se z < 0, a <= 0, b <= 0 ou q < 0.
    """
    _validar_dominio_propagacao(q, a, b, z)
    return q * (a * b) / ((a + z) * (b + z))


def acrescimo_tensao(fonte: str, q: float, a: float, b: float,
                     z: float) -> float:
    """
    Despacho por fonte: Δσ_z [kPa] pelo método pedido, sem escolher por conta
    própria qual é o "certo".

    [pratica: PC-BOUSSINESQ-NEWMARK-canto-retangulo]
    [pratica: PC-ESPRAIAMENTO-2V1H]

    fonte : FONTE_BOUSSINESQ ("boussinesq") ou FONTE_2V1H ("2v1h").

    Existem dois métodos legítimos e eles divergem em até ~37 % na faixa
    rasa; quem chama declara qual quer e o rótulo viaja junto com o número
    (ver `PropagacaoTensoes.fonte`).
    """
    if fonte == FONTE_BOUSSINESQ:
        return acrescimo_tensao_centro(q, a, b, z)
    if fonte == FONTE_2V1H:
        return acrescimo_tensao_2v1h(q, a, b, z)
    raise ValueError(
        f"fonte de propagação desconhecida: {fonte!r}. Use "
        f"{FONTE_BOUSSINESQ!r} ou {FONTE_2V1H!r}.")


# --------------------------------------------------------------------------- #
#  Parâmetros de projeto adotados para a fundação
# --------------------------------------------------------------------------- #
@dataclass
class Solo:
    """
    Parâmetros de projeto do solo de apoio da sapata (NBR 6122:2019).

    sigma_adm : tensão admissível [kPa] - obtida de prova de carga, métodos
                semiempíricos ou teoria de capacidade de carga com FS >= 3.
    hf        : profundidade da BASE da sapata (cota de assentamento) [m]
    """

    sigma_adm: float
    gamma_solo: float = 18.0
    hf: float = 1.50
    phi: float = 30.0
    coesao: float = 0.0
    fator_atrito_base: float = 2.0 / 3.0   # delta = 2/3 * phi (base rugosa)
    # FS global = 1,5 — PRÁTICA CONSAGRADA, SEM RESPALDO NORMATIVO. Não há item
    # da NBR 6122:2022 que prescreva FS global para deslizamento/tombamento de
    # fundação rasa: §6.2.1.1.2, único item aplicável, trata o assunto SÓ por
    # coeficientes parciais (FS global equivalente de 1,68 a 2,35). Valor sob
    # decisão de engenharia pendente — não alterar sem nova rodada do a2.
    # [rule: NBR6122-6.2.1.1.2-tracao-deslizamento-tombamento — PENDENTE_HUMANO]
    fs_deslizamento: float = 1.5
    fs_tombamento: float = 1.5
    coef_sigma_max_excentrico: float = 1.2  # majoração admitida no vértice
    perfil: Optional[PerfilGeotecnico] = None

    @property
    def atrito_base_rad(self) -> float:
        return math.radians(self.phi * self.fator_atrito_base)

    def sobrecarga_no_nivel_da_base(self) -> float:
        """q [kPa] do solo sobrejacente à cota de assentamento."""
        if self.perfil is not None:
            return self.perfil.tensao_vertical_efetiva(self.hf)
        return self.gamma_solo * self.hf


def sigma_adm_por_spt(nspt_medio: float, limite_MPa: float = 0.02) -> float:
    """
    Estimativa PRELIMINAR da tensão admissível [kPa] por correlação com o SPT
    (regra usual: sigma_adm [MPa] ~ N/50, com 5 <= N <= 20).

    ATENÇÃO: valor apenas indicativo para pré-dimensionamento. A NBR 6122:2019
    exige investigação geotécnica e justificativa formal da tensão adotada.
    """
    n = max(5.0, min(20.0, nspt_medio))
    return max(limite_MPa, n / 50.0) * 1000.0


# --------------------------------------------------------------------------- #
#  Propagação de tensões ao longo do perfil estratigráfico
#
#  Composição das duas soluções acima com o PerfilGeotecnico, para a
#  visualização em corte e para a coluna de Δσ por camada do memorial.
#
#  FRONTEIRA DESTA SEÇÃO (REQ-PROP-03, e é a fronteira exata da aprovação do
#  a2): tudo aqui é INFORMATIVO. Não há, e não pode passar a haver, nenhum
#  PASSA/NÃO PASSA, limite, alerta de segurança ou comparação contra σ_adm /
#  capacidade de carga de camada subjacente. O a2 aprovou o NÚMERO, não uma
#  verificação de projeto construída sobre ele.
# --------------------------------------------------------------------------- #
def tensao_liquida_na_base(q_aplicada: float, solo: "Solo") -> float:
    """
    Pressão LÍQUIDA na base [kPa] = q aplicada − sobrecarga geostática na cota
    de assentamento (alívio da escavação), limitada a valores não negativos.

    [pratica: PC-BOUSSINESQ-NEWMARK-canto-retangulo]
    [pratica: PC-ESPRAIAMENTO-2V1H]

    É a mesma conta de `AnaliseRecalque.q_liquido` e reaproveita
    `Solo.sobrecarga_no_nivel_da_base()` — que usa σ'_v0(hf) do perfil quando
    há perfil e γ·hf quando não há. Usar a pressão TOTAL superestimaria Δσ em
    toda a profundidade.

    Sem citação normativa: o alívio de escavação aparece na NBR 6122:2022 §7.2
    como um dos fatores a considerar, não como fórmula prescrita.
    """
    if not (q_aplicada >= 0.0):
        raise ValueError(f"q_aplicada = {q_aplicada} kPa: deve ser >= 0.")
    return max(0.0, q_aplicada - solo.sobrecarga_no_nivel_da_base())


def largura_equivalente(q_liquida: float, a: float, b: float,
                        delta_sigma: float) -> Optional[tuple[float, float]]:
    """
    Dimensões (a_eq, b_eq) [m] da área equivalente de espraiamento associada a
    um Δσ, para o traçado do tronco de espraiamento no corte.

    [pratica: PC-ESPRAIAMENTO-2V1H]

    Definição, por equivalência de carga total: a_eq·b_eq = q_líq·a·b / Δσ,
    com alargamento igual nas duas direções (a_eq − a = b_eq − b), que é a
    convenção geométrica do 2V:1H.

    Para a fonte 2V:1H o resultado é EXATO por construção (devolve a+z e b+z,
    pois o equilíbrio vertical é exato). Para Boussinesq/Newmark é apenas uma
    LEITURA GEOMÉTRICA ILUSTRATIVA do Δσ sob o centro — a solução elástica não
    tem tronco de espraiamento nem largura carregada, e a tensão real varia ao
    longo do plano horizontal. Não usar como largura de "área espraiada" em
    conta nenhuma.

    Devolve None quando não há largura definida (q_líq = 0 ou Δσ <= 0).
    """
    _validar_dominio_propagacao(q_liquida, a, b, 0.0)
    if q_liquida <= 0.0 or delta_sigma <= 0.0:
        return None
    area_eq = q_liquida * a * b / delta_sigma
    if area_eq <= a * b:
        return (a, b)
    s = a + b
    e = 0.5 * (-s + math.sqrt(s * s - 4.0 * (a * b - area_eq)))
    return (a + e, b + e)


@dataclass(frozen=True)
class PontoPropagacao:
    """Δσ em UMA profundidade — valor informativo, sem veredito (REQ-PROP-03).

    z                  : profundidade abaixo da BASE da sapata [m]
    profundidade       : profundidade absoluta, a partir da superfície [m]
    delta_sigma        : Δσ_z [kPa]
    largura_equivalente_a / _b : dimensões da área equivalente [m] (None se
                         indefinida); ilustrativas em Boussinesq — ver
                         `largura_equivalente`
    rotulo             : identificação do ponto no perfil ("base da sapata",
                         "base de 'Areia' / topo de 'Argila'", ...)
    fonte              : "boussinesq" ou "2v1h" — o método viaja junto com o
                         número (REQ-PROP-04)
    """

    z: float
    profundidade: float
    delta_sigma: float
    largura_equivalente_a: Optional[float]
    largura_equivalente_b: Optional[float]
    rotulo: str
    fonte: str


@dataclass(frozen=True)
class CamadaPropagacao:
    """Δσ no trecho de UMA camada dentro do intervalo analisado. Informativo.

    espessura é a do TRECHO analisado da camada (pode ser menor que a
    espessura da camada, se ela for cortada pela base da sapata ou pelo teto
    de profundidade). Corresponde aos L1/L2/L3 do desenho, assim como
    delta_sigma_topo/base correspondem aos q1/q2/q3.
    """

    indice: int
    nome: str
    tipo: str
    z_topo: float          # abaixo da base da sapata [m]
    z_base: float          # abaixo da base da sapata [m]
    espessura: float       # [m]
    delta_sigma_topo: float
    delta_sigma_base: float
    delta_sigma_medio: float
    fonte: str


@dataclass(frozen=True)
class PropagacaoTensoes:
    """Perfil de Δσ abaixo da base da sapata, por um método declarado.

    INFORMATIVO E NÃO NORMATIVO. Não contém, e não deve passar a conter,
    campo de aprovação, limite ou comparação com tensão admissível.
    """

    fonte: str
    rotulo_metodo: str
    q_aplicada: float
    sobrecarga_na_base: float
    q_liquida: float
    a: float
    b: float
    z_base_sapata: float       # cota de assentamento [m] (hf)
    z_max: float               # teto de profundidade efetivamente usado [m]
    pontos: tuple[PontoPropagacao, ...]
    camadas: tuple[CamadaPropagacao, ...]
    avisos: tuple[str, ...]
    informativo: bool = True   # sempre True — REQ-PROP-03


def propagacao_em_profundidade(solo: "Solo", a: float, b: float,
                               q_aplicada: float,
                               fonte: str = FONTE_BOUSSINESQ,
                               z_max: Optional[float] = None
                               ) -> PropagacaoTensoes:
    """
    Δσ nos limites de camada do perfil estratigráfico, abaixo da base da
    sapata, pelo método declarado em `fonte`.

    [pratica: PC-BOUSSINESQ-NEWMARK-canto-retangulo]
    [pratica: PC-ESPRAIAMENTO-2V1H]

    Parâmetros
    ----------
    solo       : `Solo` — de onde saem o perfil (`solo.perfil`), a cota de
                 assentamento (`solo.hf`) e a sobrecarga de alívio
                 (`solo.sobrecarga_no_nivel_da_base()`).
    a, b       : dimensões em planta da sapata [m], a > 0 e b > 0.
    q_aplicada : pressão TOTAL de serviço na base [kPa]. A pressão líquida é
                 calculada aqui (REQ-PROP-01) e devolvida em `q_liquida`.
    fonte      : FONTE_BOUSSINESQ (default) ou FONTE_2V1H. O software não
                 escolhe: para a comparação lado a lado use
                 `propagacao_comparada`.
    z_max      : teto de profundidade [m] abaixo da base a considerar. None =
                 até o fim do perfil informado.

    Teto de profundidade (REQ-UI-05 e `dominio_de_validade` das duas práticas)
    -------------------------------------------------------------------------
    A função NUNCA extrapola a estratigrafia: `z_max` é limitado à
    profundidade do perfil informado e, se o chamador pedir mais, o resultado
    vem truncado com um aviso em `avisos` — a última camada NÃO é estendida.
    O teto de exibição de 2·B é decisão da interface, que o passa em `z_max`.
    Se o perfil terminar na cota da base ou acima dela, devolve-se um
    resultado vazio (sem pontos e sem camadas) com o aviso correspondente, em
    vez de exceção — falta de sondagem não é erro de domínio.

    Natureza do resultado
    ---------------------
    Valores INFORMATIVOS (REQ-PROP-03): nenhuma comparação com σ_adm, nenhum
    juízo sobre camada subjacente, nenhum PASSA/NÃO PASSA. O campo é calculado
    em meio homogêneo e não representa o contraste de rigidez entre as camadas
    desenhadas (ver `avisos`).

    Levanta ValueError se a <= 0, b <= 0, q_aplicada < 0, z_max <= 0 ou
    `fonte` desconhecida.
    """
    if fonte not in ROTULO_FONTE:
        raise ValueError(
            f"fonte de propagação desconhecida: {fonte!r}. Use "
            f"{FONTE_BOUSSINESQ!r} ou {FONTE_2V1H!r}.")
    _validar_dominio_propagacao(q_aplicada, a, b, 0.0)
    if z_max is not None and not (z_max > 0.0):
        raise ValueError(f"z_max = {z_max} m: o teto de profundidade deve ser "
                         "> 0, medido a partir da base da sapata.")

    sobrecarga = solo.sobrecarga_no_nivel_da_base()
    q_liq = tensao_liquida_na_base(q_aplicada, solo)
    z_base = solo.hf
    avisos: list[str] = [AVISO_NAO_NORMATIVO, AVISO_MEIO_HOMOGENEO]
    if fonte == FONTE_2V1H:
        avisos.append(
            "Espraiamento 2V:1H é para visualização e comparação. Subestima "
            "Δσ na faixa rasa (~63 % de Boussinesq em z = B/2) e superestima "
            "abaixo de ~1,9·B, onde a comparação entre os dois inverte de "
            "sinal.")
    if q_liq <= 0.0:
        avisos.append(
            f"Pressão líquida nula: q aplicada ({q_aplicada:.1f} kPa) não "
            f"supera a sobrecarga na cota da base ({sobrecarga:.1f} kPa). "
            "Δσ = 0 em toda a profundidade.")

    perfil = solo.perfil
    if perfil is None or not perfil.camadas:
        avisos.append("Perfil geotécnico ausente: não há limites de camada "
                      "para reportar.")
        return PropagacaoTensoes(
            fonte=fonte, rotulo_metodo=ROTULO_FONTE[fonte],
            q_aplicada=q_aplicada, sobrecarga_na_base=sobrecarga,
            q_liquida=q_liq, a=a, b=b, z_base_sapata=z_base, z_max=0.0,
            pontos=(), camadas=(), avisos=tuple(avisos))

    disponivel = perfil.profundidade_total - z_base
    if disponivel <= 1e-6:
        avisos.append(
            f"Perfil geotécnico termina em {perfil.profundidade_total:.2f} m, "
            f"na cota da base da sapata ({z_base:.2f} m) ou acima dela: nada a "
            "propagar.")
        return PropagacaoTensoes(
            fonte=fonte, rotulo_metodo=ROTULO_FONTE[fonte],
            q_aplicada=q_aplicada, sobrecarga_na_base=sobrecarga,
            q_liquida=q_liq, a=a, b=b, z_base_sapata=z_base, z_max=0.0,
            pontos=(), camadas=(), avisos=tuple(avisos))

    z_pedido = disponivel if z_max is None else z_max
    z_fim = min(z_pedido, disponivel)
    if z_pedido > disponivel + 1e-6:
        avisos.append(
            f"Profundidade pedida ({z_pedido:.2f} m abaixo da base) excede o "
            f"perfil informado, que termina {disponivel:.2f} m abaixo da base. "
            "Resultado truncado; a última camada não foi estendida.")

    def ponto(z: float, rotulo: str) -> PontoPropagacao:
        ds = acrescimo_tensao(fonte, q_liq, a, b, z)
        larg = largura_equivalente(q_liq, a, b, ds)
        return PontoPropagacao(
            z=z, profundidade=z_base + z, delta_sigma=ds,
            largura_equivalente_a=None if larg is None else larg[0],
            largura_equivalente_b=None if larg is None else larg[1],
            rotulo=rotulo, fonte=fonte)

    limites = perfil.limites()
    pontos: list[PontoPropagacao] = [
        ponto(0.0, f"base da sapata / topo de '{perfil.camada_em(z_base).nome}'")]
    camadas: list[CamadaPropagacao] = []

    for indice, (abs_topo, abs_base, camada) in enumerate(limites):
        zi = max(abs_topo, z_base) - z_base          # relativo à base
        zf = min(abs_base, z_base + z_fim) - z_base
        if zf <= zi + 1e-9:
            continue
        ds_topo = acrescimo_tensao(fonte, q_liq, a, b, zi)
        ds_base = acrescimo_tensao(fonte, q_liq, a, b, zf)
        ds_medio = acrescimo_tensao(fonte, q_liq, a, b, 0.5 * (zi + zf))
        camadas.append(CamadaPropagacao(
            indice=indice, nome=camada.nome, tipo=camada.tipo.value,
            z_topo=zi, z_base=zf, espessura=zf - zi,
            delta_sigma_topo=ds_topo, delta_sigma_base=ds_base,
            delta_sigma_medio=ds_medio, fonte=fonte))
        if zf >= z_fim - 1e-9:
            proxima = (limites[indice + 1][2].nome
                       if indice + 1 < len(limites) else None)
            if abs(zf - (abs_base - z_base)) < 1e-9 and proxima:
                rotulo = f"base de '{camada.nome}' / topo de '{proxima}'"
            elif abs(zf - (abs_base - z_base)) < 1e-9:
                rotulo = f"base de '{camada.nome}' (fim do perfil)"
            else:
                rotulo = f"limite da análise, em '{camada.nome}'"
        else:
            proxima = (limites[indice + 1][2].nome
                       if indice + 1 < len(limites) else None)
            rotulo = (f"base de '{camada.nome}' / topo de '{proxima}'"
                      if proxima else f"base de '{camada.nome}'")
        pontos.append(ponto(zf, rotulo))

    return PropagacaoTensoes(
        fonte=fonte, rotulo_metodo=ROTULO_FONTE[fonte],
        q_aplicada=q_aplicada, sobrecarga_na_base=sobrecarga,
        q_liquida=q_liq, a=a, b=b, z_base_sapata=z_base, z_max=z_fim,
        pontos=tuple(pontos), camadas=tuple(camadas), avisos=tuple(avisos))


def propagacao_comparada(solo: "Solo", a: float, b: float, q_aplicada: float,
                         z_max: Optional[float] = None
                         ) -> dict[str, PropagacaoTensoes]:
    """
    Roda os DOIS métodos de propagação sobre o mesmo perfil e devolve ambos,
    indexados pela fonte — sem eleger um vencedor.

    [pratica: PC-BOUSSINESQ-NEWMARK-canto-retangulo]
    [pratica: PC-ESPRAIAMENTO-2V1H]

    A divergência entre os dois chega a ~37 % na faixa rasa e inverte de sinal
    abaixo de ~1,9·B: exibi-la lado a lado é informação útil ao projetista, e
    esconder a escolha atrás de um default seria opinião disfarçada de
    resultado. Cada `PropagacaoTensoes` carrega sua `fonte`, de modo que o
    número nunca circula sem o método que o produziu (REQ-PROP-04).
    """
    return {f: propagacao_em_profundidade(solo, a, b, q_aplicada, fonte=f,
                                          z_max=z_max)
            for f in (FONTE_BOUSSINESQ, FONTE_2V1H)}
