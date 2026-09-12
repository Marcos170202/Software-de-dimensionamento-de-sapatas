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

## RULE-ID: NBR8800-FLEX-001

- **SOURCE:** NBR 8800:2024, 5.4.1.3, página 53 (condição `MSd ≤ MRd`,
  já registrada em NBR8800-SHEAR-001) e 5.4.2.1, página 54: "O momento
  fletor resistente de cálculo, MRd, deve ser determinado de acordo
  com os Anexos D ou E, o que for aplicável [...] Devem ser
  considerados, conforme o caso, os estados-limite últimos de
  flambagem lateral com torção (FLT), flambagem local da mesa
  comprimida (FLM), flambagem local da alma (FLA) [...]".
- **DESCRIPTION:** Condição de dimensionamento ao momento fletor,
  `Msd ≤ Mrd`, onde `Mrd` é o MENOR valor entre todos os
  estados-limite aplicáveis à seção (mesmo princípio de
  `Ne=min(Nex,Ney,Nez)` em NBR8800-COMP-005 e da curva de `Vrd` em
  NBR8800-SHEAR-003). Para seções I, H com dois eixos de simetria e
  seções U não sujeitas a momento de torção, fletidas no eixo de
  maior momento de inércia (Tabela D.1, primeira linha), `Mrd =
  min(Mrd_FLT, Mrd_FLM, Mrd_FLA)` — os três estados-limite aplicáveis
  a esse caso — implementado por
  `check_flexural_resistance_major_axis` (NBR8800-FLEX-004).
- **IMPLEMENTATION:**
  `estrutura_metalica.normative.nbr8800.flexure.check_flexural_resistance_major_axis`,
  `estrutura_metalica.normative.nbr8800.flexure.check_lateral_torsional_buckling`
  (apenas FLT, isoladamente).
- **TEST:** `tests/normative/test_nbr8800_flexure.py`.

## RULE-ID: NBR8800-FLEX-002

- **SOURCE:** NBR 8800:2024, 5.4.2.3-a, página 54: "em todos os casos,
  excluindo os descritos em 5.4.2.3-b) e 5.4.2.3-c): Cb = 12,5·Mmax /
  (2,5·Mmax + 3·MA + 4·MB + 3·MC) · Rm [...] Rm [é] 1,0 para todas as
  seções duplamente simétricas [...]".
- **DESCRIPTION:** Fator de modificação para diagrama de momento
  fletor não uniforme, `Cb`, caso geral (`Rm=1,0`, único caso coberto —
  a fórmula de `Rm` para seções monossimétricas com curvatura reversa,
  `0,5+2·(Iy,m/Iy)²`, não é implementada). Não implementa 5.4.2.3-b)/c)
  (balanços) nem 5.4.2.4/5.4.2.5 (fórmulas alternativas de `Cb` para
  seções I/U com uma mesa livre para se deslocar lateralmente).
- **IMPLEMENTATION:**
  `estrutura_metalica.normative.nbr8800.flexure.moment_gradient_factor_doubly_symmetric`.
- **TEST:** `tests/normative/test_nbr8800_flexure.py`.

## RULE-ID: NBR8800-FLEX-003

- **SOURCE:** NBR 8800:2024, Anexo D, Tabela D.1 (primeira linha,
  coluna FLT) e D.2.8-a, páginas 144-145: `λr = (1,38·Cb·sqrt(Iy·J) /
  (ry·J·β1)) · sqrt(1 + sqrt(1 + 27·Cw·β1²/(Cb²·Iy)))`; `Mcr =
  (Cb·π²·E·Iy/Lb²) · sqrt((Cw/Iy)·(1 + 0,039·J·Lb²/Cw))`, onde
  `β1 = (fy-σr)·W/(E·J)`; e página 146, item e): "A tensão residual de
  compressão nas mesas, σr, deve ser considerada igual a 30% da
  resistência ao escoamento do aço utilizado."
- **DESCRIPTION:** Momento fletor crítico de flambagem elástica por
  FLT (`Mcr`), parâmetro de esbeltez correspondente ao início do
  escoamento (`λr`) e momento fletor de plastificação/momento
  correspondente ao início do escoamento (`Mpℓ=fy·Z`, `Mr=(fy-0,3·fy)·W`),
  para seções I, H com dois eixos de simetria e seções U não sujeitas
  a momento de torção, fletidas no eixo de maior momento de inércia
  (Tabela D.1, primeira linha) — `λp=1,76·sqrt(E/fy)` (D.2.1). Curva de
  3 trechos de `Mrd` conforme D.2.1 (mesma estrutura conceitual de
  NBR8800-SHEAR-003), com uma pequena descontinuidade (~0,18%
  relativo) em `λ=λr` documentada no código (mesma natureza das
  descontinuidades já registradas em NBR8800-COMP-002/NBR8800-SHEAR-003).
  Também implementa `Cw=Iy·(d-tf)²/4` para seções I (D.2.8-a), útil
  quando essa propriedade não está disponível de catálogo.
