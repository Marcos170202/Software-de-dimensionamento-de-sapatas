"""Correlações semiempíricas SPT → parcela de ELU da tensão admissível.

Ref.: ABNT NBR 6122:2022, item 7.3.3, p. 22
[rule: NBR6122-7.3.3-metodos-semiempiricos]

"São métodos que relacionam resultados de ensaios (tais como o SPT, CPT etc.)
com tensões admissíveis ou tensões resistentes de cálculo. Devem ser observados
os domínios de validade de suas aplicações, bem como as dispersões dos dados e
as limitações regionais associadas a cada um dos métodos."

O item é uma AUTORIZAÇÃO CONDICIONADA, não uma especificação de método: a NBR
6122:2022 não nomeia método semiempírico algum, não reproduz correlação alguma
N_SPT → sigma_adm, não traz tabela de valores e não cita autor. As fórmulas
deste módulo são de CINTRA/AOKI/ALBIERO (2011) e se citam com ``[pratica: ]``,
nunca com ``[rule: ]``. O que é normativo são as três obrigações do item, e
elas viram código:

(a) DOMÍNIO DE VALIDADE → guardas que RECUSAM, em ``geotecnico.dominio``;
(b) DISPERSÃO DOS DADOS → ``sigma_adm.semiempirico_spt`` roda todas as
    correlações aplicáveis e as devolve LADO A LADO, sem escolher;
(c) LIMITAÇÕES REGIONAIS → declaração explícita do usuário, sem default
    afirmativo, registrada no memorial.

FS EMBUTIDO. Estas correlações já trazem o seu próprio fator de segurança e é
PROIBIDO dividi-las de novo por FSg (dupla contagem). Mas "o autor disse que
embute 3" não é verificação: a Tabela 1 exige "valores propostos no próprio
processo E no mínimo 3,00", isto é, um valor VERIFICÁVEL. Por isso cada função
devolve ``FS_embutido`` e ``FS_embutido_origem`` e EXECUTA a asserção
``FS_embutido >= 3,00`` (REQ-SIGMA-02). Correlação cujo FS não seja
demonstrável não pode ser usada — é por isso que Mello (1975) NÃO está aqui.

MELLO (1975) — AUSÊNCIA DELIBERADA, NÃO ESQUECIMENTO. REQ-SIGMA-05 permite
exibir Mello na comparação como valor meramente informativo, mas a formulação
``FB-MELLO-1975-sigma-adm-SPT`` está PENDENTE_HUMANO no ruleset (a fonte não
declara FS algum, não imprime dedução e não distingue tipo de solo), e a regra
2 do CLAUDE.md é categórica: nada entra em ``calc_core/`` sem regra APROVADA
correspondente. A permissão de REQ-SIGMA-05 é facultativa; a proibição do
CLAUDE.md não é. Fica de fora até que o a2 aprove.
"""
from __future__ import annotations

from calc_core.geotecnico.dominio import (
    ADOTADO_DA_EXTENSAO_DE_FIGURA,
    DECLARADO_EM_TEXTO,
    ForaDoDominioError,
    exigir_declaracao,
    exigir_igualdade,
    exigir_intervalo,
    exigir_um_de,
)
from calc_core.geotecnico.seguranca import (
    FSG_MINIMO_SEMIEMPIRICOS,
    METODO_DE_SEGURANCA_DESTA_VERSAO,
    exigir_metodo_admissivel,
)
from calc_core.modelos import (
    ADVERTENCIA_FORMULARIOS_DE_BOLSO,
    DECLARACAO_REGIONAL_EXIGIDA,
    FORMA_QUADRADA,
    FORMA_RETANGULAR,
    ROTULO_ELU,
    ROTULO_FONTE_NAO_NORMATIVA,
    ResultadoSigmaAdmELU,
)

KPA_POR_MPA = 1000.0
"""Conversão MPa → kPa, aplicada num ÚNICO ponto por função (REQ-SIGMA-03).

As duas fórmulas deste módulo estão publicadas em MPa e todas as funções da v9
devolvem kPa na fronteira do módulo. A conversão não pode ficar espalhada.
"""

