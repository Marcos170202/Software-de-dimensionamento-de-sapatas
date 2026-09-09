"""
Testes de `ui/completo/janela_pilarete.py` e da ligação em
`ui/completo/formulario.py::PainelEntrada._abrir_janela_pilarete` /
`ui/completo/app.py::AppSapataCompleto._abrir_janela_pilarete`.

Cobre REQ-UI-PILARETE-01 a -12 (`ruleset.yaml`, bloco `requisitos_para_a3`,
versão 14) — pelo menos um caso de cada um. Segue o padrão Tk headless já
usado em `tests/test_ui_sigma_adm.py`/`tests/test_ui_camada_derivada.py`:
`pytest.importorskip("tkinter")`, `tk.Tk()` dentro de um `try/except
TclError` (skip sem display), `root.withdraw()`.

GEOMETRIA DE REFERÊNCIA ("Geometria A"): 30×30 cm, ell = 1,00 m
(ENGASTADO_BASE_LIVRE_TOPO), C25, CA-50, phi 16 mm, 4 barras nos vértices a
d' = 58 mm, N_d = 1000 kN, M_Sd,x = M_Sd,y = 24 kN·m, H_x = 40 kN, junta
MONOLÍTICA, Modelo I, A_sw/s = 3,1416e-4 m²/m, N_(gamma_f=1,0) = 714 kN —
EXATAMENTE a fixture `dados()` de `tests/test_pilarete_elemento_memorial.py`,
para que os números desta suíte de UI sejam os mesmos já travados contra o
núcleo (nunca um número novo calculado por este arquivo de teste).

NOTA — REQ-PILARETE-20 (backlog #13, V25, commit 1861586): em paralelo a
este trabalho de UI, `calc_core/estrutural/pilarete/` ganhou um cruzamento
NOVO (bitola×área / contagem×tupla / espaçamento×posições), com uma guarda
adicional em `DadosDoPilarete`. `numero_de_barras` é sempre `len(barras)`
por construção desta janela (REQ-UI-PILARETE-06-3), então essa parte do
cruzamento nunca dispara por aqui; o de espaçamento é evitado nos testes
que não precisam dele declarando um valor conservadoramente pequeno.
"""
from __future__ import annotations

import pytest

from calc_core.estrutural.dominio import (
    DECLARADO_EM_TEXTO,
    DECLARADO_PELO_USUARIO,
    ESCOPO_DESTA_VERSAO,
    NAO_DECLARADO_NA_FONTE,
    RecusaForaDeDominio,
)

D_LINHA = 0.058
"""d' = cobrimento 45 mm (nota d da Tabela 7.2) + estribo 5 mm + phi/2."""


def _tk_root():
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("sem display Tk disponível neste ambiente (Xvfb)")
    root.withdraw()
    return root


def _textos_da_janela(widget) -> list[str]:
    """Recolhe recursivamente o `text` de todo widget com essa opção —
    usado para varrer o que a janela efetivamente RENDERIZA, sem depender
    de conhecer a árvore exata de frames."""
    from tkinter import ttk

    textos: list[str] = []
    try:
        textos.append(str(widget.cget("text")))
    except Exception:  # noqa: BLE001 - nem todo widget tem "text"
        pass
    for filho in widget.winfo_children():
        textos.extend(_textos_da_janela(filho))
    return textos


def _achar_texto(widget):
    """`tk.Text`: devolve o widget de texto (o memorial), se existir."""
    import tkinter as tk

    if isinstance(widget, tk.Text):
        return widget
    for filho in widget.winfo_children():
        encontrado = _achar_texto(filho)
        if encontrado is not None:
            return encontrado
    return None


def _preencher_geometria_A(j) -> None:
    """Geometria A completa — FAIXA A, veredito ATENDIDO."""
    j.v_h_secao.set("0.30")
    j.v_b_secao.set("0.30")
    j.v_ell.set("1.00")
    j.v_vinculacao.set("ENGASTADO_BASE_LIVRE_TOPO")
    j.v_secao_constante.set("Sim")
    j.v_armadura_constante.set("Sim")
    j.v_fck.set("25")
    j.v_gamma_c.set("1,4")
    j.v_condicoes_desfav.set("Não")
    j.v_fyk_long.set("500")
    j.v_fyk_estribo.set("500")
    j.v_gamma_s.set("1,15")
    j.v_idade_28.set("Sim")
    j.v_classe_agressividade.set("II")
    j.v_d_agregado.set("19")
    j.v_cobrimento.set("45")
    j.v_phi_long.set("16")
    j.v_espacamento_eixos.set("184")
    j.v_phi_t.set("5")
    j.v_s_estribo.set("125")
    for pos_h in (D_LINHA, 0.30 - D_LINHA):
        for pos_b in (D_LINHA, 0.30 - D_LINHA):
            j._adicionar_barra()
            linha = j._linhas_barras[-1]
            linha["pos_h"].set(str(pos_h))
            linha["pos_b"].set(str(pos_b))
    j.v_Nd.set("1000")
    j.v_MSdx.set("24")
    j.v_MSdy.set("24")
    j.v_Hx.set("40")
    j.v_Hy.set("0")
    j.v_tipo_junta.set("MONOLITICO")
    j.v_boa_aderencia.set("Sim")
    j.v_armadura_tracionada.set("Não")
    j.v_modelo_calculo.set("MODELO_I")
    j.v_alpha_estribo.set("90")
    j.v_Asw_s.set("3.1416e-4")
    j.v_N_gamma_f_1.set("714")
    j.v_normal_compressao.set(True)


