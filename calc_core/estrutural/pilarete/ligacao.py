"""Ligação pilarete->sapata — emenda por traspasse (9.5.2.x) e junta (21.6).

Ref.: ABNT NBR 6118:2023, item 9.3.2.1 e Tabela 8.2, p. 33 e 29 (f_bd)
[rule: NBR6118-9.4.2.4-lb-basico]

Ref.: ABNT NBR 6118:2023, item 9.4.2.5, p. 38 (ell_b,nec e alpha_ancoragem)
[rule: NBR6118-9.4.2.5-lb-necessario]

Ref.: ABNT NBR 6118:2023, item 9.5.2 (1º parágrafo conforme Em1:2026) e
9.5.2.3, p. 44
[rule: NBR6118-9.5.2.3-traspasse-comprimidas]

Ref.: ABNT NBR 6118:2023, item 9.5.2.1, p. 42-43
[rule: NBR6118-9.5.2.1-emenda-100-por-cento-comprimida]

Ref.: ABNT NBR 6118:2023, itens 9.5.2.4.1 e 9.5.2.4.2, p. 44
[rule: NBR6118-9.5.2.4.2-armadura-transversal-na-emenda]

Ref.: ABNT NBR 6118:2023, item 21.6, p. 181
[rule: NBR6118-21.6-junta-de-concretagem-pilarete-sapata]

[req: REQ-PILARETE-10-emenda-por-traspasse-pilarete-sapata]
[req: REQ-PILARETE-11-junta-de-concretagem-tres-casos-e-duas-recusas]

DUAS GRANDEZAS QUE O CÓDIGO DO MOTOR AMPLO CONFUNDE, e a distinção é a
armadilha desta matéria:

* ``ell_0c`` — EMENDA POR TRASPASSE, acima do topo da sapata, com mínimo
  ``max(0,6·ell_b ; 15 phi ; 200 mm)`` (9.5.2.3);
* ``ell_b,nec`` de ANCORAGEM da espera DENTRO da sapata, com mínimo
  ``max(0,3·ell_b ; 10 phi ; 100 mm)`` (9.4.2.5).

``sapata_isolada/sapata.py::_ancoragem_pilar`` usa hoje
``max(0,6·ell_b ; 10 phi ; 100 mm)``, que é um HÍBRIDO dos dois mínimos e não
corresponde a nenhum dos itens — conservador na primeira parcela, mas sem
rastreabilidade. REQ-PILARETE-10 PROÍBE reusar aquela função, e este módulo
calcula ell_0c do seu próprio jeito, com o ``[rule: ]`` correto. A função de
lá NÃO é chamada nem corrigida aqui (é código do motor amplo, com aprovações
próprias); a pendência está registrada em kb/pendencias.md > V12.

A JUNTA É OUTRA COISA, AINDA: 21.6 trata da INTERFACE entre pilarete e
sapata; §17.4 trata do cortante AO LONGO DA ALTURA do pilarete. Verificar
§17.4 NÃO cobre a junta, e a recusa da junta aderente com H != 0 vale
integralmente mesmo num pilarete que passe folgado no cortante.
"""
from __future__ import annotations

from dataclasses import dataclass

from calc_core.estrutural.dominio import (
    DECLARADO_EM_TEXTO,
    NAO_DECLARADO_NA_FONTE,
    RecusaForaDeDominio,
    exigir_um_de,
    exigir_positivo,
)
from calc_core.sapata_isolada.materiais import (
    Aco,
    Concreto,
    eta2_aderencia,
    eta3_bitola,
)

__all__ = [
    "MONOLITICO",
    "JUNTA_COM_ADERENCIA_DECLARADA",
    "JUNTA_SEM_ADERENCIA_ASSEGURADA",
    "TIPOS_DE_JUNTA",
    "ALPHA_ANCORAGEM_BARRA_COMPRIMIDA",
    "PHI_MAXIMO_PARA_TRASPASSE_MM",
    "f_bd",
    "ell_b_basico",
    "ResultadoTraspasse",
    "comprimento_de_traspasse",
    "exigencias_de_armadura_transversal_da_emenda",
    "ResultadoJunta",
    "verificar_junta",
]

