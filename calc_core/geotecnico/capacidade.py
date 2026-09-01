"""Capacidade de carga de sapata em solo homogêneo — Terzaghi com N de Vesic.

Ref.: ABNT NBR 6122:2022, item 7.3.2, p. 22
[rule: NBR6122-7.3.2-metodos-teoricos-condicao-2022] (autorização e condição
suspensiva — o que é NORMATIVO aqui é o invólucro, não a equação)
[pratica: FB-CINTRA-TERZAGHI-VESIC-capacidade-de-carga] (origem da equação)

A NBR 6122:2022 §7.3.2 autoriza "métodos analíticos (teorias de capacidade de
carga)" mas NÃO reproduz nenhum: não traz Terzaghi, Vesic, Meyerhof, Skempton,
nem fator Nc/Nq/Nγ, nem fator de forma, nem equação alguma de capacidade de
carga de fundação rasa (busca negativa do a1, reconferida pelo a2 na camada de
texto do PDF do acervo). A equação vem de CINTRA/AOKI/ALBIERO (2011) e é
FONTE SECUNDÁRIA NÃO NORMATIVA.

    sigma_r = c·Nc·Sc + q·Nq·Sq + ½·γ·B·Nγ·Sγ        [kPa],  q = γ·h

    Nq = e^(π·tg φ)·tg²(45° + φ/2)      (Reissner, 1924)
    Nc = (Nq − 1)·cotg φ                (Prandtl, 1921); Nc(0) = 2 + π
    Nγ = 2·(Nq + 1)·tg φ                (Caquot-Kérisel / Vesic)

O QUE A NORMA EXIGE DESTE CAMINHO, e que só faz sentido junto: §7.3.2 + linha
"Analíticos" da Tabela 1 (FSg = 3,00 FIXO) + nota (b) da Tabela 1 (c e φ
CARACTERÍSTICOS, sem minoração) + §7.4 (ELS). Implementar a equação sem os
quatro é implementar outra coisa. A divisão por FSg e o rótulo de ELU ficam em
``geotecnico.sigma_adm``; aqui só se produz sigma_r.

FORMA FECHADA, NUNCA CONSULTA À TAB. 2.2. A própria fonte diz que a tabela foi
DERIVADA destas equações ("Vesic calcula os valores [...] reproduzidos na
Tab. 2.2"): a tabela é saída, não entrada. Isso elimina a interpolação (a
tabela só tem φ inteiro e a fonte não declara regra de interpolação) e resolve
o φ* do puncionamento, que quase nunca é inteiro. A Tab. 2.2 permanece em
``kb/formulas.yaml`` com papel melhor: FIXTURE DE VALIDAÇÃO (REQ-SIGMA-11).
Forma fechada NÃO amplia domínio — a guarda de 0 a 50° permanece.
"""
from __future__ import annotations

import math

from calc_core.geotecnico.dominio import (
    DECLARADO_EM_TEXTO,
    ForaDoDominioError,
    exigir_declaracao,
    exigir_intervalo,
    exigir_positivo,
    exigir_um_de,
)
from calc_core.geotecnico.seguranca import exigir_metodo_admissivel
from calc_core.modelos import (
    CARREGAMENTO_DRENADO,
    CARREGAMENTO_NAO_DRENADO,
    FORMA_CIRCULAR,
    FORMA_CORRIDA,
    FORMA_QUADRADA,
    FORMA_RETANGULAR,
    FORMAS_DE_BEER,
    MODOS_DE_RUPTURA,
    NATUREZAS_DE_CARREGAMENTO,
    RUPTURA_PUNCIONAMENTO,
    EntradaCapacidadeCarga,
    FatoresDeCapacidade,
    FatoresDeForma,
    ResultadoCapacidadeCarga,
)

_FONTE = ("CINTRA/AOKI/ALBIERO (2011), item 2.2, impressa 26 — domínio de "
          "validade declarado pela própria fonte")
_APOIO = ("ruleset.yaml > FB-CINTRA-TERZAGHI-VESIC-capacidade-de-carga > "
          "dominio_de_validade; REQ-SIGMA-07")

