# Fila humana — decisões que a2-verificador não pode tomar sozinho

Regras extraídas mas com `status: PENDENTE_HUMANO` em `ruleset.yaml`. Não
implementar em `calc_core/` até virarem `APROVADA`.

---

# RODADA 2026-08-27 (ruleset versão 3) — NBR 6118 §22.6

## NBR6118-22.6.2.2a-sapata-alongada — PRIORIDADE ALTA (lado inseguro)

**Trecho literal** (NBR 6118:2023, 22.6.2.2-a, p. 192, lido visualmente a
200 dpi pelo a2-verificador, não pelo texto extraído):

> "trabalho à flexão nas duas direções, admitindo-se que, para cada uma delas,
> a tração na flexão seja uniformemente distribuída na largura correspondente
> da sapata. Essa hipótese não se aplica à compressão na flexão, que se
> concentra mais na região do pilar que se apoia na sapata **e não se aplica
> também ao caso de sapatas muito alongadas em relação à forma do pilar**"

**Pergunta objetiva:**
1. Qual índice e qual limiar caracterizam "sapata muito alongada em relação à
   forma do pilar", para efeito de disparar um aviso?
2. Disparado o gatilho, o software deve apenas AVISAR (sem alterar número
   algum) ou mudar o modelo (largura colaborante, faixas, ou a grelha/MEF que
   já existem no pacote)?
3. A "concentração de flexão junto ao pilar" de 22.6.2.3-a) (sapata FLEXÍVEL)
   deve ser tratada pelo mesmo mecanismo?

**Leitura proposta:** o sujeito de "não se aplica também" é *Essa hipótese* —
a de tração uniformemente distribuída na largura. Em sapata muito alongada a
tração concentra-se na faixa junto ao pilar. Portanto a exceção **não** libera
redução de armadura em direção nenhuma; ela exige tratamento mais refinado.
"Em relação à forma do pilar" indica que o alongamento é relativo ao pilar
(balanços desiguais), não a razão a/b absoluta.

**Impacto se a leitura estiver errada: DO LADO INSEGURO.** Hoje
`momentos.py:207` invoca explicitamente a hipótese de 22.6.2.2-a) e
`22.6.4.1.1` manda distribuir a armadura na largura toda — sem que nada no
código detecte a condição de alongamento. Verificado por execução: com
a = 6,00 m, b = 0,80 m (balanços 2,90 m × 0,30 m, razão 9,7) o motor **não
emite alerta nenhum**. Se a concentração for relevante, a faixa sob o pilar
fica subarmada e o memorial não registra a ressalva.

**Sugestão de gatilho — NÃO NORMATIVA, NÃO APROVADA:** balanços
`c_a = (a-a_p)/2`, `c_b = (b-b_p)/2`, índice `λ = max(c_a,c_b)/min(c_a,c_b)`;
`λ ≥ 2` aviso, `λ ≥ 3` aviso forte. Os números 2 e 3 são palpite de triagem
sem respaldo em texto normativo. Só podem ir para o código depois de decisão
de engenharia registrada, rotulados como decisão de engenharia (jamais
`[rule: ]` de norma) e com o limiar como parâmetro visível e sobrescrivível.

## NBR6118-22.6.4.1.3-remissao-lajes

**Trecho literal** (p. 193, item integral): "Devem ser atendidos os requisitos
relativos às lajes e punção (ver Seções 19 e 20)."

**Pergunta objetiva:** aplicar a sapatas FLEXÍVEIS os mínimos de laje
(Tabela 19.1: `As/s ≥ 0,9 cm²/m` e `ρ_s ≥ 0,5 ρ_min` para a secundária;
20.1: secundária ≥ 20 % da principal, espaçamento ≤ 33 cm, φ ≤ h/8)?

**Obstáculo conhecido:** 20.1 e a Tabela 19.1 pressupõem laje já classificada
como "armada em uma direção" ou "nas duas direções", e a NBR 6118:2023 **não
define esse critério em lugar nenhum** (o ly/lx ≤ 2 é convenção de
bibliografia). Como 22.6.2.2-a/22.6.2.3-a já obrigam as duas direções, a
leitura coerente é que sapata nunca cai na linha "armadas em uma direção" —
mas isso precisa de confirmação humana.

**Impacto:** se devidos e não aplicados, sapata flexível pouco solicitada pode
sair abaixo do mínimo (inseguro em fissuração/ductilidade). Se aplicados a
sapata RÍGIDA, consumo de aço sobe sem amparo e o memorial cita item que não
alcança sapata rígida.

## Defeitos de CITAÇÃO no código — para A5 (não são erro de cálculo)

Os números conferem; o que está errado é o item normativo citado — o que
viola CLAUDE.md regra 3, porque essas strings alimentam o memorial e a tela.

1. **`22.6.3` usado como se fosse "sapata flexível" — 18 ocorrências.**
   `22.6.3` é *Modelo de cálculo*. O item correto para o comportamento/punção
   de sapata flexível é **22.6.2.3-b)**; para o detalhamento, **22.6.4.1.3**.
   Arquivos: `sapata.py` (4), `visual2d.py` (3), `visual3d_momentos.py` (3),
   `visual3d_tensoes.py` (3), `relatorio.py` (2), `rigidez.py` (2),
   `ui/completo/visualizacao.py` (1). Várias são texto exibido ao usuário
   (ex.: `rigidez.py:142`, `relatorio.py:84`).
2. **`22.6.4.1` citado como se autorizasse bielas e tirantes**
   (`bielas.py:6`). `22.6.4.1` é um cabeçalho sem texto próprio
   (*Detalhamento — Sapatas rígidas*). A permissão está no último parágrafo
   de **22.6.3**. Ou seja, 1 e 2 estão exatamente trocados entre si.
