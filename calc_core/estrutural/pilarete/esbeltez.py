"""Momento mínimo de 1ª ordem, comprimento equivalente e esbeltez do pilarete.

Ref.: ABNT NBR 6118:2023, item 11.3.3.4.3, p. 60
[rule: NBR6118-11.3.3.4.3-momento-minimo-pilarete]

Ref.: ABNT NBR 6118:2023, item 16.3, p. 116
[rule: NBR6118-16.3-proibicao-de-carga-centrada]

Ref.: ABNT NBR 6118:2023, itens 15.4.4, 15.6, 15.8.1 e 15.8.2, p. 103-108
[rule: NBR6118-15.4.4-elementos-isolados]
[rule: NBR6118-15.6-comprimento-equivalente]
[rule: NBR6118-15.8.1-campo-de-aplicacao-esbeltez]
[rule: NBR6118-15.8.2-dispensa-2a-ordem-local]

[req: REQ-PILARETE-04-M1d-min-obrigatorio-nas-duas-direcoes]
[req: REQ-PILARETE-05-esbeltez-com-recusa-fora-do-pilar-curto]

O QUE ESTE MÓDULO NÃO CONTÉM, e a ausência é deliberada e verificável: nada
de 15.8.3 (métodos de 2ª ordem local — regra REJEITADA), nada de ``gamma_n1``
(majoração de 15.8.1 para lambda > 140) e nada de ``M_d_tot_min_*`` (Figura
15.2, envoltória mínima COM 2ª ordem — regra REJEITADA). Encontrar qualquer
um deles implementado aqui é VETO do a6.
"""
from __future__ import annotations

from dataclasses import dataclass

from calc_core.estrutural.dominio import (
    DECLARADO_EM_TEXTO,
    DECLARADO_PELO_USUARIO,
    ESCOPO_DESTA_VERSAO,
    RecusaForaDeDominio,
    exigir_positivo,
    exigir_um_de,
)
from calc_core.estrutural.pilarete.geometria import raio_de_giracao

__all__ = [
    "VINCULACOES",
    "ENGASTADO_BASE_LIVRE_TOPO",
    "VINCULADO_DOIS_EXTREMOS",
    "ALPHA_B_PILARETE",
    "FRASE_16_3",
    "momento_minimo_1a_ordem",
    "excentricidade_de_1a_ordem",
    "classificar_elemento_isolado",
    "comprimento_equivalente",
    "verificar_campo_de_aplicacao_15_8",
    "indice_de_esbeltez",
    "limite_lambda1",
    "EsbeltezPorDirecao",
    "ResultadoEsbeltez",
    "verificar_pilar_curto",
]

ENGASTADO_BASE_LIVRE_TOPO = "ENGASTADO_BASE_LIVRE_TOPO"
"""Pilarete em balanço: ell_e = 2·ell, escrito na própria Norma (15.8.2)."""

VINCULADO_DOIS_EXTREMOS = "VINCULADO_DOIS_EXTREMOS"
"""Topo vinculado: ell_e é ENTRADA NUMÉRICA, com ell_0 e ell declarados (15.6)."""

VINCULACOES: tuple[str, ...] = (
    ENGASTADO_BASE_LIVRE_TOPO, VINCULADO_DOIS_EXTREMOS,
)
"""Enumeração FECHADA de vinculação. Não há terceira opção nem valor inferido."""

ALPHA_B_PILARETE = 1.0
"""alpha_b = 1,0 pelas alíneas c) e d) de 15.8.2.

Ref.: ABNT NBR 6118:2023, item 15.8.2, alíneas c) e d), p. 108
[rule: NBR6118-15.8.2-dispensa-2a-ordem-local]

Alínea c) — pilares em BALANÇO; alínea d) — pilares com momentos MENORES que
o momento mínimo de 11.3.3.4.3. As duas cobrem o pilarete desta feature e as
duas dão 1,0. O motivo é registrado no memorial.

NOME COMPLETO OBRIGATÓRIO: ``alpha_b`` (15.8.2) x ``alpha_c`` (17.2.2, já em
``materiais.py``). Jamais abreviar para ``alpha`` — REQ-PILARETE-01.
"""

