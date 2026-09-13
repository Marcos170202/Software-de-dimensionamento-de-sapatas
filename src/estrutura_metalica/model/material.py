"""Aço estrutural — Etapa 3 do processo de modelagem.

Valores de catálogo (fy, fu) são os usualmente adotados na prática
brasileira para os aços citados no PROCESSO_MODELAGEM_METALICA.md
(seção "Etapa 3 — Materiais e cargas"). Eles NÃO substituem a
verificação da certidão de qualidade/laudo do material realmente
fornecido em obra — servem como valor-padrão de pré-dimensionamento.

``EN_10025_S275``/``EN_10025_S355``: aços europeus (Usiminas, "Tiras
a Quente", tabela de propriedades mecânicas conforme EN 10025-2) —
usados por perfis laminados British Steel (UB/UC, ver
:mod:`~estrutura_metalica.model.british_steel_catalog`) e chapas de
aço em geral. **ATENÇÃO**: a EN 10025-2 reduz ``fy`` para espessuras
maiores — os valores aqui são os da faixa mais fina e mais comum
(``E ≤ 16 mm``: S275 ``fy=275 MPa``; S355 ``fy=355 MPa``); para
``16 < E ≤ 20 mm`` a norma já reduz para 265 MPa/345 MPa
respectivamente (dependência de espessura NÃO modelada por
:class:`SteelMaterial` — um único valor por material). ``fu`` também
varia em faixa (não um único valor) — adotado aqui o limite inferior
da faixa para ``E < 3 mm`` (mais conservador): S275 ``fu=410 MPa``;
S355 ``fu=470 MPa`` (a faixa completa impressa é 410–580 MPa e
470–630 MPa respectivamente, variando com a direção do ensaio e a
espessura).

``ASTM_A572_GR42``/``ASTM_A588``/``ASTM_A242``: aços de chapa grossa
("Aços de Qualidade Estrutural"/"...Resistentes à Corrosão
Atmosférica", ArcelorMittal, "Aços Planos", tabela "Principais
Normas") — fy/fu conferidos nessa mesma fonte para as faixas de
espessura indicadas (ASTM A572 Gr. 50 e ASTM A36 já cadastrados
acima também aparecem nessa tabela, com os MESMOS valores já usados
— confirmação cruzada independente da fonte original):

- ``ASTM_A572_GR42``: ``fy=290 MPa`` mín., ``fu=415 MPa`` mín.,
  espessura 2,00–19,00 mm.
- ``ASTM_A588`` (aço patinável/"Corten", graus A/B/K — mesmas
  propriedades mecânicas para os três graus, que diferem apenas na
  composição química): ``fy=345 MPa`` mín., ``fu=485 MPa`` mín.,
  espessura 6,00–12,00 mm.
- ``ASTM_A242`` Tipo 1 (aço patinável): ``fy=345 MPa`` mín.,
  ``fu=480 MPa`` mín., espessura 4,75–16,00 mm.
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
EN_10025_S275 = SteelMaterial(name="EN 10025 S275", fy=275e6, fu=410e6, e=_E_ACO)
EN_10025_S355 = SteelMaterial(name="EN 10025 S355", fy=355e6, fu=470e6, e=_E_ACO)
ASTM_A572_GR42 = SteelMaterial(name="ASTM A572 Gr. 42", fy=290e6, fu=415e6, e=_E_ACO)
ASTM_A588 = SteelMaterial(name="ASTM A588", fy=345e6, fu=485e6, e=_E_ACO)
ASTM_A242 = SteelMaterial(name="ASTM A242", fy=345e6, fu=480e6, e=_E_ACO)

STEEL_MATERIAL_CATALOG: dict[str, SteelMaterial] = {
    material.name: material
    for material in (
        ASTM_A36,
        ASTM_A572_GR50,
        ASTM_A992,
        EN_10025_S275,
        EN_10025_S355,
        ASTM_A572_GR42,
        ASTM_A588,
        ASTM_A242,
    )
}
