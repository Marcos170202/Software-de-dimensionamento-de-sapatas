"""Pilarete — fronteira do módulo, geometria, esbeltez e leis constitutivas.

Cobre REQ-PILARETE-01 (módulo novo e namespace), -02 (entradas explícitas),
-03 (13.2.3), -04 (M_1d,mín nas duas direções), -05 (pilar curto), -06
(eta_c/patamar/N_Rd0/j >= 28 dias), -09 (cobrimento próprio) e os testes de
propriedade (1) a (6) de REQ-PILARETE-13.

LACUNA DE VALIDAÇÃO DECLARADA, e ela é do requisito, não deste arquivo: NÃO
HÁ, em todo o acervo, um exemplo resolvido de pilarete — Bastos ("pilarete":
0 ocorrências) e Cintra/Aoki/Albiero tratam o pilar só como condição de
contorno da sapata. Os testes abaixo são de INVARIÂNCIA, FRONTEIRA, MUTAÇÃO e
FÍSICA; o único ponto com valor externo é o ell_b/phi = 37,7 contra a tabela
clássica de 38·phi (fixture ``test_ell_b_contra_tabela_classica``), e mesmo
esse vem de tabela consagrada, não de fonte do acervo.
"""
import math
import pathlib

import pytest

from calc_core.estrutural.dominio import RecusaForaDeDominio
from calc_core.estrutural.materiais_6118 import (
    eps_c2,
    eps_cu,
    eta_c,
    exigir_classe_normalizada,
    exigir_idade_28_dias,
    gamma_c_com_correcao_12_4_1,
    n_diagrama,
    sigma_c,
    sigma_s,
)
from calc_core.estrutural.pilarete.esbeltez import (
    ENGASTADO_BASE_LIVRE_TOPO,
    VINCULADO_DOIS_EXTREMOS,
    comprimento_equivalente,
    excentricidade_de_1a_ordem,
    indice_de_esbeltez,
    limite_lambda1,
    momento_minimo_1a_ordem,
    verificar_pilar_curto,
)
from calc_core.estrutural.pilarete.geometria import (
    cobrimento_nominal_minimo,
    raio_de_giracao,
    verificar_dimensoes_limites,
)
from calc_core.estrutural.pilarete.ligacao import ell_b_basico
from calc_core.estrutural.pilarete.secao import N_Rd0
from calc_core.sapata_isolada.materiais import Aco, Concreto

RAIZ = pathlib.Path(__file__).resolve().parents[1]
PACOTE = RAIZ / "calc_core" / "estrutural"


def _fontes_do_pacote() -> dict[str, str]:
    return {str(caminho.relative_to(RAIZ)): caminho.read_text(encoding="utf-8")
            for caminho in sorted(PACOTE.rglob("*.py"))}


# --- REQ-PILARETE-01: fronteira de dependência e namespace -----------------

def test_estrutural_so_importa_materiais_do_pacote_amplo():
    """`estrutural/` importa de `sapata_isolada` APENAS `materiais`.

    REQ-PILARETE-01: é PROIBIDO importar geotecnia, rigidez, recalques,
    bielas, grelha, solo_mef ou sapata. A fronteira tem de ser verificável por
    inspeção — é isso que separa o motor auditado do motor amplo.
    """
    proibidos = ("sapata_isolada.sapata", "sapata_isolada.rigidez",
                 "sapata_isolada.recalques", "sapata_isolada.bielas",
                 "sapata_isolada.grelha", "sapata_isolada.solo_mef",
                 "calc_core.geotecnico")
    for nome, fonte in _fontes_do_pacote().items():
        for proibido in proibidos:
            assert proibido not in fonte, f"{nome} importa {proibido}"
        for linha in fonte.splitlines():
            if "sapata_isolada" in linha and linha.strip().startswith(
                    ("from ", "import ")):
                assert "sapata_isolada.materiais" in linha, (
                    f"{nome}: {linha.strip()}")


