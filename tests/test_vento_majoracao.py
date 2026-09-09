"""Testes de calc_core.geotecnico.vento (NBR 6122:2022 §6.3.2).

Famílias:

1. VALOR CONHECIDO — a ``checagem_numerica`` do ruleset (300 kPa -> 345/390) e
   a tabela de (C4) que o a2 montou para o piso de 1,6.
2. BORDA — k_v exatamente nos tetos 0,15 e 0,30, e o caso em que (C4) binda.
3. REJEIÇÃO — as quatro condições, uma por teste, todas RECUSANDO.
4. NÃO PROPAGAÇÃO — k_v é geotécnico e não pode chegar ao lado estrutural;
   travado por varredura de código-fonte, não por convenção.
"""
from pathlib import Path

import pytest

from calc_core.geotecnico.seguranca import MetodoDeSegurancaError
from calc_core.geotecnico.vento import (FSG_EFETIVO_MINIMO,
                                        K_V_MAX_CASO_GERAL,
                                        K_V_MAX_LISTA_FECHADA,
                                        TIPOS_DE_OBRA_DOS_30_POR_CENTO,
                                        MajoracaoDeVentoError,
                                        k_v_maximo_admissivel,
                                        majoracao_admissivel)

RAIZ = Path(__file__).resolve().parents[1]


# --- 1. Valores conhecidos -------------------------------------------------

def test_checagem_numerica_do_ruleset():
    """sigma_adm = 300 kPa: k_v = 0,15 -> 345 kPa; k_v = 0,30 -> 390 kPa."""
    geral = majoracao_admissivel(300.0, FSg=3.0,
                                 vento_e_acao_variavel_principal=True,
                                 k_v=0.15)
    assert geral.sigma_adm_ELU_majorado_kPa == pytest.approx(345.0)

    lista = majoracao_admissivel(300.0, FSg=3.0,
                                 vento_e_acao_variavel_principal=True,
                                 tipo_de_obra_da_lista_dos_30_por_cento=True,
                                 k_v=0.30)
    assert lista.sigma_adm_ELU_majorado_kPa == pytest.approx(390.0)


def test_default_e_identidade_e_nao_majora():
    """k_v = 0 por default: a Norma dá o TETO, não o valor."""
    resultado = majoracao_admissivel(300.0, FSg=3.0)
    assert resultado.sigma_adm_ELU_majorado_kPa == 300.0
    assert resultado.k_v_adotado == 0.0
    assert resultado.k_v_maximo_admissivel == 0.0
    assert resultado.FSg_efetivo == 3.0
    assert any("NÃO utilizada" in aviso for aviso in resultado.avisos)


@pytest.mark.parametrize(
    "FSg, k_v, lista, efetivo_esperado, deve_passar",
    [
        (3.00, 0.15, False, 2.6087, True),    # não ativa
        (3.00, 0.30, True, 2.3077, True),     # não ativa
        (2.00, 0.15, False, 1.7391, True),    # não ativa
        (2.00, 0.30, True, 1.5385, False),    # ATIVA — tabela do a2
    ],
)
def test_tabela_do_piso_FSg_1_6_medida_pelo_a2(FSg, k_v, lista,
                                               efetivo_esperado, deve_passar):
    """(C4) FSg/(1 + k_v) >= 1,6 — binda em FSg = 2,00 com k_v = 0,30."""
    chamada = dict(FSg=FSg, vento_e_acao_variavel_principal=True,
                   tipo_de_obra_da_lista_dos_30_por_cento=lista, k_v=k_v)
    if deve_passar:
        resultado = majoracao_admissivel(300.0, **chamada)
        assert resultado.FSg_efetivo == pytest.approx(efetivo_esperado, abs=1e-4)
        assert resultado.FSg_efetivo >= FSG_EFETIVO_MINIMO
    else:
        with pytest.raises(MajoracaoDeVentoError) as erro:
            majoracao_admissivel(300.0, **chamada)
        assert "1.6" in str(erro.value) or "1,6" in str(erro.value)


