# Revisão de código — escopo mínimo (sapata isolada, carga centrada)

**Atenção — limitação do processo:** esta revisão foi feita pelo mesmo agente
que escreveu o código, não por uma segunda instância independente do
a6-revisor rodando numa sessão separada. `.claude/agents/a6-revisor.md`
descreve exatamente essa separação de papéis (revisor sem permissão de
escrita, corretor sem acesso ao próprio veredito) e ela não foi respeitada
aqui por restrição de ambiente. Trate a nota abaixo como autoavaliação
estruturada, não como GATE 2 independente. Recomenda-se que uma sessão nova
de Claude Code, ou um segundo engenheiro, rode `@a6-revisor` de fato sobre
este diff antes de qualquer uso profissional.

## Camada 1 — objetiva

| Ferramenta | Resultado |
|---|---|
| `ruff check calc_core/` | All checks passed |
| `mypy --strict calc_core/` | Success: no issues found in 5 source files |
| `pytest --cov=calc_core` | 21 passed, 100% cobertura de linhas |
| `python tools/checar_rastreabilidade.py` | não existe ainda — verificação manual abaixo |
| `bandit -r calc_core/` | não rodado (sem I/O, sem entrada externa não validada — risco de segurança não se aplica a este módulo) |
| `radon cc calc_core/ -a` | não rodado; funções são pequenas e lineares (ver contagem de ramos abaixo) |

Verificação manual de rastreabilidade: toda função pública em
`calc_core/geotecnico/` tem `Ref.: ABNT NBR 6122:2022, item X, p. Y` e
`[rule: <id>]` correspondente a uma entrada `APROVADA` em `ruleset.yaml`.
Conferido linha a linha:

- `dimensionar_sapata_carga_centrada` → `NBR6122-7.6.1-area-carga-centrada` e `NBR6122-5.6-peso-proprio-minimo` — ambas APROVADA.
- `verificar_dimensao_minima` → `NBR6122-7.7.1-dimensao-minima` — APROVADA.
- `_dimensoes_para_area` e `_arredondar_para_cima` são privadas (prefixo `_`), não carregam docstring de norma porque não implementam cláusula normativa — implementam decisão de engenharia registrada explicitamente no `ruleset.yaml` (campo `observacao` da regra 7.6.1) e no docstring da própria função. Nenhuma função pública ficou sem `[rule: ...]`.

## Camada 2 — semântica

Pergunta única: o código faz o que a regra diz, incluindo domínio de validade
e exceções?

- **NBR6122-7.6.1**: a norma exige tensão uniforme ≤ tensão admissível, sem
  prescrever geometria. O código resolve B×L pelo método da folga igual nas
  quatro bordas do pilar — decisão de engenharia rotulada como tal, não como
  texto normativo (ver `observacao` no ruleset). Domínio (carga sem momento)
  respeitado: a função não aceita entrada de momento, então não há risco de
  ser usada fora do domínio por engano.
- **NBR6122-5.6**: "no mínimo 5%" implementado como piso configurável, não
  como constante oculta. `percentual_peso_proprio` é parâmetro explícito.
- **NBR6122-7.7.1**: sem exceção declarada na norma; código não tem exceção.
  Decisão de *impor* o mínimo em vez de apenas reportar falha é uma extensão
  além do texto literal da norma — documentada no docstring de `geometria.py`
  e coberta por teste (`test_carga_leve_aciona_dimensao_minima`).

Nenhum caso de "caso geral certo com exceção ignorada" identificado neste
escopo porque o escopo não contém exceções ainda (elas ficam em
`kb/pendencias.md`, fora de `calc_core/`).

## Rubrica

| Eixo | Nota | Justificativa |
|---|---|---|
| E1 Aderência normativa | 5 | Toda fórmula rastreada a item+página; decisões de engenharia (folga igual, imposição do mínimo) claramente separadas de texto normativo. |
| E2 Correção numérica | 5 | Verificado por caso calculado à mão + testes de equilíbrio (`sigma*A == N_total`, tolerância 1e-9) + testes de invariância via `hypothesis` (centenas de casos gerados). |
| E3 Robustez | 5 | Toda entrada inválida levanta `ValueError` explícito (`__post_init__`); nenhuma extrapolação silenciosa; sem números mágicos (todos os limiares são parâmetros nomeados com origem normativa documentada). |
| E4 Rastreabilidade | 5 | 100% das funções públicas com item + página + rule ID. |
| E5 Testabilidade | 5 | Puro, determinístico (sem I/O), cobertura de linhas 100%, inclui os quatro tipos de teste que a7-validador.md pede. |

