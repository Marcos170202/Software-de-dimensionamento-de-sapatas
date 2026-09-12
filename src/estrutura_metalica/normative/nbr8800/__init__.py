"""ABNT NBR 8800:2024 — Projeto de Estruturas de Aço e de Estruturas
Mistas de Aço e Concreto de Edifícios.

Ver ``docs/normative/NBR8800-RULES.md`` para a rastreabilidade
completa (RULE-ID → seção/página da norma → implementação → teste) de
cada regra implementada neste pacote.

Fases já implementadas: 4.9.2 (coeficientes de ponderação da
resistência), 5.2 (tração — escoamento/ruptura), 5.3 (compressão —
flambagem por flexão e por torção para seções com dupla simetria ou
simétricas em relação a um ponto), 5.2.8/5.3.7 (limitação recomendada
do índice de esbeltez).

Fora do escopo desta fase (ver docstrings dos módulos e
``docs/normative/NBR8800-RULES.md`` para a lista completa): força
cortante (5.4.3), momento fletor (5.4.2/Anexos D-E), interação de
esforços (5.5), seções monossimétricas/assimétricas em compressão
(5.3.5.2/5.3.5.3), barras compostas, ligações.
"""

from __future__ import annotations

from .compression import (
    CompressionCheckResult,
    check_compression_member,
    effective_area_without_local_buckling,
    flexural_buckling_force,
    polar_radius_of_gyration,
    reduction_factor,
    slenderness_parameter,
    torsional_buckling_force,
)
from .resistance_factors import (
    LoadCombinationClass,
    SteelResistanceFactors,
    steel_resistance_factors,
)
from .slenderness import (
    COMPRESSION_SLENDERNESS_LIMIT,
    TENSION_SLENDERNESS_LIMIT,
    SlendernessCheckResult,
    check_compression_slenderness,
    check_tension_slenderness,
    slenderness_ratio,
)
from .tension import TensionCheckResult, check_tension_member, net_area_without_holes

__all__ = [
    "COMPRESSION_SLENDERNESS_LIMIT",
    "TENSION_SLENDERNESS_LIMIT",
    "CompressionCheckResult",
    "LoadCombinationClass",
    "SlendernessCheckResult",
    "SteelResistanceFactors",
    "TensionCheckResult",
    "check_compression_member",
    "check_compression_slenderness",
    "check_tension_member",
    "check_tension_slenderness",
    "effective_area_without_local_buckling",
    "flexural_buckling_force",
    "net_area_without_holes",
    "polar_radius_of_gyration",
    "reduction_factor",
    "slenderness_parameter",
    "slenderness_ratio",
    "steel_resistance_factors",
    "torsional_buckling_force",
]
