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

from calc_core.sapata_isolada.momentos import CampoMomentos, campo_momentos
from calc_core.sapata_isolada.sapata import ResultadoSapata, Sapata
from calc_core.sapata_isolada.visual2d import MapaMomentos, PerfilCortes, ReacaoSolo
from calc_core.sapata_isolada.visual3d import Visualizador3D
from calc_core.sapata_isolada.visual3d_momentos import SuperficieMomentos3D

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

    def atualizar(self, sapata: Sapata, res: ResultadoSapata, modelo: dict) -> None:
        try:
            campo = campo_momentos(sapata, res)
        except Exception:   # noqa: BLE001 — mapa fica vazio, não trava a UI
            campo = None
        self._campo = campo
        self._geometria = modelo
        if campo is not None:
            self.mapa2d.definir_campo(campo)
            self.superficie3d.definir(campo, modelo)


class AbaReacaoSolo(ttk.Frame):
    """Aba 'Reação do solo': modelo rígido x discretizado, por direção."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, style="Painel.TFrame")
        barra = _barra_ferramentas(self)
        ttk.Button(barra, text="Direção X",
                   command=lambda: self._mudar_direcao("X")).pack(side="left",
                                                                    padx=2)
        ttk.Button(barra, text="Direção Y",
                   command=lambda: self._mudar_direcao("Y")).pack(side="left",
                                                                    padx=2)
        canvas = _canvas(self)
        self.painel = ReacaoSolo(canvas)

    def _mudar_direcao(self, direcao: str) -> None:
        self.painel.definir_direcao(direcao)

    def atualizar(self, res: ResultadoSapata, modelo: dict) -> None:
        self.painel.definir(res.reacoes, res.classificacao, modelo)


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
        self.aba_momentos.atualizar(sapata, res, modelo)
        self.aba_reacao.atualizar(res, modelo)
        self.aba_perfil.atualizar(modelo)
