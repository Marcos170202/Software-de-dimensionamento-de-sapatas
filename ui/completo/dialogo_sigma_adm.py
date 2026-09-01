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

REDESENHO DO MODELO DE ESTADO (rodada 4 — decisão humana registrada no
pedido de trabalho, não do a6). Três rodadas seguidas de GATE 2
reprovaram este diálogo pela MESMA causa-raiz: um estado intermediário
"selecionado, pronto para usar" (`self._valor_final_kPa` +
`self._valor_final_origem` + `self._valor_final_e_majorado`), preenchido
no clique de um card e só CONSUMIDO num clique posterior em "Usar este
valor →". Entre os dois cliques, qualquer mudança nas entradas (N_SPT, B,
L, h, γ, forma, solo, modo de ruptura, e os próprios controles de vento)
podia deixar esse cache respondendo por uma entrada que já não é a que
está na tela — cada rodada de correção fechava o gatilho relatado
(primeiro só o painel de vento, depois só alguns campos) sem eliminar a
CLASSE do defeito, porque a estratégia era invalidar o cache reagindo a
cada widget individualmente, e sempre sobrava algum widget novo (ou
antigo, esquecido) fora da lista.

A correção desta rodada ELIMINA o cache, em vez de tentar invalidá-lo
completo: não existe mais `self._resultado_ativo`/`self._valor_final_*`.
Cada card de resultado (`_card_resultado`) carrega o objeto imutável
`ResultadoSigmaAdmELU` que a ELE pertence, por FECHAMENTO (closure) do
próprio botão "Usar este valor →" — `_usar_base` — e não por um atributo
de instância que sobrevive além do clique. Como todo o conteúdo de
`frame_resultado_teorico`/`frame_resultado_semi` é destruído no primeiro
passo de `_calcular_teorico`/`_calcular_semiempirico` (`for filho in
...: filho.destroy()`), um card só existe na tela enquanto representar
fielmente a última chamada ao núcleo — não há como um botão "Usar" de um
card VELHO sobreviver a um recálculo, porque o card em si já foi
destruído junto com o widget. É estruturalmente impossível "ver 160 kPa
na tela e usar 300 kPa": o botão que entrega 300 kPa só existe enquanto
o card que mostra 300 kPa também existir.

O mesmo raciocínio se aplica à majoração por vento, que era o segundo
estágio do cache antigo (`_selecionar_majorado`, `_invalidar_vento`, a
lista crescente de `trace_add`/`bind` por widget de vento). Em vez de
"Calcular teto e majoração" preencher um cache que "Selecionar valor
majorado →" lê depois, cada card ganhou sua própria mini-seção de vento:
o botão "Calcular majoração por vento..." (`_calcular_vento_no_card`) LÊ
os controles de vento (compartilhados, mas nunca cacheados) NA HORA do
clique e desenha o resultado ali mesmo, com o botão "Usar valor
majorado →" já fechado por closure sobre o `ResultadoMajoracaoVento` que
aquela MESMA chamada acabou de calcular — nunca um objeto guardado de um
clique anterior. Não há `_invalidar_vento` porque não há nada para
invalidar: mudar o k_v, a declaração de ação principal ou o tipo de obra
não estraga estado algum, porque o próximo clique em "Calcular
majoração..." (em qualquer card) sempre lê os widgets como estão NAQUELE
INSTANTE — o problema de "esqueci de invalidar este widget novo" deixa de
existir porque não há lista de widgets a vigiar.

Esta é a opção (a) do pedido de trabalho ("botão Usar por card"), e não a
opção (b) (um contador de versão de entrada com um botão único no
rodapé): com (a) é estruturalmente impossível ficar obsoleto, porque não
há intervalo de tempo entre "ver o resultado" e "usar o resultado" — o
clique QUE mostra e o clique QUE usa são o mesmo par (card, botão). A
opção (b) teria de continuar caçando "todo StringVar/BooleanVar de
entrada" para o contador de versão, o que é exatamente o padrão que já
falhou três vezes (a cada rodada aparecia um widget fora da lista); (a)
não depende de enumerar entrada alguma.

