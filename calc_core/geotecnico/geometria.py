"""Verificacao geotecnica de sapata isolada sob carga vertical centrada (v0).

Escopo EXATO do ruleset.yaml v0.1.0 (v0-geotecnico-minimo, sha256 em ruleset.lock):
sapata isolada, planta retangular, carga vertical centrada de compressao, solo declarado
homogeneo, tensao de referencia (sigma_adm, sigma_Rd ou sigma_r_k com metodo declarado)
FORNECIDA pelo engenheiro. Modo VERIFICACAO: B e L sao entradas.

Este modulo NAO calcula capacidade de carga (LAC-01/02/03), NAO calcula recalque (LAC-04),
NAO propoe B x L (LAC-11), NAO trata excentricidade (LAC-05), carga horizontal (LAC-06),
majoracao por vento (LAC-07), cotas diferentes (LAC-08) nem dimensionamento estrutural
(LAC-09). Esses casos sao RECUSADOS pelas guardas aprovadas.

Requisitos de execucao atendidos (ruleset.yaml, `requisitos_de_execucao`):
  RT-01  toda forca/tensao carrega `Natureza`; operar/comparar naturezas diferentes levanta
         ErroMisturaDeMetodo. FS_g so no metodo admissivel; gamma_m e gamma_f so no de calculo.
  RT-02  nomes de saida com namespace (geotecnico.*, cargas.*, seguranca.*).
  RT-03  guarda violada -> Verificacao(aplicavel=False, motivo, regra) e a cadeia para; nenhum
         numero parcial e devolvido.
  RT-04  entradas obrigatorias sem valor padrao; ausentes (None) -> recusa.
  RT-05  calculo interno em kN, m, kPa; constantes normativas nomeadas com unidade e regra.
  RT-06  toda funcao publica cita norma, item, pagina e [rule: <id>].
  RT-07  sem veredito global; o resultado traz cada verificacao e a lista do que NAO foi
         verificado.

Sem I/O, sem estado global mutavel, sem aleatoriedade.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import NoReturn, Optional, Tuple

# =============================================================================
# Identificadores de regra (ruleset.yaml v0.1.0)
# =============================================================================
REGRA_FUNDACAO_RASA = "NBR6122-3.28-guarda-fundacao-rasa"
REGRA_CARGA_CENTRADA = "NBR6122-7.6.2-guarda-carga-centrada"
REGRA_COMPRESSAO = "NBR6122-6.2.1.1.1-guarda-compressao"
REGRA_CASOS_PARTICULARES = "NBR6122-7.5-guarda-casos-particulares"
REGRA_VENTO = "NBR6122-6.3-guarda-vento-sem-majoracao"
REGRA_TENSAO_REFERENCIA = "NBR6122-7.3-7.4-entrada-tensao-de-referencia"
REGRA_ESFORCOS = "NBR6122-5.1-entrada-esforcos"
REGRA_PESO_PROPRIO = "NBR6122-5.6-peso-proprio"
REGRA_TENSAO_UNIFORME = "NBR6122-7.6.1-tensao-uniforme"
REGRA_VERIF_ADMISSIVEL = "NBR6122-3.30-verificacao-admissivel"
REGRA_VERIF_CALCULO = "NBR6122-3.31-verificacao-calculo"
REGRA_TABELA1 = "NBR6122-T1-resistencia-ELU"
REGRA_GAMMA_F = "NBR6122-T1c-gamma-f"
REGRA_ELU_ELS = "NBR6122-7.1-7.4-ELU-e-ELS"
REGRA_MEMORIAL = "NBR6122-6.2.1-7.1-memorial-nao-verificado"
REQ_METODO = "RT-01-separacao-de-metodo"
REQ_SEM_DEFAULT = "RT-04-sem-default-para-entrada-do-engenheiro"

# Regras aprovadas que pertencem a restricoes.py e NAO sao executadas por este modulo.
REGRA_DIMENSAO_MINIMA = "NBR6122-7.7.1-dimensao-minima"
REGRA_PROFUNDIDADE_DIVISA = "NBR6122-7.7.2-profundidade-divisa"
REGRA_LASTRO = "NBR6122-7.7.3-lastro"

# =============================================================================
# Constantes normativas nomeadas (RT-05)
# =============================================================================
#: Fator adimensional de 3.28: rasa se D_assentamento < 2 * min(B, L).
#: [rule: NBR6122-3.28-guarda-fundacao-rasa]  (adimensional)
FATOR_PROFUNDIDADE_RASA: float = 2.0

#: Fracao minima da carga vertical PERMANENTE como peso proprio (5.6: "no minimo 5 %").
#: [rule: NBR6122-5.6-peso-proprio]  (adimensional)
FRAC_MIN_PESO_PROPRIO: float = 0.05

#: gamma_f da Tabela 1, nota c, sobre esforco disponivel so em valor caracteristico.
#: [rule: NBR6122-T1c-gamma-f]  (adimensional)
GAMMA_F_6122_T1C: float = 1.4

#: Tabela 1 (6.2.1.1.1), solicitacoes de compressao. [rule: NBR6122-T1-resistencia-ELU]
FS_G_MIN_SEMIEMPIRICO: float = 3.00     # adimensional, minimo; valor proposto no processo
GAMMA_M_MIN_SEMIEMPIRICO: float = 2.15  # adimensional, minimo; valor proposto no processo
FS_G_ANALITICO: float = 3.00            # adimensional
GAMMA_M_ANALITICO: float = 2.15         # adimensional
FS_G_COM_PROVAS_DE_CARGA: float = 2.00  # adimensional
GAMMA_M_COM_PROVAS_DE_CARGA: float = 1.40  # adimensional
N_MIN_PROVAS_DE_CARGA: int = 2          # contagem ("duas ou mais provas de carga")

#: Conteudo obrigatorio do memorial (texto literal do ruleset).
#: [rule: NBR6122-6.2.1-7.1-memorial-nao-verificado]
_CONTEUDO_OBRIGATORIO_NAO_VERIFICADO: Tuple[str, ...] = (
    "ELU 6.2.1 a) perda de estabilidade global -- NAO VERIFICADO",
    "ELU 6.2.1 b) esgotamento da resistencia do terreno -- verificado SOMENTE contra a tensao "
    "de referencia fornecida pelo engenheiro",
    "ELU 6.2.1 c) deslizamento -- NAO VERIFICADO (sem carga horizontal por guarda)",
    "ELU 6.2.1 d) ruptura estrutural por movimentos da fundacao -- NAO VERIFICADO",
    "ELU 6.2.1 e) arrancamento/tracao -- NAO VERIFICADO (compressao por guarda)",
    "ELU 6.2.1 f) carregamentos transversais -- NAO VERIFICADO",
    "ELU 6.2.1 g) ruptura estrutural da sapata (NBR 6118, 7.8.1) -- NAO VERIFICADO: sem regras "
    "aprovadas",
    "ELS 6.2.2 recalques/levantamentos/vibracoes -- NAO CALCULADO; limite de ELS declarado pelo "
    "engenheiro",
    "7.1 verificacao do conjunto de fundacoes -- NAO VERIFICADO (v0 trata elemento isolado)",
    "7.7.4 fundacoes vizinhas em cotas diferentes -- NAO VERIFICADO",
    "7.2 os 12 fatores da tensao admissivel foram considerados pelo engenheiro (declaracao), nao "
    "pelo software",
)

#: Regras aprovadas cuja verificacao NAO e executada por este modulo (pertencem a
#: restricoes.py). Listadas para que nenhuma saida deste modulo sugira que foram verificadas.
_NAO_EXECUTADAS_NESTE_MODULO: Tuple[Tuple[str, str], ...] = (
    (REGRA_DIMENSAO_MINIMA,
     "7.7.1 dimensao minima em planta (60 cm) -- NAO EXECUTADA por geometria.py "
     "(pertence a restricoes.py)"),
    (REGRA_PROFUNDIDADE_DIVISA,
     "7.7.2 profundidade minima de apoio em divisa (1,5 m) -- NAO EXECUTADA por geometria.py "
     "(pertence a restricoes.py)"),
    (REGRA_LASTRO,
     "7.7.3 lastro de concreto nao estrutural (>= 5 cm) -- NAO EXECUTADA por geometria.py "
     "(pertence a restricoes.py)"),
)


# =============================================================================
# Tipos
# =============================================================================
class Metodo(Enum):
    """Metodo de verificacao da seguranca, unico e imutavel por projeto (RT-01).

    Ref.: ABNT NBR 6122:2022, itens 3.30 / 3.31 / 6.2.1.1.1, p. 6 e 17
    [rule: NBR6122-3.30-verificacao-admissivel] [rule: NBR6122-3.31-verificacao-calculo]
    """

    ADMISSIVEL = "admissivel"
    CALCULO = "calculo"


class Natureza(Enum):
    """Natureza de uma grandeza de carga ou tensao (RT-01).

    Ref.: ABNT NBR 6122:2022, itens 3.30 / 3.31, p. 6
    [rule: NBR6122-3.30-verificacao-admissivel] [rule: NBR6122-3.31-verificacao-calculo]
    """

    CARACTERISTICA = "caracteristica"
    CALCULO = "calculo"


class MetodoResistencia(Enum):
    """Linha da Tabela 1 usada para obter o limite de ELU a partir de sigma_r_k (modo B).

    Ref.: ABNT NBR 6122:2022, item 6.2.1.1.1 (Tabela 1), p. 17
    [rule: NBR6122-T1-resistencia-ELU]
    """

    SEMIEMPIRICO = "semiempirico"
    ANALITICO = "analitico"
    COM_PROVAS_DE_CARGA = "com_provas_de_carga"


class Procedimento73(Enum):
    """Procedimento declarado para fixar a tensao de referencia (modo A).

    Ref.: ABNT NBR 6122:2022, item 7.3, p. 22
    [rule: NBR6122-7.3-7.4-entrada-tensao-de-referencia]
    """

    PROVA_DE_CARGA_7_3_1 = "7.3.1"
    ANALITICO_7_3_2 = "7.3.2"
    SEMIEMPIRICO_7_3_3 = "7.3.3"


class ErroMisturaDeMetodo(Exception):
    """Operacao ou comparacao entre grandezas de naturezas diferentes (RT-01).

    Ref.: ABNT NBR 6122:2022, itens 3.30 / 3.31, p. 6
    [rule: NBR6122-3.30-verificacao-admissivel] [rule: NBR6122-3.31-verificacao-calculo]
    """


@dataclass(frozen=True)
class Verificacao:
    """Estado de uma guarda ou verificacao. Nunca e um veredito global (RT-07).

    Ref.: ABNT NBR 6122:2022, item 6.2.1 / 7.1, p. 16-21
    [rule: NBR6122-6.2.1-7.1-memorial-nao-verificado]

    aplicavel=False  -> guarda violada / entrada invalida: o caso foi RECUSADO (RT-03);
                        `atende` e None.
    aplicavel=True   -> `atende` True/False indica o estado da verificacao executada.
    `valores` sao tuplas (nome_com_namespace, valor, unidade).
    """

    regra: str
    aplicavel: bool
    atende: Optional[bool]
    motivo: str
    valores: Tuple[Tuple[str, float, str], ...] = ()


class Recusa(Exception):
    """Recusa do caso (RT-03). Carrega a Verificacao(aplicavel=False) correspondente.

    Ref.: ABNT NBR 6122:2022, item 6.2.1 / 7.1, p. 16-21
    [rule: NBR6122-6.2.1-7.1-memorial-nao-verificado]
    """

    def __init__(self, verificacao: Verificacao) -> None:
        super().__init__(f"[{verificacao.regra}] {verificacao.motivo}")
        self.verificacao = verificacao


@dataclass(frozen=True)
class Forca:
    """Forca vertical em kN com natureza declarada (RT-01, RT-05).

    Ref.: ABNT NBR 6122:2022, item 5.1, p. 13-14
    [rule: NBR6122-5.1-entrada-esforcos]

    Soma e comparacao so entre forcas da mesma natureza; caso contrario
    ErroMisturaDeMetodo.
    """

    valor_kN: float
    natureza: Natureza

    def __add__(self, outra: "Forca") -> "Forca":
        _exigir_mesma_natureza(self, outra, "soma de forcas")
        return Forca(self.valor_kN + outra.valor_kN, self.natureza)

    def __lt__(self, outra: "Forca") -> bool:
        _exigir_mesma_natureza(self, outra, "comparacao de forcas")
        return self.valor_kN < outra.valor_kN

    def __le__(self, outra: "Forca") -> bool:
        _exigir_mesma_natureza(self, outra, "comparacao de forcas")
        return self.valor_kN <= outra.valor_kN

    def __gt__(self, outra: "Forca") -> bool:
        _exigir_mesma_natureza(self, outra, "comparacao de forcas")
        return self.valor_kN > outra.valor_kN

    def __ge__(self, outra: "Forca") -> bool:
        _exigir_mesma_natureza(self, outra, "comparacao de forcas")
        return self.valor_kN >= outra.valor_kN


@dataclass(frozen=True)
class Tensao:
    """Tensao no terreno em kPa com natureza declarada (RT-01, RT-05).

    Ref.: ABNT NBR 6122:2022, itens 3.45 / 3.47 / 3.48, p. 8-9
    [rule: NBR6122-3.30-verificacao-admissivel] [rule: NBR6122-3.31-verificacao-calculo]

    Comparacao (e portanto min/max) so entre tensoes da mesma natureza; caso contrario
    ErroMisturaDeMetodo. Impede, p.ex., sigma_solo_d x sigma_adm e min(sigma_Rd, sigma_ELS).
    """

    valor_kPa: float
    natureza: Natureza

    def __lt__(self, outra: "Tensao") -> bool:
        _exigir_mesma_natureza(self, outra, "comparacao de tensoes")
        return self.valor_kPa < outra.valor_kPa

    def __le__(self, outra: "Tensao") -> bool:
        _exigir_mesma_natureza(self, outra, "comparacao de tensoes")
        return self.valor_kPa <= outra.valor_kPa

    def __gt__(self, outra: "Tensao") -> bool:
        _exigir_mesma_natureza(self, outra, "comparacao de tensoes")
        return self.valor_kPa > outra.valor_kPa

    def __ge__(self, outra: "Tensao") -> bool:
        _exigir_mesma_natureza(self, outra, "comparacao de tensoes")
        return self.valor_kPa >= outra.valor_kPa


@dataclass(frozen=True)
class Grandeza:
    """Numero do memorial, com namespace (RT-02), unidade, natureza e regra de origem (RT-06).

    Ref.: ABNT NBR 6122:2022, item 7.8.1, p. 25
    [rule: NBR6122-6.2.1-7.1-memorial-nao-verificado]

    origem in {"entrada", "calculada", "adotada"}.
    """

    nome: str
    valor: float
    unidade: str
    natureza: Optional[Natureza]
    regra: str
    origem: str


@dataclass(frozen=True)
class NotaMemorial:
    """Texto obrigatorio do memorial associado a uma regra.

    Ref.: ABNT NBR 6122:2022, item 7.8.1, p. 25
    [rule: NBR6122-6.2.1-7.1-memorial-nao-verificado]
    """

    regra: str
    texto: str


@dataclass(frozen=True)
class EsforcosResolvidos:
    """Esforcos verticais no topo da fundacao apos 5.1 / Tabela 1 nota c.

    Ref.: ABNT NBR 6122:2022, item 5.1, p. 13-14; 6.2.1.1.1 (Tabela 1, nota c), p. 17
    [rule: NBR6122-5.1-entrada-esforcos] [rule: NBR6122-T1c-gamma-f]

    N_k sempre presente (ELU admissivel e ELS). N_d so no metodo de calculo.
    """

    N_k: Forca
    N_d: Optional[Forca]
    grandezas: Tuple[Grandeza, ...]
    notas: Tuple[NotaMemorial, ...]


@dataclass(frozen=True)
class TensaoDeReferencia:
    """Limites de tensao resolvidos a partir das entradas do engenheiro.

    Ref.: ABNT NBR 6122:2022, itens 7.3 / 7.4 / 7.2, p. 22-23; 6.2.1.1.1 (Tabela 1), p. 17;
    7.1, p. 21
    [rule: NBR6122-7.3-7.4-entrada-tensao-de-referencia] [rule: NBR6122-T1-resistencia-ELU]
    [rule: NBR6122-7.1-7.4-ELU-e-ELS]

    modo in {"A", "B"}.
    Metodo admissivel: `limite` = sigma_adm (caracteristica; ja atende ELU e ELS);
                       `sigma_ELS` = None.
    Metodo de calculo: `limite` = sigma_Rd (modo A) ou sigma_Rd_ELU (modo B), natureza calculo;
                       `sigma_ELS` obrigatoria (caracteristica), verificada SEPARADAMENTE.
    """

    modo: str
    limite: Tensao
    sigma_ELS: Optional[Tensao]
    grandezas: Tuple[Grandeza, ...]
    notas: Tuple[NotaMemorial, ...]


@dataclass(frozen=True, kw_only=True)
class EntradaSapataCentrada:
    """Entradas da verificacao geotecnica v0 (kN, m, kPa).

    Ref.: ABNT NBR 6122:2022, itens 5.1, p. 13-14; 7.3 / 7.4, p. 22-23; 7.6.1, p. 23
    [rule: NBR6122-5.1-entrada-esforcos] [rule: NBR6122-7.3-7.4-entrada-tensao-de-referencia]
    [rule: NBR6122-7.6.1-tensao-uniforme]

    RT-04: campos sem valor padrao sao obrigatorios na construcao; `None` significa "nao
    informado" e leva a recusa quando a entrada for exigida. Os campos com padrao None sao
    dependentes de modo (exigidos ou proibidos conforme metodo/modo; a cadeia recusa
    combinacoes ausentes, ambiguas ou nao aplicaveis -- nada e ignorado em silencio).
    """

    # --- metodo (RT-01) ---
    metodo: Optional[Metodo]
    # --- geometria (7.6.1, 3.28) ---
    B: Optional[float]
    L: Optional[float]
    D_assentamento: Optional[float]
    # --- esforcos (5.1, 5.6, 7.6.1) ---
    N_k: Optional[float]
    N_d: Optional[float]
    G_k: Optional[float]
    P_solo_k: Optional[float]
    # --- guarda 7.6.2 / 7.6.3 ---
    M_x: Optional[float]
    M_y: Optional[float]
    H_x: Optional[float]
    H_y: Optional[float]
    e_pilar_x: Optional[float]
    e_pilar_y: Optional[float]
    # --- guarda 7.5 ---
    apoio_em_rocha: Optional[bool]
    solo_expansivo: Optional[bool]
    solo_colapsivel: Optional[bool]
    solo_homogeneo_declarado: Optional[bool]
    # --- 7.2 ---
    declaracao_fatores_7_2: Optional[bool]
    # --- opcionais / dependentes de modo ---
    coef_reducao_ao_caracteristico: Optional[float] = None
    G_k_desconhecido: bool = False
    P_pp_real_k: Optional[float] = None
    solicitar_majoracao_vento: bool = False
    sigma_adm: Optional[float] = None
    sigma_Rd: Optional[float] = None
    procedimento_7_3: Optional[Tuple[Procedimento73, ...]] = None
    declaracao_ELS_atendido: Optional[bool] = None
    sigma_ELS: Optional[float] = None
    sigma_r_k: Optional[float] = None
    metodo_resistencia: Optional[MetodoResistencia] = None
    FS_g_proposto: Optional[float] = None
    gamma_m_proposto: Optional[float] = None
    declaracao_dominio_validade_semiempirico: Optional[bool] = None
    declaracao_sem_ponderacao_parametros: Optional[bool] = None
    n_provas_de_carga: Optional[int] = None
    declaracao_provas_fase_projeto_7_3_1: Optional[bool] = None


@dataclass(frozen=True)
class ResultadoGeotecnico:
    """Resultado da verificacao. Sem veredito global (RT-07).

    Ref.: ABNT NBR 6122:2022, itens 6.2.1 / 7.1 / 6.2.2.2.1 / 7.8.1, p. 16-25
    [rule: NBR6122-6.2.1-7.1-memorial-nao-verificado]

    recusado=True  -> `grandezas` e `notas_memorial` vazias (RT-03: nenhum numero parcial);
                      a(s) Verificacao(aplicavel=False) explicam o motivo.
    `nao_verificado` e sempre preenchido.
    """

    metodo: Optional[Metodo]
    recusado: bool
    verificacoes: Tuple[Verificacao, ...]
    grandezas: Tuple[Grandeza, ...]
    notas_memorial: Tuple[NotaMemorial, ...]
    nao_verificado: Tuple[NotaMemorial, ...] = field(default=())

    def grandeza(self, nome: str) -> Grandeza:
        """Busca uma grandeza pelo nome com namespace (ex.: 'geotecnico.area_base').

        Ref.: ABNT NBR 6122:2022, item 7.8.1, p. 25
        [rule: NBR6122-6.2.1-7.1-memorial-nao-verificado]
        """
        encontradas = [g for g in self.grandezas if g.nome == nome]
        if len(encontradas) != 1:
            raise KeyError(f"grandeza '{nome}' ausente ou duplicada ({len(encontradas)})")
        return encontradas[0]

    def verificacao(self, regra: str) -> Verificacao:
        """Busca a verificacao produzida por uma regra.

        Ref.: ABNT NBR 6122:2022, item 7.8.1, p. 25
        [rule: NBR6122-6.2.1-7.1-memorial-nao-verificado]
        """
        encontradas = [v for v in self.verificacoes if v.regra == regra]
        if len(encontradas) != 1:
            raise KeyError(f"verificacao '{regra}' ausente ou duplicada ({len(encontradas)})")
        return encontradas[0]


# =============================================================================
# Auxiliares privados
# =============================================================================
def _exigir_mesma_natureza(a, b, operacao: str) -> None:
    if not isinstance(b, type(a)):
        raise TypeError(f"{operacao}: tipos incompativeis {type(a).__name__} x {type(b).__name__}")
    if a.natureza is not b.natureza:
        raise ErroMisturaDeMetodo(
            f"{operacao} entre naturezas diferentes ({a.natureza.value} x {b.natureza.value}) "
            f"-- proibido por RT-01"
        )


def _recusar(regra: str, motivo: str,
             valores: Tuple[Tuple[str, float, str], ...] = ()) -> NoReturn:
    raise Recusa(Verificacao(regra=regra, aplicavel=False, atende=None, motivo=motivo,
                             valores=valores))


def _num(nome: str, valor, regra: str, *, positivo: bool = False,
         nao_negativo: bool = False) -> float:
    """Valida numero obrigatorio, finito, com sinal exigido. Recusa caso contrario."""
    if valor is None:
        _recusar(regra, f"entrada obrigatoria '{nome}' nao informada (RT-04: sem valor padrao)")
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        _recusar(regra, f"entrada '{nome}' deve ser numero real; recebido {type(valor).__name__}")
    v = float(valor)
    if not math.isfinite(v):
        _recusar(regra, f"entrada '{nome}' nao finita ({valor!r})")
    if positivo and not v > 0.0:
        _recusar(regra, f"entrada '{nome}' deve ser > 0; recebido {v!r}")
    if nao_negativo and not v >= 0.0:
        _recusar(regra, f"entrada '{nome}' deve ser >= 0; recebido {v!r}")
    return v


def _bool(nome: str, valor, regra: str) -> bool:
    """Valida declaracao booleana obrigatoria (bool estrito)."""
    if valor is None:
        _recusar(regra, f"declaracao obrigatoria '{nome}' nao informada (RT-04: sem valor padrao)")
    if not isinstance(valor, bool):
        _recusar(regra, f"declaracao '{nome}' deve ser bool; recebido {type(valor).__name__}")
    return valor


def _exigir_ausente(nome: str, valor, regra: str, contexto: str) -> None:
    if valor is not None:
        _recusar(regra, f"entrada '{nome}' nao se aplica a {contexto}; remova-a "
                        f"(o software nao ignora entradas em silencio)")


def _exigir_natureza(nome: str, g, natureza: Natureza) -> None:
    if g.natureza is not natureza:
        raise ErroMisturaDeMetodo(
            f"'{nome}' deve ter natureza {natureza.value}; recebido {g.natureza.value} (RT-01)"
        )


def _validar_planta(B, L) -> Tuple[float, float]:
    b = _num("geotecnico.B", B, REGRA_TENSAO_UNIFORME, positivo=True)
    l_ = _num("geotecnico.L", L, REGRA_TENSAO_UNIFORME, positivo=True)
    if b > l_:
        _recusar(REGRA_TENSAO_UNIFORME,
                 f"geotecnico.B ({b!r} m) deve ser a MENOR dimensao em planta e geotecnico.L "
                 f"({l_!r} m) a maior (namespaces do ruleset, RT-02)",
                 (("geotecnico.B", b, "m"), ("geotecnico.L", l_, "m")))
    return b, l_


def _como_verificacao(funcao, *args, **kwargs) -> Verificacao:
    try:
        return funcao(*args, **kwargs)
    except Recusa as r:
        return r.verificacao


# =============================================================================
# Guardas (RT-03): devolvem Verificacao; aplicavel=False => caso recusado
# =============================================================================
def guarda_fundacao_rasa(B: Optional[float], L: Optional[float],
                         D_assentamento: Optional[float]) -> Verificacao:
    """Enquadramento como fundacao rasa: D_assentamento < 2 * min(B, L).

    Ref.: ABNT NBR 6122:2022, item 3.28, p. 5
    [rule: NBR6122-3.28-guarda-fundacao-rasa]

    D_assentamento e a MENOR profundidade da base, se nao constante (3.28). Desigualdade
    estrita: D = 2*min(B, L) NAO e rasa. Violada -> recusa (Secao 8 nao implementada).
    Ex.: 0,60 x 0,60 m com D = 1,5 m (divisa, 7.7.2) e recusada -- comportamento correto.
    """
    def _avaliar() -> Verificacao:
        b, l_ = _validar_planta(B, L)
        d = _num("geotecnico.D_assentamento", D_assentamento, REGRA_FUNDACAO_RASA,
                 nao_negativo=True)
        limite = FATOR_PROFUNDIDADE_RASA * min(b, l_)
        valores = (("geotecnico.D_assentamento", d, "m"), ("geotecnico.B", b, "m"),
                   ("geotecnico.L", l_, "m"), ("2*min(B, L)", limite, "m"))
        if d < limite:
            return Verificacao(REGRA_FUNDACAO_RASA, True, True,
                               "fundacao rasa (3.28): D_assentamento < 2*min(B, L)", valores)
        _recusar(REGRA_FUNDACAO_RASA,
                 f"NAO e fundacao rasa (3.28): D_assentamento = {d!r} m >= 2*min(B, L) = "
                 f"{limite!r} m. Fundacao profunda (Secao 8) fora do escopo v0.", valores)

    return _como_verificacao(_avaliar)


def guarda_carga_centrada(M_x: Optional[float], M_y: Optional[float],
                          H_x: Optional[float], H_y: Optional[float],
                          e_pilar_x: Optional[float], e_pilar_y: Optional[float]) -> Verificacao:
    """Recusa de carga excentrica: momentos, forcas horizontais e pilar fora do centro.

    Ref.: ABNT NBR 6122:2022, item 7.6.2, p. 23-24 (e 7.6.3, p. 24)
    [rule: NBR6122-7.6.2-guarda-carga-centrada]

    "Uma fundacao e solicitada por carga excentrica quando estiver submetida a qualquer
    composicao de forcas que incluam ou gerem momentos na fundacao." Aplicavel somente se
    M_x == M_y == H_x == H_y == e_pilar_x == e_pilar_y == 0 (valores declarados, comparacao
    exata). Todos sao obrigatorios: omitir NAO equivale a zero.
    """
    def _avaliar() -> Verificacao:
        entradas = (("M_x", M_x, "kN*m"), ("M_y", M_y, "kN*m"), ("H_x", H_x, "kN"),
                    ("H_y", H_y, "kN"), ("e_pilar_x", e_pilar_x, "m"),
                    ("e_pilar_y", e_pilar_y, "m"))
        valores = tuple((f"cargas.{n}", _num(n, v, REGRA_CARGA_CENTRADA), u)
                        for n, v, u in entradas)
        nao_nulos = [n for n, v, _ in valores if v != 0.0]
        if nao_nulos:
            _recusar(REGRA_CARGA_CENTRADA,
                     "carga excentrica (7.6.2) / horizontal (7.6.3): "
                     f"{', '.join(nao_nulos)} != 0. Fora do escopo v0 (LAC-05/LAC-06); a "
                     "distribuicao uniforme de 7.6.1 nao se aplica.", valores)
        return Verificacao(REGRA_CARGA_CENTRADA, True, True,
                           "carga centrada: momentos, forcas horizontais e excentricidade do "
                           "pilar declarados nulos", valores)

    return _como_verificacao(_avaliar)


def guarda_compressao(N_k: Optional[float], N_d: Optional[float]) -> Verificacao:
    """Tabela 1 vale so para compressao: todo esforco vertical informado deve ser > 0.

    Ref.: ABNT NBR 6122:2022, item 6.2.1.1.1 (Tabela 1), p. 17
    [rule: NBR6122-6.2.1.1.1-guarda-compressao]

    Pelo menos um de N_k, N_d deve ser informado; cada um informado deve ser > 0.
    Tracao/arrancamento (6.2.1 e; 6.2.1.1.2) -> recusa.
    """
    def _avaliar() -> Verificacao:
        if N_k is None and N_d is None:
            _recusar(REGRA_COMPRESSAO,
                     "nenhum esforco vertical informado (cargas.N_k ou cargas.N_d) -- RT-04")
        valores = []
        for nome, v in (("cargas.N_k", N_k), ("cargas.N_d", N_d)):
            if v is None:
                continue
            x = _num(nome, v, REGRA_COMPRESSAO)
            valores.append((nome, x, "kN"))
            if not x > 0.0:
                _recusar(REGRA_COMPRESSAO,
                         f"{nome} = {x!r} kN nao e compressao. Tracao/arrancamento "
                         "(6.2.1 e; 6.2.1.1.2) nao implementado no v0.",
                         tuple(valores))
        return Verificacao(REGRA_COMPRESSAO, True, True, "esforco vertical de compressao",
                           tuple(valores))

    return _como_verificacao(_avaliar)


def guarda_casos_particulares(apoio_em_rocha: Optional[bool], solo_expansivo: Optional[bool],
                              solo_colapsivel: Optional[bool],
                              solo_homogeneo_declarado: Optional[bool]) -> Verificacao:
    """Recusa de rocha, solo expansivo e solo colapsivel; exige declaracao de solo homogeneo.

    Ref.: ABNT NBR 6122:2022, itens 7.5.1 / 7.5.2 / 7.5.3, p. 23 (e 3.41, 3.43, p. 8)
    [rule: NBR6122-7.5-guarda-casos-particulares]

    Aplicavel somente se apoio_em_rocha == solo_expansivo == solo_colapsivel == False e
    solo_homogeneo_declarado == True. O software nao infere homogeneidade de perfil SPT.
    """
    def _avaliar() -> Verificacao:
        r = _bool("apoio_em_rocha", apoio_em_rocha, REGRA_CASOS_PARTICULARES)
        ex = _bool("solo_expansivo", solo_expansivo, REGRA_CASOS_PARTICULARES)
        co = _bool("solo_colapsivel", solo_colapsivel, REGRA_CASOS_PARTICULARES)
        ho = _bool("solo_homogeneo_declarado", solo_homogeneo_declarado,
                   REGRA_CASOS_PARTICULARES)
        motivos = []
        if r:
            motivos.append("apoio em rocha (7.5.1: considerar descontinuidades)")
        if ex:
            motivos.append("solo expansivo (7.5.2)")
        if co:
            motivos.append("solo colapsivel (7.5.3)")
        if not ho:
            motivos.append("solo homogeneo NAO declarado pelo engenheiro")
        if motivos:
            _recusar(REGRA_CASOS_PARTICULARES,
                     "caso particular fora do escopo v0: " + "; ".join(motivos))
        return Verificacao(REGRA_CASOS_PARTICULARES, True, True,
                           "sem rocha, sem solo expansivo/colapsivel; solo homogeneo declarado "
                           "pelo engenheiro")

    return _como_verificacao(_avaliar)


def guarda_vento_sem_majoracao(solicitar_majoracao_vento: bool) -> Verificacao:
    """Majoracao de sigma_adm / sigma_Rd por vento e proibida no v0.

    Ref.: ABNT NBR 6122:2022, itens 6.3.2 / 6.3.3, p. 21
    [rule: NBR6122-6.3-guarda-vento-sem-majoracao]

    Nao majorar e sempre conforme. O fator de majoracao nao existe neste codigo (nem como
    constante 1,0): qualquer pedido de majoracao e recusado.
    """
    def _avaliar() -> Verificacao:
        pedido = _bool("solicitar_majoracao_vento", solicitar_majoracao_vento, REGRA_VENTO)
        if pedido:
            _recusar(REGRA_VENTO,
                     "majoracao por vento solicitada (6.3.2/6.3.3: 15 %/30 %/10 %, FS_g >= 1,6) "
                     "-- nao implementada no v0 (LAC-07, pendencia P-05)")
        return Verificacao(REGRA_VENTO, True, True,
                           "nenhuma majoracao por vento aplicada a tensao de referencia")

    return _como_verificacao(_avaliar)


# =============================================================================
# Esforcos (5.1, Tabela 1 nota c) e peso proprio (5.6)
# =============================================================================
def majorar_gamma_f(F_k: Forca) -> Forca:
    """Esforco de calculo a partir do caracteristico: F_d = 1,4 * F_k.

    Ref.: ABNT NBR 6122:2022, item 6.2.1.1.1 (Tabela 1, nota c), p. 17
    [rule: NBR6122-T1c-gamma-f]

    So se aplica a esforco disponivel apenas em valor caracteristico (metodo de calculo).
    Recebe Forca caracteristica; devolve Forca de calculo.
    """
    _exigir_natureza("F_k", F_k, Natureza.CARACTERISTICA)
    return Forca(GAMMA_F_6122_T1C * F_k.valor_kN, Natureza.CALCULO)


def resolver_esforcos(metodo: Metodo, N_k: Optional[float], N_d: Optional[float],
                      coef_reducao_ao_caracteristico: Optional[float]) -> EsforcosResolvidos:
    """Resolve N_k / N_d conforme o metodo, sem nenhum coeficiente padrao.

    Ref.: ABNT NBR 6122:2022, item 5.1, p. 13-14; 6.2.1.1.1 (Tabela 1, nota c), p. 17
    [rule: NBR6122-5.1-entrada-esforcos] [rule: NBR6122-T1c-gamma-f]
    [rule: NBR6122-7.1-7.4-ELU-e-ELS]

    Admissivel: aceita N_k; ou N_d + coef_reducao (N_k = N_d/coef_reducao). N_d sem
    coef_reducao -> recusa. N_k junto com N_d -> recusa (ambiguo).
    Calculo: N_d fornecido -> usado sem coeficiente; so N_k -> N_d = 1,4*N_k. N_k e exigido
    sempre, porque o ELS (6.2.2.1) compara valores caracteristicos e o ruleset nao autoriza
    reduzir N_d a N_k no metodo de calculo. coef_reducao -> recusa (so admissivel).
    Levanta Recusa.
    """
    if not isinstance(metodo, Metodo):
        _recusar(REQ_METODO, "metodo nao declarado (RT-01)")
    notas = []
    grandezas = []
    if metodo is Metodo.ADMISSIVEL:
        if N_k is not None and (N_d is not None or coef_reducao_ao_caracteristico is not None):
            _recusar(REGRA_ESFORCOS,
                     "metodo admissivel: informe N_k OU (N_d + coef_reducao_ao_caracteristico), "
                     "nao ambos (o software nao escolhe entre entradas concorrentes)")
        if N_k is not None:
            nk = _num("cargas.N_k", N_k, REGRA_ESFORCOS, positivo=True)
            grandezas.append(Grandeza("cargas.N_k", nk, "kN", Natureza.CARACTERISTICA,
                                      REGRA_ESFORCOS, "entrada"))
            return EsforcosResolvidos(Forca(nk, Natureza.CARACTERISTICA), None,
                                      tuple(grandezas), tuple(notas))
        if N_d is None:
            _recusar(REGRA_ESFORCOS, "metodo admissivel: N_k nao informado (RT-04)")
        nd = _num("cargas.N_d", N_d, REGRA_ESFORCOS, positivo=True)
        if coef_reducao_ao_caracteristico is None:
            _recusar(REGRA_ESFORCOS,
                     "metodo admissivel com N_d: coef_reducao_ao_caracteristico obrigatorio, "
                     "fornecido pelo projetista estrutural (5.1); proibido assumir 1,4")
        coef = _num("cargas.coef_reducao_ao_caracteristico", coef_reducao_ao_caracteristico,
                    REGRA_ESFORCOS, positivo=True)
        nk = nd / coef
        grandezas += [
            Grandeza("cargas.N_d", nd, "kN", Natureza.CALCULO, REGRA_ESFORCOS, "entrada"),
            Grandeza("cargas.coef_reducao_ao_caracteristico", coef, "1", None, REGRA_ESFORCOS,
                     "entrada"),
            Grandeza("cargas.N_k", nk, "kN", Natureza.CARACTERISTICA, REGRA_ESFORCOS,
                     "calculada"),
        ]
        notas.append(NotaMemorial(REGRA_ESFORCOS,
                                  "N_k = N_d / coef_reducao_ao_caracteristico (5.1); coeficiente "
                                  "fornecido pelo projetista estrutural"))
        return EsforcosResolvidos(Forca(nk, Natureza.CARACTERISTICA), None, tuple(grandezas),
                                  tuple(notas))

    # --- metodo de calculo ---
    _exigir_ausente("cargas.coef_reducao_ao_caracteristico", coef_reducao_ao_caracteristico,
                    REGRA_ESFORCOS, "metodo de calculo (5.1: so para fator de seguranca global)")
    if N_k is None:
        _recusar(REGRA_ELU_ELS,
                 "metodo de calculo: N_k obrigatorio para a verificacao de ELS em valores "
                 "caracteristicos (6.2.2.1); o ruleset nao autoriza obter N_k a partir de N_d "
                 "neste metodo")
    nk = _num("cargas.N_k", N_k, REGRA_ESFORCOS, positivo=True)
    F_k = Forca(nk, Natureza.CARACTERISTICA)
    grandezas.append(Grandeza("cargas.N_k", nk, "kN", Natureza.CARACTERISTICA, REGRA_ESFORCOS,
                              "entrada"))
    if N_d is not None:
        nd = _num("cargas.N_d", N_d, REGRA_ESFORCOS, positivo=True)
        F_d = Forca(nd, Natureza.CALCULO)
        grandezas.append(Grandeza("cargas.N_d", nd, "kN", Natureza.CALCULO, REGRA_GAMMA_F,
                                  "entrada"))
        notas.append(NotaMemorial(REGRA_GAMMA_F,
                                  "N_d fornecido em valor de calculo: nenhum coeficiente de "
                                  "ponderacao aplicado a ele (Tabela 1, nota c)"))
    else:
        F_d = majorar_gamma_f(F_k)
        grandezas.append(Grandeza("cargas.N_d", F_d.valor_kN, "kN", Natureza.CALCULO,
                                  REGRA_GAMMA_F, "calculada"))
        notas.append(NotaMemorial(REGRA_GAMMA_F,
                                  "N_d = 1,4 * N_k: esforco disponivel apenas em valor "
                                  "caracteristico (Tabela 1, nota c)"))
    return EsforcosResolvidos(F_k, F_d, tuple(grandezas), tuple(notas))


def peso_proprio_considerado(G_k: Forca, P_pp_real_k: Optional[Forca]) -> Forca:
    """Peso proprio considerado: P_pp_k = max(P_pp_real_k, 0,05 * G_k).

    Ref.: ABNT NBR 6122:2022, item 5.6, p. 15
    [rule: NBR6122-5.6-peso-proprio]

    Envoltoria conforme sob as duas leituras do texto (resolucao do A2). Base = carga vertical
    PERMANENTE caracteristica G_k (nao a total). P_pp_real_k ausente (None) -> vale so o piso
    de 5 %. Valores caracteristicos (senao ErroMisturaDeMetodo); G_k e P_pp_real_k devem ser
    >= 0 (senao Recusa).
    """
    _exigir_natureza("cargas.G_k", G_k, Natureza.CARACTERISTICA)
    _num("cargas.G_k", G_k.valor_kN, REGRA_PESO_PROPRIO, nao_negativo=True)
    piso = Forca(FRAC_MIN_PESO_PROPRIO * G_k.valor_kN, Natureza.CARACTERISTICA)
    if P_pp_real_k is None:
        return piso
    _exigir_natureza("cargas.P_pp_real_k", P_pp_real_k, Natureza.CARACTERISTICA)
    _num("cargas.P_pp_real_k", P_pp_real_k.valor_kN, REGRA_PESO_PROPRIO, nao_negativo=True)
    return max(P_pp_real_k, piso)


# =============================================================================
# Geometria e tensao uniforme (7.6.1)
# =============================================================================
def area_base(B: float, L: float) -> float:
    """Area da base retangular, em m2: area_base = B * L.

    Ref.: ABNT NBR 6122:2022, item 7.6.1, p. 23 (DERIVADA_DO_TEXTO)
    [rule: NBR6122-7.6.1-tensao-uniforme]

    B = menor e L = maior dimensao em planta (namespaces); B, L > 0 e B <= L, senao Recusa.
    """
    b, l_ = _validar_planta(B, L)
    return b * l_


def tensao_caracteristica(N_k: Forca, P_pp_k: Forca, P_solo_k: Forca,
                          area_base_m2: float) -> Tensao:
    """Tensao caracteristica uniforme: sigma_solo_k = (N_k + P_pp_k + P_solo_k) / area_base.

    Ref.: ABNT NBR 6122:2022, item 7.6.1, p. 23 (DERIVADA_DO_TEXTO; 3.47, p. 9)
    [rule: NBR6122-7.6.1-tensao-uniforme]

    "admitidas uniformemente distribuidas" -> V/A. O memorial cita "7.6.1 (distribuicao
    uniforme admitida)", nao apresenta a expressao como texto da norma. Todas as parcelas
    caracteristicas (senao ErroMisturaDeMetodo).
    """
    for nome, f in (("cargas.N_k", N_k), ("cargas.P_pp_k", P_pp_k),
                    ("cargas.P_solo_k", P_solo_k)):
        _exigir_natureza(nome, f, Natureza.CARACTERISTICA)
    a = _num("geotecnico.area_base", area_base_m2, REGRA_TENSAO_UNIFORME, positivo=True)
    V_k = N_k + P_pp_k + P_solo_k
    return Tensao(V_k.valor_kN / a, Natureza.CARACTERISTICA)


def tensao_de_calculo(N_d: Forca, P_pp_k: Forca, P_solo_k: Forca,
                      area_base_m2: float) -> Tensao:
    """Tensao de calculo uniforme: sigma_solo_d = (N_d + 1,4*(P_pp_k + P_solo_k)) / area_base.

    Ref.: ABNT NBR 6122:2022, item 7.6.1, p. 23 (DERIVADA_DO_TEXTO); 6.2.1.1.1 (Tabela 1,
    nota c), p. 17
    [rule: NBR6122-7.6.1-tensao-uniforme] [rule: NBR6122-T1c-gamma-f]

    N_d de calculo (sem novo coeficiente); P_pp_k e P_solo_k caracteristicos, majorados por
    gamma_f = 1,4.
    """
    _exigir_natureza("cargas.N_d", N_d, Natureza.CALCULO)
    a = _num("geotecnico.area_base", area_base_m2, REGRA_TENSAO_UNIFORME, positivo=True)
    V_d = N_d + majorar_gamma_f(P_pp_k + P_solo_k)
    return Tensao(V_d.valor_kN / a, Natureza.CALCULO)


def area_minima_admissivel(N_k: Forca, P_pp_k: Forca, P_solo_k: Forca,
                           sigma_adm: Tensao) -> float:
    """Area minima (informativa), metodo admissivel: (N_k + P_pp_k + P_solo_k) / sigma_adm.

    Ref.: ABNT NBR 6122:2022, item 7.6.1, p. 23 (DERIVADA_DO_TEXTO)
    [rule: NBR6122-7.6.1-tensao-uniforme]

    Saida informativa: o v0 verifica B e L fornecidos, nao os propoe (LAC-11).
    """
    for nome, f in (("cargas.N_k", N_k), ("cargas.P_pp_k", P_pp_k),
                    ("cargas.P_solo_k", P_solo_k)):
        _exigir_natureza(nome, f, Natureza.CARACTERISTICA)
    _exigir_natureza("geotecnico.sigma_adm", sigma_adm, Natureza.CARACTERISTICA)
    s = _num("geotecnico.sigma_adm", sigma_adm.valor_kPa, REGRA_TENSAO_UNIFORME, positivo=True)
    return (N_k + P_pp_k + P_solo_k).valor_kN / s


def area_minima_calculo(N_d: Forca, P_pp_k: Forca, P_solo_k: Forca,
                        sigma_Rd: Tensao) -> float:
    """Area minima de ELU (informativa), metodo de calculo: (N_d + 1,4*(P_pp_k+P_solo_k))/sigma_Rd.

    Ref.: ABNT NBR 6122:2022, item 7.6.1, p. 23 (DERIVADA_DO_TEXTO); 6.2.1.1.1 (Tabela 1,
    nota c), p. 17
    [rule: NBR6122-7.6.1-tensao-uniforme] [rule: NBR6122-T1c-gamma-f]

    Somente ELU. O ELS (sigma_solo_k <= sigma_ELS) e verificacao separada e pode governar.
    """
    _exigir_natureza("cargas.N_d", N_d, Natureza.CALCULO)
    _exigir_natureza("geotecnico.sigma_Rd", sigma_Rd, Natureza.CALCULO)
    s = _num("geotecnico.sigma_Rd", sigma_Rd.valor_kPa, REGRA_TENSAO_UNIFORME, positivo=True)
    return (N_d + majorar_gamma_f(P_pp_k + P_solo_k)).valor_kN / s


# =============================================================================
# Tensao de referencia (7.3/7.4), Tabela 1 e ELU+ELS (7.1/7.4)
# =============================================================================
def tensao_limite_ELU_tabela1(
        metodo: Metodo, sigma_r_k: Tensao, metodo_resistencia: Optional[MetodoResistencia], *,
        FS_g_proposto: Optional[float] = None,
        gamma_m_proposto: Optional[float] = None,
        declaracao_dominio_validade_semiempirico: Optional[bool] = None,
        declaracao_sem_ponderacao_parametros: Optional[bool] = None,
        n_provas_de_carga: Optional[int] = None,
        declaracao_provas_fase_projeto_7_3_1: Optional[bool] = None,
) -> Tuple[Tensao, float]:
    """Limite de ELU a partir da ruptura caracteristica, Tabela 1 (compressao).

    Ref.: ABNT NBR 6122:2022, item 6.2.1.1.1 (Tabela 1), p. 17
    [rule: NBR6122-T1-resistencia-ELU]

    Admissivel: sigma_adm_ELU = sigma_r_k / FS_g  (natureza caracteristica).
    Calculo:    sigma_Rd_ELU  = sigma_r_k / gamma_m (natureza calculo).
    Linhas:
      semiempirico        FS_g / gamma_m PROPOSTO no processo (obrigatorio), >= 3,00 / 2,15;
                          declaracao de dominio de validade para o terreno local (nota a).
      analitico           FS_g = 3,00 / gamma_m = 2,15; declaracao de que nao houve
                          ponderacao dos parametros de resistencia (nota b).
      com_provas_de_carga FS_g = 2,00 / gamma_m = 1,40; n_provas_de_carga >= 2 (inteiro) e
                          declaracao de execucao na fase de projeto conforme 7.3.1.
    FS_g so existe no admissivel; gamma_m so no calculo (RT-01). Entradas de outra linha ou
    de outro metodo -> recusa. A saida e SO o limite de ELU, nunca a tensao de projeto
    (ver tensao_admissivel_ELU_ELS / verificar_ELS). Devolve (limite, coeficiente). Levanta
    Recusa.
    """
    if not isinstance(metodo, Metodo):
        _recusar(REQ_METODO, "metodo nao declarado (RT-01)")
    _exigir_natureza("geotecnico.sigma_r_k", sigma_r_k, Natureza.CARACTERISTICA)
    _num("geotecnico.sigma_r_k", sigma_r_k.valor_kPa, REGRA_TABELA1, positivo=True)
    if not isinstance(metodo_resistencia, MetodoResistencia):
        _recusar(REGRA_TABELA1,
                 "metodo_resistencia obrigatorio (semiempirico | analitico | "
                 "com_provas_de_carga) -- RT-04")
    admissivel = metodo is Metodo.ADMISSIVEL
    # RT-01: coeficiente do outro metodo nunca existe.
    if admissivel:
        _exigir_ausente("seguranca.gamma_m", gamma_m_proposto, REQ_METODO, "metodo admissivel")
    else:
        _exigir_ausente("seguranca.FS_g", FS_g_proposto, REQ_METODO, "metodo de calculo")

    linha = metodo_resistencia.value
    if metodo_resistencia is MetodoResistencia.SEMIEMPIRICO:
        _exigir_ausente("declaracao_sem_ponderacao_parametros",
                        declaracao_sem_ponderacao_parametros, REGRA_TABELA1, f"linha {linha}")
        _exigir_ausente("n_provas_de_carga", n_provas_de_carga, REGRA_TABELA1, f"linha {linha}")
        _exigir_ausente("declaracao_provas_fase_projeto_7_3_1",
                        declaracao_provas_fase_projeto_7_3_1, REGRA_TABELA1, f"linha {linha}")
        if not _bool("declaracao_dominio_validade_semiempirico",
                     declaracao_dominio_validade_semiempirico, REGRA_TABELA1):
            _recusar(REGRA_TABELA1,
                     "metodo semiempirico sem declaracao de atendimento ao dominio de validade "
                     "para o terreno local (Tabela 1, nota a)")
        if admissivel:
            coef = _num("seguranca.FS_g", FS_g_proposto, REGRA_TABELA1, positivo=True)
            minimo = FS_G_MIN_SEMIEMPIRICO
        else:
            coef = _num("seguranca.gamma_m", gamma_m_proposto, REGRA_TABELA1, positivo=True)
            minimo = GAMMA_M_MIN_SEMIEMPIRICO
        if coef < minimo:
            nome = "FS_g" if admissivel else "gamma_m"
            _recusar(REGRA_TABELA1,
                     f"{nome} proposto = {coef!r} abaixo do minimo da Tabela 1 para metodo "
                     f"semiempirico ({minimo!r})",
                     ((f"seguranca.{nome}", coef, "1"),))
    else:
        _exigir_ausente("seguranca.FS_g", FS_g_proposto, REGRA_TABELA1,
                        f"linha {linha} (valor fixado pela Tabela 1)")
        _exigir_ausente("seguranca.gamma_m", gamma_m_proposto, REGRA_TABELA1,
                        f"linha {linha} (valor fixado pela Tabela 1)")
        _exigir_ausente("declaracao_dominio_validade_semiempirico",
                        declaracao_dominio_validade_semiempirico, REGRA_TABELA1, f"linha {linha}")
        if metodo_resistencia is MetodoResistencia.ANALITICO:
            _exigir_ausente("n_provas_de_carga", n_provas_de_carga, REGRA_TABELA1,
                            f"linha {linha}")
            _exigir_ausente("declaracao_provas_fase_projeto_7_3_1",
                            declaracao_provas_fase_projeto_7_3_1, REGRA_TABELA1, f"linha {linha}")
            if not _bool("declaracao_sem_ponderacao_parametros",
                         declaracao_sem_ponderacao_parametros, REGRA_TABELA1):
                _recusar(REGRA_TABELA1,
                         "metodo analitico exige declaracao de que nao houve aplicacao de "
                         "coeficientes de ponderacao aos parametros de resistencia do terreno "
                         "(Tabela 1, nota b)")
            coef = FS_G_ANALITICO if admissivel else GAMMA_M_ANALITICO
        else:  # COM_PROVAS_DE_CARGA
            _exigir_ausente("declaracao_sem_ponderacao_parametros",
                            declaracao_sem_ponderacao_parametros, REGRA_TABELA1, f"linha {linha}")
            if n_provas_de_carga is None:
                _recusar(REGRA_TABELA1, "n_provas_de_carga obrigatorio (RT-04)")
            if isinstance(n_provas_de_carga, bool) or not isinstance(n_provas_de_carga, int):
                _recusar(REGRA_TABELA1, "n_provas_de_carga deve ser inteiro")
            if n_provas_de_carga < N_MIN_PROVAS_DE_CARGA:
                _recusar(REGRA_TABELA1,
                         f"linha com provas de carga exige n >= {N_MIN_PROVAS_DE_CARGA}; "
                         f"informado {n_provas_de_carga}")
            if not _bool("declaracao_provas_fase_projeto_7_3_1",
                         declaracao_provas_fase_projeto_7_3_1, REGRA_TABELA1):
                _recusar(REGRA_TABELA1,
                         "provas de carga nao declaradas como executadas na fase de projeto "
                         "conforme 7.3.1 -- linha inacessivel")
            coef = FS_G_COM_PROVAS_DE_CARGA if admissivel else GAMMA_M_COM_PROVAS_DE_CARGA

    if admissivel:
        return Tensao(sigma_r_k.valor_kPa / coef, Natureza.CARACTERISTICA), coef
    return Tensao(sigma_r_k.valor_kPa / coef, Natureza.CALCULO), coef


def tensao_admissivel_ELU_ELS(sigma_adm_ELU: Tensao, sigma_ELS: Tensao) -> Tensao:
    """Tensao admissivel que atende simultaneamente ELU e ELS: min(sigma_adm_ELU, sigma_ELS).

    Ref.: ABNT NBR 6122:2022, itens 7.1, p. 21 / 7.4, p. 23 (DERIVADA_DO_TEXTO)
    [rule: NBR6122-7.1-7.4-ELU-e-ELS]

    SO metodo admissivel (modo B): ambos caracteristicos. No metodo de calculo o min()
    misturaria bases (RT-01) -> ErroMisturaDeMetodo; use verificar_ELS.
    """
    _exigir_natureza("geotecnico.sigma_adm_ELU", sigma_adm_ELU, Natureza.CARACTERISTICA)
    _exigir_natureza("geotecnico.sigma_ELS", sigma_ELS, Natureza.CARACTERISTICA)
    return min(sigma_adm_ELU, sigma_ELS)


def resolver_tensao_de_referencia(
        metodo: Metodo, *,
        declaracao_fatores_7_2: Optional[bool],
        sigma_adm: Optional[float] = None,
        sigma_Rd: Optional[float] = None,
        procedimento_7_3: Optional[Tuple[Procedimento73, ...]] = None,
        declaracao_ELS_atendido: Optional[bool] = None,
        sigma_ELS: Optional[float] = None,
        sigma_r_k: Optional[float] = None,
        metodo_resistencia: Optional[MetodoResistencia] = None,
        FS_g_proposto: Optional[float] = None,
        gamma_m_proposto: Optional[float] = None,
        declaracao_dominio_validade_semiempirico: Optional[bool] = None,
        declaracao_sem_ponderacao_parametros: Optional[bool] = None,
        n_provas_de_carga: Optional[int] = None,
        declaracao_provas_fase_projeto_7_3_1: Optional[bool] = None,
) -> TensaoDeReferencia:
    """Contrato de entrada da tensao de referencia (fornecida e assumida pelo engenheiro).

    Ref.: ABNT NBR 6122:2022, itens 7.3 / 7.4 / 7.2, p. 22-23; 6.2.1.1.1 (Tabela 1), p. 17;
    7.1, p. 21
    [rule: NBR6122-7.3-7.4-entrada-tensao-de-referencia] [rule: NBR6122-T1-resistencia-ELU]
    [rule: NBR6122-7.1-7.4-ELU-e-ELS]

    Modo A (tensao final):
      admissivel: sigma_adm, procedimento_7_3, declaracao_ELS_atendido=True,
                  declaracao_fatores_7_2=True. sigma_ELS nao se aplica (3.45).
      calculo:    sigma_Rd, sigma_ELS, procedimento_7_3, declaracao_fatores_7_2=True.
    Modo B (ruptura caracteristica): sigma_r_k, metodo_resistencia, sigma_ELS,
      declaracao_fatores_7_2=True (+ entradas da linha da Tabela 1).
      admissivel: sigma_adm = min(sigma_r_k/FS_g, sigma_ELS).
      calculo:    sigma_Rd_ELU = sigma_r_k/gamma_m; ELS verificado a parte.
    O software NAO calcula sigma_r_k nem sigma_adm a partir de ensaio. Entradas de modos
    concorrentes ou nao aplicaveis -> recusa. Levanta Recusa.
    """
    if not isinstance(metodo, Metodo):
        _recusar(REQ_METODO, "metodo nao declarado (RT-01)")
    R = REGRA_TENSAO_REFERENCIA
    if not _bool("declaracao_fatores_7_2", declaracao_fatores_7_2, R):
        _recusar(R, "falta declaracao do engenheiro de que os fatores de 7.2 foram considerados "
                    "na fixacao da tensao de referencia")
    admissivel = metodo is Metodo.ADMISSIVEL
    if admissivel:
        _exigir_ausente("geotecnico.sigma_Rd", sigma_Rd, REQ_METODO, "metodo admissivel")
        tensao_final = sigma_adm
    else:
        _exigir_ausente("geotecnico.sigma_adm", sigma_adm, REQ_METODO, "metodo de calculo")
        tensao_final = sigma_Rd
    nome_final = "geotecnico.sigma_adm" if admissivel else "geotecnico.sigma_Rd"

    if tensao_final is not None and sigma_r_k is not None:
        _recusar(R, f"informe {nome_final} (modo A) OU geotecnico.sigma_r_k (modo B), nao ambos")
    if tensao_final is None and sigma_r_k is None:
        _recusar(R, f"tensao de referencia nao informada: {nome_final} (modo A) ou "
                    "geotecnico.sigma_r_k + metodo_resistencia (modo B) -- RT-04")

    grandezas = []
    notas = [NotaMemorial(REGRA_TENSAO_REFERENCIA,
                          "a tensao de referencia do terreno foi fixada e e assumida pelo "
                          "engenheiro (7.2, 7.3, 7.4); o software nao a calcula")]

    if tensao_final is not None:
        # ------------------------------ modo A ------------------------------
        for nome, v in (("metodo_resistencia", metodo_resistencia),
                        ("seguranca.FS_g", FS_g_proposto),
                        ("seguranca.gamma_m", gamma_m_proposto),
                        ("declaracao_dominio_validade_semiempirico",
                         declaracao_dominio_validade_semiempirico),
                        ("declaracao_sem_ponderacao_parametros",
                         declaracao_sem_ponderacao_parametros),
                        ("n_provas_de_carga", n_provas_de_carga),
                        ("declaracao_provas_fase_projeto_7_3_1",
                         declaracao_provas_fase_projeto_7_3_1)):
            _exigir_ausente(nome, v, R, "modo A (tensao final fornecida)")
        if (not isinstance(procedimento_7_3, tuple) or len(procedimento_7_3) == 0
                or not all(isinstance(p, Procedimento73) for p in procedimento_7_3)):
            _recusar(R, "procedimento_7_3 obrigatorio no modo A: tupla nao vazia de "
                        "Procedimento73 (7.3.1 | 7.3.2 | 7.3.3)")
        valor = _num(nome_final, tensao_final, R, positivo=True)
        procs = ", ".join(sorted(p.value for p in set(procedimento_7_3)))
        notas.append(NotaMemorial(R, f"procedimento(s) declarado(s) para a tensao de referencia: "
                                     f"{procs}"))
        if admissivel:
            _exigir_ausente("geotecnico.sigma_ELS", sigma_ELS, REGRA_ELU_ELS,
                            "modo A admissivel (3.45: sigma_adm ja atende ELU e ELS)")
            if not _bool("declaracao_ELS_atendido", declaracao_ELS_atendido, R):
                _recusar(R, "modo A admissivel exige declaracao de que sigma_adm atende o ELS "
                            "(7.4 / 3.45)")
            limite = Tensao(valor, Natureza.CARACTERISTICA)
            grandezas.append(Grandeza("geotecnico.sigma_adm", valor, "kPa",
                                      Natureza.CARACTERISTICA, R, "entrada"))
            notas.append(NotaMemorial(REGRA_ELU_ELS,
                                      "sigma_adm fornecida declarada como atendendo ELU e ELS "
                                      "(3.45); ELS nao verificado separadamente"))
            return TensaoDeReferencia("A", limite, None, tuple(grandezas), tuple(notas))
        _exigir_ausente("declaracao_ELS_atendido", declaracao_ELS_atendido, REGRA_ELU_ELS,
                        "metodo de calculo (o ELS e verificado contra sigma_ELS)")
        s_els = _num("geotecnico.sigma_ELS", sigma_ELS, REGRA_ELU_ELS, positivo=True)
        grandezas += [
            Grandeza("geotecnico.sigma_Rd", valor, "kPa", Natureza.CALCULO, R, "entrada"),
            Grandeza("geotecnico.sigma_ELS", s_els, "kPa", Natureza.CARACTERISTICA,
                     REGRA_ELU_ELS, "entrada"),
        ]
        return TensaoDeReferencia("A", Tensao(valor, Natureza.CALCULO),
                                  Tensao(s_els, Natureza.CARACTERISTICA), tuple(grandezas),
                                  tuple(notas))

    # -------------------------------- modo B --------------------------------
    _exigir_ausente("procedimento_7_3", procedimento_7_3, R,
                    "modo B (o metodo e declarado em metodo_resistencia)")
    _exigir_ausente("declaracao_ELS_atendido", declaracao_ELS_atendido, REGRA_ELU_ELS,
                    "modo B (o ELS e tratado com sigma_ELS)")
    s_rk = _num("geotecnico.sigma_r_k", sigma_r_k, REGRA_TABELA1, positivo=True)
    s_els = _num("geotecnico.sigma_ELS", sigma_ELS, REGRA_ELU_ELS, positivo=True)
    limite_ELU, coef = tensao_limite_ELU_tabela1(
        metodo, Tensao(s_rk, Natureza.CARACTERISTICA), metodo_resistencia,
        FS_g_proposto=FS_g_proposto, gamma_m_proposto=gamma_m_proposto,
        declaracao_dominio_validade_semiempirico=declaracao_dominio_validade_semiempirico,
        declaracao_sem_ponderacao_parametros=declaracao_sem_ponderacao_parametros,
        n_provas_de_carga=n_provas_de_carga,
        declaracao_provas_fase_projeto_7_3_1=declaracao_provas_fase_projeto_7_3_1)
    T_els = Tensao(s_els, Natureza.CARACTERISTICA)
    grandezas += [
        Grandeza("geotecnico.sigma_r_k", s_rk, "kPa", Natureza.CARACTERISTICA, REGRA_TABELA1,
                 "entrada"),
        Grandeza("geotecnico.sigma_ELS", s_els, "kPa", Natureza.CARACTERISTICA, REGRA_ELU_ELS,
                 "entrada"),
    ]
    origem_coef = ("entrada" if metodo_resistencia is MetodoResistencia.SEMIEMPIRICO
                   else "adotada")
    notas.append(NotaMemorial(REGRA_TABELA1,
                              f"metodo de determinacao de sigma_r_k declarado: "
                              f"{metodo_resistencia.value} (Tabela 1)"))
    if admissivel:
        sigma_adm_proj = tensao_admissivel_ELU_ELS(limite_ELU, T_els)
        grandezas += [
            Grandeza("seguranca.FS_g", coef, "1", None, REGRA_TABELA1, origem_coef),
            Grandeza("geotecnico.sigma_adm_ELU", limite_ELU.valor_kPa, "kPa",
                     Natureza.CARACTERISTICA, REGRA_TABELA1, "calculada"),
            Grandeza("geotecnico.sigma_adm", sigma_adm_proj.valor_kPa, "kPa",
                     Natureza.CARACTERISTICA, REGRA_ELU_ELS, "calculada"),
        ]
        notas.append(NotaMemorial(REGRA_ELU_ELS,
                                  "sigma_adm = min(sigma_adm_ELU, sigma_ELS) (7.1/7.4); "
                                  "sigma_adm_ELU sozinho NAO e tensao admissivel"))
        return TensaoDeReferencia("B", sigma_adm_proj, None, tuple(grandezas), tuple(notas))
    grandezas += [
        Grandeza("seguranca.gamma_m", coef, "1", None, REGRA_TABELA1, origem_coef),
        Grandeza("geotecnico.sigma_Rd_ELU", limite_ELU.valor_kPa, "kPa", Natureza.CALCULO,
                 REGRA_TABELA1, "calculada"),
    ]
    notas.append(NotaMemorial(REGRA_ELU_ELS,
                              "metodo de calculo: ELU (sigma_solo_d <= sigma_Rd_ELU) e ELS "
                              "(sigma_solo_k <= sigma_ELS) verificados separadamente; nenhum "
                              "min() entre bases diferentes"))
    return TensaoDeReferencia("B", limite_ELU, T_els, tuple(grandezas), tuple(notas))


# =============================================================================
# Verificacoes de seguranca
# =============================================================================
def verificar_admissivel(sigma_solo_k: Tensao, sigma_adm: Tensao) -> Verificacao:
    """Condicao de seguranca, metodo de valores admissiveis: sigma_solo_k <= sigma_adm.

    Ref.: ABNT NBR 6122:2022, item 3.30, p. 6 (LITERAL_COM_VINCULACAO a 3.45 e 3.47, p. 8-9)
    [rule: NBR6122-3.30-verificacao-admissivel]

    "Padm >= Sk" com S_k := sigma_solo_k (tensao de trabalho caracteristica, 3.47) -- vinculacao
    do A2 que corrige o defeito dimensional da redacao. Ambas caracteristicas (RT-01).
    """
    _exigir_natureza("geotecnico.sigma_solo_k", sigma_solo_k, Natureza.CARACTERISTICA)
    _exigir_natureza("geotecnico.sigma_adm", sigma_adm, Natureza.CARACTERISTICA)
    atende = sigma_solo_k <= sigma_adm
    return Verificacao(
        REGRA_VERIF_ADMISSIVEL, True, atende,
        ("sigma_solo_k <= sigma_adm" if atende else "sigma_solo_k > sigma_adm"),
        (("geotecnico.sigma_solo_k", sigma_solo_k.valor_kPa, "kPa"),
         ("geotecnico.sigma_adm", sigma_adm.valor_kPa, "kPa")))


def verificar_calculo(sigma_solo_d: Tensao, sigma_Rd: Tensao) -> Verificacao:
    """Condicao de seguranca, metodo de valores de calculo (ELU): sigma_solo_d <= sigma_Rd.

    Ref.: ABNT NBR 6122:2022, item 3.31, p. 6 (LITERAL_COM_VINCULACAO a 3.48, p. 9)
    [rule: NBR6122-3.31-verificacao-calculo]

    "Rd >= Sd" com S_d := sigma_solo_d. Ambas de calculo (RT-01). sigma_Rd e o valor de
    modo A ou sigma_Rd_ELU (modo B).
    """
    _exigir_natureza("geotecnico.sigma_solo_d", sigma_solo_d, Natureza.CALCULO)
    _exigir_natureza("geotecnico.sigma_Rd", sigma_Rd, Natureza.CALCULO)
    atende = sigma_solo_d <= sigma_Rd
    return Verificacao(
        REGRA_VERIF_CALCULO, True, atende,
        ("sigma_solo_d <= sigma_Rd" if atende else "sigma_solo_d > sigma_Rd"),
        (("geotecnico.sigma_solo_d", sigma_solo_d.valor_kPa, "kPa"),
         ("geotecnico.sigma_Rd", sigma_Rd.valor_kPa, "kPa")))


def verificar_ELS(sigma_solo_k: Tensao, sigma_ELS: Tensao) -> Verificacao:
    """Verificacao de ELS em valores caracteristicos: sigma_solo_k <= sigma_ELS.

    Ref.: ABNT NBR 6122:2022, itens 7.1, p. 21 / 7.4, p. 23 (e 6.2.2.1, p. 20)
    [rule: NBR6122-7.1-7.4-ELU-e-ELS]

    Obrigatoria no metodo de calculo (sigma_Rd e definido so pela ruptura). sigma_ELS e
    declarada pelo engenheiro; o v0 nao calcula recalque (LAC-04).
    """
    _exigir_natureza("geotecnico.sigma_solo_k", sigma_solo_k, Natureza.CARACTERISTICA)
    _exigir_natureza("geotecnico.sigma_ELS", sigma_ELS, Natureza.CARACTERISTICA)
    atende = sigma_solo_k <= sigma_ELS
    return Verificacao(
        REGRA_ELU_ELS, True, atende,
        ("sigma_solo_k <= sigma_ELS" if atende else "sigma_solo_k > sigma_ELS"),
        (("geotecnico.sigma_solo_k", sigma_solo_k.valor_kPa, "kPa"),
         ("geotecnico.sigma_ELS", sigma_ELS.valor_kPa, "kPa")))


def verificacoes_nao_executadas() -> Tuple[NotaMemorial, ...]:
    """Lista obrigatoria de verificacoes NAO realizadas (RT-07).

    Ref.: ABNT NBR 6122:2022, itens 6.2.1 / 7.1 / 6.2.2.2.1 / 7.8.1, p. 16, 17, 20, 21, 25
    [rule: NBR6122-6.2.1-7.1-memorial-nao-verificado]

    Conteudo literal do ruleset, acrescido das regras aprovadas 7.7.1-7.7.3, que pertencem a
    restricoes.py e nao sao executadas por este modulo.
    """
    return (tuple(NotaMemorial(REGRA_MEMORIAL, t) for t in _CONTEUDO_OBRIGATORIO_NAO_VERIFICADO)
            + tuple(NotaMemorial(r, t) for r, t in _NAO_EXECUTADAS_NESTE_MODULO))


# =============================================================================
# Cadeia completa
# =============================================================================
def verificar_sapata_centrada(e: EntradaSapataCentrada) -> ResultadoGeotecnico:
    """Verificacao geotecnica v0 de sapata isolada sob carga vertical centrada.

    Ref.: ABNT NBR 6122:2022, itens 3.28, p. 5; 3.30 / 3.31, p. 6; 5.1, p. 13-14; 5.6, p. 15;
    6.2.1.1.1 (Tabela 1), p. 17; 6.3.2 / 6.3.3, p. 21; 7.1, p. 21; 7.3 / 7.4, p. 22-23;
    7.5, p. 23; 7.6.1 / 7.6.2, p. 23-24
    [rule: NBR6122-3.28-guarda-fundacao-rasa] [rule: NBR6122-7.6.2-guarda-carga-centrada]
    [rule: NBR6122-6.2.1.1.1-guarda-compressao] [rule: NBR6122-7.5-guarda-casos-particulares]
    [rule: NBR6122-6.3-guarda-vento-sem-majoracao]
    [rule: NBR6122-7.3-7.4-entrada-tensao-de-referencia] [rule: NBR6122-5.1-entrada-esforcos]
    [rule: NBR6122-5.6-peso-proprio] [rule: NBR6122-7.6.1-tensao-uniforme]
    [rule: NBR6122-3.30-verificacao-admissivel] [rule: NBR6122-3.31-verificacao-calculo]
    [rule: NBR6122-T1-resistencia-ELU] [rule: NBR6122-T1c-gamma-f]
    [rule: NBR6122-7.1-7.4-ELU-e-ELS] [rule: NBR6122-6.2.1-7.1-memorial-nao-verificado]

    Ordem: metodo -> todas as guardas (todas avaliadas e reportadas) -> se alguma recusar,
    PARA sem numeros -> esforcos -> peso proprio -> tensao de referencia -> tensoes atuantes
    -> verificacoes. Qualquer Recusa na cadeia tambem para sem numeros (RT-03).
    Nao executa 7.7.1-7.7.3 (restricoes.py). Sem veredito global (RT-07).
    """
    nao_verificado = verificacoes_nao_executadas()
    metodo = e.metodo if isinstance(e.metodo, Metodo) else None

    def _recusado(verifs) -> ResultadoGeotecnico:
        return ResultadoGeotecnico(metodo=metodo, recusado=True, verificacoes=tuple(verifs),
                                   grandezas=(), notas_memorial=(),
                                   nao_verificado=nao_verificado)

    if metodo is None:
        return _recusado([Verificacao(REQ_METODO, False, None,
                                      "metodo (admissivel | calculo) obrigatorio, declarado na "
                                      "entrada e imutavel (RT-01, RT-04)")])

    guardas = (
        guarda_fundacao_rasa(e.B, e.L, e.D_assentamento),
        guarda_carga_centrada(e.M_x, e.M_y, e.H_x, e.H_y, e.e_pilar_x, e.e_pilar_y),
        guarda_compressao(e.N_k, e.N_d),
        guarda_casos_particulares(e.apoio_em_rocha, e.solo_expansivo, e.solo_colapsivel,
                                  e.solo_homogeneo_declarado),
        guarda_vento_sem_majoracao(e.solicitar_majoracao_vento),
    )
    if any(not g.aplicavel for g in guardas):
        return _recusado(guardas)

    try:
        grandezas, notas, verifs = _cadeia(metodo, e)
    except Recusa as r:
        return _recusado(guardas + (r.verificacao,))

    return ResultadoGeotecnico(metodo=metodo, recusado=False, verificacoes=guardas + verifs,
                               grandezas=grandezas, notas_memorial=notas,
                               nao_verificado=nao_verificado)


def _cadeia(metodo: Metodo, e: EntradaSapataCentrada):
    grandezas = []
    notas = []

    # --- geometria (7.6.1) ---
    b, l_ = _validar_planta(e.B, e.L)
    a = area_base(b, l_)
    d = _num("geotecnico.D_assentamento", e.D_assentamento, REGRA_FUNDACAO_RASA,
             nao_negativo=True)
    grandezas += [
        Grandeza("geotecnico.B", b, "m", None, REGRA_TENSAO_UNIFORME, "entrada"),
        Grandeza("geotecnico.L", l_, "m", None, REGRA_TENSAO_UNIFORME, "entrada"),
        Grandeza("geotecnico.D_assentamento", d, "m", None, REGRA_FUNDACAO_RASA, "entrada"),
        Grandeza("geotecnico.area_base", a, "m**2", None, REGRA_TENSAO_UNIFORME, "calculada"),
    ]

    # --- esforcos (5.1, Tabela 1 nota c) ---
    esf = resolver_esforcos(metodo, e.N_k, e.N_d, e.coef_reducao_ao_caracteristico)
    grandezas += esf.grandezas
    notas += esf.notas

    # --- G_k (5.6) ---
    desconhecido = _bool("G_k_desconhecido", e.G_k_desconhecido, REGRA_PESO_PROPRIO)
    if desconhecido:
        _exigir_ausente("cargas.G_k", e.G_k, REGRA_PESO_PROPRIO,
                        "declaracao G_k_desconhecido=True (contraditorio)")
        G_k = Forca(esf.N_k.valor_kN, Natureza.CARACTERISTICA)
        grandezas.append(Grandeza("cargas.G_k", G_k.valor_kN, "kN", Natureza.CARACTERISTICA,
                                  REGRA_PESO_PROPRIO, "adotada"))
        notas.append(NotaMemorial(REGRA_PESO_PROPRIO,
                                  "G_k declarado desconhecido: adotado G_k := N_k (conservador, "
                                  "N_k >= G_k)"))
    else:
        if e.G_k is None:
            _recusar(REGRA_PESO_PROPRIO,
                     "cargas.G_k obrigatorio (ou declarar G_k_desconhecido=True) -- RT-04")
        gk = _num("cargas.G_k", e.G_k, REGRA_PESO_PROPRIO, nao_negativo=True)
        G_k = Forca(gk, Natureza.CARACTERISTICA)
        grandezas.append(Grandeza("cargas.G_k", gk, "kN", Natureza.CARACTERISTICA,
                                  REGRA_PESO_PROPRIO, "entrada"))

    # --- peso proprio (5.6) ---
    if e.P_pp_real_k is None:
        P_pp_real = None
        notas.append(NotaMemorial(REGRA_PESO_PROPRIO,
                                  "peso real nao informado: considerado o piso de 5 % da carga "
                                  "vertical permanente (5.6)"))
    else:
        P_pp_real = Forca(_num("cargas.P_pp_real_k", e.P_pp_real_k, REGRA_PESO_PROPRIO,
                               nao_negativo=True), Natureza.CARACTERISTICA)
        grandezas.append(Grandeza("cargas.P_pp_real_k", P_pp_real.valor_kN, "kN",
                                  Natureza.CARACTERISTICA, REGRA_PESO_PROPRIO, "entrada"))
    P_pp_k = peso_proprio_considerado(G_k, P_pp_real)
    grandezas.append(Grandeza("cargas.P_pp_k", P_pp_k.valor_kN, "kN", Natureza.CARACTERISTICA,
                              REGRA_PESO_PROPRIO, "calculada"))

    # --- solo sobre a sapata (7.6.1, P-03) ---
    P_solo_k = Forca(_num("cargas.P_solo_k", e.P_solo_k, REGRA_TENSAO_UNIFORME,
                          nao_negativo=True), Natureza.CARACTERISTICA)
    grandezas.append(Grandeza("cargas.P_solo_k", P_solo_k.valor_kN, "kN",
                              Natureza.CARACTERISTICA, REGRA_TENSAO_UNIFORME, "entrada"))
    notas.append(NotaMemorial(REGRA_TENSAO_UNIFORME,
                              f"peso do solo sobre a sapata declarado pelo engenheiro: "
                              f"P_solo_k = {P_solo_k.valor_kN!r} kN (incluir ou nao depende de "
                              f"sigma de referencia bruta x liquida -- decisao do engenheiro)"))

    # --- tensao de referencia (7.3/7.4, Tabela 1, 7.1/7.4) ---
    ref = resolver_tensao_de_referencia(
        metodo,
        declaracao_fatores_7_2=e.declaracao_fatores_7_2,
        sigma_adm=e.sigma_adm, sigma_Rd=e.sigma_Rd, procedimento_7_3=e.procedimento_7_3,
        declaracao_ELS_atendido=e.declaracao_ELS_atendido, sigma_ELS=e.sigma_ELS,
        sigma_r_k=e.sigma_r_k, metodo_resistencia=e.metodo_resistencia,
        FS_g_proposto=e.FS_g_proposto, gamma_m_proposto=e.gamma_m_proposto,
        declaracao_dominio_validade_semiempirico=e.declaracao_dominio_validade_semiempirico,
        declaracao_sem_ponderacao_parametros=e.declaracao_sem_ponderacao_parametros,
        n_provas_de_carga=e.n_provas_de_carga,
        declaracao_provas_fase_projeto_7_3_1=e.declaracao_provas_fase_projeto_7_3_1)
    grandezas += ref.grandezas
    notas += ref.notas

    # --- tensoes atuantes (7.6.1) e verificacoes ---
    notas.append(NotaMemorial(REGRA_TENSAO_UNIFORME,
                              "7.6.1 (distribuicao uniforme admitida): sigma = V/(B*L) e "
                              "expressao DERIVADA do texto, nao texto literal da norma"))
    s_k = tensao_caracteristica(esf.N_k, P_pp_k, P_solo_k, a)
    grandezas.append(Grandeza("geotecnico.sigma_solo_k", s_k.valor_kPa, "kPa",
                              Natureza.CARACTERISTICA, REGRA_TENSAO_UNIFORME, "calculada"))
    verifs = []
    if metodo is Metodo.ADMISSIVEL:
        a_min = area_minima_admissivel(esf.N_k, P_pp_k, P_solo_k, ref.limite)
        grandezas.append(Grandeza("geotecnico.area_min", a_min, "m**2", None,
                                  REGRA_TENSAO_UNIFORME, "calculada"))
        verifs.append(verificar_admissivel(s_k, ref.limite))
    else:
        grandezas.append(Grandeza("seguranca.gamma_f", GAMMA_F_6122_T1C, "1", None,
                                  REGRA_GAMMA_F, "adotada"))
        s_d = tensao_de_calculo(esf.N_d, P_pp_k, P_solo_k, a)
        grandezas.append(Grandeza("geotecnico.sigma_solo_d", s_d.valor_kPa, "kPa",
                                  Natureza.CALCULO, REGRA_TENSAO_UNIFORME, "calculada"))
        a_min = area_minima_calculo(esf.N_d, P_pp_k, P_solo_k, ref.limite)
        grandezas.append(Grandeza("geotecnico.area_min", a_min, "m**2", None,
                                  REGRA_TENSAO_UNIFORME, "calculada"))
        notas.append(NotaMemorial(REGRA_TENSAO_UNIFORME,
                                  "geotecnico.area_min no metodo de calculo refere-se so ao ELU; "
                                  "o ELS e verificado separadamente e pode governar"))
        verifs.append(verificar_calculo(s_d, ref.limite))
        verifs.append(verificar_ELS(s_k, ref.sigma_ELS))
    notas.append(NotaMemorial(REGRA_TENSAO_UNIFORME,
                              "geotecnico.area_min e saida informativa; B e L sao do engenheiro "
                              "(modo verificacao)"))
    return tuple(grandezas), tuple(notas), tuple(verifs)
