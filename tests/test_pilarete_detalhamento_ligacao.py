"""Pilarete — detalhamento (17.3.5.3, 18.4.2, 18.4.3 × 18.3.3.2) e ligação.

Cobre REQ-PILARETE-07 (armadura longitudinal), -08 (estribos e a recusa do
CA-60), -10 (emenda por traspasse) e -11 (junta de concretagem, três casos e
duas recusas), mais o teste de composição (12) de REQ-PILARETE-19.

O ERRO DE LADO INSEGURO QUE ESTE ARQUIVO VIGIA: aplicar a frase "adotando-se o
menor dos limites especificados" (18.4.3, último parágrafo) a um PISO. Ela
resolve a sobreposição de TETOS; num piso, tomar o menor AFROUXA a exigência.
TETOS pelo MENOR, PISOS pelo MAIOR.
"""
import pytest

from calc_core.estrutural.dominio import RecusaForaDeDominio
from calc_core.estrutural.pilarete.detalhamento import (
    A_s_maxima,
    A_s_minima,
    k_phi_de_18_4_3,
    phi_t_maximo_18_3_3_2,
    phi_t_minimo_18_4_3,
    s_max_18_3_3_2,
    s_max_18_4_3,
    s_max_adicional_estribo_fino_18_4_3,
    s_t_max_18_3_3_2,
    verificar_armadura_longitudinal,
    verificar_estribos,
)
from calc_core.estrutural.pilarete.ligacao import (
    JUNTA_COM_ADERENCIA_DECLARADA,
    JUNTA_SEM_ADERENCIA_ASSEGURADA,
    MONOLITICO,
    comprimento_de_traspasse,
    exigencias_de_armadura_transversal_da_emenda,
    verificar_junta,
)
from calc_core.sapata_isolada.materiais import Aco, Concreto, area_barra

C25 = Concreto(fck=25.0, gamma_c=1.4)
CA25 = Aco(fyk=250.0, gamma_s=1.15)
CA50 = Aco(fyk=500.0, gamma_s=1.15)
CA60 = Aco(fyk=600.0, gamma_s=1.15)

QUATRO_PHI_16 = 4.0 * area_barra(16.0)
"""4 phi 16 mm = 8,04 cm², o arranjo de uma barra por vértice."""


# --- REQ-PILARETE-07: armadura longitudinal --------------------------------

def test_A_s_min_e_max_na_geometria_de_referencia():
    """30×30 (A_c = 900 cm²), CA-50, N_d = 1000 kN.

    0,15·N_d/f_yd = 3,45 cm² e 0,004·A_c = 3,60 cm² -> governa a parcela
    GEOMÉTRICA. A_s,máx = 72,0 cm².
    """
    A_c = 0.09
    minima = A_s_minima(N_d=1000.0, f_yd_MPa=CA50.fyd, A_c=A_c)
    assert 0.15 * 1000.0 / (CA50.fyd * 1000.0) * 1e4 == pytest.approx(
        3.45, abs=0.01)
    assert minima * 1e4 == pytest.approx(3.60, abs=0.01)
    assert A_s_maxima(A_c) * 1e4 == pytest.approx(72.0)


def test_A_s_min_pela_parcela_de_forca_quando_a_normal_e_grande():
    """A outra parcela governa com N_d alto — as duas existem por motivos diferentes."""
    minima = A_s_minima(N_d=5000.0, f_yd_MPa=CA50.fyd, A_c=0.09)
    assert minima * 1e4 == pytest.approx(17.25, abs=0.01)


def test_limite_de_8_por_cento_vale_TAMBEM_na_secao_de_emenda():
    """17.3.5.3.2: "inclusive a sobreposição em regiões de emenda".

    Com 100 % das barras emendadas na mesma seção (autorizado por 9.5.2.1 para
    armadura permanentemente comprimida), a armadura DUPLICA na emenda — o que
    limita a 4 % de A_c FORA dela. É a restrição que costuma governar.
    """
    A_c = 0.09
    # 4,5 % de A_c passa na seção corrente e REPROVA na emenda (9,0 %).
    quase_no_limite = 0.045 * A_c
    resultado = verificar_armadura_longitudinal(
        A_s_adotada=quase_no_limite, numero_de_barras=8,
        phi_longitudinal_mm=25.0, N_d=1000.0, f_yd_MPa=CA50.fyd,
        h_secao=0.30, b_secao=0.30, d_agregado_mm=19.0,
        espacamento_entre_eixos_mm=92.0)
    assert resultado.atende_A_s_maxima_secao_corrente is True
    assert resultado.atende_A_s_maxima_na_emenda is False
    assert resultado.atendido is False


