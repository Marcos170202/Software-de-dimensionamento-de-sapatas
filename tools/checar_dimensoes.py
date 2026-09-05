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
    """Registra um caso. `esperado` é uma unidade-alvo ou a string EMPIRICA.

    `valor` pode ser uma grandeza `pint` já construída ou um CALLABLE sem
    argumentos. A forma callable existe para os mutantes que quebram já na
    CONSTRUÇÃO da expressão (somar metro com número puro, por exemplo): a
    exceção precisa acontecer dentro de `main`, não no import do módulo.
    """
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

# ===========================================================================
# 6. PILARETE DE CONCRETO COMO PILAR CURTO — NBR 6118:2023 (backlog #13, v11)
#
#    Grandezas típicas do sanity check (a2-verificador.md, etapa 4):
#    seção 30x30 cm, altura livre 1,00 m engastada na base e livre no topo,
#    C25, CA-50, N_d = 1000 kN, phi 16 mm, estribo 5 mm.
# ===========================================================================
h_sec = Q(0.30, "m")          # altura da seção na direção considerada
b_sec = Q(0.30, "m")          # menor dimensão da seção
A_c = h_sec * b_sec           # área bruta de concreto
N_d = Q(1000.0, "kN")         # força normal de cálculo
ell = Q(1.00, "m")            # altura livre do pilarete
f_ck = Q(25.0, "MPa")
gamma_c = 1.4
gamma_s = 1.15
f_cd = f_ck / gamma_c
f_yk = Q(500.0, "MPa")
f_yd = f_yk / gamma_s
E_s = Q(210.0, "GPa")         # NBR 6118, 8.3.5
eps_c2 = 2.0e-3               # NBR 6118, 8.2.10.1 (classes até C50)
phi_l = Q(16.0, "mm")         # barra longitudinal
phi_t = Q(5.0, "mm")          # estribo

# --- 11.3.3.4.3 — momento mínimo de 1a ordem -------------------------------
# A expressão NÃO é homogênea como escrita: o 0,015 carrega METROS e o 0,03 é
# puro (multiplica h em metros). Só fecha com a atribuição declarada abaixo.
caso(
    "NBR6118-11.3.3.4.3-M1d-min",
    "M_1d,min = N_d*(0,015 m + 0,03*h), h em METROS",
    N_d * (Q(0.015, "m") + 0.03 * h_sec),
    "kN*m",
)
caso(
    "MUTANTE-M1d-min-h-em-cm",
    "N_d*(0,015 m + 0,03*h) com h passado como NÚMERO PURO em cm -- DEVE FALHAR",
    lambda: N_d * (Q(0.015, "m") + 0.03 * h_sec.to("cm").magnitude),
    "kN*m",
)
caso(
    "NBR6118-11.3.3.4.3-excentricidade-minima",
    "e_1,min = M_1d,min/N_d = 0,015 m + 0,03*h (independe de N_d)",
    (N_d * (Q(0.015, "m") + 0.03 * h_sec)) / N_d,
    "m",
)

# --- 15.8.2 — esbeltez ------------------------------------------------------
# i = raio de giração MÍNIMO da seção bruta. A Norma NÃO dá i = h/sqrt(12):
# isso é geometria (i = sqrt(I/A)), registrada como derivação geométrica.
I_bruta = b_sec * h_sec ** 3 / 12.0
i_giracao = (I_bruta / A_c) ** 0.5
ell_e = 2.0 * ell                       # 15.8.2: engastado na base, livre no topo
lambda_esb = ell_e / i_giracao
caso("DER-GEOM-raio-de-giracao", "i = sqrt(I/A) = sqrt((b*h^3/12)/(b*h))", i_giracao, "m")
caso("NBR6118-15.8.2-lambda", "lambda = l_e/i, com l_e = 2*l (engastado-livre)",
     lambda_esb, "dimensionless")
caso(
    "MUTANTE-lambda-com-i-ao-quadrado",
    "lambda = l_e/i^2 -- DEVE FALHAR",
    ell_e / i_giracao ** 2,
    "dimensionless",
)
e_1 = Q(0.015, "m") + 0.03 * h_sec
caso("NBR6118-15.8.2-lambda1", "lambda1 = (25 + 12,5*e_1/h)/alpha_b, alpha_b = 1,0",
     Q((25.0 + 12.5 * (e_1 / h_sec).to("dimensionless").magnitude) / 1.0, "dimensionless"),
     "dimensionless")

# --- 8.2.10.1 + 8.3.5/8.3.6 + 12.3.3/12.4.1 — derivação de N_Rd0 -----------
eta_c = 1.0 if f_ck.magnitude <= 40.0 else (40.0 / f_ck.magnitude) ** (1.0 / 3.0)
sigma_c_pico = 0.85 * eta_c * f_cd                       # 8.2.10.1 em eps = eps_c2
sigma_s2 = min((E_s * eps_c2).to("MPa"), f_yd.to("MPa"))  # 8.3.6 + 8.3.5 + 12.3.1
A_s = Q(3.6, "cm**2")                                     # >= A_s,min (ver abaixo)
caso("NBR6118-8.2.10.1-sigma-c-em-eps-c2",
     "sigma_c(eps_c2) = 0,85*eta_c*f_cd*[1-(1-1)^n] = 0,85*eta_c*f_cd",
     0.85 * eta_c * f_cd * (1.0 - (1.0 - eps_c2 / eps_c2) ** 2), "MPa")
caso("DER-NRd0-parcela-concreto", "0,85*eta_c*f_cd*A_c", sigma_c_pico * A_c, "kN")
caso("DER-NRd0-parcela-aco", "A_s*sigma_s2, sigma_s2 = min(E_s*eps_c2, f_yd)",
     A_s * sigma_s2, "kN")
