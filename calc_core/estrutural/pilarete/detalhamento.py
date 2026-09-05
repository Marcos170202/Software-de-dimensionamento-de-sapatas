"""Detalhamento do pilarete — armaduras longitudinal (17.3.5.3/18.4.2) e transversal.

Ref.: ABNT NBR 6118:2023, itens 17.3.5.3.1 e 17.3.5.3.2, p. 133
[rule: NBR6118-17.3.5.3-armaduras-limite-pilarete]

Ref.: ABNT NBR 6118:2023, itens 18.4.2.1 e 18.4.2.2, p. 153
[rule: NBR6118-18.4.2-armaduras-longitudinais-pilarete]

Ref.: ABNT NBR 6118:2023, item 18.4.3, p. 153-154
[rule: NBR6118-18.4.3-armaduras-transversais-pilarete]

Ref.: ABNT NBR 6118:2023, itens 18.3.3.1 e 18.3.3.2, com a INCLUSÃO da
Emenda 1:2026, p. 150-151
[rule: NBR6118-18.3.3.2-detalhamento-do-estribo-por-cortante]

[deriv: DER-NBR6118-composicao-18.3.3.2-com-18.4.3]
[req: REQ-PILARETE-07-armadura-longitudinal]
[req: REQ-PILARETE-08-estribos-e-a-recusa-do-CA-60]
[req: REQ-PILARETE-18-verificacao-de-forca-cortante]  (9)

TETO vs. PISO — É O ERRO DE LADO INSEGURO DESTE MÓDULO, e por isso está no
alto do arquivo. O último parágrafo de 18.4.3 manda comparar seus limites com
os de 18.3 "adotando-se o menor dos limites especificados". Aplicada
mecanicamente, essa frase AFROUXA toda exigência de PISO — tomar o menor entre
``phi_t >= max(5 mm, phi/4)`` e ``phi_t >= 5 mm`` autorizaria estribo mais
fino do que 18.4.3 exige. A leitura correta é a única compatível com
requisitos SIMULTÂNEOS (interseção dos conjuntos admissíveis):

    TETOS  -> adota-se o MENOR   (espaçamentos, diâmetro máximo do estribo)
    PISOS  -> adota-se o MAIOR   (diâmetro mínimo, phi_long >= phi_t, rho_sw)

CONSEQUÊNCIA MEDIDA, e ela precisa ser dita: na geometria de referência
(30×30, phi 16, d = 25,7 cm, V_Sd = 120 kN) quem governa o espaçamento passa
a ser 18.3.3.2, com 154,2 mm contra os 192,0 mm de 18.4.3. Um pilarete
detalhado só por 18.4.3 pode REPROVAR aqui. Não é regressão — é que 18.4.3
sozinho estava incompleto assim que o cortante entrou no escopo.

CA-60 NA ARMADURA LONGITUDINAL É RECUSA, não interpolação: 18.4.3 dá k_phi
para CA-25 (24) e CA-50 (12) e a lista é COMPLETA — CA-60 não aparece. O
espaçamento máximo do estribo para CA-60 é NAO_DECLARADO_NA_FONTE.
"""
from __future__ import annotations

from dataclasses import dataclass

from calc_core.estrutural.dominio import (
    DECLARADO_EM_TEXTO,
    ESCOPO_DESTA_VERSAO,
    NAO_DECLARADO_NA_FONTE,
    RecusaForaDeDominio,
    exigir_positivo,
)
from calc_core.sapata_isolada.materiais import Aco, Concreto

__all__ = [
    "K_PHI_POR_CATEGORIA",
    "PHI_LONGITUDINAL_MINIMO_MM",
    "PHI_ESTRIBO_MINIMO_MM",
    "ESPACAMENTO_LIVRE_MINIMO_MM",
    "TAXA_MAXIMA_DE_ARMADURA",
    "A_s_minima",
    "A_s_maxima",
    "k_phi_de_18_4_3",
    "phi_t_minimo_18_4_3",
    "s_max_18_4_3",
    "s_max_adicional_estribo_fino_18_4_3",
    "DECLARACAO_ALTERNATIVA_DE_ESTRIBO_FINO",
    "s_max_18_3_3_2",
    "s_t_max_18_3_3_2",
    "phi_t_maximo_18_3_3_2",
    "ResultadoArmaduraLongitudinal",
    "verificar_armadura_longitudinal",
    "LimiteComposto",
    "ResultadoEstribos",
    "verificar_estribos",
]

K_PHI_POR_CATEGORIA: dict[str, float] = {"CA-25": 24.0, "CA-50": 12.0}
"""Multiplicador k_phi de ``s <= k_phi·phi``, por categoria de aço [-].

Ref.: ABNT NBR 6118:2023, item 18.4.3, p. 153
[rule: NBR6118-18.4.3-armaduras-transversais-pilarete]

LISTA COMPLETA, conferida por leitura visual do a2 nas p. impressas 153 e
154: "24 phi para CA-25, 12 phi para CA-50". CA-60 NÃO APARECE, e a ausência
é o dado — ver :func:`k_phi_de_18_4_3`.
"""

PHI_LONGITUDINAL_MINIMO_MM = 10.0
"""phi >= 10 mm na armadura longitudinal de pilar (18.4.2.1)."""

PHI_ESTRIBO_MINIMO_MM = 5.0
"""Piso absoluto do diâmetro do estribo: 5 mm em 18.4.3 e em 18.3.3.2."""

ESPACAMENTO_LIVRE_MINIMO_MM = 20.0
"""Parcela fixa do espaçamento livre mínimo entre barras (18.4.2.2)."""

TAXA_MAXIMA_DE_ARMADURA = 0.08
"""A_s,max = 8 % de A_c, "inclusive a sobreposição em regiões de emenda"
(17.3.5.3.2). É esse "inclusive" que limita a 4 % FORA da emenda quando
100 % das barras emendam na mesma seção — a restrição que costuma governar o
pilarete."""