**Nota final = min(média_ponderada, E1, E2) = 5,0** — acima do portão (≥4,0
com E1,E2≥4,5), sob a ressalva de processo do topo deste documento.

## Defeitos encontrados

Nenhum na Camada 1/2 para o escopo implementado. Riscos conhecidos e
**deliberadamente fora do escopo** (não são defeitos deste código, são
lacunas do escopo — ver `kb/pendencias.md` e `CLAUDE.md`):

1. Carga excêntrica (§7.6.2) não implementada — usar este software apenas
   para carga efetivamente centrada.
2. Deslizamento/tombamento (§7.6.3) não implementados.
3. σ_adm é sempre entrada do engenheiro — nunca deduzida de SPT/CPT.
4. Nenhum dimensionamento estrutural (armadura, punção) — apenas geometria
   geotécnica. Sapata "aprovada" por este software ainda precisa de projeto
   estrutural completo (NBR 6118) antes de execução.

## Adendo — 2026-08-26: auditoria de calc_core/sapata_isolada/

O usuário forneceu um pacote maior (19 arquivos, ~6.760 linhas), cobrindo
carga excêntrica, punção, bielas e tirantes, recalques por substrato,
rigidez/grelha sobre base elástica e MEF do solo. Tratado como fonte
EXTERNA a auditar, não como verdade aceita — ao contrário do restante deste
repositório, não passou pelo pipeline A1→A2 completo antes de existir.

**Processo seguido:** leitura visual (imagem da página em 300dpi) da NBR
6118:2023, Seções 8 (materiais), 9.3-9.4 (ancoragem), 19.4 (cisalhamento) e
19.5 (punção), conferindo cada fórmula usada em
`calc_core/sapata_isolada/materiais.py` e `sapata.py` linha a linha contra o
texto normativo — não contra memória de treinamento.

**Resultado: 6 defeitos confirmados, todos corrigidos.** Dois do lado
inseguro (subestimavam exigência ou superestimavam resistência):

1. `fct,m` (fck>50MPa): constante errada (`0,11*fck` em vez de `0,1*(fck+8)`).
2. `Eci`: faltava o parâmetro α_E do agregado (fixava granito=1,0 sempre).
3. `l_b` básico: faltava o piso `>=25φ` exigido pela norma.
4. **`η1` (Tabela 8.2): CA-60 herdava 2,25 de CA-50 em vez de 1,00 — LADO
   INSEGURO** (subestima comprimento de ancoragem necessário para CA-60).
