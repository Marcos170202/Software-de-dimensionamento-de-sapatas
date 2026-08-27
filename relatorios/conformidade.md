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
