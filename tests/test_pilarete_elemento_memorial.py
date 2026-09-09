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


def test_arranjo_assimetrico_ENTRE_PLANOS_e_o_MENOR_dos_dois_que_governa():
    """d'_h != d'_b (cada plano simétrico EM SI): o MENOR dos dois RECUSA.

    Ref.: ABNT NBR 6118:2023, 7.4.7.5 e Tabela 7.2, nota (d), p. 20
    [rule: NBR6118-Tab7.2-nota-d-cobrimento-pilarete]
    [req: REQ-PILARETE-09-cobrimento-proprio-e-a-incompatibilidade-com-Sapata]

    ACHADO DO A6 NO GATE 2 (rodada 3): o mutante M4 — trocar o ``min`` por
    ``max`` em ``ConsistenciaDeCobrimento.cobrimento_implicito_mm`` — sobrevive
    à suíte inteira (823/823 continuam passando) porque nenhum teste até aqui
    tinha d'_h e d'_b DIFERENTES entre si. Todos os testes anteriores desta
    seção usam ``barras()``, que aplica o MESMO ``d_linha`` nos dois planos.

    Aqui o plano de h tem d'_h = 0,043 m (cobrimento implícito 30 mm,
    INSUFICIENTE frente ao declarado de 45 mm) e o plano de b tem d'_b =
    0,058 m (cobrimento implícito 45 mm, exatamente no limite — SUFICIENTE,
    pois a guarda exige c_implícito >= c_declarado) — cada plano é
    internamente simétrico (não confundir com arranjo assimétrico DENTRO de
    um mesmo plano, que é RECUSADO por outra guarda, 17.2.5). O código real
    usa o MENOR dos dois planos para caracterizar a peça e RECUSA. Com o
    mutante M4 (min -> max), o plano de b (45 mm, no limite mas suficiente)
    mascararia o plano de h (30 mm, insuficiente) e o cenário passaria a
    SEGUIR — reabrindo exatamente o defeito ALTA desta rodada, só que para
    arranjo assimétrico entre planos em vez de simétrico nos dois.
    """
    area = area_barra(16.0)
    h = b = 0.30
    d_linha_h = 0.043  # insuficiente: c implícito = 43 - 5 - 8 = 30 mm < 45
    d_linha_b = 0.058  # no limite:    c implícito = 58 - 5 - 8 = 45 mm >= 45
    barras_assimetricas_entre_planos = tuple(
        BarraLongitudinal(pos_h=ph, pos_b=pb, area=area)
        for ph in (d_linha_h, h - d_linha_h)
        for pb in (d_linha_b, b - d_linha_b))

    with pytest.raises(RecusaForaDeDominio) as erro:
        verificar_pilarete(dados(
            cobrimento_declarado_mm=45.0,
            barras=barras_assimetricas_entre_planos,
            espacamento_entre_eixos_mm=(h - 2 * d_linha_h) * 1000.0))

    mensagem = str(erro.value)
    assert "7.4.7.5" in mensagem
    assert "plano de h" in mensagem  # é o plano de h que governa (o MENOR)
    assert "45.00" in mensagem and "30.00" in mensagem
    assert "INSEGURO" in mensagem

    # Confirma diretamente a propriedade que o mutante M4 ataca: o cobrimento
    # implícito da PEÇA é o MENOR dos dois planos, não o maior.
    from calc_core.estrutural.pilarete.geometria import (
        cobrimento_implicito_pelas_barras,
        exigir_cobrimento_consistente_com_as_barras,
    )
    c_h = cobrimento_implicito_pelas_barras(
        d_linha=d_linha_h, phi_longitudinal_mm=16.0, phi_t_mm=5.0)
    c_b = cobrimento_implicito_pelas_barras(
        d_linha=d_linha_b, phi_longitudinal_mm=16.0, phi_t_mm=5.0)
    assert c_h == pytest.approx(30.0)
    assert c_b == pytest.approx(45.0)  # 58 - 5 - 8 = 45 mm: no limite, suficiente
    with pytest.raises(RecusaForaDeDominio):
        exigir_cobrimento_consistente_com_as_barras(
            d_linha_no_plano_de_h=d_linha_h, d_linha_no_plano_de_b=d_linha_b,
            phi_longitudinal_mm=16.0, phi_t_mm=5.0,
            cobrimento_declarado_mm=45.0, cobrimento_minimo_mm=45.0)


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