def test_armadura_longitudinal_da_geometria_de_referencia_atende():
    """4 phi 16 em 30×30: A_s = 8,04 cm² (0,89 % de A_c), tudo dentro."""
    resultado = verificar_armadura_longitudinal(
        A_s_adotada=QUATRO_PHI_16, numero_de_barras=4,
        phi_longitudinal_mm=16.0, N_d=1000.0, f_yd_MPa=CA50.fyd,
        h_secao=0.30, b_secao=0.30, d_agregado_mm=19.0,
        espacamento_entre_eixos_mm=184.0)
    assert resultado.atendido is True
    assert resultado.A_s_na_emenda == pytest.approx(2.0 * QUATRO_PHI_16)
    assert resultado.espacamento_livre_minimo_exigido_mm == pytest.approx(
        22.8, abs=0.01)   # max(20 mm; phi = 16; 1,2·19 = 22,8)
    assert resultado.phi_maximo_mm == pytest.approx(37.5)   # b_mín/8


def test_espacamento_livre_e_verificado_TAMBEM_na_emenda_com_barras_duplicadas():
    """18.4.2.2: "esses valores se aplicam também às regiões de emendas".

    Caso construído: o espaçamento livre passa na seção corrente e REPROVA na
    emenda, onde a barra da espera consome mais um diâmetro. É verificação, e
    não aviso (REQ-PILARETE-07).
    """
    resultado = verificar_armadura_longitudinal(
        A_s_adotada=QUATRO_PHI_16, numero_de_barras=4,
        phi_longitudinal_mm=16.0, N_d=1000.0, f_yd_MPa=CA50.fyd,
        h_secao=0.30, b_secao=0.30, d_agregado_mm=19.0,
        espacamento_entre_eixos_mm=52.0)
    assert resultado.espacamento_livre_na_secao_corrente_mm == pytest.approx(
        36.0)
    assert resultado.espacamento_livre_na_emenda_mm == pytest.approx(20.0)
    assert resultado.atende_espacamento_livre_secao_corrente is True
    assert resultado.atende_espacamento_livre_na_emenda is False


def test_phi_minimo_de_10_mm_e_numero_minimo_de_barras():
    """18.4.2.1/18.4.2.2: phi >= 10 mm e UMA BARRA POR VÉRTICE (4 no retângulo)."""
    resultado = verificar_armadura_longitudinal(
        A_s_adotada=QUATRO_PHI_16, numero_de_barras=3,
        phi_longitudinal_mm=8.0, N_d=1000.0, f_yd_MPa=CA50.fyd,
        h_secao=0.30, b_secao=0.30, d_agregado_mm=19.0,
        espacamento_entre_eixos_mm=184.0)
    assert resultado.atende_phi_minimo is False
    assert resultado.atende_numero_de_barras is False


def test_espacamento_entre_eixos_limitado_a_min_2b_400mm():
    """18.4.2.2: <= min(2·b_mín ; 400 mm). Em 30×30 governa o 400 mm."""
    resultado = verificar_armadura_longitudinal(
        A_s_adotada=QUATRO_PHI_16, numero_de_barras=4,
        phi_longitudinal_mm=16.0, N_d=1000.0, f_yd_MPa=CA50.fyd,
        h_secao=0.30, b_secao=0.30, d_agregado_mm=19.0,
        espacamento_entre_eixos_mm=420.0)
    assert resultado.espacamento_entre_eixos_maximo_mm == pytest.approx(400.0)
    assert resultado.atende_espacamento_entre_eixos is False


# --- REQ-PILARETE-08: estribos e a RECUSA do CA-60 -------------------------

def test_k_phi_existe_para_CA25_e_CA50_e_RECUSA_CA60():
    """18.4.3 dá 24 phi (CA-25) e 12 phi (CA-50). CA-60 NÃO APARECE.

    É PROIBIDO interpolar por f_yk, extrapolar de CA-50 ou "adotar 12 phi por
    analogia": o valor é NAO_DECLARADO_NA_FONTE e a recusa é o comportamento
    correto.
    """
    assert k_phi_de_18_4_3("CA-25") == pytest.approx(24.0)
    assert k_phi_de_18_4_3("CA-50") == pytest.approx(12.0)
    with pytest.raises(RecusaForaDeDominio) as erro:
        k_phi_de_18_4_3("CA-60")
    assert "18.4.3" in erro.value.mensagem
    assert "CA-60" in erro.value.mensagem


