"""Pilarete — guarda de 14.4.1 e ELU de FORÇA CORTANTE (§17.4, Modelos I e II).

Cobre REQ-PILARETE-16 (as duas faixas), -17 (a guarda de elemento linear),
-18 (a verificação de cortante) e os quinze testes de propriedade de
REQ-PILARETE-19, mais a fixture de integração do BASTOS.

O QUE TEM CONTRA-PROVA EXTERNA, e só isto: as EXPRESSÕES de V_Rd2 (Modelo I),
A_sw, V_Sd,mín e a FORMA do V_Rd2 do Modelo II, pelo exemplo da viga alavanca
de BASTOS (Sapatas.pdf, FONTE SECUNDÁRIA, material didático — NÃO é texto
normativo, e NÃO é pilar). SEM contra-prova externa nenhuma: (i) a majoração
V_c = V_c0(1 + M_0/M_Sd,máx) da flexo-compressão; (ii) o Modelo II com theta
arbitrado; (iii) a exceção de 17.4.1.1.2-c) para pilares. Essas três são
verificadas aqui só por propriedade interna, e o a7 NÃO pode declarar
confiança ALTA nelas com base nisto.

GEOMETRIAS, e cada uma existe por um motivo (as mesmas de
``tools/checar_dimensoes.py``, seção 8):

    A) 30×30, ell = 1,00 m — FAIXA A (razão 3,333) e pilar curto (23,1 < 35);
    B) 30×30, ell = 0,80 m — pilar curto (18,5 < 35) e FAIXA B (2,667): prova
       que a faixa B não é hipotética;
    C) 25×40, ell = 1,25 m — a única classe NÃO QUADRADA que satisfaz as duas
       fronteiras (3,125 >= 3 e 34,64 < 35). Existe porque em seção quadrada
       W_1x == W_1y e a decisão da fibra fica INVISÍVEL.
"""
import math

import pytest

from calc_core.estrutural.dominio import RecusaForaDeDominio
from calc_core.estrutural.pilarete import cortante as ct
from calc_core.estrutural.pilarete.classificacao import (
    FAIXA_A_ELEMENTO_LINEAR,
    FAIXA_B_FORA_DE_14_4_1,
    classificar_faixa,
    frases_obrigatorias_da_faixa_B,
    razao_elemento_linear,
    recusar_cortante_na_faixa_B,
)
from calc_core.sapata_isolada.materiais import Aco, Concreto

C25 = Concreto(fck=25.0, gamma_c=1.4)
CA50 = Aco(fyk=500.0, gamma_s=1.15)
CA60 = Aco(fyk=600.0, gamma_s=1.15)

# Geometria A do sanity check do a2: b_w = 30 cm, d = 25,7 cm (h − 4,3 cm).
B_W_A = 0.30
D_A = 0.257
A_SW_POR_S = 3.1416e-4
"""2 ramos phi 5,0 mm c/12,5 cm = 3,1416 cm²/m, em m²/m."""


def V_Rd2_modelo_I(b_w=B_W_A, d=D_A, concreto=C25):
    return ct.V_Rd2(modelo_de_calculo=ct.MODELO_I, f_ck_MPa=concreto.fck,
                    f_cd_MPa=concreto.fcd, b_w_no_plano_do_cortante=b_w,
                    d_util_no_plano_do_cortante=d, alpha_estribo_graus=90.0,
                    theta_biela_graus=None)


def V_Rd2_modelo_II(theta, b_w=B_W_A, d=D_A, concreto=C25):
    return ct.V_Rd2(modelo_de_calculo=ct.MODELO_II, f_ck_MPa=concreto.fck,
                    f_cd_MPa=concreto.fcd, b_w_no_plano_do_cortante=b_w,
                    d_util_no_plano_do_cortante=d, alpha_estribo_graus=90.0,
                    theta_biela_graus=theta)


# --- REQ-PILARETE-17 e -19(6)(7): a guarda de 14.4.1 -----------------------

def test_razao_de_14_4_1_usa_ell_e_nunca_ell_e():
    """MUTAÇÃO de REQ-PILARETE-19(6): trocar `ell` por `ell_e` tem de quebrar.

    Geometria B (30×30, ell = 0,80 m): razão 2,667 -> FAIXA B. Com
    ell_e = 2·ell daria 5,333 -> FAIXA A, aplicando §17.4 fora de domínio a um
    pilarete de 80 cm. Erro do lado INSEGURO por CITAÇÃO e invisível à
    checagem dimensional (a razão é adimensional nas duas leituras).
    """
    razao = razao_elemento_linear(ell=0.80, h_secao=0.30, b_secao=0.30)
    assert razao == pytest.approx(2.6667, abs=1e-4)
    assert razao != pytest.approx(2.0 * 0.80 / 0.30)
    assert classificar_faixa(ell=0.80, h_secao=0.30,
                             b_secao=0.30).faixa == FAIXA_B_FORA_DE_14_4_1