# --- REQ-PILARETE-20: os OUTROS TRÊS pares de declaração redundante ---------
#
# O DEFEITO QUE ESTES TESTES MATAM (achado do a2 na v14 do ruleset, por leitura
# adversarial de `DadosDoPilarete`): REQ-PILARETE-09 cruzou UM par (cobrimento
# × posições) e os outros TRÊS ficaram sem cruzamento nenhum — a bitola
# declarada contra a ÁREA de cada barra, `numero_de_barras` contra
# `len(barras)` e o espaçamento declarado contra as posições. É a MESMA classe
# de defeito da seção acima, do MESMO lado INSEGURO, e nenhuma checagem
# dimensional pega: área é m² nas duas leituras, contagem é adimensional nas
# duas.

def test_area_de_phi_25_com_phi_16_DECLARADO_RECUSA():
    """O CENÁRIO EXATO MEDIDO PELO a2, e ele vira o veredito.

    Ref.: ABNT NBR 6118:2023, 18.4.2.1 (p. 153) e 17.2.2 (p. 120)
    [rule: NBR6118-18.4.2-armaduras-longitudinais-pilarete]
    [req: REQ-PILARETE-20-cruzar-as-outras-tres-declaracoes-redundantes]  (a)

    Geometria A (30×30, C25, CA-50, N_d = 1000 kN, 4 barras, d' = 5,8 cm) com
    phi DECLARADO 16 mm e as `BarraLongitudinal` da tupla trazendo a área de
    phi 25 mm (4,9087 cm² por barra em vez de 2,0106). Com
    M_Sd,x = M_Sd,y = 36 kN·m o índice do par solicitante cai de 1,1257 para
    0,6978 e o veredito de §17.2 VIRA de NÃO ATENDIDO para ATENDIDO, com todo
    o detalhamento continuando "atendido" porque lê o phi declarado (A_s =
    19,64 cm² é 2,18 % de A_c, longe dos 8 % de 17.3.5.3.2). Agora RECUSA.
    """
    barras_infladas = barras(phi_mm=25.0)   # posições de phi 16, áreas de 25
    with pytest.raises(RecusaForaDeDominio) as erro:
        verificar_pilarete(dados(phi_longitudinal_mm=16.0,
                                 barras=barras_infladas,
                                 M_Sd_x=36.0, M_Sd_y=36.0))

    mensagem = str(erro.value)
    assert "18.4.2.1" in mensagem
    assert "16.00" in mensagem            # phi declarado
    assert "2.0106" in mensagem           # área da bitola declarada [cm²]
    assert "4.9087" in mensagem           # área declarada na barra [cm²]
    assert "25.00" in mensagem            # bitola implícita pela área
    assert "INSEGURO" in mensagem


