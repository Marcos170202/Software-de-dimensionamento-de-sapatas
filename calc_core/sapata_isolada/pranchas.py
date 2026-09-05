"""
pranchas.py
-----------
Monta o memorial em PDF: pranchas de fôrmas, armação e perfil geotécnico
desenhadas em escala, seguidas do memorial de cálculo em texto.

Formato padrão A3 paisagem (420 x 297 mm), com moldura e carimbo.
"""
from __future__ import annotations

import math
from datetime import date
from typing import Optional, Sequence

from .momentos import (CampoMomentos, campo_momentos, cor_isovalor,
                       curvas_nivel, niveis_uteis)
from .pdf import A3_PAISAGEM, PDF, largura_texto
from .relatorio import memorial

# ------------------------------------------------------------------ paleta
PRETO = (0.10, 0.12, 0.14)
CINZA = (0.45, 0.48, 0.50)
CINZA_CLARO = (0.72, 0.74, 0.75)
CONCRETO = (0.88, 0.89, 0.87)
COTA = (0.05, 0.42, 0.52)
ACO = (0.72, 0.20, 0.12)
VERMELHO = (0.66, 0.21, 0.17)
VERDE = (0.17, 0.48, 0.34)

CORES_SUBSTRATO = {
    "granular": (0.84, 0.71, 0.35),
    "coesivo": (0.55, 0.65, 0.53),
    "aterro": (0.66, 0.56, 0.42),
    "rocha": (0.52, 0.58, 0.64),
}

MARGEM = 10.0
CARIMBO_L, CARIMBO_A = 130.0, 34.0


# =========================================================================== #
#  Moldura e carimbo
# =========================================================================== #
def moldura(pdf: PDF, titulo: str, subtitulo: str, folha: str,
            obra: str, projetista: str, escala: str = "indicada") -> None:
    L, A = pdf.largura, pdf.altura
    pdf.retangulo(MARGEM, MARGEM, L - 2 * MARGEM, A - 2 * MARGEM,
                  contorno=PRETO, espessura=0.6)

    cx, cy = L - MARGEM - CARIMBO_L, MARGEM
    pdf.retangulo(cx, cy, CARIMBO_L, CARIMBO_A, contorno=PRETO, espessura=0.6)
    pdf.linha(cx, cy + 22, cx + CARIMBO_L, cy + 22, 0.3, PRETO)
    pdf.linha(cx, cy + 11, cx + CARIMBO_L, cy + 11, 0.3, PRETO)
    pdf.linha(cx + 82, cy, cx + 82, cy + 11, 0.3, PRETO)

    pdf.texto(cx + 3, cy + 26.5, obra[:58], 8.5, PRETO, negrito=True)
    pdf.texto(cx + 3, cy + 15.5, titulo[:60], 9.5, PRETO, negrito=True)
    pdf.texto(cx + 3, cy + 6.5, f"Escala {escala}", 7, CINZA)
    pdf.texto(cx + 3, cy + 2.5, f"Projeto: {projetista[:36]}", 7, CINZA)
    pdf.texto(cx + 85, cy + 6.5, f"Folha {folha}", 7.5, PRETO, negrito=True)
    pdf.texto(cx + 85, cy + 2.5, date.today().strftime("%d/%m/%Y"), 7, CINZA)

    pdf.texto(MARGEM + 4, A - MARGEM - 8, titulo, 13, PRETO, negrito=True)
    pdf.texto(MARGEM + 4, A - MARGEM - 13.5, subtitulo, 8, CINZA)
    pdf.linha(MARGEM, A - MARGEM - 17, L - MARGEM, A - MARGEM - 17, 0.4, PRETO)
    pdf.texto(L - MARGEM - 4, A - MARGEM - 13.5,
              "ABNT NBR 6118:2023 / NBR 6122:2019", 7, CINZA, ancora="se")