FRASE_16_3 = (
    "A NBR 6118:2023, 16.3 (p. 116), estabelece em parágrafo próprio e "
    "literal: \"Deve-se observar, também, que não se aceita o dimensionamento "
    "de pilares para carga centrada\". Por isso este software NÃO expõe "
    "caminho de compressão centrada: o momento mínimo de 1ª ordem de "
    "11.3.3.4.3 é calculado nas DUAS direções, sempre, mesmo quando o motor "
    "geotécnico chama o caso de \"carga centrada\" e passa M = 0."
)
"""Frase obrigatória do memorial (REQ-PILARETE-12-b), com item e página."""


def momento_minimo_1a_ordem(N_d: float, dimensao_no_plano_de_flexao_m: float) -> float:
    """Momento mínimo de 1ª ordem numa direção [kN·m].

    Ref.: ABNT NBR 6118:2023, item 11.3.3.4.3, p. 60, e Figura 11.3, p. 61
    [rule: NBR6118-11.3.3.4.3-momento-minimo-pilarete]
    [rule: NBR6118-11.3.3.4.3-fig11.3-envoltoria-minima-1a-ordem]
    [rule: NBR6118-16.3-proibicao-de-carga-centrada]

        M_1d,mín = N_d·(0,015 + 0,03·h),  com h em METROS

    GUARDA DE UNIDADE, e ela é obrigatória porque a análise dimensional NÃO
    pega o erro: a expressão não é homogênea como escrita — o 0,015 carrega
    METROS e o 0,03 é puro. ``h`` em centímetros produz número plausível
    (30 cm daria M = 0,915·N_d em vez de 0,024·N_d). Daí o sufixo ``_m`` no
    nome do parâmetro e a faixa validada abaixo.

    CRUZAMENTO EIXO↔DIMENSÃO, desambiguado pela Figura 11.3 e OBRIGATÓRIO:

        M_1d,mín,xx = N_d·(0,015 + 0,03·**h**)   (flexão no plano de h)
        M_1d,mín,yy = N_d·(0,015 + 0,03·**b**)   (flexão no plano de b)

    Cada momento mínimo usa a dimensão da seção medida NO PLANO EM QUE ELE
    FLEXIONA. O registro genérico do texto ("h é a altura total da seção na
    direção considerada") não desambigua; a FIGURA, sim — o croqui traz a
    seta horizontal rotulada com h e a vertical com b. Em seção QUADRADA a
    troca é invisível, e é por isso que o teste que a pega usa 20×40 cm.

    HIPÓTESE DECLARADA (``observacao`` da regra): a Norma diz que o efeito das
    imperfeições locais "PODE ser substituído" pelo momento mínimo, em
    estruturas reticuladas. Um pilarete isolado sob base metálica pode não ser
    parte de estrutura reticulada; o a2 aprovou a aplicação assim mesmo por
    razão QUANTITATIVA: pela rota alternativa de 11.3.3.4.2 (falta de
    retilineidade, theta_1 <= 1/200, e_a = theta_1·H/2), um pilarete de
    H = 1,0 m daria e_a = 2,5 mm contra os 24 mm de M_1d,mín — a substituição
    adotada é ~10× MAIS conservadora. Vai ao memorial.
    """
    exigir_positivo("N_d", N_d, permitir_zero=True,
                    fonte="ABNT NBR 6118:2023, 11.3.3.4.3, p. 60",
                    apoio_no_ruleset="NBR6118-11.3.3.4.3-momento-minimo-pilarete")
    if not (0.14 <= dimensao_no_plano_de_flexao_m <= 5.0):
        raise RecusaForaDeDominio(
            parametro="dimensao_no_plano_de_flexao_m",
            valor=dimensao_no_plano_de_flexao_m,
            intervalo="0,14 m a 5,00 m (guarda de UNIDADE: o valor é em METROS)",
            fonte="ABNT NBR 6118:2023, 11.3.3.4.3, p. 60 — a expressão "
                  "M_1d,mín = N_d·(0,015 + 0,03·h) NÃO é homogênea: o 0,015 "
                  "carrega metros; h em centímetros dá número plausível e "
                  "errado. Piso de 0,14 m por 13.2.3",
            forca=DECLARADO_EM_TEXTO,
            apoio_no_ruleset="NBR6118-11.3.3.4.3-momento-minimo-pilarete",
            sugestao="Passe a dimensão da seção em METROS.",
        )
    return N_d * (0.015 + 0.03 * dimensao_no_plano_de_flexao_m)


