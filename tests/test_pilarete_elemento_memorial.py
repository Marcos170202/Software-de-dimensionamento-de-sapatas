"""Pilarete — orquestração, veredito por FAIXA e memorial (REQ-PILARETE-12/14/16).

Cobre REQ-PILARETE-12 (o que o memorial é OBRIGADO a dizer), -14 (proibição de
mistura de método de segurança e de majoração por vento) e -16 (o nome do
veredito nas duas faixas), além da ordem das guardas de -15(1) e -17(5) e do
gamma_n de -03(3) aplicado aos esforços.

A ARMADILHA DE LEITURA QUE ESTE ARQUIVO VIGIA, e ela mudou de lado na v13: na
v12 o risco era concluir, dos estribos de 18.4.3, que o cortante estava
coberto (não estava). Agora o risco é o simétrico e maior — concluir que,
porque §17.4 foi implementado, ele se aplica sempre. NÃO SE APLICA: a FAIXA B
é comum, e para seções com h/b >= 1,684 no caso engastado-livre sob M_1d,mín
ela é a ÚNICA possível.
"""
import pytest

from calc_core.estrutural.dominio import RecusaForaDeDominio
from calc_core.estrutural.pilarete import cortante as ct
from calc_core.estrutural.pilarete.classificacao import (
    FAIXA_A_ELEMENTO_LINEAR,
    FAIXA_B_FORA_DE_14_4_1,
)
from calc_core.estrutural.pilarete.elemento import (
    DadosDoPilarete,
    exigir_valores_de_calculo,
    verificar_pilarete,
)
from calc_core.estrutural.pilarete.ligacao import (
    JUNTA_COM_ADERENCIA_DECLARADA,
    MONOLITICO,
)
from calc_core.estrutural.pilarete.secao import BarraLongitudinal
from calc_core.sapata_isolada.materiais import area_barra

D_LINHA = 0.058
"""d' = cobrimento 45 mm (nota d da Tabela 7.2) + estribo 5 mm + phi/2."""


def barras(h=0.30, b=0.30, phi_mm=16.0, d_linha=D_LINHA):
    area = area_barra(phi_mm)
    return tuple(BarraLongitudinal(pos_h=ph, pos_b=pb, area=area)
                 for ph in (d_linha, h - d_linha)
                 for pb in (d_linha, b - d_linha))


def dados(**sobrescritas):
    """Geometria A: 30×30, ell = 1,00 m, C25, CA-50, 4 phi 16, N_d = 1000 kN."""
    h = sobrescritas.pop("h_secao", 0.30)
    b = sobrescritas.pop("b_secao", 0.30)
    phi = sobrescritas.pop("phi_longitudinal_mm", 16.0)
    padrao = dict(
        h_secao=h, b_secao=b, ell=1.00,
        vinculacao="ENGASTADO_BASE_LIVRE_TOPO",
        secao_constante=True, armadura_constante=True,
        f_ck_MPa=25.0, gamma_c_base=1.4,
        condicoes_desfavoraveis_de_execucao=False,
        f_yk_longitudinal_MPa=500.0, f_yk_estribo_MPa=500.0, gamma_s=1.15,
        idade_maior_ou_igual_28_dias=True,
        classe_de_agressividade="II", d_agregado_mm=19.0,
        cobrimento_declarado_mm=45.0, phi_longitudinal_mm=phi,
        numero_de_barras=4,
        espacamento_entre_eixos_mm=(min(h, b) - 2 * D_LINHA) * 1000.0,
        phi_t_mm=5.0, s_estribo_mm=125.0,
        barras=barras(h=h, b=b, phi_mm=phi),
        N_d=1000.0, M_Sd_x=24.0, M_Sd_y=24.0, H_x=40.0, H_y=0.0,
        tipo_de_junta=MONOLITICO, boa_aderencia=True,
        armadura_tracionada_em_alguma_combinacao=False,
        modelo_de_calculo=ct.MODELO_I, theta_biela_graus=None,
        alpha_estribo_graus=90.0, A_sw_por_s=3.1416e-4, N_gamma_f_1=714.0,
        normal_de_compressao_em_todas_as_combinacoes=True,
    )
    padrao.update(sobrescritas)
    return DadosDoPilarete(**padrao)


