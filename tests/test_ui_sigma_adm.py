"""
Testes de `ui/completo/dialogo_sigma_adm.py` e da chamada em
`ui/completo/formulario.py::PainelEntrada._abrir_calculadora_sigma_adm`.

Cobre a ligação dos REQ-UI-SIGMA-01 a 06 (`ruleset.yaml`, bloco
`requisitos_para_a3`) entre a tela e `calc_core.geotecnico.{sigma_adm,
vento}`, que já passaram por GATE 2/GATE 3 sobre a v9. Esta suíte NÃO
recalcula os valores de referência: reusa os mesmos números "conhecidos"
que `test_sigma_adm_semiempirico.py`/`test_capacidade_carga_vesic.py`/
`test_vento_majoracao.py` já travam contra a fonte, e confirma que a tela
devolve o MESMO número que o núcleo — nunca um número novo calculado na
UI (CLAUDE.md, regra 4).

Segue o padrão Tk headless já usado em `test_projeto_e_excel.py` (seção
"Edição de camada"): `pytest.importorskip("tkinter")`, `tk.Tk()` dentro de
um `try/except TclError` (skip sem display), `root.withdraw()`, e
`mock.patch("ui.completo.formulario.DialogoSigmaAdm", ...)` +
`painel.wait_window = lambda w: None` para testar o formulário sem um
loop de janela modal real.

REDESENHO (rodada 4 do GATE 2 — ver a docstring de
`ui/completo/dialogo_sigma_adm.py`). O diálogo não guarda mais um
"resultado ativo"/"valor final selecionado" em atributos de instância:
cada card tem seu próprio botão "Usar este valor →" (`_usar_base`), e a
majoração por vento é calculada e usada dentro do mesmo card
(`_calcular_vento_no_card` + `_usar_majorado`). Os testes que antes
chamavam `_selecionar`/`_selecionar_majorado`/`_usar` agora chamam
`_usar_base`/`_usar_majorado` diretamente (equivalente a clicar no botão
do card — o comando do botão É essa chamada, por `lambda r=resultado:
self._usar_base(r)`), e os testes de invalidação de cache (D-01, MÉDIA
#1/#2) foram reescritos para provar a propriedade estrutural nova: um
card (e o botão que ele carrega) só existe na tela enquanto representar
fielmente o último cálculo — recalcular DESTRÓI o card antigo
(`winfo_exists()` vira falso), então não há como o botão de um resultado
obsoleto ser clicado.
"""
from __future__ import annotations

import pytest

from calc_core.geotecnico.dominio import (
    ADOTADO_DA_EXTENSAO_DE_FIGURA,
    DECLARADO_EM_TEXTO,
    ForaDoDominioError,
)
from calc_core.geotecnico.semiempirico import (
    NOME_TEIXEIRA,
    regra_brasileira_nspt_50_argila,
    teixeira_1996_areia,
)
from calc_core.geotecnico.sigma_adm import semiempirico_spt, teorico_terzaghi_vesic
from calc_core.geotecnico.vento import TIPOS_DE_OBRA_DOS_30_POR_CENTO
from calc_core.modelos import (
    ROTULO_ELU,
    EntradaCapacidadeCarga,
    EntradaSemiempiricaSPT,
    RecusaDeMetodo,
)

# `ui.completo.dialogo_sigma_adm` importa `tkinter` no topo do módulo — os
# imports de tudo que vem de `ui.completo` ficam DENTRO de cada função de
# teste (nunca no topo do arquivo), mesmo padrão já documentado em
# `test_projeto_e_excel.py` (seção "PainelEntrada é ttk.Frame..."): um
# ambiente Python sem `tkinter` instalado não pode ter a coleta da suíte
# INTEIRA abortada só porque este arquivo, em particular, testa telas.


def _botao(pai, texto: str):
    """Acha, entre os filhos DIRETOS de `pai`, o `ttk.Button` cujo texto é
    EXATAMENTE `texto` — usado para localizar "Usar este valor →"/"Usar
    valor majorado →"/"Calcular majoração por vento..." dentro de um card,
    em vez de chamar o método que o botão dispara por baixo dos panos.
    Levanta se não achar: um card sem o botão esperado é, em si, uma
    regressão do redesenho (cada card É dono do seu botão).

    Import de `tkinter` LOCAL (não no topo do arquivo): mesmo motivo já
    documentado para os imports de `ui.completo` — um ambiente sem
    `tkinter` instalado não pode ter a coleta da suíte inteira abortada só
    por causa deste arquivo de testes de tela."""
    from tkinter import ttk
    for filho in pai.winfo_children():
        if isinstance(filho, ttk.Button) and filho.cget("text") == texto:
            return filho
    raise AssertionError(f"botão {texto!r} não encontrado em {pai!r}")


# --------------------------------------------------------------------------- #
#  Testes puros — formatação de recusa (REQ-UI-SIGMA-03), sem Tk nenhum.
# --------------------------------------------------------------------------- #
def test_texto_recusa_distingue_declarado_em_texto_de_extensao_de_figura():
    """As duas guardas RECUSAM igual, mas a força é textualmente diferente
    — REQ-UI-SIGMA-03 exige que a tela diga qual é qual. Chama as funções
    FOLHA do núcleo diretamente (nunca `semiempirico_spt`, que RE-LEVANTA
    a última recusa como o mesmo objeto de exceção já capturado uma vez —
    inofensivo em produção, mas incompatível com `pytest.raises` sobre uma
    exceção `frozen=True`, que não aceita um segundo `__traceback__`; não é
    algo que esta suíte de UI deva contornar dentro de `calc_core`)."""
    tk = pytest.importorskip("tkinter")   # dialogo_sigma_adm importa tkinter
    del tk
    from ui.completo.dialogo_sigma_adm import _texto_recusa, _texto_recusa_metodo

    with pytest.raises(ForaDoDominioError) as excinfo_texto:
        teorico_terzaghi_vesic(EntradaCapacidadeCarga(
            c_kPa=0.0, phi_graus=60.0, B_m=2.0, L_m=2.0, h_m=1.0,
            gamma_acima_da_base_kN_m3=18.0, gamma_abaixo_da_base_kN_m3=18.0,
            forma="quadrada", modo_de_ruptura="geral",
            natureza_do_carregamento="drenado",
            solo_homogeneo_no_bulbo_declarado=True))
    texto_declarado = _texto_recusa(excinfo_texto.value)
    assert excinfo_texto.value.forca == DECLARADO_EM_TEXTO
    assert "DECLARADO EM TEXTO" in texto_declarado
    assert "phi_graus" in texto_declarado
    assert "60.0" in texto_declarado

    # A guarda "ADOTADO_DA_EXTENSAO_DE_FIGURA" vive no caminho semiempírico
    # (Teixeira, B fora da extensão das curvas B=1/2/3 m da Fig. 4.1).
    with pytest.raises(ForaDoDominioError) as excinfo_figura:
        teixeira_1996_areia(
            N_spt=15.0, B_m=5.0, forma="quadrada", solo_declarado="areia",
            h_m=1.5, gamma_kN_m3=18.0, aplicabilidade_regional_declarada=True)
    erro_figura = excinfo_figura.value
    assert erro_figura.forca == ADOTADO_DA_EXTENSAO_DE_FIGURA
    assert erro_figura.parametro == "B_m"

    # `_texto_recusa_metodo` é quem a tela usa para os itens de
    # `ResultadoDispersaoSemiempirica.recusas` — mesmos campos de
    # proveniência, empacotados como o núcleo já empacota (ver
    # `sigma_adm.semiempirico_spt`).
    recusa_teixeira = RecusaDeMetodo(
        nome_do_metodo=NOME_TEIXEIRA, pratica="FB-TEIXEIRA-1996-areia",
        parametro=erro_figura.parametro, valor=erro_figura.valor,
        intervalo=erro_figura.intervalo, fonte=erro_figura.fonte,
        forca=erro_figura.forca, motivo=erro_figura.mensagem)
    texto_figura = _texto_recusa_metodo(recusa_teixeira)
    assert "ADOTADO" in texto_figura and "EXTENSÃO" in texto_figura
    assert "revisável por decisão humana" in texto_figura
    # os dois textos usam vocabulário DIFERENTE para a força da guarda —
    # a exigência central de REQ-UI-SIGMA-03.
    assert "DECLARADO EM TEXTO" not in texto_figura


