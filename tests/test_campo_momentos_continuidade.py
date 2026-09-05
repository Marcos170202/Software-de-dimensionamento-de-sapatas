"""Regressão do campo de momentos usado nos desenhos (mapa 2D e superfície 3D).

Defeito corrigido (2026-08-26): dentro da projeção do pilar, `momento_1d()`
(em `campo_momentos`) fixava a posição na face ESQUERDA ou DIREITA conforme o
SINAL de `pos`, o que produzia um degrau artificial exatamente em `pos = 0` —
no meio do pilar — sempre que as duas faces tinham momentos diferentes (o caso
normal, com carga excêntrica). Na superfície 3D isso aparecia como um pico/funil
agudo sob o pilar; no mapa 2D, como uma aresta reta cruzando o centro.

`campo_de_grelha().clampar()` tinha o mesmo defeito, agravado: escolhia o "nó
imediatamente fora da projeção" por `min(fora, key=|‖c‖ − meia|)`, sem olhar o
sinal do nó preenchido. Em malha simétrica os dois candidatos empatam (a menos
de erro de ponto flutuante) e o `min` devolvia um lado arbitrário, de modo que
nós sob o pilar recebiam o momento da face OPOSTA.

A correção substitui os dois clamps por INTERPOLAÇÃO LINEAR entre os valores
das duas faces. Isso é uma escolha de desenho do campo de visualização: a
NBR 6118:2023, 22.6.4.1 (p. 192, lida por imagem da página) define a seção de
referência NA FACE do pilar e manda distribuir a armadura de flexão
uniformemente de face a face — não define, nem precisa definir, um momento sob
a própria seção de referência. O valor de dimensionamento continua vindo de
`momento_unitario()`, que usa só a face crítica e não é tocado por estes testes.

Invariantes exigidas do campo:
  - continuidade: nenhum salto entre nós vizinhos sob o pilar maior que o que
    já ocorre entre nós vizinhos fora dele;
  - limitação: sob o pilar, o valor fica entre o menor e o maior dos dois
    valores de face — o campo nunca sugere armadura crescente sob o pilar.
"""
import math

import pytest

from calc_core.sapata_isolada.acoes import (
    CasoCarga,
    Esforcos,
    Pilar,
    gerar_combinacoes,
)
from calc_core.sapata_isolada.geotecnia import Solo
from calc_core.sapata_isolada.grelha import resolver_grelha
from calc_core.sapata_isolada.materiais import Aco, Concreto
from calc_core.sapata_isolada.momentos import (
    campo_de_grelha,
    campo_momentos,
    plano_tensoes,
)
from calc_core.sapata_isolada.sapata import OpcoesProjeto, Sapata


# --------------------------------------------------------------------------- #
#  Cenário: pilar bem retangular (20x50) + Mx, My e vento — as duas faces do
#  pilar ficam com momentos claramente diferentes em ambas as direções.
# --------------------------------------------------------------------------- #
def _cenario():
    pilar = Pilar(ap=0.20, bp=0.50)
    solo = Solo(sigma_adm=250.0, gamma_solo=18.0, hf=1.5, phi=30.0)
    casos = [
        CasoCarga("G", Esforcos(N=600.0, Mx=15.0, My=8.0)),
        CasoCarga("Q", Esforcos(N=180.0, Mx=6.0), tipo="acidental"),
        CasoCarga("W", Esforcos(My=45.0, Hx=18.0), tipo="vento"),
    ]
    s = Sapata(pilar, solo, Concreto(30.0), Aco(500.0), gerar_combinacoes(casos),
               0.045, OpcoesProjeto(verificar_recalque=False))
    return s, s.dimensionar()


def _momento_balanco(esf, campo, p: float, fixo: float, eixo: str) -> float:
    """Reimplementação independente do balanço engastado em `p`, para conferir
    os valores de face sem passar pelo código sob teste."""
    N, Mx, My = esf
    sm, kx, ky = plano_tensoes(N, Mx, My, campo.a, campo.b)

    def sigma(xi, eta):
        return max(0.0, sm + kx * xi + ky * eta)

    dim = campo.a if eixo == "X" else campo.b
    borda = math.copysign(dim / 2.0, p if p != 0.0 else 1.0)
    L = abs(borda - p)
    if L <= 1e-9:
        return 0.0
    if eixo == "X":
        s0, s1 = sigma(p, fixo), sigma(borda, fixo)
    else:
        s0, s1 = sigma(fixo, p), sigma(fixo, borda)
    k = (s1 - s0) / L
    return s0 * L ** 2 / 2.0 + k * L ** 3 / 3.0


