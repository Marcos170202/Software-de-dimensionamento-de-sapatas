"""Barras prismáticas submetidas a força axial de tração.

Fonte: ABNT NBR 8800:2024, 5.2 "Barras prismáticas submetidas a força
axial de tração" (páginas 38-44). Fórmulas conferidas por leitura
direta (renderização visual) do PDF da norma — ver rastreabilidade
completa em ``docs/normative/NBR8800-RULES.md``.

Escopo desta fase: apenas

- 5.2.1.2 — condição de dimensionamento (``Nt,Sd <= Nt,Rd``);
- 5.2.2 — força axial resistente de cálculo, casos a) escoamento da
  seção bruta e b) ruptura da seção líquida;
- 5.2.4.2 — área líquida igual à área bruta quando não há furos.

**Fora do escopo** (fica para uma fase normativa futura): 5.2.3/5.2.5
(coeficiente de redução ``Ct`` para ligações soldadas/parafusadas —
requer modelagem de furos/soldas, que ``SteelSection`` não expressa),
5.2.6 (chapas ligadas por pino), 5.2.7 (barras redondas com
extremidades rosqueadas). A limitação do índice de esbeltez (5.2.8)
está em ``slenderness.py``.

Por isso esta API recebe a área líquida efetiva (``Ae``) diretamente
como parâmetro em vez de calculá-la — o chamador informa
``net_area_without_holes(section.area)`` no caso mais simples (sem
furos, 5.2.4.2) ou um valor já calculado externamente para os demais
casos.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from ._check_result import CheckResult
from ._validation import is_positive_finite
from .resistance_factors import SteelResistanceFactors


def net_area_without_holes(gross_area: float) -> float:
    """Área líquida quando não há furos na região considerada.

    NBR 8800:2024, 5.2.4.2: "Em regiões em que não existam furos, a
    área líquida, An, deve ser considerada igual à área bruta da seção
    transversal, Ag."
    """
    if not is_positive_finite(gross_area):
        raise ValueError(
            f"net_area_without_holes: gross_area deve ser finita e positiva, "
            f"recebido: {gross_area!r}"
        )
    return gross_area


@dataclass(frozen=True, slots=True)
class TensionCheckResult(CheckResult):
    """Resultado da verificação de uma barra tracionada (NBR 8800:2024,
    5.2.1.2/5.2.2).

    ``nt_rd_yield``: escoamento da seção bruta (5.2.2-a),
    ``Ag·fy/γa1``. ``nt_rd_rupture``: ruptura da seção líquida
    (5.2.2-b), ``Ae·fu/γa2``.
    """

    nt_sd: float
    nt_rd_yield: float
    nt_rd_rupture: float

    def __post_init__(self) -> None:
        for name in ("nt_sd", "nt_rd_yield", "nt_rd_rupture"):
            value = getattr(self, name)
            if not math.isfinite(value):
                raise ValueError(f"{name} deve ser finito, recebido: {value!r}")
        if not (self.nt_rd_yield > 0):
            raise ValueError(f"nt_rd_yield deve ser positivo, recebido: {self.nt_rd_yield!r}")
        if not (self.nt_rd_rupture > 0):
            raise ValueError(f"nt_rd_rupture deve ser positivo, recebido: {self.nt_rd_rupture!r}")

    @property
    def nt_rd(self) -> float:
        """Força axial de tração resistente de cálculo — o menor dos
        dois estados-limite (NBR 8800:2024, 5.2.2: "é o menor dos
        valores obtidos")."""
        return min(self.nt_rd_yield, self.nt_rd_rupture)

    @property
    def governing(self) -> Literal["escoamento_secao_bruta", "ruptura_secao_liquida"]:
        """Qual dos dois estados-limite de 5.2.2 governa (produz o
        menor Nt,Rd)."""
        if self.nt_rd_yield <= self.nt_rd_rupture:
            return "escoamento_secao_bruta"
        return "ruptura_secao_liquida"

    @property
    def sd(self) -> float:
        return self.nt_sd

    @property
    def rd(self) -> float:
        return self.nt_rd


def check_tension_member(
    nt_sd: float,
    gross_area: float,
    effective_net_area: float,
    fy: float,
    fu: float,
    resistance_factors: SteelResistanceFactors,
) -> TensionCheckResult:
    """Verifica uma barra prismática tracionada (NBR 8800:2024,
    5.2.1.2/5.2.2).

    ``nt_sd``: força axial de tração solicitante de cálculo (N),
    tipicamente o esforço axial de uma combinação última já ponderada
    (a ponderação em si e a extração do esforço a partir de um
    :class:`~estrutura_metalica.analysis.AnalysisResult` estão fora do
    escopo deste módulo). ``gross_area``/``fy``/``fu``: tipicamente
    ``section.area``/``material.fy``/``material.fu``.
    ``effective_net_area``: ``Ae`` — ver :func:`net_area_without_holes`
    para o caso sem furos.
    """
    if not math.isfinite(nt_sd):
        raise ValueError(f"check_tension_member: nt_sd deve ser finito, recebido: {nt_sd!r}")
    if not is_positive_finite(gross_area):
        raise ValueError(
            f"check_tension_member: gross_area deve ser finita e positiva, "
            f"recebido: {gross_area!r}"
        )
    if not is_positive_finite(effective_net_area):
        raise ValueError(
            f"check_tension_member: effective_net_area deve ser finita e positiva, "
            f"recebido: {effective_net_area!r}"
        )
    if effective_net_area > gross_area:
        # Ae = Ct*An e An <= Ag sempre (5.2.4.2); Ct tambem e <= 1 em
        # todos os casos de 5.2.5 — Ae > Ag e sempre erro de modelagem.
        raise ValueError(
            f"check_tension_member: effective_net_area ({effective_net_area!r}) não "
            f"pode ser maior que gross_area ({gross_area!r})"
        )
    if not is_positive_finite(fy):
        raise ValueError(f"check_tension_member: fy deve ser finito e positivo, recebido: {fy!r}")
    if not is_positive_finite(fu):
        raise ValueError(f"check_tension_member: fu deve ser finito e positivo, recebido: {fu!r}")

    nt_rd_yield = gross_area * fy / resistance_factors.gamma_a1
    nt_rd_rupture = effective_net_area * fu / resistance_factors.gamma_a2
    return TensionCheckResult(nt_sd=nt_sd, nt_rd_yield=nt_rd_yield, nt_rd_rupture=nt_rd_rupture)
