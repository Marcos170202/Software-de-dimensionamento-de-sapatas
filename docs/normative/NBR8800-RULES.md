# Rastreabilidade de regras — ABNT NBR 8800:2024

Registro de toda regra normativa implementada em
`estrutura_metalica.normative.nbr8800`. Cada entrada segue o formato:

```
RULE-ID:
SOURCE:
DESCRIPTION:
IMPLEMENTATION:
TEST:
```

Fonte de todas as regras abaixo: PDF `NBR 8800 - 2024 - Projeto de
Estruturas de Aço e de Estruturas Mistas de Aço e Concreto de
Edifícios.pdf` (terceira edição, 02.10.2024). Nenhum valor ou fórmula
abaixo foi obtido de memória/treinamento — todos foram conferidos por
leitura direta das páginas citadas (renderização visual das páginas do
PDF). O PDF em si não está neste repositório (está no repositório
irmão `dimensionamento-estrutural`, onde esse mesmo corpo normativo já
havia sido implementado e validado antes desta fase) — a leitura das
páginas abaixo foi feita diretamente contra esse PDF antes de escrever
qualquer fórmula aqui, e a implementação/estrutura de rastreabilidade
deste módulo foi adaptada da já validada naquele repositório (mesma
norma, mesmas fórmulas, entidades de domínio diferentes).

## RULE-ID: NBR8800-RES-001

- **SOURCE:** NBR 8800:2024, 4.9.2 "Coeficientes de ponderação das
  resistências no estado-limite último (ELU)", Tabela 3, página 25.
- **DESCRIPTION:** Coeficientes de ponderação da resistência do aço
  estrutural, γa1 (escoamento e instabilidade) e γa2 (ruptura), por
  classe de combinação última de ações:
  - Normais: γa1 = 1,10; γa2 = 1,35.
  - Especiais ou de construção: γa1 = 1,10; γa2 = 1,35.
  - Excepcionais: γa1 = 1,00; γa2 = 1,15.

  Escopo: apenas a coluna "Aço estrutural" da Tabela 3.
- **IMPLEMENTATION:**
  `estrutura_metalica.normative.nbr8800.resistance_factors.steel_resistance_factors`.
- **TEST:** `tests/normative/test_nbr8800_resistance_factors.py`.

## RULE-ID: NBR8800-TRAC-001

- **SOURCE:** NBR 8800:2024, 5.2.1.2 (condição `Nt,Sd <= Nt,Rd`) e
  5.2.2 caso a) "para escoamento da seção bruta", página 39.
- **DESCRIPTION:** Força axial de tração resistente de cálculo por
  escoamento da seção bruta: `Nt,Rd = Ag·fy / γa1`.
- **IMPLEMENTATION:**
  `estrutura_metalica.normative.nbr8800.tension.check_tension_member`
  (`TensionCheckResult.nt_rd_yield`).
- **TEST:** `tests/normative/test_nbr8800_tension.py`.

## RULE-ID: NBR8800-TRAC-002

- **SOURCE:** NBR 8800:2024, 5.2.2 caso b) "para ruptura da seção
  líquida", página 39.
- **DESCRIPTION:** Força axial de tração resistente de cálculo por
  ruptura da seção líquida: `Nt,Rd = Ae·fu / γa2`.
- **IMPLEMENTATION:**
  `estrutura_metalica.normative.nbr8800.tension.check_tension_member`
  (`TensionCheckResult.nt_rd_rupture`).
- **TEST:** `tests/normative/test_nbr8800_tension.py`.

## RULE-ID: NBR8800-TRAC-003

- **SOURCE:** NBR 8800:2024, 5.2.4.2, página 39: "Em regiões em que
  não existam furos, a área líquida, An, deve ser considerada igual à
  área bruta da seção transversal, Ag."
- **DESCRIPTION:** Caso particular (sem furos) da área líquida usada
  em NBR8800-TRAC-002: `An = Ag`.
- **IMPLEMENTATION:**
  `estrutura_metalica.normative.nbr8800.tension.net_area_without_holes`.
