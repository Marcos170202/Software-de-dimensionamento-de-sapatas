;;; ==========================================================================
;;; ESTRIBO.LSP - Detalhamento automatico de estribos (AutoCAD / AutoLISP)
;;; --------------------------------------------------------------------------
;;; Comandos:
;;;   ESTRIBO  (ou EST)  -> abre a janela de detalhamento de estribos
;;;   ENCONTRO           -> armadura de encontro de paredes (L cruzados)
;;;
;;; Origem da geometria:
;;;   - Generico ........ digita B x H (medidas externas do estribo, em cm)
;;;   - Selecionar secao  seleciona uma polilinha fechada (retangular ou
;;;                       poligonal, inclusive dentro de bloco); o estribo e
;;;                       gerado descontando o cobrimento
;;;   - Desenhar estribo  clica dois cantos (ou os vertices de um poligono);
;;;                       o que foi desenhado e o proprio estribo
;;;
;;; Tipos:
;;;   - Padrao  : fechado, pernas a 45 graus (gancho de 135 graus)
;;;   - Fechado : fechado, pernas a 90 graus
;;;   - Aberto  : em "U", pernas a 90 graus para dentro
;;;
;;; Layers (padrao das pranchas):
;;;   EST_ArmPos   -> desenho do estribo (secao e detalhe)
;;;   EST_Cota     -> cotas do detalhe e distribuicao (cota real, estilo EST_Cota)
;;;   EST_ArmTexto -> identificacao (N.16 6 %%c 5.0 c/17 C=125)
;;;   Todos os textos em Arial (estilo "Arial", criado se nao existir)
;;;
;;; Comprimento:
;;;   Fechado : C = perimetro externo + 2 x (perna + acrescimo de dobra)
;;;   Aberto  : C = perimetro sem o lado aberto + 2 x (perna + acrescimo)
;;;   Arredondado para cima (cm inteiro).
;;;   Acrescimo automatico: 5 fi (pernas a 45) ou 1 fi (pernas a 90).
;;;   Perna automatica (NBR 6118 9.4.6.1): 45 -> max(5 cm, 5 fi);
;;;   90 -> max(7 cm, 10 fi). Perna minima aceita: 5 cm.
;;; ==========================================================================

(vl-load-com)