def A_s_minima(*, N_d: float, f_yd_MPa: float, A_c: float) -> float:
    """Armadura longitudinal mínima do pilar [m²].

    Ref.: ABNT NBR 6118:2023, item 17.3.5.3.1, p. 133
    [rule: NBR6118-17.3.5.3-armaduras-limite-pilarete]
    [req: REQ-PILARETE-07-armadura-longitudinal]

        A_s,mín = max(0,15·N_d/f_yd ; 0,004·A_c)

    ``N_d`` em kN, ``f_yd_MPa`` em MPa (= MN/m²), ``A_c`` em m²; o resultado
    sai em m². As duas parcelas têm naturezas diferentes — uma é de FORÇA, a
    outra é GEOMÉTRICA — e num pilarete pouco solicitado quem governa é a
    segunda (30×30 com N_d = 1000 kN: 3,45 cm² contra 3,60 cm²).

    NÃO DECLARADO NA FONTE, e vai ao memorial como interpretação: a Norma não
    diz QUAL combinação fornece o N_d desta expressão. Adota-se a MAIS
    DESFAVORÁVEL, que é o lado conservador.
    """
    exigir_positivo("f_yd_MPa", f_yd_MPa,
                    fonte="ABNT NBR 6118:2023, 17.3.5.3.1, p. 133",
                    apoio_no_ruleset="NBR6118-17.3.5.3-armaduras-limite-pilarete")
    exigir_positivo("A_c", A_c,
                    fonte="ABNT NBR 6118:2023, 17.3.5.3.1, p. 133",
                    apoio_no_ruleset="NBR6118-17.3.5.3-armaduras-limite-pilarete")
    exigir_positivo("N_d", N_d, permitir_zero=True,
                    fonte="ABNT NBR 6118:2023, 17.3.5.3.1, p. 133",
                    apoio_no_ruleset="NBR6118-17.3.5.3-armaduras-limite-pilarete")
    return max(0.15 * N_d / (f_yd_MPa * 1000.0), 0.004 * A_c)


def A_s_maxima(A_c: float) -> float:
    """Armadura longitudinal máxima [m²] — 8 % de A_c, INCLUSIVE na emenda.

    Ref.: ABNT NBR 6118:2023, item 17.3.5.3.2, p. 133
    [rule: NBR6118-17.3.5.3-armaduras-limite-pilarete]

        A_s,máx = 0,08·A_c

    "Inclusive a sobreposição de armadura existente em regiões de emenda" —
    é a frase que faz o limite valer DUAS vezes: na seção corrente e na seção
    de emenda com a armadura duplicada. Ver
    :func:`verificar_armadura_longitudinal`.
    """
    exigir_positivo("A_c", A_c,
                    fonte="ABNT NBR 6118:2023, 17.3.5.3.2, p. 133",
                    apoio_no_ruleset="NBR6118-17.3.5.3-armaduras-limite-pilarete")
    return TAXA_MAXIMA_DE_ARMADURA * A_c


def k_phi_de_18_4_3(categoria_do_aco_longitudinal: str) -> float:
    """k_phi de ``s <= k_phi·phi``; RECUSA CA-60 em vez de extrapolar.

    Ref.: ABNT NBR 6118:2023, item 18.4.3, p. 153
    [rule: NBR6118-18.4.3-armaduras-transversais-pilarete]
    [req: REQ-PILARETE-08-estribos-e-a-recusa-do-CA-60]

    A recusa do CA-60 é o comportamento CORRETO, não uma limitação a
    contragosto: o item lista k_phi para CA-25 e CA-50 e não para CA-60, logo
    o espaçamento máximo do estribo com armadura longitudinal CA-60 é
    NAO_DECLARADO_NA_FONTE. É PROIBIDO interpolar por f_yk, extrapolar de
    CA-50 ou "adotar 12 phi por analogia" — as três produziriam número sem
    fonte, que é o modo de falha que este projeto recusa.

    CA-60 continua PERMITIDO como armadura TRANSVERSAL (estribo): lá o que
    vale é o teto de f_ywd = 435 MPa de 17.4.2.2-b), e não k_phi.
    """
    if categoria_do_aco_longitudinal not in K_PHI_POR_CATEGORIA:
        raise RecusaForaDeDominio(
            parametro="categoria_do_aco_longitudinal",
            valor=categoria_do_aco_longitudinal,
            intervalo="uma de " + ", ".join(sorted(K_PHI_POR_CATEGORIA)),
            fonte="ABNT NBR 6118:2023, 18.4.3, p. 153 — o item fornece k_phi "
                  "apenas para CA-25 (24 phi) e CA-50 (12 phi); a Norma NÃO "
                  "cobre o caso do CA-60 como armadura longitudinal de pilar",
            forca=NAO_DECLARADO_NA_FONTE,
            apoio_no_ruleset="NBR6118-18.4.3-armaduras-transversais-pilarete",
            sugestao="É PROIBIDO interpolar por f_yk, extrapolar de CA-50 ou "
                     "adotar 12 phi por analogia. Use CA-25 ou CA-50 na "
                     "armadura longitudinal, ou verifique fora deste software. "
                     "(CA-60 continua admitido como ESTRIBO.)",
        )
    return K_PHI_POR_CATEGORIA[categoria_do_aco_longitudinal]


def phi_t_minimo_18_4_3(phi_longitudinal_mm: float) -> float:
    """Piso do diâmetro do estribo [mm] — ``max(5 mm, phi/4)``.

    Ref.: ABNT NBR 6118:2023, item 18.4.3, p. 153
    [rule: NBR6118-18.4.3-armaduras-transversais-pilarete]

    É PISO. Aplicar-lhe a regra do "menor dos limites" do último parágrafo do
    mesmo item — que é para TETOS — afrouxaria a exigência: erro do lado
    INSEGURO, proibido por [deriv: DER-NBR6118-composicao-18.3.3.2-com-18.4.3].
    """
    exigir_positivo("phi_longitudinal_mm", phi_longitudinal_mm,
                    fonte="ABNT NBR 6118:2023, 18.4.3, p. 153",
                    apoio_no_ruleset="NBR6118-18.4.3-armaduras-transversais-pilarete")
    return max(PHI_ESTRIBO_MINIMO_MM, phi_longitudinal_mm / 4.0)


