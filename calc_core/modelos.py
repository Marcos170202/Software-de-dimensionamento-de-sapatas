"""Modelos de dados do núcleo — únicas estruturas que ui/ pode importar.

A regra do a3-interface.md é gerar formulário a partir destes modelos, nunca
escrever campos à mão. Usamos ``dataclasses`` da biblioteca padrão em vez de
Pydantic para manter o núcleo sem dependências externas (facilita empacotar
em .exe com PyInstaller sem inflar o binário).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EntradaSapataCentrada:
    """Entrada para o dimensionamento geométrico de sapata sob carga centrada.

    Unidades: kN para força, kPa para tensão, m para comprimento.
    """

    N_k: float
    """Carga vertical característica no topo da sapata, vinda do pilar [kN]."""

    sigma_adm: float
    """Tensão admissível (ou tensão resistente de cálculo) do terreno [kPa].

    Entrada do engenheiro — NBR 6122:2022 §7.2 lista doze fatores para
    fixá-la e este software não deduz nenhum deles de um perfil SPT.
    """

    pilar_a: float
    """Dimensão do pilar na direção X [m]."""

    pilar_b: float
    """Dimensão do pilar na direção Y [m]."""

    considerar_peso_proprio: bool = True
    """Se True, soma ao N_k uma estimativa de peso próprio (NBR 6122 §5.6)."""

    percentual_peso_proprio: float = 0.05
    """Percentual mínimo normativo do peso próprio sobre a carga permanente
    (NBR 6122 §5.6: "no mínimo 5%"). Sobrescrevível pelo engenheiro quando o
    peso próprio real (calculado a posteriori) for maior."""

    dimensao_minima: float = 0.60
    """Dimensão mínima em planta, NBR 6122:2022 §7.7.1 [m]."""

    modulo_arredondamento: float = 0.05
    """Incremento construtivo para arredondar B e L para cima [m]."""

    def __post_init__(self) -> None:
        if self.N_k <= 0:
            raise ValueError("N_k deve ser positivo (carga de compressão).")
        if self.sigma_adm <= 0:
            raise ValueError("sigma_adm deve ser positivo.")
        if self.pilar_a <= 0 or self.pilar_b <= 0:
            raise ValueError("Dimensões do pilar devem ser positivas.")
        if not (0 <= self.percentual_peso_proprio < 1):
            raise ValueError("percentual_peso_proprio deve estar em [0, 1).")
        if self.dimensao_minima <= 0:
            raise ValueError("dimensao_minima deve ser positiva.")
        if self.modulo_arredondamento <= 0:
            raise ValueError("modulo_arredondamento deve ser positivo.")


ROTULO_ELU = (
    "parcela de ELU da tensão admissível (NBR 6122:2022 §7.3) — "
    "§7.4 (ELS/recalque) NÃO verificado"
)
"""Rótulo OBRIGATÓRIO colado a todo valor produzido pelos caminhos da v9.

Ref.: ABNT NBR 6122:2022, itens 7.3 e 7.4, p. 22-23
[rule: NBR6122-7.3-7.4-conjuncao-ELU-ELS]

A definição 3.45 de "tensão admissível" é CONJUNTIVA (ELU **e** ELS) e nenhum
caminho aprovado na v9 verifica ELS. Chamar a saída de "tensão admissível
conforme a NBR 6122" — em variável, retorno, tela ou memorial — é anunciar
conformidade que o software não tem (REQ-SIGMA-09 / REQ-UI-SIGMA-01).
"""

ROTULO_FONTE_NAO_NORMATIVA = (
    "Formulação de CINTRA, AOKI e ALBIERO, 'Fundações Diretas: Projeto "
    "Geotécnico', Oficina de Textos, 2011 — fonte bibliográfica, NÃO "
    "normativa. A NBR 6122:2022 autoriza o procedimento (§7.3.2 / §7.3.3) "
    "mas não prescreve a fórmula."
)
"""Rótulo de origem das fórmulas da v9 (REQ-UI-SIGMA-02).

