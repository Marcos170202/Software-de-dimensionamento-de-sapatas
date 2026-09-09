"""Testes de calc_core.geotecnico.geometria.

Quatro famílias, seguindo a metodologia de a7-validador.md:
1. Conformidade — caso com valores calculados à mão (ver relatorios/conformidade.md).
   NÃO é um exemplo de livro-texto publicado: este ambiente não tem acesso a
   um exercício resolvido de bibliografia (ex.: Alonso), então o caso abaixo
   foi calculado manualmente a partir da própria fórmula da NBR 6122 §7.6.1 e
   serve como regressão, não como validação externa independente. Registrado
   como limitação em relatorios/conformidade.md.
2. Equilíbrio — sigma_atuante * area_final == N_total, sempre.
3. Invariância — dobrar N_k dobra a área necessária; girar pilar_a/pilar_b
   troca B por L.
4. Contorno — carga muito leve aciona o mínimo de 60 cm; entrada inválida
   rejeita explicitamente (sem extrapolação silenciosa).
"""
import math

import pytest
from hypothesis import given, strategies as st

from calc_core.geotecnico.geometria import dimensionar_sapata_carga_centrada
from calc_core.modelos import EntradaSapataCentrada


# --- 1. Conformidade -------------------------------------------------------

def test_caso_calculado_a_mao_pilar_30x50():
    """N_k=1200 kN, sigma_adm=250 kPa, pilar 0,30x0,50 m, sem peso próprio.

    Cálculo manual (ver relatorios/conformidade.md):
      A_nec = 1200 / 250 = 4,80 m²
      4c² + 2(0,8)c + (0,15 - 4,80) = 0  ->  c = 0,8966 m
      B_bruto = 0,30 + 2*0,8966 = 2,093 m ; L_bruto = 0,50 + 2*0,8966 = 2,293 m
      arredondado (módulo 5 cm, para cima): B=2,10 m ; L=2,30 m
      area_final = 4,83 m² ; sigma_atuante = 1200/4,83 = 248,4 kPa
    """
    entrada = EntradaSapataCentrada(
        N_k=1200, sigma_adm=250, pilar_a=0.30, pilar_b=0.50,
        considerar_peso_proprio=False,
    )
    r = dimensionar_sapata_carga_centrada(entrada)

    assert r.area_necessaria == pytest.approx(4.80, abs=0.01)
    assert r.B == pytest.approx(2.10, abs=0.001)
    assert r.L == pytest.approx(2.30, abs=0.001)
    assert r.tensao_atuante == pytest.approx(248.4, abs=0.5)
    assert r.tensao_atuante <= entrada.sigma_adm
    assert r.aprovado


def test_peso_proprio_minimo_eleva_area_5_por_cento():
    base = EntradaSapataCentrada(
        N_k=1000, sigma_adm=200, pilar_a=0.40, pilar_b=0.40,
        considerar_peso_proprio=False,
    )
    com_pp = EntradaSapataCentrada(
        N_k=1000, sigma_adm=200, pilar_a=0.40, pilar_b=0.40,
        considerar_peso_proprio=True, percentual_peso_proprio=0.05,
    )
    r_base = dimensionar_sapata_carga_centrada(base)
    r_pp = dimensionar_sapata_carga_centrada(com_pp)

    assert r_pp.N_total == pytest.approx(r_base.N_total * 1.05)
    assert r_pp.area_necessaria == pytest.approx(r_base.area_necessaria * 1.05)


# --- 2. Equilíbrio -----------------------------------------------------------

@given(
    N_k=st.floats(min_value=50, max_value=5000),
    sigma_adm=st.floats(min_value=50, max_value=600),
    pilar_a=st.floats(min_value=0.20, max_value=1.20),
    pilar_b=st.floats(min_value=0.20, max_value=1.20),
)
def test_equilibrio_sigma_vezes_area_igual_N_total(N_k, sigma_adm, pilar_a, pilar_b):
    entrada = EntradaSapataCentrada(
        N_k=N_k, sigma_adm=sigma_adm, pilar_a=pilar_a, pilar_b=pilar_b,
        considerar_peso_proprio=False,
    )
    r = dimensionar_sapata_carga_centrada(entrada)

    assert r.tensao_atuante * r.area_final == pytest.approx(r.N_total, rel=1e-9)
    # a sapata construída nunca pode transmitir mais que sigma_adm ao terreno
    assert r.tensao_atuante <= entrada.sigma_adm + 1e-9


