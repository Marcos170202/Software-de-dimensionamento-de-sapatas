"""Testes de ``estrutura_metalica.model.section``."""

from __future__ import annotations

import math

import pytest

from estrutura_metalica.model import (
    CircularTubeSection,
    RectangularTubeSection,
    SectionShape,
    SteelSection,
)


def _generic_section(**overrides: float) -> SteelSection:
    defaults: dict[str, object] = dict(
        name="perfil de teste",
        shape=SectionShape.I_H,
        area=0.01,
        ix=1e-5,
        iy=5e-6,
        j=1e-7,
        depth=0.2,
    )
    defaults.update(overrides)
    return SteelSection(**defaults)  # type: ignore[arg-type]


def test_radii_of_gyration() -> None:
    section = _generic_section(area=0.01, ix=1e-5, iy=5e-6)
    assert section.rx == pytest.approx(math.sqrt(1e-5 / 0.01))
    assert section.ry == pytest.approx(math.sqrt(5e-6 / 0.01))


@pytest.mark.parametrize("field", ["area", "ix", "iy", "j", "depth"])
def test_rejects_non_positive_geometric_properties(field: str) -> None:
    with pytest.raises(ValueError):
        _generic_section(**{field: 0.0})


def test_rejects_negative_cw() -> None:
    with pytest.raises(ValueError):
        _generic_section(cw=-1.0)


def test_cw_none_is_allowed() -> None:
    section = _generic_section(cw=None)
    assert section.cw is None


def test_cw_positive_is_kept() -> None:
    section = _generic_section(cw=2e-8)
    assert section.cw == pytest.approx(2e-8)


class TestRectangularTubeSection:
    def test_square_tube_has_equal_ix_iy_by_symmetry(self) -> None:
        section = RectangularTubeSection.from_dimensions("TR 100x100x5", h=0.1, b=0.1, t=0.005)
        assert section.ix == pytest.approx(section.iy)

    def test_area_matches_outer_minus_inner_rectangle(self) -> None:
        h, b, t = 0.15, 0.10, 0.0063
        section = RectangularTubeSection.from_dimensions("TR 150x100x6.3", h=h, b=b, t=t)
        expected_area = h * b - (h - 2 * t) * (b - 2 * t)
        assert section.area == pytest.approx(expected_area)

    def test_square_tube_torsion_constant_matches_bredt_closed_form(self) -> None:
        h = b = 0.1
        t = 0.005
        section = RectangularTubeSection.from_dimensions("TR 100x100x5", h=h, b=b, t=t)
        # Para seção quadrada, o formato fechado de Bredt se reduz a
        # J = (h - t)^3 * t (linha média quadrada de lado h - t).
        expected_j = (h - t) ** 3 * t
        assert section.j == pytest.approx(expected_j)

    def test_shape_and_dimensions_are_recorded(self) -> None:
        section = RectangularTubeSection.from_dimensions("TR", h=0.2, b=0.12, t=0.008)
        assert section.shape is SectionShape.TUBE_RECTANGULAR
        assert (section.h, section.b, section.t) == pytest.approx((0.2, 0.12, 0.008))
        assert section.depth == pytest.approx(0.2)

    def test_rejects_non_positive_outer_dimensions(self) -> None:
        with pytest.raises(ValueError):
            RectangularTubeSection.from_dimensions("TR", h=0.0, b=0.1, t=0.005)
        with pytest.raises(ValueError):
            RectangularTubeSection.from_dimensions("TR", h=0.1, b=-0.1, t=0.005)

    def test_rejects_wall_thickness_too_large(self) -> None:
        with pytest.raises(ValueError):
            RectangularTubeSection.from_dimensions("TR", h=0.1, b=0.1, t=0.06)


class TestCircularTubeSection:
    def test_area_matches_annulus_formula(self) -> None:
        d, t = 0.1, 0.005
        section = CircularTubeSection.from_dimensions("TC 100x5", d=d, t=t)
        d_i = d - 2 * t
        expected_area = math.pi / 4.0 * (d**2 - d_i**2)
        assert section.area == pytest.approx(expected_area)

    def test_ix_equals_iy_by_axisymmetry(self) -> None:
        section = CircularTubeSection.from_dimensions("TC 100x5", d=0.1, t=0.005)
        assert section.ix == pytest.approx(section.iy)

    def test_torsion_constant_is_twice_the_moment_of_inertia(self) -> None:
        # Para seção circular (aberta ou fechada), J = Ix + Iy = 2*Ix
        # (axissimétrica), resultado exato (não é a aproximação de
        # Bredt usada nos tubos retangulares).
        section = CircularTubeSection.from_dimensions("TC 100x5", d=0.1, t=0.005)
        assert section.j == pytest.approx(2 * section.ix)

    def test_shape_and_dimensions_are_recorded(self) -> None:
        section = CircularTubeSection.from_dimensions("TC", d=0.15, t=0.01)
        assert section.shape is SectionShape.TUBE_CIRCULAR
        assert (section.d, section.t) == pytest.approx((0.15, 0.01))
        assert section.depth == pytest.approx(0.15)

    def test_rejects_non_positive_diameter(self) -> None:
        with pytest.raises(ValueError):
            CircularTubeSection.from_dimensions("TC", d=0.0, t=0.005)

    def test_rejects_wall_thickness_too_large(self) -> None:
        with pytest.raises(ValueError):
            CircularTubeSection.from_dimensions("TC", d=0.1, t=0.06)