def test_texto_recusa_nunca_diz_apenas_erro_de_calculo():
    tk = pytest.importorskip("tkinter")
    del tk
    from ui.completo.dialogo_sigma_adm import _texto_recusa

    with pytest.raises(ForaDoDominioError) as excinfo:
        regra_brasileira_nspt_50_argila(
            N_spt_medio_bulbo=2.0, forma="quadrada", solo_declarado="argila",
            aplicabilidade_regional_declarada=True)
    texto = _texto_recusa(excinfo.value)
    assert "erro de cálculo" not in texto.lower()
    assert "N_spt_medio_bulbo" in texto
    assert "2.0" in texto
    assert "Limite da FONTE, não do software" in texto


# --------------------------------------------------------------------------- #
#  Fixture de janela Tk headless (padrão de test_projeto_e_excel.py)
# --------------------------------------------------------------------------- #
def _tk_root():
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("sem display Tk disponível neste ambiente (Xvfb)")
    root.withdraw()
    return root


# --------------------------------------------------------------------------- #
#  DialogoSigmaAdm — aba teórico
# --------------------------------------------------------------------------- #
def test_dialogo_teorico_bate_com_o_nucleo_e_carrega_rotulo_ELU():
    from ui.completo.dialogo_sigma_adm import DialogoSigmaAdm

    root = _tk_root()
    try:
        dialogo = DialogoSigmaAdm(root)
        dialogo.t_c.set("0")
        dialogo.t_phi.set("30")
        dialogo.t_B.set("2.0")
        dialogo.t_L.set("2.0")
        dialogo.t_h.set("1.5")
        dialogo.t_gamma_acima.set("18")
        dialogo.t_gamma_abaixo.set("18")
        dialogo.t_forma.set("quadrada")
        dialogo.t_modo.set("geral")
        dialogo.t_natureza.set("drenado")
        dialogo.t_homogeneo.set(True)

        dialogo._calcular_teorico()

        esperado = teorico_terzaghi_vesic(EntradaCapacidadeCarga(
            c_kPa=0.0, phi_graus=30.0, B_m=2.0, L_m=2.0, h_m=1.5,
            gamma_acima_da_base_kN_m3=18.0, gamma_abaixo_da_base_kN_m3=18.0,
            forma="quadrada", modo_de_ruptura="geral",
            natureza_do_carregamento="drenado",
            solo_homogeneo_no_bulbo_declarado=True))

        # um único card de resultado foi desenhado (nenhum de recusa)
        filhos = dialogo.frame_resultado_teorico.winfo_children()
        assert len(filhos) == 1
        card = filhos[0]
        assert card.cget("text") == esperado.nome_do_metodo

        # o card É dono do botão "Usar este valor →" — nenhum estado
        # intermediário de "resultado ativo"/"selecionado" (REDESENHO).
        botao_usar = _botao(card, "Usar este valor →")
        botao_usar.invoke()

        assert dialogo.resultado_kPa == pytest.approx(esperado.sigma_adm_ELU_kPa)
        # REQ-UI-SIGMA-01: rótulo obrigatório colado ao número — nunca
        # reduzido a só "tensão admissível" (a definição 3.45 da Norma é
        # CONJUNTIVA e o §7.4/ELS não foi verificado por caminho algum
        # desta versão; o rótulo tem de dizer isso, não escondê-lo).
        assert dialogo.resultado_info["rotulo_ELU"] == ROTULO_ELU
        assert "parcela de ELU" in dialogo.resultado_info["rotulo_ELU"]
        assert "NÃO verificado" in dialogo.resultado_info["rotulo_ELU"]
        assert dialogo.resultado_info["majorado_por_vento"] is False
    finally:
        root.destroy()


def test_dialogo_teorico_sem_declaracao_de_homogeneidade_recusa_com_card():
    """`solo_homogeneo_no_bulbo_declarado` não tem default afirmativo — sem
    marcar a caixa, o núcleo recusa e a tela tem de mostrar um card de
    recusa, não travar nem devolver número algum."""
    from ui.completo.dialogo_sigma_adm import DialogoSigmaAdm

    root = _tk_root()
    try:
        dialogo = DialogoSigmaAdm(root)
        assert dialogo.t_homogeneo.get() is False   # sem default afirmativo
        dialogo._calcular_teorico()

        filhos = dialogo.frame_resultado_teorico.winfo_children()
        assert len(filhos) == 1
        assert filhos[0].cget("text") == "Recusado — fora do domínio"
        assert dialogo.resultado_kPa is None
    finally:
        root.destroy()


# --------------------------------------------------------------------------- #
#  DialogoSigmaAdm — aba semiempírico (REQ-UI-SIGMA-05: dispersão lado a
#  lado, nunca escolhida pelo software)
# --------------------------------------------------------------------------- #
def test_dialogo_semiempirico_argila_mostra_um_resultado_e_uma_recusa():
    """N_SPT=15/B=2/forma=quadrada com solo='argila': a regra N/50 se
    aplica (retangular inclui quadrada) e Teixeira recusa (é só para
    'areia') — os dois precisam aparecer na tela, o card de recusa
    incluído (REQ-UI-SIGMA-03), nunca escondido."""
    from ui.completo.dialogo_sigma_adm import DialogoSigmaAdm

    root = _tk_root()
    try:
        dialogo = DialogoSigmaAdm(root)
        dialogo.s_nspt.set("15")
        dialogo.s_B.set("2.0")
        dialogo.s_forma.set("quadrada")
        dialogo.s_solo.set("argila")
        dialogo.s_h.set("1.5")
        dialogo.s_gamma.set("18")
        dialogo.s_regional.set(True)

        dialogo._calcular_semiempirico()

        titulos = [f.cget("text")
                   for f in dialogo.frame_resultado_semi.winfo_children()]
        assert "regra brasileira sigma_a = N_SPT/50, demonstrada por " \
               "Teixeira (1996) para argila" in titulos
        assert "Recusado — fora do domínio" in titulos

        dispersao = semiempirico_spt(EntradaSemiempiricaSPT(
            N_spt=15.0, B_m=2.0, forma="quadrada", solo_declarado="argila",
            h_m=1.5, gamma_kN_m3=18.0,
            aplicabilidade_regional_declarada=True))
        assert len(dispersao.resultados) == 1
        assert dispersao.resultados[0].sigma_adm_ELU_kPa == pytest.approx(300.0)
        # dispersão só é exibida com >= 2 resultados aplicáveis — com um só
        # (domínios de solo mutuamente exclusivos), a Label de dispersão
        # não deve ter sido criada.
        assert dispersao.dispersao_relativa is None
    finally:
        root.destroy()


