"""
visual3d_momentos.py
--------------------
Superfície tridimensional do campo de momentos: só a sapata e o diagrama,
sem o maciço.

O diagrama é pendurado abaixo da base, do lado tracionado do balanço — a
convenção de desenho estrutural. Como o momento é nulo nas bordas, a
superfície encosta no plano da base ao longo de todo o perímetro.
"""
from __future__ import annotations

import math
from typing import Optional

from .momentos import CampoMomentos, cor_hex, curvas_nivel, niveis_uteis
from .pintura import PoolCanvas, encadear_segmentos
from .projecao import Camera, ControleOrbital, distancia_enquadramento

FUNDO = "#1a2026"
TINTA = "#e6eaec"
TINTA_FRACA = "#8b96a0"
DESTAQUE = "#f0873c"
COR_CONCRETO = "#9aa3a6"
COR_ARESTA = "#7d8a91"
COR_MALHA = "#20272c"


class SuperficieMomentos3D:
    """
    Desenha, em perspectiva, a sapata em contorno e a superfície de momentos
    colorida por magnitude. Gira com o mouse, como o modelo 3D.
    """

    # a grade cheia do campo é fina demais para desenhar como sólido
    PASSO = 3

    def __init__(self, canvas) -> None:
        self.canvas = canvas
        self.campo: Optional[CampoMomentos] = None
        self.campo_analitico: Optional[CampoMomentos] = None
        self.campo_grelha: Optional[CampoMomentos] = None
        self.rigida: Optional[bool] = None
        self.geometria: Optional[dict] = None
        self.direcao = "X"
        self.modo = "grelha"           # "grelha" (barras) ou "superficie"
        self.mostrar_x = True          # diagramas das barras em X
        self.mostrar_y = True          # idem em Y
        self.linhas_diagrama = 9       # barras desenhadas por direção
        self.mostrar_malha = True
        self.mostrar_isolinhas = True
        self.mostrar_sapata = True
        self.cam = Camera(yaw=-0.95 - math.pi / 2, pitch=0.80)
        self._primitivas: list = []
        self._rotulos: list = []
        self.pool = PoolCanvas(canvas)

        self.controle = ControleOrbital(canvas, self.cam, self.desenhar)
        canvas.bind("<Configure>", lambda e: self._reenquadrar())

    # ------------------------------------------------------------------ dados
    def definir(self, campo_analitico: Optional[CampoMomentos],
               campo_grelha: Optional[CampoMomentos], geometria: dict,
               rigida: Optional[bool] = None) -> None:
        """
        Recebe os dois campos possíveis: o analítico (plano de tensões rígido,
        usado pelo modo "Superfície" quando a sapata é rígida, e como reserva
        do modo "Grelha" quando a grelha não foi resolvida) e o real da
        grelha discretizada (usado pelo modo "Grelha" sempre que disponível —
        `res.grelha` não é `None` — e também pelo modo "Superfície" quando a
        sapata é FLEXÍVEL, pois aí a hipótese de placa rígida do campo
        analítico não vale — NBR 6118, 22.6.1/22.6.2.3).

        `rigida` é `res.rigida`: `False` troca a fonte padrão do modo
        "Superfície" para a grelha; `True` ou desconhecida mantém o
        analítico, como antes.
        """
        self.campo_analitico = campo_analitico
        self.campo_grelha = campo_grelha
        self.rigida = rigida
        self.geometria = geometria
        self._escolher_campo()
        self.cam.yaw, self.cam.pitch = self._iso()
        self._reenquadrar()

    def _escolher_campo(self) -> None:
        """Define `self.campo` (o que os desenhos consomem) a partir do modo."""
        if self.modo == "grelha":
            self.campo = (self.campo_grelha if self.campo_grelha is not None
                          else self.campo_analitico)
        else:                          # modo "superficie"
            if self.rigida is False and self.campo_grelha is not None:
                self.campo = self.campo_grelha
            else:
                self.campo = self.campo_analitico

    def definir_modo(self, modo: str) -> None:
        self.modo = "grelha" if modo == "grelha" else "superficie"
        self._escolher_campo()
        self.cam.yaw, self.cam.pitch = self._iso()
        self._reenquadrar()

    def definir_direcao(self, direcao: str) -> None:
        self.direcao = direcao
        self.cam.yaw, self.cam.pitch = self._iso()
        self.construir()
        self.desenhar()

    def _iso(self) -> tuple[float, float]:
        """
        Vista isométrica orientada pela direção em exibição.

        O vale do diagrama corre paralelo ao eixo transversal: olhar ao longo
        dele esconde o próprio vale atrás da parede mais próxima. Por isso a
        câmera gira 90° entre uma direção e outra.
        """
        if self.modo == "grelha":
            return -0.95 - math.pi / 4, 0.72
        base = -0.95 if self.direcao == "Y" else -0.95 - math.pi / 2
        return base, 0.80

    def alternar(self, chave: str, valor: bool) -> None:
        setattr(self, chave, valor)
        self.construir()
        self.desenhar()

    def vista(self, nome: str) -> None:
        v = {"iso": self._iso(), "frente": (0.0, 0.16),
             "lado": (-math.pi / 2, 0.16), "topo": (0.0, 1.45)}.get(nome)
        if not v:
            return
        self.cam.yaw, self.cam.pitch = v
        self._reenquadrar()

    # ------------------------------------------------------------------ útil
    def _dim(self):
        return (max(self.canvas.winfo_width(), 10),
                max(self.canvas.winfo_height(), 10))

    def _escala_vertical(self) -> float:
        """Metros de altura do diagrama por kN·m/m."""
        if not self.campo:
            return 0.0
        valores = self.campo.faixa(self.direcao)
        vmax = max(max(l) for l in valores)
        if vmax <= 0:
            return 0.0
        # amplitude contida: se a parede do diagrama ficar mais inclinada que a
        # linha de visada, ela esconde o próprio vale
        alvo = 0.30 * max(self.campo.a, self.campo.b)
        return alvo / vmax

    def _reenquadrar(self):
        if not self.campo:
            self.desenhar()
            return
        W, H = self._dim()
        self.cam.focal = min(W, H) * 3.2
        c = self.campo
        alt = 0.30 * max(c.a, c.b) + (self.geometria or {}).get("h", 0.5)
        extensao = max(max(c.a, c.b) * 1.42, alt) * 1.12
        self.cam.alvo = [0.0, 0.0, -alt * 0.28]
        self.cam.dist = distancia_enquadramento(extensao, self.cam.focal, W, H, 0.95)
        self.construir()
        self.desenhar()

    # ------------------------------------------------------------- construção
    def construir(self):
        self._primitivas = []
        self._rotulos = []
        if not self.campo:
            return
        c = self.campo
        valores = c.faixa(self.direcao)
        vmax = max(max(l) for l in valores)
        k = self._escala_vertical()
        passo = self.PASSO

        if self.mostrar_sapata:
            self._sapata()

        if self.modo == "grelha":
            self._diagramas_grelha(c, k)
            return

        xs, ys = c.x, c.y
        # superfície: z = -k·m, pendurada abaixo do plano da base (z = 0)
        for j in range(0, len(ys) - passo, passo):
            for i in range(0, len(xs) - passo, passo):
                i2, j2 = i + passo, j + passo
                quad = [(xs[i], ys[j], -k * valores[j][i]),
                        (xs[i2], ys[j], -k * valores[j][i2]),
                        (xs[i2], ys[j2], -k * valores[j2][i2]),
                        (xs[i], ys[j2], -k * valores[j2][i])]
                media = sum(p[2] for p in quad) / -4.0 / k if k else 0.0
                cor = cor_hex(media / vmax if vmax > 0 else 0.0)
                self._primitivas.append(
                    ("face", quad, cor, COR_MALHA if self.mostrar_malha else cor))

        if self.mostrar_isolinhas and vmax > 0:
            for nivel in niveis_uteis(vmax, 8):
                segmentos = curvas_nivel(xs, ys, valores, nivel)
                z = -k * nivel - 0.004
                for curva in encadear_segmentos(segmentos):
                    self._primitivas.append(
                        ("polilinha", [(p[0], p[1], z) for p in curva],
                         "#12181c", 1))

        # cota do pico e da escala
        pico = self._pico(xs, ys, valores)
        if pico:
            xp, yp, vp = pico
            self._primitivas.append(
                ("linha", (xp, yp, 0.0), (xp, yp, -k * vp), DESTAQUE, 2))
            self._rotulos.append(((xp, yp, -k * vp), f"{vp:.1f} kN·m/m",
                                  DESTAQUE, 0, 14))

    # ------------------------------------------------------- modo grelha
    def _escala_comum(self) -> float:
        """Mesma escala vertical para as duas direções, senão não se comparam."""
        c = self.campo
        vmax = max(max(max(l) for l in c.mx), max(max(l) for l in c.my), 1e-9)
        return 0.30 * max(c.a, c.b) / vmax

    def _diagramas_grelha(self, c, _k):
        """
        Diagrama de momento de cada barra da grelha, desenhado como fita
        vertical pendurada sob a barra — a leitura clássica de grelha.

        As duas direções compartilham a escala vertical e a de cores, para que
        comparar X com Y signifique alguma coisa.
        """
        k = self._escala_comum()
        xs, ys = c.x, c.y
        vmax = max(max(max(l) for l in c.mx), max(max(l) for l in c.my), 1e-9)
        n = max(3, int(self.linhas_diagrama))

        def indices(total):
            if total <= n:
                return list(range(total))
            return [round(i * (total - 1) / (n - 1)) for i in range(n)]

        if self.mostrar_x:
            for j in indices(len(ys)):
                y = ys[j]
                for i in range(len(xs) - 1):
                    m0, m1 = c.mx[j][i], c.mx[j][i + 1]
                    if max(m0, m1) < vmax * 0.01:
                        continue
                    quad = [(xs[i], y, 0.0), (xs[i + 1], y, 0.0),
                            (xs[i + 1], y, -k * m1), (xs[i], y, -k * m0)]
                    cor = cor_hex((m0 + m1) / 2 / vmax)
                    self._primitivas.append(("face", quad, cor, "#1b2126"))
                # linha de fecho do diagrama
                self._primitivas.append(
                    ("polilinha", [(xs[i], y, -k * c.mx[j][i])
                                   for i in range(len(xs))], "#7fd8e8", 1))

        if self.mostrar_y:
            for i in indices(len(xs)):
                x = xs[i]
                for j in range(len(ys) - 1):
                    m0, m1 = c.my[j][i], c.my[j + 1][i]
                    if max(m0, m1) < vmax * 0.01:
                        continue
                    quad = [(x, ys[j], 0.0), (x, ys[j + 1], 0.0),
                            (x, ys[j + 1], -k * m1), (x, ys[j], -k * m0)]
                    cor = cor_hex((m0 + m1) / 2 / vmax)
                    self._primitivas.append(("face", quad, cor, "#1b2126"))
                self._primitivas.append(
                    ("polilinha", [(x, ys[j], -k * c.my[j][i])
                                   for j in range(len(ys))], "#f0a35c", 1))

        # malha no plano da base
        if self.mostrar_malha:
            for j in indices(len(ys)):
                self._primitivas.append(
                    ("linha", (xs[0], ys[j], 0.0), (xs[-1], ys[j], 0.0),
                     "#55636c", 1))
            for i in indices(len(xs)):
                self._primitivas.append(
                    ("linha", (xs[i], ys[0], 0.0), (xs[i], ys[-1], 0.0),
                     "#55636c", 1))

        mx_pico = max(max(l) for l in c.mx)
        my_pico = max(max(l) for l in c.my)
        if self.mostrar_x:
            self._rotulos.append(((c.a / 2, 0.0, -k * mx_pico),
                                  f"Mx {mx_pico:.0f}", "#7fd8e8", 26, 0))
        if self.mostrar_y:
            self._rotulos.append(((0.0, c.b / 2, -k * my_pico),
                                  f"My {my_pico:.0f}", "#f0a35c", 0, 16))

    def _cabecalho_grelha(self, W, H):
        pool = self.pool
        c = self.campo
        mx = max(max(l) for l in c.mx)
        my = max(max(l) for l in c.my)
        vmax = max(mx, my, 1e-9)
        ativos = []
        if self.mostrar_x:
            ativos.append("X")
        if self.mostrar_y:
            ativos.append("Y")
        if self.campo is self.campo_grelha and self.campo_grelha is not None:
            titulo = "Grelha discretizada — diagramas de momento por barra"
        else:
            titulo = ("Campo analítico (grelha não disponível) — "
                      "diagramas por barra")
        pool.texto(20, 22, titulo, TINTA, ("Segoe UI Semibold", 11), "w")
        pool.texto(20, 42, f"direções exibidas: {' e '.join(ativos) or 'nenhuma'}"
                           f"  ·  Mx máx {mx:.1f}  ·  My máx {my:.1f} kN·m/m",
                   TINTA_FRACA, ("Consolas", 8), "w")
        pool.texto(20, 58, f"combinação: {c.combinacao}", TINTA_FRACA,
                   ("Consolas", 8), "w")
        pool.texto(20, 74, "escala vertical e de cores comuns às duas direções",
                   TINTA_FRACA, ("Consolas", 8), "w")
        if self.rigida is False:
            pool.texto(20, 90, "Sapata FLEXÍVEL (NBR 6118, 22.6.1/22.6.2.3) — o campo "
                               "analítico assume placa rígida; use a Grelha "
                               "para o comportamento real.", DESTAQUE,
                       ("Consolas", 8), "w")
        self._escala_cores(W, H, vmax)

    def _escala_cores(self, W, H, vmax):
        pool = self.pool
        x0, y0 = W - 40, 100
        y1 = min(H - 60, y0 + 250)
        n = 40
        for i in range(n):
            t = 1 - i / n
            ya = y0 + (y1 - y0) * i / n
            yb = y0 + (y1 - y0) * (i + 1) / n
            cor = cor_hex(t)
            pool.poligono([x0, ya, x0 + 14, ya, x0 + 14, yb, x0, yb], cor, cor)
        pool.poligono([x0, y0, x0 + 14, y0, x0 + 14, y1, x0, y1], "", TINTA_FRACA)
        for i in range(4):
            t = 1 - i / 3
            yy = y0 + (y1 - y0) * i / 3
            pool.texto(x0 - 4, yy, f"{vmax * t:.0f}", TINTA, ("Consolas", 8), "e")
        pool.texto(x0 + 7, y0 - 12, "kN·m/m", TINTA_FRACA, ("Consolas", 8))

    def _pico(self, xs, ys, valores):
        melhor = None
        for j, linha in enumerate(valores):
            for i, v in enumerate(linha):
                if melhor is None or v > melhor[2]:
                    melhor = (xs[i], ys[j], v)
        return melhor

    def _sapata(self):
        """Contorno da peça no plano da base, mais o volume acima em arestas."""
        g = self.geometria or {}
        c = self.campo
        a, b = c.a, c.b
        h = g.get("h", 0.0)
        h0 = g.get("h0", 0.0)
        at, bt = g.get("at", c.ap), g.get("bt", c.bp)
        ap, bp = c.ap, c.bp

        base = [(-a/2, -b/2, 0.0), (a/2, -b/2, 0.0), (a/2, b/2, 0.0), (-a/2, b/2, 0.0)]
        aba = [(x, y, h0) for x, y, _ in base]
        topo = [(-at/2, -bt/2, h), (at/2, -bt/2, h), (at/2, bt/2, h), (-at/2, bt/2, h)]
        pilar = [(-ap/2, -bp/2, h), (ap/2, -bp/2, h), (ap/2, bp/2, h), (-ap/2, bp/2, h)]
        alto = [(x, y, h + 0.45) for x, y, _ in pilar]

        for i in range(4):     # a base é a referência entre a peça e o diagrama
            self._primitivas.append(("linha", base[i], base[(i + 1) % 4],
                                     "#dfe6e9", 2))
        for anel in (aba, topo, pilar, alto):
            for i in range(4):
                self._primitivas.append(
                    ("linha", anel[i], anel[(i + 1) % 4], COR_ARESTA, 1))
        for i in range(4):
            self._primitivas.append(("linha", base[i], aba[i], COR_ARESTA, 1))
            self._primitivas.append(("linha", aba[i], topo[i], COR_ARESTA, 1))
            self._primitivas.append(("linha", pilar[i], alto[i], COR_ARESTA, 1))

        # face do pilar: seção de referência do momento em exibição
        if self.direcao == "X":
            for sx in (-1, 1):
                self._primitivas.append(
                    ("linha", (sx * ap / 2, -b/2, 0.0), (sx * ap / 2, b/2, 0.0),
                     DESTAQUE, 1))
        else:
            for sy in (-1, 1):
                self._primitivas.append(
                    ("linha", (-a/2, sy * bp / 2, 0.0), (a/2, sy * bp / 2, 0.0),
                     DESTAQUE, 1))

    # ---------------------------------------------------------------- desenho
    def desenhar(self):
        W, H = self._dim()
        self.pool.iniciar()
        if not self.campo:
            self.pool.texto(W / 2, H / 2, "Nenhum campo calculado", TINTA_FRACA,
                            ("Segoe UI", 12))
            self.pool.finalizar()
            return

        itens = []
        for p in self._primitivas:
            if p[0] == "face":
                pr = [self.cam.projetar(v, W, H) for v in p[1]]
                if any(v[2] <= 0.1 for v in pr):
                    continue
                itens.append((sum(v[2] for v in pr) / len(pr), p, pr))
            elif p[0] == "polilinha":
                pr = [self.cam.projetar(v, W, H) for v in p[1]]
                if any(v[2] <= 0.1 for v in pr):
                    continue
                itens.append((sum(v[2] for v in pr) / len(pr) - 0.012, p, pr))
            else:
                a = self.cam.projetar(p[1], W, H)
                b = self.cam.projetar(p[2], W, H)
                if a[2] <= 0.1 or b[2] <= 0.1:
                    continue
                # arestas empatam com as faces vizinhas: puxa levemente à frente
                itens.append(((a[2] + b[2]) / 2 - 0.012, p, [a, b]))
        itens.sort(key=lambda t: -t[0])

        for _, p, pr in itens:
            if p[0] == "face":
                self.pool.poligono([v for ponto in pr for v in ponto[:2]],
                                   p[2], p[3])
            elif p[0] == "polilinha":
                self.pool.polilinha([v for ponto in pr for v in ponto[:2]],
                                    p[2], p[3])
            else:
                self.pool.polilinha([pr[0][0], pr[0][1], pr[1][0], pr[1][1]],
                                    p[3], p[4])

        for ponto, texto, cor, dx, dy in self._rotulos:
            s = self.cam.projetar(ponto, W, H)
            if s[2] <= 0.1:
                continue
            self.pool.texto(s[0] + dx, s[1] + dy, texto, cor, ("Consolas", 9))

        self._cabecalho(W, H)
        self.pool.finalizar()

    def _cabecalho(self, W, H):
        pool = self.pool
        c = self.campo
        if self.modo == "grelha":
            self._cabecalho_grelha(W, H)
            return
        valores = c.faixa(self.direcao)
        vmax = max(max(l) for l in valores)
        largura = c.b if self.direcao == "X" else c.a
        md = c.md_projeto_x if self.direcao == "X" else c.md_projeto_y

        fonte = ("grelha discretizada" if c is self.campo_grelha
                 and self.campo_grelha is not None else "campo analítico (placa rígida)")
        pool.texto(20, 22, f"Superfície de momentos — arma a direção {self.direcao}", TINTA, ("Segoe UI Semibold", 11), 'w')
        pool.texto(20, 42, f"máx {vmax:.1f} kN·m/m  ·  faixa integrada "
                            f"{vmax * largura:.1f} kN·m  ·  M_d adotado {md:.1f} kN·m"
                            f"  ·  fonte: {fonte}", TINTA_FRACA, ("Consolas", 8), 'w')
        pool.texto(20, 58, f"combinação: {c.combinacao}", TINTA_FRACA, ("Consolas", 8), 'w')
        if self.rigida is False:
            pool.texto(20, 74, "Sapata FLEXÍVEL (NBR 6118, 22.6.1/22.6.2.3) — o campo "
                               "analítico assume placa rígida; use a Grelha "
                               "para o comportamento real.", DESTAQUE,
                       ("Consolas", 8), 'w')
        pool.texto(W - 16, H - 16, "diagrama do lado tracionado · sem o maciço", TINTA_FRACA, ("Consolas", 8), 'e')

        # escala de cores compacta
        x0, y0, y1 = W - 40, 92, min(H - 60, 92 + 260)
        n = 44
        for i in range(n):
            t = 1 - i / n
            ya = y0 + (y1 - y0) * i / n
            yb = y0 + (y1 - y0) * (i + 1) / n
            cor = cor_hex(t)
            pool.poligono([x0, ya, x0 + 14, ya, x0 + 14, yb, x0, yb], cor, cor)
        pool.poligono([x0, y0, x0 + 14, y0, x0 + 14, y1, x0, y1], "", TINTA_FRACA)
        for i in range(4):
            t = 1 - i / 3
            yy = y0 + (y1 - y0) * i / 3
            pool.texto(x0 - 4, yy, f"{vmax * t:.0f}", TINTA, ("Consolas", 8), 'e')
        pool.texto(x0 + 7, y0 - 12, "kN·m/m", TINTA_FRACA, ("Consolas", 8))
