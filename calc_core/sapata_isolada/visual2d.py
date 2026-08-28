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

from .geotecnia import (
    AVISO_MEIO_HOMOGENEO,
    AVISO_NAO_NORMATIVO,
    FONTE_2V1H,
    FONTE_BOUSSINESQ,
    ROTULO_FONTE,
    PropagacaoTensoes,
    influencia_canto_retangulo,
    propagacao_em_profundidade,
)
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

# Mesmas cores do banner "Banner.TLabel" de ui/completo/tema.py (AMARELO /
# fundo #3a2a10) — reaproveitadas aqui, não reinventadas, para que o aviso
# permanente do corte de espraiamento tenha a MESMA leitura visual do banner
# de escopo amplo que já fica fixo na tela (mesmo padrão pedido no requisito
# REQ-UI-01/REQ-UI-02 do ruleset).
AVISO_BG = "#3a2a10"
AVISO_FG = "#e2b53f"

# REQ-UI-07(d): sob Boussinesq, a largura equivalente do tronco é LEITURA
# GEOMÉTRICA ILUSTRATIVA (a solução elástica não tem tronco de espraiamento
# nem largura carregada — ver `geotecnia.largura_equivalente` e o
# `uso_autorizado` de `PC-BOUSSINESQ-NEWMARK-canto-retangulo`, item 1.b).
# Texto FIXO de legenda da UI (não um valor calculado): não precisa vir do
# núcleo. Sob 2V:1H a ressalva equivalente É calculada pelo núcleo (a largura
# depende do método) e vem por `prop.avisos` — nunca duplicada aqui.
RESSALVA_LARGURA_ILUSTRATIVA_BOUSSINESQ = (
    "a_eq/b_eq sob Boussinesq: leitura geométrica ILUSTRATIVA, não a área de "
    "um tronco real — a solução elástica não tem espraiamento nem largura "
    "carregada.")


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
    # Piso da faixa reservada no topo do corte para os avisos permanentes
    # (REQ-UI-01/REQ-UI-02) quando o espraiamento por camada está ativo. A
    # ALTURA REAL é medida por `_medir_faixa_aviso` via `bbox()` dos textos de
    # verdade (eles quebram em largura variável conforme o canvas) — este
    # piso só evita uma faixa ridiculamente baixa se a medição falhar.
    FAIXA_AVISO_MINIMA = 40.0
    # Base vertical fixa do cabeçalho (título + subtítulo, `desenhar()`),
    # antes de qualquer faixa de aviso. Uma só constante para `desenhar()` e
    # `_espraiamento()` não divergirem sobre onde a faixa começa.
    TOPO_CABECALHO = 66.0

    def __init__(self, canvas) -> None:
        self.canvas = canvas
        self.modelo: Optional[dict] = None
        self.direcao = "X"
        self.mostrar_bulbo = True
        self.fonte = "boussinesq"      # ou "mef" — só do bulbo por isovalores
        self.malha_mef = None
        self._cache_bulbo = None
        # ------------------------------------------------- espraiamento por camada
        # Corte alternativo ao bulbo: pirâmide/tronco por Δσ nas INTERFACES de
        # camada (q_i, a_eq,i/b_eq,i — REQ-UI-07, ruleset v7). Estado
        # independente do `fonte` do bulbo acima: aqui "fonte_espraiamento"
        # escolhe entre Boussinesq/Newmark e 2V:1H
        # (`calc_core.sapata_isolada.geotecnia`), nunca entre analítico e MEF.
        self.mostrar_espraiamento = False
        self.fonte_espraiamento = FONTE_BOUSSINESQ
        # Mensagem de `ValueError` do núcleo na última chamada de
        # `_propagacao_atual`, para a distinguir de "sem perfil/solo" na tela
        # (a6, achado 5). `None` quando a última chamada não levantou nada.
        self._erro_espraiamento: Optional[str] = None
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

    def definir_fonte_espraiamento(self, fonte: str) -> None:
        """Boussinesq/Newmark (default) ou 2V:1H para o corte de espraiamento.

        [REQ-UI-04] Seletor de VISUALIZAÇÃO — não altera recalque nem
        verificação alguma; troca apenas qual `PropagacaoTensoes` alimenta
        `_espraiamento()`.
        """
        self.fonte_espraiamento = fonte
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
        eixo_val = "a" if self.direcao == "X" else "b"
        meia = dim * self.MEIA_LARGURA          # semilargura do corte, em metros

        # Propagação de tensões calculada UMA vez por quadro (não uma para a
        # geometria e outra para o desenho): tanto a semilargura do corte
        # (item abaixo, a6 achado 6) quanto os rótulos de `_espraiamento`
        # partem deste mesmo `PropagacaoTensoes`.
        prop_espraiamento: Optional[PropagacaoTensoes] = None
        self._erro_espraiamento = None
        if self.mostrar_espraiamento:
            try:
                prop_espraiamento = self._propagacao_atual(
                    m, self.fonte_espraiamento)
            except ValueError as e:
                self._erro_espraiamento = str(e)

        # a6, achado 6: a largura do tronco de espraiamento nunca entrava na
        # conta de `meia`/`esc`, e sob 2V:1H ela FACILMENTE excede a semi-
        # largura do corte (a_eq/2 = (a+z)/2 cresce sem limite com z). Sem
        # isto o polígono vazava ~50 px de cada lado do canvas. Usa-se a MAIOR
        # largura equivalente prevista em qualquer interface (ela é
        # estritamente crescente com z — REQ-PROP-03(F) — então o máximo é
        # sempre na interface mais profunda calculada).
        if prop_espraiamento is not None and prop_espraiamento.pontos:
            larguras = [getattr(p, f"largura_equivalente_{eixo_val}")
                       for p in prop_espraiamento.pontos]
            larguras = [v for v in larguras if v is not None]
            if larguras:
                meia = max(meia, max(larguras) / 2.0)

        col_x, col_l, faixa_rotulos = 62.0, 22.0, 158.0
        corte_x0 = col_x + col_l + faixa_rotulos
        corte_x1 = W - 22.0
        # reserva a faixa dos avisos não normativos (REQ-UI-01/REQ-UI-02, e o
        # rótulo do método/ressalva do 2V:1H — a6 achado 8) quando o
        # espraiamento por camada está ativo, para nunca sobrepor o
        # cabeçalho nem a estratigrafia. Altura MEDIDA (a6 achado 7), não
        # estimada: os textos quebram em largura variável conforme W.
        faixa_aviso = (self._medir_faixa_aviso(W, prop_espraiamento,
                                               self._erro_espraiamento)
                       if self.mostrar_espraiamento else 0.0)
        topo = self.TOPO_CABECALHO + faixa_aviso
        base = H - 52.0

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

        if self.mostrar_espraiamento:
            self._espraiamento(m, px, ym, dim, hf, base, W, topo,
                               prop_espraiamento, self._erro_espraiamento,
                               corte_x0, corte_x1)

        extras = []
        if self.mostrar_bulbo:
            extras.append("do bulbo")
        if self.mostrar_espraiamento:
            extras.append("do espraiamento por camada")
        rodape = "corte para identificação das camadas"
        if extras:
            rodape += " e " + " e ".join(extras)
        c.create_text(W - 16, H - 16, anchor="e", fill=TINTA_FRACA,
                      font=("Consolas", 8), text=rodape)

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

    # ------------------------------------------------- espraiamento por camada
    def _propagacao_atual(self, m: dict, fonte: str
                          ) -> Optional[PropagacaoTensoes]:
        """
        Chama a API do a4 (`geotecnia.propagacao_em_profundidade`) — nenhuma
        fórmula de propagação é reimplementada aqui [REQ-UI-06].

        Função de (m, fonte): `fonte` viaja como PARÂMETRO explícito — nunca
        lida de `self.fonte_espraiamento` por dentro do método — para poder
        ser testada sem depender do estado do widget (a6, achado 10) e para
        que um mutante que troque o parâmetro pelo campo de instância seja
        pego por um teste que os fixa deliberadamente diferentes.

        `m["q_servico"]` (a4, `ResultadoSapata.q_servico`, commit 783b3c3) é
        a pressão TOTAL de serviço na base, pronta — substituiu a
        reconstituição `q_liquido + sobrecarga_na_base` que existia aqui
        antes (a6, achado 4): essa soma só existia quando
        `res.recalques is not None` (falso diagnóstico de "sem perfil/solo"
        com `verificar_recalque=False`) e não era uma inversa fiel quando
        `AnaliseRecalque.q_liquido` saturava em zero. `q_servico` não tem
        nenhuma dessas duas falhas — é calculado sempre.

        Guardas de domínio do núcleo (`ValueError`) NÃO são engolidas aqui
        (a6, achado 5): propagam para o chamador, que decide o que mostrar
        na tela. Devolve None apenas quando não há dado suficiente para
        SEQUER tentar a chamada (sem solo/perfil/geometria/q_servico) — essa
        é a diferença de sentido entre "faltam dados" e "o núcleo recusou o
        domínio".
        """
        solo = m.get("solo")
        a, b = m.get("a"), m.get("b")
        q_servico = m.get("q_servico")
        if solo is None or solo.perfil is None:
            return None
        if not a or not b or q_servico is None:
            return None
        z_max = 2.0 * min(a, b)   # REQ-UI-05 — mesmo teto de 2B do bulbo
        return propagacao_em_profundidade(
            solo, a, b, q_servico, fonte=fonte, z_max=z_max)

    def _linhas_banner_espraiamento(self, prop: Optional[PropagacaoTensoes]
                                    ) -> list[tuple[str, tuple, str]]:
        """
        Sequência (texto, fonte, cor) do bloco FIXO do topo — REQ-UI-01/02 e
        REQ-UI-07(d)/(f). A MESMA sequência alimenta `_medir_faixa_aviso` (só
        mede, nunca desenha) e o desenho real em `_espraiamento`, para a
        altura reservada em `desenhar()` bater exatamente com o que sai no
        canvas — é o que resolve o `FAIXA_AVISO_ESPRAIAMENTO` fixo (a6,
        achado 7).
        """
        linhas: list[tuple[str, tuple, str]] = [
            (AVISO_NAO_NORMATIVO, ("Segoe UI Semibold", 8), AVISO_FG),
            # REQ-UI-02 — "a maior armadilha visual desta tela": o campo é de
            # meio homogêneo, mas as camadas ao lado são coloridas com suas
            # propriedades reais. Permanente, não letra miúda.
            (AVISO_MEIO_HOMOGENEO, ("Consolas", 7), AVISO_FG),
        ]
        # REQ-UI-07(f): o rótulo do método vem de `prop.rotulo_metodo` quando
        # há `prop` — nunca de `ROTULO_FONTE.get(self.fonte_espraiamento)`
        # direto (a6, achado 1). Só cai no fallback quando NÃO há prop (sem
        # perfil/solo, ou erro do núcleo) — aí não existe outra fonte.
        rotulo_metodo = (prop.rotulo_metodo if prop is not None
                         else ROTULO_FONTE.get(self.fonte_espraiamento,
                                               self.fonte_espraiamento))
        q_txt = f" · q_líq {prop.q_liquida:.0f} kPa" if prop is not None else ""
        linhas.append((f"{rotulo_metodo}{q_txt}", ("Consolas", 8, "bold"),
                       "#f4f6f7"))

        # a6, achado 8: a ressalva do MÉTODO EM USO é informação de
        # segurança, não decoração — não pode ficar no rodapé (mesmo lugar
        # que já colidiu com a coluna estratigráfica). Cada método tem a sua:
        if self.fonte_espraiamento == FONTE_BOUSSINESQ:
            linhas.append((RESSALVA_LARGURA_ILUSTRATIVA_BOUSSINESQ,
                           ("Consolas", 7), AVISO_FG))
        elif self.fonte_espraiamento == FONTE_2V1H:
            ressalva = self._ressalva_2v1h(prop)
            if ressalva is not None:
                linhas.append((ressalva, ("Consolas", 7), AVISO_FG))
        return linhas

    @staticmethod
    def _ressalva_2v1h(prop: Optional[PropagacaoTensoes]) -> Optional[str]:
        """
        A ressalva de subestimar/superestimar Δσ do 2V:1H já vem pronta do
        núcleo em `prop.avisos` (`geotecnia.propagacao_em_profundidade`) —
        nunca reescrita aqui [REQ-UI-06]. Por construção do núcleo, quando
        `fonte == FONTE_2V1H` ela é sempre o PRIMEIRO aviso que sobra depois
        de excluir os dois fixos (REQ-UI-01/02): é anexada antes da de
        "pressão líquida nula", se as duas existirem.
        """
        if prop is None:
            return None
        extras = [av for av in prop.avisos
                 if av not in (AVISO_NAO_NORMATIVO, AVISO_MEIO_HOMOGENEO)]
        return extras[0] if extras else None

    @staticmethod
    def _sem_largura_definida(prop: Optional[PropagacaoTensoes],
                              eixo_val: str) -> bool:
        """
        True quando `largura_equivalente_{a,b}` vem `None` em TODOS os
        pontos — o caso de q_líq <= 0 (`geotecnia.largura_equivalente`
        devolve `None` em todo ponto quando isso acontece). REQ-UI-07(e):
        largura indefinida nunca vira número, então esse caso não desenha
        tronco algum. Extraído em método próprio (staticmethod, sem `self`
        além da assinatura) para ser testável sem Tk (a6, achado 10).
        """
        if prop is None or not prop.pontos:
            return False
        return all(getattr(p, f"largura_equivalente_{eixo_val}") is None
                  for p in prop.pontos)

    def _avisos_nao_promovidos(self, prop: Optional[PropagacaoTensoes]
                               ) -> list[str]:
        """`prop.avisos` menos os que já aparecem na faixa fixa do topo — os
        dois permanentes (REQ-UI-01/02) e, sob 2V:1H, a ressalva específica
        do método (a6, achado 8), para nunca repetir a mesma frase duas
        vezes na tela."""
        if prop is None:
            return []
        fixos = {AVISO_NAO_NORMATIVO, AVISO_MEIO_HOMOGENEO}
        extras = [av for av in prop.avisos if av not in fixos]
        if self.fonte_espraiamento == FONTE_2V1H and extras:
            extras = extras[1:]      # o primeiro é a ressalva já promovida
        return extras

    def _mensagem_indisponivel(self, prop: Optional[PropagacaoTensoes],
                               erro: Optional[str]) -> tuple[str, str]:
        """
        (texto, cor) para quando não há tronco a desenhar — três casos bem
        distintos, que a versão anterior confundia num só letreiro genérico
        (a6, achado 3):
          1. `ValueError` do núcleo (guarda de domínio) — mostra `str(e)`,
             em destaque, NUNCA a mensagem genérica de "sem perfil/solo"
             (a6, achado 5);
          2. sem dado suficiente para sequer chamar o núcleo (sem
             perfil/solo/geometria) — mensagem genérica;
          3. o núcleo respondeu mas não há o que desenhar (perfil termina
             antes da base, profundidade excede o perfil, ou pressão líquida
             nula — REQ-UI-07(e): largura indefinida NUNCA vira número, e
             aqui é onde essa condição é tratada) — usa os avisos
             ESPECÍFICOS que o próprio núcleo já produziu, não uma frase
             nova inventada na UI [REQ-UI-06].
        """
        if erro is not None:
            return erro, DESTAQUE
        if prop is None:
            return ("Sem perfil/solo suficiente para o espraiamento por "
                    "camada.", TINTA_FRACA)
        especificos = self._avisos_nao_promovidos(prop)
        if especificos:
            return ("\n".join(especificos), TINTA_FRACA)
        return ("Sem limites de camada para propagar.", TINTA_FRACA)

    def _medir_faixa_aviso(self, W: float, prop: Optional[PropagacaoTensoes],
                           erro: Optional[str]) -> float:
        """
        Altura [px] necessária para os avisos fixos do topo, MEDIDA via
        `bbox()` dos textos reais — não estimada (a6, achado 7:
        `FAIXA_AVISO_ESPRAIAMENTO = 84.0` era um número mágico sem relação
        com a altura real do texto, que quebra por `width=`). Os itens de
        medição são criados fora da área visível e apagados antes do quadro
        real ser desenhado.
        """
        c = self.canvas
        largura_texto = max(W - 20, 160)
        y = 0.0
        itens = []
        for texto, fonte, _cor in self._linhas_banner_espraiamento(prop):
            item = c.create_text(-10_000, -10_000 + y, anchor="nw",
                                 font=fonte, text=texto, width=largura_texto)
            itens.append(item)
            bbox = c.bbox(item)
            altura = (bbox[3] - bbox[1]) if bbox else 12.0
            y += altura + 3.0
        for item in itens:
            c.delete(item)
        return max(y + 4.0, self.FAIXA_AVISO_MINIMA)

    def _espraiamento(self, m, px, ym, dim, hf, base, W, topo,
                      prop: Optional[PropagacaoTensoes],
                      erro: Optional[str],
                      corte_x0: float, corte_x1: float) -> None:
        """
        Corte em pirâmide/tronco: Δσ e a largura equivalente NAS INTERFACES
        de camada (q_i, a_eq,i/b_eq,i — REQ-UI-07, ruleset v7), alternativa
        ao bulbo contínuo de isovalores de `_bulbo()`.

        `prop` e `erro` vêm PRONTOS de `desenhar()` (uma só chamada ao
        núcleo por quadro — a mesma que já decidiu a semilargura do corte
        para o tronco não vazar do canvas, a6achado 6), não recalculados
        aqui.

        Fonte de dados: `PropagacaoTensoes` de `geotecnia.propagacao_em_
        profundidade` — [pratica: PC-BOUSSINESQ-NEWMARK-canto-retangulo] ou
        [pratica: PC-ESPRAIAMENTO-2V1H] conforme `self.fonte_espraiamento`.
        A cor de cada tronco usa a MESMA rampa de `momentos.cor_hex` já
        reaproveitada em `MapaMomentos`/`visual3d_*` — vermelho = mais Δσ, em
        toda a parte do app, não uma paleta nova.
        """
        c = self.canvas

        # REQ-UI-01/REQ-UI-02/REQ-UI-07(d)/(f) — bloco PERMANENTE (nunca só
        # em tooltip ou popup) enquanto este corte estiver ativo. A faixa foi
        # reservada em `desenhar()` com a MESMA sequência de linhas medida
        # por `_medir_faixa_aviso`; aqui elas se empilham por `bbox()`.
        faixa_aviso_y0 = self.TOPO_CABECALHO
        c.create_rectangle(0, faixa_aviso_y0, W, topo - 2, fill=AVISO_BG,
                           outline="")
        largura_texto = max(W - 20, 160)
        y = faixa_aviso_y0 + 4.0
        for texto, fonte, cor in self._linhas_banner_espraiamento(prop):
            item = c.create_text(10, y, anchor="nw", fill=cor, font=fonte,
                                 text=texto, width=largura_texto)
            bbox = c.bbox(item)
            y = (bbox[3] + 3.0) if bbox else y + 14.0

        eixo_val = "a" if self.direcao == "X" else "b"
        # REQ-UI-07(e): largura `None` (q_líq <= 0 → None em TODOS os pontos,
        # por construção de `geotecnia.largura_equivalente`) NUNCA vira
        # número — nem sequer um tronco é traçado nessa condição, para nunca
        # tropeçar em rotular a dimensão da sapata como largura calculada
        # (o antigo `... or dim`, a6/a2, achado E do ruleset v7).
        sem_largura_definida = self._sem_largura_definida(prop, eixo_val)

        if prop is None or not prop.camadas or sem_largura_definida:
            texto, cor = self._mensagem_indisponivel(prop, erro)
            c.create_text(px(0), (topo + base) / 2, fill=cor,
                          font=("Segoe UI", 10), text=texto,
                          width=max(W - 40, 160), justify="center")
            return

        def py(z_abaixo_base):
            return ym(hf + z_abaixo_base)

        def clampx(x_px: float) -> float:
            """Recorta a coordenada de pixel ao intervalo horizontal do
            corte (a6, achado 6) — mesmo com a semilargura ampliada em
            `desenhar()` para caber a_eq/b_eq no teto z_max, uma folga de
            arredondamento não deve deixar o tronco vazar do canvas."""
            return min(max(x_px, corte_x0), corte_x1)

        q_ref = max(prop.q_liquida, 1e-9)

        for indice, cam in enumerate(prop.camadas):
            pt_topo = prop.pontos[indice]
            pt_base = prop.pontos[indice + 1]
            larg_topo_val = getattr(pt_topo, f"largura_equivalente_{eixo_val}")
            larg_base_val = getattr(pt_base, f"largura_equivalente_{eixo_val}")
            # Geometria do polígono: se a largura de UM ponto específico vier
            # None num perfil onde os outros estão definidos (Δσ <= 0 muito
            # localizado — não é o caso geral de q_líq <= 0, já tratado
            # acima), cai para a largura do ponto vizinho válido, nunca para
            # `dim` da sapata.
            larg_topo = larg_topo_val if larg_topo_val is not None else (
                larg_base_val if larg_base_val is not None else dim)
            larg_base = larg_base_val if larg_base_val is not None else larg_topo
            y0, y1 = py(cam.z_topo), py(cam.z_base)
            if y0 > base:
                break
            y1 = min(y1, base)

            fracao = max(0.0, min(1.0, cam.delta_sigma_medio / q_ref))
            cor = cor_hex(fracao)
            c.create_polygon(
                clampx(px(-larg_topo / 2)), y0, clampx(px(larg_topo / 2)), y0,
                clampx(px(larg_base / 2)), y1, clampx(px(-larg_base / 2)), y1,
                fill=cor, outline="#f4f6f7", width=1)

            # setas de espraiamento: bordas inclinadas com seta apontando
            # para fora/baixo, no mesmo espírito das isolinhas de _bulbo().
            for sinal in (-1, 1):
                c.create_line(clampx(px(sinal * larg_topo / 2)), y0,
                              clampx(px(sinal * larg_base / 2)), y1,
                              fill="#f4f6f7", width=1.2, dash=(4, 2),
                              arrow="last", arrowshape=(7, 8, 3))

            c.create_line(clampx(px(-larg_base / 2)), y1,
                          clampx(px(larg_base / 2)), y1,
                          fill="#20272c", width=1)

        # REQ-UI-07(a)/(b): UM rótulo de tensão e UM de largura POR
        # INTERFACE — não por camada. A interface interna entre a camada i e
        # i+1 é COMPARTILHADA (`prop.pontos[i+1]` é ao mesmo tempo a base de
        # uma e o topo da seguinte): desenhar o ponto 0 uma vez ANTES do
        # laço e, dentro dele, só a base de cada camada, visita cada
        # interface exatamente uma vez (a6, achado 2).
        n_desenhadas = 0
        for cam in prop.camadas:
            if py(cam.z_topo) > base:
                break
            n_desenhadas += 1
        pontos_visiveis = prop.pontos[:n_desenhadas + 1] if n_desenhadas else ()
        for pt in pontos_visiveis:
            y_pt = min(py(pt.z), base)
            larg = getattr(pt, f"largura_equivalente_{eixo_val}")
            rotulo_l = (f"{eixo_val}_eq = {larg:.2f} m" if larg is not None
                       else f"{eixo_val}_eq = —")
            c.create_text(clampx(px(0)) - 4, y_pt, anchor="e", fill="#f4f6f7",
                          font=("Consolas", 7, "bold"),
                          text=f"q = {pt.delta_sigma:.1f} kPa")
            c.create_text(clampx(px(0)) + 4, y_pt, anchor="w", fill="#f4f6f7",
                          font=("Consolas", 7), text=rotulo_l)

        # Avisos extras específicos desta chamada (ex.: "pressão líquida
        # nula", "profundidade pedida excede o perfil"), diferentes dos já
        # promovidos à faixa fixa do topo (REQ-UI-01/02 e, sob 2V:1H, a
        # ressalva do método — a6, achado 8). Ancorado ABAIXO do maior
        # `bbox()` já desenhado no canvas (a6, achado 6/9: `base + 14` fixo
        # colidia com a coluna estratigráfica quando ela, ou o tronco
        # alargado, desciam mais que o previsto) — não numa constante.
        bbox_tudo = c.bbox("all")
        y_extra = max(base + 14.0, (bbox_tudo[3] + 6.0) if bbox_tudo else base + 14.0)
        for aviso in self._avisos_nao_promovidos(prop):
            item = c.create_text(10, y_extra, anchor="nw", fill=TINTA_FRACA,
                                 font=("Consolas", 7), text=aviso,
                                 width=max(W - 200, 120))
            bbox = c.bbox(item)
            y_extra = (bbox[3] + 4.0) if bbox else y_extra + 12.0

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
