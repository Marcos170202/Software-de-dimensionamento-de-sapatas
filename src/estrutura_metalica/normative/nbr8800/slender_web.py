"""Momento fletor resistente de cálculo de vigas de alma esbelta.

Fonte: ABNT NBR 8800:2024, Anexo E "Momento fletor resistente de
cálculo de vigas de alma esbelta", E.5/E.6 (páginas 148-149). Fórmulas
conferidas por leitura direta (renderização visual) do PDF da norma —
ver rastreabilidade completa em ``docs/normative/NBR8800-RULES.md``.

Este módulo fecha, para o caso de alma esbelta, a limitação de
segurança registrada em ``flexure.py``: ``check_flexural_resistance_major_axis``
daquele módulo levanta ``ValueError`` quando ``h/tw > λr = 5,70·sqrt(E/fy)``
justamente porque, nesse caso, o Anexo D inteiro deixa de se aplicar e
esta é a fase que implementa a alternativa exigida (Anexo E).

Escopo desta fase: seções I ou H SOLDADAS com dois eixos de simetria
(E.5.2), fletidas no eixo de maior momento de inércia — o caso mais
comum e o único coberto por completo pela Tabela 3 de estados-limite
citada em E.6. Cobre:

- E.5.3-b — limitação adicional de esbeltez da alma para o Anexo E se
  aplicar (``h/tw <= 260`` e ``h/tw`` limitado por um segundo valor que
  depende de ``a/h``);
- E.6.1 — escoamento da mesa tracionada, ``Mrd = Wxt·fy/γa1``;
- E.6.2-a — flambagem lateral com torção (FLT) para seções I/H, com o
  fator de redução ``kpg`` (plate girder) e a curva de 3 trechos
  (reaproveitando :func:`~estrutura_metalica.normative.nbr8800.flexure.flexural_resistance`,
  que já é genérica o suficiente — ver ATENÇÃO 1 abaixo);
- E.6.3 — flambagem local da mesa comprimida (FLM) para seções I/H,
  mesma estrutura de curva, reaproveitando ``kc``
  (:func:`~estrutura_metalica.normative.nbr8800.flexure.flange_local_buckling_coefficient_welded`,
  já que E.5.2 exige seção SOLDADA).

**ATENÇÃO 1 — reaproveitamento de ``flexural_resistance``**: a curva
de 3 trechos de E.6.2/E.6.3 (``λ<=λy``→``My/γa1``;
``λy<λ<=λr``→interpolação linear entre ``My`` e ``Mr``; ``λ>λr``→``Mcr/γa1``)
tem EXATAMENTE a mesma forma matemática da curva de D.2.1 usada em
``flexure.flexural_resistance`` — com ``My``/``λy`` no lugar de
``Mpl``/``λp``. Por isso este módulo chama aquela função diretamente
(``plastic_moment=My``, ``slenderness_limit_p=λy``) em vez de duplicar
a lógica — os nomes dos parâmetros vêm do contexto de D.2.1 (onde
``Mpl`` é de fato um momento de plastificação), mas a fórmula em si é
idêntica e válida aqui.

**ATENÇÃO 2 — LIMITAÇÃO DE SEGURANÇA sobre ``σr``**: as fórmulas de
``Mr`` em E.6.2/E.6.3 usam ``σr`` (tensão residual de compressão nas
mesas) sem redefini-lo dentro do texto do Anexo E capturado. A NBR
8800:2024 define esse mesmo símbolo, para a mesma grandeza física, em
D.2.8-e (página 146): "a tensão residual de compressão nas mesas, σr,
deve ser considerada igual a 30% da resistência ao escoamento do aço
utilizado" — valor reaproveitado aqui (``σr = 0,30·fy``) por ser a
única definição de ``σr`` em todo o documento para essa grandeza, não
por ter sido encontrado redigido novamente dentro do Anexo E. Se uma
leitura futura do Anexo E completo (D.1/D.2 já foram lidos por
completo; a simbologia específica de E pode estar em um trecho não
capturado nas páginas lidas) revelar um valor diferente, este módulo
deve ser corrigido.

**ATENÇÃO 3 — ``ryc`` não é calculado por este módulo**: E.6.2 define
``ryc`` apenas em prosa ("raio de giração, em relação ao eixo que
passa pelo plano médio da alma, da seção formada pela mesa comprimida
mais um terço da altura da alma comprimida"), sem fórmula fechada no
texto capturado. Para não fabricar uma fórmula de memória, este módulo
EXIGE ``ryc`` como parâmetro de entrada (calculado pelo chamador) em
vez de derivá-lo de ``bf``/``tf``/``tw``/``h`` internamente.

Também NÃO implementado nesta fase (ver ``docs/normative/NBR8800-RULES.md``
para a lista completa): seções com um eixo de simetria (E.5.3-a,
``αy``), seções-caixão e tubulares retangulares (E.6.4), flambagem
local da alma (FLA não é um estado-limite do Anexo E — a esbeltez da
própria alma é a premissa do anexo, não um modo de ruptura adicional),
seções LAMINADAS de alma esbelta (E.5.2 restringe o anexo a seções
SOLDADAS).
"""

