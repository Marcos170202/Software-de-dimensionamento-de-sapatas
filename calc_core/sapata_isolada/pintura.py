"""
pintura.py
----------
Infraestrutura de desenho para os visualizadores.

Dois problemas de desempenho do canvas do Tk são tratados aqui:

1. Criar e destruir itens a cada quadro é caro. `PoolCanvas` cria os itens uma
   vez e, nos quadros seguintes, só atualiza coordenadas e cores, escondendo o
   excedente. Redesenhar passa a custar uma fração do que custava.

2. Isolinhas saem do marching squares como milhares de segmentos soltos.
   `encadear_segmentos` costura os que compartilham extremidade, transformando
   cada curva numa única polilinha — menos itens e traço contínuo.
"""
from __future__ import annotations

from typing import Sequence

# tolerância para considerar que duas pontas de segmento são o mesmo ponto
_TOL = 1e-7


class PoolCanvas:
    """
    Reaproveita itens de um `tkinter.Canvas` entre quadros.

    Uso:
        pool.iniciar()
        pool.poligono(pontos, preenchimento, contorno)
        pool.linha(x0, y0, x1, y1, cor, largura)
        pool.finalizar()          # esconde o que sobrou do quadro anterior
    """

    def __init__(self, canvas) -> None:
        self.canvas = canvas
        self._poligonos: list[int] = []
        self._linhas: list[int] = []
        self._textos: list[int] = []
        self._i_pol = self._i_lin = self._i_txt = 0

    # ------------------------------------------------------------------ ciclo
    def iniciar(self) -> None:
        self._i_pol = self._i_lin = self._i_txt = 0

    def finalizar(self) -> None:
        for lista, usados in ((self._poligonos, self._i_pol),
                              (self._linhas, self._i_lin),
                              (self._textos, self._i_txt)):
            for item in lista[usados:]:
                self.canvas.itemconfigure(item, state="hidden")

    def limpar(self) -> None:
        """Descarta tudo — usar só quando a cena muda de natureza."""
        self.canvas.delete("all")
        self._poligonos.clear()
        self._linhas.clear()
        self._textos.clear()
        self._i_pol = self._i_lin = self._i_txt = 0

    # -------------------------------------------------------------- desenho
    def poligono(self, pontos: Sequence[float], preenchimento: str,
                 contorno: str = "", largura: float = 1) -> None:
        c = self.canvas
        if self._i_pol < len(self._poligonos):
            item = self._poligonos[self._i_pol]
            c.coords(item, *pontos)
            c.itemconfigure(item, fill=preenchimento, outline=contorno,
                            width=largura, state="normal")
        else:
            item = c.create_polygon(*pontos, fill=preenchimento,
                                    outline=contorno, width=largura)
            self._poligonos.append(item)
        self._i_pol += 1

    def linha(self, x0: float, y0: float, x1: float, y1: float, cor: str,
              largura: float = 1, tracejado=None) -> None:
        self.polilinha([x0, y0, x1, y1], cor, largura, tracejado)

    def polilinha(self, pontos: Sequence[float], cor: str, largura: float = 1,
                  tracejado=None) -> None:
        c = self.canvas
        if len(pontos) < 4:
            return
        if self._i_lin < len(self._linhas):
            item = self._linhas[self._i_lin]
            c.coords(item, *pontos)
            c.itemconfigure(item, fill=cor, width=largura,
                            dash=tracejado or (), state="normal")
        else:
            item = c.create_line(*pontos, fill=cor, width=largura,
                                 dash=tracejado or ())
            self._linhas.append(item)
        self._i_lin += 1

    def texto(self, x: float, y: float, texto: str, cor: str, fonte,
              ancora: str = "center", angulo: float = 0.0) -> None:
        c = self.canvas
        if self._i_txt < len(self._textos):
            item = self._textos[self._i_txt]
            c.coords(item, x, y)
            c.itemconfigure(item, text=texto, fill=cor, font=fonte,
                            anchor=ancora, angle=angulo, state="normal")
        else:
            item = c.create_text(x, y, text=texto, fill=cor, font=fonte,
                                 anchor=ancora, angle=angulo)
            self._textos.append(item)
        self._i_txt += 1


# --------------------------------------------------------------------------- #
#  Isolinhas
# --------------------------------------------------------------------------- #
def encadear_segmentos(segmentos, tolerancia: float = 1e-6) -> list[list[tuple]]:
    """
    Costura segmentos soltos em polilinhas contínuas.

    Recebe [[(x0,y0),(x1,y1)], ...] e devolve [[(x,y), (x,y), ...], ...].
    Segmentos que não encontram vizinho viram polilinhas de dois pontos.
    """
    if not segmentos:
        return []

    def chave(p):
        return (round(p[0] / tolerancia), round(p[1] / tolerancia))

    pendentes: dict[tuple, list[int]] = {}
    for i, s in enumerate(segmentos):
        pendentes.setdefault(chave(s[0]), []).append(i)
        pendentes.setdefault(chave(s[1]), []).append(i)

    usados = [False] * len(segmentos)
    curvas: list[list[tuple]] = []

    def vizinho(k, atual):
        for j in pendentes.get(k, ()):
            if j != atual and not usados[j]:
                return j
        return None

    for i, s in enumerate(segmentos):
        if usados[i]:
            continue
        usados[i] = True
        curva = [s[0], s[1]]
        # cresce pela frente
        while True:
            j = vizinho(chave(curva[-1]), -1)
            if j is None:
                break
            usados[j] = True
            a, b = segmentos[j]
            curva.append(b if chave(a) == chave(curva[-1]) else a)
        # cresce por trás
        while True:
            j = vizinho(chave(curva[0]), -1)
            if j is None:
                break
            usados[j] = True
            a, b = segmentos[j]
            curva.insert(0, b if chave(a) == chave(curva[0]) else a)
        curvas.append(curva)
    return curvas


def faixas_por_linha(valores_linha: Sequence[float], limites: Sequence[float]
                     ) -> list[tuple[int, int, int]]:
    """
    Agrupa uma linha da grade em trechos de mesma faixa de valor.

    Devolve [(i_inicial, i_final_exclusivo, indice_da_faixa), ...]. Serve para
    desenhar um retângulo por trecho em vez de um por célula.
    """
    def faixa(v):
        for k, lim in enumerate(limites):
            if v < lim:
                return k
        return len(limites)

    trechos = []
    inicio = 0
    atual = faixa(valores_linha[0])
    for i in range(1, len(valores_linha)):
        f = faixa(valores_linha[i])
        if f != atual:
            trechos.append((inicio, i, atual))
            inicio, atual = i, f
    trechos.append((inicio, len(valores_linha), atual))
    return trechos
