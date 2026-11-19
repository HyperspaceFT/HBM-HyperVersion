"""Exports for closure.py: the anvil, crucible and machine tables that hbmsntm defines in Java and never writes as JSON.

Not a gameplay check. The client's config/hbmRecipes (written when the integrated server starts) is the fourth input of
closure.py; this scenario only writes the executor's exports/anvil.json, exports/crucible.json and exports/machines.json.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='acceptance-executor.export',
    feature='acceptance-executor',
    title='Executor exports for the survival-source closure: anvil, crucible, machine tables',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

EXPECT = [
    ('anvil', 'export: the anvil construction and smithing tables are written to exports/anvil.json'),
    ('crucible', 'export: crucible melting (item to materials) and mold casts are written to exports/crucible.json'),
    ('machines', 'export: the gas centrifuge cascades, the combination oven and the RBMK rod disassembly are written to exports/machines.json'),
]


def expectations():
    return [dict(id='acceptance-executor.export-' + k, text=t, source='executor') for k, t in EXPECT]


def eid(k):
    return 'acceptance-executor.export-' + k


def run(ctx):
    _lib.setup_world(ctx, freeze=False)
    ex = ctx.step('export', kind='anvil', allow_fail=True)
    ctx.check(eid('anvil'), ex['status'] == 'ok' and ex.get('construction', 0) > 0 and ex.get('smithing', 0) > 0,
              '%s construction, %s smithing in %s %s' % (ex.get('construction'), ex.get('smithing'), ex.get('file'), ex.get('reason', '')),
              ['export seq %s' % ex['seq']])
    ec = ctx.step('export', kind='crucible', allow_fail=True)
    ctx.check(eid('crucible'), ec['status'] == 'ok' and ec.get('smelting', 0) > 0 and ec.get('casts', 0) > 0,
              '%s melting entries, %s casts in %s %s' % (ec.get('smelting'), ec.get('casts'), ec.get('file'), ec.get('reason', '')),
              ['export seq %s' % ec['seq']])
    em = ctx.step('export', kind='machines', allow_fail=True)
    ctx.check(eid('machines'), em['status'] == 'ok' and em.get('gas_centrifuge', 0) > 0 and em.get('combination', 0) > 0
              and em.get('rbmk_disassembly', 0) > 0,
              '%s gas centrifuge, %s combination, %s rod disassembly rows in %s %s' % (
                  em.get('gas_centrifuge'), em.get('combination'), em.get('rbmk_disassembly'), em.get('file'), em.get('reason', '')),
              ['export seq %s' % em['seq']])
