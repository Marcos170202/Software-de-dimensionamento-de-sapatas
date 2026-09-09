"""
projeto.py
----------
Salvar/abrir um projeto do escopo AMPLO em um formato próprio (`.s7proj`).

Restrição de a3-interface.md: esta tela não calcula nada. Este módulo só
serializa/desserializa os objetos de entrada de `calc_core.sapata_isolada`
que `ui/completo/formulario.py::PainelEntrada` já lê hoje (`ler_pilar`,
`ler_materiais`, `ler_perfil`, `ler_solo`, `ler_casos`, `ler_opcoes`) — nenhum
número novo é produzido aqui.

`ResultadoSapata` NÃO é salvo: ao abrir um projeto, os dados voltam ao
formulário e o usuário aperta Calcular (F5) de novo. Isso evita qualquer
risco de um resultado salvo ficar dessincronizado do código de cálculo que o
gerou — decisão explícita do escopo desta funcionalidade.

Formato do arquivo
-------------------
JSON puro por dentro; a extensão `.s7proj` só evita que o usuário confunda o
arquivo com um JSON genérico nos diálogos de "salvar como". Cabeçalho fixo,
para permitir versionamento futuro do formato sem quebrar leitura:

    {
      "formato": "sapata7-projeto",
      "versao": 1,
      "pilar": {...},
      "solo": {...},
      "concreto": {...},
      "aco": {...},
      "cobrimento": <float, metros>,
      "casos": [...],
      "opcoes": {...}
    }

Qualquer arquivo malformado (JSON inválido, cabeçalho ausente/errado, versão
desconhecida, chave obrigatória faltando) levanta `ValueError` com mensagem
em português citando o problema — nunca devolve um projeto parcial em
silêncio.

Campos que a TELA repõe vs. campos que voltam ao default (MEDIA #4 do GATE 2,
rodada 2)
--------------------------------------------------------------------------
`salvar_projeto` grava TODOS os campos dos objetos de entrada (nada é
omitido). `carregar_projeto` também os LÊ todos de volta — o dict que ela
devolve é fiel ao arquivo. A perda acontece um passo depois, em
`ui/completo/formulario.py::PainelEntrada.preencher_*` (chamado por
`ui/completo/app.py::_abrir_projeto`): a TELA só tem widget para um
subconjunto de cada objeto, então `preencher_*` só repõe esse subconjunto —
o resto do dataclass reconstruído por `carregar_projeto` é descartado
quando o `ler_*` seguinte (ex.: no próximo F5) reconstrói o objeto do zero
a partir dos widgets, que aplicam o default de fábrica do dataclass para
qualquer campo sem widget. Isso é TRANSPARENTE para round-trips
Python-a-Python (`test_projeto_round_trip_bit_identico`, que não passa pela
tela), mas SILENCIOSO para o fluxo real "Salvar → Abrir" pela interface —
por isso `_abrir_projeto` usa `campos_divergentes_do_default` (abaixo) para
avisar nominalmente o que será perdido, ANTES de o usuário apertar F5 de
novo. Campos sem widget na tela hoje:

  * `Pilar`: `n_barras`, `as_calc_efetiva`.
  * `Solo`: `fator_atrito_base`, `fs_deslizamento`, `fs_tombamento`,
    `coef_sigma_max_excentrico`.
  * `Concreto`: `gamma_c`, `peso_especifico`.
  * `Aco`: `gamma_s`, `Es` (`categoria` fica de fora: é sempre re-inferida
    de `fyk`, que a tela restaura — ver `CAMPOS_NAO_REPOSTOS` abaixo).
  * `CasoCarga` (cada caso G/Q/W): `tipo`, `psi0`, `psi1`, `psi2`,
    `reversivel` — a tela sempre reconstrói o tipo/psi de fábrica do NOME
    do slot (`CasoCarga(...)`/`.acidental(...)`/`.vento(...)`), não o valor
    salvo.
  * `OpcoesProjeto`: todos os campos escalares/avançados EXCETO
    `modelo_reacao`, `modelo_armadura_rigida`, `geometria_imposta` e
    `armaduras_impostas` (esses quatro têm widget e são repostos) — ver
    `CAMPOS_NAO_REPOSTOS` abaixo para a lista completa e exata.

Dar à tela um widget para cada um desses ~25 campos avançados (a correção
"ideal": guardar o dict carregado inteiro e reaplicá-lo como BASE em cada
`ler_*`, sobrescrevendo só o que os widgets editam) fica para uma rodada
futura — risco de regressão maior do que o tempo desta rodada permite
auditar com segurança (ver `relatorios/revisao_codigo.json`: o padrão desta
feature tem sido "corrigir um defeito abre outro do mesmo tipo no caminho
vizinho"); o aviso explícito abaixo é o mínimo aceitável enquanto isso não
acontece.
"""
from __future__ import annotations

import contextlib
import json
import os
import tempfile
import typing
from dataclasses import MISSING
from dataclasses import fields as dc_fields
from typing import Any

from calc_core.sapata_isolada.acoes import CasoCarga, Esforcos, Pilar, TipoAcao
from calc_core.sapata_isolada.geotecnia import (
    Camada,
    PerfilGeotecnico,
    Solo,
    TipoSubstrato,
)
from calc_core.sapata_isolada.materiais import Aco, Concreto
from calc_core.sapata_isolada.sapata import (
    ArmaduraImposta,
    GeometriaImposta,
    OpcoesProjeto,
)

# Constantes de "valores aceitos" para os dois campos de despacho por string
# de `OpcoesProjeto` (`modelo_reacao`/`modelo_armadura_rigida` — ver
# `calc_core.sapata_isolada.sapata` linhas ~668-686/1139-1141, onde o núcleo
# despacha em cadeias de `if valor == "..."` e simplesmente CAI FORA do ramo
# esperado para qualquer string não reconhecida, sem erro). Reaproveitadas de
# `formulario.py` (a mesma lista que alimenta o combobox da tela) em vez de
# duplicadas aqui — MEDIA #2, item 3, do GATE 2, rodada 2: um `.s7proj`
# editado à mão com `"modelo_reacao": "rigid"` (erro de digitação de
# "rigido") ou `"modelo_armadura_rigida": "bielaz"` abria sem erro e
# calculava com o modelo ERRADO em silêncio. Importar `.formulario` aqui não
# introduz uma dependência NOVA de `tkinter`: `ui.completo.__init__` já
# importa `.app` (que importa `tkinter`) incondicionalmente, então qualquer
# `from ui.completo import projeto` já exige `tkinter` instalado hoje —
# `formulario.py` só usa `tkinter` dentro de métodos de instância (nunca no
# escopo de módulo), então importar suas constantes não exige um display
# X/Xvfb."""
from .formulario import MODELOS_ARMADURA, MODELOS_REACAO

