"""Testes de ``estrutura_metalica.model.Node``."""

from __future__ import annotations

import math

import pytest

from estrutura_metalica.model import Node


def test_node_holds_coordinates() -> None:
    n = Node(id=1, x=1.0, y=2.0, z=3.0)
    assert (n.id, n.x, n.y, n.z) == (1, 1.0, 2.0, 3.0)


def test_node_is_immutable() -> None:
    n = Node(id=1, x=0.0, y=0.0, z=0.0)
    with pytest.raises(AttributeError):
        n.x = 5.0  # type: ignore[misc]


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), float("-inf")])
def test_node_rejects_non_finite_coordinates(bad_value: float) -> None:
    with pytest.raises(ValueError):
        Node(id=1, x=bad_value, y=0.0, z=0.0)


def test_node_distance_to_pythagorean() -> None:
    a = Node(id=1, x=0.0, y=0.0, z=0.0)
    b = Node(id=2, x=3.0, y=4.0, z=0.0)
    assert a.distance_to(b) == pytest.approx(5.0)


def test_node_distance_to_3d() -> None:
    a = Node(id=1, x=0.0, y=0.0, z=0.0)
    b = Node(id=2, x=1.0, y=2.0, z=2.0)
    assert a.distance_to(b) == pytest.approx(3.0)


def test_node_distance_is_symmetric() -> None:
    a = Node(id=1, x=1.0, y=-1.0, z=2.0)
    b = Node(id=2, x=-3.0, y=4.0, z=0.5)
    assert a.distance_to(b) == pytest.approx(b.distance_to(a))


def test_node_distance_to_self_is_zero() -> None:
    a = Node(id=1, x=1.0, y=2.0, z=3.0)
    assert a.distance_to(a) == pytest.approx(0.0)
    assert math.isclose(a.distance_to(Node(id=2, x=1.0, y=2.0, z=3.0)), 0.0, abs_tol=1e-12)
