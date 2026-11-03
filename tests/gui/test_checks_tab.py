"""Testes (offscreen) da aba Verificações NBR 8800."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from estrutura_metalica.analysis import (
    AnalysisResult,
    LoadCase,
    NodalLoad,
    StructuralModel,
    Support,
    solve,
)
from estrutura_metalica.gui.checks_tab import ChecksTab, check_member_axial
from estrutura_metalica.model import ASTM_A992, Beam, Connection, ConnectionType, Node
from estrutura_metalica.model.steel_profile_catalog import GERDAU_W_H_PROFILES

_SECTION = GERDAU_W_H_PROFILES["W150x13.0"]


def _cantilever(load: NodalLoad) -> tuple[StructuralModel, Beam, AnalysisResult]:
    n1 = Node(id=1, x=0.0, y=0.0, z=0.0)
    n2 = Node(id=2, x=3.0, y=0.0, z=0.0)
    beam = Beam(id=1, start_node_id=1, end_node_id=2, section=_SECTION, material=ASTM_A992)
    model = StructuralModel(nodes={1: n1, 2: n2}, members=(beam,), supports=(Support.fixed(1),))
    result = solve(model, LoadCase(name="c", loads=(load,)))
    return model, beam, result


class TestCheckMemberAxial:
    def test_tension_reports_governing_and_is_ok(self) -> None:
        model, beam, result = _cantilever(NodalLoad(node_id=2, fx=1000.0))
        summary = check_member_axial(model, beam, result)
        assert summary.governing == "tração"
        assert summary.axial > 0.0
        assert summary.is_ok

    def test_tension_reports_not_ok_when_force_exceeds_capacity(self) -> None:
        huge_force = _SECTION.area * ASTM_A992.fy * 100.0
        model, beam, result = _cantilever(NodalLoad(node_id=2, fx=huge_force))
        summary = check_member_axial(model, beam, result)
        assert summary.governing == "tração"
        assert not summary.is_ok

    def test_compression_reports_governing(self) -> None:
        model, beam, result = _cantilever(NodalLoad(node_id=2, fx=-1000.0))
        summary = check_member_axial(model, beam, result)
        assert summary.governing == "compressão"
        assert summary.axial < 0.0


class TestChecksTab:
    def test_update_from_populates_table(self, qapp: QApplication) -> None:
        model, _beam, result = _cantilever(NodalLoad(node_id=2, fx=1000.0))
        tab = ChecksTab()
        tab.update_from(model, result)
        assert tab.table.rowCount() == 1
        assert "verificado" in tab.status_label.text()

    def test_update_from_reports_error_for_unsupported_connection(self, qapp: QApplication) -> None:
        """Ligação semirrígida não é suportada pela recuperação de
        esforços internos (mesma limitação de
        ``estrutura_metalica.analysis.stiffness``) — o modelo aqui é
        montado à mão (sem passar por ``solve()``, que já rejeitaria
        um elemento semirrígido antes de chegar a esta aba) só para
        exercitar o tratamento defensivo de erro por elemento em
        ``ChecksTab.update_from``."""
        n1 = Node(id=1, x=0.0, y=0.0, z=0.0)
        n2 = Node(id=2, x=3.0, y=0.0, z=0.0)
        semi_rigid = Connection(ConnectionType.SEMI_RIGID, rotational_stiffness=1000.0)
        beam = Beam(
            id=1,
            start_node_id=1,
            end_node_id=2,
            section=_SECTION,
            material=ASTM_A992,
            start_connection=semi_rigid,
        )
        model = StructuralModel(nodes={1: n1, 2: n2}, members=(beam,), supports=(Support.fixed(1),))
        fabricated_result = AnalysisResult(
            displacements={1: (0.0,) * 6, 2: (0.0,) * 6}, reactions={1: (0.0,) * 6}
        )

        tab = ChecksTab()
        tab.update_from(model, fabricated_result)

        assert tab.table.rowCount() == 0
        assert tab.status_label.text().startswith("Erro(s):")