from __future__ import annotations

import math

from ._validation import is_positive_finite
from .flexure import (
    FlexureCheckResult,
    flange_local_buckling_coefficient_welded,
    flexural_resistance,
)

#: NBR 8800:2024, D.2.8-e (página 146) — ver ATENÇÃO 2 no docstring do
#: módulo: valor reaproveitado do Anexo D para a mesma grandeza `σr`.
_RESIDUAL_STRESS_FRACTION_OF_FY = 0.30


def compression_flange_area_ratio(
    web_clear_height: float, web_thickness: float, flange_width: float, flange_thickness: float
) -> float:
    """Razão ``ar = hc·tw/Afc`` (NBR 8800:2024, E.6.2), usada em
    :func:`plate_girder_bending_strength_reduction_factor`.

    Para seções com dois eixos de simetria (escopo deste módulo),
    ``hc`` (duas vezes a distância do centro geométrico à face interna
    da mesa comprimida) é igual à própria altura livre da alma,
    ``web_clear_height``. ``Afc`` é a área da mesa comprimida,
    ``flange_width · flange_thickness`` — igual à da mesa tracionada
    para seções duplamente simétricas.

    Levanta ``ValueError`` se ``ar > 10`` (NBR 8800:2024, E.6.2: "ar é
    igual à relação hc·tw/Afc, que não pode ser superior a 10").
    """
    if not is_positive_finite(web_clear_height):
        raise ValueError(
            f"compression_flange_area_ratio: web_clear_height deve ser finito e "
            f"positivo, recebido: {web_clear_height!r}"
        )
    if not is_positive_finite(web_thickness):
        raise ValueError(
            f"compression_flange_area_ratio: web_thickness deve ser finito e "
            f"positivo, recebido: {web_thickness!r}"
        )
    if not is_positive_finite(flange_width):
        raise ValueError(
            f"compression_flange_area_ratio: flange_width deve ser finito e "
            f"positivo, recebido: {flange_width!r}"
        )
    if not is_positive_finite(flange_thickness):
        raise ValueError(
            f"compression_flange_area_ratio: flange_thickness deve ser finito e "
            f"positivo, recebido: {flange_thickness!r}"
        )
    ar = (web_clear_height * web_thickness) / (flange_width * flange_thickness)
    if ar > 10.0:
        raise ValueError(
            f"compression_flange_area_ratio: ar ({ar!r}) não pode ser superior a "
            f"10 (NBR 8800:2024, E.6.2)"
        )
    return ar


