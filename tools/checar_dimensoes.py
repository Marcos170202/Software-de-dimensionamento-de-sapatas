#!/usr/bin/env python3
"""Checagem dimensional determinística das fórmulas candidatas do ruleset.

Ferramenta do a2-verificador (cascata de checagem, etapa 2). Substitui cada
variável por uma grandeza com unidade (`pint`) e verifica a homogeneidade da
expressão. Um expoente trocado, uma variável faltando ou um `d` que virou `d²`
quebra a dimensão e aparece aqui sem intervenção humana.

Uso:
    python tools/checar_dimensoes.py            # roda todos os casos
    python tools/checar_dimensoes.py <padrao>   # roda os casos cujo id casa

Convenção de saída:
    OK        — expressão homogênea e com a dimensão esperada
    FALHA     — expressão inconsistente ou com dimensão diferente da esperada
    EMPIRICA  — expressão declaradamente não homogênea (correlação empírica);
                a checagem dimensional NÃO se aplica e o motivo fica registrado

Retorna código de saída 1 se qualquer caso terminar em FALHA.
"""

from __future__ import annotations

import math
import sys

import pint

u = pint.UnitRegistry()
Q = u.Quantity

# ---------------------------------------------------------------------------
# Grandezas típicas do escopo (a2-verificador.md, etapa 4: sanity check)
# ---------------------------------------------------------------------------
N_SPT = 15.0  # adimensional (golpes)
B = Q(2.0, "m")  # menor dimensão da base
L = Q(2.0, "m")  # maior dimensão da base
h = Q(1.5, "m")  # embutimento
gamma = Q(18.0, "kN/m**3")  # peso específico efetivo
c = Q(150.0, "kPa")  # coesão (10 * N_SPT kPa)
phi = Q(math.degrees(math.atan(0.6)), "degree")  # ~31 graus

CASOS: list[tuple[str, str, object, object]] = []


def caso(ident: str, descricao: str, valor, esperado):
    """Registra um caso. `esperado` é uma unidade-alvo ou a string EMPIRICA."""
    CASOS.append((ident, descricao, valor, esperado))


# ---------------------------------------------------------------------------
# 1. Capacidade de carga de Terzaghi com fatores de forma
#    sigma_r = c*Nc*Sc + q*Nq*Sq + 0.5*gamma*B*Ngamma*Sgamma
# ---------------------------------------------------------------------------
Nc, Nq, Ngamma = 32.67, 20.63, 25.99  # adimensionais, Tab. 2.2 para phi = 31
Sc, Sq, Sgamma = 1.63, 1.60, 0.60  # adimensionais, Tab. 2.3 (quadrada)
q = gamma * h

caso(
    "CINTRA-2.2.4-parcela-coesao",
    "c * Nc * Sc",
    c * Nc * Sc,
    "kPa",
)
caso(
    "CINTRA-2.2.4-parcela-sobrecarga",
    "q * Nq * Sq, com q = gamma * h",
    q * Nq * Sq,
    "kPa",
)
caso(
    "CINTRA-2.2.4-parcela-peso",
    "0.5 * gamma * B * Ngamma * Sgamma",
    0.5 * gamma * B * Ngamma * Sgamma,
    "kPa",
)
caso(
    "CINTRA-2.2.4-equacao-completa",
    "sigma_r = c*Nc*Sc + q*Nq*Sq + 0.5*gamma*B*Ngamma*Sgamma",
    c * Nc * Sc + q * Nq * Sq + 0.5 * gamma * B * Ngamma * Sgamma,
    "kPa",
)

# Mutantes: o que a checagem dimensional PEGA e o que ela NÃO pega.
caso(
    "MUTANTE-parcela-peso-sem-o-meio-B",
    "0.5 * gamma * Ngamma * Sgamma (B faltando) -- DEVE FALHAR",
    0.5 * gamma * Ngamma * Sgamma,
    "kPa",
)
caso(
    "MUTANTE-parcela-peso-B-ao-quadrado",
    "0.5 * gamma * B**2 * Ngamma * Sgamma -- DEVE FALHAR",
    0.5 * gamma * B**2 * Ngamma * Sgamma,
    "kPa",
)
caso(
    "MUTANTE-sobrecarga-sem-gamma",
    "h * Nq * Sq (q trocado por h) -- DEVE FALHAR",
    h * Nq * Sq,
    "kPa",
)

# ---------------------------------------------------------------------------
# 2. Fatores adimensionais
# ---------------------------------------------------------------------------
caso("CINTRA-Tab2.3-Sc-retangular", "1 + (B/L)*(Nq/Nc)", 1 + (B / L) * (Nq / Nc), "dimensionless")
caso("CINTRA-Tab2.3-Sq-retangular", "1 + (B/L)*tan(phi)", 1 + (B / L) * math.tan(phi.to("rad").m), "dimensionless")
caso("CINTRA-Tab2.3-Sgamma-retangular", "1 - 0.4*(B/L)", 1 - 0.4 * (B / L), "dimensionless")
caso(
    "CINTRA-2.3.1-vesic-Ngamma",
    "Ngamma = 2*(Nq+1)*tan(phi)",
    Q(2 * (Nq + 1) * math.tan(phi.to("rad").m), "dimensionless"),
    "dimensionless",
)

