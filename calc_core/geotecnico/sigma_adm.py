"""Parcela de ELU da tensão admissível — os dois caminhos aprovados na v9.

Ref.: ABNT NBR 6122:2022, itens 7.3 e 7.4, p. 22-23
[rule: NBR6122-7.3-7.4-conjuncao-ELU-ELS]

"A tensão admissível ou a tensão resistente de cálculo deve ser fixada a partir
da utilização e interpretação de um ou mais dos procedimentos descritos em
7.3.1 a 7.3.3, além de atender ao disposto em 7.4." | "As tensões determinadas
em 7.3 devem também atender ao estado limite de serviço."

É A REGRA MAIS IMPORTANTE DESTE MÓDULO, e a única que restringe em vez de
habilitar. A definição 3.45 de "tensão admissível" é CONJUNTIVA — atende aos
estados limites últimos **E** de serviço. Tudo o que a v9 aprova (Terzaghi/
Vesic, Teixeira, regra N/50) entrega APENAS a parcela de ELU; nenhum desses
caminhos verifica recalque. Logo NENHUM produz, sozinho, a "tensão admissível"
da NBR 6122.

Consequência executável: o retorno chama-se ``sigma_adm_ELU_kPa``, nunca
``sigma_adm``, e carrega ``rotulo_ELU`` colado ao número até a tela e o
memorial (REQ-SIGMA-09). Vale IGUALMENTE para o caminho semiempírico: a
alegação de que correlações empíricas "já embutem" o recalque é plausível e NÃO
é verificável a partir do valor entregue, e em nenhum caso traz o recalque
aceitável C do projeto — que a Norma expressamente não fixa (§6.2.2.2.2 lista
sete fatores, nenhum calculável de um perfil SPT).

O ELS não é calculável nesta versão: 6.2.2.1 exige Ek <= C; o recalque estimado
existe no motor amplo (``calc_core/sapata_isolada/recalques.py``) mas está em
``escopo_amplo_em_conferencia`` e não foi auditado, e C é decisão do
engenheiro. Por isso a regra vira RÓTULO, e não aritmética.

O SOFTWARE NÃO ESCOLHE O MÉTODO. Havendo mais de um caminho legítimo, rodam-se
todos os aplicáveis e a dispersão vai para a tela; a seleção de qual valor vira
o sigma_adm do projeto é do engenheiro (REQ-SIGMA-05).
"""
from __future__ import annotations

from collections.abc import Callable

from calc_core.geotecnico.capacidade import capacidade_de_carga
from calc_core.geotecnico.dominio import ForaDoDominioError
from calc_core.geotecnico.seguranca import (
    ORIGEM_ANALITICA,
    exigir_metodo_admissivel,
    fator_de_seguranca_global,
)
from calc_core.geotecnico.semiempirico import (
    NOME_REGRA_50,
    NOME_TEIXEIRA,
    regra_brasileira_nspt_50_argila,
    teixeira_1996_areia,
)
from calc_core.modelos import (
    DECLARACAO_REGIONAL_EXIGIDA,
    ROTULO_ELU,
    ROTULO_FONTE_NAO_NORMATIVA,
    EntradaCapacidadeCarga,
    EntradaSemiempiricaSPT,
    RecusaDeMetodo,
    ResultadoDispersaoSemiempirica,
    ResultadoSigmaAdmELU,
)

NOME_TEORICO = ("capacidade de carga de Terzaghi com fatores de Vesic e "
                "fatores de forma de De Beer")