def test_fronteira_da_faixa_em_cima_do_3_000():
    """REQ-PILARETE-19(7): razão 3,000 SEGUE; 2,999 RECUSA.

    A leitura adotada de "supera em pelo menos três vezes" é a NÃO ESTRITA
    (>= 3,0), decidida pelo a2 e declarada — a diferença tem medida nula e o
    memorial imprime a razão obtida.
    """
    na_fronteira = classificar_faixa(ell=0.90, h_secao=0.30, b_secao=0.30)
    assert na_fronteira.razao_14_4_1 == pytest.approx(3.0)
    assert na_fronteira.faixa == FAIXA_A_ELEMENTO_LINEAR
    assert recusar_cortante_na_faixa_B(na_fronteira) is None

    abaixo = classificar_faixa(ell=0.8997, h_secao=0.30, b_secao=0.30)
    assert abaixo.razao_14_4_1 < 3.0
    with pytest.raises(RecusaForaDeDominio):
        recusar_cortante_na_faixa_B(abaixo)


def test_faixa_B_recusa_de_verdade_e_com_as_duas_frases():
    """REQ-PILARETE-17(3): LEVANTA EXCEÇÃO — não devolve None, zero ou "n/a"."""
    geometria_B = classificar_faixa(ell=0.80, h_secao=0.30, b_secao=0.30)
    with pytest.raises(RecusaForaDeDominio) as erro:
        ct.verificar(
            classificacao=geometria_B, concreto=C25, aco_do_estribo=CA50,
            h_secao=0.30, b_secao=0.30, d_linha_no_plano_de_h=0.043,
            d_linha_no_plano_de_b=0.043, H_x=40.0, H_y=0.0, N_d=1000.0,
            M_Sd_max_x=24.0, M_Sd_max_y=24.0, modelo_de_calculo=ct.MODELO_I,
            theta_biela_graus=None, alpha_estribo_graus=90.0,
            A_sw_por_s=A_SW_POR_S, N_gamma_f_1=714.0,
            normal_de_compressao_em_todas_as_combinacoes=True)
    mensagem = erro.value.mensagem
    assert "14.4.1" in mensagem and "2.6667" in mensagem
    primeira, segunda = frases_obrigatorias_da_faixa_B(geometria_B)
    assert "não satisfaz" in primeira.lower()
    assert "NÃO FOI VERIFICADO" in segunda
    assert "bielas e tirantes" in segunda


def test_faixa_e_campo_proprio_e_nao_string_interpretada():
    """REQ-PILARETE-16-(i): consumidor programático distingue sem parsear."""
    resultado = classificar_faixa(ell=1.25, h_secao=0.40, b_secao=0.25)
    assert resultado.faixa in (FAIXA_A_ELEMENTO_LINEAR, FAIXA_B_FORA_DE_14_4_1)
    assert resultado.e_elemento_linear is True
    assert resultado.razao_14_4_1 == pytest.approx(3.125)
    assert resultado.ell_necessario_para_faixa_A == pytest.approx(1.20)


# --- REQ-PILARETE-19(1)(2)(8)(10)(11): Modelos I e II ----------------------

def test_V_Rd2_do_modelo_I_contra_a_tabela_do_bastos():
    """REQ-PILARETE-19(a): 0,35487·b_w·d contra os 0,35·b_w·d da Tabela A-4.

    FONTE SECUNDÁRIA (BASTOS, material didático), e o autor ARREDONDA. A
    conferência é da EXPRESSÃO, com folga declarada de 2 %.
    """
    # O coeficiente da Tabela A-4 está em kN/cm²; aqui V_Rd2 sai em kN com
    # b_w e d em METROS, logo a conversão é 1 kN/cm² = 1e4 kN/m².
    coeficiente = V_Rd2_modelo_I(b_w=1.0, d=1.0, concreto=Concreto(fck=20.0))
    assert coeficiente / 1e4 == pytest.approx(0.35487, abs=1e-4)
    assert coeficiente / 1e4 == pytest.approx(0.35, rel=0.02)


def test_fronteira_dos_modelos_em_45_graus():
    """REQ-PILARETE-19(1): V_Rd2(II) == V_Rd2(I) e V_sw(II) == V_sw(I).

    Em theta = 45° e alpha_estribo = 90°: sen² = 0,5 e cotg 45° = 1, logo
    0,54·0,5·1 = 0,27. Medido pelo a2: diferença 0,0 kN.
    """
    assert V_Rd2_modelo_II(45.0) == pytest.approx(V_Rd2_modelo_I(), rel=1e-12)
    V_sw_I = ct.V_sw(modelo_de_calculo=ct.MODELO_I, A_sw_por_s=A_SW_POR_S,
                     d_util_no_plano_do_cortante=D_A,
                     f_ywd_MPa=ct.f_ywd(CA50),
                     alpha_estribo_graus=90.0, theta_biela_graus=None)
    V_sw_II = ct.V_sw(modelo_de_calculo=ct.MODELO_II, A_sw_por_s=A_SW_POR_S,
                      d_util_no_plano_do_cortante=D_A,
                      f_ywd_MPa=ct.f_ywd(CA50),
                      alpha_estribo_graus=90.0, theta_biela_graus=45.0)
    assert V_sw_II == pytest.approx(V_sw_I, rel=1e-12)
    assert V_sw_I == pytest.approx(31.59, abs=0.01)


