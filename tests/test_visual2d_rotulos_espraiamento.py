"""`visual2d.PerfilCortes` — helpers puros e caminho de desenho do corte de
espraiamento por camada (REQ-UI-07).

Contexto (GATE 2, rodada 3, retomada)
--------------------------------------
A rodada 2 reprovou por um único eixo (E5 = 3,0): o caminho de desenho tinha
0 % de cobertura e os 10 mutantes documentados em
`relatorios/revisao_codigo.json` (`mutation_testing_detalhe.sobreviventes`)
sobreviviam à suíte inteira — inclusive o que faz o rótulo do croqui voltar
a ser o símbolo proibido "L" (o próprio defeito que reprovou a rodada 1).

A sessão que fez a rodada 3 extraiu os laços de `desenhar()`/`_espraiamento`
em métodos estáticos PUROS (`_eixo_valor`, `_meia_com_tronco`, `_clampx`,
`_pontos_visiveis`, `_rotulos_de_interface`) exatamente para que estes
mutantes pudessem morrer sem Tk/Xvfb. Este arquivo testa esses helpers
diretamente e, para os dois mutantes que atacam o CALL SITE dentro de
`desenhar()`/`_espraiamento` (M5 e MI) em vez de uma função pura, usa um
canvas de mentira mínimo que grava os itens criados.

Tabela mutante → teste, para conferência (ver também o corpo do relatório
final da sessão):

    MC  test_rotulos_nunca_usam_simbolo_proibido_l_ou_b_maiusculo
    MA  test_delta_sigma_do_rotulo_vem_do_ponto_nao_da_camada
    MB  test_largura_indefinida_nunca_vira_numero_no_rotulo
    MI  test_espraiamento_nao_desenha_tronco_quando_largura_indefinida
    MF  test_pontos_visiveis_tem_um_a_mais_que_camadas_visiveis
    M4  test_eixo_valor_mapeia_direcao_para_dimensao
        test_rotulos_usam_apenas_o_eixo_pedido
    M5  test_desenhar_usa_fonte_espraiamento_do_estado_nao_boussinesq_fixo
    MD  test_meia_com_tronco_amplia_para_a_maior_largura_do_tronco
    ME  test_clampx_recorta_ao_intervalo_do_corte
    MH  test_medir_faixa_aviso_soma_a_altura_medida_nao_uma_constante
"""
from __future__ import annotations

import re

from calc_core.sapata_isolada.geotecnia import (
    AVISO_MEIO_HOMOGENEO,
    AVISO_NAO_NORMATIVO,
    FONTE_2V1H,
    FONTE_BOUSSINESQ,
    ROTULO_FONTE,
    CamadaPropagacao,
    PontoPropagacao,
    PropagacaoTensoes,
)
from calc_core.sapata_isolada.visual2d import PerfilCortes


# =========================================================================== #
#  Construtores mínimos — só os campos que cada teste precisa variar
# =========================================================================== #
def _ponto(z: float, delta_sigma: float, la, lb) -> PontoPropagacao:
    return PontoPropagacao(
        z=z, profundidade=1.5 + z, delta_sigma=delta_sigma,
        largura_equivalente_a=la, largura_equivalente_b=lb,
        rotulo=f"z={z}", fonte=FONTE_BOUSSINESQ)


def _camada(indice: int, z_topo: float, z_base: float,
           medio: float = 0.0) -> CamadaPropagacao:
    return CamadaPropagacao(
        indice=indice, nome=f"camada {indice}", tipo="granular",
        z_topo=z_topo, z_base=z_base, espessura=z_base - z_topo,
        delta_sigma_topo=medio, delta_sigma_base=medio,
        delta_sigma_medio=medio, fonte=FONTE_BOUSSINESQ)


def _prop(pontos: tuple, camadas: tuple, fonte: str = FONTE_BOUSSINESQ,
         avisos: tuple = (AVISO_NAO_NORMATIVO, AVISO_MEIO_HOMOGENEO)
         ) -> PropagacaoTensoes:
    return PropagacaoTensoes(
        fonte=fonte, rotulo_metodo=ROTULO_FONTE[fonte],
        q_aplicada=150.0, sobrecarga_na_base=27.0, q_liquida=123.0,
        a=2.2, b=2.2, z_base_sapata=1.5,
        z_max=(pontos[-1].z if pontos else 0.0),
        pontos=pontos, camadas=camadas, avisos=avisos)


