"""Pilarete — ELU de solicitações NORMAIS (17.2) e a envoltória mínima (11.3.3.4.3).

Cobre REQ-PILARETE-06 (N_Rd0 como limite superior e a proibição de veredito
por ele), REQ-PILARETE-15 (as verificações A e B, o atalho do canto, a
simetria) e os testes de propriedade (7) a (15) de REQ-PILARETE-13.

NÃO HÁ CONFERÊNCIA DE TERCEIROS, e é preciso dizer por quê: a busca negativa
do a1, reconferida pelo a2, não achou no acervo UM ÚNICO exemplo resolvido de
seção de pilar sob N + Mx + My. O "Exemplo 4 — Sapata Isolada Sob Flexão
Oblíqua" de Bastos NÃO serve: é problema GEOTÉCNICO de pressões na base, não
dimensiona seção nenhuma. Os valores usados aqui como referência
(39,05 / 78,70 / 63,95 / 32,21 kN·m e o par 91,41 / 37,05) são do SANITY CHECK
DO a2 — verificação interna independente, não fonte externa. A lacuna
continua registrada para o GATE 3.
"""
import math

import pytest

from calc_core.estrutural.dominio import RecusaForaDeDominio
from calc_core.estrutural.pilarete.secao import (
    ALPHA_INTERACAO_INFORMATIVO,
    ALPHA_INTERACAO_VEREDITO,
    BarraLongitudinal,
    N_Rd0,
    SecaoRetangular,
    esforcos_resistentes_em_x,
    envoltoria_minima_1a_ordem,
    indice_de_inclusao_da_envoltoria_minima,
    indice_do_canto,
    interacao_flexao_obliqua,
    momento_resistente_normal,
    momento_resistente_por_faixas,
    verificar_elu_solicitacoes_normais,
)
from calc_core.sapata_isolada.materiais import Aco, Concreto, area_barra

D_LINHA = 0.058
"""d' = cobrimento 45 mm + estribo 5 mm + phi/2 = 58 mm (30×30, phi 16)."""


def secao(h=0.30, b=0.30, phi_mm=16.0, fck=25.0, d_linha=D_LINHA):
    """Seção retangular com UMA barra por vértice — o arranjo de 18.4.2.2."""
    area = area_barra(phi_mm)
    barras = tuple(BarraLongitudinal(pos_h=ph, pos_b=pb, area=area)
                   for ph in (d_linha, h - d_linha)
                   for pb in (d_linha, b - d_linha))
    return SecaoRetangular(h_secao=h, b_secao=b, barras=barras,
                           concreto=Concreto(fck=fck), aco=Aco(fyk=500.0))


# --- REQ-PILARETE-06-C e -13(7): N_Rd0 e a degeneração na reta b -----------

def test_varredura_reproduz_N_Rd0_na_reta_b():
    """REQ-PILARETE-13(7): x -> infinito tem de reproduzir a forma fechada.

    É a ÚNICA verificação cruzada forte disponível — dois caminhos
    independentes sobre a mesma derivação, um numérico e um algébrico. Medido
    pelo a2: 0,000 % de diferença.
    """
    s = secao()
    camadas = ((D_LINHA, 2 * area_barra(16.0)),
               (0.30 - D_LINHA, 2 * area_barra(16.0)))
    N, _, perfil = esforcos_resistentes_em_x(
        0.30 * 1e12, altura=0.30, largura=0.30, camadas=camadas,
        concreto=s.concreto, aco=s.aco)
    assert perfil.polo == "C"
    assert N == pytest.approx(N_Rd0(s), rel=1e-9)


def test_N_Sd_acima_de_N_Rd0_recusa_sem_devolver_a_ultima_iteracao():
    """REQ-PILARETE-13(15): não existe equilíbrio a procurar acima de N_Rd0."""
    s = secao()
    with pytest.raises(RecusaForaDeDominio) as erro:
        momento_resistente_normal(s, N_Rd0(s) * 1.001, plano="xx")
    assert "N_Rd0" in erro.value.mensagem