SOLO_ARGILA = "argila"
SOLO_AREIA = "areia"

# --- regra brasileira sigma_a = N_SPT/50 (argila) --------------------------
NSPT_MINIMO_REGRA_50 = 5.0
NSPT_MAXIMO_REGRA_50 = 20.0
DIVISOR_REGRA_50 = 50.0
FS_EMBUTIDO_REGRA_50 = 3.0
FS_EMBUTIDO_ORIGEM_REGRA_50 = (
    "álgebra EXATA sobre a dedução que a fonte imprime (impressa 112): "
    "sigma_r = c·Nc com Nc = 6 (Skempton, 1951) e c = 0,01·N_SPT [MPa]; "
    "sigma_a = (0,01·N_SPT·6)/3 = 0,02·N_SPT = N_SPT/50. O '3' está "
    "literalmente no denominador da equação impressa, e "
    "sigma_r/sigma_a = 0,06·N/0,02·N = 3,0000 exato para qualquer N_SPT."
)
NOME_REGRA_50 = (
    "regra brasileira sigma_a = N_SPT/50, demonstrada por Teixeira (1996) "
    "para argila"
)
"""Rótulo obrigatório no memorial.

A fonte apresenta a expressão como "regra conhecida no meio técnico
brasileiro", e NÃO como "o método de Teixeira" — o papel de Teixeira aqui é o
de ter demonstrado a regra para um caso particular. O "método de Teixeira"
propriamente dito é o de AREIA, e é a outra função deste módulo.
"""

# --- Teixeira (1996), areia ------------------------------------------------
NSPT_MINIMO_TEIXEIRA = 4.0
NSPT_MAXIMO_TEIXEIRA = 25.0
B_MINIMO_TEIXEIRA_M = 1.0
B_MAXIMO_TEIXEIRA_M = 3.0
H_CONGELADO_TEIXEIRA_M = 1.5
GAMMA_CONGELADO_TEIXEIRA_KN_M3 = 18.0
FS_EMBUTIDO_TEIXEIRA = 3.0
FS_EMBUTIDO_ORIGEM_TEIXEIRA = (
    "piso VERIFICADO por reconstrução numérica independente do a2 (v9): "
    "partindo dos parâmetros congelados declarados (h = 1,5 m, "
    "gamma = 18 kN/m³, sapata quadrada, phi = sqrt(20·N_SPT) + 15°, c = 0), "
    "recalculou-se sigma_r por Terzaghi e comparou-se com a fórmula "
    "publicada: FS implícito entre 3,05 (N = 5, B = 1 m) e 4,55 (N = 25, "
    "B = 3 m), sempre >= 3,00. Registra-se 3,0 como piso conservador — a "
    "fórmula publicada é uma LINEARIZAÇÃO e o FS implícito cresce com N_SPT."
)
NOME_TEIXEIRA = "método de Teixeira (1996) para areia"

_FONTE_REGRA_50 = ("CINTRA/AOKI/ALBIERO (2011), item 4.1.2 a), impressa 112 — "
                   "faixa 5 <= N_SPT <= 20 declarada EM TEXTO")
_FONTE_TEIXEIRA = ("CINTRA/AOKI/ALBIERO (2011), item 4.1.2 a), impressa 113, "
                   "com Fig. 4.1")
_APOIO_REGRA_50 = ("ruleset.yaml > FB-REGRA-BRASILEIRA-Nspt-50-argila > "
                   "dominio_de_validade; REQ-SIGMA-04")
_APOIO_TEIXEIRA = ("ruleset.yaml > FB-TEIXEIRA-1996-areia > "
                   "dominio_de_validade; REQ-SIGMA-04")

Q_MPA_MAXIMO_PLAUSIVEL = 1.0
"""Teto de plausibilidade de ``q_MPa``, guarda de UNIDADE (REQ-SIGMA-03 a).

Não é domínio da fonte: é a rede contra o erro de fator 1000. Como o termo
"+ q" já é uma tensão, passar q em kPa em vez de MPa não quebra dimensão
alguma — os dois termos são "tensão" — e nenhuma checagem dimensional acusa.
1,0 MPa de sobrecarga geostática corresponde a mais de 50 m de solo acima da
cota de apoio, o que não é sapata. Esta guarda RECUSA; nunca converte por
conta própria.
"""


