"""Teste de aderência normativa do critério rígida/flexível.

    Ref.: ABNT NBR 6118:2023, item 22.6.1, p. 191.
    [rule: NBR6118-22.6.1-rigidez]  (ruleset.yaml, status APROVADA)

Enunciado literal conferido por leitura visual da p. 191 pelo a2-verificador:
"Quando se verifica a expressão a seguir, NAS DUAS DIREÇÕES, a sapata é
considerada rígida. Caso contrário, a sapata é considerada flexível."

    h >= (a - a_p)/3   e   h >= (b - b_p)/3

POR QUE ESTE ARQUIVO EXISTE
---------------------------
Na revisão de GATE 2 o a6-revisor aplicou um mutante em `rigidez.py`,
trocando

    h_nec = max((a - ap) / 3.0, (b - bp) / 3.0)     # correto
por
    h_nec = (a - ap) / 3.0                          # mutante: ignora Y

e os 57 testes então existentes no repositório PASSARAM — nenhum deles
exercitava um caso em que a direção Y (e não a X) governa a altura, de modo
que a exigência normativa "nas duas direções" ficava desprotegida. Este
arquivo fecha esse buraco: os testes abaixo morrem com aquele mutante.
"""
import pytest

from calc_core.sapata_isolada.rigidez import classificar
from calc_core.sapata_isolada.acoes import (
    CasoCarga,
    Esforcos,
    Pilar,
    gerar_combinacoes,
)
from calc_core.sapata_isolada.geotecnia import Solo
from calc_core.sapata_isolada.materiais import Aco, Concreto
from calc_core.sapata_isolada.sapata import OpcoesProjeto, Sapata


# Parâmetros de solo/concreto irrelevantes para o critério geométrico: entram
# só porque `classificar` também devolve os índices de Hetényi e Meyerhof
# (que NÃO são texto normativo). Fixados para manter o teste determinístico.
ECS_MPA = 24_000.0
KV = 25_000.0

# Cenário do a6: sapata alongada em Y. Direção X quase não tem balanço
# ((1,20 - 1,00)/3 = 0,0667 m), direção Y tem muito ((3,00 - 0,20)/3 = 0,9333 m).
CASO_Y = dict(a=1.20, b=3.00, ap=1.00, bp=0.20)
CASO_X = dict(a=3.00, b=1.20, ap=0.20, bp=1.00)   # o mesmo, girado 90°
H_NEC_ESPERADO = 2.80 / 3.0                        # 0,933333... m
H_ENSAIO = 0.35                                    # entre 0,0667 e 0,9333


def test_direcao_y_governante_torna_a_sapata_flexivel():
    """Direção Y governa: h = 0,35 m < 0,9333 m -> FLEXÍVEL.

    Com o mutante do a6 (`h_nec = (a - ap)/3`) daria h_nec = 0,0667 m e
    rigida_nbr = True — classificação do lado INSEGURO, porque dispensaria a
    verificação de punção que 22.6.2.3-b) exige da sapata flexível.
    """
    c = classificar(h=H_ENSAIO, h0=0.20, Ecs_MPa=ECS_MPA, kv=KV, **CASO_Y)
    assert c.h_necessario == pytest.approx(H_NEC_ESPERADO, abs=1e-6)
    assert c.h_necessario == pytest.approx(0.9333, abs=5e-5)
    assert c.rigida_nbr is False
    assert c.modelo_recomendado == "flexivel"


def test_direcao_x_governante_espelha_o_caso_y():
    """Simetria: girar o problema 90° troca x por y e nada mais.

    Este é o caso que os testes antigos já cobriam por acaso; sozinho ele NÃO
    mata o mutante do a6 (por isso o teste anterior existe).
    """
    c = classificar(h=H_ENSAIO, h0=0.20, Ecs_MPa=ECS_MPA, kv=KV, **CASO_X)
    assert c.h_necessario == pytest.approx(H_NEC_ESPERADO, abs=1e-6)
    assert c.rigida_nbr is False


