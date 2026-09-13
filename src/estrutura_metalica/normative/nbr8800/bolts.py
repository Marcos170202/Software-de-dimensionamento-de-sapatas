"""Ligações parafusadas — parafusos e barras redondas rosqueadas.

Fonte: ABNT NBR 8800:2024, 6.3 "Parafusos e barras redondas
rosqueadas" (páginas 82-88). Fórmulas conferidas por leitura direta
(renderização visual) do PDF da norma — ver rastreabilidade completa
em ``docs/normative/NBR8800-RULES.md``.

Escopo desta fase: apenas parafusos comuns (ASTM A307) e de alta
resistência (ASTM F3125/F3125M, ISO 4016/898-1) em ligações por
CONTATO (pressão de contato/cisalhamento simples), sem protensão
crítica ao deslizamento. Cobre:

- 6.3.2.2 — área bruta (``Ab = 0,25π·db²``) e área efetiva para tração
  (``Abe = 0,75·Ab``);
- 6.3.3.1 — força de tração resistente de cálculo,
  ``Ft,Rd = Abe·fub/γa2``;
- 6.3.3.2 — força de cisalhamento resistente de cálculo, por plano de
  corte, ``Fv,Rd = 0,45·Ab·fub/γa2`` (plano de corte passando pela
  rosca, ou parafuso comum em qualquer situação) ou
  ``Fv,Rd = 0,56·Ab·fub/γa2`` (parafuso de alta resistência/barra
  rosqueada, plano de corte fora da rosca);
- 6.3.3.3-a — força resistente de cálculo à pressão de contato na
  parede de um furo PADRÃO (já considerando o rasgamento entre furos
  consecutivos ou entre um furo extremo e a borda), nas duas variantes
  (deformação no furo como limitação de projeto, ou não);
- 6.3.3.4 — equação de interação entre tração e cisalhamento
  combinados, ``(Ft,Sd/Ft,Rd)² + (Fv,Sd/Fv,Rd)² ≤ 1,0``.

**ATENÇÃO — LIMITAÇÕES DE SEGURANÇA**:

1. **Furos não padrão**: :func:`bolt_bearing_resistance` implementa
   apenas o caso 6.3.3.3-a) (furos padrão, alargados, pouco alongados
   em qualquer direção e muito alongados na direção da força — mesma
   fórmula para todos, mas o uso de furos alargados/alongados é
   restrito a ligações por atrito, 6.3.4, não implementadas — ver item
   3). O caso 6.3.3.3-b) (furos muito alongados na direção
   PERPENDICULAR à força, fator 1,0/2,0 em vez de 1,2-1,5/2,4-3,0) NÃO
   está implementado.
2. **Tampão rosca em barras redondas rosqueadas**: a força resistente
   de cálculo à tração de uma barra redonda rosqueada (exceto
   chumbadores, ver 6.7) não pode superar ``Ab·fy/γa1`` — ver
   :func:`threaded_rod_tensile_resistance_cap`, uma função separada e
   opcional que o chamador deve aplicar (tomando o mínimo com
   :func:`bolt_tensile_resistance`) apenas para barras rosqueadas, NÃO
   para parafusos comuns/de alta resistência (onde esse limite não se
   aplica). :func:`check_bolt_tension` NÃO aplica esse limite
   automaticamente.
3. **Ligações por atrito NÃO implementadas**: 6.3.4 (força resistente
   ao deslizamento, ``Ff,Rd``, que depende de protensão mínima
   ``FTb``/6.8.4.1, coeficiente de atrito ``μ``, fator ``Ce`` e
   ``γe``/Tabela 13) está inteiramente fora do escopo. As funções deste
   módulo cobrem apenas ligações por CONTATO (tração/cisalhamento/
   pressão de contato), nunca deslizamento como estado-limite.
4. **Requisitos construtivos não verificados**: espaçamento mínimo/
   máximo entre parafusos e distâncias mínimas/máximas a bordas (6.3.7,
   não lido nesta fase) NÃO são validados por nenhuma função aqui —
   ao contrário de :func:`~estrutura_metalica.normative.nbr8800.welds.check_fillet_weld_shear`,
   que valida o tamanho mínimo de solda (Tabela 11), não há validação
   equivalente de geometria de furos neste módulo.

Também NÃO implementado nesta fase (ver
``docs/normative/NBR8800-RULES.md`` para a lista completa): 6.3.1
(requisitos de montagem/aperto — remete a 6.8), 6.3.4 (ligações por
atrito, ver item 3 acima), 6.3.5 (parafusos tracionados com efeito de
alavanca), Tabela 12 (alternativa simplificada à equação de interação
de 6.3.3.4 — implementa-se apenas a equação, não a tabela), pinos
(6.4), elementos de ligação (6.5), pressão de contato de chapas
(6.6), bases de pilares (6.7), 6.8 (projeto/montagem/inspeção de
ligações com parafusos de alta resistência, inclusive ``FTb``).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ._check_result import CheckResult
from ._validation import is_non_negative_finite, is_positive_finite


def bolt_gross_area(bolt_diameter: float) -> float:
    """Área bruta de um parafuso ou barra redonda rosqueada, ``Ab``
    (NBR 8800:2024, 6.3.2.2): ``Ab = 0,25π·db²``.

    ``bolt_diameter``: diâmetro do parafuso ou da barra rosqueada,
    ``db`` (m).
    """
    if not is_positive_finite(bolt_diameter):
        raise ValueError(
            f"bolt_gross_area: bolt_diameter deve ser finito e positivo, "
            f"recebido: {bolt_diameter!r}"
        )
    return 0.25 * math.pi * bolt_diameter**2


def bolt_effective_area_tension(gross_area: float) -> float:
    """Área efetiva de um parafuso ou barra redonda rosqueada, para
    tração, ``Abe`` (NBR 8800:2024, 6.3.2.2): ``Abe = 0,75·Ab``.

    ``gross_area``: área bruta, ``Ab`` — ver :func:`bolt_gross_area`.
    """
    if not is_positive_finite(gross_area):
        raise ValueError(
            f"bolt_effective_area_tension: gross_area deve ser finito e "
            f"positivo, recebido: {gross_area!r}"
        )
    return 0.75 * gross_area


def bolt_tensile_resistance(effective_area: float, fub: float, gamma_a2: float) -> float:
    """Força de tração resistente de cálculo de um parafuso ou barra
    redonda rosqueada, ``Ft,Rd`` (NBR 8800:2024, 6.3.3.1):
    ``Ft,Rd = Abe·fub/γa2``.

    Não aplica o limite adicional de barras redondas rosqueadas (exceto
    chumbadores) — ver ATENÇÃO 2 no docstring do módulo e
    :func:`threaded_rod_tensile_resistance_cap`.

    ``effective_area``: ``Abe`` — ver :func:`bolt_effective_area_tension`.
    ``fub``: resistência à ruptura do material do parafuso ou barra
    redonda rosqueada (Anexo A, não incluído neste pacote). ``gamma_a2``:
    NBR 8800:2024, 4.9.2, Tabela 3 — ver
    :func:`~estrutura_metalica.normative.nbr8800.resistance_factors.steel_resistance_factors`.
    """
    if not is_positive_finite(effective_area):
        raise ValueError(
            f"bolt_tensile_resistance: effective_area deve ser finito e "
            f"positivo, recebido: {effective_area!r}"
        )
    if not is_positive_finite(fub):
        raise ValueError(
            f"bolt_tensile_resistance: fub deve ser finito e positivo, recebido: {fub!r}"
        )
    if not is_positive_finite(gamma_a2):
        raise ValueError(
            f"bolt_tensile_resistance: gamma_a2 deve ser finito e positivo, "
            f"recebido: {gamma_a2!r}"
        )
    return effective_area * fub / gamma_a2


def threaded_rod_tensile_resistance_cap(gross_area: float, fy: float, gamma_a1: float) -> float:
    """Limite superior da força de tração resistente de cálculo de uma
    barra redonda rosqueada, EXCETO chumbadores (NBR 8800:2024,
    6.3.3.1): ``Ab·fy/γa1``.

    Aplicável apenas a barras redondas rosqueadas (não a parafusos
    comuns ou de alta resistência, onde esse limite não existe) — ver
    ATENÇÃO 2 no docstring do módulo. O chamador deve tomar
    ``min(bolt_tensile_resistance(...), threaded_rod_tensile_resistance_cap(...))``
    quando aplicável; esta função NÃO é chamada automaticamente por
    :func:`check_bolt_tension`.

    ``gross_area``: ``Ab`` — ver :func:`bolt_gross_area`. ``fy``:
    resistência ao escoamento do aço da barra. ``gamma_a1``: NBR
    8800:2024, 4.9.2, Tabela 3.
    """
    if not is_positive_finite(gross_area):
        raise ValueError(
            f"threaded_rod_tensile_resistance_cap: gross_area deve ser finito "
            f"e positivo, recebido: {gross_area!r}"
        )
    if not is_positive_finite(fy):
        raise ValueError(
            f"threaded_rod_tensile_resistance_cap: fy deve ser finito e "
            f"positivo, recebido: {fy!r}"
        )
    if not is_positive_finite(gamma_a1):
        raise ValueError(
            f"threaded_rod_tensile_resistance_cap: gamma_a1 deve ser finito e "
            f"positivo, recebido: {gamma_a1!r}"
        )
    return gross_area * fy / gamma_a1


def bolt_shear_resistance(
    gross_area: float,
    fub: float,
    gamma_a2: float,
    *,
    threads_excluded_from_shear_plane: bool,
) -> float:
    """Força de cisalhamento resistente de cálculo de um parafuso ou
    barra redonda rosqueada, por plano de corte, ``Fv,Rd`` (NBR
    8800:2024, 6.3.3.2):

    - ``threads_excluded_from_shear_plane=False`` (6.3.3.2-a):
      ``Fv,Rd = 0,45·Ab·fub/γa2`` — parafusos de alta resistência/
      barras rosqueadas com o plano de corte passando pela rosca, OU
      parafusos comuns em QUALQUER situação (caso mais comum e mais
      conservador — usar por padrão sempre que houver dúvida);
    - ``threads_excluded_from_shear_plane=True`` (6.3.3.2-b):
      ``Fv,Rd = 0,56·Ab·fub/γa2`` — apenas parafusos de alta
      resistência ou barras rosqueadas cujo plano de corte considerado
      NÃO passa pela rosca.

    Não verifica a pressão de contato no furo (6.3.3.3, ver
    :func:`bolt_bearing_resistance`) — ambas devem ser atendidas
    simultaneamente, por exigência textual de 6.3.3.2 e 6.3.3.3.

    ``gross_area``: ``Ab`` — ver :func:`bolt_gross_area`. ``fub``/
    ``gamma_a2``: ver :func:`bolt_tensile_resistance`.
    """
    if not is_positive_finite(gross_area):
        raise ValueError(
            f"bolt_shear_resistance: gross_area deve ser finito e positivo, "
            f"recebido: {gross_area!r}"
        )
    if not is_positive_finite(fub):
        raise ValueError(
            f"bolt_shear_resistance: fub deve ser finito e positivo, recebido: {fub!r}"
        )
    if not is_positive_finite(gamma_a2):
        raise ValueError(
            f"bolt_shear_resistance: gamma_a2 deve ser finito e positivo, "
            f"recebido: {gamma_a2!r}"
        )
    factor = 0.56 if threads_excluded_from_shear_plane else 0.45
    return factor * gross_area * fub / gamma_a2


def bolt_bearing_resistance(
    edge_or_hole_distance: float,
    thickness: float,
    fu: float,
    bolt_diameter: float,
    gamma_a2: float,
    *,
    deformation_is_design_limit: bool,
) -> float:
    """Força resistente de cálculo à pressão de contato na parede de
    um furo PADRÃO, já considerando o rasgamento entre furos
    consecutivos ou entre um furo extremo e a borda, por parafuso (NBR
    8800:2024, 6.3.3.3-a):

    - ``deformation_is_design_limit=True``:
      ``Fc,Rd = min(1,2·ℓf·t·fu/γa2, 2,4·db·t·fu/γa2)``;
    - ``deformation_is_design_limit=False``:
      ``Fc,Rd = min(1,5·ℓf·t·fu/γa2, 3,0·db·t·fu/γa2)``.

    Cobre apenas furos padrão (ver ATENÇÃO 1 no docstring do módulo —
    o caso b) de furos muito alongados perpendicularmente à força NÃO
    está implementado). A força resistente TOTAL de uma ligação é a
    soma das forças resistentes calculadas para todos os furos —
    responsabilidade do chamador, não desta função (que calcula por
    furo).

    ``edge_or_hole_distance``: distância, na direção da força, entre a
    borda do furo e a borda do furo adjacente ou a borda livre, ``ℓf``
    (m). ``thickness``: espessura da parte ligada, ``t`` (m). ``fu``:
    resistência à ruptura do aço da parede do furo (não do parafuso).
    ``bolt_diameter``: ``db`` (m). ``gamma_a2``: ver
    :func:`bolt_tensile_resistance`.
    """
    if not is_positive_finite(edge_or_hole_distance):
        raise ValueError(
            f"bolt_bearing_resistance: edge_or_hole_distance deve ser finito "
            f"e positivo, recebido: {edge_or_hole_distance!r}"
        )
    if not is_positive_finite(thickness):
        raise ValueError(
            f"bolt_bearing_resistance: thickness deve ser finito e positivo, "
            f"recebido: {thickness!r}"
        )
    if not is_positive_finite(fu):
        raise ValueError(
            f"bolt_bearing_resistance: fu deve ser finito e positivo, recebido: {fu!r}"
        )
    if not is_positive_finite(bolt_diameter):
        raise ValueError(
            f"bolt_bearing_resistance: bolt_diameter deve ser finito e "
            f"positivo, recebido: {bolt_diameter!r}"
        )
    if not is_positive_finite(gamma_a2):
        raise ValueError(
            f"bolt_bearing_resistance: gamma_a2 deve ser finito e positivo, "
            f"recebido: {gamma_a2!r}"
        )
    edge_factor, diameter_factor = (1.2, 2.4) if deformation_is_design_limit else (1.5, 3.0)
    edge_term = edge_factor * edge_or_hole_distance * thickness * fu / gamma_a2
    diameter_term = diameter_factor * bolt_diameter * thickness * fu / gamma_a2
    return min(edge_term, diameter_term)


@dataclass(frozen=True, slots=True)
class BoltCheckResult(CheckResult):
    """Resultado de uma verificação isolada (tração, cisalhamento OU
    pressão de contato) de um parafuso ou barra redonda rosqueada (NBR
    8800:2024, 6.3.3.1/6.3.3.2/6.3.3.3).

    ``force_sd``/``force_rd``: força solicitante/resistente de cálculo
    (N), do tipo correspondente à verificação (tração, cisalhamento ou
    pressão de contato — ver :func:`check_bolt_tension`,
    :func:`check_bolt_shear`, :func:`check_bolt_bearing`).
    """

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


def check_bolt_tension(
    ft_sd: float, bolt_diameter: float, fub: float, gamma_a2: float
) -> BoltCheckResult:
    """Verifica um parafuso ou barra redonda rosqueada à tração (NBR
    8800:2024, 6.3.3.1).

    **Não aplica** o limite adicional de barras redondas rosqueadas
    (``Ab·fy/γa1``) — ver ATENÇÃO 2 no docstring do módulo e
    :func:`threaded_rod_tensile_resistance_cap`.

    ``ft_sd``: força de tração solicitante de cálculo por parafuso ou
    barra rosqueada (N). ``bolt_diameter``/``fub``/``gamma_a2``: ver
    :func:`bolt_tensile_resistance`.
    """
    if not is_positive_finite(ft_sd):
        raise ValueError(
            f"check_bolt_tension: ft_sd deve ser finito e positivo, recebido: {ft_sd!r}"
        )
    gross_area = bolt_gross_area(bolt_diameter)
    effective_area = bolt_effective_area_tension(gross_area)
    ft_rd = bolt_tensile_resistance(effective_area, fub, gamma_a2)
    return BoltCheckResult(force_sd=ft_sd, force_rd=ft_rd)


def check_bolt_shear(
    fv_sd: float,
    bolt_diameter: float,
    fub: float,
    gamma_a2: float,
    *,
    threads_excluded_from_shear_plane: bool,
) -> BoltCheckResult:
    """Verifica um parafuso ou barra redonda rosqueada ao cisalhamento,
    por plano de corte (NBR 8800:2024, 6.3.3.2).

    ``fv_sd``: força de cisalhamento solicitante de cálculo no plano
    considerado (N). ``bolt_diameter``/``fub``/``gamma_a2``/
    ``threads_excluded_from_shear_plane``: ver
    :func:`bolt_shear_resistance`.
    """
    if not is_positive_finite(fv_sd):
        raise ValueError(
            f"check_bolt_shear: fv_sd deve ser finito e positivo, recebido: {fv_sd!r}"
        )
    gross_area = bolt_gross_area(bolt_diameter)
    fv_rd = bolt_shear_resistance(
        gross_area,
        fub,
        gamma_a2,
        threads_excluded_from_shear_plane=threads_excluded_from_shear_plane,
    )
    return BoltCheckResult(force_sd=fv_sd, force_rd=fv_rd)


def check_bolt_bearing(
    fc_sd: float,
    edge_or_hole_distance: float,
    thickness: float,
    fu: float,
    bolt_diameter: float,
    gamma_a2: float,
    *,
    deformation_is_design_limit: bool,
) -> BoltCheckResult:
    """Verifica a pressão de contato na parede de um furo padrão, por
    parafuso (NBR 8800:2024, 6.3.3.3-a).

    ``fc_sd``: força solicitante de cálculo transmitida pelo parafuso
    ao furo considerado (N). ``edge_or_hole_distance``/``thickness``/
    ``fu``/``bolt_diameter``/``gamma_a2``/``deformation_is_design_limit``:
    ver :func:`bolt_bearing_resistance`.
    """
    if not is_positive_finite(fc_sd):
        raise ValueError(
            f"check_bolt_bearing: fc_sd deve ser finito e positivo, recebido: {fc_sd!r}"
        )
    fc_rd = bolt_bearing_resistance(
        edge_or_hole_distance,
        thickness,
        fu,
        bolt_diameter,
        gamma_a2,
        deformation_is_design_limit=deformation_is_design_limit,
    )
    return BoltCheckResult(force_sd=fc_sd, force_rd=fc_rd)


def bolt_combined_tension_and_shear_ratio(
    ft_sd: float, ft_rd: float, fv_sd: float, fv_rd: float
) -> float:
    """Razão de interação entre tração e cisalhamento combinados em um
    parafuso ou barra redonda rosqueada (NBR 8800:2024, 6.3.3.4):

    ``(Ft,Sd/Ft,Rd)² + (Fv,Sd/Fv,Rd)²``.

    A condição de 6.3.3.4 é atendida se o valor retornado for
    ``<= 1,0`` — ver :func:`check_bolt_combined_tension_and_shear`.

    ``ft_sd``: força de tração solicitante de cálculo por parafuso ou
    barra rosqueada (N), podendo ser zero. ``ft_rd``: força de tração
    resistente de cálculo correspondente — ver
    :func:`bolt_tensile_resistance`. ``fv_sd``: força de cisalhamento
    solicitante de cálculo no plano considerado (N), podendo ser zero.
    ``fv_rd``: força de cisalhamento resistente de cálculo
    correspondente — ver :func:`bolt_shear_resistance`.
    """
    if not is_non_negative_finite(ft_sd):
        raise ValueError(
            f"bolt_combined_tension_and_shear_ratio: ft_sd deve ser finito e "
            f"não-negativo, recebido: {ft_sd!r}"
        )
    if not is_positive_finite(ft_rd):
        raise ValueError(
            f"bolt_combined_tension_and_shear_ratio: ft_rd deve ser finito e "
            f"positivo, recebido: {ft_rd!r}"
        )
    if not is_non_negative_finite(fv_sd):
        raise ValueError(
            f"bolt_combined_tension_and_shear_ratio: fv_sd deve ser finito e "
            f"não-negativo, recebido: {fv_sd!r}"
        )
    if not is_positive_finite(fv_rd):
        raise ValueError(
            f"bolt_combined_tension_and_shear_ratio: fv_rd deve ser finito e "
            f"positivo, recebido: {fv_rd!r}"
        )
    return (ft_sd / ft_rd) ** 2 + (fv_sd / fv_rd) ** 2


@dataclass(frozen=True, slots=True)
class BoltCombinedCheckResult(CheckResult):
    """Resultado da verificação à interação entre tração e
    cisalhamento combinados de um parafuso ou barra redonda rosqueada
    (NBR 8800:2024, 6.3.3.4).

    ``interaction_ratio``: valor da equação de interação — a condição
    normativa é atendida se ``interaction_ratio <= 1,0`` (``is_ok``).
    """

    ft_sd: float
    ft_rd: float
    fv_sd: float
    fv_rd: float
    interaction_ratio: float

    def __post_init__(self) -> None:
        if not is_non_negative_finite(self.ft_sd):
            raise ValueError(f"ft_sd deve ser finito e não-negativo, recebido: {self.ft_sd!r}")
        if not is_positive_finite(self.ft_rd):
            raise ValueError(f"ft_rd deve ser finito e positivo, recebido: {self.ft_rd!r}")
        if not is_non_negative_finite(self.fv_sd):
            raise ValueError(f"fv_sd deve ser finito e não-negativo, recebido: {self.fv_sd!r}")
        if not is_positive_finite(self.fv_rd):
            raise ValueError(f"fv_rd deve ser finito e positivo, recebido: {self.fv_rd!r}")
        if not math.isfinite(self.interaction_ratio) or self.interaction_ratio < 0:
            raise ValueError(
                f"interaction_ratio deve ser finito e não-negativo, "
                f"recebido: {self.interaction_ratio!r}"
            )

    @property
    def sd(self) -> float:
        """Alias genérico — o próprio ``interaction_ratio`` (ver :class:`CheckResult`)."""
        return self.interaction_ratio

    @property
    def rd(self) -> float:
        """Alias genérico — sempre ``1,0`` (o limite da equação de interação)."""
        return 1.0


def check_bolt_combined_tension_and_shear(
    ft_sd: float, ft_rd: float, fv_sd: float, fv_rd: float
) -> BoltCombinedCheckResult:
    """Verifica a interação entre tração e cisalhamento combinados em
    um parafuso ou barra redonda rosqueada (NBR 8800:2024, 6.3.3.4).

    Ver :func:`bolt_combined_tension_and_shear_ratio` para a fórmula.
    Alternativa NÃO implementada: a Tabela 12 (limitação simplificada
    de ``Ft,Sd`` por tipo de parafuso, em vez da equação de interação —
    ver ATENÇÃO no docstring do módulo).
    """
    ratio = bolt_combined_tension_and_shear_ratio(ft_sd, ft_rd, fv_sd, fv_rd)
    return BoltCombinedCheckResult(
        ft_sd=ft_sd, ft_rd=ft_rd, fv_sd=fv_sd, fv_rd=fv_rd, interaction_ratio=ratio
    )
