"""Cobertura dos ramos `travar_a` / `travar_b` de `Sapata._planta_para_area`.

Contexto
--------
Na rodada 1 de correções do GATE 2 os dois ramos passaram a usar a função
auxiliar `livre()`, que aplica o PISO DE BALANÇO (a dimensão livre não pode
sair menor que `dim_pilar + 2·modulo_dim`) além do piso de `dim_minima`. O a6
apontou na rodada 2 que nenhum teste exercitava esses dois ramos —
`--cov-report=term-missing` marcava as linhas como não cobertas — e que a
mensagem de commit da rodada 1 ("saída idêntica em 5 casos") não era amostra
representativa: numa varredura ampla o a6 encontrou ~7 % de casos com saída
diferente, SEMPRE para sapata maior (conservador).

MUDANÇA REAL DE SAÍDA, documentada aqui e não deixada implícita
---------------------------------------------------------------
Com `Pilar(ap=0,60 ; bp=0,80)`, `travar_a = 0,80 m`, área necessária de
0,50 m² e `modulo_dim = 0,05 m`:

    versão ANTIGA : (a, b) = (0,80 ; 0,65) m
    versão ATUAL  : (a, b) = (0,80 ; 0,90) m

O valor antigo é geometricamente impossível — b = 0,65 m com bp = 0,80 m põe o
pilar para fora da sapata — e explodia adiante, em `rigidez.classificar`, com
"Pilar não cabe na sapata". O valor atual dá 0,05 m de balanço por lado e o
dimensionamento roda até o fim. Não é mudança de fórmula normativa: é o
domínio de validade de 22.6.1, que pressupõe (b - b_p)/2 > 0.

O piso de balanço vale só para a dimensão LIVRE. Dimensão TRAVADA pelo
projetista continua sem correção silenciosa: se ela não couber, o erro sobe.

Rodada 3: o piso deixou de ser `2·modulo_dim` (granularidade de DESENHO) e
passou a ser `2·OpcoesProjeto.balanco_minimo` (critério de PROJETO, um balanço
por lado). Com o padrão `balanco_minimo = 0,05 m` os dois valores coincidem e a
saída é idêntica — conferido em 1008 combinações de (ap, bp, área, trava):
0 divergências. `test_regressao_planta_apos_extrair_balanco_minimo` fixa a
saída de casos concretos para que uma futura mudança de padrão não passe
despercebida.
"""
import pytest

from calc_core.sapata_isolada.acoes import (
    CasoCarga,
    Esforcos,
    Pilar,
    gerar_combinacoes,
)
from calc_core.sapata_isolada.geotecnia import Solo
from calc_core.sapata_isolada.materiais import Aco, Concreto
from calc_core.sapata_isolada.sapata import OpcoesProjeto, Sapata


def _sapata(pilar: Pilar, N: float = 400.0, sigma_adm: float = 250.0, **op):
    combs = gerar_combinacoes([CasoCarga("G", Esforcos(N=N))])
    return Sapata(pilar, Solo(sigma_adm=sigma_adm, hf=1.5), Concreto(25.0),
                  Aco(500.0), combs, 0.045,
                  OpcoesProjeto(verificar_recalque=False, **op))


# --------------------------------------------------------------------------- #
#  Sucesso: dimensão travada que CABE
# --------------------------------------------------------------------------- #
def test_travar_a_mantem_a_e_dimensiona_b_com_piso_de_balanco():
    pilar = Pilar(ap=0.60, bp=0.40)
    s = _sapata(pilar, travar_a=0.70)
    m = s.op.modulo_dim

    a, b = s._planta_para_area(0.30)     # área pequena de propósito
    assert a == pytest.approx(0.70, rel=1e-12), "a travado não pode mudar"
    assert b >= s._arredondar(pilar.bp + 2.0 * m) - 1e-9
    assert b >= s.op.dim_minima - 1e-9

    r = s.dimensionar()                  # roda até o fim, sem exceção
    assert r.a == pytest.approx(0.70, rel=1e-12)
    assert r.b > pilar.bp and r.a > pilar.ap
    assert r.h > 0.0 and len(r.armaduras) == 2
    # neste caso `dim_minima` (0,60 m) já dominava o piso de balanço (0,50 m):
    # a saída é a MESMA da versão anterior a esta leva de correções.


def test_travar_b_mantem_b_e_dimensiona_a_com_piso_de_balanco():
    """Espelho do anterior (simetria: girar 90° troca x por y)."""
    pilar = Pilar(ap=0.40, bp=0.60)
    s = _sapata(pilar, travar_b=0.70)
    m = s.op.modulo_dim

    a, b = s._planta_para_area(0.30)
    assert b == pytest.approx(0.70, rel=1e-12)
    assert a >= s._arredondar(pilar.ap + 2.0 * m) - 1e-9
    assert a >= s.op.dim_minima - 1e-9

    r = s.dimensionar()
    assert r.b == pytest.approx(0.70, rel=1e-12)
    assert r.a > pilar.ap and r.b > pilar.bp