def excentricidade_de_1a_ordem(M_1d: float, M_1d_min: float, N_d: float) -> float:
    """Excentricidade de 1ª ordem ``e_1`` para o cálculo de lambda_1 [m].

    Ref.: ABNT NBR 6118:2023, item 15.8.2, p. 107-108
    [deriv: DER-NBR6118-15.8.2-e1-de-M1d-min]

        e_1 = max(|M_1d| , M_1d,mín) / N_d

    A Norma NÃO escreve como obter ``e_1`` quando o momento de 1ª ordem é nulo
    e só existe M_1d,mín — converter momento em excentricidade por e = M/N é o
    passo do agente, daí o ``[deriv: ]``.

    TENSÃO INTERNA DA NORMA, registrada e não escondida: 15.8.2 diz que e_1
    "não inclui a excentricidade acidental" (simbologia de 15.1), e M_1d,mín
    É a substituição das imperfeições locais. O a2 adota assim mesmo porque a
    própria alínea d) de 15.8.2 remete a 11.3.3.4.3 — a Norma casa os dois
    itens — e porque o efeito é irrelevante (ver abaixo).

    ACHADO QUE VIRA TESTE DE INVARIÂNCIA: sob M_1d,mín apenas,
    ``e_1 = 0,015 + 0,03·h`` NÃO DEPENDE de N_d (o N_d cancela), logo
    ``e_1/h = 0,015/h + 0,03`` é função só de h; em toda a faixa admissível
    (0,14 m a 2,00 m) o lambda_1 bruto fica entre 25,47 e 26,71 — SEMPRE
    abaixo de 35, logo SEMPRE truncado em 35. É teorema sobre o domínio, não
    coincidência do caso testado, e mesmo assim continua PROIBIDO fixar 35 no
    código: basta o M de 1ª ordem REAL superar M_1d,mín para lambda_1 subir.

    Este ``e_1`` serve SÓ para lambda_1. É PROIBIDO usá-lo como excentricidade
    de projeto na verificação de seção — para isso vale M_1d,mín diretamente
    (``nao_autorizado`` da derivação).
    """
    exigir_positivo("N_d", N_d,
                    fonte="ABNT NBR 6118:2023, 15.8.2, p. 107",
                    apoio_no_ruleset="DER-NBR6118-15.8.2-e1-de-M1d-min")
    return max(abs(M_1d), M_1d_min) / N_d


def classificar_elemento_isolado(vinculacao: str) -> str:
    """Classifica o pilarete como elemento isolado (15.4.4) e devolve o motivo.

    Ref.: ABNT NBR 6118:2023, item 15.4.4, alínea a), p. 103
    [rule: NBR6118-15.4.4-elementos-isolados]
    [req: REQ-PILARETE-05-esbeltez-com-recusa-fora-do-pilar-curto]  (2)

    Classificação PRÉVIA e OBRIGATÓRIA para poder aplicar 15.8. Só a alínea
    a) — "elementos estruturais isostáticos" — está autorizada, e é onde cai o
    pilarete engastado na base e livre no topo: ele é isostático por
    construção. O software marca esse caso sozinho.

    As alíneas b), c) e d) dependem de informação sobre a ESTRUTURA ACIMA
    (contraventado, estrutura de contraventamento, nós móveis) que este
    software NÃO possui e NÃO pode inferir de N/M/H na base do pilar
    metálico. Se o usuário declarar o topo vinculado, a classificação passa a
    ser DECLARADO_PELO_USUARIO e ell_e vira entrada explícita. Nunca inferir.
    """
    exigir_um_de("vinculacao", vinculacao, VINCULACOES,
                 fonte="ABNT NBR 6118:2023, 15.4.4, p. 103",
                 apoio_no_ruleset="NBR6118-15.4.4-elementos-isolados")
    if vinculacao == ENGASTADO_BASE_LIVRE_TOPO:
        return ("elemento isolado por 15.4.4, alínea a) — isostático por "
                "construção (engastado na base, livre no topo). Classificação "
                "feita pelo software, com o motivo registrado.")
    return ("elemento isolado DECLARADO PELO USUÁRIO — as alíneas b), c) e d) "
            "de 15.4.4 dependem de informação sobre a estrutura acima que este "
            "software não possui e não infere de N/M/H na base do pilar "
            "metálico.")