def test_N_Rd0_nao_aprova_sozinho():
    """REQ-PILARETE-06-C: condição NECESSÁRIA e NÃO SUFICIENTE.

    Caso construído: N_Sd BEM abaixo de N_Rd0 (nu = 0,88) e ainda assim o ELU
    de solicitações normais NÃO É ATENDIDO, porque o momento mínimo de
    11.3.3.4.3 não cabe na envoltória resistente. Se o veredito saísse de
    N_Rd0, este pilarete seria "aprovado".
    """
    s = secao()
    N_Sd = 1500.0
    assert N_Sd < N_Rd0(s)
    resultado = verificar_elu_solicitacoes_normais(
        s, N_Sd=N_Sd, M_Sd_x=0.0, M_Sd_y=0.0,
        M_1d_min_xx=N_Sd * 0.024, M_1d_min_yy=N_Sd * 0.024)
    assert resultado.nu_informativo < 1.0
    assert resultado.atendido is False


# --- REQ-PILARETE-13(14): física da curva N-M ------------------------------

def test_curva_N_M_sobe_e_depois_desce():
    """Bojo da flexão composta balanceada. Curva monótona é sinal de defeito.

    Valores do sanity check do a2 para 30×30/C25/CA-50/4 phi 16: 39,05 (N=0),
    78,70 (N=500), 63,95 (N=1000), 32,21 kN·m (N=1400).
    """
    s = secao()
    esperados = {0.0: 39.05, 500.0: 78.70, 1000.0: 63.95, 1400.0: 32.21}
    obtidos = {}
    for N, esperado in esperados.items():
        resultado = momento_resistente_normal(s, max(N, 1e-9), plano="xx")
        obtidos[N] = resultado.M_Rd_normal
        assert resultado.M_Rd_normal == pytest.approx(esperado, abs=0.02)
    assert obtidos[500.0] > obtidos[0.0]
    assert obtidos[1000.0] < obtidos[500.0]
    assert obtidos[1400.0] < obtidos[1000.0]


def test_M_Rd_tende_a_zero_em_N_Rd0():
    """Em compressão centrada não sobra capacidade de momento."""
    s = secao()
    limite = N_Rd0(s)
    quase = momento_resistente_normal(s, limite * (1 - 1e-9), plano="xx")
    assert quase.M_Rd_normal == pytest.approx(0.0, abs=1e-3)


# --- REQ-PILARETE-13(8): degeneração uniaxial ------------------------------

def test_com_M_Sd_y_nulo_a_verificacao_obliqua_vira_a_normal():
    """Com M_Sd,y = 0 o índice A é exatamente |M_Sd,x|/M_Rd,xx, e vice-versa."""
    s = secao()
    M_Rd_xx = momento_resistente_normal(s, 1000.0, plano="xx").M_Rd_normal
    M_Rd_yy = momento_resistente_normal(s, 1000.0, plano="yy").M_Rd_normal
    assert interacao_flexao_obliqua(30.0, 0.0, M_Rd_xx, M_Rd_yy) == (
        pytest.approx(30.0 / M_Rd_xx))
    assert interacao_flexao_obliqua(0.0, 30.0, M_Rd_xx, M_Rd_yy) == (
        pytest.approx(30.0 / M_Rd_yy))


# --- REQ-PILARETE-13(9): ordenação dos critérios ---------------------------

