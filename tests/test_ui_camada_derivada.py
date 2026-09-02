"""
Testes de `ui/completo/formulario.py::PainelEntrada` (REQ-UI-CAMADA-01 a 05,
07) e de `ui/completo/app.py::AppSapataCompleto._importar_excel` (REQ-UI-
CAMADA-06) — `ruleset.yaml`, bloco `requisitos_para_a3`, backlog #12:
"Camada única de dados: φ'/c'/γ na base derivados da camada em h_f".

Segue o mesmo padrão Tk headless de `test_projeto_e_excel.py`/
`test_ui_sigma_adm.py`: `pytest.importorskip("tkinter")`, `tk.Tk()` dentro de
um `try/except TclError` (skip sem display), `root.withdraw()`,
`painel.wait_window = lambda w: None` + `mock.patch(".../DialogoCamada", ...)`
para simular os diálogos modais sem loop de janela real.

NENHUM CÁLCULO NOVO É TESTADO AQUI (CLAUDE.md regra 4): todo número esperado
sai de `Camada.gamma`/`Camada.phi`/`Camada.coesao`/`PerfilGeotecnico.
camada_em`/`PerfilGeotecnico.profundidade_total`, já aprovados no escopo
amplo — esta suíte só confere que a TELA lê e propaga esses valores
corretamente para os três campos soltos.
"""
from __future__ import annotations

import inspect
from dataclasses import replace
from unittest import mock

import pytest

from calc_core.sapata_isolada.geotecnia import Camada, PerfilGeotecnico, Solo

# Imports de `ui.completo` ficam dentro de cada função de teste — mesmo
# motivo já documentado em `test_ui_sigma_adm.py`/`test_projeto_e_excel.py`:
# um ambiente sem `tkinter` não pode abortar a coleta da suíte inteira.


def _tk_root():
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("sem display Tk disponível neste ambiente (Xvfb)")
    root.withdraw()
    return root


def _camada_aterro() -> Camada:
    return Camada(nome="Aterro", espessura=1.0, phi=28.0, coesao=5.0,
                  gamma_nat=17.0, gamma_sat=19.0)


def _camada_areia() -> Camada:
    return Camada(nome="Areia", espessura=2.0, phi=34.0, coesao=0.0,
                  gamma_nat=18.0, gamma_sat=20.0)


def _adicionar_camada_via_ui(painel, camada: Camada) -> None:
    """Simula "+ camada" (`_adicionar_camada`) com `DialogoCamada` mockado
    devolvendo `camada` — mesmo padrão de `test_editar_camada_substitui_
    na_posicao_preservando_ordem` (`test_projeto_e_excel.py`)."""
    from ui.completo.formulario import DialogoCamada  # noqa: F401

    class _DialogoFalso:
        def __init__(self, master):
            self.resultado = camada

    painel.wait_window = lambda w: None
    with mock.patch("ui.completo.formulario.DialogoCamada", _DialogoFalso):
        painel._adicionar_camada()


def _editar_camada_via_ui(painel, indice: int, camada_editada: Camada) -> None:
    item_id = painel.tree_camadas.get_children()[indice]
    painel.tree_camadas.selection_set(item_id)

    class _DialogoFalso:
        def __init__(self, master, camada_inicial=None):
            self.resultado = camada_editada

    painel.wait_window = lambda w: None
    with mock.patch("ui.completo.formulario.DialogoCamada", _DialogoFalso):
        painel._editar_camada()


def _remover_camada_via_ui(painel, indice: int) -> None:
    item_id = painel.tree_camadas.get_children()[indice]
    painel.tree_camadas.selection_set(item_id)
    painel._remover_camada()


# =============================================================================
#  REQ-UI-CAMADA-01 — gatilho e fonte da derivação
# =============================================================================
def test_adicionar_camadas_deriva_phi_coesao_gamma_da_camada_em_hf():
    """Critério 1: perfil [Aterro(1.0m), Areia(2.0m)], N.A. vazio,
    h_f = 1,50 -> adicionar a segunda camada pela UI deixa v_phi_solo ==
    "34", v_coesao == "0" e v_gamma_solo == "18" (camada "Areia",
    gamma_nat porque N.A. ausente)."""
    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        assert painel.v_hf.get() == "1.5"   # default da tela
        _adicionar_camada_via_ui(painel, _camada_aterro())
        _adicionar_camada_via_ui(painel, _camada_areia())

        assert painel.v_phi_solo.get() == "34"
        assert painel.v_coesao.get() == "0"
        assert painel.v_gamma_solo.get() == "18"
    finally:
        root.destroy()


def test_derivacao_com_na_acima_da_camada_usa_gamma_saturado():
    """Critério 2: mesmo perfil com N.A. = 1,20 e h_f = 1,50 ->
    v_gamma_solo == "20" (gamma_sat, abaixo_na verdadeiro)."""
    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        _adicionar_camada_via_ui(painel, _camada_aterro())
        painel.v_nivel_agua.set("1,20")   # vírgula decimal
        _adicionar_camada_via_ui(painel, _camada_areia())

        assert painel.v_gamma_solo.get() == "20"
    finally:
        root.destroy()


def test_desempate_hf_na_interface_pertence_a_camada_de_baixo():
    """Critério 3: h_f = 1,00 (exatamente a interface) deriva da camada
    "Areia", não da "Aterro"; h_f = 1,20 com N.A. = 1,20 deriva
    gamma_nat = 18, não 20 (N.A. == h_f conta como ACIMA, `>` estrito)."""
    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        _adicionar_camada_via_ui(painel, _camada_aterro())
        _adicionar_camada_via_ui(painel, _camada_areia())

        painel.v_hf.set("1.00")
        assert painel.v_phi_solo.get() == "34"   # Areia, não Aterro (phi=28)

        painel.v_nivel_agua.set("1.20")
        painel.v_hf.set("1.20")
        assert painel.v_gamma_solo.get() == "18"   # gamma_nat da Areia
    finally:
        root.destroy()