def test_mutacao_de_sen_ao_quadrado_quebra_a_fronteira():
    """REQ-PILARETE-19(8): sen²(theta) trocado por sen(theta) dá +41 % em 45°.

    O coeficiente iria de 0,27 a 0,382 — lado INSEGURO e invisível ao pint.
    """
    mutante = (0.54 * ct.alpha_v2(25.0) * C25.fcd * 1000.0 * B_W_A * D_A
               * math.sin(math.radians(45.0)) * (0.0 + 1.0))
    assert mutante == pytest.approx(V_Rd2_modelo_I() * 0.382 / 0.27, rel=1e-3)
    assert mutante != pytest.approx(V_Rd2_modelo_I(), rel=1e-3)


def test_fisica_de_theta_menor_aumenta_Vsw_e_diminui_VRd2():
    """REQ-PILARETE-19(11): monotonia em [30°, 45°].

    Medido pelo a2: 30° dá V_Rd2 = 289,7 kN e V_sw = 54,72 kN contra 334,6 e
    31,59 kN em 45°.
    """
    assert V_Rd2_modelo_II(30.0) == pytest.approx(289.7, abs=0.1)
    assert V_Rd2_modelo_II(45.0) == pytest.approx(334.6, abs=0.1)
    anterior_rd2 = 0.0
    anterior_sw = float("inf")
    for theta in (30.0, 35.0, 40.0, 45.0):
        rd2 = V_Rd2_modelo_II(theta)
        sw = ct.V_sw(modelo_de_calculo=ct.MODELO_II, A_sw_por_s=A_SW_POR_S,
                     d_util_no_plano_do_cortante=D_A,
                     f_ywd_MPa=ct.f_ywd(CA50),
                     alpha_estribo_graus=90.0, theta_biela_graus=theta)
        assert rd2 > anterior_rd2
        assert sw < anterior_sw
        anterior_rd2, anterior_sw = rd2, sw
    assert anterior_sw == pytest.approx(31.59, abs=0.01)


def test_V_c1_degenera_nos_extremos_e_nao_coincide_com_V_c0_no_meio():
    """REQ-PILARETE-19(10) e (2): a NÃO-fronteira que uma leitura apressada erra.

    V_Sd = V_c0 -> V_c1 = V_c0; V_Sd = V_Rd2 -> V_c1 = 0, exatamente. E, com
    V_Sd = 120 kN, V_c1 = 46,25 contra V_c0 = 59,33 kN: os dois modelos
    COINCIDEM em V_Rd2 e em V_sw a 45°, mas NÃO em V_Rd3. Um teste que exija
    V_Rd3(II) == V_Rd3(I) está ERRADO e quebra implementação correta.
    """
    V_c0 = ct.V_c0(concreto=C25, b_w_no_plano_do_cortante=B_W_A,
                   d_util_no_plano_do_cortante=D_A)
    assert V_c0 == pytest.approx(59.33, abs=0.01)
    V_Rd2_45 = V_Rd2_modelo_II(45.0)
    assert ct.V_c1(V_Sd=V_c0, V_c0_valor=V_c0,
                   V_Rd2_do_modelo_II=V_Rd2_45) == pytest.approx(V_c0)
    assert ct.V_c1(V_Sd=V_Rd2_45, V_c0_valor=V_c0,
                   V_Rd2_do_modelo_II=V_Rd2_45) == pytest.approx(0.0, abs=1e-9)
    assert ct.V_c1(V_Sd=120.0, V_c0_valor=V_c0,
                   V_Rd2_do_modelo_II=V_Rd2_45) == pytest.approx(46.25,
                                                                 abs=0.01)


def test_V_c1_recusa_acima_de_V_Rd2_em_vez_de_extrapolar():
    """É PROIBIDO devolver V_c1 negativo ou truncá-lo em zero em silêncio."""
    V_c0 = ct.V_c0(concreto=C25, b_w_no_plano_do_cortante=B_W_A,
                   d_util_no_plano_do_cortante=D_A)
    with pytest.raises(RecusaForaDeDominio):
        ct.V_c1(V_Sd=400.0, V_c0_valor=V_c0,
                V_Rd2_do_modelo_II=V_Rd2_modelo_II(45.0))


# --- REQ-PILARETE-19(15): o teto de f_ywd ----------------------------------

def test_teto_de_f_ywd_governa_CA60_e_nao_governa_CA50():
    """REQ-PILARETE-19(15): 435 MPa em CA-60; 434,8 MPa em CA-50 (sem teto).

    A mutação que remove o teto tem de quebrar o caso CA-60 e NÃO pode quebrar
    nenhum CA-50 — é assim que se prova que o teste testa o que diz testar.
    """
    assert ct.f_ywd(CA60) == pytest.approx(435.0)
    assert CA60.fyd == pytest.approx(521.74, abs=0.01)
    assert ct.f_ywd(CA50) == pytest.approx(CA50.fyd)
    assert ct.f_ywd(CA50) == pytest.approx(434.78, abs=0.01)