def test_sapata_do_motor_amplo_nao_importa_estrutural():
    """A seta de dependência aponta para um lado só, nesta versão.

    REQ-PILARETE-01: é PROIBIDO que `sapata.py` passe a importar
    `estrutural/` — a integração pilarete<->sapata é rodada própria, com novo
    GATE.
    """
    fonte = (RAIZ / "calc_core" / "sapata_isolada" / "sapata.py").read_text(
        encoding="utf-8")
    assert "calc_core.estrutural" not in fonte


def _identificadores(fonte: str) -> set[str]:
    """Todos os NOMES do código — sem texto de docstring nem de mensagem.

    A distinção importa: os módulos CITAM ``tau_wd`` e ``alpha`` em prosa,
    justamente para declarar que são proibidos como SÍMBOLO. A proibição de
    REQ-PILARETE-01 é sobre o identificador, não sobre a palavra.
    """
    import ast

    nomes: set[str] = set()
    for no in ast.walk(ast.parse(fonte)):
        if isinstance(no, ast.Name):
            nomes.add(no.id)
        elif isinstance(no, ast.arg):
            nomes.add(no.arg)
        elif isinstance(no, ast.Attribute):
            nomes.add(no.attr)
        elif isinstance(no, ast.keyword) and no.arg:
            nomes.add(no.arg)
        elif isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            nomes.add(no.name)
        elif isinstance(no, ast.AnnAssign) and isinstance(no.target, ast.Name):
            nomes.add(no.target.id)
    return nomes


def test_namespace_sem_simbolos_proibidos():
    """Nenhum `alpha` nu, nenhum `tau_wd`, nenhum `alpha_v` sem o "2".

    REQ-PILARETE-01: são SEIS `alpha` distintos no ruleset e um `alpha = 1.5`
    escrito de memória no lugar de `alpha_interacao` produz envoltória mais
    cheia — erro do lado INSEGURO que passa por toda a checagem dimensional.
    `tau_wd` é símbolo da NBR 6118:2014 e não existe na edição de 2023.
    `theta` nu é proibido porque são DOIS ângulos na mesma expressão
    (`theta_biela`, da biela, e `alpha_estribo`, da armadura).
    """
    proibidos = {"alpha", "tau_wd", "alpha_v", "theta", "lambda_",
                 "M_d_tot_min", "a_l", "F_Sd_cor"}
    for nome, fonte in _fontes_do_pacote().items():
        colisoes = _identificadores(fonte) & proibidos
        assert not colisoes, f"{nome}: símbolo(s) proibido(s) {colisoes}"


def test_toda_funcao_publica_tem_docstring_rastreavel():
    """Docstring com item normativo e `[rule:]`/`[deriv:]` — CLAUDE.md, regra 3.

    É o que gera o memorial e permite a auditoria. Uma função pública sem
    âncora normativa não pode existir em `calc_core/`.
    """
    import ast

    for nome, fonte in _fontes_do_pacote().items():
        arvore = ast.parse(fonte)
        for no in ast.walk(arvore):
            if not isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if no.name.startswith("_"):
                continue
            texto = ast.get_docstring(no) or ""
            assert "NBR 6118" in texto, f"{nome}:{no.name} sem item normativo"
            assert ("[rule:" in texto or "[deriv:" in texto
                    or "[pratica:" in texto), f"{nome}:{no.name} sem âncora"


def test_recusa_atravessa_gerenciador_de_contexto_sem_traceback_cru():
    """A recusa tem de sobreviver a `@contextlib.contextmanager`.

    DEFEITO ENCONTRADO NESTA RODADA: `RecusaForaDeDominio` é um dataclass
    FROZEN que herda de `ValueError`, e `contextlib` atribui `__traceback__` à
    exceção em trânsito. Sem a liberação explícita desse atributo o usuário
    veria `FrozenInstanceError: cannot assign to field '__traceback__'` — um
    traceback cru no lugar da recusa legível, que é o oposto da doutrina deste
    módulo. Os CAMPOS continuam imutáveis.
    """
    import contextlib

    @contextlib.contextmanager
    def _passagem():
        yield

    with pytest.raises(RecusaForaDeDominio) as erro:
        with _passagem():
            verificar_dimensoes_limites(h_secao=0.19, b_secao=0.18)
    assert "360" in erro.value.mensagem

    with pytest.raises(Exception):    # os campos seguem congelados
        erro.value.parametro = "outro"