PHI_MINIMO_GRAUS = 0.0
PHI_MAXIMO_GRAUS = 50.0
"""Extensão declarada da Tab. 2.2 (Vesic, 1975), reproduzida pela fonte.

Que a forma fechada saiba calcular φ = 55° NÃO é autorização para usá-la:
o domínio é o da fonte, não o do ponto flutuante (REQ-SIGMA-07 a).
"""

NC_PHI_ZERO = 2.0 + math.pi
"""Limite de Nc = (Nq − 1)·cotg φ quando φ → 0: 5,14159...

A forma fechada é 0/0 em φ = 0, e este é o caso de ARGILA NÃO DRENADA, isto é,
o caminho mais usado — um bug aqui não é caso de canto. Usa-se o LIMITE, não um
epsilon e não um ``try/except`` que devolva zero (REQ-SIGMA-07 f).
"""

REDUCAO_PUNCIONAMENTO = 2.0 / 3.0
"""Redução de puncionamento: c* = ⅔·c e tg φ* = ⅔·tg φ (item 2.2.6)."""

AVISO_EQUACAO_APROXIMADA = (
    "A própria fonte qualifica a equação de APROXIMADA: é superposição de três "
    "casos particulares que não se somam rigorosamente "
    "[pratica: FB-CINTRA-TERZAGHI-VESIC-capacidade-de-carga]."
)

AVISO_CONVENCAO_DA_FONTE = (
    "Convenção da fonte (impressa 26): na notação de CINTRA/AOKI/ALBIERO "
    "'c e phi geralmente representam os valores NÃO DRENADOS' — diferente da "
    "usual em Mecânica dos Solos. Conferir de qual convenção vieram os "
    "parâmetros informados."
)


def fator_Nq(phi_graus: float) -> float:
    """Nq = e^(π·tg φ)·tg²(45° + φ/2) (Reissner, 1924).

    Ref.: ABNT NBR 6122:2022, item 7.3.2, p. 22
    [rule: NBR6122-7.3.2-metodos-teoricos-condicao-2022] (autorização; a
    EQUAÇÃO não é normativa)
    [pratica: FB-CINTRA-TERZAGHI-VESIC-capacidade-de-carga] (origem)

    Domínio 0 <= φ <= 50°, extensão declarada da Tab. 2.2. Fora dele a função
    RECUSA (REQ-SIGMA-07 a). Contorno: φ = 0 → Nq = 1,00 exato.
    """
    _exigir_phi(phi_graus)
    phi = math.radians(phi_graus)
    return math.exp(math.pi * math.tan(phi)) * math.tan(
        math.radians(45.0 + phi_graus / 2.0)
    ) ** 2


def fator_Nc(phi_graus: float) -> float:
    """Nc = (Nq − 1)·cotg φ (Prandtl, 1921), com Nc(0) = 2 + π.

    Ref.: ABNT NBR 6122:2022, item 7.3.2, p. 22
    [rule: NBR6122-7.3.2-metodos-teoricos-condicao-2022] (autorização; a
    EQUAÇÃO não é normativa)
    [pratica: FB-CINTRA-TERZAGHI-VESIC-capacidade-de-carga] (origem)

    Em φ = 0 a forma fechada é 0/0 e o valor devolvido é o LIMITE
    ``NC_PHI_ZERO`` = 5,14159..., não um epsilon (REQ-SIGMA-07 f). É o caso de
    argila não drenada, o mais usado deste módulo.
    """
    _exigir_phi(phi_graus)
    if phi_graus == 0.0:
        return NC_PHI_ZERO
    phi = math.radians(phi_graus)
    return (fator_Nq(phi_graus) - 1.0) / math.tan(phi)


