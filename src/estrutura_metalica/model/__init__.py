"""Entidades do modelo — Etapas 2 e 3 do processo de modelagem.

Ver ``PROCESSO_MODELAGEM_METALICA.md`` na raiz do repositório.

Inclui catálogos de bitolas comerciais REAIS (não valores hipotéticos
de exemplo):

- :data:`GERDAU_W_H_PROFILES`
  (:mod:`~estrutura_metalica.model.steel_profile_catalog`, 107 perfis
  "W"/"HP" Gerdau, abas paralelas);
- :data:`GERDAU_I_PROFILES`/:data:`GERDAU_U_PROFILES`/
  :data:`GERDAU_ANGLE_PROFILES`/:data:`GERDAU_T_PROFILES`
  (:mod:`~estrutura_metalica.model.legacy_profile_catalog`, perfis
  "I"/"U"/cantoneira/"T" Gerdau, abas inclinadas — catálogo "Barras e
  Perfis");
- :data:`BRITISH_STEEL_UB_PROFILES`/:data:`BRITISH_STEEL_UC_PROFILES`
  (:mod:`~estrutura_metalica.model.british_steel_catalog`, "Universal
  Beams"/"Universal Columns" britânicos, BS EN 10365:2017 — 94 e 53
  bitolas, respectivamente);
- :data:`VALLOUREC_CIRCULAR_HOLLOW_PROFILES`/
  :data:`VALLOUREC_SQUARE_HOLLOW_PROFILES`/
  :data:`VALLOUREC_RECTANGULAR_HOLLOW_PROFILES`
  (:mod:`~estrutura_metalica.model.vallourec_catalog`, perfis
  tubulares "MSH" — EN 10210 — 562+223+450 bitolas);
- :data:`STRUCTURAL_BOLT_CATALOG`
  (:mod:`~estrutura_metalica.model.bolt_catalog`, parafusos ASTM
  A325/A490/A307).

Ver a documentação de cada módulo para a fonte e as limitações de
cada catálogo (seções monossimétricas/assimétricas, propriedades não
tabuladas etc.).
"""

from __future__ import annotations

from .bolt_catalog import STRUCTURAL_BOLT_CATALOG, StructuralBolt, get_structural_bolt
from .british_steel_catalog import (
    BRITISH_STEEL_UB_PROFILES,
    BRITISH_STEEL_UC_PROFILES,
    get_british_steel_ub_profile,
    get_british_steel_uc_profile,
)
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
    EN_10025_S275,
    EN_10025_S355,
    STEEL_MATERIAL_CATALOG,
    SteelMaterial,
)
from .members import Beam, Bracing, Column, Member
from .node import Node
from .section import (
    CircularHollowProfile,
    CircularTubeSection,
    IProfileSection,
    RectangularHollowProfile,
    RectangularTubeSection,
    SectionShape,
    SteelSection,
    compressed_flange_radius_of_gyration,
)
from .steel_profile_catalog import GERDAU_W_H_PROFILES, get_gerdau_w_h_profile
from .vallourec_catalog import (
    VALLOUREC_CIRCULAR_HOLLOW_PROFILES,
    VALLOUREC_RECTANGULAR_HOLLOW_PROFILES,
    VALLOUREC_SQUARE_HOLLOW_PROFILES,
    get_vallourec_circular_hollow_profile,
    get_vallourec_rectangular_hollow_profile,
    get_vallourec_square_hollow_profile,
)

__all__ = [
    "ASTM_A36",
    "ASTM_A572_GR50",
    "ASTM_A992",
    "BRITISH_STEEL_UB_PROFILES",
    "EN_10025_S275",
    "EN_10025_S355",
    "BRITISH_STEEL_UC_PROFILES",
    "GERDAU_ANGLE_PROFILES",
    "GERDAU_I_PROFILES",
    "GERDAU_T_PROFILES",
    "GERDAU_U_PROFILES",
    "GERDAU_W_H_PROFILES",
    "STEEL_MATERIAL_CATALOG",
    "VALLOUREC_CIRCULAR_HOLLOW_PROFILES",
    "VALLOUREC_RECTANGULAR_HOLLOW_PROFILES",
    "VALLOUREC_SQUARE_HOLLOW_PROFILES",
    "Beam",
    "Bracing",
    "CircularHollowProfile",
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
    "RectangularHollowProfile",
    "RectangularTubeSection",
    "STRUCTURAL_BOLT_CATALOG",
    "SectionShape",
    "SteelMaterial",
    "SteelSection",
    "StructuralBolt",
    "compressed_flange_radius_of_gyration",
    "get_british_steel_ub_profile",
    "get_british_steel_uc_profile",
    "get_gerdau_angle_profile",
    "get_gerdau_i_profile",
    "get_gerdau_t_profile",
    "get_gerdau_u_profile",
    "get_gerdau_w_h_profile",
    "get_structural_bolt",
    "get_vallourec_circular_hollow_profile",
    "get_vallourec_rectangular_hollow_profile",
    "get_vallourec_square_hollow_profile",
]
