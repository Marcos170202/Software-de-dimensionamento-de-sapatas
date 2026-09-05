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

## Adendo 2026-08-28 — corte de espraiamento por camada (pirâmide/tronco Boussinesq × 2V:1H)

Também revisado por instâncias separadas de **a6-revisor** (subagente,
sessão própria a cada rodada), sobre um pipeline completo
a1→a2→a4→a3→a6, com o mesmo limite de 3 rodadas.

**Origem:** pedido do usuário por uma visualização de "espraiamento" de
tensões em corte, no estilo de diagrama trapezoidal clássico (q1>q2>q3,
larguras crescendo com a profundidade). a1 confirmou busca negativa
(Boussinesq/Newmark e 2V:1H não aparecem na NBR 6122:2022 nem na apostila
Bastos); a2 aprovou as duas fórmulas como `praticas_consagradas` — a
primeira sem restrição, a segunda (`PC-ESPRAIAMENTO-2V1H`)
`APROVADA_COM_USO_RESTRITO`, proibida para recalque/capacidade de carga
(subestima Δσ ~25% na faixa rasa, lado inseguro) — restrito a
visualização/comparação.

- **Rodada 1**: REPROVADO (nota 3,78, veto E1/E5) — o texto do ruleset v6
  dizia "L1/L2/L3 = espessuras da camada"; o código desenhava a largura
  equivalente do tronco sob o mesmo símbolo "L" (camada de espessura real
  3,90 m exibida como "L2 = 6,69 m"); `q_i` exibido era a média da camada,
  não o valor de interface (variação real de 9× resumida num único
  número); `visual2d.py` com 0% de cobertura, 5/5 mutantes sobreviventes.
- **Entre rodadas**: a2 reescreveu `REQ-PROP-03` na v7 do ruleset — "L"
  abolido do croqui (colidia com 3 significados diferentes no repositório);
  novos símbolos `a_eq,i`/`b_eq,i` (largura, por INTERFACE) e `h_i`
  (espessura, por CAMADA, opcional); q exibido passa a ser o de interface.
  a4 expôs `ResultadoSapata.q_servico` (pressão de serviço total, calculada
  sempre) para eliminar uma reconstituição frágil (`q_líquido + sobrecarga`)
  que causava diagnóstico falso com `verificar_recalque=False`.
- **Rodada 2**: REPROVADO (nota 4,40, veto único em E5=3,0) — a substância
  já estava certa (E1=4,5 E2=5,0), mas o caminho de DESENHO
  (`desenhar()`/`_espraiamento()`) continuava com 0% de cobertura e 10/10
  mutantes plantados pelo a6 sobreviviam, incluindo o retorno do símbolo
  proibido "L". a6 aceitou um desvio do a3 (usar `PontoPropagacao.
  delta_sigma` em vez de `CamadaPropagacao.delta_sigma_topo/base`, ambos
  idênticos por construção — verificado em 184 pares, diferença 0,000e+00)
  e despachou 3 correções textuais não bloqueantes ao a2 (ruleset v8).
- **Rodada 3**: **APROVADO — nota final 4,60** (E1=4,6 E2=5,0 E3=4,5
  E4=4,5 E5=4,2). Cinco métodos estáticos puros extraídos do caminho de
  desenho (`_eixo_valor`, `_meia_com_tronco`, `_clampx`, `_pontos_visiveis`,
  `_rotulos_de_interface`); os 10 mutantes da rodada 2 reproduzidos e
  mortos pelo próprio a6, um a um, cada um pelo teste nominal da tabela
  mutante→teste (sem morte por acidente); `desenhar()` 0%→89%,
  `_espraiamento()` 0%→92% de cobertura; equivalência da refatoração
  confirmada byte a byte (1528 itens de canvas idênticos, 8 cenários,
  antes/depois da extração).

**Defeitos remanescentes, todos não bloqueantes** (0 ALTA, 2 MÉDIA, 9
BAIXA — critério do próprio a6, que também fixou o limite de 3 rodadas: se
a rodada 3 entregasse os testes que matam os mutantes, o portão fecharia
sem rodada 4 nem escalada; entregou):

- **E1 (MÉDIA)**: dois mutantes de "fiação" (chamada, não lógica)
  sobrevivem — apagar a chamada a `_meia_com_tronco` ou trocar `clampx` por
  identidade não derruba nenhum teste, porque os helpers puros são
  testados isoladamente mas não sua invocação real em `desenhar()`. Layout
  apenas (o tronco voltaria a vazar do canvas sob 2V:1H); nenhum número
  errado.
- **E2 (MÉDIA)**: as duas correções desta rodada (âncora da mensagem de
  erro; `_avisos_nao_promovidos` chaveado por `prop.fonte`) estão certas
  mas sem teste — reversíveis em silêncio no próximo commit.
