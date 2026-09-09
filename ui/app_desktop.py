"""Interface desktop do SAPATA-7 — escopo mínimo: sapata isolada, carga
centrada, solo homogêneo.

Regra de a3-interface.md: esta tela NÃO calcula nada. Ela coleta entrada,
chama ``calc_core`` e renderiza o resultado. Qualquer conta que pareça estar
faltando aqui pertence a ``calc_core/``, não a este arquivo.

Uso:
    python -m ui.app_desktop

Empacotado em .exe via PyInstaller — ver build_exe.spec e
.github/workflows/build-exe.yml.
"""
from __future__ import annotations

import sys
import tkinter as tk
from tkinter import messagebox, ttk

# permite `python ui/app_desktop.py` a partir do PyInstaller (que roda o
# script isolado, fora do pacote) sem quebrar o import de calc_core.
if __package__ in (None, ""):
    import pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from calc_core.geotecnico.geometria import dimensionar_sapata_carga_centrada
from calc_core.modelos import EntradaSapataCentrada, ResultadoGeometria

TITULO = "SAPATA-7 — Dimensionamento geotécnico (escopo mínimo)"

AVISO_ESCOPO = (
    "Escopo atual: apenas geometria (B×L) de sapata isolada sob carga "
    "vertical CENTRADA, em solo homogêneo, com σ_adm fornecida pelo "
    "engenheiro. NÃO inclui carga excêntrica, deslizamento, tombamento, "
    "recalques nem dimensionamento estrutural (armadura, punção). Resultado "
    "é apoio à decisão — o memorial e os desenhos finais são de "
    "responsabilidade do engenheiro que assina a ART (NBR 6122:2022 §7.1)."
)