# --- REQ-PILARETE-02: entradas explícitas e guarda de UNIDADE --------------

def test_m1d_min_recusa_dimensao_em_centimetros():
    """A guarda de unidade que a análise dimensional NÃO pega.

    REQ-PILARETE-02: M_1d,mín = N_d·(0,015 + 0,03·h) não é homogênea — o 0,015
    carrega METROS. Passar h = 30 (cm) devolveria 0,915·N_d em vez de
    0,024·N_d: número plausível, sem erro dimensional detectável.
    """
    with pytest.raises(RecusaForaDeDominio) as erro:
        momento_minimo_1a_ordem(1000.0, 30.0)
    assert "METROS" in erro.value.mensagem


def test_vinculacao_e_enumeracao_fechada_sem_default():
    """Vinculação inexistente RECUSA; não há terceira opção nem inferência."""
    with pytest.raises(RecusaForaDeDominio):
        comprimento_equivalente(vinculacao="ENGASTADO_NOS_DOIS", ell=1.0)


def test_vinculado_dois_extremos_exige_ell_e_ell_0_declarados():
    """15.6 pressupõe elementos horizontais que o software não conhece.

    REQ-PILARETE-02-b: no ramo VINCULADO_DOIS_EXTREMOS, ell_e é ENTRADA
    NUMÉRICA e ell_0 tem de ser declarado; adivinhar ell_0 é proibido.
    """
    with pytest.raises(RecusaForaDeDominio):
        comprimento_equivalente(vinculacao=VINCULADO_DOIS_EXTREMOS, ell=3.0)
    assert comprimento_equivalente(
        vinculacao=VINCULADO_DOIS_EXTREMOS, ell=3.0, ell_e_declarado=2.8,
        ell_0=2.5, h_secao=0.30) == pytest.approx(2.8)
    with pytest.raises(RecusaForaDeDominio):
        comprimento_equivalente(vinculacao=VINCULADO_DOIS_EXTREMOS, ell=3.0,
                                ell_e_declarado=9.9, ell_0=2.5, h_secao=0.30)


def test_ell_e_do_balanco_sai_da_norma_e_nao_do_usuario():
    """15.8.2 ESCREVE ell_e = 2·ell no engastado-livre — não é entrada."""
    assert comprimento_equivalente(
        vinculacao=ENGASTADO_BASE_LIVRE_TOPO, ell=1.0) == pytest.approx(2.0)


# --- REQ-PILARETE-03 e -13(3): fronteiras duras de 13.2.3 ------------------

def test_b_menor_que_14_cm_recusa():
    """b = 13,9 cm: não existe gamma_n que autorize (13.2.3)."""
    with pytest.raises(RecusaForaDeDominio) as erro:
        verificar_dimensoes_limites(h_secao=0.40, b_secao=0.139)
    assert "14" in erro.value.mensagem


def test_area_menor_que_360_cm2_recusa_mesmo_com_b_acima_de_14():
    """19×18 cm: passa em b >= 14 e REPROVA no piso de área (342 cm²).

    É a fronteira que passa batido — o piso de 360 cm² vale "em qualquer
    caso", independente de b.
    """
    with pytest.raises(RecusaForaDeDominio) as erro:
        verificar_dimensoes_limites(h_secao=0.19, b_secao=0.18)
    assert "360" in erro.value.mensagem
    assert "342" in erro.value.mensagem


def test_b_de_14_cm_aceita_com_gamma_n_de_1_25():
    """gamma_n = 1,95 − 0,05·14 = 1,25, com b em CENTÍMETROS."""
    resultado = verificar_dimensoes_limites(h_secao=0.40, b_secao=0.14)
    assert resultado.gamma_n == pytest.approx(1.25)
    assert resultado.gamma_n_aplicado is True


