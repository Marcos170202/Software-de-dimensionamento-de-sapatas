"""Coeficientes de ponderação da resistência do aço estrutural (ELU).

Fonte: ABNT NBR 8800:2024, 4.9.2 "Coeficientes de ponderação das
resistências no estado-limite último (ELU)", Tabela 3 "Valores dos
coeficientes de ponderação das resistências dos materiais γm" (página
25). Valores conferidos por leitura direta (renderização visual) do
PDF da norma — ver rastreabilidade completa em
``docs/normative/NBR8800-RULES.md``.

Escopo: apenas a coluna "Aço estrutural" (γa1 = escoamento e
instabilidade; γa2 = ruptura) da Tabela 3. As colunas de concreto (γc)
e aço das armaduras (γs) são omitidas nesta fase — sem elementos
mistos aço-concreto implementados ainda.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ._validation import is_positive_finite


class LoadCombinationClass(Enum):
    """Classificação da combinação última de ações — linhas da
    Tabela 3 (NBR 8800:2024, 4.9.2)."""

    NORMAL = "normal"
    ESPECIAL_OU_CONSTRUCAO = "especial_ou_construcao"
    EXCEPCIONAL = "excepcional"


@dataclass(frozen=True, slots=True)
class SteelResistanceFactors:
    """Coeficientes de ponderação da resistência do aço estrutural
    (NBR 8800:2024, 4.9.2, Tabela 3, coluna "Aço estrutural").

    ``gamma_a1``: estados-limite últimos de escoamento e instabilidade.
    ``gamma_a2``: estados-limite últimos de ruptura.
    """

    gamma_a1: float
    gamma_a2: float

    def __post_init__(self) -> None:
        if not is_positive_finite(self.gamma_a1):
            raise ValueError(
                f"gamma_a1 deve ser finito e positivo, recebido: {self.gamma_a1!r}"
            )
        if not is_positive_finite(self.gamma_a2):
            raise ValueError(
                f"gamma_a2 deve ser finito e positivo, recebido: {self.gamma_a2!r}"
            )


#: NBR 8800:2024, 4.9.2, Tabela 3 (RULE-ID NBR8800-RES-001 — ver
#: docs/normative/NBR8800-RULES.md).
_TABELA_3_ACO_ESTRUTURAL: dict[LoadCombinationClass, SteelResistanceFactors] = {
    LoadCombinationClass.NORMAL: SteelResistanceFactors(gamma_a1=1.10, gamma_a2=1.35),
    LoadCombinationClass.ESPECIAL_OU_CONSTRUCAO: SteelResistanceFactors(
        gamma_a1=1.10, gamma_a2=1.35
    ),
    LoadCombinationClass.EXCEPCIONAL: SteelResistanceFactors(gamma_a1=1.00, gamma_a2=1.15),
}


def steel_resistance_factors(combination_class: LoadCombinationClass) -> SteelResistanceFactors:
    """Devolve (γa1, γa2) para a classe de combinação dada (NBR
    8800:2024, 4.9.2, Tabela 3, coluna "Aço estrutural")."""
    return _TABELA_3_ACO_ESTRUTURAL[combination_class]
