"""
dialogo_sigma_adm.py
---------------------
Diálogo "Calcular σ_adm" — chamado a partir de `_secao_solo` em
`formulario.py`. Implementa REQ-UI-SIGMA-01 a REQ-UI-SIGMA-06 do
`ruleset.yaml` (bloco `requisitos_para_a3`), que ligam à tela os dois
caminhos de σ_adm já aprovados no GATE 2/GATE 3 sobre a v9:
`calc_core.geotecnico.sigma_adm.teorico_terzaghi_vesic` e
`.semiempirico_spt`, mais a majoração por vento de
`calc_core.geotecnico.vento`.

Restrição de a3-interface.md (CLAUDE.md regra 4): esta tela NÃO calcula
nada. Toda aritmética (Nc/Nq/Nγ, sigma_r, divisão por FSg, dispersão entre
correlações, teto e majoração de k_v) já está em `calc_core/geotecnico/`;
os métodos `_calcular_*` daqui só instanciam `EntradaCapacidadeCarga`/
`EntradaSemiempiricaSPT` a partir do texto digitado, chamam a função do
núcleo e formatam o que ela devolve — inclusive os textos de recusa
(`ForaDoDominioError`/`RecusaDeMetodo`), que já vêm com `parametro`,
`valor`, `intervalo`, `fonte` e `forca` prontos do núcleo; `_texto_recusa*`
só traduz o rótulo interno da força da guarda para uma frase legível
(REQ-UI-SIGMA-03) — não decide nada sobre a recusa em si.

MAPEAMENTO DOS REQUISITOS, para conferência rápida:

* REQ-UI-SIGMA-01 — `ROTULO_ELU` (constante do núcleo) aparece colado a
  TODO número devolvido, em `_card_resultado` e no resumo final. Nunca
  "tensão admissível" em rótulo algum desta tela.
* REQ-UI-SIGMA-02 — `ROTULO_FONTE_NAO_NORMATIVA` e
  `ADVERTENCIA_FORMULARIOS_DE_BOLSO` (do núcleo) aparecem junto de cada
  resultado; nenhum texto de fonte é redigido aqui.
* REQ-UI-SIGMA-03 — `_texto_recusa`/`_texto_recusa_metodo` mostram
  parâmetro, valor, intervalo e fonte, e distinguem DECLARADO_EM_TEXTO de
  ADOTADO_DA_EXTENSAO_DE_FIGURA (`_ROTULOS_DE_FORCA`). Nunca "erro de
  cálculo" genérico.
* REQ-UI-SIGMA-04 — dois campos de gamma no caminho teórico
  (`t_gamma_acima`/`t_gamma_abaixo`), com `AVISO_GAMMA_EFETIVO` visível
  junto dos dois; nenhuma classificação de solo por N_SPT é exibida em
  lugar nenhum desta tela (proibição expressa do requisito).
* REQ-UI-SIGMA-05 — `semiempirico_spt` roda TODAS as correlações
  aplicáveis e `_calcular_semiempirico` desenha um card por resultado,
  lado a lado, sem escolher; a dispersão (`dispersao_relativa`, já
  calculada pelo núcleo) é exibida quando houver mais de um valor. A
  seção de vento nunca infere `vento_e_acao_variavel_principal` e mostra
  o FSg efetivo (`ResultadoMajoracaoVento.FSg_efetivo`, do núcleo) e o
  teto (`k_v_maximo_admissivel`, do núcleo) lado a lado com o controle.
  A lista de sete tipos de obra vem de
  `vento.TIPOS_DE_OBRA_DOS_30_POR_CENTO` e é exibida por `Combobox`
  (`state="readonly"`), nunca como texto livre.
* REQ-UI-SIGMA-06 — `DECLARACAO_REGIONAL_EXIGIDA` (checkbox sem default
  afirmativo, aba semiempírico — REQ-SIGMA-06 é obrigação do §7.3.3, o
  caminho teórico não tem campo correspondente no núcleo) e
  `AVISO_ESCOPO_SIGMA_ADM` (banner fixo no topo do diálogo).

PROVENIÊNCIA NO MEMORIAL (D-02 do GATE 2, rodada 3 — revoga o adiamento
documentado nas rodadas 1/2): `_usar` grava a proveniência do valor
escolhido (método, `ROTULO_ELU`, `ROTULO_FONTE_NAO_NORMATIVA`, avisos,
regras/práticas e o próprio `valor_kPa`) em `self.resultado_info`;
`formulario.py::_abrir_calculadora_sigma_adm` copia isso para
`PainelEntrada.ultimo_sigma_adm_calculado`, que `ui.completo.app`/
`ui.completo.resultado` agora repassam para
`calc_core.sapata_isolada.relatorio.memorial`/`pranchas.gerar_memorial_pdf`
e `ui.completo.excel_export.exportar_relatorio_excel` — a linha de σ_adm
do memorial em texto/PDF/Excel carrega `ROTULO_ELU`/
`ROTULO_FONTE_NAO_NORMATIVA` sempre que o valor exportado ainda for
EXATAMENTE o que este diálogo calculou (`formulario.py::
_ao_editar_sigma_adm` zera `ultimo_sigma_adm_calculado` assim que o campo
`v_sigma_adm` muda por qualquer via que não seja o próprio preenchimento
do diálogo — edição manual, "Abrir projeto...", "Importar do Excel...").
Um σ_adm digitado à mão (ou vindo de uma dessas duas importações)
continua sem rótulo algum no memorial, exatamente como sempre foi.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from calc_core.geotecnico.dominio import (
    ADOTADO_DA_EXTENSAO_DE_FIGURA,
    DECLARADO_EM_TEXTO,
    DECLARADO_PELO_USUARIO,
    ForaDoDominioError,
)
from calc_core.geotecnico.seguranca import MetodoDeSegurancaError
from calc_core.geotecnico.semiempirico import SOLO_AREIA, SOLO_ARGILA
from calc_core.geotecnico.sigma_adm import semiempirico_spt, teorico_terzaghi_vesic
from calc_core.geotecnico.vento import (
    AVISO_ACAO_PRINCIPAL_NAO_E_INFERIDA,
    K_V_DEFAULT,
    TIPOS_DE_OBRA_DOS_30_POR_CENTO,
    MajoracaoDeVentoError,
    k_v_maximo_admissivel,
    majoracao_admissivel,
)
from calc_core.modelos import (
    DECLARACAO_REGIONAL_EXIGIDA,
    FORMAS_DE_BEER,
    MODOS_DE_RUPTURA,
    NATUREZAS_DE_CARREGAMENTO,
    ROTULO_ELU,
    ROTULO_FONTE_NAO_NORMATIVA,
    EntradaCapacidadeCarga,
    EntradaSemiempiricaSPT,
    RecusaDeMetodo,
    ResultadoMajoracaoVento,
    ResultadoSigmaAdmELU,
)

from . import tema

AVISO_ESCOPO_SIGMA_ADM = (
    "Escopo desta calculadora (NBR 6122:2022 §7.3.2/§7.3.3): sapata "
    "isolada, carga CENTRADA, solo HOMOGÊNEO no bulbo. Excentricidade NÃO "
    "é tratada — a área efetiva de Meyerhof está em kb/ mas não foi "
    "aprovada nesta versão. O valor devolvido é sempre a parcela de ELU "
    "(§7.3) — o §7.4 (ELS/recalque) não é verificado por caminho algum "
    "desta versão."
)

AVISO_GAMMA_EFETIVO = (
    "Abaixo do nível d'água o valor pedido é o peso específico EFETIVO "
    "(submerso, tipicamente 9-11 kN/m³), NÃO o saturado (19-21 kN/m³): "
    "usar o saturado como se fosse o efetivo erra gamma por um fator de "
    "~2, SEMPRE DO LADO INSEGURO. Os dois campos podem valer valores "
    "diferentes sob o mesmo símbolo — a fonte avisa disso."
)

_SEM_LISTA_FECHADA = "Nenhum destes — caso geral (majoração até 15 %)"

_ROTULOS_DE_FORCA = {
    DECLARADO_EM_TEXTO: (
        "Limite DECLARADO EM TEXTO pela fonte bibliográfica — só muda se a "
        "fonte mudar."),
    ADOTADO_DA_EXTENSAO_DE_FIGURA: (
        "Limite ADOTADO pelo a2-verificador a partir da EXTENSÃO de uma "
        "figura da fonte (não está escrito em texto) — revisável por "
        "decisão humana (ver kb/pendencias.md)."),
    DECLARADO_PELO_USUARIO: (
        "Declaração que a fonte normativa EXIGE e que o software não pode "
        "inferir — a ausência da marcação é recusa, não um default."),
}


def _float(valor: str, padrao: float = 0.0) -> float:
    valor = (valor or "").strip().replace(",", ".")
    return float(valor) if valor else padrao


def _float_opt(valor: str) -> float | None:
    valor = (valor or "").strip().replace(",", ".")
    return float(valor) if valor else None


def _int(valor: str, padrao: int = 0) -> int:
    valor = (valor or "").strip()
    return int(valor) if valor else padrao


def _float_requerido(rotulo: str, valor: str) -> float:
    """Como `_float`, mas campo VAZIO é ERRO — nunca um `padrao` plausível.

    MÉDIA #3 do GATE 2 (rodada 3): `_float(self.t_B.get(), 1.0)` e
    similares deixavam um campo de geometria/parâmetro em branco virar
    1.0/1.0/0.0 em silêncio (os `padrao` de `_calcular_teorico`), que nem
    batiam com o texto placeholder pré-preenchido nos campos ("2.0"/
    "1.5") — o núcleo então recebia um valor plausível que o engenheiro
    nunca digitou e devolvia um card de resultado completo (ex.: 202,1
    kPa) como se fosse um cálculo válido. Todo campo NUMÉRICO desta
    calculadora (as duas abas) passa por aqui: um valor ausente é uma
    entrada inválida, igual a um valor não numérico — nenhuma conta desta
    tela assume um número que o engenheiro não digitou (CLAUDE.md regra
    4). Levanta `ValueError`, capturado pelo mesmo `try/except` que já
    trata `float(texto_nao_numerico)` em `_calcular_teorico`/
    `_calcular_semiempirico`."""
    texto = (valor or "").strip().replace(",", ".")
    if not texto:
        raise ValueError(
            f"Campo obrigatório vazio: \"{rotulo}\". Preencha um valor "
            "antes de calcular — esta calculadora nunca completa um "
            "campo em branco com um número por conta própria.")
    return float(texto)


def _int_requerido(rotulo: str, valor: str) -> int:
    """Equivalente inteiro de `_float_requerido` — ver docstring lá."""
    texto = (valor or "").strip()
    if not texto:
        raise ValueError(
            f"Campo obrigatório vazio: \"{rotulo}\". Preencha um valor "
            "antes de calcular — esta calculadora nunca completa um "
            "campo em branco com um número por conta própria.")
    return int(texto)


def _texto_recusa(erro: ForaDoDominioError) -> str:
    """Formata uma ``ForaDoDominioError`` do núcleo (REQ-UI-SIGMA-03).

    Só formata o que a exceção já carrega (``parametro``, ``valor``,
    ``intervalo``, ``fonte``, ``forca``, ``sugestao``) — nenhum juízo sobre
    o domínio é feito aqui.
    """
    linhas = [
        (f"RECUSADO — {erro.parametro} = {erro.valor!r} fora do domínio "
         f"declarado ({erro.intervalo})."),
        f"Limite da FONTE, não do software: {erro.fonte}",
        _ROTULOS_DE_FORCA.get(erro.forca, erro.forca),
    ]
    if erro.sugestao:
        linhas.append(erro.sugestao)
    return "\n\n".join(linhas)


def _texto_recusa_metodo(recusa: RecusaDeMetodo) -> str:
    """Mesma tradução de ``_texto_recusa``, para uma ``RecusaDeMetodo`` de
    ``ResultadoDispersaoSemiempirica.recusas`` (correlação fora do domínio,
    mas outra(s) podem ter passado — por isso aparece como card, não como
    erro bloqueante)."""
    linhas = [
        f"{recusa.nome_do_metodo} — NÃO SE APLICA A ESTE CASO.",
        (f"{recusa.parametro} = {recusa.valor!r} fora do domínio declarado "
         f"({recusa.intervalo})."),
        f"Limite da FONTE, não do software: {recusa.fonte}",
        _ROTULOS_DE_FORCA.get(recusa.forca, recusa.forca),
    ]
    return "\n\n".join(linhas)


class DialogoSigmaAdm(tk.Toplevel):
    """Calcula σ_adm (parcela de ELU) e devolve o valor escolhido pelo
    engenheiro em ``self.resultado_kPa`` — quem chama (``formulario.py``)
    é quem decide PREENCHER o campo ``v_sigma_adm`` com ele; o campo
    continua editável depois (NBR 6122 §7.2 — sobreposição manual sempre
    disponível, nesta tela e em qualquer outra deste software)."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.title("Calcular σ_adm — parcela de ELU (NBR 6122:2022 §7.3)")
        self.configure(bg=tema.FUNDO_PAINEL)
        self.geometry("820x760")
        self.minsize(680, 520)
        self.transient(master)
        self.grab_set()

        self.resultado_kPa: float | None = None
        """Preenchido só quando o usuário clica "Usar este valor →"."""

        self.resultado_info: dict | None = None
        """Proveniência do valor escolhido — `formulario.py` guarda isto em
        `PainelEntrada.ultimo_sigma_adm_calculado` e o memorial/Excel do
        escopo amplo o usa para rotular a linha de σ_adm com `ROTULO_ELU`/
        `ROTULO_FONTE_NAO_NORMATIVA` sempre que ele ainda for válido (ver
        `formulario.py::_abrir_calculadora_sigma_adm` e
        `_ao_editar_sigma_adm`)."""

        self._resultado_ativo: ResultadoSigmaAdmELU | None = None
        self._resultado_vento: ResultadoMajoracaoVento | None = None
        self._valor_final_kPa: float | None = None
        self._valor_final_origem: str = ""
        self._valor_final_e_majorado: bool = False
        """`True` só quando `_valor_final_kPa` veio de `_selecionar_majorado`
        (MÉDIA #2 do GATE 2, rodada 3): antes desta flag,
        `resultado_info["majorado_por_vento"]` era decidido comparando
        `self._valor_final_kPa == self._resultado_vento.
        sigma_adm_ELU_majorado_kPa` — comparação de ponto flutuante
        (`==`) é frágil por definição, e ficou incorreta na prática depois
        de `_invalidar_vento` passar a zerar `_resultado_vento` (a
        comparação levantaria `AttributeError` em `None`, não só imprecisão
        de arredondamento). Setar um booleano explícito no momento da
        SELEÇÃO evita as duas classes de bug de uma vez."""

        self._montar()

    # ------------------------------------------------------------ montagem
    def _montar(self) -> None:
        ttk.Label(self, text=AVISO_ESCOPO_SIGMA_ADM, style="Banner.TLabel",
                  wraplength=780, justify="left", padding=(10, 6)).pack(
            fill="x")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=(8, 4))
        self._montar_aba_teorico(notebook)
        self._montar_aba_semiempirico(notebook)

        self._montar_vento(self)
        self._montar_resumo(self)

    def _area_rolavel(self, master: tk.Misc) -> ttk.Frame:
        """Canvas + scrollbar reaproveitando o padrão de
        ``PainelEntrada._montar_scroll`` (`formulario.py`) — o conteúdo de
        cada aba (campos + cards de resultado) pode crescer além da altura
        da janela."""
        canvas = tk.Canvas(master, bg=tema.FUNDO_PAINEL, highlightthickness=0)
        barra = ttk.Scrollbar(master, orient="vertical", command=canvas.yview)
        interior = ttk.Frame(canvas, style="Painel.TFrame")

        janela = canvas.create_window((0, 0), window=interior, anchor="nw")
        interior.bind("<Configure>",
                       lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfigure(janela, width=e.width))
        canvas.configure(yscrollcommand=barra.set)

        def _roda(evento: tk.Event) -> None:
            canvas.yview_scroll(-1 if evento.delta > 0 else 1, "units")

        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _roda))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        canvas.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        return interior

    def _campo(self, pai: ttk.Frame, row: int, rotulo: str, padrao: str,
               largura: int = 12) -> tk.StringVar:
        ttk.Label(pai, text=rotulo, style="PainelFraco.TLabel").grid(
            row=row, column=0, sticky="w", padx=(8, 4), pady=2)
        var = tk.StringVar(value=padrao)
        ttk.Entry(pai, textvariable=var, width=largura).grid(
            row=row, column=1, sticky="w", padx=(0, 8), pady=2)
        return var

    def _combo(self, pai: ttk.Frame, row: int, rotulo: str, valores,
               padrao: str, largura: int = 16) -> tk.StringVar:
        ttk.Label(pai, text=rotulo, style="PainelFraco.TLabel").grid(
            row=row, column=0, sticky="w", padx=(8, 4), pady=2)
        var = tk.StringVar(value=padrao)
        ttk.Combobox(pai, textvariable=var, state="readonly", width=largura,
                     values=list(valores)).grid(row=row, column=1, sticky="w",
                                                 padx=(0, 8), pady=2)
        return var

    # -------------------------------------------------------------- teórico
    def _montar_aba_teorico(self, notebook: ttk.Notebook) -> None:
        aba = ttk.Frame(notebook, style="Painel.TFrame")
        notebook.add(aba, text="Teórico (Terzaghi/Vesic)")
        interior = self._area_rolavel(aba)

        campos = ttk.LabelFrame(interior, text="Parâmetros — "
                                 "capacidade de carga (§7.3.2)")
        campos.grid(row=0, column=0, sticky="ew", padx=6, pady=6)

        self.t_c = self._campo(campos, 0, "c — coesão característica [kPa]", "0")
        self.t_phi = self._campo(campos, 1, "φ' — ângulo de atrito [graus]", "30")
        self.t_B = self._campo(campos, 2, "B — menor dimensão da base [m]", "2.0")
        self.t_L = self._campo(campos, 3, "L — maior dimensão da base [m]", "2.0")
        self.t_h = self._campo(campos, 4, "h — embutimento (h <= B) [m]", "1.5")
        self.t_gamma_acima = self._campo(
            campos, 5, "γ ACIMA da base [kN/m³] (efetivo)", "18")
        self.t_gamma_abaixo = self._campo(
            campos, 6, "γ ABAIXO da base [kN/m³] (efetivo)", "18")
        ttk.Label(campos, text=AVISO_GAMMA_EFETIVO, style="PainelFraco.TLabel",
                  wraplength=560, justify="left", font=("Segoe UI", 8)).grid(
            row=7, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 6))

        self.t_forma = self._combo(campos, 8, "Forma", FORMAS_DE_BEER, "quadrada")
        self.t_modo = self._combo(campos, 9, "Modo de ruptura", MODOS_DE_RUPTURA,
                                   "geral")
        self.t_natureza = self._combo(campos, 10, "Natureza do carregamento",
                                       NATUREZAS_DE_CARREGAMENTO, "drenado")

        self.t_homogeneo = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            campos, text="Declaro que o maciço no bulbo é HOMOGÊNEO (ou "
                         "camada equivalente) — sem esta marcação a função "
                         "recusa (§7.3.2, hipótese de Terzaghi)",
            variable=self.t_homogeneo).grid(
            row=11, column=0, columnspan=2, sticky="w", padx=8, pady=(4, 8))

        avancado = ttk.LabelFrame(
            interior, text="Provas de carga (opcional — FSg = 2,00 sob duas "
                           "condições, Tabela 1)")
        avancado.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 6))
        self.t_n_provas = self._campo(avancado, 0, "Nº de provas de carga", "0",
                                       largura=6)
        self.t_provas_projeto = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            avancado, text="Executadas na FASE DE PROJETO (§7.3.1) — prova de "
                          "carga de obra não reduz o FS",
            variable=self.t_provas_projeto).grid(
            row=1, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 6))

        ttk.Button(interior, text="Calcular (teórico)", style="Acento.TButton",
                   command=self._calcular_teorico).grid(
            row=2, column=0, sticky="w", padx=8, pady=8)

        self.frame_resultado_teorico = ttk.Frame(interior, style="Painel.TFrame")
        self.frame_resultado_teorico.grid(row=3, column=0, sticky="ew", padx=2)
        interior.columnconfigure(0, weight=1)

    def _calcular_teorico(self) -> None:
        for filho in self.frame_resultado_teorico.winfo_children():
            filho.destroy()
        try:
            entrada = EntradaCapacidadeCarga(
                c_kPa=_float_requerido(
                    "c — coesão característica [kPa]", self.t_c.get()),
                phi_graus=_float_requerido(
                    "φ' — ângulo de atrito [graus]", self.t_phi.get()),
                B_m=_float_requerido(
                    "B — menor dimensão da base [m]", self.t_B.get()),
                L_m=_float_requerido(
                    "L — maior dimensão da base [m]", self.t_L.get()),
                h_m=_float_requerido(
                    "h — embutimento (h <= B) [m]", self.t_h.get()),
                gamma_acima_da_base_kN_m3=_float_requerido(
                    "γ ACIMA da base [kN/m³]", self.t_gamma_acima.get()),
                gamma_abaixo_da_base_kN_m3=_float_requerido(
                    "γ ABAIXO da base [kN/m³]", self.t_gamma_abaixo.get()),
                forma=self.t_forma.get(),
                modo_de_ruptura=self.t_modo.get(),
                natureza_do_carregamento=self.t_natureza.get(),
                solo_homogeneo_no_bulbo_declarado=self.t_homogeneo.get(),
            )
        except ValueError as erro:
            messagebox.showerror("Entrada inválida", str(erro))
            return

        try:
            resultado = teorico_terzaghi_vesic(
                entrada,
                n_provas_de_carga=_int_requerido(
                    "Nº de provas de carga", self.t_n_provas.get()),
                provas_executadas_na_fase_de_projeto=self.t_provas_projeto.get(),
            )
        except ForaDoDominioError as erro:
            self._card_recusa(self.frame_resultado_teorico, _texto_recusa(erro))
            return
        except (MetodoDeSegurancaError, ValueError) as erro:
            self._card_recusa(self.frame_resultado_teorico, str(erro))
            return

        self._card_resultado(self.frame_resultado_teorico, resultado)

    # --------------------------------------------------------- semiempírico
    def _montar_aba_semiempirico(self, notebook: ttk.Notebook) -> None:
        aba = ttk.Frame(notebook, style="Painel.TFrame")
        notebook.add(aba, text="Semiempírico (SPT)")
        interior = self._area_rolavel(aba)

        campos = ttk.LabelFrame(interior, text="Parâmetros — correlações "
                                 "semiempíricas (§7.3.3)")
        campos.grid(row=0, column=0, sticky="ew", padx=6, pady=6)

        self.s_nspt = self._campo(campos, 0, "N_SPT [golpes]", "15")
        ttk.Label(
            campos, text="Para a regra N/50 é o valor MÉDIO NO BULBO de "
                         "tensões; Teixeira (1996) não declara a "
                         "profundidade de amostragem — ver avisos do "
                         "resultado.", style="PainelFraco.TLabel",
            wraplength=560, justify="left", font=("Segoe UI", 8)).grid(
            row=1, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 4))
        self.s_B = self._campo(campos, 2, "B — menor dimensão da base [m]", "2.0")
        self.s_forma = self._combo(campos, 3, "Forma", FORMAS_DE_BEER, "quadrada")
        self.s_solo = self._combo(campos, 4, "Solo declarado",
                                   (SOLO_ARGILA, SOLO_AREIA), SOLO_ARGILA)
        self.s_h = self._campo(campos, 5, "h — embutimento real [m]", "1.5")
        self.s_gamma = self._campo(campos, 6, "γ do solo [kN/m³]", "18")

        self.s_considerar_q = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            campos, text="Considerar parcela facultativa '+ q' (só regra "
                         "N/50) — desligada por default (lado seguro)",
            variable=self.s_considerar_q, command=self._alternar_q).grid(
            row=7, column=0, columnspan=2, sticky="w", padx=8, pady=(6, 0))
        self.s_q, self._entrada_q_widget = self._campo_com_widget(
            campos, 8, "q — sobrecarga [MPa] (não kPa!)", "")
        self._alternar_q()

        self.s_regional = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            campos, text="Declaro aplicabilidade regional das correlações "
                         "(obrigatório — §7.3.3 (c), sem default afirmativo)",
            variable=self.s_regional).grid(
            row=9, column=0, columnspan=2, sticky="w", padx=8, pady=(6, 2))
        ttk.Label(campos, text=DECLARACAO_REGIONAL_EXIGIDA,
                  style="PainelFraco.TLabel", wraplength=560, justify="left",
                  font=("Segoe UI", 8)).grid(
            row=10, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 8))

        ttk.Button(interior, text="Calcular (todas as correlações aplicáveis)",
                   style="Acento.TButton",
                   command=self._calcular_semiempirico).grid(
            row=1, column=0, sticky="w", padx=8, pady=8)

        self.frame_resultado_semi = ttk.Frame(interior, style="Painel.TFrame")
        self.frame_resultado_semi.grid(row=2, column=0, sticky="ew", padx=2)
        interior.columnconfigure(0, weight=1)

    def _alternar_q(self) -> None:
        """`q_MPa` só é lido pelo núcleo quando `considerar_q=True`
        (`_q_da_regra_50` recusa `q_MPa` != None com `considerar_q=False`) —
        desabilitar o campo aqui é só UX; a guarda de verdade é a do
        núcleo, chamada em `_calcular_semiempirico`."""
        estado = "normal" if self.s_considerar_q.get() else "disabled"
        self._entrada_q_widget.configure(state=estado)

    def _campo_com_widget(self, pai: ttk.Frame, row: int, rotulo: str,
                           padrao: str) -> tuple[tk.StringVar, ttk.Entry]:
        ttk.Label(pai, text=rotulo, style="PainelFraco.TLabel").grid(
            row=row, column=0, sticky="w", padx=(8, 4), pady=2)
        var = tk.StringVar(value=padrao)
        entrada = ttk.Entry(pai, textvariable=var, width=12)
        entrada.grid(row=row, column=1, sticky="w", padx=(0, 8), pady=2)
        return var, entrada

    def _calcular_semiempirico(self) -> None:
        for filho in self.frame_resultado_semi.winfo_children():
            filho.destroy()

        considerar_q = self.s_considerar_q.get()
        try:
            entrada = EntradaSemiempiricaSPT(
                N_spt=_float_requerido("N_SPT [golpes]", self.s_nspt.get()),
                B_m=_float_requerido(
                    "B — menor dimensão da base [m]", self.s_B.get()),
                forma=self.s_forma.get(),
                solo_declarado=self.s_solo.get(),
                h_m=_float_requerido(
                    "h — embutimento real [m]", self.s_h.get()),
                gamma_kN_m3=_float_requerido(
                    "γ do solo [kN/m³]", self.s_gamma.get()),
                aplicabilidade_regional_declarada=self.s_regional.get(),
                considerar_q=considerar_q,
                # `q_MPa` continua opcional aqui: quando `considerar_q=True`
                # e o campo está vazio, o próprio núcleo
                # (`semiempirico._q_da_regra_50`) recusa com "considerar_q=
                # True exige q_MPa explícito" — recusa rastreável, não um
                # default silencioso; não há necessidade de duplicar essa
                # guarda na UI.
                q_MPa=_float_opt(self.s_q.get()) if considerar_q else None,
            )
        except ValueError as erro:
            messagebox.showerror("Entrada inválida", str(erro))
            return

        try:
            dispersao = semiempirico_spt(entrada)
        except ForaDoDominioError as erro:
            self._card_recusa(self.frame_resultado_semi, _texto_recusa(erro))
            return
        except (MetodoDeSegurancaError, ValueError) as erro:
            self._card_recusa(self.frame_resultado_semi, str(erro))
            return

        if dispersao.dispersao_relativa is not None:
            ttk.Label(
                self.frame_resultado_semi,
                text=f"Dispersão observável entre os métodos aplicáveis: "
                     f"{dispersao.dispersao_relativa:.1%} (§7.3.3 (b) — a "
                     "escolha do valor de projeto é do engenheiro, "
                     "REQ-SIGMA-05).",
                style="PainelFraco.TLabel", wraplength=680, justify="left"
            ).pack(anchor="w", padx=6, pady=(2, 6))

        for resultado in dispersao.resultados:
            self._card_resultado(self.frame_resultado_semi, resultado)
        for recusa in dispersao.recusas:
            self._card_recusa(self.frame_resultado_semi,
                               _texto_recusa_metodo(recusa))

    # ------------------------------------------------------------- cards
    def _card_resultado(self, pai: tk.Misc, resultado: ResultadoSigmaAdmELU
                         ) -> None:
        f = ttk.LabelFrame(pai, text=resultado.nome_do_metodo)
        f.pack(fill="x", padx=4, pady=4)
        ttk.Label(f, text=f"{resultado.sigma_adm_ELU_kPa:.1f} kPa",
                  style="Painel.TLabel", font=("Consolas", 13, "bold")).pack(
            anchor="w", padx=8, pady=(6, 0))
        ttk.Label(f, text=resultado.rotulo_ELU, style="PainelFraco.TLabel",
                  wraplength=700, justify="left",
                  foreground=tema.AMARELO).pack(anchor="w", padx=8, pady=(2, 0))
        ttk.Label(f, text=resultado.rotulo_fonte, style="PainelFraco.TLabel",
                  wraplength=700, justify="left").pack(anchor="w", padx=8,
                                                        pady=(2, 0))
        try:
            fsg_txt = f"FSg efetivo (por trás deste valor) = {resultado.FSg_efetivo:.3f}"
        except ValueError:
            fsg_txt = "FSg efetivo indisponível para este resultado."
        ttk.Label(f, text=fsg_txt, style="PainelFraco.TLabel").pack(
            anchor="w", padx=8, pady=(2, 0))
        if resultado.avisos:
            texto_avisos = "\n".join(f"• {a}" for a in resultado.avisos)
            ttk.Label(f, text=texto_avisos, style="PainelFraco.TLabel",
                      wraplength=700, justify="left",
                      font=("Segoe UI", 8)).pack(anchor="w", padx=8,
                                                  pady=(4, 4))
        ttk.Button(f, text="Selecionar este valor →",
                   command=lambda r=resultado: self._selecionar(r)).pack(
            anchor="e", padx=8, pady=(2, 8))

    def _card_recusa(self, pai: tk.Misc, texto: str) -> None:
        f = ttk.LabelFrame(pai, text="Recusado — fora do domínio")
        f.pack(fill="x", padx=4, pady=4)
        ttk.Label(f, text=texto, style="PainelFraco.TLabel", wraplength=700,
                  justify="left", foreground=tema.VERMELHO).pack(
            anchor="w", padx=8, pady=6)

    # -------------------------------------------------------------- vento
    def _montar_vento(self, pai: tk.Misc) -> None:
        f = ttk.LabelFrame(pai, text="Majoração por vento (opcional) — "
                                      "NBR 6122:2022 §6.3.2")
        f.pack(fill="x", padx=10, pady=(4, 4))
        f.columnconfigure(1, weight=1)

        self.lbl_base_vento = ttk.Label(
            f, text="Nenhum resultado selecionado ainda — clique "
                    "\"Selecionar este valor →\" num dos cards acima para "
                    "habilitar a majoração por vento sobre ele.",
            style="PainelFraco.TLabel", wraplength=760, justify="left")
        self.lbl_base_vento.grid(row=0, column=0, columnspan=3, sticky="w",
                                  padx=8, pady=(6, 4))

        self.v_vento_principal = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            f, text="Vento é a ação variável principal na combinação "
                    "estrutural que governa este caso",
            variable=self.v_vento_principal, command=self._alternar_vento
        ).grid(row=1, column=0, columnspan=3, sticky="w", padx=8)
        ttk.Label(f, text=AVISO_ACAO_PRINCIPAL_NAO_E_INFERIDA,
                  style="PainelFraco.TLabel", wraplength=760, justify="left",
                  font=("Segoe UI", 8)).grid(row=2, column=0, columnspan=3,
                                              sticky="w", padx=8, pady=(0, 6))

        ttk.Label(f, text="Tipo de obra (lista FECHADA, §6.3.2)",
                  style="PainelFraco.TLabel").grid(row=3, column=0, sticky="w",
                                                    padx=8)
        opcoes_obra = [_SEM_LISTA_FECHADA, *TIPOS_DE_OBRA_DOS_30_POR_CENTO]
        self.v_tipo_obra = tk.StringVar(value=opcoes_obra[0])
        self.combo_tipo_obra = ttk.Combobox(
            f, textvariable=self.v_tipo_obra, state="disabled", width=52,
            values=opcoes_obra)
        self.combo_tipo_obra.grid(row=4, column=0, columnspan=3, sticky="w",
                                   padx=8, pady=(0, 6))

        ttk.Label(f, text="k_v adotado (0 = não majora; teto 0,15 ou 0,30 "
                          "conforme o tipo de obra e o piso de FSg = 1,6)",
                  style="PainelFraco.TLabel", wraplength=760,
                  justify="left").grid(row=5, column=0, columnspan=3,
                                        sticky="w", padx=8)
        self.v_kv = tk.StringVar(value=f"{K_V_DEFAULT:g}")
        ttk.Entry(f, textvariable=self.v_kv, width=10).grid(
            row=6, column=0, sticky="w", padx=8, pady=(0, 6))
        # D-01 do GATE 2, rodada 3: qualquer widget que alimenta
        # `_calcular_vento` — checkbox principal, combo de tipo de obra,
        # ou o próprio k_v — precisa invalidar `_resultado_vento` (e, se
        # for o caso, o valor "pronto para usar" majorado) assim que muda,
        # nunca só quando o botão "Calcular" é clicado de novo. Ver
        # `_invalidar_vento`.
        self.v_kv.trace_add("write", self._invalidar_vento)
        self.combo_tipo_obra.bind("<<ComboboxSelected>>", self._invalidar_vento)

        ttk.Button(f, text="Calcular teto e majoração",
                   command=self._calcular_vento).grid(
            row=6, column=1, sticky="w", padx=8, pady=(0, 6))

        self.lbl_resultado_vento = ttk.Label(
            f, text="", style="PainelFraco.TLabel", wraplength=760,
            justify="left")
        self.lbl_resultado_vento.grid(row=7, column=0, columnspan=3,
                                       sticky="w", padx=8, pady=(0, 4))

        self.btn_selecionar_vento = ttk.Button(
            f, text="Selecionar valor MAJORADO →", state="disabled",
            command=self._selecionar_majorado)
        self.btn_selecionar_vento.grid(row=8, column=0, sticky="w", padx=8,
                                        pady=(0, 8))

    def _alternar_vento(self) -> None:
        self.combo_tipo_obra.configure(
            state="readonly" if self.v_vento_principal.get() else "disabled")
        self._invalidar_vento()

    def _invalidar_vento(self, *_args) -> None:
        """Zera qualquer resultado de majoração por vento já calculado, e
        desabilita a seleção dele, sempre que um widget que ALIMENTA
        `_calcular_vento` muda depois de um cálculo (D-01 do GATE 2,
        rodada 3) — checkbox "vento é ação principal" (`_alternar_vento`),
        combo de tipo de obra (`<<ComboboxSelected>>`), campo `k_v`
        (`trace_add("write", ...)` em `v_kv`), e o início de todo novo
        `_calcular_vento` (recalcular também invalida o resultado anterior
        até o novo terminar).

        Sem isto, a sequência que o a6-revisor reproduziu passava direto:
        selecionar um resultado, marcar vento como ação principal,
        calcular a majoração, selecionar o valor MAJORADO, DESMARCAR vento
        como principal, e "Usar este valor →" ainda devolvia o número
        majorado — `_resultado_vento`/`_valor_final_kPa` ficavam em cache,
        nunca reconferidos contra a declaração atual. A guarda do núcleo
        (C1: "se not vento_principal, exigir k_v == 0") está correta; o
        problema era a TELA nunca chamá-la de novo.

        Se o valor "pronto para usar" atual (`_valor_final_kPa`) veio da
        majoração (`_valor_final_e_majorado`), ele TAMBÉM é invalidado — o
        engenheiro tem de clicar "Calcular teto e majoração" de novo e
        escolher explicitamente antes de poder usar qualquer valor. Um
        valor final que veio do card BASE (sem vento) não depende de
        nenhum destes campos e continua válido."""
        self._resultado_vento = None
        self.lbl_resultado_vento.configure(text="")
        self.btn_selecionar_vento.configure(state="disabled")
        if self._valor_final_e_majorado:
            self._valor_final_kPa = None
            self._valor_final_origem = ""
            self._valor_final_e_majorado = False
            self.btn_usar.configure(state="disabled")
            self.lbl_resumo.configure(
                text="A declaração de vento mudou depois da última "
                     "majoração — clique \"Calcular teto e majoração\" e "
                     "selecione o valor novamente antes de usar.")

    def _calcular_vento(self) -> None:
        self._invalidar_vento()
        if self._resultado_ativo is None:
            messagebox.showinfo(
                "Nenhum valor selecionado",
                "Selecione um resultado (aba Teórico ou Semiempírico) antes "
                "de calcular a majoração por vento — o teto e a majoração "
                "dependem do FSg por trás do valor escolhido.")
            return
        try:
            FSg = self._resultado_ativo.FSg_efetivo
        except ValueError as erro:
            messagebox.showerror("Sem FSg", str(erro))
            return

        principal = self.v_vento_principal.get()
        lista_30 = principal and self.v_tipo_obra.get() != _SEM_LISTA_FECHADA
        try:
            k_v = _float(self.v_kv.get(), K_V_DEFAULT)
        except ValueError:
            messagebox.showerror("Entrada inválida", "k_v deve ser numérico.")
            return

        try:
            teto = k_v_maximo_admissivel(
                FSg=FSg, vento_e_acao_variavel_principal=principal,
                tipo_de_obra_da_lista_dos_30_por_cento=lista_30)
            resultado = majoracao_admissivel(
                self._resultado_ativo.sigma_adm_ELU_kPa, FSg=FSg,
                vento_e_acao_variavel_principal=principal,
                tipo_de_obra_da_lista_dos_30_por_cento=lista_30, k_v=k_v)
        except (MajoracaoDeVentoError, ValueError) as erro:
            self.lbl_resultado_vento.configure(
                text=f"RECUSADO:\n{erro}", foreground=tema.VERMELHO)
            return

        self._resultado_vento = resultado
        texto = (
            f"Teto k_v admissível para este caso: {teto:.4f}\n"
            f"σ_adm,ELU base: {resultado.sigma_adm_ELU_base_kPa:.1f} kPa   →   "
            f"majorado: {resultado.sigma_adm_ELU_majorado_kPa:.1f} kPa "
            f"(k_v = {resultado.k_v_adotado:.4f})\n"
            f"FSg efetivo pós-majoração: {resultado.FSg_efetivo:.3f} "
            f"(piso exigido: 1,6)\n\n" + resultado.rotulo_ELU + "\n\n"
            + "\n".join(f"• {a}" for a in resultado.avisos)
        )
        self.lbl_resultado_vento.configure(text=texto, foreground=tema.TEXTO)
        self.btn_selecionar_vento.configure(state="normal")

    # ------------------------------------------------------------- resumo
    def _montar_resumo(self, pai: tk.Misc) -> None:
        f = ttk.Frame(pai, style="Painel.TFrame")
        f.pack(fill="x", padx=10, pady=(0, 10))
        self.lbl_resumo = ttk.Label(
            f, text="Nenhum valor selecionado ainda.",
            style="Painel.TLabel", font=("Segoe UI", 9, "bold"),
            wraplength=560, justify="left")
        self.lbl_resumo.pack(side="left", fill="x", expand=True)
        self.btn_usar = ttk.Button(f, text="Usar este valor →",
                                    style="Acento.TButton", state="disabled",
                                    command=self._usar)
        self.btn_usar.pack(side="right", padx=(8, 0))
        ttk.Button(f, text="Fechar sem usar valor algum",
                   command=self.destroy).pack(side="right")

    # -------------------------------------------------------------- seleção
    def _selecionar(self, resultado: ResultadoSigmaAdmELU) -> None:
        self._resultado_ativo = resultado
        self._resultado_vento = None
        self.lbl_resultado_vento.configure(text="")
        self.btn_selecionar_vento.configure(state="disabled")
        try:
            fsg_txt = f"{resultado.FSg_efetivo:.3f}"
        except ValueError:
            fsg_txt = "indisponível"
        self.lbl_base_vento.configure(
            text=f"Resultado ativo para majoração por vento: "
                 f"{resultado.nome_do_metodo} — σ_adm,ELU = "
                 f"{resultado.sigma_adm_ELU_kPa:.1f} kPa, FSg efetivo = "
                 f"{fsg_txt}.")

        self._valor_final_kPa = resultado.sigma_adm_ELU_kPa
        self._valor_final_origem = (
            f"{resultado.nome_do_metodo} — {ROTULO_ELU}, sem majoração de "
            "vento.")
        self._valor_final_e_majorado = False
        self._atualizar_resumo()

    def _selecionar_majorado(self) -> None:
        if self._resultado_vento is None or self._resultado_ativo is None:
            return
        self._valor_final_kPa = self._resultado_vento.sigma_adm_ELU_majorado_kPa
        self._valor_final_origem = (
            f"{self._resultado_ativo.nome_do_metodo} — {ROTULO_ELU}, "
            f"MAJORADA por vento (k_v = "
            f"{self._resultado_vento.k_v_adotado:.4f}, NBR 6122 §6.3.2).")
        # MÉDIA #2 do GATE 2, rodada 3: setado explicitamente AQUI, no
        # momento da seleção — nunca recalculado depois comparando floats
        # (`_valor_final_kPa == self._resultado_vento.
        # sigma_adm_ELU_majorado_kPa`, o padrão antigo em `_usar`).
        self._valor_final_e_majorado = True
        self._atualizar_resumo()

    def _atualizar_resumo(self) -> None:
        assert self._valor_final_kPa is not None
        self.lbl_resumo.configure(
            text=f"Pronto para usar: {self._valor_final_kPa:.1f} kPa — "
                 f"{self._valor_final_origem}")
        self.btn_usar.configure(state="normal")

    def _usar(self) -> None:
        if self._valor_final_kPa is None:
            return
        self.resultado_kPa = self._valor_final_kPa
        ativo = self._resultado_ativo
        self.resultado_info = {
            "valor_kPa": self._valor_final_kPa,
            "origem": self._valor_final_origem,
            "metodo": ativo.nome_do_metodo if ativo else "",
            "rotulo_ELU": ROTULO_ELU,
            "rotulo_fonte": ROTULO_FONTE_NAO_NORMATIVA,
            "avisos": list(ativo.avisos) if ativo else [],
            "regras": list(ativo.regras) if ativo else [],
            "praticas": list(ativo.praticas) if ativo else [],
            # MÉDIA #2 do GATE 2, rodada 3: flag setada explicitamente em
            # `_selecionar`/`_selecionar_majorado` — nunca mais um `==`
            # entre floats para decidir proveniência.
            "majorado_por_vento": self._valor_final_e_majorado,
        }
        self.destroy()


__all__ = ["DialogoSigmaAdm"]
