"""Barras prismáticas submetidas a força axial de compressão.

Fonte: ABNT NBR 8800:2024, 5.3 "Barras prismáticas submetidas a força
axial de compressão" (páginas 45-52). Fórmulas conferidas por leitura
direta (renderização visual) do PDF da norma — ver rastreabilidade
completa em ``docs/normative/NBR8800-RULES.md``.

Escopo desta fase: apenas

- 5.3.1/5.3.2 — condição de dimensionamento (``Nc,Sd <= Nc,Rd``) e a
  fórmula de ``Nc,Rd``;
- 5.3.3 — fator de redução ``χ`` (ambos os ramos do índice de esbeltez
  reduzido ``λ0``);
- 5.3.4.1 — área efetiva igual à área bruta quando não há flambagem
  local (``b/t <= (b/t)lim`` para todos os elementos da seção);
- 5.3.5.1, casos a), b) e c) — força axial de flambagem por FLEXÃO em
  torno de cada eixo principal de inércia
  (:func:`flexural_buckling_force`) e por TORÇÃO
  (:func:`torsional_buckling_force`, com
  :func:`polar_radius_of_gyration`), para seções com dupla simetria ou
  simetria em relação a um ponto (``x0=y0=0`` na fórmula de ``r0``).

**ATENÇÃO — LIMITAÇÃO DE SEGURANÇA IMPORTANTE**: NBR 8800:2024, 5.3.5.1
exige que a força axial de flambagem, ``Ne``, usada em ``λ0`` seja o
MENOR entre TRÊS valores: ``Nex``, ``Ney`` e ``Nez`` — todos
implementados aqui (``Ne = min(flexural_buckling_force(E, Ix, Lx),
flexural_buckling_force(E, Iy, Ly), torsional_buckling_force(...))``).
Isso cobre COMPLETAMENTE 5.3.5.1 para seções com dupla simetria (I/H,
tubulares) ou simétricas em relação a um ponto (Z).

**O que continua FORA do escopo**: para seções MONOSSIMÉTRICAS
(5.3.5.2, ex.: perfis U/C, T) ou ASSIMÉTRICAS (5.3.5.3, ex.:
cantoneiras de abas desiguais), a norma NÃO permite usar
``min(Nex, Ney, Nez)`` diretamente — exige a força de flambagem por
FLEXO-TORÇÃO (``Neyz``, combinação não linear de ``Ney``/``Nez`` com a
excentricidade do centro de cisalhamento ``y0``/``x0``, não nula nesses
casos) ou a raiz de uma equação cúbica (5.3.5.3). Nenhuma das duas está
implementada. Usar :func:`polar_radius_of_gyration`/
:func:`torsional_buckling_force` com ``x0=y0=0`` (o único caso
suportado) para uma seção sem dupla simetria nem simetria em relação a
um ponto produziria um ``Nez`` correto isoladamente, mas usá-lo em
``min(Nex, Ney, Nez)`` como se fosse ``Ne`` seria NÃO CONSERVADOR
(inseguro) — a fórmula certa é ``Neyz``, ainda não implementada.

**Fora do escopo** (ver ``docs/normative/NBR8800-RULES.md``):
5.3.4.2/5.3.4.3 (área efetiva reduzida por flambagem local — requer
classificação de elementos da seção que ``SteelSection`` não
expressa), 5.3.5.2/5.3.5.3 (flexo-torção e seções assimétricas, ver
ATENÇÃO acima), 5.3.5.4 (cantoneiras simples conectadas por uma aba),
5.3.6 (barras compostas). A limitação do índice de esbeltez (5.3.7)
está em ``slenderness.py``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ._check_result import CheckResult
from ._validation import is_positive_finite
from .resistance_factors import SteelResistanceFactors


def flexural_buckling_force(
    elastic_modulus: float, moment_of_inertia: float, length: float
) -> float:
    """Força axial de flambagem elástica por flexão em torno de um
    eixo principal.

    NBR 8800:2024, 5.3.5.1, casos a) e b) — mesma fórmula para os
    eixos x e y (``Nex = π²EIx/Lx²``, ``Ney = π²EIy/Ly²``),
    parametrizada aqui por ``moment_of_inertia``/``length`` genéricos
    para não duplicar a fórmula duas vezes.

    ``length``: comprimento destravado associado à flexão nesse eixo —
    ``KL``, já incluindo o fator de comprimento efetivo ``K`` (não
    calculado por este módulo; NBR 8800 4.10, fora do escopo).
    """
    if not is_positive_finite(elastic_modulus):
        raise ValueError(
            f"flexural_buckling_force: elastic_modulus deve ser finito e positivo, "
            f"recebido: {elastic_modulus!r}"
        )
    if not is_positive_finite(moment_of_inertia):
        raise ValueError(
            f"flexural_buckling_force: moment_of_inertia deve ser finito e positivo, "
            f"recebido: {moment_of_inertia!r}"
        )
    if not is_positive_finite(length):
        raise ValueError(
            f"flexural_buckling_force: length deve ser finito e positivo, recebido: {length!r}"
        )
    return math.pi**2 * elastic_modulus * moment_of_inertia / length**2


def polar_radius_of_gyration(radius_of_gyration_x: float, radius_of_gyration_y: float) -> float:
    """Raio de giração polar da seção bruta em relação ao centro de
    cisalhamento, ``r0``.

    NBR 8800:2024, 5.3.5.1: ``r0 = sqrt(rx²+ry²+x0²+y0²)``, onde
    ``x0``/``y0`` são as coordenadas do centro de cisalhamento em
    relação ao centro geométrico da seção. **Esta função implementa
    apenas o caso ``x0=y0=0``** (seções com dupla simetria ou
    simétricas em relação a um ponto) — ver ATENÇÃO no docstring do
    módulo.
    """
    if not is_positive_finite(radius_of_gyration_x):
        raise ValueError(
            f"polar_radius_of_gyration: radius_of_gyration_x deve ser finito e "
            f"positivo, recebido: {radius_of_gyration_x!r}"
        )
    if not is_positive_finite(radius_of_gyration_y):
        raise ValueError(
            f"polar_radius_of_gyration: radius_of_gyration_y deve ser finito e "
            f"positivo, recebido: {radius_of_gyration_y!r}"
        )
    return math.sqrt(radius_of_gyration_x**2 + radius_of_gyration_y**2)


def torsional_buckling_force(
    elastic_modulus: float,
    shear_modulus: float,
    warping_constant: float,
    torsion_constant: float,
    polar_radius_of_gyration: float,
    length: float,
) -> float:
    """Força axial de flambagem elástica por torção em relação ao eixo
    longitudinal.

    NBR 8800:2024, 5.3.5.1-c): ``Nez = (1/r0²)·[π²ECw/Lz² + GJ]``.
    Válida apenas para seções com dupla simetria ou simétricas em
    relação a um ponto — ver :func:`polar_radius_of_gyration`.

    ``warping_constant``: ``Cw`` (m⁶) — tipicamente ``section.cw``
    (opcional em :class:`~estrutura_metalica.model.SteelSection`; o
    chamador deve resolver um ``None`` antes de chegar aqui, pois esta
    função exige um valor concreto). ``Cw=0`` é válido para seções
    fechadas/tubulares (sem empenamento).
    """
    if not is_positive_finite(elastic_modulus):
        raise ValueError(
            f"torsional_buckling_force: elastic_modulus deve ser finito e positivo, "
            f"recebido: {elastic_modulus!r}"
        )
    if not is_positive_finite(shear_modulus):
        raise ValueError(
            f"torsional_buckling_force: shear_modulus deve ser finito e positivo, "
            f"recebido: {shear_modulus!r}"
        )
    if not math.isfinite(warping_constant) or warping_constant < 0:
        raise ValueError(
            f"torsional_buckling_force: warping_constant deve ser finito e "
            f"não-negativo, recebido: {warping_constant!r}"
        )
    if not is_positive_finite(torsion_constant):
        raise ValueError(
            f"torsional_buckling_force: torsion_constant deve ser finito e positivo, "
            f"recebido: {torsion_constant!r}"
        )
    if not is_positive_finite(polar_radius_of_gyration):
        raise ValueError(
            f"torsional_buckling_force: polar_radius_of_gyration deve ser finito e "
            f"positivo, recebido: {polar_radius_of_gyration!r}"
        )
    if not is_positive_finite(length):
        raise ValueError(
            f"torsional_buckling_force: length deve ser finito e positivo, "
            f"recebido: {length!r}"
        )
    return (1.0 / polar_radius_of_gyration**2) * (
        math.pi**2 * elastic_modulus * warping_constant / length**2
        + shear_modulus * torsion_constant
    )


def effective_area_without_local_buckling(gross_area: float) -> float:
    """Área efetiva quando nenhum elemento da seção sofre flambagem
    local.

    NBR 8800:2024, 5.3.4.1: "A área efetiva da seção transversal, Aef,
    deve ser considerada igual à área bruta, Ag, se todos os elementos
    componentes [...] possuírem relação entre largura e espessura
    (b/t) igual ou inferior ao valor (b/t)lim [...]."
    """
    if not is_positive_finite(gross_area):
        raise ValueError(
            f"effective_area_without_local_buckling: gross_area deve ser finita e "
            f"positiva, recebido: {gross_area!r}"
        )
    return gross_area


def slenderness_parameter(gross_area: float, fy: float, elastic_buckling_force: float) -> float:
    """Índice de esbeltez reduzido, ``λ0`` (NBR 8800:2024, 5.3.3.2):
    ``λ0 = sqrt(Ag·fy/Ne)``.

    ``elastic_buckling_force``: ``Ne`` — ver ATENÇÃO no docstring do
    módulo sobre quais modos de flambagem este valor precisa
    contemplar.
    """
    if not is_positive_finite(gross_area):
        raise ValueError(
            f"slenderness_parameter: gross_area deve ser finita e positiva, "
            f"recebido: {gross_area!r}"
        )
    if not is_positive_finite(fy):
        raise ValueError(f"slenderness_parameter: fy deve ser finito e positivo, recebido: {fy!r}")
    if not is_positive_finite(elastic_buckling_force):
        raise ValueError(
            f"slenderness_parameter: elastic_buckling_force deve ser finito e "
            f"positivo, recebido: {elastic_buckling_force!r}"
        )
    return math.sqrt(gross_area * fy / elastic_buckling_force)


def reduction_factor(lambda_0: float) -> float:
    """Fator de redução associado à resistência à compressão, ``χ``
    (NBR 8800:2024, 5.3.3.1): ``χ = 0,658^(λ0²)`` para ``λ0 <= 1,5``;
    ``χ = 0,877/λ0²`` para ``λ0 > 1,5``.

    Nota: as duas fórmulas (ajustes empíricos independentes, mesma
    origem das curvas de flambagem do AISC 360) NÃO se encontram
    exatamente em ``λ0=1,5`` — diferença de ~0,04% relativo. É uma
    característica conhecida da curva normativa, não um erro de
    implementação.
    """
    if not math.isfinite(lambda_0) or lambda_0 < 0:
        raise ValueError(
            f"reduction_factor: lambda_0 deve ser finito e não-negativo, "
            f"recebido: {lambda_0!r}"
        )
    if lambda_0 <= 1.5:
        return float(0.658 ** (lambda_0**2))
    return 0.877 / lambda_0**2


@dataclass(frozen=True, slots=True)
class CompressionCheckResult(CheckResult):
    """Resultado da verificação de uma barra comprimida (NBR
    8800:2024, 5.3.1/5.3.2).

    ``nc_rd``: força axial de compressão resistente de cálculo (N),
    ``χ·Aef·fy/γa1``.
    """

    nc_sd: float
    lambda_0: float
    chi: float
    nc_rd: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.nc_sd):
            raise ValueError(f"nc_sd deve ser finito, recebido: {self.nc_sd!r}")
        if not math.isfinite(self.lambda_0) or self.lambda_0 < 0:
            raise ValueError(
                f"lambda_0 deve ser finito e não-negativo, recebido: {self.lambda_0!r}"
            )
        if not (0.0 < self.chi <= 1.0):
            raise ValueError(f"chi deve satisfazer 0 < chi <= 1, recebido: {self.chi!r}")
        if not is_positive_finite(self.nc_rd):
            raise ValueError(f"nc_rd deve ser finito e positivo, recebido: {self.nc_rd!r}")

    @property
    def sd(self) -> float:
        return self.nc_sd

    @property
    def rd(self) -> float:
        return self.nc_rd


def check_compression_member(
    nc_sd: float,
    gross_area: float,
    effective_area: float,
    fy: float,
    elastic_buckling_force: float,
    resistance_factors: SteelResistanceFactors,
) -> CompressionCheckResult:
    """Verifica uma barra prismática comprimida (NBR 8800:2024,
    5.3.1/5.3.2).

    Ver ATENÇÃO no docstring do módulo: ``elastic_buckling_force``
    precisa já ser o menor valor entre todos os modos de flambagem
    aplicáveis à seção real — este módulo não valida isso, apenas usa
    o valor fornecido.
    """
    if not math.isfinite(nc_sd):
        raise ValueError(f"check_compression_member: nc_sd deve ser finito, recebido: {nc_sd!r}")
    if not is_positive_finite(gross_area):
        raise ValueError(
            f"check_compression_member: gross_area deve ser finita e positiva, "
            f"recebido: {gross_area!r}"
        )
    if not is_positive_finite(effective_area):
        raise ValueError(
            f"check_compression_member: effective_area deve ser finita e positiva, "
            f"recebido: {effective_area!r}"
        )
    if effective_area > gross_area:
        raise ValueError(
            f"check_compression_member: effective_area ({effective_area!r}) não pode "
            f"ser maior que gross_area ({gross_area!r})"
        )
    if not is_positive_finite(fy):
        raise ValueError(
            f"check_compression_member: fy deve ser finito e positivo, recebido: {fy!r}"
        )

    lambda_0 = slenderness_parameter(gross_area, fy, elastic_buckling_force)
    chi = reduction_factor(lambda_0)
    nc_rd = chi * effective_area * fy / resistance_factors.gamma_a1
    return CompressionCheckResult(nc_sd=nc_sd, lambda_0=lambda_0, chi=chi, nc_rd=nc_rd)
