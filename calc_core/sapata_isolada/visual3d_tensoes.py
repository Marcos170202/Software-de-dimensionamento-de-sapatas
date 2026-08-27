"""
visual3d_tensoes.py
--------------------
Superfície tridimensional da pressão de contato no solo: a sapata em contorno
e a superfície de tensão colorida por magnitude, girável com o mouse — mesma
infraestrutura de câmera e desenho de `visual3d_momentos.py` (`Camera`,
`ControleOrbital`, `projetar`, `PoolCanvas`, a rampa de cores de `momentos`).

Duas fontes possíveis, como no mapa de isovalores e na superfície de
momentos:
  - o modelo RÍGIDO (plano de tensões linear), de `CampoMomentos.sigma`;
  - o modelo discretizado da GRELHA sobre apoios elásticos (Winkler), de
    `ResultadoGrelha.pressao` — a pressão real quando a hipótese de placa
    rígida não vale (sapata FLEXÍVEL, NBR 6118:2023, 22.6.3).
`grade_de_campo_momentos`/`grade_de_grelha` adaptam esses dois objetos para
`GradeTensoes`, a grade genérica (x, y, valores) que este módulo desenha —
nenhuma conta nova é feita aqui, só leitura dos campos já calculados.

Convenção de desenho — DELIBERADAMENTE OPOSTA à do módulo de momentos
----------------------------------------------------------------------
`visual3d_momentos.py` pendura o diagrama abaixo da base, do lado tracionado
do balanço: é a convenção de desenho estrutural para momento fletor, que é um
esforço de TRAÇÃO numa das faces.

Tensão no solo não é isso: é a REAÇÃO de COMPRESSÃO do solo contra a base da
sapata. Aqui a leitura adotada é a de um "piso de referência" — um plano
plano em z = -ALT (ALT = 0,30·max(a,b), a mesma amplitude-alvo usada pelo
diagrama de momentos, para as duas superfícies terem escala comparável)
representando o solo em repouso, tensão nula. A partir desse piso, a
superfície SOBE em direção à base (z = 0) na proporção da tensão de
contato: onde a compressão é maior, a superfície do solo se aproxima mais da
base (mais "comprimida contra ela"); onde é menor (ou nula, numa seção
parcialmente descomprimida), ela fica no piso de referência, longe da base.
No pico de tensão a superfície toca exatamente o plano da base (z = 0).

Esse sentido de crescimento — de baixo para cima, terminando encostado na
base — é o oposto do diagrama de momentos, que cresce de cima (z = 0, m = 0
na borda) para baixo. A escolha também evita qualquer sobreposição visual
com o corpo da sapata (`_sapata`, desenhado inteiramente em z >= 0): a
superfície de tensões fica sempre em z <= 0, no mesmo "porão" onde vive o
diagrama de momentos, só que crescendo no sentido contrário dentro dele.

Pico e legenda em kPa (pressão), não em kN·m/m.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from .grelha import ResultadoGrelha
from .momentos import CampoMomentos, cor_hex, curvas_nivel, niveis_uteis
from .pintura import PoolCanvas, encadear_segmentos
from .projecao import Camera, ControleOrbital, distancia_enquadramento

FUNDO = "#1a2026"
TINTA = "#e6eaec"
TINTA_FRACA = "#8b96a0"
DESTAQUE = "#f0873c"
COR_ARESTA = "#7d8a91"
COR_MALHA = "#20272c"
COR_PISO = "#454f56"


# --------------------------------------------------------------------------- #
#  Grade genérica consumida pelo desenho
# --------------------------------------------------------------------------- #
@dataclass
class GradeTensoes:
    """
    Grade (x, y, valores) genérica de pressão no solo [kPa], com o suficiente
    da geometria (a, b, ap, bp) para desenhar o contorno da sapata por cima.

    Mesmo formato de `CampoMomentos`/`ResultadoGrelha` (`valores[j][i]`, nas
    coordenadas `x`/`y`) — os adaptadores abaixo só renomeiam campos, sem
    recalcular nada.
    """

    x: list[float]
    y: list[float]
    valores: list[list[float]]
    a: float
    b: float
    ap: float
    bp: float
    combinacao: str


def grade_de_campo_momentos(campo: CampoMomentos) -> GradeTensoes:
    """Adapta o campo analítico (plano de tensões rígido) já montado por
    `campo_momentos()` — `campo.sigma` é a pressão de cálculo no solo."""
    return GradeTensoes(x=campo.x, y=campo.y, valores=campo.sigma,
                        a=campo.a, b=campo.b, ap=campo.ap, bp=campo.bp,
                        combinacao=campo.combinacao)


def grade_de_grelha(g: ResultadoGrelha, ap: float, bp: float,
                    combinacao: str = "ELU governante (grelha)") -> GradeTensoes:
    """Adapta o resultado da grelha — `g.pressao` é a pressão real (Winkler)
    sobre a base elástica, já calculada por `resolver_grelha()`."""
    a = g.x[-1] - g.x[0]
    b = g.y[-1] - g.y[0]
    return GradeTensoes(x=g.x, y=g.y, valores=g.pressao, a=a, b=b,
                        ap=ap, bp=bp, combinacao=combinacao)


# --------------------------------------------------------------------------- #
#  Desenho
# --------------------------------------------------------------------------- #
class SuperficieTensoes3D:
    """
    Desenha, em perspectiva, a sapata em contorno e a superfície de tensão de
    contato no solo colorida por magnitude. Gira com o mouse, como os outros
    modelos 3D do pacote.
    """

    # a grade cheia do campo é fina demais para desenhar como sólido
    PASSO = 3

    def __init__(self, canvas) -> None:
        self.canvas = canvas
        self.campo: Optional[GradeTensoes] = None
        self.campo_analitico: Optional[GradeTensoes] = None
        self.campo_grelha: Optional[GradeTensoes] = None
        self.rigida: Optional[bool] = None
        self.geometria: Optional[dict] = None
        self.fonte = "analitico"       # ou "grelha"
        self.mostrar_malha = True
        self.mostrar_isolinhas = True
        self.mostrar_sapata = True
        self.cam = Camera(yaw=-0.95 - math.pi / 4, pitch=0.72)
        self._primitivas: list = []
        self._rotulos: list = []
        self.pool = PoolCanvas(canvas)

        self.controle = ControleOrbital(canvas, self.cam, self.desenhar)
        canvas.bind("<Configure>", lambda e: self._reenquadrar())

    # ------------------------------------------------------------------ dados
    def definir(self, campo_analitico: Optional[GradeTensoes],
               campo_grelha: Optional[GradeTensoes], geometria: dict,
               rigida: Optional[bool] = None) -> None:
        """
        Recebe as duas grades possíveis: a analítica (plano de tensões
        rígido) e a real da grelha discretizada sobre apoios elásticos —
        mesma convenção de `SuperficieMomentos3D.definir`.

        `rigida` é `res.rigida`: `False` (sapata FLEXÍVEL) troca a fonte
        padrão para a grelha — a hipótese de placa rígida do plano de
        tensões não vale nesse caso (NBR 6118:2023, 22.6.1/22.6.3); `True`
        ou desconhecida mantém o analítico.
        """
        self.campo_analitico = campo_analitico
        self.campo_grelha = campo_grelha
        self.rigida = rigida
        self.fonte = ("grelha" if rigida is False and campo_grelha is not None
                      else "analitico")
        self._escolher_campo()
        self.geometria = geometria
        self.cam.yaw, self.cam.pitch = self._iso()
        self._reenquadrar()

    def _escolher_campo(self) -> None:
        if self.fonte == "grelha" and self.campo_grelha is not None:
            self.campo = self.campo_grelha
        else:
            self.campo = self.campo_analitico

    def definir_fonte(self, fonte: str) -> None:
        self.fonte = "grelha" if fonte == "grelha" else "analitico"
        self._escolher_campo()
        self._reenquadrar()

    def _iso(self) -> tuple[float, float]:
        return -0.95 - math.pi / 4, 0.72

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

    def _profundidade(self) -> float:
        """
        Profundidade do 'piso' de referência (σ = 0), em metros — mesma
        amplitude-alvo de `SuperficieMomentos3D._escala_vertical`, para as
        duas superfícies ficarem em escala comparável.
        """
        if not self.campo:
            return 0.0
        return 0.30 * max(self.campo.a, self.campo.b)

    def _reenquadrar(self):
        if not self.campo:
            self.desenhar()
            return
        W, H = self._dim()
        self.cam.focal = min(W, H) * 3.2
        c = self.campo
        alt = self._profundidade() + (self.geometria or {}).get("h", 0.5)
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
        valores = c.valores
        vmax = max(max(l) for l in valores)
        ALT = self._profundidade()
        k = ALT / vmax if vmax > 0 else 0.0
        passo = self.PASSO

        if self.mostrar_sapata:
            self._sapata()
            self._piso(ALT)

        xs, ys = c.x, c.y
        # superfície: z = k·σ − ALT, subindo do piso (σ=0) até encostar na
        # base (σ=σ_máx → z=0) — ver a convenção no topo do módulo.
        for j in range(0, len(ys) - passo, passo):
            for i in range(0, len(xs) - passo, passo):
                i2, j2 = i + passo, j + passo
                quad = [(xs[i], ys[j], k * valores[j][i] - ALT),
                        (xs[i2], ys[j], k * valores[j][i2] - ALT),
                        (xs[i2], ys[j2], k * valores[j2][i2] - ALT),
                        (xs[i], ys[j2], k * valores[j2][i] - ALT)]
                media = sum(p[2] + ALT for p in quad) / 4.0 / k if k else 0.0
                cor = cor_hex(media / vmax if vmax > 0 else 0.0)
                self._primitivas.append(
                    ("face", quad, cor, COR_MALHA if self.mostrar_malha else cor))

        if self.mostrar_isolinhas and vmax > 0:
            for nivel in niveis_uteis(vmax, 8):
                segmentos = curvas_nivel(xs, ys, valores, nivel)
                z = k * nivel - ALT + 0.004
                for curva in encadear_segmentos(segmentos):
                    self._primitivas.append(
                        ("polilinha", [(p[0], p[1], z) for p in curva],
                         "#12181c", 1))

        # cota do pico e da escala
        pico = self._pico(xs, ys, valores)
        if pico:
            xp, yp, vp = pico
            zp = k * vp - ALT
            self._primitivas.append(
                ("linha", (xp, yp, -ALT), (xp, yp, zp), DESTAQUE, 2))
            self._rotulos.append(((xp, yp, zp), f"{vp:.1f} kPa",
                                  DESTAQUE, 0, -14))

    def _pico(self, xs, ys, valores):
        melhor = None
        for j, linha in enumerate(valores):
            for i, v in enumerate(linha):
                if melhor is None or v > melhor[2]:
                    melhor = (xs[i], ys[j], v)
        return melhor

    def _piso(self, ALT: float) -> None:
        """Contorno do plano de referência (σ = 0), em z = -ALT."""
        c = self.campo
        a, b = c.a, c.b
        piso = [(-a / 2, -b / 2, -ALT), (a / 2, -b / 2, -ALT),
                (a / 2, b / 2, -ALT), (-a / 2, b / 2, -ALT)]
        for i in range(4):
            self._primitivas.append(
                ("linha", piso[i], piso[(i + 1) % 4], COR_PISO, 1))

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
        valores = c.valores
        vmax = max(max(l) for l in valores)
        vmin = min(min(l) for l in valores)

        fonte = ("grelha discretizada" if c is self.campo_grelha
                 and self.campo_grelha is not None else "campo analítico (placa rígida)")
        pool.texto(20, 22, "Superfície de tensões no solo", TINTA,
                  ("Segoe UI Semibold", 11), 'w')
        pool.texto(20, 42, f"pico {vmax:.1f} kPa  ·  mín {vmin:.1f} kPa  ·  "
                            f"fonte: {fonte}", TINTA_FRACA, ("Consolas", 8), 'w')
        pool.texto(20, 58, f"combinação: {c.combinacao}", TINTA_FRACA,
                  ("Consolas", 8), 'w')
        if self.rigida is False:
            pool.texto(20, 74, "Sapata FLEXÍVEL (NBR 6118, 22.6.3) — o campo "
                               "analítico assume placa rígida; use a Grelha "
                               "para o comportamento real.", DESTAQUE,
                       ("Consolas", 8), 'w')
        pool.texto(W - 16, H - 16, "reação de compressão · superfície sobe "
                                    "do piso (σ=0) até a base", TINTA_FRACA,
                   ("Consolas", 8), 'e')

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
        pool.texto(x0 + 7, y0 - 12, "kPa", TINTA_FRACA, ("Consolas", 8))
