# Software de dimensionamento de sapatas — SAPATA-7

Dimensionamento geotécnico e estrutural de sapatas de fundação, seguindo as
normas ABNT (NBR 6118, 6120, 6122, 6123, 8681), com todo cálculo em Python
determinístico e rastreável item a item da norma. Ver `CLAUDE.md` para os
princípios e a ordem do pipeline.

## Estado atual — dois motores

**`calc_core/geotecnico/` (escopo mínimo, 100% auditado):** geometria (B×L)
de sapata isolada sob carga vertical **centrada**, em solo homogêneo, com
tensão admissível σ_adm fornecida pelo engenheiro (NBR 6122:2022 §5.6, §7.1,
§7.6.1, §7.7.1). Interface: `ui/app_desktop.py`.

**`calc_core/sapata_isolada/` (escopo amplo, parcialmente auditado):** carga
excêntrica, punção, bielas e tirantes, estabilidade, recalques por
substrato, rigidez/grelha sobre base elástica, MEF do solo. Materiais
(NBR 6118 §8), ancoragem (§9.3-9.4), cisalhamento (§19.4) e punção (§19.5)
foram conferidos item a item contra o texto da norma — 6 defeitos
encontrados e corrigidos, 2 deles do lado inseguro (ver
`relatorios/revisao_codigo.md`, adendo de 2026-08-26). O resto (geotecnia
excêntrica, bielas de Blévot, rigidez/Winkler, recalques, MEF do solo) está
`PENDENTE_HUMANO` em `ruleset.yaml` — portado e testado numericamente, mas
não auditado fórmula a fórmula. Interface: `ui/app_completo.py`, que exibe
esse aviso de forma permanente.

**NÃO implementado em nenhum dos dois:** determinação de σ_adm a partir de
SPT/CPT, majoração por vento na tensão admissível, pilar de borda/canto na
punção. Ver `ruleset.yaml` e `kb/pendencias.md` para o que falta e por quê.

Este software é **apoio à decisão**. O memorial e os desenhos finais são de
responsabilidade do engenheiro que assina a ART (NBR 6122:2022 §7.1). Isso
vale com força redobrada para o escopo amplo, que tem partes ainda não
auditadas.

## Como usar agora

### Opção 1 — rodar com Python (funciona em qualquer SO)

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python -m ui.app_desktop     # escopo mínimo, 100% auditado
python -m ui.app_completo    # escopo amplo — parcialmente em conferência
```

Abre uma janela desktop (Tkinter) com o formulário de entrada e o memorial
de saída.

### Opção 2 — baixar o `Sapata7.exe` pronto (Windows)

Todo push que altera `calc_core/`, `ui/` ou `sapata7.spec` dispara o workflow
**Build Sapata7.exe** (`.github/workflows/build-exe.yml`) num runner Windows
de verdade — não é um `.exe` cross-compilado. Para pegar o executável:

1. Abra a aba **Actions** deste repositório no GitHub.
2. Escolha a execução mais recente de **Build Sapata7.exe**.
3. Baixe o artifact **Sapata7-windows** — dentro dele estão `Sapata7.exe`
   (escopo mínimo) e `Sapata7Completo.exe` (escopo amplo, ver aviso acima).

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
ruff check calc_core/ ui/ --select E9        # sintaxe, repositório inteiro
ruff check calc_core/geotecnico/ calc_core/modelos.py ui/   # padrão completo
mypy --strict calc_core/geotecnico/ calc_core/modelos.py
pytest tests/ --cov=calc_core --cov-report=term-missing
```

45 testes no total, cobertura de linhas 100% em `calc_core/geotecnico/` (ver
`relatorios/revisao_codigo.md` e `relatorios/conformidade.md` para o detalhe
— incluindo as limitações do processo de revisão/validação em cada escopo).

`mypy --strict` e o padrão completo do `ruff` só são exigidos para
`calc_core/geotecnico/`, `calc_core/modelos.py` e `ui/` — o pacote externo
`calc_core/sapata_isolada/` não foi escrito sob essas convenções (399 avisos
de tipagem e 16 de imports/variáveis não usadas nesta rodada — reais, mas de
qualidade de código, não de correção numérica) e arrumá-los não fez parte do
escopo desta auditoria, que priorizou conferir as fórmulas contra a norma.
`ruff --select E9` (erros de sintaxe) passa limpo no repositório inteiro.

## Estrutura

```
CLAUDE.md                 regras do repositório e ordem do pipeline
.claude/agents/            os 7 subagentes de projeto
ruleset.yaml / ruleset.lock  regras normativas aprovadas (só a2-verificador escreve)
kb/                         extrações normativas (a1-bibliotecario) e fila humana
calc_core/geotecnico/       núcleo mínimo, 100% auditado (carga centrada)
calc_core/sapata_isolada/   núcleo amplo, parcialmente auditado (ver ruleset.yaml)
ui/app_desktop.py           interface do núcleo mínimo — não calcula nada (a3)
ui/app_completo.py          interface do núcleo amplo — idem, com aviso de escopo
tests/                      conformidade, equilíbrio, invariância, contorno, regressão das correções
relatorios/                 revisão de código e validação (a6/a7), com adendo de 2026-08-26
tools/decodificar_nbr.py    decodificador de PDFs da ABNT com CMap deslocado
sapata7.spec, .github/workflows/build-exe.yml   empacotamento em .exe
instalar_sapata7.sh         instalador do pipeline de agentes para outro projeto
```
