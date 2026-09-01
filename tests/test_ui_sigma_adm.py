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

        assert dialogo._resultado_ativo is None   # nada selecionado ainda
        # um único card de resultado foi desenhado (nenhum de recusa)
        filhos = dialogo.frame_resultado_teorico.winfo_children()
        assert len(filhos) == 1
        card = filhos[0]
        assert card.cget("text") == esperado.nome_do_metodo

        # dispara a mesma ação do botão "Selecionar este valor →" dentro
        # do card, sem precisar simular clique de mouse.
        dialogo._selecionar(esperado)
        assert dialogo._resultado_ativo is esperado
        dialogo._usar()

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
        assert dialogo._resultado_ativo is None
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


def test_dialogo_semiempirico_sem_declaracao_regional_recusa_tudo():
    """`aplicabilidade_regional_declarada=False` (default, sem afirmação)
    é recusa em TODAS as correlações — `semiempirico_spt` levanta em vez
    de devolver lista vazia (REQ-SIGMA-04), e a tela mostra um único card
    de recusa em vez de travar silenciosamente."""
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
        assert len(filhos) == 1
        assert filhos[0].cget("text") == "Recusado — fora do domínio"
    finally:
        root.destroy()


# --------------------------------------------------------------------------- #
#  Majoração por vento (REQ-UI-SIGMA-05) — lista fechada, default que não
#  majora, FSg efetivo exibido.
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
        dialogo._selecionar(resultado)
        assert dialogo.v_kv.get() == "0"   # default que não majora

        dialogo._calcular_vento()

        assert dialogo._resultado_vento is not None
        assert dialogo._resultado_vento.sigma_adm_ELU_majorado_kPa == pytest.approx(
            resultado.sigma_adm_ELU_kPa)
        assert dialogo._resultado_vento.k_v_adotado == 0.0
    finally:
        root.destroy()


def test_vento_majoracao_bate_com_a_checagem_numerica_do_ruleset():
    """300 kPa -> 345 kPa com k_v = 0,15, caso geral (mesmo número que
    `test_vento_majoracao.py::test_checagem_numerica_do_ruleset`)."""
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

        dialogo._selecionar(resultado_300)
        dialogo.v_vento_principal.set(True)
        dialogo._alternar_vento()
        dialogo.v_tipo_obra.set(dialogo.v_tipo_obra.get())  # "Nenhum destes"
        dialogo.v_kv.set("0.15")

        dialogo._calcular_vento()

        assert dialogo._resultado_vento is not None
        assert dialogo._resultado_vento.sigma_adm_ELU_majorado_kPa == pytest.approx(345.0)
        assert str(dialogo.btn_selecionar_vento.cget("state")) == "normal"

        dialogo._selecionar_majorado()
        dialogo._usar()
        assert dialogo.resultado_kPa == pytest.approx(345.0)
        assert dialogo.resultado_info["majorado_por_vento"] is True
    finally:
        root.destroy()


def test_vento_sem_resultado_selecionado_nao_calcula_nada():
    from unittest import mock

    from ui.completo.dialogo_sigma_adm import DialogoSigmaAdm

    root = _tk_root()
    try:
        dialogo = DialogoSigmaAdm(root)
        dialogo.v_kv.set("0.10")
        dialogo.v_vento_principal.set(True)
        # `_calcular_vento` chama `messagebox.showinfo` neste ramo — mockado
        # para não abrir uma caixa de diálogo real esperando clique (mesmo
        # padrão de `test_projeto_e_excel.py`).
        with mock.patch("ui.completo.dialogo_sigma_adm.messagebox.showinfo"
                        ) as mock_info:
            dialogo._calcular_vento()
        assert mock_info.called
        assert dialogo._resultado_vento is None
        assert str(dialogo.btn_selecionar_vento.cget("state")) == "disabled"
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
#  Ligação com formulario.py — PREENCHE v_sigma_adm, nunca trava o campo.
# --------------------------------------------------------------------------- #
def test_abrir_calculadora_preenche_sigma_adm_sem_travar_o_campo():
    from unittest import mock

    from ui.completo.formulario import PainelEntrada

    root = _tk_root()
    try:
        painel = PainelEntrada(root)
        painel.v_sigma_adm.set("250")

        class _DialogoFalso:
            def __init__(self, master):
                self.resultado_kPa = 345.0
                self.resultado_info = {"origem": "teste"}

        painel.wait_window = lambda w: None
        with mock.patch("ui.completo.formulario.DialogoSigmaAdm", _DialogoFalso):
            painel._abrir_calculadora_sigma_adm()

        assert painel.v_sigma_adm.get() == "345"
        assert painel.ultimo_sigma_adm_calculado == {"origem": "teste"}

        # o campo continua um Entry comum, editável — nunca travado
        # (NBR 6122 §7.2: sobreposição manual sempre disponível).
        painel.v_sigma_adm.set("999")
        assert painel.v_sigma_adm.get() == "999"
        assert painel.ler_solo().sigma_adm == pytest.approx(999.0)
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
    finally:
        root.destroy()


