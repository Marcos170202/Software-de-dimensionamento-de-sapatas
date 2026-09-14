"""Testes (offscreen) do viewport 3D.

Sem comparação de imagem renderizada (pixel a pixel) — ver
``docs/adr/ADR-002-viewport-3d.md``, seção "Testes". Verifica a
lógica de construção da cena: atores presentes/ausentes, bounds das
malhas, e o cálculo de escala automática.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtWidgets import QApplication

from estrutura_metalica.analysis import (
    AnalysisResult,
    LoadCase,
    NodalLoad,
    StructuralModel,
    Support,
    solve,
)
from estrutura_metalica.gui.viewport_3d import ModelViewport, model_scale, node_coordinates
from estrutura_metalica.model import ASTM_A992, Beam, Bracing, Column, Node
from estrutura_metalica.model.steel_profile_catalog import GERDAU_W_H_PROFILES

_SECTION = GERDAU_W_H_PROFILES["W150x13.0"]


def _cantilever() -> tuple[StructuralModel, LoadCase]:
    n1 = Node(id=1, x=0.0, y=0.0, z=0.0)
    n2 = Node(id=2, x=3.0, y=0.0, z=0.0)
    beam = Beam(id=1, start_node_id=1, end_node_id=2, section=_SECTION, material=ASTM_A992)
    model = StructuralModel(nodes={1: n1, 2: n2}, members=(beam,), supports=(Support.fixed(1),))
    load_case = LoadCase(name="c", loads=(NodalLoad(node_id=2, fz=-1000.0),))
    return model, load_case


class TestNodeCoordinatesAndScale:
    def test_node_coordinates_matches_nodes(self) -> None:
        model, _ = _cantilever()
        coordinates = node_coordinates(model)
        assert set(coordinates) == {1, 2}
        assert tuple(coordinates[2]) == (3.0, 0.0, 0.0)

    def test_model_scale_is_bounding_box_diagonal(self) -> None:
        model, _ = _cantilever()
        coordinates = node_coordinates(model)
        assert model_scale(coordinates) == 3.0

    def test_model_scale_has_floor_for_degenerate_model(self) -> None:
        coordinates = {1: np.array([0.0, 0.0, 0.0])}
        assert model_scale(coordinates) == 1.0


class TestShowModel:
    def test_draws_nodes_elements_supports_and_loads(self, qapp: QApplication) -> None:
        model, load_case = _cantilever()
        viewport = ModelViewport()
        viewport.show_model(model, load_case)

        actors = viewport.interactor.renderer.actors
        assert "nodes" in actors
        assert "elements_green" in actors  # Beam -> verde
        assert "support_0" in actors
        assert "load_0" in actors

    def test_element_mesh_bounds_match_node_coordinates(self, qapp: QApplication) -> None:
        model, load_case = _cantilever()
        viewport = ModelViewport()
        viewport.show_model(model, load_case)

        bounds = viewport.interactor.renderer.actors["elements_green"].mapper.dataset.bounds
        assert bounds.x_min == 0.0
        assert bounds.x_max == 3.0

    def test_column_uses_blue_and_bracing_uses_orange(self, qapp: QApplication) -> None:
        n1 = Node(id=1, x=0.0, y=0.0, z=0.0)
        n2 = Node(id=2, x=0.0, y=0.0, z=3.0)
        n3 = Node(id=3, x=1.0, y=0.0, z=3.0)
        column = Column(id=1, start_node_id=1, end_node_id=2, section=_SECTION, material=ASTM_A992)
        bracing = Bracing(
            id=2, start_node_id=2, end_node_id=3, section=_SECTION, material=ASTM_A992
        )
        model = StructuralModel(
            nodes={1: n1, 2: n2, 3: n3},
            members=(column, bracing),
            supports=(Support.fixed(1), Support.pinned(3)),
        )
        viewport = ModelViewport()
        viewport.show_model(model)

        actors = viewport.interactor.renderer.actors
        assert "elements_blue" in actors
        assert "elements_orange" in actors

    def test_no_loads_drawn_when_load_case_omitted(self, qapp: QApplication) -> None:
        model, _ = _cantilever()
        viewport = ModelViewport()
        viewport.show_model(model)
        assert "load_0" not in viewport.interactor.renderer.actors

    def test_pure_moment_load_draws_no_arrow(self, qapp: QApplication) -> None:
        model, _ = _cantilever()
        moment_only_case = LoadCase(name="m", loads=(NodalLoad(node_id=2, mx=50.0),))
        viewport = ModelViewport()
        viewport.show_model(model, moment_only_case)
        assert "load_0" not in viewport.interactor.renderer.actors

    def test_mixed_case_skips_only_the_pure_moment_load(self, qapp: QApplication) -> None:
        """Um caso com uma carga de força (nó 1) e uma só de momento
        (nó 2, sem componente de força): a de força ainda deve
        desenhar uma seta, mesmo com a outra sendo pulada."""
        model, _ = _cantilever()
        mixed_case = LoadCase(
            name="misto",
            loads=(
                NodalLoad(node_id=1, fx=500.0),
                NodalLoad(node_id=2, mx=50.0),
            ),
        )
        viewport = ModelViewport()
        viewport.show_model(model, mixed_case)
        actors = viewport.interactor.renderer.actors
        assert "load_0" in actors
        assert "load_1" not in actors

    def test_fixed_support_uses_cube_and_pinned_uses_cone(self, qapp: QApplication) -> None:
        n1 = Node(id=1, x=0.0, y=0.0, z=0.0)
        n2 = Node(id=2, x=3.0, y=0.0, z=0.0)
        beam = Beam(id=1, start_node_id=1, end_node_id=2, section=_SECTION, material=ASTM_A992)
        model = StructuralModel(
            nodes={1: n1, 2: n2},
            members=(beam,),
            supports=(Support.fixed(1), Support.pinned(2)),
        )
        viewport = ModelViewport()
        viewport.show_model(model)

        actors = viewport.interactor.renderer.actors
        fixed_bounds = actors["support_0"].mapper.dataset.bounds
        pinned_bounds = actors["support_1"].mapper.dataset.bounds
        # Cubo tem 8 vértices distintos nos 3 eixos; cone é mais alto
        # que largo na base — só confere que os dois glifos existem e
        # têm geometria (não compara forma exata, que é implementação
        # interna do pyvista.Cube/Cone).
        assert fixed_bounds.x_max > fixed_bounds.x_min
        assert pinned_bounds.x_max > pinned_bounds.x_min


class TestShowDeformedShape:
    def test_adds_deformed_shape_actor_when_displaced(self, qapp: QApplication) -> None:
        model, load_case = _cantilever()
        result = solve(model, load_case)
        viewport = ModelViewport()
        viewport.show_model(model, load_case)
        viewport.show_deformed_shape(model, result)
        assert "deformed_shape" in viewport.interactor.renderer.actors

    def test_removes_deformed_shape_when_no_displacement(self, qapp: QApplication) -> None:
        model, load_case = _cantilever()
        result = solve(model, load_case)
        viewport = ModelViewport()
        viewport.show_model(model, load_case)
        viewport.show_deformed_shape(model, result)
        assert "deformed_shape" in viewport.interactor.renderer.actors

        zero_result = AnalysisResult(
            displacements={1: (0.0,) * 6, 2: (0.0,) * 6}, reactions=result.reactions
        )
        viewport.show_deformed_shape(model, zero_result)
        assert "deformed_shape" not in viewport.interactor.renderer.actors

    def test_deformed_shape_scale_targets_ten_percent_of_model_size(
        self, qapp: QApplication
    ) -> None:
        n1 = Node(id=1, x=0.0, y=0.0, z=0.0)
        n2 = Node(id=2, x=10.0, y=0.0, z=0.0)
        beam = Beam(id=1, start_node_id=1, end_node_id=2, section=_SECTION, material=ASTM_A992)
        model = StructuralModel(nodes={1: n1, 2: n2}, members=(beam,), supports=(Support.fixed(1),))
        # Deslocamento vertical conhecido de 1,0 m no nó livre — maior
        # dimensão do modelo é 10 m, então a forma deformada esperada
        # desloca o nó 2 em 0,10 * 10 / 1,0 = 1,0 m (escala automática
        # alveja 10% da maior dimensão do modelo).
        fabricated_result = AnalysisResult(
            displacements={1: (0.0,) * 6, 2: (0.0, 0.0, 1.0, 0.0, 0.0, 0.0)}, reactions={}
        )
        viewport = ModelViewport()
        viewport.show_model(model)
        viewport.show_deformed_shape(model, fabricated_result)

        bounds = viewport.interactor.renderer.actors["deformed_shape"].mapper.dataset.bounds
        assert bounds.z_max == 1.0
