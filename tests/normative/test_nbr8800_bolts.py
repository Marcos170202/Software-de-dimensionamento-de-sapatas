"""Testes de ``estrutura_metalica.normative.nbr8800.bolts``.

:class:`TestWorkedExample` cobre um parafuso hipotético (M20, ASTM
A325 — ``fub=825`` MPa hipotético, ilustrativo) calculado à mão.
"""

from __future__ import annotations

import math

import pytest

from estrutura_metalica.normative.nbr8800 import (
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


class TestBoltGrossArea:
    def test_matches_formula(self) -> None:
        db = 0.020
        expected = 0.25 * math.pi * db**2
        assert bolt_gross_area(db) == pytest.approx(expected)

    def test_rejects_non_positive_diameter(self) -> None:
        with pytest.raises(ValueError):
            bolt_gross_area(0.0)


class TestBoltEffectiveAreaTension:
    def test_matches_formula(self) -> None:
        ab = 3.14159265e-4
        assert bolt_effective_area_tension(ab) == pytest.approx(0.75 * ab)

    def test_rejects_non_positive_gross_area(self) -> None:
        with pytest.raises(ValueError):
            bolt_effective_area_tension(0.0)


class TestBoltTensileResistance:
    def test_matches_formula(self) -> None:
        abe, fub, gamma_a2 = 2.356194e-4, 825e6, 1.35
        expected = abe * fub / gamma_a2
        assert bolt_tensile_resistance(abe, fub, gamma_a2) == pytest.approx(expected)

    @pytest.mark.parametrize("field", ["effective_area", "fub", "gamma_a2"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {"effective_area": 2.356194e-4, "fub": 825e6, "gamma_a2": 1.35}
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            bolt_tensile_resistance(**kwargs)


class TestThreadedRodTensileResistanceCap:
    def test_matches_formula(self) -> None:
        ab, fy, gamma_a1 = 3.14159265e-4, 250e6, 1.10
        expected = ab * fy / gamma_a1
        result = threaded_rod_tensile_resistance_cap(ab, fy, gamma_a1)
        assert result == pytest.approx(expected)

    @pytest.mark.parametrize("field", ["gross_area", "fy", "gamma_a1"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {"gross_area": 3.14159265e-4, "fy": 250e6, "gamma_a1": 1.10}
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            threaded_rod_tensile_resistance_cap(**kwargs)


class TestBoltShearResistance:
    def test_matches_formula_threads_in_shear_plane(self) -> None:
        ab, fub, gamma_a2 = 3.14159265e-4, 825e6, 1.35
        expected = 0.45 * ab * fub / gamma_a2
        result = bolt_shear_resistance(
            ab, fub, gamma_a2, threads_excluded_from_shear_plane=False
        )
        assert result == pytest.approx(expected)

    def test_matches_formula_threads_excluded_from_shear_plane(self) -> None:
        ab, fub, gamma_a2 = 3.14159265e-4, 825e6, 1.35
        expected = 0.56 * ab * fub / gamma_a2
        result = bolt_shear_resistance(
            ab, fub, gamma_a2, threads_excluded_from_shear_plane=True
        )
        assert result == pytest.approx(expected)

    def test_excluded_from_shear_plane_is_less_conservative(self) -> None:
        ab, fub, gamma_a2 = 3.14159265e-4, 825e6, 1.35
        included = bolt_shear_resistance(
            ab, fub, gamma_a2, threads_excluded_from_shear_plane=False
        )
        excluded = bolt_shear_resistance(
            ab, fub, gamma_a2, threads_excluded_from_shear_plane=True
        )
        assert excluded > included

    @pytest.mark.parametrize("field", ["gross_area", "fub", "gamma_a2"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {"gross_area": 3.14159265e-4, "fub": 825e6, "gamma_a2": 1.35}
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            bolt_shear_resistance(threads_excluded_from_shear_plane=False, **kwargs)


class TestBoltBearingResistance:
    def test_matches_formula_deformation_is_design_limit(self) -> None:
        lf, t, fu, db, gamma_a2 = 0.05, 0.010, 450e6, 0.020, 1.35
        expected_edge = 1.2 * lf * t * fu / gamma_a2
        expected_diameter = 2.4 * db * t * fu / gamma_a2
        result = bolt_bearing_resistance(
            lf, t, fu, db, gamma_a2, deformation_is_design_limit=True
        )
        assert result == pytest.approx(min(expected_edge, expected_diameter))

    def test_matches_formula_deformation_is_not_design_limit(self) -> None:
        lf, t, fu, db, gamma_a2 = 0.05, 0.010, 450e6, 0.020, 1.35
        expected_edge = 1.5 * lf * t * fu / gamma_a2
        expected_diameter = 3.0 * db * t * fu / gamma_a2
        result = bolt_bearing_resistance(
            lf, t, fu, db, gamma_a2, deformation_is_design_limit=False
        )
        assert result == pytest.approx(min(expected_edge, expected_diameter))

    def test_not_a_design_limit_is_less_conservative(self) -> None:
        kwargs = dict(
            edge_or_hole_distance=0.05, thickness=0.010, fu=450e6, bolt_diameter=0.020,
            gamma_a2=1.35,
        )
        limit = bolt_bearing_resistance(**kwargs, deformation_is_design_limit=True)
        not_limit = bolt_bearing_resistance(**kwargs, deformation_is_design_limit=False)
        assert not_limit > limit

    @pytest.mark.parametrize(
        "field", ["edge_or_hole_distance", "thickness", "fu", "bolt_diameter", "gamma_a2"]
    )
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {
            "edge_or_hole_distance": 0.05,
            "thickness": 0.010,
            "fu": 450e6,
            "bolt_diameter": 0.020,
            "gamma_a2": 1.35,
        }
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            bolt_bearing_resistance(**kwargs, deformation_is_design_limit=True)


class TestBoltCheckResultValidation:
    @pytest.mark.parametrize("bad_value", [0.0, -1.0, float("nan"), float("inf")])
    def test_rejects_non_positive_or_non_finite_force_sd(self, bad_value: float) -> None:
        with pytest.raises(ValueError):
            BoltCheckResult(force_sd=bad_value, force_rd=1.0)

    @pytest.mark.parametrize("bad_value", [0.0, -1.0, float("nan"), float("inf")])
    def test_rejects_non_positive_or_non_finite_force_rd(self, bad_value: float) -> None:
        with pytest.raises(ValueError):
            BoltCheckResult(force_sd=1.0, force_rd=bad_value)


class TestCheckBoltTension:
    _KWARGS = dict(ft_sd=1.0, bolt_diameter=0.020, fub=825e6, gamma_a2=1.35)

    def test_rejects_non_positive_ft_sd(self) -> None:
        kwargs = dict(self._KWARGS)
        kwargs["ft_sd"] = 0.0
        with pytest.raises(ValueError):
            check_bolt_tension(**kwargs)

    def test_returns_bolt_check_result(self) -> None:
        result = check_bolt_tension(**self._KWARGS)
        assert isinstance(result, BoltCheckResult)
        assert result.force_rd > 0.0

    def test_is_ok_below_and_above_capacity(self) -> None:
        low = check_bolt_tension(**{**self._KWARGS, "ft_sd": 1.0})
        high = check_bolt_tension(**{**self._KWARGS, "ft_sd": 1_000_000.0})
        assert low.is_ok is True
        assert high.is_ok is False


class TestCheckBoltShear:
    _KWARGS = dict(
        fv_sd=1.0,
        bolt_diameter=0.020,
        fub=825e6,
        gamma_a2=1.35,
        threads_excluded_from_shear_plane=False,
    )

    def test_rejects_non_positive_fv_sd(self) -> None:
        kwargs = dict(self._KWARGS)
        kwargs["fv_sd"] = 0.0
        with pytest.raises(ValueError):
            check_bolt_shear(**kwargs)

    def test_returns_bolt_check_result(self) -> None:
        result = check_bolt_shear(**self._KWARGS)
        assert isinstance(result, BoltCheckResult)
        assert result.force_rd > 0.0

    def test_is_ok_below_and_above_capacity(self) -> None:
        low = check_bolt_shear(**{**self._KWARGS, "fv_sd": 1.0})
        high = check_bolt_shear(**{**self._KWARGS, "fv_sd": 1_000_000.0})
        assert low.is_ok is True
        assert high.is_ok is False


class TestCheckBoltBearing:
    _KWARGS = dict(
        fc_sd=1.0,
        edge_or_hole_distance=0.05,
        thickness=0.010,
        fu=450e6,
        bolt_diameter=0.020,
        gamma_a2=1.35,
        deformation_is_design_limit=True,
    )

    def test_rejects_non_positive_fc_sd(self) -> None:
        kwargs = dict(self._KWARGS)
        kwargs["fc_sd"] = 0.0
        with pytest.raises(ValueError):
            check_bolt_bearing(**kwargs)

    def test_returns_bolt_check_result(self) -> None:
        result = check_bolt_bearing(**self._KWARGS)
        assert isinstance(result, BoltCheckResult)
        assert result.force_rd > 0.0

    def test_is_ok_below_and_above_capacity(self) -> None:
        low = check_bolt_bearing(**{**self._KWARGS, "fc_sd": 1.0})
        high = check_bolt_bearing(**{**self._KWARGS, "fc_sd": 1_000_000.0})
        assert low.is_ok is True
        assert high.is_ok is False


class TestBoltCombinedTensionAndShearRatio:
    def test_matches_formula(self) -> None:
        ft_sd, ft_rd, fv_sd, fv_rd = 50_000.0, 143_989.0, 40_000.0, 86_393.8
        expected = (ft_sd / ft_rd) ** 2 + (fv_sd / fv_rd) ** 2
        result = bolt_combined_tension_and_shear_ratio(ft_sd, ft_rd, fv_sd, fv_rd)
        assert result == pytest.approx(expected)

    def test_accepts_zero_ft_sd_or_fv_sd(self) -> None:
        assert bolt_combined_tension_and_shear_ratio(0.0, 100.0, 50.0, 100.0) == pytest.approx(
            0.25
        )
        assert bolt_combined_tension_and_shear_ratio(50.0, 100.0, 0.0, 100.0) == pytest.approx(
            0.25
        )

    @pytest.mark.parametrize("field", ["ft_sd", "fv_sd"])
    def test_rejects_negative_sd(self, field: str) -> None:
        kwargs = {"ft_sd": 50.0, "ft_rd": 100.0, "fv_sd": 50.0, "fv_rd": 100.0}
        kwargs[field] = -1.0
        with pytest.raises(ValueError):
            bolt_combined_tension_and_shear_ratio(**kwargs)

    @pytest.mark.parametrize("field", ["ft_rd", "fv_rd"])
    def test_rejects_non_positive_rd(self, field: str) -> None:
        kwargs = {"ft_sd": 50.0, "ft_rd": 100.0, "fv_sd": 50.0, "fv_rd": 100.0}
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            bolt_combined_tension_and_shear_ratio(**kwargs)


class TestBoltCombinedCheckResultValidation:
    _KWARGS = dict(ft_sd=50.0, ft_rd=100.0, fv_sd=50.0, fv_rd=100.0, interaction_ratio=0.5)

    @pytest.mark.parametrize("field", ["ft_sd", "fv_sd"])
    def test_rejects_negative_sd(self, field: str) -> None:
        kwargs = dict(self._KWARGS)
        kwargs[field] = -1.0
        with pytest.raises(ValueError):
            BoltCombinedCheckResult(**kwargs)

    @pytest.mark.parametrize("field", ["ft_rd", "fv_rd"])
    def test_rejects_non_positive_rd(self, field: str) -> None:
        kwargs = dict(self._KWARGS)
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            BoltCombinedCheckResult(**kwargs)

    @pytest.mark.parametrize("bad_value", [-1.0, float("nan"), float("inf")])
    def test_rejects_bad_interaction_ratio(self, bad_value: float) -> None:
        kwargs = dict(self._KWARGS)
        kwargs["interaction_ratio"] = bad_value
        with pytest.raises(ValueError):
            BoltCombinedCheckResult(**kwargs)

    def test_sd_and_rd_aliases(self) -> None:
        result = BoltCombinedCheckResult(**self._KWARGS)
        assert result.sd == result.interaction_ratio
        assert result.rd == 1.0


class TestCheckBoltCombinedTensionAndShear:
    def test_returns_combined_check_result(self) -> None:
        result = check_bolt_combined_tension_and_shear(
            ft_sd=50_000.0, ft_rd=143_989.0, fv_sd=40_000.0, fv_rd=86_393.8
        )
        assert isinstance(result, BoltCombinedCheckResult)
        assert result.is_ok is True

    def test_is_not_ok_above_capacity(self) -> None:
        result = check_bolt_combined_tension_and_shear(
            ft_sd=140_000.0, ft_rd=143_989.0, fv_sd=80_000.0, fv_rd=86_393.8
        )
        assert result.is_ok is False


class TestWorkedExample:
    """Parafuso M20 hipotético, ASTM A325 (``fub=825`` MPa, valor
    hipotético ilustrativo, não extraído do Anexo A), combinação normal
    (``γa2=1,35``).

    Cálculo à mão (NBR 8800:2024, 6.3.2.2/6.3.3.1/6.3.3.2):
    - Ab = 0,25π·0,020² = 3,14159265e-4 m²
    - Abe = 0,75·Ab = 2,356194489e-4 m²
    - Ft,Rd = Abe·fub/γa2 = 2,356194489e-4·825e6/1,35 ≈ 143 989,0 N
    - Fv,Rd (plano de corte pela rosca) = 0,45·Ab·fub/γa2 ≈ 86 393,8 N

    Pressão de contato (6.3.3.3-a, deformação como limitação de
    projeto): parte ligada com ``fu=450`` MPa (aço-carbono comum,
    ilustrativo), ``ℓf=50`` mm, ``t=10`` mm:
    - termo de borda: 1,2·0,05·0,010·450e6/1,35 = 200 000,0 N
    - termo de diâmetro: 2,4·0,020·0,010·450e6/1,35 = 160 000,0 N
    - Fc,Rd = min(200 000,0; 160 000,0) = 160 000,0 N (governa o diâmetro)
    """

    _DB = 0.020
    _FUB = 825e6
    _GAMMA_A2 = 1.35

    def test_ft_rd_matches_hand_calculation(self) -> None:
        result = check_bolt_tension(
            ft_sd=1.0, bolt_diameter=self._DB, fub=self._FUB, gamma_a2=self._GAMMA_A2
        )
        assert result.force_rd == pytest.approx(143_989.0, rel=1e-4)

    def test_fv_rd_matches_hand_calculation(self) -> None:
        result = check_bolt_shear(
            fv_sd=1.0,
            bolt_diameter=self._DB,
            fub=self._FUB,
            gamma_a2=self._GAMMA_A2,
            threads_excluded_from_shear_plane=False,
        )
        assert result.force_rd == pytest.approx(86_393.8, rel=1e-4)

    def test_fc_rd_matches_hand_calculation(self) -> None:
        result = check_bolt_bearing(
            fc_sd=1.0,
            edge_or_hole_distance=0.05,
            thickness=0.010,
            fu=450e6,
            bolt_diameter=self._DB,
            gamma_a2=self._GAMMA_A2,
            deformation_is_design_limit=True,
        )
        assert result.force_rd == pytest.approx(160_000.0, rel=1e-6)
