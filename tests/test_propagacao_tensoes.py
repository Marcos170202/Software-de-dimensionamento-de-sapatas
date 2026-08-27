"""Propagação de tensão em profundidade — Boussinesq/Newmark e 2V:1H.

Cobre `ruleset.yaml > praticas_consagradas`:
  PC-BOUSSINESQ-NEWMARK-canto-retangulo (APROVADA)
  PC-ESPRAIAMENTO-2V1H                  (APROVADA_COM_USO_RESTRITO)
e os requisitos REQ-PROP-01 a REQ-PROP-08.

Nenhum método aqui é normativo: a NBR 6122:2022 não prescreve método de
espraiamento. Os testes travam a ARITMÉTICA (equilíbrio vertical, valores
clássicos do fator de influência, razão entre os dois métodos) e as GUARDAS
DE DOMÍNIO — não conferem nada contra norma, porque não há norma a conferir.
"""
import math

import pytest

from calc_core.sapata_isolada.geotecnia import (
    FONTE_2V1H,
    FONTE_BOUSSINESQ,
    Camada,
    PerfilGeotecnico,
    Solo,
    TipoSubstrato,
    acrescimo_tensao,
    acrescimo_tensao_2v1h,
    acrescimo_tensao_centro,
    influencia_canto_retangulo,
    largura_equivalente,
    propagacao_comparada,
    propagacao_em_profundidade,
    tensao_liquida_na_base,
)
from calc_core.sapata_isolada.recalques import AnaliseRecalque


# --------------------------------------------------------------------- fixtures
def _perfil() -> PerfilGeotecnico:
    """Perfil de referência: 4 camadas, 12,0 m, N.A. a 3,0 m."""
    return PerfilGeotecnico(
        camadas=[
            Camada("Aterro", 1.5, TipoSubstrato.ATERRO, nspt=6),
            Camada("Areia média", 2.5, TipoSubstrato.GRANULAR, nspt=12),
            Camada("Argila mole", 3.0, TipoSubstrato.COESIVO, nspt=4,
                   Cc=0.45, e0=1.2, cv=2.0, Es=4000),
            Camada("Areia compacta", 5.0, TipoSubstrato.GRANULAR, nspt=25),
        ],
        nivel_agua=3.0,
    )


def _solo(hf: float = 1.5) -> Solo:
    return Solo(sigma_adm=200.0, hf=hf, perfil=_perfil())


# ======================================================================== #
#  Boussinesq / Newmark — valores conhecidos
# ======================================================================== #
def test_influencia_canto_valores_classicos():
    """I(1,1) = 0,17522 e I(2,2) = 0,23247 (ramo m²n² > m²+n²+1)."""
    assert influencia_canto_retangulo(1.0, 1.0) == pytest.approx(0.17522,
                                                                 abs=1e-4)
    assert influencia_canto_retangulo(2.0, 2.0) == pytest.approx(0.23247,
                                                                 abs=1e-4)
    # simetria e contorno
    assert influencia_canto_retangulo(3.0, 1.0) == pytest.approx(
        influencia_canto_retangulo(1.0, 3.0), rel=1e-12)
    assert influencia_canto_retangulo(1e4, 1e4) == pytest.approx(0.25,
                                                                 abs=1e-5)
    assert influencia_canto_retangulo(5.0, 0.0) == 0.0


def test_boussinesq_sob_o_centro_valores_de_referencia():
    """a = b = 2,0 m, q_líq = 200 kPa: 186 / 140 / 67,2 / 21,6 kPa."""
    for z, esperado in [(0.5, 186.0), (1.0, 140.0), (2.0, 67.2), (4.0, 21.6)]:
        assert acrescimo_tensao_centro(200.0, 2.0, 2.0, z) == pytest.approx(
            esperado, rel=0.01)


def test_boussinesq_contorno_e_decaimento():
    assert acrescimo_tensao_centro(100.0, 2.0, 2.0, 0.0) == 100.0
    assert acrescimo_tensao_centro(100.0, 2.0, 2.0, 20.0) < 2.0
    valores = [acrescimo_tensao_centro(100.0, 2.0, 3.0, z)
               for z in (0.0, 0.5, 1.0, 2.0, 4.0, 8.0)]
    assert all(x > y for x, y in zip(valores, valores[1:]))


# ======================================================================== #
#  2V:1H — REQ-PROP-06 (a) a (e)
# ======================================================================== #
def test_2v1h_em_z_zero_devolve_q_exato():
    assert acrescimo_tensao_2v1h(200.0, 2.0, 3.0, 0.0) == 200.0


@pytest.mark.parametrize("z", [0.0, 0.5, 1.0, 2.0, 4.0, 8.0])
def test_2v1h_equilibrio_vertical_exato(z):
    """Δσ·(a+z)(b+z) = q·a·b — é esta checagem que fixa o ângulo."""
    q, a, b = 200.0, 2.0, 3.0
    ds = acrescimo_tensao_2v1h(q, a, b, z)
    assert ds * (a + z) * (b + z) == pytest.approx(q * a * b, rel=1e-12)


def test_2v1h_monotonicamente_decrescente_e_tende_a_zero():
    valores = [acrescimo_tensao_2v1h(200.0, 2.0, 2.0, z)
               for z in (0.0, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 50.0)]
    assert all(x > y for x, y in zip(valores, valores[1:]))
    assert acrescimo_tensao_2v1h(200.0, 2.0, 2.0, 1e6) < 1e-3


