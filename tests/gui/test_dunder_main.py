"""Confere que ``estrutura_metalica.gui.__main__`` é importável e
reexporta ``main`` — o bloco ``if __name__ == "__main__":`` em si
(chamada real de ``sys.exit(main())``) é executado apenas quando o
módulo roda como script (``python -m estrutura_metalica.gui``), não
sob importação normal do pytest, por isso tem ``# pragma: no cover``.
"""

from __future__ import annotations

from estrutura_metalica.gui import __main__ as dunder_main
from estrutura_metalica.gui.app import main


def test_dunder_main_reexports_app_main() -> None:
    assert dunder_main.main is main
