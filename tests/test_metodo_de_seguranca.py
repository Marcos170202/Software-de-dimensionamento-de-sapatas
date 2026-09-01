"""Testes de calc_core.geotecnico.seguranca (Tabela 1 e guarda de método).

REQ-SIGMA-01 é a guarda que existe porque esta é a primeira versão em que
``calc_core`` ESCOLHE um método de segurança em vez de receber sigma_adm
pronto. As três proibições viram teste, uma a uma:

(a) aplicar gamma_m a um resultado desta versão;
(b) comparar sigma_adm contra solicitação em valores de CÁLCULO;
(c) aplicar gamma_f = 1,4 na ação E dividir a resistência por FSg.
"""
import pytest

from calc_core.geotecnico.seguranca import (BASE_CARACTERISTICA,
                                            BASE_DE_CALCULO,
                                            FSG_ANALITICOS,
                                            FSG_COM_DUAS_OU_MAIS_PROVAS_DE_CARGA,
                                            FSG_MINIMO_SEMIEMPIRICOS,
                                            MetodoDeSegurancaError,
                                            comparar_com_tensao_atuante,
                                            exigir_ausencia_de_ponderacao,
                                            exigir_metodo_admissivel,
                                            exigir_solicitacao_caracteristica,
                                            fator_de_seguranca_global)


# --- Guarda de método (REQ-SIGMA-01) --------------------------------------

def test_metodo_admissivel_e_o_unico_aceito():
    assert exigir_metodo_admissivel("admissivel") == "admissivel"
    for proibido in ("calculo", "valores_de_calculo", "", "ADMISSIVEL"):
        with pytest.raises(MetodoDeSegurancaError):
            exigir_metodo_admissivel(proibido)


def test_proibicao_a_gamma_m_nao_pode_ser_aplicado():
    """A rota de valores de cálculo NÃO está implementada."""
    exigir_ausencia_de_ponderacao()          # nada aplicado: passa
    with pytest.raises(MetodoDeSegurancaError) as erro:
        exigir_ausencia_de_ponderacao(gamma_m_aplicado=True)
    assert "gamma_m" in str(erro.value)


def test_proibicao_b_solicitacao_de_calculo_nao_se_compara_com_sigma_adm():
    assert exigir_solicitacao_caracteristica(BASE_CARACTERISTICA) == (
        BASE_CARACTERISTICA)
    with pytest.raises(MetodoDeSegurancaError):
        exigir_solicitacao_caracteristica(BASE_DE_CALCULO)
    with pytest.raises(MetodoDeSegurancaError):
        comparar_com_tensao_atuante(300.0, 250.0,
                                    base_da_solicitacao=BASE_DE_CALCULO)


def test_proibicao_c_gamma_f_na_acao_mais_FSg_e_dupla_contagem():
    """As duas colunas da Tabela 1 são alternativas: 3,00/2,15 ~= 1,4."""
    with pytest.raises(MetodoDeSegurancaError) as erro:
        comparar_com_tensao_atuante(300.0, 250.0,
                                    base_da_solicitacao=BASE_CARACTERISTICA,
                                    gamma_f_aplicado_na_acao=True)
    assert "dupla contagem" in str(erro.value)
    assert FSG_ANALITICOS / 2.15 == pytest.approx(1.4, abs=0.005)


def test_comparacao_licita_devolve_verificacao_com_o_rotulo_de_ELU():
    ok = comparar_com_tensao_atuante(300.0, 250.0,
                                     base_da_solicitacao=BASE_CARACTERISTICA)
    assert ok.ok is True
    assert ok.regra == "NBR6122-6.2.1.1.1-fatores-seguranca-tabela1"
    assert "§7.4 (ELS/recalque) NÃO verificado" in ok.mensagem

    nao_ok = comparar_com_tensao_atuante(300.0, 320.0,
                                         base_da_solicitacao=BASE_CARACTERISTICA)
    assert nao_ok.ok is False

    # Igualdade passa: a Norma exige "<=", não "<".
    limite = comparar_com_tensao_atuante(300.0, 300.0,
                                         base_da_solicitacao=BASE_CARACTERISTICA)
    assert limite.ok is True


# --- Tabela 1 (as três linhas, com as redações diferentes) ----------------

def test_linha_analiticos_e_fixa_em_3_sem_no_minimo():
    fs = fator_de_seguranca_global("analitico")
    assert fs.valor == FSG_ANALITICOS == 3.00
    assert fs.linha_da_tabela_1 == "Analíticos (b)"
    with pytest.raises(MetodoDeSegurancaError):
        fator_de_seguranca_global("analitico", FS_proposto_pelo_processo=4.0)


def test_linha_semiempiricos_tem_3_como_PISO_e_nao_como_constante():
    """"Valores propostos no próprio processo E no mínimo 3,00"."""
    assert fator_de_seguranca_global(
        "semiempirico", FS_proposto_pelo_processo=3.0).valor == 3.00
    assert fator_de_seguranca_global(
        "semiempirico", FS_proposto_pelo_processo=2.0).valor == (
            FSG_MINIMO_SEMIEMPIRICOS)
    assert fator_de_seguranca_global(
        "semiempirico", FS_proposto_pelo_processo=4.55).valor == 4.55


def test_linha_das_provas_de_carga_exige_as_duas_condicoes():
    completo = fator_de_seguranca_global(
        "analitico", n_provas_de_carga=2,
        provas_executadas_na_fase_de_projeto=True)
    assert completo.valor == FSG_COM_DUAS_OU_MAIS_PROVAS_DE_CARGA == 2.00

    for kwargs in (dict(n_provas_de_carga=1,
                        provas_executadas_na_fase_de_projeto=True),
                   dict(n_provas_de_carga=5,
                        provas_executadas_na_fase_de_projeto=False)):
        assert fator_de_seguranca_global("analitico", **kwargs).valor == 3.00


def test_recusa_origem_desconhecida_e_entradas_invalidas():
    with pytest.raises(ValueError):
        fator_de_seguranca_global("prova_de_carga")
    with pytest.raises(ValueError):
        fator_de_seguranca_global("analitico", n_provas_de_carga=-1)
    with pytest.raises(MetodoDeSegurancaError):
        fator_de_seguranca_global("analitico", metodo_de_seguranca="calculo")