MONOLITICO = "MONOLITICO"
"""Pilarete concretado monoliticamente com a sapata — 21.6 não se aplica."""

JUNTA_COM_ADERENCIA_DECLARADA = "JUNTA_COM_ADERENCIA_DECLARADA"
"""Junta com aderência e rugosidade DECLARADAS pela execução (21.6)."""

JUNTA_SEM_ADERENCIA_ASSEGURADA = "JUNTA_SEM_ADERENCIA_ASSEGURADA"
"""Junta sem aderência assegurada — RECUSA, com ou sem H."""

TIPOS_DE_JUNTA: tuple[str, ...] = (
    MONOLITICO, JUNTA_COM_ADERENCIA_DECLARADA, JUNTA_SEM_ADERENCIA_ASSEGURADA,
)
"""Enumeração FECHADA, sem default (REQ-PILARETE-02-e)."""

ALPHA_ANCORAGEM_BARRA_COMPRIMIDA = 1.0
"""alpha de 9.4.2.5 para barra COMPRIMIDA [adimensional].

Ref.: ABNT NBR 6118:2023, item 9.4.2.5, p. 38
[rule: NBR6118-9.4.2.5-lb-necessario]

Barra comprimida não tem gancho e não tem barra transversal soldada, logo os
outros valores de alpha (0,7 com gancho, 0,7/0,5 com barra soldada) NÃO se
aplicam. Nome COMPLETO ``alpha_ancoragem``: é o quinto ``alpha`` do ruleset e
um símbolo chamado ``alpha`` nu é veto do a6 (REQ-PILARETE-01).
"""

PHI_MAXIMO_PARA_TRASPASSE_MM = 32.0
"""Acima de 32 mm a emenda por traspasse é PROIBIDA (9.5.2, 1º parágrafo)."""


def f_bd(*, concreto: Concreto, aco: Aco, phi_mm: float,
         boa_aderencia: bool) -> float:
    """Resistência de aderência de cálculo [MPa].

    Ref.: ABNT NBR 6118:2023, item 9.3.2.1 e Tabela 8.2, p. 33 e 29
    [rule: NBR6118-9.4.2.4-lb-basico]

        f_bd = eta_1·eta_2·eta_3·f_ctd,   f_ctd = f_ctk,inf/gamma_c

    ``eta_2`` é DECLARADO pelo usuário (1,0 boa aderência / 0,7 má,
    REQ-PILARETE-02-g) e NUNCA assumido bom: numa espera de pilarete
    concretada por cima, a situação de aderência é decisão de execução, não de
    software.

    ``eta_1`` sai da Tabela 8.2 por CATEGORIA do aço (``Aco.eta1``, já
    conferido no motor amplo): CA-25 = 1,00, CA-50 = 2,25, CA-60 = 1,00 —
    CA-60 É nervurado e ainda assim tem 1,00, o que um booleano "nervurada"
    erraria do lado inseguro.
    """
    exigir_positivo("phi_mm", phi_mm,
                    fonte="ABNT NBR 6118:2023, 9.3.2.1, p. 33",
                    apoio_no_ruleset="NBR6118-9.4.2.4-lb-basico")
    return (aco.eta1 * eta2_aderencia(boa_aderencia) * eta3_bitola(phi_mm)
            * concreto.fctd)


