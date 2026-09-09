"""ELU de FORÇA CORTANTE do pilarete — §17.4, Modelos I e II.

Ref.: ABNT NBR 6118:2023, itens 17.4 e 17.4.1, p. 133
[rule: NBR6118-17.4.1-campo-de-aplicacao-do-cortante]

Ref.: ABNT NBR 6118:2023, item 17.4.2.1, p. 136
[rule: NBR6118-17.4.2.1-duas-condicoes-simultaneas-do-ELU-de-cortante]

Ref.: ABNT NBR 6118:2023, item 17.4.2.2, p. 136-138
[rule: NBR6118-17.4.2.2-modelo-I-VRd2-Vsw-Vc]

Ref.: ABNT NBR 6118:2023, item 17.4.2.3, p. 138-139
[rule: NBR6118-17.4.2.3-modelo-II-theta-arbitrado]

Ref.: ABNT NBR 6118:2023, item 17.4.1.1.1, p. 134
[rule: NBR6118-17.4.1.1.1-armadura-transversal-minima-por-resistencia]

Ref.: ABNT NBR 6118:2023, item 17.4.1.1.2, alíneas a) e c), p. 134
[rule: NBR6118-17.4.1.1.2-c-excecao-dos-pilares-e-o-f-ctk-sem-sufixo]

Ref.: ABNT NBR 6118:2023, itens 17.4.1.1.5 e 17.4.1.1.6, p. 135
[rule: NBR6118-17.4.1.1.5-17.4.1.1.6-intervalo-de-alpha-e-remissao-a-secao-18]

[rule: NBR6118-17.4.1.2.1-reducoes-junto-aos-apoios]  (REJEITADA — NÃO usada)
[rule: NBR6118-17.4.2.2-c-17.4.2.3-c-decalagem]        (REJEITADA — NÃO usada)
[rule: NBR6118-DELIMITACAO-17.4-vs-19.4-19.5]
[deriv: DER-NBR6118-17.4.2.2-M0-nivel-de-carregamento]
[deriv: DER-NBR6118-17.4.2.2-W1-fibra-mais-tracionada]
[deriv: DER-NBR6118-17.4.2.3-Vc1-interpolacao-linear]
[req: REQ-PILARETE-18-verificacao-de-forca-cortante]

DUAS AUSÊNCIAS DELIBERADAS, e é obrigatório que sejam visíveis:

* **reduções junto aos apoios (17.4.1.2.1)** — REJEITADA por falta de
  domínio, não por conveniência. São FACULTATIVAS, valem só em apoio DIRETO,
  só para a armadura transversal, e a própria Norma as PROÍBE em V_Rd2. Elas
  REDUZEM V_Sd; ler o engaste de um pilarete na sapata como "apoio direto"
  seria interpretação sobre um item cujo efeito é ALIVIAR a solicitação.
  Consequência: V_Sd entra INTEGRAL, o que é conservador.
* **decalagem (17.4.2.2-c / 17.4.2.3-c)** — REJEITADA por incompatibilidade
  de modelo: a decalagem opera sobre um DIAGRAMA de força no banzo tracionado
  ao longo de um vão, e o pilarete tem armadura longitudinal SIMÉTRICA
  dimensionada por flexão composta oblíqua. Encontrar ``a_l`` ou ``F_Sd,cor``
  neste pacote é VETO do a6.

INTERAÇÃO N-V — É EXATAMENTE UMA, E SÓ ELA: a majoração de V_c pela
compressão, do passo (4). NÃO há efeito de N sobre V_Rd2 (a biela). É
PROIBIDO introduzir qualquer outra por analogia, e é PROIBIDO transportar
para cá a DISPENSA de interação da PUNÇÃO (19.5.2.7), que diz o oposto e vale
para laje.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from calc_core.estrutural.dominio import (
    DECLARADO_EM_TEXTO,
    ESCOPO_DESTA_VERSAO,
    NAO_DECLARADO_NA_FONTE,
    RecusaForaDeDominio,
    exigir_declarado,
    exigir_intervalo,
    exigir_positivo,
    exigir_um_de,
)
from calc_core.estrutural.pilarete.classificacao import (
    ResultadoClassificacao,
    recusar_cortante_na_faixa_B,
)
from calc_core.sapata_isolada.materiais import Aco, Concreto

__all__ = [
    "MODELO_I",
    "MODELO_II",
    "MODELOS_DE_CALCULO",
    "ALPHA_ESTRIBO_DESTA_VERSAO",
    "TETO_F_YWD_MPA",
    "PLANO_DE_H",
    "PLANO_DE_B",
    "ESTADO_TRACIONADO_LN_FORA",
    "ESTADO_FLEXAO_SIMPLES_OU_FLEXO_TRACAO",
    "ESTADO_FLEXO_COMPRESSAO",
    "alpha_v2",
    "f_ywd",
    "V_Rd2",
    "V_sw",
    "V_c0",
    "V_c1",
    "rho_sw_min",
    "taxa_rho_sw_adotada",
    "M_0_e_fibra_governante",
    "classificar_estado_da_secao",
    "dispensa_17_4_1_1_2_c",
    "PlanoDeCortante",
    "plano_de_verificacao",
    "ResultadoCortante",
    "verificar",
]

MODELO_I = "MODELO_I"
"""Modelo de cálculo I (17.4.2.2): diagonais a 45°, theta_biela FIXO."""

MODELO_II = "MODELO_II"
"""Modelo de cálculo II (17.4.2.3): theta_biela ARBITRADO pelo projetista."""

MODELOS_DE_CALCULO: tuple[str, ...] = (MODELO_I, MODELO_II)
"""Enumeração FECHADA. A Norma apresenta os dois SEM critério de escolha."""

ALPHA_ESTRIBO_DESTA_VERSAO = 90.0
"""Única inclinação de armadura transversal aceita nesta versão [graus].

Ref.: ABNT NBR 6118:2023, item 17.4.1.1.5, p. 135
[rule: NBR6118-17.4.1.1.5-17.4.1.1.6-intervalo-de-alpha-e-remissao-a-secao-18]

A NORMA admite 45° <= alpha_estribo <= 90°. A restrição a 90° é ESCOPO DESTE
SOFTWARE, não da Norma, e a mensagem de recusa cita o escopo — nunca a Norma.
Motivo: (a) 90° é o lado conservador em V_sw do Modelo I (sen+cos vale 1 a
90° e 1,414 a 45°); (b) 18.4.3 detalha pilar com estribo transversal, não
inclinado; (c) o caminho com sen/cos não trivial ficaria sem nenhum caso de
validação. A expressão GERAL é implementada inteira mesmo assim, para que a
ampliação futura não exija reescrevê-la, e é exercitada por teste de
propriedade em 45° — teste de álgebra, não caminho certificado.

NOME COMPLETO OBRIGATÓRIO: ``alpha_estribo`` é a inclinação da ARMADURA;
``theta_biela`` é a da BIELA. Os dois aparecem na MESMA expressão e um
``theta`` nu é PROIBIDO (REQ-PILARETE-01).
"""

TETO_F_YWD_MPA = 435.0
"""Teto absoluto de f_ywd para estribos [MPa].

Ref.: ABNT NBR 6118:2023, item 17.4.2.2, alínea b), p. 137
[rule: NBR6118-17.4.2.2-modelo-I-VRd2-Vsw-Vc]

"f_ywd <= f_yd para estribos e NUNCA superior a 435 MPa". O teto GOVERNA
CA-60 (f_yd = 521,7 MPa) e NÃO governa CA-50 (434,8 MPa) — implementá-lo é
obrigatório de qualquer modo; omiti-lo é erro do lado INSEGURO.

