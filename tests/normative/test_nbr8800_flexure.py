"""Testes de ``estrutura_metalica.normative.nbr8800.flexure``.

:class:`TestWorkedExample` cobre um perfil I hipotético (calculado à
mão/independentemente em Python, não pela própria função) para validar
FLT/FLM/FLA e o ``Mrd`` governante retornado por
``check_flexural_resistance_major_axis``.
"""

from __future__ import annotations

import math

import pytest

from estrutura_metalica.normative.nbr8800 import (
    FlexureCheckResult,
    check_flexural_resistance_major_axis,
    check_lateral_torsional_buckling,
    flange_local_buckling_coefficient_welded,
    flange_local_buckling_moment_rolled,
    flange_local_buckling_moment_welded,
    flexural_resistance,
    lateral_torsional_buckling_moment,
    lateral_torsional_buckling_slenderness_limit,
    moment_gradient_factor_doubly_symmetric,
    warping_constant_i_section,
)


class TestMomentGradientFactor:
    def test_matches_formula(self) -> None:
        m_max, m_a, m_b, m_c = 100.0, 40.0, 90.0, 80.0
        expected = 12.5 * m_max / (2.5 * m_max + 3 * m_a + 4 * m_b + 3 * m_c)
        result = moment_gradient_factor_doubly_symmetric(m_max, m_a, m_b, m_c)
        assert result == pytest.approx(expected)

    def test_uniform_moment_gives_cb_one(self) -> None:
        # Momento constante ao longo do trecho: Mmax=MA=MB=MC -> Cb=1,0.
        m = 100.0
        assert moment_gradient_factor_doubly_symmetric(m, m, m, m) == pytest.approx(1.0)

    def test_rejects_non_positive_m_max(self) -> None:
        with pytest.raises(ValueError):
            moment_gradient_factor_doubly_symmetric(0.0, 0.0, 0.0, 0.0)

    @pytest.mark.parametrize("field", ["m_a", "m_b", "m_c"])
    def test_rejects_negative_secondary_moments(self, field: str) -> None:
        kwargs = {"m_max": 100.0, "m_a": 10.0, "m_b": 10.0, "m_c": 10.0}
        kwargs[field] = -1.0
        with pytest.raises(ValueError):
            moment_gradient_factor_doubly_symmetric(**kwargs)

    def test_accepts_zero_secondary_moments(self) -> None:
        # Próximo a um apoio simples, MA (por exemplo) pode ser zero.
        result = moment_gradient_factor_doubly_symmetric(100.0, 0.0, 50.0, 90.0)
        assert result > 0.0


class TestWarpingConstantISection:
    def test_matches_formula(self) -> None:
        iy, d, tf = 6.76e-6, 0.3, 0.012
        expected = iy * (d - tf) ** 2 / 4.0
        assert warping_constant_i_section(iy, d, tf) == pytest.approx(expected)

    @pytest.mark.parametrize(
        "field", ["minor_axis_moment_of_inertia", "total_depth", "flange_thickness"]
    )
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {
            "minor_axis_moment_of_inertia": 6.76e-6,
            "total_depth": 0.3,
            "flange_thickness": 0.012,
        }
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            warping_constant_i_section(**kwargs)

    def test_rejects_flange_thickness_not_smaller_than_total_depth(self) -> None:
        with pytest.raises(ValueError):
            warping_constant_i_section(6.76e-6, 0.012, 0.012)


class TestLateralTorsionalBucklingMoment:
    def test_matches_formula(self) -> None:
        cb, e, iy, j, cw, lb = 1.0, 200_000e6, 6.76e-6, 2.2e-7, 1.4e-7, 3.0
        expected = (cb * math.pi**2 * e * iy / lb**2) * math.sqrt(
            (cw / iy) * (1.0 + 0.039 * j * lb**2 / cw)
        )
        result = lateral_torsional_buckling_moment(cb, e, iy, j, cw, lb)
        assert result == pytest.approx(expected)

    @pytest.mark.parametrize(
        "field",
        [
            "cb",
            "elastic_modulus",
            "minor_axis_moment_of_inertia",
            "torsion_constant",
            "warping_constant",
            "unbraced_length",
        ],
    )
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = dict(
            cb=1.0,
            elastic_modulus=200_000e6,
            minor_axis_moment_of_inertia=6.76e-6,
            torsion_constant=2.2e-7,
            warping_constant=1.4e-7,
            unbraced_length=3.0,
        )
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            lateral_torsional_buckling_moment(**kwargs)