def test_CA60_longitudinal_recusa_no_detalhamento_do_estribo():
    """A recusa chega ao caminho de verificação, não fica só na função-folha."""
    with pytest.raises(RecusaForaDeDominio):
        verificar_estribos(concreto=C25, aco_longitudinal=CA60,
                           phi_longitudinal_mm=16.0, phi_t_mm=5.0,
                           s_adotado_mm=125.0, h_secao=0.30, b_secao=0.30)


def test_piso_de_phi_t_e_o_MAIOR_dos_dois_e_nunca_o_menor():
    """REQ-PILARETE-19(12), segunda metade: "o menor dos limites" NÃO vale em piso.

    Com phi 25 mm, 18.4.3 exige phi_t >= max(5 ; 25/4 = 6,25) = 6,25 mm e
    18.3.3.2 exige >= 5 mm. O adotado tem de ser 6,25 — tomar o menor (5,0)
    afrouxaria a exigência: erro do lado INSEGURO.
    """
    assert phi_t_minimo_18_4_3(25.0) == pytest.approx(6.25)
    resultado = verificar_estribos(
        concreto=C25, aco_longitudinal=CA50, phi_longitudinal_mm=25.0,
        phi_t_mm=5.0, s_adotado_mm=125.0, h_secao=0.30, b_secao=0.30,
        mesmo_aco_nas_duas_armaduras=False)
    assert resultado.alternativa_de_estribo_fino_invocada is False
    assert resultado.piso_phi_t.natureza == "PISO"
    assert resultado.piso_phi_t.valor_adotado == pytest.approx(6.25)
    assert resultado.piso_phi_t.item_que_governou == "18.4.3"
    assert resultado.atende_piso_phi_t is False   # 5,0 < 6,25


def test_composicao_de_tetos_na_geometria_A_governada_por_18_3_3_2():
    """REQ-PILARETE-19(12): 154,2 mm (18.3.3.2) contra 192,0 mm (18.4.3).

    Geometria A: 30×30, phi 16, d = 25,7 cm, V_Sd = 120 kN, V_Rd2 = 334,6 kN.
    Acrescentar o cortante ao escopo TORNOU o detalhamento mais restritivo — um
    pilarete detalhado só por 18.4.3 pode REPROVAR aqui.
    """
    assert s_max_18_4_3(phi_longitudinal_mm=16.0, b_min_mm=300.0,
                        k_phi=12.0) == pytest.approx(192.0)
    assert s_max_18_3_3_2(d_util_mm=257.0, V_Sd=120.0,
                          V_Rd2_valor=334.6) == pytest.approx(154.2)
    resultado = verificar_estribos(
        concreto=C25, aco_longitudinal=CA50, phi_longitudinal_mm=16.0,
        phi_t_mm=5.0, s_adotado_mm=125.0, h_secao=0.30, b_secao=0.30,
        d_util_no_plano_do_cortante=0.257, V_Sd=120.0, V_Rd2_valor=334.6)
    assert resultado.teto_s.natureza == "TETO"
    assert resultado.teto_s.valor_18_4_3 == pytest.approx(192.0)
    assert resultado.teto_s.valor_18_3_3_2 == pytest.approx(154.2)
    assert resultado.teto_s.valor_adotado == pytest.approx(154.2)
    assert resultado.teto_s.item_que_governou == "18.3.3.2"
    assert resultado.atende_teto_s is True    # s = 125 mm
    assert resultado.atendido is True
    assert "18.3.3.2" in resultado.teto_s.descricao_para_memorial


def test_ramos_dos_limiares_de_18_3_3_2():
    """Os DOIS limiares (0,67 e 0,20) governam grandezas diferentes."""
    assert s_max_18_3_3_2(d_util_mm=257.0, V_Sd=300.0,
                          V_Rd2_valor=334.6) == pytest.approx(77.1)
    assert s_t_max_18_3_3_2(d_util_mm=257.0, V_Sd=50.0,
                            V_Rd2_valor=334.6) == pytest.approx(257.0)
    assert s_t_max_18_3_3_2(d_util_mm=257.0, V_Sd=120.0,
                            V_Rd2_valor=334.6) == pytest.approx(154.2)


def test_na_faixa_B_so_18_4_3_tem_valor():
    """Sem cortante verificado não existe V_Rd2 — e é PROIBIDO arbitrar um.

    Na FAIXA B de 14.4.1 o cortante foi RECUSADO; o detalhamento continua
    valendo, mas só pela fonte que não depende de V_Rd2.
    """
    resultado = verificar_estribos(
        concreto=C25, aco_longitudinal=CA50, phi_longitudinal_mm=16.0,
        phi_t_mm=5.0, s_adotado_mm=180.0, h_secao=0.30, b_secao=0.30)
    assert resultado.cortante_verificado is False
    assert resultado.teto_s.valor_18_3_3_2 is None
    assert resultado.teto_s.valor_adotado == pytest.approx(192.0)
    assert resultado.teto_s_transversal is None
    with pytest.raises(RecusaForaDeDominio):
        verificar_estribos(concreto=C25, aco_longitudinal=CA50,
                           phi_longitudinal_mm=16.0, phi_t_mm=5.0,
                           s_adotado_mm=180.0, h_secao=0.30, b_secao=0.30,
                           V_Sd=120.0)


