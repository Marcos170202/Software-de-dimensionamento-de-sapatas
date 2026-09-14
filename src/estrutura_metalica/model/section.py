"""Perfis metálicos — Etapa 2 do processo de modelagem.

Reflete a nota do PROCESSO_MODELAGEM_METALICA.md (Etapa 3): perfis
laminados/soldados I/H e U são adotados a partir de um CATÁLOGO de
bitolas comerciais (propriedades geométricas de tabela, não derivadas
de uma fórmula simplificada — a geometria real inclui raios de
concordância, mesas de espessura variável em perfis soldados etc.).
Os tubos circulares/retangulares, por serem seções fechadas de parede
fina bem definidas, também podem ter suas propriedades calculadas
diretamente das dimensões nominais (:meth:`RectangularTubeSection.from_dimensions`,
:meth:`CircularTubeSection.from_dimensions`).

Todas as propriedades geométricas estão em unidades SI (m², m⁴, m⁶, m).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum, auto


class SectionShape(Enum):
    """Forma do perfil, conforme a Etapa 2 do processo de modelagem."""

    I_H = auto()
    U = auto()
    TUBE_CIRCULAR = auto()
    TUBE_RECTANGULAR = auto()


@dataclass(frozen=True, slots=True)
class SteelSection:
    """Propriedades geométricas de um perfil metálico.

    ``area``: área bruta da seção transversal (m²).
    ``ix``: momento de inércia em relação ao eixo de maior inércia
    ("eixo forte", x, perpendicular à alma em perfis I/H/U) (m⁴).
    ``iy``: momento de inércia em relação ao eixo de menor inércia
    ("eixo fraco", y) (m⁴).
    ``j``: constante de torção de St. Venant (m⁴).
    ``cw``: constante de empenamento (m⁶) — ``None`` quando não
    aplicável/disponível (ex.: seções fechadas, onde o empenamento é
    desprezível e a NBR 8800 não exige essa propriedade).
    ``depth``: altura total do perfil (m) — usada em verificações de
    flambagem local da alma (FLA) e no cálculo do módulo resistente.
    """

    name: str
    shape: SectionShape
    area: float
    ix: float
    iy: float
    j: float
    depth: float
    cw: float | None = None

    def __post_init__(self) -> None:
        for value, label in (
            (self.area, "area"),
            (self.ix, "ix"),
            (self.iy, "iy"),
            (self.j, "j"),
            (self.depth, "depth"),
        ):
            if value <= 0:
                raise ValueError(
                    f"Propriedade '{label}' do perfil '{self.name}' deve ser positiva, "
                    f"recebido: {value!r}"
                )
        if self.cw is not None and self.cw < 0:
            raise ValueError(
                f"Constante de empenamento 'cw' do perfil '{self.name}' não pode ser "
                f"negativa, recebido: {self.cw!r}"
            )

    @property
    def rx(self) -> float:
        """Raio de giração em relação ao eixo forte, m (rx = √(Ix/A))."""
        return math.sqrt(self.ix / self.area)

    @property
    def ry(self) -> float:
        """Raio de giração em relação ao eixo fraco, m (ry = √(Iy/A))."""
        return math.sqrt(self.iy / self.area)


def _thin_wall_tube_j(area_enclosed: float, perimeter: float, thickness: float) -> float:
    """Constante de torção de St. Venant para seção fechada de parede
    fina (fórmula de Bredt): J = 4·Ae² · t / p.
    """
    return 4.0 * area_enclosed**2 * thickness / perimeter


@dataclass(frozen=True, slots=True)
class RectangularTubeSection(SteelSection):
    """Tubo retangular (ou quadrado) de parede fina.

    Além das propriedades herdadas de :class:`SteelSection`, guarda as
    dimensões nominais usadas para construí-lo (altura ``h``, largura
    ``b`` e espessura de parede ``t``, em metros) — úteis para
    verificações de esbeltez local (NBR 8800 Tabela 1) em fases
    futuras.
    """

    h: float = 0.0
    b: float = 0.0
    t: float = 0.0

    @classmethod
    def from_dimensions(
        cls, name: str, *, h: float, b: float, t: float
    ) -> RectangularTubeSection:
        """Constrói o perfil a partir das dimensões externas nominais.

        ``h``: altura externa (m). ``b``: largura externa (m).
        ``t``: espessura de parede (m, constante).

        Aproximação de parede fina usual em pré-dimensionamento
        (linha média a meia-espessura da parede) — propriedades exatas
        de catálogo (que consideram os cantos arredondados) devem ser
        preferidas quando disponíveis.
        """
        if h <= 0 or b <= 0:
            raise ValueError(f"Dimensões h={h!r} e b={b!r} devem ser positivas")
        if t <= 0 or t >= min(h, b) / 2:
            raise ValueError(
                f"Espessura de parede t={t!r} deve ser positiva e menor que metade da "
                f"menor dimensão externa (h={h!r}, b={b!r})"
            )
        h_i = h - 2 * t
        b_i = b - 2 * t
        area = h * b - h_i * b_i
        ix = (b * h**3 - b_i * h_i**3) / 12.0
        iy = (h * b**3 - h_i * b_i**3) / 12.0
        h_m = h - t
        b_m = b - t
        area_enclosed = h_m * b_m
        perimeter = 2.0 * (h_m + b_m)
        j = _thin_wall_tube_j(area_enclosed, perimeter, t)
        return cls(
            name=name,
            shape=SectionShape.TUBE_RECTANGULAR,
            area=area,
            ix=ix,
            iy=iy,
            j=j,
            depth=h,
            cw=None,
            h=h,
            b=b,
            t=t,
        )


@dataclass(frozen=True, slots=True)
class IProfileSection(SteelSection):
    """Perfil laminado/soldado I/H de catálogo (bitola comercial).

    Além das propriedades herdadas de :class:`SteelSection` (área,
    ``ix``, ``iy``, ``j`` — St. Venant, ``cw``, ``depth`` = altura
    total ``d``), guarda as dimensões e propriedades geométricas
    adicionais exigidas pelas verificações da NBR 8800:2024 que não
    são calculáveis a partir de ``ix``/``iy``/``area`` sozinhos —
    valores de CATÁLOGO (não de fórmula), lidos diretamente do
    fabricante (ver ``source``).

    ``bf``: largura da mesa (m). ``tw``: espessura da alma (m).
    ``tf``: espessura da mesa (m). ``h``: distância livre entre as
    faces internas das mesas, descontados os raios de concordância
    ("h" na convenção da NBR 8800 — usada na razão de esbeltez da
    alma ``h/tw``; distinta da altura total ``depth``/``d``, e também
    distinta de uma eventual altura "h" de catálogo medida entre as
    faces das mesas SEM descontar o raio, quando o fabricante
    publica as duas). ``wx``/``wy``: módulo resistente elástico,
    eixos X e Y (m³). ``zx``/``zy``: módulo resistente plástico,
    eixos X e Y (m³). ``rt``: raio de giração da mesa comprimida mais
    1/3 da alma comprimida (m) — necessário para os cálculos de FLT
    de vigas de alma esbelta soldadas (Anexo E,
    :mod:`~estrutura_metalica.normative.nbr8800.slender_web`), onde a
    NBR 8800 não fornece fórmula fechada e exige valor de catálogo ou
    cálculo direto da seção. ``mass_linear``: massa por metro (kg/m,
    informativo). ``source``: identificação do catálogo/edição de
    onde os valores foram extraídos (rastreabilidade).

    As razões de esbeltez local (``bf/(2·tf)`` para a mesa,
    ``h/tw`` para a alma) NÃO são armazenadas — são triviais de obter
    a partir de ``bf``/``tf``/``h``/``tw`` e devem ser calculadas pelo
    chamador (ver
    :mod:`~estrutura_metalica.normative.nbr8800.slender_web`/
    ``compression``), evitando depender de uma eventual coluna de
    catálogo "λ" cuja consistência com as dimensões básicas não foi
    conferida para todas as bitolas (ver ATENÇÃO no módulo de
    catálogo).
    """

    bf: float = 0.0
    tw: float = 0.0
    tf: float = 0.0
    h: float = 0.0
    wx: float = 0.0
    zx: float = 0.0
    wy: float = 0.0
    zy: float = 0.0
    rt: float = 0.0
    mass_linear: float = 0.0
    source: str = ""

    def __post_init__(self) -> None:
        # Nota: usa a chamada explícita (não ``super().__post_init__()``)
        # porque ``@dataclass(slots=True)`` recria a classe após a
        # execução do corpo da classe — o ``super()`` sem argumentos
        # depende da célula de fechamento ``__class__`` capturada na
        # definição, que ainda aponta para a classe ANTES da
        # substituição por slots, e falha com
        # "TypeError: super(type, obj): obj must be an instance or
        # subtype of type".
        SteelSection.__post_init__(self)
        for value, label in (
            (self.bf, "bf"),
            (self.tw, "tw"),
            (self.tf, "tf"),
            (self.h, "h"),
            (self.wx, "wx"),
            (self.zx, "zx"),
            (self.wy, "wy"),
            (self.zy, "zy"),
            (self.rt, "rt"),
            (self.mass_linear, "mass_linear"),
        ):
            if value <= 0:
                raise ValueError(
                    f"Propriedade '{label}' do perfil '{self.name}' deve ser positiva, "
                    f"recebido: {value!r}"
                )
        if self.h >= self.depth:
            raise ValueError(
                f"Altura livre da alma 'h'={self.h!r} do perfil '{self.name}' deve ser "
                f"menor que a altura total 'depth'={self.depth!r}"
            )


def compressed_flange_radius_of_gyration(bf: float, tf: float, tw: float, h: float) -> float:
    """Raio de giração da mesa comprimida mais 1/3 da alma comprimida,
    ``ryc``/``rt`` — grandeza exigida por
    :mod:`~estrutura_metalica.normative.nbr8800.slender_web` (Anexo E,
    FLT de vigas de alma esbelta) quando não disponível como valor de
    catálogo (ex.: perfis não tabulados, ou catálogos que não
    publicam essa coluna — ver
    :mod:`~estrutura_metalica.model.british_steel_catalog`).

    Cálculo geométrico IDEALIZADO para uma seção I/H com dupla
    simetria: a "parte comprimida" de uma seção fletida em torno do
    eixo forte é a mesa comprimida inteira mais 1/3 da altura da
    alma comprimida — que, por simetria (dupla simetria, sem força
    axial), é 1/3 de metade da alma livre, ou seja, ``h/6``.
    Idealiza a mesa como um retângulo ``bf × tf`` e essa fração da
    alma como um retângulo ``tw × (h/6)``, cada um com seu próprio
    momento de inércia em relação ao eixo fraco (paralelo à alma) —
    aproximação usual quando a geometria exata (incluindo raios de
    concordância) não está disponível, análoga à aproximação de
    parede fina de :meth:`RectangularTubeSection.from_dimensions`.

    ``Ayc = bf·tf + (h/6)·tw``; ``Iyc = tf·bf³/12 + (h/6)·tw³/12``;
    ``ryc = sqrt(Iyc/Ayc)``.

    Conferido contra o valor de catálogo (coluna "rt") do perfil
    Gerdau W310x97,0 (bf=305 mm, tf=15,4 mm, tw=9,9 mm, h=245 mm):
    esta função retorna ≈8,45 cm contra o valor de catálogo 8,38 cm
    (≈1,2% de diferença, dentro do esperado para uma idealização que
    ignora os raios de concordância).

    ``bf``/``tf``/``tw``/``h``: ver :class:`IProfileSection` (m).
    Retorna o raio de giração ``ryc`` (m).
    """
    for value, label in ((bf, "bf"), (tf, "tf"), (tw, "tw"), (h, "h")):
        if value <= 0:
            raise ValueError(f"{label} deve ser finito e positivo, recebido: {value!r}")
    web_compressed_height = h / 6.0
    area_yc = bf * tf + web_compressed_height * tw
    iyc = (tf * bf**3) / 12.0 + (web_compressed_height * tw**3) / 12.0
    return math.sqrt(iyc / area_yc)


@dataclass(frozen=True, slots=True)
class CircularTubeSection(SteelSection):
    """Tubo circular de parede fina/espessa.

    Guarda o diâmetro externo ``d`` e a espessura de parede ``t``
    (metros) usados para construí-lo.
    """

    d: float = 0.0
    t: float = 0.0

    @classmethod
    def from_dimensions(cls, name: str, *, d: float, t: float) -> CircularTubeSection:
        """Constrói o perfil a partir do diâmetro externo ``d`` e da
        espessura de parede ``t`` (metros) — propriedades exatas
        (seção anelar), válidas para qualquer relação d/t.
        """
        if d <= 0:
            raise ValueError(f"Diâmetro externo d={d!r} deve ser positivo")
        if t <= 0 or t >= d / 2:
            raise ValueError(
                f"Espessura de parede t={t!r} deve ser positiva e menor que o raio "
                f"externo (d={d!r})"
            )
        d_i = d - 2 * t
        area = math.pi / 4.0 * (d**2 - d_i**2)
        i = math.pi / 64.0 * (d**4 - d_i**4)
        j = math.pi / 32.0 * (d**4 - d_i**4)
        return cls(
            name=name,
            shape=SectionShape.TUBE_CIRCULAR,
            area=area,
            ix=i,
            iy=i,
            j=j,
            depth=d,
            cw=None,
            d=d,
            t=t,
        )


@dataclass(frozen=True, slots=True)
class CircularHollowProfile(CircularTubeSection):
    """Perfil tubular circular de catálogo ("MSH" — Módulo de Seção
    Hueca — EN 10210/10219), com propriedades adicionais de catálogo
    que :class:`CircularTubeSection` não guarda.

    Ao contrário de :meth:`CircularTubeSection.from_dimensions`
    (aproximação de anel de parede fina/espessa EXATA, mas sem
    módulo resistente), os valores aqui são de CATÁLOGO — ``area``/
    ``ix``/``j`` herdados conferem com a fórmula exata do anel dentro
    de ~3% (checado nas 562 bitolas do catálogo Vallourec MSH,
    revisão do manual técnico — ver
    :mod:`~estrutura_metalica.model.vallourec_catalog`).

    ``wel``/``wpl``: módulo resistente elástico/plástico (m³, igual
    nos dois eixos por axissimetria). ``ct``: constante do módulo de
    torção (m³, ``τ = T/Ct`` na fibra mais externa). Não confundir
    com ``j`` (herdado, "It" no catálogo — constante de torção de
    Saint-Venant, m⁴). ``surface_area_per_length``: área de
    superfície por metro linear (m²/m, informativo — pintura/
    galvanização).
    """

    wel: float = 0.0
    wpl: float = 0.0
    ct: float = 0.0
    surface_area_per_length: float = 0.0
    mass_linear: float = 0.0
    source: str = ""

    def __post_init__(self) -> None:
        # Ver nota em IProfileSection.__post_init__ sobre por que a
        # chamada é explícita (não ``super()``).
        SteelSection.__post_init__(self)
        for value, label in (
            (self.wel, "wel"),
            (self.wpl, "wpl"),
            (self.ct, "ct"),
            (self.surface_area_per_length, "surface_area_per_length"),
            (self.mass_linear, "mass_linear"),
        ):
            if value <= 0:
                raise ValueError(
                    f"Propriedade '{label}' do perfil '{self.name}' deve ser positiva, "
                    f"recebido: {value!r}"
                )


@dataclass(frozen=True, slots=True)
class RectangularHollowProfile(RectangularTubeSection):
    """Perfil tubular retangular ou quadrado de catálogo ("MSH" — EN
    10210/10219), com propriedades adicionais de catálogo que
    :class:`RectangularTubeSection` não guarda.

    Cobre TANTO seções quadradas (``h == b``, onde ``welx == wely``
    e ``wplx == wply`` por simetria) QUANTO retangulares (``h != b``)
    — um quadrado é apenas o caso particular ``h == b`` de um
    retângulo, sem necessidade de uma classe separada.

    Ao contrário de :meth:`RectangularTubeSection.from_dimensions`
    (aproximação de parede fina — cantos vivos, sem os raios de
    concordância reais de um perfil tubular laminado/soldado), os
    valores aqui são de CATÁLOGO (com os raios de concordância reais
    já embutidos) — ver
    :mod:`~estrutura_metalica.model.vallourec_catalog`.

    ``welx``/``wely``/``wplx``/``wply``: módulo resistente elástico/
    plástico, eixos x (forte, "xx") e y (fraco, "yy") — m³. ``ct``:
    constante do módulo de torção (m³). ``surface_area_per_length``:
    área de superfície por metro linear (m²/m, informativo).
    """

    welx: float = 0.0
    wely: float = 0.0
    wplx: float = 0.0
    wply: float = 0.0
    ct: float = 0.0
    surface_area_per_length: float = 0.0
    mass_linear: float = 0.0
    source: str = ""

    def __post_init__(self) -> None:
        SteelSection.__post_init__(self)
        for value, label in (
            (self.welx, "welx"),
            (self.wely, "wely"),
            (self.wplx, "wplx"),
            (self.wply, "wply"),
            (self.ct, "ct"),
            (self.surface_area_per_length, "surface_area_per_length"),
            (self.mass_linear, "mass_linear"),
        ):
            if value <= 0:
                raise ValueError(
                    f"Propriedade '{label}' do perfil '{self.name}' deve ser positiva, "
                    f"recebido: {value!r}"
                )
