"""Testes de ``estrutura_metalica.normative.nbr8800.shear``.

:class:`TestWorkedExample` cobre os 3 trechos de ``Vrd`` (5.4.3.1.1)
com um perfil I hipotético, valores "expected" calculados
independentemente da chamada à função.
"""

from __future__ import annotations

import math

import pytest

from estrutura_metalica.normative.nbr8800 import (
    ShearCheckResult,
    check_shear_major_axis,
    effective_shear_area_major_axis,
    plastic_shear_force,
    shear_buckling_coefficient,
    shear_resistance,
)


class TestEffectiveShearAreaMajorAxis:
    def test_matches_formula(self) -> None:
        area = effective_shear_area_major_axis(total_depth=0.3, web_thickness=0.008)
        assert area == pytest.approx(0.0024)

    @pytest.mark.parametrize("field", ["total_depth", "web_thickness"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {"total_depth": 0.3, "web_thickness": 0.008}
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            effective_shear_area_major_axis(**kwargs)


class TestPlasticShearForce:
    def test_matches_formula(self) -> None:
        aw, fy = 0.0024, 345e6
        assert plastic_shear_force(aw, fy) == pytest.approx(0.60 * aw * fy)

    @pytest.mark.parametrize("field", ["effective_shear_area", "fy"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {"effective_shear_area": 0.0024, "fy": 345e6}
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            plastic_shear_force(**kwargs)


class TestShearBucklingCoefficient:
    def test_returns_5_34_without_stiffeners(self) -> None:
        assert shear_buckling_coefficient(web_clear_height=0.27, stiffener_spacing=None) == 5.34

    def test_returns_5_34_when_ratio_above_3(self) -> None:
        # a/h = 1.0/0.27 ≈ 3.7 > 3.
        assert shear_buckling_coefficient(web_clear_height=0.27, stiffener_spacing=1.0) == 5.34

    def test_matches_formula_when_stiffened(self) -> None:
        h, a = 0.27, 0.4
        expected = 5.0 + 5.0 / (a / h) ** 2
        assert shear_buckling_coefficient(web_clear_height=h, stiffener_spacing=a) == pytest.approx(
            expected
        )

    def test_rejects_non_positive_web_clear_height(self) -> None:
        with pytest.raises(ValueError):
            shear_buckling_coefficient(web_clear_height=0.0, stiffener_spacing=None)

    def test_rejects_non_positive_stiffener_spacing(self) -> None:
        with pytest.raises(ValueError):
            shear_buckling_coefficient(web_clear_height=0.27, stiffener_spacing=0.0)


class TestShearResistance:
    def test_plastic_branch(self) -> None:
        vpl = 500_000.0
        result = shear_resistance(
            plastic_shear_force=vpl,
            slenderness=30.0,
            slenderness_limit_p=60.0,
            slenderness_limit_r=90.0,
            gamma_a1=1.10,
        )
        assert result == pytest.approx(vpl / 1.10)

    def test_inelastic_branch(self) -> None:
        vpl, lam, lam_p, lam_r = 500_000.0, 75.0, 60.0, 90.0
        expected = (lam_p / lam) * vpl / 1.10
        result = shear_resistance(vpl, lam, lam_p, lam_r, gamma_a1=1.10)
        assert result == pytest.approx(expected)

    def test_elastic_branch(self) -> None:
        vpl, lam, lam_p, lam_r = 500_000.0, 120.0, 60.0, 90.0
        expected = 1.24 * (lam_p / lam) ** 2 * vpl / 1.10
        result = shear_resistance(vpl, lam, lam_p, lam_r, gamma_a1=1.10)
        assert result == pytest.approx(expected)

    def test_rejects_limit_r_below_limit_p(self) -> None:
        with pytest.raises(ValueError):
            shear_resistance(
                500_000.0, 50.0, slenderness_limit_p=90.0, slenderness_limit_r=60.0, gamma_a1=1.10
            )

    @pytest.mark.parametrize(
        "field",
        [
            "plastic_shear_force",
            "slenderness",
            "slenderness_limit_p",
            "slenderness_limit_r",
            "gamma_a1",
        ],
    )
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = dict(
            plastic_shear_force=500_000.0,
            slenderness=30.0,
            slenderness_limit_p=60.0,
            slenderness_limit_r=90.0,
            gamma_a1=1.10,
        )
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            shear_resistance(**kwargs)


class TestShearCheckResultValidation:
    def test_rejects_non_finite_vsd(self) -> None:
        with pytest.raises(ValueError):
            ShearCheckResult(vsd=float("nan"), vrd=1.0)

    @pytest.mark.parametrize("bad_value", [0.0, -1.0, float("nan"), float("inf")])
    def test_rejects_non_positive_or_non_finite_vrd(self, bad_value: float) -> None:
        with pytest.raises(ValueError):
            ShearCheckResult(vsd=0.0, vrd=bad_value)


class TestCheckShearMajorAxis:
    def test_rejects_non_finite_vsd(self) -> None:
        with pytest.raises(ValueError):
            check_shear_major_axis(
                vsd=float("nan"),
                total_depth=0.3,
                web_clear_height=0.27,
                web_thickness=0.008,
                fy=345e6,
                elastic_modulus=200_000e6,
                stiffener_spacing=None,
                gamma_a1=1.10,
            )

    def test_rejects_non_positive_elastic_modulus(self) -> None:
        with pytest.raises(ValueError):
            check_shear_major_axis(
                vsd=0.0,
                total_depth=0.3,
                web_clear_height=0.27,
                web_thickness=0.008,
                fy=345e6,
                elastic_modulus=0.0,
                stiffener_spacing=None,
                gamma_a1=1.10,
            )

    def test_rejects_web_clear_height_larger_than_total_depth(self) -> None:
        with pytest.raises(ValueError):
            check_shear_major_axis(
                vsd=0.0,
                total_depth=0.27,
                web_clear_height=0.3,
                web_thickness=0.008,
                fy=345e6,
                elastic_modulus=200_000e6,
                stiffener_spacing=None,
                gamma_a1=1.10,
            )


class TestWorkedExample:
    """Perfil I hipotético: d=0,3 m, h=0,27 m (alma livre), tw=0,008 m,
    aço ASTM A992 (fy=345 MPa, E=200 000 MPa), sem enrijecedores
    transversais, combinação normal (γa1=1,10).

    Cálculo à mão (NBR 8800:2024, 5.4.3.1):
    - Aw = d·tw = 0,3·0,008 = 0,0024 m²
    - Vpℓ = 0,60·Aw·fy = 0,60·0,0024·345e6 = 496 800 N
    - kv = 5,34 (sem enrijecedores)
    - λ = h/tw = 0,27/0,008 = 33,75
    - λp = 1,10·sqrt(5,34·200000e6/345e6) ≈ 61,20
    - λ ≤ λp → Vrd = Vpℓ/γa1 = 496800/1,10 ≈ 451 636,4 N (plastificação)
    """

    _D = 0.3
    _H = 0.27
    _TW = 0.008
    _FY = 345e6
    _E = 200_000e6

    def _expected_vrd(self) -> float:
        aw = self._D * self._TW
        vpl = 0.60 * aw * self._FY
        kv = 5.34
        lam = self._H / self._TW
        lam_p = 1.10 * math.sqrt(kv * self._E / self._FY)
        lam_r = 1.37 * math.sqrt(kv * self._E / self._FY)
        if lam <= lam_p:
            return vpl / 1.10
        if lam <= lam_r:
            return (lam_p / lam) * vpl / 1.10
        return 1.24 * (lam_p / lam) ** 2 * vpl / 1.10

    def test_plastification_governs(self) -> None:
        # Confere a premissa do exemplo (λ dentro do trecho de
        # plastificação) antes de comparar o resultado.
        lam = self._H / self._TW
        kv = 5.34
        lam_p = 1.10 * math.sqrt(kv * self._E / self._FY)
        assert lam <= lam_p

    def test_vrd_matches_hand_calculation(self) -> None:
        result = check_shear_major_axis(
            vsd=0.0,
            total_depth=self._D,
            web_clear_height=self._H,
            web_thickness=self._TW,
            fy=self._FY,
            elastic_modulus=self._E,
            stiffener_spacing=None,
            gamma_a1=1.10,
        )
        assert result.vrd == pytest.approx(self._expected_vrd(), rel=1e-9)
        assert result.vrd == pytest.approx(496_800.0 / 1.10, rel=1e-6)

    def test_is_ok_below_and_above_capacity(self) -> None:
        vrd = self._expected_vrd()
        low = check_shear_major_axis(
            vsd=1.0,
            total_depth=self._D,
            web_clear_height=self._H,
            web_thickness=self._TW,
            fy=self._FY,
            elastic_modulus=self._E,
            stiffener_spacing=None,
            gamma_a1=1.10,
        )
        high = check_shear_major_axis(
            vsd=vrd * 2,
            total_depth=self._D,
            web_clear_height=self._H,
            web_thickness=self._TW,
            fy=self._FY,
            elastic_modulus=self._E,
            stiffener_spacing=None,
            gamma_a1=1.10,
        )
        assert low.is_ok is True
        assert high.is_ok is False

    def test_slender_web_uses_elastic_buckling_branch(self) -> None:
        # Alma bem mais esbelta (tw menor) -> deve cair no 3o trecho.
        tw = 0.003
        result = check_shear_major_axis(
            vsd=0.0,
            total_depth=self._D,
            web_clear_height=self._H,
            web_thickness=tw,
            fy=self._FY,
            elastic_modulus=self._E,
            stiffener_spacing=None,
            gamma_a1=1.10,
        )
        kv = 5.34
        lam = self._H / tw
        lam_p = 1.10 * math.sqrt(kv * self._E / self._FY)
        lam_r = 1.37 * math.sqrt(kv * self._E / self._FY)
        assert lam > lam_r
        aw = self._D * tw
        vpl = 0.60 * aw * self._FY
        expected = 1.24 * (lam_p / lam) ** 2 * vpl / 1.10
        assert result.vrd == pytest.approx(expected, rel=1e-9)
