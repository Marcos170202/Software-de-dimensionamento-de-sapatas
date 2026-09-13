"""Entidades do modelo — Etapas 2 e 3 do processo de modelagem.

Ver ``PROCESSO_MODELAGEM_METALICA.md`` na raiz do repositório.
"""

from __future__ import annotations

from .connection import PINNED_CONNECTION, RIGID_CONNECTION, Connection, ConnectionType
from .material import (
    ASTM_A36,
    ASTM_A572_GR50,
    ASTM_A992,
    STEEL_MATERIAL_CATALOG,
    SteelMaterial,
)
from .members import Beam, Bracing, Column, Member
from .node import Node
from .section import (
    CircularTubeSection,
    RectangularTubeSection,
    SectionShape,
    SteelSection,
)

__all__ = [
    "ASTM_A36",
    "ASTM_A572_GR50",
    "ASTM_A992",
    "STEEL_MATERIAL_CATALOG",
    "Beam",
    "Bracing",
    "CircularTubeSection",
    "Column",
    "Connection",
    "ConnectionType",
    "Member",
    "Node",
    "PINNED_CONNECTION",
    "RIGID_CONNECTION",
    "RectangularTubeSection",
    "SectionShape",
    "SteelMaterial",
    "SteelSection",
]