# ============================================================================
# REQ-UI-PILARETE-01 — janela própria, standalone, não modal, instância única.
# ============================================================================
def test_sem_grab_set_e_nao_referencia_a_sapata():
    """Busca textual: nada de `grab_set`/`formulario`/`Sapata` no módulo."""
    import pathlib

    codigo = pathlib.Path("ui/completo/janela_pilarete.py").read_text(
        encoding="utf-8")
    assert "grab_set" not in codigo
    assert "ler_solo" not in codigo
    assert "ler_pilar" not in codigo
    assert "ler_casos" not in codigo
    assert "ResultadoSapata" not in codigo


def test_instancia_unica_reaberta_traz_a_mesma_janela_para_frente():
    from ui.completo.app import AppSapataCompleto

    tk = pytest.importorskip("tkinter")
    try:
        app = AppSapataCompleto()
    except tk.TclError:
        pytest.skip("sem display Tk disponível neste ambiente (Xvfb)")
    try:
        app.withdraw()
        assert app.janela_pilarete is None
        app._abrir_janela_pilarete()
        primeira = app.janela_pilarete
        assert primeira is not None
        app._abrir_janela_pilarete()
        assert app.janela_pilarete is primeira
    finally:
        app.destroy()


def test_botao_do_formulario_delega_para_a_janela_principal():
    from unittest import mock

    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        chamado = []
        root._abrir_janela_pilarete = lambda: chamado.append(True)
        painel._abrir_janela_pilarete()
        assert chamado == [True]
    finally:
        root.destroy()


# ============================================================================
# REQ-UI-PILARETE-02 — método de segurança e rotulagem dos esforços.
# ============================================================================
def test_aviso_de_valores_de_calculo_visivel_e_rotulos_marcados():
    from ui.completo.janela_pilarete import AVISO_METODO_DE_CALCULO, JanelaPilarete

    root = _tk_root()
    try:
        j = JanelaPilarete(root)
        textos = _textos_da_janela(j)
        assert AVISO_METODO_DE_CALCULO in textos
        for rotulo in ("N_d [kN] (de cálculo)", "M_Sd,x [kN·m] (de cálculo)",
                       "M_Sd,y [kN·m] (de cálculo)", "H_x [kN] (de cálculo)",
                       "H_y [kN] (de cálculo)"):
            assert rotulo in textos
    finally:
        root.destroy()


def test_janela_pilarete_nao_menciona_o_motor_geotecnico():
    import pathlib

    codigo = pathlib.Path("ui/completo/janela_pilarete.py").read_text(
        encoding="utf-8")
    for proibido in ("admissiv", "sigma_adm", "6.3.2", "6.3.3", "vento", "FS"):
        assert proibido not in codigo, proibido


# ============================================================================
# REQ-UI-PILARETE-03 — nenhum default silencioso e o tri-estado.
# ============================================================================
def test_campos_comecam_vazios_gamma_prefill_e_tri_estado():
    import tkinter as tk
    from tkinter import ttk

    from ui.completo.janela_pilarete import JanelaPilarete

    root = _tk_root()
    try:
        j = JanelaPilarete(root)
        for enumeracao in (j.v_vinculacao, j.v_classe_agressividade,
                           j.v_tipo_junta, j.v_modelo_calculo):
            assert enumeracao.get() == ""
        for tri in (j.v_secao_constante, j.v_armadura_constante,
                   j.v_condicoes_desfav, j.v_idade_28, j.v_boa_aderencia,
                   j.v_armadura_tracionada):
            assert tri.get() == ""
        # os dois únicos campos pré-preenchidos.
        assert j.v_gamma_c.get() == "1,4"
        assert j.v_gamma_s.get() == "1,15"

        # exatamente UM Checkbutton na janela inteira, e nasce desmarcado.
        checkbuttons = [w for w in _todos_os_widgets(j)
                        if isinstance(w, ttk.Checkbutton)]
        assert len(checkbuttons) == 1
        assert j.v_normal_compressao.get() is False
    finally:
        root.destroy()


def _todos_os_widgets(widget):
    achados = [widget]
    for filho in widget.winfo_children():
        achados.extend(_todos_os_widgets(filho))
    return achados


def test_campo_numerico_vazio_produz_mensagem_nomeando_o_campo():
    """ValueError de campo obrigatório em branco vira CARD inline em
    `frame_resultado` — nunca `messagebox.showerror` (REQ-UI-PILARETE-03/11,
    mesma doutrina de RECUSA aplicada a ENTRADA MALFORMADA/INCOMPLETA: um
    `messagebox` é modal de verdade e trava a interface)."""
    from ui.completo.janela_pilarete import JanelaPilarete

    root = _tk_root()
    try:
        j = JanelaPilarete(root)
        _preencher_geometria_A(j)
        j.v_Nd.set("")   # campo obrigatório em branco

        j._verificar()

        assert j.ultimo_resultado is None
        filhos = j.frame_resultado.winfo_children()
        assert len(filhos) == 1
        texto = " ".join(_textos_da_janela(filhos[0]))
        assert "N_d" in texto
        assert "vazio" in texto.lower()
    finally:
        root.destroy()


def test_secao_constante_vazio_recusa_do_nucleo_citando_15_8_1():
    from ui.completo.janela_pilarete import JanelaPilarete

    root = _tk_root()
    try:
        j = JanelaPilarete(root)
        _preencher_geometria_A(j)
        j.v_secao_constante.set("")   # tri-estado deixado vazio -> None

        j._verificar()   # não é ValueError da tela: é RecusaForaDeDominio

        filhos = j.frame_resultado.winfo_children()
        assert len(filhos) == 1
        texto = _textos_da_janela(filhos[0])
        conjunto = " ".join(texto)
        assert "secao_constante" in conjunto
        assert "15.8.1" in conjunto
    finally:
        root.destroy()


