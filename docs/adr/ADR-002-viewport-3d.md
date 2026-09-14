# ADR-002 — Viewport 3D (representação visual do modelo)

- Status: aceita
- Data: 2026-09-14

## Contexto

ADR-001 já decidiu a biblioteca (PyVista + pyvistaqt sobre VTK) e o
mecanismo de teste *offscreen* do viewport 3D. Falta decidir COMO o
modelo estrutural é desenhado nele: que geometria representa cada
entidade (nó, elemento, apoio, carga, forma deformada), quando o
viewport é reconstruído, e como ele se conecta ao resto da GUI — sem
ainda implementar a inserção interativa de nós por clique (isso é
ADR-003/task #135, um incremento posterior que consome a arquitetura
decidida aqui).

## Decisão

### Módulo e widget

`estrutura_metalica.gui.viewport_3d.ModelViewport(QWidget)` — embute
um `pyvistaqt.QtInteractor` (que já é um `QWidget`) num layout único.
O `QtInteractor` fica acessível como atributo público
(`self.interactor`) e o `pyvista.Plotter` subjacente como
`self.interactor` mesmo (pyvistaqt faz o `QtInteractor` herdar de
`Plotter`) — nenhuma camada de abstração extra por cima, para que
ADR-003 possa registrar um observador de clique (`enable_point_picking`/
`iren.AddObserver`) diretamente sobre ele sem precisar expor API nova.

### Representação visual de cada entidade