3. **`22.6.4.1` citado como definindo a "seção de referência" na face do
   pilar** (`momentos.py:201,205,359`; `sapata.py:595`; `grelha.py:299`).
   Conferido visualmente: 22.6.4.1 não tem texto, e 22.6.4.1.1 prescreve
   distribuir a armadura na largura, de face a face, com gancho nas duas
   extremidades — **não define seção de referência**. A seção de referência na
   face do pilar é prática de engenharia; deve ser rotulada como tal.
4. **`rigidez.py:56` cita "NBR 6122:2019"** — edição inexistente no acervo
   (é **2022**).

## NBR6122-7.6.2-area-comprimida (carga excêntrica) — ATUALIZADO

**Não está mais "não implementado".** `calc_core/sapata_isolada/sapata.py`
(portado do pacote do usuário em 2026-08-26) implementa diagrama
trapezoidal/triangular/área efetiva de Meyerhof para carga excêntrica —
mas isso ainda é `PENDENTE_HUMANO` no ruleset porque NINGUÉM conferiu essas
fórmulas contra o texto literal da 7.6.2 nesta rodada (a auditoria desta
sessão cobriu só materiais/ancoragem/punção/cisalhamento da NBR 6118).

**Achado concreto que precisa de decisão:** a norma exige área comprimida
`>= 2/3 da área total` para solicitações CARACTERÍSTICAS ou `>= 50%` para
solicitações de CÁLCULO — dois limiares, um por método. O código portado tem
um único parâmetro `area_comprimida_minima` (default 2/3) aplicado somente às
combinações ELS (`self.combs_els`); as combinações ELU nunca são checadas
contra o limiar de 50%. Ou seja, a verificação de área comprimida sob carga
de cálculo (ELU) está ausente, não só "usando o valor errado".

**Pergunta objetiva:** confirmar se a intenção é aplicar 2/3 às combinações
ELS-rara (parece ser o caso, dado que a verificação de tensão do solo já é
feita em ELS) e adicionar uma checagem de 50% às combinações ELU, ou se o
código deveria unificar num único critério mais conservador.

**Impacto se não for corrigido:** uma sapata poderia passar no
dimensionamento em planta (ELS) e nunca ser checada quanto à área comprimida
sob a combinação de cálculo mais desfavorável — undertesting silencioso.

## NBR6122-7.6.3-deslizamento (carga horizontal)

**Pergunta objetiva:** o escopo mínimo atual não coleta ângulo de atrito
solo-fundação nem dados de empuxo passivo. Vale a pena estender a entrada
agora ou esperar o primeiro caso de uso real com carga horizontal relevante?

**Trecho literal:** ver `kb/clausulas.jsonl`, item `7.6.3`.

**Leitura proposta:** esperar. Carga horizontal significativa é mais comum em
pilares de borda/canto com vento — cenário que também precisa de A5
(estrutural) e ainda não foi priorizado.

## NBR6122-6.2.1.1.1-fatores-seguranca-tabela1

**Pergunta objetiva:** os valores de γm e FSg extraídos do texto corrido da
Tabela 1 (semiempíricos ≥2,15 / ≥3,00; analíticos 2,15 / 3,00; com prova de
carga 1,40 / 2,00) batem com a tabela renderizada (células mescladas, não
conferidas visualmente)?

**Trecho literal:** ver `kb/clausulas.jsonl`, item `6.2.1.1.1`.

**Leitura proposta:** conferir a tabela na página 28 do PDF visualmente antes
de aprovar. Só é necessário quando o software passar a deduzir σ_adm de
SPT/CPT — o escopo atual recebe σ_adm como entrada direta do engenheiro, então
isto não bloqueia o GATE 1 do escopo mínimo.

## NBR6118-9.4.2.5-lb-necessario — α parcial (2 de 4 casos)

**Trecho literal:** ver `kb/clausulas.jsonl`, item `9.4.2.5` (lido por visão,
p. 37-38).

**O que falta:** a norma dá α=1,0 (sem gancho), 0,7 (com gancho e cobrimento
≥3φ), 0,7 (barra transversal soldada) e 0,5 (os dois juntos). O código só
implementa os dois primeiros (`sapata_isolada/sapata.py::_ancoragem`,
parâmetro booleano `com_gancho`). Os dois casos com barra transversal soldada
não têm como ser selecionados.

**Impacto:** nenhum — ausência é conservadora (nunca usa um α menor que o
correto), só limita a economia de armadura em detalhamentos que usem barra
transversal soldada como reforço de ancoragem. Baixa prioridade.

## Módulos portados ainda não auditados (escopo amplo)

Ver `ruleset.yaml`, seção `escopo_amplo_em_conferencia`, para a lista
completa (geotecnia/Boussinesq, bielas de Blévot, rigidez/grelha de Winkler,
recalques, MEF do solo, exportação PDF/visualização). Nenhum desses módulos
é `APROVADA` — todos passaram no teste de sanidade do próprio pacote e num
caso de ponta a ponta, mas não tiveram fórmula alguma conferida contra o
texto da norma nesta rodada.

---

# RODADA 2026-08-27 (ruleset versão 4) — NBR 6122 §6.2.1 / citações de edição

Origem: dois achados do a6 encaminhados ao a2 para confirmação normativa.
O a5 está PROIBIDO de tocar em qualquer um destes pontos até ler esta seção.

## Questão 1 — item de deslizamento/tombamento: a6 está CERTO na estrutura, e o problema é maior do que ele viu

