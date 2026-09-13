"""Testes de ``estrutura_metalica.model.legacy_profile_catalog``."""

from __future__ import annotations

import math

import pytest

from estrutura_metalica.model import (
    GERDAU_I_PROFILES,
    GERDAU_U_PROFILES,
    GerdauIProfile,
    GerdauUProfile,
    get_gerdau_i_profile,
    get_gerdau_u_profile,
)


def test_i_catalog_has_eight_profiles() -> None:
    assert len(GERDAU_I_PROFILES) == 8


def test_u_catalog_has_twelve_profiles() -> None:
    assert len(GERDAU_U_PROFILES) == 12


def test_get_gerdau_i_profile_matches_catalog_values() -> None:
    profile = get_gerdau_i_profile("I152x22")
    assert profile.depth * 1e3 == pytest.approx(152.4, rel=1e-6)
    assert profile.bf * 1e3 == pytest.approx(87.5, rel=1e-6)
    assert profile.tw * 1e3 == pytest.approx(8.71, rel=1e-6)
    assert profile.tf * 1e3 == pytest.approx(9.12, rel=1e-6)
    assert profile.area * 1e4 == pytest.approx(27.97, rel=1e-6)
    assert profile.ix * 1e8 == pytest.approx(1003.0, rel=1e-6)
    assert profile.wx * 1e6 == pytest.approx(131.7, rel=1e-6)
    assert profile.iy * 1e8 == pytest.approx(84.9, rel=1e-6)
    assert profile.wy * 1e6 == pytest.approx(19.4, rel=1e-6)
    assert profile.rt * 1e2 == pytest.approx(2.26, rel=1e-6)
    assert profile.mass_linear == pytest.approx(22.0, rel=1e-6)
    assert profile.bitola_imperial == '6"'


def test_get_gerdau_i_profile_radii_are_derived_from_ix_iy_and_area() -> None:
    # Confere que rx/ry batem com a coluna "r" impressa (linha sem
    # inconsistência conhecida — ver ATENÇÃO 3 no docstring do módulo).
    profile = get_gerdau_i_profile("I152x22")
    assert profile.rx * 1e2 == pytest.approx(5.99, rel=1e-2)
    assert profile.ry * 1e2 == pytest.approx(1.74, rel=1e-2)


def test_get_gerdau_u_profile_matches_catalog_values() -> None:
    profile = get_gerdau_u_profile("U203x17.1")
    assert profile.depth * 1e3 == pytest.approx(203.2, rel=1e-6)
    assert profile.bf * 1e3 == pytest.approx(57.40, rel=1e-6)
    assert profile.tw * 1e3 == pytest.approx(5.59, rel=1e-6)
    assert profile.tf * 1e3 == pytest.approx(9.50, rel=1e-6)
    assert profile.area * 1e4 == pytest.approx(21.68, rel=1e-6)
    assert profile.ix * 1e8 == pytest.approx(1344.30, rel=1e-6)
    assert profile.wx * 1e6 == pytest.approx(132.70, rel=1e-6)
    assert profile.iy * 1e8 == pytest.approx(54.10, rel=1e-6)
    assert profile.wy * 1e6 == pytest.approx(12.94, rel=1e-6)
    assert profile.x_centroid * 1e2 == pytest.approx(1.47, rel=1e-6)
    assert profile.mass_linear == pytest.approx(17.1, rel=1e-6)


def test_u_profile_ry_is_computed_not_the_flawed_catalog_ry_for_u8_bitola() -> None:
    # Para U 8" (17,10 e 20,50 kg/m), o "ry" impresso no catálogo
    # original (1,42 cm em ambas as linhas) é inconsistente com
    # Iy/Área — ver ATENÇÃO 3 no docstring do módulo. O ry calculado
    # aqui (sqrt(Iy/Área)) NÃO deve reproduzir esse valor.
    light = get_gerdau_u_profile("U203x17.1")
    heavy = get_gerdau_u_profile("U203x20.5")
    assert light.ry * 1e2 == pytest.approx(1.579, rel=1e-3)
    assert heavy.ry * 1e2 == pytest.approx(1.552, rel=1e-3)
    assert light.ry != pytest.approx(0.0142, rel=1e-2)


