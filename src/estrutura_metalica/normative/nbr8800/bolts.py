"""Ligações parafusadas — parafusos e barras redondas rosqueadas.

Fonte: ABNT NBR 8800:2024, 6.3 "Parafusos e barras redondas
rosqueadas" (páginas 82-88) e 6.8.4.1/Tabela 19 (página 110-111, força
de protensão mínima). Fórmulas conferidas por leitura direta
(renderização visual) do PDF da norma — ver rastreabilidade completa
em ``docs/normative/NBR8800-RULES.md``.

Escopo desta fase: parafusos comuns (ASTM A307) e de alta resistência
(ASTM F3125/F3125M, ISO 4016/898-1) em ligações por CONTATO (pressão
de contato/cisalhamento simples) E em ligações por ATRITO com
parafusos de alta resistência protendidos. Cobre:

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
  combinados, ``(Ft,Sd/Ft,Rd)² + (Fv,Sd/Fv,Rd)² ≤ 1,0``;
- 6.3.4 — ligações por atrito com parafusos de alta resistência: força
  resistente ao deslizamento no ESTADO-LIMITE ÚLTIMO (6.3.4.3,
  ``Ff,Rd``, furos alargados/alongados) e no ESTADO-LIMITE DE SERVIÇO
  (6.3.4.4, ``Ff,Rk``, furos padrão/pouco alongados transversais), com
  o coeficiente de atrito ``μ`` (6.3.4.1), o fator ``Ce`` de chapas de
  enchimento, ``γe`` (Tabela 13) e a força de protensão mínima ``FTb``
  (Tabela 19, 6.8.4.1);
- 6.5.7.2-a — fator de redução da força resistente dos parafusos ao
  cisalhamento/esmagamento por chapas de enchimento espessas em
  ligações por contato (``ts`` entre 6,3 mm e 19 mm).

**ATENÇÃO — LIMITAÇÕES DE SEGURANÇA**:

1. **Furos não padrão**: :func:`bolt_bearing_resistance` implementa
   apenas o caso 6.3.3.3-a) (furos padrão, alargados, pouco alongados
   em qualquer direção e muito alongados na direção da força — mesma
   fórmula para todos). O caso 6.3.3.3-b) (furos muito alongados na
   direção PERPENDICULAR à força, fator 1,0/2,0 em vez de
   1,2-1,5/2,4-3,0) NÃO está implementado.
2. **Tampão rosca em barras redondas rosqueadas**: a força resistente
   de cálculo à tração de uma barra redonda rosqueada (exceto
   chumbadores, ver 6.7) não pode superar ``Ab·fy/γa1`` — ver
   :func:`threaded_rod_tensile_resistance_cap`, uma função separada e
   opcional que o chamador deve aplicar (tomando o mínimo com
   :func:`bolt_tensile_resistance`) apenas para barras rosqueadas, NÃO
   para parafusos comuns/de alta resistência (onde esse limite não se
   aplica). :func:`check_bolt_tension` NÃO aplica esse limite
   automaticamente.
3. **Ligações por atrito são um requisito ADICIONAL, não substituto**:
   6.3.4.1 exige que uma ligação por atrito atenda a 6.3.4.3 OU 6.3.4.4
   (o que for aplicável, ver 6.3.4.2) "e ainda atenda a 6.3.3" —
   :func:`check_slip_resistance_ultimate`/:func:`check_slip_resistance_service`
   verificam APENAS o deslizamento; o cisalhamento (6.3.3.2) e a
   pressão de contato (6.3.3.3) de uma ligação por atrito devem SEMPRE
   ser verificados também, com :func:`check_bolt_shear`/
   :func:`check_bolt_bearing` — considerando o estado-limite último em
   que a ligação eventualmente desliza e passa a trabalhar por contato.
4. **``FTb`` — apenas parafusos ASTM tabelados**: :func:`minimum_bolt_pretension_force`
   implementa a Tabela 19 (parafusos ASTM F3125/F3125M, graus A325/
   F1852 e A490/F2280) como tabela de consulta EXATA por diâmetro
   nominal — não interpola nem cobre parafusos ISO 4016/898-1 ou
   diâmetros fora da Tabela 19 (levanta ``ValueError``).
5. **Requisitos construtivos não verificados**: pega longa (6.3.7),
   ligações de grande comprimento (6.3.8), espaçamento mínimo/máximo
   entre furos (6.3.9/6.3.10) e distâncias mínima/máxima a bordas
   (6.3.11/6.3.12) NÃO são validados por nenhuma função aqui — ao
   contrário de :func:`~estrutura_metalica.normative.nbr8800.welds.check_fillet_weld_shear`,
   que valida o tamanho mínimo de solda (Tabela 11), não há validação
   equivalente de geometria de furos neste módulo. Os requisitos de
   acabamento de superfície (Figura 13, região mínima sem pintura) e os
   métodos de aperto/inspeção (6.8.4.2 a 6.8.4.7 — rotação da porca,
   chave calibrada, indicador direto de tração, Tabela 20) também NÃO
   são verificados — são procedimentos de execução/inspeção em obra,
   não cálculo.
6. **6.5.7.2-a — apenas furos padrão, ``ts`` até 19 mm**:
   :func:`filler_plate_thickness_reduction_factor` NÃO é aplicado
   automaticamente por :func:`check_bolt_shear`/:func:`check_bolt_bearing`
   — o chamador deve multiplicar o resultado dessas funções pelo fator,
   quando houver chapas de enchimento. Os itens 6.5.7.2-b)/-c)
   (alternativas geométricas para ``ts>19`` mm) NÃO estão implementados.

Também NÃO implementado nesta fase (ver
``docs/normative/NBR8800-RULES.md`` para a lista completa): 6.3.1
(requisitos de montagem/aperto — remete a 6.8), 6.3.5 (parafusos
tracionados com efeito de alavanca, "prying"), Tabela 12 (alternativa
simplificada à equação de interação de 6.3.3.4 — implementa-se apenas
a equação, não a tabela), 6.5.7.1 (requisito construtivo de soldagem de
chapas de enchimento) e 6.5.7.2-b)/-c) (ver item 6 acima), pressão de
contato de chapas (6.6), bases de pilares (6.7), 6.8 (demais itens —
arruelas, métodos de aperto/inspeção, ver item 5 acima). Pinos (6.4) e
elementos de ligação (6.5.3 a 6.5.6) estão em módulos separados — ver
``pins.py``/``connection_elements.py``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from ._check_result import CheckResult
from ._validation import is_non_negative_finite, is_positive_finite
from .resistance_factors import LoadCombinationClass


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


# --- Ligações por atrito (6.3.4) ---------------------------------------


class FrictionSurfaceClass(Enum):
    """Classe de tratamento de superfície de contato em uma ligação por
    atrito (NBR 8800:2024, 6.3.4.1) — determina o coeficiente de atrito
    médio ``μ`` (ver :func:`friction_coefficient`).

    ``LAMINADA_OU_GALVANIZADA_COM_ESCOVA`` reúne as classes A e C do
    texto da norma (superfícies laminadas limpas sem pintura, isentas
    de óleos/graxas; OU superfícies galvanizadas a quente com
    rugosidade aumentada manualmente por escova de aço) — ambas têm o
    MESMO ``μ=0,30`` (6.3.4.1-a). ``JATEADA`` é a classe B (superfícies
    jateadas sem pintura, ``μ=0,50``). ``GALVANIZADA_LISA`` é o caso
    (sem letra de classe no texto) de superfície galvanizada a quente
    SEM tratamento de rugosidade (``μ=0,20``).
    """

    LAMINADA_OU_GALVANIZADA_COM_ESCOVA = "laminada_ou_galvanizada_com_escova"
    JATEADA = "jateada"
    GALVANIZADA_LISA = "galvanizada_lisa"


#: NBR 8800:2024, 6.3.4.1 (RULE-ID NBR8800-CONN-009 — ver
#: docs/normative/NBR8800-RULES.md): coeficiente de atrito médio ``μ``
#: por classe de superfície.
_MU_SUPERFICIE: dict[FrictionSurfaceClass, float] = {
    FrictionSurfaceClass.LAMINADA_OU_GALVANIZADA_COM_ESCOVA: 0.30,
    FrictionSurfaceClass.JATEADA: 0.50,
    FrictionSurfaceClass.GALVANIZADA_LISA: 0.20,
}


def friction_coefficient(surface_class: FrictionSurfaceClass) -> float:
    """Coeficiente de atrito médio, ``μ`` (NBR 8800:2024, 6.3.4.1),
    para a classe de superfície de contato dada — ver
    :class:`FrictionSurfaceClass`.

    A norma permite ainda estabelecer outros valores de ``μ`` com base
    em ensaios conforme os requisitos do RCSC — NÃO coberto por esta
    função (que implementa apenas os três valores tabelados no texto).
    """
    return _MU_SUPERFICIE[surface_class]


def filler_plate_factor(has_two_or_more_filler_plates: bool) -> float:
    """Fator relacionado a chapas de enchimento, ``Ce`` (NBR 8800:2024,
    6.3.4.1): ``0,85`` quando houver DUAS OU MAIS chapas de enchimento
    entre as partes conectadas, ``1,0`` nos demais casos (nenhuma
    chapa, ou apenas uma).
    """
    return 0.85 if has_two_or_more_filler_plates else 1.0


class SlipCriticalHoleType(Enum):
    """Tipo de furo em uma ligação por atrito de estado-limite ÚLTIMO
    (NBR 8800:2024, 6.3.4.2/6.3.4.3) — determina ``γe`` (Tabela 13, ver
    :func:`slip_resistance_factor`). Aplicável apenas quando o
    deslizamento é considerado estado-limite ÚLTIMO (furos alargados,
    ou pouco alongados com alongamento PARALELO à força, ou muito
    alongados em qualquer direção) — furos padrão e furos pouco
    alongados com alongamento TRANSVERSAL usam
    :func:`slip_resistance_service` (estado-limite de SERVIÇO), sem
    ``γe``.
    """

    ALARGADO_OU_POUCO_ALONGADO_PARALELO = "alargado_ou_pouco_alongado_paralelo"
    MUITO_ALONGADO_QUALQUER_DIRECAO = "muito_alongado_qualquer_direcao"


#: NBR 8800:2024, Tabela 13 (página 87, RULE-ID NBR8800-CONN-010 — ver
#: docs/normative/NBR8800-RULES.md): coeficiente de ponderação da
#: resistência ``γe`` ao deslizamento, estado-limite último.
_TABELA_13_GAMMA_E: dict[tuple[LoadCombinationClass, SlipCriticalHoleType], float] = {
    (
        LoadCombinationClass.NORMAL,
        SlipCriticalHoleType.ALARGADO_OU_POUCO_ALONGADO_PARALELO,
    ): 1.20,
    (
        LoadCombinationClass.ESPECIAL_OU_CONSTRUCAO,
        SlipCriticalHoleType.ALARGADO_OU_POUCO_ALONGADO_PARALELO,
    ): 1.20,
    (
        LoadCombinationClass.EXCEPCIONAL,
        SlipCriticalHoleType.ALARGADO_OU_POUCO_ALONGADO_PARALELO,
    ): 1.00,
    (
        LoadCombinationClass.NORMAL,
        SlipCriticalHoleType.MUITO_ALONGADO_QUALQUER_DIRECAO,
    ): 1.40,
    (
        LoadCombinationClass.ESPECIAL_OU_CONSTRUCAO,
        SlipCriticalHoleType.MUITO_ALONGADO_QUALQUER_DIRECAO,
    ): 1.40,
    (
        LoadCombinationClass.EXCEPCIONAL,
        SlipCriticalHoleType.MUITO_ALONGADO_QUALQUER_DIRECAO,
    ): 1.15,
}


def slip_resistance_factor(
    combination_class: LoadCombinationClass, hole_type: SlipCriticalHoleType
) -> float:
    """Coeficiente de ponderação da resistência ao deslizamento no
    estado-limite último, ``γe`` (NBR 8800:2024, Tabela 13), conforme a
    classe de combinação e o tipo de furo — ver
    :class:`SlipCriticalHoleType`.
    """
    return _TABELA_13_GAMMA_E[(combination_class, hole_type)]


class HighStrengthBoltGrade(Enum):
    """Grau do parafuso de alta resistência ASTM F3125/F3125M, para
    fins da força de protensão mínima (Tabela 19) — ver
    :func:`minimum_bolt_pretension_force`."""

    A325_OU_F1852 = "a325_ou_f1852"
    A490_OU_F2280 = "a490_ou_f2280"


#: NBR 8800:2024, Tabela 19 (página 111, RULE-ID NBR8800-CONN-011 — ver
#: docs/normative/NBR8800-RULES.md): força de protensão mínima ``FTb``
#: (N) em parafusos ASTM F3125/F3125M, por diâmetro nominal (m) —
#: trios ``(diâmetro, FTb grau A325/F1852, FTb grau A490/F2280)``, em
#: ordem crescente de diâmetro. Diâmetros em polegada convertidos
#: exatamente (1 pol. = 25,4 mm); diâmetros métricos (16/20/22/24/27/
#: 30/35/36 mm) são parafusos distintos dos equivalentes em polegada
#: mais próximos (valores de ``FTb`` diferentes, exceto 1 3/8 pol./35mm
#: — mesmo valor tabelado, coincidência de arredondamento da norma).
_TABELA_19_FTB: tuple[tuple[float, float, float], ...] = (
    (0.0127, 53_000.0, 67_000.0),  # 1/2"
    (0.015875, 85_000.0, 106_000.0),  # 5/8"
    (0.016, 91_000.0, 114_000.0),  # 16 mm
    (0.01905, 125_000.0, 157_000.0),  # 3/4"
    (0.020, 142_000.0, 178_000.0),  # 20 mm
    (0.022, 176_000.0, 221_000.0),  # 22 mm
    (0.022225, 173_000.0, 217_000.0),  # 7/8"
    (0.024, 205_000.0, 257_000.0),  # 24 mm
    (0.0254, 227_000.0, 285_000.0),  # 1"
    (0.027, 267_000.0, 334_000.0),  # 27 mm
    (0.028575, 286_000.0, 358_000.0),  # 1 1/8"
    (0.030, 326_000.0, 408_000.0),  # 30 mm
    (0.03175, 363_000.0, 455_000.0),  # 1 1/4"
    (0.034925, 433_000.0, 542_000.0),  # 1 3/8"
    (0.035, 433_000.0, 542_000.0),  # 35 mm
    (0.036, 475_000.0, 595_000.0),  # 36 mm
    (0.0381, 527_000.0, 660_000.0),  # 1 1/2"
)
_TABELA_19_TOLERANCIA_DIAMETRO_M = 0.00005  # 0,05 mm


def minimum_bolt_pretension_force(bolt_diameter: float, grade: HighStrengthBoltGrade) -> float:
    """Força de protensão mínima por parafuso, ``FTb`` (NBR 8800:2024,
    6.8.4.1, Tabela 19), para um parafuso ASTM F3125/F3125M do
    diâmetro e grau dados.

    Consulta EXATA (tolerância de 0,05 mm) — NÃO interpola entre
    diâmetros tabelados e levanta ``ValueError`` se ``bolt_diameter``
    não corresponder a nenhum diâmetro da Tabela 19. Não cobre
    parafusos ISO 4016/898-1 (a norma não tabela ``FTb`` para eles).

    ``bolt_diameter``: diâmetro nominal do parafuso, ``db`` (m).
    ``grade``: ver :class:`HighStrengthBoltGrade`.
    """
    if not is_positive_finite(bolt_diameter):
        raise ValueError(
            f"minimum_bolt_pretension_force: bolt_diameter deve ser finito e "
            f"positivo, recebido: {bolt_diameter!r}"
        )
    for diameter_m, ftb_a325, ftb_a490 in _TABELA_19_FTB:
        if abs(bolt_diameter - diameter_m) <= _TABELA_19_TOLERANCIA_DIAMETRO_M:
            return ftb_a325 if grade is HighStrengthBoltGrade.A325_OU_F1852 else ftb_a490
    raise ValueError(
        f"minimum_bolt_pretension_force: bolt_diameter ({bolt_diameter!r}) não "
        f"corresponde a nenhum diâmetro tabelado na Tabela 19"
    )


def slip_resistance_ultimate(
    mu: float,
    ce: float,
    ftb: float,
    num_slip_planes: float,
    ft_sd: float,
    gamma_e: float,
) -> float:
    """Força resistente de cálculo ao deslizamento de um parafuso de
    alta resistência protendido, estado-limite ÚLTIMO, ``Ff,Rd`` (NBR
    8800:2024, 6.3.4.3): aplicável quando o deslizamento é considerado
    estado-limite último (ver 6.3.4.2 e :class:`SlipCriticalHoleType`).

    ``Ff,Rd = (1,13·μ·Ce·FTb·ns/γe)·(1 - Ft,Sd/(1,13·FTb))``.

    Exige que 6.3.3 (cisalhamento/pressão de contato) seja TAMBÉM
    verificado — ver ATENÇÃO 3 no docstring do módulo.

    ``mu``: coeficiente de atrito médio — ver :func:`friction_coefficient`.
    ``ce``: fator de chapas de enchimento — ver :func:`filler_plate_factor`.
    ``ftb``: força de protensão mínima por parafuso — ver
    :func:`minimum_bolt_pretension_force`. ``num_slip_planes``: número
    de planos de deslizamento, ``ns`` (tipicamente 1 ou 2). ``ft_sd``:
    força de tração solicitante de cálculo no parafuso que reduz a
    protensão, calculada com as combinações últimas de ações (N),
    podendo ser zero. ``gamma_e``: NBR 8800:2024, Tabela 13 — ver
    :func:`slip_resistance_factor`.
    """
    if not is_positive_finite(mu):
        raise ValueError(
            f"slip_resistance_ultimate: mu deve ser finito e positivo, recebido: {mu!r}"
        )
    if not is_positive_finite(ce):
        raise ValueError(
            f"slip_resistance_ultimate: ce deve ser finito e positivo, recebido: {ce!r}"
        )
    if not is_positive_finite(ftb):
        raise ValueError(
            f"slip_resistance_ultimate: ftb deve ser finito e positivo, recebido: {ftb!r}"
        )
    if not is_positive_finite(num_slip_planes):
        raise ValueError(
            f"slip_resistance_ultimate: num_slip_planes deve ser finito e "
            f"positivo, recebido: {num_slip_planes!r}"
        )
    if not is_non_negative_finite(ft_sd):
        raise ValueError(
            f"slip_resistance_ultimate: ft_sd deve ser finito e não-negativo, "
            f"recebido: {ft_sd!r}"
        )
    if not is_positive_finite(gamma_e):
        raise ValueError(
            f"slip_resistance_ultimate: gamma_e deve ser finito e positivo, "
            f"recebido: {gamma_e!r}"
        )
    if ft_sd >= 1.13 * ftb:
        raise ValueError(
            f"slip_resistance_ultimate: ft_sd ({ft_sd!r}) deve ser menor que "
            f"1,13·ftb ({1.13 * ftb!r}) — protensão totalmente anulada pela tração"
        )
    return (1.13 * mu * ce * ftb * num_slip_planes / gamma_e) * (1.0 - ft_sd / (1.13 * ftb))


def slip_resistance_service(
    mu: float,
    ce: float,
    ftb: float,
    num_slip_planes: float,
    ft_sk: float,
) -> float:
    """Força resistente nominal ao deslizamento de um parafuso de alta
    resistência protendido, estado-limite de SERVIÇO, ``Ff,Rk`` (NBR
    8800:2024, 6.3.4.4): aplicável quando o deslizamento é considerado
    estado-limite de SERVIÇO (furos padrão, ou pouco alongados com
    alongamento TRANSVERSAL — ver 6.3.4.2).

    ``Ff,Rk = 0,80·μ·Ce·FTb·ns·(1 - Ft,Sk/(0,80·FTb))``.

    Comparar com a força cortante solicitante CARACTERÍSTICA (raras de
    serviço, 4.8.7.3.4) — ou, simplificadamente, 70 % da força cortante
    solicitante de cálculo das combinações últimas normais (mesma
    simplificação vale para ``ft_sk``, conforme o texto da norma).
    Exige que 6.3.3 seja TAMBÉM verificado — ver ATENÇÃO 3 no docstring
    do módulo.

    ``mu``/``ce``/``ftb``/``num_slip_planes``: ver
    :func:`slip_resistance_ultimate`. ``ft_sk``: força de tração
    solicitante CARACTERÍSTICA no parafuso que reduz a protensão (N),
    podendo ser zero.
    """
    if not is_positive_finite(mu):
        raise ValueError(
            f"slip_resistance_service: mu deve ser finito e positivo, recebido: {mu!r}"
        )
    if not is_positive_finite(ce):
        raise ValueError(
            f"slip_resistance_service: ce deve ser finito e positivo, recebido: {ce!r}"
        )
    if not is_positive_finite(ftb):
        raise ValueError(
            f"slip_resistance_service: ftb deve ser finito e positivo, recebido: {ftb!r}"
        )
    if not is_positive_finite(num_slip_planes):
        raise ValueError(
            f"slip_resistance_service: num_slip_planes deve ser finito e "
            f"positivo, recebido: {num_slip_planes!r}"
        )
    if not is_non_negative_finite(ft_sk):
        raise ValueError(
            f"slip_resistance_service: ft_sk deve ser finito e não-negativo, "
            f"recebido: {ft_sk!r}"
        )
    if ft_sk >= 0.80 * ftb:
        raise ValueError(
            f"slip_resistance_service: ft_sk ({ft_sk!r}) deve ser menor que "
            f"0,80·ftb ({0.80 * ftb!r}) — protensão totalmente anulada pela tração"
        )
    return 0.80 * mu * ce * ftb * num_slip_planes * (1.0 - ft_sk / (0.80 * ftb))


def check_slip_resistance_ultimate(
    fv_sd: float,
    mu: float,
    ce: float,
    ftb: float,
    num_slip_planes: float,
    ft_sd: float,
    gamma_e: float,
) -> BoltCheckResult:
    """Verifica um parafuso de alta resistência protendido ao
    deslizamento, estado-limite ÚLTIMO (NBR 8800:2024, 6.3.4.3).

    Verifica APENAS o deslizamento — ver ATENÇÃO 3 no docstring do
    módulo: 6.3.3 (cisalhamento/pressão de contato) deve SEMPRE ser
    verificado adicionalmente, com :func:`check_bolt_shear`/
    :func:`check_bolt_bearing`.

    ``fv_sd``: força cortante solicitante de cálculo no plano
    considerado (N). Demais parâmetros: ver
    :func:`slip_resistance_ultimate`.
    """
    if not is_positive_finite(fv_sd):
        raise ValueError(
            f"check_slip_resistance_ultimate: fv_sd deve ser finito e "
            f"positivo, recebido: {fv_sd!r}"
        )
    ff_rd = slip_resistance_ultimate(mu, ce, ftb, num_slip_planes, ft_sd, gamma_e)
    return BoltCheckResult(force_sd=fv_sd, force_rd=ff_rd)


def check_slip_resistance_service(
    fv_sk: float,
    mu: float,
    ce: float,
    ftb: float,
    num_slip_planes: float,
    ft_sk: float,
) -> BoltCheckResult:
    """Verifica um parafuso de alta resistência protendido ao
    deslizamento, estado-limite de SERVIÇO (NBR 8800:2024, 6.3.4.4).

    Verifica APENAS o deslizamento — ver ATENÇÃO 3 no docstring do
    módulo: 6.3.3 deve SEMPRE ser verificado adicionalmente.

    ``fv_sk``: força cortante solicitante CARACTERÍSTICA no plano
    considerado (N) — ver :func:`slip_resistance_service` para a
    simplificação de 70 % permitida pela norma. Demais parâmetros: ver
    :func:`slip_resistance_service`.
    """
    if not is_positive_finite(fv_sk):
        raise ValueError(
            f"check_slip_resistance_service: fv_sk deve ser finito e "
            f"positivo, recebido: {fv_sk!r}"
        )
    ff_rk = slip_resistance_service(mu, ce, ftb, num_slip_planes, ft_sk)
    return BoltCheckResult(force_sd=fv_sk, force_rd=ff_rk)


# --- Chapas de enchimento em ligações parafusadas (6.5.7.2) -------------


def filler_plate_thickness_reduction_factor(total_filler_thickness: float) -> float:
    """Fator de redução da força resistente de cálculo dos parafusos ao
    cisalhamento (e ao esmagamento) em ligações por contato com chapas
    de enchimento de furos padrão, ``[1 − 0,0154·(ts − 6,3)]`` (NBR
    8800:2024, 6.5.7.2-a), onde ``ts`` é a soma das espessuras das
    chapas de enchimento, em milímetros.

    - ``total_filler_thickness <= 6,3 mm``: sem redução (fator ``1,0``,
      6.5.7.2, caput);
    - ``6,3 mm < total_filler_thickness <= 19 mm``: fator conforme a
      fórmula acima;
    - ``total_filler_thickness > 19 mm``: NÃO coberto por esta função —
      a norma exige, em vez disso, um dos requisitos geométricos de
      6.5.7.2-b) ou -c) (prolongamento da chapa de ligação com
      parafusos adicionais, ou número de parafusos equivalente), não
      implementados (fora do escopo — ver docstring do módulo
      ``connection_elements``). Levanta ``ValueError``.

    Multiplicar o resultado desta função por ``Fv,Rd``
    (:func:`bolt_shear_resistance`) ou ``Fc,Rd``
    (:func:`bolt_bearing_resistance`) — NÃO aplicado automaticamente
    por :func:`check_bolt_shear`/:func:`check_bolt_bearing`.

    ``total_filler_thickness``: soma das espessuras das chapas de
    enchimento, ``ts`` (m).
    """
    if not is_positive_finite(total_filler_thickness):
        raise ValueError(
            f"filler_plate_thickness_reduction_factor: total_filler_thickness "
            f"deve ser finito e positivo, recebido: {total_filler_thickness!r}"
        )
    ts_mm = total_filler_thickness * 1000.0
    if ts_mm <= 6.3:
        return 1.0
    if ts_mm <= 19.0:
        return 1.0 - 0.0154 * (ts_mm - 6.3)
    raise ValueError(
        f"filler_plate_thickness_reduction_factor: total_filler_thickness "
        f"({total_filler_thickness!r} m = {ts_mm!r} mm) excede 19 mm — exige "
        f"um dos requisitos geométricos de 6.5.7.2-b)/-c), não implementados"
    )