# --------------------------------------------------------------------------- #
#  D-01 (GATE 2, rodada 3) — desmarcar "vento é ação principal" DEPOIS de
#  selecionar o valor MAJORADO não pode deixar `_usar()` devolver o número
#  majorado em cache. MÉDIA #1/#2 (mesma causa-raiz) cobertas junto.
# --------------------------------------------------------------------------- #
def test_desmarcar_vento_principal_depois_de_selecionar_majorado_invalida():
    """Reproduz EXATAMENTE a sequência do relato: selecionar um resultado,
    marcar vento como principal, calcular a majoração, selecionar o
    MAJORADO, DESMARCAR vento como principal — "Usar este valor →" não
    pode mais devolver o número majorado (345 kPa); o botão fica
    desabilitado até o engenheiro recalcular e escolher de novo."""
    from ui.completo.dialogo_sigma_adm import DialogoSigmaAdm

    root = _tk_root()
    try:
        dialogo = DialogoSigmaAdm(root)
        dispersao = semiempirico_spt(EntradaSemiempiricaSPT(
            N_spt=15.0, B_m=2.0, forma="quadrada", solo_declarado="argila",
            h_m=1.5, gamma_kN_m3=18.0,
            aplicabilidade_regional_declarada=True))
        resultado_300 = dispersao.resultados[0]
        assert resultado_300.sigma_adm_ELU_kPa == pytest.approx(300.0)

        # (1) seleciona o resultado de 300 kPa
        dialogo._selecionar(resultado_300)

        # (2) marca vento como principal, k_v = 0,15, calcula
        dialogo.v_vento_principal.set(True)
        dialogo._alternar_vento()
        dialogo.v_kv.set("0.15")
        dialogo._calcular_vento()
        assert dialogo._resultado_vento is not None
        assert dialogo._resultado_vento.sigma_adm_ELU_majorado_kPa == pytest.approx(345.0)

        # (3) seleciona o valor MAJORADO
        dialogo._selecionar_majorado()
        assert dialogo._valor_final_kPa == pytest.approx(345.0)
        assert dialogo._valor_final_e_majorado is True
        assert str(dialogo.btn_usar.cget("state")) == "normal"

        # (4) DESMARCA vento como ação principal — dispara `_alternar_vento`,
        # que precisa invalidar o resultado majorado em cache.
        dialogo.v_vento_principal.set(False)
        dialogo._alternar_vento()

        # A guarda: nem o resultado de vento, nem o valor final majorado,
        # sobrevivem à mudança de declaração.
        assert dialogo._resultado_vento is None
        assert dialogo._valor_final_e_majorado is False
        assert str(dialogo.btn_selecionar_vento.cget("state")) == "disabled"
        assert str(dialogo.btn_usar.cget("state")) == "disabled"

        # (5) "Usar este valor →" não devolve mais 345 kPa (nem nenhum
        # outro número — o botão está desabilitado, mas ainda assim
        # `_usar()` chamado diretamente por engano não pode vazar o valor
        # antigo: `_valor_final_kPa` já é `None`).
        dialogo._usar()
        assert dialogo.resultado_kPa is None
    finally:
        root.destroy()


