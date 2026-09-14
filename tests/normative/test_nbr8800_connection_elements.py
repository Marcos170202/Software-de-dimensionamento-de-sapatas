"""Testes de ``estrutura_metalica.normative.nbr8800.connection_elements``.

:class:`TestWorkedExample` cobre uma chapa de ligação hipotética
calculada à mão.
"""

from __future__ import annotations

import math

import pytest

from estrutura_metalica.normative.nbr8800 import (
    ConnectionElementCheckResult,
    LoadCombinationClass,
    axial_yield_resistance,
    block_shear_resistance,
    bolted_splice_plate_effective_net_area,
    check_block_shear,
    check_connection_element_compression,
    check_connection_element_shear,
    check_connection_element_tension,
    shear_rupture_resistance,
    shear_yield_resistance,
    steel_resistance_factors,
    tensile_rupture_resistance,
)
from estrutura_metalica.normative.nbr8800.compression import flexural_buckling_force


class TestAxialYieldResistance:
    def test_matches_formula(self) -> None:
        area, fy, gamma_a1 = 5.0e-3, 250e6, 1.10
        expected = fy * area / gamma_a1
        assert axial_yield_resistance(area, fy, gamma_a1) == pytest.approx(expected)

    @pytest.mark.parametrize("field", ["area", "fy", "gamma_a1"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {"area": 5.0e-3, "fy": 250e6, "gamma_a1": 1.10}
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            axial_yield_resistance(**kwargs)


class TestTensileRuptureResistance:
    def test_matches_formula(self) -> None:
        ae, fu, gamma_a2 = 4.0e-3, 400e6, 1.35
        expected = fu * ae / gamma_a2
        assert tensile_rupture_resistance(ae, fu, gamma_a2) == pytest.approx(expected)

    @pytest.mark.parametrize("field", ["effective_net_area", "fu", "gamma_a2"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {"effective_net_area": 4.0e-3, "fu": 400e6, "gamma_a2": 1.35}
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            tensile_rupture_resistance(**kwargs)


class TestBoltedSplicePlateEffectiveNetArea:
    def test_returns_net_area_when_below_limit(self) -> None:
        assert bolted_splice_plate_effective_net_area(net_area=4.0e-3, gross_area=5.0e-3) == (
            pytest.approx(4.0e-3)
        )

    def test_caps_at_085_gross_area(self) -> None:
        result = bolted_splice_plate_effective_net_area(net_area=4.9e-3, gross_area=5.0e-3)
        assert result == pytest.approx(0.85 * 5.0e-3)

    @pytest.mark.parametrize("field", ["net_area", "gross_area"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {"net_area": 4.0e-3, "gross_area": 5.0e-3}
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            bolted_splice_plate_effective_net_area(**kwargs)


class TestShearYieldResistance:
    def test_matches_formula(self) -> None:
        ag, fy, gamma_a1 = 5.0e-3, 250e6, 1.10
        expected = 0.60 * fy * ag / gamma_a1
        assert shear_yield_resistance(ag, fy, gamma_a1) == pytest.approx(expected)

    @pytest.mark.parametrize("field", ["gross_area", "fy", "gamma_a1"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {"gross_area": 5.0e-3, "fy": 250e6, "gamma_a1": 1.10}
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            shear_yield_resistance(**kwargs)


class TestShearRuptureResistance:
    def test_matches_formula(self) -> None:
        anv, fu, gamma_a2 = 4.0e-3, 400e6, 1.35
        expected = 0.60 * fu * anv / gamma_a2
        assert shear_rupture_resistance(anv, fu, gamma_a2) == pytest.approx(expected)

    @pytest.mark.parametrize("field", ["net_shear_area", "fu", "gamma_a2"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {"net_shear_area": 4.0e-3, "fu": 400e6, "gamma_a2": 1.35}
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            shear_rupture_resistance(**kwargs)


class TestBlockShearResistance:
    _KWARGS = dict(
        gross_shear_area=6.0e-3,
        net_shear_area=4.5e-3,
        net_tension_area=2.0e-3,
        fy=250e6,
        fu=400e6,
        cts=1.0,
        gamma_a2=1.35,
    )

    def test_matches_formula_rupture_governs(self) -> None:
        rupture_term = 0.60 * 400e6 * 4.5e-3 + 1.0 * 400e6 * 2.0e-3
        yield_term = 0.60 * 250e6 * 6.0e-3 + 1.0 * 400e6 * 2.0e-3
        expected = min(rupture_term, yield_term) / 1.35
        result = block_shear_resistance(**self._KWARGS)
        assert result == pytest.approx(expected)

    def test_takes_minimum_of_the_two_terms(self) -> None:
        # Agv muito maior que Anv -> termo de escoamento deve governar.
        kwargs = dict(self._KWARGS)
        kwargs["gross_shear_area"] = 100.0
        rupture_term = 0.60 * 400e6 * 4.5e-3 + 1.0 * 400e6 * 2.0e-3
        yield_term = 0.60 * 250e6 * 100.0 + 1.0 * 400e6 * 2.0e-3
        expected = min(rupture_term, yield_term) / 1.35
        assert expected == pytest.approx(rupture_term / 1.35)
        result = block_shear_resistance(**kwargs)
        assert result == pytest.approx(expected)

    def test_cts_zero_point_five(self) -> None:
        kwargs = dict(self._KWARGS)
        kwargs["cts"] = 0.5
        rupture_term = 0.60 * 400e6 * 4.5e-3 + 0.5 * 400e6 * 2.0e-3
        yield_term = 0.60 * 250e6 * 6.0e-3 + 0.5 * 400e6 * 2.0e-3
        expected = min(rupture_term, yield_term) / 1.35
        assert block_shear_resistance(**kwargs) == pytest.approx(expected)

    def test_rejects_invalid_cts(self) -> None:
        kwargs = dict(self._KWARGS)
        kwargs["cts"] = 0.75
        with pytest.raises(ValueError, match="cts"):
            block_shear_resistance(**kwargs)

    @pytest.mark.parametrize(
        "field",
        ["gross_shear_area", "net_shear_area", "net_tension_area", "fy", "fu", "gamma_a2"],
    )
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = dict(self._KWARGS)
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            block_shear_resistance(**kwargs)


class TestConnectionElementCheckResultValidation:
    @pytest.mark.parametrize("bad_value", [0.0, -1.0, float("nan"), float("inf")])
    def test_rejects_non_positive_or_non_finite_force_sd(self, bad_value: float) -> None:
        with pytest.raises(ValueError):
            ConnectionElementCheckResult(force_sd=bad_value, force_rd=1.0)

    @pytest.mark.parametrize("bad_value", [0.0, -1.0, float("nan"), float("inf")])
    def test_rejects_non_positive_or_non_finite_force_rd(self, bad_value: float) -> None:
        with pytest.raises(ValueError):
            ConnectionElementCheckResult(force_sd=1.0, force_rd=bad_value)


class TestCheckConnectionElementTension:
    _KWARGS = dict(
        nt_sd=1.0, gross_area=5.0e-3, effective_net_area=4.0e-3, fy=250e6, fu=400e6,
        gamma_a1=1.10, gamma_a2=1.35,
    )

    def test_rejects_non_positive_nt_sd(self) -> None:
        kwargs = dict(self._KWARGS)
        kwargs["nt_sd"] = 0.0
        with pytest.raises(ValueError):
            check_connection_element_tension(**kwargs)

    def test_takes_minimum_of_yield_and_rupture(self) -> None:
        result = check_connection_element_tension(**self._KWARGS)
        yield_rd = axial_yield_resistance(5.0e-3, 250e6, 1.10)
        rupture_rd = tensile_rupture_resistance(4.0e-3, 400e6, 1.35)
        assert result.force_rd == pytest.approx(min(yield_rd, rupture_rd))

    def test_is_ok_below_and_above_capacity(self) -> None:
        low = check_connection_element_tension(**{**self._KWARGS, "nt_sd": 1.0})
        high = check_connection_element_tension(**{**self._KWARGS, "nt_sd": 100_000_000.0})
        assert low.is_ok is True
        assert high.is_ok is False


class TestCheckConnectionElementCompression:
    _RESISTANCE_FACTORS = steel_resistance_factors(LoadCombinationClass.NORMAL)

    def test_rejects_non_positive_nc_sd(self) -> None:
        with pytest.raises(ValueError):
            check_connection_element_compression(
                nc_sd=0.0, gross_area=5.0e-3, fy=250e6,
                elastic_buckling_force=1.0e6, resistance_factors=self._RESISTANCE_FACTORS,
            )

    def test_stocky_element_governed_by_yield(self) -> None:
        # Ne muito grande -> instabilidade nao governa -> escoamento governa.
        gross_area, fy = 5.0e-3, 250e6
        result = check_connection_element_compression(
            nc_sd=1.0, gross_area=gross_area, fy=fy,
            elastic_buckling_force=1.0e12, resistance_factors=self._RESISTANCE_FACTORS,
        )
        expected = axial_yield_resistance(gross_area, fy, self._RESISTANCE_FACTORS.gamma_a1)
        assert result.force_rd == pytest.approx(expected, rel=1e-6)

    def test_slender_element_governed_by_buckling(self) -> None:
        # Ne muito pequeno -> instabilidade governa -> Frd < resistencia ao escoamento.
        gross_area, fy = 5.0e-3, 250e6
        result = check_connection_element_compression(
            nc_sd=1.0, gross_area=gross_area, fy=fy,
            elastic_buckling_force=1.0e3, resistance_factors=self._RESISTANCE_FACTORS,
        )
        yield_rd = axial_yield_resistance(gross_area, fy, self._RESISTANCE_FACTORS.gamma_a1)
        assert result.force_rd < yield_rd

    def test_matches_flexural_buckling_force_reuse(self) -> None:
        e, i, le = 200_000e6, 8.333e-8, 2.0
        ne = flexural_buckling_force(e, i, le)
        result = check_connection_element_compression(
            nc_sd=1.0, gross_area=5.0e-3, fy=250e6,
            elastic_buckling_force=ne, resistance_factors=self._RESISTANCE_FACTORS,
        )
        assert result.force_rd > 0.0

    def test_is_ok_below_and_above_capacity(self) -> None:
        kwargs = dict(
            gross_area=5.0e-3, fy=250e6, elastic_buckling_force=1.0e6,
            resistance_factors=self._RESISTANCE_FACTORS,
        )
        low = check_connection_element_compression(nc_sd=1.0, **kwargs)
        high = check_connection_element_compression(nc_sd=100_000_000.0, **kwargs)
        assert low.is_ok is True
        assert high.is_ok is False


class TestCheckConnectionElementShear:
    _KWARGS = dict(
        fv_sd=1.0, gross_area=5.0e-3, net_shear_area=4.0e-3, fy=250e6, fu=400e6,
        gamma_a1=1.10, gamma_a2=1.35,
    )

    def test_rejects_non_positive_fv_sd(self) -> None:
        kwargs = dict(self._KWARGS)
        kwargs["fv_sd"] = 0.0
        with pytest.raises(ValueError):
            check_connection_element_shear(**kwargs)

    def test_takes_minimum_of_yield_and_rupture(self) -> None:
        result = check_connection_element_shear(**self._KWARGS)
        yield_rd = shear_yield_resistance(5.0e-3, 250e6, 1.10)
        rupture_rd = shear_rupture_resistance(4.0e-3, 400e6, 1.35)
        assert result.force_rd == pytest.approx(min(yield_rd, rupture_rd))

    def test_is_ok_below_and_above_capacity(self) -> None:
        low = check_connection_element_shear(**{**self._KWARGS, "fv_sd": 1.0})
        high = check_connection_element_shear(**{**self._KWARGS, "fv_sd": 100_000_000.0})
        assert low.is_ok is True
        assert high.is_ok is False


class TestCheckBlockShear:
    _KWARGS = dict(
        fsd=1.0, gross_shear_area=6.0e-3, net_shear_area=4.5e-3, net_tension_area=2.0e-3,
        fy=250e6, fu=400e6, cts=1.0, gamma_a2=1.35,
    )

    def test_rejects_non_positive_fsd(self) -> None:
        kwargs = dict(self._KWARGS)
        kwargs["fsd"] = 0.0
        with pytest.raises(ValueError):
            check_block_shear(**kwargs)

    def test_returns_connection_element_check_result(self) -> None:
        result = check_block_shear(**self._KWARGS)
        assert isinstance(result, ConnectionElementCheckResult)
        assert result.force_rd > 0.0

    def test_is_ok_below_and_above_capacity(self) -> None:
        low = check_block_shear(**{**self._KWARGS, "fsd": 1.0})
        high = check_block_shear(**{**self._KWARGS, "fsd": 100_000_000.0})
        assert low.is_ok is True
        assert high.is_ok is False


class TestWorkedExample:
    """Chapa de ligação hipotética tracionada, `Ag=5000` mm²,
    `Ae=4000` mm² (área líquida já descontados furos, hipotética),
    aço com `fy=250` MPa/`fu=400` MPa, combinação normal.

    Cálculo à mão (NBR 8800:2024, 6.5.3):
    - escoamento: `F_Rd = fy*Ag/gamma_a1 = 250e6*5.0e-3/1.10 ≈ 1 136 364 N`
    - ruptura: `F_Rd = fu*Ae/gamma_a2 = 400e6*4.0e-3/1.35 ≈ 1 185 185 N`
    - governa o escoamento: `F_Rd ≈ 1 136 364 N`
    """

    _GROSS_AREA = 5.0e-3
    _EFFECTIVE_NET_AREA = 4.0e-3
    _FY = 250e6
    _FU = 400e6
    _GAMMA_A1 = 1.10
    _GAMMA_A2 = 1.35

    def test_tension_governed_by_yield_matches_hand_calculation(self) -> None:
        result = check_connection_element_tension(
            nt_sd=1.0, gross_area=self._GROSS_AREA, effective_net_area=self._EFFECTIVE_NET_AREA,
            fy=self._FY, fu=self._FU, gamma_a1=self._GAMMA_A1, gamma_a2=self._GAMMA_A2,
        )
        assert result.force_rd == pytest.approx(1_136_363.6, rel=1e-6)
        yield_rd = self._FY * self._GROSS_AREA / self._GAMMA_A1
        rupture_rd = self._FU * self._EFFECTIVE_NET_AREA / self._GAMMA_A2
        assert yield_rd < rupture_rd  # confirma a premissa do exemplo
        assert math.isclose(result.force_rd, yield_rd)