- **E3–E9 (BAIXA)**: comentário de justificativa com erro de fato (o
  próprio a6 corrigindo um engano seu da rodada anterior); dois achados
  reincidentes de rodadas 1–2 explicitamente despriorizados (`... or dim`
  morto na geometria; rótulo de largura fora do orçamento horizontal);
  parâmetro não utilizado numa assinatura de 12 posicionais; um dublê de
  canvas de teste cujo `delete()` é menos fiel que o real; um defeito
  **pré-existente e não relacionado a esta feature** achado por render
  (rótulo do nível d'água cortado ~30px fora do canvas, idêntico na base);
  `tools/checar_rastreabilidade.py` ainda não existe (3ª rodada
  consecutiva com a Camada 1 parcialmente manual).
- **Memorial PDF**: `pranchas.py` não foi tocado em nenhuma das 3 rodadas
  — a feature existe só na tela. Registrado como pendência COM GATILHO
  (não bloqueante) na v8 do ruleset, não como omissão silenciosa.

**Liberado para o a7-validador, com uma ressalva explícita do a6:** a
feature está aprovada na superfície TELA. O memorial PDF não a contém —
nenhum caso de validação que confira o PDF pode ser declarado ALTA
enquanto a seção não existir; declarar como descoberto, não aprovado.

## Adendo 2026-08-28 — salvar/abrir projeto (.s7proj) + importar/exportar
## Excel (`ui/completo/`): a saga completa, das 3 rodadas de GATE 2 ao GATE
## 3 reprovado

Feature de I/O puro pedida pelo usuário: salvar/reabrir o estado completo
do formulário num arquivo próprio (`.s7proj`, JSON versionado), importar
pilar/cargas e perfil geotécnico de uma planilha Excel de layout fixo, e
exportar um resumo tabular do resultado já calculado em Excel.
`calc_core/` continua sem dependência externa — `openpyxl` entra só em
`ui/completo/`. Revisada por a6-revisor (subagente, sessão própria por
rodada) e validada por a7-validador (este adendo), ambos sobre o mesmo
limite de 3 rodadas de GATE 2 já usado pelas features anteriores.

### GATE 2 — três rodadas

- **Rodada 1 (REPROVADO, nota 3,5):** `openpyxl` fora de
  `requirements-dev.txt` quebrava o CI; nomes de caso de carga duplicados
  colapsados em silêncio na tela (`por_nome = {c.nome: c for c in casos}`
  sem checar duplicata — carga permanente subestimada); resultado
  calculado não invalidado ao trocar de projeto (memorial de um projeto
  exportável enquanto a tela já mostrava outro); `Camada`/`Solo` sem
  nenhuma validação de domínio (espessura negativa dava recalque 0 mm e
  "APROVADO" em vez de erro).
- **Rodada 2 (REPROVADO, nota 4,0):** as próprias correções da rodada 1
  abriram dois ALTA novos — `ler_solo()` fora do `try/except` de
  `_importar_excel` matando a importação em silêncio no meio de um estado
  parcial (mesma classe de defeito da rodada 1, por um caminho novo), e 6
  erros de lint `TRY004` quebrando o comando exato do CI. Mais 4 MÉDIA
  (domínio numérico de `OpcoesProjeto` sem checagem de faixa;
  `modelo_reacao`/`modelo_armadura_rigida` aceitando qualquer string e
  caindo em silêncio no ramo errado do núcleo; mensagem de conflito
  ap/bp confusa quando a primeira linha estava em branco; **N1** — aviso
  de "campos não repostos" comparando cada `CasoCarga` carregado contra o
  default CRU do dataclass em vez do que `ler_casos` de fato repõe para
  Q/W, gerando 6 avisos falsos em todo projeto salvo com W).
- **Rodada 3 (APROVADO, nota 4,5):** os dois ALTA fechados sem reabrir a
  mesma classe de defeito (varredura própria do a6, não só as correções
  pontuais); painel de visualização invalidado junto com o resultado;
  validação de domínio/enum/null em `OpcoesProjeto` contra os valores que
  o NÚCLEO de fato aceita; N.A. da planilha lido e validado em todas as
  linhas. **N1 ficou aberto, único MÉDIA remanescente**, corrigido depois
  da aprovação em commit separado (`2b78697`) — `campos_divergentes_do_
  default` reescrito para comparar cada caso pelo NOME do slot
  (`_CASOS_REFERENCIA_POR_NOME`, espelhando exatamente `ler_casos`), não
  pelo default cru do dataclass; 3 testes novos (401 no total).

### GATE 3 (a7-validador) — REPROVADO

Diferente das features anteriores desta sessão, o a6 foi explícito: "o
que a7 deve exercitar são os CAMINHOS DE DADOS, não fórmulas" — não há
exemplo bibliográfico a reproduzir, e sim fidelidade de transporte:
tela→arquivo→tela, planilha vs. digitado, PDF vs. Excel do mesmo cálculo.
Detalhe completo em `relatorios/conformidade.md`, adendo do mesmo dia;
resumo aqui porque, ao contrário das rodadas de GATE 2 acima, o GATE 3
encontrou um `BUG` que as 3 rodadas de a6 não pegaram:

- **Round-trip `.s7proj` tela-a-tela: PASSOU**, 100 % dos campos com
  widget na tela batem exatamente após salvar/reabrir (incluindo um
  perfil de 3 camadas com uma coesiva completa).
- **Planilha vs. digitado à mão: REPROVOU — `BUG` novo, ALTA,
  devolvido a A3.** `excel_import.py::importar_perfil_geotecnico`
  constrói cada `Camada` sem `gamma_nat`/`gamma_sat`/`phi`/`coesao` (a
  aba "Perfil geotécnico" não tem coluna para eles) — toda camada
  importada por planilha recebe em silêncio os defaults do dataclass
  (18,0 / 20,0 / 30,0 / 0,0), nunca os valores reais do perfil. Como
  `gamma_nat`/`gamma_sat` entram direto na tensão vertical efetiva que
  alimenta o recalque por adensamento, um mesmo perfil geotécnico
  digitado na tela e importado por planilha (com os MESMOS valores nas
  colunas que a planilha de fato tem) produziu recalques 6,8 % diferentes
  neste caso de teste — sem NENHUM aviso ao usuário, ao contrário do
  padrão já estabelecido em `projeto.CAMPOS_NAO_REPOSTOS`
  (documentado, avisado nominalmente, testado) para a mesma classe de
  perda de dado no caminho `.s7proj`. Nenhuma das 3 rodadas de GATE 2
  tinha um teste que comparasse um perfil importado contra o mesmo perfil
  digitado — só contra os valores que a própria planilha de exemplo já
  trazia, o que nunca expôs a lacuna.
- **PDF vs. Excel do mesmo cálculo: PASSOU** nos valores conferidos
  (tensões, armaduras, veredito, dígito a dígito, via extrator de texto
  escrito para esta rodada — o PDF é `zlib` cru, sem biblioteca). Achado
  MÉDIA nesta própria feature (não pré-existente): `excel_export.py`
  recompõe, com um `and` de 4 booleanos, exatamente a mesma composição
  que `Sapata._montar_resultado` já usa para `resultado.aprovado` —
  duplicação sem teste que pegue deriva se o núcleo mudar o critério.
  Achado BAIXA pré-existente e fora desta feature, mas só percebido pela
  comparação PDF×Excel pedida: `pranchas.py:340` imprime "CA-50" fixo
  independente do aço real (auto-inconsistente com a linha de materiais
  do mesmo PDF, que mostra a categoria certa).
- **N1: confirmado corrigido** nas duas direções (falso-positivo — G/Q/W
  típico não gera mais aviso; falso-negativo — `.s7proj` editado à mão já
  tinha teste permanente, reconfirmado passando).
- **REQ estrutural (nenhum veredito na UI):** confirmado por leitura
  integral dos 3 módulos, com a única exceção já citada acima
  (`ok_direcao`).
- **Equilíbrio (salvar/reabrir não muda `dimensionar()`):** confirmado
  para sapata rígida, flexível e com vento — bit-idêntico, sem teste
  permanente prévio para os 3 perfis.

**Diferença em relação ao padrão das features anteriores:** todas as
feições revisadas nesta sessão até aqui (espraiamento, corte por camada)
tiveram GATE 3 aprovado depois de um GATE 2 já rigoroso — a auditoria
independente do a7 reconfirmava, sem achar `BUG` novo. Nesta feature, o
a7 achou um `BUG` real (planilha-vs-digitado) que passou pelas 3 rodadas
de a6 — não porque a6 tenha sido menos rigoroso (a rodada 2 pegou uma
classe de defeito irmã, `ler_solo()` fora do `try/except`), mas porque
nenhuma das 3 rodadas comparou um perfil IMPORTADO com o MESMO perfil
DIGITADO — o tipo de comparação cruzada de caminho de dado que só um
validador dedicado a isso (e não a um formulário de cada vez) tende a
fazer. Registrado aqui como reforço do valor de A7 ser um agente
separado de A6, não uma repetição do mesmo checklist.

## Adendo 2026-08-29 — salvar/abrir projeto + Excel: correção do defeito
## ALTA, GATE 3 repetido e **APROVADO**

Fecha o ciclo aberto no adendo anterior (2026-08-28, GATE 3 reprovado).
Entre um adendo e outro: (a) A3 corrigiu `excel_import.py::
importar_perfil_geotecnico` (commit `42badce`), acrescentando 4 colunas
novas à aba "Perfil geotécnico" (`gamma_nat`, `gamma_sat` — OBRIGATÓRIAS,
mesmo tratamento que `espessura`; `phi`, `coesao` — OPCIONAIS, mesmo
tratamento que `nspt`/`Cc`/`e0`/`cv`/`Es`) e uma função
`_validar_cabecalho` que recusa qualquer planilha cujo cabeçalho da linha
1 não bata exatamente com o layout esperado, checada ANTES de ler
qualquer linha de dados — fechando também um segundo vetor do mesmo
defeito que só apareceria quando o layout mudasse de versão (achado do
a6 numa revisão focada intermediária, junto com 2 testes de fronteira de
domínio que faltavam); (b) 10 testes novos em
`tests/test_projeto_e_excel.py` (93 → 103).

Esta rodada de A7 **não reabriu** os itens já confirmados PASSOU
anteriormente (round-trip `.s7proj` tela-a-tela, N1, PDF-vs-Excel, REQ
estrutural na UI, equilíbrio salvar/reabrir) — nenhum motivo concreto
para desconfiar deles à luz de uma correção pontual em 2 arquivos.
Focou em reproduzir, de forma independente (não relendo o despacho), o
experimento que reprovou a rodada anterior:

- **Planilha vs. digitado à mão, com gamma_nat/gamma_sat divergentes dos
  defaults: PASSOU.** Perfil de 1 camada com gamma_nat=15,5/gamma_sat=19,3
  (valores fabricados por mim, distintos dos usados no teste automatizado
  e dos defaults 18,0/20,0) — recalque importado e recalque calculado a
  partir do mesmo perfil montado diretamente no núcleo bateram
  **exatamente**: `289.78425853131404 mm` nos dois casos
  (`asdict(resultado_importado) == asdict(resultado_manual)` → `True`).
  Como controle, o mesmo perfil com gamma_nat/gamma_sat nos DEFAULTS do
  dataclass (o que a versão com bug produzia) deu `270.71 mm` — confirma
  que a divergência de ~7% do relatório anterior era real e que o fix a
  fecha de fato, não que o cenário deixou de ser discriminante.
- **Layout antigo (9 colunas) recusado: PASSOU.** Reproduzi a planilha
  exata do relatório anterior (cabeçalho de 9 colunas, linha com nspt=8,
  Cc=0,45, e0=1,10, cv=0,02) — `ValueError` citando o cabeçalho, não mais
  a leitura silenciosa nas posições erradas que o a6 tinha achado numa
  revisão intermediária (defeito D1, já corrigido antes desta rodada).
- **`phi`/`coesao` opcionais: PASSOU.** Célula em branco → defaults do
  dataclass (30,0 / 0,0); célula preenchida → valor repassado sem
  alteração.
- **Mutação própria, independente da suíte:** reverti, numa cópia isolada
  do arquivo, (1) a passagem de `gamma_nat`/`gamma_sat` a `Camada(...)` e
  (2) a chamada a `_validar_cabecalho` — os dois mutantes morreram nos
  testes correspondentes (`test_excel_gamma_nat_gamma_sat_explicitos_...`
  e `test_excel_perfil_cabecalho_layout_antigo_e_recusado_...`),
  confirmando que a proteção é o que segura o teste, não coincidência de
  dados de exemplo.
- **Varredura por defeito novo nos 2 arquivos tocados:** nenhum
  encontrado. `ruff check ui/completo/excel_import.py` limpo (idêntico ao
  baseline); os 5 `E402` de `tests/test_projeto_e_excel.py` são
  pré-existentes (reproduzidos rodando `ruff` sobre a versão do arquivo
  anterior a este diff), não introduzidos aqui. Dos 7 itens que a revisão
  focada do a6 tinha listado, os 2 marcados "obrigatório antes do
  release" (D1 — validar cabeçalho; D2 — testes de domínio para
  gamma_nat=0/gamma_sat negativo/phi negativo) estão feitos e verificados
  por mim; D3 (argumentos nomeados + `extras` tipado em vez de `**kwargs`
  cru) foi adotado incidentalmente na forma exata sugerida; D4 (número
  mágico `13` em `_linha_em_branco` em vez de `len(CABECALHO_PERFIL)`)
  segue **não corrigido** — é BAIXA/"recomendado", não bloqueante, e não
  foi agravado por este diff.
- **Casos de fronteira adicionais, fora da suíte:** aba de perfil só com
  cabeçalho (zero linhas) → "nenhuma camada encontrada"; aba
  completamente vazia (sem cabeçalho) → erro de cabeçalho; cabeçalho com
  espaço em branco extra por célula → tolerado (`str.strip()`), o que é
  comportamento pretendido (tolerar formatação, não estrutura).

**Suíte completa:** `pytest tests/ -q` (Xvfb, `CI=true`) → **411 passed**
(103 só no arquivo da feature). Confere com o declarado no despacho.

**Itens fora do escopo desta correção, mantidos sem reavaliar** (não
tocados por este diff, achados já registrados): `excel_export.py` —
`ok_direcao` recompõe a lógica de composição do núcleo em vez de
consumir um campo único (MÉDIA); `pranchas.py:340` — rótulo "CA-50" fixo
no PDF, independente do aço real do projeto (BAIXA).

### Veredito — GATE 3

**APROVADO.** O defeito ALTA que reprovou a rodada de 2026-08-28 está
fechado e reconfirmado por experimento independente (não apenas relido
do despacho de correção), o vetor de regressão por versão de layout que
o motivou (D1) também está fechado, e nenhum defeito novo apareceu nos
arquivos tocados. Detalhe completo (reprodução do experimento, mutação,
veredito por item) em `relatorios/conformidade.md`, mesmo adendo, e em
`relatorios/revisao_codigo.json`.

## Adendo 2026-09-01 — σ_adm a partir de SPT/CPT (Terzaghi/Vesic teórico +
## Teixeira 1996 semiempírico + majoração por vento): GATE 3 (a7) — **APROVADO**

Feature sobre `ruleset.yaml` v9 (hash
`sha256:56f1282b23da45e7164d2e18ebafebee1c0b2f1e317ad0090787fbbe35f277cb`,
conferido contra `ruleset.lock` antes desta rodada — sem deriva desde a
aprovação do GATE 2). Módulos novos:
`calc_core/geotecnico/{dominio,seguranca,capacidade,semiempirico,sigma_adm,vento}.py`
e acréscimo em `calc_core/modelos.py`; remoção de `sigma_adm_por_spt` em
`calc_core/sapata_isolada/geotecnia.py`. GATE 2 (a6) aprovou na rodada 1/3,
nota 4,72, sem veto, commit final `831753a` — detalhe completo em
`relatorios/revisao_codigo.json`.