Reconstrução completa a cada atualização (ver "Estratégia de
atualização" abaixo) — sem *diffing* incremental de atores, pela
simplicidade e porque os modelos lançados nesta GUI (lançamento manual
via tabelas) são pequenos o suficiente para isso não pesar:

- **Nós**: pontos renderizados como esferas
  (`add_points(..., render_points_as_spheres=True, point_size=...)`)
  — mais barato que um `glyph()` de malha de esfera de verdade, com a
  mesma leitura visual. Rótulo do id do nó via `add_point_labels`,
  sempre visível nesta fase (sem toggle de liga/desliga — fica para um
  incremento futuro se a poluição visual em modelos maiores for um
  problema real).
- **Elementos**: linhas retas entre os nós de início/fim
  (`pv.PolyData(points, lines=...)`), NÃO tubos/extrusão da seção
  real — ver ATENÇÃO 1 abaixo. Cor por tipo de elemento (paleta fixa,
  não configurável nesta fase): `Column` azul, `Beam` verde,
  `Bracing` laranja — a mesma convenção de cores em toda a aba, para
  o usuário reconhecer o tipo pela cor sem precisar consultar a
  tabela da aba Modelo.
- **Apoios**: um glifo pequeno na posição do nó, forma por tipo —
  cubo vermelho para engaste (`Support.fixed`), cone vermelho para
  rótula (`Support.pinned`) — SEM orientação (não aponta na direção
  de nenhum eixo restringido específico) nem suporte a uma combinação
  arbitrária de GDL restringidos (ver ATENÇÃO 3 em `model_tab`): só
  distingue "engastado" de "rotulado", a única distinção que a aba
  Modelo hoje produz. Tamanho do glifo proporcional à maior dimensão
  do modelo (não um valor absoluto fixo em metros), para continuar
  visível tanto num modelo de 1 m quanto de 100 m.
- **Cargas nodais**: seta (`pv.Arrow`) na direção do vetor força
  ``(fx, fy, fz)``, comprimento proporcional à magnitude da força
  relativa à maior carga do caso (a maior seta do desenho sempre tem
  um comprimento fixo relativo ao tamanho do modelo) — cor laranja.
  Momentos nodais (``mx, my, mz``) NÃO são desenhados nesta fase — ver
  ATENÇÃO 2.
- **Forma deformada** (só quando há um `AnalysisResult`): uma segunda
  malha de linhas usando as coordenadas dos nós DESLOCADAS
  (``node.xyz + result.displacements[node.id][:3] * escala``), cor
  magenta, semi-transparente (``opacity=0.6``) sobreposta à malha
  original (que continua desenhada, para comparação visual). Fator de
  escala AUTOMÁTICO, não fixo: calculado para que o maior
  deslocamento nodal do resultado corresponda a ~10% da maior
  dimensão do modelo (``escala = 0.10 * bounding_box_diagonal /
  max_displacement``, com salvaguarda para ``max_displacement == 0``
  — nesse caso não desenha a forma deformada, o modelo não se moveu).

### Estratégia de atualização — dois gatilhos, dois sinais

Reaproveita o mecanismo de sinal Qt já usado por `ChecksTab` (mantém
a dependência numa via só: viewport → modelo/análise, nunca o
contrário):

- **`ModelTab.model_built = Signal(object, object)`** (novo sinal,
  ``(StructuralModel, LoadCase)``): emitido sempre que `run_analysis()`
  monta o modelo e o caso de carga com sucesso, ANTES de chamar
  `solve()` — assim a geometria aparece no viewport mesmo quando a
  análise falha depois (mecanismo, apoio insuficiente etc.), o que
  ajuda o usuário a inspecionar visualmente ONDE pode estar o
  problema de modelagem.
- **`ModelTab.analysis_completed`** (já existe, usado por
  `ChecksTab`): o viewport também se conecta a ele para desenhar a
  forma deformada por cima da geometria já mostrada pelo
  `model_built`.

`ModelViewport` expõe `show_model(model, load_case)` (nós, elementos,
apoios, cargas — chamado a partir de `model_built`) e
`show_deformed_shape(model, result)` (chamado a partir de
`analysis_completed`, complementa o desenho já presente em vez de
substituí-lo). Câmera: `reset_camera()` após `show_model` (nunca após
`show_deformed_shape`, para não perder o enquadramento que o usuário
já ajustou manualmente ao só adicionar a forma deformada).

### Interação de câmera

Controle de câmera padrão do VTK (rotação/zoom/pan com mouse) — nenhum
código de câmera customizado nesta fase. Isso já vem "de graça" do
`QtInteractor`.

## Testes

Mesmo mecanismo *offscreen* de ADR-001 (`QT_QPA_PLATFORM=offscreen` +
`pyvista.OFF_SCREEN = True`). Sem comparação de imagem renderizada
(pixel a pixel) — abordagem frágil e fora de escopo. Os testes
verificam a LÓGICA de construção da cena: número/tipo de atores
adicionados ao `Plotter`, bounds da malha de elementos batendo com as
coordenadas dos nós, presença/ausência da malha de forma deformada
conforme o resultado tem ou não deslocamento, escala calculada
corretamente a partir de um deslocamento conhecido.

## Alternativas consideradas

- **Extrusão da seção real (tubo/perfil verdadeiro) em vez de
  linha**: visualmente mais rica (um pilar apareceria com a largura
  real da mesa), mas exige gerar uma seção transversal 2D por tipo de
  perfil (I, tubo circular, tubo retangular) e extrudá-la ao longo do
  eixo do elemento com a orientação correta (`orientation_angle` já
  calculado em `stiffness.local_axes`) — trabalho considerável e não
  essencial para o objetivo desta fase (inspecionar visualmente
  topologia/apoios/cargas/forma deformada). Fica como melhoria futura
  explícita (ver ATENÇÃO 1).
- **Atualização incremental de atores** (só adicionar/remover o que
  mudou) em vez de reconstrução completa: mais eficiente para modelos
  grandes, mas exigiria rastrear um mapeamento ator↔entidade e sua
  invalidação — complexidade desproporcional para modelos lançados à
  mão nesta GUI (dezenas de nós/elementos, não milhares).
- **Legenda gráfica na própria cena** (texto explicando as cores):
  descartada nesta fase — a convenção de cores fica só documentada
  aqui e no docstring do módulo; um widget de legenda visual fica
  para um incremento futuro se a falta dela se mostrar um problema
  real de usabilidade.

## Consequências

1. **ATENÇÃO — elementos são linhas, não a seção real extrudada**:
   um pilar `W310x97` e uma barra de contraventamento fina aparecem
   com a MESMA espessura visual (a cor indica o tipo, não a
   espessura) — não confundir com um desenho de fôrma/detalhamento.
2. **ATENÇÃO — momentos nodais não são desenhados**: uma carga
   ``NodalLoad(mx=..., my=..., mz=...)`` sem componente de força fica
   invisível no viewport (nenhuma seta aparece) mesmo estando presente
   no modelo — só a tabela da aba Modelo mostra esse valor. Um
   incremento futuro pode desenhar momentos como um glifo de "seta
   dupla"/arco, convenção ainda a definir.
3. **ATENÇÃO — apoio sem orientação nem GDL parciais**: o glifo de
   apoio distingue só engaste/rótula (as duas únicas opções que a aba
   Modelo produz hoje — ver ATENÇÃO 3 em `model_tab`); um `Support`
   com combinação arbitrária de GDL restringidos (construído fora
   desta GUI) apareceria com o glifo de rótula OU engaste conforme a
   contagem de GDL restringidos, não uma representação fiel da
   combinação real.
4. A reconstrução completa a cada atualização é aceitável para o
   tamanho de modelo esperado desta GUI, mas deve ser revisitada se um
   incremento futuro permitir importar modelos grandes de um arquivo
   externo.
5. Este ADR deixa o `QtInteractor` diretamente acessível (sem camada
   de abstração) especificamente para não bloquear ADR-003 (inserção
   interativa de nós por clique) — qualquer mudança que esconda essa
   referência precisa revisitar essa decisão.