FORMATO = "sapata7-projeto"
VERSAO = 1

_CAMPOS_OPCOES_ESPECIAIS = {"geometria_imposta", "armaduras_impostas", "bitolas"}
_DIRECOES_VALIDAS = ("X", "Y")

# Domínio numérico dos campos escalares de `OpcoesProjeto` (MEDIA #2, item 2,
# do GATE 2, rodada 2): sem esta tabela, `_dict_para_opcoes` só validava
# TIPO (nunca `bool` onde se espera número), não FAIXA — `limite_recalque_mm
# =-25`, `max_iteracoes=0`, `modulo_dim=0`, `dim_minima=-1` etc entravam sem
# erro e o núcleo calculava (ou travava em loop) com um parâmetro sem
# sentido físico. `(minimo, estrito)` no mesmo formato de `_num` acima;
# `estrito=True` exige `> minimo`. Limites de DOMÍNIO (o número tem de
# poder existir), não de engenharia — nenhum destes é uma decisão
# normativa: um `modulo_dim=0` trava a rotina de arredondamento em loop
# infinito, `max_iteracoes=0` impede QUALQUER iteração, `espacamento_min=0`
# não tem significado físico de espaçamento entre barras. Campos ausentes
# desta tabela (`boa_aderencia`, `verificar_recalque`, ... — booleanos, ou
# `travar_a`/`travar_b`/`kv`, cujo domínio já é coberto abaixo por
# permitirem `None`) não são tocados aqui.
_LIMITES_OPCOES_NUMERICAS: dict[str, tuple[float, bool]] = {
    "modulo_dim": (0.0, True),
    "dim_minima": (0.0, True),
    "h_minima": (0.0, True),
    "h0_minima": (0.0, True),
    "balanco_minimo": (0.0, False),
    "peso_proprio_estimado": (0.0, False),
    "folga_topo": (0.0, False),
    "inclinacao_max_graus": (0.0, True),
    "espacamento_max": (0.0, True),
    "espacamento_min": (0.0, True),
    "fator_armadura_minima": (0.0, False),
    "area_comprimida_minima": (0.0, True),
    "max_iteracoes": (0.0, True),
    "limite_recalque_mm": (0.0, True),
    "vida_util_anos": (0.0, True),
    "divisoes_grelha": (0.0, True),
    "coef_braco_bielas": (0.0, True),
    "theta_minimo_biela": (0.0, True),
    "recalque_referencia_kv": (0.0, True),
    "kv": (0.0, True),
    "travar_a": (0.0, True),
    "travar_b": (0.0, True),
}


def _exigir_chaves(d: dict, chaves: tuple, contexto: str) -> None:
    faltando = [c for c in chaves if c not in d]
    if faltando:
        raise ValueError(
            f"{contexto}: campo(s) obrigatório(s) ausente(s): "
            f"{', '.join(faltando)}.")


# --------------------------------------------------------------------------- #
#  Validação numérica de fronteira (defeito D14 do GATE 2, rodada 1)
#
#  `carregar_projeto` valida ESTRUTURA (chaves obrigatórias, cabeçalho,
#  versão, enums) desde a rodada anterior, mas não TIPO nem DOMÍNIO dos
#  valores numéricos — apesar de a docstring de `carregar_projeto` prometer
#  isso ("Levanta ValueError ... para valor incompatível com o construtor
#  esperado"). `.s7proj` é JSON legível e editável à mão, o que convida a
#  erro de digitação (string em vez de número, sinal trocado, `null` num
#  campo obrigatório) — `_num` é a fronteira que recusa isso citando
#  arquivo/campo, no mesmo padrão de `excel_import.py`.
# --------------------------------------------------------------------------- #
_AUSENTE = object()


def _num(d: dict, chave: str, contexto: str, *, obrigatorio: bool = False,
        minimo: float | None = None, estrito: bool = False,
        permite_none: bool = False) -> Any:
    """Lê `d[chave]` como número (`int`/`float`, NUNCA `bool`), valida
    domínio (`minimo`/`estrito`: `estrito=True` exige `> minimo`,
    `estrito=False` exige `>= minimo`) e devolve o sentinela `_AUSENTE` se
    a chave não estiver no dict — para o dataclass do núcleo aplicar seu
    PRÓPRIO default (nunca copiado aqui, ver defeito D8/`_opcoes_para_dict`
    mais abaixo). `permite_none=True` deixa `null` explícito passar como
    `None` (campos `Optional` do núcleo, ex. `Camada.nspt`); do contrário
    `null` é tratado como valor inválido (campo obrigatório) ou ausente
    (campo opcional, cai no default do dataclass)."""
    if chave not in d:
        if obrigatorio:
            raise ValueError(f"{contexto}.{chave}: campo obrigatório ausente.")
        return _AUSENTE
    valor = d[chave]
    if valor is None:
        if permite_none:
            return None
        if obrigatorio:
            raise ValueError(f"{contexto}.{chave}: campo obrigatório é nulo.")
        return _AUSENTE
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        # ValueError de propósito, não TypeError (ruff: TRY004) — o contrato
        # público de `carregar_projeto` (docstring acima) é "sempre
        # ValueError para valor incompatível com o construtor esperado",
        # testado em vários casos de tests/test_projeto_e_excel.py (ex.:
        # test_projeto_espessura_camada_string_e_recusada,
        # test_projeto_N_bool_e_recusado — ALTA #2 do GATE 2, rodada 2).
        raise ValueError(  # noqa: TRY004
            f"{contexto}.{chave}: esperado número, recebido {valor!r} "
            f"({type(valor).__name__}).")
    numero = float(valor)
    if minimo is not None:
        valido = numero > minimo if estrito else numero >= minimo
        if not valido:
            relacao = "> " if estrito else ">= "
            raise ValueError(
                f"{contexto}.{chave}: esperado número {relacao}{minimo}, "
                f"recebido {numero!r}.")
    return numero


