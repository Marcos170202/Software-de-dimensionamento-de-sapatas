"""
app.py
------
Janela principal do escopo AMPLO do SAPATA-7.

Restrição de a3-interface.md: esta tela não calcula nada. `_calcular` só
instancia `Sapata` a partir do que o formulário devolve e chama
`Sapata.dimensionar()`; todo o resto é leitura de `ResultadoSapata` e
formatação.

`calc_core/sapata_isolada/` tem parte auditada contra a NBR 6118 (materiais,
ancoragem, cisalhamento, punção — ver ruleset.yaml) e parte ainda
PENDENTE_HUMANO (geotecnia sob excentricidade, bielas, rigidez/grelha,
recalques, MEF do solo). Esse aviso fica fixo na tela (banner abaixo da
barra superior) e no rodapé do memorial — nunca só num popup de abertura.
"""
from __future__ import annotations

import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

if __package__ in (None, ""):
    import pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from calc_core.sapata_isolada.acoes import gerar_combinacoes
from calc_core.sapata_isolada.pranchas import gerar_memorial_pdf
from calc_core.sapata_isolada.sapata import ResultadoSapata, Sapata

from . import tema
from .formulario import PainelEntrada
from .modelo import construir_modelo_visual
from .resultado import PainelResultado
from .visualizacao import PainelVisualizacao

TITULO = "SAPATA ISOLADA"
SUBTITULO = "NBR 6118:2023 · NBR 6122:2019 — escopo amplo"

AVISO_BANNER = (
    "ESCOPO AMPLO — PARCIALMENTE EM CONFERÊNCIA. Materiais, ancoragem, "
    "cisalhamento e punção foram auditados item a item contra a NBR 6118 "
    "(ver ruleset.yaml). Geotecnia sob carga excêntrica, bielas e tirantes, "
    "rigidez/grelha, recalques e MEF do solo ainda NÃO foram auditados — "
    "reveja com um engenheiro antes de qualquer uso profissional. "
    "Ajuda ▸ Sobre o escopo para o texto completo."
)

AVISO_ESCOPO_COMPLETO = (
    "ESCOPO AMPLO — PARCIALMENTE EM CONFERÊNCIA.\n\n"
    "Materiais (NBR 6118 §8), ancoragem (§9.3-9.4), cisalhamento (§19.4) e "
    "punção (§19.5) foram auditados item a item contra o texto da norma por "
    "leitura visual das páginas, com 6 defeitos corrigidos (2 do lado "
    "inseguro) — ver relatorios/revisao_codigo.md, adendo.\n\n"
    "A geotecnia sob excentricidade dupla, o modelo de bielas e tirantes de "
    "Blévot, a rigidez/grelha sobre base elástica de Winkler, os recalques "
    "(Schmertmann/Terzaghi) e o MEF do solo foram PORTADOS mas AINDA NÃO "
    "auditados item a item contra a fonte normativa — ver ruleset.yaml, "
    "seção escopo_amplo_em_conferencia.\n\n"
    "σ_adm sempre admite sobreposição manual pelo engenheiro (NBR 6122 "
    "§7.2 lista doze fatores para fixá-la). Solo expansivo ou colapsível "
    "exige tratamento específico (§7.5.2/§7.5.3) que nenhum dos dois "
    "motores deste software dimensiona.\n\n"
    "Minuta sujeita a conferência do responsável técnico que assina a ART."
)


