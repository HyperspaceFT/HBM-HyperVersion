"""Screwdriver wear on the splitter in survival: every adjusting click costs one durability, the desh screwdriver never wears.

Expected values follow the 1.7.10 original (cd0cff450): ItemTooling.onItemUse (ItemTooling.java:25-40) calls onScrew and, when it answers
true and the item has durability, damages the stack by 1; CraneSplitter.onScrew (CraneSplitter.java:164-190) answers true for every
screwdriver click on the server, also when the ratio is already at its bound 1 or 16 (the value is clamped, the click still counts).
The regular screwdriver has durability 100 and the desh screwdriver 0, which never wears (ModItems.java:3715-3716). A plain click raises
the ratio of the block clicked by 1 and a sneaking click lowers it by 1 (CraneSplitter.java:178-184); the core is the left block.
The splitter is placed by hand as in the sorter scenario and the screwdriver used through the real use key; the wear is read from the
server's inventory.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='conveyor-cranes.screwdriver_wear',
    feature='conveyor-cranes',
    title='Screwdriver on the splitter in survival: one durability per click, clamped clicks included; desh never wears',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70, hide_gui=False),
)

Y = -60
SX = 1900
DRIVER, DESH = 'hbmsntm:screwdriver', 'hbmsntm:screwdriver_desh'
# (which block, sneaking, ratio left:right after the click, wear after the click); the ratios start at 1:1
CLICKS = [('core', False, (2, 1), 1), ('core', False, (3, 1), 2), ('other', False, (3, 2), 3), ('other', True, (3, 1), 4), ('other', True, (3, 1), 5)]


def expectations():
    E = [('screwdriver-wear-splitter', 'survival: five screwdriver clicks on a splitter (plain on the core twice and on the second block once, sneaking on the second '
          'block twice, the last one at the bound 1) change the ratio as expected and wear the screwdriver by 1 each, 5 in all',
          'ItemTooling.java:25-40, CraneSplitter.java:164-190, ModItems.java:3715'),
         ('screwdriver-desh-no-wear', 'survival: three clicks with the desh screwdriver raise the ratio 3 steps and leave it unworn (durability 0)',
          'ItemTooling.java:34-35 (getMaxDamage() > 0), ModItems.java:3716')]
    return [dict(id='conveyor-cranes.' + i, text=t, source=s) for i, t, s in E]


def cmd(ctx, command, **kw):
    return ctx.step('cmd', command=command, **kw)


def splitter_cells(ctx):
    d = ctx.step('dump', **{'from': [SX - 1, Y, -1], 'to': [SX + 1, Y, 1]})
    return {tuple(int(c) for c in b['pos']): b['props'] for b in d['blocks'] if b['block'] == 'hbmsntm:crane_splitter'}


def wear(ctx, item):
    """The damage of the first stack of `item` in the server's inventory, None when there is none."""
    stacks = [e for e in _lib.inventory(ctx).values() if e['id'] == item]
    return stacks[0]['damage'] if stacks else None


def ratio(ctx, core):
    """The splitter's (left, right) ratio from its block entity on the server (the core is the left block)."""
    return tuple(int(re.sub(r'[a-zA-Z]$', '', str(_lib.block_data(ctx, core, side)))) for side in ('left', 'right'))


def screw(ctx, pos, sneak):
    ctx.step('view', pos=[pos[0] + 0.5, Y, pos[2] + 2.5], look_at=[pos[0] + 0.5, Y + 0.2, pos[2] + 0.5], fly=False, hide_gui=False)
    if sneak:
        _lib.sneak(ctx, True)
    try:
        hit = ctx.step('use', target=dict(pos=list(pos), face='up', offset=[0, -0.6, 0]), any_hit=True, after=4).get('hit') or {}
    finally:
        if sneak:
            _lib.sneak(ctx, False)
    return hit.get('type') == 'BLOCK' and [int(v) for v in hit.get('pos', [])] == list(pos)


def run(ctx):
    _lib.setup_world(ctx, freeze=False)
    _lib.go_near(ctx, SX, Y, 0)
    cmd(ctx, 'clear @s', allow_error=True)
    cmd(ctx, 'item replace entity @s weapon.mainhand with hbmsntm:crane_splitter')
    ctx.step('view', pos=[SX + 0.5, Y, 2.5], look_at=[SX + 0.5, Y - 0.5, 0.5], fly=False, hide_gui=False)
    ctx.step('use', target=dict(pos=[SX, Y - 1, 0], face='up'), after=6)
    cells = splitter_cells(ctx)
    core = next((p for p, props in cells.items() if props.get('type') == 'core'), None)
    other = next((p for p in cells if p != core), None)
    cmd(ctx, 'clear @s', allow_error=True)
    if core is None or other is None:
        ctx.check('conveyor-cranes.screwdriver-wear-splitter', False, 'the splitter was not placed: cells %s' % cells)
        ctx.not_run('conveyor-cranes.screwdriver-desh-no-wear', 'no splitter')
        return
    cmd(ctx, 'gamemode survival')
    cmd(ctx, 'item replace entity @s weapon.mainhand with %s' % DRIVER)
    ctx.step('wait', ticks=4)
    start = dict(ratio=ratio(ctx, core), wear=wear(ctx, DRIVER))
    seen, hits = [], []
    for which, sneak, _, _ in CLICKS:
        hits.append(screw(ctx, core if which == 'core' else other, sneak))
        seen.append((ratio(ctx, core), wear(ctx, DRIVER)))
    want = [(r, w) for _, _, r, w in CLICKS]
    ctx.check('conveyor-cranes.screwdriver-wear-splitter', start == dict(ratio=(1, 1), wear=0) and all(hits) and seen == want,
              'start %s; per click (ratio left:right, wear) %s, expected %s; every click hit its block %s (core %s, second block %s)'
              % (start, seen, want, all(hits), core, other))
    cmd(ctx, 'clear @s %s' % DRIVER, allow_error=True)
    cmd(ctx, 'item replace entity @s weapon.mainhand with %s' % DESH)
    ctx.step('wait', ticks=4)
    desh_hits = [screw(ctx, core, False) for _ in range(3)]
    after = (ratio(ctx, core), wear(ctx, DESH))
    ctx.check('conveyor-cranes.screwdriver-desh-no-wear', all(desh_hits) and after == ((6, 1), 0),
              'after three clicks (ratio left:right, wear) %s, expected ((6, 1), 0); every click hit the core %s' % (after, all(desh_hits)))
    cmd(ctx, 'gamemode creative')