def s_max_18_4_3(*, phi_longitudinal_mm: float, b_min_mm: float,
                 k_phi: float) -> float:
    """Espaçamento longitudinal máximo do estribo por 18.4.3 [mm].

    Ref.: ABNT NBR 6118:2023, item 18.4.3, p. 153
    [rule: NBR6118-18.4.3-armaduras-transversais-pilarete]

        s <= min(200 mm ; b_mín ; k_phi·phi)

    ``b_mín`` é a MENOR dimensão da seção do pilarete, em mm. Estribos em TODA
    a altura do pilarete — não há trecho dispensado.
    """
    exigir_positivo("b_min_mm", b_min_mm,
                    fonte="ABNT NBR 6118:2023, 18.4.3, p. 153",
                    apoio_no_ruleset="NBR6118-18.4.3-armaduras-transversais-pilarete")
    return min(200.0, b_min_mm, k_phi * phi_longitudinal_mm)


def s_max_adicional_estribo_fino_18_4_3(*, phi_t_mm: float,
                                        phi_longitudinal_mm: float,
                                        f_yk_MPa: float) -> float:
    """Limitação ADICIONAL de s quando se adota phi_t < phi/4 [mm].

    Ref.: ABNT NBR 6118:2023, item 18.4.3, p. 154
    [rule: NBR6118-18.4.3-armaduras-transversais-pilarete]

        s_máx = 90000·(phi_t²/phi)/f_yk,   f_yk em MPa, comprimentos em mm

    ATENÇÃO À TRANSCRIÇÃO — e este é um achado que a camada de texto do PDF
    produz sozinha: NÃO HÁ RAIZ QUADRADA nessa expressão. O texto decodificado
    sugere um expoente 1/2 que não existe; a leitura visual a 300 dpi
    confirmou a fração 1/f_yk multiplicando o parêntese (phi_t²/phi), sem
    raiz. O mutante com raiz é REJEITADO pela checagem dimensional (dá
    mm^0,5), e está registrado em ``tools/checar_dimensoes.py``.

    ADICIONAL, NUNCA SUBSTITUTIVA de ``min(200, b_mín, k_phi·phi)``: quem
    adota estribo mais fino ganha uma restrição a mais, não uma no lugar da
    outra. Só é oferecida com o MESMO tipo de aço nas duas armaduras.
    """
    exigir_positivo("phi_t_mm", phi_t_mm,
                    fonte="ABNT NBR 6118:2023, 18.4.3, p. 154",
                    apoio_no_ruleset="NBR6118-18.4.3-armaduras-transversais-pilarete")
    exigir_positivo("f_yk_MPa", f_yk_MPa,
                    fonte="ABNT NBR 6118:2023, 18.4.3, p. 154",
                    apoio_no_ruleset="NBR6118-18.4.3-armaduras-transversais-pilarete")
    return 90000.0 * (phi_t_mm ** 2 / phi_longitudinal_mm) / f_yk_MPa


def s_max_18_3_3_2(*, d_util_mm: float, V_Sd: float, V_Rd2_valor: float) -> float:
    """Espaçamento longitudinal máximo do estribo por 18.3.3.2 [mm].

    Ref.: ABNT NBR 6118:2023, item 18.3.3.2, p. 151
    [rule: NBR6118-18.3.3.2-detalhamento-do-estribo-por-cortante]

        V_Sd <= 0,67·V_Rd2  ->  s_máx = min(0,6·d ; 300 mm)
        V_Sd >  0,67·V_Rd2  ->  s_máx = min(0,3·d ; 200 mm)

    INTERPRETAÇÃO DECLARADA (a): o item escreve ``V_d``, e §17.4 inteiro
    escreve ``V_Sd``; a Norma não declara que são o mesmo objeto. Adota-se
    ``V_d = V_Sd``, força cortante de CÁLCULO — leitura conservadora, porque
    um valor menor afrouxaria a escolha do ramo.

    O ``V_Rd2`` é o do MODELO ADOTADO. Como V_Rd2(II) < V_Rd2(I) para
    theta_biela < 45°, o Modelo II torna estes limiares MAIS restritivos, e
    misturar o V_Rd2 de um modelo aqui com o do outro na verificação de
    17.4.2.1 é proibido.
    """
    exigir_positivo("d_util_mm", d_util_mm,
                    fonte="ABNT NBR 6118:2023, 18.3.3.2, p. 151",
                    apoio_no_ruleset="NBR6118-18.3.3.2-detalhamento-do-estribo-"
                                     "por-cortante")
    exigir_positivo("V_Rd2_valor", V_Rd2_valor,
                    fonte="ABNT NBR 6118:2023, 18.3.3.2, p. 151",
                    apoio_no_ruleset="NBR6118-18.3.3.2-detalhamento-do-estribo-"
                                     "por-cortante")
    if V_Sd <= 0.67 * V_Rd2_valor:
        return min(0.6 * d_util_mm, 300.0)
    return min(0.3 * d_util_mm, 200.0)


def s_t_max_18_3_3_2(*, d_util_mm: float, V_Sd: float,
                     V_Rd2_valor: float) -> float:
    """Espaçamento TRANSVERSAL máximo entre ramos do estribo [mm].

    Ref.: ABNT NBR 6118:2023, item 18.3.3.2, p. 151
    [rule: NBR6118-18.3.3.2-detalhamento-do-estribo-por-cortante]

        V_Sd <= 0,20·V_Rd2  ->  s_t,máx = min(d ; 800 mm)
        V_Sd >  0,20·V_Rd2  ->  s_t,máx = min(0,6·d ; 350 mm)

    Os DOIS limiares (0,67 e 0,20) são de itens diferentes do mesmo parágrafo
    e governam grandezas diferentes; trocá-los é erro invisível à checagem
    dimensional, porque as duas razões de força são adimensionais.
    """
    exigir_positivo("d_util_mm", d_util_mm,
                    fonte="ABNT NBR 6118:2023, 18.3.3.2, p. 151",
                    apoio_no_ruleset="NBR6118-18.3.3.2-detalhamento-do-estribo-"
                                     "por-cortante")
    exigir_positivo("V_Rd2_valor", V_Rd2_valor,
                    fonte="ABNT NBR 6118:2023, 18.3.3.2, p. 151",
                    apoio_no_ruleset="NBR6118-18.3.3.2-detalhamento-do-estribo-"
                                     "por-cortante")
    if V_Sd <= 0.20 * V_Rd2_valor:
        return min(d_util_mm, 800.0)
    return min(0.6 * d_util_mm, 350.0)


