"""
visualizacao.py
----------------
Coluna central: as quatro abas de desenho. Todo o desenho vem pronto do
núcleo (`calc_core.sapata_isolada.visual2d`/`visual3d`/`visual3d_momentos`);
este módulo só instancia os widgets, alimenta com `definir_modelo`/`definir`
e liga os botões de vista/camada aos métodos que esses widgets já expõem
(`vista`, `alternar`, `definir_direcao`). Nenhum desenho é recalculado aqui.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from calc_core.sapata_isolada.momentos import (
    CampoMomentos,
    campo_de_grelha,
    campo_momentos,
)
from calc_core.sapata_isolada.sapata import ResultadoSapata, Sapata
from calc_core.sapata_isolada.visual2d import MapaMomentos, PerfilCortes, ReacaoSolo
from calc_core.sapata_isolada.visual3d import Visualizador3D
from calc_core.sapata_isolada.visual3d_momentos import SuperficieMomentos3D
from calc_core.sapata_isolada.visual3d_tensoes import (
    GradeTensoes,
    SuperficieTensoes3D,
    grade_de_campo_momentos,
    grade_de_grelha,
)

from . import tema


def _barra_ferramentas(pai: ttk.Frame) -> ttk.Frame:
    barra = ttk.Frame(pai, style="Painel.TFrame")
    barra.pack(side="top", fill="x", padx=4, pady=(4, 2))
    return barra


def _canvas(pai: ttk.Frame) -> tk.Canvas:
    c = tk.Canvas(pai, bg=tema.FUNDO, highlightthickness=0)
    c.pack(side="top", fill="both", expand=True, padx=4, pady=(0, 4))
    return c


class AbaModelo3D(ttk.Frame):
    """Aba 'Modelo 3D': `Visualizador3D` sobre um Canvas orbitável."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, style="Painel.TFrame")
        barra = _barra_ferramentas(self)
        for rotulo, nome in (("ISO", "iso"), ("Corte X", "frente"),
                             ("Corte Y", "lado"), ("Planta", "topo")):
            ttk.Button(barra, text=rotulo,
                       command=lambda n=nome: self.visualizador.vista(n)).pack(
                side="left", padx=2)
        ttk.Separator(barra, orient="vertical").pack(side="left", fill="y",
                                                       padx=6)
        self.v_solo = tk.BooleanVar(value=True)
        self.v_armaduras = tk.BooleanVar(value=True)
        self.v_cotas = tk.BooleanVar(value=True)
        ttk.Checkbutton(barra, text="Substrato", variable=self.v_solo,
                        command=lambda: self.visualizador.alternar(
                            "solo", self.v_solo.get())).pack(side="left", padx=4)
        ttk.Checkbutton(barra, text="Armaduras", variable=self.v_armaduras,
                        command=lambda: self.visualizador.alternar(
                            "armaduras", self.v_armaduras.get())).pack(
            side="left", padx=4)
        ttk.Checkbutton(barra, text="Cotas", variable=self.v_cotas,
                        command=lambda: self.visualizador.alternar(
                            "cotas", self.v_cotas.get())).pack(side="left", padx=4)

        canvas = _canvas(self)
        self.visualizador = Visualizador3D(canvas)

    def atualizar(self, modelo: dict) -> None:
        self.visualizador.definir_modelo(modelo)


