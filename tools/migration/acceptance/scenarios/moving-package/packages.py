"""Packages on belts: look and motion, and what a package, a partitioner and a boxer keep when the world is reopened.

Expected values follow the 1.7.10 original at cd0cff450 and the NEO port:
- a package moves along belts like a moving item (EntityMovingConveyorObject), forward only, through turns; NEO draws a
  0.5-block crate (deliberate NEO difference; the size against the original is the user's call at a station).
- saved state (EntityMovingPackage.java:102-132; TileEntityCranePartitioner; TileEntityCraneBoxer.java:41-149 with
  lastRedstone saved): a package keeps its stacks, a partitioner its queued inputs and stored items, and a boxer in
  redstone mode with the signal still on does not pack again after the world is reopened.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='moving-package.packages',
    feature='moving-package',
    title='Packages: motion and look on belts; package, partitioner and boxer state across reopening the world',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70, hide_gui=True),
)

Y = -60
OX = 1100
RING = [(0, 0, 'south', 'right'), (1, 0, 'west', 'straight'), (2, 0, 'west', 'right'), (2, 1, 'north', 'straight'),
        (2, 2, 'north', 'right'), (1, 2, 'east', 'straight'), (0, 2, 'east', 'right'), (0, 1, 'south', 'straight')]


def expectations():
    E = [('motion', 'a package runs a straight belt and a turn forward only, steps under 0.2 block per frame', 'EntityMovingConveyorObject (shared with items)'),
         ('look', 'the package is a crate sitting on the belt, not sunk into it, also in the turn', 'NEO crate 0.5 block'),
         ('path', 'a package through a right and a left bend, up a three-high vertical conveyor, along its top and down a chute: never '
          'steps back, steps under 0.35 block per frame, rises two blocks and comes down past the chute',
          'EntityMovingConveyorObject.onUpdate (items and packages share it); BlockConveyorLift; BlockConveyorChute'),
         ('pick', 'the crosshair selects a package on a belt (the pick is the entity), and right-clicking it gives its contents to the player',
          'EntityMovingConveyorObject.canBeCollidedWith; EntityMovingPackage.java:40-54'),
         ('reload-package', 'a package circling a ring keeps its 4 stacks after the world is reopened', 'EntityMovingPackage.java:102-132'),
         ('reload-partitioner', 'a partitioner keeps 8 queued oil scrap and 3 stored cobblestone after the world is reopened', 'TileEntityCranePartitioner'),
         ('reload-boxer', 'a redstone-mode boxer with the signal on packs once and not again after the world is reopened', 'TileEntityCraneBoxer.java:41-149')]
    return [dict(id='moving-package.' + i, text=t, source=s) for i, t, s in E]


def cmd(ctx, command, **kw):
    return ctx.step('cmd', command=command, **kw)


def text_of(r):
    return ' '.join(m['text'] for m in r.get('messages', []))


def counts(text, item):
    n = 0
    for entry in re.findall(r'\{[^{}]*id:\s*"%s"[^{}]*\}' % re.escape(item), text):
        m = re.search(r'count:\s*(\d+)', entry)
        n += int(m.group(1)) if m else 1
    return n


def packages(ctx, a, b):
    return [e for e in ctx.step('dump', **{'from': a, 'to': b}, entities=True)['entities'] if e['type'] == 'hbmsntm:moving_package']


def summon_package(ctx, x, z, stacks):
    contents = ','.join('{slot:%db,id:"%s",count:%d}' % (i, item, n) for i, (item, n) in enumerate(stacks))
    cmd(ctx, 'summon hbmsntm:moving_package %.1f %.2f %.1f {count:%d,contents:[%s]}' % (x, Y + 0.25, z, len(stacks), contents))


def package_path(ctx):
    """the moving_items smooth-path route (conveyors.smooth-path) with a package: items travel north"""
    x = OX + 60
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
        cmd(ctx, c)
    for z in (27, 26, 25, 24):  # a block put on top and taken away updates the lift top and the chute pieces
        cmd(ctx, 'setblock %d %d %d minecraft:stone' % (x + 2, Y + 3, z))
        cmd(ctx, 'setblock %d %d %d minecraft:air' % (x + 2, Y + 3, z))
    ctx.step('view', pos=[x + 7.5, Y + 3, 27.5], look_at=[x + 2, Y + 1, 26.5], hide_gui=True)
    _lib.placed(ctx)
    summon_package(ctx, x + 0.5, 32.5, [('minecraft:cobblestone', 64)])
    track = ctx.step('track', center=[x + 1, Y + 1, 27], radius=12, type='hbmsntm:moving_package', ticks=420)
    es = track.get('entities', [])
    e = max(es, key=lambda v: v['frames']) if es else None
    ok = (e is not None and e['reversals'] == 0 and e['max_step'] < 0.35 and e.get('max_y', e['last'][1]) >= Y + 2
          and e['last'][1] < Y + 1 and e['last'][2] < 24.5)
    ctx.check('moving-package.path', ok, ('frames %d max_step %.3f reversals %d from %s to %s, highest y %s' % (
        e['frames'], e['max_step'], e['reversals'], [round(v, 2) for v in e['first']], [round(v, 2) for v in e['last']],
        e.get('max_y'))) if e else 'no package tracked')
    cmd(ctx, 'kill @e[type=hbmsntm:moving_package]', allow_error=True)


def package_pick(ctx):
    x = OX + 50
    cmd(ctx, 'fill %d %d 0 %d %d 0 hbmsntm:conveyor[facing=west,shape=straight]' % (x, Y, x + 6, Y))
    cmd(ctx, 'clear @s', allow_error=True)
    _lib.placed(ctx)
    summon_package(ctx, x + 1.5, 0.5, [('minecraft:cobblestone', 5)])
    ctx.step('wait', ticks=30)
    p = packages(ctx, [x - 1, Y - 1, -1], [x + 7, Y + 1, 1])
    hit, got, left = None, 0, None
    if p:
        px, py, pz = p[0]['pos']
        cmd(ctx, 'tick freeze')
        ctx.step('view', eye=[px, py + 1.2, pz + 1.4], look_at=[px, py + 0.25, pz], fly=True, hide_gui=False)
        ctx.step('wait', ticks=3)
        hit = ctx.step('use', after=6).get('hit', {}).get('type')
        cmd(ctx, 'tick unfreeze')
        ctx.step('wait', ticks=4)
        got = sum(s['count'] for s in ctx.step('inv')['slots'] if s['item'] == 'minecraft:cobblestone')
        left = len(packages(ctx, [x - 1, Y - 1, -1], [x + 7, Y + 1, 1]))
    ctx.check('moving-package.pick', hit == 'ENTITY' and got == 5 and left == 0,
              'crosshair pick %s; cobblestone given %d of 5; packages left %s' % (hit, got, left))
    cmd(ctx, 'clear @s', allow_error=True)


def run(ctx):
    _lib.setup_world(ctx, freeze=False)
    x = OX
    ctx.step('view', pos=[x + 4.5, Y + 8, 3.5], pitch=80.0, yaw=180.0, fly=True, hide_gui=True)
    ctx.step('wait', ticks=60)
    # a straight run east, then a right turn to the south
    cmd(ctx, 'fill %d %d 0 %d %d 0 hbmsntm:conveyor[facing=west,shape=straight]' % (x, Y, x + 6, Y))
    cmd(ctx, 'setblock %d %d 0 hbmsntm:conveyor[facing=west,shape=right]' % (x + 7, Y))
    cmd(ctx, 'fill %d %d 1 %d %d 5 hbmsntm:conveyor[facing=north,shape=straight]' % (x + 7, Y, x + 7, Y))
    _lib.placed(ctx)
    summon_package(ctx, x + 0.5, 0.5, [('minecraft:cobblestone', 64)])
    tr = ctx.step('track', center=[x + 5, Y + 0.5, 2], radius=8, type='hbmsntm:moving_package', ticks=120)
    es = tr.get('entities', [])
    ok = len(es) == 1 and es[0]['reversals'] == 0 and es[0]['max_step'] < 0.2
    ctx.check('moving-package.motion', ok, '; '.join('frames %d max_step %.3f reversals %d %s->%s' % (
        e['frames'], e['max_step'], e['reversals'], [round(c, 2) for c in e['first']], [round(c, 2) for c in e['last']]) for e in es) or 'no package tracked')
    summon_package(ctx, x + 2.5, 0.5, [('minecraft:cobblestone', 64)])
    ctx.step('wait', ticks=20)
    shots = []
    p = packages(ctx, [x, Y - 1, -1], [x + 8, Y + 1, 6])
    if p:
        px, py, pz = p[0]['pos']
        ctx.step('cmd', command='tick freeze')
        for label, eye in (('side', [px, py + 0.5, pz + 1.6]), ('front', [px + 1.6, py + 0.5, pz]), ('top', [px, py + 1.8, pz + 0.01])):
            ctx.step('view', eye=eye, look_at=[px, py + 0.2, pz], hide_gui=True)
            ctx.step('wait', ticks=2)
            shots.append(ctx.step('shot', file=ctx.shot_name('package-' + label))['image']['file'])
        ctx.step('cmd', command='tick unfreeze')
    ctx.review('moving-package.look', 'package on a straight belt from the side, the front and above', shots)
    cmd(ctx, 'kill @e[type=hbmsntm:moving_package]', allow_error=True)
    package_path(ctx)
    package_pick(ctx)
    # state across reopening the world
    rx, rz = OX + 20, 0
    for dx, dz, facing, shape in RING:
        cmd(ctx, 'setblock %d %d %d hbmsntm:conveyor[facing=%s,shape=%s]' % (rx + dx, Y, rz + dz, facing, shape))
    _lib.placed(ctx)
    stacks = [('minecraft:cobblestone', 64), ('minecraft:dirt', 32), ('minecraft:iron_ingot', 7), ('minecraft:sand', 1)]
    summon_package(ctx, rx + 1.5, rz + 0.5, stacks)
    px_ = OX + 30
    cmd(ctx, 'setblock %d %d 0 hbmsntm:crane_partitioner[facing=south]' % (px_, Y))
    cmd(ctx, 'item replace block %d %d 0 container.0 with hbmsntm:scrap_oil 8' % (px_, Y))
    cmd(ctx, 'item replace block %d %d 0 container.45 with minecraft:cobblestone 3' % (px_, Y))
    bx = OX + 40
    cmd(ctx, 'setblock %d %d 0 hbmsntm:crane_boxer[input=north,output=south]' % (bx, Y))
    cmd(ctx, 'data merge block %d %d 0 {mode:3b}' % (bx, Y))
    cmd(ctx, 'fill %d %d 1 %d %d 8 hbmsntm:conveyor[facing=north,shape=straight]' % (bx, Y, bx, Y))
    for slot, item in enumerate(('minecraft:cobblestone', 'minecraft:dirt', 'minecraft:sand')):
        cmd(ctx, 'item replace block %d %d 0 container.%d with %s 10' % (bx, Y, slot, item))
    cmd(ctx, 'setblock %d %d 0 minecraft:redstone_block' % (bx - 1, Y))
    ctx.step('view', pos=[OX + 30.5, Y + 12, 4.5], pitch=80.0, yaw=180.0, fly=True, hide_gui=True)
    ctx.step('wait', ticks=40)
    first = len(packages(ctx, [bx - 1, Y - 1, 0], [bx + 1, Y + 1, 10]))
    cmd(ctx, 'kill @e[type=hbmsntm:moving_package,x=%d,y=%d,z=0,distance=..12]' % (bx, Y), allow_error=True)
    for slot, item in enumerate(('minecraft:cobblestone', 'minecraft:dirt', 'minecraft:sand')):
        cmd(ctx, 'item replace block %d %d 0 container.%d with %s 10' % (bx, Y, slot, item))
    ctx.step('wait', ticks=10)
    ctx.step('leave')
    ctx.step('openworld', world=ctx.run.args.world)
    ctx.step('wait', ticks=60)
    ctx.step('view', pos=[OX + 30.5, Y + 12, 4.5], pitch=80.0, yaw=180.0, fly=True, hide_gui=True)
    ctx.step('wait', ticks=60)
    r = cmd(ctx, 'data get entity @e[type=hbmsntm:moving_package,x=%d,y=%d,z=%d,distance=..4,limit=1] contents' % (rx + 1, Y, rz + 1), wait_ticks=6, allow_error=True)
    got = {item: counts(text_of(r), item) for item, _ in stacks}
    ctx.check('moving-package.reload-package', got == dict(stacks), 'package contents after reopening %s; reply %s' % (got, text_of(r)[:200]))
    r = cmd(ctx, 'data get block %d %d 0 Items' % (px_, Y), wait_ticks=6)
    got = (counts(text_of(r), 'hbmsntm:scrap_oil'), counts(text_of(r), 'minecraft:cobblestone'))
    ctx.check('moving-package.reload-partitioner', got == (8, 3), 'partitioner oil scrap %d, cobblestone %d after reopening' % got)
    again = len(packages(ctx, [bx - 1, Y - 1, 0], [bx + 1, Y + 1, 10]))
    left = sum(counts(text_of(cmd(ctx, 'data get block %d %d 0 Items' % (bx, Y), wait_ticks=6)), i) for i in ('minecraft:cobblestone', 'minecraft:dirt', 'minecraft:sand'))
    ctx.check('moving-package.reload-boxer', first == 1 and again == 0 and left == 30,
              'packages with the signal on before reopening %d; after reopening with the signal still on %d; buffer holds %d of 30' % (first, again, left))