def _maiores_saltos(campo, valores, meia: float, ao_longo_de_x: bool):
    """(maior salto entre nós vizinhos DENTRO ou na borda da projeção do pilar,
    maior salto entre nós vizinhos fora dela), na direção do balanço.

    "Dentro ou na borda" = pelo menos um dos dois nós do par cai estritamente
    sob a projeção; assim o par que atravessa a face também é auditado, que é
    justamente onde o clamp antigo criava o degrau em `campo_de_grelha`.
    """
    xs, ys, dentro, fora = campo.x, campo.y, 0.0, 0.0
    if ao_longo_de_x:
        for j in range(len(ys)):
            for i in range(len(xs) - 1):
                d = abs(valores[j][i + 1] - valores[j][i])
                if min(abs(xs[i]), abs(xs[i + 1])) < meia - 1e-12:
                    dentro = max(dentro, d)
                else:
                    fora = max(fora, d)
    else:
        for i in range(len(xs)):
            for j in range(len(ys) - 1):
                d = abs(valores[j + 1][i] - valores[j][i])
                if min(abs(ys[j]), abs(ys[j + 1])) < meia - 1e-12:
                    dentro = max(dentro, d)
                else:
                    fora = max(fora, d)
    return dentro, fora


# --------------------------------------------------------------------------- #
#  1. Sem degrau sob o pilar
# --------------------------------------------------------------------------- #
def test_campo_momentos_sem_degrau_sob_o_pilar():
    """O maior salto entre nós vizinhos sob o pilar não pode ser maior que o
    que já se observa entre nós vizinhos fora dele.

    Com o bug, o cenário deste arquivo dava um salto de 28,04 kN·m/m em mx
    exatamente em x = 0 (de 103,74 para 131,78), contra 9,90 kN·m/m de maior
    salto fora do pilar — quase 3x. Em my o salto era de 8,77 contra 7,59.
    """
    s, res = _cenario()
    campo = campo_momentos(s, res, nx=61, ny=61)

    dentro_x, fora_x = _maiores_saltos(campo, campo.mx, campo.ap / 2.0, True)
    dentro_y, fora_y = _maiores_saltos(campo, campo.my, campo.bp / 2.0, False)

    # a malha sob o pilar é a mesma de fora: o salto lá não pode ser maior
    assert dentro_x <= fora_x, (
        f"degrau em mx sob o pilar: {dentro_x:.3f} > {fora_x:.3f} fora")
    assert dentro_y <= fora_y, (
        f"degrau em my sob o pilar: {dentro_y:.3f} > {fora_y:.3f} fora")
    # e o cenário precisa continuar sendo assimétrico, senão o teste é vazio
    assert fora_x > 1.0 and fora_y > 1.0


def test_campo_momentos_transversalmente_continuo_sob_o_pilar():
    """Na direção TRANSVERSAL ao balanço o campo também não pode ter degrau."""
    s, res = _cenario()
    campo = campo_momentos(s, res, nx=61, ny=61)
    for j in range(len(campo.y)):
        for i in range(len(campo.x) - 1):
            assert abs(campo.my[j][i + 1] - campo.my[j][i]) < 1.0
    for i in range(len(campo.x)):
        for j in range(len(campo.y) - 1):
            assert abs(campo.mx[j + 1][i] - campo.mx[j][i]) < 1.0