def test_editar_camada_que_contem_hf_e_que_nao_contem_hf_mantem_coerencia():
    """Critério 4: editar a camada que contém h_f atualiza os três campos;
    editar uma camada que NÃO contém h_f também roda a derivação e os três
    campos permanecem coerentes com a camada em h_f."""
    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        _adicionar_camada_via_ui(painel, _camada_aterro())
        _adicionar_camada_via_ui(painel, _camada_areia())
        painel.v_hf.set("1.5")   # dentro da camada "Areia" (1.0 - 3.0)
        assert painel.v_phi_solo.get() == "34"

        # editar a camada que CONTÉM h_f (índice 1, "Areia")
        areia_editada = replace(_camada_areia(), phi=40.0)
        _editar_camada_via_ui(painel, 1, areia_editada)
        assert painel.v_phi_solo.get() == "40"

        # editar a camada que NÃO contém h_f (índice 0, "Aterro") — a
        # derivação roda de novo, mas continua coerente com "Areia"
        # (espessura do Aterro preservada, então a fronteira não se move)
        aterro_editado = replace(_camada_aterro(), phi=99.0)
        _editar_camada_via_ui(painel, 0, aterro_editado)
        assert painel.v_phi_solo.get() == "40"   # ainda a Areia editada
        assert painel.ultima_derivacao_de_camada["nome_camada"] == "Areia"
    finally:
        root.destroy()


def test_hf_com_virgula_decimal_deriva_igual_a_ponto():
    """Critério 5: digitar "1,80" (vírgula) em v_hf deriva da mesma camada
    que "1.80"."""
    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        _adicionar_camada_via_ui(painel, _camada_aterro())
        _adicionar_camada_via_ui(painel, _camada_areia())

        painel.v_hf.set("1.80")
        esperado = (painel.v_phi_solo.get(), painel.v_gamma_solo.get(),
                    painel.v_coesao.get())

        painel.v_hf.set("1,80")
        assert (painel.v_phi_solo.get(), painel.v_gamma_solo.get(),
                painel.v_coesao.get()) == esperado
        assert painel.v_phi_solo.get() == "34"
    finally:
        root.destroy()


# =============================================================================
#  REQ-UI-CAMADA-02 — guardas de recusa e extrapolação nunca silenciosa
# =============================================================================
def test_sem_camadas_nao_deriva():
    """Critério 1: sem camadas, escrever "2.0" em v_hf não altera nenhum
    dos três campos e ultima_derivacao_de_camada is None."""
    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        assert not painel._camadas
        antes = (painel.v_gamma_solo.get(), painel.v_phi_solo.get(),
                 painel.v_coesao.get())
        painel.v_hf.set("2.0")
        assert (painel.v_gamma_solo.get(), painel.v_phi_solo.get(),
                painel.v_coesao.get()) == antes
        assert painel.ultima_derivacao_de_camada is None
    finally:
        root.destroy()


def test_hf_em_estado_de_digitacao_nao_levanta_excecao_nem_altera_campos():
    """Critério 2: com perfil válido, escrever "abc", "" ou "1.e" em v_hf:
    nenhuma exceção propaga, nenhum messagebox é aberto, os três campos
    ficam como estavam."""
    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        _adicionar_camada_via_ui(painel, _camada_aterro())
        _adicionar_camada_via_ui(painel, _camada_areia())
        painel.v_hf.set("1.5")
        estado = (painel.v_gamma_solo.get(), painel.v_phi_solo.get(),
                  painel.v_coesao.get())

        with mock.patch("ui.completo.formulario.messagebox.showerror"
                        ) as erro:
            for texto in ("abc", "", "1.e"):
                painel.v_hf.set(texto)   # não pode levantar
        assert not erro.called
        assert (painel.v_gamma_solo.get(), painel.v_phi_solo.get(),
                painel.v_coesao.get()) == estado
    finally:
        root.destroy()


def test_hf_negativo_ou_zero_nao_deriva_da_camada_mais_profunda():
    """Critério 3: h_f = "-1" ou "0": nenhuma derivação; em particular
    v_phi_solo NÃO recebe o phi da camada mais profunda."""
    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        _adicionar_camada_via_ui(painel, _camada_aterro())
        # camada de fundo, com phi bem distinto (99) para detectar vazamento
        _adicionar_camada_via_ui(painel, replace(_camada_areia(), phi=99.0))
        painel.v_hf.set("1.5")
        assert painel.v_phi_solo.get() == "99"

        painel.v_phi_solo.set("30")   # reseta manualmente (invalida também)
        assert painel.ultima_derivacao_de_camada is None

        painel.v_hf.set("-1")
        assert painel.v_phi_solo.get() == "30"
        painel.v_hf.set("0")
        assert painel.v_phi_solo.get() == "30"
        assert painel.ultima_derivacao_de_camada is None
    finally:
        root.destroy()


def test_extrapolacao_abaixo_do_perfil_deriva_mas_avisa_em_texto():
    """Critério 4: perfil de 3,00 m e h_f = 4,00: os três campos são
    preenchidos com a camada de fundo,
    ultima_derivacao_de_camada["extrapolada"] is True e lbl_solo_derivado
    contém a profundidade total do perfil e a informação de que h_f está
    abaixo dela."""
    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        _adicionar_camada_via_ui(painel, _camada_aterro())          # 1.0 m
        _adicionar_camada_via_ui(painel, _camada_areia())           # + 2.0 m = 3.0 m

        painel.v_hf.set("4.00")

        assert painel.v_phi_solo.get() == "34"   # camada de fundo (Areia)
        assert painel.ultima_derivacao_de_camada["extrapolada"] is True
        texto = painel.lbl_solo_derivado.cget("text")
        assert "3" in texto
        assert "abaixo" in texto.lower()
    finally:
        root.destroy()


def test_na_com_texto_invalido_nao_deriva_sem_excecao():
    """Critério 5: N.A. com texto inválido ("x"): sem derivação, sem
    exceção."""
    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        _adicionar_camada_via_ui(painel, _camada_aterro())
        _adicionar_camada_via_ui(painel, _camada_areia())
        painel.v_hf.set("1.5")
        estado = (painel.v_gamma_solo.get(), painel.v_phi_solo.get(),
                  painel.v_coesao.get())

        painel.v_nivel_agua.set("x")   # não pode levantar
        assert (painel.v_gamma_solo.get(), painel.v_phi_solo.get(),
                painel.v_coesao.get()) == estado
    finally:
        root.destroy()


# =============================================================================
#  REQ-UI-CAMADA-03 — proveniência conjunta e invalidação pelos três
# =============================================================================
def test_derivacao_bem_sucedida_grava_sete_chaves_e_rotulo():
    """Critério 1: após uma derivação bem-sucedida,
    ultima_derivacao_de_camada é um dict com as sete chaves e
    lbl_solo_derivado.cget("text") contém o nome da camada e o h_f
    usado."""
    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        _adicionar_camada_via_ui(painel, _camada_aterro())
        _adicionar_camada_via_ui(painel, _camada_areia())
        painel.v_hf.set("1.5")

        info = painel.ultima_derivacao_de_camada
        assert set(info.keys()) == {"nome_camada", "hf", "abaixo_na",
                                    "gamma", "phi", "coesao", "extrapolada"}
        texto = painel.lbl_solo_derivado.cget("text")
        assert "Areia" in texto
        assert "1.5" in texto
    finally:
        root.destroy()