def test_par_de_desigualdades_phi_sobre_4_ate_phi():
    """A Emenda 1:2026 fecha a caixa: phi/4 <= phi_t <= phi.

    Nenhuma das duas fontes enuncia o par junto — 18.4.3 dá o piso e a Emenda,
    em 18.3.3.2, exige phi_long >= phi_t nas barras de canto.
    """
    resultado = verificar_estribos(
        concreto=C25, aco_longitudinal=CA50, phi_longitudinal_mm=6.3,
        phi_t_mm=8.0, s_adotado_mm=100.0, h_secao=0.30, b_secao=0.30)
    assert resultado.atende_phi_long_maior_ou_igual_phi_t is False
    assert resultado.atendido is False
    ok = verificar_estribos(
        concreto=C25, aco_longitudinal=CA50, phi_longitudinal_mm=16.0,
        phi_t_mm=5.0, s_adotado_mm=100.0, h_secao=0.30, b_secao=0.30)
    assert ok.atende_phi_long_maior_ou_igual_phi_t is True


def test_teto_de_phi_t_por_b_sobre_10_e_interpretacao_declarada():
    """18.3.3.2 escreve "1/10 da largura da alma da VIGA"; aqui é b_mín/10."""
    assert phi_t_maximo_18_3_3_2(b_min_mm=300.0,
                                 barra_lisa=False) == pytest.approx(30.0)
    assert phi_t_maximo_18_3_3_2(b_min_mm=300.0,
                                 barra_lisa=True) == pytest.approx(12.0)
    resultado = verificar_estribos(
        concreto=C25, aco_longitudinal=CA50, phi_longitudinal_mm=16.0,
        phi_t_mm=5.0, s_adotado_mm=125.0, h_secao=0.30, b_secao=0.30)
    assert any("1/10 da largura da alma" in declaracao
               for declaracao in resultado.declaracoes)


def test_s_max_adicional_do_estribo_fino_nao_tem_raiz_quadrada():
    """ARMADILHA DE TRANSCRIÇÃO: a camada de texto do PDF sugere um expoente 1/2.

    s_máx = 90000·(phi_t²/phi)/f_yk. Com phi_t 5 mm, phi 16 mm e CA-50 dá
    281,25 mm; com a raiz inexistente daria 2,25 mm (e mm^0,5, que o pint
    rejeita). É ADICIONAL, nunca substitutiva do min(200, b_mín, k_phi·phi).
    """
    valor = s_max_adicional_estribo_fino_18_4_3(
        phi_t_mm=5.0, phi_longitudinal_mm=16.0, f_yk_MPa=500.0)
    assert valor == pytest.approx(281.25, abs=0.01)
    com_raiz = 90000.0 * (5.0 ** 2 / 16.0) ** 0.5 / 500.0
    assert valor != pytest.approx(com_raiz)

    # phi_t = 3 mm está ABAIXO do piso absoluto de 5 mm: a alternativa NÃO é
    # oferecida (ela dispensa o phi/4, jamais o piso de 5 mm) e o detalhamento
    # reprova pelo piso.
    fino_demais = verificar_estribos(
        concreto=C25, aco_longitudinal=CA50, phi_longitudinal_mm=16.0,
        phi_t_mm=3.0, s_adotado_mm=125.0, h_secao=0.30, b_secao=0.30)
    assert fino_demais.alternativa_de_estribo_fino_invocada is False
    assert fino_demais.s_max_adicional_estribo_fino_mm is None
    assert fino_demais.atende_piso_phi_t is False    # 3 < max(5; 4)


