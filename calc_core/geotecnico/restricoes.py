"""Restrições dimensionais de sapatas isoladas.

Ref.: ABNT NBR 6122:2022, Seção 7.7 (Critérios adicionais)
"""
from __future__ import annotations

from calc_core.modelos import Verificacao


def verificar_dimensao_minima(B: float, L: float,
                               dimensao_minima: float = 0.60) -> Verificacao:
    """Dimensão mínima em planta de sapatas isoladas.

    Ref.: ABNT NBR 6122:2022, item 7.7.1, p. 24
    [rule: NBR6122-7.7.1-dimensao-minima]

    "Em planta, as sapatas isoladas ou os blocos não podem ter dimensões
    inferiores a 60 cm." A norma não declara exceção nem faixa de aplicação
    — vale para qualquer sapata isolada ou bloco, qualquer tipo de carga.
    """
    menor_lado = min(B, L)
    ok = menor_lado >= dimensao_minima
    return Verificacao(
        regra="NBR6122-7.7.1-dimensao-minima",
        descricao="Dimensão mínima em planta (60 cm)",
        aplicavel=True,
        ok=ok,
        mensagem=(
            f"menor lado = {menor_lado:.2f} m "
            f"{'>=' if ok else '<'} mínimo de {dimensao_minima:.2f} m"
        ),
    )