def test_gamma_c_apagado_recusa_como_qualquer_outro_campo():
    from ui.completo.janela_pilarete import JanelaPilarete

    root = _tk_root()
    try:
        j = JanelaPilarete(root)
        _preencher_geometria_A(j)
        j.v_gamma_c.set("")

        j._verificar()

        assert j.ultimo_resultado is None
        filhos = j.frame_resultado.winfo_children()
        assert len(filhos) == 1
        texto = " ".join(_textos_da_janela(filhos[0]))
        assert "gamma_c" in texto
    finally:
        root.destroy()


# ============================================================================
# REQ-UI-PILARETE-04 — campos condicionais por ramo.
# ============================================================================
def test_trocar_vinculacao_esvazia_ell_e_e_ell_0():
    from ui.completo.janela_pilarete import JanelaPilarete

    root = _tk_root()
    try:
        j = JanelaPilarete(root)
        j.v_vinculacao.set("VINCULADO_DOIS_EXTREMOS")
        j.v_ell_e.set("1.5")
        j.v_ell_0.set("1.0")
        j.v_vinculacao.set("ENGASTADO_BASE_LIVRE_TOPO")

        assert j.v_ell_e.get() == ""
        assert j.v_ell_0.get() == ""
        assert not j._frame_vinculado.winfo_ismapped()
    finally:
        root.destroy()


def test_grupo1_vinculado_dois_extremos_aparece_e_verifica_com_sucesso():
    """REQ-UI-PILARETE-04, GRUPO 1 — metade nunca exercitada no GATE 2,
    rodada 1: `ell_e_declarado`/`ell_0` (`janela_pilarete.py:760-762`) só
    existem sob `vinculacao=VINCULADO_DOIS_EXTREMOS`. Cobre as duas metades
    do campo condicional (o frame aparece com essa vinculação, some com
    qualquer outra — a metade "some" já era coberta por
    `test_trocar_vinculacao_esvazia_ell_e_e_ell_0`) e confirma que
    `_verificar()` roda com sucesso sob esse ramo, com os valores
    declarados chegando ao núcleo tal como digitados (não o `ell_e = 2·ell`
    do ramo em balanço)."""
    from ui.completo.janela_pilarete import JanelaPilarete

    root = _tk_root()
    try:
        j = JanelaPilarete(root)

        # Vazio -> GRUPO 1 escondido (estado inicial, REQ-UI-PILARETE-04).
        j.update_idletasks()
        assert not j._frame_vinculado.winfo_ismapped()

        _preencher_geometria_A(j)   # ainda com ENGASTADO_BASE_LIVRE_TOPO
        j.v_vinculacao.set("VINCULADO_DOIS_EXTREMOS")
        j.update_idletasks()
        # GRUPO 1 aparece com essa vinculação — metade "aparece".
        assert j._frame_vinculado.winfo_ismapped()

        # ell_e = min(ell_0 + h_secao, ell) = min(0,90 + 0,30 ; 1,00) = 1,00
        j.v_ell_0.set("0.90")
        j.v_ell_e.set("1.00")

        dados = j._construir_dados()
        assert dados.vinculacao == "VINCULADO_DOIS_EXTREMOS"
        assert dados.ell_e_declarado == 1.00
        assert dados.ell_0 == 0.90

        j._verificar()
        assert j.ultimo_resultado is not None, [
            w.cget("text") for w in _todos_os_widgets(j.frame_resultado)
            if hasattr(w, "cget") and "text" in w.keys()]
    finally:
        root.destroy()


def test_grupo1_vinculado_dois_extremos_divergencia_recusa_com_numeros():
    """`ell_e_declarado` que não bate com `min(ell_0 + h, ell)` é RECUSA do
    núcleo (15.6), não uma conta que a janela silenciosamente corrige —
    completa a cobertura do ramo com um caso de recusa, não só de sucesso."""
    from ui.completo.janela_pilarete import JanelaPilarete

    root = _tk_root()
    try:
        j = JanelaPilarete(root)
        _preencher_geometria_A(j)
        j.v_vinculacao.set("VINCULADO_DOIS_EXTREMOS")
        j.v_ell_0.set("0.90")
        j.v_ell_e.set("1.50")   # esperado seria 1,00 — declaração divergente

        j._verificar()
        assert j.ultimo_resultado is None
        textos = _textos_da_janela(j.frame_resultado)
        assert any("RECUSADO" in t for t in textos)
        assert any("ell_e_declarado" in t for t in textos)
    finally:
        root.destroy()


def test_trocar_modelo_de_ii_para_i_esvazia_theta():
    from ui.completo.janela_pilarete import JanelaPilarete

    root = _tk_root()
    try:
        j = JanelaPilarete(root)
        _preencher_geometria_A(j)
        j.v_modelo_calculo.set("MODELO_II")
        j.v_theta_biela.set("40")
        j.v_modelo_calculo.set("MODELO_I")

        dados = j._construir_dados()
        assert dados.theta_biela_graus is None
        assert j.v_theta_biela.get() == ""
    finally:
        root.destroy()


def test_faixa_b_esconde_grupo4_e_campos_chegam_none_ou_false():
    from ui.completo.janela_pilarete import JanelaPilarete

    root = _tk_root()
    try:
        j = JanelaPilarete(root)
        _preencher_geometria_A(j)
        j.v_ell.set("0.80")   # 30x30, ell=0.80 -> razão 2,667 -> FAIXA B

        assert not j._frame_grupo4_cortante.winfo_ismapped()
        dados = j._construir_dados()
        assert dados.modelo_de_calculo is None
        assert dados.theta_biela_graus is None
        assert dados.alpha_estribo_graus is None
        assert dados.A_sw_por_s is None
        assert dados.N_gamma_f_1 is None
        assert dados.normal_de_compressao_em_todas_as_combinacoes is False

        j.v_ell.set("1.00")
        # `winfo_ismapped` só reflete a realidade depois de o gerenciador de
        # janelas processar o `.grid()` — sem isto a checagem compara contra
        # o estado ainda não desenhado (falso negativo do TESTE, não da
        # tela: a mesma sequência funciona sob uso interativo normal, onde
        # o laço de eventos do Tk já rodou entre um clique e o outro).
        j.update_idletasks()
        assert j._frame_grupo4_cortante.winfo_ismapped()
    finally:
        root.destroy()


