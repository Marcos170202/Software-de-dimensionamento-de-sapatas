;;; ==========================================================================
;;;  ESCADA.lsp
;;;  FORMAS E ARMADURA DE ESCADAS DE CONCRETO ARMADO  --  v1.6
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
;;;    ESCADASECAO ... CORTE EM QUALQUER POSICAO: clique na planta de formas,
;;;                    trace a linha de corte (2 pontos), clique o lado para
;;;                    onde o corte olha, de o nome (B, C...) e o ponto do
;;;                    desenho.  O corte e calculado no MODELO 3D da escada.
;;;    ESCADAVIGA .... clique SOBRE uma viga / apoio na planta de formas:
;;;                    Mover (com o mouse, ponto base e novo ponto), Inverter
;;;                    (viga invertida <-> normal), Espelhar (outro lado),
;;;                    Girar (graus), Desnivel (topo, cm), Estender, Editar.
;;;                    Tudo e refeito (planta, cortes, armadura).
;;;    ESCADAGRAF .... EDICAO GRAFICA: quadrados (alcas) nos desenhos; clique,
;;;                    arraste e clique (ou digite o valor + ENTER):
;;;                    desenvolvimento - fim do lance (+/- degraus), 1.o degrau
;;;                    (piso x espelho), espessuras, fim do patamar, posicao /
;;;                    altura / largura das vigas; planta - fim dos trechos,
;;;                    vigas (mover, pontas = extensoes), linhas de corte;
;;;                    armadura - inicio / fim / meio de cada barra (gruda nos
;;;                    pontos da escada); CORTES - vigas (altura, desnivel,
;;;                    mover, largura), lajes de piso, espessuras dos trechos
;;;                    e as pontas da linha de corte.  Teclas: A apagar, E editar (janela),
;;;                    D dividir lance (corta o lance e poe um patamar), C novo
;;;                    corte, N nova barra (2 cliques no corte armado), R
;;;                    armadura automatica, Q quantitativo, J janela, Z desfazer.
;;;    ESCADAQTD ..... QUANTITATIVO de concreto (m3) e formas (m2: fundo,
;;;                    laterais, espelhos) por trecho e por viga, aco (kgf) e
;;;                    taxa; na linha de comando e na tabela do desenho.
;;;    ESCADAEDIT .... clique em qualquer desenho de uma escada: a janela abre
;;;                    com todos os dados e TODOS os desenhos (planta e cortes)
;;;                    sao refeitos no lugar (mesmo que tenham sido movidos)
;;;
;;;  --------------------------------------------------------------------
;;;  MODELO DA ESCADA
;;;  --------------------------------------------------------------------
;;;  A escada e uma sequencia de TRECHOS, de baixo para cima:
;;;   - LANCE ...... N espelhos de altura e, piso p, espessura h (medida
;;;                  perpendicular a laje inclinada).  TIPO ESTRUTURAL: laje
;;;                  inclinada (convencional) ou PLISSADA (laje dobrada: o fundo
;;;                  acompanha os degraus, placa de espessura h no piso e no
;;;                  espelho; a placa do ultimo espelho desce no patamar).  "Pisos no lance":
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
;;;  MODELO 3D: a planta (posicao, orientacao e giro de cada trecho) mais os
;;;  niveis formam os solidos da escada (lances, patamares, vigas, lajes de
;;;  piso, paredes, apoios laterais).  A laje inclinada continua sob o patamar
;;;  ate a quebra (encontro com o fundo do patamar).
;;;
;;;  DESENHOS (cada um e um BLOCO: mova a vontade; ESCADAEDIT refaz no lugar)
;;;   - PLANTA DE FORMAS: lances com os degraus numerados, linha de subida
;;;     (SOBE), patamares com nome, espessura e nivel, apoios (tracejados)
;;;     com nome, cotas e as LINHAS DE CORTE (A-A, B-B, ...).
;;;   - CORTES (A-A automatico, transversal ao lance escolhido, e os tracados
;;;     com ESCADASECAO): o que o plano corta (concreto, vigas, lajes e
;;;     paredes, com a quebra da laje), as arestas VISTAS atras do plano, sem
;;;     as escondidas, nomes, espessuras, niveis dos patamares e pavimentos e
;;;     cotas ("5x28=140", "6x18=108").
;;;   - DESENVOLVIMENTO (opcional): os trechos em sequencia, como se a escada
;;;     fosse reta (util para o detalhamento da armadura).
;;;
;;;  APRESENTACAO (botao "Apresentacao..."): niveis em m (+1,26) ou em cm
;;;  (+126.00 / %%p0.00); PAVIMENTOS de referencia (ex.: NIVEL ARQUITETURA=0;
;;;  1a FIADA=310) desenhados nos cortes com o simbolo de nivel; concreto
;;;  cortado preenchido de cinza; HACHURA por patamar (planta) com LEGENDA.
;;;  Nos cortes: vigas com nome e secao ("V3A" / "14/50"), parte da viga dentro
;;;  da laje tracejada, cotas do 1.o espelho e piso, espessura perpendicular do
;;;  lance, espessura do patamar e niveis dos patamares vistos.
;;;
;;;  VIGAS DE BORDO: cada apoio pode ser transversal (atravessa o trecho) ou de
;;;  BORDA (ao longo do trecho, esquerda/direita), com EXTENSOES alem das bordas
;;;  (ex.: V3A, V4A maiores que a escada).  Posicao livre: NORMAL (topo na
;;;  laje) ou INVERTIDA (fundo na laje, sobe acima dela - na planta aparece
;;;  cheia), desnivel do topo, deslocamento lateral e ROTACAO.
;;;
;;;  SEM EMPUXO AO VAZIO (qualquer tipo de escada): nenhuma barra longitudinal
;;;  (inferior ou superior) passa dobrada por um canto em que a tracao a
;;;  empurraria para fora do concreto.  A barra e dividida no canto e as
;;;  partes sao CRUZADAS: cada uma segue reta ate lb ou ate a outra camada e,
;;;  se faltar, dobra ao longo dela para dentro da outra placa.  Vale para a
;;;  lista automatica e para as barras editadas (janela ou ESCADAGRAF).
;;;
;;;  ARMADURA (botao "Armadura..." e marcar "Detalhamento da ARMADURA"):
;;;  LISTA DE BARRAS PARAMETRIZADAS - inclua, edite, duplique, retire e
;;;  reordene.  Cada barra: tipo (longitudinal inferior / superior,
;;;  distribuicao inferior / superior), detalhe (D1, D2...), inicio e fim
;;;  presos a pontos da escada (inicio, fim, quebras, eixo de um apoio pelo
;;;  nome) + deslocamento, ponta de cada lado (reta, gancho, dobra, ancoragem
;;;  no apoio, ancoragem QUIMICA, prolongar), bitola, espacamento, quantidade.
;;;  "Gerar lista automatica" monta a lista inicial (ver secoes 10 e 11).
;;;  Desenhos: corte armado de cada detalhe (degraus numerados, inferiores
;;;  continuas, superiores tracejadas, distribuicao em bolinhas com leque),
;;;  barras desenhadas fora do corte com as pernas, PLANTA DE ARMACAO, notas,
;;;  tabela ACO / POS / BIT / QUANT / COMPRIMENTO e RESUMO DE ACO.
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

(setq ES:VERSAO    "1.6"
      ES:LAY-CORTE "EST_FormaCorte"
      ES:LAY-VISTA "EST_FormaVista"
      ES:LAY-OCULTA "EST_FormaOculta"
      ES:LAY-TXT   "EST_FormaTexto"
      ES:LAY-EIXO  "EST_FormaEixo"
      ES:LAY-NIV   "EST_Nivel"
      ES:LAY-COTA  "EST_Cota"
      ES:LAY-TIT   "EST_Titulo"
      ES:LAY-HACH  "EST_FormaHachura"
      ES:LAY-ARMP  "EST_ArmPos"
      ES:LAY-ARMN  "EST_ArmNeg"
      ES:LAY-ARMT  "EST_ArmTexto"
      ES:LAY-TAB   "T_LINHAS_GREEN"
      ES:LAY-GRADE "TAB-ESTACAS-GRADE"
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
                    "Reta - 3 lances e 2 patamares"
                    "PLISSADA reta - 1 lance"
                    "PLISSADA reta - lance / patamar / lance"
                    "PLISSADA em L - lance / patamar 90 / lance"
                    "PLISSADA em U - lance / patamar 180 / lance"
                    "PLISSADA em U - 3 lances (dois patamares 90)"
                    "Em O (quadrada) - 4 lances e 3 patamares 90"
                    "PLISSADA em O (quadrada) - 4 lances e 3 patamares 90")
      ES:TIPOS-LANCE '("Laje inclinada (convencional)"
                       "PLISSADA (laje dobrada acompanhando os degraus)")
      ;; hachuras: (nome padrao fator-de-escala); escala = fator x altura do texto
      ES:HACHURAS '(("Nenhuma" nil 0.0) ("Cinza solido" "SOLID" 1.0)
                    ("Diagonal (ANSI31)" "ANSI31" 0.4) ("Xadrez (ANSI37)" "ANSI37" 0.4)
                    ("Pontos (DOTS)" "DOTS" 32.0) ("Concreto (AR-CONC)" "AR-CONC" 0.25)
                    ("Malha (NET)" "NET" 12.0))
      ES:DIRS-APO '("Transversal (atravessa o trecho)" "Borda ESQUERDA (ao longo do trecho)"
                    "Borda DIREITA (ao longo do trecho)")
      ES:VERTS    '("Normal (topo na laje, pendurada)" "INVERTIDA (fundo na laje, para cima)")
      ES:ANCS     '("Padrao (reta / gancho)" "Ancoragem QUIMICA (furo + adesivo)")
      ES:NIVFMTS  '("Metros:  +1,26" "Centimetros:  +126.00")
      ;; bitolas (mm) e massa linear NBR 7480 (kg/m)
      ES:BITOLAS  '("5" "6.3" "8" "10" "12.5" "16" "20")
      ES:MASSAS   '(0.154 0.245 0.395 0.617 0.963 1.578 2.466)
      ;; parametros gerais guardados em cada escada (ordem fixa; novos no fim)
      ES:PARAMS   '(ES:NOME ES:NIV ES:LAR ES:POCO ES:DIR ES:UNI ES:ESC ES:ALT
                    ES:DPLA ES:DLON ES:DTRA ES:TRAL ES:LATE ES:LATD
                    ES:MTIPO ES:MDES ES:MNDG ES:MPIS ES:MHL ES:MHP ES:MLP
                    ES:NIVFMT ES:PAVS ES:SECFILL ES:LEGH ES:HESC
                    ES:FCK ES:COB ES:AIB ES:AIS ES:ASB ES:ASS ES:ADB ES:ADS ES:NEGF ES:DARM
                    ES:DQTD))

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

;;; nivel (m) no formato escolhido: metros "+1,75" ou centimetros "+175.00"
;;; (zero = "+0,00" / "\U+00B10.00" -> escrito como "%%p0.00")
(defun es:nivtxt (m / c r)
  (if (= ES:NIVFMT 1)
    (progn
      (setq c (es:int (* (abs m) 10000.0)) r (rem c 100))
      (strcat (cond ((< c 1) "%%p") ((< m 0.0) "-") (t "+")) (itoa (/ c 100)) "."
              (if (< r 10) "0" "") (itoa r)))
    (progn
      (setq c (es:int (* (abs m) 100.0)) r (rem c 100))
      (strcat (if (< m -0.00001) "-" "+") (itoa (/ c 100)) ","
              (if (< r 10) "0" "") (itoa r))))
)

;;; valor de pavimento digitado (na unidade dos niveis) -> texto
(defun es:nivtxt-v (v) (es:nivtxt (if (= ES:NIVFMT 1) (/ v 100.0) v)))

;;; divide um texto pelo caractere ch
(defun es:split (s ch / r i)
  (while (setq i (vl-string-position (ascii ch) s))
    (setq r (cons (substr s 1 i) r) s (substr s (+ i 2))))
  (reverse (cons s r))
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
  (es:layer ES:LAY-HACH   8 nil)
  (es:layer ES:LAY-ARMP   1 20)
  (es:layer ES:LAY-ARMN   1 20)
  (es:layer ES:LAY-ARMT   7 nil)
  (es:layer ES:LAY-TAB    3 20)
  (es:layer ES:LAY-GRADE  8 13)
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
  (if ES:DESL (setq p (es:add p ES:DESL)))
  (list (+ (car ES:O) (/ (car p) ES:UC)) (+ (cadr ES:O) (/ (cadr p) ES:UC)) 0.0)
)

(defun es:line (a b lay)
  (if (and ES:REG (> (es:dist a b) 1e-6)) (setq ES:REG (cons (list (es:p2 a) (es:p2 b)) ES:REG)))
  (if (> (es:dist a b) 1e-6)
    (entmake (append (list '(0 . "LINE") '(100 . "AcDbEntity") (cons 8 lay)
                           '(100 . "AcDbLine") (cons 10 (es:w a)) (cons 11 (es:w b)))
                     (es:xd))))
)

;;; polilinha; lt = tipo de linha (nil = PorLayer); wid = largura
(defun es:pl (pts lay closed lt wid / ok q)
  (if ES:REG
    (progn
      (setq q (car pts))
      (foreach p (append (cdr pts) (if closed (list (car pts))))
        (setq ES:REG (cons (list (es:p2 q) (es:p2 p)) ES:REG) q p))))
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
                                            (strlen s) 0.65 k ES:HC))))
  (es:bb (es:add p (es:mul (es:vet ang) (* (if (= al 2) -1.0 (if (= al 1) -0.5 0.1))
                                            (strlen s) 0.65 k ES:HC))))
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