def _exigir_declaracao_regional(declarada: bool, fonte: str, apoio: str) -> None:
    """Obrigação (c) do §7.3.3: limitações regionais declaradas (REQ-SIGMA-06)."""
    exigir_declaracao(
        "aplicabilidade_regional_declarada", declarada,
        exigencia=DECLARACAO_REGIONAL_EXIGIDA, fonte=fonte,
        apoio_no_ruleset=apoio + "; REQ-SIGMA-06",
        sugestao=DECLARACAO_REGIONAL_EXIGIDA,
    )


def _conferir_FS_embutido(FS_embutido: float, nome: str) -> float:
    """Executa a asserção ``FS_embutido >= 3,00`` exigida por REQ-SIGMA-02.

    Ref.: ABNT NBR 6122:2022, item 6.2.1.1.1 e Tabela 1, p. 17
    [rule: NBR6122-6.2.1.1.1-fatores-seguranca-tabela1]

    A Tabela 1 exige, para semiempíricos, "valores propostos no próprio
    processo E no mínimo 3,00". Um número que só existe em prosa de ruleset
    não é verificável em produção: a conferência roda a cada chamada.
    """
    if FS_embutido < FSG_MINIMO_SEMIEMPIRICOS:
        raise AssertionError(
            f"{nome}: FS_embutido = {FS_embutido} < "
            f"{FSG_MINIMO_SEMIEMPIRICOS} exigido pela linha 'Semiempíricos' da "
            "Tabela 1 da NBR 6122:2022. Correlação sem FS embutido "
            "demonstrável não pode ser usada (REQ-SIGMA-02)."
        )
    return FS_embutido


