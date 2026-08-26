"""Interface desktop do SAPATA-7 — escopo AMPLO (carga excêntrica, punção,
bielas e tirantes, rigidez/grelha, recalques por substrato, MEF do solo).

Implementação em `ui/completo/` (pacote com formulário, visualização 3D/2D
e resultado separados por responsabilidade). Este arquivo é só o ponto de
entrada de compatibilidade — mantém `python -m ui.app_completo` funcionando.

Diferença para `ui/app_desktop.py`: aquela cobre só carga centrada, com
motor 100% auditado (ruleset.yaml, regras NBR6122-*). Esta cobre muito mais
casos, mas parte do motor ainda está com status PENDENTE_HUMANO no
ruleset.yaml (seção `escopo_amplo_em_conferencia`) — a tela deixa isso
visível o tempo todo, num banner fixo, não só num popup de abertura.

Uso:
    python -m ui.app_completo
"""
from __future__ import annotations

import sys

if __package__ in (None, ""):
    import pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from ui.completo.app import main

if __name__ == "__main__":
    main()
