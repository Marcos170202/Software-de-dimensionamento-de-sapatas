"""Aço estrutural — Etapa 3 do processo de modelagem.

Valores de catálogo (fy, fu) são os usualmente adotados na prática
brasileira para os aços citados no PROCESSO_MODELAGEM_METALICA.md
(seção "Etapa 3 — Materiais e cargas"). Eles NÃO substituem a
verificação da certidão de qualidade/laudo do material realmente
fornecido em obra — servem como valor-padrão de pré-dimensionamento.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SteelMaterial:
    """Propriedades do aço estrutural usadas na análise e no
    dimensionamento (NBR 8800).

    Unidades no SI: tensões em Pa, módulo de elasticidade em Pa,
    massa específica em kg/m³.

    ``g`` (módulo de elasticidade transversal) pode ser omitido: é
    calculado automaticamente a partir de ``e`` e ``poisson_ratio``
    via G = E / (2·(1+ν)) — válido para material isotrópico, hipótese
    padrão para aço estrutural.
    """

    name: str
    fy: float
    fu: float
    e: float
    poisson_ratio: float = 0.3
    density: float = 7850.0
    g: float | None = None

    def __post_init__(self) -> None:
        if self.fy <= 0:
            raise ValueError(f"fy deve ser positivo, recebido: {self.fy!r}")
        if self.fu <= 0:
            raise ValueError(f"fu deve ser positivo, recebido: {self.fu!r}")
        if self.fu < self.fy:
            raise ValueError(
                f"fu ({self.fu!r}) não pode ser menor que fy ({self.fy!r}) — "
                f"material '{self.name}' inconsistente."
            )
        if self.e <= 0:
            raise ValueError(f"Módulo de elasticidade 'e' deve ser positivo, recebido: {self.e!r}")
        if not (-1.0 < self.poisson_ratio < 0.5):
            raise ValueError(
                f"Coeficiente de Poisson fisicamente implausível: {self.poisson_ratio!r}"
            )
        if self.density <= 0:
            raise ValueError(f"Massa específica deve ser positiva, recebido: {self.density!r}")
        if self.g is None:
            object.__setattr__(self, "g", self.e / (2.0 * (1.0 + self.poisson_ratio)))
        elif self.g <= 0:
            raise ValueError(f"Módulo de elasticidade transversal 'g' deve ser positivo, "
                              f"recebido: {self.g!r}")

    @property
    def shear_modulus(self) -> float:
        """Alias explícito para ``g`` (nunca ``None`` após ``__post_init__``)."""
        assert self.g is not None
        return self.g


# Catálogo de aços estruturais citados no PROCESSO_MODELAGEM_METALICA.md
# (Etapa 3). Módulo de elasticidade padrão do aço estrutural conforme
# NBR 8800 (5.1.2): E = 200 000 MPa.
_E_ACO = 200_000e6  # Pa

ASTM_A36 = SteelMaterial(name="ASTM A36", fy=250e6, fu=400e6, e=_E_ACO)
ASTM_A572_GR50 = SteelMaterial(name="ASTM A572 Gr. 50", fy=345e6, fu=450e6, e=_E_ACO)
ASTM_A992 = SteelMaterial(name="ASTM A992", fy=345e6, fu=450e6, e=_E_ACO)

STEEL_MATERIAL_CATALOG: dict[str, SteelMaterial] = {
    material.name: material for material in (ASTM_A36, ASTM_A572_GR50, ASTM_A992)
}