def phi_t_maximo_18_3_3_2(*, b_min_mm: float, barra_lisa: bool) -> float:
    """Teto do diâmetro do estribo [mm] — b_mín/10, e 12 mm se barra lisa.

    Ref.: ABNT NBR 6118:2023, item 18.3.3.2, p. 150
    [rule: NBR6118-18.3.3.2-detalhamento-do-estribo-por-cortante]

    INTERPRETAÇÃO DECLARADA (b): o item escreve "1/10 da largura da alma da
    VIGA"; no pilarete lê-se b_mín/10, a menor dimensão da seção. É leitura
    natural e conservadora, mas é INTERPRETAÇÃO — 18.4.3 não traz teto de
    diâmetro de estribo, só piso, e sem esta leitura o teto simplesmente não
    existiria.

    A tela soldada (mínimo reduzido a 4,2 mm com precauções contra corrosão)
    NÃO é implementada: o pilarete desta versão usa estribo de barra.
    """
    exigir_positivo("b_min_mm", b_min_mm,
                    fonte="ABNT NBR 6118:2023, 18.3.3.2, p. 150",
                    apoio_no_ruleset="NBR6118-18.3.3.2-detalhamento-do-estribo-"
                                     "por-cortante")
    teto = b_min_mm / 10.0
    return min(teto, 12.0) if barra_lisa else teto


@dataclass(frozen=True)
class ResultadoArmaduraLongitudinal:
    """Verificação completa da armadura longitudinal, para o memorial.

    Ref.: ABNT NBR 6118:2023, itens 17.3.5.3 e 18.4.2, p. 133 e 153
    [rule: NBR6118-17.3.5.3-armaduras-limite-pilarete]
    [rule: NBR6118-18.4.2-armaduras-longitudinais-pilarete]
    [req: REQ-PILARETE-07-armadura-longitudinal]
    """

    A_s_adotada: float
    """Área total de armadura longitudinal na seção corrente [m²]."""
    A_s_minima_valor: float
    A_s_maxima_valor: float
    A_s_na_emenda: float
    """A_s duplicada, quando 100 % das barras emendam na mesma seção [m²]."""
    numero_de_barras: int
    phi_longitudinal_mm: float
    phi_maximo_mm: float
    """b_mín/8 (18.4.2.1)."""
    espacamento_livre_minimo_exigido_mm: float
    espacamento_livre_na_secao_corrente_mm: float
    espacamento_livre_na_emenda_mm: float
    espacamento_entre_eixos_maximo_mm: float
    """min(2·b_mín ; 400 mm) (18.4.2.2)."""
    espacamento_entre_eixos_adotado_mm: float
    atende_A_s_minima: bool
    atende_A_s_maxima_secao_corrente: bool
    atende_A_s_maxima_na_emenda: bool
    atende_phi_minimo: bool
    atende_phi_maximo: bool
    atende_numero_de_barras: bool
    atende_espacamento_livre_secao_corrente: bool
    atende_espacamento_livre_na_emenda: bool
    atende_espacamento_entre_eixos: bool
    declaracoes: tuple[str, ...]

    @property
    def atendido(self) -> bool:
        """Conjunção de TODAS as verificações deste item.

        Ref.: ABNT NBR 6118:2023, itens 17.3.5.3 e 18.4.2, p. 133 e 153
        [rule: NBR6118-18.4.2-armaduras-longitudinais-pilarete]
        """
        return all((
            self.atende_A_s_minima,
            self.atende_A_s_maxima_secao_corrente,
            self.atende_A_s_maxima_na_emenda,
            self.atende_phi_minimo,
            self.atende_phi_maximo,
            self.atende_numero_de_barras,
            self.atende_espacamento_livre_secao_corrente,
            self.atende_espacamento_livre_na_emenda,
            self.atende_espacamento_entre_eixos,
        ))


DECLARACAO_N_D_DE_A_S_MIN = (
    "A NBR 6118:2023, 17.3.5.3.1 (p. 133), escreve A_s,mín = "
    "máx(0,15·N_d/f_yd ; 0,004·A_c) sem dizer QUAL combinação fornece o N_d — "
    "NAO_DECLARADO_NA_FONTE. Este software adota a combinação mais "
    "desfavorável (maior N_d), que é o lado conservador. Interpretação "
    "declarada, não transcrição."
)

DECLARACAO_ESPACAMENTO_NA_EMENDA = (
    "Na região de emenda por traspasse com a espera da sapata, as barras estão "
    "DUPLICADAS e os espaçamentos de 18.4.2.2 continuam valendo — o item diz "
    "que \"esses valores se aplicam também às regiões de emendas por "
    "traspasse\". Hipótese geométrica declarada deste software: a barra da "
    "espera é JUSTAPOSTA à barra do pilarete na mesma camada, de modo que o "
    "espaço livre entre eixos consecutivos perde um diâmetro. É o arranjo "
    "usual e é o lado conservador; um arranjo em que a espera fique na camada "
    "interna sai deste modelo e deve ser verificado pelo projetista."
)


