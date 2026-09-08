"""Geometria do pilarete — dimensões-limite, gamma_n, raio de giração, cobrimento.

Ref.: ABNT NBR 6118:2023, item 13.2.3 e Tabela 13.1, p. 73
[rule: NBR6118-13.2.3-dimensoes-limites-pilarete]

Ref.: ABNT NBR 6118:2023, item 18.4.1, p. 152
[rule: NBR6118-18.4.1-campo-de-aplicacao-detalhamento]

Ref.: ABNT NBR 6118:2023, itens 7.4.7.1 a 7.4.7.6 e Tabela 7.2, nota (d), p. 20
[rule: NBR6118-Tab7.2-nota-d-cobrimento-pilarete]

Ref.: ABNT NBR 6118:2023, itens 18.4.2.1 e 18.4.2.2, p. 153
[rule: NBR6118-18.4.2-armaduras-longitudinais-pilarete]

[req: REQ-PILARETE-03-geometria-limite-e-recusas-duras]
[req: REQ-PILARETE-09-cobrimento-proprio-e-a-incompatibilidade-com-Sapata]
[req: REQ-PILARETE-20-cruzar-as-outras-tres-declaracoes-redundantes]

AS GUARDAS DE COERÊNCIA DAS DECLARAÇÕES REDUNDANTES MORAM AQUI, todas, e é
deliberado: ``DadosDoPilarete`` declara QUATRO grandezas físicas por DOIS
canais independentes cada uma — o cobrimento (declarado × posições das
barras), a bitola (``phi_longitudinal_mm`` × ``BarraLongitudinal.area``), a
contagem de barras (``numero_de_barras`` × ``len(barras)``) e o espaçamento
(``espacamento_entre_eixos_mm`` × as posições). Nenhuma checagem dimensional
pega a divergência entre dois canais da MESMA grandeza (área é m² nas duas
leituras, contagem é adimensional nas duas), de modo que a única defesa é o
cruzamento explícito. Todos são chamados no passo (6-bis) de
:func:`~calc_core.estrutural.pilarete.elemento.verificar_pilarete`, ANTES de
§17.2 e de §17.4.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from calc_core.estrutural.dominio import (
    DECLARADO_EM_TEXTO,
    DECLARADO_PELO_USUARIO,
    ESCOPO_DESTA_VERSAO,
    RecusaForaDeDominio,
    exigir_positivo,
    exigir_um_de,
)
from calc_core.sapata_isolada.materiais import area_barra

if TYPE_CHECKING:  # pragma: no cover - só para tipagem estática
    from calc_core.estrutural.pilarete.secao import BarraLongitudinal

__all__ = [
    "CLASSES_DE_AGRESSIVIDADE",
    "COBRIMENTO_TAB7_2_VIGA_PILAR_MM",
    "PISO_NOTA_D_MM",
    "TOLERANCIA_DE_COBRIMENTO_MM",
    "TOLERANCIA_RELATIVA_DE_AREA_DA_BARRA",
    "TOLERANCIA_DE_ESPACAMENTO_MM",
    "TOLERANCIA_DE_POSICAO_M",
    "ResultadoDimensoesLimites",
    "ConsistenciaDeCobrimento",
    "ConsistenciaDaArmaduraDeclarada",
    "verificar_dimensoes_limites",
    "verificar_campo_18_4",
    "raio_de_giracao",
    "cobrimento_nominal_minimo",
    "cobrimento_implicito_pelas_barras",
    "exigir_cobrimento_consistente_com_as_barras",
    "bitola_implicita_pela_area",
    "espacamentos_entre_eixos_pelas_barras",
    "exigir_armadura_consistente_com_as_barras",
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


# ---------------------------------------------------------------------------
# REQ-PILARETE-20 — os OUTROS TRÊS pares de declarações redundantes
# ---------------------------------------------------------------------------

TOLERANCIA_RELATIVA_DE_AREA_DA_BARRA = 1.0e-9
"""Tolerância RELATIVA do cruzamento área da barra × bitola declarada [-].

Ref.: ABNT NBR 6118:2023, item 18.4.2.1, p. 153
[rule: NBR6118-18.4.2-armaduras-longitudinais-pilarete]
[req: REQ-PILARETE-20-cruzar-as-outras-tres-declaracoes-redundantes]  (a)