def test_caso_x_e_caso_y_dao_o_mesmo_h_necessario():
    """O critério não pode depender de qual eixo o usuário chamou de 'a'."""
    cy = classificar(h=H_ENSAIO, h0=0.20, Ecs_MPa=ECS_MPA, kv=KV, **CASO_Y)
    cx = classificar(h=H_ENSAIO, h0=0.20, Ecs_MPa=ECS_MPA, kv=KV, **CASO_X)
    assert cy.h_necessario == pytest.approx(cx.h_necessario, rel=1e-12)
    assert cy.rigida_nbr == cx.rigida_nbr
    # os índices de Hetényi também devem apenas trocar de eixo
    assert cy.lambda_L_x == pytest.approx(cx.lambda_L_y, rel=1e-12)
    assert cy.lambda_L_y == pytest.approx(cx.lambda_L_x, rel=1e-12)


def test_mutante_do_a6_daria_rigida_no_mesmo_cenario():
    """Documenta o mutante literal do a6, para deixar explícito o que se perde.

    Não testa o código de produção: reproduz a expressão MUTADA aqui dentro e
    mostra que, no cenário CASO_Y, ela classificaria a sapata como rígida.
    Serve de âncora para quem, no futuro, "simplificar" `rigidez.py` de volta
    para uma única direção — o teste acima quebra e este explica por quê.
    """
    a, b, ap, bp = CASO_Y["a"], CASO_Y["b"], CASO_Y["ap"], CASO_Y["bp"]
    h_nec_mutante = (a - ap) / 3.0                     # ignora a direção Y
    assert h_nec_mutante == pytest.approx(0.0666667, abs=1e-6)
    assert H_ENSAIO >= h_nec_mutante                   # -> "rígida", errado
    h_nec_correto = max((a - ap) / 3.0, (b - bp) / 3.0)
    assert H_ENSAIO < h_nec_correto                    # -> flexível, correto


def test_altura_suficiente_nas_duas_direcoes_e_rigida():
    """Contraprova: com h acima das duas exigências, a sapata é rígida."""
    c = classificar(h=0.95, h0=0.35, Ecs_MPa=ECS_MPA, kv=KV, **CASO_Y)
    assert c.rigida_nbr is True
    assert c.modelo_recomendado == "rigida"


def test_caso_numerico_do_ruleset():
    """Confere os valores registrados em ruleset.yaml (checagem_numerica)."""
    comum = dict(a=2.00, b=2.00, ap=0.30, bp=0.50, h0=0.25,
                 Ecs_MPa=ECS_MPA, kv=KV)
    assert classificar(h=0.60, **comum).h_necessario == pytest.approx(
        0.5666667, abs=1e-6)
    assert classificar(h=0.60, **comum).rigida_nbr is True
    assert classificar(h=0.50, **comum).rigida_nbr is False
    # sapata muito alongada: h_nec = (6,00 - 0,20)/3 = 1,9333 m
    alongada = classificar(a=6.00, b=0.80, h=0.60, h0=0.25, ap=0.20, bp=0.20,
                           Ecs_MPa=ECS_MPA, kv=KV)
    assert alongada.h_necessario == pytest.approx(1.9333333, abs=1e-6)
    assert alongada.rigida_nbr is False


def test_alturas_da_sapata_respeita_as_duas_direcoes():
    """`Sapata._alturas` implementa o MESMO critério de 22.6.1 e por isso
    também precisa do caso com Y governante (mesmo mutante, outro arquivo:
    sapata.py)."""
    pilar = Pilar(ap=1.00, bp=0.20)
    solo = Solo(sigma_adm=250.0, hf=1.5)
    combs = gerar_combinacoes([CasoCarga("G", Esforcos(N=500.0))])
    s = Sapata(pilar, solo, Concreto(25.0), Aco(500.0), combs, 0.045,
               OpcoesProjeto(verificar_recalque=False))
    h, h0 = s._alturas(1.20, 3.00)
    assert h >= H_NEC_ESPERADO - 1e-9, (
        "altura pré-dimensionada ignorou a direção Y (b - bp)/3")
    assert h0 <= h