def test_alternativa_de_estribo_fino_dispensa_phi_sobre_4_mas_nao_o_piso_de_5_mm():
    """18.4.3 AUTORIZA phi_t < phi/4 com o mesmo aço e o s_máx ADICIONAL.

    phi 25 mm com estribo phi 5 mm: o phi/4 = 6,25 mm seria violado, mas a
    alternativa da Norma o dispensa — em troca do s_máx =
    90000·(5²/25)/500 = 180 mm, que é ADICIONAL ao min(200 ; b_mín ; 12·phi).
    Sem a declaração de mesmo tipo de aço a alternativa não é oferecida (ver o
    teste do piso). E ela NUNCA dispensa o piso absoluto de 5 mm.
    """
    dentro = verificar_estribos(
        concreto=C25, aco_longitudinal=CA50, phi_longitudinal_mm=25.0,
        phi_t_mm=5.0, s_adotado_mm=125.0, h_secao=0.30, b_secao=0.30,
        mesmo_aco_nas_duas_armaduras=True)
    assert dentro.alternativa_de_estribo_fino_invocada is True
    assert dentro.piso_phi_t.valor_adotado == pytest.approx(5.0)
    assert dentro.atende_piso_phi_t is True
    assert dentro.s_max_adicional_estribo_fino_mm == pytest.approx(180.0)
    assert dentro.atende_s_adicional is True
    assert dentro.atendido is True
    assert any("ADICIONAL" in d for d in dentro.declaracoes)

    # o mesmo estribo com s = 190 mm passa no teto de 18.4.3 (200 mm) e
    # REPROVA na limitação adicional — que é ADICIONAL, não substitutiva.
    fora = verificar_estribos(
        concreto=C25, aco_longitudinal=CA50, phi_longitudinal_mm=25.0,
        phi_t_mm=5.0, s_adotado_mm=190.0, h_secao=0.30, b_secao=0.30,
        mesmo_aco_nas_duas_armaduras=True)
    assert fora.teto_s.valor_adotado == pytest.approx(200.0)
    assert fora.atende_teto_s is True
    assert fora.atende_s_adicional is False
    assert fora.atendido is False


def test_empate_exato_entre_as_duas_fontes_nomeia_as_DUAS_no_memorial():
    """Empatou, os DOIS governam — e o desempate não é lexicográfico.

    Ref.: ABNT NBR 6118:2023, itens 18.4.3 e 18.3.3.2, p. 150-154
    [deriv: DER-NBR6118-composicao-18.3.3.2-com-18.4.3]

    Caso COMUM, não exótico: com phi 16 mm o phi/4 = 4 mm fica abaixo do piso
    absoluto, e as DUAS fontes exigem exatamente os mesmos 5 mm. Antes, o
    desempate saía por acidente da comparação das strings dos rótulos
    ("18.3.3.2" < "18.4.3"), o que atribuía o empate a lados opostos conforme
    a natureza fosse TETO ou PISO. O memorial dizia "governou 18.4.3", e quem
    lesse concluiria que 18.3.3.2 estava folgado ali — quando impõe o mesmo
    limite.
    """
    resultado = verificar_estribos(
        concreto=C25, aco_longitudinal=CA50, phi_longitudinal_mm=16.0,
        phi_t_mm=6.0, s_adotado_mm=125.0, h_secao=0.30, b_secao=0.30)
    piso = resultado.piso_phi_t
    assert piso.valor_18_4_3 == pytest.approx(5.0)
    assert piso.valor_18_3_3_2 == pytest.approx(5.0)
    assert piso.valor_adotado == pytest.approx(5.0)
    assert piso.item_que_governou == "18.4.3 e 18.3.3.2"
    assert "governou 18.4.3 e 18.3.3.2" in piso.descricao_para_memorial

    # Sem empate, a atribuição continua sendo a UM item só.
    assert resultado.teto_s.item_que_governou == "18.4.3"


def test_o_default_de_mesmo_aco_e_RESTRITIVO_e_nao_oferece_a_alternativa():
    """Omitir o parâmetro NÃO pode valer por afirmar a condição de 18.4.3.

    Ref.: ABNT NBR 6118:2023, item 18.4.3, p. 153-154
    [rule: NBR6118-18.4.3-armaduras-transversais-pilarete]
    [req: REQ-PILARETE-08-estribos-e-a-recusa-do-CA-60]

    ``mesmo_aco_nas_duas_armaduras`` é a CONDIÇÃO que autoriza dispensar o
    ``phi_t >= phi/4``. Com default ``True`` — como estava — todo chamador que
    ignorasse o parâmetro ganhava a dispensa de graça, com a condição da Norma
    presumida satisfeita por omissão: erro do lado INSEGURO numa função
    pública. Mesmíssima chamada do teste acima, só que SEM o parâmetro: a
    alternativa não é oferecida e o phi/4 = 6,25 mm volta a valer, reprovando
    o estribo de 5 mm.
    """
    omitido = verificar_estribos(
        concreto=C25, aco_longitudinal=CA50, phi_longitudinal_mm=25.0,
        phi_t_mm=5.0, s_adotado_mm=125.0, h_secao=0.30, b_secao=0.30)
    assert omitido.alternativa_de_estribo_fino_invocada is False
    assert omitido.piso_phi_t.valor_adotado == pytest.approx(6.25)
    assert omitido.atende_piso_phi_t is False
    assert omitido.atendido is False


