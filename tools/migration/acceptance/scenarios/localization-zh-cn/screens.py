"""Language scan, layer 2: in Chinese, every mainline machine's screen and its look overlay, read as drawn.

Each machine is placed by hand (multiblocks the way a player places them), looked at from the south (the look overlay
beside the crosshair), then opened with an empty hand on its front cell; every text the screen draws (labels, buttons,
gauges, tooltips drawn without hovering are not included) is read with the hud step. Item tooltips are layer 1's. A text
that is a translation key or still holds a placeholder is a leak; a run of Latin letters in a Chinese screen is listed
for a person, since units, symbols and machine names (RBMK, ZIRNOX, HE, mB) are legitimately Latin. The complete
findings go to <run>/language-scan-screens.json.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='localization-zh-cn.screens',
    feature='localization-zh-cn',
    title='Language scan 2: mainline machine screens and look overlays in Chinese',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

Y = -60
OX, OZ = 3000, 3000
# Machines of the mainline stages that a player opens or looks at (single blocks and multiblocks).
MACHINES = (
    'anvil', 'machine_press', 'press_preheater', 'machine_blast_furnace', 'machine_crucible', 'furnace_combination',
    'heater_firebox', 'heater_oven', 'heater_oilburner', 'heater_heatex', 'machine_shredder', 'machine_electric_furnace',
    'machine_arc_furnace', 'machine_arc_welder', 'machine_soldering_station', 'machine_assembly_machine', 'machine_chemical_plant',
    'machine_mixer', 'machine_crystallizer', 'machine_centrifuge', 'machine_gas_centrifuge', 'machine_battery_socket',
    'machine_wood_burner', 'machine_stirling', 'machine_steam_engine', 'machine_diesel', 'machine_combustion_engine',
    'machine_rtg', 'machine_industrial_boiler', 'heat_boiler', 'machine_industrial_turbine', 'machine_chungus', 'machine_condenser',
    'machine_turbofan', 'machine_fluid_tank', 'machine_well', 'machine_pumpjack', 'machine_fracking_tower', 'pump_electric',
    'machine_compressor', 'machine_refinery', 'machine_vacuum_distill', 'machine_catalytic_cracker', 'machine_fraction_tower',
    'machine_coker', 'machine_zirnox', 'machine_waste_drum', 'machine_purex', 'rbmk_console',
)
KEY = re.compile(r'(?<![\w.])(?:[a-z][a-z0-9_]*\.)+[a-z0-9_]+(?![\w.])')
PLACEHOLDER = re.compile(r'%(?:\d+\$)?[sdf]')
LATIN = re.compile(r'[A-Za-z][A-Za-z\'-]{2,}(?:\s+[A-Za-z][A-Za-z\'-]+)*')


def expectations():
    E = [
        ('screens-keys', 'Chinese: no text a mainline machine screen or look overlay draws is a translation key or holds a placeholder'),
        ('screens-latin', 'record for a person: Latin words drawn on the Chinese screens and look overlays (hard-coded English candidates)'),
        ('screens-opened', 'record: which machines were placed, which opened a screen and which have a look overlay'),
    ]
    return [dict(id='localization-zh-cn.' + i, text=t, source='GuiGraphics text calls (hud step)') for i, t in E]


def leaks_of(texts):
    return [t for t in texts if KEY.fullmatch(t.strip()) or [k for k in KEY.findall(t) if '.' in k and not re.fullmatch(r'[\d.]+', k)
                                                             and re.match(r'(?:item|block|tile|desc|container|gui|info|hbmsntm|trait|tooltip|machine)\.', k)]
            or PLACEHOLDER.search(t)]


def cmd(ctx, command, **kw):
    return ctx.step('cmd', command=command, **kw)


def place(ctx, block, x, z):
    """By hand onto the ground at (x, z), looking north; returns the cells of the placed block (pos -> state)."""
    cmd(ctx, 'item replace entity @s weapon.mainhand with hbmsntm:%s' % block)
    ctx.step('view', pos=[x + 0.5, Y, z + 4.5], look_at=[x + 0.5, Y - 0.5, z + 0.5], fly=True, hide_gui=True)
    ctx.step('use', target=dict(pos=[x, Y - 1, z], face='up'), after=8, allow_fail=True)
    cmd(ctx, 'item replace entity @s weapon.mainhand with minecraft:air')
    _lib.placed(ctx, 4)
    d = ctx.step('dump', **{'from': [x - 6, Y, z - 10], 'to': [x + 6, Y + 12, z + 3]})
    return {tuple(int(c) for c in b['pos']): b for b in d['blocks'] if b['block'] == 'hbmsntm:' + block}


def run(ctx):
    _lib.setup_world(ctx)
    _lib.go_near(ctx, OX, Y, OZ)
    # command feedback would show in the chat the hud step also reads; the next scenarios need it back
    cmd(ctx, 'gamerule sendCommandFeedback false')
    ctx.step('wait', ticks=220)  # chat lines fade after 200 ticks
    try:
        rows = scan(ctx)
    finally:
        cmd(ctx, 'gamerule sendCommandFeedback true')
    report(ctx, rows)


def scan(ctx):
    rows = []
    for i, block in enumerate(MACHINES):
        x, z = OX + (i % 10) * 14, OZ + (i // 10) * 16
        _lib.go_near(ctx, x, Y, z)
        cells = place(ctx, block, x, z)
        row = dict(block=block, placed=bool(cells))
        if cells:
            # the front cell: southmost, lowest, nearest the placement column
            front = min(cells, key=lambda p: (-p[2], p[1], abs(p[0] - x)))
            fx, fy, fz = front
            ctx.step('view', pos=[fx + 0.5, fy + 0.5, fz + 3.5], look_at=[fx + 0.5, fy + 0.5, fz + 0.5], fly=True, hide_gui=False)
            ctx.step('wait', ticks=4)
            hud = ctx.step('hud', frames=4)
            row['overlay'] = _lib.crosshair_texts(hud)
            # the front cell first, then the core and the top cell from above (some machines open only there)
            core = next((p for p, b in cells.items() if b['props'].get('type', 'core') == 'core'), front)
            top = max(cells, key=lambda p: (p[1], -abs(p[0] - x), p[2]))
            tries = [(front, 'south', [fx + 0.5, fy + 0.5, fz + 3.5])]
            for p in (core, top):
                if p != front:
                    tries.append((p, 'up', [p[0] + 0.5, p[1] + 3.5, p[2] + 0.5]))
            row['screen'] = None
            for pos, face, eye in tries:
                ctx.step('view', pos=eye, look_at=[pos[0] + 0.5, pos[1] + (1.0 if face == 'up' else 0.5), pos[2] + (0.5 if face == 'up' else 1.0)],
                         fly=True, hide_gui=False)
                ctx.step('use', target=dict(pos=list(pos), face=face), after=6, allow_fail=True)
                ctx.step('wait', ticks=6)
                screen = ctx.step('screen', expect='', allow_fail=True)  # expect '' reads whatever screen is open
                if screen.get('screen') not in (None, 'none'):
                    row['screen'], row['opened_at'] = screen['screen'], [list(pos), face]
                    break
            if row['screen']:
                hud = ctx.step('hud', frames=4)
                row['texts'] = [t['text'] for t in hud['texts'] if not t['text'].startswith('tooltip: ')]
                ctx.step('close')
                ctx.step('wait', ticks=2)
        texts = row.get('texts', []) + row.get('overlay', [])
        row['leaks'] = leaks_of(texts)
        row['latin'] = sorted({m.group(0) for t in texts for m in LATIN.finditer(t)})
        rows.append(row)
    return rows


def report(ctx, rows):
    (ctx.run.dir / 'language-scan-screens.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    leaking = [r for r in rows if r['leaks']]
    ctx.check('localization-zh-cn.screens-keys', not leaking,
              '%d of %d machines with a leak: %s' % (len(leaking), len(rows), '; '.join('%s: %s' % (r['block'], ' / '.join(r['leaks'][:2])) for r in leaking[:8])),
              evidence=['language-scan-screens.json'])
    latin = [r for r in rows if r['latin']]
    ctx.review('localization-zh-cn.screens-latin', '%d machines draw Latin words: %s' % (len(latin), '; '.join(
        '%s: %s' % (r['block'], ', '.join(r['latin'][:6])) for r in latin[:12])), evidence=['language-scan-screens.json'])
    ctx.review('localization-zh-cn.screens-opened', 'placed %d of %d; screens %d; look overlays %d; not opened: %s' % (
        sum(r['placed'] for r in rows), len(rows), sum(1 for r in rows if r.get('screen')), sum(1 for r in rows if r.get('overlay')),
        ', '.join(r['block'] for r in rows if r['placed'] and not r.get('screen'))), evidence=['language-scan-screens.json'])
