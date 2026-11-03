# Registro de decisões — SAPATA-7

Entradas mais recentes primeiro. Nunca reescrever entradas antigas: correções entram como
entrada nova que referencia a anterior.

---

## 2026-09-29 — GATE 1 fechado: ruleset v0.1.0 (v0-geotécnico-mínimo) — a2-verificador

**Decisão.** `ruleset.yaml` v0.1.0 foi congelado com 18 regras, todas APROVADA, e 0 pendentes
dentro de `regras`. Hash sha256 `30ace52819dcb1fa7fe79242b4197e217c4a77069337f8a78487ef2f06268737`,
gravado em `ruleset.lock`. Liberado para **a3-interface** e **a4-geotecnico**. **a5-estrutural NÃO
está liberado**: não há nenhuma regra da NBR 6118/8681.

**Base auditada.** A1, commits fc1fb60 e a903ce7: `kb/clausulas.jsonl` (43), `kb/formulas.yaml`
(12) e `kb/exemplos.yaml` (2). A extração foi auditada de forma adversarial pela cascata
completa:

1. *Rastreabilidade.* 43/43 cláusulas com norma, item, página e hash. Hash recomputado confere em
   43/43. O enunciado foi localizado literalmente nas páginas declaradas em 43/43 (em 5 casos foi
   preciso remover o rodapé ou o rótulo de figura intercalado; o conteúdo está íntegro). Tabela 1,
   3.30, 3.31 e 5.6 foram conferidos visualmente na página rasterizada pelo A2.
2. *Dimensional.* Foi criado `tools/checar_dimensoes.py` (pint + sympy), que não existia no
   repositório. Passou no controle negativo: acusa área ao quadrado, variável faltando, soma
   heterogênea, número puro e unidade ausente. Achados:
   - 3.30/3.31 são dimensionalmente inconsistentes na leitura literal para sapatas (tensão ≥
     "solicitações"). O defeito é da redação da norma, não do A1. Foi resolvido vinculando S_k à
     tensão de trabalho (3.47).
   - A forma simbólica do A1 para 7.7.1, 7.7.2 e 7.7.3 compara comprimento com número puro.
     Foi REJEITADA e formalizada com constantes com unidade (o A1 tinha delegado a forma simbólica
     de requisitos textuais ao A2).
3. *Consistência cruzada.* Namespaces obrigatórios (RT-02). Separação de método em tempo de
   execução, com etiqueta `natureza` e lista fechada de comparações permitidas (RT-01).
   Majoração por vento virou guarda de recusa, não constante.
4. *Sanity.* SC-01 (B = 2,0 m, D = 1,5 m, N_SPT = 15 via σ_r de Cintra): σ_adm = 296,7 kPa, dentro
   de [50, 600]. Consistência da Tabela 1: γm·γf = 3,01 ≈ FS_g = 3,00. SC-02 reproduz a área de
   Bastos (5,2885 m²). SC-03 confirma a recusa de uma sapata 0,60 × 0,60 m com D = 1,5 m como não
   rasa.
5. *Fila humana.* `kb/pendencias.md`, P-01 a P-07. Nenhuma pendência bloqueia as regras
   congeladas.

**Decisões sobre os pontos levantados pelo A1:**

- *Capacidade de carga (7.3.2/7.3.3).* A ausência de fórmula na 6122 **não bloqueia o GATE 1
  inteiro**. Congelou-se o subconjunto em que a tensão de referência (σ_adm, σ_Rd ou σ_r,k com o
  método declarado) é **entrada** do engenheiro. Capacidade de carga, semiempíricos, prova de
  carga e recalques ficam BLOQUEADOS (LAC-01 a LAC-04) até decisão humana sobre bibliografia como
  fonte (P-01).
- *5.6, peso próprio.* Lido no original. Adotada a envoltória P_pp,k = max(P_pp,real,k ; 0,05·G_k),
  conforme sob as duas leituras. A base é a carga **permanente**, não a total (o Kmaj = 1,1 de
  Bastos é hipótese do autor). O solo sobre a sapata é entrada obrigatória sem padrão (P-03).
  Pedida contra-assinatura (P-04, não bloqueante).
- *σ = N/(B·L), 7.6.1.* APROVADA como `DERIVADA_DO_TEXTO`: é consequência matemática direta de
  "admitidas uniformemente distribuídas", sem parâmetro novo. O memorial não pode apresentá-la
  como texto da norma.
- *Mojibake (495 linhas).* Auditado de forma independente. Uma amostra aleatória de 40, mais todas
  as 112 suspeitas das páginas 17–37, são português limpo. Apenas 8 linhas têm caractere fora do
  conjunto esperado ('Ø' de diâmetro e 'd´água', tipografia da própria fonte). O falso positivo
  vem da heurística de palavras-marcador do diagnóstico. A decisão do A1 foi mantida.
- *Excentricidade (7.6.2).* **Não basta omitir.** Foi criada uma guarda APROVADA que recusa o
  cálculo quando M ≠ 0, H ≠ 0 (a força horizontal gera momento na base) ou o pilar está fora do
  centro. Sem ela, o v0 aplicaria a distribuição uniforme a um caso excêntrico, contra a
  segurança.
- *NBR 8681 não extraída.* **Não bloqueia o v0.** Pela 5.1, os esforços chegam combinados do
  projetista estrutural. Vale γf = 1,4 da nota c da Tabela 1 só quando o esforço está disponível
  apenas em valor característico. É proibido assumir um divisor padrão para reduzir N_d a N_k.
  Bloqueia `combinacoes.py` (A5).

**Achado adversarial adicional.** σ_r,k/FS_g sozinho não é a "tensão admissível" da 3.45, que
exige ELU e ELS. Foi criada a regra 7.1/7.4. No método de cálculo, o ELS é uma verificação
separada em valores característicos (σ_k ≤ σ_ELS), nunca min(σ_Rd, σ_ELS), porque isso misturaria
bases.

**Devolvido ao A1 (não bloqueante para o v0):**
(a) extrair 5.3 (subpressão) e 6.1.1 (região representativa);
(b) corrigir a forma simbólica de 7.7.1, 7.7.2 e 7.7.3 (unidades na expressão);
(c) retirar de F-NBR6122-3.30 o `unidades_nota` que afirma que P_adm, R_k e S_k "têm a mesma
dimensão ... decorre das definições literais". Isso é falso (S_k é "solicitações") e é inferência
não marcada como INTERPRETACAO;
(d) padronizar o vocabulário de status (EXTRAIDO × EXTRAIDA).

**Consequência para o pipeline.** A4 pode implementar só `geometria.py` (modo verificação:
B e L de entrada), `restricoes.py` (7.7.1–7.7.3) e as guardas, sem `capacidade.py`,
`semiempirico.py`, `prova_carga.py`, `recalques.py` ou `vento.py`. **Qualquer alteração futura
em `ruleset.yaml`, incluindo a próxima ampliação de escopo, invalida as aprovações de A6 e A7.**