# =========================================================================== #
#  Vista em escala e cotagem
# =========================================================================== #
class Vista:
    """Mapeia coordenadas do modelo (m) para a folha (mm), em escala fixa."""

    def __init__(self, pdf: PDF, cx: float, cy: float, escala: float) -> None:
        self.pdf = pdf
        self.cx, self.cy = cx, cy          # centro da vista na folha [mm]
        self.escala = escala               # mm de folha por metro de modelo

    @classmethod
    def ajustada(cls, pdf: PDF, cx: float, cy: float, larg_m: float, alt_m: float,
                 larg_mm: float, alt_mm: float) -> "Vista":
        e = min(larg_mm / max(larg_m, 1e-6), alt_mm / max(alt_m, 1e-6))
        # arredonda para escala de desenho usual
        for candidata in (100, 50, 40, 33.33, 25, 20, 16.67, 12.5, 10, 8, 6.67, 5, 4, 2):
            if candidata <= e:
                e = candidata
                break
        return cls(pdf, cx, cy, e)

    @property
    def denominador(self) -> float:
        return 1000.0 / self.escala        # 1:N

    def px(self, x: float) -> float:
        return self.cx + x * self.escala

    def py(self, y: float) -> float:
        return self.cy + y * self.escala

    def p(self, x: float, y: float) -> tuple[float, float]:
        return (self.px(x), self.py(y))

    # ------------------------------------------------------------- cotagem
    def cota_h(self, x0: float, x1: float, y: float, desloc: float,
               texto: Optional[str] = None, tam: float = 6.5) -> None:
        """Cota horizontal; desloc em mm de folha (positivo para cima)."""
        pdf = self.pdf
        ya = self.py(y) + desloc
        for x in (x0, x1):
            pdf.linha(self.px(x), self.py(y), self.px(x), ya + math.copysign(1.5, desloc),
                      0.15, COTA)
        pdf.linha(self.px(x0), ya, self.px(x1), ya, 0.2, COTA)
        for x in (x0, x1):
            pdf.linha(self.px(x) - 1.2, ya - 1.2, self.px(x) + 1.2, ya + 1.2, 0.3, COTA)
        rot = texto if texto is not None else f"{abs(x1 - x0):.2f}".replace(".", ",")
        pdf.texto((self.px(x0) + self.px(x1)) / 2, ya + 1.4, rot, tam, COTA,
                  ancora="center")

    def cota_v(self, y0: float, y1: float, x: float, desloc: float,
               texto: Optional[str] = None, tam: float = 6.5) -> None:
        pdf = self.pdf
        xa = self.px(x) + desloc
        for y in (y0, y1):
            pdf.linha(self.px(x), self.py(y), xa + math.copysign(1.5, desloc),
                      self.py(y), 0.15, COTA)
        pdf.linha(xa, self.py(y0), xa, self.py(y1), 0.2, COTA)
        for y in (y0, y1):
            pdf.linha(xa - 1.2, self.py(y) - 1.2, xa + 1.2, self.py(y) + 1.2, 0.3, COTA)
        rot = texto if texto is not None else f"{abs(y1 - y0):.2f}".replace(".", ",")
        pdf.texto(xa + 1.5, (self.py(y0) + self.py(y1)) / 2, rot, tam, COTA,
                  rotacao=90, ancora="center")


def titulo_vista(pdf: PDF, x: float, y: float, txt: str, escala: float) -> None:
    pdf.texto(x, y, txt, 9, PRETO, negrito=True)
    larg = largura_texto(txt, 9)
    pdf.texto(x + larg + 6, y + 0.4, f"esc. 1:{escala:.0f}", 6.5, CINZA)
    pdf.linha(x, y - 1.8, x + larg, y - 1.8, 0.4, PRETO)