def test_ordenacao_canto_maior_ou_igual_alpha1_maior_ou_igual_alpha12():
    """canto >= índice(alpha=1) >= índice(alpha=1,2), SEMPRE.

    Consequência de t^1,2 <= t em [0,1]; verificado pelo a2 em 20.000 pares.
    Se a implementação inverter, há erro de expoente ou de sinal.
    """
    s = secao(h=0.40, b=0.20)
    M_Rd_xx = momento_resistente_normal(s, 800.0, plano="xx").M_Rd_normal
    M_Rd_yy = momento_resistente_normal(s, 800.0, plano="yy").M_Rd_normal
    for M_x, M_y in ((10.0, 5.0), (30.0, 12.0), (21.6, 16.8), (5.0, 20.0)):
        canto = indice_do_canto(M_x, M_y, 21.6, 16.8, M_Rd_xx, M_Rd_yy)
        alpha_1 = interacao_flexao_obliqua(M_x, M_y, M_Rd_xx, M_Rd_yy,
                                           ALPHA_INTERACAO_VEREDITO)
        alpha_12 = interacao_flexao_obliqua(M_x, M_y, M_Rd_xx, M_Rd_yy,
                                            ALPHA_INTERACAO_INFORMATIVO)
        assert canto >= alpha_1 - 1e-12
        assert alpha_1 >= alpha_12 - 1e-12


# --- REQ-PILARETE-13(10): forma fechada contra varredura -------------------

def test_forma_fechada_do_indice_B_coincide_com_o_maximo_sobre_a_elipse():
    """Cauchy-Schwarz contra varredura numérica da elipse da Figura 11.3.

    O índice de inclusão é o MÁXIMO de M_x/M_Rd,xx + M_y/M_Rd,yy sobre a
    elipse mínima; a forma fechada tem de coincidir com o máximo amostrado.
    """
    for h, b, N in ((0.30, 0.30, 1000.0), (0.40, 0.20, 800.0)):
        s = secao(h=h, b=b)
        M_Rd_xx = momento_resistente_normal(s, N, plano="xx").M_Rd_normal
        M_Rd_yy = momento_resistente_normal(s, N, plano="yy").M_Rd_normal
        M_min_xx = N * (0.015 + 0.03 * h)
        M_min_yy = N * (0.015 + 0.03 * b)
        fechada = indice_de_inclusao_da_envoltoria_minima(
            M_min_xx, M_min_yy, M_Rd_xx, M_Rd_yy)
        maximo = max(
            interacao_flexao_obliqua(M_x, M_y, M_Rd_xx, M_Rd_yy, 1.0)
            for M_x, M_y in envoltoria_minima_1a_ordem(M_min_xx, M_min_yy,
                                                       numero_de_pontos=20001))
        assert fechada == pytest.approx(maximo, rel=1e-6)


def test_mutacao_da_raiz_quebra_o_indice_de_inclusao():
    """REQ-PILARETE-13(12): sem a raiz o valor cai de 0,5307 para 0,2817.

    Erro do lado INSEGURO e INVISÍVEL à checagem dimensional — as duas
    leituras são adimensionais. Este teste existe para quebrar se alguém
    remover a raiz.
    """
    s = secao()
    M_Rd = momento_resistente_normal(s, 1000.0, plano="xx").M_Rd_normal
    correto = indice_de_inclusao_da_envoltoria_minima(24.0, 24.0, M_Rd, M_Rd)
    sem_raiz = (24.0 / M_Rd) ** 2 + (24.0 / M_Rd) ** 2
    assert correto == pytest.approx(0.5307, abs=1e-4)
    assert sem_raiz == pytest.approx(0.2817, abs=1e-4)
    assert correto != pytest.approx(sem_raiz)


