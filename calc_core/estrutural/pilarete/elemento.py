"""Orquestração do pilarete, veredito por FAIXA e memorial rastreável.

Ref.: ABNT NBR 6118:2023, item 17.2.1, p. 120 (ELU de solicitações normais)
[rule: NBR6118-17.2.1-envoltoria-criterio-de-seguranca]

Ref.: ABNT NBR 6118:2023, item 17.4.2.1, p. 136 (ELU de força cortante)
[rule: NBR6118-17.4.2.1-duas-condicoes-simultaneas-do-ELU-de-cortante]

Ref.: ABNT NBR 6118:2023, item 14.4.1, p. 83 (as duas FAIXAS)
[rule: NBR6118-14.4.1-elemento-linear-classificacao]
[deriv: DER-NBR6118-14.4.1-faixa-B-recusa-do-cortante]

Ref.: ABNT NBR 6118:2023, item 13.2.3 e Tabela 13.1, p. 73 (gamma_n)
[rule: NBR6118-13.2.3-dimensoes-limites-pilarete]

Ref.: ABNT NBR 6118:2023, item 16.3, p. 116 (proibição de carga centrada)
[rule: NBR6118-16.3-proibicao-de-carga-centrada]

[req: REQ-PILARETE-12-memorial-e-o-que-ele-e-obrigado-a-dizer]
[req: REQ-PILARETE-14-proibicao-de-mistura-de-metodo-e-de-majoracao-por-vento]
[req: REQ-PILARETE-15-veredito-de-ELU-de-solicitacoes-normais]
[req: REQ-PILARETE-16-escopo-do-veredito-e-o-cortante-nao-verificado]
[req: REQ-PILARETE-17-guarda-de-elemento-linear-14.4.1]

ORDEM DAS GUARDAS, E ELA NÃO É NEGOCIÁVEL (REQ-PILARETE-15(1) e -17(5)):

    12.3.3 (j >= 28 dias)  ->  13.2.3 (geometria, gamma_n)  ->  21.6 (junta)
      ->  15.8.1/15.8.2 (pilar curto)  ->  14.4.1 (FAIXA)
      ->  17.2 (N+M)  ->  17.4 (V, só na FAIXA A)  ->  detalhamento

Um V_Rd2 calculado antes de a FAIXA ser conhecida é defeito com veto do a6,
mesmo que o valor nunca chegue à tela.

O QUE ESTE MÓDULO NÃO PODE DIZER, em nenhuma formulação: "APROVADO", "OK",
"pilarete verificado" ou cor verde de peça inteira. Mesmo na FAIXA A, o que
foi verificado é o ELU de solicitações NORMAIS, o ELU de FORÇA CORTANTE e o
detalhamento — e NÃO o ELS, nem a fadiga, nem a torção (§17.5, não extraída),
nem a ligação com a sapata além da emenda por traspasse.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from calc_core.estrutural.dominio import (
    DECLARADO_EM_TEXTO,
    DECLARADO_PELO_USUARIO,
    ESCOPO_DESTA_VERSAO,
    RecusaForaDeDominio,
    exigir_declarado,
)
from calc_core.estrutural.materiais_6118 import (
    exigir_classe_normalizada,
    exigir_idade_28_dias,
    gamma_c_com_correcao_12_4_1,
)
from calc_core.estrutural.pilarete import classificacao as classificacao_14_4_1
from calc_core.estrutural.pilarete import cortante as cortante_17_4
from calc_core.estrutural.pilarete import detalhamento as detalhamento_18
from calc_core.estrutural.pilarete import ligacao as ligacao_9_5_21_6
from calc_core.estrutural.pilarete.esbeltez import (
    FRASE_16_3,
    ResultadoEsbeltez,
    momento_minimo_1a_ordem,
    verificar_pilar_curto,
)
from calc_core.estrutural.pilarete.geometria import (
    ConsistenciaDeCobrimento,
    ResultadoDimensoesLimites,
    cobrimento_nominal_minimo,
    exigir_cobrimento_consistente_com_as_barras,
    verificar_dimensoes_limites,
)
from calc_core.estrutural.pilarete.secao import (
    ALPHA_INTERACAO_INFORMATIVO,
    BarraLongitudinal,
    ResultadoELUNormal,
    SecaoRetangular,
    verificar_elu_solicitacoes_normais,
)
from calc_core.sapata_isolada.materiais import Aco, Concreto

__all__ = [
    "METODO_DE_SEGURANCA_DO_PILARETE",
    "exigir_valores_de_calculo",
    "DadosDoPilarete",
    "ResultadoPilarete",
    "verificar_pilarete",
]

METODO_DE_SEGURANCA_DO_PILARETE = "calculo"
"""Único método de segurança aceito pelo pilarete: valores DE CÁLCULO.

Ref.: ABNT NBR 6118:2023, itens 11.7 e 12.3.3, p. 66 e 70
[req: REQ-PILARETE-14-proibicao-de-mistura-de-metodo-e-de-majoracao-por-vento]

COLISÃO DE MÉTODO DE SEGURANÇA, e esta é a primeira versão em que ela fica
perigosa de verdade, porque passam a coexistir no mesmo software um bloco
``admissivel`` (geotécnico: valores CARACTERÍSTICOS + FS global da NBR 6122,
Tabela 1) e um bloco inteiramente ``calculo`` (pilarete: gamma_f/gamma_m da
NBR 6118). A API do pilarete aceita SOMENTE valores de cálculo, o parâmetro
carrega o metadado do método, e receber valor característico é ERRO
EXPLÍCITO — o software NÃO multiplica por 1,4 sozinho.

É PROIBIDO comparar qualquer grandeza do pilarete com tensão admissível do
solo, e é PROIBIDO alimentar o pilarete com o N usado na verificação
geotécnica de ELS.