def _dados_com_gamma_n():
    """Geometria na faixa REDUZIDA de 13.2.3: 24×16 cm, ell = 0,75 m.

    Escolhida com cuidado, porque as três fronteiras se apertam ao mesmo
    tempo: b_mín = 16 cm exige gamma_n = 1,15 (13.2.3), lambda = 32,5 < 35
    exige ell < 5,052·b = 0,808 m (15.8.2) e a FAIXA A exige ell >= 3·h =
    0,72 m (14.4.1). A janela inteira tem 8,8 cm.
    """
    return dados(
        h_secao=0.24, b_secao=0.16, ell=0.75, N_d=400.0, M_Sd_x=10.0,
        M_Sd_y=5.0, H_x=10.0, phi_longitudinal_mm=12.5, d_agregado_mm=9.5,
        barras=barras(h=0.24, b=0.16, phi_mm=12.5, d_linha=0.05625),
        espacamento_entre_eixos_mm=47.5, A_sw_por_s=2.0e-4,
        cobrimento_declarado_mm=45.0, N_gamma_f_1=286.0)


# --- REQ-PILARETE-16: o nome do veredito DEPENDE da faixa ------------------

def test_veredito_da_faixa_A_nomeia_as_DUAS_verificacoes():
    """FAIXA A: "...NORMAIS (17.2.1) e ELU de FORÇA CORTANTE (17.4.2.1)"."""
    resultado = verificar_pilarete(dados())
    assert resultado.faixa == FAIXA_A_ELEMENTO_LINEAR
    nome = resultado.nome_do_veredito
    assert "ELU de solicitações NORMAIS (NBR 6118:2023, 17.2.1)" in nome
    assert "ELU de FORÇA CORTANTE (NBR 6118:2023, 17.4.2.1)" in nome
    assert nome.endswith("ATENDIDO")
    assert resultado.elu_cortante is not None


def test_veredito_da_faixa_B_e_escopado_e_nao_menciona_cortante():
    """FAIXA B: EXATAMENTE "ELU de solicitações NORMAIS (17.2.1)".

    Geometria B (30×30, ell = 0,80 m): pilar curto (lambda 18,5 < 35) e FORA
    de 14.4.1 (razão 2,667). §17.4 NÃO é chamado — nem para o relatório.
    """
    resultado = verificar_pilarete(dados(ell=0.80))
    assert resultado.faixa == FAIXA_B_FORA_DE_14_4_1
    assert resultado.elu_cortante is None
    nome = resultado.nome_do_veredito
    assert nome.startswith("ELU de solicitações NORMAIS (NBR 6118:2023, 17.2.1)")
    assert "FORÇA CORTANTE" not in nome


@pytest.mark.parametrize("ell", [0.80, 1.00])
def test_veredito_nunca_diz_aprovado_nem_ok(ell):
    """CONTINUA PROIBIDO "APROVADO", "OK" ou "pilarete verificado".

    A única ocorrência autorizada da palavra é a frase que a NEGA — o memorial
    declara, com todas as letras, que este software não emite "APROVADO". Um
    leitor apressado tem de esbarrar na negação, nunca na afirmação.
    """
    resultado = verificar_pilarete(dados(ell=ell))
    linhas = resultado.memorial()
    for linha in linhas:
        if "APROVADO" in linha:
            assert "NÃO emite" in linha, linha
        assert "pilarete OK" not in linha or "NÃO emite" in linha
        assert "pilarete verificado" not in linha
    assert resultado.nome_do_veredito.endswith(
        ("ATENDIDO", "NÃO ATENDIDO"))


def test_faixa_B_traz_as_duas_frases_obrigatorias_e_a_interpretacao_de_17_2():
    """REQ-PILARETE-16-(e) e (g), com o H declarado repetindo as frases (f)."""
    memorial = " ".join(verificar_pilarete(dados(ell=0.80)).memorial())
    assert "NÃO satisfaz a definição de elemento linear" in memorial
    assert "2.6667" in memorial
    assert "0.9000 m" in memorial          # 3·máx(b,h) que faltou atingir
    assert "NÃO FOI VERIFICADO" in memorial
    assert "Seção 22" in memorial
    assert "H declarado NÃO NULO" in memorial   # alínea (f)
    assert "remissão nominal a \"pilares\"" in memorial   # alínea (g)