def _aplicar_num(kwargs: dict, d: dict, chave: str, contexto: str, **kw) -> None:
    """`_num(...)` + só grava em `kwargs` se o valor não for `_AUSENTE` —
    o dataclass do núcleo aplica o próprio default para a chave omitida."""
    valor = _num(d, chave, contexto, **kw)
    if valor is not _AUSENTE:
        kwargs[chave] = valor


# --------------------------------------------------------------------------- #
#  Pilar
# --------------------------------------------------------------------------- #
def _pilar_para_dict(pilar: Pilar) -> dict:
    return {
        "ap": pilar.ap, "bp": pilar.bp,
        "phi_arranque_mm": pilar.phi_arranque_mm,
        "n_barras": pilar.n_barras,
        "as_calc_efetiva": pilar.as_calc_efetiva,
    }


def _dict_para_pilar(d: dict) -> Pilar:
    contexto = "pilar"
    _exigir_chaves(d, ("ap", "bp"), contexto)
    kwargs: dict[str, Any] = {
        "ap": _num(d, "ap", contexto, obrigatorio=True, minimo=0, estrito=True),
        "bp": _num(d, "bp", contexto, obrigatorio=True, minimo=0, estrito=True),
    }
    _aplicar_num(kwargs, d, "phi_arranque_mm", contexto, minimo=0, estrito=True)
    _aplicar_num(kwargs, d, "n_barras", contexto, minimo=0, estrito=True)
    _aplicar_num(kwargs, d, "as_calc_efetiva", contexto, minimo=0, estrito=True)
    if "n_barras" in kwargs:
        kwargs["n_barras"] = int(kwargs["n_barras"])
    return Pilar(**kwargs)


# --------------------------------------------------------------------------- #
#  Perfil geotécnico / camadas
# --------------------------------------------------------------------------- #
def _camada_para_dict(c: Camada) -> dict:
    return {
        "nome": c.nome, "espessura": c.espessura, "tipo": c.tipo.value,
        "gamma_nat": c.gamma_nat, "gamma_sat": c.gamma_sat,
        "phi": c.phi, "coesao": c.coesao, "nspt": c.nspt,
        "Es": c.Es, "nu": c.nu,
        "Cc": c.Cc, "Cs": c.Cs, "e0": c.e0, "OCR": c.OCR, "cv": c.cv,
        "C_alpha": c.C_alpha, "drenagem_dupla": c.drenagem_dupla,
        "k_spt_MPa": c.k_spt_MPa,
    }


def _dict_para_camada(d: dict, indice: int) -> Camada:
    contexto = f"perfil.camadas[{indice}]"
    _exigir_chaves(d, ("nome", "espessura", "tipo"), contexto)
    if not isinstance(d["nome"], str) or not d["nome"].strip():
        raise ValueError(f"{contexto}.nome: esperado texto não vazio, "
                         f"recebido {d['nome']!r}.")
    try:
        tipo = TipoSubstrato(d["tipo"])
    except ValueError as erro:
        raise ValueError(
            f"{contexto}: tipo de substrato {d['tipo']!r} desconhecido; use "
            f"um de {[t.value for t in TipoSubstrato]}.") from erro
    kwargs: dict[str, Any] = {
        "nome": d["nome"], "tipo": tipo,
        "espessura": _num(d, "espessura", contexto, obrigatorio=True,
                          minimo=0, estrito=True),
    }
    _aplicar_num(kwargs, d, "gamma_nat", contexto, minimo=0, estrito=True)
    _aplicar_num(kwargs, d, "gamma_sat", contexto, minimo=0, estrito=True)
    _aplicar_num(kwargs, d, "phi", contexto, minimo=0)
    _aplicar_num(kwargs, d, "coesao", contexto, minimo=0)
    _aplicar_num(kwargs, d, "nspt", contexto, minimo=0, permite_none=True)
    _aplicar_num(kwargs, d, "Es", contexto, minimo=0, permite_none=True)
    _aplicar_num(kwargs, d, "nu", contexto, minimo=0)
    _aplicar_num(kwargs, d, "Cc", contexto, minimo=0, permite_none=True)
    _aplicar_num(kwargs, d, "Cs", contexto, minimo=0, permite_none=True)
    _aplicar_num(kwargs, d, "e0", contexto, minimo=0, permite_none=True)
    _aplicar_num(kwargs, d, "OCR", contexto, minimo=0)
    _aplicar_num(kwargs, d, "cv", contexto, minimo=0, permite_none=True)
    _aplicar_num(kwargs, d, "C_alpha", contexto, minimo=0, permite_none=True)
    _aplicar_num(kwargs, d, "k_spt_MPa", contexto, minimo=0, estrito=True)
    if "drenagem_dupla" in d:
        if not isinstance(d["drenagem_dupla"], bool):
            raise ValueError(
                f"{contexto}.drenagem_dupla: esperado verdadeiro/falso, "
                f"recebido {d['drenagem_dupla']!r}.")
        kwargs["drenagem_dupla"] = d["drenagem_dupla"]
    return Camada(**kwargs)


def _perfil_para_dict(perfil: PerfilGeotecnico) -> dict:
    return {"camadas": [_camada_para_dict(c) for c in perfil.camadas],
            "nivel_agua": perfil.nivel_agua}