def test_geometria_invalida_fecha_grupo4_sem_excecao():
    from ui.completo.janela_pilarete import JanelaPilarete

    root = _tk_root()
    try:
        j = JanelaPilarete(root)
        j.v_ell.set("")   # nunca deve levantar nada
        assert j._faixa_previa() is None
        j.update_idletasks()   # mesma ressalva de `winfo_ismapped` acima
        assert not j._frame_grupo4_cortante.winfo_ismapped()
        assert j._label_grupo4_fechado.winfo_ismapped()
        assert j._label_grupo4_fechado.cget("text") != ""
    finally:
        root.destroy()


def test_h_biaxial_chega_exato_ao_nucleo_sem_composicao():
    from ui.completo.janela_pilarete import JanelaPilarete

    root = _tk_root()
    try:
        j = JanelaPilarete(root)
        _preencher_geometria_A(j)
        j.v_Hx.set("10")
        j.v_Hy.set("0.001")
        j._verificar()

        assert j.ultimo_resultado is None
        filhos = j.frame_resultado.winfo_children()
        assert len(filhos) == 1
        texto = " ".join(_textos_da_janela(filhos[0]))
        assert "(10.0, 0.001)" in texto or "10.0" in texto and "0.001" in texto
    finally:
        root.destroy()


# ============================================================================
# REQ-UI-PILARETE-05 — cruzamento cobrimento × barras.
# ============================================================================
def test_texto_explicativo_do_cruzamento_visivel_sem_clique():
    from ui.completo.janela_pilarete import TEXTO_CRUZAMENTO_COBRIMENTO, JanelaPilarete

    root = _tk_root()
    try:
        j = JanelaPilarete(root)
        assert TEXTO_CRUZAMENTO_COBRIMENTO in _textos_da_janela(j)
    finally:
        root.destroy()


def test_barras_a_43mm_com_cobrimento_45mm_recusa_com_numeros():
    from ui.completo.janela_pilarete import JanelaPilarete

    root = _tk_root()
    try:
        j = JanelaPilarete(root)
        _preencher_geometria_A(j)
        # substitui as posições pelas do cenário exato do defeito histórico
        # (7.4.7.5): c declarado 45 mm, barras a 43 mm -> c implícito 30 mm.
        for linha in j._linhas_barras:
            atual_h = float(linha["pos_h"].get())
            novo_h = 0.043 if atual_h < 0.15 else 0.30 - 0.043
            linha["pos_h"].set(str(novo_h))
            atual_b = float(linha["pos_b"].get())
            novo_b = 0.043 if atual_b < 0.15 else 0.30 - 0.043
            linha["pos_b"].set(str(novo_b))
        j.v_espacamento_eixos.set("1")   # evita a guarda de espaçamento nova

        j._verificar()

        assert j.ultimo_resultado is None
        filhos = j.frame_resultado.winfo_children()
        assert len(filhos) == 1
        texto = " ".join(_textos_da_janela(filhos[0]))
        assert "7.4.7.5" in texto
        assert "45" in texto and "43" in texto
        # as posições digitadas continuam intactas — a tela não reposiciona.
        assert j._linhas_barras[0]["pos_h"].get() == "0.043"
    finally:
        root.destroy()


def test_verificacao_bem_sucedida_mostra_a_linha_exata_do_cruzamento():
    from ui.completo.janela_pilarete import JanelaPilarete

    root = _tk_root()
    try:
        j = JanelaPilarete(root)
        _preencher_geometria_A(j)
        j._verificar()

        assert j.ultimo_resultado is not None
        linha_esperada = (
            j.ultimo_resultado.consistencia_de_cobrimento.linha_de_memorial)
        texto = " ".join(_textos_da_janela(j.frame_resultado))
        assert linha_esperada in texto
    finally:
        root.destroy()


# ============================================================================
# REQ-UI-PILARETE-06 — bitola única, área do núcleo, contagem por len(barras).
# ============================================================================
def test_bitola_unica_area_de_todas_as_barras_vem_do_nucleo():
    from calc_core.sapata_isolada.materiais import area_barra

    from ui.completo.janela_pilarete import JanelaPilarete

    root = _tk_root()
    try:
        j = JanelaPilarete(root)
        _preencher_geometria_A(j)

        dados16 = j._construir_dados()
        assert all(b.area == pytest.approx(area_barra(16.0))
                   for b in dados16.barras)

        j.v_phi_long.set("20")
        dados20 = j._construir_dados()
        assert all(b.area == pytest.approx(area_barra(20.0))
                   for b in dados20.barras)
        assert dados20.barras[0].area != dados16.barras[0].area
    finally:
        root.destroy()


def test_numero_de_barras_e_len_barras_reprova_sem_recusa_da_tela():
    from ui.completo.janela_pilarete import JanelaPilarete

    root = _tk_root()
    try:
        j = JanelaPilarete(root)
        _preencher_geometria_A(j)
        # remove uma barra -> 3 barras, arranjo ainda simétrico (par
        # espelhado em h + uma barra exatamente no centroide).
        for linha in list(j._linhas_barras):
            j._remover_barra(linha)
        for pos_h, pos_b in ((0.058, 0.15), (0.242, 0.15), (0.15, 0.15)):
            j._adicionar_barra()
            nova = j._linhas_barras[-1]
            nova["pos_h"].set(str(pos_h))
            nova["pos_b"].set(str(pos_b))
        j.v_espacamento_eixos.set("1")   # dodge da guarda nova de espaçamento

        dados = j._construir_dados()
        assert dados.numero_de_barras == 3
        assert len(dados.barras) == 3

        j._verificar()
        assert j.ultimo_resultado is not None   # não recusou
        assert j.ultimo_resultado.armadura_longitudinal.atende_numero_de_barras is False
    finally:
        root.destroy()