def test_quando_C4_binda_o_k_v_maximo_cai_para_25_por_cento():
    """FSg = 2,00 na lista fechada: 2,00/1,6 − 1 = 0,25, não 0,30.

    É o que impede a acumulação de dois benefícios (provas de carga + vento).
    """
    maximo = k_v_maximo_admissivel(
        FSg=2.00, vento_e_acao_variavel_principal=True,
        tipo_de_obra_da_lista_dos_30_por_cento=True)
    assert maximo == pytest.approx(0.25)
    resultado = majoracao_admissivel(
        300.0, FSg=2.00, vento_e_acao_variavel_principal=True,
        tipo_de_obra_da_lista_dos_30_por_cento=True, k_v=0.25)
    assert resultado.FSg_efetivo == pytest.approx(1.6)


def test_k_v_maximo_e_zero_sem_vento_principal():
    assert k_v_maximo_admissivel(FSg=3.0) == 0.0
    assert k_v_maximo_admissivel(
        FSg=3.0, vento_e_acao_variavel_principal=True) == K_V_MAX_CASO_GERAL
    assert k_v_maximo_admissivel(
        FSg=3.0, vento_e_acao_variavel_principal=True,
        tipo_de_obra_da_lista_dos_30_por_cento=True) == K_V_MAX_LISTA_FECHADA


# --- 2. Bordas -------------------------------------------------------------

def test_tetos_exatos_sao_aceitos_e_o_epsilon_acima_e_recusado():
    majoracao_admissivel(300.0, FSg=3.0,
                         vento_e_acao_variavel_principal=True, k_v=0.15)
    with pytest.raises(MajoracaoDeVentoError):
        majoracao_admissivel(300.0, FSg=3.0,
                             vento_e_acao_variavel_principal=True, k_v=0.1501)
    majoracao_admissivel(300.0, FSg=3.0,
                         vento_e_acao_variavel_principal=True,
                         tipo_de_obra_da_lista_dos_30_por_cento=True, k_v=0.30)
    with pytest.raises(MajoracaoDeVentoError):
        majoracao_admissivel(300.0, FSg=3.0,
                             vento_e_acao_variavel_principal=True,
                             tipo_de_obra_da_lista_dos_30_por_cento=True,
                             k_v=0.3001)


def test_majoracao_e_desigualdade_e_nunca_supera_o_teto():
    """sigma_adm_vento <= (1 + k_v)·sigma_adm, com k_v dentro do teto."""
    for k_v in (0.0, 0.05, 0.10, 0.15):
        resultado = majoracao_admissivel(
            250.0, FSg=3.0, vento_e_acao_variavel_principal=True, k_v=k_v)
        assert resultado.sigma_adm_ELU_majorado_kPa <= (
            1 + K_V_MAX_CASO_GERAL) * 250.0 + 1e-9
        assert resultado.sigma_adm_ELU_majorado_kPa == pytest.approx(
            (1 + k_v) * 250.0)


# --- 3. Rejeição -----------------------------------------------------------

def test_C1_recusa_majoracao_sem_vento_como_acao_principal():
    """"Não é permitida a majoração" — zero de tolerância."""
    with pytest.raises(MajoracaoDeVentoError) as erro:
        majoracao_admissivel(300.0, FSg=3.0,
                             vento_e_acao_variavel_principal=False, k_v=0.01)
    assert "não é permitida" in str(erro.value)


def test_C1_vale_mesmo_para_obra_da_lista_fechada():
    with pytest.raises(MajoracaoDeVentoError):
        majoracao_admissivel(300.0, FSg=3.0,
                             vento_e_acao_variavel_principal=False,
                             tipo_de_obra_da_lista_dos_30_por_cento=True,
                             k_v=0.30)


def test_C2_recusa_30_por_cento_fora_da_lista_fechada():
    """Edifício comum não está na lista: fica em 15 %."""
    with pytest.raises(MajoracaoDeVentoError) as erro:
        majoracao_admissivel(300.0, FSg=3.0,
                             vento_e_acao_variavel_principal=True, k_v=0.30)
    assert "FECHADA" in str(erro.value)
    for tipo in TIPOS_DE_OBRA_DOS_30_POR_CENTO:
        assert tipo in str(erro.value)


def test_lista_fechada_tem_exatamente_os_sete_tipos():
    assert len(TIPOS_DE_OBRA_DOS_30_POR_CENTO) == 7
    assert "galpões industriais" in TIPOS_DE_OBRA_DOS_30_POR_CENTO
    assert "tanques de produtos químicos" in TIPOS_DE_OBRA_DOS_30_POR_CENTO


