"""
solo_mef.py
-----------
Análise das tensões no maciço por ELEMENTOS FINITOS axissimétricos, com o
perfil discretizado em camadas de módulos distintos.

Por que não bastava Boussinesq
------------------------------
A solução de Boussinesq — usada no bulbo e no cálculo de recalques — supõe
semiespaço HOMOGÊNEO. Ela ignora que uma camada rígida sobre uma mole atrai
tensão e reduz o que chega embaixo, e que o contrário espalha a carga. Num
perfil estratificado, que é a regra e não a exceção, isso muda o quadro.

O modelo aqui é axissimétrico: a sapata retangular é substituída por uma área
circular de mesma área (R = raiz(a·b/pi)), carregada com a pressão de contato.
Isso troca o efeito de canto pela capacidade de representar camadas — para
leitura da distribuição em profundidade, a segunda importa mais.

Elemento: quadrilátero de 4 nós, integração 2x2 de Gauss, deformação
axissimétrica (inclui a deformação circunferencial). Contorno: base indeslocável,
laterais com rolete, eixo com rolete. O sistema é montado em banda e resolvido
por Cholesky.

Saída: sigma_z, sigma_r, sigma_theta e tau_rz nos centroides, mais as
invariantes usuais (tensão média e desviadora), que é o que permite ver onde o
maciço está mais solicitado.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Sequence

from .grelha import MatrizBanda

# pontos e pesos de Gauss 2x2
_G = 1.0 / math.sqrt(3.0)
_GAUSS = ((-_G, -_G), (_G, -_G), (_G, _G), (-_G, _G))


@dataclass
class MalhaSolo:
    """Malha axissimétrica e resultado da análise."""

    r: list[float]                     # coordenadas radiais dos nós [m]
    z: list[float]                     # profundidades dos nós [m] (positivas)
    dsigma_z: list[list[float]]        # acréscimo vertical [kPa], [j][i] por célula
    dsigma_r: list[list[float]]
    dsigma_theta: list[list[float]]
    tau_rz: list[list[float]]
    recalque: list[list[float]]        # deslocamento vertical dos nós [m]
    camada: list[list[str]]            # nome da camada de cada célula
    raio_equivalente: float
    q_liquido: float
    n_gl: int
    recalque_superficie: float         # sob o eixo, na cota da base [m]
    alertas: list[str] = field(default_factory=list)

    def desviadora(self, j: int, i: int) -> float:
        """Tensão desviadora q = sigma_1 − sigma_3 no plano r-z."""
        sz, sr = self.dsigma_z[j][i], self.dsigma_r[j][i]
        t = self.tau_rz[j][i]
        centro = (sz + sr) / 2.0
        raio = math.sqrt(((sz - sr) / 2.0) ** 2 + t ** 2)
        return 2.0 * raio if raio > 0 else 0.0

    def razao_boussinesq(self, j: int, i: int) -> float:
        return self.dsigma_z[j][i] / max(self.q_liquido, 1e-9)

    def razao_em(self, raio: float, z_absoluto: float) -> float:
        """
        Δσ_z / q num ponto qualquer, por interpolação bilinear entre centroides.
        Fora do domínio devolve zero.
        """
        raio = abs(raio)
        centros_r = [(self.r[i] + self.r[i + 1]) / 2.0
                     for i in range(len(self.r) - 1)]
        centros_z = [(self.z[j] + self.z[j + 1]) / 2.0
                     for j in range(len(self.z) - 1)]
        if not centros_r or not centros_z:
            return 0.0
        if raio > centros_r[-1] or z_absoluto > centros_z[-1]:
            return 0.0

        def faixa(vetor, valor):
            k = 0
            while k < len(vetor) - 2 and vetor[k + 1] < valor:
                k += 1
            v0, v1 = vetor[k], vetor[k + 1]
            t = 0.0 if abs(v1 - v0) < 1e-12 else (valor - v0) / (v1 - v0)
            return k, max(0.0, min(1.0, t))

        i, ti = faixa(centros_r, raio)
        j, tj = faixa(centros_z, z_absoluto)
        v = (self.dsigma_z[j][i] * (1 - ti) * (1 - tj)
             + self.dsigma_z[j][i + 1] * ti * (1 - tj)
             + self.dsigma_z[j + 1][i] * (1 - ti) * tj
             + self.dsigma_z[j + 1][i + 1] * ti * tj)
        return abs(v) / max(self.q_liquido, 1e-9)


# --------------------------------------------------------------------------- #
#  Elemento axissimétrico de 4 nós
# --------------------------------------------------------------------------- #
def _matriz_elastica(E: float, nu: float) -> list[list[float]]:
    """Matriz constitutiva axissimétrica: [sr, sz, stheta, trz]."""
    c = E / ((1.0 + nu) * (1.0 - 2.0 * nu))
    a = c * (1.0 - nu)
    b = c * nu
    g = E / (2.0 * (1.0 + nu))
    return [[a, b, b, 0.0],
            [b, a, b, 0.0],
            [b, b, a, 0.0],
            [0.0, 0.0, 0.0, g]]


def _b_e_jacobiano(rn: Sequence[float], zn: Sequence[float],
                   qsi: float, eta: float):
    """Matriz B axissimétrica e det(J) no ponto de Gauss."""
    N = [0.25 * (1 - qsi) * (1 - eta), 0.25 * (1 + qsi) * (1 - eta),
         0.25 * (1 + qsi) * (1 + eta), 0.25 * (1 - qsi) * (1 + eta)]
    dNq = [-0.25 * (1 - eta), 0.25 * (1 - eta), 0.25 * (1 + eta), -0.25 * (1 + eta)]
    dNe = [-0.25 * (1 - qsi), -0.25 * (1 + qsi), 0.25 * (1 + qsi), 0.25 * (1 - qsi)]

    j11 = sum(dNq[k] * rn[k] for k in range(4))
    j12 = sum(dNq[k] * zn[k] for k in range(4))
    j21 = sum(dNe[k] * rn[k] for k in range(4))
    j22 = sum(dNe[k] * zn[k] for k in range(4))
    det = j11 * j22 - j12 * j21
    if abs(det) < 1e-14:
        raise ValueError("Elemento degenerado na malha do solo.")

    inv = 1.0 / det
    r_gauss = sum(N[k] * rn[k] for k in range(4))
    r_gauss = max(r_gauss, 1e-9)          # evita singularidade no eixo

    B = [[0.0] * 8 for _ in range(4)]
    for k in range(4):
        dNr = inv * (j22 * dNq[k] - j12 * dNe[k])
        dNz = inv * (-j21 * dNq[k] + j11 * dNe[k])
        B[0][2 * k] = dNr                  # eps_r
        B[1][2 * k + 1] = dNz              # eps_z
        B[2][2 * k] = N[k] / r_gauss       # eps_theta
        B[3][2 * k] = dNz                  # gamma_rz
        B[3][2 * k + 1] = dNr
    return B, det, r_gauss


# --------------------------------------------------------------------------- #
#  Análise
# --------------------------------------------------------------------------- #
def analisar_solo(perfil, a: float, b: float, hf: float, q_liquido: float,
                  n_radial: int = 34, n_vertical: int = 40,
                  fator_extensao: float = 10.0,
                  profundidade_extra: float = 8.0) -> MalhaSolo:
    """
    Monta e resolve o maciço abaixo da cota de assentamento.

    perfil          PerfilGeotecnico, para os módulos de cada camada
    a, b            dimensões da sapata [m]
    hf              cota de assentamento [m]
    q_liquido       pressão líquida aplicada na base [kPa]
    fator_extensao  extensão lateral do domínio, em raios equivalentes
    """
    R = math.sqrt(a * b / math.pi)
    r_max = fator_extensao * R
    z_topo = hf
    z_max = min(perfil.profundidade_total,
                hf + max(profundidade_extra * R, 3.0 * max(a, b)))
    if z_max <= z_topo + 0.1:
        z_max = z_topo + 3.0 * max(a, b)
    alertas = []

    # malha refinada perto do eixo e do topo, onde os gradientes são fortes
    def graduado(n, limite, inicio=0.0, potencia=1.8):
        return [inicio + (limite - inicio) * (i / n) ** potencia
                for i in range(n + 1)]

    rs = graduado(n_radial, r_max, 0.0, 1.9)
    # garante um nó na borda da área carregada
    rs = sorted(set([round(v, 6) for v in rs] + [round(R, 6)]))
    zs = [z_topo + (z_max - z_topo) * (j / n_vertical) ** 1.6
          for j in range(n_vertical + 1)]
    # garante nós nas interfaces das camadas
    for z0, z1, _ in perfil.limites():
        for z in (z0, z1):
            if z_topo < z < z_max:
                zs.append(z)
    zs = sorted(set(round(v, 6) for v in zs))

    nr, nz = len(rs), len(zs)
    n_gl = 2 * nr * nz

    def no(i, j):
        return j * nr + i          # i radial, j vertical

    def gl(i, j, k):
        return 2 * no(i, j) + k    # k: 0 = u_r, 1 = u_z

    semibanda = 2 * nr + 3
    K = MatrizBanda(n_gl, semibanda)
    F = [0.0] * n_gl

    for j in range(nz - 1):
        for i in range(nr - 1):
            zc = (zs[j] + zs[j + 1]) / 2.0
            camada = perfil.camada_em(zc)
            Es = camada.modulo_deformabilidade_opcional()
            if Es is None:
                Es = 15000.0
                if not alertas:
                    alertas.append(
                        f"Camada '{camada.nome}' sem módulo informado: adotado "
                        "15 MPa apenas para a análise de tensões.")
            D = _matriz_elastica(Es, camada.nu)
            rn = [rs[i], rs[i + 1], rs[i + 1], rs[i]]
            zn = [zs[j], zs[j], zs[j + 1], zs[j + 1]]
            gls = []
            for (ii, jj) in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)):
                gls += [gl(ii, jj, 0), gl(ii, jj, 1)]

            ke = [[0.0] * 8 for _ in range(8)]
            for (qsi, eta) in _GAUSS:
                B, det, rg = _b_e_jacobiano(rn, zn, qsi, eta)
                peso = det * 2.0 * math.pi * rg
                DB = [[sum(D[m][p] * B[p][c] for p in range(4))
                       for c in range(8)] for m in range(4)]
                for lin in range(8):
                    for col in range(lin, 8):
                        ke[lin][col] += peso * sum(B[m][lin] * DB[m][col]
                                                   for m in range(4))
            for lin in range(8):
                for col in range(lin, 8):
                    K.somar(gls[lin], gls[col], ke[lin][col])

    # ------------------------------------------------------------- carga
    # pressão uniforme q sobre o disco de raio R, no topo do domínio
    for i in range(nr - 1):
        if rs[i + 1] > R + 1e-9:
            break
        r0, r1 = rs[i], rs[i + 1]
        L = r1 - r0
        # carga nodal CONSISTENTE do anel: F_k = 2*pi*q * integral(N_k * r dr).
        # Repartir "proporcional ao raio" erra a distribuição e contamina o
        # campo de tensões logo abaixo da área carregada.
        f0 = 2.0 * math.pi * q_liquido / L * (
            r1 * (r1 ** 2 - r0 ** 2) / 2.0 - (r1 ** 3 - r0 ** 3) / 3.0)
        f1 = 2.0 * math.pi * q_liquido / L * (
            (r1 ** 3 - r0 ** 3) / 3.0 - r0 * (r1 ** 2 - r0 ** 2) / 2.0)
        F[gl(i, 0, 1)] += f0
        F[gl(i + 1, 0, 1)] += f1

    # --------------------------------------------------------- contorno
    grande = 1.0e14
    for i in range(nr):                       # base indeslocável
        K.somar(gl(i, nz - 1, 0), gl(i, nz - 1, 0), grande)
        K.somar(gl(i, nz - 1, 1), gl(i, nz - 1, 1), grande)
    for j in range(nz):                       # eixo e lateral: rolete radial
        K.somar(gl(0, j, 0), gl(0, j, 0), grande)
        K.somar(gl(nr - 1, j, 0), gl(nr - 1, j, 0), grande)

    u = K.resolver(F)

    # ------------------------------------------------------ pós-processo
    sz = [[0.0] * (nr - 1) for _ in range(nz - 1)]
    sr = [[0.0] * (nr - 1) for _ in range(nz - 1)]
    st = [[0.0] * (nr - 1) for _ in range(nz - 1)]
    trz = [[0.0] * (nr - 1) for _ in range(nz - 1)]
    nomes = [[""] * (nr - 1) for _ in range(nz - 1)]

    for j in range(nz - 1):
        for i in range(nr - 1):
            zc = (zs[j] + zs[j + 1]) / 2.0
            camada = perfil.camada_em(zc)
            nomes[j][i] = camada.nome
            Es = camada.modulo_deformabilidade_opcional() or 15000.0
            D = _matriz_elastica(Es, camada.nu)
            rn = [rs[i], rs[i + 1], rs[i + 1], rs[i]]
            zn = [zs[j], zs[j], zs[j + 1], zs[j + 1]]
            ue = []
            for (ii, jj) in ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)):
                ue += [u[gl(ii, jj, 0)], u[gl(ii, jj, 1)]]
            B, _, _ = _b_e_jacobiano(rn, zn, 0.0, 0.0)     # centroide
            eps = [sum(B[m][c] * ue[c] for c in range(8)) for m in range(4)]
            s = [sum(D[m][p] * eps[p] for p in range(4)) for m in range(4)]
            sr[j][i], sz[j][i], st[j][i], trz[j][i] = s[0], s[1], s[2], s[3]

    recalque = [[u[gl(i, j, 1)] for i in range(nr)] for j in range(nz)]

    return MalhaSolo(
        r=rs, z=zs, dsigma_z=sz, dsigma_r=sr, dsigma_theta=st, tau_rz=trz,
        recalque=recalque, camada=nomes, raio_equivalente=R,
        q_liquido=q_liquido, n_gl=n_gl,
        recalque_superficie=recalque[0][0], alertas=alertas)


def conferir_com_boussinesq(malha: MalhaSolo, profundidades: Sequence[float]
                            ) -> list[tuple[float, float, float]]:
    """
    Compara o acréscimo vertical no eixo com Boussinesq para carga circular:

        Δσ_z / q = 1 − [ 1 / (1 + (R/z)²) ]^{3/2}

    Só faz sentido em perfil homogêneo — é justamente a aferição do modelo.
    Devolve [(z, MEF, Boussinesq), ...] com z medido abaixo da base.
    """
    R = malha.raio_equivalente
    z0 = malha.z[0]
    centros = [(malha.z[k] + malha.z[k + 1]) / 2.0 for k in range(len(malha.z) - 1)]
    saida = []
    for prof in profundidades:
        alvo = z0 + prof
        # interpola entre centroides: com malha graduada as células têm alturas
        # muito diferentes, e pegar a mais próxima introduz ruído na aferição
        k = 0
        while k < len(centros) - 2 and centros[k + 1] < alvo:
            k += 1
        c0, c1 = centros[k], centros[k + 1]
        t = 0.0 if abs(c1 - c0) < 1e-12 else (alvo - c0) / (c1 - c0)
        t = max(0.0, min(1.0, t))
        mef = malha.dsigma_z[k][0] * (1 - t) + malha.dsigma_z[k + 1][0] * t
        teorico = -malha.q_liquido * (
            1.0 - (1.0 / (1.0 + (R / max(prof, 1e-6)) ** 2)) ** 1.5)
        saida.append((prof, mef, teorico))
    return saida
