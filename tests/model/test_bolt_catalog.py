"""Testes de ``estrutura_metalica.model.bolt_catalog``."""

from __future__ import annotations

import pytest

from estrutura_metalica.model import STRUCTURAL_BOLT_CATALOG, StructuralBolt, get_structural_bolt


def test_catalog_has_nine_diameters_for_each_of_three_grades() -> None:
    assert len(STRUCTURAL_BOLT_CATALOG) == 27
    for grade in ("ASTM A325", "ASTM A490", "ASTM A307"):
        count = sum(1 for b in STRUCTURAL_BOLT_CATALOG.values() if b.astm_grade == grade)
        assert count == 9


@pytest.mark.parametrize(
    ("imperial", "expected_mm"),
    [
        ("1/2", 12.7),
        ("5/8", 15.875),
        ("3/4", 19.05),
        ("7/8", 22.225),
        ("1", 25.4),
        ("1.1/8", 28.575),
        ("1.1/4", 31.75),
        ("1.3/8", 34.925),
        ("1.1/2", 38.1),
    ],
)
def test_nominal_diameters_match_imperial_conversion(imperial: str, expected_mm: float) -> None:
    bolt = get_structural_bolt("ASTM A325", imperial)
    assert bolt.nominal_diameter * 1e3 == pytest.approx(expected_mm, rel=1e-9)


@pytest.mark.parametrize(
    ("imperial", "expected_fub_mpa"),
    [
        ("1/2", 827.370875),
        ("3/4", 827.370875),
        ("1", 827.370875),
        ("1.1/8", 723.949516),
        ("1.1/2", 723.949516),
    ],
)
def test_a325_fub_matches_two_astm_groups(imperial: str, expected_fub_mpa: float) -> None:
    bolt = get_structural_bolt("ASTM A325", imperial)
    assert bolt.fub / 1e6 == pytest.approx(expected_fub_mpa, rel=1e-6)


def test_a490_fub_matches_150_ksi_group() -> None:
    for imperial in ("1/2", "1", "1.1/2"):
        bolt = get_structural_bolt("ASTM A490", imperial)
        assert bolt.fub / 1e6 == pytest.approx(1034.213594, rel=1e-6)


def test_a307_fub_matches_catalog_414_mpa() -> None:
    bolt = get_structural_bolt("ASTM A307", "3/4")
    assert bolt.fub == pytest.approx(414e6)


def test_get_structural_bolt_accepts_trailing_quote() -> None:
    without_quote = get_structural_bolt("ASTM A325", "7/8")
    with_quote = get_structural_bolt("ASTM A325", '7/8"')
    assert without_quote == with_quote


def test_get_structural_bolt_raises_key_error_for_unknown_diameter() -> None:
    with pytest.raises(KeyError, match="9/8"):
        get_structural_bolt("ASTM A325", "9/8")


def test_get_structural_bolt_raises_key_error_for_unknown_grade() -> None:
    with pytest.raises(KeyError):
        get_structural_bolt("ASTM A999", "3/4")


def test_structural_bolt_rejects_non_positive_diameter() -> None:
    with pytest.raises(ValueError):
        StructuralBolt(name="x", nominal_diameter=0.0, fub=1e8, astm_grade="ASTM A325", source="s")


def test_structural_bolt_rejects_non_positive_fub() -> None:
    with pytest.raises(ValueError):
        StructuralBolt(
            name="x", nominal_diameter=0.02, fub=0.0, astm_grade="ASTM A325", source="s"
        )
