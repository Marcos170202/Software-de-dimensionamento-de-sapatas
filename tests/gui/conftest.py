"""Configuração de teste para a GUI — força o backend Qt offscreen
antes de qualquer ``QApplication``, para rodar sem display real
(mesmo mecanismo do CI — ver docs/adr/ADR-001-gui-stack-e-empacotamento.md).
"""

from __future__ import annotations

import os

import pytest
import pyvista
from PySide6.QtWidgets import QApplication

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pyvista.OFF_SCREEN = True


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """``QApplication`` única para toda a sessão de testes — o Qt não
    permite mais de uma instância viva por processo."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    assert isinstance(app, QApplication)
    return app
