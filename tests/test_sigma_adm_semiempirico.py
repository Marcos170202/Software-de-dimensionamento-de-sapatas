"""Testes de calc_core.geotecnico.semiempirico e .sigma_adm (caminho SPT).

Famílias:

1. VALOR CONHECIDO — os números de ``checagem_numerica`` do ruleset, que o a2
   calculou de forma independente.
2. BORDA — os quatro extremos de cada domínio declarado, todos ACEITOS
   (intervalo fechado), e o primeiro valor fora, RECUSADO.
3. REJEIÇÃO — uma guarda por teste, incluindo as duas armadilhas de unidade
   que a análise dimensional não pega (REQ-SIGMA-03).
4. METADADO EXECUTÁVEL — FS embutido devolvido e conferido em execução
   (REQ-SIGMA-02) e rótulo de ELU colado ao número (REQ-SIGMA-09).
"""
import pytest

from calc_core.geotecnico.dominio import (ADOTADO_DA_EXTENSAO_DE_FIGURA,
                                          DECLARADO_EM_TEXTO,
                                          ForaDoDominioError)
from calc_core.geotecnico.seguranca import (MetodoDeSegurancaError,
                                            fator_de_seguranca_global)
from calc_core.geotecnico.semiempirico import (FS_EMBUTIDO_REGRA_50,
                                               FS_EMBUTIDO_TEIXEIRA,
                                               regra_brasileira_nspt_50_argila,
                                               teixeira_1996_areia)
from calc_core.geotecnico.sigma_adm import semiempirico_spt
from calc_core.modelos import EntradaSemiempiricaSPT


def _argila(**kwargs):
    base = dict(N_spt_medio_bulbo=15.0, forma="quadrada",
                solo_declarado="argila",
                aplicabilidade_regional_declarada=True)
    base.update(kwargs)
    return regra_brasileira_nspt_50_argila(**base)


def _areia(**kwargs):
    base = dict(N_spt=15.0, B_m=2.0, forma="quadrada", solo_declarado="areia",
                h_m=1.5, gamma_kN_m3=18.0,
                aplicabilidade_regional_declarada=True)
    base.update(kwargs)
    return teixeira_1996_areia(**base)


# --- 1. Valores conhecidos -------------------------------------------------

def test_regra_50_no_caso_tipico_do_ruleset():
    """N_SPT = 15, q desligado: 0,300 MPa = 300 kPa."""
    resultado = _argila()
    assert resultado.sigma_adm_ELU_kPa == pytest.approx(300.0, abs=1e-9)
    assert resultado.memoria["sigma_a_MPa"] == pytest.approx(0.300)
    assert resultado.memoria["q_MPa"] == 0.0


def test_teixeira_no_caso_tipico_do_ruleset():
    """N_SPT = 15, B = 2 m: 0,05 + 1,8·0,15 = 0,320 MPa = 320 kPa."""
    resultado = _areia()
    assert resultado.sigma_adm_ELU_kPa == pytest.approx(320.0, abs=1e-9)


def test_dispersao_medida_pelo_a2_entre_as_duas_correlacoes():
    """N_SPT = 15, B = 2 m: 300 kPa (argila) e 320 kPa (areia) — 6,7 %.

    Os dois números vêm de domínios de solo mutuamente exclusivos e por isso
    NUNCA aparecem juntos num mesmo caso; o teste fixa os dois valores que o
    a2 mediu, para travar a transcrição das duas fórmulas.
    """
    assert _argila().sigma_adm_ELU_kPa == pytest.approx(300.0)
    assert _areia().sigma_adm_ELU_kPa == pytest.approx(320.0)


def test_monotonicidade_das_duas_correlacoes():
    """Crescentes em N_SPT (as duas) e em B (Teixeira), como a Fig. 4.1."""
    argila = [_argila(N_spt_medio_bulbo=n).sigma_adm_ELU_kPa
              for n in (5.0, 10.0, 15.0, 20.0)]
    assert argila == sorted(argila)
    areia_n = [_areia(N_spt=n).sigma_adm_ELU_kPa
               for n in (4.0, 10.0, 20.0, 25.0)]
    assert areia_n == sorted(areia_n)
    areia_B = [_areia(B_m=b).sigma_adm_ELU_kPa for b in (1.0, 2.0, 3.0)]
    assert areia_B == sorted(areia_B)


