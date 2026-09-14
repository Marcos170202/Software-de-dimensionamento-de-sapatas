"""Testes de ``estrutura_metalica.analysis.support``."""

from __future__ import annotations

import pytest

from estrutura_metalica.analysis import DOF, Support


def test_fixed_restrains_all_six_dofs() -> None:
    support = Support.fixed(node_id=1)
    assert support.restrained == frozenset(DOF)


def test_pinned_restrains_only_translations() -> None:
    support = Support.pinned(node_id=1)
    assert support.restrained == frozenset({DOF.UX, DOF.UY, DOF.UZ})


def test_rejects_empty_restrained_set() -> None:
    with pytest.raises(ValueError):
        Support(node_id=1, restrained=frozenset())


def test_custom_partial_support() -> None:
    support = Support(node_id=5, restrained=frozenset({DOF.UZ, DOF.RX}))
    assert support.node_id == 5
    assert support.restrained == frozenset({DOF.UZ, DOF.RX})
