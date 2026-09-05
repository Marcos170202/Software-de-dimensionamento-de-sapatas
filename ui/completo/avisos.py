"""
avisos.py
---------
Texto do aviso de escopo (banner da tela + memorial) — extraído de `app.py`
para um módulo SEM dependência de `tkinter`, para que `excel_export.py`
(e qualquer outro exportador que não precise de widget algum) possa
importar o mesmo texto sem arrastar `tkinter` como dependência.

Defeito corrigido (D10 do GATE 2, rodada 1): a aba "Resumo" do relatório
Excel não trazia este aviso, apesar de a planilha existir justamente para
circular FORA da tela que mostra o banner (copiar/colar em outro
documento) — ver `ruleset.yaml`, "A interface e o memorial devem deixar
isso visível: em conferência não é aprovado". O memorial em PDF tem a
MESMA lacuna hoje (`calc_core.sapata_isolada.pranchas`/`relatorio`); não é
regressão desta correção, mas segue pendente — ver ruleset.yaml.
"""
from __future__ import annotations

AVISO_BANNER = (
    "ESCOPO AMPLO — PARCIALMENTE EM CONFERÊNCIA. Materiais, ancoragem, "
    "cisalhamento e punção foram auditados item a item contra a NBR 6118 "
    "(ver ruleset.yaml). Geotecnia sob carga excêntrica, bielas e tirantes, "
    "rigidez/grelha, recalques e MEF do solo ainda NÃO foram auditados — "
    "reveja com um engenheiro antes de qualquer uso profissional. "
    "Ajuda ▸ Sobre o escopo para o texto completo."
)

AVISO_ESCOPO_COMPLETO = (
    "ESCOPO AMPLO — PARCIALMENTE EM CONFERÊNCIA.\n\n"
    "Materiais (NBR 6118 §8), ancoragem (§9.3-9.4), cisalhamento (§19.4) e "
    "punção (§19.5) foram auditados item a item contra o texto da norma por "
    "leitura visual das páginas, com 6 defeitos corrigidos (2 do lado "
    "inseguro) — ver relatorios/revisao_codigo.md, adendo.\n\n"
    "A geotecnia sob excentricidade dupla, o modelo de bielas e tirantes de "
    "Blévot, a rigidez/grelha sobre base elástica de Winkler, os recalques "
    "(Schmertmann/Terzaghi) e o MEF do solo foram PORTADOS mas AINDA NÃO "
    "auditados item a item contra a fonte normativa — ver ruleset.yaml, "
    "seção escopo_amplo_em_conferencia.\n\n"
    "σ_adm sempre admite sobreposição manual pelo engenheiro (NBR 6122 "
    "§7.2 lista doze fatores para fixá-la). Solo expansivo ou colapsível "
    "exige tratamento específico (§7.5.2/§7.5.3) que nenhum dos dois "
    "motores deste software dimensiona.\n\n"
    "Minuta sujeita a conferência do responsável técnico que assina a ART."
)