**Releitura feita pelo a2**, não herdada do a6: texto extraído com pymupdf
(`NBR 06122 - 2022 - Projeto e execução de fundações.pdf`,
sha256 `65fb1d5c60b81066010c08a2e86fdedb3491d0603a7c98a46917d52f29571f53`)
E conferida contra o render a 140 dpi da mesma página. As duas leituras
coincidem caractere a caractere. Páginas impressas 17-18 = PDF p. 29-30
(offset de 12).

**Estrutura real da NBR 6122:2022, seção 6.2.1:**

| item | título literal | PDF p. |
|---|---|---|
| 6.2.1.1 | Segurança de fundação rasa (direta ou superficial) | 29 |
| 6.2.1.1.1 | Segurança na compressão | 29 |
| 6.2.1.1.2 | Coeficientes de ponderação para verificação de tração, deslizamento e tombamento | 29 |
| 6.2.1.1.3 | Fator de segurança global para verificação de flutuação | 30 |
| 6.2.1.2 | **Segurança de fundações profundas** | 30 |
| 6.2.1.2.1 | Resistência determinada por método semiempírico | 30 |
| 6.2.1.2.2 | Resistência determinada por provas de carga estáticas | 31 |

**Respostas às três perguntas:**

1. **Sim** — 6.2.1.2 é "Segurança de fundações profundas". Seu conteúdo é
   inteiramente sobre estacas (Rk, ξ1..ξ4, provas de carga). Citá-lo para
   deslizamento/tombamento de sapata é erro puro. O a6 está certo.
2. **Sim** — 6.2.1.1.2 existe e é o item de fundação rasa para tração,
   deslizamento e tombamento. O a6 está certo.
3. **NÃO.** Aqui o a6 parou cedo. O item 6.2.1.1.2 **não prescreve fator de
   segurança global nenhum.**

**Trecho literal integral de 6.2.1.1.2** (p. impressa 17-18):

> "Coeficientes de ponderação para verificação de tração, deslizamento e
> tombamento — Devem ser adotados os seguintes coeficientes de ponderação:
> γm = 1,2 (minoração) para a parcela favorável do peso; γm = 1,4 (minoração)
> para a resistência do solo; γf = 1,4 (majoração) para o esforço atuante, se
> disponível apenas o seu valor característico; se já fornecido o valor de
> cálculo, nenhum coeficiente de ponderação deve ser aplicado a ele."

É só isso. Não há FS global. Varredura das 120 páginas do PDF por
`deslizamento|tombamento` devolve **4 ocorrências e nenhuma outra**:
6.2.1.1 alínea c) (lista de mecanismos de ELU), o título de 6.2.1.1.2, o corpo
de 6.2.1.1.2, e 7.5.1 (chumbadores em rocha inclinada). Em toda a NBR 6122:2022
**não existe fator de segurança global para deslizamento ou tombamento**.
O único FS global de fundação rasa fora da compressão é 1,1, e é para
**flutuação** (6.2.1.1.3) — item diferente, fenômeno diferente.

### Consequência: a correção "6.2.1.2 → 6.2.1.1.2" NÃO pode ser aplicada sozinha

Trocar o número de item e deixar o resto como está transformaria um erro
visível (item errado) num erro invisível (item certo dando respaldo normativo
aparente a um critério que a norma não contém). Isso é PIOR. O a5 fica
bloqueado nos cinco pontos que citam 6.2.1.2 até haver decisão humana.

### Achado de segurança — LADO INSEGURO, prioridade ALTA

`sapata.py:732-750 (_verificar_estabilidade)` itera sobre `self.combs_els`
(valores **característicos**) e compara contra FS global
(`geotecnia.py:215-216`: `fs_deslizamento = 1.5`, `fs_tombamento = 1.5`).
Isso é a rota de **valores admissíveis** aplicada a uma verificação para a
qual a NBR 6122:2022 só oferece a rota de **valores de cálculo**. É a colisão
de método de segurança descrita em `.claude/agents/a2-verificador.md` §3 —
o erro clássico do setor.

Convertendo 6.2.1.1.2 para FS global equivalente, para comparar maçã com maçã:

| verificação | exigência implícita da norma | código | déficit |
|---|---|---|---|
| deslizamento (leitura estrita: 1,2 · 1,4 · 1,4) | **2,35** | 1,5 | −36 % |
| deslizamento (leitura branda: 1,4 · 1,4) | **1,96** | 1,5 | −23 % |
| tombamento (1,2 · 1,4) | **1,68** | 1,5 | −11 % |

Em **todas** as leituras possíveis o código é menos conservador que a norma.
Checagem dimensional feita com `pint`: as duas razões fecham adimensionais
(`kN/kN` e `kN·m/kN·m`) — a análise dimensional **não** acusa este defeito,
porque ele é de método e de valor, não de transcrição. Registrado aqui
justamente por isso.

Defeito irmão, mesma família, em `acoes.py:138-140`: a combinação para
tombamento/deslizamento minora o permanente estabilizante com `gamma_g = 1,0`.
A norma manda `γm = 1,2` (minoração) sobre a parcela favorável do peso.
`1,0` não é minoração nenhuma.

**Pergunta objetiva para o engenheiro (2 itens, ambos bloqueantes):**

1. "γm = 1,4 (minoração) para a resistência do solo" incide sobre tanδ e c'
   **além** da minoração de 1,2 já aplicada ao peso favorável (FS equivalente
   2,35), ou as duas são alternativas conforme a parcela (FS equivalente
   1,96)? Muda o resultado em 20 %.
