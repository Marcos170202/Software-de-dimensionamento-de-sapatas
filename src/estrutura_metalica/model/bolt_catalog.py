"""Catálogo de parafusos estruturais — ASTM A325, A490 e A307.

Fonte: catálogos de fabricante (Rudge Ramos — "Parafuso Sextavado
Estrutural A325"/"A490"/"A307") — tabela "DIÂMETRO NOMINAL" (dimensões,
mm) e tabela "PROPRIEDADES MECÂNICAS" (``LR`` — limite de resistência
à tração, ``fu`` do parafuso, em psi/PSI, convertido para SI).

Apenas ``nominal_diameter`` (``db``, m) e ``fub`` (Pa) são guardados —
os únicos dois parâmetros que as funções de
:mod:`~estrutura_metalica.normative.nbr8800.bolts` realmente exigem
(``Ab = 0,25π·db²`` é calculada a partir do diâmetro nominal pela
própria NBR 8800, 6.3.2.2 — NÃO a partir de uma "área de tensão de
tração" de catálogo, que é uma grandeza diferente, específica de
normas norte-americanas, e não usada por nenhuma fórmula da NBR 8800
implementada neste pacote). Demais colunas de catálogo (cabeça,
porca, arruela, comprimento de rosca etc.) são requisitos de
fornecimento/detalhamento, fora do escopo deste catálogo.

Conversão psi → Pa: ``1 psi = 6894,757293168 Pa`` (definição exata do
psi em unidades SI).

**ATENÇÃO — LIMITAÇÕES**:

1. **``fub`` por faixa de diâmetro**: o catálogo A325 apresenta ``fub``
   diferente para 1/2"–1" (120 000 psi mín.) e 1.1/8"–1.1/2"
   (105 000 psi mín.) — ambos os valores estão presentes aqui, um por
   diâmetro. O catálogo A490 tabula apenas duas faixas, "1"–1.1/2""
   (150 000 psi mín.) e ">1.1/2"" (140 000 psi mín.); para os
   diâmetros A490 abaixo de 1" (1/2" a 7/8", presentes na tabela
   dimensional mas fora da tabela de propriedades mecânicas do
   catálogo consultado), adota-se o mesmo valor da faixa "1"–1.1/2""
   (150 000 psi) — é o valor mínimo especificado pela ASTM F3125/A490
   para toda a faixa 1/2"–1.1/2", e o catálogo original aparenta
   apenas ter omitido a repetição da faixa na tabela impressa.
2. **``fub`` do A307**: o catálogo fornece diretamente o valor em
   N/mm² (414), sem depender de conversão psi→Pa nesta fase — usado
   como está.
3. **Apenas diâmetros 1/2" a 1.1/2"**: faixa coberta pelos três
   catálogos de referência. Diâmetros métricos (ISO 4016/898-1) NÃO
   estão incluídos — ver também a limitação equivalente de
   :func:`~estrutura_metalica.normative.nbr8800.bolts.minimum_bolt_pretension_force`.
4. **Não substitui o Anexo A da NBR 8800**: os valores de ``fub`` aqui
   são os do fabricante/ASTM — ver Anexo A da norma (não incluído
   neste pacote) para os valores normativos de referência caso
   divirjam.
"""

from __future__ import annotations

from dataclasses import dataclass

# Definição exata do psi em unidades SI (não específica da NBR 8800 —
# usada apenas para converter os valores de catálogo, publicados em
# psi, para Pa).
_PSI_TO_PA = 6894.757293168