# =========================================================================== #
#  Prancha 1 — FÔRMAS
# =========================================================================== #
def prancha_formas(pdf: PDF, res, mod: dict, obra: str, projetista: str,
                   folha: str) -> None:
    a, b, h, h0 = res.a, res.b, res.h, res.h0
    at, bt = mod["at"], mod["bt"]
    ap, bp = mod["ap"], mod["bp"]

    v_planta = Vista.ajustada(pdf, 118, 168, a * 1.45, b * 1.45, 165, 125)
    esc = v_planta.denominador
    moldura(pdf, "SAPATA ISOLADA — FÔRMAS",
            f"Sapata {a:.2f} × {b:.2f} × {h:.2f} m · pilar {ap*100:.0f}×{bp*100:.0f} cm",
            folha, obra, projetista, f"1:{esc:.0f}")

    # ------------------------------------------------------------- PLANTA
    titulo_vista(pdf, 30, 252, "PLANTA DE FÔRMAS", esc)
    P = v_planta
    pdf.poligono([P.p(-a/2, -b/2), P.p(a/2, -b/2), P.p(a/2, b/2), P.p(-a/2, b/2)],
                 CONCRETO, PRETO, 0.5)
    # aresta superior do tronco
    pdf.poligono([P.p(-at/2, -bt/2), P.p(at/2, -bt/2), P.p(at/2, bt/2), P.p(-at/2, bt/2)],
                 None, PRETO, 0.35)
    for sx in (-1, 1):
        for sy in (-1, 1):
            pdf.linha(*P.p(sx*a/2, sy*b/2), *P.p(sx*at/2, sy*bt/2), 0.2, CINZA)
    # pilar
    pdf.poligono([P.p(-ap/2, -bp/2), P.p(ap/2, -bp/2), P.p(ap/2, bp/2), P.p(-ap/2, bp/2)],
                 (0.78, 0.80, 0.79), PRETO, 0.45)
    # eixos
    pdf.linha(P.px(-a/2) - 8, P.py(0), P.px(a/2) + 8, P.py(0), 0.15, VERMELHO, [4, 1.5, 1, 1.5])
    pdf.linha(P.px(0), P.py(-b/2) - 8, P.px(0), P.py(b/2) + 8, 0.15, VERMELHO, [4, 1.5, 1, 1.5])

    P.cota_h(-a/2, a/2, -b/2, -14)
    P.cota_h(-ap/2, ap/2, b/2, 8, f"{ap:.2f}".replace(".", ","), 6)
    P.cota_v(-b/2, b/2, a/2, 14)
    P.cota_v(-bp/2, bp/2, -a/2, -16, f"{bp:.2f}".replace(".", ","), 6)
    # indicação dos cortes
    pdf.texto(P.px(-a/2) - 6, P.py(0) - 1, "A", 8, VERMELHO, negrito=True)
    pdf.texto(P.px(a/2) + 3, P.py(0) - 1, "A", 8, VERMELHO, negrito=True)
    pdf.texto(P.px(0) - 1.5, P.py(b/2) + 5, "B", 8, VERMELHO, negrito=True)
    pdf.texto(P.px(0) - 1.5, P.py(-b/2) - 9, "B", 8, VERMELHO, negrito=True)

    # ------------------------------------------------------- CORTES A-A e B-B
    def corte(cx, cy, dim, dim_t, dim_p, rotulo, largura_mm=150):
        v = Vista.ajustada(pdf, cx, cy, dim * 1.30, (h + 0.75) * 1.55, largura_mm, 62)
        e = v.denominador
        titulo_vista(pdf, cx - largura_mm / 2, cy + 46, rotulo, e)
        # solo de apoio (hachura simplificada)
        y0 = 0.0
        pdf.linha(v.px(-dim/2) - 10, v.py(y0), v.px(dim/2) + 10, v.py(y0), 0.3, CINZA)
        for i in range(18):
            x = v.px(-dim/2) - 10 + i * ((dim * v.escala + 20) / 17)
            pdf.linha(x, v.py(y0), x - 2.5, v.py(y0) - 2.5, 0.15, CINZA)
        # sapata: aba + tronco
        pdf.poligono([v.p(-dim/2, 0), v.p(dim/2, 0), v.p(dim/2, h0), v.p(-dim/2, h0)],
                     CONCRETO, PRETO, 0.5)
        pdf.poligono([v.p(-dim/2, h0), v.p(dim/2, h0), v.p(dim_t/2, h), v.p(-dim_t/2, h)],
                     CONCRETO, PRETO, 0.5)
        # pilar
        pdf.poligono([v.p(-dim_p/2, h), v.p(dim_p/2, h), v.p(dim_p/2, h + 0.55),
                      v.p(-dim_p/2, h + 0.55)], (0.78, 0.80, 0.79), PRETO, 0.45)
        # lastro de concreto magro
        pdf.retangulo(v.px(-dim/2) - 2, v.py(0) - 0.05 * v.escala,
                      dim * v.escala + 4, 0.05 * v.escala,
                      (0.80, 0.80, 0.78), CINZA, 0.2)
        pdf.texto(v.px(dim/2) + 4, v.py(0) - 0.05 * v.escala - 1,
                  "lastro concreto magro 5 cm", 5.5, CINZA)

        v.cota_h(-dim/2, dim/2, 0, -12)
        v.cota_v(0, h0, dim/2, 10, f"{h0:.2f}".replace(".", ","), 5.8)
        v.cota_v(0, h, dim/2, 28, f"{h:.2f}".replace(".", ","))
        inclin = math.degrees(math.atan2(h - h0, (dim - dim_t) / 2))
        pdf.texto(v.px(dim / 4), v.py(h0 + (h - h0) * 0.55),
                  f"{inclin:.0f}°", 6, CINZA)
        return e

    if res.reprovacoes:
        pdf.texto(28, 250, "*** NÃO ATENDE: " + res.reprovacoes[0][:78], 7,
                  VERMELHO, negrito=True)
    corte(312, 205, a, at, ap, "CORTE A-A")
    corte(312, 118, b, bt, bp, "CORTE B-B")

    # ---------------------------------------------------- quadro de geometria
    quadro(pdf, 28, 78, 155, [
        ("Dimensão a (direção X)", f"{a:.2f} m"),
        ("Dimensão b (direção Y)", f"{b:.2f} m"),
        ("Altura total h", f"{h:.2f} m"),
        ("Altura da aba h0", f"{h0:.2f} m"),
        ("Cota de assentamento", f"{mod['hf']:.2f} m"),
        ("Volume de concreto", f"{res.volume_concreto:.3f} m³"),
        ("Área de fôrma (faces laterais)", f"{2 * (a + b) * h0:.2f} m²"),
        ("Inclinação das faces", f"{res.inclinacao_graus:.1f}°"
         + ("  (dispensa fôrma)" if res.inclinacao_graus <= 30 else "  (exige fôrma)")),
        ("Cobrimento nominal", f"{mod['cobrimento']*100:.1f} cm"),
        ("Sapata rígida (22.6.1)", "sim" if res.rigida else "NÃO"),
    ], "GEOMETRIA")


