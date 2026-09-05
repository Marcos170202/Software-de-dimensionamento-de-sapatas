"""Suíte de sanidade original do pacote sapata_isolada (fornecida pelo
usuário), adaptada para pytest e para o caminho de import deste repositório
(calc_core.sapata_isolada). Mantida como está — é a regressão de referência
do próprio autor do pacote, complementar a
test_sapata_isolada_correcoes.py (que cobre especificamente os 6 defeitos
encontrados na auditoria contra a NBR 6118)."""
import math

import pytest

from calc_core.sapata_isolada import *  # noqa: F403 (mesma forma do original)
from calc_core.sapata_isolada.geotecnia import influencia_canto_retangulo
from calc_core.sapata_isolada.recalques import (
    fator_tempo,
    fator_influencia_iw,
    grau_adensamento,
)


def _aprox(a, b, tol=0.02):
    assert abs(a - b) <= tol * max(abs(b), 1e-9), f"{a} != {b}"


def test_boussinesq_canto_e_dissipacao_em_profundidade():
    _aprox(influencia_canto_retangulo(10, 10), 0.25, 0.02)
    _aprox(acrescimo_tensao_centro(100, 2, 2, 0.001), 100, 0.02)
    assert acrescimo_tensao_centro(100, 2, 2, 20) < 2


def test_adensamento_normalmente_adensado():
    h = recalque_adensamento(2.0, 1.0, 0.4, 0.07, 100.0, 100.0)
    _aprox(h, 2.0 * 0.4 / 2.0 * math.log10(2.0), 0.001)


def test_fator_tempo_e_grau_de_adensamento_ida_e_volta():
    for U in (0.3, 0.5, 0.6, 0.8, 0.9):
        _aprox(grau_adensamento(fator_tempo(U)), U, 0.02)
    _aprox(fator_tempo(0.90), 0.848, 0.02)


def test_iw_interpolado():
    _aprox(fator_influencia_iw(1.0, "centro"), 1.12, 0.001)
    _aprox(fator_influencia_iw(2.0, "rigido"), 1.20, 0.001)


@pytest.mark.parametrize("fck,esperado", [(20, 44.0), (25, 38.0), (30, 33.0)])
def test_ancoragem_ca50_valores_classicos_de_tabela(fck, esperado):
    lb = comprimento_ancoragem_basico(10.0, Concreto(fck), Aco(500), True)
    _aprox(lb / 0.010, esperado, 0.03)


def test_sapata_centrada_dimensao_bate_com_N_sobre_sigma_adm():
    pilar = Pilar(ap=0.30, bp=0.30)
    solo = Solo(sigma_adm=200.0, hf=1.5)
    combs = gerar_combinacoes([CasoCarga("G", Esforcos(N=500.0))])
    s = Sapata(pilar, solo, Concreto(25), Aco(500), combs, 0.045,
               OpcoesProjeto(verificar_recalque=False))
    r = s.dimensionar()
    assert r.a == r.b, (r.a, r.b)
    assert r.aprovado, r.alertas
    assert abs(r.a - 1.75) < 0.11, r.a
    assert r.h >= (r.a - 0.30) / 3 - 1e-9


def test_carga_excentrica_alta_secao_parcialmente_comprimida():
    pilar = Pilar(ap=0.30, bp=0.30)
    solo = Solo(sigma_adm=200.0, hf=1.5)
    combs2 = gerar_combinacoes([CasoCarga("G", Esforcos(N=300.0, My=200.0))])
    s2 = Sapata(pilar, solo, Concreto(25), Aco(500), combs2, 0.045,
                OpcoesProjeto(verificar_recalque=False, area_comprimida_minima=0.5))
    r2 = s2.dimensionar()
    assert r2.a > r2.b, (r2.a, r2.b)