caso("DER-NRd0-compressao-centrada",
     "N_Rd0 = 0,85*eta_c*f_cd*A_c + A_s*min(E_s*eps_c2, f_yd)",
     sigma_c_pico * A_c + A_s * sigma_s2, "kN")
caso(
    "MUTANTE-NRd0-sem-sigma-s2",
    "0,85*eta_c*f_cd*A_c + A_s (parcela do aço sem tensão) -- DEVE FALHAR",
    lambda: sigma_c_pico * A_c + A_s,
    "kN",
)
caso(
    "MUTANTE-NRd0-com-Ac-linear",
    "0,85*eta_c*f_cd*h (A_c trocada por h) -- DEVE FALHAR",
    sigma_c_pico * h_sec,
    "kN",
)

# --- 17.3.5.3 — armaduras longitudinais limites ----------------------------
caso("NBR6118-17.3.5.3.1-As-min-parcela-forca", "0,15*N_d/f_yd", 0.15 * N_d / f_yd, "cm**2")
caso("NBR6118-17.3.5.3.1-As-min-parcela-geometrica", "0,004*A_c", 0.004 * A_c, "cm**2")
caso("NBR6118-17.3.5.3.2-As-max", "0,08*A_c", 0.08 * A_c, "cm**2")
caso(
    "MUTANTE-As-min-com-fyk-no-lugar-de-N",
    "0,15*f_yd/N_d (invertido) -- DEVE FALHAR",
    lambda: 0.15 * f_yd / N_d,
    "cm**2",
)

# --- 18.4.3 — estribos ------------------------------------------------------
# s_max = 90000*(phi_t^2/phi)*(1/f_yk): o 90000 carrega MPa para a expressão
# fechar em milímetros. É a atribuição declarada.
caso(
    "NBR6118-18.4.3-s-max-estribo-fino",
    "s_max = 90000 MPa*(phi_t^2/phi)/f_yk",
    Q(90000.0, "MPa") * (phi_t ** 2 / phi_l) / f_yk,
    "mm",
)
caso(
    "MUTANTE-18.4.3-s-max-com-raiz",
    "s_max = 90000 MPa*sqrt(phi_t^2/phi)/f_yk (o que a camada de texto sugere) "
    "-- DEVE FALHAR",
    Q(90000.0, "MPa") * (phi_t ** 2 / phi_l) ** 0.5 / f_yk,
    "mm",
)

# --- 9.4.2.4/9.4.2.5/9.5.2.3 — ancoragem e emenda por traspasse -------------
eta_1, eta_2, eta_3 = 2.25, 1.0, 1.0          # 9.3.2.1 (CA-50, boa aderência, phi<32)
f_ctk_inf = 0.7 * Q(0.30 * 25.0 ** (2.0 / 3.0), "MPa")   # 8.2.5
f_ctd = f_ctk_inf / gamma_c
f_bd = eta_1 * eta_2 * eta_3 * f_ctd
l_b = (phi_l / 4.0) * (f_yd / f_bd)
caso("NBR6118-9.3.2.1-fbd", "f_bd = eta1*eta2*eta3*f_ctd", f_bd, "MPa")
caso("NBR6118-9.4.2.4-lb", "l_b = (phi/4)*(f_yd/f_bd) >= 25*phi", l_b, "mm")
caso("NBR6118-9.5.2.3-l0c-min", "l_0c,min = max(0,6*l_b, 15*phi, 200 mm)",
     max(0.6 * l_b, (15.0 * phi_l).to("mm"), Q(200.0, "mm")), "mm")
caso(
    "MUTANTE-lb-sem-dividir-por-fbd",
    "l_b = (phi/4)*f_yd (f_bd faltando) -- DEVE FALHAR",
    (phi_l / 4.0) * f_yd,
    "mm",
)

# --- 13.2.3 — coeficiente adicional gamma_n --------------------------------
caso(
    "NBR6118-13.2.3-gamma-n",
    "gamma_n = 1,95 - 0,05*b, b em CENTÍMETROS",
    "EMPIRICA",
    "O 1,95 e puro e o 0,05 carrega 1/cm. Passar b em metros da 1,94 (proximo "
    "de 1,00 so por coincidencia de faixa) sem nenhum erro dimensional "
    "detectavel. Exige guarda de unidade explicita e faixa 14 cm <= b < 19 cm.",
)


# ===========================================================================
# 7. ELU DE SOLICITAÇÕES NORMAIS DO PILARETE — flexão composta OBLÍQUA
#    NBR 6118:2023 17.2.1, 17.2.5, 11.3.3.4.3/Figura 11.3, 17.2.2/Figura 17.1
#    (backlog #13, rodada 3; ruleset v12)
#
#    AVISO DE ALCANCE, escrito porque é a limitação central desta seção: as
#    deformações (eps_c2, eps_cu, eps_s, 10 ‰) são ADIMENSIONAIS e o expoente
#    alpha também. O pint NÃO pega troca de expoente (2 <-> 1,2), não pega
#    troca de eixo (h <-> b) e não pega troca de polo. Esses três erros só são
#    pegos pelo teste numérico do a5/a7 e pelo sanity check do a2 — estão
#    registrados como tal em ruleset.yaml, e é por isso que existem os casos
#    EMPIRICA no fim desta seção.
# ===========================================================================
M_Rd_xx = Q(63.95, "kN*m")     # varredura numérica, N_Sd = 1000 kN, 30x30 C25
M_Rd_yy = Q(63.95, "kN*m")     # seção quadrada -> igual
M_Sd_x = Q(24.0, "kN*m")       # = M_1d,min,xx
M_Sd_y = Q(24.0, "kN*m")       # = M_1d,min,yy
alpha_interacao = 1.2          # 17.2.5, seção retangular
eps_cu_ = 3.5e-3
eps_c2_ = 2.0e-3