def _dict_para_perfil(d: dict) -> PerfilGeotecnico:
    contexto = "solo.perfil"
    _exigir_chaves(d, ("camadas",), contexto)
    camadas_raw = d["camadas"]
    if camadas_raw is None:
        # D14 do GATE 2, rodada 1: `"camadas": null` virava perfil VAZIO em
        # vez de erro — muda a sobrecarga na base do perfil em silêncio.
        # Omita a chave "perfil" inteira (não "camadas": null) se não há
        # perfil geotécnico; uma lista vazia [] continua aceita.
        raise ValueError(
            f"{contexto}.camadas: não pode ser nulo. Omita a chave "
            "'perfil' inteira em 'solo' se não há perfil geotécnico, ou "
            "informe uma lista de camadas (pode ser vazia: []).")
    if not isinstance(camadas_raw, list):
        # ValueError de propósito, não TypeError (ruff: TRY004) — mesmo
        # contrato público de `carregar_projeto` citado acima (ALTA #2 do
        # GATE 2, rodada 2).
        raise ValueError(  # noqa: TRY004
            f"{contexto}.camadas: esperada uma lista, recebido "
            f"{type(camadas_raw).__name__}.")
    camadas = [_dict_para_camada(c, i) for i, c in enumerate(camadas_raw)]
    nivel_agua = _num(d, "nivel_agua", contexto, minimo=0, permite_none=True)
    if nivel_agua is _AUSENTE:
        nivel_agua = None
    return PerfilGeotecnico(camadas=camadas, nivel_agua=nivel_agua)


# --------------------------------------------------------------------------- #
#  Solo
# --------------------------------------------------------------------------- #
def _solo_para_dict(solo: Solo) -> dict:
    return {
        "sigma_adm": solo.sigma_adm, "gamma_solo": solo.gamma_solo,
        "hf": solo.hf, "phi": solo.phi, "coesao": solo.coesao,
        "fator_atrito_base": solo.fator_atrito_base,
        "fs_deslizamento": solo.fs_deslizamento,
        "fs_tombamento": solo.fs_tombamento,
        "coef_sigma_max_excentrico": solo.coef_sigma_max_excentrico,
        "perfil": _perfil_para_dict(solo.perfil) if solo.perfil is not None else None,
    }


def _dict_para_solo(d: dict) -> Solo:
    contexto = "solo"
    _exigir_chaves(d, ("sigma_adm",), contexto)
    perfil = _dict_para_perfil(d["perfil"]) if d.get("perfil") else None
    kwargs: dict[str, Any] = {
        "sigma_adm": _num(d, "sigma_adm", contexto, obrigatorio=True,
                          minimo=0, estrito=True),
        "perfil": perfil,
    }
    _aplicar_num(kwargs, d, "gamma_solo", contexto, minimo=0, estrito=True)
    _aplicar_num(kwargs, d, "hf", contexto, minimo=0)
    _aplicar_num(kwargs, d, "phi", contexto, minimo=0)
    _aplicar_num(kwargs, d, "coesao", contexto, minimo=0)
    _aplicar_num(kwargs, d, "fator_atrito_base", contexto, minimo=0)
    _aplicar_num(kwargs, d, "fs_deslizamento", contexto, minimo=0, estrito=True)
    _aplicar_num(kwargs, d, "fs_tombamento", contexto, minimo=0, estrito=True)
    _aplicar_num(kwargs, d, "coef_sigma_max_excentrico", contexto, minimo=0,
                estrito=True)
    return Solo(**kwargs)


# --------------------------------------------------------------------------- #
#  Materiais
# --------------------------------------------------------------------------- #
def _concreto_para_dict(c: Concreto) -> dict:
    return {"fck": c.fck, "gamma_c": c.gamma_c,
            "peso_especifico": c.peso_especifico, "agregado": c.agregado}


def _dict_para_concreto(d: dict) -> Concreto:
    contexto = "concreto"
    _exigir_chaves(d, ("fck",), contexto)
    kwargs: dict[str, Any] = {
        "fck": _num(d, "fck", contexto, obrigatorio=True, minimo=0, estrito=True),
    }
    _aplicar_num(kwargs, d, "gamma_c", contexto, minimo=0, estrito=True)
    _aplicar_num(kwargs, d, "peso_especifico", contexto, minimo=0, estrito=True)
    if "agregado" in d:
        if not isinstance(d["agregado"], str) or not d["agregado"].strip():
            raise ValueError(f"{contexto}.agregado: esperado texto não "
                             f"vazio, recebido {d['agregado']!r}.")
        kwargs["agregado"] = d["agregado"]
    return Concreto(**kwargs)


def _aco_para_dict(a: Aco) -> dict:
    return {"fyk": a.fyk, "gamma_s": a.gamma_s, "Es": a.Es,
            "categoria": a.categoria}


def _dict_para_aco(d: dict) -> Aco:
    contexto = "aco"
    _exigir_chaves(d, ("fyk",), contexto)
    kwargs: dict[str, Any] = {
        "fyk": _num(d, "fyk", contexto, obrigatorio=True, minimo=0, estrito=True),
    }
    _aplicar_num(kwargs, d, "gamma_s", contexto, minimo=0, estrito=True)
    _aplicar_num(kwargs, d, "Es", contexto, minimo=0, estrito=True)
    if "categoria" in d and d["categoria"] is not None:
        if not isinstance(d["categoria"], str):
            raise ValueError(f"{contexto}.categoria: esperado texto ou "
                             f"nulo, recebido {d['categoria']!r}.")
        kwargs["categoria"] = d["categoria"]
    return Aco(**kwargs)


# --------------------------------------------------------------------------- #
#  Casos de carga
# --------------------------------------------------------------------------- #
def _caso_para_dict(c: CasoCarga) -> dict:
    e = c.esforcos
    return {
        "nome": c.nome, "N": e.N, "Mx": e.Mx, "My": e.My, "Hx": e.Hx, "Hy": e.Hy,
        "tipo": c.tipo.value, "psi0": c.psi0, "psi1": c.psi1, "psi2": c.psi2,
        "reversivel": c.reversivel,
    }