# --------------------------------------------------------------------------- #
#  2. Limitado pelos valores das duas faces
# --------------------------------------------------------------------------- #
def test_campo_sob_o_pilar_fica_entre_os_valores_das_duas_faces():
    """Invariante física: o campo não pode crescer sob o pilar. Qualquer ponto
    sob a projeção fica entre min e max dos momentos das duas faces."""
    s, res = _cenario()
    campo = campo_momentos(s, res, nx=61, ny=61)
    # os esforços de referência da combinação governante, para o cálculo manual
    esf = _esforcos_governantes(s, res)

    testados = 0
    for j, y in enumerate(campo.y):
        m_esq = _momento_balanco(esf, campo, -campo.ap / 2.0, y, "X")
        m_dir = _momento_balanco(esf, campo, +campo.ap / 2.0, y, "X")
        lo, hi = min(m_esq, m_dir), max(m_esq, m_dir)
        for i, x in enumerate(campo.x):
            if abs(x) >= campo.ap / 2.0:
                continue
            assert lo - 1e-6 <= campo.mx[j][i] <= hi + 1e-6, (
                f"mx({x:.4f},{y:.4f}) = {campo.mx[j][i]:.4f} fora de "
                f"[{lo:.4f}, {hi:.4f}]")
            testados += 1
    assert testados > 0, "nenhum nó caiu sob a projeção do pilar"

    testados = 0
    for i, x in enumerate(campo.x):
        m_inf = _momento_balanco(esf, campo, -campo.bp / 2.0, x, "Y")
        m_sup = _momento_balanco(esf, campo, +campo.bp / 2.0, x, "Y")
        lo, hi = min(m_inf, m_sup), max(m_inf, m_sup)
        for j, y in enumerate(campo.y):
            if abs(y) >= campo.bp / 2.0:
                continue
            assert lo - 1e-6 <= campo.my[j][i] <= hi + 1e-6, (
                f"my({x:.4f},{y:.4f}) = {campo.my[j][i]:.4f} fora de "
                f"[{lo:.4f}, {hi:.4f}]")
            testados += 1
    assert testados > 0


def _esforcos_governantes(s, res):
    """Reproduz a escolha da combinação feita por `campo_momentos`."""
    from calc_core.sapata_isolada.acoes import TipoCombinacao, filtrar
    from calc_core.sapata_isolada.momentos import momento_unitario
    a, b = res.a, res.b
    ap, bp = s.pilar.ap, s.pilar.bp

    def maior(c):
        e = c.esforcos
        mx = e.Mx + e.Hy * res.h
        my = e.My + e.Hx * res.h
        return max(momento_unitario(e.N, mx, my, a, b, ap, bp, "X") * b,
                   momento_unitario(e.N, mx, my, a, b, ap, bp, "Y") * a)

    comb = max(filtrar(s.combinacoes, TipoCombinacao.ELU), key=maior)
    e = comb.esforcos
    return e.N, e.Mx + e.Hy * res.h, e.My + e.Hx * res.h


# --------------------------------------------------------------------------- #
#  3. Continuidade exata na face e valor no eixo
# --------------------------------------------------------------------------- #
def test_valor_no_eixo_do_pilar_e_a_media_das_duas_faces():
    """Em pos = 0 a interpolação linear devolve exatamente a média das faces —
    e não o valor de uma delas, como fazia o clamp por sinal."""
    s, res = _cenario()
    # malha com nó exatamente em x = 0 e y = 0 (nx, ny ímpares)
    campo = campo_momentos(s, res, nx=61, ny=61)
    esf = _esforcos_governantes(s, res)
    i0 = min(range(len(campo.x)), key=lambda i: abs(campo.x[i]))
    j0 = min(range(len(campo.y)), key=lambda j: abs(campo.y[j]))
    assert abs(campo.x[i0]) < 1e-12 and abs(campo.y[j0]) < 1e-12

    y = campo.y[j0]
    media = 0.5 * (_momento_balanco(esf, campo, -campo.ap / 2.0, y, "X")
                   + _momento_balanco(esf, campo, +campo.ap / 2.0, y, "X"))
    assert campo.mx[j0][i0] == pytest.approx(media, rel=1e-9)

    x = campo.x[i0]
    media = 0.5 * (_momento_balanco(esf, campo, -campo.bp / 2.0, x, "Y")
                   + _momento_balanco(esf, campo, +campo.bp / 2.0, x, "Y"))
    assert campo.my[j0][i0] == pytest.approx(media, rel=1e-9)


