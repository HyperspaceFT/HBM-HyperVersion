"""Mining uranium ore and asbestos ore in survival: the gas that comes out, and what a player sees of it.

Expected values follow the 1.7.10 original:
- a harvested outgassing ore leaves its gas where it stood: uranium ore gives radon gas, asbestos ore asbestos gas (BlockOutgas.java:40-64 picks
  the gas, :93-101 puts it into the broken cell when the block is harvested; a break by hand is not a harvest, no gas).
- every gas block has no model and no outline (BlockGasBase.java:39-62: `getRenderType() == -1`, no collision box); what shows is the
  particles of `randomDisplayTick`: asbestos gas throws a `townaura` speck in one of five display ticks (BlockGasAsbestos.java:24-29), and every
  gas block, radon included, throws a `vanillaExt` cloud in its colour only while the player wears the ash glasses on the head
  (BlockGasBase.java:139-155, `ArmorUtil.checkArmorPiece(p, ModItems.ashglasses, 3)`). Radon gas is therefore invisible bare-headed in the original.
  NEO has no ash glasses item; its gas blocks ask for a golden helmet instead (GasBaseBlock.java:99) and its asbestos gas throws an ash particle
  (GasAsbestosBlock.java:28), so the second uranium pass wears the golden helmet.
The ore is mined with real attack steps and an iron pickaxe in a survival game; the gas is read in the client's block states around the broken cell (it
starts to move 10 ticks after it appears), after the gas of the pass was cleared away before the break; the pictures are for a person.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='materials.outgas_visible',
    feature='materials',
    title='Mining uranium and asbestos ore in survival: the gas blocks left in the broken cells and the pictures right after',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

H = 'hbmsntm:'
Y = _lib.FLAT_FEET
Z = 0
PICK = 'minecraft:iron_pickaxe'
HELMET = 'minecraft:golden_helmet'
# (pass, ore, gas, x of the first ore of two, bare head or helmet)
PASSES = [
    ('uranium-bare', H + 'ore_uranium', H + 'gas_radon', 1600, None),
    ('uranium-helmet', H + 'ore_uranium', H + 'gas_radon', 1610, HELMET),
    ('asbestos-bare', H + 'ore_asbestos', H + 'gas_asbestos', 1620, None),
]
GAS_RADIUS = 6
ASBESTOS_LOOK = 'asbestos-bare'
HOLD = (33, 60, 90)       # an iron pickaxe on hardness 5.0: 6 / 5.0 / 30 = 0.04 a tick, 25 ticks, and the 5 ticks the client waits after a block broke; the longer holds only follow a miss


def expectations():
    E = [
        ('materials.ore-uranium-releases-radon',
         'two uranium ores mined by hand in survival with an iron pickaxe, bare-headed and again with a helmet on: each broken cell (or a cell within six blocks of it, the '
         'gas starts to move after 10 ticks) holds radon gas right after the break; a build that leaves air reads none',
         'original BlockOutgas.java:40-64,93-101'),
        ('materials.ore-asbestos-releases-asbestos-gas',
         'two asbestos ores mined the same way: each broken cell (or a cell within six blocks of it) holds asbestos gas right after the break',
         'original BlockOutgas.java:40-64,93-101'),
        ('materials.ore-uranium-gas-look-bare',
         'pictures right after the second uranium ore broke, bare-headed: the radon gas is invisible, the broken cell shows nothing (the original gas block has '
         'no model and throws particles only for a player wearing the ash glasses); a visible green cloud here would not be the original\'s',
         'original BlockGasBase.java:39-62,139-155'),
        ('materials.ore-uranium-gas-look-helmet',
         'pictures right after the second uranium ore broke with a golden helmet on (NEO\'s stand-in for the ash glasses): green cloud particles in and '
         'around the broken cell, more of them over the following pictures',
         'original BlockGasBase.java:139-155 (vanillaExt cloud in the gas colour 0.1 / 0.8 / 0.1 for radon); NEO GasBaseBlock.java:99'),
        ('materials.ore-asbestos-gas-look',
         'pictures right after the second asbestos ore broke, bare-headed: grey-white ash specks float in and around the broken cell',
         'original BlockGasAsbestos.java:24-29 (townaura particle, one display tick in five)'),
    ]
    return [dict(id=i, text=t, source=s) for i, t, s in E]


def focused(ctx, max_waits=900):
    """A held attack mines only while the client window has the focus: waits (1 s steps) until it is active, then opens and closes the inventory."""
    ctx.step('close', allow_fail=True)
    for _ in range(max_waits):
        if ctx.step('wait', ticks=20).get('window_active'):
            break
    else:
        raise RuntimeError('the client window had no focus for %d s: held attacks cannot mine' % max_waits)
    ctx.step('key', key='key.keyboard.e', after=4)
    ctx.step('close')


def stand(ctx, x, look, hide_gui=False):
    ctx.step('view', pos=[x + 0.5, Y, Z + 2.5], look_at=[look[0] + 0.5, look[1] + 0.5, look[2] + 0.5], fly=False, hide_gui=hide_gui)


def mine(ctx, x, ore):
    """Attacks the south face of the ore at (x, Y, Z) from two blocks south until it is gone; returns True when it broke."""
    pos = (x, Y, Z)
    for attempt in range(len(HOLD)):
        if attempt:
            focused(ctx)
        stand(ctx, x, pos)
        ctx.step('attack', target=dict(pos=list(pos), face='south'), hold=HOLD[attempt], after=0)
        if _lib.is_gone(ctx, pos, ore):
            return True
    return False


def clear_gas(ctx, pos, gas, radius=GAS_RADIUS + 2):
    """Removes the gas of the pass left around the ore (server), so that the gas read after the next break can only be that ore's."""
    ctx.server('fill %d %d %d %d %d %d minecraft:air replace %s' % (
        pos[0] - radius, pos[1] - 4, pos[2] - radius, pos[0] + radius, pos[1] + 8, pos[2] + radius, gas), allow_error=True)


