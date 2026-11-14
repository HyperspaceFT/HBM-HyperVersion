"""Screwdriver spot check on each crane: three plain clicks set the input side, three sneaking clicks the output side.

Expected states follow the 1.7.10 original: BlockCraneBase.onScrew (BlockCraneBase.java:100-115) calls
TileEntityCraneBase.setInput or setOutputOverride (TileEntityCraneBase.java:55-78 at cd0cff450). The clicks go through the
client's real use key (the executor's use step) with a screwdriver in the main hand; sneaking is the real sneak key held.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='conveyor-cranes.screwdriver',
    feature='conveyor-cranes',
    title='Screwdriver on the five cranes: 3 plain and 3 sneaking clicks each',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70, hide_gui=False),
)

CRANES = ('crane_inserter', 'crane_extractor', 'crane_grabber', 'crane_boxer', 'crane_unboxer')
CLICKS = (('up', False), ('south', False), ('east', False), ('up', True), ('south', True), ('east', True))
GROUND = -60


class Crane:
    """TileEntityCraneBase: the input side is the metadata, the output an optional override."""

    def __init__(self, inp):
        self.inp = inp
        self.override = None

    def output(self):
        return self.override if self.override else _lib.opposite(self.inp)

    def set_output_override(self, direction):
        old = self.output()
        if old == direction:
            direction = _lib.opposite(direction)
        self.override = direction
        if direction == self.inp:
            self.set_input(old)

    def set_input(self, direction):
        self.override = self.output()
        old = self.inp
        if old == direction:
            direction = _lib.opposite(direction)
        swap = direction == self.output()
        self.inp = direction
        if swap:
            self.set_output_override(old)


def expectations():
    items = []
    for crane in CRANES:
        for n, (face, sneak) in enumerate(CLICKS, 1):
            items.append(dict(id='conveyor-cranes.screwdriver-%s-%d' % (crane[6:], n),
                              text='%s: %s screwdriver click on the %s face sets the %s side as the original does' % (
                                  crane, 'sneaking' if sneak else 'plain', face, 'output' if sneak else 'input'),
                              source='TileEntityCraneBase.java:55-78'))
    return items


def run(ctx):
    _lib.setup_world(ctx, freeze=False)
    ctx.step('cmd', command='item replace entity @s weapon.mainhand with hbmsntm:screwdriver')
    for c, crane in enumerate(CRANES):
        x, z = 200 + 8 * c, 200
        ctx.step('cmd', command='setblock %d %d %d hbmsntm:%s[input=north,output=south]' % (x, GROUND, z, crane))
        model = Crane('north')
        ctx.step('view', pos=[x + 2.5, GROUND, z + 2.5], look_at=[x + 0.5, GROUND + 0.5, z + 0.5], fly=False, hide_gui=False)
        ctx.step('wait', ticks=5)
        sneaking = False
        for n, (face, sneak) in enumerate(CLICKS, 1):
            if sneak and not sneaking:
                ctx.step('key', key='key.keyboard.left.shift', action='press', after=5)
                sneaking = True
            use = ctx.step('use', target=dict(pos=[x, GROUND, z], face=face), after=3, allow_fail=True)
            if sneak:
                model.set_output_override(face)
            else:
                model.set_input(face)
            dump = ctx.step('dump', **{'from': [x, GROUND, z]})
            props = dump['blocks'][0]['props'] if dump['blocks'] else {}
            got = (props.get('input'), props.get('output'))
            want = (model.inp, model.output())
            eid = 'conveyor-cranes.screwdriver-%s-%d' % (crane[6:], n)
            if use['status'] != 'ok':
                ctx.check(eid, False, 'use step failed: %s' % use.get('reason'), ['use seq %s' % use['seq']])
            else:
                ctx.check(eid, got == want, 'input=%s output=%s, expected input=%s output=%s (%s)' % (
                    got + want + (use.get('path'),)), ['use seq %s' % use['seq'], 'dump seq %s' % dump['seq']])
            # continue from the state the game actually has, so one wrong click does not fail the rest
            if got[0]:
                model.inp, model.override = got[0], got[1]
        if sneaking:
            ctx.step('key', key='key.keyboard.left.shift', action='release')