def test_dialogo_semiempirico_sem_declaracao_regional_recusa_cada_metodo_com_seu_card():
    """D-03 do GATE 2, rodada 3 — corrigido no núcleo desde a rodada 3
    (`NenhumMetodoAplicavelError.recusas`), mas a TELA continuava
    desenhando um card genérico com só a PRIMEIRA recusa
    (`erro.parametro`/`erro.valor`, que a própria docstring do núcleo
    avisa serem "visão degradada"). Com N_SPT=15/B=2/forma=quadrada/
    solo='argila' e regional NÃO declarada, NENHUMA correlação se aplica
    — mas por motivos DIFERENTES: a regra N/50 recusa pela falta da
    declaração regional (guarda que ela alcança, já que N_SPT/solo/forma
    passam); Teixeira recusa antes disso, no domínio de solo (exige
    'areia', e a guarda de solo é anterior à de declaração regional
    dentro do próprio método). A tela tem de desenhar um card POR
    correlação candidata, cada um com o motivo que é dele."""
    from ui.completo.dialogo_sigma_adm import DialogoSigmaAdm

    root = _tk_root()
    try:
        dialogo = DialogoSigmaAdm(root)
        dialogo.s_nspt.set("15")
        dialogo.s_B.set("2.0")
        dialogo.s_solo.set("argila")
        assert dialogo.s_regional.get() is False

        dialogo._calcular_semiempirico()

        filhos = dialogo.frame_resultado_semi.winfo_children()
        assert len(filhos) == 2   # uma correlação candidata, um card cada
        assert all(f.cget("text") == "Recusado — fora do domínio"
                   for f in filhos)

        textos = [f.winfo_children()[0].cget("text") for f in filhos]
        assert any("aplicabilidade_regional_declarada" in t for t in textos)
        assert any("solo_declarado" in t for t in textos)
        # os dois métodos aparecem nomeados, não só o parâmetro que falhou
        assert any("NÃO SE APLICA" in t for t in textos)
        assert dialogo.resultado_kPa is None
    finally:
        root.destroy()


# --------------------------------------------------------------------------- #
#  Majoração por vento (REQ-UI-SIGMA-05) — lista fechada, default que não
#  majora, FSg efetivo exibido, calculada DENTRO do card (REDESENHO).
# --------------------------------------------------------------------------- #
def test_combobox_tipo_de_obra_e_lista_fechada_e_somente_leitura():
    from ui.completo.dialogo_sigma_adm import _SEM_LISTA_FECHADA, DialogoSigmaAdm

    root = _tk_root()
    try:
        dialogo = DialogoSigmaAdm(root)
        valores = dialogo.combo_tipo_obra.cget("values")
        assert valores[0] == _SEM_LISTA_FECHADA
        assert tuple(valores[1:]) == TIPOS_DE_OBRA_DOS_30_POR_CENTO
        # nunca editável como texto livre
        assert str(dialogo.combo_tipo_obra.cget("state")) in ("disabled",
                                                               "readonly")
        dialogo.v_vento_principal.set(True)
        dialogo._alternar_vento()
        assert str(dialogo.combo_tipo_obra.cget("state")) == "readonly"
    finally:
        root.destroy()


def test_vento_default_k_v_zero_e_identidade():
    """k_v = 0 (default, NUNCA inferido) tem de devolver o MESMO valor,
    mesmo que o usuário marque vento como ação principal — a Norma dá o
    teto, não o valor (REQ-SIGMA-10 / REQ-UI-SIGMA-05)."""
    from tkinter import ttk

    from ui.completo.dialogo_sigma_adm import DialogoSigmaAdm

    root = _tk_root()
    try:
        dialogo = DialogoSigmaAdm(root)
        resultado = teorico_terzaghi_vesic(EntradaCapacidadeCarga(
            c_kPa=0.0, phi_graus=30.0, B_m=2.0, L_m=2.0, h_m=1.5,
            gamma_acima_da_base_kN_m3=18.0, gamma_abaixo_da_base_kN_m3=18.0,
            forma="quadrada", modo_de_ruptura="geral",
            natureza_do_carregamento="drenado",
            solo_homogeneo_no_bulbo_declarado=True))
        assert dialogo.v_kv.get() == "0"   # default que não majora

        saida = ttk.Frame(dialogo)
        dialogo._calcular_vento_no_card(resultado, saida)

        botao_majorado = _botao(saida, "Usar valor majorado →")
        botao_majorado.invoke()

        assert dialogo.resultado_kPa == pytest.approx(resultado.sigma_adm_ELU_kPa)
        assert dialogo.resultado_info["majorado_por_vento"] is True
    finally:
        root.destroy()


def test_vento_majoracao_bate_com_a_checagem_numerica_do_ruleset():
    """300 kPa -> 345 kPa com k_v = 0,15, caso geral (mesmo número que
    `test_vento_majoracao.py::test_checagem_numerica_do_ruleset`)."""
    from tkinter import ttk

    from ui.completo.dialogo_sigma_adm import DialogoSigmaAdm

    root = _tk_root()
    try:
        dialogo = DialogoSigmaAdm(root)
        # FSg = 3,00 (Analíticos) — monta um resultado teórico cujo
        # sigma_adm_ELU_kPa seja exatamente 300 não é trivial, então usamos
        # o resultado semiempírico já travado em 300 kPa (regra N/50,
        # N_SPT=15) para reaproveitar a checagem numérica publicada.
        dispersao = semiempirico_spt(EntradaSemiempiricaSPT(
            N_spt=15.0, B_m=2.0, forma="quadrada", solo_declarado="argila",
            h_m=1.5, gamma_kN_m3=18.0,
            aplicabilidade_regional_declarada=True))
        resultado_300 = dispersao.resultados[0]
        assert resultado_300.sigma_adm_ELU_kPa == pytest.approx(300.0)
        assert resultado_300.FSg_efetivo == pytest.approx(3.0)

        dialogo.v_vento_principal.set(True)
        dialogo._alternar_vento()
        dialogo.v_tipo_obra.set(dialogo.v_tipo_obra.get())  # "Nenhum destes"
        dialogo.v_kv.set("0.15")

        saida = ttk.Frame(dialogo)
        dialogo._calcular_vento_no_card(resultado_300, saida)

        botao_majorado = _botao(saida, "Usar valor majorado →")
        botao_majorado.invoke()

        assert dialogo.resultado_kPa == pytest.approx(345.0)
        assert dialogo.resultado_info["majorado_por_vento"] is True
    finally:
        root.destroy()


def test_calcular_vento_sem_fsg_mostra_recusa_sem_travar():
    """Um `ResultadoSigmaAdmELU` sem `FSg_aplicado` nem `FS_embutido`
    (síntese de teste — não ocorre nos dois caminhos aprovados da v9, mas
    a tela não pode presumir) mostra a recusa dentro do card, sem botão
    de uso algum e sem levantar exceção para fora do handler do botão."""
    from tkinter import ttk

    from calc_core.modelos import ResultadoSigmaAdmELU
    from ui.completo.dialogo_sigma_adm import DialogoSigmaAdm

    root = _tk_root()
    try:
        dialogo = DialogoSigmaAdm(root)
        resultado_sem_fsg = ResultadoSigmaAdmELU(
            sigma_adm_ELU_kPa=200.0, metodo="teorico", nome_do_metodo="x",
            metodo_de_seguranca="admissivel", rotulo_ELU=ROTULO_ELU,
            rotulo_fonte="fonte")
        saida = ttk.Frame(dialogo)
        dialogo._calcular_vento_no_card(resultado_sem_fsg, saida)

        textos = [w.cget("text") for w in saida.winfo_children()
                  if "text" in w.keys()]
        assert any("Sem FSg" in t for t in textos)
        assert not any(isinstance(w, ttk.Button) for w in saida.winfo_children())
    finally:
        root.destroy()


