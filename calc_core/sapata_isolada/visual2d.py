"""
visual2d.py
-----------
Dois desenhos bidimensionais para o canvas do Tkinter, cada um com sua própria
finalidade e sem misturar assuntos:

    MapaMomentos  — isovalores de momento fletor em planta (leitura estrutural)
    PerfilCortes  — cortes do maciço para identificação das camadas (geotecnia)
"""
from __future__ import annotations

import math
from typing import Optional

from .geotecnia import acrescimo_tensao_centro, influencia_canto_retangulo
from .momentos import CampoMomentos, cor_hex, curvas_nivel, niveis_uteis
from .pintura import PoolCanvas, encadear_segmentos, faixas_por_linha

FUNDO = "#1a2026"
TINTA = "#e6eaec"
TINTA_FRACA = "#8b96a0"
GRADE = "#38434d"
COTA = "#39c2dc"
DESTAQUE = "#f0873c"

CORES_SUBSTRATO = {"granular": "#c79a2e", "coesivo": "#6f8c6b",
                   "aterro": "#9a7b57", "rocha": "#6b7c8e"}


def _escurecer(hexa: str, k: float = 0.32) -> str:
    """Versão escurecida de uma cor, para o fundo do corte."""
    r, g, b = (int(hexa[i:i + 2], 16) for i in (1, 3, 5))
    return f"#{int(r*k):02x}{int(g*k):02x}{int(b*k):02x}"