MAPEAMENTO DOS REQUISITOS, para conferência rápida:

* REQ-UI-SIGMA-01 — `ROTULO_ELU` (constante do núcleo) aparece colado a
  TODO número devolvido, em `_card_resultado` e na majoração inline de
  cada card. Nunca "tensão admissível" em rótulo algum desta tela.
* REQ-UI-SIGMA-02 — `ROTULO_FONTE_NAO_NORMATIVA` e
  `ADVERTENCIA_FORMULARIOS_DE_BOLSO` (do núcleo) aparecem junto de cada
  resultado; nenhum texto de fonte é redigido aqui.
* REQ-UI-SIGMA-03 — `_texto_recusa`/`_texto_recusa_metodo` mostram
  parâmetro, valor, intervalo e fonte, e distinguem DECLARADO_EM_TEXTO de
  ADOTADO_DA_EXTENSAO_DE_FIGURA (`_ROTULOS_DE_FORCA`). Nunca "erro de
  cálculo" genérico. Quando NENHUM método semiempírico se aplica
  (`NenhumMetodoAplicavelError`), `_calcular_semiempirico` desenha UM
  CARD POR RECUSA (`erro.recusas`, na ordem de avaliação dos métodos) —
  nunca só a primeira: os campos escalares herdados da exceção
  (`erro.parametro` etc.) são, pela própria docstring do núcleo, "uma
  visão DEGRADADA... nunca a recusa principal", e usá-los sozinhos era o
  defeito D-03 da revisão a6 do GATE 2.
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
  teto (`k_v_maximo_admissivel`, do núcleo) lado a lado com o controle,
  agora embutidos em cada card (ver REDESENHO acima). A lista de sete
  tipos de obra vem de `vento.TIPOS_DE_OBRA_DOS_30_POR_CENTO` e é exibida
  por `Combobox` (`state="readonly"`), nunca como texto livre.
* REQ-UI-SIGMA-06 — `DECLARACAO_REGIONAL_EXIGIDA` (checkbox sem default
  afirmativo, aba semiempírico — REQ-SIGMA-06 é obrigação do §7.3.3, o
  caminho teórico não tem campo correspondente no núcleo) e
  `AVISO_ESCOPO_SIGMA_ADM` (banner fixo no topo do diálogo).

PROVENIÊNCIA NO MEMORIAL (D-02 do GATE 2, rodada 3 — mantida neste
redesenho). `_fechar_com_resultado` (chamada por `_usar_base`/
`_usar_majorado`, nunca diretamente por um botão) grava a proveniência do
valor escolhido (método, `ROTULO_ELU`, `ROTULO_FONTE_NAO_NORMATIVA`,
avisos, regras/práticas e o próprio `valor_kPa`) em `self.resultado_info`;
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

D-01 DO GATE 2 (rodada do redesenho + 1) — CASO NÃO COBERTO PELO
REDESENHO ACIMA. O redesenho elimina "usar um card velho depois de
RECALCULAR" (o card antigo é destruído no primeiro passo de
`_calcular_teorico`/`_calcular_semiempirico`). Mas um card sobrevive
intacto — botão "Usar este valor →" incluído — a uma mudança de ENTRADA
que NUNCA chega a disparar um recálculo: o engenheiro calcula com
N_SPT=15 (card mostra 300,0 kPa), muda o campo N_SPT para "5" e NÃO
clica em "Calcular" de novo — o botão antigo continua na tela e, se
clicado, entrega 300,0 kPa, que já não corresponde a nenhum campo
digitado (o valor correto seria 100,0 kPa; erro de +200 %, sempre do
lado inseguro, porque "esquecer de recalcular" nunca produz um valor
maior do que o real por acaso favorável).

