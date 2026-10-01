# CALCTEXTO.lsp — operações com textos numéricos no AutoCAD

Lê números de **TEXT, MTEXT, atributos, cotas e multileaders**, aceitando **vírgula ou ponto** como separador decimal
(`12,50`, `12.50`, `1.234,56`, `1,234.56`, `Área = 35,40 m²`, `-7,5`).

## Como carregar
1. No AutoCAD digite `APPLOAD`, selecione `CALCTEXTO.lsp` e clique em **Load**
   (para carregar sempre, adicione em *Startup Suite*).
2. Ou arraste o arquivo para dentro do desenho.

## Comandos

| Comando    | O que faz |
|------------|-----------|
| `CT`       | Menu com todas as operações |
| `CTSUB`    | Seleciona o **valor total** e depois os textos a **subtrair** dele (total − soma dos selecionados) |
| `CTSOMA`   | Soma todos os textos selecionados |
| `CTMULT`   | Multiplica todos os textos selecionados |
| `CTDIV`    | Dividendo ÷ divisor |
| `CTCALC`   | Calculadora em cadeia: valor `+ - * /` valor … (avalia da esquerda para a direita) |
| `CTCONFIG` | Casas decimais, separador do resultado (vírgula/ponto), separador de milhar e modo de leitura |

- Ao pedir um valor único, você pode clicar no texto **ou** escolher `Digitar` e digitar o número.
- Os textos selecionados ficam destacados e cada valor é listado na linha de comando para conferência.
- Se o texto do total for selecionado junto com os valores a subtrair, ele é ignorado automaticamente.

### O que fazer com o resultado
- **Inserir** – cria um texto novo (copia camada, estilo, altura e rotação do texto de referência).
- **Substituir** – troca apenas o número de um texto existente, mantendo prefixo/sufixo
  (`Área = 120,00 m²` → `Área = 95,50 m²`). No `CTSUB`, basta dar **Enter** para substituir o próprio total.
- **Nenhum** – só mostra na linha de comando.

Tudo é feito em um único grupo de UNDO (um `U` desfaz a operação inteira).

## Leitura dos números (modo Automático)
- Vírgula e ponto juntos: o **último** é o decimal (`1.234,56` e `1,234.56` → 1234,56).
- O mesmo separador repetido é milhar (`1.234.567` → 1234567).
- Um único separador é considerado decimal (`1.234` → 1,234). Se seus desenhos usam ponto como milhar
  sem casas decimais, ajuste em `CTCONFIG` → Leitura = **Virgula**.
- É usado o **primeiro** número encontrado no texto.
