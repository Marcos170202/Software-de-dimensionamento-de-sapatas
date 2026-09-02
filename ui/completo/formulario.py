"""
formulario.py
-------------
Coluna esquerda: coleta de entrada.

Restrição de a3-interface.md: esta tela não calcula nada. Cada método
`ler_*` só instancia os objetos de entrada de `calc_core.sapata_isolada`
(`Pilar`, `Solo`, `Concreto`, `Aco`, `CasoCarga`, `OpcoesProjeto`) a partir do
texto digitado — quem soma, multiplica ou converte unidade de projeto é
sempre o núcleo.
"""
from __future__ import annotations

import tkinter as tk
from collections import Counter
from dataclasses import replace
from tkinter import messagebox, ttk

from calc_core.modelos import ROTULO_ELU
from calc_core.sapata_isolada.acoes import CasoCarga, Esforcos, Pilar
from calc_core.sapata_isolada.geotecnia import (
    Camada,
    PerfilGeotecnico,
    Solo,
    TipoSubstrato,
)
from calc_core.sapata_isolada.materiais import BITOLAS_COMERCIAIS, Aco, Concreto
from calc_core.sapata_isolada.sapata import (
    ArmaduraImposta,
    GeometriaImposta,
    OpcoesProjeto,
    ResultadoSapata,
)

from . import tema
from .dialogo_sigma_adm import AVISO_GAMMA_EFETIVO, DialogoSigmaAdm

AGREGADOS = ["basalto", "diabasio", "granito", "gnaisse", "calcario", "arenito"]
CATEGORIAS_FYK = ["250", "500", "600"]
TIPOS_SUBSTRATO = [t.value for t in TipoSubstrato]
BITOLAS_TXT = [f"{b:g}" for b in BITOLAS_COMERCIAIS]
MODELOS_REACAO = ["rigido", "elastico", "grelha", "envoltoria"]
MODELOS_ARMADURA = ["bielas", "flexao", "envoltoria"]

# REQ-UI-CAMADA-05, Exigência 1: quando `_remover_camada` esvazia
# `self._camadas` estando a proveniência válida, γ_solo troca de papel —
# deixa de ser o γ (sat/nat) de uma camada do perfil e passa a valer como
# peso do solo na sobrecarga efetiva de h_f (`gamma_solo * h_f`, sem
# perfil — `Solo.sobrecarga_no_nivel_da_base`). O aviso é passivo (rótulo,
# nunca `messagebox`) e reaproveita, PALAVRA POR PALAVRA, o texto de
# `AVISO_GAMMA_EFETIVO` já exigido por REQ-UI-SIGMA-04/pendência V7 — a
# mesma pendência V8 (kb/pendencias.md) torna este aviso obrigatório
# enquanto não houver decisão humana registrada.
AVISO_TRANSICAO_PERFIL_VAZIO = (
    "Perfil geotécnico ficou vazio: γ_solo deixa de vir de uma camada do "
    "perfil e passa a valer como sobrecarga na cota da base (γ_solo × "
    "h_f, sem perfil). " + AVISO_GAMMA_EFETIVO
)


def _float(valor: str, padrao: float = 0.0) -> float:
    valor = (valor or "").strip().replace(",", ".")
    return float(valor) if valor else padrao


def _float_opt(valor: str) -> float | None:
    valor = (valor or "").strip().replace(",", ".")
    return float(valor) if valor else None


def _int_opt(valor: str) -> int | None:
    valor = (valor or "").strip()
    return int(valor) if valor else None


def _texto_campo(valor: float | str | None) -> str:
    """Formata um valor de `Camada` (float, str ou None) como texto para
    pré-preencher um `StringVar` do diálogo de edição."""
    if valor is None:
        return ""
    if isinstance(valor, float):
        return f"{valor:g}"
    return str(valor)


class DialogoCamada(tk.Toplevel):
    """Coleta os parâmetros de uma camada do perfil geotécnico (`Camada`).

    `camada_inicial`, se fornecida, faz o diálogo abrir em modo EDIÇÃO: os
    campos vêm pré-preenchidos com os valores daquela camada (em vez dos
    defaults fixos de "nova camada"), o título/botão mudam para deixar isso
    explícito, e `_ok` usa `dataclasses.replace(camada_inicial, ...)` em vez
    de construir um `Camada(...)` do zero — os campos que este diálogo NÃO
    coleta (Es, nu, Cc, Cs, e0, OCR, cv, C_alpha, drenagem_dupla, k_spt_MPa)
    são preservados como estavam, em vez de voltarem em silêncio ao default
    do dataclass. Isso importa de verdade para uma camada coesiva que
    chegou com Cc/e0/cv/Es de uma importação de Excel/projeto — editar só a
    espessura, por exemplo, não pode apagar os parâmetros de adensamento
    dela."""

    def __init__(self, master: tk.Misc, camada_inicial: Camada | None = None
                 ) -> None:
        super().__init__(master)
        self._camada_inicial = camada_inicial
        self.title("Editar camada" if camada_inicial is not None
                    else "Nova camada do perfil")
        self.configure(bg=tema.FUNDO_PAINEL)
        self.resultado: Camada | None = None
        self.transient(master)
        self.grab_set()

        campos = [
            ("nome", "Nome", "Camada"),
            ("espessura", "Espessura [m]", "2.0"),
            ("gamma_nat", "γ natural [kN/m³]", "18"),
            ("gamma_sat", "γ saturado [kN/m³]", "20"),
            ("phi", "φ' [graus]", "28"),
            ("coesao", "c' [kPa]", "0"),
            ("nspt", "N_SPT médio (opcional)", ""),
        ]
        self._vars: dict[str, tk.StringVar] = {}
        linha = 0
        for chave, rotulo, padrao in campos:
            ttk.Label(self, text=rotulo, style="PainelFraco.TLabel").grid(
                row=linha, column=0, sticky="w", padx=8, pady=3)
            if camada_inicial is not None:
                valor_inicial = _texto_campo(getattr(camada_inicial, chave))
            else:
                valor_inicial = padrao
            var = tk.StringVar(value=valor_inicial)
            ttk.Entry(self, textvariable=var, width=16).grid(
                row=linha, column=1, sticky="w", padx=8, pady=3)
            self._vars[chave] = var
            linha += 1

        ttk.Label(self, text="Tipo de substrato", style="PainelFraco.TLabel").grid(
            row=linha, column=0, sticky="w", padx=8, pady=3)
        tipo_inicial = (camada_inicial.tipo.value if camada_inicial is not None
                        else TIPOS_SUBSTRATO[0])
        self.v_tipo = tk.StringVar(value=tipo_inicial)
        ttk.Combobox(self, textvariable=self.v_tipo, state="readonly", width=13,
                     values=TIPOS_SUBSTRATO).grid(row=linha, column=1, sticky="w",
                                                   padx=8, pady=3)
        linha += 1

        botoes = ttk.Frame(self)
        botoes.grid(row=linha, column=0, columnspan=2, pady=8)
        texto_confirmar = "Salvar" if camada_inicial is not None else "Adicionar"
        ttk.Button(botoes, text=texto_confirmar, style="Acento.TButton",
                   command=self._ok).pack(side="left", padx=4)
        ttk.Button(botoes, text="Cancelar", command=self.destroy).pack(
            side="left", padx=4)

    def _ok(self) -> None:
        try:
            campos_editados = {
                "nome": self._vars["nome"].get() or "Camada",
                "espessura": _float(self._vars["espessura"].get(), 1.0),
                "tipo": TipoSubstrato(self.v_tipo.get()),
                "gamma_nat": _float(self._vars["gamma_nat"].get(), 18.0),
                "gamma_sat": _float(self._vars["gamma_sat"].get(), 20.0),
                "phi": _float(self._vars["phi"].get(), 28.0),
                "coesao": _float(self._vars["coesao"].get(), 0.0),
                "nspt": _float_opt(self._vars["nspt"].get()),
            }
            if self._camada_inicial is not None:
                camada = replace(self._camada_inicial, **campos_editados)
            else:
                camada = Camada(**campos_editados)
        except ValueError as erro:
            messagebox.showerror("Camada inválida", str(erro), parent=self)
            return
        if camada.espessura <= 0:
            messagebox.showerror("Camada inválida", "Espessura deve ser > 0.",
                                  parent=self)
            return
        self.resultado = camada
        self.destroy()


