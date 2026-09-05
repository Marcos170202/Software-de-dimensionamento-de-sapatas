"""
ui.completo
===========
Interface desktop do escopo AMPLO do SAPATA-7 (`calc_core.sapata_isolada`):
carga excêntrica, punção, bielas e tirantes, rigidez/grelha, recalques e MEF
do solo.

Reproduz o layout de três colunas (entrada / visualização / resultado) mais
barra superior e barra de status, todo derivado dos objetos de
`calc_core.sapata_isolada` — esta camada não calcula nada, só coleta entrada
e formata saída (ver `a3-interface.md` / `CLAUDE.md`).

Uso:
    python -m ui.completo
    # ou, mantendo compatibilidade:
    python -m ui.app_completo
"""
from __future__ import annotations

from .app import AppSapataCompleto, main

__all__ = ["AppSapataCompleto", "main"]