# --------------------------------------------------------------------------- #
#  REQ-UI-SIGMA-04 — dois campos de gamma, aviso de peso específico
#  efetivo, e nenhuma classificação de solo por N_SPT em lugar nenhum.
# --------------------------------------------------------------------------- #
def test_dois_campos_de_gamma_no_teorico_e_aviso_de_efetivo_presente():
    from ui.completo.dialogo_sigma_adm import AVISO_GAMMA_EFETIVO, DialogoSigmaAdm

    root = _tk_root()
    try:
        dialogo = DialogoSigmaAdm(root)
        assert dialogo.t_gamma_acima is not dialogo.t_gamma_abaixo
        dialogo.t_gamma_acima.set("18")
        dialogo.t_gamma_abaixo.set("10")   # abaixo do NA: efetivo, bem menor
        assert dialogo.t_gamma_acima.get() == "18"
        assert dialogo.t_gamma_abaixo.get() == "10"
        assert "EFETIVO" in AVISO_GAMMA_EFETIVO
        assert "SEMPRE DO LADO INSEGURO" in AVISO_GAMMA_EFETIVO
    finally:
        root.destroy()


_TEXTOS_DE_CLASSIFICACAO_PROIBIDOS = (
    "medianamente compacta", "argila rija", "fofa", "muito compacta")


def test_nenhum_resultado_exibe_classificacao_de_solo_por_nspt():
    """REQ-UI-SIGMA-04: PROIBIDO exibir classificação de solo (ex.: 'areia
    medianamente compacta') como se fosse resultado de cálculo — as faixas
    vêm da NBR 6484, ausente do acervo."""
    dispersao = semiempirico_spt(EntradaSemiempiricaSPT(
        N_spt=15.0, B_m=2.0, forma="quadrada", solo_declarado="areia",
        h_m=1.5, gamma_kN_m3=18.0, aplicabilidade_regional_declarada=True))
    for resultado in dispersao.resultados:
        texto = " ".join(resultado.avisos).lower()
        for proibido in _TEXTOS_DE_CLASSIFICACAO_PROIBIDOS:
            assert proibido not in texto


# --------------------------------------------------------------------------- #
#  Ligação com formulario.py — PREENCHE v_sigma_adm, nunca trava o campo,
#  e mostra ROTULO_ELU na TELA PRINCIPAL (REQ-UI-SIGMA-01, metade que
#  faltava até a rodada 3 — a outra metade, no memorial exportado, já
#  estava coberta).
# --------------------------------------------------------------------------- #
def test_abrir_calculadora_preenche_sigma_adm_sem_travar_o_campo():
    from unittest import mock

    from calc_core.modelos import ROTULO_ELU as _ROTULO_ELU
    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        painel.v_sigma_adm.set("250")
        assert painel.lbl_sigma_adm_elu.cget("text") == ""

        class _DialogoFalso:
            def __init__(self, master):
                self.resultado_kPa = 345.0
                self.resultado_info = {"origem": "teste"}

        painel.wait_window = lambda w: None
        with mock.patch("ui.completo.formulario.DialogoSigmaAdm", _DialogoFalso):
            painel._abrir_calculadora_sigma_adm()

        assert painel.v_sigma_adm.get() == "345"
        assert painel.ultimo_sigma_adm_calculado == {"origem": "teste"}
        # REQ-UI-SIGMA-01, metade "na tela principal": achado zero pela
        # varredura do a6 na rodada 3 (`grep`-se por "ELU" em todos os
        # widgets de PainelEntrada) — agora o rótulo aparece colado ao
        # campo `v_sigma_adm` quando o valor ali vem de cálculo.
        assert "ELU" in painel.lbl_sigma_adm_elu.cget("text")
        assert painel.lbl_sigma_adm_elu.cget("text") == _ROTULO_ELU

        # o campo continua um Entry comum, editável — nunca travado
        # (NBR 6122 §7.2: sobreposição manual sempre disponível).
        painel.v_sigma_adm.set("999")
        assert painel.v_sigma_adm.get() == "999"
        assert painel.ler_solo().sigma_adm == pytest.approx(999.0)
        # e a edição manual apaga o rótulo — não é mais um valor calculado.
        assert painel.lbl_sigma_adm_elu.cget("text") == ""
    finally:
        root.destroy()


def test_abrir_calculadora_cancelada_nao_altera_sigma_adm():
    from unittest import mock

    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        painel.v_sigma_adm.set("250")

        class _DialogoCancelado:
            def __init__(self, master):
                self.resultado_kPa = None
                self.resultado_info = None

        painel.wait_window = lambda w: None
        with mock.patch("ui.completo.formulario.DialogoSigmaAdm",
                        _DialogoCancelado):
            painel._abrir_calculadora_sigma_adm()

        assert painel.v_sigma_adm.get() == "250"
        assert painel.ultimo_sigma_adm_calculado is None
        assert painel.lbl_sigma_adm_elu.cget("text") == ""
    finally:
        root.destroy()


# --------------------------------------------------------------------------- #
#  REDESENHO (rodada 4) — a classe inteira de defeito que D-01/MÉDIA #1/#2
#  reproduziam (cache "selecionado, pronto para usar" sobrevivendo a uma
#  mudança de entrada) fica estruturalmente impossível: cada card só
#  existe enquanto representar o último cálculo, e o botão que ele carrega
#  morre junto com ele.
# --------------------------------------------------------------------------- #
def test_recalcular_semiempirico_apos_mudar_nspt_destroi_o_card_antigo():
    """Reproduz EXATAMENTE a classe de defeito do relato original: N_SPT =
    15 (300 kPa) calculado, depois N_SPT muda para 10 (200 kPa) e
    recalcula-se — o card antigo (com o botão que entregaria 300 kPa) tem
    de ter sido DESTRUÍDO (`winfo_exists()` falso), e o botão do card NOVO
    tem de entregar exatamente o que a tela mostra agora (200 kPa), nunca
    o valor antigo."""
    from ui.completo.dialogo_sigma_adm import DialogoSigmaAdm

    root = _tk_root()
    try:
        dialogo = DialogoSigmaAdm(root)
        dialogo.s_nspt.set("15")
        dialogo.s_B.set("2.0")
        dialogo.s_solo.set("argila")
        dialogo.s_h.set("1.5")
        dialogo.s_gamma.set("18")
        dialogo.s_regional.set(True)

        dialogo._calcular_semiempirico()
        # N_SPT=15/argila/regional=True: regra N/50 se aplica (300 kPa) E
        # Teixeira recusa (solo != areia) — dois cards, um resultado e uma
        # recusa (ver `test_dialogo_semiempirico_argila_mostra_um_
        # resultado_e_uma_recusa`).
        cartas_300 = dialogo.frame_resultado_semi.winfo_children()
        assert len(cartas_300) == 2
        card_300 = next(c for c in cartas_300
                         if c.cget("text") != "Recusado — fora do domínio")
        assert "300.0 kPa" in card_300.winfo_children()[0].cget("text")
        botao_300 = _botao(card_300, "Usar este valor →")

        # muda a entrada e recalcula — a mesma sequência que o a6 reproduziu
        dialogo.s_nspt.set("10")
        dialogo._calcular_semiempirico()

        # o card (e o botão) de 300 kPa não existem mais na árvore de widgets
        assert botao_300.winfo_exists() == 0

        cartas_200 = dialogo.frame_resultado_semi.winfo_children()
        assert len(cartas_200) == 2
        card_200 = next(c for c in cartas_200
                         if c.cget("text") != "Recusado — fora do domínio")
        assert card_200 is not card_300
        assert "200.0 kPa" in card_200.winfo_children()[0].cget("text")
        botao_200 = _botao(card_200, "Usar este valor →")
        botao_200.invoke()

        # "usar" entregou o valor do card ATUALMENTE na tela — nunca 300.
        assert dialogo.resultado_kPa == pytest.approx(200.0)
    finally:
        root.destroy()


