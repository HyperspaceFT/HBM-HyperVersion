"""The press's progress bar at the end of the return stroke: the stamp's extension ends a return stroke below zero, and the bar the screen
draws from it is never negative.

Expected values follow the 1.7.10 original:
- the extension `press` is an int that the return stroke lowers by the stamp speed every tick and does not clamp
  (TileEntityMachinePress.java:87-94: `stampSpeed = speed * progressAtMax / maxSpeed` with progressAtMax 25 and maxSpeed 400, `press -= stampSpeed`,
  the stroke ends when `press <= 0` and waits 5 ticks); a stroke runs forward while `canProcess` (:99-119, a full stroke at 200, one operation of
  200 burn ticks), the speed rises by one a tick while it works (:73), and a burning coal adds 1,600 burn ticks after the stroke logic of the tick
  (:130-136). Replayed tick by tick from those lines, the first return stroke of a press with one coal, an iron-plate stamp and eight ingots ends at
  tick 125 with press -2, the next ones at 179 (-2), 223 (-1) and 262 (-4); `expected()` below does that replay.
- the screen draws `k = (int)(renderPress * 16 / maxPress)` rows of the bar (GUIMachinePress.java:54), `renderPress` the client's smoothed copy of the
  extension (TileEntityMachinePress.java:147-153). The extension reaches the client through the block entity packet and the client's own copy of
  `press` is not what the screen reads, so no dump shows the bar: the check compares the pictures. A press holding -20 is a state a stroke at full
  speed can end in (stamp speed up to 25); its bar must look like the one of a press holding 0, and a press holding +100 must look different
  (the control that the picture compare sees a drawn bar at all). The -20 is written with `data merge` on a press without fuel (nothing moves it
  afterwards), the others the same way.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import _lib  # noqa: E402
import baseline  # noqa: E402

SCENARIO = dict(
    id='press.press_bar',
    feature='press',
    title='Press progress bar: the return stroke ends below zero on the server, the bar the screen draws never does',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

H = 'hbmsntm:'
X, Z = 1500, 0
Y = _lib.FLAT_FEET
STAND = [X + 0.5, Y, Z + 3.5]
MAX_SPEED, PROGRESS_AT_MAX, MAX_PRESS = 400, 25, 200        # TileEntityMachinePress.java:27,28,36
COAL_BURN = 1600                                             # a coal in TileEntityFurnace.getItemBurnTime
FIRST_RETURN = 125                                           # replayed below
READ_FROM, READ_TO = 124, 131                                # ticks read around the first return stroke
BAR = (79, 32, 97, 53)                                       # gui px relative to the screen: the bar column (79..97, 35..51) with a row of margin above and below
MIN_BAR_PIXELS = 100                                         # the +100 bar (8 rows x 18 columns x 4 device pixels) must change at least this many pixels


def expectations():
    E = [
        ('press.return-stroke-below-zero',
         'a press with one coal, an iron-plate stamp and eight iron ingots, stepped tick by tick from a frozen world: its extension read on the server '
         'equals the replay of the original at ticks %d to %d, is still positive at tick %d and is -2 (below zero) at tick %d where the first return '
         'stroke ends, and stays there for the five ticks of the pause; a build that clamps the stroke at 0 reads 0' % (
             READ_FROM, READ_TO, FIRST_RETURN - 1, FIRST_RETURN),
         'original TileEntityMachinePress.java:73,87-94,99-119,130-136'),
        ('press.bar-never-negative',
         'the bar drawn for a press holding -20 (a return stroke at stamp speed 25 ends between -24 and 0) is pixel for pixel the bar of a press holding '
         '0, and the bar of a press holding +100 differs from it; a screen that draws the negative bar height changes a row above the bar',
         'original GUIMachinePress.java:54 (k = (int)(renderPress * 16 / maxPress)), TileEntityMachinePress.java:87-94'),
        ('press.bar-look',
         'the press screen with the stamp extension 0, +100 and -20: the bar column between the two slots is empty, half full, and empty again',
         'original GUIMachinePress.java:54-55'),
    ]
    return [dict(id=i, text=t, source=s) for i, t, s in E]


def expected(ticks):
    """The original's press, replayed tick by tick: {tick: (press, speed)} for a press with one coal, a stamp and eight ingots
    (TileEntityMachinePress.java:73-136)."""
    speed = press = burn = delay = 0
    retracting = False
    coal, ingots = 1, 8
    out = {}
    for t in range(1, ticks + 1):
        can = burn >= 200 and ingots > 0
        if (can or retracting) and burn >= 200:
            speed = min(speed + 1, MAX_SPEED)
        else:
            speed = max(speed - 1, 0)
        if delay <= 0:
            stamp_speed = speed * PROGRESS_AT_MAX // MAX_SPEED
            if retracting:
                press -= stamp_speed
                if press <= 0:
                    retracting = False
                    delay = 5
            elif can:
                press += stamp_speed
                if press >= MAX_PRESS:
                    ingots -= 1
                    retracting = True
                    delay = 5
                    if burn >= 200:
                        burn -= 200
            elif press > 0:
                retracting = True
        else:
            delay -= 1
        if burn < 200 and coal:
            burn += COAL_BURN
            coal -= 1
        out[t] = (press, speed)
    return out


def region(path, scale, left, top):
    """The bar column of a screenshot as rows of pixel tuples; `left` and `top` are the screen's origin in gui pixels."""
    width, height, bpp, rows = baseline.pixels(path)
    x0, y0, x1, y1 = (int(round(v * scale)) for v in (left + BAR[0], top + BAR[1], left + BAR[2], top + BAR[3]))
    stride = width * bpp
    return [[tuple(rows[y * stride + x * bpp:y * stride + x * bpp + 3]) for x in range(x0, x1)] for y in range(y0, y1)]


