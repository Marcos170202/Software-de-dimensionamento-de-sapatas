#!/usr/bin/env python3
"""Checagem dimensional determinística das expressões do ruleset (A2, passo 2).

Para cada registro com expressões SymPy, substitui cada variável por uma
grandeza `pint` com a unidade declarada e verifica a homogeneidade:

  - Add / Max / Min: todos os termos com a mesma dimensão;
  - relações (Eq, Ge, Le, Gt, Lt): os dois lados com a mesma dimensão;
  - Pow: expoente adimensional e numérico;
  - funções transcendentes: argumento adimensional.

Também executa, com `--sanity`, a instância numérica típica declarada no bloco
`sanity_check` do ruleset (passo 4 da cascata): avalia os passos em ordem e
confere as faixas plausíveis.

Uso:
    python tools/checar_dimensoes.py ruleset.yaml
    python tools/checar_dimensoes.py ruleset.yaml --sanity
    python tools/checar_dimensoes.py kb/formulas.yaml --unidades mapa.yaml

Formato esperado de cada registro (lista `regras:` ou `formulas:`):

    id: ...
    sympy: ["Eq(sigma_k, N_k/(B*L))", ...]      # ou `expressoes:`
    variaveis:
      sigma_k: {unidade_pint: kPa}
      N_k:     {unidade_pint: kN}
    constantes:                                  # opcional
      B_min: {valor: 0.60, unidade_pint: m}

`--unidades` (opcional) fornece/sobrescreve unidades por registro:
    <id_registro>: {var: unidade_pint, ...}
    "*":           {var: unidade_pint, ...}

Código de saída: 0 se tudo homogêneo (e faixas atendidas com --sanity);
1 se houver qualquer inconsistência, unidade ausente ou erro de parsing.
"""
from __future__ import annotations

import argparse
import re
import sys

import pint
import sympy as sp
import yaml

UREG = pint.UnitRegistry()
Q_ = UREG.Quantity

_IDENT = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")
_FUNCOES = {"Eq", "Ge", "Le", "Gt", "Lt", "Ne", "Max", "Min", "sqrt", "Rational",
            "sin", "cos", "tan", "atan", "exp", "log", "pi", "And", "Or", "Abs",
            "Piecewise", "True", "False"}


class ErroDimensional(Exception):
    pass


def _parse(expr: str) -> sp.Basic:
    """sympify com todos os identificadores forçados a Symbol.

    Sem isso, nomes como S, E, C, N, Q, I viram objetos internos do SymPy.
    """
    local = {nome: sp.Symbol(nome) for nome in _IDENT.findall(expr)
             if nome not in _FUNCOES}
    local.update({"Max": sp.Max, "Min": sp.Min, "Eq": sp.Eq, "Ge": sp.Ge,
                  "Le": sp.Le, "Gt": sp.Gt, "Lt": sp.Lt, "Rational": sp.Rational,
                  "sqrt": sp.sqrt, "And": sp.And, "Or": sp.Or, "Abs": sp.Abs})
    return sp.sympify(expr, locals=local, evaluate=False)


def _mesma_dim(qs, contexto: str):
    base = qs[0]
    for q in qs[1:]:
        if base.dimensionality != q.dimensionality:
            raise ErroDimensional(
                f"{contexto}: {base.dimensionality} != {q.dimensionality}")
    return base


def _avaliar(no, amb: dict):
    """Avalia o nó devolvendo uma grandeza pint (magnitude arbitrária > 0)."""
    if isinstance(no, sp.Symbol):
        if no.name not in amb:
            raise ErroDimensional(f"variável sem unidade declarada: {no.name}")
        return amb[no.name]
    if no.is_Number or no in (sp.pi, sp.E):
        return Q_(float(no), "")
    if isinstance(no, sp.Add):
        termos = [_avaliar(a, amb) for a in no.args]
        _mesma_dim(termos, f"soma '{no}'")
        tot = termos[0]
        for t in termos[1:]:
            tot = tot + t.to(tot.units)
        return tot
    if isinstance(no, sp.Mul):
        r = Q_(1.0, "")
        for a in no.args:
            r = r * _avaliar(a, amb)
        return r
    if isinstance(no, sp.Pow):
        b = _avaliar(no.base, amb)
        e = _avaliar(no.exp, amb)
        if not e.dimensionless:
            raise ErroDimensional(f"expoente com dimensão em '{no}'")
        return b ** float(e.to("").magnitude)
    if isinstance(no, (sp.Max, sp.Min)):
        args = [_avaliar(a, amb) for a in no.args]
        base = _mesma_dim(args, f"{type(no).__name__} '{no}'")
        vals = [a.to(base.units).magnitude for a in args]
        return Q_(max(vals) if isinstance(no, sp.Max) else min(vals), base.units)
    if isinstance(no, sp.Abs):
        return abs(_avaliar(no.args[0], amb))
    if isinstance(no, sp.Function):  # sin, tan, exp, log...
        for a in no.args:
            q = _avaliar(a, amb)
            if not q.dimensionless:
                raise ErroDimensional(f"argumento com dimensão em '{no}'")
        return Q_(1.0, "")
    if isinstance(no, sp.core.relational.Relational):
        l = _avaliar(no.lhs, amb)
        r = _avaliar(no.rhs, amb)
        _mesma_dim([l, r], f"relação '{no}'")
        return Q_(1.0, "")
    if isinstance(no, (sp.And, sp.Or)):
        for a in no.args:
            _avaliar(a, amb)
        return Q_(1.0, "")
    raise ErroDimensional(f"nó não suportado: {type(no).__name__} em '{no}'")


