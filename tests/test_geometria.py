"""Testes de calc_core/geotecnico/geometria.py (ruleset v0.1.0).

Executar:  python -m unittest discover -s tests -v   (ou pytest, se instalado)

Cada funcao publica tem: valor conhecido, borda e rejeicao fora do dominio.
Casos do ruleset: SC-01, SC-02 (Bastos 2023, Ex. 1a), SC-03 (0,60 x 0,60 m, D = 1,5 m).
"""
from __future__ import annotations

import dataclasses
import hashlib
import inspect
import math
import re
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from calc_core.geotecnico import geometria as g  # noqa: E402
from calc_core.geotecnico.geometria import (  # noqa: E402
    EntradaSapataCentrada, ErroMisturaDeMetodo, Forca, Metodo, MetodoResistencia, Natureza,
    Procedimento73, Recusa, Tensao,
)

K = Natureza.CARACTERISTICA
D = Natureza.CALCULO


def entrada(**kw) -> EntradaSapataCentrada:
    """Caso base valido: SC-02 (Bastos 2023 Ex. 1a), metodo admissivel, modo A."""
    base = dict(
        metodo=Metodo.ADMISSIVEL,
        B=2.05, L=2.65, D_assentamento=1.5,
        N_k=1250.0, N_d=None, G_k=1250.0, P_solo_k=0.0, P_pp_real_k=125.0,
        M_x=0.0, M_y=0.0, H_x=0.0, H_y=0.0, e_pilar_x=0.0, e_pilar_y=0.0,
        apoio_em_rocha=False, solo_expansivo=False, solo_colapsivel=False,
        solo_homogeneo_declarado=True,
        declaracao_fatores_7_2=True,
        sigma_adm=260.0,  # 0,26 MPa
        procedimento_7_3=(Procedimento73.SEMIEMPIRICO_7_3_3,),
        declaracao_ELS_atendido=True,
    )
    base.update(kw)
    return EntradaSapataCentrada(**base)


def entrada_sc01(metodo: Metodo, **kw) -> EntradaSapataCentrada:
    """SC-01: B = 2,0; L = 3,0; D = 1,5; sigma_r_k = 890 kPa (Cintra), analitico; ELS = 300."""
    base = dict(
        metodo=metodo,
        B=2.0, L=3.0, D_assentamento=1.5,
        N_k=1400.0, N_d=None, G_k=1000.0, P_solo_k=97.2, P_pp_real_k=90.0,
        M_x=0.0, M_y=0.0, H_x=0.0, H_y=0.0, e_pilar_x=0.0, e_pilar_y=0.0,
        apoio_em_rocha=False, solo_expansivo=False, solo_colapsivel=False,
        solo_homogeneo_declarado=True,
        declaracao_fatores_7_2=True,
        sigma_r_k=890.0, metodo_resistencia=MetodoResistencia.ANALITICO,
        declaracao_sem_ponderacao_parametros=True, sigma_ELS=300.0,
    )
    base.update(kw)
    return EntradaSapataCentrada(**base)


class AssertRecusa:
    def assertRecusado(self, res, regra):
        self.assertTrue(res.recusado, msg=f"esperava recusa por {regra}")
        self.assertEqual(res.grandezas, (), "RT-03: recusa nao pode devolver numero parcial")
        self.assertEqual(res.notas_memorial, ())
        recusas = [v for v in res.verificacoes if not v.aplicavel]
        self.assertTrue(recusas)
        self.assertIn(regra, [v.regra for v in recusas],
                      msg=f"recusas: {[(v.regra, v.motivo) for v in recusas]}")
        for v in recusas:
            self.assertIsNone(v.atende)
            self.assertTrue(v.motivo)
        self.assertTrue(res.nao_verificado, "RT-07: lista de nao verificados sempre presente")


