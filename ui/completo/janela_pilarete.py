"""
janela_pilarete.py
-------------------
Janela de verificação do pilarete de concreto (`calc_core.estrutural.
pilarete`), backlog #13, rodada 5. Implementa REQ-UI-PILARETE-01 a -12 do
`ruleset.yaml` (bloco `requisitos_para_a3`, versão 14).

Restrição de a3-interface.md (CLAUDE.md regra 4): esta janela NÃO calcula
nada. A lista de chamadas ao núcleo é FECHADA (REQ-UI-PILARETE-12):
`verificar_pilarete`, `classificacao_14_4_1.classificar_faixa` (prévia da
FAIXA), `classificacao_14_4_1.frases_obrigatorias_da_faixa_B` (as duas
frases obrigatórias da FAIXA B, texto pronto do núcleo), `area_barra` (área
da barra a partir da bitola única) e as tuplas de enumeração importadas do
núcleo. Qualquer outra aritmética sobre os campos — conversão de unidade,
área de barra, razão de 14.4.1, comprimento equivalente, gamma_n, momento
mínimo, espaçamento livre — é veto do a6.

DECISÃO DE ARQUITETURA (REQ-UI-PILARETE-01): janela de TOPO NÃO MODAL —
esta classe nunca captura o foco exclusivo da aplicação (sem travar a
janela principal) —, instância ÚNICA gerida pela janela principal do
escopo amplo (ver `app.py`, que abre/foca esta classe e guarda a
referência). Verificação STANDALONE: nada aqui lê ou escreve um campo do
formulário da fundação, e nenhum resultado desta janela alimenta o
cálculo da fundação — os dois motores usam métodos de segurança
diferentes (um valores de cálculo, NBR 6118; o outro valores
característicos com um coeficiente de segurança GLOBAL, NBR 6122) e
misturar os dois é exatamente a mistura de métodos que o núcleo recusa.
Por isso mesmo esta janela também não guarda nenhuma referência ao
formulário da fundação nem a nenhuma classe do motor geotécnico.

PERSISTÊNCIA E EXPORTAÇÃO (REQ-UI-PILARETE-12): as entradas desta janela
NÃO são salvas no `.s7proj` nesta rodada — a janela abre vazia a cada
sessão (avisado na própria tela) — e o memorial desta verificação NÃO
entra no PDF/Excel da sapata. O que esta janela oferece é "copiar" e
"salvar memorial como .txt", com o conteúdo exato de `resultado.memorial()`.

NENHUM DEFAULT SILENCIOSO (REQ-UI-PILARETE-03): dos ~35 campos de
`DadosDoPilarete`, só DOIS têm texto pré-preenchido — `gamma_c` e
`gamma_s`, autorizados por REQ-PILARETE-02(h) — e mesmo esses recusam como
qualquer outro campo se apagados. Todo campo numérico passa por
`_float_requerido`/`_float_opt`; toda enumeração começa vazia (Combobox
`state="readonly"`, sem item pré-selecionado); os seis campos `bool | None`
do núcleo (`secao_constante`, `armadura_constante`,
`condicoes_desfavoraveis_de_execucao`, `idade_maior_ou_igual_28_dias`,
`boa_aderencia`, `armadura_tracionada_em_alguma_combinacao`) são
Combobox readonly de três valores ("", "Sim", "Não") — um `Checkbutton` de
dois estados NÃO representa `None` e está PROIBIDO para estes seis. O
único `Checkbutton` desta janela é o de
`normal_de_compressao_em_todas_as_combinacoes`, que É `bool` puro no
núcleo (default `False`, lado conservador) — nasce desmarcado.

CAMPOS CONDICIONAIS POR RAMO (REQ-UI-PILARETE-04): trocar de ramo ESVAZIA
os campos do ramo abandonado e envia `None`/`False` ao núcleo — nunca um
valor "que ficou na tela e não teve efeito". A FAIXA que decide se o bloco
de cortante aparece vem SEMPRE de `classificacao_14_4_1.classificar_faixa`
(`_faixa_previa`), nunca de uma conta feita aqui.

RECUSA NÃO É REPROVAÇÃO (REQ-UI-PILARETE-08): `RecusaForaDeDominio` (deste
pacote estrutural — classe DIFERENTE de `ForaDoDominioError` do motor
geotécnico) tem tradutor próprio, `_texto_recusa_estrutural`, que só
formata o que a exceção já carrega. Não existe, em lugar nenhum desta
janela, uma opção de confirmar e seguir em frente apesar da recusa.

O VEREDITO MORRE A CADA TECLA (REQ-UI-PILARETE-11): mesma técnica já
aprovada noutra calculadora auxiliar desta interface (a de tensão do
solo) — vigilância por DIFERENÇA de `vars(self)` antes/depois da
montagem dos campos, e não por lista manual.
`self.frame_resultado` é destruído por completo a cada disparo do trace ou
no primeiro passo de `_verificar`; `self.ultimo_resultado` só é gravado
DEPOIS de o desenho ter sido feito. Os botões de copiar/salvar memorial
capturam o `ResultadoPilarete` por FECHAMENTO sobre o texto já formatado,
nunca por um atributo de instância lido depois.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, ttk

from calc_core.estrutural.dominio import (
    DECLARADO_EM_TEXTO,
    DECLARADO_PELO_USUARIO,
    ESCOPO_DESTA_VERSAO,
    NAO_DECLARADO_NA_FONTE,
    RecusaForaDeDominio,
)
from calc_core.estrutural.pilarete import classificacao as classificacao_14_4_1
from calc_core.estrutural.pilarete.cortante import MODELO_II, MODELOS_DE_CALCULO
from calc_core.estrutural.pilarete.elemento import (
    METODO_DE_SEGURANCA_DO_PILARETE,
    DadosDoPilarete,
    ResultadoPilarete,
    verificar_pilarete,
)
from calc_core.estrutural.pilarete.esbeltez import VINCULACOES, VINCULADO_DOIS_EXTREMOS
from calc_core.estrutural.pilarete.geometria import CLASSES_DE_AGRESSIVIDADE
from calc_core.estrutural.pilarete.ligacao import TIPOS_DE_JUNTA
from calc_core.estrutural.pilarete.secao import BarraLongitudinal
from calc_core.sapata_isolada.materiais import area_barra

from . import tema

# =============================================================================
# REQ-UI-PILARETE-02 — colisão de método de segurança e a faixa permanente.
# =============================================================================
AVISO_METODO_DE_CALCULO = (
    "Verificação por VALORES DE CÁLCULO (NBR 6118: ações majoradas por "
    "gamma_f, resistências divididas por gamma_m). Todos os esforços "
    "pedidos aqui são DE CÁLCULO. É PROIBIDO informar o N característico "
    "usado na verificação geotécnica de ELS (método de valores "
    "admissíveis da NBR 6122, Tabela 1): este software NÃO multiplica por "
    "1,4 sozinho, e combinar as ações é responsabilidade do engenheiro, "
    "fora desta tela."
)
"""Faixa permanente, sempre visível, sem depender de aba/seção selecionada."""

# Os cinco rótulos de esforço — cada um carrega "de cálculo" no PRÓPRIO
# rótulo (REQ-UI-PILARETE-02-b), nunca em nota de rodapé à parte.
_ROTULOS_DE_FORCA_ESTRUTURAL: dict[str, str] = {
    DECLARADO_EM_TEXTO: (
        "Limite escrito com todas as letras na NBR 6118:2023 — só muda se "
        "a Norma mudar."),
    DECLARADO_PELO_USUARIO: (
        "Declaração que a Norma exige e que este software não pode "
        "inferir — a ausência da declaração é recusa, não um default."),
    ESCOPO_DESTA_VERSAO: (
        "Limite deste SOFTWARE, não da Norma: a NBR 6118:2023 admite um "
        "domínio maior aqui, e esta versão simplesmente não implementa a "
        "parte fora do limite indicado."),
    NAO_DECLARADO_NA_FONTE: (
        "VAZIO NORMATIVO: a NBR 6118:2023 é silente sobre este caso e não "
        "há rota alternativa no acervo deste software — não existe "
        "caminho, o que é diferente de dizer apenas que o software não "
        "faz."),
}
"""As QUATRO forças de guarda do motor estrutural (REQ-UI-PILARETE-08-b)."""

TEXTO_CRUZAMENTO_COBRIMENTO = (
    "O cobrimento declarado é o que se compara com o mínimo da Tabela 7.2 "
    "(durabilidade). As posições das barras são de onde saem o d' de "
    "§17.4 (e portanto V_Rd2 e V_c0) e os braços de alavanca de §17.2. Os "
    "dois descrevem a MESMA distância e o software os CRUZA: se as barras "
    "implicarem cobrimento MENOR que o declarado, a verificação é "
    "RECUSADA — declarar 45 mm e posicionar as barras como se fossem "
    "30 mm dá d maior, V_Rd2 maior e M_Rd maior, do lado INSEGURO."
)
"""REQ-UI-PILARETE-05: por que cobrimento e posições são DOIS canais."""

TEXTO_ESPACAMENTO_NAO_CONFERIDO = (
    "O núcleo CRUZA este valor com as posições declaradas acima "
    "(REQ-PILARETE-20-c): o declarado tem de ser <= o MENOR espaçamento "
    "real entre eixos das barras (senão RECUSA), e é o MAIOR espaçamento "
    "real — não o declarado — que é comparado com o teto de 18.4.2.2. "
    "Declare o valor verdadeiro, nunca um número \"seguro\" arbitrário: "
    "esta janela não posiciona nada por você."
)
"""REQ-UI-PILARETE-06(4): aviso junto ao espaçamento entre eixos, atualizado
para o cruzamento que REQ-PILARETE-20 acrescentou ao núcleo (commit
1861586) — ver `exigir_armadura_consistente_com_as_barras`,
`geometria.py`."""

TEXTO_H_ZERO_EXATO = (
    "H_x e H_y são OBRIGATÓRIOS e comparados com ZERO EXATO, sem "
    "tolerância: \"0\" e \"0,001\" são declarações DIFERENTES, e não "
    "existe faixa de \"H desprezível\". Esta janela não zera a componente "
    "menor, não compõe resultante e não oferece \"usar só a maior\"."
)
"""REQ-UI-PILARETE-04: aviso junto aos dois campos de força horizontal."""

TEXTO_ROTULO_N_GAMMA_F_1 = (
    "N na combinação com gamma_f = 1,0 [kN] — NÃO é o N_d acima. É a "
    "mesma combinação, no nível de carregamento sem majoração das ações, "
    "e serve só ao numerador de M_0 (NBR 6118, 17.4.2.2-b)"
)
"""REQ-UI-PILARETE-10-b: rótulo que distingue N_(gamma_f=1,0) do N_d."""

TEXTO_N_GAMMA_F_1_EM_BRANCO = (
    "Em branco: a majoração de V_c pela compressão NÃO será aplicada "
    "(lado conservador)."
)
"""REQ-UI-PILARETE-10-c: consequência do campo vazio, junto ao campo."""

TEXTO_ROTULO_A_S_CALCULADA = (
    "A_s calculada [m²] (opcional; em branco, sem redução de ell_b,nec — "
    "A_s,calc = A_s,ef, lado conservador)"
)
"""REQ-UI-PILARETE-04, GRUPO 3: único campo opcional legítimo da janela."""

TEXTO_FAIXA_INDETERMINADA = (
    "Prévia da FAIXA de 14.4.1 ainda não pôde ser determinada — preencha "
    "ell, h_secao e b_secao com números positivos para saber se o "
    "cortante (§17.4) se aplica a este pilarete."
)
"""REQ-UI-PILARETE-04: o grupo 4 fica fechado, mas nunca sem dizer por quê."""

TEXTO_BITOLA_UNICA = (
    "Bitola ÚNICA: esta janela não aceita bitolas mistas — o núcleo "
    "verifica TODO o detalhamento (espaçamento, cobrimento implícito, "
    "ancoragem) contra um phi_longitudinal ÚNICO. A área de CADA barra "
    "vem do núcleo (área da bitola declarada), nunca digitada aqui."
)
"""REQ-UI-PILARETE-06(1): por que não há campo de área/bitola por barra."""

AVISO_PERSISTENCIA = (
    "As entradas do pilarete não são salvas no projeto (.s7proj) nesta "
    "versão: esta janela abre vazia a cada sessão, e nenhum campo aqui "
    "sobrevive a fechar e reabrir. Use \"Copiar\" ou \"Salvar memorial "
    "como .txt\" antes de fechar para não perder o resultado desta "
    "verificação — o memorial do pilarete também NÃO entra no PDF/Excel "
    "da sapata."
)
"""REQ-UI-PILARETE-12: aviso FIXO (rodapé, fora do frame de resultado, não
depende de nenhuma verificação ter rodado) — motivo do ALTA do GATE 2,
rodada 1: o aviso existia só no docstring do módulo, não em widget algum."""

_TRI_ESTADO_VALORES = ("", "Sim", "Não")


def _tri_estado_para_bool_opt(texto: str) -> bool | None:
    """Converte o texto do Combobox tri-estado em `bool | None`.

    "" (nada declarado) -> `None`, que o núcleo recusa nomeando o campo e
    o item normativo — nunca um default silencioso (REQ-UI-PILARETE-03-3).
    """
    if texto == "Sim":
        return True
    if texto == "Não":
        return False
    return None


def _float_requerido(rotulo: str, valor: str) -> float:
    """Campo numérico obrigatório: VAZIO é ERRO, nunca um valor plausível.

    Mesma semântica já aprovada noutra calculadora auxiliar desta
    interface (MÉDIA #3 do GATE 2 correspondente, reaproveitada aqui de
    propósito): a mensagem NOMEIA o campo e diz que esta janela não
    completa um campo em branco por conta própria.
    """
    texto = (valor or "").strip().replace(",", ".")
    if not texto:
        raise ValueError(
            f"Campo obrigatório vazio: \"{rotulo}\". Esta janela nunca "
            "completa um campo em branco com um número por conta própria.")
    return float(texto)


def _float_opt(valor: str) -> float | None:
    """Campo numérico OPCIONAL (só `A_s_calculada` e `N_gamma_f_1`).

    Vazio devolve `None` (legítimo); texto não numérico ainda levanta
    `ValueError` — o campo é opcional quanto à AUSÊNCIA, não quanto a
    conter lixo não numérico.
    """
    texto = (valor or "").strip().replace(",", ".")
    return float(texto) if texto else None


def _float_previa(valor: str) -> float | None:
    """Leitura NÃO-BLOQUEANTE para prévias vivas (`_faixa_previa`).

    Diferente de `_float_opt`: aqui um texto vazio OU não numérico (estado
    normal de quem ainda está digitando, ex. "1." ou "-") devolve `None`
    em vez de levantar — a prévia da FAIXA não pode lançar uma caixa de
    erro a cada tecla (REQ-UI-PILARETE-04, critério "não há exceção nem
    messagebox a cada tecla digitada").
    """
    texto = (valor or "").strip().replace(",", ".")
    if not texto:
        return None
    try:
        return float(texto)
    except ValueError:
        return None


def _texto_recusa_estrutural(erro: RecusaForaDeDominio) -> str:
    """Formata uma `RecusaForaDeDominio` do motor estrutural (REQ-UI-PILARETE-08).

    Só formata o que a exceção já carrega (`parametro`, `valor`,
    `intervalo`, `fonte`, `forca`, `sugestao`) — nenhum juízo sobre o
    domínio é feito aqui, e capturar isto como "erro de cálculo" genérico
    é o que este tradutor existe para evitar.
    """
    linhas = [
        (f"RECUSADO — {erro.parametro} = {erro.valor!r} fora do domínio "
         f"declarado ({erro.intervalo})."),
        f"Fonte do limite: {erro.fonte}",
        _ROTULOS_DE_FORCA_ESTRUTURAL.get(erro.forca, erro.forca),
    ]
    if erro.sugestao:
        linhas.append(erro.sugestao)
    return "\n\n".join(linhas)


class JanelaPilarete(tk.Toplevel):
    """Verificação STANDALONE do pilarete de concreto (NBR 6118:2023).

    Janela de topo NÃO MODAL (REQ-UI-PILARETE-01) — não captura o foco
    exclusivo da aplicação. A instância é gerida pela janela principal do
    escopo amplo (atributo de classe + método de abertura/foco lá): reabrir
    com a janela já aberta traz a existente para a frente, nunca constrói
    uma segunda.
    """

    ultimo_resultado: ResultadoPilarete | None = None
    """Atributo de CLASSE, default `None`. Só é gravado DEPOIS de o
    desenho do resultado ter sido feito (`_verificar`), e é zerado por
    `_invalidar_resultado` a cada edição — nunca um resultado "congelado"
    sobrevivendo a uma mudança de entrada (REQ-UI-PILARETE-11)."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.title("Verificação do pilarete de concreto (NBR 6118:2023)")
        self.configure(bg=tema.FUNDO_PAINEL)
        self.geometry("900x840")
        self.minsize(760, 560)
        # Sem travar a janela principal nem capturar o foco exclusivo da
        # aplicação: janela de topo independente — o engenheiro pode
        # continuar consultando a tela da fundação com esta janela aberta
        # (REQ-UI-PILARETE-01).

        self.ultimo_resultado = None
        self._linhas_barras: list[dict[str, object]] = []
        """Uma entrada por barra da tabela: {"frame", "pos_h", "pos_b"}.
        NÃO são `tk.Variable` capturadas pela vigilância em massa de
        `_vigiar_entradas` — os três pontos de edição (adicionar, editar,
        remover) chamam `_invalidar_resultado` explicitamente
        (REQ-UI-PILARETE-11-c)."""

        self._montar()

    # ============================================================ montagem
    def _montar(self) -> None:
        ttk.Label(self, text=AVISO_METODO_DE_CALCULO, style="Banner.TLabel",
                  wraplength=880, justify="left", padding=(10, 6)).pack(
            fill="x")

        # REQ-UI-PILARETE-12: rodapé FIXO fora da área rolável — visível
        # sempre, nunca dentro de `frame_resultado` (não depende de
        # nenhuma verificação ter rodado). Empacotado ANTES da área
        # rolável para reservar a faixa inferior da janela.
        ttk.Label(self, text=AVISO_PERSISTENCIA, style="Banner.TLabel",
                  wraplength=880, justify="left", padding=(10, 6)).pack(
            side="bottom", fill="x")

        interior = self._area_rolavel(self)

        # REQ-UI-PILARETE-11-b: vigilância por DIFERENÇA de `vars(self)`,
        # não por lista manual — qualquer campo novo entra sozinho.
        variaveis = self._construir_e_capturar_variaveis(
            lambda: self._montar_campos(interior))
        self._vigiar_entradas(variaveis)

        # `interior` já é grade (as seis seções de `_montar_campos` usam
        # `.grid()`) — o botão e a área de resultado continuam na MESMA
        # grade em vez de `.pack()`, que o Tk proíbe misturar no mesmo pai.
        ttk.Button(interior, text="Verificar", style="Acento.TButton",
                   command=self._verificar).grid(
            row=6, column=0, sticky="w", padx=10, pady=(4, 10))

        self.frame_resultado = ttk.Frame(interior, style="Painel.TFrame")
        self.frame_resultado.grid(row=7, column=0, sticky="nsew", padx=6,
                                  pady=(0, 12))
        interior.rowconfigure(7, weight=1)

        # Estado inicial dos blocos condicionais (REQ-UI-PILARETE-04):
        # todos começam vazios, logo todos começam fechados/escondidos.
        self._ao_mudar_vinculacao()
        self._ao_mudar_modelo()
        self._atualizar_grupo4_por_faixa()

    def _area_rolavel(self, master: tk.Misc) -> ttk.Frame:
        """Canvas + scrollbar — mesmo padrão já usado no painel de entrada
        principal e noutra calculadora auxiliar desta interface."""
        canvas = tk.Canvas(master, bg=tema.FUNDO_PAINEL, highlightthickness=0)
        barra = ttk.Scrollbar(master, orient="vertical", command=canvas.yview)
        interior = ttk.Frame(canvas, style="Painel.TFrame")

        janela = canvas.create_window((0, 0), window=interior, anchor="nw")
        interior.bind("<Configure>",
                       lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfigure(janela, width=e.width))
        canvas.configure(yscrollcommand=barra.set)

        def _roda(ev: tk.Event) -> None:
            canvas.yview_scroll(-1 if ev.delta > 0 else 1, "units")

        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _roda))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        canvas.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        return interior

    def _construir_e_capturar_variaveis(self, construir) -> list[tk.Variable]:
        """Chama `construir()` e devolve toda `tk.Variable` que a chamada
        acabou de atribuir a `self`, por DIFERENÇA de `vars(self)` antes/
        depois — não por lista manual (REQ-UI-PILARETE-11-b, mesma técnica
        já aprovada noutra calculadora auxiliar desta interface)."""
        antes = set(vars(self))
        construir()
        return [valor for nome, valor in vars(self).items()
                if nome not in antes and isinstance(valor, tk.Variable)]

    def _vigiar_entradas(self, variaveis: list[tk.Variable]) -> None:
        for variavel in variaveis:
            variavel.trace_add("write", self._invalidar_resultado)

    def _invalidar_resultado(self, *_args: object) -> None:
        """Destrói TODO o conteúdo de `frame_resultado` e zera o resultado.

        Chamado pelo trace de qualquer campo de entrada e explicitamente
        pelos três pontos de edição da tabela de barras. O que restar na
        tela depois de uma edição é ilegal (REQ-UI-PILARETE-11-a)."""
        for filho in self.frame_resultado.winfo_children():
            filho.destroy()
        self.ultimo_resultado = None

    # ------------------------------------------------------------ campos
    def _montar_campos(self, pai: ttk.Frame) -> None:
        pai.columnconfigure(0, weight=1)
        self._secao_geometria(pai)
        self._secao_materiais(pai)
        self._secao_durabilidade_e_armadura(pai)
        self._secao_solicitacoes(pai)
        self._secao_ligacao(pai)
        self._secao_cortante(pai)

    def _campo(self, pai: ttk.Frame, row: int, rotulo: str,
               largura: int = 12, valor_inicial: str = "") -> tk.StringVar:
        ttk.Label(pai, text=rotulo, style="PainelFraco.TLabel",
                  wraplength=320, justify="left").grid(
            row=row, column=0, sticky="w", padx=(8, 4), pady=2)
        var = tk.StringVar(value=valor_inicial)
        ttk.Entry(pai, textvariable=var, width=largura).grid(
            row=row, column=1, sticky="w", padx=(0, 8), pady=2)
        return var

    def _combo_vazio(self, pai: ttk.Frame, row: int, rotulo: str, valores,
                      largura: int = 26) -> tk.StringVar:
        """Combobox `readonly` sem item pré-selecionado — pré-selecionar o
        primeiro item escolheria pelo projetista exatamente o que
        `exigir_um_de` existe para não deixar ninguém escolher (REQ-UI-
        PILARETE-03-2). `valores` é usado diretamente (nunca reescrito
        como string nova), sempre uma tupla importada do núcleo."""
        ttk.Label(pai, text=rotulo, style="PainelFraco.TLabel",
                  wraplength=320, justify="left").grid(
            row=row, column=0, sticky="w", padx=(8, 4), pady=2)
        var = tk.StringVar(value="")
        ttk.Combobox(pai, textvariable=var, state="readonly", width=largura,
                     values=list(valores)).grid(
            row=row, column=1, sticky="w", padx=(0, 8), pady=2)
        return var

    def _tri_estado(self, pai: ttk.Frame, row: int, rotulo: str) -> tk.StringVar:
        """Os SEIS campos `bool | None` do núcleo passam por aqui — nunca
        por um `ttk.Checkbutton` (REQ-UI-PILARETE-03-3)."""
        return self._combo_vazio(pai, row, rotulo, _TRI_ESTADO_VALORES,
                                  largura=8)

    def _texto_explicativo(self, pai: ttk.Frame, row: int, texto: str,
                            columnspan: int = 2) -> None:
        ttk.Label(pai, text=texto, style="PainelFraco.TLabel", wraplength=580,
                  justify="left", font=("Segoe UI", 8)).grid(
            row=row, column=0, columnspan=columnspan, sticky="w", padx=8,
            pady=(0, 6))

    # -------------------------------------------------------- 1. geometria
    def _secao_geometria(self, pai: ttk.Frame) -> None:
        f = ttk.LabelFrame(
            pai, text="Geometria e vinculação (13.2.3, 15.6, 15.8.1-15.8.2)")
        f.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
        f.columnconfigure(1, weight=1)

        self.v_h_secao = self._campo(f, 0, "h_secao [m]")
        self.v_b_secao = self._campo(f, 1, "b_secao [m]")
        self.v_ell = self._campo(f, 2, "ell — comprimento longitudinal REAL [m]")
        self.v_vinculacao = self._combo_vazio(
            f, 3, "Vinculação (15.4.4 / 15.6 / 15.8.2)", VINCULACOES)
        self.v_secao_constante = self._tri_estado(
            f, 4, "Seção constante ao longo do eixo (15.8.1)")
        self.v_armadura_constante = self._tri_estado(
            f, 5, "Armadura constante ao longo do eixo (15.8.1)")

        # GRUPO 1 (REQ-UI-PILARETE-04): só existe com VINCULADO_DOIS_EXTREMOS.
        self._frame_vinculado = ttk.LabelFrame(
            f, text="Só com vinculação VINCULADO_DOIS_EXTREMOS (15.6) — "
                    "com ENGASTADO_BASE_LIVRE_TOPO a própria Norma escreve "
                    "ell_e = 2·ell e o número vem do núcleo")
        self._frame_vinculado.grid(row=6, column=0, columnspan=2, sticky="ew",
                                    padx=8, pady=(4, 8))
        self.v_ell_e = self._campo(self._frame_vinculado, 0,
                                    "ell_e declarado [m]")
        self.v_ell_0 = self._campo(self._frame_vinculado, 1, "ell_0 [m]")
        self.v_vinculacao.trace_add("write", self._ao_mudar_vinculacao)

    def _ao_mudar_vinculacao(self, *_args: object) -> None:
        if self.v_vinculacao.get() == VINCULADO_DOIS_EXTREMOS:
            self._frame_vinculado.grid()
        else:
            self.v_ell_e.set("")
            self.v_ell_0.set("")
            self._frame_vinculado.grid_remove()

    # -------------------------------------------------------- 2. materiais
    def _secao_materiais(self, pai: ttk.Frame) -> None:
        f = ttk.LabelFrame(
            pai, text="Materiais — campos PRÓPRIOS do pilarete "
                      "(8.2.10.1, 12.3.1, 12.4.1)")
        f.grid(row=1, column=0, sticky="ew", padx=6, pady=(0, 6))
        f.columnconfigure(1, weight=1)

        self.v_fck = self._campo(f, 0, "f_ck [MPa] (classe normalizada C20-C90)")
        # REQ-UI-PILARETE-03-5: os DOIS ÚNICOS campos com texto
        # pré-preenchido — apagados, recusam como qualquer outro.
        self.v_gamma_c = self._campo(f, 1, "gamma_c base (Tabela 12.1)",
                                     valor_inicial="1,4")
        self.v_condicoes_desfav = self._tri_estado(
            f, 2, "Condições desfavoráveis de execução (12.4.1)")
        self.v_fyk_long = self._campo(f, 3, "f_yk longitudinal [MPa]")
        self.v_fyk_estribo = self._campo(f, 4, "f_yk do estribo [MPa]")
        self.v_gamma_s = self._campo(f, 5, "gamma_s (Tabela 12.1)",
                                     valor_inicial="1,15")
        self.v_idade_28 = self._tri_estado(
            f, 6, "Idade j >= 28 dias na verificação (12.3.3)")

    # ------------------------------------------ 3. durabilidade/armadura
    def _secao_durabilidade_e_armadura(self, pai: ttk.Frame) -> None:
        f = ttk.LabelFrame(
            pai, text="Durabilidade e detalhamento (Tabela 7.2, 18.4.2, 18.4.3)")
        f.grid(row=2, column=0, sticky="ew", padx=6, pady=(0, 6))
        f.columnconfigure(1, weight=1)

        self.v_classe_agressividade = self._combo_vazio(
            f, 0, "Classe de agressividade ambiental (CAA)",
            CLASSES_DE_AGRESSIVIDADE, largura=6)
        self.v_d_agregado = self._campo(f, 1, "d_agregado — dimensão máxima [mm]")
        self.v_cobrimento = self._campo(f, 2, "Cobrimento DECLARADO [mm]")
        self.v_phi_long = self._campo(f, 3, "phi_longitudinal — bitola ÚNICA [mm]")
        self._texto_explicativo(f, 4, TEXTO_BITOLA_UNICA)
        self.v_espacamento_eixos = self._campo(f, 5, "Espaçamento entre eixos [mm]")
        self._texto_explicativo(f, 6, TEXTO_ESPACAMENTO_NAO_CONFERIDO)
        self.v_phi_t = self._campo(f, 7, "phi_t — diâmetro do estribo [mm]")
        self.v_s_estribo = self._campo(f, 8, "s — espaçamento do estribo [mm]")

        self._texto_explicativo(f, 9, TEXTO_CRUZAMENTO_COBRIMENTO)

        bloco_barras = ttk.Frame(f, style="Painel.TFrame")
        bloco_barras.grid(row=10, column=0, columnspan=2, sticky="ew",
                          padx=8, pady=(2, 8))
        ttk.Label(
            bloco_barras,
            text="Barras longitudinais — POSIÇÕES REAIS (convenção de "
                 "BarraLongitudinal: pos_h/pos_b medidos a partir das "
                 "bordas de referência; mínimo de 1 barra por vértice, "
                 "isto é, 4 na seção retangular — quem reprova por isso é "
                 "o núcleo, não esta janela).",
            style="PainelFraco.TLabel", wraplength=580, justify="left").pack(
            anchor="w")
        self._frame_tabela_barras = ttk.Frame(bloco_barras, style="Painel.TFrame")
        self._frame_tabela_barras.pack(fill="x", anchor="w", pady=(4, 4))
        ttk.Button(bloco_barras, text="+ Adicionar barra",
                   command=self._adicionar_barra).pack(anchor="w")

    def _adicionar_barra(self) -> None:
        """Um dos TRÊS pontos de edição da tabela de barras que invalidam
        o resultado explicitamente (REQ-UI-PILARETE-11-c) — a tabela não
        é uma `tk.Variable`, logo não é coberta pela vigilância em massa."""
        linha = ttk.Frame(self._frame_tabela_barras, style="Painel.TFrame")
        linha.pack(anchor="w", fill="x", pady=1)
        indice = len(self._linhas_barras) + 1

        ttk.Label(linha, text=f"Barra {indice}:", style="PainelFraco.TLabel",
                  width=9).pack(side="left")
        ttk.Label(linha, text="pos_h [m]", style="PainelFraco.TLabel").pack(
            side="left", padx=(6, 2))
        v_h = tk.StringVar(value="")
        ttk.Entry(linha, textvariable=v_h, width=9).pack(side="left")
        ttk.Label(linha, text="pos_b [m]", style="PainelFraco.TLabel").pack(
            side="left", padx=(10, 2))
        v_b = tk.StringVar(value="")
        ttk.Entry(linha, textvariable=v_b, width=9).pack(side="left")

        registro: dict[str, object] = {"frame": linha, "pos_h": v_h, "pos_b": v_b}
        ttk.Button(linha, text="Remover",
                   command=lambda r=registro: self._remover_barra(r)).pack(
            side="left", padx=(10, 0))

        v_h.trace_add("write", self._invalidar_resultado)
        v_b.trace_add("write", self._invalidar_resultado)
        self._linhas_barras.append(registro)
        self._invalidar_resultado()

    def _remover_barra(self, registro: dict[str, object]) -> None:
        registro["frame"].destroy()   # type: ignore[union-attr]
        self._linhas_barras.remove(registro)
        self._invalidar_resultado()

    # ----------------------------------------------------- 4. solicitações
    def _secao_solicitacoes(self, pai: ttk.Frame) -> None:
        f = ttk.LabelFrame(pai, text="Solicitações DE CÁLCULO (17.2, 17.4)")
        f.grid(row=3, column=0, sticky="ew", padx=6, pady=(0, 6))
        f.columnconfigure(1, weight=1)

        self.v_Nd = self._campo(f, 0, "N_d [kN] (de cálculo)")
        self.v_MSdx = self._campo(f, 1, "M_Sd,x [kN·m] (de cálculo)")
        self.v_MSdy = self._campo(f, 2, "M_Sd,y [kN·m] (de cálculo)")
        self.v_Hx = self._campo(f, 3, "H_x [kN] (de cálculo)")
        self.v_Hy = self._campo(f, 4, "H_y [kN] (de cálculo)")
        self._texto_explicativo(f, 5, TEXTO_H_ZERO_EXATO)

    # -------------------------------------------------------- 5. ligação
    def _secao_ligacao(self, pai: ttk.Frame) -> None:
        f = ttk.LabelFrame(pai, text="Ligação com a sapata (9.5.2.x, 21.6)")
        f.grid(row=4, column=0, sticky="ew", padx=6, pady=(0, 6))
        f.columnconfigure(1, weight=1)

        self.v_tipo_junta = self._combo_vazio(
            f, 0, "Tipo de junta de concretagem (21.6)", TIPOS_DE_JUNTA,
            largura=32)
        self.v_boa_aderencia = self._tri_estado(
            f, 1, "Boa aderência da espera (9.3.2.1)")
        self.v_armadura_tracionada = self._tri_estado(
            f, 2, "Armadura tracionada em alguma combinação (9.5.2.1)")
        self.v_As_calculada = self._campo(f, 3, TEXTO_ROTULO_A_S_CALCULADA,
                                          largura=10)

    # -------------------------------------------------------- 6. cortante
    def _secao_cortante(self, pai: ttk.Frame) -> None:
        f = ttk.LabelFrame(
            pai, text="Cortante (§17.4) — só existe na FAIXA A de 14.4.1")
        f.grid(row=5, column=0, sticky="ew", padx=6, pady=(0, 6))
        f.columnconfigure(1, weight=1)

        self._label_grupo4_fechado = ttk.Label(
            f, text="", style="PainelFraco.TLabel", foreground=tema.AMARELO,
            wraplength=580, justify="left")
        self._label_grupo4_fechado.grid(row=0, column=0, columnspan=2,
                                        sticky="w", padx=8, pady=8)

        self._frame_grupo4_cortante = ttk.Frame(f, style="Painel.TFrame")
        self._frame_grupo4_cortante.grid(row=1, column=0, columnspan=2,
                                         sticky="ew")
        g = self._frame_grupo4_cortante
        g.columnconfigure(1, weight=1)

        self.v_modelo_calculo = self._combo_vazio(
            g, 0, "Modelo de cálculo (17.4.2)", MODELOS_DE_CALCULO, largura=14)

        # Sub-grupo 2: theta_biela só existe com MODELO_II.
        self._frame_theta = ttk.Frame(g, style="Painel.TFrame")
        self._frame_theta.grid(row=1, column=0, columnspan=2, sticky="ew")
        self._frame_theta.columnconfigure(1, weight=1)
        self.v_theta_biela = self._campo(
            self._frame_theta, 0,
            "theta_biela [graus] (só Modelo II; entre 30° e 45°)")
        self.v_modelo_calculo.trace_add("write", self._ao_mudar_modelo)

        self.v_alpha_estribo = self._campo(
            g, 2, "alpha_estribo [graus] (90° nesta versão de escopo)")
        self.v_Asw_s = self._campo(
            g, 3,
            "A_sw/s [m²/m] (área de armadura transversal por comprimento; "
            "2 ramos phi 5,0 mm a cada 12,5 cm = 3,1416e-4 m²/m)",
            largura=14)
        self.v_N_gamma_f_1 = self._campo(g, 4, TEXTO_ROTULO_N_GAMMA_F_1,
                                         largura=10)
        self._texto_explicativo(g, 5, TEXTO_N_GAMMA_F_1_EM_BRANCO)

        self.v_normal_compressao = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            g, text="Marque apenas se a força normal for de COMPRESSÃO em "
                    "TODAS as combinações (NBR 6118, 17.4.1.1.2-c). "
                    "Desmarcado, a dispensa de armadura transversal mínima "
                    "NÃO é considerada — lado conservador.",
            variable=self.v_normal_compressao).grid(
            row=6, column=0, columnspan=2, sticky="w", padx=8, pady=(4, 8))

        # A FAIXA vem SEMPRE do núcleo — nunca de uma razão calculada
        # aqui (REQ-UI-PILARETE-04).
        self.v_h_secao.trace_add("write", self._atualizar_grupo4_por_faixa)
        self.v_b_secao.trace_add("write", self._atualizar_grupo4_por_faixa)
        self.v_ell.trace_add("write", self._atualizar_grupo4_por_faixa)

    def _ao_mudar_modelo(self, *_args: object) -> None:
        if self.v_modelo_calculo.get() == MODELO_II:
            self._frame_theta.grid()
        else:
            self.v_theta_biela.set("")
            self._frame_theta.grid_remove()

    def _classificacao_previa(self):
        """Lê `classificacao_14_4_1.classificar_faixa` com os três campos
        de geometria — a ÚNICA fonte da prévia (REQ-UI-PILARETE-04). Nunca
        levanta: geometria inválida/incompleta devolve `None`."""
        ell = _float_previa(self.v_ell.get())
        h_secao = _float_previa(self.v_h_secao.get())
        b_secao = _float_previa(self.v_b_secao.get())
        if ell is None or h_secao is None or b_secao is None:
            return None
        try:
            return classificacao_14_4_1.classificar_faixa(
                ell=ell, h_secao=h_secao, b_secao=b_secao)
        except RecusaForaDeDominio:
            return None

    def _faixa_previa(self) -> str | None:
        """Prévia (não autoritativa) da FAIXA de 14.4.1 — `None` quando
        ell/h_secao/b_secao ainda não formam números válidos. A
        AUTORITATIVA é `ResultadoPilarete.faixa`, só depois de verificar."""
        classificacao = self._classificacao_previa()
        return classificacao.faixa if classificacao is not None else None

    def _atualizar_grupo4_por_faixa(self, *_args: object) -> None:
        classificacao = self._classificacao_previa()
        if classificacao is None:
            self._mostrar_grupo4(False, TEXTO_FAIXA_INDETERMINADA)
            return
        if classificacao.faixa == classificacao_14_4_1.FAIXA_A_ELEMENTO_LINEAR:
            self._mostrar_grupo4(True)
            return
        texto = (
            "Prévia (NBR 6118:2023, 14.4.1): FAIXA B — razão comprimento/"
            f"maior dimensão = {classificacao.razao_14_4_1:.4f} contra o "
            f"limite de {classificacao_14_4_1.LIMITE_14_4_1:.1f}. Este "
            "pilarete NÃO satisfaz a definição de elemento linear: o ELU "
            "de força cortante (§17.4) não é verificado nesta janela.")
        self._mostrar_grupo4(False, texto)

    def _mostrar_grupo4(self, mostrar: bool, texto_fechado: str = "") -> None:
        if mostrar:
            self._label_grupo4_fechado.grid_remove()
            self._frame_grupo4_cortante.grid()
            return
        self._frame_grupo4_cortante.grid_remove()
        self._esvaziar_grupo4()
        self._label_grupo4_fechado.configure(text=texto_fechado)
        self._label_grupo4_fechado.grid()

    def _esvaziar_grupo4(self) -> None:
        """Ramo abandonado -> campos ESVAZIADOS (REQ-UI-PILARETE-04): o que
        a tela EXIBE é o que a tela ENVIA ao núcleo."""
        self.v_modelo_calculo.set("")
        self.v_theta_biela.set("")
        self.v_alpha_estribo.set("")
        self.v_Asw_s.set("")
        self.v_N_gamma_f_1.set("")
        self.v_normal_compressao.set(False)

    # =============================================================== dados
    def _ler_barras(self, phi_longitudinal_mm: float) -> tuple[BarraLongitudinal, ...]:
        """A ÁREA vem de `area_barra` (núcleo, REQ-UI-PILARETE-06-2); a
        CONTAGEM é `len(barras)` (REQ-UI-PILARETE-06-3) — não há campo de
        "número de barras" nesta janela."""
        area = area_barra(phi_longitudinal_mm)
        barras: list[BarraLongitudinal] = []
        for indice, linha in enumerate(self._linhas_barras, start=1):
            pos_h = _float_requerido(f"barra {indice} — pos_h [m]",
                                     linha["pos_h"].get())   # type: ignore[union-attr]
            pos_b = _float_requerido(f"barra {indice} — pos_b [m]",
                                     linha["pos_b"].get())   # type: ignore[union-attr]
            barras.append(BarraLongitudinal(pos_h=pos_h, pos_b=pos_b, area=area))
        return tuple(barras)

    def _construir_dados(self) -> DadosDoPilarete:
        """Só COLETA e FORMATA (CLAUDE.md regra 4) — quem decide se a
        combinação é válida é sempre `verificar_pilarete`, chamado por
        `_verificar` logo em seguida."""
        h_secao = _float_requerido("h_secao [m]", self.v_h_secao.get())
        b_secao = _float_requerido("b_secao [m]", self.v_b_secao.get())
        ell = _float_requerido(
            "ell — comprimento longitudinal REAL [m]", self.v_ell.get())
        vinculacao = self.v_vinculacao.get()
        secao_constante = _tri_estado_para_bool_opt(self.v_secao_constante.get())
        armadura_constante = _tri_estado_para_bool_opt(
            self.v_armadura_constante.get())

        if vinculacao == VINCULADO_DOIS_EXTREMOS:
            ell_e_declarado = _float_requerido(
                "ell_e declarado [m]", self.v_ell_e.get())
            ell_0 = _float_requerido("ell_0 [m]", self.v_ell_0.get())
        else:
            ell_e_declarado = None
            ell_0 = None

        f_ck_MPa = _float_requerido("f_ck [MPa]", self.v_fck.get())
        gamma_c_base = _float_requerido(
            "gamma_c base (Tabela 12.1)", self.v_gamma_c.get())
        condicoes_desfavoraveis_de_execucao = _tri_estado_para_bool_opt(
            self.v_condicoes_desfav.get())
        f_yk_longitudinal_MPa = _float_requerido(
            "f_yk longitudinal [MPa]", self.v_fyk_long.get())
        f_yk_estribo_MPa = _float_requerido(
            "f_yk do estribo [MPa]", self.v_fyk_estribo.get())
        gamma_s = _float_requerido("gamma_s (Tabela 12.1)", self.v_gamma_s.get())
        idade_maior_ou_igual_28_dias = _tri_estado_para_bool_opt(
            self.v_idade_28.get())

        classe_de_agressividade = self.v_classe_agressividade.get()
        d_agregado_mm = _float_requerido(
            "d_agregado — dimensão máxima [mm]", self.v_d_agregado.get())
        cobrimento_declarado_mm = _float_requerido(
            "Cobrimento DECLARADO [mm]", self.v_cobrimento.get())
        phi_longitudinal_mm = _float_requerido(
            "phi_longitudinal — bitola ÚNICA [mm]", self.v_phi_long.get())
        espacamento_entre_eixos_mm = _float_requerido(
            "Espaçamento entre eixos [mm]", self.v_espacamento_eixos.get())
        phi_t_mm = _float_requerido(
            "phi_t — diâmetro do estribo [mm]", self.v_phi_t.get())
        s_estribo_mm = _float_requerido(
            "s — espaçamento do estribo [mm]", self.v_s_estribo.get())

        barras = self._ler_barras(phi_longitudinal_mm)
        numero_de_barras = len(barras)

        N_d = _float_requerido("N_d [kN] (de cálculo)", self.v_Nd.get())
        M_Sd_x = _float_requerido("M_Sd,x [kN·m] (de cálculo)", self.v_MSdx.get())
        M_Sd_y = _float_requerido("M_Sd,y [kN·m] (de cálculo)", self.v_MSdy.get())
        H_x = _float_requerido("H_x [kN] (de cálculo)", self.v_Hx.get())
        H_y = _float_requerido("H_y [kN] (de cálculo)", self.v_Hy.get())

        tipo_de_junta = self.v_tipo_junta.get()
        boa_aderencia = _tri_estado_para_bool_opt(self.v_boa_aderencia.get())
        armadura_tracionada_em_alguma_combinacao = _tri_estado_para_bool_opt(
            self.v_armadura_tracionada.get())
        A_s_calculada = _float_opt(self.v_As_calculada.get())

        faixa_atual = self._faixa_previa()
        permite_cortante = (
            faixa_atual == classificacao_14_4_1.FAIXA_A_ELEMENTO_LINEAR)
        if permite_cortante:
            modelo_de_calculo = self.v_modelo_calculo.get()
            if modelo_de_calculo == MODELO_II:
                theta_biela_graus = _float_requerido(
                    "theta_biela [graus]", self.v_theta_biela.get())
            else:
                theta_biela_graus = None
            alpha_estribo_graus = _float_requerido(
                "alpha_estribo [graus]", self.v_alpha_estribo.get())
            A_sw_por_s = _float_requerido("A_sw/s [m²/m]", self.v_Asw_s.get())
            N_gamma_f_1 = _float_opt(self.v_N_gamma_f_1.get())
            normal_de_compressao_em_todas_as_combinacoes = (
                self.v_normal_compressao.get())
        else:
            modelo_de_calculo = None
            theta_biela_graus = None
            alpha_estribo_graus = None
            A_sw_por_s = None
            N_gamma_f_1 = None
            normal_de_compressao_em_todas_as_combinacoes = False

        return DadosDoPilarete(
            h_secao=h_secao, b_secao=b_secao, ell=ell, vinculacao=vinculacao,
            secao_constante=secao_constante,
            armadura_constante=armadura_constante,
            f_ck_MPa=f_ck_MPa, gamma_c_base=gamma_c_base,
            condicoes_desfavoraveis_de_execucao=(
                condicoes_desfavoraveis_de_execucao),
            f_yk_longitudinal_MPa=f_yk_longitudinal_MPa,
            f_yk_estribo_MPa=f_yk_estribo_MPa, gamma_s=gamma_s,
            idade_maior_ou_igual_28_dias=idade_maior_ou_igual_28_dias,
            classe_de_agressividade=classe_de_agressividade,
            d_agregado_mm=d_agregado_mm,
            cobrimento_declarado_mm=cobrimento_declarado_mm,
            phi_longitudinal_mm=phi_longitudinal_mm,
            numero_de_barras=numero_de_barras,
            espacamento_entre_eixos_mm=espacamento_entre_eixos_mm,
            phi_t_mm=phi_t_mm, s_estribo_mm=s_estribo_mm, barras=barras,
            N_d=N_d, M_Sd_x=M_Sd_x, M_Sd_y=M_Sd_y, H_x=H_x, H_y=H_y,
            metodo_de_seguranca=METODO_DE_SEGURANCA_DO_PILARETE,
            tipo_de_junta=tipo_de_junta, boa_aderencia=boa_aderencia,
            armadura_tracionada_em_alguma_combinacao=(
                armadura_tracionada_em_alguma_combinacao),
            A_s_calculada=A_s_calculada,
            modelo_de_calculo=modelo_de_calculo,
            theta_biela_graus=theta_biela_graus,
            alpha_estribo_graus=alpha_estribo_graus, A_sw_por_s=A_sw_por_s,
            N_gamma_f_1=N_gamma_f_1,
            normal_de_compressao_em_todas_as_combinacoes=(
                normal_de_compressao_em_todas_as_combinacoes),
            ell_e_declarado=ell_e_declarado, ell_0=ell_0,
        )

    # ========================================================== verificar
    def _verificar(self) -> None:
        """ÚNICO ponto de chamada de `verificar_pilarete` (nome fixado pelo
        ruleset). Ordem: destrói o resultado anterior, coleta e formata os
        dados, chama o núcleo, desenha o que o núcleo devolveu — nunca o
        contrário."""
        for filho in self.frame_resultado.winfo_children():
            filho.destroy()
        self.ultimo_resultado = None

        try:
            dados = self._construir_dados()
        except ValueError as erro:
            self._desenhar_erro_de_entrada(erro)
            return

        try:
            resultado = verificar_pilarete(dados)
        except RecusaForaDeDominio as erro:
            self._desenhar_recusa_estrutural(erro)
            return

        self._desenhar_resultado(dados, resultado)
        self.ultimo_resultado = resultado

    def _desenhar_erro_de_entrada(self, erro: ValueError) -> None:
        """Entrada malformada/incompleta ao clicar "Verificar" — CARD

        inline, nunca `messagebox.showerror` (mesma doutrina de
        `_desenhar_recusa_estrutural`, REQ-UI-PILARETE-03/11): um
        `messagebox` é modal de verdade e trava a thread do Tk em teste
        headless — e mais geralmente trava a janela esperando um clique
        que só o usuário interativo pode dar. O texto é o que
        `_float_requerido`/`_ler_barras` já formatou (nomeia o campo),
        sem reescrita nem juízo adicional aqui.
        """
        card = ttk.LabelFrame(self.frame_resultado,
                              text="Entrada inválida")
        card.pack(fill="x", padx=4, pady=4)
        ttk.Label(card, text=str(erro),
                  style="PainelFraco.TLabel", foreground=tema.VERMELHO,
                  wraplength=820, justify="left").pack(anchor="w", padx=8,
                                                        pady=8)

    def _desenhar_recusa_estrutural(self, erro: RecusaForaDeDominio) -> None:
        card = ttk.LabelFrame(self.frame_resultado,
                              text="RECUSADO — fora do domínio aprovado")
        card.pack(fill="x", padx=4, pady=4)
        ttk.Label(card, text=_texto_recusa_estrutural(erro),
                  style="PainelFraco.TLabel", foreground=tema.VERMELHO,
                  wraplength=820, justify="left").pack(anchor="w", padx=8,
                                                        pady=8)

    # ------------------------------------------------------------ desenho
    def _desenhar_resultado(self, dados: DadosDoPilarete,
                            resultado: ResultadoPilarete) -> None:
        self._desenhar_veredito(resultado)
        self._desenhar_gamma_n(dados, resultado)
        self._desenhar_memorial(resultado)

    def _desenhar_veredito(self, resultado: ResultadoPilarete) -> None:
        card = ttk.LabelFrame(self.frame_resultado, text="Veredito")
        card.pack(fill="x", padx=4, pady=4)

        cor_titulo = tema.VERDE if resultado.atendido else tema.VERMELHO
        ttk.Label(card, text=resultado.nome_do_veredito, style="Painel.TLabel",
                  foreground=cor_titulo, font=("Segoe UI", 11, "bold"),
                  wraplength=820, justify="left").pack(anchor="w", padx=8,
                                                        pady=(6, 4))

        # REQ-UI-PILARETE-07-c: as parcelas aparecem UMA A UMA.
        parcelas = (
            ("ELU de solicitações NORMAIS (17.2.1)",
             resultado.elu_normal.atendido),
            ("Armadura longitudinal (18.4.2)",
             resultado.armadura_longitudinal.atendido),
            ("Estribos (18.4.3 / 18.3.3.2)", resultado.estribos.atendido),
            ("Cobrimento (Tabela 7.2)", resultado.atende_cobrimento),
        )
        for rotulo, atendido in parcelas:
            estado = "ATENDIDO" if atendido else "NÃO ATENDIDO"
            cor = tema.VERDE if atendido else tema.VERMELHO
            ttk.Label(card, text=f"{rotulo}: {estado}", foreground=cor,
                      style="Painel.TLabel").pack(anchor="w", padx=8, pady=1)

        # REQ-UI-PILARETE-07-b: NUNCA um visto verde silencioso quando o
        # cortante não foi verificado — as DUAS frases literais do núcleo.
        if resultado.elu_cortante is not None:
            estado = ("ATENDIDO" if resultado.elu_cortante.atendido
                      else "NÃO ATENDIDO")
            cor = tema.VERDE if resultado.elu_cortante.atendido else tema.VERMELHO
            ttk.Label(card, text=f"ELU de FORÇA CORTANTE (17.4.2.1): {estado}",
                      foreground=cor, style="Painel.TLabel").pack(
                anchor="w", padx=8, pady=1)
        else:
            primeira, segunda = classificacao_14_4_1.frases_obrigatorias_da_faixa_B(
                resultado.classificacao)
            ttk.Label(card, text="ELU de FORÇA CORTANTE (17.4.2.1): RECUSADA",
                      foreground=tema.AMARELO, font=("Segoe UI", 9, "bold"),
                      style="Painel.TLabel").pack(anchor="w", padx=8,
                                                  pady=(6, 0))
            ttk.Label(card, text=primeira, foreground=tema.AMARELO,
                      style="Painel.TLabel", wraplength=820,
                      justify="left").pack(anchor="w", padx=8, pady=1)
            ttk.Label(card, text=segunda, foreground=tema.AMARELO,
                      style="Painel.TLabel", wraplength=820,
                      justify="left").pack(anchor="w", padx=8, pady=(1, 6))

        # REQ-UI-PILARETE-07-d: a razão de 14.4.1 nas DUAS faixas.
        classificacao = resultado.classificacao
        ttk.Label(
            card, text=(
                "NBR 6118:2023, 14.4.1: razão comprimento/maior dimensão "
                f"= {classificacao.razao_14_4_1:.4f} contra o limite de "
                f"{classificacao_14_4_1.LIMITE_14_4_1:.1f} (faltariam "
                f"{classificacao.ell_necessario_para_faixa_A:.4f} m de "
                "comprimento para a FAIXA A). Esta verificação é "
                "INDEPENDENTE de lambda < lambda_1 (15.8.2) — uma decide "
                "a CLASSE do elemento, a outra a dispensa dos efeitos "
                "locais de 2ª ordem."),
            style="PainelFraco.TLabel", wraplength=820, justify="left").pack(
            anchor="w", padx=8, pady=(4, 4))

        # REQ-UI-PILARETE-05: o cruzamento SEMPRE aparece, não só no falho.
        ttk.Label(card, text=resultado.consistencia_de_cobrimento.linha_de_memorial,
                  style="PainelFraco.TLabel", wraplength=820,
                  justify="left").pack(anchor="w", padx=8, pady=(0, 4))

        # REQ-UI-PILARETE-07-e: o que NÃO foi verificado, no MESMO bloco.
        ttk.Label(card, text=resultado.memorial()[-1],
                  style="PainelFraco.TLabel", foreground=tema.AMARELO,
                  wraplength=820, justify="left").pack(anchor="w", padx=8,
                                                        pady=(4, 8))

    def _desenhar_gamma_n(self, dados: DadosDoPilarete,
                          resultado: ResultadoPilarete) -> None:
        card = ttk.LabelFrame(self.frame_resultado,
                              text="gamma_n (13.2.3, Tabela 13.1) e N a gamma_f = 1,0")
        card.pack(fill="x", padx=4, pady=4)

        if resultado.gamma_n_aplicado:
            texto_n = (
                f"gamma_n aplicado = {resultado.gamma_n:.4f} (b_mín = "
                f"{resultado.dimensoes.b_min_cm:.2f} cm, na faixa 14 a "
                "19 cm — Tabela 13.1). N_d DIGITADO = "
                f"{dados.N_d:.4f} kN -> N_d MAJORADO = "
                f"{resultado.N_d_majorado:.4f} kN. M_Sd,x digitado = "
                f"{dados.M_Sd_x:.4f} kN·m -> majorado = "
                f"{resultado.M_Sd_x_majorado:.4f} kN·m. M_Sd,y digitado = "
                f"{dados.M_Sd_y:.4f} kN·m -> majorado = "
                f"{resultado.M_Sd_y_majorado:.4f} kN·m.")
        else:
            texto_n = (
                "gamma_n = 1,00 — não há majoração adicional (b_mín = "
                f"{resultado.dimensoes.b_min_cm:.2f} cm >= 19 cm e área = "
                f"{resultado.dimensoes.area_cm2:.2f} cm² >= 360 cm²).")
        ttk.Label(card, text=texto_n, style="PainelFraco.TLabel",
                  wraplength=820, justify="left").pack(anchor="w", padx=8,
                                                        pady=(6, 4))

        if resultado.elu_cortante is not None:
            v = resultado.elu_cortante
            if v.N_gamma_f_1 is not None:
                texto_ngf1 = (
                    f"N na combinação com gamma_f = 1,0 = {v.N_gamma_f_1:.4f} "
                    f"kN, lado a lado com N_d MAJORADO = "
                    f"{resultado.N_d_majorado:.4f} kN — a Norma manda "
                    "calcular a tensão que M_0 anula com gamma_f = 1,0, "
                    "enquanto M_Sd,máx é DE CÁLCULO; a fração mistura dois "
                    "níveis de ponderação DE PROPÓSITO.")
            else:
                texto_ngf1 = (
                    "N na combinação com gamma_f = 1,0 NÃO foi declarado: "
                    "a majoração de V_c pela compressão NÃO foi aplicada "
                    "(lado conservador).")
            ttk.Label(card, text=texto_ngf1, style="PainelFraco.TLabel",
                      wraplength=820, justify="left").pack(anchor="w", padx=8,
                                                           pady=(0, 6))

    def _desenhar_memorial(self, resultado: ResultadoPilarete) -> None:
        """REQ-UI-PILARETE-09: `resultado.memorial()` NA ÍNTEGRA E NA
        ORDEM — nada aqui reordena, resume, trunca ou reescreve uma linha."""
        card = ttk.LabelFrame(
            self.frame_resultado,
            text="Memorial de cálculo (NBR 6122 §7.1) — íntegro e literal")
        card.pack(fill="both", expand=True, padx=4, pady=4)

        linhas = resultado.memorial()
        texto_memorial = "\n".join(linhas)

        caixa = tk.Text(card, height=18, wrap="none", bg=tema.FUNDO_CAMPO,
                         fg=tema.TEXTO, insertbackground=tema.TEXTO,
                         relief="flat", font=tema.FONTE_MONO)
        caixa.insert("1.0", texto_memorial)
        caixa.configure(state="disabled")
        vbar = ttk.Scrollbar(card, orient="vertical", command=caixa.yview)
        hbar = ttk.Scrollbar(card, orient="horizontal", command=caixa.xview)
        caixa.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        caixa.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=(8, 0))
        vbar.grid(row=0, column=1, sticky="ns", pady=(8, 0))
        hbar.grid(row=1, column=0, sticky="ew", padx=(8, 0))
        card.rowconfigure(0, weight=1)
        card.columnconfigure(0, weight=1)

        # REQ-UI-PILARETE-11-e: os botões capturam `ResultadoPilarete` por
        # FECHAMENTO sobre o texto já formatado — nunca por atributo lido
        # depois do clique.
        botoes = ttk.Frame(self.frame_resultado, style="Painel.TFrame")
        botoes.pack(fill="x", padx=4, pady=(0, 8))
        ttk.Button(
            botoes, text="Copiar memorial",
            command=lambda texto=texto_memorial: self._copiar_memorial(texto)
        ).pack(side="left", padx=(4, 4))
        ttk.Button(
            botoes, text="Salvar memorial como .txt...",
            command=lambda texto=texto_memorial: self._salvar_memorial(texto)
        ).pack(side="left")

    def _copiar_memorial(self, texto: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(texto)

    def _salvar_memorial(self, texto: str) -> None:
        caminho = filedialog.asksaveasfilename(
            title="Salvar memorial do pilarete", defaultextension=".txt",
            filetypes=[("Texto", "*.txt")])
        if not caminho:
            return
        with open(caminho, "w", encoding="utf-8") as arquivo:
            arquivo.write(texto)
