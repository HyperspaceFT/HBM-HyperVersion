"""Radioactive blocks placed by the player's own right-click (not by a command): polonium block, nuclear waste block, falling yellowcake block.

Expected values follow the 1.7.10 original:
- a radioactive block takes its radiation when it is placed: the item's radiation hazard x 0.1 into the block's `rad`, and a block tick
  20 ticks later; every block tick adds `rad` to the chunk and schedules the next (BlockHazard.java:120-146). block_polonium: po210 75
  x block 10 x 0.1 = 75 per 20 ticks (HazardRegistry.java:83,142); NEO HazardBlock.java:37-52.
- block_waste is a BlockNuclearWaste: every block tick first picks one of the six directions at random and, one time in two, puts dense
  radon into that neighbour when it is air (BlockNuclearWaste.java:14-22); NEO NuclearWasteBlock.java. With five air neighbours a
  tick leaves gas with chance 5/12, so 20 block ticks leave none with chance (7/12)^20 < 2e-5. Dense radon moves and fades (one
  chance in 30 a gas tick), so the box around the block is read every 40 ticks and the row passes when any read shows it.
- block_yellowcake is a BlockHazardFalling: it falls like sand when nothing holds it (BlockHazardFalling.java:39-66) and, as a hazard
  block, adds 0.35 x 10 x 3 x 0.1 = 1.05 to its chunk every 20 ticks from where it lies (HazardRegistry.java:473-474); NEO
  HazardFallingBlock.java (fall check at the block tick, 20 ticks after placement).
The chunk value is read with the Geiger counter's chunk line (cut to one decimal, original ContaminationUtil.java:161). Its window
comes from the chunk map rule (original ChunkRadiationHandlerSimple.java:71-122, NEO :72-118; every 20 ticks a chunk keeps 0.6 of its
value and hands the rest to its eight neighbours, each share landing as max(0, (S + share) x 0.99 - 0.05)): with one map update after
each of E emissions of r the chunk holds at least x_E, x_0 = 0, x_(k+1) = max(0, 0.548 (x_k + r) - 0.433), and no chunk holds more than
r x (emissions so far) x 1.001 (an update never adds to the sum of all values). E_min counts the block ticks the game time since the
placement (or the landing) guarantees, E_max the most it allows. Each source has its own chunk, far apart, read at 0 before.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='hazard-system.player_placed',
    feature='hazard-system',
    title='Radioactive blocks placed by hand: polonium chunk radiation, nuclear waste lets out dense radon, yellowcake falls and radiates',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

H = 'hbmsntm:'
Y = _lib.FLAT_FEET
TICK = 20
FLOOR_MUL, FLOOR_SUB = 0.548, 0.433
GEIGER_STEP = 0.1
# one chunk each (x of the block; z 8 is the middle of chunk z 0); 100 blocks (six chunks) apart
YC_X, PO_X, WASTE_X = 2800, 2900, 3000
BZ = 8
PO_RATE, YC_RATE = 75.0, 1.05
PO_WAIT = 300
WASTE_READS, WASTE_EVERY, WASTE_BOX = 10, 40, 6
YC_WAIT, YC_WAIT2 = 100, 300


def expectations():
    E = [
        ('hazard-system.placed-polonium-radiates',
         'a block_polonium placed by right-click in a chunk whose Geiger chunk reading is 0: 300 ticks later the chunk reading lies in the window of the '
         'module docstring for 75 per 20 ticks (at least x_E_min - 0.1, at most 75 x E_max x 1.001)',
         'original BlockHazard.java:120-146, HazardRegistry.java:83,142; NEO HazardBlock.java:37-52'),
        ('hazard-system.placed-waste-dense-radon',
         'a block_waste placed by right-click on the ground, air on its five other sides: within 400 ticks dense radon (gas_radon_dense) shows up in the '
         'box of radius 6 around it in at least one of ten reads 40 ticks apart',
         'original BlockNuclearWaste.java:14-22; NEO NuclearWasteBlock.java'),
        ('hazard-system.placed-yellowcake-falls',
         'a block_yellowcake placed by right-click on top of a stone two blocks above the ground: when the stone is removed it falls and comes to rest on '
         'the ground (the cell it was placed in is air, the ground cell holds it)',
         'original BlockHazardFalling.java:39-66; NEO HazardFallingBlock.java'),
        ('hazard-system.placed-yellowcake-radiates',
         'after it came to rest the chunk reading (0 before the placement) rises: 100 and 300 ticks after the landing it lies in the window for 1.05 per '
         '20 ticks counted from the landing (at least x_E_min - 0.1 and above 0, at most 1.05 x E_max x 1.001 with the emissions since the placement)',
         'original BlockHazardFalling.java:39-66, HazardRegistry.java:473-474; NEO HazardFallingBlock.java'),
    ]
    return [dict(id=i, text=t, source=s) for i, t, s in E]


def floor_emitting(rate, emissions):
    x = 0.0
    for _ in range(max(emissions, 0)):
        x = max(0.0, FLOOR_MUL * (x + rate) - FLOOR_SUB)
    return x


def game(ctx):
    return ctx.server()['game_time']


def prefix_of(ctx):
    return ctx.step('i18n', keys=['geiger.chunkRad'])['texts']['geiger.chunkRad'].split('Format error: ')[-1].split('%s')[0]


def geiger(ctx, x, prefix):
    """Hovers in the middle of the chunk of block x (z 4.5) looking up and uses the Geiger counter from hotbar slot 1; returns
    (value, line) of the chunk line, (None, last lines) when it is missing."""
    ctx.step('view', pos=[x + 0.5, Y + 3, 4.5], yaw=0.0, pitch=-90.0, fly=True, hide_gui=False)
    ctx.step('cmd', command='item replace entity @s hotbar.0 with %sgeiger_counter' % H)
    ctx.step('key', key='key.keyboard.1', action='tap', after=2)
    said = ctx.step('use', after=6)
    c = ctx.step('chat', count=12, since_ms=said['started_ms'], allow_fail=True)
    lines = [m['text'] for m in c.get('messages', [])]
    for line in lines:
        if prefix and prefix in line:
            m = re.search(r'(-?\d+(?:\.\d+)?)', line[line.index(prefix) + len(prefix):])
            if m:
                return float(m.group(1)), line
    return None, lines[-6:]


def place_by_hand(ctx, block, against, face, stand, fly=False):
    """Puts `block` into hotbar slot 2, selects it and right-clicks `face` of `against` from `stand`; returns the game time just
    before and just after the click."""
    ctx.step('cmd', command='item replace entity @s hotbar.1 with %s' % block)
    ctx.step('key', key='key.keyboard.2', action='tap', after=2)
    ctx.step('view', pos=list(stand), look_at=_lib.face_point(against, face), fly=fly, hide_gui=False)
    t0 = game(ctx)
    ctx.step('use', target=dict(pos=list(against), face=face), after=2)
    return t0, game(ctx)


def window(ctx, x, prefix, rate, t_from_min, t_from_max):
    """A Geiger reading with its window: E_min block ticks since t_from_min (the first one 20 ticks later, one less for the tick in
    progress), E_max since t_from_max."""
    g0 = game(ctx)
    value, line = geiger(ctx, x, prefix)
    g1 = game(ctx)
    e_min = (g0 - t_from_min) // TICK - 1
    e_max = (g1 - t_from_max) // TICK + 1
    lo, hi = floor_emitting(rate, e_min), rate * max(e_max, 0) * 1.001
    ok = value is not None and lo - GEIGER_STEP <= value <= hi
    return ok, dict(value=value, e_min=e_min, e_max=e_max, floor=round(lo, 3), cap=round(hi, 2), game=[g0, g1],
                    line=str(line)[:100])


def run(ctx):
    _lib.setup_world(ctx, freeze=False)
    ids = [e['id'] for e in expectations()]
    prefix = prefix_of(ctx)

    # ---- yellowcake: placed on a floating stone, the stone removed, falls, radiates from the ground
    def yellowcake():
        ctx.server('tick unfreeze')
        stone = (YC_X, Y + 2, BZ)
        top = (YC_X, Y + 3, BZ)
        ground = (YC_X, Y, BZ)
        _lib.go_near(ctx, YC_X, Y, BZ)
        ctx.step('cmd', command='setblock %d %d %d minecraft:stone' % stone)
        _lib.placed(ctx)
        base, base_line = geiger(ctx, YC_X, prefix)
        t0, t1 = place_by_hand(ctx, H + 'block_yellowcake', stone, 'up', [YC_X + 0.5, Y + 4, BZ - 1.5], fly=True)
        held = _lib.is_block(ctx, top, H + 'block_yellowcake')
        ctx.step('cmd', command='setblock %d %d %d minecraft:air' % stone)
        t_land = None
        for _ in range(40):
            ctx.step('wait', ticks=3)
            if _lib.is_block(ctx, ground, H + 'block_yellowcake'):
                t_land = game(ctx)
                break
        top_air = _lib.is_block(ctx, top, 'minecraft:air')
        ctx.check(ids[2], held and t_land is not None and top_air and base == 0.0,
                   'placed on the stone: %s (game %d-%d); stone removed; at rest on the ground cell %s: %s (game %s); the placed cell air: %s; '
                   'chunk reading before the placement %s' % (held, t0, t1, list(ground), t_land is not None, t_land, top_air, base))
        if t_land is None or base != 0.0:
            ctx.not_run(ids[3], 'the yellowcake did not come to rest on the ground, or the chunk was not clean before (reading %s)' % (base,))
            return
        reads = []
        for wait_to in (YC_WAIT, YC_WAIT2):
            ctx.step('wait', ticks=max(1, wait_to - (game(ctx) - t_land)))
            ok, r = window(ctx, YC_X, prefix, YC_RATE, t_land, t0)
            reads.append((ok and (r['value'] or 0) > 0, r))
        ctx.check(ids[3], all(o for o, _ in reads), '; '.join('%d ticks after the landing: %s' % (w, r) for w, (_, r) in zip((YC_WAIT, YC_WAIT2), reads)))
        ctx.step('cmd', command='setblock %d %d %d minecraft:air' % ground)

    # ---- polonium
    def polonium():
        ctx.server('tick unfreeze')
        against = (PO_X, Y - 1, BZ)
        cell = (PO_X, Y, BZ)
        _lib.go_near(ctx, PO_X, Y, BZ)
        base, base_line = geiger(ctx, PO_X, prefix)
        t0, t1 = place_by_hand(ctx, H + 'block_polonium', against, 'up', [PO_X + 0.5, Y, BZ - 2.5])
        there = _lib.is_block(ctx, cell, H + 'block_polonium')
        if not there or base != 0.0:
            ctx.check(ids[0], False, 'placed: %s; chunk reading before %s (%s)' % (there, base, base_line))
            return
        ctx.step('wait', ticks=max(1, PO_WAIT - (game(ctx) - t1)))
        ok, r = window(ctx, PO_X, prefix, PO_RATE, t1, t0)
        ctx.check(ids[0], ok, 'chunk reading before the placement 0.0; placed by right-click at game %d-%d; %d ticks later %s' % (t0, t1, PO_WAIT, r))
        ctx.step('cmd', command='setblock %d %d %d minecraft:air' % cell)

    # ---- nuclear waste
    def waste():
        ctx.server('tick unfreeze')
        against = (WASTE_X, Y - 1, BZ)
        cell = (WASTE_X, Y, BZ)
        _lib.go_near(ctx, WASTE_X, Y, BZ)
        ctx.step('cmd', command='fill %d %d %d %d %d %d minecraft:air replace %sgas_radon_dense' % (
            WASTE_X - 8, Y, BZ - 8, WASTE_X + 8, Y + 8, BZ + 8, H), allow_error=True)
        t0, t1 = place_by_hand(ctx, H + 'block_waste', against, 'up', [WASTE_X + 0.5, Y, BZ - 2.5])
        there = _lib.is_block(ctx, cell, H + 'block_waste')
        seen = []
        for n in range(WASTE_READS):
            ctx.step('wait', ticks=WASTE_EVERY)
            box = ctx.step('dump', **{'from': [WASTE_X - WASTE_BOX, Y, BZ - WASTE_BOX], 'to': [WASTE_X + WASTE_BOX, Y + WASTE_BOX, BZ + WASTE_BOX]})
            cells = [b['pos'] for b in box['blocks'] if b['block'] == H + 'gas_radon_dense']
            seen.append((game(ctx) - t1, len(cells), cells[:3]))
        ctx.check(ids[1], there and any(k for _, k, _ in seen),
                   'placed by right-click: %s (game %d-%d); reads (ticks since placement, dense radon cells, first cells): %s' % (there, t0, t1, seen))
        ctx.step('cmd', command='setblock %d %d %d minecraft:air' % cell)

    _lib.section(ctx, [ids[2], ids[3]], yellowcake, 'yellowcake section')
    _lib.section(ctx, [ids[0]], polonium, 'polonium section')
    _lib.section(ctx, [ids[1]], waste, 'waste section')
    # the placed blocks stay in the hotbar of a creative player: take them away, they would irradiate a survival player
    ctx.step('cmd', command='clear @s', allow_error=True)