# =============================================================================
# Casos do ruleset
# =============================================================================
class TestCasosRuleset(unittest.TestCase, AssertRecusa):
    def test_SC02_bastos_area_minima(self):
        res = g.verificar_sapata_centrada(entrada())
        self.assertFalse(res.recusado)
        # P_pp_k = max(125, 0,05*1250 = 62,5) = 125 kN
        self.assertEqual(res.grandeza("cargas.P_pp_k").valor, 125.0)
        # area_min = 1375/260 = 5,2885 m2 (Bastos: 52 885 cm2)
        self.assertAlmostEqual(res.grandeza("geotecnico.area_min").valor, 5.2885, delta=0.0005)
        self.assertAlmostEqual(res.grandeza("geotecnico.area_min").valor, 1375.0 / 260.0,
                               places=12)
        self.assertAlmostEqual(res.grandeza("geotecnico.area_base").valor, 5.4325, delta=0.0005)
        s_k = res.grandeza("geotecnico.sigma_solo_k").valor
        self.assertAlmostEqual(s_k, 1375.0 / (2.05 * 2.65), places=9)
        v = res.verificacao(g.REGRA_VERIF_ADMISSIVEL)
        self.assertTrue(v.aplicavel)
        self.assertTrue(v.atende)

    def test_SC01_admissivel_modo_B(self):
        res = g.verificar_sapata_centrada(entrada_sc01(Metodo.ADMISSIVEL))
        self.assertFalse(res.recusado)
        self.assertAlmostEqual(res.grandeza("geotecnico.sigma_adm_ELU").valor, 890.0 / 3.0)
        # sigma_adm = min(296,67; 300)
        self.assertAlmostEqual(res.grandeza("geotecnico.sigma_adm").valor, 890.0 / 3.0)
        self.assertEqual(res.grandeza("cargas.P_pp_k").valor, 90.0)
        s_k = res.grandeza("geotecnico.sigma_solo_k").valor
        self.assertAlmostEqual(s_k, (1400.0 + 90.0 + 97.2) / 6.0)
        self.assertTrue(50.0 <= s_k <= 600.0)
        self.assertTrue(res.verificacao(g.REGRA_VERIF_ADMISSIVEL).atende)
        nomes = [x.nome for x in res.grandezas]
        self.assertNotIn("seguranca.gamma_m", nomes)
        self.assertNotIn("seguranca.gamma_f", nomes)
        self.assertNotIn("geotecnico.sigma_solo_d", nomes)

    def test_SC01_calculo_modo_B(self):
        res = g.verificar_sapata_centrada(entrada_sc01(Metodo.CALCULO))
        self.assertFalse(res.recusado)
        self.assertAlmostEqual(res.grandeza("geotecnico.sigma_Rd_ELU").valor, 890.0 / 2.15)
        self.assertAlmostEqual(res.grandeza("cargas.N_d").valor, 1960.0)
        s_d = res.grandeza("geotecnico.sigma_solo_d").valor
        self.assertAlmostEqual(s_d, (1960.0 + 1.4 * (90.0 + 97.2)) / 6.0)
        self.assertTrue(res.verificacao(g.REGRA_VERIF_CALCULO).atende)
        self.assertTrue(res.verificacao(g.REGRA_ELU_ELS).atende)
        nomes = [x.nome for x in res.grandezas]
        self.assertNotIn("seguranca.FS_g", nomes)
        self.assertNotIn("geotecnico.sigma_adm", nomes)

    def test_SC03_sapata_minima_em_divisa_nao_rasa_recusada(self):
        res = g.verificar_sapata_centrada(entrada(B=0.60, L=0.60, D_assentamento=1.5))
        self.assertRecusado(res, g.REGRA_FUNDACAO_RASA)


# =============================================================================
# Guardas
# =============================================================================
class TestGuardaFundacaoRasa(unittest.TestCase):
    def test_valor_conhecido(self):
        v = g.guarda_fundacao_rasa(2.0, 3.0, 1.5)
        self.assertTrue(v.aplicavel and v.atende)

    def test_borda_igualdade_recusa(self):
        # 2*min(0,6; 0,6) = 1,2 m exatamente (duplicacao em float e exata)
        self.assertFalse(g.guarda_fundacao_rasa(0.6, 0.6, 1.2).aplicavel)
        self.assertTrue(g.guarda_fundacao_rasa(0.6, 0.6, 1.19).aplicavel)

    def test_usa_menor_dimensao(self):
        self.assertFalse(g.guarda_fundacao_rasa(1.0, 5.0, 2.0).aplicavel)

    def test_rejeicao_fora_do_dominio(self):
        for args in ((0.0, 1.0, 0.5), (1.0, 2.0, -0.1), (1.0, 2.0, None),
                     (float("nan"), 2.0, 0.5), (2.0, 1.0, 0.5), (1.0, 2.0, True)):
            self.assertFalse(g.guarda_fundacao_rasa(*args).aplicavel, msg=str(args))