def fator_N_gamma(phi_graus: float) -> float:
    """Nγ = 2·(Nq + 1)·tg φ (Caquot-Kérisel, adotada por Vesic).

    Ref.: ABNT NBR 6122:2022, item 7.3.2, p. 22
    [rule: NBR6122-7.3.2-metodos-teoricos-condicao-2022] (autorização; a
    EQUAÇÃO não é normativa)
    [pratica: FB-CINTRA-TERZAGHI-VESIC-capacidade-de-carga] (origem)

    NÃO é o Nγ de Terzaghi puro: a fonte afirma que "não há solução analítica
    para Nγ" e a expressão que exibe depende de um empuxo passivo que ela não
    fornece e de um ângulo obtido por minimização numérica. Aquela expressão
    NÃO pode virar código, em nenhuma hipótese. Contorno: φ = 0 → Nγ = 0,00.
    """
    _exigir_phi(phi_graus)
    return 2.0 * (fator_Nq(phi_graus) + 1.0) * math.tan(math.radians(phi_graus))


def fatores_de_capacidade(phi_graus: float) -> FatoresDeCapacidade:
    """Nc, Nq, Nγ e o quociente Nq/Nc CALCULADO (jamais lido de tabela).

    Ref.: ABNT NBR 6122:2022, item 7.3.2, p. 22
    [rule: NBR6122-7.3.2-metodos-teoricos-condicao-2022] (autorização; as
    EQUAÇÕES não são normativas)
    [pratica: FB-CINTRA-TERZAGHI-VESIC-capacidade-de-carga] (origem)

    Nq/Nc é coluna DERIVADA da própria Tab. 2.2, publicada por conveniência
    porque os fatores de forma de De Beer a exigem; usar o 0,20 impresso na
    linha φ = 0 junto com Nc = 5,14 e Nq = 1,00 tornaria a tabela internamente
    incoerente. O valor calculado é 0,1945 (REQ-SIGMA-07 h).
    """
    Nq = fator_Nq(phi_graus)
    Nc = fator_Nc(phi_graus)
    return FatoresDeCapacidade(
        phi_graus=phi_graus,
        Nc=Nc,
        Nq=Nq,
        N_gamma=fator_N_gamma(phi_graus),
        Nq_sobre_Nc=Nq / Nc,
    )


def phi_reduzido_de_puncionamento(phi_graus: float) -> float:
    """φ* = arctg(⅔·tg φ) — reduz a TANGENTE, nunca o ângulo.

    Ref.: ABNT NBR 6122:2022, item 7.3.2, p. 22
    [rule: NBR6122-7.3.2-metodos-teoricos-condicao-2022] (autorização; a
    EQUAÇÃO não é normativa)
    [pratica: FB-CINTRA-TERZAGHI-VESIC-capacidade-de-carga] (item 2.2.6)

    φ* = ⅔·φ é o erro clássico e está expressamente proibido em REQ-SIGMA-07
    (i). Em φ = 30°: arctg(⅔·0,5774) = 21,05°, contra 20,0° do erro.
    """
    _exigir_phi(phi_graus)
    return math.degrees(
        math.atan(REDUCAO_PUNCIONAMENTO * math.tan(math.radians(phi_graus)))
    )