@pytest.mark.parametrize("campo", ["v_gamma_solo", "v_phi_solo", "v_coesao"])
def test_editar_manualmente_qualquer_um_dos_tres_invalida_os_tres(campo):
    """Critério 2: painel.v_phi_solo.set("31") (edição manual simulada)
    zera ultima_derivacao_de_camada E esvazia o rótulo; idem para
    v_gamma_solo e para v_coesao."""
    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        _adicionar_camada_via_ui(painel, _camada_aterro())
        _adicionar_camada_via_ui(painel, _camada_areia())
        painel.v_hf.set("1.5")
        assert painel.ultima_derivacao_de_camada is not None

        getattr(painel, campo).set("31")
        assert painel.ultima_derivacao_de_camada is None
        assert painel.lbl_solo_derivado.cget("text") == ""
    finally:
        root.destroy()


def test_redigitar_mesmo_texto_da_derivacao_tambem_invalida():
    """Critério 3: redigitar no campo exatamente o mesmo texto que a
    derivação escreveu também invalida (rótulo vazio)."""
    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        _adicionar_camada_via_ui(painel, _camada_aterro())
        _adicionar_camada_via_ui(painel, _camada_areia())
        painel.v_hf.set("1.5")
        valor_derivado = painel.v_phi_solo.get()
        assert valor_derivado == "34"

        painel.v_phi_solo.set(valor_derivado)   # mesmo texto, "digitado"
        assert painel.ultima_derivacao_de_camada is None
        assert painel.lbl_solo_derivado.cget("text") == ""
    finally:
        root.destroy()


def test_derivacao_nao_se_autoinvalida():
    """Critério 4: a derivação NÃO se autoinvalida: logo após
    `_derivar_solo_da_camada()`, ultima_derivacao_de_camada is not
    None."""
    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        _adicionar_camada_via_ui(painel, _camada_aterro())
        _adicionar_camada_via_ui(painel, _camada_areia())
        painel.v_hf.set("1.5")
        painel._derivar_solo_da_camada()
        assert painel.ultima_derivacao_de_camada is not None
    finally:
        root.destroy()


def test_preenchendo_solo_derivado_volta_a_false_mesmo_com_excecao():
    """Critério 5: `_preenchendo_solo_derivado` volta a False mesmo se um
    .set() levantar exceção (bloco finally)."""
    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        _adicionar_camada_via_ui(painel, _camada_aterro())
        _adicionar_camada_via_ui(painel, _camada_areia())
        painel.v_hf.set("1.5")   # deriva uma vez com sucesso

        def _explode(*_a, **_k):
            raise RuntimeError("boom")

        painel.v_phi_solo.set = _explode
        with pytest.raises(RuntimeError):
            painel._derivar_solo_da_camada()
        assert painel._preenchendo_solo_derivado is False
    finally:
        root.destroy()


# =============================================================================
#  REQ-UI-CAMADA-04 — preencher_solo não deriva e a assimetria do guard
# =============================================================================
def _perfil_com_camada_em_1_5m() -> PerfilGeotecnico:
    return PerfilGeotecnico(camadas=[
        Camada(nome="Camada arquivo", espessura=3.0, phi=34.0, coesao=0.0,
              gamma_nat=20.0, gamma_sat=20.0)])


def test_preencher_solo_usa_valores_do_arquivo_nao_da_camada():
    """Critério 1: preencher_solo com Solo(sigma_adm=250, gamma_solo=15,
    hf=1.5, phi=22, coesao=7, perfil=<camada em 1,5 m tem phi=34,
    coesao=0, gamma=20>) deixa v_gamma_solo == "15", v_phi_solo == "22" e
    v_coesao == "7" — os valores do arquivo, NÃO os da camada."""
    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        solo = Solo(sigma_adm=250.0, gamma_solo=15.0, hf=1.5, phi=22.0,
                   coesao=7.0, perfil=_perfil_com_camada_em_1_5m())
        painel.preencher_solo(solo)

        assert painel.v_gamma_solo.get() == "15"
        assert painel.v_phi_solo.get() == "22"
        assert painel.v_coesao.get() == "7"
    finally:
        root.destroy()


def test_preencher_solo_deixa_provenencia_invalida():
    """Critério 2: após essa chamada, ultima_derivacao_de_camada is None e
    lbl_solo_derivado.cget("text") == ""."""
    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        solo = Solo(sigma_adm=250.0, gamma_solo=15.0, hf=1.5, phi=22.0,
                   coesao=7.0, perfil=_perfil_com_camada_em_1_5m())
        painel.preencher_solo(solo)

        assert painel.ultima_derivacao_de_camada is None
        assert painel.lbl_solo_derivado.cget("text") == ""
    finally:
        root.destroy()


def test_carregar_projeto_b_depois_de_a_nao_deixa_estratigrafia_de_a():
    """Critério 3: carregar um projeto A (perfil A) e em seguida um
    projeto B (perfil B) não deixa nenhum dos três campos com valor da
    estratigrafia de A."""
    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        perfil_a = PerfilGeotecnico(camadas=[
            Camada(nome="Camada A", espessura=3.0, phi=15.0, coesao=1.0,
                  gamma_nat=16.0, gamma_sat=16.0)])
        solo_a = Solo(sigma_adm=200.0, gamma_solo=16.0, hf=1.5, phi=15.0,
                     coesao=1.0, perfil=perfil_a)
        painel.preencher_solo(solo_a)
        assert [c.nome for c in painel._camadas] == ["Camada A"]

        perfil_b = PerfilGeotecnico(camadas=[
            Camada(nome="Camada B", espessura=3.0, phi=44.0, coesao=9.0,
                  gamma_nat=21.0, gamma_sat=21.0)])
        solo_b = Solo(sigma_adm=300.0, gamma_solo=21.0, hf=1.5, phi=44.0,
                     coesao=9.0, perfil=perfil_b)
        painel.preencher_solo(solo_b)

        assert [c.nome for c in painel._camadas] == ["Camada B"]
        nomes_tree = [painel.tree_camadas.item(i, "values")[0]
                      for i in painel.tree_camadas.get_children()]
        assert nomes_tree == ["Camada B"]
        # e o valor da tela é o do arquivo B, não uma mistura com A
        assert painel.v_phi_solo.get() == "44"
    finally:
        root.destroy()