class TestGuardaCargaCentrada(unittest.TestCase, AssertRecusa):
    def test_valor_conhecido(self):
        v = g.guarda_carga_centrada(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        self.assertTrue(v.aplicavel and v.atende)

    def test_borda_zero_negativo_e_zero(self):
        self.assertTrue(g.guarda_carga_centrada(-0.0, 0, 0, 0, 0, 0).aplicavel)

    def test_recusa_por_excentricidade(self):
        res = g.verificar_sapata_centrada(entrada(M_x=50.0))
        self.assertRecusado(res, g.REGRA_CARGA_CENTRADA)

    def test_recusa_por_forca_horizontal_e_pilar_deslocado(self):
        for campo, val in (("M_y", -1e-9), ("H_x", 5.0), ("H_y", 1.0),
                           ("e_pilar_x", 0.05), ("e_pilar_y", -0.01)):
            res = g.verificar_sapata_centrada(entrada(**{campo: val}))
            self.assertRecusado(res, g.REGRA_CARGA_CENTRADA)

    def test_omitir_nao_equivale_a_zero(self):
        res = g.verificar_sapata_centrada(entrada(M_x=None))
        self.assertRecusado(res, g.REGRA_CARGA_CENTRADA)


class TestGuardaCompressao(unittest.TestCase, AssertRecusa):
    def test_valor_conhecido(self):
        self.assertTrue(g.guarda_compressao(10.0, None).atende)
        self.assertTrue(g.guarda_compressao(None, 14.0).atende)

    def test_borda_zero_recusa(self):
        self.assertFalse(g.guarda_compressao(0.0, None).aplicavel)

    def test_rejeicao_tracao_e_ausencia(self):
        self.assertRecusado(g.verificar_sapata_centrada(entrada(N_k=-100.0)), g.REGRA_COMPRESSAO)
        self.assertRecusado(g.verificar_sapata_centrada(entrada(N_k=None)), g.REGRA_COMPRESSAO)
        self.assertFalse(g.guarda_compressao(10.0, -1.0).aplicavel)


class TestGuardaCasosParticulares(unittest.TestCase, AssertRecusa):
    def test_valor_conhecido(self):
        self.assertTrue(g.guarda_casos_particulares(False, False, False, True).atende)

    def test_rejeicoes(self):
        for kw in (dict(apoio_em_rocha=True), dict(solo_expansivo=True),
                   dict(solo_colapsivel=True), dict(solo_homogeneo_declarado=False),
                   dict(solo_homogeneo_declarado=None), dict(apoio_em_rocha=0)):
            self.assertRecusado(g.verificar_sapata_centrada(entrada(**kw)),
                                g.REGRA_CASOS_PARTICULARES)


class TestGuardaVento(unittest.TestCase, AssertRecusa):
    def test_valor_conhecido(self):
        self.assertTrue(g.guarda_vento_sem_majoracao(False).atende)

    def test_rejeicao_pedido_de_majoracao(self):
        self.assertRecusado(g.verificar_sapata_centrada(entrada(solicitar_majoracao_vento=True)),
                            g.REGRA_VENTO)
        self.assertFalse(g.guarda_vento_sem_majoracao(None).aplicavel)

    def test_nao_existe_fator_de_majoracao_no_codigo(self):
        fonte = inspect.getsource(g).lower()
        self.assertNotIn("fator_majoracao", fonte)
        self.assertNotIn("majoracao_vento =", fonte)

    def test_todas_as_guardas_reportadas(self):
        res = g.verificar_sapata_centrada(entrada(M_x=1.0, solicitar_majoracao_vento=True))
        recusadas = {v.regra for v in res.verificacoes if not v.aplicavel}
        self.assertEqual(recusadas, {g.REGRA_CARGA_CENTRADA, g.REGRA_VENTO})


# =============================================================================
# Esforcos (5.1, Tabela 1 nota c)
# =============================================================================
class TestEsforcos(unittest.TestCase, AssertRecusa):
    def test_admissivel_N_k(self):
        e = g.resolver_esforcos(Metodo.ADMISSIVEL, 100.0, None, None)
        self.assertEqual(e.N_k, Forca(100.0, K))
        self.assertIsNone(e.N_d)

    def test_admissivel_N_d_com_coef(self):
        e = g.resolver_esforcos(Metodo.ADMISSIVEL, None, 150.0, 1.5)
        self.assertEqual(e.N_k, Forca(100.0, K))

    def test_admissivel_N_d_sem_coef_recusa(self):
        with self.assertRaises(Recusa) as cm:
            g.resolver_esforcos(Metodo.ADMISSIVEL, None, 150.0, None)
        self.assertEqual(cm.exception.verificacao.regra, g.REGRA_ESFORCOS)

    def test_admissivel_ambiguo_recusa(self):
        self.assertRecusado(g.verificar_sapata_centrada(entrada(N_d=1750.0)), g.REGRA_ESFORCOS)

    def test_calculo_so_N_k_majora(self):
        e = g.resolver_esforcos(Metodo.CALCULO, 100.0, None, None)
        self.assertEqual(e.N_d, Forca(140.0, D))

    def test_calculo_N_d_fornecido_sem_coeficiente(self):
        e = g.resolver_esforcos(Metodo.CALCULO, 100.0, 135.0, None)
        self.assertEqual(e.N_d, Forca(135.0, D))
        self.assertEqual(e.N_k, Forca(100.0, K))

    def test_calculo_so_N_d_recusa_por_ELS(self):
        res = g.verificar_sapata_centrada(entrada_sc01(Metodo.CALCULO, N_k=None, N_d=1960.0))
        self.assertRecusado(res, g.REGRA_ELU_ELS)

    def test_calculo_coef_reducao_recusa(self):
        res = g.verificar_sapata_centrada(
            entrada_sc01(Metodo.CALCULO, coef_reducao_ao_caracteristico=1.4))
        self.assertRecusado(res, g.REGRA_ESFORCOS)

    def test_majorar_gamma_f(self):
        self.assertEqual(g.majorar_gamma_f(Forca(10.0, K)), Forca(14.0, D))
        self.assertEqual(g.majorar_gamma_f(Forca(0.0, K)), Forca(0.0, D))
        with self.assertRaises(ErroMisturaDeMetodo):
            g.majorar_gamma_f(Forca(10.0, D))


# =============================================================================
# Peso proprio (5.6)
# =============================================================================
class TestPesoProprio(unittest.TestCase, AssertRecusa):
    def test_real_maior_que_piso(self):
        self.assertEqual(g.peso_proprio_considerado(Forca(1000.0, K), Forca(90.0, K)),
                         Forca(90.0, K))

    def test_real_menor_que_piso(self):
        self.assertEqual(g.peso_proprio_considerado(Forca(1000.0, K), Forca(10.0, K)),
                         Forca(50.0, K))

    def test_borda_real_igual_piso_e_ausente(self):
        self.assertEqual(g.peso_proprio_considerado(Forca(1000.0, K), Forca(50.0, K)).valor_kN,
                         50.0)
        self.assertEqual(g.peso_proprio_considerado(Forca(1000.0, K), None), Forca(50.0, K))

    def test_ausente_gera_nota(self):
        res = g.verificar_sapata_centrada(entrada(P_pp_real_k=None))
        self.assertEqual(res.grandeza("cargas.P_pp_k").valor, 62.5)
        self.assertTrue(any("peso real nao informado" in n.texto for n in res.notas_memorial))

    def test_G_k_desconhecido_usa_N_k(self):
        res = g.verificar_sapata_centrada(entrada(G_k=None, G_k_desconhecido=True,
                                                  P_pp_real_k=None))
        self.assertEqual(res.grandeza("cargas.G_k").valor, 1250.0)
        self.assertEqual(res.grandeza("cargas.G_k").origem, "adotada")

    def test_rejeicoes(self):
        self.assertRecusado(g.verificar_sapata_centrada(entrada(G_k=None)), g.REGRA_PESO_PROPRIO)
        self.assertRecusado(g.verificar_sapata_centrada(entrada(G_k_desconhecido=True)),
                            g.REGRA_PESO_PROPRIO)
        self.assertRecusado(g.verificar_sapata_centrada(entrada(P_pp_real_k=-1.0)),
                            g.REGRA_PESO_PROPRIO)
        with self.assertRaises(ErroMisturaDeMetodo):
            g.peso_proprio_considerado(Forca(1000.0, D), None)
        with self.assertRaises(Recusa):
            g.peso_proprio_considerado(Forca(-1.0, K), None)


# =============================================================================
# Geometria e tensoes (7.6.1)
# =============================================================================
class TestTensaoUniforme(unittest.TestCase, AssertRecusa):
    def test_area_base(self):
        self.assertEqual(g.area_base(2.0, 2.5), 5.0)
        self.assertEqual(g.area_base(0.6, 0.6), 0.6 * 0.6)  # borda B == L
        for b, l_ in ((0.0, 1.0), (-1.0, 1.0), (2.0, 1.0), (None, 1.0), (math.inf, 1.0)):
            with self.assertRaises(Recusa):
                g.area_base(b, l_)

    def test_B_maior_que_L_recusa(self):
        self.assertRecusado(g.verificar_sapata_centrada(entrada(B=2.65, L=2.05)),
                            g.REGRA_TENSAO_UNIFORME)

    def test_tensao_caracteristica(self):
        s = g.tensao_caracteristica(Forca(1200.0, K), Forca(100.0, K), Forca(0.0, K), 5.0)
        self.assertEqual(s, Tensao(260.0, K))
        with self.assertRaises(ErroMisturaDeMetodo):
            g.tensao_caracteristica(Forca(1200.0, D), Forca(100.0, K), Forca(0.0, K), 5.0)
        with self.assertRaises(Recusa):
            g.tensao_caracteristica(Forca(1.0, K), Forca(0.0, K), Forca(0.0, K), 0.0)

    def test_tensao_de_calculo(self):
        s = g.tensao_de_calculo(Forca(1400.0, D), Forca(100.0, K), Forca(0.0, K), 5.0)
        self.assertAlmostEqual(s.valor_kPa, (1400.0 + 140.0) / 5.0)
        self.assertIs(s.natureza, D)
        with self.assertRaises(ErroMisturaDeMetodo):
            g.tensao_de_calculo(Forca(1400.0, K), Forca(100.0, K), Forca(0.0, K), 5.0)
        with self.assertRaises(ErroMisturaDeMetodo):
            g.tensao_de_calculo(Forca(1400.0, D), Forca(100.0, D), Forca(0.0, K), 5.0)

    def test_P_solo_entra_e_e_obrigatorio(self):
        r0 = g.verificar_sapata_centrada(entrada(P_solo_k=0.0))
        r1 = g.verificar_sapata_centrada(entrada(P_solo_k=54.325))
        self.assertAlmostEqual(r1.grandeza("geotecnico.sigma_solo_k").valor
                               - r0.grandeza("geotecnico.sigma_solo_k").valor, 10.0)
        self.assertRecusado(g.verificar_sapata_centrada(entrada(P_solo_k=None)),
                            g.REGRA_TENSAO_UNIFORME)
        self.assertRecusado(g.verificar_sapata_centrada(entrada(P_solo_k=-1.0)),
                            g.REGRA_TENSAO_UNIFORME)

    def test_areas_minimas(self):
        a = g.area_minima_admissivel(Forca(1250.0, K), Forca(125.0, K), Forca(0.0, K),
                                     Tensao(260.0, K))
        self.assertAlmostEqual(a, 5.2885, delta=0.0005)
        a_d = g.area_minima_calculo(Forca(1400.0, D), Forca(100.0, K), Forca(0.0, K),
                                    Tensao(308.0, D))
        self.assertAlmostEqual(a_d, 1540.0 / 308.0)
        with self.assertRaises(ErroMisturaDeMetodo):
            g.area_minima_admissivel(Forca(1.0, K), Forca(0.0, K), Forca(0.0, K),
                                     Tensao(260.0, D))
        with self.assertRaises(ErroMisturaDeMetodo):
            g.area_minima_calculo(Forca(1.0, D), Forca(0.0, K), Forca(0.0, K), Tensao(260.0, K))
        with self.assertRaises(Recusa):
            g.area_minima_admissivel(Forca(1.0, K), Forca(0.0, K), Forca(0.0, K),
                                     Tensao(0.0, K))


# =============================================================================
# Verificacoes 3.30 / 3.31 / ELS
# =============================================================================
class TestVerificacoes(unittest.TestCase):
    def test_admissivel_borda_igualdade_atende(self):
        # B*L = 5 m2; V = 1200 + max(100, 50) + 0 = 1300 kN -> 260 kPa == sigma_adm
        res = g.verificar_sapata_centrada(entrada(B=2.0, L=2.5, N_k=1200.0, G_k=1000.0,
                                                  P_pp_real_k=100.0))
        self.assertEqual(res.grandeza("geotecnico.sigma_solo_k").valor, 260.0)
        self.assertTrue(res.verificacao(g.REGRA_VERIF_ADMISSIVEL).atende)

    def test_admissivel_nao_atende_nao_e_recusa(self):
        res = g.verificar_sapata_centrada(entrada(B=2.0, L=2.5, N_k=1201.0, G_k=1000.0,
                                                  P_pp_real_k=100.0))
        self.assertFalse(res.recusado)
        v = res.verificacao(g.REGRA_VERIF_ADMISSIVEL)
        self.assertTrue(v.aplicavel)
        self.assertFalse(v.atende)

    def test_funcoes_diretas(self):
        self.assertTrue(g.verificar_admissivel(Tensao(100.0, K), Tensao(100.0, K)).atende)
        self.assertFalse(g.verificar_calculo(Tensao(101.0, D), Tensao(100.0, D)).atende)
        self.assertTrue(g.verificar_ELS(Tensao(99.0, K), Tensao(100.0, K)).atende)
        with self.assertRaises(ErroMisturaDeMetodo):
            g.verificar_admissivel(Tensao(100.0, D), Tensao(200.0, K))
        with self.assertRaises(ErroMisturaDeMetodo):
            g.verificar_calculo(Tensao(100.0, K), Tensao(200.0, D))
        with self.assertRaises(ErroMisturaDeMetodo):
            g.verificar_ELS(Tensao(100.0, D), Tensao(200.0, K))

    def test_calculo_ELS_governa_separadamente(self):
        # ELU folgado, ELS violado: as duas verificacoes aparecem com estados distintos.
        res = g.verificar_sapata_centrada(entrada_sc01(Metodo.CALCULO, sigma_ELS=200.0))
        self.assertTrue(res.verificacao(g.REGRA_VERIF_CALCULO).atende)
        self.assertFalse(res.verificacao(g.REGRA_ELU_ELS).atende)

    def test_calculo_modo_A(self):
        res = g.verificar_sapata_centrada(entrada_sc01(
            Metodo.CALCULO, sigma_r_k=None, metodo_resistencia=None,
            declaracao_sem_ponderacao_parametros=None, sigma_Rd=400.0,
            procedimento_7_3=(Procedimento73.ANALITICO_7_3_2,)))
        self.assertFalse(res.recusado)
        self.assertEqual(res.grandeza("geotecnico.sigma_Rd").valor, 400.0)
        self.assertTrue(res.verificacao(g.REGRA_VERIF_CALCULO).atende)
        self.assertTrue(res.verificacao(g.REGRA_ELU_ELS).atende)

    def test_sem_veredito_global(self):
        res = g.verificar_sapata_centrada(entrada())
        campos = {f.name for f in dataclasses.fields(res)}
        for proibido in ("aprovada", "aprovado", "ok", "passou", "veredito"):
            self.assertNotIn(proibido, campos)
        textos = [n.texto for n in res.nao_verificado]
        self.assertTrue(any("7.7.1" in t for t in textos))
        self.assertTrue(any("6.2.1 a)" in t for t in textos))


# =============================================================================
# Tensao de referencia (7.3/7.4), Tabela 1, ELU+ELS
# =============================================================================
class TestTensaoDeReferencia(unittest.TestCase, AssertRecusa):
    R = g.REGRA_TENSAO_REFERENCIA

    def test_rejeicoes_modo_A_admissivel(self):
        casos = (
            dict(procedimento_7_3=None),
            dict(procedimento_7_3=()),
            dict(declaracao_ELS_atendido=False),
            dict(declaracao_ELS_atendido=None),
            dict(declaracao_fatores_7_2=False),
            dict(sigma_adm=None),
            dict(sigma_adm=0.0),
            dict(sigma_r_k=890.0),
        )
        for kw in casos:
            self.assertRecusado(g.verificar_sapata_centrada(entrada(**kw)), self.R)

    def test_sigma_ELS_nao_se_aplica_ao_modo_A_admissivel(self):
        self.assertRecusado(g.verificar_sapata_centrada(entrada(sigma_ELS=300.0)),
                            g.REGRA_ELU_ELS)

    def test_tensao_de_outro_metodo_recusa(self):
        self.assertRecusado(g.verificar_sapata_centrada(entrada(sigma_Rd=300.0)), g.REQ_METODO)
        self.assertRecusado(g.verificar_sapata_centrada(entrada_sc01(
            Metodo.CALCULO, sigma_adm=300.0)), g.REQ_METODO)

    def test_calculo_sem_sigma_ELS_recusa(self):
        self.assertRecusado(g.verificar_sapata_centrada(entrada_sc01(Metodo.CALCULO,
                                                                     sigma_ELS=None)),
                            g.REGRA_ELU_ELS)

    def test_metodo_ausente_recusa(self):
        self.assertRecusado(g.verificar_sapata_centrada(entrada(metodo=None)), g.REQ_METODO)
        self.assertRecusado(g.verificar_sapata_centrada(entrada(metodo="admissivel")),
                            g.REQ_METODO)

    def test_admissivel_modo_B_ELS_governa(self):
        res = g.verificar_sapata_centrada(entrada_sc01(Metodo.ADMISSIVEL, sigma_ELS=250.0))
        self.assertEqual(res.grandeza("geotecnico.sigma_adm").valor, 250.0)
        self.assertAlmostEqual(res.grandeza("geotecnico.sigma_adm_ELU").valor, 890.0 / 3.0)
        self.assertFalse(res.verificacao(g.REGRA_VERIF_ADMISSIVEL).atende)


class TestTabela1(unittest.TestCase):
    rk = Tensao(900.0, K)

    def test_analitico(self):
        s, c = g.tensao_limite_ELU_tabela1(Metodo.ADMISSIVEL, self.rk, MetodoResistencia.ANALITICO,
                                           declaracao_sem_ponderacao_parametros=True)
        self.assertEqual((s, c), (Tensao(300.0, K), 3.0))
        s, c = g.tensao_limite_ELU_tabela1(Metodo.CALCULO, self.rk, MetodoResistencia.ANALITICO,
                                           declaracao_sem_ponderacao_parametros=True)
        self.assertEqual(c, 2.15)
        self.assertIs(s.natureza, D)

    def test_com_provas_de_carga(self):
        s, c = g.tensao_limite_ELU_tabela1(
            Metodo.ADMISSIVEL, self.rk, MetodoResistencia.COM_PROVAS_DE_CARGA,
            n_provas_de_carga=2, declaracao_provas_fase_projeto_7_3_1=True)
        self.assertEqual((s.valor_kPa, c), (450.0, 2.0))
        s, c = g.tensao_limite_ELU_tabela1(
            Metodo.CALCULO, self.rk, MetodoResistencia.COM_PROVAS_DE_CARGA,
            n_provas_de_carga=3, declaracao_provas_fase_projeto_7_3_1=True)
        self.assertEqual(c, 1.4)

    def test_semiempirico_borda_minimo(self):
        s, c = g.tensao_limite_ELU_tabela1(
            Metodo.ADMISSIVEL, self.rk, MetodoResistencia.SEMIEMPIRICO, FS_g_proposto=3.0,
            declaracao_dominio_validade_semiempirico=True)
        self.assertEqual(s.valor_kPa, 300.0)
        s, c = g.tensao_limite_ELU_tabela1(
            Metodo.CALCULO, self.rk, MetodoResistencia.SEMIEMPIRICO, gamma_m_proposto=2.15,
            declaracao_dominio_validade_semiempirico=True)
        self.assertEqual(c, 2.15)
        s, c = g.tensao_limite_ELU_tabela1(
            Metodo.ADMISSIVEL, self.rk, MetodoResistencia.SEMIEMPIRICO, FS_g_proposto=4.5,
            declaracao_dominio_validade_semiempirico=True)
        self.assertEqual(s.valor_kPa, 200.0)

    def test_rejeicoes(self):
        A, C = Metodo.ADMISSIVEL, Metodo.CALCULO
        SE, AN, PC = (MetodoResistencia.SEMIEMPIRICO, MetodoResistencia.ANALITICO,
                      MetodoResistencia.COM_PROVAS_DE_CARGA)
        casos = (
            (A, SE, dict(FS_g_proposto=2.99, declaracao_dominio_validade_semiempirico=True)),
            (C, SE, dict(gamma_m_proposto=2.14, declaracao_dominio_validade_semiempirico=True)),
            (A, SE, dict(FS_g_proposto=3.0, declaracao_dominio_validade_semiempirico=False)),
            (A, SE, dict(declaracao_dominio_validade_semiempirico=True)),
            (A, SE, dict(gamma_m_proposto=2.15, FS_g_proposto=3.0,
                         declaracao_dominio_validade_semiempirico=True)),
            (C, SE, dict(FS_g_proposto=3.0, gamma_m_proposto=2.15,
                         declaracao_dominio_validade_semiempirico=True)),
            (A, AN, dict(declaracao_sem_ponderacao_parametros=False)),
            (A, AN, dict(declaracao_sem_ponderacao_parametros=True, FS_g_proposto=3.5)),
            (A, PC, dict(n_provas_de_carga=1, declaracao_provas_fase_projeto_7_3_1=True)),
            (A, PC, dict(n_provas_de_carga=2.0, declaracao_provas_fase_projeto_7_3_1=True)),
            (A, PC, dict(n_provas_de_carga=2, declaracao_provas_fase_projeto_7_3_1=False)),
            (A, PC, dict(declaracao_provas_fase_projeto_7_3_1=True)),
            (A, None, dict()),
        )
        for metodo, linha, kw in casos:
            with self.assertRaises(Recusa, msg=f"{metodo} {linha} {kw}"):
                g.tensao_limite_ELU_tabela1(metodo, self.rk, linha, **kw)
        with self.assertRaises(ErroMisturaDeMetodo):
            g.tensao_limite_ELU_tabela1(A, Tensao(900.0, D), AN,
                                        declaracao_sem_ponderacao_parametros=True)

    def test_ELU_ELS_admissivel(self):
        self.assertEqual(g.tensao_admissivel_ELU_ELS(Tensao(296.0, K), Tensao(300.0, K)),
                         Tensao(296.0, K))
        self.assertEqual(g.tensao_admissivel_ELU_ELS(Tensao(300.0, K), Tensao(300.0, K)),
                         Tensao(300.0, K))
        with self.assertRaises(ErroMisturaDeMetodo):
            g.tensao_admissivel_ELU_ELS(Tensao(413.0, D), Tensao(300.0, K))


# =============================================================================
# RT-01 / determinismo / rastreabilidade
# =============================================================================
class TestRT01(unittest.TestCase):
    def test_mistura_de_naturezas_levanta(self):
        with self.assertRaises(ErroMisturaDeMetodo):
            Tensao(1.0, K) <= Tensao(2.0, D)
        with self.assertRaises(ErroMisturaDeMetodo):
            min(Tensao(1.0, K), Tensao(2.0, D))
        with self.assertRaises(ErroMisturaDeMetodo):
            Forca(1.0, K) + Forca(2.0, D)
        with self.assertRaises(TypeError):
            Forca(1.0, K) + Tensao(2.0, K)


class TestDeterminismo(unittest.TestCase):
    def test_mesma_entrada_mesma_saida(self):
        for e in (entrada(), entrada_sc01(Metodo.ADMISSIVEL), entrada_sc01(Metodo.CALCULO),
                  entrada(M_x=1.0)):
            self.assertEqual(g.verificar_sapata_centrada(e), g.verificar_sapata_centrada(e))


class TestRastreabilidade(unittest.TestCase):
    """Gate do A6 antecipado: docstring com item, pagina e [rule: id] APROVADA."""

    @classmethod
    def setUpClass(cls):
        import yaml
        texto = (RAIZ / "ruleset.yaml").read_bytes()
        cls.ruleset_bytes = texto
        dados = yaml.safe_load(texto)
        cls.aprovadas = {r["id"] for r in dados["regras"] if r["status"] == "APROVADA"}
        cls.bloqueadas = {r["id"] for r in dados["fora_do_escopo_v0"]}

    def test_ruleset_congelado_confere_com_lock(self):
        lock = (RAIZ / "ruleset.lock").read_text(encoding="utf-8")
        esperado = re.search(r"^sha256:\s*([0-9a-f]{64})", lock, re.M).group(1)
        self.assertEqual(hashlib.sha256(self.ruleset_bytes).hexdigest(), esperado)

    def _publicos(self):
        for nome, obj in vars(g).items():
            if nome.startswith("_"):
                continue
            if getattr(obj, "__module__", None) != g.__name__:
                continue
            if inspect.isfunction(obj) or inspect.isclass(obj):
                yield nome, obj
                if inspect.isclass(obj):
                    for mn, m in vars(obj).items():
                        if inspect.isfunction(m) and not mn.startswith("_"):
                            yield f"{nome}.{mn}", m

    def test_toda_funcao_publica_tem_referencia_e_regra_aprovada(self):
        vistos = 0
        for nome, obj in self._publicos():
            vistos += 1
            doc = inspect.getdoc(obj) or ""
            self.assertIn("ABNT NBR 6122:2022", doc, nome)
            self.assertRegex(doc, r"\bp\. \d+", nome)
            self.assertRegex(doc, r"\bite(m|ns)\b", nome)
            ids = re.findall(r"\[rule: ([^\]]+)\]", doc)
            self.assertTrue(ids, f"{nome} sem [rule: ...]")
            for i in ids:
                self.assertIn(i, self.aprovadas, f"{nome}: regra '{i}' nao APROVADA")
        self.assertGreater(vistos, 20)

    def test_constantes_de_regra_existem_no_ruleset(self):
        for nome, valor in vars(g).items():
            if nome.startswith("REGRA_"):
                self.assertIn(valor, self.aprovadas, nome)

    def test_constantes_normativas_conferem_com_ruleset(self):
        import yaml
        dados = yaml.safe_load(self.ruleset_bytes)
        r = {x["id"]: x for x in dados["regras"]}
        self.assertEqual(g.FRAC_MIN_PESO_PROPRIO,
                         r[g.REGRA_PESO_PROPRIO]["constantes"]["frac_min_pp"]["valor"])
        self.assertEqual(g.GAMMA_F_6122_T1C,
                         r[g.REGRA_GAMMA_F]["constantes_nomeadas"]["GAMMA_F_6122_T1C"]["valor"])
        t = r[g.REGRA_TABELA1]["tabela"]
        self.assertEqual(g.FS_G_MIN_SEMIEMPIRICO, t["semiempirico"]["FS_g"]["minimo"])
        self.assertEqual(g.GAMMA_M_MIN_SEMIEMPIRICO, t["semiempirico"]["gamma_m"]["minimo"])
        self.assertEqual(g.FS_G_ANALITICO, t["analitico"]["FS_g"]["valor"])
        self.assertEqual(g.GAMMA_M_ANALITICO, t["analitico"]["gamma_m"]["valor"])
        self.assertEqual(g.FS_G_COM_PROVAS_DE_CARGA, t["com_provas_de_carga"]["FS_g"]["valor"])
        self.assertEqual(g.GAMMA_M_COM_PROVAS_DE_CARGA,
                         t["com_provas_de_carga"]["gamma_m"]["valor"])

    def test_modulos_bloqueados_nao_existem(self):
        for nome in ("capacidade", "semiempirico", "prova_carga", "recalques", "vento"):
            self.assertFalse((RAIZ / "calc_core" / "geotecnico" / f"{nome}.py").exists(), nome)


if __name__ == "__main__":
    unittest.main()
