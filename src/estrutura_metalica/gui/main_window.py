"""Janela principal da GUI desktop.

Ver ``docs/adr/ADR-001-gui-stack-e-empacotamento.md``.
"""

from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QTabWidget

from .checks_tab import ChecksTab
from .model_tab import ModelTab

_WINDOW_TITLE = "Estrutura Metálica — NBR 8800"


class MainWindow(QMainWindow):
    """Janela principal: abas "Modelo" (nós/elementos/apoios/cargas +
    execução da análise) e "Verificações NBR 8800" (recalculada a cada
    análise bem-sucedida — ver ``ModelTab.analysis_completed``), num
    ``QTabWidget`` pronto para receber as próximas abas (Viewport 3D —
    ver ``docs/adr/``).
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(_WINDOW_TITLE)
        self.resize(1200, 800)

        self.tabs = QTabWidget(self)
        self.setCentralWidget(self.tabs)

        self.model_tab = ModelTab()
        self.tabs.addTab(self.model_tab, "Modelo")

        self.checks_tab = ChecksTab()
        self.tabs.addTab(self.checks_tab, "Verificações NBR 8800")
        self.model_tab.analysis_completed.connect(self.checks_tab.update_from)
