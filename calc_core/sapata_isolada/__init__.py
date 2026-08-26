"""
sapata_isolada
==============
Rotina de dimensionamento geotécnico e estrutural de sapatas isoladas
conforme ABNT NBR 6118:2023 e ABNT NBR 6122:2019, com análise de recalques
em função do substrato.

Uso mínimo
----------
    from sapata_isolada import *

    pilar = Pilar(ap=0.20, bp=0.50, phi_arranque_mm=16.0)
    solo  = Solo(sigma_adm=250.0, gamma_solo=18.0, hf=1.5, phi=30.0)
    combs = gerar_combinacoes([
        CasoCarga("G", Esforcos(N=600, Mx=15, My=8)),
        CasoCarga.acidental("Q", Esforcos(N=180, Mx=6)),
        CasoCarga.vento("W", Esforcos(My=45, Hx=18)),
    ])
    s = Sapata(pilar, solo, Concreto(30), Aco(500), combs, cobrimento=0.045)
    print(memorial(s.dimensionar(), s))

Interface gráfica: python sapata_desktop.py
"""
from .acoes import (CasoCarga, Combinacao, Esforcos, Pilar, TipoAcao,
                    TipoCombinacao, filtrar, gerar_combinacoes)
from .bielas import ResultadoBielas, bielas_sapata, tirante_classico
from .grelha import ResultadoGrelha, resolver_grelha
from .solo_mef import MalhaSolo, analisar_solo, conferir_com_boussinesq
from .geotecnia import (Camada, PerfilGeotecnico, Solo, TipoSubstrato,
                        acrescimo_tensao_centro, sigma_adm_por_spt)
from .materiais import Aco, Concreto, comprimento_ancoragem_basico
from .momentos import (CampoMomentos, campo_momentos, curvas_nivel,
                       momento_unitario, niveis_uteis)
from .recalques import (AnaliseRecalque, DISTORCAO_ANGULAR_LIMITE,
                        LIMITES_RECALQUE_MM, ResultadoRecalque,
                        grau_adensamento, recalque_adensamento,
                        recalque_elastico, recalque_schmertmann,
                        tempo_para_grau)
from .pdf import PDF, A3_PAISAGEM, A4_PAISAGEM, A4_RETRATO
from .pranchas import gerar_memorial_pdf
from .projecao import Camera, ControleOrbital
from .relatorio import memorial, para_json
from .rigidez import (Classificacao, ReacaoDiscretizada, classificar,
                      kv_por_modulo, kv_por_tensao_admissivel,
                      reacao_base_elastica, verificar_equilibrio)
from .sapata import (ArmaduraImposta, GeometriaImposta, OpcoesProjeto,
                     ResultadoSapata, Sapata)

__all__ = [
    "Aco", "Concreto", "comprimento_ancoragem_basico",
    "CasoCarga", "Combinacao", "Esforcos", "Pilar", "TipoAcao",
    "TipoCombinacao", "filtrar", "gerar_combinacoes",
    "Camada", "PerfilGeotecnico", "Solo", "TipoSubstrato",
    "acrescimo_tensao_centro", "sigma_adm_por_spt",
    "AnaliseRecalque", "ResultadoRecalque", "recalque_elastico",
    "recalque_adensamento", "recalque_schmertmann", "grau_adensamento",
    "tempo_para_grau", "LIMITES_RECALQUE_MM", "DISTORCAO_ANGULAR_LIMITE",
    "OpcoesProjeto", "ResultadoSapata", "Sapata",
    "GeometriaImposta", "ArmaduraImposta",
    "Classificacao", "ReacaoDiscretizada", "classificar", "reacao_base_elastica",
    "kv_por_tensao_admissivel", "kv_por_modulo", "verificar_equilibrio",
    "memorial", "para_json", "gerar_memorial_pdf",
    "PDF", "A3_PAISAGEM", "A4_PAISAGEM", "A4_RETRATO",
    "CampoMomentos", "campo_momentos", "curvas_nivel", "momento_unitario",
    "niveis_uteis", "Camera", "ControleOrbital",
    "ResultadoBielas", "bielas_sapata", "tirante_classico",
    "ResultadoGrelha", "resolver_grelha",
    "MalhaSolo", "analisar_solo", "conferir_com_boussinesq",
]
__version__ = "1.0.0"