def test_faixa_A_nao_repete_as_frases_da_faixa_B():
    """Na FAIXA A a frase "cortante NÃO verificado" seria FALSA — e some."""
    memorial = " ".join(verificar_pilarete(dados()).memorial())
    assert "NÃO FOI VERIFICADO" not in memorial
    assert "ELU de FORÇA CORTANTE" in memorial


# --- REQ-PILARETE-17(5): a ORDEM das guardas -------------------------------

def test_geometria_reprovada_recusa_antes_de_qualquer_verificacao():
    """13.2.3 vem antes de tudo: 19×18 cm nem chega ao equilíbrio de seção."""
    with pytest.raises(RecusaForaDeDominio) as erro:
        verificar_pilarete(dados(h_secao=0.19, b_secao=0.18,
                                 barras=barras(h=0.19, b=0.18,
                                               d_linha=0.045)))
    assert "360" in erro.value.mensagem


def test_pilar_esbelto_recusa_antes_do_veredito():
    """15.8.2 vem antes de 17.2: acima de lambda_1 não há veredito a emitir."""
    with pytest.raises(RecusaForaDeDominio) as erro:
        verificar_pilarete(dados(ell=2.50))
    assert "15.8.2" in erro.value.mensagem


def test_junta_recusada_impede_o_resto():
    """21.6 vem antes do ELU: junta aderente com H != 0 é recusa dura."""
    with pytest.raises(RecusaForaDeDominio) as erro:
        verificar_pilarete(dados(tipo_de_junta=JUNTA_COM_ADERENCIA_DECLARADA,
                                 H_x=0.001))
    assert "9062" in erro.value.mensagem


def test_idade_menor_que_28_dias_recusa_antes_de_tudo():
    """12.3.3-b) é a primeira guarda material."""
    with pytest.raises(RecusaForaDeDominio):
        verificar_pilarete(dados(idade_maior_ou_igual_28_dias=False))


# --- REQ-PILARETE-14: método de segurança e vento --------------------------

def test_api_recusa_valores_caracteristicos_sem_converter():
    """"O software NÃO multiplica por 1,4 sozinho" — receber característico é ERRO."""
    with pytest.raises(RecusaForaDeDominio) as erro:
        exigir_valores_de_calculo("admissivel")
    assert "cálculo" in erro.value.mensagem
    with pytest.raises(RecusaForaDeDominio):
        verificar_pilarete(dados(metodo_de_seguranca="caracteristica"))
    assert exigir_valores_de_calculo("calculo") == "calculo"


def test_pacote_nao_menciona_a_majoracao_por_vento_da_NBR_6122():
    """REQ-PILARETE-14-c: 6.3.2/6.3.3 são EXCLUSIVAS da tensão do SOLO.

    "Encontrar em `estrutural/` qualquer referência a 6.3.2/6.3.3 é veto do
    a6." O vento entra no pilarete pelos coeficientes de combinação das ações,
    do lado das AÇÕES, e só.
    """
    import ast
    import pathlib

    for caminho in pathlib.Path("calc_core/estrutural").rglob("*.py"):
        fonte = caminho.read_text(encoding="utf-8")
        arvore = ast.parse(fonte)
        # DOCUMENTAÇÃO = qualquer literal de texto SOLTO (docstring de módulo,
        # de classe, de função ou de atributo). É onde a proibição pode ser
        # CITADA. Fora daí, nenhuma string do pacote pode mencionar 6.3.2/6.3.3
        # — nem em mensagem de erro, nem em rótulo de memorial.
        documentacao = {id(no.value) for no in ast.walk(arvore)
                        if isinstance(no, ast.Expr)
                        and isinstance(no.value, ast.Constant)
                        and isinstance(no.value.value, str)}
        for no in ast.walk(arvore):
            if not isinstance(no, ast.Constant) or id(no) in documentacao:
                continue
            if isinstance(no.value, str):
                assert "6.3.2" not in no.value, caminho
                assert "6.3.3" not in no.value, caminho
        # a única menção autorizada é a PROIBIÇÃO, e ela vem com o motivo:
        if "6.3.2" in fonte:
            assert "EXCLUSIVAS da tensão do SOLO" in fonte, caminho
            assert "PROIBIDO MAJORAR RESISTÊNCIA POR VENTO" in fonte, caminho