def test_mutacao_do_expoente_quebra_testes_DIFERENTES():
    """REQ-PILARETE-13(13): o 2 da elipse e o alpha da interação são objetos distintos.

    O expoente 2 pertence à Figura 11.3 (lado SOLICITANTE); o
    alpha_interacao pertence a 17.2.5 (lado RESISTENTE). Trocar um pelo outro
    — ou por 1,5, o alpha de 17.3.1, que está na MESMA página 125 — muda
    números diferentes, e é isso que este teste fixa.
    """
    s = secao(h=0.40, b=0.20)
    M_Rd_xx = momento_resistente_normal(s, 800.0, plano="xx").M_Rd_normal
    M_Rd_yy = momento_resistente_normal(s, 800.0, plano="yy").M_Rd_normal
    inclusao = indice_de_inclusao_da_envoltoria_minima(21.6, 16.8, M_Rd_xx,
                                                       M_Rd_yy)
    com_expoente_1_2 = ((21.6 / M_Rd_xx) ** 1.2 + (16.8 / M_Rd_yy) ** 1.2) ** (
        1.0 / 1.2)
    com_expoente_1_5 = ((21.6 / M_Rd_xx) ** 1.5 + (16.8 / M_Rd_yy) ** 1.5) ** (
        1.0 / 1.5)
    assert inclusao == pytest.approx(0.5114, abs=1e-3)
    assert inclusao != pytest.approx(com_expoente_1_2, abs=1e-4)
    assert inclusao != pytest.approx(com_expoente_1_5, abs=1e-4)
    interacao = interacao_flexao_obliqua(21.6, 16.8, M_Rd_xx, M_Rd_yy,
                                         ALPHA_INTERACAO_VEREDITO)
    assert interacao != pytest.approx(inclusao)


# --- REQ-PILARETE-13(11): seção NÃO quadrada, cruzamento h <-> b -----------

def test_secao_20x40_com_os_numeros_do_sanity_check():
    """20×40 cm, N_d = 800 kN: M_Rd,xx = 91,41 e M_Rd,yy = 37,05 kN·m.

    E o índice de inclusão vale 0,5114; trocando h por b nos semieixos ele
    iria a 0,6113. EM SEÇÃO QUADRADA ESSA TROCA É INVISÍVEL — um conjunto de
    testes só com 30×30 não prova nada sobre o cruzamento de eixos.
    """
    s = secao(h=0.40, b=0.20)
    M_Rd_xx = momento_resistente_normal(s, 800.0, plano="xx").M_Rd_normal
    M_Rd_yy = momento_resistente_normal(s, 800.0, plano="yy").M_Rd_normal
    assert M_Rd_xx == pytest.approx(91.41, abs=0.02)
    assert M_Rd_yy == pytest.approx(37.05, abs=0.02)
    certo = indice_de_inclusao_da_envoltoria_minima(21.6, 16.8, M_Rd_xx,
                                                    M_Rd_yy)
    trocado = indice_de_inclusao_da_envoltoria_minima(16.8, 21.6, M_Rd_xx,
                                                      M_Rd_yy)
    assert certo == pytest.approx(0.5114, abs=1e-3)
    assert trocado == pytest.approx(0.6113, abs=1e-3)


# --- Integração fechada x varredura por faixas -----------------------------

def test_forma_fechada_e_integracao_por_faixas_coincidem():
    """DOIS caminhos sobre a mesma derivação: algébrico e numérico.

    A forma fechada trata o patamar de eps_c2 a eps_cu como um retângulo
    separado; a varredura por faixas chama sigma_c ponto a ponto e exercita o
    patamar do diagrama. Testam coisas diferentes e têm de dar o mesmo número.
    """
    s = secao()
    resultado = momento_resistente_normal(s, 1000.0, plano="xx")
    N_faixas, M_faixas, _ = momento_resistente_por_faixas(
        s, resultado.x_linha_neutra, plano="xx")
    assert M_faixas == pytest.approx(resultado.M_Rd_normal, rel=1e-6)
    assert N_faixas == pytest.approx(1000.0, rel=1e-6)


# --- REQ-PILARETE-15: as duas verificações, o canto e a simetria -----------

def test_veredito_exige_A_e_B_simultaneamente():
    """(6) do requisito: aprovar com uma só é defeito com veto do a6."""
    s = secao(h=0.40, b=0.20)
    resultado = verificar_elu_solicitacoes_normais(
        s, N_Sd=800.0, M_Sd_x=10.0, M_Sd_y=5.0, M_1d_min_xx=21.6,
        M_1d_min_yy=16.8)
    assert resultado.atendido == (
        resultado.indice_A_par_solicitante <= 1.0
        and resultado.indice_B_envoltoria_minima <= 1.0)
    assert resultado.atendido is True


