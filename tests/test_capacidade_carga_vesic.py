"""Testes de calc_core.geotecnico.capacidade (Terzaghi/Vesic + De Beer).

Famílias, seguindo a metodologia de a7-validador.md:

1. CONFORMIDADE CONTRA FIXTURE PUBLICADA — a Tab. 2.2 de Vesic (51 linhas x 3
   colunas) lida de ``kb/formulas.yaml``. É o teste central: as formas
   fechadas implementadas têm de reproduzir a tabela impressa dentro de 0,05
   absoluto OU 0,1 % relativo, o que for maior (REQ-SIGMA-11). O a2 rodou a
   mesma comparação e obteve 255/255 células dentro de 0,1 %.
2. VALOR CONHECIDO — os dois casos típicos de ``checagem_numerica`` do ruleset.
3. BORDA — phi = 0 (argila não drenada, o caminho mais usado), phi = 50, h = B.
4. REJEIÇÃO FORA DO DOMÍNIO — cada guarda de REQ-SIGMA-07, uma a uma.
"""
import math
from pathlib import Path

import pytest
import yaml

from calc_core.geotecnico.capacidade import (NC_PHI_ZERO, capacidade_de_carga,
                                             fator_Nc, fator_N_gamma, fator_Nq,
                                             fatores_de_capacidade,
                                             fatores_de_forma_de_beer,
                                             phi_reduzido_de_puncionamento)
from calc_core.geotecnico.dominio import ForaDoDominioError
from calc_core.geotecnico.seguranca import MetodoDeSegurancaError
from calc_core.geotecnico.sigma_adm import teorico_terzaghi_vesic
from calc_core.modelos import EntradaCapacidadeCarga

RAIZ = Path(__file__).resolve().parents[1]
ID_TABELA_2_2 = "CINTRA-VESIC-tabela-2.2-fatores-capacidade-carga"


def _linhas_da_tabela_2_2():
    """Fixture de validação — Tab. 2.2, NÃO tabela de consulta em runtime.

    A tabela foi DERIVADA das formas fechadas pelo próprio Vesic ("Vesic
    calcula os valores [...] reproduzidos na Tab. 2.2"), então usá-la como
    fixture verifica a transcrição das equações contra o número publicado.
    """
    dados = yaml.safe_load((RAIZ / "kb" / "formulas.yaml").read_text("utf-8"))
    tabela = next(f for f in dados["formulas"] if f["id"] == ID_TABELA_2_2)
    return tabela["valores"]["linhas"]


def _dentro_da_tolerancia(calculado: float, publicado: float) -> bool:
    """0,05 absoluto OU 0,1 % relativo, o que for MAIOR (REQ-SIGMA-11)."""
    return abs(calculado - publicado) <= max(0.05, 0.001 * abs(publicado))


def _entrada(**kwargs) -> EntradaCapacidadeCarga:
    base = dict(
        c_kPa=0.0, phi_graus=30.0, B_m=2.0, L_m=2.0, h_m=1.5,
        gamma_acima_da_base_kN_m3=18.0, gamma_abaixo_da_base_kN_m3=18.0,
        forma="quadrada", modo_de_ruptura="geral",
        natureza_do_carregamento="drenado",
        solo_homogeneo_no_bulbo_declarado=True,
    )
    base.update(kwargs)
    return EntradaCapacidadeCarga(**base)


# --- 1. Conformidade contra a Tab. 2.2 publicada ---------------------------

def test_tabela_2_2_completa_51_linhas_x_3_colunas():
    """As 153 células de Nc, Nq e Nγ, phi = 0..50 (REQ-SIGMA-11)."""
    linhas = _linhas_da_tabela_2_2()
    assert [linha["phi"] for linha in linhas] == list(range(0, 51))

    divergentes = []
    for linha in linhas:
        phi = float(linha["phi"])
        for nome, calculado, publicado in (
            ("Nc", fator_Nc(phi), linha["Nc"]),
            ("Nq", fator_Nq(phi), linha["Nq"]),
            ("N_gamma", fator_N_gamma(phi), linha["N_gamma"]),
        ):
            if not _dentro_da_tolerancia(calculado, publicado):
                divergentes.append((phi, nome, calculado, publicado))
    assert not divergentes, f"células fora da tolerância: {divergentes}"