def test_2v1h_valores_de_referencia():
    """a = b = 2,0 m, q_líq = 200 kPa: 128 / 88,9 / 50,0 / 22,2 kPa."""
    for z, esperado in [(0.5, 128.0), (1.0, 88.889), (2.0, 50.0), (4.0, 22.222)]:
        assert acrescimo_tensao_2v1h(200.0, 2.0, 2.0, z) == pytest.approx(
            esperado, rel=1e-4)


# ======================================================================== #
#  Regressão da razão 2V1H / Boussinesq — trava a troca acidental do ângulo,
#  que é o único erro que a análise dimensional não pega (1V:1H é homogêneo).
# ======================================================================== #
def _integral(f, z0: float, z1: float, n: int = 20000) -> float:
    h = (z1 - z0) / n
    return h * (0.5 * (f(z0) + f(z1)) + sum(f(z0 + i * h) for i in range(1, n)))


def test_razao_integrada_ate_2B_vale_0_748():
    """Razão das integrais de Δσ·dz de 0 a 2·B = 0,748 ± 0,01, para
    a = b = 2,0 m — proxy direto do recalque em meio homogêneo, e a
    assinatura numérica do ângulo de 26,57°.

    Este é o 0,748 registrado no ruleset (checagem_numerica de
    PC-ESPRAIAMENTO-2V1H): ele é a razão das INTEGRAIS até 2·B, não a razão
    pontual em z = 1,0 m — ver `test_razao_pontual_em_z_1m_vale_0_63`.
    """
    a = b = 2.0
    q = 200.0
    z_max = 2.0 * min(a, b)
    i_bous = _integral(lambda z: acrescimo_tensao_centro(q, a, b, z), 0.0, z_max)
    i_2v1h = _integral(lambda z: acrescimo_tensao_2v1h(q, a, b, z), 0.0, z_max)
    assert i_2v1h / i_bous == pytest.approx(0.748, abs=0.01)


@pytest.mark.parametrize("a,b", [(2.0, 2.0), (2.0, 4.0), (1.2, 1.2), (4.0, 4.0)])
def test_razao_integrada_e_praticamente_invariante_com_a_geometria(a, b):
    z_max = 2.0 * min(a, b)
    i_bous = _integral(lambda z: acrescimo_tensao_centro(100.0, a, b, z), 0.0, z_max)
    i_2v1h = _integral(lambda z: acrescimo_tensao_2v1h(100.0, a, b, z), 0.0, z_max)
    assert i_2v1h / i_bous == pytest.approx(0.748, abs=0.01)


def test_razao_pontual_em_z_1m_vale_0_63():
    """Razão PONTUAL em z = 1,0 m com a = b = 2,0 m: 0,63 ± 0,01
    (REQ-PROP-06 (e)). Não confundir com o 0,748 integrado até 2·B."""
    razao = (acrescimo_tensao_2v1h(200.0, 2.0, 2.0, 1.0)
             / acrescimo_tensao_centro(200.0, 2.0, 2.0, 1.0))
    assert razao == pytest.approx(0.63, abs=0.01)


def test_2v1h_cruza_boussinesq_perto_de_1_9B_e_inverte_de_sinal():
    """Abaixo do cruzamento o 2V:1H passa a SUPERESTIMAR — motivo do teto de
    profundidade recomendado para exibição."""
    razao = lambda z: (acrescimo_tensao_2v1h(200.0, 2.0, 2.0, z)  # noqa: E731
                       / acrescimo_tensao_centro(200.0, 2.0, 2.0, z))
    assert razao(3.78) == pytest.approx(1.0, abs=0.01)
    assert razao(2.0) < 1.0
    assert razao(8.0) > 1.3


# ======================================================================== #
#  Guardas de domínio — REQ-PROP-02
# ======================================================================== #
@pytest.mark.parametrize("funcao", [acrescimo_tensao_centro,
                                    acrescimo_tensao_2v1h])
@pytest.mark.parametrize("z", [-1e-9, -0.5, -1.0, -2.0, -10.0])
def test_z_negativo_levanta_erro_nas_duas_funcoes(funcao, z):
    """z < 0 devolvia q (Boussinesq) e 4q (2V:1H) sem erro — tensão plausível
    crescendo para cima. z = -a levantava ZeroDivisionError no 2V:1H."""
    with pytest.raises(ValueError, match="BASE da sapata"):
        funcao(200.0, 2.0, 2.0, z)


@pytest.mark.parametrize("funcao", [acrescimo_tensao_centro,
                                    acrescimo_tensao_2v1h])
@pytest.mark.parametrize("a,b", [(0.0, 2.0), (2.0, 0.0), (-2.0, 2.0),
                                 (2.0, -2.0)])
def test_dimensoes_nao_positivas_levantam_erro(funcao, a, b):
    with pytest.raises(ValueError, match="dimensões em planta"):
        funcao(200.0, a, b, 1.0)


@pytest.mark.parametrize("funcao", [acrescimo_tensao_centro,
                                    acrescimo_tensao_2v1h])
def test_pressao_negativa_levanta_erro(funcao):
    with pytest.raises(ValueError, match="LÍQUIDA"):
        funcao(-1.0, 2.0, 2.0, 1.0)