# --- REQ-PILARETE-18(2)(3)(13): plano, e a recusa do cortante BIAXIAL ------

def test_recusa_de_cortante_biaxial_em_cima_do_zero():
    """REQ-PILARETE-19(13): H_y = 0,001 kN RECUSA; H_y = 0,0 segue.

    §17.4 é escrito para UM V_Sd em b_w·d e a Norma NÃO dá regra de interação
    entre duas cortantes — o contraste com 17.2.5, que FORNECE a interação
    para os momentos oblíquos, mostra que a omissão não é descuido. É PROIBIDO
    compor sqrt(V_x² + V_y²), somar linearmente ou verificar por direção
    isolada. Sem tolerância numérica.
    """
    with pytest.raises(RecusaForaDeDominio) as erro:
        ct.plano_de_verificacao(H_x=10.0, H_y=0.001, h_secao=0.30,
                                b_secao=0.30, d_linha_no_plano_de_h=0.043,
                                d_linha_no_plano_de_b=0.043)
    assert "17.4.2.1" in erro.value.mensagem and "17.2.5" in erro.value.mensagem
    plano = ct.plano_de_verificacao(H_x=10.0, H_y=0.0, h_secao=0.30,
                                    b_secao=0.30, d_linha_no_plano_de_h=0.043,
                                    d_linha_no_plano_de_b=0.043)
    assert plano.V_Sd == pytest.approx(10.0)


def test_mutacao_de_plano_quebra_em_secao_nao_quadrada():
    """REQ-PILARETE-19(9): trocar b_w por d é invisível em 30×30.

    Geometria C (25×40): com V_Sd no plano de h, b_w = 0,25 m e d = 0,357 m;
    no plano de b, b_w = 0,40 m e d = 0,207 m. Os dois V_Rd2 diferem.
    """
    plano_h = ct.plano_de_verificacao(
        H_x=50.0, H_y=0.0, h_secao=0.40, b_secao=0.25,
        d_linha_no_plano_de_h=0.043, d_linha_no_plano_de_b=0.043)
    plano_b = ct.plano_de_verificacao(
        H_x=0.0, H_y=50.0, h_secao=0.40, b_secao=0.25,
        d_linha_no_plano_de_h=0.043, d_linha_no_plano_de_b=0.043)
    assert plano_h.plano == ct.PLANO_DE_H
    assert plano_h.b_w_no_plano_do_cortante == pytest.approx(0.25)
    assert plano_h.d_util_no_plano_do_cortante == pytest.approx(0.357)
    assert plano_b.plano == ct.PLANO_DE_B
    assert plano_b.b_w_no_plano_do_cortante == pytest.approx(0.40)
    assert plano_b.d_util_no_plano_do_cortante == pytest.approx(0.207)
    assert V_Rd2_modelo_I(b_w=0.25, d=0.357) != pytest.approx(
        V_Rd2_modelo_I(b_w=0.40, d=0.207), rel=1e-3)


# --- REQ-PILARETE-18(4)(5) e -19(3)(4)(5): M_0, a majoração e o teto -------

def test_M_0_e_a_fibra_governante_em_secao_quadrada_e_invisivel():
    """REQ-PILARETE-19(5), primeira metade: em 30×30 a diferença é ZERO."""
    fibra_x, fibra_y, governante = ct.M_0_e_fibra_governante(
        N_gamma_f_1=714.0, h_secao=0.30, b_secao=0.30, M_Sd_max_x=24.0,
        M_Sd_max_y=24.0)
    assert fibra_x.W_1 == pytest.approx(fibra_y.W_1)
    assert fibra_x.M_0 == pytest.approx(35.7, abs=0.01)
    assert governante.razao == pytest.approx(fibra_x.razao)


def test_discriminante_da_fibra_na_geometria_C_nao_quadrada():
    """REQ-PILARETE-19(5): 25×40, N_(gf=1) = 857 kN, M_Sd = 90 e 70 kN·m.

    V_c = 103,7 kN pela fibra conservadora contra 112,3 kN pela outra (8,3 %).
    A escolha é a MENOR razão — lado conservador, e emparelhada POR PLANO.
    """
    fibra_x, fibra_y, governante = ct.M_0_e_fibra_governante(
        N_gamma_f_1=857.0, h_secao=0.40, b_secao=0.25, M_Sd_max_x=90.0,
        M_Sd_max_y=70.0)
    assert fibra_x.M_0 == pytest.approx(57.13, abs=0.01)
    assert fibra_y.M_0 == pytest.approx(35.71, abs=0.01)
    assert fibra_x.razao == pytest.approx(0.6348, abs=1e-4)
    assert fibra_y.razao == pytest.approx(0.5102, abs=1e-4)
    assert governante is fibra_y

    V_c0_C = ct.V_c0(concreto=C25, b_w_no_plano_do_cortante=0.25,
                     d_util_no_plano_do_cortante=0.357)
    conservador = min(V_c0_C * (1.0 + governante.razao), 2.0 * V_c0_C)
    otimista = min(V_c0_C * (1.0 + fibra_x.razao), 2.0 * V_c0_C)
    assert conservador == pytest.approx(103.7, abs=0.1)
    assert otimista == pytest.approx(112.3, abs=0.1)
    assert otimista - conservador == pytest.approx(8.56, abs=0.02)


