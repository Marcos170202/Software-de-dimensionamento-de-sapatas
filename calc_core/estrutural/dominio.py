"""Guardas de domínio do motor estrutural — funções que RECUSAM, nunca aproximam.

Ref.: ABNT NBR 6118:2023, item 15.8.3, p. 108 (métodos de 2ª ordem, REJEITADA)
[rule: NBR6118-15.8.3-metodos-de-2a-ordem]

Ref.: ABNT NBR 6118:2023, item 14.4.1, p. 83 (classificação do elemento)
[rule: NBR6118-14.4.1-elemento-linear-classificacao]

MESMO PADRÃO, DELIBERADAMENTE, de ``calc_core/geotecnico/dominio.py``: a
exceção carrega ``parametro``, ``valor``, ``intervalo``, ``fonte``, ``forca`` e
``apoio_no_ruleset``, de modo que a interface possa dizer O QUÊ e POR QUÊ em
vez de "erro de cálculo". A classe é OUTRA (e não um import) porque
REQ-PILARETE-01 proíbe este pacote de importar ``geotecnico/``; a duplicação
de ~40 linhas é o preço declarado de manter a fronteira entre os dois motores
verificável por inspeção.

NOME DA CLASSE FIXADO PELO RULESET: ``RecusaForaDeDominio`` — é o nome que
REQ-PILARETE-17(3) escreve para a recusa de §17.4 na FAIXA B.

DOUTRINA, herdada do resto do repositório e reafirmada em REQ-PILARETE-03,
-05, -06, -08, -11, -17 e -18: fora do domínio o software LEVANTA EXCEÇÃO
nomeando parâmetro, valor, intervalo e fonte. Clampar, extrapolar, aproximar,
devolver ``None``, devolver zero ou "avisar e seguir" são PROIBIDOS — um
número devolvido fora do domínio sai plausível, que é o modo de falha mais
perigoso deste software. Não existe parâmetro, flag, variável de ambiente ou
caixa de diálogo que permita prosseguir.
"""
from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass

DECLARADO_EM_TEXTO = "declarado_em_texto_na_fonte"
"""Limite escrito com todas as letras na Norma (ex.: b >= 14 cm em 13.2.3)."""

NAO_DECLARADO_NA_FONTE = "ausencia_de_regra_na_fonte_normativa"
"""A Norma é SILENTE e não há rota alternativa no acervo (ex.: k_phi de 18.4.3
para CA-60; transferência de cortante na junta de 21.6 sem a ABNT NBR 9062).
Recusar é o comportamento correto: extrapolar seria inventar fonte."""

DECLARADO_PELO_USUARIO = "declaracao_obrigatoria_do_usuario"
"""A fonte exige uma declaração que o software não pode inferir (vinculação,
modelo de cálculo do cortante, theta_biela, tipo de junta, idade j >= 28 dias,
situação de aderência). A ausência da declaração é recusa, não default."""

ESCOPO_DESTA_VERSAO = "escopo_desta_versao_nao_limite_da_norma"
"""Limite do SOFTWARE, não da Norma (ex.: alpha_estribo != 90°, que a Norma
admite entre 45° e 90°). A mensagem cita o ESCOPO, nunca a Norma."""

_ATRIBUTOS_DA_MAQUINA_DE_EXCECOES = frozenset({
    "__traceback__", "__context__", "__cause__", "__suppress_context__",
    "__notes__", "args",
})
"""Atributos que o interpretador escreve numa exceção em trânsito.

Ref.: ABNT NBR 6118:2023, item 14.4.1, p. 83
[rule: NBR6118-14.4.1-elemento-linear-classificacao]

Lista FECHADA e mínima: são os únicos atributos que ``RecusaForaDeDominio``
deixa passar pelo congelamento do dataclass. Os CAMPOS da recusa (parâmetro,
valor, intervalo, fonte, força, apoio no ruleset) continuam imutáveis — se
fosse possível reescrevê-los depois de construída, a mensagem já formatada
deixaria de corresponder ao que a exceção diz carregar. Ver o motivo completo
em :func:`_congelar_campos_mas_deixar_a_maquina_de_excecoes_trabalhar`.
"""


