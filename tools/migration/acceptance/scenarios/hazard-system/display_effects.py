"""Client display effects of radioactive blocks: radiation fog specks, schrabidium sparkles, steam of hot blocks; pictures for a person.

Expected values follow the 1.7.10 original:
- a block with the radiation-fog effect throws one `townaura` speck next to every air neighbour per display tick (BlockHazard.java:45-108,
  `ExtDisplayEffect.RADFOG`); block_plutonium and block_waste are two of them (ModBlocks.java). NEO HazardBlock.java:54-82 throws the
  mycelium particle, the 1.21 name of `townaura`.
- block_schrabidium throws the cyan `schrabfog` sparkle in the same places (BlockHazard.java:94-104, ClientProxy.java:1699-1704);
  NEO HazardBlock.java:74-81 and NuclearTechModClient's `schrabfog` effect.
- block_polonium and block_pu238 are hot blocks: a white `cloud` puff on top while it rains on the cell above, and next to every
  side or top neighbour that holds water (BlockHotHazard.java:11-46); NEO HotHazardBlock.java. block_pu238 gives light 5
  (ModBlocks.java:1352: setLightLevel(5F / 15F)).
- block_uranium has no display effect (plain BlockHazard without ExtDisplayEffect).
Particles are client-only and the executor has no particle read, so every row is a picture for a person. The world runs (a frozen
world stops particles). A radioactive block raises its chunk fast (polonium 75 a block tick) and a chunk above 100 throws the chunk
radiation fog (ChunkRadiationHandlerSimple, config fogRad 100) that would hide the block, so every setup gets a chunk of its own, three
chunks from the next, is placed right before its pictures (night, then noon; the rain setups at noon in the rain) and removed after them.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='hazard-system.display_effects',
    feature='hazard-system',
    title='Radioactive blocks: radiation fog, schrabidium sparkles, steam of hot blocks next to water and in the rain, uranium as control',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

H = 'hbmsntm:'
Y = _lib.FLAT_FEET
Z = 0
UP = Y + 2          # floating blocks: every neighbour is air
X0 = 1208           # the middle of chunk x 75; far from player_placed (x 2800-3000), whose yellowcake row needs a chunk with no
                    # radiation, and the removed blocks here leave their chunk radiation behind
GAP = 48            # three chunks between setups
# (name, block, x, setup): 'air' floats the block with air all round; 'water' puts it on the ground with a water source on its
# west side; 'rain' puts it on the ground under open sky for the rain pass
SETUPS = [(name, block, X0 + i * GAP, kind) for i, (name, block, kind) in enumerate([
    ('plutonium', H + 'block_plutonium', 'air'),
    ('waste', H + 'block_waste', 'air'),
    ('schrabidium', H + 'block_schrabidium', 'air'),
    ('uranium', H + 'block_uranium', 'air'),
    ('polonium-water', H + 'block_polonium', 'water'),
    ('pu238-water', H + 'block_pu238', 'water'),
    ('polonium-rain', H + 'block_polonium', 'rain'),
    ('pu238-rain', H + 'block_pu238', 'rain'),
])]
LIGHT_X = X0 + len(SETUPS) * GAP


def expectations():
    E = [
        ('hazard-system.display-radfog',
         'block_plutonium and block_waste floating in air, at night and at noon: small grey specks (mycelium, the original townaura) appear in the air '
         'cells right around each block and drift a little',
         'original BlockHazard.java:45-108; NEO HazardBlock.java:54-82'),
        ('hazard-system.display-schrab',
         'block_schrabidium floating in air: small cyan sparkles around the block (the original schrabfog), not grey specks',
         'original BlockHazard.java:94-104, ClientProxy.java:1699-1704; NEO HazardBlock.java:74-81, NuclearTechModClient (schrabfog)'),
        ('hazard-system.display-none-uranium',
         'block_uranium floating in air (control): no particles around it at night or at noon',
         'original BlockHazard (no ExtDisplayEffect for block_uranium)'),
        ('hazard-system.display-hot-water',
         'block_polonium and block_pu238 with a water source on their west side: white cloud puffs on the water side of each block',
         'original BlockHotHazard.java:30-44; NEO HotHazardBlock.java'),
        ('hazard-system.display-hot-rain',
         'block_polonium and block_pu238 under open sky while it rains: white cloud puffs on the top face of each block',
         'original BlockHotHazard.java:21-28; NEO HotHazardBlock.java'),
        ('hazard-system.display-pu238-light',
         'at night block_pu238 lights the ground and the water around it (light 5); block_polonium next to it does not',
         'original ModBlocks.java:1352'),
    ]
    return [dict(id=i, text=t, source=s) for i, t, s in E]


def put(ctx, setup, on=True):
    """Places (or removes) one setup's block and water."""
    name, block, x, kind = setup
    y = UP if kind == 'air' else Y
    ctx.step('cmd', command='setblock %d %d %d %s' % (x, y, Z, block if on else 'minecraft:air'))
    if kind == 'water':
        ctx.step('cmd', command='setblock %d %d %d %s' % (x - 1, Y, Z, 'minecraft:water' if on else 'minecraft:air'))


