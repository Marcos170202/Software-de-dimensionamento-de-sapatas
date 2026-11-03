"""Testes de ``estrutura_metalica.normative.nbr8800.slender_web``.

:class:`TestWorkedExample` cobre uma viga soldada de alma esbelta
hipotética, com propriedades calculadas independentemente (não pela
própria função) a partir da geometria de placas retangulares.
"""

from __future__ import annotations

import math

import pytest

from estrutura_metalica.normative.nbr8800.flexure import FlexureCheckResult
from estrutura_metalica.normative.nbr8800.slender_web import (
    check_flexural_resistance_slender_web_major_axis,
    check_slender_web_flange_local_buckling,
    check_slender_web_lateral_torsional_buckling,
    check_tension_flange_yielding,
    compression_flange_area_ratio,
    plate_girder_bending_strength_reduction_factor,
)


class TestCompressionFlangeAreaRatio:
    def test_matches_formula(self) -> None:
        hc, tw, bf, tf = 0.76, 0.006, 0.30, 0.020
        expected = (hc * tw) / (bf * tf)
        assert compression_flange_area_ratio(hc, tw, bf, tf) == pytest.approx(expected)

    def test_rejects_ar_above_10(self) -> None:
        # hc*tw muito maior que bf*tf -> ar > 10.
        with pytest.raises(ValueError, match="ar"):
            compression_flange_area_ratio(
                web_clear_height=2.0,
                web_thickness=0.05,
                flange_width=0.10,
                flange_thickness=0.005,
            )

    @pytest.mark.parametrize(
        "field", ["web_clear_height", "web_thickness", "flange_width", "flange_thickness"]
    )
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {
            "web_clear_height": 0.76,
            "web_thickness": 0.006,
            "flange_width": 0.30,
            "flange_thickness": 0.020,
        }
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            compression_flange_area_ratio(**kwargs)


class TestPlateGirderBendingStrengthReductionFactor:
    def test_matches_formula(self) -> None:
        ar, hc, tw, fy, e = 1.16, 1.16, 0.006, 345e6, 200_000e6
        expected = 1.0 - (ar / (1200.0 + 300.0 * ar)) * (
            hc / tw - 5.70 * math.sqrt(e / fy)
        )
        result = plate_girder_bending_strength_reduction_factor(ar, hc, tw, fy, e)
        assert result == pytest.approx(expected)

    def test_clamped_to_one(self) -> None:
        # h/tw pequeno o bastante para o termo subtraido ser negativo -> kpg > 1, saturado em 1,0.
        result = plate_girder_bending_strength_reduction_factor(
            ar=1.0, web_clear_height=0.10, web_thickness=0.006, fy=345e6, elastic_modulus=200_000e6
        )
        assert result == 1.0

    @pytest.mark.parametrize(
        "field", ["ar", "web_clear_height", "web_thickness", "fy", "elastic_modulus"]
    )
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {
            "ar": 1.16,
            "web_clear_height": 1.16,
            "web_thickness": 0.006,
            "fy": 345e6,
            "elastic_modulus": 200_000e6,
        }
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            plate_girder_bending_strength_reduction_factor(**kwargs)


class TestCheckTensionFlangeYielding:
    def test_matches_formula(self) -> None:
        wxt, fy, gamma_a1 = 8.263413333e-3, 345e6, 1.10
        expected = wxt * fy / gamma_a1
        result = check_tension_flange_yielding(1.0, wxt, fy, gamma_a1)
        assert result.mrd == pytest.approx(expected)
        assert isinstance(result, FlexureCheckResult)

    def test_rejects_non_finite_msd(self) -> None:
        with pytest.raises(ValueError):
            check_tension_flange_yielding(float("nan"), 8.263413333e-3, 345e6, 1.10)

    @pytest.mark.parametrize(
        "field", ["elastic_section_modulus_tension_side", "fy", "gamma_a1"]
    )
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {
            "msd": 1.0,
            "elastic_section_modulus_tension_side": 8.263413333e-3,
            "fy": 345e6,
            "gamma_a1": 1.10,
        }
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            check_tension_flange_yielding(**kwargs)