class AbaMomentos(ttk.Frame):
    """
    Aba 'Momentos': sub-abas com o mapa de isovalores em planta (2D) e a
    superfície tridimensional do mesmo campo — o engenheiro escolhe a
    leitura que preferir, ambas vêm do mesmo `CampoMomentos`.
    """

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, style="Painel.TFrame")
        sub = ttk.Notebook(self)
        sub.pack(fill="both", expand=True)

        aba2d = ttk.Frame(sub, style="Painel.TFrame")
        aba3d = ttk.Frame(sub, style="Painel.TFrame")
        sub.add(aba2d, text="Mapa 2D")
        sub.add(aba3d, text="Superfície 3D")

        barra2d = _barra_ferramentas(aba2d)
        ttk.Button(barra2d, text="Direção X",
                   command=lambda: self._mudar_direcao_2d("X")).pack(
            side="left", padx=2)
        ttk.Button(barra2d, text="Direção Y",
                   command=lambda: self._mudar_direcao_2d("Y")).pack(
            side="left", padx=2)
        ttk.Separator(barra2d, orient="vertical").pack(side="left", fill="y",
                                                          padx=6)
        self.v_isolinhas = tk.BooleanVar(value=True)
        self.v_grade = tk.BooleanVar(value=False)
        ttk.Checkbutton(barra2d, text="Isolinhas", variable=self.v_isolinhas,
                        command=lambda: self.mapa2d.alternar(
                            "mostrar_isolinhas", self.v_isolinhas.get())).pack(
            side="left", padx=4)
        ttk.Checkbutton(barra2d, text="Grade", variable=self.v_grade,
                        command=lambda: self.mapa2d.alternar(
                            "mostrar_grade", self.v_grade.get())).pack(
            side="left", padx=4)
        ttk.Separator(barra2d, orient="vertical").pack(side="left", fill="y",
                                                          padx=6)
        ttk.Button(barra2d, text="Analítico",
                   command=lambda: self.mapa2d.definir_fonte("analitico")).pack(
            side="left", padx=2)
        ttk.Button(barra2d, text="Grelha",
                   command=lambda: self.mapa2d.definir_fonte("grelha")).pack(
            side="left", padx=2)
        canvas2d = _canvas(aba2d)
        self.mapa2d = MapaMomentos(canvas2d)

        barra3d = _barra_ferramentas(aba3d)
        ttk.Button(barra3d, text="Direção X",
                   command=lambda: self._mudar_direcao_3d("X")).pack(
            side="left", padx=2)
        ttk.Button(barra3d, text="Direção Y",
                   command=lambda: self._mudar_direcao_3d("Y")).pack(
            side="left", padx=2)
        ttk.Separator(barra3d, orient="vertical").pack(side="left", fill="y",
                                                          padx=6)
        ttk.Button(barra3d, text="Grelha",
                   command=lambda: self.superficie3d.definir_modo("grelha")).pack(
            side="left", padx=2)
        ttk.Button(barra3d, text="Superfície",
                   command=lambda: self.superficie3d.definir_modo(
                       "superficie")).pack(side="left", padx=2)
        ttk.Separator(barra3d, orient="vertical").pack(side="left", fill="y",
                                                          padx=6)
        for rotulo, nome in (("ISO", "iso"), ("Frente", "frente"),
                             ("Lado", "lado"), ("Topo", "topo")):
            ttk.Button(barra3d, text=rotulo,
                       command=lambda n=nome: self.superficie3d.vista(n)).pack(
                side="left", padx=2)
        canvas3d = _canvas(aba3d)
        self.superficie3d = SuperficieMomentos3D(canvas3d)

        self._campo: CampoMomentos | None = None
        self._geometria: dict = {}

    def _mudar_direcao_2d(self, direcao: str) -> None:
        self.mapa2d.definir_direcao(direcao)

    def _mudar_direcao_3d(self, direcao: str) -> None:
        self.superficie3d.definir_direcao(direcao)

    def atualizar(self, sapata: Sapata, res: ResultadoSapata, modelo: dict,
                 campo: CampoMomentos | None,
                 campo_grelha: CampoMomentos | None) -> None:
        """
        `campo`/`campo_grelha` já vêm prontos de `_campos_momento()`
        (montada uma única vez por `PainelVisualizacao.atualizar`) — a aba
        Reação do solo consome os mesmos dois campos para a superfície de
        tensões, e recalcular `campo_momentos()` aqui duplicaria trabalho.
        """
        self._campo = campo
        self._geometria = modelo

        # Fonte padrão: quando a sapata é FLEXÍVEL a hipótese de placa rígida
        # do campo analítico não vale — ver 22.6.3. O modo "Grelha" do 3D já
        # é o padrão da aba e já usa o campo real; aqui é o Mapa 2D e o modo
        # "Superfície" do 3D que precisam saber a classificação.
        if campo is not None:
            self.mapa2d.definir(campo, campo_grelha, res.rigida)

        self.superficie3d.definir(campo, campo_grelha, modelo, res.rigida)


