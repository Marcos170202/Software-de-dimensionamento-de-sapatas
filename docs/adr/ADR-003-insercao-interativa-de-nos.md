# ADR-003 — Inserção interativa de nós no viewport 3D

- Status: aceita
- Data: 2026-09-14

## Contexto

ADR-002/task #133 entregaram um viewport 3D só de VISUALIZAÇÃO
(desenha nós/elementos/apoios/cargas/forma deformada a partir do que
já está lançado nas tabelas da aba Modelo). Falta a via inversa: criar
um nó clicando no viewport, sem digitar coordenadas na tabela — a
funcionalidade original pedida para esta fase (histórico do projeto:
"inserção interativa de nós", clique → projeção num plano, alternância
por um botão, Shift+clique para coordenada exata, grade de
referência).

Este ADR decide o mecanismo técnico de clique→coordenada 3D (VTK não
oferece um clique "livre" pronto — só *picking* sobre geometria já
desenhada), como isso se integra ao restante da GUI sem violar a
separação de dependências já estabelecida, e a UX das quatro peças
pedidas.

## Decisão

### Mecanismo de clique → coordenada 3D (plano de inserção)

Um clique de mouse só dá uma posição 2D na tela — para obter um ponto
3D é preciso projetá-lo sobre um plano de referência. **Técnica:
interseção raio-plano manual via `vtkRenderer`**, verificada
funcionando neste ambiente (offscreen incluído):

```python
renderer.SetDisplayPoint(x, y, 0.0); renderer.DisplayToWorld()
near = renderer.GetWorldPoint()  # ponto do raio no plano próximo (near)
renderer.SetDisplayPoint(x, y, 1.0); renderer.DisplayToWorld()
far = renderer.GetWorldPoint()   # ponto do raio no plano distante (far)
# os dois pontos (convertidos de coordenadas homogêneas, dividindo
# por w) definem o raio de projeção da câmera passando pelo clique;
# interseção analítica desse raio com o plano z = Z_INSERCAO dá a
# coordenada 3D exata.
```

Não existe um utilitário de mais alto nível no PyVista para isto —
`enable_point_picking`/`enable_surface_point_picking` só resolvem
*picking* sobre uma malha já renderizada NAQUELE ponto da tela (não
funcionam clicando no vazio); a técnica acima é o padrão VTK para
"projetar um clique num plano arbitrário", por isso é feita
manualmente sobre `self.interactor.renderer` (mesmo widget acessível
sem abstração decidido em ADR-002).

### Plano de inserção

Sempre um plano HORIZONTAL ``z = Z_INSERCAO`` (não um plano
arbitrário orientado pela câmera) — mais simples de entender/prever
para quem está lançando um modelo estrutural (a maioria dos nós de
um pavimento está no mesmo nível Z). ``Z_INSERCAO`` é um campo
numérico editável na própria aba do viewport (``QDoubleSpinBox``,
padrão ``0.0``), não vinculado a nenhum nó/elemento existente —
lançar nós em vários pavimentos significa mudar esse valor entre um
clique e outro.

### Alternância (toggle)

Um `QPushButton` checável, "Inserir nó (clique no viewport)", na
própria `ModelViewport` (não na aba Modelo — a ação acontece no
viewport). Enquanto ativo:

1. Desenha uma **grade de referência** no plano ``z = Z_INSERCAO``
   (``pyvista.Plane`` em modo *wireframe*, dimensionada por
   ``model_scale`` — ver ADR-002 — para ficar proporcional ao modelo
   já lançado, ou um tamanho padrão fixo se o modelo ainda não tem
   nenhum nó) — ajuda a perceber profundidade/posição antes de
   clicar. Removida ao desativar o modo.
2. Registra o clique (ver "Distinguir clique de arraste" abaixo).

Os observadores VTK (`AddObserver`) são registrados UMA VEZ na
construção do widget — nunca adicionados/removidos a cada toggle —
e simplesmente verificam uma flag interna (`self._insert_mode`)
antes de agir, para não acumular observadores duplicados a cada
liga/desliga.

### Distinguir clique de arraste (não conflitar com a câmera)

O estilo de interação padrão do VTK (`vtkInteractorStyleTrackballCamera`)
já usa o botão esquerdo para ORBITAR a câmera durante um arraste — os
observadores de clique não o substituem (evita perder a navegação 3D
de câmera quando o modo de inserção está desligado, e mesmo quando
ligado, um arraste continua orbitando normalmente). Para não inserir
um nó indesejado no FIM de um arraste de câmera: grava a posição de
tela no `LeftButtonPressEvent`; no `LeftButtonReleaseEvent`, compara
com a posição atual — se o deslocamento entre press/release for menor
que um limiar pequeno (``3px``), trata como CLIQUE (insere o nó); caso
contrário, foi um arraste de câmera, ignora.