- **IMPLEMENTATION:**
  `estrutura_metalica.normative.nbr8800.flexure.lateral_torsional_buckling_moment`,
  `estrutura_metalica.normative.nbr8800.flexure.lateral_torsional_buckling_slenderness_limit`,
  `estrutura_metalica.normative.nbr8800.flexure.flexural_resistance`,
  `estrutura_metalica.normative.nbr8800.flexure.warping_constant_i_section`,
  `estrutura_metalica.normative.nbr8800.flexure.check_lateral_torsional_buckling`.
- **TEST:** `tests/normative/test_nbr8800_flexure.py`.

## RULE-ID: NBR8800-FLEX-004

- **SOURCE:** NBR 8800:2024, 5.4.2.1 (ver NBR8800-FLEX-001) e 5.4.2.2,
  página 54: "Para assegurar a validade da análise elástica, o momento
  fletor resistente de cálculo não pode ser considerado maior que
  1,50·W·fy/γa1 [...]".
- **DESCRIPTION:** Agregador que calcula o `Mrd` COMPLETO (dentro do
  escopo desta fase) de uma barra I/H/U duplamente simétrica fletida
  no eixo maior: `Mrd = min(Mrd_FLT, Mrd_FLM, Mrd_FLA)`
  (NBR8800-FLEX-001/005/006), com o limite adicional de 5.4.2.2
  aplicado ao resultado final. Valida a precondição de D.1.2 antes de
  calcular (NBR8800-FLEX-007).
- **IMPLEMENTATION:**
  `estrutura_metalica.normative.nbr8800.flexure.check_flexural_resistance_major_axis`.
- **TEST:** `tests/normative/test_nbr8800_flexure.py`.

## RULE-ID: NBR8800-FLEX-005

- **SOURCE:** NBR 8800:2024, Anexo D, Tabela D.1 (primeira linha,
  coluna FLM) e D.2.8-e/f/h, páginas 144-146: "Para perfis laminados:
  Mcr = 0,69·E/λ² · Wc, λr = 0,83·sqrt(E/(fy-σr)). Para perfis
  soldados: Mcr = 0,90·E·kc/λ² · Wc, λr = 0,95·sqrt(E/((fy-σr)/kc)),
  com kc conforme Tabela 4, nota de rodapé a" (D.2.8-f); "b/t [...] no
  caso de seções I e H [...] b é a metade da largura total" (D.2.8-h);
  e Tabela 4, nota a, página 47: "kc = 4/sqrt(h/tw), sendo
  0,35 ≤ kc ≤ 0,76".
- **DESCRIPTION:** Momento fletor crítico de flambagem local elástica
  da mesa comprimida (`Mcr`, FLM) para perfis LAMINADOS e SOLDADOS
  (fórmulas distintas), com o coeficiente `kc` da Tabela 4 (nota a)
  para perfis soldados, e o índice de esbeltez da mesa `λ=(bf/2)/tf`
  (D.2.8-h). Curva de 3 trechos de `Mrd` conforme D.2.1 (mesma
  estrutura de NBR8800-FLEX-003), com `Mr=(fy-0,3·fy)·W` (mesma
  fórmula usada em FLT, D.2.8-e) e `λp=0,38·sqrt(E/fy)`.
- **IMPLEMENTATION:**
  `estrutura_metalica.normative.nbr8800.flexure.flange_local_buckling_coefficient_welded`,
  `estrutura_metalica.normative.nbr8800.flexure.flange_local_buckling_moment_rolled`,
  `estrutura_metalica.normative.nbr8800.flexure.flange_local_buckling_moment_welded`,
  usadas em `check_flexural_resistance_major_axis`.
- **TEST:** `tests/normative/test_nbr8800_flexure.py`.

## RULE-ID: NBR8800-FLEX-006