def test_a_inversao_do_veredito_medida_pelo_a2_e_reproduzida_por_execucao():
    """1,1257 -> 0,6978, NÃO ATENDIDO -> ATENDIDO. É a medida, não a narrativa.

    Ref.: ABNT NBR 6118:2023, 17.2.1, 17.2.2 e 17.2.5, p. 120-125
    [rule: NBR6118-17.2.1-envoltoria-criterio-de-seguranca]
    [req: REQ-PILARETE-20-cruzar-as-outras-tres-declaracoes-redundantes]

    Chama §17.2 DIRETAMENTE, com as duas seções, porque é exatamente o módulo
    que a guarda de (6-bis) protege: se um dia a guarda for removida ou movida
    para dentro de um ramo, este teste continua documentando o tamanho do erro
    que ela impede. O caminho do ELEMENTO (com a guarda) RECUSA os dois.
    """
    from calc_core.estrutural.pilarete.secao import (
        SecaoRetangular,
        verificar_elu_solicitacoes_normais,
    )
    from calc_core.sapata_isolada.materiais import Aco, Concreto

    def _secao(phi_mm):
        return SecaoRetangular(
            h_secao=0.30, b_secao=0.30, barras=barras(phi_mm=phi_mm),
            concreto=Concreto(fck=25.0, gamma_c=1.4),
            aco=Aco(fyk=500.0, gamma_s=1.15))

    def _indice(phi_mm):
        return verificar_elu_solicitacoes_normais(
            _secao(phi_mm), N_Sd=1000.0, M_Sd_x=36.0, M_Sd_y=36.0,
            M_1d_min_xx=24.0, M_1d_min_yy=24.0)

    honesto = _indice(16.0)
    inflado = _indice(25.0)
    assert honesto.indice_A_par_solicitante == pytest.approx(1.1257, abs=1e-4)
    assert inflado.indice_A_par_solicitante == pytest.approx(0.6978, abs=1e-4)
    assert honesto.atendido is False and inflado.atendido is True

    # E o pilarete que DECLARA phi 16 com as áreas de phi 25 não chega lá.
    with pytest.raises(RecusaForaDeDominio):
        verificar_pilarete(dados(phi_longitudinal_mm=16.0,
                                 barras=barras(phi_mm=25.0),
                                 M_Sd_x=36.0, M_Sd_y=36.0))


def test_area_MENOR_que_a_da_bitola_declarada_SEGUE():
    """A guarda de (a) é de UM LADO SÓ: arredondamento comercial é conservador.

    Ref.: ABNT NBR 6118:2023, 18.4.2.1, p. 153
    [req: REQ-PILARETE-20-cruzar-as-outras-tres-declaracoes-redundantes]  (a)

    2,00 cm² por barra declarados para phi 16 mm, cuja área exata é 2,0106 cm²:
    A_s sai MENOR, M_Rd sai MENOR e N_Rd0 sai MENOR — conservador nos três. É o
    arredondamento de tabela comercial, e recusá-lo seria recusar projeto
    legítimo.
    """
    area_arredondada = 2.00e-4     # 2,00 cm² em m²
    resultado = verificar_pilarete(dados(
        phi_longitudinal_mm=16.0,
        barras=tuple(BarraLongitudinal(pos_h=b.pos_h, pos_b=b.pos_b,
                                       area=area_arredondada)
                     for b in barras())))
    consistencia = resultado.consistencia_da_armadura
    assert consistencia.areas_declaradas_nas_barras == (area_arredondada,) * 4
    assert consistencia.area_da_bitola_declarada == pytest.approx(
        area_barra(16.0))
    assert (max(consistencia.areas_declaradas_nas_barras)
            < consistencia.area_da_bitola_declarada)


def test_bitolas_MISTAS_sao_RECUSADAS_e_nao_aceitas_em_silencio():
    """Todo o detalhamento é verificado contra um phi ÚNICO. Decisão do a5.

    Ref.: ABNT NBR 6118:2023, 18.4.2.1 e 18.4.2.2, p. 153
    [req: REQ-PILARETE-20-cruzar-as-outras-tres-declaracoes-redundantes]

    O requisito manda ESCOLHER entre admitir um phi por barra e recusar a seção
    com bitolas mistas — "o que está PROIBIDO é continuar aceitando em
    silêncio". Recusa-se porque não existe leitura conservadora de um phi só
    para bitolas diferentes: a maior é conservadora no espaçamento livre e no
    ell_b de 9.5.2.3, a menor no piso de phi >= 10 mm de 18.4.2.1.
    """
    mistas = tuple(
        BarraLongitudinal(pos_h=b.pos_h, pos_b=b.pos_b,
                          area=area_barra(16.0 if i % 2 else 12.5))
        for i, b in enumerate(barras()))
    with pytest.raises(RecusaForaDeDominio) as erro:
        verificar_pilarete(dados(phi_longitudinal_mm=16.0, barras=mistas))
    mensagem = str(erro.value)
    assert "bitolas mistas" in mensagem
    assert "12.50" in mensagem and "16.00" in mensagem