def test_recalcular_teorico_apos_mudar_B_com_novo_valor_recusado_nao_deixa_botao_antigo():
    """Metade "domínio" do mesmo relato: B muda para um valor que o núcleo
    RECUSA (aqui, phi extremo o bastante para violar a hipótese de Terzaghi
    já testada em `test_texto_recusa_distingue_...`) — o card antigo, com
    resultado válido, é destruído mesmo assim, e o card novo é de RECUSA,
    sem botão "Usar" algum. Não pode sobrar um botão "Usar" de um cálculo
    que não corresponde mais ao que está na tela."""
    from tkinter import ttk

    from ui.completo.dialogo_sigma_adm import DialogoSigmaAdm

    root = _tk_root()
    try:
        dialogo = DialogoSigmaAdm(root)
        dialogo.t_c.set("0")
        dialogo.t_phi.set("30")
        dialogo.t_B.set("2.0")
        dialogo.t_L.set("2.0")
        dialogo.t_h.set("1.5")
        dialogo.t_gamma_acima.set("18")
        dialogo.t_gamma_abaixo.set("18")
        dialogo.t_homogeneo.set(True)

        dialogo._calcular_teorico()
        card_valido = dialogo.frame_resultado_teorico.winfo_children()[0]
        botao_valido = _botao(card_valido, "Usar este valor →")

        # phi = 60 graus é o mesmo valor que
        # `test_texto_recusa_distingue_declarado_em_texto_de_extensao_de_
        # figura` já trava como RECUSADO por Terzaghi.
        dialogo.t_phi.set("60")
        dialogo._calcular_teorico()

        assert botao_valido.winfo_exists() == 0
        filhos = dialogo.frame_resultado_teorico.winfo_children()
        assert len(filhos) == 1
        assert filhos[0].cget("text") == "Recusado — fora do domínio"
        assert not any(isinstance(w, ttk.Button)
                        for w in filhos[0].winfo_children())
        assert dialogo.resultado_kPa is None
    finally:
        root.destroy()


def test_usar_base_de_um_card_nunca_depende_de_estado_de_outro_card():
    """Contraprova estrutural do REDESENHO: com DOIS cards na tela ao mesmo
    tempo (dispersão semiempírica — aqui simulada calculando dois perfis
    válidos manualmente e desenhando os dois), o botão "Usar este valor →"
    de cada um entrega exatamente o valor DAQUELE card, nunca do outro —
    não existe "o card selecionado" global."""
    from ui.completo.dialogo_sigma_adm import DialogoSigmaAdm

    root = _tk_root()
    try:
        dialogo = DialogoSigmaAdm(root)
        resultado_argila = semiempirico_spt(EntradaSemiempiricaSPT(
            N_spt=15.0, B_m=2.0, forma="quadrada", solo_declarado="argila",
            h_m=1.5, gamma_kN_m3=18.0,
            aplicabilidade_regional_declarada=True)).resultados[0]
        resultado_areia = semiempirico_spt(EntradaSemiempiricaSPT(
            N_spt=15.0, B_m=2.0, forma="quadrada", solo_declarado="areia",
            h_m=1.5, gamma_kN_m3=18.0,
            aplicabilidade_regional_declarada=True)).resultados[0]
        assert resultado_argila.sigma_adm_ELU_kPa != pytest.approx(
            resultado_areia.sigma_adm_ELU_kPa)

        dialogo._card_resultado(dialogo.frame_resultado_semi, resultado_argila)
        dialogo._card_resultado(dialogo.frame_resultado_semi, resultado_areia)
        card_argila, card_areia = dialogo.frame_resultado_semi.winfo_children()

        _botao(card_areia, "Usar este valor →").invoke()
        assert dialogo.resultado_kPa == pytest.approx(
            resultado_areia.sigma_adm_ELU_kPa)
    finally:
        root.destroy()


def test_recalcular_majoracao_apos_trocar_tipo_de_obra_atualiza_teto():
    """Não existe mais `_invalidar_vento`/`bind("<<ComboboxSelected>>",
    ...)` para "esquecer" — `_calcular_vento_no_card` lê `self.v_tipo_obra`
    NA HORA de cada clique em "Calcular majoração...". Este teste prova a
    consequência observável: recalcular depois de trocar o tipo de obra
    muda o teto de 30 % (lista fechada) para 15 % (caso geral) — se algum
    dia a leitura do combo for trocada por um valor cacheado, este teste
    falha."""
    from tkinter import ttk

    from ui.completo.dialogo_sigma_adm import _SEM_LISTA_FECHADA, DialogoSigmaAdm

    root = _tk_root()
    try:
        dialogo = DialogoSigmaAdm(root)
        dispersao = semiempirico_spt(EntradaSemiempiricaSPT(
            N_spt=15.0, B_m=2.0, forma="quadrada", solo_declarado="argila",
            h_m=1.5, gamma_kN_m3=18.0,
            aplicabilidade_regional_declarada=True))
        resultado_300 = dispersao.resultados[0]

        dialogo.v_vento_principal.set(True)
        dialogo._alternar_vento()
        dialogo.v_tipo_obra.set(TIPOS_DE_OBRA_DOS_30_POR_CENTO[0])

        saida = ttk.Frame(dialogo)
        dialogo._calcular_vento_no_card(resultado_300, saida)
        texto_30 = " ".join(
            w.cget("text") for w in saida.winfo_children() if "text" in w.keys())
        assert "0.3000" in texto_30

        dialogo.v_tipo_obra.set(_SEM_LISTA_FECHADA)
        dialogo._calcular_vento_no_card(resultado_300, saida)
        texto_15 = " ".join(
            w.cget("text") for w in saida.winfo_children() if "text" in w.keys())
        assert "0.1500" in texto_15
        assert "0.3000" not in texto_15
    finally:
        root.destroy()


