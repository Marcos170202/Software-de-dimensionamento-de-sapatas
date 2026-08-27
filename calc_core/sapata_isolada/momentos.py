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
forma fechada. A expressão acima só vale FORA da projeção do pilar; sob a
projeção, o balanço deixa de existir (a seção de referência é a própria face do
pilar — prática de engenharia consagrada, não item normativo específico) e o
campo é obtido por interpolação linear entre os valores das duas faces opostas.
Ver a discussão em `momento_1d`: a norma não define momento sob a seção de
referência, e a interpolação é uma escolha de desenho do campo de visualização,
contínua e limitada pelos valores de face — o campo não sugere armadura
crescente sob o pilar.

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
    de borda mais solicitada.

    Tomar a face do pilar como seção de referência é prática de engenharia
    consagrada, não item normativo específico: a NBR 6118:2023, 22.6, não
    prescreve a posição dessa seção (22.6.3 exige apenas que o modelo de flexão
    contemple 22.6.2). Decisão de engenharia, portanto, sem identificador de
    regra normativa associado.

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

    def coords(dim: float, dim_p: float, n: int) -> list[float]:
        """
        Grade uniforme com os dois nós mais próximos das faces do pilar
        deslocados para cima delas.

        A face é a seção de referência adotada (prática de engenharia
        consagrada, não item normativo específico) e é onde o campo tem seu
        máximo: se nenhum nó cai exatamente ali, o pico lido do
        campo fica abaixo do momento de dimensionamento só por erro de
        amostragem (~1,5 % numa grade 61x61), e o cabeçalho dos desenhos passa
        a mostrar um "máx" incompatível com o M_d adotado. O deslocamento é de
        no máximo meio espaçamento, preserva a ordem e preserva a simetria da
        grade (os dois nós são espelhados por construção).
        """
        c = [-dim / 2 + dim * i / (n - 1) for i in range(n)]
        meia = dim_p / 2.0
        if meia <= 1e-9 or meia >= dim / 2.0 - 1e-9:
            return c
        i_neg = min(range(1, n - 1), key=lambda i: abs(c[i] + meia))
        i_pos = n - 1 - i_neg
        if i_neg >= i_pos:                    # pilar menor que uma célula
            return c
        c[i_neg], c[i_pos] = -meia, meia
        return c

    xs = coords(a, ap, nx)
    ys = coords(b, bp, ny)

    def momento_1d(pos: float, fixo: float, dim: float, dim_p: float,
                   eixo: str) -> float:
        """
        Momento do balanço até `pos`; sob a projeção do pilar, interpolação
        linear entre os valores das duas faces.

        Fora da projeção (|pos| >= dim_p/2) o valor é o momento da pressão do
        solo entre a borda mais próxima e `pos` — o balanço engastado na face,
        seção de referência adotada por prática de engenharia consagrada (a
        NBR 6118:2023, 22.6, p. 191-193, lida por imagem da página, não define
        a posição dessa seção).

        Sob a projeção do pilar não há balanço, e a norma nada diz sobre o
        momento ali: 22.6.4.1.1 (p. 192) manda distribuir a armadura de flexão
        uniformemente ao longo da largura, de face a face da sapata, e
        22.6.2.2 a) admite a tração na flexão uniformemente distribuída na
        largura correspondente. Ou seja, a norma NÃO define um valor de momento
        sob a própria seção de referência, e nenhum valor adotado aqui altera a
        armadura (esta vem de `momento_unitario`, que usa só a face crítica).

        A interpolação linear entre m(-dim_p/2) e m(+dim_p/2) é, portanto, uma
        escolha de DESENHO do campo de visualização, não um requisito literal
        da norma. Ela foi adotada porque:
          - é contínua por construção — coincide com a curva externa nos dois
            limites |pos| = dim_p/2, sem degrau artificial no eixo do pilar
            (o clamp por sinal usado antes saltava do valor de uma face para o
            da outra exatamente em pos = 0, o que aparecia como um pico/funil
            falso na superfície 3D e como uma aresta reta no mapa 2D);
          - é limitada pelos dois valores de face, logo nunca sugere armadura
            crescente sob o pilar — a invariante física do campo;
          - é simétrica: não depende de convenção de sinal para pos = 0, e
            girar o problema 90° troca x por y sem mais nada.
        """
        limite = dim_p / 2.0

        def balanco(p: float) -> float:
            borda = math.copysign(dim / 2.0, p if p != 0.0 else 1.0)
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

        if limite <= 1e-9 or abs(pos) >= limite:
            return balanco(pos)

        m_esq, m_dir = balanco(-limite), balanco(limite)
        t = (pos + limite) / (2.0 * limite)      # 0 na face esquerda, 1 na direita
        return m_esq + (m_dir - m_esq) * t

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

    Dentro da projeção do pilar o campo é interpolado linearmente entre os dois
    nós que ladeiam a projeção, um de cada lado — o mesmo tratamento dado ao
    campo analítico em `campo_momentos.momento_1d`: ali a grelha tem a
    singularidade da carga concentrada e o pico não converge com o refinamento,
    e a norma (NBR 6118:2023, 22.6, p. 191-193) não define momento sob a própria
    seção de referência — que é, ela mesma, prática de engenharia consagrada e
    não item normativo. A interpolação é contínua nos dois nós de apoio e fica
    contida entre eles, logo não sugere armadura crescente sob o pilar.

    A versão anterior copiava o valor do nó "mais próximo da face" escolhido por
    `min(..., key=|‖c‖ − meia|)`, sem olhar o SINAL do nó preenchido: em empate
    de distância — o caso comum numa malha simétrica — `min` devolvia sempre o
    primeiro da lista, isto é, o nó do lado NEGATIVO, e os nós do lado positivo
    sob o pilar recebiam o momento da face oposta.
    """
    xs, ys = g.x, g.y
    ap, bp = g.ap, g.bp

    def clampar(campo, coords, meia: float, ao_longo_de_x: bool):
        """Preenche a faixa |coord| < meia por interpolação entre os vizinhos
        de fora, um de cada lado (respeitando o sinal)."""
        saida = [linha[:] for linha in campo]
        internos = {k for k in range(len(coords)) if abs(coords[k]) < meia}
        if not internos:
            return saida
        neg = [k for k in range(len(coords)) if coords[k] <= -meia]
        pos = [k for k in range(len(coords)) if coords[k] >= meia]
        k_neg = max(neg, key=lambda k: coords[k]) if neg else None
        k_pos = min(pos, key=lambda k: coords[k]) if pos else None
        if k_neg is None and k_pos is None:
            return saida                      # projeção cobre a base inteira
        if k_neg is None:
            k_neg = k_pos
        if k_pos is None:
            k_pos = k_neg

        def valor(k: int, j: int, i: int) -> float:
            return campo[j][k] if ao_longo_de_x else campo[k][i]

        span = coords[k_pos] - coords[k_neg]
        for j in range(len(ys)):
            for i in range(len(xs)):
                k_int = i if ao_longo_de_x else j
                if k_int not in internos:
                    continue
                v_neg, v_pos = valor(k_neg, j, i), valor(k_pos, j, i)
                if span <= 1e-12:
                    saida[j][i] = v_neg
                    continue
                t = (coords[k_int] - coords[k_neg]) / span
                saida[j][i] = v_neg + (v_pos - v_neg) * t
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
