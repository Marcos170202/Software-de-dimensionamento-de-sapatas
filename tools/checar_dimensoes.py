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