def fatores_de_forma_de_beer(forma: str, B_m: float, L_m: float,
                             phi_graus: float) -> FatoresDeForma:
    """Sc, Sq e Sγ de De Beer (Tab. 2.3), único conjunto aprovado na v9.

    Ref.: ABNT NBR 6122:2022, item 7.3.2, p. 22
    [rule: NBR6122-7.3.2-metodos-teoricos-condicao-2022] (autorização; a
    TABELA não é normativa)
    [pratica: FB-CINTRA-TERZAGHI-VESIC-capacidade-de-carga] (Tab. 2.3)

    ==============  ====================  ==================  ===============
    forma           Sc                    Sq                  Sγ
    ==============  ====================  ==================  ===============
    corrida         1                     1                   1
    retangular      1 + (B/L)·(Nq/Nc)     1 + (B/L)·tg φ      1 − 0,4·(B/L)
    quadrada        1 + (Nq/Nc)           1 + tg φ            0,60
    circular        1 + (Nq/Nc)           1 + tg φ            0,60
    ==============  ====================  ==================  ===============

    PROIBIDO misturar com a Tab. 2.1 (Terzaghi-Peck), que NÃO é implementada
    (REQ-SIGMA-07 g): são dois pacotes coerentes entre si e a fonte não
    autoriza cruzá-los.

    O φ recebido é o DECLARADO. Sob puncionamento os fatores de forma NÃO são
    reduzidos — aparecem sem linha na fonte —, ao contrário de Nc, Nq e Nγ
    (REQ-SIGMA-07 i).
    """
    exigir_um_de("forma", forma, FORMAS_DE_BEER, fonte=_FONTE,
                 forca=DECLARADO_EM_TEXTO, apoio_no_ruleset=_APOIO)
    exigir_positivo("B_m", B_m, fonte=_FONTE, apoio_no_ruleset=_APOIO)
    exigir_positivo("L_m", L_m, fonte=_FONTE, apoio_no_ruleset=_APOIO)
    _exigir_phi(phi_graus)

    if forma == FORMA_CORRIDA:
        return FatoresDeForma(forma=forma, Sc=1.0, Sq=1.0, S_gamma=1.0)

    Nq_sobre_Nc = fatores_de_capacidade(phi_graus).Nq_sobre_Nc
    tg_phi = math.tan(math.radians(phi_graus))
    if forma in (FORMA_QUADRADA, FORMA_CIRCULAR):
        return FatoresDeForma(
            forma=forma,
            Sc=1.0 + Nq_sobre_Nc,
            Sq=1.0 + tg_phi,
            S_gamma=0.60,
        )
    razao = B_m / L_m
    return FatoresDeForma(
        forma=forma,
        Sc=1.0 + razao * Nq_sobre_Nc,
        Sq=1.0 + razao * tg_phi,
        S_gamma=1.0 - 0.4 * razao,
    )