def test_editar_kv_sem_recalcular_botao_ja_visivel_entrega_o_que_esta_no_card():
    """A propriedade central do REDESENHO, em uma frase: o que o botão
    "Usar valor majorado →" entrega é SEMPRE o que está escrito no card
    NO MOMENTO do clique — nunca recalculado às escondidas contra um
    widget que mudou depois. Aqui, calcula-se a majoração com k_v = 0,15
    (345 kPa), edita-se k_v para 0,05 SEM clicar em "Calcular" de novo, e
    o botão "Usar valor majorado →" que já estava na tela — sem ser
    recriado — continua entregando 345 kPa, exatamente o que o texto do
    card ainda mostra (o card não foi recalculado, então "o que está na
    tela" continua sendo 345 kPa; não há mentira entre tela e entrega).
    Invocar o botão fecha o diálogo (mesmo padrão de qualquer botão
    "Usar..." desta tela) — por isso este teste termina aqui, e o cenário
    "recalcular troca o card" vive em outro teste, com outro diálogo."""
    from tkinter import ttk

    from ui.completo.dialogo_sigma_adm import DialogoSigmaAdm

    root = _tk_root()
    try:
        dialogo = DialogoSigmaAdm(root)
        dispersao = semiempirico_spt(EntradaSemiempiricaSPT(
            N_spt=15.0, B_m=2.0, forma="quadrada", solo_declarado="argila",
            h_m=1.5, gamma_kN_m3=18.0,
            aplicabilidade_regional_declarada=True))
        resultado_300 = dispersao.resultados[0]

        dialogo.v_vento_principal.set(True)
        dialogo._alternar_vento()
        dialogo.v_kv.set("0.15")

        saida = ttk.Frame(dialogo)
        dialogo._calcular_vento_no_card(resultado_300, saida)
        botao_345 = _botao(saida, "Usar valor majorado →")

        # edita k_v SEM recalcular — o widget na tela ainda mostra 345 kPa
        dialogo.v_kv.set("0.05")
        assert botao_345.winfo_exists() == 1   # ninguém destruiu o card
        botao_345.invoke()
        assert dialogo.resultado_kPa == pytest.approx(345.0)
    finally:
        root.destroy()


def test_recalcular_vento_apos_editar_kv_troca_o_card_pelo_que_reflete_o_novo_valor():
    """Metade complementar do teste acima: recalcular EXPLICITAMENTE (novo
    clique em "Calcular majoração...", aqui `_calcular_vento_no_card` de
    novo) DEPOIS de editar k_v troca o card (e o botão) por um novo, que
    reflete k_v = 0,05 — o antigo (345 kPa, k_v = 0,15) é destruído."""
    from tkinter import ttk

    from ui.completo.dialogo_sigma_adm import DialogoSigmaAdm

    root = _tk_root()
    try:
        dialogo = DialogoSigmaAdm(root)
        dispersao = semiempirico_spt(EntradaSemiempiricaSPT(
            N_spt=15.0, B_m=2.0, forma="quadrada", solo_declarado="argila",
            h_m=1.5, gamma_kN_m3=18.0,
            aplicabilidade_regional_declarada=True))
        resultado_300 = dispersao.resultados[0]

        dialogo.v_vento_principal.set(True)
        dialogo._alternar_vento()
        dialogo.v_kv.set("0.15")

        saida = ttk.Frame(dialogo)
        dialogo._calcular_vento_no_card(resultado_300, saida)
        botao_345 = _botao(saida, "Usar valor majorado →")

        dialogo.v_kv.set("0.05")
        dialogo._calcular_vento_no_card(resultado_300, saida)

        assert botao_345.winfo_exists() == 0
        botao_novo = _botao(saida, "Usar valor majorado →")
        botao_novo.invoke()
        assert dialogo.resultado_kPa == pytest.approx(300.0 * 1.05)
    finally:
        root.destroy()


# --------------------------------------------------------------------------- #
#  MÉDIA #3 (GATE 2, rodada 3) — campo numérico vazio é ERRO, nunca um
#  default plausível (1.0/1.0/0.0) que produz um card de resultado válido.
# --------------------------------------------------------------------------- #
def test_campo_B_vazio_no_teorico_nao_produz_resultado_silencioso():
    from unittest import mock

    from ui.completo.dialogo_sigma_adm import DialogoSigmaAdm

    root = _tk_root()
    try:
        dialogo = DialogoSigmaAdm(root)
        dialogo.t_c.set("0")
        dialogo.t_phi.set("30")
        dialogo.t_B.set("")   # campo em branco — não "2.0" nem "1.0"
        dialogo.t_L.set("2.0")
        dialogo.t_h.set("1.5")
        dialogo.t_gamma_acima.set("18")
        dialogo.t_gamma_abaixo.set("18")
        dialogo.t_homogeneo.set(True)

        with mock.patch("ui.completo.dialogo_sigma_adm.messagebox.showerror"
                        ) as mock_erro:
            dialogo._calcular_teorico()

        assert mock_erro.called
        mensagem = mock_erro.call_args[0][1]
        assert "vazio" in mensagem.lower()
        # nenhum card de resultado (nem de recusa do núcleo) foi desenhado —
        # o erro foi pego ANTES de chegar em `teorico_terzaghi_vesic`.
        assert dialogo.frame_resultado_teorico.winfo_children() == []
    finally:
        root.destroy()


def test_campo_nspt_vazio_no_semiempirico_nao_produz_resultado_silencioso():
    from unittest import mock

    from ui.completo.dialogo_sigma_adm import DialogoSigmaAdm

    root = _tk_root()
    try:
        dialogo = DialogoSigmaAdm(root)
        dialogo.s_nspt.set("")   # campo em branco
        dialogo.s_B.set("2.0")
        dialogo.s_solo.set("argila")
        dialogo.s_h.set("1.5")
        dialogo.s_gamma.set("18")
        dialogo.s_regional.set(True)

        with mock.patch("ui.completo.dialogo_sigma_adm.messagebox.showerror"
                        ) as mock_erro:
            dialogo._calcular_semiempirico()

        assert mock_erro.called
        assert dialogo.frame_resultado_semi.winfo_children() == []
    finally:
        root.destroy()


# --------------------------------------------------------------------------- #
#  D-02 (GATE 2, rodada 3) — proveniência sobrevive até o clique em "Usar",
#  com o valor calculado incluído (`valor_kPa`), para o memorial poder
#  conferir que ainda é válida.
# --------------------------------------------------------------------------- #
def test_usar_base_grava_valor_kpa_na_proveniencia():
    from ui.completo.dialogo_sigma_adm import DialogoSigmaAdm

    root = _tk_root()
    try:
        dialogo = DialogoSigmaAdm(root)
        resultado = teorico_terzaghi_vesic(EntradaCapacidadeCarga(
            c_kPa=0.0, phi_graus=30.0, B_m=2.0, L_m=2.0, h_m=1.5,
            gamma_acima_da_base_kN_m3=18.0, gamma_abaixo_da_base_kN_m3=18.0,
            forma="quadrada", modo_de_ruptura="geral",
            natureza_do_carregamento="drenado",
            solo_homogeneo_no_bulbo_declarado=True))
        dialogo._usar_base(resultado)
        assert dialogo.resultado_info["valor_kPa"] == pytest.approx(
            resultado.sigma_adm_ELU_kPa)
        assert dialogo.resultado_info["majorado_por_vento"] is False
    finally:
        root.destroy()


