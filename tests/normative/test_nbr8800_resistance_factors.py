"""Testes de ``estrutura_metalica.normative.nbr8800.resistance_factors``."""

from __future__ import annotations

import pytest

from estrutura_metalica.normative.nbr8800 import (
    LoadCombinationClass,
    SteelResistanceFactors,
    steel_resistance_factors,
)


@pytest.mark.parametrize(
    ("combination_class", "expected_gamma_a1", "expected_gamma_a2"),
    [
        (LoadCombinationClass.NORMAL, 1.10, 1.35),
        (LoadCombinationClass.ESPECIAL_OU_CONSTRUCAO, 1.10, 1.35),
        (LoadCombinationClass.EXCEPCIONAL, 1.00, 1.15),
    ],
)
def test_steel_resistance_factors_matches_tabela_3(
    combination_class: LoadCombinationClass, expected_gamma_a1: float, expected_gamma_a2: float
) -> None:
    factors = steel_resistance_factors(combination_class)
    assert factors.gamma_a1 == pytest.approx(expected_gamma_a1)
    assert factors.gamma_a2 == pytest.approx(expected_gamma_a2)


@pytest.mark.parametrize("field", ["gamma_a1", "gamma_a2"])
@pytest.mark.parametrize("bad_value", [0.0, -1.0, float("nan"), float("inf")])
def test_rejects_non_positive_or_non_finite_factors(field: str, bad_value: float) -> None:
    kwargs = {"gamma_a1": 1.10, "gamma_a2": 1.35}
    kwargs[field] = bad_value
    with pytest.raises(ValueError):
        SteelResistanceFactors(**kwargs)
