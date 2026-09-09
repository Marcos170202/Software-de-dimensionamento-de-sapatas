"""
pdf.py
------
Gerador de PDF vetorial mínimo, escrito do zero para não introduzir
dependência externa no pacote.

Cobre o que uma prancha de projeto precisa: linhas, polígonos preenchidos,
textos com as fontes padrão do PDF (Helvetica e Courier, que não precisam ser
embutidas) e traço tracejado.

Sistema de coordenadas: milímetros, origem no canto inferior esquerdo,
eixo y para cima (igual ao PDF nativo).
"""
from __future__ import annotations

import zlib
from typing import Iterable, Optional, Sequence

MM = 72.0 / 25.4          # milímetro -> ponto PostScript

A4_RETRATO = (210.0, 297.0)
A4_PAISAGEM = (297.0, 210.0)
A3_PAISAGEM = (420.0, 297.0)

# Larguras aproximadas de Helvetica, em milésimos de em, por faixa de caractere.
# Suficiente para centralizar rótulos; não pretende ser métrica exata.
_ESTREITOS = "iljI.,:;'|!()[]{}/\\ft"
_LARGOS = "mMWO@%"

# Caracteres fora do cp1252 que existem na fonte Symbol (base 14 do PDF).
# Chave: caractere Unicode -> código na codificação Symbol.
SIMBOLOS = {
    "α": "a", "β": "b", "γ": "g", "δ": "d", "Δ": "D", "ε": "e", "ζ": "z",
    "η": "h", "θ": "q", "κ": "k", "λ": "l", "μ": "m", "ν": "n", "ξ": "x",
    "π": "p", "ρ": "r", "σ": "s", "Σ": "S", "τ": "t", "υ": "u", "φ": "f",
    "ϕ": "j", "χ": "c", "ψ": "y", "ω": "w", "Ω": "W", "Γ": "G", "Θ": "Q",
    "Λ": "L", "Ξ": "X", "Π": "P", "Φ": "F", "Ψ": "Y",
    # Códigos da fonte Symbol escritos como o caractere cp1252 de mesmo byte,
    # já que o fluxo de conteúdo é gravado nessa codificação.
    "≤": "\u00a3", "≥": "\u00b3", "≠": "\u00b9", "≈": "\u00bb",
    "∞": "\u00a5", "∑": "\u00e5", "√": "\u00d6", "∫": "\u00f2",
}

# Caracteres sem equivalente em cp1252 nem em Symbol: trocados por ASCII.
SUBSTITUICOES = {
    "\u2212": "-", "\u2010": "-", "\u2011": "-", "\u2026": "...",
    "\u00a0": " ", "\u2033": '"', "\u2032": "'",
}


def largura_texto(texto: str, tamanho: float, mono: bool = False) -> float:
    """Largura estimada do texto [mm]."""
    if mono:
        return len(texto) * tamanho * 0.600 / MM
    total = 0.0
    for c in texto:
        if c in SIMBOLOS:
            total += 600
            continue
        if c == ' ':
            total += 278
        elif c in _ESTREITOS:
            total += 250
        elif c in _LARGOS:
            total += 850
        elif c.isupper():
            total += 667
        else:
            total += 545
    return total / 1000.0 * tamanho / MM


def _escapar(txt: str) -> str:
    """Escapa parênteses e barras para a sintaxe de string do PDF."""
    return (txt.replace("\\", r"\\\\").replace("(", r"\(").replace(")", r"\)"))


