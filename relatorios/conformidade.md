# Validação por exemplos — escopo mínimo (sapata isolada, carga centrada)

**Limitação de processo, igual à da revisão de código:** `a7-validador.md`
pede validação contra "exercícios resolvidos da bibliografia" — este
ambiente não tem acesso a nenhum livro-texto de fundações (Alonso ou outro).
O caso de conformidade abaixo foi **calculado à mão pelo próprio agente, a
partir da fórmula da norma**, não extraído de uma fonte externa independente.
Isso reduz seu valor como validação: um erro sistemático na interpretação da
norma se propagaria igualmente para o cálculo manual e para o código, sem
ser pego por este teste. Os testes de equilíbrio e invariância abaixo são
verificações físicas diretas e não sofrem desse problema — são a parte mais
confiável desta validação.

**Recomendação:** antes de uso profissional, rodar o software contra pelo
menos um exemplo de um livro-texto reconhecido (Alonso, Velloso & Lopes,
Bowles) e registrar o resultado em `kb/exemplos.yaml` + suíte
`pytest.mark.parametrize`, como pede `a7-validador.md`.

## Caso de conformidade (calculado à mão)

```yaml
id: CALC-MANUAL-01
fonte: "calculado à mão pelo agente a partir da NBR 6122:2022 §7.6.1 — NÃO é exemplo de livro-texto"
hipoteses:
  - "tensão uniforme (carga efetivamente centrada, sem momento)"
  - "sem peso próprio (considerar_peso_proprio=False)"
  - "método de folga igual nas 4 bordas do pilar (decisão de engenharia, não normativa)"
entrada: {N_k: 1200, sigma_adm: 250, pilar_a: 0.30, pilar_b: 0.50}
esperado:
  area_necessaria: {valor: 4.80, tol_abs: 0.01, unidade: m2}
  B: {valor: 2.10, tol_abs: 0.01, unidade: m}
  L: {valor: 2.30, tol_abs: 0.01, unidade: m}
  tensao_atuante: {valor: 248.4, tol_rel: 0.01, unidade: kPa}
criticidade: MEDIA  # não ALTA — fonte é auto-calculada, não bibliografia externa
```

Reproduzido em `tests/test_geometria.py::test_caso_calculado_a_mao_pilar_30x50`
— **PASSOU**.

## Testes de equilíbrio

`tests/test_geometria.py::test_equilibrio_sigma_vezes_area_igual_N_total`
(hypothesis, faixas: N_k 50–5000 kN, σ_adm 50–600 kPa, pilar 0,20–1,20 m):

- `sigma_atuante * area_final == N_total` (tolerância relativa 1e-9) —
  **PASSOU** em todos os casos gerados.
- `sigma_atuante <= sigma_adm` — **PASSOU** em todos os casos gerados
  (a imposição do mínimo de 60 cm nunca aumenta sigma_atuante além do
  admissível, porque só entra em jogo quando a área calculada já é folgada).

## Testes de invariância

- Dobrar `N_k` com `sigma_adm` fixo dobra exatamente `area_necessaria` —
  **PASSOU** (`test_dobrar_N_k_dobra_area_necessaria`, hypothesis).
- Girar o pilar 90° (trocar `pilar_a` ↔ `pilar_b`) troca `B` ↔ `L` e nada
  mais — **PASSOU** (`test_girar_pilar_90_graus_troca_B_por_L`, hypothesis).

## Testes de contorno

- Carga muito leve em terreno muito bom (área calculada < 0,36 m²): o
  software impõe B=L=0,60 m em vez de devolver uma sapata abaixo do mínimo
  normativo — **PASSOU** (`test_carga_leve_aciona_dimensao_minima`).
- Toda combinação de entrada inválida (N_k, σ_adm, dimensões do pilar,
  percentual de peso próprio, dimensão mínima, módulo de arredondamento ≤ 0
  ou fora do domínio) rejeita com `ValueError` explícito, sem devolver
  número algum — **PASSOU** (8 casos parametrizados).

## Portão (GATE 3)

100% dos casos de criticidade MÉDIA (não há caso ALTA neste escopo, por
depender de bibliografia externa indisponível) aprovados; todos os testes de
equilíbrio, invariância e contorno verdes — **21/21 testes passando**,
cobertura de linhas 100% em `calc_core/`.

Aprovado **para o escopo mínimo declarado em `ruleset.yaml`**, com a ressalva
de processo registrada no topo deste documento.

## Adendo — 2026-08-26: calc_core/sapata_isolada/ (escopo amplo)

- Suíte de sanidade do próprio autor do pacote (7 casos, ver
  `tests/test_sapata_isolada_sanidade.py`) — **passa** após as 6 correções.
- Regressão dos 6 defeitos corrigidos (`tests/test_sapata_isolada_correcoes.py`)
  — **passa**, incluindo os 2 casos do lado inseguro (η1 de CA-60; teto de ρ
  na punção).
- Caso de ponta a ponta com perfil de solo em 2 camadas, vento e momento
  biaxial: roda sem exceção, gera memorial completo, e **reprova
  corretamente** uma sapata por recalque excessivo (104,2 mm contra limite de
  25 mm) — sinal de que as verificações estão de fato conectadas.
- **45/45 testes do repositório passam** após a integração.