def test_aviso_de_espacamento_nao_conferido_visivel():
    from ui.completo.janela_pilarete import (
        TEXTO_ESPACAMENTO_NAO_CONFERIDO,
        JanelaPilarete,
    )

    root = _tk_root()
    try:
        j = JanelaPilarete(root)
        assert TEXTO_ESPACAMENTO_NAO_CONFERIDO in _textos_da_janela(j)
    finally:
        root.destroy()


def test_janela_pilarete_nao_calcula_area_de_barra():
    import pathlib

    codigo = pathlib.Path("ui/completo/janela_pilarete.py").read_text(
        encoding="utf-8")
    assert "math.pi" not in codigo
    assert "3.1416" not in codigo
    assert "** 2" not in codigo


# ============================================================================
# REQ-UI-PILARETE-07 — faixa A/B na tela e a proibição do visto verde.
# ============================================================================
def test_faixa_b_mostra_as_duas_frases_obrigatorias_sem_visto_verde():
    from calc_core.estrutural.pilarete.classificacao import (
        classificar_faixa,
        frases_obrigatorias_da_faixa_B,
    )
    from ui.completo.janela_pilarete import JanelaPilarete

    root = _tk_root()
    try:
        j = JanelaPilarete(root)
        _preencher_geometria_A(j)
        j.v_ell.set("0.80")
        j._verificar()

        assert j.ultimo_resultado is not None
        assert j.ultimo_resultado.elu_cortante is None
        classificacao = classificar_faixa(ell=0.80, h_secao=0.30, b_secao=0.30)
        primeira, segunda = frases_obrigatorias_da_faixa_B(classificacao)
        texto = " ".join(_textos_da_janela(j.frame_resultado))
        assert primeira in texto
        assert segunda in texto
        assert "FORÇA CORTANTE: ATENDIDO" not in texto
        assert j.ultimo_resultado.nome_do_veredito in texto
    finally:
        root.destroy()


def test_titulo_e_o_nome_do_veredito_e_sem_palavras_proibidas():
    from ui.completo.janela_pilarete import JanelaPilarete

    root = _tk_root()
    try:
        j = JanelaPilarete(root)
        _preencher_geometria_A(j)
        j._verificar()

        assert j.ultimo_resultado is not None
        texto = " ".join(_textos_da_janela(j.frame_resultado))
        assert j.ultimo_resultado.nome_do_veredito in texto

        # A ÚNICA ocorrência autorizada de "APROVADO" é a frase do núcleo
        # que a NEGA com todas as letras (mesma doutrina de
        # `test_veredito_nunca_diz_aprovado_nem_ok`,
        # `tests/test_pilarete_elemento_memorial.py`) — removida antes de
        # varrer o texto renderizado por qualquer ocorrência afirmativa.
        negacao = 'NÃO emite "APROVADO" nem "pilarete OK"'
        assert negacao in texto
        texto_sem_negacao = texto.replace(negacao, "")
        for proibido in ("APROVADO", "pilarete verificado", "pilarete OK"):
            assert proibido not in texto_sem_negacao
        assert " OK " not in f" {texto_sem_negacao} "
    finally:
        root.destroy()


def test_razao_14_4_1_aparece_nas_duas_faixas():
    from ui.completo.janela_pilarete import JanelaPilarete

    root = _tk_root()
    try:
        for ell, razao in (("1.00", "3.3333"), ("0.80", "2.6667")):
            j = JanelaPilarete(root)
            _preencher_geometria_A(j)
            j.v_ell.set(ell)
            j._verificar()
            texto = " ".join(_textos_da_janela(j.frame_resultado))
            assert razao in texto
            assert "14.4.1" in texto
            j.destroy()
    finally:
        root.destroy()


def test_parcela_reprovada_aparece_discriminada():
    from ui.completo.janela_pilarete import JanelaPilarete

    root = _tk_root()
    try:
        j = JanelaPilarete(root)
        _preencher_geometria_A(j)
        j.v_Hx.set("400")   # reprova o cortante (mesmo caso do núcleo)
        j._verificar()

        assert j.ultimo_resultado is not None
        assert j.ultimo_resultado.elu_cortante.atendido is False
        texto = " ".join(_textos_da_janela(j.frame_resultado))
        assert "ELU de FORÇA CORTANTE (17.4.2.1): NÃO ATENDIDO" in texto
    finally:
        root.destroy()


# ============================================================================
# REQ-UI-PILARETE-08 — recusa não é reprovação.
# ============================================================================
def test_quatro_forcas_produzem_frases_distintas():
    from ui.completo.janela_pilarete import (
        _ROTULOS_DE_FORCA_ESTRUTURAL,
        _texto_recusa_estrutural,
    )

    textos = set()
    for forca in (DECLARADO_EM_TEXTO, DECLARADO_PELO_USUARIO,
                 ESCOPO_DESTA_VERSAO, NAO_DECLARADO_NA_FONTE):
        erro = RecusaForaDeDominio(
            parametro="x", valor=1, intervalo=">0", fonte="fonte-teste",
            forca=forca, apoio_no_ruleset="apoio-teste", sugestao="sugestao")
        texto = _texto_recusa_estrutural(erro)
        assert _ROTULOS_DE_FORCA_ESTRUTURAL[forca] in texto
        textos.add(_ROTULOS_DE_FORCA_ESTRUTURAL[forca])
    assert len(textos) == 4   # nenhuma força caiu no `.get(forca, forca)`


