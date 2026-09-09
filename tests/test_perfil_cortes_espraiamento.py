"""`visual2d.PerfilCortes` — corte de espraiamento por camada (REQ-UI-07).

Contexto (GATE 2, rodada 2, achados do a6 em `a00401e`, resolvidos aqui)
-------------------------------------------------------------------------
A rodada 1 reprovou (nota 3,78, veto E1/E5) por dois grupos de defeito:
símbolos errados no croqui ("L1/L2/L3" para largura, um único "q_i" por
CAMADA em vez de dois por INTERFACE) e um `_propagacao_atual` que
reconstituía `q_liquido + sobrecarga` em vez de usar `q_servico` — com dois
modos de falha reais (achados 4 e 5 do a6). O ruleset v7 fechou a definição
de símbolo (REQ-PROP-03) e o a4 exps `ResultadoSapata.q_servico` (commit
783b3c3) para eliminar a reconstituição.

Estes testes travam o comportamento NOVO de `_propagacao_atual` — função de
`(m: dict, fonte: str)`, testável SEM Tk (usa-se aqui um canvas de mentira,
que só precisa responder a `.bind()`) — e a lógica de degradação/mensagem que
`_espraiamento` usa a partir dela. Não abre `tkinter`: nada aqui desenha.
"""
from __future__ import annotations

import pytest

from calc_core.sapata_isolada.acoes import CasoCarga, Esforcos, Pilar, gerar_combinacoes
from calc_core.sapata_isolada.geotecnia import (
    AVISO_MEIO_HOMOGENEO,
    AVISO_NAO_NORMATIVO,
    FONTE_2V1H,
    FONTE_BOUSSINESQ,
    Camada,
    CamadaPropagacao,
    PerfilGeotecnico,
    PontoPropagacao,
    PropagacaoTensoes,
    ROTULO_FONTE,
    Solo,
    TipoSubstrato,
)
from calc_core.sapata_isolada.materiais import Aco, Concreto
from calc_core.sapata_isolada.sapata import OpcoesProjeto, Sapata
from calc_core.sapata_isolada.visual2d import DESTAQUE, TINTA_FRACA, PerfilCortes
from ui.completo.modelo import construir_modelo_visual


# --------------------------------------------------------------------- fixtures
class _CanvasFalso:
    """Substituto mínimo de `tk.Canvas` — `PerfilCortes.__init__` só chama
    `.bind()`. Nenhum teste aqui desenha; por isso não precisa de Tk/Xvfb."""

    def bind(self, sequencia, funcao) -> None:
        pass


def _perfil() -> PerfilGeotecnico:
    """Mesmo perfil de `test_propagacao_tensoes.py`/`test_pressao_servico_
    na_base.py`: 4 camadas, 12,0 m, N.A. a 3,0 m."""
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


def _dimensionar(*, com_perfil: bool = True, verificar_recalque: bool = True,
                 N: float = 800.0):
    """Mesmo caso de referência do a6/a2 (sapata 2,20 × 2,20 m) — é o caso
    em que o achado 6 mediu 'L = 6,69 m transbordando de uma sapata de
    2,20 m'."""
    solo = Solo(sigma_adm=200.0, hf=1.5,
                perfil=_perfil() if com_perfil else None)
    combs = gerar_combinacoes([CasoCarga("G", Esforcos(N=N))])
    s = Sapata(Pilar(ap=0.30, bp=0.30), solo, Concreto(25), Aco(500), combs,
               0.045, OpcoesProjeto(verificar_recalque=verificar_recalque))
    return s, solo, s.dimensionar()


def _modelo(**kwargs) -> dict:
    s, solo, res = _dimensionar(**kwargs)
    return construir_modelo_visual(s, res)


def _painel() -> PerfilCortes:
    return PerfilCortes(_CanvasFalso())