def plate_girder_bending_strength_reduction_factor(
    ar: float, web_clear_height: float, web_thickness: float, fy: float, elastic_modulus: float
) -> float:
    """Fator de redução da resistência à flexão de viga de alma
    esbelta, ``kpg`` (NBR 8800:2024, E.6.2):

    ``kpg = 1 - [ar/(1200+300·ar)]·(hc/tw - 5,70·sqrt(E/fy)) <= 1,0``.

    Compartilhado por FLT (E.6.2) e FLM (E.6.3) — ambos usam o mesmo
    ``kpg`` para calcular ``My``/``Mr``.

    ``ar``: ver :func:`compression_flange_area_ratio`. ``web_clear_height``:
    ``hc`` (igual à altura livre da alma para seções duplamente
    simétricas — ver :func:`compression_flange_area_ratio`).
    """
    if not is_positive_finite(ar):
        raise ValueError(
            f"plate_girder_bending_strength_reduction_factor: ar deve ser "
            f"finito e positivo, recebido: {ar!r}"
        )
    if not is_positive_finite(web_clear_height):
        raise ValueError(
            f"plate_girder_bending_strength_reduction_factor: web_clear_height "
            f"deve ser finito e positivo, recebido: {web_clear_height!r}"
        )
    if not is_positive_finite(web_thickness):
        raise ValueError(
            f"plate_girder_bending_strength_reduction_factor: web_thickness deve "
            f"ser finito e positivo, recebido: {web_thickness!r}"
        )
    if not is_positive_finite(fy):
        raise ValueError(
            f"plate_girder_bending_strength_reduction_factor: fy deve ser finito "
            f"e positivo, recebido: {fy!r}"
        )
    if not is_positive_finite(elastic_modulus):
        raise ValueError(
            f"plate_girder_bending_strength_reduction_factor: elastic_modulus "
            f"deve ser finito e positivo, recebido: {elastic_modulus!r}"
        )
    kpg = 1.0 - (ar / (1200.0 + 300.0 * ar)) * (
        web_clear_height / web_thickness - 5.70 * math.sqrt(elastic_modulus / fy)
    )
    return min(kpg, 1.0)


def _validate_slender_web_applicability(
    web_clear_height: float,
    web_thickness: float,
    fy: float,
    elastic_modulus: float,
    stiffener_spacing: float | None,
) -> None:
    """Valida E.5.2/E.5.3-b: a alma deve ser efetivamente esbelta
    (``h/tw > 5,70·sqrt(E/fy)``, senão o Anexo D deve ser usado) e
    respeitar o limite superior adicional de E.5.3-b.

    ``stiffener_spacing``: distância entre enrijecedores transversais,
    ``a``. Quando ``None`` (alma sem enrijecedores), a razão ``a/h`` é
    tratada como maior que 1,5 — o ramo ``0,42·E/fy`` de E.5.3-b, mais
    restritivo, é o aplicável a uma alma longa sem enrijecedores.
    """
    slenderness = web_clear_height / web_thickness
    slenderness_r_flat = 5.70 * math.sqrt(elastic_modulus / fy)
    if slenderness <= slenderness_r_flat:
        raise ValueError(
            f"h/tw ({slenderness!r}) não é maior que {slenderness_r_flat!r} "
            f"(NBR 8800:2024, E.5.2) — esta NÃO é uma viga de alma esbelta; "
            f"use o Anexo D (estrutura_metalica.normative.nbr8800.flexure), não "
            f"este módulo."
        )

    if stiffener_spacing is None or stiffener_spacing / web_clear_height > 1.5:
        upper_limit = 0.42 * elastic_modulus / fy
    else:
        upper_limit = 11.7 * math.sqrt(elastic_modulus / fy)
    upper_limit = min(upper_limit, 260.0)
    if slenderness > upper_limit:
        raise ValueError(
            f"h/tw ({slenderness!r}) excede o limite de {upper_limit!r} exigido "
            f"por E.5.3-b para o Anexo E se aplicar."
        )


def check_tension_flange_yielding(
    msd: float, elastic_section_modulus_tension_side: float, fy: float, gamma_a1: float
) -> FlexureCheckResult:
    """Verifica o escoamento da mesa tracionada de uma viga de alma
    esbelta (NBR 8800:2024, E.6.1): ``Mrd = Wxt·fy/γa1``.

    ``elastic_section_modulus_tension_side``: ``Wxt``, módulo de
    resistência elástico do lado tracionado da seção — igual ao
    módulo de resistência elástico usual, ``W``, para seções
    duplamente simétricas.
    """
    if not math.isfinite(msd):
        raise ValueError(f"check_tension_flange_yielding: msd deve ser finito, recebido: {msd!r}")
    if not is_positive_finite(elastic_section_modulus_tension_side):
        raise ValueError(
            f"check_tension_flange_yielding: elastic_section_modulus_tension_side "
            f"deve ser finito e positivo, recebido: {elastic_section_modulus_tension_side!r}"
        )
    if not is_positive_finite(fy):
        raise ValueError(
            f"check_tension_flange_yielding: fy deve ser finito e positivo, recebido: {fy!r}"
        )
    if not is_positive_finite(gamma_a1):
        raise ValueError(
            f"check_tension_flange_yielding: gamma_a1 deve ser finito e "
            f"positivo, recebido: {gamma_a1!r}"
        )
    mrd = elastic_section_modulus_tension_side * fy / gamma_a1
    return FlexureCheckResult(msd=msd, mrd=mrd)