def validar_entrada_capacidade(entrada: EntradaCapacidadeCarga) -> tuple[str, ...]:
    """Aplica as guardas (a) a (e) de REQ-SIGMA-07 e devolve os avisos.

    Ref.: ABNT NBR 6122:2022, item 7.3.2, p. 22
    [rule: NBR6122-7.3.2-metodos-teoricos-condicao-2022]

    A condição da edição 2022 é SUSPENSIVA — "desde que contemplem todas as
    particularidades do projeto, inclusive a natureza do carregamento (drenado
    ou não drenado)" —, e uma condição suspensiva que o software não verifica é
    uma condição que o software viola em silêncio. Guardas, todas RECUSANDO:

    (a) 0 <= φ <= 50°, extensão declarada da Tab. 2.2;
    (b) h <= B, hipótese 2 de Terzaghi — é o que autoriza trocar a camada
        acima da base pela sobrecarga q = γ·h;
    (c) solo HOMOGÊNEO no bulbo, declarado — o caso estratificado (item 2.5 da
        fonte) NÃO foi extraído em nenhuma rodada;
    (d) modo de ruptura declarado, 'geral' ou 'puncionamento' apenas;
    (e) c >= 0, B > 0, L >= B, γ > 0 (nos dois campos de γ);
    e ainda a coerência entre a natureza declarada do carregamento e os
    parâmetros recebidos (REQ-SIGMA-08).
    """
    exigir_metodo_admissivel(entrada.metodo_de_seguranca)
    _exigir_phi(entrada.phi_graus)
    exigir_positivo("c_kPa", entrada.c_kPa, fonte=_FONTE,
                    apoio_no_ruleset=_APOIO, permitir_zero=True)
    exigir_positivo("B_m", entrada.B_m, fonte=_FONTE, apoio_no_ruleset=_APOIO)
    exigir_positivo("L_m", entrada.L_m, fonte=_FONTE, apoio_no_ruleset=_APOIO)
    exigir_positivo("h_m", entrada.h_m, fonte=_FONTE, apoio_no_ruleset=_APOIO,
                    permitir_zero=True)
    exigir_positivo("gamma_acima_da_base_kN_m3",
                    entrada.gamma_acima_da_base_kN_m3, fonte=_FONTE,
                    apoio_no_ruleset=_APOIO)
    exigir_positivo("gamma_abaixo_da_base_kN_m3",
                    entrada.gamma_abaixo_da_base_kN_m3, fonte=_FONTE,
                    apoio_no_ruleset=_APOIO)

    if entrada.L_m < entrada.B_m:
        raise _fora(
            "L_m", entrada.L_m, f">= B_m = {entrada.B_m}",
            "B é a MENOR dimensão da base e L a maior. Troque os dois valores.",
        )
    if entrada.h_m > entrada.B_m:
        raise _fora(
            "h_m", entrada.h_m, f"<= B_m = {entrada.B_m} (hipótese 2 de Terzaghi)",
            "Para h > B a troca da camada acima da base pela sobrecarga "
            "q = gamma·h NÃO está justificada pela fonte, e o erro é do lado "
            "INSEGURO. Escolha outro método ou reduza o embutimento.",
        )

    exigir_um_de("forma", entrada.forma, FORMAS_DE_BEER, fonte=_FONTE,
                 forca=DECLARADO_EM_TEXTO, apoio_no_ruleset=_APOIO)
    exigir_um_de(
        "modo_de_ruptura", entrada.modo_de_ruptura, MODOS_DE_RUPTURA,
        fonte=("CINTRA/AOKI/ALBIERO (2011), itens 2.2 e 2.2.6 — a 'ruptura "
               "local' dos autores é média aritmética confessadamente sem "
               "respaldo bibliográfico e NÃO entra nesta versão"),
        forca=DECLARADO_EM_TEXTO,
        apoio_no_ruleset="REQ-SIGMA-12; FB-CINTRA-2.4-ruptura-local-media",
        sugestao=("O software NÃO infere o modo de ruptura e não oferece um "
                  "terceiro. Note que o que TERZAGHI chamou de 'ruptura local' "
                  "é o que esta fonte chama de PUNCIONAMENTO."),
    )
    exigir_um_de(
        "natureza_do_carregamento", entrada.natureza_do_carregamento,
        NATUREZAS_DE_CARREGAMENTO,
        fonte=("NBR 6122:2022 §7.3.2, redação de 2022: 'desde que contemplem "
               "todas as particularidades do projeto, inclusive a natureza do "
               "carregamento (drenado ou não drenado)'"),
        forca=DECLARADO_EM_TEXTO, apoio_no_ruleset="REQ-SIGMA-08",
    )
    exigir_declaracao(
        "solo_homogeneo_no_bulbo_declarado",
        entrada.solo_homogeneo_no_bulbo_declarado,
        exigencia=("Declare que o maciço no bulbo é homogêneo, ou informe a "
                   "camada equivalente."),
        fonte=("CINTRA/AOKI/ALBIERO (2011), item 2.2, hipótese de solo "
               "homogêneo; o caso estratificado é o item 2.5 (impressas "
               "36-40), NÃO extraído em nenhuma rodada"),
        apoio_no_ruleset=_APOIO + "; REQ-SIGMA-07 (c)",
    )

    if entrada.forma == FORMA_CORRIDA and entrada.L_m < 5.0 * entrada.B_m:
        raise _fora(
            "L_m", entrada.L_m, f">= 5·B_m = {5.0 * entrada.B_m} para 'corrida'",
            "A hipótese original é sapata CORRIDA com L >= 5B. Para L < 5B use "
            "forma='retangular': é exatamente para isso que servem os fatores "
            "de forma de De Beer.",
        )
    if entrada.forma in (FORMA_QUADRADA, FORMA_CIRCULAR) and entrada.L_m != entrada.B_m:
        raise _fora(
            "L_m", entrada.L_m, f"== B_m = {entrada.B_m} para {entrada.forma!r}",
            "Sapata quadrada tem B = L; em sapata circular B é o diâmetro. "
            "Para B != L use forma='retangular'.",
        )
    if entrada.forma == FORMA_RETANGULAR and entrada.L_m >= 5.0 * entrada.B_m:
        aviso_forma = (
            f"L/B = {entrada.L_m / entrada.B_m:.2f} >= 5: a fonte trata este "
            "caso como sapata CORRIDA no desenvolvimento original. Os fatores "
            "de forma retangulares continuam válidos, mas confira a escolha."
        )
    else:
        aviso_forma = ""

    avisos = [AVISO_EQUACAO_APROXIMADA, AVISO_CONVENCAO_DA_FONTE]
    if aviso_forma:
        avisos.append(aviso_forma)
    avisos.extend(_avisos_de_natureza(entrada))
    return tuple(avisos)