def test_influencia_canto_rejeita_argumento_negativo():
    with pytest.raises(ValueError):
        influencia_canto_retangulo(-1.0, 1.0)


def test_fonte_desconhecida_levanta_erro():
    with pytest.raises(ValueError, match="fonte de propagação"):
        acrescimo_tensao("2:1", 200.0, 2.0, 2.0, 1.0)
    with pytest.raises(ValueError, match="fonte de propagação"):
        propagacao_em_profundidade(_solo(), 2.0, 2.0, 200.0, fonte="bulbo")


def test_despacho_por_fonte_bate_com_as_funcoes_diretas():
    assert acrescimo_tensao(FONTE_BOUSSINESQ, 200.0, 2.0, 3.0, 1.5) == \
        acrescimo_tensao_centro(200.0, 2.0, 3.0, 1.5)
    assert acrescimo_tensao(FONTE_2V1H, 200.0, 2.0, 3.0, 1.5) == \
        acrescimo_tensao_2v1h(200.0, 2.0, 3.0, 1.5)


# ======================================================================== #
#  Pressão líquida — REQ-PROP-01
# ======================================================================== #
def test_tensao_liquida_desconta_a_sobrecarga_e_reaproveita_o_solo():
    solo = _solo(hf=1.5)
    sobrecarga = solo.sobrecarga_no_nivel_da_base()
    assert sobrecarga == pytest.approx(1.5 * 18.0, rel=1e-9)   # aterro γ=18
    assert tensao_liquida_na_base(200.0, solo) == pytest.approx(
        200.0 - sobrecarga, rel=1e-12)


def test_tensao_liquida_nunca_negativa():
    solo = _solo(hf=1.5)
    assert tensao_liquida_na_base(5.0, solo) == 0.0


def test_tensao_liquida_bate_com_a_do_modulo_de_recalques():
    """A mesma conta de `AnaliseRecalque.q_liquido` — uma fonte só."""
    solo = _solo(hf=1.5)
    an = AnaliseRecalque(solo.perfil, 2.0, 2.0, solo.hf, 200.0)
    assert tensao_liquida_na_base(200.0, solo) == pytest.approx(an.q_liquido,
                                                               rel=1e-12)


def test_propagacao_usa_a_liquida_e_nao_a_total():
    solo = _solo(hf=1.5)
    r = propagacao_em_profundidade(solo, 2.0, 2.0, 200.0)
    assert r.q_liquida == pytest.approx(173.0, rel=1e-9)
    assert r.q_aplicada == 200.0
    assert r.sobrecarga_na_base == pytest.approx(27.0, rel=1e-9)
    assert r.pontos[0].delta_sigma == pytest.approx(173.0, rel=1e-9)


# ======================================================================== #
#  Composição com o perfil estratigráfico
# ======================================================================== #
def test_pontos_caem_nos_limites_de_camada_abaixo_da_base():
    solo = _solo(hf=1.5)   # base no topo da 'Areia média'
    r = propagacao_em_profundidade(solo, 2.0, 2.0, 200.0)
    zs = [p.z for p in r.pontos]
    # limites absolutos 4,0 / 7,0 / 12,0 m -> 2,5 / 5,5 / 10,5 m abaixo da base
    assert zs == pytest.approx([0.0, 2.5, 5.5, 10.5], abs=1e-9)
    assert [p.profundidade for p in r.pontos] == pytest.approx(
        [1.5, 4.0, 7.0, 12.0], abs=1e-9)
    assert [c.nome for c in r.camadas] == ["Areia média", "Argila mole",
                                           "Areia compacta"]
    assert [c.espessura for c in r.camadas] == pytest.approx([2.5, 3.0, 5.0])


def test_camada_cortada_pela_base_da_sapata_entra_so_com_o_trecho_abaixo():
    solo = _solo(hf=2.5)   # base no meio da 'Areia média' (1,5 a 4,0 m)
    r = propagacao_em_profundidade(solo, 2.0, 2.0, 300.0)
    assert r.camadas[0].nome == "Areia média"
    assert r.camadas[0].z_topo == pytest.approx(0.0)
    assert r.camadas[0].espessura == pytest.approx(1.5)
    assert r.pontos[0].rotulo.startswith("base da sapata")


def test_delta_sigma_dos_pontos_bate_com_a_funcao_de_base():
    solo = _solo(hf=1.5)
    for fonte in (FONTE_BOUSSINESQ, FONTE_2V1H):
        r = propagacao_em_profundidade(solo, 2.0, 3.0, 200.0, fonte=fonte)
        for p in r.pontos:
            assert p.delta_sigma == pytest.approx(
                acrescimo_tensao(fonte, r.q_liquida, 2.0, 3.0, p.z), rel=1e-12)
            assert p.fonte == fonte


def test_delta_sigma_decresce_com_a_profundidade_nas_duas_fontes():
    solo = _solo(hf=1.5)
    for r in propagacao_comparada(solo, 2.0, 2.0, 200.0).values():
        ds = [p.delta_sigma for p in r.pontos]
        assert all(x > y for x, y in zip(ds, ds[1:]))