2. O software migra a verificação de estabilidade para o método de valores de
   cálculo (combinações ELU + coeficientes parciais de 6.2.1.1.2), ou mantém
   uma rota de valores admissíveis com FS fixado pelo projetista? Se mantiver,
   o FS **não pode** ostentar `[rule:]` de NBR 6122 — tem de ser rotulado como
   decisão de engenharia, porque a norma não o fornece.

**Impacto se a leitura estiver errada:** se eu estiver errado e existir em
algum lugar um FS global de 1,5 para estas verificações, o custo é ter
enrijecido o critério sem necessidade (sapatas maiores, obra mais cara).
Se eu estiver certo e nada for feito, o motor aprova sapatas com folga ao
deslizamento até 36 % abaixo da exigida pela norma, e o memorial cita um item
de fundação profunda como respaldo. O segundo risco é assimetricamente pior.

**Registrado no ruleset:** regra nova
`NBR6122-6.2.1.1.2-tracao-deslizamento-tombamento`, `metodo: calculo`,
`status: PENDENTE_HUMANO`.

---

### ATUALIZAÇÃO 2026-08-27 (ruleset versão 5) — a pergunta acima cai de duas para uma

Entrou no dossiê uma **fonte secundária não normativa**: BASTOS, P.S.,
*Sapatas de Fundação*, UNESP Bauru/SP, Out/2023, 119 p. (`Sapatas.pdf`).
Extração do a1 em `kb/clausulas.jsonl` (8 registros `BASTOS-*`) e
`kb/formulas.yaml` (3 fórmulas). Auditada e **aceita sem correção de
conteúdo** pelo a2, com releitura visual própria das equações a 500 dpi e
repetição da busca negativa nas 119 páginas.

**Trecho literal da nova fonte** (p. impressa 74, PDF 78; e p. 75, PDF 79):

> "O peso do solo sobre a sapata pode também ser considerado no M<sub>estab</sub>.
> O coeficiente de segurança deve ser ≥ 1,5:
> γ<sub>tomb</sub> = M<sub>estab</sub> / M<sub>tomb</sub> ≥ 1,5   (1.72)"
>
> "γ<sub>esc</sub> = F<sub>estab</sub> / F<sub>H</sub> ≥ 1,5   (1.75)"

**Leitura proposta pelo a2:** a apostila **não resolve** a pendência; ela
melhora a documentação e permite estreitar a pergunta. Ela prova que FS = 1,5
é prática de ensino e de mercado — e, pela busca negativa, prova também que
esse valor **não tem âncora normativa**: a string "6.2.1" não ocorre uma única
vez em todo o documento, e a expressão "coeficiente de segurança" ocorre uma
única vez, exatamente no parágrafo do 1,5, sem remissão a norma. Uma fonte que
cita a NBR 6122 com precisão em dezesseis itens e **não a cita** justamente ao
dar o 1,5 é evidência a favor do rótulo "prática consagrada" e evidência
adicional contra o rótulo "requisito normativo".

**Correção da própria leitura anterior do a2 (v4), feita nesta rodada.** A v4
registrou que "§7.1 permite as duas rotas". Isso é largo demais. Texto literal
de §7.1 (PDF p. 33): *"A grandeza fundamental para o projeto de fundações
rasas é a **tensão** admissível, se o projeto for feito considerando fator de
segurança global e valores característicos, ou a **tensão** resistente de
cálculo, quando for feito considerando coeficientes de ponderação e valores de
cálculo."* A escolha de rota é sobre a **tensão** — a verificação de
compressão. Não é licença geral de método. A norma distribui a rota item a
item, e a distribuição é deliberada:

| item | assunto | rotas oferecidas |
|---|---|---|
| 6.2.1.1.1 | Segurança na **compressão** | as duas, com Tabela 1 |
| 6.2.1.1.2 | tração, **deslizamento**, **tombamento** | **só** coeficientes parciais |
| 6.2.1.1.3 | flutuação | **só** FS global (1,1) |

Que 6.2.1.1.3 ofereça exclusivamente FS global mostra que a ABNT sabe
prescrever essa rota quando quer. A omissão em 6.2.1.1.2 não é lacuna de
redação. **Portanto "escolher a rota de valores admissíveis" não é opção livre
nesta verificação** — e o rótulo "prática consagrada" descreve com honestidade
o que o software faria: um afastamento documentado do único item aplicável,
não um enquadramento nele.

**O que o a2 decidiu sozinho** (documental, sem efeito sobre número algum):

1. FS = 1,5 fica rotulado **PRÁTICA CONSAGRADA, SEM RESPALDO NORMATIVO**, com
   a apostila como evidência de prática. Não vira `[rule:]` de norma nunca.
2. A eq. 1.74 da apostila (atrito + coesão) fica **REJEITADA** por
   inconsistência dimensional: `pint` acusa `DimensionalityError` ao somar
   `(N+P)·tg(2/3φ)` [kN] com `A·(2/3 c)` [m·kPa = kN/m], porque a própria
   fonte define `A` como "dimensão da base", um comprimento. Sem efeito
   prático — o código usa `coesao * a * b`, coesão × **área**, que é a forma
   correta —, mas fica marcada para ninguém a citar depois como auditada.
3. Proibido grafar a constante como **γ** em código, tela ou memorial. A
   apostila usa γ para FS global e a NBR usa γm/γf para coeficientes parciais;
   é a colisão de método de segurança já na notação. Usar `FSg_deslizamento` /
   `FSg_tombamento`.

**O que continua sendo do engenheiro — pergunta objetiva única:**

