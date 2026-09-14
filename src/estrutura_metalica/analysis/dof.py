"""Graus de liberdade (GDL) — Etapa 4 do processo de modelagem
("6 GDL por nó", igual ao HyperFrame)."""

from __future__ import annotations

from enum import Enum


class DOF(Enum):
    """Um dos 6 graus de liberdade de um nó no espaço 3D: três
    translações e três rotações.
    """

    UX = 0
    UY = 1
    UZ = 2
    RX = 3
    RY = 4
    RZ = 5


NUM_DOF_PER_NODE = 6

ALL_DOFS: tuple[DOF, ...] = tuple(DOF)
"""Os 6 :class:`DOF`, na ordem usada para indexar vetores/matrizes
locais e globais (UX, UY, UZ, RX, RY, RZ)."""