def test_contornos_fixos_da_tabela_2_2():
    """phi = 0 -> 5,14 / 1,00 / 0,00 e phi = 30 -> 30,14 / 18,40 / 22,40."""
    assert fator_Nc(0.0) == pytest.approx(5.14, abs=0.005)
    # Nq(0) = e^0·tg²(45°) = 1,00. O desvio é de um ulp, vindo da conversão de
    # 45 graus para radianos — não é questão de transcrição da fórmula.
    assert fator_Nq(0.0) == pytest.approx(1.00, abs=1e-12)
    assert fator_N_gamma(0.0) == 0.0
    assert fator_Nc(30.0) == pytest.approx(30.14, abs=0.005)
    assert fator_Nq(30.0) == pytest.approx(18.40, abs=0.005)
    assert fator_N_gamma(30.0) == pytest.approx(22.40, abs=0.005)


def test_nq_sobre_nc_em_phi_zero_e_calculado_e_nao_o_impresso():
    """A fonte imprime 0,20; o valor correto é 0,1945 (REQ-SIGMA-11).

    Testar contra o impresso congelaria o erro tipográfico da fonte, que é
    repetição da célula da linha phi = 1 (onde 0,20 está certo).
    """
    fatores = fatores_de_capacidade(0.0)
    assert fatores.Nq_sobre_Nc == pytest.approx(1.0 / (2.0 + math.pi), rel=1e-12)
    assert fatores.Nq_sobre_Nc == pytest.approx(0.1945, abs=1e-4)
    assert fatores.Nq_sobre_Nc != pytest.approx(0.20, abs=1e-4)


def test_funcoes_reais_batem_com_o_que_checar_dimensoes_assume():
    """Amarra ``tools/checar_dimensoes.py`` ao código que foi de fato escrito.

    A ferramenta do a2 substitui as variáveis por grandezas com unidade e
    ADOTA valores numéricos fixos para os fatores (linha phi = 31 da Tab. 2.2 e
    Tab. 2.3 para sapata quadrada), com phi = arctg(0,6) ~ 30,96°. A checagem
    dimensional continua passando mesmo que o código divirja desses números —
    ela só olha unidade. Este teste fecha essa lacuna.
    """
    phi = math.degrees(math.atan(0.6))
    fatores = fatores_de_capacidade(phi)
    assert fatores.Nc == pytest.approx(32.67, abs=0.3)
    assert fatores.Nq == pytest.approx(20.63, abs=0.3)
    assert fatores.N_gamma == pytest.approx(25.99, abs=0.3)

    forma = fatores_de_forma_de_beer("quadrada", 2.0, 2.0, phi)
    assert forma.Sc == pytest.approx(1.63, abs=0.01)
    assert forma.Sq == pytest.approx(1.60, abs=1e-12)   # 1 + tg phi = 1,6
    assert forma.S_gamma == 0.60


# --- 2. Valores conhecidos (checagem_numerica do ruleset) ------------------

def test_caso_tipico_areia_do_ruleset():
    """N_SPT = 15 -> phi = sqrt(20·15)+15 = 32,3205°, B = 2 m, quadrada.

    Ruleset, FB-CINTRA-TERZAGHI-VESIC > checagem_numerica: sigma_r = 1481 kPa
    e sigma_r/3 = 494 kPa. A prosa do ruleset arredonda phi para 32,3°, que dá
    1477 kPa; com o phi cheio da correlação de Teixeira o valor bate.
    """
    phi = math.sqrt(20 * 15) + 15.0
    resultado = capacidade_de_carga(_entrada(
        c_kPa=0.0, phi_graus=phi, gamma_acima_da_base_kN_m3=19.0,
        gamma_abaixo_da_base_kN_m3=19.0,
    ))
    assert resultado.sigma_r_kPa == pytest.approx(1481.0, abs=1.0)
    assert resultado.parcela_coesao_kPa == 0.0
    assert resultado.sigma_r_kPa / 3.0 == pytest.approx(494.0, abs=1.0)


