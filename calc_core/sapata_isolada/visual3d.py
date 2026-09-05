"""
visual3d.py
-----------
Visualizador 3D da sapata desenhado num canvas do Tkinter.

Projeção em perspectiva com algoritmo do pintor — sem OpenGL, sem
dependências. Mesma convenção do restante do pacote:

    x = direção de a ; y = direção de b ; z para cima
    superfície do terreno em z = 0 ; base da sapata em z = -hf

O maciço é desenhado em corte, com o quadrante (x>0, y<0) removido, para
expor a estratigrafia e a própria sapata.
"""
from __future__ import annotations

import math
from typing import Optional

from .pintura import PoolCanvas
from .projecao import ControleOrbital, distancia_enquadramento, projetar

CORES_SUBSTRATO = {
    "granular": (0xC7, 0x9A, 0x2E),
    "coesivo": (0x6F, 0x8C, 0x6B),
    "aterro": (0x9A, 0x7B, 0x57),
    "rocha": (0x6B, 0x7C, 0x8E),
}
COR_CONCRETO = (0xCC, 0xD2, 0xCE)
COR_PILAR = (0xA7, 0xAE, 0xAA)
COR_ACO = "#e6eef2"
COR_COTA = "#39c2dc"
COR_PRESSAO = "#f0873c"
COR_AGUA = "#4aa8d8"
COR_FUNDO = "#1a2026"