def capacidade_de_carga(entrada: EntradaCapacidadeCarga) -> ResultadoCapacidadeCarga:
    """sigma_r = c·Nc·Sc + q·Nq·Sq + ½·γ·B·Nγ·Sγ, com q = γ_acima·h.

    Ref.: ABNT NBR 6122:2022, item 7.3.2, p. 22
    [rule: NBR6122-7.3.2-metodos-teoricos-condicao-2022] (autorização e
    condição suspensiva; a EQUAÇÃO não é normativa)
    [pratica: FB-CINTRA-TERZAGHI-VESIC-capacidade-de-carga] (equação, fatores
    de Vesic e fatores de forma de De Beer)

    Devolve a tensão de RUPTURA, sem fator de segurança e sem rótulo de tensão
    admissível — quem divide por FSg é ``geotecnico.sigma_adm``.

    Sob ``modo_de_ruptura='puncionamento'`` (solos fofos ou moles) aplicam-se
    c* = ⅔·c e φ* = arctg(⅔·tg φ), e Nc, Nq, Nγ saem de φ*; os fatores de
    FORMA continuam calculados com o φ declarado, porque na fonte aparecem sem
    linha (REQ-SIGMA-07 i).

    Domínio de validade em ``validar_entrada_capacidade`` — fora dele esta
    função RECUSA com ``ForaDoDominioError`` e não devolve número algum.
    """
    avisos = validar_entrada_capacidade(entrada)

    if entrada.modo_de_ruptura == RUPTURA_PUNCIONAMENTO:
        c_calculo = REDUCAO_PUNCIONAMENTO * entrada.c_kPa
        phi_calculo = phi_reduzido_de_puncionamento(entrada.phi_graus)
        avisos = avisos + (
            ("Modo PUNCIONAMENTO (solos fofos ou moles): c* = 2/3·c e "
            "phi* = arctg(2/3·tg phi) = "
            f"{phi_calculo:.3f}° a partir de phi = {entrada.phi_graus:.3f}°. "
            "Os fatores de FORMA não são reduzidos. Na nomenclatura de "
            "TERZAGHI este modo chama-se 'ruptura local'; o memorial usa o "
            "vocabulário da fonte citada."),
        )
    else:
        c_calculo = entrada.c_kPa
        phi_calculo = entrada.phi_graus

    fatores = fatores_de_capacidade(phi_calculo)
    forma = fatores_de_forma_de_beer(
        entrada.forma, entrada.B_m, entrada.L_m, entrada.phi_graus
    )

    q = entrada.gamma_acima_da_base_kN_m3 * entrada.h_m
    parcela_coesao = c_calculo * fatores.Nc * forma.Sc
    parcela_sobrecarga = q * fatores.Nq * forma.Sq
    parcela_peso = (0.5 * entrada.gamma_abaixo_da_base_kN_m3 * entrada.B_m
                    * fatores.N_gamma * forma.S_gamma)

    return ResultadoCapacidadeCarga(
        sigma_r_kPa=parcela_coesao + parcela_sobrecarga + parcela_peso,
        parcela_coesao_kPa=parcela_coesao,
        parcela_sobrecarga_kPa=parcela_sobrecarga,
        parcela_peso_kPa=parcela_peso,
        q_kPa=q,
        fatores=fatores,
        fatores_de_forma=forma,
        c_de_calculo_kPa=c_calculo,
        phi_de_calculo_graus=phi_calculo,
        modo_de_ruptura=entrada.modo_de_ruptura,
        natureza_do_carregamento=entrada.natureza_do_carregamento,
        metodo_de_seguranca=entrada.metodo_de_seguranca,
        avisos=avisos,
    )