**Limitação explícita:** não há exemplo de livro-texto (Alonso ou outro)
disponível neste ambiente para os casos excêntricos/punção/bielas — a
"conformidade" aqui é contra a própria norma (leitura visual) e contra
verificações físicas (equilíbrio, invariância testados no escopo mínimo),
não contra uma segunda fonte independente para o escopo amplo. Ver
`ruleset.yaml`, seção `escopo_amplo_em_conferencia`, para o que ainda não
foi auditado item a item.

## Adendo — 2026-08-27: classificação rígida/flexível e proibição de redutor
uni/bidirecional (GATE 3 pós-GATE 2, nota 4,50, terceira rodada)

Escopo: `NBR6118-22.6.1-rigidez` (`rigidez.py::classificar`,
`sapata.py::_alturas`) e `NBR6118-22.6.2.2a-flexao-duas-direcoes`
(`sapata.py::_ciclo_flexao`, `momentos.py::momento_unitario`/`campo_momentos`),
mais as correções de citação normativa (12+ arquivos) e a extração de
`OpcoesProjeto.balanco_minimo` (commits `e7f3d26~1..96e7036`).

### Suíte completa
`pytest tests/ --cov=calc_core --cov-report=term-missing`: **101/101
passando**, rodado de forma independente (não aceito do relato dos agentes
anteriores). Eram 79 antes desta rodada e 57 antes da rodada de momentos —
crescimento confirmado pelo histórico dos próprios arquivos de teste
(`test_rigidez_nbr_22_6_1.py`, `test_flexao_duas_direcoes_nbr_22_6_2.py`,
`test_planta_travada.py`, todos novos nesta rodada). Cobertura de linhas:
100% em `modelos.py` e `geotecnico/`; 93% em `rigidez.py`; 85% em `sapata.py`.

### Casos de referência para `classificar()` — cálculo independente (não usa
a fórmula do código como oráculo)
`h_necessario = max((a-ap)/3, (b-bp)/3)` recalculado à mão para 4 geometrias:

| caso | a×b (m) | ap×bp (m) | h (m) | h_nec (m) | esperado | obtido |
|---|---|---|---|---|---|---|
| rígida nas 2 direções | 2,00×2,00 | 0,40×0,40 | 0,70 | 0,5333 | RÍGIDA | RÍGIDA |
| flexível nas 2 direções | 3,00×3,00 | 0,40×0,40 | 0,30 | 0,8667 | FLEXÍVEL | FLEXÍVEL |
| rígida em X / flexível em Y | 2,00×3,60 | 0,40×0,40 | 0,55 | 1,0667 | FLEXÍVEL | FLEXÍVEL |
| espelhado (rígida em Y / flexível em X) | 3,60×2,00 | 0,40×0,40 | 0,55 | 1,0667 | FLEXÍVEL | FLEXÍVEL |

Os dois casos mistos confirmam que basta falhar numa direção para a
classificação geral virar FLEXÍVEL — exatamente o comportamento que a
`rodada 1` do a6 havia pego como mutante (`h_nec = (a-ap)/3`, ignorando Y).
4/4 casos batem com `h_necessario` calculado à mão (rel. tol. 1e-9).

### Invariância
- `classificar()` simétrica sob troca `(a,ap) <-> (b,bp)`: 500 geometrias
  aleatórias (seed fixa), 0 contra-exemplos.
- `As_adot` estritamente positivo nas duas direções, 5 geometrias com carga
  de compressão (quadrada, alongada nos dois sentidos, grande e pequena):
  **PASSOU**, nenhuma direção suprimida.
- Sapata quadrada + carga centrada: `As_adot(X) == As_adot(Y)` (22,913 cm² em
  ambas) e mesma bitola/arranjo — **PASSOU**.

### Equilíbrio: `momento_unitario()` contra integral própria (Simpson,
10⁵ intervalos, sem reusar `plano_tensoes()` nem `momento_unitario()`)
3 cenários (centrado; excêntrico nas duas direções; excêntrico com sapata
alongada), direções X e Y — 6/6 confrontos batem em 4 casas decimais
(rel. tol. 1e-4). Exemplo: caso 3, dir. X: código = 535,665295, integral
independente = 535,665295 kN·m/m.

### Achado D1 do a6 (dívida de teste, não de cálculo)
Reproduzido `GeometriaImposta(a=3,00, b=1,20, h=0,40)`, `Pilar(0,30, 0,30)`,
`N=4000 kN`: a saída ATUAL do software dá `As_y_adot = 33,96 cm²`
(`modelo="flexao"`, `As_calc=33,96 cm² > As_min=18,00 cm²`) — confirma que o
software em si está correto hoje; D1 continua sendo só ausência de um teste
de regressão contra um mutante hipotético (`As_y *= 0.2` condicional à razão
de lados), não um resultado incorreto atual.

### `ruff check`
`--select E9` no repositório inteiro: **sem erros**. Perfil completo em
`calc_core/geotecnico/`, `calc_core/modelos.py`, `ui/`: **sem erros** — nada
quebrou fora do escopo desta rodada.

### Veredito — GATE 3
**APROVADO.** 100% dos casos de criticidade ALTA (os 4 casos de referência de
`classificar()`, os 6 confrontos de equilíbrio de momento, e a reprodução do
D1) passaram; 0 casos MÉDIA reprovados; todos os testes de equilíbrio e
invariância verdes; suíte completa 101/101; nenhuma divergência entre o
código e o cálculo independente deste agente. Nenhuma alteração de fórmula
encontrada nas correções de citação normativa nem na extração de
`balanco_minimo` (regressão de 1008 combinações, documentada em
`test_planta_travada.py`, com 0 divergências no valor padrão).

