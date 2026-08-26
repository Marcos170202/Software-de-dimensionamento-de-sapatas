"""
acoes.py
--------
Esforços no topo da fundação (cota de arrasamento), casos de carga e geração
automática de combinações últimas e de serviço conforme ABNT NBR 6118:2023
(Seção 11) e NBR 8681:2003.

Convenção de eixos
------------------
    x, y : eixos horizontais em planta (a -> direção x ; b -> direção y)
    N    : carga axial de compressão (positiva comprimindo a sapata) [kN]
    Mx   : momento em torno do eixo X  -> gera excentricidade e_y = Mx / N  [kN.m]
    My   : momento em torno do eixo Y  -> gera excentricidade e_x = My / N  [kN.m]
    Hx   : força horizontal na direção X -> acresce My na base (Hx * h)     [kN]
    Hy   : força horizontal na direção Y -> acresce Mx na base (Hy * h)     [kN]
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from itertools import product
from typing import Iterable, Sequence


class TipoAcao(Enum):
    PERMANENTE = "permanente"
    VARIAVEL = "variavel"
    VENTO = "vento"


class TipoCombinacao(Enum):
    ELU = "ELU - combinação última normal"
    ELS_RARA = "ELS - combinação rara (verificação geotécnica)"
    ELS_QP = "ELS - combinação quase permanente (recalques)"


@dataclass(frozen=True)
class Esforcos:
    """Conjunto de esforços solicitantes no topo da fundação."""

    N: float = 0.0
    Mx: float = 0.0
    My: float = 0.0
    Hx: float = 0.0
    Hy: float = 0.0

    def __add__(self, outro: "Esforcos") -> "Esforcos":
        return Esforcos(self.N + outro.N, self.Mx + outro.Mx, self.My + outro.My,
                        self.Hx + outro.Hx, self.Hy + outro.Hy)

    def __mul__(self, k: float) -> "Esforcos":
        return Esforcos(self.N * k, self.Mx * k, self.My * k, self.Hx * k, self.Hy * k)

    __rmul__ = __mul__

    def invertido(self) -> "Esforcos":
        """Inverte o sentido da ação (para ações reversíveis, p.ex. vento)."""
        return self * -1.0

    def resultante_horizontal(self) -> float:
        return (self.Hx ** 2 + self.Hy ** 2) ** 0.5


@dataclass
class CasoCarga:
    """
    Caso de carga elementar.

    psi0 / psi1 / psi2 : fatores de combinação e de redução (NBR 6118, Tab. 11.2).
    reversivel         : se True, a ação é combinada com os dois sentidos (+/-).
    """

    nome: str
    esforcos: Esforcos
    tipo: TipoAcao = TipoAcao.PERMANENTE
    psi0: float = 0.7
    psi1: float = 0.6
    psi2: float = 0.4
    reversivel: bool = False

    @classmethod
    def vento(cls, nome: str, esforcos: Esforcos) -> "CasoCarga":
        """Ação do vento com psi da NBR 6118, Tab. 11.2 (edificações correntes)."""
        return cls(nome, esforcos, TipoAcao.VENTO, psi0=0.6, psi1=0.30, psi2=0.0,
                   reversivel=True)

    @classmethod
    def acidental(cls, nome: str, esforcos: Esforcos,
                  psi0: float = 0.7, psi1: float = 0.6, psi2: float = 0.4) -> "CasoCarga":
        return cls(nome, esforcos, TipoAcao.VARIAVEL, psi0, psi1, psi2)


@dataclass
class Combinacao:
    """Combinação de ações já majorada/ponderada."""

    nome: str
    tipo: TipoCombinacao
    esforcos: Esforcos

    @property
    def N(self) -> float:
        return self.esforcos.N

    def __repr__(self) -> str:  # pragma: no cover - conveniência
        e = self.esforcos
        return (f"<{self.nome}: N={e.N:.1f} kN, Mx={e.Mx:.1f}, My={e.My:.1f}, "
                f"Hx={e.Hx:.1f}, Hy={e.Hy:.1f}>")


# --------------------------------------------------------------------------- #
#  Geração de combinações
# --------------------------------------------------------------------------- #
def _sinais(casos: Sequence[CasoCarga], limite_casos_reversiveis: int = 6):
    """Produto cartesiano de sentidos (+1/-1) apenas para as ações reversíveis."""
    reversiveis = [c.reversivel for c in casos]
    if sum(reversiveis) > limite_casos_reversiveis:
        raise ValueError("Excesso de ações reversíveis; agrupe casos de vento.")
    opcoes = [(1.0, -1.0) if r else (1.0,) for r in reversiveis]
    return product(*opcoes) if opcoes else iter([()])


def gerar_combinacoes(casos: Iterable[CasoCarga],
                      gamma_g: float = 1.4,
                      gamma_g_favoravel: float = 1.0,
                      gamma_q: float = 1.4) -> list[Combinacao]:
    """
    Gera o conjunto completo de combinações últimas e de serviço.

    ELU normal (NBR 6118, eq. 11.3):
        Fd = gamma_g * Fgk + gamma_q * (Fq1k + sum(psi0j * Fqjk))
    ELS rara (eq. 11.6) - usada na verificação da tensão admissível do solo,
    conforme prática consagrada e NBR 6122:2019, item 6.2:
        Fd,ser = Fgk + Fq1k + sum(psi1j * Fqjk)
    ELS quase permanente (eq. 11.8) - usada na estimativa de recalques:
        Fd,ser = Fgk + sum(psi2j * Fqjk)

    Também é gerada a combinação com ações permanentes minoradas
    (gamma_g = 1,0) para as verificações de tombamento e deslizamento,
    em que o peso próprio é estabilizante (NBR 6122, item 6.2.1.2).
    """
    casos = list(casos)
    if not casos:
        raise ValueError("Nenhum caso de carga informado.")

    permanentes = [c for c in casos if c.tipo is TipoAcao.PERMANENTE]
    variaveis = [c for c in casos if c.tipo is not TipoAcao.PERMANENTE]

    G = Esforcos()
    for c in permanentes:
        G = G + c.esforcos

    combinacoes: list[Combinacao] = []

    # --- só ações permanentes -------------------------------------------------
    combinacoes.append(Combinacao("ELU-G", TipoCombinacao.ELU, G * gamma_g))
    combinacoes.append(Combinacao("ELS-G", TipoCombinacao.ELS_RARA, G))
    combinacoes.append(Combinacao("ELSQP-G", TipoCombinacao.ELS_QP, G))
    if variaveis:
        combinacoes.append(
            Combinacao("ELU-Gmin", TipoCombinacao.ELU, G * gamma_g_favoravel))

    # --- uma combinação por ação variável principal ---------------------------
    for i_princ, principal in enumerate(variaveis):
        for sinais in _sinais(variaveis):
            # ELU
            acao = G * gamma_g
            rotulo = [f"1.4G", f"1.4*{_rot(principal, sinais[i_princ])}"]
            acao = acao + principal.esforcos * (gamma_q * sinais[i_princ])
            for j, sec in enumerate(variaveis):
                if j == i_princ:
                    continue
                acao = acao + sec.esforcos * (gamma_q * sec.psi0 * sinais[j])
                rotulo.append(f"1.4*{sec.psi0:g}*{_rot(sec, sinais[j])}")
            combinacoes.append(
                Combinacao(" + ".join(rotulo), TipoCombinacao.ELU, acao))

            # ELU com permanente favorável (estabilidade)
            acao_min = G * gamma_g_favoravel
            acao_min = acao_min + principal.esforcos * (gamma_q * sinais[i_princ])
            for j, sec in enumerate(variaveis):
                if j != i_princ:
                    acao_min = acao_min + sec.esforcos * (gamma_q * sec.psi0 * sinais[j])
            combinacoes.append(
                Combinacao(f"ELU-est {_rot(principal, sinais[i_princ])}",
                           TipoCombinacao.ELU, acao_min))

            # ELS rara
            serv = G + principal.esforcos * sinais[i_princ]
            rot_s = ["G", _rot(principal, sinais[i_princ])]
            for j, sec in enumerate(variaveis):
                if j == i_princ:
                    continue
                serv = serv + sec.esforcos * (sec.psi1 * sinais[j])
                rot_s.append(f"{sec.psi1:g}*{_rot(sec, sinais[j])}")
            combinacoes.append(
                Combinacao(" + ".join(rot_s), TipoCombinacao.ELS_RARA, serv))

    # --- quase permanente (única) ---------------------------------------------
    qp = G
    for c in variaveis:
        qp = qp + c.esforcos * c.psi2
    combinacoes.append(Combinacao("G + sum(psi2*Q)", TipoCombinacao.ELS_QP, qp))

    return _remover_duplicatas(combinacoes)


def _rot(caso: CasoCarga, sinal: float) -> str:
    return f"{'-' if sinal < 0 else ''}{caso.nome}"


def _remover_duplicatas(combs: list[Combinacao]) -> list[Combinacao]:
    vistos: dict[tuple, Combinacao] = {}
    for c in combs:
        chave = (c.tipo, round(c.esforcos.N, 4), round(c.esforcos.Mx, 4),
                 round(c.esforcos.My, 4), round(c.esforcos.Hx, 4),
                 round(c.esforcos.Hy, 4))
        vistos.setdefault(chave, c)
    return list(vistos.values())


def filtrar(combs: Sequence[Combinacao], tipo: TipoCombinacao) -> list[Combinacao]:
    return [c for c in combs if c.tipo is tipo]


@dataclass
class Pilar:
    """Geometria do pilar apoiado na sapata."""

    ap: float                # dimensão na direção X [m]
    bp: float                # dimensão na direção Y [m]
    phi_arranque_mm: float = 16.0   # bitola das barras de arranque
    n_barras: int = 4
    as_calc_efetiva: float = 1.0    # As,calc / As,ef das barras do pilar

    def __post_init__(self) -> None:
        if self.ap <= 0 or self.bp <= 0:
            raise ValueError("Dimensões do pilar devem ser positivas.")

    @property
    def area(self) -> float:
        return self.ap * self.bp

    @property
    def perimetro(self) -> float:
        return 2.0 * (self.ap + self.bp)

    @property
    def c1_c2(self) -> tuple[float, float]:
        """(maior, menor) dimensão - usado nos coeficientes de punção."""
        return (max(self.ap, self.bp), min(self.ap, self.bp))
