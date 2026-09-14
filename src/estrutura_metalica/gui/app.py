"""Ponto de entrada da aplicação GUI (cria o ``QApplication`` e a
janela principal, e roda o loop de eventos).

Ver ``docs/adr/ADR-001-gui-stack-e-empacotamento.md``.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .main_window import MainWindow


def main(argv: list[str] | None = None) -> int:
    """Cria a aplicação Qt, mostra a janela principal e roda o loop
    de eventos até o usuário fechar a janela.

    ``argv``: argumentos de linha de comando (por padrão,
    ``sys.argv``) — repassados ao ``QApplication`` (aceita as opções
    padrão do Qt, ex.: ``-style``).

    Retorna o código de saída da aplicação (``QApplication.exec()``).
    """
    app = QApplication.instance() or QApplication(argv if argv is not None else sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