def comprimento_equivalente(*, vinculacao: str, ell: float,
                            ell_e_declarado: float | None = None,
                            ell_0: float | None = None,
                            h_secao: float | None = None) -> float:
    """Comprimento equivalente ell_e [m], por vinculação DECLARADA.

    Ref.: ABNT NBR 6118:2023, item 15.8.2, p. 107 (ell_e = 2·ell no balanço)
    [rule: NBR6118-15.8.2-dispensa-2a-ordem-local]

    Ref.: ABNT NBR 6118:2023, item 15.6, p. 105 (ell_e = min(ell_0 + h, ell))
    [rule: NBR6118-15.6-comprimento-equivalente]

    [req: REQ-PILARETE-02-entradas-explicitas-e-recusa-por-ausencia]  (b)

    AJUSTE AO DESPACHO, com o motivo registrado no ruleset: o despacho pedia
    ell_e sempre como entrada do usuário; mas para o caso engastado-livre a
    própria Norma ESCREVE ell_e = 2·ell em 15.8.2, e transformar texto
    normativo em entrada do usuário jogaria fora rastreabilidade. O princípio
    "nunca inferir" fica preservado: o que o usuário declara é a VINCULAÇÃO,
    não o número; sem a declaração o software recusa.

    No ramo ``VINCULADO_DOIS_EXTREMOS``, ell_e é ENTRADA NUMÉRICA EXPLÍCITA e
    ell_0 tem de ser declarado, porque 15.6 pressupõe "elementos estruturais,
    supostos horizontais, que vinculam o pilar" — num pilarete de fundação
    isolado eles podem simplesmente não existir, e aí a expressão não tem
    sentido físico. O software CONFERE o valor declarado contra
    ``min(ell_0 + h, ell)`` e recusa divergência: adivinhar ell_0 (distância
    entre faces internas de elementos horizontais que o software não conhece)
    é o que ``nao_autorizado`` da regra proíbe.
    """
    exigir_um_de("vinculacao", vinculacao, VINCULACOES,
                 fonte="ABNT NBR 6118:2023, 15.6 e 15.8.2, p. 105 e 107",
                 apoio_no_ruleset="NBR6118-15.6-comprimento-equivalente")
    exigir_positivo("ell", ell,
                    fonte="ABNT NBR 6118:2023, 15.8.2, p. 107",
                    apoio_no_ruleset="NBR6118-15.8.2-dispensa-2a-ordem-local")

    if vinculacao == ENGASTADO_BASE_LIVRE_TOPO:
        return 2.0 * ell

    if ell_e_declarado is None or ell_0 is None or h_secao is None:
        raise RecusaForaDeDominio(
            parametro="ell_e_declarado / ell_0 / h_secao",
            valor=(ell_e_declarado, ell_0, h_secao),
            intervalo="os três declarados quando vinculacao = "
                      "VINCULADO_DOIS_EXTREMOS",
            fonte="ABNT NBR 6118:2023, 15.6, p. 105 — ell_e = min(ell_0 + h, "
                  "ell) pressupõe elementos horizontais que vinculam o pilar; "
                  "o software não os conhece e não pode adivinhar ell_0",
            forca=DECLARADO_PELO_USUARIO,
            apoio_no_ruleset="NBR6118-15.6-comprimento-equivalente",
        )
    esperado = min(ell_0 + h_secao, ell)
    if abs(ell_e_declarado - esperado) > 1e-9:
        raise RecusaForaDeDominio(
            parametro="ell_e_declarado",
            valor=ell_e_declarado,
            intervalo=f"= min(ell_0 + h, ell) = {esperado:.6f} m",
            fonte="ABNT NBR 6118:2023, 15.6, p. 105",
            forca=DECLARADO_EM_TEXTO,
            apoio_no_ruleset="NBR6118-15.6-comprimento-equivalente",
            sugestao=(f"Declarados ell_0 = {ell_0} m, ell = {ell} m e "
                      f"h = {h_secao} m; 15.6 dá ell_e = {esperado:.4f} m."),
        )
    return ell_e_declarado