@pytest.mark.parametrize("numero", [3, 5])
def test_numero_de_barras_declarado_tem_de_bater_com_len_barras(numero):
    """(b) é IGUALDADE: não há lado conservador numa contagem.

    Ref.: ABNT NBR 6118:2023, 18.4.2.2, p. 153
    [req: REQ-PILARETE-20-cruzar-as-outras-tres-declaracoes-redundantes]  (b)

    Declarar 5 e montar 4 satisfaz "uma barra por vértice" com armadura que não
    existe; declarar 3 e montar 4 reprova por 18.4.2.2 uma seção que a tem. Os
    dois são erro de declaração e os dois RECUSAM.
    """
    with pytest.raises(RecusaForaDeDominio) as erro:
        verificar_pilarete(dados(numero_de_barras=numero))
    mensagem = str(erro.value)
    assert "numero_de_barras" in mensagem and "len(barras)" in mensagem
    assert f"({numero}, 4)" in mensagem


def test_espacamento_declarado_MAIOR_que_o_real_RECUSA():
    """(c), lado INSEGURO: piso verificado sobre um vão livre que não existe.

    Ref.: ABNT NBR 6118:2023, 18.4.2.2, p. 153
    [req: REQ-PILARETE-20-cruzar-as-outras-tres-declaracoes-redundantes]  (c)

    Barras nos vértices de 30×30 com d' = 5,8 cm dão 184 mm entre eixos nas
    duas direções. Declarar 300 mm faz o espaçamento livre da seção corrente
    sair 284 mm e o da emenda 268 mm, quando os reais são 168 e 152 mm — e o
    piso de max(20 mm; phi; 1,2·d_agr) passa a ser verificado sobre um vão que
    a peça não tem.
    """
    with pytest.raises(RecusaForaDeDominio) as erro:
        verificar_pilarete(dados(espacamento_entre_eixos_mm=300.0))
    mensagem = str(erro.value)
    assert "18.4.2.2" in mensagem
    assert "300.00" in mensagem and "184.00" in mensagem
    assert "INSEGURO" in mensagem


def test_espacamento_declarado_MENOR_que_o_real_SEGUE():
    """(c) é assimétrica no piso: declarar menos do que existe é conservador.

    Ref.: ABNT NBR 6118:2023, 18.4.2.2, p. 153
    [req: REQ-PILARETE-20-cruzar-as-outras-tres-declaracoes-redundantes]  (c)
    """
    resultado = verificar_pilarete(dados(espacamento_entre_eixos_mm=100.0))
    consistencia = resultado.consistencia_da_armadura
    assert consistencia.espacamento_real_minimo_mm == pytest.approx(184.0)
    assert consistencia.espacamento_entre_eixos_declarado_mm == 100.0
    assert resultado.armadura_longitudinal.atende_espacamento_entre_eixos


