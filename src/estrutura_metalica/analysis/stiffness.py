"""Matriz de rigidez do elemento de pórtico 3D — Etapa 4 do processo
de modelagem.

Elemento de viga-coluna de Euler-Bernoulli (sem deformação por
cisalhamento — a inclusão da teoria de Timoshenko fica para uma fase
futura), 12 GDL (6 por nó: 3 translações + 3 rotações), com liberação
de momento FLETOR nas extremidades classificadas como rotuladas (via
condensação estática) — torção permanece sempre transmitida, mesmo em
extremidade rotulada; ver a limitação documentada em
``_released_local_dofs``.

CONVENÇÃO DE EIXOS LOCAIS (própria deste módulo — não há ainda um
"ângulo de referência" padronizado por norma para isto, cada software
de análise adota a sua):

- ``e1``: eixo do elemento, do nó inicial para o final.
- Eixo de referência global: eixo Z global, EXCETO quando o elemento é
  vertical (``e1`` paralelo a Z), caso em que se usa o eixo Y global
  (evita a referência ficar paralela a ``e1``, o que tornaria o
  produto vetorial abaixo indefinido).
- ``e2 = referência × e1`` (normalizado), ``e3 = e1 × e2``.
- ``Member.orientation_angle`` gira ``e2``/``e3`` em torno de ``e1``
  (regra da mão direita) a partir dessa orientação padrão — 0 rad
  mantém a orientação automática acima.
- O EIXO FORTE da seção (``section.ix``) resiste à flexão associada à
  deflexão ao longo de ``e3``; o eixo fraco (``section.iy``) resiste à
  flexão associada à deflexão ao longo de ``e2``. Na orientação padrão
  (ângulo 0), para um elemento horizontal isso coloca o eixo forte
  resistindo a cargas de gravidade (``e3`` fica vertical) — a
  orientação usual de vigas na prática.

Consequência: para pilares (elementos verticais), a orientação padrão
(ângulo 0) NÃO determina univocamente qual direção horizontal (X ou Y
global) recebe o eixo forte — depende só da convenção acima
(``e3 = e1 × e2`` com a referência trocada para Y global). Quando a
orientação real do perfil em obra importa, use ``orientation_angle``
para ajustar.
"""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray

from estrutura_metalica.model import ConnectionType, Member, Node

_VERTICAL_TOLERANCE = 1e-9


def member_length(start: Node, end: Node) -> float:
    """Comprimento do elemento (m) — distância entre os nós."""
    return start.distance_to(end)