def gas_cells(ctx, pos, gas):
    """The cells within GAS_RADIUS of the broken cell that hold the gas, in one snapshot of the client's block states; the gas starts to move 10 ticks after
    it appears, one cell every 2 ticks (a hold and the reads after it run a few more ticks)."""
    box = ctx.step('dump', **{'from': [pos[0] - GAS_RADIUS, max(pos[1] - GAS_RADIUS, _lib.FLAT_FEET - 4), pos[2] - GAS_RADIUS],
                              'to': [pos[0] + GAS_RADIUS, pos[1] + GAS_RADIUS, pos[2] + GAS_RADIUS]})
    return [tuple(int(c) for c in b['pos']) for b in box['blocks'] if b['block'] == gas]


def run(ctx):
    _lib.setup_world(ctx, freeze=False)
    ids = [e['id'] for e in expectations()]
    _lib.go_near(ctx, 1610, Y, Z)
    ctx.step('cmd', command='gamemode survival')
    _lib.give(ctx, (PICK, 1))
    _lib.hold(ctx, PICK)
    found = {}
    pictures = {}
    for name, ore, gas, x0, helmet in PASSES:
        for dx in (0, 2):
            ctx.step('cmd', command='setblock %d %d %d %s' % (x0 + dx, Y, Z, ore))
        ctx.step('cmd', command='item replace entity @s armor.head with %s' % (helmet or 'minecraft:air'))
        ctx.step('wait', ticks=10)
        focused(ctx)
        shots, cells = [], []
        for n, dx in enumerate((0, 2)):
            clear_gas(ctx, (x0 + dx, Y, Z), gas)
            broke = mine(ctx, x0 + dx, ore)
            near = gas_cells(ctx, (x0 + dx, Y, Z), gas) if broke else []
            cells.append((x0 + dx, broke, near))
            if n == 1 and broke:
                stand(ctx, x0 + dx, (x0 + dx, Y, Z), hide_gui=True)
                shots.append(ctx.step('shot', file=ctx.shot_name('%s-break' % name))['image']['file'])
                series = ctx.step('series', file=ctx.shot_name('%s-after' % name), count=3, interval=10)
                shots += [i['file'] for i in series['images']]
                if name == ASBESTOS_LOOK:
                    # the client picks about 667 random blocks of 33 x 33 x 33 around the player a tick for randomDisplayTick and the asbestos gas throws a speck
                    # in one display tick of five: one gas block shows a speck only about once in 270 ticks, so a patch of gas around the cell is filled in
                    ctx.step('cmd', command='fill %d %d %d %d %d %d %s replace minecraft:air' % (x0 + dx - 4, Y, Z - 2, x0 + dx + 4, Y + 3, Z + 1, gas))
                    ctx.step('wait', ticks=20)
                    patch = ctx.step('series', file=ctx.shot_name('%s-patch' % name), count=3, interval=10)
                    shots += [i['file'] for i in patch['images']]
        found[name] = cells
        pictures[name] = shots
        ctx.step('cmd', command='item replace entity @s armor.head with minecraft:air')
    ctx.step('cmd', command='gamemode creative')

    def verdict(passes):
        cells = [c for p in passes for c in found[p]]
        return all(broke and near for _, broke, near in cells), '; '.join(
            '%s ore at x %d: %s' % (p, x, 'did not break' if not broke else 'gas in %s' % (near or 'none'))
            for p in passes for x, broke, near in found[p])
    ok, detail = verdict(['uranium-bare', 'uranium-helmet'])
    ctx.check(ids[0], ok, detail + ' (radon gas = %sgas_radon)' % H)
    ok, detail = verdict(['asbestos-bare'])
    ctx.check(ids[1], ok, detail + ' (asbestos gas = %sgas_asbestos)' % H)
    for eid, name, text in (
            (ids[2], 'uranium-bare', 'uranium ore, bare head: first picture the moment after the break, then three more 10 ticks apart. Expected: the broken '
                                     'cell and the air around it look empty, no cloud and no specks'),
            (ids[3], 'uranium-helmet', 'uranium ore with a golden helmet on: first picture the moment after the break, then three more 10 ticks apart. '
                                       'Expected: green cloud particles in and around the broken cell'),
            (ids[4], 'asbestos-bare', 'asbestos ore, bare head: first picture the moment after the break, then three more 10 ticks apart. Expected: '
                                      'grey-white specks (ash particles) floating in and around the broken cell; the last three pictures are 20 ticks after a patch of asbestos gas '
                                      'blocks (9 x 4 x 4) was filled around the cell, which makes the specks frequent enough to see')):
        if pictures[name]:
            ctx.review(eid, text, pictures[name])
        else:
            ctx.not_run(eid, 'the second ore of the pass %s did not break, no pictures were taken' % name)
