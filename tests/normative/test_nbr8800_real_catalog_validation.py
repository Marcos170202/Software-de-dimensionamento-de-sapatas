"""Exemplo de validação com dados REAIS de catálogo (perfil e parafuso).

Diferente dos demais ``TestWorkedExample`` do pacote (que usam valores
numéricos hipotéticos, escolhidos apenas para exercitar as fórmulas),
este módulo refaz duas verificações — compressão axial (5.3) e
parafuso ao cisalhamento/tração/pressão de contato (6.3.3) — usando:

- um perfil REAL do catálogo Gerdau W/H
  (:func:`~estrutura_metalica.model.get_gerdau_w_h_profile`,
  ``"W310x97.0"``, aço ASTM A572 Gr. 50, ``fy=345 MPa``/``fu=450
  MPa``);
- um parafuso REAL de catálogo (Rudge Ramos, ASTM A325, 7/8",
  ``db=22,225 mm``, ``fub`` calculado a partir de 120 000 psi mín. —
  ver :func:`~estrutura_metalica.model.get_structural_bolt`).

Os valores esperados foram recalculados de forma independente (script
Python à parte, não incluído no repositório) a partir das mesmas
fórmulas — ver comentários inline com os valores intermediários.
"""

from __future__ import annotations

import math

import pytest

from estrutura_metalica.model import get_gerdau_w_h_profile, get_structural_bolt
from estrutura_metalica.normative.nbr8800 import (
    LoadCombinationClass,
    check_bolt_bearing,
    check_bolt_shear,
    check_bolt_tension,
    check_compression_member,
    flexural_buckling_force,
    steel_resistance_factors,
)


class TestRealProfileCompression:
    """Pilar W310x97,0 (H) — Gerdau, ASTM A572 Gr. 50 (fy=345 MPa),
    flambagem por flexão em torno do eixo fraco (y), ``KL=3,5 m``
    (biapoiado, K=1), combinação normal (γa1=1,10). Sem redução de
    área efetiva por flambagem local (Aef=Ag — não verificado aqui,
    ver limitação de :mod:`~estrutura_metalica.normative.nbr8800.compression`).

    Cálculo independente:
    - ``Ney = π²·E·Iy/L² = π²·200e9·7,286e-5/3,5² ≈ 11 740 398 N``
    - ``λ0 = sqrt(Ag·fy/Ney) = sqrt(0,01236·345e6/11 740 398) ≈
      0,60267``
    - ``χ = 0,658^(λ0²) ≈ 0,85897`` (λ0 ≤ 1,5)
    - ``Nc,Rd = χ·Ag·fy/γa1 = 0,85897·0,01236·345e6/1,10 ≈
      3 329 839 N``
    """

    _E = 200e9
    _L = 3.5
    _GAMMA_A1 = 1.10

    def _profile(self):  # type: ignore[no-untyped-def]
        return get_gerdau_w_h_profile("W310x97.0")

    def test_catalog_profile_matches_expected_gerdau_values(self) -> None:
        profile = self._profile()
        # Conferência direta contra a tabela impressa (cm²/cm⁴/mm),
        # para deixar claro que o teste usa o valor de catálogo real.
        assert profile.area * 1e4 == pytest.approx(123.6, rel=1e-6)
        assert profile.ix * 1e8 == pytest.approx(22284.0, rel=1e-6)
        assert profile.iy * 1e8 == pytest.approx(7286.0, rel=1e-6)
        assert profile.depth * 1e3 == pytest.approx(308.0, rel=1e-6)
        assert profile.bf * 1e3 == pytest.approx(305.0, rel=1e-6)
        assert profile.tf * 1e3 == pytest.approx(15.4, rel=1e-6)
        assert profile.mass_linear == pytest.approx(97.0, rel=1e-6)

    def test_compression_check_with_real_profile(self) -> None:
        profile = self._profile()
        fy = 345e6
        factors = steel_resistance_factors(LoadCombinationClass.NORMAL)

        ney = flexural_buckling_force(self._E, profile.iy, self._L)
        assert ney == pytest.approx(11_740_397.99, rel=1e-4)

        result = check_compression_member(
            nc_sd=2_500_000.0,
            gross_area=profile.area,
            effective_area=profile.area,
            fy=fy,
            elastic_buckling_force=ney,
            resistance_factors=factors,
        )

        assert result.lambda_0 == pytest.approx(0.602667, rel=1e-4)
        assert result.chi == pytest.approx(0.858971, rel=1e-4)
        assert result.nc_rd == pytest.approx(3_329_838.5, rel=1e-4)
        assert result.is_ok


