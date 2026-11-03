"""Testes de ``estrutura_metalica.normative.nbr8800.column_base``.

:class:`TestWorkedExample` cobre uma base de pilar hipotética (Caso
C1, compressão concêntrica) calculada à mão.
"""

from __future__ import annotations

import math

import pytest

from estrutura_metalica.normative.nbr8800 import (
    ColumnBaseCaseC1Result,
    ColumnBaseCheckResult,
    check_column_base_case_c1,
    column_base_concrete_bearing_stress,
    column_base_effective_length_x,
    column_base_effective_length_y,
    column_base_friction_shear_resistance,
    column_base_lambda,
    column_base_plate_effective_length_c1,
    column_base_plate_min_thickness_case_c1,
    column_base_x_parameter,
    column_base_yield_line_m,
    column_base_yield_line_n,
    column_base_yield_line_n0,
    concrete_bearing_resistance,
    concrete_grout_shear_friction_limit,
)


class TestConcreteBearingResistance:
    def test_matches_formula(self) -> None:
        a1, a2, fck, gamma_c = 0.1265, 0.506, 25e6, 1.40
        fck_gc = fck / gamma_c
        expected = min(0.85 * fck_gc * math.sqrt(a2 / a1), 1.7 * fck_gc)
        result = concrete_bearing_resistance(a1, a2, fck, gamma_c)
        assert result == pytest.approx(expected)

    def test_a2_over_a1_equals_4_saturates_both_terms_equally(self) -> None:
        # sqrt(4)=2 e 0,85*2=1,7 -> os dois termos da formula coincidem.
        a1, fck, gamma_c = 0.10, 25e6, 1.40
        result = concrete_bearing_resistance(a1, 4.0 * a1, fck, gamma_c)
        assert result == pytest.approx(1.7 * fck / gamma_c)

    def test_rejects_concrete_area_smaller_than_loaded_area(self) -> None:
        with pytest.raises(ValueError):
            concrete_bearing_resistance(
                loaded_area=0.20, concrete_area=0.10, fck=25e6, gamma_c=1.40
            )

    @pytest.mark.parametrize("field", ["loaded_area", "concrete_area", "fck", "gamma_c"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {"loaded_area": 0.1265, "concrete_area": 0.506, "fck": 25e6, "gamma_c": 1.40}
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            concrete_bearing_resistance(**kwargs)


class TestColumnBaseEffectiveLengthX:
    def test_matches_formula(self) -> None:
        d, a1 = 0.300, 0.040
        assert column_base_effective_length_x(d, a1) == pytest.approx(d + 4 * a1)

    @pytest.mark.parametrize("field", ["column_depth", "edge_distance"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {"column_depth": 0.300, "edge_distance": 0.040}
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            column_base_effective_length_x(**kwargs)


class TestColumnBaseEffectiveLengthY:
    def test_matches_formula_anchors_govern(self) -> None:
        nb, a1, a2, bf = 8, 0.040, 0.100, 0.150
        expected = (0.5 * nb - 1) * a2 + 2 * a1
        result = column_base_effective_length_y(nb, a1, a2, bf)
        assert result == pytest.approx(expected)

    def test_matches_formula_flange_governs(self) -> None:
        nb, a1, a2, bf = 4, 0.040, 0.100, 0.250
        expected = bf + 0.025
        result = column_base_effective_length_y(nb, a1, a2, bf)
        assert result == pytest.approx(expected)

    def test_rejects_fewer_than_four_anchors(self) -> None:
        with pytest.raises(ValueError):
            column_base_effective_length_y(3, 0.040, 0.100, 0.250)

    @pytest.mark.parametrize("field", ["edge_distance", "anchor_spacing", "flange_width"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {"edge_distance": 0.040, "anchor_spacing": 0.100, "flange_width": 0.250}
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            column_base_effective_length_y(num_anchors=4, **kwargs)


class TestColumnBaseYieldLineM:
    def test_matches_formula(self) -> None:
        lx, d = 0.460, 0.300
        assert column_base_yield_line_m(lx, d) == pytest.approx((lx - 0.95 * d) / 2)

    @pytest.mark.parametrize("field", ["lx", "column_depth"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {"lx": 0.460, "column_depth": 0.300}
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            column_base_yield_line_m(**kwargs)


class TestColumnBaseYieldLineN:
    def test_matches_formula(self) -> None:
        ly, bf = 0.275, 0.250
        assert column_base_yield_line_n(ly, bf) == pytest.approx((ly - 0.80 * bf) / 2)

    @pytest.mark.parametrize("field", ["ly", "flange_width"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {"ly": 0.275, "flange_width": 0.250}
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            column_base_yield_line_n(**kwargs)


class TestColumnBaseYieldLineN0:
    def test_matches_formula(self) -> None:
        d, bf = 0.300, 0.250
        assert column_base_yield_line_n0(d, bf) == pytest.approx(math.sqrt(d * bf) / 4)

    @pytest.mark.parametrize("field", ["column_depth", "flange_width"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {"column_depth": 0.300, "flange_width": 0.250}
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            column_base_yield_line_n0(**kwargs)


class TestColumnBaseXParameter:
    _KWARGS = dict(
        column_depth=0.300, flange_width=0.250, nsd=900_000.0, lx=0.460, ly=0.275,
        sigma_c_rd=30_357_142.857,
    )

    def test_matches_formula(self) -> None:
        d, bf = self._KWARGS["column_depth"], self._KWARGS["flange_width"]
        shape = 4 * d * bf / (d + bf) ** 2
        expected = shape * self._KWARGS["nsd"] / (
            self._KWARGS["lx"] * self._KWARGS["ly"] * self._KWARGS["sigma_c_rd"]
        )
        result = column_base_x_parameter(**self._KWARGS)
        assert result == pytest.approx(expected)

    def test_rejects_x_greater_than_one(self) -> None:
        kwargs = dict(self._KWARGS)
        kwargs["nsd"] = 100_000_000.0
        with pytest.raises(ValueError, match="X"):
            column_base_x_parameter(**kwargs)

    @pytest.mark.parametrize(
        "field", ["column_depth", "flange_width", "nsd", "lx", "ly", "sigma_c_rd"]
    )
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = dict(self._KWARGS)
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            column_base_x_parameter(**kwargs)


class TestColumnBaseLambda:
    def test_matches_formula(self) -> None:
        x = 0.232427
        expected = 2 * math.sqrt(x) / (1 + math.sqrt(1 - x))
        assert column_base_lambda(x) == pytest.approx(expected)

    def test_saturates_at_one(self) -> None:
        assert column_base_lambda(1.0) == pytest.approx(1.0)

    @pytest.mark.parametrize("bad_value", [0.0, -0.1, 1.1, float("nan")])
    def test_rejects_x_outside_0_1(self, bad_value: float) -> None:
        with pytest.raises(ValueError):
            column_base_lambda(bad_value)


class TestColumnBasePlateEffectiveLengthC1:
    def test_takes_maximum(self) -> None:
        assert column_base_plate_effective_length_c1(0.05, 0.03, 0.5, 0.10) == pytest.approx(0.05)
        assert column_base_plate_effective_length_c1(0.02, 0.03, 0.5, 0.10) == pytest.approx(0.05)

    @pytest.mark.parametrize("field", ["m", "n", "lambda_", "n0"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {"m": 0.05, "n": 0.03, "lambda_": 0.5, "n0": 0.10}
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            column_base_plate_effective_length_c1(**kwargs)


class TestColumnBaseConcreteBearingStress:
    def test_matches_formula(self) -> None:
        nsd, lx, ly = 900_000.0, 0.460, 0.275
        assert column_base_concrete_bearing_stress(nsd, lx, ly) == pytest.approx(
            nsd / (lx * ly)
        )

    @pytest.mark.parametrize("field", ["nsd", "lx", "ly"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {"nsd": 900_000.0, "lx": 0.460, "ly": 0.275}
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            column_base_concrete_bearing_stress(**kwargs)


class TestColumnBasePlateMinThicknessCaseC1:
    def test_matches_formula(self) -> None:
        l_max, sigma_c_sd, fy, gamma_a1 = 0.0875, 7_114_624.5, 250e6, 1.10
        expected = l_max * math.sqrt(2 * sigma_c_sd / (fy / gamma_a1))
        result = column_base_plate_min_thickness_case_c1(l_max, sigma_c_sd, fy, gamma_a1)
        assert result == pytest.approx(expected)

    @pytest.mark.parametrize("field", ["l_max", "sigma_c_sd", "fy", "gamma_a1"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {"l_max": 0.0875, "sigma_c_sd": 7_114_624.5, "fy": 250e6, "gamma_a1": 1.10}
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            column_base_plate_min_thickness_case_c1(**kwargs)


class TestConcreteGroutShearFrictionLimit:
    def test_uses_020_fck_when_below_ceiling(self) -> None:
        fck, gamma_c = 20e6, 1.40
        result = concrete_grout_shear_friction_limit(fck, gamma_c)
        assert result == pytest.approx(0.2 * fck / gamma_c)

    def test_saturates_at_4mpa(self) -> None:
        fck, gamma_c = 50e6, 1.20
        result = concrete_grout_shear_friction_limit(fck, gamma_c)
        assert result == pytest.approx(4.0e6)

    @pytest.mark.parametrize("field", ["fck", "gamma_c"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = {"fck": 25e6, "gamma_c": 1.40}
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            concrete_grout_shear_friction_limit(**kwargs)


class TestColumnBaseFrictionShearResistance:
    _KWARGS = dict(
        friction_coefficient=0.45, sigma_c_sd=7_114_624.5, lx=0.460, ly=0.275,
        gamma_a2=1.35, tau_c_rd=3_571_428.57,
    )

    def test_friction_term_governs(self) -> None:
        result = column_base_friction_shear_resistance(**self._KWARGS)
        friction_term = (
            self._KWARGS["friction_coefficient"] * self._KWARGS["sigma_c_sd"]
            * self._KWARGS["lx"] * self._KWARGS["ly"] / self._KWARGS["gamma_a2"]
        )
        assert result == pytest.approx(friction_term, rel=1e-4)

    def test_ceiling_term_governs(self) -> None:
        kwargs = dict(self._KWARGS)
        kwargs["tau_c_rd"] = 1.0
        result = column_base_friction_shear_resistance(**kwargs)
        expected = 1.0 * kwargs["lx"] * kwargs["ly"]
        assert result == pytest.approx(expected)

    @pytest.mark.parametrize(
        "field", ["friction_coefficient", "sigma_c_sd", "lx", "ly", "gamma_a2", "tau_c_rd"]
    )
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = dict(self._KWARGS)
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            column_base_friction_shear_resistance(**kwargs)


class TestColumnBaseCheckResultValidation:
    @pytest.mark.parametrize("bad_value", [0.0, -1.0, float("nan"), float("inf")])
    def test_rejects_non_positive_or_non_finite_demand(self, bad_value: float) -> None:
        with pytest.raises(ValueError):
            ColumnBaseCheckResult(demand=bad_value, capacity=1.0)

    @pytest.mark.parametrize("bad_value", [0.0, -1.0, float("nan"), float("inf")])
    def test_rejects_non_positive_or_non_finite_capacity(self, bad_value: float) -> None:
        with pytest.raises(ValueError):
            ColumnBaseCheckResult(demand=1.0, capacity=bad_value)

    def test_is_ok_and_utilization(self) -> None:
        ok = ColumnBaseCheckResult(demand=1.0, capacity=2.0)
        not_ok = ColumnBaseCheckResult(demand=2.0, capacity=1.0)
        assert ok.is_ok is True
        assert ok.utilization == pytest.approx(0.5)
        assert not_ok.is_ok is False


class TestWorkedExample:
    """Base de pilar hipotética, Caso C1 (compressão concêntrica):
    perfil I/H com ``d=300`` mm, ``bf=250`` mm; placa de base com
    ``a1=40`` mm, ``a2=100`` mm, ``nb=4`` chumbadores (base Tipo 1);
    aço da placa A36 (``fy=250`` MPa); concreto ``fck=25`` MPa; área de
    concreto ``A2=4·A1`` (bloco homotético, o dobro em cada dimensão);
    ``μ=0,45``; combinação normal (``γa1=1,10``, ``γa2=1,35``,
    ``γc=1,40``); ``NSd=900`` kN; ``VSd=50`` kN.

    Valores calculados independentemente por script Python (ver
    ATENÇÃO: não pela própria função) durante o desenvolvimento:
    ``ℓx=0,46`` m, ``ℓy=0,275`` m, ``m=0,0875`` m, ``n=0,0375`` m,
    ``n0≈0,068465`` m, ``σc,Rd≈30,357`` MPa (caso notável em que
    ``A2/A1=4`` faz os dois ramos da fórmula coincidirem exatamente,
    pois ``sqrt(4)=2`` e ``0,85·2=1,7``), ``X≈0,232427``,
    ``λ≈0,513943``, ``ℓmax=m=0,0875`` m (``m`` governa),
    ``σc,Sd≈7,1146`` MPa, ``tp,min≈21,894`` mm, ``τc,Rd≈3,571`` MPa,
    ``VRd=300`` kN (termo de atrito governa).
    """

    _D = 0.300
    _BF = 0.250
    _A1 = 0.040
    _A2 = 0.100
    _NB = 4
    _FY = 250e6
    _FCK = 25e6
    _MU = 0.45
    _GAMMA_A1 = 1.10
    _GAMMA_A2 = 1.35
    _GAMMA_C = 1.40
    _NSD = 900_000.0
    _VSD = 50_000.0

    def _kwargs(self, *, provided_thickness: float) -> dict:
        lx = self._D + 4 * self._A1
        ly = max((0.5 * self._NB - 1) * self._A2 + 2 * self._A1, self._BF + 0.025)
        loaded_area = lx * ly
        return dict(
            nsd=self._NSD,
            vsd=self._VSD,
            provided_thickness=provided_thickness,
            column_depth=self._D,
            flange_width=self._BF,
            edge_distance=self._A1,
            anchor_spacing=self._A2,
            num_anchors=self._NB,
            fy=self._FY,
            fck=self._FCK,
            loaded_area=loaded_area,
            concrete_area=4.0 * loaded_area,
            friction_coefficient=self._MU,
            gamma_a1=self._GAMMA_A1,
            gamma_a2=self._GAMMA_A2,
            gamma_c=self._GAMMA_C,
        )

    def test_geometry_matches_hand_calculation(self) -> None:
        lx = column_base_effective_length_x(self._D, self._A1)
        ly = column_base_effective_length_y(self._NB, self._A1, self._A2, self._BF)
        assert lx == pytest.approx(0.460)
        assert ly == pytest.approx(0.275)

    def test_tp_min_matches_hand_calculation(self) -> None:
        result = check_column_base_case_c1(**self._kwargs(provided_thickness=1.0))
        assert result.thickness.demand == pytest.approx(0.021894013475992846, rel=1e-6)

    def test_sigma_c_rd_matches_hand_calculation(self) -> None:
        result = check_column_base_case_c1(**self._kwargs(provided_thickness=1.0))
        assert result.bearing.capacity == pytest.approx(30_357_142.857142854, rel=1e-6)
        assert result.bearing.demand == pytest.approx(7_114_624.5059288535, rel=1e-6)

    def test_v_rd_matches_hand_calculation(self) -> None:
        result = check_column_base_case_c1(**self._kwargs(provided_thickness=1.0))
        assert result.shear.capacity == pytest.approx(300_000.0, rel=1e-6)

    def test_returns_column_base_case_c1_result(self) -> None:
        result = check_column_base_case_c1(**self._kwargs(provided_thickness=1.0))
        assert isinstance(result, ColumnBaseCaseC1Result)

    def test_is_ok_with_adequate_plate_thickness(self) -> None:
        # tp_min ~ 21,9 mm; fornecendo 25 mm, tudo deve estar ok.
        result = check_column_base_case_c1(**self._kwargs(provided_thickness=0.025))
        assert result.thickness.is_ok is True
        assert result.bearing.is_ok is True
        assert result.shear.is_ok is True
        assert result.is_ok is True

    def test_is_not_ok_with_thin_plate(self) -> None:
        # tp_min ~ 21,9 mm; fornecendo 10 mm, a espessura deve reprovar.
        result = check_column_base_case_c1(**self._kwargs(provided_thickness=0.010))
        assert result.thickness.is_ok is False
        assert result.is_ok is False

    def test_rejects_non_positive_vsd(self) -> None:
        kwargs = self._kwargs(provided_thickness=1.0)
        kwargs["vsd"] = 0.0
        with pytest.raises(ValueError):
            check_column_base_case_c1(**kwargs)

    def test_rejects_non_positive_provided_thickness(self) -> None:
        kwargs = self._kwargs(provided_thickness=0.0)
        with pytest.raises(ValueError):
            check_column_base_case_c1(**kwargs)

    def test_rejects_x_above_one_when_undersized(self) -> None:
        # Placa pequena demais para Nsd -> X>1 -> geometria deve ser alterada.
        kwargs = self._kwargs(provided_thickness=1.0)
        kwargs["nsd"] = 100_000_000.0
        with pytest.raises(ValueError, match="X"):
            check_column_base_case_c1(**kwargs)
