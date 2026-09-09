"""Dimensionamento geométrico de sapata isolada sob carga centrada.

Ref.: ABNT NBR 6122:2022, item 7.6.1, p. 23
"""
from __future__ import annotations

import math

from calc_core.geotecnico.restricoes import verificar_dimensao_minima
from calc_core.modelos import EntradaSapataCentrada, ResultadoGeometria, Verificacao


def _arredondar_para_cima(valor: float, modulo: float) -> float:
    """Arredonda para o próximo múltiplo de ``modulo``, sempre para cima.

    Sapata menor que a área calculada nunca é uma opção construtiva válida
    aqui — arredondar para baixo violaria sigma_atuante <= sigma_adm.
    """
    passos = math.ceil(round(valor / modulo, 9))
    return round(passos * modulo, 10)


def _dimensoes_para_area(area_necessaria: float, pilar_a: float,
                          pilar_b: float) -> tuple[float, float]:
    """Resolve B e L mantendo a mesma folga ``c`` nas quatro bordas do pilar.

    NÃO é texto da NBR 6122 — a norma (7.6.1) só exige tensão uniforme
    <= tensão admissível, sem prescrever como repartir B e L. Manter a folga
    igual nos quatro lados (B = pilar_a + 2c, L = pilar_b + 2c) é prática
    consagrada de escritório (Alonso, Bowles) porque minimiza o momento
    fletor na sapata quando a carga é de fato centrada. Registrado como
    decisão de implementação em ruleset.yaml (NBR6122-7.6.1-area-carga-
    centrada, campo `observacao`), não como regra normativa.

    (pilar_a + 2c)(pilar_b + 2c) = area_necessaria
    4c² + 2(pilar_a + pilar_b)c + (pilar_a*pilar_b - area_necessaria) = 0
    """
    a, b = pilar_a, pilar_b
    soma = a + b
    termo_independente = a * b - area_necessaria
    discriminante = soma * soma - 4 * termo_independente
    # discriminante > 0 sempre que area_necessaria > 0, pois
    # termo_independente = a*b - area_necessaria < a*b <= (soma/2)^2 em geral;
    # mesmo no caso extremo, area_necessaria > 0 garante raiz real positiva.
    c = (-soma + math.sqrt(discriminante)) / 4
    return a + 2 * c, b + 2 * c


def dimensionar_sapata_carga_centrada(
    entrada: EntradaSapataCentrada,
) -> ResultadoGeometria:
    """Dimensiona B e L de uma sapata isolada sob carga vertical centrada.

    Ref.: ABNT NBR 6122:2022, item 7.6.1, p. 23
    [rule: NBR6122-7.6.1-area-carga-centrada]

    "A área da fundação solicitada por cargas centradas deve ser tal que as
    tensões transmitidas ao terreno, admitidas uniformemente distribuídas,
    satisfaçam aos requisitos de segurança conforme Seção 6."

    Também aplica, se ``entrada.considerar_peso_proprio`` for True:

    Ref.: ABNT NBR 6122:2022, item 5.6, p. 14
    [rule: NBR6122-5.6-peso-proprio-minimo]

    "Deve ser considerado o peso próprio de blocos de coroamento ou
    sapatas, ou no mínimo 5 % da carga vertical permanente." — usado aqui
    como piso normativo para pré-dimensionamento, não como peso próprio
    real (que só se conhece depois de a sapata estar detalhada).

    Domínio de validade: carga vertical SEM excentricidade (sem momento).
    Para carga excêntrica, ver NBR6122-7.6.2-area-comprimida — regra ainda
    ``PENDENTE_HUMANO`` em ruleset.yaml, não implementada.

    Parameters
    ----------
    entrada:
        Ver :class:`calc_core.modelos.EntradaSapataCentrada`.

    Returns
    -------
    ResultadoGeometria
        B, L, tensão atuante e verificações normativas aplicadas.
    """
    if entrada.considerar_peso_proprio:
        N_total = entrada.N_k * (1 + entrada.percentual_peso_proprio)
    else:
        N_total = entrada.N_k

    area_necessaria = N_total / entrada.sigma_adm

    B_bruto, L_bruto = _dimensoes_para_area(
        area_necessaria, entrada.pilar_a, entrada.pilar_b
    )

    B = _arredondar_para_cima(B_bruto, entrada.modulo_arredondamento)
    L = _arredondar_para_cima(L_bruto, entrada.modulo_arredondamento)

    # NBR 6122:2022 §7.7.1 é uma exigência, não uma preferência: se a área
    # de tensão admissível resultar em B ou L abaixo do mínimo (carga leve
    # em terreno bom), o software IMPÕE o mínimo em vez de só sinalizar
    # falha — bumping aumenta a área e portanto só reduz sigma_atuante,
    # nunca viola NBR6122-7.6.1-area-carga-centrada.
    B = max(B, entrada.dimensao_minima)
    L = max(L, entrada.dimensao_minima)

    area_final = B * L
    tensao_atuante = N_total / area_final

    verificacao_tensao = Verificacao(
        regra="NBR6122-7.6.1-area-carga-centrada",
        descricao="Tensão uniforme atuante <= tensão admissível",
        aplicavel=True,
        ok=tensao_atuante <= entrada.sigma_adm,
        mensagem=(
            f"sigma_atuante = {tensao_atuante:.1f} kPa "
            f"{'<=' if tensao_atuante <= entrada.sigma_adm else '>'} "
            f"sigma_adm = {entrada.sigma_adm:.1f} kPa"
        ),
    )
    verificacao_dimensao = verificar_dimensao_minima(
        B, L, entrada.dimensao_minima
    )

    return ResultadoGeometria(
        N_total=N_total,
        area_necessaria=area_necessaria,
        B=B,
        L=L,
        area_final=area_final,
        tensao_atuante=tensao_atuante,
        verificacoes=[verificacao_tensao, verificacao_dimensao],
    )
