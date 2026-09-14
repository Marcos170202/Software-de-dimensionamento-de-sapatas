"""Testes de ``estrutura_metalica.normative.nbr8800.compression``.

:class:`TestWorkedExample` é um exemplo numérico calculado à mão a
partir das fórmulas da norma (5.3.3/5.3.5.1), com os valores
"expected" escritos independentemente da chamada à função (mesma
fórmula transcrita diretamente no teste), não apenas o código
comparado consigo mesmo.
"""

from __future__ import annotations

import math

import pytest

from estrutura_metalica.normative.nbr8800 import (
    CompressionCheckResult,
    LoadCombinationClass,
    check_compression_member,
    effective_area_without_local_buckling,
    flexural_buckling_force,
    polar_radius_of_gyration,
    reduction_factor,
    slenderness_parameter,
    steel_resistance_factors,
    torsional_buckling_force,
)


class TestFlexuralBucklingForce:
    def test_matches_euler_formula(self) -> None:
        e, i, length = 200_000e6, 8e-6, 3.0
        expected = math.pi**2 * e * i / length**2
        assert flexural_buckling_force(e, i, length) == pytest.approx(expected, rel=1e-12)

    @pytest.mark.parametrize("field", ["elastic_modulus", "moment_of_inertia", "length"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = dict(elastic_modulus=200_000e6, moment_of_inertia=8e-6, length=3.0)
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            flexural_buckling_force(**kwargs)


class TestPolarRadiusOfGyration:
    def test_matches_pythagorean_sum(self) -> None:
        assert polar_radius_of_gyration(0.08, 0.06) == pytest.approx(0.1, rel=1e-12)

    @pytest.mark.parametrize("field", ["radius_of_gyration_x", "radius_of_gyration_y"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {"radius_of_gyration_x": 0.08, "radius_of_gyration_y": 0.06}
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            polar_radius_of_gyration(**kwargs)


class TestTorsionalBucklingForce:
    def test_matches_formula(self) -> None:
        e, g, cw, j, r0, length = 200_000e6, 76_923e6, 1e-9, 2e-7, 0.1, 3.0
        expected = (1.0 / r0**2) * (math.pi**2 * e * cw / length**2 + g * j)
        assert torsional_buckling_force(e, g, cw, j, r0, length) == pytest.approx(
            expected, rel=1e-12
        )

    def test_accepts_zero_warping_constant_for_closed_sections(self) -> None:
        # Cw=0 é fisicamente válido para seções fechadas/tubulares.
        result = torsional_buckling_force(
            elastic_modulus=200_000e6,
            shear_modulus=76_923e6,
            warping_constant=0.0,
            torsion_constant=2e-7,
            polar_radius_of_gyration=0.1,
            length=3.0,
        )
        assert result > 0

    def test_rejects_negative_warping_constant(self) -> None:
        with pytest.raises(ValueError):
            torsional_buckling_force(
                elastic_modulus=200_000e6,
                shear_modulus=76_923e6,
                warping_constant=-1.0,
                torsion_constant=2e-7,
                polar_radius_of_gyration=0.1,
                length=3.0,
            )

    @pytest.mark.parametrize(
        "field",
        [
            "elastic_modulus",
            "shear_modulus",
            "torsion_constant",
            "polar_radius_of_gyration",
            "length",
        ],
    )
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = dict(
            elastic_modulus=200_000e6,
            shear_modulus=76_923e6,
            warping_constant=1e-9,
            torsion_constant=2e-7,
            polar_radius_of_gyration=0.1,
            length=3.0,
        )
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            torsional_buckling_force(**kwargs)


class TestEffectiveAreaWithoutLocalBuckling:
    def test_returns_gross_area_unchanged(self) -> None:
        assert effective_area_without_local_buckling(0.005) == pytest.approx(0.005)

    @pytest.mark.parametrize("bad_value", [0.0, -1.0, float("nan"), float("inf")])
    def test_rejects_non_positive_or_non_finite(self, bad_value: float) -> None:
        with pytest.raises(ValueError):
            effective_area_without_local_buckling(bad_value)


class TestReductionFactor:
    def test_short_column_branch(self) -> None:
        lambda_0 = 1.0
        assert reduction_factor(lambda_0) == pytest.approx(0.658**1.0, rel=1e-12)

    def test_slender_column_branch(self) -> None:
        lambda_0 = 2.0
        assert reduction_factor(lambda_0) == pytest.approx(0.877 / 4.0, rel=1e-12)

    def test_result_always_within_zero_one(self) -> None:
        for lambda_0 in (0.0, 0.5, 1.0, 1.5, 2.0, 5.0, 20.0):
            chi = reduction_factor(lambda_0)
            assert 0.0 < chi <= 1.0

    def test_rejects_negative_lambda(self) -> None:
        with pytest.raises(ValueError):
            reduction_factor(-1.0)


class TestSlendernessParameter:
    def test_matches_formula(self) -> None:
        gross_area, fy, ne = 0.005, 345e6, 1_500_000.0
        expected = math.sqrt(gross_area * fy / ne)
        assert slenderness_parameter(gross_area, fy, ne) == pytest.approx(expected, rel=1e-12)

    @pytest.mark.parametrize("field", ["gross_area", "fy", "elastic_buckling_force"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = dict(gross_area=0.005, fy=345e6, elastic_buckling_force=1_500_000.0)
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            slenderness_parameter(**kwargs)


class TestCompressionCheckResultValidation:
    def test_rejects_non_finite_nc_sd(self) -> None:
        with pytest.raises(ValueError):
            CompressionCheckResult(nc_sd=float("nan"), lambda_0=1.0, chi=0.5, nc_rd=1.0)

    def test_rejects_negative_lambda_0(self) -> None:
        with pytest.raises(ValueError):
            CompressionCheckResult(nc_sd=0.0, lambda_0=-1.0, chi=0.5, nc_rd=1.0)

    @pytest.mark.parametrize("bad_chi", [0.0, -0.1, 1.1])
    def test_rejects_chi_outside_zero_one(self, bad_chi: float) -> None:
        with pytest.raises(ValueError):
            CompressionCheckResult(nc_sd=0.0, lambda_0=1.0, chi=bad_chi, nc_rd=1.0)

    @pytest.mark.parametrize("bad_value", [0.0, -1.0, float("nan"), float("inf")])
    def test_rejects_non_positive_or_non_finite_nc_rd(self, bad_value: float) -> None:
        with pytest.raises(ValueError):
            CompressionCheckResult(nc_sd=0.0, lambda_0=1.0, chi=0.5, nc_rd=bad_value)


class TestCheckCompressionMember:
    def test_rejects_effective_area_larger_than_gross(self) -> None:
        with pytest.raises(ValueError):
            check_compression_member(
                nc_sd=100.0,
                gross_area=0.005,
                effective_area=0.006,
                fy=345e6,
                elastic_buckling_force=1_500_000.0,
                resistance_factors=steel_resistance_factors(LoadCombinationClass.NORMAL),
            )

    def test_rejects_non_finite_nc_sd(self) -> None:
        with pytest.raises(ValueError):
            check_compression_member(
                nc_sd=float("nan"),
                gross_area=0.005,
                effective_area=0.005,
                fy=345e6,
                elastic_buckling_force=1_500_000.0,
                resistance_factors=steel_resistance_factors(LoadCombinationClass.NORMAL),
            )

    @pytest.mark.parametrize("field", ["gross_area", "effective_area", "fy"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = dict(
            nc_sd=0.0, gross_area=0.005, effective_area=0.005, fy=345e6,
            elastic_buckling_force=1_500_000.0,
        )
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            check_compression_member(
                resistance_factors=steel_resistance_factors(LoadCombinationClass.NORMAL),
                **kwargs,
            )


class TestWorkedExample:
    """Pilar de aço ASTM A992 (fy=345 MPa, E=200 000 MPa,
    G=76 923 MPa), seção com dupla simetria: Ag=0,005 m²,
    Ix=Iy=8e-6 m⁴, J=2e-7 m⁴, Cw=1e-9 m⁶ (valor hipotético — só para
    exercitar Nez), comprimentos destravados Lx=Ly=Lz=3,0 m,
    combinação normal (γa1=1,10).

    Cálculo à mão (NBR 8800:2024, 5.3.3/5.3.5.1):
    - Nex = Ney = π²·E·I/L² (Ix=Iy neste exemplo)
    - r0 = sqrt(rx²+ry²) = sqrt(2·(I/Ag))  [rx=ry aqui]
    - Nez = (1/r0²)·[π²·E·Cw/Lz² + G·J]
    - Ne = min(Nex, Ney, Nez)
    - λ0 = sqrt(Ag·fy/Ne); χ conforme a faixa de λ0
    - Nc,Rd = χ·Ag·fy/γa1 (Aef=Ag, sem flambagem local)
    """

    _E = 200_000e6
    _G = 76_923e6
    _FY = 345e6
    _AG = 0.005
    _IX = _IY = 8e-6
    _J = 2e-7
    _CW = 1e-9
    _L = 3.0

    def _hand_calculated_ne(self) -> float:
        nex = math.pi**2 * self._E * self._IX / self._L**2
        ney = math.pi**2 * self._E * self._IY / self._L**2
        rx = math.sqrt(self._IX / self._AG)
        ry = math.sqrt(self._IY / self._AG)
        r0 = math.sqrt(rx**2 + ry**2)
        nez = (1.0 / r0**2) * (math.pi**2 * self._E * self._CW / self._L**2 + self._G * self._J)
        return min(nex, ney, nez)

    def test_flexural_and_torsional_buckling_forces_and_ne(self) -> None:
        nex = flexural_buckling_force(self._E, self._IX, self._L)
        ney = flexural_buckling_force(self._E, self._IY, self._L)
        r0 = polar_radius_of_gyration(
            math.sqrt(self._IX / self._AG), math.sqrt(self._IY / self._AG)
        )
        nez = torsional_buckling_force(self._E, self._G, self._CW, self._J, r0, self._L)
        ne = min(nex, ney, nez)
        assert ne == pytest.approx(self._hand_calculated_ne(), rel=1e-9)

    def test_full_check_compression_member(self) -> None:
        ne = self._hand_calculated_ne()
        lambda_0 = math.sqrt(self._AG * self._FY / ne)
        chi = 0.658 ** (lambda_0**2) if lambda_0 <= 1.5 else 0.877 / lambda_0**2
        expected_nc_rd = chi * self._AG * self._FY / 1.10

        result = check_compression_member(
            nc_sd=0.0,
            gross_area=self._AG,
            effective_area=effective_area_without_local_buckling(self._AG),
            fy=self._FY,
            elastic_buckling_force=ne,
            resistance_factors=steel_resistance_factors(LoadCombinationClass.NORMAL),
        )
        assert result.lambda_0 == pytest.approx(lambda_0, rel=1e-9)
        assert result.chi == pytest.approx(chi, rel=1e-9)
        assert result.nc_rd == pytest.approx(expected_nc_rd, rel=1e-9)

    def test_is_ok_below_and_above_capacity(self) -> None:
        ne = self._hand_calculated_ne()
        base_kwargs = dict(
            gross_area=self._AG,
            effective_area=effective_area_without_local_buckling(self._AG),
            fy=self._FY,
            elastic_buckling_force=ne,
            resistance_factors=steel_resistance_factors(LoadCombinationClass.NORMAL),
        )
        low = check_compression_member(nc_sd=1.0, **base_kwargs)
        high = check_compression_member(nc_sd=low.nc_rd * 2, **base_kwargs)
        assert low.is_ok is True
        assert high.is_ok is False
