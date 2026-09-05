"""
excel_export.py
----------------
Exporta um resumo tabular de um `ResultadoSapata` já calculado para uma
planilha Excel — o mesmo conteúdo do memorial em texto/PDF
(`calc_core.sapata_isolada.relatorio.memorial`, `pranchas.gerar_memorial_pdf`),
só que em tabela em vez de texto corrido, para o usuário copiar/colar em
outra planilha.

Restrição de a3-interface.md: nada é recalculado aqui. Cada linha da planilha
é leitura direta de um campo já presente em `Sapata`/`ResultadoSapata` — a
mesma fonte de dados que o memorial em texto usa; este módulo só formata.
"""
from __future__ import annotations

import openpyxl
from openpyxl.styles import Font

from calc_core.sapata_isolada.sapata import ResultadoSapata, Sapata

from .avisos import AVISO_ESCOPO_COMPLETO

_CABECALHO = ("Seção", "Item", "Valor", "Unidade", "Situação")
_INF = float("inf")


def _situacao(ok: bool) -> str:
    return "OK" if ok else "NÃO OK"


def _fs(valor: float) -> object:
    return "inf" if valor == _INF else round(valor, 2)


def exportar_relatorio_excel(caminho, sapata: Sapata, resultado: ResultadoSapata,
                             proveniencia_sigma_adm: dict | None = None) -> None:
    """Escreve uma aba única, tabular, resumindo `resultado` — dimensões
    finais, classificação rígida/flexível, tensões por combinação (ou a
    crítica), armaduras por direção, verificações principais de estabilidade
    e punção, e o veredito geral (`resultado.aprovado`/`.reprovacoes`).

    `proveniencia_sigma_adm`, se fornecido (mesmo dicionário que
    `calc_core.sapata_isolada.relatorio.memorial` recebe — ver a docstring
    de lá para o contrato completo e para quem decide validade), acrescenta
    linhas logo abaixo de "Tensão admissível do solo" com
    `ROTULO_ELU`/`ROTULO_FONTE_NAO_NORMATIVA`, a origem do cálculo (D-02
    do GATE 2, rodada 3) e os avisos do núcleo (D-03 do GATE 2, rodada do
    redesenho + 1 — inclui a declaração regional do §7.3.3 (c) quando
    aplicável, exigida no memorial por REQ-UI-SIGMA-06, e o aviso literal
    do §6.3.2 quando o valor foi majorado por vento) — sem isto, um σ_adm
    calculado por `DialogoSigmaAdm` chegava a esta planilha como um número
    nu, indistinto de um valor digitado à mão a partir de investigação
    geotécnica.
    """
    livro = openpyxl.Workbook()
    ws = livro.active
    ws.title = "Resumo"
    ws.append(_CABECALHO)
    for cel in ws[1]:
        cel.font = Font(bold=True)

    def linha(secao: str, item: str, valor: object, unidade: str = "",
              situacao: str = "") -> None:
        ws.append([secao, item, valor, unidade, situacao])

    # ------------------------------------------------------------ aviso
    # Defeito D10 do GATE 2, rodada 1: esta planilha existe para circular
    # FORA da tela que mostra o banner de escopo (copiar/colar em outro
    # documento) — o aviso precisa ir junto, não só na tela.
    for i, paragrafo in enumerate(AVISO_ESCOPO_COMPLETO.split("\n\n"), start=1):
        linha("Aviso", f"#{i}", paragrafo.replace("\n", " "))

    # --------------------------------------------------------- identificação
    linha("Situação geral", "Resultado",
         "APROVADA" if resultado.aprovado else "REPROVADA")
    linha("Situação geral", "Modo",
         "Verificação (geometria imposta)" if resultado.modo_verificacao
         else "Dimensionamento automático")
    linha("Situação geral", "Convergiu", "Sim" if resultado.convergiu else "Não")
    if sapata is not None:
        linha("Situação geral", "Pilar",
             f"{sapata.pilar.ap*100:.0f} x {sapata.pilar.bp*100:.0f} cm")
        linha("Situação geral", "Concreto", f"C{sapata.concreto.fck:.0f}")
        linha("Situação geral", "Aço", f"CA-{sapata.aco.fyk:.0f}")
        linha("Situação geral", "Tensão admissível do solo",
             round(sapata.solo.sigma_adm, 0), "kPa")
        if proveniencia_sigma_adm is not None:
            linha("Situação geral", "  ↳ " + proveniencia_sigma_adm.get(
                 "rotulo_ELU", ""), "", "")
            linha("Situação geral", "  ↳ " + proveniencia_sigma_adm.get(
                 "rotulo_fonte", ""), "", "")
            linha("Situação geral", "  ↳ Origem do cálculo",
                 proveniencia_sigma_adm.get("origem", ""), "")
            for aviso in proveniencia_sigma_adm.get("avisos", None) or []:
                linha("Situação geral", "  ↳ Aviso do núcleo", aviso, "")

    # ------------------------------------------------------------- geometria
    linha("Geometria", "a (direção X)", round(resultado.a, 3), "m")
    linha("Geometria", "b (direção Y)", round(resultado.b, 3), "m")
    linha("Geometria", "h (altura total)", round(resultado.h, 3), "m")
    linha("Geometria", "h0 (altura da aba)", round(resultado.h0, 3), "m")
    linha("Geometria", "d (altura útil média)", round(resultado.d, 3), "m")
    linha("Geometria", "Volume de concreto", round(resultado.volume_concreto, 3), "m³")
    linha("Geometria", "Peso próprio + solo", round(resultado.peso_proprio, 1), "kN")
    linha("Geometria", "Inclinação da face", round(resultado.inclinacao_graus, 1),
         "graus")
    linha("Geometria", "Classificação",
         "RÍGIDA (NBR 6118, 22.6.1)" if resultado.rigida
         else "FLEXÍVEL (NBR 6118, 22.6.2.3)")

    # -------------------------------------------------------------- tensões
    for t in resultado.tensoes:
        linha("Tensões no solo (ELS-rara)",
             f"{t.combinacao} — σ_máx / limite",
             f"{t.sigma_max:.1f} / {t.limite:.1f}", "kPa", _situacao(t.ok))

    # ---------------------------------------------------------- estabilidade
    for e in resultado.estabilidade:
        linha("Estabilidade (deslizamento/tombamento)",
             f"{e.combinacao} — FS deslizamento", _fs(e.fs_deslizamento), "-",
             _situacao(e.ok))
        linha("Estabilidade (deslizamento/tombamento)",
             f"{e.combinacao} — FS tombamento X", _fs(e.fs_tombamento_x), "-", "")
        linha("Estabilidade (deslizamento/tombamento)",
             f"{e.combinacao} — FS tombamento Y", _fs(e.fs_tombamento_y), "-", "")

    # --------------------------------------------------------------- punção
    for p in resultado.puncao:
        linha("Punção/cisalhamento (NBR 6118, 19.5)",
             f"{p.contorno} ({p.combinacao})",
             f"{p.tau_sd:.1f} / {p.tau_rd:.1f}  (aprov. {p.aproveitamento:.2f})",
             "kPa", _situacao(p.ok))

    # ------------------------------------------------------------- armaduras
    for ar in resultado.armaduras:
        ok_direcao = (ar.as_suficiente and ar.dominio_ok and ar.ancoragem_ok
                     and ar.espacamento_ok)
        linha("Armadura de flexão", f"Direção {ar.direcao} — arranjo",
             f"{ar.n_barras} Ø {ar.phi_mm:.1f} mm c/ {ar.espacamento*100:.0f} cm",
             "", _situacao(ok_direcao))
        linha("Armadura de flexão",
             f"Direção {ar.direcao} — A_s adotada / efetiva",
             f"{ar.As_adot*1e4:.2f} / {ar.As_efetiva*1e4:.2f}", "cm²", "")

    # ----------------------------------------------------------- ancoragem
    if resultado.ancoragem_arranque:
        aa = resultado.ancoragem_arranque
        linha("Ancoragem dos arranques do pilar",
             "l_b necessário / disponível",
             f"{aa['lb_necessario']*100:.0f} / {aa['disponivel']*100:.0f}", "cm",
             _situacao(aa.get("ok", True)))

    # ------------------------------------------------------------ recalques
    if resultado.recalques:
        r = resultado.recalques
        linha("Recalques (NBR 6122, 6.2)", "Recalque total / limite",
             f"{r.recalque_total_mm:.1f} / {r.limite_mm:.0f}", "mm",
             _situacao(r.aprovado))

    # ------------------------------------------------------------ reprovações
    for i, falha in enumerate(resultado.reprovacoes, start=1):
        linha("Reprovações", f"#{i}", falha, "", "NÃO OK")
    for i, aviso in enumerate(resultado.alertas, start=1):
        linha("Alertas", f"#{i}", aviso, "", "")

    for col, largura in zip("ABCDE", (32, 46, 42, 10, 10)):
        ws.column_dimensions[col].width = largura

    livro.save(caminho)
