"""eta_c no bloco retangular de tensões — correção de defeito do lado INSEGURO.

    Ref.: ABNT NBR 6118:2023, item 17.2.2, alínea e), p. impressa 121, e item
    8.2.10.1 (Figura 8.2 e parágrafo seguinte), p. impressa 26.
    [rule: NBR6118-8.2.10.1-diagrama-idealizado-do-concreto]  (ruleset.yaml
    v11, APROVADA)
    [req: REQ-ETA-C-01-eta-c-ausente-no-motor-amplo-lado-inseguro]

Texto conferido por leitura visual pelo a2-verificador (17.2.2-e):
    "a tensão constante atuante até a profundidade y pode ser tomada igual a:
    alpha_c eta_c f_cd, no caso da largura da seção, medida paralelamente à
    linha neutra, não diminuir a partir desta para a borda comprimida; 0,9
    alpha_c eta_c f_cd, no caso contrário; [...] eta_c conforme definido em
    8.2.10.1."
E em 8.2.10.1:
    "Para f_ck <= 40 MPa: eta_c = 1,0; para f_ck > 40 MPa: eta_c =
    (40/f_ck)^(1/3)."

POR QUE ESTE ARQUIVO EXISTE
---------------------------
`materiais.py::Concreto.alpha_c` implementava só alpha_c e eta_c NÃO EXISTIA
em `calc_core/`. Como `Concreto.__post_init__` aceita f_ck de 20 a 90 MPa, o
bloco comprimido ficava SUPERESTIMADO em 1/eta_c para f_ck > 40 MPa: +4,0 %
(C45), +7,7 % (C50), +14,5 % (C60), +31,0 % (C90). Dois efeitos, ambos do lado
inseguro:
  (1) armadura de flexão A MENOS (9,0 % no cenário C90/M_d = 2500 kN·m/m);
  (2) x/d SUBESTIMADO (0,486 contra 0,700 corretos no mesmo cenário), de modo
      que a verificação de dutilidade `x/d <= csi_limite` podia PASSAR quando
      devia REPROVAR.
Registro completo em kb/pendencias.md > V15. Os números de referência abaixo
são os medidos pelo a2 executando a própria fórmula do código.

MUTANTE CANÔNICO que estes testes têm de matar:

    A = self.concreto.alpha_c * fcd * bw * lam     # eta_c esquecido

Nenhum teste da suíte anterior o detectava, porque todos usavam f_ck <= 40 MPa
(regime em que eta_c = 1,0).
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
from calc_core.sapata_isolada.materiais import Aco, Concreto
from calc_core.sapata_isolada.sapata import OpcoesProjeto, Sapata


# --------------------------------------------------------------------------- #
#  Referência independente: reimplementa 17.2.2-e do zero, sem chamar o código
#  sob teste, para que o teste não "prove" o código com o próprio código.
#  `com_eta=False` reproduz DELIBERADAMENTE o comportamento defeituoso, usado
#  só para demonstrar a diferença.
# --------------------------------------------------------------------------- #
def _flexao_referencia(fck, Md, bw, d, com_eta=True, fyk=500.0):
    fcd = (fck / 1.4) * 1000.0                      # kPa
    fyd = (fyk / 1.15) * 1000.0                     # kPa
    alpha_c = 0.85 if fck <= 50.0 else 0.85 * (1.0 - (fck - 50.0) / 200.0)
    lam = 0.80 if fck <= 50.0 else 0.80 - (fck - 50.0) / 400.0
    eta_c = 1.0 if (fck <= 40.0 or not com_eta) else (40.0 / fck) ** (1.0 / 3.0)
    A = alpha_c * eta_c * fcd * bw * lam
    disc = (A * d) ** 2 - 2.0 * A * lam * Md
    if disc < 0:
        return math.inf, math.inf
    x = (A * d - math.sqrt(disc)) / (A * lam)
    z = d - lam * x / 2.0
    return Md / (z * fyd), x / d


def _sapata_para_secao(fck: float) -> Sapata:
    """Instância mínima só para exercitar `_armadura_flexao_simples`."""
    combs = gerar_combinacoes([CasoCarga("G", Esforcos(N=1000.0))])
    return Sapata(Pilar(0.30, 0.30), Solo(sigma_adm=300.0, hf=1.5),
                  Concreto(fck), Aco(500.0), combs, 0.045,
                  OpcoesProjeto(verificar_recalque=False))


# =========================================================================== #
#  1. eta_c — valores da fonte
# =========================================================================== #
@pytest.mark.parametrize("fck", [20.0, 25.0, 30.0, 35.0, 40.0])
def test_eta_c_vale_exatamente_um_ate_40_MPa(fck):
    """8.2.10.1: eta_c = 1,0 para f_ck <= 40 MPa. Igualdade EXATA, não aproximada."""
    assert Concreto(fck).eta_c == 1.0


@pytest.mark.parametrize("fck, esperado", [
    (45.0, 0.961500),      # (40/45)^(1/3)
    (50.0, 0.928318),      # ruleset.yaml, checagem_numerica: 0,9283
    (60.0, 0.873580),
    (90.0, 0.763143),      # ruleset.yaml, checagem_numerica: 0,7631
])
def test_eta_c_acima_de_40_MPa(fck, esperado):
    """8.2.10.1: eta_c = (40/f_ck)^(1/3) para f_ck > 40 MPa."""
    assert Concreto(fck).eta_c == pytest.approx(esperado, rel=1e-6)


def test_limiar_de_eta_c_e_40_MPa_e_nao_50():
    """Achado C2 do a2 (ruleset v11): eta_c muda em 40 MPa; alpha_c e lambda,
    em 50 MPa. Um código que só distinga "<= C50 / > C50" erra em silêncio na
    faixa 40 < f_ck <= 50 — é justamente onde este teste olha."""
    c45 = Concreto(45.0)
    assert c45.alpha_c == 0.85            # alpha_c ainda não reduziu
    assert c45.lambda_x == 0.80           # lambda ainda não reduziu
    assert c45.eta_c < 1.0                # mas eta_c JÁ reduziu
    assert c45.eta_c == pytest.approx(0.9615, rel=1e-4)


def test_eta_c_e_monotonicamente_decrescente_no_dominio_da_norma():
    valores = [Concreto(float(f)).eta_c for f in range(20, 91, 5)]
    assert all(a >= b for a, b in zip(valores, valores[1:]))
    assert valores[0] == 1.0
    assert valores[-1] == pytest.approx(0.763143, rel=1e-6)


def test_dominio_de_fck_permanece_o_da_norma():
    """A correção NÃO amplia nem restringe o campo de aplicação já vigente
    (20 a 90 MPa, `Concreto.__post_init__`). Fora dele continua sendo RECUSA."""
    for fora in (19.9, 90.1, 150.0):
        with pytest.raises(ValueError):
            Concreto(fora)


# =========================================================================== #
#  2. sigma_cd_bloco — a tensão do bloco, que é o que 17.2.2-e prescreve
# =========================================================================== #
def test_sigma_cd_bloco_e_alpha_c_vezes_eta_c_vezes_fcd():
    for fck in (20.0, 25.0, 40.0, 45.0, 50.0, 60.0, 90.0):
        c = Concreto(fck)
        assert c.sigma_cd_bloco == pytest.approx(c.alpha_c * c.eta_c * c.fcd,
                                                 rel=1e-12)


def test_sigma_cd_bloco_C25_bate_com_a_checagem_numerica_do_ruleset():
    """ruleset.yaml, NBR6118-8.2.10.1: C25 -> 0,85·1,0·17,857 = 15,18 MPa."""
    assert Concreto(25.0).sigma_cd_bloco == pytest.approx(15.18, abs=0.01)


@pytest.mark.parametrize("fck, superestimacao_pct", [
    (45.0, 4.0), (50.0, 7.7), (60.0, 14.5), (90.0, 31.0),
])
def test_magnitude_da_superestimacao_corrigida(fck, superestimacao_pct):
    """Confirma, contra o valor MEDIDO pelo a2, o quanto o bloco estava
    superestimado: alpha_c·f_cd / (alpha_c·eta_c·f_cd) - 1 = 1/eta_c - 1."""
    c = Concreto(fck)
    bloco_defeituoso = c.alpha_c * c.fcd
    excesso = 100.0 * (bloco_defeituoso / c.sigma_cd_bloco - 1.0)
    assert excesso == pytest.approx(superestimacao_pct, abs=0.05)


# =========================================================================== #
#  3. O cenário exato do defeito (C90, M_d = 2500 kN·m/m, d = 0,45 m)
#     Os números "antes" são os do a2; o teste exige os "depois".
# =========================================================================== #
def test_cenario_C90_Md2500_armadura_e_x_sobre_d():
    s = _sapata_para_secao(90.0)
    As, xd, dominio_ok = s._armadura_flexao_simples(Md=2500.0, bw=1.0, d=0.45)

    # DEPOIS (correto, com eta_c)
    assert As * 1e4 == pytest.approx(169.27, abs=0.05)     # cm²/m
    assert xd == pytest.approx(0.700, abs=0.001)

    # ANTES (defeituoso, sem eta_c) — tem de estar MORTO
    assert As * 1e4 != pytest.approx(153.98, abs=0.05)
    assert xd != pytest.approx(0.486, abs=0.001)

    # o déficit de armadura que o defeito produzia era de 9,0 %
    As_bug, xd_bug = _flexao_referencia(90.0, 2500.0, 1.0, 0.45, com_eta=False)
    assert 100.0 * (1.0 - As_bug / As) == pytest.approx(9.0, abs=0.1)
    assert xd_bug == pytest.approx(0.486, abs=0.001)

    # em C90 o limite é 0,35 (14.6.4.3): os dois reprovam, mas só o correto
    # informa a distância real do limite
    assert dominio_ok is False


def test_cenario_C90_pouco_armada_deficit_abaixo_de_um_por_cento():
    """O outro extremo medido pelo a2: M_d = 300 kN·m/m, d = 0,45 m — 15,60
    (defeituoso) contra 15,69 cm²/m (correto). Serve para fixar que o defeito
    é DISCRETO em seção pouco armada e explosivo perto do limite: quem só
    testasse seção pouco armada não o veria."""
    s = _sapata_para_secao(90.0)
    As, _, _ = s._armadura_flexao_simples(Md=300.0, bw=1.0, d=0.45)
    As_bug, _ = _flexao_referencia(90.0, 300.0, 1.0, 0.45, com_eta=False)
    assert As * 1e4 == pytest.approx(15.69, abs=0.01)
    assert As_bug * 1e4 == pytest.approx(15.60, abs=0.01)
    assert 100.0 * (1.0 - As_bug / As) < 1.0


def test_veredito_de_dutilidade_inverte_no_ponto_certo():
    """O efeito mais grave: veredito de dutilidade que PASSAVA e deve REPROVAR.

    C90, d = 0,45 m, b_w = 1,0 m, M_d = 1500 kN·m/m:
        sem eta_c (defeituoso): x/d = 0,267 <= 0,35  -> "aprovado"
        com eta_c (correto)   : x/d = 0,363  > 0,35  -> REPROVA
    """
    s = _sapata_para_secao(90.0)
    As, xd, dominio_ok = s._armadura_flexao_simples(Md=1500.0, bw=1.0, d=0.45)

    _, xd_bug = _flexao_referencia(90.0, 1500.0, 1.0, 0.45, com_eta=False)
    assert xd_bug == pytest.approx(0.267, abs=0.001)
    assert xd_bug <= s.concreto.csi_limite          # o defeito aprovava

    assert xd == pytest.approx(0.363, abs=0.001)
    assert xd > s.concreto.csi_limite               # a Norma reprova
    assert dominio_ok is False


# =========================================================================== #
#  4. Retrocompatibilidade: f_ck <= 40 MPa não pode mudar NADA
# =========================================================================== #
@pytest.mark.parametrize("fck", [20.0, 25.0, 30.0, 35.0, 40.0])
@pytest.mark.parametrize("Md, d", [(150.0, 0.35), (300.0, 0.45), (900.0, 0.60)])
def test_retrocompatibilidade_ate_40_MPa(fck, Md, d):
    """Com eta_c = 1,0 o resultado é IDÊNTICO ao da versão anterior — a
    referência aqui é justamente a fórmula sem eta_c."""
    s = _sapata_para_secao(fck)
    As, xd, _ = s._armadura_flexao_simples(Md=Md, bw=1.0, d=d)
    As_ref, xd_ref = _flexao_referencia(fck, Md, 1.0, d, com_eta=False)
    assert As == pytest.approx(As_ref, rel=1e-12)
    assert xd == pytest.approx(xd_ref, rel=1e-12)


# =========================================================================== #
#  5. Direção do efeito: acima de 40 MPa a correção só pode ser CONSERVADORA
# =========================================================================== #
@pytest.mark.parametrize("fck", [45.0, 50.0, 55.0, 60.0, 75.0, 90.0])
def test_correcao_e_sempre_do_lado_seguro_acima_de_40_MPa(fck):
    s = _sapata_para_secao(fck)
    for Md, d in ((300.0, 0.45), (1200.0, 0.45), (2500.0, 0.45)):
        As, xd, _ = s._armadura_flexao_simples(Md=Md, bw=1.0, d=d)
        As_bug, xd_bug = _flexao_referencia(fck, Md, 1.0, d, com_eta=False)
        assert As > As_bug          # mais armadura
        assert xd > xd_bug          # linha neutra mais funda, veredito mais duro


@pytest.mark.parametrize("fck", [25.0, 45.0, 60.0, 90.0])
@pytest.mark.parametrize("Md, bw, d", [(300.0, 1.0, 0.45), (2000.0, 2.5, 0.70)])
def test_secao_confere_contra_referencia_independente(fck, Md, bw, d):
    """A verificação direta: o código tem de reproduzir 17.2.2-e reimplementado
    do zero, para qualquer classe do domínio."""
    s = _sapata_para_secao(fck)
    As, xd, _ = s._armadura_flexao_simples(Md=Md, bw=bw, d=d)
    As_ref, xd_ref = _flexao_referencia(fck, Md, bw, d, com_eta=True)
    assert As == pytest.approx(As_ref, rel=1e-12)
    assert xd == pytest.approx(xd_ref, rel=1e-12)


# =========================================================================== #
#  6. Propagação: a correção tem de chegar ao dimensionamento completo, não
#     ficar presa na propriedade.
# =========================================================================== #
def _dimensionar_espionado(fck: float, N: float, sigma_adm: float,
                           monkeypatch, **op):
    """Dimensiona e devolve (resultado, chamadas), onde `chamadas` são as
    tuplas (M_d, b_w, d, As, x/d, dominio_ok) efetivamente processadas pela
    seção de flexão. O espião existe para que o teste use a MESMA faixa que o
    código usou, sem reimplementar a geometria da sapata aqui."""
    chamadas: list = []
    original = Sapata._armadura_flexao_simples

    def espiao(self, Md, bw, d):
        As, xd, ok = original(self, Md, bw, d)
        chamadas.append((Md, bw, d, As, xd, ok))
        return As, xd, ok

    monkeypatch.setattr(Sapata, "_armadura_flexao_simples", espiao)
    combs = gerar_combinacoes([CasoCarga("G", Esforcos(N=N))])
    s = Sapata(Pilar(0.40, 0.40), Solo(sigma_adm=sigma_adm, hf=1.5),
               Concreto(fck), Aco(500.0), combs, 0.045,
               OpcoesProjeto(verificar_recalque=False, **op))
    return s.dimensionar(), chamadas


@pytest.mark.parametrize("fck", [60.0, 90.0])
def test_propagacao_ao_dimensionamento_completo(fck, monkeypatch):
    """Roda o dimensionamento INTEIRO e confere cada avaliação da seção de
    flexão contra a referência independente COM eta_c. Se alguém reintroduzir
    `alpha_c * fcd` no consumidor (`sapata.py`), isto quebra mesmo que a
    propriedade `eta_c` continue certa em `materiais.py`."""
    _, chamadas = _dimensionar_espionado(fck, N=3000.0, sigma_adm=250.0,
                                         monkeypatch=monkeypatch,
                                         modelo_armadura_rigida="flexao")
    assert chamadas, "o dimensionamento não chegou à seção de flexão"
    houve_momento = False
    for Md, bw, d, As, xd, _ok in chamadas:
        if Md <= 0:
            continue
        houve_momento = True
        As_ref, xd_ref = _flexao_referencia(fck, Md, bw, d, com_eta=True)
        As_bug, xd_bug = _flexao_referencia(fck, Md, bw, d, com_eta=False)
        assert As == pytest.approx(As_ref, rel=1e-12)
        assert xd == pytest.approx(xd_ref, rel=1e-12)
        assert As > As_bug          # a correção chegou até aqui
        assert xd > xd_bug
    assert houve_momento


def test_propagacao_nao_muda_dimensionamento_em_C30(monkeypatch):
    """Retrocompatibilidade ponta a ponta: em C30 (eta_c = 1,0) toda a seção
    de flexão do dimensionamento completo continua idêntica à fórmula sem
    eta_c."""
    _, chamadas = _dimensionar_espionado(30.0, N=3000.0, sigma_adm=250.0,
                                         monkeypatch=monkeypatch,
                                         modelo_armadura_rigida="flexao")
    assert chamadas
    for Md, bw, d, As, xd, _ok in chamadas:
        if Md <= 0:
            continue
        As_ref, xd_ref = _flexao_referencia(30.0, Md, bw, d, com_eta=False)
        assert As == pytest.approx(As_ref, rel=1e-12)
        assert xd == pytest.approx(xd_ref, rel=1e-12)