def check_slender_web_lateral_torsional_buckling(
    msd: float,
    fy: float,
    elastic_modulus: float,
    elastic_section_modulus_compression_side: float,
    kpg: float,
    radius_of_gyration_compression_flange_plus_third_web: float,
    unbraced_length: float,
    cb: float,
    gamma_a1: float,
) -> FlexureCheckResult:
    """Verifica a FLT (isoladamente) de uma viga de alma esbelta
    (NBR 8800:2024, E.6.2-a).

    ``elastic_section_modulus_compression_side``: ``Wxc`` — igual ao
    módulo de resistência elástico usual, ``W``, para seções
    duplamente simétricas. ``kpg``: ver
    :func:`plate_girder_bending_strength_reduction_factor`.
    ``radius_of_gyration_compression_flange_plus_third_web``: ``ryc``
    — ver ATENÇÃO 3 no docstring do módulo (não calculado aqui, deve
    ser fornecido pelo chamador). ``unbraced_length``: ``Lb``, mesma
    definição de
    :func:`~estrutura_metalica.normative.nbr8800.flexure.check_lateral_torsional_buckling`.
    """
    if not math.isfinite(msd):
        raise ValueError(
            f"check_slender_web_lateral_torsional_buckling: msd deve ser "
            f"finito, recebido: {msd!r}"
        )
    if not is_positive_finite(fy):
        raise ValueError(
            f"check_slender_web_lateral_torsional_buckling: fy deve ser finito "
            f"e positivo, recebido: {fy!r}"
        )
    if not is_positive_finite(elastic_section_modulus_compression_side):
        raise ValueError(
            f"check_slender_web_lateral_torsional_buckling: "
            f"elastic_section_modulus_compression_side deve ser finito e "
            f"positivo, recebido: {elastic_section_modulus_compression_side!r}"
        )
    if not is_positive_finite(kpg):
        raise ValueError(
            f"check_slender_web_lateral_torsional_buckling: kpg deve ser "
            f"finito e positivo, recebido: {kpg!r}"
        )
    if not is_positive_finite(radius_of_gyration_compression_flange_plus_third_web):
        raise ValueError(
            f"check_slender_web_lateral_torsional_buckling: "
            f"radius_of_gyration_compression_flange_plus_third_web deve ser "
            f"finito e positivo, recebido: "
            f"{radius_of_gyration_compression_flange_plus_third_web!r}"
        )
    if not is_positive_finite(unbraced_length):
        raise ValueError(
            f"check_slender_web_lateral_torsional_buckling: unbraced_length "
            f"deve ser finito e positivo, recebido: {unbraced_length!r}"
        )

    residual_stress = _RESIDUAL_STRESS_FRACTION_OF_FY * fy
    my = kpg * fy * elastic_section_modulus_compression_side
    mr = kpg * (fy - residual_stress) * elastic_section_modulus_compression_side
    slenderness = unbraced_length / radius_of_gyration_compression_flange_plus_third_web
    slenderness_y = 1.10 * math.sqrt(elastic_modulus / fy)
    slenderness_r = math.pi * math.sqrt(elastic_modulus * cb / (fy - residual_stress))
    mcr = (
        cb * kpg * math.pi**2 * elastic_modulus * elastic_section_modulus_compression_side
    ) / slenderness**2

    mrd = flexural_resistance(
        plastic_moment=my,
        residual_moment=mr,
        critical_moment=mcr,
        slenderness=slenderness,
        slenderness_limit_p=slenderness_y,
        slenderness_limit_r=slenderness_r,
        gamma_a1=gamma_a1,
    )
    return FlexureCheckResult(msd=msd, mrd=mrd)