- **TEST:** `tests/normative/test_nbr8800_tension.py`.

## RULE-ID: NBR8800-TRAC-004

- **SOURCE:** NBR 8800:2024, 5.2.8.1, página 44.
- **DESCRIPTION:** Limitação RECOMENDADA (não estado-limite último
  obrigatório) do índice de esbeltez de uma barra tracionada
  individual: `ℓ/r ≤ 300`, tomando o maior valor entre os dois eixos
  principais.
- **IMPLEMENTATION:**
  `estrutura_metalica.normative.nbr8800.slenderness.check_tension_slenderness`.
- **TEST:** `tests/normative/test_nbr8800_slenderness.py`.

## RULE-ID: NBR8800-COMP-001

- **SOURCE:** NBR 8800:2024, 5.3.1 (condição `Nc,Sd <= Nc,Rd`) e 5.3.2,
  página 45.
- **DESCRIPTION:** Força axial de compressão resistente de cálculo:
  `Nc,Rd = χ·Aef·fy / γa1`.
- **IMPLEMENTATION:**
  `estrutura_metalica.normative.nbr8800.compression.check_compression_member`.
- **TEST:** `tests/normative/test_nbr8800_compression.py`.

## RULE-ID: NBR8800-COMP-002

- **SOURCE:** NBR 8800:2024, 5.3.3.1, página 45.
- **DESCRIPTION:** Fator de redução: `χ = 0,658^(λ0²)` para
  `λ0 ≤ 1,5`; `χ = 0,877/λ0²` para `λ0 > 1,5`.
- **IMPLEMENTATION:**
  `estrutura_metalica.normative.nbr8800.compression.reduction_factor`.
- **TEST:** `tests/normative/test_nbr8800_compression.py`.

## RULE-ID: NBR8800-COMP-003

- **SOURCE:** NBR 8800:2024, 5.3.3.2, página 45.
- **DESCRIPTION:** Índice de esbeltez reduzido: `λ0 = sqrt(Ag·fy/Ne)`.
- **IMPLEMENTATION:**
  `estrutura_metalica.normative.nbr8800.compression.slenderness_parameter`.
- **TEST:** `tests/normative/test_nbr8800_compression.py`.

## RULE-ID: NBR8800-COMP-004

- **SOURCE:** NBR 8800:2024, 5.3.4.1, página 46.
- **DESCRIPTION:** Caso particular (sem flambagem local) da área
  efetiva usada em NBR8800-COMP-001: `Aef = Ag`.
- **IMPLEMENTATION:**
  `estrutura_metalica.normative.nbr8800.compression.effective_area_without_local_buckling`.
- **TEST:** `tests/normative/test_nbr8800_compression.py`.

## RULE-ID: NBR8800-COMP-005

- **SOURCE:** NBR 8800:2024, 5.3.5.1, casos a) e b), página 48:
  `Nex = π²EIx/Lx²`, `Ney = π²EIy/Ly²`.
- **DESCRIPTION:** Força axial de flambagem elástica por flexão em
  torno de um eixo principal de inércia. **LIMITAÇÃO DE SEGURANÇA**:
  5.3.5.1 exige `Ne = min(Nex, Ney, Nez)` — `Nez` também está
  implementado (NBR8800-COMP-006/007). Seções monossimétricas/
  assimétricas (5.3.5.2/5.3.5.3, flexo-torção `Neyz` ou equação
  cúbica) NÃO estão implementadas — para essas, `min(Nex,Ney,Nez)` NÃO
  é a fórmula correta e seria não conservador.
- **IMPLEMENTATION:**
  `estrutura_metalica.normative.nbr8800.compression.flexural_buckling_force`.
- **TEST:** `tests/normative/test_nbr8800_compression.py`.

## RULE-ID: NBR8800-COMP-006

- **SOURCE:** NBR 8800:2024, 5.3.5.1, caso c), página 48:
  `Nez = (1/r0²)[π²ECw/Lz² + GJ]`.
