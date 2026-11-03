"""Testes de ``estrutura_metalica.model.members`` (Column, Beam, Bracing)."""

from __future__ import annotations

import pytest

from estrutura_metalica.model import (
    ASTM_A992,
    PINNED_CONNECTION,
    RIGID_CONNECTION,
    Beam,
    Bracing,
    CircularTubeSection,
    Column,
    Connection,
    ConnectionType,
)

_SECTION = CircularTubeSection.from_dimensions("TC 100x5", d=0.1, t=0.005)


def test_column_defaults_to_rigid_connections() -> None:
    col = Column(id=1, start_node_id=1, end_node_id=2, section=_SECTION, material=ASTM_A992)
    assert col.start_connection is RIGID_CONNECTION
    assert col.end_connection is RIGID_CONNECTION


def test_column_accepts_level_labels() -> None:
    col = Column(
        id=1,
        start_node_id=1,
        end_node_id=2,
        section=_SECTION,
        material=ASTM_A992,
        base_level="térreo",
        top_level="1º pav",
    )
    assert col.base_level == "térreo"
    assert col.top_level == "1º pav"


def test_beam_defaults_to_not_composite() -> None:
    beam = Beam(id=1, start_node_id=1, end_node_id=2, section=_SECTION, material=ASTM_A992)
    assert beam.is_composite is False


def test_beam_can_be_marked_composite() -> None:
    beam = Beam(
        id=1, start_node_id=1, end_node_id=2, section=_SECTION, material=ASTM_A992,
        is_composite=True,
    )
    assert beam.is_composite is True


def test_column_defaults_orientation_angle_to_zero() -> None:
    col = Column(id=1, start_node_id=1, end_node_id=2, section=_SECTION, material=ASTM_A992)
    assert col.orientation_angle == 0.0


def test_column_accepts_custom_orientation_angle() -> None:
    col = Column(
        id=1, start_node_id=1, end_node_id=2, section=_SECTION, material=ASTM_A992,
        orientation_angle=1.5707963267948966,
    )
    assert col.orientation_angle == pytest.approx(1.5707963267948966)


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), float("-inf")])
def test_rejects_non_finite_orientation_angle(bad_value: float) -> None:
    with pytest.raises(ValueError):
        Column(
            id=1, start_node_id=1, end_node_id=2, section=_SECTION, material=ASTM_A992,
            orientation_angle=bad_value,
        )


def test_beam_can_have_semi_rigid_end() -> None:
    semi_rigid = Connection(connection_type=ConnectionType.SEMI_RIGID, rotational_stiffness=5e6)
    beam = Beam(
        id=1, start_node_id=1, end_node_id=2, section=_SECTION, material=ASTM_A992,
        start_connection=semi_rigid,
    )
    assert beam.start_connection.rotational_stiffness == pytest.approx(5e6)


@pytest.mark.parametrize("member_cls", [Column, Beam, Bracing])
def test_member_rejects_same_start_and_end_node(member_cls: type) -> None:
    with pytest.raises(ValueError):
        member_cls(id=1, start_node_id=1, end_node_id=1, section=_SECTION, material=ASTM_A992)


def test_bracing_defaults_to_pinned_at_both_ends() -> None:
    bracing = Bracing(id=1, start_node_id=1, end_node_id=2, section=_SECTION, material=ASTM_A992)
    assert bracing.start_connection is PINNED_CONNECTION
    assert bracing.end_connection is PINNED_CONNECTION


@pytest.mark.parametrize("end", ["start_connection", "end_connection"])
def test_bracing_rejects_non_pinned_connection(end: str) -> None:
    with pytest.raises(ValueError):
        Bracing(
            id=1,
            start_node_id=1,
            end_node_id=2,
            section=_SECTION,
            material=ASTM_A992,
            **{end: RIGID_CONNECTION},
        )


def test_bracing_accepts_explicit_pinned_connections() -> None:
    bracing = Bracing(
        id=1,
        start_node_id=1,
        end_node_id=2,
        section=_SECTION,
        material=ASTM_A992,
        start_connection=PINNED_CONNECTION,
        end_connection=PINNED_CONNECTION,
    )
    assert bracing.start_connection is PINNED_CONNECTION