def test_gamma_n_com_b_em_metros_daria_1_94_e_e_o_erro_que_a_guarda_evita():
    """Contra-prova do caso EMPIRICA `NBR6118-13.2.3-gamma-n`.

    Com b em METROS a expressão devolveria 1,9430 — número plausível e sem
    erro dimensional. O código converte para cm UMA vez, e o resultado é 1,25.
    """
    resultado = verificar_dimensoes_limites(h_secao=0.40, b_secao=0.14)
    assert resultado.gamma_n != pytest.approx(1.95 - 0.05 * 0.14)


def test_pilar_parede_recusa():
    """h_max > 5·b_min é pilar-parede (18.5), fora do escopo."""
    with pytest.raises(RecusaForaDeDominio) as erro:
        verificar_dimensoes_limites(h_secao=1.00, b_secao=0.19)
    assert "18.4.1" in erro.value.mensagem


def test_secao_corrente_nao_aplica_gamma_n():
    """b >= 19 cm: gamma_n = 1,00, sem majoração adicional."""
    resultado = verificar_dimensoes_limites(h_secao=0.30, b_secao=0.30)
    assert resultado.gamma_n == pytest.approx(1.0)
    assert resultado.gamma_n_aplicado is False
    assert resultado.area_cm2 == pytest.approx(900.0)


# --- REQ-PILARETE-04 e -13(11): cruzamento eixo <-> dimensão ---------------

def test_m1d_min_usa_h_no_plano_xx_e_b_no_plano_yy():
    """20×40 cm, N_d = 800 kN: 21,60 (usa h) e 16,80 kN·m (usa b).

    REQ-PILARETE-04: cada momento mínimo usa a dimensão MEDIDA NO PLANO em que
    ele flexiona. Em seção QUADRADA a troca é invisível — daí a seção 20×40.
    """
    assert momento_minimo_1a_ordem(800.0, 0.40) == pytest.approx(21.60)
    assert momento_minimo_1a_ordem(800.0, 0.20) == pytest.approx(16.80)


def test_nao_existe_caminho_de_compressao_centrada():
    """Com M = 0 o momento mínimo continua existindo nas duas direções.

    16.3 (p. 116): "não se aceita o dimensionamento de pilares para carga
    centrada". A ausência do caminho é ESTRUTURAL: não há função que aceite só
    N_d e devolva veredito.
    """
    assert momento_minimo_1a_ordem(1000.0, 0.30) == pytest.approx(24.0)
    e_1 = excentricidade_de_1a_ordem(0.0, 24.0, 1000.0)
    assert e_1 == pytest.approx(0.024)


# --- REQ-PILARETE-05 e -13(1)(2): esbeltez ---------------------------------

@pytest.mark.parametrize("N_d", [50.0, 1000.0, 9999.0])
def test_lambda1_vale_exatamente_35_sob_m1d_min_em_toda_a_faixa(N_d):
    """INVARIÂNCIA de REQ-PILARETE-13(1): 35 EXATO, de h = 0,14 a 2,00 m.

    Sob M_1d,mín apenas, e_1 = 0,015 + 0,03·h não depende de N_d (o N_d
    cancela) e o lambda_1 bruto fica entre 25,47 e 26,71 — sempre truncado em
    35. É teorema sobre o domínio, e mesmo assim continua PROIBIDO fixar 35 no
    código: basta o M real superar M_1d,mín para lambda_1 subir.
    """
    h = 0.14
    while h <= 2.0 + 1e-12:
        M_min = momento_minimo_1a_ordem(N_d, h)
        e_1 = excentricidade_de_1a_ordem(0.0, M_min, N_d)
        assert limite_lambda1(e_1, h) == pytest.approx(35.0)
        h += 0.02


def test_lambda1_sobe_acima_de_35_quando_o_momento_real_governa():
    """A prova de que o 35 NÃO pode ser fixado no código.

    Com M de 1ª ordem REAL bem maior que M_1d,mín — o que acontece sempre que
    M ou H entram como dado na base do pilar metálico — lambda_1 sai de 35.
    """
    e_1 = excentricidade_de_1a_ordem(300.0, 24.0, 1000.0)
    assert e_1 == pytest.approx(0.30)
    # (25 + 12,5·0,30/0,30)/1,0 = 37,5 > 35 -> o truncamento em 35 NÃO governa
    assert limite_lambda1(e_1, 0.30) == pytest.approx(37.5)
    assert limite_lambda1(e_1, 0.30) > 35.0