# --- 2. Bordas do domínio (fechado nos dois extremos) ----------------------

def test_bordas_da_regra_50_sao_aceitas():
    """N = 5 -> 100 kPa; N = 20 -> 400 kPa (contornos do ruleset)."""
    assert _argila(N_spt_medio_bulbo=5.0).sigma_adm_ELU_kPa == pytest.approx(100.0)
    assert _argila(N_spt_medio_bulbo=20.0).sigma_adm_ELU_kPa == pytest.approx(400.0)


def test_bordas_de_teixeira_sao_aceitas():
    """B = 1 m/N = 4 -> 106 kPa; B = 3 m/N = 25 -> 600 kPa."""
    assert _areia(B_m=1.0, N_spt=4.0).sigma_adm_ELU_kPa == pytest.approx(106.0)
    assert _areia(B_m=3.0, N_spt=25.0).sigma_adm_ELU_kPa == pytest.approx(600.0)


def test_forma_retangular_e_aceita_na_regra_50_e_recusada_em_teixeira():
    """A dedução da regra N/50 é retangular; a de Teixeira é quadrada."""
    assert _argila(forma="retangular").sigma_adm_ELU_kPa == pytest.approx(300.0)
    with pytest.raises(ForaDoDominioError) as erro:
        _areia(forma="retangular")
    assert erro.value.parametro == "forma"


# --- 3. Rejeição fora do domínio ------------------------------------------

@pytest.mark.parametrize("n_spt", [4.9, 20.1, 0.0, 25.0, 50.0])
def test_regra_50_recusa_nspt_fora_de_5_a_20(n_spt):
    """Faixa DECLARADA EM TEXTO na fonte — nem aproxima, nem clampa."""
    with pytest.raises(ForaDoDominioError) as erro:
        _argila(N_spt_medio_bulbo=n_spt)
    assert erro.value.parametro == "N_spt_medio_bulbo"
    assert erro.value.forca == DECLARADO_EM_TEXTO
    assert "5.0 a 20.0" in erro.value.intervalo


def test_regra_50_nao_clampa_como_a_funcao_substituida_fazia():
    """Regressão contra o defeito de `sigma_adm_por_spt` (removida na v9).

    A função antiga fazia ``max(5, min(20, n))`` e devolvia 400 kPa para
    N_SPT = 50 — número plausível, sem procedência. Aqui é recusa.
    """
    with pytest.raises(ForaDoDominioError):
        _argila(N_spt_medio_bulbo=50.0)


@pytest.mark.parametrize("n_spt", [3.9, 25.1])
def test_teixeira_recusa_nspt_fora_da_extensao_da_figura(n_spt):
    """Limite ADOTADO da Fig. 4.1: recusa igual, força menor e revisável."""
    with pytest.raises(ForaDoDominioError) as erro:
        _areia(N_spt=n_spt)
    assert erro.value.forca == ADOTADO_DA_EXTENSAO_DE_FIGURA


@pytest.mark.parametrize("B_m", [0.9, 3.1, 200.0])
def test_teixeira_recusa_B_fora_de_1_a_3_metros(B_m):
    """B = 200 daria 12,2 MPa: é a guarda de unidade (cm em vez de m)."""
    with pytest.raises(ForaDoDominioError) as erro:
        _areia(B_m=B_m)
    assert erro.value.parametro == "B_m"


@pytest.mark.parametrize("h_m", [1.4999999, 1.5000001, 1.0, 3.0])
def test_teixeira_recusa_h_diferente_de_1_5_com_tolerancia_zero(h_m):
    """h é hipótese CONGELADA: h = 3,0 m moveria o resultado 59 %."""
    with pytest.raises(ForaDoDominioError) as erro:
        _areia(h_m=h_m)
    assert erro.value.parametro == "h_m"