**Duas rodadas de CI vermelho no meio do caminho**, ambas fechadas antes
desta validação: `mypy --strict` falhando por tupla de lambdas sem
anotação em `sigma_adm.py` (D-01, corrigido em `f2b43eb`) e `pyyaml`
faltando em `requirements-dev.txt` — sem essa linha `pytest tests/`
aborta na coleta de `tests/test_capacidade_carga_vesic.py`, que lê
`kb/formulas.yaml` diretamente (corrigido em `3398aff`). Depois, um
polimento não bloqueante D-04/D-05 (`831753a`): `assert` trocado por
`if/raise AssertionError` explícito em `semiempirico_spt` (sobrevive a
`python -O`, não muda a invariante) e docstring de `fator_Nq` distinguindo
o valor matemático (1,00 exato em φ=0) do valor de ponto flutuante
devolvido (0,9999999999999998) — nenhuma das duas mudanças altera número,
guarda ou rótulo, confirmado por mim lendo o diff completo do commit.

### O que eu validei de forma independente (não relida do relato do a2/a4/a6)

1. **Fatores de capacidade em ângulos NÃO testados pelos agentes
   anteriores** (evitei 0°, 20°, 30°, já cobertos): calculei à mão, com
   script Python próprio a partir das equações clássicas de
   Reissner/Prandtl/Caquot-Kérisel (não lidas de `kb/formulas.yaml` nem do
   código), Nc/Nq/Nγ para φ = 15°, 35° e 45°, e comparei contra
   `fator_Nq`/`fator_Nc`/`fator_N_gamma` de `capacidade.py`:
   φ=15° → Nq=3,9411/Nc=10,9765/Nγ=2,6480; φ=35° →
   Nq=33,2961/Nc=46,1236/Nγ=48,0288; φ=45° → Nq=134,8738/Nc=133,8738/
   Nγ=271,7477 — batem com o código a mais de 10 casas decimais nos três
   ângulos (mesma formulação fechada, como esperado) e conferem com os
   valores publicados em tabelas de referência de Vesic (ex.: Das,
   *Principles of Foundation Engineering* — Nq(45)=134,88, Nc(45)=133,88,
   Nγ(45)=271,76). Testei também os dois extremos do domínio declarado: φ=50°
   (Nq=319,06/Nc=266,88/Nγ=762,86, aceito) e φ=50,0001°/φ negativo
   (`ForaDoDominioError`, recusado nos dois lados).
2. **Caso completo de `teorico_terzaghi_vesic` ponta a ponta**, com
   parâmetros realistas: (a) argila não drenada (φ=0, c=50 kPa,
   B=2,0×L=2,5 m, h=1,5 m, γ=18 kN/m³) → σ_r=324,08 kPa, σ_adm_ELU=108,03
   kPa (FSg=3,00) — ordem de grandeza plausível para argila média rasa;
   (b) areia drenada (c=0, φ=32°, B=L=1,8 m, h=1,2 m, γ=19 kN/m³) →
   σ_r=1168,63 kPa, σ_adm_ELU=389,54 kPa — plausível para areia
   medianamente compacta. Recalculei as parcelas de cada caso à mão
   (coesão, sobrecarga, peso, fatores de forma de De Beer) e bati com o
   `memoria` devolvido pela função, dentro de arredondamento de última
   casa.
3. **Piso `FSg/(1+k_v) >= 1,6` de `vento.py`**, construído por mim: caso
   que BINDA — FSg=2,00, lista fechada (teto 0,30), k_v=0,30 → FSg
   efetivo=1,538 < 1,6, `majoracao_admissivel` RECUSA com
   `MajoracaoDeVentoError` citando o k_v máximo correto (0,25);
   `k_v_maximo_admissivel` devolve 0,25 de forma independente, e aplicar
   k_v=0,25 passa com FSg efetivo exatamente 1,600. Caso que NÃO binda —
   FSg=3,00, k_v=0,15 → passa, FSg efetivo=2,609, sem tocar o teto.
4. **Não contaminação do motor mínimo** (`calc_core/geotecnico/
   geometria.py`, usado por `ui/app_desktop.py`): `git log` confirma que
   `geometria.py` não foi tocado desde o commit original (`07bb880`); o
   diff de `calc_core/modelos.py` desde antes desta feature é
   estritamente aditivo (9 classes novas, nenhuma alteração em
   `EntradaSapataCentrada`/`ResultadoGeometria`); `ui/app_desktop.py` não
   importa nenhum dos módulos novos (`sigma_adm` que aparece ali é o nome
   do campo de entrada do engenheiro, não relacionado ao módulo novo).
   Suíte completa: 385 testes passam num worktree com as mudanças (mais 1
   falha causada por ausência de `tkinter` no Python 3.11 deste sandbox —
   ambiental, pré-existente, alheia a este commit: confirmado que até
   `ui/app_desktop.py`, do motor MÍNIMO original, já falharia ao importar
   `tkinter` neste ambiente, então não é regressão desta feature). Rodada
   isolada de `tests/test_geometria.py` (motor mínimo) e dos 5 arquivos de
   teste da feature nova: **112 passed**, sem nenhuma mudança de
   comportamento no motor mínimo.
5. **REQ-SIGMA-09 — varredura própria, não só nos arquivos que o a6 já
   olhou**: `grep -rn "sigma_adm" --include="*.py"` no repo inteiro,
   filtrando as ocorrências que já têm o sufixo `_ELU`. Todas as
   ocorrências restantes são (a) o campo de ENTRADA pré-existente do
   motor mínimo e do motor amplo (`EntradaSapataCentrada.sigma_adm`,
   `Solo.sigma_adm` em `calc_core/sapata_isolada/geotecnia.py`) — dado
   informado pelo engenheiro, não devolvido por este código novo; (b)
   docstrings/comentários dos módulos novos que EXPLICAM por que a saída
   NÃO se chama `sigma_adm` sem sufixo (avisos corretos, não violações);
   (c) nomes de variável em teste referentes ao campo de entrada
   pré-existente. Os três dataclasses que este código novo devolve
   (`ResultadoSigmaAdmELU`, `ResultadoDispersaoSemiempirica`,
   `ResultadoMajoracaoVento`) têm 100% dos campos numéricos com sufixo
   `_ELU` (`sigma_adm_ELU_kPa`, `sigma_adm_ELU_majorado_kPa`,
   `sigma_adm_ELU_base_kPa`), confirmado por leitura de
   `calc_core/modelos.py`. Nenhum código em `ui/` ou em
   `calc_core/sapata_isolada/` consome ainda `teorico_terzaghi_vesic`,
   `semiempirico_spt` ou `majoracao_admissivel` (só comentários apontando
   para onde a próxima interface vai plugar) — logo não há hoje nenhum
   ponto de consumo que possa descolar o rótulo do número.
6. **Achados residuais do a6 (D-02, D-03, D-06) — decisão própria, não
   herdada**: nenhum bloqueia o GATE 3.
   - **D-02** (`exigir_ausencia_de_ponderacao(gamma_m_aplicado=...)` sem
     chamador de produção): confirmei lendo `seguranca.py` que o único
     chamador real de fato, `comparar_com_tensao_atuante`, passa apenas
     `gamma_f_aplicado_na_acao`. Mas confirmei também que não existe, em
     nenhum lugar do repositório, uma rota que produza um resultado em
     "valores de cálculo" (gamma_m) para alimentar essa guarda — toda
     função pública desta feature chama `exigir_metodo_admissivel`
     primeiro, e o método `'calculo'` é recusado nos 5 pontos de entrada
     (reconfirmei 2 deles eu mesmo). Guarda morta em produção, mas sem
     vetor de insegurança alcançável hoje — BAIXA, registro para quando a
     rota de cálculo existir, não bloqueante.
   - **D-03** (~30 mudanças cosméticas de tipagem, `Optional[X]` →
     `X | None`, no motor amplo NÃO auditado, misturadas ao commit
     normativo): confirmei que são preservadoras de comportamento — toda
     a suíte de `sapata_isolada/` (rigidez, flexão, planta travada,
     propagação de tensões, pressão de serviço, sanidade, correções)
     passa sem alteração de resultado. É débito de HIGIENE DE PROCESSO
     (cosmética deveria ir em commit separado do normativo, especialmente
     no motor que o CLAUDE.md marca como não auditado), não defeito de
     comportamento — não bloqueante, registrado para a próxima rodada.
   - **D-06** (`tools/checar_rastreabilidade.py` pressuposto por
     `a2-verificador.md` mas ausente do repo): confirmei a ausência
     (`ls tools/` só tem `checar_dimensoes.py` e `decodificar_nbr.py`). É
     débito de INFRAESTRUTURA DE TOOLING — a rastreabilidade em si foi
     verificada (pelo a6, com script AST ad hoc, 100%; por mim, por
     amostragem manual de vários docstrings citando `[rule:]`/`[pratica:]`
     com página e item). A ausência da ferramenta não é, em si, um
     defeito nesta feature — é dívida geral do pipeline que deveria ter
     sido criada há mais rodadas. Não bloqueante para este GATE 3, mas
     deveria entrar no backlog de infraestrutura antes que outra feature
     precise da mesma checagem manual.

### Veredito — GATE 3

**APROVADO.** Os seis pontos pedidos foram verificados por experimento
independente, não por releitura do código ou do relato dos agentes
anteriores: os fatores de capacidade em três ângulos novos batem com a
formulação clássica e com tabelas publicadas independentes; os dois casos
completos (argila e areia) produzem números de ordem de grandeza correta
e parcelas que conferem à mão; o piso de vento binda e recusa exatamente
onde deveria, e não binda onde não deveria; o motor mínimo
(`geometria.py`, `ui/app_desktop.py`) está comprovadamente intocado, sem
import cruzado e sem regressão na sua suíte; REQ-SIGMA-09 se sustenta numa
varredura própria do repositório inteiro, não só dos arquivos que os
agentes anteriores tocaram; e os três achados residuais (D-02, D-03, D-06)
são, na minha avaliação independente, registro para rodadas futuras, não
bloqueio deste portão — nenhum deles altera um número, abre um vetor de
insegurança alcançável em produção, ou deixa uma afirmação normativa sem
verificação executável. Detalhe da reprodução numérica completa (scripts,
valores, comparação com tabelas publicadas) em
`relatorios/conformidade.md`, mesmo adendo.