# =========================================================================== #
#  Mapa de isovalores de momento
# =========================================================================== #
class MapaMomentos:
    """
    Mapa de momentos em planta, no formato de isovalores: fundo em cores,
    curvas de nível rotuladas e a seção de referência (face do pilar) marcada.
    """

    def __init__(self, canvas) -> None:
        self.canvas = canvas
        self.campo: Optional[CampoMomentos] = None
        self.campo_analitico: Optional[CampoMomentos] = None
        self.campo_grelha: Optional[CampoMomentos] = None
        self.fonte = "analitico"       # ou "grelha"
        self.rigida: Optional[bool] = None
        self.direcao = "X"
        self.mostrar_isolinhas = True
        self.mostrar_grade = False
        self.pool = PoolCanvas(canvas)
        canvas.bind("<Configure>", lambda e: self.desenhar())

    def definir(self, campo_analitico: Optional[CampoMomentos],
               campo_grelha: Optional[CampoMomentos] = None,
               rigida: Optional[bool] = None) -> None:
        """
        Recebe os dois campos possíveis: o analítico (plano de tensões
        rígido) e o real da grelha discretizada sobre apoios elásticos —
        mesma convenção de `SuperficieMomentos3D.definir`.

        `rigida` é a classificação da sapata (NBR 6118, 22.6.1/22.6.2.3): se
        `False` (sapata flexível), a hipótese de placa rígida do campo
        analítico não vale, e a fonte padrão passa a ser a grelha. Se `True`
        ou desconhecida, mantém o analítico como padrão.
        """
        self.campo_analitico = campo_analitico
        self.campo_grelha = campo_grelha
        self.rigida = rigida
        self.fonte = ("grelha" if rigida is False and campo_grelha is not None
                      else "analitico")
        self._escolher_campo()
        self.desenhar()

    def definir_fonte(self, fonte: str) -> None:
        self.fonte = "grelha" if fonte == "grelha" else "analitico"
        self._escolher_campo()
        self.desenhar()

    def _escolher_campo(self) -> None:
        if self.fonte == "grelha" and self.campo_grelha is not None:
            self.campo = self.campo_grelha
        else:
            self.campo = self.campo_analitico

    def definir_direcao(self, direcao: str) -> None:
        self.direcao = direcao
        self.desenhar()

    def alternar(self, chave: str, valor: bool) -> None:
        setattr(self, chave, valor)
        self.desenhar()

    # ------------------------------------------------------------------ útil
    def _dim(self):
        return (max(self.canvas.winfo_width(), 10),
                max(self.canvas.winfo_height(), 10))

    def desenhar(self) -> None:
        W, H = self._dim()
        self.pool.iniciar()
        if not self.campo:
            self.pool.texto(W / 2, H / 2, "Nenhum campo calculado", TINTA_FRACA,
                            ("Segoe UI", 12))
            self.pool.finalizar()
            return

        campo = self.campo
        valores = campo.faixa(self.direcao)
        vmax = max(max(l) for l in valores)
        largura_legenda = 92
        margem = 36

        util_w = W - 2 * margem - largura_legenda
        util_h = H - margem - 96          # espaço do cabeçalho no topo
        if util_w < 40 or util_h < 40:
            return
        esc = min(util_w / campo.a, util_h / campo.b)
        cx = margem + util_w / 2
        cy = 92 + util_h / 2

        def px(x):
            return cx + x * esc

        def py(y):
            return cy - y * esc          # y para cima no desenho

        self._celulas(campo, valores, vmax, px, py)
        if self.mostrar_grade:
            self._grade(campo, px, py)
        if self.mostrar_isolinhas:
            self._isolinhas(campo, valores, vmax, px, py)
        self._contornos(campo, px, py, esc)
        self._legenda(W, H, campo, vmax, largura_legenda)
        self._cabecalho(W, campo, vmax)
        self.pool.finalizar()

    # ------------------------------------------------------------- camadas
    N_FAIXAS = 16
    PASSO_DESENHO = 2

    def _celulas(self, campo, valores, vmax, px, py):
        """
        Preenchimento por faixas de valor, agregando células vizinhas de mesma
        faixa numa só barra. Uma grade 60x60 desenhada célula a célula custa
        milhares de itens de canvas; por faixas cai para algumas centenas, e o
        resultado ainda ganha bandas nítidas.
        """
        xs, ys = campo.x, campo.y
        if vmax <= 0:
            return
        limites = [vmax * (k + 1) / self.N_FAIXAS for k in range(self.N_FAIXAS - 1)]
        cores = [cor_hex((k + 0.5) / self.N_FAIXAS) for k in range(self.N_FAIXAS)]

        passo = self.PASSO_DESENHO
        for j in range(0, len(ys) - passo, passo):
            j2 = j + passo
            medias = [(valores[j][i] + valores[j][i + 1]
                       + valores[j2][i] + valores[j2][i + 1]) / 4.0
                      for i in range(len(xs) - 1)]
            y0, y1 = py(ys[j]), py(ys[j2])
            for i0, i1, faixa in faixas_por_linha(medias, limites):
                cor = cores[min(faixa, self.N_FAIXAS - 1)]
                self.pool.poligono(
                    [px(xs[i0]), y0, px(xs[i1]), y0, px(xs[i1]), y1,
                     px(xs[i0]), y1], cor, cor)

    def _grade(self, campo, px, py):
        passo = 0.25
        n = int(campo.a / passo)
        for i in range(n + 1):
            x = -campo.a / 2 + i * passo
            if x > campo.a / 2:
                break
            self.pool.linha(px(x), py(-campo.b / 2), px(x), py(campo.b / 2),
                            GRADE, 1)
        m = int(campo.b / passo)
        for j in range(m + 1):
            y = -campo.b / 2 + j * passo
            if y > campo.b / 2:
                break
            self.pool.linha(px(-campo.a / 2), py(y), px(campo.a / 2), py(y),
                            GRADE, 1)

    def _isolinhas(self, campo, valores, vmax, px, py):
        c = self.canvas
        niveis = niveis_uteis(vmax, 8)
        for indice, nivel in enumerate(niveis):
            segmentos = curvas_nivel(campo.x, campo.y, valores, nivel)
            # costurar os segmentos troca centenas de itens por poucas curvas
            for curva in encadear_segmentos(segmentos):
                pontos = []
                for pt in curva:
                    pontos += [px(pt[0]), py(pt[1])]
                self.pool.polilinha(pontos, "#2b3238", 1)
            if segmentos:
                # rótulo na parte inferior da isolinha, com tarja para não
                # se perder sobre o fundo colorido
                # escalona a altura do rótulo: as isolinhas são quase
                # paralelas e todos os rótulos cairiam na mesma linha
                fracao = (indice % max(len(niveis), 1)) / max(len(niveis) - 1, 1)
                alvo = campo.b * (0.36 - 0.72 * fracao)
                p = min(segmentos, key=lambda s: abs(s[0][1] - alvo))[0]
                tx, ty = px(p[0]), py(p[1])
                self.pool.poligono([tx - 11, ty - 6, tx + 11, ty - 6,
                                    tx + 11, ty + 6, tx - 11, ty + 6],
                                   "#f4f6f7", "")
                self.pool.texto(tx, ty, f"{nivel:g}", "#1d2429", ("Consolas", 7))

    def _contornos(self, campo, px, py, esc):
        pool = self.pool
        a, b, ap, bp = campo.a, campo.b, campo.ap, campo.bp

        def retangulo(x0, y0, x1, y1, contorno, largura=1, preenche=""):
            pool.poligono([x0, y0, x1, y0, x1, y1, x0, y1], preenche, contorno,
                          largura)

        retangulo(px(-a/2), py(b/2), px(a/2), py(-b/2), TINTA, 2)
        retangulo(px(-ap/2), py(bp/2), px(ap/2), py(-bp/2), TINTA, 1)

        # seção de referência: face do pilar na direção em exibição
        if self.direcao == "X":
            for sx in (-1, 1):
                pool.linha(px(sx * ap / 2), py(-b/2), px(sx * ap / 2), py(b/2),
                           DESTAQUE, 2, (6, 3))
            pool.texto(px(ap/2) + 6, py(b/2) + 12, "seção de referência",
                       DESTAQUE, ("Consolas", 8), "w")
        else:
            for sy in (-1, 1):
                pool.linha(px(-a/2), py(sy * bp / 2), px(a/2), py(sy * bp / 2),
                           DESTAQUE, 2, (6, 3))
            pool.texto(px(-a/2), py(bp/2) - 10, "seção de referência",
                       DESTAQUE, ("Consolas", 8), "w")

        pool.texto((px(-a/2) + px(a/2)) / 2, py(-b/2) + 16, f"a = {a:.2f} m",
                   COTA, ("Consolas", 9))
        pool.texto(px(a/2) + 18, (py(-b/2) + py(b/2)) / 2, f"b = {b:.2f}",
                   COTA, ("Consolas", 9), "center", 90)
        seta = "→ X" if self.direcao == "X" else "↑ Y"
        pool.texto(px(-a/2), py(-b/2) + 16, seta, TINTA_FRACA,
                   ("Consolas", 9), "w")

    def _legenda(self, W, H, campo, vmax, largura):
        pool = self.pool
        x0 = W - largura + 12
        y0, y1 = 108, H - 58
        n = 40
        for i in range(n):
            t = 1 - i / n
            yy0 = y0 + (y1 - y0) * i / n
            yy1 = y0 + (y1 - y0) * (i + 1) / n
            cor = cor_hex(t)
            pool.poligono([x0, yy0, x0 + 20, yy0, x0 + 20, yy1, x0, yy1], cor, cor)
        pool.poligono([x0, y0, x0 + 20, y0, x0 + 20, y1, x0, y1], "", TINTA_FRACA)
        for i in range(6):
            t = 1 - i / 5
            yy = y0 + (y1 - y0) * i / 5
            pool.linha(x0 + 20, yy, x0 + 24, yy, TINTA_FRACA)
            pool.texto(x0 + 27, yy, f"{vmax * t:.0f}", TINTA, ("Consolas", 8), "w")
        pool.texto(x0, y0 - 12, "kN·m/m", TINTA_FRACA, ("Consolas", 8), "w")

    def _cabecalho(self, W, campo, vmax):
        pool = self.pool
        rot = ("Momento que arma a direção X (barras paralelas a X)"
               if self.direcao == "X" else
               "Momento que arma a direção Y (barras paralelas a Y)")
        pool.texto(20, 22, rot, TINTA, ("Segoe UI Semibold", 11), "w")
        md = campo.md_projeto_x if self.direcao == "X" else campo.md_projeto_y
        largura = campo.b if self.direcao == "X" else campo.a
        fonte = ("grelha discretizada" if campo is self.campo_grelha
                 and self.campo_grelha is not None else "campo analítico (placa rígida)")
        pool.texto(20, 42, f"máx {vmax:.1f} kN·m/m  ·  faixa integrada "
                           f"{vmax * largura:.1f} kN·m  ·  fonte: {fonte}",
                   TINTA_FRACA, ("Consolas", 8), "w")
        pool.texto(20, 58, f"M_d adotado no cálculo {md:.1f} kN·m  ·  "
                           f"{campo.combinacao}", TINTA_FRACA, ("Consolas", 8), "w")
        y = 74
        if campo.parcial:
            pool.texto(20, y, "seção parcialmente comprimida — campo aproximado",
                       DESTAQUE, ("Consolas", 8), "w")
            y += 16
        if self.rigida is False:
            pool.texto(20, y, "Sapata FLEXÍVEL (NBR 6118, 22.6.1/22.6.2.3) — o campo "
                              "analítico assume placa rígida; use a Grelha para "
                              "o comportamento real.", DESTAQUE,
                       ("Consolas", 8), "w")


