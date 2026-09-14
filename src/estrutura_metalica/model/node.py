"""Nó (ponto do modelo espacial) — Etapa 2 do processo de modelagem."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Node:
    """Ponto no espaço 3D usado para posicionar pilares, vigas e
    contraventamentos.

    Coordenadas em metros, no sistema global do modelo (X, Y em planta;
    Z é a elevação/pavimento).

    ``id`` é escolhido por quem monta o modelo (não gerado
    automaticamente aqui) — a unicidade dos ids dentro de um modelo é
    responsabilidade da camada que agrega os nós (ainda não
    implementada nesta fase), não deste tipo de dado isolado.
    """

    id: int
    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        for value, label in ((self.x, "x"), (self.y, "y"), (self.z, "z")):
            if not _is_finite(value):
                raise ValueError(f"Coordenada '{label}' do nó {self.id} deve ser finita, "
                                  f"recebido: {value!r}")

    def distance_to(self, other: Node) -> float:
        """Distância euclidiana até outro nó, em metros."""
        return math.sqrt(
            (self.x - other.x) ** 2 + (self.y - other.y) ** 2 + (self.z - other.z) ** 2
        )


def _is_finite(value: float) -> bool:
    return value == value and value not in (float("inf"), float("-inf"))