---

## Adendo — GATE 3, `ui/completo/dialogo_sigma_adm.py` (UI de σ_adm a
partir de SPT), commit `e597087`

O adendo acima aprovou o MOTOR (`calc_core/geotecnico/sigma_adm.py` +
`vento.py`). Este adendo é sobre a TELA que o expõe — um GATE 3 separado,
por cima de um GATE 2 que teve uma saga fora do padrão e merece registro
completo antes do veredito.

### A saga, para quem só vai ler este parágrafo

Ciclo antigo (3 rodadas, todas REPROVADAS): o diálogo guardava um estado
intermediário "selecionado, pronto para usar" (`_valor_final_kPa` e
companhia) entre o clique que MOSTRAVA um resultado e o clique que o
USAVA. Cada rodada de correção fechava o gatilho relatado (primeiro só o
painel de vento, depois só alguns campos) sem eliminar a CLASSE do
defeito — sempre sobrava um widget novo, ou esquecido, fora da lista de
invalidação. Decisão humana registrada no pedido de trabalho, e não do
a6: em vez de uma quarta rodada de patch, REDESENHAR o modelo de estado.
O redesenho (commit `78dbb31`) eliminou o cache por completo — cada card
de resultado carrega seu próprio `ResultadoSigmaAdmELU`/
`ResultadoMajoracaoVento` por FECHAMENTO do botão "Usar...", fisicamente
destruído junto com o card sempre que a entrada muda. Ciclo novo, 3
rodadas até fechar: (1) rótulo ELU faltando na tela principal + D-03
(recusas múltiplas do semiempírico não chegando à tela) — corrigidos;
(2) card sobrevivendo a mudança de ENTRADA sem recalcular, D-01 (`fb17c55`)
— corrigido para os cards base; (3) o MESMO problema nos widgets de VENTO,
D-04 (`e597087`) — corrigido, extensão do mesmo mecanismo. GATE 2 rodada 3
(final) aprovou com nota 4,7, sem veto, registrando D-05 (cobertura de
teste, não bloqueante) para eu avaliar aqui.

### O que verifiquei por conta própria, sem me apoiar nos testes existentes

**1. Reprodução end-to-end, script próprio, dois cenários reais**
(`/tmp/.../scratchpad/repro_e2e.py`, não relido de `tests/
test_ui_sigma_adm.py`): instanciei `DialogoSigmaAdm` sob Xvfb, preenchi os
campos como um engenheiro preencheria, e invoquei os `command=` dos
botões reais da árvore de widgets (não chamei os métodos internos
diretamente) — a mesma via que um clique do usuário aciona.
- **(a) Caminho teórico, argila** (c=25 kPa, φ=18°, B=2,5×L=3,0 m,
  h=1,8 m, γ=17/17 kN/m³, retangular, geral, não-drenado, homogêneo
  declarado): `resultado_kPa` do diálogo bateu EXATAMENTE (diferença
  `< 1e-9`) com `teorico_terzaghi_vesic` chamado diretamente com os
  mesmos parâmetros; `resultado_info["rotulo_ELU"]` bateu com
  `resultado.rotulo_ELU` do núcleo.
- **(a2) Mesmo caso, majorado por vento** (ação principal marcada, tipo
  de obra da lista dos 30 %, k_v=0,20): cliquei "Calcular majoração..."
  e depois "Usar valor majorado →" nos botões reais do card; o valor
  bateu exatamente com `majoracao_admissivel` chamada direta, e a regra
  `NBR6122-6.3.2-majoracao-vento-valores-admissiveis` apareceu em
  `resultado_info["regras"]`, confirmando a união de regras do D-02 (não
  só as do método base).
- **(b) Caminho semiempírico, argila** (N_SPT=10, B=2,0 m, quadrada,
  h=1,5 m, γ=17 kN/m³, declaração regional marcada): o número de cards
  desenhados bateu com `len(semiempirico_spt(...).resultados)`; o botão
  "Usar este valor →" do primeiro card entregou exatamente o
  `sigma_adm_ELU_kPa` e o `nome_do_metodo` do primeiro resultado do
  núcleo chamado direto.

Todos os campos foram lidos pela árvore de widgets de verdade (busca
recursiva por `ttk.Button` com o texto do rótulo, não por atributo
interno), então esta reprodução também confirma, de passagem, que os
botões certos existem na tela com o texto certo.

**2. D-05 — investiguei os dois mutantes eu mesmo, independentemente do
relato do a6.**

*Mutante MP* (`break` logo após invalidar a primeira `saida` viva em
`_invalidar_todas_saidas_vento`): apliquei a mutação real no arquivo,
rodei a suíte completa sob Xvfb — **560 passed, mutante sobrevive**,
confirmando o relato do a6. Fui além do que o a6 relatou: escrevi um
script (`repro_d05.py`) que desenha DOIS cards majorados simultaneamente
(argila e areia, `semiempirico_spt`), muda `k_v` uma vez sem recalcular,
e verifica os DOIS botões "Usar valor majorado →". Com o mutante
aplicado, o botão do PRIMEIRO card é destruído corretamente mas o do
SEGUNDO sobrevive — reproduzi o defeito exato que o mutante introduziria
em produção. Restaurei o arquivo original e rodei o mesmo script: os
DOIS botões são destruídos, confirmando que o mecanismo real (não
mutado) está correto — o gap é só de COBERTURA DE TESTE, não de
comportamento.

*Mutante MJ* (remoção da guarda `if not saida.winfo_exists(): continue`):
apliquei a mutação real, rodei a suíte completa — **560 passed, mutante
sobrevive**, confirmando o relato do a6. Fui além do relato outra vez:
construí um script (`repro_d05_mj2.py`) com DOIS cards em ABAS
diferentes (teórico e semiempírico) — o card da aba teórica é destruído
por D-01 (mudei `t_B` sem recalcular), deixando sua `saida` de vento
MORTA na lista `self._saidas_vento`, na frente da `saida` VIVA do card
semiempírico. Ao mudar `k_v` de novo, com o mutante aplicado: o Tkinter
imprime `_tkinter.TclError: bad window path name ...` no
`Exception in Tkinter callback` (stderr) e **engole a exceção** —
`v_kv.set(...)` retorna normalmente, sem levantar nada capturável pelo
chamador — e o `for` de `_invalidar_todas_saidas_vento` para NO MEIO,
antes de alcançar a `saida` viva do segundo card: o botão "Usar valor
majorado →" do card semiempírico, que já não corresponde ao `k_v`
digitado, **continua na tela e continua funcional**. Isto é
exatamente D-04 reaberto em silêncio, como o a6 alertou — só que
demonstrei o vetor concreto (duas abas, uma delas invalidada por D-01
primeiro) que o dispara, não apenas a mecânica genérica. Restaurei o
arquivo original e rodei o mesmo script: sem exceção alguma, o botão do
card vivo é corretamente destruído.

**Minha avaliação, independente da do a6**: concordo que D-05 é MÉDIA,
não bloqueante para este GATE 3. Três razões: (i) o código de PRODUÇÃO
está correto — verifiquei os dois cenários (dois cards majorados
simultâneos; card morto por D-01 na frente de um vivo na mesma lista) com
o arquivo original, sem mutação, e os dois passam; (ii) os únicos vetores
que reabririam o defeito são regressões FUTURAS de um mecanismo hoje
correto, não um bug presente hoje na tela que um usuário possa acionar;
(iii) o cenário MJ, se algum dia reaparecer, é seguro por default no
sentido de "nunca maior que o real por acaso favorável" tanto quanto
D-01/D-04 em geral, mas ainda assim reabriria uma ALTA (majoração
obsoleta com regra normativa citada incorretamente) SEM aviso na tela —
por isso registro como pendência de PRIORIDADE, não como item cosmético:
os dois scripts que escrevi (`repro_d05.py`, `repro_d05_mj2.py`) já
provam a propriedade que falta e podem virar
`test_invalidar_vento_atinge_todos_os_cards_nao_so_o_primeiro` e
`test_invalidar_vento_nao_para_num_frame_ja_destruido_por_outro_caminho`
em `tests/test_ui_sigma_adm.py` com custo baixo — recomendo que a próxima
rodada de polimento os adicione antes de qualquer refatoração futura de
`_invalidar_todas_saidas_vento`.

**3. REQ-UI-SIGMA-01 a 06 — releitura própria do texto no `ruleset.yaml`
cruzada com o código atual, item por item** (não apenas os que motivaram
correção):
- **01** (rótulo de ELU, nunca "tensão admissível"): `resultado.rotulo_ELU`
  é exibido em `_card_resultado` (linha 845) e a majoração inline reusa
  `majoracao.rotulo_ELU` (linha 1069) — confirmado por leitura, nenhuma
  ocorrência de "tensão admissível" como rótulo nesta tela.
- **02** (fonte não normativa + advertência de "formulários de bolso"):
  `resultado.rotulo_fonte` (= `ROTULO_FONTE_NAO_NORMATIVA` do núcleo) é
  exibido linha 848; `ADVERTENCIA_FORMULARIOS_DE_BOLSO` vem embutida em
  `resultado.avisos` desde `calc_core/geotecnico/semiempirico.py` (linha
  241/395) e é exibida junto dos demais avisos (linha 857-862) — não
  redigida na UI, só repassada, como o requisito exige.
- **03** (recusa com parâmetro/valor/intervalo/fonte, distinguindo força
  DECLARADO_EM_TEXTO de ADOTADO_DA_EXTENSAO_DE_FIGURA; card por recusa
  quando nenhum método se aplica): `_texto_recusa`/`_texto_recusa_metodo`
  formatam exatamente esses campos; `_ROTULOS_DE_FORCA` distingue os dois
  níveis; `_calcular_semiempirico` itera `erro.recusas` (não só os campos
  degradados da exceção) desenhando um card por item — confirmado por
  leitura de código, D-03 fechado permanece fechado.