E É PROIBIDO MAJORAR RESISTÊNCIA POR VENTO: as regras NBR 6122 §6.3.2
(15 %/30 %) e §6.3.3 (10 %) são EXCLUSIVAS da tensão do SOLO. O vento entra no
pilarete pelos coeficientes de combinação das ações (NBR 8681/NBR 6118 §11) e
só. Uma referência a 6.3.2/6.3.3 em ``calc_core/estrutural/`` é veto do a6.
"""


def exigir_valores_de_calculo(metodo_de_seguranca: str) -> str:
    """Recusa qualquer método que não seja 'calculo'. Não converte nada.

    Ref.: ABNT NBR 6118:2023, item 12.3.3, p. 70
    [rule: NBR6118-12.3.3-12.4.1-valores-de-calculo]
    [req: REQ-PILARETE-14-proibicao-de-mistura-de-metodo-e-de-majoracao-por-vento]

    O metadado viaja com a entrada, como já se faz em REQ-SIGMA-01/02 do motor
    geotécnico. Receber valor característico é ERRO, não conversão automática:
    multiplicar por um gamma_f suposto seria inventar a composição da
    combinação, que este software não conhece.
    """
    if metodo_de_seguranca != METODO_DE_SEGURANCA_DO_PILARETE:
        raise RecusaForaDeDominio(
            parametro="metodo_de_seguranca",
            valor=metodo_de_seguranca,
            intervalo=f"= {METODO_DE_SEGURANCA_DO_PILARETE!r}",
            fonte="ABNT NBR 6118:2023, 12.3.3, p. 70 — a verificação de ELU do "
                  "pilarete é feita com valores DE CÁLCULO (ações majoradas por "
                  "gamma_f, resistências divididas por gamma_m)",
            forca=ESCOPO_DESTA_VERSAO,
            apoio_no_ruleset="NBR6118-12.3.3-12.4.1-valores-de-calculo",
            sugestao="É PROIBIDO alimentar o pilarete com o N característico da "
                     "verificação geotécnica de ELS (método 'admissivel' da NBR "
                     "6122, Tabela 1) e é PROIBIDO que este software multiplique "
                     "por 1,4 sozinho. Combine as ações fora e informe N_d, "
                     "M_Sd,x e M_Sd,y de cálculo.",
        )
    return metodo_de_seguranca


@dataclass(frozen=True)
class DadosDoPilarete:
    """Entradas do pilarete — todas EXPLÍCITAS, sem default silencioso.

    Ref.: ABNT NBR 6118:2023, itens 12.3.3, 13.2.3, 15.6, 17.4.2 e 21.6
    [req: REQ-PILARETE-02-entradas-explicitas-e-recusa-por-ausencia]
    [req: REQ-PILARETE-18-verificacao-de-forca-cortante]

    Os campos com valor ``None`` NÃO são opcionais no sentido usual: são os
    que dependem de um ramo declarado (``ell_e_declarado`` só existe com
    ``VINCULADO_DOIS_EXTREMOS``; ``theta_biela_graus`` só com ``MODELO_II``) e
    cuja ausência no ramo errado é RECUSA nomeando o campo e o item.

    GUARDA DE UNIDADE NO NOME DO PARÂMETRO, porque a checagem dimensional NÃO
    pega estes erros: ``_m`` para metros, ``_mm`` para milímetros, ``_MPa``
    para megapascal. ``h_secao``/``b_secao``/``ell`` em METROS; diâmetros e
    espaçamentos em MILÍMETROS; forças em kN e momentos em kN·m.
    """

    # --- geometria e vinculação (13.2.3, 15.6, 15.8.2) --------------------
    h_secao: float
    b_secao: float
    ell: float
    vinculacao: str
    secao_constante: bool | None
    armadura_constante: bool | None

    # --- materiais (8.2.10.1, 8.3.5, 12.3.1, 12.4.1) ----------------------
    f_ck_MPa: float
    gamma_c_base: float
    condicoes_desfavoraveis_de_execucao: bool | None
    f_yk_longitudinal_MPa: float
    f_yk_estribo_MPa: float
    gamma_s: float
    idade_maior_ou_igual_28_dias: bool | None

    # --- durabilidade e detalhamento (Tab. 7.2, 18.4.2, 18.4.3) -----------
    classe_de_agressividade: str
    d_agregado_mm: float
    cobrimento_declarado_mm: float
    phi_longitudinal_mm: float
    numero_de_barras: int
    espacamento_entre_eixos_mm: float
    phi_t_mm: float
    s_estribo_mm: float
    barras: tuple[BarraLongitudinal, ...]

    # --- solicitações DE CÁLCULO (REQ-PILARETE-14) ------------------------
    N_d: float
    M_Sd_x: float
    M_Sd_y: float
    H_x: float
    H_y: float
    metodo_de_seguranca: str = METODO_DE_SEGURANCA_DO_PILARETE

    # --- ligação com a sapata (9.5.2.x, 21.6) -----------------------------
    tipo_de_junta: str | None = None
    boa_aderencia: bool | None = None
    armadura_tracionada_em_alguma_combinacao: bool | None = None
    A_s_calculada: float | None = None

    # --- cortante (17.4), só usados na FAIXA A -----------------------------
    modelo_de_calculo: str | None = None
    theta_biela_graus: float | None = None
    alpha_estribo_graus: float | None = None
    A_sw_por_s: float | None = None
    N_gamma_f_1: float | None = None
    normal_de_compressao_em_todas_as_combinacoes: bool = False

    # --- ramo VINCULADO_DOIS_EXTREMOS (15.6) -------------------------------
    ell_e_declarado: float | None = None
    ell_0: float | None = None


@dataclass(frozen=True)
class ResultadoPilarete:
    """Tudo que o memorial de REQ-PILARETE-12 é obrigado a dizer.

    Ref.: ABNT NBR 6118:2023, itens 17.2.1, 17.4.2.1 e 14.4.1, p. 120, 136 e 83
    [req: REQ-PILARETE-12-memorial-e-o-que-ele-e-obrigado-a-dizer]
    [req: REQ-PILARETE-16-escopo-do-veredito-e-o-cortante-nao-verificado]
    """

    faixa: str
    """Um de :data:`~calc_core.estrutural.pilarete.classificacao.FAIXAS`.

    CAMPO PRÓPRIO, não texto: um consumidor programático tem de distinguir as
    duas faixas sem interpretar string (REQ-PILARETE-16-i).
    """
    classificacao: classificacao_14_4_1.ResultadoClassificacao
    dimensoes: ResultadoDimensoesLimites
    esbeltez: ResultadoEsbeltez
    junta: ligacao_9_5_21_6.ResultadoJunta
    traspasse: ligacao_9_5_21_6.ResultadoTraspasse
    exigencias_da_emenda: tuple[str, ...]
    elu_normal: ResultadoELUNormal
    elu_cortante: cortante_17_4.ResultadoCortante | None
    """``None`` na FAIXA B — e ali §17.4 foi RECUSADO, não "não aplicável"."""
    armadura_longitudinal: detalhamento_18.ResultadoArmaduraLongitudinal
    estribos: detalhamento_18.ResultadoEstribos
    cobrimento_minimo_mm: float
    cobrimento_declarado_mm: float
    atende_cobrimento: bool
    consistencia_de_cobrimento: ConsistenciaDeCobrimento
    """Cruzamento cobrimento DECLARADO × IMPLÍCITO nas posições das barras.

    Ref.: ABNT NBR 6118:2023, item 7.4.7.5 e Tabela 7.2, nota (d), p. 20
    [rule: NBR6118-Tab7.2-nota-d-cobrimento-pilarete]
    [req: REQ-PILARETE-09-cobrimento-proprio-e-a-incompatibilidade-com-Sapata]

    Se este campo existe, o cruzamento PASSOU — ele é feito por
    :func:`~calc_core.estrutural.pilarete.geometria.exigir_cobrimento_consistente_com_as_barras`
    ANTES de §17.2 e de §17.4, e o caso inconsistente RECUSA em vez de chegar
    até aqui. Guardá-lo no resultado é o que põe os três números no memorial:
    um cruzamento que não aparece no memorial é indistinguível de um
    cruzamento que não existe.
    """
    gamma_c_usado: float
    gamma_s_usado: float
    correcao_12_4_1_aplicada: bool
    gamma_n: float
    gamma_n_aplicado: bool
    N_d_majorado: float
    M_Sd_x_majorado: float
    M_Sd_y_majorado: float
    M_1d_min_xx: float
    M_1d_min_yy: float
    M_Sd_max_x: float
    """max(|M_Sd,x|, M_1d,mín,xx) — o de CÁLCULO usado no veredito [kN·m]."""
    M_Sd_max_y: float
    hipoteses_declaradas: tuple[str, ...] = field(default_factory=tuple)

    @property
    def atendido(self) -> bool:
        """Conjunção do que foi verificado na FAIXA correspondente.

        Ref.: ABNT NBR 6118:2023, itens 17.2.1 e 17.4.2.1, p. 120 e 136
        [rule: NBR6118-17.2.1-envoltoria-criterio-de-seguranca]
        [rule: NBR6118-17.4.2.1-duas-condicoes-simultaneas-do-ELU-de-cortante]
        [req: REQ-PILARETE-16-escopo-do-veredito-e-o-cortante-nao-verificado]

        FAIXA A: §17.2 **e** §17.4 **e** detalhamento.
        FAIXA B: §17.2 **e** detalhamento — o cortante NÃO entra porque NÃO
        FOI VERIFICADO, e é PROIBIDO tratá-lo como atendido por omissão.
        """
        parcelas = [self.elu_normal.atendido,
                    self.armadura_longitudinal.atendido,
                    self.estribos.atendido,
                    self.atende_cobrimento]
        if self.elu_cortante is not None:
            parcelas.append(self.elu_cortante.atendido)
        return all(parcelas)

    @property
    def nome_do_veredito(self) -> str:
        """Nome EXATO do veredito, e ele DEPENDE DA FAIXA.

        Ref.: ABNT NBR 6118:2023, itens 17.2.1 e 17.4.2.1, p. 120 e 136
        [rule: NBR6118-14.4.1-elemento-linear-classificacao]
        [deriv: DER-NBR6118-14.4.1-faixa-B-recusa-do-cortante]
        [req: REQ-PILARETE-16-escopo-do-veredito-e-o-cortante-nao-verificado]

        FAIXA A: "ELU de solicitações NORMAIS (NBR 6118:2023, 17.2.1) e ELU de
        FORÇA CORTANTE (NBR 6118:2023, 17.4.2.1): ATENDIDO / NÃO ATENDIDO".
        FAIXA B: "ELU de solicitações NORMAIS (NBR 6118:2023, 17.2.1):
        ATENDIDO / NÃO ATENDIDO".

        CONTINUA PROIBIDO "APROVADO", "OK", "pilarete verificado" ou qualquer
        formulação que um leitor apressado leia como aprovação do ELEMENTO.
        """
        estado = "ATENDIDO" if self.atendido else "NÃO ATENDIDO"
        if self.faixa == classificacao_14_4_1.FAIXA_A_ELEMENTO_LINEAR:
            return ("ELU de solicitações NORMAIS (NBR 6118:2023, 17.2.1) e ELU "
                    f"de FORÇA CORTANTE (NBR 6118:2023, 17.4.2.1): {estado}")
        return f"ELU de solicitações NORMAIS (NBR 6118:2023, 17.2.1): {estado}"

    def memorial(self) -> tuple[str, ...]:
        """Linhas do memorial, na ordem das alíneas de REQ-PILARETE-12.

        Ref.: ABNT NBR 6118:2023, itens 11.3.3.4.3, 12.4.1, 13.2.3, 14.4.1,
        15.8.2, 16.3, 17.2.1, 17.2.5, 17.4.2.1 e 21.6
        [rule: NBR6118-16.3-proibicao-de-carga-centrada]
        [rule: NBR6118-11.3.3.4.3-fig11.3-envoltoria-minima-1a-ordem]
        [req: REQ-PILARETE-12-memorial-e-o-que-ele-e-obrigado-a-dizer]

        Cada linha carrega item normativo e página — é isso que torna o
        memorial auditável sem o código ao lado. As alíneas cobertas: (a) itens
        com página; (b) M_1d,mín e a frase de 16.3; (c) lambda/lambda_1/i/ell_e
        por direção; (d) N_Rd0 e nu rotulados INFORMATIVOS; (e) gamma_c,
        gamma_s e a correção de 12.4.1; (f) junta, H e a declaração; (g)
        hipóteses; (h) a (k) os momentos resistentes, domínios e índices; (m) a
        razão de 14.4.1 e a FAIXA; (n) a (r) o cortante na FAIXA A; (s) as duas
        frases na FAIXA B.
        """
        linhas: list[str] = [self.nome_do_veredito]

        # (m) — a razão de 14.4.1 vai ao memorial nas DUAS faixas, com número.
        linhas.append(
            "NBR 6118:2023, 14.4.1 (p. 83): razão comprimento/maior dimensão "
            f"da seção = {self.classificacao.razao_14_4_1:.4f} contra o limite "
            f"de {classificacao_14_4_1.LIMITE_14_4_1:.1f} -> {self.faixa}. "
            "ATENÇÃO: esta verificação é INDEPENDENTE de lambda < lambda_1 "
            "(15.8.2) — uma decide a CLASSE do elemento, a outra a dispensa "
            "dos efeitos locais de 2ª ordem.")

        # (b) — M_1d,mín nas duas direções e a proibição de carga centrada.
        linhas.append(
            "NBR 6118:2023, 11.3.3.4.3 (p. 60) e Figura 11.3 (p. 61): "
            f"M_1d,mín,xx = {self.M_1d_min_xx:.4f} kN·m (usa h) e "
            f"M_1d,mín,yy = {self.M_1d_min_yy:.4f} kN·m (usa b).")
        linhas.append(FRASE_16_3)

        # (c) — esbeltez por direção, com a vinculação declarada.
        linhas.append(
            f"NBR 6118:2023, 15.8.2 (p. 107-108): vinculação declarada "
            f"{self.esbeltez.vinculacao}, ell = {self.esbeltez.ell:.4f} m, "
            f"ell_e = {self.esbeltez.ell_e:.4f} m, "
            f"alpha_b = {self.esbeltez.alpha_b:.2f}. "
            + self.esbeltez.justificativa_elemento_isolado)
        for direcao in self.esbeltez.direcoes:
            linhas.append(
                f"  direção {direcao.direcao}: i = {direcao.i_raio_de_giracao:.5f} m, "
                f"lambda = {direcao.lambda_esbeltez:.4f} < "
                f"lambda_1 = {direcao.lambda_1:.4f} "
                f"(e_1 = {direcao.e_1:.5f} m) — pilar curto por 15.8.2.")

        # (e) — coeficientes de ponderação efetivamente usados.
        linhas.append(
            f"NBR 6118:2023, Tabela 12.1 e 12.4.1 (p. 71): gamma_c = "
            f"{self.gamma_c_usado:.4f} (correção × 1,1 de 12.4.1 "
            f"{'APLICADA' if self.correcao_12_4_1_aplicada else 'não aplicada'}), "
            f"gamma_s = {self.gamma_s_usado:.4f}.")

        # 13.2.3 — gamma_n, com o valor, quando aplicado.
        if self.gamma_n_aplicado:
            linhas.append(
                "NBR 6118:2023, 13.2.3 e Tabela 13.1 (p. 73): menor dimensão "
                f"{self.dimensoes.b_min_cm:.2f} cm na faixa 14 a 19 cm — "
                f"gamma_n = 1,95 − 0,05·b = {self.gamma_n:.4f} APLICADO aos "
                f"esforços de cálculo (N_d = {self.N_d_majorado:.2f} kN, "
                f"M_Sd,x = {self.M_Sd_x_majorado:.2f} kN·m, "
                f"M_Sd,y = {self.M_Sd_y_majorado:.2f} kN·m).")
        else:
            linhas.append(
                "NBR 6118:2023, 13.2.3 e Tabela 13.1 (p. 73): menor dimensão "
                f"{self.dimensoes.b_min_cm:.2f} cm >= 19 cm, área "
                f"{self.dimensoes.area_cm2:.2f} cm² >= 360 cm² — gamma_n = 1,00 "
                "(não há majoração adicional).")

        # (d) e (h) a (k) — ELU de solicitações normais.
        linhas.append(
            f"NBR 6118:2023, 17.2.2-g) e Figura 17.1 (p. 122): N_Rd0 = "
            f"{self.elu_normal.N_Rd0_informativo:.2f} kN e nu = N_d/N_Rd0 = "
            f"{self.elu_normal.nu_informativo:.4f} — INFORMATIVOS. N_Rd0 é "
            "condição NECESSÁRIA e NÃO SUFICIENTE: ultrapassá-lo reprova, "
            "atendê-lo NÃO aprova.")
        for resultado in (self.elu_normal.resultado_xx,
                          self.elu_normal.resultado_yy):
            linhas.append(
                f"NBR 6118:2023, 17.2.2 (p. 120-122): M_Rd,{resultado.plano} = "
                f"{resultado.M_Rd_normal:.4f} kN·m para N_Sd = "
                f"{resultado.N_Sd:.2f} kN, com x = "
                f"{resultado.x_linha_neutra:.5f} m, polo {resultado.polo}, "
                f"{resultado.dominio}.")
        linhas.append(
            "NBR 6118:2023, 17.2.1 e 17.2.5 (p. 120 e 125): índice do par "
            "solicitante REAL I_A = |M_Sd,x|/M_Rd,xx + |M_Sd,y|/M_Rd,yy = "
            f"{self.elu_normal.indice_A_par_solicitante:.4f} "
            f"(alpha_interacao = {self.elu_normal.alpha_interacao_usado:.1f}).")
        linhas.append(
            "NBR 6118:2023, 11.3.3.4.3 e Figura 11.3 (p. 61): índice de "
            "inclusão da envoltória mínima I_B = "
            "sqrt((M_1d,mín,xx/M_Rd,xx)² + (M_1d,mín,yy/M_Rd,yy)²) = "
            f"{self.elu_normal.indice_B_envoltoria_minima:.4f}. As DUAS "
            "verificações são necessárias e nenhuma implica a outra.")
        linhas.append(
            "Índice do CANTO (atalho que só pode APROVAR, nunca reprovar) = "
            f"{self.elu_normal.indice_canto:.4f}"
            + (" — aprovou por atalho." if self.elu_normal.aprovado_por_atalho_do_canto
               else " — não aprovou por atalho; as verificações A e B foram "
                    "calculadas, como manda REQ-PILARETE-15(7)."))
        linhas.append(
            "A NBR 6118:2023, 17.2.5 (p. 125), escreve \"= 1\" e não \"<= 1\": "
            "a expressão descreve a SUPERFÍCIE da envoltória resistente, e ler "
            "o INTERIOR como conjunto admissível é INTERPRETAÇÃO declarada "
            "deste software [deriv: DER-NBR6118-17.2.5-criterio-menor-ou-igual"
            "-a-1].")
        linhas.append(
            f"alpha_interacao adotado = {self.elu_normal.alpha_interacao_usado:.1f}. "
            f"A NBR 6118:2023, 17.2.5 (p. 125), autorizaria "
            f"{ALPHA_INTERACAO_INFORMATIVO:.1f} para seção retangular, o que "
            f"daria I_A = "
            f"{self.elu_normal.indice_A_com_alpha_1_2_informativo:.4f} — "
            "informativo, NÃO usado no veredito.")

        # (f) — junta e H.
        linhas.extend(self.junta.declaracoes)
        linhas.append(
            f"Junta declarada: {self.junta.tipo_de_junta}; H_x = "
            f"{self.junta.H_x:.4f} kN e H_y = {self.junta.H_y:.4f} kN.")

        # Emenda por traspasse.
        linhas.append(
            "NBR 6118:2023, 9.5.2.3 (p. 44): ell_b = "
            f"{self.traspasse.ell_b * 1000.0:.1f} mm, ell_b,nec = "
            f"{self.traspasse.ell_b_nec * 1000.0:.1f} mm, mínimo de emenda "
            f"max(0,6·ell_b; 15·phi; 200 mm) = "
            f"{self.traspasse.ell_0c_minimo * 1000.0:.1f} mm -> ell_0c = "
            f"{self.traspasse.ell_0c * 1000.0:.1f} mm "
            f"(f_bd = {self.traspasse.f_bd_MPa:.4f} MPa, alpha_ancoragem = "
            f"{self.traspasse.alpha_ancoragem:.1f}).")
        linhas.extend(self.traspasse.declaracoes)
        linhas.extend(self.exigencias_da_emenda)

        # Detalhamento — armadura longitudinal.
        longitudinal = self.armadura_longitudinal
        linhas.append(
            "NBR 6118:2023, 17.3.5.3 (p. 133): A_s = "
            f"{longitudinal.A_s_adotada * 1e4:.2f} cm², A_s,mín = "
            f"{longitudinal.A_s_minima_valor * 1e4:.2f} cm², A_s,máx = "
            f"{longitudinal.A_s_maxima_valor * 1e4:.2f} cm²; na seção de EMENDA "
            f"a armadura duplicada dá {longitudinal.A_s_na_emenda * 1e4:.2f} "
            "cm², que também tem de caber nos 8 % de A_c.")
        linhas.extend(longitudinal.declaracoes)

        # (r) — detalhamento composto, com o valor de CADA fonte.
        for limite in (self.estribos.piso_phi_t, self.estribos.teto_phi_t,
                       self.estribos.teto_s, self.estribos.teto_s_transversal):
            if limite is not None:
                linhas.append("NBR 6118:2023, composição 18.4.3 × 18.3.3.2 "
                              "[deriv: DER-NBR6118-composicao-18.3.3.2-com-"
                              "18.4.3] — " + limite.descricao_para_memorial)
        linhas.extend(self.estribos.declaracoes)
        if self.estribos.nota_C55_a_C90 is not None:
            linhas.append(self.estribos.nota_C55_a_C90)

        # Cobrimento próprio do pilarete.
        linhas.append(
            "NBR 6118:2023, Tabela 7.2, nota (d) (p. 20): cobrimento nominal "
            f"mínimo do PILARETE = {self.cobrimento_minimo_mm:.1f} mm; "
            f"declarado {self.cobrimento_declarado_mm:.1f} mm — "
            + ("atende." if self.atende_cobrimento else "NÃO ATENDE.")
            + " Campo PRÓPRIO do pilarete, distinto do cobrimento da sapata, "
            "medido à face externa do ESTRIBO (7.4.7.5).")
        linhas.append(self.consistencia_de_cobrimento.linha_de_memorial)

        # (n) a (q) na FAIXA A; (s) na FAIXA B.
        if self.elu_cortante is not None:
            linhas.extend(self._linhas_do_cortante())
        else:
            primeira, segunda = (
                classificacao_14_4_1.frases_obrigatorias_da_faixa_B(
                    self.classificacao))
            linhas.append(primeira)
            linhas.append(segunda)
            if self.junta.H_resultante_declarada_nao_nula:
                linhas.append(
                    f"H declarado NÃO NULO (H_x = {self.junta.H_x:.4f} kN, "
                    f"H_y = {self.junta.H_y:.4f} kN) e, ainda assim, o ELU de "
                    "força cortante NÃO FOI VERIFICADO: " + primeira + " "
                    + segunda)
            linhas.append(
                "A verificação de §17.2 (solicitações normais) é aplicada a "
                "este elemento com base na remissão nominal a \"pilares\" de "
                "17.2.1 e na natureza de SEÇÃO da verificação — INTERPRETAÇÃO "
                "declarada [deriv: DER-NBR6118-14.4.1-faixa-B-recusa-do-"
                "cortante].")

        # (g) — hipóteses declaradas e o que NÃO foi verificado.
        linhas.extend(self.hipoteses_declaradas)
        linhas.append(
            "NÃO FORAM VERIFICADOS por esta versão: o ELS (fissuração, "
            "deformação), a fadiga, a torção (NBR 6118:2023, §17.5, não "
            "extraída) e a ligação com a sapata além da emenda por traspasse. "
            "Este software NÃO emite \"APROVADO\" nem \"pilarete OK\": o que "
            "está acima é o veredito dos itens nomeados, e a responsabilidade "
            "do projeto é do engenheiro que assina a ART.")
        return tuple(linhas)

    def _linhas_do_cortante(self) -> tuple[str, ...]:
        """Alíneas (n) a (q) de REQ-PILARETE-12 — só existem na FAIXA A.

        Ref.: ABNT NBR 6118:2023, itens 17.4.2.1 a 17.4.2.3, p. 136-139
        [rule: NBR6118-17.4.2.1-duas-condicoes-simultaneas-do-ELU-de-cortante]
        [req: REQ-PILARETE-12-memorial-e-o-que-ele-e-obrigado-a-dizer]  (n)-(q)
        """
        v = self.elu_cortante
        # NÃO é `assert`: `assert` some inteiro sob `python -O`, e o que
        # sobraria seria um AttributeError obscuro em `v.modelo_de_calculo` —
        # ou, pior, linhas de cortante meio formadas num memorial da FAIXA B,
        # onde §17.4 foi RECUSADO e não existe V_Rd2 nenhum. A guarda de uma
        # invariante que protege o memorial não pode depender do modo de
        # execução do interpretador.
        if v is None:
            raise RecusaForaDeDominio(
                parametro="elu_cortante",
                valor=None,
                intervalo="ResultadoCortante (só existe na FAIXA A de 14.4.1)",
                fonte="ABNT NBR 6118:2023, 14.4.1, p. 83 — fora da FAIXA A o "
                      "elemento não é linear e §17.4 NÃO se aplica: não há "
                      "cortante verificado para relatar",
                forca=DECLARADO_EM_TEXTO,
                apoio_no_ruleset="NBR6118-14.4.1-elemento-linear-classificacao",
                sugestao="Na FAIXA B o memorial traz as DUAS frases "
                         "obrigatórias de `frases_obrigatorias_da_faixa_B` em "
                         "vez destas linhas. É PROIBIDO redigir linhas de "
                         "cortante para um elemento cujo cortante NÃO FOI "
                         "VERIFICADO.")
        linhas = [
            f"NBR 6118:2023, 17.4.2 (p. 136-139): MODELO declarado "
            f"{v.modelo_de_calculo}"
            + (f", theta_biela = {v.theta_biela_graus:.2f}°"
               if v.theta_biela_graus is not None else "")
            + f", alpha_estribo = {v.alpha_estribo_graus:.1f}°. A escolha do "
              "modelo e de theta é do PROJETISTA: este software não a faz, não "
              "a otimiza e não varre theta.",
            f"Plano de verificação: {v.plano.plano}, V_Sd = {v.plano.V_Sd:.4f} "
            f"kN, b_w = {v.plano.b_w_no_plano_do_cortante:.4f} m, d = "
            f"{v.plano.d_util_no_plano_do_cortante:.4f} m "
            f"(alpha_v2 = {v.alpha_v2_valor:.4f}, f_ywd = {v.f_ywd_MPa:.1f} MPa "
            "com o teto de 435 MPa de 17.4.2.2-b).",
            f"V_Rd2 = {v.V_Rd2_valor:.4f} kN; V_c0 = {v.V_c0_valor:.4f} kN"
            + (f"; V_c1 = {v.V_c1_valor:.4f} kN" if v.V_c1_valor is not None
               else ("; V_c1 NÃO DEFINIDO (V_Sd > V_Rd2: a interpolação de "
                     "17.4.2.3-b) só existe entre V_c0 e V_Rd2)"
                     if v.V_c1_indefinido_por_V_Sd_acima_de_V_Rd2 else ""))
            + f"; V_c = {v.V_c_valor:.4f} kN; V_sw = {v.V_sw_valor:.4f} kN; "
              f"V_Rd3 = V_c + V_sw = {v.V_Rd3_valor:.4f} kN.",
            f"Estado da seção (17.4.2.2-b): {v.estado_da_secao}. "
            + ("Majoração de V_c pela compressão APLICADA"
               if v.majoracao_aplicada else
               "Majoração de V_c NÃO aplicada")
            + (f", com o teto de 2·V_c {'GOVERNANDO' if v.teto_2Vc_governou else 'não governando'}."
               if v.majoracao_aplicada else "."),
            f"VEREDITO DE CORTANTE (17.4.2.1): V_Sd <= V_Rd2 "
            f"{'ATENDIDA' if v.condicao_biela_atendida else 'NÃO ATENDIDA'} e "
            f"V_Sd <= V_Rd3 "
            f"{'ATENDIDA' if v.condicao_trelica_atendida else 'NÃO ATENDIDA'} "
            "— as DUAS condições são necessárias.",
            f"NBR 6118:2023, 17.4.1.1.1 (p. 134): rho_sw adotada = "
            f"{v.rho_sw_adotada:.6f} contra rho_sw,mín = 0,2·f_ct,m/f_ywk = "
            f"{v.rho_sw_minima:.6f} — "
            + ("atende." if v.rho_sw_adotada >= v.rho_sw_minima
               else "não atende pela taxa; ver a exceção de 17.4.1.1.2-c).")
            + f" Dispensa de 17.4.1.1.2-c): "
              f"{'APLICÁVEL' if v.dispensa.dispensada else 'NÃO aplicável'} "
              f"(condição (i) tensão de tração em estádio I = "
              f"{v.dispensa.tensao_de_tracao_estadio_I:.4f} MPa contra "
              f"f_ctk,inf = {v.dispensa.f_ctk_inf:.4f} MPa: "
              f"{'ok' if v.dispensa.condicao_i_atendida else 'não'}; "
              f"condição (ii) V_Sd <= V_c: "
              f"{'ok' if v.dispensa.condicao_ii_atendida else 'não'}).",
        ]
        if v.fibra_governante is not None:
            linhas.append(
                "NBR 6118:2023, 17.4.2.2-b) (p. 138) com "
                "[deriv: DER-NBR6118-17.4.2.2-W1-fibra-mais-tracionada]: "
                f"r_x = {v.fibra_x.razao:.4f} (W_1x = {v.fibra_x.W_1:.6f} m³, "
                f"M_0 = {v.fibra_x.M_0:.4f} kN·m, M_Sd,máx = "
                f"{v.fibra_x.M_Sd_max:.4f} kN·m) e r_y = {v.fibra_y.razao:.4f} "
                f"(W_1y = {v.fibra_y.W_1:.6f} m³, M_0 = {v.fibra_y.M_0:.4f} "
                f"kN·m, M_Sd,máx = {v.fibra_y.M_Sd_max:.4f} kN·m); GOVERNOU a "
                f"fibra {v.fibra_governante.plano} (a MENOR razão, lado "
                "conservador). A Norma não declara qual fibra usar sob flexão "
                "oblíqua.")
        linhas.append(
            "NBR 6118:2023, 17.4.2.2-b) (p. 138) com "
            "[deriv: DER-NBR6118-17.4.2.2-M0-nivel-de-carregamento]: "
            + (f"N_(gamma_f=1,0) = {v.N_gamma_f_1:.2f} kN e N_d = "
               f"{self.N_d_majorado:.2f} kN, lado a lado. A Norma manda "
               "calcular a tensão que M_0 anula com gamma_f = 1,0, enquanto "
               "M_Sd,máx é de CÁLCULO — a fração mistura dois níveis de "
               "ponderação DE PROPÓSITO."
               if v.N_gamma_f_1 is not None else
               "N_(gamma_f=1,0) NÃO foi declarado, portanto a majoração de V_c "
               "pela compressão NÃO foi aplicada. É PROIBIDO obtê-lo dividindo "
               "N_d por um gamma_f suposto."))
        linhas.extend(v.dispensa.declaracoes)
        linhas.extend(v.ausencias_deliberadas)
        return tuple(linhas)


HIPOTESE_M1D_MIN_SUBSTITUI_IMPERFEICOES = (
    "HIPÓTESE DECLARADA: o momento mínimo de 1ª ordem de 11.3.3.4.3 substitui "
    "o efeito das imperfeições locais de 11.3.3.4.2. A Norma diz que ele "
    "\"pode\" substituí-las em estruturas reticuladas, e um pilarete isolado "
    "sob base metálica pode não ser parte de estrutura reticulada; a "
    "substituição é adotada por ser ~10× MAIS conservadora (para H = 1,0 m, a "
    "rota de 11.3.3.4.2 daria e_a = 2,5 mm contra os 24 mm de M_1d,mín/N_d)."
)

HIPOTESE_COBRIMENTO_NO_PILARETE_INTEIRO = (
    "HIPÓTESE DECLARADA: os 45 mm da nota (d) da Tabela 7.2 valem para \"o "
    "trecho dos pilares em contato com o solo junto aos elementos de "
    "fundação\", e a Norma NÃO diz onde esse trecho termina. Este software "
    "aplica o piso ao PILARETE INTEIRO, do topo da sapata ao topo do pilarete "
    "— lado conservador, e evita inventar uma cota de transição."
)

HIPOTESE_GAMMA_N_NAO_MAJORA_N_GAMMA_F_1 = (
    "HIPÓTESE DECLARADA: o gamma_n da Tabela 13.1 majora os ESFORÇOS DE "
    "CÁLCULO (N_d, M_Sd, H). Ele NÃO é aplicado a N_(gamma_f=1,0), que por "
    "definição está no nível de carregamento com gamma_f = 1,0 — a Norma não "
    "trata do cruzamento dos dois, e não majorar reduz M_0, reduz V_c e é o "
    "lado conservador."
)


def _hipoteses(dados: DadosDoPilarete, *, gamma_n_aplicado: bool) -> tuple[str, ...]:
    """Hipóteses declaradas que a alínea (g) de REQ-PILARETE-12 exige.

    Ref.: ABNT NBR 6118:2023, itens 11.3.3.4.2, 12.3.3, 9.3.2.1 e Tabela 7.2
    [req: REQ-PILARETE-12-memorial-e-o-que-ele-e-obrigado-a-dizer]  (g)
    """
    hipoteses = [
        "HIPÓTESE DECLARADA: verificação em idade j >= 28 dias (NBR 6118:2023, "
        "12.3.3-a, p. 70). A verificação em j < 28 dias exigiria beta_1 de "
        "12.3.3-b) e dupla verificação, fora do escopo desta versão.",
        "HIPÓTESE DECLARADA: situação de aderência "
        + ("BOA (eta_2 = 1,0)" if dados.boa_aderencia else "MÁ (eta_2 = 0,7)")
        + " na espera, conforme 9.3.2.1 (p. 33) — DECLARADA pelo usuário, "
          "nunca assumida.",
        HIPOTESE_COBRIMENTO_NO_PILARETE_INTEIRO,
        HIPOTESE_M1D_MIN_SUBSTITUI_IMPERFEICOES,
    ]
    if gamma_n_aplicado:
        hipoteses.append(HIPOTESE_GAMMA_N_NAO_MAJORA_N_GAMMA_F_1)
    return tuple(hipoteses)


def verificar_pilarete(dados: DadosDoPilarete) -> ResultadoPilarete:
    """Verificação completa do pilarete, na ORDEM das guardas. RECUSA cedo.

    Ref.: ABNT NBR 6118:2023, itens 12.3.3, 13.2.3, 21.6, 15.8.2, 14.4.1,
    17.2 e 17.4, p. 70, 73, 181, 107-108, 83, 120-125 e 133-139
    [rule: NBR6118-13.2.3-dimensoes-limites-pilarete]
    [rule: NBR6118-15.8.2-dispensa-2a-ordem-local]
    [rule: NBR6118-14.4.1-elemento-linear-classificacao]
    [rule: NBR6118-17.2.1-envoltoria-criterio-de-seguranca]
    [rule: NBR6118-21.6-junta-de-concretagem-pilarete-sapata]
    [req: REQ-PILARETE-15-veredito-de-ELU-de-solicitacoes-normais]
    [req: REQ-PILARETE-16-escopo-do-veredito-e-o-cortante-nao-verificado]
    [req: REQ-PILARETE-17-guarda-de-elemento-linear-14.4.1]

    A ORDEM É A DO REQUISITO e cada passo tem seu próprio motivo de recusa:

    1. método de segurança = 'calculo' (REQ-PILARETE-14) e j >= 28 dias
       (12.3.3-b, REQ-PILARETE-06-D);
    2. 13.2.3 — b >= 14 cm, A_c >= 360 cm², gamma_n, e 18.4.1 (pilar-parede);
       os esforços de cálculo são MAJORADOS por gamma_n aqui, uma única vez;
    3. 21.6 — a junta, com as DUAS recusas duras;
    4. 11.3.3.4.3 — M_1d,mín nas DUAS direções, sempre, a partir do N_d já
       majorado; não existe caminho de compressão centrada (16.3);
    5. 15.8.1/15.8.2 — pilar curto, com lambda < lambda_1 ESTRITO;
    6. 14.4.1 — a FAIXA, que decide se §17.4 existe para este elemento;
    6-bis. 7.4.7.5 — o CRUZAMENTO entre o cobrimento declarado e o implícito
       nas posições das barras (REQ-PILARETE-09). Vem antes de 7 e de 8 porque
       é dali que saem os braços de alavanca de §17.2 e o d' de §17.4: nenhum
       número pode sair de uma geometria de armadura incoerente com o
       cobrimento declarado;
    7. 17.2 — o veredito de solicitações normais, SEMPRE, nas duas faixas;
    8. 17.4 — só na FAIXA A; na FAIXA B a chamada nem é feita, e o memorial
       traz as duas frases obrigatórias em vez de um "não aplicável";
    9. detalhamento composto (18.4.2, 18.4.3, 18.3.3.2 e 9.5.2.3).

    NÃO EXISTE, e não pode existir, caminho de "compressão centrada pura":
    mesmo com ``M_Sd_x = M_Sd_y = 0`` o veredito é calculado contra a
    envoltória mínima de 11.3.3.4.3, porque 16.3 (p. 116) diz literalmente que
    "não se aceita o dimensionamento de pilares para carga centrada".
    """
    # (1) método de segurança e idade.
    exigir_valores_de_calculo(dados.metodo_de_seguranca)
    exigir_idade_28_dias(dados.idade_maior_ou_igual_28_dias)
    exigir_classe_normalizada(dados.f_ck_MPa)
    exigir_declarado(
        "boa_aderencia", dados.boa_aderencia,
        fonte="ABNT NBR 6118:2023, 9.3.2.1, p. 33 — eta_2 = 1,0 (boa) ou 0,7 "
              "(má) é situação de aderência, decisão de execução",
        apoio_no_ruleset="NBR6118-9.4.2.4-lb-basico",
        sugestao="Declare a situação de aderência da espera. Assumir 'boa' "
                 "silenciosamente subestimaria o comprimento de traspasse.")
    exigir_declarado(
        "armadura_tracionada_em_alguma_combinacao",
        dados.armadura_tracionada_em_alguma_combinacao,
        fonte="ABNT NBR 6118:2023, 9.5.2.1, p. 43 — a autorização de emendar "
              "100 % das barras na mesma seção depende de a armadura ser "
              "PERMANENTEMENTE COMPRIMIDA",
        apoio_no_ruleset="NBR6118-9.5.2.1-emenda-100-por-cento-comprimida",
        sugestao="A hipótese é sobre o ESFORÇO, não sobre o elemento: é "
                 "PROIBIDO assumi-la porque 'é pilar'.")

    gamma_c = gamma_c_com_correcao_12_4_1(
        dados.gamma_c_base, dados.condicoes_desfavoraveis_de_execucao)
    concreto = Concreto(fck=dados.f_ck_MPa, gamma_c=gamma_c)
    aco_longitudinal = Aco(fyk=dados.f_yk_longitudinal_MPa,
                           gamma_s=dados.gamma_s)
    aco_do_estribo = Aco(fyk=dados.f_yk_estribo_MPa, gamma_s=dados.gamma_s)

    # (2) 13.2.3 + 18.4.1, e a majoração por gamma_n dos esforços de cálculo.
    dimensoes = verificar_dimensoes_limites(h_secao=dados.h_secao,
                                            b_secao=dados.b_secao)
    gamma_n = dimensoes.gamma_n
    N_d = dados.N_d * gamma_n
    M_Sd_x = dados.M_Sd_x * gamma_n
    M_Sd_y = dados.M_Sd_y * gamma_n
    H_x = dados.H_x * gamma_n
    H_y = dados.H_y * gamma_n

    # (3) 21.6 — a junta. O gatilho de H != 0 usa o H DECLARADO: gamma_n é
    # multiplicativo e não transforma zero em não zero, mas é o declarado que
    # a mensagem tem de citar.
    junta = ligacao_9_5_21_6.verificar_junta(
        tipo_de_junta=dados.tipo_de_junta, H_x=dados.H_x, H_y=dados.H_y)

    # (4) 11.3.3.4.3 nas DUAS direções, do N_d já majorado.
    M_1d_min_xx = momento_minimo_1a_ordem(N_d, dados.h_secao)
    M_1d_min_yy = momento_minimo_1a_ordem(N_d, dados.b_secao)

    # (5) 15.8.1/15.8.2 — pilar curto.
    esbeltez = verificar_pilar_curto(
        vinculacao=dados.vinculacao, ell=dados.ell, h_secao=dados.h_secao,
        b_secao=dados.b_secao, N_d=N_d, M_1d_x=M_Sd_x, M_1d_y=M_Sd_y,
        M_1d_min_xx=M_1d_min_xx, M_1d_min_yy=M_1d_min_yy,
        f_cd_MPa=concreto.fcd, secao_constante=dados.secao_constante,
        armadura_constante=dados.armadura_constante,
        ell_e_declarado=dados.ell_e_declarado, ell_0=dados.ell_0)

    # (6) 14.4.1 — a FAIXA. NUNCA com ell_e.
    classificacao = classificacao_14_4_1.classificar_faixa(
        ell=dados.ell, h_secao=dados.h_secao, b_secao=dados.b_secao)

    # (6-bis) 7.4.7.5 — CRUZAMENTO do cobrimento declarado com as posições
    # declaradas das barras, e ele vem ANTES de (7) e (8) de propósito.
    #
    # As posições das barras são a ÚNICA fonte da geometria da armadura para os
    # dois passos seguintes: §17.2 usa `dados.barras` nos braços de alavanca da
    # varredura de M_Rd e §17.4 usa o d' delas em V_Rd2 e V_c0. O cobrimento
    # declarado, até aqui, só era comparado ISOLADAMENTE contra o mínimo da
    # Tabela 7.2 (`atende_cobrimento`, lá embaixo) — os dois canais descreviam a
    # MESMA distância física e nunca se encontravam. Declarar c = 45 mm e
    # posicionar as barras como se fosse 30 mm dava d maior, V_Rd2 maior, M_Rd
    # maior e veredito ATENDIDO, do lado INSEGURO e em silêncio.
    #
    # Por isso o cruzamento é feito AQUI e não na montagem do resultado: RECUSA
    # ANTES de qualquer número sair de uma geometria incoerente, e vale nas DUAS
    # faixas (a FAIXA B não chama §17.4, mas chama §17.2, que usa as mesmas
    # barras). O d' é calculado uma vez só, e é o MESMO que (8) consome.
    cobrimento_minimo = cobrimento_nominal_minimo(
        classe_de_agressividade=dados.classe_de_agressividade,
        phi_longitudinal_mm=dados.phi_longitudinal_mm,
        d_agregado_mm=dados.d_agregado_mm)
    d_linha_h, d_linha_b = _distancias_ao_centroide_das_barras(dados)
    consistencia_de_cobrimento = exigir_cobrimento_consistente_com_as_barras(
        d_linha_no_plano_de_h=d_linha_h, d_linha_no_plano_de_b=d_linha_b,
        phi_longitudinal_mm=dados.phi_longitudinal_mm,
        phi_t_mm=dados.phi_t_mm,
        cobrimento_declarado_mm=dados.cobrimento_declarado_mm,
        cobrimento_minimo_mm=cobrimento_minimo)

    # (7) 17.2 — o veredito de solicitações normais, nas duas faixas.
    secao = SecaoRetangular(h_secao=dados.h_secao, b_secao=dados.b_secao,
                            barras=dados.barras, concreto=concreto,
                            aco=aco_longitudinal)
    elu_normal = verificar_elu_solicitacoes_normais(
        secao, N_Sd=N_d, M_Sd_x=M_Sd_x, M_Sd_y=M_Sd_y,
        M_1d_min_xx=M_1d_min_xx, M_1d_min_yy=M_1d_min_yy)

    # Os M_Sd,máx do veredito — os mesmos que alimentam M_0 no cortante.
    M_Sd_max_x = max(abs(M_Sd_x), M_1d_min_xx)
    M_Sd_max_y = max(abs(M_Sd_y), M_1d_min_yy)

    # (8) 17.4 — SÓ na FAIXA A. Na FAIXA B nem se chama: §17.4 foi RECUSADO,
    # e um V_Rd2 calculado "só para o relatório" é defeito com veto do a6.
    elu_cortante = None
    d_util_para_detalhamento = None
    V_Sd_para_detalhamento = None
    V_Rd2_para_detalhamento = None
    if classificacao.faixa == classificacao_14_4_1.FAIXA_A_ELEMENTO_LINEAR:
        # d_linha_h/d_linha_b vêm de (6-bis), já cruzados com o cobrimento
        # declarado. Não se recalculam aqui: recalcular reabriria a porta de
        # um caminho que chega a V_Rd2 sem o cruzamento ter passado.
        elu_cortante = cortante_17_4.verificar(
            classificacao=classificacao, concreto=concreto,
            aco_do_estribo=aco_do_estribo, h_secao=dados.h_secao,
            b_secao=dados.b_secao, d_linha_no_plano_de_h=d_linha_h,
            d_linha_no_plano_de_b=d_linha_b, H_x=H_x, H_y=H_y, N_d=N_d,
            M_Sd_max_x=M_Sd_max_x, M_Sd_max_y=M_Sd_max_y,
            modelo_de_calculo=dados.modelo_de_calculo,
            theta_biela_graus=dados.theta_biela_graus,
            alpha_estribo_graus=dados.alpha_estribo_graus,
            A_sw_por_s=dados.A_sw_por_s, N_gamma_f_1=dados.N_gamma_f_1,
            normal_de_compressao_em_todas_as_combinacoes=(
                dados.normal_de_compressao_em_todas_as_combinacoes))
        d_util_para_detalhamento = (
            elu_cortante.plano.d_util_no_plano_do_cortante)
        V_Sd_para_detalhamento = elu_cortante.plano.V_Sd
        V_Rd2_para_detalhamento = elu_cortante.V_Rd2_valor

    # (9) detalhamento e ligação.
    A_s_efetiva = secao.A_s_total
    longitudinal = detalhamento_18.verificar_armadura_longitudinal(
        A_s_adotada=A_s_efetiva, numero_de_barras=dados.numero_de_barras,
        phi_longitudinal_mm=dados.phi_longitudinal_mm, N_d=N_d,
        f_yd_MPa=aco_longitudinal.fyd, h_secao=dados.h_secao,
        b_secao=dados.b_secao, d_agregado_mm=dados.d_agregado_mm,
        espacamento_entre_eixos_mm=dados.espacamento_entre_eixos_mm)
    estribos = detalhamento_18.verificar_estribos(
        concreto=concreto, aco_longitudinal=aco_longitudinal,
        phi_longitudinal_mm=dados.phi_longitudinal_mm,
        phi_t_mm=dados.phi_t_mm, s_adotado_mm=dados.s_estribo_mm,
        h_secao=dados.h_secao, b_secao=dados.b_secao,
        d_util_no_plano_do_cortante=d_util_para_detalhamento,
        V_Sd=V_Sd_para_detalhamento, V_Rd2_valor=V_Rd2_para_detalhamento,
        # "Mesmo tipo de aço nas duas armaduras" é a condição que 18.4.3 impõe
        # para OFERECER a alternativa phi_t < phi/4. Aqui ela é DEDUZIDA das
        # categorias declaradas (não é default): se o projetista declarou
        # CA-50 no longitudinal e CA-25 no estribo, a alternativa não existe e
        # o piso de phi/4 continua valendo.
        mesmo_aco_nas_duas_armaduras=(
            aco_longitudinal.categoria == aco_do_estribo.categoria))
    traspasse = ligacao_9_5_21_6.comprimento_de_traspasse(
        concreto=concreto, aco=aco_longitudinal,
        phi_mm=dados.phi_longitudinal_mm,
        boa_aderencia=bool(dados.boa_aderencia),
        armadura_tracionada_em_alguma_combinacao=bool(
            dados.armadura_tracionada_em_alguma_combinacao),
        A_s_calculada=(dados.A_s_calculada if dados.A_s_calculada is not None
                       else A_s_efetiva),
        A_s_efetiva=A_s_efetiva)
    exigencias = ligacao_9_5_21_6.exigencias_de_armadura_transversal_da_emenda(
        phi_mm=dados.phi_longitudinal_mm, ell_0c=traspasse.ell_0c)

    # cobrimento_minimo já foi calculado em (6-bis) — é o mesmo número que
    # entrou no cruzamento, e calcular duas vezes só criaria a chance de
    # divergirem.
    return ResultadoPilarete(
        faixa=classificacao.faixa,
        classificacao=classificacao,
        dimensoes=dimensoes,
        esbeltez=esbeltez,
        junta=junta,
        traspasse=traspasse,
        exigencias_da_emenda=exigencias,
        elu_normal=elu_normal,
        elu_cortante=elu_cortante,
        armadura_longitudinal=longitudinal,
        estribos=estribos,
        cobrimento_minimo_mm=cobrimento_minimo,
        cobrimento_declarado_mm=dados.cobrimento_declarado_mm,
        atende_cobrimento=dados.cobrimento_declarado_mm >= cobrimento_minimo,
        consistencia_de_cobrimento=consistencia_de_cobrimento,
        gamma_c_usado=gamma_c,
        gamma_s_usado=dados.gamma_s,
        correcao_12_4_1_aplicada=bool(dados.condicoes_desfavoraveis_de_execucao),
        gamma_n=gamma_n,
        gamma_n_aplicado=dimensoes.gamma_n_aplicado,
        N_d_majorado=N_d,
        M_Sd_x_majorado=M_Sd_x,
        M_Sd_y_majorado=M_Sd_y,
        M_1d_min_xx=M_1d_min_xx,
        M_1d_min_yy=M_1d_min_yy,
        M_Sd_max_x=M_Sd_max_x,
        M_Sd_max_y=M_Sd_max_y,
        hipoteses_declaradas=_hipoteses(
            dados, gamma_n_aplicado=dimensoes.gamma_n_aplicado),
    )


def _distancias_ao_centroide_das_barras(
    dados: DadosDoPilarete,
) -> tuple[float, float]:
    """d' em cada plano, a partir das POSIÇÕES DECLARADAS das barras [m].

    Ref.: ABNT NBR 6118:2023, item 17.4.2.2, alínea a), p. 136 (com Em1:2026)
    [rule: NBR6118-17.4.2.2-modelo-I-VRd2-Vsw-Vc]

    ``d`` de §17.4 é a "distância da borda comprimida ao CENTROIDE da armadura
    de tração" na redação da Emenda 1:2026 (a de 2023 dizia "ao centro de
    gravidade da armadura de tração" — troca terminológica, sem efeito
    numérico). Aqui o d' é DEDUZIDO das posições declaradas das barras, e não
    de um cobrimento suposto: é a mesma geometria que alimenta o equilíbrio de
    seção de §17.2, o que impede que os dois módulos usem armaduras
    diferentes.

    A camada de armadura tomada é a MAIS AFASTADA da borda comprimida em cada
    plano, que é a tracionada na flexão daquele plano; com arranjo simétrico —
    verificado em :func:`verificar_elu_solicitacoes_normais` — as duas bordas
    dão o mesmo d'.
    """
    if not dados.barras:  # pragma: no cover - construção sem barras
        raise RecusaForaDeDominio(
            parametro="barras", valor=(),
            intervalo="ao menos uma barra por vértice (4 na seção retangular)",
            fonte="ABNT NBR 6118:2023, 18.4.2.2, p. 153",
            forca=DECLARADO_PELO_USUARIO,
            apoio_no_ruleset="NBR6118-18.4.2-armaduras-longitudinais-pilarete")
    d_linha_h = min(barra.pos_h for barra in dados.barras)
    d_linha_b = min(barra.pos_b for barra in dados.barras)
    return d_linha_h, d_linha_b