def _dict_para_caso(d: dict, indice: int) -> CasoCarga:
    contexto = f"casos[{indice}]"
    _exigir_chaves(d, ("nome",), contexto)
    if not isinstance(d["nome"], str) or not d["nome"].strip():
        raise ValueError(f"{contexto}.nome: esperado texto não vazio, "
                         f"recebido {d['nome']!r}.")
    tipo_txt = d.get("tipo", TipoAcao.PERMANENTE.value)
    try:
        tipo = TipoAcao(tipo_txt)
    except ValueError as erro:
        raise ValueError(
            f"{contexto}: tipo de ação {tipo_txt!r} desconhecido; use um de "
            f"{[t.value for t in TipoAcao]}.") from erro

    esf_kwargs: dict[str, Any] = {}
    for campo in ("N", "Mx", "My", "Hx", "Hy"):
        _aplicar_num(esf_kwargs, d, campo, contexto)
    esforcos = Esforcos(**esf_kwargs)

    kwargs: dict[str, Any] = {"nome": d["nome"], "esforcos": esforcos,
                              "tipo": tipo}
    _aplicar_num(kwargs, d, "psi0", contexto, minimo=0)
    _aplicar_num(kwargs, d, "psi1", contexto, minimo=0)
    _aplicar_num(kwargs, d, "psi2", contexto, minimo=0)
    if "reversivel" in d:
        if not isinstance(d["reversivel"], bool):
            raise ValueError(
                f"{contexto}.reversivel: esperado verdadeiro/falso, "
                f"recebido {d['reversivel']!r}.")
        kwargs["reversivel"] = d["reversivel"]
    return CasoCarga(**kwargs)


# --------------------------------------------------------------------------- #
#  Opções de projeto
# --------------------------------------------------------------------------- #
def _opcoes_para_dict(op: OpcoesProjeto) -> dict:
    d: dict[str, Any] = {}
    for f in dc_fields(OpcoesProjeto):
        if f.name in _CAMPOS_OPCOES_ESPECIAIS:
            continue
        d[f.name] = getattr(op, f.name)
    d["bitolas"] = list(op.bitolas)
    geo = op.geometria_imposta
    d["geometria_imposta"] = (
        {"a": geo.a, "b": geo.b, "h": geo.h, "h0": geo.h0} if geo is not None else None)
    d["armaduras_impostas"] = {
        direcao: {"phi_mm": a.phi_mm, "n_barras": a.n_barras,
                  "espacamento": a.espacamento}
        for direcao, a in op.armaduras_impostas.items()
    }
    return d


def _tipo_simples(tipo: Any) -> tuple[type, ...] | None:
    """Reduz o `type hint` resolvido de um campo de `OpcoesProjeto` a uma
    tupla de tipos "simples" aceitáveis em JSON (`bool`/`int`/`float`/
    `str`), destrinchando `Optional[X]` (`Union[X, None]`). Devolve `None`
    para tipos que este validador genérico não sabe tratar (ex.:
    `Sequence[float]`, `dict`, `GeometriaImposta`) — esses campos
    continuam sem checagem de tipo aqui (são tratados à parte, ou vêm de
    `_CAMPOS_OPCOES_ESPECIAIS`)."""
    origem = typing.get_origin(tipo)
    if origem is None:
        return (tipo,) if tipo in (bool, int, float, str) else None
    if origem is typing.Union:
        args = [a for a in typing.get_args(tipo) if a is not type(None)]
        if len(args) == 1:
            return _tipo_simples(args[0])
    return None


def _permite_none(tipo: Any) -> bool:
    """`True` se o `type hint` resolvido de um campo de `OpcoesProjeto` é
    `Optional[X]` (`Union[X, None]`) — usado por `_dict_para_opcoes` para
    recusar `null` explícito num campo que NÃO é opcional (MEDIA #2, item
    1, do GATE 2, rodada 2: antes, `null` num campo não-opcional só
    explodia mais tarde, no F5, com um `TypeError` genérico do próprio
    dataclass — exatamente o tipo de erro tardio e pouco claro que a
    validação estrita do `.s7proj` deveria eliminar)."""
    return typing.get_origin(tipo) is typing.Union and type(None) in typing.get_args(tipo)


