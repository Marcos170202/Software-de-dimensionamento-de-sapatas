"""Método de segurança e fator de segurança global da Tabela 1.

Ref.: ABNT NBR 6122:2022, item 6.2.1.1.1 e Tabela 1, p. 17
[rule: NBR6122-6.2.1.1.1-fatores-seguranca-tabela1]

Esta é a primeira versão do repositório em que ``calc_core`` ESCOLHE um método
de segurança em vez de receber a tensão admissível pronta. Por isso a guarda
de método de REQ-SIGMA-01 vive aqui e é executável, não comentário.

AS DUAS COLUNAS DA TABELA 1 SÃO ALTERNATIVAS, NÃO CUMULATIVAS. FSg (fator de
segurança global) opera sobre valores CARACTERÍSTICOS; gamma_m opera sobre
valores de CÁLCULO. A aritmética da própria Norma mostra que são calibradas
para o mesmo resultado — 3,00/2,15 = 1,3953 ~= gamma_f = 1,4 (nota c da
Tabela 1) — e portanto aplicar as duas é contar segurança duas vezes.

NESTA VERSÃO SÓ O RAMO ADMISSÍVEL EXISTE. A rota de valores de cálculo
(gamma_m = 2,15 / 1,40, gamma_f = 1,4) NÃO está implementada em lugar algum do
repositório e a regra que a habilitaria — NBR6122-6.3.3-majoracao-vento-
valores-calculo — está PENDENTE_HUMANO. Tentar usá-la aqui levanta exceção.
"""
from __future__ import annotations

from dataclasses import dataclass

from calc_core.modelos import Verificacao

METODO_DE_SEGURANCA_DESTA_VERSAO = "admissivel"
"""Único método de segurança implementado na v9 (REQ-SIGMA-01)."""

BASE_CARACTERISTICA = "caracteristica"
"""Solicitação em valores característicos — a única comparável a sigma_adm."""

BASE_DE_CALCULO = "calculo"
"""Solicitação em valores de cálculo (ações majoradas). PROIBIDA aqui."""

FSG_ANALITICOS = 3.00
"""Tabela 1, linha "Analíticos (b)": FSg = 3,00 FIXO, sem "no mínimo"."""

FSG_MINIMO_SEMIEMPIRICOS = 3.00
"""Tabela 1, linha "Semiempíricos (a)": 3,00 é PISO, não valor fixo.

"Valores propostos no próprio processo E no mínimo 3,00" — se o método de
origem propuser mais, PREVALECE O DO MÉTODO. Ver
``diferenca_de_redacao_entre_as_linhas`` no ruleset e REQ-SIGMA-02.
"""

FSG_COM_DUAS_OU_MAIS_PROVAS_DE_CARGA = 2.00
"""Tabela 1, terceira linha. Exige DUAS OU MAIS provas de carga
"necessariamente executadas na fase de projeto, conforme 7.3.1"."""

ORIGEM_ANALITICA = "analitico"
ORIGEM_SEMIEMPIRICA = "semiempirico"


class MetodoDeSegurancaError(ValueError):
    """Mistura de métodos de segurança da Tabela 1, proibida por REQ-SIGMA-01.

    Ref.: ABNT NBR 6122:2022, item 6.2.1.1.1 e Tabela 1, p. 17
    [rule: NBR6122-6.2.1.1.1-fatores-seguranca-tabela1]
    """


@dataclass(frozen=True)
class FatorDeSegurancaGlobal:
    """FSg adotado, com a linha da Tabela 1 que o justifica.

    Ref.: ABNT NBR 6122:2022, item 6.2.1.1.1 e Tabela 1, p. 17
    [rule: NBR6122-6.2.1.1.1-fatores-seguranca-tabela1]
    """

    valor: float
    """Fator de segurança global efetivamente adotado [adimensional]."""

    linha_da_tabela_1: str
    """Linha da Tabela 1 de onde o valor sai, para o memorial."""

    justificativa: str
    """Por que este valor e não outro — inclui o piso quando ele prevalece."""

    metodo_de_seguranca: str = METODO_DE_SEGURANCA_DESTA_VERSAO
    """Sempre 'admissivel' nesta versão (REQ-SIGMA-01)."""


