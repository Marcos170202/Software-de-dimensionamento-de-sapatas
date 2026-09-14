"""Aba "Modelo" — lançamento de nós/elementos/apoios/cargas e execução
da análise (Etapas 2, 4 e 5 do processo de modelagem).

Ver ``PROCESSO_MODELAGEM_METALICA.md`` e
``docs/adr/ADR-001-gui-stack-e-empacotamento.md``.

**ATENÇÃO — LIMITAÇÕES DESTE INCREMENTO**:

1. **Catálogo de seções**: só os catálogos cujas entradas são de fato
   :class:`~estrutura_metalica.model.SteelSection` são oferecidos no
   seletor (Gerdau W/H, British Steel UB/UC, Vallourec MSH
   circular/quadrado/retangular) — os catálogos "legado" Gerdau
   I/U/cantoneira/T (:mod:`~estrutura_metalica.model.legacy_profile_catalog`)
   deliberadamente NÃO estendem ``SteelSection`` (faltam
   Zx/Zy/J/Cw — ver ATENÇÃO nesse módulo) e por isso não podem ser
   usados diretamente para montar um :class:`~estrutura_metalica.model.Column`/
   :class:`~estrutura_metalica.model.Beam`/
   :class:`~estrutura_metalica.model.Bracing` nesta fase.
2. **Ligações**: apenas rígida/rotulada — semirrígida
   (:attr:`~estrutura_metalica.model.ConnectionType.SEMI_RIGID`, que
   exige uma rigidez rotacional numérica) fica para um incremento
   futuro.
3. **Apoios**: apenas engaste/rótula
   (:meth:`~estrutura_metalica.analysis.Support.fixed`/
   :meth:`~estrutura_metalica.analysis.Support.pinned`) — uma
   combinação arbitrária de graus de liberdade restringidos
   (``Support`` construído diretamente, necessário para o caso de
   treliças planas — ver ATENÇÃO em ``estrutura_metalica.analysis``)
   fica para um incremento futuro.
4. **Cargas**: um único caso de carga nodal ("Caso 1") — múltiplos
   casos e combinações (NBR 8681) ficam para um incremento futuro,
   assim como cargas distribuídas/peso próprio (ver ATENÇÃO em
   ``estrutura_metalica.analysis.load``, ainda não implementadas no
   próprio motor de cálculo).
5. **Sem edição inline do id do nó nas tabelas de elementos/apoios/
   cargas**: o nó é referenciado digitando o id (inteiro) diretamente
   — a validação de que o id existe no modelo só acontece ao rodar a
   análise (``StructuralModel`` valida as referências).
"""

from __future__ import annotations

from collections.abc import Mapping

from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from estrutura_metalica.analysis import (
    AnalysisError,
    AnalysisResult,
    LoadCase,
    NodalLoad,
    StructuralModel,
    Support,
    solve,
)
from estrutura_metalica.model import (
    BRITISH_STEEL_UB_PROFILES,
    BRITISH_STEEL_UC_PROFILES,
    GERDAU_W_H_PROFILES,
    PINNED_CONNECTION,
    RIGID_CONNECTION,
    STEEL_MATERIAL_CATALOG,
    VALLOUREC_CIRCULAR_HOLLOW_PROFILES,
    VALLOUREC_RECTANGULAR_HOLLOW_PROFILES,
    VALLOUREC_SQUARE_HOLLOW_PROFILES,
    Beam,
    Bracing,
    Column,
    Connection,
    Member,
    Node,
    SteelSection,
)

_SECTION_CATALOGS: dict[str, Mapping[str, SteelSection]] = {
    "Gerdau W/H": GERDAU_W_H_PROFILES,
    "British Steel UB": BRITISH_STEEL_UB_PROFILES,
    "British Steel UC": BRITISH_STEEL_UC_PROFILES,
    "Vallourec Circular": VALLOUREC_CIRCULAR_HOLLOW_PROFILES,
    "Vallourec Quadrado": VALLOUREC_SQUARE_HOLLOW_PROFILES,
    "Vallourec Retangular": VALLOUREC_RECTANGULAR_HOLLOW_PROFILES,
}