@pytest.mark.parametrize("gamma", [17.9, 18.1, 20.0])
def test_teixeira_recusa_gamma_diferente_de_18_com_tolerancia_zero(gamma):
    with pytest.raises(ForaDoDominioError) as erro:
        _areia(gamma_kN_m3=gamma)
    assert erro.value.parametro == "gamma_kN_m3"


def test_recusa_solo_fora_do_declarado_por_cada_correlacao():
    """"Puramente argiloso" e "areia" são literais da fonte."""
    with pytest.raises(ForaDoDominioError):
        _argila(solo_declarado="areia")
    with pytest.raises(ForaDoDominioError):
        _argila(solo_declarado="silte")
    with pytest.raises(ForaDoDominioError):
        _areia(solo_declarado="areia argilosa")


def test_recusa_sem_declaracao_regional():
    """Obrigação (c) do §7.3.3 — sem default afirmativo (REQ-SIGMA-06)."""
    for chamada in (_argila, _areia):
        with pytest.raises(ForaDoDominioError) as erro:
            chamada(aplicabilidade_regional_declarada=False)
        assert erro.value.parametro == "aplicabilidade_regional_declarada"


def test_recusa_q_em_kPa_disfarcado_de_MPa():
    """REQ-SIGMA-03 (a): o erro de fator 1000 que a dimensão não pega."""
    with pytest.raises(ForaDoDominioError) as erro:
        _argila(considerar_q=True, q_MPa=27.0)  # 27 kPa passados como MPa
    assert erro.value.parametro == "q_MPa"
    assert "MEGAPASCAL" in erro.value.mensagem


def test_q_facultativo_desligado_por_default_e_ligado_explicitamente():
    """REQ-SIGMA-13: default q = 0, que é a forma que a dedução sustenta."""
    sem_q = _argila()
    com_q = _argila(considerar_q=True, q_MPa=0.027)
    assert sem_q.sigma_adm_ELU_kPa == pytest.approx(300.0)
    assert com_q.sigma_adm_ELU_kPa == pytest.approx(327.0)
    assert com_q.sigma_adm_ELU_kPa > sem_q.sigma_adm_ELU_kPa
    assert any("não sustentado pela dedução" in a.lower() or
               "NÃO sustentado pela dedução" in a for a in com_q.avisos)


def test_q_informado_sem_ligar_a_parcela_e_erro_e_nao_silencio():
    with pytest.raises(ValueError):
        _argila(q_MPa=0.027)
    with pytest.raises(ValueError):
        _argila(considerar_q=True)


def test_recusa_metodo_de_seguranca_de_calculo():
    with pytest.raises(MetodoDeSegurancaError):
        _argila(metodo_de_seguranca="calculo")
    with pytest.raises(MetodoDeSegurancaError):
        _areia(metodo_de_seguranca="calculo")


# --- 4. FS embutido e rótulo de ELU ---------------------------------------

def test_FS_embutido_viaja_com_o_numero_e_e_conferido():
    """REQ-SIGMA-02: campo + origem demonstrável + asserção executada."""
    for resultado, esperado in ((_argila(), FS_EMBUTIDO_REGRA_50),
                                (_areia(), FS_EMBUTIDO_TEIXEIRA)):
        assert resultado.FS_embutido == esperado
        assert resultado.FS_embutido >= 3.00
        assert resultado.FS_embutido_origem
        assert resultado.FSg_aplicado is None
        assert resultado.FSg_efetivo == esperado


def test_FS_embutido_da_regra_50_e_3_por_algebra_exata():
    """sigma_r/sigma_a = 0,06·N / 0,02·N = 3,0000 para qualquer N_SPT."""
    for n in (5.0, 10.0, 15.0, 20.0):
        sigma_a_MPa = _argila(N_spt_medio_bulbo=n).sigma_adm_ELU_kPa / 1000.0
        sigma_r_MPa = 0.01 * n * 6.0        # c·Nc, com Nc = 6 (Skempton)
        assert sigma_r_MPa / sigma_a_MPa == pytest.approx(3.0, rel=1e-12)