def ell_b_basico(*, concreto: Concreto, aco: Aco, phi_mm: float,
                 boa_aderencia: bool) -> float:
    """Comprimento de ancoragem básico ell_b [m], com o piso de 25 phi.

    Ref.: ABNT NBR 6118:2023, item 9.4.2.4, p. 37
    [rule: NBR6118-9.4.2.4-lb-basico]

        ell_b = (phi/4)·(f_yd/f_bd) >= 25·phi

    CONTRA-PROVA EXTERNA (tabela consagrada, NÃO fonte do acervo): para
    C25/CA-50 em boa aderência, sem gancho, esta expressão dá
    ell_b/phi = 37,7 contra o valor clássico de 38·phi. É o único ponto desta
    feature com conferência de terceiros, e por isso vira fixture de teste com
    a origem declarada.
    """
    aderencia = f_bd(concreto=concreto, aco=aco, phi_mm=phi_mm,
                     boa_aderencia=boa_aderencia)
    phi_m = phi_mm / 1000.0
    return max(phi_m / 4.0 * (aco.fyd / aderencia), 25.0 * phi_m)


@dataclass(frozen=True)
class ResultadoTraspasse:
    """ell_0c e as parcelas que o produziram, para o memorial.

    Ref.: ABNT NBR 6118:2023, itens 9.4.2.4, 9.4.2.5 e 9.5.2.3, p. 37, 38 e 44
    [rule: NBR6118-9.5.2.3-traspasse-comprimidas]
    """

    phi_mm: float
    f_bd_MPa: float
    ell_b: float
    """Ancoragem básica [m], já com o piso de 25 phi."""
    ell_b_nec: float
    """alpha_ancoragem·ell_b·(A_s,calc/A_s,ef) [m]."""
    ell_0c_minimo: float
    """max(0,6·ell_b ; 15·phi ; 200 mm) [m] — mínimo de EMENDA (9.5.2.3)."""
    ell_0c: float
    """Comprimento de traspasse adotado [m] = max(ell_b,nec ; ell_0c,mín)."""
    alpha_ancoragem: float
    boa_aderencia: bool
    fracao_emendada_na_mesma_secao: float
    declaracoes: tuple[str, ...]


DECLARACAO_ETA_2_DECLARADO = (
    "A situação de aderência (eta_2 = 1,0 boa / 0,7 má, NBR 6118:2023, "
    "9.3.2.1, p. 33) é DECLARADA pelo usuário e não inferida por este "
    "software: numa espera de pilarete concretada por cima ela é decisão de "
    "execução. O valor declarado vai ao memorial junto com o ell_b resultante."
)

DECLARACAO_100_POR_CENTO_EMENDADAS = (
    "A NBR 6118:2023, 9.5.2.1 (p. 43), autoriza emendar TODAS as barras na "
    "mesma seção \"quando se tratar de armadura permanentemente comprimida ou "
    "de distribuição\" — sem a Tabela 9.3 e sem alpha_0t, que valem só para "
    "barras TRACIONADAS. A autorização é uma HIPÓTESE SOBRE O ESFORÇO, não "
    "sobre o elemento: se qualquer combinação tracionar a armadura, ela cai, "
    "passam a valer 9.5.2.2 e a Tabela 9.4 — não implementadas — e este "
    "software RECUSA."
)