def _ambiente(reg: dict, extra: dict) -> tuple[dict, list]:
    amb, faltando = {}, []
    variaveis = reg.get("variaveis") or {}
    for nome, meta in variaveis.items():
        un = (extra.get(nome) if extra else None)
        if un is None and isinstance(meta, dict):
            un = meta.get("unidade_pint")
        if un is None:
            faltando.append(nome)
            continue
        amb[nome] = Q_(1.7, un)  # magnitude arbitrária, não nula
    for nome, meta in (reg.get("constantes") or {}).items():
        amb[nome] = Q_(float(meta["valor"]), meta.get("unidade_pint", ""))
    for nome, un in (extra or {}).items():
        amb.setdefault(nome, Q_(1.7, un))
    return amb, faltando


def checar(caminho: str, mapa: dict | None) -> int:
    dados = yaml.safe_load(open(caminho, encoding="utf-8"))
    registros = dados.get("regras") or dados.get("formulas") or []
    falhas = 0
    for reg in registros:
        exprs = reg.get("sympy") or reg.get("expressoes") or []
        if not exprs:
            continue
        rid = reg.get("id", "?")
        extra = {}
        if mapa:
            extra.update(mapa.get("*", {}))
            extra.update(mapa.get(rid, {}))
        amb, _ = _ambiente(reg, extra)
        for e in exprs:
            try:
                _avaliar(_parse(e), amb)
                print(f"OK    {rid:48s} {e}")
            except ErroDimensional as err:
                falhas += 1
                print(f"FALHA {rid:48s} {e}\n      -> {err}")
            except Exception as err:  # parsing
                falhas += 1
                print(f"ERRO  {rid:48s} {e}\n      -> {type(err).__name__}: {err}")
    print(f"--- {falhas} falha(s) dimensional(is) ---")
    return falhas


def sanity(caminho: str) -> int:
    dados = yaml.safe_load(open(caminho, encoding="utf-8"))
    bloco = dados.get("sanity_check")
    if not bloco:
        print("sem bloco sanity_check")
        return 1
    falhas = 0
    for caso in bloco["casos"]:
        print(f"== {caso['id']}: {caso.get('descricao', '')}")
        amb = {k: Q_(float(v["valor"]), v.get("unidade_pint", ""))
               for k, v in caso["valores"].items()}
        for passo in caso["passos"]:
            alvo, expr = passo["alvo"], passo["expr"]
            q = _avaliar_num(_parse(expr), amb)
            un = passo.get("unidade_pint")
            if un:
                q = q.to(un)
            amb[alvo] = q
            print(f"   {alvo:22s} = {q:~.4g}   [{passo.get('regra', '')}]")
        for nome, fx in (caso.get("faixas") or {}).items():
            v = amb[nome].to(fx["unidade_pint"]).magnitude
            ok = fx["min"] <= v <= fx["max"]
            falhas += (not ok)
            print(f"   faixa {nome}: {v:.4g} em [{fx['min']}, {fx['max']}] "
                  f"{fx['unidade_pint']} -> {'OK' if ok else 'FORA DA FAIXA'}")
        for nome, esp in (caso.get("esperado") or {}).items():
            v = amb[nome].to(esp["unidade_pint"]).magnitude
            ok = abs(v - esp["valor"]) <= esp["tol_abs"]
            falhas += (not ok)
            print(f"   esperado {nome}: {v:.6g} vs {esp['valor']} "
                  f"(tol {esp['tol_abs']}) -> {'OK' if ok else 'DIVERGE'}")
        for cond in caso.get("condicoes") or []:
            ok = bool(_avaliar_num(_parse(cond["expr"]), amb))
            esperado = cond.get("esperado", True)
            falhas += (ok != esperado)
            print(f"   condicao {cond['expr']}: {ok} "
                  f"(esperado {esperado}) -> {'OK' if ok == esperado else 'FALHA'}")
    print(f"--- {falhas} falha(s) no sanity check ---")
    return falhas


def _avaliar_num(no, amb):
    """Avaliação numérica com pint (magnitudes reais)."""
    if isinstance(no, sp.Symbol):
        return amb[no.name]
    if no.is_Number:
        return Q_(float(no), "")
    if isinstance(no, sp.Add):
        vals = [_avaliar_num(a, amb) for a in no.args]
        tot = vals[0]
        for v in vals[1:]:
            tot = tot + v
        return tot
    if isinstance(no, sp.Mul):
        r = Q_(1.0, "")
        for a in no.args:
            r = r * _avaliar_num(a, amb)
        return r
    if isinstance(no, sp.Pow):
        return _avaliar_num(no.base, amb) ** float(_avaliar_num(no.exp, amb).to("").magnitude)
    if isinstance(no, (sp.Max, sp.Min)):
        vals = [_avaliar_num(a, amb) for a in no.args]
        u = vals[0].units
        mags = [v.to(u).magnitude for v in vals]
        return Q_(max(mags) if isinstance(no, sp.Max) else min(mags), u)
    if isinstance(no, sp.core.relational.Relational):
        l, r = _avaliar_num(no.lhs, amb), _avaliar_num(no.rhs, amb)
        r = r.to(l.units)
        op = {sp.Ge: lambda a, b: a >= b, sp.Le: lambda a, b: a <= b,
              sp.Gt: lambda a, b: a > b, sp.Lt: lambda a, b: a < b}[type(no)]
        return op(l.magnitude, r.magnitude)
    raise ErroDimensional(f"nó não suportado na avaliação numérica: {no}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("arquivo", nargs="?", default="ruleset.yaml")
    ap.add_argument("--unidades", help="YAML com unidades por registro")
    ap.add_argument("--sanity", action="store_true")
    a = ap.parse_args()
    mapa = yaml.safe_load(open(a.unidades, encoding="utf-8")) if a.unidades else None
    falhas = checar(a.arquivo, mapa)
    if a.sanity:
        falhas += sanity(a.arquivo)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
