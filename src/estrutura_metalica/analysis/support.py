"""Apoios — condições de contorno da Etapa 4/5 do processo de
modelagem."""

from __future__ import annotations

from dataclasses import dataclass

from .dof import DOF


@dataclass(frozen=True, slots=True)
class Support:
    """Apoio em um nó: conjunto de graus de liberdade com
    deslocamento/rotação prescrito como zero (não há, nesta fase,
    apoio elástico nem recalque prescrito diferente de zero — ver
    PROCESSO_MODELAGEM_METALICA.md, "Interação Solo-Estrutura", fase
    futura)."""

    node_id: int
    restrained: frozenset[DOF]

    def __post_init__(self) -> None:
        if not self.restrained:
            raise ValueError(
                f"Apoio no nó {self.node_id} não restringe nenhum grau de "
                "liberdade — não é um apoio."
            )

    @classmethod
    def fixed(cls, node_id: int) -> Support:
        """Engaste — restringe as 6 translações/rotações."""
        return cls(node_id=node_id, restrained=frozenset(DOF))

    @classmethod
    def pinned(cls, node_id: int) -> Support:
        """Apoio rotulado — restringe as 3 translações, permite
        rotação livre nos 3 eixos."""
        return cls(node_id=node_id, restrained=frozenset({DOF.UX, DOF.UY, DOF.UZ}))