def teorico_terzaghi_vesic(
    entrada: EntradaCapacidadeCarga,
    *,
    n_provas_de_carga: int = 0,
    provas_executadas_na_fase_de_projeto: bool = False,
) -> ResultadoSigmaAdmELU:
    """sigma_a = sigma_r / FSg pelo caminho teórico, com FSg = 3,00 da Tabela 1.

    Ref.: ABNT NBR 6122:2022, item 7.3.2, p. 22
    [rule: NBR6122-7.3.2-metodos-teoricos-condicao-2022] (autorização e
    condição suspensiva)

    Ref.: ABNT NBR 6122:2022, item 6.2.1.1.1 e Tabela 1, p. 17
    [rule: NBR6122-6.2.1.1.1-fatores-seguranca-tabela1] (linha "Analíticos":
    FSg = 3,00 FIXO; nota (b): c e phi CARACTERÍSTICOS, sem minoração)

    Ref.: ABNT NBR 6122:2022, itens 7.3 e 7.4, p. 22-23
    [rule: NBR6122-7.3-7.4-conjuncao-ELU-ELS] (rótulo obrigatório da saída)

    [pratica: FB-CINTRA-TERZAGHI-VESIC-capacidade-de-carga] (a EQUAÇÃO)
    [pratica: FB-CINTRA-4.1.1-sigma-adm-teorico-FS3] (a divisão por 3,0)

    Em caso de divergência futura entre a fonte bibliográfica e a Norma quanto
    ao valor do FS, PREVALECE A NORMA: o 3,0 do livro apenas coincide com a
    Tabela 1, e a citação de memorial para o divisor é
    ``[rule: NBR6122-6.2.1.1.1-fatores-seguranca-tabela1]``.

    FSg = 2,00 só é oferecido com DUAS condições declaradas pelo usuário:
    ``n_provas_de_carga >= 2`` **e** ``provas_executadas_na_fase_de_projeto``
    — prova de carga de obra não reduz o FS.

    Domínio de validade em ``capacidade.validar_entrada_capacidade``: fora
    dele esta função RECUSA e não devolve número algum.
    """
    exigir_metodo_admissivel(entrada.metodo_de_seguranca)
    resultado_capacidade = capacidade_de_carga(entrada)
    fs = fator_de_seguranca_global(
        ORIGEM_ANALITICA,
        n_provas_de_carga=n_provas_de_carga,
        provas_executadas_na_fase_de_projeto=provas_executadas_na_fase_de_projeto,
        metodo_de_seguranca=entrada.metodo_de_seguranca,
    )
    return ResultadoSigmaAdmELU(
        sigma_adm_ELU_kPa=resultado_capacidade.sigma_r_kPa / fs.valor,
        metodo="teorico",
        nome_do_metodo=NOME_TEORICO,
        metodo_de_seguranca=entrada.metodo_de_seguranca,
        rotulo_ELU=ROTULO_ELU,
        rotulo_fonte=ROTULO_FONTE_NAO_NORMATIVA,
        regras=("NBR6122-7.3.2-metodos-teoricos-condicao-2022",
                "NBR6122-6.2.1.1.1-fatores-seguranca-tabela1",
                "NBR6122-7.3-7.4-conjuncao-ELU-ELS"),
        praticas=("FB-CINTRA-TERZAGHI-VESIC-capacidade-de-carga",
                  "FB-CINTRA-4.1.1-sigma-adm-teorico-FS3"),
        FSg_aplicado=fs.valor,
        FS_embutido=None,
        FS_embutido_origem=None,
        capacidade=resultado_capacidade,
        memoria={
            "sigma_r_kPa": resultado_capacidade.sigma_r_kPa,
            "parcela_coesao_kPa": resultado_capacidade.parcela_coesao_kPa,
            "parcela_sobrecarga_kPa": resultado_capacidade.parcela_sobrecarga_kPa,
            "parcela_peso_kPa": resultado_capacidade.parcela_peso_kPa,
            "q_kPa": resultado_capacidade.q_kPa,
            "Nc": resultado_capacidade.fatores.Nc,
            "Nq": resultado_capacidade.fatores.Nq,
            "N_gamma": resultado_capacidade.fatores.N_gamma,
            "Nq_sobre_Nc": resultado_capacidade.fatores.Nq_sobre_Nc,
            "Sc": resultado_capacidade.fatores_de_forma.Sc,
            "Sq": resultado_capacidade.fatores_de_forma.Sq,
            "S_gamma": resultado_capacidade.fatores_de_forma.S_gamma,
            "FSg": fs.valor,
        },
        avisos=resultado_capacidade.avisos + (
            f"FSg = {fs.valor:.2f} — Tabela 1, linha '{fs.linha_da_tabela_1}'. "
            + fs.justificativa,
            ("sigma_r é, por coerência do FS global, um valor MÉDIO de "
            "resistência: alimentar esta divisão com c e phi já tomados como "
            "quantis inferiores conta segurança duas vezes. Registrar no "
            "memorial qual estatística de c e phi foi usada."),
            ("Escopo desta versão: sapata isolada, carga CENTRADA, solo "
            "HOMOGÊNEO. Excentricidade não é tratada — a área efetiva de "
            "Meyerhof está em kb mas NÃO foi aprovada."),
        ),
    )


