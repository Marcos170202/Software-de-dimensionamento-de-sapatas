"""
rigidez.py
----------
Classificação de rigidez da sapata e distribuição de pressões no contato,
obtida por discretização em base elástica (Winkler).

Por que isto existe
-------------------
O modelo de sapata RÍGIDA admite distribuição linear (plana) de pressões: a
peça gira como corpo rígido e o solo acompanha. Numa sapata FLEXÍVEL a peça
deforma, o solo reage proporcionalmente ao recalque local e a pressão se
concentra sob o pilar, caindo nas bordas. O momento no balanço e o cisalhamento
mudam junto — não é o mesmo problema com outra altura.

A NBR 6118:2023 separa os dois comportamentos:
    item 22.6.1  classificação: rígida quando h >= (a - a_p)/3
    item 22.6.2  rígida  — flexão nas duas direções, tração distribuída na
                 largura, ruptura por compressão diagonal (sem cone de punção)
    item 22.6.3  flexível — comporta-se como laje: punção deve ser verificada
                 nas superfícies críticas do item 19.5

Modelo numérico
---------------
Cada direção é resolvida como uma viga de largura unitária sobre apoio elástico
contínuo, por elementos finitos de viga (Hermite, 2 graus de liberdade por nó):

    K = K_flexão + K_fundação            K_f consistente de Winkler
    p(x) = k_v · w(x)                    pressão no contato

Extremidades livres saem naturalmente da formulação, e a altura variável da
sapata (tronco entre h0 e h) entra elemento a elemento. Com rigidez muito alta
a solução tende à distribuição linear, o que serve de aferição contra o modelo
rígido clássico.

Referências: Hetényi (1946); Bowles (1996); ABNT NBR 6118:2023, item 22.6.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Sequence


# =========================================================================== #
#  Coeficiente de reação vertical
# =========================================================================== #
def kv_por_tensao_admissivel(sigma_adm: float, recalque_referencia: float = 0.010
                             ) -> float:
    """
    Estimativa de k_v [kN/m³] a partir da tensão admissível (Bowles):
    o solo mobiliza sigma_adm com um recalque de referência, usualmente 10 mm.

        k_v = sigma_adm / recalque_referencia

    Valor indicativo para pré-dimensionamento; prova de carga ou ensaio de
    placa é o que a NBR 6122:2019 espera para uso em projeto.
    """
    return sigma_adm / max(recalque_referencia, 1e-4)


def kv_por_modulo(Es: float, B: float, nu: float = 0.30) -> float:
    """
    k_v [kN/m³] a partir do módulo de deformabilidade do maciço (Vésic):

        k_v = E_s / (B · (1 - nu²))

    Depende da largura B: a mesma camada dá k_v menor sob sapata maior, porque
    o bulbo alcança mais fundo.
    """
    return Es / max(B * (1.0 - nu ** 2), 1e-6)


# =========================================================================== #
#  Classificação
# =========================================================================== #
@dataclass
class Classificacao:
    """Resultado do exame de rigidez, pelos três critérios usuais."""

    rigida_nbr: bool                 # h >= (a - a_p)/3  (NBR 6118, 22.6.1)
    h_necessario: float              # altura que tornaria rígida [m]
    lambda_L_x: float                # parâmetro de Hetényi na direção X
    lambda_L_y: float
    rigidez_relativa: float          # K_r de Meyerhof
    classe_hetenyi: str              # "curta" (rígida), "média", "longa" (flexível)
    modelo_recomendado: str          # "rigida" ou "flexivel"
    observacoes: list[str] = field(default_factory=list)


def classificar(a: float, b: float, h: float, h0: float, ap: float, bp: float,
                Ecs_MPa: float, kv: float) -> Classificacao:
    """
    Cruza o critério geométrico da NBR com dois critérios de rigidez relativa.

    Hetényi define o comportamento pela grandeza adimensional lambda·L:
        lambda = (k_v · b / (4 · E · I))^(1/4)
        lambda·L < pi/4  -> viga curta: gira praticamente como corpo rígido
        lambda·L > pi    -> viga longa: a carga não alcança as extremidades
    """
    E = Ecs_MPa * 1000.0                      # MPa -> kPa
    h_med = (h + h0) / 2.0                    # altura equivalente do tronco
    obs: list[str] = []

    def lambda_L(dimensao: float, largura: float) -> float:
        I = largura * h_med ** 3 / 12.0
        lam = (kv * largura / (4.0 * E * I)) ** 0.25
        return lam * dimensao

    lLx = lambda_L(a, b)
    lLy = lambda_L(b, a)
    maior = max(lLx, lLy)

    if maior < math.pi / 4.0:
        classe = "curta (comportamento rígido)"
    elif maior > math.pi:
        classe = "longa (comportamento flexível)"
    else:
        classe = "média (comportamento intermediário)"

    h_nec = max((a - ap) / 3.0, (b - bp) / 3.0)
    rigida_nbr = h >= h_nec - 1e-9

    # rigidez relativa de Meyerhof: E_c·I / (E_s·B³); acima de ~0,5 é rígida
    B = min(a, b)
    I_faixa = 1.0 * h_med ** 3 / 12.0
    Es_equiv = kv * B * (1.0 - 0.30 ** 2)
    Kr = E * I_faixa / max(Es_equiv * B ** 3, 1e-9)

    modelo = "rigida" if rigida_nbr else "flexivel"
    if rigida_nbr and maior > math.pi:
        obs.append(
            "A geometria atende ao critério da NBR 6118 (22.6.1), mas a rigidez "
            "relativa ao solo indica comportamento flexível: vale comparar as "
            "duas distribuições de pressão antes de fechar o detalhamento.")
    if not rigida_nbr and maior < math.pi / 4.0:
        obs.append(
            "A geometria é flexível pelo critério da NBR, mas o solo é "
            "deformável o bastante para a peça responder como rígida.")
    if not rigida_nbr:
        obs.append(
            f"Sapata flexível: h = {h:.2f} m contra {h_nec:.2f} m que a tornaria "
            "rígida. A NBR 6118, 22.6.3, exige verificação de punção.")
    return Classificacao(rigida_nbr, h_nec, lLx, lLy, Kr, classe, modelo, obs)


# =========================================================================== #
#  Solução da viga sobre base elástica por elementos finitos
# =========================================================================== #
def _resolver(K: list[list[float]], F: list[float]) -> list[float]:
    """Eliminação de Gauss com pivotamento parcial (matriz pequena e cheia)."""
    n = len(F)
    M = [linha[:] + [F[i]] for i, linha in enumerate(K)]
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[piv][c]) < 1e-14:
            raise ValueError("Sistema singular na solução da base elástica.")
        M[c], M[piv] = M[piv], M[c]
        inv = 1.0 / M[c][c]
        for r in range(c + 1, n):
            f = M[r][c] * inv
            if f == 0.0:
                continue
            for k in range(c, n + 1):
                M[r][k] -= f * M[c][k]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        soma = M[r][n] - sum(M[r][c] * x[c] for c in range(r + 1, n))
        x[r] = soma / M[r][r]
    return x


@dataclass
class ReacaoDiscretizada:
    """Distribuição de pressões e esforços de uma direção."""

    direcao: str
    x: list[float]                  # coordenadas dos nós [m], de -dim/2 a +dim/2
    pressao: list[float]            # p(x) no contato [kPa]
    recalque: list[float]           # w(x) [m]
    momento: list[float]            # M(x) por unidade de largura [kN·m/m]
    pressao_linear: list[float]     # distribuição do modelo rígido, para comparar
    momento_face: float             # momento na face do pilar [kN·m/m]
    momento_face_linear: float
    rotacao: list[float] = field(default_factory=list)
    p_max: float = 0.0
    p_max_linear: float = 0.0
    kv: float = 0.0
    convergiu: bool = True


def reacao_base_elastica(N: float, M: float, dim: float, largura: float,
                         dim_pilar: float, h: float, h0: float,
                         Ecs_MPa: float, kv: float,
                         n_elementos: int = 48) -> ReacaoDiscretizada:
    """
    Resolve uma faixa da sapata como viga sobre base elástica.

    N  [kN]    carga vertical transmitida pelo pilar
    M  [kN·m]  momento na base, no plano da direção analisada
    dim        comprimento da faixa (a ou b) [m]
    largura    dimensão perpendicular (b ou a) [m]
    dim_pilar  dimensão do pilar na direção analisada [m]

    N entra distribuído na projeção do pilar; M entra como momento nodal no
    eixo. Espalhar o momento como pressão linear dentro da projeção geraria
    valores absurdos (o momento de inércia da faixa do pilar é minúsculo) e
    contaminaria a flexão local, embora seja estaticamente equivalente.
    """
    n = max(8, int(n_elementos))
    if n % 2:
        n += 1                                   # nó no eixo
    L = dim / n
    E = Ecs_MPa * 1000.0
    k_mola = kv * largura                        # kN/m por metro de viga
    xs = [-dim / 2.0 + i * L for i in range(n + 1)]

    # altura do elemento: h sob o pilar, decaindo até h0 na borda
    def altura(xm: float) -> float:
        s = abs(xm)
        if s <= dim_pilar / 2.0:
            return h
        t = (s - dim_pilar / 2.0) / max(dim / 2.0 - dim_pilar / 2.0, 1e-9)
        return h + (h0 - h) * min(t, 1.0)

    gl = 2 * (n + 1)
    K = [[0.0] * gl for _ in range(gl)]
    F = [0.0] * gl

    # Carga vertical do pilar, distribuída na sua projeção. A parcela de cada
    # elemento vem da SOBREPOSIÇÃO real com a projeção: usar o elemento inteiro
    # quando o centro cai dentro faz a resultante errar sempre que a largura do
    # pilar não é múltiplo do comprimento do elemento.
    def carga_elemento(x0: float, x1: float) -> float:
        esq = max(x0, -dim_pilar / 2.0)
        dir_ = min(x1, dim_pilar / 2.0)
        sobreposicao = max(0.0, dir_ - esq)
        if sobreposicao <= 0.0:
            return 0.0
        return (N * sobreposicao / dim_pilar) / (x1 - x0)   # kN/m

    for e in range(n):
        xm = (xs[e] + xs[e + 1]) / 2.0
        he = altura(xm)
        I = largura * he ** 3 / 12.0
        EI = E * I
        c = EI / L ** 3
        ke = [[12 * c, 6 * L * c, -12 * c, 6 * L * c],
              [6 * L * c, 4 * L * L * c, -6 * L * c, 2 * L * L * c],
              [-12 * c, -6 * L * c, 12 * c, -6 * L * c],
              [6 * L * c, 2 * L * L * c, -6 * L * c, 4 * L * L * c]]
        f = k_mola * L / 420.0
        kf = [[156 * f, 22 * L * f, 54 * f, -13 * L * f],
              [22 * L * f, 4 * L * L * f, 13 * L * f, -3 * L * L * f],
              [54 * f, 13 * L * f, 156 * f, -22 * L * f],
              [-13 * L * f, -3 * L * L * f, -22 * L * f, 4 * L * L * f]]
        q = carga_elemento(xs[e], xs[e + 1])
        fe = [q * L / 2.0, q * L * L / 12.0, q * L / 2.0, -q * L * L / 12.0]

        mapa = [2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3]
        for i in range(4):
            F[mapa[i]] += fe[i]
            for j in range(4):
                K[mapa[i]][mapa[j]] += ke[i][j] + kf[i][j]

    # momento do pilar aplicado no nó do eixo (grau de liberdade de rotação)
    if abs(M) > 1e-9:
        F[2 * (n // 2) + 1] += M

    u = _resolver(K, F)
    w = [u[2 * i] for i in range(n + 1)]
    theta = [u[2 * i + 1] for i in range(n + 1)]
    pressao = [kv * wi for wi in w]                      # kPa

    # momento por unidade de largura, da curvatura nodal
    momento = []
    for i in range(n + 1):
        i0 = min(max(i, 1), n - 1)
        curv = (w[i0 - 1] - 2 * w[i0] + w[i0 + 1]) / L ** 2
        he = altura(xs[i0])
        EI = E * largura * he ** 3 / 12.0
        momento.append(-EI * curv / largura)

    # distribuição do modelo rígido, para comparação direta
    A = dim * largura
    Iw = largura * dim ** 3 / 12.0
    linear = [max(0.0, N / A + M * x / Iw) for x in xs]

    face = dim_pilar / 2.0
    i_face = min(range(n + 1), key=lambda i: abs(abs(xs[i]) - face))
    mom_face = max(abs(momento[i_face]), abs(momento[n - i_face]))

    # momento do modelo rígido no balanço, integrando a pressão linear
    lado = 1.0 if M >= 0 else -1.0
    borda, xf = lado * dim / 2.0, lado * face
    Lb = abs(borda - xf)
    s_face = max(0.0, N / A + M * xf / Iw)
    s_borda = max(0.0, N / A + M * borda / Iw)
    mom_linear = s_face * Lb ** 2 / 2.0 + (s_borda - s_face) * Lb ** 2 / 3.0

    return ReacaoDiscretizada(
        direcao="", x=xs, pressao=pressao, recalque=w, momento=momento,
        pressao_linear=linear, momento_face=mom_face,
        momento_face_linear=mom_linear, rotacao=theta, p_max=max(pressao),
        p_max_linear=max(linear), kv=kv)


def verificar_equilibrio(r: ReacaoDiscretizada, N: float, largura: float
                         ) -> float:
    """
    Resultante das molas dividida pela carga aplicada — deve dar 1,00.

    A integração usa a própria interpolação cúbica de Hermite do elemento,
    exata para este campo; a regra do trapézio sobre os valores nodais erra
    alguns por cento porque ignora as rotações.
    """
    total = 0.0
    for i in range(len(r.x) - 1):
        L = r.x[i + 1] - r.x[i]
        # integral exata de w na cúbica de Hermite
        integral = (L / 2.0 * (r.recalque[i] + r.recalque[i + 1])
                    + L ** 2 / 12.0 * (r.rotacao[i] - r.rotacao[i + 1]))
        total += r.kv * integral * largura
    return total / max(N, 1e-9)