(setq *est:bitolas* '("4.2" "5.0" "6.3" "8.0" "10.0" "12.5" "16.0"))
(setq *est:unids*   '("cm" "m" "mm"))
(setq *est:layers*  '(("EST_ArmPos" 1) ("EST_Cota" 8) ("EST_ArmTexto" 7)))
(setq *est:keys*
  '("prefixo" "pos" "bit" "esp" "qtd" "trecho" "mais1" "incc" "tipo"
    "b" "h" "perna" "acr" "auto" "cob" "unid" "escala" "txt"
    "dsec" "ddet" "ddist" "cotadim"))

;;; --------------------------------------------------------------------------
;;; Estado (valores dos campos, sempre como string)
;;; --------------------------------------------------------------------------

(defun est:defaults ()
  (list '("prefixo" . "N.") '("pos" . "1") '("bit" . "1") '("esp" . "20")
        '("qtd" . "1") '("trecho" . "0") '("mais1" . "0") '("incc" . "1")
        '("tipo" . "t0") '("b" . "14") '("h" . "35") '("perna" . "5")
        '("acr" . "2,5") '("auto" . "1") '("cob" . "2,5") '("unid" . "0")
        '("escala" . "25") '("txt" . "2,5") '("dsec" . "1") '("ddet" . "1")
        '("ddist" . "0") '("cotadim" . "0")
        ;; ENCONTRO
        '("e_pos1" . "1") '("e_pos2" . "2") '("e_bit" . "3") '("e_esp" . "15")
        '("e_qtd" . "1") '("e_trecho" . "0") '("e_mais1" . "0") '("e_t1" . "14")
        '("e_t2" . "14") '("e_ang" . "90") '("e_cob" . "2,5") '("e_la1" . "60")
        '("e_lb1" . "50") '("e_la2" . "60") '("e_lb2" . "50") '("e_g" . "8")
        '("e_gauto" . "1") '("e_dpl" . "1") '("e_ddet" . "1") '("e_ddist" . "1")))

(defun est:g (k) (cdr (assoc k *est:st*)))

(defun est:s (k v)
  (if (assoc k *est:st*)
    (setq *est:st* (subst (cons k v) (assoc k *est:st*) *est:st*))
    (setq *est:st* (cons (cons k v) *est:st*))))

(defun est:n (k / v)
  (setq v (est:g k))
  (if v (atof (vl-string-translate "," "." v)) 0.0))

(defun est:load-cfg ( / s l)
  (if (not *est:st*)
    (progn
      (setq s (getenv "ESTRIBO_CFG"))
      (if s (setq l (vl-catch-all-apply 'read (list s))))
      (if (and l (not (vl-catch-all-error-p l)) (listp l))
        (setq *est:st* l))))
  ;; garante todas as chaves
  (foreach d (est:defaults)
    (if (not (est:g (car d))) (est:s (car d) (cdr d)))))

(defun est:save-cfg ()
  (vl-catch-all-apply 'setenv (list "ESTRIBO_CFG" (vl-prin1-to-string *est:st*))))

;;; Fator: unidades de desenho por cm
(defun est:uf () (nth (atoi (est:g "unid")) '(1.0 0.01 10.0)))

;;; Bitola em texto e em cm
(defun est:bit ()  (nth (atoi (est:g "bit")) *est:bitolas*))
(defun est:fi ()   (/ (atof (est:bit)) 10.0))

;;; Altura do texto em unidades de desenho
(defun est:th () (* (est:n "txt") (est:n "escala") 0.1 (est:uf)))

;;; Formata numero: inteiro se possivel, senao 1 casa com virgula
(defun est:fmt (v / r)
  (setq r (fix (+ v 0.5)))
  (if (< (abs (- v r)) 0.05)
    (itoa r)
    (vl-string-translate "." "," (rtos v 2 1))))

(defun est:ceil (x / r)
  (setq r (fix x))
  (if (> (- x r) 1e-4) (1+ r) r))

;;; --------------------------------------------------------------------------
;;; Vetores 2D
;;; --------------------------------------------------------------------------

(defun est:2d  (p) (list (float (car p)) (float (cadr p))))
(defun est:3d  (p) (list (car p) (cadr p) 0.0))
(defun est:add (a b) (list (+ (car a) (car b)) (+ (cadr a) (cadr b))))
(defun est:sub (a b) (list (- (car a) (car b)) (- (cadr a) (cadr b))))
(defun est:mul (a k) (list (* (car a) k) (* (cadr a) k)))
(defun est:mid (a b) (est:mul (est:add a b) 0.5))
(defun est:cross (a b) (- (* (car a) (cadr b)) (* (cadr a) (car b))))
(defun est:dot (a b) (+ (* (car a) (car b)) (* (cadr a) (cadr b))))
(defun est:len (a) (sqrt (est:dot a a)))
(defun est:unit (a / l)
  (setq l (est:len a))
  (if (> l 1e-12) (est:mul a (/ 1.0 l)) '(0.0 0.0)))
;;; normal a esquerda (interior de poligono anti-horario) e a direita (exterior)
(defun est:lnorm (a b / d) (setq d (est:unit (est:sub b a))) (list (- (cadr d)) (car d)))
(defun est:rnorm (a b / d) (setq d (est:unit (est:sub b a))) (list (cadr d) (- (car d))))

(defun est:take (l k / r) (repeat k (setq r (cons (car l) r) l (cdr l))) (reverse r))
(defun est:drop (l k) (repeat k (setq l (cdr l))) l)
(defun est:rotate (l k) (append (est:drop l k) (est:take l k)))

;;; --------------------------------------------------------------------------
;;; Poligonos (lista de pontos 2D, anti-horario, sem repetir o 1o ponto)
;;; --------------------------------------------------------------------------

(defun est:area (P / s a b)
  (setq s 0.0 a (last P))
  (foreach b P (setq s (+ s (est:cross a b)) a b))
  (/ s 2.0))

(defun est:perim (P / s a b)
  (setq s 0.0 a (last P))
  (foreach b P (setq s (+ s (distance a b)) a b))
  s)

(defun est:bbox (P)
  (list (list (apply 'min (mapcar 'car P)) (apply 'min (mapcar 'cadr P)))
        (list (apply 'max (mapcar 'car P)) (apply 'max (mapcar 'cadr P)))))

(defun est:clean (P / r n i a b c u v keep)
  (setq r nil)
  (foreach pt (mapcar 'est:2d P)
    (if (not (and r (equal pt (car r) 1e-8))) (setq r (cons pt r))))
  (setq r (reverse r))
  (if (and (> (length r) 1) (equal (car r) (last r) 1e-8))
    (setq r (reverse (cdr (reverse r)))))
  (setq n (length r) i 0 keep nil)
  (repeat n
    (setq a (nth (rem (+ i n -1) n) r) b (nth i r) c (nth (rem (1+ i) n) r)
          u (est:sub b a) v (est:sub c b))
    (if (> (abs (est:cross u v)) (* 1e-6 (est:len u) (est:len v)))
      (setq keep (cons b keep)))
    (setq i (1+ i)))
  (setq keep (reverse keep))
  (if (and (> (length keep) 2) (< (est:area keep) 0.0)) (setq keep (reverse keep)))
  (if (> (length keep) 2) keep))

(defun est:is-rect (P / n i a b c ok)
  (if (= (length P) 4)
    (progn
      (setq n 4 i 0 ok T)
      (repeat 4
        (setq a (nth (rem (+ i 3) 4) P) b (nth i P) c (nth (rem (1+ i) 4) P))
        (if (> (abs (est:dot (est:unit (est:sub b a)) (est:unit (est:sub c b)))) 1e-4)
          (setq ok nil))
        (setq i (1+ i)))
      ok)))

;;; Offset para dentro (poligono anti-horario), d em unidades de desenho
(defun est:offset-in (P d / n i a b c n1 n2 x res ok k)
  (if (and P (> (length P) 2))
    (progn
      (setq n (length P) i 0 res nil)
      (repeat n
        (setq a (nth (rem (+ i n -1) n) P) b (nth i P) c (nth (rem (1+ i) n) P)
              n1 (est:mul (est:lnorm a b) d) n2 (est:mul (est:lnorm b c) d)
              x (inters (est:add a n1) (est:add b n1) (est:add b n2) (est:add c n2) nil))
        (setq res (cons (if x (est:2d x) (est:add b n1)) res) i (1+ i)))
      (setq res (reverse res) ok (> (est:area res) 1e-9) k 0)
      ;; cada lado deve manter o sentido original (senao colapsou)
      (repeat n
        (if (<= (est:dot (est:sub (nth (rem (1+ k) n) P) (nth k P))
                         (est:sub (nth (rem (1+ k) n) res) (nth k res))) 0.0)
          (setq ok nil))
        (setq k (1+ k)))
      (if ok res))))

;;; Vertice "superior esquerdo" (maior Y, depois menor X): canto dos ganchos
(defun est:corner-idx (P / i k best)
  (setq i 0 k 0 best (car P))
  (foreach pt P
    (if (or (> (cadr pt) (+ (cadr best) 1e-6))
            (and (equal (cadr pt) (cadr best) 1e-6) (< (car pt) (car best))))
      (setq best pt k i))
    (setq i (1+ i)))
  k)

;;; Lado superior (maior Y medio): lado aberto do estribo em U
(defun est:top-edge (P / n i k best y)
  (setq n (length P) i 0 k 0 best nil)
  (repeat n
    (setq y (/ (+ (cadr (nth i P)) (cadr (nth (rem (1+ i) n) P))) 2.0))
    (if (or (not best) (> y (+ best 1e-6))) (setq best y k i))
    (setq i (1+ i)))
  k)

(defun est:minedge (P / m a b)
  (setq a (last P) m nil)
  (foreach b P
    (setq m (if m (min m (distance a b)) (distance a b)) a b))
  m)

;;; Largura x altura (cm): lados do canto dos ganchos, ou caixa envolvente
(defun est:wh (P uf / Q bb)
  (if (est:is-rect P)
    (progn
      (setq Q (est:rotate P (est:corner-idx P)))
      (list (/ (distance (last Q) (car Q)) uf) (/ (distance (car Q) (cadr Q)) uf)))
    (progn
      (setq bb (est:bbox P))
      (list (/ (- (car (cadr bb)) (car (car bb))) uf)
            (/ (- (cadr (cadr bb)) (cadr (car bb))) uf)))))

;;; --------------------------------------------------------------------------
;;; Geometria do estribo
;;; --------------------------------------------------------------------------

;;; Poligono externo do estribo (unidades de desenho) conforme a origem
(defun est:cur-poly ( / uf b h)
  (setq uf (est:uf))
  (cond
    ((= *est:src* 'SEC) (est:offset-in *est:secpoly* (* (est:n "cob") uf)))
    ((= *est:src* 'DES) *est:despoly*)
    (T
     (setq b (* (est:n "b") uf) h (* (est:n "h") uf))
     (if (and (> b 0) (> h 0))
       (list '(0.0 0.0) (list b 0.0) (list b h) (list 0.0 h))))))

;;; Retorna lista de (pontos . fechado) a desenhar
(defun est:shape (P tipo L / n ti path tA tB Q v0 a b u s e)
  (setq L (min L (* 0.45 (est:minedge P))))
  (if (= tipo "t2")
    (progn
      (setq n (length P) ti (est:top-edge P)
            path (est:rotate P (rem (1+ ti) n))
            tA (est:add (car path) (est:mul (est:unit (est:sub (last path) (car path))) L))
            tB (est:add (last path) (est:mul (est:unit (est:sub (car path) (last path))) L)))
      (list (cons (append (list tA) path (list tB)) nil)))
    (progn
      (setq Q (est:rotate P (est:corner-idx P)) v0 (car Q)
            a (est:unit (est:sub (cadr Q) v0))
            b (est:unit (est:sub (last Q) v0)))
      (if (= tipo "t0")
        (progn
          ;; pernas a 45: duas retas paralelas na bissetriz do canto
          (setq u (est:unit (est:add a b)) s (* 0.3 L))
          (list (cons Q T)
                (cons (list (est:add v0 (est:mul a s))
                            (est:add (est:add v0 (est:mul a s)) (est:mul u L))) nil)
                (cons (list (est:add v0 (est:mul b s))
                            (est:add (est:add v0 (est:mul b s)) (est:mul u L))) nil)))
        (progn
          ;; pernas a 90: cada ponta dobra paralela ao outro lado
          (setq e (* 0.25 L))
          (list (cons Q T)
                (cons (list (est:add v0 (est:mul a e))
                            (est:add (est:add v0 (est:mul a e)) (est:mul b L))) nil)
                (cons (list (est:add v0 (est:mul b e))
                            (est:add (est:add v0 (est:mul b e)) (est:mul a L))) nil)))))))

;;; Segmentos cotados no detalhe: (p1 p2 valor_cm)
(defun est:dimsegs (P tipo perna uf / pts n i p1 p2 res Q a b)
  (cond
    ((= tipo "t2")
     (setq pts (car (car (est:shape P tipo (* perna uf)))) n (length pts) i 0)
     (while (< i (1- n))
       (setq p1 (nth i pts) p2 (nth (1+ i) pts)
             res (cons (list p1 p2 (if (or (= i 0) (= i (- n 2))) perna (/ (distance p1 p2) uf)))
                       res)
             i (1+ i)))
     (reverse res))
    ((est:is-rect P)
     (setq Q (est:rotate P (est:corner-idx P)))
     (list (list (last Q) (car Q) (/ (distance (last Q) (car Q)) uf))
           (list (car Q) (cadr Q) (/ (distance (car Q) (cadr Q)) uf))))
    (T
     (setq a (last P))
     (foreach b P (setq res (cons (list a b (/ (distance a b) uf)) res) a b))
     (reverse res))))

;;; Comprimento total (cm, arredondado para cima)
(defun est:calcC (P tipo / uf per ti n)
  (setq uf (est:uf) per (/ (est:perim P) uf))
  (if (= tipo "t2")
    (setq n (length P) ti (est:top-edge P)
          per (- per (/ (distance (nth ti P) (nth (rem (1+ ti) n) P)) uf))))
  (est:ceil (+ per (* 2.0 (+ (est:n "perna") (est:n "acr"))))))

;;; --------------------------------------------------------------------------
;;; Textos de identificacao
;;; --------------------------------------------------------------------------

(defun est:lbl-esp ()
  (if (> (est:n "esp") 0) (strcat " c/" (est:g "esp")) ""))

;;; Detalhe: N.16 6 %%c 5.0 c/17 C=125
(defun est:lbl-det (C)
  (strcat (est:g "prefixo") (est:g "pos") " " (est:g "qtd") " %%c " (est:bit)
          (est:lbl-esp)
          (if (= (est:g "incc") "1") (strcat " C=" (itoa C)) "")))

;;; Distribuicao: 6 N.16 %%c 5.0 c/17
(defun est:lbl-dist ()
  (strcat (est:g "qtd") " " (est:g "prefixo") (est:g "pos") " %%c " (est:bit) (est:lbl-esp)))

(defun est:nodcl (s) (vl-string-subst "fi" "%%c" s))

;;; --------------------------------------------------------------------------
;;; Regras automaticas
;;; --------------------------------------------------------------------------

(defun est:auto-perna ( / fi)
  (if (= (est:g "auto") "1")
    (progn
      (setq fi (est:fi))
      (if (= (est:g "tipo") "t0")
        (progn (est:s "perna" (est:fmt (max 5.0 (* 5.0 fi))))
               (est:s "acr" (est:fmt (* 5.0 fi))))
        (progn (est:s "perna" (est:fmt (max 7.0 (* 10.0 fi))))
               (est:s "acr" (est:fmt fi)))))))

(defun est:auto-qtd ( / l s q)
  (setq l (est:n "trecho") s (est:n "esp"))
  (if (and (> l 0) (> s 0))
    (progn
      (setq q (+ (fix (+ (/ l s) 1e-6)) (if (= (est:g "mais1") "1") 1 0)))
      (est:s "qtd" (itoa (max 1 q))))))

;;; --------------------------------------------------------------------------
;;; Janela (DCL gerado em arquivo temporario)
;;; --------------------------------------------------------------------------

(defun est:write-dcl ( / fn f l)
  (setq fn (vl-filename-mktemp "estribo" nil ".dcl") f (open fn "w"))
  (foreach l
    '("estribo : dialog {"
      "  label = \"ESTRIBO - Detalhamento de estribos\";"
      "  : row {"
      "    : column {"
      "      : boxed_column {"
      "        label = \"Identificacao\";"
      "        : row {"
      "          : edit_box { key = \"prefixo\"; label = \"Prefixo\"; edit_width = 4; }"
      "          : edit_box { key = \"pos\"; label = \"Posicao\"; edit_width = 5; }"
      "        }"
      "        : popup_list { key = \"bit\"; label = \"Bitola (mm)\"; edit_width = 8; }"
      "        : row {"
      "          : edit_box { key = \"esp\"; label = \"Espac. c/ (cm)\"; edit_width = 6; }"
      "          : edit_box { key = \"qtd\"; label = \"Quantidade\"; edit_width = 6; }"
      "        }"
      "        : row {"
      "          : edit_box { key = \"trecho\"; label = \"Trecho (cm)\"; edit_width = 7; }"
      "          : button { key = \"btn_trecho\"; label = \"Medir <\"; fixed_width = true; }"
      "        }"
      "        : toggle { key = \"mais1\"; label = \"Quantidade = L/s + 1\"; }"
      "        : toggle { key = \"incc\"; label = \"Incluir C= na identificacao\"; }"
      "      }"
      "      : boxed_radio_column {"
      "        key = \"tipo\"; label = \"Tipo de estribo\";"
      "        : radio_button { key = \"t0\"; label = \"Padrao - fechado, pernas a 45 graus\"; }"
      "        : radio_button { key = \"t1\"; label = \"Fechado - pernas a 90 graus\"; }"
      "        : radio_button { key = \"t2\"; label = \"Aberto (U) - pernas a 90 graus\"; }"
      "      }"
      "    }"
      "    : column {"
      "      : boxed_column {"
      "        label = \"Geometria (cm) - medidas externas do estribo\";"
      "        : text { key = \"origem\"; label = \"\"; width = 46; }"
      "        : row {"
      "          : edit_box { key = \"b\"; label = \"Largura B\"; edit_width = 6; }"
      "          : edit_box { key = \"h\"; label = \"Altura H\"; edit_width = 6; }"
      "        }"
      "        : row {"
      "          : edit_box { key = \"perna\"; label = \"Perna (min. 5)\"; edit_width = 6; }"
      "          : edit_box { key = \"acr\"; label = \"Acresc. dobra\"; edit_width = 6; }"
      "        }"
      "        : toggle { key = \"auto\"; label = \"Perna e acrescimo automaticos (NBR 6118)\"; }"
      "        : edit_box { key = \"cob\"; label = \"Cobrimento da secao (cm)\"; edit_width = 6; }"
      "        : row {"
      "          : button { key = \"btn_sec\"; label = \"Selecionar secao <\"; }"
      "          : button { key = \"btn_des\"; label = \"Desenhar estribo <\"; }"
      "          : button { key = \"btn_gen\"; label = \"Generico\"; }"
      "        }"
      "      }"
      "      : boxed_column {"
      "        label = \"Desenho\";"
      "        : row {"
      "          : popup_list { key = \"unid\"; label = \"Unidade\"; edit_width = 5; }"
      "          : edit_box { key = \"escala\"; label = \"Escala 1:\"; edit_width = 5; }"
      "          : edit_box { key = \"txt\"; label = \"Texto (mm)\"; edit_width = 4; }"
      "        }"
      "        : toggle { key = \"dsec\"; label = \"Desenhar estribo na secao / no desenho\"; }"
      "        : toggle { key = \"ddet\"; label = \"Desenhar detalhe cotado ao lado\"; }"
      "        : toggle { key = \"ddist\"; label = \"Desenhar distribuicao (planta / elevacao)\"; }"
      "        : toggle { key = \"cotadim\"; label = \"Cotas como dimensao (DIMALIGNED)\"; }"
      "      }"
      "    }"
      "  }"
      "  : boxed_column {"
      "    label = \"Resultado\";"
      "    : text { key = \"res1\"; label = \"\"; width = 96; }"
      "    : text { key = \"res2\"; label = \"\"; width = 96; }"
      "    : text { key = \"res3\"; label = \"\"; width = 96; }"
      "  }"
      "  : row {"
      "    fixed_width = true; alignment = centered;"
      "    : button { key = \"accept\"; label = \"Desenhar\"; is_default = true; width = 14; }"
      "    : button { key = \"cancel\"; label = \"Cancelar\"; is_cancel = true; width = 14; }"
      "  }"
      "}"
      "encontro : dialog {"
      "  label = \"ENCONTRO - Armadura de encontro de paredes (L cruzados)\";"
      "  : row {"
      "    : column {"
      "      : boxed_column {"
      "        label = \"Identificacao\";"
      "        : row {"
      "          : edit_box { key = \"prefixo\"; label = \"Prefixo\"; edit_width = 4; }"
      "          : edit_box { key = \"e_pos1\"; label = \"Barra 1\"; edit_width = 4; }"
      "          : edit_box { key = \"e_pos2\"; label = \"Barra 2\"; edit_width = 4; }"
      "        }"
      "        : popup_list { key = \"e_bit\"; label = \"Bitola (mm)\"; edit_width = 8; }"
      "        : row {"
      "          : edit_box { key = \"e_esp\"; label = \"Espac. c/ (cm)\"; edit_width = 6; }"
      "          : edit_box { key = \"e_qtd\"; label = \"Quantidade\"; edit_width = 6; }"
      "        }"
      "        : row {"
      "          : edit_box { key = \"e_trecho\"; label = \"Trecho (cm)\"; edit_width = 7; }"
      "          : button { key = \"btn_trecho\"; label = \"Medir <\"; fixed_width = true; }"
      "        }"
      "        : toggle { key = \"e_mais1\"; label = \"Quantidade = L/s + 1\"; }"
      "        : toggle { key = \"incc\"; label = \"Incluir C= na identificacao\"; }"
      "      }"
      "      : boxed_column {"
      "        label = \"Paredes (cm)\";"
      "        : text { key = \"e_origem\"; label = \"\"; width = 46; }"
      "        : row {"
      "          : edit_box { key = \"e_t1\"; label = \"Espessura 1\"; edit_width = 5; }"
      "          : edit_box { key = \"e_t2\"; label = \"Espessura 2\"; edit_width = 5; }"
      "        }"
      "        : row {"
      "          : edit_box { key = \"e_ang\"; label = \"Angulo (graus)\"; edit_width = 5; }"
      "          : edit_box { key = \"e_cob\"; label = \"Cobrimento\"; edit_width = 5; }"
      "        }"
      "        : row {"
      "          : button { key = \"btn_enc\"; label = \"Selecionar encontro <\"; }"
      "          : button { key = \"btn_gen\"; label = \"Generico\"; }"
      "        }"
      "      }"
      "    }"
      "    : column {"
      "      : boxed_column {"
      "        label = \"Barras (cm) - medidas externas\";"
      "        : text { label = \"Barra 1: face interna da parede 1 -> face externa da parede 2\"; }"
      "        : row {"
      "          : edit_box { key = \"e_la1\"; label = \"Perna na parede 1\"; edit_width = 5; }"
      "          : edit_box { key = \"e_lb1\"; label = \"Ancoragem na parede 2\"; edit_width = 5; }"
      "        }"
      "        : text { label = \"Barra 2: face interna da parede 2 -> face externa da parede 1\"; }"
      "        : row {"
      "          : edit_box { key = \"e_la2\"; label = \"Perna na parede 2\"; edit_width = 5; }"
      "          : edit_box { key = \"e_lb2\"; label = \"Ancoragem na parede 1\"; edit_width = 5; }"
      "        }"
      "        : row {"
      "          : edit_box { key = \"e_g\"; label = \"Gancho nas pontas\"; edit_width = 5; }"
      "          : toggle { key = \"e_gauto\"; label = \"Automatico (10 fi, min. 5)\"; }"
      "        }"
      "      }"
      "      : boxed_column {"
      "        label = \"Desenho\";"
      "        : row {"
      "          : popup_list { key = \"unid\"; label = \"Unidade\"; edit_width = 5; }"
      "          : edit_box { key = \"escala\"; label = \"Escala 1:\"; edit_width = 5; }"
      "          : edit_box { key = \"txt\"; label = \"Texto (mm)\"; edit_width = 4; }"
      "        }"
      "        : toggle { key = \"e_dpl\"; label = \"Desenhar barras na planta\"; }"
      "        : toggle { key = \"e_ddet\"; label = \"Desenhar detalhes cotados ao lado\"; }"
      "        : toggle { key = \"e_ddist\"; label = \"Desenhar distribuicao (cota no corte)\"; }"
      "      }"
      "    }"
      "  }"
      "  : boxed_column {"
      "    label = \"Resultado\";"
      "    : text { key = \"res1\"; label = \"\"; width = 96; }"
      "    : text { key = \"res2\"; label = \"\"; width = 96; }"
      "    : text { key = \"res3\"; label = \"\"; width = 96; }"
      "  }"
      "  : row {"
      "    fixed_width = true; alignment = centered;"
      "    : button { key = \"accept\"; label = \"Desenhar\"; is_default = true; width = 14; }"
      "    : button { key = \"cancel\"; label = \"Cancelar\"; is_cancel = true; width = 14; }"
      "  }"
      "}")
    (write-line l f))
  (close f)
  fn)

(defun est:read-all ()
  (foreach k *est:keys* (est:s k (get_tile k))))

(defun est:changed (k)
  (est:s k (get_tile k))
  (cond
    ((member k '("tipo" "bit" "auto")) (est:auto-perna))
    ((member k '("esp" "trecho" "mais1")) (est:auto-qtd)))
  (est:refresh))

(defun est:refresh ( / uf P wh C fi pmin msg)
  (setq uf (est:uf) P (est:cur-poly))
  (if (and P (/= *est:src* 'GEN))
    (progn
      (setq wh (est:wh P uf))
      (est:s "b" (est:fmt (car wh)))
      (est:s "h" (est:fmt (cadr wh)))))
  (foreach k '("b" "h" "perna" "acr" "qtd" "trecho") (set_tile k (est:g k)))
  (mode_tile "b" (if (= *est:src* 'GEN) 0 1))
  (mode_tile "h" (if (= *est:src* 'GEN) 0 1))
  (mode_tile "perna" (if (= (est:g "auto") "1") 1 0))
  (mode_tile "acr" (if (= (est:g "auto") "1") 1 0))
  (mode_tile "cob" (if (= *est:src* 'SEC) 0 1))
  (set_tile "origem"
    (cond
      ((= *est:src* 'SEC)
       (strcat "Origem: secao selecionada"
               (if (est:is-rect *est:secpoly*)
                 " (retangular)"
                 (strcat " (poligonal, " (itoa (length *est:secpoly*)) " lados)"))))
      ((= *est:src* 'DES) "Origem: estribo desenhado no DWG")
      (T "Origem: estribo generico (B x H digitados)")))
  (if P
    (progn
      (setq C (est:calcC P (est:g "tipo")) fi (est:fi))
      (set_tile "res1"
        (strcat "Estribo " (est:g "b") " x " (est:g "h") " cm"
                (if (and (/= *est:src* 'GEN) (not (est:is-rect P)))
                  (strcat " (poligono de " (itoa (length P)) " lados)") "")
                "   |   C = " (itoa C) " cm"
                "   |   Peso total = "
                (rtos (* (atof (est:g "qtd")) (/ C 100.0) 0.006165 (* 100.0 fi fi)) 2 2) " kg"))
      (set_tile "res2"
        (strcat "Detalhe: " (est:nodcl (est:lbl-det C))
                "      Distribuicao: " (est:nodcl (est:lbl-dist))
                (if (> (est:n "trecho") 0) (strcat " (" (est:g "trecho") ")") "")))
      (setq pmin (if (= (est:g "tipo") "t0") (max 5.0 (* 5.0 fi)) (max 7.0 (* 10.0 fi))))
      (setq msg
        (cond
          ((< (est:n "perna") 5.0) "ERRO: a perna minima e 5 cm.")
          ((< (est:n "perna") (- pmin 1e-6))
           (strcat "Atencao: NBR 6118 9.4.6.1 recomenda perna >= " (est:fmt pmin) " cm para este tipo/bitola."))
          (T "OK")))
      (set_tile "res3" msg))
    (progn
      (set_tile "res1" "Geometria invalida: verifique B, H ou o cobrimento (secao pequena demais).")
      (set_tile "res2" "")
      (set_tile "res3" ""))))

(defun est:validate ( / err)
  (setq err
    (cond
      ((= (vl-string-trim " " (est:g "pos")) "") "Informe a posicao (ex.: 16).")
      ((< (est:n "perna") 5.0) "A perna minima do estribo e 5 cm.")
      ((not (est:cur-poly)) "Geometria invalida: verifique B, H ou o cobrimento.")
      ((<= (est:n "escala") 0) "Escala invalida.")
      ((<= (est:n "txt") 0) "Altura de texto invalida.")
      ((< (atoi (est:g "qtd")) 1) "Quantidade deve ser >= 1.")
      ((< (est:n "esp") 0) "Espacamento invalido.")))
  (if err (progn (alert err) nil) T))

(defun est:dlg-init ()
  (start_list "bit") (mapcar 'add_list *est:bitolas*) (end_list)
  (start_list "unid") (mapcar 'add_list *est:unids*) (end_list)
  (foreach k *est:keys* (set_tile k (est:g k)))
  (foreach k *est:keys* (action_tile k "(est:changed $key)"))
  (action_tile "btn_sec" "(est:read-all)(done_dialog 2)")
  (action_tile "btn_des" "(est:read-all)(done_dialog 3)")
  (action_tile "btn_trecho" "(est:read-all)(done_dialog 4)")
  (action_tile "btn_gen" "(setq *est:src* 'GEN)(est:refresh)")
  (action_tile "accept" "(est:read-all)(if (est:validate) (done_dialog 1))")
  (est:auto-perna)
  (est:refresh))

;;; --------------------------------------------------------------------------
;;; Selecoes no desenho
;;; --------------------------------------------------------------------------

;;; Aplica matriz de nentsel (4 linhas: 3 de rotacao/escala + translacao)
(defun est:xform (p m)
  (list (+ (* (car p) (car (nth 0 m))) (* (cadr p) (car (nth 1 m)))
           (* (caddr p) (car (nth 2 m))) (car (nth 3 m)))
        (+ (* (car p) (cadr (nth 0 m))) (* (cadr p) (cadr (nth 1 m)))
           (* (caddr p) (cadr (nth 2 m))) (cadr (nth 3 m)))))

(defun est:pick-section ( / sel en ed elev pts arc poly)
  (setq sel (nentsel "\nSelecione a polilinha fechada da secao: "))
  (cond
    ((not sel) nil)
    ((/= (cdr (assoc 0 (setq ed (entget (setq en (car sel)))))) "LWPOLYLINE")
     (alert "Selecione uma POLILINHA (LWPOLYLINE) fechada."))
    (T
     (setq elev (if (assoc 38 ed) (cdr (assoc 38 ed)) 0.0))
     (foreach g ed
       (cond
         ((= (car g) 10)
          (setq pts (cons (list (car (cdr g)) (cadr (cdr g)) elev) pts)))
         ((and (= (car g) 42) (/= (cdr g) 0.0)) (setq arc T))))
     (setq pts (reverse pts))
     (setq pts
       (if (= (length sel) 4)
         (mapcar '(lambda (pt) (est:xform pt (caddr sel))) pts)
         (mapcar '(lambda (pt) (est:2d (trans pt en 0))) pts)))
     (if (and (= 0 (logand 1 (cdr (assoc 70 ed))))
              (not (equal (car pts) (last pts) 1e-6)))
       (princ "\nAviso: polilinha aberta - sera considerada fechada."))
     (if arc (princ "\nAviso: trechos em arco serao tratados como retos."))
     (setq poly (est:clean pts))
     (if poly
       (setq *est:secpoly* poly *est:src* 'SEC)
       (alert "Polilinha invalida (menos de 3 vertices uteis).")))))

(defun est:pick-rect ( / p1 p2 pts p)
  (initget "Poligono")
  (setq p1 (getpoint "\nPrimeiro canto do estribo ou [Poligono]: "))
  (cond
    ((= p1 "Poligono")
     (if (setq p (getpoint "\nPrimeiro vertice: "))
       (progn
         (setq pts (list p))
         (while (setq p (getpoint p "\nProximo vertice <Enter fecha>: "))
           (grdraw (car pts) p 1)
           (setq pts (cons p pts)))
         (redraw)
         (setq pts (reverse pts)))))
    (p1
     (if (setq p2 (getcorner p1 "\nCanto oposto: "))
       (setq pts (list p1 (list (car p2) (cadr p1) (caddr p1)) p2
                       (list (car p1) (cadr p2) (caddr p1)))))))
  (if pts
    (progn
      (setq pts (est:clean (mapcar '(lambda (q) (est:2d (trans q 1 0))) pts)))
      (if pts
        (setq *est:despoly* pts *est:src* 'DES)
        (alert "Contorno invalido.")))))

(defun est:pick-trecho ( / p1 p2 w1 w2)
  (if (and (setq p1 (getpoint "\nInicio do trecho de distribuicao: "))
           (setq p2 (getpoint p1 "\nFim do trecho: ")))
    (progn
      (setq w1 (est:2d (trans p1 1 0)) w2 (est:2d (trans p2 1 0)))
      (setq *est:distpts* (list w1 w2))
      (est:s "trecho" (est:fmt (/ (distance w1 w2) (est:uf))))
      (est:auto-qtd))))

;;; --------------------------------------------------------------------------
;;; Criacao de entidades
;;; --------------------------------------------------------------------------

(defun est:layer (name col)
  (if (not (tblsearch "LAYER" name))
    (entmake (list '(0 . "LAYER") '(100 . "AcDbSymbolTableRecord")
                   '(100 . "AcDbLayerTableRecord") (cons 2 name) '(70 . 0)
                   (cons 62 col) '(6 . "Continuous")))))

(defun est:pline (pts closed lay)
  (entmakex
    (append
      (list '(0 . "LWPOLYLINE") '(100 . "AcDbEntity") (cons 8 lay)
            '(100 . "AcDbPolyline") (cons 90 (length pts)) (cons 70 (if closed 1 0)))
      (mapcar '(lambda (p) (cons 10 (est:2d p))) pts))))

(defun est:line (a b lay)
  (entmakex (list '(0 . "LINE") (cons 8 lay) (cons 10 (est:3d a)) (cons 11 (est:3d b)))))

;;; Texto centralizado (meio-centro)
(defun est:text (pt str h ang lay)
  (entmakex (list '(0 . "TEXT") (cons 8 lay) (cons 7 "Arial")
                  (cons 10 (est:3d pt)) (cons 11 (est:3d pt)) (cons 40 h)
                  (cons 1 str) (cons 50 ang) '(72 . 1) '(73 . 2))))

;;; Angulo legivel (texto nunca de cabeca para baixo)
(defun est:readang (a)
  (if (and (> a (+ (/ pi 2.0) 1e-6)) (<= a (+ (* 1.5 pi) 1e-6)))
    (rem (+ a pi) (* 2.0 pi))
    a))

(defun est:ms ()
  (vla-get-ModelSpace (vla-get-ActiveDocument (vlax-get-acad-object))))

;;; Cota de um lado do detalhe (texto do lado de fora ou DIMALIGNED)
(defun est:dimtext (p1 p2 v th / nr mid str)
  (setq nr (est:rnorm p1 p2) mid (est:mid p1 p2) str (est:fmt v))
  (if (= (est:g "cotadim") "1")
    (est:dim p1 p2 (est:add mid (est:mul nr (* 1.2 th)))
             (if (equal (/ (distance p1 p2) (est:uf)) v 0.05) nil str))
    (est:text (est:add mid (est:mul nr (* 0.9 th))) str th (est:readang (angle p1 p2)) "EST_Cota")))

;;; Layers, estilo de texto e estilo de cota
(defun est:setup ( / l)
  (foreach l *est:layers* (est:layer (car l) (cadr l)))
  (est:textstyle)
  (est:dimstyle))

;;; Estilo de texto Arial (criado se nao existir)
(defun est:textstyle ()
  (if (not (tblsearch "STYLE" "Arial"))
    (entmake '((0 . "STYLE") (100 . "AcDbSymbolTableRecord")
               (100 . "AcDbTextStyleTableRecord") (2 . "Arial") (70 . 0)
               (40 . 0.0) (41 . 1.0) (50 . 0.0) (71 . 0) (42 . 2.5)
               (3 . "arial.ttf") (4 . "")))))

;;; Estilo de cota EST_Cota (criado se nao existir): traco obliquo, texto
;;; Arial acima da linha e alinhado, 1 casa decimal com virgula, cores ByLayer.
;;; Tamanhos em mm de papel; a escala vai em cada cota (ScaleFactor).
(defun est:dimstyle ( / vars old doc ds)
  (if (not (tblsearch "DIMSTYLE" "EST_Cota"))
    (progn
      (setq vars (list '("DIMBLK" . "_OBLIQUE") '("DIMASZ" . 1.5)
                       (cons "DIMTXT" (est:n "txt")) '("DIMEXE" . 1.5)
                       '("DIMEXO" . 1.5) '("DIMGAP" . 0.8) '("DIMTAD" . 1)
                       '("DIMTIH" . 0) '("DIMTOH" . 0) '("DIMTIX" . 1)
                       '("DIMLUNIT" . 2) '("DIMDEC" . 1) '("DIMZIN" . 8)
                       '("DIMDSEP" . ",") '("DIMSCALE" . 1.0) '("DIMLFAC" . 1.0)
                       '("DIMCLRD" . 256) '("DIMCLRE" . 256) '("DIMCLRT" . 256)
                       '("DIMTXSTY" . "Arial"))
            old (mapcar '(lambda (v) (cons (car v) (getvar (car v)))) vars))
      (foreach v vars (vl-catch-all-apply 'setvar (list (car v) (cdr v))))
      (setq doc (vla-get-ActiveDocument (vlax-get-acad-object))
            ds (vla-add (vla-get-DimStyles doc) "EST_Cota"))
      (vla-CopyFrom ds doc)
      (foreach v old
        (vl-catch-all-apply 'setvar
          (list (car v) (if (and (= (car v) "DIMBLK") (= (cdr v) "")) "." (cdr v))))))))

;;; Cota real (DIMALIGNED) no estilo e layer EST_Cota.
;;; O valor medido sai em cm em qualquer unidade de desenho.
(defun est:dim (p1 p2 loc ovr / o)
  (setq o (vla-AddDimAligned (est:ms) (vlax-3d-point (est:3d p1)) (vlax-3d-point (est:3d p2))
                             (vlax-3d-point (est:3d loc))))
  (vla-put-StyleName o "EST_Cota")
  (vla-put-Layer o "EST_Cota")
  (vla-put-ScaleFactor o (* (est:n "escala") (est:uf) 0.1))
  (vla-put-LinearScaleFactor o (/ 1.0 (est:uf)))
  (vla-put-TextStyle o "Arial")
  (if ovr (vla-put-TextOverride o ovr))
  o)

;;; Linha de distribuicao como cota real:
;;;   "6 N.16 %%c 5.0 c/17" acima da linha e "(111)" (medido) abaixo
(defun est:dist-dim (p1 p2 lbl / loc)
  (setq loc (getpoint (est:3d p1) "\nPosicao da linha de cota <sobre os pontos>: "))
  (setq loc (if loc (est:2d (trans loc 1 0)) p1))
  (est:dim p1 p2 loc (strcat lbl "\\X(<>)")))

;;; Estribo na secao / no local desenhado
(defun est:draw-stirrup (P)
  (foreach it (est:shape P (est:g "tipo") (* (est:n "perna") (est:uf)))
    (est:pline (car it) (cdr it) "EST_ArmPos")))

;;; Detalhe cotado com identificacao embaixo
(defun est:draw-detail (P ip C th / bb d Pd uf)
  (setq uf (est:uf) bb (est:bbox P) d (est:sub ip (car bb))
        Pd (mapcar '(lambda (pt) (est:add pt d)) P))
  (foreach it (est:shape Pd (est:g "tipo") (* (est:n "perna") uf))
    (est:pline (car it) (cdr it) "EST_ArmPos"))
  (foreach sg (est:dimsegs Pd (est:g "tipo") (est:n "perna") uf)
    (est:dimtext (car sg) (cadr sg) (caddr sg) th))
  (setq bb (est:bbox Pd))
  (est:text (list (/ (+ (car (car bb)) (car (cadr bb))) 2.0) (- (cadr (car bb)) (* 3.0 th)))
            (est:lbl-det C) th 0.0 "EST_ArmTexto"))

;;; --------------------------------------------------------------------------
;;; Execucao apos o OK
;;; --------------------------------------------------------------------------

(defun est:run ( / P C th ip def bb p1 p2 l)
  (est:setup)
  ;; 0) trecho da distribuicao antes dos detalhes (a quantidade depende dele)
  (if (and (= (est:g "ddist") "1") (not *est:distpts*))
    (if (and (setq p1 (getpoint "\nInicio do trecho de distribuicao <Enter pula>: "))
             (setq p2 (getpoint p1 "\nFim do trecho: ")))
      (progn
        (setq *est:distpts* (list (est:2d (trans p1 1 0)) (est:2d (trans p2 1 0))))
        (if (<= (est:n "trecho") 0)
          (progn
            (est:s "trecho" (est:fmt (/ (apply 'distance *est:distpts*) (est:uf))))
            (est:auto-qtd))))))
  (setq P (est:cur-poly) C (est:calcC P (est:g "tipo")) th (est:th))
  ;; 1) estribo dentro da secao (ou no contorno desenhado)
  (if (and (= (est:g "dsec") "1") (member *est:src* '(SEC DES)))
    (est:draw-stirrup P))
  ;; 2) detalhe cotado ao lado
  (if (= (est:g "ddet") "1")
    (progn
      (if (/= *est:src* 'GEN)
        (setq bb (est:bbox (if (= *est:src* 'SEC) *est:secpoly* P))
              def (list (+ (car (cadr bb)) (* 6.0 th)) (cadr (car bb)))))
      (setq ip (getpoint (if def
                           "\nPonto do detalhe (canto inferior esquerdo) <ao lado>: "
                           "\nPonto do detalhe (canto inferior esquerdo) <Enter pula>: ")))
      (setq ip (if ip (est:2d (trans ip 1 0)) def))
      (if ip (est:draw-detail P ip C th))))
  ;; 3) distribuicao em planta / elevacao
  (if (= (est:g "ddist") "1")
    (progn
      (if *est:distpts*
        (est:dist-dim (car *est:distpts*) (cadr *est:distpts*) (est:lbl-dist)))))
  (princ (strcat "\n" (est:lbl-det C) "  ->  estribo " (est:g "b") " x " (est:g "h") " cm")))

;;; ==========================================================================
;;; ENCONTRO - armadura de encontro de paredes em L cruzados
;;; --------------------------------------------------------------------------
;;; Cada barra vem pela face INTERNA da sua parede, atravessa o encontro ate
;;; a face EXTERNA da outra parede e dobra ao longo dela (ancoragem). Assim
;;; nenhuma barra dobra no canto interno (evita o empuxo ao vazio).
;;;   Barra 1: face interna da parede 1 -> face externa da parede 2
;;;   Barra 2: face interna da parede 2 -> face externa da parede 1
;;; Ganchos a 90 graus nas pontas, voltados para a face oposta da parede.
;;; C = perna + ancoragem + 2 x gancho (medidas externas, arredondado p/ cima)
;;; ==========================================================================

(setq *enc:keys*
  '("prefixo" "e_pos1" "e_pos2" "e_bit" "e_esp" "e_qtd" "e_trecho" "e_mais1"
    "incc" "e_t1" "e_t2" "e_ang" "e_cob" "e_la1" "e_lb1" "e_la2" "e_lb2" "e_g"
    "e_gauto" "unid" "escala" "txt" "e_dpl" "e_ddet" "e_ddist"))

(defun enc:bit () (nth (atoi (est:g "e_bit")) *est:bitolas*))
(defun enc:fi ()  (/ (atof (enc:bit)) 10.0))

;;; Geometria do encontro: (canto_ext d1 d2 n1 n2 t1 t2), unidades de desenho.
;;; d1/d2 = direcao das faces externas; n1/n2 = normal da face externa para a
;;; interna de cada parede; t1/t2 = espessuras.
(defun enc:geo-from (po d1 d2 pin / v)
  (setq v (est:sub pin po))
  (list po d1 d2
        (est:unit (est:sub v (est:mul d1 (est:dot v d1))))
        (est:unit (est:sub v (est:mul d2 (est:dot v d2))))
        (abs (est:cross d1 v)) (abs (est:cross d2 v))))

(defun enc:geo ( / uf a d1 d2)
  (setq uf (est:uf))
  (cond
    ((= *enc:src* 'SEL) *enc:pick*)
    ((and (> (est:n "e_ang") 5.0) (< (est:n "e_ang") 175.0))
     (setq a (* (est:n "e_ang") (/ pi 180.0))
           d1 '(1.0 0.0) d2 (list (cos a) (- (sin a))))
     (list '(0.0 0.0) d1 d2
           (est:unit (est:sub d2 (est:mul d1 (est:dot d2 d1))))
           (est:unit (est:sub d1 (est:mul d2 (est:dot d1 d2))))
           (* (est:n "e_t1") uf) (* (est:n "e_t2") uf)))))

(defun enc:angle (geo)
  (* (atan (abs (est:cross (nth 1 geo) (nth 2 geo))) (est:dot (nth 1 geo) (nth 2 geo)))
     (/ 180.0 pi)))

;;; Interseccao de duas retas (ponto + direcao)
(defun enc:xl (p d q e / x)
  (setq x (inters p (est:add p d) q (est:add q e) nil))
  (if x (est:2d x)))

;;; Barra em L: vertice vx, perna (da, la), ancoragem (db, lb), ganchos
(defun enc:lbar (vx da la db lb ha ga hb gb / pa pb)
  (setq pa (est:add vx (est:mul da la)) pb (est:add vx (est:mul db lb)))
  (list (est:add pa (est:mul ha ga)) pa vx pb (est:add pb (est:mul hb gb))))

;;; Retorna (barra1 barra2 travessia1_cm travessia2_cm).
;;; real = T: ganchos com o comprimento informado (detalhe);
;;; real = nil: ganchos limitados a espessura livre (planta).
(defun enc:bars (geo real / uf po d1 d2 n1 n2 t1 t2 cb g ga1 gb1 ga2 gb2 v1 v2 x1 x2)
  (setq uf (est:uf) po (nth 0 geo) d1 (nth 1 geo) d2 (nth 2 geo)
        n1 (nth 3 geo) n2 (nth 4 geo) t1 (nth 5 geo) t2 (nth 6 geo)
        cb (* (est:n "e_cob") uf) g (* (est:n "e_g") uf))
  (if real
    (setq ga1 g gb1 g ga2 g gb2 g)
    (setq ga1 (min g (- t1 cb cb)) gb1 (min g (- t2 cb cb))
          ga2 (min g (- t2 cb cb)) gb2 (min g (- t1 cb cb))))
  ;; vertices: face interna de uma parede x face externa da outra
  (setq v1 (enc:xl (est:add po (est:mul n1 (- t1 cb))) d1 (est:add po (est:mul n2 cb)) d2)
        v2 (enc:xl (est:add po (est:mul n2 (- t2 cb))) d2 (est:add po (est:mul n1 cb)) d1))
  ;; saida do encontro: onde a perna cruza a face interna da outra parede
  (setq x1 (enc:xl v1 d1 (est:add po (est:mul n2 t2)) d2)
        x2 (enc:xl v2 d2 (est:add po (est:mul n1 t1)) d1))
  (list
    (enc:lbar v1 d1 (* (est:n "e_la1") uf) d2 (* (est:n "e_lb1") uf)
              (est:mul n1 -1.0) ga1 n2 gb1)
    (enc:lbar v2 d2 (* (est:n "e_la2") uf) d1 (* (est:n "e_lb2") uf)
              (est:mul n2 -1.0) ga2 n1 gb2)
    (/ (distance v1 x1) uf)
    (/ (distance v2 x2) uf)))

(defun enc:C (ka kb)
  (est:ceil (+ (est:n ka) (est:n kb) (* 2.0 (est:n "e_g")))))

(defun enc:lbl-esp ()
  (if (> (est:n "e_esp") 0) (strcat " c/" (est:g "e_esp")) ""))

;;; Detalhe: N.1 6 %%c 8.0 c/15 C=134
(defun enc:lbl-det (pos C)
  (strcat (est:g "prefixo") pos " " (est:g "e_qtd") " %%c " (enc:bit) (enc:lbl-esp)
          (if (= (est:g "incc") "1") (strcat " C=" (itoa C)) "")))

;;; Distribuicao: 6 N.1 N.2 %%c 8.0 c/15
(defun enc:lbl-dist ()
  (strcat (est:g "e_qtd") " " (est:g "prefixo") (est:g "e_pos1") " "
          (est:g "prefixo") (est:g "e_pos2") " %%c " (enc:bit) (enc:lbl-esp)))

;;; --------------------------------------------------------------------------
;;; Janela
;;; --------------------------------------------------------------------------

(defun enc:auto-g ()
  (if (= (est:g "e_gauto") "1")
    (est:s "e_g" (est:fmt (max 5.0 (* 10.0 (enc:fi)))))))

(defun enc:auto-qtd ( / l s)
  (setq l (est:n "e_trecho") s (est:n "e_esp"))
  (if (and (> l 0) (> s 0))
    (est:s "e_qtd"
      (itoa (max 1 (+ (fix (+ (/ l s) 1e-6)) (if (= (est:g "e_mais1") "1") 1 0)))))))

(defun enc:check (geo / c2)
  (setq c2 (* 2.0 (est:n "e_cob")))
  (cond
    ((not geo) "Angulo invalido: use entre 5 e 175 graus.")
    ((or (= (vl-string-trim " " (est:g "e_pos1")) "")
         (= (vl-string-trim " " (est:g "e_pos2")) ""))
     "Informe as posicoes das duas barras.")
    ((or (<= (/ (nth 5 geo) (est:uf)) c2) (<= (/ (nth 6 geo) (est:uf)) c2))
     "Espessura da parede menor que 2 x cobrimento.")
    ((or (<= (est:n "e_la1") 0) (<= (est:n "e_lb1") 0)
         (<= (est:n "e_la2") 0) (<= (est:n "e_lb2") 0))
     "Informe pernas e ancoragens maiores que zero.")
    ((< (est:n "e_g") 0) "Gancho invalido.")
    ((<= (est:n "escala") 0) "Escala invalida.")
    ((<= (est:n "txt") 0) "Altura de texto invalida.")
    ((< (atoi (est:g "e_qtd")) 1) "Quantidade deve ser >= 1.")))

(defun enc:refresh ( / geo uf err br C1 C2 fi msg)
  (setq geo (enc:geo) uf (est:uf))
  (if (and geo (= *enc:src* 'SEL))
    (progn
      (est:s "e_t1" (est:fmt (/ (nth 5 geo) uf)))
      (est:s "e_t2" (est:fmt (/ (nth 6 geo) uf)))
      (est:s "e_ang" (est:fmt (enc:angle geo)))))
  (foreach k '("e_t1" "e_t2" "e_ang" "e_g" "e_qtd" "e_trecho") (set_tile k (est:g k)))
  (foreach k '("e_t1" "e_t2" "e_ang") (mode_tile k (if (= *enc:src* 'SEL) 1 0)))
  (mode_tile "e_g" (if (= (est:g "e_gauto") "1") 1 0))
  (set_tile "e_origem"
    (if (= *enc:src* 'SEL)
      "Origem: encontro selecionado no desenho"
      "Origem: generico (espessuras e angulo digitados)"))
  (setq err (enc:check geo))
  (if err
    (progn (set_tile "res1" (strcat "ERRO: " err)) (set_tile "res2" "") (set_tile "res3" ""))
    (progn
      (setq br (enc:bars geo T) fi (enc:fi)
            C1 (enc:C "e_la1" "e_lb1") C2 (enc:C "e_la2" "e_lb2"))
      (set_tile "res1"
        (strcat "Paredes " (est:g "e_t1") " / " (est:g "e_t2") " cm a " (est:g "e_ang") " graus"
                "   |   " (est:g "prefixo") (est:g "e_pos1") " C=" (itoa C1)
                "   |   " (est:g "prefixo") (est:g "e_pos2") " C=" (itoa C2)
                "   |   Peso total = "
                (rtos (* (atof (est:g "e_qtd")) (/ (+ C1 C2) 100.0) 0.006165 (* 100.0 fi fi)) 2 2)
                " kg"))
      (set_tile "res2"
        (strcat (est:nodcl (enc:lbl-det (est:g "e_pos1") C1)) "   /   "
                (est:nodcl (enc:lbl-det (est:g "e_pos2") C2)) "   |   Distribuicao: "
                (est:nodcl (enc:lbl-dist))
                (if (> (est:n "e_trecho") 0) (strcat " (" (est:g "e_trecho") ")") "")))
      (setq msg
        (cond
          ((<= (est:n "e_la1") (nth 2 br))
           (strcat "Atencao: a perna da barra 1 precisa passar de " (est:fmt (nth 2 br))
                   " cm para atravessar o encontro."))
          ((<= (est:n "e_la2") (nth 3 br))
           (strcat "Atencao: a perna da barra 2 precisa passar de " (est:fmt (nth 3 br))
                   " cm para atravessar o encontro."))
          ((> (* (est:n "e_g") uf) (- (min (nth 5 geo) (nth 6 geo)) (* 2.0 (est:n "e_cob") uf)))
           "Atencao: gancho maior que a espessura livre; na planta ele sera limitado.")
          (T "OK: as barras atravessam o encontro e ancoram na face externa (sem empuxo ao vazio).")))
      (set_tile "res3" msg))))

(defun enc:read-all ()
  (foreach k *enc:keys* (est:s k (get_tile k))))

(defun enc:changed (k)
  (est:s k (get_tile k))
  (cond
    ((member k '("e_bit" "e_gauto")) (enc:auto-g))
    ((member k '("e_esp" "e_trecho" "e_mais1")) (enc:auto-qtd)))
  (enc:refresh))

(defun enc:validate ( / err)
  (setq err (enc:check (enc:geo)))
  (if err (progn (alert err) nil) T))

(defun enc:dlg-init ()
  (start_list "e_bit") (mapcar 'add_list *est:bitolas*) (end_list)
  (start_list "unid") (mapcar 'add_list *est:unids*) (end_list)
  (foreach k *enc:keys* (set_tile k (est:g k)))
  (foreach k *enc:keys* (action_tile k "(enc:changed $key)"))
  (action_tile "btn_enc" "(enc:read-all)(done_dialog 2)")
  (action_tile "btn_trecho" "(enc:read-all)(done_dialog 4)")
  (action_tile "btn_gen" "(setq *enc:src* 'GEN)(enc:refresh)")
  (action_tile "accept" "(enc:read-all)(if (enc:validate) (done_dialog 1))")
  (enc:auto-g)
  (enc:refresh))

;;; --------------------------------------------------------------------------
;;; Selecoes
;;; --------------------------------------------------------------------------

(defun enc:pick ( / po p1 p2 pin w d1 d2 geo)
  (if (and (setq po (getpoint "\nCanto EXTERNO do encontro: "))
           (setq p1 (getpoint po "\nPonto na face externa da parede 1: "))
           (setq p2 (getpoint po "\nPonto na face externa da parede 2: "))
           (setq pin (getpoint po "\nCanto INTERNO do encontro: ")))
    (progn
      (setq w (mapcar '(lambda (q) (est:2d (trans q 1 0))) (list po p1 p2 pin))
            d1 (est:unit (est:sub (nth 1 w) (nth 0 w)))
            d2 (est:unit (est:sub (nth 2 w) (nth 0 w))))
      (setq geo (enc:geo-from (nth 0 w) d1 d2 (nth 3 w)))
      (if (and (> (abs (est:cross d1 d2)) 0.05)
               (> (nth 5 geo) 1e-6) (> (nth 6 geo) 1e-6)
               (> (est:dot (nth 3 geo) d2) 0.0) (> (est:dot (nth 4 geo) d1) 0.0))
        (setq *enc:pick* geo *enc:src* 'SEL)
        (alert "Pontos invalidos: confira o canto externo, as faces externas e o canto interno.")))))

(defun enc:pick-trecho ( / p1 p2)
  (if (and (setq p1 (getpoint "\nInicio do trecho de distribuicao (no corte): "))
           (setq p2 (getpoint p1 "\nFim do trecho: ")))
    (progn
      (setq *enc:distpts* (list (est:2d (trans p1 1 0)) (est:2d (trans p2 1 0))))
      (est:s "e_trecho" (est:fmt (/ (apply 'distance *enc:distpts*) (est:uf))))
      (enc:auto-qtd))))

;;; --------------------------------------------------------------------------
;;; Desenho
;;; --------------------------------------------------------------------------

;;; Cota de um trecho, sempre do lado de fora da barra (longe do centro)
(defun enc:segdim (p1 p2 v th cen / tmp)
  (if (< (est:dot (est:rnorm p1 p2) (est:sub (est:mid p1 p2) cen)) 0.0)
    (setq tmp p1 p1 p2 p2 tmp))
  (est:dimtext p1 p2 v th))

;;; Detalhe cotado de uma barra; retorna a largura ocupada
(defun enc:detail (pts ip vals lbl th / bb d q cen i)
  (setq bb (est:bbox pts) d (est:sub ip (car bb))
        q (mapcar '(lambda (pt) (est:add pt d)) pts)
        cen (est:mul (est:add (est:add (nth 1 q) (nth 2 q)) (nth 3 q)) (/ 1.0 3.0)))
  (est:pline q nil "EST_ArmPos")
  (setq i 0)
  (repeat 4
    (if (> (nth i vals) 0) (enc:segdim (nth i q) (nth (1+ i) q) (nth i vals) th cen))
    (setq i (1+ i)))
  (setq bb (est:bbox q))
  (est:text (list (/ (+ (car (car bb)) (car (cadr bb))) 2.0) (- (cadr (car bb)) (* 3.0 th)))
            lbl th 0.0 "EST_ArmTexto")
  (max (- (car (cadr bb)) (car (car bb))) (* 0.6 th (strlen lbl))))

;;; Nome da barra na planta, do lado de dentro da parede, ao longo da perna
(defun enc:tag (bar nrm pos th / p a)
  (setq p (est:add (est:mid (nth 1 bar) (nth 2 bar))
                   (est:mul nrm (+ (* (est:n "e_cob") (est:uf)) (* 1.2 th))))
        a (est:readang (angle (nth 2 bar) (nth 1 bar))))
  (est:text p (strcat (est:g "prefixo") pos) th a "EST_ArmTexto"))

(defun enc:run ( / geo th pl rl C1 C2 bb def ip w1 p1 p2)
  (est:setup)
  ;; 0) trecho da distribuicao antes dos detalhes (a quantidade depende dele)
  (if (and (= (est:g "e_ddist") "1") (not *enc:distpts*))
    (if (and (setq p1 (getpoint "\nInicio do trecho de distribuicao <Enter pula>: "))
             (setq p2 (getpoint p1 "\nFim do trecho: ")))
      (progn
        (setq *enc:distpts* (list (est:2d (trans p1 1 0)) (est:2d (trans p2 1 0))))
        (if (<= (est:n "e_trecho") 0)
          (progn
            (est:s "e_trecho" (est:fmt (/ (apply 'distance *enc:distpts*) (est:uf))))
            (enc:auto-qtd))))))
  (setq geo (enc:geo) th (est:th)
        pl (enc:bars geo nil) rl (enc:bars geo T)
        C1 (enc:C "e_la1" "e_lb1") C2 (enc:C "e_la2" "e_lb2"))
  ;; 1) barras na planta (so quando o encontro foi selecionado)
  (if (and (= (est:g "e_dpl") "1") (= *enc:src* 'SEL))
    (progn
      (est:pline (nth 0 pl) nil "EST_ArmPos")
      (est:pline (nth 1 pl) nil "EST_ArmPos")
      (enc:tag (nth 0 pl) (nth 3 geo) (est:g "e_pos1") th)
      (enc:tag (nth 1 pl) (nth 4 geo) (est:g "e_pos2") th)))
  ;; 2) detalhes cotados
  (if (= (est:g "e_ddet") "1")
    (progn
      (if (= *enc:src* 'SEL)
        (setq bb (est:bbox (append (nth 0 pl) (nth 1 pl)))
              def (list (+ (car (cadr bb)) (* 8.0 th)) (cadr (car bb)))))
      (setq ip (getpoint (if def
                           "\nPonto dos detalhes (canto inferior esquerdo) <ao lado>: "
                           "\nPonto dos detalhes (canto inferior esquerdo) <Enter pula>: ")))
      (setq ip (if ip (est:2d (trans ip 1 0)) def))
      (if ip
        (progn
          (setq w1 (enc:detail (nth 0 rl) ip
                     (list (est:n "e_g") (est:n "e_la1") (est:n "e_lb1") (est:n "e_g"))
                     (enc:lbl-det (est:g "e_pos1") C1) th))
          (enc:detail (nth 1 rl) (list (+ (car ip) w1 (* 6.0 th)) (cadr ip))
                      (list (est:n "e_g") (est:n "e_la2") (est:n "e_lb2") (est:n "e_g"))
                      (enc:lbl-det (est:g "e_pos2") C2) th)))))
  ;; 3) distribuicao (cota real no corte / elevacao)
  (if (= (est:g "e_ddist") "1")
    (progn
      (if *enc:distpts*
        (est:dist-dim (car *enc:distpts*) (cadr *enc:distpts*) (enc:lbl-dist)))))
  (princ (strcat "\n" (enc:lbl-det (est:g "e_pos1") C1) "  /  " (enc:lbl-det (est:g "e_pos2") C2))))

;;; --------------------------------------------------------------------------
;;; Comando
;;; --------------------------------------------------------------------------

(defun c:ESTRIBO ( / *error* doc dcl id act)
  (defun *error* (m)
    (if id (unload_dialog id))
    (if (and dcl (findfile dcl)) (vl-file-delete dcl))
    (if doc (vla-EndUndoMark doc))
    (if (not (wcmatch (strcase m) "*CANCEL*,*QUIT*,*EXIT*"))
      (princ (strcat "\nErro: " m)))
    (princ))
  (est:load-cfg)
  (setq *est:src* 'GEN *est:secpoly* nil *est:despoly* nil *est:distpts* nil)
  (setq dcl (est:write-dcl) id (load_dialog dcl) act 2)
  (if (< id 0) (progn (alert "Nao foi possivel carregar a janela (DCL).") (exit)))
  (while (> act 1)
    (if (not (new_dialog "estribo" id)) (exit))
    (est:dlg-init)
    (setq act (start_dialog))
    (cond
      ((= act 2) (est:pick-section))
      ((= act 3) (est:pick-rect))
      ((= act 4) (est:pick-trecho))))
  (unload_dialog id)
  (setq id nil)
  (vl-file-delete dcl)
  (if (= act 1)
    (progn
      (setq doc (vla-get-ActiveDocument (vlax-get-acad-object)))
      (vla-StartUndoMark doc)
      (est:save-cfg)
      (est:run)
      (vla-EndUndoMark doc)
      (setq doc nil)))
  (princ))

(defun c:EST () (c:ESTRIBO))

(defun c:ENCONTRO ( / *error* doc dcl id act)
  (defun *error* (m)
    (if id (unload_dialog id))
    (if (and dcl (findfile dcl)) (vl-file-delete dcl))
    (if doc (vla-EndUndoMark doc))
    (if (not (wcmatch (strcase m) "*CANCEL*,*QUIT*,*EXIT*"))
      (princ (strcat "\nErro: " m)))
    (princ))
  (est:load-cfg)
  (setq *enc:src* 'GEN *enc:pick* nil *enc:distpts* nil)
  (setq dcl (est:write-dcl) id (load_dialog dcl) act 2)
  (if (< id 0) (progn (alert "Nao foi possivel carregar a janela (DCL).") (exit)))
  (while (> act 1)
    (if (not (new_dialog "encontro" id)) (exit))
    (enc:dlg-init)
    (setq act (start_dialog))
    (cond
      ((= act 2) (enc:pick))
      ((= act 4) (enc:pick-trecho))))
  (unload_dialog id)
  (setq id nil)
  (vl-file-delete dcl)
  (if (= act 1)
    (progn
      (setq doc (vla-get-ActiveDocument (vlax-get-acad-object)))
      (vla-StartUndoMark doc)
      (est:save-cfg)
      (enc:run)
      (vla-EndUndoMark doc)
      (setq doc nil)))
  (princ))

(princ "\nESTRIBO.LSP carregado. Comandos: ESTRIBO (ou EST) e ENCONTRO.")
(princ)
