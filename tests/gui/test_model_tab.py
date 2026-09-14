"""Testes (offscreen) da aba Modelo."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QComboBox, QDoubleSpinBox, QSpinBox

from estrutura_metalica.gui.model_tab import (
    LoadsPanel,
    MembersPanel,
    ModelTab,
    NodesPanel,
    ResultsPanel,
    SupportsPanel,
)
from estrutura_metalica.model import Beam, Bracing, Column


class TestNodesPanel:
    def test_add_row_increases_row_count(self, qapp: QApplication) -> None:
        panel = NodesPanel()
        assert panel.row_count == 0
        panel.add_row(node_id=1, x=0.0, y=0.0, z=0.0)
        assert panel.row_count == 1

    def test_nodes_builds_expected_node_objects(self, qapp: QApplication) -> None:
        panel = NodesPanel()
        panel.add_row(node_id=1, x=0.0, y=0.0, z=0.0)
        panel.add_row(node_id=2, x=3.0, y=0.0, z=0.0)
        nodes = panel.nodes()
        assert set(nodes) == {1, 2}
        assert (nodes[2].x, nodes[2].y, nodes[2].z) == (3.0, 0.0, 0.0)

    def test_nodes_rejects_duplicate_ids(self, qapp: QApplication) -> None:
        panel = NodesPanel()
        panel.add_row(node_id=1)
        panel.add_row(node_id=1)
        try:
            panel.nodes()
        except ValueError as error:
            assert "duplicado" in str(error)
        else:
            raise AssertionError("esperava ValueError")

    def test_remove_selected_rows(self, qapp: QApplication) -> None:
        panel = NodesPanel()
        panel.add_row(node_id=1)
        panel.add_row(node_id=2)
        panel.table.selectRow(0)
        panel._remove_selected_rows()
        assert panel.row_count == 1
        assert list(panel.nodes()) == [2]


class TestMembersPanel:
    def test_add_row_populates_profile_combo_for_default_catalog(self, qapp: QApplication) -> None:
        panel = MembersPanel()
        panel.add_row()
        profile_combo = panel._combo(0, 5)
        assert profile_combo.count() > 0

    def test_changing_catalog_repopulates_profile_combo(self, qapp: QApplication) -> None:
        panel = MembersPanel()
        panel.add_row()
        catalog_combo = panel._combo(0, 4)
        catalog_combo.setCurrentText("British Steel UB")
        profile_combo = panel._combo(0, 5)
        assert "UB457x191x89" in [profile_combo.itemText(i) for i in range(profile_combo.count())]

    def test_members_builds_column(self, qapp: QApplication) -> None:
        panel = MembersPanel()
        panel.add_row()
        panel._spinbox(0, 0).setValue(1)
        panel._combo(0, 1).setCurrentText("Pilar")
        panel._spinbox(0, 2).setValue(1)
        panel._spinbox(0, 3).setValue(2)
        panel._combo(0, 4).setCurrentText("Gerdau W/H")
        panel._combo(0, 5).setCurrentText("W310x97.0")
        panel._combo(0, 6).setCurrentText("ASTM A992")
        members = panel.members()
        assert len(members) == 1
        assert isinstance(members[0], Column)
        assert members[0].section.name == "W310x97.0"
        assert members[0].material.name == "ASTM A992"

    def test_members_builds_beam(self, qapp: QApplication) -> None:
        panel = MembersPanel()
        panel.add_row()
        panel._combo(0, 1).setCurrentText("Viga")
        members = panel.members()
        assert isinstance(members[0], Beam)

    def test_members_builds_bracing_forcing_pinned_connections(self, qapp: QApplication) -> None:
        panel = MembersPanel()
        panel.add_row()
        panel._combo(0, 1).setCurrentText("Contraventamento")
        # Mesmo selecionando "Rígida" nas colunas de ligação, o
        # Bracing força PINNED nas duas pontas (ver members.py).
        panel._combo(0, 7).setCurrentText("Rígida")
        panel._combo(0, 8).setCurrentText("Rígida")
        members = panel.members()
        assert isinstance(members[0], Bracing)

    def test_members_raises_for_missing_section(self, qapp: QApplication) -> None:
        panel = MembersPanel()
        panel.add_row()
        combo = panel._combo(0, 5)
        combo.clear()
        combo.addItem("perfil-inexistente")
        combo.setCurrentText("perfil-inexistente")
        try:
            panel.members()
        except ValueError as error:
            assert "não encontrado" in str(error)
        else:
            raise AssertionError("esperava ValueError")

    def test_members_raises_for_missing_material(self, qapp: QApplication) -> None:
        panel = MembersPanel()
        panel.add_row()
        combo = panel._combo(0, 6)
        combo.clear()
        combo.addItem("material-inexistente")
        combo.setCurrentText("material-inexistente")
        try:
            panel.members()
        except ValueError as error:
            assert "não encontrado" in str(error)
        else:
            raise AssertionError("esperava ValueError")


class TestSupportsPanel:
    def test_supports_fixed(self, qapp: QApplication) -> None:
        panel = SupportsPanel()
        panel.add_row()
        supports = panel.supports()
        assert len(supports) == 1
        assert len(supports[0].restrained) == 6

    def test_supports_pinned(self, qapp: QApplication) -> None:
        panel = SupportsPanel()
        panel.add_row()
        kind_widget = panel.table.cellWidget(0, 1)
        assert isinstance(kind_widget, QComboBox)
        kind_widget.setCurrentText("Rótula")
        supports = panel.supports()
        assert len(supports[0].restrained) == 3


class TestLoadsPanel:
    def test_load_case_builds_nodal_load(self, qapp: QApplication) -> None:
        panel = LoadsPanel()
        panel.add_row()
        fx_widget = panel.table.cellWidget(0, 1)
        assert isinstance(fx_widget, QDoubleSpinBox)
        fx_widget.setValue(1000.0)
        load_case = panel.load_case()
        assert load_case.name == "Caso 1"
        assert len(load_case.loads) == 1
        assert load_case.loads[0].fx == 1000.0


class TestResultsPanel:
    def test_show_result_fills_tables(self, qapp: QApplication) -> None:
        panel = ResultsPanel()
        from estrutura_metalica.analysis import AnalysisResult

        result = AnalysisResult(
            displacements={1: (0.0,) * 6, 2: (0.001, 0.0, 0.0, 0.0, 0.0, 0.0)},
            reactions={1: (100.0, 0.0, 0.0, 0.0, 0.0, 0.0)},
        )
        panel.show_result(result)
        assert panel.displacements_table.rowCount() == 2
        assert panel.reactions_table.rowCount() == 1

    def test_clear_empties_tables(self, qapp: QApplication) -> None:
        panel = ResultsPanel()
        from estrutura_metalica.analysis import AnalysisResult

        panel.show_result(AnalysisResult(displacements={1: (0.0,) * 6}, reactions={}))
        panel.clear()
        assert panel.displacements_table.rowCount() == 0


class TestModelTabIntegration:
    """Reproduz a viga em balanço de ``tests/analysis/test_solver.py``
    através da UI, ponta a ponta."""

    def _build_cantilever(self, tab: ModelTab) -> None:
        tab.nodes_panel.add_row(node_id=1, x=0.0, y=0.0, z=0.0)
        tab.nodes_panel.add_row(node_id=2, x=3.0, y=0.0, z=0.0)

        tab.members_panel.add_row()
        tab.members_panel._spinbox(0, 0).setValue(1)
        tab.members_panel._combo(0, 1).setCurrentText("Viga")
        tab.members_panel._spinbox(0, 2).setValue(1)
        tab.members_panel._spinbox(0, 3).setValue(2)
        tab.members_panel._combo(0, 4).setCurrentText("British Steel UC")
        tab.members_panel._combo(0, 5).setCurrentText("UC152x152x23")
        tab.members_panel._combo(0, 6).setCurrentText("ASTM A992")

        tab.supports_panel.add_row()  # engaste no nó 1 (padrão)

        tab.loads_panel.add_row()
        load_node_widget = tab.loads_panel.table.cellWidget(0, 0)
        assert isinstance(load_node_widget, QSpinBox)
        load_node_widget.setValue(2)  # carga no nó livre (ponta do balanço)
        fz_widget = tab.loads_panel.table.cellWidget(0, 3)
        assert isinstance(fz_widget, QDoubleSpinBox)
        fz_widget.setValue(-1000.0)

    def test_run_analysis_shows_success_and_populates_results(self, qapp: QApplication) -> None:
        tab = ModelTab()
        self._build_cantilever(tab)

        tab.run_analysis()

        assert tab.last_result is not None
        assert "concluída" in tab.status_label.text()
        assert tab.results_panel.displacements_table.rowCount() == 2
        assert tab.results_panel.reactions_table.rowCount() == 1
        # Nó livre (2) desloca para baixo sob carga Fz negativa.
        uz_free_node = tab.last_result.displacements[2][2]
        assert uz_free_node < 0.0

    def test_run_analysis_reports_error_for_invalid_reference(self, qapp: QApplication) -> None:
        tab = ModelTab()
        tab.nodes_panel.add_row(node_id=1)
        tab.members_panel.add_row()
        tab.members_panel._spinbox(0, 2).setValue(1)
        tab.members_panel._spinbox(0, 3).setValue(999)  # nó inexistente

        tab.run_analysis()

        assert tab.last_result is None
        assert tab.status_label.text().startswith("Erro:")
        assert tab.results_panel.displacements_table.rowCount() == 0

    def test_run_analysis_does_not_emit_model_built_when_model_itself_is_invalid(
        self, qapp: QApplication
    ) -> None:
        """``model_built`` só é emitido depois que ``StructuralModel``
        é montado com sucesso — uma referência de nó inválida num
        ELEMENTO já falha em ``build_model()``, antes disso."""
        tab = ModelTab()
        tab.nodes_panel.add_row(node_id=1)
        tab.members_panel.add_row()
        tab.members_panel._spinbox(0, 2).setValue(1)
        tab.members_panel._spinbox(0, 3).setValue(999)  # nó inexistente
        received: list[object] = []
        tab.model_built.connect(lambda model, load_case: received.append(model))

        tab.run_analysis()

        assert received == []

    def test_run_analysis_emits_model_built_even_when_solve_fails(self, qapp: QApplication) -> None:
        """O modelo em si é válido (``StructuralModel`` aceita), mas o
        CASO DE CARGA referencia um nó inexistente — esse erro só
        aparece dentro de ``solve()``, depois que ``model_built`` já
        deveria ter sido emitido (ver docstring do sinal)."""
        tab = ModelTab()
        self._build_cantilever(tab)
        load_node_widget = tab.loads_panel.table.cellWidget(0, 0)
        assert isinstance(load_node_widget, QSpinBox)
        load_node_widget.setValue(999)  # nó inexistente, só no caso de carga
        received: list[object] = []
        tab.model_built.connect(lambda model, load_case: received.append(model))

        tab.run_analysis()

        assert len(received) == 1
        assert tab.last_result is None
        assert tab.status_label.text().startswith("Erro:")

    def test_build_model_exposes_structural_model(self, qapp: QApplication) -> None:
        tab = ModelTab()
        self._build_cantilever(tab)
        model = tab.build_model()
        assert set(model.nodes) == {1, 2}
        assert len(model.members) == 1