# =========================================================================== #
#  Canvas de mentira — só para M5 (chamada dentro de `desenhar()`) e MI
#  (branch de `_espraiamento` que decide NÃO desenhar tronco algum)
# =========================================================================== #
class _CanvasGravador:
    """Grava cada item criado (tipo, args, kwargs) — não faz nenhum desenho
    de verdade, não precisa de Tk/Xvfb. `bbox()` devolve uma caixa fixa
    plausível: nenhum teste aqui depende de coordenada de pixel exata, só de
    QUAIS itens (e com que texto) `desenhar()`/`_espraiamento()` produziram.
    """

    def __init__(self, w: float = 900.0, h: float = 620.0) -> None:
        self._w, self._h = w, h
        self.itens: list[tuple[str, tuple, dict]] = []
        self._id = 0

    def bind(self, *_a, **_k) -> None:
        pass

    def winfo_width(self) -> float:
        return self._w

    def winfo_height(self) -> float:
        return self._h

    def delete(self, *_a) -> None:
        self.itens.clear()

    def _novo(self, tipo: str, args: tuple, kwargs: dict) -> int:
        self._id += 1
        self.itens.append((tipo, args, kwargs))
        return self._id

    def create_text(self, *a, **k):
        return self._novo("text", a, k)

    def create_rectangle(self, *a, **k):
        return self._novo("rectangle", a, k)

    def create_line(self, *a, **k):
        return self._novo("line", a, k)

    def create_polygon(self, *a, **k):
        return self._novo("polygon", a, k)

    def create_oval(self, *a, **k):
        return self._novo("oval", a, k)

    def bbox(self, _item):
        return (0.0, 0.0, 220.0, 14.0)

    # -------------------------------------------------------------- consultas
    def textos(self) -> list[str]:
        return [k.get("text", "") for tipo, _a, k in self.itens if tipo == "text"]

    def contagem(self, tipo: str) -> int:
        return sum(1 for t, _a, _k in self.itens if t == tipo)


class _CanvasMedidor:
    """Canvas de mentira cujo `bbox()` devolve uma altura FIXA e CONHECIDA
    (20 px) por item de texto — usado só por `_medir_faixa_aviso` (MH), para
    travar a ARITMÉTICA (soma das alturas medidas) contra o número mágico
    antigo (`FAIXA_AVISO_ESPRAIAMENTO = 84.0`, a6 achado 7)."""

    ALTURA_LINHA = 20.0

    def __init__(self) -> None:
        self._id = 0

    def bind(self, *_a, **_k) -> None:
        pass

    def create_text(self, *_a, **_k) -> int:
        self._id += 1
        return self._id

    def bbox(self, _item):
        return (0.0, 0.0, 200.0, self.ALTURA_LINHA)

    def delete(self, _item) -> None:
        pass


# =========================================================================== #
#  M4 — `_eixo_valor`: fonte única de "a"/"b" por direção
# =========================================================================== #
def test_eixo_valor_mapeia_direcao_para_dimensao():
    assert PerfilCortes._eixo_valor("X") == "a"
    assert PerfilCortes._eixo_valor("Y") == "b"


def test_rotulos_usam_apenas_o_eixo_pedido():
    """`_rotulos_de_interface` com `eixo_val="a"` só produz "a_eq" e nunca
    "b_eq" — e vice-versa. Mata o mesmo mutante M4 pelo lado do CONSUMIDOR
    do valor, não só da tradução direção→eixo."""
    pontos = (_ponto(z=0.0, delta_sigma=100.0, la=2.2, lb=3.1),
             _ponto(z=1.0, delta_sigma=80.0, la=2.6, lb=3.6))
    rot_a = PerfilCortes._rotulos_de_interface(None, "a", pontos)
    rot_b = PerfilCortes._rotulos_de_interface(None, "b", pontos)

    assert all("a_eq" in r[3] and "b_eq" not in r[3] for r in rot_a)
    assert all("b_eq" in r[3] and "a_eq" not in r[3] for r in rot_b)
    assert rot_a[0][3] == "a_eq = 2.20 m"
    assert rot_b[0][3] == "b_eq = 3.10 m"


# =========================================================================== #
#  MC — nenhum rótulo usa "L"/"L1/L2/L3"/"B_eq"; todos usam "{eixo}_eq = "
# =========================================================================== #
_PROIBIDO = re.compile(r"\bL\s*=|L[123]|B_eq")
_PERMITIDO = re.compile(r"^[ab]_eq = ")


def test_rotulos_nunca_usam_simbolo_proibido_l_ou_b_maiusculo():
    pontos = (_ponto(z=0.0, delta_sigma=100.0, la=2.2, lb=None),
             _ponto(z=1.0, delta_sigma=50.0, la=None, lb=3.0),
             _ponto(z=2.0, delta_sigma=10.0, la=4.5, lb=4.9))
    for eixo in ("a", "b"):
        for _z, _ds, texto_q, texto_l in PerfilCortes._rotulos_de_interface(
                None, eixo, pontos):
            assert not _PROIBIDO.search(texto_l), texto_l
            assert _PERMITIDO.match(texto_l), texto_l
            assert not _PROIBIDO.search(texto_q), texto_q