# =========================================================================== #
#  Perfil geológico em cortes
# =========================================================================== #
class PerfilCortes:
    """
    Cortes do maciço para identificação das camadas: coluna estratigráfica em
    escala, nível d'água, cota de assentamento e a sapata na posição. Sem
    diagramas de tensão — este desenho serve para reconhecer o perfil.
    """

    NIVEIS_BULBO = (0.80, 0.60, 0.50, 0.40, 0.30, 0.20, 0.15, 0.10, 0.05)
    MEIA_LARGURA = 1.25      # semilargura do corte, em múltiplos da dimensão
    PROFUNDIDADE = 2.6       # em múltiplos do menor lado
    N_GRADE = 61

    def __init__(self, canvas) -> None:
        self.canvas = canvas
        self.modelo: Optional[dict] = None
        self.direcao = "X"
        self.mostrar_bulbo = True
        self.fonte = "boussinesq"      # ou "mef"
        self.malha_mef = None
        self._cache_bulbo = None
        canvas.bind("<Configure>", lambda e: self.desenhar())

    def alternar(self, chave: str, valor: bool) -> None:
        setattr(self, chave, valor)
        self.desenhar()

    def definir_modelo(self, modelo: dict) -> None:
        self.modelo = modelo
        self._cache_bulbo = None
        self.desenhar()

    def definir_mef(self, malha) -> None:
        self.malha_mef = malha
        self._cache_bulbo = None
        self.desenhar()

    def definir_fonte(self, fonte: str) -> None:
        self.fonte = fonte
        self._cache_bulbo = None
        self.desenhar()

    def definir_direcao(self, direcao: str) -> None:
        self.direcao = direcao
        self.desenhar()

    def _dim(self):
        return (max(self.canvas.winfo_width(), 10),
                max(self.canvas.winfo_height(), 10))

    def desenhar(self) -> None:
        """
        Layout com escala ISOTRÓPICA: o corte usa o mesmo número de pixels por
        metro na horizontal e na vertical, sem o que o bulbo sairia achatado e
        deixaria de ser lido como distância real no maciço.
        """
        c = self.canvas
        c.delete("all")
        W, H = self._dim()
        m = self.modelo
        if not m:
            c.create_text(W / 2, H / 2, text="Nenhum perfil calculado",
                          fill=TINTA_FRACA, font=("Segoe UI", 12))
            return
        camadas = m.get("camadas") or []
        if not camadas:
            c.create_text(W / 2, H / 2, text="Perfil estratigráfico não informado",
                          fill=TINTA_FRACA, font=("Segoe UI", 12))
            return

        prof_total = camadas[-1]["z_base"]
        dim = m["a"] if self.direcao == "X" else m["b"]
        transversal = m["b"] if self.direcao == "X" else m["a"]
        meia = dim * self.MEIA_LARGURA          # semilargura do corte, em metros

        col_x, col_l, faixa_rotulos = 62.0, 22.0, 158.0
        corte_x0 = col_x + col_l + faixa_rotulos
        corte_x1 = W - 22.0
        topo, base = 66.0, H - 52.0

        largura_corte = max(corte_x1 - corte_x0, 60.0)
        esc = min((base - topo) / prof_total, largura_corte / (2.0 * meia))
        eixo = (corte_x0 + corte_x1) / 2.0

        def ym(z):
            return topo + z * esc

        def px(x):
            return eixo + x * esc

        rotulo = "CORTE X" if self.direcao == "X" else "CORTE Y"
        c.create_text(20, 22, anchor="w", fill=TINTA, text=f"{rotulo} — perfil",
                      font=("Segoe UI Semibold", 11))
        c.create_text(20, 40, anchor="w", fill=TINTA_FRACA, font=("Consolas", 8),
                      text=f"profundidade {prof_total:.2f} m · {len(camadas)} camadas"
                           f" · escala 1:{100/esc*10:.0f}")

        # ----------------------------------------------------- estratigrafia
        for c_ in camadas:
            y0, y1 = ym(c_["z_topo"]), ym(c_["z_base"])
            if y0 > base:
                break
            y1 = min(y1, base)
            cor = CORES_SUBSTRATO.get(c_["tipo"], "#888888")
            c.create_rectangle(col_x, y0, col_x + col_l, y1, fill=cor,
                               outline="#20272c", width=1)
            self._hachura(col_x, col_l, y0, y1, c_["tipo"])
            # faixa de fundo do corte, para o bulbo ser lido sobre o estrato
            c.create_rectangle(corte_x0, y0, corte_x1, y1,
                               fill=_escurecer(cor), outline="")
            meio = (y0 + y1) / 2
            c.create_text(col_x + col_l + 10, meio - 7, anchor="w", fill=TINTA,
                          text=c_["nome"][:24], font=("Segoe UI", 9))
            c.create_text(col_x + col_l + 10, meio + 8, anchor="w",
                          fill=TINTA_FRACA, font=("Consolas", 8),
                          text=f"{c_['tipo']} · {c_['z_topo']:.2f}–"
                               f"{c_['z_base']:.2f} m")
            c.create_line(col_x - 6, y0, col_x, y0, fill=TINTA_FRACA)
            c.create_text(col_x - 10, y0, anchor="e", fill=TINTA_FRACA,
                          text=f"{c_['z_topo']:.2f}", font=("Consolas", 8))
            c.create_line(corte_x0, y0, corte_x1, y0, fill="#2b3238")
        c.create_text(col_x - 10, min(ym(prof_total), base), anchor="e",
                      fill=TINTA_FRACA, text=f"{prof_total:.2f}",
                      font=("Consolas", 8))

        # ------------------------------------------------------ nível d'água
        na = m.get("nivel_agua")
        if na is not None and ym(na) <= base:
            y = ym(na)
            c.create_line(col_x - 24, y, corte_x1, y, fill="#4aa8d8", width=1,
                          dash=(6, 3))
            c.create_polygon(col_x - 24, y, col_x - 16, y, col_x - 20, y - 9,
                             fill="#4aa8d8", outline="")
            c.create_text(col_x - 28, y - 8, anchor="e", fill="#4aa8d8",
                          text=f"N.A. {na:.2f}", font=("Consolas", 8))

        # ----------------------------------------------------------- a sapata
        hf, h, h0 = m["hf"], m["h"], m["h0"]
        dim_t = m["at"] if self.direcao == "X" else m["bt"]
        dim_p = m["ap"] if self.direcao == "X" else m["bp"]
        y_base, y_aba, y_topo = ym(hf), ym(hf - h0), ym(hf - h)
        c.create_polygon(px(-dim/2), y_base, px(dim/2), y_base,
                         px(dim/2), y_aba, px(-dim/2), y_aba,
                         fill="#ccd2ce", outline="#eef0ec", width=1)
        c.create_polygon(px(-dim/2), y_aba, px(dim/2), y_aba,
                         px(dim_t/2), y_topo, px(-dim_t/2), y_topo,
                         fill="#ccd2ce", outline="#eef0ec", width=1)
        c.create_rectangle(px(-dim_p/2), y_topo, px(dim_p/2), y_topo - 26,
                           fill="#a7aeaa", outline="#eef0ec")
        c.create_line(col_x + col_l, y_base, px(-dim/2), y_base,
                      fill="#a8362b", width=1, dash=(4, 3))
        c.create_text(px(0), y_topo - 34, fill=TINTA, font=("Consolas", 8),
                      text=f"{dim:.2f} × {h:.2f} m  ·  assentamento {hf:.2f} m")

        if self.mostrar_bulbo:
            self._bulbo(m, px, ym, dim, transversal, hf, esc, base, W)

        c.create_text(W - 16, H - 16, anchor="e", fill=TINTA_FRACA,
                      font=("Consolas", 8),
                      text="corte para identificação das camadas"
                           + (" e do bulbo" if self.mostrar_bulbo else ""))

    # ------------------------------------------------------------- bulbo
    @staticmethod
    def _razao(x: float, z: float, a: float, b: float) -> float:
        """Δσ/q no plano do corte (y = 0), por Boussinesq/Newmark."""
        if z <= 1e-6:
            return 1.0 if abs(x) <= a / 2 else 0.0

        def termo(X, Y):
            sg = (1 if X >= 0 else -1) * (1 if Y >= 0 else -1)
            return sg * influencia_canto_retangulo(abs(X) / z, abs(Y) / z)

        return 2.0 * termo(a / 2 + x, b / 2) + 2.0 * termo(a / 2 - x, b / 2)

    def _campo_bulbo(self, dim, transversal):
        """
        Curvas de nível do campo Δσ/q no corte, guardadas entre quadros: o
        marching squares sobre a grade custa dezenas de milissegundos e o campo
        só muda quando a geometria muda.
        """
        chave = (round(dim, 4), round(transversal, 4), self.N_GRADE,
                 round(self.MEIA_LARGURA, 3), round(self.PROFUNDIDADE, 3),
                 self.fonte, id(self.malha_mef) if self.malha_mef else 0)
        if self._cache_bulbo and self._cache_bulbo[0] == chave:
            return self._cache_bulbo[1]
        n = self.N_GRADE
        meia = dim * self.MEIA_LARGURA
        prof = self.PROFUNDIDADE * min(dim, transversal)
        xs = [-meia + 2 * meia * i / (n - 1) for i in range(n)]
        zs = [prof * j / (n - 1) for j in range(n)]
        if self.fonte == "mef" and self.malha_mef is not None:
            # o campo do MEF é axissimétrico: a coordenada do corte vira raio
            z0 = self.malha_mef.z[0]
            campo = [[self.malha_mef.razao_em(x, z0 + max(z, 1e-4)) for x in xs]
                     for z in zs]
        else:
            campo = [[self._razao(x, max(z, 1e-4), dim, transversal) for x in xs]
                     for z in zs]
        curvas = {}
        for nivel in self.NIVEIS_BULBO:
            segmentos = curvas_nivel(xs, zs, campo, nivel)
            curvas[nivel] = (encadear_segmentos(segmentos),
                             max((p for seg in segmentos for p in seg),
                                 key=lambda p: p[1]) if segmentos else None)
        self._cache_bulbo = (chave, curvas)
        return curvas

    def _bulbo(self, m, px, ym, dim, transversal, hf, esc, base, W):
        """
        Bulbo delimitado por curvas de nível de Δσ/q. Sem preenchimento: no
        corte o que interessa é até onde cada fração da tensão aplicada chega.
        """
        c = self.canvas
        curvas = self._campo_bulbo(dim, transversal)

        def py(z):
            return ym(hf + z)

        for nivel in self.NIVEIS_BULBO:
            polilinhas, fundo = curvas.get(nivel, ([], None))
            if not polilinhas:
                continue
            forte = nivel in (0.10, 0.20, 0.50)
            cor = "#7fd8e8" if forte else "#43707d"
            for curva in polilinhas:
                pontos = []
                for pt in curva:
                    y = py(pt[1])
                    if y > base:
                        continue
                    pontos += [px(pt[0]), y]
                if len(pontos) >= 4:
                    c.create_line(*pontos, fill=cor,
                                  width=1.6 if forte else 1, smooth=True)
            if fundo and py(fundo[1]) <= base - 6:
                c.create_text(px(fundo[0]), py(fundo[1]) + 7,
                              text=f"{nivel*100:.0f}%", fill=cor,
                              font=("Consolas", 7))

        q = m.get("q_liquido")
        legenda = ("Δσ/q (MEF em camadas)" if self.fonte == "mef"
                   and self.malha_mef is not None else "Δσ/q (Boussinesq)")
        if q:
            legenda += f" · q_líq {q:.0f} kPa"
        c.create_text(px(0), min(py(self.PROFUNDIDADE * min(dim, transversal))
                                 + 20, base - 8),
                      text=legenda, fill="#7fd8e8", font=("Consolas", 8))

    def _hachura(self, x, larg, y0, y1, tipo):
        c = self.canvas
        n = max(1, int((y1 - y0) / 11))
        for i in range(n):
            yy = y0 + (i + 0.5) * (y1 - y0) / n
            if tipo == "coesivo":
                c.create_line(x + 6, yy, x + larg - 6, yy, fill="#4a5f47")
            elif tipo == "rocha":
                c.create_line(x + 6, yy, x + larg - 6, yy + 5, fill="#4a5560")
            else:
                for j in range(4):
                    xx = x + 12 + j * (larg - 24) / 3
                    c.create_oval(xx - 1, yy - 1, xx + 1, yy + 1,
                                  fill="#6f5a20", outline="")


