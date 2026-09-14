"""Janela principal da GUI desktop.

Ver ``docs/adr/ADR-001-gui-stack-e-empacotamento.md`` e
``docs/adr/ADR-002-viewport-3d.md``.
"""

from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QTabWidget

from .checks_tab import ChecksTab
from .model_tab import ModelTab
from .viewport_3d import ModelViewport

_WINDOW_TITLE = "Estrutura Metálica — NBR 8800"


class MainWindow(QMainWindow):
    """Janela principal: abas "Modelo" (nós/elementos/apoios/cargas +
    execução da análise), "Verificações NBR 8800" (recalculada a cada
    análise bem-sucedida — ver ``ModelTab.analysis_completed``) e
    "Viewport 3D" (geometria redesenhada a cada modelo montado com
    sucesso — ver ``ModelTab.model_built`` — e forma deformada
    sobreposta a cada análise bem-sucedida), num ``QTabWidget``.
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

        self.viewport_tab = ModelViewport()
        self.tabs.addTab(self.viewport_tab, "Viewport 3D")
        self.model_tab.model_built.connect(self.viewport_tab.show_model)
        self.model_tab.analysis_completed.connect(self.viewport_tab.show_deformed_shape)