def test_o_TETO_de_18_4_2_2_le_o_MAIOR_espacamento_REAL_e_nao_o_declarado():
    """(c), o outro sinal: 90×20 com 4 barras esconde 784 mm atrás de 84 mm.

    Ref.: ABNT NBR 6118:2023, 18.4.2.2, p. 153
    [rule: NBR6118-18.4.2-armaduras-longitudinais-pilarete]
    [req: REQ-PILARETE-20-cruzar-as-outras-tres-declaracoes-redundantes]  (c)

    O MESMO número declarado serve a dois limites de sinal contrário, e nenhum
    valor é conservador nos dois quando as duas direções têm espaçamentos
    diferentes. Aqui as barras dos vértices distam 784 mm ao longo de h e
    84 mm ao longo de b; o teto de 18.4.2.2 é min(2·200; 400) = 400 mm. Com o
    declarado (84 mm, que é o que a guarda do piso exige) o teto "atenderia";
    lido do MAIOR espaçamento real, REPROVA — e reprovar é o que tem de
    acontecer, porque excesso de espaçamento é defeito de PROJETO (faltam
    barras intermediárias), não entrada fora de domínio.
    """
    resultado = verificar_pilarete(dados(
        h_secao=0.90, b_secao=0.20, ell=0.80, N_d=800.0, M_Sd_x=0.0,
        M_Sd_y=0.0, H_x=0.0, barras=barras(h=0.90, b=0.20),
        espacamento_entre_eixos_mm=84.0, N_gamma_f_1=571.0))
    longitudinal = resultado.armadura_longitudinal
    assert longitudinal.espacamento_entre_eixos_adotado_mm == pytest.approx(84.0)
    assert longitudinal.espacamento_entre_eixos_verificado_no_teto_mm == (
        pytest.approx(784.0))
    assert longitudinal.espacamento_entre_eixos_maximo_mm == pytest.approx(400.0)
    assert longitudinal.atende_espacamento_entre_eixos is False
    assert resultado.atendido is False


def test_o_memorial_registra_os_TRES_cruzamentos_com_os_dois_numeros_de_cada():
    """Cruzamento que não aparece no memorial é indistinguível de inexistente.

    Ref.: ABNT NBR 6118:2023, 18.4.2.1 e 18.4.2.2, p. 153
    [req: REQ-PILARETE-12-memorial-e-o-que-ele-e-obrigado-a-dizer]
    [req: REQ-PILARETE-20-cruzar-as-outras-tres-declaracoes-redundantes]
    """
    memorial = " ".join(verificar_pilarete(dados()).memorial())
    assert "CRUZAMENTO bitola × áreas das barras" in memorial
    assert "phi declarado = 16.00 mm" in memorial
    assert "2.0106 cm²" in memorial
    assert "CRUZAMENTO contagem" in memorial
    assert "numero_de_barras declarado = 4 contra len(barras) = 4" in memorial
    assert "CRUZAMENTO espaçamento × posições das barras" in memorial
    assert "declarado = 184.00 mm" in memorial
    assert "mínimo 184.00 mm e máximo 184.00 mm" in memorial


def test_a_recusa_dos_tres_pares_vale_TAMBEM_na_faixa_B():
    """FAIXA B não chama §17.4, mas chama §17.2 — que usa as MESMAS barras.

    Ref.: ABNT NBR 6118:2023, 14.4.1 e 17.2.2, p. 83 e 120-122
    [req: REQ-PILARETE-20-cruzar-as-outras-tres-declaracoes-redundantes]

    Mesma disciplina de posição da guarda irmã de cobrimento: se ela estivesse
    dentro do ramo do cortante, a FAIXA B seria porta aberta — a área inflada
    entra em A_s e na varredura de M_Rd nas DUAS faixas.
    """
    for sobrescritas in ({"barras": barras(phi_mm=25.0)},
                         {"numero_de_barras": 8},
                         {"espacamento_entre_eixos_mm": 300.0}):
        with pytest.raises(RecusaForaDeDominio):
            verificar_pilarete(dados(ell=0.80, **sobrescritas))


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


# --- REQ-PILARETE-21: a MEDIÇÃO do espaçamento real e o canal do piso de phi -

