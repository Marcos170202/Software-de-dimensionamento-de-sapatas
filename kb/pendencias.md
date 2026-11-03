# Pendências para decisão humana (fila do a2-verificador)

Formato: pergunta objetiva · trecho literal da fonte · leitura proposta pelo A2 · impacto se
a leitura estiver errada · efeito sobre o GATE 1.

Nenhuma pendência abaixo bloqueia as `regras` congeladas em `ruleset.yaml` v0.1.0: todas
tratam de itens deixados FORA do escopo v0 (`fora_do_escopo_v0`) ou pedem apenas
contra-assinatura de uma decisão que já é conforme sob qualquer leitura.

Para resolver: registre a decisão em `docs/decisoes.md` (nome, data, texto da decisão) e
acione o a2-verificador. Qualquer alteração decorrente no `ruleset.yaml` invalida as aprovações
de A6 e A7.

---

## P-01 — Bibliografia como fonte para capacidade de carga e correlações SPT  [ABERTA · bloqueia LAC-01/LAC-02, não o v0]

**Pergunta.** O projeto aceita um livro (ex.: Cintra, Aoki e Albiero, 2011, *Fundações diretas*)
como fonte das equações de capacidade de carga (Terzaghi/Vesic, fatores N e de forma) e das
correlações SPT (ex.: c = 10·N_SPT kPa; φ = 28° + 0,4·N_SPT), já que a NBR 6122:2022 não traz
nenhuma dessas expressões?

**Trecho literal (NBR 6122:2022, 7.3.2, p. 22):** "Podem ser empregados métodos analíticos
(teorias de capacidade de carga) nos domínios de validade de sua aplicação, desde que contemplem
todas as particularidades do projeto, inclusive a natureza do carregamento (drenado ou não
drenado)."
**(7.3.3, p. 22):** "São métodos que relacionam resultados de ensaios (tais como o SPT, CPT etc.)
com tensões admissíveis ou tensões resistentes de cálculo. Devem ser observados os domínios de
validade de suas aplicações, bem como as dispersões dos dados e as limitações regionais
associadas a cada um dos métodos."

**Leitura proposta.** A norma autoriza, mas não fornece, os métodos. Um livro pode ser fonte de
regra desde que: (a) cada regra carregue `fonte_tipo: bibliografia` distinta de `norma`;
(b) o domínio de validade declarado pelo autor vire guarda; (c) o software rode todos os métodos
aplicáveis e mostre a dispersão, sem escolher (regra de ouro do A4); (d) as correlações regionais
fiquem marcadas como tal. Enquanto isso não for decidido, o v0 recebe a tensão de referência
como entrada.

**Impacto se errado.** Se o livro for aceito sem essas travas, o software passa a produzir
σ_adm a partir de N_SPT com aparência de resultado normativo, o que é o modo de falha mais
perigoso descrito no CLAUDE.md. Se for recusado, `capacidade.py` e `semiempirico.py` nunca
existem e o software fica restrito a verificar uma tensão fornecida.

---

## P-02 — Critério de proporção B×L e arredondamento  [ABERTA · bloqueia LAC-11, não o v0]

**Pergunta.** O software pode *propor* B e L (balanços iguais, múltiplos de 5 cm), ou deve
apenas *verificar* B e L fornecidos pelo engenheiro?

**Trecho literal (NBR 6122:2022, 7.6.1, p. 23):** "A área da fundação solicitada por cargas
centradas deve ser tal que as tensões transmitidas ao terreno, admitidas uniformemente
distribuídas, satisfaçam aos requisitos de segurança conforme Seção 6." A norma não trata de
proporção. O critério vem de Bastos (2023), Eq. 1.5 (A − B = a_p − b_p) e Eq. 1.9.

**Leitura proposta.** A proporção não afeta a segurança geotécnica (qualquer B×L que passe
nas verificações é conforme), então pode entrar como `tipo: sugestao_nao_normativa`, rotulada
assim no memorial, com B e L sempre editáveis. O v0 congelado opera só em modo verificação.

**Impacto se errado.** Baixo para a segurança geotécnica. Alto para a estrutural: balanços
iguais governam a flexão e a punção (A5). Uma sugestão apresentada como "resultado" induz o
usuário a não revisar.

---

## P-03 — Peso do solo sobre a sapata e tensão bruta × líquida  [ABERTA · não bloqueia]

**Pergunta.** A decisão do A2 de exigir `P_solo_k` como entrada obrigatória, sem valor padrão
(pode ser 0, mas declarado), é aceitável? Ou o projeto quer uma regra fixa?

**Trecho literal (NBR 6122:2022, 5.6, p. 15):** "Deve ser considerado o peso próprio de blocos de
coroamento ou sapatas, ou no mínimo 5 % da carga vertical permanente." (não menciona o solo)
**(3.45, p. 8):** "máxima tensão que, aplicada ao terreno pela fundação rasa ou pela base de
tubulão, atende, com fatores de segurança predeterminados, aos estados limites últimos (ruptura)
e de serviço (recalques, vibrações etc.)"

