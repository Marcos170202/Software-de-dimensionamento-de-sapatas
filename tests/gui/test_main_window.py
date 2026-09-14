"""Teste de fumaça (offscreen) da janela principal."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QTabWidget

from estrutura_metalica.gui.main_window import MainWindow


def test_main_window_opens_with_expected_title(qapp: QApplication) -> None:
    window = MainWindow()
    assert window.windowTitle() == "Estrutura Metálica — NBR 8800"


def test_main_window_has_empty_tab_widget_as_central_widget(qapp: QApplication) -> None:
    window = MainWindow()
    assert isinstance(window.centralWidget(), QTabWidget)
    assert window.tabs is window.centralWidget()
    assert window.tabs.count() == 0


def test_main_window_show_does_not_raise(qapp: QApplication) -> None:
    window = MainWindow()
    window.show()
    assert window.isVisible()
    window.close()
