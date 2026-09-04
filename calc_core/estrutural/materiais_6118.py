"""Leis constitutivas do ELU — concreto (8.2.10.1) e aço passivo (8.3.5/8.3.6).

Ref.: ABNT NBR 6118:2023, item 8.2.10.1, Figura 8.2 e parágrafo seguinte, p. 26
[rule: NBR6118-8.2.10.1-diagrama-idealizado-do-concreto]

Ref.: ABNT NBR 6118:2023, itens 8.3.5 e 8.3.6, Figura 8.5, p. 29-30
[rule: NBR6118-8.3.5-8.3.6-aco-passivo]

Ref.: ABNT NBR 6118:2023, itens 12.3.1, 12.3.3-a, 12.4 e Tabela 12.1, p. 70-71
[rule: NBR6118-12.3.3-12.4.1-valores-de-calculo]

[req: REQ-PILARETE-01-modulo-novo-e-fronteira-de-dependencia]
[req: REQ-PILARETE-06-NRd0-e-a-recusa-de-veredito-de-ELU]

DOIS LIMIARES DE CLASSE, NÃO UM — e é a correção de premissa mais importante
deste módulo (``observacao`` de NBR6118-8.2.10.1-...):

* ``eta_c`` muda em **f_ck = 40 MPa**;
* ``n_diagrama``, ``eps_c2`` e ``eps_cu`` mudam em **C50/C55**.

Um ``if fck <= 50: 0.85 else ...`` sem ``eta_c`` é DEFEITO COM VETO: erra em
SILÊNCIO na faixa 40 < f_ck <= 50, onde eta_c já é menor que 1 (0,9283 em C50)
enquanto n ainda é 2. O terceiro limiar (C60, parâmetro ``s`` de beta_1 na
Emenda 1:2026) pertence a j < 28 dias, que é RECUSADO por
:func:`exigir_idade_28_dias`.

REUSO, NÃO REIMPLEMENTAÇÃO: ``f_cd``, ``f_yd``, ``f_ct,m``, ``f_ctk,inf`` e
``f_ctd`` saem de ``calc_core/sapata_isolada/materiais.py`` (``Concreto`` e
``Aco``, Seção 8 já conferida item a item). Este módulo acrescenta só o que
não existe lá: os parâmetros do diagrama parábola-retângulo, o patamar, e o
diagrama do aço até 10 ‰.
"""
from __future__ import annotations

import math

from calc_core.estrutural.dominio import (
    DECLARADO_EM_TEXTO,
    DECLARADO_PELO_USUARIO,
    RecusaForaDeDominio,
)
from calc_core.sapata_isolada.materiais import Aco, Concreto

__all__ = [
    "CLASSES_NORMALIZADAS",
    "E_S_MPA",
    "EPS_S_MAXIMO",
    "TOLERANCIA_RELATIVA_DE_EPS_S",
    "eta_c",
    "n_diagrama",
    "eps_c2",
    "eps_cu",
    "sigma_c",
    "sigma_s",
    "f_cd",
    "f_yd",
    "exigir_classe_normalizada",
    "exigir_idade_28_dias",
    "gamma_c_com_correcao_12_4_1",
]

CLASSES_NORMALIZADAS: tuple[float, ...] = (
    20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0,
    55.0, 60.0, 65.0, 70.0, 75.0, 80.0, 85.0, 90.0,
)
"""Classes de resistência normalizadas admitidas, C20 a C90.

Ref.: ABNT NBR 6118:2023, item 8.2.10.1, p. 26
[rule: NBR6118-8.2.10.1-diagrama-idealizado-do-concreto]

LACUNA DE DOMÍNIO DECIDIDA PELO a2: a Norma escreve eta_c e n por f_ck
CONTÍNUO (40 MPa, 50 MPa) e eps_c2/eps_cu por CLASSE ("até C50", "C55 até
C90"). Para um f_ck não normalizado entre 50 e 55 os dois critérios divergem.
Só classes normalizadas são aceitas; f_ck fora da lista é RECUSA, nunca
interpolação (REQ-PILARETE-06-A).
"""

E_S_MPA = 210_000.0
"""Módulo de elasticidade do aço passivo [MPa].

Ref.: ABNT NBR 6118:2023, item 8.3.5, p. 29
[rule: NBR6118-8.3.5-8.3.6-aco-passivo]

210 GPa "na falta de ensaio ou de valor fornecido pelo fabricante" — valor
SUPLETIVO. NÃO confundir com os 200 GPa de 8.4.4, que são de armadura ATIVA.
"""

