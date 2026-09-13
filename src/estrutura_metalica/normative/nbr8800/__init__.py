"""ABNT NBR 8800:2024 — Projeto de Estruturas de Aço e de Estruturas
Mistas de Aço e Concreto de Edifícios.

Ver ``docs/normative/NBR8800-RULES.md`` para a rastreabilidade
completa (RULE-ID → seção/página da norma → implementação → teste) de
cada regra implementada neste pacote.

Fases já implementadas: 4.9.2 (coeficientes de ponderação da
resistência), 5.2 (tração — escoamento/ruptura), 5.3 (compressão —
flambagem por flexão e por torção para seções com dupla simetria ou
simétricas em relação a um ponto), 5.2.8/5.3.7 (limitação recomendada
do índice de esbeltez), 5.4.1.3/5.4.3.1 (força cortante resistente de
cálculo de seções I/H/U fletidas no eixo perpendicular à alma),
5.4.1.3/5.4.2/Anexo D (momento fletor resistente de cálculo — FLT, FLM
e FLA — de seções I/H com dois eixos de simetria e seções U não
sujeitas a momento de torção, fletidas no eixo de maior momento de
inércia, vigas de alma não esbelta), Anexo E (momento fletor
resistente de cálculo de vigas de alma esbelta SOLDADAS, duplamente
simétricas), 5.5.1.2 (interação entre força axial e momento fletor
biaxial, barras sem torção) e Etapa 6 de ligações — 6.2.5.1 (força
resistente de cálculo do metal da solda em soldas de filete de pernas
iguais/ângulo reto, carregadas concentricamente) e 6.3.2/6.3.3
(parafusos comuns e de alta resistência e barras redondas rosqueadas
em ligações por contato — tração, cisalhamento, pressão de contato em
furos padrão e interação tração-cisalhamento).

Fora do escopo desta fase (ver docstrings dos módulos e
``docs/normative/NBR8800-RULES.md`` para a lista completa): força
cortante para os demais tipos de seção (5.4.3.2 a 5.4.3.6), demais
linhas da Tabela D.1 (seções monossimétricas, tubulares/caixão,
sólidas) e flexão no eixo de menor momento de inércia, seções-caixão e
tubulares de alma esbelta (Anexo E.6.4), vigas de alma esbelta com um
eixo de simetria, interação com momento de torção (5.5.2, seções
tubulares), seções monossimétricas/assimétricas em compressão
(5.3.5.2/5.3.5.3), barras compostas, verificação do metal-base em
soldas (6.5), soldas de penetração/tampão, grupos de filetes
excêntricos, ligações parafusadas por atrito/protensão crítica (6.3.4),
requisitos de espaçamento/distância a bordas de parafusos (6.3.7),
pinos (6.4), bases de pilares (6.7).
"""

from __future__ import annotations

from .bolts import (
    BoltCheckResult,
    BoltCombinedCheckResult,
    bolt_bearing_resistance,
    bolt_combined_tension_and_shear_ratio,
    bolt_effective_area_tension,
    bolt_gross_area,
    bolt_shear_resistance,
    bolt_tensile_resistance,
    check_bolt_bearing,
    check_bolt_combined_tension_and_shear,
    check_bolt_shear,
    check_bolt_tension,
    threaded_rod_tensile_resistance_cap,
)
from .combined_forces import (
    CombinedForcesCheckResult,
    axial_bending_interaction_ratio,
    check_axial_and_bending_interaction,
)
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
from .flexure import (
    FlexureCheckResult,
    check_flexural_resistance_major_axis,
    check_lateral_torsional_buckling,
    flange_local_buckling_coefficient_welded,
    flange_local_buckling_moment_rolled,
    flange_local_buckling_moment_welded,
    flexural_resistance,
    lateral_torsional_buckling_moment,
    lateral_torsional_buckling_slenderness_limit,
    moment_gradient_factor_doubly_symmetric,
    warping_constant_i_section,
)
from .resistance_factors import (
    LoadCombinationClass,
    SteelResistanceFactors,
    steel_resistance_factors,
    weld_metal_resistance_factor,
)
from .shear import (
    ShearCheckResult,
    check_shear_major_axis,
    effective_shear_area_major_axis,
    plastic_shear_force,
    shear_buckling_coefficient,
    shear_resistance,
)
from .slender_web import (
    check_flexural_resistance_slender_web_major_axis,
    check_slender_web_flange_local_buckling,
    check_slender_web_lateral_torsional_buckling,
    check_tension_flange_yielding,
    compression_flange_area_ratio,
    plate_girder_bending_strength_reduction_factor,
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
from .welds import (
    WeldCheckResult,
    check_fillet_weld_shear,
    fillet_weld_effective_area,
    fillet_weld_effective_throat,
    fillet_weld_shear_resistance,
    minimum_fillet_weld_leg_size,
)

__all__ = [
    "COMPRESSION_SLENDERNESS_LIMIT",
    "TENSION_SLENDERNESS_LIMIT",
    "BoltCheckResult",
    "BoltCombinedCheckResult",
    "CombinedForcesCheckResult",
    "CompressionCheckResult",
    "FlexureCheckResult",
    "LoadCombinationClass",
    "ShearCheckResult",
    "SlendernessCheckResult",
    "SteelResistanceFactors",
    "TensionCheckResult",
    "WeldCheckResult",
    "axial_bending_interaction_ratio",
    "bolt_bearing_resistance",
    "bolt_combined_tension_and_shear_ratio",
    "bolt_effective_area_tension",
    "bolt_gross_area",
    "bolt_shear_resistance",
    "bolt_tensile_resistance",
    "check_axial_and_bending_interaction",
    "check_bolt_bearing",
    "check_bolt_combined_tension_and_shear",
    "check_bolt_shear",
    "check_bolt_tension",
    "check_compression_member",
    "check_compression_slenderness",
    "check_fillet_weld_shear",
    "check_flexural_resistance_major_axis",
    "check_flexural_resistance_slender_web_major_axis",
    "check_lateral_torsional_buckling",
    "check_shear_major_axis",
    "check_slender_web_flange_local_buckling",
    "check_slender_web_lateral_torsional_buckling",
    "check_tension_flange_yielding",
    "check_tension_member",
    "check_tension_slenderness",
    "compression_flange_area_ratio",
    "effective_area_without_local_buckling",
    "effective_shear_area_major_axis",
    "fillet_weld_effective_area",
    "fillet_weld_effective_throat",
    "fillet_weld_shear_resistance",
    "flange_local_buckling_coefficient_welded",
    "flange_local_buckling_moment_rolled",
    "flange_local_buckling_moment_welded",
    "flexural_buckling_force",
    "flexural_resistance",
    "lateral_torsional_buckling_moment",
    "lateral_torsional_buckling_slenderness_limit",
    "minimum_fillet_weld_leg_size",
    "moment_gradient_factor_doubly_symmetric",
    "net_area_without_holes",
    "plastic_shear_force",
    "plate_girder_bending_strength_reduction_factor",
    "polar_radius_of_gyration",
    "reduction_factor",
    "shear_buckling_coefficient",
    "shear_resistance",
    "slenderness_parameter",
    "slenderness_ratio",
    "steel_resistance_factors",
    "threaded_rod_tensile_resistance_cap",
    "torsional_buckling_force",
    "warping_constant_i_section",
    "weld_metal_resistance_factor",
]