# =========================================================================== #
#  Reação do solo: modelo rígido x discretizado
# =========================================================================== #
class ReacaoSolo:
    """
    Compara a distribuição de pressões do modelo rígido (linear) com a obtida
    por discretização em base elástica, na direção escolhida.

    O desenho tem três faixas: a sapata em corte, o diagrama de pressões e o
    recalque da peça — é o recalque diferencial que explica a diferença entre
    as duas distribuições.
    """

    def __init__(self, canvas) -> None:
        self.canvas = canvas
        self.reacao = None
        self.classificacao = None
        self.geometria: Optional[dict] = None
        self.direcao = "X"
        self.pool = PoolCanvas(canvas)
        canvas.bind("<Configure>", lambda e: self.desenhar())

    def definir(self, reacoes: dict, classificacao, geometria: dict) -> None:
        self.reacoes = reacoes or {}
        self.classificacao = classificacao
        self.geometria = geometria
        self.reacao = self.reacoes.get(self.direcao)
        self.desenhar()

    def definir_direcao(self, direcao: str) -> None:
        self.direcao = direcao
        self.reacao = getattr(self, "reacoes", {}).get(direcao)
        self.desenhar()

    def _dim(self):
        return (max(self.canvas.winfo_width(), 10),
                max(self.canvas.winfo_height(), 10))

    def desenhar(self) -> None:
        W, H = self._dim()
        pool = self.pool
        pool.iniciar()
        r = self.reacao
        if not r:
            pool.texto(W / 2, H / 2, "Reação do solo não calculada", TINTA_FRACA,
                       ("Segoe UI", 12))
            pool.finalizar()
            return

        m = self.geometria or {}
        dim = r.x[-1] - r.x[0]
        esq, dir_ = 70.0, W - 40.0
        esc = (dir_ - esq) / max(dim, 1e-6)

        def px(x):
            return (esq + dir_) / 2.0 + x * esc

        self._cabecalho(W, r)

        # ---------------------------------------------------- sapata em corte
        y_sapata = 148.0
        alt = 26.0
        dim_p = (m.get("ap") if self.direcao == "X" else m.get("bp")) or 0.3
        pool.poligono([px(-dim/2), y_sapata, px(dim/2), y_sapata,
                       px(dim/2), y_sapata - alt * 0.45,
                       px(-dim/2), y_sapata - alt * 0.45], "#3a4249", "#ccd2ce")
        pool.poligono([px(-dim/2), y_sapata - alt * 0.45,
                       px(dim/2), y_sapata - alt * 0.45,
                       px(dim_p/2 + 0.05), y_sapata - alt,
                       px(-dim_p/2 - 0.05), y_sapata - alt], "#3a4249", "#ccd2ce")
        pool.poligono([px(-dim_p/2), y_sapata - alt, px(dim_p/2), y_sapata - alt,
                       px(dim_p/2), y_sapata - alt - 15,
                       px(-dim_p/2), y_sapata - alt - 15], "#4a545b", "#ccd2ce")

        # ------------------------------------------------ diagrama de pressões
        topo_p = y_sapata + 16
        altura_p = (H - 150) * 0.56
        pmax = max(max(r.pressao), max(r.pressao_linear), 1e-6)
        k = altura_p / pmax

        pool.linha(px(-dim/2), topo_p, px(dim/2), topo_p, "#4a5760", 1)
        for frac in (0.25, 0.5, 0.75, 1.0):
            y = topo_p + k * pmax * frac
            pool.linha(esq, y, dir_, y, "#252d33", 1)
            pool.texto(esq - 6, y, f"{pmax*frac:.0f}", TINTA_FRACA,
                       ("Consolas", 8), "e")
        pool.texto(esq - 6, topo_p, "0", TINTA_FRACA, ("Consolas", 8), "e")
        pool.texto(esq - 6, topo_p - 14, "kPa", TINTA_FRACA, ("Consolas", 8), "e")

        linear = []
        disc = []
        for i, x in enumerate(r.x):
            linear += [px(x), topo_p + k * r.pressao_linear[i]]
            disc += [px(x), topo_p + k * r.pressao[i]]
        pool.polilinha(linear, "#8b96a0", 1, (5, 3))
        pool.polilinha(disc, "#39c2dc", 2)

        meio = len(r.x) // 2
        pool.texto(px(r.x[meio]) + 8, topo_p + k * r.pressao[meio] + 12,
                   f"discretizado — pico {max(r.pressao):.0f} kPa", "#39c2dc",
                   ("Consolas", 8), "w")
        pool.texto(px(r.x[2]) , topo_p + k * r.pressao_linear[2] - 12,
                   f"rígido (linear) — pico {max(r.pressao_linear):.0f} kPa",
                   "#8b96a0", ("Consolas", 8), "w")

        # ------------------------------------------------------- recalque
        topo_w = topo_p + altura_p + 44
        wmax = max(max(r.recalque), 1e-9)
        kw = 34.0 / wmax
        pool.linha(px(-dim/2), topo_w, px(dim/2), topo_w, "#4a5760", 1)
        curva = []
        for i, x in enumerate(r.x):
            curva += [px(x), topo_w + kw * r.recalque[i]]
        pool.polilinha(curva, "#c79a2e", 2)
        pool.texto(esq - 6, topo_w, "0", TINTA_FRACA, ("Consolas", 8), "e")
        pool.texto(px(r.x[meio]), topo_w + kw * wmax + 16,
                   f"recalque da peça — máx {wmax*1000:.2f} mm  ·  "
                   f"diferencial {abs(r.recalque[meio]-r.recalque[0])*1000:.2f} mm",
                   "#c79a2e", ("Consolas", 8))
        pool.finalizar()

    def _cabecalho(self, W, r):
        pool = self.pool
        c = self.classificacao
        pool.texto(20, 22, f"Reação do solo — direção {self.direcao}", TINTA,
                   ("Segoe UI Semibold", 11), "w")
        if c:
            regime = ("RÍGIDA pela NBR 6118, 22.6.1"
                      if c.rigida_nbr else "FLEXÍVEL — verificar punção (22.6.2.3-b)")
            pool.texto(20, 42, f"{regime}  ·  h necessário para rigidez "
                               f"{c.h_necessario:.2f} m", TINTA_FRACA,
                       ("Consolas", 8), "w")
            lam = max(c.lambda_L_x, c.lambda_L_y)
            pool.texto(20, 58, f"λ·L = {lam:.2f} → {c.classe_hetenyi}  ·  "
                               f"k_v = {r.kv:,.0f} kN/m³".replace(",", " "),
                       TINTA_FRACA, ("Consolas", 8), "w")
        razao = r.momento_face / r.momento_face_linear if r.momento_face_linear else 1
        pool.texto(20, 78, f"M na face do pilar: discretizado "
                           f"{r.momento_face:.1f} vs rígido "
                           f"{r.momento_face_linear:.1f} kN·m/m ({razao:.2f}×)",
                   DESTAQUE if abs(razao - 1) > 0.10 else TINTA_FRACA,
                   ("Consolas", 8), "w")
