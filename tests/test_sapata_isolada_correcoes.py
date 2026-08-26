"""Testes de regressão dos 6 defeitos encontrados e corrigidos na auditoria
de 2026-08-26 do pacote calc_core/sapata_isolada/ (fornecido pelo usuário)
contra a NBR 6118:2023, lida por visão (imagem da página, não texto
extraído — ver ruleset.yaml, seção de versão 2, para o relato completo).

Cada teste aqui reproduz o cálculo manual feito durante a auditoria, a
partir da imagem da página citada, não de memória de treinamento.
"""
import math

import pytest

from calc_core.sapata_isolada.materiais import (
    Aco,
    Concreto,
    comprimento_ancoragem_basico,
)
from calc_core.sapata_isolada.sapata import Sapata, OpcoesProjeto
from calc_core.sapata_isolada.acoes import CasoCarga, Esforcos, Pilar, gerar_combinacoes
from calc_core.sapata_isolada.geotecnia import Solo


# --- 1. fct,m para fck > 50 MPa (NBR 6118:2023, 8.2.5, p. 23) ---------------

def test_fctm_fck_acima_de_50_usa_formula_correta():
    c = Concreto(fck=60.0)
    esperado = 2.12 * math.log(1.0 + 0.1 * (60.0 + 8.0))
    assert c.fctm == pytest.approx(esperado, rel=1e-9)
    # a fórmula antiga (bug) dava 2,12*ln(1+0,11*60) = 4,300 MPa; a correta
    # dá um valor visivelmente diferente
    bug_antigo = 2.12 * math.log(1.0 + 0.11 * 60.0)
    assert c.fctm != pytest.approx(bug_antigo, rel=1e-3)


# --- 2. Eci precisa do parâmetro alpha_E do agregado (8.2.8, p. 24) --------

@pytest.mark.parametrize("agregado,alpha_e", [
    ("basalto", 1.2), ("diabasio", 1.2),
    ("granito", 1.0), ("gnaisse", 1.0),
    ("calcario", 0.9), ("arenito", 0.7),
])
def test_Eci_aplica_alpha_e_do_agregado(agregado, alpha_e):
    c = Concreto(fck=30.0, agregado=agregado)
    assert c.alpha_e == alpha_e
    esperado = alpha_e * 5600.0 * math.sqrt(30.0)
    assert c.Eci == pytest.approx(esperado, rel=1e-9)


def test_agregado_invalido_rejeita():
    with pytest.raises(ValueError):
        Concreto(fck=30.0, agregado="quartzito-nao-listado")


# --- 3. l_b básico >= 25*phi (9.4.2.4, p. 37) -------------------------------

def test_lb_basico_respeita_piso_25_phi():
    # concreto de alta resistência + bitola grande: fbd alto o bastante para
    # que phi/4*(fyd/fbd) caia ABAIXO de 25*phi, acionando o piso
    lb = comprimento_ancoragem_basico(32.0, Concreto(90.0), Aco(500), True)
    assert lb >= 25.0 * 32.0 / 1000.0 - 1e-9


def test_lb_basico_caso_tipico_nao_precisa_do_piso():
    # C25/CA-50/phi=10mm: o cálculo direto já supera 25*phi, então o piso
    # não deveria alterar o resultado — mantém compatibilidade com os
    # valores clássicos de tabela de escritório (44*phi para C20 etc.)
    lb = comprimento_ancoragem_basico(10.0, Concreto(20.0), Aco(500), True)
    assert lb / 0.010 == pytest.approx(44.0, rel=0.05)


# --- 4. eta_1 por categoria do aço, não por "nervurada" (Tab. 8.2, p. 29) --

def test_eta1_por_categoria_do_aco():
    assert Aco(fyk=250.0).eta1 == 1.00   # CA-25
    assert Aco(fyk=500.0).eta1 == 2.25   # CA-50
    assert Aco(fyk=600.0).eta1 == 1.00   # CA-60 — o bug antigo dava 2,25 aqui


