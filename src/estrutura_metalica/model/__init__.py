"""Entidades do modelo — Etapas 2 e 3 do processo de modelagem.

Ver ``PROCESSO_MODELAGEM_METALICA.md`` na raiz do repositório.

Inclui catálogos de bitolas comerciais REAIS (não valores hipotéticos
de exemplo): :data:`GERDAU_W_H_PROFILES`
(:mod:`~estrutura_metalica.model.steel_profile_catalog`, 107 perfis
"W"/"HP" Gerdau) e :data:`STRUCTURAL_BOLT_CATALOG`
(:mod:`~estrutura_metalica.model.bolt_catalog`, parafusos ASTM
A325/A490/A307) — ver a documentação de cada módulo para a fonte e as
limitações de cada catálogo.
"""

from __future__ import annotations

from .bolt_catalog import STRUCTURAL_BOLT_CATALOG, StructuralBolt, get_structural_bolt
from .connection import PINNED_CONNECTION, RIGID_CONNECTION, Connection, ConnectionType
from .legacy_profile_catalog import (
    GERDAU_ANGLE_PROFILES,
    GERDAU_I_PROFILES,
    GERDAU_T_PROFILES,
    GERDAU_U_PROFILES,
    GerdauAngleProfile,
    GerdauIProfile,
    GerdauTProfile,
    GerdauUProfile,
    get_gerdau_angle_profile,
    get_gerdau_i_profile,
    get_gerdau_t_profile,
    get_gerdau_u_profile,
)
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
    IProfileSection,
    RectangularTubeSection,
    SectionShape,
    SteelSection,
)
from .steel_profile_catalog import GERDAU_W_H_PROFILES, get_gerdau_w_h_profile

__all__ = [
    "ASTM_A36",
    "ASTM_A572_GR50",
    "ASTM_A992",
    "GERDAU_ANGLE_PROFILES",
    "GERDAU_I_PROFILES",
    "GERDAU_T_PROFILES",
    "GERDAU_U_PROFILES",
    "GERDAU_W_H_PROFILES",
    "STEEL_MATERIAL_CATALOG",
    "Beam",
    "Bracing",
    "CircularTubeSection",
    "Column",
    "Connection",
    "ConnectionType",
    "GerdauAngleProfile",
    "GerdauIProfile",
    "GerdauTProfile",
    "GerdauUProfile",
    "IProfileSection",
    "Member",
    "Node",
    "PINNED_CONNECTION",
    "RIGID_CONNECTION",
    "RectangularTubeSection",
    "STRUCTURAL_BOLT_CATALOG",
    "SectionShape",
    "SteelMaterial",
    "SteelSection",
    "StructuralBolt",
    "get_gerdau_angle_profile",
    "get_gerdau_i_profile",
    "get_gerdau_t_profile",
    "get_gerdau_u_profile",
    "get_gerdau_w_h_profile",
    "get_structural_bolt",
]
