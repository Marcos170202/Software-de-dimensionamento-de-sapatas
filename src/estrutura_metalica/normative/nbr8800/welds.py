"""Ligações soldadas — soldas de filete.

Fonte: ABNT NBR 8800:2024, 6.2 "Soldas" (páginas 73-81). Fórmulas
conferidas por leitura direta (renderização visual) do PDF da norma —
ver rastreabilidade completa em ``docs/normative/NBR8800-RULES.md``.

Escopo desta fase: apenas o caso mais comum de solda de filete com
pernas iguais e ângulo reto entre as partes (90°), com um grupo de
filetes cuja resultante das ações passa pelo centro geométrico do
grupo (6.2.5.1, Tabela 9, linha "Filete" — cisalhamento na seção
efetiva, o único modo de ruptura considerado). Cobre:

- 6.2.2.2-a/b — área efetiva (``Aw = comprimento efetivo · garganta
  efetiva``) e garganta efetiva (``te = dw·sen(45°)``, caso padrão de
  pernas iguais/ângulo reto — ver ATENÇÃO abaixo);
- Tabela 9 (linha "Filete", "Cisalhamento na seção efetiva") — força
  resistente de cálculo do METAL DA SOLDA, ``Fw,Rd = 0,6·fw·Aw/γw2``;
- Tabela 11/6.2.6.2.1 — tamanho mínimo da perna de uma solda de
  filete, em função da menor espessura das partes ligadas.

**ATENÇÃO — LIMITAÇÕES DE SEGURANÇA**:

1. **Metal-base não verificado**: a Tabela 9 exige, para soldas de
   filete, que "o metal-base deve atender a 6.5" (elementos de ligação
   submetidos a cisalhamento — inclui ruptura por cisalhamento e
   colapso por rasgamento, "block shear"). Esta fase verifica APENAS o
   metal da solda (``Fw,Rd`` acima) — a verificação do metal-base
   (6.5) NÃO está implementada. Uma ligação real pode ser governada
   pelo metal-base, não pela solda; usar :func:`check_fillet_weld_shear`
   isoladamente para dimensionar uma ligação completa é NÃO
   CONSERVADOR.
2. **Garganta efetiva — caso padrão apenas**: :func:`fillet_weld_effective_throat`
   implementa apenas ``te = dw·sen(45°)`` (pernas iguais, ângulo reto
   de 90° entre as partes — o caso de longe mais comum). A fórmula
   geral de 6.2.2.2-b ("menor distância medida da raiz à face plana
   teórica da solda") para pernas desiguais ou ângulos diferentes de
   90° entre as partes NÃO está implementada, nem o acréscimo de 3 mm
   permitido para soldas de arco submerso com pernas ortogonais
   maiores que 10 mm.
3. **Grupos de filetes com resultante excêntrica**: 6.2.5.2 (fórmulas
   b) e c), método do centro instantâneo de rotação para grupos de
   filetes cuja resultante das ações NÃO passa pelo centro geométrico
   do grupo) NÃO está implementado — apenas o caso concêntrico de
   6.2.5.2-a/Tabela 9.

Também NÃO implementado nesta fase (ver ``docs/normative/NBR8800-RULES.md``
para a lista completa): soldas de penetração total/parcial (Tabela 9,
demais linhas), soldas de tampão/rasgo, combinação de tipos diferentes
de solda (6.2.3), requisitos de metal de solda/procedimentos de
soldagem (6.2.4), tamanho MÁXIMO da perna (6.2.6.2.2), fator de
redução β para filetes longitudinais longos (6.2.2.2-d), parafusos e
barras rosqueadas (6.3), pinos (6.4), elementos de ligação (6.5),
pressão de contato (6.6), bases de pilares (6.7).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ._check_result import CheckResult
from ._validation import is_positive_finite

#: NBR 8800:2024, Tabela 11 (página 80): tamanho mínimo da perna de
#: uma solda de filete, ``dw`` (m), em função da menor espessura das
#: partes ligadas (m) — pares ``(espessura_limite_superior, dw_minimo)``,
#: em ordem crescente.
_TABELA_11_TAMANHO_MINIMO_FILETE: tuple[tuple[float, float], ...] = (
    (0.0063, 0.003),
    (0.0125, 0.005),
    (0.019, 0.006),
)
_TABELA_11_ACIMA_DE_19MM = 0.008


def fillet_weld_effective_throat(leg_size: float) -> float:
    """Garganta efetiva de uma solda de filete de pernas iguais e
    ângulo reto (90°) entre as partes, ``te`` (NBR 8800:2024, 6.2.2.2-b):

    ``te = dw·sen(45°)``.

    Caso padrão (o mais comum) da definição geral ("menor distância
    medida da raiz à face plana teórica da solda") — ver ATENÇÃO no
    docstring do módulo para os casos NÃO cobertos (pernas desiguais,
    ângulo diferente de 90°, acréscimo de arco submerso).

    ``leg_size``: tamanho da perna do filete de solda, ``dw`` (m).
    """
    if not is_positive_finite(leg_size):
        raise ValueError(
            f"fillet_weld_effective_throat: leg_size deve ser finito e positivo, "
            f"recebido: {leg_size!r}"
        )
    return leg_size * math.sin(math.radians(45.0))


def fillet_weld_effective_area(effective_length: float, effective_throat: float) -> float:
    """Área efetiva de uma solda de filete, ``Aw`` (NBR 8800:2024,
    6.2.2.2-a): ``Aw = comprimento efetivo · garganta efetiva``.

    ``effective_length``: comprimento efetivo da solda, ``ℓw`` (m) —
    igual ao comprimento total da solda de dimensão uniforme,
    incluindo os retornos nas extremidades, EXCETO nos casos de
    6.2.2.2-d/e (fator de redução β para filetes longitudinais longos;
    soldas em furos/rasgos) — não implementados nesta fase, ver
    ATENÇÃO no docstring do módulo. ``effective_throat``: garganta
    efetiva, ``te`` — ver :func:`fillet_weld_effective_throat`.
    """
    if not is_positive_finite(effective_length):
        raise ValueError(
            f"fillet_weld_effective_area: effective_length deve ser finito e "
            f"positivo, recebido: {effective_length!r}"
        )
    if not is_positive_finite(effective_throat):
        raise ValueError(
            f"fillet_weld_effective_area: effective_throat deve ser finito e "
            f"positivo, recebido: {effective_throat!r}"
        )
    return effective_length * effective_throat


def fillet_weld_shear_resistance(effective_area: float, fw: float, gamma_w2: float) -> float:
    """Força resistente de cálculo do METAL DA SOLDA ao cisalhamento
    na seção efetiva de uma solda de filete, ``Fw,Rd`` (NBR 8800:2024,
    Tabela 9, linha "Filete"): ``Fw,Rd = 0,6·fw·Aw/γw2``.

    **NÃO verifica o metal-base** (a Tabela 9 exige, adicionalmente,
    que "o metal-base deve atender a 6.5" — ver ATENÇÃO no docstring
    do módulo). O valor retornado é apenas a parcela do metal da
    solda.

    ``effective_area``: ``Aw`` — ver :func:`fillet_weld_effective_area`.
    ``fw``: resistência mínima à tração do metal da solda (Tabela A.4,
    conforme o eletrodo/processo escolhido — não incluída neste
    pacote). ``gamma_w2``: NBR 8800:2024, Tabela 9, nota i — ver
    :func:`~estrutura_metalica.normative.nbr8800.resistance_factors.weld_metal_resistance_factor`.
    """
    if not is_positive_finite(effective_area):
        raise ValueError(
            f"fillet_weld_shear_resistance: effective_area deve ser finito e "
            f"positivo, recebido: {effective_area!r}"
        )
    if not is_positive_finite(fw):
        raise ValueError(
            f"fillet_weld_shear_resistance: fw deve ser finito e positivo, recebido: {fw!r}"
        )
    if not is_positive_finite(gamma_w2):
        raise ValueError(
            f"fillet_weld_shear_resistance: gamma_w2 deve ser finito e positivo, "
            f"recebido: {gamma_w2!r}"
        )
    return 0.6 * fw * effective_area / gamma_w2


def minimum_fillet_weld_leg_size(thinner_part_thickness: float) -> float:
    """Tamanho mínimo da perna de uma solda de filete, ``dw`` (NBR
    8800:2024, Tabela 11), em função da menor espessura das partes
    ligadas:

    - até 6,3 mm: 3 mm;
    - acima de 6,3 até 12,5 mm: 5 mm;
    - acima de 12,5 até 19 mm: 6 mm;
    - acima de 19 mm: 8 mm.

    ``thinner_part_thickness``: menor espessura do metal-base na
    junta (m).
    """
    if not is_positive_finite(thinner_part_thickness):
        raise ValueError(
            f"minimum_fillet_weld_leg_size: thinner_part_thickness deve ser "
            f"finito e positivo, recebido: {thinner_part_thickness!r}"
        )
    for upper_limit, minimum_leg in _TABELA_11_TAMANHO_MINIMO_FILETE:
        if thinner_part_thickness <= upper_limit:
            return minimum_leg
    return _TABELA_11_ACIMA_DE_19MM


@dataclass(frozen=True, slots=True)
class WeldCheckResult(CheckResult):
    """Resultado da verificação ao cisalhamento de uma solda de filete
    (NBR 8800:2024, 6.2.5.1, Tabela 9).

    Ver ATENÇÃO no docstring do módulo: cobre apenas o metal da solda,
    não o metal-base (6.5, não implementado).

    ``fw_rd``: força resistente de cálculo do metal da solda (N) — ver
    :func:`fillet_weld_shear_resistance`.
    """

    fw_sd: float
    fw_rd: float

    def __post_init__(self) -> None:
        if not is_positive_finite(self.fw_sd):
            raise ValueError(f"fw_sd deve ser finito e positivo, recebido: {self.fw_sd!r}")
        if not is_positive_finite(self.fw_rd):
            raise ValueError(f"fw_rd deve ser finito e positivo, recebido: {self.fw_rd!r}")

    @property
    def sd(self) -> float:
        return self.fw_sd

    @property
    def rd(self) -> float:
        return self.fw_rd


def check_fillet_weld_shear(
    fw_sd: float,
    leg_size: float,
    effective_length: float,
    fw: float,
    gamma_w2: float,
    thinner_part_thickness: float,
) -> WeldCheckResult:
    """Verifica ao cisalhamento um grupo de filetes de solda de pernas
    iguais/ângulo reto, carregado concentricamente (NBR 8800:2024,
    6.2.5.1, Tabela 9).

    Valida o tamanho da perna contra o mínimo da Tabela 11
    (:func:`minimum_fillet_weld_leg_size`) antes de calcular ``Fw,Rd``
    — levanta ``ValueError`` se ``leg_size`` for menor que o mínimo
    exigido. **NÃO verifica o metal-base** — ver ATENÇÃO no docstring
    do módulo.

    ``fw_sd``: força solicitante de cálculo na solda (N), sempre
    positiva (uma força cortante em uma solda não tem "sentido"
    normativo a preservar, ao contrário de ``Msd``/``Vsd`` em
    flexão/seções abertas). ``leg_size``: tamanho da perna do filete,
    ``dw`` (m). ``effective_length``: comprimento efetivo da solda,
    ``ℓw`` (m). ``fw``/``gamma_w2``: ver
    :func:`fillet_weld_shear_resistance`. ``thinner_part_thickness``:
    menor espessura das partes ligadas (m) — ver
    :func:`minimum_fillet_weld_leg_size`.
    """
    if not is_positive_finite(fw_sd):
        raise ValueError(
            f"check_fillet_weld_shear: fw_sd deve ser finito e positivo, recebido: {fw_sd!r}"
        )
    minimum_leg = minimum_fillet_weld_leg_size(thinner_part_thickness)
    if leg_size < minimum_leg:
        raise ValueError(
            f"check_fillet_weld_shear: leg_size ({leg_size!r}) menor que o mínimo "
            f"exigido pela Tabela 11 ({minimum_leg!r}) para thinner_part_thickness="
            f"{thinner_part_thickness!r}"
        )

    throat = fillet_weld_effective_throat(leg_size)
    area = fillet_weld_effective_area(effective_length, throat)
    fw_rd = fillet_weld_shear_resistance(area, fw, gamma_w2)
    return WeldCheckResult(fw_sd=fw_sd, fw_rd=fw_rd)