def test_nao_aplicar_FSg_por_cima_do_semiempirico():
    """Dupla contagem é proibida: o caminho semiempírico não divide de novo."""
    resultado = _argila()
    assert resultado.sigma_adm_ELU_kPa == pytest.approx(300.0)
    # E o FS da Tabela 1 para semiempíricos é PISO, não constante:
    fs = fator_de_seguranca_global("semiempirico",
                                   FS_proposto_pelo_processo=4.55)
    assert fs.valor == 4.55
    fs_piso = fator_de_seguranca_global("semiempirico",
                                        FS_proposto_pelo_processo=3.0)
    assert fs_piso.valor == 3.00
    with pytest.raises(MetodoDeSegurancaError):
        fator_de_seguranca_global("semiempirico")


def test_rotulo_de_ELU_e_de_fonte_nao_normativa_colados_ao_numero():
    """REQ-SIGMA-09 e REQ-UI-SIGMA-02."""
    for resultado in (_argila(), _areia()):
        assert "parcela de ELU" in resultado.rotulo_ELU
        assert "§7.4 (ELS/recalque) NÃO verificado" in resultado.rotulo_ELU
        assert "NÃO" in resultado.rotulo_fonte and "normativa" in resultado.rotulo_fonte
        assert "NBR6122-7.3-7.4-conjuncao-ELU-ELS" in resultado.regras
        assert resultado.praticas
        assert any("formulários de bolso" in a for a in resultado.avisos)


def test_nome_do_metodo_da_regra_50_nao_e_metodo_de_teixeira():
    """A fonte a apresenta como regra do meio técnico brasileiro."""
    nome = _argila().nome_do_metodo
    assert "regra brasileira" in nome
    assert nome.startswith("regra")
    assert "método de Teixeira (1996) para areia" == _areia().nome_do_metodo


# --- 5. Dispersão lado a lado (REQ-SIGMA-05) ------------------------------

def _caso(**kwargs):
    base = dict(N_spt=15.0, B_m=2.0, forma="quadrada", solo_declarado="argila",
                h_m=1.5, gamma_kN_m3=18.0,
                aplicabilidade_regional_declarada=True)
    base.update(kwargs)
    return EntradaSemiempiricaSPT(**base)


def test_dispersao_traz_o_aplicavel_e_explica_o_recusado():
    dispersao = semiempirico_spt(_caso())
    assert [r.sigma_adm_ELU_kPa for r in dispersao.resultados] == [
        pytest.approx(300.0)]
    assert len(dispersao.recusas) == 1
    recusa = dispersao.recusas[0]
    assert recusa.pratica == "FB-TEIXEIRA-1996-areia"
    assert recusa.parametro == "solo_declarado"
    assert dispersao.declaracao_regional


def test_dispersao_em_areia_traz_teixeira():
    dispersao = semiempirico_spt(_caso(solo_declarado="areia"))
    assert dispersao.valores_kPa == (pytest.approx(320.0),)
    assert dispersao.recusas[0].pratica == "FB-REGRA-BRASILEIRA-Nspt-50-argila"
    assert dispersao.dispersao_relativa is None


def test_dispersao_nao_expoe_valor_de_projeto_escolhido():
    """O software não escolhe, não faz média e não pega o menor."""
    dispersao = semiempirico_spt(_caso())
    for proibido in ("valor_de_projeto", "sigma_adm_ELU_kPa", "melhor",
                     "recomendado", "media"):
        assert not hasattr(dispersao, proibido)


def test_dispersao_recusa_quando_nenhuma_correlacao_se_aplica():
    """Entrada sem método aplicável é RECUSA, não lista vazia."""
    with pytest.raises(ForaDoDominioError):
        semiempirico_spt(_caso(N_spt=40.0))
    with pytest.raises(ForaDoDominioError):
        semiempirico_spt(_caso(solo_declarado="silte"))