# --- 3. Invariância ----------------------------------------------------------

@given(
    N_k=st.floats(min_value=100, max_value=2000),
    sigma_adm=st.floats(min_value=80, max_value=500),
    pilar=st.floats(min_value=0.20, max_value=1.00),
)
def test_dobrar_N_k_dobra_area_necessaria(N_k, sigma_adm, pilar):
    entrada_1x = EntradaSapataCentrada(
        N_k=N_k, sigma_adm=sigma_adm, pilar_a=pilar, pilar_b=pilar,
        considerar_peso_proprio=False,
    )
    entrada_2x = EntradaSapataCentrada(
        N_k=2 * N_k, sigma_adm=sigma_adm, pilar_a=pilar, pilar_b=pilar,
        considerar_peso_proprio=False,
    )
    r1 = dimensionar_sapata_carga_centrada(entrada_1x)
    r2 = dimensionar_sapata_carga_centrada(entrada_2x)

    assert r2.area_necessaria == pytest.approx(2 * r1.area_necessaria, rel=1e-9)


@given(
    N_k=st.floats(min_value=100, max_value=2000),
    sigma_adm=st.floats(min_value=80, max_value=500),
    a=st.floats(min_value=0.20, max_value=1.00),
    b=st.floats(min_value=0.20, max_value=1.00),
)
def test_girar_pilar_90_graus_troca_B_por_L(N_k, sigma_adm, a, b):
    original = EntradaSapataCentrada(
        N_k=N_k, sigma_adm=sigma_adm, pilar_a=a, pilar_b=b,
        considerar_peso_proprio=False,
    )
    girado = EntradaSapataCentrada(
        N_k=N_k, sigma_adm=sigma_adm, pilar_a=b, pilar_b=a,
        considerar_peso_proprio=False,
    )
    r_original = dimensionar_sapata_carga_centrada(original)
    r_girado = dimensionar_sapata_carga_centrada(girado)

    assert r_girado.B == pytest.approx(r_original.L)
    assert r_girado.L == pytest.approx(r_original.B)


# --- 4. Contorno ---------------------------------------------------------

def test_carga_leve_aciona_dimensao_minima():
    """Terreno muito bom + carga muito leve: área calculada < 0,36 m² (0,6²).

    O software deve IMPOR o mínimo de 60 cm (NBR 6122 §7.7.1), não apenas
    reportar falha — ver comentário em geometria.py.
    """
    entrada = EntradaSapataCentrada(
        N_k=10, sigma_adm=500, pilar_a=0.20, pilar_b=0.20,
        considerar_peso_proprio=False,
    )
    r = dimensionar_sapata_carga_centrada(entrada)

    assert r.B >= 0.60
    assert r.L >= 0.60
    assert r.aprovado
    # a verificação de dimensão mínima deve constar do memorial mesmo tendo
    # sido satisfeita por imposição, não por cálculo direto
    regra_dimensao = next(
        v for v in r.verificacoes if v.regra == "NBR6122-7.7.1-dimensao-minima"
    )
    assert regra_dimensao.ok is True


@pytest.mark.parametrize("campo,valor", [
    ("N_k", 0),
    ("N_k", -100),
    ("sigma_adm", 0),
    ("sigma_adm", -50),
    ("pilar_a", 0),
    ("pilar_b", -0.3),
    ("dimensao_minima", 0),
    ("dimensao_minima", -0.6),
    ("modulo_arredondamento", 0),
    ("modulo_arredondamento", -0.05),
])
def test_entrada_fora_do_dominio_rejeita_explicitamente(campo, valor):
    """Nunca extrapolar em silêncio — entrada inválida levanta ValueError."""
    kwargs = dict(N_k=1000, sigma_adm=200, pilar_a=0.4, pilar_b=0.4)
    kwargs[campo] = valor
    with pytest.raises(ValueError):
        EntradaSapataCentrada(**kwargs)


def test_percentual_peso_proprio_fora_do_dominio_rejeita():
    with pytest.raises(ValueError):
        EntradaSapataCentrada(
            N_k=1000, sigma_adm=200, pilar_a=0.4, pilar_b=0.4,
            percentual_peso_proprio=1.5,
        )
