"""Testes de ``estrutura_metalica.model.vallourec_catalog``."""

from __future__ import annotations

import math

import pytest

from estrutura_metalica.model import (
    VALLOUREC_CIRCULAR_HOLLOW_PROFILES,
    VALLOUREC_RECTANGULAR_HOLLOW_PROFILES,
    VALLOUREC_SQUARE_HOLLOW_PROFILES,
    CircularHollowProfile,
    RectangularHollowProfile,
    get_vallourec_circular_hollow_profile,
    get_vallourec_rectangular_hollow_profile,
    get_vallourec_square_hollow_profile,
)


def test_circular_catalog_has_expected_count() -> None:
    assert len(VALLOUREC_CIRCULAR_HOLLOW_PROFILES) == 562


def test_square_catalog_has_expected_count() -> None:
    assert len(VALLOUREC_SQUARE_HOLLOW_PROFILES) == 223


def test_rectangular_catalog_has_expected_count() -> None:
    assert len(VALLOUREC_RECTANGULAR_HOLLOW_PROFILES) == 450


def test_all_circular_entries_are_circular_hollow_profiles() -> None:
    for profile in VALLOUREC_CIRCULAR_HOLLOW_PROFILES.values():
        assert isinstance(profile, CircularHollowProfile)


def test_all_square_and_rectangular_entries_are_rectangular_hollow_profiles() -> None:
    for profile in (
        *VALLOUREC_SQUARE_HOLLOW_PROFILES.values(),
        *VALLOUREC_RECTANGULAR_HOLLOW_PROFILES.values(),
    ):
        assert isinstance(profile, RectangularHollowProfile)


def test_get_vallourec_circular_hollow_profile_matches_catalog_values() -> None:
    profile = get_vallourec_circular_hollow_profile("TC42.4x4")
    assert profile.d * 1e3 == pytest.approx(42.4, rel=1e-6)
    assert profile.t * 1e3 == pytest.approx(4.0, rel=1e-6)
    assert profile.area * 1e4 == pytest.approx(4.83, rel=1e-6)
    assert profile.ix * 1e8 == pytest.approx(8.99, rel=1e-6)
    assert profile.wel * 1e6 == pytest.approx(4.24, rel=1e-6)
    assert profile.wpl * 1e6 == pytest.approx(5.92, rel=1e-6)
    assert profile.j * 1e8 == pytest.approx(18.0, rel=1e-6)
    assert profile.ct * 1e6 == pytest.approx(8.48, rel=1e-6)
    assert profile.surface_area_per_length == pytest.approx(0.133, rel=1e-6)
    assert profile.mass_linear == pytest.approx(3.79, rel=1e-6)


def test_circular_hollow_profile_axisymmetric_ix_equals_iy() -> None:
    profile = get_vallourec_circular_hollow_profile("TC42.4x4")
    assert profile.ix == profile.iy


def test_get_vallourec_square_hollow_profile_matches_catalog_values() -> None:
    profile = get_vallourec_square_hollow_profile("TQ60x5")
    assert profile.h * 1e3 == pytest.approx(60.0, rel=1e-6)
    assert profile.b * 1e3 == pytest.approx(60.0, rel=1e-6)
    assert profile.t * 1e3 == pytest.approx(5.0, rel=1e-6)
    assert profile.area * 1e4 == pytest.approx(10.7, rel=1e-6)
    assert profile.ix * 1e8 == pytest.approx(53.3, rel=1e-6)
    assert profile.welx * 1e6 == pytest.approx(17.8, rel=1e-6)
    assert profile.wplx * 1e6 == pytest.approx(21.9, rel=1e-6)
    assert profile.mass_linear == pytest.approx(8.42, rel=1e-6)


def test_square_hollow_profile_symmetric_properties_match_both_axes() -> None:
    profile = get_vallourec_square_hollow_profile("TQ60x5")
    assert profile.ix == profile.iy
    assert profile.welx == profile.wely
    assert profile.wplx == profile.wply


