"""Testes (offscreen) do viewport 3D.

Sem comparação de imagem renderizada (pixel a pixel) — ver
``docs/adr/ADR-002-viewport-3d.md``, seção "Testes". Verifica a
lógica de construção da cena: atores presentes/ausentes, bounds das
malhas, e o cálculo de escala automática.
"""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication, QDialog

from estrutura_metalica.analysis import (
    AnalysisResult,
    LoadCase,
    NodalLoad,
    StructuralModel,
    Support,
    solve,
)
from estrutura_metalica.gui.viewport_3d import (
    ModelViewport,
    _build_coordinate_dialog,
    model_scale,
    node_coordinates,
    project_click_to_plane,
    prompt_exact_coordinates,
)
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


def _configure_deterministic_camera(viewport: ModelViewport) -> tuple[float, float]:
    """Câmera de projeção paralela olhando de cima (eixo Z), janela de
    tamanho fixo — torna ``project_click_to_plane`` previsível o
    bastante para testar sem depender de renderização real (ver
    ADR-003, "Testes"). Devolve o centro de tela ``(cx, cy)``."""
    viewport.interactor.ren_win.SetSize(800, 600)
    viewport.interactor.camera_position = "xy"
    viewport.interactor.camera.parallel_projection = True
    viewport.interactor.camera.parallel_scale = 5.0
    viewport.interactor.render()
    size = viewport.interactor.ren_win.GetSize()
    return size[0] / 2, size[1] / 2


class _FakeVtkCaller:
    """Substitui o ``vtkRenderWindowInteractor`` real nos testes dos
    observadores de clique — só precisa responder
    ``GetEventPosition``/``GetShiftKey`` (ver ADR-003, "Testes")."""

    def __init__(self, position: tuple[float, float], shift: bool = False) -> None:
        self._position = position
        self._shift = shift

    def GetEventPosition(self) -> tuple[float, float]:
        return self._position

    def GetShiftKey(self) -> bool:
        return self._shift


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


class TestProjectClickToPlane:
    def test_center_click_hits_camera_focal_point(self, qapp: QApplication) -> None:
        viewport = ModelViewport()
        cx, cy = _configure_deterministic_camera(viewport)
        point = project_click_to_plane(viewport.interactor.renderer, cx, cy, 0.0)
        assert point == pytest.approx((0.0, 0.0, 0.0), abs=1e-6)

    def test_screen_offset_maps_to_world_offset(self, qapp: QApplication) -> None:
        viewport = ModelViewport()
        cx, cy = _configure_deterministic_camera(viewport)
        point_x = project_click_to_plane(viewport.interactor.renderer, cx + 100, cy, 0.0)
        point_y = project_click_to_plane(viewport.interactor.renderer, cx, cy + 100, 0.0)
        assert point_x == pytest.approx((1.6666667, 0.0, 0.0), abs=1e-5)
        assert point_y == pytest.approx((0.0, 1.6666667, 0.0), abs=1e-5)

    def test_projects_onto_the_requested_plane_z(self, qapp: QApplication) -> None:
        viewport = ModelViewport()
        cx, cy = _configure_deterministic_camera(viewport)
        point = project_click_to_plane(viewport.interactor.renderer, cx + 50, cy, 2.0)
        assert point == pytest.approx((0.8333333, 0.0, 2.0), abs=1e-5)


class TestPromptExactCoordinates:
    def test_confirming_returns_prefilled_values(self, qapp: QApplication) -> None:
        with patch.object(QDialog, "exec", return_value=QDialog.DialogCode.Accepted):
            result = prompt_exact_coordinates(None, 1.0, 2.0, 3.0)
        assert result == (1.0, 2.0, 3.0)

    def test_cancelling_returns_none(self, qapp: QApplication) -> None:
        with patch.object(QDialog, "exec", return_value=QDialog.DialogCode.Rejected):
            result = prompt_exact_coordinates(None, 1.0, 2.0, 3.0)
        assert result is None

    def test_dialog_prefills_boxes_with_projected_coordinate(self, qapp: QApplication) -> None:
        _dialog, x_box, y_box, z_box = _build_coordinate_dialog(None, 1.0, 2.0, 3.0)
        assert (x_box.value(), y_box.value(), z_box.value()) == (1.0, 2.0, 3.0)

    def test_editing_boxes_before_accept_changes_the_result(self, qapp: QApplication) -> None:
        """Mesma lógica de :func:`prompt_exact_coordinates`, mas
        editando os campos antes do ``accept`` — sem depender de
        interceptar o momento exato do ``exec()`` (modal/bloqueante
        numa sessão real com display)."""
        dialog, x_box, y_box, z_box = _build_coordinate_dialog(None, 1.0, 2.0, 3.0)
        x_box.setValue(9.0)
        y_box.setValue(8.0)
        z_box.setValue(7.0)
        dialog.accept()
        assert (x_box.value(), y_box.value(), z_box.value()) == (9.0, 8.0, 7.0)


class TestInsertionToggleAndGrid:
    def test_toggling_on_shows_reference_grid(self, qapp: QApplication) -> None:
        viewport = ModelViewport()
        viewport.insert_button.setChecked(True)
        assert "insertion_grid" in viewport.interactor.renderer.actors

    def test_toggling_off_removes_reference_grid(self, qapp: QApplication) -> None:
        viewport = ModelViewport()
        viewport.insert_button.setChecked(True)
        viewport.insert_button.setChecked(False)
        assert "insertion_grid" not in viewport.interactor.renderer.actors

    def test_changing_plane_z_while_active_redraws_grid_at_new_height(
        self, qapp: QApplication
    ) -> None:
        viewport = ModelViewport()
        viewport.insert_button.setChecked(True)
        viewport.plane_z_spinbox.setValue(5.0)
        bounds = viewport.interactor.renderer.actors["insertion_grid"].mapper.dataset.bounds
        assert bounds.z_min == pytest.approx(5.0)
        assert bounds.z_max == pytest.approx(5.0)

    def test_changing_plane_z_while_inactive_does_not_draw_grid(self, qapp: QApplication) -> None:
        viewport = ModelViewport()
        viewport.plane_z_spinbox.setValue(5.0)
        assert "insertion_grid" not in viewport.interactor.renderer.actors

    def test_show_model_updates_grid_size_reference(self, qapp: QApplication) -> None:
        model, _ = _cantilever()
        viewport = ModelViewport()
        viewport.show_model(model)
        assert viewport._last_model_scale == pytest.approx(3.0)


