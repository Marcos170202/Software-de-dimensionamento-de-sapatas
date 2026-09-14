"""Viewport 3D do modelo estrutural — PyVista/pyvistaqt.

Ver ``docs/adr/ADR-002-viewport-3d.md`` para as decisões de
representação de cada entidade (cor por tipo de elemento, glifo por
tipo de apoio, seta de carga, escala automática da forma deformada) e
de como este widget se conecta ao resto da GUI (sinais
``ModelTab.model_built``/``ModelTab.analysis_completed``, ver
``MainWindow``).

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
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from PySide6.QtWidgets import QVBoxLayout, QWidget
from pyvista import Arrow, Cone, Cube, PolyData
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
    abstração — ver ADR-002, "a arquitetura não deve bloquear a
    inserção interativa de nós de um incremento futuro") num layout
    único."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.interactor = QtInteractor(self)
        layout = QVBoxLayout(self)
        layout.addWidget(self.interactor)

    def show_model(self, model: StructuralModel, load_case: LoadCase | None = None) -> None:
        """Desenha nós, elementos e apoios — e cargas nodais, se
        ``load_case`` for informado. Reconstrução COMPLETA da cena
        (ver ADR-002, "Estratégia de atualização") — chame depois de
        qualquer alteração no modelo lançado nas tabelas da aba
        Modelo."""
        self.interactor.clear()
        coordinates = node_coordinates(model)
        scale = model_scale(coordinates)
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


__all__ = ["ModelViewport", "model_scale", "node_coordinates"]