def regra_brasileira_nspt_50_argila(
    *,
    N_spt_medio_bulbo: float,
    forma: str,
    solo_declarado: str,
    aplicabilidade_regional_declarada: bool,
    considerar_q: bool = False,
    q_MPa: float | None = None,
    metodo_de_seguranca: str = METODO_DE_SEGURANCA_DESTA_VERSAO,
) -> ResultadoSigmaAdmELU:
    """sigma_a = N_SPT/50 (+ q) [MPa] em terreno puramente argiloso.

    Ref.: ABNT NBR 6122:2022, item 7.3.3, p. 22
    [rule: NBR6122-7.3.3-metodos-semiempiricos] (autoriza o PROCEDIMENTO)

    Ref.: ABNT NBR 6122:2022, itens 7.3 e 7.4, p. 22-23
    [rule: NBR6122-7.3-7.4-conjuncao-ELU-ELS] (rótulo obrigatório da saída)

    [pratica: FB-REGRA-BRASILEIRA-Nspt-50-argila] (a FÓRMULA, de fonte
    bibliográfica NÃO normativa)

    Devolve a PARCELA DE ELU da tensão admissível, em kPa. Nunca "a tensão
    admissível": o §7.4 (ELS/recalque) não é verificado por caminho algum
    desta versão.

    DOMÍNIO, todo ele recusando (REQ-SIGMA-04):

    * 5 <= ``N_spt_medio_bulbo`` <= 20 — faixa DECLARADA EM TEXTO na fonte;
    * ``solo_declarado`` = 'argila' — a dedução é para terreno PURAMENTE
      argiloso, e nada de silte, areia argilosa ou perfil estratificado;
    * ``forma`` retangular ou quadrada;
    * ``aplicabilidade_regional_declarada`` = True, sem default.

    N_SPT É O VALOR MÉDIO NO BULBO DE TENSÕES, não o valor na cota de apoio —
    daí o nome do parâmetro. É erro provável de wiring e nada no cálculo o
    denuncia: o resultado sai plausível dos dois jeitos.

    A PARCELA "+ q" É FACULTATIVA e vem desligada. A fonte diz que ela "pode
    ou não ser considerada" e a dedução que a sustenta é para sapata na
    SUPERFÍCIE (h = 0), onde q seria zero; a fonte não concilia as duas coisas
    e o software não arbitra. Ligar q só pode AUMENTAR sigma_a, logo o default
    é o lado seguro (REQ-SIGMA-13). Quando ligada, ``q_MPa`` entra em MPa —
    o nome carrega a unidade porque passar kPa aqui é erro de fator 1000 que
    nenhuma checagem dimensional acusa (REQ-SIGMA-03 a).
    """
    exigir_metodo_admissivel(metodo_de_seguranca)
    exigir_intervalo(
        "N_spt_medio_bulbo", N_spt_medio_bulbo, NSPT_MINIMO_REGRA_50,
        NSPT_MAXIMO_REGRA_50, fonte=_FONTE_REGRA_50, forca=DECLARADO_EM_TEXTO,
        apoio_no_ruleset=_APOIO_REGRA_50,
        sugestao=("A fonte não autoriza a fórmula fora dessa faixa — escolha "
                  "outro método ou informe outro N_SPT. Fora da faixa o "
                  "resultado degenera depressa: N_SPT = 50 daria 1000 kPa."),
    )
    exigir_um_de(
        "solo_declarado", solo_declarado, (SOLO_ARGILA,),
        fonte=_FONTE_REGRA_50, forca=DECLARADO_EM_TEXTO,
        apoio_no_ruleset=_APOIO_REGRA_50,
        sugestao=("A dedução é para terreno PURAMENTE ARGILOSO (capacidade de "
                  "carga por Skempton com Nc = 6). Não vale para areia, "
                  "silte, solo intermediário ou perfil estratificado."),
    )
    exigir_um_de(
        "forma", forma, (FORMA_QUADRADA, FORMA_RETANGULAR),
        fonte=_FONTE_REGRA_50, forca=DECLARADO_EM_TEXTO,
        apoio_no_ruleset=_APOIO_REGRA_50,
        sugestao="A dedução é para sapata retangular (inclui quadrada).",
    )
    _exigir_declaracao_regional(aplicabilidade_regional_declarada,
                                _FONTE_REGRA_50, _APOIO_REGRA_50)

    avisos = [ADVERTENCIA_FORMULARIOS_DE_BOLSO, DECLARACAO_REGIONAL_EXIGIDA,
              ("N_SPT informado é o valor MÉDIO NO BULBO DE TENSÕES, não o "
              "valor na cota de apoio (domínio (7) declarado pela fonte).")]

    q_usado_MPa = _q_da_regra_50(considerar_q, q_MPa, avisos)

    sigma_a_MPa = N_spt_medio_bulbo / DIVISOR_REGRA_50 + q_usado_MPa
    FS = _conferir_FS_embutido(FS_EMBUTIDO_REGRA_50, NOME_REGRA_50)

    return ResultadoSigmaAdmELU(
        sigma_adm_ELU_kPa=sigma_a_MPa * KPA_POR_MPA,
        metodo="semiempirico",
        nome_do_metodo=NOME_REGRA_50,
        metodo_de_seguranca=metodo_de_seguranca,
        rotulo_ELU=ROTULO_ELU,
        rotulo_fonte=ROTULO_FONTE_NAO_NORMATIVA,
        regras=("NBR6122-7.3.3-metodos-semiempiricos",
                "NBR6122-7.3-7.4-conjuncao-ELU-ELS",
                "NBR6122-6.2.1.1.1-fatores-seguranca-tabela1"),
        praticas=("FB-REGRA-BRASILEIRA-Nspt-50-argila",),
        FSg_aplicado=None,
        FS_embutido=FS,
        FS_embutido_origem=FS_EMBUTIDO_ORIGEM_REGRA_50,
        memoria={
            "N_spt_medio_bulbo": float(N_spt_medio_bulbo),
            "divisor": DIVISOR_REGRA_50,
            "q_MPa": q_usado_MPa,
            "sigma_a_MPa": sigma_a_MPa,
        },
        avisos=tuple(avisos),
    )


