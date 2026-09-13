"""Testes de ``estrutura_metalica.normative.nbr8800.pins``.

:class:`TestWorkedExample` cobre um pino cilíndrico hipotético
calculado à mão.
"""

from __future__ import annotations

import math

import pytest

from estrutura_metalica.normative.nbr8800 import (
    PinCheckResult,
    check_pin_bearing,
    check_pin_flexure,
    check_pin_shear,
    pin_bearing_resistance,
    pin_effective_shear_area,
    pin_flexural_resistance,
    pin_shear_resistance,
)
from estrutura_metalica.normative.nbr8800.flexure import FlexureCheckResult


class TestPinFlexuralResistance:
    def test_matches_formula(self) -> None:
        w, fy, gamma_a1 = 4.0e-6, 250e6, 1.10
        expected = 1.2 * w * fy / gamma_a1
        assert pin_flexural_resistance(w, fy, gamma_a1) == pytest.approx(expected)

    @pytest.mark.parametrize("field", ["elastic_section_modulus", "fy", "gamma_a1"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {"elastic_section_modulus": 4.0e-6, "fy": 250e6, "gamma_a1": 1.10}
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            pin_flexural_resistance(**kwargs)


class TestPinEffectiveShearArea:
    def test_matches_formula(self) -> None:
        ag = 7.85e-4
        assert pin_effective_shear_area(ag) == pytest.approx(0.75 * ag)

    def test_rejects_non_positive_gross_area(self) -> None:
        with pytest.raises(ValueError):
            pin_effective_shear_area(0.0)


class TestPinShearResistance:
    def test_matches_formula(self) -> None:
        aw, fy, gamma_a1 = 5.8875e-4, 250e6, 1.10
        expected = 0.60 * aw * fy / gamma_a1
        assert pin_shear_resistance(aw, fy, gamma_a1) == pytest.approx(expected)

    @pytest.mark.parametrize("field", ["effective_shear_area", "fy", "gamma_a1"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {"effective_shear_area": 5.8875e-4, "fy": 250e6, "gamma_a1": 1.10}
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            pin_shear_resistance(**kwargs)


class TestPinBearingResistance:
    def test_matches_formula(self) -> None:
        t, d, fy, gamma_a1 = 0.020, 0.050, 250e6, 1.10
        expected = 1.5 * t * d * fy / gamma_a1
        assert pin_bearing_resistance(t, d, fy, gamma_a1) == pytest.approx(expected)

    @pytest.mark.parametrize("field", ["thickness", "pin_diameter", "fy", "gamma_a1"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {"thickness": 0.020, "pin_diameter": 0.050, "fy": 250e6, "gamma_a1": 1.10}
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            pin_bearing_resistance(**kwargs)


class TestPinCheckResultValidation:
    @pytest.mark.parametrize("bad_value", [0.0, -1.0, float("nan"), float("inf")])
    def test_rejects_non_positive_or_non_finite_force_sd(self, bad_value: float) -> None:
        with pytest.raises(ValueError):
            PinCheckResult(force_sd=bad_value, force_rd=1.0)

    @pytest.mark.parametrize("bad_value", [0.0, -1.0, float("nan"), float("inf")])
    def test_rejects_non_positive_or_non_finite_force_rd(self, bad_value: float) -> None:
        with pytest.raises(ValueError):
            PinCheckResult(force_sd=1.0, force_rd=bad_value)


class TestCheckPinFlexure:
    _KWARGS = dict(msd=1.0, elastic_section_modulus=4.0e-6, fy=250e6, gamma_a1=1.10)

    def test_rejects_non_finite_msd(self) -> None:
        kwargs = dict(self._KWARGS)
        kwargs["msd"] = float("nan")
        with pytest.raises(ValueError):
            check_pin_flexure(**kwargs)

    def test_returns_flexure_check_result(self) -> None:
        result = check_pin_flexure(**self._KWARGS)
        assert isinstance(result, FlexureCheckResult)
        assert result.mrd > 0.0


class TestCheckPinShear:
    _KWARGS = dict(fv_sd=1.0, gross_area=7.85e-4, fy=250e6, gamma_a1=1.10)

    def test_rejects_non_positive_fv_sd(self) -> None:
        kwargs = dict(self._KWARGS)
        kwargs["fv_sd"] = 0.0
        with pytest.raises(ValueError):
            check_pin_shear(**kwargs)

    def test_returns_pin_check_result(self) -> None:
        result = check_pin_shear(**self._KWARGS)
        assert isinstance(result, PinCheckResult)
        assert result.force_rd > 0.0

    def test_is_ok_below_and_above_capacity(self) -> None:
        low = check_pin_shear(**{**self._KWARGS, "fv_sd": 1.0})
        high = check_pin_shear(**{**self._KWARGS, "fv_sd": 1_000_000.0})
        assert low.is_ok is True
        assert high.is_ok is False


class TestCheckPinBearing:
    _KWARGS = dict(fc_sd=1.0, thickness=0.020, pin_diameter=0.050, fy=250e6, gamma_a1=1.10)

    def test_rejects_non_positive_fc_sd(self) -> None:
        kwargs = dict(self._KWARGS)
        kwargs["fc_sd"] = 0.0
        with pytest.raises(ValueError):
            check_pin_bearing(**kwargs)

    def test_returns_pin_check_result(self) -> None:
        result = check_pin_bearing(**self._KWARGS)
        assert isinstance(result, PinCheckResult)
        assert result.force_rd > 0.0

    def test_is_ok_below_and_above_capacity(self) -> None:
        low = check_pin_bearing(**{**self._KWARGS, "fc_sd": 1.0})
        high = check_pin_bearing(**{**self._KWARGS, "fc_sd": 1_000_000.0})
        assert low.is_ok is True
        assert high.is_ok is False


class TestWorkedExample:
    """Pino cilíndrico maciço hipotético, diâmetro ``d=50`` mm, aço com
    ``fy=250`` MPa (menor valor entre pino e chapa, hipotético), chapa
    de ligação com ``t=20`` mm de espessura, combinação normal
    (``γa1=1,10``).

    Cálculo à mão (NBR 8800:2024, 6.4.2):
    - ``Ag = π·d²/4 = π·0,050²/4 = 1,9635e-3`` m²
    - ``W = d³/6 = 0,050³/6 = 2,0833e-5`` m³ (seção circular)
    - ``MRd = 1,2·W·fy/γa1 = 1,2·2,0833e-5·250e6/1,10 ≈ 5 681,8`` N·m
    - ``Aw = 0,75·Ag = 1,4726e-3`` m²
    - ``Fv,Rd = 0,60·Aw·fy/γa1 = 0,60·1,4726e-3·250e6/1,10 ≈ 200 812,0`` N
    - ``FR,d = 1,5·t·d·fy/γa1 = 1,5·0,020·0,050·250e6/1,10 ≈ 340 909,1`` N
    """

    _D = 0.050
    _T = 0.020
    _FY = 250e6
    _GAMMA_A1 = 1.10
    _AG = math.pi * _D**2 / 4.0
    _W = _D**3 / 6.0

    def test_mrd_matches_hand_calculation(self) -> None:
        result = check_pin_flexure(1.0, self._W, self._FY, self._GAMMA_A1)
        assert result.mrd == pytest.approx(5_681.8, rel=1e-4)

    def test_fv_rd_matches_hand_calculation(self) -> None:
        result = check_pin_shear(1.0, self._AG, self._FY, self._GAMMA_A1)
        assert result.force_rd == pytest.approx(200_812.0, rel=1e-4)

    def test_fr_d_matches_hand_calculation(self) -> None:
        result = check_pin_bearing(1.0, self._T, self._D, self._FY, self._GAMMA_A1)
        assert result.force_rd == pytest.approx(340_909.1, rel=1e-4)