- **DESCRIPTION:** Força axial de flambagem elástica por torção em
  relação ao eixo longitudinal. Válida apenas para seções com dupla
  simetria ou simétricas em relação a um ponto (`x0=y0=0` em `r0`).
- **IMPLEMENTATION:**
  `estrutura_metalica.normative.nbr8800.compression.torsional_buckling_force`.
- **TEST:** `tests/normative/test_nbr8800_compression.py`.

## RULE-ID: NBR8800-COMP-007

- **SOURCE:** NBR 8800:2024, 5.3.5.1, página 49:
  `r0 = sqrt(rx²+ry²+x0²+y0²)`; `x0=y0=0` para seções com dupla
  simetria ou simétricas em relação a um ponto.
- **DESCRIPTION:** Raio de giração polar em relação ao centro de
  cisalhamento, caso particular `x0=y0=0`: `r0 = sqrt(rx²+ry²)`. Usado
  como entrada de `Nez` (NBR8800-COMP-006).
- **IMPLEMENTATION:**
  `estrutura_metalica.normative.nbr8800.compression.polar_radius_of_gyration`.
- **TEST:** `tests/normative/test_nbr8800_compression.py`.

## RULE-ID: NBR8800-COMP-008

- **SOURCE:** NBR 8800:2024, 5.3.7.1, página 52.
- **DESCRIPTION:** Limitação RECOMENDADA do índice de esbeltez de uma
  barra comprimida individual: `ℓ/r ≤ 200`, o maior valor entre os
  dois eixos principais.
- **IMPLEMENTATION:**
  `estrutura_metalica.normative.nbr8800.slenderness.check_compression_slenderness`.
- **TEST:** `tests/normative/test_nbr8800_slenderness.py`.

## RULE-ID: NBR8800-SHEAR-001

- **SOURCE:** NBR 8800:2024, 5.4.1.3, página 53: "No dimensionamento
  das barras submetidas a momento fletor e força cortante, devem ser
  atendidas as seguintes condições: MSd ≤ MRd; VSd ≤ VRd".
- **DESCRIPTION:** Condição de dimensionamento ao cisalhamento:
  `Vsd ≤ Vrd`. A condição equivalente de momento fletor (`Msd ≤ Mrd`,
  5.4.2) **não é implementada nesta fase**.
- **IMPLEMENTATION:**
  `estrutura_metalica.normative.nbr8800.shear.check_shear_major_axis`.
- **TEST:** `tests/normative/test_nbr8800_shear.py`.

## RULE-ID: NBR8800-SHEAR-002

- **SOURCE:** NBR 8800:2024, 5.4.3.1.2, página 57-58: "Vpℓ =
  0,60·Aw·fy [...] Aw = d·tw, onde d é a altura total da seção
  transversal; tw é a espessura da alma."
- **DESCRIPTION:** Força cortante correspondente à plastificação da
  alma por cisalhamento (`Vpℓ = 0,60·Aw·fy`) e área efetiva de
  cisalhamento para seções I, H e U fletidas em relação ao eixo
  perpendicular à alma (`Aw = d·tw`).
- **IMPLEMENTATION:**
  `estrutura_metalica.normative.nbr8800.shear.plastic_shear_force`,
  `estrutura_metalica.normative.nbr8800.shear.effective_shear_area_major_axis`.
- **TEST:** `tests/normative/test_nbr8800_shear.py`.

## RULE-ID: NBR8800-SHEAR-003

- **SOURCE:** NBR 8800:2024, 5.4.3.1.1, página 57: curva de 3 trechos
  de `Vrd` (`λ = h/tw`; `λp = 1,10·sqrt(kv·E/fy)`;
  `λr = 1,37·sqrt(kv·E/fy)`); `h` é a altura da alma (distância entre
  as faces internas das mesas em perfis soldados, ou esse valor menos
  os dois raios de concordância mesa/alma em perfis laminados).