def test_M_Sd_max_nulo_recusa_em_vez_de_encostar_no_teto():
    """A divisão não pode explodir: o software RECUSA."""
    with pytest.raises(RecusaForaDeDominio):
        ct.M_0_e_fibra_governante(N_gamma_f_1=714.0, h_secao=0.30,
                                  b_secao=0.30, M_Sd_max_x=0.0,
                                  M_Sd_max_y=24.0)


def _verificar_geometria_A(**kwargs):
    """Chamada padrão da geometria A (FAIXA A), com sobrescritas por kwargs."""
    padrao = dict(
        classificacao=classificar_faixa(ell=1.00, h_secao=0.30, b_secao=0.30),
        concreto=C25, aco_do_estribo=CA50, h_secao=0.30, b_secao=0.30,
        d_linha_no_plano_de_h=0.043, d_linha_no_plano_de_b=0.043,
        H_x=120.0, H_y=0.0, N_d=1000.0, M_Sd_max_x=24.0, M_Sd_max_y=24.0,
        modelo_de_calculo=ct.MODELO_I, theta_biela_graus=None,
        alpha_estribo_graus=90.0, A_sw_por_s=A_SW_POR_S, N_gamma_f_1=714.0,
        normal_de_compressao_em_todas_as_combinacoes=True)
    padrao.update(kwargs)
    return ct.verificar(**padrao)


def test_caso_A1_mascara_a_decisao_de_M_0_e_o_caso_A2_discrimina():
    """REQ-PILARETE-19(4), OBRIGATÓRIO: A1 estoura o teto, A2 discrimina.

    A1 (M_Sd,máx = 24 kN·m): as DUAS leituras de M_0 estouram o teto de 2·V_c0
    e dão 118,7 kN — o caso MASCARA a decisão V20(2). Só A2
    (M_Sd,máx = 60 kN·m) discrimina: 94,63 kN com N a gamma_f = 1,0 contra
    108,77 kN com N_d majorado (+14,9 %, lado INSEGURO). Um conjunto de testes
    só com A1 não prova nada sobre M_0.
    """
    A1 = _verificar_geometria_A(M_Sd_max_x=24.0, M_Sd_max_y=24.0)
    assert A1.V_c_valor == pytest.approx(118.7, abs=0.1)
    assert A1.teto_2Vc_governou is True
    assert A1.V_c_valor == pytest.approx(2.0 * A1.V_c0_valor)

    A2 = _verificar_geometria_A(M_Sd_max_x=60.0, M_Sd_max_y=60.0)
    assert A2.V_c_valor == pytest.approx(94.63, abs=0.05)
    assert A2.teto_2Vc_governou is False
    leitura_insegura = min(A2.V_c0_valor * (1.0 + 1000.0 * 0.05 / 60.0),
                           2.0 * A2.V_c0_valor)
    assert leitura_insegura == pytest.approx(108.77, abs=0.05)
    assert A2.V_c_valor < leitura_insegura


def test_teto_de_2_Vc_trava_quando_M_Sd_max_tende_a_zero():
    """REQ-PILARETE-19(3): mutação que remova o teto TEM de quebrar."""
    quase_zero = _verificar_geometria_A(M_Sd_max_x=1e-6, M_Sd_max_y=1e-6)
    assert quase_zero.V_c_valor == pytest.approx(
        2.0 * quase_zero.V_c0_valor, rel=1e-12)
    assert quase_zero.teto_2Vc_governou is True


def test_sem_N_gamma_f_1_declarado_nao_ha_majoracao():
    """REQ-PILARETE-18(m): sem o campo PRÓPRIO, V_c = V_c0. Sem inventar gamma_f."""
    sem = _verificar_geometria_A(N_gamma_f_1=None)
    assert sem.majoracao_aplicada is False
    assert sem.V_c_valor == pytest.approx(sem.V_c0_valor)
    assert sem.fibra_governante is None


def test_estado_da_secao_governa_o_ramo_de_V_c():
    """REQ-PILARETE-18(4): três estados, três ramos. V_c = 0 se tudo tracionado."""
    tracionada = ct.classificar_estado_da_secao(
        N_d=-500.0, h_secao=0.30, b_secao=0.30, M_Sd_max_x=1.0,
        M_Sd_max_y=1.0)
    assert tracionada == ct.ESTADO_TRACIONADO_LN_FORA
    flexao = ct.classificar_estado_da_secao(
        N_d=0.0, h_secao=0.30, b_secao=0.30, M_Sd_max_x=24.0, M_Sd_max_y=24.0)
    assert flexao == ct.ESTADO_FLEXAO_SIMPLES_OU_FLEXO_TRACAO
    compressao = ct.classificar_estado_da_secao(
        N_d=1000.0, h_secao=0.30, b_secao=0.30, M_Sd_max_x=24.0,
        M_Sd_max_y=24.0)
    assert compressao == ct.ESTADO_FLEXO_COMPRESSAO

    sem_compressao = _verificar_geometria_A(N_d=-500.0, M_Sd_max_x=1.0,
                                            M_Sd_max_y=1.0)
    assert sem_compressao.estado_da_secao == ct.ESTADO_TRACIONADO_LN_FORA
    assert sem_compressao.V_c_valor == pytest.approx(0.0)