def test_caso_tipico_argila_nao_drenada_do_ruleset():
    """phi = 0, c = 150 kPa: Nc = 5,142, Sc = 1,1945, sigma_r ~ 950 kPa."""
    resultado = capacidade_de_carga(_entrada(
        c_kPa=150.0, phi_graus=0.0, natureza_do_carregamento="nao_drenado",
    ))
    assert resultado.fatores.Nc == pytest.approx(5.142, abs=0.001)
    assert resultado.fatores.Nq == pytest.approx(1.0, abs=1e-12)
    assert resultado.fatores.N_gamma == 0.0
    assert resultado.fatores_de_forma.Sc == pytest.approx(1.1945, abs=1e-4)
    assert resultado.parcela_peso_kPa == 0.0
    assert resultado.sigma_r_kPa == pytest.approx(950.0, abs=2.0)
    assert resultado.sigma_r_kPa / 3.0 == pytest.approx(317.0, abs=1.0)


def test_soma_das_tres_parcelas_e_sigma_r():
    """Equilíbrio interno: a soma das parcelas é exatamente sigma_r."""
    resultado = capacidade_de_carga(_entrada(c_kPa=20.0, phi_graus=25.0))
    assert resultado.sigma_r_kPa == pytest.approx(
        resultado.parcela_coesao_kPa + resultado.parcela_sobrecarga_kPa
        + resultado.parcela_peso_kPa, rel=1e-15)
    assert resultado.q_kPa == pytest.approx(18.0 * 1.5, rel=1e-15)


def test_fatores_de_forma_de_beer_por_tipo():
    """Tab. 2.3: corrida, retangular, quadrada e circular."""
    corrida = fatores_de_forma_de_beer("corrida", 1.0, 10.0, 30.0)
    assert (corrida.Sc, corrida.Sq, corrida.S_gamma) == (1.0, 1.0, 1.0)

    quadrada = fatores_de_forma_de_beer("quadrada", 2.0, 2.0, 30.0)
    Nq_sobre_Nc = fatores_de_capacidade(30.0).Nq_sobre_Nc
    assert quadrada.Sc == pytest.approx(1 + Nq_sobre_Nc)
    assert quadrada.Sq == pytest.approx(1 + math.tan(math.radians(30.0)))
    assert quadrada.S_gamma == 0.60

    # A forma retangular com B = L reproduz a quadrada — coerência da Tab. 2.3.
    retangular = fatores_de_forma_de_beer("retangular", 2.0, 2.0, 30.0)
    assert retangular.Sc == pytest.approx(quadrada.Sc)
    assert retangular.Sq == pytest.approx(quadrada.Sq)
    assert retangular.S_gamma == pytest.approx(quadrada.S_gamma)

    meia = fatores_de_forma_de_beer("retangular", 1.0, 2.0, 30.0)
    assert meia.S_gamma == pytest.approx(1 - 0.4 * 0.5)


def test_puncionamento_reduz_a_tangente_e_nao_o_angulo():
    """phi* = arctg(2/3·tg phi), NUNCA 2/3·phi (REQ-SIGMA-07 i)."""
    assert phi_reduzido_de_puncionamento(30.0) == pytest.approx(21.052, abs=1e-3)
    assert phi_reduzido_de_puncionamento(30.0) != pytest.approx(20.0, abs=0.5)
    assert phi_reduzido_de_puncionamento(0.0) == 0.0


def test_puncionamento_reduz_c_e_N_mas_nao_os_fatores_de_forma():
    """c* = 2/3·c, N de phi*, fatores de FORMA com o phi declarado."""
    comum = dict(c_kPa=30.0, phi_graus=30.0)
    geral = capacidade_de_carga(_entrada(**comum, modo_de_ruptura="geral"))
    punc = capacidade_de_carga(_entrada(**comum,
                                        modo_de_ruptura="puncionamento"))

    assert punc.c_de_calculo_kPa == pytest.approx(20.0)
    assert punc.phi_de_calculo_graus == pytest.approx(21.052, abs=1e-3)
    assert punc.fatores.Nq == pytest.approx(fator_Nq(punc.phi_de_calculo_graus))
    # Fatores de forma IDÊNTICOS aos da ruptura geral: não são reduzidos.
    assert punc.fatores_de_forma == geral.fatores_de_forma
    # E o resultado é sempre menor — puncionamento é o modo menos resistente.
    assert punc.sigma_r_kPa < geral.sigma_r_kPa


