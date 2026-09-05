"""Geometria do pilarete — dimensões-limite, gamma_n, raio de giração, cobrimento.

Ref.: ABNT NBR 6118:2023, item 13.2.3 e Tabela 13.1, p. 73
[rule: NBR6118-13.2.3-dimensoes-limites-pilarete]

Ref.: ABNT NBR 6118:2023, item 18.4.1, p. 152
[rule: NBR6118-18.4.1-campo-de-aplicacao-detalhamento]

Ref.: ABNT NBR 6118:2023, itens 7.4.7.1 a 7.4.7.6 e Tabela 7.2, nota (d), p. 20
[rule: NBR6118-Tab7.2-nota-d-cobrimento-pilarete]

[req: REQ-PILARETE-03-geometria-limite-e-recusas-duras]
[req: REQ-PILARETE-09-cobrimento-proprio-e-a-incompatibilidade-com-Sapata]
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from calc_core.estrutural.dominio import (
    DECLARADO_EM_TEXTO,
    ESCOPO_DESTA_VERSAO,
    RecusaForaDeDominio,
    exigir_positivo,
    exigir_um_de,
)

__all__ = [
    "CLASSES_DE_AGRESSIVIDADE",
    "COBRIMENTO_TAB7_2_VIGA_PILAR_MM",
    "PISO_NOTA_D_MM",
    "TOLERANCIA_DE_COBRIMENTO_MM",
    "ResultadoDimensoesLimites",
    "ConsistenciaDeCobrimento",
    "verificar_dimensoes_limites",
    "verificar_campo_18_4",
    "raio_de_giracao",
    "cobrimento_nominal_minimo",
    "cobrimento_implicito_pelas_barras",
    "exigir_cobrimento_consistente_com_as_barras",
]

CLASSES_DE_AGRESSIVIDADE: tuple[str, ...] = ("I", "II", "III", "IV")
"""Classe de agressividade ambiental (CAA), Tabela 6.1 / Tabela 7.2."""

COBRIMENTO_TAB7_2_VIGA_PILAR_MM: dict[str, float] = {
    "I": 25.0, "II": 30.0, "III": 40.0, "IV": 50.0,
}
"""Cobrimento nominal da linha "Viga/pilar" da Tabela 7.2 [mm], por CAA.

Ref.: ABNT NBR 6118:2023, Tabela 7.2, p. 20
[rule: NBR6118-Tab7.2-nota-d-cobrimento-pilarete]

Lido por LEITURA VISUAL do a2 (PDF p. 38 = impressa 20). A extração de texto
crua da tabela pareia errado por causa da CÉLULA MESCLADA da linha "Elementos
estruturais em contato com o solo", onde um único 30 mm cobre as classes I e
II — é o motivo de a leitura ser visual e não textual.
"""

PISO_NOTA_D_MM = 45.0
"""Piso absoluto de 45 mm da nota de rodapé (d) da Tabela 7.2 [mm].

Ref.: ABNT NBR 6118:2023, Tabela 7.2, nota (d), p. 20
[rule: NBR6118-Tab7.2-nota-d-cobrimento-pilarete]