def test_recusa_mostra_todos_os_campos_da_excecao():
    from ui.completo.janela_pilarete import _texto_recusa_estrutural

    erro = RecusaForaDeDominio(
        parametro="phi_longitudinal_mm", valor=0.0, intervalo="> 0",
        fonte="ABNT NBR 6118:2023, 18.4.2.1, p. 153", forca=DECLARADO_EM_TEXTO,
        apoio_no_ruleset="NBR6118-18.4.2-armaduras-longitudinais-pilarete",
        sugestao="Declare uma bitola positiva.")
    texto = _texto_recusa_estrutural(erro)
    assert "phi_longitudinal_mm" in texto
    assert "0.0" in texto
    assert "> 0" in texto
    assert "18.4.2.1" in texto
    assert "Declare uma bitola positiva." in texto


def test_janela_nunca_oferece_prosseguir_mesmo_assim():
    import pathlib

    codigo = pathlib.Path("ui/completo/janela_pilarete.py").read_text(
        encoding="utf-8")
    for proibido in ("prosseguir", "continuar mesmo", "ignorar", "askyesno"):
        assert proibido not in codigo


def test_junta_sem_aderencia_mostra_nbr9062_ausente_e_alternativa_monolitica():
    from ui.completo.janela_pilarete import JanelaPilarete

    root = _tk_root()
    try:
        j = JanelaPilarete(root)
        _preencher_geometria_A(j)
        j.v_tipo_junta.set("JUNTA_SEM_ADERENCIA_ASSEGURADA")
        j._verificar()

        assert j.ultimo_resultado is None
        texto = " ".join(_textos_da_janela(j.frame_resultado))
        assert "NBR 9062" in texto
        assert "NÃO ESTÁ NO ACERVO" in texto
        assert "MONOLITICA" in texto
    finally:
        root.destroy()


def test_modelo_ii_com_v_sd_maior_que_v_rd2_mostra_vc1_nao_definido():
    from ui.completo.janela_pilarete import JanelaPilarete

    root = _tk_root()
    try:
        j = JanelaPilarete(root)
        _preencher_geometria_A(j)
        j.v_Hx.set("400")
        j.v_modelo_calculo.set("MODELO_II")
        j.v_theta_biela.set("45")
        j._verificar()

        assert j.ultimo_resultado is not None
        assert j.ultimo_resultado.elu_cortante.V_c1_valor is None
        assert j.ultimo_resultado.atendido is False
        memorial_texto = " ".join(m.get("1.0", "end-1c")
                                  for m in _todos_os_widgets(j.frame_resultado)
                                  if hasattr(m, "get") and
                                  m.__class__.__name__ == "Text")
        assert "V_c1 NÃO DEFINIDO" in memorial_texto
        assert j.ultimo_resultado.nome_do_veredito.endswith("NÃO ATENDIDO")
    finally:
        root.destroy()


# ============================================================================
# REQ-UI-PILARETE-09 — memorial literal e integral.
# ============================================================================
def test_memorial_widget_e_exatamente_a_sequencia_do_nucleo():
    from ui.completo.janela_pilarete import JanelaPilarete

    root = _tk_root()
    try:
        j = JanelaPilarete(root)
        _preencher_geometria_A(j)
        j._verificar()

        assert j.ultimo_resultado is not None
        caixa = _achar_texto(j.frame_resultado)
        assert caixa is not None
        linhas_tela = caixa.get("1.0", "end-1c").split("\n")
        assert linhas_tela == list(j.ultimo_resultado.memorial())
    finally:
        root.destroy()


def test_hipoteses_e_exigencias_presentes_sem_alteracao():
    from ui.completo.janela_pilarete import JanelaPilarete

    root = _tk_root()
    try:
        j = JanelaPilarete(root)
        _preencher_geometria_A(j)
        j._verificar()

        assert j.ultimo_resultado is not None
        caixa = _achar_texto(j.frame_resultado)
        texto = caixa.get("1.0", "end-1c")
        for hipotese in j.ultimo_resultado.hipoteses_declaradas:
            assert hipotese in texto
        for exigencia in j.ultimo_resultado.exigencias_da_emenda:
            assert exigencia in texto
    finally:
        root.destroy()


def test_memorial_na_faixa_b_tem_as_frases_e_nao_tem_linhas_de_vrd2():
    from ui.completo.janela_pilarete import JanelaPilarete

    root = _tk_root()
    try:
        j = JanelaPilarete(root)
        _preencher_geometria_A(j)
        j.v_ell.set("0.80")
        j._verificar()

        assert j.ultimo_resultado is not None
        caixa = _achar_texto(j.frame_resultado)
        texto = caixa.get("1.0", "end-1c")
        assert "NÃO FOI VERIFICADO" in texto
        assert "V_Rd2" not in texto
        assert "V_sw" not in texto
    finally:
        root.destroy()


