"""Interface desktop do SAPATA-7 — escopo AMPLO (carga excêntrica, punção,
bielas e tirantes, estabilidade, recalques por substrato homogêneo).

Regra de a3-interface.md: esta tela NÃO calcula nada. Ela coleta entrada,
chama calc_core.sapata_isolada e renderiza o memorial que o próprio pacote
já monta (calc_core.sapata_isolada.relatorio.memorial).

Diferença para ui/app_desktop.py: aquela cobre só carga centrada, com
motor 100% auditado (ruleset.yaml, regras NBR6122-*). Esta cobre muito mais
casos, mas parte do motor ainda está com status PENDENTE_HUMANO no
ruleset.yaml (seção escopo_amplo_em_conferencia) — a tela deixa isso visível
o tempo todo, não só na primeira leitura.

Uso:
    python -m ui.app_completo
"""
from __future__ import annotations

import sys
import tkinter as tk
from tkinter import messagebox, ttk

if __package__ in (None, ""):
    import pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from calc_core.sapata_isolada.acoes import CasoCarga, Esforcos, Pilar, gerar_combinacoes
from calc_core.sapata_isolada.geotecnia import Solo
from calc_core.sapata_isolada.materiais import Aco, Concreto
from calc_core.sapata_isolada.relatorio import memorial
from calc_core.sapata_isolada.sapata import OpcoesProjeto, Sapata

TITULO = "SAPATA-7 — Dimensionamento completo (escopo amplo, EM CONFERÊNCIA)"

AVISO_ESCOPO = (
    "ESCOPO AMPLO — PARCIALMENTE EM CONFERÊNCIA. Materiais (NBR 6118 §8), "
    "ancoragem (§9.4), cisalhamento (§19.4) e punção (§19.5) foram "
    "auditados item a item contra o texto da norma (ver ruleset.yaml). "
    "Geotecnia sob carga excêntrica, recalques, bielas e tirantes, e o "
    "modelo de rigidez/grelha AINDA NÃO foram auditados formula a fórmula "
    "— use com revisão manual do engenheiro antes de qualquer uso "
    "profissional. Para o caso mínimo já 100% auditado (carga centrada), "
    "use 'python -m ui.app_desktop'."
)


