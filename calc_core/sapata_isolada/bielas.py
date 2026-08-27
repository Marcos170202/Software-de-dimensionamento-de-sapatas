"""
bielas.py
---------
Dimensionamento de sapata RÍGIDA por bielas e tirantes.

A NBR 6118:2023, item 22.6.3 (Modelo de cálculo), admite os dois caminhos para
a armadura de sapata rígida — modelos de flexão "quando for o caso" e, no seu
último parágrafo, "permitindo-se a adoção de um modelo de bielas e tirantes
para a determinação das armaduras". Para peça rígida o segundo representa
melhor o que acontece: a carga do pilar desce por bielas comprimidas
inclinadas até a reação do solo, e o tirante na base é a armadura. Não há a
distribuição de deformações que a teoria de flexão pressupõe.

Modelo (Blévot, generalizado para carga excêntrica)
--------------------------------------------------
Para cada direção e cada lado da sapata:

    R      resultante da reação do solo naquele lado
    x_R    posição do centro de gravidade dessa reação
    x_p    ponto de aplicação no pilar (baricentro da meia seção, a_p/4)
    z      braço interno (adotado igual a d, como em Blévot)

    T = R · (x_R − x_p) / z              força no tirante
    tan θ = z / (x_R − x_p)              inclinação da biela

Com carga centrada isso se reduz à expressão clássica

    T = N_d · (a − a_p) / (8 · d)

Verificações de nó, NBR 6118, item 22.3.2:
    CCC (só compressão) ......... 0,85 · α_v2 · f_cd
    CCT (um tirante) ............ 0,72 · α_v2 · f_cd
com α_v2 = 1 − f_ck/250.

Sobre a tensão na biela
-----------------------
A expressão sigma = N/(A_p · sen²θ) é de Blévot para BLOCOS SOBRE ESTACAS, onde
a reação chega concentrada e a biela é um elemento discreto. Numa sapata a
reação do solo é distribuída e o que existe é um leque de bielas, com área bem
maior junto à base. Por isso a verificação da biela é reportada como
INFORMATIVA: a verificação normativa de esmagamento em sapata é a compressão
diagonal do item 19.5, feita à parte. Usar o valor de Blévot para reprovar uma
sapata seria transportar um critério para fora do seu domínio.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from .momentos import plano_tensoes


@dataclass
class ResultadoBielas:
    """Modelo de bielas e tirantes de uma direção."""

    direcao: str
    T: float                    # força no tirante [kN]
    As: float                   # armadura necessária [m²]
    theta: float                # inclinação da biela [graus]
    z: float                    # braço interno adotado [m]
    R: float                    # resultante da reação no lado governante [kN]
    x_R: float                  # centro de gravidade da reação [m]
    x_p: float                  # ponto de aplicação no pilar [m]
    sigma_biela: float          # tensão na biela, junto ao pilar [kPa]
    sigma_limite_ccc: float     # 0,85·α_v2·f_cd [kPa]
    sigma_limite_cct: float     # 0,72·α_v2·f_cd [kPa]
    biela_ok: bool
    inclinacao_ok: bool
    As_flexao: float = 0.0      # comparação com a teoria de flexão [m²]
    alertas: list[str] = field(default_factory=list)

    @property
    def aproveitamento_biela(self) -> float:
        return self.sigma_biela / max(self.sigma_limite_ccc, 1e-9)


def bielas_sapata(N: float, Mx: float, My: float, a: float, b: float,
                  ap: float, bp: float, dx: float, dy: float,
                  concreto, aco, coef_braco: float = 1.0,
                  theta_minimo: float = 45.0) -> dict:
    """
    Resolve o modelo de bielas para as duas direções.

    N, Mx, My  esforços de cálculo na base [kN, kN·m]
    dx, dy     alturas úteis de cada direção [m]
    coef_braco multiplica d para obter o braço interno z (1,0 = Blévot)

    Devolve {"X": ResultadoBielas, "Y": ResultadoBielas}.
    """
    if N <= 0:
        return {}

    sm, kx, ky = plano_tensoes(N, Mx, My, a, b)

    def sigma(x, y):
        return max(0.0, sm + kx * x + ky * y)

    fcd = concreto.fcd * 1000.0                     # kPa
    alpha_v2 = concreto.alpha_v
    lim_ccc = 0.85 * alpha_v2 * fcd
    lim_cct = 0.72 * alpha_v2 * fcd
    fyd = aco.fyd * 1000.0

    saida: dict[str, ResultadoBielas] = {}
    n = 60

    for direcao, dim, largura, dim_p, d in (("X", a, b, ap, dx),
                                            ("Y", b, a, bp, dy)):
        z = coef_braco * d
        melhor: Optional[ResultadoBielas] = None

        for lado in (-1.0, 1.0):
            # resultante da reação do solo na metade correspondente e seu c.g.
            passo = (dim / 2.0) / n
            soma, momento = 0.0, 0.0
            for i in range(n):
                c = lado * (i + 0.5) * passo            # coordenada no eixo
                # média da pressão na faixa transversal
                p = 0.0
                m = 8
                for j in range(m):
                    t = -largura / 2.0 + (j + 0.5) * largura / m
                    p += sigma(c, t) if direcao == "X" else sigma(t, c)
                p /= m
                forca = p * passo * largura
                soma += forca
                momento += forca * abs(c)
            if soma <= 1e-9:
                continue
            x_R = momento / soma
            x_p = dim_p / 4.0
            braco = max(x_R - x_p, 1e-6)
            T = soma * braco / z
            theta = math.degrees(math.atan2(z, braco))
            sin2 = math.sin(math.radians(theta)) ** 2
            sigma_biela = N / (ap * bp * max(sin2, 1e-6))

            alertas = []
            if theta < theta_minimo:
                alertas.append(
                    f"Direção {direcao}: biela a {theta:.1f}°, abaixo dos "
                    f"{theta_minimo:.0f}° recomendados por Blévot. O modelo de "
                    "bielas perde representatividade — reveja a altura.")
            if sigma_biela > lim_ccc:
                alertas.append(
                    f"Direção {direcao}: tensão na biela pela expressão de "
                    f"Blévot ({sigma_biela/1000:.1f} MPa) supera o limite do nó "
                    f"CCC ({lim_ccc/1000:.1f} MPa). Indicativo apenas: a "
                    "expressão é de blocos sobre estacas; em sapata vale a "
                    "compressão diagonal do item 19.5, verificada à parte.")

            r = ResultadoBielas(
                direcao=direcao, T=T, As=T / fyd, theta=theta, z=z, R=soma,
                x_R=x_R, x_p=x_p, sigma_biela=sigma_biela,
                sigma_limite_ccc=lim_ccc, sigma_limite_cct=lim_cct,
                biela_ok=sigma_biela <= lim_ccc,
                inclinacao_ok=theta >= theta_minimo, alertas=alertas)
            if melhor is None or r.T > melhor.T:
                melhor = r

        if melhor:
            saida[direcao] = melhor
    return saida


def tirante_classico(N: float, dim: float, dim_p: float, d: float) -> float:
    """Expressão clássica de Blévot, para conferência: T = N(a − a_p)/(8d)."""
    return N * (dim - dim_p) / (8.0 * d)