def verificar_campo_de_aplicacao_15_8(*, secao_constante: bool | None,
                                      armadura_constante: bool | None) -> None:
    """Impõe as duas condições de CAMPO de 15.8.1 antes de qualquer conta.

    Ref.: ABNT NBR 6118:2023, item 15.8.1, p. 107 (2º parágrafo conforme Em1:2026)
    [rule: NBR6118-15.8.1-campo-de-aplicacao-esbeltez]
    [req: REQ-PILARETE-05-esbeltez-com-recusa-fora-do-pilar-curto]  (1)

    15.8 vale para elementos de SEÇÃO CONSTANTE e ARMADURA CONSTANTE ao longo
    do eixo. Um pilarete com seção variável (tronco de pirâmide, transição
    para a sapata) sai do campo de 15.8.2/15.8.3.2/15.8.4 — RECUSA, nunca
    aproximação. As duas condições valem ANTES de qualquer conta.
    """
    for nome, valor in (("secao_constante", secao_constante),
                        ("armadura_constante", armadura_constante)):
        if valor is not True:
            raise RecusaForaDeDominio(
                parametro=nome,
                valor=valor,
                intervalo="declaração explícita True",
                fonte="ABNT NBR 6118:2023, 15.8.1, p. 107 — 15.8 aplica-se a "
                      "elementos de seção e armadura CONSTANTES ao longo do "
                      "eixo",
                forca=DECLARADO_PELO_USUARIO,
                apoio_no_ruleset="NBR6118-15.8.1-campo-de-aplicacao-esbeltez",
                sugestao="Pilarete de seção ou armadura variável está FORA do "
                         "campo de 15.8. O software recusa em vez de aproximar.",
            )


def indice_de_esbeltez(ell_e: float, dimensao_no_plano_de_flexao: float) -> float:
    """Índice de esbeltez ``lambda_esbeltez`` numa direção [adimensional].

    Ref.: ABNT NBR 6118:2023, item 15.8.2, p. 107
    [rule: NBR6118-15.8.2-dispensa-2a-ordem-local]
    [deriv: DER-GEOM-raio-de-giracao]

        lambda_esbeltez = ell_e / i,  com i = sqrt(I/A)

    NOME ``lambda_esbeltez`` e nunca ``lambda``: ``Concreto.lambda_x``
    (17.2.2, relação y/x do bloco retangular) já existe em ``materiais.py``, e
    ``lambda`` é palavra reservada de Python. REQ-PILARETE-01.
    """
    exigir_positivo("ell_e", ell_e,
                    fonte="ABNT NBR 6118:2023, 15.8.2, p. 107",
                    apoio_no_ruleset="NBR6118-15.8.2-dispensa-2a-ordem-local")
    return ell_e / raio_de_giracao(dimensao_no_plano_de_flexao)