# ============================================================================
# REQ-UI-PILARETE-10 — gamma_n e N a gamma_f = 1,0.
# ============================================================================
def test_gamma_n_aplicado_mostra_digitado_e_majorado_lado_a_lado():
    from ui.completo.janela_pilarete import JanelaPilarete

    root = _tk_root()
    try:
        j = JanelaPilarete(root)
        j.v_h_secao.set("0.24")
        j.v_b_secao.set("0.16")
        j.v_ell.set("0.75")
        j.v_vinculacao.set("ENGASTADO_BASE_LIVRE_TOPO")
        j.v_secao_constante.set("Sim")
        j.v_armadura_constante.set("Sim")
        j.v_fck.set("25")
        j.v_gamma_c.set("1,4")
        j.v_condicoes_desfav.set("Não")
        j.v_fyk_long.set("500")
        j.v_fyk_estribo.set("500")
        j.v_gamma_s.set("1,15")
        j.v_idade_28.set("Sim")
        j.v_classe_agressividade.set("II")
        j.v_d_agregado.set("9.5")
        j.v_cobrimento.set("45")
        j.v_phi_long.set("12.5")
        j.v_espacamento_eixos.set("47.5")
        j.v_phi_t.set("5")
        j.v_s_estribo.set("125")
        d = 0.05625
        for pos_h in (d, 0.24 - d):
            for pos_b in (d, 0.16 - d):
                j._adicionar_barra()
                linha = j._linhas_barras[-1]
                linha["pos_h"].set(str(pos_h))
                linha["pos_b"].set(str(pos_b))
        j.v_Nd.set("400")
        j.v_MSdx.set("10")
        j.v_MSdy.set("5")
        j.v_Hx.set("10")
        j.v_Hy.set("0")
        j.v_tipo_junta.set("MONOLITICO")
        j.v_boa_aderencia.set("Sim")
        j.v_armadura_tracionada.set("Não")
        j.v_modelo_calculo.set("MODELO_I")
        j.v_alpha_estribo.set("90")
        j.v_Asw_s.set("2.0e-4")
        j.v_N_gamma_f_1.set("286")
        j.v_normal_compressao.set(True)

        j._verificar()
        assert j.ultimo_resultado is not None
        assert j.ultimo_resultado.gamma_n_aplicado is True
        texto = " ".join(_textos_da_janela(j.frame_resultado))
        assert "400" in texto   # N_d digitado
        assert f"{j.ultimo_resultado.N_d_majorado:.4f}" in texto
        assert f"{j.ultimo_resultado.gamma_n:.4f}" in texto
    finally:
        root.destroy()


def test_gamma_n_nao_aplicado_mostra_motivo():
    from ui.completo.janela_pilarete import JanelaPilarete

    root = _tk_root()
    try:
        j = JanelaPilarete(root)
        _preencher_geometria_A(j)
        j._verificar()

        assert j.ultimo_resultado is not None
        assert j.ultimo_resultado.gamma_n_aplicado is False
        texto = " ".join(_textos_da_janela(j.frame_resultado))
        assert "gamma_n = 1,00" in texto
        assert ">= 19 cm" in texto
    finally:
        root.destroy()


def test_n_gamma_f_1_em_branco_verifica_e_memorial_diz_nao_aplicada():
    from ui.completo.janela_pilarete import JanelaPilarete

    root = _tk_root()
    try:
        j = JanelaPilarete(root)
        _preencher_geometria_A(j)
        j.v_N_gamma_f_1.set("")
        j._verificar()

        assert j.ultimo_resultado is not None
        assert j.ultimo_resultado.elu_cortante.N_gamma_f_1 is None
        caixa = _achar_texto(j.frame_resultado)
        texto = caixa.get("1.0", "end-1c")
        assert "NÃO foi declarado" in texto
        assert "NÃO foi aplicada" in texto
    finally:
        root.destroy()


def test_janela_pilarete_nao_infere_n_gamma_f_1_de_n_d():
    import pathlib

    codigo = pathlib.Path("ui/completo/janela_pilarete.py").read_text(
        encoding="utf-8")
    assert "/ gamma_f" not in codigo
    assert "1.4" not in codigo


# ============================================================================
# REQ-UI-PILARETE-11 — o veredito morre a cada tecla.
# ============================================================================
def test_verificar_depois_alterar_qualquer_campo_zera_o_resultado():
    from ui.completo.janela_pilarete import JanelaPilarete

    root = _tk_root()
    try:
        j = JanelaPilarete(root)
        _preencher_geometria_A(j)

        variaveis = j._construir_e_capturar_variaveis(lambda: None)
        # `_construir_e_capturar_variaveis` acima não constrói nada (a
        # janela já foi montada no `__init__`); usa-se aqui só para obter,
        # por diferença de `vars(self)`, as mesmas variáveis vigiadas —
        # como nada foi criado, refaz-se a leitura direta:
        variaveis = [v for v in vars(j).values()
                    if hasattr(v, "trace_add") and hasattr(v, "get")]
        assert variaveis, "nenhuma tk.Variable encontrada em vars(j)"

        for variavel in variaveis:
            j._verificar()
            assert j.ultimo_resultado is not None, "setup falhou"
            valor_original = variavel.get()
            if isinstance(valor_original, str):
                variavel.set(valor_original + " ")
            else:
                variavel.set(not valor_original)
            assert j.ultimo_resultado is None, variavel
            assert j.frame_resultado.winfo_children() == []
            # Restaura o valor ANTES de passar para a próxima variável: sem
            # isto, a mutação de um campo (ex.: espaço acrescentado a
            # `v_vinculacao`) sobrevive às iterações seguintes e corrompe o
            # "setup" de um campo totalmente diferente — não é o defeito que
            # este teste existe para pegar (REQ-UI-PILARETE-11), é um efeito
            # colateral cumulativo do próprio laço de teste.
            variavel.set(valor_original)
    finally:
        root.destroy()


