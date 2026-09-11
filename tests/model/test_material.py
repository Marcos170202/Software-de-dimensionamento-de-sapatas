"""Testes de ``estrutura_metalica.model.SteelMaterial`` e do catálogo."""

from __future__ import annotations

import pytest

from estrutura_metalica.model import (
    ASTM_A36,
    ASTM_A572_GR50,
    ASTM_A992,
    STEEL_MATERIAL_CATALOG,
    SteelMaterial,
)


def test_shear_modulus_computed_from_e_and_poisson() -> None:
    mat = SteelMaterial(name="teste", fy=250e6, fu=400e6, e=200_000e6, poisson_ratio=0.3)
    expected_g = 200_000e6 / (2 * 1.3)
    assert mat.g == pytest.approx(expected_g)
    assert mat.shear_modulus == pytest.approx(expected_g)


def test_explicit_g_is_kept() -> None:
    mat = SteelMaterial(name="teste", fy=250e6, fu=400e6, e=200_000e6, g=77_000e6)
    assert mat.g == pytest.approx(77_000e6)


def test_rejects_non_positive_fy() -> None:
    with pytest.raises(ValueError):
        SteelMaterial(name="teste", fy=0.0, fu=400e6, e=200_000e6)


def test_rejects_non_positive_fu() -> None:
    with pytest.raises(ValueError):
        SteelMaterial(name="teste", fy=250e6, fu=-1.0, e=200_000e6)


def test_rejects_fu_below_fy() -> None:
    with pytest.raises(ValueError, match="material 'teste' inconsistente"):
        SteelMaterial(name="teste", fy=400e6, fu=250e6, e=200_000e6)


def test_rejects_non_positive_e() -> None:
    with pytest.raises(ValueError):
        SteelMaterial(name="teste", fy=250e6, fu=400e6, e=0.0)


@pytest.mark.parametrize("poisson", [-1.0, 0.5, 0.6])
def test_rejects_implausible_poisson_ratio(poisson: float) -> None:
    with pytest.raises(ValueError):
        SteelMaterial(name="teste", fy=250e6, fu=400e6, e=200_000e6, poisson_ratio=poisson)


def test_rejects_non_positive_density() -> None:
    with pytest.raises(ValueError):
        SteelMaterial(name="teste", fy=250e6, fu=400e6, e=200_000e6, density=0.0)


def test_rejects_non_positive_explicit_g() -> None:
    with pytest.raises(ValueError):
        SteelMaterial(name="teste", fy=250e6, fu=400e6, e=200_000e6, g=-1.0)


@pytest.mark.parametrize("material", [ASTM_A36, ASTM_A572_GR50, ASTM_A992])
def test_catalog_materials_are_valid(material: SteelMaterial) -> None:
    assert material.fu >= material.fy > 0
    assert material.e == pytest.approx(200_000e6)


def test_catalog_dict_is_keyed_by_name() -> None:
    assert STEEL_MATERIAL_CATALOG["ASTM A36"] is ASTM_A36
    assert STEEL_MATERIAL_CATALOG["ASTM A572 Gr. 50"] is ASTM_A572_GR50
    assert STEEL_MATERIAL_CATALOG["ASTM A992"] is ASTM_A992
    assert len(STEEL_MATERIAL_CATALOG) == 3