# ======================================================================== #
#  ONDE `delta_sigma_medio` é amostrado — meia-altura do TRECHO analisado
#
#  Buraco de cobertura encontrado pelo a6 no GATE 2 (rodada 1): o mutante M10,
#  que troca a profundidade de amostragem da meia-altura pelo TOPO da camada
#  (`0.5*(zi+zf)` -> `zi` em `geotecnia.py:637`), sobrevivia à suíte inteira.
#  Nada fixava a profundidade de amostragem: `test_delta_sigma_nunca_supera_a
#  _pressao_liquida` só exige base <= médio <= topo, com igualdade permitida, e
#  o médio é justamente o único número que a tela exibe por camada.
#
#  Os três testes abaixo matam M10 e as variantes "amostrar na base" e "usar a
#  meia-altura da camada CHEIA em vez da do trecho analisado".
# ======================================================================== #
def test_delta_sigma_medio_e_amostrado_na_meia_altura_da_camada():
    """`delta_sigma_medio` = Δσ em z = (z_topo + z_base)/2, exatamente.

    Mata o mutante M10 (meia-altura -> topo) e o simétrico (-> base): o valor
    tem de bater com `acrescimo_tensao` chamado nessa profundidade específica
    com rel=1e-12, e tem de ficar ESTRITAMENTE entre os valores de topo e de
    base, com folga larga (>= 10 %) nesta fixture — se fosse amostrado numa
    das interfaces, a igualdade exata com aquela interface apareceria aqui.
    """
    solo = _solo(hf=1.5)
    a, b = 2.0, 3.0
    for fonte in (FONTE_BOUSSINESQ, FONTE_2V1H):
        r = propagacao_em_profundidade(solo, a, b, 200.0, fonte=fonte)
        assert r.camadas, "fixture sem camadas: o teste não estaria testando nada"
        for c in r.camadas:
            z_meio = 0.5 * (c.z_topo + c.z_base)
            esperado = acrescimo_tensao(fonte, r.q_liquida, a, b, z_meio)
            assert c.delta_sigma_medio == pytest.approx(esperado, rel=1e-12)
            # e NÃO é nenhuma das duas interfaces
            assert c.delta_sigma_base < c.delta_sigma_medio < c.delta_sigma_topo
            assert c.delta_sigma_medio < 0.90 * c.delta_sigma_topo
            assert c.delta_sigma_medio > 1.10 * c.delta_sigma_base


def test_delta_sigma_medio_do_2v1h_bate_com_a_forma_fechada_na_meia_altura():
    """Mesma checagem sem passar por `acrescimo_tensao`: para o 2V:1H o valor
    na meia-altura tem forma fechada, Δσ = q_líq·a·b / ((a+z_m)(b+z_m)).

    Independente da função de despacho, portanto sobrevive a uma mutação
    simultânea nela — o número é conferido contra a álgebra, não contra outra
    chamada do mesmo código.
    """
    solo = _solo(hf=1.5)
    a, b = 2.0, 3.0
    r = propagacao_em_profundidade(solo, a, b, 200.0, fonte=FONTE_2V1H)
    for c in r.camadas:
        z_meio = 0.5 * (c.z_topo + c.z_base)
        fechada = r.q_liquida * a * b / ((a + z_meio) * (b + z_meio))
        assert c.delta_sigma_medio == pytest.approx(fechada, rel=1e-12)


def test_delta_sigma_medio_usa_a_meia_altura_do_trecho_e_nao_da_camada_cheia():
    """Camada cortada pela base da sapata (em cima) e pelo teto de
    profundidade (embaixo): a amostragem é na meia-altura do TRECHO ANALISADO.

    hf = 2,5 m corta a 'Areia média' (1,5–4,0 m absolutos) -> trecho 0,0–1,5 m
    abaixo da base, meia-altura em 0,75 m — e não em 0,25 m, que seria a
    meia-altura da camada cheia rebatida para a origem na base. z_max = 4,0 m
    corta a 'Argila mole' (trecho 1,5–4,0 m) -> meia-altura em 2,75 m, e não
    em 3,0 m, que seria a da camada cheia (1,5–4,5 m).
    """
    solo = _solo(hf=2.5)
    a = b = 2.0
    r = propagacao_em_profundidade(solo, a, b, 300.0, z_max=4.0)
    assert [c.nome for c in r.camadas] == ["Areia média", "Argila mole"]
    assert [(c.z_topo, c.z_base) for c in r.camadas] == pytest.approx(
        [(0.0, 1.5), (1.5, 4.0)], abs=1e-9)

    esperados = {0.75: r.camadas[0], 2.75: r.camadas[1]}
    for z_meio, c in esperados.items():
        assert c.delta_sigma_medio == pytest.approx(
            acrescimo_tensao_centro(r.q_liquida, a, b, z_meio), rel=1e-12)
    # as profundidades "quase certas" que os erros plausíveis produziriam
    for z_errado, c in ((0.25, r.camadas[0]), (3.0, r.camadas[1])):
        assert c.delta_sigma_medio != pytest.approx(
            acrescimo_tensao_centro(r.q_liquida, a, b, z_errado), rel=1e-3)


# ======================================================================== #
#  REQ-PROP-04 — o método viaja junto com o número
# ======================================================================== #
def test_fonte_acompanha_todos_os_valores():
    solo = _solo(hf=1.5)
    comparada = propagacao_comparada(solo, 2.0, 2.0, 200.0)
    assert set(comparada) == {FONTE_BOUSSINESQ, FONTE_2V1H}
    for fonte, r in comparada.items():
        assert r.fonte == fonte
        assert "não normativo" in r.rotulo_metodo
        assert all(p.fonte == fonte for p in r.pontos)
        assert all(c.fonte == fonte for c in r.camadas)
        assert any("não normativo" in aviso for aviso in r.avisos)
        assert any("meio homogêneo" in aviso for aviso in r.avisos)
        assert r.informativo is True


