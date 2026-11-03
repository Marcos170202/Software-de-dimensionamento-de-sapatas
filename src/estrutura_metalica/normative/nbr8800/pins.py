"""Ligações por pino.

Fonte: ABNT NBR 8800:2024, 6.4 "Pinos" (páginas 93-94). Fórmulas
conferidas por leitura direta (renderização visual) do PDF da norma —
ver rastreabilidade completa em ``docs/normative/NBR8800-RULES.md``.

Escopo desta fase: os três estados-limite últimos de um pino, cada um
verificado isoladamente (a norma não define uma equação de interação
entre eles — apenas declara, ao final de 6.4.2, que a força normal
solicitante de cálculo a considerar é a máxima força de contato,
"para distribuição uniforme ou não"). Cobre:

- 6.4.2.1 — momento fletor resistente de cálculo do pino,
  ``MRd = 1,2·W·fy/γa1``;
- 6.4.2.2 — força cortante resistente de cálculo do pino,
  ``Fv,Rd = 0,60·Aw·fy/γa1``, com ``Aw = 0,75·Ag``;
- 6.4.2.3 — força normal resistente de cálculo ao esmagamento,
  ``FR,d = 1,5·t·d·fy/γa1``.

Em todas as três, ``fy`` é "o menor valor da resistência ao escoamento
associado ao material do pino e da chapa de ligação" (6.4.2.1, nota) —
responsabilidade do chamador determinar esse mínimo antes de invocar
estas funções.

**ATENÇÃO — LIMITAÇÕES DE SEGURANÇA**: 6.4.1 (generalidades — hipótese
de tensão de contato uniformemente distribuída ao longo da espessura
de cada parte) é uma premissa de modelagem, não uma fórmula, e não é
verificada por este módulo. Requisitos construtivos de detalhamento de
pinos (geometria da placa de olhal, diâmetro do furo em relação ao
pino etc., se existentes em outras seções da norma) NÃO são cobertos.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ._check_result import CheckResult
from ._validation import is_positive_finite
from .flexure import FlexureCheckResult


def pin_flexural_resistance(elastic_section_modulus: float, fy: float, gamma_a1: float) -> float:
    """Momento fletor resistente de cálculo de um pino, ``MRd`` (NBR
    8800:2024, 6.4.2.1): ``MRd = 1,2·W·fy/γa1``.

    ``elastic_section_modulus``: módulo de resistência elástico da
    seção do pino, ``W`` (m³). ``fy``: menor valor da resistência ao
    escoamento entre o material do pino e da chapa de ligação.
    """
    if not is_positive_finite(elastic_section_modulus):
        raise ValueError(
            f"pin_flexural_resistance: elastic_section_modulus deve ser finito "
            f"e positivo, recebido: {elastic_section_modulus!r}"
        )
    if not is_positive_finite(fy):
        raise ValueError(
            f"pin_flexural_resistance: fy deve ser finito e positivo, recebido: {fy!r}"
        )
    if not is_positive_finite(gamma_a1):
        raise ValueError(
            f"pin_flexural_resistance: gamma_a1 deve ser finito e positivo, "
            f"recebido: {gamma_a1!r}"
        )
    return 1.2 * elastic_section_modulus * fy / gamma_a1


def pin_effective_shear_area(gross_area: float) -> float:
    """Área efetiva de cisalhamento da seção de um pino, ``Aw`` (NBR
    8800:2024, 6.4.2.2): ``Aw = 0,75·Ag``.

    ``gross_area``: área bruta do pino, ``Ag`` (m²).
    """
    if not is_positive_finite(gross_area):
        raise ValueError(
            f"pin_effective_shear_area: gross_area deve ser finito e "
            f"positivo, recebido: {gross_area!r}"
        )
    return 0.75 * gross_area


def pin_shear_resistance(effective_shear_area: float, fy: float, gamma_a1: float) -> float:
    """Força cortante resistente de cálculo de um pino, ``Fv,Rd`` (NBR
    8800:2024, 6.4.2.2): ``Fv,Rd = 0,60·Aw·fy/γa1``.

    ``effective_shear_area``: ``Aw`` — ver :func:`pin_effective_shear_area`.
    ``fy``: menor valor da resistência ao escoamento entre o material
    do pino e da chapa de ligação.
    """
    if not is_positive_finite(effective_shear_area):
        raise ValueError(
            f"pin_shear_resistance: effective_shear_area deve ser finito e "
            f"positivo, recebido: {effective_shear_area!r}"
        )
    if not is_positive_finite(fy):
        raise ValueError(f"pin_shear_resistance: fy deve ser finito e positivo, recebido: {fy!r}")
    if not is_positive_finite(gamma_a1):
        raise ValueError(
            f"pin_shear_resistance: gamma_a1 deve ser finito e positivo, "
            f"recebido: {gamma_a1!r}"
        )
    return 0.60 * effective_shear_area * fy / gamma_a1


def pin_bearing_resistance(
    thickness: float, pin_diameter: float, fy: float, gamma_a1: float
) -> float:
    """Força normal resistente de cálculo ao esmagamento de um pino,
    ``FR,d`` (NBR 8800:2024, 6.4.2.3): ``FR,d = 1,5·t·d·fy/γa1``.

    ``thickness``: espessura da chapa em contato com o pino, ``t`` (m).
    ``pin_diameter``: diâmetro do pino, ``d`` (m). ``fy``: menor valor
    da resistência ao escoamento entre o material do pino e da chapa.
    """
    if not is_positive_finite(thickness):
        raise ValueError(
            f"pin_bearing_resistance: thickness deve ser finito e positivo, "
            f"recebido: {thickness!r}"
        )
    if not is_positive_finite(pin_diameter):
        raise ValueError(
            f"pin_bearing_resistance: pin_diameter deve ser finito e positivo, "
            f"recebido: {pin_diameter!r}"
        )
    if not is_positive_finite(fy):
        raise ValueError(
            f"pin_bearing_resistance: fy deve ser finito e positivo, recebido: {fy!r}"
        )
    if not is_positive_finite(gamma_a1):
        raise ValueError(
            f"pin_bearing_resistance: gamma_a1 deve ser finito e positivo, "
            f"recebido: {gamma_a1!r}"
        )
    return 1.5 * thickness * pin_diameter * fy / gamma_a1


def check_pin_flexure(
    msd: float, elastic_section_modulus: float, fy: float, gamma_a1: float
) -> FlexureCheckResult:
    """Verifica um pino ao momento fletor (NBR 8800:2024, 6.4.2.1).

    Reaproveita :class:`~estrutura_metalica.normative.nbr8800.flexure.FlexureCheckResult`
    (mesmo contrato ``msd``/``mrd`` — ver ATENÇÃO no docstring daquele
    módulo sobre o sinal de ``msd``: esta função NÃO toma o valor
    absoluto automaticamente).

    ``msd``: momento fletor solicitante de cálculo no pino (N·m).
    ``elastic_section_modulus``/``fy``/``gamma_a1``: ver
    :func:`pin_flexural_resistance`.
    """
    if not math.isfinite(msd):
        raise ValueError(f"check_pin_flexure: msd deve ser finito, recebido: {msd!r}")
    mrd = pin_flexural_resistance(elastic_section_modulus, fy, gamma_a1)
    return FlexureCheckResult(msd=msd, mrd=mrd)


@dataclass(frozen=True, slots=True)
class PinCheckResult(CheckResult):
    """Resultado de uma verificação isolada (momento, cisalhamento OU
    esmagamento) de um pino (NBR 8800:2024, 6.4.2)."""

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


def check_pin_shear(fv_sd: float, gross_area: float, fy: float, gamma_a1: float) -> PinCheckResult:
    """Verifica um pino ao cisalhamento (NBR 8800:2024, 6.4.2.2).

    ``fv_sd``: força cortante solicitante de cálculo no pino (N).
    ``gross_area``/``fy``/``gamma_a1``: ver :func:`pin_shear_resistance`.
    """
    if not is_positive_finite(fv_sd):
        raise ValueError(
            f"check_pin_shear: fv_sd deve ser finito e positivo, recebido: {fv_sd!r}"
        )
    aw = pin_effective_shear_area(gross_area)
    fv_rd = pin_shear_resistance(aw, fy, gamma_a1)
    return PinCheckResult(force_sd=fv_sd, force_rd=fv_rd)


def check_pin_bearing(
    fc_sd: float, thickness: float, pin_diameter: float, fy: float, gamma_a1: float
) -> PinCheckResult:
    """Verifica um pino ao esmagamento (NBR 8800:2024, 6.4.2.3).

    ``fc_sd``: força normal solicitante de cálculo (a máxima força de
    contato, para distribuição uniforme ou não — 6.4.2, último
    parágrafo) (N). ``thickness``/``pin_diameter``/``fy``/``gamma_a1``:
    ver :func:`pin_bearing_resistance`.
    """
    if not is_positive_finite(fc_sd):
        raise ValueError(
            f"check_pin_bearing: fc_sd deve ser finito e positivo, recebido: {fc_sd!r}"
        )
    fr_d = pin_bearing_resistance(thickness, pin_diameter, fy, gamma_a1)
    return PinCheckResult(force_sd=fc_sd, force_rd=fr_d)
