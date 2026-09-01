"""
relatorio.py
------------
Geração do memorial de cálculo em texto e exportação estruturada (dict/JSON).
"""
from __future__ import annotations

import json
from typing import Optional

from .sapata import ResultadoSapata, Sapata

LARG = 82


def _linha(c: str = "-") -> str:
    return c * LARG


def _titulo(txt: str) -> str:
    return f"\n{_linha('=')}\n{txt.upper()}\n{_linha('=')}"


def _sec(txt: str) -> str:
    return f"\n{txt}\n{_linha()}"


def memorial(res: ResultadoSapata, sapata: Optional[Sapata] = None,
             detalhar_combinacoes: int = 6,
             proveniencia_sigma_adm: Optional[dict] = None) -> str:
    """Memorial de cálculo em texto puro.

    `proveniencia_sigma_adm`, se fornecido, é o dicionário que
    `ui.completo.dialogo_sigma_adm.DialogoSigmaAdm._usar` monta quando o
    engenheiro escolhe um σ_adm calculado (`calc_core.geotecnico.sigma_adm`)
    em vez de digitar um valor — chaves esperadas: "origem" (texto livre já
    pronto), "rotulo_ELU" e "rotulo_fonte" (as constantes `ROTULO_ELU`/
    `ROTULO_FONTE_NAO_NORMATIVA` de `calc_core.modelos`, já formatadas).
    D-02 do GATE 2, rodada 3: decidir SE esse dicionário ainda é válido
    para o `sapata.solo.sigma_adm` que está sendo impresso (ou se ficou
    obsoleto por uma edição manual do campo, ou por um projeto/planilha
    carregado por cima) é responsabilidade de QUEM CHAMA
    (`ui.completo.formulario.PainelEntrada.ultimo_sigma_adm_calculado`,
    invalidado para `None` a cada edição que não seja o próprio
    preenchimento pelo diálogo) — esta função só formata o que já chegou
    pronto, sem juízo algum sobre proveniência (mesma regra "ui não
    calcula" do `a3-interface.md`, aplicada aqui por simetria: nenhuma
    parte deste módulo decide o que é ou não confiável, só imprime)."""
    L: list[str] = []
    L.append(_titulo("Memorial de cálculo - Sapata isolada"))
    L.append("Normas: ABNT NBR 6118:2023 e ABNT NBR 6122:2019")
    if res.modo_verificacao:
        L.append("MODO VERIFICAÇÃO: geometria imposta pelo projetista — a rotina "
                 "não alterou dimensões.")
    if any(a.imposta for a in res.armaduras):
        impostas = ", ".join(a.direcao for a in res.armaduras if a.imposta)
        L.append(f"Arranjo de armadura imposto pelo projetista na(s) direção(ões) "
                 f"{impostas}.")
    if sapata:
        p, s, c, a = sapata.pilar, sapata.solo, sapata.concreto, sapata.aco
        L.append(_sec("1. DADOS DE ENTRADA"))
        L.append(f"  Pilar ............... {p.ap*100:.0f} x {p.bp*100:.0f} cm")
        L.append(f"  Concreto ............ C{c.fck:.0f}  (fcd = {c.fcd:.2f} MPa, "
                 f"fctd = {c.fctd:.2f} MPa)")
        L.append(f"  Aço ................. CA-{a.fyk:.0f}  (fyd = {a.fyd:.1f} MPa)")
        L.append(f"  Cobrimento nominal .. {sapata.cobrimento*100:.1f} cm")
        L.append(f"  Tensão admissível ... {s.sigma_adm:.0f} kPa "
                 f"({s.sigma_adm/1000:.2f} MPa)")
        if proveniencia_sigma_adm is not None:
            L.append(f"    {proveniencia_sigma_adm.get('rotulo_ELU', '')}")
            L.append(f"    {proveniencia_sigma_adm.get('rotulo_fonte', '')}")
            L.append(f"    Origem do cálculo: "
                     f"{proveniencia_sigma_adm.get('origem', '')}")
        L.append(f"  Cota de assentamento  {s.hf:.2f} m ; "
                 f"gamma_solo = {s.gamma_solo:.1f} kN/m³ ; phi' = {s.phi:.0f}°")
        L.append(f"  Combinações geradas .. {len(sapata.combinacoes)} "
                 f"({len(sapata.combs_elu)} ELU, {len(sapata.combs_els)} ELS-rara)")

    # ---------------------------------------------------------------- geometria
    L.append(_sec("2. GEOMETRIA ADOTADA (Passos 1 e 2)"))
    L.append(f"  a (direção X) ....... {res.a:.2f} m")
    L.append(f"  b (direção Y) ....... {res.b:.2f} m")
    L.append(f"  h (altura total) .... {res.h:.2f} m")
    L.append(f"  h0 (altura da aba) .. {res.h0:.2f} m")
    L.append(f"  d (altura útil méd.)  {res.d:.3f} m")
    L.append(f"  Área da base ........ {res.a*res.b:.2f} m²")
    L.append(f"  Volume de concreto .. {res.volume_concreto:.3f} m³")
    L.append(f"  Peso próprio + solo . {res.peso_proprio:.1f} kN")
    L.append(f"  Inclinação da face .. {res.inclinacao_graus:.1f}°")
    L.append(f"  Sapata rígida ....... {'SIM' if res.rigida else 'NÃO'} "
             "(NBR 6118, 22.6.1)")

    if res.classificacao:
        c = res.classificacao
        L.append(_sec("2.1. RIGIDEZ E REAÇÃO DO SOLO"))
        L.append(f"  Critério NBR 6118, 22.6.1 ... h = {res.h:.2f} m contra "
                 f"{c.h_necessario:.2f} m para rigidez")
        L.append(f"  Comportamento normativo ..... "
                 f"{'RÍGIDA (22.6.2.2)' if c.rigida_nbr else 'FLEXÍVEL (22.6.2.3)'}")
        L.append(f"  Parâmetro de Hetényi ........ lambda*L = "
                 f"{max(c.lambda_L_x, c.lambda_L_y):.2f}  ->  {c.classe_hetenyi}")
        L.append(f"  Rigidez relativa (Meyerhof) . K_r = {c.rigidez_relativa:.2f}")
        L.append(f"  Modelo de reação adotado .... {res.modelo_reacao}")
        if c.rigida_nbr:
            L.append("  Ruptura por compressão diagonal; punção em C' é informativa.")
        else:
            L.append("  Verificação de punção obrigatória (NBR 6118, 22.6.2.3-b).")
        if res.grelha:
            g = res.grelha
            L.append(f"\n  Grelha discretizada — {g.n_gl} graus de liberdade, "
                     f"equilíbrio {g.equilibrio:.4f}")
            L.append(f"    Pressão máxima no contato .... {g.p_max:.1f} kPa")
            L.append(f"    M na face do pilar, direção X  {g.mx_face:.1f} kN.m/m")
            L.append(f"    M na face do pilar, direção Y  {g.my_face:.1f} kN.m/m")
            L.append(f"    Pico nodal (não usado no dimensionamento): "
                     f"Mx {g.mx_max:.1f} | My {g.my_max:.1f} kN.m/m")
            L.append("    O pico nodal cresce com o refinamento (singularidade "
                     "da carga concentrada); o dimensionamento usa o momento "
                     "na seção de referência, obtido por equilíbrio do balanço.")

        for r in res.reacoes.values():
            razao = (r.momento_face / r.momento_face_linear
                     if r.momento_face_linear else 1.0)
            L.append(f"\n  Direção {r.direcao} — k_v = {r.kv:.0f} kN/m³")
            L.append(f"    Pressão máxima: discretizada {r.p_max:.1f} kPa | "
                     f"modelo rígido {r.p_max_linear:.1f} kPa")
            L.append(f"    Momento na face: discretizado {r.momento_face:.1f} | "
                     f"rígido {r.momento_face_linear:.1f} kN.m/m ({razao:.2f}x)")
            L.append(f"    Recalque da peça: máx {max(r.recalque)*1000:.2f} mm | "
                     f"diferencial "
                     f"{abs(r.recalque[len(r.recalque)//2]-r.recalque[0])*1000:.2f} mm")

    # ------------------------------------------------------------------ tensões
    L.append(_sec("3. VERIFICAÇÃO GEOTÉCNICA - tensões na base (ELS raro)"))
    L.append(f"  {'Combinação':<26}{'s_max':>9}{'s_min':>9}{'s_méd':>9}"
             f"{'lim.':>8}{'Ac/A':>7}  status")
    L.append(f"  {'':<26}{'[kPa]':>9}{'[kPa]':>9}{'[kPa]':>9}{'[kPa]':>8}")
    piores = sorted(res.tensoes, key=lambda t: -t.sigma_max / max(t.limite, 1e-9))
    for t in piores[:detalhar_combinacoes]:
        ratio = t.area_comprimida / (res.a * res.b)
        L.append(f"  {t.combinacao[:25]:<26}{t.sigma_max:>9.1f}{t.sigma_min:>9.1f}"
                 f"{t.sigma_media:>9.1f}{t.limite:>8.0f}{ratio:>7.2f}  "
                 f"{'OK' if t.ok else '*** NÃO OK'}")
    pior = piores[0]
    L.append(f"\n  Combinação crítica: {pior.combinacao}")
    L.append(f"    e_x = {pior.ex*100:.1f} cm | e_y = {pior.ey*100:.1f} cm | "
             f"{pior.metodo}")
    L.append(f"    Núcleo central de inércia: "
             f"{'resultante DENTRO' if pior.dentro_nucleo else 'resultante FORA'}")

    # ------------------------------------------------------------- estabilidade
    L.append(_sec("4. ESTABILIDADE — deslizamento e tombamento"))
    L.append("  FS global = 1,5: PRÁTICA CONSAGRADA, SEM RESPALDO NORMATIVO "
             "DIRETO. A NBR 6122:2022")
    L.append("  §6.2.1.1.2 trata deslizamento/tombamento de fundação rasa só "
             "por coeficientes")
    L.append("  parciais (FS global equivalente de 1,68 a 2,35). Valor sob "
             "decisão de engenharia")
    L.append("  pendente — ver ruleset.yaml, regra "
             "NBR6122-6.2.1.1.2-tracao-deslizamento-tombamento.")
    L.append("")
    L.append(f"  {'Combinação':<30}{'FS desliz.':>12}{'FS tomb.X':>12}"
             f"{'FS tomb.Y':>12}  status")
    piores_e = sorted(res.estabilidade,
                      key=lambda e: min(e.fs_deslizamento, e.fs_tombamento_x,
                                        e.fs_tombamento_y))
    for e in piores_e[:detalhar_combinacoes]:
        L.append(f"  {e.combinacao[:29]:<30}{_fmt(e.fs_deslizamento):>12}"
                 f"{_fmt(e.fs_tombamento_x):>12}{_fmt(e.fs_tombamento_y):>12}  "
                 f"{'OK' if e.ok else '*** NÃO OK'}")

    # -------------------------------------------------------------------- punção
    L.append(_sec("5. VERIFICAÇÕES NO ELU - punção e cisalhamento (NBR 6118, 19.5)"))
    L.append(f"  {'Contorno':<48}{'Sd':>10}{'Rd':>10}{'Sd/Rd':>8}  status")
    agrupado: dict[str, object] = {}
    for p in res.puncao:
        chave = p.contorno
        atual = agrupado.get(chave)
        if atual is None or p.aproveitamento > atual.aproveitamento:
            agrupado[chave] = p
    for p in agrupado.values():
        L.append(f"  {p.contorno[:47]:<48}{p.tau_sd:>10.1f}{p.tau_rd:>10.1f}"
                 f"{p.aproveitamento:>8.2f}  {'OK' if p.ok else '*** NÃO OK'}")
        if p.observacao:
            L.append(f"      ({p.observacao})")

    # ----------------------------------------------------------------- armaduras
    if res.bielas:
        L.append(_sec("5.1. MODELO DE BIELAS E TIRANTES (NBR 6118, 22.6.3)"))
        for bl in res.bielas.values():
            L.append(f"  Direção {bl.direcao}:")
            L.append(f"    Resultante da reação no lado  {bl.R:.1f} kN, "
                     f"c.g. a {bl.x_R:.3f} m do eixo")
            L.append(f"    Braço interno z .............. {bl.z:.3f} m")
            L.append(f"    Inclinação da biela .......... {bl.theta:.1f}°"
                     + ("" if bl.inclinacao_ok else "  *** abaixo do recomendado"))
            L.append(f"    Força no tirante T ........... {bl.T:.1f} kN")
            L.append(f"    A_s pelo tirante ............. {bl.As*1e4:.2f} cm²")
            L.append(f"    Tensão na biela (indicativa) . {bl.sigma_biela/1000:.1f} MPa "
                     f"| nó CCC {bl.sigma_limite_ccc/1000:.1f} MPa")
        L.append("\n  A tensão na biela é indicativa: a expressão de Blévot é de")
        L.append("  blocos sobre estacas, onde a reação chega concentrada. Em sapata")
        L.append("  a reação é distribuída e vale a compressão diagonal do item 19.5.")

    L.append(_sec("6. ARMADURAS DE FLEXÃO (Passos 4 e 5)"))
    for ar in res.armaduras:
        L.append(f"  Direção {ar.direcao}:")
        L.append(f"    M_d ................. {ar.Md:.1f} kN.m")
        L.append(f"    d ................... {ar.d:.3f} m   (x/d = {ar.x_d:.3f}"
                 f"{'' if ar.dominio_ok else '  *** ACIMA DO LIMITE DE DUCTILIDADE'})")
        L.append(f"    Modelo adotado ...... {ar.modelo}")
        L.append(f"    A_s,calc ............ {ar.As_calc*1e4:.2f} cm²"
                 + (f"  (flexão {ar.As_flexao*1e4:.2f} | bielas "
                    f"{ar.As_bielas*1e4:.2f})" if ar.As_bielas else ""))
        L.append(f"    A_s,mín ............. {ar.As_min*1e4:.2f} cm²  "
                 "(NBR 6118, 19.3.3.2)")
        L.append(f"    A_s adotada ......... {ar.As_adot*1e4:.2f} cm²")
        L.append(f"    Detalhamento ........ {ar.n_barras} phi {ar.phi_mm:.1f} mm "
                 f"c/ {ar.espacamento*100:.0f} cm  "
                 f"(A_s,ef = {ar.As_efetiva*1e4:.2f} cm²)"
                 + ("  [imposto]" if ar.imposta else ""))
        if not ar.as_suficiente:
            L.append("    *** A_s efetiva ABAIXO da necessária")
        L.append(f"    Ancoragem ........... l_b,nec = {ar.lb_necessario*100:.0f} cm "
                 f"| disponível = {ar.lb_disponivel*100:.0f} cm  "
                 f"{'OK' if ar.ancoragem_ok else '*** usar gancho/aumentar aba'}")

    if res.ancoragem_arranque:
        aa = res.ancoragem_arranque
        L.append(f"\n  Arranques do pilar (phi {aa['phi_mm']:.1f} mm):")
        L.append(f"    l_b básico .......... {aa['lb_basico']*100:.0f} cm")
        L.append(f"    l_b necessário ...... {aa['lb_necessario']*100:.0f} cm")
        L.append(f"    Altura disponível ... {aa['disponivel']*100:.0f} cm  "
                 f"{'OK' if aa['ok'] else '*** NÃO OK'}")

    # ----------------------------------------------------------------- recalques
    if res.recalques:
        r = res.recalques
        L.append(_sec("7. ANÁLISE DE RECALQUES POR SUBSTRATO (NBR 6122, 6.2)"))
        L.append(f"  Tensão líquida na base .......... {r.q_liquido:.1f} kPa")
        L.append(f"  Profundidade de influência ...... {r.profundidade_influencia:.2f} m")
        L.append(f"  Recalque imediato (elástico) .... {r.recalque_imediato_mm:.1f} mm")
        L.append(f"  Recalque por adensamento ........ {r.recalque_adensamento_mm:.1f} mm")
        L.append(f"  Compressão secundária ........... {r.recalque_secundario_mm:.1f} mm")
        L.append(f"  {'RECALQUE TOTAL ESTIMADO':<32} {r.recalque_total_mm:.1f} mm "
                 f"(limite: {r.limite_mm:.0f} mm)  "
                 f"{'OK' if r.aprovado else '*** NÃO OK'}")
        L.append(f"\n  Referências cruzadas:")
        L.append(f"    Elástico global (I_w rígido) .. "
                 f"{r.recalque_elastico_global_mm:.1f} mm")
        if r.recalque_schmertmann_mm is not None:
            L.append(f"    Schmertmann (1978) ............ "
                     f"{r.recalque_schmertmann_mm:.1f} mm")
        L.append(f"\n  {'Camada':<18}{'z [m]':>13}{'s_v0':>9}{'Ds':>9}"
                 f"{'rec.[mm]':>10}  método")
        for pc in r.parcelas:
            L.append(f"  {pc.camada[:17]:<18}"
                     f"{f'{pc.z_topo:.2f}-{pc.z_base:.2f}':>13}"
                     f"{pc.sigma_v0:>9.1f}{pc.delta_sigma:>9.1f}"
                     f"{pc.recalque_mm:>10.2f}  {pc.metodo}")
        if r.tempos:
            L.append("\n  Evolução do adensamento:")
            for nome, t50, t90 in r.tempos:
                L.append(f"    {nome:<20} t(U=50%) = {t50:.2f} anos | "
                         f"t(U=90%) = {t90:.2f} anos")
        for al in r.alertas:
            L.append(f"  [!] {al}")

    # ------------------------------------------------------------------ resumo
    L.append(_sec("8. CONCLUSÃO"))
    L.append(f"  Sapata {res.a:.2f} x {res.b:.2f} x {res.h:.2f} m "
             f"(aba h0 = {res.h0:.2f} m)")
    for ar in res.armaduras:
        L.append(f"  Armadura {ar.direcao}: {ar.n_barras} phi {ar.phi_mm:.1f} "
                 f"c/ {ar.espacamento*100:.0f} cm")
    L.append(f"  SITUAÇÃO GERAL: "
             f"{'APROVADA' if res.aprovado else 'REPROVADA'}")
    if res.reprovacoes:
        L.append("\n  Verificações não atendidas:")
        for f in res.reprovacoes:
            L.append(f"  [X] {f}")
    if res.alertas:
        L.append("\n  Alertas:")
        for al in res.alertas:
            L.append(f"  [!] {al}")
    L.append(_linha("="))
    return "\n".join(L)


def _fmt(v: float) -> str:
    return "inf" if v == float("inf") else f"{v:.2f}"


def para_json(res: ResultadoSapata, caminho: Optional[str] = None,
              indent: int = 2) -> str:
    """Serializa o resultado completo em JSON."""
    texto = json.dumps(res.para_dicionario(), indent=indent, ensure_ascii=False,
                       default=str)
    if caminho:
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(texto)
    return texto
