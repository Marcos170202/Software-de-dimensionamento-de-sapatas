"""
momentos.py
-----------
Campo de momentos fletores em planta para a sapata isolada, no formato usado
para leitura por isovalores (mapa de cores + curvas de nível).

Modelo
------
A sapata rígida é lida como duas famílias de balanços engastados nas faces do
pilar. Para um ponto (x, y) da base, o momento por unidade de largura é o
momento da pressão do solo que atua entre a borda mais próxima e o ponto:

    x >= 0 :  m_x(x, y) = ∫[x .. a/2]  σ(ξ, y) · (ξ − x) dξ
    x <  0 :  m_x(x, y) = ∫[−a/2 .. x] σ(ξ, y) · (x − ξ) dξ

Como σ varia linearmente em planta (flexão oblíqua composta), a integral tem
forma fechada. Dentro da projeção do pilar o valor é mantido constante e igual
ao da face, que é a seção de referência da NBR 6118 (item 22.6.4.1): o campo
não deve sugerir armadura crescente sob o pilar.

Unidades: momentos em kN·m/m, tensões em kPa, comprimentos em m.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Sequence

from .acoes import TipoCombinacao, filtrar


# --------------------------------------------------------------------------- #
#  Núcleo compartilhado: plano de tensões e momento no balanço
#  Usado tanto pelo dimensionamento (sapata.py) quanto pelo mapa de isovalores,
#  para que os dois nunca divirjam.
# --------------------------------------------------------------------------- #
def plano_tensoes(N: float, Mx: float, My: float, a: float, b: float):
    """
    Devolve (σ_média, k_x, k_y) do plano σ(x, y) = σ_m + k_x·x + k_y·y [kPa].
    Tensões de tração são zeradas por quem consulta (o solo não traciona).
    """
    return N / (a * b), 12.0 * My / (b * a ** 3), 12.0 * Mx / (a * b ** 3)


def momento_unitario(N: float, Mx: float, My: float, a: float, b: float,
                     ap: float, bp: float, direcao: str) -> float:
    """
    Momento fletor por unidade de largura [kN·m/m] na face do pilar, na faixa
    de borda mais solicitada — seção de referência da NBR 6118, item 22.6.4.1.

    A pressão varia linearmente ao longo do eixo do balanço, com a coordenada
    transversal fixada na borda mais comprimida. Interpolar usando o vértice
    diagonal oposto subestimaria a pressão na face.
    """
    if N <= 0:
        return 0.0
    sm, kx, ky = plano_tensoes(N, Mx, My, a, b)

    def sigma(xi, eta):
        return max(0.0, sm + kx * xi + ky * eta)

    if direcao == "X":
        dim, dim_p, k_eixo, k_transv, dim_t = a, ap, kx, ky, b
    else:
        dim, dim_p, k_eixo, k_transv, dim_t = b, bp, ky, kx, a

    lado = 1.0 if k_eixo >= 0 else -1.0          # balanço mais comprimido
    transv = (1.0 if k_transv >= 0 else -1.0) * dim_t / 2.0
    borda, face = lado * dim / 2.0, lado * dim_p / 2.0
    L = abs(borda - face)
    if L <= 1e-9:
        return 0.0
    if direcao == "X":
        s_face, s_borda = sigma(face, transv), sigma(borda, transv)
    else:
        s_face, s_borda = sigma(transv, face), sigma(transv, borda)
    # ∫(s_face + k·t)·t dt de 0 a L, com t medido a partir da face
    return s_face * L ** 2 / 2.0 + (s_borda - s_face) * L ** 2 / 3.0


@dataclass
class CampoMomentos:
    """Grade de momentos em planta, para as duas direções de armadura."""

    x: list[float]                     # coordenadas da grade [m]
    y: list[float]
    mx: list[list[float]]              # mx[j][i] — arma a direção X [kN·m/m]
    my: list[list[float]]              # my[j][i] — arma a direção Y [kN·m/m]
    sigma: list[list[float]]           # pressão de cálculo no solo [kPa]
    combinacao: str
    a: float
    b: float
    ap: float
    bp: float
    sigma_max: float
    sigma_min: float
    parcial: bool                      # seção parcialmente comprimida
    md_projeto_x: float                # momento total adotado no cálculo [kN·m]
    md_projeto_y: float
    alertas: list[str] = field(default_factory=list)

    @property
    def mx_max(self) -> float:
        return max(max(linha) for linha in self.mx)

    @property
    def my_max(self) -> float:
        return max(max(linha) for linha in self.my)

    def faixa(self, direcao: str) -> list[list[float]]:
        return self.mx if direcao == "X" else self.my


def campo_momentos(sapata, res, nx: int = 61, ny: int = 61) -> CampoMomentos:
    """
    Monta o campo a partir da combinação última que produziu o maior momento
    de dimensionamento — a mesma que governou a armadura.
    """
    a, b = res.a, res.b
    ap, bp = sapata.pilar.ap, sapata.pilar.bp
    combs = filtrar(sapata.combinacoes, TipoCombinacao.ELU)

    # combinação governante: a de maior momento no balanço, como no cálculo
    def maior_momento(c):
        e = c.esforcos
        mx = e.Mx + e.Hy * res.h
        my = e.My + e.Hx * res.h
        return max(momento_unitario(e.N, mx, my, a, b, ap, bp, "X") * b,
                   momento_unitario(e.N, mx, my, a, b, ap, bp, "Y") * a)

    comb = max(combs, key=maior_momento)
    e = comb.esforcos
    N = e.N                                   # o peso próprio não flete a sapata
    Mx = e.Mx + e.Hy * res.h
    My = e.My + e.Hx * res.h
    A = a * b

    alertas: list[str] = []
    if N <= 0:
        alertas.append("Combinação governante sem compressão; campo não avaliado.")
        zeros = [[0.0] * nx for _ in range(ny)]
        return CampoMomentos([0.0], [0.0], zeros, zeros, zeros, comb.nome,
                             a, b, ap, bp, 0.0, 0.0, True, 0.0, 0.0, alertas)

    # σ(ξ, η) = N/A + kx·ξ + ky·η   (plano de tensões)
    kx = 12.0 * My / (b * a ** 3)
    ky = 12.0 * Mx / (a * b ** 3)
    s_med = N / A

    cantos = [s_med + kx * sx * a / 2 + ky * sy * b / 2
              for sx in (-1, 1) for sy in (-1, 1)]
    parcial = min(cantos) < 0.0
    if parcial:
        alertas.append(
            "Seção parcialmente comprimida: o campo usa o plano de tensões com "
            "as tensões de tração zeradas, o que é uma aproximação — o "
            "dimensionamento usa o diagrama equilibrado.")

    def sigma(xi: float, eta: float) -> float:
        return max(0.0, s_med + kx * xi + ky * eta)

    xs = [-a / 2 + a * i / (nx - 1) for i in range(nx)]
    ys = [-b / 2 + b * j / (ny - 1) for j in range(ny)]

    def momento_1d(pos: float, fixo: float, dim: float, dim_p: float,
                   eixo: str) -> float:
        """Momento do balanço até `pos`, mantido constante sob o pilar."""
        # a seção de referência é a face do pilar (NBR 6118, 22.6.4.1)
        limite = dim_p / 2.0
        p = math.copysign(max(abs(pos), limite), pos if pos != 0 else 1.0)
        borda = math.copysign(dim / 2.0, p)
        L = abs(borda - p)
        if L <= 1e-9:
            return 0.0
        if eixo == "X":
            s0, s1 = sigma(p, fixo), sigma(borda, fixo)
        else:
            s0, s1 = sigma(fixo, p), sigma(fixo, borda)
        # σ linear no trecho: ∫ (s0 + k·t)·t dt = s0·L²/2 + k·L³/3
        k = (s1 - s0) / L
        return s0 * L ** 2 / 2.0 + k * L ** 3 / 3.0

    mx = [[momento_1d(x, y, a, ap, "X") for x in xs] for y in ys]
    my = [[momento_1d(y, x, b, bp, "Y") for x in xs] for y in ys]
    sig = [[sigma(x, y) for x in xs] for y in ys]

    arm = {ar.direcao: ar.Md for ar in res.armaduras}
    return CampoMomentos(
        x=xs, y=ys, mx=mx, my=my, sigma=sig, combinacao=comb.nome,
        a=a, b=b, ap=ap, bp=bp,
        sigma_max=max(max(l) for l in sig), sigma_min=min(min(l) for l in sig),
        parcial=parcial,
        md_projeto_x=arm.get("X", 0.0), md_projeto_y=arm.get("Y", 0.0),
        alertas=alertas)


# --------------------------------------------------------------------------- #
#  Curvas de nível (marching squares)
# --------------------------------------------------------------------------- #
def curvas_nivel(xs: Sequence[float], ys: Sequence[float],
                 valores: Sequence[Sequence[float]],
                 nivel: float) -> list[list[tuple[float, float]]]:
    """
    Segmentos da isolinha de valor `nivel`, por marching squares.
    Devolve uma lista de segmentos [(x0,y0), (x1,y1)].
    """
    segmentos: list[list[tuple[float, float]]] = []

    def interp(p, q, vp, vq):
        if abs(vq - vp) < 1e-12:
            return p
        t = (nivel - vp) / (vq - vp)
        return (p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1]))

    for j in range(len(ys) - 1):
        for i in range(len(xs) - 1):
            p = [(xs[i], ys[j]), (xs[i + 1], ys[j]),
                 (xs[i + 1], ys[j + 1]), (xs[i], ys[j + 1])]
            v = [valores[j][i], valores[j][i + 1],
                 valores[j + 1][i + 1], valores[j + 1][i]]
            indice = sum((1 << k) for k in range(4) if v[k] >= nivel)
            if indice in (0, 15):
                continue
            # arestas cortadas: 0=(0,1) 1=(1,2) 2=(2,3) 3=(3,0)
            cortes = []
            for k in range(4):
                k2 = (k + 1) % 4
                if (v[k] >= nivel) != (v[k2] >= nivel):
                    cortes.append(interp(p[k], p[k2], v[k], v[k2]))
            for k in range(0, len(cortes) - 1, 2):
                segmentos.append([cortes[k], cortes[k + 1]])
    return segmentos


def niveis_uteis(maximo: float, n: int = 8) -> list[float]:
    """Escolhe níveis 'redondos' para as isolinhas."""
    if maximo <= 0:
        return []
    passo_bruto = maximo / n
    magnitude = 10 ** math.floor(math.log10(passo_bruto))
    for mult in (1, 2, 2.5, 5, 10):
        passo = mult * magnitude
        if maximo / passo <= n + 1:
            break
    k = 1
    saida = []
    while k * passo < maximo * 0.999:
        saida.append(k * passo)
        k += 1
    return saida


# --------------------------------------------------------------------------- #
#  Rampa de cores (azul frio -> vermelho quente, como nos mapas de isovalores)
# --------------------------------------------------------------------------- #
_RAMPA = [
    (0.00, (0.94, 0.96, 0.97)),
    (0.15, (0.66, 0.83, 0.89)),
    (0.35, (0.40, 0.69, 0.78)),
    (0.55, (0.55, 0.76, 0.51)),
    (0.72, (0.94, 0.83, 0.36)),
    (0.87, (0.90, 0.55, 0.24)),
    (1.00, (0.75, 0.20, 0.18)),
]


def cor_isovalor(t: float) -> tuple[float, float, float]:
    """Cor normalizada (0..1) para a fração t do máximo."""
    t = max(0.0, min(1.0, t))
    for (t0, c0), (t1, c1) in zip(_RAMPA, _RAMPA[1:]):
        if t0 <= t <= t1:
            f = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            return tuple(c0[k] + f * (c1[k] - c0[k]) for k in range(3))
    return _RAMPA[-1][1]


def cor_hex(t: float) -> str:
    r, g, b = cor_isovalor(t)
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"


# --------------------------------------------------------------------------- #
#  Campo vindo da grelha discretizada
# --------------------------------------------------------------------------- #
def campo_de_grelha(g, md_x: float, md_y: float,
                    combinacao: str) -> CampoMomentos:
    """
    Converte o resultado da grelha num CampoMomentos, para alimentar os mesmos
    desenhos usados pelo campo analítico.

    Dentro da projeção do pilar o valor é substituído pelo da face, como no
    campo analítico: ali a grelha tem a singularidade da carga concentrada e o
    pico não converge com o refinamento.
    """
    xs, ys = g.x, g.y
    ap, bp = g.ap, g.bp

    def clampar(campo, coords, meia, ao_longo_de_x: bool):
        saida = [linha[:] for linha in campo]
        for j in range(len(ys)):
            for i in range(len(xs)):
                c = xs[i] if ao_longo_de_x else ys[j]
                if abs(c) >= meia:
                    continue
                # valor do nó imediatamente fora da projeção, no mesmo alinhamento
                if ao_longo_de_x:
                    fora = [k for k in range(len(xs)) if abs(xs[k]) >= meia]
                    k = min(fora, key=lambda k: abs(abs(xs[k]) - meia))
                    saida[j][i] = campo[j][k]
                else:
                    fora = [k for k in range(len(ys)) if abs(ys[k]) >= meia]
                    k = min(fora, key=lambda k: abs(abs(ys[k]) - meia))
                    saida[j][i] = campo[k][i]
        return saida

    mx = clampar(g.mx, xs, ap / 2.0, True)
    my = clampar(g.my, ys, bp / 2.0, False)
    a = xs[-1] - xs[0]
    b = ys[-1] - ys[0]
    return CampoMomentos(
        x=xs, y=ys, mx=mx, my=my, sigma=g.pressao, combinacao=combinacao,
        a=a, b=b, ap=ap, bp=bp,
        sigma_max=g.p_max, sigma_min=min(min(l) for l in g.pressao),
        parcial=min(min(l) for l in g.pressao) < 0.0,
        md_projeto_x=md_x, md_projeto_y=md_y,
        alertas=list(g.alertas) + ["Campo obtido da grelha discretizada sobre "
                                   "apoios elásticos."])