def test_apos_carregar_projeto_editar_hf_deriva_normalmente():
    """Critério 4: depois do carregamento, escrever "1.8" em v_hf deriva
    normalmente do perfil recém-carregado e o rótulo volta a aparecer."""
    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        solo = Solo(sigma_adm=250.0, gamma_solo=15.0, hf=1.5, phi=22.0,
                   coesao=7.0, perfil=_perfil_com_camada_em_1_5m())
        painel.preencher_solo(solo)
        assert painel.ultima_derivacao_de_camada is None

        painel.v_hf.set("1.8")
        assert painel.ultima_derivacao_de_camada is not None
        assert painel.v_phi_solo.get() == "34"   # da camada do arquivo
        assert painel.lbl_solo_derivado.cget("text") != ""
    finally:
        root.destroy()


def test_carregando_solo_volta_a_false_mesmo_com_excecao():
    """Critério 5: _carregando_solo volta a False mesmo se preencher_solo
    levantar exceção no meio."""
    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)

        def _explode(*_a, **_k):
            raise RuntimeError("boom")

        painel.v_coesao.set = _explode
        solo = Solo(sigma_adm=250.0, gamma_solo=15.0, hf=1.5, phi=22.0,
                   coesao=7.0, perfil=_perfil_com_camada_em_1_5m())
        with pytest.raises(RuntimeError):
            painel.preencher_solo(solo)
        assert painel._carregando_solo is False
    finally:
        root.destroy()


# =============================================================================
#  REQ-UI-CAMADA-05 — gamma_solo tem dois papéis e o aviso é obrigatório
# =============================================================================
def test_derivacao_abaixo_do_na_diz_que_gamma_e_o_saturado():
    """Critério 1: derivação com abaixo_na = True: lbl_solo_derivado
    contém a informação de que o γ exibido é o saturado/total da
    camada."""
    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        _adicionar_camada_via_ui(painel, _camada_aterro())
        painel.v_nivel_agua.set("0.5")
        _adicionar_camada_via_ui(painel, _camada_areia())
        painel.v_hf.set("1.5")

        assert painel.ultima_derivacao_de_camada["abaixo_na"] is True
        texto = painel.lbl_solo_derivado.cget("text").upper()
        assert "SATURADO" in texto
    finally:
        root.destroy()


def test_remover_ultima_camada_com_provenencia_valida_avisa_troca_de_papel():
    """Critérios 2 e 3: remover a última camada com proveniência válida:
    ultima_derivacao_de_camada is None e há na tela texto visível dizendo
    que γ_solo passa a valer como sobrecarga na cota da base e que abaixo
    do N.A. o valor pedido é o efetivo, não o saturado. A remoção NÃO
    altera o número em v_gamma_solo e NÃO abre messagebox modal."""
    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        _adicionar_camada_via_ui(painel, _camada_areia())
        painel.v_hf.set("1.5")
        assert painel.ultima_derivacao_de_camada is not None
        gamma_antes = painel.v_gamma_solo.get()

        with mock.patch("ui.completo.formulario.messagebox.showwarning"
                        ) as aviso, \
             mock.patch("ui.completo.formulario.messagebox.showinfo"
                        ) as info, \
             mock.patch("ui.completo.formulario.messagebox.showerror"
                        ) as erro:
            _remover_camada_via_ui(painel, 0)
            assert not aviso.called
            assert not info.called
            assert not erro.called

        assert painel.ultima_derivacao_de_camada is None
        assert painel.v_gamma_solo.get() == gamma_antes

        texto = painel.lbl_solo_derivado.cget("text").lower()
        assert "sobrecarga" in texto and "base" in texto
        assert "efetivo" in texto and "saturado" in texto
    finally:
        root.destroy()


def test_nenhum_texto_chama_gamma_derivado_de_peso_do_maciço_sobrejacente():
    """Critério 4: nenhum texto da tela chama o γ derivado de peso do
    maciço sobrejacente, peso médio ou equivalente."""
    from ui.completo.formulario import AVISO_TRANSICAO_PERFIL_VAZIO, \
        PainelEntrada

    proibidos = ("peso do maciço sobrejacente", "peso médio", "peso medio")
    for termo in proibidos:
        assert termo not in AVISO_TRANSICAO_PERFIL_VAZIO.lower()

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        _adicionar_camada_via_ui(painel, _camada_aterro())
        painel.v_nivel_agua.set("0.5")
        _adicionar_camada_via_ui(painel, _camada_areia())
        painel.v_hf.set("1.5")
        texto = painel.lbl_solo_derivado.cget("text").lower()
        for termo in proibidos:
            assert termo not in texto
    finally:
        root.destroy()


# =============================================================================
#  D-01 do GATE 2, rodada 1 (a6-revisor sobre o commit 4ddc26b) — o aviso de
#  transição de perfil vazio (REQ-UI-CAMADA-05, Exigência 1) tem de
#  PERSISTIR através de edição manual de QUALQUER um dos três campos
#  derivados, e só pode ser desligado por uma NOVA derivação bem-sucedida
#  (perfil recomposto) ou por `preencher_solo` (regime novo,
#  REQ-UI-CAMADA-04). A versão reprovada escrevia o aviso DIRETO no
#  `Label` dentro de `_remover_camada`, fora de
#  `_atualizar_rotulo_solo_derivado()` — um terceiro estado e um segundo
#  escritor — e qualquer `.set()` subsequente em v_gamma_solo/v_phi_solo/
#  v_coesao apagava o aviso via `_ao_editar_solo_derivado`, mesmo que
#  γ_solo continuasse com o valor SATURADO (lado inseguro, medido pelo a6:
#  +27% na sobrecarga na cota da base, tendendo a fator ~2).
# =============================================================================
@pytest.mark.parametrize("campo,valor", [("v_phi_solo", "40"),
                                          ("v_coesao", "9"),
                                          ("v_gamma_solo", "21")])
def test_aviso_perfil_vazio_persiste_apos_edicao_manual_de_qualquer_campo(
        campo, valor):
    """Reproduz o cenário do defeito D-01: perfil com N.A. (γ derivado =
    γ_sat), remover a última camada (aviso aparece corretamente), editar
    manualmente UM dos três campos que NÃO seja necessariamente γ_solo — o
    aviso tem de continuar visível e idêntico, não sumir."""
    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        _adicionar_camada_via_ui(painel, _camada_areia())
        painel.v_nivel_agua.set("0.5")
        painel.v_hf.set("1.5")
        assert painel.ultima_derivacao_de_camada is not None
        assert painel.ultima_derivacao_de_camada["abaixo_na"] is True

        _remover_camada_via_ui(painel, 0)
        aviso = painel.lbl_solo_derivado.cget("text")
        assert aviso != ""
        assert "sobrecarga" in aviso.lower()

        # edição manual do campo (inclusive um que NÃO seja γ_solo) — o
        # aviso é sobre um REGIME que já mudou, não sobre proveniência,
        # e não pode ser apagado por esta via.
        getattr(painel, campo).set(valor)

        assert painel.ultima_derivacao_de_camada is None
        assert painel.lbl_solo_derivado.cget("text") == aviso
    finally:
        root.destroy()