**Leitura proposta.** A norma é silenciosa. Incluir ou não o reaterro depende de como σ_adm foi
obtida (bruta, com a parcela q·N_q de Terzaghi, ou líquida). Só o engenheiro sabe. Por isso a
entrada é obrigatória e registrada no memorial, e o software não escolhe.

**Impacto se errado.** Com um padrão 0 silencioso, subestima-se a tensão atuante quando σ_adm é
bruta: da ordem de γ·D ≈ 18 × 1,5 ≈ 27 kPa, cerca de 10 % de uma σ_adm de 250 kPa. Esse erro fica
contra a segurança e não aparece em nenhum teste.

---

## P-04 — Contra-assinatura da leitura do item 5.6  [ABERTA · não bloqueia]

**Pergunta.** O engenheiro responsável concorda com a envoltória
P_pp,k = max(P_pp,real,k ; 0,05·G_k)?

**Trecho literal (NBR 6122:2022, 5.6, p. 15, conferido na página rasterizada, PDF p. 27):**
"Deve ser considerado o peso próprio de blocos de coroamento ou sapatas, ou no mínimo 5 % da
carga vertical permanente."

**Leitura proposta.** Gramaticalmente o texto dá alternativas: o peso real OU, no mínimo, 5 % de
G_k. Lido ao pé da letra, permitiria adotar 5 % mesmo com peso real maior, o que é inseguro. A
envoltória max() é conforme sob as duas leituras apontadas pelo A1 e nunca é menos conservadora.
Por isso foi APROVADA sem depender desta resposta. A base é G_k (permanente), não a carga total.
Se G_k for desconhecido, usa-se N_k (conservador).

**Impacto se errado.** Se a intenção da norma for (i) pura, o v0 é levemente conservador quando
o peso real é menor que 5 % de G_k (sapatas muito carregadas). Nenhum impacto contra a segurança.

---

## P-05 — FS_g ≥ 1,6 com majoração por vento: nominal ou efetivo?  [ABERTA · bloqueia LAC-07, não o v0]

**Pergunta.** Em 6.3.2, o "fator de segurança global não pode ser inferior a 1,6" refere-se ao
FS_g nominal da Tabela 1 ou ao FS efetivo após a majoração (FS_g/(1 + majoração))?

**Trecho literal (NBR 6122:2022, 6.3.2, p. 21):** "os valores de tensão admissível de sapatas e
tubulões e as cargas admissíveis em estacas podem ser majorados em até 15 %. Quando esta
majoração for utilizada, o fator de segurança global não pode ser inferior a 1,6."

**Leitura proposta.** Efetivo: FS_g/(1 + m) ≥ 1,6. É o único modo de a cláusula ter efeito, porque
os FS_g nominais da Tabela 1 (2,00 e 3,00) já são maiores que 1,6.

**Impacto se errado.** Com provas de carga (FS_g = 2,00) e majoração de 30 %, o FS efetivo é
2,00/1,30 = 1,54 < 1,6. Na leitura nominal o software aceitaria esse caso; na efetiva, recusaria.

---

## P-06 — "Solos pouco resistentes" × "solos resistentes" (7.7.4)  [ABERTA · bloqueia LAC-08, não o v0]

**Pergunta.** Qual critério separa as duas classes para escolher α ≥ 60° ou α ≥ 45°?

**Trecho literal (NBR 6122:2022, 7.7.4, p. 24):** "a) solos pouco resistentes: α ≥ 60°;
b) solos resistentes: α ≥ 45°; e c) rochas: α ≥ 30°."

**Leitura proposta.** A norma não define o critério. O software deve pedir a classe ao engenheiro
e nunca inferi-la de N_SPT.

**Impacto se errado.** Um α menor que o exigido compromete a fundação vizinha mais alta.

---

## P-07 — Redução da profundidade mínima em divisa sem valor normativo (7.7.2)  [ABERTA · não bloqueia]

**Pergunta.** Está correto o v0 devolver INCONCLUSIVO, exigindo justificativa escrita do
engenheiro, quando D < 1,5 m em divisa numa obra com a maioria das sapatas menor que 1,0 m?

**Trecho literal (NBR 6122:2022, 7.7.2, p. 24):** "Em casos de obras cujas sapatas ou blocos
tenham, em sua maioria, dimensões inferiores a 1,0 m, essa profundidade mínima pode ser
reduzida."

**Leitura proposta.** Sim. A norma permite reduzir mas não fixa o valor, e o software não pode
inventar um piso.

**Impacto se errado.** Se o projeto quiser um piso fixo (ex.: 1,0 m), ele precisa vir de decisão
humana registrada, nunca do software.