# --- 17.2.5 — expressão de interação (lado RESISTENTE) ---------------------
caso(
    "NBR6118-17.2.5-interacao",
    "(M_Rd,x/M_Rd,xx)^alpha + (M_Rd,y/M_Rd,yy)^alpha",
    (M_Sd_x / M_Rd_xx) ** alpha_interacao + (M_Sd_y / M_Rd_yy) ** alpha_interacao,
    "dimensionless",
)
caso(
    "MUTANTE-17.2.5-normal-no-lugar-do-momento",
    "(N_Sd/M_Rd,xx)^alpha + ... (força normal no numerador) -- DEVE FALHAR",
    lambda: (N_d / M_Rd_xx) ** alpha_interacao + (M_Sd_y / M_Rd_yy) ** alpha_interacao,
    "dimensionless",
)
caso(
    "MUTANTE-17.2.5-expoente-no-momento",
    "M_Rd,x^alpha/M_Rd,xx + ... (expoente aplicado ao momento, não à razão) "
    "-- DEVE FALHAR",
    lambda: M_Sd_x ** alpha_interacao / M_Rd_xx,
    "dimensionless",
)

# --- Figura 11.3 — envoltória mínima de 1a ordem (lado SOLICITANTE) --------
M1min_xx = N_d * (Q(0.015, "m") + 0.03 * h_sec)   # usa h  (11.3.3.4.3/Fig 11.3)
M1min_yy = N_d * (Q(0.015, "m") + 0.03 * b_sec)   # usa b  (11.3.3.4.3/Fig 11.3)
caso(
    "NBR6118-Fig11.3-elipse-minima",
    "(M_1d,min,x/M_1d,min,xx)^2 + (M_1d,min,y/M_1d,min,yy)^2",
    (M_Sd_x / M1min_xx) ** 2 + (M_Sd_y / M1min_yy) ** 2,
    "dimensionless",
)
caso(
    "DER-inclusao-envoltorias-forma-fechada-alpha-1",
    "sqrt((M_1d,min,xx/M_Rd,xx)^2 + (M_1d,min,yy/M_Rd,yy)^2) <= 1 "
    "(máximo EXATO da interação alpha = 1 sobre a elipse)",
    ((M1min_xx / M_Rd_xx) ** 2 + (M1min_yy / M_Rd_yy) ** 2) ** 0.5,
    "dimensionless",
)
caso(
    "DER-inclusao-envoltorias-sem-a-raiz-NAO-PEGO",
    "(M_1d,min,xx/M_Rd,xx)^2 + (M_1d,min,yy/M_Rd,yy)^2 — esquecer a RAIZ",
    "EMPIRICA",
    "Continua adimensional: o pint NAO pega. E pior que inocuo, e do lado "
    "INSEGURO quando as duas parcelas sao menores que 1 (0,2817 contra 0,5307 "
    "no sanity check do a2, isto e, 47% do valor correto). So o teste numerico "
    "contra o maximo por varredura da elipse pega. Obrigatorio no GATE 3.",
)

# --- Figura 17.1 — posição do polo C ---------------------------------------
caso(
    "NBR6118-Fig17.1-polo-C",
    "y_C = (eps_cu - eps_c2)*h/eps_cu, medido da borda COMPRIMIDA",
    (eps_cu_ - eps_c2_) * h_sec / eps_cu_,
    "m",
)
caso(
    "MUTANTE-Fig17.1-polo-C-com-h-ao-quadrado",
    "y_C = (eps_cu - eps_c2)*h^2/eps_cu -- DEVE FALHAR",
    (eps_cu_ - eps_c2_) * h_sec ** 2 / eps_cu_,
    "m",
)

# --- varredura de equilíbrio: N_Rd(x) e M_Rd(x) ----------------------------
# Parcela genérica de uma faixa de concreto e de uma camada de armadura, com o
# braço de alavanca medido ao CENTROIDE da seção (17.2.4.1 com a redação da
# Em1:2026).
dy_faixa = Q(0.075, "mm")             # 4000 faixas em 30 cm
sigma_c_faixa = 0.85 * eta_c * f_cd   # tensão na faixa (8.2.10.1)
braco = h_sec / 2.0 - Q(0.05, "m")
caso("DER-MRd-varredura-parcela-N-concreto", "sigma_c*b*dy",
     sigma_c_faixa * b_sec * dy_faixa, "kN")
caso("DER-MRd-varredura-parcela-M-concreto", "sigma_c*b*dy*(h/2 - y)",
     sigma_c_faixa * b_sec * dy_faixa * braco, "kN*m")
caso("DER-MRd-varredura-parcela-M-aco", "A_s*sigma_s*(h/2 - y)",
     A_s * sigma_s2 * braco, "kN*m")
caso(
    "MUTANTE-MRd-varredura-sem-braco",
    "sigma_c*b*dy somado a M (parcela de força somada ao momento) -- DEVE FALHAR",
    lambda: sigma_c_faixa * b_sec * dy_faixa * braco + A_s * sigma_s2,
    "kN*m",
)

# --- o que o pint NÃO pega nesta seção -------------------------------------
caso(
    "NBR6118-17.2.5-alpha-troca-de-expoente",
    "alpha = 1,2 (17.2.5, RESISTENTE) trocado por 2 (Figura 11.3, SOLICITANTE) "
    "ou por 1,5 (alpha de 17.3.1, mesma PÁGINA 125)",
    "EMPIRICA",
    "Expoente e deformacoes sao ADIMENSIONAIS: qualquer troca de expoente passa "
    "pela checagem dimensional sem erro. So o teste numerico pega. Ordem "
    "verificada pelo a2 em 20.000 pares aleatorios: canto >= alpha=1 >= "
    "alpha=1,2, sem excecao.",
)
caso(
    "NBR6118-Fig11.3-cruzamento-eixo-dimensao",
    "M_1d,min,xx usa h e M_1d,min,yy usa b (cruzado, conforme a figura)",
    "EMPIRICA",
    "Trocar h por b mantem kN*m e passa pelo pint. Em secao quadrada nem muda o "
    "numero. Sanity check do a2 em secao 20x40 e N_d = 800 kN: a troca leva o "
    "indice de inclusao de 0,5114 para 0,6113 (20%). So teste numerico com "
    "secao NAO quadrada pega.",
)


