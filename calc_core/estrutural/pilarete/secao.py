"""ELU de solicitações NORMAIS — equilíbrio de seção, envoltórias e veredito.

Ref.: ABNT NBR 6118:2023, item 17.2.1, p. 120
[rule: NBR6118-17.2.1-envoltoria-criterio-de-seguranca]

Ref.: ABNT NBR 6118:2023, item 17.2.2, alínea g) e Figura 17.1, p. 122
[rule: NBR6118-17.2.2-fig17.1-limites-dos-dominios]

Ref.: ABNT NBR 6118:2023, item 17.2.5, p. 125
[rule: NBR6118-17.2.5-flexao-composta-obliqua]

Ref.: ABNT NBR 6118:2023, item 11.3.3.4.3 e Figura 11.3, p. 61
[rule: NBR6118-11.3.3.4.3-fig11.3-envoltoria-minima-1a-ordem]

Ref.: ABNT NBR 6118:2023, item 17.2.4.1 (com Em1:2026), p. 123
[rule: NBR6118-17.2.4.1-concentracao-de-armaduras]  (citado para dizer que NÃO é usado)

[deriv: DER-NBR6118-NRd0-compressao-centrada]
[deriv: DER-NBR6118-17.2.2-MRd-varredura]
[deriv: DER-NBR6118-17.2.5-criterio-menor-ou-igual-a-1]
[deriv: DER-NBR6118-11.3.3.4.3-inclusao-de-envoltorias]
[req: REQ-PILARETE-06-NRd0-e-a-recusa-de-veredito-de-ELU]
[req: REQ-PILARETE-15-veredito-de-ELU-de-solicitacoes-normais]

DUAS EXPRESSÕES DE INTERAÇÃO, EXPOENTES DIFERENTES, LADOS OPOSTOS — é o erro
provável desta feature e por isso está no alto do módulo:

* **Figura 11.3** (11.3.3.4.3), expoente **2**, lado **SOLICITANTE**: a
  envoltória MÍNIMA de 1ª ordem, uma elipse de semieixos M_1d,mín,xx e
  M_1d,mín,yy.
* **17.2.5**, expoente **alpha_interacao**, lado **RESISTENTE**: a superfície
  da envoltória resistente para N_Rd = N_Sd fixado.

Trocá-las inverte a verificação. Um terceiro expoente ronda a MESMA página
125: o ``alpha = 1,5`` de 17.3.1 (fator de forma de M_r), que é ELS e é
PROIBIDO introduzir aqui (``alpha_fissuracao`` não existe neste pacote).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from calc_core.estrutural.dominio import (
    DECLARADO_EM_TEXTO,
    ESCOPO_DESTA_VERSAO,
    RecusaForaDeDominio,
    exigir_positivo,
)
from calc_core.estrutural.materiais_6118 import (
    EPS_S_MAXIMO,
    eps_c2,
    eps_cu,
    eta_c,
    exigir_classe_normalizada,
    n_diagrama,
    sigma_c,
    sigma_s,
)
from calc_core.sapata_isolada.materiais import Aco, Concreto

__all__ = [
    "ALPHA_INTERACAO_VEREDITO",
    "ALPHA_INTERACAO_INFORMATIVO",
    "TOLERANCIA_RELATIVA_DE_N",
    "MAX_ITERACOES_BISSECAO",
    "BarraLongitudinal",
    "SecaoRetangular",
    "PerfilDeDeformacao",
    "perfil_de_deformacao",
    "esforcos_resistentes_em_x",
    "N_Rd0",
    "ResultadoMRd",
    "momento_resistente_normal",
    "momento_resistente_por_faixas",
    "envoltoria_minima_1a_ordem",
    "interacao_flexao_obliqua",
    "indice_de_inclusao_da_envoltoria_minima",
    "indice_do_canto",
    "ResultadoELUNormal",
    "verificar_elu_solicitacoes_normais",
]

ALPHA_INTERACAO_VEREDITO = 1.0
"""Expoente de 17.2.5 usado no VEREDITO [adimensional].

Ref.: ABNT NBR 6118:2023, item 17.2.5, p. 125
[rule: NBR6118-17.2.5-flexao-composta-obliqua]

1,0 é o valor que a própria Norma declara "a favor da segurança", é o
autorizado "em geral" (sem condição de forma de seção) e é o ÚNICO para o
qual o teste de inclusão da envoltória mínima tem forma fechada EXATA — o que
elimina erro de discretização numa verificação que não tem nenhum caso de
conferência de terceiros no acervo.

NOME COMPLETO OBRIGATÓRIO ``alpha_interacao``: são CINCO ``alpha`` no ruleset
(interacao, fissuracao, c, b, ancoragem) e dois deles declaram valor "para
seção retangular" na MESMA página 125. Um ``alpha = 1.5`` escrito de memória
no lugar da interação passa por toda a checagem dimensional e produz
envoltória mais cheia — erro do lado INSEGURO.
"""

ALPHA_INTERACAO_INFORMATIVO = 1.2
"""Expoente que 17.2.5 autoriza para seção retangular — INFORMATIVO, só.

Ref.: ABNT NBR 6118:2023, item 17.2.5, p. 125
[rule: NBR6118-17.2.5-flexao-composta-obliqua]
[req: REQ-PILARETE-12-memorial-e-o-que-ele-e-obrigado-a-dizer]  (k)

É CALCULADO e EXIBIDO, rotulado "margem adicional autorizada por 17.2.5 para
seção retangular — informativo, não usado no veredito", e é PROIBIDO que
decida o veredito nesta versão. Não é que a Norma proíba: ela autoriza
expressamente. É que alpha maior = envoltória mais cheia = critério MENOS
conservador, e quem decide gastar essa margem num modelo sem validação
externa é o engenheiro, não o agente (kb/pendencias.md > V18).
"""

TOLERANCIA_RELATIVA_DE_N = 1.0e-10
"""Critério de convergência da busca da linha neutra [adimensional].

Ref.: ABNT NBR 6118:2023, item 17.2.2, p. 120-122
[deriv: DER-NBR6118-17.2.2-MRd-varredura]

CRITÉRIO DE CONVERGÊNCIA DECLARADO, exigido pelo ``limite_declarado`` da
derivação ("um número fixo de faixas escolhido a esmo é defeito"). Esta
implementação vai além do que a derivação pede: a INTEGRAÇÃO do diagrama
parábola-retângulo sobre a área comprimida é feita em FORMA FECHADA (ver
:func:`esforcos_resistentes_em_x`), com erro de discretização IDENTICAMENTE
NULO, de modo que não há "número de faixas" a escolher. Sobra um único passo
numérico — a solução de N_Rd(x) = N_Sd —, resolvido por BISSEÇÃO monótona com
esta tolerância relativa sobre N e no máximo
:data:`MAX_ITERACOES_BISSECAO` iterações.

