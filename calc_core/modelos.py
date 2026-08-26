"""Modelos de dados do núcleo — únicas estruturas que ui/ pode importar.

A regra do a3-interface.md é gerar formulário a partir destes modelos, nunca
escrever campos à mão. Usamos ``dataclasses`` da biblioteca padrão em vez de
Pydantic para manter o núcleo sem dependências externas (facilita empacotar
em .exe com PyInstaller sem inflar o binário).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EntradaSapataCentrada:
    """Entrada para o dimensionamento geométrico de sapata sob carga centrada.

    Unidades: kN para força, kPa para tensão, m para comprimento.
    """

    N_k: float
    """Carga vertical característica no topo da sapata, vinda do pilar [kN]."""

    sigma_adm: float
    """Tensão admissível (ou tensão resistente de cálculo) do terreno [kPa].

    Entrada do engenheiro — NBR 6122:2022 §7.2 lista doze fatores para
    fixá-la e este software não deduz nenhum deles de um perfil SPT.
    """

    pilar_a: float
    """Dimensão do pilar na direção X [m]."""

    pilar_b: float
    """Dimensão do pilar na direção Y [m]."""

    considerar_peso_proprio: bool = True
    """Se True, soma ao N_k uma estimativa de peso próprio (NBR 6122 §5.6)."""

    percentual_peso_proprio: float = 0.05
    """Percentual mínimo normativo do peso próprio sobre a carga permanente
    (NBR 6122 §5.6: "no mínimo 5%"). Sobrescrevível pelo engenheiro quando o
    peso próprio real (calculado a posteriori) for maior."""

    dimensao_minima: float = 0.60
    """Dimensão mínima em planta, NBR 6122:2022 §7.7.1 [m]."""

    modulo_arredondamento: float = 0.05
    """Incremento construtivo para arredondar B e L para cima [m]."""

    def __post_init__(self) -> None:
        if self.N_k <= 0:
            raise ValueError("N_k deve ser positivo (carga de compressão).")
        if self.sigma_adm <= 0:
            raise ValueError("sigma_adm deve ser positivo.")
        if self.pilar_a <= 0 or self.pilar_b <= 0:
            raise ValueError("Dimensões do pilar devem ser positivas.")
        if not (0 <= self.percentual_peso_proprio < 1):
            raise ValueError("percentual_peso_proprio deve estar em [0, 1).")
        if self.dimensao_minima <= 0:
            raise ValueError("dimensao_minima deve ser positiva.")
        if self.modulo_arredondamento <= 0:
            raise ValueError("modulo_arredondamento deve ser positivo.")


@dataclass(frozen=True)
class Verificacao:
    """Resultado de uma verificação normativa isolada, com rastreabilidade."""

    regra: str
    """ID da regra em ruleset.yaml, ex.: 'NBR6122-7.7.1-dimensao-minima'."""

    descricao: str
    """Frase curta do que foi verificado, para o semáforo da UI."""

    aplicavel: bool
    """False quando a entrada cai fora do domínio de validade da regra."""

    ok: bool | None
    """True/False se aplicável; None se não aplicável (aplicavel=False)."""

    mensagem: str = ""
    """Detalhe legível por humano — valores obtidos, limite, motivo."""


@dataclass(frozen=True)
class ResultadoGeometria:
    """Saída do dimensionamento geométrico de sapata sob carga centrada."""

    N_total: float
    """Carga total considerada (N_k + peso próprio estimado, se aplicável) [kN]."""

    area_necessaria: float
    """Área mínima exigida por N_total / sigma_adm [m²]."""

    B: float
    """Dimensão final em X, já arredondada e verificada contra o mínimo [m]."""

    L: float
    """Dimensão final em Y, já arredondada e verificada contra o mínimo [m]."""

    area_final: float
    """B * L [m²]."""

    tensao_atuante: float
    """N_total / area_final [kPa] — deve ser <= sigma_adm."""

    verificacoes: list[Verificacao] = field(default_factory=list)
    """Todas as verificações normativas aplicadas, para o memorial."""

    @property
    def aprovado(self) -> bool:
        """True se todas as verificações aplicáveis passaram."""
        return all(v.ok is not False for v in self.verificacoes)