def test_nota_de_C55_a_C90_e_aviso_e_nunca_reprovacao():
    """A NOTA de 18.4.3 escreve "recomenda-se" — recomendação não vira critério."""
    c60 = Concreto(fck=60.0, gamma_c=1.4)
    resultado = verificar_estribos(
        concreto=c60, aco_longitudinal=CA50, phi_longitudinal_mm=16.0,
        phi_t_mm=5.0, s_adotado_mm=125.0, h_secao=0.30, b_secao=0.30)
    assert resultado.nota_C55_a_C90 is not None
    assert "recomenda" in resultado.nota_C55_a_C90.lower()
    assert resultado.atendido is True   # o aviso NÃO reprova
    em_C25 = verificar_estribos(
        concreto=C25, aco_longitudinal=CA50, phi_longitudinal_mm=16.0,
        phi_t_mm=5.0, s_adotado_mm=125.0, h_secao=0.30, b_secao=0.30)
    assert em_C25.nota_C55_a_C90 is None


def test_k_phi_de_CA25_e_o_dobro_e_o_teto_de_200_mm_passa_a_governar():
    """Com CA-25, 24·phi = 384 mm e o teto de 200 mm de 18.4.3 governa."""
    assert s_max_18_4_3(phi_longitudinal_mm=16.0, b_min_mm=300.0,
                        k_phi=24.0) == pytest.approx(200.0)


# --- REQ-PILARETE-10: emenda por traspasse ---------------------------------

def test_ell_0c_da_geometria_de_referencia():
    """phi 16, C25, CA-50, boa aderência: ell_b = 602,7 mm e ell_0c = 602,7 mm.

    ell_0c,mín = max(0,6·602,7 ; 15·16 ; 200) = 361,6 mm, e quem governa é o
    próprio ell_b,nec.
    """
    resultado = comprimento_de_traspasse(
        concreto=C25, aco=CA50, phi_mm=16.0, boa_aderencia=True,
        armadura_tracionada_em_alguma_combinacao=False,
        A_s_calculada=QUATRO_PHI_16, A_s_efetiva=QUATRO_PHI_16)
    assert resultado.f_bd_MPa == pytest.approx(2.886, abs=1e-3)
    assert resultado.ell_b * 1000.0 == pytest.approx(602.7, abs=0.2)
    assert resultado.ell_0c_minimo * 1000.0 == pytest.approx(361.6, abs=0.2)
    assert resultado.ell_0c * 1000.0 == pytest.approx(602.7, abs=0.2)
    assert resultado.alpha_ancoragem == pytest.approx(1.0)


def test_ma_aderencia_alonga_o_traspasse_em_1_sobre_0_7():
    """eta_2 é DECLARADO (9.3.2.1) e nunca assumido bom."""
    boa = comprimento_de_traspasse(
        concreto=C25, aco=CA50, phi_mm=16.0, boa_aderencia=True,
        armadura_tracionada_em_alguma_combinacao=False,
        A_s_calculada=QUATRO_PHI_16, A_s_efetiva=QUATRO_PHI_16)
    ma = comprimento_de_traspasse(
        concreto=C25, aco=CA50, phi_mm=16.0, boa_aderencia=False,
        armadura_tracionada_em_alguma_combinacao=False,
        A_s_calculada=QUATRO_PHI_16, A_s_efetiva=QUATRO_PHI_16)
    assert ma.ell_0c == pytest.approx(boa.ell_0c / 0.7, rel=1e-9)


def test_ell_0c_minimo_governa_com_bitola_pequena_e_concreto_forte():
    """O piso de 0,6·ell_b / 15·phi / 200 mm existe e às vezes governa."""
    resultado = comprimento_de_traspasse(
        concreto=Concreto(fck=25.0, gamma_c=1.4), aco=CA50, phi_mm=10.0,
        boa_aderencia=True, armadura_tracionada_em_alguma_combinacao=False,
        A_s_calculada=area_barra(10.0) * 2.0,
        A_s_efetiva=area_barra(10.0) * 4.0)
    assert resultado.ell_0c == pytest.approx(resultado.ell_0c_minimo)
    assert resultado.ell_0c >= 0.200