# --------------------------------------------------------------------------- #
#  Robustez de entrada (item 22.6.1 pressupõe balanço positivo nas 2 direções)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("kwargs", [
    dict(a=0.50, b=2.00, ap=0.50, bp=0.30),     # pilar = sapata em X
    dict(a=2.00, b=0.30, ap=0.30, bp=0.30),     # pilar = sapata em Y
    dict(a=0.40, b=2.00, ap=0.60, bp=0.30),     # pilar MAIOR que a sapata em X
    dict(a=2.00, b=0.40, ap=0.30, bp=0.60),     # pilar MAIOR que a sapata em Y
])
def test_pilar_nao_menor_que_a_sapata_e_rejeitado(kwargs):
    """Sem validação, h_necessario saía negativo e rigida_nbr = True em
    silêncio — a pior forma de errar."""
    with pytest.raises(ValueError):
        classificar(h=0.40, h0=0.20, Ecs_MPa=ECS_MPA, kv=KV, **kwargs)


@pytest.mark.parametrize("kwargs", [
    dict(a=0.0, b=2.00, ap=0.30, bp=0.30),
    dict(a=-2.0, b=2.00, ap=0.30, bp=0.30),
    dict(a=2.00, b=0.0, ap=0.30, bp=0.30),
    dict(a=2.00, b=2.00, ap=0.0, bp=0.30),
    dict(a=2.00, b=2.00, ap=0.30, bp=-0.10),
])
def test_dimensoes_nao_positivas_sao_rejeitadas(kwargs):
    with pytest.raises(ValueError):
        classificar(h=0.40, h0=0.20, Ecs_MPa=ECS_MPA, kv=KV, **kwargs)


@pytest.mark.parametrize("h,h0", [(0.0, 0.20), (-0.40, 0.20), (0.40, 0.0)])
def test_alturas_nao_positivas_sao_rejeitadas(h, h0):
    with pytest.raises(ValueError):
        classificar(a=2.00, b=2.00, ap=0.30, bp=0.30, h=h, h0=h0,
                    Ecs_MPa=ECS_MPA, kv=KV)


def test_modulo_nulo_da_erro_claro_e_nao_divisao_por_zero():
    with pytest.raises(ValueError):
        classificar(a=2.00, b=2.00, h=0.60, h0=0.25, ap=0.30, bp=0.30,
                    Ecs_MPa=0.0, kv=KV)


def test_kv_nulo_da_erro_claro():
    with pytest.raises(ValueError):
        classificar(a=2.00, b=2.00, h=0.60, h0=0.25, ap=0.30, bp=0.30,
                    Ecs_MPa=ECS_MPA, kv=0.0)


def test_carga_pequena_com_pilar_grande_ainda_tem_balanco():
    """Carga pequena + pilar grande: a área geotécnica necessária cabe dentro
    da própria seção do pilar e o pré-dimensionamento devolvia a = ap (sapata
    degenerada, sem balanço, h_necessario = 0 e 'rígida' por vacuidade).

    Com o piso de balanço em `_planta_para_area` a sapata sai maior que o
    pilar nas duas direções e o dimensionamento roda até o fim.
    """
    pilar = Pilar(ap=0.60, bp=0.60)
    solo = Solo(sigma_adm=300.0, hf=1.5)          # 100·1,05/300 = 0,35 m² < 0,36 m²
    combs = gerar_combinacoes([CasoCarga("G", Esforcos(N=100.0))])
    s = Sapata(pilar, solo, Concreto(25.0), Aco(500.0), combs, 0.045,
               OpcoesProjeto(verificar_recalque=False))
    a0, b0 = s._planta_inicial()
    assert a0 > pilar.ap and b0 > pilar.bp
    r = s.dimensionar()
    assert r.a > pilar.ap and r.b > pilar.bp