def local_axes(
    start: Node, end: Node, orientation_angle: float = 0.0
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Tripla ortonormal (e1, e2, e3) dos eixos locais do elemento, em
    coordenadas globais — ver convenção no docstring do módulo."""
    length = member_length(start, end)
    if length <= 0:
        raise ValueError("Comprimento do elemento deve ser positivo para definir eixos locais.")
    e1 = np.array(
        [end.x - start.x, end.y - start.y, end.z - start.z], dtype=np.float64
    ) / length

    global_z = np.array([0.0, 0.0, 1.0])
    if abs(abs(float(np.dot(e1, global_z))) - 1.0) < _VERTICAL_TOLERANCE:
        reference = np.array([0.0, 1.0, 0.0])
    else:
        reference = global_z

    e2 = np.cross(reference, e1)
    e2 /= np.linalg.norm(e2)
    e3 = np.cross(e1, e2)
    e3 /= np.linalg.norm(e3)

    if orientation_angle:
        cos_b, sin_b = math.cos(orientation_angle), math.sin(orientation_angle)
        e2, e3 = cos_b * e2 + sin_b * e3, -sin_b * e2 + cos_b * e3

    return e1, e2, e3


def transformation_matrix(
    start: Node, end: Node, orientation_angle: float = 0.0
) -> NDArray[np.float64]:
    """Matriz de transformação 12×12 (global → local): bloco-diagonal
    com a matriz de cossenos diretores 3×3 repetida 4 vezes (uma por
    trio de translações/rotações em cada nó)."""
    e1, e2, e3 = local_axes(start, end, orientation_angle)
    r = np.array([e1, e2, e3])
    t = np.zeros((12, 12))
    for block in range(4):
        t[3 * block : 3 * block + 3, 3 * block : 3 * block + 3] = r
    return t


def _bending_block(ei_over_l3: float, length: float, sign: float) -> NDArray[np.float64]:
    """Bloco 4×4 clássico de flexão de Euler-Bernoulli para um par
    (deflexão, rotação) em cada extremidade. ``sign`` alterna entre os
    dois planos de flexão (e1-e2 e e1-e3) — ver docstring do módulo."""
    c = ei_over_l3
    length_squared = length * length
    s6l = sign * 6.0 * length * c
    return np.array(
        [
            [12.0 * c, s6l, -12.0 * c, s6l],
            [s6l, 4.0 * length_squared * c, -s6l, 2.0 * length_squared * c],
            [-12.0 * c, -s6l, 12.0 * c, -s6l],
            [s6l, 2.0 * length_squared * c, -s6l, 4.0 * length_squared * c],
        ]
    )


def _place_block(
    k: NDArray[np.float64], block: NDArray[np.float64], dofs: tuple[int, int, int, int]
) -> None:
    for a, i in enumerate(dofs):
        for b, j in enumerate(dofs):
            k[i, j] += block[a, b]


def local_stiffness_matrix(member: Member, length: float) -> NDArray[np.float64]:
    """Matriz de rigidez local 12×12 do elemento, SEM considerar
    liberações de momento nas extremidades (ver
    :func:`element_stiffness_local` para isso).

    Ordem dos GDL por nó: (u, v, w, θx, θy, θz) — u ao longo de e1
    (axial), v ao longo de e2, w ao longo de e3, θx torção em torno de
    e1, θy rotação em torno de e2 (flexiona w), θz rotação em torno de
    e3 (flexiona v).
    """
    e, g = member.material.e, member.material.shear_modulus
    a, j = member.section.area, member.section.j
    i_strong, i_weak = member.section.ix, member.section.iy

    k = np.zeros((12, 12))

    k_ax = e * a / length
    k[0, 0] = k[6, 6] = k_ax
    k[0, 6] = k[6, 0] = -k_ax

    k_tor = g * j / length
    k[3, 3] = k[9, 9] = k_tor
    k[3, 9] = k[9, 3] = -k_tor

    # Flexão no plano e1-e2 (v, θz): eixo fraco, sign=+1.
    _place_block(k, _bending_block(e * i_weak / length**3, length, sign=1.0), (1, 5, 7, 11))
    # Flexão no plano e1-e3 (w, θy): eixo forte, sign=-1.
    _place_block(k, _bending_block(e * i_strong / length**3, length, sign=-1.0), (2, 4, 8, 10))

    return k


def _released_local_dofs(member: Member) -> tuple[int, ...]:
    """Índices locais (0-based) dos GDL rotacionais liberados (momento
    fletor nulo) nas extremidades do elemento, conforme a
    classificação de cada :class:`~estrutura_metalica.model.Connection`.

    Uma ligação rotulada libera as DUAS rotações de FLEXÃO daquela
    extremidade (``θy``, ``θz``) — a torção (``θx``) permanece sempre
    transmitida nesta fase, mesmo em ligação rotulada.

    LIMITAÇÃO DELIBERADA: isto não é só simplificação por
    conveniência — liberar torção nas DUAS extremidades ao mesmo tempo
    tornaria a submatriz condensada singular (a barra ficaria livre
    para girar em torno do próprio eixo sem nenhuma rigidez residual,
    um modo de corpo rígido), quebrando a condensação estática. Como
    contraventamentos (:class:`~estrutura_metalica.model.Bracing`)
    exigem as duas extremidades rotuladas, a torção residual (contínua
    entre os nós) que essa escolha deixa nessas barras é inofensiva na
    prática (a rigidez torcional de perfis de contraventamento é
    tipicamente desprezível e nada no modelo depende fisicamente da
    rotação de uma barra em torno do próprio eixo) — mas é uma
    aproximação, não o comportamento exato de uma rótula esférica
    real. Ligação semirrígida ainda não é suportada aqui.
    """
    released: list[int] = []
    for connection, bending_rotation_dofs in (
        (member.start_connection, (4, 5)),
        (member.end_connection, (10, 11)),
    ):
        if connection.connection_type is ConnectionType.PINNED:
            released.extend(bending_rotation_dofs)
        elif connection.connection_type is ConnectionType.SEMI_RIGID:
            raise NotImplementedError(
                f"Elemento {member.id}: ligação semirrígida ainda não é suportada "
                "pela montagem da rigidez (fase futura) — use rígida ou rotulada."
            )
    return tuple(released)


def condense(
    k: NDArray[np.float64], condensed_dofs: tuple[int, ...]
) -> NDArray[np.float64]:
    """Condensação estática (complemento de Schur): elimina os GDL em
    ``condensed_dofs`` assumindo força/momento nulo neles (válido para
    liberação de momento em extremidade de barra, sem carga aplicada
    diretamente nesse GDL — sempre o caso aqui, pois não há cargas de
    elemento nesta fase, só nodais).

    Retorna uma matriz do mesmo tamanho, com linhas/colunas dos GDL
    condensados zeradas — o elemento passa a não contribuir com
    rigidez alguma para esses GDL (fisicamente correto: um GDL
    condensado por definição não transmite esforço).
    """
    if not condensed_dofs:
        return k
    n = k.shape[0]
    retained = [d for d in range(n) if d not in condensed_dofs]
    condensed = list(condensed_dofs)

    k_rr = k[np.ix_(retained, retained)]
    k_rc = k[np.ix_(retained, condensed)]
    k_cr = k[np.ix_(condensed, retained)]
    k_cc = k[np.ix_(condensed, condensed)]

    k_reduced = k_rr - k_rc @ np.linalg.solve(k_cc, k_cr)

    result = np.zeros_like(k)
    result[np.ix_(retained, retained)] = k_reduced
    return result


def element_stiffness_local(member: Member, length: float) -> NDArray[np.float64]:
    """Matriz de rigidez local 12×12 do elemento, já com a liberação
    de momento das extremidades rotuladas condensada."""
    k = local_stiffness_matrix(member, length)
    return condense(k, _released_local_dofs(member))


def element_stiffness_global(member: Member, start: Node, end: Node) -> NDArray[np.float64]:
    """Matriz de rigidez do elemento em coordenadas globais (12×12),
    pronta para ser somada à matriz de rigidez global do modelo."""
    length = member_length(start, end)
    k_local = element_stiffness_local(member, length)
    t = transformation_matrix(start, end, member.orientation_angle)
    return t.T @ k_local @ t