def _barras_90x40_com_centroide():
    """4 vértices de 90×40 (d' = 5,8 cm) MAIS uma barra no centroide.

    Ref.: ABNT NBR 6118:2023, item 18.4.2.2, p. 153
    [req: REQ-PILARETE-21-medir-o-espacamento-real-e-o-piso-de-phi-pelo-canal-certo]  (a)

    É o arranjo EXATO que o a2 mediu: simétrico nos dois eixos (passa em
    `arranjo_simetrico()` de 17.2.5), com a barra do centroide criando uma
    camada intermediária em cada direção.
    """
    quatro = barras(h=0.90, b=0.40)
    centroide = BarraLongitudinal(pos_h=0.45, pos_b=0.20, area=area_barra(16.0))
    return quatro + (centroide,)


def test_barra_no_centroide_NAO_pode_baixar_o_espacamento_calculado_a_392mm():
    """O caso do a2: 90×40, phi 16, 4 vértices + 1 centroide -> RECUSA.

    Ref.: ABNT NBR 6118:2023, item 18.4.2.2, p. 153
    [rule: NBR6118-18.4.2-armaduras-longitudinais-pilarete]
    [req: REQ-PILARETE-21-medir-o-espacamento-real-e-o-piso-de-phi-pelo-canal-certo]  (a)

    MEDIDO PELO a2 ANTES DA CORREÇÃO, com teto = min(2·400; 400) = 400 mm:
    os 4 vértices davam 784,0 mm e NÃO ATENDIAM (certo); os MESMOS 4 mais a
    barra do centroide davam 392,0 mm e "ATENDIAM", enquanto o vão real entre
    as barras de canto de cada face longa continuava sendo 784 mm. A barra do
    centroide não está em face nenhuma e não encurta face nenhuma.

    A resposta é RECUSA (ESCOPO_DESTA_VERSAO), não reprovação: o software não
    sabe MEDIR esse arranjo — 18.4.2.2 o admite, o helper é que não o cobre.
    """
    with pytest.raises(RecusaForaDeDominio) as erro:
        verificar_pilarete(dados(
            h_secao=0.90, b_secao=0.40, ell=0.80, N_d=800.0, M_Sd_x=0.0,
            M_Sd_y=0.0, H_x=0.0, barras=_barras_90x40_com_centroide(),
            numero_de_barras=5, espacamento_entre_eixos_mm=284.0,
            N_gamma_f_1=571.0))
    recusa = erro.value
    assert recusa.forca == "escopo_desta_versao_nao_limite_da_norma"
    assert "INTERIOR" in recusa.parametro
    assert "(0.45, 0.2)" in recusa.mensagem
    # A frase de escopo tem de estar do lado do SOFTWARE, não da Norma.
    assert "limite desta versão do software, não da Norma" in recusa.sugestao
    assert "INSEGURO" in recusa.sugestao


def test_o_arranjo_de_5_barras_do_a2_PASSA_na_simetria_de_17_2_5():
    """`arranjo_simetrico()` NÃO é guarda suficiente — daí a checagem própria.

    Ref.: ABNT NBR 6118:2023, itens 17.2.5 e 18.4.2.2, p. 125 e 153
    [req: REQ-PILARETE-21-medir-o-espacamento-real-e-o-piso-de-phi-pelo-canal-certo]  (a)

    Se a simetria bastasse, a guarda nova seria redundante. Ela não basta: o
    arranjo que abre o buraco é simétrico nos DOIS eixos.
    """
    from calc_core.estrutural.pilarete.secao import SecaoRetangular
    from calc_core.sapata_isolada.materiais import Aco, Concreto

    secao = SecaoRetangular(
        h_secao=0.90, b_secao=0.40, barras=_barras_90x40_com_centroide(),
        concreto=Concreto(fck=25.0, gamma_c=1.4),
        aco=Aco(fyk=500.0, gamma_s=1.15))
    assert secao.arranjo_simetrico() is True