- **04** (dois campos de gamma, aviso de efetivo-vs-saturado, proibição
  de classificar solo por N_SPT): `t_gamma_acima`/`t_gamma_abaixo` são
  campos distintos com `AVISO_GAMMA_EFETIVO` visível entre eles; busquei
  por qualquer rótulo de classificação de solo ("medianamente compacta"
  etc.) nesta tela — nenhum.
- **05** (todas as correlações aplicáveis lado a lado, sem escolha
  automática; dispersão exibida quando houver mais de um resultado; vento
  nunca infere a ação principal; FSg efetivo e teto exibidos; lista de
  sete tipos de obra por Combobox fechado): confirmado por leitura de
  `_calcular_semiempirico` (um card por resultado E por recusa, dispersão
  condicional) e `_calcular_vento_no_card` (`teto`/`FSg_efetivo` sempre
  exibidos juntos, `principal` lido do widget, nunca inferido); a lista de
  obras vem de `TIPOS_DE_OBRA_DOS_30_POR_CENTO` do núcleo, `Combobox`
  `state="readonly"`.
- **06** (declaração regional sem default afirmativo; aviso de escopo):
  `self.s_regional = tk.BooleanVar(value=False)` (linha 726) — sem
  default afirmativo, confirmado; e confirmei que a guarda é FUNCIONAL,
  não só de UX — `calc_core/geotecnico/semiempirico.py` chama
  `_exigir_declaracao_regional` internamente nos dois caminhos (linhas
  238/367), então mesmo se a UI algum dia deixasse passar `True` por
  engano, o núcleo recusaria de qualquer forma; `AVISO_ESCOPO_SIGMA_ADM`
  é um `ttk.Label` incondicional no topo de `_montar` (`pack(fill="x")`
  antes do `Notebook`), sempre visível, não dentro de aba alguma que
  possa ficar escondida.

Os seis estão cumpridos hoje, não só os que motivaram correção nas
rodadas anteriores.

**4. Contaminação do motor mínimo — confirmação independente.**
`git log --oneline -- calc_core/geotecnico/geometria.py ui/app_desktop.py`
ao longo de TODA a saga (do commit anterior a `e4e6bdb` até `e597087`,
cobrindo as 12 commits desta feature, motor + UI) mostra um único commit
para cada arquivo: o commit original (`07bb880`), anterior a esta
feature inteira — nenhum commit da saga tocou nenhum dos dois.
`git diff` de `calc_core/modelos.py` no mesmo intervalo não tem uma única
linha removida (`grep "^-"` vazio) — é estritamente aditivo, 9 dataclasses
novas, `EntradaSapataCentrada`/`ResultadoGeometria`/`Verificacao`
byte-idênticas. `dialogo_sigma_adm.py` importa só de
`calc_core.geotecnico.{dominio,seguranca,semiempirico,sigma_adm,vento}` e
`calc_core.modelos` — nenhum import de `geometria.py`, e `geometria.py`
não importa nada da árvore nova (só `restricoes` e `modelos`). Suíte
completa: `CI=true xvfb-run -a pytest tests/ -q` → **560 passed**,
confirmando o número citado no pedido de trabalho — rodei eu mesmo, não
reli o resultado de ninguém.

**5. BAIXA reincidentes — confirmação independente, não bloqueantes.**
Confirmei os quatro por grep direto: dois `messagebox.showerror(...)`
sem `parent=self` (linhas 672 e 790 de `dialogo_sigma_adm.py`); `self.v_kv
= tk.StringVar(value=f"{K_V_DEFAULT:g}")` usa formatação `:g` (linha
958); `tools/checar_rastreabilidade.py` ausente de `tools/` (só existem
`checar_dimensoes.py` e `decodificar_nbr.py`); F541 (`f"\n  Referências
cruzadas:"`, f-string sem placeholder) em
`calc_core/sapata_isolada/relatorio.py:257` — arquivo do motor AMPLO não
tocado por esta feature, pré-existente. Nenhum dos quatro altera um
número, um rótulo normativo ou uma guarda de domínio — concordo que são
não bloqueantes, pendência de uma rodada de polimento futura junto com o
D-05.

### Veredito — GATE 3 (UI)

**APROVADO.** Os dois cenários end-to-end (teórico com e sem vento,
semiempírico) reproduzidos por script próprio, clicando nos botões reais
da árvore de widgets, batem exatamente com o núcleo chamado direto. Os
seis REQ-UI-SIGMA foram relidos e cruzados com o código linha a linha,
não só os que motivaram correção. D-05 foi investigado além do relato do
a6 (dois cenários adicionais próprios, incluindo o vetor concreto de
duas abas que reabre a D-04 em silêncio) e confirmado como MÉDIA não
bloqueante — o mecanismo de produção está correto, o gap é só de
regressão futura sem teste que a pegue; registrado com recomendação
específica de dois testes para a próxima rodada. Nenhuma contaminação do
motor mínimo (`geometria.py`/`app_desktop.py` intocados, import
unidirecional, `modelos.py` estritamente aditivo). Suíte completa
verde (560 passed) sob as mesmas condições do CI (Xvfb, `CI=true`). Os
quatro reincidentes BAIXA são pendência de polimento, não bloqueio.

## Adendo 2026-09-02 — camada única de dados: φ'/c'/γ na base derivados da
## camada em h_f (`ui/completo/formulario.py`/`app.py`, backlog #12): GATE 2
## (a6) — 3 rodadas, **APROVADO** na rodada final

**Escopo.** `ruleset.yaml` v10 (hash `99d1c2e13c1adc2836266265e705aff53e2c2cdfe6e481f870479cf02f9ff7e6`)
acrescentou `REQ-UI-CAMADA-01` a `-07` em `requisitos_para_a3`: quando existe
perfil em camadas, os três campos soltos "γ_solo"/"φ' na base"/"c' na base"
da seção "Solo de apoio" passam a ser derivados de
`PerfilGeotecnico.camada_em(h_f)` (núcleo já aprovado, escopo amplo —
`geotecnia.py:66-123`), sempre sobrescrevíveis à mão (NBR 6122 §7.2), com
proveniência conjunta e invalidação por trace — arquitetura deliberadamente
copiada da já aprovada `ultimo_sigma_adm_calculado`/`_ao_editar_sigma_adm`/
`_preenchendo_sigma_adm_calculado`. `calc_core/` não foi tocado em nenhuma
rodada.

**Rodada 1 (commit `4ddc26b`) — REPROVADO, nota 3,5, veto E1/E5.**
Defeito ALTA (D1): `_remover_camada`, ao esvaziar o perfil com proveniência
válida, escrevia `lbl_solo_derivado` diretamente, fora do único escritor
`_atualizar_rotulo_solo_derivado()` — criava um terceiro estado (proveniência
`None` com rótulo cheio) que qualquer edição manual subsequente de QUALQUER
um dos três campos apagava, mesmo sem tocar em γ_solo. Consequência de
segurança medida pelo a2 antes mesmo da implementação (REQ-UI-CAMADA-05): o
aviso obrigatório sobre a troca de papel de γ_solo (que abaixo do N.A. passa
a exigir o valor EFETIVO, não o saturado) desaparecia silenciosamente,
deixando γ_sat (19-21 kN/m³) num campo que passou a significar sobrecarga
efetiva — distorção do lado inseguro (+27%, tendendo a fator ~2, mesma classe
da pendência V7/V8 registrada em `kb/pendencias.md`). Defeito MÉDIA (D2):
gatilho de `_remover_camada` sem cobertura (mutante reduzindo a chamada a
`pass` sobrevivia a 592/592). Três defeitos BAIXA recomendados na mesma
passagem (desempate normativo duplicado inline em `app.py`; Ramos do Excel
dependendo do default silencioso de 1,5 m de `ler_solo`; rótulo dentro da
grade dos três campos distorcendo layout).

