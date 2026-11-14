"""Items on belts as the client sees them: lying flat or upright, smooth motion, how far away they are drawn.

Expected values follow the 1.7.10 original at cd0cff450 and the NEO differences stated in the NEO delivery:
- items lie flat on the belt and blocks stand upright (RenderMovingItem: item sprites are rotated flat, blocks are not);
  a person judges the picture.
- motion: the client interpolates between server positions; NEO syncs every 3 ticks (the original every tick with a
  velocity), so the rendered positions must move forward only (no backward jumps) with small steps.
- drawing distance: moving items keep the original size 0.375 (EntityMovingItem.java:23) and do not override the entity
  view distance, so the client draws them up to size x 64 x view scale (vanilla Entity.shouldRenderAtSqrDistance): 24
  blocks at entity distance 100 %, 120 at 500 % with render distance 8. In single-player the integrated server scales
  the tracking range (6 chunks) by the same option, so at 500 % the limit seen is the drawing one.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='conveyors.moving-items',
    feature='conveyors',
    title='Moving items: lying flat, smooth motion, drawing distance',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70, hide_gui=True),
)

Y = -60
TYPES = ('conveyor', 'conveyor_express', 'conveyor_double', 'conveyor_triple')


def expectations():
    items = [dict(id='conveyors.item-pose', text='an ingot and a tool lie flat on the belt, a block stands upright', source='RenderMovingItem (1.7.10)')]
    items += [dict(id='conveyors.smooth-%s' % t, text='%s: rendered item positions only move forward, steps under 0.2 block per frame' % t,
                   source='NEO: 3-tick sync with client interpolation (deliberate difference)') for t in TYPES]
    items.append(dict(id='conveyors.smooth-path', text='one item through a right and a left bend, up a three-high lift, along its top and down a chute: '
                      'the rendered positions never step back, steps under 0.35 block per frame (chutes are the fastest piece), it rises '
                      'two blocks and comes down again', source='NEO: 3-tick sync with client interpolation (deliberate difference)'))
    items.append(dict(id='conveyors.lift-exit', text='three-high vertical conveyors facing north, east, south and west: the top piece is the '
                      'half-high top and an item fed in at the bottom rises two blocks and leaves the top toward the side opposite its '
                      'facing (the side away from its input)', source='BlockConveyorLift.java:34-45; BlockConveyorBase.java:61-75; RenderConveyorLift.java:121-136'))
    items += [dict(id='conveyors.draw-far', text='entity distance 500 %: drawn at 80 and 116 blocks, not at 126 (limit 0.375 x 64 x 5 = 120)',
                   source='vanilla entity view distance by bounding box (moving items do not override it)'),
              dict(id='conveyors.draw-near', text='entity distance 100 %: drawn up to about 24 blocks (0.375 x 64), not beyond',
                   source='vanilla entity view distance by bounding box')]
    return items


def summon(ctx, x, z, item):
    ctx.step('cmd', command='summon minecraft:item %.1f %d %.1f {Item:{id:"%s",count:1},PickupDelay:32767}' % (x, Y + 1, z, item))


def moving(ctx, a, b):
    d = ctx.step('dump', **{'from': a, 'to': b}, entities=True, allow_unloaded=True)
    return [e for e in d.get('entities', []) if e['type'] == 'hbmsntm:moving_item']


def run(ctx):
    _lib.setup_world(ctx, freeze=False)
    # four lines of 40 belts along +x (input west), one per type
    for i, t in enumerate(TYPES):
        ctx.step('cmd', command='fill 0 %d %d 39 %d %d hbmsntm:%s[facing=west,shape=straight]' % (Y, 4 * i, Y, 4 * i, t))
    ctx.step('view', pos=[2.5, Y + 3, -4.5], look_at=[6.5, Y, 2.5], hide_gui=True)
    _lib.placed(ctx)
    summon(ctx, 1.5, 0.5, 'minecraft:iron_ingot')
    summon(ctx, 3.5, 0.5, 'minecraft:stone')
    summon(ctx, 5.5, 0.5, 'minecraft:iron_pickaxe')
    for i in range(1, 4):
        summon(ctx, 1.5, 4 * i + 0.5, 'minecraft:iron_ingot')
    ctx.step('wait', ticks=20)
    ctx.step('view', eye=[5.5, Y + 1.6, -1.6], look_at=[5.5, Y + 0.2, 0.5], hide_gui=True)
    ctx.step('wait', ticks=2)
    ctx.review('conveyors.item-pose', 'ingot, stone and pickaxe on the regular belt', [ctx.step('shot', file=ctx.shot_name('pose'))['image']['file']])
    track = ctx.step('track', center=[20, Y + 0.5, 6], radius=30, type='hbmsntm:moving_item', ticks=60)
    by_lane = {}
    for e in track.get('entities', []):
        lane = int(round((e['first'][2] - 0.5) / 4))
        by_lane.setdefault(lane, []).append(e)
    for i, t in enumerate(TYPES):
        es = by_lane.get(i, [])
        ok = bool(es) and all(e['reversals'] == 0 and e['max_step'] < 0.2 and e['last'][0] > e['first'][0] for e in es)
        ctx.check('conveyors.smooth-%s' % t, ok, '; '.join('frames %d max_step %.3f mean %.4f reversals %d x %.2f->%.2f' % (
            e['frames'], e['max_step'], e['mean_step'], e['reversals'], e['first'][0], e['last'][0]) for e in es) or 'no item tracked')
    smooth_path(ctx)
    lift_exit(ctx)
    # drawing distance: the server tracks a moving item 6 chunks far (96 blocks); the client draws an entity while its
    # distance is below bounding-box size x 64 x view scale, the view scale being entityDistanceScaling times
    # clamp(renderDistance / 8, 1, 2.5) (vanilla); render distance 8 keeps that factor at 1
    ctx.step('option', name='renderDistance', value=8)
    ctx.step('view', pos=[250.5, Y + 2, 3.5], look_at=[250, Y, 0.5], hide_gui=True)
    ctx.step('wait', ticks=100)  # chunks around the new spot load first
    ctx.step('cmd', command='fill 200 %d 0 299 %d 0 hbmsntm:conveyor[facing=west,shape=straight]' % (Y, Y))
    ctx.step('option', name='entityDistanceScaling', value=5.0)
    ctx.step('view', pos=[202.5, Y + 2, 3.5], look_at=[210, Y, 0.5], hide_gui=True)
    _lib.placed(ctx)
    summon(ctx, 200.5, 0.5, 'minecraft:iron_ingot')
    ctx.step('wait', ticks=10)
    seen = {}
    for dist in (80, 116, 126):
        ix = moving(ctx, [195, Y - 1, -2], [300, Y + 2, 2])
        x = ix[0]['pos'][0] if ix else 210
        ctx.step('view', pos=[x - dist, Y + 1, 0.5], look_at=[x, Y, 0.5], hide_gui=True)
        ctx.step('wait', ticks=10)
        es = moving(ctx, [195, Y - 1, -2], [300, Y + 2, 2])
        seen[dist] = [(round(e['pos'][0] - (x - dist), 1), e.get('in_render_distance')) for e in es]
    # at 126 the item must still be tracked (present, not drawn): an untracked item would pass for the wrong reason
    far = all(d for _, d in seen[80]) and seen[80] and all(d for _, d in seen[116]) and seen[116] and seen[126] and not any(d for _, d in seen[126])
    ctx.check('conveyors.draw-far', bool(far), '(distance, drawn) per stand point (entity distance 500 %%, render distance 8, limit 120): %s' % seen)
    ctx.step('option', name='entityDistanceScaling', value=1.0)
    ctx.step('cmd', command='tick freeze')  # drawing only: the item stays put while the camera steps away
    x = moving(ctx, [195, Y - 1, -2], [300, Y + 2, 2])[0]['pos'][0]
    flags = []
    for dist in range(12, 41, 2):
        ctx.step('view', pos=[x - dist, Y + 1, 0.5], look_at=[x, Y, 0.5], hide_gui=True)
        ctx.step('wait', ticks=2)
        es = moving(ctx, [195, Y - 1, -2], [300, Y + 2, 2])
        flags.append((dist, bool(es and es[0].get('in_render_distance'))))
    ctx.step('cmd', command='tick unfreeze')
    drawn = [d for d, f in flags if f]
    ctx.check('conveyors.draw-near', bool(drawn) and 22 <= max(drawn) <= 24 and all(f == (d <= max(drawn)) for d, f in flags),
              'entity distance 100 %%, render distance 8 (limit 24): drawn up to %s blocks; %s' % (max(drawn) if drawn else None, flags))
    ctx.step('option', name='renderDistance', value=12)


STEP = dict(north=(0, -1), south=(0, 1), east=(1, 0), west=(-1, 0))


def lift_exit(ctx):
    """One three-high lift per facing; a belt on the lift's input side carries an item in; it must come out of the top
    toward the opposite side."""
    x0, z0 = 440, 44
    ctx.step('view', pos=[x0 + 12.5, Y + 10, z0 + 0.5], pitch=80.0, yaw=180.0, hide_gui=True)
    ctx.step('wait', ticks=60)
    cols = []
    for i, f in enumerate(('north', 'east', 'south', 'west')):
        x, z = x0 + 8 * i, z0
        dx, dz = STEP[f]
        for dy in range(3):
            ctx.step('cmd', command='setblock %d %d %d hbmsntm:conveyor_lift[facing=%s]' % (x, Y + dy, z, f))
        ctx.step('cmd', command='setblock %d %d %d minecraft:stone' % (x, Y + 3, z))
        ctx.step('cmd', command='setblock %d %d %d minecraft:air' % (x, Y + 3, z))
        ctx.step('cmd', command='setblock %d %d %d hbmsntm:conveyor[facing=%s,shape=straight]' % (x + dx, Y, z + dz, f))
        cols.append((f, x, z))
    _lib.placed(ctx)
    for f, x, z in cols:
        dx, dz = STEP[f]
        summon(ctx, x + dx + 0.5, z + dz + 0.5, 'minecraft:iron_ingot')
    track = ctx.step('track', center=[x0 + 12, Y + 1, z0], radius=16, type='hbmsntm:moving_item', ticks=200)
    parts = {}
    for f, x, z in cols:
        top = ctx.step('dump', **{'from': [x, Y + 2, z], 'to': [x, Y + 2, z]})['blocks']
        parts[f] = top[0]['props'].get('part') if top else None
    got, ok = {}, True
    for f, x, z in cols:
        dx, dz = STEP[f]
        es = [e for e in track.get('entities', []) if abs(e['first'][0] - (x + 0.5)) < 2.5]
        e = max(es, key=lambda v: v['frames']) if es else None
        if e is None:
            got[f], ok = 'no item tracked', False
            continue
        ox, oz = e['last'][0] - (x + 0.5), e['last'][2] - (z + 0.5)
        out = -(dx * ox + dz * oz)  # distance travelled toward the side opposite the facing
        side = abs(dz * ox + dx * oz)
        got[f] = 'highest y %.2f, last offset (%.2f, %.2f), out %.2f' % (e.get('max_y', float('nan')), ox, oz, out)
        ok = ok and e.get('max_y', 0) >= Y + 2 and out > 0.2 and side < 0.2 and parts[f] == 'top'
    ctx.check('conveyors.lift-exit', ok, 'top pieces %s; items %s' % (parts, got))


def smooth_path(ctx):
    """Items travel north (a belt's facing names the side its items come from); right bend, left bend, lift, top, chute."""
    x = 500
    # the chunks over there load first, or the commands are refused
    ctx.step('view', pos=[x + 7.5, Y + 3, 27.5], look_at=[x + 2, Y + 1, 26.5], hide_gui=True)
    ctx.step('wait', ticks=60)
    cmds = ['fill %d %d 30 %d %d 32 hbmsntm:conveyor[facing=south,shape=straight]' % (x, Y, x, Y),
            'setblock %d %d 29 hbmsntm:conveyor[facing=south,shape=right]' % (x, Y),
            'setblock %d %d 29 hbmsntm:conveyor[facing=west,shape=straight]' % (x + 1, Y),
            'setblock %d %d 29 hbmsntm:conveyor[facing=west,shape=left]' % (x + 2, Y),
            'setblock %d %d 28 hbmsntm:conveyor[facing=south,shape=straight]' % (x + 2, Y)]
    cmds += ['setblock %d %d 27 hbmsntm:conveyor_lift[facing=south]' % (x + 2, Y + dy) for dy in range(3)]
    cmds += ['setblock %d %d %d hbmsntm:conveyor[facing=south,shape=straight]' % (x + 2, Y + 2, z) for z in (26, 25)]
    cmds += ['setblock %d %d 24 hbmsntm:conveyor_chute' % (x + 2, Y + dy) for dy in (1, 2)]
    cmds += ['fill %d %d 21 %d %d 24 hbmsntm:conveyor[facing=south,shape=straight]' % (x + 2, Y, x + 2, Y)]
    for c in cmds:
        ctx.step('cmd', command=c)
    # setblock does not update the placed block's own shape: a block put on top and taken away again updates the lift
    # top and the chute pieces
    for z in (27, 26, 25, 24):
        ctx.step('cmd', command='setblock %d %d %d minecraft:stone' % (x + 2, Y + 3, z))
        ctx.step('cmd', command='setblock %d %d %d minecraft:air' % (x + 2, Y + 3, z))
    ctx.step('view', pos=[x + 7.5, Y + 3, 27.5], look_at=[x + 2, Y + 1, 26.5], hide_gui=True)
    _lib.placed(ctx)
    summon(ctx, x + 0.5, 32.5, 'minecraft:iron_ingot')
    track = ctx.step('track', center=[x + 1, Y + 1, 27], radius=12, type='hbmsntm:moving_item', ticks=420)
    es = track.get('entities', [])
    e = max(es, key=lambda v: v['frames']) if es else None
    ok = (e is not None and e['reversals'] == 0 and e['max_step'] < 0.35 and e.get('max_y', e['last'][1]) >= Y + 2
          and e['last'][1] < Y + 1 and e['last'][2] < 24.5)
    ctx.check('conveyors.smooth-path', ok, ('frames %d max_step %.3f mean %.4f reversals %d from %s to %s, highest y %s; window active %s' % (
        e['frames'], e['max_step'], e['mean_step'], e['reversals'], [round(v, 2) for v in e['first']], [round(v, 2) for v in e['last']],
        e.get('max_y'), track.get('window_active'))) if e else 'no item tracked')

