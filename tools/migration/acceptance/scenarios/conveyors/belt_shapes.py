"""Conveyor belt models: four belt types x straight/left/right x four facings, the vertical conveyor and the chute.

Face textures are asserted against the 1.7.10 original (BlockConveyorBase.getIcon, BlockConveyorBase.java:44-54, and
BlockConveyorBendable.getIcon, BlockConveyorBendable.java:33-50 at cd0cff450): straight belts show the belt texture on the
top, the bottom and the two ends and conveyor_side along the travel direction; bends show their curve texture on top and
bottom and conveyor_side all round. Whether the animation runs the way items travel, and the look of the vertical conveyor
(bottom, middle, top; RenderConveyorLift.java:24-166) and the chute (RenderConveyorChute.java:115-219), is judged from the
contact sheets; the lift parts and the chute's bottom and side states are asserted from the neighbour rules
(BlockConveyorLift.java:37-38, RenderConveyorChute.java:123-133). NEO's facing is the input side; items travel to the
opposite side, a left bend leaves on the left of the travel direction.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='conveyors.models',
    feature='conveyors',
    title='Belt, vertical conveyor and chute models',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70, hide_gui=True, freeze_ticks=False,
                 camera='belts: 1.4 blocks above the top face, north up, 4 frames 2 ticks apart; lifts and chutes: '
                        'two oblique views', sheet_crop=0.62, tile=128),
)

TYPES = ('conveyor', 'conveyor_express', 'conveyor_double', 'conveyor_triple')
SHAPES = ('straight', 'left', 'right')
GROUND = -60
BELT_ROW_Z = 0
LIFT_Z = 40
BELTS = [(t, s, f) for t in TYPES for s in SHAPES for f in _lib.HORIZONTAL]
# vertical conveyor columns (height) and chute set-ups: (name, blocks bottom-up, extra blocks)
LIFTS = [('lift1', 1), ('lift2', 2), ('lift3', 3)]
CHUTES = [
    ('chute1', [(0, 'hbmsntm:conveyor_chute')], []),
    ('chute2', [(0, 'hbmsntm:conveyor_chute'), (1, 'hbmsntm:conveyor_chute')], []),
    ('chute_on_belt', [(0, 'hbmsntm:conveyor[facing=north,shape=straight]'), (1, 'hbmsntm:conveyor_chute')], []),
    ('chute_belt_beside', [(0, 'hbmsntm:conveyor_chute')], [((0, 0, 1), 'hbmsntm:conveyor[facing=north,shape=straight]')]),
]


def belt_pos(i):
    return (3 * i, GROUND, BELT_ROW_Z)


def expected_belt(t, shape, facing):
    """Per face: BlockConveyorBendable.getIcon for a belt whose input side is `facing`."""
    top = t if shape == 'straight' else '%s_curve_%s' % (t, shape)
    faces = {'up': top, 'down': top}
    for side in _lib.HORIZONTAL:
        along = side in (facing, _lib.opposite(facing))
        faces[side] = t if (shape == 'straight' and along) else 'conveyor_side'
    return {k: 'hbmsntm:block/' + v for k, v in faces.items()}


def travel(shape, facing):
    t = _lib.opposite(facing)
    return t if shape == 'straight' else (_lib.counter_clockwise(t) if shape == 'left' else _lib.clockwise(t))


def expectations():
    items = [dict(id='conveyors.faces-%s-%s-%s' % (t, s, f),
                  text='%s %s with input %s: face textures as BlockConveyorBendable.getIcon' % (t, s, f),
                  source='BlockConveyorBendable.java:33-50') for t, s, f in BELTS]
    items += [dict(id='conveyors.anim-%s' % t, text='%s: the top animation runs the way items travel in all 12 states' % t,
                   source='BlockConveyorBendable.java:33-50 (top rotation inferred from the 1.7.10 piston renderer)') for t in TYPES]
    items += [dict(id='conveyors.lift-parts', text='vertical conveyor columns of 1, 2 and 3: bottom / bottom+top / bottom+middle+top',
                   source='BlockConveyorLift.java:37-38'),
              dict(id='conveyors.lift-look', text='vertical conveyor bottom, middle and top pieces look as described (posts, back wall, chain belt, stubs, iron floor, half-high top)',
                   source='RenderConveyorLift.java:24-166'),
              dict(id='conveyors.chute-states', text='chute: bottom piece unless a belt or chute is below; side stubs towards adjacent belts',
                   source='RenderConveyorChute.java:123-133'),
              dict(id='conveyors.chute-look', text='chute forms look as described (corner posts, grates, cross belt at the bottom, stubs)',
                   source='RenderConveyorChute.java:115-219')]
    return items


def place_column(ctx, x, z, blocks):
    """setblock bottom-up, then a block above the top placed and removed so the top piece also sees its neighbours
    (setblock does not update the block it places; the player's placement does through getStateForPlacement)."""
    for dy, block in blocks:
        ctx.step('cmd', command='setblock %d %d %d %s' % (x, GROUND + dy, z, block), wait_ticks=1)
    top = GROUND + max(dy for dy, _ in blocks) + 1
    ctx.step('cmd', command='setblock %d %d %d minecraft:stone' % (x, top, z), wait_ticks=1)
    ctx.step('cmd', command='setblock %d %d %d minecraft:air' % (x, top, z), wait_ticks=1)


def oblique(ctx, x, z, height, name, tiles, text):
    for tag, dx, dz in (('SE', 2.6, 2.6), ('NW', -1.6, -1.6)):
        eye = [x + 0.5 + dx, GROUND + height + 1.2, z + 0.5 + dz]
        ctx.step('view', eye=eye, look_at=[x + 0.5, GROUND + height / 2.0, z + 0.5], hide_gui=True)
        ctx.step('settle', **{'from': [x, GROUND, z], 'to': [x, GROUND + height, z]}, ticks=2)
        file = ctx.shot_name('%s-%s' % (name, tag))
        ctx.step('shot', file=file)
        tiles.append(dict(file=file, label='%s %s' % (text, tag)))


def run(ctx):
    _lib.setup_world(ctx, freeze=False)
    _lib.go_near(ctx, belt_pos(len(BELTS) // 2)[0], GROUND, BELT_ROW_Z)
    ctx.step('cmd', command='gamemode spectator')
    for i, (t, s, f) in enumerate(BELTS):
        x, y, z = belt_pos(i)
        ctx.step('cmd', command='setblock %d %d %d hbmsntm:%s[facing=%s,shape=%s]' % (x, y, z, t, f, s), wait_ticks=1)
    _lib.placed(ctx)
    dump = ctx.step('dump', **{'from': list(belt_pos(0)), 'to': list(belt_pos(len(BELTS) - 1))}, faces=True)
    found = _lib.faces_by_pos(dump)
    for i, (t, s, f) in enumerate(BELTS):
        eid = 'conveyors.faces-%s-%s-%s' % (t, s, f)
        entry = found.get(belt_pos(i))
        if entry is None or entry['block'] != 'hbmsntm:' + t:
            ctx.check(eid, False, 'block not there')
            continue
        wrong = []
        for side, want in expected_belt(t, s, f).items():
            got = _lib.sprites(entry, side)
            if got != [want]:
                wrong.append('%s: %s, expected %s' % (side, ','.join(got) or 'none', want))
        ctx.check(eid, not wrong, '; '.join(wrong) or 'all faces as expected', ['dump seq %s' % dump['seq']])

    for t in TYPES:
        tiles = []
        for i, (bt, s, f) in enumerate(BELTS):
            if bt != t:
                continue
            x, y, z = belt_pos(i)
            ctx.step('view', eye=[x + 0.5, y + 0.25 + 1.4, z + 0.5], yaw=180.0, pitch=90.0, hide_gui=True)
            ctx.step('settle', **{'from': [x, y, z]}, ticks=1)
            base = ctx.shot_name('%s/%s-%s' % (t, s, f))
            ctx.step('series', file=base, count=4, interval=2)
            for n in range(4):
                tiles.append(dict(file='%s_%02d' % (base, n), label='%s IN=%s TO=%s F%d' % (s, _lib.SHORT[f], _lib.SHORT[travel(s, f)], n)))
        sheet = ctx.step('sheet', file=ctx.shot_name('%s-sheet' % t), tiles=tiles, cols=4, tile_width=128, tile_height=128,
                         crop=ctx.capture['sheet_crop'])
        ctx.review('conveyors.anim-%s' % t, 'rows: state (shape, input side, travel side), columns: 4 frames 2 ticks apart, north up',
                   [sheet['file']])

    tiles = []
    _lib.go_near(ctx, 12, GROUND, LIFT_Z)
    for n, (name, height) in enumerate(LIFTS):
        x = 4 * n
        place_column(ctx, x, LIFT_Z, [(dy, 'hbmsntm:conveyor_lift[facing=north]') for dy in range(height)])
    for n, (name, blocks, extra) in enumerate(CHUTES):
        x = 4 * (len(LIFTS) + n)
        for (dx, dy, dz), block in extra:
            ctx.step('cmd', command='setblock %d %d %d %s' % (x + dx, GROUND + dy, LIFT_Z + dz, block), wait_ticks=1)
        place_column(ctx, x, LIFT_Z, blocks)
    total = 4 * (len(LIFTS) + len(CHUTES))
    _lib.placed(ctx)
    dump = ctx.step('dump', **{'from': [0, GROUND, LIFT_Z - 1], 'to': [total, GROUND + 3, LIFT_Z + 1]})
    blocks = _lib.faces_by_pos(dump)
    parts = {}
    for n, (name, height) in enumerate(LIFTS):
        parts[name] = [blocks.get((4 * n, GROUND + dy, LIFT_Z), {}).get('props', {}).get('part') for dy in range(height)]
    want = dict(lift1=['bottom'], lift2=['bottom', 'top'], lift3=['bottom', 'middle', 'top'])
    ctx.check('conveyors.lift-parts', parts == want, 'parts %s, expected %s' % (parts, want), ['dump seq %s' % dump['seq']])
    wrong = []
    for n, (name, column, extra) in enumerate(CHUTES):
        x = 4 * (len(LIFTS) + n)
        for dy, block in column:
            if 'chute' not in block:
                continue
            below = GROUND + dy - 1
            below_block = blocks.get((x, below, LIFT_Z), {}).get('block', 'minecraft:grass_block')
            want_bottom = below_block not in ('hbmsntm:conveyor', 'hbmsntm:conveyor_chute', 'hbmsntm:conveyor_lift')
            props = blocks.get((x, GROUND + dy, LIFT_Z), {}).get('props', {})
            want_sides = {d: any((x + ex[0], GROUND + ex[1], LIFT_Z + ex[2]) == (x + _lib.VEC[d][0], GROUND + dy, LIFT_Z + _lib.VEC[d][2])
                                 for ex, _ in extra) for d in _lib.HORIZONTAL}
            got_sides = {d: props.get(d) == 'true' for d in _lib.HORIZONTAL}
            if (props.get('bottom') == 'true') != want_bottom or got_sides != want_sides:
                wrong.append('%s y+%d: bottom=%s sides=%s, expected bottom=%s sides=%s' % (
                    name, dy, props.get('bottom'), got_sides, want_bottom, want_sides))
    ctx.check('conveyors.chute-states', not wrong, '; '.join(wrong) or 'bottom and side states as expected', ['dump seq %s' % dump['seq']])

    for n, (name, height) in enumerate(LIFTS):
        oblique(ctx, 4 * n, LIFT_Z, height, 'lift/%s' % name, tiles, name.upper())
    sheet = ctx.step('sheet', file=ctx.shot_name('lift-sheet'), tiles=tiles, cols=2, tile_width=256, tile_height=256, crop=0.9)
    ctx.review('conveyors.lift-look', 'columns of 1, 2, 3 from south-east and north-west', [sheet['file']])
    tiles = []
    for n, (name, column, extra) in enumerate(CHUTES):
        oblique(ctx, 4 * (len(LIFTS) + n), LIFT_Z, len(column), 'chute/%s' % name, tiles, name.upper())
    sheet = ctx.step('sheet', file=ctx.shot_name('chute-sheet'), tiles=tiles, cols=2, tile_width=256, tile_height=256, crop=0.9)
    ctx.review('conveyors.chute-look', 'single, double, on a belt, belt beside the bottom; south-east and north-west', [sheet['file']])
    ctx.step('cmd', command='gamemode creative')