def test_aviso_perfil_vazio_e_desligado_so_por_nova_derivacao_bem_sucedida():
    """Complemento do D-01: só uma NOVA derivação bem-sucedida (perfil
    recomposto) substitui o aviso de transição de perfil vazio — não a
    edição manual dos três campos, que apenas invalida a proveniência sem
    tocar no aviso."""
    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        _adicionar_camada_via_ui(painel, _camada_areia())
        painel.v_hf.set("1.5")
        _remover_camada_via_ui(painel, 0)
        assert painel.lbl_solo_derivado.cget("text") != ""
        assert painel._aviso_perfil_vazio is True

        # perfil recomposto — a derivação seguinte tem de DESLIGAR o
        # aviso e voltar ao texto normal de proveniência.
        _adicionar_camada_via_ui(painel, _camada_aterro())
        texto = painel.lbl_solo_derivado.cget("text")
        assert painel._aviso_perfil_vazio is False
        assert "derivad" in texto.lower()
        assert "sobrecarga" not in texto.lower()
        assert painel.ultima_derivacao_de_camada is not None
    finally:
        root.destroy()


def test_preencher_solo_apaga_aviso_de_perfil_vazio_ativo():
    """Decorrência do D-01: `preencher_solo` (carregamento de projeto ou
    de Excel) é um regime NOVO — mesmo que o aviso de transição de perfil
    vazio estivesse ativo antes da chamada, REQ-UI-CAMADA-04 exige rótulo
    VAZIO (não o aviso residual) depois dela."""
    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        _adicionar_camada_via_ui(painel, _camada_areia())
        painel.v_hf.set("1.5")
        _remover_camada_via_ui(painel, 0)
        assert painel.lbl_solo_derivado.cget("text") != ""

        solo = Solo(sigma_adm=250.0, gamma_solo=15.0, hf=1.5, phi=22.0,
                   coesao=7.0, perfil=None)
        painel.preencher_solo(solo)

        assert painel._aviso_perfil_vazio is False
        assert painel.lbl_solo_derivado.cget("text") == ""
    finally:
        root.destroy()


# =============================================================================
#  D-02 do GATE 2, rodada 1 (a6-revisor) — cobertura de mutante: o gatilho
#  `if self._camadas: self._derivar_solo_da_camada()` dentro de
#  `_remover_camada` (REQ-UI-CAMADA-01, um dos três gatilhos NOMINALMENTE
#  exigidos) não tinha nenhum teste que sobrevivesse à troca da chamada por
#  `pass`. Este teste cobre especificamente o caso em que a camada
#  removida NÃO contém h_f, mas a remoção desloca as fronteiras o
#  suficiente para que a camada EM h_f mude.
# =============================================================================
def test_remover_camada_que_nao_contem_hf_mas_muda_camada_em_hf():
    """Perfil de 3 camadas A(0-1m)/B(1-3m)/C(3-5m), h_f = 2,00 (dentro de
    B). Remover A (que NÃO contém h_f) desloca B para 0-2m e C para
    2-4m — h_f = 2,00 cai agora exatamente na nova fronteira B/C, que
    pela convenção `z0 <= z < z1` (REQ-UI-CAMADA-01) pertence à camada DE
    BAIXO: a camada em h_f muda de "B" para "C", e os três campos e o
    rótulo têm de refletir "C", não continuar mostrando "B"."""
    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        camada_a = Camada(nome="A", espessura=1.0, phi=10.0, coesao=1.0,
                          gamma_nat=15.0, gamma_sat=16.0)
        camada_b = Camada(nome="B", espessura=2.0, phi=20.0, coesao=2.0,
                          gamma_nat=17.0, gamma_sat=18.0)
        camada_c = Camada(nome="C", espessura=2.0, phi=30.0, coesao=3.0,
                          gamma_nat=19.0, gamma_sat=20.0)
        _adicionar_camada_via_ui(painel, camada_a)
        _adicionar_camada_via_ui(painel, camada_b)
        _adicionar_camada_via_ui(painel, camada_c)

        painel.v_hf.set("2.0")
        assert painel.ultima_derivacao_de_camada["nome_camada"] == "B"
        assert painel.v_phi_solo.get() == "20"

        _remover_camada_via_ui(painel, 0)   # remove "A" — não contém h_f

        assert [c.nome for c in painel._camadas] == ["B", "C"]
        assert painel.ultima_derivacao_de_camada is not None
        assert painel.ultima_derivacao_de_camada["nome_camada"] == "C"
        assert painel.v_phi_solo.get() == "30"
        assert painel.v_coesao.get() == "3"
        texto = painel.lbl_solo_derivado.cget("text")
        assert "C" in texto
    finally:
        root.destroy()


# =============================================================================
#  REQ-UI-CAMADA-06 — importação de perfil por Excel não é carregamento de
#  arquivo (`ui/completo/app.py::_importar_excel`)
# =============================================================================
@pytest.fixture
def app_completo():
    tk = pytest.importorskip("tkinter")
    from ui.completo.app import AppSapataCompleto
    try:
        app = AppSapataCompleto()
    except tk.TclError:
        pytest.skip("sem display Tk disponível neste ambiente (Xvfb)")
    app.withdraw()
    yield app
    app.destroy()


def _planilha_pilar_e_perfil(caminho, camada_kwargs: dict) -> None:
    """Monta um .xlsx com as duas abas (Pilar+cargas e Perfil geotécnico)
    que `_importar_excel` lê juntas — uma camada só, cujos phi/coesao/gamma
    (e, desde o GATE 2 rodada 3, espessura/nível d'água) são
    parametrizáveis pelo teste via `camada_kwargs` (defaults idênticos aos
    já usados pelas rodadas 1/2 — nenhum teste existente muda de
    comportamento)."""
    openpyxl = pytest.importorskip("openpyxl")
    from ui.completo import excel_import

    livro = openpyxl.Workbook()
    ws_pilar = livro.active
    ws_pilar.title = excel_import.ABA_PILAR
    ws_pilar.append(excel_import.CABECALHO_PILAR)
    ws_pilar.append([0.30, 0.30, "G", 600.0, 15.0, 8.0])

    ws_perfil = livro.create_sheet(excel_import.ABA_PERFIL)
    ws_perfil.append(excel_import.CABECALHO_PERFIL)
    ws_perfil.append([
        camada_kwargs.get("nome", "Camada importada"), "granular",
        camada_kwargs.get("espessura", 3.0),
        camada_kwargs.get("gamma_nat", 19.0),
        camada_kwargs.get("gamma_sat", 19.0),
        camada_kwargs.get("phi", 38.0), camada_kwargs.get("coesao", 0.0),
        None, None, None, None, None,
        camada_kwargs.get("nivel_agua", None)])
    livro.save(str(caminho))