def test_get_vallourec_rectangular_hollow_profile_matches_catalog_values() -> None:
    # Bitola que teve a linha "H x B" dividida em duas no PDF original
    # (ver ATENÇÃO no docstring do módulo) - conferida especificamente
    # para garantir que a correção de extração está correta.
    profile = get_vallourec_rectangular_hollow_profile("TR180x100x5")
    assert profile.h * 1e3 == pytest.approx(180.0, rel=1e-6)
    assert profile.b * 1e3 == pytest.approx(100.0, rel=1e-6)
    assert profile.t * 1e3 == pytest.approx(5.0, rel=1e-6)
    assert profile.area * 1e4 == pytest.approx(26.7, rel=1e-6)
    assert profile.mass_linear == pytest.approx(21.0, rel=1e-6)
    assert profile.ix * 1e8 == pytest.approx(1150.0, rel=1e-6)
    assert profile.iy * 1e8 == pytest.approx(460.0, rel=1e-6)
    assert profile.welx * 1e6 == pytest.approx(128.0, rel=1e-6)
    assert profile.wely * 1e6 == pytest.approx(92.0, rel=1e-6)


def test_rectangular_180x80_bitola_is_not_corrupted_by_the_180x100_split() -> None:
    # Antes da correção, as 8 linhas de "180 x 100" ficavam
    # incorretamente atribuídas a "180 x 80" (ver ATENÇÃO no
    # docstring do módulo). Confere a linha real de 180x80.
    profile = get_vallourec_rectangular_hollow_profile("TR180x80x5.6")
    assert profile.h * 1e3 == pytest.approx(180.0, rel=1e-6)
    assert profile.b * 1e3 == pytest.approx(80.0, rel=1e-6)
    assert profile.mass_linear == pytest.approx(21.6, rel=1e-6)
    assert profile.ix * 1e8 == pytest.approx(1100.0, rel=1e-6)


def test_get_vallourec_circular_hollow_profile_raises_key_error() -> None:
    with pytest.raises(KeyError, match="TC999x1"):
        get_vallourec_circular_hollow_profile("TC999x1")


def test_get_vallourec_square_hollow_profile_raises_key_error() -> None:
    with pytest.raises(KeyError, match="TQ999x1"):
        get_vallourec_square_hollow_profile("TQ999x1")


def test_get_vallourec_rectangular_hollow_profile_raises_key_error() -> None:
    with pytest.raises(KeyError, match="TR999x999x1"):
        get_vallourec_rectangular_hollow_profile("TR999x999x1")


@pytest.mark.parametrize("name", list(VALLOUREC_CIRCULAR_HOLLOW_PROFILES))
def test_circular_area_matches_exact_annulus_formula_across_catalog(name: str) -> None:
    # Checagem cruzada com a fórmula EXATA do anel (mesma usada por
    # CircularTubeSection.from_dimensions) - valida tanto a extração
    # quanto a fórmula já implementada no pacote.
    profile = VALLOUREC_CIRCULAR_HOLLOW_PROFILES[name]
    d_i = profile.d - 2 * profile.t
    exact_area = math.pi / 4.0 * (profile.d**2 - d_i**2)
    assert profile.area == pytest.approx(exact_area, rel=0.03)


@pytest.mark.parametrize("name", list(VALLOUREC_CIRCULAR_HOLLOW_PROFILES))
def test_circular_wel_consistent_with_ix_and_diameter_across_catalog(name: str) -> None:
    # Checagem cruzada INDEPENDENTE (usa colunas diferentes de
    # catálogo, ao contrário de rx=sqrt(Ix/Área), que seria tautológico
    # já que rx não é um valor de catálogo armazenado): Wel = Ix/(D/2),
    # distância da fibra extrema ao eixo centroidal de uma seção
    # fechada axissimétrica.
    profile = VALLOUREC_CIRCULAR_HOLLOW_PROFILES[name]
    assert profile.wel == pytest.approx(profile.ix / (profile.d / 2.0), rel=0.03)


@pytest.mark.parametrize("name", list(VALLOUREC_SQUARE_HOLLOW_PROFILES))
def test_square_welx_consistent_with_ix_and_side_across_catalog(name: str) -> None:
    profile = VALLOUREC_SQUARE_HOLLOW_PROFILES[name]
    assert profile.welx == pytest.approx(profile.ix / (profile.h / 2.0), rel=0.03)


@pytest.mark.parametrize("name", list(VALLOUREC_RECTANGULAR_HOLLOW_PROFILES))
def test_rectangular_welx_wely_consistent_with_inertia_and_dimensions_across_catalog(
    name: str,
) -> None:
    profile = VALLOUREC_RECTANGULAR_HOLLOW_PROFILES[name]
    assert profile.welx == pytest.approx(profile.ix / (profile.h / 2.0), rel=0.03)
    assert profile.wely == pytest.approx(profile.iy / (profile.b / 2.0), rel=0.03)