> O software mantém a rota de valores admissíveis para deslizamento e
> tombamento, com FS = 1,5 rotulado como prática consagrada não normativa, ou
> migra para o método de valores de cálculo de §6.2.1.1.2 (combinações ELU +
> coeficientes parciais γm = 1,2 / γm = 1,4 / γf = 1,4)?

A pergunta anterior sobre os γm se somarem (2,35) ou serem alternativos (1,96)
fica **condicional e dormente**: só volta a ser bloqueante se a resposta for
"migrar". Se a resposta for "manter", ela não tem efeito sobre o código.

**Impacto se a leitura estiver errada.** Se o a2 estiver errado ao restringir
§7.1 à tensão, e a rota de valores admissíveis for de fato franqueada a
deslizamento e tombamento, então o par 1,5/1,5 é legítimo e o custo do rótulo
é apenas reputacional: um memorial que se declara mais afastado da norma do
que realmente está — projetista lê o aviso, discute, e no limite dimensiona
sapata maior que o necessário. Se o a2 estiver certo e a resposta humana for
"manter 1,5" sem que quem responde tenha visto os números, o motor libera
sapatas com folga ao deslizamento **de 11 % a 36 % abaixo** do equivalente
normativo, com o aval implícito de um software auditado. O segundo risco é
assimetricamente pior, e é por isso que a pergunta vai com os três números
(1,68 / 1,96 / 2,35) colados a ela.

**Discrepância de edição — registro, não tarefa.** Apostila cita 2021 (3×,
e "2022" não aparece em nenhuma de suas 119 páginas); código cita 2019; acervo
tem 2022. Os três trechos que a apostila cita literalmente batem palavra por
palavra com a edição 2022, e os 16 itens que ela cita têm a mesma numeração —
compatível com erro de grafia de ano, **não prova** disso, e em nada prova que
o item de deslizamento/tombamento tenha redação igual em 2021. Não há
exemplar de 2021 nem de 2019 no acervo. Fica registrado sem investigação
adicional. Efeito operacional único: a fonte deste projeto é a **NBR
6122:2022**, e toda citação no código deve dizer 2022.

**Achado colateral, pendência separada** — a mesma apostila traz um *segundo*
critério de tombamento, por área comprimida (eqs. 1.48/1.49, p. impressa 46),
esse sim com interlocução direta com §7.6.2. Não foi usado para justificar
nada nesta pendência. Registrado em `ruleset.yaml`, regra
`NBR6122-7.6.2-area-comprimida`, campo `achado_colateral_v5`. Resumo: o
critério `(e_A/A)² + (e_B/B)² ≤ 1/9` equivale a 50 % de área comprimida
(conferido pelo a2 no limite uniaxial), que é o patamar de §7.6.2 para
solicitações **de cálculo**; o código usa 2/3 sobre combinações
características, que é o patamar correto para essa rota. **Nada a corrigir** —
e serve de guarda contra trocar 2/3 por 1/9 numa "otimização" futura, o que
seria migrar de patamar sem migrar de combinação.

### Achado colateral encontrado pelo a2 nesta releitura (não veio do a6)

`geotecnia.py:217` define `coef_sigma_max_excentrico = 1.2` e `sapata.py:359`
faz `limite = self.solo.sigma_adm * 1.2` **sempre** que a seção fica
parcialmente comprimida (k > 1), sem condição alguma. Não existe na
NBR 6122:2022 majoração de 20 % da tensão admissível por excentricidade.
A única majoração de tensão admissível da norma é a de **vento**:

> §6.3.2: "...nas quais o vento é a ação variável principal, os valores de
> tensão admissível de sapatas e tubulões [...] podem ser majorados em até
> 15 %. Quando esta majoração for utilizada, o fator de segurança global não
> pode ser inferior a 1,6." (30 % em galpões industriais, torres de linhas de
> transmissão, reservatórios elevados, silos graneleiros, torres eólicas,
> torres de telecomunicações e tanques de produtos químicos.)
> §6.3.3 (valores de cálculo): até 10 %.

Ou seja: a constante 1,2 (a) excede o teto geral de 15 %, (b) ignora a
condição de vento ser ação variável principal, (c) ignora a exigência
FSg ≥ 1,6. É uma guarda condicional virada constante — exatamente o defeito
que `a2-verificador.md` §3 manda proibir. `PENDENTE_HUMANO`, a5 não mexe.

## Questão 2 — lista de ação para o a5: ocorrências de "NBR 6122:2019"

Contagem própria do a2 (`grep -rn "6122:2019" calc_core/ ui/`):
**13 ocorrências em arquivos-fonte**. O a6 está certo no total, o a5 estava
errado (12). Os `.pyc` em `__pycache__/` também casam com o grep mas são
artefatos de build — **não editar**, regeneram sozinhos.

A edição 2019 não existe no acervo deste repositório. O acervo tem
NBR 6122:**2022**. Toda ocorrência do ano deve virar 2022. O que não é
automático é o **item citado junto** — a numeração pode ter mudado entre
edições e a edição 2019 não está disponível para comparação. O que dá para
fazer, e foi feito, é conferir se o item citado existe e diz o que a string
afirma **na edição 2022**.