EPS_S_MAXIMO = 10.0e-3
"""Alongamento máximo convencional do ELU (polo A da Figura 17.1).

Ref.: ABNT NBR 6118:2023, item 17.2.2, alínea g), Figura 17.1, p. 122
[rule: NBR6118-17.2.2-fig17.1-limites-dos-dominios]
[deriv: DER-NBR6118-8.3.6-sigma-s-ate-10-por-mil]

O valor 10 ‰ está no RÓTULO DA FIGURA, não no texto corrido — rótulo de
figura da NBR 6118 é vetorizado e fora do alcance de qualquer busca textual.
É ele que neutraliza, por escopo, a lacuna de eps_su (que a Norma não
quantifica em lugar nenhum).
"""


TOLERANCIA_RELATIVA_DE_EPS_S = 1.0e-9
"""Tolerância de PONTO FLUTUANTE sobre a igualdade eps_s = 10 ‰ [adimensional].

Ref.: ABNT NBR 6118:2023, item 17.2.2, alínea g) e Figura 17.1, p. 122
[rule: NBR6118-17.2.2-fig17.1-limites-dos-dominios]

NÃO É UMA FAIXA DE TOLERÂNCIA SOBRE O LIMITE NORMATIVO, e a distinção
importa porque este projeto proíbe inventar faixas (REQ-PILARETE-11 e -18).
O polo A da Figura 17.1 produz eps_s = −10 ‰ na armadura mais tracionada
POR CONSTRUÇÃO, isto é, por uma igualdade exata; ao reconstruí-la a partir
de (y_p, D) o resultado sai como −10 ‰ ± 1e-19. Sem esta tolerância, o
domínio 2 inteiro seria recusado por erro de arredondamento. 1e-9 relativo
equivale a 1e-11 de deformação absoluta — dez ordens de grandeza abaixo de
qualquer significado físico, e seis abaixo do último dígito que a Norma
escreve.
"""


def exigir_classe_normalizada(f_ck_MPa: float) -> float:
    """Aceita apenas C20 a C90 normalizadas; RECUSA qualquer outro f_ck.

    Ref.: ABNT NBR 6118:2023, item 8.2.10.1, p. 26
    [rule: NBR6118-8.2.10.1-diagrama-idealizado-do-concreto]
    [req: REQ-PILARETE-06-NRd0-e-a-recusa-de-veredito-de-ELU]

    Motivo em ``CLASSES_NORMALIZADAS``: entre 50 e 55 MPa os dois critérios
    de classe da Norma divergem, e interpolar seria inventar lei
    constitutiva.
    """
    if f_ck_MPa not in CLASSES_NORMALIZADAS:
        raise RecusaForaDeDominio(
            parametro="f_ck_MPa",
            valor=f_ck_MPa,
            intervalo="classe normalizada, uma de "
                      + ", ".join(f"C{int(c)}" for c in CLASSES_NORMALIZADAS),
            fonte="ABNT NBR 6118:2023, 8.2.10.1, p. 26 — eta_c e n são dados "
                  "por f_ck contínuo, mas eps_c2 e eps_cu por CLASSE; entre "
                  "50 e 55 MPa os dois critérios divergem",
            forca=DECLARADO_EM_TEXTO,
            apoio_no_ruleset="NBR6118-8.2.10.1-diagrama-idealizado-do-concreto",
            sugestao="Informe uma classe normalizada. É PROIBIDO interpolar a "
                     "lei constitutiva entre classes.",
        )
    return f_ck_MPa


def exigir_idade_28_dias(idade_maior_ou_igual_28_dias: bool | None) -> bool:
    """Exige declaração de que a verificação é em idade j >= 28 dias.

    Ref.: ABNT NBR 6118:2023, itens 12.3.3-a e 12.3.3-b, p. 70
    [rule: NBR6118-12.3.3-12.4.1-valores-de-calculo]
    [req: REQ-PILARETE-06-NRd0-e-a-recusa-de-veredito-de-ELU]  (alínea D)

    A alínea b) de 12.3.3 (j < 28 dias, com beta_1 e o parâmetro ``s``) está
    FORA do escopo desta versão: é ela que exige o terceiro limiar de classe
    (C60) trazido pela Emenda 1:2026 e a dupla verificação (aos t dias e aos
    28). NÃO é hipótese acadêmica — pilarete recém-concretado recebendo base
    metálica e equipamento é o caso real.
    """
    if idade_maior_ou_igual_28_dias is not True:
        raise RecusaForaDeDominio(
            parametro="idade_maior_ou_igual_28_dias",
            valor=idade_maior_ou_igual_28_dias,
            intervalo="declaração explícita True (j >= 28 dias)",
            fonte="ABNT NBR 6118:2023, 12.3.3, alíneas a) e b), p. 70",
            forca=DECLARADO_PELO_USUARIO,
            apoio_no_ruleset="NBR6118-12.3.3-12.4.1-valores-de-calculo",
            sugestao="A verificação em j < 28 dias exige beta_1 de 12.3.3-b) e "
                     "a dupla verificação (aos t dias e aos 28), fora do "
                     "escopo desta versão. Declare j >= 28 dias ou verifique "
                     "fora deste software.",
        )
    return True


