"""`ResultadoSapata.q_servico` — a pressão TOTAL de serviço na base.

Contexto (GATE 2, rodada 1, defeito de `visual2d.py:616`/`:620`)
----------------------------------------------------------------
A pressão de serviço q = (N_qp + peso próprio)/(a·b) era variável local de
`Sapata._analisar_recalques` e morria lá dentro. Quem precisava dela a jusante
— a propagação de tensões em profundidade, que recebe a pressão TOTAL e
calcula a líquida internamente (REQ-PROP-01) — só conseguia chegar a ela
somando `res.recalques.q_liquido + solo.sobrecarga_no_nivel_da_base()`, o que
tem dois modos de falha REAIS, cada um com um teste abaixo:

  (1) `res.recalques` é None sempre que `verificar_recalque=False` ou não há
      perfil, e aí não há de onde reconstituir — mesmo com o perfil geotécnico
      presente e a pressão perfeitamente conhecida. Era o diagnóstico falso
      "Sem perfil/solo suficiente" na tela do corte de espraiamento;
  (2) `AnaliseRecalque.q_liquido` aplica `max(0; ...)`. Quando q_serviço <
      sobrecarga o valor satura em zero e a soma NÃO devolve o q_serviço de
      partida: devolve a sobrecarga. A reconstituição não é uma inversa.

Estes testes fixam que o campo existe, que vale exatamente o que alimentou
`AnaliseRecalque` (nenhum valor mudou ao ser exposto) e que ele não depende da
opção de recalque.

Sem citação normativa: a divisão N/A e a escolha da combinação de serviço não
são prescritas pela NBR 6122:2022 (a combinação é da NBR 8681). O que é
normativo é σ ≤ σ_adm, verificado em `Sapata._estado_tensao`, e não muda aqui.
"""
import pytest

from calc_core.sapata_isolada.acoes import (
    CasoCarga,
    Esforcos,
    Pilar,
    gerar_combinacoes,
)
from calc_core.sapata_isolada.geotecnia import (
    Camada,
    PerfilGeotecnico,
    Solo,
    TipoSubstrato,
    tensao_liquida_na_base,
)
from calc_core.sapata_isolada.materiais import Aco, Concreto
from calc_core.sapata_isolada.recalques import AnaliseRecalque
from calc_core.sapata_isolada.sapata import OpcoesProjeto, Sapata


# --------------------------------------------------------------------- fixtures
def _perfil() -> PerfilGeotecnico:
    """Mesmo perfil de `test_propagacao_tensoes.py`: 4 camadas, 12,0 m."""
    return PerfilGeotecnico(
        camadas=[
            Camada("Aterro", 1.5, TipoSubstrato.ATERRO, nspt=6),
            Camada("Areia média", 2.5, TipoSubstrato.GRANULAR, nspt=12),
            Camada("Argila mole", 3.0, TipoSubstrato.COESIVO, nspt=4,
                   Cc=0.45, e0=1.2, cv=2.0, Es=4000),
            Camada("Areia compacta", 5.0, TipoSubstrato.GRANULAR, nspt=25),
        ],
        nivel_agua=3.0,
    )


def _dimensionar(*, com_perfil: bool = True, verificar_recalque: bool = True,
                 N: float = 800.0):
    solo = Solo(sigma_adm=200.0, hf=1.5,
                perfil=_perfil() if com_perfil else None)
    combs = gerar_combinacoes([CasoCarga("G", Esforcos(N=N))])
    s = Sapata(Pilar(ap=0.30, bp=0.30), solo, Concreto(25), Aco(500), combs,
               0.045, OpcoesProjeto(verificar_recalque=verificar_recalque))
    return s, solo, s.dimensionar()


# ======================================================================== #
#  O campo existe e vale (N_qp + peso próprio) / (a·b)
# ======================================================================== #
def test_q_servico_e_a_carga_de_servico_dividida_pela_area():
    s, _, r = _dimensionar()
    Nqp = max(c.esforcos.N for c in s.combs_qp)
    assert r.q_servico == pytest.approx((Nqp + r.peso_proprio) / (r.a * r.b),
                                        rel=1e-12)


def test_q_servico_valor_de_regressao_do_caso_medido_pelo_a6():
    """Caso conferido em execução na revisão do GATE 2: pilar 30×30 cm,
    N = 800 kN, σ_adm = 200 kPa, hf = 1,50 m → sapata 2,20 × 2,20 m,
    q_serviço = 194,888636 kPa, sobrecarga na base = 27,0 kPa e
    q_líquido = 167,888636 kPa. Os três números vinham do relatório do a6 como
    reconstituição; agora saem do campo exposto, e ficam travados aqui."""
    _, solo, r = _dimensionar()
    assert (r.a, r.b) == pytest.approx((2.20, 2.20))
    assert r.q_servico == pytest.approx(194.888636, abs=1e-6)
    assert solo.sobrecarga_no_nivel_da_base() == pytest.approx(27.0, abs=1e-9)
    assert r.recalques.q_liquido == pytest.approx(167.888636, abs=1e-6)


