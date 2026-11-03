"""Testes de ``estrutura_metalica.analysis.internal_forces``.

Validação contra fórmulas clássicas de resistência dos materiais (viga
em balanço: axial, flexão nos dois eixos principais, torção) e contra
o equilíbrio de nó de uma treliça simples resolvido à mão — os valores
"expected" abaixo vêm de cálculo analítico independente, não de rodar
o próprio código e comparar consigo mesmo (mesmas referências de
``tests/analysis/test_solver.py``).
"""

from __future__ import annotations

import pytest

from estrutura_metalica.analysis import (
    DOF,
    LoadCase,
    NodalLoad,
    StructuralModel,
    Support,
    member_internal_forces,
    solve,
)
from estrutura_metalica.model import (
    ASTM_A992,
    Beam,
    Bracing,
    CircularTubeSection,
    Node,
    RectangularTubeSection,
)

_SECTION = RectangularTubeSection.from_dimensions("TR 200x100x8", h=0.2, b=0.1, t=0.008)
_L = 3.0
_BRACE_SECTION = CircularTubeSection.from_dimensions("TC 60x4", d=0.06, t=0.004)


def _cantilever_model() -> tuple[StructuralModel, Beam]:
    """Viga em balanço horizontal (ao longo de X global), engastada no
    nó 1 (índice local 0-5), livre no nó 2 (índice local 6-11) — eixo
    forte resiste à flexão na direção Z global, o fraco na direção Y
    global (elemento horizontal, ângulo de orientação padrão)."""
    n1 = Node(id=1, x=0, y=0, z=0)
    n2 = Node(id=2, x=_L, y=0, z=0)
    beam = Beam(id=1, start_node_id=1, end_node_id=2, section=_SECTION, material=ASTM_A992)
    model = StructuralModel(nodes={1: n1, 2: n2}, members=(beam,), supports=(Support.fixed(1),))
    return model, beam


class TestCantileverAxial:
    def test_tension(self) -> None:
        model, beam = _cantilever_model()
        p = 1000.0
        result = solve(model, LoadCase(name="ax", loads=(NodalLoad(node_id=2, fx=p),)))
        forces = member_internal_forces(model, beam, result)
        assert forces.axial == pytest.approx(p, rel=1e-9)
        assert forces.shear_major_axis == pytest.approx(0.0, abs=1e-6)
        assert forces.shear_minor_axis == pytest.approx(0.0, abs=1e-6)
        assert forces.torque == pytest.approx(0.0, abs=1e-6)
        assert forces.moment_major_axis == pytest.approx(0.0, abs=1e-6)
        assert forces.moment_minor_axis == pytest.approx(0.0, abs=1e-6)

    def test_compression(self) -> None:
        model, beam = _cantilever_model()
        p = 1000.0
        result = solve(model, LoadCase(name="ax", loads=(NodalLoad(node_id=2, fx=-p),)))
        forces = member_internal_forces(model, beam, result)
        assert forces.axial == pytest.approx(-p, rel=1e-9)


class TestCantileverBending:
    def test_major_axis_bending_matches_beam_theory(self) -> None:
        """Carga vertical (Z global) num balanço horizontal solicita o
        eixo forte — momento de engastamento M = P·L, cortante V = P
        (resistência dos materiais clássica)."""
        model, beam = _cantilever_model()
        p = 1000.0
        result = solve(model, LoadCase(name="grav", loads=(NodalLoad(node_id=2, fz=-p),)))
        forces = member_internal_forces(model, beam, result)
        assert forces.moment_major_axis == pytest.approx(p * _L, rel=1e-9)
        assert forces.shear_major_axis == pytest.approx(p, rel=1e-9)
        assert forces.axial == pytest.approx(0.0, abs=1e-6)
        assert forces.torque == pytest.approx(0.0, abs=1e-6)
        assert forces.moment_minor_axis == pytest.approx(0.0, abs=1e-6)
        assert forces.shear_minor_axis == pytest.approx(0.0, abs=1e-6)

    def test_minor_axis_bending_matches_beam_theory(self) -> None:
        """Carga lateral (Y global) num balanço horizontal solicita o
        eixo fraco."""
        model, beam = _cantilever_model()
        p = 1000.0
        result = solve(model, LoadCase(name="lat", loads=(NodalLoad(node_id=2, fy=p),)))
        forces = member_internal_forces(model, beam, result)
        assert forces.moment_minor_axis == pytest.approx(p * _L, rel=1e-9)
        assert forces.shear_minor_axis == pytest.approx(p, rel=1e-9)
        assert forces.moment_major_axis == pytest.approx(0.0, abs=1e-6)
        assert forces.shear_major_axis == pytest.approx(0.0, abs=1e-6)

    def test_torsion(self) -> None:
        model, beam = _cantilever_model()
        t = 500.0
        result = solve(model, LoadCase(name="tor", loads=(NodalLoad(node_id=2, mx=t),)))
        forces = member_internal_forces(model, beam, result)
        assert forces.torque == pytest.approx(t, rel=1e-9)
        assert forces.moment_major_axis == pytest.approx(0.0, abs=1e-6)
        assert forces.moment_minor_axis == pytest.approx(0.0, abs=1e-6)


class TestPinnedBracingHasNoMoment:
    """Treliça plana simples (mesma de
    ``TestTrussEquilibrium`` em ``test_solver.py``) — força axial
    N = P/√2 (compressão) calculada à mão, momento fletor deve ser
    nulo nas duas extremidades rotuladas de cada barra."""

    def _bracing(self, id_: int, start_node_id: int, end_node_id: int) -> Bracing:
        return Bracing(
            id=id_,
            start_node_id=start_node_id,
            end_node_id=end_node_id,
            section=_BRACE_SECTION,
            material=ASTM_A992,
        )

    def _build(self, p: float) -> tuple[StructuralModel, LoadCase, Bracing, Bracing]:
        n_a = Node(id=1, x=-1, y=0, z=0)
        n_b = Node(id=2, x=1, y=0, z=0)
        n_c = Node(id=3, x=0, y=1, z=0)
        b1 = self._bracing(1, 1, 3)
        b2 = self._bracing(2, 2, 3)
        supports = (
            Support.fixed(1),
            Support.fixed(2),
            Support(node_id=3, restrained=frozenset({DOF.UZ, DOF.RX, DOF.RY, DOF.RZ})),
        )
        model = StructuralModel(nodes={1: n_a, 2: n_b, 3: n_c}, members=(b1, b2), supports=supports)
        load_case = LoadCase(name="vertical", loads=(NodalLoad(node_id=3, fy=-p),))
        return model, load_case, b1, b2

    def test_axial_force_matches_hand_calculation(self) -> None:
        p = 1000.0
        model, load_case, b1, b2 = self._build(p)
        result = solve(model, load_case)
        expected_n = -p / 2**0.5  # compressão
        forces_b1 = member_internal_forces(model, b1, result)
        forces_b2 = member_internal_forces(model, b2, result)
        assert forces_b1.axial == pytest.approx(expected_n, rel=1e-6)
        assert forces_b2.axial == pytest.approx(expected_n, rel=1e-6)

    def test_pinned_ends_have_zero_bending_moment(self) -> None:
        p = 1000.0
        model, load_case, b1, b2 = self._build(p)
        result = solve(model, load_case)
        for member in (b1, b2):
            forces = member_internal_forces(model, member, result)
            assert forces.moment_major_axis == pytest.approx(0.0, abs=1e-6)
            assert forces.moment_minor_axis == pytest.approx(0.0, abs=1e-6)