class AppSapataCompleto(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"SAPATA-7 — {TITULO} (escopo amplo)")
        self.geometry("1600x960")
        self.minsize(1180, 760)
        tema.aplicar_tema(self)

        self._sapata: Sapata | None = None
        self._resultado: ResultadoSapata | None = None
        self._modelo: dict | None = None

        self._montar_menu()
        self._montar_topo()
        self._montar_banner()
        self._montar_corpo()
        self._montar_status()

        self.bind("<F5>", lambda evento: self._calcular())

    # ------------------------------------------------------------------ menu
    def _montar_menu(self) -> None:
        barra = tk.Menu(self)
        arquivo = tk.Menu(barra, tearoff=0)
        arquivo.add_command(label="Calcular\tF5", command=self._calcular)
        arquivo.add_command(label="Exportar PDF...", command=self._exportar_pdf)
        arquivo.add_separator()
        arquivo.add_command(label="Sair", command=self.destroy)
        barra.add_cascade(label="Arquivo", menu=arquivo)

        vista = tk.Menu(barra, tearoff=0)
        vista.add_command(label="Modelo 3D",
                          command=lambda: self.visualizacao.select(0))
        vista.add_command(label="Momentos",
                          command=lambda: self.visualizacao.select(1))
        vista.add_command(label="Reação do solo",
                          command=lambda: self.visualizacao.select(2))
        vista.add_command(label="Perfil geológico",
                          command=lambda: self.visualizacao.select(3))
        barra.add_cascade(label="Vista", menu=vista)

        ajuda = tk.Menu(barra, tearoff=0)
        ajuda.add_command(label="Sobre o escopo em conferência",
                          command=self._mostrar_escopo)
        ajuda.add_command(label="Sobre o SAPATA-7", command=self._mostrar_sobre)
        barra.add_cascade(label="Ajuda", menu=ajuda)
        self.configure(menu=barra)

    def _mostrar_escopo(self) -> None:
        messagebox.showinfo("Escopo em conferência", AVISO_ESCOPO_COMPLETO)

    def _mostrar_sobre(self) -> None:
        messagebox.showinfo(
            "Sobre o SAPATA-7",
            "SAPATA-7 — dimensionamento estrutural e geotécnico de sapatas.\n"
            "Motor: calc_core.sapata_isolada (escopo amplo).\n"
            "Todo número vem do núcleo Python; esta tela só coleta entrada e "
            "formata a saída.")

    # ------------------------------------------------------------------ topo
    def _montar_topo(self) -> None:
        topo = ttk.Frame(self, style="Painel.TFrame")
        topo.pack(side="top", fill="x")
        esquerda = ttk.Frame(topo, style="Painel.TFrame")
        esquerda.pack(side="left", padx=14, pady=8)
        ttk.Label(esquerda, text=TITULO, style="Titulo.TLabel").pack(anchor="w")
        ttk.Label(esquerda, text=SUBTITULO, style="Subtitulo.TLabel").pack(
            anchor="w")

        direita = ttk.Frame(topo, style="Painel.TFrame")
        direita.pack(side="right", padx=14, pady=8)
        ttk.Button(direita, text="Exportar PDF", style="Pdf.TButton",
                  command=self._exportar_pdf).pack(side="right", padx=(8, 0))
        ttk.Button(direita, text="Calcular (F5)", style="Acento.TButton",
                  command=self._calcular).pack(side="right")

    def _montar_banner(self) -> None:
        banner = ttk.Label(self, text=AVISO_BANNER, style="Banner.TLabel",
                           wraplength=1560, justify="left", padding=(14, 4))
        banner.pack(side="top", fill="x")
        self._banner = banner
        self.bind("<Configure>", self._reajustar_banner)

    def _reajustar_banner(self, evento: tk.Event) -> None:
        if evento.widget is self:
            self._banner.configure(wraplength=max(400, evento.width - 28))

    # ------------------------------------------------------------------ corpo
    def _montar_corpo(self) -> None:
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(side="top", fill="both", expand=True)

        self.formulario = PainelEntrada(paned)
        self.visualizacao = PainelVisualizacao(paned)
        self.resultado = PainelResultado(paned)

        paned.add(self.formulario, weight=0)
        paned.add(self.visualizacao, weight=3)
        paned.add(self.resultado, weight=2)

    def _montar_status(self) -> None:
        barra = ttk.Frame(self, style="Painel.TFrame")
        barra.pack(side="bottom", fill="x")
        self.status_esquerda = ttk.Label(
            barra, text="Preencha os dados e calcule (F5).",
            style="Rodape.TLabel")
        self.status_esquerda.pack(side="left", padx=10, pady=4)
        self.status_direita = ttk.Label(barra, text="", style="Rodape.TLabel")
        self.status_direita.pack(side="right", padx=10, pady=4)

    # -------------------------------------------------------------- cálculo
    def _calcular(self) -> None:
        try:
            pilar = self.formulario.ler_pilar()
            solo = self.formulario.ler_solo()
            concreto, aco, cobrimento = self.formulario.ler_materiais()
            casos = self.formulario.ler_casos()
            combinacoes = gerar_combinacoes(casos)
            opcoes = self.formulario.ler_opcoes()
            sapata = Sapata(pilar, solo, concreto, aco, combinacoes,
                            cobrimento=cobrimento, opcoes=opcoes)
        except ValueError as erro:
            messagebox.showerror("Entrada inválida", str(erro))
            return
        except Exception as erro:   # noqa: BLE001 — mostra ao usuário, não trava
            messagebox.showerror("Erro ao montar a sapata",
                                 f"{type(erro).__name__}: {erro}")
            return

        try:
            resultado = sapata.dimensionar()
        except Exception as erro:   # noqa: BLE001
            messagebox.showerror("Erro no cálculo",
                                 f"{type(erro).__name__}: {erro}")
            return

        self._sapata = sapata
        self._resultado = resultado
        self._modelo = construir_modelo_visual(sapata, resultado)

        if not resultado.modo_verificacao:
            self.formulario.registrar_resultado_automatico(resultado)

        self.visualizacao.atualizar(sapata, resultado, self._modelo)
        self.resultado.atualizar(sapata, resultado)
        self._atualizar_status(sapata, resultado)

    def _atualizar_status(self, sapata: Sapata, resultado: ResultadoSapata) -> None:
        if resultado.aprovado:
            msg = "Cálculo concluído — todas as verificações atendidas."
        else:
            faltas = "; ".join(resultado.reprovacoes[:3])
            extra = (f" (+{len(resultado.reprovacoes) - 3} outra(s))"
                     if len(resultado.reprovacoes) > 3 else "")
            msg = f"Reprovado: {faltas}{extra}"
        self.status_esquerda.configure(text=msg)

        n_comb = len(sapata.combinacoes)
        texto = f"{n_comb} combinações geradas"
        if resultado.tensoes:
            pior = max(resultado.tensoes,
                      key=lambda t: t.sigma_max / max(t.limite, 1e-9))
            texto += f"  ·  crítica: {pior.combinacao}"
        self.status_direita.configure(text=texto)

    # ---------------------------------------------------------------- pdf
    def _exportar_pdf(self) -> None:
        if self._resultado is None or self._sapata is None or self._modelo is None:
            messagebox.showinfo(
                "Nada para exportar",
                "Calcule a sapata (F5) antes de exportar o memorial em PDF.")
            return
        caminho = filedialog.asksaveasfilename(
            title="Salvar memorial em PDF", defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")])
        if not caminho:
            return
        try:
            gerar_memorial_pdf(caminho, self._sapata, self._resultado, self._modelo)
        except Exception as erro:   # noqa: BLE001 — mostra ao usuário, não trava
            messagebox.showerror("Erro ao exportar PDF",
                                 f"{type(erro).__name__}: {erro}")
            return
        messagebox.showinfo("PDF exportado", f"Memorial salvo em:\n{caminho}")


def main() -> None:
    AppSapataCompleto().mainloop()


if __name__ == "__main__":
    main()
