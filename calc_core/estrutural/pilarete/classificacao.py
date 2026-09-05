"""Guarda de 14.4.1 — o pilarete é, ou não é, ELEMENTO LINEAR.

Ref.: ABNT NBR 6118:2023, item 14.4.1 (lido com 14.4.1.2), p. 83
[rule: NBR6118-14.4.1-elemento-linear-classificacao]

Ref.: ABNT NBR 6118:2023, item 17.4.1, p. 133
[rule: NBR6118-17.4.1-campo-de-aplicacao-do-cortante]

[deriv: DER-NBR6118-14.4.1-faixa-B-recusa-do-cortante]
[req: REQ-PILARETE-17-guarda-de-elemento-linear-14.4.1]

GUARDA DETERMINÍSTICA, BARATA, E QUE DECIDE SE METADE DA FEATURE EXISTE.
Texto literal de 14.4.1: "São aqueles em que o comprimento longitudinal supera
em pelo menos três vezes a maior dimensão da seção transversal, sendo também
denominados barras."

ESTA VERIFICAÇÃO É DIFERENTE DE ``lambda < lambda_1``, E A CONFUSÃO É O ERRO
MAIS PROVÁVEL AQUI. 15.8.2 decide se os efeitos LOCAIS DE 2ª ORDEM podem ser
dispensados; 14.4.1 decide a CLASSE do elemento. As duas são independentes e o
software as verifica SEPARADAMENTE, imprimindo os dois resultados. A geometria
30×30 com ell = 0,80 m passa em uma (lambda = 18,48 < 35) e reprova na outra
(razão = 2,667 < 3,0).

A FAIXA B NÃO É CASO DE BORDA. Com ENGASTADO_BASE_LIVRE_TOPO (ell_e = 2·ell) e
sob M_1d,mín (lambda_1 = 35), as duas fronteiras só coexistem se
h_máx/b_mín < 1,684, e então só na janela 3·h_máx <= ell < 5,052·b_mín:

    30×30 -> ell em [0,90 ; 1,515) m — confortável
    25×40 -> ell em [1,20 ; 1,263) m — 6 cm de folga
    20×40 -> **VAZIA**: nenhuma altura satisfaz as duas

Com momento de 1ª ordem REAL maior que M_1d,mín, lambda_1 sobe e a janela
alarga; com VINCULADO_DOIS_EXTREMOS ela alarga muito mais.
"""
from __future__ import annotations

from dataclasses import dataclass

from calc_core.estrutural.dominio import (
    DECLARADO_EM_TEXTO,
    RecusaForaDeDominio,
    exigir_positivo,
)

__all__ = [
    "FAIXA_A_ELEMENTO_LINEAR",
    "FAIXA_B_FORA_DE_14_4_1",
    "FAIXAS",
    "LIMITE_14_4_1",
    "ResultadoClassificacao",
    "razao_elemento_linear",
    "classificar_faixa",
    "frases_obrigatorias_da_faixa_B",
    "recusar_cortante_na_faixa_B",
]

FAIXA_A_ELEMENTO_LINEAR = "FAIXA_A_ELEMENTO_LINEAR"
"""razao_14_4_1 >= 3,0: é elemento linear e §17.4 é aplicável."""

FAIXA_B_FORA_DE_14_4_1 = "FAIXA_B_FORA_DE_14_4_1"
"""razao_14_4_1 < 3,0: NÃO é elemento linear e §17.4 é RECUSADO."""

FAIXAS: tuple[str, ...] = (FAIXA_A_ELEMENTO_LINEAR, FAIXA_B_FORA_DE_14_4_1)
"""Enumeração FECHADA, exposta no retorno da API (REQ-PILARETE-16-i)."""

LIMITE_14_4_1 = 3.0
"""Limite "pelo menos três vezes" de 14.4.1 [adimensional].

Ref.: ABNT NBR 6118:2023, item 14.4.1, p. 83
[rule: NBR6118-14.4.1-elemento-linear-classificacao]

NAO_DECLARADO_NA_FONTE, registrado e decidido pelo a2: "supera em pelo menos
três vezes" admite leitura ESTRITA (ell > 3·máx) e NÃO estrita
(ell >= 3·máx). Adotada a NÃO ESTRITA, que é a leitura corrente e a que a
própria redação "pelo menos" sugere. A diferença tem medida nula e o memorial
imprime a razão obtida, de modo que o engenheiro vê o caso de fronteira.

É PROIBIDO tratar o 3,0 como calibrável, arredondável ou "aproximadamente", e
é PROIBIDO inventar faixa de tolerância em torno dele.
"""