def comprimento_de_traspasse(
    *,
    concreto: Concreto,
    aco: Aco,
    phi_mm: float,
    boa_aderencia: bool,
    armadura_tracionada_em_alguma_combinacao: bool,
    A_s_calculada: float,
    A_s_efetiva: float,
    fracao_emendada_na_mesma_secao: float = 1.0,
) -> ResultadoTraspasse:
    """ell_0c da emenda pilarete->sapata. RECUSA phi > 32 mm e tração.

    Ref.: ABNT NBR 6118:2023, itens 9.5.2 (Em1:2026), 9.5.2.1, 9.5.2.3,
    9.4.2.4 e 9.4.2.5, p. 42-44 e 37-38
    [rule: NBR6118-9.5.2.3-traspasse-comprimidas]
    [rule: NBR6118-9.5.2.1-emenda-100-por-cento-comprimida]
    [rule: NBR6118-9.4.2.5-lb-necessario]
    [req: REQ-PILARETE-10-emenda-por-traspasse-pilarete-sapata]

        ell_0c = ell_b,nec >= max(0,6·ell_b ; 15·phi ; 200 mm)
        ell_b,nec = alpha_ancoragem·ell_b·(A_s,calc/A_s,ef),  alpha = 1,0

    DUAS RECUSAS, e nenhuma delas é conservadorismo gratuito:

    1. ``phi > 32 mm`` -> a emenda por traspasse é PROIBIDA pelo 1º parágrafo
       de 9.5.2 (redação da Emenda 1:2026, que acrescenta "na execução" e
       estende os cuidados a elementos lineares de seção inteiramente
       tracionada, sem mudar o limite de 32 mm). Não há rota alternativa neste
       software — a emenda por solda ou por luva não foi extraída.
    2. armadura TRACIONADA em alguma combinação -> cai a autorização de
       9.5.2.1 para emendar 100 % das barras na mesma seção; passariam a valer
       9.5.2.2 e a Tabela 9.4, que esta versão NÃO implementa. É PROIBIDO
       "assumir que é permanentemente comprimida porque é pilar": a hipótese é
       sobre o ESFORÇO e o software a VERIFICA.

    A relação ``A_s,calc/A_s,ef`` entra como a Norma escreve; com armadura
    efetiva igual à calculada ela vale 1,0 e ell_b,nec = ell_b.
    """
    exigir_positivo("A_s_efetiva", A_s_efetiva,
                    fonte="ABNT NBR 6118:2023, 9.4.2.5, p. 38",
                    apoio_no_ruleset="NBR6118-9.4.2.5-lb-necessario")
    exigir_positivo("A_s_calculada", A_s_calculada,
                    fonte="ABNT NBR 6118:2023, 9.4.2.5, p. 38",
                    apoio_no_ruleset="NBR6118-9.4.2.5-lb-necessario")
    if phi_mm > PHI_MAXIMO_PARA_TRASPASSE_MM:
        raise RecusaForaDeDominio(
            parametro="phi_mm",
            valor=phi_mm,
            intervalo=f"<= {PHI_MAXIMO_PARA_TRASPASSE_MM} mm",
            fonte="ABNT NBR 6118:2023/Em1:2026, 9.5.2, 1º parágrafo, p. 44 — "
                  "emenda por traspasse não é permitida para barras de bitola "
                  "superior a 32 mm",
            forca=DECLARADO_EM_TEXTO,
            apoio_no_ruleset="NBR6118-9.5.2.3-traspasse-comprimidas",
            sugestao=f"Bitola declarada {phi_mm:.1f} mm. As alternativas "
                     "(emenda por solda, por luva) não foram extraídas para "
                     "este software: verifique fora dele.",
        )
    if armadura_tracionada_em_alguma_combinacao:
        raise RecusaForaDeDominio(
            parametro="armadura_tracionada_em_alguma_combinacao",
            valor=True,
            intervalo="False — armadura PERMANENTEMENTE COMPRIMIDA",
            fonte="ABNT NBR 6118:2023, 9.5.2.1, p. 43 — a autorização para "
                  "emendar 100 % das barras na mesma seção vale 'quando se "
                  "tratar de armadura permanentemente comprimida ou de "
                  "distribuição'",
            forca=DECLARADO_EM_TEXTO,
            apoio_no_ruleset="NBR6118-9.5.2.1-emenda-100-por-cento-comprimida",
            sugestao="Com tração em alguma combinação passam a valer 9.5.2.2 e "
                     "a Tabela 9.4 (proporção máxima emendada e alpha_0t), que "
                     "esta versão NÃO implementa. O software RECUSA em vez de "
                     "aplicar a regra da barra comprimida a uma barra "
                     "tracionada.",
        )

    ell_b = ell_b_basico(concreto=concreto, aco=aco, phi_mm=phi_mm,
                         boa_aderencia=boa_aderencia)
    ell_b_nec = (ALPHA_ANCORAGEM_BARRA_COMPRIMIDA * ell_b
                 * (A_s_calculada / A_s_efetiva))
    minimo = max(0.6 * ell_b, 15.0 * phi_mm / 1000.0, 0.200)
    return ResultadoTraspasse(
        phi_mm=phi_mm,
        f_bd_MPa=f_bd(concreto=concreto, aco=aco, phi_mm=phi_mm,
                      boa_aderencia=boa_aderencia),
        ell_b=ell_b,
        ell_b_nec=ell_b_nec,
        ell_0c_minimo=minimo,
        ell_0c=max(ell_b_nec, minimo),
        alpha_ancoragem=ALPHA_ANCORAGEM_BARRA_COMPRIMIDA,
        boa_aderencia=boa_aderencia,
        fracao_emendada_na_mesma_secao=fracao_emendada_na_mesma_secao,
        declaracoes=(DECLARACAO_ETA_2_DECLARADO,
                     DECLARACAO_100_POR_CENTO_EMENDADAS),
    )


