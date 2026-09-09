"""Proteção da REGRA DE PROIBIÇÃO de flexão nas duas direções.

    Ref.: ABNT NBR 6118:2023, itens 22.6.2.2-a) e 22.6.2.3-a), p. 192.
    [rule: NBR6118-22.6.2.2a-flexao-duas-direcoes]  (ruleset.yaml, APROVADA,
    tipo PROIBICAO)

Texto conferido pelo a2-verificador na p. 192:
    22.6.2.2-a) "trabalho à flexão nas duas direções, admitindo-se que, para
    cada uma delas, a tração na flexão seja uniformemente distribuída na
    largura correspondente da sapata";
    22.6.2.3-a) "trabalho à flexão nas duas direções, não sendo possível
    admitir tração na flexão uniformemente distribuída (...)".
As duas alíneas são INCONDICIONAIS quanto às duas direções.

POR QUE ESTE ARQUIVO EXISTE
---------------------------
A regra estava APROVADA no ruleset desde a versão 3, mas nenhum teste a
protegia: um redutor introduzido por engano na direção "secundária" — o
mutante canônico é

    As_y *= 0.2        # "20 % de 20.1", transposto como TETO em vez de PISO

— não quebrava nada na suíte. Os testes abaixo fecham esse buraco em três
frentes: simetria exata quando a geometria é simétrica, ausência de redutor
quando a flexão governa, e armadura mínima INTEGRAL (não fracionada) na
direção curta de uma sapata alongada.

Observação importante sobre o que NÃO é redutor: as duas direções têm alturas
úteis diferentes (d_x na camada inferior, d_y na superior, separadas por uma
bitola). Por isso As_y > As_x é o resultado CORRETO numa sapata quadrada com
flexão governante — a direção de cima tem braço menor e precisa de mais aço.
O que a proibição veda é um fator aplicado por ser "a outra direção".
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
from calc_core.sapata_isolada.sapata import (
    GeometriaImposta,
    OpcoesProjeto,
    Sapata,
)


FCK = 25.0


def _dimensionar(pilar: Pilar, N: float, sigma_adm: float, **op):
    combs = gerar_combinacoes([CasoCarga("G", Esforcos(N=N))])
    s = Sapata(pilar, Solo(sigma_adm=sigma_adm, hf=1.5), Concreto(FCK),
               Aco(500.0), combs, 0.045,
               OpcoesProjeto(verificar_recalque=False, **op))
    res = s.dimensionar()
    return res, {ar.direcao: ar for ar in res.armaduras}


# --------------------------------------------------------------------------- #
#  1. Simetria exata: quadrado + pilar quadrado + carga centrada
# --------------------------------------------------------------------------- #
def test_sapata_quadrada_arma_as_duas_direcoes_igualmente():
    """Girar o problema 90° troca x por y e nada mais.

    Aqui a armadura mínima governa nas duas direções (As_min = rho_min·a·h,
    idêntica por simetria), então a igualdade tem de ser EXATA. Qualquer
    redutor aplicado à direção Y — antes ou depois de As_adot — quebra este
    teste.
    """
    res, arm = _dimensionar(Pilar(ap=0.40, bp=0.40), N=1200.0, sigma_adm=250.0)
    assert res.a == pytest.approx(res.b, rel=1e-12), "premissa: sapata quadrada"
    x, y = arm["X"], arm["Y"]

    assert x.Md == pytest.approx(y.Md, rel=1e-9)
    assert x.As_min == pytest.approx(y.As_min, rel=1e-9)
    assert x.As_adot == pytest.approx(y.As_adot, rel=1e-9)
    assert x.As_efetiva == pytest.approx(y.As_efetiva, rel=1e-9)
    assert (x.phi_mm, x.n_barras) == (y.phi_mm, y.n_barras)
    assert x.As_adot > 0.0 and y.As_adot > 0.0

    # a mínima é INTEGRAL (fator 1,0 · rho_min · largura · h), não fracionada
    esperado_min = Concreto(FCK).rho_min_flexao * res.b * res.h
    assert x.As_min == pytest.approx(esperado_min, rel=1e-9)
    assert y.As_min == pytest.approx(
        Concreto(FCK).rho_min_flexao * res.a * res.h, rel=1e-9)


# --------------------------------------------------------------------------- #
#  2. Flexão governante: nenhuma direção sai fracionada
# --------------------------------------------------------------------------- #
def test_sapata_quadrada_com_flexao_governante_nao_tem_direcao_reduzida():
    """Geometria imposta 2,00 x 2,00 x 0,60 m com N = 2500 kN: As calculada
    supera a mínima nas duas direções, de modo que quem governa é o modelo
    (bielas/flexão) e não o piso.

    Valores medidos no código correto:
        X: As_adot = 29,43 cm²  (d = 0,547 m)
        Y: As_adot = 30,32 cm²  (d = 0,531 m)
    A diferença de 3 % vem só da altura útil de cada camada. Com o mutante
    `As_y *= 0.2` a razão Y/X cairia de 1,03 para 0,21.
    """
    res, arm = _dimensionar(
        Pilar(ap=0.40, bp=0.40), N=2500.0, sigma_adm=700.0,
        geometria_imposta=GeometriaImposta(a=2.00, b=2.00, h=0.60))
    x, y = arm["X"], arm["Y"]

    assert x.As_calc > x.As_min and y.As_calc > y.As_min, (
        "premissa do teste: a flexão/bielas tem de governar, não a mínima")
    # o valor adotado é exatamente o do modelo, sem fator intermediário
    for ar in (x, y):
        do_modelo = ar.As_bielas if ar.modelo == "bielas" else ar.As_flexao
        assert ar.As_calc == pytest.approx(do_modelo, rel=1e-12)
        assert ar.As_adot == pytest.approx(max(ar.As_calc, ar.As_min), rel=1e-12)

    razao = y.As_adot / x.As_adot
    assert 1.0 <= razao <= 1.06, (
        f"razão Y/X = {razao:.3f}: só a diferença de altura útil justifica "
        "diferença entre as direções")


# --------------------------------------------------------------------------- #
#  3. Sapata alongada: a direção CURTA não vira "armadura de distribuição"
# --------------------------------------------------------------------------- #
def test_sapata_alongada_direcao_curta_recebe_armadura_integral():
    """a = 3,00 m / b = 1,00 m — o caso em que a tentação de tratar a sapata
    como "corrida" e reduzir a direção curta é maior.

    Medido no código correto (N = 1200 kN, h = 0,95 m, C25):
        X (direção longa) : As_adot = 14,54 cm²  (bielas governam)
        Y (direção curta) : As_adot = 42,75 cm²  (As_min integral governa)
    A direção curta recebe MAIS aço que a longa, porque a mínima é
    rho_min·(largura = a = 3,00 m)·h e não uma fração da outra direção. O
    mutante `As_y *= 0.2` daria 8,55 cm², abaixo até da armadura da direção
    longa — e abaixo do mínimo de 19.3.3.2/Tabela 17.3.
    """
    res, arm = _dimensionar(
        Pilar(ap=0.30, bp=0.30), N=1200.0, sigma_adm=400.0,
        geometria_imposta=GeometriaImposta(a=3.00, b=1.00, h=0.95))
    x, y = arm["X"], arm["Y"]

    rho_min = Concreto(FCK).rho_min_flexao
    # largura resistente da direção Y é a dimensão a (perpendicular)
    assert y.As_min == pytest.approx(rho_min * 3.00 * 0.95, rel=1e-9)
    assert y.As_adot == pytest.approx(max(y.As_calc, y.As_min), rel=1e-12)
    assert y.As_adot == pytest.approx(y.As_min, rel=1e-12), (
        "premissa: nesta geometria quem governa a direção curta é a mínima")
    assert y.As_efetiva >= y.As_adot * 0.99

    # a direção curta NÃO é uma fração da longa
    assert y.As_adot > x.As_adot
    assert y.As_adot > 0.20 * x.As_adot * 5.0   # longe de qualquer redutor
    assert x.As_adot > 0.0


def test_momento_no_balanco_existe_nas_duas_direcoes_da_sapata_alongada():
    """Mesmo com b/a = 1/3, o momento da direção curta é calculado (não zerado
    nem substituído por regra de 'armadura de distribuição')."""
    from calc_core.sapata_isolada.momentos import momento_unitario

    mx = momento_unitario(N=1000.0, Mx=0.0, My=0.0, a=3.00, b=1.00,
                          ap=0.30, bp=0.30, direcao="X")
    my = momento_unitario(N=1000.0, Mx=0.0, My=0.0, a=3.00, b=1.00,
                          ap=0.30, bp=0.30, direcao="Y")
    assert mx > 0.0 and my > 0.0
    # balanços de 1,35 m e 0,35 m -> razão dos momentos = (1,35/0,35)²
    assert mx / my == pytest.approx((1.35 / 0.35) ** 2, rel=1e-9)


def test_simetria_do_momento_unitario_sob_rotacao_de_90_graus():
    """Girar o problema 90° troca x por y e nada mais (teste de simetria)."""
    from calc_core.sapata_isolada.momentos import momento_unitario

    direto = momento_unitario(N=900.0, Mx=0.0, My=120.0, a=2.40, b=1.60,
                              ap=0.40, bp=0.20, direcao="X")
    girado = momento_unitario(N=900.0, Mx=120.0, My=0.0, a=1.60, b=2.40,
                              ap=0.20, bp=0.40, direcao="Y")
    assert direto == pytest.approx(girado, rel=1e-12)