# =========================================================================== #
#  Prancha 2 — ARMAÇÃO
# =========================================================================== #
def prancha_armacao(pdf: PDF, res, mod: dict, obra: str, projetista: str,
                    folha: str) -> None:
    pdf.nova_pagina()
    a, b, h, h0 = res.a, res.b, res.h, res.h0
    cob = mod["cobrimento"]
    arX = next(x for x in res.armaduras if x.direcao == "X")
    arY = next(x for x in res.armaduras if x.direcao == "Y")

    P = Vista.ajustada(pdf, 112, 185, a * 1.32, b * 1.32, 150, 108)
    esc = P.denominador
    moldura(pdf, "SAPATA ISOLADA — ARMAÇÃO",
            f"N1 {arX.n_barras}ØC{arX.phi_mm:.1f} c/{arX.espacamento*100:.0f} · "
            f"N2 {arY.n_barras}ØC{arY.phi_mm:.1f} c/{arY.espacamento*100:.0f}",
            folha, obra, projetista, f"1:{esc:.0f}")

    # ------------------------------------------------------------- PLANTA
    titulo_vista(pdf, 30, 252, "PLANTA DE ARMAÇÃO — MALHA INFERIOR", esc)
    pdf.poligono([P.p(-a/2, -b/2), P.p(a/2, -b/2), P.p(a/2, b/2), P.p(-a/2, b/2)],
                 None, CINZA_CLARO, 0.4)
    pdf.poligono([P.p(-mod["ap"]/2, -mod["bp"]/2), P.p(mod["ap"]/2, -mod["bp"]/2),
                  P.p(mod["ap"]/2, mod["bp"]/2), P.p(-mod["ap"]/2, mod["bp"]/2)],
                 None, CINZA, 0.3)

    util_y = b - 2 * cob
    for i in range(arX.n_barras):
        y = -util_y / 2 + (util_y * i / max(arX.n_barras - 1, 1))
        pdf.linha(P.px(-a/2 + cob), P.py(y), P.px(a/2 - cob), P.py(y), 0.25, ACO)
    util_x = a - 2 * cob
    for i in range(arY.n_barras):
        x = -util_x / 2 + (util_x * i / max(arY.n_barras - 1, 1))
        pdf.linha(P.px(x), P.py(-b/2 + cob), P.px(x), P.py(b/2 - cob), 0.25, ACO)

    _chamada(pdf, P.px(a/2 - cob) - 12, P.py(util_y/2 * 0.55), P.px(a/2) + 16, P.py(b/2) + 6,
             f"N1  {arX.n_barras} Ø {arX.phi_mm:.1f} c/{arX.espacamento*100:.0f} — "
             f"C={arX.comprimento_barra:.2f}")
    _chamada(pdf, P.px(-util_x/2 * 0.55), P.py(-b/2 + cob) + 12, P.px(-a/2) + 4,
             P.py(-b/2) - 22,
             f"N2  {arY.n_barras} Ø {arY.phi_mm:.1f} c/{arY.espacamento*100:.0f} — "
             f"C={arY.comprimento_barra:.2f}", ancora="se")

    P.cota_h(-a/2, a/2, -b/2, -13)
    P.cota_v(-b/2, b/2, a/2, 12)

    # --------------------------------------------------------- CORTE ARMADO
    v = Vista.ajustada(pdf, 305, 208, a * 1.28, (h + 0.7) * 1.5, 140, 60)
    ec = v.denominador
    titulo_vista(pdf, 235, 252, "CORTE — POSIÇÃO DAS BARRAS", ec)
    pdf.poligono([v.p(-a/2, 0), v.p(a/2, 0), v.p(a/2, h0), v.p(-a/2, h0)],
                 CONCRETO, CINZA, 0.35)
    pdf.poligono([v.p(-a/2, h0), v.p(a/2, h0), v.p(mod["at"]/2, h), v.p(-mod["at"]/2, h)],
                 CONCRETO, CINZA, 0.35)
    # N1 em corte, com os ganchos
    yb = cob
    pdf.polilinha([v.p(-a/2 + cob, yb + arX.gancho), v.p(-a/2 + cob, yb),
                   v.p(a/2 - cob, yb), v.p(a/2 - cob, yb + arX.gancho)], 0.5, ACO)
    # N2 em seção (pontos)
    for i in range(min(arY.n_barras, 26)):
        x = -util_x / 2 + (util_x * i / max(min(arY.n_barras, 26) - 1, 1))
        pdf.circulo(v.px(x), v.py(cob + 0.014), 0.45, ACO, None)
    # arranques
    arr = res.ancoragem_arranque
    for sx in (-1, 1):
        x = sx * (mod["ap"] / 2 - cob)
        pdf.polilinha([v.p(x, h + 0.5), v.p(x, cob + 0.03),
                       v.p(x - sx * 0.12, cob + 0.03)], 0.45, ACO)
    pdf.texto(v.px(0), v.py(h + 0.58),
              f"arranques Ø{arr['phi_mm']:.1f} — l_b = {arr['lb_necessario']*100:.0f} cm",
              6, CINZA, ancora="center")
    v.cota_v(0, h, -a/2, -10, f"{h:.2f}".replace(".", ","), 6)
    pdf.texto(v.px(a/2) + 3, v.py(cob), f"cobr. {cob*100:.1f}", 5.5, CINZA)

    # -------------------------------------------------- ESQUEMA DAS BARRAS
    pdf.texto(30, 108, "ESQUEMA DE DOBRAMENTO", 9, PRETO, negrito=True)
    pdf.linha(30, 106.2, 92, 106.2, 0.4, PRETO)
    _esquema_barra(pdf, 40, 84, arX, "N1")
    _esquema_barra(pdf, 40, 56, arY, "N2")

    # ---------------------------------------------------- QUADRO DE FERROS
    linhas = []
    total_peso = 0.0
    if any(a.imposta for a in res.armaduras):
        pdf.texto(240, 172, "Arranjo definido pelo projetista", 6.5, VERMELHO)
    if res.modo_verificacao:
        pdf.texto(28, 250, "MODO VERIFICAÇÃO — geometria imposta", 7, VERMELHO,
                  negrito=True)
    for pos, ar in (("N1", arX), ("N2", arY)):
        total_peso += ar.peso_total
        linhas.append((pos, f"{ar.phi_mm:.1f}", str(ar.n_barras),
                       f"{ar.comprimento_barra:.2f}",
                       f"{ar.n_barras * ar.comprimento_barra:.2f}",
                       f"{ar.peso_total:.1f}"))
    tabela(pdf, 240, 160, [24, 22, 18, 28, 30, 26],
           ["Pos.", "Ø (mm)", "Qtd.", "C. unit. (m)", "C. total (m)", "Peso (kg)"],
           linhas, "QUADRO DE FERROS")
    pdf.texto(240, 160 - 12 - 5 * len(linhas) - 5,
              f"Peso total de aço CA-50: {total_peso:.1f} kg  "
              f"(+10% de perdas: {total_peso * 1.1:.1f} kg)", 7, PRETO, negrito=True)

    quadro(pdf, 240, 118, 148, [
        ("A_s,calc direção X", f"{arX.As_calc*1e4:.2f} cm²"),
        ("A_s,mín direção X", f"{arX.As_min*1e4:.2f} cm²"),
        ("A_s efetiva direção X", f"{arX.As_efetiva*1e4:.2f} cm²"),
        ("A_s,calc direção Y", f"{arY.As_calc*1e4:.2f} cm²"),
        ("A_s,mín direção Y", f"{arY.As_min*1e4:.2f} cm²"),
        ("A_s efetiva direção Y", f"{arY.As_efetiva*1e4:.2f} cm²"),
    ], "ÁREAS DE AÇO")


