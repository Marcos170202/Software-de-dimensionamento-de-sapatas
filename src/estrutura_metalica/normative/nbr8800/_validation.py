"""Validação numérica compartilhada — módulo privado (não faz parte
da API pública de ``estrutura_metalica.normative.nbr8800``)."""

from __future__ import annotations

import math


def is_positive_finite(value: float) -> bool:
    """``True`` se ``value`` é finito (nem NaN nem infinito) e
    estritamente positivo.

    Mais estrito que um simples ``value > 0`` — esse teste sozinho
    rejeita NaN (``NaN > 0`` é ``False``) mas NÃO rejeita infinito
    (``inf > 0`` é ``True``), o que deixaria passar, por exemplo, um
    comprimento ou área infinitos para dentro de uma fórmula
    normativa, produzindo um resultado sem sentido físico em vez de um
    erro claro na entrada.
    """
    return math.isfinite(value) and value > 0


def is_non_negative_finite(value: float) -> bool:
    """``True`` se ``value`` é finito e maior ou igual a zero.

    Usado para grandezas que podem legitimamente ser zero (ex.: um
    esforço solicitante de cálculo nulo em um dos eixos), ao contrário
    de :func:`is_positive_finite` (grandezas estritamente positivas,
    como uma área ou um comprimento)."""
    return math.isfinite(value) and value >= 0