@dataclass(frozen=True)
class RecusaForaDeDominio(ValueError):
    """Entrada fora do domínio aprovado; o software recusa em vez de calcular.

    Ref.: ABNT NBR 6118:2023, item 14.4.1, p. 83
    [rule: NBR6118-14.4.1-elemento-linear-classificacao]
    [req: REQ-PILARETE-17-guarda-de-elemento-linear-14.4.1]

    Campos estruturados para que a interface (a3) exiba parâmetro, valor,
    intervalo e fonte — mesma exigência de REQ-UI-SIGMA-03 no motor
    geotécnico. ``mensagem`` sem número é defeito (REQ-PILARETE-03).
    """

    parametro: str
    valor: object
    intervalo: str
    fonte: str
    forca: str
    apoio_no_ruleset: str
    sugestao: str = ""

    def __post_init__(self) -> None:
        ValueError.__init__(self, self.mensagem)

    @property
    def mensagem(self) -> str:
        """Texto legível, com parâmetro, valor obtido, limite e fonte.

        Ref.: ABNT NBR 6118:2023, item 13.2.3, p. 73
        [rule: NBR6118-13.2.3-dimensoes-limites-pilarete]

        REQ-PILARETE-03: "a recusa cita item, valor obtido e valor-limite.
        Mensagem sem número é defeito."
        """
        partes = [
            f"{self.parametro} = {self.valor!r} fora do domínio "
            f"({self.intervalo}).",
            f"Fonte do limite: {self.fonte}.",
            f"Força da guarda: {self.forca}.",
            f"Apoio no ruleset: {self.apoio_no_ruleset}.",
        ]
        if self.sugestao:
            partes.append(self.sugestao)
        return " ".join(partes)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.mensagem


def _congelar_campos_mas_deixar_a_maquina_de_excecoes_trabalhar(
    self: RecusaForaDeDominio, nome: str, valor: object,
) -> None:
    """Congela os CAMPOS da recusa, mas deixa o interpretador escrever os seus.

    Ref.: ABNT NBR 6118:2023, item 14.4.1, p. 83
    [rule: NBR6118-14.4.1-elemento-linear-classificacao]
    [req: REQ-PILARETE-17-guarda-de-elemento-linear-14.4.1]

    DEFEITO ENCONTRADO AO ESCREVER OS TESTES DESTA RODADA, e é sutil: um
    ``@dataclass(frozen=True)`` que herda de ``ValueError`` QUEBRA quando o
    interpretador tenta atribuir ``__traceback__`` à exceção em trânsito — o
    que acontece sempre que ela atravessa um gerenciador de contexto escrito
    com ``@contextlib.contextmanager`` (``contextlib`` faz
    ``exc.__traceback__ = traceback`` explicitamente, em Python). O usuário
    veria ``FrozenInstanceError: cannot assign to field '__traceback__'``:
    um TRACEBACK CRU, sem parâmetro, sem valor e sem fonte, no lugar da recusa
    legível. É exatamente o modo de falha que a doutrina deste módulo proíbe.

    A correção preserva a intenção do congelamento: os CAMPOS declarados
    continuam imutáveis — reescrevê-los depois de construída falsificaria a
    ``mensagem`` já formatada —, e só passam os atributos enumerados em
    :data:`_ATRIBUTOS_DA_MAQUINA_DE_EXCECOES`.

    POR QUE FORA DA CLASSE: ``@dataclass(frozen=True)`` RECUSA-SE a gerar a
    classe se ``__setattr__`` estiver definido no corpo dela ("Cannot
    overwrite attribute __setattr__"). A instalação posterior é a única forma
    de manter os dois comportamentos.

    NOTA DE ESCOPO, para o a6: ``calc_core/geotecnico/dominio.py`` tem a MESMA
    forma (``ForaDoDominioError``) e portanto o mesmo defeito latente. Ele NÃO
    é corrigido aqui — é código já aprovado por A6/A7, e alterá-lo por conta
    própria invalidaria aprovações fora do escopo desta rodada.
    """
    if nome in _ATRIBUTOS_DA_MAQUINA_DE_EXCECOES:
        object.__setattr__(self, nome, valor)
        return
    raise FrozenInstanceError(f"cannot assign to field {nome!r}")


RecusaForaDeDominio.__setattr__ = (  # type: ignore[method-assign]
    _congelar_campos_mas_deixar_a_maquina_de_excecoes_trabalhar)


