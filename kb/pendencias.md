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