@pytest.mark.parametrize("name", list(GERDAU_I_PROFILES))
def test_i_profile_area_consistent_with_ix_across_catalog(name: str) -> None:
    profile = GERDAU_I_PROFILES[name]
    assert profile.ix == pytest.approx(profile.area * profile.rx**2, rel=1e-2)


@pytest.mark.parametrize("name", list(GERDAU_U_PROFILES))
def test_u_profile_wy_consistent_with_iy_via_flange_tip_distance(name: str) -> None:
    # Checagem cruzada independente da coluna "r" (sabidamente
    # inconsistente para duas linhas): Wy = Iy / (bf - x_centroid).
    # Tolerância folgada (15%) porque a linha U76x7,44 (kg/m) também
    # diverge mais que as demais (~12,6%) — os valores são mantidos
    # como impressos no catálogo (ver ATENÇÃO 3 no docstring do
    # módulo), esta checagem serve apenas para confirmar que não há
    # erro grosseiro de extração.
    profile = GERDAU_U_PROFILES[name]
    c_max = profile.bf - profile.x_centroid
    assert profile.wy == pytest.approx(profile.iy / c_max, rel=0.15)


def test_get_gerdau_i_profile_raises_key_error_with_full_listing() -> None:
    with pytest.raises(KeyError, match="I999x1"):
        get_gerdau_i_profile("I999x1")


def test_get_gerdau_u_profile_raises_key_error_with_full_listing() -> None:
    with pytest.raises(KeyError, match="U999x1"):
        get_gerdau_u_profile("U999x1")


def _generic_i_profile(**overrides: object) -> GerdauIProfile:
    defaults: dict[str, object] = dict(
        name="I76x8.48",
        bitola_imperial='3"',
        mass_linear=8.48,
        depth=0.0762,
        bf=0.05918,
        tw=0.00432,
        tf=0.0066,
        area=0.00108,
        ix=1.051e-06,
        wx=2.76e-05,
        iy=1.89e-07,
        wy=6.4e-06,
        rt=0.0145,
        source="teste",
    )
    defaults.update(overrides)
    return GerdauIProfile(**defaults)  # type: ignore[arg-type]


def _generic_u_profile(**overrides: object) -> GerdauUProfile:
    defaults: dict[str, object] = dict(
        name="U76x6.1",
        bitola_imperial='3"',
        mass_linear=6.1,
        depth=0.0762,
        bf=0.03581,
        tw=0.00432,
        tf=0.00693,
        area=0.000778,
        ix=6.89e-07,
        wx=1.81e-05,
        iy=8.2e-08,
        wy=3.32e-06,
        x_centroid=0.0111,
        source="teste",
    )
    defaults.update(overrides)
    return GerdauUProfile(**defaults)  # type: ignore[arg-type]


class TestGerdauIProfileValidation:
    @pytest.mark.parametrize(
        "field", ["mass_linear", "depth", "bf", "tw", "tf", "area", "ix", "wx", "iy", "wy", "rt"]
    )
    def test_rejects_non_positive_properties(self, field: str) -> None:
        with pytest.raises(ValueError):
            _generic_i_profile(**{field: 0.0})

    def test_radii_of_gyration(self) -> None:
        profile = _generic_i_profile()
        assert profile.rx == pytest.approx(math.sqrt(profile.ix / profile.area))
        assert profile.ry == pytest.approx(math.sqrt(profile.iy / profile.area))


class TestGerdauUProfileValidation:
    @pytest.mark.parametrize(
        "field",
        ["mass_linear", "depth", "bf", "tw", "tf", "area", "ix", "wx", "iy", "wy", "x_centroid"],
    )
    def test_rejects_non_positive_properties(self, field: str) -> None:
        with pytest.raises(ValueError):
            _generic_u_profile(**{field: 0.0})

    def test_rejects_centroid_not_smaller_than_flange_width(self) -> None:
        with pytest.raises(ValueError):
            _generic_u_profile(x_centroid=0.05, bf=0.05)
        with pytest.raises(ValueError):
            _generic_u_profile(x_centroid=0.06, bf=0.05)

    def test_radii_of_gyration(self) -> None:
        profile = _generic_u_profile()
        assert profile.rx == pytest.approx(math.sqrt(profile.ix / profile.area))
        assert profile.ry == pytest.approx(math.sqrt(profile.iy / profile.area))
