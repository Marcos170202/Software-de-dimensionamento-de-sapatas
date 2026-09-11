"""Montagem da rigidez global e solução — Etapa 4/5 do processo de
modelagem ("análise": solver por montagem + solução direta, mesmo
princípio do skyline LDL^T do HyperFrame — aqui via eliminação direta
do numpy, agnóstica ao método de armazenamento esparso, suficiente
para os tamanhos de modelo desta fase).

Só análise linear elástica de 1ª ordem nesta fase — 2ª ordem (P-Δ),
flambagem e modal ficam para fases futuras (ver
PROCESSO_MODELAGEM_METALICA.md, Etapa 5).
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from .dof import ALL_DOFS
from .load import LoadCase
from .model import StructuralModel
from .result import AnalysisResult
from .stiffness import element_stiffness_global

_CONDITION_NUMBER_LIMIT = 1e12
"""Acima deste número de condição, a matriz de rigidez livre é
considerada instável demais para confiar na solução — heurística, não
uma prova formal de mecanismo, mas suficiente para pegar o caso comum
de um grau de liberdade sem nenhuma rigidez (ex.: rotação de um nó só
tocado por elementos com aquela extremidade rotulada)."""


class AnalysisError(Exception):
    """Modelo não pôde ser resolvido — mecanismo (grau de liberdade
    sem restrição/rigidez suficiente), apoios insuficientes, ou falha
    numérica na solução do sistema."""


def assemble_global_stiffness(model: StructuralModel) -> NDArray[np.float64]:
    """Matriz de rigidez global do modelo (soma da contribuição de
    cada elemento nos GDL globais dos seus dois nós)."""
    k_global = np.zeros((model.dof_count, model.dof_count))
    for member in model.members:
        start = model.nodes[member.start_node_id]
        end = model.nodes[member.end_node_id]
        k_element = element_stiffness_global(member, start, end)
        dof_map = [
            model.global_dof_index(node_id, dof)
            for node_id in (member.start_node_id, member.end_node_id)
            for dof in ALL_DOFS
        ]
        k_global[np.ix_(dof_map, dof_map)] += k_element
    return k_global


def assemble_load_vector(model: StructuralModel, load_case: LoadCase) -> NDArray[np.float64]:
    """Vetor de forças globais equivalente ao caso de carga (só cargas
    nodais nesta fase — ver docstring de
    ``estrutura_metalica.analysis.load``)."""
    f_global = np.zeros(model.dof_count)
    for load in load_case.loads:
        if load.node_id not in model.nodes:
            raise ValueError(
                f"Carga do caso '{load_case.name}' no nó {load.node_id!r}: nó "
                "não existe no modelo."
            )
        for dof, value in zip(ALL_DOFS, load.as_vector(), strict=True):
            f_global[model.global_dof_index(load.node_id, dof)] += value
    return f_global


def solve(model: StructuralModel, load_case: LoadCase) -> AnalysisResult:
    """Resolve o modelo para o caso de carga informado: monta a
    rigidez e o vetor de forças globais, particiona GDL livres/
    restringidos, resolve os deslocamentos livres e calcula as reações
    de apoio.

    Não há recalque de apoio prescrito nesta fase — todo GDL
    restringido tem deslocamento/rotação zero.
    """
    k_global = assemble_global_stiffness(model)
    f_global = assemble_load_vector(model, load_case)

    restrained = model.restrained_dof_indices()
    free = [i for i in range(model.dof_count) if i not in restrained]

    if not free:
        raise AnalysisError(
            "Modelo sem nenhum grau de liberdade livre — todos os GDL estão "
            "restringidos, não há o que analisar."
        )

    k_ff = k_global[np.ix_(free, free)]
    f_f = f_global[free]

    condition = np.linalg.cond(k_ff)
    if not np.isfinite(condition) or condition > _CONDITION_NUMBER_LIMIT:
        raise AnalysisError(
            "Matriz de rigidez (GDL livres) malcondicionada ou singular — o "
            "modelo provavelmente tem um mecanismo: verifique se todo grau de "
            "liberdade tem apoio ou elemento (não rotulado nessa direção) "
            "restringindo-o. Ligações rotuladas liberam TODAS as rotações da "
            "extremidade — um nó só tocado por barras rotuladas ali, sem apoio "
            "rotacional, fica livre para girar sem nenhuma rigidez."
        )

    try:
        u_f = np.linalg.solve(k_ff, f_f)
    except np.linalg.LinAlgError as exc:
        raise AnalysisError(f"Falha ao resolver o sistema de equações: {exc}") from exc

    u_global = np.zeros(model.dof_count)
    u_global[free] = u_f

    reactions_global = k_global @ u_global - f_global

    displacements = {
        node_id: tuple(
            float(u_global[model.global_dof_index(node_id, dof)]) for dof in ALL_DOFS
        )
        for node_id in model.nodes
    }
    reactions = {
        support.node_id: tuple(
            float(reactions_global[model.global_dof_index(support.node_id, dof)])
            if dof in support.restrained
            else 0.0
            for dof in ALL_DOFS
        )
        for support in model.supports
    }

    return AnalysisResult(displacements=displacements, reactions=reactions)