# --------------------------------------------------------------------------- #
# Guardas internas
# --------------------------------------------------------------------------- #
def _exigir_phi(phi_graus: float) -> float:
    """Guarda (a) de REQ-SIGMA-07: 0 <= φ <= 50°, extensão da Tab. 2.2."""
    return exigir_intervalo(
        "phi_graus", phi_graus, PHI_MINIMO_GRAUS, PHI_MAXIMO_GRAUS,
        fonte=("CINTRA/AOKI/ALBIERO (2011), Tab. 2.2 (Vesic, 1975), impressa "
               "33 — a tabela vai de 0 a 50 graus e a fonte não fornece "
               "valores acima disso"),
        forca=DECLARADO_EM_TEXTO,
        apoio_no_ruleset=_APOIO + "; REQ-SIGMA-07 (a)",
        sugestao=("A forma fechada calcularia phi > 50°, mas o domínio "
                  "declarado da fonte não vai até lá — forma fechada remove a "
                  "granularidade da tabela, não amplia o domínio."),
    )


def _fora(parametro: str, valor: object, intervalo: str,
          sugestao: str) -> ForaDoDominioError:
    """Monta a recusa de uma guarda geométrica do caminho teórico."""
    return ForaDoDominioError(
        parametro=parametro, valor=valor, intervalo=intervalo, fonte=_FONTE,
        forca=DECLARADO_EM_TEXTO, apoio_no_ruleset=_APOIO, sugestao=sugestao,
    )


def _avisos_de_natureza(entrada: EntradaCapacidadeCarga) -> tuple[str, ...]:
    """Coerência entre a natureza declarada e os parâmetros (REQ-SIGMA-08)."""
    phi, c = entrada.phi_graus, entrada.c_kPa
    natureza = entrada.natureza_do_carregamento
    if phi == 0.0 and c > 0.0 and natureza != CARREGAMENTO_NAO_DRENADO:
        raise _fora(
            "natureza_do_carregamento", natureza,
            f"{CARREGAMENTO_NAO_DRENADO!r} quando phi = 0 e c > 0",
            "phi = 0 com c > 0 é análise NÃO DRENADA (resistência ao "
            "cisalhamento não drenada). A combinação declarada tem de bater "
            "com os parâmetros recebidos.",
        )
    if phi > 0.0 and c == 0.0 and natureza != CARREGAMENTO_DRENADO:
        raise _fora(
            "natureza_do_carregamento", natureza,
            f"{CARREGAMENTO_DRENADO!r} quando phi > 0 e c = 0",
            "phi > 0 com c = 0 é análise em tensões efetivas (drenada). A "
            "combinação declarada tem de bater com os parâmetros recebidos.",
        )
    if phi > 0.0 and c > 0.0:
        return (
            (f"Parâmetros com coesão E atrito (c = {c:.1f} kPa, "
            f"phi = {phi:.2f}°) declarados como {natureza!r}: a combinação é "
            "legítima nas duas naturezas, e por isso o software não a arbitra "
            "— confira a origem dos ensaios."),
        )
    if phi == 0.0 and c == 0.0:
        return (
            ("c = 0 e phi = 0: sobra apenas a parcela de sobrecarga q·Nq·Sq. "
            "Confira se os parâmetros de resistência foram informados."),
        )
    return ()


__all__ = [
    "AVISO_CONVENCAO_DA_FONTE",
    "AVISO_EQUACAO_APROXIMADA",
    "NC_PHI_ZERO",
    "PHI_MAXIMO_GRAUS",
    "PHI_MINIMO_GRAUS",
    "REDUCAO_PUNCIONAMENTO",
    "capacidade_de_carga",
    "fator_N_gamma",
    "fator_Nc",
    "fator_Nq",
    "fatores_de_capacidade",
    "fatores_de_forma_de_beer",
    "phi_reduzido_de_puncionamento",
    "validar_entrada_capacidade",
]