# ===========================================================================
# 8. ELU DE FORÇA CORTANTE DO PILARETE — NBR 6118:2023 17.4.1 a 17.4.2.3,
#    18.3.3.2 (+ Em1:2026) e a classificação de 14.4.1
#    (backlog #13, rodada 4; ruleset v13)
#
#    TRÊS GEOMETRIAS, e cada uma existe por um motivo:
#      A) 30x30 cm, ell = 1,00 m, C25, CA-50, N_d = 1000 kN — a mesma das
#         seções 6 e 7. SATISFAZ 14.4.1 (1,00 >= 3 x 0,30 = 0,90 m) e satisfaz
#         lambda < lambda_1 (23,1 < 35). É o caso em que §17.4 É aplicável.
#      B) 30x30 cm, ell = 0,80 m — satisfaz lambda < lambda_1 (18,5 < 35) e
#         NÃO satisfaz 14.4.1 (2,67 < 3). É a FAIXA B: §17.4 RECUSADO.
#         Existe para provar que a faixa não é hipotética.
#      C) 25x40 cm, ell = 1,25 m — a única classe de seção NÃO QUADRADA que
#         satisfaz as DUAS fronteiras, e por muito pouco (razão 3,125 >= 3;
#         lambda 34,64 < 35). Existe porque em seção quadrada W_1x == W_1y e
#         a ambiguidade de W_1 da decisão V20(3) fica INVISÍVEL.
#
#    AVISO DE ALCANCE: theta, alpha, alpha_v2 e as razões de 14.4.1 são
#    ADIMENSIONAIS; o pint não pega troca de modelo (0,27 <-> 0,54), não pega
#    sen^2 trocado por sen, não pega a razão de 14.4.1 calculada com ell_e em
#    vez de ell e não pega W_1x trocado por W_1y. Casos EMPIRICA no fim.
# ===========================================================================
b_w = Q(30.0, "cm")                     # menor largura da seção (17.4.2.2)
d_util = Q(25.7, "cm")                  # h - (cob + phi_t + phi_l/2) = 30 - 4,3
f_ck_MPa = 25.0
alpha_v2 = 1.0 - f_ck_MPa / 250.0       # 17.4.2.2-a) e 17.4.2.3-a): f_ck em MPa
f_ywd = min(f_yd.to("MPa"), Q(435.0, "MPa"))   # teto de 435 MPa, 17.4.2.2-b)

# --- 14.4.1 — classificação como elemento linear ---------------------------
# A razão usa o COMPRIMENTO LONGITUDINAL REAL (ell), jamais ell_e.
razao_linear_A = (ell / max(h_sec, b_sec)).to("dimensionless")
caso(
    "NBR6118-14.4.1-razao-elemento-linear-geomA",
    "ell/max(b,h) >= 3 -> FAIXA A, 17.4 aplicavel (ell = 1,00 m, 30x30)",
    razao_linear_A,
    "dimensionless",
)
ell_B = Q(0.80, "m")
razao_linear_B = (ell_B / max(h_sec, b_sec)).to("dimensionless")
caso(
    "NBR6118-14.4.1-razao-elemento-linear-geomB-RECUSA",
    "ell/max(b,h) < 3 -> FAIXA B, 17.4 RECUSADO (ell = 0,80 m, 30x30)",
    razao_linear_B,
    "dimensionless",
)
lambda_B = (2.0 * ell_B / (b_sec / math.sqrt(12.0))).to("dimensionless")
caso(
    "NBR6118-15.8.2-lambda-geomB-passa-enquanto-14.4.1-reprova",
    "lambda = 2*ell/(b/sqrt(12)) < 35 na MESMA geometria que 14.4.1 recusa",
    lambda_B,
    "dimensionless",
)
caso(
    "DER-FRONTEIRA-14.4.1-com-15.8.2-engastado-livre",
    "ell/b_min maximo por lambda < 35 com ell_e = 2 ell: 35/(2*sqrt(12))",
    Q(35.0 / (2.0 * math.sqrt(12.0)), "dimensionless"),
    "dimensionless",
)
caso(
    "MUTANTE-14.4.1-com-ell-e-no-lugar-de-ell",
    "ell_e/max(b,h) (dobra a razão no caso engastado-livre) -- passa no pint",
    "EMPIRICA",
    "A razao e ADIMENSIONAL nas duas leituras: trocar ell por ell_e = 2*ell "
    "dobra o valor (3,33 -> 6,67 na geometria A) e faz um pilarete de 45 cm "
    "de altura ser classificado como elemento linear. Erro do lado INSEGURO "
    "por CITACAO (aplica 17.4 fora de dominio) e invisivel ao pint. So teste "
    "numerico com ell entre 1,5 e 3,0 vezes a maior dimensao pega — a "
    "geometria B (ell = 0,80 m) existe para isso.",
)

# --- 17.4.1.1.1 — armadura transversal mínima por RESISTÊNCIA --------------
f_ct_m = Q(0.30 * f_ck_MPa ** (2.0 / 3.0), "MPa")     # 8.2.5
rho_sw_min = 0.2 * f_ct_m / f_yk                       # f_ywk = f_yk = 500 MPa
caso("NBR6118-17.4.1.1.1-rho-sw-min", "rho_sw,min = 0,2*f_ct,m/f_ywk",
     rho_sw_min.to("dimensionless"), "dimensionless")