def test_sem_a_barra_interior_a_MESMA_secao_90x40_REPROVA_pelos_784mm():
    """O outro lado do caso do a2: em ANEL, a medição é exata e REPROVA.

    Ref.: ABNT NBR 6118:2023, item 18.4.2.2, p. 153
    [req: REQ-PILARETE-21-medir-o-espacamento-real-e-o-piso-de-phi-pelo-canal-certo]  (a)
    [req: REQ-PILARETE-20-cruzar-as-outras-tres-declaracoes-redundantes]  (c)

    A guarda nova não pode "consertar" recusando tudo: a mesma seção sem a
    barra interior continua sendo MEDIDA, e o teto de 400 mm continua sendo
    comparado com os 784 mm reais — REPROVAÇÃO (defeito de projeto: faltam
    barras intermediárias nas faces longas), não recusa.
    """
    resultado = verificar_pilarete(dados(
        h_secao=0.90, b_secao=0.40, ell=0.80, N_d=800.0, M_Sd_x=0.0,
        M_Sd_y=0.0, H_x=0.0, barras=barras(h=0.90, b=0.40),
        espacamento_entre_eixos_mm=284.0, N_gamma_f_1=571.0))
    longitudinal = resultado.armadura_longitudinal
    assert longitudinal.espacamento_entre_eixos_verificado_no_teto_mm == (
        pytest.approx(784.0))
    assert longitudinal.espacamento_entre_eixos_maximo_mm == pytest.approx(400.0)
    assert longitudinal.atende_espacamento_entre_eixos is False
    assert resultado.atendido is False


def test_barra_intermediaria_NA_FACE_continua_aceita_e_medida():
    """A guarda recusa barra INTERIOR, não barra intermediária de FACE.

    Ref.: ABNT NBR 6118:2023, item 18.4.2.2, p. 153
    [req: REQ-PILARETE-21-medir-o-espacamento-real-e-o-piso-de-phi-pelo-canal-certo]  (a)

    Recusar o anel com barras no meio das faces seria recusar exatamente o
    arranjo que resolve o excesso de espaçamento — e é o arranjo em que a
    projeção por camadas É o vão real. Aqui as duas faces longas de 90 cm
    ganham uma barra no meio: 784 mm passam a 392 mm REAIS, e o teto atende.
    """
    area = area_barra(16.0)
    d, meio, oposta_h, oposta_b = 0.058, 0.45, 0.842, 0.342
    anel = tuple(BarraLongitudinal(pos_h=ph, pos_b=pb, area=area)
                 for ph, pb in ((d, d), (d, oposta_b),
                                (meio, d), (meio, oposta_b),
                                (oposta_h, d), (oposta_h, oposta_b)))
    resultado = verificar_pilarete(dados(
        h_secao=0.90, b_secao=0.40, ell=0.80, N_d=800.0, M_Sd_x=0.0,
        M_Sd_y=0.0, H_x=0.0, barras=anel, numero_de_barras=6,
        espacamento_entre_eixos_mm=284.0, N_gamma_f_1=571.0))
    longitudinal = resultado.armadura_longitudinal
    assert longitudinal.espacamento_entre_eixos_verificado_no_teto_mm == (
        pytest.approx(392.0))
    assert longitudinal.atende_espacamento_entre_eixos is True