def test_bitola_acima_de_32_mm_proibe_o_traspasse():
    """9.5.2, 1º parágrafo (redação da Em1:2026): acima de 32 mm, RECUSA."""
    with pytest.raises(RecusaForaDeDominio) as erro:
        comprimento_de_traspasse(
            concreto=C25, aco=CA50, phi_mm=40.0, boa_aderencia=True,
            armadura_tracionada_em_alguma_combinacao=False,
            A_s_calculada=1e-3, A_s_efetiva=1e-3)
    assert "32" in erro.value.mensagem


def test_armadura_tracionada_derruba_a_autorizacao_de_9_5_2_1():
    """A hipótese é sobre o ESFORÇO: se alguma combinação tracionar, RECUSA.

    Caem a autorização de emendar 100 % na mesma seção; passariam a valer
    9.5.2.2 e a Tabela 9.4, não implementadas nesta versão.
    """
    with pytest.raises(RecusaForaDeDominio) as erro:
        comprimento_de_traspasse(
            concreto=C25, aco=CA50, phi_mm=16.0, boa_aderencia=True,
            armadura_tracionada_em_alguma_combinacao=True,
            A_s_calculada=QUATRO_PHI_16, A_s_efetiva=QUATRO_PHI_16)
    assert "9.5.2.1" in erro.value.mensagem
    assert "permanentemente comprimida" in erro.value.mensagem


def test_armadura_transversal_da_emenda_impoe_o_TEXTO_e_nao_dimensiona():
    """9.5.2.4.2: estribo a 4·phi além de cada extremidade; Soma A_st REMETIDA.

    Os valores que existem SÓ na Figura 9.5 não foram conferidos por leitura
    vetorial e o software NÃO dimensiona por eles.
    """
    exigencias = exigencias_de_armadura_transversal_da_emenda(
        phi_mm=16.0, ell_0c=0.6027)
    texto = " ".join(exigencias)
    assert "64 mm (4·phi)" in texto
    assert "160 mm (10·phi)" in texto
    assert "terços extremos" in texto
    assert "NÃO é" in texto and "projetista" in texto


def test_o_pilarete_nao_reusa_a_ancoragem_do_motor_amplo():
    """REQ-PILARETE-10: `sapata.py::_ancoragem_pilar` usa um HÍBRIDO dos mínimos.

    Aquela função mistura o 0,6·ell_b da EMENDA (9.5.2.3) com o 10 phi/100 mm
    da ANCORAGEM (9.4.2.5) e não corresponde a nenhum dos dois itens. O
    pilarete calcula o seu próprio ell_0c, com o `[rule:]` correto — e este
    teste fixa que os mínimos são MESMO os de 9.5.2.3.
    """
    resultado = comprimento_de_traspasse(
        concreto=C25, aco=CA50, phi_mm=16.0, boa_aderencia=True,
        armadura_tracionada_em_alguma_combinacao=False,
        A_s_calculada=QUATRO_PHI_16, A_s_efetiva=QUATRO_PHI_16)
    hibrido = max(0.6 * resultado.ell_b, 10.0 * 0.016, 0.100)
    assert resultado.ell_0c_minimo == pytest.approx(
        max(0.6 * resultado.ell_b, 15.0 * 0.016, 0.200))
    assert resultado.ell_0c_minimo == pytest.approx(hibrido)  # coincidem aqui

    # ... e NÃO coincidem quando o piso absoluto governa: 200 mm (emenda,
    # 9.5.2.3) contra 100 mm (ancoragem, 9.4.2.5). Bitola pequena com concreto
    # forte é onde isso aparece — o hibrido devolveria 150 mm de traspasse.
    fino = comprimento_de_traspasse(
        concreto=Concreto(fck=50.0, gamma_c=1.4), aco=CA50, phi_mm=10.0,
        boa_aderencia=True, armadura_tracionada_em_alguma_combinacao=False,
        A_s_calculada=1e-4, A_s_efetiva=1e-3)
    hibrido_fino = max(0.6 * fino.ell_b, 10.0 * 0.010, 0.100)
    assert fino.ell_0c_minimo == pytest.approx(0.200)
    assert hibrido_fino == pytest.approx(0.150)
    assert fino.ell_0c_minimo > hibrido_fino