class TestRealBoltConnection:
    """Parafuso ASTM A325, 7/8" (db=22,225 mm), catálogo Rudge Ramos —
    ``fub = 120 000 psi = 827 370 875,18 Pa`` (grupo 1/2"-1"),
    ligando duas chapas de aço ASTM A36 (fu=400 MPa) de espessura
    t=12,5 mm cada, distância à borda/furo adjacente ℓf=40 mm,
    combinação normal (γa2=1,35).

    Cálculo independente:
    - ``Ab = 0,25π·db² ≈ 3,879e-4 m² (3,8795 cm²)``
    - ``Fv,Rd = 0,45·Ab·fub/γa2 ≈ 106 992,27 N`` (plano de corte na
      rosca — caso mais conservador, padrão)
    - ``Fc,Rd = min(1,2·ℓf·t·fu/γa2, 2,4·db·t·fu/γa2) =
      min(177 777,78; 197 555,56) = 177 777,78 N`` (deformação como
      limitação de projeto)
    - ``Abe = 0,75·Ab``; ``Ft,Rd = Abe·fub/γa2 ≈ 178 320,45 N``
    """

    _T = 0.0125
    _FU_PLATE = 400e6
    _LF = 0.040
    _GAMMA_A2 = 1.35

    def _bolt(self):  # type: ignore[no-untyped-def]
        return get_structural_bolt("ASTM A325", "7/8")

    def test_catalog_bolt_matches_expected_values(self) -> None:
        bolt = self._bolt()
        assert bolt.nominal_diameter * 1e3 == pytest.approx(22.225, rel=1e-6)
        assert bolt.fub == pytest.approx(827_370_875.18, rel=1e-6)

    def test_shear_check_with_real_bolt(self) -> None:
        bolt = self._bolt()
        result = check_bolt_shear(
            fv_sd=90_000.0,
            bolt_diameter=bolt.nominal_diameter,
            fub=bolt.fub,
            gamma_a2=self._GAMMA_A2,
            threads_excluded_from_shear_plane=False,
        )
        assert result.force_rd == pytest.approx(106_992.27, rel=1e-4)
        assert result.is_ok

    def test_bearing_check_with_real_bolt(self) -> None:
        bolt = self._bolt()
        result = check_bolt_bearing(
            fc_sd=150_000.0,
            edge_or_hole_distance=self._LF,
            thickness=self._T,
            fu=self._FU_PLATE,
            bolt_diameter=bolt.nominal_diameter,
            gamma_a2=self._GAMMA_A2,
            deformation_is_design_limit=True,
        )
        assert result.force_rd == pytest.approx(177_777.78, rel=1e-4)
        assert result.is_ok

    def test_tension_check_with_real_bolt(self) -> None:
        bolt = self._bolt()
        result = check_bolt_tension(
            ft_sd=150_000.0,
            bolt_diameter=bolt.nominal_diameter,
            fub=bolt.fub,
            gamma_a2=self._GAMMA_A2,
        )
        assert result.force_rd == pytest.approx(178_320.45, rel=1e-4)
        assert result.is_ok


def test_math_module_used_for_docstring_expressions() -> None:
    """Confirma o valor de ``0,658^(λ0²)`` citado no docstring de
    :class:`TestRealProfileCompression` (evita que o exemplo fique
    incoerente caso a fórmula de χ mude)."""
    lambda_0 = 0.602667
    assert 0.658 ** (lambda_0**2) == pytest.approx(0.858971, rel=1e-4)
    assert math.isfinite(lambda_0)
