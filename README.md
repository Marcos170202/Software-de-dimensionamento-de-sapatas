# SAPATA-7 — Como instalar os agentes

## O que este pacote é

Sete subagentes do Claude Code, prontos para uso, mais o `CLAUDE.md` com as regras
do repositório e o decodificador de PDFs da ABNT.

```
.claude/agents/          os 7 agentes
CLAUDE.md                regras do repositório e ordem do pipeline
tools/decodificar_nbr.py decodificador de CMap deslocado da ABNT
kb/ calc_core/ tests/ relatorios/    pastas do barramento (vazias)
```

## Instalação

```bash
unzip sapata7-agentes.zip -d ~/projetos/sapata7
cd ~/projetos/sapata7
git init && git add . && git commit -m "estrutura inicial dos agentes"
mkdir refs && cp /caminho/das/normas/*.pdf refs/
pip install pymupdf pdfplumber pint sympy numpy scipy pydantic pytest hypothesis ruff mypy
claude
```

Dentro da sessão, `/agents` lista os sete. Eles são acionados de duas formas:

- **automática** — o Claude Code lê o campo `description` e delega sozinho quando
  o pedido casa. Por isso as descrições usam "MUST BE USED para..." e listam
  frases-gatilho concretas.
- **manual** — `@a4-geotecnico implemente a busca de B×L para carga centrada`.

Editar um arquivo em `.claude/agents/` recarrega o agente na hora, sem reiniciar.

## Escopo dos arquivos

`.claude/agents/` no repositório = agentes do projeto, versionados, compartilhados
com a equipe. `~/.claude/agents/` = agentes pessoais, disponíveis em qualquer
projeto. Estes sete são de projeto: pertencem a este software, não ao seu perfil.

## Primeira sessão sugerida

```
@a1-bibliotecario extraia da NBR 6122 os itens 7.1 a 7.8, só o necessário
para sapata isolada com carga centrada em solo homogêneo.

@a2-verificador audite o que o A1 extraiu e monte o ruleset.yaml.

@a4-geotecnico implemente geometria.py para carga centrada, apenas o que
estiver APROVADA no ruleset.

@a6-revisor
@a7-validador
```

Resista à tentação de mandar o A1 varrer as sete normas de uma vez. O escopo
mínimo primeiro é o que faz o pipeline inteiro rodar em um dia em vez de duas
semanas.

## Sobre o decodificador

Os PDFs da ABNT embutem subsets de fonte com CMap deslocado — o texto cru sai
como `7RGRV RV GLUHLWRV`. Os deslocamentos foram identificados e validados
(+29/−29 no code point, acentuação em MacRoman, ligaduras fi/fl em slots
próprios).

A decodificação correta é **por span**, usando o nome da fonte que o `pymupdf`
devolve — uma mesma linha da NBR 6118 mistura as duas fontes (corpo de texto numa,
numeração e pontos do sumário na outra). Sem `pymupdf` o script cai para detecção
por linha, que deixa resíduo nas linhas mistas. Por isso o A1 tem instrução
explícita de parar e reportar quando sobrar mojibake, em vez de adivinhar
palavras.

As equações continuam fora do alcance de qualquer decodificador: são vetores, sem
camada de texto. Só saem por leitura visual da página rasterizada, e é isso que o
A1 faz — com dupla passada e flag de divergência.