def test_campo_bate_com_o_balanco_exatamente_na_face():
    """A interpolação coincide com a curva externa nos dois limites: uma malha
    cujos nós caem exatamente sobre ±ap/2 não pode mostrar salto ali."""
    s, res = _cenario()
    campo = campo_momentos(s, res, nx=61, ny=61)
    esf = _esforcos_governantes(s, res)
    for j, y in enumerate(campo.y[::7]):
        jj = j * 7
        for lado in (-1.0, 1.0):
            p = lado * campo.ap / 2.0
            # nó da malha mais próximo da face, já fora da projeção
            i = min((i for i, x in enumerate(campo.x)
                     if abs(x) >= campo.ap / 2.0 and x * lado > 0),
                    key=lambda i: abs(campo.x[i] - p))
            esperado = _momento_balanco(esf, campo, campo.x[i], y, "X")
            assert campo.mx[jj][i] == pytest.approx(esperado, rel=1e-9)


def test_grade_encaixa_as_faces_do_pilar():
    """A grade tem nós exatamente sobre ±ap/2 e ±bp/2.

    Sem esse encaixe, com a interpolação nenhum nó cai sobre a seção de
    referência e o pico lido do campo fica ~1,5 % abaixo do momento de
    dimensionamento — o cabeçalho dos desenhos passaria a mostrar
    'máx 138,9 · faixa integrada 284,8' contra 'M_d adotado 289,2'.
    """
    s, res = _cenario()
    campo = campo_momentos(s, res, nx=61, ny=61)
    for alvo in (-campo.ap / 2.0, campo.ap / 2.0):
        assert any(abs(x - alvo) < 1e-12 for x in campo.x), f"falta x = {alvo}"
    for alvo in (-campo.bp / 2.0, campo.bp / 2.0):
        assert any(abs(y - alvo) < 1e-12 for y in campo.y), f"falta y = {alvo}"
    # o encaixe não pode desordenar a grade
    assert all(u < v for u, v in zip(campo.x, campo.x[1:]))
    assert all(u < v for u, v in zip(campo.y, campo.y[1:]))
    # e o pico do campo tem de reproduzir o M_d que dimensionou a armadura
    assert campo.mx_max * campo.b == pytest.approx(campo.md_projeto_x, rel=1e-9)
    assert campo.my_max * campo.a == pytest.approx(campo.md_projeto_y, rel=1e-9)


def test_campo_de_tensoes_em_equilibrio():
    """∫σ dA = N e ∫σ·x dA = My, ∫σ·y dA = Mx sobre a grade (não parcializada).

    Guarda o encaixe das faces: mexer na grade não pode quebrar o equilíbrio
    do diagrama de tensões que alimenta o mesmo desenho.
    """
    s, res = _cenario()
    campo = campo_momentos(s, res, nx=61, ny=61)
    assert not campo.parcial, "cenário deixou de ser totalmente comprimido"
    N, Mx, My = _esforcos_governantes(s, res)

    def integra(f):
        tot = 0.0
        for j in range(len(campo.y) - 1):
            for i in range(len(campo.x) - 1):
                dx = campo.x[i + 1] - campo.x[i]
                dy = campo.y[j + 1] - campo.y[j]
                xm = (campo.x[i] + campo.x[i + 1]) / 2.0
                ym = (campo.y[j] + campo.y[j + 1]) / 2.0
                sm = (campo.sigma[j][i] + campo.sigma[j][i + 1]
                      + campo.sigma[j + 1][i] + campo.sigma[j + 1][i + 1]) / 4.0
                tot += f(sm, xm, ym) * dx * dy
        return tot

    assert integra(lambda sg, x, y: sg) == pytest.approx(N, rel=1e-9)
    assert integra(lambda sg, x, y: sg * x) == pytest.approx(My, rel=1e-3)
    assert integra(lambda sg, x, y: sg * y) == pytest.approx(Mx, rel=1e-3)