def test_comparada_expoe_a_divergencia_entre_os_metodos():
    solo = _solo(hf=1.5)
    c = propagacao_comparada(solo, 2.0, 2.0, 200.0)
    b = {p.z: p.delta_sigma for p in c[FONTE_BOUSSINESQ].pontos}
    v = {p.z: p.delta_sigma for p in c[FONTE_2V1H].pontos}
    assert b.keys() == v.keys()
    assert v[2.5] < b[2.5]          # faixa rasa: 2V:1H subestima
    assert v[10.5] > b[10.5]        # abaixo do cruzamento: superestima


# ======================================================================== #
#  REQ-PROP-03 — resultado estritamente informativo, sem veredito
# ======================================================================== #
def test_resultado_nao_carrega_nenhum_veredito():
    """Se algum campo de aprovação/limite aparecer aqui, a fronteira da
    aprovação do a2 foi cruzada — o número é informativo, não critério."""
    solo = _solo(hf=1.5)
    r = propagacao_em_profundidade(solo, 2.0, 2.0, 200.0)
    proibidos = ("aprovado", "passa", "ok", "limite", "sigma_adm",
                 "tensao_admissivel", "verificacao", "fs", "seguranca")
    campos = set(vars(r)) | set(vars(r.pontos[0])) | set(vars(r.camadas[0]))
    for campo in campos:
        assert not any(p in campo.lower() for p in proibidos), campo
    # e nenhum aviso emite juízo de aprovação
    for aviso in r.avisos:
        assert "não passa" not in aviso.lower()
        assert "reprovado" not in aviso.lower()


# ======================================================================== #
#  REQ-PROP-05 — nenhum caminho novo para o 2V:1H em recalque
# ======================================================================== #
def test_recalque_continua_com_boussinesq_por_default():
    an = AnaliseRecalque(_perfil(), 2.0, 2.0, 1.5, 200.0)
    assert an.usar_boussinesq is True


def test_propagacao_nao_expoe_seletor_de_recalque():
    """A fonte de VISUALIZAÇÃO não pode chegar a `AnaliseRecalque`."""
    import inspect
    assinatura = inspect.signature(propagacao_em_profundidade)
    assert "usar_boussinesq" not in assinatura.parameters
    fonte_recalque = inspect.getsource(AnaliseRecalque._delta_sigma)
    assert "propagacao_em_profundidade" not in fonte_recalque


# ======================================================================== #
#  REQ-PROP-07 — consolidação da duplicação de recalques.py
# ======================================================================== #
@pytest.mark.parametrize("z", [0.0, 0.001, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 20.0])
@pytest.mark.parametrize("a,b", [(2.0, 2.0), (2.0, 4.0), (1.2, 1.2)])
def test_ramo_2v1h_de_recalques_reproduz_a_expressao_original(a, b, z):
    """A expressão que estava escrita à mão em `recalques.py:265-266`,
    reproduzida aqui, tem de continuar dando exatamente o mesmo número depois
    da consolidação em `acrescimo_tensao_2v1h`."""
    an = AnaliseRecalque(_perfil(), a, b, 1.5, 200.0, usar_boussinesq=False)
    original = an.q_liquido * (a * b) / ((a + z) * (b + z))
    assert an._delta_sigma(z) == pytest.approx(original, rel=1e-12)


def test_recalque_total_inalterado_apos_a_consolidacao():
    """Valores capturados rodando o código de HEAD (antes da consolidação)
    sobre esta mesma fixture: a mudança é de forma, não de número.

        usar_boussinesq=True  -> 50,3067622248 mm  (6,3490226763 imediato)
        usar_boussinesq=False -> 45,3365549841 mm  (4,5384594134 imediato)
    """
    esperado = {True: (50.3067622248, 6.3490226763, 43.9577395485),
                False: (45.3365549841, 4.5384594134, 40.7980955707)}
    for usar_b, (total, imediato, adensamento) in esperado.items():
        r = AnaliseRecalque(_perfil(), 2.0, 2.0, 1.5, 200.0,
                            usar_boussinesq=usar_b).executar()
        assert r.recalque_total_mm == pytest.approx(total, abs=1e-9)
        assert r.recalque_imediato_mm == pytest.approx(imediato, abs=1e-9)
        assert r.recalque_adensamento_mm == pytest.approx(adensamento, abs=1e-9)


def test_delta_sigma_por_fatia_inalterado_apos_a_consolidacao():
    """Δσ fatia a fatia, também capturado do código de HEAD."""
    an = AnaliseRecalque(_perfil(), 2.0, 2.0, 1.5, 200.0, usar_boussinesq=False)
    esperado = [173.0, 110.72, 76.8888888889, 43.25, 19.2222222222, 6.92]
    obtido = [an._delta_sigma(z) for z in (0.0, 0.5, 1.0, 2.0, 4.0, 8.0)]
    assert obtido == pytest.approx(esperado, abs=1e-9)


