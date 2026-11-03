"""Testes de ``estrutura_metalica.normative.nbr8800.combined_forces``.

:class:`TestWorkedExample` cobre os dois ramos da equação de interação
(5.5.1.2-a e -b) com valores calculados à mão.
"""

from __future__ import annotations

import pytest

from estrutura_metalica.normative.nbr8800 import (
    CombinedForcesCheckResult,
    axial_bending_interaction_ratio,
    check_axial_and_bending_interaction,
)


class TestAxialBendingInteractionRatio:
    def test_branch_a_when_ratio_n_at_least_0_2(self) -> None:
        n_sd, n_rd = 300.0, 1000.0  # Nsd/Nrd = 0,3 >= 0,2
        mx_sd, mx_rd = 50.0, 200.0
        my_sd, my_rd = 20.0, 100.0
        expected = n_sd / n_rd + (8.0 / 9.0) * (mx_sd / mx_rd + my_sd / my_rd)
        result = axial_bending_interaction_ratio(n_sd, n_rd, mx_sd, mx_rd, my_sd, my_rd)
        assert result == pytest.approx(expected)

    def test_branch_b_when_ratio_n_below_0_2(self) -> None:
        n_sd, n_rd = 100.0, 1000.0  # Nsd/Nrd = 0,1 < 0,2
        mx_sd, mx_rd = 50.0, 200.0
        my_sd, my_rd = 20.0, 100.0
        expected = n_sd / (2.0 * n_rd) + (mx_sd / mx_rd + my_sd / my_rd)
        result = axial_bending_interaction_ratio(n_sd, n_rd, mx_sd, mx_rd, my_sd, my_rd)
        assert result == pytest.approx(expected)

    def test_boundary_ratio_n_exactly_0_2_uses_branch_a(self) -> None:
        n_sd, n_rd = 200.0, 1000.0  # Nsd/Nrd = 0,2 exatamente -> ramo a)
        mx_sd, mx_rd = 0.0, 200.0
        my_sd, my_rd = 0.0, 100.0
        expected_a = n_sd / n_rd + (8.0 / 9.0) * (mx_sd / mx_rd + my_sd / my_rd)
        result = axial_bending_interaction_ratio(n_sd, n_rd, mx_sd, mx_rd, my_sd, my_rd)
        assert result == pytest.approx(expected_a)

    def test_accepts_zero_moment_in_one_axis(self) -> None:
        # Barra sem momento em torno de y (flexão só em x).
        result = axial_bending_interaction_ratio(
            n_sd=100.0, n_rd=1000.0, mx_sd=50.0, mx_rd=200.0, my_sd=0.0, my_rd=100.0
        )
        assert result > 0.0

    def test_accepts_zero_axial_force(self) -> None:
        # Barra fletida pura, sem força axial.
        result = axial_bending_interaction_ratio(
            n_sd=0.0, n_rd=1000.0, mx_sd=50.0, mx_rd=200.0, my_sd=20.0, my_rd=100.0
        )
        assert result > 0.0

    @pytest.mark.parametrize("field", ["n_sd", "mx_sd", "my_sd"])
    def test_rejects_negative_magnitudes(self, field: str) -> None:
        kwargs = dict(n_sd=100.0, n_rd=1000.0, mx_sd=50.0, mx_rd=200.0, my_sd=20.0, my_rd=100.0)
        kwargs[field] = -1.0
        with pytest.raises(ValueError):
            axial_bending_interaction_ratio(**kwargs)

    @pytest.mark.parametrize("field", ["n_sd", "mx_sd", "my_sd"])
    def test_rejects_non_finite_magnitudes(self, field: str) -> None:
        kwargs = dict(n_sd=100.0, n_rd=1000.0, mx_sd=50.0, mx_rd=200.0, my_sd=20.0, my_rd=100.0)
        kwargs[field] = float("nan")
        with pytest.raises(ValueError):
            axial_bending_interaction_ratio(**kwargs)

    @pytest.mark.parametrize("field", ["n_rd", "mx_rd", "my_rd"])
    def test_rejects_non_positive_resistances(self, field: str) -> None:
        kwargs = dict(n_sd=100.0, n_rd=1000.0, mx_sd=50.0, mx_rd=200.0, my_sd=20.0, my_rd=100.0)
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            axial_bending_interaction_ratio(**kwargs)


