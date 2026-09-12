"""Limitação (recomendada) do índice de esbeltez de barras tracionadas
e comprimidas.

Fonte: ABNT NBR 8800:2024, 5.2.8.1 (barras tracionadas, página 44) e
5.3.7.1 (barras comprimidas, página 52). Conferido por leitura direta
(renderização visual) do PDF da norma — ver rastreabilidade completa
em ``docs/normative/NBR8800-RULES.md``.

**Diferença importante em relação aos demais módulos deste pacote**:
esta NÃO é uma verificação de estado-limite último obrigatória. O
texto da norma usa "recomenda-se" (não "deve"), e 5.2.8.3 explicita
que, se a recomendação não for adotada, cabe ao responsável técnico
pelo projeto estabelecer novos limites — não há uma condição binária
"aprovado/reprovado" equivalente a ``Nt,Sd <= Nt,Rd``. Por isso
``SlendernessCheckResult`` não herda de
:class:`~estrutura_metalica.normative.nbr8800._check_result.CheckResult`
e expõe ``is_within_recommended_limit`` em vez de ``is_ok``.

Escopo desta fase: apenas o caso mais simples — barra tracionada
individual (5.2.8.1) ou comprimida individual (5.3.7.1), usando o
maior índice de esbeltez entre os eixos principais.

**Fora do escopo**: 5.2.8.2 (requisito adicional para barras COMPOSTAS
tracionadas) e a parte equivalente para barras compostas comprimidas
(5.3.6) — requerem modelagem de barras compostas (múltiplos perfis com
ligações intermediárias), ainda não presente no domínio geométrico
atual.
"""

from __future__ import annotations

from dataclasses import dataclass

from ._validation import is_positive_finite

#: NBR 8800:2024, 5.2.8.1: índice de esbeltez recomendado para barras
#: tracionadas, excetuando-se tirantes de barras redondas pré-
#: tensionadas ou outras barras montadas com pré-tensão (não modelados
#: aqui).
TENSION_SLENDERNESS_LIMIT = 300.0

#: NBR 8800:2024, 5.3.7.1: índice de esbeltez recomendado para barras
#: comprimidas.
COMPRESSION_SLENDERNESS_LIMIT = 200.0


def slenderness_ratio(length: float, radius_of_gyration: float) -> float:
    """Índice de esbeltez, ``ℓ/r`` (NBR 8800:2024, 5.2.8.1/5.3.7.1).

    ``length``: comprimento destravado da barra — para compressão,
    especificamente o "comprimento destravado associado à flexão"
    (5.3.7.1); tipicamente ``KL`` (já incluído o fator de comprimento
    efetivo ``K``, não calculado por este módulo).
    ``radius_of_gyration``: raio de giração correspondente ao mesmo
    eixo de flexão usado para ``length`` — tipicamente ``section.rx``
    ou ``section.ry``.
    """
    if not is_positive_finite(length):
        raise ValueError(
            f"slenderness_ratio: length deve ser finito e positivo, recebido: {length!r}"
        )
    if not is_positive_finite(radius_of_gyration):
        raise ValueError(
            f"slenderness_ratio: radius_of_gyration deve ser finito e positivo, "
            f"recebido: {radius_of_gyration!r}"
        )
    return length / radius_of_gyration


@dataclass(frozen=True, slots=True)
class SlendernessCheckResult:
    """Resultado da verificação (recomendada, não obrigatória) do
    índice de esbeltez — ver docstring do módulo para o motivo de não
    seguir o padrão ``CheckResult`` (solicitante/resistente).

    ``ratio``: o maior índice de esbeltez entre os eixos principais.
    ``limit``: 300 para tração (5.2.8.1) ou 200 para compressão
    (5.3.7.1).
    """

    ratio: float
    limit: float

    def __post_init__(self) -> None:
        if not is_positive_finite(self.ratio):
            raise ValueError(f"ratio deve ser finito e positivo, recebido: {self.ratio!r}")
        if not is_positive_finite(self.limit):
            raise ValueError(f"limit deve ser finito e positivo, recebido: {self.limit!r}")

    @property
    def is_within_recommended_limit(self) -> bool:
        """``True`` se ``ratio <= limit``. ``False`` NÃO significa
        reprovação normativa — significa que (5.2.8.3, tração; sem
        cláusula equivalente explícita para compressão em 5.3.7) cabe
        ao responsável técnico pelo projeto estabelecer novos limites
        justificados para essa barra."""
        return self.ratio <= self.limit


def check_tension_slenderness(
    length_x: float,
    radius_of_gyration_x: float,
    length_y: float,
    radius_of_gyration_y: float,
) -> SlendernessCheckResult:
    """Verifica o índice de esbeltez recomendado de uma barra
    tracionada (NBR 8800:2024, 5.2.8.1, limite recomendado 300),
    considerando o maior índice entre os dois eixos principais."""
    ratio_x = slenderness_ratio(length_x, radius_of_gyration_x)
    ratio_y = slenderness_ratio(length_y, radius_of_gyration_y)
    return SlendernessCheckResult(ratio=max(ratio_x, ratio_y), limit=TENSION_SLENDERNESS_LIMIT)


def check_compression_slenderness(
    length_x: float,
    radius_of_gyration_x: float,
    length_y: float,
    radius_of_gyration_y: float,
) -> SlendernessCheckResult:
    """Verifica o índice de esbeltez recomendado de uma barra
    comprimida (NBR 8800:2024, 5.3.7.1, limite recomendado 200), mesma
    lógica de :func:`check_tension_slenderness`."""
    ratio_x = slenderness_ratio(length_x, radius_of_gyration_x)
    ratio_y = slenderness_ratio(length_y, radius_of_gyration_y)
    return SlendernessCheckResult(
        ratio=max(ratio_x, ratio_y), limit=COMPRESSION_SLENDERNESS_LIMIT
    )
