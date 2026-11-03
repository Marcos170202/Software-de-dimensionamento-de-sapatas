"""Elementos de ligação.

Fonte: ABNT NBR 8800:2024, 6.5 "Elementos de ligação" (páginas 94-96).
Fórmulas conferidas por leitura direta (renderização visual) do PDF da
norma — ver rastreabilidade completa em
``docs/normative/NBR8800-RULES.md``.

Escopo desta fase: 6.5.3 a 6.5.6 — as verificações de resistência de
enrijecedores, chapas de ligação, cantoneiras, consolos e partes das
peças ligadas afetadas localmente pela ligação (6.5.1). Cobre:

- 6.5.3 — força de tração resistente de cálculo (escoamento E ruptura,
  menor valor);
- 6.5.4 — força de compressão resistente de cálculo (escoamento E
  instabilidade conforme 5.3, menor valor — ver ATENÇÃO 1 abaixo);
- 6.5.5 — força cortante resistente de cálculo (escoamento E ruptura,
  menor valor);
- 6.5.6 — colapso por rasgamento ("block shear").

**ATENÇÃO — LIMITAÇÕES/DECISÕES DE PROJETO**:

1. **6.5.4, ambiguidade de aplicabilidade no texto extraído**: o PDF
   lido apresenta, literalmente, "Le/r ≤ 25" tanto no item a)
   (escoamento) quanto no item b) (instabilidade) — aparente erro de
   digitação da norma (o padrão em todo o restante do documento é
   faixas de esbeltez COMPLEMENTARES/mutuamente exclusivas, e não faria
   sentido físico restringir a verificação de instabilidade a `Le/r`
   BAIXO). Em vez de arriscar uma leitura errada do limite exato,
   :func:`check_connection_element_compression` calcula SEMPRE os dois
   estados-limite (escoamento via :func:`axial_yield_resistance` e
   instabilidade via
   :func:`~estrutura_metalica.normative.nbr8800.compression.check_compression_member`,
   reaproveitado de 5.3) e toma o MENOR — correto e conservador em toda
   a faixa de esbeltez, tornando irrelevante a leitura exata do limite
   (para `Le/r` baixo, o próprio fator de redução χ de 5.3 já se
   aproxima de 1,0, convergindo para o resultado do item a)).
2. **6.5.4-b, apenas flambagem por flexão em um eixo**: reaproveita
   :func:`~estrutura_metalica.normative.nbr8800.compression.flexural_buckling_force`
   (``Ne = π²EI/Le²``) — um elemento de ligação típico (chapa,
   enrijecedor) não tem a complexidade de seção aberta de uma barra
   comprimida geral; flambagem por torção (5.3.5.1-c) NÃO é considerada
   aqui.
3. **6.5.3/6.5.5, área líquida efetiva não calculada**: ``effective_net_area``
   (tração) e ``net_shear_area``/``net_tension_area`` (cisalhamento/
   rasgamento) são parâmetros de entrada — o chamador deve descontar
   furos de parafusos da área bruta antes de invocar estas funções
   (mesma responsabilidade já documentada em
   :func:`~estrutura_metalica.normative.nbr8800.tension.net_area_without_holes`).
   O limite ``Ae = An <= 0,85·Ag`` (6.5.3, nota, específico de chapas de
   emenda parafusadas) está disponível como função separada e OPCIONAL
   (:func:`bolted_splice_plate_effective_net_area`) — NÃO aplicado
   automaticamente por :func:`check_connection_element_tension`, pois
   só se aplica a esse caso específico, não a toda chapa de ligação
   tracionada.
4. **6.5.6, ``Cts`` é parâmetro de entrada**: a norma define ``Cts=1,0``
   quando a tensão de tração na área líquida é uniforme e ``Cts=0,5``
   quando não é (Figura 16-b/c) — julgamento sobre a geometria da
   ligação que esta função não faz; o chamador deve determinar e
   informar o valor correto.

**Fora do escopo** (ver ``docs/normative/NBR8800-RULES.md``): 6.5.1
(generalidades, sem fórmula), 6.5.2 (ligações excêntricas — remete a
6.1.8.2/ABNT NBR 16239 para perfis tubulares, sem fórmula própria),
6.5.7 (chapas de enchimento — 6.5.7.1 é puramente construtivo; o fator
de redução de 6.5.7.2-a) está implementado em
:func:`~estrutura_metalica.normative.nbr8800.bolts.filler_plate_thickness_reduction_factor`,
não aqui; os itens b) e c) de 6.5.7.2, sobre prolongamento da chapa ou
parafusos equivalentes, são requisitos geométricos/de detalhamento).
"""

from __future__ import annotations