Recomendação de dívida técnica (não bloqueante para este GATE): fechar D1 com
um teste de regressão específico para o mutante condicional à razão de lados,
como já sinalizado por a6.

## Adendo — 2026-08-28: corte de espraiamento por camada (GATE 3 pós-GATE 2,
nota 4,60, terceira rodada, 0 achados ALTA)

Escopo: `calc_core/sapata_isolada/geotecnia.py` (funções de propagação —
`influencia_canto_retangulo`, `acrescimo_tensao_centro`,
`acrescimo_tensao_2v1h`, `acrescimo_tensao`, `tensao_liquida_na_base`,
`largura_equivalente`, `propagacao_em_profundidade`, `propagacao_comparada`),
`calc_core/sapata_isolada/visual2d.py::PerfilCortes` (corte na tela) e o
trecho de `recalques.py::AnaliseRecalque` tocado pela consolidação
(REQ-PROP-07). Ruleset v8, `praticas_consagradas > PC-BOUSSINESQ-NEWMARK-
canto-retangulo` (APROVADA) e `PC-ESPRAIAMENTO-2V1H`
(APROVADA_COM_USO_RESTRITO), `requisitos_para_a4 > REQ-PROP-01..09`,
`requisitos_para_a3 > REQ-UI-01..07`.

### Ressalva de escopo herdada do a6, cumprida à risca
`calc_core/sapata_isolada/pranchas.py` **não contém esta feature** — nenhum
número de propagação por camada, rótulo de método ou aviso não-normativo
desta feature chega ao memorial PDF; o único trecho de `pranchas.py` que se
aproxima do assunto (linha 562, "BULBO DE TENSÕES (Boussinesq)") é o bulbo de
**recalque** pré-existente, alimentado por `ResultadoRecalque.parcelas`
(sempre Boussinesq fixo via `AnaliseRecalque.usar_boussinesq=True`), não pela
`PropagacaoTensoes`/`FONTE_2V1H` desta feature — não há seletor de método ali
e não há ambiguidade a rotular. Confirmado por grep (`espraiamento|2v1h|
2V1H|2V:1H|propagacao` → zero ocorrências em `pranchas.py`, exceto a citação
literal a "Boussinesq" da linha 562). **Nenhum caso de validação que confira
o PDF é aqui declarado ALTA nem aprovado — é declarado DESCOBERTO**, conforme
instrução explícita; a ausência já está registrada como pendência com
gatilho (não bloqueante) em `ruleset.yaml > REQ-UI-01 > nota_de_escopo_v8` e
não reprova este GATE 3.

- **DESCOBERTO-01** — `pranchas.py` não emite o croqui de espraiamento por
  camada, o rótulo do método (`prop.rotulo_metodo`) nem os dois avisos
  permanentes (não-normativo / meio homogêneo) no memorial PDF. Trigger de
  reabertura já registrado (gatilhos i/ii/iii de `REQ-UI-01`); o gatilho
  (iii) — "o A7 rodar sobre esta feature" — **acaba de se cumprir com esta
  própria validação**, então a pendência passa de "registrada" para
  "confirmada por A7 nesta rodada" e deve entrar na próxima pauta de A3/A4,
  sem bloquear o GATE 3 atual (a omissão não emite número errado — não emite
  número algum).

### Casos de referência recomputados de forma independente (não usam o
código como oráculo)

**Boussinesq/Newmark** — `acrescimo_tensao_centro` comparado a integração
numérica direta e independente do núcleo pontual `3·q·z³/(2π·R⁵)` sobre o
retângulo carregado (quadratura de Simpson própria, sem importar nada de
`calc_core`, salvo o valor a comparar), em 3 geometrias (2×2, 2,5×4, 1,5×1,5)
× 3 profundidades cada (9 combinações): diferença relativa **0,0000 %** em
todos os pontos (ex.: a=2,5, b=4,0, z=2,5 m → integral = 88,276091 kPa,
`calc_core` = 88,276091 kPa).

`influencia_canto_retangulo(m,n)` conferida separadamente por integração
numérica do canto (Simpson, malha própria) em 11 pares (m,n) de 0,1 a 10,0,
incluindo o ramo crítico `m²n²>m²+n²+1` (m=n=2, 3, 5) e o limite assintótico
m,n→∞ → 0,25 (I(10,10) = 0,249815, fisicamente correto: um plano infinito
dividido em 4 quadrantes carrega q/4 por quadrante): diferença **0,0000** em
todos os 11 pares. **Nota metodológica:** uma primeira tentativa desta
verificação usou uma tabela de Newmark reconstituída de memória, que se
revelou **inconsistente** (I(5,5)=0,3367 excede o limite físico de 0,25) —
descartada e substituída pela integração numérica direta, que não depende de
memorização de tabela.

**2V:1H** — forma fechada `q·a·b/((a+z)(b+z))` recomputada à parte e
comparada a `acrescimo_tensao_2v1h` nas mesmas 9 combinações: diferença
**0,0e+00** em todas.

### Equilíbrio e invariância (verificação física direta, independe de
bibliografia)

- z=0 → Δσ = q exatamente, nos dois métodos, nas 3 geometrias: **confirmado**.
- Equilíbrio vertical exato do 2V:1H, `Δσ·(a+z)(b+z) = q·a·b`, em 5
  profundidades × 3 geometrias (15 pontos): erro relativo **0,0** (ou
  1,1e-16, ruído de ponto flutuante) em todos.