_CONNECTIONS: dict[str, Connection] = {
    "Rígida": RIGID_CONNECTION,
    "Rotulada": PINNED_CONNECTION,
}

_MEMBER_TYPES: tuple[str, ...] = ("Pilar", "Viga", "Contraventamento")

_DEFAULT_LOAD_CASE_NAME = "Caso 1"


def _new_id_spinbox(minimum: int = 1, value: int = 1) -> QSpinBox:
    box = QSpinBox()
    box.setRange(minimum, 999_999)
    box.setValue(value)
    return box


def _new_coordinate_spinbox(value: float = 0.0) -> QDoubleSpinBox:
    box = QDoubleSpinBox()
    box.setRange(-1.0e6, 1.0e6)
    box.setDecimals(4)
    box.setValue(value)
    return box


def _new_force_spinbox() -> QDoubleSpinBox:
    box = QDoubleSpinBox()
    box.setRange(-1.0e12, 1.0e12)
    box.setDecimals(2)
    box.setValue(0.0)
    return box


class _TablePanel(QWidget):
    """Base comum das quatro tabelas editáveis (nós/elementos/apoios/
    cargas): um ``QTableWidget`` com botões "Adicionar"/"Remover
    selecionada(s)"."""

    headers: tuple[str, ...] = ()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.table = QTableWidget(0, len(self.headers), self)
        self.table.setHorizontalHeaderLabels(list(self.headers))
        header = self.table.horizontalHeader()
        assert header is not None
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        add_button = QPushButton("Adicionar")
        add_button.clicked.connect(self.add_row)
        remove_button = QPushButton("Remover selecionada(s)")
        remove_button.clicked.connect(self._remove_selected_rows)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(add_button)
        buttons_layout.addWidget(remove_button)
        buttons_layout.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(buttons_layout)
        layout.addWidget(self.table)

    def add_row(self) -> None:  # pragma: no cover - sobrescrito nas subclasses
        raise NotImplementedError

    def _remove_selected_rows(self) -> None:
        rows = sorted({index.row() for index in self.table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.table.removeRow(row)

    @property
    def row_count(self) -> int:
        return self.table.rowCount()


class NodesPanel(_TablePanel):
    """Tabela de nós: id, x, y, z (m)."""

    headers = ("ID", "X (m)", "Y (m)", "Z (m)")

    def add_row(self, node_id: int = 1, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setCellWidget(row, 0, _new_id_spinbox(value=node_id))
        self.table.setCellWidget(row, 1, _new_coordinate_spinbox(x))
        self.table.setCellWidget(row, 2, _new_coordinate_spinbox(y))
        self.table.setCellWidget(row, 3, _new_coordinate_spinbox(z))

    def nodes(self) -> dict[int, Node]:
        """Constrói os :class:`~estrutura_metalica.model.Node` a partir
        das linhas da tabela.

        Levanta ``ValueError`` se dois nós tiverem o mesmo id.
        """
        nodes: dict[int, Node] = {}
        for row in range(self.row_count):
            node_id = self._cell_spinbox(row, 0).value()
            x = self._cell_double_spinbox(row, 1).value()
            y = self._cell_double_spinbox(row, 2).value()
            z = self._cell_double_spinbox(row, 3).value()
            if node_id in nodes:
                raise ValueError(f"Id de nó duplicado na tabela de nós: {node_id!r}.")
            nodes[node_id] = Node(id=node_id, x=x, y=y, z=z)
        return nodes

    def _cell_spinbox(self, row: int, column: int) -> QSpinBox:
        widget = self.table.cellWidget(row, column)
        assert isinstance(widget, QSpinBox)
        return widget

    def _cell_double_spinbox(self, row: int, column: int) -> QDoubleSpinBox:
        widget = self.table.cellWidget(row, column)
        assert isinstance(widget, QDoubleSpinBox)
        return widget


class MembersPanel(_TablePanel):
    """Tabela de elementos: id, tipo, nó inicial/final, catálogo de
    seção + perfil, material, ligações e ângulo de orientação."""

    headers = (
        "ID",
        "Tipo",
        "Nó Inicial",
        "Nó Final",
        "Catálogo",
        "Perfil",
        "Material",
        "Ligação Inicial",
        "Ligação Final",
        "Ângulo (rad)",
    )

    def add_row(self) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setCellWidget(row, 0, _new_id_spinbox(value=row + 1))

        type_combo = QComboBox()
        type_combo.addItems(_MEMBER_TYPES)
        self.table.setCellWidget(row, 1, type_combo)

        self.table.setCellWidget(row, 2, _new_id_spinbox(value=1))
        self.table.setCellWidget(row, 3, _new_id_spinbox(value=2))

        catalog_combo = QComboBox()
        catalog_combo.addItems(sorted(_SECTION_CATALOGS))
        profile_combo = QComboBox()
        catalog_combo.currentTextChanged.connect(
            lambda catalog_name, combo=profile_combo: self._populate_profiles(combo, catalog_name)
        )
        self.table.setCellWidget(row, 4, catalog_combo)
        self.table.setCellWidget(row, 5, profile_combo)
        self._populate_profiles(profile_combo, catalog_combo.currentText())

        material_combo = QComboBox()
        material_combo.addItems(sorted(STEEL_MATERIAL_CATALOG))
        self.table.setCellWidget(row, 6, material_combo)

        # Nota: NÃO ordenado alfabeticamente (ao contrário dos demais
        # combos desta função) — "Rígida" precisa ficar em primeiro
        # lugar (selecionado por padrão ao adicionar uma linha), pelo
        # mesmo motivo de ``_StructuralMember`` usar
        # ``RIGID_CONNECTION`` como padrão (ver members.py):
        # ordenação alfabética colocaria "Rotulada" primeiro (o "í"
        # de "Rígida" vem depois de "o" na comparação de codepoints
        # Unicode), mudando o padrão da UI para rotulada sem intenção.
        start_conn_combo = QComboBox()
        start_conn_combo.addItems(list(_CONNECTIONS))
        self.table.setCellWidget(row, 7, start_conn_combo)

        end_conn_combo = QComboBox()
        end_conn_combo.addItems(list(_CONNECTIONS))
        self.table.setCellWidget(row, 8, end_conn_combo)

        angle_box = QDoubleSpinBox()
        angle_box.setRange(-1000.0, 1000.0)
        angle_box.setDecimals(4)
        self.table.setCellWidget(row, 9, angle_box)

    @staticmethod
    def _populate_profiles(combo: QComboBox, catalog_name: str) -> None:
        combo.clear()
        catalog = _SECTION_CATALOGS.get(catalog_name, {})
        combo.addItems(sorted(catalog))

    def members(self) -> tuple[Member, ...]:
        """Constrói os elementos (:class:`~estrutura_metalica.model.Column`/
        ``Beam``/``Bracing``) a partir das linhas da tabela.

        Levanta ``ValueError`` se o perfil ou o material selecionado
        não existir mais no catálogo (não deveria acontecer via a UI
        normal, só como salvaguarda).
        """
        members: list[Member] = []
        for row in range(self.row_count):
            member_id = self._spinbox(row, 0).value()
            member_type = self._combo(row, 1).currentText()
            start_node_id = self._spinbox(row, 2).value()
            end_node_id = self._spinbox(row, 3).value()
            catalog_name = self._combo(row, 4).currentText()
            profile_name = self._combo(row, 5).currentText()
            material_name = self._combo(row, 6).currentText()
            start_connection_name = self._combo(row, 7).currentText()
            end_connection_name = self._combo(row, 8).currentText()
            angle = self._double_spinbox(row, 9).value()

            section = _SECTION_CATALOGS.get(catalog_name, {}).get(profile_name)
            if section is None:
                raise ValueError(
                    f"Elemento {member_id}: perfil {profile_name!r} não encontrado no "
                    f"catálogo {catalog_name!r}."
                )
            material = STEEL_MATERIAL_CATALOG.get(material_name)
            if material is None:
                raise ValueError(
                    f"Elemento {member_id}: material {material_name!r} não encontrado."
                )
            start_connection = _CONNECTIONS[start_connection_name]
            end_connection = _CONNECTIONS[end_connection_name]

            member: Member
            if member_type == "Pilar":
                member = Column(
                    id=member_id,
                    start_node_id=start_node_id,
                    end_node_id=end_node_id,
                    section=section,
                    material=material,
                    start_connection=start_connection,
                    end_connection=end_connection,
                    orientation_angle=angle,
                )
            elif member_type == "Viga":
                member = Beam(
                    id=member_id,
                    start_node_id=start_node_id,
                    end_node_id=end_node_id,
                    section=section,
                    material=material,
                    start_connection=start_connection,
                    end_connection=end_connection,
                    orientation_angle=angle,
                )
            else:
                member = Bracing(
                    id=member_id,
                    start_node_id=start_node_id,
                    end_node_id=end_node_id,
                    section=section,
                    material=material,
                    orientation_angle=angle,
                )
            members.append(member)
        return tuple(members)

    def _spinbox(self, row: int, column: int) -> QSpinBox:
        widget = self.table.cellWidget(row, column)
        assert isinstance(widget, QSpinBox)
        return widget

    def _double_spinbox(self, row: int, column: int) -> QDoubleSpinBox:
        widget = self.table.cellWidget(row, column)
        assert isinstance(widget, QDoubleSpinBox)
        return widget

    def _combo(self, row: int, column: int) -> QComboBox:
        widget = self.table.cellWidget(row, column)
        assert isinstance(widget, QComboBox)
        return widget


_SUPPORT_KINDS = ("Engaste", "Rótula")


class SupportsPanel(_TablePanel):
    """Tabela de apoios: nó e tipo (engaste ou rótula — ver ATENÇÃO 3
    no docstring do módulo)."""

    headers = ("Nó", "Tipo")

    def add_row(self) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setCellWidget(row, 0, _new_id_spinbox(value=1))
        kind_combo = QComboBox()
        kind_combo.addItems(_SUPPORT_KINDS)
        self.table.setCellWidget(row, 1, kind_combo)

    def supports(self) -> tuple[Support, ...]:
        supports = []
        for row in range(self.row_count):
            node_widget = self.table.cellWidget(row, 0)
            assert isinstance(node_widget, QSpinBox)
            node_id = node_widget.value()
            kind_widget = self.table.cellWidget(row, 1)
            assert isinstance(kind_widget, QComboBox)
            kind = kind_widget.currentText()
            support = Support.fixed(node_id) if kind == "Engaste" else Support.pinned(node_id)
            supports.append(support)
        return tuple(supports)


class LoadsPanel(_TablePanel):
    """Tabela de cargas nodais concentradas, todas no único caso de
    carga desta fase (ver ATENÇÃO 4 no docstring do módulo)."""

    headers = ("Nó", "Fx (N)", "Fy (N)", "Fz (N)", "Mx (N·m)", "My (N·m)", "Mz (N·m)")

    def add_row(self) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setCellWidget(row, 0, _new_id_spinbox(value=1))
        for column in range(1, len(self.headers)):
            self.table.setCellWidget(row, column, _new_force_spinbox())

    def load_case(self, name: str = _DEFAULT_LOAD_CASE_NAME) -> LoadCase:
        loads = []
        for row in range(self.row_count):
            node_widget = self.table.cellWidget(row, 0)
            assert isinstance(node_widget, QSpinBox)
            node_id = node_widget.value()
            values = []
            for column in range(1, len(self.headers)):
                widget = self.table.cellWidget(row, column)
                assert isinstance(widget, QDoubleSpinBox)
                values.append(widget.value())
            fx, fy, fz, mx, my, mz = values
            loads.append(NodalLoad(node_id=node_id, fx=fx, fy=fy, fz=fz, mx=mx, my=my, mz=mz))
        return LoadCase(name=name, loads=tuple(loads))


class ResultsPanel(QWidget):
    """Exibe os deslocamentos e reações de um
    :class:`~estrutura_metalica.analysis.AnalysisResult`."""

    _DISPLACEMENT_HEADERS = ("Nó", "Ux (m)", "Uy (m)", "Uz (m)", "Rx (rad)", "Ry (rad)", "Rz (rad)")
    _REACTION_HEADERS = ("Nó", "Fx (N)", "Fy (N)", "Fz (N)", "Mx (N·m)", "My (N·m)", "Mz (N·m)")

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.displacements_table = QTableWidget(0, len(self._DISPLACEMENT_HEADERS), self)
        self.displacements_table.setHorizontalHeaderLabels(list(self._DISPLACEMENT_HEADERS))
        self.reactions_table = QTableWidget(0, len(self._REACTION_HEADERS), self)
        self.reactions_table.setHorizontalHeaderLabels(list(self._REACTION_HEADERS))

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Deslocamentos"))
        layout.addWidget(self.displacements_table)
        layout.addWidget(QLabel("Reações de apoio"))
        layout.addWidget(self.reactions_table)

    def show_result(self, result: AnalysisResult) -> None:
        self._fill(self.displacements_table, result.displacements)
        self._fill(self.reactions_table, result.reactions)

    def clear(self) -> None:
        self.displacements_table.setRowCount(0)
        self.reactions_table.setRowCount(0)

    @staticmethod
    def _fill(table: QTableWidget, values: dict[int, tuple[float, ...]]) -> None:
        table.setRowCount(0)
        for node_id in sorted(values):
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(str(node_id)))
            for column, component in enumerate(values[node_id], start=1):
                table.setItem(row, column, QTableWidgetItem(f"{component:.6g}"))


class ModelTab(QWidget):
    """Aba "Modelo": sub-abas Nós/Elementos/Apoios/Cargas, botão
    "Rodar análise" e o painel de resultados."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.nodes_panel = NodesPanel()
        self.members_panel = MembersPanel()
        self.supports_panel = SupportsPanel()
        self.loads_panel = LoadsPanel()

        sub_tabs = QTabWidget()
        sub_tabs.addTab(self.nodes_panel, "Nós")
        sub_tabs.addTab(self.members_panel, "Elementos")
        sub_tabs.addTab(self.supports_panel, "Apoios")
        sub_tabs.addTab(self.loads_panel, "Cargas")

        self.run_button = QPushButton("Rodar análise")
        self.run_button.clicked.connect(self.run_analysis)

        self.status_label = QLabel("")

        self.results_panel = ResultsPanel()

        layout = QVBoxLayout(self)
        layout.addWidget(sub_tabs)
        layout.addWidget(self.run_button)
        layout.addWidget(self.status_label)
        layout.addWidget(self.results_panel)

        self.last_result: AnalysisResult | None = None

    def build_model(self) -> StructuralModel:
        """Monta o :class:`~estrutura_metalica.analysis.StructuralModel`
        a partir do conteúdo atual das quatro tabelas.

        Levanta ``ValueError`` (ids duplicados/perfil ou material
        ausente do catálogo, vindos das próprias tabelas) ou o
        ``ValueError`` de validação cruzada de
        :class:`~estrutura_metalica.analysis.StructuralModel`
        (referência a nó inexistente etc.).
        """
        nodes = self.nodes_panel.nodes()
        members = self.members_panel.members()
        supports = self.supports_panel.supports()
        return StructuralModel(nodes=nodes, members=members, supports=supports)

    def run_analysis(self) -> None:
        """Monta o modelo, resolve o caso de carga único e mostra o
        resultado — ou a mensagem de erro, sem interromper a
        aplicação, se o modelo for inválido ou tiver mecanismo."""
        try:
            model = self.build_model()
            load_case = self.loads_panel.load_case()
            result = solve(model, load_case)
        except (ValueError, AnalysisError) as error:
            self.last_result = None
            self.results_panel.clear()
            self.status_label.setText(f"Erro: {error}")
            return

        self.last_result = result
        self.results_panel.show_result(result)
        self.status_label.setText("Análise concluída.")


__all__ = [
    "LoadsPanel",
    "MembersPanel",
    "ModelTab",
    "NodesPanel",
    "ResultsPanel",
    "SupportsPanel",
]