def limite_lambda1(e_1: float, h_secao_no_plano_de_flexao: float,
                   alpha_b: float = ALPHA_B_PILARETE) -> float:
    """Valor-limite ``lambda_1`` de 15.8.2, CALCULADO PELA FÓRMULA.

    Ref.: ABNT NBR 6118:2023, item 15.8.2, p. 107-108
    [rule: NBR6118-15.8.2-dispensa-2a-ordem-local]

        lambda_1 = min(90 ; max(35 ; (25 + 12,5·e_1/h)/alpha_b))

    É PROIBIDO FIXAR 35 NO CÓDIGO, e a proibição vale MESMO SABENDO que sob
    M_1d,mín o resultado é exatamente 35 em todo o domínio admissível (ver
    :func:`excentricidade_de_1a_ordem`). Basta o momento de 1ª ordem REAL
    superar M_1d,mín — o que acontece SEMPRE que M ou H entram como dado na
    base do pilar metálico — para lambda_1 subir acima de 35 e a fronteira
    mudar. O 35 correto obtido pela fórmula e o 35 escrito à mão são o mesmo
    número hoje e objetos diferentes amanhã.

    ``e_1`` e ``h_secao_no_plano_de_flexao`` na MESMA unidade (metros, pela
    convenção do pacote). A razão e_1/h é adimensional com qualquer unidade —
    se um vier em cm e o outro em m, o pint converte e o erro passa; só a
    guarda explícita pega (``checagem_dimensional`` da regra).
    """
    exigir_positivo("h_secao_no_plano_de_flexao", h_secao_no_plano_de_flexao,
                    fonte="ABNT NBR 6118:2023, 15.8.2, p. 107",
                    apoio_no_ruleset="NBR6118-15.8.2-dispensa-2a-ordem-local")
    exigir_positivo("alpha_b", alpha_b,
                    fonte="ABNT NBR 6118:2023, 15.8.2, p. 108",
                    apoio_no_ruleset="NBR6118-15.8.2-dispensa-2a-ordem-local")
    bruto = (25.0 + 12.5 * (e_1 / h_secao_no_plano_de_flexao)) / alpha_b
    return min(90.0, max(35.0, bruto))


@dataclass(frozen=True)
class EsbeltezPorDirecao:
    """lambda, lambda_1, i e e_1 de UMA direção principal.

    Ref.: ABNT NBR 6118:2023, item 15.8.2, p. 107-108
    [rule: NBR6118-15.8.2-dispensa-2a-ordem-local]
    """

    direcao: str
    """``"xx"`` (flexão no plano de h) ou ``"yy"`` (flexão no plano de b)."""

    dimensao_no_plano: float
    """Dimensão da seção medida no plano de flexão desta direção [m]."""

    i_raio_de_giracao: float
    """i = dimensao/sqrt(12) [m]."""

    lambda_esbeltez: float
    """ell_e/i [adimensional]."""

    e_1: float
    """max(|M_1d|, M_1d,mín)/N_d [m]."""

    lambda_1: float
    """min(90, max(35, (25 + 12,5·e_1/h)/alpha_b)) [adimensional]."""

    @property
    def pilar_curto(self) -> bool:
        """lambda < lambda_1, com desigualdade ESTRITA (15.8.2).

        Ref.: ABNT NBR 6118:2023, item 15.8.2, p. 107
        [rule: NBR6118-15.8.2-dispensa-2a-ordem-local]
        """
        return self.lambda_esbeltez < self.lambda_1


def _folga_de_esbeltez(direcao: EsbeltezPorDirecao) -> float:
    """Chave de ordenação: quanto lambda excede lambda_1 nesta direção.

    Ref.: ABNT NBR 6118:2023, item 15.8.2, p. 107
    [rule: NBR6118-15.8.2-dispensa-2a-ordem-local]

    Auxiliar privado, existente só para que este pacote não contenha nenhuma
    expressão ``lambda`` de Python — ver o comentário em
    :func:`verificar_pilar_curto`.
    """
    return direcao.lambda_esbeltez - direcao.lambda_1