# ======================================================================== #
#  Largura equivalente de espraiamento — a_eq / b_eq do croqui
#  (grandeza de PONTO, por interface; ruleset v7, REQ-PROP-03 (B). O símbolo
#  "L" foi abolido deste croqui por ter significado largura e espessura ao
#  mesmo tempo em artefatos diferentes — REQ-PROP-03 (C).)
# ======================================================================== #
@pytest.mark.parametrize("z", [0.0, 0.5, 1.0, 2.0, 5.0])
def test_largura_equivalente_do_2v1h_e_exatamente_a_mais_z(z):
    a, b, q = 2.0, 3.0, 200.0
    ds = acrescimo_tensao_2v1h(q, a, b, z)
    la, lb = largura_equivalente(q, a, b, ds)
    assert la == pytest.approx(a + z, rel=1e-9)
    assert lb == pytest.approx(b + z, rel=1e-9)


def test_largura_equivalente_preserva_a_carga_total():
    a, b, q = 2.0, 3.0, 200.0
    ds = acrescimo_tensao_centro(q, a, b, 2.0)
    la, lb = largura_equivalente(q, a, b, ds)
    assert ds * la * lb == pytest.approx(q * a * b, rel=1e-9)
    assert la - a == pytest.approx(lb - b, rel=1e-9)


def test_largura_equivalente_indefinida_devolve_none():
    assert largura_equivalente(200.0, 2.0, 2.0, 0.0) is None
    assert largura_equivalente(0.0, 2.0, 2.0, 10.0) is None


def test_larguras_dos_pontos_crescem_com_a_profundidade():
    solo = _solo(hf=1.5)
    for r in propagacao_comparada(solo, 2.0, 2.0, 200.0).values():
        larguras = [p.largura_equivalente_a for p in r.pontos]
        assert all(x is not None for x in larguras)
        assert all(x < y for x, y in zip(larguras, larguras[1:]))
        assert larguras[0] == pytest.approx(2.0, rel=1e-9)


# ======================================================================== #
#  Teto de profundidade — REQ-UI-05 e `dominio_de_validade` das práticas
# ======================================================================== #
def test_teto_de_profundidade_trunca_o_resultado():
    solo = _solo(hf=1.5)
    r = propagacao_em_profundidade(solo, 2.0, 2.0, 200.0, z_max=2.0 * 2.0)
    assert r.z_max == pytest.approx(4.0)
    assert max(p.z for p in r.pontos) == pytest.approx(4.0)
    assert [c.nome for c in r.camadas] == ["Areia média", "Argila mole"]
    assert r.camadas[-1].z_base == pytest.approx(4.0)
    assert r.pontos[-1].rotulo.startswith("limite da análise")


def test_nao_extrapola_alem_do_perfil_e_avisa():
    """Além do perfil: trunca e avisa; a última camada NÃO é estendida."""
    solo = _solo(hf=1.5)
    r = propagacao_em_profundidade(solo, 2.0, 2.0, 200.0, z_max=40.0)
    assert r.z_max == pytest.approx(10.5)          # 12,0 − 1,5 m
    assert max(p.z for p in r.pontos) == pytest.approx(10.5)
    assert any("excede o perfil informado" in a for a in r.avisos)


def test_z_max_default_vai_ate_o_fim_do_perfil():
    solo = _solo(hf=1.5)
    r = propagacao_em_profundidade(solo, 2.0, 2.0, 200.0)
    assert r.z_max == pytest.approx(10.5)
    assert not any("excede o perfil" in a for a in r.avisos)


def test_z_max_nao_positivo_levanta_erro():
    with pytest.raises(ValueError, match="teto de profundidade"):
        propagacao_em_profundidade(_solo(), 2.0, 2.0, 200.0, z_max=0.0)
    with pytest.raises(ValueError, match="teto de profundidade"):
        propagacao_em_profundidade(_solo(), 2.0, 2.0, 200.0, z_max=-3.0)


def test_base_abaixo_do_fim_do_perfil_devolve_vazio_com_aviso():
    solo = Solo(sigma_adm=200.0, hf=15.0, perfil=_perfil())   # perfil só até 12 m
    r = propagacao_em_profundidade(solo, 2.0, 2.0, 400.0)
    assert r.pontos == ()
    assert r.camadas == ()
    assert r.z_max == 0.0
    assert any("nada a propagar" in a for a in r.avisos)


def test_solo_sem_perfil_devolve_vazio_com_aviso_em_vez_de_quebrar():
    solo = Solo(sigma_adm=200.0, hf=1.5)          # perfil = None
    r = propagacao_em_profundidade(solo, 2.0, 2.0, 200.0)
    assert r.pontos == ()
    assert r.camadas == ()
    assert r.q_liquida == pytest.approx(200.0 - 18.0 * 1.5)
    assert any("Perfil geotécnico ausente" in a for a in r.avisos)


def test_geometria_invalida_na_composicao_levanta_erro():
    with pytest.raises(ValueError, match="dimensões em planta"):
        propagacao_em_profundidade(_solo(), 0.0, 2.0, 200.0)
    with pytest.raises(ValueError, match="LÍQUIDA|>= 0"):
        propagacao_em_profundidade(_solo(), 2.0, 2.0, -10.0)


# ======================================================================== #
#  Sanidade global do campo
# ======================================================================== #
def test_delta_sigma_nunca_supera_a_pressao_liquida():
    solo = _solo(hf=1.5)
    for r in propagacao_comparada(solo, 2.0, 3.0, 250.0).values():
        for p in r.pontos:
            assert 0.0 <= p.delta_sigma <= r.q_liquida + 1e-9
        for c in r.camadas:
            assert c.delta_sigma_base <= c.delta_sigma_medio <= c.delta_sigma_topo


