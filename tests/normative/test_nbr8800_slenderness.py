"""Testes de ``estrutura_metalica.normative.nbr8800.slenderness``."""

from __future__ import annotations

import pytest

from estrutura_metalica.normative.nbr8800 import (
    COMPRESSION_SLENDERNESS_LIMIT,
    TENSION_SLENDERNESS_LIMIT,
    SlendernessCheckResult,
    check_compression_slenderness,
    check_tension_slenderness,
    slenderness_ratio,
)


def test_limits_match_norm() -> None:
    assert TENSION_SLENDERNESS_LIMIT == 300.0
    assert COMPRESSION_SLENDERNESS_LIMIT == 200.0


class TestSlendernessCheckResultValidation:
    @pytest.mark.parametrize("bad_value", [0.0, -1.0, float("nan"), float("inf")])
    def test_rejects_non_positive_or_non_finite_ratio(self, bad_value: float) -> None:
        with pytest.raises(ValueError):
            SlendernessCheckResult(ratio=bad_value, limit=300.0)

    @pytest.mark.parametrize("bad_value", [0.0, -1.0, float("nan"), float("inf")])
    def test_rejects_non_positive_or_non_finite_limit(self, bad_value: float) -> None:
        with pytest.raises(ValueError):
            SlendernessCheckResult(ratio=100.0, limit=bad_value)


class TestSlendernessRatio:
    def test_matches_formula(self) -> None:
        assert slenderness_ratio(length=6.0, radius_of_gyration=0.05) == pytest.approx(120.0)

    @pytest.mark.parametrize("field", ["length", "radius_of_gyration"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {"length": 6.0, "radius_of_gyration": 0.05}
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            slenderness_ratio(**kwargs)


class TestCheckTensionSlenderness:
    def test_takes_larger_ratio_between_axes(self) -> None:
        result = check_tension_slenderness(
            length_x=6.0, radius_of_gyration_x=0.05, length_y=6.0, radius_of_gyration_y=0.03
        )
        # eixo y: 6/0.03=200 > eixo x: 6/0.05=120 -> governa y.
        assert result.ratio == pytest.approx(200.0)
        assert result.limit == TENSION_SLENDERNESS_LIMIT

    def test_within_limit(self) -> None:
        result = check_tension_slenderness(
            length_x=3.0, radius_of_gyration_x=0.05, length_y=3.0, radius_of_gyration_y=0.05
        )
        assert result.is_within_recommended_limit is True

    def test_exceeds_limit(self) -> None:
        result = check_tension_slenderness(
            length_x=100.0, radius_of_gyration_x=0.1, length_y=100.0, radius_of_gyration_y=0.1
        )
        assert result.ratio == pytest.approx(1000.0)
        assert result.is_within_recommended_limit is False


class TestCheckCompressionSlenderness:
    def test_within_limit(self) -> None:
        result = check_compression_slenderness(
            length_x=3.0, radius_of_gyration_x=0.05, length_y=3.0, radius_of_gyration_y=0.05
        )
        assert result.limit == COMPRESSION_SLENDERNESS_LIMIT
        assert result.is_within_recommended_limit is True

    def test_exceeds_limit(self) -> None:
        result = check_compression_slenderness(
            length_x=50.0, radius_of_gyration_x=0.1, length_y=50.0, radius_of_gyration_y=0.1
        )
        assert result.ratio == pytest.approx(500.0)
        assert result.is_within_recommended_limit is False

    def test_exact_limit_is_within(self) -> None:
        result = check_compression_slenderness(
            length_x=200.0, radius_of_gyration_x=1.0, length_y=200.0, radius_of_gyration_y=1.0
        )
        assert result.ratio == pytest.approx(200.0)
        assert result.is_within_recommended_limit is True