def _esquema_barra(pdf: PDF, x: float, y: float, ar, pos: str) -> None:
    """Desenho fora de escala da barra dobrada, com as cotas de corte."""
    esc = 100.0 / max(ar.comprimento_reto, 0.1)     # o trecho reto ocupa 100 mm
    g = ar.gancho * esc
    pdf.polilinha([(x, y + g), (x, y), (x + 100, y), (x + 100, y + g)], 0.7, ACO)
    pdf.texto(x + 50, y - 5, f"{ar.comprimento_reto:.2f}".replace(".", ","), 6.5,
              COTA, ancora="center")
    pdf.linha(x, y - 2.5, x + 100, y - 2.5, 0.2, COTA)
    for gx in (x, x + 100):
        pdf.linha(gx, y - 1.2, gx, y - 3.8, 0.2, COTA)
        pdf.texto(gx + (2.5 if gx == x else -2.5), y + g / 2,
                  f"{ar.gancho*100:.0f}", 6, COTA,
                  ancora="sw" if gx == x else "se")
    pdf.texto(x - 6, y + 1,
              f"{pos}", 8, PRETO, negrito=True)
    pdf.texto(x + 106, y + 1,
              f"{ar.n_barras} Ø {ar.phi_mm:.1f} mm — C = {ar.comprimento_barra:.2f} m",
              7, PRETO)
    pdf.texto(x + 106, y - 3.5,
              f"c/ {ar.espacamento*100:.0f} cm · peso {ar.peso_total:.1f} kg", 6.2, CINZA)


def _chamada(pdf: PDF, x0: float, y0: float, x1: float, y1: float, txt: str,
             ancora: str = "sw") -> None:
    pdf.linha(x0, y0, x1, y1, 0.2, PRETO)
    pdf.circulo(x0, y0, 0.6, PRETO, None)
    pdf.texto(x1 + (1.5 if ancora == "sw" else -1.5), y1 + 1, txt, 6.5, PRETO,
              ancora=ancora)


# =========================================================================== #
#  Prancha 3 — MOMENTOS FLETORES (isovalores)
# =========================================================================== #
def prancha_momentos(pdf: PDF, res, campo: CampoMomentos, obra: str,
                     projetista: str, folha: str) -> None:
    pdf.nova_pagina()
    moldura(pdf, "SAPATA ISOLADA — MOMENTOS FLETORES",
            f"Isovalores em planta · combinação {campo.combinacao}",
            folha, obra, projetista, "indicada")

    _mapa(pdf, 112, 170, campo, "X", res)
    _mapa(pdf, 292, 170, campo, "Y", res)

    arX = next(a for a in res.armaduras if a.direcao == "X")
    arY = next(a for a in res.armaduras if a.direcao == "Y")
    quadro(pdf, 28, 80, 175, [
        ("Combinação governante", campo.combinacao[:34]),
        ("σ na base (cálculo)", f"{campo.sigma_min:.0f} a {campo.sigma_max:.0f} kPa"),
        ("m máx — arma direção X", f"{campo.mx_max:.1f} kN·m/m"),
        ("M_d integrado na largura b", f"{campo.mx_max * campo.b:.1f} kN·m"),
        ("M_d adotado direção X", f"{arX.Md:.1f} kN·m"),
        ("m máx — arma direção Y", f"{campo.my_max:.1f} kN·m/m"),
        ("M_d integrado na largura a", f"{campo.my_max * campo.a:.1f} kN·m"),
        ("M_d adotado direção Y", f"{arY.Md:.1f} kN·m"),
    ], "VALORES DE PROJETO")

    # acima do carimbo, para não sobrepor
    pdf.retangulo(215, 50, 172, 44, (0.97, 0.97, 0.96), PRETO, 0.35)
    pdf.texto(218, 87, "COMO LER", 7.5, PRETO, negrito=True)
    for i, linha in enumerate([
            "Momento por unidade de largura do balanço, com a pressão do solo",
            "da combinação última governante. A seção de referência é a face do",
            "pilar (prática de engenharia, não item normativo): sob o pilar o",
            "valor é mantido no patamar da face, e não cresce. A armadura é",
            "dimensionada pela faixa de borda mais solicitada, por isso o M_d",
            "adotado corresponde ao pico do mapa integrado na largura da sapata."]):
        pdf.texto(218, 80 - i * 4.4, linha, 6.2, CINZA)

    if campo.alertas:
        for i, a in enumerate(campo.alertas):
            pdf.texto(28, 26 - i * 4.5, "[!] " + a[:118], 6.2, VERMELHO)