class PainelEntrada(ttk.Frame):
    """Coluna esquerda: formulário derivado dos objetos de entrada do núcleo."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, style="Painel.TFrame")
        self._camadas: list[Camada] = []
        self._arm: dict[str, dict] = {}
        self._preenchendo_sigma_adm_calculado = False
        """Guarda interna de `_abrir_calculadora_sigma_adm`/
        `_ao_editar_sigma_adm` — ver docstrings dos dois."""
        self._preenchendo_solo_derivado = False
        """Guarda de escrita de `_derivar_solo_da_camada` — impede que os
        três `.set()` programáticos que ela faz em v_gamma_solo/v_phi_solo/
        v_coesao disparem `_ao_editar_solo_derivado` (que existe para
        invalidar a proveniência em qualquer OUTRA edição desses campos).
        Mesma arquitetura de `_preenchendo_sigma_adm_calculado` (REQ-UI-
        CAMADA-03)."""
        self._carregando_solo = False
        """Guarda de `preencher_solo` — suprime a DERIVAÇÃO disparada pelos
        traces de escrita de v_hf/v_nivel_agua enquanto um projeto/Excel
        está sendo carregado (REQ-UI-CAMADA-04). Assimetria proposital:
        NUNCA suprime a invalidação de `ultima_derivacao_de_camada` — os
        valores de arquivo não são derivados, então a invalidação (via
        `_ao_editar_solo_derivado`, disparada pelos `.set()` de v_gamma_
        solo/v_phi_solo/v_coesao dentro de `preencher_solo`) tem de correr
        normalmente."""
        self._montar_scroll()

    # ------------------------------------------------------------- estrutura
    def _montar_scroll(self) -> None:
        canvas = tk.Canvas(self, bg=tema.FUNDO_PAINEL, highlightthickness=0)
        barra = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.interior = ttk.Frame(canvas, style="Painel.TFrame")

        janela = canvas.create_window((0, 0), window=self.interior, anchor="nw")
        self.interior.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(janela, width=e.width))
        canvas.configure(yscrollcommand=barra.set)

        def _roda(evento):
            canvas.yview_scroll(-1 if evento.delta > 0 else 1, "units")

        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _roda))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        canvas.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")

        self._montar_secoes(self.interior)

    def _montar_secoes(self, pai: ttk.Frame) -> None:
        pai.columnconfigure(0, weight=1)
        construtores = (self._secao_pilar, self._secao_materiais,
                        self._secao_acoes, self._secao_solo,
                        self._secao_geometria, self._secao_armaduras,
                        self._secao_opcoes)
        for linha, construtor in enumerate(construtores):
            construtor(pai, linha)

    # ------------------------------------------------------------- utilidades
    def _campo(self, parent: ttk.Frame, row: int, rotulo: str, padrao: str = "",
               largura: int = 10) -> tk.StringVar:
        var, _ = self._campo_widget(parent, row, rotulo, padrao, largura)
        return var

    def _campo_widget(self, parent: ttk.Frame, row: int, rotulo: str,
                       padrao: str = "", largura: int = 10
                       ) -> tuple[tk.StringVar, ttk.Entry]:
        ttk.Label(parent, text=rotulo, style="PainelFraco.TLabel").grid(
            row=row, column=0, sticky="w", padx=(8, 4), pady=2)
        var = tk.StringVar(value=padrao)
        entrada = ttk.Entry(parent, textvariable=var, width=largura)
        entrada.grid(row=row, column=1, sticky="w", padx=(0, 8), pady=2)
        return var, entrada

    def _combo(self, parent: ttk.Frame, row: int, rotulo: str, valores, padrao: str,
               largura: int = 10) -> tk.StringVar:
        ttk.Label(parent, text=rotulo, style="PainelFraco.TLabel").grid(
            row=row, column=0, sticky="w", padx=(8, 4), pady=2)
        var = tk.StringVar(value=padrao)
        ttk.Combobox(parent, textvariable=var, state="readonly", width=largura - 2,
                     values=list(valores)).grid(row=row, column=1, sticky="w",
                                                 padx=(0, 8), pady=2)
        return var

    # ------------------------------------------------------------------ pilar
    def _secao_pilar(self, pai: ttk.Frame, row: int) -> None:
        f = ttk.LabelFrame(pai, text="Pilar")
        f.grid(row=row, column=0, sticky="ew", padx=8, pady=(8, 4))
        self.v_ap = self._campo(f, 0, "a_p — direção X [m]", "0.20")
        self.v_bp = self._campo(f, 1, "b_p — direção Y [m]", "0.50")
        self.v_phi_arranque = self._campo(f, 2, "Ø arranque [mm]", "16")

    # -------------------------------------------------------------- materiais
    def _secao_materiais(self, pai: ttk.Frame, row: int) -> None:
        f = ttk.LabelFrame(pai, text="Materiais")
        f.grid(row=row, column=0, sticky="ew", padx=8, pady=4)
        self.v_fck = self._campo(f, 0, "f_ck [MPa]", "30")
        self.v_fyk = self._combo(f, 1, "f_yk [MPa]", CATEGORIAS_FYK, "500")
        self.v_agregado = self._combo(f, 2, "Agregado graúdo", AGREGADOS, "granito")
        self.v_cobrimento = self._campo(f, 3, "Cobrimento [cm]", "4.5")

    # ------------------------------------------------------------------ ações
    def _grupo_esforcos(self, pai: ttk.Frame, row: int, prefixo: str) -> dict:
        vs = {}
        rotulos = (("N", "kN"), ("Mx", "kN·m"), ("My", "kN·m"),
                   ("Hx", "kN"), ("Hy", "kN"))
        for i, (chave, unid) in enumerate(rotulos):
            vs[chave] = self._campo(pai, row + i, f"{chave} [{unid}]", "0")
        return vs

    def _secao_acoes(self, pai: ttk.Frame, row: int) -> None:
        f = ttk.LabelFrame(pai, text="Ações (por caso de carga)")
        f.grid(row=row, column=0, sticky="ew", padx=8, pady=4)

        ttk.Label(f, text="Permanente (G) — sempre incluída",
                  style="Secao.TLabel").grid(row=0, column=0, columnspan=2,
                                              sticky="w", padx=8, pady=(4, 2))
        self.v_G = self._grupo_esforcos(f, 1, "G")
        self.v_G["N"].set("600")
        self.v_G["Mx"].set("15")
        self.v_G["My"].set("8")

        r = 6
        self.usar_q = tk.BooleanVar(value=True)
        ttk.Checkbutton(f, text="Acidental (Q)", variable=self.usar_q).grid(
            row=r, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 2))
        self.v_Q = self._grupo_esforcos(f, r + 1, "Q")
        self.v_Q["N"].set("180")
        self.v_Q["Mx"].set("6")

        r = r + 6
        self.usar_w = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text="Vento (W, reversível)", variable=self.usar_w).grid(
            row=r, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 2))
        self.v_W = self._grupo_esforcos(f, r + 1, "W")
        self.v_W["My"].set("45")
        self.v_W["Hx"].set("18")

    # -------------------------------------------------------------------- solo
    def _secao_solo(self, pai: ttk.Frame, row: int) -> None:
        f = ttk.LabelFrame(pai, text="Solo de apoio")
        f.grid(row=row, column=0, sticky="ew", padx=8, pady=4)
        self.v_sigma_adm = self._campo(f, 0, "σ_adm [kPa]", "250")
        # REQ-UI-SIGMA-01, metade "na tela principal" (a outra metade, no
        # memorial exportado, já existia — ver `_atualizar_rotulo_sigma_
        # adm_elu`): rótulo visível colado ao campo sempre que o valor ali
        # ainda vier de um cálculo desta calculadora, na condição EXATA
        # que já existe para `ultimo_sigma_adm_calculado` (D-02/MÉDIA #4
        # do GATE 2, rodada 3).
        self.lbl_sigma_adm_elu = ttk.Label(
            f, text="", style="PainelFraco.TLabel", foreground=tema.AMARELO,
            wraplength=250, justify="left")
        self.lbl_sigma_adm_elu.grid(row=0, column=3, sticky="w", padx=(4, 8),
                                     pady=2)
        # D-02 do GATE 2, rodada 3: `ultimo_sigma_adm_calculado` só pode
        # rotular o memorial (ROTULO_ELU/ROTULO_FONTE_NAO_NORMATIVA) se
        # `v_sigma_adm` ainda for EXATAMENTE o que o diálogo calculou — o
        # trace abaixo invalida (`None`) sempre que o texto do campo muda
        # por QUALQUER via, inclusive teclado, "Abrir projeto..." e
        # "Importar do Excel..." (`preencher_solo`, mais abaixo, só chama
        # `.set()`, sem tratamento especial: o trace cobre os dois casos
        # da MÉDIA #4 com o mesmo código). `_abrir_calculadora_sigma_adm`
        # é a ÚNICA chamada que deve sobreviver — ela liga
        # `_preenchendo_sigma_adm_calculado` antes do `.set()` e desliga
        # depois, e o próprio callback pula a invalidação enquanto essa
        # flag está ligada. O mesmo callback também atualiza
        # `lbl_sigma_adm_elu` — um único ponto para as duas metades do
        # requisito.
        self.v_sigma_adm.trace_add("write", self._ao_editar_sigma_adm)
        ttk.Button(f, text="Calcular σ_adm a partir de SPT...",
                   command=self._abrir_calculadora_sigma_adm).grid(
            row=0, column=2, sticky="w", padx=(0, 8), pady=2)
        self.v_hf = self._campo(f, 1, "Cota da base h_f [m]", "1.5")
        self.v_gamma_solo = self._campo(f, 2, "γ_solo [kN/m³]", "18")
        self.v_phi_solo = self._campo(f, 3, "φ' na base [graus]", "30")
        self.v_coesao = self._campo(f, 4, "c' na base [kPa]", "0")
        self.v_nivel_agua = self._campo(f, 5, "Nível d'água [m] (vazio = ausente)", "")

        # REQ-UI-CAMADA-01/03 (backlog #12): γ_solo/φ'/c' na base passam a
        # ser PREENCHIDOS a partir da camada vigente em h_f, em vez de
        # digitados de novo — mesma arquitetura de `ultimo_sigma_adm_
        # calculado`/`_ao_editar_sigma_adm`/`lbl_sigma_adm_elu` acima:
        # rótulo discreto que só `_atualizar_rotulo_solo_derivado()`
        # escreve, ligado à proveniência conjunta dos três campos.
        self.lbl_solo_derivado = ttk.Label(
            f, text="", style="PainelFraco.TLabel", foreground=tema.AMARELO,
            wraplength=250, justify="left")
        self.lbl_solo_derivado.grid(row=2, column=2, columnspan=2, rowspan=3,
                                     sticky="w", padx=(4, 8), pady=2)
        # GATILHOS, lista FECHADA (REQ-UI-CAMADA-01): as duas cotas que
        # decidem qual camada vale disparam a derivação...
        self.v_hf.trace_add("write", self._derivar_solo_da_camada)
        self.v_nivel_agua.trace_add("write", self._derivar_solo_da_camada)
        # ...e a edição manual de QUALQUER um dos três campos derivados
        # invalida a proveniência dos TRÊS ao mesmo tempo (REQ-UI-CAMADA-03).
        # `_preenchendo_solo_derivado` (ligado só dentro de `_derivar_solo_
        # da_camada`) impede que os `.set()` da própria derivação se
        # autoinvalidem.
        self.v_gamma_solo.trace_add("write", self._ao_editar_solo_derivado)
        self.v_phi_solo.trace_add("write", self._ao_editar_solo_derivado)
        self.v_coesao.trace_add("write", self._ao_editar_solo_derivado)

        ttk.Label(f, text="σ_adm sempre admite sobreposição manual pelo "
                          "engenheiro (NBR 6122 §7.2) — inclusive depois de "
                          "\"Calcular σ_adm a partir de SPT...\": o botão só "
                          "PREENCHE este campo, nunca o trava.",
                  style="PainelFraco.TLabel",
                  wraplength=260, justify="left").grid(
            row=6, column=0, columnspan=2, sticky="w", padx=8, pady=(2, 6))

        cam = ttk.LabelFrame(f, text="Perfil em camadas (opcional — recalques)")
        cam.grid(row=7, column=0, columnspan=2, sticky="ew", padx=6, pady=(0, 6))
        cam.columnconfigure(0, weight=1)
        cols = ("nome", "espessura", "tipo")
        self.tree_camadas = ttk.Treeview(cam, columns=cols, show="headings",
                                          height=4)
        for c, rot, larg in zip(cols, ("Nome", "e [m]", "Tipo"), (90, 55, 78)):
            self.tree_camadas.heading(c, text=rot)
            self.tree_camadas.column(c, width=larg, anchor="w")
        self.tree_camadas.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 2))
        # Duplo-clique numa linha edita a camada daquela posição (padrão
        # usual de Treeview no Tk); o botão "editar" cobre o mesmo caminho
        # para quem prefere/precisa de mouse sem duplo-clique (acessibilidade
        # e descoberta — nem todo usuário tenta duplo-clique por conta
        # própria).
        self.tree_camadas.bind("<Double-1>", self._editar_camada)
        botoes = ttk.Frame(cam)
        botoes.grid(row=1, column=0, sticky="w", padx=6, pady=(0, 6))
        ttk.Button(botoes, text="+ camada", command=self._adicionar_camada).pack(
            side="left", padx=(0, 4))
        ttk.Button(botoes, text="editar", command=self._editar_camada).pack(
            side="left", padx=(0, 4))
        ttk.Button(botoes, text="- remover", command=self._remover_camada).pack(
            side="left")

        expansivo_colapsivel = ttk.Frame(f)
        expansivo_colapsivel.grid(row=8, column=0, columnspan=2, sticky="w",
                                   padx=8, pady=(2, 8))
        self.solo_expansivo = tk.BooleanVar(value=False)
        self.solo_colapsivel = tk.BooleanVar(value=False)
        ttk.Checkbutton(expansivo_colapsivel, text="Solo expansivo (§7.5.2)",
                        variable=self.solo_expansivo,
                        command=self._aviso_solo_especial).pack(anchor="w")
        ttk.Checkbutton(expansivo_colapsivel, text="Solo colapsível (§7.5.3)",
                        variable=self.solo_colapsivel,
                        command=self._aviso_solo_especial).pack(anchor="w")

    def _aviso_solo_especial(self) -> None:
        if self.solo_expansivo.get() or self.solo_colapsivel.get():
            messagebox.showwarning(
                "Solo especial — alerta bloqueante",
                "Solo expansivo ou colapsível foi marcado. A NBR 6122 §7.5.2/"
                "§7.5.3 exige tratamento específico de fundação (ex.: alívio de "
                "pressão, controle de umidade, radier ou estaca) — nenhum dos "
                "dois motores deste software dimensiona esse caso. Não use o "
                "resultado deste cálculo como fundação final.")

    def _abrir_calculadora_sigma_adm(self) -> None:
        """Abre `DialogoSigmaAdm` (teórico Terzaghi/Vesic + semiempírico SPT
        + majoração por vento, todos calc_core.geotecnico) e, se o
        engenheiro escolher um valor ("Usar este valor →"), PREENCHE
        `v_sigma_adm` com ele — nunca substitui o campo por um widget
        travado (NBR 6122 §7.2, mesma nota já fixa na tela). `ler_solo()`
        continua lendo só o texto de `v_sigma_adm`, exatamente como para
        qualquer valor digitado à mão: nenhuma conta acontece aqui, o
        diálogo já devolve o número pronto.

        `dialogo.resultado_info` guarda a proveniência (método, rótulos,
        avisos, regras/práticas, `valor_kPa`) em
        `self.ultimo_sigma_adm_calculado` — `ui.completo.app`/
        `ui.completo.resultado` a repassam para o memorial/Excel do escopo
        amplo (D-02 do GATE 2, rodada 3), que rotula a linha de σ_adm com
        `ROTULO_ELU`/`ROTULO_FONTE_NAO_NORMATIVA` enquanto ela continuar
        válida (ver `_ao_editar_sigma_adm`).

        `self._preenchendo_sigma_adm_calculado` liga ANTES do `.set()` e
        desliga logo depois: sem isto, o próprio `.set()` desta linha
        dispararia o trace `_ao_editar_sigma_adm` (que existe para
        invalidar `ultimo_sigma_adm_calculado` em qualquer OUTRA edição de
        `v_sigma_adm`) e apagaria a proveniência no mesmo instante em que
        ela é gravada."""
        dialogo = DialogoSigmaAdm(self)
        self.wait_window(dialogo)
        if dialogo.resultado_kPa is not None:
            self._preenchendo_sigma_adm_calculado = True
            try:
                self.v_sigma_adm.set(f"{dialogo.resultado_kPa:.10g}")
            finally:
                self._preenchendo_sigma_adm_calculado = False
            self.ultimo_sigma_adm_calculado = dialogo.resultado_info
            self._atualizar_rotulo_sigma_adm_elu()

    def _atualizar_rotulo_sigma_adm_elu(self) -> None:
        """Metade "na tela principal" de REQ-UI-SIGMA-01 — a outra metade
        (memorial exportado) já usava `ultimo_sigma_adm_calculado` desde
        D-02. Chamada pelos dois pontos que mudam esse atributo
        (`_abrir_calculadora_sigma_adm` quando preenche, `_ao_editar_
        sigma_adm` quando invalida) para que o rótulo `ROTULO_ELU` ao
        lado do campo `v_sigma_adm` nunca fique fora de sincronia com a
        proveniência que o memorial vai usar."""
        self.lbl_sigma_adm_elu.configure(
            text=ROTULO_ELU if self.ultimo_sigma_adm_calculado is not None
            else "")

    def _ao_editar_sigma_adm(self, *_args) -> None:
        """MÉDIA #4 do GATE 2, rodada 3: invalida a proveniência calculada
        assim que `v_sigma_adm` muda por qualquer via que não seja o
        próprio preenchimento feito por `_abrir_calculadora_sigma_adm`
        (edição manual pelo engenheiro NBR 6122 §7.2, "Abrir projeto...",
        "Importar do Excel..." — `preencher_solo`, mais abaixo, não
        precisa de tratamento especial: ela só chama `.set()`, e este
        trace já cobre qualquer `.set()` de fora). Sem isto, D-02
        rotularia como "calculado" (com `ROTULO_ELU`/
        `ROTULO_FONTE_NAO_NORMATIVA`) um valor que na verdade foi
        sobrescrito à mão por cima, ou que veio de um projeto carregado
        sem relação alguma com o cálculo anterior."""
        if getattr(self, "_preenchendo_sigma_adm_calculado", False):
            return
        self.ultimo_sigma_adm_calculado = None
        self._atualizar_rotulo_sigma_adm_elu()

    # --------------------------------------------------------------------
    # REQ-UI-CAMADA-01 a 07 (backlog #12) — camada única de dados:
    # γ_solo/φ'/c' na base derivados da camada vigente em h_f, em vez de
    # digitados de novo. Mesma arquitetura de `ultimo_sigma_adm_calculado`/
    # `_ao_editar_sigma_adm`/`_preenchendo_sigma_adm_calculado` acima —
    # reaproveitada, não reinventada (REQ-UI-CAMADA-03).
    # --------------------------------------------------------------------
    def _atualizar_rotulo_solo_derivado(self) -> None:
        """Único ponto que escreve `lbl_solo_derivado` — chamado tanto por
        `_derivar_solo_da_camada` (quando preenche) quanto por
        `_ao_editar_solo_derivado`/`_remover_camada` (quando invalida),
        para que o rótulo e `ultima_derivacao_de_camada` nunca saiam de
        sincronia (REQ-UI-CAMADA-03). Só dois estados possíveis: texto
        vazio (proveniência inválida) ou um texto que contém o radical
        "derivad", o nome exato da camada e o h_f usado — nunca mais do
        que isso (REQ-UI-CAMADA-05, Exigência 3: nada de "peso do maciço
        sobrejacente" ou equivalente)."""
        info = self.ultima_derivacao_de_camada
        if info is None:
            self.lbl_solo_derivado.configure(text="")
            return
        texto = (f'valores derivados da camada "{info["nome_camada"]}" em '
                 f'h_f = {info["hf"]:.10g} m')
        if info["abaixo_na"]:
            # REQ-UI-CAMADA-05, Exigência 2: dizer explicitamente que o γ
            # exibido é o SATURADO (total) da camada — nunca sugerir que o
            # software escolheu entre saturado/efetivo/natural por conta
            # própria.
            texto += (" — γ_solo exibido é o SATURADO (total) dessa "
                       "camada, por h_f estar abaixo do N.A.")
        if info["extrapolada"]:
            # REQ-UI-CAMADA-02: extrapolação abaixo do perfil nunca em
            # silêncio. `profundidade_total` é lido do núcleo (soma de
            # espessuras é conta do núcleo, não desta tela).
            perfil = PerfilGeotecnico(camadas=list(self._camadas))
            texto += (" — ATENÇÃO: h_f está ABAIXO da base do perfil "
                      f"cadastrado (profundidade total "
                      f"{perfil.profundidade_total:.10g} m); os três "
                      "campos foram preenchidos com a camada de fundo, "
                      "por extrapolação")
        self.lbl_solo_derivado.configure(text=texto)

    def _derivar_solo_da_camada(self, *_args) -> None:
        """ÚNICA derivação (REQ-UI-CAMADA-01). PREENCHE `v_gamma_solo`/
        `v_phi_solo`/`v_coesao` a partir de `PerfilGeotecnico.camada_em
        (h_f)`, NUNCA trava os campos (continuam `ttk.Entry` comuns,
        editáveis — NBR 6122 §7.2). Chamada pelos três editores de camada
        (`_adicionar_camada`/`_editar_camada`/`_remover_camada`, depois de
        `_atualizar_tree_camadas`) e pelos traces de escrita de `v_hf`/
        `v_nivel_agua` — nunca por `ler_solo`/`ler_perfil`/`preencher_solo`
        (REQ-UI-CAMADA-04/07: o guard `_carregando_solo` cobre o caso em
        que esses dois traces disparariam durante `preencher_solo`).

        GUARDAS DE RECUSA (REQ-UI-CAMADA-02), todas silenciosas — sem
        exceção, sem `messagebox`, sem tocar nos três campos: sem perfil;
        h_f em branco ou não numérico (os traces disparam a CADA tecla,
        "1", "1." e "1.e" são estados normais de digitação); N.A. não
        numérico (em branco é válido — N.A. ausente); h_f <= 0 (evita
        `camada_em` devolver a camada de FUNDO do perfil para uma cota
        negativa digitada por engano, ver geotecnia.py:121-122).

        Extrapolação (h_f além da base do perfil) DERIVA, mas nunca em
        silêncio — `ultima_derivacao_de_camada["extrapolada"]` fica `True`
        e `_atualizar_rotulo_solo_derivado` avisa em texto."""
        if self._carregando_solo:
            return
        if not self._camadas:
            return
        try:
            hf = _float_opt(self.v_hf.get())
        except ValueError:
            return
        if hf is None or hf <= 0:
            return
        try:
            nivel_agua = _float_opt(self.v_nivel_agua.get())
        except ValueError:
            return

        perfil = PerfilGeotecnico(camadas=list(self._camadas),
                                  nivel_agua=nivel_agua)
        camada = perfil.camada_em(hf)
        abaixo_na = nivel_agua is not None and hf > nivel_agua
        extrapolada = hf > perfil.profundidade_total

        self._preenchendo_solo_derivado = True
        try:
            self.v_gamma_solo.set(f"{camada.gamma(abaixo_na):.10g}")
            self.v_phi_solo.set(f"{camada.phi:.10g}")
            self.v_coesao.set(f"{camada.coesao:.10g}")
        finally:
            self._preenchendo_solo_derivado = False

        self.ultima_derivacao_de_camada = {
            "nome_camada": camada.nome,
            "hf": hf,
            "abaixo_na": abaixo_na,
            "gamma": camada.gamma(abaixo_na),
            "phi": camada.phi,
            "coesao": camada.coesao,
            "extrapolada": extrapolada,
        }
        self._atualizar_rotulo_solo_derivado()

    def _ao_editar_solo_derivado(self, *_args) -> None:
        """Trace de escrita de v_gamma_solo/v_phi_solo/v_coesao —
        invalida a proveniência dos TRÊS ao mesmo tempo assim que qualquer
        um deles muda por uma via que não seja o próprio preenchimento
        feito por `_derivar_solo_da_camada` (REQ-UI-CAMADA-03). Mesmo
        padrão de `_ao_editar_sigma_adm`: `_preenchendo_solo_derivado`
        (ligada só dentro da derivação) é a única exceção que sobrevive."""
        if getattr(self, "_preenchendo_solo_derivado", False):
            return
        self.ultima_derivacao_de_camada = None
        self._atualizar_rotulo_solo_derivado()

    def _adicionar_camada(self) -> None:
        dialogo = DialogoCamada(self)
        self.wait_window(dialogo)
        if dialogo.resultado is not None:
            self._camadas.append(dialogo.resultado)
            self._atualizar_tree_camadas()
            self._derivar_solo_da_camada()

    def _remover_camada(self) -> None:
        selecao = self.tree_camadas.selection()
        if not selecao:
            return
        indice = self.tree_camadas.index(selecao[0])
        del self._camadas[indice]
        self._atualizar_tree_camadas()
        if self._camadas:
            self._derivar_solo_da_camada()
        elif self.ultima_derivacao_de_camada is not None:
            # REQ-UI-CAMADA-05, Exigência 1: remoção esvaziou o perfil
            # estando a proveniência válida — γ_solo troca de papel. Aviso
            # passivo (nunca `messagebox`), e o NÚMERO em v_gamma_solo não
            # é tocado: quem decide é o engenheiro.
            self.ultima_derivacao_de_camada = None
            self.lbl_solo_derivado.configure(text=AVISO_TRANSICAO_PERFIL_VAZIO)

    def _editar_camada(self, evento: tk.Event | None = None) -> None:
        """Abre `DialogoCamada` preenchido com a `Camada` da linha
        selecionada (duplo-clique na `tree_camadas`, ou botão "editar") e,
        se confirmado, SUBSTITUI a camada naquela POSIÇÃO da lista — nunca
        acrescenta uma nova no fim, porque a ordem topo-para-base de
        `self._camadas` é significativa (`PerfilGeotecnico.camadas` é lida
        nessa ordem). Sem seleção (duplo-clique fora de qualquer linha, ou
        botão com a tree vazia), não faz nada — mesmo guard clause de
        `_remover_camada`. Cancelar o diálogo (`dialogo.resultado is None`)
        também não faz nada: a camada original permanece intacta."""
        selecao = self.tree_camadas.selection()
        if not selecao:
            return
        indice = self.tree_camadas.index(selecao[0])
        dialogo = DialogoCamada(self, camada_inicial=self._camadas[indice])
        self.wait_window(dialogo)
        if dialogo.resultado is not None:
            self._camadas[indice] = dialogo.resultado
            self._atualizar_tree_camadas()
            self._derivar_solo_da_camada()

    def _atualizar_tree_camadas(self) -> None:
        self.tree_camadas.delete(*self.tree_camadas.get_children())
        for c in self._camadas:
            self.tree_camadas.insert(
                "", "end", values=(c.nome, f"{c.espessura:.2f}", c.tipo.value))

    # -------------------------------------------------------------- geometria
    def _secao_geometria(self, pai: ttk.Frame, row: int) -> None:
        f = ttk.LabelFrame(pai, text="Geometria da sapata")
        f.grid(row=row, column=0, sticky="ew", padx=8, pady=4)
        self.modo_verificacao = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text="Definir eu mesmo (modo verificação)",
                        variable=self.modo_verificacao,
                        command=self._alternar_geometria).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(6, 2))

        self.v_geo_a, e_a = self._campo_widget(f, 1, "a — direção X [m]", "")
        self.v_geo_b, e_b = self._campo_widget(f, 2, "b — direção Y [m]", "")
        self.v_geo_h, e_h = self._campo_widget(f, 3, "h — altura total [m]", "")
        self.v_geo_h0, e_h0 = self._campo_widget(
            f, 4, "h0 — altura da aba [m] (vazio = auto)", "")
        self._entradas_geometria = (e_a, e_b, e_h, e_h0)

        self.btn_copiar_geometria = ttk.Button(
            f, text="Copiar do cálculo automático",
            command=self._on_copiar_geometria)
        self.btn_copiar_geometria.grid(row=5, column=0, columnspan=2, padx=8,
                                        pady=(2, 8), sticky="ew")
        self._alternar_geometria()

    def _alternar_geometria(self) -> None:
        """Os campos a/b/h/h0 só valem quando o modo verificação está ativo —
        desabilitá-los no modo automático deixa isso visível na hora."""
        estado = "normal" if self.modo_verificacao.get() else "disabled"
        for entrada in self._entradas_geometria:
            entrada.configure(state=estado)

    def _on_copiar_geometria(self) -> None:
        if self._ultimo_automatico is None:
            messagebox.showinfo(
                "Sem resultado automático",
                "Rode primeiro um dimensionamento automático (checkbox de "
                "geometria desmarcado) para ter o que copiar.")
            return
        self.preencher_geometria_automatica(self._ultimo_automatico)

    # -------------------------------------------------------------- armaduras
    def _secao_direcao_armadura(self, pai: ttk.Frame, coluna: int,
                                 direcao: str) -> None:
        f = ttk.LabelFrame(pai, text=f"Direção {direcao}")
        f.grid(row=0, column=coluna, sticky="new", padx=4, pady=2)
        impor = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text="Impor arranjo", variable=impor).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=6, pady=(4, 2))
        phi = self._combo(f, 1, "Ø [mm]", BITOLAS_TXT, "12.5", largura=8)
        n = self._campo(f, 2, "Nº de barras", "", largura=6)
        esp = self._campo(f, 3, "Espaçamento [m]", "", largura=6)
        botao = ttk.Button(f, text="Copiar do automático",
                           command=lambda d=direcao: self._on_copiar_armadura(d))
        botao.grid(row=4, column=0, columnspan=2, padx=6, pady=(2, 6), sticky="ew")
        self._arm[direcao] = {"impor": impor, "phi": phi, "n": n,
                              "espacamento": esp}

    def _secao_armaduras(self, pai: ttk.Frame, row: int) -> None:
        f = ttk.LabelFrame(pai, text="Arranjo de armaduras")
        f.grid(row=row, column=0, sticky="ew", padx=8, pady=4)
        f.columnconfigure(0, weight=1)
        interno = ttk.Frame(f)
        interno.grid(row=0, column=0, sticky="ew")
        interno.columnconfigure(0, weight=1)
        interno.columnconfigure(1, weight=1)
        self._secao_direcao_armadura(interno, 0, "X")
        self._secao_direcao_armadura(interno, 1, "Y")

    def _on_copiar_armadura(self, direcao: str) -> None:
        if self._ultimo_automatico is None:
            messagebox.showinfo(
                "Sem resultado automático",
                "Rode primeiro um dimensionamento automático para ter o que "
                "copiar.")
            return
        self.preencher_armadura_automatica(self._ultimo_automatico, direcao)

    # ---------------------------------------------------------------- opções
    def _secao_opcoes(self, pai: ttk.Frame, row: int) -> None:
        f = ttk.LabelFrame(pai, text="Opções do modelo (avançado)")
        f.grid(row=row, column=0, sticky="ew", padx=8, pady=(4, 12))
        self.v_modelo_reacao = self._combo(f, 0, "Reação do solo", MODELOS_REACAO,
                                           "rigido")
        self.v_modelo_armadura = self._combo(f, 1, "Armadura (sapata rígida)",
                                             MODELOS_ARMADURA, "bielas")

    # ------------------------------------------------------------------------
    # Estado do último dimensionamento automático (para os botões "Copiar")
    # ------------------------------------------------------------------------
    _ultimo_automatico: ResultadoSapata | None = None

    ultimo_sigma_adm_calculado: dict | None = None
    """Proveniência (método, rótulos, avisos, regras/práticas, `valor_kPa`)
    do último σ_adm preenchido por `_abrir_calculadora_sigma_adm` — `None`
    sempre que `v_sigma_adm` mudou por qualquer outra via desde então
    (`_ao_editar_sigma_adm`). `ui.completo.app` repassa isto para o
    memorial/Excel do escopo amplo (D-02 do GATE 2, rodada 3): só quando
    este atributo é `not None` a linha de σ_adm do memorial ganha
    `ROTULO_ELU`/`ROTULO_FONTE_NAO_NORMATIVA`."""

    ultima_derivacao_de_camada: dict | None = None
    """Proveniência (REQ-UI-CAMADA-01/03, backlog #12) do último
    preenchimento de v_gamma_solo/v_phi_solo/v_coesao por
    `_derivar_solo_da_camada` — `None` sempre que qualquer um dos três
    mudou por qualquer outra via desde então (`_ao_editar_solo_derivado`),
    ou o perfil ficou vazio (`_remover_camada`), ou um projeto/Excel foi
    carregado (`preencher_solo`, REQ-UI-CAMADA-04). Chaves: `nome_camada`,
    `hf`, `abaixo_na`, `gamma`, `phi`, `coesao`, `extrapolada`. Auxílio de
    preenchimento de campo — NÃO é repassado a `ler_solo()` nem ao
    memorial/PDF/Excel (REQ-UI-CAMADA-07): o núcleo só vê o número final."""

    def registrar_resultado_automatico(self, res: ResultadoSapata) -> None:
        self._ultimo_automatico = res

    def preencher_geometria_automatica(self, res: ResultadoSapata) -> None:
        self.v_geo_a.set(f"{res.a:.3f}")
        self.v_geo_b.set(f"{res.b:.3f}")
        self.v_geo_h.set(f"{res.h:.3f}")
        self.v_geo_h0.set(f"{res.h0:.3f}")

    def preencher_armadura_automatica(self, res: ResultadoSapata, direcao: str) -> None:
        ar = next((a for a in res.armaduras if a.direcao == direcao), None)
        if ar is None:
            return
        w = self._arm[direcao]
        w["phi"].set(f"{ar.phi_mm:.10g}")
        w["n"].set(str(ar.n_barras))
        w["espacamento"].set("")

    # ------------------------------------------------------------------------
    # "Preencher" — caminho inverso de "ler_*": mostra nos campos visíveis um
    # objeto vindo de fora (projeto salvo em .s7proj ou planilha Excel
    # importada). Usado por "Abrir projeto..." e "Importar do Excel..." em
    # `ui/completo/app.py`. Reaproveita os mesmos widgets/estruturas de dados
    # de `ler_*` — nenhum sistema de widgets paralelo.
    # ------------------------------------------------------------------------
    def preencher_pilar(self, pilar: Pilar) -> None:
        self.v_ap.set(f"{pilar.ap:.10g}")
        self.v_bp.set(f"{pilar.bp:.10g}")
        self.v_phi_arranque.set(f"{pilar.phi_arranque_mm:.10g}")

    def preencher_materiais(self, concreto: Concreto, aco: Aco,
                            cobrimento: float) -> None:
        """`cobrimento` é esperado em METROS — mesma unidade que
        `ler_materiais` devolve (o campo na tela é em cm; a conversão de
        volta espelha a que `ler_materiais` já faz ao ler)."""
        self.v_fck.set(f"{concreto.fck:.10g}")
        self.v_fyk.set(f"{aco.fyk:.10g}")
        self.v_agregado.set(concreto.agregado)
        self.v_cobrimento.set(f"{cobrimento*100:.10g}")

    def preencher_solo(self, solo: Solo) -> None:
        """`self.v_sigma_adm.set(...)` abaixo dispara
        `_ao_editar_sigma_adm` (trace de escrita registrado em
        `_secao_solo`) e zera `ultimo_sigma_adm_calculado` — MÉDIA #4 do
        GATE 2, rodada 3: um projeto carregado (.s7proj ou Excel) nunca
        tem relação com um cálculo de σ_adm feito ANTES de abri-lo, então
        o memorial não pode seguir rotulando o valor antigo como
        "calculado" depois desta chamada.

        REQ-UI-CAMADA-04 (backlog #12): γ_solo/φ'/c' vindos de `solo` são
        valores EXPLÍCITOS de arquivo (possivelmente sobrescritos à mão
        pelo engenheiro antes de salvar, NBR 6122 §7.2) — nunca
        reinterpretados como derivados da estratigrafia, mesmo que `solo`
        traga um `perfil`. `self._carregando_solo` (ligada em TODO o corpo
        desta função, `try/finally`) suprime a derivação que os traces de
        `v_hf`/`v_nivel_agua` disparariam abaixo — sem o guard, a escrita
        de `v_hf` na linha seguinte derivaria da estratigrafia ANTERIOR
        (`self._camadas` só é substituída mais abaixo). A invalidação de
        `ultima_derivacao_de_camada` (via `_ao_editar_solo_derivado`,
        disparada pelos `.set()` de v_gamma_solo/v_phi_solo/v_coesao logo
        abaixo) NÃO é suprimida — é o resultado correto: valores de
        arquivo não são derivados."""
        self._carregando_solo = True
        try:
            self.v_sigma_adm.set(f"{solo.sigma_adm:.10g}")
            self.v_hf.set(f"{solo.hf:.10g}")
            self.v_gamma_solo.set(f"{solo.gamma_solo:.10g}")
            self.v_phi_solo.set(f"{solo.phi:.10g}")
            self.v_coesao.set(f"{solo.coesao:.10g}")

            perfil = solo.perfil
            self._camadas = list(perfil.camadas) if perfil is not None else []
            self._atualizar_tree_camadas()
            nivel_agua = perfil.nivel_agua if perfil is not None else None
            self.v_nivel_agua.set(
                f"{nivel_agua:.10g}" if nivel_agua is not None else "")
        finally:
            self._carregando_solo = False
        # Estado terminal explícito (REQ-UI-CAMADA-04): mesmo que os
        # `.set()` acima já tenham invalidado a proveniência via trace,
        # este par deixa o desfecho garantido e nomeado, o mesmo que
        # `_ao_editar_sigma_adm` já produz para σ_adm nesta função.
        self.ultima_derivacao_de_camada = None
        self._atualizar_rotulo_solo_derivado()

    def preencher_casos(self, casos: list[CasoCarga]) -> None:
        """Repõe os grupos G/Q/W a partir de uma lista de casos carregada,
        casando pelo NOME — os mesmos "G"/"Q"/"W" que `ler_casos` sempre usa.
        Um caso "Q"/"W" ausente na lista desmarca o checkbox correspondente
        (o projeto carregado não tinha aquele caso ativo).

        A tela só tem os três slots fixos G/Q/W (`ler_casos` nunca produz
        outro nome). Um `CasoCarga` com QUALQUER outro nome não tem onde
        entrar — levantar `ValueError` aqui, ANTES de mexer em qualquer
        widget, é a alternativa a descartá-lo em silêncio (o defeito
        corrigido depois da verificação independente de 2026-08-28: a
        versão anterior desta função ignorava nomes fora de G/Q/W sem
        aviso, e quem chamava (`ui/completo/app.py::_abrir_projeto`,
        `_importar_excel`) reportava sucesso mesmo assim).

        O mesmo guard clause recusa nomes REPETIDOS (defeito D2 do GATE 2,
        rodada 1): a tela tem UM slot por nome, então `por_nome = {c.nome:
        c for c in casos}`, mais abaixo, colapsaria duplicatas em silêncio
        — o último caso "G" da lista venceria e as parcelas anteriores
        (ex.: peso próprio numa linha, sobrecarga permanente noutra)
        somem sem erro, subestimando a carga permanente exibida na tela.
        Se a origem dos dados tem duas linhas "G", a soma tem de ser feita
        ANTES de chegar aqui (na planilha, ou somando os `Esforcos` no
        `.s7proj`) — nunca dentro da UI (regra "ui/ não calcula")."""
        NOMES_ACEITOS = ("G", "Q", "W")
        desconhecidos = [c.nome for c in casos if c.nome not in NOMES_ACEITOS]
        if desconhecidos:
            raise ValueError(
                "Caso(s) de carga com nome não reconhecido pelo formulário: "
                f"{desconhecidos!r}. Esta tela só tem campos fixos para os "
                f"nomes {NOMES_ACEITOS!r} (G é sempre obrigatório; Q e W são "
                "opcionais). Renomeie o(s) caso(s) para um desses três nomes "
                "(exatamente, maiúsculas) na origem dos dados (planilha "
                "Excel ou arquivo .s7proj) antes de importar/abrir — nenhum "
                "caso foi preenchido nesta tentativa, para não misturar "
                "dados antigos e novos.")

        repetidos = sorted(nome for nome, qtd in Counter(c.nome for c in casos).items()
                           if qtd > 1)
        if repetidos:
            raise ValueError(
                f"Caso(s) de carga com nome repetido: {repetidos!r}. Esta "
                "tela tem UM slot por nome (G/Q/W) — se a origem dos dados "
                "traz mais de uma linha/entrada com o mesmo nome (ex.: "
                "duas linhas 'G' para peso próprio e sobrecarga "
                "permanente), some as parcelas ANTES de importar/abrir "
                "(na planilha, ou somando N/Mx/My/Hx/Hy no arquivo "
                ".s7proj); preencher um dos dois em silêncio descartaria a "
                "carga do outro sem aviso — nenhum caso foi preenchido "
                "nesta tentativa, para não misturar dados antigos e "
                "novos.")

        def preencher_grupo(vs: dict, esforcos: Esforcos) -> None:
            vs["N"].set(f"{esforcos.N:.10g}")
            vs["Mx"].set(f"{esforcos.Mx:.10g}")
            vs["My"].set(f"{esforcos.My:.10g}")
            vs["Hx"].set(f"{esforcos.Hx:.10g}")
            vs["Hy"].set(f"{esforcos.Hy:.10g}")

        por_nome = {c.nome: c for c in casos}

        if "G" in por_nome:
            preencher_grupo(self.v_G, por_nome["G"].esforcos)
        if "Q" in por_nome:
            self.usar_q.set(True)
            preencher_grupo(self.v_Q, por_nome["Q"].esforcos)
        else:
            self.usar_q.set(False)
        if "W" in por_nome:
            self.usar_w.set(True)
            preencher_grupo(self.v_W, por_nome["W"].esforcos)
        else:
            self.usar_w.set(False)

    def preencher_opcoes(self, opcoes: OpcoesProjeto) -> None:
        self.v_modelo_reacao.set(opcoes.modelo_reacao)
        self.v_modelo_armadura.set(opcoes.modelo_armadura_rigida)

        imposta = opcoes.geometria_imposta
        self.modo_verificacao.set(imposta is not None)
        if imposta is not None:
            self.v_geo_a.set(f"{imposta.a:.10g}")
            self.v_geo_b.set(f"{imposta.b:.10g}")
            self.v_geo_h.set(f"{imposta.h:.10g}")
            self.v_geo_h0.set(f"{imposta.h0:.10g}" if imposta.h0 is not None else "")
        else:
            self.v_geo_a.set("")
            self.v_geo_b.set("")
            self.v_geo_h.set("")
            self.v_geo_h0.set("")
        self._alternar_geometria()

        for direcao, w in self._arm.items():
            arm = opcoes.armaduras_impostas.get(direcao)
            w["impor"].set(arm is not None)
            if arm is not None:
                w["phi"].set(f"{arm.phi_mm:.10g}")
                w["n"].set(str(arm.n_barras) if arm.n_barras is not None else "")
                w["espacamento"].set(
                    f"{arm.espacamento:.10g}" if arm.espacamento is not None else "")
            else:
                w["phi"].set("12.5")
                w["n"].set("")
                w["espacamento"].set("")

    # ------------------------------------------------------------------ leitura
    def ler_pilar(self) -> Pilar:
        return Pilar(ap=_float(self.v_ap.get(), 0.20), bp=_float(self.v_bp.get(), 0.50),
                     phi_arranque_mm=_float(self.v_phi_arranque.get(), 16.0))

    def ler_materiais(self) -> tuple[Concreto, Aco, float]:
        concreto = Concreto(fck=_float(self.v_fck.get(), 25.0),
                            agregado=self.v_agregado.get())
        aco = Aco(fyk=_float(self.v_fyk.get(), 500.0))
        cobrimento = _float(self.v_cobrimento.get(), 4.5) / 100.0
        return concreto, aco, cobrimento

    def ler_perfil(self) -> PerfilGeotecnico | None:
        if not self._camadas:
            return None
        return PerfilGeotecnico(camadas=list(self._camadas),
                                nivel_agua=_float_opt(self.v_nivel_agua.get()))

    def ler_solo(self) -> Solo:
        return Solo(sigma_adm=_float(self.v_sigma_adm.get(), 250.0),
                    gamma_solo=_float(self.v_gamma_solo.get(), 18.0),
                    hf=_float(self.v_hf.get(), 1.5),
                    phi=_float(self.v_phi_solo.get(), 30.0),
                    coesao=_float(self.v_coesao.get(), 0.0),
                    perfil=self.ler_perfil())

    def solo_marcado_especial(self) -> bool:
        return bool(self.solo_expansivo.get() or self.solo_colapsivel.get())

    def ler_casos(self) -> list[CasoCarga]:
        def esf(vs: dict) -> Esforcos:
            return Esforcos(N=_float(vs["N"].get()), Mx=_float(vs["Mx"].get()),
                            My=_float(vs["My"].get()), Hx=_float(vs["Hx"].get()),
                            Hy=_float(vs["Hy"].get()))

        casos = [CasoCarga("G", esf(self.v_G))]
        if self.usar_q.get():
            casos.append(CasoCarga.acidental("Q", esf(self.v_Q)))
        if self.usar_w.get():
            casos.append(CasoCarga.vento("W", esf(self.v_W)))
        return casos

    def ler_opcoes(self) -> OpcoesProjeto:
        kwargs: dict = {
            "modelo_reacao": self.v_modelo_reacao.get(),
            "modelo_armadura_rigida": self.v_modelo_armadura.get(),
        }
        if self.modo_verificacao.get():
            kwargs["geometria_imposta"] = GeometriaImposta(
                a=_float(self.v_geo_a.get()), b=_float(self.v_geo_b.get()),
                h=_float(self.v_geo_h.get()), h0=_float_opt(self.v_geo_h0.get()))

        impostas = {}
        for direcao, w in self._arm.items():
            if w["impor"].get():
                impostas[direcao] = ArmaduraImposta(
                    phi_mm=_float(w["phi"].get(), 12.5),
                    n_barras=_int_opt(w["n"].get()),
                    espacamento=_float_opt(w["espacamento"].get()))
        kwargs["armaduras_impostas"] = impostas
        return OpcoesProjeto(**kwargs)
