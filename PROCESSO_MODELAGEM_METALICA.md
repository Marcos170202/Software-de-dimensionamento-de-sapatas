# Processo de Modelagem — Estrutura Metálica

> Baseado no processo de modelagem do **HyperFrame**
> (https://github.com/candidoalfilho/hyperframe), primeiro software
> brasileiro open-source de análise/dimensionamento estrutural. O
> HyperFrame cobre concreto armado (NBR 6118); este documento copia a
> mesma sequência de etapas e a mesma separação de camadas
> (motor de cálculo × interface), adaptando cada etapa para
> **estruturas de aço** (NBR 8800), e conectando a saída (reações de
> apoio) com o módulo de fundações (sapatas) já existente neste
> repositório.
>
> Este documento é a especificação do PROCESSO — o "como se modela",
> etapa por etapa — não uma reimplementação do HyperFrame. Nenhum
> código do HyperFrame é copiado; apenas a sequência/arquitetura do
> fluxo de trabalho.

## 1. Processo original do HyperFrame (referência)

O HyperFrame modela edifícios de concreto armado em 8 etapas:

1. **Criação do projeto** — assistente de novo projeto ou exemplo pronto.
2. **Lançamento em planta (2D)** — eixos, pilares, vigas (poligonais,
   seções variáveis), contorno de lajes (detecção automática),
   escadas/reservatórios como regiões, aberturas/shafts.
3. **Materiais e cargas** — classe do concreto, aço, presets NBR 6120,
   vento por zona (NBR 6123), combinações (13 ULS + 6 SLS por NBR 8681).
4. **Sincronização 3D** — geração automática do pórtico espacial, 6 GDL
   por nó, diafragma rígido de piso, análise em duas passagens
   (rigidez reduzida ELU + ELS completo).
5. **Análise** — solver (skyline LDL^T), 2ª ordem (P-Δ), modal, sísmica.
6. **Dimensionamento** — vigas T automáticas, viga-parede, pilar-parede,
   lajes/punção/fundações, alvenaria.
7. **Detalhamento** — armaduras, pranchas, desenhos de fundação/alvenaria.
8. **Saída** — SVG, DXF, PDF 1:1 em folha ABNT, memorial de cálculo.

Arquitetura: motor de cálculo puro (`packages/engine`, sem dependências)
separado da interface (`apps/desktop`, Tauri/React/three.js) — o motor
nunca depende da UI.

## 2. Processo adaptado — Estrutura Metálica (NBR 8800)

Mesma sequência de 8 etapas, mesma separação motor↔interface, trocando
apenas o que é específico de concreto armado (NBR 6118) por aço
estrutural (NBR 8800), e adicionando o elo com fundações que este
repositório já cobre.

### Etapa 1 — Criação do projeto
Igual ao HyperFrame: assistente de novo projeto (unidades, norma de
vento/ações a usar) ou carregamento de um exemplo (ex.: galpão em
pórtico simples, um pavimento em steel frame).

### Etapa 2 — Lançamento em planta (2D)
Em vez de pilares/vigas de concreto com seção variável, lança-se:

- **Pilares metálicos**: perfis I/H laminados ou soldados, tubos
  (circulares/retangulares), posição/rotação em planta, nível de
  transferência (igual ao conceito de "transferência" do HyperFrame,
  mas aqui tipicamente para o perfil mudar de seção entre pavimentos).
- **Vigas metálicas**: perfis I/H, U, treliçadas (quando vão grande),
  poligonais como no HyperFrame, com viga mista opcional (laje colaborante
  com conectores de cisalhamento — equivalente à mesa colaborante T
  do HyperFrame, mas modelada como seção mista aço-concreto).
- **Contraventamentos**: elemento específico do aço sem equivalente
  direto no HyperFrame — barras de treliça em X, V ou diagonal única,
  lançadas por painel de pórtico, resistindo apenas a força axial.
- **Ligações (nós)**: cada nó viga-pilar/pilar-contraventamento recebe
  desde já uma classificação (rígida, semirrígida ou rotulada) — decisão
  que no concreto é quase sempre "rígida" por monolitismo, mas no aço
  altera a rigidez do pórtico e por isso precisa ser decidida na
  modelagem, não só no detalhamento.
- **Contorno de lajes**: mesma detecção automática de contorno do
  HyperFrame, mas a laje é steel deck (fôrma de aço incorporada) ou
  laje maciça apoiada em vigas — sem punção de laje lisa (não existe
  laje lisa em steel frame típico).
- Aberturas/shafts: igual ao HyperFrame.

### Etapa 3 — Materiais e cargas
- **Aço estrutural**: classe (ex.: ASTM A36, A572 Gr. 50, A992) em vez
  de classe de concreto/aço CA-50; tabela de perfis (catálogo de
  bitolas comerciais I/H/U/tubo) em vez de seções retangulares/circulares
  de concreto.
- **Cargas permanentes/acidentais**: mesmos presets NBR 6120 do
  HyperFrame (reaproveitáveis sem alteração — a norma de ações não muda
  com o material da estrutura).
- **Vento**: mesmo módulo NBR 6123 do HyperFrame (cartas de coeficiente
  de pressão digitalizadas), reaproveitável — estruturas metálicas
  costumam ser mais sensíveis a vento (menor massa/mais flexíveis), então
  a precisão desse módulo importa ainda mais aqui.
- **Combinações**: mesma NBR 8681, mas os coeficientes de ponderação de
  resistência trocam para os de estruturas de aço (NBR 8800 seção 4),
  e entram combinações específicas de incêndio (ação térmica) quando
  aplicável.

### Etapa 4 — Sincronização 3D
Igual em espírito ao HyperFrame (geração automática do pórtico espacial
a partir da planta, 6 GDL/nó, diafragma rígido de piso quando a laje é
suficientemente rígida no plano), com duas diferenças por causa do aço:

- **Rigidez dos nós**: a matriz de rigidez dos elementos de viga/pilar
  precisa liberar momentos nos GDL rotacionais das extremidades
  classificadas como rotuladas na Etapa 2 (liberação de momento fletor
  na matriz de rigidez do elemento de pórtico) — no concreto armado
  monolítico do HyperFrame isso não existe.
- **Elementos de treliça**: contraventamentos entram como elementos de
  barra biarticulada (só rigidez axial, sem flexão) na mesma malha 3D.

Duas passagens de rigidez do HyperFrame (ELU reduzida / ELS completa)
não se aplicam da mesma forma — aço não fissura como concreto — mas o
princípio de "duas análises com propósitos diferentes" é reaproveitado:
uma análise para verificação de resistência (combinações ELU) e outra
para verificação de deslocamentos/vibração (combinações ELS,
serviço, sem majoração).

### Etapa 5 — Análise
- **Solver**: mesmo princípio (montagem de rigidez global + solução
  direta); o skyline LDL^T do HyperFrame é reaproveitável tal como está,
  pois é agnóstico ao material.
- **2ª ordem**: aço estrutural é tipicamente mais esbelto que concreto,
  então a verificação P-Δ (e P-δ ao longo da barra, via NBR 8800 Anexo D)
  é ainda mais crítica; reaproveita-se a mesma abordagem iterativa do
  HyperFrame (forças laterais fictícias por pavimento, resolvidas até
  convergência).
- **Flambagem**: etapa nova sem equivalente direto no HyperFrame —
  cálculo de comprimento de flambagem (K) por pavimento/contraventamento
  e verificação de flambagem por flexão, torção e flexo-torção
  (NBR 8800 5.3), inexistente em concreto armado convencional.
- **Modal/sísmica**: mesmo módulo do HyperFrame (NBR 15421),
  reaproveitável — mas com massas e rigidezes recalculadas para os
  perfis metálicos.

### Etapa 6 — Dimensionamento (NBR 8800 em vez de NBR 6118)
Troca completa do corpo normativo de dimensionamento, mantendo o mesmo
"loop de dimensionamento" do HyperFrame (percorrer cada elemento,
aplicar verificações da norma, marcar aprovação/reprovação com folga):

- Barras tracionadas (5.2) e comprimidas (5.3 — flambagem por flexão e
  por torção).
- Força cortante resistente (5.4.1.3/5.4.3.1) e momento fletor
  resistente — FLT (flambagem lateral com torção), FLM (flambagem local
  da mesa), FLA (flambagem local da alma) — (5.4.2, Anexo D).
- Interação força axial + momento fletor biaxial (5.5).
- **Ligações** (dimensionamento de parafusos/soldas — sem equivalente
  no HyperFrame, cujas ligações são monolíticas por natureza): ligação
  viga-pilar, base de pilar (chapa de base + chumbadores), emendas.
- Sem equivalente de "viga T colaborante automática", "viga-parede" ou
  "pilar-parede" do HyperFrame — não existem em estrutura metálica
  convencional; em vez disso, entra a verificação de **viga mista**
  (aço-concreto, conectores de cisalhamento) quando houver laje
  colaborante.

### Etapa 7 — Fundações (elo com este repositório)
O HyperFrame já teria fundações (sapatas rígidas, blocos sobre estacas,
radier) como etapa final de dimensionamento. Neste repositório o módulo
de **sapatas** já existe/está em desenvolvimento (ver PDFs normativos na
raiz: NBR 6122, "Fundações Diretas", "Sapatas.pdf"). O processo de
modelagem metálica deste documento entrega exatamente a interface que
esse módulo de fundações precisa como entrada:

- Reações de apoio (Nsd, Vsd, Mx,sd, My,sd) de cada pilar metálico, por
  combinação ULS e ELS — mesma saída que o HyperFrame produziria de um
  pilar de concreto, mas vinda do modelo de aço.
- Não se reinventa aqui verificação geotécnica nem dimensionamento de
  sapata — isso é o módulo já existente/planejado deste repositório
  (ver PDFs de fundações diretas/NBR 6122/Sapatas).

### Etapa 8 — Detalhamento e saída
- **Detalhamento**: lista de perfis por elemento (peso/m, comprimento),
  parafusos/soldas por ligação (diâmetro/quantidade, comprimento de
  solda), plano de contraventamento — equivalente às pranchas de
  armadura do HyperFrame, mas para peças metálicas.
- **Saída**: mesmo conjunto do HyperFrame — SVG (em app), DXF
  (exportação), PDF 1:1 em folha ABNT, memorial de cálculo (agora com
  seções específicas de NBR 8800 em vez de NBR 6118).
- **Quantificação/custo**: peso total de aço por perfil (kg), parafusos
  e área de solda, custo por kg de aço — equivalente ao quantitativo de
  concreto/fôrma/aço do HyperFrame.

## 3. Arquitetura proposta (mesma separação do HyperFrame)

```
motor de cálculo (puro, sem dependências de UI)
├── model/      — tipos de dados: nós, perfis, materiais (aço), ligações
├── geometry/   — geometria 2D do lançamento em planta (reaproveitável)
├── analysis/   — geração do pórtico espacial, solver, 2ª ordem, modal
├── nbr/        — NBR 8800 (tração, compressão, flexão, cortante,
│                 interação, ligações), NBR 6120/6123/8681 (reaproveitados)
├── design/     — loop de dimensionamento + detalhamento de ligações
├── drawing/    — primitivas neutras → SVG/DXF
└── report/     — memorial de cálculo em PDF

interface (2D/3D, inspeção, resultados) — camada fina, sem fórmulas
```

Essa separação — motor de cálculo agnóstico de interface, camada de UI
fina que só chama o motor — é exatamente o princípio que o HyperFrame
segue e que este processo copia deliberadamente.

## 4. O que este documento NÃO faz

- Não copia nenhuma linha de código do HyperFrame (licença MIT do
  HyperFrame permitiria, mas não há necessidade — a lógica de aço é
  toda nova).
- Não substitui o dimensionamento geotécnico/de sapatas já em
  desenvolvimento neste repositório — apenas define a interface
  (reações de apoio) entre os dois módulos.
- Não é, ainda, uma implementação — é a especificação do processo de
  modelagem a ser seguida quando o módulo de estrutura metálica deste
  repositório for implementado.