def check_slender_web_flange_local_buckling(
    msd: float,
    fy: float,
    elastic_modulus: float,
    elastic_section_modulus_compression_side: float,
    kpg: float,
    flange_width: float,
    flange_thickness: float,
    web_clear_height: float,
    web_thickness: float,
    gamma_a1: float,
) -> FlexureCheckResult:
    """Verifica a FLM (isoladamente) de uma viga de alma esbelta
    SOLDADA (NBR 8800:2024, E.6.3).

    Reaproveita
    :func:`~estrutura_metalica.normative.nbr8800.flexure.flange_local_buckling_coefficient_welded`
    para ``kc`` — E.5.2 restringe este Anexo a seções SOLDADAS.
    Demais parâmetros: ver :func:`check_slender_web_lateral_torsional_buckling`.
    """
    if not math.isfinite(msd):
        raise ValueError(
            f"check_slender_web_flange_local_buckling: msd deve ser finito, recebido: {msd!r}"
        )
    if not is_positive_finite(fy):
        raise ValueError(
            f"check_slender_web_flange_local_buckling: fy deve ser finito e "
            f"positivo, recebido: {fy!r}"
        )
    if not is_positive_finite(elastic_section_modulus_compression_side):
        raise ValueError(
            f"check_slender_web_flange_local_buckling: "
            f"elastic_section_modulus_compression_side deve ser finito e "
            f"positivo, recebido: {elastic_section_modulus_compression_side!r}"
        )
    if not is_positive_finite(kpg):
        raise ValueError(
            f"check_slender_web_flange_local_buckling: kpg deve ser finito e "
            f"positivo, recebido: {kpg!r}"
        )
    if not is_positive_finite(flange_width):
        raise ValueError(
            f"check_slender_web_flange_local_buckling: flange_width deve ser "
            f"finito e positivo, recebido: {flange_width!r}"
        )
    if not is_positive_finite(flange_thickness):
        raise ValueError(
            f"check_slender_web_flange_local_buckling: flange_thickness deve "
            f"ser finito e positivo, recebido: {flange_thickness!r}"
        )

    residual_stress = _RESIDUAL_STRESS_FRACTION_OF_FY * fy
    my = kpg * fy * elastic_section_modulus_compression_side
    mr = kpg * (fy - residual_stress) * elastic_section_modulus_compression_side
    kc = flange_local_buckling_coefficient_welded(
        web_clear_height=web_clear_height, web_thickness=web_thickness
    )
    slenderness = flange_width / (2.0 * flange_thickness)
    slenderness_y = 0.38 * math.sqrt(elastic_modulus / fy)
    slenderness_r = 0.95 * math.sqrt(kc * elastic_modulus / (fy - residual_stress))
    mcr = (
        0.90 * kpg * elastic_modulus * kc * elastic_section_modulus_compression_side
    ) / slenderness**2

    mrd = flexural_resistance(
        plastic_moment=my,
        residual_moment=mr,
        critical_moment=mcr,
        slenderness=slenderness,
        slenderness_limit_p=slenderness_y,
        slenderness_limit_r=slenderness_r,
        gamma_a1=gamma_a1,
    )
    return FlexureCheckResult(msd=msd, mrd=mrd)


