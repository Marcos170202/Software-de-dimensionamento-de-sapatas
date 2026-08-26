"""Dimensionamento geotécnico — escopo atual: sapata isolada, carga centrada,
solo homogêneo (ver ``ruleset.yaml`` e ``CLAUDE.md`` para o que falta)."""
from calc_core.geotecnico.geometria import dimensionar_sapata_carga_centrada
from calc_core.geotecnico.restricoes import verificar_dimensao_minima

__all__ = [
    "dimensionar_sapata_carga_centrada",
    "verificar_dimensao_minima",
]