def test_fronteira_estrita_lambda_igual_a_lambda1_nao_dispensa():
    """REQ-PILARETE-13(2): a desigualdade é ESTRITA. Teste EM CIMA do valor.

    Escolhe-se ell tal que lambda = 35,0000 exatamente e verifica-se que o
    software RECUSA — 15.8.2 dispensa "quando o índice de esbeltez for MENOR
    QUE o valor-limite".
    """
    b = h = 0.30
    i = raio_de_giracao(h)
    ell = 35.0 * i / 2.0  # ell_e = 2·ell no balanço
    assert indice_de_esbeltez(2.0 * ell, h) == pytest.approx(35.0)
    with pytest.raises(RecusaForaDeDominio) as erro:
        verificar_pilar_curto(
            vinculacao=ENGASTADO_BASE_LIVRE_TOPO, ell=ell, h_secao=h,
            b_secao=b, N_d=1000.0, M_1d_x=0.0, M_1d_y=0.0,
            M_1d_min_xx=24.0, M_1d_min_yy=24.0, f_cd_MPa=25.0 / 1.4,
            secao_constante=True, armadura_constante=True)
    assert "ESTRITA" in erro.value.mensagem
    # e logo abaixo da fronteira segue normalmente
    resultado = verificar_pilar_curto(
        vinculacao=ENGASTADO_BASE_LIVRE_TOPO, ell=ell * 0.999, h_secao=h,
        b_secao=b, N_d=1000.0, M_1d_x=0.0, M_1d_y=0.0, M_1d_min_xx=24.0,
        M_1d_min_yy=24.0, f_cd_MPa=25.0 / 1.4, secao_constante=True,
        armadura_constante=True)
    assert resultado.lambda_maximo < 35.0


def test_campo_de_15_8_1_exige_secao_e_armadura_constantes():
    """Seção ou armadura variável ao longo do eixo sai do campo de 15.8."""
    for secao_ok, armadura_ok in ((False, True), (True, False), (None, True)):
        with pytest.raises(RecusaForaDeDominio):
            verificar_pilar_curto(
                vinculacao=ENGASTADO_BASE_LIVRE_TOPO, ell=1.0, h_secao=0.30,
                b_secao=0.30, N_d=1000.0, M_1d_x=0.0, M_1d_y=0.0,
                M_1d_min_xx=24.0, M_1d_min_yy=24.0, f_cd_MPa=25.0 / 1.4,
                secao_constante=secao_ok, armadura_constante=armadura_ok)


def test_lambda_cresce_com_ell():
    """FÍSICA de REQ-PILARETE-13(5): lambda é monótono crescente em ell."""
    valores = [indice_de_esbeltez(2.0 * ell, 0.30)
               for ell in (0.5, 0.8, 1.0, 1.4)]
    assert valores == sorted(valores)
    assert valores[0] < valores[-1]


def test_raio_de_giracao_e_h_sobre_raiz_de_12():
    """i = sqrt(I/A) = h/sqrt(12) — o b cancela (álgebra exata)."""
    assert raio_de_giracao(0.30) == pytest.approx(0.30 / math.sqrt(12.0))
    assert raio_de_giracao(0.30) == pytest.approx(
        math.sqrt((0.25 * 0.30 ** 3 / 12.0) / (0.25 * 0.30)))


# --- REQ-PILARETE-06 e -13(4)(5): leis constitutivas e N_Rd0 ---------------

def test_eta_c_muda_em_40_MPa_e_n_muda_em_C50():
    """DOIS limiares, não um — a correção de premissa de REQ-PILARETE-06-A."""
    assert eta_c(40.0) == pytest.approx(1.0)
    assert eta_c(45.0) == pytest.approx((40.0 / 45.0) ** (1.0 / 3.0))
    assert eta_c(50.0) == pytest.approx(0.92832, abs=1e-5)
    assert n_diagrama(50.0) == pytest.approx(2.0)
    assert n_diagrama(55.0) < 2.0
    assert eps_c2(50.0) == pytest.approx(2.0e-3)
    assert eps_cu(50.0) == pytest.approx(3.5e-3)
    assert eps_c2(90.0) > eps_c2(55.0) and eps_cu(90.0) < eps_cu(55.0)


