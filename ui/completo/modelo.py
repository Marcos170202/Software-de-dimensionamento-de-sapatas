"""
modelo.py
---------
Empacota os campos que já saíram de `calc_core.sapata_isolada` no formato de
dicionário que os desenhos (`visual3d.Visualizador3D`, `visual2d.PerfilCortes`)
e o exportador (`pranchas.gerar_memorial_pdf`) esperam.

Nenhuma conta nova é feita aqui: `at`/`bt` (dimensões do topo do tronco)
vêm de `Sapata._geometria_volumes`, a mesma rotina que o núcleo usa
internamente para chegar em `res.volume_concreto`. É a mesma fórmula, só
não exposta por um atributo público em `ResultadoSapata` — chamá-la aqui é
reaproveitar o cálculo do núcleo, não recalcular nada na UI. Os demais
campos são leitura direta de `sapata` e `res`.
"""
from __future__ import annotations

from calc_core.sapata_isolada.sapata import ResultadoSapata, Sapata


def construir_modelo_visual(sapata: Sapata, res: ResultadoSapata) -> dict:
    """Dicionário de geometria/estratigrafia para os visualizadores e o PDF."""
    # _geometria_volumes é privada, mas é a própria rotina do núcleo que
    # produziu res.volume_concreto — reaproveitada aqui só para expor "at"/
    # "bt" (dimensões do topo do tronco) aos desenhos.
    geo = sapata._geometria_volumes(res.a, res.b, res.h, res.h0)

    perfil = sapata.solo.perfil
    camadas: list[dict] = []
    if perfil is not None:
        for z_topo, z_base, camada in perfil.limites():
            camadas.append({
                "nome": camada.nome,
                "tipo": camada.tipo.value,
                "z_topo": z_topo,
                "z_base": z_base,
            })

    armaduras = [{"direcao": ar.direcao, "n": ar.n_barras, "phi_mm": ar.phi_mm}
                 for ar in res.armaduras]

    q_liquido: float | None = None
    if res.recalques is not None:
        q_liquido = res.recalques.q_liquido

    return {
        "a": res.a, "b": res.b, "h": res.h, "h0": res.h0,
        "at": geo["at"], "bt": geo["bt"],
        "ap": sapata.pilar.ap, "bp": sapata.pilar.bp,
        "hf": sapata.solo.hf,
        "cobrimento": sapata.cobrimento,
        "camadas": camadas,
        "nivel_agua": perfil.nivel_agua if perfil is not None else None,
        "armaduras": armaduras,
        "q_liquido": q_liquido,
    }