class TestCombinedForcesCheckResultValidation:
    _VALID = dict(
        n_sd=100.0,
        n_rd=1000.0,
        mx_sd=50.0,
        mx_rd=200.0,
        my_sd=20.0,
        my_rd=100.0,
        interaction_ratio=0.5,
    )

    def test_valid_construction(self) -> None:
        result = CombinedForcesCheckResult(**self._VALID)
        assert result.interaction_ratio == pytest.approx(0.5)

    @pytest.mark.parametrize("field", ["n_sd", "mx_sd", "my_sd"])
    def test_rejects_negative_magnitudes(self, field: str) -> None:
        kwargs = dict(self._VALID)
        kwargs[field] = -1.0
        with pytest.raises(ValueError):
            CombinedForcesCheckResult(**kwargs)

    @pytest.mark.parametrize("field", ["n_rd", "mx_rd", "my_rd"])
    def test_rejects_non_positive_resistances(self, field: str) -> None:
        kwargs = dict(self._VALID)
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            CombinedForcesCheckResult(**kwargs)

    @pytest.mark.parametrize("bad_value", [-1.0, float("nan"), float("inf")])
    def test_rejects_invalid_interaction_ratio(self, bad_value: float) -> None:
        kwargs = dict(self._VALID)
        kwargs["interaction_ratio"] = bad_value
        with pytest.raises(ValueError):
            CombinedForcesCheckResult(**kwargs)

    def test_sd_and_rd_aliases(self) -> None:
        result = CombinedForcesCheckResult(**self._VALID)
        assert result.sd == result.interaction_ratio
        assert result.rd == 1.0


class TestCheckAxialAndBendingInteraction:
    def test_is_ok_when_ratio_at_or_below_one(self) -> None:
        result = check_axial_and_bending_interaction(
            n_sd=100.0, n_rd=1000.0, mx_sd=50.0, mx_rd=500.0, my_sd=20.0, my_rd=500.0
        )
        assert result.is_ok is True
        assert result.utilization == pytest.approx(result.interaction_ratio)

    def test_is_not_ok_when_ratio_above_one(self) -> None:
        result = check_axial_and_bending_interaction(
            n_sd=900.0, n_rd=1000.0, mx_sd=180.0, mx_rd=200.0, my_sd=90.0, my_rd=100.0
        )
        assert result.is_ok is False
        assert result.interaction_ratio > 1.0

    def test_returns_combined_forces_check_result(self) -> None:
        result = check_axial_and_bending_interaction(
            n_sd=0.0, n_rd=1000.0, mx_sd=0.0, mx_rd=200.0, my_sd=0.0, my_rd=100.0
        )
        assert isinstance(result, CombinedForcesCheckResult)
        assert result.interaction_ratio == pytest.approx(0.0)
        assert result.is_ok is True


class TestWorkedExample:
    """Valores hipotéticos calculados à mão para os dois ramos de
    5.5.1.2.
    """

    def test_branch_a_worked_example(self) -> None:
        # Nsd/Nrd = 500/1000 = 0,5 >= 0,2 -> ramo a).
        n_sd, n_rd = 500.0, 1000.0
        mx_sd, mx_rd = 100.0, 400.0  # Mx,sd/Mx,rd = 0,25
        my_sd, my_rd = 50.0, 200.0  # My,sd/My,rd = 0,25
        # ratio = 0,5 + (8/9)*(0,25+0,25) = 0,5 + (8/9)*0,5 = 0,5+0,44444...
        expected = 0.5 + (8.0 / 9.0) * 0.5
        result = check_axial_and_bending_interaction(n_sd, n_rd, mx_sd, mx_rd, my_sd, my_rd)
        assert result.interaction_ratio == pytest.approx(expected, rel=1e-9)
        assert result.interaction_ratio == pytest.approx(0.9444444444444444, rel=1e-9)
        assert result.is_ok is True

    def test_branch_b_worked_example(self) -> None:
        # Nsd/Nrd = 100/1000 = 0,1 < 0,2 -> ramo b).
        n_sd, n_rd = 100.0, 1000.0
        mx_sd, mx_rd = 100.0, 400.0  # Mx,sd/Mx,rd = 0,25
        my_sd, my_rd = 50.0, 200.0  # My,sd/My,rd = 0,25
        # ratio = 0,1/2 + (0,25+0,25) = 0,05 + 0,5 = 0,55
        expected = 0.05 + 0.5
        result = check_axial_and_bending_interaction(n_sd, n_rd, mx_sd, mx_rd, my_sd, my_rd)
        assert result.interaction_ratio == pytest.approx(expected, rel=1e-9)
        assert result.interaction_ratio == pytest.approx(0.55, rel=1e-9)
        assert result.is_ok is True
