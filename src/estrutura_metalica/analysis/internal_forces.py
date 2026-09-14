"""Recuperação de esforços internos por elemento a partir de um
:class:`~estrutura_metalica.analysis.AnalysisResult` — insumo para as
verificações normativas por barra (NBR 8800), que trabalham com
esforço solicitante de cálculo (``Nsd``, ``Vsd``, ``Msd``, ...) por
elemento, não com deslocamento/reação nodal global.

**ATENÇÃO — esforços exatos, não um envelope aproximado**: como esta
fase do motor de cálculo só tem cargas NODAIS (nenhuma carga de
elemento — distribuída, peso próprio ou concentrada fora dos nós — ver
ATENÇÃO em ``estrutura_metalica.analysis.load``), o diagrama de esforço
normal e de momento torçor é CONSTANTE ao longo do elemento, o de força
cortante também é CONSTANTE, e o de momento fletor é LINEAR entre as
duas extremidades. Isso significa que os dois valores nas extremidades
determinam o valor exato em qualquer ponto do elemento — não há
aproximação em usar o maior valor absoluto entre as duas extremidades
como esforço "governante": é o pico exato do diagrama. Quando cargas de
elemento existirem, este módulo precisará ser revisto (o pico de
momento pode ficar no meio do vão, não numa extremidade).

Técnica de recuperação: ``{f}_local = [k]_local_condensado @ [T] @
{u}_global`` — a matriz de rigidez local já condensada
(:func:`~estrutura_metalica.analysis.stiffness.element_stiffness_local`)
garante momento fletor nulo automaticamente nas extremidades rotuladas,
mesmo usando aqui o deslocamento nodal GLOBAL (compartilhado com os
demais elementos que concorrem no nó): a linha/coluna daquele grau de
liberdade fica zerada na matriz condensada, então o valor do
deslocamento ali não influencia a força recuperada (ver dedução no
docstring de :func:`member_local_end_forces`).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from estrutura_metalica.model import Member

from .model import StructuralModel
from .result import AnalysisResult
from .stiffness import element_stiffness_local, member_length, transformation_matrix


def member_local_end_forces(
    model: StructuralModel, member: Member, result: AnalysisResult
) -> NDArray[np.float64]:
    """12-vetor de forças/momentos nodais do elemento, em eixos LOCAIS
    — mesma ordem de graus de liberdade de
    ``estrutura_metalica.analysis.stiffness.local_stiffness_matrix``:
    ``(N, Vy, Vz, T, My, Mz)`` no nó inicial seguido do mesmo conjunto
    de componentes no nó final (índices 0-5 e 6-11).

    Convenção de sinal do esforço normal: ``+f[6]`` (componente axial
    na extremidade FINAL) é a força normal com tração positiva — o
    valor na extremidade inicial tem sinal oposto (``f[0] == -f[6]``
    sempre, pois não há carga axial de elemento nesta fase). Cortante e
    momento fletor têm sinal oposto entre as duas extremidades pela
    mesma razão (mesmo esforço "visto" de cada lado) — ver
    :func:`~estrutura_metalica.analysis.internal_forces.member_internal_forces`
    para os valores já resumidos em magnitude, prontos para uso nas
    verificações normativas.
    """
    start = model.nodes[member.start_node_id]
    end = model.nodes[member.end_node_id]
    length = member_length(start, end)
    u_global = np.array(
        result.displacements[member.start_node_id] + result.displacements[member.end_node_id]
    )
    t = transformation_matrix(start, end, member.orientation_angle)
    u_local = t @ u_global
    k_local = element_stiffness_local(member, length)
    return np.asarray(k_local @ u_local, dtype=np.float64)


@dataclass(frozen=True, slots=True)
class MemberInternalForces:
    """Esforços internos governantes de um elemento — ver ATENÇÃO no
    docstring do módulo sobre por que os dois valores de extremidade
    bastam para determinar o pico exato de cada diagrama nesta fase.

    ``axial``: força normal (N), tração positiva.
    ``shear_major_axis``/``shear_minor_axis``: força cortante (N) nos
    planos de flexão em torno do eixo forte/fraco da seção (ver
    convenção de eixos locais em
    ``estrutura_metalica.analysis.stiffness``) — magnitude (sempre
    ``>= 0``).
    ``torque``: momento torçor (N·m), magnitude.
    ``moment_major_axis``/``moment_minor_axis``: momento fletor (N·m)
    em torno do eixo forte/fraco da seção — magnitude do maior valor
    entre as duas extremidades (pico exato do diagrama linear).
    """

    member_id: int
    axial: float
    shear_major_axis: float
    shear_minor_axis: float
    torque: float
    moment_major_axis: float
    moment_minor_axis: float


def member_internal_forces(
    model: StructuralModel, member: Member, result: AnalysisResult
) -> MemberInternalForces:
    """Esforços internos governantes do elemento — ver
    :class:`MemberInternalForces`."""
    f = member_local_end_forces(model, member, result)
    return MemberInternalForces(
        member_id=member.id,
        axial=float(f[6]),
        shear_major_axis=float(max(abs(f[2]), abs(f[8]))),
        shear_minor_axis=float(max(abs(f[1]), abs(f[7]))),
        torque=float(max(abs(f[3]), abs(f[9]))),
        moment_major_axis=float(max(abs(f[4]), abs(f[10]))),
        moment_minor_axis=float(max(abs(f[5]), abs(f[11]))),
    )


__all__ = ["MemberInternalForces", "member_internal_forces", "member_local_end_forces"]
