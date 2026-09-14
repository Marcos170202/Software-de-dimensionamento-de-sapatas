"""Barras prismáticas submetidas a momento fletor.

Fonte: ABNT NBR 8800:2024, 5.4.2 "Momento fletor resistente de
cálculo" (página 54) e Anexo D "Momento fletor resistente de cálculo
de vigas de alma não esbelta", D.1/D.2/D.2.8-a,e,f,h (páginas 137,
144-146). Fórmulas conferidas por leitura direta (renderização visual)
do PDF da norma — ver rastreabilidade completa em
``docs/normative/NBR8800-RULES.md``.

Escopo desta fase: os três estados-limite da PRIMEIRA linha da Tabela
D.1 — flambagem lateral com torção (FLT), flambagem local da mesa
comprimida (FLM) e flambagem local da alma (FLA) — para seções I, H
com dois eixos de simetria e seções U não sujeitas a momento de
torção, fletidas em relação ao eixo de MAIOR momento de inércia (o
caso mais comum). Cobre:

- 5.4.1.3/5.4.2.1 — condição de dimensionamento (``Msd <= Mrd``), com
  ``Mrd = min(Mrd_FLT, Mrd_FLM, Mrd_FLA)``
  (:func:`check_flexural_resistance_major_axis`);
- 5.4.2.2 — limite ``Mrd <= 1,50·W·fy/γa1``, aplicado ao ``Mrd``
  final;
- 5.4.2.3-a — fator ``Cb`` (caso geral, ``Rm=1,0`` para seções
  duplamente simétricas — os demais casos de 5.4.2.3/5.4.2.4 não são
  implementados);
- D.2.1/D.2.8-a — curva de 3 trechos de ``Mrd`` para FLT (plastificação
  / escoamento com tensão residual / flambagem elástica), com
  ``Mcr``/``λr`` conforme D.2.8-a;
- D.2.8-e/f/h — a mesma curva de 3 trechos para FLM, com ``Mcr``/``λr``
  distintos para perfis LAMINADOS e SOLDADOS (este último usando o
  coeficiente ``kc`` da Tabela 4, nota de rodapé a);
- Tabela D.1 (FLA, primeira linha) — a mesma curva de 3 trechos para
  FLA, restrita a vigas de alma NÃO esbelta (D.1.2) — ver ATENÇÃO
  abaixo.

**ATENÇÃO — LIMITAÇÃO DE SEGURANÇA (Anexo E, vigas de alma esbelta)**:
D.1.2 restringe TODO o Anexo D (não apenas o estado-limite FLA) a
"vigas de alma não esbelta" (``λ = h/tw <= λr = 5,70·sqrt(E/fy)``). Se
a alma for esbelta, a norma exige usar o Anexo E (vigas de alma
esbelta) para TODA a verificação — não apenas substituir o ramo de
FLA. :func:`check_flexural_resistance_major_axis` VALIDA essa
precondição (``ValueError`` se violada) antes de calcular
FLT/FLM/FLA, mas o Anexo E em si NÃO está implementado — para vigas de
alma esbelta, nenhuma função deste módulo pode ser usada.

Também NÃO implementado (fora do escopo desta fase, ver
``docs/normative/NBR8800-RULES.md`` para a lista completa): 5.4.2.3,
casos b) e c), e 5.4.2.4/5.4.2.5 (``Cb`` para balanços e para seções
monossimétricas — apenas o caso geral duplamente simétrico está
aqui); 5.4.2.6 (furos na mesa tracionada); demais linhas da Tabela D.1
(seções monossimétricas, tubulares/caixão, sólidas) e flexão em torno
do eixo de menor momento de inércia (onde FLT não se aplica); Anexo E
(ver ATENÇÃO acima); Anexos F/G/H/I; 5.5 (combinação de esforços).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ._check_result import CheckResult
from ._validation import is_positive_finite


def moment_gradient_factor_doubly_symmetric(
    m_max: float, m_a: float, m_b: float, m_c: float
) -> float:
    """Fator de modificação para diagrama de momento fletor não
    uniforme, ``Cb`` (NBR 8800:2024, 5.4.2.3-a, caso geral).

    ``Cb = 12,5·Mmax / (2,5·Mmax + 3·MA + 4·MB + 3·MC) · Rm``, com
    ``Rm = 1,0`` para seções duplamente simétricas (único caso
    coberto aqui — a fórmula geral de ``Rm`` para seções
    monossimétricas com curvatura reversa não é implementada). Não
    cobre os casos b)/c) de 5.4.2.3 (balanços) nem 5.4.2.4/5.4.2.5.

    ``m_max``: momento fletor máximo solicitante de cálculo, em
    módulo, no comprimento destravado. ``m_a``/``m_b``/``m_c``:
    momento fletor solicitante de cálculo, em módulo, a 1/4, no meio e
    a 3/4 do comprimento destravado (podem ser zero, mas não
    negativos).
    """
    if not is_positive_finite(m_max):
        raise ValueError(
            f"moment_gradient_factor_doubly_symmetric: m_max deve ser finito e "
            f"positivo, recebido: {m_max!r}"
        )
    for name, value in (("m_a", m_a), ("m_b", m_b), ("m_c", m_c)):
        if not math.isfinite(value) or value < 0:
            raise ValueError(
                f"moment_gradient_factor_doubly_symmetric: {name} deve ser finito e "
                f"não-negativo, recebido: {value!r}"
            )
    return 12.5 * m_max / (2.5 * m_max + 3.0 * m_a + 4.0 * m_b + 3.0 * m_c)


def warping_constant_i_section(
    minor_axis_moment_of_inertia: float, total_depth: float, flange_thickness: float
) -> float:
    """Constante de empenamento, ``Cw``, para seções I (NBR 8800:2024,
    D.2.8-a): ``Cw = Iy·(d-tf)²/4``.

    Útil quando a propriedade não está disponível de catálogo. Não
    cobre a fórmula (mais complexa) de ``Cw`` para seções U, também
    dada em D.2.8-a.

    ``minor_axis_moment_of_inertia``: ``Iy`` — o eixo perpendicular ao
    eixo de flexão (``SteelSection.iy`` nesta convenção). ``total_depth``:
    altura total da seção, ``d``. ``flange_thickness``: espessura da
    mesa, ``tf``.
    """
    if not is_positive_finite(minor_axis_moment_of_inertia):
        raise ValueError(
            f"warping_constant_i_section: minor_axis_moment_of_inertia deve ser "
            f"finito e positivo, recebido: {minor_axis_moment_of_inertia!r}"
        )
    if not is_positive_finite(total_depth):
        raise ValueError(
            f"warping_constant_i_section: total_depth deve ser finito e positivo, "
            f"recebido: {total_depth!r}"
        )
    if not is_positive_finite(flange_thickness):
        raise ValueError(
            f"warping_constant_i_section: flange_thickness deve ser finito e "
            f"positivo, recebido: {flange_thickness!r}"
        )
    if flange_thickness >= total_depth:
        # tf < d sempre para qualquer seção I real (mesma lógica de
        # web_clear_height<=total_depth em shear.py).
        raise ValueError(
            f"warping_constant_i_section: flange_thickness ({flange_thickness!r}) "
            f"deve ser menor que total_depth ({total_depth!r})"
        )
    return minor_axis_moment_of_inertia * (total_depth - flange_thickness) ** 2 / 4.0


def lateral_torsional_buckling_moment(
    cb: float,
    elastic_modulus: float,
    minor_axis_moment_of_inertia: float,
    torsion_constant: float,
    warping_constant: float,
    unbraced_length: float,
) -> float:
    """Momento fletor crítico de flambagem elástica por FLT, ``Mcr``
    (NBR 8800:2024, D.2.8-a):

    ``Mcr = (Cb·π²·E·Iy/Lb²) · sqrt((Cw/Iy)·(1 + 0,039·J·Lb²/Cw))``.

    ``cb``: fator de modificação — ver
    :func:`moment_gradient_factor_doubly_symmetric`. ``minor_axis_moment_of_inertia``:
    ``Iy``, eixo perpendicular ao eixo de flexão. ``torsion_constant``:
    constante de torção de St. Venant, ``J``. ``warping_constant``:
    constante de empenamento, ``Cw`` — ver :func:`warping_constant_i_section`.
    ``unbraced_length``: comprimento destravado à FLT, ``Lb``.
    """
    if not is_positive_finite(cb):
        raise ValueError(
            f"lateral_torsional_buckling_moment: cb deve ser finito e positivo, "
            f"recebido: {cb!r}"
        )
    if not is_positive_finite(elastic_modulus):
        raise ValueError(
            f"lateral_torsional_buckling_moment: elastic_modulus deve ser finito e "
            f"positivo, recebido: {elastic_modulus!r}"
        )
    if not is_positive_finite(minor_axis_moment_of_inertia):
        raise ValueError(
            f"lateral_torsional_buckling_moment: minor_axis_moment_of_inertia deve "
            f"ser finito e positivo, recebido: {minor_axis_moment_of_inertia!r}"
        )
    if not is_positive_finite(torsion_constant):
        raise ValueError(
            f"lateral_torsional_buckling_moment: torsion_constant deve ser finito e "
            f"positivo, recebido: {torsion_constant!r}"
        )
    if not is_positive_finite(warping_constant):
        raise ValueError(
            f"lateral_torsional_buckling_moment: warping_constant deve ser finito e "
            f"positivo, recebido: {warping_constant!r}"
        )
    if not is_positive_finite(unbraced_length):
        raise ValueError(
            f"lateral_torsional_buckling_moment: unbraced_length deve ser finito e "
            f"positivo, recebido: {unbraced_length!r}"
        )
    return (
        cb * math.pi**2 * elastic_modulus * minor_axis_moment_of_inertia / unbraced_length**2
    ) * math.sqrt(
        (warping_constant / minor_axis_moment_of_inertia)
        * (1.0 + 0.039 * torsion_constant * unbraced_length**2 / warping_constant)
    )


def lateral_torsional_buckling_slenderness_limit(
    cb: float,
    elastic_modulus: float,
    minor_axis_moment_of_inertia: float,
    torsion_constant: float,
    warping_constant: float,
    radius_of_gyration_minor_axis: float,
    residual_moment: float,
) -> float:
    """Parâmetro de esbeltez correspondente ao início do escoamento,
    ``λr`` (NBR 8800:2024, D.2.8-a):

    ``β1 = Mr/(E·J)``;
    ``λr = (1,38·Cb·sqrt(Iy·J)/(ry·J·β1)) · sqrt(1 + sqrt(1 + 27·Cw·β1²/(Cb²·Iy)))``.

    ``radius_of_gyration_minor_axis``: ``ry``, eixo perpendicular ao
    eixo de flexão. ``residual_moment``: momento fletor correspondente
    ao início do escoamento considerando tensão residual, ``Mr =
    (fy-0,3·fy)·W`` — ver :func:`check_lateral_torsional_buckling`.
    Demais parâmetros: ver :func:`lateral_torsional_buckling_moment`.
    """
    if not is_positive_finite(cb):
        raise ValueError(
            f"lateral_torsional_buckling_slenderness_limit: cb deve ser finito e "
            f"positivo, recebido: {cb!r}"
        )
    if not is_positive_finite(elastic_modulus):
        raise ValueError(
            f"lateral_torsional_buckling_slenderness_limit: elastic_modulus deve "
            f"ser finito e positivo, recebido: {elastic_modulus!r}"
        )
    if not is_positive_finite(minor_axis_moment_of_inertia):
        raise ValueError(
            f"lateral_torsional_buckling_slenderness_limit: "
            f"minor_axis_moment_of_inertia deve ser finito e positivo, recebido: "
            f"{minor_axis_moment_of_inertia!r}"
        )
    if not is_positive_finite(torsion_constant):
        raise ValueError(
            f"lateral_torsional_buckling_slenderness_limit: torsion_constant deve "
            f"ser finito e positivo, recebido: {torsion_constant!r}"
        )
    if not is_positive_finite(warping_constant):
        raise ValueError(
            f"lateral_torsional_buckling_slenderness_limit: warping_constant deve "
            f"ser finito e positivo, recebido: {warping_constant!r}"
        )
    if not is_positive_finite(radius_of_gyration_minor_axis):
        raise ValueError(
            f"lateral_torsional_buckling_slenderness_limit: "
            f"radius_of_gyration_minor_axis deve ser finito e positivo, recebido: "
            f"{radius_of_gyration_minor_axis!r}"
        )
    if not is_positive_finite(residual_moment):
        raise ValueError(
            f"lateral_torsional_buckling_slenderness_limit: residual_moment deve "
            f"ser finito e positivo, recebido: {residual_moment!r}"
        )
    beta1 = residual_moment / (elastic_modulus * torsion_constant)
    return (
        1.38
        * cb
        * math.sqrt(minor_axis_moment_of_inertia * torsion_constant)
        / (radius_of_gyration_minor_axis * torsion_constant * beta1)
    ) * math.sqrt(
        1.0
        + math.sqrt(
            1.0 + 27.0 * warping_constant * beta1**2 / (cb**2 * minor_axis_moment_of_inertia)
        )
    )


def flexural_resistance(
    plastic_moment: float,
    residual_moment: float,
    critical_moment: float,
    slenderness: float,
    slenderness_limit_p: float,
    slenderness_limit_r: float,
    gamma_a1: float,
) -> float:
    """Momento fletor resistente de cálculo, ``Mrd``, curva de 3
    trechos (NBR 8800:2024, D.2.1):

    - ``λ <= λp``: ``Mrd = Mpℓ/γa1``;
    - ``λp < λ <= λr``: ``Mrd = [Mpℓ - (Mpℓ-Mr)·(λ-λp)/(λr-λp)]/γa1``;
    - ``λ > λr``: ``Mrd = Mcr/γa1``.

    Mesma forma conceitual de
    :func:`~estrutura_metalica.normative.nbr8800.shear.shear_resistance`
    e de
    :func:`~estrutura_metalica.normative.nbr8800.compression.reduction_factor`
    (plastificação / regime inelástico com tensão residual / flambagem
    elástica). Escrita de forma genérica o suficiente para ser
    reaproveitada pelos estados-limite FLM e FLA (mesma estrutura de
    fórmula na Tabela D.1), não apenas por FLT.

    Nota: para FLT, há uma pequena descontinuidade (~0,18% relativo)
    exatamente em ``λ=λr`` — ``critical_moment`` calculado em ``λr``
    (via :func:`lateral_torsional_buckling_moment`) não coincide
    exatamente com ``residual_moment`` (o limite que o segundo ramo
    atinge em ``λr``), pois ``Mcr`` e ``λr`` (D.2.8-a) são fórmulas
    empíricas independentes. Mesma natureza das descontinuidades já
    documentadas em ``compression.reduction_factor`` (~0,04% em
    ``λ0=1,5``) e ``shear.shear_resistance`` (~0,4% em ``λ=λr``) — uma
    característica das fórmulas da norma, não um erro de
    implementação.

    ``plastic_moment``: momento fletor de plastificação da seção,
    ``Mpℓ=fy·Z``, ``Z`` o módulo de resistência plástico.
    ``residual_moment``: momento fletor correspondente ao início do
    escoamento considerando tensão residual, ``Mr``. ``critical_moment``:
    momento fletor crítico de flambagem elástica, ``Mcr``.
    ``slenderness``/``slenderness_limit_p``/``slenderness_limit_r``:
    índice de esbeltez e seus limites (``λ``, ``λp``, ``λr``) — para
    FLT, ``λ=Lb/ry``. ``gamma_a1``: NBR 8800:2024, 4.9.2, Tabela 3.
    """
    if not is_positive_finite(plastic_moment):
        raise ValueError(
            f"flexural_resistance: plastic_moment deve ser finito e positivo, "
            f"recebido: {plastic_moment!r}"
        )
    if not is_positive_finite(residual_moment):
        raise ValueError(
            f"flexural_resistance: residual_moment deve ser finito e positivo, "
            f"recebido: {residual_moment!r}"
        )
    if residual_moment > plastic_moment:
        # Mr <= Mpl sempre (Mr=(fy-σr)·W <= fy·Z=Mpl, já que Z>=W para
        # qualquer seção real, fator de forma >= 1).
        raise ValueError(
            f"flexural_resistance: residual_moment ({residual_moment!r}) não pode "
            f"ser maior que plastic_moment ({plastic_moment!r})"
        )
    if not is_positive_finite(critical_moment):
        raise ValueError(
            f"flexural_resistance: critical_moment deve ser finito e positivo, "
            f"recebido: {critical_moment!r}"
        )
    if not is_positive_finite(slenderness):
        raise ValueError(
            f"flexural_resistance: slenderness deve ser finito e positivo, "
            f"recebido: {slenderness!r}"
        )
    if not is_positive_finite(slenderness_limit_p):
        raise ValueError(
            f"flexural_resistance: slenderness_limit_p deve ser finito e positivo, "
            f"recebido: {slenderness_limit_p!r}"
        )
    if not is_positive_finite(slenderness_limit_r):
        raise ValueError(
            f"flexural_resistance: slenderness_limit_r deve ser finito e positivo, "
            f"recebido: {slenderness_limit_r!r}"
        )
    if slenderness_limit_r < slenderness_limit_p:
        raise ValueError(
            f"flexural_resistance: slenderness_limit_r ({slenderness_limit_r!r}) não "
            f"pode ser menor que slenderness_limit_p ({slenderness_limit_p!r})"
        )
    if not is_positive_finite(gamma_a1):
        raise ValueError(
            f"flexural_resistance: gamma_a1 deve ser finito e positivo, "
            f"recebido: {gamma_a1!r}"
        )

    if slenderness <= slenderness_limit_p:
        return plastic_moment / gamma_a1
    if slenderness <= slenderness_limit_r:
        ratio = (slenderness - slenderness_limit_p) / (slenderness_limit_r - slenderness_limit_p)
        return (plastic_moment - (plastic_moment - residual_moment) * ratio) / gamma_a1
    return critical_moment / gamma_a1


@dataclass(frozen=True, slots=True)
class FlexureCheckResult(CheckResult):
    """Resultado da verificação ao momento fletor de uma barra (NBR
    8800:2024, 5.4.1.3).

    **ATENÇÃO sobre o sinal de ``msd``**: esta classe NÃO toma o valor
    absoluto de ``msd`` automaticamente — ``is_ok``/``utilization``
    (herdados de :class:`CheckResult`) comparam ``msd`` diretamente
    contra ``mrd`` (sempre positivo). A condição normativa de 5.4.1.3
    é, na prática, sobre a MAGNITUDE do momento fletor (``|Msd|<=Mrd``);
    um ``msd`` negativo grande (momento no sentido oposto, comum em
    vigas contínuas com regiões de momento negativo) faria ``is_ok``
    retornar ``True`` de forma NÃO CONSERVADORA. **O chamador é
    responsável por passar ``abs(msd)``** caso o interesse seja
    verificar a magnitude do momento solicitante — mesma
    responsabilidade já documentada para ``Vsd`` em
    :class:`~estrutura_metalica.normative.nbr8800.shear.ShearCheckResult`.

    ``mrd``: momento fletor resistente de cálculo (N·m) — ver
    :func:`flexural_resistance`.
    """

    msd: float
    mrd: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.msd):
            raise ValueError(f"msd deve ser finito, recebido: {self.msd!r}")
        if not is_positive_finite(self.mrd):
            raise ValueError(f"mrd deve ser finito e positivo, recebido: {self.mrd!r}")

    @property
    def sd(self) -> float:
        return self.msd

    @property
    def rd(self) -> float:
        return self.mrd


def check_lateral_torsional_buckling(
    msd: float,
    fy: float,
    elastic_modulus: float,
    elastic_section_modulus: float,
    plastic_section_modulus: float,
    minor_axis_moment_of_inertia: float,
    torsion_constant: float,
    warping_constant: float,
    radius_of_gyration_minor_axis: float,
    unbraced_length: float,
    cb: float,
    gamma_a1: float,
) -> FlexureCheckResult:
    """Verifica a FLT (isoladamente) de uma barra I/H/U duplamente
    simétrica fletida no eixo maior (NBR 8800:2024, 5.4.1.3 e Anexo D,
    Tabela D.1/D.2.8-a).

    **Cobre apenas FLT** — não é o ``Mrd`` completo de 5.4.2.1 (que
    também precisa de FLM e FLA); ver
    :func:`check_flexural_resistance_major_axis` para o ``Mrd``
    completo.

    Convenção de eixos: os parâmetros de FLT
    (``minor_axis_moment_of_inertia``, ``radius_of_gyration_minor_axis``)
    sempre se referem ao eixo PERPENDICULAR ao eixo de flexão
    (``SteelSection.iy``/``ry`` nesta convenção), independentemente de
    qual eixo é fletido — é assim que a própria fórmula de FLT é
    definida (a resistência à flambagem lateral vem da rigidez à
    flexão lateral e à torção, não da rigidez em torno do eixo de
    flexão).

    ``msd``: momento fletor solicitante de cálculo (N·m) — ver ATENÇÃO
    sobre sinal em :class:`FlexureCheckResult`. ``elastic_section_modulus``/
    ``plastic_section_modulus``: módulo de resistência elástico/plástico
    em relação ao eixo de flexão, ``W``/``Z``. ``cb``: ver
    :func:`moment_gradient_factor_doubly_symmetric`, ou ``1,0`` de
    forma conservadora (sempre válido, 5.4.2.3). ``gamma_a1``: NBR
    8800:2024, 4.9.2, Tabela 3 — passado direto (mesmo padrão de
    ``shear.check_shear_major_axis``).
    """
    if not math.isfinite(msd):
        raise ValueError(
            f"check_lateral_torsional_buckling: msd deve ser finito, recebido: {msd!r}"
        )
    if not is_positive_finite(fy):
        raise ValueError(
            f"check_lateral_torsional_buckling: fy deve ser finito e positivo, "
            f"recebido: {fy!r}"
        )
    if not is_positive_finite(elastic_section_modulus):
        raise ValueError(
            f"check_lateral_torsional_buckling: elastic_section_modulus deve ser "
            f"finito e positivo, recebido: {elastic_section_modulus!r}"
        )
    if not is_positive_finite(plastic_section_modulus):
        raise ValueError(
            f"check_lateral_torsional_buckling: plastic_section_modulus deve ser "
            f"finito e positivo, recebido: {plastic_section_modulus!r}"
        )
    if plastic_section_modulus < elastic_section_modulus:
        # Z >= W sempre (fator de forma >= 1) para qualquer seção real.
        raise ValueError(
            f"check_lateral_torsional_buckling: plastic_section_modulus "
            f"({plastic_section_modulus!r}) não pode ser menor que "
            f"elastic_section_modulus ({elastic_section_modulus!r})"
        )
    if not is_positive_finite(radius_of_gyration_minor_axis):
        raise ValueError(
            f"check_lateral_torsional_buckling: radius_of_gyration_minor_axis deve "
            f"ser finito e positivo, recebido: {radius_of_gyration_minor_axis!r}"
        )
    if not is_positive_finite(unbraced_length):
        raise ValueError(
            f"check_lateral_torsional_buckling: unbraced_length deve ser finito e "
            f"positivo, recebido: {unbraced_length!r}"
        )

    residual_stress = 0.30 * fy
    residual_moment = (fy - residual_stress) * elastic_section_modulus
    plastic_moment = fy * plastic_section_modulus

    critical_moment = lateral_torsional_buckling_moment(
        cb=cb,
        elastic_modulus=elastic_modulus,
        minor_axis_moment_of_inertia=minor_axis_moment_of_inertia,
        torsion_constant=torsion_constant,
        warping_constant=warping_constant,
        unbraced_length=unbraced_length,
    )
    slenderness_limit_p = 1.76 * math.sqrt(elastic_modulus / fy)
    slenderness_limit_r = lateral_torsional_buckling_slenderness_limit(
        cb=cb,
        elastic_modulus=elastic_modulus,
        minor_axis_moment_of_inertia=minor_axis_moment_of_inertia,
        torsion_constant=torsion_constant,
        warping_constant=warping_constant,
        radius_of_gyration_minor_axis=radius_of_gyration_minor_axis,
        residual_moment=residual_moment,
    )
    slenderness = unbraced_length / radius_of_gyration_minor_axis

    mrd = flexural_resistance(
        plastic_moment=plastic_moment,
        residual_moment=residual_moment,
        critical_moment=critical_moment,
        slenderness=slenderness,
        slenderness_limit_p=slenderness_limit_p,
        slenderness_limit_r=slenderness_limit_r,
        gamma_a1=gamma_a1,
    )
    return FlexureCheckResult(msd=msd, mrd=mrd)


def flange_local_buckling_coefficient_welded(
    web_clear_height: float, web_thickness: float
) -> float:
    """Coeficiente ``kc`` para FLM de perfis SOLDADOS (Tabela 4, nota
    de rodapé a): ``kc = 4/sqrt(h/tw)``, limitado a ``0,35 <= kc <=
    0,76``.

    Usado apenas em :func:`flange_local_buckling_moment_welded` —
    perfis LAMINADOS não usam ``kc``, ver
    :func:`flange_local_buckling_moment_rolled`.

    ``web_clear_height``: altura da alma, ``h`` — mesma definição
    usada em ``shear.py``. ``web_thickness``: espessura da alma,
    ``tw``.
    """
    if not is_positive_finite(web_clear_height):
        raise ValueError(
            f"flange_local_buckling_coefficient_welded: web_clear_height deve ser "
            f"finito e positivo, recebido: {web_clear_height!r}"
        )
    if not is_positive_finite(web_thickness):
        raise ValueError(
            f"flange_local_buckling_coefficient_welded: web_thickness deve ser "
            f"finito e positivo, recebido: {web_thickness!r}"
        )
    kc = 4.0 / math.sqrt(web_clear_height / web_thickness)
    return min(0.76, max(0.35, kc))


def flange_local_buckling_moment_rolled(
    elastic_modulus: float, compressed_side_section_modulus: float, slenderness: float
) -> float:
    """Momento fletor crítico de FLM para perfis LAMINADOS, ``Mcr``
    (NBR 8800:2024, D.2.8-f): ``Mcr = 0,69·E/λ² · Wc``.

    ``compressed_side_section_modulus``: módulo de resistência
    elástico do lado comprimido da seção, ``Wc`` — para seções
    duplamente simétricas, igual a ``elastic_section_modulus``.
    ``slenderness``: índice de esbeltez da mesa, ``λ=b/t`` (D.2.8-h,
    ``b`` é a metade da largura total da mesa para seções I/H).
    """
    if not is_positive_finite(elastic_modulus):
        raise ValueError(
            f"flange_local_buckling_moment_rolled: elastic_modulus deve ser finito "
            f"e positivo, recebido: {elastic_modulus!r}"
        )
    if not is_positive_finite(compressed_side_section_modulus):
        raise ValueError(
            f"flange_local_buckling_moment_rolled: compressed_side_section_modulus "
            f"deve ser finito e positivo, recebido: {compressed_side_section_modulus!r}"
        )
    if not is_positive_finite(slenderness):
        raise ValueError(
            f"flange_local_buckling_moment_rolled: slenderness deve ser finito e "
            f"positivo, recebido: {slenderness!r}"
        )
    return 0.69 * elastic_modulus / slenderness**2 * compressed_side_section_modulus


def flange_local_buckling_moment_welded(
    elastic_modulus: float,
    flange_local_buckling_coefficient: float,
    compressed_side_section_modulus: float,
    slenderness: float,
) -> float:
    """Momento fletor crítico de FLM para perfis SOLDADOS, ``Mcr``
    (NBR 8800:2024, D.2.8-f): ``Mcr = 0,90·E·kc/λ² · Wc``.

    ``flange_local_buckling_coefficient``: ``kc`` — ver
    :func:`flange_local_buckling_coefficient_welded`.
    ``compressed_side_section_modulus``/``slenderness``: ver
    :func:`flange_local_buckling_moment_rolled`.
    """
    if not is_positive_finite(elastic_modulus):
        raise ValueError(
            f"flange_local_buckling_moment_welded: elastic_modulus deve ser finito "
            f"e positivo, recebido: {elastic_modulus!r}"
        )
    if not is_positive_finite(flange_local_buckling_coefficient):
        raise ValueError(
            f"flange_local_buckling_moment_welded: flange_local_buckling_coefficient "
            f"deve ser finito e positivo, recebido: {flange_local_buckling_coefficient!r}"
        )
    if not is_positive_finite(compressed_side_section_modulus):
        raise ValueError(
            f"flange_local_buckling_moment_welded: compressed_side_section_modulus "
            f"deve ser finito e positivo, recebido: {compressed_side_section_modulus!r}"
        )
    if not is_positive_finite(slenderness):
        raise ValueError(
            f"flange_local_buckling_moment_welded: slenderness deve ser finito e "
            f"positivo, recebido: {slenderness!r}"
        )
    return (
        0.90
        * elastic_modulus
        * flange_local_buckling_coefficient
        / slenderness**2
        * compressed_side_section_modulus
    )


def check_flexural_resistance_major_axis(
    msd: float,
    fy: float,
    elastic_modulus: float,
    elastic_section_modulus: float,
    plastic_section_modulus: float,
    minor_axis_moment_of_inertia: float,
    torsion_constant: float,
    warping_constant: float,
    radius_of_gyration_minor_axis: float,
    unbraced_length: float,
    cb: float,
    flange_width: float,
    flange_thickness: float,
    web_clear_height: float,
    web_thickness: float,
    rolled: bool,
    gamma_a1: float,
) -> FlexureCheckResult:
    """Verifica o momento fletor resistente de cálculo COMPLETO
    (FLT+FLM+FLA) de uma barra I/H/U duplamente simétrica fletida no
    eixo maior.

    NBR 8800:2024, 5.4.1.3/5.4.2.1/5.4.2.2 e Anexo D, Tabela D.1
    (primeira linha): ``Mrd = min(Mrd_FLT, Mrd_FLM, Mrd_FLA)``, com o
    limite adicional de 5.4.2.2 (``Mrd <= 1,50·W·fy/γa1``) aplicado ao
    resultado.

    **Precondição de aplicabilidade (D.1.2)**: esta função SÓ é válida
    para vigas de alma NÃO esbelta (``h/tw <= 5,70·sqrt(E/fy)``) — se a
    alma for esbelta, TODO o Anexo D deixa de se aplicar (não apenas
    FLA) e a verificação deveria ser feita pelo Anexo E (não
    implementado); esta função levanta ``ValueError`` nesse caso, ver
    ATENÇÃO no docstring do módulo.

    Convenção de eixos: ver docstring de
    :func:`check_lateral_torsional_buckling` — os parâmetros de FLT
    (``minor_axis_moment_of_inertia``, ``radius_of_gyration_minor_axis``)
    sempre se referem ao eixo PERPENDICULAR ao eixo de flexão.

    ``flange_width``: largura total da mesa, ``bf`` — usada em
    ``b/t=(bf/2)/tf`` (D.2.8-h). ``flange_thickness``: espessura da
    mesa, ``tf``. ``web_clear_height``/``web_thickness``: ``h``/``tw`` —
    mesma definição usada em ``shear.py``. ``rolled``: ``True`` para
    perfis LAMINADOS, ``False`` para SOLDADOS (usa ``kc`` da Tabela 4).
    ``gamma_a1``: NBR 8800:2024, 4.9.2, Tabela 3.

    Retorna
    -------
    :class:`FlexureCheckResult` com ``mrd`` = o MENOR entre FLT, FLM e
    FLA, já limitado por 5.4.2.2.
    """
    if not math.isfinite(msd):
        raise ValueError(
            f"check_flexural_resistance_major_axis: msd deve ser finito, recebido: {msd!r}"
        )
    if not is_positive_finite(fy):
        raise ValueError(
            f"check_flexural_resistance_major_axis: fy deve ser finito e positivo, "
            f"recebido: {fy!r}"
        )
    if not is_positive_finite(elastic_modulus):
        raise ValueError(
            f"check_flexural_resistance_major_axis: elastic_modulus deve ser finito "
            f"e positivo, recebido: {elastic_modulus!r}"
        )
    if not is_positive_finite(elastic_section_modulus):
        raise ValueError(
            f"check_flexural_resistance_major_axis: elastic_section_modulus deve "
            f"ser finito e positivo, recebido: {elastic_section_modulus!r}"
        )
    if not is_positive_finite(plastic_section_modulus):
        raise ValueError(
            f"check_flexural_resistance_major_axis: plastic_section_modulus deve "
            f"ser finito e positivo, recebido: {plastic_section_modulus!r}"
        )
    if plastic_section_modulus < elastic_section_modulus:
        raise ValueError(
            f"check_flexural_resistance_major_axis: plastic_section_modulus "
            f"({plastic_section_modulus!r}) não pode ser menor que "
            f"elastic_section_modulus ({elastic_section_modulus!r})"
        )
    if not is_positive_finite(flange_width):
        raise ValueError(
            f"check_flexural_resistance_major_axis: flange_width deve ser finito e "
            f"positivo, recebido: {flange_width!r}"
        )
    if not is_positive_finite(flange_thickness):
        raise ValueError(
            f"check_flexural_resistance_major_axis: flange_thickness deve ser "
            f"finito e positivo, recebido: {flange_thickness!r}"
        )
    if not is_positive_finite(web_clear_height):
        raise ValueError(
            f"check_flexural_resistance_major_axis: web_clear_height deve ser "
            f"finito e positivo, recebido: {web_clear_height!r}"
        )
    if not is_positive_finite(web_thickness):
        raise ValueError(
            f"check_flexural_resistance_major_axis: web_thickness deve ser finito e "
            f"positivo, recebido: {web_thickness!r}"
        )

    residual_stress = 0.30 * fy
    residual_moment = (fy - residual_stress) * elastic_section_modulus
    plastic_moment = fy * plastic_section_modulus

    # --- Precondição D.1.2: viga de alma não esbelta (senão, Anexo E) ---
    fla_slenderness = web_clear_height / web_thickness
    fla_slenderness_limit_r = 5.70 * math.sqrt(elastic_modulus / fy)
    if fla_slenderness > fla_slenderness_limit_r:
        raise ValueError(
            f"check_flexural_resistance_major_axis: h/tw ({fla_slenderness!r}) "
            f"excede o limite de {fla_slenderness_limit_r!r} (D.1.2) — esta é uma "
            f"viga de ALMA ESBELTA, fora do escopo do Anexo D (todas as fórmulas "
            f"deste módulo); a verificação deveria ser feita pelo Anexo E, ainda "
            f"não implementado (ver docstring do módulo)."
        )

    # --- FLT (D.2.8-a) ---
    flt_critical_moment = lateral_torsional_buckling_moment(
        cb=cb,
        elastic_modulus=elastic_modulus,
        minor_axis_moment_of_inertia=minor_axis_moment_of_inertia,
        torsion_constant=torsion_constant,
        warping_constant=warping_constant,
        unbraced_length=unbraced_length,
    )
    flt_slenderness_limit_p = 1.76 * math.sqrt(elastic_modulus / fy)
    flt_slenderness_limit_r = lateral_torsional_buckling_slenderness_limit(
        cb=cb,
        elastic_modulus=elastic_modulus,
        minor_axis_moment_of_inertia=minor_axis_moment_of_inertia,
        torsion_constant=torsion_constant,
        warping_constant=warping_constant,
        radius_of_gyration_minor_axis=radius_of_gyration_minor_axis,
        residual_moment=residual_moment,
    )
    flt_slenderness = unbraced_length / radius_of_gyration_minor_axis
    mrd_flt = flexural_resistance(
        plastic_moment=plastic_moment,
        residual_moment=residual_moment,
        critical_moment=flt_critical_moment,
        slenderness=flt_slenderness,
        slenderness_limit_p=flt_slenderness_limit_p,
        slenderness_limit_r=flt_slenderness_limit_r,
        gamma_a1=gamma_a1,
    )

    # --- FLM (D.2.8-e/f/h) ---
    fy_minus_residual_stress = fy - residual_stress
    flm_slenderness = (flange_width / 2.0) / flange_thickness
    flm_slenderness_limit_p = 0.38 * math.sqrt(elastic_modulus / fy)
    if rolled:
        flm_critical_moment = flange_local_buckling_moment_rolled(
            elastic_modulus=elastic_modulus,
            compressed_side_section_modulus=elastic_section_modulus,
            slenderness=flm_slenderness,
        )
        flm_slenderness_limit_r = 0.83 * math.sqrt(elastic_modulus / fy_minus_residual_stress)
    else:
        kc = flange_local_buckling_coefficient_welded(
            web_clear_height=web_clear_height, web_thickness=web_thickness
        )
        flm_critical_moment = flange_local_buckling_moment_welded(
            elastic_modulus=elastic_modulus,
            flange_local_buckling_coefficient=kc,
            compressed_side_section_modulus=elastic_section_modulus,
            slenderness=flm_slenderness,
        )
        flm_slenderness_limit_r = 0.95 * math.sqrt(elastic_modulus * kc / fy_minus_residual_stress)
    mrd_flm = flexural_resistance(
        plastic_moment=plastic_moment,
        residual_moment=residual_moment,
        critical_moment=flm_critical_moment,
        slenderness=flm_slenderness,
        slenderness_limit_p=flm_slenderness_limit_p,
        slenderness_limit_r=flm_slenderness_limit_r,
        gamma_a1=gamma_a1,
    )

    # --- FLA (Tabela D.1) ---
    # fla_slenderness<=fla_slenderness_limit_r já confirmado acima
    # (D.1.2) -> o terceiro ramo (flambagem elástica, Anexo E) nunca é
    # selecionado aqui; fla_residual_moment (=fy*W<=fy*Z=plastic_moment,
    # já que Z>=W foi validado acima) serve também de placeholder
    # válido para critical_moment (nunca de fato usado, mas exigido
    # pela assinatura genérica de flexural_resistance()).
    fla_residual_moment = fy * elastic_section_modulus
    fla_slenderness_limit_p = 3.76 * math.sqrt(elastic_modulus / fy)
    mrd_fla = flexural_resistance(
        plastic_moment=plastic_moment,
        residual_moment=fla_residual_moment,
        critical_moment=fla_residual_moment,
        slenderness=fla_slenderness,
        slenderness_limit_p=fla_slenderness_limit_p,
        slenderness_limit_r=fla_slenderness_limit_r,
        gamma_a1=gamma_a1,
    )

    mrd = min(mrd_flt, mrd_flm, mrd_fla)
    # 5.4.2.2: limite para garantir validade da análise elástica.
    mrd = min(mrd, 1.50 * elastic_section_modulus * fy / gamma_a1)
    return FlexureCheckResult(msd=msd, mrd=mrd)