- **SOURCE:** NBR 8800:2024, Anexo D, Tabela D.1 (primeira linha,
  coluna FLA), página 144: "Mr = fy·W [...] λ = h/tw [...]
  λp = 3,76·sqrt(E/fy) [...] λr = 5,70·sqrt(E/fy)"; e página 143,
  D.2.2: remete ao Anexo E para `λ > λr` (FLA).
- **DESCRIPTION:** Curva de 3 trechos de `Mrd` para flambagem local da
  alma (FLA), com `Mr=fy·W` (diferente de FLT/FLM, que usam
  `Mr=(fy-σr)·W`) e `λ=h/tw`. O terceiro trecho (`λ>λr`) não é
  calculável por uma fórmula fechada — remete ao Anexo E (vigas de
  alma esbelta), tratado como precondição de aplicabilidade (ver
  NBR8800-FLEX-007), não um terceiro ramo substituído.
- **IMPLEMENTATION:**
  `estrutura_metalica.normative.nbr8800.flexure.check_flexural_resistance_major_axis`
  (cálculo de FLA embutido, reaproveitando
  `estrutura_metalica.normative.nbr8800.flexure.flexural_resistance`).
- **TEST:** `tests/normative/test_nbr8800_flexure.py`.

## RULE-ID: NBR8800-FLEX-007

- **SOURCE:** NBR 8800:2024, D.1.2, página 137: "Vigas de alma não
  esbelta são aquelas constituídas por seções I, H, U [...] cujas
  almas, quando perpendiculares ao eixo de flexão, têm parâmetro de
  esbeltez λ inferior ou igual a λr (λ e λr determinados na Tabela D.1
  para o estado-limite FLA) [...]".
- **DESCRIPTION:** **LIMITAÇÃO DE SEGURANÇA**: D.1.2 restringe TODO o
  Anexo D (não apenas o estado-limite FLA) a vigas de alma NÃO
  esbelta. Se a alma for esbelta (`h/tw > λr=5,70·sqrt(E/fy)`), a
  norma exige usar o Anexo E (vigas de alma esbelta) para TODA a
  verificação de momento fletor — não apenas substituir o ramo de FLA
  por uma fórmula diferente. `check_flexural_resistance_major_axis`
  VALIDA essa precondição (levanta `ValueError` se violada) antes de
  calcular FLT/FLM/FLA, mas o **Anexo E não está implementado** — para
  vigas de alma esbelta, nenhuma função do módulo `flexure` pode ser
  usada.
- **IMPLEMENTATION:** N/A (limitação documentada + validação de
  precondição, não uma regra de cálculo) — ver
  `estrutura_metalica.normative.nbr8800.flexure.check_flexural_resistance_major_axis`.
- **TEST:** `tests/normative/test_nbr8800_flexure.py`
  (`test_rejects_slender_web`, `test_accepts_web_at_exact_slenderness_limit`).

**Nota adicional sobre o sinal de `msd`:** `FlexureCheckResult.is_ok`/
`utilization` (herdados de `CheckResult`) comparam `msd` diretamente
contra `mrd` (sempre positivo), sem valor absoluto — a condição
normativa de 5.4.1.3 é sobre a MAGNITUDE do momento (`|Msd|<=Mrd`). Um
`msd` negativo grande (momento no sentido oposto, comum em vigas
contínuas ou combinações com inversão de sinal) faria `is_ok` retornar
`True` de forma NÃO CONSERVADORA. **O chamador é responsável por
passar `abs(msd)`** — mesma responsabilidade já documentada para `Vsd`
em `ShearCheckResult` (ver docstring de `FlexureCheckResult` e teste
`test_is_ok_ignores_sign_caller_must_pass_magnitude`).

## RULE-ID: NBR8800-COMB-001

- **SOURCE:** NBR 8800:2024, 5.5.1.2, página 60: "Para a atuação
  simultânea da força axial de tração ou de compressão e de momentos
  fletores, deve ser atendida a limitação fornecida pelas seguintes
  equações de interação: a) para NSd/NRd ≥ 0,2: NSd/NRd + (8/9)·
  (Mx,Sd/Mx,Rd + My,Sd/My,Rd) ≤ 1,0; b) para NSd/NRd < 0,2: NSd/(2·NRd)
  + (Mx,Sd/Mx,Rd + My,Sd/My,Rd) ≤ 1,0."