def test_recalcular_vento_com_kv_diferente_invalida_selecao_majorada_anterior():
    """MÉDIA #1: mesma causa-raiz do D-01, mas pelo caminho "editar k_v e
    recalcular" em vez de "desmarcar o checkbox" — o valor majorado
    anterior (com o k_v velho) não pode sobreviver a um recálculo com um
    k_v novo sem que o engenheiro selecione de novo."""
    from ui.completo.dialogo_sigma_adm import DialogoSigmaAdm

    root = _tk_root()
    try:
        dialogo = DialogoSigmaAdm(root)
        dispersao = semiempirico_spt(EntradaSemiempiricaSPT(
            N_spt=15.0, B_m=2.0, forma="quadrada", solo_declarado="argila",
            h_m=1.5, gamma_kN_m3=18.0,
            aplicabilidade_regional_declarada=True))
        resultado_300 = dispersao.resultados[0]

        dialogo._selecionar(resultado_300)
        dialogo.v_vento_principal.set(True)
        dialogo._alternar_vento()
        dialogo.v_kv.set("0.15")
        dialogo._calcular_vento()
        dialogo._selecionar_majorado()
        assert dialogo._valor_final_kPa == pytest.approx(345.0)

        # edita k_v SEM clicar em "Calcular" de novo — o trace de escrita
        # em `v_kv` já precisa invalidar sozinho.
        dialogo.v_kv.set("0.05")

        assert dialogo._resultado_vento is None
        assert dialogo._valor_final_e_majorado is False
        assert dialogo._valor_final_kPa is None
        assert str(dialogo.btn_usar.cget("state")) == "disabled"
    finally:
        root.destroy()


def test_selecionar_valor_base_sobrevive_a_mudanca_em_campo_de_vento():
    """Contraprova: um valor final que veio do card BASE (nunca passou
    por `_selecionar_majorado`) não depende de campo algum de vento — ele
    continua "pronto para usar" mesmo que o engenheiro mexa no k_v depois
    (só o resultado de vento em si é zerado, não o valor final)."""
    from ui.completo.dialogo_sigma_adm import DialogoSigmaAdm

    root = _tk_root()
    try:
        dialogo = DialogoSigmaAdm(root)
        dispersao = semiempirico_spt(EntradaSemiempiricaSPT(
            N_spt=15.0, B_m=2.0, forma="quadrada", solo_declarado="argila",
            h_m=1.5, gamma_kN_m3=18.0,
            aplicabilidade_regional_declarada=True))
        resultado_300 = dispersao.resultados[0]
        dialogo._selecionar(resultado_300)
        assert dialogo._valor_final_kPa == pytest.approx(300.0)

        dialogo.v_kv.set("0.20")   # mexe num campo de vento, sem selecionar
                                    # nenhum valor majorado

        assert dialogo._valor_final_kPa == pytest.approx(300.0)
        assert str(dialogo.btn_usar.cget("state")) == "normal"
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
#  D-02 (GATE 2, rodada 3) — proveniência sobrevive até `_usar()`, com o
#  valor calculado incluído (`valor_kPa`), para o memorial poder conferir
#  que ainda é válida.
# --------------------------------------------------------------------------- #
def test_usar_grava_valor_kpa_na_proveniencia():
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
        dialogo._selecionar(resultado)
        dialogo._usar()
        assert dialogo.resultado_info["valor_kPa"] == pytest.approx(
            resultado.sigma_adm_ELU_kPa)
    finally:
        root.destroy()


# --------------------------------------------------------------------------- #
#  MÉDIA #4 (GATE 2, rodada 3) — `ultimo_sigma_adm_calculado` é invalidado
#  em qualquer edição de `v_sigma_adm` que não seja o próprio preenchimento
#  pelo diálogo (edição manual, `preencher_solo`).
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

        # edição manual, como se fosse o engenheiro digitando por cima
        # (NBR 6122 §7.2 — sobreposição sempre disponível)
        painel.v_sigma_adm.set("400")
        assert painel.ultimo_sigma_adm_calculado is None
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
    finally:
        root.destroy()