# --- 3. Bordas -------------------------------------------------------------

def test_nc_em_phi_zero_usa_o_limite_e_nao_epsilon_nem_zero():
    """Nc(0) = 2 + pi = 5,14159..., o caso de argila não drenada."""
    assert fator_Nc(0.0) == NC_PHI_ZERO
    assert NC_PHI_ZERO == pytest.approx(5.14159, abs=1e-5)
    # Continuidade: a forma fechada tende ao limite pela direita.
    assert fator_Nc(1e-4) == pytest.approx(NC_PHI_ZERO, rel=1e-4)


def test_phi_50_e_aceito_e_phi_50_0001_e_recusado():
    """A extensão da Tab. 2.2 é FECHADA em 50°."""
    assert fator_Nq(50.0) == pytest.approx(319.07, abs=0.05)
    with pytest.raises(ForaDoDominioError):
        fator_Nq(50.0001)


def test_h_igual_a_B_e_aceito_e_h_maior_e_recusado():
    """Hipótese 2 de Terzaghi: h <= B, com igualdade admitida."""
    capacidade_de_carga(_entrada(B_m=1.5, L_m=1.5, h_m=1.5))
    with pytest.raises(ForaDoDominioError) as erro:
        capacidade_de_carga(_entrada(B_m=1.4, L_m=1.4, h_m=1.5))
    assert erro.value.parametro == "h_m"


def test_monotonicidade_em_phi_e_em_B():
    """sigma_r cresce com phi e com B — propriedade física básica."""
    valores_phi = [capacidade_de_carga(_entrada(phi_graus=p)).sigma_r_kPa
                   for p in (10.0, 20.0, 30.0, 40.0)]
    assert valores_phi == sorted(valores_phi)
    valores_B = [capacidade_de_carga(_entrada(B_m=b, L_m=b)).sigma_r_kPa
                 for b in (1.5, 2.0, 2.5, 3.0)]
    assert valores_B == sorted(valores_B)


# --- 4. Rejeição fora do domínio (REQ-SIGMA-07, uma guarda por teste) ------

def test_recusa_phi_acima_de_50():
    """(a) 0 <= phi <= 50: saber calcular phi = 55° não é autorização."""
    with pytest.raises(ForaDoDominioError) as erro:
        capacidade_de_carga(_entrada(phi_graus=55.0))
    assert erro.value.parametro == "phi_graus"
    assert "0.0 a 50.0" in erro.value.intervalo


def test_recusa_phi_negativo():
    with pytest.raises(ForaDoDominioError):
        fator_Nq(-1.0)


def test_recusa_h_maior_que_B():
    """(b) h <= B — o erro seria do lado INSEGURO."""
    with pytest.raises(ForaDoDominioError) as erro:
        capacidade_de_carga(_entrada(B_m=1.0, L_m=1.0, h_m=2.0))
    assert "INSEGURO" in erro.value.mensagem


def test_recusa_solo_nao_declarado_homogeneo():
    """(c) solo HOMOGÊNEO no bulbo — item 2.5 da fonte não foi extraído."""
    with pytest.raises(ForaDoDominioError) as erro:
        capacidade_de_carga(_entrada(solo_homogeneo_no_bulbo_declarado=False))
    assert erro.value.parametro == "solo_homogeneo_no_bulbo_declarado"


def test_recusa_modo_de_ruptura_inventado():
    """(d) só 'geral' ou 'puncionamento'; não há terceiro modo."""
    with pytest.raises(ForaDoDominioError) as erro:
        capacidade_de_carga(_entrada(modo_de_ruptura="local"))
    assert erro.value.parametro == "modo_de_ruptura"
    assert "PUNCIONAMENTO" in erro.value.mensagem


def test_recusa_geometria_invalida():
    """(e) c >= 0, B > 0, L >= B, gamma > 0."""
    with pytest.raises(ForaDoDominioError):
        capacidade_de_carga(_entrada(c_kPa=-1.0))
    with pytest.raises(ForaDoDominioError):
        capacidade_de_carga(_entrada(B_m=0.0, L_m=0.0))
    with pytest.raises(ForaDoDominioError):
        capacidade_de_carga(_entrada(forma="retangular", B_m=3.0, L_m=2.0,
                                     h_m=1.5))
    with pytest.raises(ForaDoDominioError):
        capacidade_de_carga(_entrada(gamma_abaixo_da_base_kN_m3=0.0))