def check_flexural_resistance_slender_web_major_axis(
    msd: float,
    fy: float,
    elastic_modulus: float,
    elastic_section_modulus: float,
    radius_of_gyration_compression_flange_plus_third_web: float,
    unbraced_length: float,
    cb: float,
    flange_width: float,
    flange_thickness: float,
    web_clear_height: float,
    web_thickness: float,
    stiffener_spacing: float | None,
    gamma_a1: float,
) -> FlexureCheckResult:
    """Verifica o momento fletor resistente de cálculo COMPLETO
    (escoamento da mesa tracionada + FLT + FLM) de uma viga de alma
    esbelta SOLDADA, duplamente simétrica, fletida no eixo maior (NBR
    8800:2024, Anexo E).

    ``Mrd = min(Mrd_E.6.1, Mrd_FLT, Mrd_FLM)``. Valida as precondições
    de E.5.2/E.5.3-b antes de calcular — levanta ``ValueError`` se a
    alma não for de fato esbelta (``h/tw <= 5,70·sqrt(E/fy)`` — use o
    Anexo D,
    :func:`~estrutura_metalica.normative.nbr8800.flexure.check_flexural_resistance_major_axis`,
    nesse caso) ou se ``h/tw`` exceder o limite adicional de E.5.3-b.

    ``elastic_section_modulus``: ``Wxc = Wxt = W`` para seções
    duplamente simétricas (ver ATENÇÃO nos docstrings de
    :func:`check_tension_flange_yielding`/
    :func:`check_slender_web_lateral_torsional_buckling`).
    ``radius_of_gyration_compression_flange_plus_third_web``: ``ryc``
    — ver ATENÇÃO 3 no docstring do módulo (fornecido pelo chamador,
    não calculado aqui). ``stiffener_spacing``: ``a``, distância entre
    enrijecedores transversais, ou ``None`` se a alma não tiver
    enrijecedores (ver :func:`_validate_slender_web_applicability`).

    Retorna
    -------
    :class:`~estrutura_metalica.normative.nbr8800.flexure.FlexureCheckResult`
    com ``mrd`` = o MENOR entre E.6.1, FLT e FLM.
    """
    if not math.isfinite(msd):
        raise ValueError(
            f"check_flexural_resistance_slender_web_major_axis: msd deve ser "
            f"finito, recebido: {msd!r}"
        )
    if not is_positive_finite(fy):
        raise ValueError(
            f"check_flexural_resistance_slender_web_major_axis: fy deve ser "
            f"finito e positivo, recebido: {fy!r}"
        )
    if not is_positive_finite(elastic_modulus):
        raise ValueError(
            f"check_flexural_resistance_slender_web_major_axis: "
            f"elastic_modulus deve ser finito e positivo, recebido: "
            f"{elastic_modulus!r}"
        )
    if not is_positive_finite(elastic_section_modulus):
        raise ValueError(
            f"check_flexural_resistance_slender_web_major_axis: "
            f"elastic_section_modulus deve ser finito e positivo, recebido: "
            f"{elastic_section_modulus!r}"
        )
    if not is_positive_finite(web_clear_height):
        raise ValueError(
            f"check_flexural_resistance_slender_web_major_axis: "
            f"web_clear_height deve ser finito e positivo, recebido: "
            f"{web_clear_height!r}"
        )
    if not is_positive_finite(web_thickness):
        raise ValueError(
            f"check_flexural_resistance_slender_web_major_axis: web_thickness "
            f"deve ser finito e positivo, recebido: {web_thickness!r}"
        )

    _validate_slender_web_applicability(
        web_clear_height=web_clear_height,
        web_thickness=web_thickness,
        fy=fy,
        elastic_modulus=elastic_modulus,
        stiffener_spacing=stiffener_spacing,
    )

    ar = compression_flange_area_ratio(
        web_clear_height=web_clear_height,
        web_thickness=web_thickness,
        flange_width=flange_width,
        flange_thickness=flange_thickness,
    )
    kpg = plate_girder_bending_strength_reduction_factor(
        ar=ar,
        web_clear_height=web_clear_height,
        web_thickness=web_thickness,
        fy=fy,
        elastic_modulus=elastic_modulus,
    )

    tension_flange = check_tension_flange_yielding(
        msd=msd,
        elastic_section_modulus_tension_side=elastic_section_modulus,
        fy=fy,
        gamma_a1=gamma_a1,
    )
    flt = check_slender_web_lateral_torsional_buckling(
        msd=msd,
        fy=fy,
        elastic_modulus=elastic_modulus,
        elastic_section_modulus_compression_side=elastic_section_modulus,
        kpg=kpg,
        radius_of_gyration_compression_flange_plus_third_web=(
            radius_of_gyration_compression_flange_plus_third_web
        ),
        unbraced_length=unbraced_length,
        cb=cb,
        gamma_a1=gamma_a1,
    )
    flm = check_slender_web_flange_local_buckling(
        msd=msd,
        fy=fy,
        elastic_modulus=elastic_modulus,
        elastic_section_modulus_compression_side=elastic_section_modulus,
        kpg=kpg,
        flange_width=flange_width,
        flange_thickness=flange_thickness,
        web_clear_height=web_clear_height,
        web_thickness=web_thickness,
        gamma_a1=gamma_a1,
    )

    mrd = min(tension_flange.mrd, flt.mrd, flm.mrd)
    return FlexureCheckResult(msd=msd, mrd=mrd)