def test_determinismo():
    solo = _solo(hf=1.5)
    a = propagacao_comparada(solo, 2.0, 3.0, 250.0, z_max=4.0)
    b = propagacao_comparada(_solo(hf=1.5), 2.0, 3.0, 250.0, z_max=4.0)
    assert a == b


def test_angulo_do_2v1h_e_26_57_graus():
    """Alargamento de z/2 por lado = arctan(0,5) com a vertical."""
    z = 3.0
    a = 2.0
    alargamento_por_lado = (a + z - a) / 2.0
    assert math.degrees(math.atan(alargamento_por_lado / z)) == pytest.approx(
        26.565, abs=0.01)


# ======================================================================== #
#  REQ-PROP-09 (c) — símbolos do croqui: a_eq/b_eq são LARGURA (grandeza de
#  PONTO, por interface, i = 0..n) e `espessura` é h_i (grandeza de TRECHO,
#  por camada, i = 1..n). As duas famílias são [length], de modo que NENHUMA
#  análise dimensional distingue uma da outra: só teste de propriedade
#  distingue, e é o que estes cinco travam.
#
#  Histórico: a v6 do ruleset definia "L1/L2/L3 = espessuras" e o desenho
#  usava "L" para largura. Símbolo queimado, abolido na v7.
# ======================================================================== #
_GEOMETRIAS_DO_CROQUI = [(2.0, 2.0), (2.0, 4.0), (1.5, 3.0)]


@pytest.mark.parametrize("fonte", [FONTE_BOUSSINESQ, FONTE_2V1H])
@pytest.mark.parametrize("a,b", _GEOMETRIAS_DO_CROQUI)
def test_largura_equivalente_em_z_zero_e_a_propria_sapata(fonte, a, b):
    """(c.1) a_eq(z=0) == a e b_eq(z=0) == b, EXATOS, nos dois métodos.

    Protege a ancoragem do índice de interface da v7: i = 0 é a base da
    sapata, e lá a área equivalente é a área real — o tronco de espraiamento
    nasce com a largura da sapata, não com zero e não com uma espessura.
    Igualdade exata (==), não aproximada: em z = 0 o Δσ é q_líq exato nos dois
    métodos, logo a_eq·b_eq = a·b exato. Qualquer offset introduzido na
    fórmula da largura aparece aqui na primeira casa.

    Checado na função `largura_equivalente` e no ponto i = 0 de
    `PontoPropagacao`, que é o que a UI lê (REQ-UI-06).
    """
    q = 200.0
    ds0 = acrescimo_tensao(fonte, q, a, b, 0.0)
    assert largura_equivalente(q, a, b, ds0) == (a, b)

    solo = _solo(hf=1.5)
    r = propagacao_em_profundidade(solo, a, b, 200.0, fonte=fonte)
    assert r.pontos[0].z == 0.0
    assert r.pontos[0].rotulo.startswith("base da sapata")
    assert r.pontos[0].largura_equivalente_a == a
    assert r.pontos[0].largura_equivalente_b == b


@pytest.mark.parametrize("fonte", [FONTE_BOUSSINESQ, FONTE_2V1H])
@pytest.mark.parametrize("a,b", _GEOMETRIAS_DO_CROQUI)
def test_largura_equivalente_e_estritamente_crescente_com_a_profundidade(
        fonte, a, b):
    """(c.2) a_eq e b_eq estritamente CRESCENTES em >= 4 profundidades.

    É a propriedade que distingue LARGURA de ESPESSURA, e o motivo central da
    decisão do a2 na v7: a espessura de camada não tem por que crescer com a
    profundidade (e não cresce — ver o contraexemplo em
    `test_espessura_das_camadas_nao_e_monotona_quando_z_max_corta`), enquanto
    a largura equivalente cresce necessariamente, porque Δσ decresce e a carga
    total se conserva. Se alguém voltar a alimentar o croqui com `espessura`
    no lugar de a_eq, este teste é o que cai.

    O alargamento é igual nas duas direções por construção (a_eq − a =
    b_eq − b), o que também é verificado aqui.
    """
    q = 200.0
    profundidades = (0.0, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0)   # 7 > 4 exigidas
    larguras_a, larguras_b = [], []
    for z in profundidades:
        ds = acrescimo_tensao(fonte, q, a, b, z)
        a_eq, b_eq = largura_equivalente(q, a, b, ds)
        assert a_eq - a == pytest.approx(b_eq - b, rel=1e-9, abs=1e-12)
        larguras_a.append(a_eq)
        larguras_b.append(b_eq)
    assert all(x < y for x, y in zip(larguras_a, larguras_a[1:]))
    assert all(x < y for x, y in zip(larguras_b, larguras_b[1:]))