def test_reprovacao_pela_envoltoria_minima_mesmo_com_par_real_folgado():
    """B reprova onde A aprova: nenhuma das duas implica a outra.

    Caso construído com M_Sd real pequeno e N_Sd alto: o par solicitante passa
    folgado e a ELIPSE MÍNIMA de 11.3.3.4.3 não cabe na envoltória resistente.
    """
    s = secao()
    N_Sd = 1550.0
    resultado = verificar_elu_solicitacoes_normais(
        s, N_Sd=N_Sd, M_Sd_x=1.0, M_Sd_y=1.0,
        M_1d_min_xx=N_Sd * 0.024, M_1d_min_yy=N_Sd * 0.024)
    assert resultado.indice_A_par_solicitante <= 1.0
    assert resultado.indice_B_envoltoria_minima > 1.0
    assert resultado.atendido is False


def test_atalho_do_canto_so_aprova_e_e_mais_severo_que_a_norma():
    """(7) do requisito: o canto pode APROVAR, jamais reprovar.

    Ele é 41 % mais severo que o critério da Figura 11.3 (48,00 contra
    33,94 kN·m de M_R exigido no sanity check). Aqui exibe-se um caso em que o
    canto REPROVA (> 1) e as verificações A e B APROVAM — e o veredito segue
    A e B, como manda o requisito. O caso tem M_Sd,x grande e M_Sd,y pequeno,
    porque é aí que o CANTO (que soma os dois máximos SIMULTANEAMENTE) se
    afasta mais da elipse que a Norma escreve.
    """
    s = secao()
    resultado = verificar_elu_solicitacoes_normais(
        s, N_Sd=1000.0, M_Sd_x=45.0, M_Sd_y=5.0, M_1d_min_xx=24.0,
        M_1d_min_yy=24.0)
    assert resultado.indice_canto > 1.0
    assert resultado.aprovado_por_atalho_do_canto is False
    assert resultado.indice_A_par_solicitante <= 1.0
    assert resultado.indice_B_envoltoria_minima <= 1.0
    assert resultado.atendido is True


def test_alpha_1_2_e_informativo_e_nao_decide_o_veredito():
    """(9) do requisito: 17.2.5 autoriza 1,2, mas quem decide é 1,0."""
    s = secao()
    resultado = verificar_elu_solicitacoes_normais(
        s, N_Sd=1000.0, M_Sd_x=24.0, M_Sd_y=24.0, M_1d_min_xx=24.0,
        M_1d_min_yy=24.0)
    assert resultado.alpha_interacao_usado == pytest.approx(1.0)
    assert (resultado.indice_A_com_alpha_1_2_informativo
            < resultado.indice_A_par_solicitante)


def test_arranjo_assimetrico_recusa_em_vez_de_assumir_simetria():
    """(8) do requisito: é PROIBIDO ASSUMIR a simetria — o código VERIFICA."""
    area = area_barra(16.0)
    barras = (
        BarraLongitudinal(pos_h=D_LINHA, pos_b=D_LINHA, area=area),
        BarraLongitudinal(pos_h=D_LINHA, pos_b=0.30 - D_LINHA, area=area),
        BarraLongitudinal(pos_h=0.30 - D_LINHA, pos_b=D_LINHA, area=area),
    )
    assimetrica = SecaoRetangular(h_secao=0.30, b_secao=0.30, barras=barras,
                                  concreto=Concreto(fck=25.0),
                                  aco=Aco(fyk=500.0))
    assert assimetrica.arranjo_simetrico() is False
    with pytest.raises(RecusaForaDeDominio) as erro:
        verificar_elu_solicitacoes_normais(
            assimetrica, N_Sd=800.0, M_Sd_x=10.0, M_Sd_y=10.0,
            M_1d_min_xx=20.0, M_1d_min_yy=20.0)
    assert "simétrico" in erro.value.mensagem