- Δσ estritamente decrescente com z, nos dois métodos, e largura equivalente
  (`a_eq`) estritamente crescente com z, nas 3 geometrias: **confirmado** em
  8 profundidades por geometria (z de 0 a 20 m).
- z→∞: Δσ→0 nos dois métodos (checado em z=1e6 m): **confirmado**.

Todos os valores acima batem, ponto a ponto, com o que já está documentado
em `ruleset.yaml > PC-BOUSSINESQ-NEWMARK-canto-retangulo > checagem_numerica`
e `PC-ESPRAIAMENTO-2V1H > checagem_numerica` (I(1,1)=0,17522; equilíbrio
exato; contorno em z=0) — recomputados aqui de forma independente, não
aceitos por citação.

### REQ-PROP-03(A) — sem veredito

Grep em `geotecnia.py` e no bloco `PerfilCortes` de `visual2d.py` por
PASSA/aprovado/reprovado/falha/cor de reprovação: **nenhuma ocorrência** fora
de comentários/docstrings que **proíbem** essas construções. A rampa de cor
do tronco (`cor_hex`, vermelho = mais Δσ) é reaproveitada de `MapaMomentos` e
é escala de magnitude, não veredito — documentado como tal na própria
docstring de `_espraiamento`. `test_resultado_nao_carrega_nenhum_veredito`
(já existente) roda e passa, e a inspeção manual dos campos de
`PropagacaoTensoes`/`PontoPropagacao`/`CamadaPropagacao` confirma ausência de
qualquer campo de aprovação/limite. **Condição da aprovação de
`PC-ESPRAIAMENTO-2V1H` cumprida**, não apenas estilo.

### `PC-ESPRAIAMENTO-2V1H` uso restrito respeitado

- `AnaliseRecalque.__init__` mantém `usar_boussinesq: bool = True` como
  default (`recalques.py:239`).
- Grep em todo o repositório por `usar_boussinesq`: o único caminho de
  produção que instancia `AnaliseRecalque` é `sapata.py:919`, sem passar o
  parâmetro (default prevalece); as únicas ocorrências de
  `usar_boussinesq=False` estão em `tests/test_propagacao_tensoes.py`
  (testes que travam justamente esse comportamento).
- Grep por `fonte_espraiamento` em todo `calc_core/` e `ui/`: confinado a
  `visual2d.py` (núcleo do widget) e `ui/completo/visualizacao.py` (seletor
  de tela) — nenhum caminho liga a escolha de método do corte a
  `AnaliseRecalque` nem a `Sapata`/capacidade de carga.
- `tests/test_propagacao_tensoes.py::test_recalque_continua_com_boussinesq_por_default`
  e `::test_propagacao_nao_expoe_seletor_de_recalque` (REQ-PROP-05) — **ambos
  passam**; o segundo inspeciona a assinatura de `propagacao_em_profundidade`
  (sem `usar_boussinesq`) e o código-fonte de `AnaliseRecalque._delta_sigma`
  (sem chamar `propagacao_em_profundidade`), continuam protegendo a fronteira.

### Rastreabilidade normativa

Toda função pública nova/tocada em `geotecnia.py` carrega `[pratica: PC-*]`
(nunca `[rule:]`): `influencia_canto_retangulo`, `acrescimo_tensao_centro`,
`acrescimo_tensao_2v1h`, `acrescimo_tensao`, `tensao_liquida_na_base`,
`largura_equivalente`, `propagacao_em_profundidade`, `propagacao_comparada` —
confirmado por inspeção via AST (não apenas grep de texto). `visual2d.py`
(`_espraiamento`) e `recalques.py` (`_delta_sigma`) citam a prática aplicável
no docstring. Único `[rule:]` remanescente nestes três arquivos é o
pré-existente e não relacionado (`Solo.fs_deslizamento`,
NBR6122-6.2.1.1.2, PENDENTE_HUMANO, fora do escopo desta feature).

### Suíte completa

`pytest tests/` rodado num venv Python 3.12 com tkinter (permite incluir os
testes de `visual2d.py`): **308/308 passando**, batendo com o número
declarado pelo a6 na v8 do ruleset. Isolando
`tests/test_propagacao_tensoes.py`: **166/166 passando**.
`ruff check --select E9 calc_core/ ui/`: sem erros (mesmo critério das
rodadas anteriores; `ruff check` completo, sem `--select`, aponta 52 avisos
de estilo `UP045`/`Optional`→`X | None`, pré-existentes e fora do escopo
desta feature — não é regressão introduzida por ela).

### Render real (Xvfb + tkinter, `canvas.postscript()` → PNG via
Ghostscript)

Sapata 3,00×0,90 m sobre perfil de 4 camadas (aterro/areia média/argila
mole/areia compacta), N.A. em 3,00 m, carga excêntrica (My=150 kN·m) — mesmo
tipo de caso já usado pelo a6 nas rodadas de GATE 2, mas renderizado nesta
rodada, de novo, por este agente.

- **Corte X, Boussinesq:** rótulos por interface `a_eq = 3.00 m` / `a_eq =
  4.79 m` / `a_eq = 7.24 m` e `q = 124.8 kPa` / `q = 43.1 kPa` / `q = 17.7
  kPa` — nunca "L". Os dois avisos permanentes (não-normativo, meio
  homogêneo) presentes, rótulo de método `Boussinesq/Newmark (método não
  normativo) · q_líq 125 kPa` e a ressalva "leitura geométrica ILUSTRATIVA"
  específica do Boussinesq, todos no bloco fixo do topo. Tronco contido no
  canvas.
