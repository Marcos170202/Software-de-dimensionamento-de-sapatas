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

Fases futuras (ver PROCESSO_MODELAGEM_METALICA.md): geometria 2D do
lançamento em planta, geração automática do pórtico espacial (análise),
NBR 8800 (dimensionamento), detalhamento/desenho e o elo de saída
(reações de apoio) com o módulo de sapatas/fundações deste repositório.
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
