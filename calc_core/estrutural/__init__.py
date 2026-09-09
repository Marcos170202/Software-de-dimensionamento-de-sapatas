"""Motor ESTRUTURAL — pilarete de concreto (pilar curto) sob a base metálica.

Ref.: ABNT NBR 6118:2023, Seções 8, 9, 11, 12, 13, 14, 15, 17, 18 e 21
[req: REQ-PILARETE-01-modulo-novo-e-fronteira-de-dependencia]

POR QUE ESTE PACOTE É NOVO, e não uma extensão de ``calc_core/sapata_isolada/``
(decisão do a2-verificador, registrada em ``ruleset.yaml`` v13, cabeçalho de
``requisitos_para_a5``): ``sapata_isolada/`` é o motor de ESCOPO AMPLO, apenas
PARCIALMENTE auditado ("escopo amplo em conferência"). O pilarete nasce 100 %
rastreado pelo GATE 1 desta rodada, e misturar os dois apagaria exatamente a
informação que o usuário mais precisa ler — qual parte do memorial está
auditada e qual não está.

FRONTEIRA DE DEPENDÊNCIA PERMITIDA (REQ-PILARETE-01), verificável por inspeção:
este pacote importa de ``calc_core/sapata_isolada/materiais.py`` apenas
``Concreto`` e ``Aco`` (Seção 8, já conferida item a item — ver
``relatorios/revisao_codigo.md``, adendo) e NADA MAIS do pacote amplo. É
PROIBIDO importar geotecnia, rigidez, recalques, bielas, grelha, solo_mef ou
sapata; e é PROIBIDO que ``sapata.py`` passe a importar ``estrutural/`` nesta
versão (a integração pilarete<->sapata é rodada própria, com novo GATE).

CONVENÇÃO DE UNIDADES DESTE PACOTE, declarada porque a checagem dimensional
NÃO pega os dois erros mais prováveis desta feature (REQ-PILARETE-02):

    força ......................... kN
    comprimento (geometria) ....... m
    momento ....................... kN·m
    resistência de material ....... MPa
    diâmetro de barra ............. mm  (parâmetros terminados em ``_mm``)
    deformação .................... adimensional (2,0 ‰ = 0.002)

Os dois pontos em que a unidade é armadilha, e que por isso viajam no NOME do
parâmetro: ``h_secao_m`` na expressão de M_1d,mín (o 0,015 carrega METROS) e
``b_min_cm`` na de gamma_n (o 0,05 carrega 1/cm). Uma terceira, acrescentada
na v13: ``f_ck_MPa`` dentro de alpha_v2 = (1 − f_ck/250).

NAMESPACE — SEIS COLISÕES DE SÍMBOLO REGISTRADAS PELO a2 (REQ-PILARETE-01).
São normativas para este pacote e valem como critério de veto do a6:

===========================  =================================================
Nome usado AQUI              Motivo
===========================  =================================================
``h_secao`` / ``b_secao``    ``h`` é altura da SAPATA em 22.6.1 e espessura de
                             camada na geotecnia.
``b_min_cm``                 ``b`` é largura da sapata, em METROS, na
                             geotecnia; aqui é a menor dimensão da seção em
                             CENTÍMETROS (13.2.3, Tabela 13.1).
``lambda_esbeltez``          ``Concreto.lambda_x`` (17.2.2, relação y/x do
                             bloco retangular) já existe em ``materiais.py``.
``alpha_b`` / ``alpha_c`` /  são CINCO ``alpha`` distintos no ruleset; nomes
``alpha_interacao`` /        completos sempre. Um símbolo chamado ``alpha``
``alpha_ancoragem`` /        NU é VETO do a6 — ``alpha = 1.5`` na interação
``alpha_estribo``            passa por toda a checagem dimensional e produz
                             envoltória mais cheia (lado INSEGURO).
``gamma_n``                  13.2.3 (seção reduzida) x ``gamma_n1`` (15.8.1,
                             2ª ordem para lambda > 140, que NÃO existe aqui).
``M_Rd_normal_xx``           componente OBLÍQUA ``M_Rd_obliquo_x`` (17.2.5) x
                             resistente em flexão composta NORMAL. Um "x" a
                             mais troca o significado.
``M_1d_min_xx``              lado SOLICITANTE, expoente 2 (Figura 11.3);
                             ``M_d_tot_min_*`` (Figura 15.2, com 2ª ordem) é
                             REJEITADO por escopo e não pode existir aqui.
``alpha_v2``                 17.4.2.2/17.4.2.3 (elemento linear) x ``alpha_v``
                             de 19.5.3.1 (punção de laje), já em uso no motor
                             amplo. É PROIBIDO um ``alpha_v`` aqui e um
                             ``alpha_v2`` em ``sapata_isolada/``.
``V_Rd2``                    FORÇA em b_w·d [kN] x ``tau_Rd2`` de 19.5.3.1,
                             que é TENSÃO em contorno crítico [MPa]. É
                             PROIBIDO um ``tau_Rd2`` aqui.
``theta_biela``              inclinação da BIELA (17.4.2.3, 30°-45°) x
                             ``alpha_estribo``, inclinação da ARMADURA
                             (17.4.1.1.5, 45°-90°). Dois ângulos na mesma
                             expressão; ``theta`` nu é PROIBIDO.
``d_util_no_plano_do_``      ``d`` é altura útil no plano de V_Sd (17.4.2.2),
``cortante`` /               altura útil das solicitações normais e
``b_w_no_plano_do_cortante`` profundidade de assentamento na geotecnia.
``V_c0`` / ``V_c1`` / ``V_c``  theta = 45° / 30°<=theta<=45° / o valor
                             efetivamente usado. Três objetos distintos que a
                             lista de símbolos da p. 119 separa.
===========================  =================================================

``tau_wd`` é PROIBIDO em todo ``calc_core/``: é símbolo da NBR 6118:2014, não
existe na edição de 2023 e não há regra que o sustente.

O QUE ESTE PACOTE NÃO FAZ, deliberadamente (REQ-PILARETE-12 e -16): não emite
"APROVADO"/"OK" global, não verifica ELS, fadiga, torção (§17.5), efeitos
locais de 2ª ordem (15.8.3, REJEITADA), decalagem (17.4.2.2-c, REJEITADA),
reduções junto aos apoios (17.4.1.2.1, REJEITADA) nem a ligação com a sapata
além da emenda por traspasse.
"""
