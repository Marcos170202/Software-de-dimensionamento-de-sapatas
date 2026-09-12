"""Barras prismáticas submetidas a força cortante.

Fonte: ABNT NBR 8800:2024, 5.4.1 "Generalidades" (condição de
dimensionamento, página 53) e 5.4.3 "Força cortante resistente de
cálculo", 5.4.3.1 "Seções I, H e U fletidas em relação ao eixo
perpendicular à alma" (páginas 56-58). Fórmulas conferidas por leitura
direta (renderização visual) do PDF da norma — ver rastreabilidade
completa em ``docs/normative/NBR8800-RULES.md``.

Escopo desta fase: apenas

- 5.4.1.3 — condição de dimensionamento para força cortante
  (``Vsd <= Vrd``; a condição de momento fletor, ``Msd <= Mrd``, NÃO é
  implementada aqui, ver ``flexure.py``);
- 5.4.3.1 — força cortante resistente de cálculo de seções I, H e U
  fletidas em relação ao eixo perpendicular à alma (eixo de maior
  momento de inércia) — o caso mais comum, com a alma resistindo ao
  cisalhamento.

**Fora do escopo**: 5.4.3.2 a 5.4.3.6 (força cortante resistente para
seções tubulares/caixão, T, cantoneiras duplas, I/H/U fletidas em
torno do eixo fraco, e tubulares circulares — mesma estrutura de
fórmula de 5.4.3.1, com ``kv``/área efetiva de cisalhamento
diferentes), 5.4.4 (chapas de reforço/lamelas), 5.4.5 (requisitos para
seções soldadas), 5.5 (combinação de momento fletor, força cortante,
força axial e momento de torção).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ._check_result import CheckResult
from ._validation import is_positive_finite


def effective_shear_area_major_axis(total_depth: float, web_thickness: float) -> float:
    """Área efetiva de cisalhamento, ``Aw = d·tw`` (NBR 8800:2024,
    5.4.3.1.2).

    Válida para seções I, H e U fletidas em relação ao eixo
    perpendicular à alma (eixo de maior momento de inércia).

    ``total_depth``: altura total da seção transversal, ``d``.
    ``web_thickness``: espessura da alma, ``tw``.
    """
    if not is_positive_finite(total_depth):
        raise ValueError(
            f"effective_shear_area_major_axis: total_depth deve ser finito e "
            f"positivo, recebido: {total_depth!r}"
        )
    if not is_positive_finite(web_thickness):
        raise ValueError(
            f"effective_shear_area_major_axis: web_thickness deve ser finito e "
            f"positivo, recebido: {web_thickness!r}"
        )
    return total_depth * web_thickness


def plastic_shear_force(effective_shear_area: float, fy: float) -> float:
    """Força cortante correspondente à plastificação da alma por
    cisalhamento, ``Vpℓ = 0,60·Aw·fy`` (NBR 8800:2024, 5.4.3.1.2).

    ``effective_shear_area``: ``Aw`` — ver
    :func:`effective_shear_area_major_axis` para o caso de 5.4.3.1.
    """
    if not is_positive_finite(effective_shear_area):
        raise ValueError(
            f"plastic_shear_force: effective_shear_area deve ser finito e "
            f"positivo, recebido: {effective_shear_area!r}"
        )
    if not is_positive_finite(fy):
        raise ValueError(f"plastic_shear_force: fy deve ser finito e positivo, recebido: {fy!r}")
    return 0.60 * effective_shear_area * fy


def shear_buckling_coefficient(web_clear_height: float, stiffener_spacing: float | None) -> float:
    """Coeficiente de flambagem por cisalhamento, ``kv`` (NBR
    8800:2024, 5.4.3.1.1).

    ``kv = 5,34`` para almas sem enrijecedores transversais OU para
    ``a/h > 3``; ``kv = 5,0 + 5/(a/h)²`` para os demais casos.

    ``web_clear_height``: altura da alma, ``h`` — a distância entre as
    faces internas das mesas nos perfis soldados, ou esse valor
    subtraindo os dois raios de concordância mesa/alma nos perfis
    laminados. **Não é a altura total da seção** (``d``, usada em
    :func:`effective_shear_area_major_axis`).
    ``stiffener_spacing``: distância entre enrijecedores transversais
    adjacentes, ``a``, ou ``None`` se a alma não tiver enrijecedores
    transversais.
    """
    if not is_positive_finite(web_clear_height):
        raise ValueError(
            f"shear_buckling_coefficient: web_clear_height deve ser finito e "
            f"positivo, recebido: {web_clear_height!r}"
        )
    if stiffener_spacing is None:
        return 5.34
    if not is_positive_finite(stiffener_spacing):
        raise ValueError(
            f"shear_buckling_coefficient: stiffener_spacing deve ser finito e "
            f"positivo (ou None), recebido: {stiffener_spacing!r}"
        )
    ratio = stiffener_spacing / web_clear_height
    if ratio > 3:
        return 5.34
    return 5.0 + 5.0 / ratio**2


def shear_resistance(
    plastic_shear_force: float,
    slenderness: float,
    slenderness_limit_p: float,
    slenderness_limit_r: float,
    gamma_a1: float,
) -> float:
    """Força cortante resistente de cálculo, ``Vrd`` (NBR 8800:2024,
    5.4.3.1.1) — curva em 3 trechos (plastificação / flambagem
    inelástica / flambagem elástica por cisalhamento), mesma estrutura
    conceitual de
    :func:`~estrutura_metalica.normative.nbr8800.compression.reduction_factor`:

    - ``λ <= λp``: ``Vrd = Vpℓ/γa1``;
    - ``λp < λ <= λr``: ``Vrd = (λp/λ)·Vpℓ/γa1``;
    - ``λ > λr``: ``Vrd = 1,24·(λp/λ)²·Vpℓ/γa1``.

    Nota: há uma pequena descontinuidade (~0,4% relativo) exatamente
    em ``λ=λr``, pois ``λr/λp = 1,37/1,10 = 1,24545...`` não é
    exatamente ``1,24``. Mesma natureza da descontinuidade documentada
    em ``compression.reduction_factor`` (~0,04% em ``λ0=1,5``) — uma
    característica das fórmulas empíricas da norma, não um erro de
    implementação.

    ``slenderness_limit_p``/``slenderness_limit_r``: ``λp =
    1,10·sqrt(kv·E/fy)`` e ``λr = 1,37·sqrt(kv·E/fy)`` (calculados pelo
    chamador — ver :func:`shear_buckling_coefficient` para ``kv``).
    """
    if not is_positive_finite(plastic_shear_force):
        raise ValueError(
            f"shear_resistance: plastic_shear_force deve ser finito e positivo, "
            f"recebido: {plastic_shear_force!r}"
        )
    if not is_positive_finite(slenderness):
        raise ValueError(
            f"shear_resistance: slenderness deve ser finito e positivo, "
            f"recebido: {slenderness!r}"
        )
    if not is_positive_finite(slenderness_limit_p):
        raise ValueError(
            f"shear_resistance: slenderness_limit_p deve ser finito e positivo, "
            f"recebido: {slenderness_limit_p!r}"
        )
    if not is_positive_finite(slenderness_limit_r):
        raise ValueError(
            f"shear_resistance: slenderness_limit_r deve ser finito e positivo, "
            f"recebido: {slenderness_limit_r!r}"
        )
    if slenderness_limit_r < slenderness_limit_p:
        raise ValueError(
            f"shear_resistance: slenderness_limit_r ({slenderness_limit_r!r}) não "
            f"pode ser menor que slenderness_limit_p ({slenderness_limit_p!r})"
        )
    if not is_positive_finite(gamma_a1):
        raise ValueError(
            f"shear_resistance: gamma_a1 deve ser finito e positivo, recebido: {gamma_a1!r}"
        )

    if slenderness <= slenderness_limit_p:
        return plastic_shear_force / gamma_a1
    if slenderness <= slenderness_limit_r:
        return (slenderness_limit_p / slenderness) * plastic_shear_force / gamma_a1
    return 1.24 * (slenderness_limit_p / slenderness) ** 2 * plastic_shear_force / gamma_a1


@dataclass(frozen=True, slots=True)
class ShearCheckResult(CheckResult):
    """Resultado da verificação ao cisalhamento de uma barra fletida
    (NBR 8800:2024, 5.4.1.3).

    ``vrd``: força cortante resistente de cálculo (N) — ver
    :func:`shear_resistance`.
    """

    vsd: float
    vrd: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.vsd):
            raise ValueError(f"vsd deve ser finito, recebido: {self.vsd!r}")
        if not is_positive_finite(self.vrd):
            raise ValueError(f"vrd deve ser finito e positivo, recebido: {self.vrd!r}")

    @property
    def sd(self) -> float:
        return self.vsd

    @property
    def rd(self) -> float:
        return self.vrd


def check_shear_major_axis(
    vsd: float,
    total_depth: float,
    web_clear_height: float,
    web_thickness: float,
    fy: float,
    elastic_modulus: float,
    stiffener_spacing: float | None,
    gamma_a1: float,
) -> ShearCheckResult:
    """Verifica ao cisalhamento uma barra I/H/U fletida no eixo forte
    (NBR 8800:2024, 5.4.1.3/5.4.3.1).

    ``vsd``: força cortante solicitante de cálculo (N).
    ``total_depth``: altura total da seção, ``d`` — usada em
    ``Aw=d·tw``. ``web_clear_height``: altura livre da alma, ``h`` —
    usada em ``λ=h/tw`` e em ``kv`` (ver ATENÇÃO em
    :func:`shear_buckling_coefficient` sobre a diferença entre ``h`` e
    ``d``). ``web_thickness``: espessura da alma, ``tw``.
    ``stiffener_spacing``: distância entre enrijecedores transversais
    adjacentes, ou ``None`` se a alma não tiver enrijecedores.
    ``gamma_a1``: NBR 8800:2024, 4.9.2, Tabela 3 — passado direto (não
    :class:`~estrutura_metalica.normative.nbr8800.resistance_factors.SteelResistanceFactors`
    completo) pois esta verificação usa apenas esse coeficiente.
    """
    if not math.isfinite(vsd):
        raise ValueError(f"check_shear_major_axis: vsd deve ser finito, recebido: {vsd!r}")
    if not is_positive_finite(elastic_modulus):
        raise ValueError(
            f"check_shear_major_axis: elastic_modulus deve ser finito e positivo, "
            f"recebido: {elastic_modulus!r}"
        )
    if web_clear_height > total_depth:
        # h (altura livre da alma) é sempre menor que d (altura total,
        # que inclui as duas mesas) para qualquer seção real.
        raise ValueError(
            f"check_shear_major_axis: web_clear_height ({web_clear_height!r}) não pode "
            f"ser maior que total_depth ({total_depth!r})"
        )

    aw = effective_shear_area_major_axis(total_depth, web_thickness)
    vpl = plastic_shear_force(aw, fy)
    kv = shear_buckling_coefficient(web_clear_height, stiffener_spacing)
    lambda_ratio = web_clear_height / web_thickness
    lambda_p = 1.10 * math.sqrt(kv * elastic_modulus / fy)
    lambda_r = 1.37 * math.sqrt(kv * elastic_modulus / fy)
    vrd = shear_resistance(vpl, lambda_ratio, lambda_p, lambda_r, gamma_a1)
    return ShearCheckResult(vsd=vsd, vrd=vrd)
