# kb/ — base normativa e de catálogos (importada de EstruturasMetalicas)

Este diretório foi copiado em 2026-11-03 do repositório
`Marcos170202/EstruturasMetalicas` (commit da branch `main` no momento da
cópia) para dentro desta branch (`claude/openstruct-3d-foundation-core-5n9rpx`),
a pedido do usuário, para servir de base normativa/catálogos ao app de análise
estrutural 3D que já estava em desenvolvimento aqui (`src/estrutura_metalica/`).

## O que tem aqui

- `fontes_originais/normas/` — PDFs originais da ABNT: NBR 8800:2024 (projeto
  de estruturas de aço), NBR 6120:2019 (ações), NBR 6123:2023 (vento),
  NBR 8681:2025 (ações e segurança).
- `fontes_originais/catalogos/` — PDFs originais de catálogos de fabricante
  (Gerdau, ArcelorMittal, British Steel, Vallourec, Usiminas, parafusos
  Hard/Rudge Ramos, chumbadores Hilti/Ancora, barras roscadas Walsywa).
- `catalogos/*.json` — catálogos já extraídos e estruturados (perfis W/H,
  L/I/U/T/barras, aços especiais, parafusos) com citação de página/fonte.
- `nbr8800/*.json` — itens da NBR 8800:2024 já extraídos com citação de
  norma+item+página+hash (tração, compressão/flambagem global, flexão simples,
  flexo-compressão, cisalhamento, ligações parafusadas simples, combinações de
  ações da NBR 8681, deslocamentos limites, propriedades de materiais).
- `livros/*.json` — exemplos resolvidos de bibliografia (Pfeil) usados para
  validação (A7) no projeto de origem.

## O que NÃO foi feito ainda (próximo passo, não desta cópia)

**Esta cópia é só a matéria-prima normativa — ela NÃO foi reconciliada com o
código já existente em `src/estrutura_metalica/`.** Em particular:

1. `docs/normative/NBR8800-RULES.md` (já existente nesta branch) é uma
   redação própria, sem citação de página/hash — os itens em `kb/nbr8800/*.json`
   são mais rastreáveis (citam página e hash do trecho) e devem ser usados como
   fonte de verdade quando os dois divergirem. Alguém precisa comparar os dois
   e decidir.
2. Os catálogos hardcoded em `src/estrutura_metalica/model/*_catalog.py`
   (perfis Gerdau W/H e L/I/U/T, aços EN 10025/A572, tubos Vallourec, perfis
   British Steel, parafusos ASTM) **não foram verificados linha a linha**
   contra `kb/catalogos/*.json` nem contra os PDFs de catálogo. Pode haver
   divergência de valores — isso precisa de uma auditoria tipo A2/A6 antes de
   confiar nos dois lados como equivalentes.
3. Vários catálogos aqui (Usiminas chapas/laminados, Hilti, Ancora, Walsywa,
   aços especiais Gerdau) ainda não têm NENHUM código correspondente em
   `src/estrutura_metalica/model/` — são material para extensão futura, não
   uso imediato.
4. O escopo de `kb/nbr8800/*.json` cobre tração, compressão/flambagem global,
   flexão simples, flexo-compressão, cisalhamento e ligações parafusadas
   simples — **não cobre** flexão com FLT completa, ligações soldadas nem
   análise de 2ª ordem/P-Delta, que (no projeto de origem) viviam em código
   Python separado (`calc_core/analise3d/`, `calc_core/dimensionamento/`),
   não em JSON extraído — esse código não foi copiado, só a base normativa.

Pendência registrada para quando alguém (A2-equivalente deste projeto, ou o
usuário) decidir como reconciliar as duas fontes.
