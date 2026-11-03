"""Verificações normativas — Etapa 6 do processo de modelagem
("Dimensionamento").

Ver ``PROCESSO_MODELAGEM_METALICA.md`` na raiz do repositório.

Pacote de plugin: deliberadamente separado do núcleo
``estrutura_metalica.model``/``estrutura_metalica.analysis`` — o motor
de análise permanece agnóstico de norma; ``normative.nbr8800`` só
consome as propriedades já expostas por ``SteelSection``/
``SteelMaterial`` (nunca o contrário).
"""

from __future__ import annotations