É RUÍDO DE PONTO FLUTUANTE, não margem de projeto: 1e-9 relativo é ~5 ordens
de grandeza acima do erro de representação de ``math.pi * (phi/1000)**2 / 4``
e ~7 abaixo da menor diferença que qualquer arredondamento comercial produz
(declarar 2,00 cm² para phi 16 mm, cuja área exata é 2,0106 cm², é 5e-3
relativo). Afrouxá-la para "0,5 %" autorizaria em silêncio uma área de barra
MAIOR que a da bitola declarada, que é o lado INSEGURO desta guarda.
"""

TOLERANCIA_DE_ESPACAMENTO_MM = 1.0e-6
"""Tolerância do cruzamento espaçamento declarado × posições das barras [mm].

Ref.: ABNT NBR 6118:2023, item 18.4.2.2, p. 153
[rule: NBR6118-18.4.2-armaduras-longitudinais-pilarete]
[req: REQ-PILARETE-20-cruzar-as-outras-tres-declaracoes-redundantes]  (c)

Mesma doutrina e mesma ordem de grandeza de
:data:`TOLERANCIA_DE_COBRIMENTO_MM`: 1e-6 mm é um picômetro, ruído de
representação e nada mais.
"""

TOLERANCIA_DE_POSICAO_M = 1.0e-9
"""Agrupamento de posições de barras em CAMADAS [m].

Ref.: ABNT NBR 6118:2023, item 18.4.2.2, p. 153
[rule: NBR6118-18.4.2-armaduras-longitudinais-pilarete]
[req: REQ-PILARETE-20-cruzar-as-outras-tres-declaracoes-redundantes]  (c)