# =========================================================================== #
#  MA — o Δσ do rótulo é `pt.delta_sigma` (grandeza de PONTO), nunca
#  `cam.delta_sigma_medio` (grandeza de CAMADA, outro universo de índice)
# =========================================================================== #
def test_delta_sigma_do_rotulo_vem_do_ponto_nao_da_camada():
    pontos = (_ponto(z=0.0, delta_sigma=111.0, la=2.2, lb=2.2),
             _ponto(z=1.0, delta_sigma=77.0, la=2.6, lb=2.6),
             _ponto(z=2.0, delta_sigma=33.0, la=3.0, lb=3.0))
    # delta_sigma_medio das camadas DELIBERADAMENTE diferente de qualquer
    # pt.delta_sigma, para o teste não passar por coincidência numérica.
    camadas = (_camada(0, 0.0, 1.0, medio=999.0),
              _camada(1, 1.0, 2.0, medio=888.0))
    prop = _prop(pontos, camadas)

    rotulos = PerfilCortes._rotulos_de_interface(prop, "a", pontos)
    assert len(rotulos) == len(pontos)
    for (z, delta_sigma, texto_q, _texto_l), pt in zip(rotulos, pontos):
        assert z == pt.z
        assert delta_sigma == pt.delta_sigma
        assert delta_sigma not in (999.0, 888.0)
        assert texto_q == f"q = {pt.delta_sigma:.1f} kPa"


# =========================================================================== #
#  MB — largura indefinida (None) NUNCA vira número no rótulo
# =========================================================================== #
def test_largura_indefinida_nunca_vira_numero_no_rotulo():
    pontos = (_ponto(z=0.0, delta_sigma=100.0, la=None, lb=None),
             _ponto(z=1.0, delta_sigma=50.0, la=None, lb=None))
    for eixo in ("a", "b"):
        for _z, _ds, _texto_q, texto_l in PerfilCortes._rotulos_de_interface(
                None, eixo, pontos):
            assert texto_l == f"{eixo}_eq = —"
            assert not any(ch.isdigit() for ch in texto_l)


# =========================================================================== #
#  MI — a decisão de NÃO desenhar tronco algum quando a largura vem
#  indefinida em TODOS os pontos é tomada em `_espraiamento`, antes do laço
#  de polígonos — testado aqui contra o MÉTODO de verdade (não só a função
#  pura `_sem_largura_definida`, já coberta em
#  test_perfil_cortes_espraiamento.py::test_sem_largura_definida_quando_
#  q_liquido_e_zero)
# =========================================================================== #
def test_espraiamento_nao_desenha_tronco_quando_largura_indefinida():
    pontos = (_ponto(z=0.0, delta_sigma=0.0, la=None, lb=None),
             _ponto(z=1.0, delta_sigma=0.0, la=None, lb=None))
    camadas = (_camada(0, 0.0, 1.0, medio=0.0),)
    aviso_texto = ("Pressão líquida nula: sem largura equivalente a "
                  "reportar.")
    prop = _prop(pontos, camadas,
                avisos=(AVISO_NAO_NORMATIVO, AVISO_MEIO_HOMOGENEO,
                       aviso_texto))

    canvas = _CanvasGravador()
    pc = PerfilCortes(canvas)
    pc.direcao = "X"

    def px(x):
        return 400.0 + x * 10.0

    def ym(z):
        return 100.0 + z * 40.0

    pc._espraiamento({}, px, ym, 2.2, 1.5, 560.0, 900.0, 110.0,
                     prop, None, 240.0, 880.0)

    assert canvas.contagem("polygon") == 0
    texto_junto = " ".join(canvas.textos()).lower()
    assert "líquida nula" in texto_junto or "liquida nula" in texto_junto


# =========================================================================== #
#  MF — `_pontos_visiveis` devolve n_camadas_visiveis + 1 pontos
# =========================================================================== #
def test_pontos_visiveis_tem_um_a_mais_que_camadas_visiveis():
    camadas = tuple(_camada(i, float(i), float(i + 1)) for i in range(4))
    pontos = tuple(_ponto(z=float(i), delta_sigma=100.0 - 10 * i,
                          la=2.0 + 0.1 * i, lb=2.0 + 0.1 * i)
                   for i in range(5))
    prop = _prop(pontos, camadas)

    def py(z):
        return z   # identidade — evita depender de escala real de pixel

    for base, n_camadas_visiveis in ((1.5, 2), (2.5, 3), (3.5, 4)):
        visiveis = PerfilCortes._pontos_visiveis(prop, py, base)
        assert len(visiveis) == n_camadas_visiveis + 1


