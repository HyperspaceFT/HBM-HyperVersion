"""Cranes beyond their face textures: item icons, Shift descriptions, no look overlay, placement facing, the five screens.

Expected values follow the 1.7.10 original at cd0cff450:
- item icon: BlockCraneBase.getIcon for metadata 0 (BlockCraneBase.java:218-247): bottom the output icon, top the input
  icon, the four sides the "directional up" icon (each crane's icon fields, e.g. CraneExtractor.java:28-42).
- descriptions: ITooltipProvider.addStandardInfo shows the tile.<crane>.desc lines with Shift held and the hold-Shift
  hint without (ITooltipProvider.java:19-28; en_US.lang:5433-5448; NEO keys block.hbmsntm.<crane>.desc).
- no look overlay: BlockCraneBase implements no ILookOverlay (BlockCraneBase.java:35).
- placement: BlockCraneBase.onBlockPlacedBy uses BlockPistonBase.determineOrientation (1.7.10): within two blocks
  horizontally, an eye more than 2 above the block gives input up, an eye below the block input down; otherwise the
  input faces the player.
- screens (GUICraneInserter.java:30-58, GUICraneExtractor.java:31-92, GUICraneGrabber.java:32-81, GUICraneBoxer.java:27-40,
  GUICraneUnboxer.java:23-24): sizes, the inserter title at 88 - width/2 - 18, the others centred, the buttons and
  their hover texts; the boxer button cycles four modes, NEO answers the left button only (deliberate difference).
- comparators: the inserter, boxer and unboxer give a comparator signal from their buffer, the grabber none.
"""
import importlib.util
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

_spec = importlib.util.spec_from_file_location('crane_faces_fields', Path(__file__).with_name('crane_faces.py'))
faces = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(faces)

SCENARIO = dict(
    id='conveyor-cranes.misc',
    feature='conveyor-cranes',
    title='Crane icons, descriptions, look overlay, placement facing, screens, comparators',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70, hide_gui=False),
)

Y = -60
CRANES = faces.CRANES
DESC = dict(zh_cn=dict(crane_inserter=(4, 2, '手持螺丝刀按住Shift单击以设置输出侧'), crane_extractor=(5, 2, '用螺丝刀右键单击以设置输出侧'),
                       crane_grabber=(6, 4, '手持螺丝刀按住Shift单击以设置输出侧'), crane_boxer=(4, 0, '包裹'),
                       crane_unboxer=(4, 0, '接收打包好的物品并解包'), hint='显示更多信息'),
            en_us=dict(crane_inserter=(4, 2, 'Shift-click with screwdriver to set the output side'),
                       crane_extractor=(5, 2, 'Right-click with screwdriver to set output side'),
                       crane_grabber=(6, 4, 'Shift-click with screwdriver to set the output side'), crane_boxer=(4, 0, 'boxes'),
                       crane_unboxer=(4, 0, 'Receives boxes'), hint='display more info'))
SIZES = dict(crane_inserter=(176, 185), crane_extractor=(212, 185), crane_grabber=(176, 185), crane_boxer=(176, 185), crane_unboxer=(176, 185))
TITLES = dict(zh_cn=dict(crane_inserter='输送带导入器', crane_extractor='输送带提取器', crane_grabber='输送带抓斗', crane_boxer='输送带打包机',
                         crane_unboxer='输送带解包机'),
              en_us=dict(crane_inserter='Conveyor Inserter', crane_extractor='Conveyor Ejector', crane_grabber='Conveyor Grabber',
                         crane_boxer='Conveyor Boxer', crane_unboxer='Conveyor Unboxer'))
# buttons (x, y, w, h relative to the screen corner) and the hover text they show, if any
BUTTONS = dict(crane_inserter=[('destroyer', 151, 34, 18, 18, dict(zh_cn='销毁溢出物品', en_us='Destroy overflow'))],
               crane_extractor=[('maxEject', 187, 34, 18, 18, dict(zh_cn='只取满额', en_us='Only take maximum possible')),
                                ('whitelist', 128, 30, 14, 26, None)],
               crane_grabber=[('whitelist', 97, 30, 14, 26, None)],
               crane_boxer=[('mode', 151, 34, 18, 18, None)],
               crane_unboxer=[])


