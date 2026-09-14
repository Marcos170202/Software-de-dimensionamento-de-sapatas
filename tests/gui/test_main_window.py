"""Teste de fumaça (offscreen) da janela principal."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QTabWidget

from estrutura_metalica.gui.main_window import MainWindow


def test_main_window_opens_with_expected_title(qapp: QApplication) -> None:
    window = MainWindow()
    assert window.windowTitle() == "Estrutura Metálica — NBR 8800"


def test_main_window_has_tab_widget_with_model_tab(qapp: QApplication) -> None:
    window = MainWindow()
    assert isinstance(window.centralWidget(), QTabWidget)
    assert window.tabs is window.centralWidget()
    assert window.tabs.count() == 1
    assert window.tabs.tabText(0) == "Modelo"
    assert window.tabs.widget(0) is window.model_tab


def test_main_window_show_does_not_raise(qapp: QApplication) -> None:
    window = MainWindow()
    window.show()
    assert window.isVisible()
    window.close()