def _dict_para_opcoes(d: dict) -> OpcoesProjeto:
    """Constrói `OpcoesProjeto` só com as chaves REALMENTE presentes no
    JSON (`OpcoesProjeto` aplica seu próprio default para o resto — nunca
    um literal copiado aqui, ver defeito D8/`_num` acima), com checagem de
    TIPO (nunca `bool` onde se espera número, nunca outra coisa onde se
    espera `bool`/texto), de `null` em campo não-opcional, de DOMÍNIO
    numérico (`_LIMITES_OPCOES_NUMERICAS`) e dos dois campos de despacho
    por string (`modelo_reacao`/`modelo_armadura_rigida`) — defeito D14 do
    GATE 2, rodada 1, e MEDIA #2 do GATE 2, rodada 2."""
    contexto = "opcoes"
    campos = {f.name: f for f in dc_fields(OpcoesProjeto)}
    dicas = typing.get_type_hints(OpcoesProjeto)
    kwargs: dict[str, Any] = {}
    for chave, valor in d.items():
        if chave in _CAMPOS_OPCOES_ESPECIAIS or chave not in campos:
            continue     # campo de versão futura desconhecida: ignora, não quebra
        tipo_hint = dicas.get(chave)
        if valor is None:
            if not _permite_none(tipo_hint):
                raise ValueError(
                    f"{contexto}.{chave}: campo não-opcional recebeu "
                    "'null' — omita a chave inteira para usar o default do "
                    "núcleo, em vez de gravar 'null' explicitamente.")
            kwargs[chave] = None
            continue
        tipos = _tipo_simples(tipo_hint)
        if tipos is not None:
            # bool é subclasse de int em Python: exclui explicitamente
            # quando o campo NÃO é bool, para não aceitar True/False onde
            # se espera número (mesmo cuidado de excel_import.py). JSON não
            # distingue int/float (`1` e `1.0` chegam como o mesmo tipo
            # conforme o gerador da planilha/arquivo) — um campo `float`
            # aceita `int` (e é convertido), nunca o contrário.
            bool_permitido = bool in tipos
            tipos_aceitos = tipos
            if float in tipos and int not in tipos_aceitos:
                tipos_aceitos = (*tipos_aceitos, int)
            valido = isinstance(valor, tipos_aceitos) and (
                bool_permitido or not isinstance(valor, bool))
            if not valido:
                nomes = "/".join(t.__name__ for t in tipos)
                raise ValueError(
                    f"{contexto}.{chave}: esperado {nomes}, recebido "
                    f"{valor!r} ({type(valor).__name__}).")
            if (valido and float in tipos and int not in tipos
                    and isinstance(valor, int) and not isinstance(valor, bool)):
                valor = float(valor)
        kwargs[chave] = valor
    if d.get("bitolas") is not None:
        bitolas_raw = d["bitolas"]
        if not isinstance(bitolas_raw, list):
            raise ValueError(
                f"{contexto}.bitolas: esperada uma lista, recebido "
                f"{type(bitolas_raw).__name__}.")
        # MEDIA #2, item 4: cada elemento passa por `_num` (mesma checagem
        # de tipo/domínio que os demais campos numéricos) — antes,
        # `bitolas=['a', -1]` era aceita sem erro (só `tuple(d["bitolas"])`,
        # sem checar nada), e uma bitola negativa/textual só quebraria (ou
        # pior, seria usada) bem dentro do dimensionamento no núcleo.
        bitolas_validadas = []
        for i, b in enumerate(bitolas_raw):
            bitolas_validadas.append(
                _num({"valor": b}, "valor", f"{contexto}.bitolas[{i}]",
                    obrigatorio=True, minimo=0, estrito=True))
        kwargs["bitolas"] = tuple(bitolas_validadas)

    # Domínio numérico dos campos escalares (MEDIA #2, item 2) — roda DEPOIS
    # da checagem de tipo acima (só compara número com número).
    for chave, (minimo, estrito) in _LIMITES_OPCOES_NUMERICAS.items():
        if chave not in kwargs or kwargs[chave] is None:
            continue
        valor = kwargs[chave]
        valido = valor > minimo if estrito else valor >= minimo
        if not valido:
            relacao = "> " if estrito else ">= "
            raise ValueError(
                f"{contexto}.{chave}: esperado número {relacao}{minimo!r}, "
                f"recebido {valor!r}.")

    # Modelos de despacho por string (MEDIA #2, item 3) — o núcleo
    # (`calc_core.sapata_isolada.sapata`) despacha por comparação de string
    # e CAI FORA do ramo esperado, em silêncio, para qualquer valor não
    # reconhecido; a lista aceita é a mesma que alimenta o combobox da
    # tela (`ui/completo/formulario.py::MODELOS_REACAO`/
    # `MODELOS_ARMADURA`), para as duas fontes nunca divergirem.
    if "modelo_reacao" in kwargs and kwargs["modelo_reacao"] not in MODELOS_REACAO:
        raise ValueError(
            f"{contexto}.modelo_reacao: {kwargs['modelo_reacao']!r} "
            f"desconhecido; use um de {MODELOS_REACAO!r}.")
    if ("modelo_armadura_rigida" in kwargs
            and kwargs["modelo_armadura_rigida"] not in MODELOS_ARMADURA):
        raise ValueError(
            f"{contexto}.modelo_armadura_rigida: "
            f"{kwargs['modelo_armadura_rigida']!r} desconhecido; use um de "
            f"{MODELOS_ARMADURA!r}.")

    geo = d.get("geometria_imposta")
    if geo is not None:
        geo_contexto = "opcoes.geometria_imposta"
        _exigir_chaves(geo, ("a", "b", "h"), geo_contexto)
        h0 = _num(geo, "h0", geo_contexto, minimo=0, estrito=True,
                  permite_none=True)
        kwargs["geometria_imposta"] = GeometriaImposta(
            a=_num(geo, "a", geo_contexto, obrigatorio=True, minimo=0,
                  estrito=True),
            b=_num(geo, "b", geo_contexto, obrigatorio=True, minimo=0,
                  estrito=True),
            h=_num(geo, "h", geo_contexto, obrigatorio=True, minimo=0,
                  estrito=True),
            h0=(h0 if h0 is not _AUSENTE else None))
    else:
        kwargs["geometria_imposta"] = None

    impostas: dict[str, ArmaduraImposta] = {}
    for direcao, a in (d.get("armaduras_impostas") or {}).items():
        if direcao not in _DIRECOES_VALIDAS:
            raise ValueError(
                f"opcoes.armaduras_impostas: direção {direcao!r} "
                f"desconhecida; use uma de {_DIRECOES_VALIDAS!r}.")
        arm_contexto = f"opcoes.armaduras_impostas[{direcao!r}]"
        _exigir_chaves(a, ("phi_mm",), arm_contexto)
        n_barras = _num(a, "n_barras", arm_contexto, minimo=0, estrito=True,
                        permite_none=True)
        espacamento = _num(a, "espacamento", arm_contexto, minimo=0,
                           estrito=True, permite_none=True)
        impostas[direcao] = ArmaduraImposta(
            phi_mm=_num(a, "phi_mm", arm_contexto, obrigatorio=True,
                       minimo=0, estrito=True),
            n_barras=(int(n_barras) if isinstance(n_barras, float) else None),
            espacamento=(espacamento if isinstance(espacamento, float)
                        else None))
    kwargs["armaduras_impostas"] = impostas

    return OpcoesProjeto(**kwargs)


# --------------------------------------------------------------------------- #
#  API pública
# --------------------------------------------------------------------------- #
def salvar_projeto(caminho, pilar: Pilar, solo: Solo, concreto: Concreto,
                   aco: Aco, cobrimento: float, casos: list, opcoes: OpcoesProjeto
                   ) -> None:
    """Salva o estado do formulário num arquivo `.s7proj` (JSON com cabeçalho).

    Não salva `ResultadoSapata` — só os dados de entrada. `cobrimento` é
    esperado em METROS (mesma unidade que `PainelEntrada.ler_materiais`
    devolve, já dividido por 100 a partir do campo em cm da tela).
    """
    dados = {
        "formato": FORMATO,
        "versao": VERSAO,
        "pilar": _pilar_para_dict(pilar),
        "solo": _solo_para_dict(solo),
        "concreto": _concreto_para_dict(concreto),
        "aco": _aco_para_dict(aco),
        "cobrimento": cobrimento,
        "casos": [_caso_para_dict(c) for c in casos],
        "opcoes": _opcoes_para_dict(opcoes),
    }
    # Escreve num arquivo TEMPORÁRIO no mesmo diretório e troca com
    # `os.replace` (atômico no mesmo sistema de arquivos) em vez de abrir o
    # destino direto em "w": se `json.dump` falhar no meio (disco cheio,
    # permissão, caminho de rede), o arquivo ANTERIOR do usuário sobrevive
    # intacto, em vez de ficar truncado pela metade.
    diretorio = os.path.dirname(os.path.abspath(caminho)) or "."
    try:
        fd, tmp = tempfile.mkstemp(dir=diretorio, prefix=".s7proj_tmp_")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(dados, f, indent=2, ensure_ascii=False)
            os.replace(tmp, caminho)
        except BaseException:
            with contextlib.suppress(OSError):
                os.remove(tmp)
            raise
    except OSError as erro:
        raise ValueError(
            f"Não foi possível salvar o projeto em {caminho!r}: {erro}"
        ) from erro


