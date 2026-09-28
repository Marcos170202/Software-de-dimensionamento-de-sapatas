;;; ==========================================================================
;;;  ARMVAR.lsp
;;;  Detalhamento de armadura de COMPRIMENTO VARIAVEL  --  v1.1
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
;;;  Comando:  ARMVAR
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
;;;  7. Clique onde inserir a TABELA DE FERROS VARIAVEIS (N?A, N?B, ...) e
;;;     onde inserir o RESUMO DE ACO.
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
;;;  - Uma barra com C > comercial e dividida no MENOR numero de pedacos
;;;    <= comercial, no padrao do detalhe de parede da prancha modelo
;;;    (PAR101: N.1 C=890 + N.2 C=450, traspasse 48): os pedacos do meio
;;;    tem o comprimento comercial e o restante e repartido 2/3 no 1.o
;;;    pedaco e 1/3 no ultimo.  Cada emenda acrescenta L ao consumo.
;;;  - ALTERNANCIA (opcao "Alternar barras vizinhas"): a barra vizinha usa
;;;    os MESMOS pedacos em ordem inversa.  No desenho, a barra simetrica
;;;    (tracejada) ja aparece com os pedacos invertidos; sem simetria, e
;;;    desenhada ao lado a barra "ALTER.".  Assim as
;;;    emendas de barras vizinhas nao ficam na mesma secao e a tabela tem
;;;    poucos comprimentos.  As zonas de traspasse de barras vizinhas ficam
;;;    afastadas de pelo menos o "afastamento entre emendas" (padrao 20 cm);
;;;    se nao ficarem, o 1.o pedaco e aumentado ou e usado um pedaco a mais.
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
;;;                           "(1300)" e cota do traspasse.  Se o CAD nao
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

;;; lt/lts: tipo de linha e escala da entidade (nil = PorLayer)
(defun av:mk-line (p1 p2 lay lt lts)
  (entmake (append
             (list '(0 . "LINE") '(100 . "AcDbEntity") (cons 8 lay))
             (if (and lt (tblsearch "LTYPE" lt)) (list (cons 6 lt) (cons 48 lts)))
             (list '(100 . "AcDbLine")
                   (cons 10 (list (car p1) (cadr p1) 0.0))
                   (cons 11 (list (car p2) (cadr p2) 0.0)))))
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
             (mapcar '(lambda (p) (cons 10 (list (car p) (cadr p)))) pts)))
)

(defun av:mk-pline (pts lay closed) (av:mk-pl pts lay closed nil nil nil))

(defun av:mk-circ (c r lay)
  (entmake (list '(0 . "CIRCLE") (cons 8 lay)
                 (cons 10 (list (car c) (cadr c) 0.0)) (cons 40 r)))
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
             )))
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

