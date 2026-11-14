"""Goal 30 small fixes that ride with the Goal 31 package: per-instance render boxes of nine machines, duct arms that change
only on a neighbour update, and the boiler's top steam port.

Expected values:
- render boxes (Goal 30 small fix three): the original keeps the box in a TileEntity field, one per machine
  (TileEntityMachineFluidTank.java:216-233 and the eight others); the NEO port had moved it into the shared renderer, so every
  machine of a kind was culled by the box of the first one drawn. Each machine must report a box around itself.
- duct arms (Goal 30 acceptance 4.5, supplement 11.3 alternative): a saved duct state keeps its arms until a neighbour update
  recomputes them (FluidDuctConnectingBlock.updateShape); since 30C a press, a substation or a large radar cell has no fluid
  connection, so after the update the arm toward it is gone. The duct state is written with /setblock, which does not
  recompute the block's own shape; no world saved before 0.30.0 is loaded.
- boiler top port (Goal 30 small fix two): heat_boiler and machine_industrial_boiler accept fluid connections on every face
  (TileEntityHeatBoiler.java:41, TileEntityHeatBoilerIndustrial.java:35 use IFluidConnectorMK2.java:14-16), so a duct on the
  top steam port (y+4, y+5 above the core) draws its arm down and steam leaves through it.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402
import common  # noqa: E402

SCENARIO = dict(
    id='goal30-fixes.regressions',
    feature='goal30-fixes',
    title='Goal 30 fixes: render boxes of nine machines, duct arms on a neighbour update, boiler top steam port',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70, hide_gui=True),
)

Y = -60
X0 = 1400
APART = 40
MACHINES = ['machine_fluid_tank', 'launch_pad_large', 'launch_pad', 'machine_pumpjack', 'machine_well', 'machine_radar',
            'machine_battery_redd', 'machine_press', 'machine_assembly_machine']
ARM_MACHINES = [('machine_press', 'TileEntityMachinePress'), ('substation', 'Goal 30B substation'), ('machine_radar_large', 'TileEntityMachineRadarLarge')]
BOILERS = [('heat_boiler', 4, 'TileEntityHeatBoiler.java:41'), ('machine_industrial_boiler', 5, 'TileEntityHeatBoilerIndustrial.java:35')]


def expectations():
    E = [('render-%s' % m, '%s: two machines %d blocks apart each report their own render box, holding all of their cells' % (m, APART),
          'Goal 30 small fix three; original box per TileEntity, around the whole machine (e.g. TileEntityMachineFluidTank.java:216-233, '
          'TileEntityBatteryREDD.java:210-220)') for m in MACHINES]
    E.append(('redd-off-centre', 'machine_battery_redd seen from above its east edge with the core out of view: the box holds the edge '
              'cells and reaches the view (a centre box of +-2, as before the small fix, would not), and the outer ring is drawn',
              'TileEntityBatteryREDD.java:210-220 (box -4..+5)'))
    E += [('arm-%s' % m, '%s: a duct state with an arm toward a non-core cell keeps it until a neighbour update, then the arm is gone' % m,
           'FluidDuctConnectingBlock.updateShape; 30C proxy fluid rules; %s has no fluid connector' % src) for m, src in ARM_MACHINES]
    E += [('boiler-%s' % b, '%s: a duct on the top steam port (core y+%d) draws its arm down; steam leaves through that port into a barrel' % (b, h),
           '%s; IFluidConnectorMK2.java:14-16; Goal 30 small fix two' % src) for b, h, src in BOILERS]
    E += [('pipe-shapes', 'Pipe small fix (2026-11-13): universal fluid ducts as an isolated piece, straight along x, y and z, an L, a T and a '
           'cross each get their connection state and model quads; the duct item in the hand and in the inventory screen; the client '
           'log gets no exception or error line meanwhile', 'Goal 31 small fix 2026-11-13: PipeNeoBakedModel reads the six connection '
           'properties without a catch'),
          ('item-nbt-string', 'Item small fix (2026-11-13): ItemStackUtil.addNBTFromString catches only CommandSyntaxException',
           'original ItemStackUtil.java:250 (catches NBTException only)')]
    return [dict(id='goal30-fixes.' + i, text=t, source=s) for i, t, s in E]


# central duct at (cx, Y + 1, 60); neighbours by offset; the central duct's connections expected
SHAPES = [('isolated', [], set()),
          ('straight-x', [(1, 0, 0), (-1, 0, 0)], {'east', 'west'}),
          ('straight-y', [(0, 1, 0), (0, -1, 0)], {'up', 'down'}),
          ('straight-z', [(0, 0, 1), (0, 0, -1)], {'south', 'north'}),
          ('l', [(1, 0, 0), (0, 0, 1)], {'east', 'south'}),
          ('t', [(1, 0, 0), (-1, 0, 0), (0, 0, 1)], {'east', 'west', 'south'}),
          ('cross', [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)], {'east', 'west', 'up', 'down', 'south', 'north'})]


def pipe_shapes(ctx):
    log = common.CLIENTS / ctx.run.args.client / 'logs' / 'latest.log'
    start = len(log.read_text(encoding='utf-8', errors='replace').splitlines()) if log.exists() else 0
    x0, z = X0, 60
    ctx.step('view', pos=[x0 + 12.5, Y + 6, z + 6.5], look_at=[x0 + 12.5, Y + 1, z], fly=True, hide_gui=True)
    ctx.step('wait', ticks=40)
    got, ok = {}, True
    for i, (name, offs, want) in enumerate(SHAPES):
        cx = x0 + 4 * i
        cmd(ctx, 'setblock %d %d %d hbmsntm:fluid_duct_neo' % (cx, Y + 1, z))
        for dx, dy, dz in offs:
            cmd(ctx, 'setblock %d %d %d hbmsntm:fluid_duct_neo' % (cx + dx, Y + 1 + dy, z + dz))
    _lib.placed(ctx)
    for i, (name, offs, want) in enumerate(SHAPES):
        cx = x0 + 4 * i
        d = ctx.step('dump', **{'from': [cx, Y + 1, z]}, faces=True)['blocks']
        props = d[0]['props'] if d else {}
        conn = {k for k in ('east', 'west', 'up', 'down', 'south', 'north') if str(props.get(k)) == 'true'}
        quads = sum(len(v) for v in d[0]['faces'].values()) if d else 0
        got[name] = (sorted(conn), quads)
        ok = ok and conn == want and quads > 0
    shot = ctx.step('shot', file=ctx.shot_name('pipe-shapes'))['image']['file']
    # the item in the hand and in the inventory screen (the model with no block state)
    cmd(ctx, 'item replace entity @s weapon.mainhand with hbmsntm:fluid_duct_neo 8')
    ctx.step('view', pos=[x0 + 12.5, Y + 6, z + 6.5], look_at=[x0 + 12.5, Y + 1, z], fly=True, hide_gui=False)
    ctx.step('wait', ticks=6)
    m = ctx.step('itemmodel', item='hbmsntm:fluid_duct_neo')
    ctx.step('key', key='key.keyboard.e', action='tap', after=6)
    ctx.step('wait', ticks=6)
    ctx.step('close')
    cmd(ctx, 'item replace entity @s weapon.mainhand with minecraft:air')
    lines = log.read_text(encoding='utf-8', errors='replace').splitlines()[start:] if log.exists() else []
    bad = [l[:200] for l in lines if re.search(r'Exception|\bERROR\b|/ERROR\]', l)]
    # the dump reads the model without the level's model data, so the quad count is the same for every shape; the picture
    # shows the arms
    ctx.check('goal30-fixes.pipe-shapes', ok and log.exists() and not bad,
              '(connections, quads) per shape %s; item model sprites %s; client log %s: %d new lines, bad %s' % (
                  got, sorted(set(m.get('sprites', []))), log.name, len(lines), bad[:5]), [shot])
    ctx.not_run('goal30-fixes.item-nbt-string', 'addNBTFromString is reached only from recipe JSON files under config/hbmRecipes '
                '(static: its callers read that folder); exercising it needs a hand-edited config file in the client, outside this '
                'batch\'s authorization; the narrowed catch is a compile-level change (gap ledger)')


def cmd(ctx, command, **kw):
    return ctx.step('cmd', command=command, **kw)


def value(ctx, pos, key):
    r = cmd(ctx, 'data get block %d %d %d %s' % (pos[0], pos[1], pos[2], key), wait_ticks=6, allow_error=True)
    text = ' '.join(m['text'] for m in r.get('messages', []))
    m = re.search(r'[:：]\s*(-?\d+)[a-z]?\s*$', text)
    return int(m.group(1)) if m else None


def place(ctx, block, x, z, reach=(10, 12, 2)):
    """Places the block item by hand on the ground at (x, z), looking north from 4 blocks south; returns the cells and the core."""
    cmd(ctx, 'item replace entity @s weapon.mainhand with hbmsntm:%s' % block)
    ctx.step('view', pos=[x + 0.5, Y, z + 4.5], look_at=[x + 0.5, Y - 0.5, z + 0.5], fly=False, hide_gui=True)
    ctx.step('use', target=dict(pos=[x, Y - 1, z], face='up'), after=8)
    cmd(ctx, 'item replace entity @s weapon.mainhand with minecraft:air')
    w, h, back = reach
    d = ctx.step('dump', **{'from': [x - w, Y, z - w], 'to': [x + w, Y + h, z + back]})
    cells = {tuple(int(c) for c in b['pos']): b['props'].get('type', 'core') for b in d['blocks'] if b['block'] == 'hbmsntm:' + block}
    core = next((p for p, t in cells.items() if t == 'core'), None)
    return cells, core


def render_box(ctx, core):
    d = ctx.step('dump', **{'from': list(core), 'to': list(core)}, render_box=True)
    return d['blocks'][0].get('render_box') if d['blocks'] else None


def inside(box, p):
    return box != 'infinite' and box is not None and all(box[i] <= p[i] + 0.5 <= box[i + 3] for i in range(3))


def boxes(ctx):
    for i, m in enumerate(MACHINES):
        z = -16 * i
        cmd(ctx, 'fill %d %d %d %d %d %d minecraft:air' % (X0 - 10, Y, z - 12, X0 + APART + 10, Y + 12, z + 3), allow_error=True)
        placed = []
        for x in (X0, X0 + APART):
            cells, core = place(ctx, m, x, z)
            placed.append((cells, core))
        eid = 'goal30-fixes.render-%s' % m
        if any(core is None for _, core in placed):
            ctx.check(eid, False, 'not placed: cores %s' % [c for _, c in placed])
            continue
        (ca, a), (cb, b) = placed
        ctx.step('view', pos=[a[0] + 0.5, Y + 14, a[2] + 8.5], look_at=[a[0] + 0.5, Y + 2, a[2] + 0.5], fly=True, hide_gui=True)
        ctx.step('wait', ticks=10)
        box_a = render_box(ctx, a)
        shot_a = ctx.step('shot', file=ctx.shot_name('render-%s-first' % m))['image']['file']
        ctx.step('view', pos=[b[0] + 0.5, Y + 14, b[2] + 8.5], look_at=[b[0] + 0.5, Y + 2, b[2] + 0.5], fly=True, hide_gui=True)
        ctx.step('wait', ticks=10)
        box_b = render_box(ctx, b)
        shot_b = ctx.step('shot', file=ctx.shot_name('render-%s-second' % m))['image']['file']
        cover_a = sum(inside(box_a, p) for p in ca)
        cover_b = sum(inside(box_b, p) for p in cb)
        ok = (box_a not in (None, 'infinite') and box_b not in (None, 'infinite') and box_a != box_b
              and inside(box_a, a) and inside(box_b, b) and not inside(box_a, b) and not inside(box_b, a)
              and cover_a == len(ca) and cover_b == len(cb))
        ctx.check(eid, ok, 'core %s box %s (holds %d of %d cells); core %s box %s (holds %d of %d cells)' % (
            a, box_a, cover_a, len(ca), b, box_b, cover_b, len(cb)), [shot_a, shot_b])
        if m == 'machine_battery_redd':
            redd_off_centre(ctx, a, ca, box_a)


def redd_off_centre(ctx, core, cells, box):
    """Looks straight down from 3 blocks above the machine's east edge, facing east: with the vertical field of view of 70
    degrees the picture spans about 2.1 blocks east and west of the eye, so the core (4.5 blocks west) is out of view."""
    edge = max(c[0] for c in cells)
    eye_x = edge + 1.0
    half = 3.0 * 0.7002  # tan(35 degrees) at 3 blocks
    view_x = (eye_x - half, eye_x + half)
    ctx.step('view', pos=[eye_x, Y + 1.4, core[2] + 0.5], pitch=89.0, yaw=-90.0, fly=True, hide_gui=True)
    ctx.step('wait', ticks=10)
    shot = ctx.step('shot', file=ctx.shot_name('redd-off-centre'))['image']['file']
    old = (core[0] - 2, core[0] + 2)
    reaches = box not in (None, 'infinite') and box[3] >= view_x[0]
    old_misses = old[1] < view_x[0]
    edge_cells = [c for c in cells if c[0] == edge]
    held = box not in (None, 'infinite') and all(inside(box, c) for c in edge_cells)
    detail = ('view spans x %.1f..%.1f (core x %d); box %s reaches it %s, holds the %d east edge cells %s; a +-2 box (x %d..%d) misses it %s' % (
                  view_x[0], view_x[1], core[0], box, reaches, len(edge_cells), held, old[0], old[1], old_misses))
    if reaches and old_misses and held and core[0] + 0.5 < view_x[0]:
        # the box data hold; whether the outer ring is actually drawn is in the picture
        ctx.review('goal30-fixes.redd-off-centre', detail + '; look: the outer ring of the battery fills the picture', [shot])
    else:
        ctx.check('goal30-fixes.redd-off-centre', False, detail, [shot])


def arms(ctx):
    z = -160
    for i, (m, _) in enumerate(ARM_MACHINES):
        x = X0 + 20 * i
        cmd(ctx, 'fill %d %d %d %d %d %d minecraft:air' % (x - 8, Y, z - 12, x + 8, Y + 10, z + 3), allow_error=True)
        cells, core = place(ctx, m, x, z)
        eid = 'goal30-fixes.arm-%s' % m
        if core is None:
            ctx.check(eid, False, '%s not placed' % m)
            continue
        # a non-core cell on the east edge with air east of it
        edge = max((p for p in cells if p != core and (p[0] + 1, p[1], p[2]) not in cells), key=lambda p: (p[0], -p[1]), default=None)
        if edge is None:
            ctx.check(eid, False, 'no non-core cell with a free east side; cells %s' % sorted(cells))
            continue
        duct = (edge[0] + 1, edge[1], edge[2])
        cmd(ctx, 'setblock %d %d %d hbmsntm:fluid_duct_neo[west=true]' % duct)
        _lib.placed(ctx)
        ctx.step('view', pos=[duct[0] + 3.5, duct[1] + 1.5, duct[2] + 3.5], look_at=[duct[0] + 0.5, duct[1] + 0.5, duct[2] + 0.5], fly=True, hide_gui=True)
        ctx.step('wait', ticks=10)
        before = ctx.step('dump', **{'from': list(duct), 'to': list(duct)})['blocks'][0]['props']
        shot_before = ctx.step('shot', file=ctx.shot_name('arm-%s-before' % m))['image']['file']
        # the neighbour update: a block east of the duct, then air again
        cmd(ctx, 'setblock %d %d %d minecraft:stone' % (duct[0] + 1, duct[1], duct[2]))
        cmd(ctx, 'setblock %d %d %d minecraft:air' % (duct[0] + 1, duct[1], duct[2]))
        _lib.placed(ctx)
        after = ctx.step('dump', **{'from': list(duct), 'to': list(duct)})['blocks'][0]['props']
        shot_after = ctx.step('shot', file=ctx.shot_name('arm-%s-after' % m))['image']['file']
        ok = before.get('west') == 'true' and after.get('west') == 'false'
        ctx.check(eid, ok, 'duct %s next to %s cell %s: west arm before the update %s, after %s (the machine has no fluid connector, so '
                  'nothing to send or receive)' % (duct, cells[edge], edge, before.get('west'), after.get('west')), [shot_before, shot_after])


def boilers(ctx):
    z = -200
    # the steam id, read back from a barrel set by name
    probe = (X0 - 6, Y, z + 6)
    cmd(ctx, 'setblock %d %d %d hbmsntm:barrel_steel' % probe)
    cmd(ctx, 'data merge block %d %d %d {tank_type:"STEAM"}' % probe)
    steam = value(ctx, probe, 'tank_type')
    cmd(ctx, 'setblock %d %d %d minecraft:air' % probe)
    for i, (b, h, _) in enumerate(BOILERS):
        x = X0 + 16 * i
        cmd(ctx, 'fill %d %d %d %d %d %d minecraft:air' % (x - 6, Y, z - 8, x + 6, Y + 10, z + 3), allow_error=True)
        cells, core = place(ctx, b, x, z)
        eid = 'goal30-fixes.boiler-%s' % b
        if core is None or steam is None:
            ctx.check(eid, False, '%s not placed (core %s) or steam id unknown (%s)' % (b, core, steam))
            continue
        duct = (core[0], core[1] + h, core[2])
        barrel = (duct[0], duct[1] + 1, duct[2])
        cmd(ctx, 'setblock %d %d %d hbmsntm:fluid_duct_neo' % duct)
        cmd(ctx, 'data merge block %d %d %d {Type:%d}' % (duct + (steam,)))
        cmd(ctx, 'setblock %d %d %d hbmsntm:barrel_steel' % barrel)
        cmd(ctx, 'data merge block %d %d %d {tank_type:"STEAM",mode:0s}' % barrel)
        # the neighbour update that lets the duct work out its arms (the barrel above was just placed, so recompute after it)
        cmd(ctx, 'setblock %d %d %d minecraft:stone' % (duct[0] + 1, duct[1], duct[2]))
        cmd(ctx, 'setblock %d %d %d minecraft:air' % (duct[0] + 1, duct[1], duct[2]))
        _lib.placed(ctx)
        props = ctx.step('dump', **{'from': list(duct), 'to': list(duct)})['blocks'][0]['props']
        ctx.step('view', pos=[duct[0] + 4.5, duct[1] + 1.5, duct[2] + 4.5], look_at=[duct[0] + 0.5, duct[1] - 0.5, duct[2] + 0.5], fly=True, hide_gui=True)
        ctx.step('wait', ticks=10)
        shot = ctx.step('shot', file=ctx.shot_name('boiler-%s' % b))['image']['file']
        # steam through the top port: a steam barrel in the port's place (a duct typed by data merge joins no network)
        cmd(ctx, 'setblock %d %d %d minecraft:air' % barrel)
        cmd(ctx, 'setblock %d %d %d hbmsntm:barrel_steel' % duct)
        cmd(ctx, 'data merge block %d %d %d {tank_type:"STEAM",mode:0s}' % duct)
        cmd(ctx, 'data merge block %d %d %d {output:4000}' % core)
        ctx.step('wait', ticks=60)
        got = value(ctx, duct, 'tank')
        left = value(ctx, core, 'output')
        ok = props.get('down') == 'true' and (got or 0) > 0
        ctx.check(eid, ok, 'duct %s on the top port: arms %s; a steam barrel in its place then got %s mB, left in the boiler %s of 4000' % (
            duct, {k: v for k, v in props.items() if v == 'true'}, got, left), [shot])


def run(ctx):
    _lib.setup_world(ctx, freeze=False)
    ctx.step('view', pos=[X0 + 20.5, Y + 20, 0.5], pitch=60.0, yaw=180.0, fly=True, hide_gui=True)
    ctx.step('wait', ticks=40)
    boxes(ctx)
    arms(ctx)
    boilers(ctx)
    pipe_shapes(ctx)