from dataclasses import dataclass

from ._check_result import CheckResult
from ._validation import is_positive_finite
from .compression import check_compression_member
from .resistance_factors import SteelResistanceFactors


def axial_yield_resistance(area: float, fy: float, gamma_a1: float) -> float:
    """Força axial resistente de cálculo ao escoamento, ``F_Rd`` (NBR
    8800:2024, 6.5.3-a — tração — e 6.5.4-a — compressão, mesma
    fórmula literal nos dois itens): ``F_Rd = fy·A/γa1``.

    ``area``: área bruta do elemento, ``Ag`` (m²).
    """
    if not is_positive_finite(area):
        raise ValueError(
            f"axial_yield_resistance: area deve ser finito e positivo, recebido: {area!r}"
        )
    if not is_positive_finite(fy):
        raise ValueError(f"axial_yield_resistance: fy deve ser finito e positivo, recebido: {fy!r}")
    if not is_positive_finite(gamma_a1):
        raise ValueError(
            f"axial_yield_resistance: gamma_a1 deve ser finito e positivo, "
            f"recebido: {gamma_a1!r}"
        )
    return fy * area / gamma_a1


def tensile_rupture_resistance(effective_net_area: float, fu: float, gamma_a2: float) -> float:
    """Força de tração resistente de cálculo ao estado-limite último de
    ruptura, ``F_Rd`` (NBR 8800:2024, 6.5.3-b): ``F_Rd = fu·Ae/γa2``.

    ``effective_net_area``: área líquida efetiva, ``Ae`` — ver ATENÇÃO
    3 no docstring do módulo e :func:`bolted_splice_plate_effective_net_area`.
    """
    if not is_positive_finite(effective_net_area):
        raise ValueError(
            f"tensile_rupture_resistance: effective_net_area deve ser finito e "
            f"positivo, recebido: {effective_net_area!r}"
        )
    if not is_positive_finite(fu):
        raise ValueError(
            f"tensile_rupture_resistance: fu deve ser finito e positivo, recebido: {fu!r}"
        )
    if not is_positive_finite(gamma_a2):
        raise ValueError(
            f"tensile_rupture_resistance: gamma_a2 deve ser finito e positivo, "
            f"recebido: {gamma_a2!r}"
        )
    return fu * effective_net_area / gamma_a2


def bolted_splice_plate_effective_net_area(net_area: float, gross_area: float) -> float:
    """Área líquida efetiva de uma chapa de emenda parafusada, ``Ae``
    (NBR 8800:2024, 6.5.3, nota): ``Ae = An <= 0,85·Ag``.

    Caso específico OPCIONAL — ver ATENÇÃO 3 no docstring do módulo.
    Não aplicado automaticamente por :func:`check_connection_element_tension`.

    ``net_area``: área líquida da chapa, ``An`` (m²). ``gross_area``:
    área bruta, ``Ag`` (m²).
    """
    if not is_positive_finite(net_area):
        raise ValueError(
            f"bolted_splice_plate_effective_net_area: net_area deve ser finito "
            f"e positivo, recebido: {net_area!r}"
        )
    if not is_positive_finite(gross_area):
        raise ValueError(
            f"bolted_splice_plate_effective_net_area: gross_area deve ser "
            f"finito e positivo, recebido: {gross_area!r}"
        )
    return min(net_area, 0.85 * gross_area)


def shear_yield_resistance(gross_area: float, fy: float, gamma_a1: float) -> float:
    """Força cortante resistente de cálculo ao estado-limite último de
    escoamento, ``F_Rd`` (NBR 8800:2024, 6.5.5-a):
    ``F_Rd = 0,60·fy·Ag/γa1``.
    """
    if not is_positive_finite(gross_area):
        raise ValueError(
            f"shear_yield_resistance: gross_area deve ser finito e positivo, "
            f"recebido: {gross_area!r}"
        )
    if not is_positive_finite(fy):
        raise ValueError(f"shear_yield_resistance: fy deve ser finito e positivo, recebido: {fy!r}")
    if not is_positive_finite(gamma_a1):
        raise ValueError(
            f"shear_yield_resistance: gamma_a1 deve ser finito e positivo, "
            f"recebido: {gamma_a1!r}"
        )
    return 0.60 * fy * gross_area / gamma_a1