A correção NÃO reintroduz o cache antigo (isto continua sendo do card,
por closure — `_card_resultado`/`_usar_base` não mudaram). O que muda é
que cada card agora se OUVE destruir assim que qualquer campo de
ENTRADA da aba que o gerou muda, mesmo sem recálculo algum:
`_vigiar_entradas_da_aba` regista um `trace_add("write", ...)` em TODA
`StringVar`/`BooleanVar` que a construção de `_montar_aba_teorico`/
`_montar_aba_semiempirico` cria e amarra a `self` (isto é, todo campo
que seguiu o padrão já existente `self.t_xxx = self._campo(...)`/
`self._combo(...)` ou `tk.BooleanVar(...)` direto) — a lista de vars
observadas é obtida por DIFERENÇA de `vars(self)` antes/depois de cada
`_montar_aba_*`, não por enumeração manual campo a campo: um campo novo
adicionado nessas duas abas, no futuro, entra na vigilância sozinho,
contanto que seja atribuído a `self` como os demais já são (mesmo
padrão que o núcleo pede de "parâmetro novo aparece na UI sozinho").
Isto cobre exatamente os 13 campos do teórico (c, phi, B, L, h,
gamma_acima, gamma_abaixo, forma, modo, natureza, homogêneo, n_provas,
provas_projeto) e os 9 do semiempírico (N_SPT, B, forma, solo, h,
gamma, considerar_q, q, regional) sem listar nenhum deles aqui — e
DELIBERADAMENTE não inclui os controles de vento (`v_vento_principal`,
`v_tipo_obra`, `v_kv`), que são montados por `_montar_vento` DEPOIS
desta varredura: a mini-seção de vento de cada card já resolve sua
própria invalidação por closure/releitura no clique (ver REDESENHO
acima) — não há cache algum ali para "esquecer de invalidar" por
mudança de k_v/tipo de obra fora de um recálculo explícito daquela
seção, que é o cenário coberto por
`test_editar_kv_sem_recalcular_botao_ja_visivel_entrega_o_que_esta_no_card`.