### Shift+clique — diálogo de coordenada exata

Um clique comum (sem Shift) insere o nó diretamente na coordenada
projetada (rápido, aproximado). **Shift+clique** (`iren.GetShiftKey()`
no evento) abre um diálogo modal simples (`QDialog` com três
`QDoubleSpinBox` X/Y/Z, pré-preenchidos com a coordenada projetada)
para o usuário digitar a posição exata antes de confirmar — cobre o
caso comum de "cliquei perto do lugar certo, mas quero o nó exatamente
em (3.000, 0.000, 2.750)".

### Integração com a aba Modelo (sem acoplar os widgets)

Mesmo padrão de sinal Qt já usado em ADR-002 (mantém a dependência
numa via só): **`ModelViewport.node_inserted = Signal(float, float,
float)`**, emitido com ``(x, y, z)`` tanto no clique simples quanto
após confirmar o diálogo do Shift+clique. `MainWindow` conecta esse
sinal a um novo método `ModelTab.add_node_from_viewport(x, y, z)`,
que:

1. calcula o próximo id livre (novo helper `NodesPanel.next_free_id()`
   — maior id existente + 1, ou 1 se a tabela estiver vazia);
2. chama `self.nodes_panel.add_row(node_id=..., x=x, y=y, z=z)`;
3. muda a aba ativa de volta para "Modelo" (`MainWindow`, não
   `ModelTab` — quem troca de aba é quem tem o `QTabWidget`), para o
   usuário ver a linha nova imediatamente na tabela.

`ModelViewport` nunca importa nada de `model_tab`/`ModelTab` —
continua só emitindo o sinal, igual a `model_built`/
`analysis_completed` no sentido contrário.

### Feedback visual imediato (antes de rodar a análise de novo)

Um nó recém-inserido só vira uma esfera branca "de verdade" na
próxima vez que `show_model` for chamado (isso exige rodar a análise
de novo ou uma ação equivalente — nenhuma mudança nisso aqui). Para
não deixar o clique sem feedback nenhum até lá, `ModelViewport` mantém
um marcador temporário AMARELO (mesmo glifo de esfera, cor
diferente) em cada ponto inserido nesta sessão de edição — nome de
ator fixo `pending_node_markers`, substituído (não acumulado) a cada
inserção. `show_model()` limpa esses marcadores (`self.interactor.clear()`
já cuida disso) — na prática, assim que os nós pendentes viram nós
reais desenhados em branco.

## Alternativas consideradas

- **Plano orientado pela câmera** (perpendicular à direção de visão,
  passando por um ponto de referência) em vez de sempre horizontal:
  mais "natural" para desenhar em qualquer orientação, mas
  imprevisível para lançar um modelo estrutural real (a maioria dos
  nós de projeto está no mesmo nível Z de um pavimento) — descartado
  em favor de um plano horizontal explícito e prevísivel.
- **Novo estilo de interação VTK dedicado** (`vtkInteractorStyleUser`
  customizado) em vez de observadores sobre o estilo padrão: daria
  controle mais fino, mas trocar o estilo de interação também exige
  reimplementar rotação/zoom/pan manualmente para não perder a
  navegação de câmera de que o usuário já depende — desnecessário
  quando observadores adicionais bastam.
- **`pyvista.enable_point_picking`** (picking sobre geometria
  existente): não serve para clicar no vazio (é o caso comum de
  lançar um nó novo, sem nada desenhado ainda naquele ponto exato).

## Consequências

1. **ATENÇÃO — só planos horizontais**: não dá para inserir um nó
   "no meio do ar" fora do plano ``z = Z_INSERCAO`` atual sem antes
   ajustar esse valor — não há inserção por interseção com um
   elemento/plano inclinado existente.
2. **ATENÇÃO — nó pendente não é validado até rodar a análise de
   novo**: um clique sempre insere a linha na tabela de nós (mesmo
   coordenada duplicada de outro nó, por exemplo) — a mesma validação
   que já existe em `NodesPanel`/`StructuralModel` (ids duplicados,
   etc.) só dispara quando o usuário rodar a análise, igual a
   qualquer edição manual da tabela hoje.
3. O limiar de 3px para distinguir clique de arraste é um valor fixo
   nesta fase (não configurável) — se se mostrar sensível demais
   (inserindo nó em pequenos tremores de mão) ou insensível
   (exigindo clique perfeitamente parado), pode virar uma constante
   ajustável num incremento futuro.
4. Este ADR não cobre inserção de ELEMENTOS por clique (só nós) —
   ligar dois nós clicados continua exigindo a tabela de Elementos da
   aba Modelo.
