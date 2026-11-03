"""Testes de ``estrutura_metalica.analysis.load``."""

from __future__ import annotations

import pytest

from estrutura_metalica.analysis import LoadCase, NodalLoad


def test_nodal_load_defaults_to_zero() -> None:
    load = NodalLoad(node_id=1)
    assert load.as_vector() == (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


def test_nodal_load_as_vector_order() -> None:
    load = NodalLoad(node_id=1, fx=1.0, fy=2.0, fz=3.0, mx=4.0, my=5.0, mz=6.0)
    assert load.as_vector() == (1.0, 2.0, 3.0, 4.0, 5.0, 6.0)


@pytest.mark.parametrize("field", ["fx", "fy", "fz", "mx", "my", "mz"])
@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), float("-inf")])
def test_rejects_non_finite_components(field: str, bad_value: float) -> None:
    with pytest.raises(ValueError):
        NodalLoad(node_id=1, **{field: bad_value})


def test_load_case_requires_non_empty_name() -> None:
    with pytest.raises(ValueError):
        LoadCase(name="")
    with pytest.raises(ValueError):
        LoadCase(name="   ")


def test_load_case_defaults_to_no_loads() -> None:
    case = LoadCase(name="vazio")
    assert case.loads == ()


def test_load_case_holds_loads() -> None:
    load = NodalLoad(node_id=1, fx=10.0)
    case = LoadCase(name="caso 1", loads=(load,))
    assert case.loads == (load,)