def test_recusa_forma_incoerente_com_as_dimensoes():
    """Quadrada exige B = L; corrida exige L >= 5B (hipótese original)."""
    with pytest.raises(ForaDoDominioError):
        capacidade_de_carga(_entrada(forma="quadrada", B_m=2.0, L_m=3.0))
    with pytest.raises(ForaDoDominioError):
        capacidade_de_carga(_entrada(forma="corrida", B_m=2.0, L_m=4.0))
    capacidade_de_carga(_entrada(forma="corrida", B_m=2.0, L_m=10.0))


def test_recusa_natureza_do_carregamento_incoerente():
    """(REQ-SIGMA-08) phi = 0 com c > 0 é NÃO DRENADA; phi > 0, c = 0 é drenada."""
    with pytest.raises(ForaDoDominioError) as erro:
        capacidade_de_carga(_entrada(c_kPa=150.0, phi_graus=0.0,
                                     natureza_do_carregamento="drenado"))
    assert erro.value.parametro == "natureza_do_carregamento"
    with pytest.raises(ForaDoDominioError):
        capacidade_de_carga(_entrada(c_kPa=0.0, phi_graus=30.0,
                                     natureza_do_carregamento="nao_drenado"))
    with pytest.raises(ForaDoDominioError):
        capacidade_de_carga(_entrada(natureza_do_carregamento="parcial"))


def test_recusa_forma_fora_da_tabela_2_3():
    """(g) só os fatores de De Beer; nada de forma inventada."""
    with pytest.raises(ForaDoDominioError):
        fatores_de_forma_de_beer("trapezoidal", 2.0, 2.0, 30.0)


def test_recusa_metodo_de_seguranca_de_calculo():
    """REQ-SIGMA-01: a rota de valores de cálculo não está implementada."""
    with pytest.raises(MetodoDeSegurancaError):
        capacidade_de_carga(_entrada(metodo_de_seguranca="calculo"))


# --- 5. Caminho completo até a parcela de ELU ------------------------------

def test_teorico_divide_por_FSg_3_e_rotula_como_ELU():
    """Tabela 1, linha 'Analíticos': FSg = 3,00 FIXO."""
    entrada = _entrada(c_kPa=150.0, phi_graus=0.0,
                       natureza_do_carregamento="nao_drenado")
    resultado = teorico_terzaghi_vesic(entrada)
    assert resultado.FSg_aplicado == 3.00
    assert resultado.sigma_adm_ELU_kPa == pytest.approx(
        resultado.capacidade.sigma_r_kPa / 3.0, rel=1e-15)
    assert "§7.4 (ELS/recalque) NÃO verificado" in resultado.rotulo_ELU
    assert "NBR6122-7.3-7.4-conjuncao-ELU-ELS" in resultado.regras
    assert "FB-CINTRA-TERZAGHI-VESIC-capacidade-de-carga" in resultado.praticas
    assert resultado.FS_embutido is None
    assert resultado.FSg_efetivo == 3.00


def test_duas_provas_de_carga_na_fase_de_projeto_dao_FSg_2():
    """Tabela 1, terceira linha — exige as DUAS condições declaradas."""
    entrada = _entrada(c_kPa=150.0, phi_graus=0.0,
                       natureza_do_carregamento="nao_drenado")
    com_provas = teorico_terzaghi_vesic(
        entrada, n_provas_de_carga=2,
        provas_executadas_na_fase_de_projeto=True)
    assert com_provas.FSg_aplicado == 2.00

    # Provas de carga que não são da fase de projeto NÃO reduzem o FS.
    sem_fase = teorico_terzaghi_vesic(
        entrada, n_provas_de_carga=3,
        provas_executadas_na_fase_de_projeto=False)
    assert sem_fase.FSg_aplicado == 3.00
    assert any("fase de projeto" in aviso for aviso in sem_fase.avisos)

    uma_so = teorico_terzaghi_vesic(
        entrada, n_provas_de_carga=1,
        provas_executadas_na_fase_de_projeto=True)
    assert uma_so.FSg_aplicado == 3.00
