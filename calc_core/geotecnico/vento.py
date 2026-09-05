"""Majoração por vento dos valores admissíveis — condicional, nunca automática.

Ref.: ABNT NBR 6122:2022, item 6.3.2 (com 6.3.1), p. 21
[rule: NBR6122-6.3.2-majoracao-vento-valores-admissiveis]

"Quando se tratar de solicitações obtidas de combinações de ações nas quais o
vento é a ação variável principal, os valores de tensão admissível de sapatas e
tubulões e as cargas admissíveis em estacas podem ser majorados em até 15 %.
Quando esta majoração for utilizada, o fator de segurança global não pode ser
inferior a 1,6. [...] Quando se tratar de solicitações [...] nas quais o vento
não é a ação variável principal, não é permitida a majoração [...] Em qualquer
caso, deve ser feita a verificação estrutural do elemento de fundação. | No
caso de galpões industriais, torres de linhas de transmissão, reservatórios
elevados, silos graneleiros, torres eólicas, torres de telecomunicações e
tanques de produtos químicos, nos quais o vento é a ação variável principal,
[...] podem ser majorados em até 30 %."

DESIGUALDADE, JAMAIS IGUALDADE. "Em ATÉ 15 %" é TETO de uma FACULDADE ("podem
ser"). Escrever ``sigma_adm_vento = 1,15 * sigma_adm`` seria majorar por conta
própria. Formalização::

    sigma_adm_vento <= (1 + k_v) * sigma_adm

sujeito, SIMULTANEAMENTE, a:

    (C1) k_v = 0                  se o vento NÃO é a ação variável principal
    (C2) k_v <= 0,15              caso geral
    (C3) k_v <= 0,30              somente na lista FECHADA de sete obras
    (C4) FSg / (1 + k_v) >= 1,6   piso do fator de segurança global

NADA É INFERIDO. "O vento é a ação variável principal" é definido pela ABNT NBR
8681 (remissão de 6.3.1), vem da análise estrutural a montante e não é
dedutível dentro do módulo de fundação — a NBR 8681:2025 está no acervo mas
nunca foi varrida. O tipo de obra é lista FECHADA e TAXATIVA: edifício
residencial ou comercial comum não está nela e fica em 15 %; nada de "obra
semelhante a galpão". E ``k_v`` é escolha do projetista dentro do teto, com
default 0 (REQ-SIGMA-10).

LEITURA DO PISO DE 1,6, e ela é interpretação declarada, não texto. A Norma não
diz COMO se afere o FSg quando se majora. Adotou-se (a2, v9) que o 1,6 incide
sobre o FSg EFETIVO, o que resta depois da majoração — majorar sigma_adm em
15 % é, por identidade, dividir sigma_rup por FSg/1,15, e não há terceira
grandeza a que o 1,6 possa se referir. A condição BINDA de fato: com FSg = 2,00
(linha das provas de carga) e k_v = 0,30 dá 1,538 < 1,6, e o k_v máximo cai
para 25 %. O efeito de (C4) é contido por construção — só pode RECUSAR ou
REDUZIR uma majoração, nunca criar uma —, de modo que, se a leitura estiver
errada, o software terá sido conservador, nunca inseguro. Pendência
interpretativa registrada em ``kb/pendencias.md`` > V1.

A MAJORAÇÃO É GEOTÉCNICA. "Em qualquer caso, deve ser feita a verificação
estrutural do elemento de fundação" é literal: ``k_v`` não toca flexão,
cisalhamento, punção nem ancoragem, que seguem com os coeficientes da NBR 6118.
Este módulo não é importado por nenhum módulo estrutural e não deve passar a
ser (REQ-SIGMA-10, travado por teste).

O §6.3.3 (10 % sobre valores de CÁLCULO) NÃO está implementado: é o gêmeo desta
regra no outro método de segurança, está PENDENTE_HUMANO no ruleset, e criá-lo
aqui instituiria um segundo padrão de segurança convivendo com o primeiro.

COLISÃO DE SÍMBOLO (a2-verificador.md §3), a registrar antes que alguém as
misture: o ``k_v`` deste módulo é a MAJORAÇÃO POR VENTO, ADIMENSIONAL, entre 0
e 0,30, e o nome vem imposto por REQ-SIGMA-10. Em
``calc_core/sapata_isolada/rigidez.py`` o mesmo símbolo ``k_v`` nomeia o
COEFICIENTE DE REAÇÃO VERTICAL do apoio elástico de Winkler, em kN/m³, de
origem numérica não normativa (Bowles, Vésic) e status PENDENTE_HUMANO. São
grandezas diferentes, com unidades diferentes e proveniências diferentes; o
namespace ``geotecnico.vento.k_v`` é o que as separa. Nenhum dos dois deve ser
lido a partir do outro, e nenhuma função estrutural consome este aqui.

OUTRA MAJORAÇÃO, NÃO CONFUNDIR: ``Solo.coef_sigma_max_excentrico = 1.2`` em
``sapata_isolada/geotecnia.py`` majora sigma_adm INCONDICIONALMENTE sob
excentricidade e é defeito PENDENTE_HUMANO reconhecido no ruleset — não tem
respaldo na NBR 6122:2022 e não é a majoração deste módulo. A existência desta
implementação NÃO autoriza "consertar" aquele valor: são decisões diferentes e
a segunda não foi tomada pelo a2.
"""
from __future__ import annotations