| # | arquivo:linha | ação |
|---|---|---|
| 1 | `calc_core/sapata_isolada/__init__.py:5` | **trocar ano** |
| 2 | `calc_core/sapata_isolada/recalques.py:14` | **trocar ano** + ver nota A |
| 3 | `calc_core/sapata_isolada/pranchas.py:67` | **trocar ano** (carimbo da prancha) |
| 4 | `calc_core/sapata_isolada/sapata.py:5` | **trocar ano** |
| 5 | `calc_core/sapata_isolada/relatorio.py:33` | **trocar ano** (cabeçalho do memorial) |
| 6 | `calc_core/sapata_isolada/acoes.py:133` | **trocar ano** + ver nota B |
| 7 | `calc_core/sapata_isolada/geotecnia.py:7` | **trocar ano** |
| 8 | `calc_core/sapata_isolada/geotecnia.py:202` | **trocar ano** |
| 9 | `calc_core/sapata_isolada/geotecnia.py:236` | **trocar ano** |
| 10 | `ui/completo/resultado.py:21` | **trocar ano** (itens conferidos, ver nota C) |
| 11 | `ui/completo/resultado.py:22` | **REVISAR ITEM PRIMEIRO — BLOQUEADO** (Questão 1) |
| 12 | `ui/completo/resultado.py:27` | **trocar ano** + ver nota A |
| 13 | `ui/completo/app.py:38` | **trocar ano** (subtítulo da janela) |

Conferência dos itens citados junto ao ano, contra a edição 2022:

- **Nota C — `resultado.py:21`, "§7.1/§7.6.1 — tensão admissível na base":
  CORRETO na 2022, troca de ano é segura.** §7.1 "Generalidades" (PDF p. 33,
  p. impressa 21) abre com "A grandeza fundamental para o projeto de fundações
  rasas é a tensão admissível, se o projeto for feito considerando fator de
  segurança global e valores característicos, ou a tensão resistente de
  cálculo, quando for feito considerando coeficientes de ponderação e valores
  de cálculo." §7.6.1 "Cargas centradas" (PDF p. 35) confere e já é regra
  `APROVADA` no ruleset (`NBR6122-7.6.1-area-carga-centrada`).
