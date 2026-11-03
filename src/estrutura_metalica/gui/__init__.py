"""Interface gráfica desktop — camada opcional sobre o motor de cálculo.

Ver ``docs/adr/ADR-001-gui-stack-e-empacotamento.md`` para a decisão
de arquitetura (PySide6 + PyVista/pyvistaqt + PyInstaller) e
``PROCESSO_MODELAGEM_METALICA.md`` para o processo de modelagem que
esta GUI expõe ao usuário.

Este subpacote depende de ``estrutura_metalica.model``/``.analysis``/
``.normative`` (motor de cálculo), nunca o contrário — instalar
``estrutura-metalica`` sozinho (sem o extra ``[gui]``) não requer
Qt/VTK. Ver ``pyproject.toml``, ``[project.optional-dependencies].gui``.

Fases já implementadas: apenas a janela principal vazia
(:class:`~estrutura_metalica.gui.main_window.MainWindow`), preparada
com um ``QTabWidget`` para as próximas abas (Modelo, Verificações
NBR 8800, Viewport 3D).
"""

from __future__ import annotations

__all__: list[str] = []