Duas barras cujas coordenadas diferem menos que 1 nanômetro estão na MESMA
camada — a diferença é aritmética de ponto flutuante (``h - d_linha``
calculado de duas formas), não arranjo. Sem esse agrupamento, um par de
camadas "distintas" a 1e-16 m produziria um espaçamento real ~0 e a guarda
recusaria toda seção legítima.
"""


def bitola_implicita_pela_area(area: float) -> float:
    """Bitola [mm] que a ÁREA declarada de uma barra implica.

    Ref.: ABNT NBR 6118:2023, item 18.4.2.1, p. 153
    [rule: NBR6118-18.4.2-armaduras-longitudinais-pilarete]
    [req: REQ-PILARETE-20-cruzar-as-outras-tres-declaracoes-redundantes]  (a)

        phi = 1000 · sqrt(4·A/pi)      [mm], com A em m²

    Inversa exata de :func:`~calc_core.sapata_isolada.materiais.area_barra`.
    NÃO É VERIFICAÇÃO NORMATIVA: é a conversão entre as duas formas de
    declarar a MESMA barra, e existe para que a mensagem de recusa e o memorial
    possam citar os dois números na mesma unidade. Quem verifica é
    :func:`exigir_armadura_consistente_com_as_barras`.
    """
    exigir_positivo("area", area,
                    fonte="ABNT NBR 6118:2023, 18.4.2.1, p. 153",
                    apoio_no_ruleset="NBR6118-18.4.2-armaduras-longitudinais-"
                                     "pilarete")
    return 1000.0 * math.sqrt(4.0 * area / math.pi)


def espacamentos_entre_eixos_pelas_barras(
    barras: Sequence["BarraLongitudinal"],
) -> tuple[float, ...]:
    """Espaçamentos entre eixos [mm] que as POSIÇÕES declaradas implicam.

    Ref.: ABNT NBR 6118:2023, item 18.4.2.2, p. 153
    [rule: NBR6118-18.4.2-armaduras-longitudinais-pilarete]
    [req: REQ-PILARETE-20-cruzar-as-outras-tres-declaracoes-redundantes]  (c)

    Em cada direção (``pos_h`` e ``pos_b``), as barras são agrupadas nas
    CAMADAS distintas que ocupam (tolerância :data:`TOLERANCIA_DE_POSICAO_M`) e
    devolvem-se as diferenças entre camadas CONSECUTIVAS. Numa seção retangular
    com armadura em anel — barras nos vértices e, quando houver, barras
    intermediárias nas faces, que é o arranjo que 18.4.2.2 governa — essas
    diferenças SÃO os espaçamentos entre eixos de barras vizinhas ao longo de
    cada face: 4 barras em 30×30 com d' = 5,8 cm dão (184 mm, 184 mm); 8 barras
    (vértices + meio de face) dão (92, 92, 92, 92) mm.

    HIPÓTESE GEOMÉTRICA DECLARADA, e ela é do software, não da Norma: o
    espaçamento entre eixos é medido POR DIREÇÃO, ao longo das faces. Um
    arranjo que não seja em anel (barras no interior da seção) produziria aqui
    diferenças entre camadas que não são distâncias entre barras vizinhas —
    para esse arranjo o número declarado teria de ser reconferido pelo
    projetista. O pacote não gera esse arranjo e não o recusa: ele está fora do
    que 18.4.2.2 descreve.

    NÃO É VERIFICAÇÃO NORMATIVA. Quem verifica é
    :func:`exigir_armadura_consistente_com_as_barras` (o cruzamento) e
    :func:`~calc_core.estrutural.pilarete.detalhamento.verificar_armadura_longitudinal`
    (os limites de 18.4.2.2).
    """
    casas = max(0, -int(round(math.log10(TOLERANCIA_DE_POSICAO_M))))
    espacamentos: list[float] = []
    for coordenada in ("pos_h", "pos_b"):
        camadas = sorted({round(getattr(barra, coordenada), casas)
                          for barra in barras})
        espacamentos.extend(
            (b - a) * 1000.0 for a, b in zip(camadas, camadas[1:]))
    return tuple(espacamentos)


@dataclass(frozen=True)
class ConsistenciaDaArmaduraDeclarada:
    """Cruzamento dos TRÊS pares redundantes de declaração da armadura.

    Ref.: ABNT NBR 6118:2023, itens 18.4.2.1 e 18.4.2.2, p. 153
    [rule: NBR6118-18.4.2-armaduras-longitudinais-pilarete]
    [rule: NBR6118-17.3.5.3-armaduras-limite-pilarete]
    [req: REQ-PILARETE-20-cruzar-as-outras-tres-declaracoes-redundantes]

    Os pares e o consumidor de cada canal:

    ==== ============================= ==================================
    par  canal A (declarado)           canal B (a tupla ``barras``)
    ==== ============================= ==================================
    (1)  ``phi_longitudinal_mm``       ``BarraLongitudinal.area``
         18.4.2.1, espaçamento livre,  A_s de 17.3.5.3, varredura de M_Rd
         cobrimento, ell_b de 9.5.2.3  de 17.2.2, N_Rd0
    (2)  ``numero_de_barras``          ``len(barras)``
         18.4.2.2 (uma por vértice)    tudo que integra a seção
    (3)  ``espacamento_entre_eixos``   ``pos_h`` / ``pos_b``
         os DOIS limites de 18.4.2.2   d' de §17.4 e §17.2
    ==== ============================= ==================================

    Se uma instância existe, os três cruzamentos PASSARAM. Os números vão ao
    memorial pela razão já escrita em :class:`ConsistenciaDeCobrimento`: um
    cruzamento que não aparece no memorial é indistinguível de um cruzamento
    que não existe.
    """

    phi_longitudinal_declarado_mm: float
    area_da_bitola_declarada: float
    """pi·phi²/4 da bitola DECLARADA [m²] — o teto de cada barra."""
    areas_declaradas_nas_barras: tuple[float, ...]
    """Área de cada ``BarraLongitudinal`` [m²], na ordem da tupla."""
    numero_de_barras_declarado: int
    numero_de_barras_nas_posicoes: int
    espacamento_entre_eixos_declarado_mm: float
    espacamentos_entre_eixos_pelas_posicoes_mm: tuple[float, ...]

    @property
    def bitola_implicita_maxima_mm(self) -> float:
        """Bitola implicada pela MAIOR área declarada nas barras [mm].

        Ref.: ABNT NBR 6118:2023, item 18.4.2.1, p. 153
        [rule: NBR6118-18.4.2-armaduras-longitudinais-pilarete]

        É a MAIOR porque é ela que a guarda de (a) compara com a bitola
        declarada: uma única barra com área acima de pi·phi²/4 já infla A_s.
        """
        return bitola_implicita_pela_area(max(self.areas_declaradas_nas_barras))

    @property
    def espacamento_real_minimo_mm(self) -> float:
        """Menor espaçamento entre eixos que as posições implicam [mm].

        Ref.: ABNT NBR 6118:2023, item 18.4.2.2, p. 153
        [rule: NBR6118-18.4.2-armaduras-longitudinais-pilarete]

        É o que governa o PISO de 18.4.2.2 (espaçamento livre >= max(20 mm;
        phi; 1,2·d_agr)) — e é por isso que a guarda recusa um declarado MAIOR
        que ele.
        """
        return min(self.espacamentos_entre_eixos_pelas_posicoes_mm)

    @property
    def espacamento_real_maximo_mm(self) -> float:
        """Maior espaçamento entre eixos que as posições implicam [mm].

        Ref.: ABNT NBR 6118:2023, item 18.4.2.2, p. 153
        [rule: NBR6118-18.4.2-armaduras-longitudinais-pilarete]

        É o que governa o TETO de 18.4.2.2 (entre eixos <= min(2·b_mín;
        400 mm)) — e é este valor, não o declarado, que
        :func:`~calc_core.estrutural.pilarete.detalhamento.verificar_armadura_longitudinal`
        compara com o teto (ver a alínea (c) de
        :func:`exigir_armadura_consistente_com_as_barras`).
        """
        return max(self.espacamentos_entre_eixos_pelas_posicoes_mm)

    @property
    def linhas_de_memorial(self) -> tuple[str, ...]:
        """Uma linha por par cruzado, com os DOIS números de cada par.

        Ref.: ABNT NBR 6118:2023, itens 18.4.2.1 e 18.4.2.2, p. 153
        [rule: NBR6118-18.4.2-armaduras-longitudinais-pilarete]
        [req: REQ-PILARETE-12-memorial-e-o-que-ele-e-obrigado-a-dizer]
        [req: REQ-PILARETE-20-cruzar-as-outras-tres-declaracoes-redundantes]
        """
        espacamentos = ", ".join(
            f"{s:.2f}"
            for s in self.espacamentos_entre_eixos_pelas_posicoes_mm)
        return (
            "NBR 6118:2023, 18.4.2.1 (p. 153): CRUZAMENTO bitola × áreas das "
            f"barras — phi declarado = "
            f"{self.phi_longitudinal_declarado_mm:.2f} mm (área "
            f"{self.area_da_bitola_declarada * 1e4:.4f} cm² por barra) contra "
            f"a MAIOR área declarada na tupla de barras, "
            f"{max(self.areas_declaradas_nas_barras) * 1e4:.4f} cm² "
            f"(bitola implícita {self.bitola_implicita_maxima_mm:.2f} mm). O "
            "software RECUSA área de barra MAIOR que a da bitola declarada: "
            "ela infla A_s, M_Rd e N_Rd0 sem tocar em nenhuma verificação de "
            "detalhamento, que lê o phi declarado.",
            "NBR 6118:2023, 18.4.2.2 (p. 153): CRUZAMENTO contagem — "
            f"numero_de_barras declarado = {self.numero_de_barras_declarado} "
            f"contra len(barras) = {self.numero_de_barras_nas_posicoes}. São a "
            "contagem da MESMA coisa e a guarda é a IGUALDADE: o inteiro "
            "declarado alimenta o mínimo de uma barra por vértice e a tupla "
            "alimenta A_s e toda a geometria.",
            "NBR 6118:2023, 18.4.2.2 (p. 153): CRUZAMENTO espaçamento × "
            "posições das barras — espaçamento entre eixos declarado = "
            f"{self.espacamento_entre_eixos_declarado_mm:.2f} mm contra os "
            f"espaçamentos que as posições declaradas implicam ({espacamentos})"
            f" mm, mínimo {self.espacamento_real_minimo_mm:.2f} mm e máximo "
            f"{self.espacamento_real_maximo_mm:.2f} mm. O PISO de 18.4.2.2 é "
            "verificado com o DECLARADO (que a guarda obriga a ser <= o mínimo "
            "real) e o TETO com o MÁXIMO REAL — o mesmo número servia aos dois "
            "limites, de sinais contrários, e nenhum deles olhava para as "
            "barras.",
        )


def exigir_armadura_consistente_com_as_barras(
    *,
    barras: Sequence["BarraLongitudinal"],
    phi_longitudinal_mm: float,
    numero_de_barras: int,
    espacamento_entre_eixos_mm: float,
) -> ConsistenciaDaArmaduraDeclarada:
    """RECUSA quando bitola, contagem ou espaçamento divergem das ``barras``.

    Ref.: ABNT NBR 6118:2023, itens 18.4.2.1 e 18.4.2.2, p. 153
    [rule: NBR6118-18.4.2-armaduras-longitudinais-pilarete]

    Ref.: ABNT NBR 6118:2023, item 17.3.5.3, p. 133
    [rule: NBR6118-17.3.5.3-armaduras-limite-pilarete]

    [req: REQ-PILARETE-20-cruzar-as-outras-tres-declaracoes-redundantes]

    MESMO DEFEITO, MESMO DESENHO DE GUARDA de
    :func:`exigir_cobrimento_consistente_com_as_barras`: duas fontes de verdade
    para a MESMA grandeza física, sem cruzamento, uma delas divergindo em
    silêncio. Medido por execução pelo a2 na geometria de 30×30, C25, CA-50,
    N_d = 1000 kN, 4 barras, phi DECLARADO 16 mm e barras com a área de phi
    25 mm: o índice de inclusão da envoltória mínima cai de 1,1257 para 0,6978
    com M_Sd,x = M_Sd,y = 36 kN·m e o veredito VIRA de NÃO ATENDIDO para
    ATENDIDO, com todo o detalhamento continuando "atendido" porque lê o phi
    declarado. Nenhuma checagem dimensional pega: área é m² nas duas leituras.

    (a) ÁREA × BITOLA — guarda ASSIMÉTRICA, e o lado é escolhido:

        * ``area > pi·phi²/4`` -> RECUSA. É o lado que infla A_s (17.3.5.3.1),
          M_Rd (17.2.2) e N_Rd0 sem tocar em nenhuma verificação de
          detalhamento.
        * ``area <= pi·phi²/4`` -> SEGUE. Resolve de graça o arredondamento
          comercial legítimo (2,00 cm² declarados para phi 16 mm, cuja área
          exata é 2,0106 cm²), que é CONSERVADOR em M_Rd, e mantém a mesma
          assimetria da guarda irmã de cobrimento.

        RESÍDUO DECLARADO desta assimetria, dito para que o a2 possa
        reconferi-lo: uma sub-declaração UNIFORME e grande (phi 16 declarado
        com todas as barras de phi 8) é conservadora em A_s, M_Rd, ell_b,
        cobrimento e espaçamento livre, mas passaria pelo piso de phi >= 10 mm
        de 18.4.2.1, que lê o phi declarado. O memorial imprime a bitola
        implícita pelas áreas ao lado da declarada, de modo que o caso é
        AUDITÁVEL por leitura; fechá-lo exigiria um phi POR BARRA, que é
        mudança de API e de escopo.

    (a-bis) BITOLAS MISTAS — RECUSA, e a decisão é do a5 (o requisito manda
        escolher entre admitir um phi por barra ou recusar). Recusa-se porque
        TODO o detalhamento — 18.4.2.1, o espaçamento livre, o cobrimento
        implícito e o ell_b de 9.5.2.3 — é verificado contra um phi ÚNICO, e
        não existe leitura conservadora de "um phi só" para um conjunto de
        bitolas diferentes: o phi maior é conservador no espaçamento livre e no
        ell_b, o menor é conservador no piso de 18.4.2.1. Aceitar em silêncio é
        que está PROIBIDO. Admitir um phi por barra é mudança de API e fica
        para quando houver requisito que a peça.

    (b) CONTAGEM — IGUALDADE. Não há lado conservador: ``numero_de_barras`` e
        ``len(barras)`` contam a MESMA coisa. Declarar 4 e montar 2 barras
        satisfaz "uma barra por vértice" (18.4.2.2) com metade da armadura;
        declarar 2 e montar 4 reprova por 18.4.2.2 uma seção que a tem.

    (c) ESPAÇAMENTO — o par que o requisito manda desenhar POR EXTENSO, porque
        o mesmo número serve a DOIS limites de sinal contrário em 18.4.2.2
        (espaçamento livre >= max(20 mm; phi; 1,2·d_agr) e espaçamento entre
        eixos <= min(2·b_mín; 400 mm)). Nenhum valor declarado é conservador
        nos dois ao mesmo tempo quando as duas direções têm espaçamentos
        diferentes (uma seção 40×25 com 4 barras tem 284 mm numa direção e
        134 mm na outra), e exigir igualdade com um deles recusaria seções
        retangulares perfeitamente legítimas. O desenho adotado é:

        1. o DECLARADO tem de ser ``<=`` o MENOR espaçamento real (guarda
           assimétrica, aqui): declarar mais do que existe faria o piso ser
           verificado sobre um vão livre que a peça não tem — lado INSEGURO.
           Declarar menos é conservador no piso e SEGUE;
        2. o TETO deixa de ler o declarado e passa a ler o MÁXIMO REAL das
           posições (em
           :func:`~calc_core.estrutural.pilarete.detalhamento.verificar_armadura_longitudinal`,
           por ``espacamento_entre_eixos_maximo_real_mm``). Sem isso, uma seção
           90×20 com 4 barras declararia 84 mm (a direção curta) e esconderia
           os 784 mm da direção longa, que 18.4.2.2 REPROVA — e reprovar é o
           que tem de acontecer, não recusar: excesso de espaçamento é defeito
           de PROJETO, não entrada fora de domínio.

        As duas metades juntas dão: piso verificado com valor ``<=`` o real e
        teto verificado com o real. É o análogo da cadeia fechada da guarda de
        cobrimento.

    PENDENTE DE RECONFERÊNCIA PELO a2, e está escrito porque o requisito o
    exige com todas as letras: a alínea (c) e a decisão de (a-bis) são desenho
    do a5 e não transcrição de norma; o a2 as reconfere antes de aprovar.
    """
    exigir_positivo("phi_longitudinal_mm", phi_longitudinal_mm,
                    fonte="ABNT NBR 6118:2023, 18.4.2.1, p. 153",
                    apoio_no_ruleset="NBR6118-18.4.2-armaduras-longitudinais-"
                                     "pilarete")
    exigir_positivo("espacamento_entre_eixos_mm", espacamento_entre_eixos_mm,
                    fonte="ABNT NBR 6118:2023, 18.4.2.2, p. 153",
                    apoio_no_ruleset="NBR6118-18.4.2-armaduras-longitudinais-"
                                     "pilarete")
    if not barras:
        raise RecusaForaDeDominio(
            parametro="barras", valor=(),
            intervalo="ao menos uma barra por vértice (4 na seção retangular)",
            fonte="ABNT NBR 6118:2023, 18.4.2.2, p. 153 — a armadura "
                  "longitudinal do pilar tem no mínimo uma barra por vértice",
            forca=DECLARADO_PELO_USUARIO,
            apoio_no_ruleset="NBR6118-18.4.2-armaduras-longitudinais-pilarete",
            sugestao="Sem barras declaradas não há o que cruzar com "
                     f"numero_de_barras = {numero_de_barras}, com phi = "
                     f"{phi_longitudinal_mm:.2f} mm nem com o espaçamento "
                     f"declarado de {espacamento_entre_eixos_mm:.2f} mm.")

    # (b) CONTAGEM — igualdade, e é a mais barata das três.
    if numero_de_barras != len(barras):
        raise RecusaForaDeDominio(
            parametro="(numero_de_barras, len(barras))",
            valor=(numero_de_barras, len(barras)),
            intervalo="numero_de_barras == len(barras)",
            fonte="ABNT NBR 6118:2023, 18.4.2.2, p. 153 — o mínimo de uma "
                  "barra por vértice é verificado sobre o INTEIRO declarado, "
                  "enquanto A_s (17.3.5.3.1), a varredura de M_Rd (17.2.2) e "
                  "o d' de §17.4 saem da TUPLA de barras",
            forca=DECLARADO_EM_TEXTO,
            apoio_no_ruleset="NBR6118-18.4.2-armaduras-longitudinais-pilarete",
            sugestao=(
                f"Declarado numero_de_barras = {numero_de_barras} e montadas "
                f"{len(barras)} barras na tupla. São a contagem da MESMA "
                "coisa e não há lado conservador: declarar mais do que se "
                "monta satisfaz 18.4.2.2 com armadura que não existe, e "
                "declarar menos reprova uma seção que a tem. O software não "
                "escolhe entre as duas declarações — corrija a que estiver "
                "errada."),
        )

    areas = tuple(barra.area for barra in barras)
    for indice, area in enumerate(areas):
        exigir_positivo(f"barras[{indice}].area", area,
                        fonte="ABNT NBR 6118:2023, 17.2.2, p. 120",
                        apoio_no_ruleset="NBR6118-17.3.5.3-armaduras-limite-"
                                         "pilarete")

    # (a-bis) BITOLAS MISTAS — recusadas: todo o detalhamento usa um phi único.
    area_minima, area_maxima = min(areas), max(areas)
    if area_maxima - area_minima > TOLERANCIA_RELATIVA_DE_AREA_DA_BARRA * area_maxima:
        raise RecusaForaDeDominio(
            parametro="áreas das barras (bitolas mistas)",
            valor=(round(area_minima, 12), round(area_maxima, 12)),
            intervalo="todas as barras com a MESMA área",
            fonte="ABNT NBR 6118:2023, 18.4.2.1 e 18.4.2.2, p. 153 — o piso de "
                  "phi >= 10 mm, o teto de phi <= b_mín/8, o espaçamento livre "
                  "e o ell_b de 9.5.2.3 são verificados contra um phi ÚNICO",
            forca=ESCOPO_DESTA_VERSAO,
            apoio_no_ruleset="NBR6118-18.4.2-armaduras-longitudinais-pilarete",
            sugestao=(
                f"As barras declaram áreas diferentes entre si — de "
                f"{area_minima * 1e4:.4f} cm² (bitola implícita "
                f"{bitola_implicita_pela_area(area_minima):.2f} mm) a "
                f"{area_maxima * 1e4:.4f} cm² (bitola implícita "
                f"{bitola_implicita_pela_area(area_maxima):.2f} mm) — e o "
                "pacote verifica TODO o detalhamento contra um phi único "
                f"({phi_longitudinal_mm:.2f} mm declarado). Não existe leitura "
                "conservadora de um phi só para bitolas diferentes: a maior é "
                "conservadora no espaçamento livre e no ell_b, a menor no piso "
                "de 18.4.2.1. Declare uma seção com bitola ÚNICA. É limite "
                "desta versão do software, não da Norma."),
        )

    # (a) ÁREA × BITOLA — recusa só do lado que INFLA a armadura.
    area_da_bitola = area_barra(phi_longitudinal_mm)
    teto_de_area = area_da_bitola * (1.0 + TOLERANCIA_RELATIVA_DE_AREA_DA_BARRA)
    if area_maxima > teto_de_area:
        raise RecusaForaDeDominio(
            parametro="(phi_longitudinal_mm, BarraLongitudinal.area)",
            valor=(phi_longitudinal_mm, round(area_maxima, 12)),
            intervalo="área de cada barra <= pi·phi²/4 da bitola declarada",
            fonte="ABNT NBR 6118:2023, 18.4.2.1 (p. 153) e 17.2.2 (p. 120) — a "
                  "bitola declarada governa o detalhamento (phi >= 10 mm, phi "
                  "<= b_mín/8, espaçamento livre, cobrimento, ell_b de "
                  "9.5.2.3) e a ÁREA declarada em cada barra governa A_s "
                  "(17.3.5.3.1), a varredura de M_Rd (17.2.2) e N_Rd0: são a "
                  "MESMA barra",
            forca=DECLARADO_EM_TEXTO,
            apoio_no_ruleset="NBR6118-18.4.2-armaduras-longitudinais-pilarete",
            sugestao=(
                f"Declarado phi = {phi_longitudinal_mm:.2f} mm, cuja área é "
                f"{area_da_bitola * 1e4:.4f} cm² por barra, mas a tupla de "
                f"barras traz até {area_maxima * 1e4:.4f} cm² por barra — área "
                f"de uma bitola de {bitola_implicita_pela_area(area_maxima):.2f}"
                " mm. Área MAIOR que a da bitola declarada aumenta A_s, "
                "aumenta M_Rd e aumenta N_Rd0 enquanto TODO o detalhamento "
                "continua sendo verificado contra o phi declarado: é erro do "
                "lado INSEGURO, e nenhuma checagem dimensional o pega (área é "
                "m² nas duas leituras). Área MENOR ou igual segue, porque é "
                "conservadora e cobre o arredondamento comercial."),
        )

    # (c) ESPAÇAMENTO × POSIÇÕES — assimétrica no piso; o teto passa a ler o
    # máximo real (ver a alínea (c) do docstring).
    espacamentos = espacamentos_entre_eixos_pelas_barras(barras)
    if not espacamentos:
        raise RecusaForaDeDominio(
            parametro="posições das barras (pos_h, pos_b)",
            valor=tuple((barra.pos_h, barra.pos_b) for barra in barras),
            intervalo="ao menos duas camadas distintas em alguma direção",
            fonte="ABNT NBR 6118:2023, 18.4.2.2, p. 153 — o espaçamento entre "
                  "eixos só existe entre barras vizinhas em camadas distintas",
            forca=DECLARADO_PELO_USUARIO,
            apoio_no_ruleset="NBR6118-18.4.2-armaduras-longitudinais-pilarete",
            sugestao=(
                "Todas as barras declaradas ocupam a MESMA posição nas duas "
                "direções, de modo que não há espaçamento real com que cruzar "
                f"o declarado ({espacamento_entre_eixos_mm:.2f} mm). O arranjo "
                "mínimo de 18.4.2.2 é uma barra por vértice."),
        )
    consistencia = ConsistenciaDaArmaduraDeclarada(
        phi_longitudinal_declarado_mm=phi_longitudinal_mm,
        area_da_bitola_declarada=area_da_bitola,
        areas_declaradas_nas_barras=areas,
        numero_de_barras_declarado=numero_de_barras,
        numero_de_barras_nas_posicoes=len(barras),
        espacamento_entre_eixos_declarado_mm=espacamento_entre_eixos_mm,
        espacamentos_entre_eixos_pelas_posicoes_mm=espacamentos,
    )
    minimo_real = consistencia.espacamento_real_minimo_mm
    if espacamento_entre_eixos_mm > minimo_real + TOLERANCIA_DE_ESPACAMENTO_MM:
        raise RecusaForaDeDominio(
            parametro="(espacamento_entre_eixos_mm, posições das barras)",
            valor=(round(espacamento_entre_eixos_mm, 6), round(minimo_real, 6)),
            intervalo=("espaçamento declarado <= menor espaçamento entre eixos "
                       "implicado pelas posições das barras"),
            fonte="ABNT NBR 6118:2023, 18.4.2.2, p. 153 — o espaçamento livre "
                  "mínimo, na seção corrente e na região de emenda, é "
                  "verificado a partir do espaçamento entre eixos declarado, "
                  "enquanto as posições das barras são a geometria real da "
                  "seção",
            forca=DECLARADO_EM_TEXTO,
            apoio_no_ruleset="NBR6118-18.4.2-armaduras-longitudinais-pilarete",
            sugestao=(
                f"Declarado espaçamento entre eixos = "
                f"{espacamento_entre_eixos_mm:.2f} mm, mas as posições "
                f"declaradas implicam espaçamentos de "
                + ", ".join(f"{s:.2f}" for s in espacamentos)
                + f" mm — o MENOR é {minimo_real:.2f} mm. Declarar mais do que "
                "existe faz o piso de 18.4.2.2 (espaçamento livre >= max(20 "
                "mm; phi; 1,2·d_agr), inclusive na emenda com as barras "
                "duplicadas) ser verificado sobre um vão livre que a peça não "
                "tem: é erro do lado INSEGURO. Declarar o MENOR espaçamento "
                "real, ou menos, segue — é conservador. O TETO de 18.4.2.2 "
                "(<= min(2·b_mín; 400 mm)) NÃO depende deste número: é "
                "verificado contra o MAIOR espaçamento real."),
        )
    return consistencia
