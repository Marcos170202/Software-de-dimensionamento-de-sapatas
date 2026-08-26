"""
grelha.py
---------
Discretização da sapata como GRELHA sobre apoios elásticos.

O modelo anterior (`rigidez.py`) resolvia duas faixas independentes em X e Y.
Isso serve para comparar distribuições, mas ignora que as faixas dividem os
mesmos nós: o que uma recebe, a outra deixa de receber, e o giro de uma vira
torção na outra. A grelha resolve as duas direções num sistema só.

Modelo
------
Malha de barras ortogonais no plano médio da sapata. Cada nó tem 3 graus de
liberdade:

    w    deslocamento vertical
    tx   giro em torno de X  (adotado como a inclinação dw/dy)
    ty   giro em torno de Y  (adotado como a inclinação dw/dx)

Cada barra contribui com flexão (viga de Hermite) na direção em que corre e com
torção na direção transversal. As propriedades seguem a analogia de grelha para
lajes (Hambly):

    I = b · h³ / 12          J = b · h³ / 6          G = E / (2(1+ν))

Sob cada nó há uma mola de Winkler com rigidez k_v vezes a área tributária. As
extremidades são livres: são as molas que equilibram o sistema.

A altura da sapata varia elemento a elemento — h sob o pilar, h0 na borda —
como no tronco real.

Referências: Hambly, "Bridge Deck Behaviour" (analogia de grelha);
Hetényi (1946); ABNT NBR 6118:2023, item 22.6.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional


# =========================================================================== #
#  Álgebra: matriz simétrica em banda
# =========================================================================== #
class MatrizBanda:
    """
    Armazenamento em banda superior de uma matriz simétrica.

    `u[i][j - i]` guarda o termo (i, j) para j entre i e i + semibanda. Numa
    grelha, a banda vale cerca de 3·(nx+1), o que reduz a fatoração de O(n³)
    para O(n·b²) — a diferença entre segundos e minutos em Python puro.
    """

    def __init__(self, n: int, semibanda: int) -> None:
        self.n = n
        self.b = semibanda
        self.u = [[0.0] * (semibanda + 1) for _ in range(n)]

    def somar(self, i: int, j: int, valor: float) -> None:
        """
        Soma no termo (i, j). Como só o triângulo superior é guardado, cada par
        deve ser informado UMA vez — enviar (i,j) e (j,i) dobraria o valor.
        """
        if j < i:
            i, j = j, i
        d = j - i
        if d > self.b:
            raise ValueError(
                f"Termo ({i}, {j}) fora da banda ({d} > {self.b}): a numeração "
                "dos nós ou a semibanda estão inconsistentes.")
        self.u[i][d] += valor

    def resolver(self, f: list[float]) -> list[float]:
        """Cholesky em banda, seguido de substituições."""
        n, b, u = self.n, self.b, self.u
        for i in range(n):
            for j in range(i, min(i + b, n - 1) + 1):
                s = u[i][j - i]
                k0 = max(0, i - b, j - b)
                for k in range(k0, i):
                    s -= u[k][i - k] * u[k][j - k]
                if j == i:
                    if s <= 1e-12:
                        raise ValueError(
                            "Matriz da grelha não é positiva definida: reveja "
                            "k_v, a rigidez da peça ou o refinamento.")
                    u[i][0] = math.sqrt(s)
                else:
                    u[i][j - i] = s / u[i][0]

        y = [0.0] * n
        for i in range(n):
            s = f[i]
            for k in range(max(0, i - b), i):
                s -= u[k][i - k] * y[k]
            y[i] = s / u[i][0]

        x = [0.0] * n
        for i in range(n - 1, -1, -1):
            s = y[i]
            for k in range(i + 1, min(i + b, n - 1) + 1):
                s -= u[i][k - i] * x[k]
            x[i] = s / u[i][0]
        return x


# =========================================================================== #
#  Resultado
# =========================================================================== #
@dataclass
class ResultadoGrelha:
    """Campos nodais da grelha, em coordenadas centradas na sapata."""

    x: list[float]                    # nós em X [m]
    y: list[float]                    # nós em Y [m]
    w: list[list[float]]              # recalque w[j][i] [m]
    pressao: list[list[float]]        # p = k_v·w [kPa]
    mx: list[list[float]]             # momento que arma X [kN·m/m]
    my: list[list[float]]             # momento que arma Y [kN·m/m]
    kv: float
    n_gl: int
    equilibrio: float                 # resultante das molas / carga aplicada
    p_max: float = 0.0
    mx_max: float = 0.0          # pico no eixo — sensível ao refinamento
    my_max: float = 0.0
    mx_face: float = 0.0         # na face do pilar — valor de dimensionamento
    my_face: float = 0.0
    ap: float = 0.0
    bp: float = 0.0
    alertas: list[str] = field(default_factory=list)

    def faixa(self, direcao: str) -> list[list[float]]:
        return self.mx if direcao == "X" else self.my


# =========================================================================== #
#  Montagem e solução
# =========================================================================== #
def resolver_grelha(N: float, Mx: float, My: float, a: float, b: float,
                    ap: float, bp: float, h: float, h0: float,
                    Ecs_MPa: float, kv: float, nu: float = 0.20,
                    divisoes: int = 14) -> ResultadoGrelha:
    """
    Resolve a sapata como grelha sobre base elástica.

    N   [kN]    carga vertical do pilar
    Mx  [kN·m]  momento em torno de X (excentricidade em Y)
    My  [kN·m]  momento em torno de Y (excentricidade em X)
    divisoes    número de elementos por direção (par, para haver nó no eixo)
    """
    nx = ny = max(6, int(divisoes) + (int(divisoes) % 2))
    dx, dy = a / nx, b / ny
    xs = [-a / 2 + i * dx for i in range(nx + 1)]
    ys = [-b / 2 + j * dy for j in range(ny + 1)]
    E = Ecs_MPa * 1000.0                       # kPa
    G = E / (2.0 * (1.0 + nu))

    def no(i: int, j: int) -> int:
        return j * (nx + 1) + i

    def gl(i: int, j: int, k: int) -> int:
        return 3 * no(i, j) + k                 # k: 0=w, 1=tx, 2=ty

    n_gl = 3 * (nx + 1) * (ny + 1)
    semibanda = 3 * (nx + 1) + 2
    K = MatrizBanda(n_gl, semibanda)
    F = [0.0] * n_gl

    def altura(xm: float, ym: float) -> float:
        """h sob a projeção do pilar, decaindo linearmente até h0 na borda."""
        sx = max(0.0, (abs(xm) - ap / 2) / max(a / 2 - ap / 2, 1e-9))
        sy = max(0.0, (abs(ym) - bp / 2) / max(b / 2 - bp / 2, 1e-9))
        t = min(1.0, max(sx, sy))
        return h + (h0 - h) * t

    # ------------------------------------------------------------- barras
    def montar_barra(no1, no2, L, larg, he, flex_k, tors_k):
        """flex_k = índice do gl de rotação de flexão; tors_k o de torção."""
        I = larg * he ** 3 / 12.0
        J = larg * he ** 3 / 6.0
        c = E * I / L ** 3
        gls = [3 * no1, 3 * no1 + flex_k, 3 * no2, 3 * no2 + flex_k]
        ke = [[12 * c, 6 * L * c, -12 * c, 6 * L * c],
              [6 * L * c, 4 * L * L * c, -6 * L * c, 2 * L * L * c],
              [-12 * c, -6 * L * c, 12 * c, -6 * L * c],
              [6 * L * c, 2 * L * L * c, -6 * L * c, 4 * L * L * c]]
        # apenas o triângulo superior do elemento: a matriz é simétrica e o
        # armazenamento em banda já representa os dois lados
        for p in range(4):
            for q in range(p, 4):
                K.somar(gls[p], gls[q], ke[p][q])
        t = G * J / L
        g1, g2 = 3 * no1 + tors_k, 3 * no2 + tors_k
        K.somar(g1, g1, t)
        K.somar(g2, g2, t)
        K.somar(g1, g2, -t)

    for j in range(ny + 1):
        for i in range(nx):
            he = altura((xs[i] + xs[i + 1]) / 2.0, ys[j])
            larg = dy * (0.5 if j in (0, ny) else 1.0)
            montar_barra(no(i, j), no(i + 1, j), dx, larg, he, 2, 1)
    for i in range(nx + 1):
        for j in range(ny):
            he = altura(xs[i], (ys[j] + ys[j + 1]) / 2.0)
            larg = dx * (0.5 if i in (0, nx) else 1.0)
            montar_barra(no(i, j), no(i, j + 1), dy, larg, he, 1, 2)

    # -------------------------------------------------------------- molas
    for j in range(ny + 1):
        for i in range(nx + 1):
            area = dx * dy * (0.5 if i in (0, nx) else 1.0) \
                           * (0.5 if j in (0, ny) else 1.0)
            K.somar(gl(i, j, 0), gl(i, j, 0), kv * area)

    # -------------------------------------------------- carga do pilar
    # Distribuída na projeção do pilar pela área de sobreposição de cada célula,
    # para a resultante fechar com N mesmo quando o pilar não é múltiplo da malha.
    def sobreposicao(c0, c1, lim):
        return max(0.0, min(c1, lim) - max(c0, -lim))

    total_area = 0.0
    pesos = {}
    for j in range(ny):
        for i in range(nx):
            sx = sobreposicao(xs[i], xs[i + 1], ap / 2)
            sy = sobreposicao(ys[j], ys[j + 1], bp / 2)
            if sx <= 0 or sy <= 0:
                continue
            pesos[(i, j)] = sx * sy
            total_area += sx * sy
    if total_area <= 0:                     # pilar menor que uma célula
        i0, j0 = nx // 2, ny // 2
        pesos[(i0, j0)] = 1.0
        total_area = 1.0

    for (i, j), peso in pesos.items():
        parcela = N * peso / total_area
        for (ii, jj) in ((i, j), (i + 1, j), (i, j + 1), (i + 1, j + 1)):
            F[gl(ii, jj, 0)] += parcela / 4.0

    # momentos do pilar, espalhados nos nós da sua projeção
    nos_pilar = sorted({(ii, jj) for (i, j) in pesos
                        for (ii, jj) in ((i, j), (i + 1, j),
                                         (i, j + 1), (i + 1, j + 1))})
    if nos_pilar:
        for (i, j) in nos_pilar:
            F[gl(i, j, 1)] += Mx / len(nos_pilar)
            F[gl(i, j, 2)] += My / len(nos_pilar)

    u = K.resolver(F)

    # ------------------------------------------------------- pós-processo
    w = [[u[gl(i, j, 0)] for i in range(nx + 1)] for j in range(ny + 1)]
    tx = [[u[gl(i, j, 1)] for i in range(nx + 1)] for j in range(ny + 1)]
    ty = [[u[gl(i, j, 2)] for i in range(nx + 1)] for j in range(ny + 1)]
    pressao = [[kv * w[j][i] for i in range(nx + 1)] for j in range(ny + 1)]

    def momentos(direcao: str):
        """Momento por unidade de largura, das forças de extremidade das barras."""
        campo = [[0.0] * (nx + 1) for _ in range(ny + 1)]
        contagem = [[0] * (nx + 1) for _ in range(ny + 1)]
        if direcao == "X":
            for j in range(ny + 1):
                for i in range(nx):
                    he = altura((xs[i] + xs[i + 1]) / 2.0, ys[j])
                    EI = E * dy * he ** 3 / 12.0
                    L = dx
                    w1, w2 = w[j][i], w[j][i + 1]
                    t1, t2 = ty[j][i], ty[j][i + 1]
                    m1 = EI * ((6 * (w1 - w2) / L ** 2) + (4 * t1 + 2 * t2) / L)
                    m2 = EI * ((6 * (w1 - w2) / L ** 2) + (2 * t1 + 4 * t2) / L)
                    campo[j][i] += abs(m1) / dy
                    campo[j][i + 1] += abs(m2) / dy
                    contagem[j][i] += 1
                    contagem[j][i + 1] += 1
        else:
            for i in range(nx + 1):
                for j in range(ny):
                    he = altura(xs[i], (ys[j] + ys[j + 1]) / 2.0)
                    EI = E * dx * he ** 3 / 12.0
                    L = dy
                    w1, w2 = w[j][i], w[j + 1][i]
                    t1, t2 = tx[j][i], tx[j + 1][i]
                    m1 = EI * ((6 * (w1 - w2) / L ** 2) + (4 * t1 + 2 * t2) / L)
                    m2 = EI * ((6 * (w1 - w2) / L ** 2) + (2 * t1 + 4 * t2) / L)
                    campo[j][i] += abs(m1) / dx
                    campo[j + 1][i] += abs(m2) / dx
                    contagem[j][i] += 1
                    contagem[j + 1][i] += 1
        return [[campo[j][i] / max(contagem[j][i], 1) for i in range(nx + 1)]
                for j in range(ny + 1)]

    mx_campo = momentos("X")
    my_campo = momentos("Y")

    def momento_face(direcao: str) -> float:
        """
        Momento na seção de referência (face do pilar, NBR 6118, 22.6.4.1),
        por EQUILÍBRIO do trecho em balanço.

        Ler o momento nodal perto do pilar não serve: ali o campo tem a
        singularidade da carga concentrada e o valor não converge com o
        refinamento. Integrar a pressão além da face é estável — a pressão
        converge — e reproduz a definição normativa da seção de referência.
        """
        melhor = 0.0
        if direcao == "X":
            face = ap / 2.0
            for j in range(ny + 1):
                for lado in (-1.0, 1.0):
                    m = 0.0
                    for i in range(nx):
                        x0, x1 = xs[i], xs[i + 1]
                        xm = (x0 + x1) / 2.0
                        if lado > 0 and xm < face:
                            continue
                        if lado < 0 and xm > -face:
                            continue
                        braco = abs(xm) - face
                        p = (pressao[j][i] + pressao[j][i + 1]) / 2.0
                        m += p * dx * braco
                    melhor = max(melhor, m)
        else:
            face = bp / 2.0
            for i in range(nx + 1):
                for lado in (-1.0, 1.0):
                    m = 0.0
                    for j in range(ny):
                        y0, y1 = ys[j], ys[j + 1]
                        ym = (y0 + y1) / 2.0
                        if lado > 0 and ym < face:
                            continue
                        if lado < 0 and ym > -face:
                            continue
                        braco = abs(ym) - face
                        p = (pressao[j][i] + pressao[j + 1][i]) / 2.0
                        m += p * dy * braco
                    melhor = max(melhor, m)
        return melhor

    mx_face = momento_face("X")
    my_face = momento_face("Y")

    # equilíbrio: resultante das molas contra a carga aplicada
    resultante = 0.0
    for j in range(ny + 1):
        for i in range(nx + 1):
            area = dx * dy * (0.5 if i in (0, nx) else 1.0) \
                           * (0.5 if j in (0, ny) else 1.0)
            resultante += kv * w[j][i] * area

    alertas = []
    if min(min(l) for l in pressao) < -1e-6:
        alertas.append(
            "Há tração no contato em parte da base: o modelo de Winkler linear "
            "não representa descolamento, e a região tracionada deveria ser "
            "desconsiderada numa análise mais fina.")

    return ResultadoGrelha(
        x=xs, y=ys, w=w, pressao=pressao, mx=mx_campo, my=my_campo, kv=kv,
        n_gl=n_gl, equilibrio=resultante / max(N, 1e-9),
        p_max=max(max(l) for l in pressao),
        mx_max=max(max(l) for l in mx_campo),
        my_max=max(max(l) for l in my_campo),
        mx_face=mx_face, my_face=my_face, ap=ap, bp=bp,
        alertas=alertas)