O memorial cita ``[pratica: <id>]``, nunca ``[rule: <id>]``, para tudo que
venha desta fonte.
"""

ADVERTENCIA_FORMULARIOS_DE_BOLSO = (
    "Advertência publicada pela própria fonte (Mello, 1975, p. 61): é preciso "
    "analisar a origem e a validade de tais 'formulários de bolso' antes de "
    "usá-los."
)
"""Advertência que acompanha as correlações semiempíricas (REQ-UI-SIGMA-02)."""

DECLARACAO_REGIONAL_EXIGIDA = (
    "Estas correlações são brasileiras e foram calibradas em solos do Sudeste "
    "— a própria fonte compara a Fig. 4.1 com valores de experiência prática "
    "em São Paulo, relatados por Vargas (1951). A NBR 6122:2022 §7.3.3 exige "
    "observar as limitações regionais de cada método e não define 'região'. O "
    "software não infere aplicabilidade regional de um perfil SPT: a "
    "declaração é do engenheiro e vai para o memorial."
)
"""Texto mínimo da declaração regional exigida por REQ-SIGMA-06."""


@dataclass(frozen=True)
class Verificacao:
    """Resultado de uma verificação normativa isolada, com rastreabilidade."""

    regra: str
    """ID da regra em ruleset.yaml, ex.: 'NBR6122-7.7.1-dimensao-minima'."""

    descricao: str
    """Frase curta do que foi verificado, para o semáforo da UI."""

    aplicavel: bool
    """False quando a entrada cai fora do domínio de validade da regra."""

    ok: bool | None
    """True/False se aplicável; None se não aplicável (aplicavel=False)."""

    mensagem: str = ""
    """Detalhe legível por humano — valores obtidos, limite, motivo."""


@dataclass(frozen=True)
class ResultadoGeometria:
    """Saída do dimensionamento geométrico de sapata sob carga centrada."""

    N_total: float
    """Carga total considerada (N_k + peso próprio estimado, se aplicável) [kN]."""

    area_necessaria: float
    """Área mínima exigida por N_total / sigma_adm [m²]."""

    B: float
    """Dimensão final em X, já arredondada e verificada contra o mínimo [m]."""

    L: float
    """Dimensão final em Y, já arredondada e verificada contra o mínimo [m]."""

    area_final: float
    """B * L [m²]."""

    tensao_atuante: float
    """N_total / area_final [kPa] — deve ser <= sigma_adm."""

    verificacoes: list[Verificacao] = field(default_factory=list)
    """Todas as verificações normativas aplicadas, para o memorial."""

    @property
    def aprovado(self) -> bool:
        """True se todas as verificações aplicáveis passaram."""
        return all(v.ok is not False for v in self.verificacoes)


# ===========================================================================
# v9 — parcela de ELU da tensão admissível (SPT/CPT e caminho teórico)
#
# Todos os modelos abaixo são PURAMENTE DADOS. As guardas de domínio que os
# validam vivem nos módulos de cálculo (``geotecnico.capacidade``,
# ``geotecnico.semiempirico``, ``geotecnico.vento``) e são executadas na
# entrada de cada função pública — nunca aqui, para que ``modelos`` continue
# sem importar nada de ``calc_core.geotecnico`` (ciclo de importação).
#
# UNIDADES NA FRONTEIRA: kPa para tensão, m para comprimento, kN/m³ para peso
# específico, graus para ângulo. Fórmulas cuja fonte está em MPa convertem num
# único ponto, dentro do módulo (REQ-SIGMA-03).
# ===========================================================================

FORMA_CORRIDA = "corrida"
FORMA_RETANGULAR = "retangular"
FORMA_QUADRADA = "quadrada"
FORMA_CIRCULAR = "circular"
FORMAS_DE_BEER = (FORMA_CORRIDA, FORMA_RETANGULAR, FORMA_QUADRADA,
                  FORMA_CIRCULAR)
"""Formas cobertas pela Tab. 2.3 (De Beer) — as únicas aprovadas na v9."""

RUPTURA_GERAL = "geral"
RUPTURA_PUNCIONAMENTO = "puncionamento"
MODOS_DE_RUPTURA = (RUPTURA_GERAL, RUPTURA_PUNCIONAMENTO)
"""Modos de ruptura admitidos (REQ-SIGMA-12). NÃO há terceira opção.