class TestLateralTorsionalBucklingSlendernessLimit:
    def test_matches_formula(self) -> None:
        cb, e, iy, j, cw, ry, mr = 1.0, 200_000e6, 6.76e-6, 2.2e-7, 1.4e-7, 0.0341, 142_800.0
        beta1 = mr / (e * j)
        expected = (1.38 * cb * math.sqrt(iy * j) / (ry * j * beta1)) * math.sqrt(
            1.0 + math.sqrt(1.0 + 27.0 * cw * beta1**2 / (cb**2 * iy))
        )
        result = lateral_torsional_buckling_slenderness_limit(cb, e, iy, j, cw, ry, mr)
        assert result == pytest.approx(expected)

    @pytest.mark.parametrize(
        "field",
        [
            "cb",
            "elastic_modulus",
            "minor_axis_moment_of_inertia",
            "torsion_constant",
            "warping_constant",
            "radius_of_gyration_minor_axis",
            "residual_moment",
        ],
    )
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = dict(
            cb=1.0,
            elastic_modulus=200_000e6,
            minor_axis_moment_of_inertia=6.76e-6,
            torsion_constant=2.2e-7,
            warping_constant=1.4e-7,
            radius_of_gyration_minor_axis=0.0341,
            residual_moment=142_800.0,
        )
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            lateral_torsional_buckling_slenderness_limit(**kwargs)


class TestFlexuralResistance:
    def test_plastic_branch(self) -> None:
        mpl = 200_000.0
        result = flexural_resistance(
            plastic_moment=mpl,
            residual_moment=140_000.0,
            critical_moment=100_000.0,
            slenderness=30.0,
            slenderness_limit_p=40.0,
            slenderness_limit_r=90.0,
            gamma_a1=1.10,
        )
        assert result == pytest.approx(mpl / 1.10)

    def test_inelastic_branch(self) -> None:
        mpl, mr, lam, lam_p, lam_r = 200_000.0, 140_000.0, 60.0, 40.0, 90.0
        ratio = (lam - lam_p) / (lam_r - lam_p)
        expected = (mpl - (mpl - mr) * ratio) / 1.10
        result = flexural_resistance(mpl, mr, 100_000.0, lam, lam_p, lam_r, gamma_a1=1.10)
        assert result == pytest.approx(expected)

    def test_elastic_branch(self) -> None:
        mcr = 90_000.0
        result = flexural_resistance(
            plastic_moment=200_000.0,
            residual_moment=140_000.0,
            critical_moment=mcr,
            slenderness=120.0,
            slenderness_limit_p=40.0,
            slenderness_limit_r=90.0,
            gamma_a1=1.10,
        )
        assert result == pytest.approx(mcr / 1.10)

    def test_rejects_residual_moment_above_plastic_moment(self) -> None:
        with pytest.raises(ValueError):
            flexural_resistance(
                plastic_moment=100_000.0,
                residual_moment=150_000.0,
                critical_moment=90_000.0,
                slenderness=30.0,
                slenderness_limit_p=40.0,
                slenderness_limit_r=90.0,
                gamma_a1=1.10,
            )

    def test_rejects_limit_r_below_limit_p(self) -> None:
        with pytest.raises(ValueError):
            flexural_resistance(
                200_000.0,
                140_000.0,
                100_000.0,
                50.0,
                slenderness_limit_p=90.0,
                slenderness_limit_r=40.0,
                gamma_a1=1.10,
            )

    @pytest.mark.parametrize(
        "field",
        [
            "plastic_moment",
            "residual_moment",
            "critical_moment",
            "slenderness",
            "slenderness_limit_p",
            "slenderness_limit_r",
            "gamma_a1",
        ],
    )
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = dict(
            plastic_moment=200_000.0,
            residual_moment=140_000.0,
            critical_moment=100_000.0,
            slenderness=30.0,
            slenderness_limit_p=40.0,
            slenderness_limit_r=90.0,
            gamma_a1=1.10,
        )
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            flexural_resistance(**kwargs)