def verificar_armadura_longitudinal(
    *,
    A_s_adotada: float,
    numero_de_barras: int,
    phi_longitudinal_mm: float,
    N_d: float,
    f_yd_MPa: float,
    h_secao: float,
    b_secao: float,
    d_agregado_mm: float,
    espacamento_entre_eixos_mm: float,
    fracao_emendada_na_mesma_secao: float = 1.0,
) -> ResultadoArmaduraLongitudinal:
    """As verificações de 17.3.5.3 e 18.4.2, incluindo a REGIÃO DE EMENDA.

    Ref.: ABNT NBR 6118:2023, itens 17.3.5.3.1, 17.3.5.3.2, 18.4.2.1 e
    18.4.2.2, p. 133 e 153
    [rule: NBR6118-17.3.5.3-armaduras-limite-pilarete]
    [rule: NBR6118-18.4.2-armaduras-longitudinais-pilarete]
    [rule: NBR6118-9.5.2.1-emenda-100-por-cento-comprimida]
    [req: REQ-PILARETE-07-armadura-longitudinal]

    Verifica, e devolve TODOS os valores para o memorial:

    * ``A_s >= max(0,15·N_d/f_yd ; 0,004·A_c)`` (17.3.5.3.1);
    * ``A_s <= 0,08·A_c`` na seção corrente **e** na seção de emenda com a
      armadura DUPLICADA (17.3.5.3.2, "inclusive a sobreposição") — é isso que
      limita a 4 % fora da emenda quando 100 % das barras emendam na mesma
      seção, e é a restrição que costuma governar;
    * ``phi >= 10 mm`` e ``phi <= b_mín/8`` (18.4.2.1);
    * mínimo UMA BARRA POR VÉRTICE, isto é, 4 na seção retangular (18.4.2.2);
    * espaçamento livre ``>= max(20 mm ; phi ; 1,2·d_agregado)``, TAMBÉM na
      região de emenda com as barras duplicadas (18.4.2.2);
    * espaçamento entre eixos ``<= min(2·b_mín ; 400 mm)`` (18.4.2.2).

    ESTE MÓDULO NÃO REPROVA POR EXCEÇÃO: devolve o resultado com cada
    ``atende_*`` separado, porque o memorial precisa dizer QUAL limite não foi
    atendido, e porque um detalhamento insuficiente é REPROVAÇÃO — não é
    entrada fora de domínio. As recusas (exceção) ficam para o que a Norma não
    cobre, como o CA-60 de :func:`k_phi_de_18_4_3`.
    """
    exigir_positivo("A_s_adotada", A_s_adotada,
                    fonte="ABNT NBR 6118:2023, 17.3.5.3.1, p. 133",
                    apoio_no_ruleset="NBR6118-17.3.5.3-armaduras-limite-pilarete")
    exigir_positivo("phi_longitudinal_mm", phi_longitudinal_mm,
                    fonte="ABNT NBR 6118:2023, 18.4.2.1, p. 153",
                    apoio_no_ruleset="NBR6118-18.4.2-armaduras-longitudinais-pilarete")
    exigir_positivo("d_agregado_mm", d_agregado_mm,
                    fonte="ABNT NBR 6118:2023, 18.4.2.2, p. 153",
                    apoio_no_ruleset="NBR6118-18.4.2-armaduras-longitudinais-pilarete")
    exigir_positivo("espacamento_entre_eixos_mm", espacamento_entre_eixos_mm,
                    fonte="ABNT NBR 6118:2023, 18.4.2.2, p. 153",
                    apoio_no_ruleset="NBR6118-18.4.2-armaduras-longitudinais-pilarete")

    A_c = h_secao * b_secao
    b_min_mm = min(h_secao, b_secao) * 1000.0
    A_s_min = A_s_minima(N_d=N_d, f_yd_MPa=f_yd_MPa, A_c=A_c)
    A_s_max = A_s_maxima(A_c)
    A_s_emenda = A_s_adotada * (1.0 + fracao_emendada_na_mesma_secao)

    livre_exigido = max(ESPACAMENTO_LIVRE_MINIMO_MM, phi_longitudinal_mm,
                        1.2 * d_agregado_mm)
    livre_corrente = espacamento_entre_eixos_mm - phi_longitudinal_mm
    # Barras duplicadas na emenda: a espera é justaposta e consome mais um
    # diâmetro do vão livre entre eixos consecutivos (declaração acima).
    livre_na_emenda = (espacamento_entre_eixos_mm
                       - phi_longitudinal_mm
                       - fracao_emendada_na_mesma_secao * phi_longitudinal_mm)
    entre_eixos_max = min(2.0 * b_min_mm, 400.0)

    return ResultadoArmaduraLongitudinal(
        A_s_adotada=A_s_adotada,
        A_s_minima_valor=A_s_min,
        A_s_maxima_valor=A_s_max,
        A_s_na_emenda=A_s_emenda,
        numero_de_barras=numero_de_barras,
        phi_longitudinal_mm=phi_longitudinal_mm,
        phi_maximo_mm=b_min_mm / 8.0,
        espacamento_livre_minimo_exigido_mm=livre_exigido,
        espacamento_livre_na_secao_corrente_mm=livre_corrente,
        espacamento_livre_na_emenda_mm=livre_na_emenda,
        espacamento_entre_eixos_maximo_mm=entre_eixos_max,
        espacamento_entre_eixos_adotado_mm=espacamento_entre_eixos_mm,
        atende_A_s_minima=A_s_adotada >= A_s_min,
        atende_A_s_maxima_secao_corrente=A_s_adotada <= A_s_max,
        atende_A_s_maxima_na_emenda=A_s_emenda <= A_s_max,
        atende_phi_minimo=phi_longitudinal_mm >= PHI_LONGITUDINAL_MINIMO_MM,
        atende_phi_maximo=phi_longitudinal_mm <= b_min_mm / 8.0,
        atende_numero_de_barras=numero_de_barras >= 4,
        atende_espacamento_livre_secao_corrente=livre_corrente >= livre_exigido,
        atende_espacamento_livre_na_emenda=livre_na_emenda >= livre_exigido,
        atende_espacamento_entre_eixos=(
            espacamento_entre_eixos_mm <= entre_eixos_max),
        declaracoes=(DECLARACAO_N_D_DE_A_S_MIN,
                     DECLARACAO_ESPACAMENTO_NA_EMENDA),
    )