# ---------------------------------------------------------------------------
# 3. Tensão admissível pelo caminho teórico (FS global adimensional)
# ---------------------------------------------------------------------------
sigma_r = c * Nc * Sc + q * Nq * Sq + 0.5 * gamma * B * Ngamma * Sgamma
caso("CINTRA-4.1.1-sigma-adm-teorico", "sigma_a = sigma_r / 3.0", sigma_r / 3.0, "kPa")

# ---------------------------------------------------------------------------
# 4. Majoração por vento — fator adimensional sobre tensão
# ---------------------------------------------------------------------------
caso(
    "NBR6122-6.3.2-majoracao",
    "(1 + k_v) * sigma_adm, k_v <= 0.15 ou 0.30",
    (1 + 0.15) * Q(250.0, "kPa"),
    "kPa",
)
caso(
    "NBR6122-6.3.3-majoracao",
    "(1 + k_v) * sigma_Rd, k_v <= 0.10",
    (1 + 0.10) * Q(250.0, "kPa"),
    "kPa",
)

# ---------------------------------------------------------------------------
# 5. Correlações empíricas — NÃO são homogêneas, e isso é declarado
# ---------------------------------------------------------------------------
caso(
    "CINTRA-2.9.1-coesao-por-Nspt",
    "c = 10 * N_spt (kPa) -- coeficiente carrega kPa/golpe",
    "EMPIRICA",
    "N_spt e adimensional (golpes) e o resultado e kPa: o coeficiente 10 nao e "
    "puro, carrega kPa por golpe. A homogeneidade so fecha se a unidade for "
    "atribuida ao coeficiente, o que a fonte nao faz.",
)
caso(
    "CINTRA-2.9.2-phi-teixeira",
    "phi = sqrt(20*N_spt) + 15 (graus)",
    "EMPIRICA",
    "Soma um numero puro (raiz de golpes) a um angulo. Nao homogenea por "
    "construcao. A checagem dimensional NAO tem poder aqui e NAO pode ser "
    "usada para validar a geometria do radical -- so a leitura visual pega "
    "sqrt(20*N+15) no lugar de sqrt(20*N)+15.",
)
caso(
    "CINTRA-4.1.2a-sigma-adm-SPT-Nspt-50",
    "sigma_a = N_spt/50 + q (MPa)",
    "EMPIRICA",
    "N_spt/50 e numero puro somado a q em MPa. So fecha atribuindo MPa/golpe "
    "ao divisor 50. ARMADILHA REAL: como o termo +q JA e uma tensao, um "
    "implementador que passe q em kPa em vez de MPa produz erro de fator 1000 "
    "que a analise dimensional do codigo NAO acusa -- os dois termos sao "
    "'tensao'. Exige guarda de unidade explicita.",
)
caso(
    "CINTRA-4.1.2a-teixeira-1996-areia",
    "sigma_a = 0.05 + (1 + 0.4*B)*N_spt/100 (MPa)",
    "EMPIRICA",
    "O coeficiente 0.4 carrega 1/m e o 0.05 carrega MPa. B TEM de entrar em "
    "metros. ARMADILHA REAL: passar B em cm produz numero grande e plausivel "
    "sem nenhum erro dimensional detectavel. Exige guarda de unidade explicita.",
)
caso(
    "CINTRA-4.1.2a-mello-1975",
    "sigma_a = 0.1*(sqrt(N_spt) - 1) (MPa)",
    "EMPIRICA",
    "Raiz de grandeza adimensional menos 1, vezes coeficiente que carrega MPa.",
)


def main(padrao: str | None = None) -> int:
    falhas = 0
    largura = max(len(i) for i, *_ in CASOS)
    for ident, descricao, valor, esperado in CASOS:
        if padrao and padrao not in ident:
            continue
        if valor == "EMPIRICA":
            print(f"EMPIRICA {ident:<{largura}}  {descricao}")
            print(f"         {'':<{largura}}  motivo: {esperado}")
            continue
        try:
            convertido = valor.to(esperado)
            deve_falhar = ident.startswith("MUTANTE")
            marca = "FALHA" if deve_falhar else "OK   "
            if deve_falhar:
                falhas += 1
            print(f"{marca}    {ident:<{largura}}  {descricao}")
            print(f"         {'':<{largura}}  -> {convertido:~.4P}")
        except pint.DimensionalityError as erro:
            if ident.startswith("MUTANTE"):
                print(f"OK(mut) {ident:<{largura}}  {descricao}")
                print(f"         {'':<{largura}}  rejeitado como esperado: {erro}")
            else:
                falhas += 1
                print(f"FALHA    {ident:<{largura}}  {descricao}")
                print(f"         {'':<{largura}}  {erro}")
    print()
    print(f"casos com FALHA: {falhas}")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