class TestCheckSlenderWebLateralTorsionalBuckling:
    _KWARGS = dict(
        msd=1.0,
        fy=345e6,
        elastic_modulus=200_000e6,
        elastic_section_modulus_compression_side=8.263413333e-3,
        kpg=0.9579661404741309,
        radius_of_gyration_compression_flange_plus_third_web=0.07928052872324244,
        unbraced_length=3.0,
        cb=1.0,
        gamma_a1=1.10,
    )

    def test_rejects_non_finite_msd(self) -> None:
        kwargs = dict(self._KWARGS)
        kwargs["msd"] = float("nan")
        with pytest.raises(ValueError):
            check_slender_web_lateral_torsional_buckling(**kwargs)

    @pytest.mark.parametrize(
        "field",
        [
            "fy",
            "elastic_section_modulus_compression_side",
            "kpg",
            "radius_of_gyration_compression_flange_plus_third_web",
            "unbraced_length",
        ],
    )
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = dict(self._KWARGS)
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            check_slender_web_lateral_torsional_buckling(**kwargs)

    def test_returns_positive_mrd(self) -> None:
        result = check_slender_web_lateral_torsional_buckling(**self._KWARGS)
        assert result.mrd > 0.0


class TestCheckSlenderWebFlangeLocalBuckling:
    _KWARGS = dict(
        msd=1.0,
        fy=345e6,
        elastic_modulus=200_000e6,
        elastic_section_modulus_compression_side=8.263413333e-3,
        kpg=0.9579661404741309,
        flange_width=0.30,
        flange_thickness=0.020,
        web_clear_height=1.16,
        web_thickness=0.006,
        gamma_a1=1.10,
    )

    def test_rejects_non_finite_msd(self) -> None:
        kwargs = dict(self._KWARGS)
        kwargs["msd"] = float("nan")
        with pytest.raises(ValueError):
            check_slender_web_flange_local_buckling(**kwargs)

    @pytest.mark.parametrize(
        "field",
        [
            "fy",
            "elastic_section_modulus_compression_side",
            "kpg",
            "flange_width",
            "flange_thickness",
        ],
    )
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = dict(self._KWARGS)
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            check_slender_web_flange_local_buckling(**kwargs)

    def test_returns_positive_mrd(self) -> None:
        result = check_slender_web_flange_local_buckling(**self._KWARGS)
        assert result.mrd > 0.0


