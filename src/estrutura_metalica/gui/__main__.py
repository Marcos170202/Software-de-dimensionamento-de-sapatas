"""Ponto de entrada via ``python -m estrutura_metalica.gui``."""

from __future__ import annotations

import sys

from .app import main

if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
