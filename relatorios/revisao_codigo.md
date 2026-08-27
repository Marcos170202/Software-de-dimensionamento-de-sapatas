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