- **DESCRIPTION:** Interação entre força axial (tração OU compressão,
  a que for aplicável) e momento fletor biaxial, para barras SEM
  torção. Duas equações conforme a razão `Nsd/Nrd` seja maior/igual ou
  menor que 0,2. `Nrd` deve ser o mesmo tipo de esforço de `Nsd`
  (`Nt,Rd` de 5.2 ou `Nc,Rd` de 5.3, conforme aplicável); `Mx,Rd`/
  `My,Rd` determinados conforme 5.4.2 (ver NBR8800-FLEX-004 para o
  eixo de maior momento de inércia — o eixo de menor momento de
  inércia não está implementado, ver docstring do módulo `flexure`).
  **ATENÇÃO**: diferente de `ShearCheckResult`/`FlexureCheckResult`,
  as funções deste módulo EXIGEM que `n_sd`/`mx_sd`/`my_sd` já sejam
  passados como magnitude (`>=0`), levantando `ValueError` caso
  contrário — decisão deliberada para não repetir a mesma armadilha de
  sinal já documentada (não corrigida) em `ShearCheckResult`/
  `FlexureCheckResult`.
- **IMPLEMENTATION:**
  `estrutura_metalica.normative.nbr8800.combined_forces.axial_bending_interaction_ratio`,
  `estrutura_metalica.normative.nbr8800.combined_forces.check_axial_and_bending_interaction`.
- **TEST:** `tests/normative/test_nbr8800_combined_forces.py`.

## RULE-ID: NBR8800-COMB-002

- **SOURCE:** NBR 8800:2024, 5.5.1.3, página 61: "Para os casos de
  força cortante atuante na direção de um dos eixos centrais de
  inércia, a verificação da barra a esse esforço deve ser feita
  conforme 5.4.3."
- **DESCRIPTION:** Quando a força cortante atua em um único eixo
  central de inércia, NÃO há equação de interação adicional — basta
  verificar `Vsd ≤ Vrd` isoladamente conforme 5.4.3
  (NBR8800-SHEAR-001 a 004). Não há nenhuma função nova a implementar
  para este caso; documentado aqui apenas para rastreabilidade
  (registrar que a cláusula foi lida e conscientemente não gerou
  código, por já estar coberta). O caso de força cortante atuando
  SIMULTANEAMENTE nos dois eixos remete a 5.5.2.3-b)/d) (seções
  tubulares combinadas com torção) — fora do escopo, ver abaixo.
- **IMPLEMENTATION:** N/A (remete diretamente a
  `estrutura_metalica.normative.nbr8800.shear.check_shear_major_axis`,
  já implementado).
- **TEST:** N/A.

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
- **5.4.2.3-b)/c), 5.4.2.4, 5.4.2.5** (páginas 54-55): `Cb` para
  balanços e para seções I/U com uma mesa livre para se deslocar
  lateralmente — apenas o caso geral duplamente simétrico (5.4.2.3-a)
  está implementado (NBR8800-FLEX-002).
- **5.4.2.6** (página 55): dimensionamento ao momento fletor com furos
  na mesa tracionada.
- **Anexo D, demais linhas da Tabela D.1** (páginas 137-146): seções
  I/H monossimétricas, seções I/H/U fletidas no eixo de menor momento
  de inércia, seções-caixão/tubulares retangulares, seções T,
  cantoneiras duplas e seções sólidas — FLT, FLM e FLA da PRIMEIRA
  linha (seções duplamente simétricas, eixo maior) já estão completos
  (NBR8800-FLEX-001/004/005/006).
- **Anexo E** (páginas 148-151): momento fletor resistente de cálculo
  de vigas de ALMA ESBELTA — substitui o Anexo D inteiramente quando a
  seção não satisfaz D.1.2 (ver NBR8800-FLEX-007).
- **Anexos F, G, H, I**: aberturas em almas de vigas, barras de seção
  variável, fadiga e vibrações em pisos, respectivamente.
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
- **5.5.2** (páginas 61-62): seções tubulares circulares e retangulares
  submetidas a momento de torção, força axial, momentos fletores e
  força cortante — inclui `Trd` para torção pura (5.5.2.1) e a equação
  de interação com torção (5.5.2.2). `SteelSection` não distingue
  seções tubulares de I/H/U com a riqueza necessária para essa
  verificação, e `Trd` nunca foi implementado em nenhuma fase anterior
  deste pacote — 5.5.1.2/5.5.1.3 (interação sem torção) já estão
  implementadas (NBR8800-COMB-001/002).
- **Ligações** (parafusos, soldas, chapa de base): fase futura
  (PROCESSO_MODELAGEM_METALICA.md, Etapa 6 — "Dimensionamento de
  ligações").
