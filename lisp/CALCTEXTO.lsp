;;; ===========================================================================
;;;  CALCTEXTO.LSP  -  Operacoes matematicas com textos numericos no AutoCAD
;;; ===========================================================================
;;;
;;;  Le numeros contidos em TEXT, MTEXT, atributos de bloco, cotas e
;;;  multileaders, aceitando VIRGULA ou PONTO como separador decimal
;;;  (ex.: "12,50"  "12.50"  "1.234,56"  "1,234.56"  "Area = 35,40 m2").
;;;
;;;  COMANDOS
;;;    CT        - Menu com todas as opcoes abaixo
;;;    CTSUB     - Seleciona o VALOR TOTAL e depois os textos a SUBTRAIR dele
;;;    CTSOMA    - Soma todos os textos selecionados
;;;    CTMULT    - Multiplica todos os textos selecionados
;;;    CTDIV     - Divide um valor (dividendo) por outro (divisor)
;;;    CTCALC    - Calculadora em cadeia: valor [+ - * /] valor [+ - * /] ...
;;;    CTCONFIG  - Casas decimais, separador do resultado, milhar e leitura
;;;
;;;  Em toda selecao de valor unico tambem e possivel DIGITAR um numero
;;;  (opcao "Digitar").
;;;
;;;  Ao final o resultado e mostrado na linha de comando e voce escolhe:
;;;    Inserir    - cria um novo texto com o resultado (copia camada, estilo,
;;;                 altura e rotacao do texto de referencia)
;;;    Substituir - troca o numero de um texto existente pelo resultado,
;;;                 mantendo prefixos/sufixos (ex.: "Area = 12,50 m2")
;;;    Nenhum     - apenas mostra o resultado
;;;
;;;  Carregar: comando APPLOAD (ou arrastar o arquivo para o desenho).
;;; ===========================================================================

(vl-load-com)

;;; ---------------------------------------------------------------------------
;;;  Configuracao (gravada no registro do AutoCAD via setenv)
;;; ---------------------------------------------------------------------------

(defun ct:prec (/ v)
  (setq v (getenv "CT_PREC"))
  (if v (max 0 (min 8 (atoi v))) 2)
)

