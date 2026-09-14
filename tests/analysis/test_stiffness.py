"""Testes de ``estrutura_metalica.analysis.stiffness``.

Validação numérica dos casos analíticos clássicos (viga em balanço:
axial, flexão nos dois eixos, torção) está em ``test_solver.py`` (via
:func:`estrutura_metalica.analysis.solve`, que exercita esta matriz
local completa + transformação + montagem). Aqui testam-se as peças
isoladas: eixos locais, matriz local antes/depois da condensação, e a
condensação em si.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from estrutura_metalica.analysis.stiffness import (
    condense,
    element_stiffness_global,
    element_stiffness_local,
    local_axes,
    local_stiffness_matrix,
    member_length,
    transformation_matrix,
)
from estrutura_metalica.model import (
    ASTM_A992,
    Beam,
    Bracing,
    Column,
    Connection,
    ConnectionType,
    Node,
    RectangularTubeSection,
)

_SECTION = RectangularTubeSection.from_dimensions("TR 200x100x8", h=0.2, b=0.1, t=0.008)


def _member(**overrides: object) -> Beam:
    defaults: dict[str, object] = dict(
        id=1, start_node_id=1, end_node_id=2, section=_SECTION, material=ASTM_A992
    )
    defaults.update(overrides)
    return Beam(**defaults)  # type: ignore[arg-type]


class TestMemberLength:
    def test_matches_node_distance(self) -> None:
        a = Node(id=1, x=0, y=0, z=0)
        b = Node(id=2, x=3, y=4, z=0)
        assert member_length(a, b) == pytest.approx(5.0)


class TestLocalAxes:
    def test_horizontal_member_uses_global_z_reference(self) -> None:
        start = Node(id=1, x=0, y=0, z=0)
        end = Node(id=2, x=5, y=0, z=0)
        e1, e2, e3 = local_axes(start, end)
        assert e1 == pytest.approx([1.0, 0.0, 0.0])
        assert e2 == pytest.approx([0.0, 1.0, 0.0])
        assert e3 == pytest.approx([0.0, 0.0, 1.0])

    def test_vertical_member_uses_global_y_reference(self) -> None:
        start = Node(id=1, x=0, y=0, z=0)
        end = Node(id=2, x=0, y=0, z=5)
        e1, e2, e3 = local_axes(start, end)
        assert e1 == pytest.approx([0.0, 0.0, 1.0])
        assert e2 == pytest.approx([1.0, 0.0, 0.0])
        assert e3 == pytest.approx([0.0, 1.0, 0.0])

    def test_axes_are_orthonormal_for_arbitrary_direction(self) -> None:
        start = Node(id=1, x=0, y=0, z=0)
        end = Node(id=2, x=1, y=2, z=3)
        e1, e2, e3 = local_axes(start, end)
        for vector in (e1, e2, e3):
            assert np.linalg.norm(vector) == pytest.approx(1.0)
        assert np.dot(e1, e2) == pytest.approx(0.0, abs=1e-12)
        assert np.dot(e1, e3) == pytest.approx(0.0, abs=1e-12)
        assert np.dot(e2, e3) == pytest.approx(0.0, abs=1e-12)
        # Tripla à direita: e1 x e2 = e3.
        assert np.cross(e1, e2) == pytest.approx(e3, abs=1e-12)

    def test_orientation_angle_rotates_e2_e3_about_e1(self) -> None:
        start = Node(id=1, x=0, y=0, z=0)
        end = Node(id=2, x=5, y=0, z=0)
        e1, e2, e3 = local_axes(start, end, orientation_angle=math.pi / 2)
        assert e1 == pytest.approx([1.0, 0.0, 0.0])
        # Rotação de 90° leva e2 -> e3 original e e3 -> -e2 original.
        assert e2 == pytest.approx([0.0, 0.0, 1.0], abs=1e-12)
        assert e3 == pytest.approx([0.0, -1.0, 0.0], abs=1e-12)

    def test_orientation_angle_zero_is_identity(self) -> None:
        start = Node(id=1, x=0, y=0, z=0)
        end = Node(id=2, x=1, y=1, z=1)
        without = local_axes(start, end)
        with_zero = local_axes(start, end, orientation_angle=0.0)
        for a, b in zip(without, with_zero, strict=True):
            assert a == pytest.approx(b)

    def test_rejects_zero_length_member(self) -> None:
        node = Node(id=1, x=0, y=0, z=0)
        with pytest.raises(ValueError):
            local_axes(node, node)


class TestTransformationMatrix:
    def test_is_orthogonal(self) -> None:
        start = Node(id=1, x=0, y=0, z=0)
        end = Node(id=2, x=1, y=2, z=3)
        t = transformation_matrix(start, end)
        assert t @ t.T == pytest.approx(np.eye(12), abs=1e-12)

    def test_is_block_diagonal_with_repeated_3x3(self) -> None:
        start = Node(id=1, x=0, y=0, z=0)
        end = Node(id=2, x=1, y=2, z=3)
        t = transformation_matrix(start, end)
        block = t[0:3, 0:3]
        for i in range(4):
            assert t[3 * i : 3 * i + 3, 3 * i : 3 * i + 3] == pytest.approx(block)
        # Fora dos blocos diagonais, tudo zero.
        off_diagonal_mask = np.ones((12, 12), dtype=bool)
        for i in range(4):
            off_diagonal_mask[3 * i : 3 * i + 3, 3 * i : 3 * i + 3] = False
        assert np.all(t[off_diagonal_mask] == 0.0)


class TestLocalStiffnessMatrix:
    def test_is_symmetric(self) -> None:
        k = local_stiffness_matrix(_member(), length=3.0)
        assert k == pytest.approx(k.T)

    def test_axial_terms(self) -> None:
        member = _member()
        length = 3.0
        k = local_stiffness_matrix(member, length)
        k_ax = member.material.e * member.section.area / length
        assert k[0, 0] == pytest.approx(k_ax)
        assert k[6, 6] == pytest.approx(k_ax)
        assert k[0, 6] == pytest.approx(-k_ax)

    def test_torsion_terms(self) -> None:
        member = _member()
        length = 3.0
        k = local_stiffness_matrix(member, length)
        k_tor = member.material.shear_modulus * member.section.j / length
        assert k[3, 3] == pytest.approx(k_tor)
        assert k[9, 9] == pytest.approx(k_tor)
        assert k[3, 9] == pytest.approx(-k_tor)

    def test_bending_plane_uses_weak_axis_for_v_theta_z(self) -> None:
        member = _member()
        length = 3.0
        k = local_stiffness_matrix(member, length)
        ei = member.material.e * member.section.iy
        assert k[1, 1] == pytest.approx(12 * ei / length**3)
        assert k[5, 5] == pytest.approx(4 * ei / length)

    def test_bending_plane_uses_strong_axis_for_w_theta_y(self) -> None:
        member = _member()
        length = 3.0
        k = local_stiffness_matrix(member, length)
        ei = member.material.e * member.section.ix
        assert k[2, 2] == pytest.approx(12 * ei / length**3)
        assert k[4, 4] == pytest.approx(4 * ei / length)

    def test_no_coupling_between_axial_torsion_and_bending_planes(self) -> None:
        k = local_stiffness_matrix(_member(), length=3.0)
        axial = (0, 6)
        torsion = (3, 9)
        bend_v = (1, 5, 7, 11)
        bend_w = (2, 4, 8, 10)
        groups = [axial, torsion, bend_v, bend_w]
        for gi, group_i in enumerate(groups):
            for gj, group_j in enumerate(groups):
                if gi == gj:
                    continue
                for i in group_i:
                    for j in group_j:
                        assert k[i, j] == pytest.approx(0.0, abs=1e-9)


class TestCondense:
    def test_empty_condensed_dofs_returns_unchanged_matrix(self) -> None:
        k = local_stiffness_matrix(_member(), length=3.0)
        assert condense(k, ()) is k

    def test_result_is_symmetric(self) -> None:
        k = local_stiffness_matrix(_member(), length=3.0)
        reduced = condense(k, (5, 11))
        assert reduced == pytest.approx(reduced.T)

    def test_condensed_rows_and_columns_are_zeroed(self) -> None:
        k = local_stiffness_matrix(_member(), length=3.0)
        reduced = condense(k, (4, 5, 10, 11))
        for i in (4, 5, 10, 11):
            assert np.all(reduced[i, :] == 0.0)
            assert np.all(reduced[:, i] == 0.0)


class TestElementStiffnessLocal:
    def test_rigid_rigid_matches_local_stiffness_matrix_unchanged(self) -> None:
        member = _member()
        length = 3.0
        assert element_stiffness_local(member, length) == pytest.approx(
            local_stiffness_matrix(member, length)
        )

    def test_pinned_end_condenses_only_bending_rotations_not_torsion(self) -> None:
        pinned = Connection(connection_type=ConnectionType.PINNED)
        member = _member(end_connection=pinned)
        length = 3.0
        k = element_stiffness_local(member, length)
        # Torção continua transmitida (ver limitação documentada).
        k_tor = member.material.shear_modulus * member.section.j / length
        assert k[9, 9] == pytest.approx(k_tor)
        # As rotações de flexão na extremidade final ficam zeradas.
        for i in (10, 11):
            assert np.all(k[i, :] == 0.0)
            assert np.all(k[:, i] == 0.0)

    def test_both_ends_pinned_reduces_to_pure_axial_plus_torsion(self) -> None:
        # Argumento físico: sem carga transversal ao longo do vão e
        # momento fletor nulo nas duas extremidades, o diagrama de
        # momento (linear entre os dois extremos) é identicamente
        # nulo — só sobra esforço axial (e a torção, que este módulo
        # mantém sempre transmitida, ver limitação documentada).
        brace = Bracing(id=1, start_node_id=1, end_node_id=2, section=_SECTION, material=ASTM_A992)
        length = 3.0
        k = element_stiffness_local(brace, length)
        k_ax = brace.material.e * brace.section.area / length
        assert k[0, 0] == pytest.approx(k_ax)
        assert k[6, 6] == pytest.approx(k_ax)
        assert k[0, 6] == pytest.approx(-k_ax)
        bending_dofs = (1, 2, 4, 5, 7, 8, 10, 11)
        for i in bending_dofs:
            assert np.all(np.abs(k[i, :]) < 1e-6)
            assert np.all(np.abs(k[:, i]) < 1e-6)

    def test_semi_rigid_raises_not_implemented(self) -> None:
        semi_rigid = Connection(connection_type=ConnectionType.SEMI_RIGID, rotational_stiffness=1e6)
        member = _member(start_connection=semi_rigid)
        with pytest.raises(NotImplementedError):
            element_stiffness_local(member, length=3.0)


class TestElementStiffnessGlobal:
    def test_is_symmetric(self) -> None:
        start = Node(id=1, x=0, y=0, z=0)
        end = Node(id=2, x=1, y=2, z=3)
        member = _member()
        k = element_stiffness_global(member, start, end)
        assert k == pytest.approx(k.T, abs=1e-6)

    def test_rigid_body_translation_produces_no_force(self) -> None:
        """Deslocar os dois nós igualmente (translação de corpo
        rígido, sem deformar o elemento) não deve gerar força alguma —
        checagem geral de sanidade da matriz de rigidez, independente
        da orientação do elemento."""
        start = Node(id=1, x=0, y=0, z=0)
        end = Node(id=2, x=2, y=3, z=-1)
        member = _member()
        k = element_stiffness_global(member, start, end)
        translation = np.array([0.7, -1.3, 0.4])
        u = np.zeros(12)
        u[0:3] = translation
        u[6:9] = translation
        forces = k @ u
        assert forces == pytest.approx(np.zeros(12), abs=1e-4)

    def test_column_uses_column_class(self) -> None:
        start = Node(id=1, x=0, y=0, z=0)
        end = Node(id=2, x=0, y=0, z=3)
        column = Column(id=1, start_node_id=1, end_node_id=2, section=_SECTION, material=ASTM_A992)
        k = element_stiffness_global(column, start, end)
        assert k.shape == (12, 12)
        assert k == pytest.approx(k.T, abs=1e-6)