class AplicativoSapata7Completo(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(TITULO)
        self.geometry("880x760")
        self.minsize(760, 640)
        self._montar_layout()

    # ------------------------------------------------------------------
    def _campo(self, frame, row, rotulo, padrao, col=0):
        ttk.Label(frame, text=rotulo).grid(row=row, column=col * 2, sticky="w", padx=6, pady=3)
        var = tk.StringVar(value=padrao)
        ttk.Entry(frame, textvariable=var, width=12).grid(
            row=row, column=col * 2 + 1, sticky="w", padx=6, pady=3
        )
        return var

    def _montar_layout(self) -> None:
        aviso = ttk.Label(
            self, text=AVISO_ESCOPO, wraplength=850, justify="left",
            foreground="#8a4b00", font=("TkDefaultFont", 9, "italic"),
        )
        aviso.pack(fill="x", padx=12, pady=(10, 4))

        notebook = ttk.Notebook(self)
        notebook.pack(fill="x", padx=12, pady=4)

        # --- aba pilar / materiais -----------------------------------
        aba1 = ttk.Frame(notebook)
        notebook.add(aba1, text="Pilar e materiais")
        self.v = {}
        self.v["ap"] = self._campo(aba1, 0, "Pilar — dimensão X [m]", "0.30")
        self.v["bp"] = self._campo(aba1, 1, "Pilar — dimensão Y [m]", "0.50")
        self.v["fck"] = self._campo(aba1, 2, "Concreto — fck [MPa]", "30")
        self.agregado = tk.StringVar(value="granito")
        ttk.Label(aba1, text="Agregado graúdo (define alpha_E)").grid(row=3, column=0, sticky="w", padx=6, pady=3)
        ttk.Combobox(
            aba1, textvariable=self.agregado, state="readonly", width=10,
            values=["basalto", "diabasio", "granito", "gnaisse", "calcario", "arenito"],
        ).grid(row=3, column=1, sticky="w", padx=6, pady=3)
        self.v["fyk"] = self._campo(aba1, 4, "Aço — fyk [MPa] (250/500/600)", "500")
        self.v["cobrimento"] = self._campo(aba1, 5, "Cobrimento nominal [cm]", "4.5")

        # --- aba solo ---------------------------------------------------
        aba2 = ttk.Frame(notebook)
        notebook.add(aba2, text="Solo")
        self.v["sigma_adm"] = self._campo(aba2, 0, "Tensão admissível σ_adm [kPa]", "250")
        self.v["gamma_solo"] = self._campo(aba2, 1, "Peso específico do solo [kN/m³]", "18")
        self.v["hf"] = self._campo(aba2, 2, "Cota de assentamento [m]", "1.5")
        self.v["phi_solo"] = self._campo(aba2, 3, "Ângulo de atrito φ' [graus]", "30")
        self.v["coesao"] = self._campo(aba2, 4, "Coesão c' [kPa]", "0")

        # --- aba ações ----------------------------------------------
        aba3 = ttk.Frame(notebook)
        notebook.add(aba3, text="Ações")
        ttk.Label(aba3, text="Permanente (G) — sempre incluída",
                  font=("TkDefaultFont", 9, "bold")).grid(row=0, column=0, columnspan=4, sticky="w", padx=6, pady=(6, 2))
        self.v["G_N"] = self._campo(aba3, 1, "N [kN]", "600", col=0)
        self.v["G_Mx"] = self._campo(aba3, 1, "Mx [kN.m]", "15", col=1)
        self.v["G_My"] = self._campo(aba3, 2, "My [kN.m]", "8", col=0)
        self.v["G_Hx"] = self._campo(aba3, 2, "Hx [kN]", "0", col=1)

        self.usar_q = tk.BooleanVar(value=True)
        ttk.Checkbutton(aba3, text="Incluir ação variável (Q)", variable=self.usar_q).grid(
            row=3, column=0, columnspan=2, sticky="w", padx=6, pady=(10, 2))
        self.v["Q_N"] = self._campo(aba3, 4, "N [kN]", "180", col=0)
        self.v["Q_Mx"] = self._campo(aba3, 4, "Mx [kN.m]", "6", col=1)

        self.usar_w = tk.BooleanVar(value=False)
        ttk.Checkbutton(aba3, text="Incluir vento (W, reversível)", variable=self.usar_w).grid(
            row=5, column=0, columnspan=2, sticky="w", padx=6, pady=(10, 2))
        self.v["W_My"] = self._campo(aba3, 6, "My [kN.m]", "45", col=0)
        self.v["W_Hx"] = self._campo(aba3, 6, "Hx [kN]", "18", col=1)

        # --- aba opções ----------------------------------------------
        aba4 = ttk.Frame(notebook)
        notebook.add(aba4, text="Opções")
        self.modelo_reacao = tk.StringVar(value="rigido")
        ttk.Label(aba4, text="Modelo de reação do solo").grid(row=0, column=0, sticky="w", padx=6, pady=3)
        ttk.Combobox(
            aba4, textvariable=self.modelo_reacao, state="readonly", width=12,
            values=["rigido", "elastico", "grelha", "envoltoria"],
        ).grid(row=0, column=1, sticky="w", padx=6, pady=3)
        self.modelo_armadura = tk.StringVar(value="bielas")
        ttk.Label(aba4, text="Armadura de sapata rígida").grid(row=1, column=0, sticky="w", padx=6, pady=3)
        ttk.Combobox(
            aba4, textvariable=self.modelo_armadura, state="readonly", width=12,
            values=["bielas", "flexao", "envoltoria"],
        ).grid(row=1, column=1, sticky="w", padx=6, pady=3)

        ttk.Button(self, text="Dimensionar", command=self._calcular).pack(pady=8)

        resultado_frame = ttk.LabelFrame(self, text="Memorial")
        resultado_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.texto = tk.Text(resultado_frame, wrap="word", font=("TkFixedFont", 9), state="disabled")
        barra = ttk.Scrollbar(resultado_frame, command=self.texto.yview)
        self.texto.configure(yscrollcommand=barra.set)
        self.texto.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        barra.pack(side="right", fill="y", pady=6)

    # ------------------------------------------------------------------
    def _f(self, chave: str) -> float:
        return float(self.v[chave].get().replace(",", "."))

    def _calcular(self) -> None:
        try:
            pilar = Pilar(ap=self._f("ap"), bp=self._f("bp"))
            solo = Solo(
                sigma_adm=self._f("sigma_adm"), gamma_solo=self._f("gamma_solo"),
                hf=self._f("hf"), phi=self._f("phi_solo"), coesao=self._f("coesao"),
            )
            concreto = Concreto(fck=self._f("fck"), agregado=self.agregado.get())
            aco = Aco(fyk=self._f("fyk"))

            casos = [CasoCarga("G", Esforcos(
                N=self._f("G_N"), Mx=self._f("G_Mx"),
                My=self._f("G_My"), Hx=self._f("G_Hx"),
            ))]
            if self.usar_q.get():
                casos.append(CasoCarga.acidental(
                    "Q", Esforcos(N=self._f("Q_N"), Mx=self._f("Q_Mx"))))
            if self.usar_w.get():
                casos.append(CasoCarga.vento(
                    "W", Esforcos(My=self._f("W_My"), Hx=self._f("W_Hx"))))

            combinacoes = gerar_combinacoes(casos)
            opcoes = OpcoesProjeto(
                verificar_recalque=False,  # perfil de solo em camadas não coletado nesta tela
                modelo_reacao=self.modelo_reacao.get(),
                modelo_armadura_rigida=self.modelo_armadura.get(),
            )
            sapata = Sapata(pilar, solo, concreto, aco, combinacoes,
                            cobrimento=self._f("cobrimento") / 100.0, opcoes=opcoes)
        except ValueError as erro:
            messagebox.showerror("Entrada inválida", str(erro))
            return
        except Exception as erro:  # noqa: BLE001 — mostra ao usuário, não trava a UI
            messagebox.showerror("Erro no cálculo", f"{type(erro).__name__}: {erro}")
            return

        resultado = sapata.dimensionar()
        texto_memorial = (
            "AVISO: parte deste memorial vem de módulos ainda EM CONFERÊNCIA\n"
            "(ver ruleset.yaml, escopo_amplo_em_conferencia). Reveja com um\n"
            "engenheiro antes de qualquer uso profissional.\n"
            + memorial(resultado, sapata)
        )
        self.texto.configure(state="normal")
        self.texto.delete("1.0", "end")
        self.texto.insert("1.0", texto_memorial)
        self.texto.configure(state="disabled")


def main() -> None:
    AplicativoSapata7Completo().mainloop()


if __name__ == "__main__":
    main()