def exigencias_de_armadura_transversal_da_emenda(
    *, phi_mm: float, ell_0c: float,
) -> tuple[str, ...]:
    """O TEXTO de 9.5.2.4.1/9.5.2.4.2; NÃO dimensiona Soma A_st.

    Ref.: ABNT NBR 6118:2023, itens 9.5.2.4.1 e 9.5.2.4.2, p. 44
    [rule: NBR6118-9.5.2.4.2-armadura-transversal-na-emenda]
    [req: REQ-PILARETE-10-emenda-por-traspasse-pilarete-sapata]

    O QUE ESTA FUNÇÃO DELIBERADAMENTE NÃO FAZ: dimensionar a Soma A_st. Os
    valores correspondentes (Soma A_st/2 em cada terço, 1/3·ell_0,
    espaçamento <= 150 mm) existem SÓ NA FIGURA 9.5, foram transcritos da
    camada de texto da figura pelo a1 e NÃO foram conferidos por leitura
    vetorial. Enquanto não forem, o software impõe o TEXTO e REMETE o
    dimensionamento ao projetista, com aviso no memorial — inventar o número
    seria exatamente o que este projeto recusa.

    9.5.2.4.2 é REMISSIVO: manda manter os critérios do caso anterior
    (9.5.2.4.1, escrito para barras tracionadas) e ACRESCENTA o estribo a
    4 phi além de cada extremidade. É por isso que o item de barras
    tracionadas entra na cadeia de um pilarete comprimido.
    """
    exigir_positivo("ell_0c", ell_0c,
                    fonte="ABNT NBR 6118:2023, 9.5.2.4.2, p. 44",
                    apoio_no_ruleset="NBR6118-9.5.2.4.2-armadura-transversal-na-emenda")
    quatro_phi_mm = 4.0 * phi_mm
    dez_phi_mm = 10.0 * phi_mm
    return (
        f"NBR 6118:2023, 9.5.2.4.2 (p. 44): pelo menos UMA barra de armadura "
        f"transversal posicionada {quatro_phi_mm:.0f} mm (4·phi) ALÉM de cada "
        f"extremidade da emenda, que tem {ell_0c * 1000.0:.0f} mm.",
        "NBR 6118:2023, 9.5.2.4.1 (p. 44): a armadura transversal da emenda "
        "deve ser capaz de resistir à força de UMA barra emendada, e os "
        "estribos devem ser CONCENTRADOS nos terços extremos da emenda.",
        f"NBR 6118:2023, 9.5.2.4.1 (p. 44): estribos FECHADOS quando a "
        f"distância entre as duas barras mais próximas de duas emendas for "
        f"menor que {dez_phi_mm:.0f} mm (10·phi) — no pilarete o estribo já é "
        "fechado por 18.4.3, e o critério fica atendido por construção.",
        "AVISO: a Soma A_st da armadura transversal da emenda NÃO é "
        "dimensionada por este software. Os valores correspondentes existem "
        "apenas na Figura 9.5 da NBR 6118:2023 e não foram conferidos por "
        "leitura vetorial nesta rodada. O dimensionamento é remetido ao "
        "projetista.",
    )