def carregar_projeto(caminho) -> dict:
    """Lê um arquivo `.s7proj` e devolve um dict com as chaves `pilar`,
    `solo`, `concreto`, `aco`, `cobrimento`, `casos`, `opcoes`, cada uma já
    reconstruída como o dataclass correspondente (não dicts crus).

    Levanta `ValueError`, com mensagem em português citando o problema, para:
    arquivo ilegível, JSON malformado, cabeçalho/versão desconhecidos, chave
    obrigatória ausente ou valor incompatível com o construtor esperado.
    Nunca devolve um projeto parcial em silêncio.
    """
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            texto = f.read()
    except OSError as erro:
        raise ValueError(
            f"Não foi possível abrir o arquivo de projeto {caminho!r}: "
            f"{erro}") from erro

    try:
        dados = json.loads(texto)
    except json.JSONDecodeError as erro:
        raise ValueError(
            f"Arquivo de projeto {caminho!r} não é um JSON válido "
            f"(linha {erro.lineno}, coluna {erro.colno}): {erro.msg}") from erro

    if not isinstance(dados, dict):
        # ValueError de propósito, não TypeError (ruff: TRY004) — o contrato
        # público desta função é "sempre ValueError para arquivo malformado",
        # documentado acima e coberto por
        # tests/test_projeto_e_excel.py::test_projeto_cabecalho_ausente.
        raise ValueError(  # noqa: TRY004
            f"Arquivo de projeto {caminho!r}: o conteúdo raiz deveria ser um "
            "objeto JSON (chave/valor), não uma lista ou valor simples.")

    if dados.get("formato") != FORMATO:
        raise ValueError(
            f"Arquivo de projeto {caminho!r} não tem o cabeçalho esperado "
            f'("formato": {FORMATO!r}); encontrado: {dados.get("formato")!r}. '
            "Não parece ser um arquivo .s7proj válido.")

    versao = dados.get("versao")
    if versao != VERSAO:
        raise ValueError(
            f"Arquivo de projeto {caminho!r} está na versão {versao!r}, mas "
            f"esta versão do SAPATA-7 só lê projetos na versão {VERSAO}. "
            "Abra com uma versão compatível do software.")

    contexto_arquivo = f"projeto {caminho!r}"
    _exigir_chaves(dados, ("pilar", "solo", "concreto", "aco", "cobrimento",
                           "casos", "opcoes"), contexto_arquivo)

    # As três checagens `isinstance` abaixo levantam `ValueError` de
    # propósito, não `TypeError` (ruff: TRY004) — mesmo contrato público de
    # `carregar_projeto` citado na docstring da função e nos `noqa` acima em
    # `_num`/`_dict_para_perfil` (ALTA #2 do GATE 2, rodada 2): "sempre
    # ValueError para arquivo malformado", nunca uma exceção de tipo
    # diferente vazando de um erro de digitação no JSON do usuário.
    for chave in ("pilar", "solo", "concreto", "aco", "opcoes"):
        if not isinstance(dados[chave], dict):
            raise ValueError(  # noqa: TRY004
                f"{contexto_arquivo}.{chave}: esperado um objeto JSON "
                f"(chave/valor), recebido {type(dados[chave]).__name__}.")
    if not isinstance(dados["casos"], list):
        raise ValueError(  # noqa: TRY004
            f"{contexto_arquivo}.casos: esperada uma lista, recebido "
            f"{type(dados['casos']).__name__}.")
    for i, c in enumerate(dados["casos"]):
        if not isinstance(c, dict):
            raise ValueError(  # noqa: TRY004
                f"{contexto_arquivo}.casos[{i}]: esperado um objeto JSON "
                f"(chave/valor), recebido {type(c).__name__}.")

    try:
        pilar = _dict_para_pilar(dados["pilar"])
        solo = _dict_para_solo(dados["solo"])
        concreto = _dict_para_concreto(dados["concreto"])
        aco = _dict_para_aco(dados["aco"])
        cobrimento = _num(dados, "cobrimento", "projeto", obrigatorio=True,
                          minimo=0, estrito=True)
        casos = [_dict_para_caso(c, i) for i, c in enumerate(dados["casos"])]
        opcoes = _dict_para_opcoes(dados["opcoes"])
    except (TypeError, KeyError, AttributeError) as erro:
        raise ValueError(
            f"Arquivo de projeto {caminho!r} malformado: {erro}") from erro

    return {"pilar": pilar, "solo": solo, "concreto": concreto, "aco": aco,
            "cobrimento": cobrimento, "casos": casos, "opcoes": opcoes}