`_invalidar_resultado` (o callback do trace) não apaga a tela em
silêncio: troca o conteúdo de `frame_resultado_teorico`/
`frame_resultado_semi` — se houver algo lá — por um único aviso,
`_AVISO_ENTRADAS_ALTERADAS`, explicando que as entradas mudaram e que é
preciso recalcular; o botão "Usar este valor →" (ou "Usar valor
majorado →") do card antigo é destruído junto, pela mesma razão
estrutural do REDESENHO: não sobrevive widget nenhum do card velho.

Esta abordagem por diferença de `vars(self)` é segura por construção,
ao contrário do cache antigo: esquecer de atribuir um campo futuro a
`self` (ou atribuí-lo fora da janela de `_montar_aba_*` observada)
produz, no PIOR caso, um card que não é invalidado quando deveria — o
comportamento de HOJE, antes desta correção — nunca a entrega de um
valor errado, porque o valor entregue continua vindo sempre do
`ResultadoSigmaAdmELU` fechado por closure no botão do card que
efetivamente está na tela.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from calc_core.geotecnico.dominio import (
    ADOTADO_DA_EXTENSAO_DE_FIGURA,
    DECLARADO_EM_TEXTO,
    DECLARADO_PELO_USUARIO,
    ForaDoDominioError,
    NenhumMetodoAplicavelError,
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

_AVISO_ENTRADAS_ALTERADAS = (
    "ENTRADAS ALTERADAS DESDE ESTE CÁLCULO — recalcule antes de usar. "
    "Nenhum botão \"Usar\" desta aba corresponde mais aos valores "
    "digitados agora (D-01, GATE 2)."
)

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
    erro bloqueante) OU de ``NenhumMetodoAplicavelError.recusas`` (nenhuma
    correlação se aplicou — mesmo formato, um card por método)."""
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
    disponível, nesta tela e em qualquer outra deste software).

    Ver o REDESENHO documentado no topo do módulo: não há mais um
    "resultado ativo"/"valor final" cacheado no diálogo. Cada card de
    resultado é dono do seu próprio botão "Usar este valor →", e a
    majoração por vento é calculada e usada dentro do mesmo card, sob
    demanda, nunca guardada num atributo à espera de um segundo clique.
    """

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.title("Calcular σ_adm — parcela de ELU (NBR 6122:2022 §7.3)")
        self.configure(bg=tema.FUNDO_PAINEL)
        self.geometry("820x760")
        self.minsize(680, 520)
        self.transient(master)
        self.grab_set()

        self.resultado_kPa: float | None = None
        """Preenchido só quando o usuário clica em algum dos botões "Usar
        este valor →"/"Usar valor majorado →" — a partir daí o diálogo
        fecha (`self.destroy()`) no mesmo clique."""

        self.resultado_info: dict | None = None
        """Proveniência do valor escolhido — `formulario.py` guarda isto em
        `PainelEntrada.ultimo_sigma_adm_calculado` e o memorial/Excel do
        escopo amplo o usa para rotular a linha de σ_adm com `ROTULO_ELU`/
        `ROTULO_FONTE_NAO_NORMATIVA` sempre que ele ainda for válido (ver
        `formulario.py::_abrir_calculadora_sigma_adm` e
        `_ao_editar_sigma_adm`)."""

        self._montar()

    # ------------------------------------------------------------ montagem
    def _montar(self) -> None:
        ttk.Label(self, text=AVISO_ESCOPO_SIGMA_ADM, style="Banner.TLabel",
                  wraplength=780, justify="left", padding=(10, 6)).pack(
            fill="x")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=(8, 4))

        # D-01 (GATE 2, rodada do redesenho + 1): cada `_montar_aba_*`
        # atribui todo campo de entrada a `self` (`self.t_xxx`/`self.s_xxx`
        # — mesmo padrão de sempre). Vigiar essas variáveis por DIFERENÇA
        # de `vars(self)` antes/depois de cada chamada — em vez de listar
        # campo por campo aqui — é o que torna esta vigilância robusta a
        # um campo novo esquecido (ver docstring do módulo, seção D-01).
        vars_teorico = self._construir_e_capturar_variaveis(
            lambda: self._montar_aba_teorico(notebook))
        vars_semi = self._construir_e_capturar_variaveis(
            lambda: self._montar_aba_semiempirico(notebook))
        self._vigiar_entradas(vars_teorico, self.frame_resultado_teorico)
        self._vigiar_entradas(vars_semi, self.frame_resultado_semi)

        self._montar_vento(self)
        self._montar_rodape(self)

    def _construir_e_capturar_variaveis(self, construir) -> list[tk.Variable]:
        """Chama `construir()` (um `_montar_aba_*`) e devolve toda
        `tk.Variable` (StringVar/BooleanVar/...) que a chamada acabou de
        atribuir a `self` — por diferença de `vars(self)` antes/depois,
        não por lista manual (D-01). Só pega variáveis amarradas a `self`
        porque é exatamente o padrão que `_campo`/`_combo`/os
        `tk.BooleanVar(...)` das duas abas já seguem (`self.t_xxx = ...`/
        `self.s_xxx = ...`) — uma variável local que não vire atributo de
        `self` não entraria na vigilância, mas nenhum campo de entrada
        desta tela é assim hoje."""
        antes = set(vars(self))
        construir()
        return [valor for nome, valor in vars(self).items()
                if nome not in antes and isinstance(valor, tk.Variable)]

    def _vigiar_entradas(self, variaveis: list[tk.Variable],
                          frame_resultado: ttk.Frame) -> None:
        """Registra, em cada `variavel` de `variaveis`, um `trace_add`
        que invalida `frame_resultado` (`_invalidar_resultado`) assim que
        ela mudar — cobre Entry (via `textvariable`), Combobox (idem — o
        `Combobox` já escreve na mesma `StringVar` quando o engenheiro
        escolhe um item) e Checkbutton (via `variable`), sem distinguir o
        tipo de widget: o que importa é que a VARIÁVEL mudou (D-01)."""
        for variavel in variaveis:
            variavel.trace_add(
                "write",
                lambda *_ignorado, fr=frame_resultado:
                    self._invalidar_resultado(fr))

    def _invalidar_resultado(self, frame_resultado: ttk.Frame,
                              *_ignorado: object) -> None:
        """Callback de `_vigiar_entradas` (D-01): se `frame_resultado`
        tiver algum card (de resultado OU de recusa) desenhado a partir de
        um cálculo anterior, destrói tudo — o(s) botão(ões) "Usar..." que
        esses cards carregavam somem junto, mesma garantia estrutural do
        REDESENHO (um botão "Usar" só existe enquanto o card que o
        desenhou também existir) — e desenha, no lugar, um único aviso
        pedindo para recalcular. Não faz nada se o frame já estiver vazio
        (nada calculado ainda) ou se já for só o próprio aviso (evita
        destruir/recriar o mesmo aviso a cada tecla digitada)."""
        filhos = frame_resultado.winfo_children()
        if not filhos:
            return
        if len(filhos) == 1 and getattr(
                filhos[0], "_aviso_entradas_alteradas", False):
            return
        for filho in filhos:
            filho.destroy()
        aviso = ttk.Label(
            frame_resultado, text=_AVISO_ENTRADAS_ALTERADAS,
            style="PainelFraco.TLabel", wraplength=700, justify="left",
            foreground=tema.VERMELHO, font=("Segoe UI", 9, "bold"),
            padding=(8, 8))
        aviso._aviso_entradas_alteradas = True
        aviso.pack(anchor="w", fill="x", padx=4, pady=4)

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
        except NenhumMetodoAplicavelError as erro:
            # D-03 do GATE 2, rodada 3 (reincidente na TELA até agora, mesmo
            # com o núcleo já corrigido): `erro.parametro`/`erro.valor`/
            # `erro.intervalo`/`erro.fonte` são só a PRIMEIRA recusa — a
            # própria docstring de `NenhumMetodoAplicavelError` avisa que é
            # "uma visão DEGRADADA... nunca a recusa principal". O contrato
            # do a4 é "um card por item": itera `erro.recusas` (uma por
            # método candidato, na ordem de avaliação) e desenha um card
            # para CADA uma — mesmo padrão já usado no caminho em que ao
            # menos uma correlação se aplica (`dispersao.recusas`, abaixo).
            for recusa in erro.recusas:
                self._card_recusa(self.frame_resultado_semi,
                                   _texto_recusa_metodo(recusa))
            return
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
        """Um card = um `ResultadoSigmaAdmELU` imutável, dono do seu
        próprio botão "Usar este valor →" e da sua própria mini-seção de
        majoração por vento (ver REDESENHO na docstring do módulo). Nada
        aqui é guardado em `self` para ser lido depois — tudo o que o
        botão precisa já está fechado (closure) sobre `resultado`."""
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
        ttk.Button(f, text="Usar este valor →",
                   command=lambda r=resultado: self._usar_base(r)).pack(
            anchor="e", padx=8, pady=(2, 4))

        self._secao_vento_no_card(f, resultado)

    def _secao_vento_no_card(self, pai_card: ttk.LabelFrame,
                              resultado: ResultadoSigmaAdmELU) -> None:
        """Mini-seção de majoração por vento embutida no card — parte do
        MESMO fluxo imediato do card, não um segundo estágio (ver
        REDESENHO). O botão "Calcular majoração..." lê os controles
        compartilhados (`self.v_vento_principal`/`self.v_tipo_obra`/
        `self.v_kv`, montados por `_montar_vento`) e ESTE `resultado` — o
        objeto exato do card — no instante do clique; o botão "Usar valor
        majorado →" que aparece depois fecha por closure sobre o
        `ResultadoMajoracaoVento` que aquela MESMA chamada acabou de
        calcular, nunca sobre um valor de um clique anterior."""
        vento = ttk.LabelFrame(
            pai_card, text="Majoração por vento sobre este valor "
                           "(opcional) — NBR 6122:2022 §6.3.2")
        vento.pack(fill="x", padx=8, pady=(0, 8))
        saida = ttk.Frame(vento)
        ttk.Button(
            vento, text="Calcular majoração por vento...",
            command=lambda r=resultado, s=saida: self._calcular_vento_no_card(r, s)
        ).pack(anchor="w", padx=6, pady=(6, 2))
        saida.pack(fill="x", padx=6, pady=(0, 6))

    def _card_recusa(self, pai: tk.Misc, texto: str) -> None:
        f = ttk.LabelFrame(pai, text="Recusado — fora do domínio")
        f.pack(fill="x", padx=4, pady=4)
        ttk.Label(f, text=texto, style="PainelFraco.TLabel", wraplength=700,
                  justify="left", foreground=tema.VERMELHO).pack(
            anchor="w", padx=8, pady=6)

    # -------------------------------------------------------------- vento
    def _montar_vento(self, pai: tk.Misc) -> None:
        """Controles COMPARTILHADOS da majoração por vento — só a
        DECLARAÇÃO (vento é ação principal?, tipo de obra, k_v adotado).
        Não há botão "Calcular"/"Selecionar" neste painel: o cálculo em
        si acontece dentro de cada card (`_secao_vento_no_card` /
        `_calcular_vento_no_card`), que lê estes widgets no instante do
        clique. Por isso não existe `_invalidar_vento` nem `trace_add`/
        `bind` algum aqui: não há valor de majoração cacheado neste
        painel para ficar obsoleto — ver REDESENHO na docstring do
        módulo."""
        f = ttk.LabelFrame(pai, text="Declaração para majoração por vento "
                                      "(opcional) — NBR 6122:2022 §6.3.2")
        f.pack(fill="x", padx=10, pady=(4, 4))
        f.columnconfigure(1, weight=1)

        self.v_vento_principal = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            f, text="Vento é a ação variável principal na combinação "
                    "estrutural que governa este caso",
            variable=self.v_vento_principal, command=self._alternar_vento
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=8, pady=(6, 0))
        ttk.Label(f, text=AVISO_ACAO_PRINCIPAL_NAO_E_INFERIDA,
                  style="PainelFraco.TLabel", wraplength=760, justify="left",
                  font=("Segoe UI", 8)).grid(row=1, column=0, columnspan=3,
                                              sticky="w", padx=8, pady=(0, 6))

        ttk.Label(f, text="Tipo de obra (lista FECHADA, §6.3.2)",
                  style="PainelFraco.TLabel").grid(row=2, column=0, sticky="w",
                                                    padx=8)
        opcoes_obra = [_SEM_LISTA_FECHADA, *TIPOS_DE_OBRA_DOS_30_POR_CENTO]
        self.v_tipo_obra = tk.StringVar(value=opcoes_obra[0])
        self.combo_tipo_obra = ttk.Combobox(
            f, textvariable=self.v_tipo_obra, state="disabled", width=52,
            values=opcoes_obra)
        self.combo_tipo_obra.grid(row=3, column=0, columnspan=3, sticky="w",
                                   padx=8, pady=(0, 6))

        ttk.Label(f, text="k_v adotado (0 = não majora; teto 0,15 ou 0,30 "
                          "conforme o tipo de obra e o piso de FSg = 1,6) — "
                          "lido de novo a cada clique em \"Calcular "
                          "majoração...\" de qualquer card, nunca travado "
                          "num valor antigo",
                  style="PainelFraco.TLabel", wraplength=760,
                  justify="left").grid(row=4, column=0, columnspan=3,
                                        sticky="w", padx=8)
        self.v_kv = tk.StringVar(value=f"{K_V_DEFAULT:g}")
        ttk.Entry(f, textvariable=self.v_kv, width=10).grid(
            row=5, column=0, sticky="w", padx=8, pady=(0, 8))

    def _alternar_vento(self) -> None:
        self.combo_tipo_obra.configure(
            state="readonly" if self.v_vento_principal.get() else "disabled")

    def _calcular_vento_no_card(self, resultado: ResultadoSigmaAdmELU,
                                 saida: ttk.Frame) -> None:
        """Lê os controles de vento (compartilhados, nunca cacheados) e
        ESTE `resultado` (o objeto do card que chamou, por closure) NO
        INSTANTE do clique, e desenha a majoração ou a recusa dentro de
        `saida`. Chamável de novo a qualquer momento — cada chamada relê
        os widgets do zero, então mudar k_v/tipo de obra/declaração entre
        dois cliques não deixa resíduo algum: o próximo clique já reflete
        o estado atual, sem invalidação nenhuma para esquecer."""
        for filho in saida.winfo_children():
            filho.destroy()

        try:
            FSg = resultado.FSg_efetivo
        except ValueError as erro:
            ttk.Label(saida, text=f"Sem FSg: {erro}",
                      style="PainelFraco.TLabel", foreground=tema.VERMELHO,
                      wraplength=680, justify="left").pack(
                anchor="w", pady=(2, 4))
            return

        principal = self.v_vento_principal.get()
        lista_30 = principal and self.v_tipo_obra.get() != _SEM_LISTA_FECHADA
        try:
            k_v = _float(self.v_kv.get(), K_V_DEFAULT)
        except ValueError:
            ttk.Label(saida, text="k_v deve ser numérico.",
                      style="PainelFraco.TLabel", foreground=tema.VERMELHO
                      ).pack(anchor="w", pady=(2, 4))
            return

        try:
            teto = k_v_maximo_admissivel(
                FSg=FSg, vento_e_acao_variavel_principal=principal,
                tipo_de_obra_da_lista_dos_30_por_cento=lista_30)
            majoracao = majoracao_admissivel(
                resultado.sigma_adm_ELU_kPa, FSg=FSg,
                vento_e_acao_variavel_principal=principal,
                tipo_de_obra_da_lista_dos_30_por_cento=lista_30, k_v=k_v)
        except (MajoracaoDeVentoError, ValueError) as erro:
            ttk.Label(saida, text=f"RECUSADO:\n{erro}",
                      style="PainelFraco.TLabel", foreground=tema.VERMELHO,
                      wraplength=680, justify="left").pack(
                anchor="w", pady=(2, 4))
            return

        texto = (
            f"Teto k_v admissível para este caso: {teto:.4f}\n"
            f"σ_adm,ELU base: {majoracao.sigma_adm_ELU_base_kPa:.1f} kPa   →   "
            f"majorado: {majoracao.sigma_adm_ELU_majorado_kPa:.1f} kPa "
            f"(k_v = {majoracao.k_v_adotado:.4f})\n"
            f"FSg efetivo pós-majoração: {majoracao.FSg_efetivo:.3f} "
            f"(piso exigido: 1,6)\n\n" + majoracao.rotulo_ELU + "\n\n"
            + "\n".join(f"• {a}" for a in majoracao.avisos)
        )
        ttk.Label(saida, text=texto, style="PainelFraco.TLabel",
                  wraplength=680, justify="left").pack(anchor="w", pady=(2, 4))
        ttk.Button(
            saida, text="Usar valor majorado →",
            command=lambda r=resultado, m=majoracao: self._usar_majorado(r, m)
        ).pack(anchor="e", pady=(2, 4))

    # ------------------------------------------------------------- rodapé
    def _montar_rodape(self, pai: tk.Misc) -> None:
        f = ttk.Frame(pai, style="Painel.TFrame")
        f.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Label(
            f, text="Cada resultado acima tem seu próprio botão \"Usar "
                    "este valor →\" (base ou majorado por vento) — não há "
                    "um valor \"selecionado\" à parte guardado nesta "
                    "janela: o botão de um card sempre entrega exatamente "
                    "o número mostrado NAQUELE card, no momento do "
                    "clique.",
            style="Painel.TLabel", wraplength=560, justify="left"
        ).pack(side="left", fill="x", expand=True)
        ttk.Button(f, text="Fechar sem usar valor algum",
                   command=self.destroy).pack(side="right")

    # -------------------------------------------------------------- usar
    def _usar_base(self, resultado: ResultadoSigmaAdmELU) -> None:
        """Comando do botão "Usar este valor →" de `_card_resultado` — sem
        majoração de vento. `resultado` chega por closure do próprio
        botão que este card criou; não há atributo intermediário para
        ficar obsoleto entre a criação do card e este clique."""
        self._fechar_com_resultado(
            valor_kPa=resultado.sigma_adm_ELU_kPa,
            origem=(f"{resultado.nome_do_metodo} — {ROTULO_ELU}, sem "
                    "majoração de vento."),
            base=resultado, majorado=False)

    def _usar_majorado(self, resultado: ResultadoSigmaAdmELU,
                        majoracao: ResultadoMajoracaoVento) -> None:
        """Comando do botão "Usar valor majorado →" que
        `_calcular_vento_no_card` desenha — `majoracao` é o
        `ResultadoMajoracaoVento` que aquela MESMA chamada acabou de
        calcular (closure), nunca um valor lido de um atributo preenchido
        num clique anterior."""
        self._fechar_com_resultado(
            valor_kPa=majoracao.sigma_adm_ELU_majorado_kPa,
            origem=(f"{resultado.nome_do_metodo} — {ROTULO_ELU}, "
                    f"MAJORADA por vento (k_v = {majoracao.k_v_adotado:.4f}"
                    ", NBR 6122 §6.3.2)."),
            base=resultado, majorado=True, majoracao=majoracao)

    def _fechar_com_resultado(self, *, valor_kPa: float, origem: str,
                               base: ResultadoSigmaAdmELU,
                               majorado: bool,
                               majoracao: ResultadoMajoracaoVento | None = None
                               ) -> None:
        """Único ponto de saída "com valor" do diálogo — grava
        `resultado_kPa`/`resultado_info` (proveniência para o memorial,
        D-02 do GATE 2 rodada 3) e fecha a janela no mesmo clique que a
        chamou. `base` é sempre o `ResultadoSigmaAdmELU` do card de
        origem, mesmo quando `majorado=True` (os avisos/regras/práticas
        do método de base continuam se aplicando).

        D-02 do GATE 2 (rodada do redesenho + 1): quando `majoracao` vem
        preenchida (`_usar_majorado`), as regras e os avisos do PRÓPRIO
        `ResultadoMajoracaoVento` — inclusive a regra
        `NBR6122-6.3.2-majoracao-vento-valores-admissiveis`, que é quem
        AUTORIZA a majoração, e o aviso literal do §6.3.2 sobre a
        verificação estrutural obrigatória — entram em `resultado_info`
        em UNIÃO com os de `base` (sem duplicar), em vez de serem
        descartados. `ResultadoMajoracaoVento` não tem campo `praticas`
        próprio (a formulação bibliográfica é sempre a do método de
        base)."""
        regras = list(base.regras)
        avisos = list(base.avisos)
        if majoracao is not None:
            for regra in majoracao.regras:
                if regra not in regras:
                    regras.append(regra)
            for aviso in majoracao.avisos:
                if aviso not in avisos:
                    avisos.append(aviso)
        self.resultado_kPa = valor_kPa
        self.resultado_info = {
            "valor_kPa": valor_kPa,
            "origem": origem,
            "metodo": base.nome_do_metodo,
            "rotulo_ELU": ROTULO_ELU,
            "rotulo_fonte": ROTULO_FONTE_NAO_NORMATIVA,
            "avisos": avisos,
            "regras": regras,
            "praticas": list(base.praticas),
            "majorado_por_vento": majorado,
        }
        self.destroy()


__all__ = ["DialogoSigmaAdm"]
