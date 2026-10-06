;;; ==========================================================================
;;;  ARMVAR.lsp
;;;  Detalhamento de armadura de COMPRIMENTO VARIAVEL  --  v1.12
;;;
;;;  Desenvolvido por Baluarte Soluc,o~es Estruturais
;;;  Eng. Matusalem do Carmo de Oliveira
;;;  baluarteengenharia@outlook.com  /  matusa00@gmail.com
;;;
;;;  AVISO: esta rotina e uma FERRAMENTA DE APOIO. A conferencia do
;;;  resultado e a responsabilidade tecnica pelo projeto sao inteiramente
;;;  do engenheiro responsavel. Confira SEMPRE os comprimentos, a tabela e o
;;;  resumo de aco antes de emitir o desenho. Os autores nao se
;;;  responsabilizam por erros, omissoes ou prejuizos decorrentes do uso.
;;;
;;;  Comandos:
;;;    ARMVAR ....... cria um detalhamento
;;;    ARMVAREDIT ... edita um detalhamento existente (clique em qualquer parte
;;;                   dele): a janela abre com os dados dele e tudo e refeito
;;;    ARMVARATU .... refaz todos os detalhamentos (se os reatores estiverem
;;;                   desligados, ex.: desenho aberto sem a Lisp carregada)
;;;    ARMVARLISTA .. LISTA DE FERROS + RESUMO DE ACO de todo o desenho
;;;                   (armadura variavel: comprimento UNITARIO = "VAR.")
;;;    ARMVARTESTE .. diagnostico: testa no CAD (AutoCAD/ZWCAD) cada recurso
;;;                   usado (xdata, xrecord, blocos, atributos, cotas, reatores)
;;;
;;;  ELEMENTO PARAMETRIZADO  (bloco com atributos + reatores)
;;;  --------------------------------------------------------------------
;;;  Cada detalhamento e UM objeto: o bloco "ARMVAR$AVn$DET" (ferro, cotas,
;;;  textos), com os parametros em ATRIBUTOS: POSICAO, BITOLA, ESPACAMENTO,
;;;  COBRIMENTO, REPETICOES, PERNA/PONTA INICIAL/FINAL, ANGULO_PERNA_INI/FIM
;;;  (desenho da perna: 90 = no plano, 45 = entrando na tela, 135 = saindo da
;;;  tela, 180 = dobrada/gancho; so a representacao, comprimentos iguais),
;;;  GANCHOS_LADO, ACO,
;;;  SIMETRIA, EMENDAS, COMPR_COMERCIAL, TRASPASSE, PRIMEIRO_PEDACO,
;;;  ALTERNAR, AFASTAMENTO, TABELA_EQUIV, ELEMENTO.
;;;   - Selecione o bloco e altere um atributo na janela PROPRIEDADES (depois
;;;     tecle ESC) ou com DUPLO CLIQUE: o detalhamento e refeito, e tambem a
;;;     tabela, o resumo e a LISTA DE FERROS.
;;;   - Altere o CONTORNO da laje (STRETCH, grips): tudo e recalculado.
;;;   - MOVA o bloco ou as tabelas (tambem blocos) a vontade.
;;;   - Valor invalido num atributo e ignorado (o atributo volta ao valor
;;;     valido).
;;;  Os reatores so funcionam com a Lisp carregada: carregue-a sempre
;;;  (APPLOAD > Startup Suite, ou acaddoc.lsp).  Sem reatores, use ARMVARATU.
;;;
;;;  --------------------------------------------------------------------
;;;  NUMERACAO AUTOMATICA
;;;  --------------------------------------------------------------------
;;;  Na janela, "Numeracao": Manual (campo Posicao N), Automatica - desenho
;;;  inteiro, ou Automatica - selecionar area.  A Lisp le os textos, MTEXTs
;;;  e cotas ("N.1", "N1A", "(2X) N.3 N.4"...) e comeca na maior posicao
;;;  encontrada + 1.
;;;
;;;  --------------------------------------------------------------------
;;;  DETALHAMENTO PARAMETRIZADO (edicao futura)
;;;  --------------------------------------------------------------------
;;;  Cada detalhamento guarda no DWG (dicionario ARMVAR_DADOS) os dados da
;;;  janela, a direcao, o contorno (e os handles das entidades do contorno)
;;;  e os pontos clicados; todas as entidades criadas levam o XDATA
;;;  ("ARMVAR" id).  ARMVAREDIT:
;;;   - reabre a janela com os dados do detalhamento (altere o que quiser);
;;;   - rele o contorno das entidades originais, se ainda existirem (se a
;;;     laje foi esticada, as barras sao recalculadas);
;;;   - apaga e refaz ferro, cotas, textos e tabelas (as tabelas ficam onde
;;;     estiverem, mesmo se foram movidas);
;;;   - atualiza a LISTA DE FERROS geral.
;;;  O campo "Elemento" (ex.: L1) agrupa as posicoes na LISTA DE FERROS.
;;;  A LISTA tambem se atualiza sozinha a cada ARMVAR / ARMVAREDIT; um
;;;  detalhamento apagado do desenho sai da lista no proximo ARMVARLISTA.
;;;  Obs.: ferro e cotas sao refeitos nos pontos clicados originalmente;
;;;  se eles foram movidos a mao, voltam para a posicao original.
;;;
;;;  Compatibilidade:  AutoCAD  e  ZWCAD 2024   (AutoLISP puro + DCL)
;;;  Obs.: todos os textos deste arquivo sao ASCII (sem acentos) de proposito,
;;;        para nao depender da pagina de codigo do CAD.  Os acentos dos
;;;        nomes de layer (ex.: EST_Indicacao) sao gerados com (chr ...).
;;;
;;;  --------------------------------------------------------------------
;;;  O QUE ELE FAZ
;;;  --------------------------------------------------------------------
;;;  Detalha armaduras cujo comprimento VARIA ao longo de um contorno
;;;  (paredes com topo inclinado, lajes trapezoidais, tampas circulares...),
;;;  no padrao da prancha modelo (1222-EC-PE-PIEM-ADLT-401-LAJ).
;;;
;;;  1. Janela: formato da barra (perna e ponta em cada extremidade, em cm;
;;;     0 = sem o trecho), bitola, espacamento, cobrimento, posicao (N),
;;;     repeticoes / simetria e emendas por traspasse.
;;;  2. Direcao principal do ferro: digite o angulo (graus) OU clique numa
;;;     linha/polilinha e o LISP assume a direcao dela.
;;;  3. Contorno fechado: retangulo, circulo, polilinha fechada, ou linhas e
;;;     arcos que juntos formem uma figura fechada. O LISP mostra a forma e
;;;     pede a confirmacao.
;;;  4. Clique num ponto DENTRO do contorno: escolhe a barra representada.
;;;  5. Clique onde DESENHAR o ferro (ENTER = no proprio ponto). Pode ser
;;;     fora da laje: uma linha de chamada tracejada liga o ferro a faixa.
;;;  6. Clique a posicao da LINHA DE DISTRIBUICAO (ENTER = automatica).
;;;     A cota da faixa tem LINHA DE EXTENSAO nas duas pontas, ancorada nos
;;;     vertices do contorno que definem a faixa; clique ate 2 vertices
;;;     para trocar a ancora da ponta mais proxima (ENTER = automatico).
;;;     Se ela ficar FORA do ferro, clique o ponto da LINHA DE CHAMADA: a
;;;     bolinha vai sobre o ferro nesse ponto e a chamada tracejada (em "L") segue
;;;     ate a faixa (ENTER = automatico).
;;;  7. Clique onde inserir a TABELA DE FERROS VARIAVEIS (N?A, N?B, ...) e
;;;     onde inserir o RESUMO DE ACO.  Com a opcao "Tabela com comprimento
;;;     unitario equivalente", a tabela sai numa linha so:
;;;     POS. | %%c | QTD. | C.UNIT | C.TOTAL, com C.UNIT = C.TOTAL / QTD.
;;;
;;;  --------------------------------------------------------------------
;;;  PADRAO DOS TEXTOS  (igual a prancha modelo)
;;;  --------------------------------------------------------------------
;;;   - Ferro ..............  (2X) N.1 87 %%c 8 C/15 C=VAR
;;;                          (repeticao, posicao, quantidade, bitola,
;;;                           espacamento, comprimento; "C=368" quando
;;;                           todas as barras tem o mesmo comprimento)
;;;   - Linha de distribuicao  87 (2X) N.1 %%c 8 C/15   e, abaixo, (1300)
;;;   - Trecho principal ...  VAR  (ou o valor, se for constante)
;;;   - Sem repeticao (rep = 1) o prefixo "(2X) " nao e escrito.
;;;   - Comprimento CONSTANTE e emendado: cada pedaco vira uma POSICAO
;;;     separada (N.1, N.2, ...), com o seu texto no ferro
;;;     "(2X) N.1 9 %%c 10 C/15 C=1200" / "(2X) N.2 9 %%c 10 C/15 C=165",
;;;     a faixa "9 (2X) N.1 N.2 %%c 10 C/15" e uma linha por posicao nas
;;;     tabelas.  A janela passa a abrir na proxima posicao livre.
;;;
;;;  --------------------------------------------------------------------
;;;  SIMETRIA  (repeticoes >= 2)
;;;  --------------------------------------------------------------------
;;;  Com a opcao "Desenhar a barra simetrica invertida" ligada, alem do
;;;  ferro positivo (continuo, EST_ArmPos) e desenhada a barra simetrica
;;;  INVERTIDA (negativa), tracejada, na layer EST_ArmNegInt: espelhada,
;;;  com as pernas voltadas para o ferro positivo e ao lado dele, como na
;;;  prancha modelo.
;;;
;;;  --------------------------------------------------------------------
;;;  EMENDAS POR TRASPASSE  (barras maiores que o comprimento comercial)
;;;  --------------------------------------------------------------------
;;;  - Comprimento comercial padrao: 1200 cm (CA-50 / CA-60).
;;;  - Traspasse L padrao (DETALHE DE EMENDAS da prancha modelo):
;;;       L = 40 cm p/ %%c 6,3    L = 40 cm p/ %%c 8,0
;;;       L = 50 cm p/ %%c 10,0   L = 60 cm p/ %%c 12,5
;;;    demais bitolas: 50 x diametro (CONFIRA com a NBR 6118, 9.5.2).
;;;    O valor pode ser alterado na janela.
;;;  - Uma barra com C > comercial e dividida em pedacos <= comercial:
;;;    o 1.o pedaco tem o comprimento COMERCIAL (1200), a nao ser que outro
;;;    valor seja informado no campo "1.o pedaco" (ex.: 890, como no
;;;    detalhe de parede PAR101); os do meio tambem tem o comercial e o
;;;    ultimo leva o resto + L.  Cada emenda acrescenta L ao consumo.
;;;  - O ultimo pedaco nunca fica menor que (gancho final + 2 L): se o resto
;;;    for pequeno, o pedaco anterior e encurtado.
;;;  - ALTERNANCIA (opcao "Alternar barras vizinhas"): a barra vizinha usa
;;;    os MESMOS pedacos em ordem inversa.  No desenho, a barra simetrica
;;;    (tracejada) ja aparece com os pedacos invertidos; sem simetria, e
;;;    desenhada ao lado a barra "ALTER.".  Assim as
;;;    emendas de barras vizinhas nao ficam na mesma secao e a tabela tem
;;;    poucos comprimentos.  As zonas de traspasse de barras vizinhas ficam
;;;    afastadas de pelo menos o "afastamento entre emendas" (padrao 20 cm);
;;;    se nao ficarem, o 1.o pedaco e encurtado de 10 em 10 cm.
;;;  - A tabela de ferros variaveis lista os PEDACOS (ja com o traspasse) e
;;;    o resumo de aco soma o comprimento real consumido.
;;;  - O ferro desenhado mostra as emendas (pedacos desencontrados) com a
;;;    cota do traspasse, se a barra representada passar do comercial.
;;;
;;;  --------------------------------------------------------------------
;;;  COMO OS COMPRIMENTOS SAO CALCULADOS
;;;  --------------------------------------------------------------------
;;;  - O ferro e paralelo a direcao principal e as barras ficam espacadas
;;;    de "esp" na perpendicular.
;;;  - Faixa de distribuicao = largura TOTAL do contorno na perpendicular
;;;    (e o valor da cota).  N.o de barras = teto( faixa / esp ), centradas
;;;    na faixa (mesma regra do modelo: 68/15 -> 5 barras, 292/15 -> 20).
;;;    Se n barras a "esp" nao couberem entre os cobrimentos laterais, o
;;;    espacamento e reduzido (o LISP avisa).
;;;  - Em cada barra, o comprimento PRINCIPAL e a corda do contorno, menos o
;;;    cobrimento medido perpendicularmente a cada borda (numa borda obliqua
;;;    ao ferro o recuo e  cob / sen(angulo da borda com o ferro)).
;;;  - Comprimento TOTAL = principal + pernas + pontas, arredondado a 1 cm.
;;;    Nao ha desconto/acrescimo de dobra: confira com o criterio do projeto.
;;;  - Contornos fechados adicionais na selecao valem como FUROS (regra par-
;;;    impar), e as barras sao interrompidas neles.
;;;  - Peso linear conforme NBR 7480 (kg/m).
;;;
;;;  UNIDADES DO DESENHO
;;;  --------------------------------------------------------------------
;;;  O desenho-modelo esta em "cm de papel" na escala 1:50 (1 unidade = 50 cm
;;;  reais; texto 0.2 = 2 mm plotados).  Isso e o padrao da janela.  Tambem
;;;  ha opcao para desenhos em metros, centimetros ou milimetros reais.
;;;
;;;  LIMITACOES CONHECIDAS
;;;  --------------------------------------------------------------------
;;;  - Trabalha no plano XY do WCS (contorno e desenho no plano do WCS).
;;;  - Elipse/spline no contorno sao aproximadas por segmentos.
;;;  - Cobrimento em contornos curvos e aproximado (exato em bordas retas).
;;;
;;;  LAYERS USADAS  (as mesmas da prancha modelo; criadas se nao existirem)
;;;  --------------------------------------------------------------------
;;;    EST_ArmPos ........... ferro (positivo, continuo)
;;;    EST_ArmNegInt ........ barra simetrica invertida (negativa, tracejada)
;;;    EST_ArmTexto ......... texto do ferro  "(2X) N.1 87 %%c 8 C/15 C=VAR"
;;;    2 .................... comprimentos dos trechos e textos das tabelas
;;;    EST_Cota ............. COTAS (entidades DIMENSION, com tiques): linha
;;;                           de distribuicao "87 (2X) N.1 %%c 8 C/15" /
;;;                           "(1300)" e cota do traspasse, com o TEXTO na
;;;                           cor 7 (white).  Se o CAD nao
;;;                           aceitar ActiveX, sao desenhadas com linhas.
;;;    EST_Indicacao ........ chamada tracejada e circulos (ferro x faixa)
;;;    T_LINHAS_GREEN ....... molduras das tabelas
;;;    TAB-ESTACAS-GRADE .... grade das colunas da tabela de ferros
;;;  Estilo de texto: TQS_ARIAL (arial.ttf), criado se nao existir.
;;;  Tipo de linha:   AV_TRACEJADO (traco 2 : espaco 1), criado se nao existir.
;;; ==========================================================================

(vl-load-com)

;;; --------------------------------------------------------------------------
;;;  PARAMETROS
;;; --------------------------------------------------------------------------
(setq AV:LAY-BAR   "EST_ArmPos"
      AV:LAY-NEG   "EST_ArmNegInt"
      AV:LAY-ESPEC "EST_ArmTexto"
      AV:LAY-TXT   "2"
      AV:LAY-COTA  "EST_Cota"
      AV:LAY-IND   (strcat "EST_Indica" (chr 231) (chr 227) "o")
      AV:LAY-TAB   "T_LINHAS_GREEN"
      AV:LAY-GRADE "TAB-ESTACAS-GRADE"
      AV:STY       "TQS_ARIAL"
      AV:LT-NOME   "AV_TRACEJADO"
      AV:TOL       0.001            ; tolerancia para fechar o contorno
      AV:COR-TXT-COTA 7             ; cor do texto das cotas (7 = white)
      AV:APP       "ARMVAR"         ; aplicacao do XDATA (marca as entidades)
      AV:DIC-NOME  "ARMVAR_DADOS"   ; dicionario com os dados dos detalhamentos
)

(setq AV:BITOLAS '("5" "6.3" "8" "10" "12.5" "16" "20" "22" "25" "32")
      ;; massa linear NBR 7480 (kg/m)
      AV:MASSAS  '(0.154 0.245 0.395 0.617 0.963 1.578 2.466 2.984 3.853 6.313)
      ;; traspasse padrao (cm): DETALHE DE EMENDAS da prancha modelo
      ;; (6.3, 8, 10, 12.5); demais bitolas = 50 x diametro -> CONFERIR
      AV:TRASP   '(40 40 40 50 60 80 100 110 125 160)
      AV:ACOS    '("CA-50" "CA-60" "CA-25")
      AV:UNIDADES '("cm de papel (padrao TQS)"
                    "metros reais"
                    "centimetros reais"
                    "milimetros reais")
      AV:LADOS   '("Direita da direcao (horario)"
                   "Esquerda da direcao (anti-horario)")
      AV:NUMS    '("Manual (campo Posicao N)"
                   "Automatica - desenho inteiro"
                   "Automatica - selecionar area")
      ;; parametros da janela guardados em cada detalhamento (ordem fixa)
      AV:PARAMS  '(AV:P-PL1 AV:P-PT1 AV:P-PL2 AV:P-PT2 AV:P-PM AV:P-LADO
                   AV:P-BIT AV:P-ESP AV:P-COB AV:P-POS AV:P-REP AV:P-ACO
                   AV:P-UNI AV:P-ESC AV:P-ALT AV:P-SIM AV:P-EMD AV:P-LCM
                   AV:P-TRA AV:P-DFS AV:P-AFS AV:P-PIN AV:P-EQU AV:P-ELE
                   AV:P-AG1 AV:P-AG2)
)

;;; ==========================================================================
;;;  1.  UTILITARIOS
;;; ==========================================================================

;;; texto -> real (aceita virgula); nil se invalido
(defun av:num (s / i r)
  (if (or (null s) (= s ""))
    nil
    (progn
      (setq i (vl-string-position 44 s))
      (if i (setq s (strcat (substr s 1 i) "." (substr s (+ i 2)))))
      (setq s (vl-string-trim " " s))
      (if (and (/= s "") (numberp (distof s 2))) (distof s 2) nil)
    )
  )
)

;;; formata cm: inteiro sem casas, senao 1 casa
(defun av:fmt (v)
  (if (< (abs (- v (fix (+ v 0.5)))) 0.0005)
    (itoa (fix (+ v 0.5)))
    (rtos v 2 1)
  )
)

(defun av:hyp (dx dy) (sqrt (+ (* dx dx) (* dy dy))))

(defun av:dist (a b) (av:hyp (- (car a) (car b)) (- (cadr a) (cadr b))))

(defun av:pol (p ang d)
  (list (+ (car p) (* d (cos ang))) (+ (cadr p) (* d (sin ang))))
)

;;; ponto a partir do vetor unitario e do ponto
(defun av:mad (p v d)
  (list (+ (car p) (* d (car v))) (+ (cadr p) (* d (cadr v))))
)

(defun av:dot (a b) (+ (* (car a) (car b)) (* (cadr a) (cadr b))))

;;; angulo de leitura: mantem o texto legivel (-90 < ang <= 90 graus)
(defun av:leitura (a / d)
  (setq d (* a (/ 180.0 pi)))
  (while (< d 0.0) (setq d (+ d 360.0)))
  (while (>= d 360.0) (setq d (- d 360.0)))
  (if (and (> d 90.0001) (<= d 270.0001)) (setq d (- d 180.0)))
  (* d (/ pi 180.0))
)

;;; letras de posicao: 0->A ... 25->Z, 26->AA
(defun av:letra (i)
  (if (< i 26)
    (chr (+ 65 i))
    (strcat (av:letra (- (/ i 26) 1)) (chr (+ 65 (rem i 26))))
  )
)

(defun av:setnth (l n v / r i)
  (setq r nil i 0)
  (foreach x l (setq r (cons (if (= i n) v x) r) i (1+ i)))
  (reverse r)
)

(defun av:remove1 (item lst / r feito)
  (setq r nil feito nil)
  (foreach x lst
    (if (and (not feito) (eq x item))
      (setq feito T)
      (setq r (cons x r))
    )
  )
  (reverse r)
)

(defun av:ultimo (l) (car (reverse l)))

;;; nth que aceita lista vazia ou curta (o ZWCAD da erro em (nth 0 nil))
(defun av:nth (n l)
  (if (and l (listp l) (>= n 0) (< n (length l))) (nth n l))
)

;;; ==========================================================================
;;;  2.  CRIACAO DE ENTIDADES
;;; ==========================================================================

(defun av:layer-liberar (nome / e ed flg cor)
  (if (setq e (tblobjname "LAYER" nome))
    (progn
      (setq ed  (entget e)
            flg (cdr (assoc 70 ed))
            cor (cdr (assoc 62 ed)))
      (setq ed (subst (cons 70 (logand flg (~ 5))) (assoc 70 ed) ed))
      (if (< cor 0) (setq ed (subst (cons 62 (abs cor)) (assoc 62 ed) ed)))
      (entmod ed)
    )
  )
)

