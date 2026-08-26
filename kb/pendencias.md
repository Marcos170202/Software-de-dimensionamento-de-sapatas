# Fila humana — decisões que a2-verificador não pode tomar sozinho

Regras extraídas mas com `status: PENDENTE_HUMANO` em `ruleset.yaml`. Não
implementar em `calc_core/` até virarem `APROVADA`.

## NBR6122-7.6.2-area-comprimida (carga excêntrica)

**Pergunta objetiva:** qual estratégia de busca usar para B×L quando há
excentricidade em uma ou duas direções, respeitando a área comprimida mínima
(2/3 característica / 50% cálculo) e o núcleo central?

**Trecho literal:** ver `kb/clausulas.jsonl`, item `7.6.2`.

**Leitura proposta:** implementar em duas etapas — (1) diagrama trapezoidal
enquanto a resultante cai dentro do núcleo central (e ≤ B/6), (2) diagrama
triangular com redistribuição de área quando e > B/6, limitando pela área
comprimida mínima. É o método padrão de livros-texto de fundações (não é
texto da norma, é prática consagrada — precisa virar decisão explícita, não
suposição do agente).

**Impacto se a leitura estiver errada:** subdimensionamento da sapata sob
momento — o tipo de erro que a norma trata como estado limite último (ruptura
por esgotamento de resistência do terreno, 6.2.1 g).

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