;;; triangulo cheio (entidade SOLID)
(defun es:solido (a b c lay / pa pb pc)
  (setq pa (es:w a) pb (es:w b) pc (es:w c))
  (entmake (append (list '(0 . "SOLID") (cons 8 lay) (cons 10 pa) (cons 11 pb) (cons 12 pc) (cons 13 pc))
                   (es:xd)))
)

;;; simbolo de nivel: triangulo (meio cheio) com a ponta em p e o texto em cima
(defun es:nivel (p txt / c)
  (setq c ES:HC)
  (es:pl (list p (es:add p (list (* -0.45 c) (* 0.8 c))) (es:add p (list (* 0.45 c) (* 0.8 c))))
         ES:LAY-NIV T nil nil)
  (es:solido p (es:add p (list 0.0 (* 0.8 c))) (es:add p (list (* 0.45 c) (* 0.8 c))) ES:LAY-NIV)
  (es:line (es:add p (list (* -1.2 c) 0.0)) (es:add p (list (* 1.2 c) 0.0)) ES:LAY-NIV)
  (es:txt txt (es:add p (list 0.0 (* 1.2 c))) 1.0 0.0 ES:LAY-NIV 1 0)
)

;;; HACHURA (ActiveX, nao associativa) no contorno fechado pts (cm locais).
;;; pat = nome do padrao ("SOLID", "ANSI31"...), fat = fator da escala,
;;; cor = cor da entidade (nil = PorLayer).  Se o CAD recusar, nao desenha.
(defun es:hachura (pts pat fat lay cor / spc ar q pl h ok)
  (setq spc (vl-catch-all-apply
              '(lambda () (vla-get-Block (vla-get-ActiveLayout (vla-get-ActiveDocument (vlax-get-acad-object)))))
              nil))
  (if (and pat (> (length pts) 2) (not (vl-catch-all-error-p spc)))
    (progn
      (setq ar nil)
      (foreach p pts (setq q (es:w p) ar (append ar (list (car q) (cadr q)))))
      (setq pl (vl-catch-all-apply 'vla-AddLightWeightPolyline
                 (list spc (vlax-make-variant
                             (vlax-safearray-fill (vlax-make-safearray vlax-vbDouble (cons 0 (1- (length ar)))) ar)))))
      (if (not (vl-catch-all-error-p pl))
        (progn
          (vl-catch-all-apply 'vla-put-Closed (list pl :vlax-true))
          (setq h (vl-catch-all-apply 'vla-AddHatch (list spc 1 pat :vlax-false)))
          (if (vl-catch-all-error-p h)
            (setq h nil)
            (progn
              (setq ok (vl-catch-all-apply 'vla-AppendOuterLoop
                         (list h (vlax-make-variant
                                   (vlax-safearray-fill (vlax-make-safearray vlax-vbObject '(0 . 0)) (list pl))))))
              (if (vl-catch-all-error-p ok)
                (progn (vl-catch-all-apply 'vla-Delete (list h)) (setq h nil))
                (progn
                  (if (/= pat "SOLID")
                    (vl-catch-all-apply 'vla-put-PatternScale (list h (max 1e-4 (* fat ES:H (es:n ES:HESC))))))
                  (vl-catch-all-apply 'vla-put-Layer (list h lay))
                  (if cor (vl-catch-all-apply 'vla-put-Color (list h cor)))
                  (vl-catch-all-apply 'vla-Evaluate (list h))
                  (vl-catch-all-apply 'es:xd-ent (list (vlax-vla-object->ename h)))))))
          (vl-catch-all-apply 'vla-Delete (list pl))))
      (if (null h) (setq ES:SEM-HACH T))))
  h
)

;;; hachura de um item de ES:HACHURAS (indice)
(defun es:hachura-i (pts i lay cor / hh)
  (setq hh (es:nth (es:int (es:n i)) ES:HACHURAS))
  (if (and hh (cadr hh))
    (es:hachura pts (cadr hh) (caddr hh) lay (if (= (cadr hh) "SOLID") 253 cor)))
)

;;; simbolo de nivel de PAVIMENTO (circulo com 2 quadrantes cheios), linha
;;; tracejada desde x0, valor em cima e nome embaixo
(defun es:datum (x0 x y val nome / c r o a)
  (setq c ES:HC r (* 0.6 c) o (list x y))
  (es:pl (list (list x0 y) (list (- x r) y)) ES:LAY-NIV nil ES:LT nil)
  (es:circ o r ES:LAY-NIV)
  (es:line (list (- x r) y) (list (+ x r) y) ES:LAY-NIV)
  (es:line (list x (- y r)) (list x (+ y r)) ES:LAY-NIV)
  (foreach a (list 0.0 (* 0.25 pi) pi (* 1.25 pi))
    (es:solido o (es:add o (es:mul (es:vet a) r)) (es:add o (es:mul (es:vet (+ a (* 0.25 pi))) r)) ES:LAY-NIV))
  (es:txt val (list (- x (* 1.1 r)) (+ y (* 0.35 c))) 0.8 0.0 ES:LAY-NIV 2 0)
  (es:txt nome (list (- x (* 1.1 r)) (- y (* 1.15 c))) 0.8 0.0 ES:LAY-NIV 2 0)
)

;;; pavimentos: "NOME=valor;NOME=valor" -> ((nome y) ...), y em cm relativo ao
;;; nivel inicial da escada (valor na unidade dos niveis: m ou cm)
(defun es:lista-pavs ( / r kv v)
  (if (and ES:PAVS (/= (vl-string-trim " " ES:PAVS) ""))
    (foreach it (es:split ES:PAVS ";")
      (setq kv (es:split it "="))
      (if (and (cadr kv) (setq v (es:num (cadr kv))))
        (setq r (cons (list (vl-string-trim " " (car kv))
                            (- (if (= ES:NIVFMT 1) v (* 100.0 v)) (* 100.0 (es:n ES:NIV)))
                            v)
                      r)))))
  (es:ordena (reverse r) '(lambda (x) (cadr x)))
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
;;;    ("LANCE"   nome N e p modo h tipo)  modo "0" = N-1 pisos, "1" = N pisos
;;;               tipo "0" laje inclinada (convencional)  "1" PLISSADA (laje
;;;               dobrada: fundo paralelo aos degraus, espessura h no piso e
;;;               no espelho)
;;;    ("PATAMAR" nome L hp desnivel giro)   giro "0".."4" (ver ES:GIROS)
;;;  Apoios:
;;;    (nome tipo b h pos desl)  tipo "0" viga "1" laje "2" parede;
;;;    pos = 2 x (trecho - 1) + (0 inicio / 1 fim);  desl = cm (+ = sobe)
;;;  Laterais (ES:LATE / ES:LATD):  (tipo nome b h)
;;; ==========================================================================

(defun es:lance-p (tr) (= (car tr) "LANCE"))
(defun es:lance-plis (tr) (and (es:lance-p tr) (= (es:nth 7 tr) "1")))

;;; fundo "quebrado" de um registro (plissada, patamar com a aba da plissada) ou nil.
;;; Registros de es:geo (20 campos): campo 19; pedacos de corte (11): campo 10.
(defun es:cad-fundo (g) (if (> (length g) 15) (es:nth 19 g) (es:nth 10 g)))

;;; fundo da plissada: o perfil dos degraus deslocado de (h, -h), do inicio
;;; (s0, y0 - h) ate a abscissa xe
(defun es:plis-fundo (tp s0 y0 h xe / r a q fim)
  (setq r (list (list s0 (- y0 h))) a (car r) fim nil)
  (foreach p tp
    (if (not fim)
      (progn
        (setq q (list (+ (car p) h) (- (cadr p) h)))
        (if (<= (car q) (+ xe 1e-6))
          (progn (if (not (equal q a 1e-6)) (setq r (cons q r))) (setq a q))
          (progn
            (if (< (car a) (- xe 1e-6))
              (setq r (cons (list xe (+ (cadr a) (* (- (cadr q) (cadr a)) (/ (- xe (car a)) (- (car q) (car a)))))) r)))
            (setq fim T))))))
  (reverse r)
)

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
;;;  19 fundo quebrado (plissada / patamar depois da plissada) ou nil
(defun es:geo (trs / s y r g n e p m h c pts k l d yt hp cf ya ha)
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
        (setq pts (reverse pts))
        (setq r (cons (list "L" s (+ s l) y (+ y (* n e))
                            (- y (* s (/ e p)) (/ h c)) (/ e p)
                            pts h (nth 1 tr) tr (+ y (* n e))
                            n e p m 0.0 0 l
                            (if (es:lance-plis tr) (es:plis-fundo pts s y h (+ s l))))
                      r))
        (setq s (+ s l) y (+ y (* n e)))
      )
      (progn
        (setq l (es:n (nth 2 tr)) hp (es:n (nth 3 tr)) d (es:n (nth 4 tr))
              yt (+ y d))
        (setq pts (if (> (abs d) 0.001)
                    (list (list s y) (list s yt) (list (+ s l) yt))
                    (list (list s y) (list (+ s l) yt))))
        ;; depois de uma plissada: a placa do ultimo espelho desce abaixo do patamar
        (setq cf nil)
        (if (and r (es:cad-fundo (car r)) (= (car (car r)) "L"))
          (progn
            (setq ya (cadr (es:ultimo (es:cad-fundo (car r)))) ha (nth 8 (car r)))
            (if (and (< ya (- yt hp 0.5)) (< ha l))
              (setq cf (list (list s ya) (list (+ s ha) ya) (list (+ s ha) (- yt hp)) (list (+ s l) (- yt hp)))))))
        (setq r (cons (list "P" s (+ s l) y yt (- yt hp) 0.0 pts hp (nth 1 tr) tr yt
                            0 0.0 0.0 0 d (es:int (es:n (nth 5 tr))) l cf)
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
(defun es:intradorso (gs / r g1 g2 sj sx c1 c2 q)
  (setq g1 (car gs) c1 (es:cad-fundo g1))
  (setq r (if c1 (reverse c1) (list (list (es:s-ini gs) (es:yint g1 (es:s-ini gs))))))
  (foreach g2 (cdr gs)
    (setq sj (nth 2 g1) c1 (es:cad-fundo g1) c2 (es:cad-fundo g2))
    (if (and (null c1) (null c2))
      (if (> (abs (- (nth 6 g1) (nth 6 g2))) 1e-9)
        (progn
          (setq sx (/ (- (nth 5 g2) (nth 5 g1)) (- (nth 6 g1) (nth 6 g2))))
          (if (and (>= sx (- (nth 1 g1) 1e-6)) (<= sx (+ (nth 2 g2) 1e-6))
                   (>= sx (- (car (car r)) 1e-6)))
            (setq r (cons (list sx (es:yint g1 sx)) r))
            (setq r (cons (list sj (es:yint g2 sj)) (cons (list sj (es:yint g1 sj)) r)))))
        (if (> (abs (- (nth 5 g1) (nth 5 g2))) 1e-6)
          (setq r (cons (list sj (es:yint g2 sj)) (cons (list sj (es:yint g1 sj)) r)))))
      (progn
        ;; um dos dois tem fundo quebrado: liga pela vertical na juncao
        (if (null c1) (setq r (cons (list sj (es:yint g1 sj)) r)))
        (foreach q (if c2 c2 (list (list sj (es:yint g2 sj))))
          (if (not (equal q (car r) 1e-6)) (setq r (cons q r))))))
    (setq g1 g2))
  (if (null (es:cad-fundo g1))
    (setq r (cons (list (nth 2 g1) (es:yint g1 (nth 2 g1))) r)))
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

;;; apoio: direcao 0 transversal / 1 borda esquerda / 2 borda direita;
;;; extensoes (cm) e ancoragem ("0" padrao / "1" quimica) e profundidade
(defun es:apo-dir (ap) (es:int (es:n (es:nth 6 ap))))
(defun es:apo-ext1 (ap) (es:n (es:nth 7 ap)))
(defun es:apo-ext2 (ap) (es:n (es:nth 8 ap)))
(defun es:apo-quim (ap) (= (es:int (es:n (es:nth 9 ap))) 1))
(defun es:apo-lq (ap) (es:num (es:nth 10 ap)))
;;; apoio completo (preenche os campos novos)
(defun es:apo-completo (ap)
  (list (nth 0 ap) (nth 1 ap) (nth 2 ap) (nth 3 ap) (nth 4 ap) (nth 5 ap)
        (if (es:nth 6 ap) (nth 6 ap) "0") (if (es:nth 7 ap) (nth 7 ap) "0")
        (if (es:nth 8 ap) (nth 8 ap) "0") (if (es:nth 9 ap) (nth 9 ap) "0")
        (if (es:nth 10 ap) (nth 10 ap) "")
        (if (es:nth 11 ap) (nth 11 ap) "0") (if (es:nth 12 ap) (nth 12 ap) "0")
        (if (es:nth 13 ap) (nth 13 ap) "0") (if (es:nth 14 ap) (nth 14 ap) "0"))
)
;;; posicao livre da viga: invertida, desnivel do topo, deslocamento lateral, rotacao
(defun es:apo-inv (ap) (= (es:int (es:n (es:nth 11 ap))) 1))
(defun es:apo-dz (ap) (es:n (es:nth 12 ap)))
(defun es:apo-dv (ap) (es:n (es:nth 13 ap)))
(defun es:apo-gr (ap) (* (es:n (es:nth 14 ap)) (/ pi 180.0)))

;;; fundo da laje (intradorso) na abscissa s do desenvolvimento
(defun es:fundo-est (gs s / cad)
  (setq cad (es:intradorso gs))
  (cond ((<= s (car (car cad))) (cadr (car cad)))
        ((>= s (car (es:ultimo cad))) (cadr (es:ultimo cad)))
        (t (es:y-cadeia cad s)))
)

;;; fundo e topo de uma viga / parede transversal na abscissa s: (yb yt)
;;; normal: topo no topo da laje (+ desnivel); INVERTIDA: fundo no fundo da laje
(defun es:apo-vert (gs ap s / h yt yb)
  (setq h (es:n (nth 3 ap)))
  (if (es:apo-inv ap)
    (setq yb (+ (es:fundo-est gs s) (es:apo-dz ap)) yt (+ yb h))
    (setq yt (+ (es:topo-est gs s) (es:apo-dz ap)) yb (- yt h)))
  (list yb yt)
)
;;; patamar: hachura (indice em ES:HACHURAS) e texto da legenda
(defun es:pat-hach (tr) (if (es:nth 6 tr) (es:int (es:n (nth 6 tr))) 0))
(defun es:pat-leg (tr / s)
  (setq s (es:nth 7 tr))
  (if (and s (/= (vl-string-trim " " s) "")) s
    (strcat "LAJE DO " (nth 1 tr) "  h=" (es:f (es:n (nth 3 tr))))))

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
            yt  (+ (es:topo-est gs s) (es:apo-dz ap))
            x1  (min s (+ s (* dir b))) x2 (max s (+ s (* dir b))))
      (list x1 x2 (- yt h) yt tp))
    (progn
      (setq yt (es:apo-vert gs ap s))
      (list (- s (* 0.5 b)) (+ s (* 0.5 b)) (car yt) (cadr yt) tp)))
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
(defun es:gera-modelo ( / tipo des nt p hl hp lp w nl ns giros e i k trs aps lps nv q pl)
  (setq tipo ES:MTIPO des (es:n ES:MDES) nt (max 1 (es:int (es:n ES:MNDG)))
        p (es:n ES:MPIS) hl ES:MHL hp ES:MHP lp (es:n ES:MLP) w (es:n ES:LAR))
  (setq nl    (nth tipo '(1 2 2 2 3 3 1 2 2 2 3 4 4))
        giros (nth tipo '(nil ("0") ("1") ("3") ("1" "1") ("0" "0")
                          nil ("0") ("1") ("3") ("1" "1") ("1" "1" "1") ("1" "1" "1")))
        pl    (if (member tipo '(6 7 8 9 10 12)) "1" "0"))
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
                          (es:f e) (es:f p) "0" hl pl)
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
(defun es:nome-h (g) (strcat (nth 9 g) "  (h=" (es:f (nth 8 g)) (if (es:cad-fundo g) (if (= (car g) "L") ", plissada" "") "") ")"))
(defun es:nivel-m (y) (+ (es:n ES:NIV) (/ y 100.0)))

;;; rotulo de um apoio: ("V3A" "14/50"); laje ("L5" "h=12"); parede ("PAR1" "e=15")
(defun es:apo-rot (ap / tp)
  (setq tp (es:int (es:n (nth 1 ap))))
  (list (nth 0 ap)
        (cond
          ((= tp 1) (strcat "h=" (es:f (es:n (nth 3 ap)))))
          ((= tp 2) (strcat "e=" (es:f (es:n (nth 2 ap)))))
          (t (strcat (es:f (es:n (nth 2 ap))) "/" (es:f (es:n (nth 3 ap)))))))
)
;;; texto numa linha: "V3A 14/50"
(defun es:apo-txt (ap / r) (setq r (es:apo-rot ap)) (strcat (car r) " " (cadr r)))

;;; ---------------------------------------------------------------------------
;;;  CORTE LONGITUDINAL (desenvolvido).  Origem = inicio do 1.o trecho, no
;;;  nivel inicial.
;;; ---------------------------------------------------------------------------
(defun es:des-lon (gs / c top sc s0 s1 y1 rets r x1 x2 yb yt tp ylim ymin ymax xmax
                        xd yd sm ys ang n bb g ap ym)
  (setq c ES:HC top (es:topo gs) sc (es:intradorso gs)
        s0 (es:s-ini gs) s1 (es:s-fim gs) y1 (es:y-fim gs))
  ;; apoios (retangulos) - usados tambem para recortar as faces das pontas
  (setq rets (mapcar '(lambda (ap) (es:apo-ret gs ap)) (es:apos-transv)))
  ;; ---- concreto: topo (degraus), intradorso e faces das pontas
  (es:pl top ES:LAY-CORTE nil nil nil)
  (es:pl sc ES:LAY-CORTE nil nil nil)
  (foreach sg (es:recorta-v s0 (cadr (car sc)) (cadr (car top)) rets)
    (es:line (list s0 (car sg)) (list s0 (cadr sg)) ES:LAY-CORTE))
  (foreach sg (es:recorta-v s1 (cadr (es:ultimo sc)) y1 rets)
    (es:line (list s1 (car sg)) (list s1 (cadr sg)) ES:LAY-CORTE))
  ;; ---- apoios
  (setq ymin (apply 'min (mapcar 'cadr sc)))
  (foreach ap (es:apos-transv)
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
       ;; viga invertida (ou elevada): parte acima do topo da escada
       (foreach xx (list x1 x2)
         (setq ym (if (and (>= xx s0) (<= xx s1)) (es:y-cadeia top xx) yt))
         (if (and ym (> yt (+ ym 0.5))) (es:line (list xx ym) (list xx yt) ES:LAY-CORTE)))
       (setq ym (if (and (>= (* 0.5 (+ x1 x2)) s0) (<= (* 0.5 (+ x1 x2)) s1)) (es:y-cadeia top (* 0.5 (+ x1 x2))) nil))
       (if (and ym (> yt (+ ym 0.5))) (es:line (list x1 yt) (list x2 yt) ES:LAY-CORTE))
       (es:txt (es:apo-txt ap) (list (* 0.5 (+ x1 x2)) (if (es:apo-inv ap) (+ yt (* 1.0 c)) (- yb (* 1.6 c))))
               0.9 0.0 ES:LAY-TXT 1 0)))
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
  (es:alcas-lon gs)
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
                        w bb kk vd ndg ap dr leg)
  (setq c ES:HC refs (es:planta-refs gs) w (es:n ES:LAR) k 0 nl 0 ndg 0)
  ;; hachura dos patamares e legenda
  (setq leg nil k 0)
  (foreach g gs
    (if (and (= (car g) "P") (> (es:pat-hach (nth 10 g)) 0))
      (progn
        (setq rf (nth k refs) p (nth 0 rf) ang (nth 1 rf) l (nth 2 rf))
        (es:hachura-i (list (es:uv p ang 0.0 (nth 3 rf)) (es:uv p ang l (nth 3 rf))
                            (es:uv p ang l (nth 4 rf)) (es:uv p ang 0.0 (nth 4 rf)))
                      (es:pat-hach (nth 10 g)) ES:LAY-HACH nil)
        (if (not (assoc (es:pat-leg (nth 10 g)) leg))
          (setq leg (cons (list (es:pat-leg (nth 10 g)) (es:pat-hach (nth 10 g))) leg)))))
    (setq k (1+ k)))
  (setq k 0)
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
        (es:txt-bloco (list (nth 9 g) (strcat "h=" (es:f (nth 8 g)) (if (es:lance-plis (nth 10 g)) "  PLISSADA" ""))
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
        ;; numeracao dos degraus (continua desde o 1.o lance)
        (setq x 1)
        (while (<= x (nth 15 g))
          (es:txt-bloco (list (itoa (+ ndg x))) (es:uv p ang (* (- x 0.5) (nth 14 g)) (- vmax (* 0.8 c)))
                        ang 0.55 ES:LAY-TXT)
          (setq x (1+ x)))
        (setq ndg (+ ndg (nth 15 g)))
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
  ;; apoios (tracejados, sob a laje), com extensoes e vigas de borda
  (foreach so (es:solidos gs)
    (if (and (= (car so) "B") (nth 8 (nth 9 so)))
      (progn
        (setq ap (nth 8 (nth 9 so)) p (nth 1 so) ang (nth 2 so)
              tp (es:int (es:n (nth 1 ap))) dr (es:apo-dir ap))
        (if (= tp 1)
          ;; laje de piso: so o nome, perto da ponta de fora
          (es:txt-bloco (list (es:apo-txt ap))
                        (es:uv p ang (if (es:apo-fim ap)
                                       (- (nth 4 so) (max (* 2.0 c) (* 0.25 (- (nth 4 so) (nth 3 so)))))
                                       (+ (nth 3 so) (max (* 2.0 c) (* 0.25 (- (nth 4 so) (nth 3 so))))))
                               (* 0.5 (+ (nth 5 so) (nth 6 so))))
                        ang 0.8 ES:LAY-TXT)
          (progn
            ;; viga normal: tracejada (sob a laje); INVERTIDA: vista (acima da laje)
            (es:pl (list (es:uv p ang (nth 3 so) (nth 5 so)) (es:uv p ang (nth 4 so) (nth 5 so))
                         (es:uv p ang (nth 4 so) (nth 6 so)) (es:uv p ang (nth 3 so) (nth 6 so)))
                   (if (es:apo-inv ap) ES:LAY-VISTA ES:LAY-OCULTA) T (if (not (es:apo-inv ap)) ES:LT) nil)
            (if (= dr 0)
              ;; transversal: nome ao longo da viga, do lado de fora do trecho
              (es:txt-bloco (list (es:apo-txt ap))
                            (es:uv p ang (if (es:apo-fim ap)
                                           (+ (nth 4 so) (* 0.9 c))
                                           (- (nth 3 so) (* 0.9 c)))
                                   (* 0.5 (+ (nth 5 so) (nth 6 so))))
                            (+ ang (/ pi 2.0)) 0.8 ES:LAY-TXT)
              ;; borda: nome ao longo da viga, do lado de fora
              (es:txt-bloco (list (es:apo-txt ap))
                            (es:uv p ang (* 0.5 (+ (nth 3 so) (nth 4 so)))
                                   (if (= dr 1) (+ (nth 6 so) (* 0.9 c)) (- (nth 5 so) (* 0.9 c))))
                            ang 0.8 ES:LAY-TXT)))))))
  (if (and leg (= ES:LEGH "1"))
    (progn
      (setq bb ES:CAIXA x (+ (caddr bb) (* 4.0 c)) u (cadddr bb))
      (es:txt "LEGENDA" (list x u) 1.0 0.0 ES:LAY-TXT 0 0)
      (foreach it (reverse leg)
        (setq u (- u (* 3.0 c)))
        (es:ret x u (+ x (* 3.0 c)) (+ u (* 2.0 c)) ES:LAY-TXT nil)
        (es:hachura-i (list (list x u) (list (+ x (* 3.0 c)) u) (list (+ x (* 3.0 c)) (+ u (* 2.0 c)))
                            (list x (+ u (* 2.0 c))))
                      (cadr it) ES:LAY-HACH nil)
        (es:txt (car it) (list (+ x (* 3.8 c)) (+ u c)) 0.8 0.0 ES:LAY-TXT 0 2))))
  ;; linhas de corte
  (es:marca-cortes gs)
  (es:alcas-pla gs)
  (setq bb ES:CAIXA)
  (es:titulo (strcat "PLANTA DE FORMAS - " ES:NOME) (strcat "ESC. 1:" ES:ESC)
             (* 0.5 (+ (car bb) (caddr bb))) (- (cadr bb) (* 3.0 c)))
)

;;; apoios transversais (os de borda correm ao longo do trecho)
(defun es:apos-transv ()
  (vl-remove-if '(lambda (ap) (> (es:apo-dir ap) 0)) ES:APO)
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
          ;; na ordem de criacao (hachuras por baixo das linhas)
          (foreach e (es:ordena ents '(lambda (x) (es:hex (cdr (assoc 5 (entget x))))))
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

;;; handle (hexadecimal) -> numero
(defun es:hex (s / r c i)
  (setq r 0.0 i 1)
  (if s
    (while (<= i (strlen s))
      (setq c (ascii (strcase (substr s i 1))) i (1+ i))
      (cond ((and (>= c 48) (<= c 57)) (setq r (+ (* r 16.0) (- c 48))))
            ((and (>= c 65) (<= c 70)) (setq r (+ (* r 16.0) (- c 55)))))))
  r
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

;;; desenha um desenho (grp = "PLA" "LON" "TRA" "ARM" "PAR" "QTD" "SEC-x") com origem o e empacota
(defun es:desenha-view (id grp o gs)
  (foreach e (es:soltos id grp) (entdel e))
  (setq ES:PEGAS (vl-remove-if '(lambda (h) (= (car h) grp)) ES:PEGAS))
  (setq ES:ID id ES:TAG "" ES:GRP grp ES:O (es:p2 o) ES:CAIXA nil ES:REG nil ES:DESL nil)
  (cond
    ((= grp "PLA") (es:des-pla gs))
    ((= grp "LON") (es:des-lon gs))
    ((= grp "TRA") (es:des-sec gs (es:corte-aa gs)))
    ((= grp "ARM") (es:des-arm gs))
    ((= grp "PAR") (if (null ES:ARMS) (setq ES:ARMS (es:arm-auto gs))) (es:des-parm gs))
    ((= grp "QTD") (es:des-qtd gs))
    ((wcmatch grp "SEC-*")
     (foreach ct (es:cortes-todos gs)
       (if (= (strcat "SEC-" (car ct)) grp) (es:des-sec gs ct))))
  )
  (setq ES:ID nil ES:GRP nil)
  (es:empacota id grp)
)

;;; ---- registro de uma escada ---------------------------------------------------
;;; (versao  parametros  trechos  apoios  origens  cortes)
;;; origens = (("PLA" x y) ...);  cortes = ((nome ax ay bx by) ...) em cm da planta
(defun es:dados (origens)
  (list ES:VERSAO (mapcar 'eval ES:PARAMS) ES:TRE ES:APO origens ES:CORTES ES:ARMS)
)

(defun es:carrega (d / vs)
  (setq vs (nth 1 d))
  (foreach s ES:PARAMS
    (if vs (progn (set s (car vs)) (setq vs (cdr vs)))))
  (setq ES:TRE (es:nth 2 d) ES:APO (es:nth 3 d) ES:CORTES (es:nth 5 d) ES:ARMS (es:nth 6 d))
  (es:defaults)
  (es:nth 4 d)
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
  (if (null ES:DLON)  (setq ES:DLON "0"))
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
  (if (null ES:NIVFMT) (setq ES:NIVFMT 0))
  (if (null ES:PAVS)  (setq ES:PAVS ""))
  (if (null ES:SECFILL) (setq ES:SECFILL "1"))
  (if (null ES:LEGH)  (setq ES:LEGH "1"))
  (if (null ES:HESC)  (setq ES:HESC "1"))
  (if (null ES:FCK)   (setq ES:FCK "25"))
  (if (null ES:COB)   (setq ES:COB "2.5"))
  (if (null ES:AIB)   (setq ES:AIB 3))
  (if (null ES:AIS)   (setq ES:AIS "12"))
  (if (null ES:ASB)   (setq ES:ASB 2))
  (if (null ES:ASS)   (setq ES:ASS "15"))
  (if (null ES:ADB)   (setq ES:ADB 1))
  (if (null ES:ADS)   (setq ES:ADS "20"))
  (if (null ES:NEGF)  (setq ES:NEGF "0.25"))
  (if (null ES:DARM)  (setq ES:DARM "0"))
  (if (null ES:DQTD)  (setq ES:DQTD "1"))
  (if (null ES:TRE)   (es:gera-modelo))
  (setq ES:APO (mapcar 'es:apo-completo ES:APO))
)

(defun es:write-dcl ( / f nome)
  (setq nome (strcat (getvar "TEMPPREFIX") "ES_ESCADA.dcl")
        f    (open nome "w"))
  (foreach ln
   (list
"es_main : dialog {"
"  label = \"ESCADA  -  FORMAS E ARMADURA      v1.6      Baluarte\";"
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
"        : toggle { key = \"dtra\"; label = \"Corte A-A automatico (transversal ao lance)\"; }"
"        : popup_list { key = \"tral\"; label = \"Corte A-A no :\"; edit_width = 20; }"
"        : toggle { key = \"dlon\"; label = \"Desenvolvimento (trechos em sequencia)\"; }"
"        : text { label = \"Cortes tracados na planta (ESCADASECAO) :\"; }"
"        : list_box { key = \"cor\"; height = 3; width = 30; }"
"        : button { key = \"rmc\"; label = \"Remover corte\"; }"
"        : toggle { key = \"darm\"; label = \"Detalhamento da ARMADURA + lista de ferros\"; }"
"        : toggle { key = \"dqtd\"; label = \"QUANTITATIVO de concreto e formas (tabela)\"; }"
"        : row {"
"          : button { key = \"apr\"; label = \"Apresentacao...\"; }"
"          : button { key = \"arm\"; label = \"Armadura...\"; }"
"        }"
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
"  : edit_box { key = \"h\"; label = \"Espessura  h (cm; perpendicular a laje / na plissada: da placa) :\"; edit_width = 7; }"
"  : popup_list { key = \"tipo\"; label = \"Tipo estrutural :\"; edit_width = 46; }"
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
"  : popup_list { key = \"hach\"; label = \"Hachura na planta :\"; edit_width = 24; }"
"  : edit_box { key = \"leg\"; label = \"Texto na legenda (vazio = automatico) :\"; edit_width = 30; }"
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
"  : popup_list { key = \"dir\"; label = \"Direcao :\"; edit_width = 40; }"
"  : edit_box { key = \"ext1\"; label = \"Extensao alem da borda DIREITA (transv.) / antes do inicio (borda), cm :\"; edit_width = 7; }"
"  : edit_box { key = \"ext2\"; label = \"Extensao alem da borda ESQUERDA (transv.) / depois do fim (borda), cm :\"; edit_width = 7; }"
"  : boxed_column {"
"    label = \"Posicao livre (tambem pelo comando ESCADAVIGA, clicando na planta)\";"
"    : popup_list { key = \"vert\"; label = \"Posicao vertical :\"; edit_width = 40; }"
"    : row {"
"      : edit_box { key = \"dz\"; label = \"Desnivel (cm, + sobe) :\"; edit_width = 6; }"
"      : edit_box { key = \"dv\"; label = \"Desloc. lateral (cm, + a esquerda) :\"; edit_width = 6; }"
"      : edit_box { key = \"gr\"; label = \"Rotacao (graus) :\"; edit_width = 6; }"
"    }"
"  }"
"  : popup_list { key = \"anc\"; label = \"Ancoragem das barras neste apoio :\"; edit_width = 40; }"
"  : edit_box { key = \"lq\"; label = \"Profundidade da ancoragem quimica (cm, vazio = lb) :\"; edit_width = 7; }"
"  : text { label = \"Transversal: o EIXO fica na posicao + deslocamento (topo no nivel da laje).\"; }"
"  : text { label = \"Borda: viga ao longo do trecho, rente a borda (deslocamento + = para fora).\"; }"
"  : text { label = \"Laje de piso: sai para fora da escada a partir da posicao.\"; }"
"  : text { label = \"Vigas de bordo maiores (ex.: V3A, V4A): use as extensoes.\"; }"
"  ok_cancel;"
"}"
""
"es_apr : dialog {"
"  label = \"Apresentacao\";"
"  : popup_list { key = \"nivfmt\"; label = \"Niveis em :\"; edit_width = 26; }"
"  : edit_box { key = \"pavs\"; label = \"Pavimentos (NOME=nivel; NOME=nivel) :\"; edit_width = 60; }"
"  : text { label = \"ex.: NIVEL ARQUITETURA=0; 1a FIADA 1o PAV=310   (nivel na unidade acima)\"; }"
"  : toggle { key = \"secfill\"; label = \"Preencher de cinza o concreto cortado nos cortes\"; }"
"  : toggle { key = \"legh\"; label = \"Legenda das hachuras na planta\"; }"
"  : edit_box { key = \"hesc\"; label = \"Fator de escala das hachuras :\"; edit_width = 6; }"
"  ok_cancel;"
"}"
""
"es_arm : dialog {"
"  label = \"Armadura da escada  -  barras parametrizadas\";"
"  : row {"
"    : boxed_column {"
"      label = \"Dados gerais e padrao do gerador automatico\";"
"      : row {"
"        : edit_box { key = \"fck\"; label = \"fck (MPa) :\"; edit_width = 5; }"
"        : edit_box { key = \"cob\"; label = \"Cobrimento (cm) :\"; edit_width = 5; }"
"      }"
"      : row {"
"        : popup_list { key = \"aib\"; label = \"Inferior :\"; edit_width = 6; }"
"        : edit_box { key = \"ais\"; label = \"c/\"; edit_width = 4; }"
"      }"
"      : row {"
"        : popup_list { key = \"asb\"; label = \"Superior :\"; edit_width = 6; }"
"        : edit_box { key = \"ass\"; label = \"c/\"; edit_width = 4; }"
"      }"
"      : row {"
"        : popup_list { key = \"adb\"; label = \"Distribuicao :\"; edit_width = 6; }"
"        : edit_box { key = \"ads\"; label = \"c/\"; edit_width = 4; }"
"      }"
"      : edit_box { key = \"negf\"; label = \"Negativos: fracao do vao :\"; edit_width = 5; }"
"      : button { key = \"auto\"; label = \"Gerar lista automatica (substitui)\"; }"
"    }"
"    : boxed_column {"
"      label = \"Barras  (B = ordem na lista; no desenho as barras iguais viram uma posicao N;  duplo clique = editar)\";"
"      : list_box { key = \"arms\"; height = 16; width = 84; }"
"      : row {"
"        : button { key = \"addb\"; label = \"+ Barra\"; }"
"        : button { key = \"edb\"; label = \"Editar...\"; }"
"        : button { key = \"dupb\"; label = \"Duplicar\"; }"
"        : button { key = \"rmb\"; label = \"Remover\"; }"
"        : button { key = \"upb\"; label = \"Subir\"; }"
"        : button { key = \"dnb\"; label = \"Descer\"; }"
"      }"
"      : image { key = \"preva\"; width = 84; height = 10; color = -15; }"
"    }"
"  }"
"  : text { key = \"lbinfo\"; width = 100; }"
"  : text { label = \"Ancoragem padrao ou QUIMICA de cada apoio: na janela do apoio (ou na ponta da barra).\"; }"
"  ok_cancel;"
"}"
""
"es_barra : dialog {"
"  label = \"Barra\";"
"  : popup_list { key = \"tipo\"; label = \"Tipo :\"; edit_width = 36; }"
"  : popup_list { key = \"det\"; label = \"Detalhe (corte) :\"; edit_width = 50; }"
"  : boxed_row {"
"    label = \"Inicio\";"
"    : popup_list { key = \"ini\"; label = \"Ponto :\"; edit_width = 30; }"
"    : edit_box { key = \"offi\"; label = \"desloc. (cm) :\"; edit_width = 6; }"
"    : popup_list { key = \"pti\"; label = \"Ponta :\"; edit_width = 32; }"
"    : edit_box { key = \"vali\"; label = \"valor :\"; edit_width = 5; }"
"  }"
"  : boxed_row {"
"    label = \"Fim\";"
"    : popup_list { key = \"fim\"; label = \"Ponto :\"; edit_width = 30; }"
"    : edit_box { key = \"offf\"; label = \"desloc. (cm) :\"; edit_width = 6; }"
"    : popup_list { key = \"ptf\"; label = \"Ponta :\"; edit_width = 32; }"
"    : edit_box { key = \"valf\"; label = \"valor :\"; edit_width = 5; }"
"  }"
"  : row {"
"    : popup_list { key = \"bit\"; label = \"Bitola (mm) :\"; edit_width = 6; }"
"    : edit_box { key = \"esp\"; label = \"Espacamento (cm) :\"; edit_width = 5; }"
"    : edit_box { key = \"qtd\"; label = \"Quantidade (vazio = automatica) :\"; edit_width = 5; }"
"  }"
"  : text { label = \"Deslocamento: + no sentido da subida.  Valor da ponta: perna da dobra, Lq da quimica ou\"; }"
"  : text { label = \"prolongamento (vazio = automatico: espessura - 2c / lb).\"; }"
"  : image { key = \"prevb\"; width = 90; height = 13; color = -15; }"
"  : text { key = \"info\"; width = 90; }"
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
              (es:f (* (nth 3 g) (nth 2 g))) ")   h=" (es:f (nth 4 g))
              (if (es:lance-plis tr) "   PLISSADA" "")))
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
          (if (> (abs (es:n (nth 5 ap))) 0.001) (strcat "  " (es:f (es:n (nth 5 ap))) " cm") "")
          (if (> (es:apo-dir ap) 0) (if (= (es:apo-dir ap) 1) "  [borda esq.]" "  [borda dir.]") "")
          (if (es:apo-inv ap) "  INVERTIDA" "")
          (if (/= (es:apo-dz ap) 0.0) (strcat "  dz=" (es:f (es:apo-dz ap))) "")
          (if (/= (es:apo-dv ap) 0.0) (strcat "  lat=" (es:f (es:apo-dv ap))) "")
          (if (/= (es:n (es:nth 14 ap)) 0.0) (strcat "  rot=" (es:f (es:n (es:nth 14 ap)))) "")
          (if (es:apo-quim ap) "  QUIMICA" ""))
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
  (es:lista "cor" (mapcar '(lambda (c) (strcat "Corte " (car c) "-" (car c))) ES:CORTES) nil)
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
  (set_tile "darm" ES:DARM) (set_tile "dqtd" ES:DQTD)
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
        ES:DARM (get_tile "darm") ES:DQTD (get_tile "dqtd")
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
    ((and (= (get_tile "dpla") "0") (= (get_tile "dlon") "0") (= (get_tile "dtra") "0")
          (= (get_tile "darm") "0") (null ES:CORTES))
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
    ((= a "rmc")
     (if (setq i (es:sel "cor"))
       (progn (setq ES:CORTES (es:remove-nth ES:CORTES i)) (es:main-listas))))
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
      (foreach k '("gera" "rmt" "upt" "dnt" "rma" "rmc")
        (action_tile k (strcat "(vl-catch-all-apply 'es:acao (list \"" k "\"))")))
      (foreach k '("mndg" "mdes" "mpis") (action_tile k "(es:minfo)"))
      (action_tile "addl" "(es:sai 10)")
      (action_tile "addp" "(es:sai 11)")
      (action_tile "edt"  "(if (es:sel \"tre\") (es:sai 12))")
      (action_tile "tre"  "(setq ES:SEL-T (atoi $value)) (if (= $reason 4) (es:sai 12))")
      (action_tile "adda" "(es:sai 20)")
      (action_tile "apr" "(es:sai 30)")
      (action_tile "arm" "(es:sai 31)")
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
      (es:lista "tipo" ES:TIPOS-LANCE nil)
      (set_tile "tipo" (if (es:nth 7 tr) (nth 7 tr) "0"))
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
                " (get_tile \"npis\") (get_tile \"h\") (get_tile \"tipo\"))) (done_dialog 1)))"))
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
      (es:lista "hach" (mapcar 'car ES:HACHURAS) nil)
      (set_tile "hach" (itoa (es:pat-hach tr)))
      (set_tile "leg" (if (es:nth 7 tr) (nth 7 tr) ""))
      (action_tile "accept"
        (strcat "(cond"
                "((= (vl-string-trim \" \" (get_tile \"nome\")) \"\") (es:erro-campo \"nome\" \"Informe o nome do patamar.\"))"
                "((not (es:pos? \"l\")) (es:erro-campo \"l\" \"O comprimento deve ser maior que zero.\"))"
                "((not (es:pos? \"hp\")) (es:erro-campo \"hp\" \"A espessura deve ser maior que zero.\"))"
                "((null (es:num (get_tile \"desn\"))) (es:erro-campo \"desn\" \"Desnivel invalido (0 = sem).\"))"
                "(t (setq ES:RETORNO (list \"PATAMAR\" (vl-string-trim \" \" (get_tile \"nome\"))"
                " (get_tile \"l\") (get_tile \"hp\") (get_tile \"desn\") (get_tile \"giro\")"
                " (get_tile \"hach\") (vl-string-trim \" \" (get_tile \"leg\")))) (done_dialog 1)))"))
      (action_tile "cancel" "(done_dialog 0)")
      (setq ES:RETORNO nil ok (start_dialog))
      (if (= ok 1) ES:RETORNO)
    )
  )
)

(defun es:dlg-apo (id ap / ok)
  (if (null ap)
    (setq ap (list (strcat "V" (itoa (1+ (length ES:APO)))) "0" "14" "40"
                   (itoa (if ES:SEL-T (* 2 ES:SEL-T) 0)) "0" "0" "0" "0" "0" "" "0" "0" "0" "0")))
  (if (new_dialog "es_apo" id)
    (progn
      (es:lista "tipo" ES:TIPOS-APO nil)
      (es:lista "pos" (es:pos-linhas) nil)
      (set_tile "nome" (nth 0 ap)) (set_tile "tipo" (nth 1 ap)) (set_tile "b" (nth 2 ap))
      (set_tile "h" (nth 3 ap))
      (set_tile "pos" (itoa (min (es:int (es:n (nth 4 ap))) (1- (* 2 (length ES:TRE))))))
      (set_tile "desl" (nth 5 ap))
      (setq ap (es:apo-completo ap))
      (es:lista "dir" ES:DIRS-APO nil)
      (es:lista "anc" ES:ANCS nil)
      (set_tile "dir" (nth 6 ap)) (set_tile "ext1" (nth 7 ap)) (set_tile "ext2" (nth 8 ap))
      (set_tile "anc" (nth 9 ap)) (set_tile "lq" (nth 10 ap))
      (es:lista "vert" ES:VERTS nil)
      (set_tile "vert" (nth 11 ap)) (set_tile "dz" (nth 12 ap)) (set_tile "dv" (nth 13 ap)) (set_tile "gr" (nth 14 ap))
      (action_tile "accept"
        (strcat "(cond"
                "((= (vl-string-trim \" \" (get_tile \"nome\")) \"\") (es:erro-campo \"nome\" \"Informe o nome do apoio.\"))"
                "((not (es:pos? \"b\")) (es:erro-campo \"b\" \"b deve ser maior que zero.\"))"
                "((not (es:pos? \"h\")) (es:erro-campo \"h\" \"h deve ser maior que zero.\"))"
                "((null (es:num (get_tile \"desl\"))) (es:erro-campo \"desl\" \"Deslocamento invalido (0 = sem).\"))"
                "((or (null (es:num (get_tile \"ext1\"))) (< (es:num (get_tile \"ext1\")) 0)) (es:erro-campo \"ext1\" \"Extensao: numero >= 0.\"))"
                "((or (null (es:num (get_tile \"ext2\"))) (< (es:num (get_tile \"ext2\")) 0)) (es:erro-campo \"ext2\" \"Extensao: numero >= 0.\"))"
                "((and (/= (vl-string-trim \" \" (get_tile \"lq\")) \"\") (not (es:pos? \"lq\"))) (es:erro-campo \"lq\" \"Profundidade: numero > 0 ou vazio.\"))"
                "((null (es:num (get_tile \"dz\"))) (es:erro-campo \"dz\" \"Desnivel: numero (0 = sem).\"))"
                "((null (es:num (get_tile \"dv\"))) (es:erro-campo \"dv\" \"Deslocamento: numero (0 = sem).\"))"
                "((null (es:num (get_tile \"gr\"))) (es:erro-campo \"gr\" \"Rotacao: numero em graus (0 = sem).\"))"
                "(t (setq ES:RETORNO (list (vl-string-trim \" \" (get_tile \"nome\")) (get_tile \"tipo\")"
                " (get_tile \"b\") (get_tile \"h\") (get_tile \"pos\") (get_tile \"desl\")"
                " (get_tile \"dir\") (get_tile \"ext1\") (get_tile \"ext2\") (get_tile \"anc\")"
                " (vl-string-trim \" \" (get_tile \"lq\"))"
                " (get_tile \"vert\") (get_tile \"dz\") (get_tile \"dv\") (get_tile \"gr\"))) (done_dialog 1)))"))
      (action_tile "cancel" "(done_dialog 0)")
      (setq ES:RETORNO nil ok (start_dialog))
      (if (= ok 1) ES:RETORNO)
    )
  )
)

;;; comprimentos de ancoragem para a janela
(defun es:lb-info ( / f b1 b2)
  (setq f (es:num (get_tile "fck")))
  (if (and f (> f 0))
    (progn
      (setq ES:FCK (get_tile "fck")
            b1 (nth (atoi (get_tile "aib")) ES:BITOLAS) b2 (nth (atoi (get_tile "asb")) ES:BITOLAS))
      (set_tile "lbinfo" (strcat "lb (NBR 6118, boa aderencia):  inferior %%c" b1 " = "
                                 (es:f (es:lb-cm (es:num b1) T)) " cm;   superior %%c" b2 " (ma aderencia) = "
                                 (es:f (es:lb-cm (es:num b2) nil)) " cm")))
    (set_tile "lbinfo" ""))
)

(defun es:dlg-apr (id / ok)
  (if (new_dialog "es_apr" id)
    (progn
      (es:lista "nivfmt" ES:NIVFMTS nil)
      (set_tile "nivfmt" (itoa ES:NIVFMT)) (set_tile "pavs" ES:PAVS)
      (set_tile "secfill" ES:SECFILL) (set_tile "legh" ES:LEGH) (set_tile "hesc" ES:HESC)
      (action_tile "accept"
        (strcat "(if (not (es:pos? \"hesc\")) (es:erro-campo \"hesc\" \"Fator de escala > 0.\")"
                " (progn (setq ES:NIVFMT (atoi (get_tile \"nivfmt\")) ES:PAVS (get_tile \"pavs\")"
                " ES:SECFILL (get_tile \"secfill\") ES:LEGH (get_tile \"legh\") ES:HESC (get_tile \"hesc\"))"
                " (done_dialog 1)))"))
      (action_tile "cancel" "(done_dialog 0)")
      (setq ok (start_dialog))))
)

;;; ---- janela de armaduras parametrizadas ------------------------------------------
(defun es:arm-linha (i d / p1 p2)
  (setq p1 (es:ad d 2) p2 (es:ad d 4))
  (strcat "B" (itoa i) "   D" (es:ad d 1) "   " (nth (es:int (es:n (car d))) ES:TIPOS-ARM-C)
          "   fi " (nth (es:int (es:n (es:ad d 10))) ES:BITOLAS) " c/" (es:ad d 11)
          (if (es:num (es:ad d 12)) (strcat "  (" (es:ad d 12) " un.)") "")
          "   " p1 (if (/= (es:n (es:ad d 3)) 0.0) (strcat (if (> (es:n (es:ad d 3)) 0) "+" "") (es:ad d 3)) "")
          " -> " p2 (if (/= (es:n (es:ad d 5)) 0.0) (strcat (if (> (es:n (es:ad d 5)) 0) "+" "") (es:ad d 5)) "")
          (if (member (car d) '("0" "1"))
            (strcat "   [" (nth (es:int (es:n (es:ad d 6))) ES:PONTAS-C) " / "
                    (nth (es:int (es:n (es:ad d 8))) ES:PONTAS-C) "]")
            ""))
)

(defun es:arm-listar ( / i r)
  (setq i 0 r nil)
  (foreach d ES:ARMS (setq i (1+ i) r (cons (es:arm-linha i d) r)))
  (es:lista "arms" (reverse r) ES:SEL-B)
)

;;; le os padroes da janela (sem validar)
(defun es:arm-le ()
  (setq ES:FCK (get_tile "fck") ES:COB (get_tile "cob")
        ES:AIB (atoi (get_tile "aib")) ES:AIS (get_tile "ais")
        ES:ASB (atoi (get_tile "asb")) ES:ASS (get_tile "ass")
        ES:ADB (atoi (get_tile "adb")) ES:ADS (get_tile "ads") ES:NEGF (get_tile "negf"))
)

(defun es:arm-acao (a / i)
  (setq i (es:sel "arms"))
  (cond
    ((= a "auto")
     (es:arm-le)
     (if (and (es:pos? "fck") (es:pos? "cob") (es:pos? "ais") (es:pos? "ass") (es:pos? "ads") (es:pos? "negf"))
       (progn (setq ES:ARMS (es:arm-auto (es:geo ES:TRE)) ES:SEL-B 0) (es:arm-listar))
       (alert "Preencha os dados gerais com numeros > 0.")))
    ((and (= a "rmb") i)
     (setq ES:ARMS (es:remove-nth ES:ARMS i) ES:SEL-B (max 0 (1- i))) (es:arm-listar))
    ((and (= a "dupb") i)
     (setq ES:ARMS (es:insere-nth ES:ARMS (1+ i) (nth i ES:ARMS)) ES:SEL-B (1+ i)) (es:arm-listar))
    ((and (= a "upb") i (> i 0))
     (setq ES:ARMS (es:troca ES:ARMS i (1- i)) ES:SEL-B (1- i)) (es:arm-listar))
    ((and (= a "dnb") i (< i (1- (length ES:ARMS))))
     (setq ES:ARMS (es:troca ES:ARMS i (1+ i)) ES:SEL-B (1+ i)) (es:arm-listar)))
)

(defun es:dlg-arm (id / ok)
  (if (new_dialog "es_arm" id)
    (progn
      (foreach k '("aib" "asb" "adb") (es:lista k ES:BITOLAS nil))
      (set_tile "fck" ES:FCK) (set_tile "cob" ES:COB)
      (set_tile "aib" (itoa ES:AIB)) (set_tile "ais" ES:AIS)
      (set_tile "asb" (itoa ES:ASB)) (set_tile "ass" ES:ASS)
      (set_tile "adb" (itoa ES:ADB)) (set_tile "ads" ES:ADS)
      (set_tile "negf" ES:NEGF)
      (es:arm-listar)
      (es:lb-info)
      (foreach k '("fck" "aib" "asb") (action_tile k "(es:lb-info)"))
      (foreach k '("auto" "rmb" "dupb" "upb" "dnb")
        (action_tile k (strcat "(vl-catch-all-apply 'es:arm-acao (list \"" k "\"))")))
      (action_tile "arms" "(setq ES:SEL-B (atoi $value)) (es:img-barra \"preva\" (es:nth ES:SEL-B ES:ARMS)) (if (= $reason 4) (progn (es:arm-le) (done_dialog 41)))")
      (es:img-barra "preva" (es:nth (if ES:SEL-B ES:SEL-B 0) ES:ARMS))
      (action_tile "addb" "(es:arm-le) (setq ES:SEL-B (es:sel \"arms\")) (done_dialog 40)")
      (action_tile "edb" "(if (es:sel \"arms\") (progn (es:arm-le) (setq ES:SEL-B (es:sel \"arms\")) (done_dialog 41)))")
      (action_tile "accept"
        (strcat "(cond"
                "((not (es:pos? \"fck\")) (es:erro-campo \"fck\" \"fck > 0.\"))"
                "((not (es:pos? \"cob\")) (es:erro-campo \"cob\" \"Cobrimento > 0.\"))"
                "((not (es:pos? \"ais\")) (es:erro-campo \"ais\" \"Espacamento > 0.\"))"
                "((not (es:pos? \"ass\")) (es:erro-campo \"ass\" \"Espacamento > 0.\"))"
                "((not (es:pos? \"ads\")) (es:erro-campo \"ads\" \"Espacamento > 0.\"))"
                "((not (es:pos? \"negf\")) (es:erro-campo \"negf\" \"Fracao > 0 (ex.: 0.25).\"))"
                "(t (es:arm-le) (done_dialog 1)))"))
      (action_tile "cancel" "(done_dialog 0)")
      (setq ok (start_dialog))))
)

;;; sub-janela de uma barra
(defun es:barra-pontos ( / gs dts geo tp dt k1 k2)
  (setq gs (es:geo ES:TRE) dts (es:arm-detalhes gs)
        dt (es:nth (atoi (get_tile "det")) dts) tp (get_tile "tipo"))
  (if dt
    (progn
      (setq geo (es:arm-geo gs dt) ES:BR-PTS (es:arm-pontos geo tp))
      (setq k1 (if ES:BR-KI ES:BR-KI "INI") k2 (if ES:BR-KF ES:BR-KF "FIM"))
      (es:lista "ini" (mapcar 'cadr ES:BR-PTS) nil)
      (es:lista "fim" (mapcar 'cadr ES:BR-PTS) nil)
      (set_tile "ini" (itoa (es:idx-chave k1)))
      (set_tile "fim" (itoa (es:idx-chave k2)))
      (set_tile "info" (strcat "Comprimento do detalhe: "
                               (es:f (- (caddr (assoc "FIM" ES:BR-PTS)) (caddr (assoc "INI" ES:BR-PTS))))
                               " cm   |   apoios: "
                               (apply 'strcat (mapcar '(lambda (s) (strcat (car (nth 5 s)) " ")) (nth 3 geo)))))))
)
(defun es:idx-chave (k / i r)
  (setq i 0 r nil)
  (foreach p ES:BR-PTS (if (and (null r) (= (car p) k)) (setq r i)) (setq i (1+ i)))
  (if r r (if (= k "FIM") 1 0))
)
(defun es:barra-chaves ()
  (setq ES:BR-KI (car (es:nth (atoi (get_tile "ini")) ES:BR-PTS))
        ES:BR-KF (car (es:nth (atoi (get_tile "fim")) ES:BR-PTS)))
)
(defun es:barra-modo ( / m)
  (setq m (if (member (get_tile "tipo") '("2" "3")) 1 0))
  (foreach k '("pti" "vali" "ptf" "valf") (mode_tile k m))
)

(defun es:dlg-barra (id d / ok nd)
  (if (null d)
    (setq d (list "0" "1" "INI" "0" "FIM" "0" "3" "" "3" "" (itoa ES:AIB) ES:AIS "")))
  (setq nd (length (es:arm-detalhes (es:geo ES:TRE))))
  (if (new_dialog "es_barra" id)
    (progn
      (es:lista "tipo" ES:TIPOS-ARM nil)
      (es:lista "det" (mapcar '(lambda (x) (strcat "D" (itoa (1+ (vl-position x (es:arm-detalhes (es:geo ES:TRE))))) " - " (car x)))
                              (es:arm-detalhes (es:geo ES:TRE))) nil)
      (es:lista "pti" ES:PONTAS nil) (es:lista "ptf" ES:PONTAS nil)
      (es:lista "bit" ES:BITOLAS nil)
      (set_tile "tipo" (car d))
      (set_tile "det" (itoa (max 0 (min (1- nd) (1- (es:int (es:n (es:ad d 1))))))))
      (setq ES:BR-KI (es:ad d 2) ES:BR-KF (es:ad d 4))
      (es:barra-pontos)
      (set_tile "offi" (es:ad d 3)) (set_tile "offf" (es:ad d 5))
      (set_tile "pti" (es:ad d 6)) (set_tile "vali" (es:ad d 7))
      (set_tile "ptf" (es:ad d 8)) (set_tile "valf" (es:ad d 9))
      (set_tile "bit" (es:ad d 10)) (set_tile "esp" (es:ad d 11)) (set_tile "qtd" (es:ad d 12))
      (es:barra-modo)
      (es:barra-prev)
      (action_tile "tipo" "(es:barra-chaves) (es:barra-pontos) (es:barra-modo) (es:barra-prev)")
      (action_tile "det" "(setq ES:BR-KI \"INI\" ES:BR-KF \"FIM\") (es:barra-pontos) (es:barra-prev)")
      (foreach k '("ini" "fim" "offi" "offf" "pti" "ptf" "vali" "valf" "bit" "esp")
        (action_tile k "(es:barra-chaves) (es:barra-prev)"))
      (action_tile "accept"
        (strcat "(cond"
                "((null (es:num (get_tile \"offi\"))) (es:erro-campo \"offi\" \"Deslocamento: numero (0 = no ponto).\"))"
                "((null (es:num (get_tile \"offf\"))) (es:erro-campo \"offf\" \"Deslocamento: numero (0 = no ponto).\"))"
                "((and (/= (vl-string-trim \" \" (get_tile \"vali\")) \"\") (not (es:pos? \"vali\"))) (es:erro-campo \"vali\" \"Valor > 0 ou vazio.\"))"
                "((and (/= (vl-string-trim \" \" (get_tile \"valf\")) \"\") (not (es:pos? \"valf\"))) (es:erro-campo \"valf\" \"Valor > 0 ou vazio.\"))"
                "((not (es:pos? \"esp\")) (es:erro-campo \"esp\" \"Espacamento > 0.\"))"
                "((and (/= (vl-string-trim \" \" (get_tile \"qtd\")) \"\") (not (es:pos? \"qtd\"))) (es:erro-campo \"qtd\" \"Quantidade > 0 ou vazio.\"))"
                "(t (es:barra-chaves)"
                " (setq ES:RETORNO (list (get_tile \"tipo\") (itoa (1+ (atoi (get_tile \"det\"))))"
                " ES:BR-KI (get_tile \"offi\") ES:BR-KF (get_tile \"offf\")"
                " (get_tile \"pti\") (vl-string-trim \" \" (get_tile \"vali\"))"
                " (get_tile \"ptf\") (vl-string-trim \" \" (get_tile \"valf\"))"
                " (get_tile \"bit\") (get_tile \"esp\") (vl-string-trim \" \" (get_tile \"qtd\"))))"
                " (done_dialog 1)))"))
      (action_tile "cancel" "(done_dialog 0)")
      (setq ES:RETORNO nil ok (start_dialog))
      (if (= ok 1) ES:RETORNO)))
)

;;; barra com os valores atuais da janela (sem validar)
(defun es:barra-tiles ()
  (list (get_tile "tipo") (itoa (1+ (atoi (get_tile "det"))))
        (if ES:BR-KI ES:BR-KI "INI") (get_tile "offi") (if ES:BR-KF ES:BR-KF "FIM") (get_tile "offf")
        (get_tile "pti") (vl-string-trim " " (get_tile "vali"))
        (get_tile "ptf") (vl-string-trim " " (get_tile "valf"))
        (get_tile "bit") (get_tile "esp") (vl-string-trim " " (get_tile "qtd")))
)
(defun es:barra-prev () (es:img-barra "prevb" (es:barra-tiles)))

;;; previa de uma barra no corte do seu detalhe: concreto (cinza), apoios,
;;; outras barras do detalhe (apagadas) e a barra (vermelho)
(defun es:img-barra (key d / w h gs dts dt geo top bot sups b pts xmin xmax ymin ymax k ox oy
                         a q lst i os r)
  (setq w (dimx_tile key) h (dimy_tile key))
  (start_image key)
  (fill_image 0 0 w h -15)
  (if (and d ES:TRE)
    (progn
      (setq gs (es:geo ES:TRE) dts (es:arm-detalhes gs) i (es:int (es:n (es:ad d 1)))
            dt (es:nth (1- i) dts))
      (if dt (setq geo (es:arm-geo gs dt)))
      (if (and geo (car geo))
        (progn
          (setq top (es:topo-grupo (car geo)) bot (nth 1 geo) sups (nth 3 geo)
                b (vl-catch-all-apply 'es:arm-barra (list gs geo d (es:n ES:LAR))))
          (if (vl-catch-all-error-p b) (setq b nil))
          (setq os nil)
          (foreach e ES:ARMS
            (if (and (= (es:int (es:n (es:ad e 1))) i) (not (equal e d))
                     (member (car e) '("0" "1")))
              (progn
                (setq r (vl-catch-all-apply 'es:arm-barra (list gs geo e (es:n ES:LAR))))
                (if (and r (not (vl-catch-all-error-p r))) (setq os (cons (nth 1 r) os))))))
          (setq pts (append top bot))
          (foreach s sups (setq pts (cons (list (car s) (nth 2 s)) (cons (list (cadr s) (nth 3 s)) pts))))
          (if b (setq pts (append pts (nth 1 b))))
          (setq xmin (apply 'min (mapcar 'car pts)) xmax (apply 'max (mapcar 'car pts))
                ymin (apply 'min (mapcar 'cadr pts)) ymax (apply 'max (mapcar 'cadr pts)))
          (setq k (min (/ (- w 10.0) (max 1.0 (- xmax xmin))) (/ (- h 10.0) (max 1.0 (- ymax ymin))))
                ox (* 0.5 (- w (* k (- xmax xmin)))) oy (* 0.5 (- h (* k (- ymax ymin)))))
          (setq lst (list (list top 8) (list bot 8)
                          (list (list (car bot) (car top)) 8) (list (list (es:ultimo bot) (es:ultimo top)) 8)))
          (foreach s sups
            (setq lst (cons (list (list (list (car s) (nth 2 s)) (list (cadr s) (nth 2 s)) (list (cadr s) (nth 3 s))
                                        (list (car s) (nth 3 s)) (list (car s) (nth 2 s))) 9) lst)))
          (foreach o os (setq lst (cons (list o 251) lst)))
          (if b
            (if (member (car b) '("2" "3"))
              (foreach p (nth 1 b)
                (setq lst (cons (list (list (es:add p '(-2.0 -2.0)) (es:add p '(2.0 2.0))) 1)
                                (cons (list (list (es:add p '(-2.0 2.0)) (es:add p '(2.0 -2.0))) 1) lst))))
              (setq lst (cons (list (nth 1 b) 1) lst))))
          (foreach c (reverse lst)
            (setq a (es:img-pt (car (car c)) k ox oy xmin ymin h))
            (foreach p (cdr (car c))
              (setq q (es:img-pt p k ox oy xmin ymin h))
              (vector_image (car a) (cadr a) (car q) (cadr q) (cadr c))
              (setq a q)))))))
  (end_image)
)
(defun es:img-pt (p k ox oy xmin ymin h)
  (list (fix (+ ox (* k (- (car p) xmin)))) (fix (- h oy (* k (- (cadr p) ymin)))))
)

;;; laco da janela de armaduras (Cancelar desfaz tudo o que foi feito nela)
(defun es:dlg-arm-laco (id / bk fim c r)
  (setq bk (list ES:ARMS ES:FCK ES:COB ES:AIB ES:AIS ES:ASB ES:ASS ES:ADB ES:ADS ES:NEGF) fim nil)
  (if (null ES:ARMS) (setq ES:ARMS (es:arm-auto (es:geo ES:TRE))))
  (while (not fim)
    (setq c (es:dlg-arm id))
    (cond
      ((= c 1) (setq fim T))
      ((= c 40)
       (if (setq r (es:dlg-barra id nil))
         (setq ES:SEL-B (if ES:SEL-B (1+ ES:SEL-B) (length ES:ARMS))
               ES:ARMS (es:insere-nth ES:ARMS ES:SEL-B r))))
      ((= c 41)
       (if (and ES:SEL-B (es:nth ES:SEL-B ES:ARMS) (setq r (es:dlg-barra id (nth ES:SEL-B ES:ARMS))))
         (setq ES:ARMS (es:setnth ES:ARMS ES:SEL-B r))))
      (t
       (setq fim T ES:ARMS (nth 0 bk) ES:FCK (nth 1 bk) ES:COB (nth 2 bk) ES:AIB (nth 3 bk)
             ES:AIS (nth 4 bk) ES:ASB (nth 5 bk) ES:ASS (nth 6 bk) ES:ADB (nth 7 bk)
             ES:ADS (nth 8 bk) ES:NEGF (nth 9 bk)))))
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
        ((= acao 30) (es:dlg-apr id))
        ((= acao 31) (es:dlg-arm-laco id))
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
;;;  9.  MODELO 3D E CORTES EM QUALQUER POSICAO
;;;  Cada trecho e um SOLIDO: a planta (referencial P ang, u ao longo da
;;;  subida, v a esquerda) vezes o perfil vertical, que so depende de u:
;;;    lance ..... topo = degraus, fundo = laje inclinada
;;;    patamar ... topo = nivel, fundo = nivel - espessura
;;;    caixa ..... vigas, paredes, lajes de piso e apoios laterais
;;;  Um CORTE e uma linha na planta (A -> B) e olha para a ESQUERDA de A->B.
;;;  No desenho do corte: x = distancia ao longo de A->B (cm), y = nivel (cm).
;;; ==========================================================================

;;; solido: (tipo P ang umin umax vmin vmax k g dados)
;;;   tipo "L" lance / "P" patamar / "B" caixa;  g = registro de es:geo
;;;   dados da caixa: (topo-em-umin topo-em-umax altura tipo nome quebra-topo u-longe)
;;;     tipo "V" viga, "W" parede, "S" laje de piso
;;; lances prolongados ate a quebra da laje dentro do patamar vizinho (a laje
;;; inclinada continua sob o patamar ate encontrar o fundo dele)
(defun es:estende (sols gs / r k g ant prx sx lo hi cad)
  (setq cad (es:intradorso gs))
  (foreach so sols
    (if (= (car so) "L")
      (progn
        (setq k (nth 7 so) g (nth 8 so) lo 0.0 hi (nth 4 so)
              ant (es:nth (1- k) gs) prx (es:nth (1+ k) gs))
        (if (and ant (> (abs (- (nth 6 g) (nth 6 ant))) 1e-9))
          (progn
            (setq sx (/ (- (nth 5 ant) (nth 5 g)) (- (nth 6 g) (nth 6 ant))))
            (if (and (< sx (nth 1 g)) (> sx (- (nth 1 ant) 1e-6))) (setq lo (- sx (nth 1 g))))))
        (if (and prx (> (abs (- (nth 6 g) (nth 6 prx))) 1e-9))
          (progn
            (setq sx (/ (- (nth 5 prx) (nth 5 g)) (- (nth 6 g) (nth 6 prx))))
            (if (and (> sx (nth 2 g)) (< sx (+ (nth 2 prx) 1e-6))) (setq hi (- sx (nth 1 g))))))
        (if (es:cad-fundo g) (setq lo 0.0 hi (nth 4 so)))
        (setq r (cons (list "L" (nth 1 so) (nth 2 so) lo hi (nth 5 so) (nth 6 so) k g
                            (if (es:cad-fundo g) (es:cad-fundo g) cad))
                      r)))
      (setq r (cons so r))))
  (reverse r)
)

(defun es:solidos (gs / refs k r g rf p ang l vmin vmax lat b h tp u ap kk s yt dir e pp y0 top0
                       e1 e2 dr ds rot v1 dz dv gr vc uc hl f0 f1 yv)
  (setq refs (es:planta-refs gs) k 0 r nil)
  (foreach g gs
    (setq rf (nth k refs) p (nth 0 rf) ang (nth 1 rf) l (nth 2 rf)
          vmin (nth 3 rf) vmax (nth 4 rf))
    (setq r (cons (list (car g) p ang 0.0 l vmin vmax k g nil) r))
    ;; apoios laterais dos lances (viga inclinada rente aos bocais / parede)
    (if (= (car g) "L")
      (foreach lat (list (list ES:LATE 1.0) (list ES:LATD -1.0))
        (if (and (car lat) (> (es:int (es:n (car (car lat)))) 0))
          (progn
            (setq b (es:n (nth 2 (car lat))) h (es:n (nth 3 (car lat)))
                  e (nth 13 g) pp (nth 14 g) y0 (nth 3 g))
            (if (= (es:int (es:n (car (car lat)))) 1)
              (setq top0 (+ y0 e) tp "V")
              (setq top0 (+ y0 e 100.0) h (+ 140.0 e (/ (nth 8 g) (cos (atan (/ e pp))))) tp "W"))
            (setq r (cons (list "B" p ang 0.0 l
                                (if (> (cadr lat) 0.0) vmax (- vmin b))
                                (if (> (cadr lat) 0.0) (+ vmax b) vmin)
                                k g (list top0 (+ top0 (* l (/ e pp))) h tp
                                          (list (nth 1 (car lat))
                                                (if (= tp "W") "" (strcat (es:f b) "/" (es:f h))))
                                          (= tp "W") nil ang nil))
                          r))))))
    (setq k (1+ k))
  )
  ;; apoios: transversais (com extensoes alem das bordas) e de borda (ao longo).
  ;; Cada viga tem o seu referencial (centro, angulo): deslocamento lateral e
  ;; rotacao livres; normal (topo na laje) ou INVERTIDA (fundo na laje).
  (foreach ap ES:APO
    (setq kk (es:apo-k gs ap) rf (nth kk refs) g (nth kk gs)
          p (nth 0 rf) ang (nth 1 rf) vmin (nth 3 rf) vmax (nth 4 rf) l (nth 2 rf)
          b (es:n (nth 2 ap)) h (es:n (nth 3 ap)) tp (es:int (es:n (nth 1 ap)))
          e1 (es:apo-ext1 ap) e2 (es:apo-ext2 ap) dr (es:apo-dir ap) ds (es:n (nth 5 ap))
          rot (es:apo-rot ap) dz (es:apo-dz ap) dv (es:apo-dv ap) gr (es:apo-gr ap))
    (cond
      ((> dr 0)
       ;; viga de borda: ao longo do trecho, rente a borda (desl. + = para fora)
       (setq v1 (if (= dr 1) (+ (- vmax b) ds) (- vmin ds))
             vc (+ v1 (* 0.5 b) dv) uc (* 0.5 (- (+ l e2) e1)) hl (* 0.5 (+ l e1 e2)))
       (if (= (car g) "L")
         (setq y0 (+ (nth 3 g) (* (- e1) (nth 6 g))) yt (+ (nth 3 g) (* (+ l e2) (nth 6 g)))
               f0 (- y0 (/ (nth 8 g) (cos (atan (nth 6 g))))) f1 (- yt (/ (nth 8 g) (cos (atan (nth 6 g))))))
         (setq y0 (nth 11 g) yt y0 f0 (- y0 (nth 8 g)) f1 f0))
       (if (es:apo-inv ap)
         (setq y0 (+ f0 dz h) yt (+ f1 dz h))
         (setq y0 (+ y0 dz) yt (+ yt dz)))
       (setq r (cons (list "B" (es:uv p ang uc vc) (+ ang gr) (- hl) hl (* -0.5 b) (* 0.5 b) kk g
                           (list y0 yt h (if (= tp 2) "W" "V") rot nil nil (+ ang gr) ap))
                     r)))
      ((= tp 1)
       (setq u (+ (if (es:apo-fim ap) l 0.0) ds) s (es:apo-s gs ap) yt (+ (es:topo-est gs s) dz)
             dir (if (es:apo-fim ap) 1.0 -1.0))
       (setq r (cons (list "B" p ang (min u (+ u (* dir b))) (max u (+ u (* dir b))) (+ (- vmin e1) dv) (+ vmax e2 dv) kk g
                           (list yt yt h "S" rot nil (+ u (* dir b)) (+ ang (/ pi 2.0)) ap))
                     r)))
      (t
       (setq u (+ (if (es:apo-fim ap) l 0.0) ds) s (es:apo-s gs ap) yv (es:apo-vert gs ap s)
             vc (+ (* 0.5 (+ (- vmin e1) vmax e2)) dv) hl (* 0.5 (+ (- vmax vmin) e1 e2)))
       (setq r (cons (list "B" (es:uv p ang u vc) (+ ang gr) (* -0.5 b) (* 0.5 b) (- hl) hl kk g
                           (list (cadr yv) (cadr yv) h (if (= tp 2) "W" "V") rot nil nil (+ ang gr (/ pi 2.0)) ap))
                     r))))
  )
  (reverse r)
)

;;; topo e fundo de um solido na coordenada u
(defun es:sol-top (so u / g k d)
  (setq g (nth 8 so))
  (cond
    ((= (car so) "L")
     (if (< u -1e-6)
       (nth 3 g)
       (+ (nth 3 g) (* (max 1 (min (1+ (fix (/ u (nth 14 g)))) (nth 12 g))) (nth 13 g)))))
    ((= (car so) "P") (nth 11 g))
    (t
     (setq d (nth 9 so))
     (if (> (- (nth 4 so) (nth 3 so)) 1e-6)
       (+ (nth 0 d) (* (- (nth 1 d) (nth 0 d)) (/ (- u (nth 3 so)) (- (nth 4 so) (nth 3 so)))))
       (nth 0 d))))
)
(defun es:sol-bot (so u / g yy)
  (setq g (nth 8 so))
  (cond
    ((= (car so) "L")
     ;; lance estendido: fundo = linha de quebra do intradorso (es:estende);
     ;; plissada: o proprio fundo dobrado
     (cond
       ((and (es:cad-fundo g) (setq yy (es:y-cadeia (es:cad-fundo g) (+ (nth 1 g) (max 0.0 (min u (nth 18 g))))))) yy)
       ((and (nth 9 so) (setq yy (es:y-cadeia (nth 9 so) (+ (nth 1 g) u)))) yy)
       (t (es:yint g (+ (nth 1 g) u)))))
    ((= (car so) "P")
     (if (and (es:cad-fundo g) (setq yy (es:y-cadeia (es:cad-fundo g) (+ (nth 1 g) (max 0.0 (min u (nth 18 g)))))))
       yy
       (nth 5 g)))
    (t (- (es:sol-top so u) (nth 2 (nth 9 so)))))
)

;;; coordenadas locais (u v) de um ponto da planta
(defun es:sol-u (so x) (+ (* (- (car x) (car (nth 1 so))) (cos (nth 2 so))) (* (- (cadr x) (cadr (nth 1 so))) (sin (nth 2 so)))))
(defun es:sol-v (so x) (- (* (- (cadr x) (cadr (nth 1 so))) (cos (nth 2 so))) (* (- (car x) (car (nth 1 so))) (sin (nth 2 so)))))

;;; recorte de Liang-Barsky de uma variavel p0 + t dp em [lo, hi]
(defun es:lb (p0 dp lo hi iv / t1 t2 tx)
  (cond
    ((null iv) nil)
    ((< (abs dp) 1e-12) (if (and (>= p0 (- lo 1e-6)) (<= p0 (+ hi 1e-6))) iv))
    (t
     (setq t1 (/ (- lo p0) dp) t2 (/ (- hi p0) dp))
     (if (> t1 t2) (setq tx t1 t1 t2 t2 tx))
     (setq iv (list (max (car iv) t1) (min (cadr iv) t2)))
     (if (< (car iv) (cadr iv)) iv)))
)

;;; trecho da reta X = b0 + t dir (t0..t1) dentro da planta do solido: (ta tb) ou nil
(defun es:sol-int (so b0 dir t0 t1 / iv c s u0 v0 du dv)
  (setq c (cos (nth 2 so)) s (sin (nth 2 so))
        u0 (es:sol-u so b0) v0 (es:sol-v so b0)
        du (+ (* (car dir) c) (* (cadr dir) s))
        dv (- (* (cadr dir) c) (* (car dir) s)))
  (setq iv (es:lb u0 du (nth 3 so) (nth 4 so) (list t0 t1)))
  (setq iv (es:lb v0 dv (nth 5 so) (nth 6 so) iv))
  (if (and iv (> (- (cadr iv) (car iv)) 0.01)) iv)
)

;;; ---- cortes guardados --------------------------------------------------------
;;; ES:CORTES = ((nome ax ay bx by) ...) em cm da planta
;;; corte A-A automatico: transversal ao lance escolhido, atravessando a escada
(defun es:corte-aa (gs / refs k nl i g rf q dir t1 t2 iv m)
  (setq refs (es:planta-refs gs) k 0 nl 0 i nil)
  (foreach g gs
    (if (= (car g) "L")
      (progn
        (if (or (null i) (= nl (es:int (es:n ES:TRAL)))) (setq i k))
        (setq nl (1+ nl))))
    (setq k (1+ k)))
  (if i
    (progn
      (setq g (nth i gs) rf (nth i refs)
            q (es:uv (nth 0 rf) (nth 1 rf) (* (+ (fix (* 0.5 (nth 15 g))) 0.5) (nth 14 g)) 0.0)
            dir (es:mul (es:nrm (nth 1 rf)) -1.0)
            t1 nil t2 nil)
      (foreach so (es:solidos gs)
        (if (setq iv (es:sol-int so q dir -100000.0 100000.0))
          (setq t1 (if t1 (min t1 (car iv)) (car iv)) t2 (if t2 (max t2 (cadr iv)) (cadr iv)))))
      (setq m 40.0)
      (list "A" (es:add q (es:mul dir (- t1 m))) (es:add q (es:mul dir (+ t2 m))))))
)

(defun es:cortes-todos (gs / r)
  (setq r (mapcar '(lambda (c) (list (car c) (list (nth 1 c) (nth 2 c)) (list (nth 3 c) (nth 4 c))))
                  ES:CORTES))
  (if (= ES:DTRA "1") (setq r (cons (es:corte-aa gs) r)))
  (vl-remove-if 'null r)
)

;;; marcacao dos cortes na planta: traco grosso nas pontas, seta e letra
(defun es:marca-cortes (gs / c a b dc nv)
  (setq c ES:HC)
  (foreach ct (es:cortes-todos gs)
    (setq a (nth 1 ct) b (nth 2 ct) dc (es:mul (es:sub b a) (/ 1.0 (max 1e-6 (es:dist a b))))
          nv (list (- (cadr dc)) (car dc)))
    (foreach en (list (list a dc) (list b (es:mul dc -1.0)))
      (es:pl (list (car en) (es:add (car en) (es:mul (cadr en) (* 1.5 c)))) ES:LAY-EIXO nil nil (* 0.25 c))
      (es:seta (car en) (es:add (car en) (es:mul nv (* 1.4 c))) (* 0.8 c) (* 0.4 c) ES:LAY-EIXO)
      (es:txt (car ct) (es:add (es:add (car en) (es:mul nv (* 1.0 c))) (es:mul (cadr en) (* -1.2 c)))
              1.2 0.0 ES:LAY-EIXO 1 2)))
)

;;; ---- desenho de um corte --------------------------------------------------------
;;; pedaco cortado de um lance/patamar: (tipo ta tb nil nil a b topo k solido)
;;; (a b = fundo em funcao de x, como em es:geo, para usar es:intradorso)
(defun es:pedaco (so a0 dc ta tb / g c s u0 du tl k uk tk ts y0 yy pts b0 b1 um)
  (setq g (nth 8 so) c (cos (nth 2 so)) s (sin (nth 2 so))
        u0 (es:sol-u so a0) du (+ (* (car dc) c) (* (cadr dc) s)))
  ;; pontos de quebra do topo (espelhos)
  (setq ts nil)
  (if (and (= (car so) "L") (> (abs du) 1e-9))
    (progn
      (setq k 1)
      (while (< k (nth 12 g))
        (setq uk (* k (nth 14 g)) tk (/ (- uk u0) du))
        (if (and (> tk (+ ta 1e-6)) (< tk (- tb 1e-6))) (setq ts (cons tk ts)))
        (setq k (1+ k)))))
  (setq ts (append (list ta) (es:ordena ts '(lambda (v) v)) (list tb)) pts nil)
  (while (cdr ts)
    (setq um (+ u0 (* du (* 0.5 (+ (car ts) (cadr ts)))))
          yy (es:sol-top so um)
          pts (cons (list (cadr ts) yy) (cons (list (car ts) yy) pts))
          ts (cdr ts)))
  (setq pts (reverse pts))
  (setq b0 (es:sol-bot so u0) b1 (es:sol-bot so (+ u0 du)))
  (list (car so) ta tb nil nil b0 (- b1 b0) pts (nth 7 so) so
        (if (and (es:cad-fundo g) (> (abs du) 1e-6)) (es:pedaco-fundo so g u0 du ta tb)))
)

;;; fundo quebrado de um pedaco (plissada / aba): cadeia em x do corte
(defun es:pedaco-fundo (so g u0 du ta tb / us ts r a b ya yb eps)
  (setq ts nil eps 0.01)
  (foreach pt (es:cad-fundo g)
    (setq a (/ (- (- (car pt) (nth 1 g)) u0) du))
    (if (and (> a (+ ta eps)) (< a (- tb eps)) (not (vl-some '(lambda (x) (< (abs (- x a)) eps)) ts)))
      (setq ts (cons a ts))))
  (setq ts (append (list ta) (es:ordena ts '(lambda (v) v)) (list tb)) r nil)
  (while (cdr ts)
    (setq a (car ts) b (cadr ts)
          ya (es:sol-bot so (+ u0 (* du (+ a (* eps 0.5)))))
          yb (es:sol-bot so (+ u0 (* du (- b (* eps 0.5))))))
    (if (not (and r (equal (list a ya) (car r) 1e-6))) (setq r (cons (list a ya) r)))
    (setq r (cons (list b yb) r) ts (cdr ts)))
  (reverse r)
)

;;; caixa cortada: (ta tb bot-a bot-b top-a top-b dados quebra-a quebra-b)
(defun es:pedaco-caixa (so a0 dc ta tb / c s u0 du ua ub d)
  (setq c (cos (nth 2 so)) s (sin (nth 2 so)) d (nth 9 so)
        u0 (es:sol-u so a0) du (+ (* (car dc) c) (* (cadr dc) s))
        ua (+ u0 (* du ta)) ub (+ u0 (* du tb)))
  (list ta tb (es:sol-bot so ua) (es:sol-bot so ub) (es:sol-top so ua) (es:sol-top so ub) d
        (and (nth 6 d) (< (abs (- ua (nth 6 d))) 0.5))
        (and (nth 6 d) (< (abs (- ub (nth 6 d))) 0.5)))
)

;;; topo (degraus) de um grupo de pedacos, sem repetidos
(defun es:topo-grupo (g / top)
  (foreach p g (foreach q (nth 7 p) (if (not (and top (equal q (car top) 1e-6))) (setq top (cons q top)))))
  (reverse top)
)

;;; subtrai intervalos: [a b] menos a lista ivs -> lista de intervalos
(defun es:menos (a b ivs / r novo)
  (setq r (list (list a b)))
  (foreach iv ivs
    (setq novo nil)
    (foreach x r
      (if (< (car x) (car iv)) (setq novo (cons (list (car x) (min (cadr x) (car iv))) novo)))
      (if (> (cadr x) (cadr iv)) (setq novo (cons (list (max (car x) (cadr iv)) (cadr x)) novo))))
    (setq r (vl-remove-if '(lambda (q) (< (- (cadr q) (car q)) 0.05)) novo)))
  r
)

;;; trecho da reta dentro da planta do solido ENCOLHIDA de "ins" (um raio que
;;; corre rente a uma face nao e escondido por ela)
(defun es:sol-int-in (so b0 dir t0 t1 ins / iv c s u0 v0 du dv)
  (setq c (cos (nth 2 so)) s (sin (nth 2 so))
        u0 (es:sol-u so b0) v0 (es:sol-v so b0)
        du (+ (* (car dir) c) (* (cadr dir) s))
        dv (- (* (cadr dir) c) (* (car dir) s)))
  (setq iv (es:lb u0 du (+ (nth 3 so) ins) (- (nth 4 so) ins) (list t0 t1)))
  (setq iv (es:lb v0 dv (+ (nth 5 so) ins) (- (nth 6 so) ins) iv))
  (if (and iv (> (- (cadr iv) (car iv)) 0.01)) iv)
)

;;; ponto (x y prof) escondido por algum solido entre o plano do corte e ele?
(defun es:oculto (x y pr sols a0 dc nv / b0 r iv n i rr u)
  (setq b0 (es:add a0 (es:mul dc x)) r nil)
  (foreach so sols
    (if (and (null r) (> pr 1.0) (setq iv (es:sol-int-in so b0 nv 0.0 (- pr 0.8) 0.4)))
      (progn
        (setq i 0 n (max 6 (min 40 (fix (/ (- (cadr iv) (car iv)) 4.0)))))
        (while (and (null r) (<= i n))
          (setq rr (+ (car iv) (* (- (cadr iv) (car iv)) (/ i (float n))))
                u  (es:sol-u so (es:add b0 (es:mul nv rr))))
          (if (and (> y (+ (es:sol-bot so u) 0.3)) (< y (- (es:sol-top so u) 0.3))) (setq r T))
          (setq i (1+ i))))))
  r
)

;;; ponto 3D (x y z) dentro de algum solido (fechado)?
(defun es:dentro3 (pt sols / r u v)
  (foreach so sols
    (if (not r)
      (progn
        (setq u (es:sol-u so pt))
        (if (and (>= u (- (nth 3 so) 1e-6)) (<= u (+ (nth 4 so) 1e-6)))
          (progn
            (setq v (es:sol-v so pt))
            (if (and (>= v (- (nth 5 so) 1e-6)) (<= v (+ (nth 6 so) 1e-6))
                     (>= (caddr pt) (- (es:sol-bot so u) 1e-6)) (<= (caddr pt) (+ (es:sol-top so u) 1e-6)))
              (setq r T)))))))
  r
)

;;; o ponto p da aresta de direcao d e uma DOBRA de verdade do concreto?  Olha
;;; 16 pontos num circulo em volta (plano perpendicular a aresta): nenhum ou
;;; todos cheios = sem aresta (fora ou dentro do concreto); metade, seguidos =
;;; face plana (junta de dois solidos: lance/patamar, viga/laje...); senao e
;;; dobra (inclusive as quebras suaves do fundo).
(defun es:dobra-real (p d so sols / l e1 e2 h cs ok n k a q tr)
  (setq l (sqrt (+ (* (car d) (car d)) (* (cadr d) (cadr d)) (* (caddr d) (caddr d)))))
  (if (< l 1e-9)
    T
    (progn
      (setq d (list (/ (car d) l) (/ (cadr d) l) (/ (caddr d) l)))
      (if (> (abs (caddr d)) 0.99)
        (setq e1 (list (cos (nth 2 so)) (sin (nth 2 so)) 0.0) e2 (list (- (sin (nth 2 so))) (cos (nth 2 so)) 0.0))
        (progn
          (setq h (sqrt (+ (* (car d) (car d)) (* (cadr d) (cadr d))))
                e1 (list (- (/ (cadr d) h)) (/ (car d) h) 0.0)
                ;; e2 = d x e1
                e2 (list (- (* (cadr d) (caddr e1)) (* (caddr d) (cadr e1)))
                         (- (* (caddr d) (car e1)) (* (car d) (caddr e1)))
                         (- (* (car d) (cadr e1)) (* (cadr d) (car e1)))))))
      (setq cs nil k 0)
      (repeat 16
        (setq a (* (+ k 0.5) (/ pi 8.0)) k (1+ k))
        (setq q (list (+ (car p) (* 0.8 (+ (* (cos a) (car e1)) (* (sin a) (car e2)))))
                      (+ (cadr p) (* 0.8 (+ (* (cos a) (cadr e1)) (* (sin a) (cadr e2)))))
                      (+ (caddr p) (* 0.8 (+ (* (cos a) (caddr e1)) (* (sin a) (caddr e2)))))))
        (setq cs (cons (if (es:dentro3 q sols) 1 0) cs)))
      (setq n (apply '+ cs) tr 0 a (es:ultimo cs))
      (foreach q cs (if (/= q a) (setq tr (1+ tr))) (setq a q))
      (cond
        ((or (= n 0) (= n 16)) nil)
        ((and (= n 8) (= tr 2)) nil)
        (t T))))
)

;;; pontos de quebra do intradorso dentro do lance estendido: ((u y) ...)
(defun es:quebras-lance (so g / r uu)
  (foreach pt (nth 9 so)
    (setq uu (- (car pt) (nth 1 g)))
    (if (and (> uu (+ (nth 3 so) 0.01)) (< uu (- (nth 4 so) 0.01)))
      (setq r (cons (list uu (cadr pt)) r))))
  (reverse r)
)

;;; ponto 3D (usa p e ang de es:sol-arestas)
(defun es:p3 (u v y / xy) (setq xy (es:uv p ang u v)) (list (car xy) (cadr xy) y))

;;; arestas de um solido (segmentos 3D na planta: ((x y z) (x y z)))
(defun es:sol-arestas (so / g q r p ang pt e0)
  (setq g (nth 8 so) p (nth 1 so) ang (nth 2 so))
  (setq q (cond
            ((= (car so) "L")
             (append (if (< (nth 3 so) -1e-6) (list (list (nth 3 so) (nth 3 g))))
                     (mapcar '(lambda (pt) (list (- (car pt) (nth 1 g)) (cadr pt))) (nth 7 g))
                     (if (> (nth 4 so) (+ (nth 18 g) 1e-6)) (list (list (nth 4 so) (nth 11 g))))
                     (list (list (nth 4 so) (es:sol-bot so (nth 4 so))))
                     ;; quebras do intradorso dentro do lance
                     (reverse (es:quebras-lance so g))
                     (list (list (nth 3 so) (es:sol-bot so (nth 3 so))))))
            ((and (= (car so) "P") (es:cad-fundo g))
             ;; patamar com a aba da plissada: fundo quebrado
             (append (list (list (nth 3 so) (es:sol-top so (nth 3 so))) (list (nth 4 so) (es:sol-top so (nth 4 so))))
                     (reverse (mapcar '(lambda (pt) (list (- (car pt) (nth 1 g)) (cadr pt))) (es:cad-fundo g)))))
            (t (list (list (nth 3 so) (es:sol-top so (nth 3 so))) (list (nth 4 so) (es:sol-top so (nth 4 so)))
                     (list (nth 4 so) (es:sol-bot so (nth 4 so))) (list (nth 3 so) (es:sol-bot so (nth 3 so)))))))
  (setq r nil e0 (es:ultimo q))
  (foreach pt q
    (foreach v (list (nth 5 so) (nth 6 so))
      (setq r (cons (list (es:p3 (car e0) v (cadr e0)) (es:p3 (car pt) v (cadr pt))) r)))
    (setq r (cons (list (es:p3 (car pt) (nth 5 so) (cadr pt)) (es:p3 (car pt) (nth 6 so) (cadr pt))) r))
    (setq e0 pt))
  r
)

;;; arestas vistas (atras do plano), sem as escondidas: lista de ((x1 y1) (x2 y2))
(defun es:vistas (sols a0 dc nv len / r ar p q x1 x2 d1 d2 iv n i xa xb ya yb pa pb vis ini fim seg ok)
  (setq r nil)
  (foreach so sols
    (foreach ar (es:sol-arestas so)
      (setq p (car ar) q (cadr ar)
            x1 (+ (* (- (car p) (car a0)) (car dc)) (* (- (cadr p) (cadr a0)) (cadr dc)))
            x2 (+ (* (- (car q) (car a0)) (car dc)) (* (- (cadr q) (cadr a0)) (cadr dc)))
            d1 (+ (* (- (car p) (car a0)) (car nv)) (* (- (cadr p) (cadr a0)) (cadr nv)))
            d2 (+ (* (- (car q) (car a0)) (car nv)) (* (- (cadr q) (cadr a0)) (cadr nv))))
      ;; so a parte da frente (prof > 0.5) e dentro do comprimento do corte
      (setq iv (es:lb d1 (- d2 d1) 0.5 1e9 (list 0.0 1.0)))
      (setq iv (es:lb x1 (- x2 x1) 0.0 len iv))
      (if iv
        (progn
          (setq n (max 4 (min 40 (fix (/ (* (- (cadr iv) (car iv)) (distance p q)) 6.0)))) i 0 ini nil)
          (repeat n
            (setq pa (+ (car iv) (* (- (cadr iv) (car iv)) (/ i (float n))))
                  pb (+ (car iv) (* (- (cadr iv) (car iv)) (/ (1+ i) (float n))))
                  xa (* 0.5 (+ pa pb))
                  vis (and (es:dobra-real (list (+ (car p) (* xa (- (car q) (car p))))
                                                (+ (cadr p) (* xa (- (cadr q) (cadr p))))
                                                (+ (caddr p) (* xa (- (caddr q) (caddr p)))))
                                          (list (- (car q) (car p)) (- (cadr q) (cadr p)) (- (caddr q) (caddr p)))
                                          so sols)
                           (not (es:oculto (+ x1 (* xa (- x2 x1))) (+ (caddr p) (* xa (- (caddr q) (caddr p))))
                                           (+ d1 (* xa (- d2 d1))) sols a0 dc nv))))
            (cond
              ((and vis (null ini)) (setq ini pa fim pb))
              (vis (setq fim pb))
              (ini (setq r (cons (list ini fim p q x1 x2) r) ini nil)))
            (setq i (1+ i)))
          (if ini (setq r (cons (list ini fim p q x1 x2) r)))))))
  ;; em coordenadas do corte, sem repetidos e sem os de comprimento zero
  (setq seg nil)
  (foreach s r
    (setq pa (list (+ (nth 4 s) (* (car s) (- (nth 5 s) (nth 4 s))))
                   (+ (caddr (nth 2 s)) (* (car s) (- (caddr (nth 3 s)) (caddr (nth 2 s))))))
          pb (list (+ (nth 4 s) (* (cadr s) (- (nth 5 s) (nth 4 s))))
                   (+ (caddr (nth 2 s)) (* (cadr s) (- (caddr (nth 3 s)) (caddr (nth 2 s)))))))
    (if (> (es:dist pa pb) 0.3)
      (progn
        (setq ok T)
        (foreach z seg
          (if (or (and (< (es:dist pa (car z)) 0.3) (< (es:dist pb (cadr z)) 0.3))
                  (and (< (es:dist pa (cadr z)) 0.3) (< (es:dist pb (car z)) 0.3)))
            (setq ok nil)))
        (if ok (setq seg (cons (list pa pb) seg))))))
  seg
)

;;; partes do segmento sg que nao estao sobre nenhum segmento de "cort"
(defun es:tira-sobrepostos (sg cort / a b l u n r ivs t1 t2 d1 d2)
  (setq a (car sg) b (cadr sg) l (es:dist a b))
  (if (< l 1e-6)
    nil
    (progn
      (setq u (es:mul (es:sub b a) (/ 1.0 l)) n (list (- (cadr u)) (car u)) ivs nil)
      (foreach c cort
        (setq d1 (+ (* (- (car (car c)) (car a)) (car n)) (* (- (cadr (car c)) (cadr a)) (cadr n)))
              d2 (+ (* (- (car (cadr c)) (car a)) (car n)) (* (- (cadr (cadr c)) (cadr a)) (cadr n))))
        (if (and (< (abs d1) 0.2) (< (abs d2) 0.2))
          (progn
            (setq t1 (+ (* (- (car (car c)) (car a)) (car u)) (* (- (cadr (car c)) (cadr a)) (cadr u)))
                  t2 (+ (* (- (car (cadr c)) (car a)) (car u)) (* (- (cadr (cadr c)) (cadr a)) (cadr u))))
            (setq ivs (cons (list (min t1 t2) (max t1 t2)) ivs)))))
      (mapcar '(lambda (iv) (list (es:add a (es:mul u (car iv))) (es:add a (es:mul u (cadr iv)))))
              (es:menos 0.0 l ivs))))
)

;;; desenha o corte ct = (nome A B)
(defun es:des-sec (gs ct / c sols a0 b0 len dc nv pcs cxs iv grupos gr top bot rets cob
                      x1 x2 y xm ang n lv lvs bb xmax ymin s0 s1 k nm so cort du ua ub txt lvl
                      rt u0 tr sg um pv tp)
  (setq c ES:HC sols (es:solidos gs) a0 (nth 1 ct) b0 (nth 2 ct) len (es:dist a0 b0))
  (setq dc (es:mul (es:sub b0 a0) (/ 1.0 (max 1e-6 len))) nv (list (- (cadr dc)) (car dc)))
  ;; pedacos cortados
  (setq pcs nil cxs nil ES:REG (list (list '(0.0 0.0) '(0.0 0.0))))
  (foreach so sols
    (if (setq iv (es:sol-int so a0 dc 0.0 len))
      (if (= (car so) "B")
        (setq cxs (cons (es:pedaco-caixa so a0 dc (car iv) (cadr iv)) cxs))
        (setq pcs (cons (es:pedaco so a0 dc (car iv) (cadr iv)) pcs)))))
  (setq pcs (es:ordena pcs '(lambda (p) (nth 1 p))))
  ;; grupos: trechos vizinhos (k e k+1) que se tocam no corte formam uma peca so
  (setq grupos nil gr nil)
  (foreach p pcs
    (if (and gr (< (abs (- (nth 1 p) (nth 2 (car gr)))) 1.0) (= 1 (abs (- (nth 8 p) (nth 8 (car gr))))))
      (setq gr (cons p gr))
      (progn (if gr (setq grupos (cons (reverse gr) grupos))) (setq gr (list p)))))
  (if gr (setq grupos (cons (reverse gr) grupos)))
  (setq rets (mapcar '(lambda (x) (list (nth 0 x) (nth 1 x) (min (nth 2 x) (nth 3 x)) (max (nth 4 x) (nth 5 x))))
                     cxs)
        cob  (mapcar '(lambda (g) (list (nth 1 (car g)) (nth 2 (es:ultimo g)) (es:intradorso g) (es:topo-grupo g)))
                     grupos))
  ;; ---- preenchimento cinza do concreto cortado (por baixo das linhas)
  (if (= ES:SECFILL "1")
    (progn
      (foreach g grupos
        (setq top nil)
        (foreach p g (foreach q (nth 7 p) (if (not (and top (equal q (car top) 1e-6))) (setq top (cons q top)))))
        (es:hachura (append (reverse top) (reverse (es:intradorso g))) "SOLID" 1.0 ES:LAY-HACH 253))
      (foreach x cxs
        (if (/= (nth 3 (nth 6 x)) "W")
          (es:hachura (list (list (nth 0 x) (nth 2 x)) (list (nth 1 x) (nth 3 x))
                            (list (nth 1 x) (nth 5 x)) (list (nth 0 x) (nth 4 x)))
                      "SOLID" 1.0 ES:LAY-HACH 253)))))
  ;; ---- lajes cortadas
  (foreach g grupos
    (setq top nil)
    (foreach p g (foreach q (nth 7 p) (if (not (and top (equal q (car top) 1e-6))) (setq top (cons q top)))))
    (setq top (reverse top) bot (es:intradorso g))
    (es:pl top ES:LAY-CORTE nil nil nil)
    (es:pl bot ES:LAY-CORTE nil nil nil)
    (foreach sg (es:recorta-v (car (car top)) (cadr (car bot)) (cadr (car top)) rets)
      (es:line (list (car (car top)) (car sg)) (list (car (car top)) (cadr sg)) ES:LAY-CORTE))
    (foreach sg (es:recorta-v (car (es:ultimo top)) (cadr (es:ultimo bot)) (cadr (es:ultimo top)) rets)
      (es:line (list (car (es:ultimo top)) (car sg)) (list (car (es:ultimo top)) (cadr sg)) ES:LAY-CORTE)))
  ;; ---- vigas, paredes e lajes de piso cortadas
  (foreach x cxs
    (setq x1 (nth 0 x) x2 (nth 1 x))
    ;; fundo
    (if (= (nth 3 (nth 6 x)) "W")
      (es:quebra (list (- x1 (* 0.3 c)) (nth 2 x)) (list (+ x2 (* 0.3 c)) (nth 3 x)) ES:LAY-CORTE)
      (es:line (list x1 (nth 2 x)) (list x2 (nth 3 x)) ES:LAY-CORTE))
    ;; topo: visivel fora da laje ou acima dela (viga invertida); dentro, tracejado
    (foreach iv (es:menos x1 x2 (mapcar '(lambda (g) (list (car g) (cadr g))) cob))
      (setq y (list (+ (nth 4 x) (* (- (nth 5 x) (nth 4 x)) (/ (- (car iv) x1) (max 1e-6 (- x2 x1)))))
                    (+ (nth 4 x) (* (- (nth 5 x) (nth 4 x)) (/ (- (cadr iv) x1) (max 1e-6 (- x2 x1)))))))
      (if (nth 5 (nth 6 x))
        (es:quebra (list (car iv) (car y)) (list (cadr iv) (car (cdr y))) ES:LAY-CORTE)
        (es:line (list (car iv) (car y)) (list (cadr iv) (cadr y)) ES:LAY-CORTE)))
    (foreach g cob
      (setq iv (list (max x1 (car g)) (min x2 (cadr g))))
      (if (> (- (cadr iv) (car iv)) 0.5)
        (progn
          (setq y (list (+ (nth 4 x) (* (- (nth 5 x) (nth 4 x)) (/ (- (car iv) x1) (max 1e-6 (- x2 x1)))))
                        (+ (nth 4 x) (* (- (nth 5 x) (nth 4 x)) (/ (- (cadr iv) x1) (max 1e-6 (- x2 x1))))))
                tp (es:y-cadeia (cadddr g) (* 0.5 (+ (car iv) (cadr iv)))))
          (cond
            ((> (max (car y) (cadr y)) (+ tp 0.5))
             (es:line (list (car iv) (car y)) (list (cadr iv) (cadr y)) ES:LAY-CORTE))
            ((and (/= (nth 3 (nth 6 x)) "W") (< (max (car y) (cadr y)) (- tp 0.5)))
             (es:pl (list (list (car iv) (car y)) (list (cadr iv) (cadr y))) ES:LAY-OCULTA nil ES:LT nil))))))
    ;; faces laterais: visiveis fora da laje, tracejadas dentro (ou interrupcao
    ;; na ponta da laje de piso)
    (foreach fc (list (list x1 (nth 2 x) (nth 4 x) (nth 7 x)) (list x2 (nth 3 x) (nth 5 x) (nth 8 x)))
      (if (cadddr fc)
        (es:quebra (list (car fc) (+ (caddr fc) (* 0.3 c))) (list (car fc) (- (cadr fc) (* 0.3 c))) ES:LAY-CORTE)
        (progn
          (setq lv nil)
          (foreach g cob
            (if (and (>= (car fc) (- (car g) 1e-6)) (<= (car fc) (+ (cadr g) 1e-6)))
              (setq lv (list (es:y-cadeia (caddr g) (car fc)) (es:y-cadeia (cadddr g) (car fc))))))
          (if (and lv (car lv) (cadr lv))
            (progn
              (foreach sg (es:recorta-v (car fc) (cadr fc) (caddr fc)
                                        (list (list (- (car fc) 0.01) (+ (car fc) 0.01) (car lv) (cadr lv))))
                (es:line (list (car fc) (car sg)) (list (car fc) (cadr sg)) ES:LAY-CORTE))
              (setq y (list (max (cadr fc) (car lv)) (min (caddr fc) (cadr lv))))
              (if (and (/= (nth 3 (nth 6 x)) "W") (> (- (cadr y) (car y)) 0.5))
                (es:pl (list (list (car fc) (car y)) (list (car fc) (cadr y))) ES:LAY-OCULTA nil ES:LT nil)))
            (es:line (list (car fc) (cadr fc)) (list (car fc) (caddr fc)) ES:LAY-CORTE)))))
    ;; nome grande e secao embaixo: "V3A" / "14/50"
    (setq rt (nth 4 (nth 6 x)) y (- (min (nth 2 x) (nth 3 x)) (* 1.9 c)))
    ;; viga invertida: nome em cima
    (if (and (es:nth 8 (nth 6 x)) (es:apo-inv (es:nth 8 (nth 6 x))))
      (setq y (+ (max (nth 4 x) (nth 5 x)) (* 3.0 c))))
    (if (listp rt)
      (progn
        (es:txt (car rt) (list (* 0.5 (+ x1 x2)) y) 1.3 0.0 ES:LAY-TXT 1 0)
        (if (/= (cadr rt) "") (es:txt (cadr rt) (list (* 0.5 (+ x1 x2)) (- y (* 1.6 c))) 1.0 0.0 ES:LAY-TXT 1 0)))
      (es:txt rt (list (* 0.5 (+ x1 x2)) y) 0.8 0.0 ES:LAY-TXT 1 0)))
  ;; ---- arestas vistas (menos o que coincide com o contorno cortado)
  (setq cort ES:REG ES:REG nil)
  (foreach sg (es:vistas (es:estende sols gs) a0 dc nv len)
    (foreach q (es:tira-sobrepostos sg cort) (es:line (car q) (cadr q) ES:LAY-VISTA)))
  ;; ---- nomes, espessuras e niveis dos trechos cortados
  (setq lvs nil lvl nil)
  (foreach p pcs
    (setq xm (* 0.5 (+ (nth 1 p) (nth 2 p))) y (es:yint p xm) ang (atan (nth 6 p)) n (es:nrm ang)
          so (nth 9 p) nm (nth 8 so)
          du (+ (* (car dc) (cos (nth 2 so))) (* (cadr dc) (sin (nth 2 so))))
          ua (+ (es:sol-u so a0) (* du (nth 1 p))) ub (+ (es:sol-u so a0) (* du (nth 2 p))))
    (if (> (- (nth 2 p) (nth 1 p)) (* 3.0 c))
      (es:txt (es:nome-h nm) (es:add (list xm y) (es:mul n (* -1.6 c))) 0.8 ang ES:LAY-TXT 1 0))
    (if (= (car p) "P")
      (progn
        (es:nivel (list xm (nth 11 nm)) (es:nivtxt (es:nivel-m (nth 11 nm))))
        (setq lvs (cons (nth 11 nm) lvs)))
      (if (> (abs du) 0.5)
        ;; lance cortado ao longo: niveis de partida e de chegada
        (progn
          (setq lvs (cons (nth 3 nm) (cons (nth 4 nm) lvs))
                lvl (cons (list (nth 3 nm) (nth 4 nm) (es:txt-esp nm)) lvl))
          ;; piso (pavimento) no inicio / fim da escada
          (if (and (= (nth 7 so) 0) (< (min ua ub) 0.5))
            (es:nivel (list (+ (nth 1 p) (/ (- 0.0 ua) du) (* (if (> du 0) -6.0 6.0) c)) (nth 3 nm))
                      (es:nivtxt (es:nivel-m (nth 3 nm)))))
          (if (and (= (nth 7 so) (1- (length gs))) (> (max ua ub) (- (nth 18 nm) 0.5)))
            (es:nivel (list (+ (nth 1 p) (/ (- (nth 18 nm) ua) du) (* (if (> du 0) 6.0 -6.0) c)) (nth 4 nm))
                      (es:nivtxt (es:nivel-m (nth 4 nm))))))
        (setq lvs (cons (apply 'min (mapcar 'cadr (nth 7 p))) (cons (apply 'max (mapcar 'cadr (nth 7 p))) lvs))))))
  ;; ---- cotas: larguras cortadas (embaixo) e niveis (a direita)
  (if (and pcs ES:CAIXA)
    (progn
      (setq bb ES:CAIXA ymin (cadr bb) xmax (caddr bb))
      (foreach p pcs
        (setq so (nth 9 p) nm (nth 8 so)
              du (+ (* (car dc) (cos (nth 2 so))) (* (cadr dc) (sin (nth 2 so))))
              ua (+ (es:sol-u so a0) (* du (nth 1 p))) ub (+ (es:sol-u so a0) (* du (nth 2 p))))
        ;; lance cortado de ponta a ponta: "8x28=224"
        (setq txt (if (and (= (car p) "L") (< (abs (- (min ua ub) 0.0)) 0.5)
                           (< (abs (- (max ua ub) (nth 18 nm))) 0.5) (> (abs du) 0.999))
                    (es:txt-pisos nm)
                    (es:f (- (nth 2 p) (nth 1 p)))))
        (es:dimh (nth 1 p) (nth 2 p) (- ymin (* 0.5 c)) (- ymin (* 2.5 c)) txt))
      (setq s0 (apply 'min (mapcar '(lambda (p) (nth 1 p)) pcs))
            s1 (apply 'max (mapcar '(lambda (p) (nth 2 p)) pcs)))
      (if (> (length pcs) 1)
        (es:dimh s0 s1 (- ymin (* 0.5 c)) (- ymin (* 5.0 c)) (es:f (- s1 s0))))
      ;; niveis distintos em ordem; o desnivel de um lance sai como "9x17,5=158"
      (setq lv nil)
      (foreach v (es:ordena lvs '(lambda (v) v))
        (if (not (and lv (< (abs (- v (car lv))) 0.5))) (setq lv (cons v lv))))
      (setq lv (reverse lv) k 0)
      (if (> (length lv) 2)
        (es:dimv (car lv) (es:ultimo lv) (+ xmax (* 0.5 c)) (+ xmax (* 4.5 c)) (es:f (- (es:ultimo lv) (car lv)))))
      (while (cdr lv)
        (setq txt (es:f (- (cadr lv) (car lv))))
        (foreach z lvl
          (if (and (< (abs (- (car z) (car lv))) 0.5) (< (abs (- (cadr z) (cadr lv))) 0.5)) (setq txt (caddr z))))
        (es:dimv (car lv) (cadr lv) (+ xmax (* 0.5 c)) (+ xmax (* 2.0 c)) txt)
        (setq lv (cdr lv)))))
  ;; ---- espelho e piso do 1.o degrau, espessura perpendicular do lance e
  ;;      espessura do patamar (como na prancha modelo)
  (foreach p pcs
    (setq so (nth 9 p) nm (nth 8 so)
          du (+ (* (car dc) (cos (nth 2 so))) (* (cadr dc) (sin (nth 2 so))))
          u0 (es:sol-u so a0) ua (+ u0 (* du (nth 1 p))) ub (+ u0 (* du (nth 2 p))))
    (if (and (= (car p) "L") (> (abs du) 0.98))
      (progn
        ;; 1.o espelho e 1.o piso
        (if (and (<= (min ua ub) 0.5) (>= (max ua ub) (nth 14 nm)))
          (progn
            (setq tr (/ (- 0.0 u0) du) sg (if (> du 0) 1.0 -1.0))
            (es:dimv (nth 3 nm) (+ (nth 3 nm) (nth 13 nm)) tr (- tr (* sg 1.2 c)) (es:f (nth 13 nm)))
            (es:dimh tr (+ tr (* sg (/ (nth 14 nm) (abs du))))
                     (+ (nth 3 nm) (nth 13 nm)) (+ (nth 3 nm) (nth 13 nm) (* 0.9 c)) (es:f (nth 14 nm)))))
        ;; espessura perpendicular no meio do lance
        (setq um (* 0.5 (nth 18 nm)))
        (if (and (>= um (min ua ub)) (<= um (max ua ub)))
          (progn
            (setq tr (/ (- um u0) du) ang (atan (* (nth 6 nm) du)) n (es:nrm ang)
                  xm (list tr (es:sol-bot so um)) y (es:add xm (es:mul n (nth 8 nm))))
            (if (es:cad-fundo nm)
              ;; plissada: espessura da placa no piso
              (es:dimv (es:sol-bot so um) (es:sol-top so um) tr (+ tr (* 1.2 c)) (es:f (nth 8 nm)))
              (es:dim xm y (es:add (es:mul (es:add xm y) 0.5) (es:mul (es:vet ang) (* 1.2 c)))
                      (+ ang (/ pi 2.0)) (es:f (nth 8 nm))))))))
    (if (= (car p) "P")
      ;; espessura do patamar junto ao lance vizinho (ou no inicio)
      (progn
        (setq tr (if (vl-some '(lambda (q) (and (= (car q) "L") (< (abs (- (nth 1 q) (nth 2 p))) 1.0))) pcs)
                   (- (nth 2 p) (* 1.5 c))
                   (+ (nth 1 p) (* 1.5 c))))
        (es:dimv (nth 5 nm) (nth 11 nm) tr tr (es:f (nth 8 nm))))))
  ;; ---- niveis dos patamares VISTOS (atras do plano)
  (foreach so sols
    (if (and (= (car so) "P") (not (vl-some '(lambda (q) (eq (nth 9 q) so)) pcs)))
      (progn
        (setq lv nil)
        (foreach uv (list (list (nth 3 so) (nth 5 so)) (list (nth 4 so) (nth 5 so))
                          (list (nth 3 so) (nth 6 so)) (list (nth 4 so) (nth 6 so)))
          (setq xm (es:uv (nth 1 so) (nth 2 so) (car uv) (cadr uv))
                lv (cons (list (+ (* (- (car xm) (car a0)) (car dc)) (* (- (cadr xm) (cadr a0)) (cadr dc)))
                               (+ (* (- (car xm) (car a0)) (car nv)) (* (- (cadr xm) (cadr a0)) (cadr nv))))
                         lv)))
        (setq x1 (max 0.0 (apply 'min (mapcar 'car lv))) x2 (min len (apply 'max (mapcar 'car lv)))
              y (nth 11 (nth 8 so)))
        (if (and (> (- x2 x1) (* 2.0 c)) (> (apply 'min (mapcar 'cadr lv)) 0.5)
                 (not (es:oculto (* 0.5 (+ x1 x2)) (- y 0.5) (+ (apply 'min (mapcar 'cadr lv)) 1.0) sols a0 dc nv)))
          (es:nivel (list (* 0.5 (+ x1 x2)) y) (es:nivtxt (es:nivel-m y)))))))
  ;; ---- niveis de referencia dos PAVIMENTOS
  (if (and (setq pv (es:lista-pavs)) ES:CAIXA)
    (progn
      (setq bb ES:CAIXA xm (+ (caddr bb) (* 7.0 c)))
      (foreach z pv
        (es:datum (car bb) xm (cadr z) (es:nivtxt-v (caddr z)) (car z)))
      (setq lv pv)
      (while (cdr lv)
        (es:dimv (cadr (car lv)) (cadr (cadr lv)) (- xm (* 1.0 c)) (- xm (* 2.5 c))
                 (es:f (- (cadr (cadr lv)) (cadr (car lv)))))
        (setq lv (cdr lv)))))
  (es:alcas-sec ct pcs cxs a0 dc len)
  (setq bb ES:CAIXA)
  (if bb
    (es:titulo (strcat "CORTE " (car ct) "-" (car ct)) (strcat ES:NOME "   ESC. 1:" ES:ESC)
               (* 0.5 (+ (car bb) (caddr bb))) (- (cadr bb) (* 3.0 c))))
  (if (null pcs) (es:aviso (strcat "o corte " (car ct) "-" (car ct) " nao atravessa nenhum lance/patamar.")))
)

;;; ---- tracar cortes na planta -------------------------------------------------------
;;; ponto do desenho -> cm da planta (considera a planta movida/girada)
(defun es:mundo->planta (p ins o / ip r s q)
  (setq ip (cdr (assoc 10 (entget ins))) r (cdr (assoc 50 (entget ins)))
        s (cdr (assoc 41 (entget ins))))
  (if (null r) (setq r 0.0))
  (if (or (null s) (= s 0.0)) (setq s 1.0))
  (setq q (es:sub (es:p2 p) (es:p2 ip))
        q (list (/ (+ (* (car q) (cos r)) (* (cadr q) (sin r))) s)
                (/ (- (* (cadr q) (cos r)) (* (car q) (sin r))) s)))
  (es:mul (es:sub q (es:p2 o)) ES:UC)
)

(defun es:letra-livre ( / l i usados)
  (setq usados (mapcar 'car ES:CORTES) i 66)
  (if (/= ES:DTRA "1") (setq i 65))
  (while (member (chr i) usados) (setq i (1+ i)))
  (chr i)
)

;;; laco: o usuario traca cortes na planta da escada id (ja desenhada)
(defun es:secao-laco (id / d ors ins o p1 p2 p3 a b nm lc cr cz novo)
  (setq novo nil)
  (while (and (setq d (es:reg-le id)) (setq ors (es:carrega d))
              (setq ins (es:insert-de id "PLA")) (setq o (es:origem ors "PLA"))
              (setq p1 (es:pede-ponto "\nLINHA DE CORTE na planta - primeiro ponto <ENTER = terminar>: " nil)))
    (setq p2 (vl-catch-all-apply 'getpoint (list p1 "\nSegundo ponto da linha de corte: ")))
    (if (and p2 (not (vl-catch-all-error-p p2)))
      (progn
        (setq p3 (es:pede-ponto "\nClique do LADO para onde o corte olha: " nil))
        (es:unidades)
        (setq a (es:mundo->planta p1 ins o) b (es:mundo->planta p2 ins o))
        ;; olha para a esquerda de A->B: se o lado clicado for a direita, inverte
        (if (and p3 (< (- (* (- (car p2) (car p1)) (- (cadr p3) (cadr p1)))
                          (* (- (cadr p2) (cadr p1)) (- (car p3) (car p1)))) 0.0))
          (setq cz a a b b cz))
        (setq lc (es:letra-livre)
              nm (vl-catch-all-apply 'getstring (list (strcat "\nNome do corte <" lc ">: "))))
        (if (or (vl-catch-all-error-p nm) (null nm) (= (vl-string-trim " " nm) "")) (setq nm lc))
        (setq nm (strcase (vl-string-trim " " nm)))
        (if (not (wcmatch nm "#,@,##,@@,@#,#@,@##,##@,@@#,@@@,###"))
          (progn (princ "\nNome invalido (use ate 3 letras/numeros); usei ") (princ lc) (setq nm lc)))
        ;; substitui um corte com o mesmo nome
        (setq ES:CORTES (append (vl-remove-if '(lambda (x) (= (car x) nm)) ES:CORTES)
                                (list (list nm (car a) (cadr a) (car b) (cadr b)))))
        (es:roda 'es:gera (list id ors nil) (strcat "corte " nm))))
  )
  (princ)
)

;;; ==========================================================================
;;; 10.  DETALHAMENTO DA ARMADURA
;;;
;;;  A escada e dividida em DETALHES (D1, D2...): trechos seguidos na mesma
;;;  direcao; um patamar com giro fecha um detalhe e abre o seguinte (entra
;;;  inteiro nos dois).  Cada detalhe e um corte ao longo do eixo do seu 1.o
;;;  lance, feito no modelo 3D:
;;;   - APOIOS reconhecidos: vigas / paredes / lajes de piso que cruzam o eixo
;;;     (perpendiculares a ele); o que corre ao longo (vigas laterais) nao apoia
;;;     essa armadura.  Vaos = entre eixos de apoios; ponta sem apoio = balanco.
;;;   - ARMADURA INFERIOR: acompanha o fundo (intradorso).  Nos cantos em que a
;;;     barra tracionada tenderia a arrancar o cobrimento (quebra lance ->
;;;     patamar superior) as barras sao CRUZADAS: cada uma segue reta e
;;;     ancora lb alem do canto.  Nos outros cantos a barra e dobrada.
;;;   - ARMADURA SUPERIOR: negativos sobre os apoios (fracao do vao de cada
;;;     lado) e barras de canto nas quebras (cruzadas quando necessario), com
;;;     dobras nas pontas.
;;;   - ANCORAGEM nos apoios de extremidade: ate a face oposta do apoio (menos
;;;     o cobrimento), com gancho se a parte reta for menor que lb; ou
;;;     ANCORAGEM QUIMICA (barra reta, profundidade Lq = lb ou informada) no
;;;     apoio marcado como tal.  Laje de piso: reta, lb para dentro da laje.
;;;   - DISTRIBUICAO transversal sobre as barras principais.
;;;  lb pela NBR 6118 (9.4): fbd = eta1 eta2 eta3 fctd; lb = (fi/4)(fyd/fbd)
;;;  >= 25 fi (boa aderencia nas inferiores, ma nas superiores).
;;; ==========================================================================

(defun es:unit (v / l)
  (setq l (distance '(0.0 0.0) (es:p2 v)))
  (if (> l 1e-12) (es:mul v (/ 1.0 l)) '(1.0 0.0))
)
(defun es:cross (a b) (- (* (car a) (cadr b)) (* (cadr a) (car b))))
(defun es:teto (v) (if (> v (fix v)) (1+ (fix v)) (fix v)))

;;; comprimento de ancoragem basico (cm); fi em mm; boa = boa aderencia
(defun es:lb-cm (fi boa / fck fctd fbd fyd n1)
  (setq fck (max 10.0 (es:n ES:FCK))
        fctd (/ (* 0.7 0.3 (expt fck (/ 2.0 3.0))) 1.4)
        n1 (if (<= fi 5.0) 1.4 2.25)
        fyd (/ (if (<= fi 5.0) 600.0 500.0) 1.15)
        fbd (* n1 (if boa 1.0 0.7) fctd))
  (max (/ (* (/ fi 10.0) fyd) (* 4.0 fbd)) (* 25.0 (/ fi 10.0)))
)

(defun es:bit (i) (es:num (nth i ES:BITOLAS)))

;;; ---- polilinhas --------------------------------------------------------------
;;; paralela a pts a distancia d; lado +1 = a esquerda do sentido, -1 = direita
(defun es:offset (pts d lado / segs a u n r l1 cr q s)
  (setq segs nil a (car pts))
  (foreach b (cdr pts)
    (if (> (es:dist a b) 1e-6)
      (progn
        (setq u (es:unit (es:sub b a)) n (list (* lado -1.0 (cadr u)) (* lado (car u))))
        (setq segs (cons (list (es:add a (es:mul n d)) (es:add b (es:mul n d)) u) segs) a b))))
  (setq segs (reverse segs) r (list (car (car segs))) l1 (car segs))
  (foreach l2 (cdr segs)
    (setq cr (es:cross (caddr l1) (caddr l2)))
    (if (< (abs cr) 1e-9)
      (setq r (cons (cadr l1) r))
      (setq q (es:sub (car l2) (car l1))
            s (/ (es:cross q (caddr l2)) cr)
            r (cons (es:add (car l1) (es:mul (caddr l1) s)) r)))
    (setq l1 l2))
  (reverse (cons (cadr l1) r))
)

;;; giro no vertice i (>0 esquerda, <0 direita)
(defun es:giro (pts i)
  (es:cross (es:unit (es:sub (nth i pts) (nth (1- i) pts)))
            (es:unit (es:sub (nth (1+ i) pts) (nth i pts))))
)

;;; distancia ao longo do raio p + s u ate a polilinha (ou nil)
(defun es:raio (p u pts / r a den s tt d)
  (setq a (car pts))
  (foreach b (cdr pts)
    (setq d (es:sub b a) den (es:cross u d))
    (if (> (abs den) 1e-12)
      (progn
        (setq s (/ (es:cross (es:sub a p) d) den) tt (/ (es:cross (es:sub a p) u) den))
        (if (and (> s 0.05) (>= tt -1e-6) (<= tt (+ 1.0 1e-6)) (or (null r) (< s r))) (setq r s))))
    (setq a b))
  r
)

;;; parte da polilinha (crescente em x) entre x1 e x2
(defun es:corta-x (pts x1 x2 / r a y)
  (setq a (car pts) r nil)
  (if (and (>= (car a) (- x1 1e-6)) (<= (car a) (+ x2 1e-6))) (setq r (list a)))
  (foreach b (cdr pts)
    (if (and (< (car a) x1) (> (car b) x1))
      (setq r (cons (list x1 (+ (cadr a) (* (- (cadr b) (cadr a)) (/ (- x1 (car a)) (- (car b) (car a)))))) r)))
    (if (and (>= (car b) (- x1 1e-6)) (<= (car b) (+ x2 1e-6)))
      (setq r (cons b r)))
    (if (and (< (car a) x2) (> (car b) x2))
      (setq r (cons (list x2 (+ (cadr a) (* (- (cadr b) (cadr a)) (/ (- x2 (car a)) (- (car b) (car a)))))) r)))
    (setq a b))
  (reverse r)
)

(defun es:comp (pts / l a)
  (setq l 0.0 a (car pts))
  (foreach b (cdr pts) (setq l (+ l (es:dist a b)) a b))
  l
)

;;; pernas (comprimentos arredondados) de uma barra
(defun es:pernas (pts / r a)
  (setq a (car pts))
  (foreach b (cdr pts) (setq r (cons (es:int (es:dist a b)) r) a b))
  (reverse r)
)

;;; indices dos vertices onde a barra deve ser CRUZADA (canto que arranca o
;;; cobrimento): lado +1 (concreto a esquerda) -> giro a direita; -1 o contrario
(defun es:cantos (pts lado / r i)
  (setq i 1)
  (while (< i (1- (length pts)))
    (if (< (* lado (es:giro pts i)) -1e-3) (setq r (cons i r)))
    (setq i (1+ i)))
  (reverse r)
)

;;; ---- detalhes (segmentos da escada) ------------------------------------------
;;; ((nome (indices) A B) ...): eixo do 1.o lance de cada detalhe
(defun es:arm-detalhes (gs / r cur k nomes refs sols a b iv t1 t2 kl rf nm)
  (setq refs (es:planta-refs gs) sols (es:solidos gs) k 0 cur nil r nil)
  (foreach g gs
    (setq cur (cons k cur))
    (if (and (= (car g) "P") (/= (nth 17 g) 0))
      (setq r (cons (reverse cur) r) cur (list k)))
    (setq k (1+ k)))
  (if (cdr cur) (setq r (cons (reverse cur) r)))
  (if (and cur (null (cdr cur)) (= (car (nth (car cur) gs)) "L")) (setq r (cons cur r)))
  (setq r (vl-remove-if-not
            '(lambda (ix) (vl-some '(lambda (i) (= (car (nth i gs)) "L")) ix))
            (reverse r)))
  (mapcar
    '(lambda (ix)
       (setq kl (car (vl-remove-if-not '(lambda (i) (= (car (nth i gs)) "L")) ix))
             rf (nth kl refs) a (nth 0 rf) b (es:vet (nth 1 rf)) t1 nil t2 nil nm nil)
       (foreach so sols
         (if (and (member (car so) '("L" "P")) (member (nth 7 so) ix)
                  (setq iv (es:sol-int so a b -100000.0 100000.0)))
           (setq t1 (if t1 (min t1 (car iv)) (car iv)) t2 (if t2 (max t2 (cadr iv)) (cadr iv)))))
       (foreach i ix (setq nm (if nm (strcat nm " + " (nth 9 (nth i gs))) (nth 9 (nth i gs)))))
       (list nm ix (es:add a (es:mul b (- t1 80.0))) (es:add a (es:mul b (+ t2 80.0))) (nth 1 rf)))
    r)
)

;;; geometria de um detalhe ao longo da linha A->B:
;;; (pedacos grupo fundo topo-estrutural apoios dc a0 len)
;;; apoio = (ta tb yb yt tipo rotulo apoio-original)
(defun es:arm-geo (gs dt / sols a0 b0 len dc pcs sups iv so d ang pc tl u0 du g ax)
  (setq sols (es:solidos gs) a0 (nth 2 dt) b0 (nth 3 dt) len (es:dist a0 b0)
        dc (es:mul (es:sub b0 a0) (/ 1.0 len)) ang (nth 4 dt) pcs nil sups nil)
  (foreach so sols
    (cond
      ((and (member (car so) '("L" "P")) (member (nth 7 so) (nth 1 dt)))
       (if (setq iv (es:sol-int so a0 dc 0.0 len))
         (setq pcs (cons (es:pedaco so a0 dc (car iv) (cadr iv)) pcs))))
      ((= (car so) "B")
       (setq d (nth 9 so) ax (es:nth 7 d))
       ;; so apoia se cruzar o eixo (perpendicular a ele)
       (if (and ax (< (abs (cos (- ax ang))) 0.5) (setq iv (es:sol-int so a0 dc 0.0 len)))
         (setq pc (es:pedaco-caixa so a0 dc (car iv) (cadr iv))
               sups (cons (list (nth 0 pc) (nth 1 pc) (min (nth 2 pc) (nth 3 pc)) (max (nth 4 pc) (nth 5 pc))
                                (nth 3 d) (nth 4 d) (es:nth 8 d))
                          sups))))))
  (setq pcs (es:ordena pcs '(lambda (p) (nth 1 p)))
        sups (es:ordena sups '(lambda (x) (* 0.5 (+ (car x) (cadr x))))))
  ;; topo estrutural: linha dos cantos internos (lance) / nivel (patamar)
  (setq tl (mapcar '(lambda (p / so g u0 du)
                      (setq so (nth 9 p) g (nth 8 so) u0 (es:sol-u so a0)
                            du (+ (* (car dc) (cos (nth 2 so))) (* (cadr dc) (sin (nth 2 so)))))
                      (cond
                        ((and (= (car p) "L") (es:cad-fundo g))
                         ;; plissada: o topo estrutural e o proprio perfil dos degraus
                         (list "X" (nth 1 p) (nth 2 p) nil nil (nth 3 g) 0.0 nil nil nil (nth 7 p)))
                        ((= (car p) "L")
                         (list "X" (nth 1 p) (nth 2 p) nil nil
                               (+ (nth 3 g) (* u0 (nth 6 g))) (* du (nth 6 g))))
                        (t (list "X" (nth 1 p) (nth 2 p) nil nil (nth 11 g) 0.0))))
                   pcs))
  (list pcs (es:intradorso pcs) (es:intradorso tl) sups dc a0 len)
)

;;; espessura (topo estrutural - fundo) na abscissa x
(defun es:esp-x (bot top x / a b)
  (setq a (es:y-cadeia bot x) b (es:y-cadeia top x))
  (if (and a b) (- b a) 10.0)
)

;;; apoio que contem a abscissa x (com folga tol).  Inferior prefere viga /
;;; parede; superior prefere laje de piso (continuidade).  Entre iguais, o
;;; que vai mais para fora.
(defun es:apoio-em (sups x lado cam tol / r pref)
  (setq pref (if (= cam "S") '("S") '("V" "W")))
  (foreach modo (list T nil)
    (if (null r)
      (foreach s sups
        (if (and (<= (car s) (+ x tol)) (>= (cadr s) (- x tol))
                 (or (not modo) (member (nth 4 s) pref)))
          (if (or (null r) (if (< lado 0) (< (car s) (car r)) (> (cadr s) (cadr r)))) (setq r s))))))
  r
)

;;; ---- ancoragem na ponta de uma barra ---------------------------------------------
;;; pts = barra; fim = T (ultima ponta) ou nil (primeira); cam "I"/"S"
;;; devolve (pts quimica-Lq-ou-nil)
(defun es:arm-ponta (pts fim cam fi geo / p q u lado sup xs xf c lb s s2 e e2 e3 leg lin quim lq ap tp esp
                         bot top yt rest)
  (setq c (es:n ES:COB) bot (nth 1 geo) top (nth 2 geo)
        p (if fim (es:ultimo pts) (car pts))
        q (if fim (nth (- (length pts) 2) pts) (cadr pts))
        u (es:unit (es:sub p q)) lado (if (> (car u) 0.0) 1.0 -1.0)
        lb (es:lb-cm fi (= cam "I"))
        sup (es:apoio-em (nth 3 geo) (car p) lado cam (+ c 4.0))
        xs (if fim (car (es:ultimo bot)) (car (car bot)))
        esp (es:esp-x bot top xs) quim nil)
  (cond
    ;; sem apoio: termina no cobrimento e fecha com gancho ate a outra camada
    ((and (null sup) ES:FORCA-QUIM)
     ;; quimica sem apoio reconhecido: reta, Lq alem da ponta
     (setq lq (if (numberp ES:FORCA-QUIM) ES:FORCA-QUIM (es:teto lb))
           e (es:add p (es:mul u lq)) e2 nil quim (es:int lq)))
    ((null sup)
     (setq s (/ (- (- xs (* lado c)) (car p)) (car u)) e (es:add p (es:mul u s)))
     (setq leg (max 5.0 (- esp (* 2.0 c) (/ fi 10.0))))
     (setq e2 (es:add e (list 0.0 (if (= cam "I") leg (- leg))))))
    (t
     (setq ap (nth 6 sup) tp (nth 4 sup)
           xf (if (> lado 0) (cadr sup) (car sup))                ; face de fora do apoio
           lin (if (> lado 0) (car sup) (cadr sup)))              ; face de dentro
     (cond
       ;; ancoragem QUIMICA: reta, Lq para dentro do apoio a partir da face de dentro
       ((or ES:FORCA-QUIM (and ap (es:apo-quim ap)))
        (setq lq (cond ((numberp ES:FORCA-QUIM) ES:FORCA-QUIM)
                       ((and ap (es:apo-lq ap)) (es:apo-lq ap))
                       (t (es:teto lb)))
              s (+ (/ (- lin (car p)) (car u)) (/ lq (abs (car u)))))
        ;; o furo nao pode sair do apoio: limita na face de fora / fundo
        (setq s2 (/ (- (- xf (* lado c)) (car p)) (car u)))
        (if (< s2 s) (setq s s2))
        (if (< (cadr u) -1e-6)
          (setq s2 (/ (- (+ (nth 2 sup) c) (cadr p)) (cadr u)) s (min s s2)))
        (setq e (es:add p (es:mul u s)) e2 nil
              quim (es:int (abs (/ (- (car e) lin) (car u)))))
        (if (and (< quim (- lq 0.5))
                 (not (vl-some '(lambda (a) (wcmatch a (strcat (car (nth 5 sup)) ":*"))) ES:AVISOS)))
          (setq ES:AVISOS (cons (strcat (car (nth 5 sup)) ": ancoragem quimica limitada a " (itoa quim)
                                        " cm pela geometria do apoio (pedido " (itoa (es:int lq)) " cm)")
                                ES:AVISOS))))
       ;; laje de piso: sobe/desce ate a camada da laje e segue na horizontal lb
       ((= tp "S")
        (setq yt (if (= cam "S") (- (nth 3 sup) c (/ fi 20.0)) (+ (nth 2 sup) c (/ fi 20.0))))
        (setq s (if (> (abs (cadr u)) 1e-6) (/ (- yt (cadr p)) (cadr u)) -1.0)
              s2 (/ (- (- xs (* lado c)) (car p)) (car u)))        ; ate a face da ponta
        (if (or (< s 0.0) (> s (* 3.0 lb))) (setq s 0.0 yt (cadr p)))
        (if (> s (max s2 -10.0))
          ;; nao cabe inclinado ate a laje: sobe/desce na face e entra na laje
          (setq e (es:add p (es:mul u (max s2 -10.0)))
                rest (min lb (max 0.0 (* lado (- (- xf (* lado c)) (car e)))))
                e2 (list (car e) yt)
                e3 (if (> rest 1.0) (list (+ (car e) (* lado rest)) yt)))
          (setq e (es:add p (es:mul u s))
                rest (min lb (max 0.0 (* lado (- (- xf (* lado c)) (car e)))))
                e2 (if (> rest 1.0) (list (+ (car e) (* lado rest)) yt)))))
       ;; viga / parede: ate a face de fora menos o cobrimento; gancho se faltar lb
       (t
        (setq s (/ (- (- xf (* lado c)) (car p)) (car u)))
        (if (< (cadr u) -1e-6)
          (setq s2 (/ (- (+ (nth 2 sup) c) (cadr p)) (cadr u)) s (min s s2)))
        (setq e (es:add p (es:mul u s)))
        (setq lin (abs (/ (- (car e) lin) (car u))))
        (setq leg (if (= cam "I")
                    (min (max (* 1.0 fi) 8.0) (max 0.0 (- (cadr e) (+ (nth 2 sup) c))))
                    (max 5.0 (- esp (* 2.0 c) (/ fi 10.0)))))
        ;; viga INVERTIDA (sem altura para baixo): o gancho da inferior sobe
        (if (and (= cam "I") (< leg 5.0) (> (- (nth 3 sup) c (cadr e)) leg))
          (setq leg (- (min (max (* 1.0 fi) 8.0) (- (nth 3 sup) c (cadr e))))))
        (setq e2 (if (and (or (= cam "S") (< lin (* 0.7 lb))) (> (abs leg) 1.0)) (es:add e (list 0.0 (- leg)))))))))
  (setq pts (if fim (es:remove-nth pts (1- (length pts))) (cdr pts)))
  (setq pts (if fim
              (append pts (vl-remove-if 'null (list e e2 e3)))
              (append (vl-remove-if 'null (list e3 e2 e)) pts)))
  (list (es:limpa pts) quim)
)

;;; tira pontos a menos de 1 cm do anterior
(defun es:limpa (pts / r)
  (foreach p pts (if (not (and r (< (es:dist p (car r)) 1.0))) (setq r (cons p r))))
  (reverse r)
)

;;; prolonga a ponta alem de um canto CRUZADO (sem empuxo ao vazio): reta ate
;;; lb; se a outra camada chegar antes, vai ate ela e DOBRA ao longo dela (para
;;; dentro da outra placa) ate completar lb.  lay = camada da propria barra.
(defun es:arm-cruza (pts fim fi boa outra lay / p q u s d lb e i k dn rest disp r v)
  (setq p (if fim (es:ultimo pts) (car pts))
        q (if fim (nth (- (length pts) 2) pts) (cadr pts))
        u (es:unit (es:sub p q)) lb (if ES:LB-FORCA ES:LB-FORCA (es:lb-cm fi boa))
        s lb r nil)
  ;; barreiras: a outra camada e as faces das pontas do concreto (menos o cobrimento)
  (foreach ob (if (listp (car (car outra))) outra (list outra))
    (if (setq d (es:raio p u ob)) (setq s (min s (max 0.0 (- d 0.5))))))
  (setq e (es:add p (es:mul u s)))
  ;; dobra: direcao do trecho da camada depois do canto (a outra placa)
  (if (and lay (< s (- lb 3.0)))
    (progn
      (setq i nil k 0)
      (foreach v lay (if (and (null i) (< (es:dist v p) 1.5)) (setq i k)) (setq k (1+ k)))
      (if i
        (progn
          (setq v (if fim (es:nth (1+ i) lay) (es:nth (1- i) lay)))
          (if v
            (setq dn (es:unit (es:sub v (nth i lay)))
                  disp (- (es:dist v (nth i lay)) 2.0)
                  rest (min (- lb s) disp))
            (setq rest 0.0))
          (if (> rest 3.0) (setq r (es:add e (es:mul dn rest))))))))
  (if fim
    (append (es:remove-nth pts (1- (length pts))) (vl-remove-if 'null (list e r)))
    (append (vl-remove-if 'null (list r e)) (cdr pts)))
)

;;; parte da camada entre xa e xb; ka / kb = indice do vertice quando a ponta
;;; esta EXATAMENTE num canto (Qk sem deslocamento) - nas quebras verticais
;;; (plissada) o x sozinho nao diz de que lado do canto a barra fica
(defun es:sub-camada (lay xa xb ka kb / r i)
  (if (and ka (or (< ka 0) (>= ka (length lay)))) (setq ka nil))
  (if (and kb (or (< kb 0) (>= kb (length lay)))) (setq kb nil))
  (if (or ka kb)
    (progn
      (setq r nil i 0)
      (foreach p lay
        (if (and (or (null ka) (>= i ka)) (or (null kb) (<= i kb))) (setq r (cons p r)))
        (setq i (1+ i)))
      (setq r (reverse r))
      (es:corta-x r (if ka (car (car r)) xa) (if kb (car (es:ultimo r)) xb)))
    (es:corta-x lay xa xb))
)

;;; indice do canto de uma chave "Qk" sem deslocamento (ou nil)
(defun es:chave-k (key off)
  (if (and (wcmatch key "Q#*") (< (abs (es:n off)) 0.01)) (atoi (substr key 2)))
)

;;; ---- sem EMPUXO AO VAZIO: nenhuma barra longitudinal passa dobrada por um
;;; canto em que a tracao a empurraria para fora do concreto.  A barra que
;;; atravessa um canto assim e dividida nele e as partes sao CRUZADAS
;;; (es:arm-cruza).  Vale para qualquer escada (laje inclinada, quebras
;;; lance/patamar, plissada) e para barras editadas a mao.
(defun es:arm-sem-empuxo (gs defs / dts geos r d i geo tp fi lay lado ks xa xb x0 x1 cs ini pcs msg n k dt a b ka kb)
  (setq dts (es:arm-detalhes gs) geos nil r nil msg nil n 0)
  (foreach d defs
    (setq n (1+ n) i (es:int (es:n (es:ad d 1))) tp (car d) cs nil)
    (if (and (member tp '("0" "1")) (setq dt (es:nth (1- i) dts)))
      (progn
        (if (null (assoc i geos)) (setq geos (cons (cons i (es:arm-geo gs dt)) geos)))
        (setq geo (cdr (assoc i geos)))
        (if (car geo)
          (progn
            (setq fi (es:bit (es:int (es:n (es:ad d 10))))
                  lay (es:arm-camada geo tp fi) lado (if (= tp "0") 1.0 -1.0)
                  xa (+ (es:arm-x geo tp (es:ad d 2)) (es:n (es:ad d 3)))
                  xb (+ (es:arm-x geo tp (es:ad d 4)) (es:n (es:ad d 5))))
            ;; inicio sempre antes do fim
            (if (> xa xb)
              (setq d (list (nth 0 d) (nth 1 d) (nth 4 d) (nth 5 d) (nth 2 d) (nth 3 d)
                            (nth 8 d) (nth 9 d) (nth 6 d) (nth 7 d) (nth 10 d) (nth 11 d) (nth 12 d))
                    x0 xa xa xb xb x0))
            ;; canto interno: pelo indice quando a ponta esta num canto (Qk), senao pelo x
            (setq ka (es:chave-k (nth 2 d) (nth 3 d)) kb (es:chave-k (nth 4 d) (nth 5 d)))
            (foreach k (es:cantos lay lado)
              (if (and (if ka (> k ka) (> (car (nth k lay)) (+ xa 1.0)))
                       (if kb (< k kb) (< (car (nth k lay)) (- xb 1.0))))
                (setq cs (cons (strcat "Q" (itoa k)) cs))))
            (setq cs (reverse cs))))))
    (if cs
      (progn
        (setq a (list (nth 2 d) (nth 3 d) (nth 6 d) (nth 7 d)))
        (foreach k cs
          (setq r (cons (list tp (nth 1 d) (car a) (cadr a) k "0" (caddr a) (cadddr a) "5" "" (nth 10 d) (nth 11 d) (nth 12 d)) r)
                a (list k "0" "5" "")))
        (setq r (cons (list tp (nth 1 d) (car a) (cadr a) (nth 4 d) (nth 5 d) (caddr a) (cadddr a) (nth 8 d) (nth 9 d)
                            (nth 10 d) (nth 11 d) (nth 12 d))
                      r))
        (setq msg (cons (strcat "B" (itoa n) " dividida no(s) canto(s) "
                                (apply 'strcat (mapcar '(lambda (x) (strcat x " ")) cs))
                                "(empuxo ao vazio: barras cruzadas)")
                        msg)))
      (setq r (cons d r))))
  (foreach m (reverse msg) (es:aviso m))
  (reverse r)
)

;;; divide uma polilinha nos vertices ix (indices) -> lista de (pts corte-ini corte-fim)
(defun es:divide (pts ix / r cur i ini)
  (setq i 0 cur nil ini nil)
  (foreach p pts
    (setq cur (cons p cur))
    (if (member i ix)
      (setq r (cons (list (reverse cur) ini T) r) cur (list p) ini T))
    (setq i (1+ i)))
  (reverse (cons (list (reverse cur) ini nil) r))
)

;;; pontos a cada "s" ao longo de uma polilinha, deslocados de d para o lado
(defun es:ao-longo (pts s d lado / r a l0 acc u n k)
  (setq a (car pts) acc (* 0.5 s) r nil)
  (foreach b (cdr pts)
    (setq l0 (es:dist a b))
    (if (> l0 1e-6)
      (progn
        (setq u (es:unit (es:sub b a)) n (list (* lado -1.0 (cadr u)) (* lado (car u))))
        (while (<= acc l0)
          (setq r (cons (es:add (es:add a (es:mul u acc)) (es:mul n d)) r) acc (+ acc s)))
        (setq acc (- acc l0))))
    (setq a b))
  (reverse r)
)

;;; ---- desenho do detalhamento -------------------------------------------------------
;;; contorno simplificado do concreto e dos apoios de um detalhe
(defun es:arm-contorno (geo / pcs top bot c x rt y)
  (setq c ES:HC pcs (car geo) bot (nth 1 geo) top (es:topo-grupo pcs))
  (es:pl top ES:LAY-CORTE nil nil nil)
  (es:pl bot ES:LAY-CORTE nil nil nil)
  (foreach sg (es:recorta-v (car (car top)) (cadr (car bot)) (cadr (car top)) (nth 3 geo))
    (es:line (list (car (car top)) (car sg)) (list (car (car top)) (cadr sg)) ES:LAY-CORTE))
  (foreach sg (es:recorta-v (car (es:ultimo top)) (cadr (es:ultimo bot)) (cadr (es:ultimo top)) (nth 3 geo))
    (es:line (list (car (es:ultimo top)) (car sg)) (list (car (es:ultimo top)) (cadr sg)) ES:LAY-CORTE))
  (foreach s (nth 3 geo)
    (foreach x (list (car s) (cadr s))
      (setq y (if (and (>= x (car (car bot))) (<= x (car (es:ultimo bot)))) (es:y-cadeia bot x) (nth 3 s)))
      (if (and y (> y (nth 2 s))) (es:line (list x (nth 2 s)) (list x y) ES:LAY-CORTE)))
    (if (= (nth 4 s) "W")
      (es:quebra (list (car s) (nth 2 s)) (list (cadr s) (nth 2 s)) ES:LAY-CORTE)
      (es:line (list (car s) (nth 2 s)) (list (cadr s) (nth 2 s)) ES:LAY-CORTE))
    (foreach iv (es:menos (car s) (cadr s) (list (list (car (car bot)) (car (es:ultimo bot)))))
      (es:line (list (car iv) (nth 3 s)) (list (cadr iv) (nth 3 s)) ES:LAY-CORTE))
    (setq rt (nth 5 s))
    (if (listp rt)
      (progn
        (es:txt (car rt) (list (* 0.5 (+ (car s) (cadr s))) (- (nth 2 s) (* 1.9 c))) 1.1 0.0 ES:LAY-TXT 1 0)
        (if (/= (cadr rt) "")
          (es:txt (cadr rt) (list (* 0.5 (+ (car s) (cadr s))) (- (nth 2 s) (* 3.3 c))) 0.8 0.0 ES:LAY-TXT 1 0)))))
  top
)

;;; texto dos apoios reconhecidos de um detalhe
(defun es:arm-apoios (dt geo i / sups r nm ant bot xs xe v)
  (setq sups (nth 3 geo) bot (nth 1 geo) xs (car (car bot)) xe (car (es:ultimo bot)) r nil ant nil)
  (foreach s sups
    (setq nm (car (nth 5 s)) v (* 0.5 (+ (car s) (cadr s))))
    (if ant (setq r (cons (strcat "vao " (car ant) "-" nm " = " (es:f (- v (cadr ant))) " cm") r)))
    (setq ant (list nm v)))
  (strcat "D" (itoa i) " (" (car dt) "): apoios "
          (if sups (apply 'strcat (mapcar '(lambda (s) (strcat (car (nth 5 s)) " ")) sups)) "NENHUM ")
          (if r (strcat "- " (apply 'strcat (mapcar '(lambda (x) (strcat x "; ")) (reverse r)))) "")
          (if (or (null sups) (> (car (car sups)) (+ xs 1.0))) "BALANCO NO INICIO; " "")
          (if (or (null sups) (< (cadr (es:ultimo sups)) (- xe 1.0))) "BALANCO NO FIM; " ""))
)

(defun es:arm-notas (x y apoios quims / c l)
  (setq c ES:HC l (list "NOTAS:"
                        (strcat "1. CONCRETO fck = " ES:FCK " MPa;  COBRIMENTO = " (es:f (es:n ES:COB))
                                " cm;  ACO CA-50 (CA-60 p/ %%c5).")
                        (strcat "2. ANCORAGEM (NBR 6118): lb inferior %%c" (nth ES:AIB ES:BITOLAS) " = "
                                (itoa (es:teto (es:lb-cm (es:bit ES:AIB) T))) " cm;  lb superior %%c"
                                (nth ES:ASB ES:BITOLAS) " = " (itoa (es:teto (es:lb-cm (es:bit ES:ASB) nil))) " cm.")
                        "3. Nos cantos que arrancariam o cobrimento as barras sao CRUZADAS e ancoradas lb.")
        y y)
  (if quims
    (setq l (append l (list (strcat "4. ANCORAGEM QUIMICA: furo com diametro = barra + 4 mm e profundidade Lq"
                                    " indicada, limpo (escova e ar),")
                            "   preenchido com adesivo estrutural a base de epoxi; seguir o fabricante e verificar."))))
  (setq l (append l (list "APOIOS RECONHECIDOS:") apoios))
  (if ES:AVISOS
    (progn
      (setq l (append l (list "ATENCAO:") (reverse ES:AVISOS)))
      (foreach a ES:AVISOS (es:aviso a))))
  (foreach s l
    (es:txt s (list x y) 0.8 0.0 ES:LAY-ARMT 0 0)
    (setq y (- y (* 1.5 c))))
  y
)


;;; ==========================================================================
;;; 11.  ARMADURAS PARAMETRIZADAS  (lista ES:ARMS, editavel na janela)
;;;
;;;  Cada barra (posicao N1, N2... na ordem da lista) e:
;;;   (tipo detalhe inicio desl-ini fim desl-fim ponta-ini valor-ini
;;;    ponta-fim valor-fim bitola espacamento quantidade)
;;;   tipo:   "0" longitudinal INFERIOR   "1" longitudinal SUPERIOR (negativa)
;;;           "2" distribuicao INFERIOR   "3" distribuicao SUPERIOR
;;;   detalhe: "1", "2"... (D1, D2: trechos na mesma direcao)
;;;   inicio / fim: ponto da escada + deslocamento (cm, + = sentido da subida)
;;;           "INI" inicio   "FIM" fim   "Q1".."Qn" quebras da camada
;;;           "A:V3A" eixo do apoio V3A
;;;   pontas: "0" reta  "1" gancho ate a outra camada  "2" dobra (perna cm)
;;;           "3" ancoragem no apoio (automatica)  "4" ancoragem QUIMICA (Lq)
;;;           "5" prolongar reta (cm; vazio = lb)
;;;   quantidade vazia = largura / espacamento (+1); na distribuicao = pelo
;;;   comprimento coberto.
;;;  Os pontos acompanham a geometria: mudou a escada, as barras se ajustam.
;;; ==========================================================================

(setq ES:TIPOS-ARM '("Longitudinal INFERIOR (positiva)" "Longitudinal SUPERIOR (negativa)"
                     "Distribuicao INFERIOR" "Distribuicao SUPERIOR")
      ES:TIPOS-ARM-C '("INF" "SUP" "DIST.INF" "DIST.SUP")
      ES:PONTAS '("Reta" "Gancho ate a outra camada" "Dobra (perna em cm)"
                  "Ancoragem no apoio (automatica)" "Ancoragem QUIMICA (Lq em cm)"
                  "Prolongar reta (cm; vazio = lb)")
      ES:PONTAS-C '("reta" "gancho" "dobra" "apoio" "quimica" "prolonga"))

(defun es:ad (d k) (es:nth k d))

;;; camada de uma barra: paralela ao fundo (inferior) ou ao topo (superior)
(defun es:arm-camada (geo tipo fi / c)
  (setq c (es:n ES:COB))
  (if (member tipo '("0" "2"))
    (es:offset (nth 1 geo) (+ c (/ fi 20.0)) 1.0)
    (es:offset (nth 2 geo) (+ c (/ fi 20.0)) -1.0))
)

;;; pontos notaveis de um detalhe para um tipo: ((chave rotulo x) ...)
(defun es:arm-pontos (geo tipo / cad r k)
  (setq cad (if (member tipo '("0" "2")) (nth 1 geo) (nth 2 geo))
        r (list (list "INI" "Inicio" (car (car cad))) (list "FIM" "Fim" (car (es:ultimo cad)))) k 1)
  (while (< k (1- (length cad)))
    (setq r (append r (list (list (strcat "Q" (itoa k))
                                  (strcat "Quebra " (itoa k) "  (x=" (es:f (- (car (nth k cad)) (car (car cad)))) ")")
                                  (car (nth k cad)))))
          k (1+ k)))
  (foreach s (nth 3 geo)
    (setq r (append r (list (list (strcat "A:" (car (nth 5 s))) (strcat "Apoio " (car (nth 5 s)))
                                  (* 0.5 (+ (car s) (cadr s))))))))
  r
)

(defun es:arm-x (geo tipo key / p)
  (setq p (assoc key (es:arm-pontos geo tipo)))
  (if p (caddr p)
    (progn (es:aviso (strcat "ponto " key " nao existe mais; usei o inicio.")) (caddr (assoc "INI" (es:arm-pontos geo tipo)))))
)

;;; ---- gerador automatico ------------------------------------------------------
(defun es:arm-auto (gs / r dts i geo bl tl c f fi fs sups tc zs zn j s0 s1 xs xe lb pcs ks q cs a b ref
                       ai as ad ais ass ads)
  (setq r nil dts (es:arm-detalhes gs) i 0 c (es:n ES:COB) f (es:n ES:NEGF)
        fi (es:bit ES:AIB) fs (es:bit ES:ASB)
        ai (itoa ES:AIB) as (itoa ES:ASB) ad (itoa ES:ADB) ais ES:AIS ass ES:ASS ads ES:ADS)
  (foreach dt dts
    (setq i (1+ i) geo (es:arm-geo gs dt))
    (if (car geo)
      (progn
        (setq bl (es:arm-camada geo "0" fi) tl (es:arm-camada geo "1" fs)
              xs (car (car (nth 1 geo))) xe (car (es:ultimo (nth 1 geo))) sups (nth 3 geo))
        ;; inferiores: entre inicio / quebras que arrancariam o cobrimento / fim
        (setq ks (append (list "INI") (mapcar '(lambda (k) (strcat "Q" (itoa k))) (es:cantos bl 1.0)) (list "FIM")))
        (while (cdr ks)
          (setq r (cons (list "0" (itoa i) (car ks) "0" (cadr ks) "0"
                              (if (= (car ks) "INI") "3" "5") "" (if (= (cadr ks) "FIM") "3" "5") ""
                              ai ais "")
                        r)
                ks (cdr ks)))
        (setq r (cons (list "2" (itoa i) "INI" "0" "FIM" "0" "0" "" "0" "" ad ads "") r))
        ;; superiores: zonas sobre os apoios e nas quebras (com a referencia)
        ;; apoios agrupados (centros a menos de 60 cm = um apoio so; nome da viga)
        (setq tc nil)
        (foreach s sups
          (setq a (list (* 0.5 (+ (car s) (cadr s))) (strcat "A:" (car (nth 5 s))) (nth 4 s)))
          (if (and tc (< (- (car a) (car (car tc))) 60.0))
            (if (and (= (caddr (car tc)) "S") (/= (caddr a) "S")) (setq tc (cons a (cdr tc))))
            (setq tc (cons a tc))))
        (setq tc (reverse tc) zs nil j 0 lb (+ (es:lb-cm fs nil) 15.0))
        (foreach t0 tc
          (setq a (es:nth (1- j) tc) b (es:nth (1+ j) tc))
          (setq zs (cons (list (if a (- (car t0) (* f (- (car t0) (car a)))) xs)
                               (if a (list (cadr t0) (es:int (- (* f (- (car t0) (car a)))))) (list "INI" 0))
                               (if b (+ (car t0) (* f (- (car b) (car t0)))) xe)
                               (if b (list (cadr t0) (es:int (* f (- (car b) (car t0))))) (list "FIM" 0)))
                         zs)
                j (1+ j)))
        (foreach k (es:cantos tl -1.0)
          (setq q (nth k tl) ref (strcat "Q" (itoa k)))
          (setq zs (cons (list (- (car q) lb) (list ref (es:int (- lb))) (+ (car q) lb) (list ref (es:int lb))) zs)))
        ;; descarta as vazias; encosta no inicio / fim; junta as que se sobrepoem
        (setq zs (vl-remove-if '(lambda (z) (<= (caddr z) (+ (car z) 1.0))) zs))
        (setq zs (mapcar '(lambda (z)
                            (list (car z) (if (<= (car z) (+ xs (* 2.0 c))) (list "INI" 0) (cadr z))
                                  (caddr z) (if (>= (caddr z) (- xe (* 2.0 c))) (list "FIM" 0) (cadddr z))))
                         zs))
        (setq zs (es:ordena zs '(lambda (z) (car z))) zn nil)
        (foreach z zs
          (if (and zn (<= (car z) (+ (caddr (car zn)) 1.0)))
            (if (> (caddr z) (caddr (car zn)))
              (setq zn (cons (list (car (car zn)) (cadr (car zn)) (caddr z) (cadddr z)) (cdr zn))))
            (setq zn (cons z zn))))
        (foreach z (reverse zn)
          ;; quebras dentro da zona dividem a barra (cruzadas)
          (setq cs nil)
          (foreach k (es:cantos tl -1.0)
            (if (and (> (car (nth k tl)) (+ (car z) 1.0)) (< (car (nth k tl)) (- (caddr z) 1.0)))
              (setq cs (cons (strcat "Q" (itoa k)) cs))))
          (setq ks (append (list (cadr z)) (mapcar '(lambda (k) (list k 0)) (reverse cs)) (list (cadddr z))))
          (while (cdr ks)
            (setq a (car ks) b (cadr ks))
            (setq r (cons (list "1" (itoa i) (car a) (itoa (cadr a)) (car b) (itoa (cadr b))
                                (cond ((member (car a) '("INI" "FIM")) "3") ((and (wcmatch (car a) "Q*") (= (cadr a) 0)) "5") (t "2")) ""
                                (cond ((member (car b) '("INI" "FIM")) "3") ((and (wcmatch (car b) "Q*") (= (cadr b) 0)) "5") (t "2")) ""
                                as ass "")
                          r)
                  ks (cdr ks)))
          (setq r (cons (list "3" (itoa i) (car (cadr z)) (itoa (cadr (cadr z))) (car (cadddr z)) (itoa (cadr (cadddr z)))
                              "0" "" "0" "" ad ads "")
                        r))))))
  (reverse r)
)

;;; ---- uma barra da lista -> geometria ---------------------------------------------
;;; devolve (tipo pts fi-indice esp quant quimica comprimento-distr)
(defun es:arm-barra (gs geo d w / tipo fi lay out xa xb x0 x1 sub pts c r q u leg y2 cam quim ptt vl ok esp n dots ka kb)
  (setq tipo (car d) fi (es:bit (es:int (es:n (es:ad d 10)))) c (es:n ES:COB)
        lay (es:arm-camada geo tipo fi)
        out (es:arm-camada geo (if (member tipo '("0" "2")) "1" "0") fi)
        cam (if (member tipo '("0" "2")) "I" "S")
        esp (es:n (es:ad d 11))
        xa (+ (es:arm-x geo tipo (es:ad d 2)) (es:n (es:ad d 3)))
        xb (+ (es:arm-x geo tipo (es:ad d 4)) (es:n (es:ad d 5))))
  (setq ka (es:chave-k (es:ad d 2) (es:ad d 3)) kb (es:chave-k (es:ad d 4) (es:ad d 5)))
  (if (> xa xb) (setq q xa xa xb xb q q ka ka kb kb q))
  (setq x0 (car (car lay)) x1 (car (es:ultimo lay))
        sub (es:sub-camada lay (max x0 xa) (min x1 xb) ka kb) quim nil)
  (cond
    ((< (length sub) 2) nil)
    ((member tipo '("2" "3"))
     ;; distribuicao: pontos ao longo da camada principal (por dentro dela)
     (setq dots (es:ao-longo sub (max 1.0 esp) (/ (+ (es:bit (if (= tipo "2") ES:AIB ES:ASB)) fi) 20.0)
                             (if (= tipo "2") 1.0 -1.0)))
     (setq n (if (es:num (es:ad d 12)) (es:int (es:num (es:ad d 12))) (length dots)))
     (list tipo dots (es:int (es:n (es:ad d 10))) esp n nil (- w (* 2.0 c))))
    (t
     (setq pts sub)
     (foreach fim (list nil T)
       (setq ptt (es:ad d (if fim 8 6)) vl (es:num (es:ad d (if fim 9 7))))
       (cond
         ((= ptt "1")
          (setq q (if fim (es:ultimo pts) (car pts)) y2 (es:y-cadeia out (car q)))
          (if y2 (setq pts (if fim (append pts (list (list (car q) y2))) (cons (list (car q) y2) pts)))))
         ((= ptt "2")
          (setq q (if fim (es:ultimo pts) (car pts))
                leg (if vl vl (max 5.0 (- (es:esp-x (nth 1 geo) (nth 2 geo) (car q)) (* 2.0 c) (/ fi 10.0)))))
          (setq q (list (car q) (+ (cadr q) (if (= cam "I") leg (- leg)))))
          (setq pts (if fim (append pts (list q)) (cons q pts))))
         ((member ptt '("3" "4"))
          (setq ES:FORCA-QUIM (if (= ptt "4") (if vl vl T)))
          (setq r (es:arm-ponta pts fim cam fi geo))
          (setq ES:FORCA-QUIM nil pts (car r))
          (if (cadr r) (setq quim (cadr r))))
         ((= ptt "5")
          (setq ES:LB-FORCA vl)
          (setq pts (es:arm-cruza pts fim fi (= cam "I")
                                  (list out
                                        (list (list (+ (car (car (nth 1 geo))) c) -1e4) (list (+ (car (car (nth 1 geo))) c) 1e4))
                                        (list (list (- (car (es:ultimo (nth 1 geo))) c) -1e4) (list (- (car (es:ultimo (nth 1 geo))) c) 1e4)))
                                  lay)
                ES:LB-FORCA nil))))
     (setq n (if (es:num (es:ad d 12)) (es:int (es:num (es:ad d 12)))
               (1+ (fix (/ (- w (* 2.0 c)) (max 1.0 esp))))))
     (list tipo (es:limpa pts) (es:int (es:n (es:ad d 10))) esp n quim nil)))
)

;;; ---- POSICOES: barras iguais (tipo, bitola, espacamento e forma) = mesma
;;; posicao N no desenho e na tabela (quantidades somadas).  A lista (B1, B2...)
;;; continua uma barra por linha.
(defun es:lista< (a b / r)
  (while (and a b (null r) (= (car a) (car b))) (setq a (cdr a) b (cdr b)))
  (and a b (< (car a) (car b)))
)
(defun es:arm-chave (b / p q)
  (if (member (car b) '("2" "3"))
    (list (car b) (nth 2 b) (es:f (nth 3 b)) (es:teto (nth 6 b)))
    (progn
      (setq p (es:pernas (nth 1 b)) q (reverse p))
      (list (car b) (nth 2 b) (es:f (nth 3 b)) (if (es:lista< q p) q p))))
)
;;; ((indice-na-lista . posicao) ...)
(defun es:arm-posicoes (gs / dts geos k i dt geo b ch chs r n)
  (setq dts (es:arm-detalhes gs) geos nil k 0 chs nil r nil n 0)
  (foreach d ES:ARMS
    (setq k (1+ k) i (es:int (es:n (es:ad d 1))) dt (es:nth (1- i) dts))
    (if dt
      (progn
        (if (null (assoc i geos)) (setq geos (cons (cons i (es:arm-geo gs dt)) geos)))
        (setq geo (cdr (assoc i geos)))
        (if (and (car geo) (setq b (es:arm-barra gs geo d (es:n ES:LAR))))
          (progn
            (setq ch (es:arm-chave b))
            (if (null (assoc ch chs)) (setq n (1+ n) chs (cons (cons ch n) chs)))
            (setq r (cons (cons k (cdr (assoc ch chs))) r)))))))
  (reverse r)
)
(defun es:pos (k / x) (if (setq x (assoc k ES:POSMAP)) (cdr x) k))

;;; texto padrao: "9 N1 %%c10 C/15 C=268"
(defun es:txt-pos (pos b / l)
  (setq l (if (member (car b) '("2" "3")) (es:teto (nth 6 b)) (es:teto (es:comp (nth 1 b)))))
  (strcat (itoa (nth 4 b)) " N" (itoa pos) " %%c " (nth (nth 2 b) ES:BITOLAS)
          " C/" (es:f (nth 3 b)) " C=" (itoa l))
)

;;; comprimento de uma barra (cm, arredondado para cima)
(defun es:comp-barra (b)
  (if (member (car b) '("2" "3")) (es:teto (nth 6 b)) (es:teto (es:comp (nth 1 b))))
)

;;; barra "extraida" (deslocada), com as pernas e o texto ao longo da maior perna
(defun es:barra-extr (pts dy txt lay lt / q a best bl m n ang c)
  (setq c ES:HC q (mapcar '(lambda (p) (list (car p) (+ (cadr p) dy))) pts))
  (es:pl q lay nil lt nil)
  (setq a (car q) bl 0.0)
  (foreach b (cdr q)
    (if (> (es:dist a b) 0.5)
      (progn
        (setq ang (es:leitura (angle (es:p2 a) (es:p2 b))) n (es:nrm ang) m (es:mul (es:add a b) 0.5))
        (es:txt (itoa (es:int (es:dist a b))) (es:add m (es:mul n (* -1.2 c))) 0.75 ang ES:LAY-ARMT 1 0)
        (if (> (es:dist a b) bl) (setq bl (es:dist a b) best (list a b)))))
    (setq a b))
  (if best
    (progn
      (setq ang (es:leitura (angle (es:p2 (car best)) (es:p2 (cadr best)))) n (es:nrm ang)
            m (es:mul (es:add (car best) (cadr best)) 0.5))
      (es:txt txt (es:add m (es:mul n (* 0.6 c))) 0.85 ang ES:LAY-ARMT 1 0)))
)

;;; leque: linhas de um ponto a cada bolinha e o texto no ponto
(defun es:leque (dots apice txt lay / k st i)
  (setq st (max 1 (es:teto (/ (length dots) 12.0))) i 0)
  (foreach p dots
    (if (= 0 (rem i st)) (es:line apice p lay))
    (setq i (1+ i)))
  (es:line apice (es:add apice (list (* (strlen txt) 0.55 0.8 ES:HC) 0.0)) lay)
  (es:txt txt (es:add apice (list 0.0 (* 0.3 ES:HC))) 0.8 0.0 ES:LAY-ARMT 0 0)
)

;;; ---- desenho: um corte armado por detalhe, barras extraidas, lista ---------------
(defun es:des-arm (gs / c dts w i geo defs k pos bars b ymin ymax dyi dys yb ybaixo xmx top xm feitas cxs tx lg plsup fs
                       quims notas lista nb y0 ap bot)
  (setq c ES:HC dts (es:arm-detalhes gs) w (es:n ES:LAR) ES:DESL (list 0.0 0.0)
        ybaixo 0.0 xmx 0.0 ES:AVISOS nil quims nil notas nil lista nil i 0 feitas nil)
  (if (null ES:ARMS) (setq ES:ARMS (es:arm-auto gs)))
  ;; nenhuma barra passa dobrada por canto com empuxo ao vazio
  (setq ES:ARMS (es:arm-sem-empuxo gs ES:ARMS) ES:POSMAP (es:arm-posicoes gs))
  (foreach dt dts
    (setq i (1+ i) geo (es:arm-geo gs dt))
    (if (car geo)
      (progn
        ;; barras deste detalhe (com o numero da posicao)
        (setq bars nil k 0)
        (foreach d ES:ARMS
          (setq k (1+ k))
          (if (= (es:int (es:n (es:ad d 1))) i)
            (if (setq b (es:arm-barra gs geo d w)) (setq bars (cons (cons k b) bars)))))
        (setq bars (reverse bars) cxs nil
              top (es:topo-grupo (car geo)) bot (nth 1 geo)
              ymax (apply 'max (append (mapcar 'cadr top) (mapcar 'cadddr (nth 3 geo))))
              ymin (apply 'min (append (mapcar 'cadr bot) (mapcar 'caddr (nth 3 geo)))))
        ;; espaco para as superiores extraidas em cima
        (setq nb (vl-remove-if-not '(lambda (x) (= (cadr x) "1")) bars)
              dys (if nb (- (+ ymax (* 9.0 c)) (apply 'min (mapcar '(lambda (x) (apply 'min (mapcar 'cadr (caddr x)))) nb))) 0.0)
              y0 (if nb (+ (apply 'max (mapcar '(lambda (x) (apply 'max (mapcar 'cadr (caddr x)))) nb)) dys (* 2.0 c)) (+ ymax (* 4.0 c))))
        ;; superiores extraidas: lugar planejado antes (sem sobrepor), a altura
        ;; do detalhe considera todas
        (setq plsup nil fs feitas)
        (foreach x bars
          (if (and (= (cadr x) "1") (not (member (es:pos (car x)) fs)))
            (setq fs (cons (es:pos (car x)) fs)
                  tx (es:txt-pos (es:pos (car x)) (es:qtd-pos (car x) bars))
                  lg (es:extr-lugar (caddr x) dys (* 3.0 c) cxs tx) cxs (cadr lg)
                  plsup (cons (list x (car lg) tx) plsup))))
        (foreach z plsup
          (setq y0 (max y0 (+ (apply 'max (mapcar 'cadr (caddr (car z)))) (cadr z) (* 2.5 c)))))
        (setq ES:DESL (list (- (car (car bot))) (- ybaixo (* 6.0 c) y0)) ES:CAIXA nil)
        ;; concreto e degraus numerados
        (es:arm-contorno geo)
        (es:arm-num-degraus gs geo)
        ;; barras no lugar; superiores tracejadas
        (foreach x bars
          (setq b (cdr x))
          (cond
            ((= (car b) "0") (es:pl (nth 1 b) ES:LAY-ARMP nil nil nil))
            ((= (car b) "1") (es:pl (nth 1 b) ES:LAY-ARMN nil ES:LT nil))
            (t (foreach p (nth 1 b) (es:circ p (max (/ (es:bit (nth 2 b)) 20.0) (* 0.12 c))
                                             (if (= (car b) "2") ES:LAY-ARMP ES:LAY-ARMN)))))
          (if (nth 5 b) (setq quims (cons (nth 5 b) quims))))
        ;; distribuicao: leque ate o texto (inferior embaixo, superior em cima)
        (foreach x bars
          (setq b (cdr x))
          (if (and (member (car b) '("2" "3")) (nth 1 b))
            (progn
              (setq xm (car (nth (/ (length (nth 1 b)) 2) (nth 1 b))))
              (es:leque (nth 1 b)
                        (list (+ xm (* 3.0 c)) (if (= (car b) "2") (- (es:y-cadeia bot xm) (* 5.0 c)) (+ ymax (* 3.0 c))))
                        (es:txt-pos (es:pos (car x)) b) ES:LAY-ARMT))))
        ;; barras extraidas: inferiores embaixo, superiores em cima (mesma posicao)
        (setq nb (vl-remove-if-not '(lambda (x) (= (cadr x) "0")) bars))
        (if nb
          (progn
            (setq dyi (- (- ymin (* 11.0 c)) (apply 'max (mapcar '(lambda (x) (apply 'max (mapcar 'cadr (caddr x)))) nb))))
            ;; cada POSICAO e extraida uma vez so
            (foreach x nb
              (if (not (member (es:pos (car x)) feitas))
                (progn
                  (setq feitas (cons (es:pos (car x)) feitas)
                        tx (es:txt-pos (es:pos (car x)) (es:qtd-pos (car x) bars))
                        lg (es:extr-lugar (caddr x) dyi (* -3.0 c) cxs tx) cxs (cadr lg))
                  (es:barra-extr (caddr x) (car lg) tx ES:LAY-ARMP nil))))))
        (foreach z (reverse plsup)
          (setq feitas (cons (es:pos (car (car z))) feitas))
          (es:barra-extr (caddr (car z)) (cadr z) (caddr z) ES:LAY-ARMN ES:LT))
        (es:alcas-arm geo i)
        ;; lista (uma linha por posicao)
        (foreach x bars (setq lista (cons x lista)))
        (setq notas (cons (es:arm-apoios dt geo i) notas))
        (es:titulo (strcat "CORTE D" (itoa i) " - " (car dt)) (strcat ES:NOME "   ESC. 1:" ES:ESC)
                   (* 0.5 (+ (car ES:CAIXA) (caddr ES:CAIXA))) (- (cadr ES:CAIXA) (* 3.0 c)))
        (es:alca "ZONA" i nil nil nil (list ES:DESL ES:CAIXA))
        (setq ybaixo (+ (cadr ES:CAIXA) (cadr ES:DESL)) xmx (max xmx (+ (caddr ES:CAIXA) (car ES:DESL)))))))
  ;; notas e lista ao lado
  (setq ES:DESL (list (+ xmx (* 10.0 c)) 0.0) ES:CAIXA nil)
  (setq yb (es:arm-notas 0.0 0.0 (reverse notas) quims))
  (es:arm-tabela (es:agrupa-pos lista) 0.0 (- yb (* 3.0 c)))
  (setq ES:DESL nil)
)

;;; numeros dos degraus (01, 02...) sobre os pisos do corte armado (numeracao
;;; continua desde o 1.o lance, como na planta)
(defun es:arm-num-degraus (gs geo / a0 dc so g ant u0 du a um nd c)
  (setq a0 (nth 5 geo) dc (nth 4 geo) c ES:HC)
  (foreach p (car geo)
    (if (= (car p) "L")
      (progn
        (setq so (nth 9 p) g (nth 8 so) ant 0)
        (foreach h gs (if (and (= (car h) "L") (< (nth 1 h) (nth 1 g))) (setq ant (+ ant (nth 15 h)))))
        (setq u0 (es:sol-u so a0) du (+ (* (car dc) (cos (nth 2 so))) (* (cadr dc) (sin (nth 2 so)))) a nil)
        (foreach q (nth 7 p)
          (if (and a (> (abs (- (car q) (car a))) 1.0) (< (abs (- (cadr q) (cadr a))) 0.1))
            (progn
              (setq um (+ u0 (* du (* 0.5 (+ (car q) (car a)))))
                    nd (+ ant (1+ (fix (/ um (nth 14 g))))))
              (if (and (>= um 0.0) (<= nd (+ ant (nth 15 g))))
                (es:txt (if (< nd 10) (strcat "0" (itoa nd)) (itoa nd))
                        (list (* 0.5 (+ (car q) (car a))) (+ (cadr q) (* 0.5 c))) 0.7 0.0 ES:LAY-TXT 1 0))))
          (setq a q)))))
)

;;; lugar livre para uma barra extraida: desce (passo < 0) ou sobe a partir de dy0
;;; ate a caixa (com folga para os textos) nao bater nas ja colocadas.
;;; devolve (dy caixas)
(defun es:extr-lugar (pts dy0 passo caixas txt / c x0 x1 y0 y1 lt dy ok n bx)
  (setq c ES:HC x0 (apply 'min (mapcar 'car pts)) x1 (apply 'max (mapcar 'car pts))
        y0 (apply 'min (mapcar 'cadr pts)) y1 (apply 'max (mapcar 'cadr pts))
        lt (* 0.5 (strlen txt) 0.6 0.85 c)
        x0 (- (min x0 (- (* 0.5 (+ x0 x1)) lt)) c) x1 (+ (max x1 (+ (* 0.5 (+ x0 x1)) lt)) c)
        dy dy0 n 0 ok nil)
  (while (and (not ok) (< n 40))
    (setq bx (list x0 (+ y0 dy (* -1.8 c)) x1 (+ y1 dy (* 1.8 c))) ok T)
    (foreach b caixas
      (if (and (< (car bx) (caddr b)) (> (caddr bx) (car b)) (< (cadr bx) (cadddr b)) (> (cadddr bx) (cadr b)))
        (setq ok nil)))
    (if (not ok) (setq dy (+ dy passo) n (1+ n))))
  (list dy (cons bx caixas))
)

;;; barra k com a quantidade de TODAS as barras da mesma posicao no detalhe
(defun es:qtd-pos (k bars / b n)
  (setq b (cdr (assoc k bars)) n 0)
  (foreach x bars (if (= (es:pos (car x)) (es:pos k)) (setq n (+ n (nth 4 (cdr x))))))
  (es:setnth b 4 n)
)

;;; lista ((k . barra) ...) -> uma linha por POSICAO, quantidade somada
(defun es:agrupa-pos (lista / r p m)
  (foreach x (es:ordena lista '(lambda (x) (car x)))
    (setq p (es:pos (car x)) m (assoc p r))
    (if m
      (setq r (subst (cons p (es:setnth (cdr m) 4 (+ (nth 4 (cdr m)) (nth 4 (cdr x))))) m r))
      (setq r (cons (cons p (cdr x)) r))))
  (es:ordena r '(lambda (x) (car x)))
)

;;; aco pela bitola (5 mm = CA-60)
(defun es:aco-bit (fi) (if (<= (es:bit fi) 5.0) "60B" "50A"))

;;; LISTA (padrao ACO | POS | BIT | QUANT | COMPRIMENTO UNIT / TOTAL) e RESUMO
(defun es:arm-tabela (lista x0 y0 / h cx y wd res b fi l k m tot aco)
  (setq h ES:HC y y0 cx (list 0.0 6.0 11.0 17.0 23.0 30.0 37.0) wd (* 37.0 h))
  ;; cabecalho
  (es:ret x0 (- y (* 5.0 h)) (+ x0 wd) y ES:LAY-TAB nil)
  (setq k 0)
  (foreach s (list "ACO" "POS" "BIT" "QUANT")
    (es:txt s (list (+ x0 (* h (* 0.5 (+ (nth k cx) (nth (1+ k) cx))))) (- y (* 1.25 h))) 0.8 0.0 ES:LAY-TXT 1 2)
    (setq k (1+ k)))
  (es:txt "COMPRIMENTO" (list (+ x0 (* h 30.0)) (- y (* 1.25 h))) 0.8 0.0 ES:LAY-TXT 1 2)
  (es:line (list (+ x0 (* h 23.0)) (- y (* 2.5 h))) (list (+ x0 wd) (- y (* 2.5 h))) ES:LAY-GRADE)
  (es:txt "UNIT" (list (+ x0 (* h 26.5)) (- y (* 3.25 h))) 0.8 0.0 ES:LAY-TXT 1 2)
  (es:txt "TOTAL" (list (+ x0 (* h 33.5)) (- y (* 3.25 h))) 0.8 0.0 ES:LAY-TXT 1 2)
  (es:txt "mm" (list (+ x0 (* h 14.0)) (- y (* 4.4 h))) 0.7 0.0 ES:LAY-TXT 1 2)
  (es:txt "cm" (list (+ x0 (* h 26.5)) (- y (* 4.4 h))) 0.7 0.0 ES:LAY-TXT 1 2)
  (es:txt "cm" (list (+ x0 (* h 33.5)) (- y (* 4.4 h))) 0.7 0.0 ES:LAY-TXT 1 2)
  (foreach xx (list 6.0 11.0 17.0 23.0)
    (es:line (list (+ x0 (* h xx)) y) (list (+ x0 (* h xx)) (- y (* 5.0 h))) ES:LAY-GRADE))
  (es:line (list (+ x0 (* h 30.0)) (- y (* 2.5 h))) (list (+ x0 (* h 30.0)) (- y (* 5.0 h))) ES:LAY-GRADE)
  (setq y (- y (* 5.0 h)))
  (es:txt (strcat "ARMACOES DA ESCADA " ES:NOME) (list (+ x0 (* 0.5 wd)) (- y (* 0.9 h))) 0.75 0.0 ES:LAY-TXT 1 2)
  (setq y (- y (* 1.8 h)) res nil)
  (foreach x lista
    (setq b (cdr x) fi (nth 2 b) l (es:comp-barra b) k 0)
    (foreach s (list (es:aco-bit fi) (itoa (car x)) (nth fi ES:BITOLAS) (itoa (nth 4 b)) (itoa l) (itoa (* l (nth 4 b))))
      (es:txt s (list (+ x0 (* h (+ (nth (1+ k) cx) -0.8))) (- y (* 0.9 h))) 0.8 0.0 ES:LAY-TXT 2 2)
      (setq k (1+ k)))
    (setq m (assoc fi res))
    (if m (setq res (subst (list fi (+ (cadr m) (* l (nth 4 b)))) m res))
          (setq res (cons (list fi (* l (nth 4 b))) res)))
    (setq y (- y (* 1.8 h))))
  (foreach xx (list 6.0 11.0 17.0 23.0 30.0)
    (es:line (list (+ x0 (* h xx)) (+ y (* 1.8 h (length lista)))) (list (+ x0 (* h xx)) y) ES:LAY-GRADE))
  (es:ret x0 y (+ x0 wd) y0 ES:LAY-TAB nil)
  ;; resumo
  (setq y (- y (* 4.0 h)) y0 y cx (list 0.0 9.0 16.0 26.0 37.0))
  (es:txt "RESUMO DE ACO" (list (+ x0 (* 0.5 wd)) (- y (* 1.0 h))) 0.9 0.0 ES:LAY-TXT 1 2)
  (es:line (list x0 (- y (* 2.0 h))) (list (+ x0 wd) (- y (* 2.0 h))) ES:LAY-GRADE)
  (setq k 0)
  (foreach s (list "ACO" "BIT" "COMPR" "PESO")
    (es:txt s (list (+ x0 (* h (* 0.5 (+ (nth k cx) (nth (1+ k) cx))))) (- y (* 3.0 h))) 0.8 0.0 ES:LAY-TXT 1 2)
    (setq k (1+ k)))
  (setq k 1)
  (foreach s (list "mm" "m" "kgf")
    (es:txt s (list (+ x0 (* h (* 0.5 (+ (nth k cx) (nth (1+ k) cx))))) (- y (* 4.2 h))) 0.7 0.0 ES:LAY-TXT 1 2)
    (setq k (1+ k)))
  (setq y (- y (* 5.0 h)) tot 0.0)
  (es:line (list x0 y) (list (+ x0 wd) y) ES:LAY-GRADE)
  (foreach m (es:ordena res '(lambda (x) (car x)))
    (setq l (/ (cadr m) 100.0) tot (+ tot (* l (nth (car m) ES:MASSAS))) k 0)
    (foreach s (list (es:aco-bit (car m)) (nth (car m) ES:BITOLAS) (itoa (es:teto l))
                     (itoa (es:teto (* l (nth (car m) ES:MASSAS)))))
      (es:txt s (list (+ x0 (* h (* 0.5 (+ (nth k cx) (nth (1+ k) cx))))) (- y (* 0.9 h))) 0.8 0.0 ES:LAY-TXT 1 2)
      (setq k (1+ k)))
    (setq y (- y (* 1.8 h))))
  (foreach xx (list 9.0 16.0 26.0)
    (es:line (list (+ x0 (* h xx)) (- y0 (* 2.0 h))) (list (+ x0 (* h xx)) y) ES:LAY-GRADE))
  (es:line (list x0 y) (list (+ x0 wd) y) ES:LAY-GRADE)
  (es:txt "Peso Total" (list (+ x0 (* h 0.5)) (- y (* 0.9 h))) 0.8 0.0 ES:LAY-TXT 0 2)
  (es:txt "50A =" (list (+ x0 (* h 16.0)) (- y (* 0.9 h))) 0.8 0.0 ES:LAY-TXT 1 2)
  (es:txt (strcat (itoa (es:teto tot)) " kgf") (list (+ x0 (* h 36.0)) (- y (* 0.9 h))) 0.8 0.0 ES:LAY-TXT 2 2)
  (setq y (- y (* 1.8 h)))
  (es:ret x0 y (+ x0 wd) y0 ES:LAY-TAB nil)
)

;;; ---- PLANTA DE ARMACAO: caminho de cada barra na planta ---------------------------
(defun es:des-parm (gs / c w refs k g rf p ang l x dts i dt geo dc a0 k2 d b xa xb vi vs v t1 t2 nb bb lay)
  (setq c ES:HC w (es:n ES:LAR) refs (es:planta-refs gs) k 0
        ES:ARMS (es:arm-sem-empuxo gs ES:ARMS) ES:POSMAP (es:arm-posicoes gs))
  ;; base: contornos, espelhos e numeracao dos degraus
  (setq nb 0)
  (foreach g gs
    (setq rf (nth k refs) p (nth 0 rf) ang (nth 1 rf) l (nth 2 rf))
    (es:pl (list (es:uv p ang 0.0 (nth 3 rf)) (es:uv p ang l (nth 3 rf))
                 (es:uv p ang l (nth 4 rf)) (es:uv p ang 0.0 (nth 4 rf)))
           ES:LAY-VISTA T nil nil)
    (if (= (car g) "L")
      (progn
        (setq x 1)
        (while (< x (nth 12 g))
          (if (< (* x (nth 14 g)) (- l 1e-6))
            (es:line (es:uv p ang (* x (nth 14 g)) (nth 3 rf)) (es:uv p ang (* x (nth 14 g)) (nth 4 rf)) ES:LAY-VISTA))
          (setq x (1+ x)))
        (setq x 1)
        (while (<= x (nth 15 g))
          (es:txt-bloco (list (if (< (+ nb x) 10) (strcat "0" (itoa (+ nb x))) (itoa (+ nb x))))
                        (es:uv p ang (* (- x 0.5) (nth 14 g)) (- (nth 4 rf) (* 0.8 c))) ang 0.55 ES:LAY-TXT)
          (setq x (1+ x)))
        (setq nb (+ nb (nth 15 g)))))
    (setq k (1+ k)))
  ;; apoios (tracejados) com o nome
  (foreach so (es:solidos gs)
    (if (and (= (car so) "B") (nth 8 (nth 9 so)) (/= (nth 3 (nth 9 so)) "S"))
      (es:pl (list (es:uv (nth 1 so) (nth 2 so) (nth 3 so) (nth 5 so)) (es:uv (nth 1 so) (nth 2 so) (nth 4 so) (nth 5 so))
                   (es:uv (nth 1 so) (nth 2 so) (nth 4 so) (nth 6 so)) (es:uv (nth 1 so) (nth 2 so) (nth 3 so) (nth 6 so)))
             ES:LAY-OCULTA T ES:LT nil)))
  ;; barras de cada detalhe, na faixa do lance do detalhe
  (setq dts (es:arm-detalhes gs) i 0 k2 0)
  (foreach dt dts
    (setq i (1+ i) geo (es:arm-geo gs dt) a0 (nth 2 dt) dc (es:vet (nth 4 dt)) vi 0 vs 0)
    (if (car geo)
      (progn
        (setq k2 0)
        (foreach d ES:ARMS
          (setq k2 (1+ k2))
          (if (= (es:int (es:n (es:ad d 1))) i)
            (progn
              (setq xa (+ (es:arm-x geo (car d) (es:ad d 2)) (es:n (es:ad d 3)))
                    xb (+ (es:arm-x geo (car d) (es:ad d 4)) (es:n (es:ad d 5))))
              (if (> xa xb) (setq v xa xa xb xb v))
              (setq xa (max xa (car (car (nth 1 geo)))) xb (min xb (car (es:ultimo (nth 1 geo)))))
              (cond
                ((member (car d) '("0" "1"))
                 ;; longitudinais: uma faixa por barra (inferiores a direita, superiores a esquerda)
                 (if (= (car d) "0")
                   (setq v (- (* (+ 0.12 (* 0.09 vi)) w)) vi (1+ vi))
                   (setq v (* (+ 0.12 (* 0.09 vs)) w) vs (1+ vs)))
                 (setq t1 (es:add (es:add a0 (es:mul dc xa)) (es:mul (es:nrm (nth 4 dt)) v))
                       t2 (es:add (es:add a0 (es:mul dc xb)) (es:mul (es:nrm (nth 4 dt)) v)))
                 (es:pl (list t1 t2) (if (= (car d) "0") ES:LAY-ARMP ES:LAY-ARMN) nil
                        (if (= (car d) "1") ES:LT) (* 0.25 c))
                 (es:txt-bloco (list (strcat "N" (itoa (es:pos k2))))
                               (es:add (es:mul (es:add t1 t2) 0.5) (es:mul (es:nrm (nth 4 dt)) (* 0.9 c)))
                               (nth 4 dt) 0.8 ES:LAY-ARMT))
                (t
                 ;; distribuicao: uma linha transversal no meio do trecho coberto
                 (setq v (* 0.5 (+ xa xb))
                       t1 (es:add (es:add a0 (es:mul dc v)) (es:mul (es:nrm (nth 4 dt)) (- (* 0.5 w) (es:n ES:COB))))
                       t2 (es:add (es:add a0 (es:mul dc v)) (es:mul (es:nrm (nth 4 dt)) (- (es:n ES:COB) (* 0.5 w)))))
                 (es:pl (list t1 t2) (if (= (car d) "2") ES:LAY-ARMP ES:LAY-ARMN) nil
                        (if (= (car d) "3") ES:LT) (* 0.25 c))
                 (es:txt-bloco (list (strcat "N" (itoa (es:pos k2))))
                               (es:add (es:add a0 (es:mul dc (+ v (* 1.0 c)))) (es:mul (es:nrm (nth 4 dt)) (* 0.3 w)))
                               (+ (nth 4 dt) (/ pi 2.0)) 0.8 ES:LAY-ARMT)))))))))
  (setq bb ES:CAIXA)
  (es:titulo (strcat "PLANTA DE ARMACAO - " ES:NOME) (strcat "ESC. 1:" ES:ESC)
             (* 0.5 (+ (car bb) (caddr bb))) (- (cadr bb) (* 3.0 c)))
)

;;; ==========================================================================
;;; 12.  QUANTITATIVO DE CONCRETO E FORMAS  (a partir do modelo)
;;;  Por trecho: volume da secao (degraus + laje, com a cunha da quebra sob o
;;;  patamar) x largura; formas de fundo (descontadas as vigas), laterais
;;;  (sem as laterais encostadas em viga / parede lateral), espelhos e bordas
;;;  livres dos patamares.  Vigas: b x h x comprimento menos o que ja esta na
;;;  laje.  Lajes de piso e paredes de apoio NAO entram (estrutura existente).
;;;  ESTIMATIVA: confira.
;;; ==========================================================================

;;; numero com 2 casas e virgula: 0.625 -> "0,63"
(defun es:f2 (v / c r)
  (setq c (es:int (* (abs v) 100.0)) r (rem c 100))
  (strcat (if (< v -0.004) "-" "") (itoa (/ c 100)) "," (if (< r 10) "0" "") (itoa r))
)

;;; area de um poligono (valor absoluto)
(defun es:area-pol (pts / a p)
  (setq a 0.0 p (es:ultimo pts))
  (foreach q pts
    (setq a (+ a (- (* (car p) (cadr q)) (* (car q) (cadr p)))) p q))
  (abs (* 0.5 a))
)

;;; parte de uma cadeia (x crescente) ABAIXO de yref, com x em [x1, x2]:
;;; (area comprimento-da-cadeia extensao-horizontal)
(defun es:cunha (cad x1 x2 yref / a l e p xa xb ya yb xm k)
  (setq a 0.0 l 0.0 e 0.0 p (car cad))
  (foreach q (cdr cad)
    (setq xa (max x1 (min (car p) (car q))) xb (min x2 (max (car p) (car q))))
    (if (> xb (+ xa 1e-9))
      (progn
        (setq k (/ (- (cadr q) (cadr p)) (- (car q) (car p)))
              ya (- yref (+ (cadr p) (* k (- xa (car p)))))
              yb (- yref (+ (cadr p) (* k (- xb (car p))))))
        (cond
          ((and (<= ya 1e-6) (<= yb 1e-6)) nil)
          ((and (>= ya -1e-6) (>= yb -1e-6))
           (setq a (+ a (* 0.5 (+ ya yb) (- xb xa))) e (+ e (- xb xa))
                 l (+ l (* (- xb xa) (sqrt (+ 1.0 (* k k)))))))
          (t
           (setq xm (+ xa (* (- xb xa) (/ ya (- ya yb)))))
           (if (> ya 0.0)
             (setq a (+ a (* 0.5 ya (- xm xa))) e (+ e (- xm xa))
                   l (+ l (* (- xm xa) (sqrt (+ 1.0 (* k k))))))
             (setq a (+ a (* 0.5 yb (- xb xm))) e (+ e (- xb xm))
                   l (+ l (* (- xb xm) (sqrt (+ 1.0 (* k k)))))))))))
    (setq p q))
  (list a l e)
)

;;; comprimento de sobreposicao de [a1 a2] com [b1 b2]
(defun es:sobrepoe (a1 a2 b1 b2) (max 0.0 (- (min a2 b2) (max a1 b1))))

;;; apoio lateral ativo (viga "1" / parede "2")
(defun es:lat-tipo (lat) (if lat (es:int (es:n (car lat))) 0))

;;; linhas do quantitativo: ((nome volume-cm3 fundo-cm2 lateral-cm2 espelho-cm2 grupo) ...)
;;; grupo "E" escada / "V" viga
(defun es:quant (gs / refs sc k r g rf wt vol fu la es ant prx cw tp sub ext cu lat nlat
                      ap rt lc so d b h ll lov t0 s bx inv c)
  (setq refs (es:planta-refs gs) sc (es:intradorso gs) k 0 r nil)
  (foreach g gs
    (setq rf (nth k refs) wt (- (nth 4 rf) (nth 3 rf))
          ant (es:nth (1- k) gs) prx (es:nth (1+ k) gs))
    (if (= (car g) "L")
      (progn
        ;; secao: degraus + laje entre s0 e s1, mais as cunhas sob patamares vizinhos
        (setq sub (es:corta-x sc (nth 1 g) (nth 2 g))
              vol (es:area-pol (append (nth 7 g) (reverse sub)))
              fu (es:comp sub) ext 0.0)
        (foreach vz (list ant prx)
          (if (and vz (= (car vz) "P"))
            (progn
              (setq cu (es:cunha sc (nth 1 vz) (nth 2 vz) (nth 5 vz)))
              (setq vol (+ vol (car cu)) fu (+ fu (cadr cu))))))
        (setq nlat (- 2 (if (> (es:lat-tipo ES:LATE) 0) 1 0) (if (> (es:lat-tipo ES:LATD) 0) 1 0))
              la (* nlat vol) es (* (nth 12 g) (nth 13 g) wt)
              c (sqrt (+ 1.0 (* (nth 6 g) (nth 6 g))))
              vol (* vol wt) fu (* fu wt)))
      (progn
        (setq vol (* (nth 18 g) wt (nth 8 g)) fu (* (nth 18 g) wt) c 1.0
              es (* (max 0.0 (nth 16 g)) wt))
        ;; o fundo do patamar sob a cunha dos lances vizinhos fica no lance
        (if (or (and ant (= (car ant) "L")) (and prx (= (car prx) "L")))
          (setq cu (es:cunha sc (nth 1 g) (nth 2 g) (nth 5 g))
                fu (max 0.0 (- fu (* (caddr cu) (es:n ES:LAR))))))
        ;; bordas livres: frente (u = 0), fundo (u = L) e lados (v)
        (setq lat (list (- wt (if ant (es:n ES:LAR) 0.0) (if (and prx (member (nth 17 g) '(3 4))) (es:n ES:LAR) 0.0))
                        (- wt (if (and prx (= (nth 17 g) 0)) (es:n ES:LAR) 0.0))
                        (- (nth 18 g) (if (and prx (= (nth 17 g) 1)) (es:n ES:LAR) 0.0))
                        (- (nth 18 g) (if (and prx (= (nth 17 g) 2)) (es:n ES:LAR) 0.0))))
        ;; vigas de borda deste patamar escondem o lado
        (foreach ap ES:APO
          (if (and (= (es:apo-k gs ap) k) (> (es:apo-dir ap) 0) (/= (es:int (es:n (nth 1 ap))) 1))
            (setq lat (es:setnth lat (if (= (es:apo-dir ap) 1) 2 3)
                                 (max 0.0 (- (nth (if (= (es:apo-dir ap) 1) 2 3) lat) (nth 18 g)))))))
        (setq la (* (nth 8 g) (apply '+ (mapcar '(lambda (x) (max 0.0 x)) lat))))))
    ;; fundo apoiado em vigas / paredes transversais (nao invertidas)
    (foreach ap (es:apos-transv)
      (if (and (/= (es:int (es:n (nth 1 ap))) 1) (not (es:apo-inv ap)))
        (progn
          (setq rt (es:apo-ret gs ap) lc (es:sobrepoe (nth 0 rt) (nth 1 rt) (nth 1 g) (nth 2 g)))
          (if (> lc 0.0)
            (setq fu (max 0.0 (- fu (* lc c (min wt (+ (es:n ES:LAR) (es:apo-ext1 ap) (es:apo-ext2 ap)))))))))))
    (setq r (cons (list (nth 9 g) vol fu la es "E") r) k (1+ k)))
  ;; vigas laterais inclinadas dos lances
  (foreach lat (list ES:LATE ES:LATD)
    (if (= (es:lat-tipo lat) 1)
      (progn
        (setq b (es:n (nth 2 lat)) h (es:n (nth 3 lat)) ll 0.0 lov 0.0)
        (foreach g gs
          (if (= (car g) "L")
            (setq c (sqrt (+ 1.0 (* (nth 6 g) (nth 6 g))))
                  ll (+ ll (* (nth 18 g) c))
                  lov (+ lov (* (nth 18 g) c (min h (/ (nth 8 g) (/ 1.0 c))))))))
        (if (> ll 0.0)
          (setq r (cons (list (nth 1 lat) (* b h ll) (* b ll) (- (* 2.0 h ll) lov) 0.0 "V") r))))))
  ;; vigas de apoio (tipo viga): caixa menos o que ja esta dentro da laje
  (foreach so (es:solidos gs)
    (if (and (= (car so) "B") (setq ap (es:nth 8 (nth 9 so))) (= (es:int (es:n (nth 1 ap))) 0))
      (progn
        (setq d (nth 9 so) h (nth 2 d) inv (es:apo-inv ap)
              bx (if (> (es:apo-dir ap) 0) (- (nth 6 so) (nth 5 so)) (- (nth 4 so) (nth 3 so)))
              ll (if (> (es:apo-dir ap) 0) (- (nth 4 so) (nth 3 so)) (- (nth 6 so) (nth 5 so)))
              g (nth 8 so) k (nth 7 so) rf (nth k refs) wt (- (nth 4 rf) (nth 3 rf)))
        (if (> (es:apo-dir ap) 0)
          (progn
            ;; borda: ao longo do trecho (inclinada no lance); faixa dentro da laje
            (setq c (if (= (car g) "L") (sqrt (+ 1.0 (* (nth 6 g) (nth 6 g)))) 1.0)
                  ll (* ll c)
                  t0 (min h (if (= (car g) "L") (* (nth 8 g) c) (nth 8 g)))
                  lov (* t0 (min (nth 18 g) ll))
                  s (max 0.0 (- bx (max 0.0 (es:n (nth 5 ap)))))))
          (progn
            (setq s (es:apo-s gs ap)
                  t0 (min h (max 0.0 (- (es:topo-est gs s) (es:fundo-est gs s))))
                  s (es:sobrepoe (- s (* 0.5 bx)) (+ s (* 0.5 bx)) (es:s-ini gs) (es:s-fim gs))
                  lov (* t0 (min ll wt)))))
        ;; volume: tira a parte dentro da laje; fundo (invertida: so fora da laje);
        ;; laterais: altura toda menos a parte encostada na laje
        (setq r (cons (list (car ap)
                            (max 0.0 (- (* bx h ll) (* s lov)))
                            (if inv (* bx (max 0.0 (- ll (if (> (es:apo-dir ap) 0) (min (nth 18 g) ll) (min ll wt))))) (* bx ll))
                            (max 0.0 (- (* 2.0 h ll) (* (if (> (es:apo-dir ap) 0) (if (> s 0.0) 1.0 0.0) (* 2.0 (/ s (max 1.0 bx)))) lov)))
                            0.0 "V")
                      r)))))
  (reverse r)
)

;;; peso de aco (kgf) da lista de barras
(defun es:aco-kg (gs / dts i geo k b tot w)
  (setq dts (es:arm-detalhes gs) i 0 tot 0.0 w (es:n ES:LAR))
  (if (null ES:ARMS) (setq ES:ARMS (es:arm-auto gs)))
  (setq ES:ARMS (es:arm-sem-empuxo gs ES:ARMS))
  (foreach dt dts
    (setq i (1+ i) geo (es:arm-geo gs dt))
    (if (car geo)
      (foreach d ES:ARMS
        (if (and (= (es:int (es:n (es:ad d 1))) i) (setq b (es:arm-barra gs geo d w)))
          (setq tot (+ tot (* (/ (es:comp-barra b) 100.0) (nth 4 b) (nth (nth 2 b) ES:MASSAS))))))))
  tot
)

;;; totais: (volume-m3 forma-m2 aco-kg ou nil)
(defun es:quant-tot (lin / v f)
  (setq v 0.0 f 0.0)
  (foreach x lin (setq v (+ v (nth 1 x)) f (+ f (nth 2 x) (nth 3 x) (nth 4 x))))
  (list (/ v 1e6) (/ f 1e4))
)

;;; linha de comando
(defun es:quant-print (gs / lin tt kg)
  (setq lin (es:quant gs) tt (es:quant-tot lin))
  (princ (strcat "\n---- QUANTITATIVO - ESCADA " ES:NOME " (estimativa) ----"
                 "\n  ELEMENTO              CONCRETO m3   FORMA m2 (fundo + lateral + espelho)"))
  (foreach x lin
    (princ (strcat "\n  " (substr (strcat (car x) "                      ") 1 22)
                   (substr (strcat (es:f2 (/ (nth 1 x) 1e6)) "            ") 1 14)
                   (es:f2 (/ (+ (nth 2 x) (nth 3 x) (nth 4 x)) 1e4))
                   "  (" (es:f2 (/ (nth 2 x) 1e4)) " + " (es:f2 (/ (nth 3 x) 1e4)) " + " (es:f2 (/ (nth 4 x) 1e4)) ")")))
  (princ (strcat "\n  TOTAL: concreto " (es:f2 (car tt)) " m3 (fck " ES:FCK " MPa),  formas " (es:f2 (cadr tt)) " m2"))
  (if (or ES:ARMS (= ES:DARM "1"))
    (progn
      (setq kg (es:aco-kg gs))
      (princ (strcat "\n  ACO: " (itoa (es:teto kg)) " kgf  -  taxa "
                     (if (> (car tt) 0.0) (itoa (es:int (/ kg (car tt)))) "-") " kg/m3"))))
  (princ "\n  (lajes de piso e paredes de apoio nao incluidas; confira)")
  (princ)
)

;;; ---- desenho: tabela QUANTITATIVO ------------------------------------------------
(defun es:des-qtd (gs / h cx wd y y0 lin tt kg k cab x0 sg)
  (setq h ES:HC lin (es:quant gs) tt (es:quant-tot lin) x0 0.0 y0 0.0 y 0.0
        cx (list 0.0 16.0 25.0 32.0 39.0 46.0 54.0) wd (* 54.0 h))
  (es:txt (strcat "QUANTITATIVO - ESCADA " ES:NOME) (list (* 0.5 wd) (* 1.2 h)) 1.1 0.0 ES:LAY-TIT 1 0)
  ;; cabecalho
  (es:line (list 0.0 (- y (* 5.0 h))) (list wd (- y (* 5.0 h))) ES:LAY-GRADE)
  (setq cab (list "ELEMENTO" "CONCRETO" "FUNDO" "LATERAL" "ESPELHO" "TOTAL") k 0)
  (foreach s cab
    (es:txt s (list (* h (* 0.5 (+ (nth k cx) (nth (1+ k) cx)))) (- y (* (if (< k 2) 2.0 3.6) h))) 0.8 0.0 ES:LAY-TXT 1 2)
    (setq k (1+ k)))
  (es:txt "FORMAS (m2)" (list (* h 39.5) (- y (* 1.1 h))) 0.8 0.0 ES:LAY-TXT 1 2)
  (es:txt "(m3)" (list (* h 20.5) (- y (* 3.4 h))) 0.7 0.0 ES:LAY-TXT 1 2)
  (es:line (list (* h 25.0) (- y (* 2.2 h))) (list wd (- y (* 2.2 h))) ES:LAY-GRADE)
  (foreach xx (list 16.0 25.0)
    (es:line (list (* h xx) y) (list (* h xx) (- y (* 5.0 h))) ES:LAY-GRADE))
  (setq y (- y (* 5.0 h)) sg nil)
  (foreach x lin
    (if (and sg (/= sg (nth 5 x)))
      (es:line (list 0.0 y) (list wd y) ES:LAY-GRADE))
    (setq sg (nth 5 x) k 0)
    (foreach s (list (car x) (es:f2 (/ (nth 1 x) 1e6)) (es:f2 (/ (nth 2 x) 1e4)) (es:f2 (/ (nth 3 x) 1e4))
                     (es:f2 (/ (nth 4 x) 1e4)) (es:f2 (/ (+ (nth 2 x) (nth 3 x) (nth 4 x)) 1e4)))
      (if (= k 0)
        (es:txt s (list (* h 0.6) (- y (* 0.9 h))) 0.8 0.0 ES:LAY-TXT 0 2)
        (es:txt s (list (* h (- (nth (1+ k) cx) 0.8)) (- y (* 0.9 h))) 0.8 0.0 ES:LAY-TXT 2 2))
      (setq k (1+ k)))
    (setq y (- y (* 1.8 h))))
  ;; total
  (es:line (list 0.0 y) (list wd y) ES:LAY-GRADE)
  (es:txt "TOTAL" (list (* h 0.6) (- y (* 0.9 h))) 0.85 0.0 ES:LAY-TXT 0 2)
  (es:txt (es:f2 (car tt)) (list (* h 24.2) (- y (* 0.9 h))) 0.85 0.0 ES:LAY-TXT 2 2)
  (es:txt (es:f2 (cadr tt)) (list (* h 53.2) (- y (* 0.9 h))) 0.85 0.0 ES:LAY-TXT 2 2)
  (setq y (- y (* 1.8 h)))
  (foreach xx (list 16.0 25.0 32.0 39.0 46.0)
    (es:line (list (* h xx) (- y0 (if (> xx 26.0) (* 2.2 h) 0.0))) (list (* h xx) y) ES:LAY-GRADE))
  (es:ret 0.0 y wd y0 ES:LAY-TAB nil)
  ;; aco e observacoes
  (setq y (- y (* 1.6 h)))
  (es:txt (strcat "Concreto: fck = " ES:FCK " MPa") (list 0.0 y) 0.75 0.0 ES:LAY-TXT 0 2)
  (if (or ES:ARMS (= ES:DARM "1"))
    (progn
      (setq kg (es:aco-kg gs) y (- y (* 1.4 h)))
      (es:txt (strcat "Aco (lista de ferros): " (itoa (es:teto kg)) " kgf   -   taxa "
                      (if (> (car tt) 0.0) (itoa (es:int (/ kg (car tt)))) "-") " kg/m3")
              (list 0.0 y) 0.75 0.0 ES:LAY-TXT 0 2)))
  (setq y (- y (* 1.4 h)))
  (es:txt "Estimativa pelo modelo. Lajes de piso e paredes de apoio nao incluidas." (list 0.0 y) 0.65 0.0 ES:LAY-TXT 0 2)
  (setq y (- y (* 1.2 h)))
  (es:txt "Formas: fundo (sem as faixas sobre vigas), laterais livres, espelhos." (list 0.0 y) 0.65 0.0 ES:LAY-TXT 0 2)
)

;;; ==========================================================================
;;; 13.  EDITOR GRAFICO  (comando ESCADAGRAF)
;;;  Os desenhos registram ALCAS (quadrados) nos pontos editaveis:
;;;   DESENVOLVIMENTO: fim do lance (+/- degraus), 1.o degrau (piso x espelho),
;;;     espessura do lance, fim e espessura do patamar, posicao, altura e
;;;     largura das vigas;
;;;   PLANTA DE FORMAS: fim de cada trecho, vigas (mover e pontas = extensoes),
;;;     linhas de corte (pontas e meio);
;;;   ARMADURA: inicio, fim e meio de cada barra (gruda nos pontos da escada).
;;;  Arraste com o mouse (clique na alca, mova, clique); digite um valor +
;;;  ENTER durante o arraste para um valor exato.  Tudo e refeito na hora.
;;;  Alca = (desenho tipo indice ponto-no-bloco direcao descricao extra)
;;; ==========================================================================

;;; ponto local (cm) -> coordenadas do bloco (sem mexer na caixa envolvente)
(defun es:w0 (p / q)
  (setq q (if ES:DESL (es:add p ES:DESL) p))
  (list (+ (car ES:O) (/ (car q) ES:UC)) (+ (cadr ES:O) (/ (cadr q) ES:UC)))
)

(defun es:alca (tipo idx p dir desc extra)
  (if ES:GRP
    (setq ES:PEGAS (cons (list ES:GRP tipo idx (if p (es:w0 p)) dir desc extra) ES:PEGAS)))
)

;;; bloco <-> mundo (insercao movida, girada ou escalada)
(defun es:ins-dados (ins / ed ip r s)
  (setq ed (entget ins) ip (cdr (assoc 10 ed)) r (cdr (assoc 50 ed)) s (cdr (assoc 41 ed)))
  (if (null r) (setq r 0.0))
  (if (or (null s) (= s 0.0)) (setq s 1.0))
  (list (es:p2 ip) r s)
)
(defun es:bloco->mundo (p id3 / r s)
  (setq r (cadr id3) s (caddr id3))
  (es:add (car id3) (list (* s (- (* (car p) (cos r)) (* (cadr p) (sin r))))
                          (* s (+ (* (car p) (sin r)) (* (cadr p) (cos r))))))
)
(defun es:mundo->bloco (p id3 / q r s)
  (setq r (cadr id3) s (caddr id3) q (es:sub (es:p2 p) (car id3)))
  (list (/ (+ (* (car q) (cos r)) (* (cadr q) (sin r))) s)
        (/ (- (* (cadr q) (cos r)) (* (car q) (sin r))) s))
)
;;; vetor em cm locais -> vetor no mundo
(defun es:vet->mundo (v id3)
  (es:sub (es:bloco->mundo (es:mul v (/ 1.0 ES:UC)) id3) (es:bloco->mundo '(0.0 0.0) id3))
)

(defun es:dot (a b) (+ (* (car a) (car b)) (* (cadr a) (cadr b))))
(defun es:arred (v passo) (* passo (es:int (/ v passo))))

;;; ---- alcas ativas: ((alca ponto-mundo dados-da-insercao) ...) -----------------
(defun es:graf-alcas (id / r ins id3 cache c)
  (setq r nil cache nil)
  (foreach h ES:PEGAS
    (if (nth 3 h)
      (progn
        (if (setq c (assoc (car h) cache))
          (setq id3 (cdr c))
          (setq id3 (if (setq ins (es:insert-de id (car h))) (es:ins-dados ins))
                cache (cons (cons (car h) id3) cache)))
        (if id3 (setq r (cons (list h (es:bloco->mundo (nth 3 h) id3) id3) r))))))
  r
)

(defun es:graf-cor (tp)
  (cond ((wcmatch tp "L-*") 5) ((wcmatch tp "P-*") 4) ((wcmatch tp "A-*,V-*,SV-*") 3)
        ((wcmatch tp "C-*,SC-*") 6) (t 1))
)

;;; quadrado (e um X se destacado) para grvecs
(defun es:graf-quad (p r cor x / a b c d)
  (setq a (list (- (car p) r) (- (cadr p) r)) b (list (+ (car p) r) (- (cadr p) r))
        c (list (+ (car p) r) (+ (cadr p) r)) d (list (- (car p) r) (+ (cadr p) r)))
  (append (list cor a b cor b c cor c d cor d a)
          (if x (list cor a c cor b d)))
)

(defun es:graf-tam () (/ (getvar "VIEWSIZE") 110.0))

(defun es:graf-mostra (alcas sel / r v)
  (redraw)
  (setq r (es:graf-tam) v nil)
  (foreach a alcas
    (setq v (append v (es:graf-quad (cadr a) r (if (eq a sel) 2 (es:graf-cor (nth 1 (car a)))) (eq a sel)))))
  (if v (grvecs v))
)

;;; alca mais perto do ponto (dentro de 1,6 x o tamanho)
(defun es:graf-perto (alcas p / r dmin d)
  (setq dmin (* 1.6 (es:graf-tam)) r nil)
  (foreach a alcas
    (if (< (setq d (es:dist (cadr a) p)) dmin) (setq dmin d r a)))
  r
)

;;; ---- valores de um arraste ---------------------------------------------------------
;;; dcm = deslocamento do mouse em cm locais.  Devolve (texto valor desloc-cm-previa)
(defun es:graf-valor (h dcm / tp i d g tr ap n p e v ct x xs best key off pts dir k)
  (setq tp (nth 1 h) i (nth 2 h) dir (nth 4 h)
        d (if dir (es:dot dcm dir) 0.0))
  (cond
    ((= tp "L-FIM")
     (setq g (nth i ES:GS) p (nth 14 g) n (max 1 (+ (nth 12 g) (es:int (/ d p)))))
     (list (strcat (nth 9 g) ":  N = " (itoa n) " espelhos  (" (itoa (+ (nth 15 g) (- n (nth 12 g)))) " pisos)")
           n (es:mul dir (* p (- n (nth 12 g))))))
    ((= tp "L-DEG")
     (setq g (nth i ES:GS)
           p (max 10.0 (es:arred (+ (nth 14 g) (car dcm)) 0.5))
           e (max 5.0 (es:arred (+ (nth 13 g) (cadr dcm)) 0.5)))
     (list (strcat (nth 9 g) ":  piso " (es:f p) " x espelho " (es:f e) "   (2e + p = " (es:f (+ p e e)) ")")
           (list p e) (list (- p (nth 14 g)) (- e (nth 13 g)))))
    ((member tp '("L-H" "P-H"))
     (setq g (nth i ES:GS) v (max 5.0 (es:arred (+ (nth 8 g) d) 1.0)))
     (list (strcat (nth 9 g) ":  espessura h = " (es:f v) " cm") v (es:mul dir (- v (nth 8 g)))))
    ((= tp "P-FIM")
     (setq g (nth i ES:GS) v (max 10.0 (es:arred (+ (nth 18 g) d) 1.0)))
     (list (strcat (nth 9 g) ":  comprimento = " (es:f v) " cm") v (es:mul dir (- v (nth 18 g)))))
    ((= tp "A-MOV")
     (setq ap (nth i ES:APO) v (es:arred (+ (es:n (nth 5 ap)) d) 1.0))
     (list (strcat (car ap) ":  deslocamento do eixo = " (es:f v) " cm") v (es:mul dir (- v (es:n (nth 5 ap))))))
    ((= tp "A-H")
     (setq ap (nth i ES:APO) v (max 5.0 (es:arred (+ (es:n (nth 3 ap)) d) 1.0)))
     (list (strcat (car ap) ":  altura h = " (es:f v) " cm  (" (es:f (es:n (nth 2 ap))) "/" (es:f v) ")")
           v (es:mul dir (- v (es:n (nth 3 ap))))))
    ((= tp "A-B")
     (setq ap (nth i ES:APO) v (max 5.0 (es:arred (+ (es:n (nth 2 ap)) (* 2.0 d)) 1.0)))
     (list (strcat (car ap) ":  largura b = " (es:f v) " cm  (" (es:f v) "/" (es:f (es:n (nth 3 ap))) ")")
           v (es:mul dir (* 0.5 (- v (es:n (nth 2 ap)))))))
    ((= tp "V-MOV")
     (setq ap (nth i ES:APO) v (list (es:arred (car dcm) 1.0) (es:arred (cadr dcm) 1.0)))
     (list (strcat (car ap) ":  mover  dx = " (es:f (car v)) "  dy = " (es:f (cadr v)) " cm") v v))
    ((member tp '("V-E1" "V-E2"))
     (setq ap (nth i ES:APO) k (if (= tp "V-E1") 7 8)
           v (max 0.0 (es:arred (+ (es:n (nth k ap)) d) 1.0)))
     (list (strcat (car ap) ":  extensao = " (es:f v) " cm") v (es:mul dir (- v (es:n (nth k ap))))))
    ((member tp '("C-A" "C-B" "C-M"))
     (setq ct (nth i ES:CORTES) v (list (es:arred (car dcm) 1.0) (es:arred (cadr dcm) 1.0)))
     (list (strcat "Corte " (car ct) "-" (car ct) ":  "
                   (cond ((= tp "C-A") "ponta A") ((= tp "C-B") "ponta B") (t "mover a linha")))
           v v))
    ((member tp '("B-I" "B-F"))
     ;; extra = (pontos-notaveis x-atual chave-campo); gruda no ponto mais perto
     (setq pts (car (nth 6 h)) x (+ (cadr (nth 6 h)) d) best nil
           k (if (= tp "B-I") 2 3) ap (nth i ES:ARMS)
           key (es:ad ap (if (= tp "B-I") 2 4)))
     (foreach q pts
       (if (and (< (abs (- x (caddr q))) (max 3.0 (* 1.2 ES:HC)))
                (or (null best) (< (abs (- x (caddr q))) (abs (- x (caddr best))))))
         (setq best q)))
     (if best
       (setq key (car best) off 0 xs (caddr best))
       (progn
         (setq xs (caddr (assoc key pts)))
         (if (null xs) (setq key "INI" xs (caddr (assoc "INI" pts))))
         (setq off (es:int (- x xs)) xs (+ xs off))))
     (list (strcat "B" (itoa (1+ i)) (if (= tp "B-I") "  inicio: " "  fim: ") key
                   (if (/= off 0) (strcat (if (> off 0) " +" " ") (itoa off)) "  (no ponto)"))
           (list key off) (list (- xs (cadr (nth 6 h))) 0.0)))
    ((= tp "A-DZ")
     (setq ap (nth i ES:APO) v (es:arred (+ (es:apo-dz ap) d) 1.0))
     (list (strcat (car ap) ":  desnivel do topo = " (es:f v) " cm") v (es:mul dir (- v (es:apo-dz ap)))))
    ((= tp "SV-MOV")
     (setq ap (nth i ES:APO) v (es:arred d 1.0))
     (list (strcat (car ap) ":  mover " (es:f v) " cm ao longo do corte") (es:mul (nth 6 h) v) (list v 0.0)))
    ((member tp '("SC-A" "SC-B"))
     (setq ct (nth i ES:CORTES) v (es:arred d 1.0))
     (list (strcat "Corte " (car ct) "-" (car ct) ":  ponta " (if (= tp "SC-A") "A" "B") " " (es:f v) " cm")
           (es:mul (nth 6 h) v) (list v 0.0)))
    ((= tp "B-MOV")
     (setq v (es:int d))
     (list (strcat "B" (itoa (1+ i)) ":  mover a barra " (itoa v) " cm") v (list (float v) 0.0)))
    (t (list tp nil '(0.0 0.0))))
)

;;; valor digitado durante o arraste (absoluto; dois numeros com "/")
(defun es:graf-digitado (h s / tp i nums g ap v)
  (setq tp (nth 1 h) i (nth 2 h)
        nums (vl-remove-if 'null (mapcar 'es:num (apply 'append (mapcar '(lambda (x) (es:split x ";")) (es:split s "/"))))))
  (if nums
    (cond
      ((= tp "L-FIM") (max 1 (es:int (car nums))))
      ((= tp "L-DEG")
       (setq g (nth i ES:GS))
       (list (max 10.0 (car nums)) (if (cadr nums) (max 5.0 (cadr nums)) (nth 13 g))))
      ((member tp '("L-H" "P-H" "A-H" "A-B")) (max 5.0 (car nums)))
      ((= tp "P-FIM") (max 10.0 (car nums)))
      ((member tp '("A-MOV" "A-DZ")) (car nums))
      ((member tp '("SV-MOV" "SC-A" "SC-B")) (es:mul (nth 6 h) (car nums)))
      ((member tp '("V-E1" "V-E2")) (max 0.0 (car nums)))
      ((member tp '("V-MOV" "C-A" "C-B" "C-M")) (list (car nums) (if (cadr nums) (cadr nums) 0.0)))
      ((member tp '("B-I" "B-F"))
       (setq ap (nth i ES:ARMS))
       (list (es:ad ap (if (= tp "B-I") 2 4)) (es:int (car nums))))
      ((= tp "B-MOV") (es:int (car nums)))))
)

;;; ---- aplica um valor no modelo ------------------------------------------------------
(defun es:graf-aplica (h v / tp i tr ap ct d)
  (setq tp (nth 1 h) i (nth 2 h))
  ;; alcas dos cortes: mesmas acoes da planta (valor ja em cm da planta)
  (setq tp (cond ((= tp "SV-MOV") "V-MOV") ((= tp "SC-A") "C-A") ((= tp "SC-B") "C-B") (t tp)))
  (cond
    ((null v) nil)
    ((wcmatch tp "L-*,P-*")
     (setq tr (nth i ES:TRE))
     (cond
       ((= tp "L-FIM") (setq tr (es:setnth tr 2 (itoa v))))
       ((= tp "L-DEG") (setq tr (es:setnth (es:setnth tr 4 (es:f (car v))) 3 (es:f (cadr v)))))
       ((= tp "L-H") (setq tr (es:setnth tr 6 (es:f v))))
       ((= tp "P-FIM") (setq tr (es:setnth tr 2 (es:f v))))
       ((= tp "P-H") (setq tr (es:setnth tr 3 (es:f v)))))
     (setq ES:TRE (es:setnth ES:TRE i tr)))
    ((wcmatch tp "A-*,V-*")
     (setq ap (nth i ES:APO))
     (cond
       ((= tp "A-MOV") (setq ap (es:setnth ap 5 (es:f v))))
       ((= tp "A-H") (setq ap (es:setnth ap 3 (es:f v))))
       ((= tp "A-B") (setq ap (es:setnth ap 2 (es:f v))))
       ((= tp "A-DZ") (setq ap (es:setnth ap 12 (es:f v))))
       ((= tp "V-MOV") (setq ap (es:apo-move ap v ES:GS)))
       ((= tp "V-E1") (setq ap (es:setnth ap 7 (es:f v))))
       ((= tp "V-E2") (setq ap (es:setnth ap 8 (es:f v)))))
     (setq ES:APO (es:setnth ES:APO i ap)))
    ((wcmatch tp "C-*")
     (setq ct (nth i ES:CORTES))
     (if (member tp '("C-A" "C-M"))
       (setq ct (es:setnth (es:setnth ct 1 (+ (nth 1 ct) (car v))) 2 (+ (nth 2 ct) (cadr v)))))
     (if (member tp '("C-B" "C-M"))
       (setq ct (es:setnth (es:setnth ct 3 (+ (nth 3 ct) (car v))) 4 (+ (nth 4 ct) (cadr v)))))
     (setq ES:CORTES (es:setnth ES:CORTES i ct)))
    ((wcmatch tp "B-*")
     (setq d (nth i ES:ARMS))
     (cond
       ((= tp "B-I") (setq d (es:setnth (es:setnth d 2 (car v)) 3 (itoa (cadr v)))))
       ((= tp "B-F") (setq d (es:setnth (es:setnth d 4 (car v)) 5 (itoa (cadr v)))))
       ((= tp "B-MOV")
        (setq d (es:setnth (es:setnth d 3 (itoa (+ (es:int (es:n (es:ad d 3))) v)))
                           5 (itoa (+ (es:int (es:n (es:ad d 5))) v))))))
     (setq ES:ARMS (es:setnth ES:ARMS i d))))
)

;;; ---- arraste de uma alca: devolve o valor (ou nil = cancelado) ----------------------
(defun es:graf-arrasta (a alcas / h p0 id3 fim r g dcm vv buf pp c)
  (setq h (car a) p0 (cadr a) id3 (caddr a) fim nil r nil buf "")
  (princ (strcat "\n" (nth 5 h) "  - mova e clique  (ou digite o valor + ENTER; ESC / botao direito = cancela)"))
  (while (not fim)
    (setq g (vl-catch-all-apply 'grread (list T 15 0)))
    (cond
      ((vl-catch-all-error-p g) (setq fim T r nil))
      ((member (car g) '(5 3))
       (setq dcm (es:mul (es:sub (es:mundo->bloco (cadr g) id3) (es:mundo->bloco p0 id3)) ES:UC)
             vv (es:graf-valor h dcm)
             pp (es:add p0 (es:vet->mundo (caddr vv) id3)))
       (es:graf-mostra alcas a)
       (grvecs (append (list -2 p0 pp) (es:graf-quad pp (es:graf-tam) 2 T)))
       (grtext -1 (if (/= buf "") (strcat "Valor: " buf) (car vv)))
       (if (= (car g) 3)
         (progn (setq r (cadr vv) fim T) (princ (strcat "\n" (car vv))))))
      ((= (car g) 2)
       (setq c (cadr g))
       (cond
         ((member c '(13 32))
          (if (/= buf "")
            (progn (setq r (es:graf-digitado h buf) fim T)
                   (if (null r) (princ (strcat "\nValor invalido: " buf))))
            (setq fim T r nil)))
         ((= c 27) (setq fim T r nil))
         ((= c 8) (if (> (strlen buf) 0) (setq buf (substr buf 1 (1- (strlen buf))))) (grtext -1 (strcat "Valor: " buf)))
         ((or (and (>= c 48) (<= c 57)) (member c '(44 45 46 47 59)))
          (setq buf (strcat buf (chr c))) (grtext -1 (strcat "Valor: " buf)))))
      ((member (car g) '(11 25)) (setq fim T r nil))))
  r
)

;;; ---- comandos por tecla ---------------------------------------------------------------
;;; ponto do mundo -> (grp ponto-local) no desenho LON / PLA / ARM (ou nil)
(defun es:graf-onde (id ors p grp / ins o q)
  (if (and (setq ins (es:insert-de id grp)) (setq o (es:origem ors grp)))
    (es:mul (es:sub (es:mundo->bloco p (es:ins-dados ins)) (es:p2 o)) ES:UC))
)

;;; lance sob o ponto: (indice degrau) no desenvolvimento ou na planta
(defun es:graf-lance-em (id ors p / q r k refs rf u v g)
  (setq r nil)
  (if (setq q (es:graf-onde id ors p "LON"))
    (progn
      (setq k 0)
      (foreach g ES:GS
        (if (and (null r) (= (car g) "L") (>= (car q) (nth 1 g)) (<= (car q) (nth 2 g))
                 (>= (cadr q) (- (es:yint g (car q)) 20.0)) (<= (cadr q) (+ (nth 4 g) 20.0)))
          (setq r (list k (- (car q) (nth 1 g)))))
        (setq k (1+ k)))))
  (if (and (null r) (setq q (es:graf-onde id ors p "PLA")))
    (progn
      (setq refs (es:planta-refs ES:GS) k 0)
      (foreach g ES:GS
        (setq rf (nth k refs)
              u (es:dot (es:sub q (nth 0 rf)) (es:vet (nth 1 rf)))
              v (es:dot (es:sub q (nth 0 rf)) (es:nrm (nth 1 rf))))
        (if (and (null r) (= (car g) "L") (>= u 0.0) (<= u (nth 2 rf)) (>= v (nth 3 rf)) (<= v (nth 4 rf)))
          (setq r (list k u)))
        (setq k (1+ k)))))
  (if r
    (progn
      (setq g (nth (car r) ES:GS))
      (list (car r) (max 1 (min (1- (nth 12 g)) (1+ (fix (/ (cadr r) (nth 14 g))))))))
  )
)

;;; renumera "LANCE n" / "PATAMAR n" na ordem
(defun es:renumera ( / nl np r)
  (setq nl 0 np 0 r nil)
  (foreach tr ES:TRE
    (if (es:lance-p tr)
      (progn (setq nl (1+ nl))
             (if (wcmatch (strcase (nth 1 tr)) "LANCE #*") (setq tr (es:setnth tr 1 (strcat "LANCE " (itoa nl))))))
      (progn (setq np (1+ np))
             (if (wcmatch (strcase (nth 1 tr)) "PATAMAR #*") (setq tr (es:setnth tr 1 (strcat "PATAMAR " (itoa np)))))))
    (setq r (cons tr r)))
  (setq ES:TRE (reverse r))
)

;;; divide o lance k no degrau j: lance (j espelhos) + patamar + lance (resto)
(defun es:divide-lance (k j lp / tr n a b pt r jj kk f)
  (setq tr (nth k ES:TRE) n (es:int (es:n (nth 2 tr))))
  (if (and (> n 1) (>= j 1) (< j n))
    (progn
      (setq a (es:setnth (es:setnth tr 2 (itoa j)) 5 "0")
            b (es:setnth (es:setnth tr 2 (itoa (- n j))) 1 (strcat (nth 1 tr) "B"))
            pt (list "PATAMAR" "PATAMAR 0" (es:f lp) (nth 6 tr) "0" "0" "0" ""))
      (setq ES:TRE (es:insere-nth (es:insere-nth (es:setnth ES:TRE k a) (1+ k) pt) (+ k 2) b))
      ;; apoios do fim do lance vao para o fim do novo lance; os de depois andam 2
      (foreach ap ES:APO
        (setq jj (es:int (es:n (nth 4 ap))) kk (/ jj 2) f (rem jj 2))
        (if (or (> kk k) (and (= kk k) (= f 1))) (setq kk (+ kk 2)))
        (setq r (cons (es:setnth ap 4 (itoa (+ (* 2 kk) f))) r)))
      (setq ES:APO (reverse r))
      (es:renumera)
      T))
)

;;; ponto notavel mais perto de x (ou deslocamento a partir do inicio): (chave desl)
(defun es:graf-gruda (pts x / best)
  (foreach q pts
    (if (and (< (abs (- x (caddr q))) (max 5.0 (* 1.5 ES:HC)))
             (or (null best) (< (abs (- x (caddr q))) (abs (- x (caddr best))))))
      (setq best q)))
  (if best (list (car best) 0) (list "INI" (es:int (- x (caddr (assoc "INI" pts))))))
)

;;; nova barra: clique no corte armado (inicio) e no fim; abre a janela da barra
(defun es:graf-nova-barra (id ors p1 / q z c ql bb i geo tp x1 x2 p2 q2 pts k1 k2 d dcl did r yb yt)
  (setq q (es:graf-onde id ors p1 "ARM") z nil r nil)
  (if q
    (foreach h ES:PEGAS
      (if (and (null z) (= (car h) "ARM") (= (nth 1 h) "ZONA"))
        (progn
          (setq c (nth 6 h) bb (cadr c) ql (if (car c) (es:sub q (car c)) q))
          (if (and bb (>= (car ql) (car bb)) (<= (car ql) (caddr bb))
                   (>= (cadr ql) (cadr bb)) (<= (cadr ql) (cadddr bb)))
            (setq z (list (nth 2 h) (car c) ql)))))))
  (if (null z)
    (princ "\nClique DENTRO de um corte armado (desenho da ARMADURA).")
    (progn
      (setq i (car z) geo (es:arm-geo ES:GS (nth (1- i) (es:arm-detalhes ES:GS)))
            x1 (car (caddr z))
            yb (es:y-cadeia (nth 1 geo) x1) yt (es:y-cadeia (nth 2 geo) x1)
            tp (if (and yb yt (> (abs (- (cadr (caddr z)) yb)) (abs (- (cadr (caddr z)) yt)))) "1" "0"))
      (princ (strcat "\nNova barra " (if (= tp "0") "INFERIOR" "SUPERIOR") " no detalhe D" (itoa i) "."))
      (setq p2 (vl-catch-all-apply 'getpoint (list p1 "\nFim da nova barra: ")))
      (if (and p2 (not (vl-catch-all-error-p p2)) (setq q2 (es:graf-onde id ors p2 "ARM")))
        (progn
          (setq x2 (car (if (cadr z) (es:sub q2 (cadr z)) q2)))
          (if (> x1 x2) (setq d x1 x1 x2 x2 d))
          (setq pts (es:arm-pontos geo tp) k1 (es:graf-gruda pts x1) k2 (es:graf-gruda pts x2))
          (setq d (list tp (itoa i) (car k1) (itoa (cadr k1)) (car k2) (itoa (cadr k2))
                        (if (member (car k1) '("INI" "FIM")) "3" (if (= tp "0") "5" "2")) ""
                        (if (member (car k2) '("INI" "FIM")) "3" (if (= tp "0") "5" "2")) ""
                        (itoa (if (= tp "0") ES:AIB ES:ASB)) (if (= tp "0") ES:AIS ES:ASS) ""))
          (setq dcl (es:write-dcl) did (load_dialog dcl))
          (if (> did 0)
            (progn
              (setq d (es:dlg-barra did d))
              (unload_dialog did)
              (if d (setq ES:ARMS (append ES:ARMS (list d)) r T))))))))
  r
)

;;; E: janela do elemento da alca
(defun es:graf-edita (a / h tp i dcl did r)
  (setq h (car a) tp (nth 1 h) i (nth 2 h) r nil)
  (setq dcl (es:write-dcl) did (load_dialog dcl))
  (if (> did 0)
    (progn
      (cond
        ((wcmatch tp "L-*,P-*")
         (if (setq r (if (es:lance-p (nth i ES:TRE)) (es:dlg-lance did (nth i ES:TRE)) (es:dlg-pat did (nth i ES:TRE))))
           (setq ES:TRE (es:setnth ES:TRE i r))))
        ((wcmatch tp "A-*,V-*,SV-*")
         (if (setq r (es:dlg-apo did (nth i ES:APO))) (setq ES:APO (es:setnth ES:APO i r))))
        ((wcmatch tp "B-*")
         (if (setq r (es:dlg-barra did (nth i ES:ARMS))) (setq ES:ARMS (es:setnth ES:ARMS i r))))
        (t (princ "\nLinha de corte: arraste as pontas ou o meio; para apagar use A.")))
      (unload_dialog did)))
  r
)

;;; A: apaga o elemento da alca
(defun es:graf-apaga (a / h tp i)
  (setq h (car a) tp (nth 1 h) i (nth 2 h))
  (cond
    ((wcmatch tp "L-*,P-*")
     (if (> (length ES:TRE) 1)
       (progn
         (princ (strcat "\n" (nth 1 (nth i ES:TRE)) " apagado."))
         (setq ES:TRE (es:remove-nth ES:TRE i))
         (es:apo-remapeia (list "rem" i))
         (es:renumera)
         T)
       (progn (princ "\nA escada precisa de pelo menos um trecho.") nil)))
    ((wcmatch tp "A-*,V-*,SV-*")
     (princ (strcat "\nApoio " (car (nth i ES:APO)) " apagado."))
     (setq ES:APO (es:remove-nth ES:APO i)) T)
    ((wcmatch tp "C-*,SC-*")
     (princ (strcat "\nCorte " (car (nth i ES:CORTES)) " apagado."))
     (setq ES:CORTES (es:remove-nth ES:CORTES i)) T)
    ((wcmatch tp "B-*")
     (princ (strcat "\nBarra B" (itoa (1+ i)) " apagada."))
     (setq ES:ARMS (es:remove-nth ES:ARMS i))
     (if (null ES:ARMS) (princ "\n(lista vazia: a armadura automatica volta a ser gerada)"))
     T))
)

;;; ---- laco principal ----------------------------------------------------------------
(defun es:graf-recarrega (id / d ors)
  (if (setq d (es:reg-le id))
    (progn (setq ors (es:carrega d)) (es:unidades) (setq ES:GS (es:geo ES:TRE)) ors))
)
(defun es:graf-refaz (id ors)
  (setq ES:PEGAS nil)
  (redraw)
  (es:roda 'es:gera (list id ors nil) "ESCADAGRAF")
  (es:graf-recarrega id)
)

(defun es:graf-ajuda ()
  (princ (strcat
    "\n---- ESCADAGRAF: edicao grafica da escada " ES:NOME " ----"
    "\n  Clique numa ALCA (quadrado) e arraste; clique de novo para soltar."
    "\n  Durante o arraste: digite o valor exato + ENTER (dois valores: 28/17.5)."
    "\n  Azul = lances, ciano = patamares, verde = vigas / apoios, magenta = cortes,"
    "\n  vermelho = barras da armadura."
    "\n  Teclas:  A apagar   E editar (janela)   D dividir lance (cortar com patamar)"
    "\n           C novo corte na planta   N nova barra (2 cliques no corte armado)"
    "\n           R refazer armadura automatica   Q quantitativo   J janela completa"
    "\n           Z desfazer   ?  ajuda   ENTER / botao direito = sair"))
)

(defun es:graf-modo-txt (m)
  (cond ((= m "A") "APAGAR: clique na alca do elemento")
        ((= m "E") "EDITAR: clique na alca (fora de alca = janela completa)")
        ((= m "D") "DIVIDIR: clique no degrau do lance onde entra o patamar")
        ((= m "N") "NOVA BARRA: clique no inicio da barra no corte armado")
        (t ""))
)

(defun es:graf-refazer-arm? ( / k)
  (if ES:ARMS
    (progn
      (initget "Sim Nao")
      (setq k (vl-catch-all-apply 'getkword (list "\nA escada mudou de trechos. Refazer a armadura automatica? [Sim/Nao] <Sim>: ")))
      (if (or (vl-catch-all-error-p k) (/= k "Nao")) (setq ES:ARMS nil))))
)

(defun es:graf-laco (id / ors alcas fim g a modo desf p r v k bk lp)
  (setq desf nil fim nil modo nil)
  (setq ors (es:graf-refaz id (es:graf-recarrega id)))
  (setq alcas (es:graf-alcas id))
  (es:graf-ajuda)
  (if (null alcas) (princ "\nNenhuma alca: ligue a PLANTA, o DESENVOLVIMENTO ou a ARMADURA no ESCADAEDIT."))
  (while (and (not fim) ors)
    (setq g (vl-catch-all-apply 'grread (list T 15 0)))
    (cond
      ((vl-catch-all-error-p g) (setq fim T))
      ((= (car g) 5)
       (setq a (es:graf-perto alcas (cadr g)))
       (es:graf-mostra alcas a)
       (grtext -1 (cond (modo (strcat (es:graf-modo-txt modo) (if a (strcat "  -  " (nth 5 (car a))) "")))
                        (a (nth 5 (car a)))
                        (t "ESCADAGRAF: arraste as alcas  |  A E D C N R Q J Z  |  ENTER sai"))))
      ((= (car g) 3)
       (setq a (es:graf-perto alcas (cadr g)) p (cadr g) r nil bk (es:dados ors))
       (cond
         ((= modo "A")
          (if a (setq r (es:graf-apaga a)) (princ "\nNada para apagar aqui: clique numa alca."))
          (if (and r (wcmatch (nth 1 (car a)) "L-*,P-*")) (es:graf-refazer-arm?)))
         ((= modo "E")
          (redraw)
          (if a
            (setq r (es:graf-edita a))
            (if (not (setq r (es:janela))) (es:carrega bk))))
         ((= modo "D")
          (if (setq v (es:graf-lance-em id ors p))
            (progn
              (initget 6)
              (setq lp (vl-catch-all-apply 'getreal (list (strcat "\nComprimento do novo patamar (cm) <" ES:MLP ">: "))))
              (if (or (vl-catch-all-error-p lp) (null lp)) (setq lp (es:n ES:MLP)))
              (if (setq r (es:divide-lance (car v) (cadr v) lp))
                (progn (princ (strcat "\nLance dividido no degrau " (itoa (cadr v)) "."))
                       (es:graf-refazer-arm?))
                (princ "\nEsse lance nao pode ser dividido ai (precisa de 2 espelhos ou mais).")))
            (princ "\nClique SOBRE um lance (no desenvolvimento ou na planta).")))
         ((= modo "N") (redraw) (setq r (es:graf-nova-barra id ors p)))
         (a
          (if (setq v (es:graf-arrasta a alcas)) (progn (es:graf-aplica (car a) v) (setq r T)))))
       (setq modo nil)
       (if r
         (setq desf (cons bk desf) ors (es:graf-refaz id ors) alcas (es:graf-alcas id))))
      ((= (car g) 2)
       (setq k (strcase (chr (cadr g))))
       (cond
         ((member (cadr g) '(13 32 27)) (if modo (setq modo nil) (setq fim T)))
         ((member k '("A" "E" "D" "N"))
          (setq modo k) (princ (strcat "\n" (es:graf-modo-txt k) "  (botao direito = desiste)")))
         ((= k "Z")
          (if desf
            (progn (es:carrega (car desf)) (setq desf (cdr desf) ors (es:graf-refaz id ors) alcas (es:graf-alcas id))
                   (princ "\nDesfeito."))
            (princ "\nNada para desfazer.")))
         ((= k "C")
          (redraw) (setq bk (es:dados ors))
          (es:secao-laco id)
          (setq desf (cons bk desf) ors (es:graf-refaz id (es:graf-recarrega id)) alcas (es:graf-alcas id)))
         ((= k "R")
          (setq desf (cons (es:dados ors) desf) ES:ARMS (es:arm-auto ES:GS)
                ors (es:graf-refaz id ors) alcas (es:graf-alcas id))
          (princ "\nArmadura automatica refeita."))
         ((= k "Q") (es:quant-print ES:GS))
         ((= k "J")
          (redraw) (setq bk (es:dados ors))
          (if (es:janela)
            (setq desf (cons bk desf) ors (es:graf-refaz id ors) alcas (es:graf-alcas id))
            (es:carrega bk)))
         ((member k '("?" "H")) (es:graf-ajuda))))
      ((member (car g) '(11 25)) (if modo (setq modo nil) (setq fim T)))))
  (redraw)
  (grtext -1 "")
  (princ "\nESCADAGRAF terminado.")
  (princ)
)

;;; ---- alcas de cada desenho (chamadas no fim do desenho) -----------------------------
(defun es:alcas-lon (gs / k sm r ap inv)
  (setq k 0)
  (foreach g gs
    (if (= (car g) "L")
      (progn
        (es:alca "L-FIM" k (list (nth 2 g) (nth 4 g)) '(1.0 0.0)
                 (strcat (nth 9 g) ": fim do lance (arraste = + / - degraus)") nil)
        (es:alca "L-DEG" k (list (+ (nth 1 g) (nth 14 g)) (+ (nth 3 g) (nth 13 g))) nil
                 (strcat (nth 9 g) ": 1.o degrau (horizontal = piso, vertical = espelho)") nil)
        (setq sm (* 0.5 (+ (nth 1 g) (nth 2 g))))
        (es:alca "L-H" k (list sm (if (es:cad-fundo g) (es:fundo-est gs sm) (es:yint g sm)))
                 (if (es:cad-fundo g) '(0.0 -1.0) (es:mul (es:nrm (atan (nth 6 g))) -1.0))
                 (strcat (nth 9 g) ": espessura") nil))
      (progn
        (es:alca "P-FIM" k (list (nth 2 g) (nth 11 g)) '(1.0 0.0)
                 (strcat (nth 9 g) ": fim do patamar (comprimento)") nil)
        (es:alca "P-H" k (list (* 0.5 (+ (nth 1 g) (nth 2 g))) (nth 5 g)) '(0.0 -1.0)
                 (strcat (nth 9 g) ": espessura") nil)))
    (setq k (1+ k)))
  (setq k 0)
  (foreach ap ES:APO
    (if (= (es:apo-dir ap) 0)
      (progn
        (setq r (es:apo-ret gs ap) inv (es:apo-inv ap))
        (es:alca "A-MOV" k (list (* 0.5 (+ (nth 0 r) (nth 1 r))) (* 0.5 (+ (nth 2 r) (nth 3 r)))) '(1.0 0.0)
                 (strcat (car ap) ": posicao (deslocamento do eixo)") nil)
        (if (/= (nth 4 r) 1)
          (progn
            (es:alca "A-H" k (list (* 0.5 (+ (nth 0 r) (nth 1 r))) (if inv (nth 3 r) (nth 2 r)))
                     (if inv '(0.0 1.0) '(0.0 -1.0)) (strcat (car ap) ": altura h") nil)
            (es:alca "A-B" k (list (nth 1 r) (+ (nth 2 r) (* 0.25 (- (nth 3 r) (nth 2 r))))) '(1.0 0.0)
                     (strcat (car ap) ": largura b") nil)))))
    (setq k (1+ k)))
)

(defun es:alcas-pla (gs / refs k rf so ap i a d dr)
  (setq refs (es:planta-refs gs) k 0)
  (foreach g gs
    (setq rf (nth k refs))
    (es:alca (if (= (car g) "L") "L-FIM" "P-FIM") k
             (es:uv (nth 0 rf) (nth 1 rf) (nth 2 rf) (* 0.5 (+ (nth 3 rf) (nth 4 rf)))) (es:vet (nth 1 rf))
             (strcat (nth 9 g) (if (= (car g) "L") ": fim do lance (arraste = + / - degraus)" ": comprimento"))
             nil)
    (setq k (1+ k)))
  (foreach so (es:solidos gs)
    (if (and (= (car so) "B") (setq ap (es:nth 8 (nth 9 so))) (/= (nth 3 (nth 9 so)) "S")
             (setq i (vl-position ap ES:APO)))
      (progn
        (setq a (nth 2 so) d (nth 1 so) dr (es:apo-dir ap))
        (es:alca "V-MOV" i (es:uv d a (* 0.5 (+ (nth 3 so) (nth 4 so))) (* 0.5 (+ (nth 5 so) (nth 6 so)))) nil
                 (strcat (car ap) ": mover a viga") nil)
        (if (= dr 0)
          (progn
            (es:alca "V-E1" i (es:uv d a 0.0 (nth 5 so)) (es:mul (es:nrm a) -1.0) (strcat (car ap) ": ponta (extensao)") nil)
            (es:alca "V-E2" i (es:uv d a 0.0 (nth 6 so)) (es:nrm a) (strcat (car ap) ": ponta (extensao)") nil))
          (progn
            (es:alca "V-E1" i (es:uv d a (nth 3 so) 0.0) (es:mul (es:vet a) -1.0) (strcat (car ap) ": ponta (extensao)") nil)
            (es:alca "V-E2" i (es:uv d a (nth 4 so) 0.0) (es:vet a) (strcat (car ap) ": ponta (extensao)") nil))))))
  (setq k 0)
  (foreach ct ES:CORTES
    (es:alca "C-A" k (list (nth 1 ct) (nth 2 ct)) nil (strcat "Corte " (car ct) ": ponta") nil)
    (es:alca "C-B" k (list (nth 3 ct) (nth 4 ct)) nil (strcat "Corte " (car ct) ": ponta") nil)
    (es:alca "C-M" k (list (* 0.5 (+ (nth 1 ct) (nth 3 ct))) (* 0.5 (+ (nth 2 ct) (nth 4 ct)))) nil
             (strcat "Corte " (car ct) ": mover a linha") nil)
    (setq k (1+ k)))
)

;;; barras de um detalhe: pontas presas aos pontos, meio = mover
(defun es:alcas-arm (geo i / k pts fi lay xi xf x0 x1 y)
  (setq k 0)
  (foreach d ES:ARMS
    (if (= (es:int (es:n (es:ad d 1))) i)
      (progn
        (setq pts (es:arm-pontos geo (car d)) fi (es:bit (es:int (es:n (es:ad d 10))))
              lay (es:arm-camada geo (car d) fi) x0 (car (car lay)) x1 (car (es:ultimo lay))
              xi (+ (es:arm-x geo (car d) (es:ad d 2)) (es:n (es:ad d 3)))
              xf (+ (es:arm-x geo (car d) (es:ad d 4)) (es:n (es:ad d 5))))
        (foreach e (list (list "B-I" xi "inicio") (list "B-F" xf "fim"))
          (setq y (es:y-cadeia lay (max x0 (min x1 (cadr e)))))
          (if y
            (es:alca (car e) k (list (max x0 (min x1 (cadr e))) y) '(1.0 0.0)
                     (strcat "B" (itoa (1+ k)) " = N" (itoa (es:pos (1+ k))) " (" (nth (es:int (es:n (car d))) ES:TIPOS-ARM-C) "): " (caddr e)
                             " - gruda nos pontos da escada")
                     (list pts (cadr e)))))
        (setq y (es:y-cadeia lay (max x0 (min x1 (* 0.5 (+ xi xf))))))
        (if y
          (es:alca "B-MOV" k (list (max x0 (min x1 (* 0.5 (+ xi xf)))) y) '(1.0 0.0)
                   (strcat "B" (itoa (1+ k)) " = N" (itoa (es:pos (1+ k))) ": mover a barra inteira") nil))))
    (setq k (1+ k)))
)

;;; alcas de um CORTE (A-A ou tracado): vigas / lajes cortadas, espessuras dos
;;; trechos e as pontas da linha de corte
(defun es:alcas-sec (ct pcs cxs a0 dc len / ic d ap i x1 x2 yb yt inv xm ax so g u0 du)
  (setq ic (vl-position (car ct) (mapcar 'car ES:CORTES)))
  (foreach x cxs
    (setq d (nth 6 x) ap (es:nth 8 d))
    (if (and ap (setq i (vl-position ap ES:APO)))
      (progn
        (setq x1 (nth 0 x) x2 (nth 1 x) inv (es:apo-inv ap) xm (* 0.5 (+ x1 x2))
              yb (* 0.5 (+ (nth 2 x) (nth 3 x))) yt (* 0.5 (+ (nth 4 x) (nth 5 x))))
        (es:alca "A-H" i (list xm (if inv yt yb)) (if inv '(0.0 1.0) '(0.0 -1.0))
                 (strcat (car ap) ": altura h") nil)
        (es:alca "A-DZ" i (list xm (if inv yb yt)) '(0.0 1.0) (strcat (car ap) ": desnivel (sobe / desce)") nil)
        (es:alca "SV-MOV" i (list xm (* 0.5 (+ yb yt))) '(1.0 0.0) (strcat (car ap) ": mover ao longo do corte") dc)
        (setq ax (es:nth 7 d))
        (if (and ax (/= (nth 3 d) "S") (< (abs (+ (* (cos ax) (car dc)) (* (sin ax) (cadr dc)))) 0.3))
          (es:alca "A-B" i (list x2 (+ yb (* 0.25 (- yt yb)))) '(1.0 0.0) (strcat (car ap) ": largura b") nil)))))
  (foreach p pcs
    (setq so (nth 9 p) g (nth 8 so) xm (* 0.5 (+ (nth 1 p) (nth 2 p)))
          u0 (es:sol-u so a0) du (+ (* (car dc) (cos (nth 2 so))) (* (cadr dc) (sin (nth 2 so)))))
    (if (= (car p) "L")
      (es:alca "L-H" (nth 7 so) (list xm (es:sol-bot so (+ u0 (* du xm))))
               (if (es:cad-fundo g) '(0.0 -1.0) (list 0.0 (- (cos (atan (nth 6 g))))))
               (strcat (nth 9 g) ": espessura") nil)
      (es:alca "P-H" (nth 7 so) (list xm (es:sol-bot so (+ u0 (* du xm)))) '(0.0 -1.0)
               (strcat (nth 9 g) ": espessura") nil)))
  (if ic
    (progn
      (es:alca "SC-A" ic '(0.0 0.0) '(1.0 0.0) (strcat "Corte " (car ct) ": ponta (alonga / encurta)") dc)
      (es:alca "SC-B" ic (list len 0.0) '(1.0 0.0) (strcat "Corte " (car ct) ": ponta (alonga / encurta)") dc)))
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
;;; londef = origem sugerida para o desenvolvimento (ESCADACORTE).
;;; Desenho sem ponto (ENTER) e desligado; corte sem ponto e removido.
(defun es:gera (id ors londef / gs novos o feitos vs grp cortes0 refaz)
  (setq ES:ETAPA "preparo")
  (es:prepara)
  (es:unidades)
  (setq gs (es:geo ES:TRE) novos nil feitos nil cortes0 ES:CORTES refaz nil)
  ;; desenhos de cortes que nao existem mais
  (foreach x ors
    (if (and (wcmatch (car x) "SEC-*")
             (not (member (substr (car x) 5) (mapcar 'car ES:CORTES))))
      (es:apaga-des id (car x))))
  (setq vs (append
             (list (list "PLA" 'ES:DPLA "\nPLANTA DE FORMAS - ponto do inicio do 1.o lance, no eixo <nao desenhar>: " nil)
                   (list "TRA" 'ES:DTRA "\nCORTE A-A - ponto do inicio da linha de corte, no nivel inicial <nao desenhar>: " nil)
                   (list "LON" 'ES:DLON (if londef
                                          "\nDESENVOLVIMENTO - inicio da escada, nivel inicial <ENTER = sobre o corte selecionado>: "
                                          "\nDESENVOLVIMENTO - inicio da escada, nivel inicial <nao desenhar>: ")
                         londef)
                   (list "ARM" 'ES:DARM "\nDETALHAMENTO DA ARMADURA - ponto de insercao <nao desenhar>: " nil)
                   (list "PAR" 'ES:DARM "\nPLANTA DE ARMACAO - ponto do inicio do 1.o lance, no eixo <nao desenhar>: " nil)
                   (list "QTD" 'ES:DQTD "\nQUANTITATIVO (tabela) - canto superior esquerdo <nao desenhar>: " nil))
             (mapcar '(lambda (c) (list (strcat "SEC-" (car c)) nil
                                        (strcat "\nCORTE " (car c) "-" (car c)
                                                " - ponto do inicio da linha de corte, no nivel inicial <remover o corte>: ")
                                        nil))
                     ES:CORTES)))
  (foreach v vs
    (setq grp (car v) ES:ETAPA (strcat "desenho " grp) o nil)
    (if (or (null (cadr v)) (= (eval (cadr v)) "1"))
      (progn
        (setq o (es:origem ors grp))
        (if (null o) (setq o (es:pede-ponto (caddr v) (cadddr v))))
        (if o
          (progn
            (es:desenha-view id grp o gs)
            (setq novos (cons (cons grp (es:p2 o)) novos) feitos (cons grp feitos)))
          (progn
            (es:apaga-des id grp)
            (if (cadr v)
              (set (cadr v) "0")
              (setq ES:CORTES (vl-remove-if '(lambda (c) (= (strcat "SEC-" (car c)) grp)) ES:CORTES)
                    refaz T)))))
      (es:apaga-des id grp))
  )
  ;; um corte foi removido: a planta perde a marcacao dele
  (if (and refaz (es:origem novos "PLA"))
    (es:desenha-view id "PLA" (es:origem novos "PLA") gs))
  (setq ES:ETAPA "gravar")
  (es:reg-grava id (es:dados (reverse novos)))
  (princ (strcat "\nESCADA " ES:NOME " (" id "): " (itoa (length feitos)) " desenho(s)."
                 "  Alterar: ESCADAEDIT.  Novos cortes: ESCADASECAO."))
  feitos
)

(defun es:undo-ini ( / doc)
  (setq doc (vla-get-ActiveDocument (vlax-get-acad-object)))
  (vl-catch-all-apply 'vla-StartUndoMark (list doc))
  doc
)
(defun es:undo-fim (doc) (if doc (vl-catch-all-apply 'vla-EndUndoMark (list doc))))

(defun c:ESCADA ( / *error* doc id)
  (defun *error* (msg)
    (if (and msg (not (wcmatch (strcase msg) "*CANCEL*,*QUIT*,*EXIT*")))
      (princ (strcat "\n*** Erro: " msg (if ES:ETAPA (strcat "  [etapa: " ES:ETAPA "]") ""))))
    (es:undo-fim doc) (setq ES:ID nil ES:GRP nil) (princ))
  (setq ES:ETAPA "janela" ES:ARMS nil ES:CORTES nil)
  (if (es:roda 'es:janela nil "janela")
    (progn
      (setq doc (es:undo-ini) id (es:novo-id) ES:CORTES nil)
      (es:roda 'es:gera (list id nil nil) "desenhando")
      (if (es:insert-de id "PLA") (es:roda 'es:secao-laco (list id) "cortes"))
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

;;; tracar cortes numa escada existente: clique na planta de formas
(defun c:ESCADASECAO ( / *error* doc s id x)
  (defun *error* (msg)
    (if (and msg (not (wcmatch (strcase msg) "*CANCEL*,*QUIT*,*EXIT*")))
      (princ (strcat "\n*** Erro: " msg (if ES:ETAPA (strcat "  [etapa: " ES:ETAPA "]") ""))))
    (es:undo-fim doc) (setq ES:ID nil ES:GRP nil) (princ))
  (setq s (entsel "\nClique na PLANTA DE FORMAS da escada: "))
  (cond
    ((null s) (princ "\nNada selecionado."))
    ((null (setq x (es:id-ent (car s)))) (princ "\nIsso nao e um desenho da ESCADA."))
    ((null (es:insert-de (setq id (car x)) "PLA"))
     (princ "\nEssa escada nao tem planta de formas: ligue a planta no ESCADAEDIT."))
    ((null (es:reg-le id)) (princ (strcat "\nOs dados da escada " id " nao foram encontrados.")))
    (t
     (setq doc (es:undo-ini))
     (es:roda 'es:secao-laco (list id) "cortes")
     (es:undo-fim doc)))
  (princ)
)

;;; ---- ESCADAVIGA: mexer numa viga / apoio direto na planta -------------------------
;;; move um apoio de dl (cm da planta): transversal = deslocamento do eixo + lateral;
;;; borda = afastamento da borda + extensoes (desliza ao longo do trecho)
(defun es:apo-move (ap dl gs / ang du dv)
  (setq ang (nth 1 (nth (es:apo-k gs ap) (es:planta-refs gs)))
        du (+ (* (car dl) (cos ang)) (* (cadr dl) (sin ang)))
        dv (- (* (cadr dl) (cos ang)) (* (car dl) (sin ang))))
  (if (> (es:apo-dir ap) 0)
    (setq ap (es:setnth ap 5 (es:f (+ (es:n (nth 5 ap)) (if (= (es:apo-dir ap) 1) dv (- dv)))))
          ap (es:setnth ap 7 (es:f (- (es:apo-ext1 ap) du)))
          ap (es:setnth ap 8 (es:f (+ (es:apo-ext2 ap) du))))
    (setq ap (es:setnth ap 5 (es:f (+ (es:n (nth 5 ap)) du)))
          ap (es:setnth ap 13 (es:f (+ (es:apo-dv ap) dv)))))
  ap
)

;;; apoio mais proximo do ponto (cm da planta): indice em ES:APO ou nil
(defun es:viga-perto (gs q / r dmin so d u v du dv dd i)
  (setq dmin (* 4.0 ES:HC))
  (foreach so (es:solidos gs)
    (if (and (= (car so) "B") (setq d (nth 8 (nth 9 so))))
      (progn
        (setq u (es:sol-u so q) v (es:sol-v so q)
              du (max 0.0 (- (nth 3 so) u) (- u (nth 4 so)))
              dv (max 0.0 (- (nth 5 so) v) (- v (nth 6 so)))
              dd (sqrt (+ (* du du) (* dv dv))))
        (if (< dd dmin) (setq dmin dd r d)))))
  (if r (vl-position r ES:APO))
)

(defun es:viga-laco (id pt / d ors ins o q i ap op gs p1 p2 a b ang dl du dv dcl did r)
  (setq d (es:reg-le id) ors (es:carrega d) ins (es:insert-de id "PLA") o (es:origem ors "PLA"))
  (es:unidades)
  (setq gs (es:geo ES:TRE))
  (if (and pt (setq q (es:mundo->planta pt ins o)) (setq i (es:viga-perto gs q)))
    (progn
      (setq op "Mover")
      (while op
        (setq ap (nth i ES:APO))
        (initget "Mover Inverter Espelhar Girar Desnivel Estender Editar Sair")
        (setq op (getkword (strcat "\nApoio " (car ap) (if (es:apo-inv ap) " (INVERTIDA)" "")
                                   ": [Mover/Inverter/Espelhar/Girar/Desnivel/Estender/Editar/Sair] <Sair>: ")))
        (if (= op "Sair") (setq op nil))
        (cond
          ((null op) nil)
          ((= op "Mover")
           (setq p1 (getpoint "\nPonto base: "))
           (if (and p1 (setq p2 (getpoint p1 "\nNovo ponto: ")))
             (setq ap (es:apo-move ap (es:sub (es:mundo->planta p2 ins o) (es:mundo->planta p1 ins o)) gs))))
          ((= op "Inverter")
           (setq ap (es:setnth ap 11 (if (es:apo-inv ap) "0" "1"))))
          ((= op "Espelhar")
           ;; borda: troca de lado; transversal: para o outro lado da posicao
           (if (> (es:apo-dir ap) 0)
             (setq ap (es:setnth ap 6 (if (= (es:apo-dir ap) 1) "2" "1")))
             (setq ap (es:setnth ap 5 (es:f (- (es:n (nth 5 ap))))))))
          ((= op "Girar")
           (if (setq a (getreal (strcat "\nRotacao em graus (anti-horario) <" (es:f (es:n (nth 14 ap))) ">: ")))
             (setq ap (es:setnth ap 14 (es:f a)))))
          ((= op "Desnivel")
           (if (setq a (getreal (strcat "\nDesnivel do topo em cm (+ sobe) <" (es:f (es:apo-dz ap)) ">: ")))
             (setq ap (es:setnth ap 12 (es:f a)))))
          ((= op "Estender")
           (initget 4)
           (if (setq a (getreal (strcat "\nExtensao lado direito / inicio (cm) <" (es:f (es:apo-ext1 ap)) ">: ")))
             (setq ap (es:setnth ap 7 (es:f a))))
           (initget 4)
           (if (setq b (getreal (strcat "\nExtensao lado esquerdo / fim (cm) <" (es:f (es:apo-ext2 ap)) ">: ")))
             (setq ap (es:setnth ap 8 (es:f b)))))
          ((= op "Editar")
           (setq dcl (es:write-dcl) did (load_dialog dcl))
           (if (> did 0)
             (progn (if (setq r (es:dlg-apo did ap)) (setq ap r)) (unload_dialog did)))))
        (if op
          (progn
            (setq ES:APO (es:setnth ES:APO i ap))
            (es:roda 'es:gera (list id ors nil) (strcat "apoio " (car ap)))
            (setq d (es:reg-le id) ors (es:carrega d) ins (es:insert-de id "PLA") gs (es:geo ES:TRE))))))
    (princ "\nNenhuma viga / apoio perto do ponto clicado (clique sobre a viga na PLANTA DE FORMAS)."))
  (princ)
)

(defun c:ESCADAVIGA ( / *error* doc s x id)
  (defun *error* (msg)
    (if (and msg (not (wcmatch (strcase msg) "*CANCEL*,*QUIT*,*EXIT*")))
      (princ (strcat "\n*** Erro: " msg (if ES:ETAPA (strcat "  [etapa: " ES:ETAPA "]") ""))))
    (es:undo-fim doc) (setq ES:ID nil ES:GRP nil) (princ))
  (princ "\nESCADAVIGA: mover, inverter, espelhar, girar, desnivelar ou estender uma viga.")
  (setq doc (es:undo-ini))
  (setq s (entsel "\nClique SOBRE a viga / apoio na PLANTA DE FORMAS da escada: "))
  (cond
    ((null s) (princ "\nNada selecionado."))
    ((null (setq x (es:id-ent (car s)))) (princ "\nIsso nao e um desenho da ESCADA."))
    ((null (es:insert-de (setq id (car x)) "PLA")) (princ "\nEssa escada nao tem planta de formas."))
    (t (es:roda 'es:viga-laco (list id (cadr s)) "ESCADAVIGA")))
  (es:undo-fim doc)
  (princ)
)

;;; ---- ESCADAGRAF: edicao grafica (alcas arrastaveis) ---------------------------------
(defun c:ESCADAGRAF ( / *error* doc s id)
  (defun *error* (msg)
    (if (and msg (not (wcmatch (strcase msg) "*CANCEL*,*QUIT*,*EXIT*")))
      (princ (strcat "\n*** Erro: " msg (if ES:ETAPA (strcat "  [etapa: " ES:ETAPA "]") ""))))
    (redraw) (grtext -1 "") (es:undo-fim doc) (setq ES:ID nil ES:GRP nil) (princ))
  (setq s (entsel "\nESCADAGRAF - clique num desenho da escada: "))
  (cond
    ((null s) (princ "\nNada selecionado."))
    ((null (setq id (car (es:id-ent (car s))))) (princ "\nIsso nao e um desenho da ESCADA."))
    ((null (es:reg-le id)) (princ (strcat "\nOs dados da escada " id " nao foram encontrados.")))
    (t
     (setq doc (es:undo-ini))
     (es:roda 'es:graf-laco (list id) "ESCADAGRAF")
     (es:undo-fim doc)))
  (princ)
)

;;; ---- ESCADAQTD: quantitativo na linha de comando (e a tabela) ------------------------
(defun c:ESCADAQTD ( / *error* doc s id ors k)
  (defun *error* (msg)
    (if (and msg (not (wcmatch (strcase msg) "*CANCEL*,*QUIT*,*EXIT*")))
      (princ (strcat "\n*** Erro: " msg (if ES:ETAPA (strcat "  [etapa: " ES:ETAPA "]") ""))))
    (es:undo-fim doc) (setq ES:ID nil ES:GRP nil) (princ))
  (setq s (entsel "\nESCADAQTD - clique num desenho da escada: "))
  (cond
    ((null s) (princ "\nNada selecionado."))
    ((null (setq id (car (es:id-ent (car s))))) (princ "\nIsso nao e um desenho da ESCADA."))
    ((null (es:reg-le id)) (princ (strcat "\nOs dados da escada " id " nao foram encontrados.")))
    (t
     (setq ors (es:carrega (es:reg-le id)))
     (es:unidades)
     (es:roda 'es:quant-print (list (es:geo ES:TRE)) "quantitativo")
     (initget "Sim Nao")
     (setq k (getkword (strcat "\n" (if (es:insert-de id "QTD") "Atualizar" "Desenhar")
                               " a tabela QUANTITATIVO no desenho? [Sim/Nao] <Sim>: ")))
     (if (/= k "Nao")
       (progn
         (setq doc (es:undo-ini) ES:DQTD "1")
         (es:roda 'es:gera (list id ors nil) "quantitativo")
         (es:undo-fim doc)))))
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
         (setq ES:TRE (car r) ES:DLON "1" ES:CORTES nil ES:ARMS nil
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
               "ESCADACORTE (a partir de um corte desenhado), ESCADASECAO (tracar cortes na planta), "
               "ESCADAVIGA (mover / inverter / girar vigas na planta), "
               "ESCADAGRAF (editar arrastando alcas: trechos, vigas, cortes, barras), "
               "ESCADAQTD (quantitativo de concreto e formas), "
               "ESCADAEDIT (editar; armaduras no botao Armadura...)."))
(princ)
