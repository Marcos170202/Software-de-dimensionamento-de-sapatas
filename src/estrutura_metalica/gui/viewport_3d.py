"""Viewport 3D do modelo estrutural — PyVista/pyvistaqt.

Ver ``docs/adr/ADR-002-viewport-3d.md`` para as decisões de
representação de cada entidade (cor por tipo de elemento, glifo por
tipo de apoio, seta de carga, escala automática da forma deformada) e
de como este widget se conecta ao resto da GUI (sinais
``ModelTab.model_built``/``ModelTab.analysis_completed``, ver
``MainWindow``). Ver ``docs/adr/ADR-003-insercao-interativa-de-nos.md``
para a inserção de nós por clique (mecanismo de projeção clique→3D,
distinção clique/arraste, diálogo do Shift+clique, grade de
referência).

**ATENÇÃO — ver ADR-002, seção "Consequências", para as limitações
desta fase**: elementos são desenhados como linhas (não a seção real
extrudada — todo elemento tem a mesma espessura visual,
independentemente do perfil real); momentos nodais (``mx``, ``my``,
``mz``) não são desenhados, só a componente de força; o glifo de apoio
distingue só engaste/rótula pela CONTAGEM de graus de liberdade
restringidos (``len(support.restrained) == 6`` → engaste, cubo;
qualquer outra contagem → rótula, cone) — não representa fielmente uma
combinação arbitrária de GDL restringidos construída fora da aba
Modelo.

**ATENÇÃO — ver ADR-003, seção "Consequências", para a inserção de
nós**: só planos horizontais (``z = Z_INSERCAO``, sem inserção fora
desse plano); o nó inserido não é validado (id duplicado etc.) até o
usuário rodar a análise de novo; o limiar de 3px que distingue clique
de arraste de câmera é fixo nesta fase; não há inserção de elementos
por clique, só de nós.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from pyvista import Arrow, Cone, Cube, Plane, PolyData
from pyvistaqt import QtInteractor

from estrutura_metalica.analysis import AnalysisResult, LoadCase, StructuralModel
from estrutura_metalica.model import Beam, Bracing, Column, Member

_ELEMENT_COLORS: dict[type[Member], str] = {
    Column: "blue",
    Beam: "green",
    Bracing: "orange",
}
_DEFAULT_ELEMENT_COLOR = "gray"
"""Cor de um tipo de elemento sem entrada em ``_ELEMENT_COLORS`` —
nunca deveria ocorrer com os três tipos existentes hoje
(``Column``/``Beam``/``Bracing``), mas evita um ``KeyError`` se um
tipo novo for adicionado ao domínio antes de atualizar esta paleta."""

_NODE_POINT_SIZE = 14.0
_FIXED_DOF_COUNT = 6
"""Nº de GDL restringidos que caracteriza um apoio "engaste"
(``Support.fixed``) — ver ATENÇÃO no docstring do módulo."""
_SUPPORT_GLYPH_FRACTION = 0.04
"""Tamanho do glifo de apoio como fração da maior dimensão do
modelo."""
_LOAD_ARROW_FRACTION = 0.25
"""Comprimento da seta da MAIOR carga do caso, como fração da maior
dimensão do modelo — as demais setas são proporcionais a esta."""
_DEFORMED_SHAPE_TARGET_FRACTION = 0.10
"""Fração da maior dimensão do modelo que o maior deslocamento nodal
deve ocupar visualmente, na escala automática da forma deformada."""

_DEFAULT_INSERTION_SCALE = 10.0
"""Tamanho da grade de referência (m) quando ``show_model`` nunca foi
chamado ainda (nenhum modelo desenhado para calcular ``model_scale``)
— ver ``docs/adr/ADR-003-insercao-interativa-de-nos.md``."""
_GRID_RESOLUTION = 10
"""Nº de células da grade de referência em cada direção."""
_DRAG_THRESHOLD_PIXELS = 3.0
"""Distância (px de tela) entre o ``LeftButtonPressEvent`` e o
``LeftButtonReleaseEvent`` abaixo da qual o evento é tratado como
CLIQUE (insere um nó) em vez de arraste de câmera — ver ADR-003,
"Distinguir clique de arraste"."""


def _new_coordinate_spinbox(value: float = 0.0) -> QDoubleSpinBox:
    box = QDoubleSpinBox()
    box.setRange(-1.0e6, 1.0e6)
    box.setDecimals(4)
    box.setValue(value)
    return box


def project_click_to_plane(
    renderer: Any, display_x: float, display_y: float, plane_z: float
) -> tuple[float, float, float]:
    """Projeta um clique de tela (coordenadas de *display* do VTK)
    sobre o plano horizontal ``z = plane_z``, por interseção do raio
    de projeção da câmera com o plano — ver ADR-003, "Mecanismo de
    clique → coordenada 3D (plano de inserção)".

    ``renderer``: tipicamente ``ModelViewport.interactor.renderer``
    (``Any`` porque a VTK não distribui stubs de tipo para
    ``vtkRenderer``/``SetDisplayPoint``/``DisplayToWorld``).
    """
    renderer.SetDisplayPoint(display_x, display_y, 0.0)
    renderer.DisplayToWorld()
    near = np.array(renderer.GetWorldPoint())
    near = near[:3] / near[3]
    renderer.SetDisplayPoint(display_x, display_y, 1.0)
    renderer.DisplayToWorld()
    far = np.array(renderer.GetWorldPoint())
    far = far[:3] / far[3]
    direction = far - near
    t = (plane_z - near[2]) / direction[2]
    point = near + t * direction
    return float(point[0]), float(point[1]), float(point[2])


def _build_coordinate_dialog(
    parent: QWidget | None, x: float, y: float, z: float
) -> tuple[QDialog, QDoubleSpinBox, QDoubleSpinBox, QDoubleSpinBox]:
    """Monta (sem exibir) o diálogo de coordenada exata do Shift+clique
    — separado de :func:`prompt_exact_coordinates` para poder testar a
    edição dos campos sem depender do momento em que ``exec()`` seria
    chamado (modal, bloqueante numa sessão real com display)."""
    dialog = QDialog(parent)
    dialog.setWindowTitle("Coordenada exata do nó")
    layout = QFormLayout(dialog)
    x_box = _new_coordinate_spinbox(x)
    y_box = _new_coordinate_spinbox(y)
    z_box = _new_coordinate_spinbox(z)
    layout.addRow("X (m)", x_box)
    layout.addRow("Y (m)", y_box)
    layout.addRow("Z (m)", z_box)
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addRow(buttons)
    return dialog, x_box, y_box, z_box


def prompt_exact_coordinates(
    parent: QWidget | None, x: float, y: float, z: float
) -> tuple[float, float, float] | None:
    """Diálogo modal (Shift+clique — ver ADR-003) com três campos
    X/Y/Z pré-preenchidos pela coordenada projetada do clique.
    Devolve ``None`` se o usuário cancelar."""
    dialog, x_box, y_box, z_box = _build_coordinate_dialog(parent, x, y, z)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return x_box.value(), y_box.value(), z_box.value()


def node_coordinates(model: StructuralModel) -> dict[int, NDArray[np.float64]]:
    """Coordenadas ``(x, y, z)`` de cada nó do modelo, por id."""
    return {
        node_id: np.array([node.x, node.y, node.z], dtype=np.float64)
        for node_id, node in model.nodes.items()
    }


def model_scale(coordinates: dict[int, NDArray[np.float64]]) -> float:
    """Maior dimensão do modelo (diagonal da caixa envolvente dos
    nós) — usada para dimensionar glifos/setas/escala de forma
    independente da unidade/tamanho absoluto do modelo.

    ``1.0`` como piso para um modelo degenerado (um único nó, ou todos
    os nós coincidentes), para os glifos não terem tamanho zero.
    """
    points = np.array(list(coordinates.values()))
    diagonal = float(np.linalg.norm(points.max(axis=0) - points.min(axis=0)))
    return diagonal if diagonal > 1e-9 else 1.0


def _lines_mesh(
    points: NDArray[np.float64], index_of: dict[int, int], members: list[Member]
) -> PolyData:
    lines: list[int] = []
    for member in members:
        lines.extend([2, index_of[member.start_node_id], index_of[member.end_node_id]])
    return PolyData(points, lines=np.array(lines, dtype=np.int64))


class ModelViewport(QWidget):
    """Widget do viewport 3D — embute um ``pyvistaqt.QtInteractor``
    (``self.interactor``, acessível diretamente, sem camada de
    abstração — ver ADR-002) num layout que também traz os controles
    de inserção interativa de nós por clique (ver
    ``docs/adr/ADR-003-insercao-interativa-de-nos.md``)."""

    node_inserted = Signal(float, float, float)
    """Emitido com ``(x, y, z)`` quando um nó é inserido por clique no
    viewport (modo "Inserir nó" ativo — ver ADR-003). ``MainWindow``
    conecta este sinal a ``ModelTab.add_node_from_viewport`` — este
    módulo nunca importa ``model_tab`` (dependência numa via só, mesmo
    princípio de ``model_built``/``analysis_completed``)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.interactor = QtInteractor(self)

        self._insert_mode = False
        self._press_position: tuple[float, float] | None = None
        self._pending_points: list[tuple[float, float, float]] = []
        self._last_model_scale = _DEFAULT_INSERTION_SCALE

        self.insert_button = QPushButton("Inserir nó (clique no viewport)")
        self.insert_button.setCheckable(True)
        self.insert_button.toggled.connect(self._on_toggle_insert_mode)

        self.plane_z_spinbox = _new_coordinate_spinbox(0.0)
        self.plane_z_spinbox.valueChanged.connect(self._on_plane_z_changed)

        toolbar = QHBoxLayout()
        toolbar.addWidget(self.insert_button)
        toolbar.addWidget(QLabel("Z do plano de inserção (m):"))
        toolbar.addWidget(self.plane_z_spinbox)
        toolbar.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(toolbar)
        layout.addWidget(self.interactor)

        if self.interactor.iren is not None:  # pragma: no cover
            # Sem interactor real em modo offscreen (usado nos testes
            # e em qualquer ambiente sem display — ver
            # pyvistaqt.QtInteractor/pyvista.OFF_SCREEN): não há
            # evento de mouse para observar nesse caso, e por isso
            # este bloco nunca roda sob teste (`# pragma: no cover`,
            # mesmo padrão do guard `if __name__ == "__main__":` em
            # app.py/__main__.py). A lógica de clique em si
            # (``_handle_click`` e o que ela chama) é testada
            # diretamente, sem depender destes observadores — ver
            # ADR-003, "Testes".
            vtk_interactor = self.interactor.iren.interactor
            vtk_interactor.AddObserver("LeftButtonPressEvent", self._on_left_button_press)
            vtk_interactor.AddObserver("LeftButtonReleaseEvent", self._on_left_button_release)

    def show_model(self, model: StructuralModel, load_case: LoadCase | None = None) -> None:
        """Desenha nós, elementos e apoios — e cargas nodais, se
        ``load_case`` for informado. Reconstrução COMPLETA da cena
        (ver ADR-002, "Estratégia de atualização") — chame depois de
        qualquer alteração no modelo lançado nas tabelas da aba
        Modelo.

        Limpa também os marcadores de nós pendentes (ver ADR-003) —
        a essa altura, se o round-trip pela aba Modelo funcionou, eles
        já viraram nós de verdade, desenhados normalmente abaixo.
        """
        self.interactor.clear()
        self._pending_points = []
        coordinates = node_coordinates(model)
        scale = model_scale(coordinates)
        self._last_model_scale = scale
        node_ids = sorted(coordinates)
        index_of = {node_id: i for i, node_id in enumerate(node_ids)}
        points = np.array([coordinates[node_id] for node_id in node_ids])

        self._add_nodes(points, node_ids)
        self._add_elements(list(model.members), points, index_of)
        self._add_supports(model, coordinates, scale)
        if load_case is not None:
            self._add_loads(load_case, coordinates, scale)

        # mypy confunde a assinatura destes dois métodos por causa do
        # decorador interno `_deprecate_positional_args` do pyvista —
        # funcionam normalmente em tempo de execução (conferido
        # manualmente); não é um erro real de tipo.
        self.interactor.reset_camera()  # type: ignore[call-arg]
        self.interactor.view_isometric()  # type: ignore[call-arg]

    def show_deformed_shape(self, model: StructuralModel, result: AnalysisResult) -> None:
        """Sobrepõe a forma deformada (escala automática — ver
        ``_DEFORMED_SHAPE_TARGET_FRACTION``) à geometria já desenhada
        por :meth:`show_model` — NÃO redesenha nós/elementos/apoios/
        cargas nem mexe na câmera (ver ADR-002).

        Se o maior deslocamento nodal for ~zero (modelo não se moveu
        sob o caso de carga resolvido), remove uma forma deformada
        anterior em vez de desenhar uma escala infinita/indefinida.
        """
        coordinates = node_coordinates(model)
        scale = model_scale(coordinates)
        max_displacement = max(
            (
                float(np.linalg.norm(np.array(result.displacements[node_id][:3])))
                for node_id in model.nodes
            ),
            default=0.0,
        )
        if max_displacement <= 1e-12:
            # Mesmo motivo do comentário em show_model (decorador do
            # pyvista confunde o mypy, não um erro real de tipo).
            self.interactor.remove_actor("deformed_shape")  # type: ignore[arg-type]
            return

        deformation_scale = _DEFORMED_SHAPE_TARGET_FRACTION * scale / max_displacement
        node_ids = sorted(coordinates)
        index_of = {node_id: i for i, node_id in enumerate(node_ids)}
        points = np.array(
            [
                coordinates[node_id]
                + np.array(result.displacements[node_id][:3]) * deformation_scale
                for node_id in node_ids
            ]
        )
        mesh = _lines_mesh(points, index_of, list(model.members))
        self.interactor.add_mesh(
            mesh, color="magenta", opacity=0.6, line_width=2, name="deformed_shape"
        )

    def _add_nodes(self, points: NDArray[np.float64], node_ids: list[int]) -> None:
        self.interactor.add_points(
            points,
            render_points_as_spheres=True,
            point_size=_NODE_POINT_SIZE,
            color="white",
            name="nodes",
        )
        self.interactor.add_point_labels(
            points, [str(node_id) for node_id in node_ids], name="node_labels", show_points=False
        )

    def _add_elements(
        self, members: list[Member], points: NDArray[np.float64], index_of: dict[int, int]
    ) -> None:
        by_color: dict[str, list[Member]] = {}
        for member in members:
            color = _ELEMENT_COLORS.get(type(member), _DEFAULT_ELEMENT_COLOR)
            by_color.setdefault(color, []).append(member)
        for color, members_of_color in by_color.items():
            mesh = _lines_mesh(points, index_of, members_of_color)
            self.interactor.add_mesh(mesh, color=color, line_width=4, name=f"elements_{color}")

    def _add_supports(
        self, model: StructuralModel, coordinates: dict[int, NDArray[np.float64]], scale: float
    ) -> None:
        glyph_size = _SUPPORT_GLYPH_FRACTION * scale
        for index, support in enumerate(model.supports):
            center = coordinates[support.node_id]
            if len(support.restrained) == _FIXED_DOF_COUNT:
                glyph = Cube(center=tuple(center)).scale(glyph_size)
            else:
                glyph = Cone(center=tuple(center)).scale(glyph_size)
            self.interactor.add_mesh(glyph, color="red", name=f"support_{index}")

    def _add_loads(
        self,
        load_case: LoadCase,
        coordinates: dict[int, NDArray[np.float64]],
        scale: float,
    ) -> None:
        force_vectors = {
            load.node_id: np.array([load.fx, load.fy, load.fz], dtype=np.float64)
            for load in load_case.loads
        }
        magnitudes = {
            node_id: float(np.linalg.norm(vector)) for node_id, vector in force_vectors.items()
        }
        max_magnitude = max(magnitudes.values(), default=0.0)
        if max_magnitude <= 1e-12:
            return

        for index, (node_id, vector) in enumerate(force_vectors.items()):
            magnitude = magnitudes[node_id]
            if magnitude <= 1e-12:
                continue  # carga só de momento (mx/my/mz) — ver ATENÇÃO no docstring.
            length = _LOAD_ARROW_FRACTION * scale * (magnitude / max_magnitude)
            arrow = Arrow(start=tuple(coordinates[node_id]), direction=tuple(vector), scale=length)
            self.interactor.add_mesh(arrow, color="orange", name=f"load_{index}")

    # -- Inserção interativa de nós (ADR-003) --------------------------

    def _on_toggle_insert_mode(self, checked: bool) -> None:
        self._insert_mode = checked
        if checked:
            self._show_insertion_grid()
        else:
            # Mesmo motivo dos outros `type: ignore[arg-type]` deste
            # módulo (decorador do pyvista confunde o mypy).
            self.interactor.remove_actor("insertion_grid")  # type: ignore[arg-type]

    def _on_plane_z_changed(self, _value: float) -> None:
        if self._insert_mode:
            self._show_insertion_grid()

    def _show_insertion_grid(self) -> None:
        """Grade de referência (*wireframe*) no plano de inserção
        atual — ajuda a perceber posição/profundidade antes de
        clicar (ver ADR-003)."""
        plane_z = self.plane_z_spinbox.value()
        size = self._last_model_scale
        grid = Plane(
            center=(0.0, 0.0, plane_z),
            i_size=size,
            j_size=size,
            i_resolution=_GRID_RESOLUTION,
            j_resolution=_GRID_RESOLUTION,
        )
        self.interactor.add_mesh(grid, style="wireframe", color="gray", name="insertion_grid")

    def _on_left_button_press(self, caller: Any, event: str) -> None:
        if not self._insert_mode:
            return
        self._press_position = tuple(caller.GetEventPosition())

    def _on_left_button_release(self, caller: Any, event: str) -> None:
        if not self._insert_mode or self._press_position is None:
            return
        release_position = tuple(caller.GetEventPosition())
        shift_pressed = bool(caller.GetShiftKey())
        press_position = self._press_position
        self._press_position = None
        self._handle_click(press_position, release_position, shift_pressed)

    def _handle_click(
        self,
        press_position: tuple[float, float],
        release_position: tuple[float, float],
        shift_pressed: bool,
    ) -> None:
        """Lógica de um clique de inserção, já separada da leitura do
        evento VTK em si (``_on_left_button_press``/``_release``) para
        ser testável sem um interactor real — ver ADR-003, "Testes"."""
        dx = release_position[0] - press_position[0]
        dy = release_position[1] - press_position[1]
        if (dx * dx + dy * dy) ** 0.5 > _DRAG_THRESHOLD_PIXELS:
            return  # Arraste de câmera, não um clique.

        plane_z = self.plane_z_spinbox.value()
        x, y, z = project_click_to_plane(
            self.interactor.renderer, release_position[0], release_position[1], plane_z
        )

        if shift_pressed:
            exact = prompt_exact_coordinates(self, x, y, z)
            if exact is None:
                return
            x, y, z = exact

        self._add_pending_node(x, y, z)

    def _add_pending_node(self, x: float, y: float, z: float) -> None:
        """Marca o ponto inserido com uma esfera AMARELA temporária
        (some na próxima reconstrução completa da cena — ver
        ``show_model``) e emite :attr:`node_inserted`."""
        self._pending_points.append((x, y, z))
        self.interactor.add_points(
            np.array(self._pending_points),
            render_points_as_spheres=True,
            point_size=_NODE_POINT_SIZE,
            color="yellow",
            name="pending_node_markers",
        )
        self.node_inserted.emit(x, y, z)


__all__ = [
    "ModelViewport",
    "model_scale",
    "node_coordinates",
    "project_click_to_plane",
    "prompt_exact_coordinates",
]