def shear_rupture_resistance(net_shear_area: float, fu: float, gamma_a2: float) -> float:
    """Força cortante resistente de cálculo ao estado-limite último de
    ruptura, ``F_Rd`` (NBR 8800:2024, 6.5.5-b):
    ``F_Rd = 0,60·fu·Anv/γa2``.

    ``net_shear_area``: área líquida sujeita a cisalhamento, ``Anv``.
    """
    if not is_positive_finite(net_shear_area):
        raise ValueError(
            f"shear_rupture_resistance: net_shear_area deve ser finito e "
            f"positivo, recebido: {net_shear_area!r}"
        )
    if not is_positive_finite(fu):
        raise ValueError(
            f"shear_rupture_resistance: fu deve ser finito e positivo, recebido: {fu!r}"
        )
    if not is_positive_finite(gamma_a2):
        raise ValueError(
            f"shear_rupture_resistance: gamma_a2 deve ser finito e positivo, "
            f"recebido: {gamma_a2!r}"
        )
    return 0.60 * fu * net_shear_area / gamma_a2


def block_shear_resistance(
    gross_shear_area: float,
    net_shear_area: float,
    net_tension_area: float,
    fy: float,
    fu: float,
    cts: float,
    gamma_a2: float,
) -> float:
    """Força resistente de cálculo ao colapso por rasgamento ("block
    shear"), ``Fr,Rd`` (NBR 8800:2024, 6.5.6):

    ``Fr,Rd = min(0,60·fu·Anv + Cts·fu·Ant, 0,60·fy·Agv + Cts·fu·Ant)/γa2``.

    Note que AMBOS os termos (ruptura por cisalhamento + tração, e
    escoamento por cisalhamento + tração) são divididos pelo MESMO
    ``γa2`` — assim definido pela norma, não um erro de digitação desta
    implementação (o mecanismo combinado de colapso é tratado como um
    único estado-limite de ruptura, ainda que uma de suas parcelas seja
    "escoamento por cisalhamento").

    ``gross_shear_area``: área bruta sujeita a cisalhamento, ``Agv``.
    ``net_shear_area``: área líquida sujeita a cisalhamento, ``Anv``.
    ``net_tension_area``: área líquida sujeita à tração, ``Ant``.
    ``cts``: ``1,0`` quando a tensão de tração na área líquida for
    uniforme, ``0,5`` quando não for (Figura 16-b/c) — ver ATENÇÃO 4 no
    docstring do módulo.
    """
    if not is_positive_finite(gross_shear_area):
        raise ValueError(
            f"block_shear_resistance: gross_shear_area deve ser finito e "
            f"positivo, recebido: {gross_shear_area!r}"
        )
    if not is_positive_finite(net_shear_area):
        raise ValueError(
            f"block_shear_resistance: net_shear_area deve ser finito e "
            f"positivo, recebido: {net_shear_area!r}"
        )
    if not is_positive_finite(net_tension_area):
        raise ValueError(
            f"block_shear_resistance: net_tension_area deve ser finito e "
            f"positivo, recebido: {net_tension_area!r}"
        )
    if not is_positive_finite(fy):
        raise ValueError(f"block_shear_resistance: fy deve ser finito e positivo, recebido: {fy!r}")
    if not is_positive_finite(fu):
        raise ValueError(f"block_shear_resistance: fu deve ser finito e positivo, recebido: {fu!r}")
    if cts not in (0.5, 1.0):
        raise ValueError(f"block_shear_resistance: cts deve ser 0,5 ou 1,0, recebido: {cts!r}")
    if not is_positive_finite(gamma_a2):
        raise ValueError(
            f"block_shear_resistance: gamma_a2 deve ser finito e positivo, "
            f"recebido: {gamma_a2!r}"
        )
    rupture_term = 0.60 * fu * net_shear_area + cts * fu * net_tension_area
    yield_term = 0.60 * fy * gross_shear_area + cts * fu * net_tension_area
    return min(rupture_term, yield_term) / gamma_a2


@dataclass(frozen=True, slots=True)
class ConnectionElementCheckResult(CheckResult):
    """Resultado de uma verificação isolada (tração, compressão,
    cisalhamento OU colapso por rasgamento) de um elemento de ligação
    (NBR 8800:2024, 6.5.3 a 6.5.6)."""

    force_sd: float
    force_rd: float

    def __post_init__(self) -> None:
        if not is_positive_finite(self.force_sd):
            raise ValueError(f"force_sd deve ser finito e positivo, recebido: {self.force_sd!r}")
        if not is_positive_finite(self.force_rd):
            raise ValueError(f"force_rd deve ser finito e positivo, recebido: {self.force_rd!r}")

    @property
    def sd(self) -> float:
        return self.force_sd

    @property
    def rd(self) -> float:
        return self.force_rd


