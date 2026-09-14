"""Ligações — Etapa 2 do processo de modelagem.

Ver PROCESSO_MODELAGEM_METALICA.md, Etapa 2: "cada nó viga-pilar/
pilar-contraventamento recebe desde já uma classificação (rígida,
semirrígida ou rotulada) [...] altera a rigidez do pórtico e por isso
precisa ser decidida na modelagem, não só no detalhamento." Sem
equivalente direto no concreto armado monolítico do HyperFrame.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class ConnectionType(Enum):
    """Classificação da ligação quanto à restrição ao giro relativo
    entre as barras conectadas (NBR 8800, 4.9.6 — classificação de
    ligações viga-pilar).
    """

    RIGID = auto()
    """Momento totalmente transmitido — hipótese de continuidade
    total do giro entre as barras."""

    SEMI_RIGID = auto()
    """Transmite momento parcialmente, com uma relação
    momento-rotação própria (``rotational_stiffness``)."""

    PINNED = auto()
    """Rotulada — não transmite momento fletor; apenas força axial e
    cortante. (A camada de análise trata a torção separadamente da
    classificação aqui — ver limitação documentada em
    ``estrutura_metalica.analysis.stiffness``.)"""


@dataclass(frozen=True, slots=True)
class Connection:
    """Ligação em uma extremidade de uma barra (viga, pilar ou
    contraventamento).

    ``rotational_stiffness`` (N·m/rad) é obrigatória apenas para
    :attr:`ConnectionType.SEMI_RIGID` — é a rigidez rotacional da
    curva momento-rotação da ligação (modelo linear elástico
    simplificado; modelos não lineares ficam para fase futura), usada
    na Etapa 4 (sincronização 3D) para liberar parcialmente o momento
    na matriz de rigidez do elemento.
    """

    connection_type: ConnectionType
    rotational_stiffness: float | None = None

    def __post_init__(self) -> None:
        if self.connection_type is ConnectionType.SEMI_RIGID:
            if self.rotational_stiffness is None:
                raise ValueError(
                    "Ligação semirrígida requer 'rotational_stiffness' (N·m/rad)."
                )
            if self.rotational_stiffness <= 0:
                raise ValueError(
                    "'rotational_stiffness' deve ser positiva, recebido: "
                    f"{self.rotational_stiffness!r}"
                )
        elif self.rotational_stiffness is not None:
            raise ValueError(
                f"'rotational_stiffness' só se aplica a ligações {ConnectionType.SEMI_RIGID.name}"
                f", não a {self.connection_type.name}."
            )

    @property
    def transmits_moment(self) -> bool:
        """``True`` para ligações rígidas ou semirrígidas — usado por
        fases futuras (Etapa 4) para decidir se o GDL de rotação da
        extremidade participa (total ou parcialmente) da rigidez do
        elemento."""
        return self.connection_type is not ConnectionType.PINNED


RIGID_CONNECTION = Connection(connection_type=ConnectionType.RIGID)
"""Instância pronta para o caso mais comum (ligação rígida) — evita
repetir ``Connection(connection_type=ConnectionType.RIGID)`` em cada
barra do modelo."""

PINNED_CONNECTION = Connection(connection_type=ConnectionType.PINNED)
"""Instância pronta para ligação rotulada (ex.: extremidades de
contraventamentos, que a NBR 8800 pressupõe biarticulados)."""
