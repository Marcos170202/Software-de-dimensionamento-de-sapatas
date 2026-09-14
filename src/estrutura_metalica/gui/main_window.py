"""Janela principal da GUI desktop.

Ver ``docs/adr/ADR-001-gui-stack-e-empacotamento.md``.
"""

from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QTabWidget

_WINDOW_TITLE = "Estrutura Metálica — NBR 8800"


class MainWindow(QMainWindow):
    """Janela principal: um ``QTabWidget`` vazio, pronto para receber
    as abas Modelo, Verificações NBR 8800 e Viewport 3D em
    incrementos futuros (ver ``docs/adr/``).
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(_WINDOW_TITLE)
        self.resize(1200, 800)

        self.tabs = QTabWidget(self)
        self.setCentralWidget(self.tabs)