def check_connection_element_tension(
    nt_sd: float, gross_area: float, effective_net_area: float, fy: float, fu: float,
    gamma_a1: float, gamma_a2: float,
) -> ConnectionElementCheckResult:
    """Verifica um elemento de ligação tracionado (NBR 8800:2024,
    6.5.3): ``F_Rd = min(fy·Ag/γa1, fu·Ae/γa2)``.

    ``nt_sd``: força de tração solicitante de cálculo (N).
    ``effective_net_area``: ``Ae`` — ver ATENÇÃO 3 no docstring do
    módulo. Demais parâmetros: ver :func:`axial_yield_resistance`/
    :func:`tensile_rupture_resistance`.
    """
    if not is_positive_finite(nt_sd):
        raise ValueError(
            f"check_connection_element_tension: nt_sd deve ser finito e "
            f"positivo, recebido: {nt_sd!r}"
        )
    yield_rd = axial_yield_resistance(gross_area, fy, gamma_a1)
    rupture_rd = tensile_rupture_resistance(effective_net_area, fu, gamma_a2)
    return ConnectionElementCheckResult(force_sd=nt_sd, force_rd=min(yield_rd, rupture_rd))


def check_connection_element_compression(
    nc_sd: float,
    gross_area: float,
    fy: float,
    elastic_buckling_force: float,
    resistance_factors: SteelResistanceFactors,
) -> ConnectionElementCheckResult:
    """Verifica um elemento de ligação comprimido (NBR 8800:2024,
    6.5.4): ``F_Rd = min(fy·Ag/γa1, χ·Ag·fy/γa1)``, o segundo termo
    reaproveitado de 5.3
    (:func:`~estrutura_metalica.normative.nbr8800.compression.check_compression_member`)
    — ver ATENÇÃO 1/2 no docstring do módulo.

    ``nc_sd``: força de compressão solicitante de cálculo (N).
    ``elastic_buckling_force``: ``Ne`` — ver
    :func:`~estrutura_metalica.normative.nbr8800.compression.flexural_buckling_force`.
    ``resistance_factors``: ver
    :class:`~estrutura_metalica.normative.nbr8800.resistance_factors.SteelResistanceFactors`.
    """
    if not is_positive_finite(nc_sd):
        raise ValueError(
            f"check_connection_element_compression: nc_sd deve ser finito e "
            f"positivo, recebido: {nc_sd!r}"
        )
    yield_rd = axial_yield_resistance(gross_area, fy, resistance_factors.gamma_a1)
    buckling_result = check_compression_member(
        nc_sd=nc_sd,
        gross_area=gross_area,
        effective_area=gross_area,
        fy=fy,
        elastic_buckling_force=elastic_buckling_force,
        resistance_factors=resistance_factors,
    )
    return ConnectionElementCheckResult(
        force_sd=nc_sd, force_rd=min(yield_rd, buckling_result.nc_rd)
    )


def check_connection_element_shear(
    fv_sd: float, gross_area: float, net_shear_area: float, fy: float, fu: float,
    gamma_a1: float, gamma_a2: float,
) -> ConnectionElementCheckResult:
    """Verifica um elemento de ligação submetido a cisalhamento (NBR
    8800:2024, 6.5.5): ``F_Rd = min(0,60·fy·Ag/γa1, 0,60·fu·Anv/γa2)``.

    ``fv_sd``: força cortante solicitante de cálculo (N). Demais
    parâmetros: ver :func:`shear_yield_resistance`/
    :func:`shear_rupture_resistance`.
    """
    if not is_positive_finite(fv_sd):
        raise ValueError(
            f"check_connection_element_shear: fv_sd deve ser finito e "
            f"positivo, recebido: {fv_sd!r}"
        )
    yield_rd = shear_yield_resistance(gross_area, fy, gamma_a1)
    rupture_rd = shear_rupture_resistance(net_shear_area, fu, gamma_a2)
    return ConnectionElementCheckResult(force_sd=fv_sd, force_rd=min(yield_rd, rupture_rd))


def check_block_shear(
    fsd: float,
    gross_shear_area: float,
    net_shear_area: float,
    net_tension_area: float,
    fy: float,
    fu: float,
    cts: float,
    gamma_a2: float,
) -> ConnectionElementCheckResult:
    """Verifica o colapso por rasgamento ("block shear") de um elemento
    de ligação (NBR 8800:2024, 6.5.6).

    ``fsd``: força solicitante de cálculo no plano de rasgamento (N).
    Demais parâmetros: ver :func:`block_shear_resistance`.
    """
    if not is_positive_finite(fsd):
        raise ValueError(
            f"check_block_shear: fsd deve ser finito e positivo, recebido: {fsd!r}"
        )
    fr_rd = block_shear_resistance(
        gross_shear_area, net_shear_area, net_tension_area, fy, fu, cts, gamma_a2
    )
    return ConnectionElementCheckResult(force_sd=fsd, force_rd=fr_rd)