# --------------------------------------------------------------------------- #
#  MÉDIA #4 (GATE 2, rodada 3) — `ultimo_sigma_adm_calculado` (e o rótulo
#  visível `lbl_sigma_adm_elu`, novo nesta rodada) é invalidado em
#  qualquer edição de `v_sigma_adm` que não seja o próprio preenchimento
#  pelo diálogo.
# --------------------------------------------------------------------------- #
def test_editar_sigma_adm_manualmente_invalida_proveniencia():
    from unittest import mock

    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)

        class _DialogoFalso:
            def __init__(self, master):
                self.resultado_kPa = 345.0
                self.resultado_info = {"origem": "teste", "valor_kPa": 345.0}

        painel.wait_window = lambda w: None
        with mock.patch("ui.completo.formulario.DialogoSigmaAdm", _DialogoFalso):
            painel._abrir_calculadora_sigma_adm()
        assert painel.ultimo_sigma_adm_calculado is not None
        assert painel.lbl_sigma_adm_elu.cget("text") != ""

        # edição manual, como se fosse o engenheiro digitando por cima
        # (NBR 6122 §7.2 — sobreposição sempre disponível)
        painel.v_sigma_adm.set("400")
        assert painel.ultimo_sigma_adm_calculado is None
        assert painel.lbl_sigma_adm_elu.cget("text") == ""
    finally:
        root.destroy()


# --------------------------------------------------------------------------- #
#  D-01 (GATE 2, rodada do redesenho + 1) — um card (com o botão "Usar
#  este valor →" que carrega) sobrevivia a uma mudança de ENTRADA que
#  nunca chegava a disparar um recálculo: reprodução exata do relato do
#  a6 (N_SPT=15 -> 300 kPa calculado; N_SPT muda para 5 SEM clicar em
#  "Calcular" de novo; o botão antigo continuava entregando 300 kPa, que
#  já não corresponde a N_SPT=5).
# --------------------------------------------------------------------------- #
def test_mudar_nspt_sem_recalcular_invalida_o_card_e_o_botao_antigo():
    """Reprodução EXATA do relato do a6: N_SPT=15 calculado (300,0 kPa,
    botão "Usar este valor →" criado); N_SPT muda para "5" SEM clicar em
    "Calcular" de novo. O card antigo (e o botão que entregaria 300 kPa,
    +200 % do correto para N_SPT=5 = 100 kPa, sempre do lado inseguro)
    precisa ter sido destruído, substituído por um aviso pedindo
    recálculo — nunca continuar na tela entregando o valor velho."""
    from ui.completo.dialogo_sigma_adm import (
        _AVISO_ENTRADAS_ALTERADAS,
        DialogoSigmaAdm,
    )

    root = _tk_root()
    try:
        dialogo = DialogoSigmaAdm(root)
        dialogo.s_nspt.set("15")
        dialogo.s_B.set("2.0")
        dialogo.s_forma.set("quadrada")
        dialogo.s_solo.set("argila")
        dialogo.s_h.set("1.5")
        dialogo.s_gamma.set("18")
        dialogo.s_regional.set(True)

        dialogo._calcular_semiempirico()
        card_300 = next(
            c for c in dialogo.frame_resultado_semi.winfo_children()
            if c.cget("text") != "Recusado — fora do domínio")
        assert "300.0 kPa" in card_300.winfo_children()[0].cget("text")
        botao_300 = _botao(card_300, "Usar este valor →")

        # muda a entrada SEM clicar em "Calcular" de novo — o gatilho
        # exato que o REDESENHO da rodada anterior não cobria.
        dialogo.s_nspt.set("5")

        # o card (e o botão) de 300 kPa não existem mais na árvore de
        # widgets — nenhum botão "Usar" entrega mais 300 kPa.
        assert botao_300.winfo_exists() == 0
        filhos = dialogo.frame_resultado_semi.winfo_children()
        assert len(filhos) == 1
        assert filhos[0].cget("text") == _AVISO_ENTRADAS_ALTERADAS
        # nenhum botão "Usar" sobra em lugar nenhum do frame de resultado.
        with pytest.raises(AssertionError):
            _botao(dialogo.frame_resultado_semi, "Usar este valor →")
        # continua None: nada foi (nem pode ser) "usado" a partir do card
        # velho.
        assert dialogo.resultado_kPa is None

        # recalcular de novo faz o valor CORRETO aparecer (100 kPa para
        # N_SPT=5 pela regra N/50) e o aviso desaparece.
        dialogo._calcular_semiempirico()
        card_100 = next(
            c for c in dialogo.frame_resultado_semi.winfo_children()
            if c.cget("text") != "Recusado — fora do domínio")
        assert "100.0 kPa" in card_100.winfo_children()[0].cget("text")
        botao_100 = _botao(card_100, "Usar este valor →")
        botao_100.invoke()
        assert dialogo.resultado_kPa == pytest.approx(100.0)
    finally:
        root.destroy()


def test_mudar_campo_teorico_sem_recalcular_invalida_o_card():
    """Mesma classe de defeito, caminho teórico — cobre um campo NUMÉRICO
    comum (B) fora do caminho semiempírico já testado acima, provando que
    a vigilância não é específica de uma aba só."""
    from ui.completo.dialogo_sigma_adm import (
        _AVISO_ENTRADAS_ALTERADAS,
        DialogoSigmaAdm,
    )

    root = _tk_root()
    try:
        dialogo = DialogoSigmaAdm(root)
        dialogo.t_c.set("0")
        dialogo.t_phi.set("30")
        dialogo.t_B.set("2.0")
        dialogo.t_L.set("2.0")
        dialogo.t_h.set("1.5")
        dialogo.t_gamma_acima.set("18")
        dialogo.t_gamma_abaixo.set("18")
        dialogo.t_homogeneo.set(True)

        dialogo._calcular_teorico()
        assert len(dialogo.frame_resultado_teorico.winfo_children()) == 1
        botao_antigo = _botao(
            dialogo.frame_resultado_teorico.winfo_children()[0],
            "Usar este valor →")

        dialogo.t_B.set("2.5")   # muda SEM recalcular

        assert botao_antigo.winfo_exists() == 0
        filhos = dialogo.frame_resultado_teorico.winfo_children()
        assert len(filhos) == 1
        assert filhos[0].cget("text") == _AVISO_ENTRADAS_ALTERADAS
        assert dialogo.resultado_kPa is None
    finally:
        root.destroy()


def test_mudar_checkbox_homogeneo_sem_recalcular_invalida_o_card():
    """Cobre especificamente um `BooleanVar` de Checkbutton (não um Entry
    nem um Combobox) — `t_homogeneo` — para provar que a vigilância por
    `trace_add` não depende do tipo de widget."""
    from ui.completo.dialogo_sigma_adm import (
        _AVISO_ENTRADAS_ALTERADAS,
        DialogoSigmaAdm,
    )

    root = _tk_root()
    try:
        dialogo = DialogoSigmaAdm(root)
        dialogo.t_c.set("0")
        dialogo.t_phi.set("30")
        dialogo.t_B.set("2.0")
        dialogo.t_L.set("2.0")
        dialogo.t_h.set("1.5")
        dialogo.t_gamma_acima.set("18")
        dialogo.t_gamma_abaixo.set("18")
        dialogo.t_homogeneo.set(True)

        dialogo._calcular_teorico()
        assert len(dialogo.frame_resultado_teorico.winfo_children()) == 1

        dialogo.t_homogeneo.set(False)   # muda SEM recalcular

        filhos = dialogo.frame_resultado_teorico.winfo_children()
        assert len(filhos) == 1
        assert filhos[0].cget("text") == _AVISO_ENTRADAS_ALTERADAS
    finally:
        root.destroy()