def exigir_metodo_admissivel(metodo_de_seguranca: str) -> str:
    """Recusa qualquer método de segurança que não seja 'admissivel'.

    Ref.: ABNT NBR 6122:2022, item 6.2.1.1.1 e Tabela 1, p. 17
    [rule: NBR6122-6.2.1.1.1-fatores-seguranca-tabela1]

    REQ-SIGMA-01: toda função que produza ou consuma sigma_adm nesta versão
    carrega ``metodo_de_seguranca`` com valor obrigatório 'admissivel'. A rota
    de valores de cálculo não está implementada e não pode ser simulada.
    """
    if metodo_de_seguranca != METODO_DE_SEGURANCA_DESTA_VERSAO:
        raise MetodoDeSegurancaError(
            f"metodo_de_seguranca = {metodo_de_seguranca!r}: esta versão "
            f"implementa apenas {METODO_DE_SEGURANCA_DESTA_VERSAO!r} "
            "(valores característicos + FSg da Tabela 1). A rota de valores "
            "de cálculo (gamma_m = 2,15 / 1,40) NÃO está implementada — a "
            "regra NBR6122-6.3.3-majoracao-vento-valores-calculo está "
            "PENDENTE_HUMANO no ruleset."
        )
    return metodo_de_seguranca


def exigir_ausencia_de_ponderacao(*, gamma_m_aplicado: bool = False,
                                  gamma_f_aplicado_na_acao: bool = False) -> None:
    """Recusa a mistura das duas colunas da Tabela 1.

    Ref.: ABNT NBR 6122:2022, item 6.2.1.1.1 e Tabela 1, notas b e c, p. 17
    [rule: NBR6122-6.2.1.1.1-fatores-seguranca-tabela1]

    Cobre as proibições (a) e (c) de REQ-SIGMA-01:

    (a) aplicar gamma_m (2,15 / 1,40) a um resultado desta versão — a rota de
        valores de cálculo não existe aqui;
    (c) aplicar gamma_f = 1,4 sobre a ação **e** dividir a resistência por FSg
        — as duas colunas são ALTERNATIVAS (3,00/2,15 ~= 1,4), e usar as duas
        conta segurança duas vezes.
    """
    if gamma_m_aplicado:
        raise MetodoDeSegurancaError(
            "gamma_m (2,15 / 1,40) não pode ser aplicado a resultado desta "
            "versão: a rota de valores de cálculo NÃO está implementada "
            "(REQ-SIGMA-01 a). As duas colunas da Tabela 1 são alternativas."
        )
    if gamma_f_aplicado_na_acao:
        raise MetodoDeSegurancaError(
            "gamma_f = 1,4 na ação E divisão da resistência por FSg é dupla "
            "contagem de segurança (REQ-SIGMA-01 c): a nota c da Tabela 1 "
            "pertence à coluna de VALORES DE CÁLCULO, alternativa à do FSg "
            "(3,00/2,15 = 1,3953 ~= 1,4)."
        )


def exigir_solicitacao_caracteristica(base_da_solicitacao: str) -> str:
    """Recusa comparar sigma_adm contra solicitação em valores de cálculo.

    Ref.: ABNT NBR 6122:2022, item 6.2.1.1.1 e Tabela 1, p. 17
    [rule: NBR6122-6.2.1.1.1-fatores-seguranca-tabela1]

    Proibição (b) de REQ-SIGMA-01, que se apoia na definição §3.47 da mesma
    Norma: tensão de trabalho é "em valores característicos". Comparar contra
    combinação de CÁLCULO (ações majoradas) é erro de método, não de
    arredondamento.
    """
    if base_da_solicitacao != BASE_CARACTERISTICA:
        raise MetodoDeSegurancaError(
            f"base_da_solicitacao = {base_da_solicitacao!r}: sigma_adm só pode "
            f"ser comparada a solicitações {BASE_CARACTERISTICA!r} "
            "(NBR 6122:2022 §3.47, 'em valores característicos'). Comparar "
            "com ações majoradas é mistura de métodos (REQ-SIGMA-01 b)."
        )
    return base_da_solicitacao


