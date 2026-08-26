# SAPATA-7 — Dimensionamento estrutural e geotécnico de sapatas

## Princípio mestre

**O LLM raciocina, interpreta e escreve código. O LLM NUNCA executa o cálculo de
projeto.** Todo número do memorial vem de Python determinístico, versionado,
testado e rastreável a um item normativo. Se os agentes sumirem amanhã, o software
continua funcionando e auditável.

## Ordem do pipeline e portões

```
a1-bibliotecario → a2-verificador → [GATE 1: ruleset.yaml congelado]
                                  ↓
      a3-interface | a4-geotecnico | a5-estrutural   (paralelo)
                                  ↓
                   a6-revisor → [GATE 2: nota ≥ 4, com veto em E1 e E2]
                                  ↓
                   a7-validador → [GATE 3: 100% dos casos ALTA]
                                  ↓
                              release
```

Realimentação: A6 devolve a A3/A4/A5 (máx. 3 ciclos); A7 devolve a A4/A5; A2
devolve a A1.

## Regras do repositório

1. `ruleset.yaml` só é escrito pelo **a2-verificador**. Mais ninguém.
2. Nada entra em `calc_core/` sem regra `APROVADA` correspondente no ruleset.
3. Toda função pública em `calc_core/` carrega docstring com item normativo,
   página e `[rule: <id>]`. É isso que gera o memorial e permite a auditoria.
4. `ui/` não calcula. Nenhuma exceção.
5. Alterar o `ruleset.yaml` invalida as aprovações de A6 e A7 — nova rodada.

## Ordem sugerida de execução

Rode A1 e A2 **apenas** para o subconjunto mínimo: sapata isolada, carga centrada,
solo homogêneo. Depois A4 → A5 → A6 → A7. Só então amplie o escopo.

Fazer o A1 varrer as sete normas inteiras antes de existir uma linha de
`calc_core` é a forma mais confiável de gastar duas semanas e não ter software.

## Normas do acervo

NBR 6122:2022 (fundações) · NBR 6118:2023 + Emenda 1 (concreto) · NBR 8681:2025
(ações e segurança) · NBR 6120:2019 (cargas) · NBR 6123:2023 (vento)

Os PDFs ficam na raiz deste repositório (não em `refs/`). A NBR 6122:2022 tem
texto UTF-8 limpo (confirmado por extração direta com pymupdf); a NBR 6118:2023
é a que usa CMap deslocado — rode `python tools/decodificar_nbr.py <arquivo>`
antes de ler seu texto corrido. As equações da 6118 continuam sem camada de
texto em qualquer dos dois casos: só saem por leitura visual da página.

## Estado do pipeline

- **GATE 1 (congelado):** `ruleset.yaml` — sapata isolada, carga centrada, solo
  homogêneo, a partir da NBR 6122 §5.6, §7.1, §7.6.1, §7.7.1. Ver
  `relatorios/`.
- **Implementado (A4):** `calc_core/geotecnico/geometria.py` (busca de B×L para
  carga centrada) e `restricoes.py` (dimensão mínima em planta).
- **Pendente:** carga excêntrica (§7.6.2), deslizamento/tombamento (§7.6.3),
  recalques (§7.4), determinação de σ_adm a partir de SPT/CPT (§7.3.3), e todo
  o dimensionamento estrutural (A5, depende de extrair as fórmulas da NBR 6118
  por visão — ainda não feito). Não use este software para nada além da
  geometria da sapata sob carga centrada até esses itens serem implementados.

## Limites

Ferramenta de apoio à decisão. A NBR 6122 §7.2 lista doze fatores para fixar a
tensão admissível, incluindo peculiaridades da obra e alívio de tensões — nenhum
software infere isso de um perfil SPT. O memorial e os desenhos são de
responsabilidade do engenheiro que assina a ART.