# ======================================================================== #
#  (a) round-trip de q_servico, sem reconstituição
# ======================================================================== #
def test_q_servico_passa_direto_do_modelo_para_o_nucleo():
    """`modelo['q_servico']` é o MESMO valor de `res.q_servico` (passagem
    simples de `construir_modelo_visual`) e é exatamente o que chega a
    `propagacao_em_profundidade` como `q_aplicada` — sem somar nem subtrair
    nada na UI [REQ-UI-06]."""
    s, solo, res = _dimensionar()
    m = construir_modelo_visual(s, res)
    assert m["q_servico"] == pytest.approx(res.q_servico, rel=1e-12)

    pc = _painel()
    prop = pc._propagacao_atual(m, FONTE_BOUSSINESQ)
    assert prop is not None
    assert prop.q_aplicada == pytest.approx(res.q_servico, rel=1e-12)


def test_q_servico_nao_e_reconstituido_por_soma(monkeypatch):
    """Trava a causa-raiz do achado 4: se alguém reintroduzir
    `q_liquido + sobrecarga`, este teste denuncia porque teria de reproduzir
    a MESMA conta duas vezes (uma no núcleo, outra na chamada). Aqui só
    confirmamos que remover `q_liquido` do modelo não muda o resultado —
    `_propagacao_atual` não olha mais para ele."""
    s, solo, res = _dimensionar()
    m = construir_modelo_visual(s, res)
    m_sem_q_liquido = dict(m)
    m_sem_q_liquido["q_liquido"] = None

    pc = _painel()
    prop_com = pc._propagacao_atual(m, FONTE_BOUSSINESQ)
    prop_sem = pc._propagacao_atual(m_sem_q_liquido, FONTE_BOUSSINESQ)
    assert prop_com.q_aplicada == pytest.approx(prop_sem.q_aplicada, rel=1e-12)


# ======================================================================== #
#  (b) z_max respeita 2*min(a, b) — REQ-UI-05
# ======================================================================== #
def test_z_max_e_2b_quando_perfil_e_profundo_o_bastante():
    m = _modelo()
    a, b = m["a"], m["b"]
    pc = _painel()
    prop = pc._propagacao_atual(m, FONTE_BOUSSINESQ)
    assert prop is not None
    assert prop.z_max == pytest.approx(2.0 * min(a, b), rel=1e-9)


def test_z_max_nao_e_2_vezes_max():
    """Mutante 'z_max = 2*max(a,b) trocado por 2*min' — geometria da sapata
    de referência é quadrada (2,20 × 2,20), então o teste usa um retângulo
    para o mutante não passar por acidente."""
    s, solo, res = _dimensionar()
    # Geometria não-quadrada explícita, sem depender do dimensionamento:
    m = construir_modelo_visual(s, res)
    m = dict(m)
    m["a"], m["b"] = 2.0, 4.0
    pc = _painel()
    prop = pc._propagacao_atual(m, FONTE_BOUSSINESQ)
    assert prop.z_max == pytest.approx(2.0 * min(2.0, 4.0), rel=1e-9)
    assert prop.z_max != pytest.approx(2.0 * max(2.0, 4.0), rel=1e-9)


# ======================================================================== #
#  (c) a fonte propagada é a passada por PARÂMETRO, não `self.fonte_
#      espraiamento` — a6, achado 1 e a6, achado 10 (mutante 5)
# ======================================================================== #
@pytest.mark.parametrize("fonte", [FONTE_BOUSSINESQ, FONTE_2V1H])
def test_fonte_propagada_corretamente_para_o_nucleo(fonte):
    m = _modelo()
    pc = _painel()
    prop = pc._propagacao_atual(m, fonte)
    assert prop.fonte == fonte
    assert prop.rotulo_metodo == ROTULO_FONTE[fonte]


def test_propagacao_atual_usa_o_parametro_fonte_nao_o_campo_de_instancia():
    """Mata o mutante 'self.fonte_espraiamento ignorado': `self.
    fonte_espraiamento` fica deliberadamente DIFERENTE do `fonte` passado —
    se a implementação lesse o campo em vez do parâmetro, devolveria o
    método errado."""
    m = _modelo()
    pc = _painel()
    pc.fonte_espraiamento = FONTE_BOUSSINESQ
    prop = pc._propagacao_atual(m, FONTE_2V1H)
    assert prop.fonte == FONTE_2V1H