from calc_core.geotecnico.seguranca import (
    METODO_DE_SEGURANCA_DESTA_VERSAO,
    exigir_metodo_admissivel,
)
from calc_core.modelos import ROTULO_ELU, ResultadoMajoracaoVento

K_V_MAX_CASO_GERAL = 0.15
"""Teto geral da majoração ("em até 15 %")."""

K_V_MAX_LISTA_FECHADA = 0.30
"""Teto da lista fechada de sete obras ("em até 30 %")."""

FSG_EFETIVO_MINIMO = 1.6
"""Piso do fator de segurança global quando a majoração é utilizada."""

K_V_DEFAULT = 0.0
"""Default que NÃO majora. A Norma dá o teto, não o valor."""

TIPOS_DE_OBRA_DOS_30_POR_CENTO = (
    "galpões industriais",
    "torres de linhas de transmissão",
    "reservatórios elevados",
    "silos graneleiros",
    "torres eólicas",
    "torres de telecomunicações",
    "tanques de produtos químicos",
)
"""Lista FECHADA e TAXATIVA do §6.3.2. Apresentar por seleção, nunca por texto
livre, e nunca por semelhança."""

AVISO_VERIFICACAO_ESTRUTURAL = (
    "Em qualquer caso, deve ser feita a verificação estrutural do elemento de "
    "fundação (NBR 6122:2022 §6.3.2, literal). A majoração por vento é "
    "GEOTÉCNICA: k_v não se propaga para flexão, cisalhamento, punção ou "
    "ancoragem, que seguem com os coeficientes da NBR 6118."
)

AVISO_TETO_NAO_E_VALOR = (
    "A Norma escreve 'podem ser majorados em ATÉ 15 %' (30 % na lista "
    "fechada): é TETO de uma faculdade, não valor a aplicar. k_v é decisão de "
    "engenharia e o default é 0."
)

AVISO_ACAO_PRINCIPAL_NAO_E_INFERIDA = (
    "Quem define se o vento é a ação variável principal é a ABNT NBR 8681 "
    "(remissão do §6.3.1) e a análise estrutural a montante — o software não "
    "verifica e não infere."
)


class MajoracaoDeVentoError(ValueError):
    """Majoração por vento fora das condições (C1) a (C4) do §6.3.2.

    Ref.: ABNT NBR 6122:2022, item 6.3.2, p. 21
    [rule: NBR6122-6.3.2-majoracao-vento-valores-admissiveis]
    """


def k_v_maximo_admissivel(
    *,
    FSg: float,
    vento_e_acao_variavel_principal: bool = False,
    tipo_de_obra_da_lista_dos_30_por_cento: bool = False,
) -> float:
    """Maior k_v que satisfaz (C1), (C2)/(C3) e (C4) simultaneamente.

    Ref.: ABNT NBR 6122:2022, item 6.3.2 (com 6.3.1), p. 21
    [rule: NBR6122-6.3.2-majoracao-vento-valores-admissiveis]

    Devolve 0,0 quando o vento não é a ação variável principal — a Norma
    escreve "NÃO é permitida a majoração", com zero de tolerância.

    Serve para a interface exibir o teto ao lado do controle (REQ-UI-SIGMA-05).
    NÃO é o valor a adotar: adotar é decisão do engenheiro. Exemplo em que
    (C4) binda: FSg = 2,00 na lista fechada devolve 0,25, e não 0,30.
    """
    if FSg <= 0:
        raise MajoracaoDeVentoError(f"FSg = {FSg}: deve ser positivo.")
    if not vento_e_acao_variavel_principal:
        return 0.0
    teto = (K_V_MAX_LISTA_FECHADA if tipo_de_obra_da_lista_dos_30_por_cento
            else K_V_MAX_CASO_GERAL)
    teto_por_FSg = FSg / FSG_EFETIVO_MINIMO - 1.0
    return max(0.0, min(teto, teto_por_FSg))


