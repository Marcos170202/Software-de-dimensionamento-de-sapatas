"""Agregação do modelo — Etapa 4 do processo de modelagem
("sincronização 3D": junta os nós/elementos lançados na Etapa 2 num
único modelo consistente, pronto para a montagem da rigidez).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from estrutura_metalica.model import Member, Node

from .dof import DOF, NUM_DOF_PER_NODE
from .support import Support


@dataclass(frozen=True, slots=True)
class StructuralModel:
    """Modelo estrutural completo: nós, elementos e apoios, validados
    em conjunto (cada elemento/apoio referencia nós que de fato
    existem no modelo, sem ids duplicados).

    ``nodes`` é indexado pelo ``id`` do nó — a chave do dicionário deve
    ser igual a ``node.id`` para cada entrada (ver validação em
    :meth:`__post_init__`).
    """

    nodes: dict[int, Node]
    members: tuple[Member, ...]
    supports: tuple[Support, ...] = ()
    _node_index: dict[int, int] = field(default_factory=dict, repr=False, compare=False)

    def __post_init__(self) -> None:
        for node_id, node in self.nodes.items():
            if node.id != node_id:
                raise ValueError(
                    f"Nó armazenado sob a chave {node_id!r} tem id diferente "
                    f"({node.id!r}) — as chaves de 'nodes' devem ser iguais ao "
                    "id do nó correspondente."
                )
        if not self.nodes:
            raise ValueError("StructuralModel requer ao menos um nó.")

        seen_member_ids: set[int] = set()
        for member in self.members:
            if member.id in seen_member_ids:
                raise ValueError(f"Id de elemento duplicado: {member.id!r}.")
            seen_member_ids.add(member.id)
            for end_label, node_id in (
                ("inicial", member.start_node_id),
                ("final", member.end_node_id),
            ):
                if node_id not in self.nodes:
                    raise ValueError(
                        f"Elemento {member.id}: nó {end_label} {node_id!r} não "
                        "existe no modelo."
                    )

        seen_support_nodes: set[int] = set()
        for support in self.supports:
            if support.node_id not in self.nodes:
                raise ValueError(
                    f"Apoio no nó {support.node_id!r}: nó não existe no modelo."
                )
            if support.node_id in seen_support_nodes:
                raise ValueError(
                    f"Nó {support.node_id!r} tem mais de um apoio definido — "
                    "combine as restrições num único Support."
                )
            seen_support_nodes.add(support.node_id)

        node_index = {node_id: i for i, node_id in enumerate(sorted(self.nodes))}
        object.__setattr__(self, "_node_index", node_index)

    @property
    def dof_count(self) -> int:
        """Número total de graus de liberdade do modelo (6 por nó)."""
        return NUM_DOF_PER_NODE * len(self.nodes)

    def node_local_index(self, node_id: int) -> int:
        """Posição do nó (0-based) na ordenação estável usada para
        numerar os GDL globais — nós ordenados pelo ``id``."""
        return self._node_index[node_id]

    def global_dof_index(self, node_id: int, dof: DOF) -> int:
        """Índice (0-based) do grau de liberdade ``dof`` do nó
        ``node_id`` no vetor/matriz global do sistema."""
        return self.node_local_index(node_id) * NUM_DOF_PER_NODE + dof.value

    def restrained_dof_indices(self) -> frozenset[int]:
        """Índices globais de todos os GDL restringidos por algum
        apoio do modelo."""
        indices = set()
        for support in self.supports:
            for dof in support.restrained:
                indices.add(self.global_dof_index(support.node_id, dof))
        return frozenset(indices)