class TestHandleClick:
    def test_drag_beyond_threshold_is_ignored(self, qapp: QApplication) -> None:
        viewport = ModelViewport()
        _configure_deterministic_camera(viewport)
        viewport.insert_button.setChecked(True)
        received: list[tuple[float, float, float]] = []
        viewport.node_inserted.connect(lambda x, y, z: received.append((x, y, z)))

        viewport._handle_click((100.0, 100.0), (110.0, 100.0), shift_pressed=False)

        assert received == []
        assert "pending_node_markers" not in viewport.interactor.renderer.actors

    def test_plain_click_adds_pending_node_and_emits_signal(self, qapp: QApplication) -> None:
        viewport = ModelViewport()
        cx, cy = _configure_deterministic_camera(viewport)
        viewport.insert_button.setChecked(True)
        received: list[tuple[float, float, float]] = []
        viewport.node_inserted.connect(lambda x, y, z: received.append((x, y, z)))

        viewport._handle_click((cx, cy), (cx, cy), shift_pressed=False)

        assert received == [pytest.approx((0.0, 0.0, 0.0), abs=1e-6)]
        assert "pending_node_markers" in viewport.interactor.renderer.actors

    def test_two_clicks_accumulate_pending_markers(self, qapp: QApplication) -> None:
        viewport = ModelViewport()
        cx, cy = _configure_deterministic_camera(viewport)
        viewport.insert_button.setChecked(True)

        viewport._handle_click((cx, cy), (cx, cy), shift_pressed=False)
        viewport._handle_click((cx + 100, cy), (cx + 100, cy), shift_pressed=False)

        assert len(viewport._pending_points) == 2

    def test_shift_click_uses_dialog_result(self, qapp: QApplication) -> None:
        viewport = ModelViewport()
        cx, cy = _configure_deterministic_camera(viewport)
        viewport.insert_button.setChecked(True)
        received: list[tuple[float, float, float]] = []
        viewport.node_inserted.connect(lambda x, y, z: received.append((x, y, z)))

        with patch(
            "estrutura_metalica.gui.viewport_3d.prompt_exact_coordinates",
            return_value=(9.0, 8.0, 7.0),
        ):
            viewport._handle_click((cx, cy), (cx, cy), shift_pressed=True)

        assert received == [(9.0, 8.0, 7.0)]

    def test_shift_click_cancelled_dialog_adds_nothing(self, qapp: QApplication) -> None:
        viewport = ModelViewport()
        cx, cy = _configure_deterministic_camera(viewport)
        viewport.insert_button.setChecked(True)
        received: list[tuple[float, float, float]] = []
        viewport.node_inserted.connect(lambda x, y, z: received.append((x, y, z)))

        with patch(
            "estrutura_metalica.gui.viewport_3d.prompt_exact_coordinates",
            return_value=None,
        ):
            viewport._handle_click((cx, cy), (cx, cy), shift_pressed=True)

        assert received == []
        assert "pending_node_markers" not in viewport.interactor.renderer.actors

    def test_show_model_clears_pending_points(self, qapp: QApplication) -> None:
        model, _ = _cantilever()
        viewport = ModelViewport()
        _configure_deterministic_camera(viewport)
        viewport.insert_button.setChecked(True)
        viewport._handle_click((400.0, 300.0), (400.0, 300.0), shift_pressed=False)
        assert viewport._pending_points

        viewport.show_model(model)

        assert viewport._pending_points == []
        assert "pending_node_markers" not in viewport.interactor.renderer.actors


class TestLeftButtonObservers:
    def test_press_outside_insert_mode_is_ignored(self, qapp: QApplication) -> None:
        viewport = ModelViewport()
        viewport._on_left_button_press(_FakeVtkCaller((10.0, 10.0)), "LeftButtonPressEvent")
        assert viewport._press_position is None

    def test_release_without_prior_press_is_ignored(self, qapp: QApplication) -> None:
        viewport = ModelViewport()
        viewport.insert_button.setChecked(True)
        received: list[tuple[float, float, float]] = []
        viewport.node_inserted.connect(lambda x, y, z: received.append((x, y, z)))

        viewport._on_left_button_release(_FakeVtkCaller((10.0, 10.0)), "LeftButtonReleaseEvent")

        assert received == []

    def test_full_press_release_cycle_inserts_node(self, qapp: QApplication) -> None:
        viewport = ModelViewport()
        cx, cy = _configure_deterministic_camera(viewport)
        viewport.insert_button.setChecked(True)
        received: list[tuple[float, float, float]] = []
        viewport.node_inserted.connect(lambda x, y, z: received.append((x, y, z)))

        viewport._on_left_button_press(_FakeVtkCaller((cx, cy)), "LeftButtonPressEvent")
        viewport._on_left_button_release(_FakeVtkCaller((cx, cy)), "LeftButtonReleaseEvent")

        assert received == [pytest.approx((0.0, 0.0, 0.0), abs=1e-6)]
        assert viewport._press_position is None