A_sw_por_s_min = rho_sw_min * b_w * 1.0                # sen(alpha=90) = 1
caso("NBR6118-17.4.1.1.1-Asw-sobre-s-min",
     "(A_sw/s)_min = rho_sw,min*b_w*sen(alpha) [cm2 por metro]",
     (A_sw_por_s_min * Q(100.0, "cm")).to("cm**2"), "cm**2")
caso(
    "MUTANTE-17.4.1.1.1-sen-alpha-no-numerador",
    "rho_sw = A_sw*sen(alpha)/(b_w*s) -- passa no pint",
    "EMPIRICA",
    "sen(alpha) e ADIMENSIONAL: po-lo no numerador em vez do denominador "
    "passa pela checagem dimensional. Para estribo vertical (alpha = 90) nem "
    "muda o numero. So estribo inclinado a 45 graus pega (fator 1,41). A "
    "camada de texto do PDF devolve a equacao embaralhada e sugere isso; a "
    "leitura visual do a2 na p. impressa 134 confirma sen NO DENOMINADOR.",
)

# --- 17.4.2.2 — Modelo I ---------------------------------------------------
V_Rd2_I = 0.27 * alpha_v2 * f_cd * b_w * d_util
caso("NBR6118-17.4.2.2-VRd2-modelo-I", "V_Rd2 = 0,27*alpha_v2*f_cd*b_w*d",
     V_Rd2_I.to("kN"), "kN")
caso(
    "MUTANTE-VRd2-com-perimetro-no-lugar-de-bw-d",
    "0,27*alpha_v2*f_cd*u_0 (a forma de 19.5.3.1, que e TENSAO) -- DEVE FALHAR",
    lambda: (0.27 * alpha_v2 * f_cd * (2.0 * (b_w + h_sec.to("cm")))).to("kN"),
    "kN",
)
# Estribo ADOTADO: 2 ramos phi 5,0 mm a cada 12,5 cm.
#   A_sw = 2 x 0,1963 = 0,3927 cm2 ; A_sw/s = 0,03142 cm2/cm = 3,142 cm2/m
# Escolhido por SATISFAZER (A_sw/s)_min = 0,03078 cm2/cm de 17.4.1.1.1 — o
# valor 0,20 cm2/cm da rodada anterior era 6,4x maior que este e NAO
# correspondia ao estribo descrito no proprio comentario (defeito de fixture
# encontrado pelo a2 ao reauditar o proprio trabalho; V_sw saia 201 kN, valor
# implausivel para um pilarete 30x30).
A_sw_s = Q(0.031416, "cm**2/cm")
caso("SANITY-estribo-adotado-satisfaz-17.4.1.1.1",
     "(A_sw/s)_adotado - (A_sw/s)_min, 2 phi 5,0 c/12,5 cm (deve ser >= 0)",
     ((A_sw_s - A_sw_por_s_min) * Q(100.0, "cm")).to("cm**2"), "cm**2")
V_sw_I = A_sw_s * 0.9 * d_util * f_ywd * (1.0 + 0.0)   # alpha = 90 graus
caso("NBR6118-17.4.2.2-Vsw-modelo-I",
     "V_sw = (A_sw/s)*0,9*d*f_ywd*(sen a + cos a), a = 90 graus",
     V_sw_I.to("kN"), "kN")
caso(
    "MUTANTE-Vsw-sem-dividir-por-s",
    "A_sw*0,9*d*f_ywd (espaçamento faltando) -- DEVE FALHAR",
    lambda: (Q(0.3927, "cm**2") * 0.9 * d_util * f_ywd).to("kN"),
    "kN",
)
f_ctk_inf_25 = 0.7 * f_ct_m             # 8.2.5; DECISÃO V20(1): sempre o INF
f_ctd_25 = f_ctk_inf_25 / gamma_c
V_c0 = 0.6 * f_ctd_25 * b_w * d_util
caso("NBR6118-17.4.2.2-Vc0", "V_c0 = 0,6*f_ctd*b_w*d, f_ctd = f_ctk,inf/gamma_c",
     V_c0.to("kN"), "kN")
caso("SANITY-tensao-de-referencia-Vc0",
     "V_c0/(b_w*d) — faixa plausivel de tensao de concreto ao cortante",
     (V_c0 / (b_w * d_util)).to("MPa"), "MPa")
caso("SANITY-tensao-de-esmagamento-VRd2",
     "V_Rd2/(b_w*d) = 0,27*alpha_v2*f_cd — NAO confundir com a faixa de tau_Rd",
     (V_Rd2_I / (b_w * d_util)).to("MPa"), "MPa")

# --- 17.4.2.2 — M_0 e a majoração de V_c na flexo-compressão ---------------
# DECISÃO V20(2): o N do numerador de M_0 é o da combinação com gamma_f = 1,0,
# como a Norma escreve ("essa tensão calculada com valores de gamma_f e gamma_p
# iguais a 1,0 e 0,9"). É ENTRADA DECLARADA: é PROIBIDO obtê-lo dividindo N_d
# por um gamma_f suposto — o software não conhece a composição da combinação.
# Aqui 714 kN é DECLARADO (corresponde a N_d = 1000 kN numa combinação em que
# todas as ações têm gamma_f = 1,4, mas o software não faz essa conta).
N_gf1 = Q(714.0, "kN")
W_1 = b_sec.to("cm") * h_sec.to("cm") ** 2 / 6.0      # 4500 cm3 (secao quadrada)
M_0 = N_gf1 * (W_1 / A_c.to("cm**2"))
caso("NBR6118-17.4.2.2-M0-concreto-armado",
     "M_0 = N*(W_1/A_c), com P_d = 0 (concreto armado) e N a gamma_f = 1,0",
     M_0.to("kN*m"), "kN*m")