- **Corte Y, 2V:1H + bulbo combinados:** rótulo de método `Espraiamento
  2V:1H — 26,57° (método não normativo) · q_líq 125 kPa` com a ressalva
  específica ("subestima Δσ na faixa rasa... superestima abaixo de ~1,9·B,
  onde a comparação... inverte de sinal"), rótulos `b_eq` (nunca `a_eq` nem
  "L", corretamente trocado por estar em corte Y) por interface. Tronco e
  isolinhas do bulbo contidos no canvas, sem sobreposição ilegível.
- Nenhum texto de veredito (PASSA/aprovado/reprovado) em nenhum dos 150/170
  itens desenhados no canvas, nas duas configurações — lista de textos
  extraída programaticamente do canvas, não só inspeção visual.

Imagens em
`/tmp/claude-0/-home-user-Software-de-dimensionamento-de-sapatas/08dfb96e-3dcd-5ce8-8489-4cf432c45335/scratchpad/a7_check_boussinesq.png`
e `a7_check_2v1h.png` (scratchpad da sessão, não versionadas).

### Veredito — GATE 3

**APROVADO**, com uma pendência DESCOBERTA (não bloqueante, já registrada com
gatilho no ruleset v8) devolvida a A3/A4 para a próxima pauta.

- 100 % dos casos de criticidade ALTA passaram: os 9+9 confrontos numéricos
  independentes (Boussinesq e 2V:1H), os 11 pares de `influencia_canto_
  retangulo`, os 15 pontos de equilíbrio vertical exato do 2V:1H, a ausência
  de veredito (REQ-PROP-03(A)), o uso restrito do 2V:1H (REQ-PROP-05) e a
  suíte completa (308/308).
- 0 casos MÉDIA/BAIXA reprovados nesta rodada; a única pendência encontrada
  (DESCOBERTO-01, ausência no PDF) é de natureza diferente — omissão
  documentada, não erro — e por instrução explícita desta rodada **não pode
  ser classificada como ALTA reprovada** enquanto a seção não existir no
  memorial; ela é reportada como confirmação do gatilho (iii) já previsto em
  `REQ-UI-01 > nota_de_escopo_v8`.
- Nenhum defeito de cálculo, equilíbrio violado ou veredito indevido
  encontrado — reconfirma, sem depender do relato do a6, o histórico desta
  feature. Nenhuma regressão real identificada; nada devolvido a A4/A5 além
  do já registrado.

## Adendo — 2026-08-28: salvar/abrir projeto (.s7proj) + importar/exportar
## Excel (`ui/completo/`), GATE 2 aprovado rodada 3/3 nota 4,5 + correção N1

Escopo: `ui/completo/projeto.py`, `ui/completo/excel_import.py`,
`ui/completo/excel_export.py` (commits `0eb8011` feature completa +
`2b78697` correção do único MÉDIA remanescente, N1). Como o próprio a6
apontou no despacho, esta feature é I/O puro (serialização JSON, planilha
Excel) — não introduz fórmula de engenharia nova. O que este agente
exercitou foram os **caminhos de dado**, não a física: tela → arquivo →
tela, planilha → núcleo vs. tela → núcleo, e PDF vs. Excel do mesmo
cálculo, campo a campo — na ordem sugerida pelo a6.

Ambiente: `tkinter` não está disponível no Python 3.11 deste container;
suíte completa rodada num venv Python 3.12 (`pytest`, `openpyxl`,
`hypothesis`) sob `xvfb-run -a`, com `CI=true` (o próprio
`test_ci_exige_display_para_suite_de_tk` desta feature falha em vez de
pular se isso não estiver correto — rodou e passou). Scripts ad hoc desta
rodada em
`/tmp/claude-0/-home-user-Software-de-dimensionamento-de-sapatas/08dfb96e-3dcd-5ce8-8489-4cf432c45335/scratchpad/`
(`item1_tela_a_tela.py`, `item2_planilha_vs_digitado.py`,
`item3_pdf_vs_excel.py`, `item6_invariancia.py`, `pdf_extrai_texto.py` —
scratchpad da sessão, não versionados; não são regressão automática até
serem promovidos a `tests/` por A3).

### Suíte completa (linha de base, antes de qualquer script ad hoc)

`pytest tests/ -q`: **401/401 passando** (398 + as 3 novas do commit
`2b78697`), confirmando o número do commit de forma independente.
`tests/test_projeto_e_excel.py` isolado: **93/93 passando**.

### Item 1 — round-trip `.s7proj` TELA-a-TELA (ALTA) — **PASSOU**

