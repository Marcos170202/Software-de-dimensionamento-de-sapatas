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