def teixeira_1996_areia(
    *,
    N_spt: float,
    B_m: float,
    forma: str,
    solo_declarado: str,
    h_m: float,
    gamma_kN_m3: float,
    aplicabilidade_regional_declarada: bool,
    metodo_de_seguranca: str = METODO_DE_SEGURANCA_DESTA_VERSAO,
) -> ResultadoSigmaAdmELU:
    """sigma_a = 0,05 + (1 + 0,4·B)·N_SPT/100 [MPa], sapata quadrada em areia.

    Ref.: ABNT NBR 6122:2022, item 7.3.3, p. 22
    [rule: NBR6122-7.3.3-metodos-semiempiricos] (autoriza o PROCEDIMENTO)

    Ref.: ABNT NBR 6122:2022, itens 7.3 e 7.4, p. 22-23
    [rule: NBR6122-7.3-7.4-conjuncao-ELU-ELS] (rótulo obrigatório da saída)

    [pratica: FB-TEIXEIRA-1996-areia] (a FÓRMULA, de fonte bibliográfica NÃO
    normativa; a referência primária — TEIXEIRA, SEFE III, 1996 — está ausente
    do acervo e esta é reprodução de segunda mão)

    Devolve a PARCELA DE ELU da tensão admissível, em kPa.

    PARÂMETROS CONGELADOS NA DEDUÇÃO — não são variáveis da fórmula, e é o que
    torna este domínio tão estreito. ``h_m`` e ``gamma_kN_m3`` são pedidos
    justamente para poderem ser RECUSADOS quando diferirem, com TOLERÂNCIA
    ZERO: h = 1,5 m exatos e gamma = 18 kN/m³ exatos. Medido pelo a2, variar
    só o h move o resultado de −39 % (h = 0,5 m, lado INSEGURO) a +59 %
    (h = 3,0 m); gamma ±2 kN/m³ move ±11 %. A fórmula publicada não tem h como
    variável: usá-la com outro h não é "extrapolar um pouco", é usar um número
    calculado para outra situação.

    FAIXAS NUMÉRICAS DE FORÇA MENOR: 1,0 <= ``B_m`` <= 3,0 e 4 <= ``N_spt``
    <= 25 NÃO estão declaradas em texto na fonte — vêm da EXTENSÃO da Fig. 4.1
    (eixo de N_SPT de 0 a 25, curvas B = 1, 2 e 3 m) e foram adotadas pelo a2.
    Recusam igual, mas são revisáveis por decisão humana (kb/pendencias.md >
    V3). A guarda de B também é a guarda de unidade: B em centímetros produz
    número grande e plausível sem nenhum erro dimensional (REQ-SIGMA-03 b).

    A fonte NÃO declara em que profundidade N_SPT é amostrado para esta
    correlação — ao contrário da regra N/50, que fixa a média no bulbo. O
    parâmetro chama-se ``N_spt`` por isso, e a lacuna vai nos avisos.
    """
    exigir_metodo_admissivel(metodo_de_seguranca)
    exigir_um_de(
        "solo_declarado", solo_declarado, (SOLO_AREIA,),
        fonte=_FONTE_TEIXEIRA, forca=DECLARADO_EM_TEXTO,
        apoio_no_ruleset=_APOIO_TEIXEIRA,
        sugestao=("A dedução é para AREIA. Não silte, não areia argilosa, não "
                  "solo intermediário."),
    )
    exigir_um_de(
        "forma", forma, (FORMA_QUADRADA,),
        fonte=_FONTE_TEIXEIRA, forca=DECLARADO_EM_TEXTO,
        apoio_no_ruleset=_APOIO_TEIXEIRA,
        sugestao="A dedução é para sapata QUADRADA de lado B (B = L).",
    )
    exigir_igualdade(
        "h_m", h_m, H_CONGELADO_TEIXEIRA_M, fonte=_FONTE_TEIXEIRA,
        forca=DECLARADO_EM_TEXTO, apoio_no_ruleset=_APOIO_TEIXEIRA,
        sugestao=("h é hipótese CONGELADA da dedução, não variável da fórmula. "
                  "Tolerância zero até decisão humana (kb/pendencias.md > V3): "
                  "h = 0,5 m tornaria o uso INSEGURO em até 39 %."),
    )
    exigir_igualdade(
        "gamma_kN_m3", gamma_kN_m3, GAMMA_CONGELADO_TEIXEIRA_KN_M3,
        fonte=_FONTE_TEIXEIRA, forca=DECLARADO_EM_TEXTO,
        apoio_no_ruleset=_APOIO_TEIXEIRA,
        sugestao=("gamma é hipótese CONGELADA da dedução. Tolerância zero até "
                  "decisão humana: ±2 kN/m³ movem o resultado ±11 %."),
    )
    exigir_intervalo(
        "B_m", B_m, B_MINIMO_TEIXEIRA_M, B_MAXIMO_TEIXEIRA_M,
        fonte=_FONTE_TEIXEIRA + " — extensão das curvas B = 1, 2 e 3 m",
        forca=ADOTADO_DA_EXTENSAO_DE_FIGURA,
        apoio_no_ruleset=_APOIO_TEIXEIRA,
        sugestao=("Limite ADOTADO pelo a2 a partir da extensão da Fig. 4.1, "
                  "não declarado em texto na fonte — é revisável por decisão "
                  "humana. B entra em METROS: B = 200 (cm) daria 12,2 MPa."),
    )
    exigir_intervalo(
        "N_spt", N_spt, NSPT_MINIMO_TEIXEIRA, NSPT_MAXIMO_TEIXEIRA,
        fonte=_FONTE_TEIXEIRA + " — extensão do eixo N_SPT (0 a 25)",
        forca=ADOTADO_DA_EXTENSAO_DE_FIGURA,
        apoio_no_ruleset=_APOIO_TEIXEIRA,
        sugestao=("Limite ADOTADO pelo a2 a partir da extensão da Fig. 4.1, "
                  "não declarado em texto — revisável por decisão humana. A "
                  "concordância com Terzaghi degrada monotonicamente com "
                  "N_SPT, o que sugere que o domínio útil termina onde a "
                  "figura termina."),
    )
    _exigir_declaracao_regional(aplicabilidade_regional_declarada,
                                _FONTE_TEIXEIRA, _APOIO_TEIXEIRA)

    sigma_a_MPa = 0.05 + (1.0 + 0.4 * B_m) * N_spt / 100.0
    FS = _conferir_FS_embutido(FS_EMBUTIDO_TEIXEIRA, NOME_TEIXEIRA)

    return ResultadoSigmaAdmELU(
        sigma_adm_ELU_kPa=sigma_a_MPa * KPA_POR_MPA,
        metodo="semiempirico",
        nome_do_metodo=NOME_TEIXEIRA,
        metodo_de_seguranca=metodo_de_seguranca,
        rotulo_ELU=ROTULO_ELU,
        rotulo_fonte=ROTULO_FONTE_NAO_NORMATIVA,
        regras=("NBR6122-7.3.3-metodos-semiempiricos",
                "NBR6122-7.3-7.4-conjuncao-ELU-ELS",
                "NBR6122-6.2.1.1.1-fatores-seguranca-tabela1"),
        praticas=("FB-TEIXEIRA-1996-areia",),
        FSg_aplicado=None,
        FS_embutido=FS,
        FS_embutido_origem=FS_EMBUTIDO_ORIGEM_TEIXEIRA,
        memoria={
            "N_spt": float(N_spt),
            "B_m": float(B_m),
            "h_congelado_m": H_CONGELADO_TEIXEIRA_M,
            "gamma_congelado_kN_m3": GAMMA_CONGELADO_TEIXEIRA_KN_M3,
            "sigma_a_MPa": sigma_a_MPa,
        },
        avisos=(
            ADVERTENCIA_FORMULARIOS_DE_BOLSO,
            DECLARACAO_REGIONAL_EXIGIDA,
            ("Parâmetros CONGELADOS na dedução e verificados por igualdade "
            f"estrita: h = {H_CONGELADO_TEIXEIRA_M} m e "
            f"gamma = {GAMMA_CONGELADO_TEIXEIRA_KN_M3} kN/m³. A correlação de "
            "phi (phi = sqrt(20·N_SPT) + 15°, de Teixeira) já está dentro das "
            "constantes 0,05/0,4/100 e não pode ser substituída."),
            ("A fonte NÃO declara a profundidade de amostragem de N_SPT para "
            "esta correlação (ao contrário da regra N/50, que fixa a média no "
            "bulbo). Registrar no memorial de onde veio o valor informado."),
            ("Reprodução de SEGUNDA MÃO: a referência primária (TEIXEIRA, "
            "A. H., SEFE III, 1996) está ausente do acervo. O que foi "
            "verificado é a aritmética, por reconstrução independente."),
        ),
    )


