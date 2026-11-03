"""Barras prismáticas submetidas a esforços combinados.

Fonte: ABNT NBR 8800:2024, 5.5 "Barras prismáticas submetidas à
combinação de esforços solicitantes", 5.5.1 "Barras submetidas a
momentos fletores, força axial e forças cortantes" (páginas 60-61).
Fórmulas conferidas por leitura direta (renderização visual) do PDF da
norma — ver rastreabilidade completa em
``docs/normative/NBR8800-RULES.md``.

Escopo desta fase: apenas 5.5.1.2 — interação entre força axial
(tração OU compressão, o que for aplicável) e momento fletor biaxial,
para barras SEM torção. Cobre:

- 5.5.1.2 — as duas equações de interação (``Nsd/Nrd>=0,2`` e
  ``Nsd/Nrd<0,2``), reunidas em
  :func:`axial_bending_interaction_ratio`/:func:`check_axial_and_bending_interaction`.

5.5.1.3 (força cortante) NÃO precisa de nenhuma fórmula nova: a própria
norma remete diretamente a 5.4.3 (já implementado em ``shear.py``) —
"a verificação da barra a esse esforço deve ser feita conforme 5.4.3"
quando a força cortante atua em um único eixo central de inércia. O
caso de força cortante atuando SIMULTANEAMENTE nos dois eixos remete a
5.5.2.3-b)/d) (seções tubulares combinadas com torção) — fora do
escopo, ver abaixo.

**Fora do escopo** (ver ``docs/normative/NBR8800-RULES.md`` para o
registro completo): 5.5.2 (seções tubulares circulares e retangulares
submetidas a momento de torção, força axial, momentos fletores e força
cortante — inclui ``Trd`` para torção pura, 5.5.2.1, e a equação de
interação com torção, 5.5.2.2). O domínio geométrico atual
(``SteelSection``) não distingue seções tubulares de I/H/U com a
riqueza necessária, e a verificação de torção pura (``Trd``) nunca foi
implementada em nenhuma fase anterior deste pacote.

**ATENÇÃO sobre magnitude de Nsd/Msd**: diferente de
``ShearCheckResult``/``FlexureCheckResult`` (onde ``vsd``/``msd``
aceitam qualquer sinal e o chamador é responsável por passar a
magnitude quando for o caso — ver ATENÇÃO nesses módulos), as funções
deste módulo EXIGEM que ``n_sd``, ``mx_sd`` e ``my_sd`` já sejam
passados como magnitudes (``>=0``), levantando ``ValueError`` caso
contrário — decisão de projeto deliberada para não repetir aqui a
mesma armadilha (documentada, não corrigida por compatibilidade
retroativa, nos módulos ``shear``/``flexure``).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ._check_result import CheckResult
from ._validation import is_non_negative_finite, is_positive_finite


def axial_bending_interaction_ratio(
    n_sd: float,
    n_rd: float,
    mx_sd: float,
    mx_rd: float,
    my_sd: float,
    my_rd: float,
) -> float:
    """Razão de interação entre força axial e momento fletor biaxial
    (NBR 8800:2024, 5.5.1.2).

    - ``Nsd/Nrd >= 0,2``:
      ``Nsd/Nrd + (8/9)·(Mx,sd/Mx,rd + My,sd/My,rd)``;
    - ``Nsd/Nrd < 0,2``:
      ``Nsd/(2·Nrd) + (Mx,sd/Mx,rd + My,sd/My,rd)``.

    A barra atende à condição de 5.5.1.2 se o valor retornado for
    ``<= 1,0`` — ver :func:`check_axial_and_bending_interaction`.

    ``n_sd``: força axial solicitante de cálculo, de TRAÇÃO OU
    COMPRESSÃO (a que for aplicável), em MAGNITUDE (``>=0``) — ver
    ATENÇÃO no docstring do módulo. ``n_rd``: força axial resistente
    de cálculo correspondente ao mesmo tipo de esforço de ``n_sd``
    (``Nt,Rd`` conforme 5.2 — ver ``tension.check_tension_member`` —
    ou ``Nc,Rd`` conforme 5.3 — ver
    ``compression.check_compression_member``). ``mx_sd``/``my_sd``:
    momentos fletores solicitantes de cálculo em relação aos eixos x e
    y da seção transversal, em MAGNITUDE (``>=0``) — podem ser zero
    (ex.: barra sem momento em um dos eixos). ``mx_rd``/``my_rd``:
    momentos fletores resistentes de cálculo correspondentes,
    determinados conforme 5.4.2 — ver
    ``flexure.check_flexural_resistance_major_axis`` para o eixo de
    maior momento de inércia (o eixo de menor momento de inércia não
    está implementado, ver ATENÇÃO no docstring do módulo ``flexure``).
    """
    if not is_non_negative_finite(n_sd):
        raise ValueError(
            f"axial_bending_interaction_ratio: n_sd deve ser finito e "
            f"não-negativo (magnitude), recebido: {n_sd!r}"
        )
    if not is_positive_finite(n_rd):
        raise ValueError(
            f"axial_bending_interaction_ratio: n_rd deve ser finito e "
            f"positivo, recebido: {n_rd!r}"
        )
    if not is_non_negative_finite(mx_sd):
        raise ValueError(
            f"axial_bending_interaction_ratio: mx_sd deve ser finito e "
            f"não-negativo (magnitude), recebido: {mx_sd!r}"
        )
    if not is_positive_finite(mx_rd):
        raise ValueError(
            f"axial_bending_interaction_ratio: mx_rd deve ser finito e "
            f"positivo, recebido: {mx_rd!r}"
        )
    if not is_non_negative_finite(my_sd):
        raise ValueError(
            f"axial_bending_interaction_ratio: my_sd deve ser finito e "
            f"não-negativo (magnitude), recebido: {my_sd!r}"
        )
    if not is_positive_finite(my_rd):
        raise ValueError(
            f"axial_bending_interaction_ratio: my_rd deve ser finito e "
            f"positivo, recebido: {my_rd!r}"
        )

    ratio_n = n_sd / n_rd
    bending_term = mx_sd / mx_rd + my_sd / my_rd
    if ratio_n >= 0.2:
        return ratio_n + (8.0 / 9.0) * bending_term
    return ratio_n / 2.0 + bending_term


@dataclass(frozen=True, slots=True)
class CombinedForcesCheckResult(CheckResult):
    """Resultado da verificação a esforços combinados de uma barra
    (NBR 8800:2024, 5.5.1.2).

    ``n_sd``/``n_rd``/``mx_sd``/``mx_rd``/``my_sd``/``my_rd``: ver
    :func:`axial_bending_interaction_ratio`. ``interaction_ratio``:
    valor da equação de interação (5.5.1.2-a ou -b, conforme
    ``n_sd/n_rd``) — a barra atende à condição normativa se
    ``interaction_ratio <= 1,0`` (``is_ok``).
    """

    n_sd: float
    n_rd: float
    mx_sd: float
    mx_rd: float
    my_sd: float
    my_rd: float
    interaction_ratio: float

    def __post_init__(self) -> None:
        if not is_non_negative_finite(self.n_sd):
            raise ValueError(f"n_sd deve ser finito e não-negativo, recebido: {self.n_sd!r}")
        if not is_positive_finite(self.n_rd):
            raise ValueError(f"n_rd deve ser finito e positivo, recebido: {self.n_rd!r}")
        if not is_non_negative_finite(self.mx_sd):
            raise ValueError(f"mx_sd deve ser finito e não-negativo, recebido: {self.mx_sd!r}")
        if not is_positive_finite(self.mx_rd):
            raise ValueError(f"mx_rd deve ser finito e positivo, recebido: {self.mx_rd!r}")
        if not is_non_negative_finite(self.my_sd):
            raise ValueError(f"my_sd deve ser finito e não-negativo, recebido: {self.my_sd!r}")
        if not is_positive_finite(self.my_rd):
            raise ValueError(f"my_rd deve ser finito e positivo, recebido: {self.my_rd!r}")
        if not math.isfinite(self.interaction_ratio) or self.interaction_ratio < 0:
            raise ValueError(
                f"interaction_ratio deve ser finito e não-negativo, "
                f"recebido: {self.interaction_ratio!r}"
            )

    @property
    def sd(self) -> float:
        """Alias genérico — o próprio ``interaction_ratio`` (ver :class:`CheckResult`)."""
        return self.interaction_ratio

    @property
    def rd(self) -> float:
        """Alias genérico — sempre ``1,0`` (o limite da equação de interação)."""
        return 1.0


def check_axial_and_bending_interaction(
    n_sd: float,
    n_rd: float,
    mx_sd: float,
    mx_rd: float,
    my_sd: float,
    my_rd: float,
) -> CombinedForcesCheckResult:
    """Verifica a interação entre força axial e momento fletor biaxial
    (NBR 8800:2024, 5.5.1).

    Ver :func:`axial_bending_interaction_ratio` para as fórmulas e a
    ATENÇÃO no docstring do módulo sobre a exigência de magnitude em
    ``n_sd``/``mx_sd``/``my_sd``.

    Retorna
    -------
    :class:`CombinedForcesCheckResult` com ``interaction_ratio``, a
    taxa de utilização (idêntica a ``interaction_ratio``, pois o
    limite normativo é sempre ``1,0``) e se a condição de 5.5.1.2 é
    atendida.
    """
    ratio = axial_bending_interaction_ratio(
        n_sd=n_sd, n_rd=n_rd, mx_sd=mx_sd, mx_rd=mx_rd, my_sd=my_sd, my_rd=my_rd
    )
    return CombinedForcesCheckResult(
        n_sd=n_sd,
        n_rd=n_rd,
        mx_sd=mx_sd,
        mx_rd=mx_rd,
        my_sd=my_sd,
        my_rd=my_rd,
        interaction_ratio=ratio,
    )
