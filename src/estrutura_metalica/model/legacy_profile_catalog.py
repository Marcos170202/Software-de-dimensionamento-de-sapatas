"""Catálogo de perfis laminados "I" e "U" (abas inclinadas) — Gerdau.

Fonte: "Perfil I e U Gerdau" (folder técnico, www.gerdau.com.br).
Perfis de formato tradicional, abas inclinadas ("perfil I"/"perfil
U" clássico, distinto dos perfis "W"/"H" de abas paralelas — ver
:mod:`~estrutura_metalica.model.steel_profile_catalog`). Produzidos
normalmente em aço ASTM A36 (ASTM A572/A588 sob encomenda). Valores
extraídos do texto do PDF (``pdftotext -layout``) e convertidos para
SI (m, m2, m3, m4). Conferidos por checagem cruzada ``Ix/rx² ≈ Área`` e
(quando aplicável) ``Iy ≈ Wy·(bf-x)`` para os perfis U.

**ATENÇÃO — LIMITAÇÕES**:

1. **Sem módulo resistente plástico (``Zx``/``Zy``) nem constantes de
   torção/empenamento (``J``/``Cw``)**: este catálogo, ao contrário do
   catálogo Gerdau W/H, NÃO tabula essas propriedades. Por isso
   :class:`GerdauIProfile`/:class:`GerdauUProfile` NÃO estendem
   :class:`~estrutura_metalica.model.section.SteelSection` (que exige
   ``j`` positivo) nem
   :class:`~estrutura_metalica.model.section.IProfileSection` (que
   exige ``zx``/``zy`` positivos) — o chamador que precisar dessas
   propriedades para uma verificação específica (ex.: Anexo D/FLM com
   seção compacta, ou ``Nez`` em 5.3.5.1-c) deve fornecê-las
   separadamente ou aproximá-las (ex.: ``J ≈ Σ(b·t³)/3`` para os
   retângulos que compõem a seção — aproximação clássica de paredes
   finas, não específica da NBR 8800 e não implementada aqui).
2. **``GerdauUProfile`` é uma seção MONOSSIMÉTRICA**: a NBR 8800,
   5.3.5.2, exige a força de flambagem por FLEXO-TORÇÃO (não
   ``min(Nex,Ney,Nez)``) para o dimensionamento à compressão de perfis
   U — NÃO implementada em
   :mod:`~estrutura_metalica.normative.nbr8800.compression` (ver
   ATENÇÃO nesse módulo). ``x_centroid`` (distância do dorso da alma
   ao centroide) é fornecido para uma eventual implementação futura,
   mas não é usado por nenhuma função deste pacote hoje.
3. **Coluna de catálogo "r" (raio de giração) NÃO reproduzida**:
   ``rx``/``ry`` são calculados aqui como ``sqrt(I/Área)``
   (consistente com
   :class:`~estrutura_metalica.model.section.SteelSection`), em vez
   de copiar a coluna "r" impressa no catálogo. Motivo: nas duas
   linhas da bitola U 8" (17,10 kg/m e 20,50 kg/m), o "ry" impresso
   (1,42 cm em ambas) é inconsistente com ``Iy``/Área — confirmado
   de forma independente via ``Wy·(bf-x) ≈ Iy`` (bate com o ``Iy``
   impresso, não com o ``ry`` impresso). Considera-se ``Iy`` (e
   ``Ix``) os valores confiáveis dessas linhas, não ``ry``. Também
   observa-se, na mesma checagem cruzada (``Wy·(bf-x) ≈ Iy``), que a
   linha "U 3\" 7,44 kg/m" diverge mais que as demais (~12,6%,
   contra <2,3% em todas as outras 11 linhas do perfil U) — mantido
   como impresso, por não haver como determinar qual grandeza
   (``Iy``, ``Wy``, ``bf`` ou ``x``) está inconsistente nessa linha
   específica.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

_SOURCE = "Gerdau - Perfil I e U (abas inclinadas), folder tecnico"


@dataclass(frozen=True, slots=True)
class GerdauIProfile:
    """Perfil "I" Gerdau, abas inclinadas (catálogo próprio — ver
    ATENÇÃO no docstring do módulo sobre propriedades NÃO tabuladas).

    Seção com dupla simetria. ``rt``: raio de giração da mesa
    comprimida mais 1/3 da alma comprimida (m) — valor de catálogo,
    ver uso equivalente em
    :class:`~estrutura_metalica.model.section.IProfileSection`.
    """

    name: str
    bitola_imperial: str
    mass_linear: float
    depth: float
    bf: float
    tw: float
    tf: float
    area: float
    ix: float
    wx: float
    iy: float
    wy: float
    rt: float
    source: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.mass_linear, "mass_linear"),
            (self.depth, "depth"),
            (self.bf, "bf"),
            (self.tw, "tw"),
            (self.tf, "tf"),
            (self.area, "area"),
            (self.ix, "ix"),
            (self.wx, "wx"),
            (self.iy, "iy"),
            (self.wy, "wy"),
            (self.rt, "rt"),
        ):
            if value <= 0:
                raise ValueError(
                    f"Propriedade '{label}' do perfil '{self.name}' deve ser "
                    f"positiva, recebido: {value!r}"
                )

    @property
    def rx(self) -> float:
        """Raio de giração em relação ao eixo forte, m (calculado —
        ver ATENÇÃO 3 no docstring do módulo)."""
        return math.sqrt(self.ix / self.area)

    @property
    def ry(self) -> float:
        """Raio de giração em relação ao eixo fraco, m (calculado —
        ver ATENÇÃO 3 no docstring do módulo)."""
        return math.sqrt(self.iy / self.area)


@dataclass(frozen=True, slots=True)
class GerdauUProfile:
    """Perfil "U" Gerdau, abas inclinadas — seção MONOSSIMÉTRICA (ver
    ATENÇÃO 2 no docstring do módulo).

    ``x_centroid``: distância do dorso (face externa) da alma ao
    centroide da seção, m — informativo (ver ATENÇÃO 2).
    """

    name: str
    bitola_imperial: str
    mass_linear: float
    depth: float
    bf: float
    tw: float
    tf: float
    area: float
    ix: float
    wx: float
    iy: float
    wy: float
    x_centroid: float
    source: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.mass_linear, "mass_linear"),
            (self.depth, "depth"),
            (self.bf, "bf"),
            (self.tw, "tw"),
            (self.tf, "tf"),
            (self.area, "area"),
            (self.ix, "ix"),
            (self.wx, "wx"),
            (self.iy, "iy"),
            (self.wy, "wy"),
            (self.x_centroid, "x_centroid"),
        ):
            if value <= 0:
                raise ValueError(
                    f"Propriedade '{label}' do perfil '{self.name}' deve ser "
                    f"positiva, recebido: {value!r}"
                )
        if self.x_centroid >= self.bf:
            raise ValueError(
                f"x_centroid={self.x_centroid!r} do perfil '{self.name}' nao pode "
                f"ser maior ou igual a bf={self.bf!r}"
            )

    @property
    def rx(self) -> float:
        """Raio de giração em relação ao eixo forte, m (calculado)."""
        return math.sqrt(self.ix / self.area)

    @property
    def ry(self) -> float:
        """Raio de giração em relação ao eixo fraco, m (calculado — ver
        ATENÇÃO 3 no docstring do módulo)."""
        return math.sqrt(self.iy / self.area)


_RAW_I_PROFILES: tuple[GerdauIProfile, ...] = (
    GerdauIProfile(
        name="I76x8.48",
        bitola_imperial='3"',
        mass_linear=8.4800000000e+00,
        depth=7.6200000000e-02,
        bf=5.9180000000e-02,
        tw=4.3200000000e-03,
        tf=6.6000000000e-03,
        area=1.0800000000e-03,
        ix=1.0510000000e-06,
        wx=2.7600000000e-05,
        iy=1.8900000000e-07,
        wy=6.4000000000e-06,
        rt=1.4500000000e-02,
        source=_SOURCE,
    ),
    GerdauIProfile(
        name="I76x9.68",
        bitola_imperial='3"',
        mass_linear=9.6800000000e+00,
        depth=7.6200000000e-02,
        bf=6.1240000000e-02,
        tw=6.3800000000e-03,
        tf=6.6000000000e-03,
        area=1.2320000000e-03,
        ix=1.1500000000e-06,
        wx=3.0180000000e-05,
        iy=4.5600000000e-07,
        wy=1.1480000000e-05,
        rt=1.9800000000e-02,
        source=_SOURCE,
    ),
    GerdauIProfile(
        name="I102x11.46",
        bitola_imperial='4"',
        mass_linear=1.1460000000e+01,
        depth=1.0160000000e-01,
        bf=6.7600000000e-02,
        tw=4.9000000000e-03,
        tf=7.4400000000e-03,
        area=1.4500000000e-03,
        ix=2.5200000000e-06,
        wx=4.9700000000e-05,
        iy=3.1700000000e-07,
        wy=9.4000000000e-06,
        rt=1.6800000000e-02,
        source=_SOURCE,
    ),
    GerdauIProfile(
        name="I102x12.65",
        bitola_imperial='4"',
        mass_linear=1.2650000000e+01,
        depth=1.0160000000e-01,
        bf=6.9200000000e-02,
        tw=6.4300000000e-03,
        tf=7.4400000000e-03,
        area=1.6110000000e-03,
        ix=2.6600000000e-06,
        wx=5.2400000000e-05,
        iy=3.4300000000e-07,
        wy=9.9000000000e-06,
        rt=1.8300000000e-02,
        source=_SOURCE,
    ),
    GerdauIProfile(
        name="I127x14.88",
        bitola_imperial='5"',
        mass_linear=1.4880000000e+01,
        depth=1.2700000000e-01,
        bf=7.6300000000e-02,
        tw=5.4400000000e-03,
        tf=8.2800000000e-03,
        area=1.8800000000e-03,
        ix=5.1100000000e-06,
        wx=8.0400000000e-05,
        iy=5.0200000000e-07,
        wy=1.3200000000e-05,
        rt=1.8800000000e-02,
        source=_SOURCE,
    ),
    GerdauIProfile(
        name="I127x18.24",
        bitola_imperial='5"',
        mass_linear=1.8240000000e+01,
        depth=1.2700000000e-01,
        bf=7.9700000000e-02,
        tw=8.8100000000e-03,
        tf=8.2800000000e-03,
        area=2.3240000000e-03,
        ix=5.7000000000e-06,
        wx=8.9800000000e-05,
        iy=5.8600000000e-07,
        wy=1.4700000000e-05,
        rt=1.9200000000e-02,
        source=_SOURCE,
    ),
    GerdauIProfile(
        name="I152x18.6",
        bitola_imperial='6"',
        mass_linear=1.8600000000e+01,
        depth=1.5240000000e-01,
        bf=8.4630000000e-02,
        tw=5.8900000000e-03,
        tf=9.1200000000e-03,
        area=2.3600000000e-03,
        ix=9.1900000000e-06,
        wx=1.2060000000e-04,
        iy=7.5700000000e-07,
        wy=1.7900000000e-05,
        rt=2.0800000000e-02,
        source=_SOURCE,
    ),
    GerdauIProfile(
        name="I152x22",
        bitola_imperial='6"',
        mass_linear=2.2000000000e+01,
        depth=1.5240000000e-01,
        bf=8.7500000000e-02,
        tw=8.7100000000e-03,
        tf=9.1200000000e-03,
        area=2.7970000000e-03,
        ix=1.0030000000e-05,
        wx=1.3170000000e-04,
        iy=8.4900000000e-07,
        wy=1.9400000000e-05,
        rt=2.2600000000e-02,
        source=_SOURCE,
    ),
)

_RAW_U_PROFILES: tuple[GerdauUProfile, ...] = (
    GerdauUProfile(
        name="U76x6.1",
        bitola_imperial='3"',
        mass_linear=6.1000000000e+00,
        depth=7.6200000000e-02,
        bf=3.5810000000e-02,
        tw=4.3200000000e-03,
        tf=6.9300000000e-03,
        area=7.7800000000e-04,
        ix=6.8900000000e-07,
        wx=1.8100000000e-05,
        iy=8.2000000000e-08,
        wy=3.3200000000e-06,
        x_centroid=1.1100000000e-02,
        source=_SOURCE,
    ),
    GerdauUProfile(
        name="U76x7.44",
        bitola_imperial='3"',
        mass_linear=7.4400000000e+00,
        depth=7.6200000000e-02,
        bf=3.5050000000e-02,
        tw=6.5500000000e-03,
        tf=6.9300000000e-03,
        area=9.4800000000e-04,
        ix=7.7200000000e-07,
        wx=2.0300000000e-05,
        iy=1.0300000000e-07,
        wy=3.8200000000e-06,
        x_centroid=1.1100000000e-02,
        source=_SOURCE,
    ),
    GerdauUProfile(
        name="U102x8.04",
        bitola_imperial='4"',
        mass_linear=8.0400000000e+00,
        depth=1.0160000000e-01,
        bf=4.0230000000e-02,
        tw=4.6700000000e-03,
        tf=7.5200000000e-03,
        area=1.0100000000e-03,
        ix=1.5950000000e-06,
        wx=3.1400000000e-05,
        iy=1.3100000000e-07,
        wy=4.6100000000e-06,
        x_centroid=1.1600000000e-02,
        source=_SOURCE,
    ),
    GerdauUProfile(
        name="U102x9.3",
        bitola_imperial='4"',
        mass_linear=9.3000000000e+00,
        depth=1.0160000000e-01,
        bf=4.1830000000e-02,
        tw=6.2700000000e-03,
        tf=7.5200000000e-03,
        area=1.1900000000e-03,
        ix=1.7440000000e-06,
        wx=3.4300000000e-05,
        iy=1.5500000000e-07,
        wy=5.1000000000e-06,
        x_centroid=1.1500000000e-02,
        source=_SOURCE,
    ),
    GerdauUProfile(
        name="U152x12.2",
        bitola_imperial='6"',
        mass_linear=1.2200000000e+01,
        depth=1.5240000000e-01,
        bf=4.8770000000e-02,
        tw=5.0800000000e-03,
        tf=8.7100000000e-03,
        area=1.5500000000e-03,
        ix=5.4600000000e-06,
        wx=7.1700000000e-05,
        iy=2.8800000000e-07,
        wy=8.1600000000e-06,
        x_centroid=1.3000000000e-02,
        source=_SOURCE,
    ),
    GerdauUProfile(
        name="U152x15.62",
        bitola_imperial='6"',
        mass_linear=1.5620000000e+01,
        depth=1.5240000000e-01,
        bf=5.1660000000e-02,
        tw=7.9800000000e-03,
        tf=8.7100000000e-03,
        area=1.9900000000e-03,
        ix=6.3200000000e-06,
        wx=8.2900000000e-05,
        iy=3.6000000000e-07,
        wy=9.2400000000e-06,
        x_centroid=1.2700000000e-02,
        source=_SOURCE,
    ),
    GerdauUProfile(
        name="U203x17.1",
        bitola_imperial='8"',
        mass_linear=1.7100000000e+01,
        depth=2.0320000000e-01,
        bf=5.7400000000e-02,
        tw=5.5900000000e-03,
        tf=9.5000000000e-03,
        area=2.1680000000e-03,
        ix=1.3443000000e-05,
        wx=1.3270000000e-04,
        iy=5.4100000000e-07,
        wy=1.2940000000e-05,
        x_centroid=1.4700000000e-02,
        source=_SOURCE,
    ),
    GerdauUProfile(
        name="U203x20.5",
        bitola_imperial='8"',
        mass_linear=2.0500000000e+01,
        depth=2.0320000000e-01,
        bf=5.9510000000e-02,
        tw=7.7000000000e-03,
        tf=9.5000000000e-03,
        area=2.5930000000e-03,
        ix=1.4900000000e-05,
        wx=1.4750000000e-04,
        iy=6.2400000000e-07,
        wy=1.4090000000e-05,
        x_centroid=1.4200000000e-02,
        source=_SOURCE,
    ),
    GerdauUProfile(
        name="U254x22.77",
        bitola_imperial='10"',
        mass_linear=2.2770000000e+01,
        depth=2.5400000000e-01,
        bf=6.6040000000e-02,
        tw=6.1000000000e-03,
        tf=1.1100000000e-02,
        area=2.9000000000e-03,
        ix=2.8000000000e-05,
        wx=2.2100000000e-04,
        iy=9.5000000000e-07,
        wy=1.9000000000e-05,
        x_centroid=1.6100000000e-02,
        source=_SOURCE,
    ),
    GerdauUProfile(
        name="U254x29.76",
        bitola_imperial='10"',
        mass_linear=2.9760000000e+01,
        depth=2.5400000000e-01,
        bf=6.9570000000e-02,
        tw=9.6300000000e-03,
        tf=1.1100000000e-02,
        area=3.7900000000e-03,
        ix=3.2900000000e-05,
        wx=2.5900000000e-04,
        iy=1.1700000000e-06,
        wy=2.1600000000e-05,
        x_centroid=1.5400000000e-02,
        source=_SOURCE,
    ),
    GerdauUProfile(
        name="U305x30.8",
        bitola_imperial='12"',
        mass_linear=3.0800000000e+01,
        depth=3.0500000000e-01,
        bf=7.4000000000e-02,
        tw=7.2000000000e-03,
        tf=1.2700000000e-02,
        area=3.9300000000e-03,
        ix=5.3700000000e-05,
        wx=3.5200000000e-04,
        iy=1.6100000000e-06,
        wy=2.8300000000e-05,
        x_centroid=1.7700000000e-02,
        source=_SOURCE,
    ),
    GerdauUProfile(
        name="U305x37",
        bitola_imperial='12"',
        mass_linear=3.7000000000e+01,
        depth=3.0500000000e-01,
        bf=7.7000000000e-02,
        tw=9.8000000000e-03,
        tf=1.2700000000e-02,
        area=4.7400000000e-03,
        ix=6.0100000000e-05,
        wx=3.9400000000e-04,
        iy=1.8600000000e-06,
        wy=3.0900000000e-05,
        x_centroid=1.7100000000e-02,
        source=_SOURCE,
    ),
)

GERDAU_I_PROFILES: dict[str, GerdauIProfile] = {p.name: p for p in _RAW_I_PROFILES}
GERDAU_U_PROFILES: dict[str, GerdauUProfile] = {p.name: p for p in _RAW_U_PROFILES}


def get_gerdau_i_profile(name: str) -> GerdauIProfile:
    """Busca um perfil no catálogo Gerdau I pelo nome (ex.: ``"I152x22"``).

    Levanta ``KeyError`` com a listagem completa de nomes disponíveis
    quando não encontrado (catálogo pequeno — 8 bitolas).
    """
    try:
        return GERDAU_I_PROFILES[name]
    except KeyError:
        raise KeyError(
            f"Perfil {name!r} nao encontrado no catalogo Gerdau I. "
            f"Disponiveis: {sorted(GERDAU_I_PROFILES)!r}"
        ) from None


def get_gerdau_u_profile(name: str) -> GerdauUProfile:
    """Busca um perfil no catálogo Gerdau U pelo nome (ex.: ``"U152x12.2"``).

    Levanta ``KeyError`` com a listagem completa de nomes disponíveis
    quando não encontrado (catálogo pequeno — 12 bitolas).
    """
    try:
        return GERDAU_U_PROFILES[name]
    except KeyError:
        raise KeyError(
            f"Perfil {name!r} nao encontrado no catalogo Gerdau U. "
            f"Disponiveis: {sorted(GERDAU_U_PROFILES)!r}"
        ) from None

