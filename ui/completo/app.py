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

import importlib
import sys
import tkinter as tk
from dataclasses import replace
from tkinter import filedialog, messagebox, ttk

if __package__ in (None, ""):
    import pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from calc_core.sapata_isolada.acoes import gerar_combinacoes
from calc_core.sapata_isolada.geotecnia import PerfilGeotecnico
from calc_core.sapata_isolada.pranchas import gerar_memorial_pdf
from calc_core.sapata_isolada.sapata import ResultadoSapata, Sapata

from . import avisos, projeto, tema
from .formulario import PainelEntrada, _camada_e_abaixo_na, _hf_valido
from .modelo import construir_modelo_visual
from .resultado import PainelResultado
from .visualizacao import PainelVisualizacao

# `excel_export`/`excel_import` importam `openpyxl` no topo do arquivo — uma
# dependência de runtime SÓ dos 4 itens de menu de Excel (ver
# requirements.txt). Importá-los aqui, no topo de `app.py`, tornaria
# `openpyxl` uma dependência DURA de `ui.completo` inteiro (o pacote é
# importado por `ui.completo.__init__` -> `.app`), derrubando qualquer teste
# ou uso deste módulo num ambiente sem `openpyxl` (ver defeito D1 do GATE 2,
# rodada 1). `_modulo_excel` faz o import tardio, só quando um desses 4 itens
# de menu é de fato usado, e mostra um aviso claro se a lib estiver ausente
# em vez de deixar o app inteiro morrer com `ModuleNotFoundError` no boot.
_AVISO_OPENPYXL_AUSENTE = (
    "Os recursos de Excel (importar planilha, gerar modelo, exportar "
    "relatório) exigem a biblioteca 'openpyxl', que não está instalada "
    "neste ambiente Python.\n\nInstale com:\n    pip install openpyxl\n\n"
    "(já está listada em requirements.txt e requirements-dev.txt).")


def _modulo_excel(nome: str):
    """Importa `ui.completo.excel_import` ou `ui.completo.excel_export` sob
    demanda. Devolve `None` (depois de avisar o usuário) se `openpyxl` não
    estiver instalado, em vez de deixar o `ImportError` subir cru."""
    try:
        return importlib.import_module(f".{nome}", package=__package__)
    except ImportError as erro:
        # BAIXA do GATE 2, rodada 2 (`app.py:55`): capturar `ImportError` do
        # módulo INTEIRO (não só de `openpyxl`) faz um erro de refactor no
        # núcleo (símbolo renomeado/removido em
        # `calc_core.sapata_isolada.*`, importado por `excel_import`/
        # `excel_export`) ser diagnosticado ERRADO como "openpyxl ausente" —
        # confunde o diagnóstico e esconde o bug real. `erro.name` é o nome
        # do módulo que faltou — a `ModuleNotFoundError` real que o
        # interpretador levanta quando `import openpyxl` (no topo de
        # `excel_import.py`/`excel_export.py`) falha SEMPRE traz
        # `name="openpyxl"`; só re-propaga quando o atributo está presente
        # E aponta para outro módulo (`erro.name is None` — sem informação
        # — mantém o comportamento antigo, para não arriscar confundir um
        # `ImportError` genérico sem `.name` com um bug do núcleo).
        nome_faltante = getattr(erro, "name", None)
        if nome_faltante is not None and nome_faltante != "openpyxl":
            raise
        messagebox.showerror("Biblioteca ausente", _AVISO_OPENPYXL_AUSENTE)
        return None


TITULO = "SAPATA ISOLADA"
SUBTITULO = "NBR 6118:2023 · NBR 6122:2022 — escopo amplo"

