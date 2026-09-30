;;; ==========================================================================
;;;  ESCADA.lsp
;;;  FORMAS DE ESCADAS DE CONCRETO ARMADO  --  v1.0
;;;
;;;  Desenvolvido por Baluarte Solucoes Estruturais
;;;  Eng. Matusalem do Carmo de Oliveira
;;;  baluarteengenharia@outlook.com  /  matusa00@gmail.com
;;;
;;;  AVISO: esta rotina e uma FERRAMENTA DE APOIO. A conferencia do
;;;  resultado e a responsabilidade tecnica pelo projeto sao inteiramente
;;;  do engenheiro responsavel. Confira SEMPRE as dimensoes, niveis e
;;;  apoios antes de emitir o desenho. Os autores nao se responsabilizam
;;;  por erros, omissoes ou prejuizos decorrentes do uso.
;;;
;;;  Comandos:
;;;    ESCADA ........ cria uma escada nova (janela de modelagem)
;;;    ESCADACORTE ... le um CORTE ja desenhado (polilinha ou linhas do perfil
;;;                    dos degraus / contorno do corte), reconhece lances,
;;;                    patamares, espelhos, pisos e espessuras e abre a janela
;;;                    ja preenchida
;;;    ESCADAEDIT .... clique em qualquer desenho de uma escada: a janela abre
;;;                    com todos os dados e os desenhos sao refeitos no lugar
;;;                    (mesmo que tenham sido movidos)
;;;
;;;  --------------------------------------------------------------------
;;;  MODELO DA ESCADA
;;;  --------------------------------------------------------------------
;;;  A escada e uma sequencia de TRECHOS, de baixo para cima:
;;;   - LANCE ...... N espelhos de altura e, piso p, espessura h (medida
;;;                  perpendicular a laje inclinada).  "Pisos no lance":
;;;                  N-1 (padrao: o ultimo degrau chega no patamar / piso)
;;;                  ou N (o ultimo piso pertence ao lance).
;;;                  Comprimento horizontal = pisos x p;  desnivel = N x e.
;;;   - PATAMAR .... comprimento (na direcao da subida), espessura, desnivel
;;;                  no inicio (degrau no patamar, 0 = sem) e GIRO da escada
;;;                  no patamar: reto, 90 esquerda/direita, 180 (escada em U)
;;;                  esquerda/direita.
;;;  Exemplos: lance / patamar / lance / patamar / lance (predio, 3 lances
;;;  em U), lance / patamar 180 / lance (U), lance unico, etc.  O "Modelo
;;;  rapido" da janela gera os trechos e os apoios a partir do desnivel piso
;;;  a piso e do numero de espelhos; depois ajuste o que quiser.
;;;
;;;  APOIOS: quantos quiser, cada um com NOME (V1, V5, L3...), tipo (viga,
;;;  laje de piso ou parede), dimensoes e posicao: inicio ou fim de um
;;;  trecho + deslocamento do eixo.  Apoios intermediarios: escolha o
;;;  inicio/fim do patamar ou do lance desejado.  APOIOS LATERAIS dos lances
;;;  (viga ou parede, a esquerda e/ou a direita) aparecem na planta e no
;;;  corte transversal.
;;;
;;;  DESENHOS (cada um e um BLOCO: mova a vontade; ESCADAEDIT refaz no lugar)
;;;   - PLANTA DE FORMAS: lances com os degraus, linha de subida (SOBE),
;;;     patamares com nome, espessura e nivel, apoios (tracejados) com nome,
;;;     cotas e a indicacao do corte A-A.
;;;   - CORTE LONGITUDINAL (desenvolvido): perfil dos degraus, laje inclinada,
;;;     patamares, apoios com nome e secao, espessuras, niveis e cotas
;;;     (pisos "8x28=224" e espelhos "9x17,5=158").
;;;   - CORTE TRANSVERSAL A-A de um lance: laje, degrau visto, apoios
;;;     laterais e cotas.
;;;  Obs.: numa escada com giro, o corte longitudinal e DESENVOLVIDO (os
;;;  trechos em sequencia, como se a escada fosse reta).
;;;
;;;  UNIDADES: padrao "cm de papel" na escala 1:50 (igual a ARMVAR / TQS);
;;;  tambem metros, centimetros ou milimetros reais.  Todas as medidas da
;;;  janela sao em cm (niveis em m).
;;;
;;;  Compatibilidade: AutoCAD e ZWCAD (AutoLISP + DCL).  Texto ASCII.
;;;
;;;  LAYERS (criadas se nao existirem; mude os nomes abaixo se quiser)
;;;    EST_FormaCorte ... arestas cortadas (concreto no corte)
;;;    EST_FormaVista ... arestas vistas (degraus, contorno em planta)
;;;    EST_FormaOculta .. arestas ocultas (vigas sob a laje), tracejada
;;;    EST_FormaTexto ... nomes, espessuras
;;;    EST_FormaEixo .... linha de subida (SOBE) e indicacao de corte
;;;    EST_Nivel ........ niveis
;;;    EST_Cota ......... cotas (DIMENSION, texto branco)
;;;    EST_Titulo ....... titulos dos desenhos
;;; ==========================================================================

(vl-load-com)

(setq ES:VERSAO    "1.0"
      ES:LAY-CORTE "EST_FormaCorte"
      ES:LAY-VISTA "EST_FormaVista"
      ES:LAY-OCULTA "EST_FormaOculta"
      ES:LAY-TXT   "EST_FormaTexto"
      ES:LAY-EIXO  "EST_FormaEixo"
      ES:LAY-NIV   "EST_Nivel"
      ES:LAY-COTA  "EST_Cota"
      ES:LAY-TIT   "EST_Titulo"
      ES:STY       "TQS_ARIAL"
      ES:LT        "ES_TRACEJADO"
      ES:APP       "ESCADA"
      ES:DIC-NOME       "ESCADA_DADOS"
      ES:COR-TXT-COTA 7)

(setq ES:LST-UNI '("cm de papel (padrao TQS)" "metros reais"
                    "centimetros reais" "milimetros reais")
      ES:DIRS     '("Direita (+X)" "Cima (+Y)" "Esquerda (-X)" "Baixo (-Y)")
      ES:GIROS    '("Reto (sem giro)" "90 graus a esquerda" "90 graus a direita"
                    "180 graus a esquerda (U)" "180 graus a direita (U)")
      ES:GIROS-C  '("reto" "90 esq." "90 dir." "180 esq." "180 dir.")
      ES:TIPOS-APO '("Viga" "Laje de piso" "Parede")
      ES:TIPOS-LAT '("Nenhum" "Viga lateral" "Parede lateral")
      ES:NPIS     '("N-1  (o ultimo degrau chega no patamar / piso)"
                    "N  (o ultimo piso pertence ao lance)")
      ES:MODELOS  '("Reta - 1 lance"
                    "Reta - lance / patamar / lance"
                    "Em L - lance / patamar 90 / lance"
                    "Em U - lance / patamar 180 / lance"
                    "Em U - 3 lances (lance/patamar/lance/patamar/lance)"
                    "Reta - 3 lances e 2 patamares")
      ;; parametros gerais guardados em cada escada (ordem fixa)
      ES:PARAMS   '(ES:NOME ES:NIV ES:LAR ES:POCO ES:DIR ES:UNI ES:ESC ES:ALT
                    ES:DPLA ES:DLON ES:DTRA ES:TRAL ES:LATE ES:LATD
                    ES:MTIPO ES:MDES ES:MNDG ES:MPIS ES:MHL ES:MHP ES:MLP))

;;; ==========================================================================
;;;  1.  UTILITARIOS
;;; ==========================================================================