def changed(a, b, tolerance=2):
    return sum(1 for ra, rb in zip(a, b) for pa, pb in zip(ra, rb) if any(abs(i - j) > tolerance for i, j in zip(pa, pb)))


def merge(ctx, core, **fields):
    text = ','.join('%s:%s' % (k, v) for k, v in fields.items())
    ctx.server('data merge block %d %d %d {%s}' % (core + (text,)))


def run(ctx):
    _lib.setup_world(ctx, freeze=False)
    ids = [e['id'] for e in expectations()]
    _lib.go_near(ctx, X, Y, Z)
    ctx.step('cmd', command='setblock %d %d %d minecraft:stone' % (X, Y - 1, Z))
    _lib.give(ctx, (H + 'machine_press', 1))
    _lib.place(ctx, H + 'machine_press', (X, Y - 1, Z), 'up', STAND)
    core, _ = _lib.core_of(ctx, H + 'machine_press', (X - 2, Y, Z - 2), (X + 2, Y + 3, Z + 2))

    # the stroke on the server
    ctx.server('tick freeze')
    ctx.server('item replace block %d %d %d container.0 with minecraft:coal 1' % core)
    ctx.server('item replace block %d %d %d container.1 with %sstamp_iron_plate 1' % (core + (H,)))
    ctx.server('item replace block %d %d %d container.2 with minecraft:iron_ingot 8' % core)
    want = expected(READ_TO)
    got = {}
    _lib.advance(ctx, READ_FROM, 'press first stroke')
    got[READ_FROM] = _lib.block_data(ctx, core)
    for t in range(READ_FROM + 1, READ_TO + 1):
        _lib.server_steps(ctx, 1)
        got[t] = _lib.block_data(ctx, core)
    read = {t: (d.get('press'), d.get('speed')) for t, d in got.items()}
    differences = {t: (read[t], want[t]) for t in read if read[t] != want[t]}
    ctx.check(ids[0], not differences and want[FIRST_RETURN - 1][0] > 0 and want[FIRST_RETURN][0] == -2 and read[FIRST_RETURN][0] < 0
              and read[FIRST_RETURN - 1][0] > 0,
              'press (server) by tick %s; replay of the original %s; differences (read, replay) %s; core %s' % (
                  {t: v[0] for t, v in read.items()}, {t: want[t][0] for t in read}, differences or 'none', list(core)))

    # the bar on the client
    hud = _lib.open_gui(ctx, core, 'south', STAND, 'MachinePressScreen')
    shots = {}
    for label, value in (('zero', 0), ('half', 100), ('negative', -20)):
        merge(ctx, core, press=value, speed=0, burnTime=0, ret='0b')
        _lib.server_steps(ctx, 10)       # the client's copy of the extension approaches the synced value on the block entity's ticks, which a frozen world runs only while stepping
        ctx.step('wait', ticks=12)
        hud = ctx.step('hud', frames=2)
        image = ctx.step('shot', file=ctx.shot_name('bar-%s' % label))['image']
        shots[label] = (image['file'], hud['gui_left'], hud['gui_top'], _lib.block_data(ctx, core).get('press'),
                        image['width'] / hud['gui_scaled_width'])
    ctx.step('close')

    def pixels(label):
        file, left, top, press, factor = shots[label]
        return region(Path(ctx.channels[ctx.default].dir) / file, factor, left, top)
    zero, half, negative = pixels('zero'), pixels('half'), pixels('negative')
    # the bar column is the same place in all three pictures: the screen did not move between them
    same_place = len({(s[1], s[2]) for s in shots.values()}) == 1
    drawn, negative_vs_zero = changed(half, zero), changed(negative, zero)
    ctx.check(ids[1], same_place and [shots[k][3] for k in ('zero', 'half', 'negative')] == [0, 100, -20] and drawn >= MIN_BAR_PIXELS and negative_vs_zero == 0,
              'server press in the three pictures %s; screen origin %s; pixels of the bar region that differ from the 0 picture: +100 %d (at least %d expected, '
              'the control), -20 %d (0 expected); picture scale %.2f device pixels per gui pixel' % (
                  [shots[k][3] for k in ('zero', 'half', 'negative')], sorted({(s[1], s[2]) for s in shots.values()}), drawn, MIN_BAR_PIXELS,
                  negative_vs_zero, shots['zero'][4]),
              [shots[k][0] for k in ('zero', 'half', 'negative')])
    ctx.review(ids[2], 'press screen with the stamp extension 0, +100 and -20 (pictures in that order): the arrow-shaped bar column between the stamp '
                       'slot above and the input slot below is empty in the first, filled about halfway from the top in the second, and empty again in '
                       'the third, with no stripe above the column', [shots[k][0] for k in ('zero', 'half', 'negative')])
    ctx.step('cmd', command='fill %d %d %d %d %d %d minecraft:air' % (X - 2, Y, Z - 2, X + 2, Y + 3, Z + 2))
