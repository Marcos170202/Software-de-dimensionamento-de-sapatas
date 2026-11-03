"""Resultado da análise — Etapa 5 do processo de modelagem."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Resultado de uma análise linear elástica de 1ª ordem.

    ``displacements``: por nó, os 6 deslocamentos/rotações globais,
    SEMPRE nesta ordem — (ux, uy, uz, rx, ry, rz), metros e radianos
    (mesma ordem de :data:`estrutura_metalica.analysis.dof.ALL_DOFS`).

    ``reactions``: por nó COM APOIO, as 6 forças/momentos de reação
    globais, na mesma ordem (N, N·m) — só os GDL restringidos têm
    reação fisicamente definida; os demais componentes de um nó com
    apoio parcial vêm como 0.0 (nenhuma reação nesse GDL, por não
    estar restringido).
    """

    displacements: dict[int, tuple[float, ...]]
    reactions: dict[int, tuple[float, ...]]
