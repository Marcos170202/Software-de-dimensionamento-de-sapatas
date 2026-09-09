"""
projecao.py
-----------
Câmera em perspectiva e controle orbital, compartilhados por todos os
visualizadores tridimensionais do pacote.

Fica num módulo só para que a matemática de projeção exista em um único lugar:
duplicar fórmula entre desenhos já custou caro antes.

Convenção de eixos: x e y no plano horizontal, z para cima.
"""
from __future__ import annotations

import math
from typing import Callable, Sequence


def projetar(p: Sequence[float], alvo: Sequence[float], yaw: float, pitch: float,
             dist: float, focal: float, W: float, H: float
             ) -> tuple[float, float, float]:
    """
    Projeta um ponto do mundo na tela. Devolve (x_tela, y_tela, profundidade);
    profundidade <= 0 significa atrás da câmera.
    """
    x = p[0] - alvo[0]
    y = p[1] - alvo[1]
    z = p[2] - alvo[2]
    cy, sy = math.cos(yaw), math.sin(yaw)
    X = x * cy - y * sy
    Yr = x * sy + y * cy
    cp, sp = math.cos(pitch), math.sin(pitch)
    D = Yr * cp + z * sp + dist
    U = -Yr * sp + z * cp
    f = focal / max(D, 0.08)
    return (W / 2 + X * f, H / 2 - U * f, D)


def distancia_enquadramento(extensao: float, focal: float, W: float, H: float,
                            fracao: float = 0.92) -> float:
    """Distância da câmera para que `extensao` ocupe `fracao` da menor dimensão."""
    return extensao * focal / (fracao * max(min(W, H), 1.0))


class ControleOrbital:
    """Liga arrastar-para-girar e roda-para-aproximar a um canvas do Tkinter."""

    def __init__(self, canvas, camera, ao_girar: Callable[[], None],
                 ao_aproximar: Callable[[], None] | None = None) -> None:
        self.canvas = canvas
        self.cam = camera
        self.ao_girar = ao_girar
        self.ao_aproximar = ao_aproximar or ao_girar
        self._arrastando = False
        self._px = self._py = 0
        self._pendente = False      # há um quadro a redesenhar?

        canvas.bind("<ButtonPress-1>", self._pressionar)
        canvas.bind("<B1-Motion>", self._mover)
        canvas.bind("<ButtonRelease-1>", self._soltar)
        canvas.bind("<MouseWheel>", self._roda)              # Windows / macOS
        canvas.bind("<Button-4>", lambda e: self._zoom(-1))  # Linux
        canvas.bind("<Button-5>", lambda e: self._zoom(1))

    def _pressionar(self, e):
        self._arrastando = True
        self._px, self._py = e.x, e.y

    def _mover(self, e):
        if not self._arrastando:
            return
        self.cam.yaw += (e.x - self._px) * 0.010
        self.cam.pitch = max(-0.25, min(1.45,
                                        self.cam.pitch + (e.y - self._py) * 0.008))
        self._px, self._py = e.x, e.y
        self._agendar()

    def _agendar(self):
        """
        Descarta quadros intermediários: eventos de movimento chegam muito mais
        rápido do que o canvas consegue redesenhar, e processar todos deixa a
        interface emborrachada. Só um redesenho fica pendente por vez.
        """
        if self._pendente:
            return
        self._pendente = True
        self.canvas.after_idle(self._executar)

    def _executar(self):
        self._pendente = False
        self.ao_girar()

    def _soltar(self, _e):
        self._arrastando = False

    def _roda(self, e):
        self._zoom(-1 if e.delta > 0 else 1)

    def _zoom(self, sentido):
        self.cam.dist = max(1.0, min(400.0,
                                     self.cam.dist * (1 + sentido * 0.11)))
        if self._pendente:
            return
        self._pendente = True
        self.canvas.after_idle(lambda: (setattr(self, "_pendente", False),
                                        self.ao_aproximar()))


class Camera:
    """Estado da câmera orbital."""

    def __init__(self, yaw: float = -1.06, pitch: float = 0.34,
                 dist: float = 14.0, alvo: Sequence[float] = (0.0, 0.0, 0.0),
                 focal: float = 900.0) -> None:
        self.yaw = yaw
        self.pitch = pitch
        self.dist = dist
        self.alvo = list(alvo)
        self.focal = focal

    def projetar(self, p, W, H):
        return projetar(p, self.alvo, self.yaw, self.pitch, self.dist,
                        self.focal, W, H)