def test_rotulo_do_banner_vem_de_prop_rotulo_metodo_nao_do_estado_da_ui():
    """REQ-UI-07(f) / a6, achado 1: o rótulo do banner tem de vir de
    `prop.rotulo_metodo`, mesmo que `self.fonte_espraiamento` esteja
    (propositalmente, aqui) desalinhado do que gerou `prop`."""
    m = _modelo()
    pc = _painel()
    prop_2v1h = pc._propagacao_atual(m, FONTE_2V1H)
    pc.fonte_espraiamento = FONTE_BOUSSINESQ   # desalinhado de propósito
    linhas = pc._linhas_banner_espraiamento(prop_2v1h)
    textos = [t for t, _f, _c in linhas]
    assert any(ROTULO_FONTE[FONTE_2V1H] in t for t in textos)
    assert not any(ROTULO_FONTE[FONTE_BOUSSINESQ] in t for t in textos)


# ======================================================================== #
#  (d) ValueError do núcleo propaga (não é engolida) e é distinguível de
#      "sem perfil/solo" — a6, achado 5
# ======================================================================== #
def test_valueerror_do_nucleo_nao_e_engolida():
    m = _modelo()
    m = dict(m)
    m["q_servico"] = -5.0   # guarda de domínio do núcleo: q_aplicada >= 0
    pc = _painel()
    with pytest.raises(ValueError):
        pc._propagacao_atual(m, FONTE_BOUSSINESQ)


def test_mensagem_de_erro_e_distinta_da_mensagem_de_sem_perfil():
    pc = _painel()
    m = _modelo()
    m_invalido = dict(m)
    m_invalido["q_servico"] = -5.0
    try:
        pc._propagacao_atual(m_invalido, FONTE_BOUSSINESQ)
        assert False, "deveria ter levantado ValueError"
    except ValueError as e:
        erro = str(e)

    texto_erro, cor_erro = pc._mensagem_indisponivel(None, erro)
    texto_generico, cor_generico = pc._mensagem_indisponivel(None, None)

    assert texto_erro == erro
    assert cor_erro == DESTAQUE
    assert texto_generico != erro
    assert "sem perfil" in texto_generico.lower() or \
        "sem perfil" in texto_generico.lower()
    assert cor_generico == TINTA_FRACA


# ======================================================================== #
#  (e) degradação correta: depende de solo/perfil, NUNCA de q_liquido — a6,
#      achado 4 (o defeito original: com verificar_recalque=False a tela
#      culpava o perfil mesmo com ele presente)
# ======================================================================== #
def test_sem_perfil_devolve_none_mesmo_com_q_servico_definido():
    m = _modelo(com_perfil=False)
    assert m["q_servico"] is not None and m["q_servico"] > 0
    pc = _painel()
    assert pc._propagacao_atual(m, FONTE_BOUSSINESQ) is None


def test_verificar_recalque_falso_com_perfil_presente_nao_degrada():
    """O defeito relatado pelo a6: `verificar_recalque=False` fazia
    `res.recalques` ser `None`, e a UI antiga não tinha de onde tirar
    `q_aplicada` — mesmo com o perfil geotécnico presente. Com `q_servico`
    (calculado sempre, fora do `if` de recalque), o corte aparece."""
    s, solo, res = _dimensionar(verificar_recalque=False)
    assert res.recalques is None   # a pré-condição do defeito original
    m = construir_modelo_visual(s, res)
    assert m["q_servico"] is not None

    pc = _painel()
    prop = pc._propagacao_atual(m, FONTE_BOUSSINESQ)
    assert prop is not None
    assert prop.camadas   # o croqui tem o que desenhar