- **DESCRIPTION:** Força cortante resistente de cálculo `Vrd` em 3
  trechos (plastificação / flambagem inelástica / flambagem elástica
  por cisalhamento), aplicável apenas a seções I, H e U fletidas em
  relação ao eixo perpendicular à alma. Nota: distinção crítica entre
  `h` (altura livre da alma, usada aqui e em `kv`) e `d` (altura total
  da seção, usada em `Aw`, NBR8800-SHEAR-002). Há uma pequena
  descontinuidade (~0,4% relativo) em `λ=λr`, pois `λr/λp =
  1,37/1,10 = 1,24545...` não é exatamente `1,24` — característica da
  fórmula empírica da norma, não um erro de implementação.
- **IMPLEMENTATION:**
  `estrutura_metalica.normative.nbr8800.shear.shear_resistance`,
  `estrutura_metalica.normative.nbr8800.shear.check_shear_major_axis`.
- **TEST:** `tests/normative/test_nbr8800_shear.py`.

## RULE-ID: NBR8800-SHEAR-004

- **SOURCE:** NBR 8800:2024, 5.4.3.1.1, página 57: "kv = 5,34, para
  almas sem enrijecedores transversais e para a/h > 3; kv = 5,0 +
  5/(a/h)², para todos os outros casos".
- **DESCRIPTION:** Coeficiente de flambagem por cisalhamento `kv`,
  usado em `λp`/`λr` (NBR8800-SHEAR-003). Não implementa 5.4.3.1.3
  (requisitos construtivos dos próprios enrijecedores transversais — a
  distância `a` é recebida como parâmetro, não verificada/dimensionada).
- **IMPLEMENTATION:**
  `estrutura_metalica.normative.nbr8800.shear.shear_buckling_coefficient`.
- **TEST:** `tests/normative/test_nbr8800_shear.py`.

## Fora do escopo desta fase (não implementado)

- **5.2.3/5.2.5** (páginas 39-42): coeficiente de redução `Ct` da área
  líquida — requer modelagem de furos/soldas/parafusos que
  `SteelSection` não expressa.
- **5.2.6/5.2.7** (páginas 43-44): chapas ligadas por pino; barras
  redondas com extremidades rosqueadas.
- **5.2.8.2** (página 44): esbeltez de barras COMPOSTAS tracionadas.
- **5.3.4.2/5.3.4.3** (páginas 46-48): área efetiva reduzida por
  flambagem local — requer classificação geométrica detalhada de cada
  elemento da seção que `SteelSection` (propriedades agregadas) não
  expressa.
- **5.3.5.2/5.3.5.3** (página 49): flambagem por flexo-torção em
  seções monossimétricas (`Neyz`) e equação cúbica de seções
  assimétricas — ver LIMITAÇÃO DE SEGURANÇA em NBR8800-COMP-005.
- **5.3.5.4** (páginas 50-51): comprimento destravado equivalente para
  cantoneiras simples conectadas por uma aba.
- **5.3.6** (páginas 51-52): barras compostas comprimidas.
- **5.4.2** (momento fletor resistente de cálculo — páginas 53-56,
  Anexos D/E): fase normativa futura, substancialmente mais complexa
  que 5.4.3 (classificação da seção compacta/semicompacta/esbelta,
  flambagem lateral com torção).
- **5.4.3.2 a 5.4.3.6** (páginas 58-60): força cortante resistente
  para seções tubulares/caixão, T, cantoneiras duplas, I/H/U fletidas
  em torno do eixo fraco, e tubulares circulares — mesma estrutura de
  fórmula de 5.4.3.1 (NBR8800-SHEAR-002/003), com `kv`/área efetiva de
  cisalhamento diferentes.
- **5.4.3.1.3** (página 58): requisitos construtivos para
  dimensionamento dos próprios enrijecedores transversais (ver
  NBR8800-SHEAR-004).
- **5.4.4/5.4.5** (chapas de reforço/lamelas e requisitos para seções
  soldadas).
- **5.5** (interação de esforços — páginas 60-62): fase normativa
  futura, não aberta nesta etapa.
- **Ligações** (parafusos, soldas, chapa de base): fase futura
  (PROCESSO_MODELAGEM_METALICA.md, Etapa 6 — "Dimensionamento de
  ligações").
