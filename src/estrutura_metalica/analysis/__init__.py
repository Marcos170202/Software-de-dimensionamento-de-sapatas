"""Camada de análise — Etapas 4 e 5 do processo de modelagem
(sincronização 3D e análise).

Ver ``PROCESSO_MODELAGEM_METALICA.md`` na raiz do repositório.

LIMITAÇÃO DE MODELAGEM CONHECIDA — nós ligados só por
:class:`~estrutura_metalica.model.Bracing` (contraventamento, ambas as
extremidades rotuladas): como o elemento usa a formulação de pórtico
de 6 GDL/nó com a flexão condensada (não uma formulação de treliça
"pura" de 3 GDL/nó), um nó tocado só por barras rotuladas pode ficar
com graus de liberdade sem NENHUMA rigidez, mesmo com o modelo
fisicamente razoável:

- Rotação do nó em torno de eixos não cobertos pelas barras que
  chegam nele (uma treliça plana lançada no espaço 3D, por exemplo,
  deixa a rotação fora do próprio plano, e a translação fora do
  plano, sem nenhuma resistência).

Nesses casos, restrinja explicitamente os GDL "sobrando" com um
:class:`Support` construído diretamente (não só ``Support.fixed``/
``Support.pinned``) — ex.: para um nó de treliça plana no plano X-Y,
``Support(node_id=..., restrained=frozenset({DOF.UZ, DOF.RX, DOF.RY,
DOF.RZ}))``. :func:`solve` detecta o mecanismo resultante (matriz
malcondicionada) e recusa a resolver em vez de devolver um resultado
sem sentido — mas não identifica automaticamente QUAL GDL falta
restringir.
"""

from __future__ import annotations

from .dof import ALL_DOFS, DOF, NUM_DOF_PER_NODE
from .load import LoadCase, NodalLoad
from .model import StructuralModel
from .result import AnalysisResult
from .solver import AnalysisError, assemble_global_stiffness, assemble_load_vector, solve
from .support import Support

__all__ = [
    "ALL_DOFS",
    "DOF",
    "NUM_DOF_PER_NODE",
    "AnalysisError",
    "AnalysisResult",
    "LoadCase",
    "NodalLoad",
    "StructuralModel",
    "Support",
    "assemble_global_stiffness",
    "assemble_load_vector",
    "solve",
]
