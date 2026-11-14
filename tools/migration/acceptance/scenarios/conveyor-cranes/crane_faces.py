"""Five conveyor cranes in all 30 input/output states: the texture of every face, and the top arrows for a person.

The expected texture of each face is computed here from the 1.7.10 original (BlockCraneBase.getIcon,
BlockCraneBase.java:144-215 at cd0cff450; each crane's icon fields from its registerBlockIcons: CraneInserter.java:39-51,
CraneExtractor.java:30-42, CraneGrabber.java:28-42, CraneBoxer.java:36-50, CraneUnboxer.java:36-50) and compared with the
sprites of the baked model the client draws. The arrow direction (the original's UV rotations) is judged from the contact
sheets. States are placed with setblock ... [input=,output=] in the air, one camera per face.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='conveyor-cranes.faces',
    feature='conveyor-cranes',
    title='Crane face textures and top arrows, 5 cranes x 30 states',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70, hide_gui=True, freeze_ticks=True,
                 camera='1.6 blocks off each face centre; top/bottom views with north up', sheet_crop=0.62, tile=128),
)

CRANES = ('crane_inserter', 'crane_extractor', 'crane_grabber', 'crane_boxer', 'crane_unboxer')
PAIRS = [(i, o) for i in _lib.DIRS for o in _lib.DIRS if i != o]
Y = -50
FIELDS = ('Directional', 'DirectionalUp', 'DirectionalDown', 'TurnLeft', 'TurnRight', 'SideLeftTurnUp', 'SideRightTurnUp',
          'SideLeftTurnDown', 'SideRightTurnDown', 'SideUpTurnLeft', 'SideUpTurnRight', 'SideDownTurnLeft', 'SideDownTurnRight')


def _fields(prefix, reversed_order):
    """The 13 directional icon fields. Inserter, grabber and boxer register them in BlockCraneBase order; the extractor
    and unboxer point the fields at their files in another order (CraneExtractor.java:30-42, CraneUnboxer.java:38-50)."""
    if not reversed_order:
        names = ('top', 'side_up', 'side_down', 'top_left', 'top_right', 'side_left_turn_up', 'side_right_turn_up',
                 'side_left_turn_down', 'side_right_turn_down', 'side_up_turn_left', 'side_up_turn_right',
                 'side_down_turn_left', 'side_down_turn_right')
    else:
        names = ('top', 'side_down', 'side_up', 'top_right', 'top_left', 'side_up_turn_left', 'side_up_turn_right',
                 'side_down_turn_left', 'side_down_turn_right', 'side_left_turn_up', 'side_right_turn_up',
                 'side_left_turn_down', 'side_right_turn_down')
    return {f: '%s_%s' % (prefix, n) for f, n in zip(FIELDS, names)}


def icons(crane):
    base = dict(Block='crane_top', Side='crane_side', In='crane_in', SideIn='crane_side_in', Out='crane_out', SideOut='crane_side_out')
    if crane == 'crane_inserter':
        base.update(_fields('crane_in', False))
    elif crane == 'crane_extractor':
        base.update(_fields('crane_out', True))
    elif crane == 'crane_grabber':
        base.update(_fields('crane_grabber', False), In='crane_pull', SideIn='crane_side_pull')
    elif crane == 'crane_boxer':
        base.update(_fields('crane_boxer', False), Out='crane_box', SideOut='crane_side_box')
    elif crane == 'crane_unboxer':
        base.update(_fields('crane_unboxer', True), Out='crane_box', SideOut='crane_side_box')
    return base


def expected_icon(ic, side, inp, out):
    """BlockCraneBase.getIcon(IBlockAccess, ...) for one side; the output is overridden when it is not opposite the input."""
    overridden = out != _lib.opposite(inp)
    left = _lib.cross(out, inp) if overridden else None
    if side in ('down', 'up'):
        if side == out:
            return ic['Out']
        if side == inp:
            return ic['In']
        if side == 'up':
            if overridden:
                if left == 'up':
                    return ic['TurnLeft']
                if left == 'down':
                    return ic['TurnRight']
            else:
                return ic['Directional']
        return ic['Block']
    if side == out:
        return ic['SideOut']
    if side == inp:
        return ic['SideIn']
    if overridden:
        if left == side:
            if out == 'up':
                return ic['SideLeftTurnUp']
            if out == 'down':
                return ic['SideRightTurnDown']
            if inp == 'up':
                return ic['SideUpTurnRight']
            if inp == 'down':
                return ic['SideDownTurnLeft']
        if left is not None and _lib.opposite(left) == side:
            if out == 'up':
                return ic['SideRightTurnUp']
            if out == 'down':
                return ic['SideLeftTurnDown']
            if inp == 'up':
                return ic['SideUpTurnLeft']
            if inp == 'down':
                return ic['SideDownTurnRight']
    else:
        if out == 'up':
            return ic['DirectionalUp']
        if out == 'down':
            return ic['DirectionalDown']
    return ic['Side']


def pos(c, k):
    return (4 * k, Y, 8 * c)


def label(inp, out):
    return 'I=%s O=%s' % (_lib.SHORT[inp], _lib.SHORT[out])


def expectations():
    items = []
    for crane in CRANES:
        for inp, out in PAIRS:
            items.append(dict(id='conveyor-cranes.faces-%s-%s-%s' % (crane[6:], inp, out),
                              text='%s input=%s output=%s: the six face textures follow BlockCraneBase.getIcon' % (crane, inp, out),
                              source='BlockCraneBase.java:144-215'))
    for crane in CRANES:
        table = 'table 1 (arrow from input to output)' if crane in ('crane_inserter', 'crane_grabber', 'crane_boxer') else \
            'table 2 (arrow from output to input, CraneExtractor.java:45-76 / CraneUnboxer.java:54-84)'
        items.append(dict(id='conveyor-cranes.arrows-%s' % crane[6:],
                          text='%s: top and turning-side arrows point the right way in all 30 states, %s' % (crane, table),
                          source='BlockCraneBase.java:249-261'))
    return items


def run(ctx):
    _lib.setup_world(ctx, freeze=True)
    lo, hi = pos(0, 0), pos(len(CRANES) - 1, len(PAIRS) - 1)
    _lib.go_near(ctx, (lo[0] + hi[0]) // 2, Y, (lo[2] + hi[2]) // 2)
    for c, crane in enumerate(CRANES):
        for k, (inp, out) in enumerate(PAIRS):
            x, y, z = pos(c, k)
            ctx.step('cmd', command='setblock %d %d %d hbmsntm:%s[input=%s,output=%s]' % (x, y, z, crane, inp, out), wait_ticks=1)
    _lib.placed(ctx)
    dump = ctx.step('dump', **{'from': list(lo), 'to': list(hi)}, faces=True)
    found = _lib.faces_by_pos(dump)
    for c, crane in enumerate(CRANES):
        ic = icons(crane)
        for k, (inp, out) in enumerate(PAIRS):
            eid = 'conveyor-cranes.faces-%s-%s-%s' % (crane[6:], inp, out)
            entry = found.get(pos(c, k))
            if entry is None or entry['block'] != 'hbmsntm:' + crane:
                ctx.check(eid, False, 'block not there: %s' % (entry and entry['block']))
                continue
            props = entry['props']
            wrong = []
            if props.get('input') != inp or props.get('output') != out:
                wrong.append('state %s' % props)
            for side in _lib.DIRS:
                want = 'hbmsntm:block/' + expected_icon(ic, side, inp, out)
                got = _lib.sprites(entry, side)
                if got != [want]:
                    wrong.append('%s: %s, expected %s' % (side, ','.join(got) or 'none', want))
            ctx.check(eid, not wrong, '; '.join(wrong) or 'all six faces as expected', ['dump: seq %s' % dump['seq']])

    # spectator: the camera body passes through the cranes (the top view's feet are inside the block)
    ctx.step('cmd', command='gamemode spectator')
    for c, crane in enumerate(CRANES):
        tiles = []
        for k, (inp, out) in enumerate(PAIRS):
            x, y, z = pos(c, k)
            for view, eye, yaw, pitch in _lib.views(x, y, z):
                name = ctx.shot_name('%s/%s-%s-%s' % (crane, inp, out, view))
                ctx.step('view', eye=eye, yaw=yaw, pitch=pitch, hide_gui=True)
                ctx.step('settle', **{'from': [x, y, z]}, ticks=1)
                ctx.step('shot', file=name)
                tiles.append(dict(file=name, label='%s %s' % (label(inp, out), view)))
        sheet = ctx.step('sheet', file=ctx.shot_name('%s-sheet' % crane), tiles=tiles, cols=6, tile_width=128, tile_height=128,
                         crop=ctx.capture['sheet_crop'])
        ctx.review('conveyor-cranes.arrows-%s' % crane[6:], 'contact sheet: one row per state, TOP BOTTOM N S W E',
                   [sheet['file']])
    ctx.step('cmd', command='tick unfreeze')
    ctx.step('cmd', command='gamemode creative')