def gamma_c_com_correcao_12_4_1(
    gamma_c_base: float,
    condicoes_desfavoraveis_de_execucao: bool | None,
) -> float:
    """gamma_c da Tabela 12.1, com a correção × 1,1 de 12.4.1 quando aplicável.

    Ref.: ABNT NBR 6118:2023, item 12.4.1 e Tabela 12.1, p. 71
    [rule: NBR6118-12.3.3-12.4.1-valores-de-calculo]
    [req: REQ-PILARETE-02-entradas-explicitas-e-recusa-por-ausencia]  (h)

    A correção é OBRIGATÓRIA ("deve ser multiplicado") quando previstas
    condições desfavoráveis de execução — e "concretagem deficiente por
    concentração de armadura" é caso plausível num pilarete de seção pequena
    com 100 % das barras emendadas na mesma seção. O software PERGUNTA; não
    infere e não assume 1,4. A ausência da resposta é RECUSA, não ``False``.
    """
    if condicoes_desfavoraveis_de_execucao is None:
        raise RecusaForaDeDominio(
            parametro="condicoes_desfavoraveis_de_execucao",
            valor=None,
            intervalo="declaração explícita True/False",
            fonte="ABNT NBR 6118:2023, 12.4.1, p. 71 — 'deve ser multiplicado "
                  "por 1,1' quando previstas condições desfavoráveis",
            forca=DECLARADO_PELO_USUARIO,
            apoio_no_ruleset="NBR6118-12.3.3-12.4.1-valores-de-calculo",
            sugestao="Um pilarete de seção pequena com 100 % das barras "
                     "emendadas na mesma seção é candidato natural a "
                     "'concentração de armadura'. Responda explicitamente.",
        )
    return gamma_c_base * 1.1 if condicoes_desfavoraveis_de_execucao else gamma_c_base


def eta_c(f_ck_MPa: float) -> float:
    """Fator de redução eta_c do diagrama idealizado [adimensional].

    Ref.: ABNT NBR 6118:2023, item 8.2.10.1, Figura 8.2, p. 26
    [rule: NBR6118-8.2.10.1-diagrama-idealizado-do-concreto]

        eta_c = 1,0                para f_ck <= 40 MPa
        eta_c = (40/f_ck)^(1/3)    para f_ck  > 40 MPa

    LIMIAR 40 MPa, não 50. eta_c NÃO existia na NBR 6118:2014; qualquer
    memória de treinamento que escreva sigma_c = 0,85·f_cd·[...] está
    desatualizada acima de C40.
    """
    exigir_classe_normalizada(f_ck_MPa)
    if f_ck_MPa <= 40.0:
        return 1.0
    return (40.0 / f_ck_MPa) ** (1.0 / 3.0)


def n_diagrama(f_ck_MPa: float) -> float:
    """Expoente ``n`` da parábola do diagrama idealizado [adimensional].

    Ref.: ABNT NBR 6118:2023, item 8.2.10.1, Figura 8.2, p. 26
    [rule: NBR6118-8.2.10.1-diagrama-idealizado-do-concreto]

        n = 2                                para f_ck <= 50 MPa
        n = 1,4 + 23,4·[(90 − f_ck)/100]^4   para f_ck  > 50 MPa

    Nome ``n_diagrama`` e não ``n``: ``n`` sozinho é ilegível a três linhas
    de distância e colide com contadores de laço.
    """
    exigir_classe_normalizada(f_ck_MPa)
    if f_ck_MPa <= 50.0:
        return 2.0
    return 1.4 + 23.4 * ((90.0 - f_ck_MPa) / 100.0) ** 4


