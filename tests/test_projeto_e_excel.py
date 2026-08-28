"""
Salvar/abrir projeto (`ui/completo/projeto.py`) e importar/exportar Excel
(`ui/completo/excel_import.py`, `ui/completo/excel_export.py`) — escopo
AMPLO. Cobre:

  * round-trip de projeto (.s7proj): salva uma `Sapata` real com perfil de
    4 camadas (incluindo uma coesiva com Cc/e0/cv/Es), carrega de volta,
    reconstrói `Sapata` a partir do dict carregado e confirma que
    `dimensionar()` produz um resultado BIT-IDÊNTICO ao original — não só
    que os campos batem, que o CÁLCULO reproduzido bate.
  * round-trip de Excel: `gerar_modelo_importacao` -> `importar_*` no
    arquivo gerado -> confere que os valores batem com o exemplo escrito.
  * casos de erro: cada um levantando `ValueError` com mensagem que cite
    onde está o problema (aba/linha/coluna, ou o campo do .s7proj) — nunca
    uma exceção genérica do openpyxl/json vazando para fora.

Não abre nenhum widget Tk: tudo aqui opera sobre os dataclasses de
`calc_core.sapata_isolada` e sobre arquivos em disco.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path

import pytest

# BAIXA do GATE 2, rodada 2: `import openpyxl` cru no topo do módulo faz a
# AUSÊNCIA de `openpyxl` virar um ERRO DE COLETA (não um skip) para o
# arquivo inteiro — mesmo padrão de `pytest.importorskip("tkinter")` já
# usado nas funções deste arquivo, aqui aplicado no escopo do módulo
# (antes da linha abaixo, que importa `ui.completo.excel_import`/
# `excel_export` — ambos também fazem `import openpyxl` cru no próprio
# topo — para a ausência nunca chegar lá).
openpyxl = pytest.importorskip("openpyxl")

from calc_core.sapata_isolada.acoes import (
    CasoCarga,
    Esforcos,
    Pilar,
    gerar_combinacoes,
)
from calc_core.sapata_isolada.geotecnia import (
    Camada,
    PerfilGeotecnico,
    Solo,
    TipoSubstrato,
)
from calc_core.sapata_isolada.materiais import Aco, Concreto
from calc_core.sapata_isolada.sapata import (
    ArmaduraImposta,
    GeometriaImposta,
    OpcoesProjeto,
    Sapata,
)
from ui.completo import excel_export, excel_import, projeto


# --------------------------------------------------------------------------- #
#  Fixtures de domínio
# --------------------------------------------------------------------------- #
def _perfil_4_camadas() -> PerfilGeotecnico:
    camadas = [
        Camada(nome="Aterro", espessura=1.0, tipo=TipoSubstrato.ATERRO,
              gamma_nat=17.0, gamma_sat=18.0, phi=25.0, coesao=0.0, nspt=4.0),
        Camada(nome="Areia argilosa", espessura=2.5, tipo=TipoSubstrato.GRANULAR,
              gamma_nat=18.0, gamma_sat=19.5, phi=30.0, coesao=0.0, nspt=12.0,
              Es=18000.0, nu=0.30),
        Camada(nome="Argila mole", espessura=3.0, tipo=TipoSubstrato.COESIVO,
              gamma_nat=15.0, gamma_sat=16.0, phi=22.0, coesao=15.0,
              Cc=0.45, Cs=0.08, e0=1.10, OCR=1.2, cv=0.9, C_alpha=0.01,
              drenagem_dupla=True),
        Camada(nome="Rocha alterada", espessura=5.0, tipo=TipoSubstrato.ROCHA,
              gamma_nat=22.0, gamma_sat=22.0, phi=35.0, coesao=50.0),
    ]
    return PerfilGeotecnico(camadas=camadas, nivel_agua=1.8)


def _dados_completos() -> dict:
    """Um conjunto de dados de entrada completo — pilar, solo com perfil de
    4 camadas, materiais, 3 casos de carga (G/Q/W) e opções — usado tanto
    para montar a `Sapata` "original" quanto para alimentar
    `projeto.salvar_projeto`, sem duplicar a definição dos casos em dois
    lugares (a duplicação é o jeito mais fácil de um teste de round-trip
    "passar" comparando um objeto consigo mesmo por engano)."""
    return {
        "pilar": Pilar(ap=0.30, bp=0.40, phi_arranque_mm=16.0),
        "solo": Solo(sigma_adm=220.0, gamma_solo=18.0, hf=1.5, phi=28.0,
                    coesao=5.0, perfil=_perfil_4_camadas()),
        "concreto": Concreto(fck=30.0, agregado="basalto"),
        "aco": Aco(fyk=500.0),
        "cobrimento": 0.045,
        "casos": [
            CasoCarga("G", Esforcos(N=650.0, Mx=20.0, My=10.0)),
            CasoCarga.acidental("Q", Esforcos(N=200.0, Mx=8.0, My=4.0)),
            CasoCarga.vento("W", Esforcos(My=40.0, Hx=15.0)),
        ],
        "opcoes": OpcoesProjeto(verificar_recalque=True),
    }


def _sapata_de(dados: dict) -> Sapata:
    combinacoes = gerar_combinacoes(dados["casos"])
    return Sapata(dados["pilar"], dados["solo"], dados["concreto"], dados["aco"],
                 combinacoes, cobrimento=dados["cobrimento"], opcoes=dados["opcoes"])


# --------------------------------------------------------------------------- #
#  Projeto (.s7proj) — round-trip
# --------------------------------------------------------------------------- #
def test_projeto_round_trip_bit_identico(tmp_path):
    dados_originais = _dados_completos()
    sapata = _sapata_de(dados_originais)
    resultado_original = sapata.dimensionar()

    caminho = tmp_path / "projeto.s7proj"
    projeto.salvar_projeto(str(caminho), dados_originais["pilar"],
                           dados_originais["solo"], dados_originais["concreto"],
                           dados_originais["aco"], dados_originais["cobrimento"],
                           dados_originais["casos"], dados_originais["opcoes"])

    dados_carregados = projeto.carregar_projeto(str(caminho))
    sapata_2 = _sapata_de(dados_carregados)
    resultado_2 = sapata_2.dimensionar()

    assert asdict(resultado_2) == asdict(resultado_original)


def test_projeto_round_trip_com_geometria_e_armadura_impostas(tmp_path):
    """Cobre os dois ramos "especiais" de OpcoesProjeto que exigem
    reconstrução explícita: geometria_imposta e armaduras_impostas."""
    pilar = Pilar(ap=0.25, bp=0.25)
    solo = Solo(sigma_adm=200.0)
    concreto = Concreto(fck=25.0)
    aco = Aco(fyk=500.0)
    casos = [CasoCarga("G", Esforcos(N=400.0, Mx=5.0, My=5.0))]
    opcoes = OpcoesProjeto(
        geometria_imposta=GeometriaImposta(a=1.60, b=1.60, h=0.50, h0=0.30),
        armaduras_impostas={"X": ArmaduraImposta(phi_mm=12.5, n_barras=10)},
        verificar_recalque=False)

    caminho = tmp_path / "projeto_imposto.s7proj"
    projeto.salvar_projeto(str(caminho), pilar, solo, concreto, aco, 0.045,
                           casos, opcoes)
    dados = projeto.carregar_projeto(str(caminho))

    assert dados["opcoes"].geometria_imposta == GeometriaImposta(
        a=1.60, b=1.60, h=0.50, h0=0.30)
    assert dados["opcoes"].armaduras_impostas["X"].phi_mm == 12.5
    assert dados["opcoes"].armaduras_impostas["X"].n_barras == 10

    combinacoes = gerar_combinacoes(casos)
    sapata_original = Sapata(pilar, solo, concreto, aco, combinacoes,
                             cobrimento=0.045, opcoes=opcoes)
    sapata_2 = _sapata_de(dados)
    assert asdict(sapata_2.dimensionar()) == asdict(sapata_original.dimensionar())


def test_projeto_sem_perfil_geotecnico(tmp_path):
    """Solo sem perfil (perfil=None) — caminho mais comum do escopo mínimo
    de dados, precisa sobreviver ao round-trip sem virar lista vazia."""
    pilar = Pilar(ap=0.20, bp=0.50)
    solo = Solo(sigma_adm=250.0)
    assert solo.perfil is None
    caminho = tmp_path / "sem_perfil.s7proj"
    projeto.salvar_projeto(str(caminho), pilar, solo, Concreto(), Aco(), 0.045,
                           [CasoCarga("G", Esforcos(N=300.0))], OpcoesProjeto())
    dados = projeto.carregar_projeto(str(caminho))
    assert dados["solo"].perfil is None


# --------------------------------------------------------------------------- #
#  Projeto (.s7proj) — erros
# --------------------------------------------------------------------------- #
def test_projeto_arquivo_json_invalido(tmp_path):
    caminho = tmp_path / "corrompido.s7proj"
    caminho.write_text("{isto nao e json", encoding="utf-8")
    with pytest.raises(ValueError, match="não é um JSON válido"):
        projeto.carregar_projeto(str(caminho))


def test_projeto_cabecalho_ausente(tmp_path):
    caminho = tmp_path / "sem_cabecalho.s7proj"
    caminho.write_text(json.dumps({"pilar": {}}), encoding="utf-8")
    with pytest.raises(ValueError, match="cabeçalho esperado"):
        projeto.carregar_projeto(str(caminho))


def test_projeto_versao_desconhecida(tmp_path):
    caminho = tmp_path / "versao_futura.s7proj"
    caminho.write_text(
        json.dumps({"formato": "sapata7-projeto", "versao": 99}), encoding="utf-8")
    with pytest.raises(ValueError, match="versão"):
        projeto.carregar_projeto(str(caminho))


def test_projeto_chave_obrigatoria_faltando(tmp_path):
    caminho = tmp_path / "incompleto.s7proj"
    caminho.write_text(
        json.dumps({"formato": "sapata7-projeto", "versao": 1, "pilar": {"ap": 0.3}}),
        encoding="utf-8")
    with pytest.raises(ValueError, match="obrigatório"):
        projeto.carregar_projeto(str(caminho))


def test_projeto_arquivo_inexistente():
    with pytest.raises(ValueError, match="Não foi possível abrir"):
        projeto.carregar_projeto("/caminho/que/nao/existe/projeto.s7proj")


def test_projeto_tipo_substrato_invalido_na_camada(tmp_path):
    caminho = tmp_path / "tipo_invalido.s7proj"
    dados = {
        "formato": "sapata7-projeto", "versao": 1,
        "pilar": {"ap": 0.3, "bp": 0.3},
        "solo": {"sigma_adm": 200.0,
                "perfil": {"camadas": [{"nome": "X", "espessura": 1.0,
                                        "tipo": "granito_marciano"}],
                          "nivel_agua": None}},
        "concreto": {"fck": 25.0}, "aco": {"fyk": 500.0}, "cobrimento": 0.045,
        "casos": [{"nome": "G", "N": 300.0}], "opcoes": {},
    }
    caminho.write_text(json.dumps(dados), encoding="utf-8")
    with pytest.raises(ValueError, match="tipo de substrato"):
        projeto.carregar_projeto(str(caminho))


# --------------------------------------------------------------------------- #
#  Excel — round-trip do modelo gerado
# --------------------------------------------------------------------------- #
def test_excel_modelo_round_trip_pilar_e_cargas(tmp_path):
    caminho = tmp_path / "modelo.xlsx"
    excel_import.gerar_modelo_importacao(str(caminho))

    pilar, casos = excel_import.importar_pilar_e_cargas(str(caminho))
    assert pilar.ap == pytest.approx(0.30)
    assert pilar.bp == pytest.approx(0.30)
    assert [c.nome for c in casos] == ["G", "Q"]
    assert casos[0].esforcos.N == pytest.approx(600.0)
    assert casos[0].esforcos.Mx == pytest.approx(15.0)
    assert casos[0].esforcos.My == pytest.approx(8.0)
    assert casos[1].esforcos.N == pytest.approx(180.0)
    assert casos[1].esforcos.Mx == pytest.approx(6.0)
    assert casos[1].esforcos.My == pytest.approx(0.0)
    # Hx/Hy não fazem parte deste layout — sempre 0.
    assert casos[0].esforcos.Hx == 0.0 and casos[0].esforcos.Hy == 0.0


def test_excel_modelo_round_trip_perfil_geotecnico(tmp_path):
    caminho = tmp_path / "modelo.xlsx"
    excel_import.gerar_modelo_importacao(str(caminho))

    perfil = excel_import.importar_perfil_geotecnico(str(caminho))
    assert [c.nome for c in perfil.camadas] == ["Areia argilosa", "Argila mole"]
    assert perfil.camadas[0].tipo is TipoSubstrato.GRANULAR
    assert perfil.camadas[0].espessura == pytest.approx(2.0)
    assert perfil.camadas[0].nspt == pytest.approx(12.0)
    assert perfil.camadas[0].Cc is None
    assert perfil.camadas[1].tipo is TipoSubstrato.COESIVO
    assert perfil.camadas[1].Cc == pytest.approx(0.45)
    assert perfil.camadas[1].e0 == pytest.approx(1.10)
    assert perfil.camadas[1].cv == pytest.approx(0.02)
    assert perfil.nivel_agua == pytest.approx(1.5)


def test_excel_modelo_gera_aba_de_instrucoes(tmp_path):
    caminho = tmp_path / "modelo.xlsx"
    excel_import.gerar_modelo_importacao(str(caminho))
    livro = openpyxl.load_workbook(str(caminho))
    assert set(livro.sheetnames) == {"Pilar e cargas", "Perfil geotécnico",
                                     "Instruções"}
    assert livro["Instruções"]["A1"].value is not None


# --------------------------------------------------------------------------- #
#  Excel — round-trip completo, alimentando Sapata.dimensionar()
# --------------------------------------------------------------------------- #
def test_excel_importado_alimenta_dimensionar_sem_excecao(tmp_path):
    caminho = tmp_path / "modelo.xlsx"
    excel_import.gerar_modelo_importacao(str(caminho))

    pilar, casos = excel_import.importar_pilar_e_cargas(str(caminho))
    perfil = excel_import.importar_perfil_geotecnico(str(caminho))
    solo = Solo(sigma_adm=220.0, perfil=perfil)
    combinacoes = gerar_combinacoes(casos)
    sapata = Sapata(pilar, solo, Concreto(fck=25.0), Aco(fyk=500.0), combinacoes,
                    cobrimento=0.045)
    resultado = sapata.dimensionar()
    assert resultado.a > 0 and resultado.b > 0


# --------------------------------------------------------------------------- #
#  Excel — erros
# --------------------------------------------------------------------------- #
def test_excel_aba_pilar_ausente(tmp_path):
    caminho = tmp_path / "sem_aba.xlsx"
    livro = openpyxl.Workbook()
    livro.active.title = "Outra coisa"
    livro.save(str(caminho))
    with pytest.raises(ValueError, match="Pilar e cargas"):
        excel_import.importar_pilar_e_cargas(str(caminho))


def test_excel_aba_perfil_ausente_e_aba_ausente(tmp_path):
    caminho = tmp_path / "sem_perfil.xlsx"
    livro = openpyxl.Workbook()
    ws = livro.active
    ws.title = excel_import.ABA_PILAR
    ws.append(excel_import.CABECALHO_PILAR)
    ws.append([0.3, 0.3, "G", 500.0, 0.0, 0.0])
    livro.save(str(caminho))
    with pytest.raises(excel_import.AbaAusente):
        excel_import.importar_perfil_geotecnico(str(caminho))
    # AbaAusente é ValueError — quem só trata ValueError continua funcionando
    with pytest.raises(ValueError):
        excel_import.importar_perfil_geotecnico(str(caminho))


# --------------------------------------------------------------------------- #
#  PainelEntrada.preencher_casos — nomes de caso fora de G/Q/W
#
#  Reproduz o defeito achado na verificação independente de 2026-08-28:
#  `preencher_casos` reconhecia só "G"/"Q"/"W" e descartava qualquer outro
#  nome em silêncio (sem erro, sem aviso — o caso simplesmente sumia e
#  `ler_casos()` devolvia só "G" com os valores PADRÃO da tela). Isso é
#  exatamente o formato de `CasoCarga` que uma importação de Excel produz
#  quando a coluna "caso" traz um nome livre (ex. "Permanente",
#  "Acidental") em vez de "G"/"Q"/"W".
#
#  `PainelEntrada` é `ttk.Frame` (herda de `tkinter`) — importar o módulo
#  exige que `tkinter` esteja instalado (não exige um display X/Xvfb: só a
#  biblioteca). `pytest.importorskip` deixa este teste pular, em vez de
#  quebrar a suíte inteira, num ambiente sem `tkinter` (ex.: python
#  compilado sem Tcl/Tk) — mesma cautela dos outros testes deste pacote que
#  evitam depender de Tk/Xvfb (ver tests/test_perfil_cortes_espraiamento.py,
#  tests/test_visual2d_rotulos_espraiamento.py). O caminho de erro de
#  `preencher_casos` não toca em nenhum widget antes de levantar
#  `ValueError` (é a primeira coisa que a função faz), então chamá-lo sem
#  instanciar de fato uma janela Tk (sem `self` real) já basta para provar
#  a correção — não precisa de Xvfb.
# --------------------------------------------------------------------------- #
def test_preencher_casos_rejeita_nomes_fora_de_gqw():
    tk = pytest.importorskip("tkinter")
    from ui.completo.formulario import PainelEntrada

    casos = [
        CasoCarga(nome="Permanente", esforcos=Esforcos(N=600.0, Mx=15.0, My=8.0)),
        CasoCarga(nome="Acidental", esforcos=Esforcos(N=180.0, Mx=6.0, My=0.0)),
    ]

    class _FormularioFalso:
        """Só precisa existir como primeiro argumento posicional — o ramo de
        erro de `preencher_casos` nunca lê/escreve nenhum atributo antes de
        levantar `ValueError`, então nenhum widget Tk real é necessário."""

    with pytest.raises(ValueError, match=r"Permanente.*Acidental|Acidental.*Permanente"):
        PainelEntrada.preencher_casos(_FormularioFalso(), casos)

    # a mensagem cita os 3 nomes aceitos, para orientar a correção
    with pytest.raises(ValueError, match=r"'G', 'Q', 'W'"):
        PainelEntrada.preencher_casos(_FormularioFalso(), casos)

    del tk  # só usado para o importorskip acima


def test_preencher_casos_aceita_gqw_sem_erro_no_ramo_de_validacao():
    """Nomes válidos (G/Q/W, em qualquer subconjunto) não devem cair no
    ramo de erro — só confere que a lista de "desconhecidos" fica vazia
    (mesma lógica do guard clause), sem precisar preencher widgets reais."""
    pytest.importorskip("tkinter")
    from ui.completo.formulario import PainelEntrada

    casos = [CasoCarga(nome="G", esforcos=Esforcos(N=600.0)),
             CasoCarga(nome="Q", esforcos=Esforcos(N=180.0))]

    class _RegistraChamadas:
        chamado = False

    # Se a validação passar, a função segue para o corpo normal, que tenta
    # usar self.v_G/self.usar_q/etc — widgets que este dublê não tem. O
    # comportamento esperado aqui é falhar por FALTA desses atributos
    # (AttributeError), não por ValueError de nome não reconhecido — o que
    # prova que "G" e "Q" passaram no guard clause sem serem rejeitados.
    with pytest.raises(AttributeError):
        PainelEntrada.preencher_casos(_RegistraChamadas(), casos)


def test_modelo_excel_nao_sugere_mais_g_mais_q_como_nome_de_caso(tmp_path):
    """A instrução antiga (`caso: ... ex. 'G', 'G+Q'`) convidava o usuário a
    usar exatamente o tipo de nome que `preencher_casos` rejeita — cobre os
    itens 3 do defeito reportado em 2026-08-28: nem o docstring do módulo
    nem o texto gravado na aba "Instruções" do modelo gerado devem mais
    sugerir "G+Q" como nome de caso."""
    caminho_modulo = (Path(excel_import.__file__))
    texto_modulo = caminho_modulo.read_text(encoding="utf-8")
    assert "G+Q" not in texto_modulo

    caminho_xlsx = tmp_path / "modelo.xlsx"
    excel_import.gerar_modelo_importacao(str(caminho_xlsx))
    livro = openpyxl.load_workbook(str(caminho_xlsx))
    ws_instr = livro[excel_import.ABA_INSTRUCOES]
    texto_instrucoes = "\n".join(
        str(c.value) for linha in ws_instr.iter_rows() for c in linha
        if c.value is not None)
    assert "G+Q" not in texto_instrucoes
    # a instrução deve deixar explícito que o nome tem de casar com G/Q/W
    # para a importação automática de pilar/cargas na tela funcionar
    assert "'G', 'Q' ou 'W'" in texto_instrucoes


def test_excel_celula_obrigatoria_vazia(tmp_path):
    caminho = tmp_path / "n_vazio.xlsx"
    livro = openpyxl.Workbook()
    ws = livro.active
    ws.title = excel_import.ABA_PILAR
    ws.append(excel_import.CABECALHO_PILAR)
    ws.append([0.3, 0.3, "G", None, 0.0, 0.0])
    livro.save(str(caminho))
    with pytest.raises(ValueError, match=r"linha 2.*N \(kN\)"):
        excel_import.importar_pilar_e_cargas(str(caminho))


def test_excel_valor_nao_numerico(tmp_path):
    caminho = tmp_path / "n_texto.xlsx"
    livro = openpyxl.Workbook()
    ws = livro.active
    ws.title = excel_import.ABA_PILAR
    ws.append(excel_import.CABECALHO_PILAR)
    ws.append([0.3, 0.3, "G", "muito", 0.0, 0.0])
    livro.save(str(caminho))
    with pytest.raises(ValueError, match="não é numérico"):
        excel_import.importar_pilar_e_cargas(str(caminho))


def test_excel_tipo_substrato_invalido(tmp_path):
    caminho = tmp_path / "tipo_ruim.xlsx"
    livro = openpyxl.Workbook()
    ws = livro.active
    ws.title = excel_import.ABA_PERFIL
    ws.append(excel_import.CABECALHO_PERFIL)
    ws.append(["Camada X", "granito", 1.0, None, None, None, None, None, None])
    livro.save(str(caminho))
    with pytest.raises(ValueError, match="linha 2.*tipo"):
        excel_import.importar_perfil_geotecnico(str(caminho))


def test_excel_arquivo_inexistente():
    with pytest.raises(ValueError, match="não encontrado"):
        excel_import.importar_pilar_e_cargas("/caminho/inexistente.xlsx")


# --------------------------------------------------------------------------- #
#  Exportação do relatório resumo
# --------------------------------------------------------------------------- #
def test_excel_export_relatorio(tmp_path):
    sapata = _sapata_de(_dados_completos())
    resultado = sapata.dimensionar()
    caminho = tmp_path / "relatorio.xlsx"
    excel_export.exportar_relatorio_excel(str(caminho), sapata, resultado)

    livro = openpyxl.load_workbook(str(caminho))
    ws = livro["Resumo"]
    linhas = [tuple(c.value for c in linha) for linha in ws.iter_rows(min_row=2)]
    itens = {linha[1]: linha for linha in linhas}

    assert ws["A1"].value == "Seção"
    situacao_geral = itens["Resultado"][2]
    assert situacao_geral in ("APROVADA", "REPROVADA")
    assert situacao_geral == ("APROVADA" if resultado.aprovado else "REPROVADA")
    assert "a (direção X)" in itens
    assert itens["a (direção X)"][2] == pytest.approx(resultado.a, abs=1e-6)
    assert itens["h (altura total)"][2] == pytest.approx(resultado.h, abs=1e-6)
    # ao menos uma linha por direção de armadura
    assert any(chave.startswith("Direção X — arranjo") for chave in itens)
    assert any(chave.startswith("Direção Y — arranjo") for chave in itens)


def test_excel_export_relatorio_com_reprovacoes(tmp_path):
    """Sapata francamente subdimensionada em modo verificação — cobre o
    ramo de reprovações/alertas na planilha."""
    pilar = Pilar(ap=0.20, bp=0.20)
    solo = Solo(sigma_adm=100.0)
    concreto = Concreto(fck=20.0)
    aco = Aco(fyk=500.0)
    casos = [CasoCarga("G", Esforcos(N=2000.0, Mx=50.0, My=50.0))]
    opcoes = OpcoesProjeto(
        geometria_imposta=GeometriaImposta(a=0.60, b=0.60, h=0.30),
        verificar_recalque=False)
    combinacoes = gerar_combinacoes(casos)
    sapata = Sapata(pilar, solo, concreto, aco, combinacoes, cobrimento=0.045,
                    opcoes=opcoes)
    resultado = sapata.dimensionar()
    assert not resultado.aprovado
    assert resultado.reprovacoes

    caminho = tmp_path / "reprovado.xlsx"
    excel_export.exportar_relatorio_excel(str(caminho), sapata, resultado)
    livro = openpyxl.load_workbook(str(caminho))
    ws = livro["Resumo"]
    secoes = {linha[0].value for linha in ws.iter_rows(min_row=2)}
    assert "Reprovações" in secoes


def test_excel_export_traz_aviso_de_escopo(tmp_path):
    """Defeito D10 do GATE 2, rodada 1: a aba "Resumo" não trazia o aviso
    de escopo amplo, apesar de a planilha existir para circular FORA da
    tela que mostra o banner."""
    sapata = _sapata_de(_dados_completos())
    resultado = sapata.dimensionar()
    caminho = tmp_path / "relatorio.xlsx"
    excel_export.exportar_relatorio_excel(str(caminho), sapata, resultado)

    livro = openpyxl.load_workbook(str(caminho))
    ws = livro["Resumo"]
    linhas = list(ws.iter_rows(min_row=2, values_only=True))
    secoes = [linha[0] for linha in linhas]
    assert secoes[0] == "Aviso"
    texto_aviso = " ".join(str(linha[2]) for linha in linhas if linha[0] == "Aviso")
    assert "ESCOPO AMPLO" in texto_aviso
    assert "PARCIALMENTE EM CONFERÊNCIA" in texto_aviso
    # a seção "Aviso" vem ANTES de "Situação geral" (primeira coisa que o
    # engenheiro vê ao abrir a planilha).
    assert secoes.index("Aviso") < secoes.index("Situação geral")


# --------------------------------------------------------------------------- #
#  Mutantes M3/M6/M8 do GATE 2, rodada 1 — cada teste abaixo MATA um dos três
#  mutantes que sobreviveram à suíte anterior (332 passed mesmo com o bug
#  presente). Ver relatorios/revisao_codigo.json, "mutation_testing".
# --------------------------------------------------------------------------- #
def test_excel_formula_sem_valor_calculado_da_erro_claro(tmp_path):
    """M3: `_abrir(caminho)` trocando `data_only=True` por `False` faz a
    suíte antiga passar do mesmo jeito — nenhum teste cobria célula com
    FÓRMULA sem cache de valor calculado (planilha montada por script,
    nunca aberta no Excel/LibreOffice). `data_only=True` sozinho devolve
    `None` para essa célula, indistinguível de "vazia"; o segundo livro
    (`data_only=False`) é o que permite dar um erro específico em vez de
    "célula obrigatória vazia" (que engana: o usuário VÊ algo na célula)."""
    caminho = tmp_path / "formula.xlsx"
    livro = openpyxl.Workbook()
    ws = livro.active
    ws.title = excel_import.ABA_PILAR
    ws.append(excel_import.CABECALHO_PILAR)
    ws.append([0.3, 0.3, "G", "=100*6", 0.0, 0.0])
    livro.save(str(caminho))
    with pytest.raises(ValueError, match=r"fórmula.*=100\*6"):
        excel_import.importar_pilar_e_cargas(str(caminho))


def test_excel_formula_sem_valor_calculado_em_coluna_opcional(tmp_path):
    """Mesmo cenário do teste acima, mas numa coluna OPCIONAL (Mx): sem a
    correção, o mutante faz `Mx` virar 0.0 em silêncio (célula 'vazia' com
    obrigatorio=False) em vez de recusar a importação."""
    caminho = tmp_path / "formula_opcional.xlsx"
    livro = openpyxl.Workbook()
    ws = livro.active
    ws.title = excel_import.ABA_PILAR
    ws.append(excel_import.CABECALHO_PILAR)
    ws.append([0.3, 0.3, "G", 600.0, "=2+3", 0.0])
    livro.save(str(caminho))
    with pytest.raises(ValueError, match=r"fórmula.*=2\+3"):
        excel_import.importar_pilar_e_cargas(str(caminho))


def test_float_aceita_virgula_decimal_brasileira():
    """M6: remover o `.replace(',', '.')` de `_celula_float`/`_float` faz a
    suíte antiga passar do mesmo jeito — nenhum teste cobria vírgula
    decimal brasileira ('600,5'), nem na planilha nem no formulário."""
    pytest.importorskip("tkinter")
    from ui.completo.formulario import _float, _float_opt

    assert _float("600,5") == pytest.approx(600.5)
    assert _float_opt("12,34") == pytest.approx(12.34)


def test_excel_celula_com_virgula_decimal(tmp_path):
    """Mesmo mutante M6, mas pelo caminho de `excel_import._celula_float`
    (texto, não `int`/`float` nativo do openpyxl) — a planilha guarda o
    número como texto '600,5' (célula formatada como texto, ou colada de
    outra fonte)."""
    caminho = tmp_path / "virgula.xlsx"
    livro = openpyxl.Workbook()
    ws = livro.active
    ws.title = excel_import.ABA_PILAR
    ws.append(excel_import.CABECALHO_PILAR)
    ws.append([0.3, 0.3, "G", "600,5", "15,0", 0.0])
    livro.save(str(caminho))
    _, casos = excel_import.importar_pilar_e_cargas(str(caminho))
    assert casos[0].esforcos.N == pytest.approx(600.5)
    assert casos[0].esforcos.Mx == pytest.approx(15.0)


def test_preencher_materiais_unidade_cobrimento_cm_para_m():
    """M8: `preencher_materiais` trocando `cobrimento*100` por `cobrimento`
    faz a suíte antiga passar do mesmo jeito — bug de UNIDADE cm/m na
    ÚNICA conversão de unidade da feature inteira. `cobrimento` chega em
    METROS (mesma unidade que `ler_materiais` devolve); o campo na tela é
    em CENTÍMETROS."""
    tk = pytest.importorskip("tkinter")
    from ui.completo.formulario import PainelEntrada

    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("sem display Tk disponível neste ambiente (Xvfb)")
    try:
        root.withdraw()
        painel = PainelEntrada(root)
        painel.preencher_materiais(Concreto(fck=30.0), Aco(fyk=500.0),
                                   cobrimento=0.045)
        # 0.045 m = 4.5 cm — se o mutante estiver ativo, o campo mostraria
        # "0.045" em vez de "4.5".
        assert painel.v_cobrimento.get() == "4.5"
        _, _, cobrimento_lido = painel.ler_materiais()
        assert cobrimento_lido == pytest.approx(0.045)
    finally:
        root.destroy()


# --------------------------------------------------------------------------- #
#  Defeitos D2/D3/D4/D5/D6 do GATE 2, rodada 1
# --------------------------------------------------------------------------- #
def test_preencher_casos_rejeita_nomes_duplicados():
    """D2: `por_nome = {c.nome: c for c in casos}` colapsava duas linhas
    "G" em silêncio — o último caso vencia e a carga do primeiro
    desaparecia sem erro nem aviso, subestimando a carga permanente."""
    pytest.importorskip("tkinter")
    from ui.completo.formulario import PainelEntrada

    casos = [
        CasoCarga(nome="G", esforcos=Esforcos(N=600.0)),
        CasoCarga(nome="G", esforcos=Esforcos(N=250.0)),
        CasoCarga(nome="Q", esforcos=Esforcos(N=180.0)),
    ]

    class _FormularioFalso:
        pass

    with pytest.raises(ValueError, match=r"repetido.*'G'"):
        PainelEntrada.preencher_casos(_FormularioFalso(), casos)


def test_excel_importar_pilar_e_cargas_com_nomes_duplicados_nao_falha_aqui(tmp_path):
    """`importar_pilar_e_cargas` (camada de baixo nível) continua aceitando
    nomes repetidos — ela não sabe nada sobre os slots fixos da tela; é
    `preencher_casos`, uma camada acima, que recusa. Este teste apenas
    documenta a fronteira onde a rejeição acontece."""
    caminho = tmp_path / "duas_g.xlsx"
    livro = openpyxl.Workbook()
    ws = livro.active
    ws.title = excel_import.ABA_PILAR
    ws.append(excel_import.CABECALHO_PILAR)
    ws.append([0.3, 0.3, "G", 600.0, 10.0, 5.0])
    ws.append([None, None, "G", 250.0, 30.0, 0.0])
    ws.append([None, None, "Q", 180.0, 6.0, 0.0])
    livro.save(str(caminho))
    _, casos = excel_import.importar_pilar_e_cargas(str(caminho))
    assert [c.nome for c in casos] == ["G", "G", "Q"]

    pytest.importorskip("tkinter")
    from ui.completo.formulario import PainelEntrada

    class _FormularioFalso:
        pass

    with pytest.raises(ValueError, match="repetido"):
        PainelEntrada.preencher_casos(_FormularioFalso(), casos)


def test_excel_espessura_negativa_e_recusada(tmp_path):
    """D4: espessura negativa (erro de digitação/sinal) entrava inteira no
    núcleo antes desta correção — com espessura +3,0 m o dimensionamento
    dá recalque REPROVADO; com -3,0 m (mesmo caso, só o sinal trocado) o
    resultado passava para APROVADO em silêncio, perfil de profundidade
    total negativa. Agora a importação recusa antes de chegar no núcleo."""
    caminho = tmp_path / "espessura_negativa.xlsx"
    livro = openpyxl.Workbook()
    ws = livro.active
    ws.title = excel_import.ABA_PERFIL
    ws.append(excel_import.CABECALHO_PERFIL)
    ws.append(["Argila mole", "coesivo", -3.0, None, 0.45, 1.10, 0.02, None, 1.5])
    livro.save(str(caminho))
    with pytest.raises(ValueError, match=r"espessura.*fora do domínio"):
        excel_import.importar_perfil_geotecnico(str(caminho))


def test_excel_nspt_negativo_e_recusado(tmp_path):
    caminho = tmp_path / "nspt_negativo.xlsx"
    livro = openpyxl.Workbook()
    ws = livro.active
    ws.title = excel_import.ABA_PERFIL
    ws.append(excel_import.CABECALHO_PERFIL)
    ws.append(["Areia", "granular", 2.0, -5.0, None, None, None, None, None])
    livro.save(str(caminho))
    with pytest.raises(ValueError, match=r"nspt.*fora do domínio"):
        excel_import.importar_perfil_geotecnico(str(caminho))


def test_excel_nivel_agua_negativo_e_recusado(tmp_path):
    caminho = tmp_path / "na_negativo.xlsx"
    livro = openpyxl.Workbook()
    ws = livro.active
    ws.title = excel_import.ABA_PERFIL
    ws.append(excel_import.CABECALHO_PERFIL)
    ws.append(["Areia", "granular", 2.0, None, None, None, None, None, -1.5])
    livro.save(str(caminho))
    with pytest.raises(ValueError, match=r"nível d'água.*fora do domínio"):
        excel_import.importar_perfil_geotecnico(str(caminho))


def test_excel_valor_logico_bool_e_recusado(tmp_path):
    """D7: `isinstance(valor, (int, float))` aceita `bool` (subclasse de
    `int` em Python) — TRUE numa célula numérica virava 1.0 em silêncio."""
    caminho = tmp_path / "bool.xlsx"
    livro = openpyxl.Workbook()
    ws = livro.active
    ws.title = excel_import.ABA_PILAR
    ws.append(excel_import.CABECALHO_PILAR)
    ws.append([0.3, 0.3, "G", True, 0.0, 0.0])
    livro.save(str(caminho))
    with pytest.raises(ValueError, match="lógico"):
        excel_import.importar_pilar_e_cargas(str(caminho))


def test_excel_ap_conflitante_entre_linhas_e_recusado(tmp_path):
    """`ap`/`bp` só são lidos da primeira linha — um valor DIFERENTE numa
    linha seguinte agora é recusado em vez de descartado em silêncio."""
    caminho = tmp_path / "ap_conflitante.xlsx"
    livro = openpyxl.Workbook()
    ws = livro.active
    ws.title = excel_import.ABA_PILAR
    ws.append(excel_import.CABECALHO_PILAR)
    ws.append([0.30, 0.30, "G", 600.0, 10.0, 5.0])
    ws.append([0.90, 0.90, "Q", 180.0, 6.0, 0.0])
    livro.save(str(caminho))
    with pytest.raises(ValueError, match=r"conflita"):
        excel_import.importar_pilar_e_cargas(str(caminho))


def test_excel_ap_repetido_igual_continua_aceito(tmp_path):
    caminho = tmp_path / "ap_repetido.xlsx"
    livro = openpyxl.Workbook()
    ws = livro.active
    ws.title = excel_import.ABA_PILAR
    ws.append(excel_import.CABECALHO_PILAR)
    ws.append([0.30, 0.30, "G", 600.0, 10.0, 5.0])
    ws.append([0.30, 0.30, "Q", 180.0, 6.0, 0.0])
    livro.save(str(caminho))
    pilar, casos = excel_import.importar_pilar_e_cargas(str(caminho))
    assert pilar.ap == pytest.approx(0.30)
    assert len(casos) == 2


def test_excel_nivel_agua_conflitante_entre_linhas_e_recusado(tmp_path):
    caminho = tmp_path / "na_conflitante.xlsx"
    livro = openpyxl.Workbook()
    ws = livro.active
    ws.title = excel_import.ABA_PERFIL
    ws.append(excel_import.CABECALHO_PERFIL)
    ws.append(["Areia", "granular", 2.0, None, None, None, None, None, 1.5])
    ws.append(["Argila", "coesivo", 3.0, None, 0.4, 1.0, 0.02, None, 2.5])
    livro.save(str(caminho))
    with pytest.raises(ValueError, match=r"conflita"):
        excel_import.importar_perfil_geotecnico(str(caminho))


# --------------------------------------------------------------------------- #
#  D14 (projeto.py): validação numérica de tipo/domínio na fronteira do
#  .s7proj — antes desta correção, todos os casos abaixo eram aceitos SEM
#  erro (`carregar_projeto` validava estrutura, não tipo/domínio, apesar de
#  a docstring prometer isso).
# --------------------------------------------------------------------------- #
def _projeto_base() -> dict:
    return {
        "formato": "sapata7-projeto", "versao": 1,
        "pilar": {"ap": 0.3, "bp": 0.3},
        "solo": {"sigma_adm": 200.0},
        "concreto": {"fck": 25.0}, "aco": {"fyk": 500.0},
        "cobrimento": 0.045,
        "casos": [{"nome": "G", "N": 300.0}], "opcoes": {},
    }


def _escrever_projeto(tmp_path, dados: dict, nome: str = "p.s7proj") -> str:
    caminho = tmp_path / nome
    caminho.write_text(json.dumps(dados), encoding="utf-8")
    return str(caminho)


def test_projeto_espessura_camada_string_e_recusada(tmp_path):
    dados = _projeto_base()
    dados["solo"]["perfil"] = {
        "camadas": [{"nome": "X", "espessura": "dois metros", "tipo": "coesivo"}]}
    caminho = _escrever_projeto(tmp_path, dados)
    with pytest.raises(ValueError, match=r"espessura.*esperado número"):
        projeto.carregar_projeto(caminho)


def test_projeto_espessura_camada_negativa_e_recusada(tmp_path):
    dados = _projeto_base()
    dados["solo"]["perfil"] = {
        "camadas": [{"nome": "X", "espessura": -2.0, "tipo": "coesivo"}]}
    caminho = _escrever_projeto(tmp_path, dados)
    with pytest.raises(ValueError, match=r"espessura.*> 0"):
        projeto.carregar_projeto(caminho)


def test_projeto_sigma_adm_negativo_e_recusado(tmp_path):
    dados = _projeto_base()
    dados["solo"]["sigma_adm"] = -200.0
    caminho = _escrever_projeto(tmp_path, dados)
    with pytest.raises(ValueError, match=r"sigma_adm.*> 0"):
        projeto.carregar_projeto(caminho)


def test_projeto_cobrimento_string_e_recusado(tmp_path):
    dados = _projeto_base()
    dados["cobrimento"] = "4.5cm"
    caminho = _escrever_projeto(tmp_path, dados)
    with pytest.raises(ValueError, match=r"cobrimento.*esperado número"):
        projeto.carregar_projeto(caminho)


def test_projeto_cobrimento_nulo_e_recusado(tmp_path):
    dados = _projeto_base()
    dados["cobrimento"] = None
    caminho = _escrever_projeto(tmp_path, dados)
    with pytest.raises(ValueError, match=r"cobrimento.*nulo"):
        projeto.carregar_projeto(caminho)


def test_projeto_camadas_nulo_vira_erro_nao_lista_vazia(tmp_path):
    dados = _projeto_base()
    dados["solo"]["perfil"] = {"camadas": None}
    caminho = _escrever_projeto(tmp_path, dados)
    with pytest.raises(ValueError, match=r"camadas.*não pode ser nulo"):
        projeto.carregar_projeto(caminho)


def test_projeto_camadas_vazia_continua_aceita(tmp_path):
    dados = _projeto_base()
    dados["solo"]["perfil"] = {"camadas": []}
    caminho = _escrever_projeto(tmp_path, dados)
    dados_carregados = projeto.carregar_projeto(caminho)
    assert dados_carregados["solo"].perfil is not None
    assert dados_carregados["solo"].perfil.camadas == []


def test_projeto_direcao_armadura_invalida_e_recusada(tmp_path):
    dados = _projeto_base()
    dados["opcoes"] = {"armaduras_impostas": {"Z": {"phi_mm": 12.5}}}
    caminho = _escrever_projeto(tmp_path, dados)
    with pytest.raises(ValueError, match=r"direção 'Z' desconhecida"):
        projeto.carregar_projeto(caminho)


def test_projeto_opcao_booleana_como_string_e_recusada(tmp_path):
    dados = _projeto_base()
    dados["opcoes"] = {"verificar_recalque": "sim"}
    caminho = _escrever_projeto(tmp_path, dados)
    with pytest.raises(ValueError, match=r"verificar_recalque.*esperado bool"):
        projeto.carregar_projeto(caminho)


def test_projeto_opcao_numerica_como_string_e_recusada(tmp_path):
    dados = _projeto_base()
    dados["opcoes"] = {"max_iteracoes": "oitenta"}
    caminho = _escrever_projeto(tmp_path, dados)
    with pytest.raises(ValueError, match=r"max_iteracoes.*esperado int"):
        projeto.carregar_projeto(caminho)


def test_projeto_N_bool_e_recusado(tmp_path):
    dados = _projeto_base()
    dados["casos"][0]["N"] = True
    caminho = _escrever_projeto(tmp_path, dados)
    with pytest.raises(ValueError, match=r"N.*esperado número"):
        projeto.carregar_projeto(caminho)


def test_projeto_opcao_float_aceita_inteiro_sem_ponto_decimal(tmp_path):
    """JSON não distingue `1` de `1.0` — um editor manual ou outra
    ferramenta pode gravar um campo `float` de `OpcoesProjeto` (ex.:
    `dim_minima`) como inteiro sem parte decimal. Isso tem de continuar
    sendo aceito (e convertido para `float`); só `bool` é recusado."""
    dados = _projeto_base()
    dados["opcoes"] = {"dim_minima": 1, "modulo_dim": 1}
    caminho = _escrever_projeto(tmp_path, dados)
    carregado = projeto.carregar_projeto(caminho)
    assert carregado["opcoes"].dim_minima == pytest.approx(1.0)
    assert isinstance(carregado["opcoes"].dim_minima, float)


def test_projeto_opcao_float_ainda_recusa_bool(tmp_path):
    dados = _projeto_base()
    dados["opcoes"] = {"dim_minima": True}
    caminho = _escrever_projeto(tmp_path, dados)
    with pytest.raises(ValueError, match=r"dim_minima.*esperado float"):
        projeto.carregar_projeto(caminho)


def test_projeto_opcoes_sem_chave_usa_default_do_nucleo_nao_literal_copiado(tmp_path):
    """D8: `_dict_para_solo`/`_dict_para_pilar`/etc não devem mais copiar um
    literal (`d.get('fs_deslizamento', 1.5)`) — a chave ausente tem de
    resultar no default ATUAL do dataclass do núcleo, não num número
    fixado na UI. Não dá para reproduzir uma divergência hoje (os literais
    antigos batiam com o núcleo), mas o teste prende o COMPORTAMENTO: o
    valor carregado bate com `Solo()`/`Pilar()` vazios, não com um literal
    hard-coded neste teste."""
    dados = _projeto_base()
    caminho = _escrever_projeto(tmp_path, dados)
    carregado = projeto.carregar_projeto(caminho)
    assert carregado["solo"].fs_deslizamento == Solo(sigma_adm=200.0).fs_deslizamento
    assert carregado["solo"].fs_tombamento == Solo(sigma_adm=200.0).fs_tombamento
    assert carregado["pilar"].phi_arranque_mm == Pilar(ap=0.3, bp=0.3).phi_arranque_mm
    assert carregado["casos"][0].psi0 == CasoCarga("G", Esforcos()).psi0


def test_projeto_salvar_e_atomico_arquivo_antigo_sobrevive_a_falha(tmp_path,
                                                                    monkeypatch):
    """`salvar_projeto` escreve num temporário + `os.replace` — se
    `json.dump` falhar no meio, o arquivo ANTERIOR do usuário não pode
    ficar truncado."""
    caminho = tmp_path / "existente.s7proj"
    dados_originais = _dados_completos()
    projeto.salvar_projeto(str(caminho), dados_originais["pilar"],
                           dados_originais["solo"], dados_originais["concreto"],
                           dados_originais["aco"], dados_originais["cobrimento"],
                           dados_originais["casos"], dados_originais["opcoes"])
    conteudo_original = caminho.read_text(encoding="utf-8")

    def _json_dump_com_falha(*a, **kw):
        raise OSError("disco cheio (simulado)")

    monkeypatch.setattr(projeto.json, "dump", _json_dump_com_falha)
    with pytest.raises(ValueError, match="Não foi possível salvar"):
        projeto.salvar_projeto(str(caminho), dados_originais["pilar"],
                               dados_originais["solo"], dados_originais["concreto"],
                               dados_originais["aco"], dados_originais["cobrimento"],
                               dados_originais["casos"], dados_originais["opcoes"])
    assert caminho.read_text(encoding="utf-8") == conteudo_original
    # nenhum arquivo temporário sobra no diretório
    assert list(tmp_path.glob(".s7proj_tmp_*")) == []


# --------------------------------------------------------------------------- #
#  GATE 2, rodada 2 — mutantes M11/M15: fronteira "estrito" (valor == 0, não
#  só negativo) para espessura/ap/sigma_adm/fck, tanto pelo Excel quanto pelo
#  .s7proj. Os testes de rodada 1 só cobriam valor NEGATIVO.
# --------------------------------------------------------------------------- #
def test_excel_espessura_zero_e_recusada(tmp_path):
    """M11: espessura = 0 (fronteira exata de `estrito=True`, distinta do
    caso negativo já coberto por `test_excel_espessura_negativa_e_recusada`)."""
    caminho = tmp_path / "espessura_zero.xlsx"
    livro = openpyxl.Workbook()
    ws = livro.active
    ws.title = excel_import.ABA_PERFIL
    ws.append(excel_import.CABECALHO_PERFIL)
    ws.append(["Argila mole", "coesivo", 0.0, None, 0.45, 1.10, 0.02, None, None])
    livro.save(str(caminho))
    with pytest.raises(ValueError, match=r"espessura.*fora do domínio"):
        excel_import.importar_perfil_geotecnico(str(caminho))


def test_excel_ap_zero_e_recusado(tmp_path):
    """M11: ap = 0."""
    caminho = tmp_path / "ap_zero.xlsx"
    livro = openpyxl.Workbook()
    ws = livro.active
    ws.title = excel_import.ABA_PILAR
    ws.append(excel_import.CABECALHO_PILAR)
    ws.append([0.0, 0.3, "G", 600.0, 0.0, 0.0])
    livro.save(str(caminho))
    with pytest.raises(ValueError, match=r"ap.*fora do domínio"):
        excel_import.importar_pilar_e_cargas(str(caminho))


def test_projeto_espessura_camada_zero_e_recusada(tmp_path):
    """M15: mesma fronteira, agora pelo .s7proj (`_num` em vez de
    `_celula_float`)."""
    dados = _projeto_base()
    dados["solo"]["perfil"] = {
        "camadas": [{"nome": "X", "espessura": 0.0, "tipo": "coesivo"}]}
    caminho = _escrever_projeto(tmp_path, dados)
    with pytest.raises(ValueError, match=r"espessura.*> 0"):
        projeto.carregar_projeto(caminho)


def test_projeto_ap_zero_e_recusado(tmp_path):
    dados = _projeto_base()
    dados["pilar"]["ap"] = 0.0
    caminho = _escrever_projeto(tmp_path, dados)
    with pytest.raises(ValueError, match=r"ap.*> 0"):
        projeto.carregar_projeto(caminho)


def test_projeto_sigma_adm_zero_e_recusado(tmp_path):
    dados = _projeto_base()
    dados["solo"]["sigma_adm"] = 0.0
    caminho = _escrever_projeto(tmp_path, dados)
    with pytest.raises(ValueError, match=r"sigma_adm.*> 0"):
        projeto.carregar_projeto(caminho)


def test_projeto_fck_zero_e_recusado(tmp_path):
    dados = _projeto_base()
    dados["concreto"]["fck"] = 0.0
    caminho = _escrever_projeto(tmp_path, dados)
    with pytest.raises(ValueError, match=r"fck.*> 0"):
        projeto.carregar_projeto(caminho)


# --------------------------------------------------------------------------- #
#  GATE 2, rodada 2 — mutante M25: `drenagem_dupla` não-booleano numa camada
#  do .s7proj.
# --------------------------------------------------------------------------- #
def test_projeto_drenagem_dupla_nao_booleana_e_recusada(tmp_path):
    dados = _projeto_base()
    dados["solo"]["perfil"] = {
        "camadas": [{"nome": "X", "espessura": 1.0, "tipo": "coesivo",
                    "drenagem_dupla": "sim"}]}
    caminho = _escrever_projeto(tmp_path, dados)
    with pytest.raises(ValueError, match=r"drenagem_dupla.*verdadeiro/falso"):
        projeto.carregar_projeto(caminho)


# --------------------------------------------------------------------------- #
#  GATE 2, rodada 2 — MEDIA #3: nível d'água em branco na PRIMEIRA linha de
#  dados e preenchido numa linha seguinte — reproduz o cenário exato do
#  relatório (linha 2 em branco, linha 3 = 2,5), que antes devolvia
#  `nivel_agua=None` em silêncio (recalque subestimado, lado inseguro).
# --------------------------------------------------------------------------- #
def test_excel_nivel_agua_em_branco_na_primeira_linha_e_preenchido_depois_e_recusado(
        tmp_path):
    caminho = tmp_path / "na_branco_depois_preenchido.xlsx"
    livro = openpyxl.Workbook()
    ws = livro.active
    ws.title = excel_import.ABA_PERFIL
    ws.append(excel_import.CABECALHO_PERFIL)
    ws.append(["Areia", "granular", 2.0, None, None, None, None, None, None])
    ws.append(["Argila", "coesivo", 3.0, None, 0.4, 1.0, 0.02, None, 2.5])
    livro.save(str(caminho))
    with pytest.raises(ValueError, match=r"conflita"):
        excel_import.importar_perfil_geotecnico(str(caminho))


def test_excel_nivel_agua_em_branco_nas_duas_linhas_continua_aceito(tmp_path):
    """Não pode virar falso positivo: as duas linhas em branco na coluna de
    N.A. continuam significando 'sem N.A. informado', sem erro."""
    caminho = tmp_path / "na_branco_nas_duas.xlsx"
    livro = openpyxl.Workbook()
    ws = livro.active
    ws.title = excel_import.ABA_PERFIL
    ws.append(excel_import.CABECALHO_PERFIL)
    ws.append(["Areia", "granular", 2.0, None, None, None, None, None, None])
    ws.append(["Argila", "coesivo", 3.0, None, 0.4, 1.0, 0.02, None, None])
    livro.save(str(caminho))
    perfil = excel_import.importar_perfil_geotecnico(str(caminho))
    assert perfil.nivel_agua is None


# --------------------------------------------------------------------------- #
#  GATE 2, rodada 2 — MEDIA #2: `null` em campo não-opcional, domínio
#  numérico de `OpcoesProjeto`, `modelo_reacao`/`modelo_armadura_rigida`
#  fora da lista aceita, e cada elemento de `bitolas`.
# --------------------------------------------------------------------------- #
def test_projeto_opcao_nao_opcional_nula_e_recusada(tmp_path):
    dados = _projeto_base()
    dados["opcoes"] = {"limite_recalque_mm": None}
    caminho = _escrever_projeto(tmp_path, dados)
    with pytest.raises(ValueError, match=r"limite_recalque_mm.*'null'"):
        projeto.carregar_projeto(caminho)


def test_projeto_opcao_optional_nula_continua_aceita(tmp_path):
    """`travar_a`/`travar_b`/`kv` são `Optional[float]` — `null` continua
    válido (não é a mesma classe de bug que campo não-opcional nulo)."""
    dados = _projeto_base()
    dados["opcoes"] = {"travar_a": None, "kv": None}
    caminho = _escrever_projeto(tmp_path, dados)
    carregado = projeto.carregar_projeto(caminho)
    assert carregado["opcoes"].travar_a is None
    assert carregado["opcoes"].kv is None


def test_projeto_max_iteracoes_zero_e_recusado(tmp_path):
    dados = _projeto_base()
    dados["opcoes"] = {"max_iteracoes": 0}
    caminho = _escrever_projeto(tmp_path, dados)
    with pytest.raises(ValueError, match=r"max_iteracoes.*> 0"):
        projeto.carregar_projeto(caminho)


def test_projeto_dim_minima_negativa_e_recusada(tmp_path):
    dados = _projeto_base()
    dados["opcoes"] = {"dim_minima": -1.0}
    caminho = _escrever_projeto(tmp_path, dados)
    with pytest.raises(ValueError, match=r"dim_minima.*> 0"):
        projeto.carregar_projeto(caminho)


def test_projeto_limite_recalque_negativo_e_recusado(tmp_path):
    dados = _projeto_base()
    dados["opcoes"] = {"limite_recalque_mm": -25.0}
    caminho = _escrever_projeto(tmp_path, dados)
    with pytest.raises(ValueError, match=r"limite_recalque_mm.*> 0"):
        projeto.carregar_projeto(caminho)


def test_projeto_modulo_dim_zero_e_recusado(tmp_path):
    dados = _projeto_base()
    dados["opcoes"] = {"modulo_dim": 0.0}
    caminho = _escrever_projeto(tmp_path, dados)
    with pytest.raises(ValueError, match=r"modulo_dim.*> 0"):
        projeto.carregar_projeto(caminho)


def test_projeto_modelo_reacao_invalido_e_recusado(tmp_path):
    dados = _projeto_base()
    dados["opcoes"] = {"modelo_reacao": "rigid"}
    caminho = _escrever_projeto(tmp_path, dados)
    with pytest.raises(ValueError, match=r"modelo_reacao.*'rigid'"):
        projeto.carregar_projeto(caminho)


def test_projeto_modelo_armadura_rigida_invalido_e_recusado(tmp_path):
    dados = _projeto_base()
    dados["opcoes"] = {"modelo_armadura_rigida": "bielaz"}
    caminho = _escrever_projeto(tmp_path, dados)
    with pytest.raises(ValueError, match=r"modelo_armadura_rigida.*'bielaz'"):
        projeto.carregar_projeto(caminho)


def test_projeto_modelos_validos_continuam_aceitos(tmp_path):
    dados = _projeto_base()
    dados["opcoes"] = {"modelo_reacao": "grelha",
                       "modelo_armadura_rigida": "flexao"}
    caminho = _escrever_projeto(tmp_path, dados)
    carregado = projeto.carregar_projeto(caminho)
    assert carregado["opcoes"].modelo_reacao == "grelha"
    assert carregado["opcoes"].modelo_armadura_rigida == "flexao"


def test_projeto_bitola_negativa_e_recusada(tmp_path):
    dados = _projeto_base()
    dados["opcoes"] = {"bitolas": [10.0, -1.0]}
    caminho = _escrever_projeto(tmp_path, dados)
    with pytest.raises(ValueError, match=r"bitolas\[1\].*esperado número"):
        projeto.carregar_projeto(caminho)


def test_projeto_bitola_textual_e_recusada(tmp_path):
    dados = _projeto_base()
    dados["opcoes"] = {"bitolas": ["a", 10.0]}
    caminho = _escrever_projeto(tmp_path, dados)
    with pytest.raises(ValueError, match=r"bitolas\[0\].*esperado número"):
        projeto.carregar_projeto(caminho)


def test_projeto_bitolas_validas_continuam_aceitas(tmp_path):
    dados = _projeto_base()
    dados["opcoes"] = {"bitolas": [8.0, 10.0, 12.5]}
    caminho = _escrever_projeto(tmp_path, dados)
    carregado = projeto.carregar_projeto(caminho)
    assert carregado["opcoes"].bitolas == (8.0, 10.0, 12.5)


# --------------------------------------------------------------------------- #
#  GATE 2, rodada 2 — MEDIA #4: `campos_divergentes_do_default`.
# --------------------------------------------------------------------------- #
def test_campos_divergentes_do_default_vazio_quando_tudo_no_padrao(tmp_path):
    dados_originais = _dados_completos()
    dados_originais["opcoes"] = OpcoesProjeto()   # sem nada avançado
    dados_originais["pilar"] = Pilar(ap=0.3, bp=0.3)   # sem n_barras custom
    dados_originais["casos"] = [CasoCarga("G", Esforcos(N=400.0))]
    caminho = tmp_path / "sem_divergencia.s7proj"
    projeto.salvar_projeto(str(caminho), dados_originais["pilar"],
                           dados_originais["solo"], dados_originais["concreto"],
                           dados_originais["aco"], dados_originais["cobrimento"],
                           dados_originais["casos"], dados_originais["opcoes"])
    dados = projeto.carregar_projeto(str(caminho))
    assert projeto.campos_divergentes_do_default(dados) == []


def test_campos_divergentes_do_default_lista_campos_perdidos(tmp_path):
    pilar = Pilar(ap=0.3, bp=0.3, n_barras=8, as_calc_efetiva=0.9)
    solo = Solo(sigma_adm=200.0, fs_deslizamento=2.0)
    concreto = Concreto(fck=25.0, gamma_c=1.5)
    aco = Aco(fyk=500.0)
    casos = [CasoCarga("G", Esforcos(N=300.0), psi0=0.5)]
    opcoes = OpcoesProjeto(max_iteracoes=120)
    caminho = tmp_path / "com_divergencia.s7proj"
    projeto.salvar_projeto(str(caminho), pilar, solo, concreto, aco, 0.045,
                           casos, opcoes)
    dados = projeto.carregar_projeto(str(caminho))
    divergentes = " | ".join(projeto.campos_divergentes_do_default(dados))
    assert "pilar.n_barras" in divergentes
    assert "solo.fs_deslizamento" in divergentes
    assert "concreto.gamma_c" in divergentes
    assert "opcoes.max_iteracoes" in divergentes
    assert "psi0" in divergentes
    # `categoria` do aço é sempre re-inferida de fyk (que a tela restaura) —
    # não deve gerar falso positivo mesmo sem ter sido explicitada.
    assert "aco.categoria" not in divergentes


# --------------------------------------------------------------------------- #
#  MEDIA #5 do GATE 2, rodada 2: trava para o CI nunca mais rodar a suíte de
#  Tk em modo "skip" silencioso. `app_completo` (fixture abaixo) faz
#  `pytest.skip(...)` sem display — comportamento correto para um ambiente
#  de DESENVOLVEDOR sem X, mas catastrófico dentro do CI (job `testes` do
#  workflow), que TEM de ter Xvfb: measurement do relatório mostrou "361
#  passed, 5 skipped" sem Xvfb — a suíte inteira "passa" mesmo com os
#  mutantes que reintroduzem o ALTA #1 e o bug de unidade cm/m (ambos só
#  cobertos pelos testes que dependem de `tk.Tk()`). `CI=true` é definida
#  pelo GitHub Actions (e pelo próprio workflow deste repositório, ver
#  `.github/workflows/build-exe.yml`) em todo job — se ela estiver
#  presente e não houver `DISPLAY`, é sinal de que o job ESQUECEU o Xvfb;
#  este teste FALHA (não pula) para isso nunca mais passar despercebido.
# --------------------------------------------------------------------------- #
def test_ci_exige_display_para_suite_de_tk():
    if os.environ.get("CI") and not os.environ.get("DISPLAY"):
        pytest.fail(
            "CI está definida mas DISPLAY está vazio/ausente — os testes "
            "que dependem de tk.Tk() (fixture app_completo, cobrindo o "
            "ALTA #1 do GATE 2 rodada 2 e outros) vão SKIPAR em vez de "
            "RODAR, deixando a proteção desta feature inerte no CI. "
            "Verifique se o job 'testes' de "
            ".github/workflows/build-exe.yml instala o pacote 'xvfb' e "
            "roda a suíte com 'xvfb-run -a'.")


# --------------------------------------------------------------------------- #
#  D3/D5/D6 (app.py) — precisam de um `tk.Tk()` de verdade sob Xvfb, porque
#  tocam em `self.resultado`/`self.visualizacao`/`self.status_esquerda`, não
#  só em `self.formulario` como os testes de `preencher_casos` acima.
# --------------------------------------------------------------------------- #
@pytest.fixture
def app_completo():
    tk = pytest.importorskip("tkinter")
    from ui.completo.app import AppSapataCompleto
    try:
        app = AppSapataCompleto()
    except tk.TclError:
        pytest.skip("sem display Tk disponível neste ambiente (Xvfb)")
    app.withdraw()
    yield app
    app.destroy()


def test_abrir_outro_projeto_invalida_resultado_anterior(app_completo, tmp_path):
    """D3: exportar PDF/Excel depois de abrir outro projeto (sem apertar
    F5) exportava o cálculo do projeto ANTERIOR — reproduz exatamente o
    cenário do relatório: projeto A (20x50 cm, sigma_adm 250 kPa)
    calculado, depois projeto B (60x60 cm, sigma_adm 120 kPa) aberto SEM
    recalcular."""
    from unittest import mock

    caminho_a = str(tmp_path / "a.s7proj")
    projeto.salvar_projeto(
        caminho_a, Pilar(ap=0.20, bp=0.50), Solo(sigma_adm=250.0),
        Concreto(fck=25.0), Aco(fyk=500.0), 0.045,
        [CasoCarga("G", Esforcos(N=600.0, Mx=15.0, My=8.0))], OpcoesProjeto())
    caminho_b = str(tmp_path / "b.s7proj")
    projeto.salvar_projeto(
        caminho_b, Pilar(ap=0.60, bp=0.60), Solo(sigma_adm=120.0),
        Concreto(fck=25.0), Aco(fyk=500.0), 0.045,
        [CasoCarga("G", Esforcos(N=600.0, Mx=15.0, My=8.0))], OpcoesProjeto())

    app = app_completo
    with mock.patch("ui.completo.app.filedialog.askopenfilename",
                    return_value=caminho_a), \
         mock.patch("ui.completo.app.messagebox.showinfo"), \
         mock.patch("ui.completo.app.messagebox.showerror"):
        app._abrir_projeto()
    app._calcular()
    assert app._resultado is not None and app._sapata is not None

    with mock.patch("ui.completo.app.filedialog.askopenfilename",
                    return_value=caminho_b), \
         mock.patch("ui.completo.app.messagebox.showinfo"), \
         mock.patch("ui.completo.app.messagebox.showerror"):
        app._abrir_projeto()

    assert app._sapata is None
    assert app._resultado is None
    assert app._modelo is None

    with mock.patch("ui.completo.app.filedialog.asksaveasfilename",
                    return_value=str(tmp_path / "nao_deveria_existir.xlsx")), \
         mock.patch("ui.completo.app.messagebox.showinfo") as mock_info, \
         mock.patch("ui.completo.app.messagebox.showerror"):
        app._exportar_excel()
    assert mock_info.called
    assert not (tmp_path / "nao_deveria_existir.xlsx").exists()

    pilar_tela = app.formulario.ler_pilar()
    assert pilar_tela.ap == pytest.approx(0.60)
    assert pilar_tela.bp == pytest.approx(0.60)


def test_importar_excel_nao_troca_pilar_se_casos_forem_recusados(app_completo,
                                                                  tmp_path):
    """D5: `_importar_excel` aplicava `preencher_pilar` ANTES de
    `preencher_casos` — se os casos fossem recusados, o pilar já tinha
    sido trocado e o formulário ficava num estado misto."""
    from unittest import mock

    app = app_completo
    app.formulario.v_ap.set("0.20")
    app.formulario.v_bp.set("0.50")

    caminho = tmp_path / "nome_invalido.xlsx"
    livro = openpyxl.Workbook()
    ws = livro.active
    ws.title = excel_import.ABA_PILAR
    ws.append(excel_import.CABECALHO_PILAR)
    ws.append([0.90, 0.90, "Permanente", 600.0, 10.0, 5.0])
    livro.save(str(caminho))

    with mock.patch("ui.completo.app.filedialog.askopenfilename",
                    return_value=str(caminho)), \
         mock.patch("ui.completo.app.messagebox.showinfo"), \
         mock.patch("ui.completo.app.messagebox.showerror") as mock_err:
        app._importar_excel()

    assert mock_err.called
    pilar_tela = app.formulario.ler_pilar()
    assert pilar_tela.ap == pytest.approx(0.20)
    assert pilar_tela.bp == pytest.approx(0.50)


def test_importar_excel_sem_aba_perfil_mantem_perfil_anterior_e_avisa(
        app_completo, tmp_path):
    """D6: quando a aba "Perfil geotécnico" falta, o perfil que já estava
    na tela é mantido — mas isso precisa ser dito na mensagem final, não
    deixado em silêncio."""
    from unittest import mock

    app = app_completo
    caminho_modelo = tmp_path / "modelo.xlsx"
    excel_import.gerar_modelo_importacao(str(caminho_modelo))
    with mock.patch("ui.completo.app.filedialog.askopenfilename",
                    return_value=str(caminho_modelo)), \
         mock.patch("ui.completo.app.messagebox.showinfo"), \
         mock.patch("ui.completo.app.messagebox.showerror"):
        app._importar_excel()
    perfil_antes = app.formulario.ler_solo().perfil
    assert perfil_antes is not None and len(perfil_antes.camadas) == 2

    caminho_sem_perfil = tmp_path / "sem_perfil.xlsx"
    livro = openpyxl.Workbook()
    ws = livro.active
    ws.title = excel_import.ABA_PILAR
    ws.append(excel_import.CABECALHO_PILAR)
    ws.append([0.30, 0.30, "G", 500.0, 0.0, 0.0])
    livro.save(str(caminho_sem_perfil))

    with mock.patch("ui.completo.app.filedialog.askopenfilename",
                    return_value=str(caminho_sem_perfil)), \
         mock.patch("ui.completo.app.messagebox.showinfo") as mock_info, \
         mock.patch("ui.completo.app.messagebox.showerror"):
        app._importar_excel()

    mensagem = mock_info.call_args[0][1]
    assert "MANTIDO" in mensagem
    assert "2 camada" in mensagem
    perfil_depois = app.formulario.ler_solo().perfil
    assert perfil_depois is not None and len(perfil_depois.camadas) == 2


def test_importar_excel_sem_openpyxl_avisa_e_nao_derruba_o_app(app_completo,
                                                                monkeypatch):
    """D1: sem `openpyxl` instalado, os 4 itens de menu de Excel mostram um
    aviso claro em vez de derrubar o app inteiro com `ModuleNotFoundError`."""
    from unittest import mock

    import ui.completo.app as app_mod

    original_import_module = app_mod.importlib.import_module

    def _falha_so_para_excel(nome, package=None):
        if package == app_mod.__package__ and nome.lstrip(".").startswith("excel"):
            raise ImportError("No module named 'openpyxl'")
        return original_import_module(nome, package)

    monkeypatch.setattr(app_mod.importlib, "import_module", _falha_so_para_excel)
    with mock.patch("ui.completo.app.messagebox.showerror") as mock_err:
        app_completo._importar_excel()
    assert mock_err.called
    assert "openpyxl" in mock_err.call_args[0][1]


# --------------------------------------------------------------------------- #
#  GATE 2, rodada 2 — ALTA #1: `ler_solo()` fora de qualquer try/except em
#  `_importar_excel`. Cenário (a) do relatório: "200 kPa" no campo de
#  sigma_adm (a tela tolera até apertar F5) + "Importar do Excel...".
# --------------------------------------------------------------------------- #
def test_importar_excel_com_solo_invalido_mostra_dialogo_e_nao_mistura_dados(
        app_completo, tmp_path):
    """Sem a correção: `ler_solo()` só era chamada DEPOIS de
    `preencher_casos`/`preencher_pilar` já terem trocado o pilar/casos na
    tela — o `ValueError` de `_float("200 kPa")` subia sem `try/except`
    ao redor, `_invalidar_resultado` nunca rodava, e uma exportação
    seguinte gravaria o cálculo do projeto ANTERIOR com a tela já
    mostrando pilar/casos NOVOS. Com a correção, nada é aplicado."""
    from unittest import mock

    app = app_completo
    app.formulario.v_ap.set("0.20")
    app.formulario.v_bp.set("0.50")
    app.formulario.v_sigma_adm.set("200 kPa")   # unidade colada ao número

    caminho = tmp_path / "modelo.xlsx"
    excel_import.gerar_modelo_importacao(str(caminho))   # pilar 0.30x0.30

    with mock.patch("ui.completo.app.filedialog.askopenfilename",
                    return_value=str(caminho)), \
         mock.patch("ui.completo.app.messagebox.showinfo") as mock_info, \
         mock.patch("ui.completo.app.messagebox.showerror") as mock_err:
        app._importar_excel()

    # diálogo de erro apareceu — nunca falhou em silêncio (a exceção NÃO
    # propagou até este teste, que é exatamente o sintoma do defeito: sem
    # a correção, este bloco levantaria ValueError aqui).
    assert mock_err.called
    assert not mock_info.called

    # tela NÃO ficou com estado misto: pilar continua o ORIGINAL (0.20 x
    # 0.50), não o importado (0.30 x 0.30) — tudo-ou-nada.
    assert app.formulario.v_ap.get() == "0.20"
    assert app.formulario.v_bp.get() == "0.50"
    assert app._resultado is None


def test_importar_excel_com_solo_invalido_nao_exporta_calculo_antigo_com_tela_nova(
        app_completo, tmp_path):
    """Reproduz o cenário completo do relatório: calcula um projeto válido,
    corrompe o campo de σ_adm, importa uma planilha com pilar DIFERENTE —
    a exportação seguinte tem de continuar batendo com o que está na tela
    (que não mudou), nunca com uma mistura tela-nova/cálculo-velho."""
    from unittest import mock

    app = app_completo
    app.formulario.v_ap.set("0.20")
    app.formulario.v_bp.set("0.50")
    with mock.patch("ui.completo.app.messagebox.showerror"):
        app._calcular()
    assert app._resultado is not None
    resultado_original = app._resultado
    sapata_original = app._sapata

    app.formulario.v_sigma_adm.set("200 kPa")
    caminho = tmp_path / "modelo.xlsx"
    excel_import.gerar_modelo_importacao(str(caminho))

    with mock.patch("ui.completo.app.filedialog.askopenfilename",
                    return_value=str(caminho)), \
         mock.patch("ui.completo.app.messagebox.showinfo") as mock_info, \
         mock.patch("ui.completo.app.messagebox.showerror") as mock_err:
        app._importar_excel()

    assert mock_err.called
    assert not mock_info.called
    assert app.formulario.v_ap.get() == "0.20"
    assert app.formulario.v_bp.get() == "0.50"
    # nada foi invalidado por engano — a tela continua fiel ao ÚLTIMO
    # cálculo válido, porque nada de fato mudou nela.
    assert app._resultado is resultado_original
    assert app._sapata is sapata_original


# --------------------------------------------------------------------------- #
#  GATE 2, rodada 2 — ALTA #1, rede de segurança: `report_callback_exception`.
# --------------------------------------------------------------------------- #
def test_report_callback_exception_mostra_dialogo_em_vez_de_stderr_mudo(
        app_completo):
    from unittest import mock

    try:
        raise RuntimeError("falha simulada dentro de um callback do Tk")
    except RuntimeError:
        import sys
        exc_tipo, exc_val, exc_tb = sys.exc_info()

    with mock.patch("ui.completo.app.messagebox.showerror") as mock_err:
        app_completo.report_callback_exception(exc_tipo, exc_val, exc_tb)

    assert mock_err.called
    assert "falha simulada" in mock_err.call_args[0][1]


def test_report_callback_exception_esta_instalado_na_janela(app_completo):
    """Confirma que o handler é o método da classe (não o padrão do Tk,
    que só imprime em stderr) — sem isto, qualquer exceção que escape de
    um `try/except` dentro de um comando de menu volta a morrer muda num
    `.exe` com `console=False`."""
    assert (app_completo.report_callback_exception.__func__
            is type(app_completo).report_callback_exception)


# --------------------------------------------------------------------------- #
#  GATE 2, rodada 2 — MEDIA #1: `PainelVisualizacao.limpar` chamado por
#  `_invalidar_resultado`. Cenário (c) do relatório: contagem de itens dos
#  canvases antes/depois de abrir outro projeto.
# --------------------------------------------------------------------------- #
def test_invalidar_resultado_limpa_tambem_o_painel_de_visualizacao(
        app_completo, tmp_path):
    from unittest import mock

    app = app_completo
    app.formulario.v_ap.set("0.20")
    app.formulario.v_bp.set("0.50")
    with mock.patch("ui.completo.app.messagebox.showerror"):
        app._calcular()
    assert app._resultado is not None

    canvases = app.visualizacao._canvases()
    itens_antes = {id(c): len(c.find_all()) for c in canvases}
    assert sum(itens_antes.values()) > 0, (
        "esperava algum item desenhado em algum canvas após calcular — "
        "sem isso o teste não prova nada")

    app._invalidar_resultado("teste de invalidação")

    for c in canvases:
        itens = c.find_all()
        # ou o canvas ficou vazio, ou só tem o(s) item(ns) de TEXTO da
        # mensagem de aviso — nunca sobra desenho da sapata anterior
        # (linha, polígono, etc.).
        for item in itens:
            assert c.type(item) == "text", (
                f"canvas {c} ainda tem item {c.type(item)!r} depois de "
                "limpar() — o desenho da sapata ANTERIOR não foi apagado")
    total_depois = sum(len(c.find_all()) for c in canvases)
    total_antes = sum(itens_antes.values())
    assert total_depois < total_antes, (
        "limpar() não reduziu o total de itens desenhados nos canvases")


def test_abrir_outro_projeto_limpa_visualizacao_end_to_end(app_completo, tmp_path):
    """Mesmo cenário (c), mas pelo fluxo real 'Abrir projeto...' (não só
    chamando `_invalidar_resultado` diretamente)."""
    from unittest import mock

    caminho_a = str(tmp_path / "a.s7proj")
    projeto.salvar_projeto(
        caminho_a, Pilar(ap=0.20, bp=0.50), Solo(sigma_adm=250.0),
        Concreto(fck=25.0), Aco(fyk=500.0), 0.045,
        [CasoCarga("G", Esforcos(N=600.0, Mx=15.0, My=8.0))], OpcoesProjeto())

    app = app_completo
    with mock.patch("ui.completo.app.filedialog.askopenfilename",
                    return_value=caminho_a), \
         mock.patch("ui.completo.app.messagebox.showinfo"), \
         mock.patch("ui.completo.app.messagebox.showerror"):
        app._abrir_projeto()
    with mock.patch("ui.completo.app.messagebox.showerror"):
        app._calcular()
    assert app._resultado is not None

    canvases = app.visualizacao._canvases()
    assert sum(len(c.find_all()) for c in canvases) > 0

    caminho_b = str(tmp_path / "b.s7proj")
    projeto.salvar_projeto(
        caminho_b, Pilar(ap=0.60, bp=0.60), Solo(sigma_adm=120.0),
        Concreto(fck=25.0), Aco(fyk=500.0), 0.045,
        [CasoCarga("G", Esforcos(N=600.0, Mx=15.0, My=8.0))], OpcoesProjeto())
    with mock.patch("ui.completo.app.filedialog.askopenfilename",
                    return_value=caminho_b), \
         mock.patch("ui.completo.app.messagebox.showinfo"), \
         mock.patch("ui.completo.app.messagebox.showerror"):
        app._abrir_projeto()

    for c in canvases:
        for item in c.find_all():
            assert c.type(item) == "text"


# --------------------------------------------------------------------------- #
#  GATE 2, rodada 2 — mutante M4: ordem "valida tudo antes de aplicar" em
#  `_abrir_projeto` (o código já estava certo — conferido à mão pelo a6 —
#  mas nada prendia isso com teste; espelha
#  `test_importar_excel_nao_troca_pilar_se_casos_forem_recusados`, D5).
# --------------------------------------------------------------------------- #
def test_abrir_projeto_nao_troca_pilar_se_casos_forem_recusados(app_completo,
                                                                  tmp_path):
    from unittest import mock

    app = app_completo
    app.formulario.v_ap.set("0.20")
    app.formulario.v_bp.set("0.50")
    app.formulario.v_sigma_adm.set("250")

    dados = {
        "formato": "sapata7-projeto", "versao": 1,
        "pilar": {"ap": 0.90, "bp": 0.90},
        "solo": {"sigma_adm": 500.0},
        "concreto": {"fck": 30.0}, "aco": {"fyk": 500.0},
        "cobrimento": 0.05,
        "casos": [{"nome": "Permanente", "N": 600.0}],
        "opcoes": {},
    }
    caminho = tmp_path / "nome_invalido.s7proj"
    caminho.write_text(json.dumps(dados), encoding="utf-8")

    with mock.patch("ui.completo.app.filedialog.askopenfilename",
                    return_value=str(caminho)), \
         mock.patch("ui.completo.app.messagebox.showinfo"), \
         mock.patch("ui.completo.app.messagebox.showerror") as mock_err:
        app._abrir_projeto()

    assert mock_err.called
    pilar_tela = app.formulario.ler_pilar()
    assert pilar_tela.ap == pytest.approx(0.20)
    assert pilar_tela.bp == pytest.approx(0.50)
    solo_tela = app.formulario.ler_solo()
    assert solo_tela.sigma_adm == pytest.approx(250.0)


# --------------------------------------------------------------------------- #
#  GATE 2, rodada 2 — pedido extra do a6: os 5 handlers de menu, ponta a
#  ponta, com um campo INVÁLIDO em CADA seção da tela por vez. Cenário (g).
# --------------------------------------------------------------------------- #
def test_cinco_handlers_por_cinco_secoes_invalidas_nunca_falham_em_silencio(
        app_completo, tmp_path):
    from unittest import mock

    app = app_completo

    secoes = {
        "pilar": (lambda: app.formulario.v_ap.set("abc"),
                 lambda: app.formulario.v_ap.set("0.20")),
        "solo": (lambda: app.formulario.v_sigma_adm.set("200 kPa"),
                lambda: app.formulario.v_sigma_adm.set("250")),
        "materiais": (lambda: app.formulario.v_fck.set("abc"),
                     lambda: app.formulario.v_fck.set("30")),
        "casos": (lambda: app.formulario.v_G["N"].set("abc"),
                 lambda: app.formulario.v_G["N"].set("600")),
        "opcoes": (lambda: (app.formulario.modo_verificacao.set(True),
                            app.formulario.v_geo_a.set("abc")),
                  lambda: (app.formulario.v_geo_a.set(""),
                          app.formulario.modo_verificacao.set(False))),
    }

    # Handlers que de fato LEEM aquela seção da tela — só nesses cenários um
    # diálogo de ERRO é o resultado esperado. Nos demais, o handler nem
    # toca o campo corrompido (pilar/casos vêm do arquivo/planilha, não da
    # tela) — dar certo mesmo com lixo naquele campo é o comportamento
    # CORRETO; o que este teste proíbe é quebrar em silêncio (exceção sem
    # diálogo nenhum).
    handlers_que_leem = {
        "_salvar_projeto": {"pilar", "solo", "materiais", "casos", "opcoes"},
        "_importar_excel": {"solo"},
        "_abrir_projeto": set(),
        "_gerar_modelo_excel": set(),
        "_exportar_excel": set(),
    }

    caminho_modelo = tmp_path / "modelo.xlsx"
    excel_import.gerar_modelo_importacao(str(caminho_modelo))
    caminho_projeto_valido = tmp_path / "valido.s7proj"
    projeto.salvar_projeto(
        str(caminho_projeto_valido), Pilar(ap=0.3, bp=0.3), Solo(sigma_adm=200.0),
        Concreto(fck=25.0), Aco(fyk=500.0), 0.045,
        [CasoCarga("G", Esforcos(N=400.0))], OpcoesProjeto())

    for nome_secao, (corromper, restaurar) in secoes.items():
        corromper()
        for indice, (nome_handler, secoes_lidas) in enumerate(
                handlers_que_leem.items()):
            saida = tmp_path / f"{nome_secao}_{indice}.saida"
            caminho_abrir = (str(caminho_modelo)
                             if nome_handler == "_importar_excel"
                             else str(caminho_projeto_valido))
            with mock.patch("ui.completo.app.filedialog.asksaveasfilename",
                            return_value=str(saida)), \
                 mock.patch("ui.completo.app.filedialog.askopenfilename",
                            return_value=caminho_abrir), \
                 mock.patch("ui.completo.app.messagebox.showinfo") as mock_info, \
                 mock.patch("ui.completo.app.messagebox.showerror") as mock_err:
                metodo = getattr(app, nome_handler)
                try:
                    metodo()
                except Exception as erro:   # noqa: BLE001 — é o que este teste proíbe
                    pytest.fail(
                        f"{nome_handler}() levantou "
                        f"{type(erro).__name__} sem mostrar diálogo (seção "
                        f"{nome_secao!r} corrompida): {erro}")

            algum_dialogo = mock_info.called or mock_err.called
            assert algum_dialogo, (
                f"{nome_handler}() com {nome_secao!r} corrompida não "
                "mostrou NENHUM diálogo — silêncio total.")
            if nome_secao in secoes_lidas:
                assert mock_err.called, (
                    f"{nome_handler}() lê a seção {nome_secao!r} "
                    "(corrompida), mas não mostrou diálogo de ERRO "
                    f"(showinfo={mock_info.called}).")
        restaurar()