@dataclass(frozen=True)
class ResultadoJunta:
    """Tipo de junta declarado, H e o que o memorial tem de dizer.

    Ref.: ABNT NBR 6118:2023, item 21.6, p. 181
    [rule: NBR6118-21.6-junta-de-concretagem-pilarete-sapata]
    [req: REQ-PILARETE-11-junta-de-concretagem-tres-casos-e-duas-recusas]
    """

    tipo_de_junta: str
    H_x: float
    H_y: float
    H_resultante_declarada_nao_nula: bool
    declaracoes: tuple[str, ...]


EXIGENCIA_1O_PARAGRAFO_21_6 = (
    "NBR 6118:2023, 21.6, 1º parágrafo (p. 181): o projeto de execução deve "
    "indicar de forma precisa o LOCAL e a CONFIGURAÇÃO da superfície da junta "
    "de concretagem. Esta exigência é do PROJETO DE EXECUÇÃO e não é suprida "
    "por nenhum cálculo deste software."
)

DECLARACAO_JUNTA_ADERENTE = (
    "A aderência e a rugosidade da junta entre pilarete e sapata foram "
    "DECLARADAS ASSEGURADAS pela especificação de execução "
    "(DECLARADO_PELO_USUARIO). Nesse caso a NBR 6118:2023, 21.6 (p. 181), não "
    "exige armadura de costura além da espera já dimensionada por 9.5.2.3, e "
    "é a espera que atravessa a junta."
)