@dataclass(frozen=True, slots=True)
class StructuralBolt:
    """Parafuso ou barra redonda rosqueada de catálogo.

    ``nominal_diameter``: diâmetro nominal, ``db`` (m). ``fub``:
    resistência à ruptura do material do parafuso (Pa) — usada
    diretamente pelas funções de
    :mod:`~estrutura_metalica.normative.nbr8800.bolts`. ``astm_grade``:
    especificação ASTM. ``source``: catálogo/edição de origem.
    """

    name: str
    nominal_diameter: float
    fub: float
    astm_grade: str
    source: str

    def __post_init__(self) -> None:
        if self.nominal_diameter <= 0:
            raise ValueError(
                f"nominal_diameter do parafuso '{self.name}' deve ser positivo, "
                f"recebido: {self.nominal_diameter!r}"
            )
        if self.fub <= 0:
            raise ValueError(
                f"fub do parafuso '{self.name}' deve ser positivo, recebido: {self.fub!r}"
            )


_IN_TO_M = 0.0254
_RR_A325 = "Rudge Ramos - Parafuso Sextavado Estrutural ASTM A325"
_RR_A490 = "Rudge Ramos - Parafuso Sextavado Estrutural ASTM A490"
_RR_A307 = "Rudge Ramos - Parafuso Sextavado Estrutural ASTM A307"

# Diâmetros nominais (polegadas fracionárias -> m) comuns aos três catálogos.
_DIAMETERS_IN: dict[str, float] = {
    "1/2": 0.5,
    "5/8": 0.625,
    "3/4": 0.75,
    "7/8": 0.875,
    "1": 1.0,
    "1.1/8": 1.125,
    "1.1/4": 1.25,
    "1.3/8": 1.375,
    "1.1/2": 1.5,
}

_A325_FUB_GROUP_1 = 120_000 * _PSI_TO_PA  # 1/2" a 1" (mín.)
_A325_FUB_GROUP_2 = 105_000 * _PSI_TO_PA  # 1.1/8" a 1.1/2" (mín.)
_A490_FUB = 150_000 * _PSI_TO_PA  # 1/2" a 1.1/2" (mín.) - ver ATENÇÃO 1
_A307_FUB = 414e6  # N/mm² = MPa -> Pa, valor direto do catálogo

_A325_GROUP_1_SIZES = {"1/2", "5/8", "3/4", "7/8", "1"}


def _bolt(imperial: str, fub: float, grade: str, source: str) -> StructuralBolt:
    diameter_m = _DIAMETERS_IN[imperial] * _IN_TO_M
    name = f"{grade} {imperial}\""
    return StructuralBolt(
        name=name, nominal_diameter=diameter_m, fub=fub, astm_grade=grade, source=source
    )


_ALL_BOLTS: tuple[StructuralBolt, ...] = tuple(
    [
        _bolt(
            size,
            _A325_FUB_GROUP_1 if size in _A325_GROUP_1_SIZES else _A325_FUB_GROUP_2,
            "ASTM A325",
            _RR_A325,
        )
        for size in _DIAMETERS_IN
    ]
    + [_bolt(size, _A490_FUB, "ASTM A490", _RR_A490) for size in _DIAMETERS_IN]
    + [_bolt(size, _A307_FUB, "ASTM A307", _RR_A307) for size in _DIAMETERS_IN]
)

STRUCTURAL_BOLT_CATALOG: dict[str, StructuralBolt] = {bolt.name: bolt for bolt in _ALL_BOLTS}


def get_structural_bolt(astm_grade: str, imperial_diameter: str) -> StructuralBolt:
    """Busca um parafuso de catálogo por especificação ASTM e diâmetro
    nominal em polegadas (ex.: ``get_structural_bolt("ASTM A325", '7/8"')``
    ou ``get_structural_bolt("ASTM A325", "7/8")`` — a aspa final é
    opcional).

    Levanta ``KeyError`` com a listagem de diâmetros disponíveis para a
    especificação quando não encontrado.
    """
    diameter = imperial_diameter.rstrip('"')
    name = f'{astm_grade} {diameter}"'
    try:
        return STRUCTURAL_BOLT_CATALOG[name]
    except KeyError:
        available = sorted(
            b.name for b in STRUCTURAL_BOLT_CATALOG.values() if b.astm_grade == astm_grade
        )
        raise KeyError(
            f"Parafuso {name!r} nao encontrado. Disponiveis para {astm_grade!r}: {available!r}"
        ) from None
