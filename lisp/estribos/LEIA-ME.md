# ESTRIBO.LSP: detalhamento automático de estribos

Rotina AutoLISP com janela de edição (DCL) que desenha estribos na seção, cria o
detalhe cotado ao lado e a linha de distribuição, com a nomenclatura no padrão
das pranchas (ex.: `N.16 6 Ø 5.0 c/17 C=113`).

## Como carregar

1. No AutoCAD: `APPLOAD`, selecione `ESTRIBO.lsp` e clique em **Load**.
   Para carregar sempre, adicione o arquivo ao **Startup Suite** (Contents...).
2. Digite `ESTRIBO` (ou `EST`).

Não precisa de nenhum arquivo `.dcl` separado: a janela é gerada
automaticamente.

## Layers

Os layers são criados automaticamente se ainda não existirem no desenho. Se já
existirem, a rotina não altera nada neles.

| Elemento                                      | Layer          |
|-----------------------------------------------|----------------|
| Estribo na seção e no detalhe                 | `EST_ArmPos`   |
| Cotas do detalhe e linha de distribuição      | `EST_Cota`     |
| Identificação (`N.16 6 Ø 5.0 c/17 C=113`)     | `EST_ArmTexto` |

## Janela

**Identificação**
- *Prefixo* e *Posição*: `N.` + `16` resulta em `N.16` (use prefixo `N` para ter `N4`, como na prancha 251).
- *Bitola*: 4.2 / 5.0 / 6.3 / 8.0 / 10.0 / 12.5 / 16.0.
- *Espaçamento c/* e *Quantidade*. Com um *Trecho* informado (ou medido com
  **Medir <**), a quantidade é calculada: `n = int(L/s)` e, se marcado, `+1`.
- *Incluir C=*: acrescenta o comprimento total na identificação do detalhe.

**Tipo de estribo**
- **Padrão**: fechado, pernas a 45° (gancho de 135°).
- **Fechado**: fechado, pernas a 90°.
- **Aberto (U)**: aberto em cima, pernas a 90° para dentro.

**Geometria** (cm, medidas externas do estribo)
- **Genérico**: digite B x H. Sai só o detalhe (e a distribuição, se marcada).
- **Selecionar seção <**: clique na polilinha fechada da seção (pode estar
  dentro de bloco). O estribo é gerado descontando o *cobrimento*, desenhado
  dentro da seção e detalhado ao lado. Funciona com seção retangular ou
  poligonal (L, T, U...).
- **Desenhar estribo <**: clique dois cantos, ou use a opção `Poligono` e
  clique os vértices. O contorno desenhado é o próprio estribo, e B x H são
  medidos automaticamente.
- *Perna* (mínimo **5 cm**) e *Acréscimo de dobra*. No modo automático:
  - 45°: perna = max(5 cm, 5φ); acréscimo = 5φ
  - 90°: perna = max(7 cm, 10φ); acréscimo = 1φ

  (NBR 6118, item 9.4.6.1). Sem o modo automático, qualquer perna ≥ 5 cm é
  aceita e a janela avisa se ficar abaixo do que a norma recomenda.

**Desenho**
- *Unidade* do DWG (cm, m ou mm), *Escala* e *Altura do texto* em mm no papel.
  Exemplo: 2,5 mm a 1:25 em cm dá texto de 6,25.
- Marque o que desenhar: estribo na seção, detalhe cotado, distribuição.
- *Cotas como dimensão*: em vez de texto, cria `DIMALIGNED` com o valor em cm
  (usa o estilo de cota corrente).

A caixa **Resultado** mostra, em tempo real, B x H, o comprimento C, o peso e
como a identificação vai sair.

## Comprimento do estribo

```
Fechado : C = perímetro externo + 2 x (perna + acréscimo)
Aberto  : C = perímetro sem o lado aberto + 2 x (perna + acréscimo)
```

O resultado é arredondado para cima, em cm inteiros. Exemplo: estribo 14 x 35,
Ø 5.0, pernas a 45° dá 98 + 2 x (5 + 2,5) = **113**, igual à prancha
1222-EC-PR-PIEM-VES-251.

## Saída (exemplos)

Seção 19 x 40 selecionada (cobrimento 2,5), com distribuição medida de 111 cm c/17:

![seção](exemplo_secao.png)

Seção poligonal em L:

![poligonal](exemplo_poligonal.png)

Estribo aberto (U):

![aberto](exemplo_aberto.png)

## Observações

- As configurações da janela ficam salvas entre usos (variável `ESTRIBO_CFG`).
- Tudo é feito em um único *undo*: um `U` desfaz o comando inteiro.
- Trechos em arco da polilinha são tratados como retos (a rotina avisa).
- Os ganchos ficam no canto superior esquerdo do estribo.