caso(
    "MUTANTE-M0-sem-dividir-por-Ac",
    "M_0 = N*W_1 (A_c faltando) -- DEVE FALHAR",
    lambda: (N_gf1 * W_1).to("kN*m"),
    "kN*m",
)
# Caso A1 — M_Sd,max = M_1d,min = 24 kN.m: o TETO 2*V_c0 GOVERNA. Este caso
# MASCARA o erro de V20(2) (as duas leituras estouram o teto) e por isso NAO
# serve sozinho como fixture de validação.
M_Sd_max_A1 = Q(24.0, "kN*m")
V_c_A1 = min((V_c0 * (1.0 + (M_0 / M_Sd_max_A1).to("dimensionless"))).to("kN"),
             (2.0 * V_c0).to("kN"))
caso("NBR6118-17.4.2.2-Vc-flexo-compressao-A1-teto-governa",
     "V_c = min(V_c0*(1 + M_0/M_Sd,max), 2*V_c0), M_Sd,max = 24 kN.m",
     V_c_A1, "kN")
# Caso A2 — M_Sd,max = 60 kN.m: o teto NÃO governa e a decisão V20(2) fica
# VISÍVEL (94,63 kN com gamma_f = 1,0 contra 108,77 kN com N_d majorado,
# +14,9 % do lado INSEGURO). É ESTE o caso que o a7 tem de usar.
M_Sd_max_A2 = Q(60.0, "kN*m")
V_c_A2 = min((V_c0 * (1.0 + (M_0 / M_Sd_max_A2).to("dimensionless"))).to("kN"),
             (2.0 * V_c0).to("kN"))
caso("NBR6118-17.4.2.2-Vc-flexo-compressao-A2-teto-nao-governa",
     "V_c com M_Sd,max = 60 kN.m (fixture DISCRIMINANTE de V20(2))",
     V_c_A2, "kN")
V_c_A2_errado = min(
    (V_c0 * (1.0 + (N_d * (W_1 / A_c.to("cm**2")) / M_Sd_max_A2)
             .to("dimensionless"))).to("kN"),
    (2.0 * V_c0).to("kN"))
caso("SANITY-V20-2-diferenca-entre-as-duas-leituras",
     "V_c(N_d majorado) - V_c(N a gamma_f = 1,0) no caso A2 (lado INSEGURO)",
     (V_c_A2_errado - V_c_A2).to("kN"), "kN")
caso("NBR6118-17.4.2.1-VRd3-modelo-I", "V_Rd3 = V_c + V_sw (caso A2)",
     (V_c_A2 + V_sw_I).to("kN"), "kN")

# --- V20(3): W_1 sob flexão oblíqua, na geometria C (25x40) ----------------
b_C, h_C = Q(25.0, "cm"), Q(40.0, "cm")
A_c_C = b_C * h_C
ell_C = Q(1.25, "m")
caso("NBR6118-14.4.1-razao-elemento-linear-geomC",
     "ell/max(b,h) = 1,25/0,40 (FAIXA A, por pouco)",
     (ell_C / h_C.to("m")).to("dimensionless"), "dimensionless")
caso("NBR6118-15.8.2-lambda-geomC",
     "lambda = 2*ell/(b/sqrt(12)) (< 35, por pouco)",
     (2.0 * ell_C / (b_C.to("m") / math.sqrt(12.0))).to("dimensionless"),
     "dimensionless")
W_1x_C = b_C * h_C ** 2 / 6.0        # flexão no plano de h
W_1y_C = h_C * b_C ** 2 / 6.0        # flexão no plano de b
N_gf1_C = Q(857.0, "kN")
M_0x_C = N_gf1_C * (W_1x_C / A_c_C)
M_0y_C = N_gf1_C * (W_1y_C / A_c_C)
caso("NBR6118-17.4.2.2-M0-fibra-x-geomC", "M_0 com W_1x = b*h^2/6",
     M_0x_C.to("kN*m"), "kN*m")
caso("NBR6118-17.4.2.2-M0-fibra-y-geomC", "M_0 com W_1y = h*b^2/6",
     M_0y_C.to("kN*m"), "kN*m")
M_Sd_x_C, M_Sd_y_C = Q(90.0, "kN*m"), Q(70.0, "kN*m")
d_C = h_C - Q(4.3, "cm")                       # cortante no plano de h
V_c0_C = 0.6 * f_ctd_25 * b_C * d_C
razao_x = (M_0x_C / M_Sd_x_C).to("dimensionless")
razao_y = (M_0y_C / M_Sd_y_C).to("dimensionless")
V_c_C_conservador = min((V_c0_C * (1.0 + min(razao_x, razao_y))).to("kN"),
                        (2.0 * V_c0_C).to("kN"))
V_c_C_otimista = min((V_c0_C * (1.0 + max(razao_x, razao_y))).to("kN"),
                     (2.0 * V_c0_C).to("kN"))
caso("DER-V20-3-Vc-com-W1-conservador-geomC",
     "V_c com o MENOR M_0/M_Sd,max entre as duas fibras (decisao V20(3))",
     V_c_C_conservador, "kN")
caso("SANITY-V20-3-diferenca-entre-as-duas-fibras",
     "V_c(fibra otimista) - V_c(fibra conservadora) na geometria C",
     (V_c_C_otimista - V_c_C_conservador).to("kN"), "kN")

