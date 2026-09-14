"""Janela principal da GUI desktop.

Ver ``docs/adr/ADR-001-gui-stack-e-empacotamento.md``.
"""

from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QTabWidget

from .model_tab import ModelTab

_WINDOW_TITLE = "Estrutura Metálica — NBR 8800"


class MainWindow(QMainWindow):
    """Janela principal: aba "Modelo" (nós/elementos/apoios/cargas +
    execução da análise) e um ``QTabWidget`` pronto para receber as
    próximas abas (Verificações NBR 8800, Viewport 3D — ver
    ``docs/adr/``).
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(_WINDOW_TITLE)
        self.resize(1200, 800)

        self.tabs = QTabWidget(self)
        self.setCentralWidget(self.tabs)

        self.model_tab = ModelTab()
        self.tabs.addTab(self.model_tab, "Modelo")
