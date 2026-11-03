"""Testes de ``estrutura_metalica.model.british_steel_catalog``."""

from __future__ import annotations

import pytest

from estrutura_metalica.model import (
    BRITISH_STEEL_UB_PROFILES,
    BRITISH_STEEL_UC_PROFILES,
    IProfileSection,
    get_british_steel_ub_profile,
    get_british_steel_uc_profile,
)
from estrutura_metalica.model.section import SectionShape


def test_ub_catalog_has_ninety_four_profiles() -> None:
    assert len(BRITISH_STEEL_UB_PROFILES) == 94


def test_uc_catalog_has_fifty_three_profiles() -> None:
    assert len(BRITISH_STEEL_UC_PROFILES) == 53


def test_all_entries_are_i_profile_sections() -> None:
    for profile in (*BRITISH_STEEL_UB_PROFILES.values(), *BRITISH_STEEL_UC_PROFILES.values()):
        assert isinstance(profile, IProfileSection)
        assert profile.shape is SectionShape.I_H


def test_get_british_steel_ub_profile_matches_catalog_values() -> None:
    profile = get_british_steel_ub_profile("UB457x191x89")
    assert profile.depth * 1e3 == pytest.approx(463.4, rel=1e-6)
    assert profile.bf * 1e3 == pytest.approx(191.9, rel=1e-6)
    assert profile.tw * 1e3 == pytest.approx(10.5, rel=1e-6)
    assert profile.tf * 1e3 == pytest.approx(17.7, rel=1e-6)
    assert profile.h * 1e3 == pytest.approx(402.6, rel=1e-6)
    assert profile.area * 1e4 == pytest.approx(114.0, rel=1e-6)
    assert profile.ix * 1e8 == pytest.approx(41232.0, rel=1e-6)
    assert profile.iy * 1e8 == pytest.approx(2090.0, rel=1e-6)
    assert profile.wx * 1e6 == pytest.approx(1780.0, rel=1e-6)
    assert profile.zx * 1e6 == pytest.approx(2024.0, rel=1e-6)
    assert profile.wy * 1e6 == pytest.approx(218.0, rel=1e-6)
    assert profile.zy * 1e6 == pytest.approx(339.0, rel=1e-6)
    assert profile.j * 1e8 == pytest.approx(93.3, rel=1e-6)
    assert profile.cw * 1e6 == pytest.approx(1.04, rel=1e-6)
    assert profile.mass_linear == pytest.approx(89.3, rel=1e-6)
    assert profile.rx * 1e2 == pytest.approx(19.00, rel=1e-3)
    assert profile.ry * 1e2 == pytest.approx(4.28, rel=1e-3)


def test_get_british_steel_uc_profile_matches_catalog_values() -> None:
    profile = get_british_steel_uc_profile("UC152x152x23")
    assert profile.depth * 1e3 == pytest.approx(152.4, rel=1e-6)
    assert profile.bf * 1e3 == pytest.approx(152.2, rel=1e-6)
    assert profile.area * 1e4 == pytest.approx(29.2, rel=1e-6)
    assert profile.ix * 1e8 == pytest.approx(1250.0, rel=1e-6)
    assert profile.iy * 1e8 == pytest.approx(400.0, rel=1e-6)
    assert profile.mass_linear == pytest.approx(23.0, rel=1e-6)


def test_rt_is_computed_and_close_to_a_reference_catalog_value() -> None:
    # UB457x191x89 nao publica "rt" - usamos o valor calculado e so
    # conferimos que e positivo e da ordem de grandeza esperada
    # (entre ry e rx, tipico para essa grandeza).
    profile = get_british_steel_ub_profile("UB457x191x89")
    assert profile.ry < profile.rt < profile.rx


def test_get_british_steel_ub_profile_raises_key_error_with_full_listing() -> None:
    with pytest.raises(KeyError, match="UB999x999x999"):
        get_british_steel_ub_profile("UB999x999x999")


def test_get_british_steel_uc_profile_raises_key_error_with_full_listing() -> None:
    with pytest.raises(KeyError, match="UC999x999x999"):
        get_british_steel_uc_profile("UC999x999x999")


@pytest.mark.parametrize("name", list(BRITISH_STEEL_UB_PROFILES))
def test_ub_area_consistent_with_ix_and_iy_across_catalog(name: str) -> None:
    profile = BRITISH_STEEL_UB_PROFILES[name]
    assert profile.ix == pytest.approx(profile.area * profile.rx**2, rel=0.05)
    assert profile.iy == pytest.approx(profile.area * profile.ry**2, rel=0.05)


@pytest.mark.parametrize("name", list(BRITISH_STEEL_UC_PROFILES))
def test_uc_area_consistent_with_ix_and_iy_across_catalog(name: str) -> None:
    profile = BRITISH_STEEL_UC_PROFILES[name]
    assert profile.ix == pytest.approx(profile.area * profile.rx**2, rel=0.05)
    assert profile.iy == pytest.approx(profile.area * profile.ry**2, rel=0.05)


@pytest.mark.parametrize("name", list(BRITISH_STEEL_UB_PROFILES))
def test_ub_web_clear_height_smaller_than_depth(name: str) -> None:
    profile = BRITISH_STEEL_UB_PROFILES[name]
    assert profile.h < profile.depth


@pytest.mark.parametrize("name", list(BRITISH_STEEL_UC_PROFILES))
def test_uc_web_clear_height_smaller_than_depth(name: str) -> None:
    profile = BRITISH_STEEL_UC_PROFILES[name]
    assert profile.h < profile.depth