def _mapa(pdf: PDF, cx: float, cy: float, campo: CampoMomentos, direcao: str,
          res) -> None:
    """Mapa de isovalores de uma direção, com escala de cores ao lado."""
    valores = campo.faixa(direcao)
    vmax = max(max(l) for l in valores)
    largura_mm, altura_mm = 132.0, 118.0
    esc = min(largura_mm / campo.a, altura_mm / campo.b)
    xs, ys = campo.x, campo.y

    def px(x):
        return cx + x * esc

    def py(y):
        return cy + y * esc

    rot = (f"MOMENTO QUE ARMA A DIREÇÃO {direcao}")
    titulo_vista(pdf, cx - campo.a * esc / 2, cy + campo.b * esc / 2 + 12, rot,
                 1000.0 / esc)

    for j in range(len(ys) - 1):
        for i in range(len(xs) - 1):
            v = (valores[j][i] + valores[j][i + 1]
                 + valores[j + 1][i] + valores[j + 1][i + 1]) / 4.0
            cor = cor_isovalor(v / vmax if vmax > 0 else 0.0)
            pdf.retangulo(px(xs[i]), py(ys[j]), (xs[i + 1] - xs[i]) * esc + 0.06,
                          (ys[j + 1] - ys[j]) * esc + 0.06, cor, None)

    for nivel in niveis_uteis(vmax, 8):
        for (p, q) in curvas_nivel(xs, ys, valores, nivel):
            pdf.linha(px(p[0]), py(p[1]), px(q[0]), py(q[1]), 0.12, (0.15, 0.18, 0.20))

    a, b, ap, bp = campo.a, campo.b, campo.ap, campo.bp
    pdf.retangulo(px(-a/2), py(-b/2), a * esc, b * esc, None, PRETO, 0.5)
    pdf.retangulo(px(-ap/2), py(-bp/2), ap * esc, bp * esc, None, PRETO, 0.35)
    if direcao == "X":
        for sx in (-1, 1):
            pdf.linha(px(sx*ap/2), py(-b/2), px(sx*ap/2), py(b/2), 0.35,
                      (0.90, 0.45, 0.15), [2, 1.5])
    else:
        for sy in (-1, 1):
            pdf.linha(px(-a/2), py(sy*bp/2), px(a/2), py(sy*bp/2), 0.35,
                      (0.90, 0.45, 0.15), [2, 1.5])

    pdf.texto(cx, py(-b/2) - 5, f"máx {vmax:.1f} kN·m/m", 7, PRETO,
              ancora="center", negrito=True)

    # escala de cores
    ex = px(a/2) + 7
    ey0, ey1 = py(-b/2), py(b/2)
    n = 40
    for i in range(n):
        t = i / n
        pdf.retangulo(ex, ey0 + (ey1 - ey0) * i / n, 5,
                      (ey1 - ey0) / n + 0.05, cor_isovalor(t), None)
    pdf.retangulo(ex, ey0, 5, ey1 - ey0, None, CINZA, 0.2)
    for i in range(5):
        t = i / 4
        yy = ey0 + (ey1 - ey0) * t
        pdf.linha(ex + 5, yy, ex + 6.5, yy, 0.2, CINZA)
        pdf.texto(ex + 7.5, yy - 1, f"{vmax * t:.0f}", 6, PRETO)
    pdf.texto(ex, ey1 + 2.5, "kN·m/m", 6, CINZA)


