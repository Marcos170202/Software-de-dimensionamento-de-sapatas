"""
geotecnia.py
------------
Parâmetros de projeto do solo, perfil estratigráfico (substrato), tensões
geostáticas e propagação de tensões no maciço.

Referências: ABNT NBR 6122:2019 (Projeto e execução de fundações),
NBR 6484 (SPT), Boussinesq (1885) / Newmark (1935).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

GAMMA_AGUA = 9.81  # kN/m3


class TipoSubstrato(Enum):
    """Comportamento predominante da camada quanto à deformabilidade."""

    GRANULAR = "granular"    # areias/pedregulhos -> recalque imediato (elástico)
    COESIVO = "coesivo"      # argilas saturadas  -> adensamento primário + secundário
    ROCHA = "rocha"          # recalque desprezível
    ATERRO = "aterro"        # tratado como granular, com alerta


@dataclass
class Camada:
    """
    Camada do perfil geotécnico (uma linha da sondagem interpretada).

    Parâmetros de deformabilidade
    -----------------------------
    GRANULAR : E_s [kPa] (ou nspt + correlação), nu
    COESIVO  : Cc, Cs, e0, OCR (ou sigma_vm), cv [m2/ano], C_alpha
    """

    nome: str
    espessura: float                          # [m]
    tipo: TipoSubstrato = TipoSubstrato.GRANULAR
    gamma_nat: float = 18.0                   # [kN/m3] acima do N.A.
    gamma_sat: float = 20.0                   # [kN/m3] abaixo do N.A.

    # --- resistência (estabilidade / capacidade de carga)
    phi: float = 30.0                         # ângulo de atrito efetivo [graus]
    coesao: float = 0.0                       # coesão efetiva [kPa]
    nspt: Optional[float] = None              # N_SPT médio da camada

    # --- deformabilidade: solos granulares
    Es: Optional[float] = None                # módulo de deformabilidade [kPa]
    nu: float = 0.30                          # coeficiente de Poisson

    # --- deformabilidade: solos coesivos
    Cc: Optional[float] = None                # índice de compressão
    Cs: Optional[float] = None                # índice de recompressão (~Cc/6)
    e0: Optional[float] = None                # índice de vazios inicial
    OCR: float = 1.0                          # razão de sobreadensamento
    cv: Optional[float] = None                # coef. de adensamento [m2/ano]
    C_alpha: Optional[float] = None           # coef. de compressão secundária
    drenagem_dupla: bool = True

    # --- correlação SPT -> Es (indicativa; NÃO substitui ensaio)
    k_spt_MPa: float = 3.5                    # Es[MPa] ~ k * N (areias)

    def gamma(self, abaixo_na: bool) -> float:
        return self.gamma_sat if abaixo_na else self.gamma_nat

    def modulo_deformabilidade(self) -> float:
        """Es [kPa] - do valor informado ou da correlação com o SPT."""
        if self.Es is not None:
            return self.Es
        if self.nspt is not None:
            return self.k_spt_MPa * self.nspt * 1000.0
        raise ValueError(f"Camada '{self.nome}': informe Es ou nspt.")

    def modulo_deformabilidade_opcional(self) -> Optional[float]:
        """Como modulo_deformabilidade(), mas devolve None se faltarem dados."""
        try:
            return self.modulo_deformabilidade()
        except ValueError:
            return None

    def indice_recompressao(self) -> float:
        if self.Cs is not None:
            return self.Cs
        if self.Cc is not None:
            return self.Cc / 6.0     # relação usual Cs ~ Cc/5 a Cc/10
        raise ValueError(f"Camada '{self.nome}': informe Cc/Cs.")


@dataclass
class PerfilGeotecnico:
    """
    Perfil estratigráfico a partir da superfície do terreno (z = 0, para baixo).

    nivel_agua : profundidade do N.A. [m] a partir da superfície (None = ausente)
    """

    camadas: list[Camada] = field(default_factory=list)
    nivel_agua: Optional[float] = None

    # ------------------------------------------------------------------ acesso
    @property
    def profundidade_total(self) -> float:
        return sum(c.espessura for c in self.camadas)

    def limites(self) -> list[tuple[float, float, Camada]]:
        """Lista de (z_topo, z_base, camada)."""
        z = 0.0
        out = []
        for c in self.camadas:
            out.append((z, z + c.espessura, c))
            z += c.espessura
        return out

    def camada_em(self, z: float) -> Camada:
        for z0, z1, c in self.limites():
            if z0 <= z < z1 or (abs(z - z1) < 1e-9 and c is self.camadas[-1]):
                return c
        if self.camadas:
            return self.camadas[-1]
        raise ValueError("Perfil geotécnico vazio.")

    # --------------------------------------------------- tensões geostáticas
    def tensao_vertical_total(self, z: float) -> float:
        """sigma_v [kPa] na profundidade z."""
        na = self.nivel_agua if self.nivel_agua is not None else math.inf
        sigma = 0.0
        restante = z
        for z0, z1, c in self.limites():
            if restante <= 0:
                break
            dz = min(z1, z) - z0
            if dz <= 0:
                continue
            # separa o trecho acima e abaixo do N.A.
            z_seco = max(0.0, min(z1, z, na) - z0)
            z_sub = max(0.0, dz - z_seco)
            sigma += z_seco * c.gamma_nat + z_sub * c.gamma_sat
            restante -= dz
        return sigma

    def poropressao(self, z: float) -> float:
        if self.nivel_agua is None or z <= self.nivel_agua:
            return 0.0
        return (z - self.nivel_agua) * GAMMA_AGUA

    def tensao_vertical_efetiva(self, z: float) -> float:
        """sigma'_v0 [kPa] na profundidade z."""
        return max(0.0, self.tensao_vertical_total(z) - self.poropressao(z))

    def tensao_pre_adensamento(self, z: float) -> float:
        """sigma'_vm [kPa] = OCR * sigma'_v0."""
        return self.camada_em(z).OCR * self.tensao_vertical_efetiva(z)


