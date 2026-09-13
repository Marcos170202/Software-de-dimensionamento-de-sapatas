"""Bases de pilares.

Fonte: ABNT NBR 8800:2024, 6.7 "Bases de pilares" (páginas 100-109) e
6.6.5 "Apoios de concreto" (página 99, pressão de contato da placa de
base sobre o bloco de concreto — prerequisito consumido apenas aqui).
Fórmulas conferidas por leitura direta (renderização visual) do PDF da
norma — ver rastreabilidade completa em
``docs/normative/NBR8800-RULES.md``.

Escopo desta fase: ligação de pilares de perfil I ou H de aço à
fundação de concreto armado por meio de placa de base retangular e
chumbadores (barras redondas rosqueadas), **APENAS o Caso C1** (6.7.1.4
— força axial de COMPRESSÃO concêntrica, sem momento fletor, o caso
mais comum), para os dois tipos de base da Figura 21 (chumbadores
externos — Tipo 1 — ou internos — Tipo 2). Cobre:

- 6.6.5 — tensão de compressão resistente de cálculo do apoio sobre o
  bloco de concreto, ``σc,Rd = min(0,85·fck/γc·sqrt(A2/A1), 1,7·fck/γc)``;
- 6.7.2.1 — grandezas geométricas ``ℓx``, ``ℓy``, ``m``, ``n``, ``n0``,
  ``X``, ``λ`` (método das linhas de escoamento/"yield line", igual em
  espírito ao AISC Design Guide 1);
- 6.7.2.2-a — Caso C1 (``e=0``): espessura mínima da placa de base
  ``tp,min``, tensão de contato solicitante ``σc,Sd`` e força cortante
  resistente de cálculo por atrito, ``VRd`` (limitada por
  ``τc,Rd·ℓx·ℓy``).

**ATENÇÃO — LIMITAÇÕES DE SEGURANÇA IMPORTANTES**:

1. **Apenas Caso C1 (compressão concêntrica, ``e=0``)**: os Casos C2 e
   C3 (compressão com excentricidade pequena/grande — 6.7.2.2-b/c) e os
   Casos T1, T2 e T3 (força axial de TRAÇÃO — 6.7.2.2-d/e/f) NÃO estão
   implementados. Uma ligação com momento fletor atuante (mesmo
   pequeno) ou com força axial de tração exige as fórmulas desses
   casos, não as deste módulo — usar :func:`check_column_base_case_c1`
   fora do Caso C1 é INCORRETO (a própria fórmula de ``tp,min`` muda de
   forma).
2. **Dispositivos de cisalhamento (6.7.2.4/6.7.2.5) NÃO implementados**:
   quando ``VSd > VRd`` (força cortante resistente por atrito
   insuficiente), a norma exige placa de cisalhamento ou arruelas
   especiais soldadas — nenhum dos dois métodos está implementado;
   :func:`check_column_base_case_c1` apenas reporta que a condição não
   é atendida.
3. **Tabela 18 (disposições construtivas) NÃO validada**: dimensões de
   chumbadores/arruelas especiais, armadura mínima do bloco e demais
   disposições construtivas da Tabela 18 NÃO são verificadas por
   nenhuma função aqui.
4. **Solda pilar-placa NÃO verificada por este módulo**: 6.7.1.3
   observa que "a solda de ligação do pilar à placa de base é
   dimensionada conforme esta Norma" — usar
   :mod:`~estrutura_metalica.normative.nbr8800.welds` separadamente.
5. **Bases tubulares fora do escopo**: 6.7.1.1 remete à ABNT NBR 16239
   para bases de pilares tubulares — não coberto (este módulo cobre
   apenas perfis I/H, conforme o próprio escopo de 6.7).
6. **γc — apenas para este módulo**:
   :func:`~estrutura_metalica.normative.nbr8800.resistance_factors.concrete_resistance_factor`
   foi adicionado exclusivamente para uso aqui — NÃO implica suporte a
   elementos mistos de aço e concreto (Seções 7/8), fora do escopo
   deste pacote.

Também NÃO implementado nesta fase (ver
``docs/normative/NBR8800-RULES.md`` para a lista completa): 6.6.1 a
6.6.4 (pressão de contato em superfícies usinadas/não usinadas e
aparelhos de apoio cilíndricos — apenas 6.6.5 está implementado, por
ser o único prerequisito de 6.7 consumido neste pacote); ``ℓ0``
(6.7.2.1, usado apenas pelos Casos T1/T2 de base Tipo 2, fora do
escopo); ``p``/``τc,Rd`` como insumos de ``ℓmax`` no ramo ``ℓc<m`` dos
Casos C2/C3 (não aplicável ao Caso C1, onde ``ℓc`` não existe).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ._validation import is_positive_finite

#: Fator de conversão MPa -> Pa, usado apenas para o limite fixo de
#: 4 MPa em :func:`concrete_grout_shear_friction_limit` (6.6.1, nota
#: b, referenciada por 6.7.2.1).
_MPA_TO_PA = 1.0e6


def concrete_bearing_resistance(
    loaded_area: float, concrete_area: float, fck: float, gamma_c: float
) -> float:
    """Tensão de compressão resistente de cálculo do apoio da placa de
    base sobre o bloco de concreto, ``σc,Rd`` (NBR 8800:2024, 6.6.5):

    ``σc,Rd = min(0,85·(fck/γc)·sqrt(A2/A1), 1,7·fck/γc)``.

    Aplicável quando a superfície de concreto se estende além da placa
    de apoio com contorno homotético em relação à área carregada
    (6.6.5-a) — ver Figura 20. O caso 6.6.5-b (contornos não
    homotéticos, ``A2`` calculada conforme a Figura 20) usa a MESMA
    fórmula, apenas com ``A2`` determinada de outra forma pelo
    chamador.

    ``loaded_area``: área carregada sob a placa de apoio, ``A1`` (m²).
    ``concrete_area``: área da superfície de concreto, ``A2`` (m²) —
    deve ser ``>= A1``. ``fck``: resistência característica à
    compressão do concreto (Pa). ``gamma_c``: NBR 8800:2024, 4.9.2,
    Tabela 3, coluna "Concreto" — ver
    :func:`~estrutura_metalica.normative.nbr8800.resistance_factors.concrete_resistance_factor`.
    """
    if not is_positive_finite(loaded_area):
        raise ValueError(
            f"concrete_bearing_resistance: loaded_area deve ser finito e "
            f"positivo, recebido: {loaded_area!r}"
        )
    if not is_positive_finite(concrete_area):
        raise ValueError(
            f"concrete_bearing_resistance: concrete_area deve ser finito e "
            f"positivo, recebido: {concrete_area!r}"
        )
    if concrete_area < loaded_area:
        raise ValueError(
            f"concrete_bearing_resistance: concrete_area ({concrete_area!r}) não "
            f"pode ser menor que loaded_area ({loaded_area!r})"
        )
    if not is_positive_finite(fck):
        raise ValueError(
            f"concrete_bearing_resistance: fck deve ser finito e positivo, recebido: {fck!r}"
        )
    if not is_positive_finite(gamma_c):
        raise ValueError(
            f"concrete_bearing_resistance: gamma_c deve ser finito e positivo, "
            f"recebido: {gamma_c!r}"
        )
    fck_gamma_c = fck / gamma_c
    return min(0.85 * fck_gamma_c * math.sqrt(concrete_area / loaded_area), 1.7 * fck_gamma_c)


def column_base_effective_length_x(column_depth: float, edge_distance: float) -> float:
    """Dimensão efetiva da placa de base na direção ``x``, ``ℓx`` (NBR
    8800:2024, 6.7.2.1): ``ℓx = d + 4·a1``.

    ``column_depth``: altura do perfil I/H do pilar, ``d`` (m).
    ``edge_distance``: distância da linha de chumbadores mais externa
    ao eixo da placa, ``a1`` (m, ver Figuras 21 a 23).
    """
    if not is_positive_finite(column_depth):
        raise ValueError(
            f"column_base_effective_length_x: column_depth deve ser finito e "
            f"positivo, recebido: {column_depth!r}"
        )
    if not is_positive_finite(edge_distance):
        raise ValueError(
            f"column_base_effective_length_x: edge_distance deve ser finito e "
            f"positivo, recebido: {edge_distance!r}"
        )
    return column_depth + 4.0 * edge_distance


def column_base_effective_length_y(
    num_anchors: int, edge_distance: float, anchor_spacing: float, flange_width: float
) -> float:
    """Dimensão efetiva da placa de base na direção ``y``, ``ℓy`` (NBR
    8800:2024, 6.7.2.1):
    ``ℓy = max((0,5·nb − 1)·a2 + 2·a1, bf + 25 mm)``.

    ``num_anchors``: número de chumbadores da ligação, ``nb`` (entre 4
    e 8, para base Tipo 1; igual a 4, para base Tipo 2 — não validado
    aqui, ver ATENÇÃO no docstring do módulo). ``edge_distance``:
    ``a1`` (m). ``anchor_spacing``: espaçamento entre linhas de
    chumbadores, ``a2`` (m). ``flange_width``: largura da mesa do
    perfil do pilar, ``bf`` (m).
    """
    if num_anchors < 4:
        raise ValueError(
            f"column_base_effective_length_y: num_anchors deve ser >= 4, "
            f"recebido: {num_anchors!r}"
        )
    if not is_positive_finite(edge_distance):
        raise ValueError(
            f"column_base_effective_length_y: edge_distance deve ser finito e "
            f"positivo, recebido: {edge_distance!r}"
        )
    if not is_positive_finite(anchor_spacing):
        raise ValueError(
            f"column_base_effective_length_y: anchor_spacing deve ser finito e "
            f"positivo, recebido: {anchor_spacing!r}"
        )
    if not is_positive_finite(flange_width):
        raise ValueError(
            f"column_base_effective_length_y: flange_width deve ser finito e "
            f"positivo, recebido: {flange_width!r}"
        )
    from_anchors = (0.5 * num_anchors - 1.0) * anchor_spacing + 2.0 * edge_distance
    return max(from_anchors, flange_width + 0.025)


def column_base_yield_line_m(lx: float, column_depth: float) -> float:
    """Parâmetro geométrico ``m`` do método das linhas de escoamento
    (NBR 8800:2024, 6.7.2.1): ``m = (ℓx − 0,95·d)/2``.
    """
    if not is_positive_finite(lx):
        raise ValueError(
            f"column_base_yield_line_m: lx deve ser finito e positivo, recebido: {lx!r}"
        )
    if not is_positive_finite(column_depth):
        raise ValueError(
            f"column_base_yield_line_m: column_depth deve ser finito e "
            f"positivo, recebido: {column_depth!r}"
        )
    return (lx - 0.95 * column_depth) / 2.0


def column_base_yield_line_n(ly: float, flange_width: float) -> float:
    """Parâmetro geométrico ``n`` do método das linhas de escoamento
    (NBR 8800:2024, 6.7.2.1): ``n = (ℓy − 0,80·bf)/2``.
    """
    if not is_positive_finite(ly):
        raise ValueError(
            f"column_base_yield_line_n: ly deve ser finito e positivo, recebido: {ly!r}"
        )
    if not is_positive_finite(flange_width):
        raise ValueError(
            f"column_base_yield_line_n: flange_width deve ser finito e "
            f"positivo, recebido: {flange_width!r}"
        )
    return (ly - 0.80 * flange_width) / 2.0


def column_base_yield_line_n0(column_depth: float, flange_width: float) -> float:
    """Parâmetro geométrico ``n0`` do método das linhas de escoamento
    (NBR 8800:2024, 6.7.2.1): ``n0 = sqrt(d·bf)/4``.
    """
    if not is_positive_finite(column_depth):
        raise ValueError(
            f"column_base_yield_line_n0: column_depth deve ser finito e "
            f"positivo, recebido: {column_depth!r}"
        )
    if not is_positive_finite(flange_width):
        raise ValueError(
            f"column_base_yield_line_n0: flange_width deve ser finito e "
            f"positivo, recebido: {flange_width!r}"
        )
    return math.sqrt(column_depth * flange_width) / 4.0


def column_base_x_parameter(
    column_depth: float, flange_width: float, nsd: float, lx: float, ly: float, sigma_c_rd: float
) -> float:
    """Parâmetro adimensional ``X`` do método das linhas de escoamento
    (NBR 8800:2024, 6.7.2.1):

    ``X = [4·d·bf/(d+bf)²]·Nsd/(ℓx·ℓy·σc,Rd)``.

    Levanta ``ValueError`` se ``X > 1`` — a fórmula de ``λ`` (ver
    :func:`column_base_lambda`) exige ``X <= 1``; ``X > 1`` indica que
    a tensão de contato solicitante já excede ``σc,Rd`` na área
    ``ℓx·ℓy`` — a ligação (geometria da placa) deve ser alterada.

    ``nsd``: força axial de compressão solicitante de cálculo, ``NSd``
    (N, positiva). ``sigma_c_rd``: ``σc,Rd`` — ver
    :func:`concrete_bearing_resistance`.
    """
    if not is_positive_finite(column_depth):
        raise ValueError(
            f"column_base_x_parameter: column_depth deve ser finito e "
            f"positivo, recebido: {column_depth!r}"
        )
    if not is_positive_finite(flange_width):
        raise ValueError(
            f"column_base_x_parameter: flange_width deve ser finito e "
            f"positivo, recebido: {flange_width!r}"
        )
    if not is_positive_finite(nsd):
        raise ValueError(
            f"column_base_x_parameter: nsd deve ser finito e positivo, recebido: {nsd!r}"
        )
    if not is_positive_finite(lx):
        raise ValueError(
            f"column_base_x_parameter: lx deve ser finito e positivo, recebido: {lx!r}"
        )
    if not is_positive_finite(ly):
        raise ValueError(
            f"column_base_x_parameter: ly deve ser finito e positivo, recebido: {ly!r}"
        )
    if not is_positive_finite(sigma_c_rd):
        raise ValueError(
            f"column_base_x_parameter: sigma_c_rd deve ser finito e positivo, "
            f"recebido: {sigma_c_rd!r}"
        )
    shape_factor = 4.0 * column_depth * flange_width / (column_depth + flange_width) ** 2
    x = shape_factor * nsd / (lx * ly * sigma_c_rd)
    if x > 1.0:
        raise ValueError(
            f"column_base_x_parameter: X ({x!r}) > 1 — a tensão de contato "
            f"solicitante excede sigma_c_rd na área lx*ly; aumentar a placa de base"
        )
    return x


def column_base_lambda(x: float) -> float:
    """Parâmetro ``λ`` do método das linhas de escoamento (NBR
    8800:2024, 6.7.2.1): ``λ = 2·sqrt(X)/(1+sqrt(1−X)) <= 1,0``.

    ``x``: ``X`` — ver :func:`column_base_x_parameter` (``0 < X <= 1``).
    """
    if not (0.0 < x <= 1.0):
        raise ValueError(f"column_base_lambda: x deve satisfazer 0 < x <= 1, recebido: {x!r}")
    return min(2.0 * math.sqrt(x) / (1.0 + math.sqrt(1.0 - x)), 1.0)


def column_base_plate_effective_length_c1(m: float, n: float, lambda_: float, n0: float) -> float:
    """Comprimento efetivo governante da placa de base para o Caso C1,
    ``ℓmax`` (NBR 8800:2024, 6.7.2.2-a): ``ℓmax = max(m, n, λ·n0)``.

    Aplicável somente ao Caso C1 (``e=0``) — os Casos C2/C3 têm uma
    definição de ``ℓmax`` diferente e condicional a ``ℓc`` vs. ``m``
    (fora do escopo, ver ATENÇÃO no docstring do módulo).
    """
    if not is_positive_finite(m):
        raise ValueError(
            f"column_base_plate_effective_length_c1: m deve ser finito e "
            f"positivo, recebido: {m!r}"
        )
    if not is_positive_finite(n):
        raise ValueError(
            f"column_base_plate_effective_length_c1: n deve ser finito e "
            f"positivo, recebido: {n!r}"
        )
    if not is_positive_finite(lambda_):
        raise ValueError(
            f"column_base_plate_effective_length_c1: lambda_ deve ser finito "
            f"e positivo, recebido: {lambda_!r}"
        )
    if not is_positive_finite(n0):
        raise ValueError(
            f"column_base_plate_effective_length_c1: n0 deve ser finito e "
            f"positivo, recebido: {n0!r}"
        )
    return max(m, n, lambda_ * n0)


def column_base_concrete_bearing_stress(nsd: float, lx: float, ly: float) -> float:
    """Tensão de compressão solicitante de cálculo sob a placa de
    base, ``σc,Sd`` (NBR 8800:2024, 6.7.2.2-a, Caso C1):
    ``σc,Sd = Nsd/(ℓx·ℓy)``.
    """
    if not is_positive_finite(nsd):
        raise ValueError(
            f"column_base_concrete_bearing_stress: nsd deve ser finito e "
            f"positivo, recebido: {nsd!r}"
        )
    if not is_positive_finite(lx):
        raise ValueError(
            f"column_base_concrete_bearing_stress: lx deve ser finito e "
            f"positivo, recebido: {lx!r}"
        )
    if not is_positive_finite(ly):
        raise ValueError(
            f"column_base_concrete_bearing_stress: ly deve ser finito e "
            f"positivo, recebido: {ly!r}"
        )
    return nsd / (lx * ly)


def column_base_plate_min_thickness_case_c1(
    l_max: float, sigma_c_sd: float, fy: float, gamma_a1: float
) -> float:
    """Espessura mínima da placa de base, ``tp,min``, Caso C1 (NBR
    8800:2024, 6.7.2.2-a): ``tp,min = ℓmax·sqrt(2·σc,Sd/(fy/γa1))``.

    ``l_max``: ``ℓmax`` — ver :func:`column_base_plate_effective_length_c1`.
    ``sigma_c_sd``: ``σc,Sd`` — ver :func:`column_base_concrete_bearing_stress`.
    ``fy``: resistência ao escoamento da placa de base.
    """
    if not is_positive_finite(l_max):
        raise ValueError(
            f"column_base_plate_min_thickness_case_c1: l_max deve ser finito "
            f"e positivo, recebido: {l_max!r}"
        )
    if not is_positive_finite(sigma_c_sd):
        raise ValueError(
            f"column_base_plate_min_thickness_case_c1: sigma_c_sd deve ser "
            f"finito e positivo, recebido: {sigma_c_sd!r}"
        )
    if not is_positive_finite(fy):
        raise ValueError(
            f"column_base_plate_min_thickness_case_c1: fy deve ser finito e "
            f"positivo, recebido: {fy!r}"
        )
    if not is_positive_finite(gamma_a1):
        raise ValueError(
            f"column_base_plate_min_thickness_case_c1: gamma_a1 deve ser "
            f"finito e positivo, recebido: {gamma_a1!r}"
        )
    return l_max * math.sqrt(2.0 * sigma_c_sd / (fy / gamma_a1))


def concrete_grout_shear_friction_limit(fck: float, gamma_c: float) -> float:
    """Limite de tensão de cisalhamento resistente de cálculo entre a
    placa de base e a argamassa/concreto, ``τc,Rd`` (NBR 8800:2024,
    6.7.2.2-a, referenciando o mesmo limite de 6.6.1):
    ``τc,Rd = min(0,2·fck/γc, 4 MPa)``.
    """
    if not is_positive_finite(fck):
        raise ValueError(
            f"concrete_grout_shear_friction_limit: fck deve ser finito e "
            f"positivo, recebido: {fck!r}"
        )
    if not is_positive_finite(gamma_c):
        raise ValueError(
            f"concrete_grout_shear_friction_limit: gamma_c deve ser finito e "
            f"positivo, recebido: {gamma_c!r}"
        )
    return min(0.2 * fck / gamma_c, 4.0 * _MPA_TO_PA)


def column_base_friction_shear_resistance(
    friction_coefficient: float,
    sigma_c_sd: float,
    lx: float,
    ly: float,
    gamma_a2: float,
    tau_c_rd: float,
) -> float:
    """Força cortante resistente de cálculo por atrito na base do
    pilar, ``VRd``, Caso C1 (NBR 8800:2024, 6.7.2.2-a):
    ``VRd = min(μ·σc,Sd·ℓx·ℓy/γa2, τc,Rd·ℓx·ℓy)``.

    ``friction_coefficient``: coeficiente de atrito entre a placa de
    base e a argamassa expansiva de assentamento, ``μ`` — a norma
    permite considerá-lo igual a 0,45. ``sigma_c_sd``: ``σc,Sd`` — ver
    :func:`column_base_concrete_bearing_stress`. ``tau_c_rd``:
    ``τc,Rd`` — ver :func:`concrete_grout_shear_friction_limit`.
    """
    if not is_positive_finite(friction_coefficient):
        raise ValueError(
            f"column_base_friction_shear_resistance: friction_coefficient "
            f"deve ser finito e positivo, recebido: {friction_coefficient!r}"
        )
    if not is_positive_finite(sigma_c_sd):
        raise ValueError(
            f"column_base_friction_shear_resistance: sigma_c_sd deve ser "
            f"finito e positivo, recebido: {sigma_c_sd!r}"
        )
    if not is_positive_finite(lx):
        raise ValueError(
            f"column_base_friction_shear_resistance: lx deve ser finito e "
            f"positivo, recebido: {lx!r}"
        )
    if not is_positive_finite(ly):
        raise ValueError(
            f"column_base_friction_shear_resistance: ly deve ser finito e "
            f"positivo, recebido: {ly!r}"
        )
    if not is_positive_finite(gamma_a2):
        raise ValueError(
            f"column_base_friction_shear_resistance: gamma_a2 deve ser "
            f"finito e positivo, recebido: {gamma_a2!r}"
        )
    if not is_positive_finite(tau_c_rd):
        raise ValueError(
            f"column_base_friction_shear_resistance: tau_c_rd deve ser "
            f"finito e positivo, recebido: {tau_c_rd!r}"
        )
    friction_term = friction_coefficient * sigma_c_sd * lx * ly / gamma_a2
    ceiling_term = tau_c_rd * lx * ly
    return min(friction_term, ceiling_term)


@dataclass(frozen=True, slots=True)
class ColumnBaseCheckResult:
    """Resultado de uma verificação isolada (espessura da placa, tensão
    de contato OU cisalhamento por atrito) de uma base de pilar, Caso
    C1 (NBR 8800:2024, 6.7.1.5).

    ``demand``: grandeza solicitante (ou mínima exigida, no caso da
    espessura — ``tp,min``). ``capacity``: grandeza resistente (ou
    fornecida, no caso da espessura — ``tp`` instalada). A condição
    normativa é atendida se ``demand <= capacity`` (``is_ok``).
    """

    demand: float
    capacity: float

    def __post_init__(self) -> None:
        if not is_positive_finite(self.demand):
            raise ValueError(f"demand deve ser finito e positivo, recebido: {self.demand!r}")
        if not is_positive_finite(self.capacity):
            raise ValueError(f"capacity deve ser finito e positivo, recebido: {self.capacity!r}")

    @property
    def is_ok(self) -> bool:
        return self.demand <= self.capacity

    @property
    def utilization(self) -> float:
        return self.demand / self.capacity


@dataclass(frozen=True, slots=True)
class ColumnBaseCaseC1Result:
    """Resultado completo (dentro do escopo desta fase) da verificação
    de uma base de pilar sob compressão concêntrica, Caso C1 (NBR
    8800:2024, 6.7.1.5-a/d/e).

    ``thickness``: ``tp >= tp,min`` (item a). ``bearing``:
    ``σc,Sd <= σc,Rd`` (item d). ``shear``: ``VSd <= VRd`` (item e).
    Item b (chumbadores tracionados) não se aplica ao Caso C1 (sem
    tração nos chumbadores); item c (materiais/disposições
    construtivas da Tabela 18) não é verificado — ver ATENÇÃO no
    docstring do módulo.
    """

    thickness: ColumnBaseCheckResult
    bearing: ColumnBaseCheckResult
    shear: ColumnBaseCheckResult

    @property
    def is_ok(self) -> bool:
        return self.thickness.is_ok and self.bearing.is_ok and self.shear.is_ok


def check_column_base_case_c1(
    nsd: float,
    vsd: float,
    provided_thickness: float,
    column_depth: float,
    flange_width: float,
    edge_distance: float,
    anchor_spacing: float,
    num_anchors: int,
    fy: float,
    fck: float,
    loaded_area: float,
    concrete_area: float,
    friction_coefficient: float,
    gamma_a1: float,
    gamma_a2: float,
    gamma_c: float,
) -> ColumnBaseCaseC1Result:
    """Verifica uma base de pilar de perfil I/H sob força axial de
    compressão CONCÊNTRICA (Caso C1, ``e=0`` — NBR 8800:2024, 6.7.1.4/
    6.7.2.2-a).

    Ver ATENÇÃO no docstring do módulo: cobre apenas o Caso C1 —
    momento fletor atuante (mesmo pequeno) ou força axial de tração
    exigem os Casos C2/C3/T1/T2/T3, não implementados. Não verifica a
    solda pilar-placa (ver módulo ``welds``) nem dispositivos de
    cisalhamento quando ``VSd > VRd`` (6.7.2.4/6.7.2.5, não
    implementados) — apenas reporta a condição.

    ``nsd``: força axial de compressão solicitante de cálculo, ``NSd``
    (N, positiva). ``vsd``: força cortante solicitante de cálculo na
    base, ``VSd`` (N). ``provided_thickness``: espessura da placa de
    base efetivamente adotada, ``tp`` (m). ``column_depth``/
    ``flange_width``: ``d``/``bf`` do perfil do pilar (m).
    ``edge_distance``/``anchor_spacing``: ``a1``/``a2`` (m, Figura 21).
    ``num_anchors``: ``nb`` (ver :func:`column_base_effective_length_y`).
    ``fy``: resistência ao escoamento da placa de base. ``fck``:
    resistência característica à compressão do concreto.
    ``loaded_area``/``concrete_area``: ``A1``/``A2`` (m², 6.6.5, Figura
    20). ``friction_coefficient``: ``μ`` (6.7.2.2-a — a norma permite
    considerá-lo igual a 0,45). ``gamma_a1``/``gamma_a2``: NBR
    8800:2024, Tabela 3, coluna "Aço estrutural". ``gamma_c``: Tabela
    3, coluna "Concreto" — ver
    :func:`~estrutura_metalica.normative.nbr8800.resistance_factors.concrete_resistance_factor`.
    """
    if not is_positive_finite(vsd):
        raise ValueError(
            f"check_column_base_case_c1: vsd deve ser finito e positivo, recebido: {vsd!r}"
        )
    if not is_positive_finite(provided_thickness):
        raise ValueError(
            f"check_column_base_case_c1: provided_thickness deve ser finito "
            f"e positivo, recebido: {provided_thickness!r}"
        )

    lx = column_base_effective_length_x(column_depth, edge_distance)
    ly = column_base_effective_length_y(num_anchors, edge_distance, anchor_spacing, flange_width)
    m = column_base_yield_line_m(lx, column_depth)
    n = column_base_yield_line_n(ly, flange_width)
    n0 = column_base_yield_line_n0(column_depth, flange_width)

    sigma_c_rd = concrete_bearing_resistance(loaded_area, concrete_area, fck, gamma_c)
    x = column_base_x_parameter(column_depth, flange_width, nsd, lx, ly, sigma_c_rd)
    lambda_ = column_base_lambda(x)
    l_max = column_base_plate_effective_length_c1(m, n, lambda_, n0)

    sigma_c_sd = column_base_concrete_bearing_stress(nsd, lx, ly)
    tp_min = column_base_plate_min_thickness_case_c1(l_max, sigma_c_sd, fy, gamma_a1)

    tau_c_rd = concrete_grout_shear_friction_limit(fck, gamma_c)
    v_rd = column_base_friction_shear_resistance(
        friction_coefficient, sigma_c_sd, lx, ly, gamma_a2, tau_c_rd
    )

    return ColumnBaseCaseC1Result(
        thickness=ColumnBaseCheckResult(demand=tp_min, capacity=provided_thickness),
        bearing=ColumnBaseCheckResult(demand=sigma_c_sd, capacity=sigma_c_rd),
        shear=ColumnBaseCheckResult(demand=vsd, capacity=v_rd),
    )
