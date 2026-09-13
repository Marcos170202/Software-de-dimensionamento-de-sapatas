"""Testes de ``estrutura_metalica.analysis.solver``.

Validação contra fórmulas clássicas de resistência dos materiais
(viga em balanço: axial, flexão nos dois eixos principais, torção) e
contra o equilíbrio de nó de uma treliça simples resolvido à mão —
os valores "expected" abaixo vêm de cálculo analítico independente,
não de rodar o próprio código e comparar consigo mesmo.
"""

from __future__ import annotations

import numpy as np
import pytest

from estrutura_metalica.analysis import (
    DOF,
    AnalysisError,
    LoadCase,
    NodalLoad,
    StructuralModel,
    Support,
    assemble_global_stiffness,
    assemble_load_vector,
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
_E = ASTM_A992.e
_G = ASTM_A992.shear_modulus
_A = _SECTION.area
_IX = _SECTION.ix  # eixo forte
_IY = _SECTION.iy  # eixo fraco
_J = _SECTION.j
_L = 3.0
_BRACE_SECTION = CircularTubeSection.from_dimensions("TC 60x4", d=0.06, t=0.004)


def _bracing(id_: int, start_node_id: int, end_node_id: int) -> Bracing:
    return Bracing(
        id=id_,
        start_node_id=start_node_id,
        end_node_id=end_node_id,
        section=_BRACE_SECTION,
        material=ASTM_A992,
    )


def _cantilever_model() -> tuple[StructuralModel, Beam]:
    """Viga em balanço horizontal (ao longo de X global), engastada no
    nó 1, livre no nó 2 — ver convenção de eixos em
    ``estrutura_metalica.analysis.stiffness``: como o elemento é
    horizontal, o eixo forte resiste à flexão na direção Z global
    (gravidade) e o fraco na direção Y global."""
    n1 = Node(id=1, x=0, y=0, z=0)
    n2 = Node(id=2, x=_L, y=0, z=0)
    beam = Beam(id=1, start_node_id=1, end_node_id=2, section=_SECTION, material=ASTM_A992)
    model = StructuralModel(nodes={1: n1, 2: n2}, members=(beam,), supports=(Support.fixed(1),))
    return model, beam


class TestAssembleGlobalStiffness:
    def test_shape_matches_dof_count(self) -> None:
        model, _ = _cantilever_model()
        k = assemble_global_stiffness(model)
        assert k.shape == (model.dof_count, model.dof_count)

    def test_is_symmetric(self) -> None:
        model, _ = _cantilever_model()
        k = assemble_global_stiffness(model)
        assert k == pytest.approx(k.T, abs=1e-3)


class TestAssembleLoadVector:
    def test_places_load_at_correct_global_index(self) -> None:
        model, _ = _cantilever_model()
        load_case = LoadCase(name="teste", loads=(NodalLoad(node_id=2, fx=100.0, mz=50.0),))
        f = assemble_load_vector(model, load_case)
        assert f[model.global_dof_index(2, DOF.UX)] == pytest.approx(100.0)
        assert f[model.global_dof_index(2, DOF.RZ)] == pytest.approx(50.0)
        assert f[model.global_dof_index(1, DOF.UX)] == pytest.approx(0.0)

    def test_rejects_load_at_unknown_node(self) -> None:
        model, _ = _cantilever_model()
        load_case = LoadCase(name="teste", loads=(NodalLoad(node_id=99, fx=1.0),))
        with pytest.raises(ValueError):
            assemble_load_vector(model, load_case)


class TestCantileverAnalytics:
    """Cada caso compara o deslocamento na ponta livre com a fórmula
    clássica correspondente (Hibbeler/Timoshenko), tolerância relativa
    de 1e-6."""

    def test_axial_elongation(self) -> None:
        model, _ = _cantilever_model()
        p = 1000.0
        result = solve(model, LoadCase(name="axial", loads=(NodalLoad(node_id=2, fx=p),)))
        expected = p * _L / (_E * _A)
        assert result.displacements[2][0] == pytest.approx(expected, rel=1e-6)

    def test_gravity_direction_bending_uses_strong_axis(self) -> None:
        model, _ = _cantilever_model()
        p = 1000.0
        result = solve(model, LoadCase(name="grav", loads=(NodalLoad(node_id=2, fz=-p),)))
        expected = -p * _L**3 / (3 * _E * _IX)
        assert result.displacements[2][2] == pytest.approx(expected, rel=1e-6)

    def test_lateral_bending_uses_weak_axis(self) -> None:
        model, _ = _cantilever_model()
        p = 1000.0
        result = solve(model, LoadCase(name="lat", loads=(NodalLoad(node_id=2, fy=p),)))
        expected = p * _L**3 / (3 * _E * _IY)
        assert result.displacements[2][1] == pytest.approx(expected, rel=1e-6)

    def test_torsion(self) -> None:
        model, _ = _cantilever_model()
        t = 500.0
        result = solve(model, LoadCase(name="tor", loads=(NodalLoad(node_id=2, mx=t),)))
        expected = t * _L / (_G * _J)
        assert result.displacements[2][3] == pytest.approx(expected, rel=1e-6)

    def test_tip_moment_bending(self) -> None:
        """Momento aplicado na ponta em torno de Y global -> flexão no
        eixo forte; rotação na ponta = M·L/(E·Ix) (viga em balanço)."""
        model, _ = _cantilever_model()
        m = 800.0
        result = solve(model, LoadCase(name="momento", loads=(NodalLoad(node_id=2, my=m),)))
        expected = m * _L / (_E * _IX)
        assert result.displacements[2][4] == pytest.approx(expected, rel=1e-6)


class TestReactionsEquilibrium:
    def test_reaction_balances_applied_force_and_moment(self) -> None:
        model, _ = _cantilever_model()
        p = 1000.0
        result = solve(model, LoadCase(name="grav", loads=(NodalLoad(node_id=2, fz=-p),)))
        rx, ry, rz, mx, my, mz = result.reactions[1]
        # Equilíbrio de forças: reação vertical equilibra a carga aplicada.
        assert rz == pytest.approx(p, rel=1e-6)
        assert rx == pytest.approx(0.0, abs=1e-6)
        assert ry == pytest.approx(0.0, abs=1e-6)
        # Equilíbrio de momento em torno do engaste: M = P * L.
        assert my == pytest.approx(-p * _L, rel=1e-6)
        assert mx == pytest.approx(0.0, abs=1e-6)
        assert mz == pytest.approx(0.0, abs=1e-6)

    def test_unrestrained_dof_reaction_component_is_zero(self) -> None:
        """Um apoio parcial (Support.pinned) não tem reação de momento
        — os componentes de rotação do resultado vêm como 0.0."""
        n1 = Node(id=1, x=0, y=0, z=0)
        n2 = Node(id=2, x=_L, y=0, z=0)
        n3 = Node(id=3, x=2 * _L, y=0, z=0)
        beam1 = Beam(id=1, start_node_id=1, end_node_id=2, section=_SECTION, material=ASTM_A992)
        beam2 = Beam(id=2, start_node_id=2, end_node_id=3, section=_SECTION, material=ASTM_A992)
        model = StructuralModel(
            nodes={1: n1, 2: n2, 3: n3},
            members=(beam1, beam2),
            supports=(Support.pinned(1), Support.fixed(3)),
        )
        result = solve(model, LoadCase(name="c", loads=(NodalLoad(node_id=2, fz=-1000.0),)))
        assert result.reactions[1][3:] == pytest.approx((0.0, 0.0, 0.0))


class TestSymmetricTwoBarTruss:
    """Treliça simétrica de 2 barras: A=(-1,0,0) e B=(1,0,0) engastados,
    C=(0,1,0) livre (translações no plano) com carga vertical.
    Solução de equilíbrio de nó calculada à mão (ver comentários) —
    ângulo de 45° em cada barra:

    Força axial nas barras: N = P/√2 (compressão).
    Reação em A: (P/2, P/2, 0). Reação em B: (-P/2, P/2, 0).
    """

    def _build(self, p: float) -> tuple[StructuralModel, LoadCase]:
        n_a = Node(id=1, x=-1, y=0, z=0)
        n_b = Node(id=2, x=1, y=0, z=0)
        n_c = Node(id=3, x=0, y=1, z=0)
        b1 = _bracing(1, 1, 3)
        b2 = _bracing(2, 2, 3)
        supports = (
            Support.fixed(1),
            Support.fixed(2),
            # Treliça plana (todos os nós em z=0): sem apoio algum na
            # translação/rotação fora do plano, o nó C fica com GDL
            # sem nenhuma rigidez (ver limitação documentada em
            # estrutura_metalica.analysis) — restringidos aqui.
            Support(node_id=3, restrained=frozenset({DOF.UZ, DOF.RX, DOF.RY, DOF.RZ})),
        )
        model = StructuralModel(nodes={1: n_a, 2: n_b, 3: n_c}, members=(b1, b2), supports=supports)
        load_case = LoadCase(name="vertical", loads=(NodalLoad(node_id=3, fy=-p),))
        return model, load_case

    def test_reactions_match_hand_calculated_joint_equilibrium(self) -> None:
        p = 1000.0
        model, load_case = self._build(p)
        result = solve(model, load_case)
        rax, ray, raz = result.reactions[1][:3]
        rbx, rby, rbz = result.reactions[2][:3]
        assert (rax, ray, raz) == pytest.approx((p / 2, p / 2, 0.0), abs=1e-6)
        assert (rbx, rby, rbz) == pytest.approx((-p / 2, p / 2, 0.0), abs=1e-6)

    def test_global_force_equilibrium(self) -> None:
        p = 1000.0
        model, load_case = self._build(p)
        result = solve(model, load_case)
        sum_fx = result.reactions[1][0] + result.reactions[2][0]
        sum_fy = result.reactions[1][1] + result.reactions[2][1]
        assert sum_fx == pytest.approx(0.0, abs=1e-6)
        assert sum_fy == pytest.approx(p, rel=1e-6)


class TestAnalysisError:
    def test_raises_when_no_free_dof(self) -> None:
        node = Node(id=1, x=0, y=0, z=0)
        model = StructuralModel(nodes={1: node}, members=(), supports=(Support.fixed(1),))
        with pytest.raises(AnalysisError):
            solve(model, LoadCase(name="vazio"))

    def test_raises_on_planar_truss_without_out_of_plane_restraint(self) -> None:
        n_a = Node(id=1, x=-1, y=0, z=0)
        n_b = Node(id=2, x=1, y=0, z=0)
        n_c = Node(id=3, x=0, y=1, z=0)
        b1 = _bracing(1, 1, 3)
        b2 = _bracing(2, 2, 3)
        # Sem restringir UZ/rotações em C -> mecanismo (ver limitação
        # documentada em estrutura_metalica.analysis).
        model = StructuralModel(
            nodes={1: n_a, 2: n_b, 3: n_c},
            members=(b1, b2),
            supports=(Support.fixed(1), Support.fixed(2)),
        )
        with pytest.raises(AnalysisError):
            solve(model, LoadCase(name="c", loads=(NodalLoad(node_id=3, fy=-1000.0),)))

    def test_wraps_linalg_error_from_solve(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Mesmo quando a checagem de número de condição não pega o
        problema (ou o próprio numpy levanta ``LinAlgError`` por outro
        motivo numérico), a falha deve chegar como ``AnalysisError``,
        não como uma exceção genérica do numpy."""
        model, _ = _cantilever_model()

        def _raise_singular(*_args: object, **_kwargs: object) -> None:
            raise np.linalg.LinAlgError("forçado no teste")

        monkeypatch.setattr("estrutura_metalica.analysis.solver.np.linalg.solve", _raise_singular)
        monkeypatch.setattr(
            "estrutura_metalica.analysis.solver.np.linalg.cond", lambda _matrix: 1.0
        )
        with pytest.raises(AnalysisError):
            solve(model, LoadCase(name="axial", loads=(NodalLoad(node_id=2, fx=1.0),)))
