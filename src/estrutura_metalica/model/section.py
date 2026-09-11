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