def eps_c2(f_ck_MPa: float) -> float:
    """Deformação no início do patamar plástico [adimensional].

    Ref.: ABNT NBR 6118:2023, item 8.2.10.1, parágrafo após a Figura 8.2, p. 26
    [rule: NBR6118-8.2.10.1-diagrama-idealizado-do-concreto]

        eps_c2 = 2,0 ‰                            até C50
        eps_c2 = 2,0 ‰ + 0,085 ‰·(f_ck − 50)^0,53  de C55 a C90

    Devolvido em valor ABSOLUTO (2,0 ‰ = 0.002), nunca em ‰: a razão
    eps_c/eps_c2 é adimensional nos dois casos e um fator 1000 misturado NÃO
    é detectável por análise dimensional (``checagem_dimensional`` da regra).
    """
    exigir_classe_normalizada(f_ck_MPa)
    if f_ck_MPa <= 50.0:
        return 2.0e-3
    return 2.0e-3 + 0.085e-3 * (f_ck_MPa - 50.0) ** 0.53


def eps_cu(f_ck_MPa: float) -> float:
    """Deformação de encurtamento na ruptura [adimensional].

    Ref.: ABNT NBR 6118:2023, item 8.2.10.1, parágrafo após a Figura 8.2, p. 26
    [rule: NBR6118-8.2.10.1-diagrama-idealizado-do-concreto]

        eps_cu = 3,5 ‰                              até C50
        eps_cu = 2,6 ‰ + 35 ‰·[(90 − f_ck)/100]^4    de C55 a C90

    Acima de C55 eps_cu CAI (3,5 -> 2,6 ‰) enquanto eps_c2 SOBE: as duas
    convergem. Se a transcrição tivesse trocado as expressões, essa
    convergência não apareceria — é a contra-prova interna da leitura.

    A Norma escreve ``eps_cu``, NÃO ``eps_cu2``: o índice "2" é nomenclatura
    do Eurocode e não deve ser introduzido no código.
    """
    exigir_classe_normalizada(f_ck_MPa)
    if f_ck_MPa <= 50.0:
        return 3.5e-3
    return 2.6e-3 + 35.0e-3 * ((90.0 - f_ck_MPa) / 100.0) ** 4


def sigma_c(eps_c: float, concreto: Concreto) -> float:
    """Tensão de compressão do concreto no ELU [MPa], COM o patamar.

    Ref.: ABNT NBR 6118:2023, item 8.2.10.1, Figura 8.2, p. 26
    [rule: NBR6118-8.2.10.1-diagrama-idealizado-do-concreto]

        sigma_c = 0,85·eta_c·f_cd·[1 − (1 − eps_c/eps_c2)^n]   0 <= eps_c <= eps_c2
        sigma_c = 0,85·eta_c·f_cd            (CONSTANTE)       eps_c2 < eps_c <= eps_cu
        sigma_c = 0                                            eps_c <= 0

    ARMADILHA DE IMPLEMENTAÇÃO REGISTRADA (REQ-PILARETE-06-B): a expressão da
    Figura 8.2 vale SÓ no ramo curvo. De eps_c2 a eps_cu a tensão é constante,
    e isso está no DESENHO, não na fórmula — avaliar a expressão acima de
    eps_c2 não reproduz o patamar e pode até DECRESCER (com n = 2 e
    eps_c = 2·eps_c2 a expressão devolve zero).

    Tração do concreto DESPREZADA (17.2.2, alínea d): eps_c <= 0 devolve 0.

    ``eps_c`` é ADIMENSIONAL (2,0 ‰ = 0.002), com compressão POSITIVA.
    """
    f_ck_MPa = concreto.fck
    exigir_classe_normalizada(f_ck_MPa)
    if eps_c <= 0.0:
        return 0.0
    pico = 0.85 * eta_c(f_ck_MPa) * concreto.fcd
    eps_2 = eps_c2(f_ck_MPa)
    eps_u = eps_cu(f_ck_MPa)
    if eps_c > eps_u:
        raise RecusaForaDeDominio(
            parametro="eps_c",
            valor=eps_c,
            intervalo=f"0 a eps_cu = {eps_u:.6f}",
            fonte="ABNT NBR 6118:2023, 8.2.10.1, p. 26 — o diagrama termina "
                  "em eps_cu; acima disso a Norma não declara tensão alguma",
            forca=DECLARADO_EM_TEXTO,
            apoio_no_ruleset="NBR6118-8.2.10.1-diagrama-idealizado-do-concreto",
        )
    if eps_c >= eps_2:
        return pico
    return pico * (1.0 - (1.0 - eps_c / eps_2) ** n_diagrama(f_ck_MPa))