Transcrição literal: "No trecho dos pilares em contato com o solo junto aos
elementos de fundação, a armadura deve ter cobrimento nominal >= 45 mm".
É PISO ABSOLUTO, independente da classe de agressividade, mas NÃO é teto: em
CAA IV a linha "Viga/pilar" dá 50 mm e governa.
"""


@dataclass(frozen=True)
class ResultadoDimensoesLimites:
    """Saída de :func:`verificar_dimensoes_limites`, para o memorial.

    Ref.: ABNT NBR 6118:2023, item 13.2.3 e Tabela 13.1, p. 73
    [rule: NBR6118-13.2.3-dimensoes-limites-pilarete]
    """

    b_min_cm: float
    """Menor dimensão da seção, em CENTÍMETROS (unidade de 13.2.3)."""

    h_max_cm: float
    """Maior dimensão da seção, em CENTÍMETROS."""

    area_cm2: float
    """Área bruta da seção [cm²], comparada com o piso de 360 cm²."""

    gamma_n: float
    """Coeficiente adicional da Tabela 13.1 (1,0 quando b_min >= 19 cm)."""

    gamma_n_aplicado: bool
    """True quando 14 <= b_min < 19 cm e os esforços foram majorados."""

    razao_h_sobre_b: float
    """h_max/b_min, comparada com o limite 5 de 18.4.1 (pilar-parede)."""


def verificar_dimensoes_limites(h_secao: float,
                                b_secao: float) -> ResultadoDimensoesLimites:
    """Impõe as TRÊS fronteiras duras de 13.2.3 e devolve gamma_n.

    Ref.: ABNT NBR 6118:2023, item 13.2.3 e Tabela 13.1, p. 73
    [rule: NBR6118-13.2.3-dimensoes-limites-pilarete]

    Ref.: ABNT NBR 6118:2023, item 18.4.1, p. 152
    [rule: NBR6118-18.4.1-campo-de-aplicacao-detalhamento]

    [req: REQ-PILARETE-03-geometria-limite-e-recusas-duras]

    ``h_secao`` e ``b_secao`` em METROS (convenção do pacote). A conversão
    para centímetros é feita AQUI, uma vez, porque gamma_n = 1,95 − 0,05·b é
    NÃO HOMOGÊNEA: o 1,95 é puro e o 0,05 carrega 1/cm. Passar ``b`` em
    metros devolveria 1,94 — número plausível, sem nenhum erro dimensional
    detectável (é o caso EMPIRICA ``NBR6118-13.2.3-gamma-n`` do
    ``tools/checar_dimensoes.py``). Daí o nome ``b_min_cm`` no resultado.

    ORDEM OBRIGATÓRIA DAS VERIFICAÇÕES, e a segunda é a que costuma passar
    batido:

    1. ``b_min < 14 cm`` -> PROIBIDO. Não existe gamma_n que autorize.
    2. ``A_c < 360 cm²`` -> PROIBIDO "em qualquer caso", INDEPENDENTE de b:
       um pilarete 19×18 cm passa em (1) (b = 18 >= 14) e reprova AQUI
       (A_c = 342 cm²). É teste obrigatório de GATE 3.
    3. ``14 <= b_min < 19 cm`` -> admissível SOMENTE com
       ``gamma_n = 1,95 − 0,05·b_min_cm`` majorando os esforços de cálculo.
       Aplicado e REGISTRADO no memorial, com o valor.
    4. ``h_max > 5·b_min`` -> é PILAR-PAREDE (18.5), FORA do escopo: RECUSA.

    NÃO DECLARADO NA FONTE, e decidido pelo a2: a ordem de aplicação de
    gamma_n em relação aos efeitos de 2ª ordem. A NOTA da Tabela 13.1 diz
    "esforços solicitantes FINAIS de cálculo". Como esta rodada só admite
    PILAR CURTO (2ª ordem local dispensada por 15.8.2), não existe "depois da
    2ª ordem" e a ambiguidade não se materializa.
    """
    exigir_positivo("h_secao", h_secao,
                    fonte="ABNT NBR 6118:2023, 13.2.3, p. 73",
                    apoio_no_ruleset="NBR6118-13.2.3-dimensoes-limites-pilarete")
    exigir_positivo("b_secao", b_secao,
                    fonte="ABNT NBR 6118:2023, 13.2.3, p. 73",
                    apoio_no_ruleset="NBR6118-13.2.3-dimensoes-limites-pilarete")

    b_min_cm = min(h_secao, b_secao) * 100.0
    h_max_cm = max(h_secao, b_secao) * 100.0
    area_cm2 = b_min_cm * h_max_cm

    # (1) piso absoluto de 14 cm.
    if b_min_cm < 14.0:
        raise RecusaForaDeDominio(
            parametro="b_min_cm (menor dimensão da seção do pilarete)",
            valor=round(b_min_cm, 4),
            intervalo=">= 14 cm",
            fonte="ABNT NBR 6118:2023, 13.2.3, p. 73 — 'em qualquer caso, não "
                  "se permite pilar com seção transversal de área inferior a "
                  "360 cm²' e a dimensão mínima de 19 cm reduzível a 14 cm "
                  "com gamma_n; abaixo de 14 cm não há gamma_n que autorize",
            forca=DECLARADO_EM_TEXTO,
            apoio_no_ruleset="NBR6118-13.2.3-dimensoes-limites-pilarete",
            sugestao=f"Obtido {b_min_cm:.2f} cm contra o limite de 14,00 cm.",
        )

    # (2) piso de área, INDEPENDENTE de b — a fronteira que passa batido.
    if area_cm2 < 360.0:
        raise RecusaForaDeDominio(
            parametro="area_da_secao_cm2",
            valor=round(area_cm2, 4),
            intervalo=">= 360 cm²",
            fonte="ABNT NBR 6118:2023, 13.2.3, p. 73 — piso de área válido "
                  "'em qualquer caso', independente de b_min",
            forca=DECLARADO_EM_TEXTO,
            apoio_no_ruleset="NBR6118-13.2.3-dimensoes-limites-pilarete",
            sugestao=(f"Obtido {area_cm2:.2f} cm² ({b_min_cm:.2f} × "
                      f"{h_max_cm:.2f} cm) contra o limite de 360,00 cm². "
                      "Atender b_min >= 14 cm NÃO dispensa este piso."),
        )

    # (3) gamma_n da Tabela 13.1, na faixa reduzida.
    if b_min_cm < 19.0:
        gamma_n = 1.95 - 0.05 * b_min_cm
        gamma_n_aplicado = True
    else:
        gamma_n = 1.0
        gamma_n_aplicado = False

    # (4) pilar-parede — fora do escopo.
    razao = h_max_cm / b_min_cm
    verificar_campo_18_4(h_max_cm=h_max_cm, b_min_cm=b_min_cm)

    return ResultadoDimensoesLimites(
        b_min_cm=b_min_cm,
        h_max_cm=h_max_cm,
        area_cm2=area_cm2,
        gamma_n=gamma_n,
        gamma_n_aplicado=gamma_n_aplicado,
        razao_h_sobre_b=razao,
    )


def verificar_campo_18_4(*, h_max_cm: float, b_min_cm: float) -> float:
    """Recusa pilar-parede (h_max > 5·b_min); devolve a razão h_max/b_min.

    Ref.: ABNT NBR 6118:2023, item 18.4.1, p. 152
    [rule: NBR6118-18.4.1-campo-de-aplicacao-detalhamento]
    [req: REQ-PILARETE-03-geometria-limite-e-recusas-duras]  (4)

    18.4 não se aplica a pilar-parede, que 18.5 trata com efeitos LOCALIZADOS
    de 2ª ordem — matéria não extraída e fora do escopo desta versão.

    A segunda fronteira de 18.4.1 ("não são válidas para as REGIÕES ESPECIAIS,
    ver Seção 21") foi decidida pelo a2 e não gera código aqui: 18.4 governa o
    FUSTE do pilarete; a região da junta é governada por 9.5.2.x (emenda por
    traspasse) e por 21.6 (junta de concretagem). O software não estende 18.4
    à região da junta e não usa a Seção 22 nesta versão.
    """
    razao = h_max_cm / b_min_cm
    if razao > 5.0:
        raise RecusaForaDeDominio(
            parametro="razao_h_max_sobre_b_min",
            valor=round(razao, 4),
            intervalo="<= 5,0",
            fonte="ABNT NBR 6118:2023, 18.4.1, p. 152 — acima de 5 o elemento "
                  "é PILAR-PAREDE, tratado por 18.5 com efeitos localizados "
                  "de 2ª ordem",
            forca=ESCOPO_DESTA_VERSAO,
            apoio_no_ruleset="NBR6118-18.4.1-campo-de-aplicacao-detalhamento",
            sugestao=(f"Obtido {razao:.4f} ({h_max_cm:.2f} / {b_min_cm:.2f} cm) "
                      "contra o limite de 5,0. Pilar-parede está fora do "
                      "escopo desta versão."),
        )
    return razao


def raio_de_giracao(dimensao_no_plano_de_flexao: float) -> float:
    """Raio de giração ``i`` da seção retangular bruta [m].

    Ref.: ABNT NBR 6118:2023, item 4.3, p. 6 (define o símbolo, não a expressão)
    [deriv: DER-GEOM-raio-de-giracao]

        i = sqrt(I/A);  para retângulo b×h em torno do eixo considerado,
        i = h/sqrt(12)  (o b cancela — álgebra exata, não aproximação)

    CALCULADO NO NÚCLEO, nunca pedido à UI e nunca digitado
    (REQ-PILARETE-05(3)): é geometria, não entrada de projeto.

    ``dimensao_no_plano_de_flexao`` é a dimensão da seção MEDIDA NO PLANO em
    que a peça flete — ``h_secao`` para a flexão em torno do eixo x,
    ``b_secao`` para a flexão em torno do eixo y. "Mínimo" é palavra da
    definição de 4.3 e tem consequência: quem avalia as duas direções e toma
    o MENOR ``i`` (isto é, o MAIOR lambda) é
    :func:`~calc_core.estrutural.pilarete.esbeltez.verificar_pilar_curto`.
    """
    exigir_positivo(
        "dimensao_no_plano_de_flexao", dimensao_no_plano_de_flexao,
        fonte="ABNT NBR 6118:2023, 4.3, p. 6 (definição de i)",
        apoio_no_ruleset="DER-GEOM-raio-de-giracao",
    )
    return dimensao_no_plano_de_flexao / math.sqrt(12.0)


def cobrimento_nominal_minimo(*, classe_de_agressividade: str,
                              phi_longitudinal_mm: float,
                              d_agregado_mm: float) -> float:
    """Cobrimento nominal mínimo do PILARETE [mm] — campo PRÓPRIO, não o da sapata.

    Ref.: ABNT NBR 6118:2023, itens 7.4.7.1 a 7.4.7.6 e Tabela 7.2, nota (d), p. 20
    [rule: NBR6118-Tab7.2-nota-d-cobrimento-pilarete]
    [req: REQ-PILARETE-09-cobrimento-proprio-e-a-incompatibilidade-com-Sapata]

        c_nom,pilarete = max(45 mm ;
                             Tabela 7.2 linha "Viga/pilar" para a CAA ;
                             phi_longitudinal ;
                             d_agregado/1,2)

    Medido à face externa do ESTRIBO (7.4.7.5), não à barra longitudinal.

    TRÊS DECISÕES DO a2 QUE O TEXTO NÃO TOMA POR SI, todas registradas:

    1. A nota (d) é PISO ABSOLUTO, independente da classe, mas NÃO é teto: em
       CAA IV a linha "Viga/pilar" dá 50 mm e governa. Toma-se o MÁXIMO.
    2. "Onde termina o trecho em contato com o solo" é NAO_DECLARADO_NA_FONTE.
       DECISÃO: aplicar os 45 mm ao PILARETE INTEIRO, do topo da sapata ao
       topo do pilarete — lado conservador, e evita inventar uma cota de
       transição que a Norma não define. Vai ao memorial como hipótese.
    3. A redução de 5 mm por classe de resistência superior à mínima e a de
       7.4.7.4 (Delta_c = 5 mm, que exige a ABNT NBR 9062, AUSENTE do acervo)
       NÃO são implementadas.

    INCOMPATIBILIDADE DELIBERADAMENTE NÃO CONSERTADA: ``Sapata.__init__``
    recebe UM único ``cobrimento`` para a peça inteira, e esse número
    atravessa o formulário, o schema ``.s7proj``, o relatório, as pranchas e o
    3D. O pilarete NÃO reusa esse campo e NÃO o altera nesta versão — mudar o
    significado do campo existente invalidaria aprovações de A6/A7 sobre
    ``ui/`` sem necessidade.
    """
    exigir_um_de(
        "classe_de_agressividade", classe_de_agressividade,
        CLASSES_DE_AGRESSIVIDADE,
        fonte="ABNT NBR 6118:2023, Tabela 7.2, p. 20",
        apoio_no_ruleset="NBR6118-Tab7.2-nota-d-cobrimento-pilarete",
    )
    exigir_positivo("phi_longitudinal_mm", phi_longitudinal_mm,
                    fonte="ABNT NBR 6118:2023, 7.4.7.2, p. 19",
                    apoio_no_ruleset="NBR6118-Tab7.2-nota-d-cobrimento-pilarete")
    exigir_positivo("d_agregado_mm", d_agregado_mm,
                    fonte="ABNT NBR 6118:2023, 7.4.7.6, p. 20",
                    apoio_no_ruleset="NBR6118-Tab7.2-nota-d-cobrimento-pilarete")
    return max(
        PISO_NOTA_D_MM,
        COBRIMENTO_TAB7_2_VIGA_PILAR_MM[classe_de_agressividade],
        phi_longitudinal_mm,
        d_agregado_mm / 1.2,
    )


TOLERANCIA_DE_COBRIMENTO_MM = 1.0e-6
"""Tolerância do cruzamento cobrimento × posições das barras [mm].

Ref.: ABNT NBR 6118:2023, item 7.4.7.5 e Tabela 7.2, nota (d), p. 20
[rule: NBR6118-Tab7.2-nota-d-cobrimento-pilarete]

É RUÍDO DE PONTO FLUTUANTE, e não margem de projeto: 1e-6 mm = 1 picômetro,
umas 8 ordens de grandeza acima do erro de representação de um cobrimento na
casa das dezenas de milímetros (~1e-14 mm) e umas 5 abaixo de qualquer
diferença que um projeto possa querer declarar. Nenhum afrouxamento cabe aqui
— uma tolerância "prática" de 0,1 mm ou 1 mm seria um cobrimento a menos
autorizado em silêncio, que é exatamente o que esta guarda existe para impedir.
"""


@dataclass(frozen=True)
class ConsistenciaDeCobrimento:
    """Cruzamento entre o cobrimento DECLARADO e o IMPLÍCITO nas barras.

    Ref.: ABNT NBR 6118:2023, itens 7.4.7.5 e Tabela 7.2, nota (d), p. 20
    [rule: NBR6118-Tab7.2-nota-d-cobrimento-pilarete]
    [req: REQ-PILARETE-09-cobrimento-proprio-e-a-incompatibilidade-com-Sapata]

    Os três números vão ao memorial: sem eles o leitor não tem como saber que
    o cruzamento foi feito, e um cruzamento que não aparece no memorial é
    indistinguível de um cruzamento que não existe.
    """

    cobrimento_declarado_mm: float
    cobrimento_minimo_mm: float
    cobrimento_implicito_no_plano_de_h_mm: float
    """c implícito por ``min(pos_h)``, na direção de ``h_secao`` [mm]."""
    cobrimento_implicito_no_plano_de_b_mm: float
    """c implícito por ``min(pos_b)``, na direção de ``b_secao`` [mm]."""

    @property
    def cobrimento_implicito_mm(self) -> float:
        """O MENOR dos dois — é ele que caracteriza a peça.

        Ref.: ABNT NBR 6118:2023, item 7.4.7.5, p. 20
        [rule: NBR6118-Tab7.2-nota-d-cobrimento-pilarete]
        """
        return min(self.cobrimento_implicito_no_plano_de_h_mm,
                   self.cobrimento_implicito_no_plano_de_b_mm)

    @property
    def linha_de_memorial(self) -> str:
        """Linha pronta, com os três números do cruzamento.

        Ref.: ABNT NBR 6118:2023, itens 7.4.7.5 e Tabela 7.2, nota (d), p. 20
        [rule: NBR6118-Tab7.2-nota-d-cobrimento-pilarete]
        [req: REQ-PILARETE-12-memorial-e-o-que-ele-e-obrigado-a-dizer]
        """
        return (
            "NBR 6118:2023, 7.4.7.5 (p. 20): CRUZAMENTO cobrimento × posições "
            "das barras — c implícito pelas posições declaradas = "
            f"{self.cobrimento_implicito_no_plano_de_h_mm:.2f} mm (plano de h) "
            f"e {self.cobrimento_implicito_no_plano_de_b_mm:.2f} mm (plano de "
            f"b), contra c declarado = {self.cobrimento_declarado_mm:.1f} mm. "
            "As posições das barras e o cobrimento declarado são DUAS fontes "
            "da MESMA grandeza (a distância da borda à armadura) e o software "
            "RECUSA quando as barras implicam cobrimento MENOR que o "
            "declarado — é dali que sai o d' de §17.4 e o braço de alavanca "
            "de §17.2.")


def cobrimento_implicito_pelas_barras(*, d_linha: float,
                                      phi_longitudinal_mm: float,
                                      phi_t_mm: float) -> float:
    """Cobrimento [mm] que a posição declarada da barra implica.

    Ref.: ABNT NBR 6118:2023, item 7.4.7.5 e Tabela 7.2, nota (d), p. 20
    [rule: NBR6118-Tab7.2-nota-d-cobrimento-pilarete]
    [req: REQ-PILARETE-09-cobrimento-proprio-e-a-incompatibilidade-com-Sapata]

        c = 1000·d' − phi_t − phi_longitudinal/2      [mm]

    ``d_linha`` em METROS (distância da borda ao CENTROIDE da barra, que é o
    que ``BarraLongitudinal.pos_h``/``.pos_b`` declaram); ``phi`` em
    MILÍMETROS. A identidade é a leitura aritmética de 7.4.7.5 — "o cobrimento
    é referido à armadura EXTERNA, face externa do ESTRIBO" —, com o estribo
    envolvendo a barra longitudinal: da face do concreto até o eixo da barra
    há o cobrimento, mais o diâmetro do estribo, mais meio diâmetro da barra.

    NÃO É VERIFICAÇÃO NORMATIVA, é a conversão entre as duas formas de
    declarar a MESMA distância. Quem verifica é
    :func:`exigir_cobrimento_consistente_com_as_barras`.
    """
    exigir_positivo("d_linha", d_linha,
                    fonte="ABNT NBR 6118:2023, 7.4.7.5, p. 20",
                    apoio_no_ruleset="NBR6118-Tab7.2-nota-d-cobrimento-pilarete")
    exigir_positivo("phi_longitudinal_mm", phi_longitudinal_mm,
                    fonte="ABNT NBR 6118:2023, 7.4.7.2, p. 19",
                    apoio_no_ruleset="NBR6118-Tab7.2-nota-d-cobrimento-pilarete")
    exigir_positivo("phi_t_mm", phi_t_mm,
                    fonte="ABNT NBR 6118:2023, 7.4.7.5, p. 20",
                    apoio_no_ruleset="NBR6118-Tab7.2-nota-d-cobrimento-pilarete")
    return d_linha * 1000.0 - phi_t_mm - phi_longitudinal_mm / 2.0


def exigir_cobrimento_consistente_com_as_barras(
    *,
    d_linha_no_plano_de_h: float,
    d_linha_no_plano_de_b: float,
    phi_longitudinal_mm: float,
    phi_t_mm: float,
    cobrimento_declarado_mm: float,
    cobrimento_minimo_mm: float,
) -> ConsistenciaDeCobrimento:
    """RECUSA quando as barras implicam cobrimento MENOR que o declarado.

    Ref.: ABNT NBR 6118:2023, item 7.4.7.5 e Tabela 7.2, nota (d), p. 20
    [rule: NBR6118-Tab7.2-nota-d-cobrimento-pilarete]
    [req: REQ-PILARETE-09-cobrimento-proprio-e-a-incompatibilidade-com-Sapata]

    DUAS FONTES DE VERDADE PARA A MESMA GRANDEZA FÍSICA, e é por isso que esta
    guarda existe. A distância da borda do concreto à armadura entra no
    software por DOIS canais independentes:

    1. ``cobrimento_declarado_mm``, que é comparado com o mínimo de 7.4.7 /
       Tabela 7.2 (:func:`cobrimento_nominal_minimo`) e produz a REPROVAÇÃO de
       durabilidade;
    2. ``BarraLongitudinal.pos_h``/``.pos_b``, de onde saem o ``d'`` de §17.4
       (e portanto ``V_Rd2`` e ``V_c0``) e os braços de alavanca da varredura
       de ``M_Rd`` de §17.2.

    Sem cruzamento, os dois canais NUNCA SE ENCONTRAM: bastava declarar 45 mm
    (atendendo nominalmente a nota (d)) e posicionar as barras como se o
    cobrimento fosse 30 mm para obter um ``d`` maior, um ``V_Rd2`` maior e um
    veredito ATENDIDO — do lado INSEGURO, em silêncio. Este é o mesmo padrão
    de guarda de :func:`~calc_core.estrutural.pilarete.detalhamento.verificar_estribos`
    para ``(d_util, V_Sd, V_Rd2)``: dados que descrevem a mesma coisa chegam
    coerentes ou não chegam.

    A GUARDA É DE UM LADO SÓ, e o lado é escolhido, não esquecido:

    * ``c_implícito < c_declarado`` -> RECUSA. O ``d`` estaria a favor da
      segurança que não existe e o cobrimento declarado seria ficção.
    * ``c_implícito > c_declarado`` -> SEGUE. As barras estão mais para dentro
      do que o declarado: o ``d``  sai MENOR (conservador em §17.4 e §17.2) e
      a verificação de durabilidade usa o MENOR dos dois (conservador em
      7.4.7). É também o que preserva REQ-PILARETE-09 como REPROVAÇÃO e não
      recusa: declarar 30 mm com barras posicionadas a 45 mm continua sendo
      reprovado pelo mínimo da Tabela 7.2, sem virar exceção.

    A CADEIA QUE ISSO FECHA, e ela só fecha com as duas metades: esta guarda dá
    ``c_implícito >= c_declarado`` e a reprovação de durabilidade dá
    ``c_declarado >= c_mín``; juntas, todo veredito ATENDIDO tem
    ``c_implícito >= c_mín``, que é o que REQ-PILARETE-09 exige da PEÇA — e não
    de um número declarado à parte.

    ``d_linha_*`` em METROS, ``phi_*`` e cobrimentos em MILÍMETROS. Os dois
    ``d'`` são os MESMOS que alimentam §17.4 (a camada mais próxima de cada
    borda); com arranjo assimétrico a face oposta poderia ter cobrimento menor,
    mas arranjo assimétrico já é RECUSADO por
    :func:`~calc_core.estrutural.pilarete.secao.verificar_elu_solicitacoes_normais`
    (17.2.5), de modo que ``min(pos_h) == h − max(pos_h)`` sempre que se chega
    até aqui.
    """
    c_h = cobrimento_implicito_pelas_barras(
        d_linha=d_linha_no_plano_de_h,
        phi_longitudinal_mm=phi_longitudinal_mm, phi_t_mm=phi_t_mm)
    c_b = cobrimento_implicito_pelas_barras(
        d_linha=d_linha_no_plano_de_b,
        phi_longitudinal_mm=phi_longitudinal_mm, phi_t_mm=phi_t_mm)
    consistencia = ConsistenciaDeCobrimento(
        cobrimento_declarado_mm=cobrimento_declarado_mm,
        cobrimento_minimo_mm=cobrimento_minimo_mm,
        cobrimento_implicito_no_plano_de_h_mm=c_h,
        cobrimento_implicito_no_plano_de_b_mm=c_b,
    )
    implicito = consistencia.cobrimento_implicito_mm
    if implicito < cobrimento_declarado_mm - TOLERANCIA_DE_COBRIMENTO_MM:
        plano = "h" if c_h <= c_b else "b"
        d_linha = (d_linha_no_plano_de_h if plano == "h"
                   else d_linha_no_plano_de_b)
        d_linha_coerente = (cobrimento_declarado_mm + phi_t_mm
                            + phi_longitudinal_mm / 2.0) / 1000.0
        raise RecusaForaDeDominio(
            parametro=("(cobrimento_declarado_mm, posições das barras) — "
                       f"plano de {plano}"),
            valor=(round(cobrimento_declarado_mm, 4), round(d_linha, 6)),
            intervalo=("cobrimento implícito pelas posições das barras >= "
                       "cobrimento declarado"),
            fonte="ABNT NBR 6118:2023, 7.4.7.5 e Tabela 7.2, nota (d), p. 20 — "
                  "o cobrimento é referido à face externa do ESTRIBO, de modo "
                  "que a posição do eixo da barra é c_nom + phi_t + phi/2 e as "
                  "duas declarações descrevem a MESMA distância",
            forca=DECLARADO_EM_TEXTO,
            apoio_no_ruleset="NBR6118-Tab7.2-nota-d-cobrimento-pilarete",
            sugestao=(
                f"Declarado c = {cobrimento_declarado_mm:.2f} mm, mas a barra "
                f"mais próxima da borda está a d' = {d_linha * 1000.0:.2f} mm "
                f"do eixo, o que com phi_t = {phi_t_mm:.2f} mm e phi = "
                f"{phi_longitudinal_mm:.2f} mm implica c = {implicito:.2f} mm "
                f"(mínimo exigido: {cobrimento_minimo_mm:.2f} mm). Um c "
                "implícito MENOR que o declarado aumenta d, aumenta V_Rd2 e "
                "aumenta M_Rd: é erro do lado INSEGURO, e o software não "
                "escolhe entre as duas declarações. Para o c declarado, as "
                f"barras teriam de estar a d' >= {d_linha_coerente * 1000.0:.2f}"
                " mm da borda."),
        )
    return consistencia
