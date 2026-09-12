"""Testes de ``estrutura_metalica.normative.nbr8800.welds``.

:class:`TestWorkedExample` cobre uma solda de filete hipotética
calculada à mão.
"""

from __future__ import annotations

import math

import pytest

from estrutura_metalica.normative.nbr8800 import (
    WeldCheckResult,
    check_fillet_weld_shear,
    fillet_weld_effective_area,
    fillet_weld_effective_throat,
    fillet_weld_shear_resistance,
    minimum_fillet_weld_leg_size,
)


class TestFilletWeldEffectiveThroat:
    def test_matches_formula(self) -> None:
        dw = 0.008
        expected = dw * math.sin(math.radians(45.0))
        assert fillet_weld_effective_throat(dw) == pytest.approx(expected)

    def test_rejects_non_positive_leg_size(self) -> None:
        with pytest.raises(ValueError):
            fillet_weld_effective_throat(0.0)


class TestFilletWeldEffectiveArea:
    def test_matches_formula(self) -> None:
        length, throat = 0.10, 0.0042426
        assert fillet_weld_effective_area(length, throat) == pytest.approx(length * throat)

    @pytest.mark.parametrize("field", ["effective_length", "effective_throat"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {"effective_length": 0.10, "effective_throat": 0.0042426}
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            fillet_weld_effective_area(**kwargs)


class TestFilletWeldShearResistance:
    def test_matches_formula(self) -> None:
        aw, fw, gamma_w2 = 4.24e-4, 485e6, 1.35
        expected = 0.6 * fw * aw / gamma_w2
        result = fillet_weld_shear_resistance(aw, fw, gamma_w2)
        assert result == pytest.approx(expected)

    @pytest.mark.parametrize("field", ["effective_area", "fw", "gamma_w2"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {"effective_area": 4.24e-4, "fw": 485e6, "gamma_w2": 1.35}
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            fillet_weld_shear_resistance(**kwargs)


class TestMinimumFilletWeldLegSize:
    @pytest.mark.parametrize(
        ("thickness", "expected_minimum"),
        [
            (0.003, 0.003),
            (0.0063, 0.003),
            (0.0064, 0.005),
            (0.0125, 0.005),
            (0.0126, 0.006),
            (0.019, 0.006),
            (0.0191, 0.008),
            (0.050, 0.008),
        ],
    )
    def test_matches_tabela_11(self, thickness: float, expected_minimum: float) -> None:
        assert minimum_fillet_weld_leg_size(thickness) == pytest.approx(expected_minimum)

    def test_rejects_non_positive_thickness(self) -> None:
        with pytest.raises(ValueError):
            minimum_fillet_weld_leg_size(0.0)


class TestWeldCheckResultValidation:
    @pytest.mark.parametrize("bad_value", [0.0, -1.0, float("nan"), float("inf")])
    def test_rejects_non_positive_or_non_finite_fw_sd(self, bad_value: float) -> None:
        with pytest.raises(ValueError):
            WeldCheckResult(fw_sd=bad_value, fw_rd=1.0)

    @pytest.mark.parametrize("bad_value", [0.0, -1.0, float("nan"), float("inf")])
    def test_rejects_non_positive_or_non_finite_fw_rd(self, bad_value: float) -> None:
        with pytest.raises(ValueError):
            WeldCheckResult(fw_sd=1.0, fw_rd=bad_value)


class TestCheckFilletWeldShear:
    _KWARGS = dict(
        fw_sd=1.0,
        leg_size=0.006,
        effective_length=0.10,
        fw=485e6,
        gamma_w2=1.35,
        thinner_part_thickness=0.008,
    )

    def test_rejects_non_positive_fw_sd(self) -> None:
        kwargs = dict(self._KWARGS)
        kwargs["fw_sd"] = 0.0
        with pytest.raises(ValueError):
            check_fillet_weld_shear(**kwargs)

    def test_rejects_leg_size_below_minimum(self) -> None:
        # thinner_part_thickness=8mm -> minimo Tabela 11 = 5mm; perna de 3mm viola.
        kwargs = dict(self._KWARGS)
        kwargs["leg_size"] = 0.003
        with pytest.raises(ValueError, match="Tabela 11"):
            check_fillet_weld_shear(**kwargs)

    def test_accepts_leg_size_at_exact_minimum(self) -> None:
        kwargs = dict(self._KWARGS)
        kwargs["leg_size"] = minimum_fillet_weld_leg_size(kwargs["thinner_part_thickness"])
        result = check_fillet_weld_shear(**kwargs)
        assert result.fw_rd > 0.0

    def test_returns_weld_check_result(self) -> None:
        result = check_fillet_weld_shear(**self._KWARGS)
        assert isinstance(result, WeldCheckResult)
        assert result.fw_rd > 0.0

    def test_is_ok_below_and_above_capacity(self) -> None:
        low = check_fillet_weld_shear(**{**self._KWARGS, "fw_sd": 1.0})
        high = check_fillet_weld_shear(**{**self._KWARGS, "fw_sd": 1_000_000.0})
        assert low.is_ok is True
        assert high.is_ok is False


class TestWorkedExample:
    """Solda de filete hipotética: perna dw=6 mm, comprimento efetivo
    ℓw=100 mm, metal da solda com fw=485 MPa (valor hipotético,
    ilustrativo, não extraído da Tabela A.4 da norma), combinação
    normal (γw2=1,35).

    Cálculo à mão (NBR 8800:2024, 6.2.2.2/6.2.5.1):
    - te = dw·sen(45°) = 0,006·0,70711 = 0,0042426 m
    - Aw = ℓw·te = 0,10·0,0042426 = 4,2426e-4 m²
    - Fw,Rd = 0,6·fw·Aw/γw2 = 0,6·485e6·4,2426e-4/1,35 ≈ 91 452,5 N
    """

    _DW = 0.006
    _LW = 0.10
    _FW = 485e6
    _GAMMA_W2 = 1.35

    def _expected_fw_rd(self) -> float:
        te = self._DW * math.sin(math.radians(45.0))
        aw = self._LW * te
        return 0.6 * self._FW * aw / self._GAMMA_W2

    def test_fw_rd_matches_hand_calculation(self) -> None:
        result = check_fillet_weld_shear(
            fw_sd=1.0,
            leg_size=self._DW,
            effective_length=self._LW,
            fw=self._FW,
            gamma_w2=self._GAMMA_W2,
            thinner_part_thickness=0.008,
        )
        assert result.fw_rd == pytest.approx(self._expected_fw_rd(), rel=1e-9)
        assert result.fw_rd == pytest.approx(91_452.477, rel=1e-6)
