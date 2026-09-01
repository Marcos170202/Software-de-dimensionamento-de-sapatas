"""Guardas de domínio de validade — funções que RECUSAM, nunca aproximam.

Ref.: ABNT NBR 6122:2022, item 7.3.3, p. 22
[rule: NBR6122-7.3.3-metodos-semiempiricos]

Ref.: ABNT NBR 6122:2022, item 7.3.2, p. 22
[rule: NBR6122-7.3.2-metodos-teoricos-condicao-2022]

Os dois itens impõem, em texto normativo, que os métodos só podem ser
empregados "nos domínios de validade de sua aplicação" (7.3.2) e que "devem
ser observados os domínios de validade de suas aplicações" (7.3.3). Este
módulo é a implementação executável dessa obrigação, conforme REQ-SIGMA-04 e
REQ-SIGMA-07 do ``ruleset.yaml`` v9: fora do domínio a função **levanta
exceção**, nomeando o parâmetro, o valor recebido e o intervalo declarado.

NÃO É "MELHOR ESFORÇO". Aproximar, extrapolar, clampar ou avisar-e-seguir é
proibido: um número devolvido fora do domínio é um número sem procedência, e
sai plausível — que é o modo de falha mais perigoso deste software.

FORÇA DA GUARDA. Nem toda guarda tem a mesma origem, e a distinção viaja com
a exceção para que a interface possa dizê-lo ao usuário (REQ-UI-SIGMA-03):

``DECLARADO_EM_TEXTO``
    limite escrito com todas as letras na fonte (ex.: 5 <= N_SPT <= 20 da
    regra N/50). Só muda se a fonte mudar.
``ADOTADO_DA_EXTENSAO_DE_FIGURA``
    limite que o a2 adotou lendo a EXTENSÃO de uma figura da fonte, não o seu
    texto (ex.: 1 a 3 m e 4 a 25 golpes de Teixeira, da Fig. 4.1). Recusa
    igual, força menor: é revisável por decisão humana registrada em
    ``kb/pendencias.md`` > V3.
``DECLARADO_PELO_USUARIO``
    a fonte exige uma declaração que o software não pode inferir (solo
    homogêneo, modo de ruptura, natureza do carregamento, aplicabilidade
    regional). A ausência da declaração é recusa, não default.
"""
from __future__ import annotations

from dataclasses import dataclass

DECLARADO_EM_TEXTO = "declarado_em_texto_na_fonte"
"""Limite escrito na fonte. Ver docstring do módulo."""

ADOTADO_DA_EXTENSAO_DE_FIGURA = "extensao_de_figura_nao_declarada_em_texto"
"""Limite adotado pelo a2 a partir da extensão de uma figura da fonte."""

DECLARADO_PELO_USUARIO = "declaracao_obrigatoria_do_usuario"
"""Condição que o software não infere e que o usuário tem de declarar."""