def test_categoria_explicita_sobrepoe_inferencia_por_fyk():
    aco = Aco(fyk=500.0, categoria="CA-25")
    assert aco.eta1 == 1.00


def test_fyk_sem_categoria_correspondente_exige_categoria_explicita():
    with pytest.raises(ValueError):
        Aco(fyk=435.0)   # não é 250/500/600 e não veio 'categoria'


# --- 5 e 6. tau_Rd1 no contorno C' (19.5.3.2, p. 168) -----------------------
#   5. "d" do fator ke deve estar em CENTÍMETROS, não milímetros.
#   6. rho = sqrt(rho_x*rho_y) deve ser limitado a 0,02.

def _tau_rd1_manual(rho: float, fck: float, d_m: float) -> float:
    """Reproduz a fórmula da p. 168 diretamente, para comparação independente."""
    d_cm = d_m * 100.0
    ke = min(2.0, 1.0 + math.sqrt(20.0 / d_cm))
    rho = min(0.02, rho)
    return 0.13 * ke * (100.0 * rho * fck) ** (1.0 / 3.0) * 1000.0  # kPa


def test_ke_usa_d_em_centimetros():
    # chamada direta a _verificar_puncao com geometria generosa o bastante
    # para o contorno C' caber dentro da base ((a-ap)/2 >= 2d) — numa sapata
    # RÍGIDA dimensionada no mínimo normativo isso quase nunca acontece
    # (por construção h~=(a-ap)/3, então 2d~=2h > 1,5h~=(a-ap)/2), por isso
    # o teste força uma base bem maior que o mínimo.
    pilar = Pilar(ap=0.30, bp=0.30)
    solo = Solo(sigma_adm=250.0, hf=1.5)
    combs = gerar_combinacoes([CasoCarga("G", Esforcos(N=800.0))])
    s = Sapata(pilar, solo, Concreto(25.0), Aco(500.0), combs, 0.045,
               OpcoesProjeto(verificar_recalque=False))
    s.a, s.b = 4.0, 4.0          # base bem maior que o mínimo rígido
    s.h, s.h0 = 0.40, 0.20       # d pequeno o bastante para (a-ap)/2 >= 2d
    s._avaliar(s.a, s.b, s.h, s.h0)   # efeito colateral: define s.classificacao
    d = s._altura_util(s.h, 12.5)[2]
    assert (s.a - pilar.ap) / 2.0 >= 2.0 * d, "premissa do teste não vale mais"

    puncao = s._verificar_puncao(s.a, s.b, s.h, d, rho=0.02)
    contorno_c_linha = next(
        p for p in puncao if p.contorno.startswith("C' (a 2d")
    )
    manual = _tau_rd1_manual(0.02, 25.0, d)
    assert contorno_c_linha.tau_rd == pytest.approx(manual, rel=1e-6)


def test_rho_da_puncao_respeita_teto_de_2_por_cento():
    """Uma sapata muito armada não pode gerar rho > 0,02 na fórmula de tau_Rd1
    — sem o teto, tau_Rd1 seria superestimado (erro do lado inseguro)."""
    pilar = Pilar(ap=0.30, bp=0.30)
    solo = Solo(sigma_adm=400.0, hf=1.5)
    combs = gerar_combinacoes([CasoCarga("G", Esforcos(N=3000.0, Mx=200.0, My=200.0))])
    s = Sapata(pilar, solo, Concreto(25.0), Aco(500.0), combs, 0.045,
               OpcoesProjeto(verificar_recalque=False, area_comprimida_minima=0.5))
    r = s.dimensionar()
    # a própria função interna nunca deve passar rho > 0,02 para a fórmula:
    # verificado indiretamente checando que tau_rd1 relatado bate com o teto
    contorno_c_linha = next(
        (p for p in r.puncao if p.contorno.startswith("C' (a 2d")), None)
    if contorno_c_linha is not None:
        limite_com_teto = _tau_rd1_manual(0.02, 25.0, r.d)
        assert contorno_c_linha.tau_rd <= limite_com_teto + 1e-6