def test_recusa_k_v_negativo_e_entradas_invalidas():
    with pytest.raises(MajoracaoDeVentoError):
        majoracao_admissivel(300.0, FSg=3.0,
                             vento_e_acao_variavel_principal=True, k_v=-0.05)
    with pytest.raises(MajoracaoDeVentoError):
        majoracao_admissivel(0.0, FSg=3.0)
    with pytest.raises(MajoracaoDeVentoError):
        majoracao_admissivel(300.0, FSg=0.0)


def test_recusa_metodo_de_seguranca_de_calculo():
    """§6.3.3 (10 % sobre valores de cálculo) NÃO está implementado."""
    with pytest.raises(MetodoDeSegurancaError):
        majoracao_admissivel(300.0, FSg=3.0, metodo_de_seguranca="calculo")


# --- 4. Não propagação para o lado estrutural ------------------------------

def test_k_v_nao_chega_ao_lado_estrutural():
    """REQ-SIGMA-10: a majoração é GEOTÉCNICA e não toca a NBR 6118.

    Varredura de código-fonte, não convenção: nenhum módulo estrutural do
    motor amplo pode importar ``geotecnico.vento`` nem consumir os seus
    símbolos. Se este teste falhar, a majoração de vento vazou para flexão,
    cisalhamento, punção ou ancoragem.
    """
    estruturais = ("bielas.py", "materiais.py", "momentos.py", "rigidez.py",
                   "grelha.py", "sapata.py", "acoes.py")
    vazamentos = ("geotecnico.vento", "majoracao_admissivel",
                  "k_v_maximo_admissivel", "ResultadoMajoracaoVento",
                  "k_v_adotado", "K_V_MAX")
    base = RAIZ / "calc_core" / "sapata_isolada"
    for nome in estruturais:
        fonte = (base / nome).read_text("utf-8")
        for simbolo in vazamentos:
            assert simbolo not in fonte, f"{nome} consome {simbolo}"


def test_colisao_de_simbolo_k_v_esta_documentada():
    """``k_v`` de vento (adimensional) x ``kv`` de Winkler [kN/m³].

    Colisão real e registrada: ``rigidez.py`` usa ``k_v`` para o coeficiente de
    reação vertical do apoio elástico, que é outra grandeza, com outra unidade
    e outra origem (Bowles/Vésic, não normativa). O nome ``k_v`` da majoração
    é imposto por REQ-SIGMA-10 e fica namespaced em ``geotecnico.vento``; o
    aviso tem de estar escrito no módulo, senão a próxima leitura mistura os
    dois — que é exatamente o defeito que a2-verificador.md §3 manda proibir.
    """
    fonte = (RAIZ / "calc_core" / "geotecnico" / "vento.py").read_text("utf-8")
    assert "COLISÃO DE SÍMBOLO" in fonte
    assert "rigidez" in fonte and "Winkler" in fonte


def test_resultado_de_vento_mantem_o_rotulo_de_ELU():
    """Majorar não verifica recalque: continua sendo parcela de ELU."""
    resultado = majoracao_admissivel(300.0, FSg=3.0,
                                     vento_e_acao_variavel_principal=True,
                                     k_v=0.10)
    assert "§7.4 (ELS/recalque) NÃO verificado" in resultado.rotulo_ELU
    assert "NBR6122-6.3.2-majoracao-vento-valores-admissiveis" in resultado.regras
    assert any("verificação estrutural" in aviso for aviso in resultado.avisos)


def test_coef_sigma_max_excentrico_permanece_intocado():
    """O 1,2 de geotecnia.py é PENDENTE_HUMANO e não é escopo desta rodada.

    Aprovar a majoração de vento NÃO autoriza "consertar" o 1,2 trocando-o por
    1,15: são decisões diferentes e a segunda não foi tomada. Este teste trava
    a constante para que a proximidade dos dois assuntos não convide à mistura.
    """
    fonte = (RAIZ / "calc_core" / "sapata_isolada" / "geotecnia.py").read_text(
        "utf-8")
    assert "coef_sigma_max_excentrico: float = 1.2" in fonte