class TestCheckFlexuralResistanceSlenderWebMajorAxis:
    """Viga soldada hipotética de alma esbelta: mesas 300x20 mm, alma
    1160x6 mm (``d=1,20`` m), ASTM A992 -- fy=345 MPa, E=200 000 MPa,
    sem enrijecedores transversais. Propriedades calculadas
    independentemente (não pela própria função) a partir da geometria
    de placas retangulares, ignorando raios de concordância (perfil
    soldado, portanto sem raios de fato).
    """

    _D = 1.20
    _BF = 0.30
    _TF = 0.020
    _TW = 0.006
    _H = _D - 2 * _TF
    _FY = 345e6
    _E = 200_000e6
    _GAMMA_A1 = 1.10
    _CB = 1.0

    _IX = 2 * (_BF * _TF**3 / 12 + _BF * _TF * (_D / 2 - _TF / 2) ** 2) + _TW * _H**3 / 12
    _W = _IX / (_D / 2)
    # ryc: mesa comprimida + 1/3 da altura da alma comprimida (h/2/3),
    # em relação ao eixo fraco -- cálculo independente para o teste
    # (o próprio módulo não calcula ryc, ver ATENÇÃO 3 no docstring).
    _HC3 = (_H / 2) / 3
    _IYY_RYC = _TF * _BF**3 / 12 + _HC3 * _TW**3 / 12
    _A_RYC = _BF * _TF + _HC3 * _TW
    _RYC = math.sqrt(_IYY_RYC / _A_RYC)

    def _kwargs(self, *, msd: float = 1.0, unbraced_length: float) -> dict:
        return dict(
            msd=msd,
            fy=self._FY,
            elastic_modulus=self._E,
            elastic_section_modulus=self._W,
            radius_of_gyration_compression_flange_plus_third_web=self._RYC,
            unbraced_length=unbraced_length,
            cb=self._CB,
            flange_width=self._BF,
            flange_thickness=self._TF,
            web_clear_height=self._H,
            web_thickness=self._TW,
            stiffener_spacing=None,
            gamma_a1=self._GAMMA_A1,
        )

    def test_web_is_actually_slender(self) -> None:
        # Confere a premissa do exemplo antes de tudo.
        lam_r_flat = 5.70 * math.sqrt(self._E / self._FY)
        assert lam_r_flat < self._H / self._TW

    def test_rejects_non_slender_web(self) -> None:
        # Alma mais espessa -> nao esbelta -> deve remeter ao Anexo D.
        kwargs = self._kwargs(unbraced_length=3.0)
        kwargs["web_thickness"] = 0.020
        with pytest.raises(ValueError, match="Anexo D"):
            check_flexural_resistance_slender_web_major_axis(**kwargs)

    def test_rejects_web_slenderness_above_e_5_3_b_limit(self) -> None:
        # Alma extremamente fina -> viola o limite adicional de E.5.3-b.
        kwargs = self._kwargs(unbraced_length=3.0)
        kwargs["web_thickness"] = 0.002
        with pytest.raises(ValueError, match="E.5.3-b"):
            check_flexural_resistance_slender_web_major_axis(**kwargs)

    def test_rejects_non_finite_msd(self) -> None:
        kwargs = self._kwargs(unbraced_length=3.0)
        kwargs["msd"] = float("nan")
        with pytest.raises(ValueError):
            check_flexural_resistance_slender_web_major_axis(**kwargs)

    @pytest.mark.parametrize(
        "field",
        ["fy", "elastic_modulus", "elastic_section_modulus", "web_clear_height", "web_thickness"],
    )
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = self._kwargs(unbraced_length=3.0)
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            check_flexural_resistance_slender_web_major_axis(**kwargs)

    def test_mrd_matches_hand_calculation_flt_governs(self) -> None:
        # Lb=3,0 m -> FLT no trecho inelastico, menor que E.6.1 e FLM
        # (calculado a mao, ver docstring da classe e verificacao
        # numerica independente feita durante o desenvolvimento).
        result = check_flexural_resistance_slender_web_major_axis(
            **self._kwargs(unbraced_length=3.0)
        )
        assert result.mrd == pytest.approx(2_350_454.1428016373, rel=1e-6)

    def test_is_ok_below_and_above_capacity(self) -> None:
        low = check_flexural_resistance_slender_web_major_axis(
            **self._kwargs(unbraced_length=3.0, msd=1.0)
        )
        high = check_flexural_resistance_slender_web_major_axis(
            **self._kwargs(unbraced_length=3.0, msd=10_000_000.0)
        )
        assert low.is_ok is True
        assert high.is_ok is False

    def test_stiffened_web_with_close_spacing_uses_looser_upper_limit(self) -> None:
        # a/h<=1,5 -> limite superior de E.5.3-b usa 11,7*sqrt(E/fy),
        # mais permissivo que 0,42*E/fy (sem enrijecedores) para este
        # fy -- confere que informar 'a' pequeno não quebra o exemplo.
        kwargs = self._kwargs(unbraced_length=3.0)
        kwargs["stiffener_spacing"] = self._H * 1.0  # a/h = 1,0 <= 1,5
        result = check_flexural_resistance_slender_web_major_axis(**kwargs)
        assert result.mrd > 0.0