def semiempirico_spt(
    entrada: EntradaSemiempiricaSPT,
) -> ResultadoDispersaoSemiempirica:
    """Roda TODAS as correlações semiempíricas e devolve as aplicáveis lado a lado.

    Ref.: ABNT NBR 6122:2022, item 7.3.3, p. 22
    [rule: NBR6122-7.3.3-metodos-semiempiricos]

    Ref.: ABNT NBR 6122:2022, itens 7.3 e 7.4, p. 22-23
    [rule: NBR6122-7.3-7.4-conjuncao-ELU-ELS]

    [pratica: FB-REGRA-BRASILEIRA-Nspt-50-argila]
    [pratica: FB-TEIXEIRA-1996-areia]

    Implementa a obrigação (b) do §7.3.3 ("bem como as dispersões dos dados").
    NÃO escolhe, não faz média e não pega o menor: devolve os valores e o nome
    de cada método, e a seleção é do engenheiro (REQ-SIGMA-05).

    O QUE NÃO SE APLICA TAMBÉM APARECE. As correlações fora do domínio saem em
    ``recusas``, com parâmetro, valor, intervalo e a FORÇA do limite —
    distinguindo o que a fonte declara em texto (5 a 20 da regra N/50) do que o
    a2 adotou lendo a extensão de uma figura (1 a 3 m e 4 a 25 de Teixeira),
    porque os dois recusam mas o segundo é revisável (REQ-UI-SIGMA-03).

    NOTA DE LEITURA, para que o resultado não pareça um defeito: as duas
    correlações aprovadas têm domínios de SOLO mutuamente exclusivos — uma é
    para terreno puramente argiloso, a outra para areia. Declarado o solo, no
    máximo uma delas se aplica hoje, e ``recusas`` explica a outra. A dispersão
    de valores só passa a ser observável quando houver duas correlações
    aprovadas para o mesmo tipo de solo; Mello (1975), que seria a terceira, é
    PENDENTE_HUMANO e por isso não está implementada (ver o módulo
    ``geotecnico.semiempirico``).

    Se NENHUMA correlação se aplicar, a função levanta ``ForaDoDominioError``
    da última recusa em vez de devolver lista vazia: entrada sem método
    aplicável é recusa, não resultado (REQ-SIGMA-04).
    """
    exigir_metodo_admissivel(entrada.metodo_de_seguranca)
    resultados: list[ResultadoSigmaAdmELU] = []
    recusas: list[RecusaDeMetodo] = []
    ultima_recusa: ForaDoDominioError | None = None

    tentativas: tuple[tuple[str, str, Callable[[], ResultadoSigmaAdmELU]], ...] = (
        (NOME_REGRA_50, "FB-REGRA-BRASILEIRA-Nspt-50-argila",
         lambda: regra_brasileira_nspt_50_argila(
             N_spt_medio_bulbo=entrada.N_spt,
             forma=entrada.forma,
             solo_declarado=entrada.solo_declarado,
             aplicabilidade_regional_declarada=(
                 entrada.aplicabilidade_regional_declarada),
             considerar_q=entrada.considerar_q,
             q_MPa=entrada.q_MPa,
             metodo_de_seguranca=entrada.metodo_de_seguranca,
         )),
        (NOME_TEIXEIRA, "FB-TEIXEIRA-1996-areia",
         lambda: teixeira_1996_areia(
             N_spt=entrada.N_spt,
             B_m=entrada.B_m,
             forma=entrada.forma,
             solo_declarado=entrada.solo_declarado,
             h_m=entrada.h_m,
             gamma_kN_m3=entrada.gamma_kN_m3,
             aplicabilidade_regional_declarada=(
                 entrada.aplicabilidade_regional_declarada),
             metodo_de_seguranca=entrada.metodo_de_seguranca,
         )),
    )

    for nome, pratica, executar in tentativas:
        try:
            resultados.append(executar())
        except ForaDoDominioError as recusa:
            ultima_recusa = recusa
            recusas.append(RecusaDeMetodo(
                nome_do_metodo=nome,
                pratica=pratica,
                parametro=recusa.parametro,
                valor=recusa.valor,
                intervalo=recusa.intervalo,
                fonte=recusa.fonte,
                forca=recusa.forca,
                motivo=recusa.mensagem,
            ))

    if not resultados:
        assert ultima_recusa is not None
        raise ultima_recusa

    return ResultadoDispersaoSemiempirica(
        resultados=tuple(resultados),
        recusas=tuple(recusas),
        declaracao_regional=DECLARACAO_REGIONAL_EXIGIDA,
    )


__all__ = [
    "NOME_TEORICO",
    "semiempirico_spt",
    "teorico_terzaghi_vesic",
]