# Texto movido para `avisos.py` (sem dependência de tkinter) para que
# `excel_export.py` também possa gravá-lo na aba "Resumo" do relatório
# Excel (defeito D10 do GATE 2, rodada 1) sem precisar importar `app.py`
# (que importa `tkinter`). Reexportado aqui por compatibilidade — quem já
# importava `AVISO_BANNER`/`AVISO_ESCOPO_COMPLETO` de `ui.completo.app`
# continua funcionando.
AVISO_BANNER = avisos.AVISO_BANNER
AVISO_ESCOPO_COMPLETO = avisos.AVISO_ESCOPO_COMPLETO


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
        self._proveniencia_sigma_adm: dict | None = None
        """Snapshot de `PainelEntrada.ultimo_sigma_adm_calculado` no momento
        do último `_calcular()` — ver ali e D-02 do GATE 2, rodada 3."""

        self._montar_menu()
        self._montar_topo()
        self._montar_banner()
        self._montar_corpo()
        self._montar_status()

        self.bind("<F5>", lambda evento: self._calcular())

    # ---------------------------------------------------- rede de segurança
    def report_callback_exception(self, exc, val, tb) -> None:
        """Sobrescreve o handler padrão do Tk para exceção não tratada
        DENTRO de um callback (comando de menu, `bind`, `after`, etc.).

        Por padrão o Tk só IMPRIME a exceção em `sys.stderr` via
        `traceback.print_exception` — invisível num `.exe` empacotado com
        `console=False` (ver `sapata7.spec`), então qualquer bug que escape
        de um `try/except` dentro de um handler de menu falha 100% em
        silêncio: nenhum diálogo, nenhum log, a tela simplesmente para de
        reagir ou fica com estado parcial (ALTA #1 do GATE 2, rodada 2 —
        `ler_solo()` fora de qualquer `try/except` em `_importar_excel`
        era só UM sítio onde isso podia acontecer; este handler é a rede de
        segurança para qualquer outro, presente ou futuro). Mostra a mesma
        caixa de diálogo `messagebox.showerror` que os handlers já usam, em
        vez de deixar a exceção morrer muda."""
        import traceback
        detalhe = "".join(traceback.format_exception(exc, val, tb))
        try:
            messagebox.showerror(
                "Erro inesperado",
                "Ocorreu um erro inesperado e não tratado nesta ação.\n\n"
                f"{val}\n\nDetalhes técnicos:\n{detalhe[-2000:]}")
        except Exception:   # noqa: BLE001, S110 — último recurso: este é o
            # próprio handler de erro; se ele mesmo falhar (ex.: Tk já em
            # processo de destruição), não há mais nenhum lugar para
            # reportar — engolir aqui é preferível a um traceback duplo/
            # recursivo no encerramento do app.
            pass

    # ------------------------------------------------------------------ menu
    def _montar_menu(self) -> None:
        barra = tk.Menu(self)
        arquivo = tk.Menu(barra, tearoff=0)
        arquivo.add_command(label="Calcular\tF5", command=self._calcular)
        arquivo.add_command(label="Salvar projeto...", command=self._salvar_projeto)
        arquivo.add_command(label="Abrir projeto...", command=self._abrir_projeto)
        arquivo.add_separator()
        arquivo.add_command(label="Importar do Excel...", command=self._importar_excel)
        arquivo.add_command(label="Gerar modelo de planilha...",
                            command=self._gerar_modelo_excel)
        arquivo.add_separator()
        arquivo.add_command(label="Exportar PDF...", command=self._exportar_pdf)
        arquivo.add_command(label="Exportar relatório Excel...",
                            command=self._exportar_excel)
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
        # D-02 do GATE 2, rodada 3: snapshot da proveniência de σ_adm NO
        # MOMENTO deste cálculo — `PainelEntrada.ultimo_sigma_adm_calculado`
        # já é `None` sempre que `v_sigma_adm` não é mais o que o diálogo
        # calculou (ver `formulario.py::_ao_editar_sigma_adm`), então
        # copiar a referência aqui é suficiente; não há necessidade de
        # revalidar de novo nesta camada.
        self._proveniencia_sigma_adm = self.formulario.ultimo_sigma_adm_calculado

        if not resultado.modo_verificacao:
            self.formulario.registrar_resultado_automatico(resultado)

        self.visualizacao.atualizar(sapata, resultado, self._modelo)
        self.resultado.atualizar(sapata, resultado, self._proveniencia_sigma_adm)
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

    # ------------------------------------------------------------ projeto
    def _salvar_projeto(self) -> None:
        caminho = filedialog.asksaveasfilename(
            title="Salvar projeto", defaultextension=".s7proj",
            filetypes=[("Projeto SAPATA-7", "*.s7proj")])
        if not caminho:
            return
        try:
            pilar = self.formulario.ler_pilar()
            solo = self.formulario.ler_solo()
            concreto, aco, cobrimento = self.formulario.ler_materiais()
            casos = self.formulario.ler_casos()
            opcoes = self.formulario.ler_opcoes()
            projeto.salvar_projeto(caminho, pilar, solo, concreto, aco,
                                   cobrimento, casos, opcoes)
        except ValueError as erro:
            messagebox.showerror("Entrada inválida", str(erro))
            return
        except Exception as erro:   # noqa: BLE001 — mostra ao usuário, não trava
            messagebox.showerror("Erro ao salvar projeto",
                                 f"{type(erro).__name__}: {erro}")
            return
        messagebox.showinfo("Projeto salvo", f"Projeto salvo em:\n{caminho}")

    def _abrir_projeto(self) -> None:
        caminho = filedialog.askopenfilename(
            title="Abrir projeto", filetypes=[("Projeto SAPATA-7", "*.s7proj")])
        if not caminho:
            return
        try:
            dados = projeto.carregar_projeto(caminho)
        except ValueError as erro:
            messagebox.showerror("Erro ao abrir projeto", str(erro))
            return
        except Exception as erro:   # noqa: BLE001
            messagebox.showerror("Erro ao abrir projeto",
                                 f"{type(erro).__name__}: {erro}")
            return

        # Valida TUDO antes de aplicar QUALQUER coisa (D5 do GATE 2, rodada
        # 1): `preencher_casos` é o único `preencher_*` que pode recusar os
        # dados (nomes de caso fora de G/Q/W, ou duplicados), então é
        # chamado PRIMEIRO — se falhar, nenhum outro campo do formulário
        # (pilar/solo/materiais/opções) é tocado, e a mensagem de erro
        # "nenhum caso foi preenchido, para não misturar dados antigos e
        # novos" continua verdadeira para a tela inteira, não só para os
        # casos de carga.
        try:
            self.formulario.preencher_casos(dados["casos"])
            self.formulario.preencher_pilar(dados["pilar"])
            self.formulario.preencher_solo(dados["solo"])
            self.formulario.preencher_materiais(dados["concreto"], dados["aco"],
                                                dados["cobrimento"])
            self.formulario.preencher_opcoes(dados["opcoes"])
        except ValueError as erro:
            messagebox.showerror("Erro ao abrir projeto", str(erro))
            return

        # MEDIA #4 do GATE 2, rodada 2: a tela não tem widget para TODO
        # campo que o arquivo pode trazer (ver `projeto.py`, docstring do
        # módulo, e `projeto.CAMPOS_NAO_REPOSTOS`) — os que faltam voltam
        # ao default do dataclass em silêncio no próximo F5. Avisa
        # NOMINALMENTE só os que de fato DIVERGEM do default (evita ruído
        # quando o arquivo já tinha os valores padrão).
        divergentes = projeto.campos_divergentes_do_default(dados)
        msg_divergentes = ""
        if divergentes:
            linhas = "\n".join(f"  • {d}" for d in divergentes)
            msg_divergentes = (
                "\n\nATENÇÃO — a tela não tem campo para os itens abaixo; "
                "eles voltarão ao valor padrão do núcleo ao calcular (F5), "
                "em vez do valor salvo no arquivo:\n" + linhas)

        self._invalidar_resultado(
            "Projeto carregado — calcule (F5) para atualizar o resultado.")
        messagebox.showinfo(
            "Projeto aberto",
            f"Projeto carregado de:\n{caminho}\n\nRevise os campos e calcule "
            "(F5) quando quiser — nenhum resultado foi recalculado "
            "automaticamente (o resultado salvo nunca é lido: só os dados de "
            "entrada). O resultado exibido na tela (se havia algum, de um "
            f"cálculo anterior) foi marcado como obsoleto.{msg_divergentes}")

    # ------------------------------------------------------- invalidação
    def _invalidar_resultado(self, mensagem: str) -> None:
        """Zera o cálculo em memória e marca a tela como desatualizada em
        relação aos dados de entrada que acabaram de ser repostos por
        "Abrir projeto..."/"Importar do Excel...". Sem isto, "Exportar PDF"/
        "Exportar relatório Excel" continuavam exportando o cálculo
        ANTERIOR — de outro projeto — enquanto o formulário já mostrava os
        dados novos (defeito D3 do GATE 2, rodada 1). Os dois handlers de
        exportação já caem sozinhos no ramo "calcule (F5) antes de
        exportar" assim que `self._resultado`/`self._sapata` voltam a
        `None`.

        `self.visualizacao.limpar(...)` (MEDIA #1 do GATE 2, rodada 2):
        sem isto, o modelo 3D/diagramas da sapata ANTERIOR continuavam
        desenhados na coluna central enquanto `PainelResultado` já mostrava
        "NÃO CALCULADO" e o formulário já tinha os dados do projeto NOVO —
        um estado misto que `_invalidar_resultado` deveria eliminar por
        inteiro, não só na coluna direita."""
        self._sapata = None
        self._resultado = None
        self._modelo = None
        self._proveniencia_sigma_adm = None
        self.resultado.limpar(mensagem)
        self.visualizacao.limpar(mensagem)
        self.status_esquerda.configure(text=mensagem)
        self.status_direita.configure(text="")

    # -------------------------------------------------------------- excel
    def _importar_excel(self) -> None:
        excel_import = _modulo_excel("excel_import")
        if excel_import is None:
            return
        caminho = filedialog.askopenfilename(
            title="Importar do Excel", filetypes=[("Excel", "*.xlsx")])
        if not caminho:
            return
        try:
            pilar, casos = excel_import.importar_pilar_e_cargas(caminho)
            # `ler_solo()` é lido AQUI, dentro do MESMO `try` que trata
            # `ValueError`, ANTES de qualquer `preencher_*` tocar a tela —
            # não depois (ALTA #1 do GATE 2, rodada 2: `_float()` levanta
            # `ValueError` para um campo com texto não numérico, ex. "200
            # kPa" digitado em σ_adm; se isso só fosse descoberto depois de
            # pilar/casos já terem sido aplicados, a tela ficava com uma
            # mistura de dados antigos (solo) e novos (pilar/casos) e SEM
            # invalidar o resultado — o mesmo defeito que a promessa
            # "tudo-ou-nada" abaixo já existe para resolver, agora
            # reaplicado ao próprio solo). O objeto é reaproveitado abaixo
            # tanto para a mensagem "perfil mantido" quanto para o
            # `replace(...)` que grava o perfil novo — nunca lido de novo.
            solo_atual = self.formulario.ler_solo()
            # D-04 do GATE 2, rodada 1 (a6): o TEXTO bruto de v_hf é
            # capturado AQUI, antes de `preencher_solo` (mais abaixo)
            # reescrever o campo com `solo_atual.hf` já formatado — que é
            # `_float(v_hf.get(), 1.5)`, ou seja, campo em branco vira
            # 1,5 m em silêncio. Usar esse default como base do Ramo B
            # (divergência) inventaria proveniência que o usuário não
            # digitou (mesma proibição de REQ-UI-CAMADA-02(b)).
            texto_hf_antes_da_importacao = self.formulario.v_hf.get()
        except ValueError as erro:
            messagebox.showerror("Erro ao importar planilha", str(erro))
            return
        except Exception as erro:   # noqa: BLE001
            messagebox.showerror("Erro ao importar planilha",
                                 f"{type(erro).__name__}: {erro}")
            return

        # BAIXA do GATE 2, rodada 2 (`app.py:364`): o layout desta planilha
        # não tem colunas de Hx/Hy — `preencher_casos` abaixo grava
        # Hx=Hy=0 em CADA slot (G sempre; Q/W se importados) que o usuário
        # eventualmente já tinha preenchido na tela. Zerar força horizontal
        # ALIVIA deslizamento/tombamento — é silêncio do lado INSEGURO se a
        # mensagem final não disser isso (a aba "Instruções" já avisa, mas
        # o usuário pode não a ler). Captura ANTES de `preencher_casos`
        # sobrescrever os campos.
        nomes_importados = {c.nome for c in casos}
        slots_com_horizontal_zerada = []
        for nome, vs in (("G", self.formulario.v_G), ("Q", self.formulario.v_Q),
                         ("W", self.formulario.v_W)):
            if nome not in nomes_importados:
                continue
            try:
                hx = float((vs["Hx"].get() or "0").strip().replace(",", "."))
                hy = float((vs["Hy"].get() or "0").strip().replace(",", "."))
            except ValueError:
                continue
            if hx != 0.0 or hy != 0.0:
                slots_com_horizontal_zerada.append(nome)

        # Mesma ordem "valida tudo antes de aplicar" de `_abrir_projeto`
        # acima: `preencher_casos` primeiro, pilar só depois de confirmado
        # que os casos vão entrar — senão um nome de caso recusado deixava
        # o pilar já trocado e as cargas antigas na tela, um estado misto
        # que a própria mensagem de erro nega (D5 do GATE 2, rodada 1).
        try:
            self.formulario.preencher_casos(casos)
            self.formulario.preencher_pilar(pilar)
        except ValueError as erro:
            messagebox.showerror("Erro ao importar planilha", str(erro))
            return

        perfil_anterior = solo_atual.perfil
        n_anterior = len(perfil_anterior.camadas) if perfil_anterior else 0
        try:
            perfil = excel_import.importar_perfil_geotecnico(caminho)
        except excel_import.AbaAusente:
            # não é fatal: nem toda planilha do usuário traz as duas abas.
            # O perfil que já estava na tela é MANTIDO — mas isso precisa
            # ser dito, não deixado em silêncio (D6 do GATE 2, rodada 1).
            if n_anterior:
                msg_perfil = (f"perfil geotécnico: aba ausente — o perfil "
                              f"que já estava na tela foi MANTIDO "
                              f"({n_anterior} camada(s)).")
            else:
                msg_perfil = "perfil geotécnico: aba ausente — não importado."
        except ValueError as erro:
            # Mesma coda do ramo `AbaAusente` acima (BAIXA da lista do GATE
            # 2, rodada 2, `app.py:384`): um erro na aba "Perfil geotécnico"
            # (célula inválida, tipo de substrato desconhecido etc.) também
            # MANTÉM o perfil que já estava na tela — dizer isso evita o
            # usuário concluir, ao ver só "NÃO importado por erro", que o
            # perfil ficou vazio.
            if n_anterior:
                msg_perfil = (f"perfil geotécnico: NÃO importado por erro — "
                              f"{erro} — o perfil que já estava na tela foi "
                              f"MANTIDO ({n_anterior} camada(s)).")
            else:
                msg_perfil = f"perfil geotécnico: NÃO importado por erro — {erro}"
        else:
            # REQ-UI-CAMADA-06 (backlog #12): "Importar do Excel..." NÃO é
            # um carregamento de arquivo como "Abrir projeto..." — os três
            # valores em `solo_atual` (gamma_solo/phi/coesao) não vêm da
            # planilha (`importar_perfil_geotecnico` devolve só o perfil),
            # são sobra da TELA casada com um perfil possivelmente de
            # outra obra. O estado da proveniência é capturado ANTES de
            # `preencher_solo`, que a zera incondicionalmente
            # (REQ-UI-CAMADA-04 continua valendo — `preencher_solo`
            # permanece um setter burro; a decisão é deste chamador).
            proveniencia_valida_antes = (
                self.formulario.ultima_derivacao_de_camada is not None)
            valores_tela = (solo_atual.gamma_solo, solo_atual.phi,
                            solo_atual.coesao)
            self.formulario.preencher_solo(replace(solo_atual, perfil=perfil))
            msg_perfil = (f"perfil geotécnico: {len(perfil.camadas)} "
                          "camada(s) importada(s).")
            if proveniencia_valida_antes:
                # RAMO A: os três campos eram derivados do perfil ANTIGO,
                # que acabou de ser descartado — nada que o engenheiro
                # tenha digitado se perde. Deriva-se do perfil NOVO com a
                # mesma função e as mesmas guardas de REQ-UI-CAMADA-01/02.
                self.formulario._derivar_solo_da_camada()
            else:
                # RAMO B: valores digitados à mão ou vindos de um projeto
                # aberto (proveniência já inválida) — NUNCA sobrescritos
                # (preencher_solo já garante isso: só o `perfil` muda em
                # `replace(...)`). Acrescenta uma linha de DIVERGÊNCIA ao
                # resumo quando algum dos três diferir da camada do perfil
                # NOVO na mesma cota h_f — mesma doutrina de "aba ausente,
                # perfil MANTIDO" (D6) e "Hx/Hy zeradas" (BAIXA) desta
                # mesma função: o que a importação faz ou deixa de fazer
                # com dados da tela é dito no resumo, nunca em silêncio.
                #
                # D-04 do GATE 2, rodada 1 (a6): a guarda usa o TEXTO
                # bruto capturado ANTES da importação (`_hf_valido`, a
                # mesma função que `_derivar_solo_da_camada` usa) — não
                # `solo_atual.hf`, que já veio com o default silencioso de
                # 1,5 m se o campo estivesse em branco (derivar dessa cota
                # fantasma inventaria proveniência, REQ-UI-CAMADA-02(b)).
                hf_ramo_b = _hf_valido(texto_hf_antes_da_importacao)
                if hf_ramo_b is not None and perfil.camadas:
                    # D-03 do GATE 2, rodada 1 (a6): `_camada_e_abaixo_na`
                    # é o ÚNICO ponto que decide camada/abaixo_na — a
                    # mesma função que `_derivar_solo_da_camada` usa — em
                    # vez de uma segunda cópia local do desempate
                    # normativo.
                    perfil_novo = PerfilGeotecnico(
                        camadas=list(perfil.camadas),
                        nivel_agua=perfil.nivel_agua)
                    camada_nova, abaixo_na_novo = _camada_e_abaixo_na(
                        perfil_novo, hf_ramo_b)
                    valores_novos = (camada_nova.gamma(abaixo_na_novo),
                                     camada_nova.phi, camada_nova.coesao)
                    rotulos = ("γ_solo", "φ'", "c'")
                    linhas_divergencia = [
                        f"  • {rotulo}: tela = {da_tela:.10g}, camada "
                        f'"{camada_nova.nome}" em h_f = {hf_ramo_b:.10g} m'
                        f" = {da_camada:.10g}"
                        for rotulo, da_tela, da_camada
                        in zip(rotulos, valores_tela, valores_novos)
                        if da_tela != da_camada
                    ]
                    if linhas_divergencia:
                        msg_perfil += (
                            "\n\nATENÇÃO — divergência entre os valores da "
                            "tela (mantidos, NBR 6122 §7.2) e a camada do "
                            "perfil novo na cota h_f atual:\n"
                            + "\n".join(linhas_divergencia))

        msg_horizontais = ""
        if slots_com_horizontal_zerada:
            msg_horizontais = (
                "\n\nATENÇÃO: esta planilha não tem colunas de Hx/Hy — a "
                f"força horizontal que já estava preenchida em {', '.join(slots_com_horizontal_zerada)} "
                "foi ZERADA pela importação (alivia deslizamento/tombamento "
                "— confira/repreencha se o projeto tem ação horizontal).")

        self._invalidar_resultado(
            "Excel importado — calcule (F5) para atualizar o resultado.")
        messagebox.showinfo(
            "Excel importado",
            f"Pilar e {len(casos)} caso(s) de carga importados de:\n"
            f"{caminho}\n\n{msg_perfil}{msg_horizontais}\n\nO resultado "
            "exibido na tela (se havia algum, de um cálculo anterior) foi "
            "marcado como obsoleto.")

    def _gerar_modelo_excel(self) -> None:
        excel_import = _modulo_excel("excel_import")
        if excel_import is None:
            return
        caminho = filedialog.asksaveasfilename(
            title="Gerar modelo de planilha", defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")])
        if not caminho:
            return
        try:
            excel_import.gerar_modelo_importacao(caminho)
        except Exception as erro:   # noqa: BLE001
            messagebox.showerror("Erro ao gerar modelo",
                                 f"{type(erro).__name__}: {erro}")
            return
        messagebox.showinfo("Modelo gerado",
                            f"Modelo de planilha salvo em:\n{caminho}")

    def _exportar_excel(self) -> None:
        if self._resultado is None or self._sapata is None:
            messagebox.showinfo(
                "Nada para exportar",
                "Calcule a sapata (F5) antes de exportar o relatório em "
                "Excel.")
            return
        excel_export = _modulo_excel("excel_export")
        if excel_export is None:
            return
        caminho = filedialog.asksaveasfilename(
            title="Salvar relatório em Excel", defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")])
        if not caminho:
            return
        try:
            excel_export.exportar_relatorio_excel(
                caminho, self._sapata, self._resultado,
                proveniencia_sigma_adm=self._proveniencia_sigma_adm)
        except Exception as erro:   # noqa: BLE001
            messagebox.showerror("Erro ao exportar Excel",
                                 f"{type(erro).__name__}: {erro}")
            return
        messagebox.showinfo("Excel exportado", f"Relatório salvo em:\n{caminho}")

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
            gerar_memorial_pdf(
                caminho, self._sapata, self._resultado, self._modelo,
                proveniencia_sigma_adm=self._proveniencia_sigma_adm)
        except Exception as erro:   # noqa: BLE001 — mostra ao usuário, não trava
            messagebox.showerror("Erro ao exportar PDF",
                                 f"{type(erro).__name__}: {erro}")
            return
        messagebox.showinfo("PDF exportado", f"Memorial salvo em:\n{caminho}")


def main() -> None:
    AppSapataCompleto().mainloop()


if __name__ == "__main__":
    main()