def fator_de_seguranca_global(
    origem: str,
    *,
    FS_proposto_pelo_processo: float | None = None,
    n_provas_de_carga: int = 0,
    provas_executadas_na_fase_de_projeto: bool = False,
    metodo_de_seguranca: str = METODO_DE_SEGURANCA_DESTA_VERSAO,
) -> FatorDeSegurancaGlobal:
    """FSg da Tabela 1 para solicitações de compressão em fundação rasa.

    Ref.: ABNT NBR 6122:2022, item 6.2.1.1.1 e Tabela 1, p. 17
    [rule: NBR6122-6.2.1.1.1-fatores-seguranca-tabela1]

    Três linhas, e a diferença de redação entre elas NÃO pode ser apagada:

    * "Analíticos (b)": FSg = 3,00 **fixo**, sem cláusula de "no mínimo".
      Passar ``FS_proposto_pelo_processo`` aqui é erro e levanta exceção — o
      caminho teórico não propõe FS próprio.
    * "Semiempíricos (a)": "valores propostos no próprio processo E no mínimo
      3,00" — 3,00 é PISO. ``FS_proposto_pelo_processo`` é obrigatório e o
      resultado é o MAIOR entre ele e 3,00 (REQ-SIGMA-02).
    * "acrescidos de duas ou mais provas de carga, necessariamente executadas
      na fase de projeto": FSg = 2,00, e só com as DUAS condições declaradas.
      Prova de carga de obra não vale para reduzir o FS.

    ESCOPO: fundações rasas, solicitações de COMPRESSÃO. Não cobre tração,
    deslizamento e tombamento (6.2.1.1.2) nem flutuação (6.2.1.1.3) — não
    estender por analogia.
    """
    exigir_metodo_admissivel(metodo_de_seguranca)
    if origem not in (ORIGEM_ANALITICA, ORIGEM_SEMIEMPIRICA):
        raise ValueError(
            f"origem = {origem!r}: a Tabela 1 conhece apenas "
            f"{ORIGEM_ANALITICA!r} e {ORIGEM_SEMIEMPIRICA!r} nesta versão."
        )
    if n_provas_de_carga < 0:
        raise ValueError("n_provas_de_carga não pode ser negativo.")

    if n_provas_de_carga >= 2 and provas_executadas_na_fase_de_projeto:
        return FatorDeSegurancaGlobal(
            valor=FSG_COM_DUAS_OU_MAIS_PROVAS_DE_CARGA,
            linha_da_tabela_1=(
                "Semiempíricos (a) ou analíticos (b) acrescidos de duas ou "
                "mais provas de carga, necessariamente executadas na fase de "
                "projeto, conforme 7.3.1"
            ),
            justificativa=(
                f"{n_provas_de_carga} provas de carga declaradas na fase de "
                "projeto (>= 2), o que autoriza FSg = 2,00."
            ),
        )

    aviso_provas = ""
    if n_provas_de_carga >= 2 and not provas_executadas_na_fase_de_projeto:
        aviso_provas = (
            f" {n_provas_de_carga} provas de carga informadas, mas NÃO "
            "declaradas como executadas na fase de projeto: a Tabela 1 exige "
            "as duas condições, então FSg = 2,00 não foi oferecido."
        )

    if origem == ORIGEM_ANALITICA:
        if FS_proposto_pelo_processo is not None:
            raise MetodoDeSegurancaError(
                "A linha 'Analíticos (b)' da Tabela 1 crava FSg = 3,00, SEM "
                "cláusula de 'no mínimo'. Não há FS proposto pelo processo a "
                "considerar no caminho teórico."
            )
        return FatorDeSegurancaGlobal(
            valor=FSG_ANALITICOS,
            linha_da_tabela_1="Analíticos (b)",
            justificativa=(
                "FSg = 3,00 FIXO para métodos analíticos; a nota (b) exige "
                "ainda que c e phi entrem CARACTERÍSTICOS, sem minoração."
                + aviso_provas
            ),
        )

    if FS_proposto_pelo_processo is None:
        raise MetodoDeSegurancaError(
            "Caminho semiempírico exige FS_proposto_pelo_processo: a Tabela 1 "
            "diz 'valores propostos no próprio processo E no mínimo 3,00'. "
            "Escrever FSg = 3,00 como constante do caminho semiempírico é "
            "INSEGURO sempre que o método de origem pedir mais (REQ-SIGMA-02)."
        )
    valor = max(FSG_MINIMO_SEMIEMPIRICOS, FS_proposto_pelo_processo)
    prevalece = (
        "o valor proposto pelo processo prevalece sobre o piso"
        if FS_proposto_pelo_processo > FSG_MINIMO_SEMIEMPIRICOS
        else "o piso normativo de 3,00 prevalece"
    )
    return FatorDeSegurancaGlobal(
        valor=valor,
        linha_da_tabela_1="Semiempíricos (a)",
        justificativa=(
            f"FS proposto pelo processo = {FS_proposto_pelo_processo:.4g}; "
            f"piso da Tabela 1 = {FSG_MINIMO_SEMIEMPIRICOS:.2f}; {prevalece}."
            + aviso_provas
        ),
    )