# --------------------------------------------------------------------------- #
#  Aviso do que a TELA descarta ao repor um projeto carregado (MEDIA #4 do
#  GATE 2, rodada 2) — ver o docstring do módulo, seção "Campos que a TELA
#  repõe vs. campos que voltam ao default", para a explicação completa.
# --------------------------------------------------------------------------- #
CAMPOS_NAO_REPOSTOS: dict[str, tuple[str, ...]] = {
    "pilar": ("n_barras", "as_calc_efetiva"),
    "solo": ("fator_atrito_base", "fs_deslizamento", "fs_tombamento",
             "coef_sigma_max_excentrico"),
    "concreto": ("gamma_c", "peso_especifico"),
    # "categoria" fica FORA desta lista de propósito: `Aco.__post_init__`
    # sempre a INFERE de `fyk` quando ela não é explicitada (ver
    # `calc_core.sapata_isolada.materiais.Aco`) — como `fyk` É restaurado
    # pela tela (`preencher_materiais`), a categoria será re-inferida
    # IDENTICAMENTE no próximo F5 no caso comum (categoria implícita, o
    # único que o combobox `f_yk` da tela produz). Incluir "categoria" aqui
    # geraria um falso positivo em praticamente TODO projeto aberto — o
    # único caso real de perda (categoria explicitamente forçada,
    # divergente de fyk, só possível editando o `.s7proj` à mão) não vale
    # o ruído constante no caso comum.
    "aco": ("gamma_s", "Es"),
    "opcoes": ("modulo_dim", "dim_minima", "h_minima", "h0_minima",
               "balanco_minimo", "peso_proprio_estimado", "folga_topo",
               "inclinacao_max_graus", "espacamento_max", "espacamento_min",
               "fator_armadura_minima", "travar_a", "travar_b",
               "boa_aderencia", "ganchos_nas_pontas", "area_comprimida_minima",
               "considerar_excentricidade_puncao", "bitolas", "max_iteracoes",
               "verificar_recalque", "limite_recalque_mm", "vida_util_anos",
               "divisoes_grelha", "coef_braco_bielas", "theta_minimo_biela",
               "kv", "recalque_referencia_kv"),
}
# `CasoCarga` é uma LISTA (um por G/Q/W), não um objeto único — tratado à
# parte em `campos_divergentes_do_default` abaixo.
CAMPOS_NAO_REPOSTOS_POR_CASO: tuple[str, ...] = (
    "tipo", "psi0", "psi1", "psi2", "reversivel")
# `ler_casos` (`ui/completo/formulario.py`) NÃO reconstrói G/Q/W com o
# default "cru" do dataclass `CasoCarga` — usa as factories
# `CasoCarga.acidental`/`CasoCarga.vento`, que sobrescrevem tipo/psi0/psi1/
# psi2/reversivel de acordo com o NOME do slot. Comparar contra
# `_default_do_campo(caso, campo)` (default do dataclass) produz avisos
# falsos para W (tipo/psi0/psi1/psi2/reversivel do dataclass ≠ o que a tela
# repõe) e deixa de avisar quando o `.s7proj` tem, por coincidência, o
# default do dataclass num campo que a tela vai sobrescrever para outro
# valor (ex.: W.psi0=0.7 no arquivo — igual ao default do dataclass, mas
# `ler_casos` sempre repõe 0.6 para W). A referência correta é por NOME de
# slot, espelhando exatamente `ler_casos`. Um `caso.nome` fora de G/Q/W nem
# chega aqui — `preencher_casos` já recusa antes.
_CASOS_REFERENCIA_POR_NOME: dict[str, CasoCarga] = {
    "G": CasoCarga("G", Esforcos()),
    "Q": CasoCarga.acidental("Q", Esforcos()),
    "W": CasoCarga.vento("W", Esforcos()),
}


def _default_do_campo(obj: Any, campo: str) -> Any:
    """`f.default` do campo `campo` no dataclass de `obj`, ou o sentinela
    `MISSING` do próprio `dataclasses` se o campo usa `default_factory` (ou
    não existe) — nenhum dos campos listados em `CAMPOS_NAO_REPOSTOS`/
    `CAMPOS_NAO_REPOSTOS_POR_CASO` usa `default_factory` hoje, mas a função
    devolve `MISSING` em vez de arriscar uma comparação sem sentido caso
    isso mude no núcleo no futuro."""
    for f in dc_fields(obj):
        if f.name == campo:
            return f.default
    return MISSING


def campos_divergentes_do_default(dados: dict) -> list[str]:
    """Lista, como texto pronto para exibição ("objeto.campo: valor salvo "
    "X (o formulário vai repor o default Y)"), os campos de `dados` (o dict
    devolvido por `carregar_projeto`) que a TELA não tem widget para repor
    (`CAMPOS_NAO_REPOSTOS`/`CAMPOS_NAO_REPOSTOS_POR_CASO`) E que têm, no
    arquivo carregado, um valor DIFERENTE do que a tela de fato repõe ao
    reconstruir o projeto — default do dataclass do núcleo para
    `CAMPOS_NAO_REPOSTOS`; para `CAMPOS_NAO_REPOSTOS_POR_CASO`, o valor que
    `ler_casos` (`ui/completo/formulario.py`) produz para aquele NOME de
    slot (G/Q/W), via `_CASOS_REFERENCIA_POR_NOME` — não o default "cru" do
    dataclass `CasoCarga`, que W e Q não usam. Campos que já batem com o que
    a tela repõe não entram na lista (nada muda, de fato, ao reabrir o
    projeto).

    Usada só para AVISAR (`ui/completo/app.py::_abrir_projeto`, MEDIA #4 do
    GATE 2, rodada 2); nunca para decidir o que salvar/carregar."""
    divergentes: list[str] = []
    for nome_obj, campos in CAMPOS_NAO_REPOSTOS.items():
        obj = dados.get(nome_obj)
        if obj is None:
            continue
        for campo in campos:
            default = _default_do_campo(obj, campo)
            if default is MISSING:
                continue
            try:
                atual = getattr(obj, campo)
            except AttributeError:
                continue
            if atual != default:
                divergentes.append(
                    f"{nome_obj}.{campo}: {atual!r} (o formulário vai repor "
                    f"o default {default!r})")
    for i, caso in enumerate(dados.get("casos") or []):
        referencia = _CASOS_REFERENCIA_POR_NOME.get(caso.nome)
        if referencia is None:
            continue
        for campo in CAMPOS_NAO_REPOSTOS_POR_CASO:
            try:
                atual = getattr(caso, campo)
            except AttributeError:
                continue
            reposto = getattr(referencia, campo)
            valor_reposto = reposto.value if hasattr(reposto, "value") else reposto
            valor_atual = atual.value if hasattr(atual, "value") else atual
            if valor_atual != valor_reposto:
                divergentes.append(
                    f"casos[{i}] ({caso.nome!r}).{campo}: {valor_atual!r} (o "
                    f"formulário vai repor o default {valor_reposto!r})")
    return divergentes
