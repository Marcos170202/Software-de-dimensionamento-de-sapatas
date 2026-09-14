"""Base compartilhada para resultados de verificação normativa —
módulo privado (não faz parte da API pública de
``estrutura_metalica.normative.nbr8800``).

Toda verificação da NBR 8800 segue o mesmo padrão "solicitante <=
resistente" (tração 5.2.1.2, compressão 5.3.1, e as fases futuras
desta mesma norma) — fatorado aqui para não duplicar a mesma lógica de
``utilization``/``is_ok`` em cada novo ``*CheckResult``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class CheckResult(ABC):
    """Contrato comum: um resultado de verificação normativa expõe um
    esforço solicitante (``sd``) e um esforço resistente (``rd``), dos
    quais ``utilization`` e ``is_ok`` são sempre derivados da mesma
    forma (``sd/rd`` e ``sd <= rd``)."""

    __slots__ = ()

    @property
    @abstractmethod
    def sd(self) -> float:
        """Esforço solicitante de cálculo (ex.: ``Nt,Sd``, ``Nc,Sd``)."""
        raise NotImplementedError  # pragma: no cover

    @property
    @abstractmethod
    def rd(self) -> float:
        """Esforço resistente de cálculo (ex.: ``Nt,Rd``, ``Nc,Rd``)."""
        raise NotImplementedError  # pragma: no cover

    @property
    def utilization(self) -> float:
        """Taxa de utilização (``sd/rd`` — ``<=1`` significa que a
        condição de dimensionamento é atendida)."""
        return self.sd / self.rd

    @property
    def is_ok(self) -> bool:
        """Condição de dimensionamento genérica: ``sd <= rd``."""
        return self.sd <= self.rd