@pytest.mark.parametrize("op,esperado", [
    (dict(travar_a=0.80), (0.80, 0.90)),
    (dict(travar_b=0.80), (0.90, 0.80)),
])
def test_piso_de_balanco_muda_a_saida_quando_dim_minima_nao_domina(op, esperado):
    """Caso em que a mudança de comportamento da rodada 1 é REAL.

    Pilar 0,60 x 0,80 m (ou girado), área necessária 0,50 m²:
        ANTIGO -> dimensão livre = max(0,60 ; ceil(0,50/0,80)) = 0,65 m
                  (pilar de 0,80 m para fora da sapata -> ValueError adiante)
        ATUAL  -> max(0,60 ; 0,65 ; 0,80 + 2·0,05) = 0,90 m
    Sempre para sapata MAIOR: conservador, sem risco de segurança.
    """
    ap, bp = (0.60, 0.80) if "travar_a" in op else (0.80, 0.60)
    s = _sapata(Pilar(ap=ap, bp=bp), N=150.0, sigma_adm=300.0, **op)
    assert s._planta_para_area(0.50) == pytest.approx(esperado, rel=1e-12)

    r = s.dimensionar()
    assert (r.a, r.b) == pytest.approx(esperado, rel=1e-12)
    assert r.a > ap and r.b > bp


# --------------------------------------------------------------------------- #
#  Regressão da extração de `balanco_minimo` (era 2·modulo_dim embutido)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("nome,pilar,N,sigma_adm,op,esperado", [
    ("centrada típica",
     Pilar(0.30, 0.30), 800.0, 250.0, {}, (1.95, 1.95, 0.55, 0.20)),
    ("pilar retangular",
     Pilar(0.20, 0.60), 1000.0, 300.0, {}, (1.75, 2.15, 0.55, 0.20)),
    ("carga pequena / pilar grande (piso de balanço ATIVO)",
     Pilar(0.60, 0.60), 100.0, 300.0, {}, (0.70, 0.70, 0.30, 0.20)),
    ("dimensão a travada",
     Pilar(0.60, 0.40), 400.0, 250.0, dict(travar_a=0.70),
     (0.70, 2.60, 0.75, 0.25)),
    ("dimensão b travada, piso de balanço ATIVO",
     Pilar(0.80, 0.60), 150.0, 300.0, dict(travar_b=0.80),
     (0.90, 0.80, 0.30, 0.20)),
])
def test_regressao_planta_apos_extrair_balanco_minimo(
        nome, pilar, N, sigma_adm, op, esperado):
    """Fixa (a, b, h, h0) de casos que já funcionavam ANTES da rodada 3.

    Os cinco valores foram medidos no código imediatamente anterior à extração
    de `balanco_minimo` e reproduzidos sem alteração depois dela — o refactor é
    de nomenclatura, não de resultado. Se um dia `balanco_minimo` mudar de
    padrão, estes números mudam junto e a mudança fica visível, em vez de
    passar silenciosa como ocorreu com o piso de balanço da rodada 1.
    """
    s = _sapata(pilar, N=N, sigma_adm=sigma_adm, **op)
    assert s.op.balanco_minimo == pytest.approx(0.05, rel=1e-12)
    r = s.dimensionar()
    assert (r.a, r.b, r.h, r.h0) == pytest.approx(esperado, abs=1e-9), nome


def test_balanco_minimo_e_independente_do_modulo_de_desenho():
    """`modulo_dim` é granularidade de desenho; `balanco_minimo` é critério de
    projeto. Mudar só o balanço mínimo tem de mudar a planta, sem tocar no
    arredondamento — era justamente isso que a versão com `2·modulo_dim`
    embutido não permitia separar.

    Pilar 0,60 x 0,60 m, área necessária 0,20 m² (cai dentro do próprio pilar):
        balanco_minimo = 0,05 m -> 0,70 x 0,70 m
        balanco_minimo = 0,20 m -> 1,00 x 1,00 m
    """
    pilar = Pilar(0.60, 0.60)
    padrao = _sapata(pilar, N=100.0, sigma_adm=300.0)
    largo = _sapata(pilar, N=100.0, sigma_adm=300.0, balanco_minimo=0.20)
    assert padrao._planta_para_area(0.20) == pytest.approx((0.70, 0.70))
    assert largo._planta_para_area(0.20) == pytest.approx((1.00, 1.00))
    assert padrao.op.modulo_dim == largo.op.modulo_dim == 0.05


# --------------------------------------------------------------------------- #
#  Rejeição: dimensão travada que NÃO cabe — nada é corrigido em silêncio
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("op", [
    dict(travar_a=0.60),      # travar_a == ap
    dict(travar_a=0.50),      # travar_a  < ap
])
def test_travar_a_menor_ou_igual_ao_pilar_e_rejeitado(op):
    """A dimensão travada pelo projetista não recebe piso de balanço: se o
    pilar não cabe, `rigidez.classificar` levanta ValueError explícito em vez
    de a rotina aumentar a sapata por conta própria (o que contrariaria uma
    imposição de projeto sem avisar)."""
    s = _sapata(Pilar(ap=0.60, bp=0.40), **op)
    with pytest.raises(ValueError, match="Pilar não cabe na sapata"):
        s.dimensionar()


@pytest.mark.parametrize("op", [
    dict(travar_b=0.60),
    dict(travar_b=0.50),
])
def test_travar_b_menor_ou_igual_ao_pilar_e_rejeitado(op):
    s = _sapata(Pilar(ap=0.40, bp=0.60), **op)
    with pytest.raises(ValueError, match="Pilar não cabe na sapata"):
        s.dimensionar()
