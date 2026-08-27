"""
resultado.py
------------
Coluna direita: o semáforo de verificações, os quadros-resumo e o memorial.

Nada aqui soma, multiplica ou compara com um limite normativo: cada método
`_pior_*` só faz `max`/`min` de Python sobre listas que `ResultadoSapata` já
trouxe prontas, para mostrar o caso mais desfavorável — a mesma técnica que
`relatorio.memorial` usa para ordenar as tabelas do memorial em texto.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from calc_core.sapata_isolada.relatorio import memorial
from calc_core.sapata_isolada.sapata import ResultadoSapata, Sapata

from . import tema

ITEM_TENSOES = "NBR 6122:2019 §7.1/§7.6.1 — tensão admissível na base"
ITEM_ESTABILIDADE = "NBR 6122:2019 §6.2.1.2 — deslizamento e tombamento"
ITEM_PUNCAO = ("NBR 6118:2023 §19.5.3.1 (C) · §19.5.3.2 (C') · "
               "§19.4.1 (cisalhamento como laje)")
ITEM_ARMADURAS = ("NBR 6118:2023 §17.2.2 (flexão) · §19.3.3.2 (A_s,mín) · "
                   "§9.4.2.4 (ancoragem) · §22.6.3 (bielas, sapata rígida)")
ITEM_RECALQUES = "NBR 6122:2019 §6.2/§7 — deslocamentos e sua verificação"


def _status(ok: bool) -> str:
    return "OK" if ok else "NÃO OK"


def _pior_tensao(res: ResultadoSapata):
    if not res.tensoes:
        return None
    return max(res.tensoes, key=lambda t: t.sigma_max / max(t.limite, 1e-9))


def _pior_estabilidade(res: ResultadoSapata):
    if not res.estabilidade:
        return None
    return min(res.estabilidade,
               key=lambda e: min(e.fs_deslizamento, e.fs_tombamento_x,
                                  e.fs_tombamento_y))


def _pior_puncao(res: ResultadoSapata):
    if not res.puncao:
        return None
    return max(res.puncao, key=lambda p: p.aproveitamento)


class _Tile(ttk.Frame):
    """Um dos seis cartões de resumo do cabeçalho."""

    def __init__(self, master: tk.Misc, titulo: str) -> None:
        super().__init__(master, style="Tile.TFrame", padding=(10, 8))
        ttk.Label(self, text=titulo, style="Tile.TLabel",
                  font=tema.FONTE_SECAO).pack(anchor="w")
        self.valor = ttk.Label(self, text="—", style="Tile.TLabel",
                               font=("Consolas", 11, "bold"))
        self.valor.pack(anchor="w", pady=(4, 0))
        self.detalhe = ttk.Label(self, text="", style="Tile.TLabel",
                                 font=("Segoe UI", 8), wraplength=170,
                                 justify="left")
        self.detalhe.pack(anchor="w", pady=(2, 0))

    def definir(self, valor: str, detalhe: str, ok: bool | None) -> None:
        self.valor.configure(text=valor)
        self.detalhe.configure(text=detalhe)
        cor = tema.TEXTO_FRACO if ok is None else tema.cor_status(ok)
        self.valor.configure(foreground=cor)


def _tabela(pai: ttk.Frame, colunas: tuple[str, ...],
            larguras: tuple[int, ...]) -> ttk.Treeview:
    arv = ttk.Treeview(pai, columns=colunas, show="headings", height=8)
    for c, rot, larg in zip(colunas, colunas, larguras):
        arv.heading(c, text=rot)
        arv.column(c, width=larg, anchor="center")
    barra = ttk.Scrollbar(pai, orient="vertical", command=arv.yview)
    arv.configure(yscrollcommand=barra.set)
    arv.pack(side="left", fill="both", expand=True)
    barra.pack(side="right", fill="y")
    return arv


class PainelResultado(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, style="Painel.TFrame")
        self._montar()

    # ------------------------------------------------------------------ ui
    def _montar(self) -> None:
        cab = ttk.Frame(self, style="Painel.TFrame")
        cab.pack(fill="x", padx=8, pady=8)
        self.selo = ttk.Label(cab, text="—", style="StatusErro.TLabel",
                              anchor="center")
        self.selo.pack(fill="x")
        self.dims = ttk.Label(cab, text="—", style="Painel.TLabel",
                              font=("Consolas", 13, "bold"))
        self.dims.pack(anchor="w", pady=(6, 0))
        self.governante = ttk.Label(cab, text="—", style="PainelFraco.TLabel",
                                    wraplength=320, justify="left")
        self.governante.pack(anchor="w")

        tiles = ttk.Frame(self, style="Painel.TFrame")
        tiles.pack(fill="x", padx=6, pady=(0, 6))
        for i in range(3):
            tiles.columnconfigure(i, weight=1)
        titulos = ["Tensão no solo", "Estabilidade", "Punção/cisalhamento",
                   "Rigidez", "Flexão", "Recalque"]
        self.tiles: dict[str, _Tile] = {}
        for i, titulo in enumerate(titulos):
            t = _Tile(tiles, titulo)
            t.grid(row=i // 3, column=i % 3, sticky="nsew", padx=3, pady=3)
            self.tiles[titulo] = t

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=(4, 4))
        self._montar_aba_verificacoes(notebook)
        self._montar_aba_armaduras(notebook)
        self._montar_aba_recalques(notebook)
        self._montar_aba_memorial(notebook)

        alertas_frame = ttk.LabelFrame(self, text="Alertas")
        alertas_frame.pack(fill="x", padx=8, pady=(0, 8))
        self.texto_alertas = tk.Text(alertas_frame, height=5, wrap="word",
                                     bg=tema.FUNDO_CAMPO, fg=tema.AMARELO,
                                     insertbackground=tema.TEXTO, relief="flat",
                                     font=("Segoe UI", 8), state="disabled")
        self.texto_alertas.pack(fill="x", padx=4, pady=4)

    def _montar_aba_verificacoes(self, notebook: ttk.Notebook) -> None:
        aba = ttk.Frame(notebook, style="Painel.TFrame")
        notebook.add(aba, text="Verificações")
        sub = ttk.Notebook(aba)
        sub.pack(fill="both", expand=True)

        f1 = ttk.Frame(sub, style="Painel.TFrame")
        sub.add(f1, text="Tensões")
        ttk.Label(f1, text=ITEM_TENSOES, style="PainelFraco.TLabel",
                  font=("Segoe UI", 8)).pack(anchor="w", padx=4, pady=(4, 0))
        self.tab_tensoes = _tabela(
            f1, ("Combinação", "σ máx [kPa]", "σ mín [kPa]", "limite [kPa]",
                 "status"), (140, 80, 80, 80, 60))

        f2 = ttk.Frame(sub, style="Painel.TFrame")
        sub.add(f2, text="Estabilidade")
        ttk.Label(f2, text=ITEM_ESTABILIDADE, style="PainelFraco.TLabel",
                  font=("Segoe UI", 8)).pack(anchor="w", padx=4, pady=(4, 0))
        self.tab_estabilidade = _tabela(
            f2, ("Combinação", "FS desliz.", "FS tomb.X", "FS tomb.Y", "status"),
            (150, 80, 80, 80, 60))

        f3 = ttk.Frame(sub, style="Painel.TFrame")
        sub.add(f3, text="Punção/Cisalhamento")
        ttk.Label(f3, text=ITEM_PUNCAO, style="PainelFraco.TLabel",
                  font=("Segoe UI", 8), wraplength=420).pack(anchor="w", padx=4,
                                                              pady=(4, 0))
        self.tab_puncao = _tabela(
            f3, ("Combinação", "Contorno", "Sd", "Rd", "Sd/Rd", "status"),
            (100, 190, 60, 60, 60, 60))

    def _montar_aba_armaduras(self, notebook: ttk.Notebook) -> None:
        aba = ttk.Frame(notebook, style="Painel.TFrame")
        notebook.add(aba, text="Armaduras")
        ttk.Label(aba, text=ITEM_ARMADURAS, style="PainelFraco.TLabel",
                  font=("Segoe UI", 8), wraplength=420).pack(anchor="w", padx=6,
                                                              pady=(6, 4))
        self.frame_armaduras = ttk.Frame(aba, style="Painel.TFrame")
        self.frame_armaduras.pack(fill="both", expand=True, padx=4, pady=4)

    def _montar_aba_recalques(self, notebook: ttk.Notebook) -> None:
        aba = ttk.Frame(notebook, style="Painel.TFrame")
        notebook.add(aba, text="Recalques")
        ttk.Label(aba, text=ITEM_RECALQUES, style="PainelFraco.TLabel",
                  font=("Segoe UI", 8)).pack(anchor="w", padx=6, pady=(6, 4))
        self.frame_recalques = ttk.Frame(aba, style="Painel.TFrame")
        self.frame_recalques.pack(fill="both", expand=True, padx=4, pady=4)

    def _montar_aba_memorial(self, notebook: ttk.Notebook) -> None:
        aba = ttk.Frame(notebook, style="Painel.TFrame")
        notebook.add(aba, text="Memorial")
        self.texto_memorial = tk.Text(aba, wrap="none", bg=tema.FUNDO_CAMPO,
                                      fg=tema.TEXTO, insertbackground=tema.TEXTO,
                                      relief="flat", font=tema.FONTE_MONO,
                                      state="disabled")
        vbar = ttk.Scrollbar(aba, orient="vertical",
                             command=self.texto_memorial.yview)
        hbar = ttk.Scrollbar(aba, orient="horizontal",
                             command=self.texto_memorial.xview)
        self.texto_memorial.configure(yscrollcommand=vbar.set,
                                      xscrollcommand=hbar.set)
        self.texto_memorial.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")
        aba.rowconfigure(0, weight=1)
        aba.columnconfigure(0, weight=1)

    # -------------------------------------------------------------- atualizar
    def atualizar(self, sapata: Sapata, res: ResultadoSapata) -> None:
        self._atualizar_cabecalho(res)
        self._atualizar_tiles(res)
        self._atualizar_verificacoes(res)
        self._atualizar_armaduras(res)
        self._atualizar_recalques(res)
        self._atualizar_memorial(sapata, res)
        self._atualizar_alertas(res)

    def _atualizar_cabecalho(self, res: ResultadoSapata) -> None:
        if res.aprovado:
            self.selo.configure(text="APROVADA", style="StatusOk.TLabel")
        else:
            self.selo.configure(text="REPROVADA", style="StatusErro.TLabel")
        self.dims.configure(
            text=f"{res.a:.2f} × {res.b:.2f} × {res.h:.2f} m"
                 + (f"  (h0={res.h0:.2f})" if res.h0 != res.h else ""))
        pior = _pior_tensao(res)
        modo = "verificação (geometria imposta)" if res.modo_verificacao else "dimensionamento automático"
        if pior is not None:
            self.governante.configure(
                text=f"Modo: {modo}  ·  combinação governante (tensão): "
                     f"{pior.combinacao}")
        else:
            self.governante.configure(text=f"Modo: {modo}")

    def _atualizar_tiles(self, res: ResultadoSapata) -> None:
        pt = _pior_tensao(res)
        if pt is not None:
            self.tiles["Tensão no solo"].definir(
                f"{pt.sigma_max:.0f} / {pt.limite:.0f} kPa",
                pt.combinacao, pt.ok)
        pe = _pior_estabilidade(res)
        if pe is not None:
            fs_min = min(pe.fs_deslizamento, pe.fs_tombamento_x, pe.fs_tombamento_y)
            fs_txt = "∞" if fs_min == float("inf") else f"{fs_min:.2f}"
            self.tiles["Estabilidade"].definir(f"FS mín {fs_txt}", pe.combinacao,
                                               pe.ok)
        pp = _pior_puncao(res)
        if pp is not None:
            self.tiles["Punção/cisalhamento"].definir(
                f"{pp.tau_sd:.1f} / {pp.tau_rd:.1f}",
                f"{pp.contorno} (Sd/Rd={pp.aproveitamento:.2f})", pp.ok)
        if res.classificacao is not None:
            c = res.classificacao
            lam = max(c.lambda_L_x, c.lambda_L_y)
            self.tiles["Rigidez"].definir(
                "RÍGIDA" if res.rigida else "FLEXÍVEL",
                f"λ·L = {lam:.2f} — {c.classe_hetenyi}", res.rigida)
        if res.armaduras:
            partes = [f"{a.direcao}: {a.n_barras}Ø{a.phi_mm:g} c/"
                     f"{a.espacamento*100:.0f}cm" for a in res.armaduras]
            ok_flex = all(a.dominio_ok and a.as_suficiente and a.espacamento_ok
                         and a.ancoragem_ok for a in res.armaduras)
            self.tiles["Flexão"].definir(" | ".join(f"{a.n_barras}Ø{a.phi_mm:g}"
                                                     for a in res.armaduras),
                                         " | ".join(partes), ok_flex)
        if res.recalques is not None:
            r = res.recalques
            self.tiles["Recalque"].definir(
                f"{r.recalque_total_mm:.1f} / {r.limite_mm:.0f} mm",
                "recalque total estimado", r.aprovado)
        else:
            self.tiles["Recalque"].definir("não avaliado",
                                           "perfil geotécnico não informado ou "
                                           "verificação desativada", None)

    def _atualizar_verificacoes(self, res: ResultadoSapata) -> None:
        for arv in (self.tab_tensoes, self.tab_estabilidade, self.tab_puncao):
            arv.delete(*arv.get_children())
        for t in res.tensoes:
            self.tab_tensoes.insert("", "end", values=(
                t.combinacao, f"{t.sigma_max:.1f}", f"{t.sigma_min:.1f}",
                f"{t.limite:.0f}", _status(t.ok)))
        def fmt(v: float) -> str:
            return "∞" if v == float("inf") else f"{v:.2f}"

        for e in res.estabilidade:
            self.tab_estabilidade.insert("", "end", values=(
                e.combinacao, fmt(e.fs_deslizamento), fmt(e.fs_tombamento_x),
                fmt(e.fs_tombamento_y), _status(e.ok)))
        for p in res.puncao:
            self.tab_puncao.insert("", "end", values=(
                p.combinacao, p.contorno, f"{p.tau_sd:.1f}", f"{p.tau_rd:.1f}",
                f"{p.aproveitamento:.2f}", _status(p.ok)))

    def _atualizar_armaduras(self, res: ResultadoSapata) -> None:
        for filho in self.frame_armaduras.winfo_children():
            filho.destroy()
        for ar in res.armaduras:
            f = ttk.LabelFrame(self.frame_armaduras, text=f"Direção {ar.direcao}")
            f.pack(fill="x", padx=4, pady=4)
            linhas = [
                ("M_d [kN·m]", f"{ar.Md:.1f}"),
                ("d [m]", f"{ar.d:.3f}  (x/d={ar.x_d:.3f})"),
                ("Modelo adotado", ar.modelo),
                ("A_s,calc [cm²]", f"{ar.As_calc*1e4:.2f}"),
                ("A_s,mín [cm²]", f"{ar.As_min*1e4:.2f}"),
                ("A_s adotada [cm²]", f"{ar.As_adot*1e4:.2f}"),
                ("Detalhamento", f"{ar.n_barras} Ø {ar.phi_mm:g} mm c/ "
                                 f"{ar.espacamento*100:.0f} cm"
                                 + ("  [imposto]" if ar.imposta else "")),
                ("A_s efetiva [cm²]", f"{ar.As_efetiva*1e4:.2f}"),
                ("Ancoragem l_b [cm]", (f"nec. {ar.lb_necessario*100:.0f} / "
                                        f"disp. {ar.lb_disponivel*100:.0f}")),
            ]
            for i, (rot, val) in enumerate(linhas):
                ttk.Label(f, text=rot, style="PainelFraco.TLabel").grid(
                    row=i, column=0, sticky="w", padx=6, pady=1)
                ttk.Label(f, text=val, style="Painel.TLabel").grid(
                    row=i, column=1, sticky="w", padx=6, pady=1)
            ok = (ar.dominio_ok and ar.as_suficiente and ar.espacamento_ok
                  and ar.ancoragem_ok)
            ttk.Label(f, text=_status(ok),
                     foreground=tema.cor_status(ok), background=tema.FUNDO_PAINEL,
                     font=tema.FONTE_SECAO).grid(row=0, column=2, rowspan=2,
                                                 sticky="e", padx=8)

    def _atualizar_recalques(self, res: ResultadoSapata) -> None:
        for filho in self.frame_recalques.winfo_children():
            filho.destroy()
        r = res.recalques
        if r is None:
            ttk.Label(self.frame_recalques,
                     text="Recalque não avaliado: nenhum perfil geotécnico foi "
                          "informado (ou a verificação de recalque está "
                          "desativada nas opções). Preencha o perfil em camadas "
                          "na seção 'Solo de apoio' para habilitar esta análise.",
                     style="PainelFraco.TLabel", wraplength=380,
                     justify="left").pack(anchor="w", padx=6, pady=6)
            return
        resumo = ttk.Frame(self.frame_recalques, style="Painel.TFrame")
        resumo.pack(fill="x", padx=4, pady=4)
        linhas = [
            ("Tensão líquida na base [kPa]", f"{r.q_liquido:.1f}"),
            ("Profundidade de influência [m]", f"{r.profundidade_influencia:.2f}"),
            ("Recalque imediato [mm]", f"{r.recalque_imediato_mm:.1f}"),
            ("Recalque por adensamento [mm]", f"{r.recalque_adensamento_mm:.1f}"),
            ("Compressão secundária [mm]", f"{r.recalque_secundario_mm:.1f}"),
            ("TOTAL estimado [mm]",
             f"{r.recalque_total_mm:.1f}  (limite {r.limite_mm:.0f})"),
        ]
        for i, (rot, val) in enumerate(linhas):
            ttk.Label(resumo, text=rot, style="PainelFraco.TLabel").grid(
                row=i, column=0, sticky="w", padx=4, pady=1)
            ttk.Label(resumo, text=val, style="Painel.TLabel").grid(
                row=i, column=1, sticky="w", padx=4, pady=1)
        ttk.Label(resumo, text=_status(r.aprovado),
                 foreground=tema.cor_status(r.aprovado),
                 background=tema.FUNDO_PAINEL, font=tema.FONTE_SECAO).grid(
            row=0, column=2, sticky="e", padx=8)

        tabela_frame = ttk.Frame(self.frame_recalques, style="Painel.TFrame")
        tabela_frame.pack(fill="both", expand=True, padx=4, pady=(6, 4))
        arv = _tabela(tabela_frame,
                     ("Camada", "z [m]", "σ'v0", "Δσ", "recalque [mm]"),
                     (110, 80, 60, 60, 90))
        for pc in r.parcelas:
            arv.insert("", "end", values=(
                pc.camada, f"{pc.z_topo:.2f}–{pc.z_base:.2f}",
                f"{pc.sigma_v0:.1f}", f"{pc.delta_sigma:.1f}",
                f"{pc.recalque_mm:.2f}"))

    def _atualizar_memorial(self, sapata: Sapata, res: ResultadoSapata) -> None:
        texto = memorial(res, sapata)
        self.texto_memorial.configure(state="normal")
        self.texto_memorial.delete("1.0", "end")
        self.texto_memorial.insert("1.0", texto)
        self.texto_memorial.configure(state="disabled")

    def _atualizar_alertas(self, res: ResultadoSapata) -> None:
        self.texto_alertas.configure(state="normal")
        self.texto_alertas.delete("1.0", "end")
        if res.alertas:
            self.texto_alertas.insert("1.0", "\n".join(f"• {a}" for a in res.alertas))
        else:
            self.texto_alertas.insert("1.0", "Nenhum alerta do núcleo para esta "
                                              "geometria.")
        self.texto_alertas.configure(state="disabled")