@dataclass(frozen=True)
class ResultadoClassificacao:
    """Razão de 14.4.1, faixa e o comprimento que faltou — para o memorial.

    Ref.: ABNT NBR 6118:2023, item 14.4.1, p. 83
    [rule: NBR6118-14.4.1-elemento-linear-classificacao]
    [req: REQ-PILARETE-16-escopo-do-veredito-e-o-cortante-nao-verificado]  (h, i)

    A FAIXA é CAMPO PRÓPRIO do valor de retorno, não apenas texto: um
    consumidor programático tem de poder distinguir sem interpretar string.
    """

    razao_14_4_1: float
    """ell / max(b_secao, h_secao) [adimensional]."""

    faixa: str
    """Um de :data:`FAIXAS`."""

    ell: float
    """COMPRIMENTO LONGITUDINAL REAL do pilarete [m] — nunca ell_e."""

    maior_dimensao_da_secao: float
    """max(b_secao, h_secao) [m]."""

    ell_necessario_para_faixa_A: float
    """3·max(b,h) [m] — o valor que faltou atingir, exigido na mensagem."""

    @property
    def e_elemento_linear(self) -> bool:
        """True na FAIXA A. Atalho de leitura; a FAIXA é que é o campo.

        Ref.: ABNT NBR 6118:2023, item 14.4.1, p. 83
        [rule: NBR6118-14.4.1-elemento-linear-classificacao]
        """
        return self.faixa == FAIXA_A_ELEMENTO_LINEAR


def razao_elemento_linear(*, ell: float, h_secao: float,
                          b_secao: float) -> float:
    """Razão comprimento/maior dimensão da seção [adimensional].

    Ref.: ABNT NBR 6118:2023, item 14.4.1, p. 83
    [rule: NBR6118-14.4.1-elemento-linear-classificacao]
    [req: REQ-PILARETE-17-guarda-de-elemento-linear-14.4.1]  (1)

        razao_14_4_1 = ell / max(b_secao, h_secao)

    ``ell`` É O COMPRIMENTO LONGITUDINAL REAL, e o nome do parâmetro é
    obrigatório (``ell``, nunca ``ell_e``, nunca ``L``). É PROIBIDO usar
    ``ell_e`` aqui: no caso ENGASTADO_BASE_LIVRE_TOPO ell_e = 2·ell e a razão
    DOBRA, classificando como elemento linear um pilarete de 45 cm. Erro do
    lado INSEGURO por CITAÇÃO — aplica §17.4 fora de domínio — e INVISÍVEL à
    checagem dimensional, porque a razão é adimensional nas duas leituras
    (caso EMPIRICA ``MUTANTE-14.4.1-com-ell-e-no-lugar-de-ell``). O teste de
    mutação que troca um pelo outro tem de quebrar, e o caso que pega é a
    geometria B (30×30, ell = 0,80 m): 2,667 -> FAIXA B; com ell_e daria
    5,333 -> FAIXA A.
    """
    exigir_positivo("ell", ell,
                    fonte="ABNT NBR 6118:2023, 14.4.1, p. 83",
                    apoio_no_ruleset="NBR6118-14.4.1-elemento-linear-classificacao")
    exigir_positivo("h_secao", h_secao,
                    fonte="ABNT NBR 6118:2023, 14.4.1, p. 83",
                    apoio_no_ruleset="NBR6118-14.4.1-elemento-linear-classificacao")
    exigir_positivo("b_secao", b_secao,
                    fonte="ABNT NBR 6118:2023, 14.4.1, p. 83",
                    apoio_no_ruleset="NBR6118-14.4.1-elemento-linear-classificacao")
    return ell / max(h_secao, b_secao)


def classificar_faixa(*, ell: float, h_secao: float,
                      b_secao: float) -> ResultadoClassificacao:
    """Classifica em FAIXA A / FAIXA B. NÃO levanta exceção — só classifica.

    Ref.: ABNT NBR 6118:2023, item 14.4.1, p. 83
    [rule: NBR6118-14.4.1-elemento-linear-classificacao]
    [deriv: DER-NBR6118-14.4.1-faixa-B-recusa-do-cortante]
    [req: REQ-PILARETE-17-guarda-de-elemento-linear-14.4.1]  (2)

    A classificação é SEMPRE calculada e SEMPRE vai ao memorial, nas duas
    faixas, com o número ao lado do limite 3,0. Imprimir só
    "aplicável/não aplicável" sem o número é defeito.

    Quem RECUSA é :func:`recusar_cortante_na_faixa_B`, chamada pelo módulo de
    cortante — a separação existe porque na FAIXA B a verificação de §17.2
    (N+M) SEGUE normalmente e só o cortante é recusado.

    ORDEM IMPORTA (REQ-PILARETE-17(5)): esta guarda roda DEPOIS de
    REQ-PILARETE-03 (geometria) e -05 (pilar curto) e ANTES de qualquer
    expressão de §17.4. Um V_Rd2 calculado antes de a faixa ser conhecida é
    defeito com veto do a6, mesmo que o valor nunca chegue à tela.
    """
    razao = razao_elemento_linear(ell=ell, h_secao=h_secao, b_secao=b_secao)
    maior = max(h_secao, b_secao)
    return ResultadoClassificacao(
        razao_14_4_1=razao,
        faixa=(FAIXA_A_ELEMENTO_LINEAR if razao >= LIMITE_14_4_1
               else FAIXA_B_FORA_DE_14_4_1),
        ell=ell,
        maior_dimensao_da_secao=maior,
        ell_necessario_para_faixa_A=LIMITE_14_4_1 * maior,
    )