# --- REQ-PILARETE-03(3): gamma_n majora os ESFORÇOS ------------------------

def test_gamma_n_majora_os_esforcos_e_e_registrado_no_memorial():
    """14 <= b_mín < 19 cm: gamma_n = 1,95 − 0,05·b majorando N_d, M e H.

    Seção 24×16 cm (A_c = 384 cm² >= 360; h/b = 1,5 <= 5) com ell = 0,75 m —
    uma das poucas geometrias que satisfaz ao mesmo tempo a faixa reduzida de
    13.2.3, o pilar curto de 15.8.2 (lambda = 32,5 < 35) e o elemento linear
    de 14.4.1 (razão 3,125 >= 3,0).
    """
    resultado = verificar_pilarete(_dados_com_gamma_n())
    assert resultado.gamma_n == pytest.approx(1.15)
    assert resultado.gamma_n_aplicado is True
    assert resultado.N_d_majorado == pytest.approx(460.0)
    assert resultado.M_Sd_x_majorado == pytest.approx(11.5)
    assert resultado.M_Sd_y_majorado == pytest.approx(5.75)
    memorial = " ".join(resultado.memorial())
    assert "gamma_n = 1,95 − 0,05·b = 1.1500 APLICADO" in memorial


def test_M_1d_min_sai_do_N_d_JA_majorado():
    """A envoltória mínima acompanha o esforço majorado, não o declarado."""
    resultado = verificar_pilarete(_dados_com_gamma_n())
    assert resultado.M_1d_min_xx == pytest.approx(460.0 * (0.015 + 0.03 * 0.24))
    assert resultado.M_1d_min_yy == pytest.approx(460.0 * (0.015 + 0.03 * 0.16))


# --- REQ-PILARETE-12: o que o memorial é obrigado a dizer ------------------

def test_memorial_traz_todas_as_alineas_da_faixa_A():
    """As alíneas (a) a (r) de REQ-PILARETE-12, na FAIXA A."""
    resultado = verificar_pilarete(dados())
    memorial = " ".join(resultado.memorial())

    # (a) itens normativos com página
    assert "NBR 6118:2023, 14.4.1 (p. 83)" in memorial
    assert "NBR 6118:2023, 11.3.3.4.3 (p. 60)" in memorial
    # (b) M_1d,mín das duas direções e a frase de 16.3
    assert "M_1d,mín,xx = 24.0000 kN·m" in memorial
    assert "16.3 (p. 116)" in memorial
    assert "não se aceita o dimensionamento de pilares para carga centrada" in (
        memorial)
    # (c) lambda, lambda_1, i e ell_e por direção, com a vinculação
    assert "ENGASTADO_BASE_LIVRE_TOPO" in memorial
    assert "ell_e = 2.0000 m" in memorial
    assert "lambda = 23.0940" in memorial
    assert "lambda_1 = 35.0000" in memorial
    # (d) N_Rd0 e nu rotulados INFORMATIVOS
    assert "N_Rd0 = 1703.86 kN" in memorial
    assert "INFORMATIVOS" in memorial
    assert "NÃO SUFICIENTE" in memorial
    # (e) gamma_c e gamma_s efetivamente usados
    assert "gamma_c = 1.4000" in memorial and "gamma_s = 1.1500" in memorial
    assert "não aplicada" in memorial
    # (f) tipo de junta e H
    assert "Junta declarada: MONOLITICO" in memorial
    assert "H_x = 40.0000 kN" in memorial
    # (h) M_Rd com N_Sd, x e o domínio
    assert "M_Rd,xx = 63.9599 kN·m" in memorial
    assert "domínio" in memorial and "polo" in memorial
    # (i) os dois índices
    assert "I_A" in memorial and "I_B" in memorial
    # (j) o "= 1" de 17.2.5 lido como "<= 1"
    assert "escreve \"= 1\"" in memorial
    # (k) o alpha informativo
    assert "informativo, NÃO usado no veredito" in memorial
    # (m) a razão de 14.4.1 e a faixa
    assert "razão comprimento/maior dimensão da seção = 3.3333" in memorial
    # (n) o modelo declarado e os valores do cortante
    assert "MODELO declarado MODELO_I" in memorial
    assert "V_Rd2" in memorial and "V_sw" in memorial and "V_Rd3" in memorial
    assert "escolha do modelo e de theta é do PROJETISTA" in memorial
    # (o) os dois níveis de normal lado a lado
    assert "N_(gamma_f=1,0) = 714.00 kN" in memorial
    assert "dois níveis de ponderação DE PROPÓSITO" in memorial
    # (p) f_ctk lido como f_ctk,inf
    assert "f_ctk,inf" in memorial
    # (q) as duas ausências deliberadas
    assert "17.4.1.2.1" in memorial and "decalagem" in memorial.lower()
    # (r) o detalhamento composto, com o valor de CADA fonte
    assert "18.4.3 = 192" in memorial and "18.3.3.2 = " in memorial
    assert "governou 18.3.3.2" in memorial
    # (g) hipóteses e o que NÃO foi verificado
    assert "j >= 28 dias" in memorial
    assert "NÃO FORAM VERIFICADOS" in memorial
    assert "fadiga" in memorial and "§17.5" in memorial


