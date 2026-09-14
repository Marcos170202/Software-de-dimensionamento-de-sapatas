# ADR-001 — Stack de GUI desktop e empacotamento

- Status: aceita
- Data: 2026-09-14

## Contexto

O pacote `estrutura_metalica` é, até aqui, um motor de cálculo puro
(modelagem, análise 3D de 1ª ordem, dimensionamento NBR 8800), sem
nenhuma dependência de interface gráfica — ver o docstring de
`estrutura_metalica/__init__.py` e a nota da Etapa 1 do
`PROCESSO_MODELAGEM_METALICA.md`. Falta, porém, uma forma de um
usuário final (engenheiro projetista) lançar um modelo, rodar a
análise e ver as verificações normativas sem escrever código Python.

Este ADR decide o *stack* de uma aplicação desktop que consome o
motor de cálculo já existente — sem alterar esse motor — cobrindo:

1. framework de janelas/widgets (formulários, tabelas, abas);
2. renderização de um viewport 3D interativo (nós, elementos,
   apoios, cargas, forma deformada, e — em incremento futuro —
   inserção interativa de nós por clique);
3. empacotamento para distribuição a um usuário Windows sem Python
   instalado.

## Decisão

- **Widgets/janelas: PySide6** (bindings oficiais do Qt 6 mantidos
  pela The Qt Company, licença LGPLv3 — compatível com distribuir um
  executável fechado, ao contrário do PyQt6/GPL). Motivos: é a opção
  mais madura para uma aplicação desktop rica em formulários/tabelas
  no ecossistema Python; tem um caminho de teste headless direto
  (`QT_QPA_PLATFORM=offscreen`, ver seção Testes); e se integra
  nativamente com o VTK/PyVista escolhido para o viewport (via
  `pyvistaqt.QtInteractor`, que é um `QWidget`).
- **Viewport 3D: PyVista + pyvistaqt** (wrapper de alto nível sobre o
  VTK). Motivos: API declarativa para malhas/linhas/setas/texto (nós
  como pontos, elementos como linhas ou tubos, apoios/cargas como
  glifos, forma deformada como uma segunda malha escalada) sem
  escrever chamadas VTK de baixo nível; renderiza em um
  `QtInteractor` embutível direto num layout do PySide6; suporta
  renderização offscreen (`pyvista.OFF_SCREEN = True`) para os
  testes de fumaça.
- **Empacotamento: PyInstaller**, gerando um único executável Windows
  (`--onefile` ou `--onedir`, a decidir no incremento de
  empacotamento conforme o tamanho final do bundle VTK). Motivos:
  ferramenta padrão de fato para distribuir aplicações PySide6/VTK
  sem exigir Python no computador do usuário; testada em CI via
  GitHub Actions (workflow dedicado, a criar no incremento de
  empacotamento).

## Separação do motor de cálculo

A GUI vive num subpacote próprio, **`estrutura_metalica.gui`**,
dentro do mesmo pacote Python — não um pacote PyPI separado, para
manter um único repositório/versão — mas com as dependências de GUI
(`PySide6`, `pyvista`, `pyvistaqt`) declaradas como um extra
opcional (`pip install estrutura-metalica[gui]`), nunca na lista
`dependencies` principal do `pyproject.toml`. Nenhum módulo de
`estrutura_metalica.model`/`.analysis`/`.normative` importa nada de
`estrutura_metalica.gui` — a dependência é sempre num único sentido
(GUI → motor de cálculo), preservando a possibilidade de usar o
motor de cálculo isoladamente (ex.: como biblioteca num script, ou
futuramente embutido no software de sapatas) sem instalar Qt/VTK.

## Testes

Testada em modo *offscreen* (`QT_QPA_PLATFORM=offscreen` +
`pyvista.OFF_SCREEN = True`), sem precisar de um display real — o
mesmo mecanismo funciona neste ambiente de execução isolado (sem
X11) e em CI. **Diferença consciente frente ao motor de cálculo**:
não se exige 100% de cobertura de linha na GUI — testes de fumaça
(a janela abre, os widgets principais existem, uma ação de usuário
simulada via `QTest`/sinais Qt produz o efeito esperado no estado)
cobrem os caminhos principais; ramos puramente de apresentação
(estilos, layouts, textos estáticos) não são perseguidos linha a
linha. `ruff`/`mypy --strict` continuam se aplicando normalmente ao
código da GUI.

## Alternativas consideradas

- **Tkinter**: já vem com o Python (sem dependência extra), mas sem
  um caminho maduro de embutir um viewport VTK/PyVista, e com
  widgets de tabela/formulário mais limitados para o volume de dados
  de um modelo estrutural (múltiplos nós/elementos/cargas).
- **PyQt6** (em vez de PySide6): API quase idêntica, mas licenciado
  GPLv3 (ou licença comercial paga) — exigiria abrir o código da GUI
  ou pagar licença para distribuir um `.exe` fechado. PySide6/LGPLv3
  permite distribuição fechada normalmente.
- **Aplicação web (Flask/FastAPI + Three.js/Plotly)**: adiaria a
  necessidade de empacotamento nativo, mas trocaria "rodar um
  `.exe`" por "rodar um servidor local" — pior experiência para o
  usuário-alvo (engenheiro sem infraestrutura de servidor), e exigiria
  reimplementar a interação de viewport 3D (rotação/zoom/clique) do
  zero em JavaScript em vez de reaproveitar VTK.
- **Matplotlib 3D** para o viewport, em vez de PyVista/VTK: mais leve
  para instalar, mas interação 3D (rotação suave, seleção de
  objetos por clique — necessária para a inserção interativa de nós
  planejada) é sabidamente pobre no `mplot3d`; VTK é a ferramenta de
  visualização científica 3D de fato no ecossistema científico
  Python.

## Consequências

- Uma nova árvore de dependências pesada (Qt + VTK) passa a existir
  no repositório, mas só é instalada por quem pedir o extra `[gui]`
  — quem só quer o motor de cálculo (`pip install estrutura-metalica`)
  não baixa nada disso.
- O executável empacotado tende a ser grande (o bundle VTK sozinho
  já soma dezenas de MB) — aceitável para uma ferramenta de desktop
  de engenharia, mas a decisão de `--onefile` vs. `--onedir` fica
  para o incremento de empacotamento, quando o tamanho real puder
  ser medido.
- Testar a GUI em CI exige o ambiente `QT_QPA_PLATFORM=offscreen`
  configurado no workflow (nenhum display real disponível nos
  runners padrão do GitHub Actions) — replicado aqui desde o
  primeiro esqueleto da GUI para não descobrir problemas de
  ambiente só no incremento de empacotamento.