def look(ctx, x, y, distance=3.0, hide_gui=True):
    ctx.step('view', pos=[x + 0.5, y - 0.6, Z + 0.5 + distance], look_at=[x + 0.5, y + 0.5, Z + 0.5], fly=True, hide_gui=hide_gui)


def series(ctx, name, tag, count):
    ctx.step('wait', ticks=30)
    return [i['file'] for i in ctx.step('series', file=ctx.shot_name('%s-%s' % (name, tag)), count=count, interval=10)['images']]


def run(ctx):
    _lib.setup_world(ctx, freeze=False)
    ids = [e['id'] for e in expectations()]
    night, noon, rain = {}, {}, {}
    for setup in SETUPS:
        name, block, x, kind = setup
        y = UP if kind == 'air' else Y
        _lib.go_near(ctx, x, Y, Z)
        if kind == 'rain':
            ctx.step('cmd', command='time set 6000')
            ctx.step('cmd', command='weather rain')
            ctx.step('wait', ticks=100)         # the rain level ramps up over about 100 ticks
        look(ctx, x, y)
        put(ctx, setup)
        if kind == 'rain':
            rain[name] = series(ctx, name, 'rain', 3)
            ctx.step('cmd', command='weather clear')
        else:
            ctx.step('cmd', command='time set 18000')
            night[name] = series(ctx, name, 'night', 3)
            ctx.step('cmd', command='time set 6000')
            noon[name] = series(ctx, name, 'noon', 2)
        put(ctx, setup, on=False)
    # a wide night picture of both hot blocks next to water: pu238 lights its surroundings, polonium does not
    pair = [('light-polonium', H + 'block_polonium', LIGHT_X, 'water'), ('light-pu238', H + 'block_pu238', LIGHT_X + 4, 'water')]
    _lib.go_near(ctx, LIGHT_X + 2, Y, Z)
    ctx.step('cmd', command='time set 18000')
    ctx.step('view', pos=[LIGHT_X + 2.5, Y + 1.5, Z + 6.5], look_at=[LIGHT_X + 2.5, Y + 0.5, Z + 0.5], fly=True, hide_gui=True)
    for setup in pair:
        put(ctx, setup)
    ctx.step('wait', ticks=30)
    light = [ctx.step('shot', file=ctx.shot_name('light-night'))['image']['file']]
    for setup in pair:
        put(ctx, setup, on=False)
    ctx.step('cmd', command='time set 6000')

    def both(names, *sets):
        return [f for n in names for s in sets for f in s.get(n, [])]

    ctx.review(ids[0], 'block_plutonium, then block_waste, each floating in air: three pictures at night 10 ticks apart, two at noon. Expected: small '
                       'grey specks in the air cells right around each block', both(['plutonium', 'waste'], night, noon))
    ctx.review(ids[1], 'block_schrabidium floating in air: three pictures at night, two at noon. Expected: small cyan sparkles around the block',
               both(['schrabidium'], night, noon))
    ctx.review(ids[2], 'block_uranium floating in air (control): three pictures at night, two at noon. Expected: nothing around the block',
               both(['uranium'], night, noon))
    ctx.review(ids[3], 'block_polonium, then block_pu238, on the ground with a water source on the west (left) side: three pictures at night, two '
                       'at noon. Expected: white cloud puffs on the water side', both(['polonium-water', 'pu238-water'], night, noon))
    ctx.review(ids[4], 'block_polonium, then block_pu238, on the ground under open sky in the rain: three pictures each. Expected: white cloud '
                       'puffs on the top face', both(['polonium-rain', 'pu238-rain'], rain))
    ctx.review(ids[5], 'night, both hot blocks next to their water from the south (polonium left, pu238 right) and the night series of each. '
                       'Expected: the ground and water around block_pu238 are lit, around block_polonium dark',
               light + both(['polonium-water', 'pu238-water'], night))