def test_mutacao_remover_eta_c_quebra_em_C45_e_nao_em_C25():
    """MUTAÇÃO de REQ-PILARETE-13(4) — é assim que se prova o que o teste testa.

    Remover eta_c do cálculo de sigma_c tem de QUEBRAR um teste com
    f_ck = 45 MPa e NÃO pode quebrar nenhum com f_ck = 25 MPa.
    """
    c25 = Concreto(fck=25.0)
    c45 = Concreto(fck=45.0)
    sem_eta_c_25 = 0.85 * c25.fcd
    sem_eta_c_45 = 0.85 * c45.fcd
    assert sigma_c(2.0e-3, c25) == pytest.approx(sem_eta_c_25)
    assert sigma_c(2.0e-3, c45) != pytest.approx(sem_eta_c_45)
    assert sigma_c(2.0e-3, c45) == pytest.approx(sem_eta_c_45 * eta_c(45.0))


def test_patamar_do_diagrama_e_constante_de_eps_c2_a_eps_cu():
    """REQ-PILARETE-06-B: acima de eps_c2 a expressão da parábola DECRESCE.

    Avaliá-la fora do ramo curvo é defeito: com n = 2 e eps_c = 2·eps_c2 ela
    devolve ZERO, quando a tensão real é o pico constante.
    """
    concreto = Concreto(fck=25.0)
    pico = 0.85 * eta_c(25.0) * concreto.fcd
    assert sigma_c(2.0e-3, concreto) == pytest.approx(pico)
    assert sigma_c(3.0e-3, concreto) == pytest.approx(pico)
    assert sigma_c(3.5e-3, concreto) == pytest.approx(pico)
    # A expressão da parábola, avaliada FORA do ramo curvo, decresce: em
    # eps_c = 3,5 ‰ ela já vale 44 % do pico e em 2·eps_c2 = 4 ‰ devolve ZERO.
    def _parabola(eps):
        return pico * (1.0 - (1.0 - eps / 2.0e-3) ** 2)

    assert _parabola(3.5e-3) < pico
    assert _parabola(4.0e-3) == pytest.approx(0.0)
    assert sigma_c(3.5e-3, concreto) > _parabola(3.5e-3)


def test_classe_nao_normalizada_recusa_em_vez_de_interpolar():
    """Entre 50 e 55 MPa os dois critérios de classe da Norma DIVERGEM."""
    with pytest.raises(RecusaForaDeDominio):
        exigir_classe_normalizada(52.0)
    assert exigir_classe_normalizada(55.0) == 55.0


def test_idade_menor_que_28_dias_recusa():
    """REQ-PILARETE-06-D: j < 28 dias exige beta_1 de 12.3.3-b), fora do escopo."""
    with pytest.raises(RecusaForaDeDominio):
        exigir_idade_28_dias(False)
    with pytest.raises(RecusaForaDeDominio):
        exigir_idade_28_dias(None)
    assert exigir_idade_28_dias(True) is True


def test_correcao_12_4_1_e_perguntada_e_nao_assumida():
    """gamma_c × 1,1 é OBRIGATÓRIO quando previstas condições desfavoráveis."""
    with pytest.raises(RecusaForaDeDominio):
        gamma_c_com_correcao_12_4_1(1.4, None)
    assert gamma_c_com_correcao_12_4_1(1.4, False) == pytest.approx(1.4)
    assert gamma_c_com_correcao_12_4_1(1.4, True) == pytest.approx(1.54)


def test_sigma_s2_de_420_MPa_para_CA50_em_2_por_mil():
    """CONTRA-PROVA de REQ-PILARETE-13(6): E_s·eps_c2 = 420 MPa < f_yd."""
    aco = Aco(fyk=500.0)
    assert sigma_s(2.0e-3, aco) == pytest.approx(420.0)
    assert sigma_s(2.0e-3, aco) < aco.fyd


