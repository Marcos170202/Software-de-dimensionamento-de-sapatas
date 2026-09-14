"""Elementos estruturais (pilar, viga, contraventamento) — Etapa 2 do
processo de modelagem.

Cada elemento liga dois nós (pelo ``id``, não pela instância — a
resolução/validação de que os ids existem e formam um modelo
consistente é responsabilidade da camada de agregação do modelo,
``estrutura_metalica.analysis.model.StructuralModel``) e carrega o
perfil, o material e a classificação de ligação em cada extremidade.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .connection import PINNED_CONNECTION, RIGID_CONNECTION, Connection, ConnectionType
from .material import SteelMaterial
from .section import SteelSection


@dataclass(frozen=True, slots=True)
class _StructuralMember:
    """Campos e validações comuns a pilar, viga e contraventamento.

    Não é instanciada diretamente — serve só para não repetir a
    validação de nós/seção/material/ligações nas três subclasses.

    ``orientation_angle`` (radianos) fixa a orientação dos eixos
    principais da seção em torno do eixo longitudinal do elemento —
    ver ``estrutura_metalica.analysis.stiffness`` para a convenção
    exata (ângulo 0 = orientação padrão: eixo forte resistindo à
    flexão no plano "vertical" da orientação automática do elemento).
    """

    id: int
    start_node_id: int
    end_node_id: int
    section: SteelSection
    material: SteelMaterial
    start_connection: Connection = field(default=RIGID_CONNECTION)
    end_connection: Connection = field(default=RIGID_CONNECTION)
    orientation_angle: float = 0.0

    def __post_init__(self) -> None:
        if self.start_node_id == self.end_node_id:
            raise ValueError(
                f"Elemento {self.id}: nó inicial e final não podem ser o mesmo "
                f"(id={self.start_node_id!r})."
            )
        if not math.isfinite(self.orientation_angle):
            raise ValueError(
                f"Elemento {self.id}: 'orientation_angle' deve ser finito, "
                f"recebido: {self.orientation_angle!r}"
            )


@dataclass(frozen=True, slots=True)
class Column(_StructuralMember):
    """Pilar metálico — perfil I/H, U ou tubo (circular/retangular),
    ligações às vigas/base classificadas em cada extremidade (Etapa 2).

    ``base_level``/``top_level`` são rótulos livres de pavimento
    (ex.: "térreo", "1º pav"), opcionais — usados apenas como metadado
    de apresentação; a posição geométrica real vem dos nós referenciados.
    """

    base_level: str | None = None
    top_level: str | None = None


@dataclass(frozen=True, slots=True)
class Beam(_StructuralMember):
    """Viga metálica — perfil I/H ou U, com opção de seção mista
    aço-concreto (laje colaborante com conectores de cisalhamento,
    Etapa 2 do processo).

    ``is_composite`` só sinaliza a intenção de projeto nesta fase —
    o dimensionamento da seção mista (verificação dos conectores de
    cisalhamento, largura efetiva de mesa colaborante etc.) é uma fase
    futura (NBR 8800, Anexo O), fora do escopo desta entidade de dado.
    """

    is_composite: bool = False


@dataclass(frozen=True, slots=True)
class Bracing(_StructuralMember):
    """Contraventamento — barra de treliça biarticulada, resistindo
    apenas a força axial (Etapa 2: "elemento específico do aço sem
    equivalente direto no HyperFrame").

    Ambas as extremidades são forçosamente rotuladas — não é permitido
    passar ``start_connection``/``end_connection`` diferentes de
    rotulada, pois a hipótese de barra biarticulada é o que torna o
    contraventamento um elemento de treliça (só rigidez axial e de
    flexão liberada) em vez de um elemento de pórtico. O padrão já é
    rotulado em ambas as pontas (sobrescrevendo o padrão rígido herdado
    de ``_StructuralMember``), então normalmente nem precisa ser
    passado.

    LIMITAÇÃO: a camada de análise mantém a torção sempre transmitida
    entre as extremidades, mesmo aqui (ver
    ``estrutura_metalica.analysis.stiffness``) — irrelevante na
    prática (rigidez torcional de contraventamentos é tipicamente
    desprezível e nada no modelo depende da rotação da barra em torno
    do próprio eixo), mas não é o comportamento exato de uma rótula
    esférica real.
    """

    start_connection: Connection = field(default=PINNED_CONNECTION)
    end_connection: Connection = field(default=PINNED_CONNECTION)

    def __post_init__(self) -> None:
        # Nota: `super().__post_init__()` (forma sem argumentos) não é usada
        # aqui de propósito — `@dataclass(slots=True)` recria a classe após o
        # corpo ser executado, o que invalida a célula `__class__` capturada
        # pelo super() sem argumentos definido no corpo original e causa
        # `TypeError: super(type, obj): obj must be an instance or subtype
        # of type` em tempo de execução. Chamar o método da classe-base
        # explicitamente evita depender dessa célula.
        _StructuralMember.__post_init__(self)
        for end, connection in (("inicial", self.start_connection), ("final", self.end_connection)):
            if connection.connection_type is not ConnectionType.PINNED:
                raise ValueError(
                    f"Contraventamento {self.id}: ligação {end} deve ser rotulada "
                    f"(PINNED), recebido: {connection.connection_type.name}. "
                    "Contraventamentos são barras biarticuladas por hipótese."
                )


Member = Column | Beam | Bracing
"""Alias de tipo para qualquer elemento estrutural — usado pela camada
``analysis`` (agregação do modelo, montagem da rigidez) para aceitar
pilares, vigas e contraventamentos de forma uniforme."""