;;; texto -> real (aceita virgula); nil se invalido
(defun es:num (s / i)
  (cond
    ((numberp s) (float s))
    ((or (null s) (/= (type s) 'STR)) nil)
    (t
     (setq i (vl-string-position 44 s))
     (if i (setq s (strcat (substr s 1 i) "." (substr s (+ i 2)))))
     (setq s (vl-string-trim " " s))
     (if (and (/= s "") (numberp (distof s 2))) (distof s 2) nil))
  )
)

;;; numero de um campo (0.0 se invalido)
(defun es:n (s / v) (if (setq v (es:num s)) v 0.0))

(defun es:int (v) (if (< v 0.0) (- (fix (+ (- v) 0.5))) (fix (+ v 0.5))))

;;; nth que aceita lista vazia ou curta (o ZWCAD da erro em (nth 0 nil))
(defun es:nth (n l)
  (if (and l (listp l) (>= n 0) (< n (length l))) (nth n l))
)

(defun es:setnth (l n v / r i)
  (setq r nil i 0)
  (foreach x l (setq r (cons (if (= i n) v x) r) i (1+ i)))
  (reverse r)
)

(defun es:remove-nth (l n / r i)
  (setq r nil i 0)
  (foreach x l (if (/= i n) (setq r (cons x r))) (setq i (1+ i)))
  (reverse r)
)

(defun es:insere-nth (l n v / r i)
  (setq r nil i 0)
  (foreach x l
    (if (= i n) (setq r (cons v r)))
    (setq r (cons x r) i (1+ i)))
  (if (>= n (length l)) (setq r (cons v r)))
  (reverse r)
)

(defun es:troca (l a b / va vb)
  (setq va (nth a l) vb (nth b l))
  (es:setnth (es:setnth l a vb) b va)
)

(defun es:ultimo (l) (car (reverse l)))

;;; "." -> ","
(defun es:virg (s / i)
  (while (setq i (vl-string-position 46 s))
    (setq s (strcat (substr s 1 i) "," (substr s (+ i 2)))))
  s
)

;;; numero com ate 1 casa, virgula decimal: 17.5 -> "17,5"  224.0 -> "224"
(defun es:f (v / d sg)
  (setq sg (if (< v -0.00001) "-" "")
        d  (es:int (* (abs v) 10.0)))
  (if (= (rem d 10) 0)
    (strcat sg (itoa (/ d 10)))
    (strcat sg (itoa (/ d 10)) "," (itoa (rem d 10))))
)

;;; nivel em metros: 1.75 -> "+1,75"
(defun es:nivtxt (m / c r)
  (setq c (es:int (* (abs m) 100.0)) r (rem c 100))
  (strcat (if (< m -0.00001) "-" "+") (itoa (/ c 100)) ","
          (if (< r 10) "0" "") (itoa r))
)

(defun es:p2 (p) (list (car p) (cadr p)))
(defun es:add (a b) (list (+ (car a) (car b)) (+ (cadr a) (cadr b))))
(defun es:sub (a b) (list (- (car a) (car b)) (- (cadr a) (cadr b))))
(defun es:mul (a k) (list (* (car a) k) (* (cadr a) k)))
(defun es:dist (a b) (distance (es:p2 a) (es:p2 b)))
(defun es:vet (ang) (list (cos ang) (sin ang)))
(defun es:nrm (ang) (list (- (sin ang)) (cos ang)))
;;; ponto de um referencial: origem p, direcao ang, u ao longo, v a esquerda
(defun es:uv (p ang u v)
  (es:add p (es:add (es:mul (es:vet ang) u) (es:mul (es:nrm ang) v)))
)

;;; angulo de leitura (texto nunca de cabeca para baixo)
(defun es:leitura (a / d)
  (setq d (* a (/ 180.0 pi)))
  (while (< d 0.0) (setq d (+ d 360.0)))
  (while (>= d 360.0) (setq d (- d 360.0)))
  (if (and (> d 90.0001) (<= d 270.0001)) (setq d (- d 180.0)))
  (* d (/ pi 180.0))
)

;;; ---- mensagens ------------------------------------------------------------
(defun es:aviso (msg) (princ (strcat "\nESCADA aviso: " msg)))

;;; chama f com args; se der erro, MOSTRA o erro e devolve nil
(defun es:roda (f args rotulo / r)
  (setq ES:ETAPA nil r (vl-catch-all-apply f args))
  (if (vl-catch-all-error-p r)
    (progn
      (princ (strcat "\n*** ESCADA erro (" rotulo "): " (vl-catch-all-error-message r)
                     (if ES:ETAPA (strcat "  [etapa: " ES:ETAPA "]") "")))
      nil)
    r)
)

;;; ==========================================================================
;;;  2.  CRIACAO DE ENTIDADES
;;;  Todos os desenhos sao calculados em CM REAIS num referencial local; ES:O
;;;  e a origem (unidades do desenho) e ES:UC quantos cm reais cabem numa
;;;  unidade do desenho.  ES:H = altura do texto (unid. do desenho) e
;;;  ES:HC = a mesma altura em cm reais (para os afastamentos).
;;; ==========================================================================

(defun es:layer-liberar (nome / e ed flg cor)
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

(defun es:layer (nome cor lw / base)
  (if (not (tblsearch "LAYER" nome))
    (progn
      (setq base (list '(0 . "LAYER")
                       '(100 . "AcDbSymbolTableRecord")
                       '(100 . "AcDbLayerTableRecord")
                       (cons 2 nome) '(70 . 0) (cons 62 cor) '(6 . "Continuous")))
      (if (not (and lw (entmake (append base (list (cons 370 lw))))))
        (entmake base))
    )
    (es:layer-liberar nome)
  )
)

(defun es:prepara ()
  (es:layer ES:LAY-CORTE  4 35)
  (es:layer ES:LAY-VISTA  2 18)
  (es:layer ES:LAY-OCULTA 8 13)
  (es:layer ES:LAY-TXT    7 nil)
  (es:layer ES:LAY-EIXO   1 13)
  (es:layer ES:LAY-NIV    7 nil)
  (es:layer ES:LAY-COTA   8 13)
  (es:layer ES:LAY-TIT    7 30)
  (if (not (tblsearch "LTYPE" ES:LT))
    (entmake
      (list '(0 . "LTYPE") '(100 . "AcDbSymbolTableRecord")
            '(100 . "AcDbLinetypeTableRecord") (cons 2 ES:LT) '(70 . 0)
            '(3 . "Tracejado ESCADA __ __ __") '(72 . 65) '(73 . 2) '(40 . 1.5)
            '(49 . 1.0) '(74 . 0) '(49 . -0.5) '(74 . 0))))
  (regapp ES:APP)
  (if (not (tblsearch "STYLE" ES:STY))
    (entmake
      (list '(0 . "STYLE") '(100 . "AcDbSymbolTableRecord")
            '(100 . "AcDbTextStyleTableRecord") (cons 2 ES:STY)
            '(70 . 0) '(40 . 0.0) '(41 . 1.0) '(50 . 0.0) '(71 . 0) '(42 . 0.2)
            '(3 . "arial.ttf") '(4 . ""))))
)

;;; XDATA: ("ESCADA" (1000 . id) (1000 . etiqueta) (1000 . desenho))
(defun es:xd-lista (id tag grp)
  (list -3 (list ES:APP (cons 1000 id) (cons 1000 tag) (cons 1000 grp)))
)
(defun es:xd ()
  (if ES:ID (list (es:xd-lista ES:ID (if ES:TAG ES:TAG "") (if ES:GRP ES:GRP ""))))
)
(defun es:xd-ent (e)
  (if (and e ES:ID) (entmod (append (entget e) (es:xd))))
)

;;; ponto local (cm) -> desenho; acumula a caixa envolvente local
(defun es:bb (p)
  (if ES:CAIXA
    (setq ES:CAIXA (list (min (car ES:CAIXA) (car p)) (min (cadr ES:CAIXA) (cadr p))
                      (max (caddr ES:CAIXA) (car p)) (max (cadddr ES:CAIXA) (cadr p))))
    (setq ES:CAIXA (list (car p) (cadr p) (car p) (cadr p))))
)
(defun es:w (p)
  (es:bb p)
  (list (+ (car ES:O) (/ (car p) ES:UC)) (+ (cadr ES:O) (/ (cadr p) ES:UC)) 0.0)
)

(defun es:line (a b lay)
  (if (> (es:dist a b) 1e-6)
    (entmake (append (list '(0 . "LINE") '(100 . "AcDbEntity") (cons 8 lay)
                           '(100 . "AcDbLine") (cons 10 (es:w a)) (cons 11 (es:w b)))
                     (es:xd))))
)

;;; polilinha; lt = tipo de linha (nil = PorLayer); wid = largura
(defun es:pl (pts lay closed lt wid / ok)
  (setq ok (and lt (tblsearch "LTYPE" lt)))
  (entmake (append
             (list '(0 . "LWPOLYLINE") '(100 . "AcDbEntity") (cons 8 lay))
             (if ok (list (cons 6 lt) (cons 48 (* 0.6 ES:H))))
             (list '(100 . "AcDbPolyline") (cons 90 (length pts))
                   (cons 70 (+ (if closed 1 0) (if ok 128 0))))
             (if wid (list (cons 43 (/ wid ES:UC))))
             (mapcar '(lambda (p) (cons 10 (es:p2 (es:w p)))) pts)
             (es:xd)))
)

;;; retangulo local
(defun es:ret (x1 y1 x2 y2 lay lt)
  (es:pl (list (list x1 y1) (list x2 y1) (list x2 y2) (list x1 y2)) lay T lt nil)
)

;;; texto: k = fator da altura; al 0 esq / 1 centro / 2 dir; va 0 base / 2 meio
(defun es:txt (s p k ang lay al va / q)
  (setq q (es:w p))
  (entmake (append
             (list '(0 . "TEXT") (cons 8 lay) (cons 10 q) (cons 40 (* k ES:H)) (cons 1 s)
                   (cons 50 ang) '(41 . 1.0) (cons 7 ES:STY))
             (if (or (/= al 0) (/= va 0)) (list (cons 72 al) (cons 11 q) (cons 73 va)))
             (es:xd)))
  ;; a caixa envolvente considera o tamanho aproximado do texto
  (es:bb (es:add p (es:mul (es:vet ang) (* (if (= al 0) 1.0 (if (= al 1) 0.5 -0.1))
                                            (strlen s) 0.8 k ES:HC))))
  (es:bb (es:add p (es:mul (es:vet ang) (* (if (= al 2) -1.0 (if (= al 1) -0.5 0.1))
                                            (strlen s) 0.8 k ES:HC))))
)

(defun es:circ (c r lay)
  (entmake (append (list '(0 . "CIRCLE") (cons 8 lay) (cons 10 (es:w c)) (cons 40 (/ r ES:UC)))
                   (es:xd)))
)

;;; seta cheia com a ponta em q, vindo de p (comprimento c, largura w, em cm)
(defun es:seta (p q c w lay / a b)
  (setq a (angle (es:p2 p) (es:p2 q))
        b (es:add q (es:mul (es:vet a) (- c))))
  (entmake (append
             (list '(0 . "LWPOLYLINE") '(100 . "AcDbEntity") (cons 8 lay)
                   '(100 . "AcDbPolyline") '(90 . 2) '(70 . 0)
                   (cons 10 (es:p2 (es:w b))) (cons 40 (/ w ES:UC)) '(41 . 0.0)
                   (cons 10 (es:p2 (es:w q))) '(40 . 0.0) '(41 . 0.0))
             (es:xd)))
)

;;; linha de interrupcao (zigue-zague) de p a q
(defun es:quebra (p q lay / l a u n m c)
  (setq l (es:dist p q))
  (if (> l 1e-6)
    (progn
      (setq a (angle (es:p2 p) (es:p2 q)) u (es:vet a) n (es:nrm a)
            m (es:mul (es:add p q) 0.5)
            c (min (* 0.15 l) (* 0.8 ES:HC)))
      (es:pl (list (es:add p (es:mul u (* -0.4 c)))
                   (es:add m (es:mul u (- c)))
                   (es:add (es:add m (es:mul u (* -0.35 c))) (es:mul n (* 1.2 c)))
                   (es:add (es:add m (es:mul u (* 0.35 c))) (es:mul n (* -1.2 c)))
                   (es:add m (es:mul u c))
                   (es:add q (es:mul u (* 0.4 c))))
             lay nil nil nil)))
)

;;; simbolo de nivel: triangulo com a ponta em p e o texto em cima
(defun es:nivel (p txt / c)
  (setq c ES:HC)
  (es:pl (list p (es:add p (list (* -0.45 c) (* 0.8 c))) (es:add p (list (* 0.45 c) (* 0.8 c))))
         ES:LAY-NIV T nil nil)
  (es:line (es:add p (list (* -1.2 c) 0.0)) (es:add p (list (* 1.2 c) 0.0)) ES:LAY-NIV)
  (es:txt txt (es:add p (list 0.0 (* 1.2 c))) 1.0 0.0 ES:LAY-NIV 1 0)
)

;;; titulo sublinhado centrado em (x, y) com a escala embaixo
(defun es:titulo (txt sub x y / c l)
  (setq c ES:HC l (* (strlen txt) 0.95 1.4 c))
  (es:txt txt (list x y) 1.4 0.0 ES:LAY-TIT 1 0)
  (es:line (list (- x (* 0.5 l)) (- y (* 0.45 c))) (list (+ x (* 0.5 l)) (- y (* 0.45 c))) ES:LAY-TIT)
  (if sub (es:txt sub (list x (- y (* 1.9 c))) 0.9 0.0 ES:LAY-TIT 1 0))
)

;;; ---- cotas -----------------------------------------------------------------
;;; cota linear REAL (DIMENSION rotacionada), layer EST_Cota, tiques, texto
;;; "txt" no lugar do valor.  Pontos em cm locais.  Sem ActiveX: desenha a mao.
(defun es:dim (p1 p2 ploc ang txt / spc d)
  (setq spc (vl-catch-all-apply
              '(lambda ()
                 (vla-get-Block (vla-get-ActiveLayout
                                  (vla-get-ActiveDocument (vlax-get-acad-object)))))
              nil))
  (if (not (vl-catch-all-error-p spc))
    (setq d (vl-catch-all-apply 'vla-AddDimRotated
              (list spc (vlax-3d-point (es:w p1)) (vlax-3d-point (es:w p2))
                    (vlax-3d-point (es:w ploc)) ang))))
  (if (or (null d) (vl-catch-all-error-p d))
    (es:dim-manual p1 p2 ploc ang txt)
    (progn
      (foreach pr (list (list 'vla-put-Layer ES:LAY-COTA)
                        (list 'vla-put-ScaleFactor 1.0)
                        (list 'vla-put-TextStyle ES:STY)
                        (list 'vla-put-TextHeight (* 0.9 ES:H))
                        (list 'vla-put-TextGap (* 0.3 ES:H))
                        (list 'vla-put-Arrowhead1Type 4)
                        (list 'vla-put-Arrowhead2Type 4)
                        (list 'vla-put-ArrowheadSize (* 0.6 ES:H))
                        (list 'vla-put-DimensionLineExtend (* 0.75 ES:H))
                        (list 'vla-put-ExtensionLineExtend (* 0.75 ES:H))
                        (list 'vla-put-ExtensionLineOffset (* 0.4 ES:H))
                        (list 'vla-put-VerticalTextPosition 1)
                        (list 'vla-put-DimensionLineColor 256)
                        (list 'vla-put-ExtensionLineColor 256)
                        (list 'vla-put-TextColor ES:COR-TXT-COTA)
                        (list 'vla-put-TextOverride txt))
        (vl-catch-all-apply (car pr) (list d (cadr pr)))
      )
      (vl-catch-all-apply 'es:xd-ent (list (vlax-vla-object->ename d)))
      d
    )
  )
)

;;; projecao de p na linha de cota (que passa por ploc com angulo ang)
(defun es:proj (p ploc ang / u tt)
  (setq u (es:vet ang)
        tt (+ (* (- (car p) (car ploc)) (car u)) (* (- (cadr p) (cadr ploc)) (cadr u))))
  (es:add ploc (es:mul u tt))
)

(defun es:tique (p ang / a v)
  (setq a (+ ang (/ pi 4.0)) v (es:vet a))
  (es:pl (list (es:add p (es:mul v (* -0.5 ES:HC))) (es:add p (es:mul v (* 0.5 ES:HC))))
         ES:LAY-COTA nil nil nil (* 0.1 ES:HC))
)

(defun es:dim-manual (p1 p2 ploc ang txt / q1 q2 u n rot m)
  (setq q1 (es:proj p1 ploc ang) q2 (es:proj p2 ploc ang) u (es:vet ang))
  (es:line (es:add q1 (es:mul u (* -0.75 ES:HC))) (es:add q2 (es:mul u (* 0.75 ES:HC))) ES:LAY-COTA)
  (es:line p1 q1 ES:LAY-COTA)
  (es:line p2 q2 ES:LAY-COTA)
  (es:tique q1 ang)
  (es:tique q2 ang)
  (setq rot (es:leitura ang) n (es:nrm rot) m (es:mul (es:add q1 q2) 0.5))
  (es:txt txt (es:add m (es:mul n (* 0.3 ES:HC))) 0.9 rot ES:LAY-COTA 1 0)
  T
)

;;; cota horizontal entre x1 e x2; pontos em yref, linha em y
(defun es:dimh (x1 x2 yref y txt)
  (if (> (abs (- x2 x1)) 0.01)
    (es:dim (list x1 yref) (list x2 yref) (list (* 0.5 (+ x1 x2)) y) 0.0 txt))
)
;;; cota vertical entre y1 e y2; pontos em xref, linha em x
(defun es:dimv (y1 y2 xref x txt)
  (if (> (abs (- y2 y1)) 0.01)
    (es:dim (list xref y1) (list xref y2) (list x (* 0.5 (+ y1 y2))) (/ pi 2.0) txt))
)

;;; ==========================================================================
;;;  3.  MODELO E GEOMETRIA
;;;  Trechos (textos, como na janela):
;;;    ("LANCE"   nome N e p modo h)     modo "0" = N-1 pisos, "1" = N pisos
;;;    ("PATAMAR" nome L hp desnivel giro)   giro "0".."4" (ver ES:GIROS)
;;;  Apoios:
;;;    (nome tipo b h pos desl)  tipo "0" viga "1" laje "2" parede;
;;;    pos = 2 x (trecho - 1) + (0 inicio / 1 fim);  desl = cm (+ = sobe)
;;;  Laterais (ES:LATE / ES:LATD):  (tipo nome b h)
;;; ==========================================================================

(defun es:lance-p (tr) (= (car tr) "LANCE"))

;;; numeros de um lance: (N e p pisos h)
(defun es:lance-num (tr / n m)
  (setq n (max 1 (es:int (es:n (nth 2 tr))))
        m (if (or (= (nth 5 tr) "1") (= n 1)) n (1- n)))
  (list n (es:n (nth 3 tr)) (es:n (nth 4 tr)) m (es:n (nth 6 tr)))
)

;;; geometria dos trechos no corte DESENVOLVIDO (cm; s horizontal, y vertical;
;;; s = 0 e y = 0 no inicio do 1.o trecho, no nivel inicial).  Um registro:
;;;  0 tipo "L"/"P"  1 s0  2 s1  3 y0 (topo no inicio)  4 y1 (topo no fim)
;;;  5 a  6 b  (intradorso: y = a + b s)  7 pontos do topo (degraus)
;;;  8 espessura  9 nome  10 trecho  11 topo do patamar / fim do lance
;;;  12 N  13 e  14 p  15 pisos  16 desnivel  17 giro  18 comprimento
(defun es:geo (trs / s y r g n e p m h c pts k l d yt hp)
  (setq s 0.0 y 0.0 r nil)
  (foreach tr trs
    (if (es:lance-p tr)
      (progn
        (setq g (es:lance-num tr)
              n (nth 0 g) e (nth 1 g) p (nth 2 g) m (nth 3 g) h (nth 4 g))
        (if (<= p 0.0) (setq p 1.0))
        (setq c (/ p (sqrt (+ (* e e) (* p p))))
              l (* m p)
              pts (list (list s y)) k 1)
        (while (<= k n)
          (setq pts (cons (list (+ s (* (1- k) p)) (+ y (* k e))) pts))
          (if (or (< k n) (= m n))
            (setq pts (cons (list (+ s (* k p)) (+ y (* k e))) pts)))
          (setq k (1+ k))
        )
        (setq r (cons (list "L" s (+ s l) y (+ y (* n e))
                            (- y (* s (/ e p)) (/ h c)) (/ e p)
                            (reverse pts) h (nth 1 tr) tr (+ y (* n e))
                            n e p m 0.0 0 l)
                      r))
        (setq s (+ s l) y (+ y (* n e)))
      )
      (progn
        (setq l (es:n (nth 2 tr)) hp (es:n (nth 3 tr)) d (es:n (nth 4 tr))
              yt (+ y d))
        (setq pts (if (> (abs d) 0.001)
                    (list (list s y) (list s yt) (list (+ s l) yt))
                    (list (list s y) (list (+ s l) yt))))
        (setq r (cons (list "P" s (+ s l) y yt (- yt hp) 0.0 pts hp (nth 1 tr) tr yt
                            0 0.0 0.0 0 d (es:int (es:n (nth 5 tr))) l)
                      r))
        (setq s (+ s l) y yt)
      )
    )
  )
  (reverse r)
)

(defun es:s-ini (gs) (nth 1 (car gs)))
(defun es:s-fim (gs) (nth 2 (es:ultimo gs)))
(defun es:y-fim (gs) (nth 4 (es:ultimo gs)))

;;; perfil do topo (degraus e patamares) de todos os trechos, sem repetidos
(defun es:topo (gs / r)
  (setq r nil)
  (foreach g gs
    (foreach p (nth 7 g)
      (if (not (and r (equal p (car r) 1e-6))) (setq r (cons p r)))))
  (reverse r)
)

(defun es:yint (g s) (+ (nth 5 g) (* (nth 6 g) s)))

;;; intradorso (face inferior): lista de pontos do inicio ao fim.  As retas de
;;; trechos vizinhos se encontram no ponto de intersecao (a "quebra" da laje);
;;; se nao houver intersecao valida, liga com um trecho vertical na juncao.
(defun es:intradorso (gs / r g1 g2 sj sx)
  (setq r (list (list (es:s-ini gs) (es:yint (car gs) (es:s-ini gs)))))
  (setq g1 (car gs))
  (foreach g2 (cdr gs)
    (setq sj (nth 2 g1))
    (if (> (abs (- (nth 6 g1) (nth 6 g2))) 1e-9)
      (progn
        (setq sx (/ (- (nth 5 g2) (nth 5 g1)) (- (nth 6 g1) (nth 6 g2))))
        (if (and (>= sx (- (nth 1 g1) 1e-6)) (<= sx (+ (nth 2 g2) 1e-6))
                 (>= sx (- (car (car r)) 1e-6)))
          (setq r (cons (list sx (es:yint g1 sx)) r))
          (setq r (cons (list sj (es:yint g2 sj)) (cons (list sj (es:yint g1 sj)) r))))
      )
      (if (> (abs (- (nth 5 g1) (nth 5 g2))) 1e-6)
        (setq r (cons (list sj (es:yint g2 sj)) (cons (list sj (es:yint g1 sj)) r))))
    )
    (setq g1 g2)
  )
  (setq r (cons (list (es:s-fim gs) (es:yint g1 (es:s-fim gs))) r))
  (reverse r)
)

;;; y de uma cadeia de pontos (crescente em x) na abscissa x (nil se fora)
(defun es:y-cadeia (pts x / r a b)
  (setq a (car pts))
  (foreach b (cdr pts)
    (if (and (null r) (> (abs (- (car b) (car a))) 1e-9)
             (>= x (- (min (car a) (car b)) 1e-6)) (<= x (+ (max (car a) (car b)) 1e-6)))
      (setq r (+ (cadr a) (* (- (cadr b) (cadr a)) (/ (- x (car a)) (- (car b) (car a)))))))
    (setq a b)
  )
  r
)

;;; topo ESTRUTURAL na abscissa s: nivel do patamar, ou a linha dos cantos
;;; internos dos degraus no lance (face superior da laje inclinada)
(defun es:topo-est (gs s / r)
  (cond
    ((<= s (+ (es:s-ini gs) 1e-6)) (setq r (nth 3 (car gs))))
    ((>= s (- (es:s-fim gs) 1e-6)) (setq r (es:y-fim gs)))
    (t
     (foreach g gs
       (if (and (= (car g) "P") (>= s (- (nth 1 g) 1e-6)) (<= s (+ (nth 2 g) 1e-6)))
         (setq r (nth 11 g))))
     (if (null r)
       (foreach g gs
         (if (and (null r) (= (car g) "L") (>= s (nth 1 g)) (<= s (nth 2 g)))
           (setq r (+ (nth 3 g) (* (- s (nth 1 g)) (nth 6 g)))))))))
  (if r r 0.0)
)

;;; trecho (indice) e ponta (0 inicio / 1 fim) de um apoio
(defun es:apo-k (gs ap / j)
  (setq j (es:int (es:n (nth 4 ap))))
  (min (/ j 2) (1- (length gs)))
)
(defun es:apo-fim (ap) (= 1 (rem (es:int (es:n (nth 4 ap))) 2)))

;;; abscissa do eixo do apoio no corte desenvolvido
(defun es:apo-s (gs ap / g)
  (setq g (nth (es:apo-k gs ap) gs))
  (+ (if (es:apo-fim ap) (nth 2 g) (nth 1 g)) (es:n (nth 5 ap)))
)

;;; retangulo do apoio no corte: (x1 x2 yb yt tipo)
(defun es:apo-ret (gs ap / s b h tp yt x1 x2 dir)
  (setq s (es:apo-s gs ap) b (es:n (nth 2 ap)) h (es:n (nth 3 ap))
        tp (es:int (es:n (nth 1 ap))))
  (if (= tp 1)
    ;; laje de piso: sai para fora a partir da juncao
    (progn
      (setq dir (if (es:apo-fim ap) 1.0 -1.0)
            yt  (es:topo-est gs s)
            x1  (min s (+ s (* dir b))) x2 (max s (+ s (* dir b))))
      (list x1 x2 (- yt h) yt tp))
    (progn
      (setq yt (es:topo-est gs s))
      (list (- s (* 0.5 b)) (+ s (* 0.5 b)) (- yt h) yt tp)))
)

;;; parte de um segmento vertical (x, ya..yb) que NAO esta dentro dos
;;; retangulos (x1 x2 y1 y2 ...): lista de (y1 y2)
(defun es:recorta-v (x ya yb rets / segs novo lo hi)
  (setq segs (list (list (min ya yb) (max ya yb))))
  (foreach rt rets
    (if (and (>= x (- (nth 0 rt) 1e-6)) (<= x (+ (nth 1 rt) 1e-6)))
      (progn
        (setq lo (nth 2 rt) hi (nth 3 rt) novo nil)
        (foreach sg segs
          (if (> (car sg) (- lo 1e-6))
            (if (< (cadr sg) (+ hi 1e-6)) nil
              (if (< (car sg) hi) (setq novo (cons (list hi (cadr sg)) novo))
                (setq novo (cons sg novo))))
            (progn
              (setq novo (cons (list (car sg) (min (cadr sg) lo)) novo))
              (if (> (cadr sg) hi) (setq novo (cons (list hi (cadr sg)) novo))))))
        (setq segs (vl-remove-if '(lambda (q) (< (- (cadr q) (car q)) 1e-4)) novo))
      )
    )
  )
  segs
)

;;; resumo para mensagens: desnivel total, desenvolvimento, pior Blondel
(defun es:resumo (gs / tot bl v)
  (setq bl nil)
  (foreach g gs
    (if (= (car g) "L")
      (progn
        (setq v (+ (* 2.0 (nth 13 g)) (nth 14 g)))
        (if (or (null bl) (> (abs (- v 62.5)) (abs (- bl 62.5)))) (setq bl v)))))
  (list (es:y-fim gs) (es:s-fim gs) bl)
)

;;; ---- modelos prontos ---------------------------------------------------------
;;; gera ES:TRE e ES:APO a partir do "Modelo rapido"
(defun es:gera-modelo ( / tipo des nt p hl hp lp w nl ns giros e i k trs aps lps nv q)
  (setq tipo ES:MTIPO des (es:n ES:MDES) nt (max 1 (es:int (es:n ES:MNDG)))
        p (es:n ES:MPIS) hl ES:MHL hp ES:MHP lp (es:n ES:MLP) w (es:n ES:LAR))
  (setq nl    (nth tipo '(1 2 2 2 3 3))
        giros (nth tipo '(nil ("0") ("1") ("3") ("1" "1") ("0" "0"))))
  (if (< nt nl) (setq nt nl))
  (setq e (/ des nt) trs nil i 0)
  ;; espelhos por lance (o resto vai para os primeiros)
  (setq ns nil k 0)
  (repeat nl
    (setq ns (cons (+ (/ nt nl) (if (< k (rem nt nl)) 1 0)) ns) k (1+ k)))
  (setq ns (reverse ns))
  (setq k 0)
  (foreach n ns
    (setq trs (cons (list "LANCE" (strcat "LANCE " (itoa (1+ k))) (itoa n)
                          (es:f e) (es:f p) "0" hl)
                    trs))
    (if (< k (1- nl))
      (setq trs (cons (list "PATAMAR" (strcat "PATAMAR " (itoa (1+ k)))
                            (es:f (if (member (nth k giros) '("1" "2")) w lp))
                            hp "0" (nth k giros))
                      trs)))
    (setq k (1+ k))
  )
  (setq ES:TRE (reverse trs))
  ;; apoios: inicio, fim e (escada com giro) a borda de cada patamar
  (setq aps (list (list "V1" "0" "14" "40" "0" "0")) nv 2 i 0)
  (foreach tr ES:TRE
    (if (and (not (es:lance-p tr)) (/= (nth 5 tr) "0"))
      (setq aps (cons (list (strcat "V" (itoa nv)) "0" "14" "40" (itoa (1+ (* 2 i))) "0") aps)
            nv (1+ nv)))
    (setq i (1+ i)))
  (setq aps (cons (list (strcat "V" (itoa nv)) "0" "14" "40"
                        (itoa (1- (* 2 (length ES:TRE)))) "0")
                  aps))
  (setq ES:APO (reverse aps))
)

;;; ==========================================================================
;;;  4.  DESENHOS
;;; ==========================================================================

;;; textos das cotas: "8x28=224" (pisos) e "9x17,5=158" (espelhos)
(defun es:txt-pisos (g)
  (if (> (nth 15 g) 1)
    (strcat (itoa (nth 15 g)) "x" (es:f (nth 14 g)) "=" (es:f (- (nth 2 g) (nth 1 g))))
    (es:f (- (nth 2 g) (nth 1 g))))
)
(defun es:txt-esp (g)
  (if (> (nth 12 g) 1)
    (strcat (itoa (nth 12 g)) "x" (es:f (nth 13 g)) "=" (es:f (* (nth 12 g) (nth 13 g))))
    (es:f (nth 13 g)))
)
(defun es:nome-h (g) (strcat (nth 9 g) "  (h=" (es:f (nth 8 g)) ")"))
(defun es:nivel-m (y) (+ (es:n ES:NIV) (/ y 100.0)))

;;; texto de um apoio: "V1 (14x40)"
(defun es:apo-txt (ap / tp)
  (setq tp (es:int (es:n (nth 1 ap))))
  (cond
    ((= tp 1) (strcat (nth 0 ap) " (h=" (es:f (es:n (nth 3 ap))) ")"))
    ((= tp 2) (nth 0 ap))
    (t (strcat (nth 0 ap) " (" (es:f (es:n (nth 2 ap))) "x" (es:f (es:n (nth 3 ap))) ")")))
)

;;; ---------------------------------------------------------------------------
;;;  CORTE LONGITUDINAL (desenvolvido).  Origem = inicio do 1.o trecho, no
;;;  nivel inicial.
;;; ---------------------------------------------------------------------------
(defun es:des-lon (gs / c top sc s0 s1 y1 rets r x1 x2 yb yt tp ylim ymin ymax xmax
                        xd yd sm ys ang n bb g ap)
  (setq c ES:HC top (es:topo gs) sc (es:intradorso gs)
        s0 (es:s-ini gs) s1 (es:s-fim gs) y1 (es:y-fim gs))
  ;; apoios (retangulos) - usados tambem para recortar as faces das pontas
  (setq rets (mapcar '(lambda (ap) (es:apo-ret gs ap)) ES:APO))
  ;; ---- concreto: topo (degraus), intradorso e faces das pontas
  (es:pl top ES:LAY-CORTE nil nil nil)
  (es:pl sc ES:LAY-CORTE nil nil nil)
  (foreach sg (es:recorta-v s0 (cadr (car sc)) (cadr (car top)) rets)
    (es:line (list s0 (car sg)) (list s0 (cadr sg)) ES:LAY-CORTE))
  (foreach sg (es:recorta-v s1 (cadr (es:ultimo sc)) y1 rets)
    (es:line (list s1 (car sg)) (list s1 (cadr sg)) ES:LAY-CORTE))
  ;; ---- apoios
  (setq ymin (apply 'min (mapcar 'cadr sc)))
  (foreach ap ES:APO
    (setq r (es:apo-ret gs ap) x1 (nth 0 r) x2 (nth 1 r) yb (nth 2 r) yt (nth 3 r)
          tp (nth 4 r) ymin (min ymin yb))
    (setq ylim (list (if (and (>= x1 (- s0 1e-6)) (<= x1 (+ s1 1e-6))) (es:y-cadeia sc x1) yt)
                     (if (and (>= x2 (- s0 1e-6)) (<= x2 (+ s1 1e-6))) (es:y-cadeia sc x2) yt)))
    (cond
      ((= tp 1)
       ;; laje de piso: topo, fundo e interrupcao na ponta de fora
       (es:line (list x1 yt) (list x2 yt) ES:LAY-CORTE)
       (es:line (list x1 yb) (list x2 yb) ES:LAY-CORTE)
       (if (es:apo-fim ap)
         (es:quebra (list x2 (+ yt (* 0.3 c))) (list x2 (- yb (* 0.3 c))) ES:LAY-CORTE)
         (es:quebra (list x1 (+ yt (* 0.3 c))) (list x1 (- yb (* 0.3 c))) ES:LAY-CORTE))
       (es:txt (es:apo-txt ap) (list (* 0.5 (+ x1 x2)) (- yb (* 1.5 c))) 0.9 0.0 ES:LAY-TXT 1 0))
      (t
       ;; viga / parede: faces laterais ate a laje, fundo, topo fora da escada
       (if (> (car ylim) (+ yb 1e-6)) (es:line (list x1 yb) (list x1 (car ylim)) ES:LAY-CORTE))
       (if (> (cadr ylim) (+ yb 1e-6)) (es:line (list x2 yb) (list x2 (cadr ylim)) ES:LAY-CORTE))
       (if (< x1 s0) (es:line (list x1 yt) (list (min x2 s0) yt) ES:LAY-CORTE))
       (if (> x2 s1) (es:line (list (max x1 s1) yt) (list x2 yt) ES:LAY-CORTE))
       (if (= tp 2)
         (es:quebra (list (- x1 (* 0.3 c)) yb) (list (+ x2 (* 0.3 c)) yb) ES:LAY-CORTE)
         (es:line (list x1 yb) (list x2 yb) ES:LAY-CORTE))
       (es:txt (es:apo-txt ap) (list (* 0.5 (+ x1 x2)) (- yb (* 1.6 c))) 0.9 0.0 ES:LAY-TXT 1 0)))
  )
  ;; ---- nomes e espessuras (embaixo do intradorso de cada trecho)
  (foreach g gs
    (setq sm (* 0.5 (+ (nth 1 g) (nth 2 g))) ys (es:yint g sm)
          ang (atan (nth 6 g)) n (es:nrm ang))
    (es:txt (es:nome-h g) (es:add (list sm ys) (es:mul n (* -1.6 c))) 0.8 ang ES:LAY-TXT 1 0)
  )
  ;; ---- niveis
  (es:nivel (list (- s0 (* 3.0 c)) 0.0) (es:nivtxt (es:nivel-m 0.0)))
  (foreach g gs
    (if (= (car g) "P")
      (es:nivel (list (* 0.5 (+ (nth 1 g) (nth 2 g))) (nth 11 g))
                (es:nivtxt (es:nivel-m (nth 11 g))))))
  (es:nivel (list (+ s1 (* 3.0 c)) y1) (es:nivtxt (es:nivel-m y1)))
  ;; ---- cotas horizontais (embaixo) e verticais (a direita)
  (setq bb ES:CAIXA ymin (min ymin (cadr bb)) xmax (caddr bb) ymax (cadddr bb))
  (setq yd (- ymin (* 2.5 c)))
  (foreach g gs
    (es:dimh (nth 1 g) (nth 2 g) (- ymin (* 0.5 c)) yd
             (if (= (car g) "L") (es:txt-pisos g) (es:f (- (nth 2 g) (nth 1 g))))))
  (es:dimh s0 s1 (- ymin (* 0.5 c)) (- yd (* 2.5 c)) (es:f (- s1 s0)))
  (setq xd (+ xmax (* 2.0 c)))
  (foreach g gs
    (if (= (car g) "L")
      (es:dimv (nth 3 g) (nth 4 g) (+ xmax (* 0.5 c)) xd (es:txt-esp g))
      (if (> (abs (nth 16 g)) 0.001)
        (es:dimv (nth 3 g) (nth 11 g) (+ xmax (* 0.5 c)) xd (es:f (nth 16 g))))))
  (es:dimv 0.0 y1 (+ xmax (* 0.5 c)) (+ xd (* 2.5 c)) (es:f y1))
  ;; ---- titulo
  (setq bb ES:CAIXA)
  (es:titulo (strcat "CORTE LONGITUDINAL - " ES:NOME)
             (strcat "(DESENVOLVIDO)   ESC. 1:" ES:ESC)
             (* 0.5 (+ (car bb) (caddr bb))) (- (cadr bb) (* 3.0 c)))
)

;;; ---------------------------------------------------------------------------
;;;  PLANTA DE FORMAS.  Origem = inicio do 1.o trecho, no eixo da escada.
;;;  Cada trecho tem um referencial (P ang): u ao longo da subida, v a esquerda.
;;; ---------------------------------------------------------------------------

;;; referenciais: lista de (P ang comprimento vmin vmax)
(defun es:planta-refs (gs / w poco p ang r l gi vmin vmax)
  (setq w (es:n ES:LAR) poco (es:n ES:POCO)
        p '(0.0 0.0) ang (* ES:DIR (/ pi 2.0)) r nil)
  (foreach g gs
    (setq l (nth 18 g) gi (nth 17 g) vmin (* -0.5 w) vmax (* 0.5 w))
    (if (= (car g) "P")
      (cond ((= gi 3) (setq vmax (+ (* 1.5 w) poco)))
            ((= gi 4) (setq vmin (- (+ (* 1.5 w) poco))))))
    (setq r (cons (list p ang l vmin vmax) r))
    (if (= (car g) "L")
      (setq p (es:uv p ang l 0.0))
      (cond
        ((= gi 0) (setq p (es:uv p ang l 0.0)))
        ((= gi 1) (setq p (es:uv p ang (- l (* 0.5 w)) (* 0.5 w)) ang (+ ang (/ pi 2.0))))
        ((= gi 2) (setq p (es:uv p ang (- l (* 0.5 w)) (* -0.5 w)) ang (- ang (/ pi 2.0))))
        ((= gi 3) (setq p (es:uv p ang 0.0 (+ w poco)) ang (+ ang pi)))
        ((= gi 4) (setq p (es:uv p ang 0.0 (- (+ w poco))) ang (+ ang pi)))))
  )
  (reverse r)
)

;;; texto de 1 ou mais linhas centrado em c, na direcao ang (legivel)
(defun es:txt-bloco (linhas c ang k lay / rot up n i)
  (setq rot (es:leitura ang) up (es:nrm rot) n (length linhas) i 0)
  (foreach s linhas
    (es:txt s (es:add c (es:mul up (* (- (* 0.5 (1- n)) i) 1.5 k ES:HC))) k rot lay 1 2)
    (setq i (1+ i)))
)

(defun es:des-pla (gs / c refs rf p ang l vmin vmax k u x b nl uu tp
                        bx w bb kk uc vd)
  (setq c ES:HC refs (es:planta-refs gs) w (es:n ES:LAR) k 0 nl 0)
  (foreach g gs
    (setq rf (nth k refs) p (nth 0 rf) ang (nth 1 rf) l (nth 2 rf)
          vmin (nth 3 rf) vmax (nth 4 rf))
    ;; contorno do trecho
    (es:pl (list (es:uv p ang 0.0 vmin) (es:uv p ang l vmin)
                 (es:uv p ang l vmax) (es:uv p ang 0.0 vmax))
           ES:LAY-VISTA T nil nil)
    (if (= (car g) "L")
      (progn
        ;; degraus (linhas dos espelhos)
        (setq x 1)
        (while (< x (nth 12 g))
          (setq u (* x (nth 14 g)))
          (if (< u (- l 1e-6))
            (es:line (es:uv p ang u vmin) (es:uv p ang u vmax) ES:LAY-VISTA))
          (setq x (1+ x)))
        ;; linha de subida
        (setq uu (min (* 0.5 (nth 14 g)) (* 0.3 l)))
        (es:circ (es:uv p ang uu 0.0) (* 0.35 c) ES:LAY-EIXO)
        (es:line (es:uv p ang (+ uu (* 0.35 c)) 0.0) (es:uv p ang (- l (* 0.2 (nth 14 g))) 0.0)
                 ES:LAY-EIXO)
        (es:seta (es:uv p ang uu 0.0) (es:uv p ang (- l (* 0.2 (nth 14 g))) 0.0)
                 (* 1.2 c) (* 0.5 c) ES:LAY-EIXO)
        (es:txt-bloco (list "SOBE") (es:uv p ang (+ uu (* 1.2 c)) (* 0.8 c)) ang 0.8 ES:LAY-EIXO)
        ;; nome e espessura
        (es:txt-bloco (list (nth 9 g) (strcat "h=" (es:f (nth 8 g)))
                            (strcat (itoa (nth 12 g)) " degr. " (es:f (nth 13 g)) "x" (es:f (nth 14 g))))
                      (es:uv p ang (* 0.5 l) (* -0.25 w)) ang 0.8 ES:LAY-TXT)
        ;; apoios laterais
        (foreach lat (list (list ES:LATE 1.0) (list ES:LATD -1.0))
          (if (and (car lat) (> (es:int (es:n (car (car lat)))) 0))
            (progn
              (setq b (es:n (nth 2 (car lat))))
              (if (> (cadr lat) 0.0)
                (es:pl (list (es:uv p ang 0.0 vmax) (es:uv p ang l vmax)
                             (es:uv p ang l (+ vmax b)) (es:uv p ang 0.0 (+ vmax b)))
                       ES:LAY-OCULTA T ES:LT nil)
                (es:pl (list (es:uv p ang 0.0 vmin) (es:uv p ang l vmin)
                             (es:uv p ang l (- vmin b)) (es:uv p ang 0.0 (- vmin b)))
                       ES:LAY-OCULTA T ES:LT nil))
              ;; nome dentro da faixa do apoio lateral
              (es:txt-bloco (list (nth 1 (car lat)))
                            (es:uv p ang (* 0.25 l) (if (> (cadr lat) 0.0)
                                                        (+ vmax (* 0.5 b))
                                                        (- vmin (* 0.5 b))))
                            ang (min 0.7 (/ (* 0.8 b) ES:HC)) ES:LAY-TXT))))
        ;; indicacao do corte A-A
        (if (and (= nl (es:int (es:n ES:TRAL))) (= ES:DTRA "1"))
          (progn
            (setq uc (* (+ (fix (* 0.5 (nth 15 g))) 0.5) (nth 14 g)))
            (if (> uc l) (setq uc (* 0.5 l)))
            (foreach sd (list (list vmax 1.0) (list vmin -1.0))
              ;; lado direito: depois das cotas; lado esquerdo: junto a escada
              (setq bx (+ (car sd) (* (cadr sd) (+ (if (> (cadr sd) 0) (* 0.5 c) (* 3.6 c))
                                                   (if (> (cadr sd) 0) (es:lat-b ES:LATE) (es:lat-b ES:LATD))))))
              (es:pl (list (es:uv p ang uc bx) (es:uv p ang uc (+ bx (* (cadr sd) 1.5 c))))
                     ES:LAY-EIXO nil nil (* 0.25 c))
              (es:seta (es:uv p ang uc (+ bx (* (cadr sd) 1.5 c)))
                       (es:uv p ang (+ uc (* 1.4 c)) (+ bx (* (cadr sd) 1.5 c)))
                       (* 0.8 c) (* 0.4 c) ES:LAY-EIXO)
              (es:txt-bloco (list "A") (es:uv p ang (+ uc (* 2.4 c)) (+ bx (* (cadr sd) 1.5 c)))
                            ang 1.2 ES:LAY-EIXO))))
        (setq nl (1+ nl))
      )
      ;; patamar: nome, espessura e nivel
      (es:txt-bloco (list (nth 9 g) (strcat "h=" (es:f (nth 8 g)))
                          (es:nivtxt (es:nivel-m (nth 11 g))))
                    (es:uv p ang (* 0.5 l) (* 0.5 (+ vmin vmax))) ang 0.8 ES:LAY-TXT)
    )
    ;; cotas: comprimento (lado direito) e largura
    (setq vd (- vmin (* 2.2 c) (if (= (car g) "L") (es:lat-b ES:LATD) 0.0)))
    (es:dim (es:uv p ang 0.0 vmin) (es:uv p ang l vmin) (es:uv p ang (* 0.5 l) vd) ang
            (if (= (car g) "L") (es:txt-pisos g) (es:f l)))
    (if (or (= k 0) (= (car g) "P"))
      (progn
        (setq u (if (= k 0) (- (es:folga-ini gs c)) (+ l (* 3.8 c))))
        (es:dim (es:uv p ang (if (= k 0) 0.0 l) vmin) (es:uv p ang (if (= k 0) 0.0 l) vmax)
                (es:uv p ang u (* 0.5 (+ vmin vmax))) (+ ang (/ pi 2.0))
                (es:f (- vmax vmin)))))
    (setq k (1+ k))
  )
  ;; apoios (tracejados, sob a laje) com o nome do lado de fora
  (foreach ap ES:APO
    (setq kk (es:apo-k gs ap) rf (nth kk refs) p (nth 0 rf) ang (nth 1 rf)
          vmin (nth 3 rf) vmax (nth 4 rf) b (es:n (nth 2 ap))
          tp (es:int (es:n (nth 1 ap)))
          u (+ (if (es:apo-fim ap) (nth 2 rf) 0.0) (es:n (nth 5 ap))))
    (if (= tp 1)
      ;; laje de piso: so o nome, do lado de fora
      (es:txt-bloco (list (es:apo-txt ap))
                    (es:uv p ang (+ u (* (if (es:apo-fim ap) 1.0 -1.0) (max (* 2.0 c) (* 0.5 b)))) 0.0)
                    ang 0.8 ES:LAY-TXT)
      (progn
        (es:pl (list (es:uv p ang (- u (* 0.5 b)) vmin) (es:uv p ang (+ u (* 0.5 b)) vmin)
                     (es:uv p ang (+ u (* 0.5 b)) vmax) (es:uv p ang (- u (* 0.5 b)) vmax))
               ES:LAY-OCULTA T ES:LT nil)
        ;; nome ao longo da viga, do lado de fora do trecho
        (es:txt-bloco (list (es:apo-txt ap))
                      (es:uv p ang (+ u (* (if (es:apo-fim ap) 1.0 -1.0) (+ (* 0.5 b) (* 0.9 c))))
                             (* 0.5 (+ vmin vmax)))
                      (+ ang (/ pi 2.0)) 0.8 ES:LAY-TXT)))
  )
  (setq bb ES:CAIXA)
  (es:titulo (strcat "PLANTA DE FORMAS - " ES:NOME) (strcat "ESC. 1:" ES:ESC)
             (* 0.5 (+ (car bb) (caddr bb))) (- (cadr bb) (* 3.0 c)))
)

;;; afastamento da cota de largura antes do 1.o trecho (passa dos apoios do inicio)
(defun es:folga-ini (gs c / r)
  (setq r (* 2.2 c))
  (foreach ap ES:APO
    (if (and (= (es:apo-k gs ap) 0) (not (es:apo-fim ap)))
      (setq r (max r (+ (- (es:n (nth 5 ap)))
                        (if (= (es:int (es:n (nth 1 ap))) 1)
                          (+ (max (* 2.0 c) (* 0.5 (es:n (nth 2 ap)))) (* 4.0 c))
                          (+ (* 0.5 (es:n (nth 2 ap))) (* 3.5 c))))))))
  r
)

(defun es:lat-b (lat)
  (if (and lat (> (es:int (es:n (car lat))) 0)) (es:n (nth 2 lat)) 0.0)
)

;;; ---------------------------------------------------------------------------
;;;  CORTE TRANSVERSAL A-A de um lance (no meio de um piso).  Origem = centro
;;;  da face inferior da laje.
;;; ---------------------------------------------------------------------------
(defun es:lance-idx (gs i / r k)
  (setq k 0)
  (foreach g gs
    (if (= (car g) "L")
      (progn (if (= k i) (setq r g)) (setq k (1+ k)))))
  (if r r (car (vl-remove-if-not '(lambda (g) (= (car g) "L")) gs)))
)

(defun es:des-tra (gs / c g w m sc tp hh e rets x0 x1 tpl b h nm yb yt sd bb xr yd xx hv)
  (setq c ES:HC g (es:lance-idx gs (es:int (es:n ES:TRAL))) w (es:n ES:LAR))
  (if g
    (progn
      (setq m  (fix (* 0.5 (nth 15 g)))
            sc (+ (nth 1 g) (* (+ m 0.5) (nth 14 g)))
            tp (+ (nth 3 g) (* (1+ m) (nth 13 g)))
            hh (- tp (es:yint g sc))
            e  (nth 13 g)
            x0 (* -0.5 w) x1 (* 0.5 w) rets nil)
      ;; apoios laterais: retangulos
      (foreach lat (list (list ES:LATE -1.0) (list ES:LATD 1.0))
        (setq tpl (es:int (es:n (car (car lat)))) sd (cadr lat))
        (if (> tpl 0)
          (progn
            (setq b (es:n (nth 2 (car lat))) h (es:n (nth 3 (car lat))) nm (nth 1 (car lat)))
            (if (= tpl 1)
              (setq yt hh yb (- hh h))
              (setq yt (+ hh (* 2.5 c) e) yb (- (* 3.0 c))))
            (setq xr (if (< sd 0.0) (list (- x0 b) x0) (list x1 (+ x1 b))))
            (setq rets (cons (list (car xr) (cadr xr) yb yt) rets))
            ;; face externa, e interna fora da laje
            (es:line (list (if (< sd 0.0) (car xr) (cadr xr)) yb)
                     (list (if (< sd 0.0) (car xr) (cadr xr)) yt) ES:LAY-CORTE)
            (setq xx (if (< sd 0.0) (cadr xr) (car xr)))
            (foreach sg (es:recorta-v xx yb yt (list (list (- xx 0.001) (+ xx 0.001) 0.0 hh)))
              (es:line (list xx (car sg)) (list xx (cadr sg)) ES:LAY-CORTE))
            (if (= tpl 1)
              (progn
                (es:line (list (car xr) yb) (list (cadr xr) yb) ES:LAY-CORTE)
                (es:line (list (car xr) yt) (list (cadr xr) yt) ES:LAY-CORTE)
                (es:txt nm (list (* 0.5 (+ (car xr) (cadr xr))) (- yb (* 1.5 c))) 0.8 0.0 ES:LAY-TXT 1 0))
              (progn
                (es:quebra (list (- (car xr) (* 0.3 c)) yb) (list (+ (cadr xr) (* 0.3 c)) yb) ES:LAY-CORTE)
                (es:quebra (list (- (car xr) (* 0.3 c)) yt) (list (+ (cadr xr) (* 0.3 c)) yt) ES:LAY-CORTE)
                (es:txt nm (list (* 0.5 (+ (car xr) (cadr xr))) (- yb (* 2.0 c))) 0.8 0.0 ES:LAY-TXT 1 0)))
          )
        )
      )
      ;; laje cortada
      (es:line (list x0 0.0) (list x1 0.0) ES:LAY-CORTE)
      (es:line (list x0 hh) (list x1 hh) ES:LAY-CORTE)
      (foreach xx (list x0 x1)
        (foreach sg (es:recorta-v xx 0.0 hh rets)
          (es:line (list xx (car sg)) (list xx (cadr sg)) ES:LAY-CORTE)))
      ;; degrau seguinte, visto
      (es:line (list x0 (+ hh e)) (list x1 (+ hh e)) ES:LAY-VISTA)
      (foreach xx (list x0 x1)
        (foreach sg (es:recorta-v xx hh (+ hh e) rets)
          (es:line (list xx (car sg)) (list xx (cadr sg)) ES:LAY-VISTA)))
      ;; cotas
      (setq bb ES:CAIXA yd (- (min 0.0 (cadr bb)) (* 2.0 c)))
      (es:dimh x0 x1 (- (min 0.0 (cadr bb)) (* 0.5 c)) yd (es:f w))
      (setq xr (+ (caddr bb) (* 2.0 c)))
      (setq hv (/ (nth 8 g) (cos (atan (nth 6 g)))))
      (if (< hv (- hh 0.5))
        (progn
          (es:dimv 0.0 hv (+ (caddr bb) (* 0.5 c)) xr (es:f hv))
          (es:dimv hv hh (+ (caddr bb) (* 0.5 c)) xr (es:f (- hh hv))))
        (es:dimv 0.0 hh (+ (caddr bb) (* 0.5 c)) xr (es:f hh)))
      (es:dimv 0.0 hh (+ (caddr bb) (* 0.5 c)) (+ xr (* 2.5 c)) (es:f hh))
      (es:dimv hh (+ hh e) (+ (caddr bb) (* 0.5 c)) xr (es:f e))
      (setq bb ES:CAIXA)
      (es:titulo "CORTE A-A" (strcat ES:NOME " - " (nth 9 g) " (h=" (es:f (nth 8 g))
                                     ")   ESC. 1:" ES:ESC)
                 (* 0.5 (+ (car bb) (caddr bb))) (- (cadr bb) (* 3.0 c)))
    )
  )
)

;;; ==========================================================================
;;;  5.  DADOS NO DWG (dicionario ESCADA_DADOS) E BLOCOS DOS DESENHOS
;;; ==========================================================================

;;; valor -> grupos DXF de XRECORD (listas aninhadas)
(defun es:enc (x)
  (cond
    ((null x) (list (cons 281 0)))
    ((eq x T) (list (cons 281 1)))
    ((= (type x) 'STR) (list (cons 300 x)))
    ((= (type x) 'INT) (list (cons 90 x)))
    ((= (type x) 'REAL) (list (cons 40 x)))
    ((= (type x) 'LIST)
     (append (list (cons 282 1)) (apply 'append (mapcar 'es:enc x)) (list (cons 282 0))))
    (t (list (cons 281 0)))
  )
)

(defun es:dec (gs / stk cur)
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

(defun es:dic ( / d x)
  (if (setq d (dictsearch (namedobjdict) ES:DIC-NOME))
    (cdr (assoc -1 d))
    (progn
      (setq x (entmakex '((0 . "DICTIONARY") (100 . "AcDbDictionary"))))
      (dictadd (namedobjdict) ES:DIC-NOME x)
      x
    )
  )
)

(defun es:reg-ids ( / r)
  (foreach g (entget (es:dic)) (if (= (car g) 3) (setq r (cons (cdr g) r))))
  (reverse r)
)

;;; novo id: ES1, ES2, ...
(defun es:novo-id ( / n m)
  (setq n 0)
  (foreach k (es:reg-ids)
    (if (wcmatch k "ES#*") (if (> (setq m (atoi (substr k 3))) n) (setq n m))))
  (strcat "ES" (itoa (1+ n)))
)

(defun es:reg-grava (id dados / d x)
  (setq d (es:dic))
  (if (dictsearch d id) (dictremove d id))
  (setq x (entmakex (append (list '(0 . "XRECORD") '(100 . "AcDbXrecord")) (es:enc dados))))
  (if x
    (progn
      (dictadd d id x)
      (if (not (equal (es:reg-le id) dados 1e-6))
        (es:aviso (strcat "os dados de " id " nao foram lidos de volta iguais."))))
    (es:aviso (strcat "nao foi possivel gravar os dados de " id " (XRECORD).")))
  x
)

(defun es:reg-le (id / r gs)
  (if (setq r (dictsearch (es:dic) id))
    (progn
      (foreach g r (if (member (car g) '(300 40 90 281 282)) (setq gs (cons g gs))))
      (es:dec (reverse gs))))
)

;;; (id etiqueta desenho) do XDATA de uma entidade, ou nil
(defun es:id-ent (e / x r)
  (if (setq x (cdr (assoc -3 (entget e (list ES:APP)))))
    (progn
      (foreach g (cdr (car x)) (if (= (car g) 1000) (setq r (cons (cdr g) r))))
      (reverse r)))
)

(defun es:ents-id (id / ss i e r)
  (if (setq ss (ssget "_X" (list (list -3 (list ES:APP)))))
    (progn
      (setq i 0)
      (while (< i (sslength ss))
        (setq e (ssname ss i) i (1+ i))
        (if (= (car (es:id-ent e)) id) (setq r (cons e r))))))
  r
)

;;; entidades soltas (fora do bloco) de um desenho
(defun es:soltos (id grp / r)
  (foreach e (es:ents-id id)
    (if (and (/= (cdr (assoc 0 (entget e))) "INSERT") (= (caddr (es:id-ent e)) grp))
      (setq r (cons e r))))
  r
)

(defun es:insert-de (id grp / r)
  (foreach e (es:ents-id id)
    (if (and (null r) (= (cdr (assoc 0 (entget e))) "INSERT") (= (caddr (es:id-ent e)) grp))
      (setq r e)))
  r
)

(defun es:nome-bloco (id grp) (strcat "ESCADA$" id "$" grp))

;;; junta as entidades soltas do desenho num bloco (cria ou REDEFINE) e
;;; garante uma insercao em 0,0 (o usuario pode mover a insercao; na edicao a
;;; definicao e refeita e a insercao continua onde estiver).
(defun es:empacota (id grp / ents nome ins ed n ok copiados fora fim novo)
  (setq ents (es:soltos id grp) nome (es:nome-bloco id grp) ins (es:insert-de id grp))
  (if ins (setq nome (cdr (assoc 2 (entget ins)))))
  (if (null ents)
    (if ins (entdel ins))
    (progn
      (setq ok (entmake (list '(0 . "BLOCK") '(100 . "AcDbEntity") '(8 . "0")
                              '(100 . "AcDbBlockBegin") (cons 2 nome) '(70 . 0)
                              '(10 0.0 0.0 0.0))))
      (if (not ok)
        (progn
          (setq n 1)
          (while (tblsearch "BLOCK" (strcat (es:nome-bloco id grp) "$" (itoa n))) (setq n (1+ n)))
          (setq nome (strcat (es:nome-bloco id grp) "$" (itoa n))
                ok (entmake (list '(0 . "BLOCK") '(100 . "AcDbEntity") '(8 . "0")
                                  '(100 . "AcDbBlockBegin") (cons 2 nome) '(70 . 0)
                                  '(10 0.0 0.0 0.0))))))
      (if (not ok)
        (es:aviso (strcat "o CAD nao aceitou criar o bloco " nome "; o desenho fica solto."))
        (progn
          (setq copiados nil fora nil)
          (foreach e (reverse ents)
            (setq ed (vl-remove-if '(lambda (g) (member (car g) '(-1 5 67 102 330 360 410)))
                                   (entget e (list "*"))))
            (if (entmake ed) (setq copiados (cons e copiados)) (setq fora (cons (cdr (assoc 0 ed)) fora))))
          (setq fim (entmake '((0 . "ENDBLK"))))
          (if (not fim)
            (es:aviso (strcat "o CAD nao fechou o bloco " nome "; o desenho fica solto."))
            (progn
              (foreach e copiados (entdel e))
              (if fora
                (es:aviso (strcat (itoa (length fora)) " objeto(s) (" (car fora)
                                  ") ficaram fora do bloco " nome ".")))
              (if ins
                (progn
                  (if (/= (cdr (assoc 2 (entget ins))) nome)
                    (entmod (subst (cons 2 nome) (assoc 2 (entget ins)) (entget ins))))
                  (entupd ins))
                (progn
                  (setq novo (entmake (list '(0 . "INSERT") '(100 . "AcDbEntity") '(8 . "0")
                                            '(100 . "AcDbBlockReference") (cons 2 nome)
                                            '(10 0.0 0.0 0.0) '(41 . 1.0) '(42 . 1.0) '(43 . 1.0)
                                            '(50 . 0.0) (es:xd-lista id "" grp))))
                  (if (not novo) (es:aviso (strcat "o CAD nao aceitou inserir o bloco " nome ".")))))
            )
          )
        )
      )
    )
  )
)

;;; apaga um desenho (insercao e soltos)
(defun es:apaga-des (id grp / ins)
  (foreach e (es:soltos id grp) (entdel e))
  (if (setq ins (es:insert-de id grp)) (entdel ins))
)

;;; ---- unidades -----------------------------------------------------------------
;;; ES:UC = cm reais por unidade do desenho; ES:H texto (unid. desenho); ES:HC em cm
(defun es:unidades ( / esc)
  (setq esc (es:n ES:ESC))
  (if (<= esc 0.0) (setq esc 50.0))
  (setq ES:UC (cond ((= ES:UNI 0) esc) ((= ES:UNI 1) 100.0) ((= ES:UNI 2) 1.0) (t 0.1))
        ES:H  (/ (* (/ (es:n ES:ALT) 10.0) esc) ES:UC)
        ES:HC (* ES:H ES:UC))
)

;;; desenha um desenho (grp = "PLA" "LON" "TRA") com origem o e empacota
(defun es:desenha-view (id grp o gs)
  (foreach e (es:soltos id grp) (entdel e))
  (setq ES:ID id ES:TAG "" ES:GRP grp ES:O (es:p2 o) ES:CAIXA nil)
  (cond
    ((= grp "PLA") (es:des-pla gs))
    ((= grp "LON") (es:des-lon gs))
    ((= grp "TRA") (es:des-tra gs))
  )
  (setq ES:ID nil ES:GRP nil)
  (es:empacota id grp)
)

;;; ---- registro de uma escada ---------------------------------------------------
;;; (versao  parametros  trechos  apoios  origens)   origens = (("PLA" x y) ...)
(defun es:dados (origens)
  (list ES:VERSAO (mapcar 'eval ES:PARAMS) ES:TRE ES:APO origens)
)

(defun es:carrega (d / vs)
  (setq vs (nth 1 d))
  (foreach s ES:PARAMS
    (if vs (progn (set s (car vs)) (setq vs (cdr vs)))))
  (setq ES:TRE (nth 2 d) ES:APO (nth 3 d))
  (es:defaults)
  (nth 4 d)
)

;;; origem guardada de um desenho
(defun es:origem (origens grp / r)
  (if (setq r (assoc grp origens)) (cdr r))
)

;;; ==========================================================================
;;;  6.  JANELAS (DCL gerado em tempo de execucao)
;;; ==========================================================================

(defun es:defaults ()
  (if (null ES:NOME)  (setq ES:NOME "ESC1"))
  (if (null ES:NIV)   (setq ES:NIV "0.00"))
  (if (null ES:LAR)   (setq ES:LAR "120"))
  (if (null ES:POCO)  (setq ES:POCO "10"))
  (if (null ES:DIR)   (setq ES:DIR 0))
  (if (null ES:UNI)   (setq ES:UNI 0))
  (if (null ES:ESC)   (setq ES:ESC "50"))
  (if (null ES:ALT)   (setq ES:ALT "2"))
  (if (null ES:DPLA)  (setq ES:DPLA "1"))
  (if (null ES:DLON)  (setq ES:DLON "1"))
  (if (null ES:DTRA)  (setq ES:DTRA "1"))
  (if (null ES:TRAL)  (setq ES:TRAL 0))
  (if (null ES:LATE)  (setq ES:LATE (list "0" "VL1" "14" "40")))
  (if (null ES:LATD)  (setq ES:LATD (list "0" "VL2" "14" "40")))
  (if (null ES:MTIPO) (setq ES:MTIPO 4))
  (if (null ES:MDES)  (setq ES:MDES "288"))
  (if (null ES:MNDG)  (setq ES:MNDG "16"))
  (if (null ES:MPIS)  (setq ES:MPIS "28"))
  (if (null ES:MHL)   (setq ES:MHL "12"))
  (if (null ES:MHP)   (setq ES:MHP "12"))
  (if (null ES:MLP)   (setq ES:MLP "120"))
  (if (null ES:TRE)   (es:gera-modelo))
)

(defun es:write-dcl ( / f nome)
  (setq nome (strcat (getvar "TEMPPREFIX") "ES_ESCADA.dcl")
        f    (open nome "w"))
  (foreach ln
   (list
"es_main : dialog {"
"  label = \"ESCADA  -  FORMAS      v1.0      Baluarte\";"
"  : row {"
"    : column {"
"      : boxed_column {"
"        label = \"Escada\";"
"        : edit_box { key = \"nome\"; label = \"Nome :\"; edit_width = 10; }"
"        : edit_box { key = \"niv\"; label = \"Nivel inicial (m) :\"; edit_width = 8; }"
"        : edit_box { key = \"lar\"; label = \"Largura dos lances (cm) :\"; edit_width = 8; }"
"        : edit_box { key = \"poco\"; label = \"Vao entre lances em U (cm) :\"; edit_width = 8; }"
"        : popup_list { key = \"dir\"; label = \"Planta - sobe para :\"; edit_width = 14; }"
"      }"
"      : boxed_column {"
"        label = \"Modelo rapido  (gera trechos e apoios)\";"
"        : popup_list { key = \"mtipo\"; edit_width = 46; }"
"        : edit_box { key = \"mdes\"; label = \"Desnivel total piso a piso (cm) :\"; edit_width = 7; }"
"        : edit_box { key = \"mndg\"; label = \"Numero total de espelhos :\"; edit_width = 7; }"
"        : edit_box { key = \"mpis\"; label = \"Piso p (cm) :\"; edit_width = 7; }"
"        : edit_box { key = \"mhl\"; label = \"Espessura dos lances h (cm) :\"; edit_width = 7; }"
"        : edit_box { key = \"mhp\"; label = \"Espessura dos patamares (cm) :\"; edit_width = 7; }"
"        : edit_box { key = \"mlp\"; label = \"Comprimento do patamar reto/U (cm) :\"; edit_width = 7; }"
"        : text { key = \"minfo\"; width = 46; }"
"        : button { key = \"gera\"; label = \"Gerar trechos e apoios pelo modelo\"; }"
"      }"
"      : boxed_column {"
"        label = \"Desenhos\";"
"        : toggle { key = \"dpla\"; label = \"Planta de formas\"; }"
"        : toggle { key = \"dlon\"; label = \"Corte longitudinal (desenvolvido)\"; }"
"        : toggle { key = \"dtra\"; label = \"Corte transversal A-A\"; }"
"        : popup_list { key = \"tral\"; label = \"Corte A-A no :\"; edit_width = 20; }"
"      }"
"    }"
"    : column {"
"      : boxed_column {"
"        label = \"Trechos  (de baixo para cima;  duplo clique = editar)\";"
"        : list_box { key = \"tre\"; height = 9; width = 70; }"
"        : row {"
"          : button { key = \"addl\"; label = \"+ Lance\"; }"
"          : button { key = \"addp\"; label = \"+ Patamar\"; }"
"          : button { key = \"edt\"; label = \"Editar...\"; }"
"          : button { key = \"rmt\"; label = \"Remover\"; }"
"          : button { key = \"upt\"; label = \"Subir\"; }"
"          : button { key = \"dnt\"; label = \"Descer\"; }"
"        }"
"      }"
"      : boxed_column {"
"        label = \"Apoios  (vigas, lajes de piso, paredes)\";"
"        : list_box { key = \"apo\"; height = 5; width = 70; }"
"        : row {"
"          : button { key = \"adda\"; label = \"+ Apoio\"; }"
"          : button { key = \"eda\"; label = \"Editar...\"; }"
"          : button { key = \"rma\"; label = \"Remover\"; }"
"        }"
"      }"
"      : image { key = \"prev\"; width = 70; height = 11; color = -15; }"
"      : text { key = \"info\"; width = 70; }"
"    }"
"  }"
"  : row {"
"    : boxed_column {"
"      label = \"Apoio lateral ESQUERDO dos lances\";"
"      : popup_list { key = \"latet\"; edit_width = 16; }"
"      : row {"
"        : edit_box { key = \"laten\"; label = \"Nome :\"; edit_width = 6; }"
"        : edit_box { key = \"lateb\"; label = \"b :\"; edit_width = 4; }"
"        : edit_box { key = \"lateh\"; label = \"h :\"; edit_width = 4; }"
"      }"
"    }"
"    : boxed_column {"
"      label = \"Apoio lateral DIREITO dos lances\";"
"      : popup_list { key = \"latdt\"; edit_width = 16; }"
"      : row {"
"        : edit_box { key = \"latdn\"; label = \"Nome :\"; edit_width = 6; }"
"        : edit_box { key = \"latdb\"; label = \"b :\"; edit_width = 4; }"
"        : edit_box { key = \"latdh\"; label = \"h :\"; edit_width = 4; }"
"      }"
"    }"
"    : boxed_column {"
"      label = \"Unidades e texto\";"
"      : popup_list { key = \"uni\"; label = \"Desenho em :\"; edit_width = 24; }"
"      : row {"
"        : edit_box { key = \"esc\"; label = \"Escala 1 :\"; edit_width = 5; }"
"        : edit_box { key = \"alt\"; label = \"Texto (mm) :\"; edit_width = 4; }"
"      }"
"    }"
"  }"
"  : text { label = \"AVISO: ferramenta de apoio. A conferencia do resultado e a responsabilidade tecnica sao do engenheiro responsavel.\"; }"
"  ok_cancel;"
"}"
""
"es_lance : dialog {"
"  label = \"Lance\";"
"  : edit_box { key = \"nome\"; label = \"Nome :\"; edit_width = 16; }"
"  : edit_box { key = \"nesp\"; label = \"Numero de espelhos  N :\"; edit_width = 7; }"
"  : row {"
"    : edit_box { key = \"e\"; label = \"Espelho  e (cm) :\"; edit_width = 7; }"
"    : button { key = \"calc\"; label = \"e = desnivel / N\"; }"
"    : edit_box { key = \"des\"; label = \"desnivel do lance (cm) :\"; edit_width = 7; }"
"  }"
"  : edit_box { key = \"p\"; label = \"Piso  p (cm) :\"; edit_width = 7; }"
"  : popup_list { key = \"npis\"; label = \"Pisos no lance :\"; edit_width = 46; }"
"  : edit_box { key = \"h\"; label = \"Espessura  h (cm, perpendicular a laje) :\"; edit_width = 7; }"
"  : text { key = \"info\"; width = 64; }"
"  : text { key = \"info2\"; width = 64; }"
"  ok_cancel;"
"}"
""
"es_pat : dialog {"
"  label = \"Patamar\";"
"  : edit_box { key = \"nome\"; label = \"Nome :\"; edit_width = 16; }"
"  : edit_box { key = \"l\"; label = \"Comprimento na direcao da subida (cm) :\"; edit_width = 7; }"
"  : edit_box { key = \"hp\"; label = \"Espessura (cm) :\"; edit_width = 7; }"
"  : edit_box { key = \"desn\"; label = \"Desnivel no inicio do patamar (cm, 0 = sem) :\"; edit_width = 7; }"
"  : popup_list { key = \"giro\"; label = \"Giro da escada no patamar :\"; edit_width = 28; }"
"  : text { label = \"Giro de 90 graus: use comprimento = largura do lance.\"; }"
"  : text { label = \"Giro de 180 (U): a largura do patamar = 2 x largura + vao entre lances.\"; }"
"  ok_cancel;"
"}"
""
"es_apo : dialog {"
"  label = \"Apoio\";"
"  : edit_box { key = \"nome\"; label = \"Nome (ex.: V1, L5, PAR1) :\"; edit_width = 12; }"
"  : popup_list { key = \"tipo\"; label = \"Tipo :\"; edit_width = 18; }"
"  : edit_box { key = \"b\"; label = \"Largura b (cm)   [laje: comprimento desenhado] :\"; edit_width = 7; }"
"  : edit_box { key = \"h\"; label = \"Altura h (cm)   [laje: espessura] :\"; edit_width = 7; }"
"  : popup_list { key = \"pos\"; label = \"Posicao :\"; edit_width = 40; }"
"  : edit_box { key = \"desl\"; label = \"Deslocamento do eixo (cm, + = no sentido da subida) :\"; edit_width = 7; }"
"  : text { label = \"Viga / parede: o EIXO fica na posicao + deslocamento (topo no nivel da laje).\"; }"
"  : text { label = \"Laje de piso: sai para fora da escada a partir da posicao.\"; }"
"  ok_cancel;"
"}"
   )
    (write-line ln f)
  )
  (close f)
  nome
)

;;; ---- textos das listas -------------------------------------------------------
(defun es:tre-linha (i tr / g)
  (if (es:lance-p tr)
    (progn
      (setq g (es:lance-num tr))
      (strcat "T" (itoa (1+ i)) "   " (nth 1 tr) "   :   " (itoa (nth 0 g)) " espelhos de "
              (es:f (nth 1 g)) "  x  piso " (es:f (nth 2 g)) "   (" (itoa (nth 3 g)) " pisos = "
              (es:f (* (nth 3 g) (nth 2 g))) ")   h=" (es:f (nth 4 g))))
    (strcat "T" (itoa (1+ i)) "   " (nth 1 tr) "   :   L=" (es:f (es:n (nth 2 tr)))
            "   h=" (es:f (es:n (nth 3 tr)))
            (if (> (abs (es:n (nth 4 tr))) 0.001) (strcat "   desnivel " (es:f (es:n (nth 4 tr)))) "")
            "   giro " (nth (es:int (es:n (nth 5 tr))) ES:GIROS-C)))
)

;;; posicoes possiveis de um apoio (inicio/fim de cada trecho)
(defun es:pos-linhas ( / r i)
  (setq i 0)
  (foreach tr ES:TRE
    (setq r (cons (strcat "T" (itoa (1+ i)) " " (nth 1 tr) " - fim")
                  (cons (strcat "T" (itoa (1+ i)) " " (nth 1 tr) " - inicio") r))
          i (1+ i)))
  (reverse r)
)

(defun es:apo-linha (ap / j pl)
  (setq j (es:int (es:n (nth 4 ap))) pl (es:pos-linhas))
  (strcat (nth 0 ap) "   " (nth (es:int (es:n (nth 1 ap))) ES:TIPOS-APO) " "
          (es:f (es:n (nth 2 ap))) "x" (es:f (es:n (nth 3 ap))) "   em  "
          (if (es:nth j pl) (es:nth j pl) (es:ultimo pl))
          (if (> (abs (es:n (nth 5 ap))) 0.001) (strcat "  " (es:f (es:n (nth 5 ap))) " cm") ""))
)

(defun es:lances-nomes ( / r)
  (foreach tr ES:TRE (if (es:lance-p tr) (setq r (cons (nth 1 tr) r))))
  (reverse r)
)

;;; ---- janela principal: preencher, ler, atualizar -------------------------------
(defun es:lista (k itens sel)
  (start_list k) (mapcar 'add_list itens) (end_list)
  (if (and sel itens) (set_tile k (itoa (min sel (1- (length itens))))))
)

(defun es:main-listas ( / i r)
  (setq i 0 r nil)
  (foreach tr ES:TRE (setq r (cons (es:tre-linha i tr) r) i (1+ i)))
  (es:lista "tre" (reverse r) ES:SEL-T)
  (es:lista "apo" (mapcar 'es:apo-linha ES:APO) ES:SEL-A)
  (es:lista "tral" (es:lances-nomes) nil)
  (set_tile "tral" (itoa (min (es:int (es:n ES:TRAL)) (max 0 (1- (length (es:lances-nomes)))))))
  (vl-catch-all-apply 'es:prev-img nil)
  (vl-catch-all-apply 'es:main-info nil)
)

(defun es:main-info ( / r gs)
  (setq gs (es:geo ES:TRE) r (es:resumo gs))
  (set_tile "info" (strcat "Desnivel total " (es:f (nth 0 r)) " cm   |   desenvolvimento "
                           (es:f (nth 1 r)) " cm"
                           (if (nth 2 r) (strcat "   |   Blondel 2e+p = " (es:f (nth 2 r))
                                                 (if (and (>= (nth 2 r) 60.0) (<= (nth 2 r) 65.0))
                                                   " (ok)" " (fora de 60 a 65!)"))
                             "")))
)

(defun es:minfo ( / n d p e)
  (setq n (es:num (get_tile "mndg")) d (es:num (get_tile "mdes")) p (es:num (get_tile "mpis")))
  (if (and n d p (> n 0))
    (progn
      (setq e (/ d (fix n)))
      (set_tile "minfo" (strcat "Espelho e = " (es:f e) " cm    2e+p = " (es:f (+ e e p))
                                (if (and (>= (+ e e p) 60.0) (<= (+ e e p) 65.0)) "  (ok)" "  (fora de 60 a 65)"))))
    (set_tile "minfo" ""))
)

;;; ponto da previa (usa k ox oy xmin ymin h de es:prev-img)
(defun es:pv (p)
  (list (fix (+ ox (* k (- (car p) xmin)))) (fix (- h oy (* k (- (cadr p) ymin)))))
)

;;; desenho do corte na previa
(defun es:prev-img ( / w h gs top sc pts xmin xmax ymin ymax k ox oy a rets q)
  (setq w (dimx_tile "prev") h (dimy_tile "prev"))
  (start_image "prev")
  (fill_image 0 0 w h -15)
  (if ES:TRE
    (progn
      (setq gs (es:geo ES:TRE) top (es:topo gs) sc (es:intradorso gs)
            rets (mapcar '(lambda (ap) (es:apo-ret gs ap)) ES:APO)
            pts (append top sc))
      (foreach r rets (setq pts (cons (list (nth 0 r) (nth 2 r)) (cons (list (nth 1 r) (nth 3 r)) pts))))
      (setq xmin (apply 'min (mapcar 'car pts)) xmax (apply 'max (mapcar 'car pts))
            ymin (apply 'min (mapcar 'cadr pts)) ymax (apply 'max (mapcar 'cadr pts)))
      (setq k (min (/ (- w 12.0) (max 1.0 (- xmax xmin))) (/ (- h 12.0) (max 1.0 (- ymax ymin))))
            ox (* 0.5 (- w (* k (- xmax xmin))))
            oy (* 0.5 (- h (* k (- ymax ymin)))))
      (foreach cad (list top sc
                         (list (car sc) (car top))
                         (list (es:ultimo sc) (es:ultimo top)))
        (setq a (es:pv (car cad)))
        (foreach p (cdr cad)
          (setq q (es:pv p))
          (vector_image (car a) (cadr a) (car q) (cadr q) 5)
          (setq a q)))
      (foreach r rets
        (setq a (es:pv (list (nth 0 r) (nth 2 r))) q (es:pv (list (nth 1 r) (nth 3 r))))
        (vector_image (car a) (cadr a) (car q) (cadr a) 1)
        (vector_image (car q) (cadr a) (car q) (cadr q) 1)
        (vector_image (car q) (cadr q) (car a) (cadr q) 1)
        (vector_image (car a) (cadr q) (car a) (cadr a) 1))
    )
  )
  (end_image)
)

(defun es:main-set ()
  (es:lista "dir" ES:DIRS nil)
  (es:lista "mtipo" ES:MODELOS nil)
  (es:lista "latet" ES:TIPOS-LAT nil)
  (es:lista "latdt" ES:TIPOS-LAT nil)
  (es:lista "uni" ES:LST-UNI nil)
  (set_tile "nome" ES:NOME) (set_tile "niv" ES:NIV) (set_tile "lar" ES:LAR)
  (set_tile "poco" ES:POCO) (set_tile "dir" (itoa ES:DIR))
  (set_tile "mtipo" (itoa ES:MTIPO)) (set_tile "mdes" ES:MDES) (set_tile "mndg" ES:MNDG)
  (set_tile "mpis" ES:MPIS) (set_tile "mhl" ES:MHL) (set_tile "mhp" ES:MHP) (set_tile "mlp" ES:MLP)
  (set_tile "dpla" ES:DPLA) (set_tile "dlon" ES:DLON) (set_tile "dtra" ES:DTRA)
  (set_tile "latet" (nth 0 ES:LATE)) (set_tile "laten" (nth 1 ES:LATE))
  (set_tile "lateb" (nth 2 ES:LATE)) (set_tile "lateh" (nth 3 ES:LATE))
  (set_tile "latdt" (nth 0 ES:LATD)) (set_tile "latdn" (nth 1 ES:LATD))
  (set_tile "latdb" (nth 2 ES:LATD)) (set_tile "latdh" (nth 3 ES:LATD))
  (set_tile "uni" (itoa ES:UNI)) (set_tile "esc" ES:ESC) (set_tile "alt" ES:ALT)
  (es:main-listas)
  (es:minfo)
)

;;; le todos os campos (sem validar)
(defun es:main-le ( / v)
  (setq ES:NOME (vl-string-trim " " (get_tile "nome")) ES:NIV (get_tile "niv")
        ES:LAR (get_tile "lar") ES:POCO (get_tile "poco") ES:DIR (atoi (get_tile "dir"))
        ES:MTIPO (atoi (get_tile "mtipo")) ES:MDES (get_tile "mdes") ES:MNDG (get_tile "mndg")
        ES:MPIS (get_tile "mpis") ES:MHL (get_tile "mhl") ES:MHP (get_tile "mhp")
        ES:MLP (get_tile "mlp")
        ES:DPLA (get_tile "dpla") ES:DLON (get_tile "dlon") ES:DTRA (get_tile "dtra")
        ES:LATE (list (get_tile "latet") (get_tile "laten") (get_tile "lateb") (get_tile "lateh"))
        ES:LATD (list (get_tile "latdt") (get_tile "latdn") (get_tile "latdb") (get_tile "latdh"))
        ES:UNI (atoi (get_tile "uni")) ES:ESC (get_tile "esc") ES:ALT (get_tile "alt"))
  (if (/= (setq v (get_tile "tral")) "") (setq ES:TRAL (atoi v)))
)

(defun es:erro-campo (k msg) (alert msg) (mode_tile k 2) nil)

(defun es:pos? (k) (and (es:num (get_tile k)) (> (es:num (get_tile k)) 0.0)))

(defun es:main-valida ()
  (cond
    ((= (vl-string-trim " " (get_tile "nome")) "") (es:erro-campo "nome" "Informe o nome da escada (ex.: ESC1)."))
    ((null (es:num (get_tile "niv"))) (es:erro-campo "niv" "Nivel inicial invalido (em metros, ex.: 0.00)."))
    ((not (es:pos? "lar")) (es:erro-campo "lar" "A largura deve ser maior que zero."))
    ((or (null (es:num (get_tile "poco"))) (< (es:num (get_tile "poco")) 0.0))
     (es:erro-campo "poco" "O vao entre lances deve ser >= 0."))
    ((null ES:TRE) (alert "Crie pelo menos um trecho (lance ou patamar).") nil)
    ((not (es:lances-nomes)) (alert "A escada precisa de pelo menos um LANCE.") nil)
    ((and (/= (get_tile "latet") "0") (not (and (es:pos? "lateb") (es:pos? "lateh"))))
     (es:erro-campo "lateb" "Informe b e h do apoio lateral esquerdo."))
    ((and (/= (get_tile "latdt") "0") (not (and (es:pos? "latdb") (es:pos? "latdh"))))
     (es:erro-campo "latdb" "Informe b e h do apoio lateral direito."))
    ((not (es:pos? "esc")) (es:erro-campo "esc" "A escala deve ser maior que zero (ex.: 50)."))
    ((not (es:pos? "alt")) (es:erro-campo "alt" "A altura do texto deve ser maior que zero (ex.: 2)."))
    ((and (= (get_tile "dpla") "0") (= (get_tile "dlon") "0") (= (get_tile "dtra") "0"))
     (alert "Marque pelo menos um desenho.") nil)
    (t T)
  )
)

;;; mantem cada apoio preso ao mesmo trecho depois de inserir / remover / trocar
;;; trechos.  op = (list "ins" i) (list "rem" i) (list "troca" a b)
(defun es:apo-remapeia (op / r j k f)
  (foreach ap ES:APO
    (setq j (es:int (es:n (nth 4 ap))) k (/ j 2) f (rem j 2))
    (cond
      ((= (car op) "ins") (if (>= k (cadr op)) (setq k (1+ k))))
      ((= (car op) "rem")
       (cond ((> k (cadr op)) (setq k (1- k)))
             ((and (= k (cadr op)) (> k 0)) (setq k (1- k) f 1))))
      ((= (car op) "troca")
       (cond ((= k (cadr op)) (setq k (caddr op)))
             ((= k (caddr op)) (setq k (cadr op))))))
    (setq r (cons (es:setnth ap 4 (itoa (+ (* 2 k) f))) r)))
  (setq ES:APO (reverse r))
)

;;; indice selecionado de uma lista (ou nil)
(defun es:sel (k / v) (if (/= (setq v (get_tile k)) "") (atoi v)))

;;; acoes feitas sem fechar a janela
(defun es:acao (a / i)
  (cond
    ((= a "gera")
     (es:main-le)
     (if (and (es:num ES:MDES) (es:num ES:MNDG) (es:num ES:MPIS) (es:num ES:MLP)
              (es:num ES:MHL) (es:num ES:MHP) (> (es:num ES:MNDG) 0))
       (progn (es:gera-modelo) (setq ES:SEL-T 0 ES:SEL-A 0) (es:main-listas))
       (alert "Preencha os campos do modelo rapido com numeros.")))
    ((= a "rmt")
     (if (setq i (es:sel "tre"))
       (progn (setq ES:TRE (es:remove-nth ES:TRE i) ES:SEL-T (max 0 (1- i)))
              (es:apo-remapeia (list "rem" i)) (es:main-listas))))
    ((= a "upt")
     (if (and (setq i (es:sel "tre")) (> i 0))
       (progn (setq ES:TRE (es:troca ES:TRE i (1- i)) ES:SEL-T (1- i))
              (es:apo-remapeia (list "troca" i (1- i))) (es:main-listas))))
    ((= a "dnt")
     (if (and (setq i (es:sel "tre")) (< i (1- (length ES:TRE))))
       (progn (setq ES:TRE (es:troca ES:TRE i (1+ i)) ES:SEL-T (1+ i))
              (es:apo-remapeia (list "troca" i (1+ i))) (es:main-listas))))
    ((= a "rma")
     (if (setq i (es:sel "apo"))
       (progn (setq ES:APO (es:remove-nth ES:APO i) ES:SEL-A (max 0 (1- i))) (es:main-listas))))
  )
)

;;; fecha a janela para abrir uma sub-janela (os campos ficam guardados)
(defun es:sai (cod)
  (es:main-le)
  (setq ES:SEL-T (es:sel "tre") ES:SEL-A (es:sel "apo"))
  (done_dialog cod)
)

(defun es:dlg-main (id / r)
  (if (not (new_dialog "es_main" id))
    0
    (progn
      (es:main-set)
      (foreach k '("gera" "rmt" "upt" "dnt" "rma")
        (action_tile k (strcat "(vl-catch-all-apply 'es:acao (list \"" k "\"))")))
      (foreach k '("mndg" "mdes" "mpis") (action_tile k "(es:minfo)"))
      (action_tile "addl" "(es:sai 10)")
      (action_tile "addp" "(es:sai 11)")
      (action_tile "edt"  "(if (es:sel \"tre\") (es:sai 12))")
      (action_tile "tre"  "(setq ES:SEL-T (atoi $value)) (if (= $reason 4) (es:sai 12))")
      (action_tile "adda" "(es:sai 20)")
      (action_tile "eda"  "(if (es:sel \"apo\") (es:sai 21))")
      (action_tile "apo"  "(setq ES:SEL-A (atoi $value)) (if (= $reason 4) (es:sai 21))")
      (action_tile "accept" "(if (es:main-valida) (progn (es:main-le) (done_dialog 1)))")
      (action_tile "cancel" "(done_dialog 0)")
      (start_dialog)
    )
  )
)

;;; ---- sub-janelas -----------------------------------------------------------------
(defun es:lance-info ( / n e p m d l)
  (setq n (es:num (get_tile "nesp")) e (es:num (get_tile "e")) p (es:num (get_tile "p"))
        m (get_tile "npis"))
  (if (and n e p (>= n 1))
    (progn
      (setq n (fix n) l (* p (if (or (= m "1") (= n 1)) n (1- n))))
      (set_tile "info" (strcat "Desnivel do lance = " (itoa n) " x " (es:f e) " = " (es:f (* n e))
                               " cm      Comprimento = " (es:f l) " cm"))
      (set_tile "info2" (strcat "Blondel: 2e + p = " (es:f (+ e e p))
                                (if (and (>= (+ e e p) 60.0) (<= (+ e e p) 65.0))
                                  "  (ok, 60 a 65)" "  (FORA de 60 a 65 cm)"))))
    (progn (set_tile "info" "") (set_tile "info2" "")))
)

(defun es:dlg-lance (id tr / r ok)
  (if (null tr) (setq tr (list "LANCE" (strcat "LANCE " (itoa (1+ (length (es:lances-nomes)))))
                               "9" (es:f (/ (es:n ES:MDES) (max 1 (es:int (es:n ES:MNDG)))))
                               ES:MPIS "0" ES:MHL)))
  (if (new_dialog "es_lance" id)
    (progn
      (es:lista "npis" ES:NPIS nil)
      (set_tile "nome" (nth 1 tr)) (set_tile "nesp" (nth 2 tr)) (set_tile "e" (nth 3 tr))
      (set_tile "p" (nth 4 tr)) (set_tile "npis" (nth 5 tr)) (set_tile "h" (nth 6 tr))
      (set_tile "des" (es:f (* (es:n (nth 2 tr)) (es:n (nth 3 tr)))))
      (es:lance-info)
      (foreach k '("nesp" "e" "p" "npis") (action_tile k "(es:lance-info)"))
      (action_tile "calc"
        "(if (and (es:pos? \"des\") (es:pos? \"nesp\")) (progn (set_tile \"e\" (es:f (/ (es:num (get_tile \"des\")) (fix (es:num (get_tile \"nesp\")))))) (es:lance-info)))")
      (action_tile "accept"
        (strcat "(cond"
                "((= (vl-string-trim \" \" (get_tile \"nome\")) \"\") (es:erro-campo \"nome\" \"Informe o nome do lance.\"))"
                "((or (null (es:num (get_tile \"nesp\"))) (< (es:num (get_tile \"nesp\")) 1)) (es:erro-campo \"nesp\" \"N deve ser um inteiro >= 1.\"))"
                "((not (es:pos? \"e\")) (es:erro-campo \"e\" \"O espelho deve ser maior que zero.\"))"
                "((not (es:pos? \"p\")) (es:erro-campo \"p\" \"O piso deve ser maior que zero.\"))"
                "((not (es:pos? \"h\")) (es:erro-campo \"h\" \"A espessura deve ser maior que zero.\"))"
                "(t (setq ES:RETORNO (list \"LANCE\" (vl-string-trim \" \" (get_tile \"nome\"))"
                " (itoa (fix (es:num (get_tile \"nesp\")))) (get_tile \"e\") (get_tile \"p\")"
                " (get_tile \"npis\") (get_tile \"h\"))) (done_dialog 1)))"))
      (action_tile "cancel" "(done_dialog 0)")
      (setq ES:RETORNO nil ok (start_dialog))
      (if (= ok 1) ES:RETORNO)
    )
  )
)

(defun es:dlg-pat (id tr / ok)
  (if (null tr)
    (setq tr (list "PATAMAR" (strcat "PATAMAR " (itoa (1+ (- (length ES:TRE) (length (es:lances-nomes))))))
                   ES:MLP ES:MHP "0" "0")))
  (if (new_dialog "es_pat" id)
    (progn
      (es:lista "giro" ES:GIROS nil)
      (set_tile "nome" (nth 1 tr)) (set_tile "l" (nth 2 tr)) (set_tile "hp" (nth 3 tr))
      (set_tile "desn" (nth 4 tr)) (set_tile "giro" (nth 5 tr))
      (action_tile "accept"
        (strcat "(cond"
                "((= (vl-string-trim \" \" (get_tile \"nome\")) \"\") (es:erro-campo \"nome\" \"Informe o nome do patamar.\"))"
                "((not (es:pos? \"l\")) (es:erro-campo \"l\" \"O comprimento deve ser maior que zero.\"))"
                "((not (es:pos? \"hp\")) (es:erro-campo \"hp\" \"A espessura deve ser maior que zero.\"))"
                "((null (es:num (get_tile \"desn\"))) (es:erro-campo \"desn\" \"Desnivel invalido (0 = sem).\"))"
                "(t (setq ES:RETORNO (list \"PATAMAR\" (vl-string-trim \" \" (get_tile \"nome\"))"
                " (get_tile \"l\") (get_tile \"hp\") (get_tile \"desn\") (get_tile \"giro\"))) (done_dialog 1)))"))
      (action_tile "cancel" "(done_dialog 0)")
      (setq ES:RETORNO nil ok (start_dialog))
      (if (= ok 1) ES:RETORNO)
    )
  )
)

(defun es:dlg-apo (id ap / ok)
  (if (null ap)
    (setq ap (list (strcat "V" (itoa (1+ (length ES:APO)))) "0" "14" "40"
                   (itoa (if ES:SEL-T (* 2 ES:SEL-T) 0)) "0")))
  (if (new_dialog "es_apo" id)
    (progn
      (es:lista "tipo" ES:TIPOS-APO nil)
      (es:lista "pos" (es:pos-linhas) nil)
      (set_tile "nome" (nth 0 ap)) (set_tile "tipo" (nth 1 ap)) (set_tile "b" (nth 2 ap))
      (set_tile "h" (nth 3 ap))
      (set_tile "pos" (itoa (min (es:int (es:n (nth 4 ap))) (1- (* 2 (length ES:TRE))))))
      (set_tile "desl" (nth 5 ap))
      (action_tile "accept"
        (strcat "(cond"
                "((= (vl-string-trim \" \" (get_tile \"nome\")) \"\") (es:erro-campo \"nome\" \"Informe o nome do apoio.\"))"
                "((not (es:pos? \"b\")) (es:erro-campo \"b\" \"b deve ser maior que zero.\"))"
                "((not (es:pos? \"h\")) (es:erro-campo \"h\" \"h deve ser maior que zero.\"))"
                "((null (es:num (get_tile \"desl\"))) (es:erro-campo \"desl\" \"Deslocamento invalido (0 = sem).\"))"
                "(t (setq ES:RETORNO (list (vl-string-trim \" \" (get_tile \"nome\")) (get_tile \"tipo\")"
                " (get_tile \"b\") (get_tile \"h\") (get_tile \"pos\") (get_tile \"desl\"))) (done_dialog 1)))"))
      (action_tile "cancel" "(done_dialog 0)")
      (setq ES:RETORNO nil ok (start_dialog))
      (if (= ok 1) ES:RETORNO)
    )
  )
)

;;; ---- laco da janela: devolve T se o usuario confirmou ------------------------------
(defun es:janela ( / dcl id acao fim ok r i)
  (es:defaults)
  (setq dcl (es:write-dcl) id (load_dialog dcl) fim nil ok nil)
  (if (< id 0)
    (princ "\n*** Nao foi possivel carregar o DCL.")
    (while (not fim)
      (setq acao (es:dlg-main id))
      (cond
        ((= acao 1) (setq ok T fim T))
        ((or (null acao) (= acao 0)) (setq fim T))
        ((member acao '(10 11))
         (if (setq r (if (= acao 10) (es:dlg-lance id nil) (es:dlg-pat id nil)))
           (progn
             (setq i (if ES:SEL-T (1+ ES:SEL-T) (length ES:TRE)))
             (es:apo-remapeia (list "ins" i))
             (setq ES:TRE (es:insere-nth ES:TRE i r) ES:SEL-T i))))
        ((= acao 12)
         (if (and ES:SEL-T (setq i ES:SEL-T) (es:nth i ES:TRE))
           (if (setq r (if (es:lance-p (nth i ES:TRE))
                         (es:dlg-lance id (nth i ES:TRE)) (es:dlg-pat id (nth i ES:TRE))))
             (setq ES:TRE (es:setnth ES:TRE i r)))))
        ((= acao 20)
         (if (setq r (es:dlg-apo id nil))
           (setq ES:APO (append ES:APO (list r)) ES:SEL-A (1- (length ES:APO)))))
        ((= acao 21)
         (if (and ES:SEL-A (es:nth ES:SEL-A ES:APO))
           (if (setq r (es:dlg-apo id (nth ES:SEL-A ES:APO)))
             (setq ES:APO (es:setnth ES:APO ES:SEL-A r)))))
      )
    )
  )
  (if (> id 0) (unload_dialog id))
  ok
)

;;; ==========================================================================
;;;  7.  LEITURA DE UM CORTE JA DESENHADO  (ESCADACORTE)
;;;  O perfil dos degraus e o maior "caminho em escada" (segmentos horizontais
;;;  para a direita e verticais para cima) formado pelas linhas selecionadas.
;;;  Serve tanto a polilinha so do perfil quanto o contorno fechado do corte
;;;  (a laje inclinada e as faces das pontas nao entram no caminho).
;;; ==========================================================================

;;; segmentos (cm) de uma entidade
(defun es:segs-ent (e / ed tp pts r e2 ed2 fech)
  (setq ed (entget e) tp (cdr (assoc 0 ed)))
  (cond
    ((= tp "LINE")
     (setq r (list (list (es:mul (es:p2 (cdr (assoc 10 ed))) ES:UC)
                         (es:mul (es:p2 (cdr (assoc 11 ed))) ES:UC)))))
    ((= tp "LWPOLYLINE")
     (foreach g ed (if (= (car g) 10) (setq pts (cons (es:mul (es:p2 (cdr g)) ES:UC) pts))))
     (setq pts (reverse pts) fech (= 1 (logand 1 (cdr (assoc 70 ed))))))
    ((= tp "POLYLINE")
     (setq fech (= 1 (logand 1 (cdr (assoc 70 ed)))) e2 (entnext e))
     (while (and e2 (= (cdr (assoc 0 (setq ed2 (entget e2)))) "VERTEX"))
       (setq pts (cons (es:mul (es:p2 (cdr (assoc 10 ed2))) ES:UC) pts) e2 (entnext e2)))
     (setq pts (reverse pts)))
  )
  (if pts
    (progn
      (if fech (setq pts (append pts (list (car pts)))))
      (while (cdr pts)
        (setq r (cons (list (car pts) (cadr pts)) r) pts (cdr pts)))))
  r
)

;;; ordena uma lista pela chave (insercao; mantem repetidos)
(defun es:ordena (l chave / r x a b)
  (setq r nil)
  (foreach x l
    (setq a nil b r)
    (while (and b (<= (apply chave (list (car b))) (apply chave (list x)))) (setq a (cons (car b) a) b (cdr b)))
    (setq r (append (reverse a) (list x) b)))
  r
)

(defun es:mediana (l / s n)
  (setq s (es:ordena l '(lambda (v) v)) n (length s))
  (if (> n 0) (nth (/ n 2) s))
)

;;; maior caminho em escada: lista de (p q tipo comprimento), tipo "H" ou "V"
(defun es:no (p / i k)
  (setq i 0 k nil)
  (foreach q nos (if (and (null k) (< (es:dist p q) 0.5)) (setq k i)) (setq i (1+ i)))
  (if k k (progn (setq nos (append nos (list p))) (1- (length nos))))
)

(defun es:escadaria (segs / nos ars a b dx dy l cnt ant i j k best r ed)
  (setq nos nil ars nil)
  (foreach sg segs
    (setq a (car sg) b (cadr sg) dx (- (car b) (car a)) dy (- (cadr b) (cadr a))
          l (sqrt (+ (* dx dx) (* dy dy))))
    (if (> l 0.5)
      (cond
        ((<= (abs dy) (* 0.02 l))
         (if (< dx 0.0) (setq ars (cons (list (es:no b) (es:no a) "H" l) ars))
                        (setq ars (cons (list (es:no a) (es:no b) "H" l) ars))))
        ((<= (abs dx) (* 0.02 l))
         (if (< dy 0.0) (setq ars (cons (list (es:no b) (es:no a) "V" l) ars))
                        (setq ars (cons (list (es:no a) (es:no b) "V" l) ars)))))))
  (if ars
    (progn
      (setq ars (es:ordena ars '(lambda (x) (+ (car (nth (car x) nos)) (cadr (nth (car x) nos))))))
      (setq cnt nil ant nil)
      (repeat (length nos) (setq cnt (cons 0 cnt) ant (cons nil ant)))
      (foreach x ars
        (setq i (car x) j (cadr x))
        (if (> (1+ (nth i cnt)) (nth j cnt))
          (setq cnt (es:setnth cnt j (1+ (nth i cnt))) ant (es:setnth ant j x))))
      ;; no com o maior caminho (empate: o mais alto)
      (setq best 0 k 0 i 0)
      (foreach c cnt
        (if (or (> c best) (and (= c best) (> c 0) (> (cadr (nth i nos)) (cadr (nth k nos)))))
          (setq best c k i))
        (setq i (1+ i)))
      (setq r nil)
      (while (setq ed (nth k ant))
        (setq r (cons (list (nth (car ed) nos) (nth (cadr ed) nos) (caddr ed) (cadddr ed)) r)
              k (car ed)))
      ;; junta pedacos seguidos do mesmo tipo
      (setq ars r r nil)
      (foreach x ars
        (if (and r (= (caddr (car r)) (caddr x)))
          (setq r (cons (list (car (car r)) (cadr x) (caddr x) (+ (cadddr (car r)) (cadddr x))) (cdr r)))
          (setq r (cons x r))))
      (reverse r)
    )
  )
)

;;; espelha os segmentos em x
(defun es:espelha (segs)
  (mapcar '(lambda (sg) (mapcar '(lambda (p) (list (- (car p)) (cadr p))) sg)) segs)
)

;;; reconhece a escada.  Devolve (trechos origem-cm sinal) ou uma mensagem (texto).
(defun es:imp-fecha ()
  (if (> nv 0)
    (if (and (= nv 1) (= nh 0) trs (not (es:lance-p (car trs))) pat)
      (setq des (/ sv nv))                        ; 1 degrau entre patamares
      (setq trs (cons (list "LANCE" (strcat "LANCE " (itoa (1+ (length (vl-remove-if-not 'es:lance-p trs)))))
                            (itoa nv) (es:f (/ sv nv)) (es:f (if (> nh 0) (/ sh nh) pm))
                            (if (>= nh nv) "1" "0") ES:MHL)
                      trs))))
  (setq nv 0 sv 0.0 nh 0 sh 0.0)
)

(defun es:importa (segs0 / sg2 c1 c2 sgn segs cam em pm hs vs i x o trs nv sv nh sh
                          ult pat des r trx gs best d y ym xm b cs)
  (setq c1 (es:escadaria segs0) c2 (es:escadaria (setq sg2 (es:espelha segs0))))
  (if (> (length c2) (length c1))
    (setq cam c2 sgn -1.0 segs sg2)
    (setq cam c1 sgn 1.0 segs segs0))
  ;; tira os horizontais do inicio (piso de baixo)
  (while (and cam (= (caddr (car cam)) "H")) (setq cam (cdr cam)))
  (setq vs nil hs nil i 0)
  (foreach x cam
    (if (= (caddr x) "V") (setq vs (cons (cadddr x) vs)))
    (if (and (= (caddr x) "H") (> i 0) (< i (1- (length cam)))) (setq hs (cons (cadddr x) hs)))
    (setq i (1+ i)))
  (cond
    ((or (< (length vs) 2) (null hs))
     "Nao reconheci degraus na selecao (preciso de linhas horizontais e verticais do perfil).")
    (t
     (setq em (es:mediana vs) pm (es:mediana (vl-remove-if '(lambda (v) (> v (* 3.0 (es:mediana hs)))) hs)))
     (if (null pm) (setq pm (es:mediana hs)))
     ;; 1.o vertical muito alto = face da ponta + 1.o espelho
     (setq x (car cam))
     (if (> (cadddr x) (* 1.4 em))
       (setq cam (cons (list (list (car (cadr x)) (- (cadr (cadr x)) em)) (cadr x) "V" em) (cdr cam))))
     (setq o (car (car cam)))
     ;; percorre: lances e patamares
     (setq trs nil nv 0 sv 0.0 nh 0 sh 0.0 i 0 des 0.0 pat nil)
     (foreach x cam
       (setq ult (= i (1- (length cam))))
       (cond
         ((= (caddr x) "V") (setq nv (1+ nv) sv (+ sv (cadddr x))))
         ((and (not ult) (> (cadddr x) (max (* 1.5 pm) (+ pm 20.0))))
          (setq pat T)
          (es:imp-fecha)
          (setq trs (cons (list "PATAMAR" (strcat "PATAMAR " (itoa (1+ (length (vl-remove-if 'es:lance-p trs)))))
                                (es:f (cadddr x)) ES:MHP (es:f des) "0")
                          trs)
                des 0.0))
         (ult
          (if (<= (abs (- (cadddr x) pm)) (* 0.35 pm))
            (setq nh (1+ nh) sh (+ sh (cadddr x)))))
         (t (setq nh (1+ nh) sh (+ sh (cadddr x)))))
       (setq i (1+ i)))
     (setq pat nil)
     (es:imp-fecha)
     (setq trs (reverse trs))
     ;; espessuras: laje inclinada paralela ao lance / fundo do patamar
     (setq gs (es:geo trs) r nil)
     (foreach g gs
       (setq best nil)
       (foreach sg segs
         (setq xm (* 0.5 (+ (car (car sg)) (car (cadr sg)))) ym (* 0.5 (+ (cadr (car sg)) (cadr (cadr sg))))
               d  (- (car (cadr sg)) (car (car sg))))
         (if (and (>= (- xm (car o)) (- (nth 1 g) 1.0)) (<= (- xm (car o)) (+ (nth 2 g) 1.0))
                  (> (abs d) 0.5))
           (progn
             (setq b (/ (- (cadr (cadr sg)) (cadr (car sg))) d))
             (if (= (car g) "L")
               (if (< (abs (- b (nth 6 g))) (* 0.05 (max 0.2 (nth 6 g))))
                 (progn
                   ;; distancia vertical da linha dos cantos internos -> perpendicular
                   (setq y (- (+ (cadr o) (nth 3 g) (* (- (- xm (car o)) (nth 1 g)) (nth 6 g))) ym)
                         cs (cos (atan (nth 6 g))))
                   (if (and (> y 1.0) (or (null best) (< (* y cs) best))) (setq best (* y cs)))))
               (if (< (abs b) 0.02)
                 (progn
                   (setq y (- (+ (cadr o) (nth 11 g)) ym))
                   (if (and (> y 1.0) (or (null best) (< y best))) (setq best y))))))))
       (setq trx (nth 10 g))
       (if best
         (setq trx (if (= (car g) "L") (es:setnth trx 6 (es:f best)) (es:setnth trx 3 (es:f best)))))
       (setq r (cons trx r)))
     (list (reverse r) o sgn em pm))
  )
)

;;; ==========================================================================
;;;  8.  COMANDOS
;;; ==========================================================================

;;; ponto (ENTER = dflt; ESC = nil)
(defun es:pede-ponto (msg dflt / r)
  (setq r (vl-catch-all-apply 'getpoint (list msg)))
  (cond ((vl-catch-all-error-p r) nil)
        ((null r) dflt)
        (t r))
)

;;; desenha / refaz os desenhos marcados.  ors = origens guardadas (edicao);
;;; londef = origem sugerida para o corte longitudinal (ESCADACORTE)
(defun es:gera (id ors londef / gs novos o feitos)
  (setq ES:ETAPA "preparo")
  (es:prepara)
  (es:unidades)
  (setq gs (es:geo ES:TRE) novos nil feitos nil)
  (foreach v (list (list "PLA" ES:DPLA "\nPLANTA DE FORMAS - ponto do inicio do 1.o lance, no eixo <nao desenhar>: " nil)
                   (list "LON" ES:DLON (if londef
                                         "\nCORTE LONGITUDINAL - inicio da escada, no nivel inicial <ENTER = sobre o corte selecionado>: "
                                         "\nCORTE LONGITUDINAL - inicio da escada, no nivel inicial <nao desenhar>: ")
                         londef)
                   (list "TRA" ES:DTRA "\nCORTE A-A - centro da face inferior da laje <nao desenhar>: " nil))
    (setq ES:ETAPA (strcat "desenho " (car v)) o nil)
    (if (= (cadr v) "1")
      (progn
        (setq o (es:origem ors (car v)))
        (if (null o) (setq o (es:pede-ponto (caddr v) (cadddr v))))
        (if o
          (progn
            (es:desenha-view id (car v) o gs)
            (setq novos (cons (cons (car v) (es:p2 o)) novos) feitos (cons (car v) feitos)))
          (es:apaga-des id (car v))))
      (es:apaga-des id (car v)))
  )
  (setq ES:ETAPA "gravar")
  (es:reg-grava id (es:dados (reverse novos)))
  (princ (strcat "\nESCADA " ES:NOME " (" id "): " (itoa (length feitos)) " desenho(s)."
                 "  Para alterar: ESCADAEDIT e clique num dos desenhos."))
  feitos
)

(defun es:undo-ini ( / doc)
  (setq doc (vla-get-ActiveDocument (vlax-get-acad-object)))
  (vl-catch-all-apply 'vla-StartUndoMark (list doc))
  doc
)
(defun es:undo-fim (doc) (if doc (vl-catch-all-apply 'vla-EndUndoMark (list doc))))

(defun c:ESCADA ( / *error* doc)
  (defun *error* (msg)
    (if (and msg (not (wcmatch (strcase msg) "*CANCEL*,*QUIT*,*EXIT*")))
      (princ (strcat "\n*** Erro: " msg (if ES:ETAPA (strcat "  [etapa: " ES:ETAPA "]") ""))))
    (es:undo-fim doc) (setq ES:ID nil ES:GRP nil) (princ))
  (setq ES:ETAPA "janela")
  (if (es:roda 'es:janela nil "janela")
    (progn
      (setq doc (es:undo-ini))
      (es:roda 'es:gera (list (es:novo-id) nil nil) "desenhando")
      (es:undo-fim doc))
    (princ "\nCancelado."))
  (princ)
)

(defun c:ESCADAEDIT ( / *error* doc s id d ors)
  (defun *error* (msg)
    (if (and msg (not (wcmatch (strcase msg) "*CANCEL*,*QUIT*,*EXIT*")))
      (princ (strcat "\n*** Erro: " msg (if ES:ETAPA (strcat "  [etapa: " ES:ETAPA "]") ""))))
    (es:undo-fim doc) (setq ES:ID nil ES:GRP nil) (princ))
  (setq s (entsel "\nClique num desenho da escada (planta ou corte): "))
  (cond
    ((null s) (princ "\nNada selecionado."))
    ((null (setq id (car (es:id-ent (car s))))) (princ "\nIsso nao e um desenho da ESCADA."))
    ((null (setq d (es:reg-le id))) (princ (strcat "\nOs dados da escada " id " nao foram encontrados.")))
    (t
     (setq ors (es:carrega d))
     (if (es:roda 'es:janela nil "janela")
       (progn
         (setq doc (es:undo-ini))
         (es:roda 'es:gera (list id ors nil) (strcat "editando " id))
         (es:undo-fim doc))
       (princ "\nSem alteracoes.")))
  )
  (princ)
)

(defun c:ESCADACORTE ( / *error* doc u e ss i segs r)
  (defun *error* (msg)
    (if (and msg (not (wcmatch (strcase msg) "*CANCEL*,*QUIT*,*EXIT*")))
      (princ (strcat "\n*** Erro: " msg (if ES:ETAPA (strcat "  [etapa: " ES:ETAPA "]") ""))))
    (es:undo-fim doc) (setq ES:ID nil ES:GRP nil) (princ))
  (es:defaults)
  (initget "Papel Metros Centimetros Milimetros")
  (setq u (getkword (strcat "\nO desenho esta em [Papel/Metros/Centimetros/Milimetros] <"
                            (nth ES:UNI '("Papel" "Metros" "Centimetros" "Milimetros")) ">: ")))
  (if u (setq ES:UNI (cond ((= u "Papel") 0) ((= u "Metros") 1) ((= u "Centimetros") 2) (t 3))))
  (if (= ES:UNI 0)
    (progn
      (initget 6)
      (if (setq e (getreal (strcat "\nEscala do desenho 1:<" ES:ESC ">: "))) (setq ES:ESC (es:f e)))))
  (es:unidades)
  (princ "\nSelecione as linhas / polilinhas do CORTE da escada (perfil dos degraus ou contorno): ")
  (if (setq ss (ssget '((0 . "LINE,LWPOLYLINE,POLYLINE"))))
    (progn
      (setq i 0 segs nil)
      (while (< i (sslength ss))
        (setq segs (append segs (es:segs-ent (ssname ss i))) i (1+ i)))
      (setq r (es:roda 'es:importa (list segs) "lendo o corte"))
      (cond
        ((null r) nil)
        ((= (type r) 'STR) (alert r))
        (t
         (setq ES:TRE (car r)
               ES:APO (list (list "V1" "0" "14" "40" "0" "0")
                            (list "V2" "0" "14" "40" (itoa (1- (* 2 (length ES:TRE)))) "0"))
               ES:SEL-T 0 ES:SEL-A 0)
         (princ (strcat "\nReconhecidos " (itoa (length ES:TRE)) " trecho(s): espelho ~"
                        (es:f (nth 3 r)) " cm, piso ~" (es:f (nth 4 r)) " cm."))
         (if (or (< (nth 3 r) 8.0) (> (nth 3 r) 30.0))
           (princ "\n  ATENCAO: espelho fora de 8 a 30 cm - confira as UNIDADES / ESCALA."))
         (if (es:roda 'es:janela nil "janela")
           (progn
             (setq doc (es:undo-ini))
             (es:roda 'es:gera
                      (list (es:novo-id) nil
                            (if (> (caddr r) 0.0) (es:mul (cadr r) (/ 1.0 ES:UC))))
                      "desenhando")
             (es:undo-fim doc))
           (princ "\nCancelado.")))
      )
    )
    (princ "\nNada selecionado.")
  )
  (princ)
)

(princ (strcat "\nESCADA v" ES:VERSAO " carregada (Baluarte).  Comandos: ESCADA (nova), "
               "ESCADACORTE (a partir de um corte desenhado), ESCADAEDIT (editar)."))
(princ)