def test_o_minimo_de_15_phi_nunca_governa_dado_o_piso_de_25_phi():
    """ACHADO desta rodada, registrado como teste porque é verificável.

    9.5.2.3 manda ell_0c,mín = max(0,6·ell_b ; 15·phi ; 200 mm) e 9.4.2.4 impõe
    ell_b >= 25·phi. Logo 0,6·ell_b >= 15·phi SEMPRE: a parcela de 15·phi é
    REDUNDANTE em toda a faixa admissível, e quem pode governar são só as
    outras duas. O código implementa as três parcelas como a Norma escreve —
    transcrição é transcrição —, e este teste documenta que a terceira nunca
    decide, para que ninguém a "otimize" achando que encontrou um caso.
    """
    for phi_mm, fck in ((10.0, 20.0), (16.0, 25.0), (25.0, 50.0),
                        (32.0, 90.0)):
        resultado = comprimento_de_traspasse(
            concreto=Concreto(fck=fck, gamma_c=1.4), aco=CA50, phi_mm=phi_mm,
            boa_aderencia=True, armadura_tracionada_em_alguma_combinacao=False,
            A_s_calculada=1e-4, A_s_efetiva=1e-3)
        assert resultado.ell_b >= 25.0 * phi_mm / 1000.0 - 1e-12
        assert 0.6 * resultado.ell_b >= 15.0 * phi_mm / 1000.0 - 1e-12


# --- REQ-PILARETE-11: a junta, três casos e DUAS recusas -------------------

def test_monolitico_segue_com_ou_sem_H():
    """Não há junta e 21.6 não se aplica — mas 17.4 (outra coisa) continua."""
    sem_H = verificar_junta(tipo_de_junta=MONOLITICO, H_x=0.0, H_y=0.0)
    com_H = verificar_junta(tipo_de_junta=MONOLITICO, H_x=40.0, H_y=0.0)
    assert sem_H.tipo_de_junta == MONOLITICO
    assert com_H.H_resultante_declarada_nao_nula is True
    assert any("MONOLÍTICA" in d for d in com_H.declaracoes)


def test_junta_aderente_com_H_igual_a_zero_segue_com_declaracao_literal():
    """A declaração vai LITERAL ao memorial, com a exigência do 1º parágrafo."""
    resultado = verificar_junta(tipo_de_junta=JUNTA_COM_ADERENCIA_DECLARADA,
                                H_x=0.0, H_y=0.0)
    juntas = " ".join(resultado.declaracoes)
    assert "DECLARADAS ASSEGURADAS" in juntas
    assert "local" in juntas.lower() and "configuração" in juntas.lower()


def test_junta_aderente_com_H_de_0_001_kN_RECUSA():
    """TESTE EM CIMA DO ZERO (REQ-PILARETE-11), porque recusa que não recusa é
    pior que recusa nenhuma.

    O gatilho é H != 0 DECLARADO. É PROIBIDO criar faixa de "H pequeno", "H
    desprezível" ou fração de N — não há base normativa para o limiar.
    """
    seguiu = verificar_junta(tipo_de_junta=JUNTA_COM_ADERENCIA_DECLARADA,
                             H_x=0.0, H_y=0.0)
    assert seguiu.H_resultante_declarada_nao_nula is False
    with pytest.raises(RecusaForaDeDominio) as erro:
        verificar_junta(tipo_de_junta=JUNTA_COM_ADERENCIA_DECLARADA,
                        H_x=0.001, H_y=0.0)
    mensagem = erro.value.mensagem
    assert "0.001" in mensagem                    # (i) o valor de H
    assert "ADERENTE" in mensagem                 # (ii) a declaração
    assert "21.6" in mensagem and "181" in mensagem   # (iii) item e página
    assert "9062" in mensagem                     # (iv) a norma ausente
    assert "MONOLITICA" in mensagem               # (v) a alternativa
    assert "prosseguir mesmo assim" in mensagem.lower()


def test_junta_aderente_com_H_y_nao_nulo_tambem_recusa():
    """As DUAS componentes disparam a recusa: o gatilho é a força horizontal."""
    with pytest.raises(RecusaForaDeDominio):
        verificar_junta(tipo_de_junta=JUNTA_COM_ADERENCIA_DECLARADA,
                        H_x=0.0, H_y=0.001)


def test_junta_sem_aderencia_recusa_com_ou_sem_H():
    """A segunda recusa dura de 21.6, e ela não depende de H."""
    for H_x in (0.0, 50.0):
        with pytest.raises(RecusaForaDeDominio) as erro:
            verificar_junta(tipo_de_junta=JUNTA_SEM_ADERENCIA_ASSEGURADA,
                            H_x=H_x, H_y=0.0)
        assert "9062" in erro.value.mensagem


def test_tipo_de_junta_e_enumeracao_fechada_sem_default():
    """Sem declaração não há cálculo — e "JUNTA_QUALQUER" não existe."""
    with pytest.raises(RecusaForaDeDominio):
        verificar_junta(tipo_de_junta=None, H_x=0.0, H_y=0.0)
    with pytest.raises(RecusaForaDeDominio):
        verificar_junta(tipo_de_junta="JUNTA_QUALQUER", H_x=0.0, H_y=0.0)