def test_memorial_declara_quando_nao_ha_majoracao_de_V_c():
    """Alínea (o): sem N_(gamma_f=1,0) declarado, a frase é obrigatória."""
    memorial = " ".join(verificar_pilarete(dados(N_gamma_f_1=None)).memorial())
    assert "NÃO foi declarado" in memorial
    assert "PROIBIDO obtê-lo dividindo" in memorial


def test_memorial_registra_a_correcao_de_12_4_1_quando_aplicada():
    """Alínea (e): gamma_c × 1,1 é OBRIGATÓRIO quando previstas condições
    desfavoráveis, e o memorial diz que foi aplicada."""
    resultado = verificar_pilarete(
        dados(condicoes_desfavoraveis_de_execucao=True))
    assert resultado.gamma_c_usado == pytest.approx(1.54)
    assert resultado.correcao_12_4_1_aplicada is True
    assert "correção × 1,1 de 12.4.1 APLICADA" in " ".join(resultado.memorial())


def test_memorial_traz_o_traspasse_e_as_exigencias_da_emenda():
    """A espera é o que atravessa a junta — e a Soma A_st é REMETIDA."""
    memorial = " ".join(verificar_pilarete(dados()).memorial())
    assert "9.5.2.3 (p. 44)" in memorial
    assert "ell_0c = 602" in memorial
    assert "4·phi" in memorial
    assert "remetido ao projetista" in memorial.lower()


def test_cobrimento_insuficiente_reprova_sem_recusar():
    """Cobrimento é verificação de PROJETO: reprova, não recusa."""
    resultado = verificar_pilarete(dados(cobrimento_declarado_mm=30.0))
    assert resultado.cobrimento_minimo_mm == pytest.approx(45.0)
    assert resultado.atende_cobrimento is False
    assert resultado.atendido is False
    assert "NÃO ATENDE" in " ".join(resultado.memorial())


# --- REQ-PILARETE-09: o CRUZAMENTO cobrimento × posições das barras ---------
#
# O DEFEITO QUE ESTES TESTES MATAM (backlog #13, GATE 2, rodada 1, commit
# d466a59 — veto do a6 em E3): o d' que alimenta V_Rd2, V_c0 e a varredura de
# M_Rd saía de min(pos_h)/min(pos_b) — as posições DECLARADAS das barras — sem
# NENHUM cruzamento com cobrimento_declarado_mm, que só era comparado,
# isolado, contra o mínimo da Tabela 7.2 em `atende_cobrimento`. Duas fontes
# para a MESMA distância física, e elas nunca se encontravam.