def test_adicionar_remover_editar_barra_invalida_o_resultado():
    """REQ-UI-PILARETE-11-c: os três pontos de edição da tabela de barras
    (adicionar, editar, remover) invalidam um resultado DE FATO existente.

    Cada bloco abaixo parte de `_verificar()` bem-sucedido
    (`ultimo_resultado is not None`) ANTES de editar a tabela — critério
    real de invalidação. GATE 2, rodada 1: a versão anterior deste teste
    chamava `_adicionar_barra()` (que nasce com `pos_h`/`pos_b` vazios) e
    então reverificava ANTES de testar editar/remover; essa reverificação
    já falhava sozinha em `_ler_barras` por causa da barra vazia, deixando
    `ultimo_resultado` em `None` por um motivo diferente do que o teste
    dizia cobrir — as asserções seguintes de `is None` passariam mesmo que
    a invalidação por edição/remoção não existisse. Cada bloco agora usa
    uma janela nova para não herdar esse "já None" de um bloco anterior."""
    from ui.completo.janela_pilarete import JanelaPilarete

    root = _tk_root()
    try:
        # ---- EDITAR uma barra existente invalida um resultado válido. ----
        j = JanelaPilarete(root)
        _preencher_geometria_A(j)
        j._verificar()
        assert j.ultimo_resultado is not None, "setup falhou (editar)"
        registro = j._linhas_barras[0]
        registro["pos_h"].set("0.06")
        assert j.ultimo_resultado is None
        assert j.frame_resultado.winfo_children() == []

        # ---- REMOVER uma barra existente invalida um resultado válido. ----
        j = JanelaPilarete(root)
        _preencher_geometria_A(j)
        j._verificar()
        assert j.ultimo_resultado is not None, "setup falhou (remover)"
        j._remover_barra(j._linhas_barras[-1])
        assert j.ultimo_resultado is None
        assert j.frame_resultado.winfo_children() == []

        # ---- ADICIONAR uma barra invalida um resultado válido, mesmo com
        # a barra nova ainda vazia — a invalidação é IMEDIATA, no próprio
        # clique em "+ Adicionar barra" (`_invalidar_resultado` explícito
        # em `_adicionar_barra`), sem esperar outro "Verificar".
        j = JanelaPilarete(root)
        _preencher_geometria_A(j)
        j._verificar()
        assert j.ultimo_resultado is not None, "setup falhou (adicionar)"
        j._adicionar_barra()
        assert j.ultimo_resultado is None
        assert j.frame_resultado.winfo_children() == []
    finally:
        root.destroy()


def test_nao_existe_atributo_de_instancia_guardando_o_resultado_entre_cliques():
    """Os botões de copiar/salvar memorial fecham sobre o TEXTO já
    formatado, não sobre um atributo lido depois — verificado por busca
    textual (nenhum `self._ultimo_texto_memorial` ou equivalente)."""
    import pathlib

    codigo = pathlib.Path("ui/completo/janela_pilarete.py").read_text(
        encoding="utf-8")
    assert "self._texto_memorial" not in codigo
    assert "self.texto_memorial" not in codigo


# ============================================================================
# REQ-UI-PILARETE-12 — fronteira com o núcleo, persistência e exportação.
# ============================================================================
def test_aviso_de_persistencia_visivel_no_widget_sem_depender_de_resultado():
    """GATE 2, rodada 1 — motivo do ALTA: o aviso de que as entradas do
    pilarete não são salvas no `.s7proj` existia só no docstring do módulo
    (linhas 31-35), não em nenhum widget. Varredura recursiva de `text`
    (mesma técnica do a6) confirmando que a string está presente E visível
    (`winfo_ismapped`) na janela RECÉM-ABERTA, sem depender de nenhuma
    `_verificar()` ter rodado — o aviso não é `frame_resultado`."""
    from ui.completo.janela_pilarete import AVISO_PERSISTENCIA, JanelaPilarete

    root = _tk_root()
    try:
        j = JanelaPilarete(root)
        j.update_idletasks()   # mapeamento só reflete a realidade depois

        textos = _textos_da_janela(j)
        candidatos = [t for t in textos
                      if "não são salvas" in t or "s7proj" in t.lower()]
        assert candidatos, "nenhum widget da janela menciona a não-persistência"
        assert AVISO_PERSISTENCIA in textos

        widgets_com_o_aviso = [
            w for w in _todos_os_widgets(j)
            if hasattr(w, "cget") and "text" in w.keys()
            and w.cget("text") == AVISO_PERSISTENCIA]
        assert widgets_com_o_aviso, "aviso não está em nenhum widget da janela"
        assert all(w.winfo_ismapped() for w in widgets_com_o_aviso), (
            "aviso presente no texto, mas escondido (não mapeado)")
    finally:
        root.destroy()


def test_s7proj_identico_antes_e_depois_de_usar_a_janela_do_pilarete(tmp_path):
    from calc_core.sapata_isolada.acoes import CasoCarga
    from ui.completo import projeto

    tk = pytest.importorskip("tkinter")
    from ui.completo.app import AppSapataCompleto

    try:
        app = AppSapataCompleto()
    except tk.TclError:
        pytest.skip("sem display Tk disponível neste ambiente (Xvfb)")
    try:
        app.withdraw()
        caminho = tmp_path / "antes.s7proj"
        pilar = app.formulario.ler_pilar()
        solo = app.formulario.ler_solo()
        concreto, aco, cobrimento = app.formulario.ler_materiais()
        casos = app.formulario.ler_casos()
        opcoes = app.formulario.ler_opcoes()
        projeto.salvar_projeto(str(caminho), pilar, solo, concreto, aco,
                               cobrimento, casos, opcoes)
        conteudo_antes = caminho.read_text(encoding="utf-8")

        app._abrir_janela_pilarete()
        _preencher_geometria_A(app.janela_pilarete)
        app.janela_pilarete._verificar()
        assert app.janela_pilarete.ultimo_resultado is not None
        app.janela_pilarete.destroy()

        caminho2 = tmp_path / "depois.s7proj"
        projeto.salvar_projeto(str(caminho2), pilar, solo, concreto, aco,
                               cobrimento, casos, opcoes)
        conteudo_depois = caminho2.read_text(encoding="utf-8")
        assert conteudo_antes == conteudo_depois
    finally:
        app.destroy()


def test_lista_de_chamadas_ao_nucleo_e_fechada():
    import pathlib

    codigo = pathlib.Path("ui/completo/janela_pilarete.py").read_text(
        encoding="utf-8")
    # nenhuma referência a `Sapata`/exportadores da fundação.
    for proibido in ("relatorio.py", "pranchas", "excel_export",
                     "construir_modelo_visual"):
        assert proibido not in codigo