# =========================================================================== #
#  Prancha 4 — PERFIL GEOTÉCNICO E RECALQUES
# =========================================================================== #
def prancha_perfil(pdf: PDF, res, mod: dict, obra: str, projetista: str,
                   folha: str) -> None:
    pdf.nova_pagina()
    moldura(pdf, "SAPATA ISOLADA — PERFIL GEOTÉCNICO E RECALQUES",
            "Estratigrafia adotada, bulbo de tensões e contribuição por camada",
            folha, obra, projetista, "indicada")

    camadas = mod.get("camadas") or []
    if not camadas:
        pdf.texto(30, 150, "Perfil estratigráfico não informado.", 10, CINZA)
        return

    prof_total = camadas[-1]["z_base"]
    topo_mm, base_mm = 244.0, 72.0
    esc = (topo_mm - base_mm) / prof_total          # mm por metro
    col_x, col_l = 40.0, 26.0

    def ym(z):                                       # profundidade -> folha
        return topo_mm - z * esc

    pdf.texto(30, 252, "PERFIL DE SONDAGEM", 9, PRETO, negrito=True)
    pdf.linha(30, 250.2, 100, 250.2, 0.4, PRETO)
    pdf.texto(col_x + col_l + 3, 252, f"esc. vert. 1:{1000/esc:.0f}", 6.5, CINZA)

    for c in camadas:
        y1, y0 = ym(c["z_topo"]), ym(c["z_base"])
        cor = CORES_SUBSTRATO.get(c["tipo"], CORES_SUBSTRATO["granular"])
        pdf.retangulo(col_x, y0, col_l, y1 - y0, cor, PRETO, 0.3)
        # hachura conforme o tipo de substrato
        n = max(1, int((y1 - y0) / 3))
        for i in range(n):
            yy = y0 + (i + 0.5) * (y1 - y0) / n
            if c["tipo"] == "coesivo":
                pdf.linha(col_x + 2, yy, col_x + col_l - 2, yy, 0.12, (0.3, 0.35, 0.3))
            elif c["tipo"] == "rocha":
                pdf.linha(col_x + 2, yy, col_x + col_l - 2, yy + 1.5, 0.12, (0.3, 0.3, 0.35))
            else:
                for j in range(4):
                    px = col_x + 4 + j * (col_l - 8) / 3
                    pdf.circulo(px, yy, 0.25, (0.45, 0.38, 0.2), None)
        pdf.texto(col_x + col_l + 4, (y0 + y1) / 2 - 1, c["nome"][:34], 7, PRETO)
        pdf.texto(col_x + col_l + 4, (y0 + y1) / 2 - 4.6,
                  f"{c['tipo']} · {c['z_topo']:.2f}–{c['z_base']:.2f} m", 6, CINZA)
        pdf.texto(col_x - 2, y1 - 1.5, f"{c['z_topo']:.2f}", 6, CINZA, ancora="se")
    pdf.texto(col_x - 2, ym(prof_total) - 1.5, f"{prof_total:.2f}", 6, CINZA, ancora="se")

    # nível d'água
    if mod.get("nivel_agua") is not None:
        yn = ym(mod["nivel_agua"])
        pdf.linha(col_x - 6, yn, col_x + col_l + 2, yn, 0.35, (0.18, 0.50, 0.66), [3, 2])
        pdf.poligono([(col_x - 6, yn), (col_x - 3, yn), (col_x - 4.5, yn - 2.6)],
                     (0.18, 0.50, 0.66), None)
        pdf.texto(col_x - 8, yn + 1, f"N.A. {mod['nivel_agua']:.2f}", 6,
                  (0.18, 0.50, 0.66), ancora="se")

    # sapata na posição real
    hf, a, h = mod["hf"], res.a, res.h
    largura_sapata = max(a * esc, 14.0)
    xs = col_x + col_l + 74
    pdf.retangulo(xs - largura_sapata / 2, ym(hf), largura_sapata, h * esc,
                  CONCRETO, PRETO, 0.5)
    pdf.texto(xs, ym(hf) + h * esc + 2.5,
              f"sapata {a:.2f}×{res.b:.2f}×{h:.2f}", 6.5, PRETO, ancora="center")
    pdf.linha(col_x + col_l, ym(hf), xs - largura_sapata / 2, ym(hf), 0.15, CINZA, [2, 2])
    pdf.texto(col_x + col_l + 3, ym(hf) - 3.2,
              f"cota de assentamento {hf:.2f} m", 6, VERMELHO)

    # ------------------------------------------------------- bulbo de tensões
    p = res.recalques
    if p:
        pdf.texto(xs + 34, 252, "BULBO DE TENSÕES (Boussinesq)", 9, PRETO, negrito=True)
        pdf.linha(xs + 34, 250.2, xs + 125, 250.2, 0.4, PRETO)
        base = xs + 40
        for pc in p.parcelas:
            y1, y0 = ym(pc["z_topo"] if isinstance(pc, dict) else pc.z_topo), None
            zt = pc["z_topo"] if isinstance(pc, dict) else pc.z_topo
            zb = pc["z_base"] if isinstance(pc, dict) else pc.z_base
            ds = pc["delta_sigma"] if isinstance(pc, dict) else pc.delta_sigma
            larg = ds / max(p.q_liquido, 1e-6) * 55
            pdf.retangulo(base, ym(zb), max(larg, 0.2), ym(zt) - ym(zb),
                          (0.30 + 0.55 * min(1, ds / max(p.q_liquido, 1)),
                           0.62, 0.70), None)
        pdf.linha(base, ym(0), base, ym(prof_total), 0.3, PRETO)
        pdf.texto(base, ym(prof_total) - 5, f"Δσ  (q_líq = {p.q_liquido:.0f} kPa)",
                  6.5, CINZA)

        # tabela de contribuições
        linhas = []
        for pc in p.parcelas[:14]:
            d = pc if isinstance(pc, dict) else pc.__dict__
            linhas.append((d["camada"][:24],
                           f"{d['z_topo']:.2f}–{d['z_base']:.2f}",
                           f"{d['sigma_v0']:.0f}", f"{d['delta_sigma']:.0f}",
                           f"{d['recalque_mm']:.2f}"))
        tabela(pdf, 258, 210, [50, 30, 22, 22, 26],
               ["Camada", "z (m)", "σ'v0", "Δσ", "rec. (mm)"], linhas,
               "CONTRIBUIÇÃO POR SUBCAMADA", tam=6.2)

        quadro(pdf, 258, 100, 150, [
            ("Tensão líquida na base", f"{p.q_liquido:.1f} kPa"),
            ("Profundidade de influência", f"{p.profundidade_influencia:.2f} m"),
            ("Recalque imediato", f"{p.recalque_imediato_mm:.1f} mm"),
            ("Adensamento primário", f"{p.recalque_adensamento_mm:.1f} mm"),
            ("Compressão secundária", f"{p.recalque_secundario_mm:.1f} mm"),
            ("TOTAL estimado", f"{p.recalque_total_mm:.1f} mm  "
                               f"(limite {p.limite_mm:.0f} mm)"),
            ("Elástico global (I_w)", f"{p.recalque_elastico_global_mm:.1f} mm"),
        ] + ([("Schmertmann (1978)", f"{p.recalque_schmertmann_mm:.1f} mm")]
             if p.recalque_schmertmann_mm is not None else []),
            "RECALQUES")
    else:
        pdf.texto(xs + 40, 200, "Recalques não calculados.", 9, CINZA)