def test_barras_que_implicam_cobrimento_MENOR_que_o_declarado_RECUSAM():
    """O CENÁRIO EXATO DO DEFEITO: c = 45 mm declarado, barras a 43 mm.

    Ref.: ABNT NBR 6118:2023, 7.4.7.5 e Tabela 7.2, nota (d), p. 20
    [rule: NBR6118-Tab7.2-nota-d-cobrimento-pilarete]
    [req: REQ-PILARETE-09-cobrimento-proprio-e-a-incompatibilidade-com-Sapata]

    45 mm SATISFAZ `atende_cobrimento` (mínimo 45 mm para phi 16 / CAA II /
    d_agr 19 mm), mas d' = 0,043 m com phi_t = 5 mm e phi = 16 mm implica
    c = 43 − 5 − 8 = 30 mm — o cobrimento REAL da peça é 30 mm, e MENOR que o
    declarado. Antes da correção isso passava em silêncio e dava
    V_Rd2 = 334,56 kN em vez de 315,03 kN (+6,20 %, do lado INSEGURO), com
    veredito ATENDIDO. Agora RECUSA.
    """
    with pytest.raises(RecusaForaDeDominio) as erro:
        verificar_pilarete(dados(
            cobrimento_declarado_mm=45.0,
            barras=barras(d_linha=0.043),
            espacamento_entre_eixos_mm=(0.30 - 2 * 0.043) * 1000.0))

    mensagem = str(erro.value)
    assert "7.4.7.5" in mensagem
    # Os três números do cruzamento aparecem na recusa: o declarado, o
    # implícito e o d' que teria de ser adotado para os dois baterem.
    assert "45.00" in mensagem and "30.00" in mensagem
    assert "58.00" in mensagem  # d' coerente = 45 + 5 + 16/2 = 58 mm
    assert "INSEGURO" in mensagem


def test_a_recusa_do_cruzamento_vale_TAMBEM_na_faixa_B():
    """FAIXA B não chama §17.4, mas chama §17.2 — que usa as MESMAS barras.

    Ref.: ABNT NBR 6118:2023, 7.4.7.5 e 17.2.2, p. 20 e 120-122
    [req: REQ-PILARETE-09-cobrimento-proprio-e-a-incompatibilidade-com-Sapata]

    Se a guarda estivesse dentro do ramo do cortante, a FAIXA B seria uma
    porta aberta: os braços de alavanca da varredura de M_Rd saem das mesmas
    posições declaradas, e um d' inflado aumenta M_Rd do mesmo jeito.
    """
    with pytest.raises(RecusaForaDeDominio):
        verificar_pilarete(dados(
            ell=0.80, cobrimento_declarado_mm=45.0,
            barras=barras(d_linha=0.043),
            espacamento_entre_eixos_mm=(0.30 - 2 * 0.043) * 1000.0))


def test_barras_MAIS_para_dentro_que_o_declarado_seguem_sem_recusa():
    """A guarda é de UM LADO SÓ, e o lado é escolhido.

    Ref.: ABNT NBR 6118:2023, 7.4.7.5 e Tabela 7.2, nota (d), p. 20
    [req: REQ-PILARETE-09-cobrimento-proprio-e-a-incompatibilidade-com-Sapata]

    c implícito (65 − 5 − 8 = 52 mm) MAIOR que o declarado (45 mm): o d' sai
    MENOR, que é conservador em §17.2 e §17.4. Segue, e o cobrimento continua
    sendo verificado pelo mínimo da Tabela 7.2 — REQ-PILARETE-09 permanece
    REPROVAÇÃO, e não recusa.
    """
    resultado = verificar_pilarete(dados(
        cobrimento_declarado_mm=45.0, barras=barras(d_linha=0.065),
        espacamento_entre_eixos_mm=(0.30 - 2 * 0.065) * 1000.0))
    consistencia = resultado.consistencia_de_cobrimento
    assert consistencia.cobrimento_implicito_mm == pytest.approx(52.0)
    assert resultado.atende_cobrimento is True


