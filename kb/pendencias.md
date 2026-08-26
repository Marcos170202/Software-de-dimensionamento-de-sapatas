# Fila humana — decisões que a2-verificador não pode tomar sozinho

Regras extraídas mas com `status: PENDENTE_HUMANO` em `ruleset.yaml`. Não
implementar em `calc_core/` até virarem `APROVADA`.

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