**Rodada 2 (commit `7b78d6c`) — REPROVADO, nota 4,0, veto E1.** D1, D2, D3 e
D5 fechados e confirmados por execução (não releitura): novo estado
`_aviso_perfil_vazio` consultado e priorizado pelo escritor único, desligado
só por nova derivação bem-sucedida ou por `preencher_solo`; `_camada_e_
abaixo_na`/`_hf_valido` extraídos como fonte única do desempate normativo.
Mas a correção de D4 (Ramo B do Excel) foi aplicada ao ramo ERRADO: a
proibição de REQ-UI-CAMADA-02(b) ("não inventar proveniência do default
silencioso de 1,5 m") vale para o Ramo A, que GRAVA proveniência — o a3
aplicou-a também ao Ramo B, que só compara texto, usando o h_f capturado
ANTES de `preencher_solo`. Resultado: com `v_hf` em branco antes de importar,
a comparação nunca rodava, mesmo que a tela terminasse mostrando "1,5" e a
camada nova divergisse fortemente — regressão do lado inseguro em relação à
própria rodada 1 (que emitia o aviso nesse caso). O a6 registrou
explicitamente sua própria parcela do erro ("meu D-04 da rodada 1 estava
errado para o Ramo B") — precedente de auditoria adversarial que se
autocorrige, não só aponta defeito em código alheio.

**Rodada 3 (commit `d8615cf`) — APROVADO, nota final 4,4 (E1 4,5 / E2 4,5 /
E3 4,0 / E4 4,5 / E5 4,0), sem veto.** Correção final: leitura de `v_hf` para
o Ramo B movida para DEPOIS de `preencher_solo` — a cota que a tela vai
efetivamente exibir ao final da importação, não a de antes; `_hf_valido`
continua como única guarda (recusa h_f≤0/não numérico). Quatro testes novos
matando os mutantes MC1-MC4 (Ramo B voltar ao valor cru sem guarda; captura
no momento errado; perda da guarda `perfil.camadas`; desempate normativo
reimplementado inline). O a6 replantou o MC2 original (a causa exata da
regressão da rodada 2) e confirmou que agora derruba a suíte inteira — não
aceitou a alegação do a3 sem reprodução própria. Revalidação por mutação de
9 pontos já fechados nas rodadas 1-2: 8 mortos, 1 sobrevivente identificado e
justificado como mutante EQUIVALENTE (neutralizar o guard
`_preenchendo_solo_derivado` não muda estado observável porque `_derivar_
solo_da_camada` escreve os três `StringVar` antes de gravar `ultima_
derivacao_de_camada` — a invalidação extra é sobrescrita no mesmo callback),
registrado para o a7 não tratar como buraco de cobertura.

**Três BAIXA abertos como backlog, não bloqueantes:** cobertura do ramo
`except ValueError` da importação Excel (só `AbaAusente` é exercitado);
comentário em `app.py:554` que promete mais do que o código garante sobre
02(b) e o Ramo A (derivar com h_f preenchido, apagar o campo depois — a
proveniência não se autoinvalida — e importar ainda rotula com a cota
antiga); comparação de divergência por float exato podendo acusar diferença
de ruído de ponto flutuante em `:.10g`. Também aberto para o a2 decidir
(fora do escopo do a6/a3): extrapolação em h_f exatamente igual à
profundidade total do perfil cai no fallback de `camada_em` sem o aviso de
extrapolação, porque REQ-UI-CAMADA-02 define o limiar com `>` estrito — o a3
seguiu a letra do requisito, o requisito é que tem a lacuna.

602/602 testes passando (592 baseline + 10 desta rodada) sob as mesmas
condições do CI (Xvfb, `CI=true`, `/usr/bin/python3.12`). `calc_core/`
intocado em toda a saga; `ler_solo()` byte-idêntico à v9.

**Próximo passo do pipeline:** a7-validador (GATE 3).

## Adendo 2026-09-02 — GATE 3, camada única de dados (REQ-UI-CAMADA-01..07,
## backlog #12), commit `d8615cf` — **APROVADO**

Validação independente do GATE 2 acima (mesma feature, portão diferente):
não reli o relato do a6, rodei o software de ponta a ponta sob Xvfb
(`DISPLAY=:99`, `/usr/bin/python3.12`) e conferi números contra o núcleo
chamado direto. Scripts próprios em
`/tmp/claude-0/.../scratchpad/valida_camada_e2e.py`,
`valida_camada_guardas.py`, `valida_camada_excel.py` — nenhum deles chama
`_derivar_solo_da_camada` isoladamente como atalho: instanciei
`PainelEntrada`/`AppSapataCompleto` sob Tk real, preenchi `StringVar` de
verdade e cliquei nos comandos reais de "+ camada"/"editar"/"- remover"
(`DialogoCamada` mockado só porque é um `Toplevel` modal bloqueante — o
mesmo padrão que `tests/test_ui_camada_derivada.py` já usa, não um atalho
meu).

### 1. Cenário end-to-end, 2 camadas (acima/abaixo do N.A.)

Perfil Aterro(1,0 m, φ=28°, c=5 kPa, γ_nat=17/γ_sat=19) + Areia(2,0 m,
φ=34°, c=0, γ_nat=18/γ_sat=20) cadastrado pelos botões reais. Com
N.A.=1,20 m e h_f=1,50 m (abaixo do N.A.): `v_gamma_solo`/`v_phi_solo`/
`v_coesao` = "20"/"34"/"0", batendo EXATAMENTE com
`PerfilGeotecnico(camadas=[...], nivel_agua=1.20).camada_em(1.50)` e
`Camada.gamma(abaixo_na=True)` chamados diretamente do núcleo, sem
intermediação de UI (diferença zero, comparação de string). Rótulo contém
"Areia", o radical "derivad" e a palavra "SATURADO" (Exigência 2 de
REQ-UI-CAMADA-05). Removido o N.A. (h_f continua 1,50 m, agora acima de
qualquer N.A.): `v_gamma_solo` muda para "18" = `gamma_nat`, também
batendo com o núcleo puro.

### 2. Cenário de segurança D1/REQ-05 (o que custou 2 rodadas do GATE 2)

Perfil de uma camada (Areia), N.A.=1,20 m, h_f=1,50 m → deriva γ_sat="20".
Removida a única camada pelo botão real "- remover": proveniência
invalidada (`ultima_derivacao_de_camada is None`) e o rótulo passa a
exibir o aviso obrigatório de transição ("γ_solo deixa de vir de uma
camada do perfil... Abaixo do nível d'água o valor pedido é o peso
específico EFETIVO... NÃO o saturado... erra gamma por um fator de ~2,
SEMPRE DO LADO INSEGURO"); o número em `v_gamma_solo` continua "20"
(o software avisa, não corrige). Editei manualmente `v_phi_solo` para
"31" **sem tocar em `v_gamma_solo`**: o texto do aviso permaneceu
BYTE-IDÊNTICO ao de antes da edição — não desapareceu. Repeti editando
`v_coesao`: mesmo resultado. Este é exatamente o defeito D1 da rodada 1
do GATE 2 (rótulo escrito fora do escritor único, apagado por qualquer
edição manual subsequente) — confirmei com os próprios olhos que a
correção da rodada 3 se sustenta.

### 3. Cenário Ramo B da importação Excel (regressão da rodada 2)

`AppSapataCompleto` real. `v_hf` deixado em BRANCO, os três campos
digitados à mão (γ=22, φ'=40, c'=15 — proveniência inválida). Importei
planilha `.xlsx` real (montada com `openpyxl`, abas "Pilar e cargas" +
"Perfil geotécnico") com uma camada "Argila mole importada" bem diferente
(γ=14, φ'=17°, c'=25 kPa). Após `_importar_excel()`: `v_hf` passa a
mostrar "1.5" (o default silencioso de `ler_solo`, agora visível na
tela); os três campos da tela permanecem 22/40/15 (Ramo B não sobrescreve
— confirmado); e a mensagem final de `messagebox.showinfo` (capturada de
verdade, não mockada com `MagicMock` cego) contém:

```
ATENÇÃO — divergência entre os valores da tela (mantidos, NBR 6122 §7.2)
e a camada do perfil novo na cota h_f atual:
  • γ_solo: tela = 22, camada "Argila mole importada" em h_f = 1.5 m = 14
  • φ': tela = 40, camada "Argila mole importada" em h_f = 1.5 m = 17
  • c': tela = 15, camada "Argila mole importada" em h_f = 1.5 m = 25
```

Exatamente o cenário que a regressão da rodada 2 silenciava (h_f em
branco fazia `_hf_valido("")` devolver `None` ANTES de `preencher_solo`
escrever o default) — confirmado que a correção DEF-01 (ler `v_hf` DEPOIS
de `preencher_solo`) se sustenta com um perfil e valores diferentes dos
usados pelos testes de `tests/test_ui_camada_derivada.py`.

### 4. Consistência com exemplo da bibliografia

Verificado `kb/exemplos.yaml` (152 linhas, um único caso —
`BASTOS-ex9-gtot-prisma-uniforme`): usa sobrecarga uniforme
`γ_solo × h`, sem perfil em camadas explícito com φ'/c'/γ na base. Não
aplicável — não há exemplo do acervo com perfil em camadas explícito
contra o qual conferir a derivação; registrado, não descartado sem
verificação.

### 5. Invariância física

**Perfil homogêneo** (uma camada, φ=32°, c=3 kPa, γ_nat=17,5/γ_sat=19,5,
5,0 m): derivei em h_f = 0,5/1,5/2,5/3,5/4,9 m — os três campos saem
IDÊNTICOS ("17.5"/"32"/"3") nos cinco pontos, sem dependência espúria de
h_f dentro da mesma camada.

**Invariância de reparticionamento**: a mesma camada dividida em duas
idênticas (2,0 m + 3,0 m, mesmos φ/c/γ) contra a original (5,0 m única) —
testado em h_f = 0,5/1,5/1,9999/2,0/2,5/4,9 m (inclusive nos dois lados
da interface artificial em 2,0 m introduzida pela divisão): os três
campos batem exatamente entre as duas versões do perfil em todos os seis
pontos.

### 6. Fronteira com o núcleo intocada

`ler_solo()` com proveniência derivada devolve `Solo(gamma_solo=18.0,
phi=34.0, coesao=0.0, hf=1.5, ...)`. Um segundo `PainelEntrada`, com os
MESMOS três valores digitados à mão (sem perfil, proveniência `None`),
produz um `Solo` idêntico exceto no atributo `perfil` (esperado — um tem
perfil cadastrado, o outro não). Fui além do pedido mínimo: montei um
TERCEIRO cenário com o MESMO perfil nos dois lados — deriveis os três
campos, rodei `Sapata(...).dimensionar()` completo (`gerar_combinacoes`,
`ler_pilar`/`ler_materiais`/`ler_casos`/`ler_opcoes` reais, camadas com
`nspt` para não estourar `_analisar_recalques`); depois redigitei
MANUALMENTE, nos mesmos campos, o EXATO texto que a derivação já tinha
escrito (isso invalida `ultima_derivacao_de_camada` — REQ-UI-CAMADA-03
confirmado de novo, "vazio mesmo que os números coincidam") e rodei
`dimensionar()` de novo. Comparei TODOS os campos do dataclass
`ResultadoSapata` (via `dataclasses.fields`) entre as duas rodadas:
**idênticos em cada campo**, prova de que a derivação não é um caminho de
cálculo paralelo — é só conveniência de preenchimento de string, o núcleo
nunca vê rótulo de proveniência.

### 7. Guardas de recusa e desempates normativos (REQ-UI-CAMADA-02/01)

Script à parte (`valida_camada_guardas.py`), porque é o ponto de segurança
C1 do cabeçalho da v10 do `ruleset.yaml`. Confirmado por execução, não por
leitura do código:
- `camada_em(-1.0)` do núcleo, chamado direto, de fato devolve a camada de
  FUNDO ("Areia") para uma cota negativa — reproduzi a premissa do achado
  do a2 antes de testar a guarda.
- Com um estado de derivação válido em h_f=0,5 m (camada "Aterro",
  φ="28"), digitar "-1" em `v_hf` NÃO altera nem `ultima_derivacao_de_camada`
  nem os três campos — permanecem em "Aterro"/0,5 m, provando que a
  guarda (d) impede exatamente o salto para a camada de fundo que o núcleo
  puro produziria.
- h_f="0": mesma recusa, estado intocado.
- Texto genuinamente não numérico ("abc", "", "1.e"): sem exceção, estado
  intocado. `"1."` é diferente — `float("1.")==1.0` é um float Python
  válido, então DERIVA normalmente (não é caso da guarda (b); só precisa
  não quebrar, e não quebra).
- N.A. com texto inválido ("x"): sem exceção, estado intocado.
- Desempate de interface: h_f=1,0 m (exatamente na fronteira
  Aterro/Areia) deriva da camada de BAIXO ("Areia"), confirmando
  `z0 <= z < z1`.
- Desempate N.A.: h_f == N.A. (1,20 m == 1,20 m) conta como ACIMA
  (`abaixo_na=False`, γ_nat="18"), por ser `>` estrito.
- Extrapolação: h_f=10,0 m contra um perfil de 3,0 m deriva (não trava)
  com a camada de fundo ("Areia", φ="34"), e o rótulo avisa em texto —
  "ATENÇÃO: h_f está ABAIXO da base do perfil cadastrado (profundidade
  total 3 m)... por extrapolação" — nunca em silêncio.

### 8. Suíte completa

Rodei eu mesmo, não confiei no número relatado pelo a3/a6:
`DISPLAY=:99 CI=true /usr/bin/python3.12 -m pytest -q` →
**602 passed** (mesma contagem do adendo de GATE 2, sem regressão nem
adição por mim). `git status --short` limpo antes e depois — nenhum
arquivo do repositório foi tocado por esta validação.

### Veredito — GATE 3

**APROVADO.** Os sete cenários pedidos (end-to-end com 2 camadas, aviso de
segurança persistente, Ramo B do Excel com h_f em branco, bibliografia
— não aplicável e verificado como tal —, invariância homogênea e de
reparticionamento, fronteira com o núcleo incluindo dimensionamento
completo idêntico, guardas de recusa/desempates) foram reproduzidos por
execução própria, sob Xvfb, clicando nos botões reais, e batem exatamente
com o núcleo chamado direto. Nenhum defeito encontrado. 602/602 testes
confirmados por mim mesmo. `calc_core/` não foi tocado por esta rodada
(confirmado junto com o GATE 2 acima) e a fronteira `ler_solo()` continua
sendo pura leitura de `StringVar`, sem preferência por proveniência —
confirmado por dimensionamento completo idêntico entre os dois casos.

## Adendo 2026-09-02 — V15: η_c ausente no bloco retangular de tensões
## (`calc_core/sapata_isolada/materiais.py`/`sapata.py`, REQ-ETA-C-01): GATE 2
## (a6) — **APROVADO** na rodada 1

**Contexto.** Defeito descoberto pelo a2 ao auditar a extração normativa do
backlog #13 (pilarete) — não é do pilarete, é dívida preexistente no motor
`sapata_isolada/` já aprovado por A6/A7. `Concreto.alpha_c` (NBR 6118 §17.2.2,
coeficiente do diagrama retangular de tensões) não aplicava `η_c` (§8.2.10.1:
`η_c=1,0` para f_ck≤40MPa, `η_c=(40/f_ck)^(1/3)` acima), superestimando a
tensão do bloco comprimido para f_ck>40MPa — armadura de flexão A MENOS e x/d
SUBESTIMADO, com a verificação de dutilidade `x/d≤ξ_limite` podendo passar
quando deveria reprovar. Lado inseguro, em código já em produção. Usuário
autorizou correção imediata, em ciclo próprio, paralelo ao backlog #13.

**Correção.** Nova propriedade `Concreto.eta_c` (fórmula acima) e
`Concreto.sigma_cd_bloco = alpha_c·eta_c·fcd`, único ponto de aplicação da
tensão do bloco — `sapata.py::_armadura_flexao_simples` passou a consumir
`sigma_cd_bloco` em vez de `alpha_c*fcd` cru. Implementa só o primeiro ramo de
§17.2.2-e (largura não decrescente da linha neutra para a borda comprimida,
que é a geometria modelada); o ramo `0,9·α_c·η_c·f_cd` fica documentado como
fora de escopo, não implementado por analogia. `bielas.py` (α_v2, coeficiente
genuinamente diferente) foi verificado e confirmado como corretamente
intocado.

**Achado do a5 sobre o próprio relato do a2.** No cenário C90/M_d=2500 citado
pelo a2 como exemplo de inversão de veredito, o a6 confirmou por reprodução
independente que o veredito NÃO inverte (0,486 e 0,700 reprovam ambos contra
ξ_lim=0,35) — o efeito é real, mas o cenário não o demonstra. O a5 isolou o
cenário que demonstra a inversão de fato (C90, M_d=1500 kN·m/m: x/d 0,267
PASSAVA → 0,363 REPROVA), e o a6 confirmou essa correção por conta própria
antes de aceitá-la — nenhum dos dois números foi aceito de segunda mão.

**Verificação independente do a6** (não releitura do relato do a5): 5
mutantes plantados (remover η_c da fórmula; trocar limiar 40→50; trocar
limiar 40→45, o mais fino da faixa 40-50 avisada pelo próprio a2; expoente
1/3→1/2; reverter o consumidor para `alpha_c*fcd` com a propriedade intacta)
— todos mortos pela suíte. Limiar de 40MPa (não 50) confirmado por execução:
em C45/C50, η_c<1 enquanto α_c ainda vale 0,85. Retrocompatibilidade exata
para f_ck≤40MPa confirmada bit a bit (`eta_c` devolve o float `1.0` literal).
`ruff` sem regressão (74→74), `bandit` limpo, 655 testes passando (rodado
duas vezes pelo a6, sob Xvfb/`python3.12`).

**Nota final: 4,6** (E1 4,8 · E2 4,8 · E3 4,0 · E4 4,5 · E5 4,3). Sem veto.

**Defeitos abertos, nenhum bloqueante:**
- MÉDIA/E3 (`sapata.py:719`): a correção do η_c amplia o ramo `disc<0`
  (seção que não resiste a M_d) — o M_d que dispara essa condição cai de
  4426 para 3378 kN·m/m em C90; o chamador mascara `inf` para `0,0` e a
  mensagem final fica autocontraditória ("x/d = 0.000 acima do limite").
  Sem cobertura de teste. Recomendação: sinalizador próprio de "seção
  insuficiente à compressão" com M_lim explícito na mensagem.
- BAIXA/E4 (`relatorio.py:70`): o memorial só imprime `f_cd`, nunca η_c nem
  a tensão final do bloco — o engenheiro que assina a ART não vê se a
  correção foi aplicada num memorial C90.
- BAIXA/E5 (`materiais.py:110`): `mypy --strict` novo `no-any-return`
  (baseline 455→456) — falta `float(...)` no retorno.
- BAIXA/E4, roteados ao a2 (não ao a5, que agiu certo em não tocar): não
  existe regra aprovada em `ruleset.yaml` v11 para §17.2.2 nem §14.6.4.3 —
  `alpha_c`/`lambda_x`/`csi_limite` continuam sem `[rule:]`, e a correção
  do η_c aumenta a sensibilidade do veredito a `csi_limite`, que é
  justamente o valor não auditado.

**Próximo passo:** a7-validador (GATE 3), sobre a superfície de flexão do
motor amplo — não o motor inteiro.

## Adendo 2026-09-03 — GATE 3, V15 (η_c ausente no bloco retangular de
## tensões, REQ-ETA-C-01), commit `2ac1033` — **APROVADO**

Portão sobre `calc_core/sapata_isolada/materiais.py::Concreto.eta_c` /
`sigma_cd_bloco` e `sapata.py::_armadura_flexao_simples`. GATE 2 (a6)
fechou na rodada 1, nota 4,6, sem veto (adendo anterior, mesmo arquivo).
Validação **independente** — reprodução própria, não releitura do relato
do a5/a6, com script em Python rodado por este agente
(`/usr/bin/python3.12`, fora da suíte versionada).

### 1. Reimplementação independente de 17.2.2-e/8.2.10.1 (3 classes)

Reconstruí a fórmula do zero (α_c, η_c, λ, σ_cd = α_c·η_c·f_cd, equação
quadrática de equilíbrio do bloco retangular) sem importar `Concreto`/
`Sapata`, e comparei contra `_armadura_flexao_simples`:

| classe | η_c | As independente | As código | x/d independente | x/d código |
|---|---|---|---|---|---|
| C30 (≤40 MPa) | 1,000000 | 21,6925 cm²/m | 21,6925 cm²/m | 0,143836 | 0,143836 |
| C45 (faixa crítica 40-50) | 0,961500 | 44,5365 cm²/m | 44,5365 cm²/m | 0,204754 | 0,204754 |
| C90 (>50 MPa) | 0,763143 | 68,0366 cm²/m | 68,0366 cm²/m | 0,281498 | 0,281498 |

Igualdade bit a bit (`rel_tol=1e-9`) nas três classes, inclusive na faixa
40-50 MPa onde α_c e λ ainda não reduziram mas η_c já reduziu — a faixa
que um código "≤C50/>C50" erraria em silêncio (achado C2 do a2, v11).

### 2. Cenário de inversão de veredito, `dimensionar()` de ponta a ponta

Não me limitei a rechamar `_armadura_flexao_simples` isolada (o que o a5/
a6 já fizeram). Montei uma sapata C90 com geometria imposta
(`GeometriaImposta`, `modelo_armadura_rigida="flexao"`, pilar 0,40×0,40 m,
base 3,00×3,00 m, `N_k` calculado para que o momento por metro na direção
X saísse em 1500 kN·m/m) e rodei `Sapata.dimensionar()` completo:

- `Md` calculado pelo pipeline (não escolhido por mim): 4500,00 kN·m
  totais / 3,00 m de largura = **1500,00 kN·m/m**, exatamente o alvo.
- `d` efetivamente usado pelo pipeline: 0,44025 m (o valor de 0,45 m que
  eu tinha como alvo se desvia ligeiramente porque `dimensionar()`
  recalcula `d` com a bitola escolhida na 1ª passada — efeito real do
  pipeline, não um erro meu).
- `x/d` devolvido pelo `ResultadoSapata` = **0,3827**, `dominio_ok =
  False` — bate byte a byte (`rel_tol=1e-6`) com uma segunda
  reimplementação independente minha usando esse `Md`/`d` exatos.
- Recalculando à mão a fórmula **sem** η_c (o bug antigo) para o mesmo
  `Md`/`d`: `x/d = 0,2804 ≤ 0,35` → "PASSA". Com η_c (pipeline atual):
  `x/d = 0,3827 > 0,35` → REPROVA. **Inversão de veredito confirmada
  ponta a ponta**, não só na função isolada.
- Também reproduzi o par exato citado pelo a5/a6 (C90, `d=0,45` m,
  `bw=1,0` m, `Md=1500` kN·m/m) chamando `_armadura_flexao_simples`
  isolada: `x/d = 0,3634 ≈ 0,363`, confirmando o número relatado.

Durante esta reprodução eu mesmo cometi um bug de script (variável de
laço `bw` reaproveitada como nome global, mascarando o parâmetro `bw_m`
da minha função de referência) que produzia um discriminante negativo
espúrio. Registro isso aqui porque é exatamente o tipo de erro que este
processo existe para pegar — e pegou, no meu próprio código de teste, não
no software: identificado, corrigido, e a reprodução refeita antes de
aceitar o resultado.

### 3. Retrocompatibilidade contra exemplo de bibliografia (Bastos ex.1)

Rodei `kb/exemplos.yaml > BASTOS-ex1-ancoragem-arranque-governa-altura-da-
sapata` (pilar 80×20 cm, `N_k=1250` kN, `σ_adm=0,26` MPa, **C25** ≤40 MPa,
CA-50, cobrimento 4,0 cm) através de `Sapata.dimensionar()` completo,
sem geometria imposta (dimensionamento automático, como no exercício).

Achado de método, não de defeito: a sapata sai classificada como RÍGIDA
(`classificacao.rigida_nbr = True`), e nesse regime `dimensionar()`
combina flexão com o modelo de bielas de Blévot (`22.6.3`) — o campo
`As_calc`/`As_adot` reflete esse envelope, não a flexão pura. A correção
do η_c só toca a via de flexão (`bielas.py` usa α_v2, confirmado
intocado pelo a6). Comparei então contra o campo `As_flexao` (saída crua
de `_armadura_flexao_simples`, antes do envelope):

| direção | Md (kN·m) | As_flexao pipeline | As_flexao referência (η_c=1) | x/d pipeline | x/d referência |
|---|---|---|---|---|---|
| X | 282,518 | 10,9001 cm² | 10,9001 cm² | 0,031533 | 0,031533 |
| Y | 365,206 | 14,3962 cm² | 14,3962 cm² | 0,032899 | 0,032899 |

`Concreto(25.0).eta_c == 1.0` exatamente. Igualdade bit a bit
(`rel_tol=1e-9`) — o exemplo bibliográfico usado em rodadas anteriores do
a1/a2 não muda em nada com a correção, confirmando retrocompatibilidade
com um caso real, não só com a fórmula genérica.

### 4. Continuidade numérica em torno de f_ck = 40 MPa

Para uma seção fixa (Md=500 kN·m, bw=1,0 m, d=0,40 m), variando f_ck em
passos decrescentes ao redor do limiar (39,5→40,0 ; 40,0→40,5 ; 39,9→40,1
; 39,99→40,01): maior salto relativo em As foi 0,10 % e em x/d foi
0,0024 (passo de 0,5 MPa) — caindo proporcionalmente com o passo, sem
descontinuidade. `η_c` é contínua no limiar por construção
((40/40)^(1/3) = 1,0 = valor do outro ramo no mesmo ponto); confirmado
aqui que essa continuidade se propaga a As e x/d, não só à propriedade
isolada.

### 5. Suíte completa

`xvfb-run -a /usr/bin/python3.12 -m pytest -q` → **655 passed**, rodado
por mim nesta validação (não reaproveitando o número relatado pelo a5/
a6). `git status --short` limpo antes e depois — nenhuma alteração de
repositório por esta validação.

### 6. Defeito MÉDIA/E3 aberto pelo a6 (`sapata.py:719`, ramo `disc<0`)

Confirmado como problema de MENSAGEM/COBERTURA, não de CORRETUDE.
Reproduzi o ramo `disc<0` de propósito (seção C90, `h=0,30` m, momento
muito acima da capacidade de compressão da seção) via `dimensionar()`
completo:

- `ar.x_d` reportado = `0,000` (o `inf` interno é mascarado para `0,0` na
  saída), e a mensagem final diz *"Direção X: x/d = 0,000 acima do limite
  de ductilidade"* — autocontraditória em texto, como o a6 já apontara.
- Mas `ar.dominio_ok = False`, `res.aprovado = False`, e
  `res.reprovacoes` **contém** a linha acima, junto com as reprovações de
  punção e ancoragem. `As_adot` cai para o mínimo normativo (23,04 cm²)
  — um valor real e definido, mas exibido ao lado de um veredito
  explícito de REPROVAÇÃO, não como se a seção resistisse.

Ou seja: nenhum número é apresentado como confiável quando `disc<0`
ocorre de fato — o software nunca aprova essa seção, apenas erra o texto
de uma mensagem dentro de uma lista de reprovações que já está correta em
substância. Não bloqueia o GATE 3 (é qualidade de mensagem e cobertura de
teste, não segurança numérica); mantenho a recomendação do a6 de um
sinalizador próprio ("seção insuficiente à compressão", com `M_lim`
explícito) para uma rodada futura de polimento, com teste de cobertura
dedicado.

### Veredito — GATE 3

**APROVADO.** Fórmula normativa reproduzida do zero e batendo byte a
byte em 3 classes (uma de cada lado do limiar de 40 MPa e uma na faixa
crítica 40-50); cenário de inversão de veredito confirmado ponta a ponta
via `dimensionar()`, não só na função isolada; retrocompatibilidade
exata confirmada contra um exemplo de bibliografia já usado em rodadas
anteriores (Bastos ex.1); continuidade numérica em torno de f_ck=40 MPa
confirmada em As e x/d, não só em η_c; suíte completa verde (655 passed)
rodada por mim; defeito MÉDIA/E3 aberto confirmado como não afetando
corretude — o software nunca aprova uma seção que não resiste, mesmo
quando a mensagem que descreve a reprovação está errada. Detalhe
completo (incluindo o script de reprodução) também referenciado em
`relatorios/conformidade.md`, mesmo adendo.

## Adendo 2026-09-05 — FrozenInstanceError em ForaDoDominioError/
## NenhumMetodoAplicavelError (`calc_core/geotecnico/dominio.py`): GATE 2
## (a6) — **APROVADO**, nota 4,7

**Contexto.** Defeito latente descoberto pelo a6 ao auditar `calc_core/
estrutural/pilarete/` (backlog #13), fora do escopo dessa feature —
código de produção já aprovado por A6/A7. `ForaDoDominioError`/
`NenhumMetodoAplicavelError` são `@dataclass(frozen=True)` herdando de
`ValueError`. Quando código Python (não o C do interpretador) escreve
`__traceback__`/`__notes__` numa exceção em trânsito — o que acontece de
verdade em `contextlib.contextmanager.__exit__` (`contextlib.py:191`,
`exc.__traceback__ = traceback`) e em `Exception.add_note` — o
`__setattr__` gerado pelo dataclass frozen recusa, produzindo
`FrozenInstanceError` em vez da recusa legível (parâmetro/valor/
intervalo/fonte) que REQ-UI-SIGMA-03 e a doutrina geral do projeto
exigem. Propagação comum (`raise`/`except` simples) nunca dispara —
CPython escreve direto na struct C — por isso escapou de A6/A7
anteriores. Confirmado como defeito PREVENTIVO, não vivo: nenhum caminho
de produção usa `contextmanager`/`add_note` sobre essas exceções hoje
(`ui/completo/dialogo_sigma_adm.py` captura com `except` simples).

**Correção (a4).** `__setattr__` customizado instalado nas DUAS classes
(o dataclass gera um `__setattr__` próprio por classe, mesmo em
subclasses de outra frozen — instalar só na base deixaria
`NenhumMetodoAplicavelError`, a exceção que `semiempirico_spt` realmente
levanta, com o defeito intacto), liberando uma lista fechada de
atributos da máquina de exceções (`__traceback__`, `__context__`,
`__cause__`, `__suppress_context__`, `__notes__`, `args`) e mantendo os
campos de domínio genuinamente imutáveis. Varredura por AST + runtime
confirma: só três classes no repositório tinham essa estrutura (as duas
aqui + `RecusaForaDeDominio` em `calc_core/estrutural/dominio.py`, já
corrigida pelo a5 na mesma sessão, backlog #13).

**Verificação independente do a6** (não releitura do relato do a4):
reproduziu o defeito revertendo a correção em cópia isolada (4 de 5
testes falham, `FrozenInstanceError` exatamente como esperado);
confirmou por dois métodos independentes (AST estática + varredura em
runtime) que são as mesmas três classes; confirmou que os campos de
domínio (incluindo `recusas` na subclasse) continuam recusando escrita;
4 mutantes plantados e mortos (remover `__notes__`/`__traceback__`
individualmente, ampliar a lista para incluir um campo de domínio,
instalar só na base). `mypy --strict`/`ruff` limpos, `bandit` limpo,
100% de cobertura em `dominio.py`. 823/823 testes passando.

**Nota final: 4,7** (E1 4,8 · E2 5,0 · E3 4,3 · E4 4,6 · E5 4,3). Sem
veto.

**Cinco defeitos BAIXA, nenhum bloqueante** (podem entrar junto com
trabalho futuro na superfície): teste de imutabilidade só cobre
`ForaDoDominioError` com 7 nomes escritos à mão, não `recusas` nem a
subclasse via `dataclasses.fields()`; `__delattr__` não foi corrigido
(mesma classe de defeito, metade não coberta do protocolo); docstring
descreve a lista como "mínima" quando só 2 dos 6 atributos liberados têm
chamador conhecido; o `__setattr__` substituto abandona a guarda
`type(self) is cls` do dataclass original, apertando o congelamento em
vez de só preservá-lo (sem consequência hoje, nenhuma subclasse não-
dataclass existe); citação normativa completa (§7.3.3) em constantes
sem conteúdo normativo (lista de dunders, tupla de classes).

**Próximo passo:** a7-validador (GATE 3) sobre a superfície `geotecnico/`
tocada.