def test_nome_do_veredito_de_17_2_nao_diz_aprovado():
    """O nome é EXATO e nunca "pilarete OK"."""
    s = secao()
    resultado = verificar_elu_solicitacoes_normais(
        s, N_Sd=1000.0, M_Sd_x=24.0, M_Sd_y=24.0, M_1d_min_xx=24.0,
        M_1d_min_yy=24.0)
    nome = resultado.nome_do_veredito
    assert nome.startswith("ELU de solicitações NORMAIS (NBR 6118:2023, 17.2.1)")
    assert "APROVADO" not in nome and "OK" not in nome


# --- Simetria do problema (teste pedido pelo despacho) ---------------------

def test_girar_a_secao_90_graus_troca_xx_por_yy_e_nada_mais():
    """SIMETRIA: girar o problema 90° troca x por y, e só.

    A seção 20×40 girada vira 40×20 com as coordenadas das barras trocadas; o
    M_Rd,xx de uma tem de ser o M_Rd,yy da outra, com igualdade EXATA (não é
    aproximação numérica: é a mesma varredura com os papéis invertidos).
    """
    direta = secao(h=0.40, b=0.20)
    girada = secao(h=0.20, b=0.40)
    assert (momento_resistente_normal(direta, 800.0, plano="xx").M_Rd_normal
            == pytest.approx(
                momento_resistente_normal(girada, 800.0, plano="yy")
                .M_Rd_normal, rel=1e-12))
    assert (momento_resistente_normal(direta, 800.0, plano="yy").M_Rd_normal
            == pytest.approx(
                momento_resistente_normal(girada, 800.0, plano="xx")
                .M_Rd_normal, rel=1e-12))


def test_equilibrio_da_secao_no_ponto_de_projeto():
    """EQUILÍBRIO: no x* encontrado, N_Rd(x*) == N_Sd e o M devolvido é o do x*.

    É o teste de equilíbrio que o despacho pede, na forma que faz sentido para
    uma seção: a resultante das tensões integradas iguala a normal aplicada, e
    o momento é o das MESMAS tensões em torno do centroide da seção bruta.
    """
    s = secao()
    resultado = momento_resistente_normal(s, 1000.0, plano="xx")
    camadas = ((D_LINHA, 2 * area_barra(16.0)),
               (0.30 - D_LINHA, 2 * area_barra(16.0)))
    N, M, _ = esforcos_resistentes_em_x(
        resultado.x_linha_neutra, altura=0.30, largura=0.30, camadas=camadas,
        concreto=s.concreto, aco=s.aco)
    assert N == pytest.approx(1000.0, abs=1e-6)
    assert M == pytest.approx(resultado.M_Rd_normal, rel=1e-12)
    assert resultado.residuo_de_N < 1e-6


def test_dominio_e_nomeado_para_o_memorial():
    """O DOMÍNIO da Figura 17.1 é impresso; é só para isso que eps_yd serve."""
    s = secao()
    assert "domínio" in momento_resistente_normal(s, 100.0, plano="xx").dominio
    assert momento_resistente_normal(s, 1e-9, plano="xx").polo in ("A", "B")
    assert momento_resistente_normal(s, 1690.0, plano="xx").polo == "C"


def test_pi_nao_entra_no_criterio(): # noqa: D401
    """Guarda de sanidade: nenhum dos índices depende de math.pi.

    Ref.: sem item normativo — é teste de teste, e existe porque a primeira
    versão do croqui da elipse usava ângulos: se alguém trocar a forma fechada
    pela varredura angular sem normalizar, o índice muda com o número de
    pontos amostrados.
    """
    pontos_grosseiros = envoltoria_minima_1a_ordem(24.0, 24.0, 361)
    pontos_finos = envoltoria_minima_1a_ordem(24.0, 24.0, 3601)
    for pontos in (pontos_grosseiros, pontos_finos):
        assert max(math.hypot(x / 24.0, y / 24.0)
                   for x, y in pontos) == pytest.approx(1.0)
