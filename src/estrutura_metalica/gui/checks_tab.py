"""Aba "Verificações NBR 8800" — verificação axial (tração ou
compressão) de cada elemento do modelo, a partir do último resultado
de análise da aba Modelo.

Ver ``PROCESSO_MODELAGEM_METALICA.md`` e
``docs/adr/ADR-001-gui-stack-e-empacotamento.md``.

**ATENÇÃO — LIMITAÇÕES DESTE INCREMENTO**:

1. **Escopo normativo**: só a força axial (5.2 tração / 5.3 compressão)
   e o índice de esbeltez recomendado (5.2.8/5.3.7). Cisalhamento
   (5.4.3), flexão (5.4.2/Anexo D) e a interação axial+flexão
   (5.5.1.2) exigem geometria de mesa/alma que só existe em
   :class:`~estrutura_metalica.model.IProfileSection` — não nos
   perfis tubulares Vallourec também oferecidos na aba Modelo — e
   ficam para um incremento futuro que trate os dois grupos de seção
   separadamente (ver ATENÇÃO 1 em ``model_tab``).
2. **Comprimento destravado (KL)**: usa o comprimento geométrico do
   próprio elemento com ``K=1,0`` para os dois eixos principais e para
   torção — não há ainda entrada de usuário para comprimento
   destravado distinto do comprimento geométrico nem para o fator de
   comprimento efetivo ``K`` (NBR 8800:2024, 4.10, fora do escopo
   desta fase). Isso pode SUPERESTIMAR a esbeltez (resultado
   conservador, não inseguro) para barras travadas lateralmente em
   pontos intermediários, e SUBESTIMAR para barras com ``K`` real > 1
   sem travamento (ex.: pilar em balanço) — o usuário deve interpretar
   os resultados sabendo disso.
3. **Classe de combinação**: sempre
   :attr:`~estrutura_metalica.normative.nbr8800.LoadCombinationClass.NORMAL`
   (``γa1=1,10``, ``γa2=1,35``) — não há seleção de classe de
   combinação nem ponderação de cargas nesta aba, consistente com a
   ATENÇÃO 4 de ``model_tab`` (as cargas lançadas já são tratadas como
   valores de cálculo).
4. **``Ne = min(Nex, Ney, Nez)``** (NBR 8800:2024, 5.3.5.1) só é válida
   para seções com dupla simetria ou simétricas em relação a um ponto
   — ver ATENÇÃO em
   ``estrutura_metalica.normative.nbr8800.compression``. É SEGURA para
   todos os catálogos oferecidos na aba Modelo (Gerdau W/H, British
   Steel UB/UC — perfis I duplamente simétricos — e os três perfis
   tubulares Vallourec, também duplamente simétricos); se um futuro
   incremento adicionar um catálogo monossimétrico ou assimétrico
   (perfis U, T, cantoneiras) a esta aba, este cálculo de compressão
   deixa de ser válido e precisa ser revisto antes.
5. **Constante de empenamento (``Cw``)**: quando ``section.cw`` é
   ``None`` (catálogos Vallourec de perfis tubulares fechados),
   tratado como ``0,0`` — valor correto para seções fechadas/
   tubulares sem empenamento (ver docstring de
   ``torsional_buckling_force``), não uma aproximação para esses
   catálogos especificamente.
6. **Área efetiva/líquida**: sempre igual à área bruta (nenhuma
   flambagem local nem furo de ligação considerados) — mesma
   simplificação documentada em
   ``effective_area_without_local_buckling``/``net_area_without_holes``,
   não uma simplificação nova introduzida por esta aba.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from estrutura_metalica.analysis import AnalysisResult, StructuralModel, member_internal_forces
from estrutura_metalica.model import Member
from estrutura_metalica.normative.nbr8800 import (
    LoadCombinationClass,
    check_compression_member,
    check_compression_slenderness,
    check_tension_member,
    check_tension_slenderness,
    effective_area_without_local_buckling,
    flexural_buckling_force,
    net_area_without_holes,
    polar_radius_of_gyration,
    steel_resistance_factors,
    torsional_buckling_force,
)

_RESISTANCE_FACTORS = steel_resistance_factors(LoadCombinationClass.NORMAL)

_HEADERS = (
    "Elemento",
    "Tipo",
    "Nsd (N)",
    "Verificação",
    "Utilização (Sd/Rd)",
    "Esbeltez (KL/r | limite)",
    "Situação",
)


@dataclass(frozen=True, slots=True)
class MemberAxialCheckSummary:
    """Resultado resumido da verificação axial (tração ou compressão)
    de um elemento — ver ATENÇÃO no docstring do módulo."""

    member_id: int
    axial: float
    governing: str
    """``"tração"`` ou ``"compressão"``."""
    utilization: float
    slenderness_ratio: float
    slenderness_limit: float
    is_ok: bool


def _radii_of_gyration(member: Member) -> tuple[float, float]:
    area = member.section.area
    rx = (member.section.ix / area) ** 0.5
    ry = (member.section.iy / area) ** 0.5
    return rx, ry


def _elastic_buckling_force(member: Member, length: float) -> float:
    """``Ne = min(Nex, Ney, Nez)`` — ver ATENÇÃO 4 no docstring do
    módulo sobre a validade desta fórmula ficar restrita a seções com
    dupla simetria ou simétricas em relação a um ponto."""
    e = member.material.e
    g = member.material.shear_modulus
    rx, ry = _radii_of_gyration(member)
    nex = flexural_buckling_force(e, member.section.ix, length)
    ney = flexural_buckling_force(e, member.section.iy, length)
    r0 = polar_radius_of_gyration(rx, ry)
    cw = member.section.cw if member.section.cw is not None else 0.0
    nez = torsional_buckling_force(e, g, cw, member.section.j, r0, length)
    return min(nex, ney, nez)


def check_member_axial(
    model: StructuralModel, member: Member, result: AnalysisResult
) -> MemberAxialCheckSummary:
    """Verifica a força axial do elemento — tração (5.2) se
    ``Nsd >= 0``, compressão (5.3) caso contrário — e o índice de
    esbeltez recomendado correspondente (5.2.8/5.3.7). Ver ATENÇÃO no
    docstring do módulo para as simplificações desta fase."""
    forces = member_internal_forces(model, member, result)
    start = model.nodes[member.start_node_id]
    end = model.nodes[member.end_node_id]
    length = start.distance_to(end)
    area = member.section.area
    rx, ry = _radii_of_gyration(member)

    if forces.axial >= 0.0:
        tension_check = check_tension_member(
            nt_sd=forces.axial,
            gross_area=area,
            effective_net_area=net_area_without_holes(area),
            fy=member.material.fy,
            fu=member.material.fu,
            resistance_factors=_RESISTANCE_FACTORS,
        )
        slenderness = check_tension_slenderness(length, rx, length, ry)
        return MemberAxialCheckSummary(
            member_id=member.id,
            axial=forces.axial,
            governing="tração",
            utilization=tension_check.utilization,
            slenderness_ratio=slenderness.ratio,
            slenderness_limit=slenderness.limit,
            is_ok=tension_check.is_ok,
        )

    elastic_buckling_force = _elastic_buckling_force(member, length)
    compression_check = check_compression_member(
        nc_sd=-forces.axial,
        gross_area=area,
        effective_area=effective_area_without_local_buckling(area),
        fy=member.material.fy,
        elastic_buckling_force=elastic_buckling_force,
        resistance_factors=_RESISTANCE_FACTORS,
    )
    slenderness = check_compression_slenderness(length, rx, length, ry)
    return MemberAxialCheckSummary(
        member_id=member.id,
        axial=forces.axial,
        governing="compressão",
        utilization=compression_check.utilization,
        slenderness_ratio=slenderness.ratio,
        slenderness_limit=slenderness.limit,
        is_ok=compression_check.is_ok,
    )


class ChecksTab(QWidget):
    """Aba "Verificações NBR 8800": tabela com a verificação axial de
    cada elemento do modelo, recalculada a cada análise bem-sucedida
    da aba Modelo (ver ``ModelTab.analysis_completed``/
    ``MainWindow``). Ver ATENÇÃO no docstring do módulo para o escopo
    desta fase."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.status_label = QLabel("Rode a análise na aba Modelo para ver as verificações.")

        self.table = QTableWidget(0, len(_HEADERS), self)
        self.table.setHorizontalHeaderLabels(list(_HEADERS))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table)

    def update_from(self, model: StructuralModel, result: AnalysisResult) -> None:
        """Recalcula e mostra a verificação axial de todos os
        elementos do modelo."""
        self.table.setRowCount(0)
        errors: list[str] = []
        for member in model.members:
            try:
                summary = check_member_axial(model, member, result)
            except (ValueError, NotImplementedError) as error:
                errors.append(f"Elemento {member.id}: {error}")
                continue
            self._add_row(member, summary)

        if errors:
            self.status_label.setText("Erro(s): " + " | ".join(errors))
        else:
            self.status_label.setText(f"{len(model.members)} elemento(s) verificado(s).")

    def _add_row(self, member: Member, summary: MemberAxialCheckSummary) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(str(summary.member_id)))
        self.table.setItem(row, 1, QTableWidgetItem(type(member).__name__))
        self.table.setItem(row, 2, QTableWidgetItem(f"{summary.axial:.6g}"))
        self.table.setItem(row, 3, QTableWidgetItem(summary.governing))
        self.table.setItem(row, 4, QTableWidgetItem(f"{summary.utilization:.3f}"))
        self.table.setItem(
            row,
            5,
            QTableWidgetItem(f"{summary.slenderness_ratio:.1f} / {summary.slenderness_limit:.0f}"),
        )
        self.table.setItem(row, 6, QTableWidgetItem("OK" if summary.is_ok else "REPROVADO"))


__all__ = ["ChecksTab", "MemberAxialCheckSummary", "check_member_axial"]