def frases_obrigatorias_da_faixa_B(
    classificacao: ResultadoClassificacao,
) -> tuple[str, str]:
    """As DUAS frases que o memorial imprime SEMPRE na FAIXA B.

    Ref.: ABNT NBR 6118:2023, itens 14.4.1 e 17.4.1, p. 83 e 133
    [rule: NBR6118-14.4.1-elemento-linear-classificacao]
    [rule: NBR6118-17.4.1-campo-de-aplicacao-do-cortante]
    [deriv: DER-NBR6118-14.4.1-faixa-B-recusa-do-cortante]
    [req: REQ-PILARETE-16-escopo-do-veredito-e-o-cortante-nao-verificado]  (e)

    SEMPRE, e não só quando H != 0. Quando H != 0 elas são REPETIDAS junto ao
    valor de H, com o valor (alínea (f) do mesmo requisito).

    A segunda frase diz o que nenhum software gosta de dizer: que NÃO HÁ, na
    Norma, rota alternativa para este caso. A Seção 21.1 manda os elementos
    "que por sua forma ou proporções caracterizam uma descontinuidade
    generalizada" para a Seção 22, e a Seção 22 trata vigas-parede, consolos,
    dentes Gerber, sapatas, blocos e pilares-parede — NÃO trata pilarete,
    pedestal nem pilar curto de fundação. É VAZIO NORMATIVO no cortante, e
    não lacuna de escopo deste pipeline.
    """
    primeira = (
        "Este pilarete NÃO satisfaz a definição de elemento linear da "
        "NBR 6118:2023, 14.4.1 (p. 83): a razão comprimento/maior dimensão da "
        f"seção é {classificacao.razao_14_4_1:.4f}, abaixo do mínimo de 3,0 "
        f"(seriam necessários {classificacao.ell_necessario_para_faixa_A:.4f} m "
        f"de comprimento, contra os {classificacao.ell:.4f} m declarados)."
    )
    segunda = (
        "Por esse motivo o ELU de força cortante NÃO FOI VERIFICADO. A Seção "
        "17.4 da NBR 6118:2023 aplica-se a elementos lineares e exclui "
        "expressamente elementos de volume, lajes, vigas-parede e consolos "
        "curtos; a Seção 22 (elementos especiais) não trata pilarete, pedestal "
        "nem pilar curto de fundação. Não há, na Norma, rota alternativa para "
        "este caso — o cortante é responsabilidade do engenheiro, por modelo "
        "de bielas e tirantes ou outro caminho, fora deste software."
    )
    return primeira, segunda


def recusar_cortante_na_faixa_B(
    classificacao: ResultadoClassificacao,
) -> None:
    """RECUSA §17.4 na FAIXA B; não faz nada na FAIXA A.

    Ref.: ABNT NBR 6118:2023, itens 14.4.1 e 17.4.1, p. 83 e 133
    [rule: NBR6118-14.4.1-elemento-linear-classificacao]
    [rule: NBR6118-17.4.1-campo-de-aplicacao-do-cortante]
    [deriv: DER-NBR6118-14.4.1-faixa-B-recusa-do-cortante]
    [req: REQ-PILARETE-17-guarda-de-elemento-linear-14.4.1]  (3)

    LEVANTA EXCEÇÃO. NÃO devolve ``None``, NÃO devolve zero, NÃO devolve "não
    aplicável" como se fosse resultado. É PROIBIDO qualquer parâmetro, flag,
    variável de ambiente ou caixa de diálogo que permita prosseguir.

    A mensagem traz, nesta ordem: a razão OBTIDA; o limite 3,0; o valor
    3·máx(b,h) que faltou atingir, em metros; a citação de 14.4.1 com a
    página; a lista de exclusões de 17.4.1; e a constatação de que a Seção 22
    não cobre o pilarete.
    """
    if classificacao.faixa == FAIXA_A_ELEMENTO_LINEAR:
        return
    primeira, segunda = frases_obrigatorias_da_faixa_B(classificacao)
    raise RecusaForaDeDominio(
        parametro="razao_14_4_1 (ell / max(b_secao, h_secao))",
        valor=round(classificacao.razao_14_4_1, 4),
        intervalo=f">= {LIMITE_14_4_1} para ser elemento linear",
        fonte="ABNT NBR 6118:2023, 14.4.1, p. 83 — 'o comprimento longitudinal "
              "supera em pelo menos três vezes a maior dimensão da seção "
              "transversal'; e 17.4.1, p. 133 — as prescrições de §17.4 'não "
              "se aplicam a elementos de volume, lajes, vigas-parede e "
              "consolos curtos, que são tratados em outras Seções desta Norma'",
        forca=DECLARADO_EM_TEXTO,
        apoio_no_ruleset="DER-NBR6118-14.4.1-faixa-B-recusa-do-cortante",
        sugestao=primeira + " " + segunda,
    )