# --- REQ-PILARETE-18(7): as DUAS condições, sempre -------------------------

def test_veredito_de_cortante_exige_biela_e_trelica():
    """(7) do requisito: aprovar com uma só é defeito com veto do a6."""
    resultado = _verificar_geometria_A(M_Sd_max_x=60.0, M_Sd_max_y=60.0)
    assert resultado.V_Rd2_valor == pytest.approx(334.6, abs=0.1)
    assert resultado.V_Rd3_valor == pytest.approx(126.2, abs=0.1)
    assert resultado.condicao_biela_atendida is True
    assert resultado.condicao_trelica_atendida is True
    assert resultado.atendido is True

    reprova_na_trelica = _verificar_geometria_A(H_x=200.0, M_Sd_max_x=60.0,
                                                M_Sd_max_y=60.0)
    assert reprova_na_trelica.condicao_biela_atendida is True
    assert reprova_na_trelica.condicao_trelica_atendida is False
    assert reprova_na_trelica.atendido is False

    reprova_na_biela = _verificar_geometria_A(H_x=400.0, M_Sd_max_x=60.0,
                                              M_Sd_max_y=60.0)
    assert reprova_na_biela.condicao_biela_atendida is False
    assert reprova_na_biela.atendido is False


def test_V_Sd_acima_de_V_Rd2_no_modelo_II_reprova_sem_levantar_excecao():
    """Reprovação NÃO é recusa: o software calcula, reprova e diz por quê.

    Acima de V_Rd2 a interpolação de V_c1 (17.4.2.3-b) não existe; o resultado
    registra ``V_c1_indefinido_por_V_Sd_acima_de_V_Rd2`` em vez de inventar um
    número, e o veredito sai NÃO ATENDIDO pela condição da biela.
    """
    resultado = _verificar_geometria_A(
        H_x=400.0, modelo_de_calculo=ct.MODELO_II, theta_biela_graus=45.0,
        M_Sd_max_x=60.0, M_Sd_max_y=60.0)
    assert resultado.V_c1_valor is None
    assert resultado.V_c1_indefinido_por_V_Sd_acima_de_V_Rd2 is True
    assert resultado.condicao_biela_atendida is False
    assert resultado.atendido is False


def test_modelo_II_nao_coincide_com_modelo_I_em_V_Rd3():
    """REQ-PILARETE-19(2): a NÃO-fronteira. V_c1 <= V_c0 sempre que V_Sd > V_c0."""
    modelo_I = _verificar_geometria_A(M_Sd_max_x=60.0, M_Sd_max_y=60.0)
    modelo_II = _verificar_geometria_A(
        modelo_de_calculo=ct.MODELO_II, theta_biela_graus=45.0,
        M_Sd_max_x=60.0, M_Sd_max_y=60.0)
    assert modelo_II.V_Rd2_valor == pytest.approx(modelo_I.V_Rd2_valor,
                                                  rel=1e-12)
    assert modelo_II.V_sw_valor == pytest.approx(modelo_I.V_sw_valor,
                                                 rel=1e-12)
    assert modelo_II.V_c1_valor == pytest.approx(46.25, abs=0.01)
    assert modelo_II.V_Rd3_valor < modelo_I.V_Rd3_valor


# --- REQ-PILARETE-18(j)(k)(l) e -19(14): entradas sem default --------------

def test_modelo_nao_declarado_recusa():
    """REQ-PILARETE-19(14): sem MODELO não há cálculo. Sem default, sem "tentar os dois"."""
    with pytest.raises(RecusaForaDeDominio) as erro:
        _verificar_geometria_A(modelo_de_calculo=None)
    assert "Modelos I e II" in erro.value.mensagem


@pytest.mark.parametrize("theta", [29.9, 45.1, 0.0, 90.0])
def test_theta_fora_de_30_a_45_recusa_citando_o_item(theta):
    """17.4.2.3 fixa 30° <= theta <= 45°; fora disso RECUSA."""
    with pytest.raises(RecusaForaDeDominio) as erro:
        _verificar_geometria_A(modelo_de_calculo=ct.MODELO_II,
                               theta_biela_graus=theta)
    assert "17.4.2.3" in erro.value.mensagem