def comparar_com_tensao_atuante(sigma_adm_ELU_kPa: float,
                                sigma_atuante_kPa: float, *,
                                base_da_solicitacao: str,
                                gamma_f_aplicado_na_acao: bool = False,
                                metodo_de_seguranca: str =
                                METODO_DE_SEGURANCA_DESTA_VERSAO) -> Verificacao:
    """Compara tensão atuante característica contra a parcela de ELU.

    Ref.: ABNT NBR 6122:2022, item 6.2.1.1.1 e Tabela 1, p. 17
    [rule: NBR6122-6.2.1.1.1-fatores-seguranca-tabela1]

    Ref.: ABNT NBR 6122:2022, itens 7.3 e 7.4, p. 22-23
    [rule: NBR6122-7.3-7.4-conjuncao-ELU-ELS]

    A comparação só é lícita com solicitação em valores CARACTERÍSTICOS
    (REQ-SIGMA-01 b) e sem gamma_f = 1,4 já aplicado na ação (REQ-SIGMA-01 c):
    o sigma_adm recebido já foi dividido por FSg, e majorar a ação por cima
    disso conta segurança duas vezes. Declarar ``gamma_f_aplicado_na_acao``
    levanta exceção — é entrada, não inferência, porque o software não tem como
    saber o que foi feito com a ação antes de chegar aqui.

    ``ok=True`` NÃO significa conformidade com a NBR 6122: o segundo termo da
    definição 3.45 (ELS, §7.4) não foi verificado por nenhum caminho desta
    versão — a mensagem carrega o rótulo obrigatório.
    """
    exigir_metodo_admissivel(metodo_de_seguranca)
    exigir_solicitacao_caracteristica(base_da_solicitacao)
    exigir_ausencia_de_ponderacao(
        gamma_f_aplicado_na_acao=gamma_f_aplicado_na_acao)
    if sigma_adm_ELU_kPa <= 0:
        raise ValueError("sigma_adm_ELU_kPa deve ser positivo.")
    ok = sigma_atuante_kPa <= sigma_adm_ELU_kPa
    return Verificacao(
        regra="NBR6122-6.2.1.1.1-fatores-seguranca-tabela1",
        descricao="Tensão atuante característica <= parcela de ELU (§7.3)",
        aplicavel=True,
        ok=ok,
        mensagem=(
            f"sigma_atuante = {sigma_atuante_kPa:.1f} kPa "
            f"{'<=' if ok else '>'} {sigma_adm_ELU_kPa:.1f} kPa — "
            "parcela de ELU da tensão admissível (NBR 6122:2022 §7.3); "
            "§7.4 (ELS/recalque) NÃO verificado"
        ),
    )