class AplicativoSapata7(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(TITULO)
        self.geometry("720x640")
        self.minsize(640, 560)

        self._montar_layout()

    # ------------------------------------------------------------------
    # layout
    # ------------------------------------------------------------------
    def _montar_layout(self) -> None:
        aviso = ttk.Label(
            self, text=AVISO_ESCOPO, wraplength=680, justify="left",
            foreground="#8a4b00", font=("TkDefaultFont", 9, "italic"),
        )
        aviso.pack(fill="x", padx=12, pady=(10, 4))

        entrada_frame = ttk.LabelFrame(self, text="Entrada")
        entrada_frame.pack(fill="x", padx=12, pady=8)

        self.campos: dict[str, tk.StringVar] = {}
        linhas = [
            ("N_k", "Carga vertical característica N_k [kN]", "1200"),
            ("sigma_adm", "Tensão admissível do terreno σ_adm [kPa]", "250"),
            ("pilar_a", "Dimensão do pilar em X [m]", "0.30"),
            ("pilar_b", "Dimensão do pilar em Y [m]", "0.50"),
            ("percentual_peso_proprio", "Peso próprio estimado [% da carga, mín. 5 — NBR 6122 §5.6]", "5"),
            ("dimensao_minima", "Dimensão mínima em planta [m — NBR 6122 §7.7.1]", "0.60"),
            ("modulo_arredondamento", "Arredondar B/L para múltiplos de [m]", "0.05"),
        ]
        for i, (chave, rotulo, padrao) in enumerate(linhas):
            ttk.Label(entrada_frame, text=rotulo).grid(
                row=i, column=0, sticky="w", padx=6, pady=4
            )
            var = tk.StringVar(value=padrao)
            ttk.Entry(entrada_frame, textvariable=var, width=14).grid(
                row=i, column=1, sticky="e", padx=6, pady=4
            )
            self.campos[chave] = var

        self.considerar_peso_proprio = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            entrada_frame,
            text="Considerar peso próprio estimado (NBR 6122 §5.6)",
            variable=self.considerar_peso_proprio,
        ).grid(row=len(linhas), column=0, columnspan=2, sticky="w", padx=6, pady=(4, 8))

        entrada_frame.columnconfigure(1, weight=1)

        ttk.Button(
            self, text="Calcular", command=self._calcular
        ).pack(pady=(0, 8))

        resultado_frame = ttk.LabelFrame(self, text="Resultado e memorial")
        resultado_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.texto_resultado = tk.Text(
            resultado_frame, wrap="word", height=16, state="disabled",
            font=("TkFixedFont", 10),
        )
        self.texto_resultado.pack(fill="both", expand=True, padx=6, pady=6)

    # ------------------------------------------------------------------
    # ação — só coleta e delega; nenhuma conta acontece aqui
    # ------------------------------------------------------------------
    def _calcular(self) -> None:
        try:
            entrada = EntradaSapataCentrada(
                N_k=float(self.campos["N_k"].get().replace(",", ".")),
                sigma_adm=float(self.campos["sigma_adm"].get().replace(",", ".")),
                pilar_a=float(self.campos["pilar_a"].get().replace(",", ".")),
                pilar_b=float(self.campos["pilar_b"].get().replace(",", ".")),
                considerar_peso_proprio=self.considerar_peso_proprio.get(),
                percentual_peso_proprio=(
                    float(self.campos["percentual_peso_proprio"].get().replace(",", ".")) / 100
                ),
                dimensao_minima=float(self.campos["dimensao_minima"].get().replace(",", ".")),
                modulo_arredondamento=float(self.campos["modulo_arredondamento"].get().replace(",", ".")),
            )
        except ValueError as erro:
            messagebox.showerror("Entrada inválida", str(erro))
            return

        resultado = dimensionar_sapata_carga_centrada(entrada)
        self._renderizar(entrada, resultado)

    # ------------------------------------------------------------------
    # renderização — só formata o que calc_core já calculou
    # ------------------------------------------------------------------
    def _renderizar(self, entrada: EntradaSapataCentrada, r: ResultadoGeometria) -> None:
        linhas = []
        linhas.append("=" * 60)
        linhas.append("MEMORIAL — DIMENSIONAMENTO GEOTÉCNICO (escopo mínimo)")
        linhas.append("=" * 60)
        linhas.append("")
        linhas.append(f"N_k (carga do pilar) ............. {entrada.N_k:.2f} kN")
        if entrada.considerar_peso_proprio:
            linhas.append(
                f"Peso próprio estimado ............ "
                f"{entrada.percentual_peso_proprio * 100:.1f} % "
                f"[rule: NBR6122-5.6-peso-proprio-minimo]"
            )
        linhas.append(f"N_total (carga considerada) ...... {r.N_total:.2f} kN")
        linhas.append(f"σ_adm (entrada do engenheiro) .... {entrada.sigma_adm:.2f} kPa")
        linhas.append(f"Pilar ............................ {entrada.pilar_a:.2f} × {entrada.pilar_b:.2f} m")
        linhas.append("")
        linhas.append(f"Área necessária (N_total/σ_adm) .. {r.area_necessaria:.3f} m²")
        linhas.append(f"B × L (arredondado) .............. {r.B:.2f} × {r.L:.2f} m")
        linhas.append(f"Área final ........................ {r.area_final:.3f} m²")
        linhas.append(f"σ_atuante ......................... {r.tensao_atuante:.1f} kPa")
        linhas.append("")
        linhas.append("-" * 60)
        linhas.append("VERIFICAÇÕES NORMATIVAS")
        linhas.append("-" * 60)
        for v in r.verificacoes:
            selo = "[OK]" if v.ok else "[REPROVADO]"
            linhas.append(f"{selo} {v.regra}")
            linhas.append(f"       {v.descricao}")
            linhas.append(f"       {v.mensagem}")
            linhas.append("")

        linhas.append("-" * 60)
        status = "APROVADO neste escopo mínimo" if r.aprovado else "REPROVADO — revisar entrada"
        linhas.append(f"RESULTADO GERAL: {status}")
        linhas.append("-" * 60)
        linhas.append("")
        linhas.append(
            "Este resultado cobre apenas a geometria geotécnica da sapata sob "
            "carga centrada. Dimensionamento estrutural (armadura, punção), "
            "verificação de recalques, deslizamento e tombamento NÃO estão "
            "incluídos — ver CLAUDE.md e ruleset.yaml deste repositório."
        )

        self.texto_resultado.configure(state="normal")
        self.texto_resultado.delete("1.0", "end")
        self.texto_resultado.insert("1.0", "\n".join(linhas))
        self.texto_resultado.configure(state="disabled")


def main() -> None:
    app = AplicativoSapata7()
    app.mainloop()


if __name__ == "__main__":
    main()
