#!/usr/bin/env python3
"""Decodifica textos de PDFs da ABNT com subset de fonte de CMap deslocado.

Os PDFs da ABNT frequentemente embutem subsets de fonte cujo CMap desloca os
code points. O texto extraído sai como:

    7RGRV RV GLUHLWRV UHVHUYDGRV

em vez de "Todos os direitos reservados".

Deslocamentos validados nos arquivos da NBR 6118:2023:
  - fonte A: +29 no code point (faixa <= 0x60), +30 acima, tabela MacRoman
  - fonte B: -29 / -30, mesma lógica espelhada
NBR 6122:2022 e NBR 6123:2023 já vêm em UTF-8 limpo — a detecção deixa passar.

A detecção é feita LINHA A LINHA porque uma mesma página costuma misturar as
duas fontes (corpo de texto e sumário/títulos).

Uso:
    python tools/decodificar_nbr.py refs/NBR_6118.pdf > kb/raw/nbr6118.txt
"""
import sys

LIGADURAS = {"›": "fi", "‹": "fl"}

# marcadores de português para pontuar a hipótese vencedora
MARCADORES = (" de ", " da ", " do ", " para ", " que ", " com ",
              "ção", " ser ", " em ", " os ", " as ", " não ")


def _deslocar(texto: str, k: int) -> str:
    saida = []
    for ch in texto:
        try:
            b = ch.encode("mac_roman")[0]
        except Exception:
            saida.append(ch)
            continue
        # a faixa acima de 0x60 carrega um off-by-one no subset
        delta = k if b <= 0x60 else k + (1 if k > 0 else -1)
        n = b + delta
        if 0 < n < 256:
            try:
                saida.append(bytes([n]).decode("mac_roman"))
            except Exception:
                saida.append(ch)
        else:
            saida.append(ch)
    return "".join(saida)


def _pontuar(texto: str) -> int:
    t = texto.lower()
    return sum(t.count(m) for m in MARCADORES)


def decodificar_linha(linha: str) -> str:
    candidatos = [linha, _deslocar(linha, 29), _deslocar(linha, -29)]
    melhor = max(candidatos, key=_pontuar)
    if melhor is candidatos[0]:
        return linha  # já estava limpa
    for k, v in LIGADURAS.items():
        melhor = melhor.replace(k, v)
    return melhor.replace("\x03", " ").replace("=", " ")


def decodificar(texto: str) -> str:
    return "\n".join(decodificar_linha(l) for l in texto.splitlines())


def extrair_pdf(caminho: str) -> str:
    """Extrai o PDF com decodificação POR SPAN (caminho correto).

    Uma mesma linha da NBR 6118 mistura as duas fontes: corpo de texto numa,
    numeração e pontos de preenchimento do sumário na outra. Decidir o
    deslocamento por linha deixa resíduo garantido. Com pymupdf dá para ler o
    nome da fonte de cada span e decidir span a span.

    Sem pymupdf, cai para o modo linha — que é aproximado. Nesse caso o A1 deve
    tratar o resultado como suspeito e conferir o diagnóstico.
    """
    try:
        import fitz  # pymupdf
    except ImportError:
        with open(caminho, encoding="utf-8", errors="replace") as f:
            return decodificar(f.read())

    doc = fitz.open(caminho)
    paginas = []
    for pagina in doc:
        linhas = []
        for bloco in pagina.get_text("dict")["blocks"]:
            for linha in bloco.get("lines", []):
                partes = [decodificar_span(s["text"], s["font"])
                          for s in linha.get("spans", [])]
                linhas.append("".join(partes))
        paginas.append("\n".join(linhas))
    return "\n".join(paginas)


# cache de deslocamento por nome de fonte: descoberto uma vez, reusado sempre
_CACHE_FONTE: dict = {}


def decodificar_span(texto: str, fonte: str) -> str:
    """Decide o deslocamento pelo nome da fonte, não pelo conteúdo do span.

    Spans curtos ("19.5.1") não têm marcador português suficiente para a
    heurística acertar. A fonte, sim, é estável na página inteira.
    """
    if fonte not in _CACHE_FONTE:
        _CACHE_FONTE[fonte] = None  # descoberto na primeira amostra longa
    k = _CACHE_FONTE[fonte]
    if k is None and len(texto) > 40:
        k = max((0, 29, -29),
                key=lambda kk: _pontuar(texto if kk == 0 else _deslocar(texto, kk)))
        _CACHE_FONTE[fonte] = k
    if not k:
        return texto
    saida = _deslocar(texto, k)
    for a, b in LIGADURAS.items():
        saida = saida.replace(a, b)
    return saida.replace("\x03", " ")


def diagnosticar(texto: str) -> dict:
    """Relata se sobrou mojibake — A1 deve PARAR se sobrar."""
    linhas = texto.splitlines()
    suspeitas = [l for l in linhas
                 if len(l) > 20 and _pontuar(l) == 0 and any(c.isalpha() for c in l)]
    return {"linhas": len(linhas), "suspeitas": len(suspeitas),
            "amostra": suspeitas[:5]}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("uso: decodificar_nbr.py <arquivo.pdf>")
    saida = extrair_pdf(sys.argv[1])
    diag = diagnosticar(saida)
    print(saida)
    print(f"\n--- diagnostico: {diag['linhas']} linhas, "
          f"{diag['suspeitas']} suspeitas de mojibake residual ---",
          file=sys.stderr)