É PROIBIDO aplicar aqui os tetos de f_ywd de 19.4.2 (250 MPa até 15 cm de
espessura, 435 MPa acima de 35 cm, com interpolação linear): aqueles são de
LAJE, e o do pilarete é este, sem interpolação por espessura
([rule: NBR6118-DELIMITACAO-17.4-vs-19.4-19.5], item 5).
"""

PLANO_DE_H = "PLANO_DE_H"
"""V_Sd atua no plano de h_secao: b_w = b_secao e d medido ao longo de h."""

PLANO_DE_B = "PLANO_DE_B"
"""V_Sd atua no plano de b_secao: b_w = h_secao e d medido ao longo de b."""

ESTADO_TRACIONADO_LN_FORA = "TRACIONADO_COM_LN_FORA_DA_SECAO"
ESTADO_FLEXAO_SIMPLES_OU_FLEXO_TRACAO = "FLEXAO_SIMPLES_OU_FLEXO_TRACAO_LN_CORTANDO"
ESTADO_FLEXO_COMPRESSAO = "FLEXO_COMPRESSAO"

DECLARACAO_F_CTK_SEM_SUFIXO = (
    "A NBR 6118:2023, 17.4.1.1.2-c) (p. 134), escreve \"f_ctk\" SEM sufixo; "
    "8.2.5 (p. 23) define apenas f_ctk,inf = 0,7·f_ct,m e f_ctk,sup = "
    "1,3·f_ct,m, que diferem em 86 %. Este software adota f_ctk,inf, o mais "
    "restritivo — interpretação declarada, NÃO transcrição. Com f_ctk,sup a "
    "dispensa da armadura mínima seria 86 % mais fácil de obter, e o pilarete "
    "deixaria de ser armado onde a leitura conservadora manda armar."
)
"""Declaração LITERAL obrigatória no memorial (decisão V20(1) do a2)."""

DECLARACAO_PREDOMINANTEMENTE_A_COMPRESSAO = (
    "\"Predominantemente à compressão\", em 17.4.1.1.2-c), NÃO é quantificado "
    "pela NBR 6118:2023 em lugar nenhum de §17.4 — NAO_DECLARADO_NA_FONTE. "
    "Enquanto não houver decisão humana, este software só aplica a dispensa "
    "quando a força normal for de COMPRESSÃO em todas as combinações "
    "verificadas; em qualquer outro caso, NÃO dispensa (lado conservador)."
)

AUSENCIAS_DELIBERADAS = (
    "As reduções de V_Sd junto aos apoios (NBR 6118:2023, 17.4.1.2.1, p. 135) "
    "NÃO foram aplicadas: são facultativas, valem só em apoio direto, só para "
    "a armadura transversal, e a Norma as proíbe em V_Rd2 — aplicá-las ao "
    "engaste do pilarete seria interpretação sobre um item que ALIVIA a "
    "solicitação. V_Sd entra integral, o que é conservador.",
    "A decalagem do diagrama de força no banzo tracionado (NBR 6118:2023, "
    "17.4.2.2-c) e 17.4.2.3-c), p. 138-139) NÃO foi calculada: ela pressupõe "
    "armadura longitudinal determinada por equilíbrio em seção normal ao eixo "
    "e um diagrama de momentos de vão; o pilarete tem armadura simétrica "
    "dimensionada por flexão composta oblíqua e não tem banzo tracionado de "
    "vão.",
)
"""As duas ausências que o memorial declara na FAIXA A (REQ-PILARETE-12-q)."""


def alpha_v2(f_ck_MPa: float) -> float:
    """Fator de efetividade da biela comprimida [adimensional].

    Ref.: ABNT NBR 6118:2023, itens 17.4.2.2-a) e 17.4.2.3-a), p. 136 e 138
    [rule: NBR6118-17.4.2.2-modelo-I-VRd2-Vsw-Vc]
    [rule: NBR6118-DELIMITACAO-17.4-vs-19.4-19.5]

        alpha_v2 = 1 − f_ck/250,  com **f_ck OBRIGATORIAMENTE EM MPa**

    GUARDA DE UNIDADE, e é o erro clássico deste item: na MESMA expressão de
    V_Rd2 convivem ``alpha_v2`` (que exige f_ck em MPa, porque o 250 carrega
    MPa) e ``f_cd`` (que tem de estar na unidade coerente com b_w·d). Misturar
    as duas produz número plausível. Daí o sufixo ``_MPa`` no parâmetro.

    NOME ``alpha_v2``, com o "2", e a distinção NÃO é cosmética: 19.5.3.1
    (punção de laje) usa ``alpha_v`` com definição IDÊNTICA, e esse símbolo já
    existe em ``sapata_isolada/materiais.py``. O número coincide
    (0,900 em C25); a GRANDEZA em que ele entra, não — lá é TENSÃO em
    contorno crítico, aqui é FORÇA em b_w·d. Reaproveitar o símbolo é defeito
    de RASTREABILIDADE mesmo sem mudar número nenhum: o memorial passaria a
    citar o item errado. É PROIBIDO um ``alpha_v`` neste pacote e um
    ``alpha_v2`` em ``sapata_isolada/``.
    """
    exigir_intervalo("f_ck_MPa", f_ck_MPa, 20.0, 90.0,
                     fonte="ABNT NBR 6118:2023, 17.4.2.2-a), p. 136",
                     forca=DECLARADO_EM_TEXTO,
                     apoio_no_ruleset="NBR6118-17.4.2.2-modelo-I-VRd2-Vsw-Vc")
    return 1.0 - f_ck_MPa / 250.0


def f_ywd(aco_do_estribo: Aco) -> float:
    """Resistência de cálculo do estribo [MPa], com o TETO de 435 MPa.

    Ref.: ABNT NBR 6118:2023, item 17.4.2.2, alínea b), p. 137
    [rule: NBR6118-17.4.2.2-modelo-I-VRd2-Vsw-Vc]
    [deriv: DER-NBR6118-12.3.1-fyd]

        f_ywd = min(f_yd , 435 MPa)

    O teto governa CA-60 (521,7 -> 435 MPa) e não governa CA-50 (434,8 MPa).
    É essa assimetria que torna o teste obrigatório: um caso em CA-60 tem de
    usar 435 MPa, e a mutação que remova o teto tem de quebrar esse caso e
    NÃO pode quebrar nenhum em CA-50.

    CA-60 é RECUSADO como armadura LONGITUDINAL por 18.4.3 (k_phi não
    declarado). Aqui trata-se da armadura TRANSVERSAL, e o teto se aplica
    normalmente.
    """
    return min(aco_do_estribo.fyd, TETO_F_YWD_MPA)


def V_Rd2(*, modelo_de_calculo: str, f_ck_MPa: float, f_cd_MPa: float,
          b_w_no_plano_do_cortante: float, d_util_no_plano_do_cortante: float,
          alpha_estribo_graus: float, theta_biela_graus: float | None) -> float:
    """Força cortante resistente de COMPRESSÃO DIAGONAL da biela [kN].

    Ref.: ABNT NBR 6118:2023, itens 17.4.2.2-a) e 17.4.2.3-a), p. 136 e 138
    [rule: NBR6118-17.4.2.2-modelo-I-VRd2-Vsw-Vc]
    [rule: NBR6118-17.4.2.3-modelo-II-theta-arbitrado]

        Modelo I  : V_Rd2 = 0,27·alpha_v2·f_cd·b_w·d
        Modelo II : V_Rd2 = 0,54·alpha_v2·f_cd·b_w·d·sen²(theta_biela)
                            ·(cotg alpha_estribo + cotg theta_biela)

    PROPRIEDADE DE FRONTEIRA, obrigatória como teste: em theta_biela = 45° e
    alpha_estribo = 90°, sen² = 0,5 e cotg theta = 1, logo
    V_Rd2(II) = 0,27·alpha_v2·f_cd·b_w·d = V_Rd2(I), EXATAMENTE.

    O EXPOENTE 2 SOBRE O SENO É OBRIGATÓRIO. Trocar sen²(theta) por
    sen(theta) leva o coeficiente de 0,27 para 0,382 em 45° (+41 %, lado
    INSEGURO) e passa INTEIRAMENTE pela checagem dimensional — a camada de
    texto do PDF perde o 0,54 e o intervalo inteiro, e só a leitura visual
    recupera a expressão.

    ``b_w`` é a MENOR largura da seção ao longo da altura útil, medida
    PERPENDICULARMENTE ao plano de atuação de V_Sd; ``d`` é a altura útil
    medida NO plano de V_Sd (na redação da Em1:2026, "distância da borda
    comprimida ao CENTROIDE da armadura de tração" — troca terminológica, sem
    efeito numérico). Trocar os dois de plano muda V_Rd2 e V_c0 na MESMA
    proporção e passa por toda a checagem dimensional; numa seção não
    quadrada é erro real, daí os nomes longos dos parâmetros.

    É PROIBIDO reaproveitar o coeficiente 0,27 vindo de 19.5.3.1 (tau_Rd2):
    mesmo número, item diferente, grandeza diferente, símbolo diferente.
    """
    exigir_um_de("modelo_de_calculo", modelo_de_calculo, MODELOS_DE_CALCULO,
                 fonte="ABNT NBR 6118:2023, 17.4.2, p. 136",
                 apoio_no_ruleset="NBR6118-17.4.2.1-duas-condicoes-simultaneas-"
                                  "do-ELU-de-cortante")
    fator = alpha_v2(f_ck_MPa) * f_cd_MPa * 1000.0 * b_w_no_plano_do_cortante \
        * d_util_no_plano_do_cortante
    if modelo_de_calculo == MODELO_I:
        return 0.27 * fator
    theta_rad = math.radians(float(theta_biela_graus))  # type: ignore[arg-type]
    alpha_rad = math.radians(alpha_estribo_graus)
    cotg_alpha = 0.0 if abs(alpha_estribo_graus - 90.0) < 1e-12 \
        else 1.0 / math.tan(alpha_rad)
    return (0.54 * fator * math.sin(theta_rad) ** 2
            * (cotg_alpha + 1.0 / math.tan(theta_rad)))


def V_sw(*, modelo_de_calculo: str, A_sw_por_s: float,
         d_util_no_plano_do_cortante: float, f_ywd_MPa: float,
         alpha_estribo_graus: float, theta_biela_graus: float | None) -> float:
    """Parcela resistida pela armadura transversal [kN].

    Ref.: ABNT NBR 6118:2023, itens 17.4.2.2-b) e 17.4.2.3-b), p. 137 e 139
    [rule: NBR6118-17.4.2.2-modelo-I-VRd2-Vsw-Vc]
    [rule: NBR6118-17.4.2.3-modelo-II-theta-arbitrado]

        Modelo I  : V_sw = (A_sw/s)·0,9·d·f_ywd·(sen alpha + cos alpha)
        Modelo II : V_sw = (A_sw/s)·0,9·d·f_ywd·(cotg alpha + cotg theta)·sen alpha

    O braço ``0,9·d`` é FIXO na expressão; NÃO é o ``z`` calculado da seção.

    ``A_sw_por_s`` em [m²/m] (isto é, em metros): área da armadura transversal
    por unidade de comprimento do eixo. Em 45° as duas expressões coincidem —
    (sen+cos) = 1,414 e (cotg 90 + cotg 45)·sen 90 = 1 — não, e é justamente
    aí que está a propriedade: com alpha_estribo = 90°, sen+cos = 1 e
    (0 + 1)·1 = 1, e os dois modelos dão o MESMO V_sw em theta = 45°.
    """
    exigir_um_de("modelo_de_calculo", modelo_de_calculo, MODELOS_DE_CALCULO,
                 fonte="ABNT NBR 6118:2023, 17.4.2, p. 136",
                 apoio_no_ruleset="NBR6118-17.4.2.1-duas-condicoes-simultaneas-"
                                  "do-ELU-de-cortante")
    alpha_rad = math.radians(alpha_estribo_graus)
    base = A_sw_por_s * 0.9 * d_util_no_plano_do_cortante * f_ywd_MPa * 1000.0
    if modelo_de_calculo == MODELO_I:
        return base * (math.sin(alpha_rad) + math.cos(alpha_rad))
    cotg_alpha = 0.0 if abs(alpha_estribo_graus - 90.0) < 1e-12 \
        else 1.0 / math.tan(alpha_rad)
    theta_rad = math.radians(float(theta_biela_graus))  # type: ignore[arg-type]
    return base * (cotg_alpha + 1.0 / math.tan(theta_rad)) * math.sin(alpha_rad)


def V_c0(*, concreto: Concreto, b_w_no_plano_do_cortante: float,
         d_util_no_plano_do_cortante: float) -> float:
    """Valor de referência de V_c para theta_biela = 45° [kN].

    Ref.: ABNT NBR 6118:2023, item 17.4.2.2, alínea b), p. 137
    [rule: NBR6118-17.4.2.2-modelo-I-VRd2-Vsw-Vc]

        V_c0 = 0,6·f_ctd·b_w·d,  com f_ctd = f_ctk,inf/gamma_c

    ``V_c0``, ``V_c1`` e ``V_c`` são TRÊS OBJETOS DISTINTOS, separados
    explicitamente na lista de símbolos da p. 119: ``V_c0`` é o valor de
    referência a 45°; ``V_c1`` o de 30° <= theta <= 45° (Modelo II); ``V_c`` o
    valor efetivamente usado, já com o ramo de estado e a majoração. Nomes
    completos sempre.

    CONTRAPROVA EXTERNA (FONTE SECUNDÁRIA): reconstruindo esta expressão em
    C20 com f_ct,m = 0,3·20^(2/3), o a2 obteve V_c0 = 0,06631·b_w·d, que
    combinado com rho_sw,mín de 17.4.1.1.1 e o teto de 435 MPa reproduz o
    V_Sd,mín = 0,101·b_w·d da Tabela A-4 do BASTOS. Um único número de
    terceiros amarra o 0,2 de 17.4.1.1.1, o 0,6 e o f_ctk,inf daqui, o 0,9·d
    e o teto de f_ywd.
    """
    return 0.6 * concreto.fctd * 1000.0 * b_w_no_plano_do_cortante \
        * d_util_no_plano_do_cortante


def V_c1(*, V_Sd: float, V_c0_valor: float, V_Rd2_do_modelo_II: float) -> float:
    """Valor de referência de V_c no Modelo II, por interpolação linear [kN].

    Ref.: ABNT NBR 6118:2023, item 17.4.2.3, alínea b), p. 139
    [rule: NBR6118-17.4.2.3-modelo-II-theta-arbitrado]
    [deriv: DER-NBR6118-17.4.2.3-Vc1-interpolacao-linear]

        V_c1 = V_c0                                  , se V_Sd <= V_c0
        V_c1 = V_c0·(V_Rd2 − V_Sd)/(V_Rd2 − V_c0)    , se V_c0 < V_Sd <= V_Rd2

    A Norma dá DOIS PONTOS ("V_c1 = V_c0 quando V_Sd <= V_c0; V_c1 = 0 quando
    V_Sd = V_Rd2") e a palavra "interpolando-se linearmente"; a expressão
    fechada NÃO está escrita em lugar nenhum. Escrevê-la é DERIVAÇÃO,
    declarada como tal, jamais registrada como transcrição.

    O ``V_Rd2`` da interpolação é o do MODELO II com o theta_biela DECLARADO,
    nunca o do Modelo I.

    ARMADILHA REGISTRADA, e é um erro provável: os dois modelos COINCIDEM em
    V_Rd2 e em V_sw quando theta_biela = 45°, mas NÃO coincidem em V_Rd3,
    porque V_c1 <= V_c0 sempre que V_Sd > V_c0. Um teste que exija
    V_Rd3(II) == V_Rd3(I) em 45° está ERRADO e quebra uma implementação
    correta.

    Extrapolar a reta para V_Sd > V_Rd2 é PROIBIDO: nesse caso 17.4.2.1 já
    REPROVOU e o software reprova ANTES de avaliar V_c1. Devolver V_c1
    negativo, ou truncá-lo em zero em silêncio, também é proibido — daí a
    recusa explícita abaixo.
    """
    if V_Sd <= V_c0_valor:
        return V_c0_valor
    if V_Sd > V_Rd2_do_modelo_II:
        raise RecusaForaDeDominio(
            parametro="V_Sd",
            valor=round(V_Sd, 4),
            intervalo=f"<= V_Rd2 = {V_Rd2_do_modelo_II:.4f} kN",
            fonte="ABNT NBR 6118:2023, 17.4.2.3-b), p. 139 — a interpolação de "
                  "V_c1 é definida entre V_c0 e V_Rd2; acima de V_Rd2 a "
                  "condição de 17.4.2.1 já está violada",
            forca=DECLARADO_EM_TEXTO,
            apoio_no_ruleset="DER-NBR6118-17.4.2.3-Vc1-interpolacao-linear",
            sugestao="É PROIBIDO extrapolar a reta, devolver V_c1 negativo ou "
                     "truncá-lo em zero em silêncio.",
        )
    return V_c0_valor * (V_Rd2_do_modelo_II - V_Sd) / (V_Rd2_do_modelo_II - V_c0_valor)


def rho_sw_min(*, concreto: Concreto, f_ywk_MPa: float) -> float:
    """Taxa geométrica mínima de armadura transversal por RESISTÊNCIA.

    Ref.: ABNT NBR 6118:2023, item 17.4.1.1.1, p. 134
    [rule: NBR6118-17.4.1.1.1-armadura-transversal-minima-por-resistencia]
    [rule: NBR6118-8.2.5-fctm]

        rho_sw = A_sw/(b_w·s·sen alpha_estribo) >= 0,2·f_ct,m/f_ywk

    ``f_ct,m`` de 8.2.5 e ``f_ywk`` na MESMA unidade — a razão é adimensional.

    TRÊS LEITURAS QUE A CAMADA DE TEXTO DO PDF DEVOLVE ERRADAS e que a leitura
    visual do a2 confirmou: o coeficiente é 0,2 (dois décimos, e o texto
    decodificado o parte em "0 2"); o sinal é ">=" (que aparece ANTES da
    fração no texto extraído); e ``sen alpha_estribo`` está NO DENOMINADOR.
    Pôr o seno no numerador é erro DORMENTE: com estribo vertical o número nem
    muda, e só apareceria no dia em que alguém habilitasse estribo inclinado.

    É PISO, NÃO TETO. Aplicar-lhe a regra do "menor dos limites" de 18.4.3 —
    que é para TETOS — afrouxaria a exigência: erro do lado INSEGURO. Ver
    [deriv: DER-NBR6118-composicao-18.3.3.2-com-18.4.3].
    """
    exigir_positivo("f_ywk_MPa", f_ywk_MPa,
                    fonte="ABNT NBR 6118:2023, 17.4.1.1.1, p. 134",
                    apoio_no_ruleset="NBR6118-17.4.1.1.1-armadura-transversal-"
                                     "minima-por-resistencia")
    return 0.2 * concreto.fctm / f_ywk_MPa


def taxa_rho_sw_adotada(*, A_sw_por_s: float, b_w_no_plano_do_cortante: float,
                        alpha_estribo_graus: float) -> float:
    """Taxa rho_sw do estribo ADOTADO [adimensional].

    Ref.: ABNT NBR 6118:2023, item 17.4.1.1.1, p. 134
    [rule: NBR6118-17.4.1.1.1-armadura-transversal-minima-por-resistencia]

        rho_sw = (A_sw/s) / (b_w · sen alpha_estribo)

    A verificação é de um estribo CONCRETO (A_sw e s declarados), não de uma
    área abstrata — REQ-PILARETE-18(n).
    """
    exigir_positivo("b_w_no_plano_do_cortante", b_w_no_plano_do_cortante,
                    fonte="ABNT NBR 6118:2023, 17.4.1.1.1, p. 134",
                    apoio_no_ruleset="NBR6118-17.4.1.1.1-armadura-transversal-"
                                     "minima-por-resistencia")
    return A_sw_por_s / (b_w_no_plano_do_cortante
                         * math.sin(math.radians(alpha_estribo_graus)))


@dataclass(frozen=True)
class FibraDeM0:
    """M_0 e a razão M_0/M_Sd,máx de UMA fibra candidata, sob flexão oblíqua.

    Ref.: ABNT NBR 6118:2023, item 17.4.2.2, alínea b), p. 138
    [deriv: DER-NBR6118-17.4.2.2-W1-fibra-mais-tracionada]
    """

    plano: str
    """``"x"`` (W_1 = b·h²/6) ou ``"y"`` (W_1 = h·b²/6)."""

    W_1: float
    """Módulo de resistência da seção bruta nesta fibra [m³]."""

    M_0: float
    """N_(gamma_f=1,0)·W_1/A_c [kN·m]."""

    M_Sd_max: float
    """Momento de CÁLCULO máximo no MESMO plano [kN·m]."""

    razao: float
    """M_0/M_Sd,máx [adimensional]."""


def M_0_e_fibra_governante(
    *, N_gamma_f_1: float, h_secao: float, b_secao: float,
    M_Sd_max_x: float, M_Sd_max_y: float,
) -> tuple[FibraDeM0, FibraDeM0, FibraDeM0]:
    """Devolve (fibra_x, fibra_y, governante) — a governante é a de MENOR razão.

    Ref.: ABNT NBR 6118:2023, item 17.4.2.2, alínea b), p. 137-138
    [rule: NBR6118-17.4.2.2-modelo-I-VRd2-Vsw-Vc]
    [deriv: DER-NBR6118-17.4.2.2-M0-nivel-de-carregamento]
    [deriv: DER-NBR6118-17.4.2.2-W1-fibra-mais-tracionada]

        M_0 = P_d·(W_1/A_c + e_p) + N·(W_1/A_c),  com P_d = 0 em concreto
        armado  ->  M_0 = N_(gamma_f=1,0)·W_1/A_c

        r_x = (N·W_1x/A_c)/M_Sd,máx,x,  W_1x = b·h²/6
        r_y = (N·W_1y/A_c)/M_Sd,máx,y,  W_1y = h·b²/6
        adota-se  min(r_x, r_y)

    DUAS DECISÕES DO a2, AMBAS DO LADO CONSERVADOR, AMBAS DECLARADAS:

    **V20(2) — nível de carregamento de N.** A Norma manda calcular a tensão
    que M_0 anula "com valores de gamma_f e gamma_p iguais a 1,0 e 0,9,
    respectivamente"; o denominador M_Sd,máx é de CÁLCULO, e a mesma alínea
    explica por quê ("os momentos correspondentes a essas forças normais não
    podem ser considerados no cálculo dessa tensão pois são considerados em
    M_Sd,máx"). A fração mistura dois níveis de ponderação DE PROPÓSITO, e não
    cabe ao software "corrigi-la". Usar N_d majorado infla M_0, infla V_c e é
    do lado INSEGURO — a leitura LITERAL coincide aqui com a conservadora. É
    PROIBIDO obter N_(gamma_f=1,0) dividindo N_d por um gamma_f suposto: o
    software não conhece a composição da combinação, e 1,4 não é
    necessariamente a razão efetiva. Sem o valor declarado, não se majora.

    **V20(3) — qual fibra sob flexão OBLÍQUA.** As designações de W_1 ("módulo
    de resistência na fibra mais tracionada") e de M_Sd,máx são UNIAXIAIS,
    mas o pilarete está SEMPRE sob flexão oblíqua — M_1d,mín é obrigatório nas
    duas direções e 16.3 proíbe a compressão centrada. Há, portanto, duas
    fibras candidatas e dois M_Sd,máx, e a Norma não diz qual usar. V_c cresce
    com M_0/M_Sd,máx, logo o lado conservador é a MENOR razão. O
    EMPARELHAMENTO POR PLANO é parte da decisão: cruzar o W_1 de um plano com
    o M_Sd,máx do outro produziria uma razão que não corresponde a estado
    nenhum. Em seção QUADRADA W_1x = W_1y e a escolha é INVISÍVEL — o caso
    25×40 é obrigatório no GATE 3.

    RECUSA se algum M_Sd,máx vier nulo ou negativo, em vez de deixar a divisão
    explodir e encostar no teto de 2·V_c0.
    """
    A_c = h_secao * b_secao
    fibras = []
    for plano, W_1, M_Sd_max in (
        ("x", b_secao * h_secao ** 2 / 6.0, M_Sd_max_x),
        ("y", h_secao * b_secao ** 2 / 6.0, M_Sd_max_y),
    ):
        if M_Sd_max <= 0.0:
            raise RecusaForaDeDominio(
                parametro=f"M_Sd_max_{plano}",
                valor=M_Sd_max,
                intervalo="> 0",
                fonte="ABNT NBR 6118:2023, 17.4.2.2-b), p. 138 — M_Sd,máx é o "
                      "denominador de M_0/M_Sd,máx",
                forca=DECLARADO_EM_TEXTO,
                apoio_no_ruleset="DER-NBR6118-17.4.2.2-W1-fibra-mais-tracionada",
                sugestao="Os momentos de cálculo do veredito já incluem "
                         "M_1d,mín, logo são estritamente positivos por "
                         "construção. Um zero aqui indica erro de wiring; o "
                         "software RECUSA em vez de encostar no teto de "
                         "2·V_c0.",
            )
        M_0 = N_gamma_f_1 * W_1 / A_c
        fibras.append(FibraDeM0(plano=plano, W_1=W_1, M_0=M_0,
                                M_Sd_max=M_Sd_max, razao=M_0 / M_Sd_max))
    fibra_x, fibra_y = fibras
    governante = fibra_x if fibra_x.razao <= fibra_y.razao else fibra_y
    return fibra_x, fibra_y, governante


def classificar_estado_da_secao(*, N_d: float, h_secao: float, b_secao: float,
                                M_Sd_max_x: float, M_Sd_max_y: float) -> str:
    """Classifica o estado da seção ANTES de escolher o ramo de V_c.

    Ref.: ABNT NBR 6118:2023, item 17.4.2.2, alínea b), p. 137
    [rule: NBR6118-17.4.2.2-modelo-I-VRd2-Vsw-Vc]
    [req: REQ-PILARETE-18-verificacao-de-forca-cortante]  (4)

    Três estados, e a Norma dá um ramo de V_c para cada:

    * **tracionado com LN fora da seção** -> V_c = 0;
    * **flexão simples ou flexo-tração com LN cortando a seção** -> V_c = V_c0
      (Modelo I) ou V_c1 (Modelo II);
    * **flexo-compressão** -> V_c majorado por (1 + M_0/M_Sd,máx), com teto.

    A classificação usa as tensões de borda em ESTÁDIO I (seção bruta, não
    fissurada), compressão positiva:
    ``sigma = N/A_c ± M_Sd,máx,x/W_1x ± M_Sd,máx,y/W_1y``. Se a maior delas
    for de tração, toda a seção está tracionada e a LN caiu fora.

    O ESTADO É IMPRESSO NO MEMORIAL. Aplicar a majoração fora da
    flexo-compressão é defeito COM VETO.
    """
    A_c = h_secao * b_secao
    W_1x = b_secao * h_secao ** 2 / 6.0
    W_1y = h_secao * b_secao ** 2 / 6.0
    parcela_de_flexao = abs(M_Sd_max_x) / W_1x + abs(M_Sd_max_y) / W_1y
    sigma_maxima_de_compressao = N_d / A_c + parcela_de_flexao
    if sigma_maxima_de_compressao <= 0.0:
        return ESTADO_TRACIONADO_LN_FORA
    if N_d > 0.0:
        return ESTADO_FLEXO_COMPRESSAO
    return ESTADO_FLEXAO_SIMPLES_OU_FLEXO_TRACAO


@dataclass(frozen=True)
class ResultadoDispensa:
    """Saída de :func:`dispensa_17_4_1_1_2_c`, com as DUAS condições separadas.

    Ref.: ABNT NBR 6118:2023, item 17.4.1.1.2, alínea c), p. 134
    [rule: NBR6118-17.4.1.1.2-c-excecao-dos-pilares-e-o-f-ctk-sem-sufixo]
    """

    dispensada: bool
    tensao_de_tracao_estadio_I: float
    """Maior tração de borda em estádio I [MPa], positiva."""
    f_ctk_inf: float
    """Limite adotado [MPa] — o INFERIOR, por decisão declarada."""
    condicao_i_atendida: bool
    V_Sd: float
    V_c_do_modelo_I: float
    condicao_ii_atendida: bool
    normal_de_compressao_em_todas_as_combinacoes: bool
    declaracoes: tuple[str, ...]


def dispensa_17_4_1_1_2_c(
    *, concreto: Concreto, N_d: float, h_secao: float, b_secao: float,
    M_Sd_max_x: float, M_Sd_max_y: float, V_Sd: float,
    V_c_do_modelo_I: float,
    normal_de_compressao_em_todas_as_combinacoes: bool,
) -> ResultadoDispensa:
    """Exceção de armadura mínima para PILARES — as DUAS condições, juntas.

    Ref.: ABNT NBR 6118:2023, item 17.4.1.1.2, alínea c), p. 134
    [rule: NBR6118-17.4.1.1.2-c-excecao-dos-pilares-e-o-f-ctk-sem-sufixo]
    [rule: NBR6118-8.2.5-fctm]
    [req: REQ-PILARETE-18-verificacao-de-forca-cortante]  (8)

    A alínea c) dispensa a armadura mínima de 17.4.1.1.1 para "os pilares e
    elementos lineares de fundação submetidos predominantemente à compressão"
    quando SIMULTANEAMENTE, na combinação mais desfavorável de ELU e com a
    seção calculada em **ESTÁDIO I**:

    (i) em nenhum ponto se ultrapassa a tensão f_ctk;
    (ii) V_Sd <= V_c, com V_c de 17.4.2.2.

    Esta remissão NOMINAL a "pilares" é, aliás, o que autoriza aplicar §17.4 a
    pilar: é expressa e não precisa ser interpretada.

    DECISÃO V20(1) — ``f_ctk`` sem sufixo é lido como ``f_ctk,inf``. Ver
    :data:`DECLARACAO_F_CTK_SEM_SUFIXO`, que vai LITERAL ao memorial.

    ``V_c`` da condição (ii) é SEMPRE o do Modelo I, mesmo num projeto que
    adote o Modelo II na verificação de resistência: o texto remete
    nominalmente a "V_c definido em 17.4.2.2".

    NÃO CONFUNDIR: a dispensa alcança SÓ a TAXA rho_sw de 17.4.1.1.1. Ela NÃO
    dispensa a verificação de resistência de 17.4.2 — pelo contrário, uma das
    duas condições É essa verificação — e NÃO dispensa os mínimos da Seção 18,
    que continuam valendo INTEGRALMENTE ("nesse caso, a armadura transversal
    mínima é a definida na Seção 18").
    """
    A_c = h_secao * b_secao
    W_1x = b_secao * h_secao ** 2 / 6.0
    W_1y = h_secao * b_secao ** 2 / 6.0
    # Estádio I, seção bruta; compressão positiva. Tensão de TRAÇÃO em MPa.
    sigma_minima_kPa = (N_d / A_c
                        - abs(M_Sd_max_x) / W_1x - abs(M_Sd_max_y) / W_1y)
    tracao_MPa = max(0.0, -sigma_minima_kPa) / 1000.0
    limite = concreto.fctk_inf
    condicao_i = tracao_MPa <= limite
    condicao_ii = V_Sd <= V_c_do_modelo_I
    dispensada = (condicao_i and condicao_ii
                  and normal_de_compressao_em_todas_as_combinacoes)
    return ResultadoDispensa(
        dispensada=dispensada,
        tensao_de_tracao_estadio_I=tracao_MPa,
        f_ctk_inf=limite,
        condicao_i_atendida=condicao_i,
        V_Sd=V_Sd,
        V_c_do_modelo_I=V_c_do_modelo_I,
        condicao_ii_atendida=condicao_ii,
        normal_de_compressao_em_todas_as_combinacoes=(
            normal_de_compressao_em_todas_as_combinacoes),
        declaracoes=(DECLARACAO_F_CTK_SEM_SUFIXO,
                     DECLARACAO_PREDOMINANTEMENTE_A_COMPRESSAO),
    )


@dataclass(frozen=True)
class PlanoDeCortante:
    """Plano de atuação de V_Sd, com b_w e d já emparelhados a ele.

    Ref.: ABNT NBR 6118:2023, item 17.4.2.2, p. 136-137
    [rule: NBR6118-17.4.2.2-modelo-I-VRd2-Vsw-Vc]
    [req: REQ-PILARETE-18-verificacao-de-forca-cortante]  (3)
    """

    plano: str
    """:data:`PLANO_DE_H` ou :data:`PLANO_DE_B`."""

    V_Sd: float
    """Força cortante de cálculo neste plano [kN]."""

    b_w_no_plano_do_cortante: float
    """Dimensão PERPENDICULAR ao plano de V_Sd [m]."""

    d_util_no_plano_do_cortante: float
    """Altura útil MEDIDA NO plano de V_Sd [m]."""


def plano_de_verificacao(*, H_x: float, H_y: float, h_secao: float,
                         b_secao: float, d_linha_no_plano_de_h: float,
                         d_linha_no_plano_de_b: float) -> PlanoDeCortante:
    """Determina o plano de V_Sd e RECUSA cortante BIAXIAL.

    Ref.: ABNT NBR 6118:2023, itens 17.4.2.1 e 17.2.5, p. 136 e 125
    [rule: NBR6118-17.4.2.1-duas-condicoes-simultaneas-do-ELU-de-cortante]
    [req: REQ-PILARETE-18-verificacao-de-forca-cortante]  (2) e (3)

    ``H_x`` é a componente horizontal cujo plano de atuação é o **plano de h**
    (o mesmo em que atua M_Sd,x e em que W_1x = b·h²/6); ``H_y``, o plano de
    b. Nesse plano, ``b_w`` é a dimensão PERPENDICULAR e ``d`` é a altura útil
    MEDIDA NO plano. Trocar os dois passa por toda a checagem dimensional e
    muda V_Rd2 e V_c0 na mesma proporção — teste obrigatório em seção NÃO
    quadrada.

    GUARDA DE CORTANTE BIAXIAL: se ``H_x != 0`` **e** ``H_y != 0``, RECUSA.
    §17.4 é escrito para UM V_Sd atuando no plano de b_w·d, e a Norma NÃO
    fornece regra de interação entre duas cortantes. O contraste com 17.2.5,
    que fornece a interação para os MOMENTOS oblíquos, é evidência de que a
    omissão não é descuido. É PROIBIDO compor sqrt(V_x² + V_y²), somar
    linearmente, ou verificar cada direção isoladamente como se fossem
    independentes.

    SEM TOLERÂNCIA NUMÉRICA: o gatilho é "as duas componentes DECLARADAS não
    nulas", comparadas com zero exato. Não há base normativa para um limiar de
    "H_y desprezível" e inventá-lo seria exatamente o que esta doutrina
    recusa. H_y = 0,001 kN RECUSA; H_y = 0,0 segue.
    """
    if H_x != 0.0 and H_y != 0.0:
        raise RecusaForaDeDominio(
            parametro="(H_x, H_y)",
            valor=(H_x, H_y),
            intervalo="no máximo UMA componente não nula (cortante uniaxial)",
            fonte="ABNT NBR 6118:2023, 17.4.2.1, p. 136 — §17.4 é escrito para "
                  "UM V_Sd atuando no plano de b_w·d, e a Norma não fornece "
                  "regra de interação entre duas cortantes; o contraste com "
                  "17.2.5 (p. 125), que FORNECE a interação para os momentos "
                  "oblíquos, mostra que a omissão não é descuido",
            forca=NAO_DECLARADO_NA_FONTE,
            apoio_no_ruleset="NBR6118-17.4.2.1-duas-condicoes-simultaneas-do-"
                             "ELU-de-cortante",
            sugestao=(f"Declaradas H_x = {H_x} kN e H_y = {H_y} kN. É PROIBIDO "
                      "compor sqrt(V_x² + V_y²), somar linearmente ou "
                      "verificar cada direção isoladamente. Sem tolerância "
                      "numérica: o gatilho é o zero exato."),
        )
    if H_y != 0.0:
        return PlanoDeCortante(
            plano=PLANO_DE_B, V_Sd=abs(H_y),
            b_w_no_plano_do_cortante=h_secao,
            d_util_no_plano_do_cortante=b_secao - d_linha_no_plano_de_b,
        )
    return PlanoDeCortante(
        plano=PLANO_DE_H, V_Sd=abs(H_x),
        b_w_no_plano_do_cortante=b_secao,
        d_util_no_plano_do_cortante=h_secao - d_linha_no_plano_de_h,
    )


@dataclass(frozen=True)
class ResultadoCortante:
    """Veredito de cortante com tudo que REQ-PILARETE-12-(n) a (q) exige.

    Ref.: ABNT NBR 6118:2023, item 17.4.2.1, p. 136
    [rule: NBR6118-17.4.2.1-duas-condicoes-simultaneas-do-ELU-de-cortante]
    """

    modelo_de_calculo: str
    theta_biela_graus: float | None
    alpha_estribo_graus: float
    plano: PlanoDeCortante
    alpha_v2_valor: float
    f_ywd_MPa: float
    V_Rd2_valor: float
    V_c0_valor: float
    V_c1_valor: float | None
    """V_c1 do Modelo II; ``None`` no Modelo I e no ramo indefinido abaixo."""
    V_c1_indefinido_por_V_Sd_acima_de_V_Rd2: bool
    """True quando o Modelo II foi declarado e V_Sd > V_Rd2.

    Ref.: ABNT NBR 6118:2023, item 17.4.2.3, alínea b), p. 139
    [deriv: DER-NBR6118-17.4.2.3-Vc1-interpolacao-linear]

    A interpolação de V_c1 é definida entre V_c0 e V_Rd2; acima de V_Rd2 ela
    NÃO existe e extrapolá-la daria valor negativo. A seção já está REPROVADA
    por ``condicao_biela_atendida``, e o memorial diz que V_c1 não foi
    definido em vez de imprimir um número inventado.
    """
    estado_da_secao: str
    N_gamma_f_1: float | None
    fibra_x: FibraDeM0 | None
    fibra_y: FibraDeM0 | None
    fibra_governante: FibraDeM0 | None
    majoracao_aplicada: bool
    teto_2Vc_governou: bool
    V_c_valor: float
    V_sw_valor: float
    V_Rd3_valor: float
    condicao_biela_atendida: bool
    """V_Sd <= V_Rd2 (compressão diagonal do concreto, 17.4.2.1-a)."""
    condicao_trelica_atendida: bool
    """V_Sd <= V_Rd3 = V_c + V_sw (tração diagonal, 17.4.2.1-b)."""
    atendido: bool
    """Conjunção das duas. Aprovar com uma só é defeito com veto do a6."""
    rho_sw_adotada: float
    rho_sw_minima: float
    dispensa: ResultadoDispensa
    armadura_minima_atendida: bool
    ausencias_deliberadas: tuple[str, ...]

    @property
    def nome_do_veredito(self) -> str:
        """Nome EXATO do veredito de §17.4, sem atalho.

        Ref.: ABNT NBR 6118:2023, item 17.4.2.1, p. 136
        [rule: NBR6118-17.4.2.1-duas-condicoes-simultaneas-do-ELU-de-cortante]

        "ELU de FORÇA CORTANTE (NBR 6118:2023, 17.4.2.1): ATENDIDO / NÃO
        ATENDIDO". O nome COMPLETO do veredito do ELEMENTO, que depende da
        FAIXA de 14.4.1, é montado em :mod:`...pilarete.elemento`.
        """
        estado = "ATENDIDO" if self.atendido else "NÃO ATENDIDO"
        return (f"ELU de FORÇA CORTANTE (NBR 6118:2023, 17.4.2.1): {estado}")


def verificar(
    *,
    classificacao: ResultadoClassificacao,
    concreto: Concreto,
    aco_do_estribo: Aco,
    h_secao: float,
    b_secao: float,
    d_linha_no_plano_de_h: float,
    d_linha_no_plano_de_b: float,
    H_x: float,
    H_y: float,
    N_d: float,
    M_Sd_max_x: float,
    M_Sd_max_y: float,
    modelo_de_calculo: str | None,
    theta_biela_graus: float | None,
    alpha_estribo_graus: float | None,
    A_sw_por_s: float | None,
    N_gamma_f_1: float | None,
    normal_de_compressao_em_todas_as_combinacoes: bool,
) -> ResultadoCortante:
    """ELU de força cortante completo. Só roda na FAIXA A; recusa na FAIXA B.

    Ref.: ABNT NBR 6118:2023, itens 17.4.2.1, 17.4.2.2, 17.4.2.3, 17.4.1.1.1,
    17.4.1.1.2-c) e 17.4.1.1.5, p. 134-139
    [rule: NBR6118-17.4.2.1-duas-condicoes-simultaneas-do-ELU-de-cortante]
    [rule: NBR6118-17.4.2.2-modelo-I-VRd2-Vsw-Vc]
    [rule: NBR6118-17.4.2.3-modelo-II-theta-arbitrado]
    [rule: NBR6118-17.4.1.1.1-armadura-transversal-minima-por-resistencia]
    [rule: NBR6118-17.4.1.1.2-c-excecao-dos-pilares-e-o-f-ctk-sem-sufixo]
    [rule: NBR6118-17.4.1.1.5-17.4.1.1.6-intervalo-de-alpha-e-remissao-a-secao-18]
    [deriv: DER-NBR6118-14.4.1-faixa-B-recusa-do-cortante]
    [deriv: DER-NBR6118-17.4.2.2-M0-nivel-de-carregamento]
    [deriv: DER-NBR6118-17.4.2.2-W1-fibra-mais-tracionada]
    [deriv: DER-NBR6118-17.4.2.3-Vc1-interpolacao-linear]
    [req: REQ-PILARETE-18-verificacao-de-forca-cortante]

    VEREDITO = ``V_Sd <= V_Rd2`` **e** ``V_Sd <= V_Rd3 = V_c + V_sw``. As
    duas, sempre. Aprovar com uma só é defeito com veto do a6.

    A PRIMEIRA COISA que a função faz é chamar a guarda de 14.4.1: um V_Rd2
    calculado antes de a faixa ser conhecida é defeito com veto, mesmo que o
    valor nunca chegue à tela.

    ENTRADAS SEM DEFAULT SILENCIOSO, cada uma com recusa própria: o MODELO
    (a Norma apresenta os dois sem critério de escolha — "é PROIBIDO default,
    é PROIBIDO tentar os dois, é PROIBIDO adotar o que aprova"),
    ``theta_biela`` só com Modelo II e em [30°, 45°], ``alpha_estribo``,
    ``A_sw/s`` do estribo ADOTADO e ``N_(gamma_f=1,0)``.

    NÃO EXISTE, E NÃO PODE EXISTIR, LAÇO SOBRE ``theta_biela`` neste pacote:
    a Norma não fixa theta, não dá critério de escolha, não recomenda valor e
    não manda otimizar; em 17.5.1.1 (torção), com o mesmo intervalo, ela
    escreve "pode ser arbitrada pelo projeto". Encontrar aqui uma varredura de
    theta é VETO do a6.

    A seção verificada é a de MAIOR V_Sd do pilarete — num pilarete engastado
    na base com H no topo, é a seção da BASE, que é a mesma em que
    REQ-PILARETE-15 verifica N+M.
    """
    # (1)/(5) A GUARDA DE FAIXA VEM ANTES DE QUALQUER EXPRESSÃO DE §17.4.
    recusar_cortante_na_faixa_B(classificacao)

    exigir_declarado(
        "modelo_de_calculo", modelo_de_calculo,
        fonte="ABNT NBR 6118:2023, 17.4.2, p. 136 — a Norma apresenta os "
              "Modelos I e II SEM critério de escolha; a escolha é do "
              "PROJETISTA",
        apoio_no_ruleset="NBR6118-17.4.2.1-duas-condicoes-simultaneas-do-ELU-"
                         "de-cortante",
        sugestao="É PROIBIDO default, é PROIBIDO 'tentar os dois' e é "
                 "PROIBIDO adotar o que aprova.",
    )
    exigir_um_de("modelo_de_calculo", modelo_de_calculo, MODELOS_DE_CALCULO,
                 fonte="ABNT NBR 6118:2023, 17.4.2, p. 136",
                 apoio_no_ruleset="NBR6118-17.4.2.1-duas-condicoes-simultaneas-"
                                  "do-ELU-de-cortante")

    if modelo_de_calculo == MODELO_II:
        exigir_declarado(
            "theta_biela_graus", theta_biela_graus,
            fonte="ABNT NBR 6118:2023, 17.4.2.3, p. 138 — theta é ARBITRADO "
                  "pelo projeto, entre 30° e 45°",
            apoio_no_ruleset="NBR6118-17.4.2.3-modelo-II-theta-arbitrado",
            sugestao="Sem theta declarado, o Modelo II NÃO está disponível. É "
                     "PROIBIDO adotar 30°, 45° ou qualquer outro como default "
                     "silencioso, e é PROIBIDO otimizar.",
        )
        exigir_intervalo(
            "theta_biela_graus", float(theta_biela_graus), 30.0, 45.0,
            fonte="ABNT NBR 6118:2023, 17.4.2.3, p. 138",
            forca=DECLARADO_EM_TEXTO,
            apoio_no_ruleset="NBR6118-17.4.2.3-modelo-II-theta-arbitrado")
    elif theta_biela_graus is not None:
        raise RecusaForaDeDominio(
            parametro="theta_biela_graus",
            valor=theta_biela_graus,
            intervalo="ausente (None) quando o modelo é MODELO_I",
            fonte="ABNT NBR 6118:2023, 17.4.2.2, p. 136 — no Modelo I as "
                  "diagonais são fixas a 45° e NÃO há escolha de theta",
            forca=DECLARADO_EM_TEXTO,
            apoio_no_ruleset="NBR6118-17.4.2.2-modelo-I-VRd2-Vsw-Vc",
        )

    exigir_declarado(
        "alpha_estribo_graus", alpha_estribo_graus,
        fonte="ABNT NBR 6118:2023, 17.4.1.1.5, p. 135",
        apoio_no_ruleset="NBR6118-17.4.1.1.5-17.4.1.1.6-intervalo-de-alpha-e-"
                         "remissao-a-secao-18")
    exigir_intervalo(
        "alpha_estribo_graus", float(alpha_estribo_graus), 45.0, 90.0,
        fonte="ABNT NBR 6118:2023, 17.4.1.1.5, p. 135 — 45° <= alpha <= 90°",
        forca=DECLARADO_EM_TEXTO,
        apoio_no_ruleset="NBR6118-17.4.1.1.5-17.4.1.1.6-intervalo-de-alpha-e-"
                         "remissao-a-secao-18")
    if float(alpha_estribo_graus) != ALPHA_ESTRIBO_DESTA_VERSAO:
        raise RecusaForaDeDominio(
            parametro="alpha_estribo_graus",
            valor=alpha_estribo_graus,
            intervalo=f"= {ALPHA_ESTRIBO_DESTA_VERSAO}° NESTA VERSÃO",
            fonte="ESCOPO deste software, NÃO da Norma: a NBR 6118:2023, "
                  "17.4.1.1.5 (p. 135), admite 45° <= alpha <= 90°",
            forca=ESCOPO_DESTA_VERSAO,
            apoio_no_ruleset="NBR6118-17.4.1.1.5-17.4.1.1.6-intervalo-de-alpha-"
                             "e-remissao-a-secao-18",
            sugestao="Motivo do escopo: 90° é o lado conservador em V_sw, é o "
                     "que 18.4.3 detalha para pilar, e o caminho com sen/cos "
                     "não trivial ficaria sem nenhum caso de validação.",
        )
    exigir_declarado(
        "A_sw_por_s", A_sw_por_s,
        fonte="ABNT NBR 6118:2023, 17.4.2.2-b), p. 137 — a verificação é de um "
              "estribo CONCRETO (A_sw e s adotados), não de uma área abstrata",
        apoio_no_ruleset="NBR6118-17.4.2.2-modelo-I-VRd2-Vsw-Vc")
    exigir_positivo("A_sw_por_s", float(A_sw_por_s),
                    fonte="ABNT NBR 6118:2023, 17.4.2.2-b), p. 137",
                    apoio_no_ruleset="NBR6118-17.4.2.2-modelo-I-VRd2-Vsw-Vc")

    # (2)/(3) plano de verificação, com a recusa do cortante biaxial.
    plano = plano_de_verificacao(
        H_x=H_x, H_y=H_y, h_secao=h_secao, b_secao=b_secao,
        d_linha_no_plano_de_h=d_linha_no_plano_de_h,
        d_linha_no_plano_de_b=d_linha_no_plano_de_b)

    fator_v2 = alpha_v2(concreto.fck)
    tensao_do_estribo = f_ywd(aco_do_estribo)
    V_Rd2_valor = V_Rd2(
        modelo_de_calculo=str(modelo_de_calculo), f_ck_MPa=concreto.fck,
        f_cd_MPa=concreto.fcd,
        b_w_no_plano_do_cortante=plano.b_w_no_plano_do_cortante,
        d_util_no_plano_do_cortante=plano.d_util_no_plano_do_cortante,
        alpha_estribo_graus=float(alpha_estribo_graus),
        theta_biela_graus=theta_biela_graus)
    V_sw_valor = V_sw(
        modelo_de_calculo=str(modelo_de_calculo),
        A_sw_por_s=float(A_sw_por_s),
        d_util_no_plano_do_cortante=plano.d_util_no_plano_do_cortante,
        f_ywd_MPa=tensao_do_estribo,
        alpha_estribo_graus=float(alpha_estribo_graus),
        theta_biela_graus=theta_biela_graus)
    V_c0_valor = V_c0(
        concreto=concreto,
        b_w_no_plano_do_cortante=plano.b_w_no_plano_do_cortante,
        d_util_no_plano_do_cortante=plano.d_util_no_plano_do_cortante)

    # (4) estado da seção ANTES de escolher o ramo de V_c.
    estado = classificar_estado_da_secao(
        N_d=N_d, h_secao=h_secao, b_secao=b_secao,
        M_Sd_max_x=M_Sd_max_x, M_Sd_max_y=M_Sd_max_y)

    # (6) referência de V_c do modelo DECLARADO: V_c0 no Modelo I, V_c1 no II.
    #
    # A GUARDA `plano.V_Sd <= V_Rd2_valor` NÃO É DEFENSIVA, é de DOMÍNIO: a
    # interpolação de 17.4.2.3-b) está definida entre V_c0 e V_Rd2 e
    # :func:`V_c1` RECUSA acima de V_Rd2 (extrapolar a reta daria V_c1
    # negativo). Mas ultrapassar V_Rd2 NÃO é entrada fora de domínio — é uma
    # seção que REPROVA, e 17.4.2.1 já a reprova por ``condicao_biela``. Um
    # veredito "NÃO ATENDIDO" é resultado legítimo e o software tem de
    # emiti-lo, com todos os valores, em vez de levantar exceção: recusa e
    # reprovação são coisas diferentes neste projeto (a recusa diz "não sei
    # calcular", a reprovação diz "calculei e não passa").
    #
    # Nesse ramo V_c1 fica INDEFINIDO — e é isso que o memorial diz, pelo
    # campo ``V_c1_indefinido_por_V_Sd_acima_de_V_Rd2``. A referência entra
    # como 0,0 (o valor para o qual a própria interpolação tende em
    # V_Sd = V_Rd2), o que é o lado conservador e não altera o veredito, já
    # reprovado pela biela.
    V_c1_valor: float | None = None
    V_c1_indefinido = False
    if modelo_de_calculo == MODELO_II:
        if plano.V_Sd <= V_Rd2_valor:
            V_c1_valor = V_c1(V_Sd=plano.V_Sd, V_c0_valor=V_c0_valor,
                              V_Rd2_do_modelo_II=V_Rd2_valor)
        else:
            V_c1_indefinido = True

    if modelo_de_calculo == MODELO_I:
        referencia = V_c0_valor
    elif V_c1_valor is not None:
        referencia = V_c1_valor
    else:
        referencia = 0.0

    # (5) M_0, com a fibra conservadora, e a majoração.
    fibra_x = fibra_y = governante = None
    majoracao_aplicada = False
    teto_governou = False
    if estado == ESTADO_TRACIONADO_LN_FORA:
        V_c_valor = 0.0
    elif estado == ESTADO_FLEXO_COMPRESSAO and N_gamma_f_1 is not None:
        fibra_x, fibra_y, governante = M_0_e_fibra_governante(
            N_gamma_f_1=N_gamma_f_1, h_secao=h_secao, b_secao=b_secao,
            M_Sd_max_x=M_Sd_max_x, M_Sd_max_y=M_Sd_max_y)
        majorado = referencia * (1.0 + governante.razao)
        teto = 2.0 * referencia
        majoracao_aplicada = True
        teto_governou = majorado > teto
        V_c_valor = min(majorado, teto)
    else:
        V_c_valor = referencia

    V_Rd3_valor = V_c_valor + V_sw_valor
    condicao_biela = plano.V_Sd <= V_Rd2_valor
    condicao_trelica = plano.V_Sd <= V_Rd3_valor

    # (8) armadura mínima por resistência, com a exceção de 17.4.1.1.2-c).
    rho_minima = rho_sw_min(concreto=concreto, f_ywk_MPa=aco_do_estribo.fyk)
    rho_adotada = taxa_rho_sw_adotada(
        A_sw_por_s=float(A_sw_por_s),
        b_w_no_plano_do_cortante=plano.b_w_no_plano_do_cortante,
        alpha_estribo_graus=float(alpha_estribo_graus))
    V_c_modelo_I_para_dispensa = (
        0.0 if estado == ESTADO_TRACIONADO_LN_FORA else
        (min(V_c0_valor * (1.0 + governante.razao), 2.0 * V_c0_valor)
         if governante is not None else V_c0_valor))
    dispensa = dispensa_17_4_1_1_2_c(
        concreto=concreto, N_d=N_d, h_secao=h_secao, b_secao=b_secao,
        M_Sd_max_x=M_Sd_max_x, M_Sd_max_y=M_Sd_max_y, V_Sd=plano.V_Sd,
        V_c_do_modelo_I=V_c_modelo_I_para_dispensa,
        normal_de_compressao_em_todas_as_combinacoes=(
            normal_de_compressao_em_todas_as_combinacoes))

    return ResultadoCortante(
        modelo_de_calculo=str(modelo_de_calculo),
        theta_biela_graus=theta_biela_graus,
        alpha_estribo_graus=float(alpha_estribo_graus),
        plano=plano,
        alpha_v2_valor=fator_v2,
        f_ywd_MPa=tensao_do_estribo,
        V_Rd2_valor=V_Rd2_valor,
        V_c0_valor=V_c0_valor,
        V_c1_valor=V_c1_valor,
        V_c1_indefinido_por_V_Sd_acima_de_V_Rd2=V_c1_indefinido,
        estado_da_secao=estado,
        N_gamma_f_1=N_gamma_f_1,
        fibra_x=fibra_x,
        fibra_y=fibra_y,
        fibra_governante=governante,
        majoracao_aplicada=majoracao_aplicada,
        teto_2Vc_governou=teto_governou,
        V_c_valor=V_c_valor,
        V_sw_valor=V_sw_valor,
        V_Rd3_valor=V_Rd3_valor,
        condicao_biela_atendida=condicao_biela,
        condicao_trelica_atendida=condicao_trelica,
        atendido=condicao_biela and condicao_trelica,
        rho_sw_adotada=rho_adotada,
        rho_sw_minima=rho_minima,
        dispensa=dispensa,
        armadura_minima_atendida=(rho_adotada >= rho_minima
                                  or dispensa.dispensada),
        ausencias_deliberadas=AUSENCIAS_DELIBERADAS,
    )
