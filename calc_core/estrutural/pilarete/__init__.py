"""Pilarete de concreto (pilar curto) sob a base do pilar METÁLICO.

Ref.: ABNT NBR 6118:2023, Seções 9, 11, 12, 13, 14, 15, 17, 18 e 21
[req: REQ-PILARETE-01-modulo-novo-e-fronteira-de-dependencia]

ESCOPO DO SUBPACOTE, e o que fica de fora por decisão registrada: verifica-se
o FUSTE do pilarete (geometria de 13.2.3, esbeltez de 15.8.2, ELU de
solicitações normais de 17.2, ELU de força cortante de 17.4 quando 14.4.1
autoriza, detalhamento de 18.4 composto com 18.3.3.2) e a TRANSFERÊNCIA para
a sapata pela emenda por traspasse (9.5.2.3) e pela junta de concretagem
(21.6). N, M e H na base do pilar METÁLICO são DADO DE ENTRADA: placa de base
e chumbadores pertencem à ABNT NBR 8800, ausente do acervo, e não são
calculados aqui.

ORDEM DE VERIFICAÇÃO, fixada por REQ-PILARETE-15(1) e -17(5), e ela IMPORTA
porque cada guarda é pré-condição da seguinte:

    13.2.3 (geometria)  ->  15.8.1/15.8.2 (pilar curto)  ->  14.4.1 (faixa)
        ->  17.2 (N+M, sempre)  ->  17.4 (V, só na FAIXA A)

Um V_Rd2 calculado antes de a FAIXA ser conhecida é defeito com veto do a6,
mesmo que o valor nunca chegue à tela.

AS DUAS FRONTEIRAS SÃO INDEPENDENTES E É FÁCIL CONFUNDI-LAS: ``lambda <
lambda_1`` (15.8.2) decide se os efeitos LOCAIS DE 2ª ORDEM podem ser
dispensados; ``ell/máx(b,h) >= 3`` (14.4.1) decide a CLASSE do elemento. A
geometria 30×30 com ell = 0,80 m passa na primeira e reprova na segunda.

Módulos, um por matéria:

===================  ========================================================
``geometria``        13.2.3 (b >= 14 cm, A_c >= 360 cm², gamma_n), 18.4.1
                     (pilar-parede), i = sqrt(I/A), cobrimento próprio
                     (Tabela 7.2, nota d).
``esbeltez``         11.3.3.4.3 (M_1d,mín nas duas direções), 15.4.4, 15.6,
                     15.8.1 e 15.8.2 (ell_e, lambda, lambda_1, pilar curto).
``classificacao``    14.4.1 — a razão, a FAIXA e a recusa de §17.4 na FAIXA B.
``secao``            17.2.1/17.2.2/17.2.5 e Figura 11.3 — equilíbrio de seção,
                     M_Rd por varredura, N_Rd0 e o veredito de ELU normal.
``cortante``         17.4.2.1 a 17.4.2.3, 17.4.1.1.1 e 17.4.1.1.2-c) — V_Rd2,
                     V_sw, V_c0/V_c1/V_c, M_0 e a armadura mínima.
``detalhamento``     17.3.5.3, 18.4.2, 18.4.3 e 18.3.3.2 (+ Em1:2026) — as
                     armaduras longitudinal e transversal, com a COMPOSIÇÃO
                     de tetos pelo menor e pisos pelo maior.
``ligacao``          9.5.2.1/9.5.2.3/9.5.2.4.2 (emenda por traspasse) e 21.6
                     (junta de concretagem, com as DUAS recusas).
``elemento``         orquestração na ordem acima, veredito por FAIXA e o
                     memorial de REQ-PILARETE-12.
===================  ========================================================
"""
