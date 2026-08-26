"""
materiais.py
------------
Propriedades de concreto e aço conforme ABNT NBR 6118:2023.

Convenção de unidades do pacote:
    força .............. kN
    comprimento ........ m
    tensão (solo) ...... kPa
    resistência (mat.).. MPa  (convertida internamente quando necessário)
    momento ............ kN.m
"""
from __future__ import annotations

import math
from dataclasses import dataclass

MPA_PARA_KPA = 1000.0

# alpha_E - NBR 6118:2023, 8.2.8, por natureza do agregado graúdo
ALPHA_E_POR_AGREGADO = {
    "basalto": 1.2, "diabasio": 1.2,
    "granito": 1.0, "gnaisse": 1.0,
    "calcario": 0.9,
    "arenito": 0.7,
}


@dataclass
class Concreto:
    """Concreto estrutural (NBR 6118:2023, Seção 8.2)."""

    fck: float = 25.0            # MPa - resistência característica à compressão
    gamma_c: float = 1.4         # NBR 6118, Tab. 12.1 - coef. de ponderação (ELU)
    peso_especifico: float = 25.0  # kN/m3 - NBR 6120 (concreto armado)
    agregado: str = "granito"    # NBR 6118, 8.2.8 - natureza do agregado graúdo,
                                  # define alpha_E (afeta Eci/Ecs, logo a rigidez
                                  # usada em rigidez.py/grelha.py). "granito"
                                  # (alpha_E=1,0) é adotado como padrão por ser o
                                  # mais comum na falta de informação do projeto —
                                  # NÃO é um valor da norma, é uma escolha deste
                                  # software; o engenheiro deve confirmar o
                                  # agregado real do traço.

    def __post_init__(self) -> None:
        if not 20.0 <= self.fck <= 90.0:
            raise ValueError("fck fora do campo de aplicação da NBR 6118 (20 a 90 MPa).")
        if self.agregado not in ALPHA_E_POR_AGREGADO:
            raise ValueError(
                f"agregado {self.agregado!r} desconhecido; use um de "
                f"{sorted(ALPHA_E_POR_AGREGADO)}.")

    @property
    def alpha_e(self) -> float:
        """alpha_E - NBR 6118:2023, 8.2.8, conforme o agregado graúdo."""
        return ALPHA_E_POR_AGREGADO[self.agregado]

    # ---------------------------------------------------------------- resistências
    @property
    def fcd(self) -> float:
        """Resistência de cálculo à compressão [MPa] - NBR 6118, 12.3.3."""
        return self.fck / self.gamma_c

    @property
    def fctm(self) -> float:
        """Resistência média à tração [MPa] - NBR 6118, 8.2.5.

        [rule: NBR6118-8.2.5-fctm]
        Conferido por leitura visual da p. 23: para fck > 50 MPa,
        fct,m = 2,12 * ln[1 + 0,1*(fck + 8)] (não 0,11*fck — os dois
        coeficientes produzem valores próximos mas diferentes).
        """
        if self.fck <= 50.0:
            return 0.30 * self.fck ** (2.0 / 3.0)
        return 2.12 * math.log(1.0 + 0.1 * (self.fck + 8.0))

    @property
    def fctk_inf(self) -> float:
        """Resistência característica inferior à tração [MPa] - NBR 6118, 8.2.5."""
        return 0.7 * self.fctm

    @property
    def fctd(self) -> float:
        """Resistência de cálculo à tração [MPa] - NBR 6118, 12.3.3."""
        return self.fctk_inf / self.gamma_c

    # ---------------------------------------------------------------- parâmetros do diagrama
    @property
    def alpha_c(self) -> float:
        """Coeficiente do diagrama retangular - NBR 6118, 17.2.2."""
        if self.fck <= 50.0:
            return 0.85
        return 0.85 * (1.0 - (self.fck - 50.0) / 200.0)

    @property
    def lambda_x(self) -> float:
        """Relação y/x do diagrama retangular - NBR 6118, 17.2.2."""
        if self.fck <= 50.0:
            return 0.80
        return 0.80 - (self.fck - 50.0) / 400.0

    @property
    def csi_limite(self) -> float:
        """Limite de ductilidade x/d - NBR 6118, 14.6.4.3."""
        return 0.45 if self.fck <= 50.0 else 0.35

    @property
    def alpha_v(self) -> float:
        """alpha_v2 = (1 - fck/250) - NBR 6118, 19.5.3.1 (bielas de punção)."""
        return 1.0 - self.fck / 250.0

    @property
    def Eci(self) -> float:
        """Módulo de elasticidade inicial [MPa] - NBR 6118, 8.2.8.

        [rule: NBR6118-8.2.8-Eci]
        Conferido por leitura visual da p. 24: as duas expressões levam o
        fator alpha_E do agregado graúdo multiplicando o termo todo — a
        versão anterior deste código fixava alpha_E=1,0 (granito/gnaisse)
        sem deixar isso configurável.
        """
        if self.fck <= 50.0:
            return self.alpha_e * 5600.0 * math.sqrt(self.fck)
        return self.alpha_e * 21500.0 * ((self.fck / 10.0) + 1.25) ** (1.0 / 3.0)

    @property
    def Ecs(self) -> float:
        """Módulo de elasticidade secante [MPa] - NBR 6118, 8.2.8."""
        alpha_i = min(1.0, 0.8 + 0.2 * self.fck / 80.0)
        return alpha_i * self.Eci

    @property
    def rho_min_flexao(self) -> float:
        """
        Taxa mínima de armadura de flexão (relativa a Ac) - NBR 6118, Tab. 17.3,
        para concreto com gamma_c = 1.4 e aço CA-50.
        """
        tabela = {20: 0.00150, 25: 0.00150, 30: 0.00150, 35: 0.00164,
                  40: 0.00179, 45: 0.00194, 50: 0.00208, 55: 0.00211,
                  60: 0.00219, 65: 0.00226, 70: 0.00233, 75: 0.00239,
                  80: 0.00245, 85: 0.00251, 90: 0.00256}
        chaves = sorted(tabela)
        if self.fck <= chaves[0]:
            return tabela[chaves[0]]
        if self.fck >= chaves[-1]:
            return tabela[chaves[-1]]
        for k0, k1 in zip(chaves, chaves[1:]):
            if k0 <= self.fck <= k1:
                t = (self.fck - k0) / (k1 - k0)
                return tabela[k0] + t * (tabela[k1] - tabela[k0])
        return tabela[chaves[-1]]


