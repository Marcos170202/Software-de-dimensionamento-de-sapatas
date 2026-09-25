;;; ==========================================================================
;;; ESTRIBO.LSP - Detalhamento automatico de estribos (AutoCAD / AutoLISP)
;;; --------------------------------------------------------------------------
;;; Comandos:
;;;   ESTRIBO  (ou EST)  -> abre a janela de detalhamento
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
;;;   EST_Cota     -> cotas do detalhe e linha de distribuicao
;;;   EST_ArmTexto -> identificacao (N.16 6 %%c 5.0 c/17 C=125)
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
        '("ddist" . "0") '("cotadim" . "0")))

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
  (entmakex (list '(0 . "TEXT") (cons 8 lay) (cons 7 (getvar "TEXTSTYLE"))
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
(defun est:dimtext (p1 p2 v th / nr mid str o)
  (setq nr (est:rnorm p1 p2) mid (est:mid p1 p2) str (est:fmt v))
  (if (= (est:g "cotadim") "1")
    (progn
      (setq o (vla-AddDimAligned (est:ms) (vlax-3d-point (est:3d p1)) (vlax-3d-point (est:3d p2))
                                 (vlax-3d-point (est:3d (est:add mid (est:mul nr (* 1.5 th)))))))
      (vla-put-Layer o "EST_Cota")
      (vla-put-TextOverride o str))
    (est:text (est:add mid (est:mul nr (* 0.9 th))) str th (est:readang (angle p1 p2)) "EST_Cota")))

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

;;; Linha de distribuicao: "6 N.16 %%c 5.0 c/17" em cima e "(111)" embaixo
(defun est:draw-dist (p1 p2 th / a tmp dir up w mid tk)
  (setq a (angle p1 p2))
  (if (/= (est:readang a) a) (setq tmp p1 p1 p2 p2 tmp a (angle p1 p2)))
  (setq dir (est:unit (est:sub p2 p1)) up (list (- (cadr dir)) (car dir))
        w (est:unit (est:add dir up)) mid (est:mid p1 p2) tk (* 0.5 th))
  (est:line p1 p2 "EST_Cota")
  (foreach pt (list p1 p2)
    (est:line (est:sub pt (est:mul w tk)) (est:add pt (est:mul w tk)) "EST_Cota")
    (est:line (est:sub pt (est:mul up th)) (est:add pt (est:mul up th)) "EST_Cota"))
  (est:text (est:add mid (est:mul up (* 0.9 th))) (est:lbl-dist) th a "EST_ArmTexto")
  (est:text (est:sub mid (est:mul up (* 0.9 th)))
            (strcat "(" (est:fmt (/ (distance p1 p2) (est:uf))) ")") th a "EST_ArmTexto"))

;;; --------------------------------------------------------------------------
;;; Execucao apos o OK
;;; --------------------------------------------------------------------------

(defun est:run ( / P C th ip def bb p1 p2 l)
  (foreach l *est:layers* (est:layer (car l) (cadr l)))
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
      (if (not *est:distpts*)
        (if (and (setq p1 (getpoint "\nInicio do trecho de distribuicao <Enter pula>: "))
                 (setq p2 (getpoint p1 "\nFim do trecho: ")))
          (progn
            (setq *est:distpts* (list (est:2d (trans p1 1 0)) (est:2d (trans p2 1 0))))
            (if (<= (est:n "trecho") 0)
              (progn
                (est:s "trecho" (est:fmt (/ (apply 'distance *est:distpts*) (est:uf))))
                (est:auto-qtd))))))
      (if *est:distpts*
        (est:draw-dist (car *est:distpts*) (cadr *est:distpts*) th))))
  (princ (strcat "\n" (est:lbl-det C) "  ->  estribo " (est:g "b") " x " (est:g "h") " cm")))

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

(princ "\nESTRIBO.LSP carregado. Digite ESTRIBO (ou EST) para detalhar estribos.")
(princ)