class PDF:
    """Documento PDF de páginas com conteúdo vetorial."""

    def __init__(self, tamanho: tuple[float, float] = A3_PAISAGEM) -> None:
        self.largura, self.altura = tamanho
        self._paginas: list[list[str]] = []
        self._atual: Optional[list[str]] = None
        self.nova_pagina()

    # ------------------------------------------------------------------ páginas
    def nova_pagina(self) -> None:
        self._atual = []
        self._paginas.append(self._atual)

    @property
    def n_paginas(self) -> int:
        return len(self._paginas)

    # ------------------------------------------------------------- primitivas
    def _cor(self, c: Sequence[float], preenche: bool) -> str:
        op = "rg" if preenche else "RG"
        return f"{c[0]:.3f} {c[1]:.3f} {c[2]:.3f} {op}"

    def linha(self, x0: float, y0: float, x1: float, y1: float,
              espessura: float = 0.20, cor: Sequence[float] = (0, 0, 0),
              tracejado: Optional[Sequence[float]] = None) -> None:
        d = ("[" + " ".join(f"{v * MM:.2f}" for v in tracejado) + "] 0 d"
             if tracejado else "[] 0 d")
        self._atual.append(
            f"q {self._cor(cor, False)} {espessura * MM:.2f} w {d} "
            f"{x0 * MM:.2f} {y0 * MM:.2f} m {x1 * MM:.2f} {y1 * MM:.2f} l S Q")

    def polilinha(self, pts: Sequence[Sequence[float]], espessura: float = 0.20,
                  cor: Sequence[float] = (0, 0, 0),
                  tracejado: Optional[Sequence[float]] = None,
                  fechar: bool = False) -> None:
        if len(pts) < 2:
            return
        d = ("[" + " ".join(f"{v * MM:.2f}" for v in tracejado) + "] 0 d"
             if tracejado else "[] 0 d")
        c = [f"q {self._cor(cor, False)} {espessura * MM:.2f} w {d}",
             f"{pts[0][0] * MM:.2f} {pts[0][1] * MM:.2f} m"]
        c += [f"{p[0] * MM:.2f} {p[1] * MM:.2f} l" for p in pts[1:]]
        if fechar:
            c.append("h")
        c.append("S Q")
        self._atual.append(" ".join(c))

    def poligono(self, pts: Sequence[Sequence[float]],
                 preenchimento: Optional[Sequence[float]] = None,
                 contorno: Optional[Sequence[float]] = (0, 0, 0),
                 espessura: float = 0.20) -> None:
        if len(pts) < 3:
            return
        c = ["q"]
        if preenchimento is not None:
            c.append(self._cor(preenchimento, True))
        if contorno is not None:
            c.append(self._cor(contorno, False))
            c.append(f"{espessura * MM:.2f} w")
        c.append(f"{pts[0][0] * MM:.2f} {pts[0][1] * MM:.2f} m")
        c += [f"{p[0] * MM:.2f} {p[1] * MM:.2f} l" for p in pts[1:]]
        c.append("h")
        if preenchimento is not None and contorno is not None:
            c.append("B")
        elif preenchimento is not None:
            c.append("f")
        else:
            c.append("S")
        c.append("Q")
        self._atual.append(" ".join(c))

    def retangulo(self, x: float, y: float, larg: float, alt: float,
                  preenchimento: Optional[Sequence[float]] = None,
                  contorno: Optional[Sequence[float]] = (0, 0, 0),
                  espessura: float = 0.20) -> None:
        self.poligono([(x, y), (x + larg, y), (x + larg, y + alt), (x, y + alt)],
                      preenchimento, contorno, espessura)

    def circulo(self, cx: float, cy: float, raio: float,
                preenchimento: Optional[Sequence[float]] = None,
                contorno: Optional[Sequence[float]] = (0, 0, 0),
                espessura: float = 0.20) -> None:
        k = 0.5523 * raio
        p = [(cx + raio, cy), (cx + raio, cy + k), (cx + k, cy + raio), (cx, cy + raio),
             (cx - k, cy + raio), (cx - raio, cy + k), (cx - raio, cy),
             (cx - raio, cy - k), (cx - k, cy - raio), (cx, cy - raio),
             (cx + k, cy - raio), (cx + raio, cy - k), (cx + raio, cy)]
        c = ["q"]
        if preenchimento is not None:
            c.append(self._cor(preenchimento, True))
        if contorno is not None:
            c.append(self._cor(contorno, False))
            c.append(f"{espessura * MM:.2f} w")
        c.append(f"{p[0][0] * MM:.2f} {p[0][1] * MM:.2f} m")
        for i in range(1, 13, 3):
            a, b, d = p[i], p[i + 1], p[i + 2]
            c.append(f"{a[0]*MM:.2f} {a[1]*MM:.2f} {b[0]*MM:.2f} {b[1]*MM:.2f} "
                     f"{d[0]*MM:.2f} {d[1]*MM:.2f} c")
        c.append("B" if (preenchimento is not None and contorno is not None)
                 else ("f" if preenchimento is not None else "S"))
        c.append("Q")
        self._atual.append(" ".join(c))

    # ------------------------------------------------------------------ texto
    def texto(self, x: float, y: float, txt: str, tamanho: float = 8.0,
              cor: Sequence[float] = (0, 0, 0), negrito: bool = False,
              mono: bool = False, ancora: str = "sw",
              rotacao: float = 0.0) -> None:
        """
        Escreve texto. Caracteres gregos e matemáticos ausentes do cp1252 são
        emitidos automaticamente na fonte Symbol, intercalados no mesmo Tj.

        ancora: 'sw' (padrão), 'center', 'se'. rotacao em graus, anti-horário.
        """
        for de, para in SUBSTITUICOES.items():
            if de in txt:
                txt = txt.replace(de, para)
        fonte = "F3" if mono else ("F2" if negrito else "F1")
        larg = largura_texto(txt, tamanho, mono)
        dx = {"sw": 0.0, "center": -larg / 2.0, "se": -larg}.get(ancora, 0.0)

        # quebra em trechos (fonte normal / Symbol)
        trechos: list[tuple[str, str]] = []
        atual, em_simbolo = "", False
        for c in txt:
            simbolo = c in SIMBOLOS
            if simbolo != em_simbolo and atual:
                trechos.append((atual, "S" if em_simbolo else "N"))
                atual = ""
            em_simbolo = simbolo
            atual += SIMBOLOS[c] if simbolo else c
        if atual:
            trechos.append((atual, "S" if em_simbolo else "N"))

        corpo = []
        for conteudo, tipo in trechos:
            f = "F4" if tipo == "S" else fonte
            corpo.append(f"/{f} {tamanho:.2f} Tf ({_escapar(conteudo)}) Tj")
        miolo = " ".join(corpo)

        if abs(rotacao) < 1e-9:
            self._atual.append(
                f"q BT {self._cor(cor, True)} "
                f"{(x + dx) * MM:.2f} {y * MM:.2f} Td {miolo} ET Q")
        else:
            import math
            r = math.radians(rotacao)
            co, si = math.cos(r), math.sin(r)
            self._atual.append(
                f"q BT {self._cor(cor, True)} "
                f"{co:.5f} {si:.5f} {-si:.5f} {co:.5f} "
                f"{(x + dx * co) * MM:.2f} {(y + dx * si) * MM:.2f} Tm {miolo} ET Q")

    # ------------------------------------------------------------------ saída
    def salvar(self, caminho: str) -> None:
        objetos: list[bytes] = []

        def add(corpo: bytes) -> int:
            objetos.append(corpo)
            return len(objetos)          # número do objeto (1-based)

        n_pag = len(self._paginas)
        # objetos: 1 catálogo, 2 páginas, 3..5 fontes, depois pares página/conteúdo
        cat, pags = 1, 2
        f1, f2, f3, f4 = 3, 4, 5, 6
        primeiro = 7
        ids_pagina = [primeiro + 2 * i for i in range(n_pag)]

        add(f"<< /Type /Catalog /Pages {pags} 0 R >>".encode())
        kids = " ".join(f"{i} 0 R" for i in ids_pagina)
        add(f"<< /Type /Pages /Count {n_pag} /Kids [{kids}] >>".encode())
        for nome in ("Helvetica", "Helvetica-Bold", "Courier"):
            add(f"<< /Type /Font /Subtype /Type1 /BaseFont /{nome} "
                f"/Encoding /WinAnsiEncoding >>".encode())
        # Symbol usa a própria codificação (não aceita WinAnsiEncoding)
        add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Symbol >>")

        cx = self.largura * MM
        cy = self.altura * MM
        for i, conteudo in enumerate(self._paginas):
            fluxo = zlib.compress("\n".join(conteudo).encode("cp1252", "replace"))
            id_conteudo = ids_pagina[i] + 1
            add(f"<< /Type /Page /Parent {pags} 0 R /MediaBox [0 0 {cx:.2f} {cy:.2f}] "
                f"/Resources << /Font << /F1 {f1} 0 R /F2 {f2} 0 R /F3 {f3} 0 R "
                f"/F4 {f4} 0 R >> >> "
                f"/Contents {id_conteudo} 0 R >>".encode())
            add(b"<< /Length " + str(len(fluxo)).encode() + b" /Filter /FlateDecode >>\n"
                b"stream\n" + fluxo + b"\nendstream")

        saida = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        deslocamentos = [0]
        for numero, corpo in enumerate(objetos, start=1):
            deslocamentos.append(len(saida))
            saida += f"{numero} 0 obj\n".encode() + corpo + b"\nendobj\n"

        inicio_xref = len(saida)
        saida += f"xref\n0 {len(objetos) + 1}\n".encode()
        saida += b"0000000000 65535 f \n"
        for d in deslocamentos[1:]:
            saida += f"{d:010d} 00000 n \n".encode()
        saida += (f"trailer\n<< /Size {len(objetos) + 1} /Root {cat} 0 R >>\n"
                  f"startxref\n{inicio_xref}\n%%EOF\n").encode()

        with open(caminho, "wb") as f:
            f.write(bytes(saida))