def test_importar_excel_ramo_a_deriva_do_perfil_novo(app_completo, tmp_path):
    """Critério 1 (Ramo A): com proveniência válida, importar planilha
    com aba de perfil cuja camada em h_f tem phi=38 deixa v_phi_solo ==
    "38" e a proveniência VÁLIDA de novo, apontando para a camada do
    perfil novo."""
    from unittest import mock as _mock

    app = app_completo
    formulario = app.formulario
    _adicionar_camada_via_ui(formulario, _camada_areia())   # perfil ANTIGO
    formulario.v_hf.set("1.5")
    assert formulario.ultima_derivacao_de_camada is not None
    assert formulario.v_phi_solo.get() == "34"

    caminho = tmp_path / "perfil_novo.xlsx"
    _planilha_pilar_e_perfil(caminho, {"nome": "Camada nova", "phi": 38.0,
                                       "coesao": 0.0})

    with _mock.patch("ui.completo.app.filedialog.askopenfilename",
                     return_value=str(caminho)), \
         _mock.patch("ui.completo.app.messagebox.showinfo"), \
         _mock.patch("ui.completo.app.messagebox.showerror"):
        app._importar_excel()

    assert formulario.v_phi_solo.get() == "38"
    assert formulario.ultima_derivacao_de_camada is not None
    assert formulario.ultima_derivacao_de_camada["nome_camada"] == \
        "Camada nova"


def test_importar_excel_ramo_b_com_divergencia_nao_sobrescreve_e_avisa(
        app_completo, tmp_path):
    """Critério 2 (Ramo B): com os três digitados à mão (proveniência
    inválida), a importação NÃO altera nenhum dos três, e a mensagem
    final contém uma linha citando o valor da tela e o da camada nova
    para cada um dos três que divergir."""
    from unittest import mock as _mock

    app = app_completo
    formulario = app.formulario
    formulario.v_hf.set("1.5")
    formulario.v_gamma_solo.set("16")
    formulario.v_phi_solo.set("25")
    formulario.v_coesao.set("3")
    assert formulario.ultima_derivacao_de_camada is None   # digitado à mão

    caminho = tmp_path / "perfil_divergente.xlsx"
    _planilha_pilar_e_perfil(caminho, {"nome": "Camada nova", "phi": 38.0,
                                       "coesao": 0.0, "gamma_nat": 19.0})

    with _mock.patch("ui.completo.app.filedialog.askopenfilename",
                     return_value=str(caminho)), \
         _mock.patch("ui.completo.app.messagebox.showinfo") as info, \
         _mock.patch("ui.completo.app.messagebox.showerror"):
        app._importar_excel()

    # nenhum dos três foi sobrescrito
    assert formulario.v_gamma_solo.get() == "16"
    assert formulario.v_phi_solo.get() == "25"
    assert formulario.v_coesao.get() == "3"
    assert formulario.ultima_derivacao_de_camada is None

    mensagem = info.call_args[0][1]
    assert "16" in mensagem and "19" in mensagem   # gamma: tela x camada
    assert "25" in mensagem and "38" in mensagem   # phi: tela x camada
    assert "3" in mensagem                          # coesao: tela x camada
    assert "Camada nova" in mensagem


def test_importar_excel_ramo_b_sem_divergencia_nao_acrescenta_linha(
        app_completo, tmp_path):
    """Critério 3: Ramo B sem divergência (os três já iguais à camada em
    h_f): nenhuma linha de divergência é acrescentada."""
    from unittest import mock as _mock

    app = app_completo
    formulario = app.formulario
    formulario.v_hf.set("1.5")
    formulario.v_gamma_solo.set("19")
    formulario.v_phi_solo.set("38")
    formulario.v_coesao.set("0")
    assert formulario.ultima_derivacao_de_camada is None

    caminho = tmp_path / "perfil_identico.xlsx"
    _planilha_pilar_e_perfil(caminho, {"nome": "Camada nova", "phi": 38.0,
                                       "coesao": 0.0, "gamma_nat": 19.0})

    with _mock.patch("ui.completo.app.filedialog.askopenfilename",
                     return_value=str(caminho)), \
         _mock.patch("ui.completo.app.messagebox.showinfo") as info, \
         _mock.patch("ui.completo.app.messagebox.showerror"):
        app._importar_excel()

    mensagem = info.call_args[0][1]
    assert "ATENÇÃO — divergência" not in mensagem