def test_o_cruzamento_fecha_a_cadeia_ate_o_minimo_da_tabela_7_2():
    """c_implícito >= c_declarado >= c_mín em TODO veredito ATENDIDO.

    Ref.: ABNT NBR 6118:2023, 7.4.7.5 e Tabela 7.2, nota (d), p. 20
    [req: REQ-PILARETE-09-cobrimento-proprio-e-a-incompatibilidade-com-Sapata]

    É a composição das duas metades — a guarda de 6-bis dá a primeira
    desigualdade, `atende_cobrimento` dá a segunda — e é ela que faz o mínimo
    da Tabela 7.2 valer para a PEÇA, e não para um número declarado à parte.
    """
    resultado = verificar_pilarete(dados())
    assert resultado.atendido is True
    consistencia = resultado.consistencia_de_cobrimento
    assert (consistencia.cobrimento_implicito_mm
            >= resultado.cobrimento_declarado_mm
            >= resultado.cobrimento_minimo_mm)


def test_o_memorial_registra_o_cruzamento_com_os_tres_numeros():
    """Cruzamento que não aparece no memorial é indistinguível de inexistente.

    Ref.: ABNT NBR 6118:2023, 7.4.7.5 e Tabela 7.2, nota (d), p. 20
    [req: REQ-PILARETE-12-memorial-e-o-que-ele-e-obrigado-a-dizer]
    """
    memorial = " ".join(verificar_pilarete(dados()).memorial())
    assert "CRUZAMENTO cobrimento × posições das barras" in memorial
    assert "45.00 mm (plano de h)" in memorial
    assert "45.00 mm (plano de b)" in memorial
    assert "c declarado = 45.0 mm" in memorial


def test_d_linha_do_cortante_e_o_MESMO_que_passou_pelo_cruzamento():
    """Não há caminho até V_Rd2 que escape do cruzamento.

    Ref.: ABNT NBR 6118:2023, 7.4.7.5 e 17.4.2.2, p. 20 e 136
    [req: REQ-PILARETE-09-cobrimento-proprio-e-a-incompatibilidade-com-Sapata]

    Fecha o defeito pelo lado do CONSUMIDOR: o d_útil que o cortante usa tem de
    ser reconstrutível a partir do cobrimento cruzado. Se alguém voltar a
    recalcular o d' dentro do ramo de §17.4, esta igualdade quebra.
    """
    resultado = verificar_pilarete(dados())
    consistencia = resultado.consistencia_de_cobrimento
    d_linha_esperado = (consistencia.cobrimento_implicito_no_plano_de_h_mm
                        + 5.0 + 16.0 / 2.0) / 1000.0
    d_util = resultado.elu_cortante.plano.d_util_no_plano_do_cortante
    assert d_util == pytest.approx(0.30 - d_linha_esperado)


# --- Veredito como CONJUNÇÃO -----------------------------------------------

def test_veredito_reprova_quando_o_cortante_reprova():
    """FAIXA A: o veredito é a CONJUNÇÃO. Falhar em um reprova."""
    resultado = verificar_pilarete(dados(H_x=400.0))
    assert resultado.elu_normal.atendido is True
    assert resultado.elu_cortante.atendido is False
    assert resultado.atendido is False
    assert resultado.nome_do_veredito.endswith("NÃO ATENDIDO")


def test_na_faixa_B_o_cortante_nao_entra_como_atendido_por_omissao():
    """O cortante NÃO FOI VERIFICADO — é PROIBIDO tratá-lo como atendido."""
    resultado = verificar_pilarete(dados(ell=0.80, H_x=400.0))
    assert resultado.elu_cortante is None
    assert resultado.atendido is resultado.elu_normal.atendido
    memorial = " ".join(resultado.memorial())
    assert "NÃO FOI VERIFICADO" in memorial


def test_linhas_do_cortante_na_faixa_B_RECUSAM_e_nao_dependem_de_assert():
    """A invariante é guarda de verdade — `assert` some sob `python -O`.

    Ref.: ABNT NBR 6118:2023, item 14.4.1, p. 83
    [rule: NBR6118-14.4.1-elemento-linear-classificacao]
    [req: REQ-PILARETE-16-escopo-do-veredito-e-o-cortante-nao-verificado]

    Chamar `_linhas_do_cortante` num resultado de FAIXA B é erro de wiring, e o
    que ele produziria é o pior tipo de saída: linhas de cortante num memorial
    de elemento cujo §17.4 foi RECUSADO. Com `assert`, a proteção existia em
    modo normal e DESAPARECIA sob `python -O` — a suíte passaria e a produção
    otimizada não teria guarda nenhuma.
    """
    resultado = verificar_pilarete(dados(ell=0.80))
    assert resultado.elu_cortante is None
    with pytest.raises(RecusaForaDeDominio) as erro:
        resultado._linhas_do_cortante()
    assert "14.4.1" in str(erro.value)


