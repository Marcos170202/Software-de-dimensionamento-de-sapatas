"""Dimensionamento geotécnico — escopo atual: sapata isolada, carga centrada,
solo homogêneo (ver ``ruleset.yaml`` e ``CLAUDE.md`` para o que falta).

A v9 acrescenta a determinação da PARCELA DE ELU da tensão admissível a partir
de SPT (``semiempirico``, ``sigma_adm``) e do caminho teórico de capacidade de
carga (``capacidade``), mais a majoração condicional por vento (``vento``).
Nenhum desses caminhos verifica o §7.4 (ELS/recalque): ver ``ROTULO_ELU``.
"""
from calc_core.geotecnico.capacidade import (
                                             capacidade_de_carga,
                                             fator_N_gamma,
                                             fator_Nc,
                                             fator_Nq,
                                             fatores_de_capacidade,
                                             fatores_de_forma_de_beer,
                                             phi_reduzido_de_puncionamento,
                                             validar_entrada_capacidade,
)
from calc_core.geotecnico.dominio import (
                                             ForaDoDominioError,
                                             NenhumMetodoAplicavelError,
)
from calc_core.geotecnico.geometria import dimensionar_sapata_carga_centrada
from calc_core.geotecnico.restricoes import verificar_dimensao_minima
from calc_core.geotecnico.seguranca import (
                                             MetodoDeSegurancaError,
                                             comparar_com_tensao_atuante,
                                             fator_de_seguranca_global,
)
from calc_core.geotecnico.semiempirico import (
                                             regra_brasileira_nspt_50_argila,
                                             teixeira_1996_areia,
)
from calc_core.geotecnico.sigma_adm import semiempirico_spt, teorico_terzaghi_vesic
from calc_core.geotecnico.vento import (
                                             MajoracaoDeVentoError,
                                             k_v_maximo_admissivel,
                                             majoracao_admissivel,
)

__all__ = [
                                             "ForaDoDominioError",
                                             "MajoracaoDeVentoError",
                                             "MetodoDeSegurancaError",
                                             "NenhumMetodoAplicavelError",
                                             "capacidade_de_carga",
                                             "comparar_com_tensao_atuante",
                                             "dimensionar_sapata_carga_centrada",
                                             "fator_N_gamma",
                                             "fator_Nc",
                                             "fator_Nq",
                                             "fator_de_seguranca_global",
                                             "fatores_de_capacidade",
                                             "fatores_de_forma_de_beer",
                                             "k_v_maximo_admissivel",
                                             "majoracao_admissivel",
                                             "phi_reduzido_de_puncionamento",
                                             "regra_brasileira_nspt_50_argila",
                                             "semiempirico_spt",
                                             "teixeira_1996_areia",
                                             "teorico_terzaghi_vesic",
                                             "validar_entrada_capacidade",
                                             "verificar_dimensao_minima",
]