# --------------------------------------------------------------------------- #
#  4. Simetria: girar o problema 90° troca x por y e nada mais
# --------------------------------------------------------------------------- #
def test_girar_90_graus_troca_x_por_y():
    """Rodando o problema 90° (a<->b, ap<->bp, Mx<->My, e o campo transposto),
    mx e my devem apenas trocar de papel — inclusive sob o pilar."""
    pilar = Pilar(ap=0.20, bp=0.50)
    solo = Solo(sigma_adm=250.0, gamma_solo=18.0, hf=1.5, phi=30.0)
    casos = [CasoCarga("G", Esforcos(N=600.0, Mx=40.0, My=15.0))]
    s = Sapata(pilar, solo, Concreto(30.0), Aco(500.0), gerar_combinacoes(casos),
               0.045, OpcoesProjeto(verificar_recalque=False))
    r = s.dimensionar()
    c = campo_momentos(s, r, nx=41, ny=41)

    girado = Sapata(Pilar(ap=pilar.bp, bp=pilar.ap), solo, Concreto(30.0),
                    Aco(500.0),
                    gerar_combinacoes([CasoCarga("G", Esforcos(N=600.0,
                                                               Mx=15.0,
                                                               My=40.0))]),
                    0.045, OpcoesProjeto(verificar_recalque=False))
    rg = girado.dimensionar()
    cg = campo_momentos(girado, rg, nx=41, ny=41)

    assert (rg.a, rg.b) == (r.b, r.a)
    for j in range(41):
        for i in range(41):
            # my do girado, transposto, é o mx do original
            assert cg.my[i][j] == pytest.approx(c.mx[j][i], rel=1e-9, abs=1e-9)
            assert cg.mx[i][j] == pytest.approx(c.my[j][i], rel=1e-9, abs=1e-9)


def test_carga_centrada_da_plato_simetrico_sob_o_pilar():
    """Sem excentricidade as duas faces têm o mesmo momento: sob o pilar o
    campo é um platô plano, e o campo inteiro é par em x e em y."""
    pilar = Pilar(ap=0.20, bp=0.50)
    solo = Solo(sigma_adm=250.0, gamma_solo=18.0, hf=1.5, phi=30.0)
    s = Sapata(pilar, solo, Concreto(30.0), Aco(500.0),
               gerar_combinacoes([CasoCarga("G", Esforcos(N=600.0))]),
               0.045, OpcoesProjeto(verificar_recalque=False))
    r = s.dimensionar()
    c = campo_momentos(s, r, nx=41, ny=41)
    n = 41
    for j in range(n):
        for i in range(n):
            assert c.mx[j][i] == pytest.approx(c.mx[j][n - 1 - i], abs=1e-9)
            assert c.my[j][i] == pytest.approx(c.my[n - 1 - j][i], abs=1e-9)
    # platô sob o pilar
    j0 = n // 2
    sob = [c.mx[j0][i] for i, x in enumerate(c.x) if abs(x) < c.ap / 2.0]
    assert max(sob) - min(sob) < 1e-9


# --------------------------------------------------------------------------- #
#  5. campo_de_grelha: nó sob o pilar não pode receber o valor do lado oposto
# --------------------------------------------------------------------------- #
def _grelha_assimetrica():
    return resolver_grelha(N=800.0, Mx=120.0, My=80.0, a=2.20, b=2.00,
                           ap=0.20, bp=0.50, h=0.65, h0=0.25,
                           Ecs_MPa=27000.0, kv=20000.0, divisoes=14)