ARMADILHA DE NOMENCLATURA: o que TERZAGHI chamou de "ruptura local" é o que a
fonte desta versão chama de PUNCIONAMENTO. A interface não pode usar "ruptura
local" para nomear o puncionamento. A "ruptura local" dos autores (média
aritmética entre os dois modos) NÃO entra nesta versão.
"""

CARREGAMENTO_DRENADO = "drenado"
CARREGAMENTO_NAO_DRENADO = "nao_drenado"
NATUREZAS_DE_CARREGAMENTO = (CARREGAMENTO_DRENADO, CARREGAMENTO_NAO_DRENADO)
"""Natureza do carregamento, exigência normativa expressa do §7.3.2 (2022)."""


@dataclass(frozen=True)
class EntradaCapacidadeCarga:
    """Entrada do caminho teórico de capacidade de carga (Terzaghi/Vesic).

    Ref.: ABNT NBR 6122:2022, item 7.3.2, p. 22
    [rule: NBR6122-7.3.2-metodos-teoricos-condicao-2022] (autorização e
    condição suspensiva; a EQUAÇÃO não é normativa)
    [pratica: FB-CINTRA-TERZAGHI-VESIC-capacidade-de-carga] (origem da
    equação, fonte bibliográfica não normativa)

    c e phi são ENTRADA DIRETA DO ENGENHEIRO, em valores CARACTERÍSTICOS, e
    NÃO são derivados de N_SPT nesta versão (nota (b) da Tabela 1: "sem
    aplicação de coeficientes de ponderação aos parâmetros de resistência do
    terreno"). Registrar no memorial qual estatística de c e phi foi usada:
    alimentar a divisão por FSg com quantis inferiores conta segurança duas
    vezes, porque sigma_r é, por construção do FS global, um valor MÉDIO.
    """

    c_kPa: float
    """Coesão característica do solo [kPa]. c >= 0."""

    phi_graus: float
    """Ângulo de atrito interno característico [graus]. 0 <= phi <= 50."""

    B_m: float
    """Menor dimensão da base [m] (diâmetro, se circular). B > 0."""

    L_m: float
    """Maior dimensão da base [m]. L >= B."""

    h_m: float
    """Embutimento, da superfície à cota de apoio [m]. Exige h <= B."""

    gamma_acima_da_base_kN_m3: float
    """Peso específico EFETIVO acima da cota da base [kN/m³], usado em q = γ·h.

    Abaixo do nível d'água o valor é o EFETIVO (submerso, tipicamente
    9-11 kN/m³), NÃO o saturado (19-21 kN/m³): usar o saturado erra gamma por
    um fator de ~2, sempre do lado INSEGURO.
    """

    gamma_abaixo_da_base_kN_m3: float
    """Peso específico EFETIVO abaixo da base [kN/m³], usado em ½·γ·B·Nγ.

    Campo separado do anterior de propósito: a fonte avisa que os dois podem
    diferir apesar de aparecerem com o mesmo símbolo.
    """

    forma: str
    """Uma de ``FORMAS_DE_BEER``. Fatores de forma de De Beer (Tab. 2.3)."""

    modo_de_ruptura: str
    """``'geral'`` ou ``'puncionamento'``, DECLARADO pelo usuário."""

    natureza_do_carregamento: str
    """``'drenado'`` ou ``'nao_drenado'``, declarada (§7.3.2 de 2022)."""

    solo_homogeneo_no_bulbo_declarado: bool
    """Declaração de que o maciço no bulbo é HOMOGÊNEO (ou camada equivalente).

    Sem default: o caso estratificado está no item 2.5 da fonte, NÃO extraído
    em nenhuma rodada, e aplicar esta equação a perfil estratificado é o risco
    que o CLAUDE.md nomeia explicitamente.
    """

    metodo_de_seguranca: str = "admissivel"
    """Guarda de método (REQ-SIGMA-01). Único valor aceito nesta versão."""


@dataclass(frozen=True)
class EntradaSemiempiricaSPT:
    """Um caso de obra, avaliado por TODAS as correlações semiempíricas.

    Ref.: ABNT NBR 6122:2022, item 7.3.3, p. 22
    [rule: NBR6122-7.3.3-metodos-semiempiricos]

    Os campos ``h_m`` e ``gamma_kN_m3`` são pedidos mesmo para correlações que
    não os têm como variável: em Teixeira (1996) eles são hipóteses CONGELADAS
    na dedução, e existem aqui exatamente para poderem ser conferidos e
    RECUSADOS quando diferirem (h = 1,5 m e γ = 18 kN/m³, tolerância zero).
    """

    N_spt: float
    """N_SPT do caso [golpes]. Na regra N/50 é o valor MÉDIO NO BULBO de
    tensões, não o da cota de apoio; Teixeira (1996) não declara a
    profundidade de amostragem — ver os avisos de cada resultado."""

    B_m: float
    """Menor dimensão da base [m]. SEMPRE em metros (REQ-SIGMA-03 b)."""

    forma: str
    """Uma de ``FORMAS_DE_BEER``. Teixeira exige quadrada; N/50 aceita
    retangular."""

    solo_declarado: str
    """``'argila'`` ou ``'areia'``, declarado — o software não classifica solo
    a partir de N_SPT (as faixas de N_SPT vêm da NBR 6484, ausente do acervo)."""

    h_m: float
    """Embutimento real da sapata [m]."""

    gamma_kN_m3: float
    """Peso específico do solo [kN/m³]."""

    aplicabilidade_regional_declarada: bool
    """Declaração explícita do usuário (REQ-SIGMA-06). Sem default."""

    considerar_q: bool = False
    """Parcela facultativa "+ q" da regra N/50 (REQ-SIGMA-13). Default: não."""

    q_MPa: float | None = None
    """Sobrecarga em MEGAPASCAL, só quando ``considerar_q`` (REQ-SIGMA-03 a)."""

    metodo_de_seguranca: str = "admissivel"
    """Guarda de método (REQ-SIGMA-01)."""


@dataclass(frozen=True)
class FatoresDeCapacidade:
    """Nc, Nq e Nγ pelas formas fechadas, com o quociente Nq/Nc calculado.

    [pratica: FB-CINTRA-TERZAGHI-VESIC-capacidade-de-carga]

    ``Nq_sobre_Nc`` é SEMPRE calculado de Nq e Nc, jamais lido da Tab. 2.2:
    é coluna derivada, e a linha phi = 0 da fonte imprime 0,20 quando
    1,00/5,14159 = 0,1945 (erro tipográfico reconhecido, repetido da linha
    phi = 1). Ver ``decisao_2`` no ruleset e REQ-SIGMA-07 (h).
    """

    phi_graus: float
    Nc: float
    Nq: float
    N_gamma: float
    Nq_sobre_Nc: float


@dataclass(frozen=True)
class FatoresDeForma:
    """Sc, Sq e Sγ de De Beer (Tab. 2.3) — único conjunto aprovado na v9.

    [pratica: FB-CINTRA-TERZAGHI-VESIC-capacidade-de-carga]

    PROIBIDO misturar com a Tab. 2.1 (Terzaghi-Peck), que não é implementada:
    são dois pacotes coerentes entre si e a fonte não autoriza cruzá-los.
    Medido pelo a2 no caso típico: a troca move sigma_adm de 494 para
    369 kPa (26,8 %).
    """

    forma: str
    Sc: float
    Sq: float
    S_gamma: float


@dataclass(frozen=True)
class ResultadoCapacidadeCarga:
    """sigma_r do sistema sapata-solo, com as três parcelas separadas.

    Ref.: ABNT NBR 6122:2022, item 7.3.2, p. 22
    [rule: NBR6122-7.3.2-metodos-teoricos-condicao-2022] (autorização)
    [pratica: FB-CINTRA-TERZAGHI-VESIC-capacidade-de-carga] (equação)

    Não é tensão admissível nem parcela de ELU: é a tensão de RUPTURA, antes
    de qualquer fator de segurança.
    """

    sigma_r_kPa: float
    """Capacidade de carga do sistema sapata-solo [kPa]."""

    parcela_coesao_kPa: float
    """c·Nc·Sc [kPa]."""

    parcela_sobrecarga_kPa: float
    """q·Nq·Sq, com q = γ_acima·h [kPa]."""

    parcela_peso_kPa: float
    """½·γ_abaixo·B·Nγ·Sγ [kPa]."""

    q_kPa: float
    """Sobrecarga na cota de apoio, q = γ_acima·h [kPa]."""

    fatores: FatoresDeCapacidade
    """Fatores usados no cálculo — com phi* se o modo for puncionamento."""

    fatores_de_forma: FatoresDeForma
    """De Beer, calculados com o phi DECLARADO (não reduzido)."""

    c_de_calculo_kPa: float
    """c usado (c* = 2/3·c no puncionamento) [kPa]."""

    phi_de_calculo_graus: float
    """phi usado (phi* = arctg(2/3·tg phi) no puncionamento) [graus]."""

    modo_de_ruptura: str
    natureza_do_carregamento: str
    metodo_de_seguranca: str
    avisos: tuple[str, ...] = ()
    """Ressalvas que têm de chegar ao memorial (equação aproximada etc.)."""


@dataclass(frozen=True)
class ResultadoSigmaAdmELU:
    """Parcela de ELU da tensão admissível — NUNCA "tensão admissível".

    Ref.: ABNT NBR 6122:2022, itens 7.3 e 7.4, p. 22-23
    [rule: NBR6122-7.3-7.4-conjuncao-ELU-ELS]

    O nome do campo é ``sigma_adm_ELU_kPa`` por exigência de REQ-SIGMA-09, e
    ``rotulo_ELU`` viaja colado ao número até a tela e o memorial. Nenhum
    caminho da v9 verifica o §7.4 (ELS/recalque), e a definição 3.45 da Norma
    é conjuntiva.
    """

    sigma_adm_ELU_kPa: float
    """Parcela de ELU da tensão admissível [kPa]. Ver ``rotulo_ELU``."""

    metodo: str
    """``'teorico'`` ou ``'semiempirico'``."""

    nome_do_metodo: str
    """Nome que vai ao memorial, na nomenclatura da fonte citada."""

    metodo_de_seguranca: str
    """Sempre ``'admissivel'`` nesta versão (REQ-SIGMA-01)."""

    rotulo_ELU: str
    """``ROTULO_ELU`` — obrigatório junto ao número (REQ-SIGMA-09)."""

    rotulo_fonte: str
    """``ROTULO_FONTE_NAO_NORMATIVA`` (REQ-UI-SIGMA-02)."""

    regras: tuple[str, ...] = ()
    """IDs de regra NORMATIVA aplicados — citar como ``[rule: ...]``."""

    praticas: tuple[str, ...] = ()
    """IDs de formulação bibliográfica — citar como ``[pratica: ...]``."""

    FSg_aplicado: float | None = None
    """FSg dividido AQUI (caminho teórico). None no semiempírico."""

    FS_embutido: float | None = None
    """FS já embutido na correlação (REQ-SIGMA-02). None no teórico."""

    FS_embutido_origem: str | None = None
    """Como o FS embutido foi DEMONSTRADO — não presumido (REQ-SIGMA-02)."""

    capacidade: ResultadoCapacidadeCarga | None = None
    """sigma_r que originou o valor, no caminho teórico."""

    memoria: dict[str, float] = field(default_factory=dict)
    """Valores intermediários nomeados, para o memorial."""

    avisos: tuple[str, ...] = ()
    """Ressalvas obrigatórias — domínio, dedução, advertência da fonte."""

    @property
    def FSg_efetivo(self) -> float:
        """FS global que existe por trás deste valor, majoração à parte.

        Ref.: ABNT NBR 6122:2022, item 6.2.1.1.1 e Tabela 1, p. 17
        [rule: NBR6122-6.2.1.1.1-fatores-seguranca-tabela1]

        É o FSg do caminho teórico ou o FS embutido da correlação. É este o
        número que a condição (C4) da majoração por vento consome.
        """
        if self.FSg_aplicado is not None:
            return self.FSg_aplicado
        if self.FS_embutido is not None:
            return self.FS_embutido
        raise ValueError(
            "Resultado sem FSg aplicado nem FS embutido: não é possível "
            "aferir o fator de segurança global (REQ-SIGMA-02)."
        )


@dataclass(frozen=True)
class RecusaDeMetodo:
    """Método que NÃO se aplica ao caso, com o motivo estruturado.

    Ref.: ABNT NBR 6122:2022, item 7.3.3, p. 22
    [rule: NBR6122-7.3.3-metodos-semiempiricos]

    Existe para que a interface diga O QUÊ e POR QUÊ (REQ-UI-SIGMA-03) em vez
    de "erro de cálculo", e para que a recusa apareça ao lado dos métodos que
    se aplicam, em vez de sumir.
    """

    nome_do_metodo: str
    pratica: str
    parametro: str
    valor: object
    intervalo: str
    fonte: str
    forca: str
    """``DECLARADO_EM_TEXTO`` ou ``ADOTADO_DA_EXTENSAO_DE_FIGURA``: os dois
    recusam, mas têm força diferente e o segundo é revisável (REQ-UI-SIGMA-03)."""
    motivo: str


@dataclass(frozen=True)
class ResultadoDispersaoSemiempirica:
    """Todas as correlações aplicáveis LADO A LADO — o software não escolhe.

    Ref.: ABNT NBR 6122:2022, item 7.3.3, p. 22
    [rule: NBR6122-7.3.3-metodos-semiempiricos]

    Implementa a obrigação (b) do §7.3.3 ("bem como as dispersões dos dados").
    Nenhuma correlação desta rodada publica desvio-padrão ou intervalo de
    confiança, e o software NÃO pode inventar um: o que se exibe é a dispersão
    OBSERVÁVEL entre métodos que estejam, todos, dentro do seu domínio.

    NÃO EXISTE, DE PROPÓSITO, um campo "valor de projeto": a seleção de qual
    valor vira o sigma_adm do projeto é do engenheiro. O software não escolhe,
    não faz média e não pega o menor automaticamente (REQ-SIGMA-05).
    """

    resultados: tuple[ResultadoSigmaAdmELU, ...]
    """Correlações DENTRO do domínio, na ordem em que foram avaliadas."""

    recusas: tuple[RecusaDeMetodo, ...] = ()
    """Correlações fora do domínio, com o motivo — exibir junto."""

    declaracao_regional: str = ""
    """Texto da declaração regional do usuário, para o memorial."""

    @property
    def valores_kPa(self) -> tuple[float, ...]:
        """Valores lado a lado [kPa], na mesma ordem de ``resultados``.

        Ref.: ABNT NBR 6122:2022, item 7.3.3, p. 22
        [rule: NBR6122-7.3.3-metodos-semiempiricos]

        Ordem de avaliação, não ordem de preferência: a lista não é ranking e
        o primeiro elemento não é "o valor". Quem escolhe é o engenheiro.
        """
        return tuple(r.sigma_adm_ELU_kPa for r in self.resultados)

    @property
    def dispersao_relativa(self) -> float | None:
        """(máx − mín)/mín entre os valores aplicáveis, ou None se houver um só.

        Ref.: ABNT NBR 6122:2022, item 7.3.3, p. 22
        [rule: NBR6122-7.3.3-metodos-semiempiricos]

        Estatística DESCRITIVA da dispersão observável, para leitura humana.
        Não é veredito e não seleciona valor: quem decide se a convergência é
        boa o bastante é o engenheiro, e ele só decide se vir todos.
        """
        valores = self.valores_kPa
        if len(valores) < 2:
            return None
        return (max(valores) - min(valores)) / min(valores)


@dataclass(frozen=True)
class ResultadoMajoracaoVento:
    """Majoração por vento sobre a parcela de ELU — GEOTÉCNICA e só.

    Ref.: ABNT NBR 6122:2022, item 6.3.2 (com 6.3.1), p. 21
    [rule: NBR6122-6.3.2-majoracao-vento-valores-admissiveis]

    "Em qualquer caso, deve ser feita a verificação estrutural do elemento de
    fundação" é literal: ``k_v`` NÃO pode se propagar para flexão,
    cisalhamento, punção ou ancoragem (REQ-SIGMA-10).
    """

    sigma_adm_ELU_majorado_kPa: float
    """(1 + k_v)·sigma_adm_ELU [kPa]. Igual ao original quando k_v = 0."""

    sigma_adm_ELU_base_kPa: float
    """Valor antes da majoração [kPa]."""

    k_v_adotado: float
    """Majoração EFETIVAMENTE adotada pelo engenheiro [adimensional]."""

    k_v_maximo_admissivel: float
    """Teto resultante das condições (C2)/(C3)/(C4) para este caso."""

    FSg_base: float
    """Fator de segurança global por trás do sigma_adm recebido."""

    FSg_efetivo: float
    """FSg_base/(1 + k_v) — tem de ser >= 1,6 quando se majora."""

    vento_e_acao_variavel_principal: bool
    tipo_de_obra_da_lista_dos_30_por_cento: bool
    rotulo_ELU: str
    metodo_de_seguranca: str
    regras: tuple[str, ...] = ()
    avisos: tuple[str, ...] = ()