def test_sigma_s_recusa_acima_de_10_por_mil():
    """eps_su NÃO TEM VALOR na Norma: fora do domínio o software RECUSA."""
    with pytest.raises(RecusaForaDeDominio):
        sigma_s(-0.011, Aco(fyk=500.0))


def test_N_Rd0_monotono_em_As_e_em_fck():
    """FÍSICA de REQ-PILARETE-13(5)."""
    from calc_core.estrutural.pilarete.secao import (
        BarraLongitudinal, SecaoRetangular)
    from calc_core.sapata_isolada.materiais import area_barra

    def _secao(phi_mm, fck):
        area = area_barra(phi_mm)
        barras = tuple(BarraLongitudinal(pos_h=ph, pos_b=pb, area=area)
                       for ph in (0.058, 0.242) for pb in (0.058, 0.242))
        return SecaoRetangular(h_secao=0.30, b_secao=0.30, barras=barras,
                               concreto=Concreto(fck=fck), aco=Aco(fyk=500.0))

    assert N_Rd0(_secao(20.0, 25.0)) > N_Rd0(_secao(16.0, 25.0))
    assert N_Rd0(_secao(16.0, 30.0)) > N_Rd0(_secao(16.0, 25.0))


# --- REQ-PILARETE-09: cobrimento PRÓPRIO do pilarete -----------------------

def test_cobrimento_do_pilarete_tem_piso_de_45_mm():
    """Nota (d) da Tabela 7.2: piso ABSOLUTO, independente da classe."""
    assert cobrimento_nominal_minimo(classe_de_agressividade="I",
                                     phi_longitudinal_mm=16.0,
                                     d_agregado_mm=19.0) == pytest.approx(45.0)
    assert cobrimento_nominal_minimo(classe_de_agressividade="II",
                                     phi_longitudinal_mm=16.0,
                                     d_agregado_mm=19.0) == pytest.approx(45.0)


def test_cobrimento_em_CAA_IV_e_governado_pela_tabela_e_nao_pela_nota():
    """Os 45 mm são PISO, não TETO: em CAA IV a linha "Viga/pilar" dá 50 mm."""
    assert cobrimento_nominal_minimo(classe_de_agressividade="IV",
                                     phi_longitudinal_mm=16.0,
                                     d_agregado_mm=19.0) == pytest.approx(50.0)


def test_cobrimento_governado_pela_bitola_e_pelo_agregado():
    """c_nom >= phi e c_nom >= d_agregado/1,2 também entram no máximo."""
    assert cobrimento_nominal_minimo(classe_de_agressividade="I",
                                     phi_longitudinal_mm=60.0,
                                     d_agregado_mm=19.0) == pytest.approx(60.0)
    assert cobrimento_nominal_minimo(classe_de_agressividade="I",
                                     phi_longitudinal_mm=16.0,
                                     d_agregado_mm=76.0) == pytest.approx(
                                         76.0 / 1.2)


# --- REQ-PILARETE-13(6): a única contra-prova externa disponível -----------

def test_ell_b_contra_tabela_classica():
    """ell_b/phi = 37,7 para C25/CA-50, boa aderência, sem gancho.

    CONTRA-PROVA PARCIAL, com a origem declarada: 38·phi é valor de TABELA
    CONSAGRADA, não fonte do acervo. É o único ponto desta feature com
    conferência numérica externa.
    """
    ell_b = ell_b_basico(concreto=Concreto(fck=25.0), aco=Aco(fyk=500.0),
                         phi_mm=16.0, boa_aderencia=True)
    assert ell_b / 0.016 == pytest.approx(37.7, abs=0.1)


def test_ell_b_cresce_com_phi_e_decresce_com_fck():
    """FÍSICA de REQ-PILARETE-13(5), aplicada à ancoragem."""
    def _ell_b(phi, fck):
        return ell_b_basico(concreto=Concreto(fck=fck), aco=Aco(fyk=500.0),
                            phi_mm=phi, boa_aderencia=True)

    assert _ell_b(20.0, 25.0) > _ell_b(16.0, 25.0)
    assert _ell_b(16.0, 40.0) < _ell_b(16.0, 25.0)