def test_q_servico_e_a_pressao_total_nao_a_liquida():
    """Não pode ter descontado o alívio de escavação: quem desconta é
    `tensao_liquida_na_base` / `AnaliseRecalque.q_liquido`, adiante."""
    _, solo, r = _dimensionar()
    assert r.q_servico > r.recalques.q_liquido
    assert r.q_servico - r.recalques.q_liquido == pytest.approx(
        solo.sobrecarga_no_nivel_da_base(), rel=1e-12)


# ======================================================================== #
#  Modo de falha (1): existe mesmo sem análise de recalques
# ======================================================================== #
def test_q_servico_existe_com_verificar_recalque_desligado():
    """O defeito original: perfil PRESENTE, `verificar_recalque=False`,
    `res.recalques is None` — e a pressão de serviço, que sempre existiu,
    ficava inacessível."""
    _, _, r = _dimensionar(verificar_recalque=False)
    assert r.recalques is None
    assert r.q_servico > 0.0


def test_q_servico_existe_sem_perfil_geotecnico():
    _, _, r = _dimensionar(com_perfil=False)
    assert r.recalques is None
    assert r.q_servico > 0.0


def test_q_servico_nao_depende_da_opcao_de_recalque():
    """Mesma sapata, mesma carga: a opção de VERIFICAÇÃO não pode alterar a
    pressão de serviço."""
    _, _, com = _dimensionar(verificar_recalque=True)
    _, _, sem = _dimensionar(verificar_recalque=False)
    assert (com.a, com.b, com.h, com.h0) == (sem.a, sem.b, sem.h, sem.h0)
    assert sem.q_servico == pytest.approx(com.q_servico, rel=1e-12)


# ======================================================================== #
#  É o MESMO número que alimenta AnaliseRecalque — expor não mudou valor
# ======================================================================== #
def test_q_servico_e_exatamente_o_que_entrou_na_analise_de_recalques():
    """`q_liquido` do resultado tem de ser recuperável de `q_servico` pela
    conta do núcleo, com erro zero. Se `_pressao_servico` passasse a devolver
    outra coisa que não o q que `_analisar_recalques` usa, este teste cai."""
    _, solo, r = _dimensionar()
    assert tensao_liquida_na_base(r.q_servico, solo) == pytest.approx(
        r.recalques.q_liquido, rel=1e-15)


def test_recalque_inalterado_apos_expor_a_pressao_de_servico():
    """Valor capturado com o código de HEAD antes da exposição do campo: a
    mudança é de visibilidade, não de número."""
    _, _, r = _dimensionar()
    assert r.recalques.recalque_total_mm == pytest.approx(65.91531882440958,
                                                          abs=1e-9)


# ======================================================================== #
#  Modo de falha (2): a soma q_liquido + sobrecarga não é inversa
# ======================================================================== #
def test_reconstituir_por_soma_falha_quando_a_pressao_liquida_satura():
    """Motivo de o campo ter de ser exposto em vez de reconstituído: com
    q_serviço abaixo da sobrecarga, `max(0; ...)` zera a líquida e a soma
    devolve a SOBRECARGA, não o q_serviço de partida. Δσ continua correto
    (zero em toda a profundidade), mas o valor de pressão exibido seria falso.
    """
    solo = Solo(sigma_adm=200.0, hf=1.5, perfil=_perfil())
    sobrecarga = solo.sobrecarga_no_nivel_da_base()
    q_servico = 0.5 * sobrecarga
    an = AnaliseRecalque(solo.perfil, 2.0, 2.0, solo.hf, q_servico)

    assert an.q_liquido == 0.0
    reconstituido = an.q_liquido + sobrecarga
    assert reconstituido == pytest.approx(sobrecarga, rel=1e-12)
    assert reconstituido != pytest.approx(q_servico, rel=1e-6)


# ======================================================================== #
#  Guarda de domínio de `_pressao_servico` (não extrapolar em silêncio)
# ======================================================================== #
@pytest.mark.parametrize("a,b", [(0.0, 2.0), (2.0, 0.0), (-2.0, 2.0)])
def test_pressao_servico_rejeita_area_nao_positiva(a, b):
    """Área nula daria ZeroDivisionError ou infinito silencioso."""
    s, _, _ = _dimensionar()
    with pytest.raises(ValueError, match="Dimensões em planta"):
        s._pressao_servico(a, b, 0.60, 0.25)