def test_campo_de_grelha_interpola_entre_os_dois_lados():
    """Cada nó sob a projeção fica entre os valores dos dois nós que a ladeiam,
    e o valor cresce monotonicamente do lado menor para o maior.

    Com o bug, no cenário abaixo os três nós sob o pilar em Y recebiam todos
    114,29 kN·m/m — o valor da face SUPERIOR — enquanto o nó imediatamente
    abaixo da projeção valia 63,31: um degrau de 50,98 na borda da projeção.
    """
    g = _grelha_assimetrica()
    campo = campo_de_grelha(g, 100.0, 100.0, "grelha assimétrica")
    xs, ys = campo.x, campo.y

    # --- direção X ---------------------------------------------------------
    meia = g.ap / 2.0
    k_neg = max((k for k, x in enumerate(xs) if x <= -meia), key=lambda k: xs[k])
    k_pos = min((k for k, x in enumerate(xs) if x >= meia), key=lambda k: xs[k])
    dentro = [i for i, x in enumerate(xs) if abs(x) < meia]
    assert dentro, "nenhum nó sob a projeção em X — cenário inútil"
    for j in range(len(ys)):
        lo = min(campo.mx[j][k_neg], campo.mx[j][k_pos])
        hi = max(campo.mx[j][k_neg], campo.mx[j][k_pos])
        for i in dentro:
            assert lo - 1e-9 <= campo.mx[j][i] <= hi + 1e-9
        # nós de fora não podem ter sido alterados
        assert campo.mx[j][k_neg] == pytest.approx(g.mx[j][k_neg])
        assert campo.mx[j][k_pos] == pytest.approx(g.mx[j][k_pos])

    # --- direção Y ---------------------------------------------------------
    meia = g.bp / 2.0
    j_neg = max((k for k, y in enumerate(ys) if y <= -meia), key=lambda k: ys[k])
    j_pos = min((k for k, y in enumerate(ys) if y >= meia), key=lambda k: ys[k])
    dentro = [j for j, y in enumerate(ys) if abs(y) < meia]
    assert len(dentro) >= 3, "cenário precisa de vários nós sob a projeção em Y"
    for i in range(len(xs)):
        lo = min(campo.my[j_neg][i], campo.my[j_pos][i])
        hi = max(campo.my[j_neg][i], campo.my[j_pos][i])
        anteriores = [campo.my[j][i] for j in dentro]
        for v in anteriores:
            assert lo - 1e-9 <= v <= hi + 1e-9
        # monotônico entre os dois lados (interpolação linear)
        crescente = campo.my[j_pos][i] >= campo.my[j_neg][i]
        seq = [campo.my[j_neg][i]] + anteriores + [campo.my[j_pos][i]]
        for u, v in zip(seq, seq[1:]):
            assert (v >= u - 1e-9) if crescente else (v <= u + 1e-9)


def test_campo_de_grelha_sem_degrau_na_borda_da_projecao():
    """O maior salto entre nós vizinhos dentro/na borda da projeção não pode
    superar o maior salto observado fora dela."""
    g = _grelha_assimetrica()
    campo = campo_de_grelha(g, 100.0, 100.0, "grelha assimétrica")
    dentro_x, fora_x = _maiores_saltos(campo, campo.mx, g.ap / 2.0, True)
    dentro_y, fora_y = _maiores_saltos(campo, campo.my, g.bp / 2.0, False)
    assert dentro_x <= fora_x, f"degrau em mx: {dentro_x:.2f} > {fora_x:.2f}"
    assert dentro_y <= fora_y, f"degrau em my: {dentro_y:.2f} > {fora_y:.2f}"


def test_campo_de_grelha_nao_inverte_lados_em_malha_par_ou_impar():
    """O bug do `min()` dependia da paridade/ordem da malha. Varrendo vários
    refinamentos, o nó sob o pilar mais próximo de um lado nunca pode ficar
    mais perto do valor do lado OPOSTO."""
    for divisoes in (6, 8, 10, 12, 14, 16, 18):
        g = resolver_grelha(N=800.0, Mx=150.0, My=0.0, a=2.20, b=2.00,
                            ap=0.20, bp=0.60, h=0.65, h0=0.25,
                            Ecs_MPa=27000.0, kv=20000.0, divisoes=divisoes)
        campo = campo_de_grelha(g, 100.0, 100.0, "x")
        ys, meia = campo.y, g.bp / 2.0
        dentro = [j for j, y in enumerate(ys) if abs(y) < meia]
        if len(dentro) < 2:
            continue
        j_neg = max((k for k, y in enumerate(ys) if y <= -meia),
                    key=lambda k: ys[k])
        j_pos = min((k for k, y in enumerate(ys) if y >= meia),
                    key=lambda k: ys[k])
        i0 = min(range(len(campo.x)), key=lambda i: abs(campo.x[i]))
        v_neg, v_pos = campo.my[j_neg][i0], campo.my[j_pos][i0]
        if abs(v_pos - v_neg) < 1e-6:
            continue
        j_baixo, j_alto = dentro[0], dentro[-1]
        # o nó mais baixo da projeção tem de estar mais perto do valor de baixo
        assert abs(campo.my[j_baixo][i0] - v_neg) <= \
            abs(campo.my[j_baixo][i0] - v_pos) + 1e-9, \
            f"divisoes={divisoes}: nó inferior puxado para a face oposta"
        assert abs(campo.my[j_alto][i0] - v_pos) <= \
            abs(campo.my[j_alto][i0] - v_neg) + 1e-9, \
            f"divisoes={divisoes}: nó superior puxado para a face oposta"