O teste existente (`test_projeto_round_trip_bit_identico`) só cobre
Python-a-Python via `asdict(dimensionar())`; não passa pela tela. Este
agente montou duas instâncias reais de `PainelEntrada` sob Xvfb: a
primeira com pilar, materiais, G+Q+W, solo com perfil de 3 camadas
(aterro/areia/**argila mole com Cc/Cs/e0/OCR/cv/C_alpha/drenagem_dupla**),
N.A., `modelo_reacao="elastico"`, `modelo_armadura_rigida="flexao"`;
salvou com `projeto.salvar_projeto`; reabriu numa SEGUNDA instância via
`projeto.carregar_projeto` + os cinco `preencher_*`; leu de volta com os
`ler_*`. Todos os 20 campos comparados (pilar, solo incluindo as 3 camadas
completas e N.A., materiais, cobrimento, os 3 casos de carga com seus
`Esforcos`, e as opções de modelo) batem **exatamente** — não só que
`dimensionar()` dá o mesmo resultado, o CAMINHO
`PainelEntrada→arquivo→PainelEntrada` preserva os dados visíveis, byte a
byte nos campos que a tela expõe. Nenhuma divergência.

### Item 2 — planilha importada vs. digitado à mão (ALTA) — **REPROVOU**

Montado um perfil de 4 camadas (aterro/areia argilosa/argila
mole/areia compacta, com N.A.) com valores de `gamma_nat`/`gamma_sat`/
`phi`/`coesao` REALISTAS e diferenciados por camada (como qualquer perfil
geotécnico de verdade tem) diretamente em `PainelEntrada._camadas`; a
mesma planilha foi gerada por `excel_import.gerar_modelo_importacao` e
editada com os MESMOS valores nas colunas que a aba "Perfil geotécnico"
de fato tem (`camada | tipo | espessura | nspt | Cc | e0 | cv | Es | nível
d'água`); importada de volta via `excel_import.importar_perfil_geotecnico`.
Resultado, para o MESMO pilar/cargas/solo de apoio nos dois casos:

```
digitado na tela : recalque_total_mm = 117.62
importado do xlsx: recalque_total_mm = 109.65
diferença        : 7.97 mm  (6,8 % do total) — FORA da tolerância de
                    equilíbrio esperada (deveria ser 0,000, não ±15 %;
                    esta não é uma comparação contra bibliografia, é o
                    MESMO cálculo por dois caminhos que deveriam ser
                    idênticos)
```

**Causa raiz:** `excel_import.py::importar_perfil_geotecnico` constrói
cada camada com `Camada(nome=nome, espessura=espessura, tipo=tipo,
nspt=nspt, Cc=Cc, e0=e0, cv=cv, Es=Es)` — **sem** `gamma_nat`,
`gamma_sat`, `phi` nem `coesao`. A aba "Perfil geotécnico"
(`CABECALHO_PERFIL`) não tem coluna nenhuma para esses quatro campos.
Toda camada importada de uma planilha recebe, em silêncio, os defaults do
dataclass `Camada` (`gamma_nat=18.0`, `gamma_sat=20.0`, `phi=30.0`,
`coesao=0.0`) — nunca os valores reais do perfil geotécnico do projeto.
`PerfilGeotecnico.tensao_vertical_efetiva` (`geotecnia.py:141`) usa
`gamma_nat`/`gamma_sat` diretamente na tensão vertical efetiva por
camada, que alimenta `recalque_adensamento`/`recalque_schmertmann`
(`recalques.py`) — não é um campo decorativo, é um dos poucos parâmetros
que mais pesam no recalque de uma camada coesiva. A magnitude da
divergência (aqui 6,8 %) escala com o quão diferente o perfil real é dos
defaults genéricos — pode ser maior ou menor caso a caso, inclusive do
lado inseguro (um solo mais leve que 18/20 kN/m³ real, importado como
18/20, SUPERESTIMA a tensão efetiva e pode tanto super quanto
subestimar o recalque dependendo de qual lado do cálculo domina).

**Por que isto é `BUG`, não `HIPOTESE_DIVERGENTE` nem
comportamento-pré-existente-documentado:** ao contrário do padrão já
usado em `projeto.py` (`CAMPOS_NAO_REPOSTOS` — documentado na íntegra,
com aviso nominal ao usuário via `campos_divergentes_do_default`, e
testado em 6+ casos), a ausência de `gamma_nat`/`gamma_sat`/`phi`/
`coesao` na planilha de perfil geotécnico **não tem nenhum aviso
equivalente**: nem no docstring do módulo (que documenta em detalhe
`cv`/`Es`/N.A. mas nunca menciona que peso específico e resistência da
camada não são capturados), nem na aba "Instruções" gerada por
`gerar_modelo_importacao`, nem em qualquer diálogo de
`ui/completo/app.py::_importar_excel`. O próprio despacho desta rodada
presumia "os dois caminhos terminam nos mesmos construtores
`Camada`/`PerfilGeotecnico`" — presunção correta para pilar/cargas
(`importar_pilar_e_cargas`, que reproduz `Pilar`/`Esforcos` completos) mas
**falsa** para o perfil geotécnico, e isso passou pelas 3 rodadas de GATE
2 sem ser pego (nenhum teste de `test_projeto_e_excel.py` compara um
perfil importado contra o mesmo perfil digitado — só contra os valores
que a própria planilha de exemplo já tinha, o que não expõe a lacuna).

**Devolvido a A3** (`ui/completo/excel_import.py`), criticidade **ALTA**:
ou (a) acrescentar colunas `gamma_nat`/`gamma_sat`/`phi`/`coesao` (m
opcionais, como `Cc`/`e0`) à aba "Perfil geotécnico" e passá-las ao
construtor de `Camada`, ou (b), no mínimo, avisar explicitamente — no
docstring, na aba "Instruções" e num diálogo em `_importar_excel` — que
esses quatro campos **não são importados** e ficam nos defaults
genéricos, no mesmo padrão de aviso nominal já usado em
`projeto.CAMPOS_NAO_REPOSTOS`/`campos_divergentes_do_default`. Recomendo
também um teste permanente equivalente ao script desta rodada (perfil
digitado vs. mesmo perfil pela planilha, comparando `recalque_total_mm`)
em `tests/test_projeto_e_excel.py`.

### Item 3 — memorial Excel vs. memorial PDF do MESMO cálculo, campo a
### campo (ALTA) — **PASSOU nos valores; 3 achados de rótulo/cobertura, não
### bloqueantes**

Calculado um caso (pilar 40×40, C30, **CA-60** — escolhido de propósito
para expor rótulo de categoria de aço —, `N=900+250`, sem perfil
geotécnico), exportado `pranchas.gerar_memorial_pdf` e
`excel_export.exportar_relatorio_excel` do MESMO `resultado`. Como o PDF
é escrito à mão com `zlib` (sem biblioteca de PDF), este agente escreveu
um extrator de texto ad hoc (descompacta cada `stream`/`endstream` com
`zlib`, concatena os `Tj` dentro de cada bloco `BT..ET`) para comparar
programaticamente, não por inspeção visual.

- **Tensões** (`ELS-G — σ_máx/limite`: PDF "202.1 ... 250"; Excel "202.1 /
  250.0" — e `G+Q`: PDF "249.3 ... 250"; Excel "249.3 / 250.0"),
  **armaduras** (`A_s,calc`/`A_s,mín`/`A_s adotada`/detalhamento
  "22 Ø 12.5 mm c/ 11 cm (A_s,ef = 27.00 cm²)" idêntico nos dois canais,
  dígito a dígito) e o **veredito geral** (`APROVADA`/reprovações/alertas)
  batem exatamente entre os dois canais — confirma que ambos formatam o
  mesmo `ResultadoSapata`, não dois cálculos independentes.
- **Achado (BAIXA, pré-existente, fora do escopo desta feature — não
  causado pelos commits `0eb8011`/`2b78697`):** `pranchas.py:340` imprime
  `f"Peso total de aço CA-50: ..."` com "CA-50" **hardcoded**, mesmo com
  `Aco(fyk=600.0)` — no MESMO PDF, a linha de materiais (via
  `relatorio.py:47`) mostra corretamente "CA-600". O documento fica
  auto-inconsistente (duas menções à categoria do aço, uma certa outra
  fixa) sempre que o aço não é o CA-50 default. `pranchas.py` não foi
  tocado pelos commits desta feature; registrado aqui porque só apareceu
  ao fazer a comparação PDF×Excel pedida por este GATE — recomendo rotear
  a quem mantém `pranchas.py`, fora desta feature.
- **Achado (BAIXA):** `excel_export.py` não inclui "Cobrimento nominal" no
  resumo — o PDF mostra em dois lugares (`cobr. 4.5` no desenho e
  "Cobrimento nominal .. 4.5 cm" no quadro/memorial texto), o Excel não
  tem essa linha em nenhuma seção. Lacuna de cobertura, não valor errado.
- **Observação (não é defeito):** a seção "Geometria" do Excel usa
  `round(resultado.a, 3)` (3 casas) enquanto o quadro do PRÓPRIO PDF
  (`pranchas.py`, não o memorial-texto) usa `f"{a:.2f}"` (2 casas) — MESMO
  valor (2,30 m em ambos), só a apresentação difere ("2.30" no PDF vs.
  "2.3" na célula do Excel, sem zero à direita). O memorial-texto embutido
  no PDF (`relatorio.py`, produzido por `f"{res.volume_concreto:.3f}"`
  etc.) já usa 3 casas nesses campos e bate exatamente com o Excel — a
  única divergência de precisão é dentro do próprio PDF, entre o quadro
  desenhado e o memorial-texto que ele mesmo embute, pré-existente e não
  desta feature.

### Item 4 — aviso do N1 (`campos_divergentes_do_default`) — **CONFIRMADO
### CORRIGIDO**

Reproduzido o cenário exato do defeito original: projeto com G/Q/W salvo
e reaberto (`ler_casos` sempre recompõe W com `CasoCarga.vento(...)`, que
sobrescreve `psi0=0,6`/`psi1=0,3`/`psi2=0,0`/`reversivel=True` — valores
que ANTES da correção divergiam do default cru do dataclass `CasoCarga` e
geravam 6 avisos falsos de "campo não reposto"). Rodado com o script desta
sessão (item 1, reaproveitando os mesmos dados G/Q/W digitados): `
projeto.campos_divergentes_do_default(dados)` devolve lista **vazia** — 0
avisos falsos, como esperado após `2b78697`. O caso de falso-negativo (
`.s7proj` editado à mão com `W.psi0=0,7`, que corresponderia ao default
cru do dataclass mas diverge do que `ler_casos` de fato repõe para W) já
tem cobertura permanente em
`test_campos_divergentes_do_default_detecta_psi0_w_editado_a_mao`
(passou na suíte completa) — não repetido manualmente por já estar
coberto. **N1 confirmado corrigido, nas duas direções.**

### Item 5 — nenhum veredito/cálculo na UI (REQ-PROP-03(A) aplicado a esta
### feature) — **PASSOU com um achado MÉDIA**

Leitura integral de `projeto.py`, `excel_import.py` e `excel_export.py`
confirma o padrão: toda validação é de DOMÍNIO/TIPO (não de engenharia —
"o número pode existir", nunca "o número é aceitável estruturalmente"), e
todo campo exportado em `excel_export.py` é leitura direta de um campo já
calculado em `ResultadoSapata`/`Sapata`, com `_situacao(ok)` só traduzindo
um booleano JÁ calculado pelo núcleo em texto "OK"/"NÃO OK".

**Achado (MÉDIA, devolvido a A3):** uma exceção a esse padrão —
`excel_export.py:114`:

```python
ok_direcao = (ar.as_suficiente and ar.dominio_ok and ar.ancoragem_ok
             and ar.espacamento_ok)
```

`ArmaduraDirecao` (`sapata.py`) não expõe um único campo `ok` por
direção — só os 4 booleanos individuais. Este `and` de 4 termos
**recomputa**, dentro da UI, exatamente a mesma expressão que
`Sapata._montar_resultado` já usa para compor `resultado.aprovado`
(`sapata.py:243-244`: `all(a.dominio_ok and a.ancoragem_ok and
a.as_suficiente and a.espacamento_ok for a in self.armaduras)`) — hoje
IDÊNTICA à do núcleo (confirmado por leitura lado a lado), mas é uma
fórmula DUPLICADA, não um campo consumido. Se o núcleo um dia adicionar
um quinto critério a essa composição (ex.: uma verificação nova de
punção por direção), `excel_export.py` continuaria mostrando "OK" com
base só nos 4 critérios antigos, sem nenhum teste que capture a
divergência — drift silencioso. Nem `relatorio.py` nem `pranchas.py`
fazem essa composição: ambos imprimem os 4 flags/anotações
separadamente, nunca um "OK"/"NÃO OK" agregado por direção. Confirmado
por `git show 0eb8011 -- ui/completo/excel_export.py`: a linha já nasceu
assim nesta feature, não é código anterior. Recomendo expor um campo
`ok`/`aprovada` em `ArmaduraDirecao` (calc_core) e `excel_export.py`
passar a lê-lo, em vez de recompor o `and`.

### Item 6 — equilíbrio: salvar/reabrir não muda `dimensionar()` (rígida,
### flexível, com vento) — **PASSOU**

Não havia teste automatizado para os três perfis pedidos explicitamente
pelo a6; rodado nesta sessão (script `item6_invariancia.py`):

| caso      | rígida | `a` (m) | `b` (m) | `h` (m) | bit-idêntico após save/reload |
|-----------|--------|---------|---------|---------|--------------------------------|
| rígida    | True   | 1.60    | 1.80    | 0.40    | **sim** |
| flexível  | False  | 1.20    | 3.00    | 0.35    | **sim** |
| com vento | True   | 2.30    | 1.90    | 0.65    | **sim** |

`asdict(resultado_antes) == asdict(resultado_depois)` para os 3 casos —
igualdade estrita, não tolerância. Recomendo promover este script a um
teste permanente em `tests/test_projeto_e_excel.py` (hoje só existe o
round-trip Python-a-Python com um único perfil "rígido" implícito).

### Veredito — GATE 3

**REPROVADO.** O critério do próprio despacho — "100 % dos casos de
criticidade ALTA (round-trip tela-a-tela, planilha-vs-digitado,
PDF-vs-Excel) precisam passar" — não se cumpre: o item 2
(planilha-vs-digitado) reproduz uma divergência real e mensurável (7,97 mm
de recalque, 6,8 %) por um defeito específico e localizável em
`excel_import.py::importar_perfil_geotecnico`, não uma tolerância de
arredondamento nem uma hipótese bibliográfica divergente — classificado
como **`BUG`**, devolvido a **A3**.

- Item 1 (tela-a-tela): **PASSOU**, 100 %.
- Item 2 (planilha-vs-digitado): **REPROVOU** — `BUG` ALTA, devolvido a
  A3/`excel_import.py` (perfil geotécnico sem colunas de
  `gamma_nat`/`gamma_sat`/`phi`/`coesao`, silenciosamente substituídos
  pelo default do dataclass `Camada`, sem aviso nenhum ao usuário).
- Item 3 (PDF-vs-Excel): **PASSOU** nos valores calculados conferidos
  (tensões, armaduras, veredito); 1 achado BAIXA pré-existente fora do
  escopo desta feature (`pranchas.py`, rótulo "CA-50" fixo) e 1 achado
  BAIXA desta feature (cobrimento ausente do resumo Excel) — nenhum dos
  dois muda o veredito do item, mas ambos registrados para a próxima
  pauta.
- Item 4 (N1): confirmado corrigido nas duas direções (falso-positivo
  testado manualmente nesta rodada; falso-negativo já coberto por teste
  permanente).
- Item 5 (REQ estrutural — nenhum veredito na UI): **PASSOU** com 1
  achado MÉDIA devolvido a A3 (`ok_direcao` recompõe lógica do núcleo em
  vez de consumir um campo único — sem divergência numérica HOJE, mas
  risco de deriva sem teste que o pegue).
- Item 6 (equilíbrio save/reload): **PASSOU**, 3/3 casos bit-idênticos.

**Não corrigido por este agente** (fora do mandato desta rodada). Devolve
a **A3** dois defeitos específicos (item 2, ALTA; item 5, MÉDIA) e regista
dois achados de baixa severidade para a próxima pauta de quem mantém
`pranchas.py`/`excel_export.py`. Recomenda-se que, antes de reabrir o
GATE 3, A3 promova pelo menos os scripts dos itens 1, 2 e 6 desta rodada a
testes permanentes em `tests/test_projeto_e_excel.py` — nenhum dos três
tinha cobertura automática antes desta validação.