def test_theta_ausente_com_modelo_II_recusa_e_presente_com_modelo_I_tambem():
    """theta pertence ao Modelo II e SÓ a ele; no Modelo I não há escolha."""
    with pytest.raises(RecusaForaDeDominio):
        _verificar_geometria_A(modelo_de_calculo=ct.MODELO_II,
                               theta_biela_graus=None)
    with pytest.raises(RecusaForaDeDominio):
        _verificar_geometria_A(modelo_de_calculo=ct.MODELO_I,
                               theta_biela_graus=45.0)


def test_alpha_estribo_diferente_de_90_recusa_citando_o_ESCOPO():
    """A Norma admite 45° a 90°; a restrição a 90° é ESCOPO DESTE SOFTWARE.

    A mensagem tem de citar o escopo, NUNCA a Norma — o contrário seria
    atribuir à NBR 6118 uma proibição que ela não faz.
    """
    with pytest.raises(RecusaForaDeDominio) as erro:
        _verificar_geometria_A(alpha_estribo_graus=45.0)
    assert "ESCOPO" in erro.value.mensagem
    with pytest.raises(RecusaForaDeDominio):
        _verificar_geometria_A(alpha_estribo_graus=30.0)


def test_A_sw_por_s_e_de_um_estribo_concreto():
    """REQ-PILARETE-18(n): a verificação é de um estribo ADOTADO."""
    with pytest.raises(RecusaForaDeDominio):
        _verificar_geometria_A(A_sw_por_s=None)
    with pytest.raises(RecusaForaDeDominio):
        _verificar_geometria_A(A_sw_por_s=0.0)


def test_nao_existe_laco_sobre_theta_no_pacote():
    """"Encontrar aqui uma varredura de theta é VETO do a6" (REQ-PILARETE-18-k)."""
    import pathlib
    fonte = pathlib.Path(
        "calc_core/estrutural/pilarete/cortante.py").read_text(encoding="utf-8")
    for linha in fonte.splitlines():
        codigo = linha.split("#")[0]
        if codigo.strip().startswith(("for ", "while ")):
            assert "theta" not in codigo, codigo


# --- REQ-PILARETE-18(8): armadura mínima e a exceção de 17.4.1.1.2-c) ------

def test_rho_sw_min_e_a_armadura_minima_do_bastos():
    """rho_sw,mín = 0,2·f_ct,m/f_ywk; em C20/CA-50 e b_w = 35 cm dá 3,09 cm²/m.

    CONTRA-PROVA EXTERNA (BASTOS, fonte secundária): o autor escreve
    "20·f_ct,m/f_ywk·b_w" em cm²/m, que é a MESMA regra em outras unidades —
    o fator 20 = 0,2 × 100.
    """
    c20 = Concreto(fck=20.0, gamma_c=1.4)
    rho = ct.rho_sw_min(concreto=c20, f_ywk_MPa=500.0)
    assert c20.fctm == pytest.approx(2.2104, abs=1e-4)
    assert rho * 0.35 * 1e4 == pytest.approx(3.09, abs=0.01)


def test_sen_de_alpha_estribo_esta_no_DENOMINADOR_de_rho_sw():
    """Erro DORMENTE: com estribo vertical o número nem muda.

    Só estribo inclinado revela a troca (fator 1,41 a 45°). A leitura visual
    do a2 confirmou o seno NO DENOMINADOR.
    """
    vertical = ct.taxa_rho_sw_adotada(A_sw_por_s=A_SW_POR_S,
                                      b_w_no_plano_do_cortante=B_W_A,
                                      alpha_estribo_graus=90.0)
    inclinado = ct.taxa_rho_sw_adotada(A_sw_por_s=A_SW_POR_S,
                                       b_w_no_plano_do_cortante=B_W_A,
                                       alpha_estribo_graus=45.0)
    assert vertical == pytest.approx(A_SW_POR_S / B_W_A)
    assert inclinado == pytest.approx(vertical * math.sqrt(2.0))


def test_dispensa_de_17_4_1_1_2_c_exige_as_DUAS_condicoes_com_f_ctk_inf():
    """A exceção só vale com (i) e (ii) SIMULTÂNEAS, em ESTÁDIO I.

    E "f_ctk" sem sufixo é lido como f_ctk,inf (decisão V20(1)): com f_ctk,sup
    a dispensa seria 86 % mais fácil de obter, e o pilarete deixaria de ser
    armado onde a leitura conservadora manda armar.
    """
    dispensa = ct.dispensa_17_4_1_1_2_c(
        concreto=C25, N_d=1000.0, h_secao=0.30, b_secao=0.30,
        M_Sd_max_x=24.0, M_Sd_max_y=24.0, V_Sd=30.0, V_c_do_modelo_I=59.33,
        normal_de_compressao_em_todas_as_combinacoes=True)
    assert dispensa.f_ctk_inf == pytest.approx(C25.fctk_inf)
    assert dispensa.f_ctk_inf == pytest.approx(1.7955, abs=1e-3)
    assert dispensa.condicao_i_atendida is True
    assert dispensa.condicao_ii_atendida is True
    assert dispensa.dispensada is True

    reprova_por_V = ct.dispensa_17_4_1_1_2_c(
        concreto=C25, N_d=1000.0, h_secao=0.30, b_secao=0.30,
        M_Sd_max_x=24.0, M_Sd_max_y=24.0, V_Sd=120.0, V_c_do_modelo_I=59.33,
        normal_de_compressao_em_todas_as_combinacoes=True)
    assert reprova_por_V.condicao_ii_atendida is False
    assert reprova_por_V.dispensada is False

    sem_compressao_declarada = ct.dispensa_17_4_1_1_2_c(
        concreto=C25, N_d=1000.0, h_secao=0.30, b_secao=0.30,
        M_Sd_max_x=24.0, M_Sd_max_y=24.0, V_Sd=30.0, V_c_do_modelo_I=59.33,
        normal_de_compressao_em_todas_as_combinacoes=False)
    assert sem_compressao_declarada.dispensada is False


