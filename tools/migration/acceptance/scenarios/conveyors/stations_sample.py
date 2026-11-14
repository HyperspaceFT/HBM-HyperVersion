"""Sample user-station set (three stations) for stations.py: things only a person at a real keyboard and speaker can judge.

Not run by drive.py (group "station"); stations.py builds them into a corridor world, each with a sign and a reset button.
"""
SCENARIO = dict(
    id='conveyors.stations-sample',
    feature='conveyors',
    title='Sample stations: belt motion, a Shift tooltip with the physical key, a sound',
    group='station',
    station=True,
)

G = -60


def _belts(ctx, x, z):
    for n, t in enumerate(('conveyor', 'conveyor_express', 'conveyor_double', 'conveyor_triple')):
        for dz in range(5):
            ctx.step('cmd', command='setblock %d %d %d hbmsntm:%s[facing=north,shape=straight]' % (x + 2 * n, G, z + dz, t), wait_ticks=1)
    ctx.step('cmd', command='setblock %d %d %d minecraft:chest[facing=south]' % (x, G, z - 2))
    ctx.step('cmd', command='item replace block %d %d %d container.0 with minecraft:iron_ingot 64' % (x, G, z - 2))


def _crane(ctx, x, z):
    ctx.step('cmd', command='setblock %d %d %d minecraft:chest[facing=south]' % (x, G, z))
    ctx.step('cmd', command='item replace block %d %d %d container.0 with hbmsntm:crane_router 1' % (x, G, z))


def _sound(ctx, x, z):
    ctx.step('cmd', command='setblock %d %d %d minecraft:gold_block' % (x, G - 1, z))
    ctx.step('cmd', command='setblock %d %d %d minecraft:note_block[instrument=bell]' % (x, G, z))


STATIONS = [
    dict(id='conveyors.station-belt-motion', short=['BELT MOTION', 'drop iron', 'on each belt'],
         todo='Take the iron ingots from the chest and drop some on each of the four belts (Q).',
         expect='Items lie flat and slide south smoothly without jumping; faster on the express belt; no flicker.',
         build=_belts, size=(8, 2, 8)),
    dict(id='conveyors.station-router-shift', short=['SHIFT TIP', 'hold Shift', 'over router'],
         todo='Open the chest, point at the conveyor sorter (crane router) and hold the real Shift key; release it; switch to another app and back, then point at it again.',
         expect='Holding Shift replaces the "hold Shift" hint with the yellow description lines; releasing Shift brings the hint back; after switching apps Shift is not stuck.',
         build=_crane, size=(1, 1, 1)),
    dict(id='conveyors.station-sound', short=['SOUND', 'press the', 'reset button'],
         todo='Press the reset button on the command block, then right click the note block twice.',
         expect='A bell note you can hear, higher the second time.',
         build=_sound, size=(1, 1, 1)),
]


def expectations():
    return [dict(id=s['id'], text=s['expect'], source='user station') for s in STATIONS]
