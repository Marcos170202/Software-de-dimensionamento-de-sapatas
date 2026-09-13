"""Motor de cálculo — estrutura metálica (NBR 8800).

Ver ``PROCESSO_MODELAGEM_METALICA.md`` na raiz do repositório para a
especificação completa do processo de modelagem (adaptado do
HyperFrame — github.com/candidoalfilho/hyperframe — para estruturas de
aço). Este pacote é o "motor de cálculo puro" descrito na seção 3
daquele documento: sem dependência de interface gráfica, sem
dependências externas.

Fases já implementadas:

- ``model``: entidades de dados da Etapa 2 (lançamento em planta) e da
  Etapa 3 (materiais) do processo — :class:`~estrutura_metalica.model.Node`,
  :class:`~estrutura_metalica.model.SteelMaterial`, hierarquia de
  :class:`~estrutura_metalica.model.SteelSection` (perfis I/H, U, tubos
  circular/retangular), :class:`~estrutura_metalica.model.ConnectionType`
  e os elementos estruturais :class:`~estrutura_metalica.model.Column`,
  :class:`~estrutura_metalica.model.Beam` e
  :class:`~estrutura_metalica.model.Bracing`.
- ``analysis``: Etapas 4 e 5 (sincronização 3D e análise) —
  :class:`~estrutura_metalica.analysis.StructuralModel` (agregação),
  matriz de rigidez do elemento de pórtico 3D, montagem global e
  solução linear elástica de 1ª ordem
  (:func:`~estrutura_metalica.analysis.solve`).
- ``normative.nbr8800``: Etapa 6 (dimensionamento) — ABNT NBR
  8800:2024, tração (5.2), compressão (5.3, flambagem por flexão e por
  torção para seções com dupla simetria ou simétricas em relação a um
  ponto), força cortante (5.4.1.3/5.4.3.1, seções I/H/U fletidas no
  eixo perpendicular à alma), momento fletor (5.4.1.3/5.4.2/Anexo D —
  FLT, FLM e FLA de seções I/H/U duplamente simétricas fletidas no
  eixo maior, vigas de alma não esbelta), Anexo E (momento fletor
  resistente de cálculo de vigas de alma esbelta SOLDADAS, duplamente
  simétricas — escoamento da mesa tracionada, FLT e FLM), interação
  entre força axial e momento fletor biaxial (5.5.1.2, barras sem
  torção), a limitação recomendada do índice de esbeltez (5.2.8/5.3.7)
  e ligações metálicas (6.2.5.1, força resistente do metal da solda em
  soldas de filete concêntricas; 6.3.2/6.3.3, parafusos e barras
  redondas rosqueadas em ligações por contato — tração, cisalhamento,
  pressão de contato e interação tração-cisalhamento). Ver
  ``docs/normative/NBR8800-RULES.md`` para a rastreabilidade completa
  e o que ainda está fora do escopo (interação com torção, metal-base
  em soldas, ligações por atrito, pinos, bases de pilares).

Fases futuras (ver PROCESSO_MODELAGEM_METALICA.md): geometria 2D do
lançamento em planta, restante das ligações metálicas (ligações por
atrito, metal-base em soldas, pinos, bases de pilares),
detalhamento/desenho e o elo de saída (reações de apoio) com o módulo
de sapatas/fundações deste repositório.
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