# -----------------------------------------------------------------------
# DEF-01/DEF-02 do GATE 2, rodada 3 (backlog #12): a rodada 2 corrigiu D-04
# capturando o texto de `v_hf` ANTES de `preencher_solo` reescrevê-lo — mas
# isso é o próprio bug (regressão): com o campo em branco antes de
# importar, o texto pré-importação é "" e `_hf_valido("")` devolve `None`,
# silenciando a linha de divergência mesmo que a tela acabe mostrando
# "1,5" (default de `ler_solo`) e a camada nova divirja fortemente dela —
# silêncio do lado INSEGURO. Os quatro testes abaixo travam a correção
# (ler `v_hf` DEPOIS de `preencher_solo`) e os quatro mutantes que o a6
# plantou/confirmou na rodada 2.
# -----------------------------------------------------------------------
def test_importar_excel_ramo_b_hf_em_branco_compara_com_valor_pos_preenchimento(
        app_completo, tmp_path):
    """DEF-01: `v_hf` em BRANCO antes de importar (proveniência já
    inválida = Ramo B) — a comparação de divergência tem de rodar contra a
    cota que a tela efetivamente PASSA A MOSTRAR ao final da importação
    (default silencioso de `ler_solo`, "1,5"), não contra o texto vazio de
    antes. Reproduz o cenário do a6: tela γ=20/φ'=38/c'=10 (à mão) vs.
    camada nova "Argila mole" em h_f=1,5 com γ=15/φ'=18/c'=2 — a mensagem
    final TEM de conter a linha de divergência.

    Mata MC2 (captura do texto de `v_hf` no momento errado: código da
    rodada 2 lia o texto ANTES de `preencher_solo`, que aqui é ""; com o
    fix, lê DEPOIS, que aqui é "1.5")."""
    from unittest import mock as _mock

    app = app_completo
    formulario = app.formulario
    formulario.v_hf.set("")
    formulario.v_gamma_solo.set("20")
    formulario.v_phi_solo.set("38")
    formulario.v_coesao.set("10")
    assert formulario.ultima_derivacao_de_camada is None

    caminho = tmp_path / "perfil_argila_mole.xlsx"
    _planilha_pilar_e_perfil(caminho, {
        "nome": "Argila mole", "gamma_nat": 15.0, "gamma_sat": 15.0,
        "phi": 18.0, "coesao": 2.0})

    with _mock.patch("ui.completo.app.filedialog.askopenfilename",
                     return_value=str(caminho)), \
         _mock.patch("ui.completo.app.messagebox.showinfo") as info, \
         _mock.patch("ui.completo.app.messagebox.showerror"):
        app._importar_excel()

    assert formulario.v_hf.get() == "1.5"   # default silencioso, agora na tela
    # nenhum dos três campos da tela foi sobrescrito (Ramo B continua)
    assert formulario.v_gamma_solo.get() == "20"
    assert formulario.v_phi_solo.get() == "38"
    assert formulario.v_coesao.get() == "10"

    mensagem = info.call_args[0][1]
    assert "ATENÇÃO — divergência" in mensagem
    assert "Argila mole" in mensagem
    assert "h_f = 1.5" in mensagem
    assert "tela = 20" in mensagem and "= 15" in mensagem       # gamma
    assert "tela = 38" in mensagem and "= 18" in mensagem       # phi
    assert "tela = 10" in mensagem and "= 2" in mensagem        # coesao


def test_importar_excel_ramo_b_hf_invalido_antes_de_importar_nao_compara(
        app_completo, tmp_path):
    """DEF-01/MC1: `v_hf` com texto EXPLICITAMENTE inválido (h_f <= 0,
    "0") antes de importar. `ler_solo()` (chamado sobre esse texto ANTES
    da importação) devolve `Solo.hf == 0.0` sem levantar exceção —
    `_float` só aplica o default de 1,5 m para texto EM BRANCO, não para
    "0" — e `preencher_solo` reescreve `v_hf` como "0" (o mesmo texto,
    formatado). A guarda `_hf_valido` tem de continuar recusando essa
    cota (h_f <= 0) mesmo lendo `v_hf` DEPOIS de `preencher_solo`.

    Mata MC1 (mutante que troca `_hf_valido(v_hf.get())` por
    `solo_atual.hf` cru, sem a guarda): aqui o texto pré- e
    pós-importação COINCIDEM ("0" nos dois momentos), então MC2 sozinho
    não pega este mutante — só a guarda de `_hf_valido` (ausente em MC1)
    evita a comparação com h_f=0."""
    from unittest import mock as _mock

    app = app_completo
    formulario = app.formulario
    formulario.v_hf.set("0")
    formulario.v_gamma_solo.set("99")   # bem diferente de qualquer camada
    formulario.v_phi_solo.set("99")
    formulario.v_coesao.set("99")
    assert formulario.ultima_derivacao_de_camada is None

    caminho = tmp_path / "perfil_qualquer.xlsx"
    _planilha_pilar_e_perfil(caminho, {"nome": "Camada nova", "gamma_nat": 15.0,
                                       "phi": 18.0, "coesao": 2.0})

    with _mock.patch("ui.completo.app.filedialog.askopenfilename",
                     return_value=str(caminho)), \
         _mock.patch("ui.completo.app.messagebox.showinfo") as info, \
         _mock.patch("ui.completo.app.messagebox.showerror"):
        app._importar_excel()

    assert formulario.v_hf.get() == "0"
    mensagem = info.call_args[0][1]
    assert "ATENÇÃO — divergência" not in mensagem


def test_importar_excel_ramo_b_perfil_sem_camadas_nao_compara_nem_quebra(
        app_completo, tmp_path):
    """DEF-01/MC3: `PerfilGeotecnico` com `camadas == []`. A própria
    `excel_import.importar_perfil_geotecnico` recusa uma aba sem NENHUMA
    linha de dado (levanta `ValueError: nenhuma camada encontrada` —
    `ui/completo/excel_import.py:482-483`), então esse caso concreto nunca
    chega ao Ramo B por um arquivo .xlsx real; `importar_perfil_geotecnico`
    é mockado para devolver o `PerfilGeotecnico` vazio diretamente,
    isolando a guarda do app (defesa em profundidade: qualquer chamador
    futuro de `_importar_excel` que devolva um perfil vazio não pode
    quebrar `_importar_excel`, que tentaria `perfil.camada_em(hf)` — isso
    levantaria `ValueError` num perfil sem camadas).

    Mata MC3 (mutante que remove a guarda `and perfil.camadas` de `if
    hf_ramo_b is not None and perfil.camadas:`)."""
    from unittest import mock as _mock

    app = app_completo
    formulario = app.formulario
    formulario.v_hf.set("1.5")
    formulario.v_gamma_solo.set("20")
    formulario.v_phi_solo.set("38")
    formulario.v_coesao.set("10")
    assert formulario.ultima_derivacao_de_camada is None

    caminho = tmp_path / "perfil_vazio.xlsx"
    _planilha_pilar_e_perfil(caminho, {})   # aba de pilar válida; a de
                                             # perfil é ignorada (mockada)

    from ui.completo import excel_import as excel_import_real
    perfil_vazio = PerfilGeotecnico(camadas=[])

    with _mock.patch("ui.completo.app.filedialog.askopenfilename",
                     return_value=str(caminho)), \
         _mock.patch("ui.completo.app.messagebox.showinfo") as info, \
         _mock.patch("ui.completo.app.messagebox.showerror"), \
         _mock.patch.object(excel_import_real, "importar_perfil_geotecnico",
                            return_value=perfil_vazio):
        app._importar_excel()   # não pode levantar exceção

    assert formulario.v_gamma_solo.get() == "20"
    assert formulario.v_phi_solo.get() == "38"
    assert formulario.v_coesao.get() == "10"

    mensagem = info.call_args[0][1]
    assert "0 camada(s) importada(s)" in mensagem
    assert "ATENÇÃO — divergência" not in mensagem