;;; divide uma barra de comprimento total "tot" (cm, inteiro) em pedacos de
;;; no maximo "lcom", com traspasse "lap" entre pedacos consecutivos, no
;;; padrao do detalhe de parede da prancha modelo (N.1 C=890 + N.2 C=450):
;;;   - n = menor numero de pedacos;  pedacos do meio = lcom;
;;;   - o que sobra (r) e repartido 2/3 no 1.o pedaco (arredondado a 10 cm,
;;;     max. lcom) e 1/3 no ultimo;
;;;   - a barra vizinha usa os MESMOS pedacos em ordem inversa (ALTER.),
;;;     entao as emendas de barras vizinhas ficam desencontradas; se ficarem
;;;     a menos de (lap + def) uma da outra, aumenta o 1.o pedaco ou usa
;;;     um pedaco a mais.
;;;   ini / fim = ganchos (perna + ponta) no inicio / no fim
;;; devolve a lista dos pedacos (inteiros) na ordem da barra;
;;; soma dos pedacos = tot + (n - 1) x lap
(defun av:divide (tot ini fim lcom lap def / n n0 s r p1 pn pcs ok)
  (if (<= tot lcom)
    (list tot)
    (progn
      (setq n 2)
      (while (> (+ tot (* (1- n) lap)) (* n lcom)) (setq n (1+ n)))
      (setq n0 n ok nil)
      (while (and (not ok) (<= n (+ n0 2)))
        (setq s  (+ tot (* (1- n) lap))
              r  (- s (* (- n 2) lcom))
              p1 (min lcom (* 10 (fix (/ (* 2.0 r) 30.0))))
              pn (- r p1))
        (if (and (> pn 0) (<= pn lcom))
          (progn
            ;; se as emendas espelhadas coincidirem, desloca 10 cm por vez
            (setq pcs (av:monta p1 pn n lcom))
            (while (and (not (av:alterna-ok pcs tot lap def))
                        (<= (+ p1 10) lcom) (> (- pn 10) (+ fim lap)))
              (setq p1 (+ p1 10) pn (- pn 10)
                    pcs (av:monta p1 pn n lcom))
            )
            (if (and (av:alterna-ok pcs tot lap def)
                     (>= p1 (+ ini lap)) (>= pn (+ fim lap)))
              (setq ok pcs))
          )
        )
        (setq n (1+ n))
      )
      ;; sem solucao espelhada boa: fica com a divisao minima
      (if ok ok
        (progn
          (setq s  (+ tot (* (1- n0) lap))
                r  (- s (* (- n0 2) lcom))
                p1 (min lcom (* 10 (fix (/ (* 2.0 r) 30.0)))))
          (av:monta p1 (- r p1) n0 lcom)
        )
      )
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

;;; ferro:        (2X) N.1 87 %%c 8 C/15 C=VAR
(defun av:txt-ferro (rep pos n bit esp ctxt)
  (strcat (av:rep-txt rep) "N." (itoa pos) " " (itoa n)
          " %%c " bit " C/" (av:fmt esp) " C=" ctxt)
)

;;; distribuicao: 87 (2X) N.1 %%c 8 C/15
(defun av:txt-faixa (rep pos n bit esp)
  (strcat (itoa n) " " (av:rep-txt rep) "N." (itoa pos)
          " %%c " bit " C/" (av:fmt esp))
)

;;; titulo da tabela: (2X) N.1 87 %%c 8 C/15   (sem o "C=")
(defun av:titulo-barra (rep pos n bit esp)
  (strcat (av:rep-txt rep) "N." (itoa pos) " " (itoa n)
          " %%c " bit " C/" (av:fmt esp))
)

;;; tabela de ferros variaveis
;;;   p0 = canto superior esquerdo da moldura;  nota = texto abaixo (ou nil)
(defun av:tab-ferros (p0 h pos pref rep bit esp grupos nbar nota
                      / n x0 y0 wd ht y i yh xg)
  (setq n (length grupos)
        x0 (car p0) y0 (cadr p0)
        wd (* 22.0 h)
        ht (+ (* 1.5 h) (* 1.5 h n) (* 1.0 h))
        yh (- y0 (* 1.5 h)))
  ;; titulo acima da moldura
  (av:mk-text (av:titulo-barra rep pos nbar bit esp)
              (list (+ x0 (* 1.0 h)) (+ y0 (* 0.5 h))) h 0.0 AV:LAY-TXT nil)
  (av:mk-pline (list (list x0 y0) (list (+ x0 wd) y0)
                     (list (+ x0 wd) (- y0 ht)) (list x0 (- y0 ht)))
               AV:LAY-TAB T)
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
    (av:mk-text (strcat pref (av:letra i))
                (list (+ x0 (* 1.0 h)) y) h 0.0 AV:LAY-TXT nil)
    (av:mk-text (itoa (cdr g))
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

;;; resumo de aco: uma barra
(defun av:tab-aco (p0 h pref bit aco qtd ctot kgm / x0 y0 wd ht peso m)
  (setq x0 (car p0) y0 (cadr p0)
        wd (* 47.0 h) ht (* 6.5 h)
        m (/ ctot 100.0)          ; comprimento total em metros
        peso (* m kgm))
  (av:mk-text (strcat "RESUMO DE A" (chr 199) "O  -  " aco)
              (list (+ x0 (* 1.0 h)) (+ y0 (* 0.5 h))) h 0.0 AV:LAY-TXT nil)
  (av:mk-pline (list (list x0 y0) (list (+ x0 wd) y0)
                     (list (+ x0 wd) (- y0 ht)) (list x0 (- y0 ht)))
               AV:LAY-TAB T)
  ;; cabecalho
  (foreach c (list (list 1.0 "POS.") (list 8.0 "%%c (mm)") (list 16.0 "QTD.")
                   (list 22.0 "C.TOTAL (m)") (list 36.0 "PESO (kg)"))
    (av:mk-text (cadr c) (list (+ x0 (* (car c) h)) (- y0 (* 1.2 h))) h 0.0
                AV:LAY-TXT nil)
  )
  (av:mk-line (list x0 (- y0 (* 1.5 h))) (list (+ x0 wd) (- y0 (* 1.5 h)))
              AV:LAY-TAB nil nil)
  ;; linha da barra
  (foreach c (list (list 1.0 pref) (list 8.0 bit) (list 16.0 (itoa qtd))
                   (list 22.0 (rtos m 2 2)) (list 36.0 (rtos peso 2 1)))
    (av:mk-text (cadr c) (list (+ x0 (* (car c) h)) (- y0 (* 3.0 h))) h 0.0
                AV:LAY-TXT nil)
  )
  ;; total
  (av:mk-line (list x0 (- y0 (* 3.5 h))) (list (+ x0 wd) (- y0 (* 3.5 h)))
              AV:LAY-TAB nil nil)
  (foreach c (list (list 1.0 "TOTAL") (list 22.0 (rtos m 2 2))
                   (list 36.0 (rtos peso 2 1)))
    (av:mk-text (cadr c) (list (+ x0 (* (car c) h)) (- y0 (* 5.0 h))) h 0.0
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
(defun av:ferro (th u qa qb hooks sg uc pcs lap sh off lay lt lts
                 / l1 t1 l2 t2 ini n k a b ka kb uu ul pts p)
  (setq l1 (nth 0 hooks) t1 (nth 1 hooks) l2 (nth 2 hooks) t2 (nth 3 hooks)
        ini (+ l1 t1) n (length pcs) k 0 a 0.0)
  (foreach p pcs
    (setq b  (+ a p)
          ka (if (= k 0) qa (+ qa (/ (- a ini) uc)))
          kb (if (= k (1- n)) qb (+ qa (/ (- b ini) uc)))
          uu (if (= (rem k 2) 1) (+ u off) u)
          pts (list (list (+ ka sh) uu) (list (+ kb sh) uu)))
    ;; gancho inicial (so no 1.o pedaco)
    (if (and (= k 0) (> l1 0.0))
      (progn
        (setq ul  (+ uu (* sg (/ l1 uc)))
              pts (cons (list (+ ka sh) ul) pts))
        (if (> t1 0.0)
          (setq pts (cons (list (+ ka sh (/ t1 uc)) ul) pts)))
      )
    )
    ;; gancho final (so no ultimo pedaco)
    (if (and (= k (1- n)) (> l2 0.0))
      (progn
        (setq ul  (+ uu (* sg (/ l2 uc)))
              pts (append pts (list (list (+ kb sh) ul))))
        (if (> t2 0.0)
          (setq pts (append pts (list (list (- (+ kb sh) (/ t2 uc)) ul)))))
      )
    )
    (av:mk-pl (mapcar '(lambda (q) (av:tu th (car q) (cadr q))) pts)
              lay nil lt lts nil)
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
)

;;; cota linear REAL (entidade DIMENSION, rotacionada), layer EST_Cota,
;;; com tiques (arch tick) e o texto "txt" no lugar do valor medido.
;;;   p1,p2 = pontos de definicao;  ploc = ponto da linha de cota
;;;   ang   = angulo da linha de cota;  vpos = 1 texto acima / 2 do lado de
;;;           fora (longe dos pontos);  sup = T suprime as linhas de chamada
;;;   Na string "txt", "\X" separa o texto de cima e o de baixo da linha.
;;; devolve o objeto, ou nil se o CAD nao aceitar (usa-se o desenho manual)
(defun av:mk-dim (p1 p2 ploc ang txt h vpos sup / spc d)
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
                        (list 'vla-put-TextColor 256)
                        (list 'vla-put-ExtLine1Suppress (if sup :vlax-true :vlax-false))
                        (list 'vla-put-ExtLine2Suppress (if sup :vlax-true :vlax-false))
                        (list 'vla-put-TextOverride txt))
        (vl-catch-all-apply (car pr) (list d (cadr pr)))
      )
      d
    )
  )
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
(defun av:desenha (th ud ta tb lo hi tdim hooks lado h uc espec faixa wtxt
                   mtxt pcs neg lap pcsa atxt
                   / sg l1 t1 l2 t2 ini fim emd tc d nrm hk dneg p0 leg1 tip1
                     p1 leg2 tip2 uvar ues ualt rot up mid lts)
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
        lts (av:ltscale))

  ;; --- ferro positivo (continuo) ----------------------------------------
  (av:ferro th ud ta tb hooks sg uc pcs lap 0.0 (* -0.3 h sg)
            AV:LAY-BAR nil nil)

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
  (if (> l1 0.0)
    (progn
      (setq leg1 (av:tu th ta (+ ud (* sg (/ l1 uc)))))
      (if (> t1 0.0)
        (setq tip1 (av:tu th (+ ta (/ t1 uc)) (+ ud (* sg (/ l1 uc))))))
    )
  )
  (if (> l2 0.0)
    (progn
      (setq leg2 (av:tu th tb (+ ud (* sg (/ l2 uc)))))
      (if (> t2 0.0)
        (setq tip2 (av:tu th (- tb (/ t2 uc)) (+ ud (* sg (/ l2 uc))))))
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
      (av:rotulo (av:fmt l1) (list (/ (+ (car p0) (car leg1)) 2.0)
                                   (/ (+ (cadr p0) (cadr leg1)) 2.0))
                 (angle '(0.0 0.0) hk) (list (- (car d)) (- (cadr d))) h AV:LAY-TXT)
      (if tip1
        (av:rotulo (av:fmt t1) (list (/ (+ (car leg1) (car tip1)) 2.0)
                                     (/ (+ (cadr leg1) (cadr tip1)) 2.0))
                   th hk h AV:LAY-TXT)
      )
    )
  )
  (if leg2
    (progn
      (av:rotulo (av:fmt l2) (list (/ (+ (car p1) (car leg2)) 2.0)
                                   (/ (+ (cadr p1) (cadr leg2)) 2.0))
                 (angle '(0.0 0.0) hk) d h AV:LAY-TXT)
      (if tip2
        (av:rotulo (av:fmt t2) (list (/ (+ (car leg2) (car tip2)) 2.0)
                                     (/ (+ (cadr leg2) (cadr tip2)) 2.0))
                   th hk h AV:LAY-TXT)
      )
    )
  )

  ;; --- texto do ferro: centrado, do lado oposto aos ganchos --------------
  (setq ues (- ud (* sg (if emd (* 0.3 h) 0.0))))
  (av:rotulo espec (av:tu th tc ues) th (list (- (car hk)) (- (cadr hk)))
             h AV:LAY-ESPEC)

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
  ;;     "87 (2X) N.1 %%c 8 C/15" acima  e  "(1300)" abaixo da linha
  (if (not (av:mk-dim (av:tu th tdim lo) (av:tu th tdim hi) (av:tu th tdim lo)
                      (+ th (/ pi 2.0)) (strcat faixa "\\X" wtxt) h 1 T))
    (progn
      (av:mk-line (av:tu th tdim (- lo (* 0.75 h))) (av:tu th tdim (+ hi (* 0.75 h)))
                  AV:LAY-COTA nil nil)
      (av:tique (av:tu th tdim lo) nrm h AV:LAY-COTA)
      (av:tique (av:tu th tdim hi) nrm h AV:LAY-COTA)
      (setq rot (av:leitura (+ th (/ pi 2.0)))
            up  (list (- (sin rot)) (cos rot))
            mid (av:tu th tdim (/ (+ lo hi) 2.0)))
      (av:mk-text faixa (av:mad mid up (* 0.7 h)) (* 0.9 h) rot AV:LAY-COTA T)
      (av:mk-text wtxt  (av:mad mid up (* -1.6 h)) (* 0.9 h) rot AV:LAY-COTA T)
    )
  )

  ;; --- indicacao: circulos no ferro e chamada tracejada ate a faixa -------
  (if (and (>= tdim (- ta 1e-9)) (<= tdim (+ tb 1e-9)))
    (progn
      (av:mk-circ (av:tu th tdim ud) (* 0.225 h) AV:LAY-IND)
      (av:mk-circ (av:tu th tdim ud) (* 0.375 h) AV:LAY-IND)
      (cond
        ((< ud (- lo 1e-9))
         (av:mk-line (av:tu th tdim lo) (av:tu th tdim (+ ud (* 0.375 h)))
                     AV:LAY-IND AV:LT-NOME (/ h lts)))
        ((> ud (+ hi 1e-9))
         (av:mk-line (av:tu th tdim hi) (av:tu th tdim (- ud (* 0.375 h)))
                     AV:LAY-IND AV:LT-NOME (/ h lts)))
      )
    )
  )
  T
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
       (setq aneis (av:aneis-da-selecao ss))
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

;;; ponto dentro do contorno -> (u tA tB sA sB) da corda que o contem, ou nil
(defun av:pede-ponto (edges th cov / pt tt uu c r)
  (setq r nil)
  (while (not r)
    (setq pt (vl-catch-all-apply
               'getpoint
               (list "\nClique num ponto DENTRO do contorno para desenhar o ferro: ")))
    (cond
      ((vl-catch-all-error-p pt) (setq r 'cancel))
      ((null pt) (setq r 'cancel))
      (t
       (setq pt (trans pt 1 0)
             tt (+ (* (car pt) (cos th)) (* (cadr pt) (sin th)))
             uu (+ (* (- (car pt)) (sin th)) (* (cadr pt) (cos th))))
       (foreach c (av:cortes edges uu cov)
         (if (and (>= tt (car c)) (<= tt (cadr c)))
           (setq r (list uu (car c) (cadr c) (caddr c) (cadddr c)))
         )
       )
       (cond
         ((null r) (princ "\n  Ponto fora do contorno (ou dentro de um furo). Tente de novo."))
         ((<= (- (- (nth 2 r) (nth 4 r)) (+ (nth 1 r) (nth 3 r))) 1e-9)
          (princ "\n  Ponto muito proximo da borda: nao cabe ferro com esse cobrimento.")
          (setq r nil))
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
)

(defun av:write-dcl ( / f nome)
  (setq nome (strcat (getvar "TEMPPREFIX") "AV_ARMVAR.dcl")
        f    (open nome "w"))
  (foreach ln
   (list
"av_armvar : dialog {"
"  label = \"ARMADURA DE COMPRIMENTO VARIAVEL      v1.1      Baluarte\";"
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
"      }"
"      : column {"
"        : image { key = \"prev\"; width = 40; height = 7; color = -15; }"
"        : edit_box { key = \"pm\"; label = \"Principal (so previa) :\"; edit_width = 7; }"
"      }"
"      : boxed_column {"
"        label = \"Extremidade FINAL\";"
"        : edit_box { key = \"pl2\"; label = \"Perna (perp.) :\"; edit_width = 7; }"
"        : edit_box { key = \"pt2\"; label = \"Ponta (paral.) :\";  edit_width = 7; }"
"      }"
"    }"
"    : text { label = \"Principal = VAR (vem do contorno); o valor acima so ajusta a previa.\"; }"
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
"      : edit_box   { key = \"rep\"; label = \"Repeticoes (2 = simetria) :\"; edit_width = 5; }"
"      : toggle     { key = \"sim\"; label = \"Desenhar a barra simetrica invertida\"; }"
"      : text       { label = \"   (negativa, tracejada - se repeticoes >= 2)\"; }"
"    }"
"    : boxed_column {"
"      label = \"Emendas por traspasse\";"
"      : toggle   { key = \"emd\"; label = \"Emendar barras maiores que o comercial\"; }"
"      : edit_box { key = \"lcm\"; label = \"Comprimento comercial (cm) :\"; edit_width = 7; }"
"      : edit_box { key = \"tra\"; label = \"Traspasse  L  (cm) :\";         edit_width = 7; }"
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

(defun av:preview ( / w h m x1 x2 pm sc l1 t1 l2 t2 lado y0 dy p1 p2 tt)
  (setq w (dimx_tile "prev") h (dimy_tile "prev")
        m 14 x1 m x2 (- w m)
        pm (av:tile-num "pm")
        l1 (av:tile-num "pl1") t1 (av:tile-num "pt1")
        l2 (av:tile-num "pl2") t2 (av:tile-num "pt2")
        lado (atoi (get_tile "lado")))
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
  ;; extremidade inicial
  (if (> l1 0.0)
    (progn
      (av:linha-g x1 y0 x1 (+ y0 (* dy p1)) 1)
      (if (> t1 0.0)
        (progn
          (setq tt (max 4 (fix (* t1 sc))))
          (av:linha-g x1 (+ y0 (* dy p1)) (+ x1 tt) (+ y0 (* dy p1)) 5)))
    )
  )
  ;; extremidade final
  (if (> l2 0.0)
    (progn
      (av:linha-g x2 y0 x2 (+ y0 (* dy p2)) 1)
      (if (> t2 0.0)
        (progn
          (setq tt (max 4 (fix (* t2 sc))))
          (av:linha-g x2 (+ y0 (* dy p2)) (- x2 tt) (+ y0 (* dy p2)) 5)))
    )
  )
  (end_image)
  ;; ponta so faz sentido com perna
  (mode_tile "pt1" (if (> l1 0.0) 0 1))
  (mode_tile "pt2" (if (> l2 0.0) 0 1))
)

;;; habilita / desabilita os campos de emenda
(defun av:modo-emd ( / m)
  (setq m (if (= (get_tile "emd") "1") 0 1))
  (foreach k '("lcm" "tra" "dfs") (mode_tile k m))
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
            AV:P-DFS (get_tile "dfs") AV:P-AFS (get_tile "afs"))
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
        (vl-catch-all-apply 'av:logo-desenha nil)
        (vl-catch-all-apply 'av:preview nil)
        (vl-catch-all-apply 'av:modo-emd nil)
        (foreach k '("pl1" "pt1" "pl2" "pt2" "pm" "lado")
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

;;; (890 450) -> "890+450"
(defun av:junta (l / r)
  (setq r (itoa (car l)))
  (foreach v (cdr l) (setq r (strcat r "+" (itoa v))))
  r
)

(defun c:ARMVAR ( / *error* doc th aneis edges ex uc esc h cov esp espcm bit kgm
                    hooks lado pos pref rep bars u c total-cm b hsum grupos
                    tot nbar ctot pk lo hi umin umax pt1 pt2 marcou g posu
                    iu ini fim emd lcom lap afs dfs neg pcs npcs nemd tots
                    ctxt mtxt ta tb ud tdim tc tr pcsr pcsa r ok nota)
  (defun *error* (msg)
    (if (and msg (not (wcmatch (strcase msg) "*CANCEL*,*QUIT*,*EXIT*")))
      (princ (strcat "\n*** Erro: " msg)))
    (if marcou (vl-catch-all-apply 'vla-EndUndoMark (list doc)))
    (vl-catch-all-apply 'redraw nil)
    (princ)
  )
  (setq doc (vla-get-ActiveDocument (vlax-get-acad-object)) marcou nil)

  (if (not (av:dialog))
    (progn (princ "\nCancelado.") (princ))
    (progn
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
                        (av:num AV:P-PL2) (av:num AV:P-PT2))
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
            afs  (av:int (av:num AV:P-AFS)))
      ;; ponta sem perna nao existe
      (if (<= (nth 0 hooks) 0.0) (setq hooks (av:setnth hooks 1 0.0)))
      (if (<= (nth 2 hooks) 0.0) (setq hooks (av:setnth hooks 3 0.0)))
      (setq ini  (+ (nth 0 hooks) (nth 1 hooks))
            fim  (+ (nth 2 hooks) (nth 3 hooks))
            hsum (+ ini fim))

      ;; ---- 1) direcao --------------------------------------------------
      (setq th (av:pede-direcao))
      (if (null th)
        (princ "\nCancelado.")
        (progn
          ;; ---- 2) contorno --------------------------------------------
          (setq aneis (av:pede-contorno uc))
          (if (null aneis)
            (princ "\nCancelado.")
            (progn
              (setq edges (av:arestas aneis th)
                    ex    (av:extensao edges)
                    umin  (nth 0 ex) umax (nth 1 ex)
                    lo    umin hi umax)
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
                    (setq pcs (if emd (av:divide tot ini fim lcom lap afs) (list tot)))
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
                    (setq ctxt (av:junta (if emd (av:divide (car tots) ini fim lcom lap afs)
                                                 (list (car tots))))
                          mtxt (av:fmt (- (car tots) hsum)))
                    (setq ctxt "VAR" mtxt "VAR")
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
                  ;; ---- 4) ponto do ferro --------------------------------
                  (setq pk (av:pede-ponto edges th cov))
                  (if (null pk)
                    (princ "\nCancelado.")
                    (progn
                      (setq ud (nth 0 pk)
                            ta (+ (nth 1 pk) (nth 3 pk))
                            tb (- (nth 2 pk) (nth 4 pk))
                            tc (/ (+ ta tb) 2.0)
                            ok T)
                      ;; ---- 5) onde desenhar o ferro ---------------------
                      (setq r (av:pede-opc "\nPosicao do DESENHO do ferro - clique (ENTER = no ponto escolhido): "))
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
                          (setq r (av:pede-opc "\nPosicao da LINHA DE DISTRIBUICAO - clique (ENTER = automatica): "))
                          (cond ((eq r 'cancel) (setq ok nil))
                                (r (setq tdim (car (av:xy-tu r th)))))
                        )
                      )
                      (if (not ok)
                        (princ "\nCancelado.")
                        (progn
                          ;; pedacos da barra representada e da vizinha (ALTER.)
                          (setq tr   (av:int (+ (* (- tb ta) uc) hsum))
                                pcsr (if emd (av:divide tr ini fim lcom lap afs) (list tr))
                                pcsa (if (and dfs (cdr pcsr)) (av:inverte pcsr ini fim)))
                          ;; ---- 7) desenha o ferro e a faixa --------------
                          (vla-StartUndoMark doc) (setq marcou T)
                          (av:prepara)
                          (av:desenha th ud ta tb lo hi tdim hooks lado h uc
                                      (av:txt-ferro rep pos nbar bit espcm ctxt)
                                      (av:txt-faixa rep pos nbar bit espcm)
                                      (strcat "(" (rtos (* (- hi lo) uc) 2 0) ")")
                                      mtxt pcsr neg lap pcsa
                                      (strcat (av:rep-txt rep) "N." (itoa pos) " %%c " bit
                                              " C/" (av:fmt espcm) " ALTER."))
                          ;; ---- 8) tabelas --------------------------------
                          (setq nota (if (> nemd 0)
                                       (strcat "EMENDAS POR TRASPASSE: L = " (itoa lap)
                                               " cm  (BARRAS > " (itoa lcom) " cm)"
                                               (if dfs " - BARRAS ALTERNADAS" ""))))
                          (setq pt1 (av:pede-canto "\nClique no canto superior esquerdo da TABELA DE FERROS VARIAVEIS (ENTER = nao gerar): "))
                          (if pt1
                            (av:tab-ferros pt1 h pos pref rep bit espcm grupos nbar nota)
                          )
                          (setq pt2 (av:pede-canto "\nClique no canto superior esquerdo do RESUMO DE ACO (ENTER = nao gerar): "))
                          (if pt2
                            (av:tab-aco pt2 h pref bit (nth AV:P-ACO AV:ACOS)
                                        (* npcs rep) ctot kgm)
                          )
                          (vla-EndUndoMark doc) (setq marcou nil)
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

(princ "\nARMVAR v1.1 carregado.  Digite ARMVAR para iniciar.")
(princ)