;; separador decimal do resultado: "," ou "."
(defun ct:sep (/ v)
  (setq v (getenv "CT_SEP"))
  (if (member v '("," ".")) v ",")
)

;; usa separador de milhar no resultado?
(defun ct:milhar-p ()
  (= (getenv "CT_MILHAR") "1")
)

;; modo de leitura: "A" automatico, "V" virgula decimal, "P" ponto decimal
(defun ct:leitura (/ v)
  (setq v (getenv "CT_LEITURA"))
  (if (member v '("A" "V" "P")) v "A")
)

(defun ct:leitura-nome ()
  (cdr (assoc (ct:leitura) '(("A" . "Automatico") ("V" . "Virgula") ("P" . "Ponto"))))
)

;;; ---------------------------------------------------------------------------
;;;  Utilitarios de string
;;; ---------------------------------------------------------------------------

(defun ct:digito-p (c)
  (and c (/= c "") (<= 48 (ascii c) 57))
)

;; quantas vezes o caractere c aparece em s
(defun ct:conta (c s / n p)
  (setq n 0 p 0)
  (while (setq p (vl-string-search c s p))
    (setq n (1+ n) p (1+ p))
  )
  n
)

;; remove todas as ocorrencias do caractere c em s
(defun ct:remove-char (c s)
  (while (vl-string-search c s)
    (setq s (vl-string-subst "" c s))
  )
  s
)

;; remove codigos de formatacao de MTEXT (\P, \H2.5x; {\fArial|b0;...} etc.)
(defun ct:limpa-mtext (s / out i n c d j)
  (setq out "" i 1 n (strlen s))
  (while (<= i n)
    (setq c (substr s i 1))
    (cond
      ((= c "\\")
       (setq d (substr s (1+ i) 1))
       (cond
         ((member d '("\\" "{" "}"))
          (setq out (strcat out d) i (+ i 2)))
         ((member d '("P" "N" "~"))
          (setq out (strcat out " ") i (+ i 2)))
         ((wcmatch d "[fFHhCcAaTtQqWwpS]")
          ;; codigo com parametros terminado em ";"
          (if (setq j (vl-string-search ";" s i))
            (setq i (+ j 2))
            (setq i (1+ n))))
         (t (setq i (+ i 2)))       ; \L \l \O \o \K \k ...
       ))
      ((member c '("{" "}"))
       (setq i (1+ i)))
      (t
       (setq out (strcat out c) i (1+ i)))
    )
  )
  out
)

;; remove codigos %%c %%d %%p %%nnn etc.
(defun ct:limpa-percent (s / out i n)
  (setq out "" i 1 n (strlen s))
  (while (<= i n)
    (if (= (substr s i 2) "%%")
      (if (ct:digito-p (substr s (+ i 2) 1))
        (setq i (+ i 5))                         ; %%nnn
        (setq out (strcat out " ") i (+ i 3)))   ; %%c %%d %%p %%u %%o %%%
      (setq out (strcat out (substr s i 1)) i (1+ i))
    )
  )
  out
)

(defun ct:texto-limpo (raw tipo)
  (if (member tipo '("MTEXT" "MULTILEADER"))
    (setq raw (ct:limpa-mtext raw))
  )
  (ct:limpa-percent raw)
)

;;; ---------------------------------------------------------------------------
;;;  Leitura de numeros
;;; ---------------------------------------------------------------------------

;; Retorna o primeiro "token" numerico da string (ex.: "-1.234,56") ou nil
(defun ct:extrai-token (s / n i ini fim tok)
  (setq n (strlen s) i 1)
  (while (and (<= i n) (not (ct:digito-p (substr s i 1))))
    (setq i (1+ i))
  )
  (if (<= i n)
    (progn
      (setq ini i)
      ;; sinal negativo: "-5", "= -5", "(-5)"  (mas nao "P-3")
      (if (and (> ini 1)
               (= (substr s (1- ini) 1) "-")
               (or (= ini 2) (not (wcmatch (substr s (- ini 2) 1) "@"))))
        (setq ini (1- ini))
      )
      (setq fim i)
      (while (and (<= fim n)
                  (or (ct:digito-p (substr s fim 1))
                      (member (substr s fim 1) '("." ","))))
        (setq fim (1+ fim))
      )
      (setq tok (substr s ini (- fim ini)))
      ;; descarta separadores no final ("12,5." -> "12,5")
      (while (member (substr tok (strlen tok) 1) '("." ","))
        (setq tok (substr tok 1 (1- (strlen tok))))
      )
      tok
    )
  )
)

;; Converte o token em numero real, detectando o separador decimal
(defun ct:token->num (tok / neg modo nv np dec mil p r)
  (setq neg (= (substr tok 1 1) "-"))
  (if neg (setq tok (substr tok 2)))
  (setq modo (ct:leitura)
        nv   (ct:conta "," tok)
        np   (ct:conta "." tok))
  (cond
    ((= modo "V") (setq dec "," mil "."))
    ((= modo "P") (setq dec "." mil ","))
    ;; os dois aparecem: o ULTIMO e o decimal ("1.234,56" / "1,234.56")
    ((and (> nv 0) (> np 0))
     (if (> (vl-string-position (ascii ",") tok nil T)
            (vl-string-position (ascii ".") tok nil T))
       (setq dec "," mil ".")
       (setq dec "." mil ",")))
    ;; o mesmo separador repetido e milhar ("1.234.567" / "1,234,567")
    ((> nv 1) (setq dec "." mil ","))
    ((> np 1) (setq dec "," mil "."))
    ;; uma unica virgula ou um unico ponto: decimal
    ((= nv 1) (setq dec "," mil "."))
    (t        (setq dec "." mil ","))
  )
  (setq tok (ct:remove-char mil tok))
  (setq tok (vl-string-translate dec "." tok))
  ;; se ainda houver mais de um ponto, considera so ate o segundo
  (if (and (setq p (vl-string-search "." tok))
           (setq p (vl-string-search "." tok (1+ p))))
    (setq tok (substr tok 1 p))
  )
  (if (= (substr tok 1 1) ".") (setq tok (strcat "0" tok)))
  (if (setq r (distof tok 2))
    (if neg (- r) r)
  )
)

;; string -> (numero token) ou nil
(defun ct:valor-str (s / tok n)
  (if (and s
           (setq tok (ct:extrai-token s))
           (setq n (ct:token->num tok)))
    (list n tok)
  )
)

;; conteudo "cru" do texto (com codigos de formatacao)
(defun ct:string-bruta (en / obj r)
  (setq obj (vlax-ename->vla-object en))
  (if (vlax-property-available-p obj 'TextString)
    (progn
      (setq r (vl-catch-all-apply 'vla-get-textstring (list obj)))
      (if (not (vl-catch-all-error-p r)) r)
    )
  )
)

;; entidade -> (numero ename) ou nil
(defun ct:valor-ent (en / ed tipo s r m f)
  (setq ed (entget en) tipo (cdr (assoc 0 ed)))
  (cond
    ((member tipo '("TEXT" "MTEXT" "ATTRIB" "ATTDEF" "MULTILEADER"))
     (if (and (setq s (ct:string-bruta en))
              (setq r (ct:valor-str (ct:texto-limpo s tipo))))
       (list (car r) en)))
    ((= tipo "DIMENSION")
     (setq s (cdr (assoc 1 ed)) m (cdr (assoc 42 ed)))
     (cond
       ;; texto da cota substituido manualmente
       ((and s (/= s "") (not (vl-string-search "<>" s))
             (setq r (ct:valor-str (ct:texto-limpo s "MTEXT"))))
        (list (car r) en))
       (m
        (if (member (logand 7 (cdr (assoc 70 ed))) '(2 5))
          (setq m (* m (/ 180.0 pi)))                     ; cota angular -> graus
          (progn
            (setq f (vl-catch-all-apply 'vla-get-linearscalefactor
                                        (list (vlax-ename->vla-object en))))
            (if (numberp f) (setq m (* m f)))))
        (list m en))))
  )
)

;;; ---------------------------------------------------------------------------
;;;  Formatacao do resultado
;;; ---------------------------------------------------------------------------

(defun ct:agrupa-milhar (int sep / res)
  (setq res "")
  (while (> (strlen int) 3)
    (setq res (strcat sep (substr int (- (strlen int) 2)) res)
          int (substr int 1 (- (strlen int) 3)))
  )
  (strcat int res)
)

(defun ct:formata (v / dz s neg pos int dec)
  (setq dz (getvar "DIMZIN"))
  (setvar "DIMZIN" 0)                       ; mantem zeros a direita
  (setq s (rtos (abs v) 2 (ct:prec)))
  (setvar "DIMZIN" dz)
  (setq neg (and (< v 0) (/= (distof s 2) 0.0)))
  (if (setq pos (vl-string-search "." s))
    (setq int (substr s 1 pos) dec (substr s (+ pos 2)))
    (setq int s dec nil)
  )
  (if (ct:milhar-p)
    (setq int (ct:agrupa-milhar int (if (= (ct:sep) ",") "." ",")))
  )
  (strcat (if neg "-" "") int (if dec (strcat (ct:sep) dec) ""))
)

;;; ---------------------------------------------------------------------------
;;;  Selecao
;;; ---------------------------------------------------------------------------

(setq *ct:destacados* nil)

(defun ct:destaca (en)
  (if (not (vl-catch-all-error-p (vl-catch-all-apply 'redraw (list en 3))))
    (setq *ct:destacados* (cons en *ct:destacados*))
  )
)

(defun ct:limpa-destaque ()
  (foreach en *ct:destacados*
    (vl-catch-all-apply 'redraw (list en 4))
  )
  (setq *ct:destacados* nil)
)

;; trata o retorno do nentsel: se clicou dentro de uma cota ou multileader,
;; usa o objeto "pai"
(defun ct:ent-da-selecao (sel / en pai)
  (setq en (car sel))
  (if (and (= (length sel) 4)
           (/= (cdr (assoc 0 (entget en))) "ATTRIB")
           (setq pai (car (last sel)))
           (member (cdr (assoc 0 (entget pai))) '("DIMENSION" "MULTILEADER")))
    (setq en pai)
  )
  en
)

;; Pede UM valor (clicando num texto ou digitando).
;; Retorna (numero ename) - ename e nil se digitado - ou nil se Enter.
(defun ct:pega-valor (msg / sel en v ok s)
  (while (not ok)
    (setvar "ERRNO" 0)
    (initget "Digitar")
    (setq sel (nentsel (strcat msg " ou [Digitar]: ")))
    (cond
      ((= sel "Digitar")
       (setq s (getstring T "\nDigite o valor: "))
       (if (setq v (ct:valor-str s))
         (setq v (list (car v) nil) ok T)
         (princ "\nValor invalido."))
      )
      ((null sel)
       (if (= (getvar "ERRNO") 7)
         (princ "\nNada selecionado, tente novamente.")
         (setq v nil ok T))                       ; Enter = sair
      )
      ((setq v (ct:valor-ent (setq en (ct:ent-da-selecao sel))))
       (ct:destaca en)
       (setq ok T)
      )
      (t
       (princ "\nO objeto selecionado nao contem numero (use TEXT, MTEXT, atributo, cota ou multileader).")
      )
    )
  )
  v
)

;; Selecao de VARIOS textos. Retorna lista de (numero ename).
(defun ct:seleciona-varios (msg excluir / ss i en v lst ign)
  (princ msg)
  (setq ign 0)
  (if (setq ss (ssget '((0 . "TEXT,MTEXT,MULTILEADER,DIMENSION"))))
    (progn
      (setq i 0)
      (repeat (sslength ss)
        (setq en (ssname ss i) i (1+ i))
        (cond
          ((and excluir (equal en excluir))
           (princ "\n(O texto do valor total estava na selecao e foi ignorado.)"))
          ((setq v (ct:valor-ent en))
           (ct:destaca en)
           (setq lst (cons v lst)))
          (t (setq ign (1+ ign)))
        )
      )
      (if (> ign 0)
        (princ (strcat "\n" (itoa ign) " objeto(s) sem numero foram ignorados.")))
    )
  )
  (reverse lst)
)

(defun ct:lista-valores (lst sinal)
  (foreach v lst
    (princ (strcat "\n   " sinal " " (ct:formata (car v))))
  )
)

;;; ---------------------------------------------------------------------------
;;;  Saida do resultado
;;; ---------------------------------------------------------------------------

(defun ct:aninhado-p (en / own nome)
  (and (setq own (cdr (assoc 330 (entget en))))
       (= (cdr (assoc 0 (entget own))) "BLOCK_RECORD")
       (setq nome (cdr (assoc 2 (entget own))))
       (not (wcmatch (strcase nome) "`*MODEL_SPACE,`*PAPER_SPACE*")))
)

(defun ct:insere-texto (txt ref / pt ed alt est cam rot)
  (setq alt (getvar "TEXTSIZE")
        est (getvar "TEXTSTYLE")
        cam (getvar "CLAYER")
        rot (angle '(0 0) (getvar "UCSXDIR")))
  (if (and ref
           (setq ed (entget ref))
           (member (cdr (assoc 0 ed)) '("TEXT" "MTEXT" "ATTRIB")))
    (setq alt (cond ((cdr (assoc 40 ed))) (alt))
          est (cond ((cdr (assoc 7 ed))) (est))
          cam (cond ((cdr (assoc 8 ed))) (cam))
          rot (cond ((cdr (assoc 50 ed))) (rot)))
  )
  (if (tblsearch "LAYER" cam) nil (setq cam (getvar "CLAYER")))
  (if (setq pt (getpoint "\nPonto de insercao do texto: "))
    (if (entmake (list '(0 . "TEXT")
                       (cons 8 cam)
                       (cons 7 est)
                       (cons 10 (trans pt 1 0))
                       (cons 40 alt)
                       (cons 50 rot)
                       (cons 1 txt)))
      (princ (strcat "\nTexto \"" txt "\" inserido."))
      (princ "\nNao foi possivel criar o texto.")
    )
  )
)

;; troca o numero do texto pelo resultado, mantendo o restante da string
(defun ct:substitui (en txt / tipo obj raw tok novo)
  (setq tipo (cdr (assoc 0 (entget en)))
        obj  (vlax-ename->vla-object en))
  (cond
    ((= tipo "DIMENSION")
     (vla-put-textoverride obj txt)
     (princ "\nTexto da cota substituido.")
     T)
    ((and (member tipo '("TEXT" "MTEXT" "ATTRIB" "ATTDEF" "MULTILEADER"))
          (setq raw (ct:string-bruta en)))
     (setq tok (ct:extrai-token (ct:texto-limpo raw tipo)))
     (setq novo (if (and tok (vl-string-search tok raw))
                  (vl-string-subst txt tok raw)
                  txt))
     (vla-put-textstring obj novo)
     (vla-update obj)
     (if (ct:aninhado-p en)
       (vla-regen (vla-get-activedocument (vlax-get-acad-object)) acActiveViewport))
     (princ "\nTexto substituido.")
     T)
    (t (princ "\nObjeto nao suportado para substituicao.") nil)
  )
)

(defun ct:saida (valor ref / txt op sel en ok)
  (setq txt (ct:formata valor))
  (princ (strcat "\n>>> RESULTADO = " txt))
  (initget "Inserir Substituir Nenhum")
  (setq op (getkword "\nO que fazer com o resultado? [Inserir/Substituir/Nenhum] <Inserir>: "))
  (cond
    ((or (null op) (= op "Inserir"))
     (ct:insere-texto txt ref))
    ((= op "Substituir")
     (while (not ok)
       (setvar "ERRNO" 0)
       (setq sel (nentsel (if ref
                            "\nSelecione o texto a substituir <texto de referencia>: "
                            "\nSelecione o texto a substituir: ")))
       (cond
         (sel (setq en (ct:ent-da-selecao sel) ok T))
         ((= (getvar "ERRNO") 7) (princ "\nNada selecionado, tente novamente."))
         (t (setq en ref ok T))
       )
     )
     (if en (ct:substitui en txt)))
  )
)

;;; ---------------------------------------------------------------------------
;;;  Rotinas
;;; ---------------------------------------------------------------------------

;; Executa uma rotina com tratamento de erro e UNDO agrupado
(defun ct:executa (fun / *error* doc)
  (setq doc (vla-get-activedocument (vlax-get-acad-object)))
  (defun *error* (msg)
    (ct:limpa-destaque)
    (vla-endundomark doc)
    (if (not (wcmatch (strcase msg) "*BREAK*,*CANCEL*,*EXIT*"))
      (princ (strcat "\nErro: " msg)))
    (princ)
  )
  (vla-startundomark doc)
  (apply fun nil)
  (ct:limpa-destaque)
  (vla-endundomark doc)
  (princ)
)

;; VALOR TOTAL - (soma dos textos selecionados)
(defun ct:subtrair (/ tot lst soma res)
  (if (setq tot (ct:pega-valor "\nSelecione o texto do VALOR TOTAL"))
    (progn
      (princ (strcat "\nValor total: " (ct:formata (car tot))))
      (if (setq lst (ct:seleciona-varios "\nSelecione os textos a SUBTRAIR do total: " (cadr tot)))
        (progn
          (ct:lista-valores lst "-")
          (setq soma (apply '+ (mapcar 'car lst))
                res  (- (car tot) soma))
          (princ (strcat "\n" (ct:formata (car tot)) " - " (ct:formata soma)
                         " (" (itoa (length lst)) " valor(es)) = " (ct:formata res)))
          (ct:saida res (cadr tot))
        )
        (princ "\nNenhum valor para subtrair.")
      )
    )
  )
)

(defun ct:somar (/ lst res)
  (if (setq lst (ct:seleciona-varios "\nSelecione os textos a SOMAR: " nil))
    (progn
      (ct:lista-valores lst "+")
      (setq res (apply '+ (mapcar 'car lst)))
      (princ (strcat "\nSoma de " (itoa (length lst)) " valor(es) = " (ct:formata res)))
      (ct:saida res (cadr (car lst)))
    )
    (princ "\nNenhum valor numerico selecionado.")
  )
)

(defun ct:multiplicar (/ lst res)
  (if (setq lst (ct:seleciona-varios "\nSelecione os textos a MULTIPLICAR: " nil))
    (progn
      (ct:lista-valores lst "x")
      (setq res (apply '* (mapcar 'car lst)))
      (princ (strcat "\nProduto de " (itoa (length lst)) " valor(es) = " (ct:formata res)))
      (ct:saida res (cadr (car lst)))
    )
    (princ "\nNenhum valor numerico selecionado.")
  )
)

(defun ct:dividir (/ a b res)
  (if (and (setq a (ct:pega-valor "\nSelecione o DIVIDENDO (numerador)"))
           (setq b (ct:pega-valor "\nSelecione o DIVISOR (denominador)")))
    (if (equal (car b) 0.0 1e-12)
      (princ "\nErro: divisao por zero.")
      (progn
        (setq res (/ (car a) (car b)))
        (princ (strcat "\n" (ct:formata (car a)) " / " (ct:formata (car b))
                       " = " (ct:formata res)))
        (ct:saida res (cadr a))
      )
    )
  )
)

;; pede o operador da calculadora em cadeia; nil = finalizar
(defun ct:pede-operador (/ op ok)
  (while (not ok)
    (setq op (vl-string-trim " " (getstring "\nOperacao [+ - * /] <Enter = finalizar>: ")))
    (cond
      ((= op "") (setq op nil ok T))
      ((member op '("+" "-" "*" "/")) (setq ok T))
      ((member op '("x" "X")) (setq op "*" ok T))
      (t (princ "\nOperacao invalida. Use + - * ou /."))
    )
  )
  op
)

;; Calculadora em cadeia (avalia da esquerda para a direita)
(defun ct:calculadora (/ v res ref op hist)
  (if (setq v (ct:pega-valor "\nSelecione o PRIMEIRO valor"))
    (progn
      (setq res  (car v)
            ref  (cadr v)
            hist (ct:formata res))
      (while (and (setq op (ct:pede-operador))
                  (setq v (ct:pega-valor "\nSelecione o PROXIMO valor")))
        (cond
          ((and (= op "/") (equal (car v) 0.0 1e-12))
           (princ "\nDivisao por zero ignorada."))
          (t
           (setq res (cond ((= op "+") (+ res (car v)))
                           ((= op "-") (- res (car v)))
                           ((= op "*") (* res (car v)))
                           ((= op "/") (/ res (car v))))
                 hist (strcat hist " " op " " (ct:formata (car v))))
           (princ (strcat "\n" hist " = " (ct:formata res))))
        )
      )
      (ct:saida res ref)
    )
  )
)

(defun ct:configurar (/ p k)
  (princ (strcat "\nConfiguracao atual: casas decimais = " (itoa (ct:prec))
                 " | separador do resultado = \"" (ct:sep) "\""
                 " | milhar = " (if (ct:milhar-p) "Sim" "Nao")
                 " | leitura = " (ct:leitura-nome)))
  (initget 4)
  (if (setq p (getint (strcat "\nCasas decimais (0 a 8) <" (itoa (ct:prec)) ">: ")))
    (setenv "CT_PREC" (itoa (min p 8)))
  )
  (initget "Virgula Ponto")
  (if (setq k (getkword (strcat "\nSeparador decimal do resultado [Virgula/Ponto] <"
                                (if (= (ct:sep) ",") "Virgula" "Ponto") ">: ")))
    (setenv "CT_SEP" (if (= k "Virgula") "," "."))
  )
  (initget "Sim Nao")
  (if (setq k (getkword (strcat "\nUsar separador de milhar no resultado? [Sim/Nao] <"
                                (if (ct:milhar-p) "Sim" "Nao") ">: ")))
    (setenv "CT_MILHAR" (if (= k "Sim") "1" "0"))
  )
  (initget "Automatico Virgula Ponto")
  (if (setq k (getkword (strcat "\nSeparador decimal na LEITURA dos textos [Automatico/Virgula/Ponto] <"
                                (ct:leitura-nome) ">: ")))
    (setenv "CT_LEITURA" (substr k 1 1))
  )
  (princ "\nConfiguracao gravada.")
)

;;; ---------------------------------------------------------------------------
;;;  Comandos
;;; ---------------------------------------------------------------------------

(defun c:CTSUB    () (ct:executa 'ct:subtrair))
(defun c:CTSOMA   () (ct:executa 'ct:somar))
(defun c:CTMULT   () (ct:executa 'ct:multiplicar))
(defun c:CTDIV    () (ct:executa 'ct:dividir))
(defun c:CTCALC   () (ct:executa 'ct:calculadora))
(defun c:CTCONFIG () (ct:configurar) (princ))

(defun c:CT (/ op)
  (initget "Somar sUbtrair Multiplicar Dividir CAlculadora COnfigurar")
  (setq op (getkword "\nOperacao com textos [Somar/sUbtrair/Multiplicar/Dividir/CAlculadora/COnfigurar] <sUbtrair>: "))
  (cond
    ((= op "Somar")       (c:CTSOMA))
    ((= op "Multiplicar") (c:CTMULT))
    ((= op "Dividir")     (c:CTDIV))
    ((= op "CAlculadora") (c:CTCALC))
    ((= op "COnfigurar")  (c:CTCONFIG))
    (t                    (c:CTSUB))
  )
  (princ)
)

(princ "\nCALCTEXTO carregado. Comandos: CT (menu), CTSUB, CTSOMA, CTMULT, CTDIV, CTCALC, CTCONFIG")
(princ)