@dataclass(frozen=True)
class ResultadoEsbeltez:
    """Saída de :func:`verificar_pilar_curto`, inteira, para o memorial.

    Ref.: ABNT NBR 6118:2023, itens 15.8.1 e 15.8.2, p. 107-108
    [rule: NBR6118-15.8.2-dispensa-2a-ordem-local]
    [req: REQ-PILARETE-12-memorial-e-o-que-ele-e-obrigado-a-dizer]  (c)
    """

    vinculacao: str
    justificativa_elemento_isolado: str
    ell: float
    ell_e: float
    alpha_b: float
    direcoes: tuple[EsbeltezPorDirecao, ...]
    lambda_maximo: float
    """MAIOR lambda das duas direções, isto é, o do MENOR raio de giração."""
    elemento_pouco_comprimido: bool
    """N_d < 0,10·f_cd·A_c (exceção do 2º parágrafo de 15.8.1, redação Em1)."""


def verificar_pilar_curto(
    *,
    vinculacao: str,
    ell: float,
    h_secao: float,
    b_secao: float,
    N_d: float,
    M_1d_x: float,
    M_1d_y: float,
    M_1d_min_xx: float,
    M_1d_min_yy: float,
    f_cd_MPa: float,
    secao_constante: bool | None,
    armadura_constante: bool | None,
    ell_e_declarado: float | None = None,
    ell_0: float | None = None,
) -> ResultadoEsbeltez:
    """Sequência completa de REQ-PILARETE-05; RECUSA fora do pilar curto.

    Ref.: ABNT NBR 6118:2023, itens 15.8.1, 15.8.2 e 15.8.3, p. 107-108
    [rule: NBR6118-15.8.1-campo-de-aplicacao-esbeltez]
    [rule: NBR6118-15.8.2-dispensa-2a-ordem-local]
    [rule: NBR6118-15.8.3-metodos-de-2a-ordem]  (REJEITADA -> é a recusa)
    [deriv: DER-GEOM-raio-de-giracao]
    [deriv: DER-NBR6118-15.8.2-e1-de-M1d-min]
    [req: REQ-PILARETE-05-esbeltez-com-recusa-fora-do-pilar-curto]

    Passos, cada um com seu próprio motivo de recusa:

    1. campo de 15.8.1 — seção e armadura constantes;
    2. classificação como elemento isolado (15.4.4-a) ou declaração;
    3. ``i = sqrt(I/A)`` calculado NO NÚCLEO, nas duas direções;
    4. ``lambda = ell_e/i`` por direção;
    5. ``lambda_1`` por direção, pela FÓRMULA (nunca 35 fixo);
    6. ``lambda < lambda_1`` ESTRITO -> pilar curto; ``>=`` -> RECUSA;
    7. ``lambda <= 200`` (15.8.1 na redação da Em1:2026, com N_d de CÁLCULO
       na exceção de elemento pouco comprimido).

    A DESIGUALDADE É ESTRITA: a dispensa vale "quando o índice de esbeltez
    for MENOR QUE o valor-limite". ``lambda == lambda_1`` NÃO dispensa, e o
    teste em cima do valor é obrigatório no GATE 3.

    A recusa cita 15.8.2/15.8.3, o lambda obtido, o lambda_1 calculado e a
    direção que governou — porque acima de lambda_1 seriam necessários os
    métodos de 15.8.3 (não lineares, sem fórmula fechada), que esta versão
    REJEITA. Recusar é o comportamento correto; calcular "aproximadamente"
    seria produzir número sem regra aprovada.
    """
    verificar_campo_de_aplicacao_15_8(secao_constante=secao_constante,
                                      armadura_constante=armadura_constante)
    justificativa = classificar_elemento_isolado(vinculacao)
    ell_e = comprimento_equivalente(
        vinculacao=vinculacao, ell=ell, ell_e_declarado=ell_e_declarado,
        ell_0=ell_0, h_secao=h_secao,
    )

    direcoes: list[EsbeltezPorDirecao] = []
    for nome, dimensao, M_1d, M_1d_min in (
        ("xx", h_secao, M_1d_x, M_1d_min_xx),
        ("yy", b_secao, M_1d_y, M_1d_min_yy),
    ):
        e_1 = excentricidade_de_1a_ordem(M_1d, M_1d_min, N_d)
        direcoes.append(EsbeltezPorDirecao(
            direcao=nome,
            dimensao_no_plano=dimensao,
            i_raio_de_giracao=raio_de_giracao(dimensao),
            lambda_esbeltez=indice_de_esbeltez(ell_e, dimensao),
            e_1=e_1,
            lambda_1=limite_lambda1(e_1, dimensao, ALPHA_B_PILARETE),
        ))

    lambda_maximo = max(d.lambda_esbeltez for d in direcoes)
    A_c = h_secao * b_secao
    # 0,10·f_cd·A_c com f_cd em MPa = MN/m² -> ×1000 para kN.
    elemento_pouco_comprimido = N_d < 0.10 * f_cd_MPa * 1000.0 * A_c

    # (7) teto absoluto de 15.8.1, com a exceção da Emenda 1:2026.
    if lambda_maximo > 200.0 and not elemento_pouco_comprimido:
        raise RecusaForaDeDominio(
            parametro="lambda_esbeltez",
            valor=round(lambda_maximo, 4),
            intervalo="<= 200",
            fonte="ABNT NBR 6118:2023/Em1:2026, 15.8.1, 2º parágrafo, p. 107 "
                  "— lambda > 200 só é admitido em elementos POUCO "
                  "COMPRIMIDOS, com força normal DE CÁLCULO menor que "
                  "0,10·f_cd·A_c",
            forca=DECLARADO_EM_TEXTO,
            apoio_no_ruleset="NBR6118-15.8.1-campo-de-aplicacao-esbeltez",
            sugestao=(f"N_d = {N_d:.2f} kN contra 0,10·f_cd·A_c = "
                      f"{0.10 * f_cd_MPa * 1000.0 * A_c:.2f} kN."),
        )

    # (6) fronteira ESTRITA do pilar curto.
    reprovadas = [d for d in direcoes if not d.pilar_curto]
    if reprovadas:
        # Sem expressão `lambda` de Python em todo o pacote: o a6 confere o
        # namespace por busca textual, e um `lambda` de linguagem no meio de
        # um módulo cujo símbolo proibido se chama `lambda` custa mais tempo
        # de auditoria do que a tupla ordenada abaixo (REQ-PILARETE-01).
        pior = sorted(
            reprovadas,
            key=_folga_de_esbeltez,
        )[-1]
        raise RecusaForaDeDominio(
            parametro=f"lambda_esbeltez (direção {pior.direcao})",
            valor=round(pior.lambda_esbeltez, 4),
            intervalo=f"< lambda_1 = {pior.lambda_1:.4f} (desigualdade ESTRITA)",
            fonte="ABNT NBR 6118:2023, 15.8.2, p. 107 — a dispensa dos efeitos "
                  "locais de 2ª ordem vale 'quando o índice de esbeltez for "
                  "MENOR QUE o valor-limite'; acima disso valem os métodos de "
                  "15.8.3 (p. 108), que esta versão NÃO implementa",
            forca=ESCOPO_DESTA_VERSAO,
            apoio_no_ruleset="NBR6118-15.8.2-dispensa-2a-ordem-local",
            sugestao=(f"Direção {pior.direcao}: ell_e = {ell_e:.4f} m, "
                      f"i = {pior.i_raio_de_giracao:.5f} m, "
                      f"lambda = {pior.lambda_esbeltez:.4f} >= "
                      f"lambda_1 = {pior.lambda_1:.4f}. Este software só "
                      "verifica PILAR CURTO; 15.8.3 exige fluência acima de "
                      "lambda = 90 e método geral acima de 140."),
        )

    return ResultadoEsbeltez(
        vinculacao=vinculacao,
        justificativa_elemento_isolado=justificativa,
        ell=ell,
        ell_e=ell_e,
        alpha_b=ALPHA_B_PILARETE,
        direcoes=tuple(direcoes),
        lambda_maximo=lambda_maximo,
        elemento_pouco_comprimido=elemento_pouco_comprimido,
    )