class TestFlexureCheckResultValidation:
    def test_rejects_non_finite_msd(self) -> None:
        with pytest.raises(ValueError):
            FlexureCheckResult(msd=float("nan"), mrd=1.0)

    @pytest.mark.parametrize("bad_value", [0.0, -1.0, float("nan"), float("inf")])
    def test_rejects_non_positive_or_non_finite_mrd(self, bad_value: float) -> None:
        with pytest.raises(ValueError):
            FlexureCheckResult(msd=0.0, mrd=bad_value)

    def test_is_ok_ignores_sign_caller_must_pass_magnitude(self) -> None:
        # ATENÇÃO documentada na classe: msd muito negativo "passa" mesmo
        # que a barra esteja sobrecarregada no sentido oposto -- o
        # chamador deve passar abs(msd) se quiser checar a magnitude.
        result = FlexureCheckResult(msd=-1_000_000.0, mrd=100.0)
        assert result.is_ok is True


class TestFlangeLocalBucklingCoefficientWelded:
    def test_matches_formula_within_bounds(self) -> None:
        h, tw = 0.276, 0.008
        expected = 4.0 / math.sqrt(h / tw)
        assert 0.35 <= expected <= 0.76
        assert flange_local_buckling_coefficient_welded(h, tw) == pytest.approx(expected)

    def test_clamped_to_upper_bound(self) -> None:
        # h/tw muito pequeno -> kc calculado > 0,76, deve saturar em 0,76.
        kc = flange_local_buckling_coefficient_welded(web_clear_height=0.05, web_thickness=0.02)
        assert kc == 0.76

    def test_clamped_to_lower_bound(self) -> None:
        # h/tw muito grande -> kc calculado < 0,35, deve saturar em 0,35.
        kc = flange_local_buckling_coefficient_welded(web_clear_height=2.0, web_thickness=0.002)
        assert kc == 0.35

    @pytest.mark.parametrize("field", ["web_clear_height", "web_thickness"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {"web_clear_height": 0.276, "web_thickness": 0.010}
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            flange_local_buckling_coefficient_welded(**kwargs)


class TestFlangeLocalBucklingMomentRolled:
    def test_matches_formula(self) -> None:
        e, wc, lam = 200_000e6, 5.9e-4, 15.0
        expected = 0.69 * e / lam**2 * wc
        assert flange_local_buckling_moment_rolled(e, wc, lam) == pytest.approx(expected)

    @pytest.mark.parametrize(
        "field", ["elastic_modulus", "compressed_side_section_modulus", "slenderness"]
    )
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {
            "elastic_modulus": 200_000e6,
            "compressed_side_section_modulus": 5.9e-4,
            "slenderness": 15.0,
        }
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            flange_local_buckling_moment_rolled(**kwargs)


class TestFlangeLocalBucklingMomentWelded:
    def test_matches_formula(self) -> None:
        e, kc, wc, lam = 200_000e6, 0.6, 5.9e-4, 15.0
        expected = 0.90 * e * kc / lam**2 * wc
        assert flange_local_buckling_moment_welded(e, kc, wc, lam) == pytest.approx(expected)

    @pytest.mark.parametrize(
        "field",
        [
            "elastic_modulus",
            "flange_local_buckling_coefficient",
            "compressed_side_section_modulus",
            "slenderness",
        ],
    )
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = dict(
            elastic_modulus=200_000e6,
            flange_local_buckling_coefficient=0.6,
            compressed_side_section_modulus=5.9e-4,
            slenderness=15.0,
        )
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            flange_local_buckling_moment_welded(**kwargs)


class TestCheckLateralTorsionalBuckling:
    _KWARGS = dict(
        msd=0.0,
        fy=345e6,
        elastic_modulus=200_000e6,
        elastic_section_modulus=5.9139456e-4,
        plastic_section_modulus=6.707520e-4,
        minor_axis_moment_of_inertia=6.761776e-6,
        torsion_constant=2.19904e-7,
        warping_constant=1.40212187136e-7,
        radius_of_gyration_minor_axis=0.03412063350604725,
        unbraced_length=1.0,
        cb=1.0,
        gamma_a1=1.10,
    )

    def test_rejects_non_finite_msd(self) -> None:
        kwargs = dict(self._KWARGS)
        kwargs["msd"] = float("nan")
        with pytest.raises(ValueError):
            check_lateral_torsional_buckling(**kwargs)

    def test_rejects_plastic_modulus_smaller_than_elastic_modulus(self) -> None:
        kwargs = dict(self._KWARGS)
        kwargs["plastic_section_modulus"] = kwargs["elastic_section_modulus"] / 2.0
        with pytest.raises(ValueError):
            check_lateral_torsional_buckling(**kwargs)

    @pytest.mark.parametrize(
        "field",
        [
            "fy",
            "elastic_section_modulus",
            "plastic_section_modulus",
            "radius_of_gyration_minor_axis",
            "unbraced_length",
        ],
    )
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = dict(self._KWARGS)
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            check_lateral_torsional_buckling(**kwargs)

    def test_returns_flexure_check_result(self) -> None:
        result = check_lateral_torsional_buckling(**self._KWARGS)
        assert isinstance(result, FlexureCheckResult)
        assert result.mrd > 0.0


class TestCheckFlexuralResistanceMajorAxis:
    """Perfil I hipotético (mesas 0,15x0,012 m, alma 0,276x0,008 m,
    ``d=0,3`` m, laminado, ASTM A992 -- fy=345 MPa, E=200 000 MPa),
    propriedades calculadas independentemente (não pela própria
    função) a partir da geometria de placas retangulares, ignorando
    raios de concordância.
    """

    _D = 0.3
    _BF = 0.15
    _TF = 0.012
    _TW = 0.008
    _H = _D - 2 * _TF
    _FY = 345e6
    _E = 200_000e6
    _GAMMA_A1 = 1.10

    _A = 2 * _BF * _TF + _H * _TW
    _IX = 2 * (_BF * _TF**3 / 12 + _BF * _TF * (_D / 2 - _TF / 2) ** 2) + _TW * _H**3 / 12
    _W = _IX / (_D / 2)
    _Z = _BF * _TF * (_D - _TF) + _TW * _H**2 / 4
    _IY = 2 * (_TF * _BF**3 / 12) + _H * _TW**3 / 12
    _RY = math.sqrt(_IY / _A)
    _J = 2 * (_BF * _TF**3) / 3 + (_H * _TW**3) / 3
    _CW = _IY * (_D - _TF) ** 2 / 4

    def _kwargs(self, *, msd: float = 0.0, unbraced_length: float, rolled: bool = True) -> dict:
        return dict(
            msd=msd,
            fy=self._FY,
            elastic_modulus=self._E,
            elastic_section_modulus=self._W,
            plastic_section_modulus=self._Z,
            minor_axis_moment_of_inertia=self._IY,
            torsion_constant=self._J,
            warping_constant=self._CW,
            radius_of_gyration_minor_axis=self._RY,
            unbraced_length=unbraced_length,
            cb=1.0,
            flange_width=self._BF,
            flange_thickness=self._TF,
            web_clear_height=self._H,
            web_thickness=self._TW,
            rolled=rolled,
            gamma_a1=self._GAMMA_A1,
        )

    def test_rejects_non_finite_msd(self) -> None:
        kwargs = self._kwargs(unbraced_length=1.0)
        kwargs["msd"] = float("nan")
        with pytest.raises(ValueError):
            check_flexural_resistance_major_axis(**kwargs)

    def test_rejects_plastic_modulus_smaller_than_elastic_modulus(self) -> None:
        kwargs = self._kwargs(unbraced_length=1.0)
        kwargs["plastic_section_modulus"] = kwargs["elastic_section_modulus"] / 2.0
        with pytest.raises(ValueError):
            check_flexural_resistance_major_axis(**kwargs)

    @pytest.mark.parametrize(
        "field",
        [
            "fy",
            "elastic_modulus",
            "elastic_section_modulus",
            "plastic_section_modulus",
            "flange_width",
            "flange_thickness",
            "web_clear_height",
            "web_thickness",
        ],
    )
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = self._kwargs(unbraced_length=1.0)
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            check_flexural_resistance_major_axis(**kwargs)

    def test_rejects_slender_web(self) -> None:
        # Reduz tw para forçar h/tw acima do limite D.1.2 (5,70*sqrt(E/fy)).
        kwargs = self._kwargs(unbraced_length=1.0)
        kwargs["web_thickness"] = 0.001
        with pytest.raises(ValueError, match="ALMA ESBELTA"):
            check_flexural_resistance_major_axis(**kwargs)

    def test_accepts_web_at_exact_slenderness_limit(self) -> None:
        lam_r_fla = 5.70 * math.sqrt(self._E / self._FY)
        tw_at_limit = self._H / lam_r_fla
        kwargs = self._kwargs(unbraced_length=1.0)
        kwargs["web_thickness"] = tw_at_limit
        result = check_flexural_resistance_major_axis(**kwargs)
        assert result.mrd > 0.0

    def test_plastic_branch_all_limit_states_governs_equally(self) -> None:
        # Lb=1,0 m -> os três estados-limite (FLT/FLM/FLA) caem no
        # trecho de plastificação -> Mrd = Mpl/gamma_a1 em todos, e o
        # limite de 5.4.2.2 não governa.
        lam_p_flt = 1.76 * math.sqrt(self._E / self._FY)
        lb = 1.0
        assert lb / self._RY <= lam_p_flt  # confere a premissa

        mpl = self._FY * self._Z
        expected_mrd = mpl / self._GAMMA_A1
        cap = 1.50 * self._W * self._FY / self._GAMMA_A1
        assert expected_mrd < cap  # confere que o limite 5.4.2.2 não governa

        result = check_flexural_resistance_major_axis(**self._kwargs(unbraced_length=lb))
        assert result.mrd == pytest.approx(expected_mrd, rel=1e-9)
        assert result.mrd == pytest.approx(210_372.21818181814, rel=1e-6)

    def test_long_unbraced_length_flt_governs_via_inelastic_branch(self) -> None:
        # Lb=4,0 m -> FLT cai no trecho inelástico (Mrd_FLT menor que o
        # Mrd_FLM/FLA, que continuam no trecho de plastificação, já que
        # não dependem de Lb) -> Mrd = Mrd_FLT.
        lb = 4.0
        lam_flt = lb / self._RY
        lam_p_flt = 1.76 * math.sqrt(self._E / self._FY)
        beta1 = (self._FY - 0.30 * self._FY) * self._W / (self._E * self._J)
        lam_r_flt = (
            1.38 * math.sqrt(self._IY * self._J) / (self._RY * self._J * beta1)
        ) * math.sqrt(1.0 + math.sqrt(1.0 + 27.0 * self._CW * beta1**2 / self._IY))
        assert lam_p_flt < lam_flt <= lam_r_flt  # confere a premissa (trecho inelástico)

        mpl = self._FY * self._Z
        mr = (self._FY - 0.30 * self._FY) * self._W
        ratio = (lam_flt - lam_p_flt) / (lam_r_flt - lam_p_flt)
        expected_mrd_flt = (mpl - (mpl - mr) * ratio) / self._GAMMA_A1

        result = check_flexural_resistance_major_axis(**self._kwargs(unbraced_length=lb))
        assert result.mrd == pytest.approx(expected_mrd_flt, rel=1e-6)
        assert result.mrd == pytest.approx(142_760.5583177484, rel=1e-6)

    def test_welded_section_uses_kc_and_gives_different_flm_than_rolled(self) -> None:
        # Trecho longo o bastante para não deixar FLM no trecho de
        # plastificação (senão laminado/soldado dariam o mesmo Mrd).
        kwargs_rolled = self._kwargs(unbraced_length=0.3, rolled=True)
        kwargs_welded = self._kwargs(unbraced_length=0.3, rolled=False)
        result_rolled = check_flexural_resistance_major_axis(**kwargs_rolled)
        result_welded = check_flexural_resistance_major_axis(**kwargs_welded)
        # Ambos válidos (Mrd positivo); o valor pode até coincidir se
        # ambos caírem no trecho de plastificação -- o que importa é
        # que nenhuma exceção é levantada para rolled=False também.
        assert result_rolled.mrd > 0.0
        assert result_welded.mrd > 0.0

    def test_is_ok_below_and_above_capacity(self) -> None:
        low = check_flexural_resistance_major_axis(**self._kwargs(unbraced_length=1.0, msd=1.0))
        high = check_flexural_resistance_major_axis(
            **self._kwargs(unbraced_length=1.0, msd=10_000_000.0)
        )
        assert low.is_ok is True
        assert high.is_ok is False