def test_phi_16_declarado_com_todas_as_barras_de_phi_8_REPROVA_no_piso():
    """(b) do a2: barras reais de 8 mm não passam num piso normativo de 10 mm.

    Ref.: ABNT NBR 6118:2023, item 18.4.2.1, p. 153
    [rule: NBR6118-18.4.2-armaduras-longitudinais-pilarete]
    [req: REQ-PILARETE-21-medir-o-espacamento-real-e-o-piso-de-phi-pelo-canal-certo]  (b)

    MEDIDO PELO a2 ANTES DA CORREÇÃO: `atende_phi_minimo = True`. A
    sub-declaração uniforme é conservadora em A_s, M_Rd, ell_b, cobrimento e
    espaçamento livre — e é do lado ERRADO exatamente no piso de phi, que lia
    o DECLARADO. Passa a ler min(declarado; bitola implícita pela MENOR área).

    É REPROVAÇÃO, não recusa: phi abaixo do mínimo é defeito de PROJETO
    (18.4.2.1), não entrada fora de domínio — e a guarda de área de
    REQ-PILARETE-20(a) admite área MENOR de propósito.
    """
    resultado = verificar_pilarete(dados(
        phi_longitudinal_mm=16.0, barras=barras(phi_mm=8.0)))
    longitudinal = resultado.armadura_longitudinal
    assert longitudinal.phi_longitudinal_mm == pytest.approx(16.0)
    assert longitudinal.phi_verificado_no_piso_mm == pytest.approx(8.0)
    assert longitudinal.atende_phi_minimo is False
    # O TETO segue lendo o DECLARADO (canal mais conservador do outro lado).
    assert longitudinal.phi_maximo_mm == pytest.approx(37.5)
    assert longitudinal.atende_phi_maximo is True
    assert resultado.atendido is False
    memorial = " ".join(resultado.memorial())
    assert "PISO (phi >= 10 mm)" in memorial
    assert "bitola implícita pela MENOR área declarada 8.00 mm" in memorial


def test_o_arredondamento_comercial_continua_passando_no_piso_de_phi():
    """2,00 cm² para phi 16 dão 15,96 mm implícitos — folgadíssimo sobre 10 mm.

    Ref.: ABNT NBR 6118:2023, item 18.4.2.1, p. 153
    [req: REQ-PILARETE-21-medir-o-espacamento-real-e-o-piso-de-phi-pelo-canal-certo]  (b)

    A correção de (b) não pode transformar tabela comercial em reprovação —
    é o caso que a assimetria de REQ-PILARETE-20(a) foi feita para admitir.
    """
    area_arredondada = 2.00e-4
    resultado = verificar_pilarete(dados(
        phi_longitudinal_mm=16.0,
        barras=tuple(BarraLongitudinal(pos_h=b.pos_h, pos_b=b.pos_b,
                                       area=area_arredondada)
                     for b in barras())))
    longitudinal = resultado.armadura_longitudinal
    assert longitudinal.phi_verificado_no_piso_mm == pytest.approx(15.9577,
                                                                  abs=1e-4)
    assert longitudinal.atende_phi_minimo is True


def test_a_recusa_de_bitolas_mistas_NAO_atribui_a_frase_a_Norma():
    """(c): a Norma verifica POR BARRA; quem tem phi único é o SOFTWARE.

    Ref.: ABNT NBR 6118:2023, itens 18.4.2.1 e 18.4.2.2, p. 153
    [req: REQ-PILARETE-21-medir-o-espacamento-real-e-o-piso-de-phi-pelo-canal-certo]  (c)

    O campo `fonte` de uma recusa é CITAÇÃO DE FONTE e vai ao memorial: não
    pode conter frase que a Norma não escreve. A decisão de escopo (um phi só)
    fica onde pertence — na descrição do limite do software.
    """
    mistas = tuple(
        BarraLongitudinal(pos_h=b.pos_h, pos_b=b.pos_b,
                          area=area_barra(16.0 if i % 2 else 12.5))
        for i, b in enumerate(barras()))
    with pytest.raises(RecusaForaDeDominio) as erro:
        verificar_pilarete(dados(phi_longitudinal_mm=16.0, barras=mistas))
    recusa = erro.value
    assert "são verificados contra um phi ÚNICO" not in recusa.fonte
    assert "POR BARRA" in recusa.fonte
    assert "ESTE SOFTWARE" in recusa.fonte
    assert "NÃO proíbe" in recusa.fonte
    assert recusa.forca == "escopo_desta_versao_nao_limite_da_norma"
