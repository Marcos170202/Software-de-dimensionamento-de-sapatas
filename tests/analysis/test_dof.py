"""Testes de ``estrutura_metalica.analysis.dof``."""

from __future__ import annotations

from estrutura_metalica.analysis.dof import ALL_DOFS, DOF, NUM_DOF_PER_NODE


def test_dof_has_six_members() -> None:
    assert len(DOF) == 6 == NUM_DOF_PER_NODE


def test_dof_values_are_0_to_5_in_declared_order() -> None:
    assert [d.value for d in DOF] == [0, 1, 2, 3, 4, 5]


def test_all_dofs_matches_dof_enum() -> None:
    assert tuple(DOF) == ALL_DOFS
    assert len(ALL_DOFS) == NUM_DOF_PER_NODE