;;; cria a layer se nao existir (cor ACI, espessura em 1/100 mm e cor RGB
;;; opcionais); se ja existir, apenas liga/descongela/destrava
(defun av:layer (nome cor lw rgb / base)
  (if (not (tblsearch "LAYER" nome))
    (progn
      (setq base (list '(0 . "LAYER")
                       '(100 . "AcDbSymbolTableRecord")
                       '(100 . "AcDbLayerTableRecord")
                       (cons 2 nome)
                       '(70 . 0)
                       (cons 62 cor)
                       '(6 . "Continuous")))
      (if (not (entmake (append base
                                (if lw  (list (cons 370 lw)))
                                (if rgb (list (cons 420 rgb))))))
        (entmake base)
      )
    )
    (av:layer-liberar nome)
  )
)

;;; tipo de linha tracejado (traco 1.0 / espaco 0.5), escalado por entidade
(defun av:ltype (nome)
  (if (not (tblsearch "LTYPE" nome))
    (entmake
      (list '(0 . "LTYPE")
            '(100 . "AcDbSymbolTableRecord")
            '(100 . "AcDbLinetypeTableRecord")
            (cons 2 nome)
            '(70 . 0)
            '(3 . "Tracejado ARMVAR __ __ __ __")
            '(72 . 65)
            '(73 . 2)
            '(40 . 1.5)
            '(49 . 1.0) '(74 . 0)
            '(49 . -0.5) '(74 . 0)
      )
    )
  )
)

(defun av:ltscale ( / v)
  (setq v (getvar "LTSCALE"))
  (if (and v (> v 0.0)) v 1.0)
)

(defun av:prepara ( / fnt)
  (av:layer AV:LAY-BAR   1 20 nil)
  (av:layer AV:LAY-NEG   1 13 (+ (* 221 65536) 55))   ; RGB 221,0,55
  (av:layer AV:LAY-ESPEC 7 nil nil)
  (av:layer AV:LAY-TXT   2 nil nil)
  (av:layer AV:LAY-COTA  8 13 nil)
  (av:layer AV:LAY-IND   8 13 nil)
  (av:layer AV:LAY-TAB   3 20 nil)
  (av:layer AV:LAY-GRADE 8 13 nil)
  (av:ltype AV:LT-NOME)
  (regapp AV:APP)
  (if (not (tblsearch "STYLE" AV:STY))
    (entmake
      (list '(0 . "STYLE")
            '(100 . "AcDbSymbolTableRecord")
            '(100 . "AcDbTextStyleTableRecord")
            (cons 2 AV:STY)
            '(70 . 0) '(40 . 0.0) '(41 . 1.0) '(50 . 0.0)
            '(71 . 0) '(42 . 0.2)
            '(3 . "arial.ttf") '(4 . "")
      )
    )
  )
)

;;; XDATA que marca as entidades de um detalhamento:
;;;   ("ARMVAR" (1000 . id) (1000 . etiqueta) (1000 . grupo))
;;; AV:ID  = id do detalhamento em construcao (nil = sem marca)
;;; AV:TAG = etiqueta ("ESP" texto do ferro, "FP" 1.o pedaco...) ou ""
;;; AV:GRP = bloco a que a entidade vai: "DET" (ferro), "T1" (tabela de
;;;          ferros), "T2" (resumo de aco), "LST" (lista geral)
(defun av:xd ()
  (if AV:ID (list (av:xd-lista AV:ID (if AV:TAG AV:TAG "") (if AV:GRP AV:GRP ""))))
)

(defun av:xd-lista (id tag grp)
  (list -3 (list AV:APP (cons 1000 id) (cons 1000 tag) (cons 1000 grp)))
)

;;; marca uma entidade ja criada (ex.: cotas feitas por ActiveX)
(defun av:xd-ent (e)
  (if (and e AV:ID) (entmod (append (entget e) (av:xd))))
)

;;; lt/lts: tipo de linha e escala da entidade (nil = PorLayer)
(defun av:mk-line (p1 p2 lay lt lts)
  (entmake (append
             (list '(0 . "LINE") '(100 . "AcDbEntity") (cons 8 lay))
             (if (and lt (tblsearch "LTYPE" lt)) (list (cons 6 lt) (cons 48 lts)))
             (list '(100 . "AcDbLine")
                   (cons 10 (list (car p1) (cadr p1) 0.0))
                   (cons 11 (list (car p2) (cadr p2) 0.0)))
             (av:xd)))
)

;;; polilinha: lt/lts = tipo de linha (com PLINEGEN), wid = largura constante
(defun av:mk-pl (pts lay closed lt lts wid / ok)
  (setq ok (and lt (tblsearch "LTYPE" lt)))
  (entmake (append
             (list '(0 . "LWPOLYLINE") '(100 . "AcDbEntity") (cons 8 lay))
             (if ok (list (cons 6 lt) (cons 48 lts)))
             (list '(100 . "AcDbPolyline")
                   (cons 90 (length pts))
                   (cons 70 (+ (if closed 1 0) (if ok 128 0))))
             (if wid (list (cons 43 wid)))
             (mapcar '(lambda (p) (cons 10 (list (car p) (cadr p)))) pts)
             (av:xd)))
)

(defun av:mk-pline (pts lay closed) (av:mk-pl pts lay closed nil nil nil))

(defun av:mk-circ (c r lay)
  (entmake (append (list '(0 . "CIRCLE") (cons 8 lay)
                         (cons 10 (list (car c) (cadr c) 0.0)) (cons 40 r))
                   (av:xd)))
)

;;; texto:  cen = T -> centrado (ponto = centro da base); senao alinhado a esquerda
(defun av:mk-text (txt p h ang lay cen)
  (entmake (append
             (list '(0 . "TEXT") (cons 8 lay)
                   (cons 10 (list (car p) (cadr p) 0.0))
                   (cons 40 h) (cons 1 txt) (cons 50 ang) '(41 . 1.0)
                   (cons 7 AV:STY))
             (if cen
               (list '(72 . 1) (cons 11 (list (car p) (cadr p) 0.0)) '(73 . 0))
             )
             (av:xd)))
)

;;; muda a cor da ultima entidade criada (textos das cotas desenhadas a mao)
(defun av:cor-ultimo (cor / ed)
  (if (setq ed (entget (entlast)))
    (entmod (if (assoc 62 ed)
              (subst (cons 62 cor) (assoc 62 ed) ed)
              (append ed (list (cons 62 cor)))))
  )
)

;;; tique de cota (traco inclinado a 45 graus, cheio) com centro em "p";
;;; dir = vetor unitario da linha de cota
(defun av:tique (p dir h lay / a v)
  (setq a (+ (angle '(0.0 0.0) dir) (/ pi 4.0))
        v (list (cos a) (sin a)))
  (av:mk-pl (list (av:mad p v (* -0.635 h)) (av:mad p v (* 0.635 h)))
            lay nil nil nil (* 0.125 h))
)

;;; texto centrado ao lado de um segmento.
;;;   mid    = ponto medio do segmento
;;;   lang   = angulo (rad) da direcao do segmento
;;;   away   = vetor unitario do lado onde o texto deve ficar
(defun av:rotulo (txt mid lang away h lay / rot nrm gap base)
  (setq rot (av:leitura lang)
        nrm (list (- (sin rot)) (cos rot))
        gap (* 0.5 h))
  (setq base (if (> (av:dot nrm away) 0.0)
               (av:mad mid away gap)
               (av:mad mid away (+ gap h))))
  (av:mk-text txt base h rot lay T)
)

;;; ==========================================================================
;;;  3.  GEOMETRIA DO CONTORNO
;;; ==========================================================================

(defun av:p2 (p) (list (car p) (cadr p)))

;;; ponto OCS -> WCS (2D)
(defun av:wcs (p ext)
  (if (equal ext '(0.0 0.0 1.0) 1e-9)
    (av:p2 p)
    (av:p2 (trans p ext 0))
  )
)

;;; arco -> pontos (sem o inicial); a1 e sweep em rad (sweep com sinal)
(defun av:arco-pts (c r a1 sweep / n k pts)
  (setq n (max 4 (fix (+ 1.0 (/ (* (abs sweep) 180.0) pi)))) k 1 pts nil)
  (while (<= k n)
    (setq pts (cons (av:pol c (+ a1 (* sweep (/ (float k) n))) r) pts)
          k (1+ k))
  )
  (reverse pts)
)

;;; LWPOLYLINE -> lista de pontos (WCS), com bulges tesselados
(defun av:lwpoly-pts (ed / ext elev vs cl v i n p1 p2 b pts th ch cen r a1 md dd nrm arc)
  (setq ext  (cdr (assoc 210 ed))
        elev (if (assoc 38 ed) (cdr (assoc 38 ed)) 0.0)
        cl   (= 1 (logand 1 (cdr (assoc 70 ed))))
        vs   nil)
  (if (null ext) (setq ext '(0.0 0.0 1.0)))
  (foreach g ed
    (cond
      ((= (car g) 10) (setq vs (cons (list (cadr g) (caddr g) 0.0) vs)))
      ((and (= (car g) 42) vs)
       (setq vs (cons (list (car (car vs)) (cadr (car vs)) (cdr g)) (cdr vs))))
    )
  )
  (setq vs (reverse vs) n (length vs) pts nil i 0)
  (while (< i n)
    (setq v  (nth i vs)
          p1 (list (car v) (cadr v))
          b  (caddr v))
    (setq pts (cons (av:wcs (list (car p1) (cadr p1) elev) ext) pts))
    ;; segmento em arco (bulge) ate o proximo vertice: pontos intermediarios
    (if (and (or cl (< i (1- n))) b (> (abs b) 1e-9))
      (progn
        (setq v  (nth (rem (1+ i) n) vs)
              p2 (list (car v) (cadr v))
              th (* 4.0 (atan b))
              ch (av:dist p1 p2)
              md (list (/ (+ (car p1) (car p2)) 2.0) (/ (+ (cadr p1) (cadr p2)) 2.0))
              dd (/ ch 2.0)
              nrm (list (- (/ (- (cadr p2) (cadr p1)) ch)) (/ (- (car p2) (car p1)) ch))
              cen (av:mad md nrm (/ dd (/ (sin (/ th 2.0)) (cos (/ th 2.0)))))
              r   (abs (/ dd (sin (/ th 2.0))))
              a1  (atan (- (cadr p1) (cadr cen)) (- (car p1) (car cen)))
              arc (av:arco-pts cen r a1 th))
        ;; o ultimo ponto do arco e o proprio p2 (entra no proximo vertice)
        (setq arc (reverse (cdr (reverse arc))))
        (foreach q arc
          (setq pts (cons (av:wcs (list (car q) (cadr q) elev) ext) pts))
        )
      )
    )
    (setq i (1+ i))
  )
  (setq pts (reverse pts))
  ;; polilinha fechada: repete o primeiro ponto
  (if cl (setq pts (append pts (list (car pts)))))
  pts
)

;;; qualquer curva (ELLIPSE, SPLINE, POLYLINE...) por amostragem
(defun av:curva-pts (e / p1 p2 n i pts pt)
  (setq p1 (vlax-curve-getStartParam e)
        p2 (vlax-curve-getEndParam e)
        n  (max 96 (* 16 (1+ (fix (- p2 p1)))))
        i 0 pts nil)
  (while (<= i n)
    (setq pt (vlax-curve-getPointAtParam e (+ p1 (* (- p2 p1) (/ (float i) n)))))
    (if pt (setq pts (cons (av:p2 pt) pts)))
    (setq i (1+ i))
  )
  (reverse pts)
)

;;; entidade -> lista de pontos (peca). nil se nao suportada
(defun av:peca (e / ed typ ext c r a1 a2)
  (setq ed (entget e) typ (cdr (assoc 0 ed))
        ext (cdr (assoc 210 ed)))
  (if (null ext) (setq ext '(0.0 0.0 1.0)))
  (cond
    ((= typ "LINE")
     (list (av:p2 (cdr (assoc 10 ed))) (av:p2 (cdr (assoc 11 ed)))))
    ((= typ "ARC")
     (setq c  (cdr (assoc 10 ed)) r (cdr (assoc 40 ed))
           a1 (cdr (assoc 50 ed)) a2 (cdr (assoc 51 ed)))
     (if (<= a2 a1) (setq a2 (+ a2 (* 2.0 pi))))
     (mapcar '(lambda (q) (av:wcs (list (car q) (cadr q) (caddr c)) ext))
             (cons (av:pol c a1 r) (av:arco-pts c r a1 (- a2 a1))))
    )
    ((= typ "CIRCLE")
     (setq c (cdr (assoc 10 ed)) r (cdr (assoc 40 ed)))
     (mapcar '(lambda (q) (av:wcs (list (car q) (cadr q) (caddr c)) ext))
             (cons (av:pol c 0.0 r) (av:arco-pts c r 0.0 (* 2.0 pi))))
    )
    ((= typ "LWPOLYLINE") (av:lwpoly-pts ed))
    ((member typ '("POLYLINE" "ELLIPSE" "SPLINE"))
     (vl-catch-all-apply 'av:curva-pts (list e)))
    (t nil)
  )
)

(defun av:fechada (pts tol)
  (and (> (length pts) 3) (< (av:dist (car pts) (av:ultimo pts)) tol))
)

;;; junta pecas abertas em aneis.  devolve (aneis . ok)
(defun av:encadeia (pecas tol / aneis cur ext ini fim ok)
  (setq aneis nil ok T)
  (while pecas
    (setq cur (car pecas) pecas (cdr pecas))
    (if (not (av:fechada cur tol))
      (progn
        (setq ext T)
        (while (and ext (not (av:fechada cur tol)))
          (setq ext nil ini (car cur) fim (av:ultimo cur))
          (foreach q pecas
            (if (not ext)
              (cond
                ((< (av:dist fim (car q)) tol)
                 (setq cur (append cur (cdr q)) ext q))
                ((< (av:dist fim (av:ultimo q)) tol)
                 (setq cur (append cur (cdr (reverse q))) ext q))
                ((< (av:dist ini (av:ultimo q)) tol)
                 (setq cur (append q (cdr cur)) ext q))
                ((< (av:dist ini (car q)) tol)
                 (setq cur (append (reverse q) (cdr cur)) ext q))
              )
            )
          )
          (if ext (setq pecas (av:remove1 ext pecas)))
        )
      )
    )
    (if (av:fechada cur tol)
      (setq aneis (cons cur aneis))
      (setq ok nil)
    )
  )
  (cons (reverse aneis) ok)
)

;;; anel: tira pontos repetidos e o ponto final igual ao inicial
(defun av:limpa-anel (pts / r)
  (setq r nil)
  (foreach p pts
    (if (or (null r) (> (av:dist p (car r)) 1e-9))
      (setq r (cons p r))
    )
  )
  (setq r (reverse r))
  (if (and (> (length r) 1) (< (av:dist (car r) (av:ultimo r)) 1e-9))
    (setq r (reverse (cdr (reverse r))))
  )
  r
)

(defun av:area (pts / s n i p q)
  (setq s 0.0 n (length pts) i 0)
  (while (< i n)
    (setq p (nth i pts) q (nth (rem (1+ i) n) pts)
          s (+ s (- (* (car p) (cadr q)) (* (car q) (cadr p))))
          i (1+ i))
  )
  (/ s 2.0)
)

;;; selecao -> lista de aneis (cada anel = lista de pontos, sem repeticao)
;;; devolve nil se nao houver contorno fechado
(defun av:aneis-da-selecao (ss / i pecas p r)
  (setq i 0 pecas nil)
  (while (< i (sslength ss))
    (setq p (av:peca (ssname ss i)))
    (if (and p (not (vl-catch-all-error-p p)) (> (length p) 1))
      (setq pecas (cons p pecas))
    )
    (setq i (1+ i))
  )
  (setq r (av:encadeia (reverse pecas) AV:TOL))
  (if (and (cdr r) (car r))
    (mapcar 'av:limpa-anel (car r))
    nil
  )
)

;;; ==========================================================================
;;;  4.  CORTES DAS BARRAS
;;; ==========================================================================

;;; converte aneis (x y) para arestas em (t u):  t = ao longo, u = perpendicular
(defun av:arestas (aneis th / c s edges n i p q)
  (setq c (cos th) s (sin th) edges nil)
  (foreach an aneis
    (setq n (length an) i 0)
    (while (< i n)
      (setq p (nth i an) q (nth (rem (1+ i) n) an))
      (setq edges (cons (list (+ (* (car p) c) (* (cadr p) s))
                              (+ (* (- (car p)) s) (* (cadr p) c))
                              (+ (* (car q) c) (* (cadr q) s))
                              (+ (* (- (car q)) s) (* (cadr q) c)))
                        edges))
      (setq i (1+ i))
    )
  )
  edges
)

;;; extensao perpendicular (umin umax) e ao longo (tmin tmax)
(defun av:extensao (edges / umin umax tmin tmax)
  (foreach e edges
    (foreach k '(0 2)
      (setq tmin (if tmin (min tmin (nth k e)) (nth k e))
            tmax (if tmax (max tmax (nth k e)) (nth k e))))
    (foreach k '(1 3)
      (setq umin (if umin (min umin (nth k e)) (nth k e))
            umax (if umax (max umax (nth k e)) (nth k e))))
  )
  (list umin umax tmin tmax)
)

;;; cortes da reta u = u0: lista de (ta tb sa sb) -- corda bruta [ta,tb] e
;;; recuos sa/sb (em unidades do desenho) pelo cobrimento "cov" (unidades)
(defun av:cortes (edges u0 cov / xs t1 u1 t2 u2 len sn r a b)
  (setq xs nil)
  (foreach e edges
    (setq t1 (car e) u1 (cadr e) t2 (caddr e) u2 (cadddr e))
    (if (or (and (<= u1 u0) (> u2 u0)) (and (<= u2 u0) (> u1 u0)))
      (progn
        (setq len (av:hyp (- t2 t1) (- u2 u1))
              sn  (/ (abs (- u2 u1)) len)
              xs  (cons (cons (+ t1 (* (/ (- u0 u1) (- u2 u1)) (- t2 t1)))
                              (/ cov (max sn 1e-3)))
                        xs))
      )
    )
  )
  (setq xs (vl-sort xs '(lambda (a b) (< (car a) (car b)))))
  (setq r nil)
  (while (and xs (cdr xs))
    (setq a (car xs) b (cadr xs) xs (cddr xs))
    (setq r (cons (list (car a) (car b) (cdr a) (cdr b)) r))
  )
  (reverse r)
)

;;; posicoes u das barras: devolve lista de u (unidades do desenho).
;;;   n = teto( largura / esp )  (largura TOTAL do contorno, como no modelo),
;;;   barras centradas, com o cobrimento respeitado nas bordas paralelas ao ferro.
;;;   Se n barras a "esp" nao couberem entre os cobrimentos, o espacamento e
;;;   reduzido (nunca aumentado).
(defun av:posicoes (umin umax cov esp / w a q n sp off i r)
  (setq w (- umax umin) a (- w (* 2.0 cov)) r nil)
  (if (and (> w 1e-9) (> a 1e-9))
    (progn
      (setq q (/ w esp) n (fix q))
      (if (> (- q n) 1e-9) (setq n (1+ n)))
      (if (< n 1) (setq n 1))
      (if (= n 1)
        (setq r (list (/ (+ umin umax) 2.0)))
        (progn
          (setq sp esp)
          (if (> (* (1- n) esp) (+ a 1e-9)) (setq sp (/ a (1- n))))
          (setq off (+ umin cov (/ (- a (* (1- n) sp)) 2.0)) i 0)
          (while (< i n)
            (setq r (cons (+ off (* i sp)) r) i (1+ i))
          )
          (setq r (reverse r))
        )
      )
    )
  )
  r
)

;;; ==========================================================================
;;;  5.  EMENDAS POR TRASPASSE
;;; ==========================================================================

;;; teto (inteiro)
(defun av:teto (v)
  (if (> v (fix v)) (1+ (fix v)) (fix v))
)

;;; monta a lista:  p1, (n - 2) x m, pn
(defun av:monta (p1 pn n m / r)
  (setq r (list pn))
  (repeat (- n 2) (setq r (cons m r)))
  (cons p1 r)
)

;;; centros das zonas de traspasse, medidos do inicio da barra (cm)
(defun av:zonas (pcs lap / a b r)
  (setq a 0.0 r nil)
  (foreach p (reverse (cdr (reverse pcs)))
    (setq b (+ a p)
          r (cons (- b (/ lap 2.0)) r)
          a (- b lap))
  )
  (reverse r)
)

;;; T se, espelhando a barra na vizinha (ALTER.), as zonas de traspasse das
;;; duas ficam afastadas de pelo menos "def" (centros a >= lap + def)
(defun av:alterna-ok (pcs tot lap def / za ok)
  (setq za (av:zonas pcs lap) ok T)
  (foreach ca za
    (foreach cb za
      (if (< (abs (- ca (- tot cb))) (- (+ lap def) 1e-6)) (setq ok nil))
    )
  )
  ok
)

;;; pedacos com o 1.o pedaco = p1, os seguintes com o comprimento comercial
;;; e o ultimo com o resto (+ lap).  O ultimo nunca fica menor que
;;; (gancho final + 2 lap): se o resto for pequeno, o anterior e encurtado.
(defun av:corta (tot p1 fim lcom lap / pcs rest ult lmin dd)
  (setq pcs (list p1) rest (- tot p1))
  (while (> (+ rest lap) lcom)
    (setq pcs  (cons lcom pcs)
          rest (- (+ rest lap) lcom))
  )
  (setq ult  (+ rest lap)
        lmin (av:int (+ fim lap lap)))
  (if (< ult lmin)
    (setq dd  (- lmin ult)
          pcs (cons (- (car pcs) dd) (cdr pcs))
          ult lmin)
  )
  (reverse (cons ult pcs))
)

;;; divide uma barra de comprimento total "tot" (cm, inteiro) em pedacos de
;;; no maximo "lcom", com traspasse "lap" entre pedacos consecutivos.
;;;   - o 1.o pedaco tem o comprimento COMERCIAL (1200), a nao ser que outro
;;;     valor seja informado em "pini" (0 = comercial); os do meio tambem
;;;     tem o comercial e o ultimo leva o resto + lap;
;;;   - alt = T: a barra vizinha usa os MESMOS pedacos em ordem inversa;
;;;     se as emendas das duas ficarem a menos de "def" uma da outra, o 1.o
;;;     pedaco e encurtado de 10 em 10 cm ate desencontrarem.
;;;   ini / fim = ganchos (perna + ponta) no inicio / no fim
;;; devolve a lista dos pedacos (inteiros) na ordem da barra;
;;; soma dos pedacos = tot + (n - 1) x lap
(defun av:divide (tot ini fim lcom lap def pini alt / p1 pcs pmin)
  (if (<= tot lcom)
    (list tot)
    (progn
      (setq p1   (if (and pini (> pini 0)) (min pini lcom) lcom)
            pmin (av:int (+ ini lap lap)))
      (if (< p1 pmin) (setq p1 pmin))
      (setq pcs (av:corta tot p1 fim lcom lap))
      (if alt
        (while (and (not (av:alterna-ok pcs tot lap def))
                    (>= (- p1 10) pmin))
          (setq p1  (- p1 10)
                pcs (av:corta tot p1 fim lcom lap))
        )
      )
      pcs
    )
  )
)

;;; pedacos da barra vizinha (ALTER.): ordem inversa; se os ganchos das
;;; pontas forem diferentes, corrige o 1.o e o ultimo pedaco
(defun av:inverte (pcs ini fim / r)
  (setq r (reverse pcs))
  (if (and (cdr r) (/= ini fim))
    (setq r (av:setnth (av:setnth r 0 (av:int (+ (car r) (- ini fim))))
                       (1- (length r))
                       (av:int (+ (av:ultimo r) (- fim ini)))))
  )
  r
)

;;; ==========================================================================
;;;  6.  TEXTOS PADRAO E TABELAS
;;; ==========================================================================

;;; "(2X) " para rep > 1
(defun av:rep-txt (rep)
  (if (> rep 1) (strcat "(" (itoa rep) "X) ") "")
)

;;; posicao: 1 -> "N.1";  uma string ("N.1 N.2") e usada como esta
(defun av:ptxt (pos)
  (if (= (type pos) 'STR) pos (strcat "N." (itoa pos)))
)

;;; ferro:        (2X) N.1 87 %%c 8 C/15 C=VAR
(defun av:txt-ferro (rep pos n bit esp ctxt)
  (strcat (av:rep-txt rep) (av:ptxt pos) " " (itoa n)
          " %%c " bit " C/" (av:fmt esp) " C=" ctxt)
)

;;; distribuicao: 87 (2X) N.1 %%c 8 C/15
(defun av:txt-faixa (rep pos n bit esp)
  (strcat (itoa n) " " (av:rep-txt rep) (av:ptxt pos)
          " %%c " bit " C/" (av:fmt esp))
)

;;; titulo da tabela: (2X) N.1 87 %%c 8 C/15   (sem o "C=")
(defun av:titulo-barra (rep pos n bit esp)
  (strcat (av:rep-txt rep) (av:ptxt pos) " " (itoa n)
          " %%c " bit " C/" (av:fmt esp))
)

;;; tabela de ferros variaveis
;;;   p0 = canto superior esquerdo da moldura;  nota = texto abaixo (ou nil)
;;;   QTD. de cada linha ja multiplicada pelas REPETICOES (simetria = 2X): a
;;;   soma das linhas e o total de barras da posicao
;;;   rots = rotulos das linhas (ex.: ("N1" "N2")), ou nil -> N1A, N1B, ...
(defun av:tab-ferros (p0 h pos pref rep bit esp grupos nbar nota rots
                      / n x0 y0 wd ht y i yh xg)
  (setq n (length grupos)
        x0 (car p0) y0 (cadr p0)
        wd (* 22.0 h)
        ht (+ (* 1.5 h) (* 1.5 h n) (* 1.0 h))
        yh (- y0 (* 1.5 h)))
  ;; titulo acima da moldura
  (av:mk-text (av:titulo-barra rep pos nbar bit esp)
              (list (+ x0 (* 1.0 h)) (+ y0 (* 0.5 h))) h 0.0 AV:LAY-TXT nil)
  (setq AV:TAG "T1")
  (av:mk-pline (list (list x0 y0) (list (+ x0 wd) y0)
                     (list (+ x0 wd) (- y0 ht)) (list x0 (- y0 ht)))
               AV:LAY-TAB T)
  (setq AV:TAG nil)
  ;; cabecalho das colunas
  (av:mk-text "POS." (list (+ x0 (* 1.0 h)) (- y0 (* 1.2 h))) h 0.0 AV:LAY-TXT nil)
  (av:mk-text "QTD." (list (+ x0 (* 9.0 h)) (- y0 (* 1.2 h))) h 0.0 AV:LAY-TXT nil)
  (av:mk-text "C (cm)" (list (+ x0 (* 15.0 h)) (- y0 (* 1.2 h))) h 0.0 AV:LAY-TXT nil)
  (av:mk-line (list x0 yh) (list (+ x0 wd) yh) AV:LAY-TAB nil nil)
  ;; grade das colunas
  (foreach xg '(5.5 13.6)
    (av:mk-line (list (+ x0 (* xg h)) yh) (list (+ x0 (* xg h)) (- y0 ht))
                AV:LAY-GRADE nil nil)
  )
  ;; linhas
  (setq i 0 y (- y0 (* 3.0 h)))
  (foreach g grupos
    (av:mk-text (if rots (av:nth i rots) (strcat pref (av:letra i)))
                (list (+ x0 (* 1.0 h)) y) h 0.0 AV:LAY-TXT nil)
    ;; quantidade ja multiplicada pelas repeticoes (simetria: 2X)
    (av:mk-text (itoa (* (max 1 rep) (cdr g)))
                (list (+ x0 (* 9.0 h)) y) h 0.0 AV:LAY-TXT nil)
    (av:mk-text (itoa (car g))
                (list (+ x0 (* 15.0 h)) y) h 0.0 AV:LAY-TXT nil)
    (setq y (- y (* 1.5 h)) i (1+ i))
  )
  ;; observacao (emendas)
  (if nota
    (av:mk-text nota (list x0 (- y0 ht (* 1.5 h))) (* 0.9 h) 0.0 AV:LAY-TXT nil)
  )
)

;;; tabela com o COMPRIMENTO UNITARIO EQUIVALENTE (como a LISTA DE FERROS da
;;; prancha modelo):  POS. | %%c | QTD. | C.UNIT (cm) | C.TOTAL (cm)
;;;   C.UNIT = C.TOTAL / QTD  (ex.: 111388 / 174 = 640)
;;;   linhas = ((pos qtd ctot) ...)  -- uma por posicao
(defun av:tab-equiv (p0 h pos rep bit esp nbar linhas nota
                     / x0 y0 wd ht yh xg c y ln)
  (setq x0 (car p0) y0 (cadr p0)
        wd (* 36.0 h) ht (+ (* 2.5 h) (* 1.5 h (length linhas)))
        yh (- y0 (* 1.5 h)))
  (av:mk-text (av:titulo-barra rep pos nbar bit esp)
              (list (+ x0 (* 1.0 h)) (+ y0 (* 0.5 h))) h 0.0 AV:LAY-TXT nil)
  (setq AV:TAG "T1")
  (av:mk-pline (list (list x0 y0) (list (+ x0 wd) y0)
                     (list (+ x0 wd) (- y0 ht)) (list x0 (- y0 ht)))
               AV:LAY-TAB T)
  (setq AV:TAG nil)
  (foreach c (list (list 1.0 "POS.") (list 7.0 "%%c (mm)") (list 12.0 "QTD.")
                   (list 18.0 "C.UNIT (cm)") (list 27.0 "C.TOTAL (cm)"))
    (av:mk-text (cadr c) (list (+ x0 (* (car c) h)) (- y0 (* 1.2 h))) h 0.0
                AV:LAY-TXT nil)
  )
  (av:mk-line (list x0 yh) (list (+ x0 wd) yh) AV:LAY-TAB nil nil)
  (foreach xg '(6.0 11.0 17.0 26.0)
    (av:mk-line (list (+ x0 (* xg h)) yh) (list (+ x0 (* xg h)) (- y0 ht))
                AV:LAY-GRADE nil nil)
  )
  (setq y (- y0 (* 3.0 h)))
  (foreach ln linhas
    (foreach c (list (list 1.0 (car ln)) (list 7.0 bit) (list 12.0 (itoa (cadr ln)))
                     (list 18.0 (itoa (av:int (/ (caddr ln) (cadr ln)))))
                     (list 27.0 (av:fmt (caddr ln))))
      (av:mk-text (cadr c) (list (+ x0 (* (car c) h)) y) h 0.0 AV:LAY-TXT nil)
    )
    (setq y (- y (* 1.5 h)))
  )
  (if nota
    (av:mk-text nota (list x0 (- y0 ht (* 1.5 h))) (* 0.9 h) 0.0 AV:LAY-TXT nil)
  )
)

;;; resumo de aco:  linhas = ((pos qtd ctot) ...)  -- uma por posicao
(defun av:tab-aco (p0 h linhas bit aco kgm / x0 y0 wd ht n y ln mt m c)
  (setq n  (length linhas)
        x0 (car p0) y0 (cadr p0)
        wd (* 47.0 h) ht (+ (* 6.5 h) (* 1.5 h (1- n)))
        mt 0.0)
  (av:mk-text (strcat "RESUMO DE A" (chr 199) "O  -  " aco)
              (list (+ x0 (* 1.0 h)) (+ y0 (* 0.5 h))) h 0.0 AV:LAY-TXT nil)
  (setq AV:TAG "T2")
  (av:mk-pline (list (list x0 y0) (list (+ x0 wd) y0)
                     (list (+ x0 wd) (- y0 ht)) (list x0 (- y0 ht)))
               AV:LAY-TAB T)
  (setq AV:TAG nil)
  ;; cabecalho
  (foreach c (list (list 1.0 "POS.") (list 8.0 "%%c (mm)") (list 16.0 "QTD.")
                   (list 22.0 "C.TOTAL (m)") (list 36.0 "PESO (kg)"))
    (av:mk-text (cadr c) (list (+ x0 (* (car c) h)) (- y0 (* 1.2 h))) h 0.0
                AV:LAY-TXT nil)
  )
  (av:mk-line (list x0 (- y0 (* 1.5 h))) (list (+ x0 wd) (- y0 (* 1.5 h)))
              AV:LAY-TAB nil nil)
  ;; uma linha por posicao
  (setq y (- y0 (* 3.0 h)))
  (foreach ln linhas
    (setq m (/ (caddr ln) 100.0) mt (+ mt m))
    (foreach c (list (list 1.0 (car ln)) (list 8.0 bit) (list 16.0 (itoa (cadr ln)))
                     (list 22.0 (rtos m 2 2)) (list 36.0 (rtos (* m kgm) 2 1)))
      (av:mk-text (cadr c) (list (+ x0 (* (car c) h)) y) h 0.0 AV:LAY-TXT nil)
    )
    (setq y (- y (* 1.5 h)))
  )
  ;; total
  (setq y (+ y (* 1.0 h)))
  (av:mk-line (list x0 y) (list (+ x0 wd) y) AV:LAY-TAB nil nil)
  (foreach c (list (list 1.0 "TOTAL") (list 22.0 (rtos mt 2 2))
                   (list 36.0 (rtos (* mt kgm) 2 1)))
    (av:mk-text (cadr c) (list (+ x0 (* (car c) h)) (- y (* 1.5 h))) h 0.0
                AV:LAY-TXT nil)
  )
)

;;; ==========================================================================
;;;  7.  DESENHO DO FERRO
;;; ==========================================================================

;;; (t,u) -> (x y)
(defun av:tu (th tt uu)
  (list (- (* tt (cos th)) (* uu (sin th)))
        (+ (* tt (sin th)) (* uu (cos th))))
)

;;; (x y) -> (t u)
(defun av:xy-tu (p th)
  (list (+ (* (car p) (cos th)) (* (cadr p) (sin th)))
        (+ (* (- (car p)) (sin th)) (* (cadr p) (cos th))))
)

;;; desenha UM ferro (positivo ou negativo), ja dividido nos pedacos "pcs".
;;;   u      = posicao perpendicular do trecho principal
;;;   qa,qb  = extremos do trecho principal (t), ja com cobrimento
;;;   sg     = +1/-1: lado (em u) para onde vao as pernas
;;;   sh     = deslocamento ao longo do ferro (t)
;;;   off    = deslocamento (u) dos pedacos de ordem impar (emendas)
;;; pontos da PERNA desenhada a partir do canto (x u), em (t u) do desenho.
;;;   L = comprimento desenhado; ang = angulo de REPRESENTACAO (rad) medido a
;;;   partir do prolongamento da barra: 90 = perpendicular (no plano),
;;;   45 = inclinada para fora (entrando na tela), 135 = inclinada para
;;;   dentro (saindo da tela), 180 = dobrada para tras, paralela a barra, ao
;;;   lado dela (gancho).  fim = T na extremidade final.  Devolve a lista de
;;;   pontos do canto para fora (sem o canto).
(defun av:perna-pts (x u L ang sg fim / s c dt g)
  (setq s (sin ang) c (cos ang))
  (if (< (abs c) 1e-9) (setq c 0.0 s (if (> s 0.0) 1.0 -1.0)))
  (setq dt (* (if fim 1.0 -1.0) L c)
        g (if AV:GAP AV:GAP (* 0.15 L)))
  (cond
    ((>= (abs s) 0.05) (list (list (+ x dt) (+ u (* sg L s)))))
    ((< c 0.0)
     ;; 180: volta paralela a barra, afastada g para o lado da perna
     (list (list x (+ u (* sg g))) (list (+ x dt) (+ u (* sg g)))))
    (t (list (list (+ x dt) u))))
)
;;; lado para afastar o texto da perna: para fora da barra (fora) se a perna
;;; nao for paralela a barra; na de 180 (paralela), para o lado do gancho
(defun av:fora-perna (a b fora hk / v l)
  (setq v (list (- (car b) (car a)) (- (cadr b) (cadr a))) l (av:hyp (car v) (cadr v)))
  (if (and (> l 1e-9) (> (abs (av:dot (list (/ (car v) l) (/ (cadr v) l)) fora)) 0.95)) hk fora)
)

;;; angulo de desenho de uma perna (rad); padrao 90
(defun av:ang-perna (hooks i / a) (if (setq a (av:nth i hooks)) a (/ pi 2.0)))

(defun av:ferro (th u qa qb hooks sg uc pcs lap sh off lay lt lts
                 / l1 t1 l2 t2 ini n k a b ka kb uu ul pts p lp)
  (setq l1 (nth 0 hooks) t1 (nth 1 hooks) l2 (nth 2 hooks) t2 (nth 3 hooks)
        ini (+ l1 t1) n (length pcs) k 0 a 0.0)
  (foreach p pcs
    (setq b  (+ a p)
          ka (if (= k 0) qa (+ qa (/ (- a ini) uc)))
          kb (if (= k (1- n)) qb (+ qa (/ (- b ini) uc)))
          uu (if (= (rem k 2) 1) (+ u off) u)
          pts (list (list (+ ka sh) uu) (list (+ kb sh) uu)))
    ;; gancho inicial (so no 1.o pedaco): perna no angulo de desenho + ponta
    (if (and (= k 0) (> l1 0.0))
      (progn
        (setq lp (av:perna-pts (+ ka sh) uu (/ l1 uc) (av:ang-perna hooks 4) sg nil)
              ul (av:ultimo lp))
        (if (> t1 0.0)
          (setq lp (append lp (list (list (+ (car ul) (/ t1 uc)) (cadr ul))))))
        (setq pts (append (reverse lp) pts))
      )
    )
    ;; gancho final (so no ultimo pedaco)
    (if (and (= k (1- n)) (> l2 0.0))
      (progn
        (setq lp (av:perna-pts (+ kb sh) uu (/ l2 uc) (av:ang-perna hooks 5) sg T)
              ul (av:ultimo lp))
        (if (> t2 0.0)
          (setq lp (append lp (list (list (- (car ul) (/ t2 uc)) (cadr ul))))))
        (setq pts (append pts lp))
      )
    )
    (av:mk-pl (mapcar '(lambda (q) (av:tu th (car q) (cadr q))) pts)
              lay nil lt lts nil)
    (setq AV:TAG nil)          ; "FP" so no 1.o pedaco
    (setq a (- b lap) k (1+ k))
  )
)

;;; cota linear paralela ao ferro (traspasse), com tiques e linhas de
;;; chamada.  ka,kb = extremos (t); ul = posicao da linha (u);
;;; ub = inicio das linhas de chamada (u); sd = +1/-1 lado de fora (u)
(defun av:cota (th ka kb ul ub sd h txt / d nrm fora)
  (if (not (av:mk-dim (av:tu th ka ub) (av:tu th kb ub) (av:tu th ka ul) th txt h 2 nil))
    (av:cota-manual th ka kb ul ub sd h txt))
)

;;; a mesma cota desenhada com linhas, tiques e texto (CAD sem ActiveX)
(defun av:cota-manual (th ka kb ul ub sd h txt / d nrm fora)
  (setq d    (list (cos th) (sin th))
        nrm  (list (- (sin th)) (cos th))
        fora (list (* sd (car nrm)) (* sd (cadr nrm))))
  (av:mk-line (av:tu th (- ka (* 0.75 h)) ul) (av:tu th (+ kb (* 0.75 h)) ul)
              AV:LAY-COTA nil nil)
  (av:mk-line (av:tu th ka ub) (av:tu th ka (+ ul (* sd 0.75 h))) AV:LAY-COTA nil nil)
  (av:mk-line (av:tu th kb ub) (av:tu th kb (+ ul (* sd 0.75 h))) AV:LAY-COTA nil nil)
  (av:tique (av:tu th ka ul) d h AV:LAY-COTA)
  (av:tique (av:tu th kb ul) d h AV:LAY-COTA)
  (av:rotulo txt (av:tu th (/ (+ ka kb) 2.0) ul) th fora (* 0.9 h) AV:LAY-COTA)
  (av:cor-ultimo AV:COR-TXT-COTA)
)

;;; cota linear REAL (entidade DIMENSION, rotacionada), layer EST_Cota,
;;; com tiques (arch tick) e o texto "txt" no lugar do valor medido.
;;;   p1,p2 = pontos de definicao;  ploc = ponto da linha de cota
;;;   ang   = angulo da linha de cota;  vpos = 1 texto acima / 2 do lado de
;;;           fora (longe dos pontos);  sup = T suprime as linhas de chamada
;;;   Na string "txt", "\X" separa o texto de cima e o de baixo da linha.
;;; devolve o objeto, ou nil se o CAD nao aceitar (usa-se o desenho manual)
(defun av:mk-dim (p1 p2 ploc ang txt h vpos sup / spc d s1 s2)
  ;; sup = T/nil (as duas linhas de chamada) ou (s1 s2) (cada uma)
  (setq s1 (if (listp sup) (car sup) sup)
        s2 (if (listp sup) (cadr sup) sup))
  (setq spc (vl-catch-all-apply
              '(lambda ()
                 (vla-get-Block (vla-get-ActiveLayout
                                  (vla-get-ActiveDocument (vlax-get-acad-object)))))
              nil))
  (if (not (vl-catch-all-error-p spc))
    (setq d (vl-catch-all-apply 'vla-AddDimRotated
              (list spc
                    (vlax-3d-point (list (car p1) (cadr p1) 0.0))
                    (vlax-3d-point (list (car p2) (cadr p2) 0.0))
                    (vlax-3d-point (list (car ploc) (cadr ploc) 0.0))
                    ang)))
  )
  (if (or (null d) (vl-catch-all-error-p d))
    nil
    (progn
      (foreach pr (list (list 'vla-put-Layer AV:LAY-COTA)
                        (list 'vla-put-ScaleFactor 1.0)
                        (list 'vla-put-TextStyle AV:STY)
                        (list 'vla-put-TextHeight (* 0.9 h))
                        (list 'vla-put-TextGap (* 0.3 h))
                        (list 'vla-put-Arrowhead1Type 4)        ; arch tick
                        (list 'vla-put-Arrowhead2Type 4)
                        (list 'vla-put-ArrowheadSize (* 0.6 h))
                        (list 'vla-put-DimensionLineExtend (* 0.75 h))
                        (list 'vla-put-ExtensionLineExtend (* 0.75 h))
                        (list 'vla-put-ExtensionLineOffset (* 0.2 h))
                        (list 'vla-put-VerticalTextPosition vpos)
                        (list 'vla-put-ForceLineInside :vlax-true)
                        (list 'vla-put-DimensionLineColor 256)  ; PorLayer
                        (list 'vla-put-ExtensionLineColor 256)
                        (list 'vla-put-TextColor AV:COR-TXT-COTA) ; texto white
                        (list 'vla-put-ExtLine1Suppress (if s1 :vlax-true :vlax-false))
                        (list 'vla-put-ExtLine2Suppress (if s2 :vlax-true :vlax-false))
                        (list 'vla-put-TextOverride txt))
        (vl-catch-all-apply (car pr) (list d (cadr pr)))
      )
      (vl-catch-all-apply 'av:xd-ent (list (vlax-vla-object->ename d)))
      d
    )
  )
)

;;; um texto do ferro por pedaco (posicoes separadas N.1, N.2...), centrado
;;; em cada pedaco, do lado "away"
(defun av:rot-espec (th uu ta tb pcs ini uc lap away h textos / n k a b ka kb p)
  (setq n (length pcs) k 0 a 0.0)
  (foreach p pcs
    (setq b  (+ a p)
          ka (if (= k 0) ta (+ ta (/ (- a ini) uc)))
          kb (if (= k (1- n)) tb (+ ta (/ (- b ini) uc))))
    (if (av:nth k textos)
      (av:rotulo (av:nth k textos) (av:tu th (/ (+ ka kb) 2.0) uu) th away h AV:LAY-ESPEC))
    (setq a (- b lap) k (1+ k))
  )
)

;;; posicao (u) da linha do ferro no ponto "tt": os pedacos de ordem impar
;;; sao desenhados deslocados de "off"; na zona de traspasse vale o pedaco par
(defun av:u-pedaco (tt u ta tb pcs ini uc lap off / n k a b ka kb r p)
  (setq n (length pcs) k 0 a 0.0 r nil)
  (foreach p pcs
    (setq b  (+ a p)
          ka (if (= k 0) ta (+ ta (/ (- a ini) uc)))
          kb (if (= k (1- n)) tb (+ ta (/ (- b ini) uc))))
    (if (and (>= tt (- ka 1e-9)) (<= tt (+ kb 1e-9))
             (or (null r) (= (rem k 2) 0)))
      (setq r (if (= (rem k 2) 1) (+ u off) u)))
    (setq a (- b lap) k (1+ k))
  )
  (if r r u)
)

;;; cotas dos traspasses de um ferro desenhado em "uu" (lado oposto aos
;;; ganchos, sg = lado dos ganchos)
(defun av:cotas-trasp (th uu ta pcs ini uc lap sg h / k a b)
  (setq k 0 a 0.0)
  (while (< k (1- (length pcs)))
    (setq b (+ a (nth k pcs)))
    (av:cota th (+ ta (/ (- b lap ini) uc)) (+ ta (/ (- b ini) uc))
             (- uu (* sg 2.8 h)) (- uu (* sg 0.5 h)) (- sg) h (av:fmt lap))
    (setq a (- b lap) k (1+ k))
  )
)

;;; comprimento reto de cada pedaco (sem os ganchos), escrito no centro do
;;; pedaco, do lado "away" (como "885" e "445" no detalhe de parede)
(defun av:rot-pedacos (th uu ta tb pcs ini fim uc lap away h / n k a b ka kb c p)
  (setq n (length pcs) k 0 a 0.0)
  (foreach p pcs
    (setq b  (+ a p)
          ka (if (= k 0) ta (+ ta (/ (- a ini) uc)))
          kb (if (= k (1- n)) tb (+ ta (/ (- b ini) uc)))
          c  (- p (if (= k 0) ini 0.0) (if (= k (1- n)) fim 0.0)))
    (av:rotulo (av:fmt c) (av:tu th (/ (+ ka kb) 2.0) uu) th away h AV:LAY-TXT)
    (setq a (- b lap) k (1+ k))
  )
)

;;; desenha o ferro (e a barra simetrica invertida), os textos e a faixa.
;;;   th    = direcao;  ud = posicao perpendicular (u) do ferro desenhado
;;;   ta,tb = extremos do trecho principal (JA com cobrimento), em t
;;;   lo,hi = limites da faixa de distribuicao (u);  tdim = t da faixa
;;;   espec = texto do ferro;  faixa = texto da faixa;  wtxt = "(1300)"
;;;   mtxt  = texto do trecho principal ("VAR" ou o valor)
;;;   pcs   = pedacos (cm) da barra representada;  neg = T -> simetrica
;;;   pcsa  = pedacos da barra vizinha alternada (ALTER.) ou nil
;;;   atxt  = texto do desenho ALTER.
;;;   espl  = textos do ferro por pedaco (posicoes separadas) ou nil
;;;   anc   = (vlo vhi): vertices (t u) onde ancorar as linhas de extensao
;;;           da faixa (cada um pode ser nil)
;;;   chama = (t u) do ponto da linha de chamada, ou nil (automatico); so e
;;;           usado quando a faixa de distribuicao NAO cruza o ferro
(defun av:desenha (th ud ta tb lo hi tdim hooks lado h uc espec faixa wtxt
                   mtxt pcs neg lap pcsa atxt chama anc espl
                   / sg l1 t1 l2 t2 ini fim emd tc d nrm hk dneg p0 leg1 tip1 lp1 lp2
                     p1 leg2 tip2 uvar ues ualt rot up mid lts ucir tcir uq alo ahi av)
  (setq sg  (if (= lado 0) -1.0 1.0)       ; direita = -u, esquerda = +u
        l1 (nth 0 hooks) t1 (nth 1 hooks) l2 (nth 2 hooks) t2 (nth 3 hooks)
        ini (+ l1 t1)
        fim (+ l2 t2)
        emd (> (length pcs) 1)
        tc  (/ (+ ta tb) 2.0)
        d   (list (cos th) (sin th))
        nrm (list (- (sin th)) (cos th))
        hk  (list (* sg (car nrm)) (* sg (cadr nrm)))
        ;; afastamento da barra invertida: perna + folga (min. 1 texto)
        dneg (max (+ (/ (max l1 l2) uc) (* 0.35 h)) h)
        lts (av:ltscale)
        ;; folga do desenho da perna dobrada a 180 graus (gancho)
        AV:GAP (* 0.4 h))

  ;; --- ferro positivo (continuo) ----------------------------------------
  (setq AV:TAG "FP")
  (av:ferro th ud ta tb hooks sg uc pcs lap 0.0 (* -0.3 h sg)
            AV:LAY-BAR nil nil)
  (setq AV:TAG nil)

  ;; --- barra simetrica invertida (negativa, tracejada) -------------------
  ;;     espelhada: pernas voltadas para o ferro positivo, ao lado dele.
  ;;     Com emendas alternadas ela mostra os pedacos na ordem INVERSA
  ;;     (emendas desencontradas entre as duas barras).
  (if neg
    (av:ferro th (+ ud (* sg dneg)) ta tb hooks (- sg) uc
              (if (and emd pcsa) pcsa pcs) lap
              (* 0.2 h) (* 0.3 h sg)
              AV:LAY-NEG AV:LT-NOME (/ (* 0.5 h) lts))
  )

  ;; --- rotulos de cada trecho (geometria do positivo) --------------------
  (setq p0 (av:tu th ta ud)
        p1 (av:tu th tb ud))
  ;; pernas no angulo de desenho: p0/p1 passam a ser o inicio do trecho da
  ;; perna (no gancho de 180, o ponto afastado da barra)
  (if (> l1 0.0)
    (progn
      (setq lp1 (av:perna-pts ta ud (/ l1 uc) (av:ang-perna hooks 4) sg nil)
            leg1 (av:tu th (car (av:ultimo lp1)) (cadr (av:ultimo lp1))))
      (if (cdr lp1) (setq p0 (av:tu th (car (car lp1)) (cadr (car lp1)))))
      (if (> t1 0.0)
        (setq tip1 (av:tu th (+ (car (av:ultimo lp1)) (/ t1 uc)) (cadr (av:ultimo lp1)))))
    )
  )
  (if (> l2 0.0)
    (progn
      (setq lp2 (av:perna-pts tb ud (/ l2 uc) (av:ang-perna hooks 5) sg T)
            leg2 (av:tu th (car (av:ultimo lp2)) (cadr (av:ultimo lp2))))
      (if (cdr lp2) (setq p1 (av:tu th (car (car lp2)) (cadr (car lp2)))))
      (if (> t2 0.0)
        (setq tip2 (av:tu th (- (car (av:ultimo lp2)) (/ t2 uc)) (cadr (av:ultimo lp2)))))
    )
  )
  ;; trecho principal: do lado das pernas (alem da barra invertida)
  (setq uvar (if neg
               (+ ud (* sg (+ dneg (if emd (* 0.3 h) 0.0))))
               ud))
  ;; com emendas e comprimento constante: o comprimento de cada pedaco
  (if (and emd (/= mtxt "VAR"))
    (av:rot-pedacos th uvar ta tb pcs ini fim uc lap hk h)
    (av:rotulo mtxt (av:tu th tc uvar) th hk h AV:LAY-TXT)
  )
  (if leg1
    (progn
      (if (cdr lp1)
        ;; gancho de 180: cota da perna na dobra, por fora (nao bate na ponta)
        (av:rotulo (av:fmt l1) (list (/ (+ (car p0) (car (av:tu th ta ud))) 2.0)
                                     (/ (+ (cadr p0) (cadr (av:tu th ta ud))) 2.0))
                   (angle '(0.0 0.0) hk) (list (- (car d)) (- (cadr d))) h AV:LAY-TXT)
        (av:rotulo (av:fmt l1) (list (/ (+ (car p0) (car leg1)) 2.0)
                                     (/ (+ (cadr p0) (cadr leg1)) 2.0))
                   (angle p0 leg1) (av:fora-perna p0 leg1 (list (- (car d)) (- (cadr d))) hk) h AV:LAY-TXT))
      (if tip1
        (av:rotulo (av:fmt t1) (list (/ (+ (car leg1) (car tip1)) 2.0)
                                     (/ (+ (cadr leg1) (cadr tip1)) 2.0))
                   th hk h AV:LAY-TXT)
      )
    )
  )
  (if leg2
    (progn
      (if (cdr lp2)
        (av:rotulo (av:fmt l2) (list (/ (+ (car p1) (car (av:tu th tb ud))) 2.0)
                                     (/ (+ (cadr p1) (cadr (av:tu th tb ud))) 2.0))
                   (angle '(0.0 0.0) hk) d h AV:LAY-TXT)
        (av:rotulo (av:fmt l2) (list (/ (+ (car p1) (car leg2)) 2.0)
                                     (/ (+ (cadr p1) (cadr leg2)) 2.0))
                   (angle p1 leg2) (av:fora-perna p1 leg2 d hk) h AV:LAY-TXT))
      (if tip2
        (av:rotulo (av:fmt t2) (list (/ (+ (car leg2) (car tip2)) 2.0)
                                     (/ (+ (cadr leg2) (cadr tip2)) 2.0))
                   th hk h AV:LAY-TXT)
      )
    )
  )

  ;; --- texto do ferro: centrado, do lado oposto aos ganchos --------------
  (setq ues (- ud (* sg (if emd (* 0.3 h) 0.0))))
  (setq AV:TAG "ESP")
  (if espl
    ;; posicoes separadas: um texto centrado em cada pedaco
    (av:rot-espec th ues ta tb pcs ini uc lap (list (- (car hk)) (- (cadr hk))) h espl)
    (av:rotulo espec (av:tu th tc ues) th (list (- (car hk)) (- (cadr hk)))
               h AV:LAY-ESPEC)
  )
  (setq AV:TAG nil)

  ;; --- cotas dos traspasses (do lado oposto aos ganchos) -----------------
  (if emd (av:cotas-trasp th ud ta pcs ini uc lap sg h))

  ;; --- sem simetria: barra vizinha ALTERNADA desenhada ao lado ------------
  ;;     (com simetria a alternancia ja aparece na barra tracejada)
  (if (and emd pcsa (not neg))
    (progn
      (setq ualt (- ud (* sg 8.0 h)))
      (av:ferro th ualt ta tb hooks sg uc pcsa lap 0.0 (* -0.3 h sg)
                AV:LAY-BAR nil nil)
      (if (/= mtxt "VAR")
        (av:rot-pedacos th (+ ualt (* sg 0.3 h)) ta tb pcsa ini fim uc lap hk h)
      )
      (av:rotulo atxt (av:tu th tc (- ualt (* sg 0.3 h))) th
                 (list (- (car hk)) (- (cadr hk))) h AV:LAY-ESPEC)
      (av:cotas-trasp th ualt ta pcsa ini uc lap sg h)
    )
  )

  ;; --- linha de distribuicao: COTA (EST_Cota) ---------------------------
  ;;     "87 (2X) N.1 %%c 8 C/15" acima  e  "(1300)" abaixo da linha.
  ;;     anc = (vertice-lo vertice-hi), em (t u): a ponta com vertice ganha
  ;;     linha de extensao ate ele; sem vertice, a linha fica suprimida.
  (setq alo (car anc) ahi (cadr anc))
  (if (not (av:mk-dim (if alo (av:tu th (car alo) (cadr alo)) (av:tu th tdim lo))
                      (if ahi (av:tu th (car ahi) (cadr ahi)) (av:tu th tdim hi))
                      (av:tu th tdim lo)
                      (+ th (/ pi 2.0)) (strcat faixa "\\X" wtxt) h 1
                      (list (null alo) (null ahi))))
    (progn
      (foreach av (list (list alo lo) (list ahi hi))
        (if (car av)
          (av:mk-line (av:tu th (+ (car (car av)) (* (if (> tdim (car (car av))) 0.2 -0.2) h))
                             (cadr (car av)))
                      (av:tu th (+ tdim (* (if (> tdim (car (car av))) 0.75 -0.75) h))
                             (cadr (car av)))
                      AV:LAY-COTA nil nil))
      )
      (av:mk-line (av:tu th tdim (- lo (* 0.75 h))) (av:tu th tdim (+ hi (* 0.75 h)))
                  AV:LAY-COTA nil nil)
      (av:tique (av:tu th tdim lo) nrm h AV:LAY-COTA)
      (av:tique (av:tu th tdim hi) nrm h AV:LAY-COTA)
      (setq rot (av:leitura (+ th (/ pi 2.0)))
            up  (list (- (sin rot)) (cos rot))
            mid (av:tu th tdim (/ (+ lo hi) 2.0)))
      (av:mk-text faixa (av:mad mid up (* 0.7 h)) (* 0.9 h) rot AV:LAY-COTA T)
      (av:cor-ultimo AV:COR-TXT-COTA)
      (av:mk-text wtxt  (av:mad mid up (* -1.6 h)) (* 0.9 h) rot AV:LAY-COTA T)
      (av:cor-ultimo AV:COR-TXT-COTA)
    )
  )

  ;; --- indicacao: circulos SOBRE o ferro (no pedaco que a faixa cruza) e
  ;;     chamada tracejada ate a faixa ------------------------------------
  (if (and (>= tdim (- ta 1e-9)) (<= tdim (+ tb 1e-9)))
    (progn
      (setq ucir (av:u-pedaco tdim ud ta tb pcs ini uc lap (* -0.3 h sg)))
      (av:mk-circ (av:tu th tdim ucir) (* 0.225 h) AV:LAY-IND)
      (av:mk-circ (av:tu th tdim ucir) (* 0.375 h) AV:LAY-IND)
      (cond
        ((< ucir (- lo 1e-9))
         (av:mk-line (av:tu th tdim lo) (av:tu th tdim (+ ucir (* 0.375 h)))
                     AV:LAY-IND AV:LT-NOME (/ h lts)))
        ((> ucir (+ hi 1e-9))
         (av:mk-line (av:tu th tdim hi) (av:tu th tdim (- ucir (* 0.375 h)))
                     AV:LAY-IND AV:LT-NOME (/ h lts)))
      )
    )
    ;; faixa FORA do ferro: bolinha sobre o ferro e linha de chamada em "L"
    ;; (perpendicular ao ferro e depois paralela a ele) ate a faixa
    (progn
      (setq tcir (if chama
                   (max ta (min tb (car chama)))
                   (if (< tdim ta)
                     (min tb (+ ta (* 6.0 h)))
                     (max ta (- tb (* 6.0 h)))))
            ucir (av:u-pedaco tcir ud ta tb pcs ini uc lap (* -0.3 h sg)))
      ;; trecho paralelo: dentro da faixa (senao nao encontra a linha)
      (if chama
        (setq uq (max lo (min hi (cadr chama))))
        (progn
          (setq uq (max lo (min hi (- ucir (* sg 3.0 h)))))
          (if (< (abs (- uq ucir)) (* 2.0 h))
            (setq uq (max lo (min hi (+ ucir (* sg 3.0 h))))))
        )
      )
      (av:mk-circ (av:tu th tcir ucir) (* 0.225 h) AV:LAY-IND)
      (av:mk-circ (av:tu th tcir ucir) (* 0.375 h) AV:LAY-IND)
      (if (> (abs (- uq ucir)) (* 0.375 h))
        (av:mk-pl (list (av:tu th tcir (+ ucir (if (> uq ucir) (* 0.375 h) (* -0.375 h))))
                        (av:tu th tcir uq)
                        (av:tu th tdim uq))
                  AV:LAY-IND nil AV:LT-NOME (/ h lts) nil)
        (av:mk-line (av:tu th (+ tcir (if (> tdim tcir) (* 0.375 h) (* -0.375 h))) ucir)
                    (av:tu th tdim ucir) AV:LAY-IND AV:LT-NOME (/ h lts))
      )
    )
  )
  T
)

;;; ==========================================================================
;;;  7b. DADOS NO DESENHO (edicao futura), NUMERACAO E LISTA DE FERROS
;;; ==========================================================================
;;;  Cada detalhamento guarda, num XRECORD do dicionario ARMVAR_DADOS, os
;;;  parametros da janela e as respostas dadas (direcao, contorno e seus
;;;  handles, pontos clicados).  Todas as entidades criadas recebem o XDATA
;;;  ("ARMVAR" (1000 . id)).  ARMVAREDIT reabre a janela com esses dados e
;;;  redesenha tudo; ARMVARLISTA soma todos os detalhamentos.

;;; valor -> grupos DXF tipados (sem converter numeros em texto):
;;;   (300 . texto)  (40 . real)  (90 . inteiro)  (281 . 0/1) nil/T
;;;   (282 . 1) ... (282 . 0)  = lista
(defun av:enc (x)
  (cond
    ((null x) (list (cons 281 0)))
    ((eq x T) (list (cons 281 1)))
    ((= (type x) 'STR) (list (cons 300 x)))
    ((= (type x) 'INT) (list (cons 90 x)))
    ((= (type x) 'REAL) (list (cons 40 x)))
    ((= (type x) 'LIST)
     (append (list (cons 282 1)) (apply 'append (mapcar 'av:enc x)) (list (cons 282 0))))
    (t (list (cons 281 0)))
  )
)

;;; grupos -> valor (inverso de av:enc)
(defun av:dec (gs / stk cur g)
  (setq stk nil cur nil)
  (foreach g gs
    (cond
      ((= (car g) 282)
       (if (= (cdr g) 1)
         (setq stk (cons cur stk) cur nil)
         (setq cur (cons (reverse cur) (car stk)) stk (cdr stk))))
      ((= (car g) 281) (setq cur (cons (if (= (cdr g) 1) T nil) cur)))
      ((member (car g) '(300 40 90)) (setq cur (cons (cdr g) cur)))
    )
  )
  (car cur)
)

;;; dicionario dos dados (cria se nao existir)
(defun av:dic ( / d x)
  (if (setq d (dictsearch (namedobjdict) AV:DIC-NOME))
    (cdr (assoc -1 d))
    (progn
      (setq x (entmakex '((0 . "DICTIONARY") (100 . "AcDbDictionary"))))
      (dictadd (namedobjdict) AV:DIC-NOME x)
      x
    )
  )
)

;;; ids (chaves) guardados
(defun av:reg-ids ( / r)
  (setq r nil)
  (foreach g (entget (av:dic))
    (if (= (car g) 3) (setq r (cons (cdr g) r)))
  )
  (reverse r)
)

;;; novo id: AV1, AV2, ...
(defun av:novo-id ( / n m)
  (setq n 0)
  (foreach k (av:reg-ids)
    (if (wcmatch k "AV#*")
      (if (> (setq m (atoi (substr k 3))) n) (setq n m)))
  )
  (strcat "AV" (itoa (1+ n)))
)

;;; grava a lista "dados" no id
(defun av:reg-grava (id dados / d x)
  (setq d (av:dic))
  (if (dictsearch d id) (dictremove d id))
  (setq x (entmakex (append (list '(0 . "XRECORD") '(100 . "AcDbXrecord"))
                            (av:enc dados))))
  (if x
    (progn
      (dictadd d id x)
      ;; confere a leitura (evita edicao futura com dados errados)
      (if (not (equal (av:reg-le id) dados 1e-6))
        (av:aviso (strcat "os dados de " id " nao foram lidos de volta iguais."))))
    (av:aviso (strcat "nao foi possivel gravar os dados de " id " (XRECORD)."))
  )
  x
)

;;; le os dados do id (ou nil)
(defun av:reg-le (id / r gs)
  (if (setq r (dictsearch (av:dic) id))
    (progn
      (foreach g r (if (member (car g) '(300 40 90 281 282)) (setq gs (cons g gs))))
      (av:dec (reverse gs))
    )
  )
)

(defun av:reg-apaga (id / d)
  (setq d (av:dic))
  (if (dictsearch d id) (dictremove d id))
)

;;; id (e etiqueta) do XDATA de uma entidade:  (id etiqueta) ou nil
(defun av:id-ent (e / x r)
  (if (setq x (cdr (assoc -3 (entget e (list AV:APP)))))
    (progn
      (foreach g (cdr (car x)) (if (= (car g) 1000) (setq r (cons (cdr g) r))))
      (reverse r)
    )
  )
)

;;; entidades de um detalhamento
(defun av:ents-id (id / ss i e r)
  (setq r nil)
  (if (setq ss (ssget "_X" (list (list -3 (list AV:APP)))))
    (progn
      (setq i 0)
      (while (< i (sslength ss))
        (setq e (ssname ss i) i (1+ i))
        (if (= (car (av:id-ent e)) id) (setq r (cons e r)))
      )
    )
  )
  r
)

(defun av:apaga-id (id)
  (foreach e (av:ents-id id) (entdel e))
)

;;; canto superior esquerdo (1.o vertice) da moldura com a etiqueta "tag"
(defun av:ancora (id tag / r)
  (foreach e (av:ents-id id)
    (if (and (null r) (= (cadr (av:id-ent e)) tag))
      (setq r (av:p2 (cdr (assoc 10 (entget e)))))
    )
  )
  r
)

;;; ---- mensagens: nada de erro silencioso -------------------------------------
(defun av:aviso (msg) (princ (strcat "\nARMVAR aviso: " msg)))

;;; chama f com args; se der erro, MOSTRA o erro e devolve nil
(defun av:roda (f args rotulo / r)
  (setq AV:ETAPA nil r (vl-catch-all-apply f args))
  (if (vl-catch-all-error-p r)
    (progn
      (princ (strcat "\n*** ARMVAR erro (" rotulo "): " (vl-catch-all-error-message r)
                     (if AV:ETAPA (strcat "  [etapa: " AV:ETAPA "]") "")))
      nil)
    r)
)

;;; ---- ELEMENTO PARAMETRIZADO = BLOCO COM ATRIBUTOS ---------------------------
;;;  Cada detalhamento vira o bloco "ARMVAR$<id>$DET" (ferro, cotas, textos),
;;;  com os parametros em ATRIBUTOS invisiveis (editaveis na janela
;;;  Propriedades ou com duplo clique).  As tabelas viram "ARMVAR$<id>$T1" e
;;;  "$T2", e a lista geral "ARMVAR$LISTA$LST".  Os blocos tem ponto base
;;;  0,0,0 e sao inseridos em 0,0,0: mover o bloco move o desenho; ao
;;;  atualizar, a definicao e refeita e a insercao continua onde estiver.

;;; parametros guardados -> variaveis; detalhamento antigo (lista menor): os
;;; campos novos voltam ao padrao (angulos das pernas = 90)
(defun av:set-params (vals / n)
  (mapcar 'set AV:PARAMS vals)
  (setq n (length vals))
  (if (< n 25) (setq AV:P-AG1 "90"))
  (if (< n 26) (setq AV:P-AG2 "90"))
)

;;; atributos: (tag  prompt  variavel  tipo)
(setq AV:ATRIBS
  '(("POSICAO"         "Posicao N"                          AV:P-POS  int)
    ("BITOLA"          "Bitola (mm)"                        AV:P-BIT  bit)
    ("ESPACAMENTO"     "Espacamento (cm)"                   AV:P-ESP  pos)
    ("COBRIMENTO"      "Cobrimento (cm)"                    AV:P-COB  num)
    ("REPETICOES"      "Repeticoes (2 = simetria)"          AV:P-REP  int)
    ("PERNA_INICIAL"   "Perna inicial (cm)"                 AV:P-PL1  num)
    ("PONTA_INICIAL"   "Ponta inicial (cm)"                 AV:P-PT1  num)
    ("PERNA_FINAL"     "Perna final (cm)"                   AV:P-PL2  num)
    ("PONTA_FINAL"     "Ponta final (cm)"                   AV:P-PT2  num)
    ("ANGULO_PERNA_INI" "Representacao da perna inicial (graus: 90/45/135/180)" AV:P-AG1 ang)
    ("ANGULO_PERNA_FIM" "Representacao da perna final (graus: 90/45/135/180)"   AV:P-AG2 ang)
    ("GANCHOS_LADO"    "Ganchos para o lado (DIREITA/ESQUERDA)" AV:P-LADO lado)
    ("ACO"             "Aco (CA-50/CA-60/CA-25)"            AV:P-ACO  aco)
    ("SIMETRIA"        "Barra simetrica invertida (SIM/NAO)" AV:P-SIM sn)
    ("EMENDAS"         "Emendar barras longas (SIM/NAO)"    AV:P-EMD  sn)
    ("COMPR_COMERCIAL" "Comprimento comercial (cm)"         AV:P-LCM  pos)
    ("TRASPASSE"       "Traspasse L (cm)"                   AV:P-TRA  num)
    ("PRIMEIRO_PEDACO" "1.o pedaco (cm, vazio = comercial)" AV:P-PIN  vaz)
    ("ALTERNAR"        "Alternar barras vizinhas (SIM/NAO)" AV:P-DFS  sn)
    ("AFASTAMENTO"     "Afastamento entre emendas (cm)"     AV:P-AFS  num)
    ("TABELA_EQUIV"    "Tabela c/ compr. equivalente (SIM/NAO)" AV:P-EQU sn)
    ("ELEMENTO"        "Elemento (lista)"                   AV:P-ELE  txt))
)

;;; parametros atuais -> ((tag valor) ...)
(defun av:params->atrs ( / r v)
  (foreach a AV:ATRIBS
    (setq v (eval (caddr a)))
    (setq v (cond
              ((= (cadddr a) 'bit)  (nth v AV:BITOLAS))
              ((= (cadddr a) 'aco)  (nth v AV:ACOS))
              ((= (cadddr a) 'lado) (if (= v 1) "ESQUERDA" "DIREITA"))
              ((= (cadddr a) 'sn)   (if (= v "1") "SIM" "NAO"))
              (t (if v v ""))))
    (setq r (cons (list (car a) (if v v "")) r))
  )
  (reverse r)
)

;;; ((tag valor) ...) -> parametros (valores invalidos sao ignorados)
(defun av:atrs->params (pares / a v n k)
  (foreach pv pares
    (if (setq a (assoc (strcase (car pv)) AV:ATRIBS))
      (progn
        (setq v (vl-string-trim " " (cadr pv)) n (av:num v))
        (cond
          ((= (cadddr a) 'int)  (if (and n (>= n 1)) (set (caddr a) (itoa (fix n)))))
          ((= (cadddr a) 'num)  (if (and n (>= n 0)) (set (caddr a) (av:fmt n))))
          ((= (cadddr a) 'ang)  (if (and n (>= n 0) (<= n 360)) (set (caddr a) (av:fmt n))))
          ((= (cadddr a) 'pos)  (if (and n (> n 0)) (set (caddr a) (av:fmt n))))
          ((= (cadddr a) 'vaz)  (if (or (= v "") (and n (> n 0))) (set (caddr a) v)))
          ((= (cadddr a) 'txt)  (set (caddr a) v))
          ((= (cadddr a) 'sn)   (set (caddr a) (if (wcmatch (strcase v) "S*,1,Y*,T*") "1" "0")))
          ((= (cadddr a) 'lado) (set (caddr a) (if (wcmatch (strcase v) "E*,L*,1") 1 0)))
          ((= (cadddr a) 'bit)
           (setq k 0)
           (foreach b AV:BITOLAS
             (if (and n (equal (atof b) n 1e-6)) (set (caddr a) k))
             (setq k (1+ k))))
          ((= (cadddr a) 'aco)
           (setq k 0)
           (foreach b AV:ACOS
             (if (= (strcase b) (strcase v)) (set (caddr a) k))
             (setq k (1+ k))))
        )
      )
    )
  )
)

;;; atributos de uma insercao: ((tag valor) ...)
(defun av:atr-le (ins / e ed r)
  (setq e (entnext ins) r nil)
  (while (and e (setq ed (entget e)) (= (cdr (assoc 0 ed)) "ATTRIB"))
    (setq r (cons (list (cdr (assoc 2 ed)) (cdr (assoc 1 ed))) r) e (entnext e))
  )
  (reverse r)
)

;;; grava valores nos atributos de uma insercao
(defun av:atr-grava (ins pares / e ed p)
  (setq e (entnext ins))
  (while (and e (setq ed (entget e)) (= (cdr (assoc 0 ed)) "ATTRIB"))
    (if (and (setq p (assoc (cdr (assoc 2 ed)) pares))
             (/= (cadr p) (cdr (assoc 1 ed))))
      (entmod (subst (cons 1 (cadr p)) (assoc 1 ed) ed)))
    (setq e (entnext e))
  )
  (entupd ins)
)

;;; entidades SOLTAS (nao blocos) de um detalhamento e grupo
(defun av:soltos (id grp / r x)
  (foreach e (av:ents-id id)
    (setq x (av:id-ent e))
    (if (and (/= (cdr (assoc 0 (entget e))) "INSERT") (= (caddr x) grp))
      (setq r (cons e r)))
  )
  r
)

;;; insercao do bloco de um detalhamento e grupo (ou nil)
(defun av:insert-de (id grp / r x)
  (foreach e (av:ents-id id)
    (setq x (av:id-ent e))
    (if (and (null r) (= (cdr (assoc 0 (entget e))) "INSERT") (= (caddr x) grp))
      (setq r e))
  )
  r
)

(defun av:nome-bloco (id grp) (strcat "ARMVAR$" id "$" grp))

;;; DXF completos (com marcadores de subclasse) -- aceitos por AutoCAD e ZWCAD
(defun av:dxf-bloco (nome atr)
  (list '(0 . "BLOCK") '(100 . "AcDbEntity") '(8 . "0") '(100 . "AcDbBlockBegin")
        (cons 2 nome) (cons 70 (if atr 2 0)) '(10 0.0 0.0 0.0))
)
(defun av:dxf-attdef (tag prompt val h)
  (list '(0 . "ATTDEF") '(100 . "AcDbEntity") '(8 . "0") '(100 . "AcDbText")
        '(10 0.0 0.0 0.0) (cons 40 h) (cons 1 val) (cons 7 AV:STY)
        '(100 . "AcDbAttributeDefinition") (cons 3 prompt) (cons 2 tag) '(70 . 1))
)
(defun av:dxf-attrib (tag val h)
  (list '(0 . "ATTRIB") '(100 . "AcDbEntity") '(8 . "0") '(100 . "AcDbText")
        '(10 0.0 0.0 0.0) (cons 40 h) (cons 1 val) (cons 7 AV:STY)
        '(100 . "AcDbAttribute") (cons 2 tag) '(70 . 1))
)
(defun av:dxf-insert (nome atr xd)
  (list '(0 . "INSERT") '(100 . "AcDbEntity") '(8 . "0") '(100 . "AcDbBlockReference")
        (cons 66 (if atr 1 0)) (cons 2 nome) '(10 0.0 0.0 0.0)
        '(41 . 1.0) '(42 . 1.0) '(43 . 1.0) '(50 . 0.0) xd)
)

;;; junta as entidades soltas do grupo num bloco (cria ou REDEFINE) e garante
;;; uma insercao; atrs = ((tag valor) ...) dos atributos (ou nil).
;;; Se o CAD recusar algo, avisa e deixa as entidades soltas (nada se perde).
(defun av:empacota (id grp atrs h / ents nome ins e ed n ok copiados fora fim novo)
  (setq ents (av:soltos id grp) nome (av:nome-bloco id grp)
        ins  (av:insert-de id grp))
  ;; bloco em uso por esta insercao (pode ter sufixo $n)
  (if ins (setq nome (cdr (assoc 2 (entget ins)))))
  (if (null ents)
    ;; nada a desenhar (ex.: tabela desligada): tira a insercao antiga
    (if ins (entdel ins))
    (progn
      ;; redefine o bloco; se o CAD nao aceitar redefinir, usa um nome novo
      (setq ok (entmake (av:dxf-bloco nome atrs)))
      (if (not ok)
        (progn
          (setq n 1)
          (while (tblsearch "BLOCK" (strcat (av:nome-bloco id grp) "$" (itoa n)))
            (setq n (1+ n)))
          (setq nome (strcat (av:nome-bloco id grp) "$" (itoa n))
                ok   (entmake (av:dxf-bloco nome atrs)))
        )
      )
      (if (not ok)
        (av:aviso (strcat "o CAD nao aceitou criar o bloco " nome
                          "; o desenho fica solto (use ARMVAREDIT para editar)."))
        (progn
          (setq copiados nil fora nil)
          (foreach e (reverse ents)
            (setq ed (vl-remove-if '(lambda (g) (member (car g) '(-1 5 67 102 330 360 410)))
                                   (entget e (list "*"))))
            (if (entmake ed)
              (setq copiados (cons e copiados))
              (setq fora (cons (cdr (assoc 0 ed)) fora)))
          )
          (foreach a atrs
            (if (not (entmake (av:dxf-attdef (car a) (cadr (assoc (car a) AV:ATRIBS)) (cadr a) h)))
              (setq fora (cons "ATTDEF" fora)))
          )
          (setq fim (entmake '((0 . "ENDBLK"))))
          (if (not fim)
            (av:aviso (strcat "o CAD nao fechou o bloco " nome "; o desenho fica solto."))
            (progn
              (foreach e copiados (entdel e))
              (if fora
                (av:aviso (strcat (itoa (length fora)) " objeto(s) ("
                                  (car fora) ") ficaram fora do bloco " nome ".")))
              (if ins
                (progn
                  ;; bloco com nome novo: a insercao passa a usa-lo
                  (if (/= (cdr (assoc 2 (entget ins))) nome)
                    (entmod (subst (cons 2 nome) (assoc 2 (entget ins)) (entget ins))))
                  (if atrs (av:atr-grava ins atrs))
                  (entupd ins)
                )
                (progn
                  (setq novo (entmake (av:dxf-insert nome atrs (av:xd-lista id "" grp))))
                  (if (and novo atrs)
                    (progn
                      (foreach a atrs (entmake (av:dxf-attrib (car a) (cadr a) h)))
                      (entmake '((0 . "SEQEND")))
                    )
                  )
                  (if novo
                    (setq ins (av:insert-de id grp))
                    (av:aviso (strcat "o CAD nao aceitou inserir o bloco " nome ".")))
                )
              )
            )
          )
        )
      )
    )
  )
  ins
)

;;; ---- respostas: gravacao (criacao) e repeticao (edicao) -------------------
;;; AV:MODO = 'replay durante ARMVAREDIT; AV:RESP = dados guardados
(defun av:rp-p () (eq AV:MODO 'replay))
(defun av:rp (k) (cadr (assoc k AV:RESP)))
(defun av:gr (k v) (setq AV:REC (cons (list k v) AV:REC)) v)

;;; contorno na edicao: relido das entidades originais (se ainda existirem
;;; e ainda formarem contorno fechado), senao o contorno guardado
(defun av:aneis-replay ( / ss e ok an)
  (setq ss (ssadd) ok T)
  (foreach hd (av:rp "hnd")
    (if (and (setq e (handent hd)) (entget e))
      (ssadd e ss)
      (setq ok nil)
    )
  )
  (if (and ok (> (sslength ss) 0)) (setq an (av:aneis-da-selecao ss)))
  (setq AV:HND (av:rp "hnd"))
  (if an
    (progn (princ "\n  Contorno relido do desenho.") an)
    (progn (princ "\n  Contorno original nao encontrado: usando o contorno guardado.")
           (av:rp "anel"))
  )
)

;;; ---- numeracao automatica ------------------------------------------------
;;; posicoes citadas num texto: "N.1", "N1A", "(2X) N.3 N.4" -> (1 3 4)
(defun av:pos-texto (s / i n c ant j dg r)
  (setq i 1 n (strlen s) r nil)
  (while (<= i n)
    (setq c (substr s i 1))
    (if (and (= c "N")
             (or (= i 1)
                 (not (wcmatch (setq ant (substr s (1- i) 1)) "@,#"))))
      (progn
        (setq j (1+ i))
        (if (= (substr s j 1) ".") (setq j (1+ j)))
        (setq dg "")
        (while (and (<= j n) (wcmatch (substr s j 1) "#"))
          (setq dg (strcat dg (substr s j 1)) j (1+ j))
        )
        (if (/= dg "") (setq r (cons (atoi dg) r)))
      )
    )
    (setq i (1+ i))
  )
  r
)

;;; maior posicao nos textos (TEXT, MTEXT, cotas) de uma selecao e nos
;;; blocos ARMVAR selecionados (posicoes guardadas nos dados)
(defun av:pos-max (ss / i e ed s mx x d)
  (setq mx 0 i 0)
  (if ss
    (while (< i (sslength ss))
      (setq e (ssname ss i) ed (entget e) s "" i (1+ i))
      (if (= (cdr (assoc 0 ed)) "INSERT")
        (if (and (setq x (av:id-ent e)) (setq d (av:reg-le (car x))))
          (foreach ln (cadr (assoc "res" d)) (setq s (strcat s " " (car ln)))))
        (foreach g ed (if (member (car g) '(1 3)) (setq s (strcat s " " (cdr g)))))
      )
      (foreach v (av:pos-texto s) (if (> v mx) (setq mx v)))
    )
  )
  mx
)

;;; aplica a numeracao escolhida na janela (AV:P-NUM): 1 = desenho inteiro,
;;; 2 = area selecionada.  Ajusta AV:P-POS para a proxima posicao livre.
(defun av:numera ( / ss mx)
  (cond
    ((= AV:P-NUM 1)
     (setq ss (ssget "_X" '((0 . "TEXT,MTEXT,DIMENSION,INSERT")))))
    ((= AV:P-NUM 2)
     (princ "\nSelecione a AREA com os ferros ja detalhados (janela/crossing): ")
     (setq ss (vl-catch-all-apply 'ssget (list '((0 . "TEXT,MTEXT,DIMENSION,INSERT")))))
     (if (vl-catch-all-error-p ss) (setq ss nil)))
  )
  (if (member AV:P-NUM '(1 2))
    (progn
      (setq mx (av:pos-max ss) AV:P-POS (itoa (1+ mx)))
      (princ (strcat "\n  Maior posicao encontrada: "
                     (if (> mx 0) (strcat "N." (itoa mx)) "nenhuma")
                     "  ->  este detalhamento comeca em N." AV:P-POS))
    )
  )
)

;;; ---- LISTAS DE FERROS ------------------------------------------------------
;;;  "LISTA" = lista geral (todos os detalhamentos); "LS1", "LS2", ... =
;;;  listas de detalhamentos SELECIONADOS (dados: ("p0" canto) ("ids" (...))).
;;;  Cada lista so e refeita quando muda um detalhamento que ela contem.

;;; o id e de uma lista?
(defun av:lista-id-p (id)
  (and id (or (= id "LISTA") (wcmatch id "LS#*")))
)

;;; ids das listas guardadas
(defun av:listas ( / r)
  (foreach id (av:reg-ids) (if (av:lista-id-p id) (setq r (cons id r))))
  (reverse r)
)

;;; novo id de lista: LS1, LS2, ...
(defun av:lista-novo-id ( / n m)
  (setq n 0)
  (foreach k (av:reg-ids)
    (if (wcmatch k "LS#*")
      (if (> (setq m (atoi (substr k 3))) n) (setq n m)))
  )
  (strcat "LS" (itoa (1+ n)))
)
;;; linha guardada em cada detalhamento ("res"):
;;;   (rotulo bitola qtd ctot aco kgm elemento variavel)
;;;   variavel = "VAR" quando a posicao tem barras de comprimentos diferentes
(defun av:lista-linhas (ids / r d vivos)
  (setq r nil)
  (foreach id (av:reg-ids)
    (if (and (not (av:lista-id-p id)) (or (null ids) (member id ids)))
      (if (av:ents-id id)
        (if (setq d (av:reg-le id))
          (foreach ln (av:rp-de d "res")
            (if (and (listp ln) (>= (length ln) 7) (= (type (car ln)) 'STR))
              (setq r (cons ln r)))))
        ;; detalhamento apagado do desenho: descarta os dados
        (av:reg-apaga id)
      )
    )
  )
  (reverse r)
)

(defun av:rp-de (d k) (cadr (assoc k d)))
(defun av:num-rot (rot) (atoi (substr rot 2)))

;;; ---- desenho das listas (padrao Baluarte) ---------------------------------
;;; texto alinhado pelo MEIO: al 0 = esquerda, 1 = centro, 2 = direita
(defun av:txt-al (txt x y h lay al)
  (entmake (append
             (list '(0 . "TEXT") (cons 8 lay) (cons 10 (list x y 0.0))
                   (cons 40 h) (cons 1 txt) '(50 . 0.0) '(41 . 1.0) (cons 7 AV:STY)
                   (cons 72 al) (cons 11 (list x y 0.0)) '(73 . 2))
             (av:xd)))
)
(defun av:hl (x1 x2 y lay) (av:mk-line (list x1 y) (list x2 y) lay nil nil))
(defun av:vl (x y1 y2 lay) (av:mk-line (list x y1) (list x y2) lay nil nil))
(defun av:ret (x1 y1 x2 y2 lay)
  (av:mk-pline (list (list x1 y1) (list x2 y1) (list x2 y2) (list x1 y2)) lay T)
)
;;; nome do aco no titulo do resumo: CA-50 -> CA-50A, CA-60 -> CA-60B
(defun av:aco-titulo (a)
  (cond ((= a "CA-50") "CA-50A") ((= a "CA-60") "CA-60B") (t a))
)

;;; desenha a LISTA DE FERROS e o(s) RESUMO(S) DE ACO a partir do canto p0
;;;   LISTA:  N | %%c (mm) | QUANT. | COMPRIMENTOS: UNITARIO (cm) | TOTAL (cm)
;;;           com uma linha de titulo por ELEMENTO (campo "Elemento");
;;;           posicao com barras de comprimentos diferentes (armadura
;;;           variavel, "C=VAR" no ferro): UNITARIO = "VAR."
;;;   RESUMO: um por aco -  %%c | kg/m | COMPR. (m) | PESO (kg) | PESO TOTAL
(defun av:lista-desenha (lid ids p0 h / lns els x0 y0 y wd n el res tot
                                 k mt c ln lst cx rc ya yb yc ym yt acos ac pk)
  (setq lns (vl-sort (av:lista-linhas ids)
                     '(lambda (a b) (< (av:num-rot (car a)) (av:num-rot (car b)))))
        AV:ID lid AV:GRP "LST")
  (foreach e (av:soltos lid "LST") (entdel e))
  (av:prepara)
  (setq x0 (car p0) y0 (cadr p0) wd (* 36.5 h)
        ;; colunas (bordas esquerdas + borda direita)
        cx (mapcar '(lambda (v) (+ x0 (* v h))) '(0.0 4.5 9.0 16.5 26.5 36.5)))
  ;; elementos na ordem da 1.a posicao
  (setq els nil)
  (foreach ln lns (if (not (member (av:nth 6 ln) els)) (setq els (append els (list (av:nth 6 ln))))))
  ;; linhas da tabela: ("EL" nome) ou ("POS" linha)
  (setq lst nil)
  (foreach el els
    (if (/= el "") (setq lst (append lst (list (list "EL" el)))))
    (foreach ln lns (if (= (av:nth 6 ln) el) (setq lst (append lst (list (list "POS" ln))))))
  )
  ;; ---- titulo
  (setq ya (- y0 (* 3.5 h)))
  (av:txt-al "LISTA DE FERROS" (+ x0 (/ wd 2.0)) (/ (+ y0 ya) 2.0) (* 2.0 h) AV:LAY-TXT 1)
  ;; ---- cabecalho (duas linhas)
  (setq yb (- ya (* 2.2 h)) yc (- yb (* 3.2 h)) ym (/ (+ ya yc) 2.0))
  (av:txt-al "N" (/ (+ (nth 0 cx) (nth 1 cx)) 2.0) ym h AV:LAY-TXT 1)
  (av:txt-al "%%c" (/ (+ (nth 1 cx) (nth 2 cx)) 2.0) (+ ym (* 0.8 h)) h AV:LAY-TXT 1)
  (av:txt-al "(mm)" (/ (+ (nth 1 cx) (nth 2 cx)) 2.0) (- ym (* 0.8 h)) h AV:LAY-TXT 1)
  (av:txt-al "QUANT." (/ (+ (nth 2 cx) (nth 3 cx)) 2.0) ym h AV:LAY-TXT 1)
  (av:txt-al "COMPRIMENTOS" (/ (+ (nth 3 cx) (nth 5 cx)) 2.0) (/ (+ ya yb) 2.0) h AV:LAY-TXT 1)
  (setq ym (/ (+ yb yc) 2.0))
  (av:txt-al (strcat "UNIT" (chr 193) "RIO") (/ (+ (nth 3 cx) (nth 4 cx)) 2.0) (+ ym (* 0.8 h)) h AV:LAY-TXT 1)
  (av:txt-al "(cm)" (/ (+ (nth 3 cx) (nth 4 cx)) 2.0) (- ym (* 0.8 h)) h AV:LAY-TXT 1)
  (av:txt-al "TOTAL" (/ (+ (nth 4 cx) (nth 5 cx)) 2.0) (+ ym (* 0.8 h)) h AV:LAY-TXT 1)
  (av:txt-al "(cm)" (/ (+ (nth 4 cx) (nth 5 cx)) 2.0) (- ym (* 0.8 h)) h AV:LAY-TXT 1)
  (av:hl x0 (+ x0 wd) ya AV:LAY-TAB)
  (av:hl (nth 3 cx) (nth 5 cx) yb AV:LAY-GRADE)
  (av:hl x0 (+ x0 wd) yc AV:LAY-TAB)
  (foreach xg (list (nth 1 cx) (nth 2 cx) (nth 3 cx)) (av:vl xg ya yc AV:LAY-GRADE))
  (av:vl (nth 4 cx) yb yc AV:LAY-GRADE)
  ;; ---- linhas
  (setq y yc)
  (foreach it lst
    (setq yt (- y (* 2.0 h)) ym (- y h))
    (if (= (car it) "EL")
      (av:txt-al (cadr it) (+ x0 (* 0.6 h)) ym h AV:LAY-TXT 0)
      (progn
        (setq ln (cadr it))
        (foreach xg (list (nth 1 cx) (nth 2 cx) (nth 3 cx) (nth 4 cx)) (av:vl xg y yt AV:LAY-GRADE))
        (setq k 1)
        (foreach c (list (itoa (av:num-rot (car ln))) (av:nth 1 ln)
                         (itoa (av:nth 2 ln))
                         ;; armadura variavel: comprimento unitario "VAR."
                         (if (= (av:nth 7 ln) "VAR")
                           "VAR."
                           (itoa (av:int (/ (av:nth 3 ln) (max 1 (av:nth 2 ln))))))
                         (itoa (av:int (av:nth 3 ln))))
          (av:txt-al c (- (nth k cx) (* 0.6 h)) ym h AV:LAY-TXT 2)
          (setq k (1+ k))
        )
      )
    )
    (if (/= it (av:ultimo lst)) (av:hl x0 (+ x0 wd) yt AV:LAY-GRADE))
    (setq y yt)
  )
  (setq AV:TAG "LST")
  (av:ret x0 y0 (+ x0 wd) y AV:LAY-TAB)
  (setq AV:TAG nil)
  ;; ---- resumo por aco e bitola: ((aco bitola) ctot kgm)
  (setq res nil)
  (foreach ln lns
    (setq k (list (av:nth 4 ln) (av:nth 1 ln)))
    (if (assoc k res)
      (setq res (subst (list k (+ (cadr (assoc k res)) (av:nth 3 ln)) (av:nth 5 ln))
                       (assoc k res) res))
      (setq res (append res (list (list k (av:nth 3 ln) (av:nth 5 ln)))))
    )
  )
  (setq res (vl-sort res '(lambda (a b)
                            (if (= (car (car a)) (car (car b)))
                              (< (atof (cadr (car a))) (atof (cadr (car b))))
                              (< (car (car a)) (car (car b)))))))
  (setq acos nil)
  (foreach g res (if (not (member (car (car g)) acos)) (setq acos (append acos (list (car (car g)))))))
  (setq rc (mapcar '(lambda (v) (+ x0 (* v h))) '(0.0 4.5 14.0 26.5 36.5))
        y (- y (* 4.0 h)) pk 0.0)
  (foreach ac acos
    (setq y0 y ya (- y (* 3.0 h)) tot 0.0)
    (av:txt-al (strcat "RESUMO DE A" (chr 199) "O " (av:aco-titulo ac))
               (+ x0 (/ wd 2.0)) (/ (+ y ya) 2.0) (* 1.6 h) AV:LAY-TXT 1)
    (av:hl x0 (+ x0 wd) ya AV:LAY-TAB)
    (setq y ya yt (- y (* 2.0 h)) ym (- y h) k 0)
    (foreach c '("%%c" "kg/m" "COMPR. (m)" "PESO (kg)")
      (av:txt-al c (/ (+ (nth k rc) (nth (1+ k) rc)) 2.0) ym h AV:LAY-TXT 1)
      (setq k (1+ k)))
    (foreach xg (list (nth 1 rc) (nth 2 rc) (nth 3 rc)) (av:vl xg y yt AV:LAY-GRADE))
    (av:hl x0 (+ x0 wd) yt AV:LAY-GRADE)
    (setq y yt)
    (foreach g res
      (if (= (car (car g)) ac)
        (progn
          (setq mt (/ (cadr g) 100.0) tot (+ tot (* mt (caddr g)))
                yt (- y (* 2.0 h)) ym (- y h) k 1)
          (foreach c (list (cadr (car g)) (rtos (caddr g) 2 3) (rtos mt 2 1)
                           (rtos (* mt (caddr g)) 2 0))
            (av:txt-al c (- (nth k rc) (* 0.6 h)) ym h AV:LAY-TXT 2)
            (setq k (1+ k)))
          (foreach xg (list (nth 1 rc) (nth 2 rc) (nth 3 rc)) (av:vl xg y yt AV:LAY-GRADE))
          (av:hl x0 (+ x0 wd) yt AV:LAY-GRADE)
          (setq y yt)
        )
      )
    )
    (setq yt (- y (* 2.0 h)) ym (- y h))
    (av:txt-al "PESO TOTAL" (/ (+ x0 (nth 3 rc)) 2.0) ym h AV:LAY-TXT 1)
    (av:txt-al (rtos tot 2 0) (- (+ x0 wd) (* 0.6 h)) ym h AV:LAY-TXT 2)
    (av:vl (nth 3 rc) y yt AV:LAY-GRADE)
    (setq y yt pk (+ pk tot))
    (av:ret x0 y0 (+ x0 wd) y AV:LAY-TAB)
    (setq y (- y (* 3.0 h)))
  )
  (setq AV:ID nil AV:GRP nil)
  (av:empacota lid "LST" nil h)
  (av:reg-grava lid (list (list "p0" p0) (list "h" h) (list "ids" ids)))
  (princ (strcat "\n  LISTA DE FERROS"
                 (if ids (strcat " (" (itoa (length ids)) " detalhamento(s) selecionado(s))") " geral")
                 ": " (itoa (length lns)) " posicao(oes), "
                 (rtos pk 2 1) " kg."))
)

;;; refaz as listas existentes que contem o detalhamento id
;;; (id nil = todas); a insercao de cada lista fica onde estiver
(defun av:lista-auto (h id / d ids)
  (foreach lid (av:listas)
    (if (and (av:insert-de lid "LST") (setq d (av:reg-le lid)))
      (progn
        (setq ids (cadr (assoc "ids" d)))
        (if (or (null id) (null ids) (member id ids))
          (av:lista-desenha lid ids (cadr (assoc "p0" d)) h))
      )
    )
  )
)

;;; ==========================================================================
;;;  8.  ENTRADA DO USUARIO
;;; ==========================================================================

;;; graus -> [0,180)
(defun av:norm180 (d)
  (while (< d 0.0) (setq d (+ d 180.0)))
  (while (>= d 180.0) (setq d (- d 180.0)))
  d
)

;;; direcao principal em radianos [0,pi) ou nil (cancelado)
(defun av:pede-direcao ( / r ang e pk s ps p ucs msg)
  (setq ang nil
        ucs (angle '(0.0 0.0 0.0) (trans '(1.0 0.0 0.0) 1 0 T)))
  (while (not ang)
    (initget 128)
    (setq r (vl-catch-all-apply
              'entsel
              (list "\nDirecao principal do ferro - digite o angulo em graus OU clique sobre uma linha: ")))
    (cond
      ((vl-catch-all-error-p r)
       (setq msg (strcase (vl-catch-all-error-message r)))
       (if (wcmatch msg "*CANCEL*,*QUIT*,*EXIT*,*ABORT*")
         (setq ang 'cancel)
         ;; o CAD nao aceitou texto no entsel: pede so o angulo
         (progn
           (setq s (getreal "\nDirecao principal do ferro - angulo em graus (0 = eixo X): "))
           (setq ang (if s (+ (* s (/ pi 180.0)) ucs) 'cancel))
         )
       )
      )
      ((null r) (setq ang 'cancel))
      ((= (type r) 'STR)
       (setq s (av:num r))
       (if s
         (setq ang (+ (* s (/ pi 180.0)) ucs))
         (princ "\n  Valor invalido. Digite um numero (graus) ou clique numa linha.")
       )
      )
      ((= (type r) 'LIST)
       (setq e (car r) pk (trans (cadr r) 1 0))
       (setq p (vl-catch-all-apply
                 '(lambda ()
                    (setq ps (vlax-curve-getParamAtPoint
                               e (vlax-curve-getClosestPointTo e pk)))
                    (vlax-curve-getFirstDeriv e ps))))
       (if (and (not (vl-catch-all-error-p p)) (listp p) (> (av:hyp (car p) (cadr p)) 1e-12))
         (progn
           (setq ang (atan (cadr p) (car p)))
           (princ (strcat "\n  Direcao assumida da linha: "
                          (rtos (av:norm180 (* ang (/ 180.0 pi))) 2 4) " graus."))
         )
         (princ "\n  Esse objeto nao e uma linha/curva. Tente outro.")
       )
      )
    )
  )
  (if (eq ang 'cancel)
    nil
    (* (av:norm180 (* ang (/ 180.0 pi))) (/ pi 180.0))
  )
)

;;; realca os aneis na tela
(defun av:realca (aneis / n i p q)
  (foreach an aneis
    (setq n (length an) i 0)
    (while (< i n)
      (setq p (nth i an) q (nth (rem (1+ i) n) an))
      (grdraw p q 2 1)
      (setq i (1+ i))
    )
  )
)

;;; seleciona e confirma o contorno.  devolve lista de aneis ou nil
(defun av:pede-contorno (uc / ss aneis ok area ext r)
  (setq ok nil)
  (while (not ok)
    (princ "\nSelecione o CONTORNO FECHADO (polilinha, circulo, retangulo, ou linhas/arcos que formem uma figura fechada).")
    (setq ss (vl-catch-all-apply
               'ssget (list '((0 . "LINE,ARC,CIRCLE,LWPOLYLINE,POLYLINE,ELLIPSE,SPLINE")))))
    (cond
      ((vl-catch-all-error-p ss) (setq ok 'cancel))
      ((null ss) (setq ok 'cancel))
      (t
       (setq aneis (av:aneis-da-selecao ss)
             AV:HND (av:handles ss))
       (if (null aneis)
         (princ "\n  Os objetos selecionados NAO formam um contorno fechado (confira as pontas / tolerancia). Tente de novo.")
         (progn
           (av:realca aneis)
           (setq area (apply 'max (mapcar '(lambda (a) (abs (av:area a))) aneis)))
           (princ (strcat "\n  Contorno(s) fechado(s): " (itoa (length aneis))
                          "   Area (maior): "
                          (rtos (/ (* area uc uc) 10000.0) 2 3) " m2"
                          (if (> (length aneis) 1)
                            "   (os demais aneis serao tratados como FUROS)" "")))
           (initget "Sim Nao")
           (setq r (vl-catch-all-apply
                     'getkword (list "\nConfirmar este contorno? [Sim/Nao] <Sim>: ")))
           (redraw)
           (cond
             ((vl-catch-all-error-p r) (setq ok 'cancel))
             ((or (null r) (= r "Sim")) (setq ok aneis))
           )
         )
       )
      )
    )
  )
  (if (eq ok 'cancel) nil ok)
)

;;; handles das entidades de uma selecao
(defun av:handles (ss / i r)
  (setq i 0 r nil)
  (while (< i (sslength ss))
    (setq r (cons (cdr (assoc 5 (entget (ssname ss i)))) r) i (1+ i))
  )
  (reverse r)
)

;;; ponto (WCS) -> (u tA tB sA sB) da corda que o contem;
;;; 'fora se o ponto nao estiver no contorno, 'borda se nao couber ferro
(defun av:corda (edges th cov pt / tt uu c r)
  (setq tt (+ (* (car pt) (cos th)) (* (cadr pt) (sin th)))
        uu (+ (* (- (car pt)) (sin th)) (* (cadr pt) (cos th)))
        r  nil)
  (foreach c (av:cortes edges uu cov)
    (if (and (>= tt (car c)) (<= tt (cadr c)))
      (setq r (list uu (car c) (cadr c) (caddr c) (cadddr c)))
    )
  )
  (cond
    ((null r) 'fora)
    ((<= (- (- (nth 2 r) (nth 4 r)) (+ (nth 1 r) (nth 3 r))) 1e-9) 'borda)
    (t r)
  )
)

;;; como av:corda, mas se o ponto ficou fora do contorno (laje alterada)
;;; usa a barra mais proxima dele.  Devolve (u tA tB sA sB) ou nil
(defun av:corda-perto (edges th cov esp pt / r ex tt uu best d dbest c)
  (setq r (av:corda edges th cov pt))
  (if (listp r)
    r
    (progn
      (setq ex (av:extensao edges)
            tt (+ (* (car pt) (cos th)) (* (cadr pt) (sin th)))
            uu (+ (* (- (car pt)) (sin th)) (* (cadr pt) (cos th)))
            best nil)
      (foreach u (av:posicoes (nth 0 ex) (nth 1 ex) cov esp)
        (foreach c (av:cortes edges u cov)
          (if (> (- (- (cadr c) (cadddr c)) (+ (car c) (caddr c))) 1e-9)
            (progn
              (setq d (+ (abs (- u uu))
                         (max 0.0 (- (car c) tt)) (max 0.0 (- tt (cadr c)))))
              (if (or (null best) (< d dbest))
                (setq best (list u (car c) (cadr c) (caddr c) (cadddr c)) dbest d))
            )
          )
        )
      )
      best
    )
  )
)

;;; ponto dentro do contorno -> (u tA tB sA sB) da corda que o contem, ou nil
;;; (o ponto clicado fica em AV:PKPT, para a edicao futura)
(defun av:pede-ponto (edges th cov / pt r)
  (setq r nil)
  (while (not r)
    (setq pt (vl-catch-all-apply
               'getpoint
               (list "\nClique num ponto DENTRO do contorno para desenhar o ferro: ")))
    (cond
      ((vl-catch-all-error-p pt) (setq r 'cancel))
      ((null pt) (setq r 'cancel))
      (t
       (setq pt (av:p2 (trans pt 1 0))
             r  (av:corda edges th cov pt))
       (cond
         ((eq r 'fora)
          (princ "\n  Ponto fora do contorno (ou dentro de um furo). Tente de novo.")
          (setq r nil))
         ((eq r 'borda)
          (princ "\n  Ponto muito proximo da borda: nao cabe ferro com esse cobrimento.")
          (setq r nil))
         (t (setq AV:PKPT pt))
       )
      )
    )
  )
  (if (eq r 'cancel) nil r)
)

;;; getpoint protegido
(defun av:pede-canto (msg / p)
  (setq p (vl-catch-all-apply 'getpoint (list msg)))
  (if (or (vl-catch-all-error-p p) (null p)) nil (av:p2 (trans p 1 0)))
)

;;; vertice do contorno que define a ponta "uu" da faixa (u = lo ou hi):
;;; entre os vertices com u = uu, o mais proximo (em t) da linha "tdim".
;;; devolve (t u) ou nil
(defun av:vert-ext (aneis th uu tdim / tol best q d dbest)
  (setq tol 1e-6 best nil)
  (foreach an aneis
    (foreach p an
      (setq q (av:xy-tu p th))
      (if (< (abs (- (cadr q) uu)) (max tol (* 1e-6 (abs uu))))
        (progn
          (setq d (abs (- (car q) tdim)))
          (if (or (null best) (< d dbest)) (setq best q dbest d))
        )
      )
    )
  )
  best
)

;;; getpoint opcional:  'cancel (ESC),  nil (ENTER)  ou  o ponto (WCS)
(defun av:pede-opc (msg / p)
  (setq p (vl-catch-all-apply 'getpoint (list msg)))
  (cond
    ((vl-catch-all-error-p p) 'cancel)
    ((null p) nil)
    (t (av:p2 (trans p 1 0)))
  )
)

;;; ==========================================================================
;;;  9.  LOGO DA BALUARTE
;;; ==========================================================================
;;;  Mesma marca usada em TABELAESTACAS / FUNDACAO: segmentos (x1 y1 x2 y2)
;;;  num quadrado 0..1000 com y crescendo para BAIXO (convencao do tile).
;;;  ATENCAO: lista LITERAL (com apostrofo).

(setq AV:LOGO_COR 34)

(setq AV:LOGO '(
    (77 682 77 296) (77 296 495 0) (495 0 513 2)
    (513 2 923 296) (923 296 923 682) (923 682 775 798)
    (775 798 773 618) (773 618 505 425) (505 425 479 439)
    (479 439 231 618) (231 618 231 798) (231 798 77 682)
    (152 598 500 354) (500 354 853 598) (853 598 853 307)
    (853 307 773 248) (773 248 773 354) (773 354 756 343)
    (756 343 708 307) (708 307 708 199) (708 199 638 150)
    (638 150 638 255) (638 255 627 249) (627 249 572 209)
    (572 209 572 101) (572 101 505 55) (505 55 500 55)
    (500 55 432 100) (432 100 432 209) (432 209 378 249)
    (378 249 367 255) (367 255 367 150) (367 150 297 201)
    (297 201 297 307) (297 307 247 344) (247 344 231 354)
    (231 354 231 248) (231 248 153 305) (153 305 152 598)
    (500 757 562 815) (562 815 562 958) (562 958 507 1000)
    (507 1000 498 998) (498 998 445 958) (445 958 445 813)
    (445 813 500 757)))

(defun av:le (v s) (fix (/ (* v s) 1000.0)))

(defun av:logo-desenha ( / w h s ox oy)
  (setq w (dimx_tile "logo") h (dimy_tile "logo")
        s (min w h) ox (/ (- w s) 2) oy (/ (- h s) 2))
  (start_image "logo")
  (fill_image 0 0 w h -15)
  (foreach g AV:LOGO
    (vector_image (+ ox (av:le (car g) s))   (+ oy (av:le (cadr g) s))
                  (+ ox (av:le (caddr g) s)) (+ oy (av:le (cadddr g) s))
                  AV:LOGO_COR))
  (end_image)
)

;;; ==========================================================================
;;;  10.  JANELA (DCL gerado em tempo de execucao)
;;; ==========================================================================

(defun av:defaults ()
  (if (null AV:P-PL1) (setq AV:P-PL1 "20"))
  (if (null AV:P-PT1) (setq AV:P-PT1 "10"))
  (if (null AV:P-PL2) (setq AV:P-PL2 "20"))
  (if (null AV:P-PT2) (setq AV:P-PT2 "10"))
  (if (null AV:P-AG1) (setq AV:P-AG1 "90"))       ; representacao das pernas
  (if (null AV:P-AG2) (setq AV:P-AG2 "90"))
  (if (null AV:P-PM)  (setq AV:P-PM  "200"))
  (if (null AV:P-LADO) (setq AV:P-LADO 0))
  (if (null AV:P-BIT) (setq AV:P-BIT 3))          ; 10 mm
  (if (null AV:P-ESP) (setq AV:P-ESP "15"))
  (if (null AV:P-COB) (setq AV:P-COB "3"))
  (if (null AV:P-POS) (setq AV:P-POS "1"))
  (if (null AV:P-REP) (setq AV:P-REP "1"))
  (if (null AV:P-ACO) (setq AV:P-ACO 0))
  (if (null AV:P-UNI) (setq AV:P-UNI 0))
  (if (null AV:P-ESC) (setq AV:P-ESC "50"))
  (if (null AV:P-ALT) (setq AV:P-ALT "2"))
  (if (null AV:P-SIM) (setq AV:P-SIM "1"))        ; desenha a simetrica
  (if (null AV:P-EMD) (setq AV:P-EMD "1"))        ; emenda barras longas
  (if (null AV:P-LCM) (setq AV:P-LCM "1200"))     ; comprimento comercial
  (if (null AV:P-TRA) (setq AV:P-TRA (av:fmt (nth AV:P-BIT AV:TRASP))))
  (if (null AV:P-DFS) (setq AV:P-DFS "1"))        ; alterna barras vizinhas
  (if (null AV:P-AFS) (setq AV:P-AFS "20"))       ; afastamento entre emendas
  (if (null AV:P-PIN) (setq AV:P-PIN ""))         ; 1.o pedaco (vazio = comercial)
  (if (null AV:P-EQU) (setq AV:P-EQU "0"))        ; tabela c/ comprimento equivalente
  (if (null AV:P-NUM) (setq AV:P-NUM 0))          ; numeracao manual
  (if (null AV:P-ELE) (setq AV:P-ELE ""))         ; elemento (agrupa a lista)
)

(defun av:write-dcl ( / f nome)
  (setq nome (strcat (getvar "TEMPPREFIX") "AV_ARMVAR.dcl")
        f    (open nome "w"))
  (foreach ln
   (list
"av_armvar : dialog {"
"  label = \"ARMADURA DE COMPRIMENTO VARIAVEL      v1.12      Baluarte\";"
"  width = 100;"
"  : boxed_row {"
"    label = \"Como usar\";"
"    : column {"
"      : text { label = \"1)  Configure a barra e a armadura; clique OK.\"; }"
"      : text { label = \"2)  Direcao: digite o angulo (graus) ou clique\"; }"
"      : text { label = \"      sobre uma linha.\"; }"
"      : text { label = \"3)  Selecione o CONTORNO FECHADO e confirme.\"; }"
"      : text { label = \"4)  Clique num ponto DENTRO do contorno.\"; }"
"    }"
"    : spacer { width = 2; }"
"    : column {"
"      : text { label = \"5)  Clique onde DESENHAR o ferro (ENTER = no ponto).\"; }"
"      : text { label = \"6)  Clique a LINHA DE DISTRIBUICAO (ENTER = auto).\"; }"
"      : text { label = \"7)  Indique onde vai a TABELA DE FERROS e o\"; }"
"      : text { label = \"      RESUMO DE ACO.\"; }"
"    }"
"  }"
"  : boxed_column {"
"    label = \"Formato da barra   (cm ;  0 = sem o trecho)\";"
"    : row {"
"      : boxed_column {"
"        label = \"Extremidade INICIAL\";"
"        : edit_box { key = \"pl1\"; label = \"Perna (perp.) :\"; edit_width = 7; }"
"        : edit_box { key = \"pt1\"; label = \"Ponta (paral.) :\";  edit_width = 7; }"
"        : edit_box { key = \"ag1\"; label = \"Desenho (graus) :\"; edit_width = 7; }"
"      }"
"      : column {"
"        : image { key = \"prev\"; width = 40; height = 7; color = -15; }"
"        : edit_box { key = \"pm\"; label = \"Principal (so previa) :\"; edit_width = 7; }"
"      }"
"      : boxed_column {"
"        label = \"Extremidade FINAL\";"
"        : edit_box { key = \"pl2\"; label = \"Perna (perp.) :\"; edit_width = 7; }"
"        : edit_box { key = \"pt2\"; label = \"Ponta (paral.) :\";  edit_width = 7; }"
"        : edit_box { key = \"ag2\"; label = \"Desenho (graus) :\"; edit_width = 7; }"
"      }"
"    }"
"    : text { label = \"Principal = VAR (vem do contorno); o valor acima so ajusta a previa.\"; }"
"    : text { label = \"Desenho da perna: 90 = no plano;  45 = entrando na tela;  135 = saindo da tela;  180 = dobrada (gancho).\"; }"
"    : popup_list { key = \"lado\"; label = \"Ganchos para o lado :\"; edit_width = 34; }"
"  }"
"  : row {"
"    : boxed_column {"
"      label = \"Armadura\";"
"      : popup_list { key = \"bit\"; label = \"Bitola (mm) :\";      edit_width = 10; }"
"      : popup_list { key = \"aco\"; label = \"Aco :\";              edit_width = 10; }"
"      : edit_box   { key = \"esp\"; label = \"Espacamento (cm) :\"; edit_width = 8; }"
"      : edit_box   { key = \"cob\"; label = \"Cobrimento (cm) :\";  edit_width = 8; }"
"      : edit_box   { key = \"pos\"; label = \"Posicao  N :\";       edit_width = 8; }"
"      : popup_list { key = \"num\"; label = \"Numeracao :\"; edit_width = 26; }"
"      : edit_box   { key = \"ele\"; label = \"Elemento (lista, ex.: L1) :\"; edit_width = 8; }"
"      : edit_box   { key = \"rep\"; label = \"Repeticoes (2 = simetria) :\"; edit_width = 5; }"
"      : toggle     { key = \"sim\"; label = \"Desenhar a barra simetrica invertida\"; }"
"      : text       { label = \"   (negativa, tracejada - se repeticoes >= 2)\"; }"
"    }"
"    : boxed_column {"
"      label = \"Emendas por traspasse\";"
"      : toggle   { key = \"emd\"; label = \"Emendar barras maiores que o comercial\"; }"
"      : edit_box { key = \"lcm\"; label = \"Comprimento comercial (cm) :\"; edit_width = 7; }"
"      : edit_box { key = \"tra\"; label = \"Traspasse  L  (cm) :\";         edit_width = 7; }"
"      : edit_box { key = \"pin\"; label = \"1.o pedaco (cm, vazio = comercial) :\"; edit_width = 7; }"
"      : toggle   { key = \"dfs\"; label = \"Alternar barras vizinhas (ALTER.)\"; }"
"      : edit_box { key = \"afs\"; label = \"Afastamento min. entre emendas (cm) :\"; edit_width = 7; }"
"      : text { label = \"L padrao: 40 (6.3 e 8), 50 (10), 60 (12.5);\"; }"
"      : text { label = \"demais bitolas 50 x diam. - CONFERIR.\"; }"
"    }"
"    : boxed_column {"
"      label = \"Unidades e texto\";"
"      : popup_list { key = \"uni\"; label = \"O desenho esta em :\"; edit_width = 26; }"
"      : edit_box   { key = \"esc\"; label = \"Escala de plotagem  1 :\"; edit_width = 8; }"
"      : edit_box   { key = \"alt\"; label = \"Altura do texto (mm) :\"; edit_width = 6; }"
"      : toggle     { key = \"equ\"; label = \"Tabela com comprimento unitario equivalente\"; }"
"      : text       { label = \"   (C.UNIT = C.TOTAL / QTD., uma linha por posicao)\"; }"
"      : text { label = \"Padrao TQS: cm de papel, escala 1:50, texto 2 mm.\"; }"
"    }"
"  }"
"  : boxed_column {"
"    label = \"AVISO IMPORTANTE  --  leia antes de usar\";"
"    : text { label = \"Esta rotina e uma FERRAMENTA DE APOIO. A conferencia do resultado e a\"; }"
"    : text { label = \"responsabilidade tecnica pelo projeto sao INTEIRAMENTE do engenheiro\"; }"
"    : text { label = \"responsavel. Confira SEMPRE os comprimentos, a tabela e o resumo de aco\"; }"
"    : text { label = \"antes de emitir o desenho. Os autores e a Baluarte nao se responsabilizam\"; }"
"    : text { label = \"por erros, omissoes ou prejuizos decorrentes do uso desta rotina.\"; }"
"  }"
"  : row {"
"    : image { key = \"logo\"; width = 11; aspect_ratio = 1.0; color = -15; }"
"    : column {"
"      : text { label = \"Desenvolvido por:\"; }"
     (strcat "      : text { label = \"Baluarte Solu" (chr 231) (chr 245) "es Estruturais\"; }")
     (strcat "      : text { label = \"Eng. Matusal" (chr 233) "m do Carmo de Oliveira\"; }")
"      : text { label = \"baluarteengenharia@outlook.com    /    matusa00@gmail.com\"; }"
"    }"
"    : spacer { width = 2; }"
"  }"
"  ok_cancel;"
"}"
   )
    (write-line ln f)
  )
  (close f)
  nome
)

;;; ---- previa da barra (tile "prev") ---------------------------------------
(defun av:tile-num (k / v)
  (setq v (av:num (get_tile k)))
  (if (or (null v) (< v 0.0)) 0.0 v)
)

(defun av:linha-g (x1 y1 x2 y2 cor)
  (vector_image x1 y1 x2 y2 cor)
  (vector_image x1 (1+ y1) x2 (1+ y2) cor)
  (vector_image (1+ x1) y1 (1+ x2) y2 cor)
)

(defun av:preview ( / w h m x1 x2 pm sc l1 t1 l2 t2 lado y0 dy p1 p2 tt a1 a2 q)
  (setq w (dimx_tile "prev") h (dimy_tile "prev")
        m 14 x1 m x2 (- w m)
        pm (av:tile-num "pm")
        l1 (av:tile-num "pl1") t1 (av:tile-num "pt1")
        l2 (av:tile-num "pl2") t2 (av:tile-num "pt2")
        lado (atoi (get_tile "lado"))
        a1 (* (if (av:num (get_tile "ag1")) (av:num (get_tile "ag1")) 90.0) (/ pi 180.0))
        a2 (* (if (av:num (get_tile "ag2")) (av:num (get_tile "ag2")) 90.0) (/ pi 180.0)))
  (if (< pm 1.0) (setq pm 200.0))
  (setq sc (/ (float (- x2 x1)) (max pm (+ t1 t2) 1.0)))
  ;; a barra fica na parte de cima (ganchos para baixo) ou de baixo
  (setq y0 (if (= lado 0) (fix (* h 0.25)) (fix (* h 0.75)))
        dy (if (= lado 0) 1 -1))
  (setq p1 (min (fix (* l1 sc)) (- (fix (* h 0.5)) 4))
        p2 (min (fix (* l2 sc)) (- (fix (* h 0.5)) 4)))
  (if (and (> l1 0.0) (< p1 4)) (setq p1 4))
  (if (and (> l2 0.0) (< p2 4)) (setq p2 4))
  (start_image "prev")
  (fill_image 0 0 w h -15)
  ;; principal
  (av:linha-g x1 y0 x2 y0 0)
  ;; extremidades: perna no angulo de desenho (u da imagem = dy) + ponta
  (foreach e (list (list x1 p1 a1 t1 nil) (list x2 p2 a2 t2 T))
    (if (> (cadr e) 0)
      (progn
        (setq AV:GAP 3
              q (av:perna-pts (car e) y0 (cadr e) (caddr e) dy (nth 4 e))
              AV:GAP nil)
        (setq m (list (car e) y0))
        (foreach r q
          (av:linha-g (fix (car m)) (fix (cadr m)) (fix (car r)) (fix (cadr r)) 1)
          (setq m r))
        (if (> (cadddr e) 0.0)
          (progn
            (setq tt (max 4 (fix (* (cadddr e) sc))))
            (av:linha-g (fix (car m)) (fix (cadr m)) (fix (+ (car m) (if (nth 4 e) (- tt) tt))) (fix (cadr m)) 5))))))
  (end_image)
  ;; ponta so faz sentido com perna
  (mode_tile "pt1" (if (> l1 0.0) 0 1))
  (mode_tile "pt2" (if (> l2 0.0) 0 1))
)

;;; habilita / desabilita os campos de emenda
(defun av:modo-emd ( / m)
  (setq m (if (= (get_tile "emd") "1") 0 1))
  (foreach k '("lcm" "tra" "pin" "dfs") (mode_tile k m))
  (mode_tile "afs" (if (and (= m 0) (= (get_tile "dfs") "1")) 0 1))
)

;;; le e valida os campos; devolve T se ok
(defun av:le-tiles ( / v msg)
  (setq msg nil)
  (foreach k '("pl1" "pt1" "pl2" "pt2" "pm")
    (if (and (null msg) (or (null (av:num (get_tile k))) (< (av:num (get_tile k)) 0.0)))
      (setq msg (list k "Informe um numero maior ou igual a zero (cm)."))
    )
  )
  (foreach k '("ag1" "ag2")
    (if (and (null msg) (or (null (av:num (get_tile k))) (< (av:num (get_tile k)) 0.0) (> (av:num (get_tile k)) 360.0)))
      (setq msg (list k "Angulo de desenho da perna em graus (0 a 360): 90, 45, 135 ou 180."))
    )
  )
  (if (and (null msg) (or (null (av:num (get_tile "esp"))) (<= (av:num (get_tile "esp")) 0.0)))
    (setq msg (list "esp" "O espacamento deve ser maior que zero.")))
  (if (and (null msg) (or (null (av:num (get_tile "cob"))) (< (av:num (get_tile "cob")) 0.0)))
    (setq msg (list "cob" "O cobrimento deve ser um numero maior ou igual a zero.")))
  (if (and (null msg) (or (null (av:num (get_tile "pos"))) (< (av:num (get_tile "pos")) 1.0)))
    (setq msg (list "pos" "A posicao (N) deve ser um inteiro maior ou igual a 1.")))
  (if (and (null msg) (or (null (av:num (get_tile "rep"))) (< (av:num (get_tile "rep")) 1.0)))
    (setq msg (list "rep" "As repeticoes devem ser um inteiro maior ou igual a 1.")))
  (if (and (null msg) (or (null (av:num (get_tile "lcm"))) (< (av:num (get_tile "lcm")) 100.0)))
    (setq msg (list "lcm" "O comprimento comercial deve ser de pelo menos 100 cm (padrao 1200).")))
  (if (and (null msg) (or (null (av:num (get_tile "tra"))) (< (av:num (get_tile "tra")) 0.0)
                          (>= (* 3.0 (av:num (get_tile "tra"))) (av:num (get_tile "lcm")))))
    (setq msg (list "tra" "O traspasse deve ser >= 0 e menor que 1/3 do comprimento comercial.")))
  (if (and (null msg) (/= (vl-string-trim " " (get_tile "pin")) "")
           (or (null (av:num (get_tile "pin")))
               (< (av:num (get_tile "pin")) (* 2.0 (av:num (get_tile "tra"))))
               (> (av:num (get_tile "pin")) (av:num (get_tile "lcm")))))
    (setq msg (list "pin" "O 1.o pedaco deve ficar entre 2 x L e o comprimento comercial (ou vazio).")))
  (if (and (null msg) (or (null (av:num (get_tile "afs"))) (< (av:num (get_tile "afs")) 0.0)))
    (setq msg (list "afs" "O afastamento entre emendas deve ser >= 0 (padrao 20 cm).")))
  (if (and (null msg) (or (null (av:num (get_tile "esc"))) (<= (av:num (get_tile "esc")) 0.0)))
    (setq msg (list "esc" "A escala deve ser maior que zero (ex.: 50).")))
  (if (and (null msg) (or (null (av:num (get_tile "alt"))) (<= (av:num (get_tile "alt")) 0.0)))
    (setq msg (list "alt" "A altura do texto deve ser maior que zero (ex.: 2).")))
  (if msg
    (progn
      (alert (cadr msg))
      (mode_tile (car msg) 2)
      nil
    )
    (progn
      (setq AV:P-AG1 (av:fmt (av:num (get_tile "ag1"))) AV:P-AG2 (av:fmt (av:num (get_tile "ag2"))))
      (setq AV:P-PL1 (get_tile "pl1") AV:P-PT1 (get_tile "pt1")
            AV:P-PL2 (get_tile "pl2") AV:P-PT2 (get_tile "pt2")
            AV:P-PM  (get_tile "pm")  AV:P-LADO (atoi (get_tile "lado"))
            AV:P-BIT (atoi (get_tile "bit")) AV:P-ACO (atoi (get_tile "aco"))
            AV:P-ESP (get_tile "esp") AV:P-COB (get_tile "cob")
            AV:P-POS (get_tile "pos") AV:P-REP (get_tile "rep")
            AV:P-UNI (atoi (get_tile "uni")) AV:P-ESC (get_tile "esc")
            AV:P-ALT (get_tile "alt")
            AV:P-SIM (get_tile "sim") AV:P-EMD (get_tile "emd")
            AV:P-LCM (get_tile "lcm") AV:P-TRA (get_tile "tra")
            AV:P-DFS (get_tile "dfs") AV:P-AFS (get_tile "afs")
            AV:P-PIN (vl-string-trim " " (get_tile "pin"))
            AV:P-EQU (get_tile "equ")
            AV:P-NUM (atoi (get_tile "num"))
            AV:P-ELE (vl-string-trim " " (get_tile "ele")))
      T
    )
  )
)

;;; devolve T se o usuario confirmou (OK)
(defun av:dialog ( / dcl id res)
  (av:defaults)
  (setq dcl (av:write-dcl) id (load_dialog dcl))
  (if (< id 0)
    (progn (princ "\n*** Nao foi possivel carregar o DCL.") (setq res 0))
    (if (not (new_dialog "av_armvar" id))
      (setq res 0)
      (progn
        (start_list "bit") (mapcar 'add_list AV:BITOLAS) (end_list)
        (start_list "aco") (mapcar 'add_list AV:ACOS) (end_list)
        (start_list "uni") (mapcar 'add_list AV:UNIDADES) (end_list)
        (start_list "lado") (mapcar 'add_list AV:LADOS) (end_list)
        (set_tile "pl1" AV:P-PL1) (set_tile "pt1" AV:P-PT1)
        (set_tile "ag1" AV:P-AG1) (set_tile "ag2" AV:P-AG2)
        (set_tile "pl2" AV:P-PL2) (set_tile "pt2" AV:P-PT2)
        (set_tile "pm"  AV:P-PM)
        (set_tile "lado" (itoa AV:P-LADO))
        (set_tile "bit" (itoa AV:P-BIT))
        (set_tile "aco" (itoa AV:P-ACO))
        (set_tile "esp" AV:P-ESP) (set_tile "cob" AV:P-COB)
        (set_tile "pos" AV:P-POS) (set_tile "rep" AV:P-REP)
        (set_tile "uni" (itoa AV:P-UNI))
        (set_tile "esc" AV:P-ESC) (set_tile "alt" AV:P-ALT)
        (set_tile "sim" AV:P-SIM) (set_tile "emd" AV:P-EMD)
        (set_tile "lcm" AV:P-LCM) (set_tile "tra" AV:P-TRA)
        (set_tile "dfs" AV:P-DFS) (set_tile "afs" AV:P-AFS)
        (set_tile "pin" AV:P-PIN)
        (set_tile "equ" AV:P-EQU)
        (start_list "num") (mapcar 'add_list AV:NUMS) (end_list)
        (set_tile "num" (itoa (if (av:rp-p) 0 AV:P-NUM)))
        (set_tile "ele" AV:P-ELE)
        ;; na edicao a numeracao e a do proprio detalhamento
        (if (av:rp-p) (mode_tile "num" 1))
        (vl-catch-all-apply 'av:logo-desenha nil)
        (vl-catch-all-apply 'av:preview nil)
        (vl-catch-all-apply 'av:modo-emd nil)
        (foreach k '("pl1" "pt1" "pl2" "pt2" "pm" "lado" "ag1" "ag2")
          (action_tile k "(vl-catch-all-apply 'av:preview nil)")
        )
        ;; trocou a bitola: traspasse padrao da bitola
        (action_tile "bit" "(set_tile \"tra\" (av:fmt (nth (atoi $value) AV:TRASP)))")
        (action_tile "emd" "(av:modo-emd)")
        (action_tile "dfs" "(av:modo-emd)")
        (action_tile "accept" "(if (av:le-tiles) (done_dialog 1))")
        (action_tile "cancel" "(done_dialog 0)")
        (setq res (start_dialog))
      )
    )
  )
  (if (> id 0) (unload_dialog id))
  (= res 1)
)

;;; ==========================================================================
;;;  11.  COMANDO PRINCIPAL
;;; ==========================================================================

;;; inteiro mais proximo
(defun av:int (v) (fix (+ v 0.5)))

;;; ((1200 . 1) (165 . 2)) -> "N.1 N.2"
(defun av:ptxt-lista (posl / r)
  (setq r nil)
  (foreach g posl
    (setq r (if r (strcat r " N." (itoa (cdr g))) (strcat "N." (itoa (cdr g))))))
  r
)

;;; (890 450) -> "890+450"
(defun av:junta (l / r)
  (setq r (itoa (car l)))
  (foreach v (cdr l) (setq r (strcat r "+" (itoa v))))
  r
)

(defun c:ARMVAR ( / *error* doc th aneis edges ex uc esc h cov esp espcm bit kgm
                    hooks lado pos pref rep bars u c total-cm b hsum grupos
                    tot nbar ctot pk lo hi umin umax pt1 pt2 marcou g posu
                    iu ini fim emd lcom lap afs dfs pini neg pcs npcs nemd tots
                    ctxt mtxt ta tb ud tdim tc tr pcsr pcsa r ok nota chama anc k
                    posl sep ptx espl linhas pvs pvg ocup0 idl)
  (defun *error* (msg)
    (if (and msg (not (wcmatch (strcase msg) "*CANCEL*,*QUIT*,*EXIT*")))
      (princ (strcat "\n*** Erro: " msg (if AV:ETAPA (strcat "  [etapa: " AV:ETAPA "]") ""))))
    (if marcou (vl-catch-all-apply 'vla-EndUndoMark (list doc)))
    (setq AV:ID nil AV:TAG nil AV:GRP nil AV:OCUP nil)
    (vl-catch-all-apply 'redraw nil)
    (princ)
  )
  (setq doc (vla-get-ActiveDocument (vlax-get-acad-object)) marcou nil
        AV:REC nil AV:ID nil AV:TAG nil AV:ETAPA "0 janela")

  (if (not (if AV:SEMDLG T (av:dialog)))
    (progn (princ "\nCancelado.") (princ))
    (progn
      ;; numeracao automatica (so na criacao)
      (if (not (av:rp-p)) (av:numera))
      ;; ---- parametros da janela ----------------------------------------
      (setq esc  (av:num AV:P-ESC)
            uc   (cond ((= AV:P-UNI 0) esc) ((= AV:P-UNI 1) 100.0)
                       ((= AV:P-UNI 2) 1.0) (t 0.1))
            ;; altura do texto (unidades do desenho): alt mm plotados x escala
            h    (/ (* (/ (av:num AV:P-ALT) 10.0) esc) uc)
            cov  (/ (av:num AV:P-COB) uc)
            espcm (av:num AV:P-ESP)
            esp  (/ espcm uc)
            bit  (nth AV:P-BIT AV:BITOLAS)
            kgm  (nth AV:P-BIT AV:MASSAS)
            hooks (list (av:num AV:P-PL1) (av:num AV:P-PT1)
                        (av:num AV:P-PL2) (av:num AV:P-PT2)
                        ;; angulos de DESENHO das pernas (rad): so representacao
                        (* (if (av:num AV:P-AG1) (av:num AV:P-AG1) 90.0) (/ pi 180.0))
                        (* (if (av:num AV:P-AG2) (av:num AV:P-AG2) 90.0) (/ pi 180.0)))
            lado AV:P-LADO
            pos  (fix (av:num AV:P-POS))
            rep  (fix (av:num AV:P-REP))
            pref (strcat "N" (itoa pos))
            ;; simetria e emendas
            neg  (and (= AV:P-SIM "1") (> rep 1))
            emd  (= AV:P-EMD "1")
            lcom (av:int (av:num AV:P-LCM))
            lap  (av:int (av:num AV:P-TRA))
            dfs  (= AV:P-DFS "1")
            afs  (av:int (av:num AV:P-AFS))
            ;; 1.o pedaco informado (vazio / 0 = comprimento comercial)
            pini (if (av:num AV:P-PIN) (av:int (av:num AV:P-PIN)) 0))
      ;; ponta sem perna nao existe
      (if (<= (nth 0 hooks) 0.0) (setq hooks (av:setnth hooks 1 0.0)))
      (if (<= (nth 2 hooks) 0.0) (setq hooks (av:setnth hooks 3 0.0)))
      (setq ini  (+ (nth 0 hooks) (nth 1 hooks))
            fim  (+ (nth 2 hooks) (nth 3 hooks))
            hsum (+ ini fim))

      (setq AV:ETAPA "1 direcao")
      ;; ---- 1) direcao --------------------------------------------------
      (setq th (av:gr "dir" (if (av:rp-p) (av:rp "dir") (av:pede-direcao))))
      (if (null th)
        (princ "\nCancelado.")
        (progn
          (setq AV:ETAPA "2 contorno")
          ;; ---- 2) contorno --------------------------------------------
          (setq aneis (if (av:rp-p) (av:aneis-replay) (av:pede-contorno uc)))
          (av:gr "anel" aneis)
          (av:gr "hnd" AV:HND)
          (if (null aneis)
            (princ "\nCancelado.")
            (progn
              (setq edges (av:arestas aneis th)
                    ex    (av:extensao edges)
                    umin  (nth 0 ex) umax (nth 1 ex)
                    lo    umin hi umax)
              (setq AV:ETAPA "3 barras")
              ;; ---- 3) barras --------------------------------------------
              ;;      cada barra = (u  principal-cm  indice-da-posicao-u)
              (setq bars nil iu 0 posu (av:posicoes umin umax cov esp))
              (if (and (cdr posu) (< (* (- (cadr posu) (car posu)) uc) (- espcm 0.01)))
                (princ (strcat "
  ATENCAO: para respeitar o cobrimento o espacamento real ficou "
                               (rtos (* (- (cadr posu) (car posu)) uc) 2 1) " cm."))
              )
              (foreach u posu
                (foreach c (av:cortes edges u cov)
                  (setq total-cm (* (- (- (cadr c) (cadddr c)) (+ (car c) (caddr c))) uc))
                  (if (> total-cm 1e-6)
                    (setq bars (cons (list u total-cm iu) bars))
                  )
                )
                (setq iu (1+ iu))
              )
              (setq bars (reverse bars))
              (if (null bars)
                (princ "\nNenhuma barra cabe no contorno com esse cobrimento/espacamento.")
                (progn
                  ;; comprimentos totais (principal + pernas + pontas), em cm,
                  ;; ja divididos em pedacos <= comercial (com traspasse)
                  (setq grupos nil tots nil npcs 0 nemd 0)
                  (foreach b bars
                    (setq tot (av:int (+ (cadr b) hsum)))
                    (if (not (member tot tots)) (setq tots (cons tot tots)))
                    (setq pcs (if emd (av:divide tot ini fim lcom lap afs pini dfs) (list tot)))
                    ;; barras alternadas: mesmos pedacos em ordem inversa
                    (if (and emd dfs (= 1 (rem (caddr b) 2)))
                      (setq pcs (av:inverte pcs ini fim)))
                    (if (cdr pcs) (setq nemd (1+ nemd)))
                    (foreach g pcs
                      (setq npcs (1+ npcs))
                      (if (assoc g grupos)
                        (setq grupos (subst (cons g (1+ (cdr (assoc g grupos))))
                                            (assoc g grupos) grupos))
                        (setq grupos (cons (cons g 1) grupos))
                      )
                    )
                  )
                  (setq grupos (vl-sort grupos '(lambda (a b) (< (car a) (car b))))
                        tots   (vl-sort tots '<)
                        nbar   (length bars)
                        ctot   0.0)
                  (foreach g grupos (setq ctot (+ ctot (* 1.0 (car g) (cdr g)))))
                  (setq ctot (* ctot rep))
                  ;; "C=368" se todas iguais ("C=890+450" se emendadas);
                  ;; senao "C=VAR"
                  (if (= (length tots) 1)
                    (setq ctxt (av:junta (if emd (av:divide (car tots) ini fim lcom lap afs pini dfs)
                                                 (list (car tots))))
                          mtxt (av:fmt (- (car tots) hsum)))
                    (setq ctxt "VAR" mtxt "VAR")
                  )
                  ;; comprimento constante e emendado: cada pedaco vira uma
                  ;; POSICAO separada (N.1, N.2, ...), como no detalhe de parede
                  (setq posl nil sep nil)
                  (if (and emd (= (length tots) 1))
                    (progn
                      (setq pcs (av:divide (car tots) ini fim lcom lap afs pini dfs)
                            k   pos)
                      (if (cdr pcs)
                        (progn
                          (setq sep T)
                          (foreach g (append pcs (if dfs (av:inverte pcs ini fim)))
                            (if (not (assoc g posl))
                              (setq posl (append posl (list (cons g k))) k (1+ k)))
                          )
                        )
                      )
                    )
                  )
                  (princ (strcat "\n  " (itoa nbar) " barra(s) por repeticao, "
                                 (itoa (length tots)) " comprimento(s) diferente(s)"
                                 " (de " (itoa (car tots)) " a "
                                 (itoa (av:ultimo tots)) " cm)."))
                  (if (> nemd 0)
                    (princ (strcat "\n  " (itoa nemd) " barra(s) acima de "
                                   (itoa lcom) " cm: emendadas por traspasse L = "
                                   (itoa lap) " cm  (" (itoa npcs) " pedacos por repeticao).")))
                  (if (and (not emd) (> (av:ultimo tots) lcom))
                    (princ (strcat "\n  ATENCAO: ha barras acima de " (itoa lcom)
                                   " cm e as emendas estao desligadas.")))
                  (if sep
                    (progn
                      (princ "\n  Posicoes separadas:")
                      (foreach g posl
                        (princ (strcat "  N." (itoa (cdr g)) " C=" (itoa (car g))
                                       " (" (itoa (cdr (assoc (car g) grupos))) ")")))
                      (princ (strcat "\n  Proxima posicao livre: N." (itoa k)))
                    )
                  )
                  (setq AV:ETAPA "4 ponto do ferro")
                  ;; ---- 4) ponto do ferro --------------------------------
                  (if (av:rp-p)
                    (progn
                      (setq AV:PKPT (av:rp "pk")
                            pk (if AV:PKPT (av:corda-perto edges th cov esp AV:PKPT)))
                      (if (null pk)
                        (princ "\n*** Nenhuma barra cabe no contorno alterado: nada foi refeito.")))
                    (setq pk (av:pede-ponto edges th cov))
                  )
                  (av:gr "pk" AV:PKPT)
                  (if (null pk)
                    (princ "\nCancelado.")
                    (progn
                      (setq ud (nth 0 pk)
                            ta (+ (nth 1 pk) (nth 3 pk))
                            tb (- (nth 2 pk) (nth 4 pk))
                            tc (/ (+ ta tb) 2.0)
                            ok T)
                      (setq AV:ETAPA "5 posicao do desenho")
                      ;; ---- 5) onde desenhar o ferro ---------------------
                      (setq r (if (av:rp-p) (av:rp "pd")
                                (av:pede-opc "\nPosicao do DESENHO do ferro - clique (ENTER = no ponto escolhido): ")))
                      (av:gr "pd" (if (listp r) r))
                      (cond ((eq r 'cancel) (setq ok nil))
                            (r (setq ud (cadr (av:xy-tu r th)))))
                      ;; ---- 6) linha de distribuicao ---------------------
                      ;;      automatica: fora do texto centrado do ferro
                      (setq tr   (+ (* 0.35 h (strlen (av:txt-ferro rep pos nbar bit espcm ctxt)))
                                    (* 1.5 h))
                            tdim (+ tc (max tr (* 0.3 (- tb ta)))))
                      (if (> tdim (- tb h)) (setq tdim (+ tb (* 3.0 h))))
                      (if ok
                        (progn
                          (setq r (if (av:rp-p) (av:rp "pf")
                                    (av:pede-opc "\nPosicao da LINHA DE DISTRIBUICAO - clique (ENTER = automatica): ")))
                          (av:gr "pf" (if (listp r) r))
                          (cond ((eq r 'cancel) (setq ok nil))
                                (r (setq tdim (car (av:xy-tu r th)))))
                        )
                      )
                      (setq AV:ETAPA "6a linhas de extensao")
                      ;; ---- 6a) linhas de extensao da faixa, nas DUAS pontas ---
                      ;;      padrao: vertices do contorno que definem cada
                      ;;      ponta; um vertice clicado substitui o da ponta
                      ;;      mais proxima
                      (setq anc (list (av:vert-ext aneis th lo tdim)
                                      (av:vert-ext aneis th hi tdim))
                            k 0 pvs (av:rp "pv") pvg nil)
                      (while (and ok (< k 2))
                        (setq r (if (av:rp-p)
                                  (av:nth k pvs)
                                  (av:pede-opc (if (= k 0)
                                    "\nVertice para a LINHA DE EXTENSAO da faixa (ENTER = cantos do contorno): "
                                    "\nVertice para a outra ponta da faixa (ENTER = canto do contorno): "))))
                        (if (and r (listp r)) (setq pvg (append pvg (list r))))
                        (cond ((eq r 'cancel) (setq ok nil))
                              ((null r) (setq k 2))
                              (t (setq r (av:xy-tu r th))
                                 (if (< (abs (- (cadr r) lo)) (abs (- (cadr r) hi)))
                                   (setq anc (list r (cadr anc)))
                                   (setq anc (list (car anc) r)))
                                 (setq k (1+ k))))
                      )
                      (av:gr "pv" pvg)
                      (setq AV:ETAPA "6b linha de chamada")
                      ;; ---- 6b) faixa fora do ferro: linha de chamada ---------
                      (setq chama nil)
                      (if (and ok (or (< tdim ta) (> tdim tb)))
                        (progn
                          (setq r (if (av:rp-p) (av:rp "pc")
                                    (av:pede-opc "\nPonto da LINHA DE CHAMADA (bolinha no ferro) - clique (ENTER = automatico): ")))
                          (av:gr "pc" (if (listp r) r))
                          (cond ((eq r 'cancel) (setq ok nil))
                                (r (setq chama (av:xy-tu r th))))
                        )
                      )
                      (if (not ok)
                        (princ "\nCancelado.")
                        (progn
                          ;; pedacos da barra representada e da vizinha (ALTER.)
                          (setq tr   (av:int (+ (* (- tb ta) uc) hsum))
                                pcsr (if emd (av:divide tr ini fim lcom lap afs pini dfs) (list tr))
                                pcsa (if (and dfs (cdr pcsr)) (av:inverte pcsr ini fim)))
                          (setq AV:ETAPA "7 desenho do ferro")
                          ;; ---- 7) desenha o ferro e a faixa --------------
                          (if (or (not AV:SEMDLG) AV:EDITA) (progn (vla-StartUndoMark doc) (setq marcou T)))
                          (setq ocup0 AV:OCUP AV:OCUP T)  ; reatores ignoram as nossas alteracoes
                          (av:prepara)
                          ;; edicao: reusa o id (o bloco sera redefinido)
                          (setq AV:ID (if (av:rp-p) AV:ED-ID (av:novo-id)) AV:GRP "DET")
                          ;; restos soltos de uma tentativa anterior
                          (foreach g '("DET" "T1" "T2")
                            (foreach e (av:soltos AV:ID g) (entdel e)))
                          ;; posicoes separadas: "N.1 N.2" e um texto por pedaco
                          (setq ptx (if sep (av:ptxt-lista posl) pos)
                                espl (if sep
                                       (mapcar '(lambda (g)
                                                  (av:txt-ferro rep
                                                    (if (assoc g posl) (cdr (assoc g posl)) pos)
                                                    (if (assoc g grupos) (cdr (assoc g grupos)) nbar)
                                                    bit espcm (itoa g)))
                                               pcsr)))
                          (av:desenha th ud ta tb lo hi tdim hooks lado h uc
                                      (av:txt-ferro rep pos nbar bit espcm ctxt)
                                      (av:txt-faixa rep ptx nbar bit espcm)
                                      (strcat "(" (rtos (* (- hi lo) uc) 2 0) ")")
                                      mtxt pcsr neg lap pcsa
                                      (strcat (av:rep-txt rep) "N." (itoa pos) " %%c " bit
                                              " C/" (av:fmt espcm) " ALTER.")
                                      chama anc espl)
                          (setq AV:ETAPA "8 tabelas")
                          ;; ---- 8) tabelas --------------------------------
                          (setq AV:GRP "T1")
                          (setq nota (if (> nemd 0)
                                       (strcat "EMENDAS POR TRASPASSE: L = " (itoa lap)
                                               " cm  (BARRAS > " (itoa lcom) " cm)"
                                               (if dfs " - BARRAS ALTERNADAS" ""))))
                          (setq pt1 (av:gr "t1" (if (av:rp-p) (av:rp "t1")
                                      (av:pede-canto "\nClique no canto superior esquerdo da TABELA DE FERROS VARIAVEIS (ENTER = nao gerar): "))))
                          ;; linhas por posicao: ((pos qtd ctot variavel) ...)
                          ;; variavel = T quando as barras da posicao tem mais de
                          ;; um comprimento (a LISTA geral mostra "VAR.")
                          (setq linhas
                                (if sep
                                  (mapcar '(lambda (g / q)
                                             (setq q (* rep (cdr (assoc (car g) grupos))))
                                             (list (strcat "N" (itoa (cdr g))) q (* 1.0 q (car g)) nil))
                                          posl)
                                  (list (list pref (* npcs rep) ctot (if (cdr grupos) T nil)))))
                          (if pt1
                            (if (= AV:P-EQU "1")
                              ;; comprimento unitario equivalente (total / qtd.)
                              (av:tab-equiv pt1 h ptx rep bit espcm nbar linhas nota)
                              (if sep
                                (av:tab-ferros pt1 h ptx pref rep bit espcm
                                               (mapcar '(lambda (g) (cons (car g) (cdr (assoc (car g) grupos)))) posl)
                                               nbar nota
                                               (mapcar '(lambda (g) (strcat "N" (itoa (cdr g)))) posl))
                                (av:tab-ferros pt1 h pos pref rep bit espcm grupos nbar nota nil)
                              )
                            )
                          )
                          (setq AV:GRP "T2")
                          (setq pt2 (av:gr "t2" (if (av:rp-p) (av:rp "t2")
                                      (av:pede-canto "\nClique no canto superior esquerdo do RESUMO DE ACO (ENTER = nao gerar): "))))
                          (if pt2
                            (av:tab-aco pt2 h linhas bit (nth AV:P-ACO AV:ACOS) kgm)
                          )
                          (setq AV:ETAPA "9 blocos")
                          ;; ---- 9) elemento parametrizado: blocos -------------
                          (setq AV:GRP nil)
                          (av:empacota AV:ID "DET" (av:params->atrs) h)
                          (av:empacota AV:ID "T1" nil h)
                          (av:empacota AV:ID "T2" nil h)
                          (setq AV:ETAPA "10 dados e lista")
                          ;; ---- 10) dados para edicao futura e lista geral --
                          (av:reg-grava AV:ID
                            (append
                              (list (list "ver" 12)
                                    (list "p" (mapcar 'eval AV:PARAMS))
                                    (list "h" h)
                                    (list "res" (mapcar '(lambda (ln)
                                                           (list (car ln) bit (cadr ln) (caddr ln)
                                                                 (nth AV:P-ACO AV:ACOS) kgm
                                                                 (if AV:P-ELE AV:P-ELE "")
                                                                 (if (av:nth 3 ln) "VAR" "")))
                                                        linhas)))
                              AV:REC))
                          (princ (strcat "\n  Detalhamento " AV:ID
                                         (if (av:rp-p) " atualizado (bloco " " criado como bloco (")
                                         (av:nome-bloco AV:ID "DET")
                                         "). Edite os atributos na janela Propriedades,"
                                         " com duplo clique ou com ARMVAREDIT."))
                          (setq idl AV:ID AV:ID nil AV:ETAPA "10 listas")
                          (av:lista-auto h idl)
                          (if marcou (progn (vla-EndUndoMark doc) (setq marcou nil)))
                          (setq AV:OCUP ocup0)
                          (setq AV:ETAPA "11 reatores")
                          (if (not AV:SEMDLG) (av:reat-liga))
                          ;; a janela ja abre na proxima posicao livre
                          (if (not (av:rp-p))
                            (setq AV:P-POS (itoa (+ pos (if sep (length posl) 1)))))
                          (princ (strcat "\nConcluido:  " (av:rep-txt rep) "N." (itoa pos)
                                         "  %%c" bit "  -  "
                                         (rtos (/ ctot 100.0) 2 2) " m  /  "
                                         (rtos (* (/ ctot 100.0) kgm) 2 1) " kg."))
                        )
                      )
                    )
                  )
                )
              )
            )
          )
        )
      )
      (princ)
    )
  )
)

;;; ==========================================================================
;;;  12.  EDICAO E LISTA
;;; ==========================================================================

;;; parametros de um detalhamento: os guardados, corrigidos pelos ATRIBUTOS
;;; do bloco (que o usuario pode ter editado)
(defun av:params-de (id rec / ins)
  (av:set-params (cadr (assoc "p" rec)))
  (if (setq ins (av:insert-de id "DET"))
    (av:atrs->params (av:atr-le ins)))
)

;;; os atributos do bloco diferem dos dados guardados?
(defun av:atrs-mudaram-p (id rec / salvo r)
  (setq salvo (mapcar 'eval AV:PARAMS))
  (av:params-de id rec)
  (setq r (not (equal (mapcar 'eval AV:PARAMS) (cadr (assoc "p" rec)))))
  (mapcar 'set AV:PARAMS salvo)
  r
)

;;; escreve nos atributos do bloco os parametros guardados
(defun av:atrs-restaura (id rec / salvo ins)
  (if (setq ins (av:insert-de id "DET"))
    (progn
      (setq salvo (mapcar 'eval AV:PARAMS))
      (av:set-params (cadr (assoc "p" rec)))
      (av:atr-grava ins (av:params->atrs))
      (mapcar 'set AV:PARAMS salvo)
    )
  )
)

;;; refaz um detalhamento sem perguntar nada (contorno relido, atributos)
(defun av:regenera (id / rec salvo)
  (if (setq rec (av:reg-le id))
    (progn
      (setq salvo (mapcar 'eval AV:PARAMS))
      (av:params-de id rec)
      (setq AV:RESP rec AV:MODO 'replay AV:ED-ID id AV:SEMDLG T)
      (av:roda 'c:ARMVAR nil (strcat "atualizando " id))
      (mapcar 'set AV:PARAMS salvo)
      (setq AV:MODO nil AV:ED-ID nil AV:RESP nil AV:ID nil AV:SEMDLG nil AV:GRP nil)
    )
  )
)

;;; ---- ARMVAREDIT: menu do que editar ----------------------------------------
;;;  Os pontos novos sao pedidos ANTES de redesenhar (ESC cancela sem mexer
;;;  em nada) e gravados nas respostas guardadas; o detalhamento e refeito
;;;  com elas.  Os pontos do desenho ficam no sistema do BLOCO: se o bloco
;;;  foi movido/girado, o clique e convertido para que o elemento apareca
;;;  exatamente onde foi clicado.

;;; ponto (WCS) -> sistema do bloco "grp" do detalhamento id
(defun av:bloco-pt (p id grp / ins ed b sx sy a x y)
  (if (and p (listp p) (setq ins (av:insert-de id grp)))
    (progn
      (setq ed (entget ins) b (cdr (assoc 10 ed))
            sx (cdr (assoc 41 ed)) sy (cdr (assoc 42 ed)) a (cdr (assoc 50 ed)))
      (if (or (null sx) (equal sx 0.0 1e-12)) (setq sx 1.0))
      (if (or (null sy) (equal sy 0.0 1e-12)) (setq sy 1.0))
      (if (null a) (setq a 0.0))
      (setq x (- (car p) (car b)) y (- (cadr p) (cadr b)))
      (list (/ (+ (* x (cos a)) (* y (sin a))) sx)
            (/ (- (* y (cos a)) (* x (sin a))) sy))
    )
    p
  )
)

;;; troca (ou cria) a resposta k nas respostas da edicao
(defun av:resp-muda (k v)
  (setq AV:RESP (cons (list k v)
                      (vl-remove-if '(lambda (x) (and (listp x) (= (car x) k))) AV:RESP)))
)

;;; clique opcional convertido para o bloco: 'cancel, nil (ENTER) ou ponto
(defun av:ed-pede (msg id grp / r)
  (setq r (av:pede-opc msg))
  (if (and r (listp r)) (av:bloco-pt r id grp) r)
)

;;; canto de tabela: ENTER = manter, N = nao gerar
(defun av:ed-tabela (msg atual id grp / p)
  (initget "Nao")
  (setq p (vl-catch-all-apply 'getpoint (list msg)))
  (cond
    ((vl-catch-all-error-p p) 'cancel)
    ((null p) (list atual))
    ((= (type p) 'STR) (list nil))
    (t (list (av:bloco-pt (av:p2 (trans p 1 0)) id grp)))
  )
)

;;; pede os pontos das chaves ks; devolve T (ok) ou nil (cancelado)
(defun av:ed-pergunta (id ks / ok r l k)
  (setq ok T)
  (if (and ok (member "pk" ks))
    (progn
      (setq r (av:pede-opc "\nClique num ponto DENTRO do contorno: barra que o ferro representa (ENTER = manter): "))
      (cond ((eq r 'cancel) (setq ok nil))
            (r (av:resp-muda "pk" r)))))
  (if (and ok (member "pd" ks))
    (progn
      (setq r (av:ed-pede "\nNova posicao do DESENHO do ferro - clique (ENTER = sobre a barra): " id "DET"))
      (if (eq r 'cancel) (setq ok nil) (av:resp-muda "pd" r))))
  (if (and ok (member "pf" ks))
    (progn
      (setq r (av:ed-pede "\nNova posicao da LINHA DE DISTRIBUICAO - clique (ENTER = automatica): " id "DET"))
      (if (eq r 'cancel) (setq ok nil) (av:resp-muda "pf" r))))
  (if (and ok (member "pv" ks))
    (progn
      (setq l nil k 0)
      (while (and ok (< k 2))
        (setq r (av:ed-pede (if (= k 0)
                              "\nVertice para a LINHA DE EXTENSAO da faixa (ENTER = cantos do contorno): "
                              "\nVertice para a outra ponta da faixa (ENTER = canto do contorno): ")
                            id "DET"))
        (cond ((eq r 'cancel) (setq ok nil))
              ((null r) (setq k 2))
              (t (setq l (append l (list r)) k (1+ k)))))
      (if ok (av:resp-muda "pv" l))))
  (if (and ok (member "pc" ks))
    (progn
      (setq r (av:ed-pede "\nNovo ponto da LINHA DE CHAMADA (bolinha no ferro) - clique (ENTER = automatico): " id "DET"))
      (if (eq r 'cancel) (setq ok nil) (av:resp-muda "pc" r))))
  (if (and ok (member "t1" ks))
    (progn
      (setq r (av:ed-tabela "\nNovo canto da TABELA DE FERROS VARIAVEIS - clique (ENTER = manter, N = nao gerar): "
                            (av:rp "t1") id "T1"))
      (if (eq r 'cancel) (setq ok nil) (av:resp-muda "t1" (car r)))))
  (if (and ok (member "t2" ks))
    (progn
      (setq r (av:ed-tabela "\nNovo canto do RESUMO DE ACO - clique (ENTER = manter, N = nao gerar): "
                            (av:rp "t2") id "T2"))
      (if (eq r 'cancel) (setq ok nil) (av:resp-muda "t2" (car r)))))
  ok
)

;;; opcoes do menu: (palavra  abre-janela  pontos)
(setq AV:ED-OPCOES
  '(("Parametros" T   nil)
    ("Armadura"   nil ("pk" "pd"))
    ("Faixa"      nil ("pf"))
    ("Extensao"   nil ("pv"))
    ("Indicacao"  nil ("pc"))
    ("Tabelas"    nil ("t1" "t2"))
    ("Desenho"    nil ("pk" "pd" "pf" "pv" "pc"))
    ("Completo"   T   ("pk" "pd" "pf" "pv" "pc" "t1" "t2"))))

(defun av:ed-menu (dflt / r)
  (initget "Parametros Armadura Faixa Extensao Indicacao Tabelas Desenho Completo Sair")
  (setq r (vl-catch-all-apply 'getkword
            (list (strcat "\nEditar [Parametros/Armadura/Faixa/Extensao/Indicacao/Tabelas/Desenho/Completo/Sair] <"
                          dflt ">: "))))
  (cond ((vl-catch-all-error-p r) nil)
        ((null r) dflt)
        (t r))
)

;;; edita o detalhamento id conforme a opcao do menu
(defun av:ed-executa (id op / rec salvo o ok)
  (setq o (assoc op AV:ED-OPCOES))
  (if (null (setq rec (av:reg-le id)))
    (progn (princ "\nDados desse detalhamento nao encontrados.") nil)
    (progn
      (setq salvo (mapcar 'eval AV:PARAMS))
      (av:params-de id rec)
      (setq AV:RESP rec AV:MODO 'replay AV:ED-ID id AV:EDITA T AV:OCUP T)
      (setq ok (if (cadr o) (av:dialog) T))
      (if ok (setq ok (av:ed-pergunta id (caddr o))))
      (if ok
        (progn
          (princ (strcat "\nEditando o detalhamento " id "..."))
          (setq AV:SEMDLG T)
          (av:roda 'c:ARMVAR nil (strcat "editando " id)))
        (princ "\nEdicao cancelada: nada foi alterado."))
      (mapcar 'set AV:PARAMS salvo)
      (setq AV:MODO nil AV:ED-ID nil AV:RESP nil AV:ID nil AV:GRP nil
            AV:SEMDLG nil AV:EDITA nil AV:OCUP nil)
      ok
    )
  )
)

;;; ARMVAREDIT: clique no detalhamento (ferro ou tabelas) e escolha o que
;;; editar: parametros (janela), armadura, faixa, linhas de extensao, linha
;;; de chamada, tabelas, todo o desenho ou tudo.  Repete ate "Sair".
(defun c:ARMVAREDIT ( / sel id op dflt)
  (setq sel (vl-catch-all-apply 'entsel
              (list "\nSelecione o detalhamento ARMVAR: ")))
  (if (and sel (not (vl-catch-all-error-p sel)))
    (setq id (car (av:id-ent (car sel))))
  )
  (cond
    ((or (null id) (av:lista-id-p id))
     (princ "\nEsse objeto nao e um detalhamento ARMVAR (v1.12)."))
    ((null (av:reg-le id))
     (princ "\nDados desse detalhamento nao encontrados."))
    (t
     (setq dflt "Parametros")
     (while (and (setq op (av:ed-menu dflt)) (/= op "Sair"))
       (av:ed-executa id op)
       (setq dflt "Sair")
     )
     (av:reat-liga)
    )
  )
  (princ)
)

;;; ARMVARATU: refaz TODOS os detalhamentos (contornos relidos) e a lista
(defun c:ARMVARATU ( / n)
  (setq n 0 AV:OCUP T)
  (foreach id (av:reg-ids)
    (if (and (not (av:lista-id-p id)) (av:insert-de id "DET"))
      (progn (av:regenera id) (setq n (1+ n))))
  )
  (setq AV:OCUP nil)
  (av:reat-liga)
  (princ (strcat "\n  " (itoa n) " detalhamento(s) atualizado(s)."))
  (princ)
)

;;; ---- reatores: o bloco acompanha o desenho ---------------------------------
;;;  Observa o CONTORNO (handles guardados), o BLOCO e os seus ATRIBUTOS.
;;;  A alteracao so e anotada; o detalhamento e refeito quando o comando
;;;  termina (reator de comando) ou quando a selecao muda depois de editar
;;;  na janela Propriedades (reator de selecao).
(defun av:vla (e / o)
  (if (and e (entget e))
    (progn (setq o (vl-catch-all-apply 'vlax-ename->vla-object (list e)))
           (if (vl-catch-all-error-p o) nil o))
  )
)

(defun av:reat-liga ( / rec objs e o r ins)
  (foreach r AV:REATORES (vl-catch-all-apply 'vlr-remove (list r)))
  (setq AV:REATORES nil AV:CONTORNOS nil)
  (foreach id (av:reg-ids)
    (if (and (not (av:lista-id-p id)) (setq ins (av:insert-de id "DET")) (setq rec (av:reg-le id)))
      (progn
        (setq objs nil)
        ;; contorno
        (foreach hd (cadr (assoc "hnd" rec))
          (if (setq o (av:vla (handent hd)))
            (setq objs (cons o objs) AV:CONTORNOS (cons hd AV:CONTORNOS))))
        ;; bloco e atributos
        (if (setq o (av:vla ins)) (setq objs (cons o objs)))
        (setq e (entnext ins))
        (while (and e (= (cdr (assoc 0 (entget e))) "ATTRIB"))
          (if (setq o (av:vla e)) (setq objs (cons o objs)))
          (setq e (entnext e))
        )
        (setq r (vl-catch-all-apply 'vlr-object-reactor
                  (list objs id '((:vlr-modified . av:cb-mod)))))
        (if (not (vl-catch-all-error-p r)) (setq AV:REATORES (cons r AV:REATORES)))
      )
    )
  )
  (if (null AV:REAT-CMD)
    (progn
      (setq r (vl-catch-all-apply 'vlr-command-reactor
                (list "ARMVAR" '((:vlr-commandEnded . av:cb-cmd)
                                 (:vlr-commandCancelled . av:cb-cmd)
                                 (:vlr-commandFailed . av:cb-cmd)))))
      (if (not (vl-catch-all-error-p r)) (setq AV:REAT-CMD r))
    )
  )
  (if (null AV:REAT-SEL)
    (progn
      (setq r (vl-catch-all-apply 'vlr-miscellaneous-reactor
                (list "ARMVAR" '((:vlr-pickfirstModified . av:cb-sel)))))
      (if (not (vl-catch-all-error-p r)) (setq AV:REAT-SEL r))
    )
  )
  (length AV:REATORES)
)

;;; objeto alterado: so anota (nao pode alterar o desenho aqui)
;;;   AV:PEND = ((id contorno-alterado?) ...)
(defun av:cb-mod (obj rea args / id c)
  (if (and (not AV:OCUP) (not (vlax-erased-p obj)))
    (progn
      (setq id (vlr-data rea)
            c  (member (vla-get-Handle obj) AV:CONTORNOS))
      (if (assoc id AV:PEND)
        (if c (setq AV:PEND (subst (list id T) (assoc id AV:PEND) AV:PEND)))
        (setq AV:PEND (cons (list id (if c T nil)) AV:PEND))
      )
    )
  )
)

;;; processa as alteracoes anotadas
(defun av:processa ( / pend rec n)
  (if (and AV:PEND (not AV:OCUP))
    (progn
      (setq pend AV:PEND AV:PEND nil AV:OCUP T n 0)
      (foreach it pend
        (if (setq rec (av:reg-le (car it)))
          (if (or (cadr it) (av:atrs-mudaram-p (car it) rec))
            (progn
              (princ (strcat "\nARMVAR: atualizando o detalhamento " (car it) "..."))
              (av:roda 'av:regenera (list (car it)) (strcat "atualizando " (car it)))
              (setq n (1+ n))
            )
            ;; nada mudou de fato (ex.: valor invalido): atributos voltam
            ;; aos valores validos guardados
            (av:roda 'av:atrs-restaura (list (car it) rec) "atributos")
          )
        )
      )
      (setq AV:OCUP nil)
      (if (> n 0) (av:reat-liga))
    )
  )
)

;;; fim de comando do usuario (MOVE, STRETCH, EATTEDIT, grips...)
(defun av:cb-cmd (rea args / cmd)
  (setq cmd (strcase (if (car args) (car args) "")))
  (if (wcmatch cmd "U,UNDO,REDO,MREDO")
    (setq AV:PEND nil)
    (av:roda 'av:processa nil "fim de comando")
  )
)

;;; selecao mudou (ex.: ESC depois de editar na janela Propriedades)
(defun av:cb-sel (rea args)
  (if (and AV:PEND (= (getvar "CMDACTIVE") 0))
    (av:roda 'av:processa nil "selecao"))
)

;;; ARMVARLISTA:
;;;   Geral    - lista de TODOS os detalhamentos (se ja existir, e refeita
;;;              no mesmo lugar);
;;;   Selecao  - lista NOVA so dos detalhamentos selecionados (ferros ou
;;;              tabelas); ela nao muda com os outros detalhamentos;
;;;   Atualizar- refaz so a lista clicada.
;;; As listas tambem se refazem sozinhas quando um detalhamento delas muda.
(defun av:lista-sel-ids ( / ss i id r)
  (princ "\nSelecione os detalhamentos (ferros ou tabelas) da lista: ")
  (setq ss (vl-catch-all-apply 'ssget (list (list (list -3 (list AV:APP))))))
  (if (and ss (not (vl-catch-all-error-p ss)))
    (progn
      (setq i 0)
      (while (< i (sslength ss))
        (setq id (car (av:id-ent (ssname ss i))) i (1+ i))
        (if (and id (not (av:lista-id-p id)) (not (member id r)) (av:reg-le id))
          (setq r (cons id r)))
      )
    )
  )
  (vl-sort r '(lambda (a b) (< (atoi (substr a 3)) (atoi (substr b 3)))))
)

(defun c:ARMVARLISTA ( / p h esc uc op d ids lid sel)
  (setq esc (av:num (if AV:P-ESC AV:P-ESC "50"))
        uc  (cond ((or (null AV:P-UNI) (= AV:P-UNI 0)) esc) ((= AV:P-UNI 1) 100.0)
                  ((= AV:P-UNI 2) 1.0) (t 0.1))
        h   (/ (* (/ (av:num (if AV:P-ALT AV:P-ALT "2")) 10.0) esc) uc))
  (initget "Geral Selecao Atualizar")
  (setq op (vl-catch-all-apply 'getkword
             (list "\nLista de ferros [Geral/Selecao/Atualizar] <Geral>: ")))
  (cond ((vl-catch-all-error-p op) (setq op nil))
        ((null op) (setq op "Geral")))
  (setq AV:OCUP T)
  (cond
    ((= op "Geral")
     (if (and (av:insert-de "LISTA" "LST") (setq d (av:reg-le "LISTA")))
       (progn (av:lista-desenha "LISTA" nil (cadr (assoc "p0" d)) h)
              (princ "\n  Lista geral atualizada."))
       (if (setq p (av:pede-canto "\nClique no canto superior esquerdo da LISTA DE FERROS: "))
         (av:lista-desenha "LISTA" nil p h))))
    ((= op "Selecao")
     (if (null (setq ids (av:lista-sel-ids)))
       (princ "\n  Nenhum detalhamento ARMVAR selecionado.")
       (progn
         (princ (strcat "\n  Detalhamentos: " (av:junta-txt ids)))
         (if (setq p (av:pede-canto "\nClique no canto superior esquerdo da LISTA DE FERROS: "))
           (av:lista-desenha (av:lista-novo-id) ids p h)))))
    ((= op "Atualizar")
     (setq sel (vl-catch-all-apply 'entsel (list "\nClique na lista de ferros: ")))
     (if (and sel (not (vl-catch-all-error-p sel))
              (av:lista-id-p (setq lid (car (av:id-ent (car sel)))))
              (setq d (av:reg-le lid)))
       (progn (av:lista-desenha lid (cadr (assoc "ids" d)) (cadr (assoc "p0" d)) h)
              (princ "\n  Lista atualizada."))
       (princ "\n  Isso nao e uma lista de ferros ARMVAR.")))
  )
  (setq AV:OCUP nil)
  (princ)
)

;;; ("AV1" "AV3") -> "AV1, AV3"
(defun av:junta-txt (l / r)
  (setq r "")
  (foreach x l (setq r (if (= r "") x (strcat r ", " x))))
  r
)

;;; ==========================================================================
;;;  13.  ARMVARTESTE: diagnostico do CAD (AutoCAD / ZWCAD)
;;; ==========================================================================
(defun av:teste (nome f / r)
  (setq r (vl-catch-all-apply f nil))
  (princ (strcat "\n  " nome ": "
                 (cond ((vl-catch-all-error-p r) (strcat "FALHOU - " (vl-catch-all-error-message r)))
                       (r "OK")
                       (t "FALHOU"))))
  (if (vl-catch-all-error-p r) nil r)
)

(defun c:ARMVARTESTE ( / ln bl ins dim dados id0 hh)
  (princ (strcat "\n=== ARMVAR v1.12 - diagnostico ===  CAD: "
                 (vl-princ-to-string (getvar "ACADVER"))
                 "  " (vl-princ-to-string (getvar "PRODUCT"))))
  (setq id0 AV:ID hh 0.2)
  (av:prepara)
  (av:teste "1 ActiveX (vlax-get-acad-object)" '(lambda () (vlax-get-acad-object)))
  (setq AV:ID "TESTE" AV:GRP "DET")
  (setq ln (av:teste "2 XDATA (entmake com xdata)"
             '(lambda () (av:mk-line '(0.0 0.0) '(1.0 0.0) "0" nil nil) (entlast))))
  (av:teste "3 XDATA (leitura)" '(lambda () (= (car (av:id-ent ln)) "TESTE")))
  (av:teste "4 ssget X por XDATA" '(lambda () (member ln (av:ents-id "TESTE"))))
  (setq dados (list (list "a" 1) (list "b" 2.5) (list "c" "texto") (list "d" nil)
                    (list "e" (list (list 1.0 2.0) (list 3.5 -4.25)))))
  (av:teste "5 XRECORD (gravar)" '(lambda () (av:reg-grava "TESTE" dados)))
  (av:teste "6 XRECORD (ler igual)" '(lambda () (equal (av:reg-le "TESTE") dados 1e-6)))
  (setq dim (av:teste "7 cota ActiveX (AddDimRotated)"
              '(lambda () (av:mk-dim '(0.0 1.0) '(1.0 1.0) '(0.0 1.5) 0.0 "T" hh 1 T))))
  (setq AV:ID nil AV:GRP nil)
  (av:teste "8 bloco com atributo (entmake BLOCK/ATTDEF/INSERT)"
            '(lambda ( / ok)
               (entmake (av:dxf-bloco "ARMVAR$TESTE" T))
               (entmake (list '(0 . "LINE") '(8 . "0") '(10 0.0 0.0 0.0) '(11 1.0 1.0 0.0)))
               (entmake (av:dxf-attdef "POSICAO" "Posicao" "1" hh))
               (setq ok (entmake '((0 . "ENDBLK"))))
               (if ok (entmake (av:dxf-insert "ARMVAR$TESTE" T (av:xd-lista "TESTE" "" "TST"))))
               (if ok (progn (entmake (av:dxf-attrib "POSICAO" "1" hh)) (entmake '((0 . "SEQEND")))))
               (setq ins (av:insert-de "TESTE" "TST"))
               (and ok ins (equal (av:atr-le ins) '(("POSICAO" "1"))))))
  (av:teste "9 editar atributo (entmod ATTRIB)"
            '(lambda () (av:atr-grava ins '(("POSICAO" "7"))) (equal (av:atr-le ins) '(("POSICAO" "7")))))
  (av:teste "10 REDEFINIR bloco por entmake"
            '(lambda () (and (entmake (av:dxf-bloco "ARMVAR$TESTE" nil))
                             (entmake (list '(0 . "CIRCLE") '(8 . "0") '(10 0.0 0.0 0.0) '(40 . 1.0)))
                             (entmake '((0 . "ENDBLK"))))))
  (if dim
    (av:teste "11 copiar COTA para dentro de bloco"
              '(lambda ( / ed)
                 (setq ed (vl-remove-if '(lambda (g) (member (car g) '(-1 5 67 102 330 360 410)))
                                        (entget (vlax-vla-object->ename dim) (list "*"))))
                 (and (entmake (av:dxf-bloco "ARMVAR$TESTE2" nil)) (entmake ed)
                      (entmake '((0 . "ENDBLK")))))))
  (av:teste "12 reator de objeto (vlr-object-reactor)"
            '(lambda ( / r) (setq r (vlr-object-reactor (list (vlax-ename->vla-object ln)) "T" '((:vlr-modified . av:cb-nada3))))
                            (vlr-remove r) T))
  (av:teste "13 reator de comando (vlr-command-reactor)"
            '(lambda ( / r) (setq r (vlr-command-reactor "T" '((:vlr-commandEnded . av:cb-nada)))) (vlr-remove r) T))
  (av:teste "14 reator de selecao (vlr-miscellaneous-reactor)"
            '(lambda ( / r) (setq r (vlr-miscellaneous-reactor "T" '((:vlr-pickfirstModified . av:cb-nada)))) (vlr-remove r) T))
  (av:teste "15 nth em lista vazia" '(lambda () (nth 0 nil) T))
  (princ (strcat "\n  reatores ligados agora: " (itoa (length AV:REATORES))
                 "   comando: " (if AV:REAT-CMD "sim" "NAO")
                 "   selecao: " (if AV:REAT-SEL "sim" "NAO")))
  (princ (strcat "\n  detalhamentos guardados: " (vl-princ-to-string (av:reg-ids))))
  ;; limpeza
  (foreach e (av:ents-id "TESTE") (entdel e))
  (if (and ins (entget ins)) (entdel ins))
  (av:reg-apaga "TESTE")
  (setq AV:ID id0 AV:GRP nil)
  (princ "\n=== fim do diagnostico: copie estas linhas e envie. ===")
  (princ)
)
(defun av:cb-nada (a b) nil)
(defun av:cb-nada3 (a b c) nil)

(setq AV:OCUP nil AV:PEND nil)
;;; reatores dos detalhamentos que ja existem no desenho aberto
(av:roda 'av:reat-liga nil "ligando reatores")
(cond
  ((null AV:REAT-CMD)
   (princ "\nARMVAR: este CAD nao aceitou o reator de comandos -> use ARMVARATU depois de editar."))
  ((null AV:REAT-SEL)
   (princ "\nARMVAR: sem reator de selecao -> alteracoes feitas na janela Propriedades sao aplicadas no proximo comando (ou use ARMVARATU)."))
)
(princ "\nARMVAR v1.12 carregado.  Comandos: ARMVAR, ARMVAREDIT, ARMVARATU, ARMVARLISTA, ARMVARTESTE.")
(princ "\n  Para editar um detalhamento: selecione-o e altere os ATRIBUTOS na janela Propriedades (ou duplo clique).")
(princ "\n  ARMVARLISTA: Geral (todos), Selecao (so os detalhamentos escolhidos) ou Atualizar (so a lista clicada).")
(princ "\n  ARMVAREDIT: escolha o que editar - Parametros, Armadura, Faixa, Extensao, Indicacao, Tabelas, Desenho ou Completo.")
(princ)