# --- 17.4.2.3 — Modelo II, a fronteira e a NÃO-fronteira -------------------
theta_45 = Q(45.0, "degree")
sen2_45 = math.sin(theta_45.to("radian").magnitude) ** 2
cotg_45 = 1.0 / math.tan(theta_45.to("radian").magnitude)
cotg_alpha = 0.0                        # alpha = 90 graus
V_Rd2_II_45 = (0.54 * alpha_v2 * f_cd * b_w * d_util * sen2_45
               * (cotg_alpha + cotg_45))
caso("NBR6118-17.4.2.3-VRd2-modelo-II-45",
     "V_Rd2 = 0,54*alpha_v2*f_cd*b_w*d*sen^2(theta)*(cotg a + cotg theta)",
     V_Rd2_II_45.to("kN"), "kN")
caso("NBR6118-17.4-fronteira-VRd2-modelo-I-igual-modelo-II",
     "V_Rd2(II) - V_Rd2(I) em theta = 45 e alpha = 90 (deve ser ~0)",
     (V_Rd2_II_45 - V_Rd2_I).to("kN"), "kN")
theta_30 = Q(30.0, "degree")
sen2_30 = math.sin(theta_30.to("radian").magnitude) ** 2
cotg_30 = 1.0 / math.tan(theta_30.to("radian").magnitude)
V_Rd2_II_30 = (0.54 * alpha_v2 * f_cd * b_w * d_util * sen2_30
               * (cotg_alpha + cotg_30))
caso("NBR6118-17.4.2.3-VRd2-modelo-II-30",
     "V_Rd2(II) em theta = 30 graus (menor que o do Modelo I)",
     V_Rd2_II_30.to("kN"), "kN")
V_sw_II_30 = A_sw_s * 0.9 * d_util * f_ywd * (cotg_alpha + cotg_30) * 1.0
caso("NBR6118-17.4.2.3-Vsw-modelo-II-30",
     "V_sw = (A_sw/s)*0,9*d*f_ywd*(cotg a + cotg theta)*sen a, theta = 30",
     V_sw_II_30.to("kN"), "kN")
# DERIVAÇÃO: a Norma dá os dois extremos de V_c1 e a palavra "interpolando-se
# linearmente", mas NÃO escreve a expressão fechada. Escrevê-la é DERIVAÇÃO.
V_Sd_ = Q(120.0, "kN")
V_c1_45 = (V_c0 if V_Sd_ <= V_c0 else
           V_c0 * ((V_Rd2_II_45 - V_Sd_) / (V_Rd2_II_45 - V_c0)).to("dimensionless"))
caso("DER-NBR6118-17.4.2.3-Vc1-interpolacao-linear",
     "V_c1 = V_c0*(V_Rd2 - V_Sd)/(V_Rd2 - V_c0), theta = 45, V_Sd = 120 kN",
     V_c1_45.to("kN"), "kN")
caso("SANITY-modelo-II-NAO-coincide-com-I-em-VRd3",
     "V_c1(theta=45) - V_c0: o Modelo II e MAIS conservador em V_Rd3 mesmo "
     "na fronteira em que V_Rd2 coincide (deve ser < 0)",
     (V_c1_45 - V_c0).to("kN"), "kN")
caso(
    "MUTANTE-modelo-II-sem-sen-ao-quadrado",
    "0,54*...*sen(theta)*(cotg a + cotg theta) -- passa no pint",
    "EMPIRICA",
    "sen^2(theta) e ADIMENSIONAL: trocar por sen(theta) leva V_Rd2(II) de "
    "0,27 para 0,382*alpha_v2*f_cd*b_w*d em theta = 45 graus (+41%, lado "
    "INSEGURO) sem nenhum erro dimensional. A propriedade de fronteira "
    "V_Rd2(II) == V_Rd2(I) em theta = 45 / alpha = 90 e o teste que pega.",
)

# --- 18.3.3.2 (p. impressas 150-151) x 18.4.3 (p. impressa 154) ------------
s_max_1833 = (min(0.6 * d_util.to("mm"), Q(300.0, "mm"))
              if V_Sd_ <= 0.67 * V_Rd2_I.to("kN")
              else min(0.3 * d_util.to("mm"), Q(200.0, "mm")))
caso("NBR6118-18.3.3.2-s-max", "s_max = min(0,6d, 300 mm) se V_d <= 0,67 V_Rd2",
     s_max_1833, "mm")
s_t_max_1833 = (min(d_util.to("mm"), Q(800.0, "mm"))
                if V_Sd_ <= 0.20 * V_Rd2_I.to("kN")
                else min(0.6 * d_util.to("mm"), Q(350.0, "mm")))
caso("NBR6118-18.3.3.2-s-t-max",
     "s_t,max = min(0,6d, 350 mm) se V_d > 0,20 V_Rd2", s_t_max_1833, "mm")
s_max_1843 = min(Q(200.0, "mm"), b_sec.to("mm"), (12.0 * phi_l).to("mm"))
caso("NBR6118-18.4.3-s-max-pilar", "s = min(200 mm, b_min, 12 phi) (CA-50)",
     s_max_1843, "mm")
caso("DER-COMPOSICAO-18.4.3-com-18.3.3.2-TETOS",
     "teto de espacamento = MENOR dos dois limites (18.4.3, ultimo paragrafo)",
     min(s_max_1833, s_max_1843), "mm")
caso("DER-COMPOSICAO-18.4.3-com-18.3.3.2-PISOS",
     "piso de diametro do estribo = MAIOR dos dois: max(5 mm, phi/4) e 5 mm",
     max(max(Q(5.0, "mm"), (phi_l / 4.0).to("mm")), Q(5.0, "mm")), "mm")
caso("NBR6118-18.3.3.2-phi-t-teto-b-sobre-10",
     "phi_t <= b_w/10 (18.3.3.2; b_w lido como menor dimensao do pilarete)",
     (b_sec.to("mm") / 10.0 - phi_t).to("mm"), "mm")