# eta_1 - NBR 6118:2023, Tabela 8.2 (coeficiente de aderência)
ETA1_POR_CATEGORIA = {"CA-25": 1.00, "CA-50": 2.25, "CA-60": 1.00}
_CATEGORIA_POR_FYK = {250.0: "CA-25", 500.0: "CA-50", 600.0: "CA-60"}


@dataclass
class Aco:
    """Aço para armadura passiva (NBR 6118:2023, Seção 8.3 / NBR 7480).

    [rule: NBR6118-Tab8.2-eta1]
    A Tabela 8.2 dá eta_1 por CATEGORIA do aço (CA-25=1,00 / CA-50=2,25 /
    CA-60=1,00) — não por "ser nervurada ou não". CA-60 É nervurada e ainda
    assim tem eta_1=1,00, diferente de CA-50. Uma versão anterior deste
    código usava um booleano `nervurada` que atribuía 2,25 a qualquer aço
    de alta aderência, incluindo CA-60 — subestimava o comprimento de
    ancoragem necessário para CA-60 (erro do lado inseguro).
    """

    fyk: float = 500.0        # MPa
    gamma_s: float = 1.15     # NBR 6118, Tab. 12.1
    Es: float = 210_000.0     # MPa - NBR 6118, 8.3.5
    categoria: str | None = None   # "CA-25"/"CA-50"/"CA-60"; None = inferida de fyk

    def __post_init__(self) -> None:
        if self.categoria is None:
            self.categoria = _CATEGORIA_POR_FYK.get(self.fyk)
            if self.categoria is None:
                raise ValueError(
                    f"fyk={self.fyk} MPa não corresponde diretamente a "
                    "CA-25/CA-50/CA-60 (250/500/600 MPa); informe "
                    "'categoria' explicitamente para fixar eta_1 (Tab. 8.2).")
        if self.categoria not in ETA1_POR_CATEGORIA:
            raise ValueError(
                f"categoria de aço {self.categoria!r} desconhecida; use um "
                f"de {sorted(ETA1_POR_CATEGORIA)}.")

    @property
    def fyd(self) -> float:
        """Resistência de cálculo ao escoamento [MPa] - NBR 6118, 12.3.3."""
        return self.fyk / self.gamma_s

    @property
    def eta1(self) -> float:
        """Coeficiente de aderência eta_1 - NBR 6118, Tabela 8.2 (p. 29)."""
        return ETA1_POR_CATEGORIA[self.categoria]

    @property
    def eps_yd(self) -> float:
        return self.fyd / self.Es


# Bitolas comerciais [mm] - NBR 7480
BITOLAS_COMERCIAIS = (6.3, 8.0, 10.0, 12.5, 16.0, 20.0, 25.0, 32.0)


def area_barra(phi_mm: float) -> float:
    """Área da seção transversal de uma barra [m2]."""
    return math.pi * (phi_mm / 1000.0) ** 2 / 4.0


def massa_linear(phi_mm: float) -> float:
    """Massa linear nominal da barra [kg/m] - NBR 7480 (aço 7850 kg/m3)."""
    return 7850.0 * area_barra(phi_mm)


def eta2_aderencia(boa_aderencia: bool = True) -> float:
    """Coeficiente de situação de aderência - NBR 6118, 9.3.2.1."""
    return 1.0 if boa_aderencia else 0.7


def eta3_bitola(phi_mm: float) -> float:
    """Coeficiente relativo ao diâmetro - NBR 6118, 9.3.2.1."""
    return 1.0 if phi_mm < 32.0 else (132.0 - phi_mm) / 100.0


def comprimento_ancoragem_basico(phi_mm: float, concreto: Concreto, aco: Aco,
                                 boa_aderencia: bool = True) -> float:
    """
    Comprimento de ancoragem básico l_b [m] - NBR 6118:2023, item 9.4.2.4, p. 37.

    [rule: NBR6118-9.4.2.4-lb-basico]
        f_bd = eta1 * eta2 * eta3 * f_ctd
        l_b  = (phi / 4) * (f_yd / f_bd)  >=  25*phi

    Conferido por leitura visual: a norma exige o piso "l_b >= 25*phi", que
    uma versão anterior deste código omitia. Só passa a valer para bitolas
    grandes com concreto de alta resistência (fbd alto) — em CA-50/C25 com
    phi < 32mm o próprio cálculo já supera 25*phi, então o piso raramente
    aparece nos casos usuais; ainda assim é exigência literal da norma.
    """
    fbd = aco.eta1 * eta2_aderencia(boa_aderencia) * eta3_bitola(phi_mm) * concreto.fctd
    lb_calculado = (phi_mm / 1000.0) / 4.0 * (aco.fyd / fbd)
    return max(lb_calculado, 25.0 * phi_mm / 1000.0)
