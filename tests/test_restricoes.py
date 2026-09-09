from calc_core.geotecnico.restricoes import verificar_dimensao_minima


def test_dimensao_acima_do_minimo_passa():
    v = verificar_dimensao_minima(B=1.20, L=1.50)
    assert v.aplicavel is True
    assert v.ok is True


def test_dimensao_abaixo_do_minimo_falha():
    v = verificar_dimensao_minima(B=0.50, L=1.50)
    assert v.ok is False


def test_dimensao_exatamente_no_minimo_passa():
    v = verificar_dimensao_minima(B=0.60, L=0.60, dimensao_minima=0.60)
    assert v.ok is True


def test_usa_o_menor_lado():
    # B grande, L pequeno: quem decide é o menor dos dois lados.
    v = verificar_dimensao_minima(B=3.00, L=0.40)
    assert v.ok is False
