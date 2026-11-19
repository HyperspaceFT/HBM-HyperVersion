"""Meltdown gas lets out dense radon into the air next to it.

Expected values follow the 1.7.10 original: every update of a meltdown gas block picks one of the six directions at random and, one
time in seven, puts dense radon into that neighbour when it is air (BlockGasMeltdown.java:75-79); NEO GasMeltdownBlock.java:67-88.
The gas also moves (into an air neighbour) and vanishes one update in 350, and dense radon itself fades, so the gas is shut in a
stone room of 3 x 3 x 3 air cells, four rooms side by side, each with one meltdown gas block in the middle and nothing else; the
rooms are read every 20 ticks for 1,200 ticks. Inside a closed room any dense radon can only come from the meltdown gas. A room's
cells always have at least three air or gas neighbours inside the room, so an update leaves dense radon with chance >= 3/42 while
the room has air; the gas updates every 2 ticks (GasBaseBlock delay), and a room whose gas vanishes before any dense radon does so with
chance about (1/350) / (1/14 + 1/350) = 4 %, so all four rooms failing together is below 1e-5 from that cause.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='hazard-system.meltdown_gas_radon',
    feature='hazard-system',
    title='Meltdown gas in closed stone rooms: dense radon appears in the air cells next to it',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

H = 'hbmsntm:'
Y = _lib.FLAT_FEET
X0, Z0 = 3400, 0
ROOMS = 4
STEP = 6            # rooms side by side along x; each room's walls span 5 blocks
READS, EVERY = 60, 20


def expectations():
    return [dict(id='hazard-system.meltdown-gas-dense-radon',
                 text='four closed stone rooms of 3 x 3 x 3 air cells, a meltdown gas block in the middle of each: within 1,200 ticks dense radon '
                      '(gas_radon_dense) appears inside at least one room (reads every 20 ticks); the gas that let it out is still in that room or '
                      'was there at the read before',
                 source='original BlockGasMeltdown.java:75-79; NEO GasMeltdownBlock.java:67-88')]


def room(i):
    """(lo, hi) of room i's inner air cells."""
    x = X0 + i * STEP
    return (x, Y + 1, Z0), (x + 2, Y + 3, Z0 + 2)


def run(ctx):
    _lib.setup_world(ctx, freeze=False)
    eid = expectations()[0]['id']
    _lib.go_near(ctx, X0 + 10, Y, Z0)
    ctx.step('view', pos=[X0 + 10.5, Y + 2, Z0 - 6.5], look_at=[X0 + 10.5, Y + 2, Z0 + 1], fly=True, hide_gui=False)
    ctx.step('wait', ticks=40)      # the chunks around a far teleport need a moment on the server before setblock accepts them
    for i in range(ROOMS):
        lo, hi = room(i)
        for attempt in range(10):
            r = ctx.server('fill %d %d %d %d %d %d minecraft:stone hollow' % (lo[0] - 1, lo[1] - 1, lo[2] - 1, hi[0] + 1, hi[1] + 1, hi[2] + 1),
                           allow_error=True)
            if _lib.is_block(ctx, (lo[0] - 1, lo[1] - 1, lo[2] - 1), 'minecraft:stone'):
                break
            ctx.step('wait', ticks=20)
        ctx.server('setblock %d %d %d %sgas_meltdown' % (lo[0] + 1, lo[1] + 1, lo[2] + 1, H))
    t0 = ctx.server()['game_time']
    first = {}
    gas_seen = {i: True for i in range(ROOMS)}
    timeline = []
    for n in range(READS):
        ctx.step('wait', ticks=EVERY)
        t = ctx.server()['game_time'] - t0
        row = []
        for i in range(ROOMS):
            lo, hi = room(i)
            box = ctx.step('dump', **{'from': list(lo), 'to': list(hi)})
            kinds = [b['block'] for b in box['blocks']]
            radon, gas = kinds.count(H + 'gas_radon_dense'), kinds.count(H + 'gas_meltdown')
            if radon and i not in first:
                first[i] = dict(tick=t, radon=radon, gas=gas, gas_before=gas_seen[i])
            gas_seen[i] = gas > 0
            row.append((radon, gas))
        if n % 10 == 9:
            timeline.append((t, row))
        if len(first) == ROOMS:
            timeline.append((t, row))
            break
    ok = bool(first) and all(f['gas'] or f['gas_before'] for f in first.values())
    ctx.check(eid, ok, 'rooms with dense radon (first read: ticks since the gas was set, radon cells, meltdown gas cells, gas at the read before): %s; '
                       '%d of %d rooms; timeline (ticks, [(radon, gas)] per room): %s' % (first or 'none', len(first), ROOMS, timeline))