5. `τRd1` (punção, contorno C'): "d" do fator ke em milímetros em vez de
   centímetros — subestimava a resistência (conservador, não inseguro).
6. **`τRd1`: faltava o teto ρ≤0,02 — LADO INSEGURO** em sapata muito armada
   (superestima a resistência à punção reportada).

Ver `ruleset.yaml` (regras `NBR6118-*`) para o detalhe de cada correção, e
`tests/test_sapata_isolada_correcoes.py` para a regressão de cada uma.

**O que NÃO foi auditado nesta rodada** (portado, testado numericamente, mas
sem verificação formula-a-fórmula contra a norma): geotecnia sob carga
excêntrica (núcleo central, diagramas trapezoidal/triangular, FS de
deslizamento/tombamento), recalques (Schmertmann, adensamento de Terzaghi),
bielas e tirantes de Blévot, classificação de rigidez e o modelo de grelha
sobre base elástica de Winkler, MEF do solo, e toda a camada de
exportação/visualização (`pdf.py`, `pranchas.py`, `projecao.py`, `pintura.py`,
`visual2d.py`, `visual3d*.py`). Todos marcados `PENDENTE_HUMANO` em
`ruleset.yaml`, seção `escopo_amplo_em_conferencia` — **nenhum destes é
"aprovado"**, e a interface (`ui/app_completo.py`) exibe esse aviso de forma
permanente, não só na primeira tela.

**Nota de processo:** esta continua sendo uma autoavaliação — não houve
segunda instância independente revisando. A cobertura desta rodada (Seções
8, 9, 19.4, 19.5) foi escolhida por consequência (ruptura frágil/ELU), não
por ser exaustiva; o volume de fórmulas restante (Seções 12, 14, 17, 20, 22
completas) é grande o bastante para não caber em uma sessão — ver
`kb/pendencias.md`.

## Adendo — 2026-08-26: interface do escopo amplo (ui/completo/)

Delegado ao **a3-interface** (conforme pedido explícito do usuário, com um
screenshot de referência) a reconstrução da tela do escopo amplo, para
reproduzir um layout de três colunas com modelo 3D interativo, mapas de
momentos, reação do solo, perfil geológico e exportação de PDF.

O agente reaproveitou integralmente os desenhos e o exportador que já
existiam no pacote portado (`visual2d.py`, `visual3d.py`,
`visual3d_momentos.py`, `projecao.py`, `pintura.py`, `pdf.py`, `pranchas.py`)
— não escreveu nenhuma rotina de cálculo nova. `ui/app_completo.py` virou um
lançador fino para o novo pacote `ui/completo/` (app, formulário,
visualização, resultado, tema, empacotamento do modelo visual).

**Revisão independente feita pela sessão principal** (não só aceito o
relatório do subagente):
- Leitura completa dos 5 arquivos novos (`app.py`, `formulario.py`,
  `visualizacao.py`, `resultado.py`, `modelo.py`) — nenhuma conta encontrada
  fora de `calc_core.sapata_isolada`; `resultado.py` só faz `max`/`min` sobre
  listas que o núcleo já produziu (mesma técnica de `relatorio.memorial`).
- Teste headless próprio (Xvfb) que achou e depois **descartou** um falso
  positivo: a aba "Mapa 2D" de Momentos aparentava não desenhar nada
  (0 itens no canvas) — investigado e confirmado como artefato do teste (a
  aba nunca tinha sido selecionada, então o Tkinter não deu tamanho real ao
  canvas). Selecionando a aba de verdade antes de medir, ela desenha 954
  itens normalmente — as quatro abas de visualização, exportação de PDF
  (`%PDF-` válido, ~100 KB), modo verificação e os botões "copiar do
  automático" foram confirmados funcionando de ponta a ponta.
- `ruff` (padrão completo) tinha 17 avisos de estilo (import não ordenado,
  `Optional[X]` em vez de `X | None`, um loop por índice em vez de
  `enumerate`, concatenação implícita de string numa tupla) — corrigidos
  (`--fix` + 2 ajustes manuais) e reconferidos com o mesmo teste headless
  para garantir que a limpeza de estilo não mudou comportamento.

Nenhum defeito de cálculo encontrado nesta revisão — esperado, já que a
interface não calcula por construção (a3-interface.md).

## Adendo — 2026-08-27: degrau no campo de momentos (Superfície 3D / Mapa 2D)

Usuário reportou que o diagrama de momentos na aba "Superfície 3D" parecia
errado — com um pico/funil agudo bem sob o pilar, mais parecido com uma
tensão de solo concentrada (sapata flexível) do que com a curva suave de um
balanço engastado. Pedido explícito de investigar até achar uma verificação
correta, e não parar na primeira correção que "parecesse certa".

**Processo:** antes de acionar qualquer agente, a sessão principal reproduziu
o cenário do usuário e renderizou o canvas de verdade — headless, via Xvfb +
Tkinter (`/usr/bin/python3.12`, que tem `tkinter`; o `python3` deste ambiente
não tem) + `canvas.postscript()` + `ghostscript` — para *ver* o defeito, não
só ler o código. Isso confirmou visualmente o pico/funil relatado e permitiu
isolar a causa por eliminação: `grelha.py` e `campo_momentos()` produziam
perfis fisicamente corretos (pico no centro, ~0 nas bordas) quando
inspecionados isoladamente — o defeito não estava no cálculo agregado.

**Causa raiz confirmada:** `momento_1d()` (dentro de `campo_momentos()`,
`momentos.py`), sob a projeção do pilar, fixava a posição na face ESQUERDA ou
DIREITA conforme o SINAL de `pos` (`copysign`), incluindo uma escolha
arbitrária para `pos == 0`. Como as duas faces do pilar quase sempre têm
momentos diferentes (carga excêntrica, o caso normal), isso criava um DEGRAU
artificial exatamente no eixo do pilar — no cenário de reprodução, um salto de
~24,6 kN·m/m em `mx` bem no meio do pilar. Na Superfície 3D isso aparecia como
o pico/funil agudo relatado; no Mapa 2D, como uma aresta reta cruzando o
centro. `campo_de_grelha().clampar()` tinha um defeito relacionado e mais
grave: escolhia o "nó de fora mais próximo" por `min(..., key=|‖c‖ − meia|)`
sem olhar o sinal do nó preenchido — em malha simétrica (o caso comum) o
`min` empatava e sempre devolvia o nó do lado esquerdo, então nós do lado
direito sob o pilar recebiam o valor da face OPOSTA.

**Correção** (delegada ao **a5-estrutural**, releitura visual da NBR
6118:2023 item 22.6.4.1/22.6.4.1.1/22.6.2.2-a antes de decidir): os dois
clamps por sinal foram substituídos por interpolação linear entre os valores
das duas faces do pilar — contínua por construção (bate com a curva externa
nos dois limites), limitada pelos dois valores de face (não pode sugerir
armadura crescente sob o pilar) e simétrica (não depende de convenção de
sinal para `pos == 0`). A norma não define um valor de momento sob a própria
seção de referência — a interpolação é documentada no código como escolha de
desenho do campo de visualização, não como requisito normativo literal. A
grade de amostragem (`nx`/`ny` pontos) também passou a encaixar dois nós
exatamente sobre `±ap/2`/`±bp/2` (as faces do pilar), para que o pico do
campo renderizado reproduza o `M_d` real usado no dimensionamento
(`momento_unitario()`, que não foi tocado — o valor de projeto da armadura
nunca dependeu do clamp com defeito).

Novo arquivo `tests/test_campo_momentos_continuidade.py` (12 casos): sem
degrau sob o pilar (comparado ao maior salto observado fora dele), valor
sempre entre os dois extremos de face, valor exato no eixo = média das faces,
coincidência exata com a curva externa na própria face, simetria por rotação
de 90° (x↔y), platô simétrico para carga centrada, equilíbrio de tensões
(∫σ dA = N, ∫σ·x dA = My, ∫σ·y dA = Mx) preservado, e os mesmos invariantes
para `campo_de_grelha()` com malha assimétrica variando o refinamento (6 a 18
divisões, para não depender de paridade). **Suíte completa: 57/57 passando**
(45 pré-existentes + 12 novos). `ruff --select E9` limpo em todo o repositório.

**Revisão independente feita pela sessão principal** (o processo do
a5-estrutural foi interrompido por limite de sessão da API antes de reportar,
mas o diff que ele já tinha escrito em disco foi conferido do zero, não
apenas aceito):
- Releitura linha a linha do diff de `momentos.py` contra a descrição acima.
- Re-execução dos 12 testes novos e da suíte completa, isoladamente.
- Reprodução numérica direta (fora dos testes do agente) dos valores de `mx`
  perto de `x=0`: antes, salto de 102,16→126,77 exatamente em `x=0`; depois,
  progressão suave e monótona de 102,16 (face esquerda) a 126,77 (face
  direita) passando por vários nós intermediários.
- Nova renderização headless do canvas real (mesmo método usado para achar o
  defeito) confirmando que o degrau desapareceu; o formato geral em "cunha"
  que sobra é a forma correta de um momento de balanço engastado — zero na
  borda livre, máximo na face do pilar — presente tanto em sapata rígida
  quanto flexível (não é um artefato nem indica classificação errada).
- `ruff check calc_core/sapata_isolada/ --select E9` e perfil completo em
  `calc_core/geotecnico/`, `calc_core/modelos.py`, `ui/` (17→0 avisos após 1
  correção manual de estilo pré-existente e não relacionada, um `lambda`
  reatribuído em loop, achado pelo perfil completo em `ui/completo/resultado.py`).
- `mypy --strict` limpo em `calc_core/geotecnico/`, `calc_core/modelos.py`.

**Trabalho relacionado, delegado em paralelo ao a3-interface:** o modo
"Grelha" da Superfície 3D tinha um defeito de rótulo — o cabeçalho dizia
"Grelha discretizada" mas na verdade mostrava o mesmo campo analítico do modo
"Superfície" (`AbaMomentos.atualizar()` nunca chamava `campo_de_grelha()`).
Corrigido: `AbaMomentos` agora monta os dois campos (analítico e o real de
`res.grelha`, via `campo_de_grelha`) e `SuperficieMomentos3D` escolhe a fonte
certa por modo, com um cabeçalho honesto quando a grelha não está disponível
(caindo no campo analítico). Verificado headless que os dois modos mostram
valores numéricos DIFERENTES de fato quando `res.grelha` existe.

**Sobre o "diagrama de tensão no solo" pedido pelo usuário:** já existe e já
varia com o modelo (aba "Reação do solo" / `ReacaoSolo` em `visual2d.py`),
comparando a pressão discretizada (base elástica de Winkler, sensível à
rigidez local) com a pressão rígida linear, rotulada com a classificação
`rigida_nbr`/`22.6.1`. Conferido numericamente pela sessão principal: para o
cenário de reprodução (classificado rígido), as duas curvas praticamente
coincidem (diferença relativa < 1%) — o comportamento fisicamente esperado
para uma sapata rígida, e evidência de que o mecanismo já funciona (não foi
possível, no tempo desta rodada, forçar `dimensionar()` a produzir um caso
genuinamente flexível para conferir a divergência esperada nesse regime —
fica como pendência de teste, não como defeito confirmado).

**Nota de processo:** como no adendo anterior, a auditoria da correção do
a5-estrutural foi feita pela sessão principal, não por uma segunda instância
independente do a6-revisor. `momentos.py` continua em
`escopo_amplo_em_conferencia` no `ruleset.yaml` (`PENDENTE_HUMANO`) — esta
correção não muda esse status; é um conserto de um defeito de desenho já
identificado, não uma auditoria formula-a-fórmula completa do módulo.

## Adendo — 2026-08-27 (2ª rodada): diagramas de momento agora variam com a
## classificação rígida/flexível

O adendo anterior corrigiu o degrau no campo de momentos, mas deixou passar
uma lacuna real do pedido original do usuário: ele pediu que o diagrama de
MOMENTO também variasse conforme a sapata é rígida ou flexível, do mesmo
jeito que o diagrama de tensão no solo já varia — e o "Mapa 2D" e o modo
"Superfície" da "Superfície 3D" continuavam a mostrar sempre o campo
analítico (que assume placa rígida com pressão linear), mesmo quando a
sapata é classificada `FLEXÍVEL` (NBR 6118, 22.6.3), sem nenhum aviso disso
na tela.

**Verificação que confirmou a lacuna:** forçar um caso genuinamente flexível
via `GeometriaImposta` (o "modo verificação" já exposto no formulário —
não é um caso de laboratório inatingível pelo usuário real: `a=b=3,0 m`,
`h=0,30 m` contra `0,93 m` que tornaria rígida) e comparar os dois modelos:
pressão do solo discretizada (Winkler) 97,5–134,8 kPa contra rígida linear
118,8–123,8 kPa (17,4% de diferença no pico — isso já funcionava certo em
`ReacaoSolo`), e confirmar visualmente (renderização headless real, mesmo
método das rodadas anteriores) que o campo de momentos discretizado tem
forma bem diferente do analítico: concentrado numa "ilha" sob o pilar
(comportamento elástico local, esperado numa sapata flexível), contra a
mancha espalhada por toda a base que o modelo rígido sempre produz.

**Correção** (delegada ao a3-interface, só wiring/exibição — nenhuma conta
nova, `momentos.py`/`sapata.py`/`grelha.py`/`ReacaoSolo` não foram tocados):
- `MapaMomentos` (`visual2d.py`) ganhou a mesma capacidade de dois campos que
  a `SuperficieMomentos3D` já tinha (`definir(analitico, grelha, rigida)`,
  botões "Analítico"/"Grelha" na barra da aba "Mapa 2D").
- Fonte padrão agora depende de `res.rigida`: grelha quando a sapata é
  flexível (a hipótese de placa rígida do campo analítico não vale nesse
  caso), analítico quando é rígida — nas duas telas (Mapa 2D e o modo
  "Superfície" da 3D; o modo "Grelha" da 3D já usava sempre o campo real,
  desde a rodada anterior).
- Aviso visível (mesmo estilo de cor `DESTAQUE`/laranja já usado para
  "seção parcialmente comprimida") nas duas telas quando a sapata é
  flexível: "Sapata FLEXÍVEL (NBR 6118, 22.6.3) — o campo analítico assume
  placa rígida; use a Grelha para o comportamento real."
- Rótulo de rodapé em cada desenho agora também informa a fonte ativa
  ("fonte: grelha discretizada" / "campo analítico (placa rígida)").

**Revisão independente feita pela sessão principal** (o processo do
a3-interface foi interrompido de novo por erro de conexão da API antes de
reportar — igual à rodada anterior — mas o diff já escrito em disco foi lido
e conferido do zero):
- Suíte completa (57/57), `ruff --select E9` em `calc_core/sapata_isolada/`,
  perfil completo em `calc_core/geotecnico/`/`calc_core/modelos.py`/`ui/`, e
  `mypy --strict` no mesmo escopo — todos limpos, sem regressão.
- Teste headless de ponta a ponta (Xvfb + `AbaMomentos` real, não só as
  classes de desenho isoladas) com os DOIS cenários — rígido (o de sempre) e
  o flexível forçado acima — confirmando a escolha de fonte certa nos dois
  casos, nas duas telas.
- Renderização real (postscript + ghostscript) do caso flexível nas duas
  telas: o "Mapa 2D" mostrou a mancha concentrada sob o pilar com o rótulo
  "fonte: grelha discretizada" e o aviso laranja; a primeira tentativa de
  renderizar a "Superfície 3D" veio em branco — investigado antes de
  concluir que era defeito: era o mesmo artefato de teste já documentado no
  adendo de 2026-08-26 (o Tkinter não dá tamanho real ao canvas de uma aba
  de sub-`Notebook` nunca selecionada). Selecionando a aba "Superfície 3D"
  de verdade antes de medir, a superfície apareceu corretamente — concha
  suave concentrada sob o pilar, rótulo "fonte: grelha discretizada" e o
  mesmo aviso. Não era um defeito do código.

## Adendo — 2026-08-27 (3ª rodada): superfície 3D de tensão no solo

O pedido original do usuário (screenshot de referência, início da interface
do escopo amplo) foi por "modelos 3D interativos que indicam momentos,
cargas, tensões no solo". As duas primeiras rodadas trataram o 3D de
momentos; a tensão no solo só tinha o corte 2D de sempre (`ReacaoSolo`,
aba "Reação do solo") — nenhuma superfície 3D. Usuário perguntou
diretamente se isso seria acrescentado.

**Implementado** (delegado ao a3-interface, sem cálculo novo — só desenho,
consumindo `CampoMomentos.sigma` e `ResultadoGrelha.pressao`, que já
existiam prontos): `calc_core/sapata_isolada/visual3d_tensoes.py`
(`SuperficieTensoes3D`, `GradeTensoes`, `grade_de_campo_momentos`,
`grade_de_grelha`), reaproveitando a câmera/projeção/rampa de cores já
testadas em `visual3d_momentos.py`/`projecao.py`/`pintura.py`. Convenção de
desenho documentada no topo do módulo: como tensão no solo é reação de
COMPRESSÃO (não tração, como o momento), a superfície cresce no sentido
OPOSTO ao diagrama de momentos — sobe de um "piso" de referência (σ=0) até
encostar no plano da base (σ=σ_máx), em vez de pendurar abaixo dele.
Sensível à classificação rígida/flexível, mesmo padrão dos outros dois
diagramas (fonte padrão grelha quando `res.rigida is False`, analítico
quando rígida, aviso laranja quando flexível).

Encaixado como sub-aba "Superfície 3D" dentro de "Reação do solo" (que virou
um `Notebook` com "Corte 2D" + "Superfície 3D", espelhando o padrão já usado
em "Momentos"). Como efeito colateral positivo, `PainelVisualizacao` passou
a montar `campo_momentos()`/`campo_de_grelha()` uma única vez por
atualização (`_campos_momento()`) e repassar para as duas abas que
precisam, em vez de recalcular por aba.

**Revisão independente da sessão principal:** suíte completa (57/57), ruff
`--select E9` em `calc_core/sapata_isolada/`, perfil completo em
`calc_core/geotecnico/`/`calc_core/modelos.py`/`ui/`, `mypy --strict` no
mesmo escopo — todos limpos. Renderização real de ponta a ponta (headless,
`PainelVisualizacao` completo, não só a classe de desenho isolada) dos dois
cenários (rígido e flexível forçado): rígido mostrou um plano inclinado liso
(pico 312,7 kPa, "fonte: campo analítico"), coerente com pressão linear sob
carga excêntrica; flexível mostrou uma concentração em "domo" bem sob o
pilar (pico 160,2 kPa, "fonte: grelha discretizada", isolinhas concêntricas)
com o aviso laranja de sapata flexível — os dois fisicamente coerentes com
os respectivos modelos.

## Adendo — 2026-08-27 (4ª rodada): GATE 2 formal — a6-revisor independente

Diferente das rodadas anteriores, esta foi revisada por uma instância
separada do **a6-revisor** rodando como subagente (não a sessão que escreveu
o código) — mais próximo da separação de papéis que `.claude/agents/a6-revisor.md`
pede, embora ainda dentro da mesma sessão orquestradora.

**Origem:** pergunta do usuário sobre classificação uni/bidirecional de
sapata levou a um pipeline completo a1→a2→a5→a6, com 3 rodadas de revisão
(protocolo do próprio a6: 3 tentativas antes de escalar para decisão
humana).

- **Rodada 1**: REPROVADO (nota 4,25) — regra `NBR6118-22.6.1-rigidez`
  aprovada sem `[rule:]` no código e sem teste que a protegesse (mutante que
  apaga a exigência "nas duas direções" passava em todos os testes).
- **Rodada 2**: REPROVADO (nota 4,38) — corrigido o achado da rodada 1, mas
  o a6 achou um mutante espelhado (mesma falha, direção oposta, em
  `sapata.py::_alturas`) e a regra de proibição de redutor de armadura
  (`NBR6118-22.6.2.2a-flexao-duas-direcoes`) também sem tag nem teste.
- **Rodada 3**: **APROVADO — nota final 4,50** (E1=4,5 E2=5,0 E3=4,0 E4=4,5
  E5=4,0). Todos os mutantes das rodadas anteriores confirmados mortos,
  reproduzidos de forma independente pelo próprio a6 (não só aceitos do
  relato do a5).

**Defeitos remanescentes, todos não bloqueantes** (registrados para
disciplina, não para nova rodada — critério do próprio a6):

- **D1 (MÉDIA)**: o teste que protege a proibição de redutor de armadura não
  pega a forma condicional à razão de lados (`if direcao=="Y" and
  min(a,b)/max(a,b)<0.5: As*=0.2`) — exatamente o "redutor por
  classificação uni/bidirecional" que a regra proíbe, porque os dois casos
  de teste existentes (quadrado e alongado) mascaram esse mutante por vias
  diferentes. Reproduzido pelo a6: `a=3,00/b=1,20/h=0,40/ap=bp=0,30/N=4000
  kN` → correto `As_y=33,96 cm²`, mutante `As_y=18,00 cm²` (−47%, lado
  inseguro), suíte 101/101 verde. **Corrigir no próximo toque em
  `sapata.py`, com o teste especificado pelo a6** (sapata alongada onde a
  flexão/bielas governa a direção curta, não a mínima).
- **D2 (BAIXA)**: tolerância de fronteira em `rigidez.py:164` só é
  protegida até `1e-2`; `1e-3` ainda sobrevive.
- **D3 (BAIXA)**: 4 das 14 regras `APROVADA` do ruleset (ancoragem,
  cisalhamento, punção — pré-existentes, fora do escopo desta rodada) citam
  norma+item na docstring mas sem o `[rule: <id>]`/página formais. Zero tags
  órfãs (nenhuma tag sem regra correspondente).
- **D4 (BAIXA, processo)**: `tools/checar_rastreabilidade.py`, previsto na
  Camada 1 do protocolo do a6, não existe neste repositório — a checagem
  cruzada ruleset↔código é feita manualmente a cada rodada.

**Liberado para o a7-validador.** Nenhum destes defeitos altera número
produzido hoje pelo software; D1 é dívida de proteção contra regressão
futura, não um resultado incorreto atual.
