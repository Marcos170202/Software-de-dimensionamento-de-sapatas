"""Testes de ``estrutura_metalica.model.Connection``."""

from __future__ import annotations

import pytest

from estrutura_metalica.model import PINNED_CONNECTION, RIGID_CONNECTION, Connection, ConnectionType


def test_rigid_connection_transmits_moment() -> None:
    conn = Connection(connection_type=ConnectionType.RIGID)
    assert conn.transmits_moment is True
    assert conn.rotational_stiffness is None


def test_pinned_connection_does_not_transmit_moment() -> None:
    conn = Connection(connection_type=ConnectionType.PINNED)
    assert conn.transmits_moment is False


def test_semi_rigid_transmits_moment_and_requires_stiffness() -> None:
    conn = Connection(connection_type=ConnectionType.SEMI_RIGID, rotational_stiffness=1e6)
    assert conn.transmits_moment is True
    assert conn.rotational_stiffness == pytest.approx(1e6)


def test_semi_rigid_without_stiffness_is_rejected() -> None:
    with pytest.raises(ValueError):
        Connection(connection_type=ConnectionType.SEMI_RIGID)


def test_semi_rigid_with_non_positive_stiffness_is_rejected() -> None:
    with pytest.raises(ValueError):
        Connection(connection_type=ConnectionType.SEMI_RIGID, rotational_stiffness=0.0)


@pytest.mark.parametrize("connection_type", [ConnectionType.RIGID, ConnectionType.PINNED])
def test_stiffness_not_allowed_outside_semi_rigid(connection_type: ConnectionType) -> None:
    with pytest.raises(ValueError):
        Connection(connection_type=connection_type, rotational_stiffness=1e6)


def test_shared_constants_have_expected_types() -> None:
    assert RIGID_CONNECTION.connection_type is ConnectionType.RIGID
    assert PINNED_CONNECTION.connection_type is ConnectionType.PINNED