def verificar_junta(*, tipo_de_junta: str | None, H_x: float,
                    H_y: float) -> ResultadoJunta:
    """TRÊS casos, DUAS recusas. O gatilho é ``H != 0`` EXATO, sem tolerância.

    Ref.: ABNT NBR 6118:2023, item 21.6, p. 181
    [rule: NBR6118-21.6-junta-de-concretagem-pilarete-sapata]
    [req: REQ-PILARETE-11-junta-de-concretagem-tres-casos-e-duas-recusas]

    * ``MONOLITICO`` -> segue. Não há junta e 21.6 não se aplica. (Com H != 0
      continuam valendo a rotulagem por FAIXA de 14.4.1 e, na FAIXA A, o ELU
      de força cortante de §17.4 — que é o cortante AO LONGO DA ALTURA, coisa
      DIFERENTE da transferência NA INTERFACE de que trata 21.6.)
    * ``JUNTA_COM_ADERENCIA_DECLARADA`` com ``H == 0`` -> segue, com a
      declaração LITERAL no memorial e a exigência do 1º parágrafo de 21.6.
    * ``JUNTA_COM_ADERENCIA_DECLARADA`` com ``H != 0`` -> **RECUSA**.
    * ``JUNTA_SEM_ADERENCIA_ASSEGURADA`` -> **RECUSA**, com ou sem H.

    DECISÃO HUMANA REGISTRADA (2026-09-03): recusar, e não avisar. A v11
    previa AVISO OBRIGATÓRIO; o usuário decidiu pela recusa, com a razão
    escrita — "mais restritivo, mais seguro", a mesma doutrina de recusar em
    vez de aproximar quando não há fonte no acervo.

    SEM TOLERÂNCIA NUMÉRICA, e a proibição é explícita: o gatilho é H
    DECLARADO diferente de zero. É PROIBIDO criar faixa de "H pequeno", "H
    desprezível" ou fração de N — não há base normativa para o limiar e
    inventá-lo seria exatamente o que a decisão do usuário recusou.
    H = 0,001 kN RECUSA; H = 0,0 segue.

    É PROIBIDO oferecer "prosseguir mesmo assim", caixa de confirmação, aviso
    no memorial em lugar da recusa, ou qualquer cálculo por Eurocódigo, ACI ou
    analogia com cisalhamento-atrito.
    """
    exigir_um_de("tipo_de_junta", tipo_de_junta, TIPOS_DE_JUNTA,
                 fonte="ABNT NBR 6118:2023, 21.6, p. 181",
                 apoio_no_ruleset="NBR6118-21.6-junta-de-concretagem-pilarete-sapata",
                 sugestao="Enumeração fechada e sem default: declare "
                          "MONOLITICO, JUNTA_COM_ADERENCIA_DECLARADA ou "
                          "JUNTA_SEM_ADERENCIA_ASSEGURADA.")
    H_nao_nulo = (H_x != 0.0) or (H_y != 0.0)

    if tipo_de_junta == JUNTA_SEM_ADERENCIA_ASSEGURADA:
        raise RecusaForaDeDominio(
            parametro="tipo_de_junta",
            valor=tipo_de_junta,
            intervalo="MONOLITICO ou JUNTA_COM_ADERENCIA_DECLARADA (esta "
                      "última só com H = 0)",
            fonte="ABNT NBR 6118:2023, 21.6, p. 181 — a junta exige armadura "
                  "de costura e a Norma NÃO fornece modelo de cisalhamento na "
                  "interface (sem coeficiente de atrito, sem coesão, sem "
                  "rugosidade em milímetros, sem taxa mínima)",
            forca=NAO_DECLARADO_NA_FONTE,
            apoio_no_ruleset="NBR6118-21.6-junta-de-concretagem-pilarete-sapata",
            sugestao="A ABNT NBR 9062, que forneceria o modelo de "
                     "cisalhamento-atrito, NÃO ESTÁ NO ACERVO deste software. "
                     "A alternativa é executar a ligação MONOLITICA.",
        )

    if tipo_de_junta == JUNTA_COM_ADERENCIA_DECLARADA and H_nao_nulo:
        raise RecusaForaDeDominio(
            parametro="(tipo_de_junta, H_x, H_y)",
            valor=(tipo_de_junta, H_x, H_y),
            intervalo="H_x = H_y = 0,0 exatamente, quando a junta é declarada "
                      "aderente",
            fonte="ABNT NBR 6118:2023, 21.6, p. 181 — a Norma trata a junta "
                  "APENAS por armadura de costura e NÃO fornece nenhum modelo "
                  "de transferência de CORTANTE na interface: sem coeficiente "
                  "de atrito, sem coesão, sem rugosidade em milímetros, sem "
                  "taxa mínima",
            forca=NAO_DECLARADO_NA_FONTE,
            apoio_no_ruleset="NBR6118-21.6-junta-de-concretagem-pilarete-sapata",
            sugestao=(f"(i) Força horizontal declarada: H_x = {H_x} kN, "
                      f"H_y = {H_y} kN. (ii) A junta foi DECLARADA ADERENTE. "
                      "(iii) A NBR 6118:2023, 21.6 (p. 181), não fornece "
                      "modelo de transferência de cortante na interface. "
                      "(iv) A ABNT NBR 9062, que forneceria o modelo de "
                      "cisalhamento-atrito, NÃO ESTÁ NO ACERVO. (v) A "
                      "alternativa é executar a ligação MONOLITICA. NÃO há "
                      "opção de prosseguir mesmo assim, e o gatilho é H != 0 "
                      "exato — não existe faixa de 'H desprezível'. ATENÇÃO: "
                      "verificar §17.4 (cortante ao longo da altura) NÃO cobre "
                      "a junta, que é a interface."),
        )

    declaracoes: tuple[str, ...]
    if tipo_de_junta == MONOLITICO:
        declaracoes = (
            "Ligação pilarete-sapata declarada MONOLÍTICA: não há junta de "
            "concretagem e a NBR 6118:2023, 21.6 (p. 181), não se aplica. A "
            "espera continua sendo dimensionada por 9.5.2.3 (emenda por "
            "traspasse).",
        )
    else:
        declaracoes = (DECLARACAO_JUNTA_ADERENTE, EXIGENCIA_1O_PARAGRAFO_21_6)

    return ResultadoJunta(
        tipo_de_junta=str(tipo_de_junta),
        H_x=H_x,
        H_y=H_y,
        H_resultante_declarada_nao_nula=H_nao_nulo,
        declaracoes=declaracoes,
    )
