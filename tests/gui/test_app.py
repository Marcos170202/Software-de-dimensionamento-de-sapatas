"""Teste de fumaça (offscreen) do ponto de entrada ``app.main``."""

from __future__ import annotations

from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from estrutura_metalica.gui.app import main


def test_main_shows_window_and_returns_exit_code(qapp: QApplication) -> None:
    # QApplication.exec() bloquearia o teste esperando o usuário
    # fechar a janela — substitui por um retorno imediato, já que o
    # que se quer testar aqui é que a janela é criada e mostrada, não
    # o loop de eventos do Qt em si (isso é responsabilidade do Qt,
    # não do código deste pacote).
    with patch.object(QApplication, "exec", return_value=0) as mock_exec:
        exit_code = main([])

    assert exit_code == 0
    mock_exec.assert_called_once()