def sigma_s(eps_s: float, aco: Aco) -> float:
    """Tensão no aço passivo [MPa], tração e compressão, até |eps_s| <= 10 ‰.

    Ref.: ABNT NBR 6118:2023, itens 8.3.5 e 8.3.6, Figura 8.5, p. 29-30
    [rule: NBR6118-8.3.5-8.3.6-aco-passivo]
    [deriv: DER-NBR6118-8.3.6-sigma-s-ate-10-por-mil]
    [deriv: DER-NBR6118-12.3.1-fyd]

        sigma_s(eps_s) = sinal(eps_s)·min(E_s·|eps_s| , f_yd)

    A Norma NÃO escreve equação alguma em 8.3.6: a Figura 8.5 é só desenho —
    ramo reto de inclinação arctg(E_s) e patamar em f_yd, sem eps_yd rotulado
    e sem valor para eps_su. Converter o desenho em código é DERIVAÇÃO, e é
    por isso que a docstring cita ``[deriv: ]`` e não só ``[rule: ]``.

    O diagrama é aplicável À COMPRESSÃO pela autorização expressa do parágrafo
    de continuação da p. 30 ("pode ser aplicado para tração e compressão") —
    é ela que legitima usá-lo na armadura comprimida do pilarete.

    RECUSA acima de 10 ‰, e não por conservadorismo: eps_su NÃO TEM VALOR NA
    NORMA, logo não existe base para dizer o que acontece com o aço além do
    limite convencional do ELU. Dentro dos domínios da Figura 17.1 o ponto de
    trabalho nunca sai desse intervalo, então a recusa só dispara se a
    varredura sair do domínio aprovado.

    ``eps_yd`` NÃO entra em conta nenhuma aqui: ``min(E_s·eps, f_yd)`` não
    precisa saber onde fica o joelho. Ele serve só para NOMEAR o domínio no
    memorial (domínio 3 se eps_s >= eps_yd, domínio 4 se menor).
    """
    if abs(eps_s) > EPS_S_MAXIMO * (1.0 + TOLERANCIA_RELATIVA_DE_EPS_S):
        raise RecusaForaDeDominio(
            parametro="eps_s",
            valor=eps_s,
            intervalo=f"|eps_s| <= {EPS_S_MAXIMO} (10 por mil)",
            fonte="ABNT NBR 6118:2023, 17.2.2-g) e Figura 17.1, p. 122 — polo "
                  "A fixa o alongamento máximo convencional do ELU em 10 ‰; "
                  "eps_su não tem valor em item algum da Norma",
            forca=DECLARADO_EM_TEXTO,
            apoio_no_ruleset="DER-NBR6118-8.3.6-sigma-s-ate-10-por-mil",
            sugestao="Fora do domínio aprovado do diagrama do aço. O software "
                     "RECUSA em vez de extrapolar o patamar.",
        )
    return math.copysign(min(aco.Es * abs(eps_s), aco.fyd), eps_s)


def f_cd(concreto: Concreto) -> float:
    """Resistência de cálculo do concreto à compressão [MPa].

    Ref.: ABNT NBR 6118:2023, itens 12.3.1, 12.3.3-a e Tabela 12.1, p. 70-71
    [rule: NBR6118-12.3.3-12.4.1-valores-de-calculo]

        f_cd = f_ck / gamma_c

    Envelope fino sobre ``Concreto.fcd`` (``sapata_isolada/materiais.py``, §8
    já conferida): existe para dar ao pilarete o NOME que REQ-PILARETE-01
    fixa e para que a rastreabilidade do memorial aponte para 12.3.3, e não
    para reimplementar a divisão. ``gamma_c`` é ENTRADA do objeto ``Concreto``,
    nunca constante fechada — a correção × 1,1 de 12.4.1 entra por
    :func:`gamma_c_com_correcao_12_4_1`.
    """
    return concreto.fcd


def f_yd(aco: Aco) -> float:
    """Resistência de cálculo do aço ao escoamento [MPa].

    Ref.: ABNT NBR 6118:2023, item 12.3.1 e Tabela 12.1 (12.4.1), p. 70-71
    [deriv: DER-NBR6118-12.3.1-fyd]

        f_yd = f_yk / gamma_s

    Citado como DERIVAÇÃO, e não como transcrição, por um motivo registrado:
    a Norma NÃO escreve "f_yd = f_yk/1,15" em item algum. Ela escreve a regra
    geral f_d = f_k/gamma_m em 12.3.1 e tabela gamma_s = 1,15 na Tabela 12.1;
    ``f_yd`` só aparece como rótulo de eixo na Figura 8.5. É o tipo de coisa
    que a memória do modelo escreveria como se fosse texto normativo.
    """
    return aco.fyd