def exigir_declarado(parametro: str, valor: object, *, fonte: str,
                     apoio_no_ruleset: str, sugestao: str = "") -> object:
    """Recusa ``None``: entrada obrigatória SEM default silencioso.

    Ref.: ABNT NBR 6118:2023, item 17.4.2.3, p. 138-139
    [rule: NBR6118-17.4.2.3-modelo-II-theta-arbitrado]
    [req: REQ-PILARETE-02-entradas-explicitas-e-recusa-por-ausencia]

    É a guarda de todas as entradas que a Norma manda o PROJETISTA arbitrar e
    que o software não pode escolher por ele: vinculação, MODELO_DE_CALCULO,
    theta_biela, tipo de junta, situação de aderência eta_2, idade j >= 28
    dias. "É PROIBIDO default, é PROIBIDO 'tentar os dois', é PROIBIDO adotar
    o que aprova" (REQ-PILARETE-18-j).
    """
    if valor is None:
        raise RecusaForaDeDominio(
            parametro=parametro,
            valor=None,
            intervalo="declaração explícita obrigatória (sem default)",
            fonte=fonte,
            forca=DECLARADO_PELO_USUARIO,
            apoio_no_ruleset=apoio_no_ruleset,
            sugestao=sugestao,
        )
    return valor


def exigir_um_de(parametro: str, valor: object, admitidos: tuple[str, ...], *,
                 fonte: str, apoio_no_ruleset: str,
                 sugestao: str = "") -> str:
    """Aceita apenas um dos rótulos de ``admitidos``; RECUSA qualquer outro.

    Ref.: ABNT NBR 6118:2023, item 21.6, p. 181
    [rule: NBR6118-21.6-junta-de-concretagem-pilarete-sapata]
    [req: REQ-PILARETE-02-entradas-explicitas-e-recusa-por-ausencia]

    Guarda das enumerações FECHADAS: vinculação, tipo de junta, modelo de
    cálculo do cortante, categoria do aço, classe de agressividade. Não há
    terceira opção e não há valor inferido.
    """
    if valor not in admitidos:
        raise RecusaForaDeDominio(
            parametro=parametro,
            valor=valor,
            intervalo="um de " + ", ".join(repr(a) for a in admitidos),
            fonte=fonte,
            forca=DECLARADO_PELO_USUARIO,
            apoio_no_ruleset=apoio_no_ruleset,
            sugestao=sugestao,
        )
    return str(valor)


def exigir_intervalo(parametro: str, valor: float, minimo: float,
                     maximo: float, *, fonte: str, forca: str,
                     apoio_no_ruleset: str, sugestao: str = "") -> float:
    """Aceita ``valor`` em [minimo, maximo] fechado; RECUSA fora, sem clampar.

    Ref.: ABNT NBR 6118:2023, item 17.4.2.3, p. 138-139
    [rule: NBR6118-17.4.2.3-modelo-II-theta-arbitrado]

    Usada em theta_biela (30° a 45°, 17.4.2.3) e alpha_estribo (45° a 90°,
    17.4.1.1.5). Intervalo FECHADO: os extremos são valores que a Norma
    escreve e portanto autoriza.
    """
    if not (minimo <= valor <= maximo):
        raise RecusaForaDeDominio(
            parametro=parametro,
            valor=valor,
            intervalo=f"{minimo} a {maximo}",
            fonte=fonte,
            forca=forca,
            apoio_no_ruleset=apoio_no_ruleset,
            sugestao=sugestao,
        )
    return valor


def exigir_positivo(parametro: str, valor: float, *, fonte: str,
                    apoio_no_ruleset: str,
                    permitir_zero: bool = False) -> float:
    """Exige valor positivo (ou não negativo, se ``permitir_zero``).

    Ref.: ABNT NBR 6118:2023, item 13.2.3, p. 73
    [rule: NBR6118-13.2.3-dimensoes-limites-pilarete]

    Grandeza geométrica negativa não é caso de canto: é erro de wiring, e
    devolveria número plausível de sinal trocado.
    """
    ok = valor >= 0.0 if permitir_zero else valor > 0.0
    if not ok:
        raise RecusaForaDeDominio(
            parametro=parametro,
            valor=valor,
            intervalo=">= 0" if permitir_zero else "> 0",
            fonte=fonte,
            forca=DECLARADO_EM_TEXTO,
            apoio_no_ruleset=apoio_no_ruleset,
        )
    return valor