def _q_da_regra_50(considerar_q: bool, q_MPa: float | None,
                   avisos: list[str]) -> float:
    """Resolve a parcela facultativa "+ q" da regra N/50 (REQ-SIGMA-13)."""
    if not considerar_q:
        if q_MPa not in (None, 0.0):
            raise ValueError(
                f"q_MPa = {q_MPa} informado com considerar_q=False. A parcela "
                "'+ q' é FACULTATIVA e vem DESLIGADA por default; ignorá-la em "
                "silêncio esconderia a discordância. Ligue considerar_q=True "
                "se quiser somá-la."
            )
        return 0.0
    if q_MPa is None:
        raise ValueError(
            "considerar_q=True exige q_MPa explícito, em MEGAPASCAL. O termo "
            "'+ q' já é uma tensão: passar kPa aqui produz erro de fator 1000 "
            "que nenhuma checagem dimensional acusa (REQ-SIGMA-03 a)."
        )
    if q_MPa < 0.0:
        raise ValueError(f"q_MPa = {q_MPa}: sobrecarga não pode ser negativa.")
    if q_MPa > Q_MPA_MAXIMO_PLAUSIVEL:
        raise ForaDoDominioError(
            parametro="q_MPa", valor=q_MPa,
            intervalo=f"0 a {Q_MPA_MAXIMO_PLAUSIVEL} MPa",
            fonte=("guarda de UNIDADE, não domínio da fonte: sobrecarga acima "
                   "de 1 MPa corresponderia a mais de 50 m de solo acima da "
                   "cota de apoio"),
            forca=DECLARADO_EM_TEXTO,
            apoio_no_ruleset="REQ-SIGMA-03 (a) — guarda de unidade",
            sugestao=("O parâmetro é q_MPa, em MEGAPASCAL. Se o valor veio em "
                      "kPa, divida por 1000 antes de passá-lo — o software "
                      "não converte por conta própria."),
        )
    avisos.append(
        f"Parcela '+ q' = {q_MPa} MPa LIGADA por escolha explícita. É "
        "acréscimo NÃO sustentado pela dedução da fonte, que vale para sapata "
        "na SUPERFÍCIE (h = 0), onde q seria zero. A fonte exibe o termo e o "
        "declara facultativo sem conciliar as duas coisas; o software não "
        "arbitra (REQ-SIGMA-13)."
    )
    return q_MPa


__all__ = [
    "B_MAXIMO_TEIXEIRA_M",
    "B_MINIMO_TEIXEIRA_M",
    "FS_EMBUTIDO_REGRA_50",
    "FS_EMBUTIDO_TEIXEIRA",
    "GAMMA_CONGELADO_TEIXEIRA_KN_M3",
    "H_CONGELADO_TEIXEIRA_M",
    "KPA_POR_MPA",
    "NOME_REGRA_50",
    "NOME_TEIXEIRA",
    "NSPT_MAXIMO_REGRA_50",
    "NSPT_MAXIMO_TEIXEIRA",
    "NSPT_MINIMO_REGRA_50",
    "NSPT_MINIMO_TEIXEIRA",
    "SOLO_AREIA",
    "SOLO_ARGILA",
    "regra_brasileira_nspt_50_argila",
    "teixeira_1996_areia",
]