def expectations():
    items = []
    for c in CRANES:
        n = c[6:]
        items += [dict(id='conveyor-cranes.icon-%s' % n, text='%s item icon: output icon below, input icon on top, "directional up" on the sides' % c,
                       source='BlockCraneBase.java:218-247'),
                  dict(id='conveyor-cranes.desc-%s' % n, text='%s: Shift shows the description lines, otherwise the hold-Shift hint' % c,
                       source='ITooltipProvider.java:19-28; en_US.lang:5433-5448'),
                  dict(id='conveyor-cranes.no-overlay-%s' % n, text='aiming at a %s draws no look overlay' % c, source='BlockCraneBase.java:35'),
                  dict(id='conveyor-cranes.place-%s' % n, text='%s placed from beside (input faces the player), from above (up) and from below (down)' % c,
                       source='BlockPistonBase.determineOrientation (1.7.10)'),
                  dict(id='conveyor-cranes.screen-%s' % n, text='%s screen: size and title position as the original' % c,
                       source='GUICrane%s.java' % n.capitalize()),
                  dict(id='conveyor-cranes.screen-look-%s' % n, text='%s screen picture: texts fit, nothing cut off' % c,
                       source='GUICrane%s.java' % n.capitalize())]
    items += [dict(id='conveyor-cranes.button-%s-%s' % (c[6:], b[0]), text='%s %s button: hover text, left click toggles, right click does nothing' % (c, b[0]),
                   source='GUICrane*.java buttons; NEO left button only') for c in CRANES for b in BUTTONS[c]]
    items += [dict(id='conveyor-cranes.comparator', text='comparator next to inserter, boxer and unboxer reads the filled buffer; next to the grabber 0',
                   source='BlockCraneBase comparator (inserter/boxer/unboxer); grabber none')]
    return items


def sneak(ctx, on):
    ctx.step('key', key='key.keyboard.left.shift', action='press' if on else 'release', after=3)


def data(ctx, x, y, z, path=''):
    r = ctx.step('cmd', command=('data get block %d %d %d %s' % (x, y, z, path)).strip(), wait_ticks=6)
    return ' '.join(m['text'] for m in r.get('messages', []))


