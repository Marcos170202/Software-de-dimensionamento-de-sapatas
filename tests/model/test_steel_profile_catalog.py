"""Testes de ``estrutura_metalica.model.steel_profile_catalog``."""

from __future__ import annotations

import pytest

from estrutura_metalica.model import (
    GERDAU_W_H_PROFILES,
    IProfileSection,
    SectionShape,
    get_gerdau_w_h_profile,
)


def test_catalog_has_expected_number_of_profiles() -> None:
    # Tabela impressa do folder Gerdau (revisão 11/2018): W150 a W610,
    # incluindo variantes HP — 107 bitolas extraídas.
    assert len(GERDAU_W_H_PROFILES) == 107


def test_all_entries_are_i_profile_sections_with_i_h_shape() -> None:
    for profile in GERDAU_W_H_PROFILES.values():
        assert isinstance(profile, IProfileSection)
        assert profile.shape is SectionShape.I_H


def test_get_gerdau_w_h_profile_returns_expected_w310x97() -> None:
    profile = get_gerdau_w_h_profile("W310x97.0")
    # Conferência direta contra a tabela impressa do catálogo (em
    # unidades de catálogo: mm/cm²/cm⁴/cm³/cm/kg-m).
    assert profile.depth * 1e3 == pytest.approx(308.0, rel=1e-6)
    assert profile.bf * 1e3 == pytest.approx(305.0, rel=1e-6)
    assert profile.tw * 1e3 == pytest.approx(9.9, rel=1e-6)
    assert profile.tf * 1e3 == pytest.approx(15.4, rel=1e-6)
    assert profile.h * 1e3 == pytest.approx(245.0, rel=1e-6)
    assert profile.area * 1e4 == pytest.approx(123.6, rel=1e-6)
    assert profile.ix * 1e8 == pytest.approx(22284.0, rel=1e-6)
    assert profile.iy * 1e8 == pytest.approx(7286.0, rel=1e-6)
    assert profile.wx * 1e6 == pytest.approx(1447.0, rel=1e-6)
    assert profile.zx * 1e6 == pytest.approx(1594.2, rel=1e-6)
    assert profile.wy * 1e6 == pytest.approx(477.8, rel=1e-6)
    assert profile.zy * 1e6 == pytest.approx(725.0, rel=1e-6)
    assert profile.rt * 1e2 == pytest.approx(8.38, rel=1e-6)
    assert profile.j * 1e8 == pytest.approx(92.12, rel=1e-6)
    assert profile.cw * 1e12 == pytest.approx(1_558_682.0, rel=1e-6)
    assert profile.mass_linear == pytest.approx(97.0, rel=1e-6)


def test_get_gerdau_w_h_profile_smallest_and_largest_profiles() -> None:
    smallest = get_gerdau_w_h_profile("W150x13.0")
    assert smallest.depth * 1e3 == pytest.approx(148.0, rel=1e-6)
    assert smallest.area * 1e4 == pytest.approx(16.6, rel=1e-6)

    largest = get_gerdau_w_h_profile("W610x217.0")
    assert largest.depth * 1e3 == pytest.approx(628.0, rel=1e-6)
    assert largest.area * 1e4 == pytest.approx(278.4, rel=1e-6)


def test_get_gerdau_w_h_profile_hp_variant() -> None:
    profile = get_gerdau_w_h_profile("HP310x110.0")
    assert profile.depth * 1e3 == pytest.approx(308.0, rel=1e-6)
    assert profile.bf * 1e3 == pytest.approx(310.0, rel=1e-6)


def test_get_gerdau_w_h_profile_raises_key_error_for_unknown_name() -> None:
    with pytest.raises(KeyError, match="W310x999.0"):
        get_gerdau_w_h_profile("W310x999.0")


def test_get_gerdau_w_h_profile_error_lists_same_series_profiles() -> None:
    with pytest.raises(KeyError, match="W310x97.0"):
        get_gerdau_w_h_profile("W310x999.0")


@pytest.mark.parametrize("name", list(GERDAU_W_H_PROFILES))
def test_area_is_consistent_with_ix_and_rx_for_every_profile(name: str) -> None:
    # Checagem cruzada: Ix = Área * rx² e Iy = Área * ry², para todas
    # as 107 bitolas — confere a extração/conversão de unidades
    # (mm/cm²/cm⁴ -> SI) contra a relação geométrica rx = sqrt(Ix/Área).
    profile = GERDAU_W_H_PROFILES[name]
    assert profile.ix == pytest.approx(profile.area * profile.rx**2, rel=1e-3)
    assert profile.iy == pytest.approx(profile.area * profile.ry**2, rel=1e-3)


@pytest.mark.parametrize("name", list(GERDAU_W_H_PROFILES))
def test_web_clear_height_smaller_than_total_depth_for_every_profile(name: str) -> None:
    profile = GERDAU_W_H_PROFILES[name]
    assert profile.h < profile.depth