# --------------------------------------------------------------------------- #
#  Propagação de tensões
# --------------------------------------------------------------------------- #
def influencia_canto_retangulo(m: float, n: float) -> float:
    """
    Fator de influência de Newmark para o CANTO de área retangular
    uniformemente carregada (solução de Boussinesq).

        m = B / z ,  n = L / z
    """
    if m <= 0 or n <= 0:
        return 0.0
    m2n2 = m * m + n * n
    num = 2.0 * m * n * math.sqrt(m2n2 + 1.0)
    den1 = m2n2 + 1.0 + (m * n) ** 2
    termo1 = (num / den1) * ((m2n2 + 2.0) / (m2n2 + 1.0))
    den2 = m2n2 + 1.0 - (m * n) ** 2
    # atan2 resolve automaticamente o acréscimo de pi quando den2 < 0
    termo2 = math.atan2(num, den2)
    return (termo1 + termo2) / (4.0 * math.pi)


def acrescimo_tensao_centro(q: float, a: float, b: float, z: float) -> float:
    """
    Acréscimo de tensão vertical [kPa] sob o CENTRO de uma sapata retangular
    a x b, à profundidade z abaixo da base (superposição de 4 quadrantes).
    """
    if z <= 1e-6:
        return q
    return 4.0 * q * influencia_canto_retangulo((a / 2.0) / z, (b / 2.0) / z)


def acrescimo_tensao_2v1h(q: float, a: float, b: float, z: float) -> float:
    """Espraiamento simplificado 2V:1H (método do bulbo aproximado)."""
    return q * (a * b) / ((a + z) * (b + z))


# --------------------------------------------------------------------------- #
#  Parâmetros de projeto adotados para a fundação
# --------------------------------------------------------------------------- #
@dataclass
class Solo:
    """
    Parâmetros de projeto do solo de apoio da sapata (NBR 6122:2019).

    sigma_adm : tensão admissível [kPa] - obtida de prova de carga, métodos
                semiempíricos ou teoria de capacidade de carga com FS >= 3.
    hf        : profundidade da BASE da sapata (cota de assentamento) [m]
    """

    sigma_adm: float
    gamma_solo: float = 18.0
    hf: float = 1.50
    phi: float = 30.0
    coesao: float = 0.0
    fator_atrito_base: float = 2.0 / 3.0   # delta = 2/3 * phi (base rugosa)
    fs_deslizamento: float = 1.5           # NBR 6122, 6.2.1.2
    fs_tombamento: float = 1.5
    coef_sigma_max_excentrico: float = 1.2  # majoração admitida no vértice
    perfil: Optional[PerfilGeotecnico] = None

    @property
    def atrito_base_rad(self) -> float:
        return math.radians(self.phi * self.fator_atrito_base)

    def sobrecarga_no_nivel_da_base(self) -> float:
        """q [kPa] do solo sobrejacente à cota de assentamento."""
        if self.perfil is not None:
            return self.perfil.tensao_vertical_efetiva(self.hf)
        return self.gamma_solo * self.hf


def sigma_adm_por_spt(nspt_medio: float, limite_MPa: float = 0.02) -> float:
    """
    Estimativa PRELIMINAR da tensão admissível [kPa] por correlação com o SPT
    (regra usual: sigma_adm [MPa] ~ N/50, com 5 <= N <= 20).

    ATENÇÃO: valor apenas indicativo para pré-dimensionamento. A NBR 6122:2019
    exige investigação geotécnica e justificativa formal da tensão adotada.
    """
    n = max(5.0, min(20.0, nspt_medio))
    return max(limite_MPa, n / 50.0) * 1000.0