def majoracao_admissivel(
    sigma_adm_ELU_kPa: float,
    *,
    FSg: float,
    vento_e_acao_variavel_principal: bool = False,
    tipo_de_obra_da_lista_dos_30_por_cento: bool = False,
    k_v: float = K_V_DEFAULT,
    metodo_de_seguranca: str = METODO_DE_SEGURANCA_DESTA_VERSAO,
) -> ResultadoMajoracaoVento:
    """Aplica (1 + k_v) à parcela de ELU, sob as quatro condições do §6.3.2.

    Ref.: ABNT NBR 6122:2022, item 6.3.2 (com 6.3.1), p. 21
    [rule: NBR6122-6.3.2-majoracao-vento-valores-admissiveis]

    Ref.: ABNT NBR 6122:2022, item 6.2.1.1.1 e Tabela 1, p. 17
    [rule: NBR6122-6.2.1.1.1-fatores-seguranca-tabela1] (origem do FSg que a
    condição (C4) consome)

    Ref.: ABNT NBR 6122:2022, itens 7.3 e 7.4, p. 22-23
    [rule: NBR6122-7.3-7.4-conjuncao-ELU-ELS] (o valor majorado continua sendo
    parcela de ELU: majorar não verifica recalque)

    Guardas executadas NESTA ORDEM, todas RECUSANDO (REQ-SIGMA-10):

    1. ``not vento_e_acao_variavel_principal`` exige ``k_v == 0`` — a Norma
       escreve "não é permitida a majoração";
    2. ``k_v <= 0,30`` na lista fechada, ``k_v <= 0,15`` caso geral;
    3. ``FSg/(1 + k_v) >= 1,6``.

    Com ``k_v = 0`` (default) o resultado é a identidade: mesmo número, com o
    registro de que a majoração não foi utilizada e de que, nesse caso, "podem
    ser aplicados todos os requisitos desta Norma relativos ao valor do fator
    de segurança global".

    ``FSg`` é o fator de segurança global que existe por trás do
    ``sigma_adm_ELU_kPa`` recebido: 3,00 no caminho analítico, ou o
    ``FS_embutido`` da correlação semiempírica (``ResultadoSigmaAdmELU.
    FSg_efetivo`` entrega o número certo nos dois casos). Com FSg >= 3,00 e
    k_v <= 0,30 o efetivo é >= 2,31 e (C4) não binda por esse caminho — mas a
    verificação é EXECUTADA, não presumida.
    """
    exigir_metodo_admissivel(metodo_de_seguranca)
    if sigma_adm_ELU_kPa <= 0:
        raise MajoracaoDeVentoError(
            f"sigma_adm_ELU_kPa = {sigma_adm_ELU_kPa}: deve ser positivo."
        )
    if FSg <= 0:
        raise MajoracaoDeVentoError(f"FSg = {FSg}: deve ser positivo.")
    if k_v < 0:
        raise MajoracaoDeVentoError(
            f"k_v = {k_v}: a majoração não pode ser negativa. Para não majorar "
            "use k_v = 0, que é o default."
        )

    # (C1) — vento não principal: majoração EXPRESSAMENTE proibida.
    if not vento_e_acao_variavel_principal and k_v > 0:
        raise MajoracaoDeVentoError(
            f"k_v = {k_v} com vento_e_acao_variavel_principal=False: a NBR "
            "6122:2022 §6.3.2 escreve que 'não é permitida a majoração dos "
            "valores de tensão admissível' quando o vento não é a ação "
            "variável principal. Zero de tolerância. "
            + AVISO_ACAO_PRINCIPAL_NAO_E_INFERIDA
        )

    # (C2)/(C3) — teto do tipo de obra, lista FECHADA.
    teto = (K_V_MAX_LISTA_FECHADA if tipo_de_obra_da_lista_dos_30_por_cento
            else K_V_MAX_CASO_GERAL)
    if k_v > teto:
        qual = ("a lista fechada de sete tipos de obra do §6.3.2"
                if tipo_de_obra_da_lista_dos_30_por_cento
                else "o caso geral")
        raise MajoracaoDeVentoError(
            f"k_v = {k_v} excede o teto de {teto} para {qual}. A lista dos "
            "30 % é FECHADA e TAXATIVA: "
            + ", ".join(TIPOS_DE_OBRA_DOS_30_POR_CENTO)
            + ". Edifício residencial ou comercial comum não está nela e fica "
            "em 15 % — nada de 'obra semelhante a galpão'."
        )

    # (C4) — piso do fator de segurança global efetivo.
    FSg_efetivo = FSg / (1.0 + k_v)
    if k_v > 0 and FSg_efetivo < FSG_EFETIVO_MINIMO:
        maximo = k_v_maximo_admissivel(
            FSg=FSg,
            vento_e_acao_variavel_principal=vento_e_acao_variavel_principal,
            tipo_de_obra_da_lista_dos_30_por_cento=(
                tipo_de_obra_da_lista_dos_30_por_cento),
        )
        raise MajoracaoDeVentoError(
            f"k_v = {k_v} com FSg = {FSg} dá FSg efetivo = {FSg_efetivo:.4g} < "
            f"{FSG_EFETIVO_MINIMO}: 'quando esta majoração for utilizada, o "
            "fator de segurança global não pode ser inferior a 1,6' "
            f"(§6.3.2). O k_v máximo neste caso é {maximo:.4g}. É o que impede "
            "a acumulação de dois benefícios (provas de carga + vento)."
        )

    maximo = k_v_maximo_admissivel(
        FSg=FSg,
        vento_e_acao_variavel_principal=vento_e_acao_variavel_principal,
        tipo_de_obra_da_lista_dos_30_por_cento=(
            tipo_de_obra_da_lista_dos_30_por_cento),
    )
    avisos = [AVISO_TETO_NAO_E_VALOR, AVISO_VERIFICACAO_ESTRUTURAL]
    if k_v > 0:
        avisos.append(AVISO_ACAO_PRINCIPAL_NAO_E_INFERIDA)
        avisos.append(
            f"Majoração de {k_v:.1%} UTILIZADA: FSg efetivo = "
            f"{FSg_efetivo:.3f} (>= {FSG_EFETIVO_MINIMO}). Leitura adotada do "
            "piso de 1,6 — incide sobre o FSg que resta depois da majoração —, "
            "declarada como interpretação em ruleset.yaml > "
            "NBR6122-6.3.2 > decisao_do_a2_sobre_o_piso_FSg_1_6."
        )
    else:
        avisos.append(
            "Majoração NÃO utilizada (k_v = 0): aplicam-se todos os requisitos "
            "desta Norma relativos ao valor do fator de segurança global "
            "(§6.3.2, terceira frase)."
        )

    return ResultadoMajoracaoVento(
        sigma_adm_ELU_majorado_kPa=(1.0 + k_v) * sigma_adm_ELU_kPa,
        sigma_adm_ELU_base_kPa=sigma_adm_ELU_kPa,
        k_v_adotado=k_v,
        k_v_maximo_admissivel=maximo,
        FSg_base=FSg,
        FSg_efetivo=FSg_efetivo,
        vento_e_acao_variavel_principal=vento_e_acao_variavel_principal,
        tipo_de_obra_da_lista_dos_30_por_cento=(
            tipo_de_obra_da_lista_dos_30_por_cento),
        rotulo_ELU=ROTULO_ELU,
        metodo_de_seguranca=metodo_de_seguranca,
        regras=("NBR6122-6.3.2-majoracao-vento-valores-admissiveis",
                "NBR6122-6.2.1.1.1-fatores-seguranca-tabela1",
                "NBR6122-7.3-7.4-conjuncao-ELU-ELS"),
        avisos=tuple(avisos),
    )


__all__ = [
    "AVISO_ACAO_PRINCIPAL_NAO_E_INFERIDA",
    "AVISO_TETO_NAO_E_VALOR",
    "AVISO_VERIFICACAO_ESTRUTURAL",
    "FSG_EFETIVO_MINIMO",
    "K_V_DEFAULT",
    "K_V_MAX_CASO_GERAL",
    "K_V_MAX_LISTA_FECHADA",
    "TIPOS_DE_OBRA_DOS_30_POR_CENTO",
    "MajoracaoDeVentoError",
    "k_v_maximo_admissivel",
    "majoracao_admissivel",
]