@dataclass(frozen=True)
class LimiteComposto:
    """Um limite com o valor de CADA fonte e o adotado, com quem governou.

    Ref.: ABNT NBR 6118:2023, itens 18.4.3 (p. 154) e 18.3.3.2 (p. 150-151)
    [deriv: DER-NBR6118-composicao-18.3.3.2-com-18.4.3]
    [req: REQ-PILARETE-12-memorial-e-o-que-ele-e-obrigado-a-dizer]  (r)

    O memorial imprime, para cada teto e cada piso, o valor de CADA fonte e o
    adotado, com o item que governou. É por isso que esta classe guarda os
    três números em vez de só o resultado.
    """

    nome: str
    natureza: str
    """``"TETO"`` (adota-se o MENOR) ou ``"PISO"`` (adota-se o MAIOR)."""
    valor_18_4_3: float | None
    valor_18_3_3_2: float | None
    valor_adotado: float
    item_que_governou: str
    """``"18.4.3"``, ``"18.3.3.2"`` ou ``"18.4.3 e 18.3.3.2"`` no EMPATE EXATO.

    Ref.: ABNT NBR 6118:2023, itens 18.4.3 e 18.3.3.2, p. 150-154
    [deriv: DER-NBR6118-composicao-18.3.3.2-com-18.4.3]

    O empate é caso REAL e não hipótese remota: com ``phi_t`` abaixo do piso
    absoluto, os dois itens exigem os mesmos 5 mm. Atribuí-lo a um só dos itens
    esconderia do memorial que o limite é imposto DUAS vezes — quem lesse
    "governou 18.3.3.2" concluiria que 18.4.3 foi folgado ali.
    """

    @property
    def descricao_para_memorial(self) -> str:
        """Linha pronta do memorial, com os dois valores e o que governou.

        Ref.: ABNT NBR 6118:2023, itens 18.4.3 e 18.3.3.2, p. 150-154
        [deriv: DER-NBR6118-composicao-18.3.3.2-com-18.4.3]
        """
        def _fmt(valor: float | None) -> str:
            return "não se aplica" if valor is None else f"{valor:.4g}"
        return (f"{self.nome} [{self.natureza}]: 18.4.3 = {_fmt(self.valor_18_4_3)}; "
                f"18.3.3.2 = {_fmt(self.valor_18_3_3_2)}; "
                f"adotado = {self.valor_adotado:.4g} "
                f"(governou {self.item_que_governou}).")


def _compor(nome: str, natureza: str, valor_18_4_3: float | None,
            valor_18_3_3_2: float | None) -> LimiteComposto:
    """Compõe um limite pelo MENOR (teto) ou pelo MAIOR (piso).

    Ref.: ABNT NBR 6118:2023, item 18.4.3, último parágrafo, p. 154
    [deriv: DER-NBR6118-composicao-18.3.3.2-com-18.4.3]

    A frase da Norma ("adotando-se o menor dos limites especificados") resolve
    o caso de TETO. Aplicá-la a um PISO é erro do lado INSEGURO, e é a metade
    da composição que a derivação acrescenta: requisitos SIMULTÂNEOS pedem a
    INTERSEÇÃO dos conjuntos admissíveis — mínimo em teto, máximo em piso.
    """
    candidatos = [(v, i) for v, i in ((valor_18_4_3, "18.4.3"),
                                      (valor_18_3_3_2, "18.3.3.2"))
                  if v is not None]
    if not candidatos:  # pragma: no cover - chamada sempre com ao menos uma fonte
        raise RecusaForaDeDominio(
            parametro=nome, valor=None,
            intervalo="ao menos uma fonte com valor",
            fonte="ABNT NBR 6118:2023, 18.4.3 e 18.3.3.2",
            forca=ESCOPO_DESTA_VERSAO,
            apoio_no_ruleset="DER-NBR6118-composicao-18.3.3.2-com-18.4.3")
    # O EMPATE EXATO É TRATADO EXPLICITAMENTE, e não deixado ao acaso da
    # ordenação de tuplas. `min(candidatos)`/`max(candidatos)` sobre pares
    # (valor, rótulo) desempatavam comparando as STRINGS "18.3.3.2" e "18.4.3":
    # determinístico, sim, mas por acidente — o critério era a ordem
    # lexicográfica dos rótulos, de modo que o TETO atribuía o empate a
    # "18.3.3.2" e o PISO a "18.4.3" (lados opostos, sem nenhuma razão de
    # engenharia), e renomear um rótulo inverteria a atribuição.
    #
    # `valor_adotado` nunca dependeu disso — num empate os dois números são o
    # mesmo. O que dependia era `item_que_governou`, que vai ao MEMORIAL: dizer
    # que um item governou quando os DOIS impõem exatamente o mesmo limite é
    # falso num documento auditável, e apaga a informação de que o limite é
    # imposto duas vezes. Empatou, os dois governam, e o memorial diz isso.
    valores = [valor for valor, _ in candidatos]
    valor_adotado = min(valores) if natureza == "TETO" else max(valores)
    governantes = [item for valor, item in candidatos if valor == valor_adotado]
    return LimiteComposto(
        nome=nome, natureza=natureza, valor_18_4_3=valor_18_4_3,
        valor_18_3_3_2=valor_18_3_3_2, valor_adotado=valor_adotado,
        # A ordem vem da construção de `candidatos` (18.4.3, depois 18.3.3.2),
        # e não da grafia dos rótulos.
        item_que_governou=" e ".join(governantes),
    )


@dataclass(frozen=True)
class ResultadoEstribos:
    """Detalhamento do estribo, com a composição 18.4.3 × 18.3.3.2.

    Ref.: ABNT NBR 6118:2023, itens 18.4.3 e 18.3.3.2, p. 150-154
    [rule: NBR6118-18.4.3-armaduras-transversais-pilarete]
    [rule: NBR6118-18.3.3.2-detalhamento-do-estribo-por-cortante]
    [deriv: DER-NBR6118-composicao-18.3.3.2-com-18.4.3]
    """

    phi_t_mm: float
    s_adotado_mm: float
    k_phi: float
    cortante_verificado: bool
    """False na FAIXA B: sem V_Sd/V_Rd2, só 18.4.3 tem valor."""
    piso_phi_t: LimiteComposto
    teto_phi_t: LimiteComposto
    teto_s: LimiteComposto
    teto_s_transversal: LimiteComposto | None
    s_max_adicional_estribo_fino_mm: float | None
    """Só quando phi_t < phi/4 e mesmo aço nas duas armaduras (18.4.3)."""
    alternativa_de_estribo_fino_invocada: bool
    """True quando 18.4.3 autorizou phi_t < phi/4 pela alternativa.

    Ref.: ABNT NBR 6118:2023, item 18.4.3, p. 153-154
    [rule: NBR6118-18.4.3-armaduras-transversais-pilarete]

    A alternativa DISPENSA o phi/4 (é para isso que ela existe) e acrescenta
    o s_máx de 90000·(phi_t²/phi)/f_yk. Ela NÃO dispensa o piso ABSOLUTO de
    5 mm nem o teto composto de espaçamento.
    """
    atende_piso_phi_t: bool
    atende_teto_phi_t: bool
    atende_teto_s: bool
    atende_s_adicional: bool
    atende_phi_long_maior_ou_igual_phi_t: bool
    """Emenda 1:2026 em 18.3.3.2 — barras de canto com phi_long >= phi_t."""
    nota_C55_a_C90: str | None
    """RECOMENDAÇÃO de 18.4.3 (aviso), jamais reprovação."""
    declaracoes: tuple[str, ...]

    @property
    def atendido(self) -> bool:
        """Conjunção de todos os limites de detalhamento do estribo.

        Ref.: ABNT NBR 6118:2023, itens 18.4.3 e 18.3.3.2, p. 150-154
        [deriv: DER-NBR6118-composicao-18.3.3.2-com-18.4.3]
        """
        return all((self.atende_piso_phi_t, self.atende_teto_phi_t,
                    self.atende_teto_s, self.atende_s_adicional,
                    self.atende_phi_long_maior_ou_igual_phi_t))