# --- Simetria do problema (teste pedido pelo despacho) ---------------------

def test_girar_o_pilarete_90_graus_troca_x_por_y_e_nada_mais():
    """SIMETRIA no nível do ELEMENTO: 25×40 girada vira 40×25.

    Trocam-se h<->b, M_Sd,x<->M_Sd,y e H_x<->H_y; o veredito, os índices, a
    razão de 14.4.1 e o V_Rd2 têm de ser os MESMOS, e os M_1d,mín trocam de
    lugar. Se algo mais mudar, há cruzamento de eixo escondido.
    """
    direto = verificar_pilarete(dados(
        h_secao=0.40, b_secao=0.25, ell=1.25, N_d=800.0, M_Sd_x=30.0,
        M_Sd_y=20.0, H_x=60.0, H_y=0.0,
        barras=barras(h=0.40, b=0.25), espacamento_entre_eixos_mm=134.0,
        N_gamma_f_1=571.0))
    girado = verificar_pilarete(dados(
        h_secao=0.25, b_secao=0.40, ell=1.25, N_d=800.0, M_Sd_x=20.0,
        M_Sd_y=30.0, H_x=0.0, H_y=60.0,
        barras=barras(h=0.25, b=0.40), espacamento_entre_eixos_mm=134.0,
        N_gamma_f_1=571.0))

    assert direto.faixa == girado.faixa
    assert direto.classificacao.razao_14_4_1 == pytest.approx(
        girado.classificacao.razao_14_4_1)
    assert direto.M_1d_min_xx == pytest.approx(girado.M_1d_min_yy)
    assert direto.M_1d_min_yy == pytest.approx(girado.M_1d_min_xx)
    assert direto.elu_normal.indice_A_par_solicitante == pytest.approx(
        girado.elu_normal.indice_A_par_solicitante, rel=1e-12)
    assert direto.elu_normal.indice_B_envoltoria_minima == pytest.approx(
        girado.elu_normal.indice_B_envoltoria_minima, rel=1e-12)
    assert direto.elu_cortante.V_Rd2_valor == pytest.approx(
        girado.elu_cortante.V_Rd2_valor, rel=1e-12)
    assert direto.elu_cortante.V_c_valor == pytest.approx(
        girado.elu_cortante.V_c_valor, rel=1e-12)
    assert direto.atendido == girado.atendido


def test_a_janela_de_14_4_1_com_15_8_2_e_estreita_e_pode_ser_vazia():
    """FRONTEIRA QUANTIFICADA de REQ-PILARETE-17, verificada por execução.

    Com ENGASTADO_BASE_LIVRE_TOPO e sob M_1d,mín (lambda_1 = 35), as duas
    fronteiras só coexistem se h_máx/b_mín < 1,684. Em 20×40 (razão 2,0) a
    janela é VAZIA: qualquer ell que satisfaça 14.4.1 já reprova em 15.8.2.
    """
    with pytest.raises(RecusaForaDeDominio) as erro:
        verificar_pilarete(dados(
            h_secao=0.40, b_secao=0.20, ell=1.20, N_d=800.0, M_Sd_x=0.0,
            M_Sd_y=0.0, H_x=0.0, barras=barras(h=0.40, b=0.20),
            espacamento_entre_eixos_mm=84.0, N_gamma_f_1=571.0))
    assert "lambda" in erro.value.mensagem
    # e com ell menor, o pilar é curto mas cai na FAIXA B:
    curto = verificar_pilarete(dados(
        h_secao=0.40, b_secao=0.20, ell=1.00, N_d=800.0, M_Sd_x=0.0,
        M_Sd_y=0.0, H_x=0.0, barras=barras(h=0.40, b=0.20),
        espacamento_entre_eixos_mm=84.0, N_gamma_f_1=571.0))
    assert curto.faixa == FAIXA_B_FORA_DE_14_4_1