def run(ctx):
    lang = ctx.capture['lang']
    _lib.setup_world(ctx, freeze=False)
    for c in CRANES:
        n = c[6:]
        ic = faces.icons(c)
        m = ctx.step('itemmodel', item='hbmsntm:' + c)
        f = {d: sorted({q['sprite'].split('/')[-1] for q in m['faces'][d]}) for d in _lib.DIRS}
        want = dict(down=[ic['Out']], up=[ic['In']], **{d: [ic['DirectionalUp']] for d in _lib.HORIZONTAL})
        ctx.check('conveyor-cranes.icon-%s' % n, f == want, 'item model faces %s, want %s' % (f, want))
        ctx.step('mod', shift=False)
        plain = ctx.step('itemtip', item='hbmsntm:' + c)['tooltip']
        ctx.step('mod', shift=True)
        full = ctx.step('itemtip', item='hbmsntm:' + c)['tooltip']
        ctx.step('mod', shift=False)
        count, idx, text = DESC[lang][c]
        lines = full[1:]
        ok = any(DESC[lang]['hint'] in l for l in plain) and len(lines) == count and text in lines[idx]
        ctx.check('conveyor-cranes.desc-%s' % n, ok, 'without Shift %s; with Shift %s' % (plain[1:], lines))
    # look overlay and placement: a row of cranes, one per x
    ctx.step('view', pos=[312.5, Y + 3, 6.5], pitch=60.0, yaw=180.0, fly=True, hide_gui=False)
    ctx.step('wait', ticks=60)  # the chunks over there load first
    for i, c in enumerate(CRANES):
        n = c[6:]
        x = 300 + 6 * i
        ctx.step('cmd', command='setblock %d %d 0 hbmsntm:%s[input=north,output=south]' % (x, Y, c))
        ctx.step('cmd', command='item replace entity @s weapon.mainhand with minecraft:air')
        ctx.step('view', pos=[x + 0.5, Y, 2.5], look_at=[x + 0.5, Y + 0.5, 0.5], fly=False, hide_gui=False)
        ctx.step('wait', ticks=3)
        hud, problems = _lib.hud_on(ctx, (x, Y, 0))
        cross = _lib.crosshair_texts(hud)
        # the same view and read on a block that has an overlay must find text, or "none" proves nothing
        control = _lib.look_control(ctx, x + 3, Y, 0)
        ctx.check('conveyor-cranes.no-overlay-%s' % n, not cross and bool(control) and not problems,
                  'texts at the crosshair: %s; same read: %s; control (standard fluid duct beside it, same view and read): %s'
                  % (cross, '; '.join(problems) or 'action-bar probe read, crosshair on the crane', control))
        ctx.step('cmd', command='item replace entity @s weapon.mainhand with hbmsntm:%s 16' % c)
        got = {}
        # beside: standing two blocks south of the target cell, clicking the ground under it
        ctx.step('view', pos=[x + 0.5, Y, 8.5], look_at=[x + 0.5, Y - 0.5, 6.5], fly=False, hide_gui=False)
        ctx.step('use', target=dict(pos=[x, Y - 1, 6], face='up'), after=4)
        got['beside'] = ctx.step('dump', **{'from': [x, Y, 6]})['blocks']
        # above: eye more than 2 above the block, within 2 blocks horizontally
        ctx.step('view', pos=[x + 0.5, Y + 2.2, 11.5], look_at=[x + 0.5, Y - 0.5, 10.5], fly=True, hide_gui=False)
        ctx.step('use', target=dict(pos=[x, Y - 1, 10], face='up'), after=4)
        got['above'] = ctx.step('dump', **{'from': [x, Y, 10]})['blocks']
        # below: a ceiling block at Y + 3, the player under it clicks its bottom face
        ctx.step('cmd', command='setblock %d %d 14 minecraft:stone' % (x, Y + 3))
        ctx.step('view', pos=[x + 0.5, Y, 15.5], look_at=[x + 0.5, Y + 2.5, 14.5], fly=False, hide_gui=False)
        ctx.step('use', target=dict(pos=[x, Y + 3, 14], face='down'), any_hit=True, after=4)
        got['below'] = ctx.step('dump', **{'from': [x, Y + 2, 14]})['blocks']
        inputs = {k: (v[0]['props'].get('input') if v else None) for k, v in got.items()}
        ctx.check('conveyor-cranes.place-%s' % n, inputs == dict(beside='south', above='up', below='down'), 'input sides %s' % inputs)
    # screens: open each crane with an empty hand
    ctx.step('cmd', command='item replace entity @s weapon.mainhand with minecraft:air')
    for i, c in enumerate(CRANES):
        n = c[6:]
        x = 300 + 6 * i
        ctx.step('view', pos=[x + 0.5, Y, 2.5], look_at=[x + 0.5, Y + 0.5, 0.5], fly=False, hide_gui=False)
        ctx.step('use', target=dict(pos=[x, Y, 0], face='south'), after=6)
        ctx.step('screen', expect='Screen')
        hud = ctx.step('hud', frames=4)
        left, top = hud.get('gui_left'), hud.get('gui_top')
        title = [t for t in hud['texts'] if t['text'] == TITLES[lang][c]]
        iw, ih = hud.get('image_width'), hud.get('image_height')
        ok = (iw, ih) == SIZES[c] and title
        if title:
            tx = title[0]['x']  # screen labels are drawn in coordinates relative to the screen corner
            want_x = 88 - title[0]['width'] // 2 - 18 if c == 'crane_inserter' else iw // 2 - title[0]['width'] // 2
            ok = ok and abs(tx - want_x) <= 1 and title[0]['y'] in (5, 6)
        ctx.check('conveyor-cranes.screen-%s' % n, bool(ok), 'size %sx%s; title %s' % (
            iw, ih, [(t['x'], t['y'], t['width']) for t in title] if title else 'not drawn'))
        ctx.review('conveyor-cranes.screen-look-%s' % n, '%s screen in %s' % (c, lang), [ctx.step('shot', file=ctx.shot_name('screen-%s-%s' % (n, lang)))['image']['file']])
        for name, bx, by, bw, bh, hover in BUTTONS[c]:
            centre = [left + bx + bw / 2.0, top + by + bh / 2.0]
            before = data(ctx, x, Y, 0)
            texts = []
            if hover:
                ctx.step('hover', at=centre, frames=3)
                texts = [t['text'] for t in ctx.step('hud', frames=4)['texts'] if hover[lang] in t['text']]
            ctx.step('click', at=centre, button=1, after=4)
            after_right = data(ctx, x, Y, 0)
            ctx.step('click', at=centre, button=0, after=4)
            after_left = data(ctx, x, Y, 0)
            if hover:
                ctx.step('hover', at=centre, frames=3)
                texts += [t['text'] for t in ctx.step('hud', frames=4)['texts'] if hover[lang] in t['text']]
            ok = after_right == before and after_left != before and (not hover or (len(set(texts)) == 2))
            ctx.check('conveyor-cranes.button-%s-%s' % (n, name), ok, 'hover texts %s; right click changed data: %s; left click changed data: %s' % (
                texts, after_right != before, after_left != before))
        ctx.step('close')
    # comparators: fill the first buffer slots, read the comparator
    readings = {}
    for i, c in enumerate(CRANES):
        if c == 'crane_extractor':
            continue
        x = 300 + 6 * i
        ctx.step('cmd', command='setblock %d %d 1 minecraft:comparator[facing=north]' % (x, Y))
        slot = 0
        ctx.step('cmd', command='item replace block %d %d 0 container.%d with minecraft:cobblestone 64' % (x, Y, slot), allow_error=True)
        ctx.step('wait', ticks=6)
        readings[c] = data(ctx, x, Y, 1, 'OutputSignal')
    level = {c: int((re.findall(r'(\d+)\s*$', r) or ['-1'])[0]) for c, r in readings.items()}
    ok = all(level[c] > 0 for c in ('crane_inserter', 'crane_boxer', 'crane_unboxer')) and level['crane_grabber'] == 0
    ctx.check('conveyor-cranes.comparator', ok, 'comparator OutputSignal replies %s' % readings)
