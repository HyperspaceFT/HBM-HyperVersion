"""Conveyor wands placed by hand: item icons, single placement facing, screwdriver bends, lifts and chutes, pick block, off hand.

Expected values follow the 1.7.10 original at cd0cff450:
- icon: the wand renders the straight belt block of its type (ClientProxy.java:615, ItemRenderConveyorWand); the face textures
  of a straight belt are BlockConveyorBase.getIcon (belt texture on top, bottom and ends, conveyor_side along the sides).
- placement: BlockConveyorBase.onBlockPlacedBy (BlockConveyorBase.java:157-172) sets the input side behind the player, so
  items travel the way the player faced; NEO's `facing` property is the input side.
- screwdriver while sneaking: BlockConveyorBendable.onScrew (BlockConveyorBendable.java:107-128) cycles straight -> left curve
  (meta 6-9) -> right curve (meta 10-13) -> straight; getIcon (:33-50) names dir 1 the left and dir 2 the right curve.
- lifts and chutes: ItemConveyorWand.java:106-140, a regular wand clicked while sneaking on the top (bottom) face of a straight
  regular belt turns it into a lift (chute) and places another above (below); BlockConveyorLift.java:37-38 names the parts.
- the vertical conveyor's stub towards a neighbouring belt (RenderConveyorLift.java:24-166) and the chute bottom without a
  grate on its exit side (RenderConveyorChute.java:115-219) are pictures for a person.
- NEO differences stated in the NEO delivery: the wand answers the main hand only (an off-hand wand does nothing).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='conveyors.wand-place',
    feature='conveyors',
    title='Wand icons, hand placement, bends, lifts and chutes, pick block, off hand',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70, hide_gui=True,
                 camera='lift and chute: four side views 2.2 blocks off the column, eye level'),
)

TYPES = ('conveyor', 'conveyor_express', 'conveyor_double', 'conveyor_triple')
GROUND = -61  # the top layer of the superflat world is y -61; blocks stand on it at y -60
Y = -60
# yaw of a player facing each direction (0 south, 90 west, 180 north, -90 east)
# aim points below the top of a full block: belts are a quarter block high, the lift top piece half a block
BELT_TOP = [0, -0.8, 0]
HALF_TOP = [0, -0.6, 0]
# sneaking screwdriver clicks: BlockConveyorBendable.onScrew; the regular belt's own onScrew turns a right curve into a lift
# (BlockConveyor.java:25-48), the lift into a chute and the chute into a straight belt (BlockConveyorLift.java:106-117,
# BlockConveyorChute.java:100-111)
BEND_CYCLE = {t: [(t, 'left'), (t, 'right'), (t, 'straight')] for t in ('conveyor_express', 'conveyor_double', 'conveyor_triple')}
BEND_CYCLE['conveyor'] = [('conveyor', 'left'), ('conveyor', 'right'), ('conveyor_lift', None), ('conveyor_chute', None),
                          ('conveyor', 'straight')]
YAW = dict(south=0.0, west=90.0, north=180.0, east=-90.0)


def wand(meta):
    return 'hbmsntm:conveyor_wand[hbmsntm:meta=%d]' % meta


def expectations():
    items = [dict(id='conveyors.icon-%s' % t, text='%s wand icon is the straight belt block of its type' % t,
                  source='ClientProxy.java:615; BlockConveyorBase.java:44-54') for t in TYPES]
    items += [dict(id='conveyors.place-%s-%s' % (t, f), text='%s placed by a player facing %s carries items %s' % (t, f, f),
                   source='BlockConveyorBase.java:157-172') for t in TYPES for f in _lib.HORIZONTAL]
    items += [dict(id='conveyors.bend-%s' % t, text='%s: sneaking screwdriver clicks cycle the curves (regular: on to lift, chute, straight)' % t,
                   source='BlockConveyorBendable.java:107-128; BlockConveyor.java:25-48') for t in TYPES]
    items += [dict(id='conveyors.lift-by-wand', text='sneaking regular wand on a belt top builds a lift column bottom/middle/top',
                   source='ItemConveyorWand.java:106-140; BlockConveyorLift.java:37-38'),
              dict(id='conveyors.chute-by-wand', text='sneaking regular wand on a belt bottom builds a chute column with the bottom piece last',
                   source='ItemConveyorWand.java:106-140; RenderConveyorChute.java:123-133'),
              dict(id='conveyors.lift-stub-look', text='a vertical conveyor next to a belt shows the short belt stub towards it',
                   source='RenderConveyorLift.java:24-166'),
              dict(id='conveyors.chute-exit-look', text='the chute bottom piece has no grate on its exit side, grates on the other three',
                   source='RenderConveyorChute.java:115-219'),
              dict(id='conveyors.pick-block', text='middle click on each belt type in creative selects the wand of that type',
                   source='NEO deliberate difference: ConveyorBaseBlock.getCloneItemStack gives the wand of the type; the original has no '
                          'override, so Block.getPickBlock gives the hidden belt block item, which NEO does not register'),
              dict(id='conveyors.offhand-wand', text='a wand in the off hand does not place or start a route (NEO: main hand only)',
                   source='NEO deliberate difference: ConveyorWandItem uses the main hand')]
    return items


def hold(ctx, item):
    ctx.step('cmd', command='item replace entity @s weapon.mainhand with %s' % item)


def sneak(ctx, on):
    ctx.step('key', key='key.keyboard.left.shift', action='press' if on else 'release', after=3)


def state(ctx, pos):
    d = ctx.step('dump', **{'from': list(pos)})
    return d['blocks'][0] if d['blocks'] else {}


def run(ctx):
    _lib.setup_world(ctx, freeze=False)
    # icons
    for meta, t in enumerate(TYPES):
        m = ctx.step('itemmodel', item=wand(meta))
        got = set(m['sprites'])
        want = {'hbmsntm:block/' + t, 'hbmsntm:block/conveyor_side'}
        ctx.check('conveyors.icon-%s' % t, got == want, 'item model sprites %s, want %s' % (sorted(got), sorted(want)))
    # hand placement: stand 2 blocks behind the target cell, facing f, and click the ground's top face while sneaking
    for meta, t in enumerate(TYPES):
        hold(ctx, wand(meta) + ' 64')
        for i, f in enumerate(_lib.HORIZONTAL):
            x, z = -30 + 6 * meta, -30 + 6 * i
            dx, _, dz = _lib.VEC[f]
            ctx.step('view', pos=[x + 0.5 - 2 * dx, Y, z + 0.5 - 2 * dz], yaw=YAW[f], pitch=40.0, fly=False, hide_gui=False)
            sneak(ctx, True)
            ctx.step('use', target=dict(pos=[x, GROUND, z], face='up'), after=4)
            sneak(ctx, False)
            _lib.placed(ctx, 4)
            s = state(ctx, (x, Y, z))
            ok = s.get('block') == 'hbmsntm:' + t and s.get('props', {}).get('facing') == _lib.opposite(f)
            ctx.check('conveyors.place-%s-%s' % (t, f), ok, 'got %s %s, want %s facing=%s (input behind the player)' % (
                s.get('block'), s.get('props'), t, _lib.opposite(f)))
    # bends on the belts placed facing north (i = 0); the regular belt goes on to a lift and a chute and back
    hold(ctx, 'hbmsntm:screwdriver')
    for meta, t in enumerate(TYPES):
        x, z = -30 + 6 * meta, -30
        ctx.step('view', pos=[x + 2.5, Y, z + 2.5], look_at=[x + 0.5, Y + 0.2, z + 0.5], fly=False, hide_gui=False)
        sneak(ctx, True)
        got = []
        for _ in range(len(BEND_CYCLE[t])):
            ctx.step('use', target=dict(pos=[x, Y, z], face='up', offset=BELT_TOP), any_hit=True, after=4)
            b = state(ctx, (x, Y, z))
            got.append((b.get('block', 'air').split(':')[-1], b.get('props', {}).get('shape')))
        sneak(ctx, False)
        ctx.check('conveyors.bend-%s' % t, got == BEND_CYCLE[t], 'after each click %s, want %s' % (got, BEND_CYCLE[t]))
    # lift: regular belt on the ground, three sneaking clicks on the top of the column
    lx, lz = 20, 0
    hold(ctx, wand(0) + ' 64')
    ctx.step('cmd', command='setblock %d %d %d hbmsntm:conveyor[facing=north,shape=straight]' % (lx, Y, lz))
    ctx.step('cmd', command='setblock %d %d %d hbmsntm:conveyor[facing=west,shape=straight]' % (lx + 1, Y, lz))
    _lib.placed(ctx)
    for h in range(2):
        ctx.step('view', pos=[lx + 0.5, Y + h + 2.6, lz + 3.5], look_at=[lx + 0.5, Y + h + 1.0, lz + 0.5], fly=True, hide_gui=False)
        sneak(ctx, True)  # flying players sink while sneaking, so the key goes down only for the click
        ctx.step('use', target=dict(pos=[lx, Y + h, lz], face='up', offset=BELT_TOP if h == 0 else HALF_TOP), after=5)
        sneak(ctx, False)
    _lib.placed(ctx)
    parts = [state(ctx, (lx, Y + h, lz)).get('props', {}).get('part') for h in range(3)]
    ctx.check('conveyors.lift-by-wand', parts == ['bottom', 'middle', 'top'], 'parts bottom-up %s' % parts)
    # chute: a belt on a pillar, two sneaking clicks on the bottom of the column
    cx, cz = 30, 0
    ctx.step('cmd', command='setblock %d %d %d minecraft:stone' % (cx, Y + 5, cz + 1))
    ctx.step('cmd', command='setblock %d %d %d hbmsntm:conveyor[facing=north,shape=straight]' % (cx, Y + 5, cz))
    _lib.placed(ctx)
    for h in range(2):
        ctx.step('view', pos=[cx + 0.5, Y + 5 - h - 2.8, cz + 3.0], look_at=[cx + 0.5, Y + 5 - h, cz + 0.5], fly=True, hide_gui=False)
        sneak(ctx, True)
        ctx.step('use', target=dict(pos=[cx, Y + 5 - h, cz], face='down'), any_hit=True, after=5)
        sneak(ctx, False)
    _lib.placed(ctx)
    col = [state(ctx, (cx, Y + 5 - h, cz)) for h in range(3)]
    blocks = [c.get('block') for c in col]
    bottoms = [c.get('props', {}).get('bottom') for c in col]
    ctx.check('conveyors.chute-by-wand', blocks == ['hbmsntm:conveyor_chute'] * 3 and bottoms == ['false', 'false', 'true'],
              'top-down %s bottom=%s (the lowest piece stands on the ground)' % (blocks, bottoms))
    # pictures: lift with a belt beside it, and the chute bottom from four sides
    shots = []
    for label, eye, yaw, pitch in _lib.views(lx, Y, lz, distance=2.2)[2:]:
        ctx.step('view', eye=eye, yaw=yaw, pitch=pitch, hide_gui=True)
        ctx.step('settle', **{'from': [lx - 2, Y - 1, lz - 2], 'to': [lx + 2, Y + 3, lz + 2]}, ticks=2)
        shots.append(ctx.step('shot', file=ctx.shot_name('lift-%s' % label))['image']['file'])
    ctx.review('conveyors.lift-stub-look', 'lift column with an east neighbour belt feeding it from the east: stub towards it', shots)
    shots = []
    for label, eye, yaw, pitch in _lib.views(cx, Y + 3, cz, distance=2.2)[2:]:
        ctx.step('view', eye=eye, yaw=yaw, pitch=pitch, hide_gui=True)
        ctx.step('settle', **{'from': [cx - 2, Y - 1, cz - 2], 'to': [cx + 2, Y + 6, cz + 2]}, ticks=2)
        shots.append(ctx.step('shot', file=ctx.shot_name('chute-%s' % label))['image']['file'])
    ctx.review('conveyors.chute-exit-look', 'chute bottom at y %d, belt input north so items leave south: no grate on the S view' % (Y + 3), shots)
    # pick block with the middle mouse button on the four belts placed facing east (i = 1)
    picked = []
    for meta, t in enumerate(TYPES):
        x, z = -30 + 6 * meta, -24
        ctx.step('cmd', command='item replace entity @s weapon.mainhand with minecraft:air')
        ctx.step('view', pos=[x + 0.5, Y + 1.6, z - 1.5], look_at=[x + 0.5, Y + 0.1, z + 0.5], fly=True, hide_gui=False)
        ctx.step('mouse', button=2, action='click', after=4)
        inv = ctx.step('inv')
        main = [s for s in inv['slots'] if s['slot'] == inv['selected']]
        picked.append((t, main[0]['item'] if main else None, main[0].get('components', '') if main else ''))
    ok = all(item == 'hbmsntm:conveyor_wand' and ('meta=>%d' % i in comp or ('meta' not in comp and i == 0))
             for i, (_, item, comp) in enumerate(picked))
    ctx.check('conveyors.pick-block', ok, 'picked %s' % picked)
    # off hand: a wand in the off hand, empty main hand, click a block top while sneaking
    ox, oz = 40, 0
    ctx.step('cmd', command='item replace entity @s weapon.offhand with %s' % wand(0))
    ctx.step('cmd', command='item replace entity @s weapon.mainhand with minecraft:air')
    ctx.step('view', pos=[ox + 0.5, Y, oz + 2.5], yaw=180.0, pitch=45.0, fly=False, hide_gui=False)
    sneak(ctx, True)
    ctx.step('use', target=dict(pos=[ox, GROUND, oz], face='up'), after=4)
    sneak(ctx, False)
    ctx.step('use', target=dict(pos=[ox, GROUND, oz], face='up'), after=4)
    _lib.placed(ctx)
    s = state(ctx, (ox, Y, oz))
    inv = ctx.step('inv')
    off = [x for x in inv['slots'] if x['slot'] == 40]
    data = off[0].get('components', '') if off else ''
    ctx.check('conveyors.offhand-wand', not s and 'custom_data' not in data,
              'block above the clicked ground: %s; off-hand wand components: %s' % (s.get('block'), data or 'none'))
    ctx.step('cmd', command='item replace entity @s weapon.offhand with minecraft:air')