class AbaReacaoSolo(ttk.Frame):
    """
    Aba 'Reação do solo': sub-abas com o corte 2D (modelo rígido x
    discretizado, por direção) e a superfície tridimensional de tensão de
    contato — mesmo padrão de `AbaMomentos` ('Mapa 2D'/'Superfície 3D').
    """

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, style="Painel.TFrame")
        sub = ttk.Notebook(self)
        sub.pack(fill="both", expand=True)

        aba2d = ttk.Frame(sub, style="Painel.TFrame")
        aba3d = ttk.Frame(sub, style="Painel.TFrame")
        sub.add(aba2d, text="Corte 2D")
        sub.add(aba3d, text="Superfície 3D")

        barra2d = _barra_ferramentas(aba2d)
        ttk.Button(barra2d, text="Direção X",
                   command=lambda: self._mudar_direcao("X")).pack(side="left",
                                                                    padx=2)
        ttk.Button(barra2d, text="Direção Y",
                   command=lambda: self._mudar_direcao("Y")).pack(side="left",
                                                                    padx=2)
        canvas2d = _canvas(aba2d)
        self.painel = ReacaoSolo(canvas2d)

        barra3d = _barra_ferramentas(aba3d)
        ttk.Button(barra3d, text="Analítico",
                   command=lambda: self.superficie3d.definir_fonte(
                       "analitico")).pack(side="left", padx=2)
        ttk.Button(barra3d, text="Grelha",
                   command=lambda: self.superficie3d.definir_fonte(
                       "grelha")).pack(side="left", padx=2)
        ttk.Separator(barra3d, orient="vertical").pack(side="left", fill="y",
                                                          padx=6)
        for rotulo, nome in (("ISO", "iso"), ("Frente", "frente"),
                             ("Lado", "lado"), ("Topo", "topo")):
            ttk.Button(barra3d, text=rotulo,
                       command=lambda n=nome: self.superficie3d.vista(n)).pack(
                side="left", padx=2)
        canvas3d = _canvas(aba3d)
        self.superficie3d = SuperficieTensoes3D(canvas3d)

    def _mudar_direcao(self, direcao: str) -> None:
        self.painel.definir_direcao(direcao)

    def atualizar(self, res: ResultadoSapata, modelo: dict,
                 campo: CampoMomentos | None) -> None:
        self.painel.definir(res.reacoes, res.classificacao, modelo)

        grade_analitica: GradeTensoes | None = None
        if campo is not None:
            grade_analitica = grade_de_campo_momentos(campo)
        grade_grelha: GradeTensoes | None = None
        if res.grelha is not None:
            grade_grelha = grade_de_grelha(res.grelha, res.grelha.ap,
                                           res.grelha.bp)
        self.superficie3d.definir(grade_analitica, grade_grelha, modelo,
                                  res.rigida)


class AbaPerfilGeologico(ttk.Frame):
    """Aba 'Perfil geológico': cortes com estratigrafia e bulbo de Boussinesq."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, style="Painel.TFrame")
        barra = _barra_ferramentas(self)
        ttk.Button(barra, text="Corte X",
                   command=lambda: self._mudar_direcao("X")).pack(side="left",
                                                                    padx=2)
        ttk.Button(barra, text="Corte Y",
                   command=lambda: self._mudar_direcao("Y")).pack(side="left",
                                                                    padx=2)
        ttk.Separator(barra, orient="vertical").pack(side="left", fill="y",
                                                        padx=6)
        self.v_bulbo = tk.BooleanVar(value=True)
        ttk.Checkbutton(barra, text="Bulbo de tensões", variable=self.v_bulbo,
                        command=lambda: self.painel.alternar(
                            "mostrar_bulbo", self.v_bulbo.get())).pack(
            side="left", padx=4)
        canvas = _canvas(self)
        self.painel = PerfilCortes(canvas)

    def _mudar_direcao(self, direcao: str) -> None:
        self.painel.definir_direcao(direcao)

    def atualizar(self, modelo: dict) -> None:
        self.painel.definir_modelo(modelo)


class PainelVisualizacao(ttk.Notebook):
    """Coluna central: as quatro abas de desenho."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.aba_3d = AbaModelo3D(self)
        self.aba_momentos = AbaMomentos(self)
        self.aba_reacao = AbaReacaoSolo(self)
        self.aba_perfil = AbaPerfilGeologico(self)
        self.add(self.aba_3d, text="Modelo 3D")
        self.add(self.aba_momentos, text="Momentos")
        self.add(self.aba_reacao, text="Reação do solo")
        self.add(self.aba_perfil, text="Perfil geológico")

    def atualizar(self, sapata: Sapata, res: ResultadoSapata, modelo: dict) -> None:
        self.aba_3d.atualizar(modelo)
        campo, campo_grelha = _campos_momento(sapata, res)
        self.aba_momentos.atualizar(sapata, res, modelo, campo, campo_grelha)
        self.aba_reacao.atualizar(res, modelo, campo)
        self.aba_perfil.atualizar(modelo)


def _campos_momento(sapata: Sapata, res: ResultadoSapata
                    ) -> tuple[CampoMomentos | None, CampoMomentos | None]:
    """
    Monta os dois campos de momento (analítico e grelha) uma única vez por
    atualização. `AbaMomentos` os consome diretamente; `AbaReacaoSolo` deriva
    a grade de tensões dos mesmos campos (`campo.sigma`/`res.grelha.pressao`,
    via `grade_de_campo_momentos`/`grade_de_grelha`) — assim `campo_momentos()`
    não é recalculado por aba.
    """
    try:
        campo = campo_momentos(sapata, res)
    except Exception:   # noqa: BLE001 — abas ficam vazias, não trava a UI
        campo = None

    campo_grelha = None
    if res.grelha is not None:
        md = {ar.direcao: ar.Md for ar in res.armaduras}
        try:
            campo_grelha = campo_de_grelha(
                res.grelha, md.get("X", 0.0), md.get("Y", 0.0),
                "ELU governante (grelha)")
        except Exception:   # noqa: BLE001 — cai no fallback analítico
            campo_grelha = None

    return campo, campo_grelha