@pytest.mark.parametrize("fonte", [FONTE_BOUSSINESQ, FONTE_2V1H])
@pytest.mark.parametrize("a,b", _GEOMETRIAS_DO_CROQUI)
def test_faixa_de_sanidade_da_largura_em_z_igual_a_2B(fonte, a, b):
    """(c.3) Em z = 2·B (B = min(a,b)): 2,7 <= a_eq/B <= 3,1.

    Faixa de sanidade de REQ-PROP-03 (F), medida nos dois métodos e em três
    geometrias. É o teste de TRANSCRIÇÃO: uma espessura de camada trocada por
    uma largura (ou vice-versa) passa ilesa por qualquer checagem dimensional,
    porque ambas são [length] — mas não passa por esta faixa. No perfil de
    referência, na mesma cota, as espessuras de trecho valem 2,5 e 3,0 m, isto
    é, h/B ~ 1,3 a 1,5: fora da faixa por larga margem.

    Valores medidos (não são normativos, são regressão): 2V:1H dá exatamente
    3,000 em toda geometria, porque a_eq = a + 2B e, aqui, a = B; Boussinesq
    dá 3,042 nas sapatas quadradas e 2,782 nas retangulares.
    """
    B = min(a, b)
    assert a == B, "fixture: 'a' deve ser o lado menor, senão a razão muda"
    q = 200.0
    z = 2.0 * B
    ds = acrescimo_tensao(fonte, q, a, b, z)
    a_eq, _ = largura_equivalente(q, a, b, ds)
    assert 2.7 <= a_eq / B <= 3.1, f"{fonte}: a_eq/B = {a_eq / B:.4f}"


@pytest.mark.parametrize("fonte", [FONTE_BOUSSINESQ, FONTE_2V1H])
def test_pressao_liquida_nula_deixa_a_largura_none_em_todos_os_pontos(fonte):
    """(c.4) q_líq = 0 -> a_eq e b_eq são None em TODOS os pontos.

    Trava o contrato que REQ-PROP-03 (E) obriga a UI a respeitar: sem pressão
    líquida não existe largura de espraiamento, e None é AUSÊNCIA de largura —
    não zero, e sobretudo não a dimensão da sapata. O idioma
    `largura_equivalente_a or dim` substituiria o None pela dimensão da sapata
    e a exibiria como largura calculada, ao lado de um Δσ = 0.

    O contrato é "None em todos os pontos", não "None em alguns": se um único
    ponto trouxesse número, a tela desenharia um tronco parcial e o engano
    voltaria por outra porta. O aviso de pressão líquida nula tem de vir
    junto, porque é ele que explica o traço no desenho.
    """
    solo = _solo(hf=1.5)
    sobrecarga = solo.sobrecarga_no_nivel_da_base()
    r = propagacao_em_profundidade(solo, 2.0, 3.0, sobrecarga, fonte=fonte)

    assert r.q_liquida == 0.0
    assert r.pontos, "fixture sem pontos: o teste não estaria testando nada"
    for p in r.pontos:
        assert p.largura_equivalente_a is None, p.rotulo
        assert p.largura_equivalente_b is None, p.rotulo
        assert p.delta_sigma == 0.0
    assert any("Pressão líquida nula" in aviso for aviso in r.avisos)


def test_espessura_das_camadas_nao_e_monotona_quando_z_max_corta():
    """(c.5) Contraexemplo que encerrou a leitura "L1/L2/L3 = espessuras".

    Perfil de referência (1,5 / 2,5 / 3,0 / 5,0 m) com a base em 1,5 m: abaixo
    da sapata sobram trechos de 2,5 / 3,0 / 5,0 m, crescentes por acaso da
    estratigrafia. Basta o teto de exibição `z_max` cair dentro de uma camada
    para a sequência EXIBIDA deixar de ser crescente:

        z_max = 6,0 m (corta a última)     -> 2,5 / 3,0 / 0,5
        z_max = 4,0 m (corta a penúltima)  -> 2,5 / 1,5

    Como z_max = 2·B é justamente o teto recomendado de exibição
    (REQ-UI-05), este é o caso NORMAL da tela, não uma borda exótica.

    A propriedade protegida é a distinção da v7: `espessura` é h_i, grandeza
    de TRECHO recortada pela estratigrafia e pelo teto de profundidade — não
    tem, e não deve ter, o comportamento monótono crescente de a_eq (ver
    `test_largura_equivalente_e_estritamente_crescente_com_a_profundidade`).
    Se um dia esta sequência passar a ser sempre crescente, ou alguém a ligou
    à largura, ou reintroduziu extrapolação da última camada.
    """
    solo = _solo(hf=1.5)

    r_cheio = propagacao_em_profundidade(solo, 2.0, 2.0, 200.0)
    assert [c.espessura for c in r_cheio.camadas] == pytest.approx(
        [2.5, 3.0, 5.0])

    r6 = propagacao_em_profundidade(solo, 2.0, 2.0, 200.0, z_max=6.0)
    espessuras6 = [c.espessura for c in r6.camadas]
    assert espessuras6 == pytest.approx([2.5, 3.0, 0.5])
    assert not all(x < y for x, y in zip(espessuras6, espessuras6[1:]))
    assert espessuras6[-1] < espessuras6[-2]

    r4 = propagacao_em_profundidade(solo, 2.0, 2.0, 200.0, z_max=4.0)
    espessuras4 = [c.espessura for c in r4.camadas]
    assert espessuras4 == pytest.approx([2.5, 1.5])
    assert not all(x < y for x, y in zip(espessuras4, espessuras4[1:]))

    # ... e, na MESMA análise, a largura por interface continua crescente:
    # duas famílias de grandeza, dois comportamentos, um só universo [length].
    larguras = [p.largura_equivalente_a for p in r4.pontos]
    assert all(x is not None for x in larguras)
    assert all(x < y for x, y in zip(larguras, larguras[1:]))