# =========================================================================== #
#  M5 — `desenhar()` usa `self.fonte_espraiamento` de verdade, não
#  `FONTE_BOUSSINESQ` fixo — o seletor REQ-UI-04 não pode parar de funcionar
#  em silêncio. Precisa do MÉTODO de verdade (não só `_propagacao_atual`
#  isolado, já coberto em test_propagacao_atual_usa_o_parametro_fonte_nao_
#  o_campo_de_instancia) porque o mutante ataca o CALL SITE dentro de
#  `desenhar()`.
# =========================================================================== #
def test_desenhar_usa_fonte_espraiamento_do_estado_nao_boussinesq_fixo():
    from tests.test_perfil_cortes_espraiamento import _modelo

    m = _modelo()
    canvas = _CanvasGravador()
    pc = PerfilCortes(canvas)
    pc.mostrar_bulbo = False
    pc.mostrar_espraiamento = True
    pc.fonte_espraiamento = FONTE_2V1H

    pc.definir_modelo(m)   # dispara desenhar()

    textos = canvas.textos()
    assert any(ROTULO_FONTE[FONTE_2V1H] in t for t in textos)
    assert not any(ROTULO_FONTE[FONTE_BOUSSINESQ] in t for t in textos)


# =========================================================================== #
#  MD — `_meia_com_tronco`: amplia a semilargura para caber a MAIOR largura
#  equivalente do tronco; sem propagação, devolve `meia` inalterado
# =========================================================================== #
def test_meia_com_tronco_amplia_para_a_maior_largura_do_tronco():
    pontos = (_ponto(z=0.0, delta_sigma=100.0, la=2.2, lb=2.2),
             _ponto(z=1.0, delta_sigma=50.0, la=10.0, lb=8.0))
    camadas = (_camada(0, 0.0, 1.0),)
    prop = _prop(pontos, camadas)

    meia_original = 1.375   # bem menor que 10.0 / 2
    meia = PerfilCortes._meia_com_tronco(meia_original, prop, "a")
    assert meia >= 10.0 / 2.0
    assert meia > meia_original

    # eixo "b": maior largura é 8.0 -> semilargura mínima 4.0, ainda maior
    # que meia_original
    meia_b = PerfilCortes._meia_com_tronco(meia_original, prop, "b")
    assert meia_b >= 8.0 / 2.0


def test_meia_com_tronco_sem_propagacao_devolve_meia_inalterado():
    assert PerfilCortes._meia_com_tronco(1.375, None, "a") == 1.375


# =========================================================================== #
#  ME — `_clampx`: recorta ao intervalo [corte_x0, corte_x1]
# =========================================================================== #
def test_clampx_recorta_ao_intervalo_do_corte():
    assert PerfilCortes._clampx(50.0, 100.0, 300.0) == 100.0
    assert PerfilCortes._clampx(500.0, 100.0, 300.0) == 300.0
    assert PerfilCortes._clampx(200.0, 100.0, 300.0) == 200.0


# =========================================================================== #
#  MH — `_medir_faixa_aviso` soma a altura MEDIDA (via `bbox()`), não uma
#  constante mágica
# =========================================================================== #
def test_medir_faixa_aviso_soma_a_altura_medida_nao_uma_constante():
    pontos = (_ponto(z=0.0, delta_sigma=100.0, la=2.2, lb=2.2),)
    camadas = (_camada(0, 0.0, 1.0),)
    prop = _prop(pontos, camadas, fonte=FONTE_BOUSSINESQ)

    canvas = _CanvasMedidor()
    pc = PerfilCortes(canvas)
    pc.fonte_espraiamento = FONTE_BOUSSINESQ   # 4 linhas fixas nesse caso:
    # AVISO_NAO_NORMATIVO, AVISO_MEIO_HOMOGENEO, rótulo do método (+q_líq),
    # ressalva ilustrativa do Boussinesq — as quatro sempre presentes,
    # independente de `prop.avisos`.
    n_linhas = len(pc._linhas_banner_espraiamento(prop))
    assert n_linhas == 4

    esperado = n_linhas * (_CanvasMedidor.ALTURA_LINHA + 3.0) + 4.0
    resultado = pc._medir_faixa_aviso(900.0, prop, None)

    assert resultado == esperado
    assert resultado != 84.0   # o número mágico antigo (a6, achado 7)