@dataclass(frozen=True)
class ForaDoDominioError(ValueError):
    """Entrada fora do domínio de validade declarado pela fonte do método.

    Ref.: ABNT NBR 6122:2022, itens 7.3.2 e 7.3.3, p. 22
    [rule: NBR6122-7.3.3-metodos-semiempiricos]

    Carrega os campos estruturados de que a interface precisa para dizer
    O QUÊ e POR QUÊ (REQ-UI-SIGMA-03), em vez de "erro de cálculo":
    ``parametro``, ``valor``, ``intervalo``, ``fonte``, ``forca`` e o campo do
    ruleset em que a guarda se apoia (``apoio_no_ruleset``, exigido por
    REQ-SIGMA-04 para que o a6 possa conferir uma a uma).
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
        """Texto legível, com parâmetro, valor recebido e intervalo.

        Ref.: ABNT NBR 6122:2022, item 7.3.3, p. 22
        [rule: NBR6122-7.3.3-metodos-semiempiricos]

        É o texto que a interface exibe (REQ-UI-SIGMA-03): nunca "erro de
        cálculo", sempre o quê, o porquê e de quem é o limite.
        """
        partes = [
            (f"{self.parametro} = {self.valor!r} fora do domínio declarado "
            f"({self.intervalo})."),
            f"Limite da FONTE, não do software: {self.fonte}.",
            f"Força da guarda: {self.forca}.",
            f"Apoio no ruleset: {self.apoio_no_ruleset}.",
        ]
        if self.sugestao:
            partes.append(self.sugestao)
        return " ".join(partes)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.mensagem


def exigir_intervalo(parametro: str, valor: float, minimo: float,
                     maximo: float, *, fonte: str, forca: str,
                     apoio_no_ruleset: str, sugestao: str = "") -> float:
    """Aceita ``valor`` em [minimo, maximo]; RECUSA fora, sem clampar.

    Ref.: ABNT NBR 6122:2022, item 7.3.3, p. 22
    [rule: NBR6122-7.3.3-metodos-semiempiricos]

    Intervalo FECHADO nos dois extremos — os extremos são valores que a fonte
    tabula ou plota, e portanto autoriza.
    """
    if not (minimo <= valor <= maximo):
        raise ForaDoDominioError(
            parametro=parametro,
            valor=valor,
            intervalo=f"{minimo} a {maximo}",
            fonte=fonte,
            forca=forca,
            apoio_no_ruleset=apoio_no_ruleset,
            sugestao=sugestao,
        )
    return valor


def exigir_igualdade(parametro: str, valor: float, esperado: float, *,
                     fonte: str, forca: str, apoio_no_ruleset: str,
                     sugestao: str = "") -> float:
    """Aceita apenas ``valor == esperado``, com TOLERÂNCIA ZERO.

    Ref.: ABNT NBR 6122:2022, item 7.3.3, p. 22
    [rule: NBR6122-7.3.3-metodos-semiempiricos]

    Usada nos parâmetros CONGELADOS na dedução de uma correlação (h = 1,5 m e
    gamma = 18 kN/m³ em Teixeira, 1996), que não são variáveis da fórmula. A
    comparação é exata de propósito: REQ-SIGMA-04 determina "igualdade
    estrita, tolerância ZERO até decisão humana", e a tolerância admissível
    está em ``kb/pendencias.md`` > V3, ainda não decidida. Medido pelo a2:
    h = 3,0 m em vez de 1,5 m move o resultado 59 %.
    """
    if valor != esperado:
        raise ForaDoDominioError(
            parametro=parametro,
            valor=valor,
            intervalo=f"exatamente {esperado} (parâmetro CONGELADO na dedução)",
            fonte=fonte,
            forca=forca,
            apoio_no_ruleset=apoio_no_ruleset,
            sugestao=sugestao,
        )
    return valor


def exigir_um_de(parametro: str, valor: object, admitidos: tuple[str, ...], *,
                 fonte: str, forca: str, apoio_no_ruleset: str,
                 sugestao: str = "") -> str:
    """Aceita apenas um dos rótulos de ``admitidos``; RECUSA qualquer outro.

    Ref.: ABNT NBR 6122:2022, item 7.3.2, p. 22
    [rule: NBR6122-7.3.2-metodos-teoricos-condicao-2022]

    É a guarda das ENTRADAS CATEGÓRICAS que o software não infere: modo de
    ruptura (REQ-SIGMA-12), natureza do carregamento (REQ-SIGMA-08), forma da
    sapata e tipo de solo declarado. Não há terceira opção e não há default.
    """
    if valor not in admitidos:
        raise ForaDoDominioError(
            parametro=parametro,
            valor=valor,
            intervalo="um de " + ", ".join(repr(a) for a in admitidos),
            fonte=fonte,
            forca=forca,
            apoio_no_ruleset=apoio_no_ruleset,
            sugestao=sugestao,
        )
    return str(valor)


def exigir_declaracao(parametro: str, declarado: bool, *, exigencia: str,
                      fonte: str, apoio_no_ruleset: str,
                      sugestao: str = "") -> bool:
    """Exige declaração afirmativa e explícita do usuário; RECUSA a ausência.

    Ref.: ABNT NBR 6122:2022, item 7.3.3, p. 22
    [rule: NBR6122-7.3.3-metodos-semiempiricos]

    Implementa a obrigação (c) do §7.3.3 ("as limitações regionais associadas
    a cada um dos métodos") e a hipótese de solo HOMOGÊNEO do §7.3.2, ambas
    fora do alcance de qualquer inferência a partir de um perfil SPT. Sem
    default afirmativo, por REQ-SIGMA-06: silêncio não é declaração.
    """
    if declarado is not True:
        raise ForaDoDominioError(
            parametro=parametro,
            valor=declarado,
            intervalo="declaração explícita True",
            fonte=fonte,
            forca=DECLARADO_PELO_USUARIO,
            apoio_no_ruleset=apoio_no_ruleset,
            sugestao=sugestao or exigencia,
        )
    return True


def exigir_positivo(parametro: str, valor: float, *, fonte: str,
                    apoio_no_ruleset: str, permitir_zero: bool = False) -> float:
    """Exige valor positivo (ou não negativo, se ``permitir_zero``).

    Ref.: ABNT NBR 6122:2022, item 7.3.2, p. 22
    [rule: NBR6122-7.3.2-metodos-teoricos-condicao-2022]

    Guarda (e) de REQ-SIGMA-07: c >= 0, B > 0, gamma > 0. Grandeza física
    negativa aqui não é caso de canto — é erro de wiring, e devolveria número
    plausível de sinal trocado.
    """
    limite_ok = valor >= 0.0 if permitir_zero else valor > 0.0
    if not limite_ok:
        raise ForaDoDominioError(
            parametro=parametro,
            valor=valor,
            intervalo=">= 0" if permitir_zero else "> 0",
            fonte=fonte,
            forca=DECLARADO_EM_TEXTO,
            apoio_no_ruleset=apoio_no_ruleset,
        )
    return valor