def test_declaracoes_obrigatorias_do_memorial_de_cortante():
    """REQ-PILARETE-12 (p) e (q): f_ctk,inf declarado e as duas ausências."""
    resultado = _verificar_geometria_A(M_Sd_max_x=60.0, M_Sd_max_y=60.0)
    juntas = " ".join(resultado.dispensa.declaracoes)
    assert "f_ctk,inf" in juntas
    assert "predominantemente à compressão" in juntas.lower()
    ausencias = " ".join(resultado.ausencias_deliberadas)
    assert "17.4.1.2.1" in ausencias
    assert "decalagem" in ausencias.lower()


# --- Fixture de integração do BASTOS (viga alavanca, NÃO é pilar) ----------

def test_fixture_bastos_viga_alavanca_modelo_I():
    """BASTOS, viga alavanca: V_Rd2, V_c0, A_sw e V_Sd,mín, com DUAS ressalvas.

    RESSALVA 1: é VIGA ALAVANCA, não pilar. Serve como conferência das
    EXPRESSÕES de §17.4, jamais como precedente de aplicar §17.4 a pilarete.
    RESSALVA 2: o autor arredonda 0,35487 -> 0,35, o que põe o caso a 0,1 kN
    da fronteira dos 0,67·V_Rd2 — o caso é FRÁGIL por construção e NÃO deve
    ser usado como teste de fronteira.

    C20, b_w = 35 cm, d = 70 cm, V_Sd = 574,4 kN, CA-50, estribo vertical.
    """
    c20 = Concreto(fck=20.0, gamma_c=1.4)
    b_w, d = 0.35, 0.70
    V_Sd = 1.4 * 410.3

    V_Rd2_literal = ct.V_Rd2(
        modelo_de_calculo=ct.MODELO_I, f_ck_MPa=20.0, f_cd_MPa=c20.fcd,
        b_w_no_plano_do_cortante=b_w, d_util_no_plano_do_cortante=d,
        alpha_estribo_graus=90.0, theta_biela_graus=None)
    assert V_Sd == pytest.approx(574.42, abs=0.01)
    assert V_Rd2_literal == pytest.approx(857.5, rel=0.02)   # folga declarada
    assert V_Sd < V_Rd2_literal

    V_c0 = ct.V_c0(concreto=c20, b_w_no_plano_do_cortante=b_w,
                   d_util_no_plano_do_cortante=d)
    assert V_c0 == pytest.approx(162.4, abs=0.2)

    # A_sw/s pela expressão literal, contra os 14,97 cm²/m da Tabela A-4.
    A_sw_por_s = (V_Sd - V_c0) / (0.9 * d * ct.f_ywd(CA50) * 1000.0)
    assert A_sw_por_s * 1e4 == pytest.approx(14.97, rel=0.01)

    # V_Sd,mín — o número que amarra rho_sw,mín, V_c0 e o teto de 435 MPa.
    rho_min = ct.rho_sw_min(concreto=c20, f_ywk_MPa=500.0)
    V_sw_min = rho_min * b_w * 0.9 * d * ct.f_ywd(CA50) * 1000.0
    # 0,101 kN/cm² da fonte, convertidos para kN com b_w e d em metros.
    assert (V_c0 + V_sw_min) == pytest.approx(0.101 * 1e4 * b_w * d, rel=0.01)

    # E a FORMA do Modelo II a 45°, que o autor tabula como 0,71·b_w·d·sen·cos.
    V_Rd2_II = ct.V_Rd2(
        modelo_de_calculo=ct.MODELO_II, f_ck_MPa=20.0, f_cd_MPa=c20.fcd,
        b_w_no_plano_do_cortante=1.0, d_util_no_plano_do_cortante=1.0,
        alpha_estribo_graus=90.0, theta_biela_graus=45.0)
    assert V_Rd2_II / 1e4 == pytest.approx(0.35487, abs=1e-4)
    # 0,54·alpha_v2·f_cd = 7,097 MPa = 0,70974 kN/cm², a "forma" tabulada.
    coeficiente_da_forma = 0.54 * ct.alpha_v2(20.0) * c20.fcd
    assert coeficiente_da_forma / 10.0 == pytest.approx(0.70974, abs=1e-4)
