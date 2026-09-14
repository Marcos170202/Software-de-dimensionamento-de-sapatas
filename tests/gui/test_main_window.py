"""Teste de fumaça (offscreen) da janela principal."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QSpinBox, QTabWidget

from estrutura_metalica.gui.main_window import MainWindow


def test_main_window_opens_with_expected_title(qapp: QApplication) -> None:
    window = MainWindow()
    assert window.windowTitle() == "Estrutura Metálica — NBR 8800"


def test_main_window_has_tab_widget_with_model_and_checks_tabs(qapp: QApplication) -> None:
    window = MainWindow()
    assert isinstance(window.centralWidget(), QTabWidget)
    assert window.tabs is window.centralWidget()
    assert window.tabs.count() == 2
    assert window.tabs.tabText(0) == "Modelo"
    assert window.tabs.widget(0) is window.model_tab
    assert window.tabs.tabText(1) == "Verificações NBR 8800"
    assert window.tabs.widget(1) is window.checks_tab


def test_running_analysis_updates_checks_tab(qapp: QApplication) -> None:
    window = MainWindow()
    window.model_tab.nodes_panel.add_row(node_id=1, x=0.0, y=0.0, z=0.0)
    window.model_tab.nodes_panel.add_row(node_id=2, x=3.0, y=0.0, z=0.0)
    window.model_tab.members_panel.add_row()
    window.model_tab.members_panel._spinbox(0, 2).setValue(1)
    window.model_tab.members_panel._spinbox(0, 3).setValue(2)
    window.model_tab.supports_panel.add_row()
    window.model_tab.loads_panel.add_row()
    load_node_widget = window.model_tab.loads_panel.table.cellWidget(0, 0)
    assert isinstance(load_node_widget, QSpinBox)
    load_node_widget.setValue(2)

    window.model_tab.run_analysis()

    assert window.checks_tab.table.rowCount() == 1


def test_main_window_show_does_not_raise(qapp: QApplication) -> None:
    window = MainWindow()
    window.show()
    assert window.isVisible()
    window.close()