A âncora de aceitação continua sendo a mesma que a derivação manda usar: a
varredura tem de reproduzir N_Rd0 na reta b (x -> infinito), e o teste que
compara os dois caminhos — um numérico, um algébrico — é obrigatório no
GATE 3. :func:`momento_resistente_por_faixas` fica disponível como SEGUNDA
implementação, por faixas com refinamento, exclusivamente para essa
conferência cruzada.
"""

MAX_ITERACOES_BISSECAO = 400
"""Teto de iterações da bisseção. Estourá-lo é RECUSA, nunca 'melhor esforço'."""

_ROTULOS_DE_DOMINIO = {
    2: "domínio 2 (polo A, 10 ‰ na armadura mais tracionada)",
    3: "domínio 3 (polo B, eps_cu na borda comprimida, armadura escoada)",
    4: "domínio 4 (polo B, eps_cu na borda comprimida, armadura NÃO escoada)",
    "4a": "domínio 4a (polo B, linha neutra na região das armaduras)",
    5: "domínio 5 (polo C, seção inteiramente comprimida)",
}


@dataclass(frozen=True)
class BarraLongitudinal:
    """Uma barra longitudinal, com posição nos DOIS eixos da seção.

    Ref.: ABNT NBR 6118:2023, item 17.2.2, alínea b), p. 120
    [rule: NBR6118-17.2.2-fig17.1-limites-dos-dominios]

    ``pos_h`` e ``pos_b`` são medidas [m] a partir de UMA borda de referência,
    ao longo de ``h_secao`` e de ``b_secao`` respectivamente. A convenção é
    fixa: para a flexão no plano de h (índice ``xx``) a coordenada que importa
    é ``pos_h``; para a flexão no plano de b (índice ``yy``), ``pos_b``.

    A varredura soma barra a barra (camada a camada), com a deformação do
    PRÓPRIO nível de cada camada (17.2.2-b). A permissão de 17.2.4.1 de
    concentrar as forças no centroide NÃO é usada: ela é CONDICIONADA a que a
    distância do centroide à armadura mais afastada seja menor que 10 % de h,
    e num pilarete 30×30 com barras nos vértices e d' = 5,8 cm essa distância
    é ~9,2 cm contra o limite de 3,0 cm. Agrupar seria ILEGÍTIMO ali, e do
    lado INSEGURO.
    """

    pos_h: float
    """Posição ao longo de h_secao, de 0 a h_secao [m]."""

    pos_b: float
    """Posição ao longo de b_secao, de 0 a b_secao [m]."""

    area: float
    """Área da seção transversal da barra [m²]."""


@dataclass(frozen=True)
class SecaoRetangular:
    """Seção retangular do pilarete com armadura passiva discreta.

    Ref.: ABNT NBR 6118:2023, item 17.2.2, p. 120-122
    [rule: NBR6118-17.2.2-fig17.1-limites-dos-dominios]

    Só seção RETANGULAR, e a restrição não é de conveniência: o critério
    elíptico da Figura 11.3 e o alpha_interacao = 1,2 de 17.2.5 são AMBOS
    declarados só para seção retangular — sem essa guarda, os dois caem.
    """

    h_secao: float
    """Altura da seção [m]. NÃO é a altura da sapata (22.6.1)."""

    b_secao: float
    """Menor dimensão da seção [m]. NÃO é a largura da sapata (geotécnico)."""

    barras: tuple[BarraLongitudinal, ...]
    concreto: Concreto
    aco: Aco

    @property
    def A_c(self) -> float:
        """Área bruta de concreto [m²].

        Ref.: ABNT NBR 6118:2023, item 17.2.2, p. 120
        [rule: NBR6118-17.2.2-fig17.1-limites-dos-dominios]
        """
        return self.h_secao * self.b_secao

    @property
    def A_s_total(self) -> float:
        """Área total de armadura longitudinal [m²].

        Ref.: ABNT NBR 6118:2023, item 17.3.5.3, p. 133
        [rule: NBR6118-17.3.5.3-armaduras-limite-pilarete]
        """
        return sum(barra.area for barra in self.barras)

    def arranjo_simetrico(self, tolerancia: float = 1e-9) -> bool:
        """True se o arranjo de barras for simétrico nos DOIS eixos.

        Ref.: ABNT NBR 6118:2023, item 17.2.5, p. 125
        [deriv: DER-NBR6118-17.2.5-criterio-menor-ou-igual-a-1]  (PASSO 4)
        [req: REQ-PILARETE-15-veredito-de-ELU-de-solicitacoes-normais]  (8)

        A redução aos valores ABSOLUTOS dos momentos solicitantes pressupõe
        envoltória simétrica nos quatro quadrantes, o que por sua vez
        pressupõe arranjo de armadura simétrico nos dois eixos. É PROIBIDO
        ASSUMIR a simetria: o código VERIFICA, e quem não passa é RECUSADO
        (ver :func:`verificar_elu_solicitacoes_normais`).
        """
        pontos = {(round(barra.pos_h, 9), round(barra.pos_b, 9), round(barra.area, 12))
                  for barra in self.barras}
        espelho_h = {(round(self.h_secao - ph, 9), pb, a) for ph, pb, a in pontos}
        espelho_b = {(ph, round(self.b_secao - pb, 9), a) for ph, pb, a in pontos}
        del tolerancia  # arredondamento a 1 nm já é a tolerância efetiva
        return pontos == espelho_h and pontos == espelho_b


@dataclass(frozen=True)
class PerfilDeDeformacao:
    """Perfil linear de deformações de um ELU, pivotando num polo da Figura 17.1.

    Ref.: ABNT NBR 6118:2023, item 17.2.2, alínea g) e Figura 17.1, p. 122
    [rule: NBR6118-17.2.2-fig17.1-limites-dos-dominios]

    eps(y) = eps_c2·(1 + (y_p − y)/D), com y medido a partir da BORDA
    COMPRIMIDA, compressão POSITIVA. ``y_p`` é a cota em que eps = eps_c2
    (início do patamar) e ``D`` é a distância de ``y_p`` à linha neutra, de
    modo que eps(y_p) = eps_c2 e eps(y_p + D) = 0.

    Esta parametrização por (y_p, D) — e não por (x, k) — é DELIBERADA e é uma
    decisão de estabilidade numérica, não de estilo: no polo C, com x -> oo
    (reta b), tanto x quanto k = eps_c2/(x − y_C) degeneram, e a expressão
    ingênua eps = k·(x − y) perde todos os dígitos por cancelamento. Em (y_p,
    D), y_p é CONSTANTE e igual a y_C nesse ramo, e as integrais fechadas
    ficam estáveis até x/h = 1e12 — que é o que permite reproduzir N_Rd0 na
    reta b com diferença nula, verificação cruzada exigida por
    REQ-PILARETE-06-C(ii).
    """

    x: float
    """Profundidade da linha neutra, medida da borda comprimida [m]."""

    y_p: float
    """Cota em que eps = eps_c2 [m]. Pode ser negativa (sem patamar)."""

    D: float
    """Distância de y_p à linha neutra [m]; eps = eps_c2·(1 + (y_p − y)/D)."""

    eps_borda_comprimida: float
    """eps(0) [adimensional]."""

    polo: str
    """``"A"``, ``"B"`` ou ``"C"`` da Figura 17.1."""

    eps_c2_da_classe: float
    """eps_c2 de 8.2.10.1 para a classe do concreto [adimensional]."""

    def deformacao_em(self, y: float) -> float:
        """Deformação na cota ``y`` [adimensional], compressão positiva.

        Ref.: ABNT NBR 6118:2023, item 17.2.2, alínea a), p. 120
        [rule: NBR6118-17.2.2-fig17.1-limites-dos-dominios]

        Seções planas (alínea a): eps é LINEAR em y. Escrita em (y_p, D) e não
        em (x, k) pelo motivo de estabilidade explicado na classe.
        """
        return self.eps_c2_da_classe * (1.0 + (self.y_p - y) / self.D)


def perfil_de_deformacao(x: float, *, altura: float, d_max: float,
                         f_ck_MPa: float) -> PerfilDeDeformacao:
    """Perfil de deformação do ELU para a linha neutra em ``x``.

    Ref.: ABNT NBR 6118:2023, item 17.2.2, alínea a) e g), Figura 17.1, p. 122
    [rule: NBR6118-17.2.2-fig17.1-limites-dos-dominios]
    [deriv: DER-NBR6118-17.2.2-MRd-varredura]  (PASSO 1)

    Os TRÊS POLOS, lidos da FIGURA (não do texto — a Norma desenha os domínios
    e não escreve nenhuma equação de eps(y); a leitura de que eps é linear com
    pivô no polo do domínio é a alínea a), seções planas, aplicada ao desenho):

    * **polo A** — 10 ‰ de alongamento na armadura mais tracionada, em
      ``d_max``. Vale enquanto ``x < x_lim = eps_cu·d_max/(eps_cu + 10 ‰)``.
    * **polo B** — ``eps_cu`` na borda comprimida. Vale de ``x_lim`` a
      ``altura``.
    * **polo C** — ``eps_c2`` na cota
      ``y_C = (eps_cu − eps_c2)·altura/eps_cu``, MEDIDA DO NÍVEL DA BORDA
      COMPRIMIDA. Vale acima de ``altura``, e no limite x -> oo dá a RETA b
      (compressão uniforme em eps_c2), que é o caso-limite de N_Rd0.

    ``y_C`` é calculado pela EXPRESSÃO, nunca como 3h/7: o atalho 3h/7 vale só
    até C50, porque eps_c2 e eps_cu dependem da classe por 8.2.10.1.

    LIMITE DECLARADO da checagem dimensional, e é o motivo de os três ramos
    serem escritos separados: como eps_cu e eps_c2 são adimensionais, trocar
    um pelo outro, trocar o sinal da diferença ou medir y_C da borda
    TRACIONADA em vez da COMPRIMIDA passa incólume pelo pint.
    """
    exigir_classe_normalizada(f_ck_MPa)
    exigir_positivo("x", x,
                    fonte="ABNT NBR 6118:2023, 17.2.2-g), Figura 17.1, p. 122",
                    apoio_no_ruleset="NBR6118-17.2.2-fig17.1-limites-dos-dominios")
    e_c2 = eps_c2(f_ck_MPa)
    e_cu = eps_cu(f_ck_MPa)
    x_lim_polo_A = e_cu * d_max / (e_cu + EPS_S_MAXIMO)

    if x < x_lim_polo_A:
        polo = "A"
        eps_topo = EPS_S_MAXIMO * x / (d_max - x)
        D = e_c2 * x / eps_topo
        y_p = x * (1.0 - e_c2 / eps_topo)
    elif x <= altura:
        polo = "B"
        eps_topo = e_cu
        D = e_c2 * x / eps_topo
        y_p = x * (1.0 - e_c2 / eps_topo)
    else:
        polo = "C"
        y_C = (e_cu - e_c2) * altura / e_cu
        D = x - y_C
        y_p = y_C
        eps_topo = e_c2 * (1.0 + y_p / D)

    return PerfilDeDeformacao(
        x=x, y_p=y_p, D=D, eps_borda_comprimida=eps_topo, polo=polo,
        eps_c2_da_classe=e_c2,
    )


def _G(u: float, n: float) -> float:
    """Primitiva de (1 − u^n): G(u) = u − u^(n+1)/(n+1)."""
    return u - u ** (n + 1.0) / (n + 1.0)


def _H(u: float, n: float) -> float:
    """Primitiva de u·(1 − u^n): H(u) = u²/2 − u^(n+2)/(n+2)."""
    return u * u / 2.0 - u ** (n + 2.0) / (n + 2.0)


def esforcos_resistentes_em_x(
    x: float, *, altura: float, largura: float,
    camadas: tuple[tuple[float, float], ...],
    concreto: Concreto, aco: Aco,
) -> tuple[float, float, PerfilDeDeformacao]:
    """(N_Rd, M_Rd, perfil) para uma linha neutra em ``x``. Integração EXATA.

    Ref.: ABNT NBR 6118:2023, itens 17.2.2 (alíneas a, b, d, g) e 8.2.10.1,
    p. 120-122 e 26
    [rule: NBR6118-17.2.2-fig17.1-limites-dos-dominios]
    [rule: NBR6118-8.2.10.1-diagrama-idealizado-do-concreto]
    [deriv: DER-NBR6118-17.2.2-MRd-varredura]
    [deriv: DER-NBR6118-8.3.6-sigma-s-ate-10-por-mil]

        N_Rd(x) = ∫_Ac sigma_c(eps(y)) dA + Σ_i A_si·sigma_s(eps(y_i))
        M_Rd(x) = ∫_Ac sigma_c(eps(y))·(h/2 − y) dA
                  + Σ_i A_si·sigma_s(eps(y_i))·(h/2 − y_i)

    ``camadas`` é uma tupla ``(y_i, A_si)`` com ``y_i`` medido da borda
    comprimida [m] e ``A_si`` em [m²]. Momentos tomados no CENTROIDE da seção
    BRUTA, e o polo TEM de ser o mesmo usado para M_Sd — polo diferente é erro
    silencioso (PASSO 4 da derivação).

    Tração do concreto DESPREZADA (17.2.2-d): a integral vai de y = 0 a
    y = min(x, h).

    A INTEGRAÇÃO É FECHADA, e vale a pena escrever por quê. Com
    eps(y) = eps_c2·(1 + (y_p − y)/D) e a substituição u = 1 − eps/eps_c2
    (u = 0 no início do patamar, u = 1 na linha neutra), o diagrama de
    8.2.10.1 vira ``sigma = P·(1 − u^n)`` e as duas integrais têm primitiva
    elementar mesmo com ``n`` não inteiro (n = 1,4 em C90):

        ∫ sigma dy       = P·D·[G(u)],            G(u) = u − u^(n+1)/(n+1)
        ∫ sigma(h/2−y)dy = P·D·[C·G(u) − D·H(u)], H(u) = u²/2 − u^(n+2)/(n+2)

    com ``C = h/2 − y_p`` e ``P = 0,85·eta_c·f_cd``. Erro de discretização
    IDENTICAMENTE NULO — não há faixas, não há máximo perdido entre dois
    pontos amostrados, e o patamar de eps_c2 a eps_cu entra como o retângulo
    ``P·y_patamar`` em vez de ser reamostrado (a armadilha de 8.2.10.1: a
    expressão da parábola, avaliada acima de eps_c2, DECRESCE).

    É PROIBIDO misturar esta parábola-retângulo com o bloco retangular
    simplificado de 17.2.2-e no mesmo cálculo. Os dois são autorizados; o
    exato dispensa a discussão sobre lambda_x e alpha_c.
    """
    f_ck_MPa = concreto.fck
    d_max = max(y for y, _ in camadas)
    perfil = perfil_de_deformacao(x, altura=altura, d_max=d_max,
                                  f_ck_MPa=f_ck_MPa)
    n = n_diagrama(f_ck_MPa)
    # P em kN/m²: f_cd vem em MPa = MN/m².
    P = 0.85 * eta_c(f_ck_MPa) * concreto.fcd * 1000.0

    y_c = min(x, altura)                      # fim da zona comprimida
    y_patamar = min(max(perfil.y_p, 0.0), y_c)  # trecho em tensão constante
    y_inicio_parabola = y_patamar
    # u = 1 − eps/eps_c2, logo u = 0 no fim do patamar e u = 1 na linha
    # neutra. Os dois limites estão em [0, 1] POR CONSTRUÇÃO (ver a dedução
    # na docstring); o clip é higiene de ponto flutuante contra um 1 + 1e-16
    # que estouraria u**(n+1) com n não inteiro, não uma correção de domínio.
    u_a = min(1.0, max(0.0, (y_inicio_parabola - perfil.y_p) / perfil.D))
    u_b = min(1.0, max(0.0, (y_c - perfil.y_p) / perfil.D))
    C = altura / 2.0 - perfil.y_p

    N_concreto = largura * (
        P * y_patamar + P * perfil.D * (_G(u_b, n) - _G(u_a, n))
    )
    M_concreto = largura * (
        P * (altura / 2.0 * y_patamar - y_patamar ** 2 / 2.0)
        + P * perfil.D * (
            C * (_G(u_b, n) - _G(u_a, n)) - perfil.D * (_H(u_b, n) - _H(u_a, n))
        )
    )

    N_aco = 0.0
    M_aco = 0.0
    for y_i, A_si in camadas:
        eps_i = perfil.deformacao_em(y_i)
        # sigma_s RECUSA acima de 10 ‰ — a guarda está lá, não aqui.
        tensao = sigma_s(eps_i, aco) * 1000.0   # MPa -> kN/m²
        N_aco += A_si * tensao
        M_aco += A_si * tensao * (altura / 2.0 - y_i)

    return N_concreto + N_aco, M_concreto + M_aco, perfil


def N_Rd0(secao: SecaoRetangular) -> float:
    """Força normal resistente de compressão centrada [kN] — INFORMATIVA.

    Ref.: ABNT NBR 6118:2023, itens 17.2.1, 17.2.2-g), 8.2.10.1, 8.3.5/8.3.6
    e 12.3.1, p. 120-122, 26, 29-30 e 70
    [rule: NBR6118-17.2.2-fig17.1-limites-dos-dominios]
    [rule: NBR6118-8.2.10.1-diagrama-idealizado-do-concreto]
    [rule: NBR6118-8.3.5-8.3.6-aco-passivo]
    [deriv: DER-NBR6118-NRd0-compressao-centrada]
    [req: REQ-PILARETE-06-NRd0-e-a-recusa-de-veredito-de-ELU]

        N_Rd0 = 0,85·eta_c·f_cd·A_c + A_s·sigma_s(eps_c2)

    O PASSO MAIS FORTE da derivação está no primeiro termo: identificar a
    "reta b" da Figura 17.1 (compressão uniforme) com a deformação uniforme
    eps = eps_c2. A Norma NOMEIA a reta b na figura e NÃO lhe atribui
    deformação. Avaliando o diagrama em eps_c2 o colchete [1 − (1−1)^n] vale
    1, e sobra 0,85·eta_c·f_cd.

    É PROIBIDO QUALQUER CAMINHO DE CÓDIGO EM QUE ``N_d <= N_Rd0`` PRODUZA
    "APROVADO", cor verde ou ausência de aviso. A condição é NECESSÁRIA e NÃO
    SUFICIENTE: por 11.3.3.4.3 existe M_1d,mín nas duas direções, logo o
    estado real é de FLEXO-COMPRESSÃO OBLÍQUA e o critério aplicável é a
    envoltória de 17.2.1 (:func:`verificar_elu_solicitacoes_normais`). O
    caminho inverso é legítimo: ``N_d > N_Rd0`` é condição SUFICIENTE para
    REPROVAR, e é usada como guarda de entrada da varredura.

    Usos autorizados, e só estes três: (i) valor informativo; (ii) denominador
    de nu = N_d/N_Rd0 no relatório; (iii) guarda de recusa e verificação
    cruzada da varredura na reta b.
    """
    f_ck_MPa = secao.concreto.fck
    pico_kN_m2 = 0.85 * eta_c(f_ck_MPa) * secao.concreto.fcd * 1000.0
    tensao_aco_kN_m2 = sigma_s(eps_c2(f_ck_MPa), secao.aco) * 1000.0
    return pico_kN_m2 * secao.A_c + secao.A_s_total * tensao_aco_kN_m2


def _camadas(secao: SecaoRetangular, plano: str) -> tuple[tuple[float, float], ...]:
    """Camadas (y_i, A_si) da armadura no plano de flexão pedido.

    Ref.: ABNT NBR 6118:2023, item 17.2.2, alínea b), p. 120
    [rule: NBR6118-17.2.2-fig17.1-limites-dos-dominios]

    ``plano`` = ``"xx"`` (flexão no plano de h; y = pos_h) ou ``"yy"`` (flexão
    no plano de b; y = pos_b). Barras com a mesma cota são somadas — o que é
    exato, e não a simplificação de 17.2.4.1 (que agruparia no CENTROIDE da
    armadura, coisa diferente e não usada aqui).
    """
    acumulado: dict[float, float] = {}
    for barra in secao.barras:
        y = round(barra.pos_h if plano == "xx" else barra.pos_b, 12)
        acumulado[y] = acumulado.get(y, 0.0) + barra.area
    return tuple(sorted(acumulado.items()))


@dataclass(frozen=True)
class ResultadoMRd:
    """M_Rd de uma flexão composta NORMAL, com x, domínio e diagnóstico.

    Ref.: ABNT NBR 6118:2023, item 17.2.2 e Figura 17.1, p. 120-122
    [deriv: DER-NBR6118-17.2.2-MRd-varredura]
    [req: REQ-PILARETE-12-memorial-e-o-que-ele-e-obrigado-a-dizer]  (h)
    """

    plano: str
    """``"xx"`` (flexão no plano de h) ou ``"yy"`` (flexão no plano de b)."""

    N_Sd: float
    """Normal para a qual este M_Rd foi calculado [kN]. Ver 17.2.5."""

    M_Rd_normal: float
    """Momento resistente da flexão composta NORMAL [kN·m]."""

    x_linha_neutra: float
    """Profundidade da linha neutra que equilibra N_Sd [m]."""

    dominio: str
    """Nome do domínio da Figura 17.1 em que a seção caiu."""

    polo: str
    """Polo da Figura 17.1 em que o perfil pivotou: A, B ou C."""

    eps_borda_comprimida: float
    eps_armadura_mais_tracionada: float
    iteracoes: int
    residuo_de_N: float
    """|N_Rd(x*) − N_Sd| [kN] ao fim da bisseção."""


def _nomear_dominio(perfil: PerfilDeDeformacao, *, altura: float,
                    d_max: float, eps_s_max_tracao: float,
                    aco: Aco) -> str:
    """Nomeia o domínio da Figura 17.1 — só para o memorial, não altera número.

    Ref.: ABNT NBR 6118:2023, item 17.2.2, alínea g) e Figura 17.1, p. 122
    [rule: NBR6118-17.2.2-fig17.1-limites-dos-dominios]
    [deriv: DER-NBR6118-8.3.6-sigma-s-ate-10-por-mil]

    É AQUI, e SÓ aqui, que ``eps_yd = f_yd/E_s`` é usado (fronteira dos
    domínios 3 e 4). Ele não entra em conta nenhuma: sigma_s sai de
    min(E_s·eps, f_yd), que não precisa saber onde fica o joelho. Nome de
    domínio impresso em relatório não altera número.

    ``eps_yd`` aparece na Figura 17.1 apenas como RÓTULO de abscissa, sem
    valor e sem expressão — lacuna reconfirmada por leitura visual do a2.
    """
    if perfil.polo == "A":
        return _ROTULOS_DE_DOMINIO[2]
    if perfil.polo == "C":
        return _ROTULOS_DE_DOMINIO[5]
    if perfil.x > d_max:
        return _ROTULOS_DE_DOMINIO["4a"]
    return (_ROTULOS_DE_DOMINIO[3] if eps_s_max_tracao >= aco.eps_yd
            else _ROTULOS_DE_DOMINIO[4])


def momento_resistente_normal(secao: SecaoRetangular, N_Sd: float, *,
                              plano: str) -> ResultadoMRd:
    """M_Rd,xx ou M_Rd,yy por varredura de equilíbrio, para N_Rd = N_Sd.

    Ref.: ABNT NBR 6118:2023, itens 17.2.1, 17.2.2 e 17.2.5, p. 120-125
    [rule: NBR6118-17.2.1-envoltoria-criterio-de-seguranca]
    [rule: NBR6118-17.2.2-fig17.1-limites-dos-dominios]
    [rule: NBR6118-17.2.5-flexao-composta-obliqua]
    [deriv: DER-NBR6118-17.2.2-MRd-varredura]
    [deriv: DER-NBR6118-NRd0-compressao-centrada]  (guarda de entrada)
    [req: REQ-PILARETE-15-veredito-de-ELU-de-solicitacoes-normais]  (3)

    ``plano="xx"`` resolve a flexão no plano de ``h_secao`` (altura = h,
    largura = b); ``plano="yy"`` resolve no plano de ``b_secao`` (altura = b,
    largura = h) com as coordenadas das barras transpostas. Resolver DUAS
    vezes, uma por eixo principal, e NUNCA com linha neutra inclinada, é o que
    17.2.5 autoriza — e o preço declarado da redução é ela ser "processo
    aproximado".

    TRÊS RECUSAS, e nenhuma delas devolve "o último valor da iteração":

    * ``N_Sd > N_Rd0`` -> não existe equilíbrio a procurar;
    * raiz de ``N_Rd(x) = N_Sd`` NÃO colchetada -> recusa;
    * ``|eps_s| > 10 ‰`` em qualquer camada -> recusa (vinda de
      :func:`~calc_core.estrutural.materiais_6118.sigma_s`), porque eps_su não
      tem valor na Norma.

    A busca é uma BISSEÇÃO na variável ``t = x/(x + altura)``, que leva
    ``x`` de 0 a infinito num intervalo limitado — é isso que torna a reta b
    (x -> oo) um ponto ALCANÇÁVEL da busca em vez de um limite assintótico
    inatingível, e é o que permite a verificação cruzada contra N_Rd0.
    ``N_Rd(x)`` é monótona crescente em x, então a bisseção é robusta e não
    depende de derivada.

    É PROIBIDO reaproveitar um M_Rd,xx calculado para OUTRO N_Sd: a condição
    "M_Rd,xx e M_Rd,yy para o mesmo N_Rd = N_Sd" está escrita em 17.2.5 e é o
    erro silencioso mais provável de quem faz cache.
    """
    if plano not in ("xx", "yy"):
        raise RecusaForaDeDominio(
            parametro="plano", valor=plano, intervalo="'xx' ou 'yy'",
            fonte="ABNT NBR 6118:2023, 17.2.5, p. 125",
            forca=DECLARADO_EM_TEXTO,
            apoio_no_ruleset="NBR6118-17.2.5-flexao-composta-obliqua")

    limite = N_Rd0(secao)
    if N_Sd > limite:
        raise RecusaForaDeDominio(
            parametro="N_Sd",
            valor=round(N_Sd, 4),
            intervalo=f"<= N_Rd0 = {limite:.4f} kN",
            fonte="ABNT NBR 6118:2023, 17.2.1 e 17.2.2-g), p. 120-122 — acima "
                  "de N_Rd0 (compressão centrada, reta b da Figura 17.1) não "
                  "existe equilíbrio de seção a procurar",
            forca=DECLARADO_EM_TEXTO,
            apoio_no_ruleset="DER-NBR6118-NRd0-compressao-centrada",
            sugestao=(f"N_Sd = {N_Sd:.2f} kN contra N_Rd0 = {limite:.2f} kN "
                      "(nu = " + (f"{N_Sd / limite:.3f}" if limite else "inf")
                      + "). N_Rd0 é condição NECESSÁRIA e NÃO suficiente: "
                      "ultrapassá-lo REPROVA, mas atendê-lo NÃO aprova."),
        )

    altura = secao.h_secao if plano == "xx" else secao.b_secao
    largura = secao.b_secao if plano == "xx" else secao.h_secao
    camadas = _camadas(secao, plano)
    d_max = max(y for y, _ in camadas)

    def _x_de(t: float) -> float:
        return altura * t / (1.0 - t)

    def _N_de(t: float) -> float:
        N, _, _ = esforcos_resistentes_em_x(
            _x_de(t), altura=altura, largura=largura, camadas=camadas,
            concreto=secao.concreto, aco=secao.aco)
        return N

    t_lo, t_hi = 1.0e-9, 1.0 - 1.0e-13
    N_lo, N_hi = _N_de(t_lo), _N_de(t_hi)
    if not (N_lo <= N_Sd <= N_hi):
        raise RecusaForaDeDominio(
            parametro="N_Sd",
            valor=round(N_Sd, 6),
            intervalo=f"[{N_lo:.6f} ; {N_hi:.6f}] kN (raiz colchetada)",
            fonte="ABNT NBR 6118:2023, 17.2.2, p. 120-122 — o equilíbrio "
                  "N_Rd(x) = N_Sd não tem raiz no domínio da Figura 17.1",
            forca=DECLARADO_EM_TEXTO,
            apoio_no_ruleset="DER-NBR6118-17.2.2-MRd-varredura",
            sugestao="É PROIBIDO devolver o valor do último passo da iteração: "
                     "o software RECUSA. Uma normal de TRAÇÃO abaixo do limite "
                     "de escoamento da armadura cai fora do domínio aprovado.",
        )

    escala = max(1.0, abs(N_Sd))
    iteracoes = 0
    t_meio = 0.5 * (t_lo + t_hi)
    for iteracoes in range(1, MAX_ITERACOES_BISSECAO + 1):
        t_meio = 0.5 * (t_lo + t_hi)
        N_meio = _N_de(t_meio)
        if abs(N_meio - N_Sd) <= TOLERANCIA_RELATIVA_DE_N * escala:
            break
        if N_meio < N_Sd:
            t_lo = t_meio
        else:
            t_hi = t_meio
        if t_hi - t_lo <= 1.0e-16:
            break
    else:  # pragma: no cover - só com aritmética patológica
        raise RecusaForaDeDominio(
            parametro="convergencia_da_bissecao",
            valor=MAX_ITERACOES_BISSECAO,
            intervalo=f"resíduo <= {TOLERANCIA_RELATIVA_DE_N} · max(1, |N_Sd|)",
            fonte="ABNT NBR 6118:2023, 17.2.2, p. 120-122 — a Norma não "
                  "prescreve método numérico; o critério de convergência é "
                  "declarado por este software",
            forca=ESCOPO_DESTA_VERSAO,
            apoio_no_ruleset="DER-NBR6118-17.2.2-MRd-varredura",
        )

    x_estrela = _x_de(t_meio)
    N_final, M_final, perfil = esforcos_resistentes_em_x(
        x_estrela, altura=altura, largura=largura, camadas=camadas,
        concreto=secao.concreto, aco=secao.aco)
    eps_s_max_tracao = -perfil.deformacao_em(d_max)

    return ResultadoMRd(
        plano=plano,
        N_Sd=N_Sd,
        M_Rd_normal=M_final,
        x_linha_neutra=x_estrela,
        dominio=_nomear_dominio(perfil, altura=altura, d_max=d_max,
                                eps_s_max_tracao=eps_s_max_tracao,
                                aco=secao.aco),
        polo=perfil.polo,
        eps_borda_comprimida=perfil.eps_borda_comprimida,
        eps_armadura_mais_tracionada=eps_s_max_tracao,
        iteracoes=iteracoes,
        residuo_de_N=abs(N_final - N_Sd),
    )


def momento_resistente_por_faixas(
    secao: SecaoRetangular, x: float, *, plano: str,
    faixas_iniciais: int = 500, tolerancia_relativa: float = 1.0e-8,
    faixas_maximas: int = 512_000,
) -> tuple[float, float, int]:
    """SEGUNDA implementação, por faixas com refinamento — só para conferência.

    Ref.: ABNT NBR 6118:2023, itens 17.2.2 e 8.2.10.1, p. 120-122 e 26
    [deriv: DER-NBR6118-17.2.2-MRd-varredura]

    Devolve ``(N_Rd, M_Rd, faixas_usadas)`` integrando por REGRA DO PONTO
    MÉDIO e DOBRANDO o número de faixas até que a variação relativa de M_Rd
    caia abaixo de ``tolerancia_relativa`` — que é literalmente o critério que
    o ``limite_declarado`` da derivação pede ("refinamento até variação de
    M_Rd abaixo de um limiar declarado").

    NÃO É O CAMINHO DE PRODUÇÃO. :func:`esforcos_resistentes_em_x` integra em
    forma FECHADA e é ela que alimenta o veredito. Esta função existe para o
    GATE 3 ter DOIS caminhos independentes sobre a mesma derivação — um
    algébrico e um numérico — e poder comparar. Se um dia divergirem, é sinal
    de defeito em um dos dois, e é exatamente isso que se quer detectar.

    Chama :func:`~calc_core.estrutural.materiais_6118.sigma_c` faixa a faixa,
    o que exercita o PATAMAR do diagrama (a expressão da parábola avaliada
    acima de eps_c2 decresce) — a forma fechada trata o patamar como um
    retângulo separado, então os dois caminhos testam coisas diferentes.
    """
    altura = secao.h_secao if plano == "xx" else secao.b_secao
    largura = secao.b_secao if plano == "xx" else secao.h_secao
    camadas = _camadas(secao, plano)
    d_max = max(y for y, _ in camadas)
    perfil = perfil_de_deformacao(x, altura=altura, d_max=d_max,
                                  f_ck_MPa=secao.concreto.fck)
    y_c = min(x, altura)

    N_aco = 0.0
    M_aco = 0.0
    for y_i, A_si in camadas:
        tensao = sigma_s(perfil.deformacao_em(y_i), secao.aco) * 1000.0
        N_aco += A_si * tensao
        M_aco += A_si * tensao * (altura / 2.0 - y_i)

    faixas = faixas_iniciais
    # O critério de parada é sobre M_Rd APENAS, e isso é o que a derivação
    # declara ("refinamento até variação de M_Rd abaixo de um limiar
    # declarado"). Não se guarda um N anterior porque N não entra no critério:
    # guardá-lo sem usar sugeriria um teste de convergência que não existe, e
    # ACRESCENTAR N ao critério seria implementar além do que a derivação
    # aprovada autoriza.
    M_anterior = None
    while faixas <= faixas_maximas:
        passo = y_c / faixas
        N_c = 0.0
        M_c = 0.0
        for indice in range(faixas):
            y = (indice + 0.5) * passo
            tensao = sigma_c(perfil.deformacao_em(y), secao.concreto) * 1000.0
            N_c += tensao * largura * passo
            M_c += tensao * largura * passo * (altura / 2.0 - y)
        if M_anterior is not None:
            variacao = abs(M_c - M_anterior) / max(1.0, abs(M_c))
            if variacao <= tolerancia_relativa:
                return N_c + N_aco, M_c + M_aco, faixas
        M_anterior = M_c
        faixas *= 2

    raise RecusaForaDeDominio(  # pragma: no cover - refinamento não converge
        parametro="faixas",
        valor=faixas_maximas,
        intervalo=f"variação relativa de M_Rd <= {tolerancia_relativa}",
        fonte="ABNT NBR 6118:2023, 17.2.2, p. 120-122",
        forca=ESCOPO_DESTA_VERSAO,
        apoio_no_ruleset="DER-NBR6118-17.2.2-MRd-varredura",
    )


def envoltoria_minima_1a_ordem(M_1d_min_xx: float, M_1d_min_yy: float,
                               numero_de_pontos: int = 721,
                               ) -> tuple[tuple[float, float], ...]:
    """Pontos da ELIPSE mínima de 1ª ordem (Figura 11.3), para o croqui.

    Ref.: ABNT NBR 6118:2023, item 11.3.3.4.3 e Figura 11.3, p. 61
    [rule: NBR6118-11.3.3.4.3-fig11.3-envoltoria-minima-1a-ordem]

        (M_x/M_1d,mín,xx)² + (M_y/M_1d,mín,yy)² = 1

    O EXPOENTE É 2, e não o ``alpha_interacao`` de 17.2.5. As duas expressões
    estão em LADOS OPOSTOS da verificação: esta é a envoltória SOLICITANTE
    mínima; a de 17.2.5 é a RESISTENTE. Confirmado por leitura visual do a2 na
    p. impressa 61, com atenção deliberada a este ponto.

    Função de APOIO (desenho e teste); o veredito usa a forma fechada de
    :func:`indice_de_inclusao_da_envoltoria_minima`, que não discretiza nada.
    """
    pontos = []
    for indice in range(numero_de_pontos):
        angulo = 2.0 * math.pi * indice / (numero_de_pontos - 1)
        pontos.append((M_1d_min_xx * math.cos(angulo),
                       M_1d_min_yy * math.sin(angulo)))
    return tuple(pontos)


def interacao_flexao_obliqua(M_Sd_x: float, M_Sd_y: float,
                             M_Rd_normal_xx: float, M_Rd_normal_yy: float,
                             alpha_interacao: float = ALPHA_INTERACAO_VEREDITO,
                             ) -> float:
    """Índice de interação de 17.2.5 [adimensional]; ATENDE quando <= 1.

    Ref.: ABNT NBR 6118:2023, item 17.2.5, p. 125
    [rule: NBR6118-17.2.5-flexao-composta-obliqua]
    [deriv: DER-NBR6118-17.2.5-criterio-menor-ou-igual-a-1]

        (|M_Sd,x|/M_Rd,xx)^alpha_interacao
      + (|M_Sd,y|/M_Rd,yy)^alpha_interacao   <= 1

    A NORMA ESCREVE "= 1", NÃO "<= 1". A expressão descreve a SUPERFÍCIE da
    envoltória resistente; ler o INTERIOR como conjunto admissível é
    INTERPRETAÇÃO do agente, aprovada em derivação própria e declarada no
    memorial. Um ``[rule: ]`` apontando para a DESIGUALDADE (e não para a
    igualdade transcrita) seria defeito com veto — daí o ``[deriv: ]`` acima.

    Note os SUBSCRITOS: ``M_Rd_normal_xx`` é o resistente da flexão composta
    NORMAL; ``M_Rd_obliquo_x`` (com um "x" só) seria a COMPONENTE oblíqua,
    incógnita da própria expressão de 17.2.5. Um "x" a mais ou a menos troca o
    significado, e é a colisão de subscrito registrada em REQ-PILARETE-01.

    Valores ABSOLUTOS: só legítimo com arranjo de armadura simétrico nos dois
    eixos — quem verifica é :func:`verificar_elu_solicitacoes_normais`.
    """
    exigir_positivo("M_Rd_normal_xx", M_Rd_normal_xx,
                    fonte="ABNT NBR 6118:2023, 17.2.5, p. 125",
                    apoio_no_ruleset="NBR6118-17.2.5-flexao-composta-obliqua")
    exigir_positivo("M_Rd_normal_yy", M_Rd_normal_yy,
                    fonte="ABNT NBR 6118:2023, 17.2.5, p. 125",
                    apoio_no_ruleset="NBR6118-17.2.5-flexao-composta-obliqua")
    return ((abs(M_Sd_x) / M_Rd_normal_xx) ** alpha_interacao
            + (abs(M_Sd_y) / M_Rd_normal_yy) ** alpha_interacao)


def indice_de_inclusao_da_envoltoria_minima(
    M_1d_min_xx: float, M_1d_min_yy: float,
    M_Rd_normal_xx: float, M_Rd_normal_yy: float,
) -> float:
    """Índice EXATO de inclusão da elipse mínima na envoltória resistente.

    Ref.: ABNT NBR 6118:2023, item 11.3.3.4.3 e Figura 11.3, p. 61
    [rule: NBR6118-11.3.3.4.3-fig11.3-envoltoria-minima-1a-ordem]
    [deriv: DER-NBR6118-11.3.3.4.3-inclusao-de-envoltorias]
    [req: REQ-PILARETE-15-veredito-de-ELU-de-solicitacoes-normais]  (5)

        I_B = sqrt( (M_1d,mín,xx/M_Rd,xx)² + (M_1d,mín,yy/M_Rd,yy)² )  <= 1

    A Norma manda a envoltória resistente ENGLOBAR a envoltória mínima e NÃO
    escreve o teste de inclusão de uma curva na outra. O teste é derivação, em
    quatro passos: (1) "englobar" é inclusão de conjuntos; (2) basta testar a
    CURVA, porque o conjunto resistente de expoente >= 1 é CONVEXO e contém a
    origem; (3) para alpha_interacao = 1 o máximo de
    M_x/M_Rd,xx + M_y/M_Rd,yy sobre a elipse tem FORMA FECHADA EXATA, por
    Cauchy-Schwarz — sem discretização, sem máximo perdido entre dois pontos
    amostrados; (4) os dois expoentes são diferentes de propósito (2 no
    solicitante, alpha no resistente).

    É PROIBIDO OMITIR A RAIZ QUADRADA. Erro do lado INSEGURO e INVISÍVEL à
    análise dimensional — no sanity check do a2 o valor sem raiz é 0,2817
    contra 0,5307 correto, isto é, 47 % do valor certo. Teste de mutação
    obrigatório no GATE 3.

    É PROIBIDO usar esta forma fechada com alpha_interacao != 1: com 1,2 o
    máximo sobre a elipse não tem forma fechada e exigiria varredura com
    refinamento declarado.
    """
    exigir_positivo("M_Rd_normal_xx", M_Rd_normal_xx,
                    fonte="ABNT NBR 6118:2023, 11.3.3.4.3, p. 61",
                    apoio_no_ruleset="DER-NBR6118-11.3.3.4.3-inclusao-de-envoltorias")
    exigir_positivo("M_Rd_normal_yy", M_Rd_normal_yy,
                    fonte="ABNT NBR 6118:2023, 11.3.3.4.3, p. 61",
                    apoio_no_ruleset="DER-NBR6118-11.3.3.4.3-inclusao-de-envoltorias")
    return math.sqrt((M_1d_min_xx / M_Rd_normal_xx) ** 2
                     + (M_1d_min_yy / M_Rd_normal_yy) ** 2)


def indice_do_canto(M_Sd_x: float, M_Sd_y: float,
                    M_1d_min_xx: float, M_1d_min_yy: float,
                    M_Rd_normal_xx: float, M_Rd_normal_yy: float) -> float:
    """Índice do CANTO — atalho que só pode APROVAR, jamais reprovar.

    Ref.: ABNT NBR 6118:2023, itens 11.3.3.4.3 e 17.2.5, p. 61 e 125
    [deriv: DER-NBR6118-11.3.3.4.3-inclusao-de-envoltorias]
    [req: REQ-PILARETE-15-veredito-de-ELU-de-solicitacoes-normais]  (7)

        max(|M_Sd,x|, M_1d,mín,xx)/M_Rd,xx
      + max(|M_Sd,y|, M_1d,mín,yy)/M_Rd,yy   <= 1

    Tomar os dois máximos SIMULTANEAMENTE é o CANTO do retângulo circunscrito
    à elipse da Figura 11.3, e é 41 % MAIS SEVERO do que o critério que a
    Norma escreve (48,00 contra 33,94 kN·m de M_R exigido no sanity check).

    DIREÇÃO ÚNICA, e é a razão de este atalho existir: passando no canto,
    passa nas verificações A e B simultaneamente — o retângulo contém a elipse
    e o conjunto resistente de 17.2.5 com expoente >= 1 é convexo. FALHANDO no
    canto, o código É OBRIGADO a calcular A e B; reprovar pelo canto seria
    substituir o critério escrito na Figura 11.3 por outro, mais duro,
    inventado aqui. Foi exatamente esse o achado D2 que corrigiu a v11.
    """
    return (max(abs(M_Sd_x), M_1d_min_xx) / M_Rd_normal_xx
            + max(abs(M_Sd_y), M_1d_min_yy) / M_Rd_normal_yy)


@dataclass(frozen=True)
class ResultadoELUNormal:
    """Veredito do ELU de solicitações NORMAIS, com tudo que o memorial exige.

    Ref.: ABNT NBR 6118:2023, itens 17.2.1, 17.2.5 e 11.3.3.4.3, p. 120-125 e 61
    [rule: NBR6118-17.2.1-envoltoria-criterio-de-seguranca]
    [req: REQ-PILARETE-12-memorial-e-o-que-ele-e-obrigado-a-dizer]  (h, i, j, k)
    [req: REQ-PILARETE-15-veredito-de-ELU-de-solicitacoes-normais]
    """

    N_Sd: float
    M_Sd_x: float
    M_Sd_y: float
    M_1d_min_xx: float
    M_1d_min_yy: float
    resultado_xx: ResultadoMRd
    resultado_yy: ResultadoMRd
    N_Rd0_informativo: float
    nu_informativo: float
    """N_Sd/N_Rd0 — INFORMATIVO. Não decide nada (REQ-PILARETE-06-C)."""
    indice_A_par_solicitante: float
    indice_B_envoltoria_minima: float
    indice_canto: float
    indice_A_com_alpha_1_2_informativo: float
    aprovado_por_atalho_do_canto: bool
    alpha_interacao_usado: float
    atendido: bool
    """Conjunção de A **e** B. Aprovar com uma só é defeito com veto do a6."""

    @property
    def nome_do_veredito(self) -> str:
        """Nome EXATO do veredito de §17.2, sem atalho.

        Ref.: ABNT NBR 6118:2023, item 17.2.1, p. 120
        [rule: NBR6118-17.2.1-envoltoria-criterio-de-seguranca]
        [req: REQ-PILARETE-16-escopo-do-veredito-e-o-cortante-nao-verificado]

        "ELU de solicitações NORMAIS (NBR 6118:2023, 17.2.1): ATENDIDO / NÃO
        ATENDIDO". Nunca "pilarete OK", nunca "ELU" sem o qualificador. O nome
        COMPLETO do veredito do elemento, que depende da FAIXA de 14.4.1, é
        montado em :mod:`calc_core.estrutural.pilarete.elemento`.
        """
        estado = "ATENDIDO" if self.atendido else "NÃO ATENDIDO"
        return (f"ELU de solicitações NORMAIS (NBR 6118:2023, 17.2.1): {estado}")


def verificar_elu_solicitacoes_normais(
    secao: SecaoRetangular, *, N_Sd: float, M_Sd_x: float, M_Sd_y: float,
    M_1d_min_xx: float, M_1d_min_yy: float,
) -> ResultadoELUNormal:
    """Veredito de ELU de solicitações normais: verificação A **e** B.

    Ref.: ABNT NBR 6118:2023, itens 17.2.1, 17.2.5, 17.2.2 e 11.3.3.4.3,
    p. 120, 125, 122 e 61
    [rule: NBR6118-17.2.1-envoltoria-criterio-de-seguranca]
    [rule: NBR6118-17.2.5-flexao-composta-obliqua]
    [rule: NBR6118-11.3.3.4.3-fig11.3-envoltoria-minima-1a-ordem]
    [rule: NBR6118-17.2.4.1-concentracao-de-armaduras]  (NÃO usado, citado)
    [deriv: DER-NBR6118-17.2.2-MRd-varredura]
    [deriv: DER-NBR6118-17.2.5-criterio-menor-ou-igual-a-1]
    [deriv: DER-NBR6118-11.3.3.4.3-inclusao-de-envoltorias]
    [req: REQ-PILARETE-15-veredito-de-ELU-de-solicitacoes-normais]

    DUAS VERIFICAÇÕES, AMBAS NECESSÁRIAS, NENHUMA IMPLICA A OUTRA:

    * **A — par solicitante REAL** (17.2.1 + 17.2.5), com
      ``alpha_interacao = 1,0``: cobre o esforço que de fato atua.
    * **B — inclusão da envoltória MÍNIMA** (11.3.3.4.3), em forma fechada
      exata: cobre o momento mínimo que a Norma impõe INDEPENDENTEMENTE do
      carregamento.

    APROVAR COM UMA SÓ É DEFEITO COM VETO DO a6.

    O ATALHO DO CANTO é calculado e, quando passa, dispensa nada — as duas
    verificações são feitas de qualquer modo, porque os índices vão ao
    memorial. O que o atalho garante é a implicação lógica, registrada no
    campo ``aprovado_por_atalho_do_canto``; ele NUNCA reprova.

    ``alpha_interacao = 1,2`` é calculado e exposto como INFORMATIVO, com a
    frase de que 17.2.5 o autorizaria para seção retangular. É PROIBIDO que
    decida o veredito nesta versão.

    PRÉ-CONDIÇÕES (REQ-PILARETE-15(1)): só entra aqui quem já passou por
    REQ-PILARETE-03 (13.2.3), -05 (pilar curto), -06-D (j >= 28 dias) e -11
    (junta). Quem orquestra a ordem é
    :mod:`calc_core.estrutural.pilarete.elemento`.
    """
    if not secao.arranjo_simetrico():
        raise RecusaForaDeDominio(
            parametro="arranjo_de_armadura",
            valor="assimétrico em pelo menos um eixo",
            intervalo="simétrico nos DOIS eixos da seção",
            fonte="ABNT NBR 6118:2023, 17.2.5, p. 125 — a redução aos valores "
                  "absolutos dos momentos solicitantes pressupõe envoltória "
                  "simétrica nos quatro quadrantes",
            forca=ESCOPO_DESTA_VERSAO,
            apoio_no_ruleset="DER-NBR6118-17.2.5-criterio-menor-ou-igual-a-1",
            sugestao="É PROIBIDO ASSUMIR a simetria. Com arranjo assimétrico "
                     "seria preciso avaliar os quatro quadrantes com os "
                     "sinais, o que esta versão não implementa: RECUSA.",
        )

    resultado_xx = momento_resistente_normal(secao, N_Sd, plano="xx")
    resultado_yy = momento_resistente_normal(secao, N_Sd, plano="yy")
    M_Rd_normal_xx = resultado_xx.M_Rd_normal
    M_Rd_normal_yy = resultado_yy.M_Rd_normal

    indice_A = interacao_flexao_obliqua(
        M_Sd_x, M_Sd_y, M_Rd_normal_xx, M_Rd_normal_yy,
        ALPHA_INTERACAO_VEREDITO)
    indice_B = indice_de_inclusao_da_envoltoria_minima(
        M_1d_min_xx, M_1d_min_yy, M_Rd_normal_xx, M_Rd_normal_yy)
    indice_canto = indice_do_canto(
        M_Sd_x, M_Sd_y, M_1d_min_xx, M_1d_min_yy,
        M_Rd_normal_xx, M_Rd_normal_yy)
    indice_A_1_2 = interacao_flexao_obliqua(
        M_Sd_x, M_Sd_y, M_Rd_normal_xx, M_Rd_normal_yy,
        ALPHA_INTERACAO_INFORMATIVO)

    limite = N_Rd0(secao)
    return ResultadoELUNormal(
        N_Sd=N_Sd, M_Sd_x=M_Sd_x, M_Sd_y=M_Sd_y,
        M_1d_min_xx=M_1d_min_xx, M_1d_min_yy=M_1d_min_yy,
        resultado_xx=resultado_xx, resultado_yy=resultado_yy,
        N_Rd0_informativo=limite,
        nu_informativo=N_Sd / limite if limite else float("inf"),
        indice_A_par_solicitante=indice_A,
        indice_B_envoltoria_minima=indice_B,
        indice_canto=indice_canto,
        indice_A_com_alpha_1_2_informativo=indice_A_1_2,
        aprovado_por_atalho_do_canto=indice_canto <= 1.0,
        alpha_interacao_usado=ALPHA_INTERACAO_VEREDITO,
        atendido=(indice_A <= 1.0) and (indice_B <= 1.0),
    )