DECLARACAO_V_D_LIDO_COMO_V_SD = (
    "A NBR 6118:2023, 18.3.3.2 (p. 151), escreve \"V_d\" nos limiares de "
    "0,67·V_Rd2 e 0,20·V_Rd2, enquanto todo o §17.4 escreve \"V_Sd\"; a Norma "
    "não declara que são o mesmo objeto — NAO_DECLARADO_NA_FONTE. Este "
    "software adota V_d = V_Sd (força cortante de CÁLCULO), leitura "
    "conservadora: um valor menor afrouxaria a escolha do ramo de s_máx."
)

DECLARACAO_PHI_T_TETO_B_SOBRE_10 = (
    "A NBR 6118:2023, 18.3.3.2 (p. 150), limita o diâmetro do estribo a "
    "\"1/10 da largura da alma da viga\". No pilarete isso é lido como "
    "b_mín/10, a menor dimensão da seção — INTERPRETAÇÃO declarada. Sem ela "
    "não existiria teto de diâmetro de estribo, porque 18.4.3 só traz piso."
)

DECLARACAO_ALTERNATIVA_DE_ESTRIBO_FINO = (
    "A NBR 6118:2023, 18.4.3 (p. 154), AUTORIZA phi_t < phi/4 desde que as "
    "duas armaduras sejam do mesmo tipo de aço — declaração do projetista, "
    "adotada aqui — e que o espaçamento respeite TAMBÉM "
    "s_máx = 90000·(phi_t²/phi)/f_yk. Essa limitação é ADICIONAL, nunca "
    "substitutiva de min(200 mm ; b_mín ; k_phi·phi), e a alternativa NÃO "
    "dispensa o piso absoluto de 5 mm. Sem a declaração do tipo de aço a "
    "alternativa não é oferecida e o piso de phi/4 continua valendo."
)

NOTA_C55_A_C90 = (
    "RECOMENDAÇÃO (não requisito) da NOTA de 18.4.3, p. 154, para concretos "
    "C55 a C90: reduzir em 50 % os espaçamentos máximos do estribo e usar "
    "ganchos a 135°. A Norma escreve \"recomenda-se\"; este software emite o "
    "AVISO e NÃO reprova por ele — recomendação não vira critério de software."
)