# =========================================================================== #
#  Blocos auxiliares
# =========================================================================== #
def quadro(pdf: PDF, x: float, y: float, larg: float,
           itens: Sequence[tuple[str, str]], titulo: str) -> None:
    alt = 7.5 + 5.0 * len(itens)
    pdf.retangulo(x, y - alt + 7.5, larg, alt, (0.97, 0.97, 0.96), PRETO, 0.35)
    pdf.linha(x, y + 1.5, x + larg, y + 1.5, 0.35, PRETO)
    pdf.texto(x + 2.5, y + 3.2, titulo, 7.5, PRETO, negrito=True)
    for i, (rot, val) in enumerate(itens):
        yy = y - 2.5 - i * 5.0
        pdf.texto(x + 2.5, yy, rot, 6.5, CINZA)
        pdf.texto(x + larg - 2.5, yy, val, 6.5, PRETO, ancora="se")


def tabela(pdf: PDF, x: float, y: float, larguras: Sequence[float],
           cabecalho: Sequence[str], linhas: Sequence[Sequence[str]],
           titulo: str, tam: float = 6.5) -> None:
    larg = sum(larguras)
    pdf.texto(x, y + 3.5, titulo, 7.5, PRETO, negrito=True)
    pdf.linha(x, y + 2, x + larg, y + 2, 0.35, PRETO)
    cx = x
    for i, c in enumerate(cabecalho):
        pdf.texto(cx + larguras[i] - 1.5 if i else cx + 1.5, y - 3.5, c, tam - 0.3,
                  CINZA, ancora="se" if i else "sw")
        cx += larguras[i]
    pdf.linha(x, y - 5.5, x + larg, y - 5.5, 0.25, CINZA)
    for j, linha in enumerate(linhas):
        yy = y - 10.5 - j * 5.0
        cx = x
        for i, celula in enumerate(linha):
            pdf.texto(cx + larguras[i] - 1.5 if i else cx + 1.5, yy, str(celula), tam,
                      PRETO, ancora="se" if i else "sw", mono=bool(i))
            cx += larguras[i]
        pdf.linha(x, yy - 1.6, x + larg, yy - 1.6, 0.12, (0.88, 0.88, 0.87))


def paginas_memorial(pdf: PDF, texto: str, obra: str, projetista: str,
                     folha_inicial: int, total: int) -> int:
    """Escreve o memorial de cálculo em texto; devolve o número de páginas."""
    linhas = texto.split("\n")
    por_pagina = 62
    blocos = [linhas[i:i + por_pagina] for i in range(0, len(linhas), por_pagina)]
    for i, bloco in enumerate(blocos):
        pdf.nova_pagina()
        moldura(pdf, "SAPATA ISOLADA — MEMORIAL DE CÁLCULO",
                f"Verificações normativas — parte {i + 1} de {len(blocos)}",
                f"{folha_inicial + i}/{total}", obra, projetista, "—")
        y = pdf.altura - MARGEM - 24
        for linha in bloco:
            pdf.texto(MARGEM + 6, y, linha[:118], 6.2, PRETO, mono=True)
            y -= 3.9
    return len(blocos)


# =========================================================================== #
#  Ponto de entrada
# =========================================================================== #
def gerar_memorial_pdf(caminho: str, sapata, res, modelo: dict,
                       obra: str = "Obra sem identificação",
                       projetista: str = "—",
                       proveniencia_sigma_adm: Optional[dict] = None) -> str:
    """Monta o PDF completo (fôrmas, armação, perfil e memorial).

    `proveniencia_sigma_adm` só repassa para `relatorio.memorial` — ver a
    docstring de `memorial` sobre o contrato do dicionário e sobre quem
    decide se ele ainda é válido (D-02 do GATE 2, rodada 3)."""
    texto = memorial(res, sapata, proveniencia_sigma_adm=proveniencia_sigma_adm)
    # conta as folhas antes de desenhar, para o carimbo trazer "n/total"
    n_memorial = max(1, math.ceil(len(texto.split("\n")) / 62))
    try:
        campo = campo_momentos(sapata, res, nx=45, ny=45)
    except Exception:
        campo = None
    total = (4 if campo else 3) + n_memorial

    pdf = PDF(A3_PAISAGEM)
    prancha_formas(pdf, res, modelo, obra, projetista, f"1/{total}")
    prancha_armacao(pdf, res, modelo, obra, projetista, f"2/{total}")
    folha = 3
    if campo:
        prancha_momentos(pdf, res, campo, obra, projetista, f"{folha}/{total}")
        folha += 1
    prancha_perfil(pdf, res, modelo, obra, projetista, f"{folha}/{total}")
    paginas_memorial(pdf, texto, obra, projetista, folha + 1, total)
    pdf.salvar(caminho)
    return caminho