caso(
    "NBR6118-Em1-18.3.3.2-phi-long-maior-que-phi-t",
    "phi_longitudinal - phi_estribo nas barras de canto (Em1:2026, >= 0)",
    (phi_l - phi_t).to("mm"),
    "mm",
)
caso("SANITY-espacamento-adotado-abaixo-do-teto-composto",
     "teto composto - s adotado (125 mm) — deve ser >= 0",
     (min(s_max_1833, s_max_1843) - Q(125.0, "mm")).to("mm"), "mm")

# --- 7.4.7.5 — o CRUZAMENTO cobrimento x posicoes das barras ---------------
# A identidade MISTURA UNIDADES: d' entra em METROS (é posição de barra, como
# h e b) e phi_t/phi_l em MILÍMETROS. Era exatamente aqui que um fator 1000
# trocado passaria despercebido — o resultado continua "um comprimento" e
# nenhum teste de veredito o pegaria, porque o número errado só apareceria
# como um cobrimento implausível. Com d' = 58 mm, phi_t = 5 mm e phi = 16 mm,
# c = 58 - 5 - 8 = 45 mm, que é o piso da nota (d) da Tabela 7.2.
d_linha_barra = Q(0.058, "m")   # posição declarada do eixo da barra
caso("NBR6118-7.4.7.5-cobrimento-implicito-pelas-barras",
     "c = d' - phi_t - phi_l/2, com d' em METROS e phi em MILIMETROS "
     "(cobrimento à face externa do ESTRIBO)",
     (d_linha_barra.to("mm") - phi_t - phi_l / 2.0).to("mm"), "mm")
caso("SANITY-cobrimento-implicito-nao-menor-que-o-declarado",
     "c_implicito - c_declarado (45 mm) — deve ser >= 0, senao RECUSA",
     (d_linha_barra.to("mm") - phi_t - phi_l / 2.0 - Q(45.0, "mm")).to("mm"),
     "mm")

# --- 17.4.1.1.2-a) — o ramo que a guarda de 13.2.3 torna inalcançável ------
caso("NBR6118-17.4.1.1.2-a-bw-maior-que-5d",
     "b_w - 5*d (se > 0, tratar como laje por 19.4; com h <= 5*b de 13.2.3 "
     "nunca ocorre — deve ser NEGATIVO)",
     (b_w - 5.0 * d_util).to("cm"), "cm")

# --- o que o pint NÃO pega nesta seção -------------------------------------
caso(
    "NBR6118-17.4.1.1.2-c-qual-f-ctk",
    "f_ctk sem sufixo em 17.4.1.1.2-c): f_ctk,inf x f_ctk,sup",
    "EMPIRICA",
    "Os dois sao tensoes e passam identicamente pelo pint. f_ctk,sup e 86% "
    "maior que f_ctk,inf e DISPENSA a armadura minima em pilarete que a "
    "leitura conservadora manda armar. DECISAO V20(1) do a2: sempre "
    "f_ctk,inf. So teste numerico com a constante trocada pega.",
)
caso(
    "NBR6118-17.4.2.2-M0-nivel-de-carregamento",
    "N a gamma_f = 1,0 (numerador de M_0) x N_d majorado",
    "EMPIRICA",
    "As duas leituras dao kN e passam pelo pint. DECISAO V20(2) do a2: "
    "gamma_f = 1,0, que e o que a Norma ESCREVE, e o valor e ENTRADA "
    "DECLARADA — proibido dividir N_d por gamma_f suposto. Sem o valor "
    "declarado o software NAO majora (V_c = V_c0). O caso A1 (M_Sd,max = "
    "24 kN.m) MASCARA o erro porque as duas leituras estouram o teto de "
    "2*V_c0; so o caso A2 (M_Sd,max = 60 kN.m) discrimina.",
)
caso(
    "NBR6118-17.4.2.2-W1-fibra-mais-tracionada",
    "W_1 sob flexao obliqua: duas fibras candidatas na secao retangular",
    "EMPIRICA",
    "W_1x = b*h^2/6 e W_1y = h*b^2/6 tem a MESMA dimensao (cm3) e em secao "
    "QUADRADA o MESMO valor — a geometria A (30x30) nao pega nada. DECISAO "
    "V20(3) do a2: calcular a razao M_0/M_Sd,max nas duas direcoes e adotar "
    "a MENOR (menor V_c, mais estribo). A geometria C (25x40) existe para "
    "tornar a escolha visivel.",
)
caso(
    "NBR6118-17.4-cortante-BIAXIAL-sem-regra-na-Norma",
    "H_x != 0 e H_y != 0 simultaneos: 17.4 e escrito para UM V_Sd em b_w*d",
    "EMPIRICA",
    "Nenhuma checagem dimensional detecta a composicao inventada de duas "
    "cortantes (sqrt(Vx^2+Vy^2), interacao linear, verificacao por direcao "
    "isolada): todas dao kN. A Norma escreve 17.2.5 para MOMENTOS obliquos e "
    "NADA para cortante obliqua. DECISAO do a2: RECUSA do cisalhamento "
    "quando as duas componentes de H sao nao nulas.",
)
caso(
    "NBR6118-17.4.2.3-menor-estrito-em-2-Vc1",
    "Modelo I escreve '<= 2 V_c0' e Modelo II escreve '< 2 V_c1'",
    "EMPIRICA",
    "Diferenca tipografica REAL, conferida por leitura visual do a2 nas p. "
    "impressas 137 e 139. Nenhuma checagem dimensional a alcanca e a "
    "diferenca numerica tem medida nula. DECISAO do a2: implementar os dois "
    "como teto nao estrito (min com 2*V_c1), transcrevendo a tipografia como "
    "esta na fonte.",
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
            bruto = valor() if callable(valor) else valor
            convertido = bruto.to(esperado)
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