- **Nota A — `recalques.py:14` e `resultado.py:27`, "§6.2/§7 — deslocamentos e
  sua verificação": ano pode ser trocado; item é impreciso, não falso.**
  Na 2022, §6.2 é "Estados limites" (não "deslocamentos"); quem trata de
  deslocamento é §6.2.2 (ELS, `Ek ≤ C`) e §6.2.2.2 ("Valores limites dos
  deslocamentos das fundações"). §7 inteiro é "Fundação rasa"; o item que
  amarra tensão ao ELS é §7.4, que remete explicitamente a 6.2.2. Sugestão
  **não bloqueante** para o a5 aplicar junto: `§6.2.2.2/§7.4`. Se preferir
  não mexer no item agora, trocar só o ano é aceitável — a citação atual é
  ancestral verdadeiro, apenas grosso.
- **Nota B — `acoes.py:133`, "prática consagrada e NBR 6122:2019, item 6.2":
  ano pode ser trocado; NÃO promover a citação.** §6.2.2.1 exige `Ek ≤ C` com
  ações e parâmetros **característicos**, o que sustenta usar combinação de
  serviço para verificar a tensão do solo. Mas a norma **não** prescreve a
  combinação "ELS rara" especificamente. A docstring já rotula como "prática
  consagrada" e esse rótulo tem de **permanecer**. Refinar para §6.2.2.1 é
  opcional; o que não pode é a linha passar a sugerir que a escolha da
  combinação é texto normativo.

### Correção adicional que o a6 não listou: `6.2.1.2` aparece em CINCO lugares, não quatro

O a6 listou quatro e usou números de linha desatualizados (`sapata.py:712`,
depois dos commits do a5 é `sapata.py:732`). Lista correta e verificada
(`grep -rn "6\.2\.1\.2" calc_core/ ui/ --include=*.py`) — **todos BLOQUEADOS**
até a decisão da Questão 1:

| arquivo:linha | trecho |
|---|---|
| `calc_core/sapata_isolada/sapata.py:732` | `#  Estabilidade global (NBR 6122, item 6.2.1.2)` |
| `calc_core/sapata_isolada/relatorio.py:129` | `_sec("4. ESTABILIDADE (NBR 6122, 6.2.1.2)")` |
| `calc_core/sapata_isolada/acoes.py:140` | `... peso próprio é estabilizante (NBR 6122, item 6.2.1.2).` |
| `calc_core/sapata_isolada/geotecnia.py:215` | `fs_deslizamento: float = 1.5  # NBR 6122, 6.2.1.2` ← **omitido pelo a6** |
| `ui/completo/resultado.py:22` | `ITEM_ESTABILIDADE = "NBR 6122:2019 §6.2.1.2 — ..."` |

`geotecnia.py:215` é justamente a linha onde a citação errada e o valor sem
respaldo normativo estão na mesma linha — a mais importante das cinco, e a que
escapou das duas revisões anteriores.

### Sobre a inconsistência 2019/2022 apontada pelo a6

Procede: `rigidez.py:56` já foi corrigido para 2022 pelo a5 e as outras 13
ficaram em 2019. A correção do a5 estava **certa em mérito** (2019 não existe
no acervo), só ficou incompleta. Não reverter `rigidez.py:56`; completar as
outras 12 liberadas acima. A ocorrência 11 permanece em 2019 até a decisão
humana — e isso é intencional e preferível: uma citação visivelmente errada
é mais segura que uma citação errada disfarçada de certa.

---

## Rodada 2026-08-27 (b) — Espraiamento 2V:1H entre camadas de solo

**Pedido:** visualização de corte mostrando espraiamento de tensões entre camadas.
Gatilho: `calc_core/sapata_isolada/geotecnia.py:191`, função órfã
`acrescimo_tensao_2v1h(q, a, b, z)`.

**Resultado da busca: NEGATIVO em todo o acervo.** Registros novos em
`kb/clausulas.jsonl`: `NBR6122-espraiamento-2v1h-nada` e
`BASTOS-espraiamento-2v1h-nada` (buscas negativas), mais cinco registros
positivos de contexto (`NBR6122-1-escopo-melhoramento-solo-excluido`,
`NBR6122-7.3.1-camadas-influenciadas`, `NBR6122-7.3.2-metodos-teoricos-dominio`,
`NBR6122-7.7.4-cotas-diferentes-angulo-alfa`, `NBR6122-7.8.2-bloco-angulo-beta`,
`NBR6122-8.3-efeito-grupo-sapata-hipotetica`) e
`BASTOS-1.5-distribuicao-tensoes-na-base`.

### O que o a2 precisa decidir (não decidido aqui)

1. **Rótulo da fórmula.** Não há item normativo citável. Diferença relevante em
   relação ao FS = 1,5 e a Winkler/Hetényi: para aqueles existia ao menos uma
   fonte secundária no acervo (apostila do Bastos, eq. 1.72/1.75). Para o 2V:1H
   **não há fonte alguma no repositório** — nem normativa nem secundária. Se o
   rótulo for `PRÁTICA CONSAGRADA`, ele se apoiará em conhecimento geral de
   Mecânica dos Solos sem documento de respaldo neste acervo. Isso é um degrau
   abaixo dos casos já rotulados.
2. **`kb/formulas.yaml` não recebeu entrada para o 2V:1H**, deliberadamente:
   um registro exige norma + item + página + hash, e não existe fonte para
   nenhum dos quatro. Registrar a fórmula a partir do código-fonte seria
   inverter o sentido do pipeline (o código passaria a ser a fonte da regra).
3. **Cobertura no ruleset.** `escopo_amplo_em_conferencia > sapata_isolada.geotecnia`
   está `PENDENTE_HUMANO` e cobre "propagação de Boussinesq/Newmark" — a função
   2V:1H está no módulo listado, mas **não** na enumeração do que o item cobre.
   Zona cinzenta a resolver explicitamente.
4. **Boussinesq também não tem respaldo na NBR 6122** (0 ocorrências). O bulbo
   já desenhado por `PerfilCortes._bulbo` e o 2V:1H estão no mesmo patamar
   normativo: nenhum. A diferença é de consagração bibliográfica, não de estatuto.

### Armadilhas de citação a evitar no memorial

- §7.7.4 (α ≥ 60°/45°/30°) **não** é ângulo de espraiamento: é proteção
  geométrica entre fundações vizinhas em cotas diferentes, medido com a
  **vertical**, e cresce para solo **pior** — comportamento oposto ao de um
  ângulo de difusão de tensão (2V:1H ≙ 26,57° com a vertical, fixo).
- §7.8.2 (β ≥ 60°) é geometria do **bloco de concreto**, não do solo.
- §8.3 (sapata hipotética a f/3) é **fundação profunda** e mantém o **contorno
  do grupo sem alargamento** com a profundidade.
- §1 Escopo **exclui** "melhoramento do solo" — camada de reforço/lastro de
  rachão sobre solo mole está fora do escopo da Norma **por declaração**, não
  por omissão. É o argumento mais forte contra qualquer `[rule: ]` de NBR 6122
  numa futura implementação.

---

## Rodada 2026-08-27 (c) — a2-verificador: decisão sobre propagação de tensão

Fecha o levantamento da rodada (b). Registros criados em `ruleset.yaml`
(versão 6, seção nova `praticas_consagradas`):

| id | status |
|---|---|
| `PC-BOUSSINESQ-NEWMARK-canto-retangulo` | `APROVADA` |
| `PC-ESPRAIAMENTO-2V1H` | `APROVADA_COM_USO_RESTRITO` |

Ambas com `respaldo_normativo: NENHUM` e `natureza: PRATICA_CONSAGRADA`. Citação
em código é `[pratica: <id>]`, **nunca** `[rule: <id>]`.

### O que NÃO foi aprovado e continua exigindo decisão humana

**Pendência C1 — o ramo 2V:1H de `recalques.py:263-266` alimentando recalque.**

*Pergunta objetiva:* o parâmetro `usar_boussinesq` de `RecalqueCalculador` deve
ser removido (mantendo só Boussinesq), ou mantido como opção do projetista com
aviso de que subestima o recalque?

*Trecho literal (código, `calc_core/sapata_isolada/recalques.py:262-266`):*

```python
def _delta_sigma(self, z_abaixo_base: float) -> float:
    if self.usar_boussinesq:
        return acrescimo_tensao_centro(self.q_liquido, self.a, self.b, z_abaixo_base)
    return self.q_liquido * (self.a * self.b) / \
        ((self.a + z_abaixo_base) * (self.b + z_abaixo_base))
```

*Leitura proposta pelo a2:* remover o ramo. Não é uma alternativa equivalente.
Integrando `dsigma·dz` de 0 a 2B — proxy direto do recalque em meio homogêneo —
o 2V:1H entrega **0,748** do valor de Boussinesq, fator praticamente invariante
com a geometria (0,748 para 2x2, 2x4, 1,2x1,2 e 4x4 m; 0,797 se integrado até
4B). Recalque ~25 % menor, **do lado inseguro**, sistemático. O default hoje é
`True` e nenhum chamador passa `False`, então o ramo é inalcançável na prática —
não há urgência, mas há uma armadilha carregada.

*Impacto se a leitura estiver errada:* se houver razão de projeto para preferir
o 2V:1H em recalque (não conhecida pelo a2), remover o ramo tira uma opção
legítima. Custo baixo e reversível. O impacto do erro oposto — expor o seletor e
alguém usá-lo — é recalque 25 % menor num memorial assinado.

*Enquanto não houver decisão:* `REQ-PROP-05` proíbe expor o seletor, ligá-lo por
default ou usá-lo em memorial.

**Pendência C2 — espraiamento com ângulo variável por camada / lastro de rachão.**

*Pergunta objetiva:* o software deve algum dia oferecer espraiamento com ângulo
diferente por camada (o caso da imagem de referência 1: lastro de rachão sobre
solo mole)?

*Leitura proposta pelo a2:* **não**, e por dois motivos independentes — cada um
bastaria. (i) A NBR 6122:2022 §1 (Escopo) exclui "melhoramento do solo" por
declaração, não por omissão: não existe item da norma para citar. (ii) Mais
decisivo, é erro de modelo: o benefício de um lastro vem justamente do contraste
de rigidez, e um método de ângulo constante não enxerga contraste de rigidez —
não pode quantificar o efeito que o lastro existe para produzir. Adotar ângulos
diferentes por camada também descaracteriza a fórmula aprovada: a área alargada
deixa de ser `(a+z)(b+z)` e a verificação de equilíbrio vertical feita nesta
rodada não vale mais.

*Impacto se a leitura estiver errada:* nenhum sobre o código atual (nada disso
está implementado). O risco é de expectativa: se a funcionalidade for prometida
na UI, o memorial insinuará cobertura normativa que a norma explicitamente não
dá. `REQ-UI-03` proíbe nomear ou insinuar a funcionalidade.

**Pendência C3 — verificação de camada subjacente.**

*Pergunta objetiva:* o software pode comparar `dsigma_z(z) + sigma'_v0(z)` com o
`sigma_adm` de uma camada mais profunda e emitir PASSA/NÃO PASSA?

*Leitura proposta pelo a2:* não sem decisão de engenharia registrada. A NBR
6122:2022 não prescreve o procedimento, e transformar um valor informativo em
critério de aceitação é exatamente o que separa o que o a2 pode aprovar sozinho
do que não pode. `REQ-PROP-03` mantém os valores como informativos.

*Impacto se a leitura estiver errada:* se a verificação for devida e não for
feita, uma camada mole profunda passa despercebida — lado inseguro. É a
pendência mais relevante das três em consequência de projeto, e a que mais
merece a atenção do engenheiro.

---

## Rodada 2026-08-28 (ruleset versão 8) — lacuna de memorial do croqui de espraiamento

Registro de escopo, não de norma. A v8 do ruleset é editorial (três textos
realinhados a decisões de implementação já verificadas pelo a6 na rodada 2 do
GATE 2); dois dos três ajustes não deixam pendência. Este deixa.

**Pendência D1 — a feature de espraiamento não chega ao memorial PDF.**

*Pergunta objetiva:* a integração do croqui de espraiamento ao memorial
(`calc_core/sapata_isolada/pranchas.py`) fica para rodada posterior, ou é
condição para liberar a feature ao usuário final?

*Trecho literal da fonte (relatorio do a6, rodada 2, defeito BAIXA/E4,
`pranchas.py:496`):* "Reincidente da rodada 1, item 13, não endereçado:
pranchas.py não foi tocado por nenhum dos 4 commits. O espraiamento por camada,
o rótulo de método e os dois avisos permanentes existem só na tela. Nenhum
número errado é emitido — a feature simplesmente não chega ao PDF — mas a
metade 'repetido no memorial' de REQ-UI-01 continua em aberto e
fonte_espraiamento continua sendo estado exclusivamente de UI, que é o que
REQ-PROP-04 nomeia. (...) Hoje o requisito está parcialmente aberto sem nenhum
registro de que isso é deliberado."

*Leitura proposta pelo a2:* **fica para rodada posterior, como pendência aberta
com gatilho, e não é bloqueante para este GATE 2.** Confirmado por
`git log 8e46372..HEAD --name-only` que `pranchas.py` não aparece em nenhum dos
quatro commits (72b9987, 783b3c3, 3f92b39, 9ecebd2). A lacuna é de OMISSÃO, não
de erro: nada desta feature chega ao PDF, logo nenhum número errado é emitido, e
REQ-PROP-04 fica satisfeito por vacuidade — não há número desacompanhado de
método porque não há número. Prazo em calendário não é cobrável por este
pipeline; gatilho é. Registrado em `ruleset.yaml` v8 em
`REQ-UI-01 > nota_de_escopo_v8` e `REQ-PROP-04 > nota_de_escopo_v8`, com três
gatilhos que tornam a integração bloqueante: (i) release ao usuário final com o
memorial apresentado como completo para esta feature; (ii) `pranchas.py` passar
a emitir qualquer valor de propagação; (iii) o A7 rodar sobre esta feature com
caso que confira o PDF.

*Impacto se a leitura estiver errada:* se a integração for devida agora e for
adiada, o engenheiro que assina a ART recebe um memorial que **silencia** sobre
uma análise que viu na tela — pior, sobre a única análise da feature que a NBR
6122:2022 não prescreve. Ele pode concluir que o espraiamento foi considerado no
documento assinado quando não foi. O risco é de expectativa e de rastreabilidade,
não de número errado; nenhum valor incorreto é emitido em nenhuma hipótese.
Se, ao contrário, a integração for feita sem os rótulos junto (o gatilho (ii)),
o risco inverte de sinal e passa a ser violação direta de REQ-PROP-04 — método
não rastreável em documento assinado, com diferença medida de até 37 % entre os
dois métodos para a mesma camada.
