"""Testes de ``estrutura_metalica.model.section``."""

from __future__ import annotations

import math

import pytest

from estrutura_metalica.model import (
    CircularTubeSection,
    IProfileSection,
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


def _generic_i_profile(**overrides: object) -> IProfileSection:
    defaults: dict[str, object] = dict(
        name="W310x97.0",
        shape=SectionShape.I_H,
        area=0.01236,
        ix=0.00022284,
        iy=7.286e-05,
        j=9.212e-07,
        depth=0.308,
        cw=1.558682e-06,
        bf=0.305,
        tw=0.0099,
        tf=0.0154,
        h=0.245,
        wx=0.001447,
        zx=0.0015942,
        wy=0.0004778,
        zy=0.000725,
        rt=0.0838,
        mass_linear=97.0,
        source="teste",
    )
    defaults.update(overrides)
    return IProfileSection(**defaults)  # type: ignore[arg-type]


class TestIProfileSection:
    def test_valid_profile_keeps_all_fields(self) -> None:
        profile = _generic_i_profile()
        assert profile.shape is SectionShape.I_H
        assert profile.bf == pytest.approx(0.305)
        assert profile.tw == pytest.approx(0.0099)
        assert profile.tf == pytest.approx(0.0154)
        assert profile.h == pytest.approx(0.245)
        assert profile.wx == pytest.approx(0.001447)
        assert profile.zx == pytest.approx(0.0015942)
        assert profile.wy == pytest.approx(0.0004778)
        assert profile.zy == pytest.approx(0.000725)
        assert profile.rt == pytest.approx(0.0838)
        assert profile.mass_linear == pytest.approx(97.0)
        assert profile.source == "teste"

    def test_inherits_steel_section_validation(self) -> None:
        # area=0.0 deve disparar a validação de SteelSection.__post_init__,
        # chamada explicitamente (não via super()) por IProfileSection.
        with pytest.raises(ValueError):
            _generic_i_profile(area=0.0)

    def test_radii_of_gyration_use_inherited_properties(self) -> None:
        profile = _generic_i_profile()
        assert profile.rx == pytest.approx(math.sqrt(profile.ix / profile.area))
        assert profile.ry == pytest.approx(math.sqrt(profile.iy / profile.area))

    @pytest.mark.parametrize(
        "field", ["bf", "tw", "tf", "h", "wx", "zx", "wy", "zy", "rt", "mass_linear"]
    )
    def test_rejects_non_positive_extra_properties(self, field: str) -> None:
        with pytest.raises(ValueError):
            _generic_i_profile(**{field: 0.0})

    def test_rejects_web_clear_height_not_smaller_than_depth(self) -> None:
        with pytest.raises(ValueError):
            _generic_i_profile(h=0.308, depth=0.308)
        with pytest.raises(ValueError):
            _generic_i_profile(h=0.4, depth=0.308)
