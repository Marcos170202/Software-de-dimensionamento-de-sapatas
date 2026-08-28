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
