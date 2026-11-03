"""Testes de ``estrutura_metalica.analysis.model.StructuralModel``."""

from __future__ import annotations

import pytest

from estrutura_metalica.analysis import DOF, StructuralModel, Support
from estrutura_metalica.model import ASTM_A992, Beam, CircularTubeSection, Node

_SECTION = CircularTubeSection.from_dimensions("TC 100x5", d=0.1, t=0.005)


def _beam(id_: int, start: int, end: int) -> Beam:
    return Beam(id=id_, start_node_id=start, end_node_id=end, section=_SECTION, material=ASTM_A992)


def test_requires_at_least_one_node() -> None:
    with pytest.raises(ValueError):
        StructuralModel(nodes={}, members=())


def test_rejects_node_dict_key_mismatch() -> None:
    node = Node(id=1, x=0, y=0, z=0)
    with pytest.raises(ValueError):
        StructuralModel(nodes={2: node}, members=())


def test_accepts_single_node_model() -> None:
    node = Node(id=1, x=0, y=0, z=0)
    model = StructuralModel(nodes={1: node}, members=())
    assert model.dof_count == 6


def test_rejects_duplicate_member_id() -> None:
    nodes = {
        1: Node(id=1, x=0, y=0, z=0),
        2: Node(id=2, x=1, y=0, z=0),
        3: Node(id=3, x=2, y=0, z=0),
    }
    members = (_beam(1, 1, 2), _beam(1, 2, 3))
    with pytest.raises(ValueError):
        StructuralModel(nodes=nodes, members=members)


def test_rejects_member_referencing_missing_start_node() -> None:
    nodes = {1: Node(id=1, x=0, y=0, z=0)}
    with pytest.raises(ValueError):
        StructuralModel(nodes=nodes, members=(_beam(1, 99, 1),))


def test_rejects_member_referencing_missing_end_node() -> None:
    nodes = {1: Node(id=1, x=0, y=0, z=0)}
    with pytest.raises(ValueError):
        StructuralModel(nodes=nodes, members=(_beam(1, 1, 99),))


def test_rejects_support_referencing_missing_node() -> None:
    nodes = {1: Node(id=1, x=0, y=0, z=0)}
    with pytest.raises(ValueError):
        StructuralModel(nodes=nodes, members=(), supports=(Support.fixed(99),))


def test_rejects_duplicate_support_on_same_node() -> None:
    nodes = {1: Node(id=1, x=0, y=0, z=0)}
    with pytest.raises(ValueError):
        StructuralModel(
            nodes=nodes, members=(), supports=(Support.fixed(1), Support.pinned(1))
        )


def test_dof_count_is_six_times_node_count() -> None:
    nodes = {
        1: Node(id=1, x=0, y=0, z=0),
        5: Node(id=5, x=1, y=0, z=0),
        9: Node(id=9, x=2, y=0, z=0),
    }
    model = StructuralModel(nodes=nodes, members=())
    assert model.dof_count == 18


def test_node_local_index_follows_sorted_node_id_order() -> None:
    nodes = {
        5: Node(id=5, x=0, y=0, z=0),
        1: Node(id=1, x=1, y=0, z=0),
        9: Node(id=9, x=2, y=0, z=0),
    }
    model = StructuralModel(nodes=nodes, members=())
    assert model.node_local_index(1) == 0
    assert model.node_local_index(5) == 1
    assert model.node_local_index(9) == 2


def test_global_dof_index() -> None:
    nodes = {5: Node(id=5, x=0, y=0, z=0), 1: Node(id=1, x=1, y=0, z=0)}
    model = StructuralModel(nodes=nodes, members=())
    # nó 1 é o índice local 0, nó 5 é o índice local 1.
    assert model.global_dof_index(1, DOF.UX) == 0
    assert model.global_dof_index(1, DOF.RZ) == 5
    assert model.global_dof_index(5, DOF.UX) == 6
    assert model.global_dof_index(5, DOF.RZ) == 11


def test_restrained_dof_indices() -> None:
    nodes = {1: Node(id=1, x=0, y=0, z=0), 2: Node(id=2, x=1, y=0, z=0)}
    model = StructuralModel(nodes=nodes, members=(), supports=(Support.pinned(1),))
    # nó 1 (índice 0): UX,UY,UZ restringidos -> índices globais 0,1,2.
    assert model.restrained_dof_indices() == frozenset({0, 1, 2})
