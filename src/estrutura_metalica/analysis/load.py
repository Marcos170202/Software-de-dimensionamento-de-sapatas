"""Cargas nodais e casos de carga — Etapa 3/5 do processo de
modelagem.

Só cargas concentradas em nós nesta fase — cargas distribuídas ao
longo do elemento (peso próprio, cargas de laje etc., ver Etapa 3 do
PROCESSO_MODELAGEM_METALICA.md) ficam para uma fase futura em que a
montagem da rigidez (``estrutura_metalica.analysis.stiffness``) também
precisa gerar as forças nodais equivalentes correspondentes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NodalLoad:
    """Força/momento concentrado aplicado em um nó, no sistema global.

    Forças em N, momentos em N·m.
    """

    node_id: int
    fx: float = 0.0
    fy: float = 0.0
    fz: float = 0.0
    mx: float = 0.0
    my: float = 0.0
    mz: float = 0.0

    def __post_init__(self) -> None:
        for value, label in (
            (self.fx, "fx"),
            (self.fy, "fy"),
            (self.fz, "fz"),
            (self.mx, "mx"),
            (self.my, "my"),
            (self.mz, "mz"),
        ):
            if not math.isfinite(value):
                raise ValueError(
                    f"Carga no nó {self.node_id}: componente '{label}' deve ser "
                    f"finita, recebido: {value!r}"
                )

    def as_vector(self) -> tuple[float, float, float, float, float, float]:
        """Componentes na ordem (fx, fy, fz, mx, my, mz) — mesma ordem
        de :data:`estrutura_metalica.analysis.dof.ALL_DOFS`."""
        return (self.fx, self.fy, self.fz, self.mx, self.my, self.mz)


@dataclass(frozen=True, slots=True)
class LoadCase:
    """Conjunto nomeado de cargas nodais a resolver de uma vez.

    Combinações ponderadas entre casos de carga (NBR 8681, Etapa 3 do
    processo) ficam para uma fase futura — aqui um caso é resolvido
    isoladamente, sem coeficientes de ponderação.
    """

    name: str
    loads: tuple[NodalLoad, ...] = ()

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("LoadCase requer um 'name' não vazio.")