def test_mudar_entrada_de_uma_aba_nao_invalida_o_card_da_outra():
    """A vigilância é POR ABA (por frame de resultado) — mudar N_SPT não
    pode apagar um card já calculado na aba teórico, e vice-versa."""
    from ui.completo.dialogo_sigma_adm import DialogoSigmaAdm

    root = _tk_root()
    try:
        dialogo = DialogoSigmaAdm(root)
        dialogo.t_c.set("0")
        dialogo.t_phi.set("30")
        dialogo.t_B.set("2.0")
        dialogo.t_L.set("2.0")
        dialogo.t_h.set("1.5")
        dialogo.t_gamma_acima.set("18")
        dialogo.t_gamma_abaixo.set("18")
        dialogo.t_homogeneo.set(True)
        dialogo._calcular_teorico()
        assert len(dialogo.frame_resultado_teorico.winfo_children()) == 1

        dialogo.s_nspt.set("999")   # muda a OUTRA aba

        # o card teórico continua intacto — mesmo objeto, mesmo botão.
        filhos = dialogo.frame_resultado_teorico.winfo_children()
        assert len(filhos) == 1
        _botao(filhos[0], "Usar este valor →")   # ainda existe
    finally:
        root.destroy()


def test_mudar_entrada_sem_calculo_previo_nao_desenha_aviso_nenhum():
    """Sem card algum na tela ainda, mudar um campo não deve desenhar o
    aviso "ENTRADAS ALTERADAS" — não há nada para invalidar."""
    from ui.completo.dialogo_sigma_adm import DialogoSigmaAdm

    root = _tk_root()
    try:
        dialogo = DialogoSigmaAdm(root)
        dialogo.s_nspt.set("20")
        assert dialogo.frame_resultado_semi.winfo_children() == []
    finally:
        root.destroy()


def test_mudar_vento_sem_recalcular_nao_invalida_o_card_teorico_ou_semi():
    """Fora de escopo desta correção (documentado no pedido de trabalho):
    os controles de vento (`v_vento_principal`/`v_tipo_obra`/`v_kv`) não
    fazem parte da vigilância dos frames de resultado principais — a
    mini-seção de vento de cada card já resolve sua própria invalidação
    por closure/releitura no clique (mecanismo intocado nesta rodada)."""
    from ui.completo.dialogo_sigma_adm import DialogoSigmaAdm

    root = _tk_root()
    try:
        dialogo = DialogoSigmaAdm(root)
        dialogo.t_c.set("0")
        dialogo.t_phi.set("30")
        dialogo.t_B.set("2.0")
        dialogo.t_L.set("2.0")
        dialogo.t_h.set("1.5")
        dialogo.t_gamma_acima.set("18")
        dialogo.t_gamma_abaixo.set("18")
        dialogo.t_homogeneo.set(True)
        dialogo._calcular_teorico()

        dialogo.v_vento_principal.set(True)
        dialogo.v_kv.set("0.10")

        filhos = dialogo.frame_resultado_teorico.winfo_children()
        assert len(filhos) == 1
        _botao(filhos[0], "Usar este valor →")   # ainda existe, intacto
    finally:
        root.destroy()


# --------------------------------------------------------------------------- #
#  D-02 (GATE 2, rodada do redesenho + 1) — `_usar_majorado` incluía as
#  regras/avisos de `base` (`ResultadoSigmaAdmELU`) mas descartava os do
#  PRÓPRIO `ResultadoMajoracaoVento` — perdendo a regra que AUTORIZA a
#  majoração e o aviso literal do §6.3.2 sobre a verificação estrutural.
# --------------------------------------------------------------------------- #
def test_usar_majorado_inclui_regras_e_avisos_da_majoracao_de_vento():
    from tkinter import ttk

    from ui.completo.dialogo_sigma_adm import DialogoSigmaAdm

    root = _tk_root()
    try:
        dialogo = DialogoSigmaAdm(root)
        dispersao = semiempirico_spt(EntradaSemiempiricaSPT(
            N_spt=15.0, B_m=2.0, forma="quadrada", solo_declarado="argila",
            h_m=1.5, gamma_kN_m3=18.0,
            aplicabilidade_regional_declarada=True))
        resultado_300 = dispersao.resultados[0]

        dialogo.v_vento_principal.set(True)
        dialogo._alternar_vento()
        dialogo.v_kv.set("0.15")

        saida = ttk.Frame(dialogo)
        dialogo._calcular_vento_no_card(resultado_300, saida)
        botao_majorado = _botao(saida, "Usar valor majorado →")
        botao_majorado.invoke()

        info = dialogo.resultado_info
        assert info["majorado_por_vento"] is True
        # a regra que AUTORIZA a majoração precisa estar presente — sem
        # ela, o memorial cita o método de base como se a majoração não
        # tivesse fundamento normativo próprio.
        assert "NBR6122-6.3.2-majoracao-vento-valores-admissiveis" in \
            info["regras"]
        # as regras do método de BASE continuam presentes também (união,
        # não substituição).
        assert set(resultado_300.regras) <= set(info["regras"])
        # o aviso literal do §6.3.2 (verificação estrutural obrigatória)
        # precisa ter chegado — é o mesmo texto que
        # `ResultadoMajoracaoVento.avisos` carrega.
        assert set(resultado_300.avisos) <= set(info["avisos"])
        assert len(info["avisos"]) >= len(resultado_300.avisos)
        # sem duplicação: nenhum aviso repetido na lista final.
        assert len(info["avisos"]) == len(set(info["avisos"]))
        assert len(info["regras"]) == len(set(info["regras"]))
    finally:
        root.destroy()


def test_usar_base_nao_inclui_regras_de_majoracao_alguma():
    """Contraprova: `_usar_base` (sem vento) continua só com as
    regras/avisos do método de base — não há `ResultadoMajoracaoVento`
    algum envolvido nesse caminho."""
    from ui.completo.dialogo_sigma_adm import DialogoSigmaAdm

    root = _tk_root()
    try:
        dialogo = DialogoSigmaAdm(root)
        resultado = teorico_terzaghi_vesic(EntradaCapacidadeCarga(
            c_kPa=0.0, phi_graus=30.0, B_m=2.0, L_m=2.0, h_m=1.5,
            gamma_acima_da_base_kN_m3=18.0, gamma_abaixo_da_base_kN_m3=18.0,
            forma="quadrada", modo_de_ruptura="geral",
            natureza_do_carregamento="drenado",
            solo_homogeneo_no_bulbo_declarado=True))
        dialogo._usar_base(resultado)
        assert dialogo.resultado_info["regras"] == list(resultado.regras)
        assert dialogo.resultado_info["avisos"] == list(resultado.avisos)
        assert dialogo.resultado_info["majorado_por_vento"] is False
    finally:
        root.destroy()


def test_preencher_solo_invalida_proveniencia_calculada():
    from unittest import mock

    from calc_core.sapata_isolada.geotecnia import Solo
    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)

        class _DialogoFalso:
            def __init__(self, master):
                self.resultado_kPa = 345.0
                self.resultado_info = {"origem": "teste", "valor_kPa": 345.0}

        painel.wait_window = lambda w: None
        with mock.patch("ui.completo.formulario.DialogoSigmaAdm", _DialogoFalso):
            painel._abrir_calculadora_sigma_adm()
        assert painel.ultimo_sigma_adm_calculado is not None

        # "Abrir projeto..."/"Importar do Excel..." repõem o solo por
        # `preencher_solo` — a proveniência do cálculo ANTERIOR não tem
        # relação alguma com os dados recém-carregados.
        painel.preencher_solo(Solo(sigma_adm=180.0))
        assert painel.ultimo_sigma_adm_calculado is None
        assert painel.v_sigma_adm.get() == "180"
        assert painel.lbl_sigma_adm_elu.cget("text") == ""
    finally:
        root.destroy()
