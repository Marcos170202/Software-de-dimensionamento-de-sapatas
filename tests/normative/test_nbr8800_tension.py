"""Testes de ``estrutura_metalica.normative.nbr8800.tension``.

O caso em :class:`TestWorkedExample` é um exemplo numérico calculado à
mão a partir das fórmulas da norma (5.2.2-a/b), não apenas o código
comparado consigo mesmo.
"""

from __future__ import annotations

import pytest

from estrutura_metalica.normative.nbr8800 import (
    LoadCombinationClass,
    TensionCheckResult,
    check_tension_member,
    net_area_without_holes,
    steel_resistance_factors,
)


class TestNetAreaWithoutHoles:
    def test_returns_gross_area_unchanged(self) -> None:
        assert net_area_without_holes(0.005) == pytest.approx(0.005)

    @pytest.mark.parametrize("bad_value", [0.0, -1.0, float("nan"), float("inf")])
    def test_rejects_non_positive_or_non_finite(self, bad_value: float) -> None:
        with pytest.raises(ValueError):
            net_area_without_holes(bad_value)


class TestCheckTensionMember:
    def test_rejects_effective_area_larger_than_gross(self) -> None:
        with pytest.raises(ValueError):
            check_tension_member(
                nt_sd=100.0,
                gross_area=0.005,
                effective_net_area=0.006,
                fy=345e6,
                fu=450e6,
                resistance_factors=steel_resistance_factors(LoadCombinationClass.NORMAL),
            )

    @pytest.mark.parametrize("field", ["gross_area", "effective_net_area", "fy", "fu"])
    def test_rejects_non_positive_inputs(self, field: str) -> None:
        kwargs = dict(
            nt_sd=100.0, gross_area=0.005, effective_net_area=0.005, fy=345e6, fu=450e6
        )
        kwargs[field] = 0.0
        with pytest.raises(ValueError):
            check_tension_member(
                resistance_factors=steel_resistance_factors(LoadCombinationClass.NORMAL),
                **kwargs,
            )

    def test_rejects_non_finite_nt_sd(self) -> None:
        with pytest.raises(ValueError):
            check_tension_member(
                nt_sd=float("nan"),
                gross_area=0.005,
                effective_net_area=0.005,
                fy=345e6,
                fu=450e6,
                resistance_factors=steel_resistance_factors(LoadCombinationClass.NORMAL),
            )


class TestTensionCheckResultValidation:
    def test_rejects_non_finite_nt_sd(self) -> None:
        with pytest.raises(ValueError):
            TensionCheckResult(nt_sd=float("nan"), nt_rd_yield=1.0, nt_rd_rupture=1.0)

    def test_rejects_non_positive_nt_rd_yield(self) -> None:
        with pytest.raises(ValueError):
            TensionCheckResult(nt_sd=0.0, nt_rd_yield=0.0, nt_rd_rupture=1.0)

    def test_rejects_non_positive_nt_rd_rupture(self) -> None:
        with pytest.raises(ValueError):
            TensionCheckResult(nt_sd=0.0, nt_rd_yield=1.0, nt_rd_rupture=0.0)

    def test_governing_state_can_be_rupture(self) -> None:
        result = TensionCheckResult(nt_sd=0.0, nt_rd_yield=2.0, nt_rd_rupture=1.0)
        assert result.governing == "ruptura_secao_liquida"
        assert result.nt_rd == pytest.approx(1.0)


class TestWorkedExample:
    """Barra tracionada, aço ASTM A992 (fy=345 MPa, fu=450 MPa), seção
    sem furos com área bruta de 5000 mm² = 0,005 m², combinação normal
    (γa1=1,10, γa2=1,35).

    Cálculo à mão (NBR 8800:2024, 5.2.2):
    - Nt,Rd (escoamento) = Ag·fy/γa1 = 0,005·345e6/1,10 ≈ 1 568 181,8 N
    - Nt,Rd (ruptura, Ae=Ag) = Ag·fu/γa2 = 0,005·450e6/1,35 ≈ 1 666 666,7 N
    - Governa o escoamento (menor valor).
    """

    def _result(self, nt_sd: float) -> TensionCheckResult:
        gross_area = 0.005
        return check_tension_member(
            nt_sd=nt_sd,
            gross_area=gross_area,
            effective_net_area=net_area_without_holes(gross_area),
            fy=345e6,
            fu=450e6,
            resistance_factors=steel_resistance_factors(LoadCombinationClass.NORMAL),
        )

    def test_nt_rd_yield(self) -> None:
        result = self._result(nt_sd=0.0)
        assert result.nt_rd_yield == pytest.approx(0.005 * 345e6 / 1.10, rel=1e-9)

    def test_nt_rd_rupture(self) -> None:
        result = self._result(nt_sd=0.0)
        assert result.nt_rd_rupture == pytest.approx(0.005 * 450e6 / 1.35, rel=1e-9)

    def test_governing_state_is_yield(self) -> None:
        result = self._result(nt_sd=0.0)
        assert result.governing == "escoamento_secao_bruta"
        assert result.nt_rd == pytest.approx(result.nt_rd_yield)

    def test_is_ok_below_capacity(self) -> None:
        result = self._result(nt_sd=1_000_000.0)
        assert result.is_ok is True
        assert result.utilization == pytest.approx(1_000_000.0 / result.nt_rd)

    def test_is_ok_above_capacity(self) -> None:
        result = self._result(nt_sd=2_000_000.0)
        assert result.is_ok is False
