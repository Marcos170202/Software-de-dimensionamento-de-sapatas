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