def verificar_estribos(
    *,
    concreto: Concreto,
    aco_longitudinal: Aco,
    phi_longitudinal_mm: float,
    phi_t_mm: float,
    s_adotado_mm: float,
    h_secao: float,
    b_secao: float,
    d_util_no_plano_do_cortante: float | None = None,
    V_Sd: float | None = None,
    V_Rd2_valor: float | None = None,
    mesmo_aco_nas_duas_armaduras: bool = False,
    barra_lisa_no_estribo: bool = False,
) -> ResultadoEstribos:
    """Detalhamento do estribo, compondo 18.4.3 com 18.3.3.2. TETOS × PISOS.

    Ref.: ABNT NBR 6118:2023, itens 18.4.3 (p. 153-154) e 18.3.3.2
    (p. 150-151, com a INCLUSÃO da Emenda 1:2026)
    [rule: NBR6118-18.4.3-armaduras-transversais-pilarete]
    [rule: NBR6118-18.3.3.2-detalhamento-do-estribo-por-cortante]
    [deriv: DER-NBR6118-composicao-18.3.3.2-com-18.4.3]
    [req: REQ-PILARETE-08-estribos-e-a-recusa-do-CA-60]
    [req: REQ-PILARETE-18-verificacao-de-forca-cortante]  (9)

    ``d_util_no_plano_do_cortante``, ``V_Sd`` e ``V_Rd2_valor`` são OPCIONAIS
    porque na FAIXA B de 14.4.1 não existe verificação de cortante e portanto
    não existe V_Rd2: ali só 18.4.3 tem valor, e o campo
    ``cortante_verificado`` diz isso ao memorial. Fornecer V_Sd sem V_Rd2 (ou
    vice-versa) é erro de wiring e RECUSA.

    O PAR DE DESIGUALDADES QUE NENHUMA DAS DUAS FONTES ENUNCIA JUNTO: o
    ``phi_t >= phi/4`` de 18.4.3 e o ``phi_long >= phi_t`` que a Emenda 1:2026
    inclui em 18.3.3.2 ENCAIXOTAM a relação em ``phi/4 <= phi_t <= phi``. O
    software verifica as duas em conjunto — é composição, não transcrição.

    ``mesmo_aco_nas_duas_armaduras`` TEM DEFAULT RESTRITIVO (``False``), e o
    default é escolhido, não herdado. Esse parâmetro é a CONDIÇÃO que 18.4.3
    impõe para OFERECER a alternativa ``phi_t < phi/4``: com ele em ``True`` a
    função DISPENSA o piso de ``phi/4``. Um default ``True`` numa função
    pública entregaria a dispensa a todo chamador que simplesmente não soubesse
    do parâmetro — a condição da Norma seria presumida satisfeita por omissão,
    que é o lado INSEGURO. Com ``False``, quem não declara nada fica com o
    ``phi/4`` de 18.4.3 valendo integralmente, e a alternativa só existe para
    quem AFIRMA a condição. O caminho de integração
    (:func:`~calc_core.estrutural.pilarete.elemento.verificar_pilarete`) não
    depende do default: lá o valor é DEDUZIDO das categorias de aço declaradas.

    RECUSA (exceção) só para o que a Norma NÃO COBRE: armadura longitudinal
    CA-60, cujo k_phi é NAO_DECLARADO_NA_FONTE. Limite não atendido é
    REPROVAÇÃO (campo ``atende_*``), não recusa.
    """
    exigir_positivo("phi_t_mm", phi_t_mm,
                    fonte="ABNT NBR 6118:2023, 18.4.3, p. 153",
                    apoio_no_ruleset="NBR6118-18.4.3-armaduras-transversais-pilarete")
    exigir_positivo("s_adotado_mm", s_adotado_mm,
                    fonte="ABNT NBR 6118:2023, 18.4.3, p. 153",
                    apoio_no_ruleset="NBR6118-18.4.3-armaduras-transversais-pilarete")
    tem_cortante = (d_util_no_plano_do_cortante is not None
                    and V_Sd is not None and V_Rd2_valor is not None)
    algum_dado_de_cortante = any(valor is not None for valor in
                                 (d_util_no_plano_do_cortante, V_Sd,
                                  V_Rd2_valor))
    if algum_dado_de_cortante and not tem_cortante:
        raise RecusaForaDeDominio(
            parametro="(d_util_no_plano_do_cortante, V_Sd, V_Rd2_valor)",
            valor=(d_util_no_plano_do_cortante, V_Sd, V_Rd2_valor),
            intervalo="os TRÊS declarados, ou NENHUM (FAIXA B de 14.4.1)",
            fonte="ABNT NBR 6118:2023, 18.3.3.2, p. 151 — os limiares de "
                  "espaçamento dependem simultaneamente de d, de V_Sd e do "
                  "V_Rd2 do MODELO ADOTADO",
            forca=DECLARADO_EM_TEXTO,
            apoio_no_ruleset="NBR6118-18.3.3.2-detalhamento-do-estribo-por-"
                             "cortante",
            sugestao="Na FAIXA B (razão de 14.4.1 < 3,0) não há verificação de "
                     "cortante e portanto não há V_Rd2: chame sem nenhum dos "
                     "três. É PROIBIDO arbitrar um V_Rd2 só para preencher o "
                     "limiar.",
        )

    k_phi = k_phi_de_18_4_3(str(aco_longitudinal.categoria))
    b_min_mm = min(h_secao, b_secao) * 1000.0

    # A ALTERNATIVA DE 18.4.3, e ela é uma AUTORIZAÇÃO da Norma, não uma
    # brecha: "permite-se phi_t < phi/4, desde que as armaduras sejam
    # constituídas do mesmo tipo de aço e o espaçamento respeite também
    # s_máx = 90000·(phi_t²/phi)/f_yk". Invocada, ela DISPENSA o phi/4 — é para
    # isso que existe — e acrescenta o s_máx; NÃO dispensa o piso ABSOLUTO de
    # 5 mm (que 18.4.3 e 18.3.3.2 exigem em separado) nem o teto composto de
    # espaçamento. Sem a declaração do tipo de aço, a alternativa NÃO é
    # oferecida e o phi/4 continua valendo: é o lado conservador, e a
    # declaração é do projetista.
    alternativa = (phi_t_mm < phi_longitudinal_mm / 4.0
                   and phi_t_mm >= PHI_ESTRIBO_MINIMO_MM
                   and bool(mesmo_aco_nas_duas_armaduras))
    piso_18_4_3 = (PHI_ESTRIBO_MINIMO_MM if alternativa
                   else phi_t_minimo_18_4_3(phi_longitudinal_mm))
    piso_phi_t = _compor(
        "phi_t mínimo [mm]", "PISO", piso_18_4_3, PHI_ESTRIBO_MINIMO_MM)
    teto_phi_t = _compor(
        "phi_t máximo [mm]", "TETO", None,
        phi_t_maximo_18_3_3_2(b_min_mm=b_min_mm, barra_lisa=barra_lisa_no_estribo))
    teto_s = _compor(
        "s máximo [mm]", "TETO",
        s_max_18_4_3(phi_longitudinal_mm=phi_longitudinal_mm,
                     b_min_mm=b_min_mm, k_phi=k_phi),
        (s_max_18_3_3_2(d_util_mm=float(d_util_no_plano_do_cortante) * 1000.0,
                        V_Sd=float(V_Sd), V_Rd2_valor=float(V_Rd2_valor))
         if tem_cortante else None))
    teto_s_t = (_compor(
        "s_t máximo entre ramos [mm]", "TETO", None,
        s_t_max_18_3_3_2(d_util_mm=float(d_util_no_plano_do_cortante) * 1000.0,
                         V_Sd=float(V_Sd), V_Rd2_valor=float(V_Rd2_valor)))
        if tem_cortante else None)

    s_adicional = None
    atende_adicional = True
    if alternativa:
        s_adicional = s_max_adicional_estribo_fino_18_4_3(
            phi_t_mm=phi_t_mm, phi_longitudinal_mm=phi_longitudinal_mm,
            f_yk_MPa=aco_longitudinal.fyk)
        atende_adicional = s_adotado_mm <= s_adicional

    declaracoes = [DECLARACAO_PHI_T_TETO_B_SOBRE_10]
    if tem_cortante:
        declaracoes.insert(0, DECLARACAO_V_D_LIDO_COMO_V_SD)
    if alternativa:
        declaracoes.append(DECLARACAO_ALTERNATIVA_DE_ESTRIBO_FINO)

    return ResultadoEstribos(
        phi_t_mm=phi_t_mm,
        s_adotado_mm=s_adotado_mm,
        k_phi=k_phi,
        cortante_verificado=tem_cortante,
        piso_phi_t=piso_phi_t,
        teto_phi_t=teto_phi_t,
        teto_s=teto_s,
        teto_s_transversal=teto_s_t,
        s_max_adicional_estribo_fino_mm=s_adicional,
        alternativa_de_estribo_fino_invocada=alternativa,
        atende_piso_phi_t=phi_t_mm >= piso_phi_t.valor_adotado,
        atende_teto_phi_t=phi_t_mm <= teto_phi_t.valor_adotado,
        atende_teto_s=s_adotado_mm <= teto_s.valor_adotado,
        atende_s_adicional=atende_adicional,
        atende_phi_long_maior_ou_igual_phi_t=(
            phi_longitudinal_mm >= phi_t_mm),
        nota_C55_a_C90=NOTA_C55_A_C90 if concreto.fck >= 55.0 else None,
        declaracoes=tuple(declaracoes),
    )
