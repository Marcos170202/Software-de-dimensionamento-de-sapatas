# Software de dimensionamento de sapatas — SAPATA-7

Dimensionamento geotécnico e estrutural de sapatas de fundação, seguindo as
normas ABNT (NBR 6118, 6120, 6122, 6123, 8681), com todo cálculo em Python
determinístico e rastreável item a item da norma. Ver `CLAUDE.md` para os
princípios e a ordem do pipeline.

## Estado atual (escopo mínimo)

**Implementado e testado:** geometria (B×L) de sapata isolada sob carga
vertical **centrada**, em solo homogêneo, com tensão admissível σ_adm
fornecida pelo engenheiro (NBR 6122:2022 §5.6, §7.1, §7.6.1, §7.7.1).

**NÃO implementado ainda:** carga excêntrica, deslizamento, tombamento,
recalques, determinação de σ_adm a partir de SPT/CPT, e todo o
dimensionamento estrutural (armadura, punção — depende da NBR 6118). Ver
`ruleset.yaml` e `kb/pendencias.md` para o que falta e por quê.

Este software é **apoio à decisão**. O memorial e os desenhos finais são de
responsabilidade do engenheiro que assina a ART (NBR 6122:2022 §7.1).

## Como usar agora

### Opção 1 — rodar com Python (funciona em qualquer SO)

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python -m ui.app_desktop
```

Abre uma janela desktop (Tkinter) com o formulário de entrada e o memorial
de saída.

### Opção 2 — baixar o `Sapata7.exe` pronto (Windows)

Todo push que altera `calc_core/`, `ui/` ou `sapata7.spec` dispara o workflow
**Build Sapata7.exe** (`.github/workflows/build-exe.yml`) num runner Windows
de verdade — não é um `.exe` cross-compilado. Para pegar o executável:

1. Abra a aba **Actions** deste repositório no GitHub.
2. Escolha a execução mais recente de **Build Sapata7.exe**.
3. Baixe o artifact **Sapata7-windows** — dentro dele está `Sapata7.exe`.

Não precisa de Python instalado na máquina que só vai *rodar* o `.exe`;
Python só é necessário para desenvolver ou gerar o executável.

### Opção 3 — instalar o pipeline de agentes em outro projeto

`instalar_sapata7.sh` empacota `CLAUDE.md`, os sete subagentes de projeto
(`.claude/agents/`) e o decodificador de PDFs da ABNT para iniciar um projeto
SAPATA-7 do zero em outro diretório:

```bash
bash instalar_sapata7.sh ~/projetos/sapata7
```

Não é necessário para usar o software deste repositório — os agentes já
estão instalados aqui também (`.claude/agents/`).

## Rodando os testes

```bash
pip install -r requirements-dev.txt
ruff check calc_core/
mypy --strict calc_core/
pytest tests/ --cov=calc_core --cov-report=term-missing
```

21 testes, cobertura de linhas 100% em `calc_core/` (ver
`relatorios/revisao_codigo.md` e `relatorios/conformidade.md` para o detalhe
— incluindo as limitações do processo de revisão/validação neste escopo).

## Estrutura

```
CLAUDE.md                 regras do repositório e ordem do pipeline
.claude/agents/            os 7 subagentes de projeto
ruleset.yaml / ruleset.lock  regras normativas aprovadas (só a2-verificador escreve)
kb/                         extrações normativas (a1-bibliotecario) e fila humana
calc_core/                  núcleo de cálculo determinístico (a4/a5)
ui/                         interface desktop — não calcula nada (a3)
tests/                      testes de conformidade, equilíbrio, invariância, contorno
relatorios/                 revisão de código e validação (a6/a7)
tools/decodificar_nbr.py    decodificador de PDFs da ABNT com CMap deslocado
sapata7.spec, .github/workflows/build-exe.yml   empacotamento em .exe
instalar_sapata7.sh         instalador do pipeline de agentes para outro projeto
```