# ======================================================================== #
#  Símbolos e degradação de largura indefinida — REQ-UI-07(e)
# ======================================================================== #
def test_sem_largura_definida_quando_q_liquido_e_zero():
    """q_servico igual à sobrecarga geostática -> q_líquido = 0 -> largura
    equivalente None em TODOS os pontos (garantido pelo núcleo). A UI não
    deve inventar nenhum número no lugar."""
    solo = Solo(sigma_adm=200.0, hf=1.5, perfil=_perfil())
    sobrecarga = solo.sobrecarga_no_nivel_da_base()
    pontos = (
        PontoPropagacao(z=0.0, profundidade=1.5, delta_sigma=0.0,
                        largura_equivalente_a=None,
                        largura_equivalente_b=None,
                        rotulo="base da sapata", fonte=FONTE_BOUSSINESQ),
        PontoPropagacao(z=1.0, profundidade=2.5, delta_sigma=0.0,
                        largura_equivalente_a=None,
                        largura_equivalente_b=None,
                        rotulo="base de 'Areia média'", fonte=FONTE_BOUSSINESQ),
    )
    camadas = (
        CamadaPropagacao(indice=0, nome="Areia média", tipo="granular",
                         z_topo=0.0, z_base=1.0, espessura=1.0,
                         delta_sigma_topo=0.0, delta_sigma_base=0.0,
                         delta_sigma_medio=0.0, fonte=FONTE_BOUSSINESQ),
    )
    prop = PropagacaoTensoes(
        fonte=FONTE_BOUSSINESQ, rotulo_metodo=ROTULO_FONTE[FONTE_BOUSSINESQ],
        q_aplicada=sobrecarga, sobrecarga_na_base=sobrecarga, q_liquida=0.0,
        a=2.2, b=2.2, z_base_sapata=1.5, z_max=1.0,
        pontos=pontos, camadas=camadas,
        avisos=(AVISO_NAO_NORMATIVO, AVISO_MEIO_HOMOGENEO,
               "Pressão líquida nula: ..."))

    pc = _painel()
    assert pc._sem_largura_definida(prop, "a") is True
    assert pc._sem_largura_definida(prop, "b") is True

    texto, cor = pc._mensagem_indisponivel(prop, None)
    assert "líquida nula" in texto.lower() or "liquida nula" in texto.lower()
    assert cor == TINTA_FRACA


def test_com_largura_definida_nao_e_sinalizado_como_indefinida():
    m = _modelo()
    pc = _painel()
    prop = pc._propagacao_atual(m, FONTE_BOUSSINESQ)
    assert pc._sem_largura_definida(prop, "a") is False
    # a_eq(z=0) == a exatamente (REQ-PROP-03 (F))
    assert prop.pontos[0].largura_equivalente_a == pytest.approx(m["a"])


# ======================================================================== #
#  Ressalva do 2V:1H promovida ao topo (a6, achado 8) e não duplicada no
#  rodapé
# ======================================================================== #
def test_ressalva_2v1h_e_identificada_e_promovida():
    m = _modelo()
    pc = _painel()
    pc.fonte_espraiamento = FONTE_2V1H
    prop = pc._propagacao_atual(m, FONTE_2V1H)

    ressalva = pc._ressalva_2v1h(prop)
    assert ressalva is not None
    assert "2V:1H" in ressalva

    linhas = pc._linhas_banner_espraiamento(prop)
    textos_banner = [t for t, _f, _c in linhas]
    assert any(ressalva in t for t in textos_banner)

    # não duplicada no rodapé
    extras = pc._avisos_nao_promovidos(prop)
    assert ressalva not in extras


def test_boussinesq_nao_promove_ressalva_do_2v1h():
    m = _modelo()
    pc = _painel()
    pc.fonte_espraiamento = FONTE_BOUSSINESQ
    prop = pc._propagacao_atual(m, FONTE_BOUSSINESQ)
    linhas = pc._linhas_banner_espraiamento(prop)
    textos_banner = " ".join(t for t, _f, _c in linhas)
    assert "2V:1H" not in textos_banner
    # a ressalva PRÓPRIA do Boussinesq (leitura ilustrativa) aparece:
    assert "ilustrativa" in textos_banner.lower()


# ======================================================================== #
#  Proibição de símbolo — nenhum rótulo usa "L"/"L1/L2/L3"/"B_eq"
# ======================================================================== #
def test_nenhum_rotulo_do_banner_usa_simbolos_proibidos():
    m = _modelo()
    pc = _painel()
    for fonte in (FONTE_BOUSSINESQ, FONTE_2V1H):
        prop = pc._propagacao_atual(m, fonte)
        for texto, _f, _c in pc._linhas_banner_espraiamento(prop):
            assert "B_eq" not in texto