def test_importar_excel_ramo_b_na_igual_hf_usa_gamma_nat_desempate_estrito(
        app_completo, tmp_path):
    """DEF-01/MC4: N.A. exatamente igual ao h_f final (pós-
    `preencher_solo`) — pelo desempate normativo ÚNICO de
    `_camada_e_abaixo_na` (mesmo usado por `_derivar_solo_da_camada`:
    comparação ESTRITA `hf > nivel_agua`), h_f == N.A. conta como ACIMA do
    N.A., logo a camada usa `gamma_nat` (17), não `gamma_sat` (23).

    Mata MC4 (cópia inline do desempate com `>=` no lugar de `>`, que
    deslocaria hf==N.A. para 'abaixo' e citaria `gamma_sat` na linha de
    divergência em vez de `gamma_nat`)."""
    from unittest import mock as _mock

    app = app_completo
    formulario = app.formulario
    formulario.v_hf.set("1.5")
    formulario.v_gamma_solo.set("50")   # diverge tanto de 17 quanto de 23
    formulario.v_phi_solo.set("38")     # igual à camada — sem divergência
    formulario.v_coesao.set("0")        # igual à camada — sem divergência
    assert formulario.ultima_derivacao_de_camada is None

    caminho = tmp_path / "perfil_na_no_hf.xlsx"
    _planilha_pilar_e_perfil(caminho, {
        "nome": "Camada com NA", "gamma_nat": 17.0, "gamma_sat": 23.0,
        "phi": 38.0, "coesao": 0.0, "nivel_agua": 1.5})

    with _mock.patch("ui.completo.app.filedialog.askopenfilename",
                     return_value=str(caminho)), \
         _mock.patch("ui.completo.app.messagebox.showinfo") as info, \
         _mock.patch("ui.completo.app.messagebox.showerror"):
        app._importar_excel()

    mensagem = info.call_args[0][1]
    assert "ATENÇÃO — divergência" in mensagem
    assert "γ_solo: tela = 50" in mensagem
    assert "= 17" in mensagem     # gamma_nat, desempate correto (hf == NA -> ACIMA)
    assert "= 23" not in mensagem   # gamma_sat NUNCA deveria aparecer aqui


def test_importar_excel_aba_ausente_ou_erro_nao_deriva_nem_toca_campos(
        app_completo, tmp_path):
    """Critério 4: ramos AbaAusente e ValueError (app.py:489-511) não
    derivam nada e não tocam nos três campos — o perfil antigo foi
    mantido, os valores também."""
    from unittest import mock as _mock

    openpyxl = pytest.importorskip("openpyxl")
    from ui.completo import excel_import

    app = app_completo
    formulario = app.formulario
    _adicionar_camada_via_ui(formulario, _camada_areia())
    formulario.v_hf.set("1.5")
    assert formulario.ultima_derivacao_de_camada is not None
    estado_antes = (formulario.v_gamma_solo.get(), formulario.v_phi_solo.get(),
                    formulario.v_coesao.get())
    provenencia_antes = formulario.ultima_derivacao_de_camada

    # planilha só com a aba de pilar — perfil geotécnico ausente
    caminho = tmp_path / "sem_perfil.xlsx"
    livro = openpyxl.Workbook()
    ws = livro.active
    ws.title = excel_import.ABA_PILAR
    ws.append(excel_import.CABECALHO_PILAR)
    ws.append([0.30, 0.30, "G", 600.0, 15.0, 8.0])
    livro.save(str(caminho))

    with _mock.patch("ui.completo.app.filedialog.askopenfilename",
                     return_value=str(caminho)), \
         _mock.patch("ui.completo.app.messagebox.showinfo"), \
         _mock.patch("ui.completo.app.messagebox.showerror"):
        app._importar_excel()

    assert (formulario.v_gamma_solo.get(), formulario.v_phi_solo.get(),
            formulario.v_coesao.get()) == estado_antes
    assert formulario.ultima_derivacao_de_camada == provenencia_antes


# =============================================================================
#  REQ-UI-CAMADA-07 — fronteira com o núcleo e com o memorial
# =============================================================================
def test_ler_solo_corpo_identico_ao_da_v9():
    """Critério 1: o diff da rodada não toca calc_core/; o corpo de
    ler_solo sai idêntico ao da v9 (comparação textual)."""
    from ui.completo.formulario import PainelEntrada

    esperado = '''    def ler_solo(self) -> Solo:
        return Solo(sigma_adm=_float(self.v_sigma_adm.get(), 250.0),
                    gamma_solo=_float(self.v_gamma_solo.get(), 18.0),
                    hf=_float(self.v_hf.get(), 1.5),
                    phi=_float(self.v_phi_solo.get(), 30.0),
                    coesao=_float(self.v_coesao.get(), 0.0),
                    perfil=self.ler_perfil())
'''
    origem = inspect.getsource(PainelEntrada.ler_solo)
    assert origem == esperado


def test_ler_solo_ignora_provenencia_e_valor_manual_prevalece():
    """Critério 2: com proveniência válida, ler_solo() devolve exatamente
    os números que estão nos campos; sobrescrever v_phi_solo à mão para
    "20" e chamar ler_solo() devolve phi == 20.0 (o valor da camada NÃO
    prevalece)."""
    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        _adicionar_camada_via_ui(painel, _camada_aterro())
        _adicionar_camada_via_ui(painel, _camada_areia())
        painel.v_hf.set("1.5")
        assert painel.ultima_derivacao_de_camada is not None
        assert painel.ler_solo().phi == pytest.approx(34.0)

        painel.v_phi_solo.set("20")
        assert painel.ultima_derivacao_de_camada is None
        assert painel.ler_solo().phi == pytest.approx(20.0)
    finally:
        root.destroy()


def test_ultima_derivacao_de_camada_so_aparece_em_formulario_app_e_testes():
    """Critério 3: busca textual por ultima_derivacao_de_camada não
    encontra ocorrência fora de ui/completo/formulario.py,
    ui/completo/app.py e dos testes."""
    import pathlib
    import re

    raiz = pathlib.Path(__file__).resolve().parent.parent
    permitidos = {
        raiz / "ui" / "completo" / "formulario.py",
        raiz / "ui" / "completo" / "app.py",
    }
    padrao = re.compile(r"ultima_derivacao_de_camada")
    for caminho in raiz.rglob("*.py"):
        if "tests" in caminho.parts:
            continue
        if any(parte.startswith(".") for parte in caminho.parts):
            continue
        if caminho in permitidos:
            continue
        try:
            texto = caminho.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        assert not padrao.search(texto), (
            f"'ultima_derivacao_de_camada' encontrado fora do esperado em "
            f"{caminho}")