def _hex(rgb, k=1.0):
    r, g, b = (max(0, min(255, int(c * k))) for c in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def _misturar(rgb, k, alfa, fundo=(0x1a, 0x20, 0x26)):
    """Simula transparência compondo contra o fundo (canvas não tem alfa)."""
    r, g, b = (c * k for c in rgb)
    r = r * alfa + fundo[0] * (1 - alfa)
    g = g * alfa + fundo[1] * (1 - alfa)
    b = b * alfa + fundo[2] * (1 - alfa)
    return _hex((r, g, b))


class Visualizador3D:
    """Cena 3D ligada a um `tkinter.Canvas`."""

    def __init__(self, canvas) -> None:
        self.canvas = canvas
        self.modelo: Optional[dict] = None
        self.yaw = -1.06
        self.pitch = 0.34
        self.dist = 14.0
        self.alvo = [0.0, 0.0, -1.2]
        self.focal = 900.0
        # esta vista é da geometria: pressões e bulbo pertencem às abas de
        # momentos e de perfil, e sujavam a leitura da peça
        self.opcoes = {"solo": True, "armaduras": True, "cotas": True}
        self._primitivas: list = []
        self._sobrepostas: list = []
        self.pool = PoolCanvas(canvas)
        self.controle = ControleOrbital(canvas, self, self._ao_girar)
        canvas.bind("<Configure>", lambda e: self.desenhar())

    # ------------------------------------------------------------- geometria
    def _extensao_macico(self, m) -> float:
        return max(m["a"], m["b"]) * 0.62 + 0.40

    def _fundo_corte(self, m) -> float:
        return -m["hf"] - 0.75 * min(m["a"], m["b"])

    def _dim(self):
        return (max(self.canvas.winfo_width(), 10),
                max(self.canvas.winfo_height(), 10))

    def projetar(self, p):
        W, H = self._dim()
        return projetar(p, self.alvo, self.yaw, self.pitch, self.dist,
                        self.focal, W, H)

    def enquadrar(self):
        if not self.modelo:
            return
        W, H = self._dim()
        m = self.modelo
        self.focal = min(W, H) * 3.2
        E = self._extensao_macico(m)
        zf = self._fundo_corte(m)
        extensao = max(2.0 * E * math.sqrt(2), abs(zf)) * 1.18
        self.alvo = [0.0, 0.0, zf / 2]
        self.dist = distancia_enquadramento(extensao, self.focal, W, H)

    # ---------------------------------------------------------- primitivas
    def _face(self, pts, cor, contorno=None):
        self._primitivas.append(("face", pts, cor, contorno))

    def _linha(self, a, b, cor, larg=1, tracejado=None, sobreposta=False):
        alvo = self._sobrepostas if sobreposta else self._primitivas
        alvo.append(("linha", a, b, cor, larg, tracejado))

    def _rotulo(self, p, txt, cor, dx=0, dy=0, tam=9):
        self._sobrepostas.append(("rotulo", p, txt, cor, dx, dy, tam))

    def _caixa(self, x0, x1, y0, y1, z0, z1, rgb, alfa=1.0, corte=None,
               so_contorno=False):
        if x1 - x0 <= 1e-6 or y1 - y0 <= 1e-6 or z1 - z0 <= 1e-6:
            return
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
             (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        faces = [((4, 5, 6, 7), 1.16), ((0, 1, 2, 3), 0.55), ((0, 1, 5, 4), 0.86),
                 ((3, 2, 6, 7), 0.70), ((1, 2, 6, 5), 0.96), ((0, 3, 7, 4), 0.74)]
        ocluida = {2: bool(corte and corte[1]), 4: bool(corte and corte[0])}
        for i, (idx, k0) in enumerate(faces):
            k = k0 * 0.52 if ocluida.get(i) else k0
            preenche = None if so_contorno else _misturar(rgb, k, alfa)
            self._face([v[j] for j in idx], preenche, _misturar(rgb, 1.0, 1.0))

    def _tronco(self, a0, b0, z0, a1, b1, z1, rgb, alfa=1.0, so_contorno=False):
        i = [(-a0/2, -b0/2, z0), (a0/2, -b0/2, z0), (a0/2, b0/2, z0), (-a0/2, b0/2, z0)]
        s = [(-a1/2, -b1/2, z1), (a1/2, -b1/2, z1), (a1/2, b1/2, z1), (-a1/2, b1/2, z1)]
        for p, q, k in ((0, 1, 0.86), (1, 2, 0.96), (2, 3, 0.70), (3, 0, 0.74)):
            preenche = None if so_contorno else _misturar(rgb, k, alfa)
            self._face([i[p], i[q], s[q], s[p]], preenche, _misturar(rgb, 1.0, 1.0))
        self._face(s, None if so_contorno else _misturar(rgb, 1.16, alfa),
                   _misturar(rgb, 1.0, 1.0))

    # ------------------------------------------------------- Boussinesq
    @staticmethod
    def _fator_canto(m, n):
        if m <= 0 or n <= 0:
            return 0.0
        s = m * m + n * n
        num = 2.0 * m * n * math.sqrt(s + 1.0)
        t1 = (num / (s + 1.0 + (m * n) ** 2)) * ((s + 2.0) / (s + 1.0))
        return (t1 + math.atan2(num, s + 1.0 - (m * n) ** 2)) / (4.0 * math.pi)

    def _razao(self, x, y, z, a, b):
        if z <= 1e-6:
            return 1.0 if (abs(x) <= a / 2 and abs(y) <= b / 2) else 0.0
        def termo(X, Y):
            sg = (1 if X >= 0 else -1) * (1 if Y >= 0 else -1)
            return sg * self._fator_canto(abs(X) / z, abs(Y) / z)
        return (termo(a/2 + x, b/2 + y) + termo(a/2 + x, b/2 - y)
                + termo(a/2 - x, b/2 + y) + termo(a/2 - x, b/2 - y))

    # ------------------------------------------------------ montagem da cena
    def construir(self):
        self._primitivas = []
        self._sobrepostas = []
        m = self.modelo
        if not m:
            return
        zBase = -m["hf"]
        zAba = zBase + m["h0"]
        zTopo = zBase + m["h"]
        E = self._extensao_macico(m)
        zFundo = self._fundo_corte(m)
        alfa = 0.60 if self.opcoes["armaduras"] else 1.0

        if self.opcoes["solo"]:
            self._substrato(m, zBase, E, zFundo)
        self._sapata(m, zBase, zAba, zTopo, alfa)
        if self.opcoes["armaduras"]:
            self._armaduras(m, zBase)
        if self.opcoes["cotas"]:
            self._cotas(m, zBase, zTopo, E)

    def _substrato(self, m, zBase, E, zFundo):
        camadas = m.get("camadas") or [
            {"nome": "Solo", "tipo": "granular", "z_topo": 0.0,
             "z_base": m["hf"] + 3 * max(m["a"], m["b"])}]
        for c in camadas:
            zt = min(-c["z_topo"], 0.0)
            zb = max(-c["z_base"], zFundo)
            if zt - zb <= 1e-4:
                continue
            fatias = ([(zBase, zt), (zb, zBase)] if zb < zBase < zt else [(zb, zt)])
            for z0, z1 in fatias:
                if z1 - z0 <= 1e-4:
                    continue
                if z1 > zBase + 1e-6:
                    rects = [(-E, E, m["b"]/2, E), (-E, -m["a"]/2, -m["b"]/2, m["b"]/2),
                             (m["a"]/2, E, 0, m["b"]/2), (-E, 0, -E, -m["b"]/2)]
                else:
                    rects = [(-E, E, 0, E), (-E, 0, -E, 0)]
                rgb = CORES_SUBSTRATO.get(c["tipo"], CORES_SUBSTRATO["granular"])
                for x0, x1, y0, y1 in rects:
                    self._caixa(x0, x1, y0, y1, z0, z1, rgb, 1.0,
                                (abs(x1) < 1e-6, abs(y0) < 1e-6))
        total = camadas[-1]["z_base"]
        if total > -zFundo + 0.05:
            self._rotulo((0, 0, zFundo),
                         f"corte até {-zFundo:.2f} m — perfil vai a {total:.2f} m",
                         "#8b96a0", 0, 16, 8)
        na = m.get("nivel_agua")
        if na is not None:
            zn = -na
            self._linha((0, 0, zn), (E, 0, zn), COR_AGUA, 1, (5, 4), True)
            self._linha((0, -E, zn), (0, 0, zn), COR_AGUA, 1, (5, 4), True)
            self._rotulo((E, 0, zn), f"N.A. {na:.2f}", COR_AGUA, 0, -11, 8)

    def _sapata(self, m, zBase, zAba, zTopo, alfa):
        """
        Com as armaduras visíveis, a fôrma é desenhada apenas em contorno — o
        canvas do Tk não tem canal alfa, e preencher esconderia as barras.
        """
        a, b = m["a"], m["b"]
        vazado = self.opcoes["armaduras"]
        self._caixa(-a/2, a/2, -b/2, b/2, zBase, zAba, COR_CONCRETO, alfa,
                    so_contorno=vazado)
        if m["h"] > m["h0"] + 1e-6:
            self._tronco(a, b, zAba, m["at"], m["bt"], zTopo, COR_CONCRETO, alfa,
                         so_contorno=vazado)
        alt = min(0.85, m["hf"] * 0.6)
        self._caixa(-m["ap"]/2, m["ap"]/2, -m["bp"]/2, m["bp"]/2, zTopo, zTopo + alt,
                    COR_PILAR, 1.0)

    def _armaduras(self, m, zBase):
        cob = m["cobrimento"]
        arX = next((x for x in m["armaduras"] if x["direcao"] == "X"), None)
        arY = next((x for x in m["armaduras"] if x["direcao"] == "Y"), None)
        if arX and arX["n"] > 1:
            util = m["b"] - 2 * cob
            for i in range(arX["n"]):
                y = -util/2 + util * i / (arX["n"] - 1)
                self._linha((-m["a"]/2 + cob, y, zBase + cob),
                            (m["a"]/2 - cob, y, zBase + cob), COR_ACO, 1)
        if arY and arY["n"] > 1:
            util = m["a"] - 2 * cob
            for i in range(arY["n"]):
                x = -util/2 + util * i / (arY["n"] - 1)
                self._linha((x, -m["b"]/2 + cob, zBase + cob + 0.014),
                            (x, m["b"]/2 - cob, zBase + cob + 0.014), COR_ACO, 1)

    def _cotas(self, m, zBase, zTopo, E):
        a, b = m["a"], m["b"]
        fora = 0.45
        yc, xc = -b/2 - fora, a/2 + fora
        verticais = self.pitch < 1.2
        if abs(math.cos(self.yaw)) > 0.25:
            self._cota((-a/2, yc, zBase), (a/2, yc, zBase), f"a = {a:.2f}", (0, 0, 1))
        if abs(math.sin(self.yaw)) > 0.25:
            self._cota((xc, -b/2, zBase), (xc, b/2, zBase), f"b = {b:.2f}", (0, 0, 1))
        if verticais:
            self._cota((a/2 + 0.22, -b/2 - 0.22, zBase),
                       (a/2 + 0.22, -b/2 - 0.22, zTopo), f"h = {m['h']:.2f}", (1, 0, 0))
            self._cota((xc + 0.45, 0, 0), (xc + 0.45, 0, zBase),
                       f"h_f = {m['hf']:.2f}", (1, 0, 0))

    def _cota(self, p, q, txt, dir_tique):
        self._linha(p, q, COR_COTA, 1, None, True)
        t = 0.09
        for e in (p, q):
            self._linha(tuple(e[i] - dir_tique[i] * t for i in range(3)),
                        tuple(e[i] + dir_tique[i] * t for i in range(3)),
                        COR_COTA, 1, None, True)
        self._rotulo(tuple((p[i] + q[i]) / 2 for i in range(3)), txt, COR_COTA, 0, -8, 8)

    # ------------------------------------------------------------- desenho
    def desenhar(self):
        W, H = self._dim()
        self.pool.iniciar()
        if not self.modelo:
            self.pool.texto(W / 2, H / 2, "Nenhum modelo calculado", "#6b7a85",
                            ("Segoe UI", 12))
            self.pool.texto(W / 2, H / 2 + 22,
                            "Preencha os dados e use Calcular (F5). "
                            "Arraste para girar, role para aproximar.",
                            "#4f5d66", ("Segoe UI", 9))
            self.pool.finalizar()
            return

        itens = []
        for p in self._primitivas:
            if p[0] == "face":
                pr = [self.projetar(v) for v in p[1]]
                if any(v[2] <= 0.1 for v in pr):
                    continue
                itens.append((sum(v[2] for v in pr) / len(pr), p, pr))
            else:
                a, b = self.projetar(p[1]), self.projetar(p[2])
                if a[2] <= 0.1 or b[2] <= 0.1:
                    continue
                itens.append(((a[2] + b[2]) / 2, p, [a, b]))
        itens.sort(key=lambda t: -t[0])
        for _, p, pr in itens:
            self._pintar(p, pr)

        for p in self._sobrepostas:
            if p[0] == "face":
                pr = [self.projetar(v) for v in p[1]]
                if not any(v[2] <= 0.1 for v in pr):
                    self._pintar(p, pr)
            elif p[0] == "linha":
                a, b = self.projetar(p[1]), self.projetar(p[2])
                if a[2] > 0.1 and b[2] > 0.1:
                    self._pintar(p, [a, b])
        for p in self._sobrepostas:
            if p[0] != "rotulo":
                continue
            s = self.projetar(p[1])
            if s[2] <= 0.1:
                continue
            self.pool.texto(s[0] + p[4], s[1] + p[5], p[2], p[3],
                            ("Consolas", p[6]))
        self.pool.finalizar()

    def _pintar(self, p, pr):
        if p[0] == "face":
            pontos = [v for ponto in pr for v in ponto[:2]]
            self.pool.poligono(pontos, p[2] or "", p[3] or (p[2] or ""))
        else:
            self.pool.polilinha([pr[0][0], pr[0][1], pr[1][0], pr[1][1]],
                                p[3], p[4], p[5])

    # ----------------------------------------------------------- interação
    def _ao_girar(self):
        """As cotas dependem do ângulo, então a cena é remontada ao girar."""
        self.construir()
        self.desenhar()

    def definir_modelo(self, m):
        self.modelo = m
        self.enquadrar()
        self.construir()
        self.desenhar()

    def alternar(self, chave, valor):
        self.opcoes[chave] = valor
        self.construir()
        self.desenhar()

    def vista(self, nome) -> dict:
        v = {"iso": (-1.06, 0.34, {"solo": True}),
             "frente": (0.0, 0.02, {"solo": True}),
             "lado": (-math.pi / 2, 0.02, {"solo": True}),
             "topo": (0.0, 1.53, {"solo": False, "armaduras": True})}.get(nome)
        if not v:
            return {}
        self.yaw, self.pitch, forcadas = v
        self.opcoes.update(forcadas)
        self.enquadrar()
        self.construir()
        self.desenhar()
        return forcadas

