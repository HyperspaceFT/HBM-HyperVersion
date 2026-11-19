"""Two-point building with the conveyor wand: preview, chat messages, counting, hand switch, creative line break.

Expected values follow the 1.7.10 original at cd0cff450:
- after the first click the client shows the whole route, cyan when it can be built and red when it is blocked or short
  (ItemConveyorWand.java:249-308, RenderOverhead.java:398-447); a regular wand routes up and down with lifts and chutes
  (ItemConveyorWand.java:106-140 and the route construction); the preview ends with the second click.
- chat after the second click: "Conveyor built!", "Not enough conveyors, build cancelled", "Conveyor obstructed, build
  cancelled" (ItemConveyorWand.java:211-215; NEO keys item.hbmsntm.conveyor_wand.built/not_enough/obstructed).
- creative, sneaking, wand in hand, aiming at a belt: the look overlay names the block and "Break whole conveyor line"
  (ItemConveyorWand.java:505-517); breaking one belt then removes the connected line without drops, at most 31 belts
  upstream and 29 downstream (the original's walk limits); without sneaking only one belt goes.
- NEO deliberate differences: the second click counts the wands left in the main inventory again (dropping wands between
  the clicks cancels the build); switching the held slot clears the preview.
- the original belt block has no look overlay (BlockConveyorBase implements no ILookOverlay), so aiming at a belt with an
  empty hand draws nothing at the crosshair.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='conveyors.wand-build',
    feature='conveyors',
    title='Wand two-point build: preview, messages, counting, hand switch, line break',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70, hide_gui=False),
)

Y = -60
WAND = 'hbmsntm:conveyor_wand'
TEXT = dict(zh_cn=dict(built='输送带已建成！', short='输送带数量不足，已取消建造', blocked='输送带路线受阻，已取消建造',
                       name='输送带', break_line='拆除整条输送带'),
            en_us=dict(built='Conveyor built!', short='Not enough conveyors, build cancelled',
                       blocked='Conveyor obstructed, build cancelled', name='Conveyor Belt', break_line='Break whole conveyor line'))


def expectations():
    return [
        dict(id='conveyors.preview-valid', text='after the first click the preview holds the whole route and is cyan (buildable)',
             source='ItemConveyorWand.java:249-308; RenderOverhead.java:398-447'),
        dict(id='conveyors.preview-lifts', text='a regular wand route 3 blocks up holds vertical conveyor pieces in the preview',
             source='ItemConveyorWand.java:106-140'),
        dict(id='conveyors.preview-blocked', text='a route through a block shows a red (not buildable) preview',
             source='ItemConveyorWand.java:249-308'),
        dict(id='conveyors.built-message', text='the second click builds the route, prints "Conveyor built!" and ends the preview',
             source='ItemConveyorWand.java:211'),
        dict(id='conveyors.blocked-message', text='a blocked route is not built and prints the obstructed message',
             source='ItemConveyorWand.java:215'),
        dict(id='conveyors.short-message', text='survival, 5 wands, 10-block route: not built, not-enough message, wands kept',
             source='ItemConveyorWand.java:213'),
        dict(id='conveyors.recount', text='survival: wands dropped between the clicks so too few are left: not built (NEO counts again)',
             source='NEO deliberate difference: ConveyorWandItem counts at the second click'),
        dict(id='conveyors.consumption', text='survival: a built route takes exactly one wand per belt placed',
             source='ItemConveyorWand.java:180-223'),
        dict(id='conveyors.hand-switch', text='switching the held hotbar slot after the first click clears the preview',
             source='NEO: ConveyorWandPreview.render clears without a wand start in the main hand'),
        dict(id='conveyors.break-overlay', text='creative, sneaking, wand held, aiming at a belt: overlay with the block name and "Break whole conveyor line"',
             source='ItemConveyorWand.java:505-517'),
        dict(id='conveyors.break-line', text='breaking the middle of a 70-belt line removes 31 upstream, 29 downstream and itself, with no drops',
             source='ItemConveyorWand.java line-break walk (31 up, 29 down)'),
        dict(id='conveyors.break-single', text='without sneaking only the hit belt goes',
             source='ItemConveyorWand.java:505-517 (sneak only)'),
        dict(id='conveyors.aim-overlay', text='aiming at a belt with an empty hand draws no look overlay (the original belt has none)',
             source='BlockConveyorBase.java:28 (no ILookOverlay)'),
        dict(id='conveyors.look-names', text='creative, sneaking, wand in the main hand: aiming at each of the six belt blocks (regular, express, '
             'double, triple, vertical, chute) names that block in the client language at the crosshair',
             source='ItemConveyorWand.java:505-517 (printHook names the aimed block); zh_cn / en_us block names'),
        dict(id='conveyors.offhand-text', text='the same aim with the wand only in the off hand draws no text at the crosshair (the main-hand '
             'reading of conveyors.look-names in the same scenario is the positive control)', source='NEO deliberate difference: the wand answers the main hand only'),
        dict(id='conveyors.preview-update', text='after the first click the preview follows the aimed target: two targets give two different '
             'routes, aiming at the sky clears it, aiming back brings it back; buildable is cyan, blocked red (success flag)',
             source='ItemConveyorWand.java:249-308; RenderOverhead.java:398-447 (glColor 0,1,1 / 1,0,0)'),
        dict(id='conveyors.route-self-cross', text='record: a regular-wand route forced up and down again passes the same cell twice; in survival '
             'note the preview cells, the wands taken and the blocks placed (a NEO deliberate difference: the original fails mid-route)',
             source='ItemConveyorWand.java:411-457 (route on the real world); NEO ConveyorWandItem.construct:365-444'),
    ]


NAMES = dict(zh_cn=dict(conveyor='输送带', conveyor_express='快速输送带', conveyor_double='双轨道输送带', conveyor_triple='三轨道输送带',
                        conveyor_lift='垂直输送带', conveyor_chute='输送带滑槽'),
             en_us=dict(conveyor='Conveyor Belt', conveyor_express='Express Conveyor Belt', conveyor_double='Double-Lane Conveyor Belt',
                        conveyor_triple='Triple-Lane Conveyor Belt', conveyor_lift='Conveyor Chain Lift', conveyor_chute='Conveyor Chute'))


def sneak(ctx, on):
    ctx.step('key', key='key.keyboard.left.shift', action='press' if on else 'release', after=3)


def chat_since(ctx, started):
    return [m if isinstance(m, str) else m.get('text', '') for m in ctx.step('chat', count=20, since_ms=started).get('messages', [])]


def belts(ctx, a, b):
    d = ctx.step('dump', **{'from': a, 'to': b})
    return [x for x in d['blocks'] if x['block'].startswith('hbmsntm:conveyor')]


def crosshair(ctx, hud):
    w, h = hud['gui_scaled_width'], hud['gui_scaled_height']
    return [t['text'] for t in hud['texts'] if t['x'] >= w // 2 + 6 and h // 2 - 12 <= t['y'] <= h // 2 + 30]


def run(ctx):
    t = TEXT[ctx.capture['lang']]
    _lib.setup_world(ctx, freeze=False)
    # other scenarios sharing the world may have left belts here (their areas overlap this one); the chunks load first
    ctx.step('view', pos=[34.5, Y + 30, 22.5], pitch=90.0, yaw=180.0, fly=True, hide_gui=False)
    ctx.step('wait', ticks=60)
    ctx.step('cmd', command='fill -2 %d -2 70 %d 46 minecraft:air' % (Y, Y + 4), allow_error=True)
    ctx.step('cmd', command='kill @e[type=!minecraft:player,x=34,y=%d,z=22,distance=..60]' % Y, allow_error=True)
    ctx.step('wait', ticks=2)  # animals killed above drop their loot
    ctx.step('cmd', command='kill @e[type=minecraft:item,x=34,y=%d,z=22,distance=..60]' % Y, allow_error=True)
    ctx.step('cmd', command='item replace entity @s weapon.mainhand with %s 64' % WAND)
    # clicks stay within reach (4.5 blocks survival, 5 creative); route from the east face of a stone at x 0 to the west face of a stone 10 east and 3 up
    for x, y in ((0, Y), (11, Y + 3)):
        ctx.step('cmd', command='setblock %d %d 0 minecraft:stone' % (x, y))
    ctx.step('view', pos=[2.5, Y, 2.5], look_at=[1.0, Y + 0.5, 0.5], fly=True, hide_gui=False)
    ctx.step('use', target=dict(pos=[0, Y, 0], face='east'), after=4)
    ctx.step('view', pos=[9.5, Y + 3, 2.5], look_at=[11.0, Y + 3.5, 0.5], fly=True, hide_gui=False)
    ctx.step('wait', ticks=6)
    p = ctx.step('preview')
    blocks = p.get('blocks', [])
    ctx.check('conveyors.preview-valid', p.get('present') and p.get('success') is True and len(blocks) >= 10,
              'preview present=%s success=%s blocks=%d' % (p.get('present'), p.get('success'), len(blocks)))
    lifts = [b['block'] for b in blocks if b['block'] in ('hbmsntm:conveyor_lift', 'hbmsntm:conveyor_chute')]
    ctx.check('conveyors.preview-lifts', len(lifts) >= 3, 'vertical pieces in the preview: %s' % lifts)
    shot = ctx.step('shot', file=ctx.shot_name('preview-valid'))['image']['file']
    started = ctx.step('use', target=dict(pos=[11, Y + 3, 0], face='west'), after=6)['started_ms']
    lines = chat_since(ctx, started)
    built = belts(ctx, [0, Y, -1], [11, Y + 4, 1])
    after = ctx.step('preview')
    ctx.check('conveyors.built-message', any(t['built'] in l for l in lines) and len(built) >= 10 and not after.get('present'),
              'chat %s; %d belt blocks built; preview after: %s' % (lines, len(built), after.get('present')), [shot])
    # blocked: a wall across a straight route
    ctx.step('cmd', command='setblock 0 %d 6 minecraft:stone' % Y)
    ctx.step('cmd', command='setblock 11 %d 6 minecraft:stone' % Y)
    ctx.step('cmd', command='fill 5 %d 4 5 %d 8 minecraft:stone' % (Y, Y + 4))
    ctx.step('view', pos=[2.5, Y, 8.5], look_at=[1.0, Y + 0.5, 6.5], fly=True, hide_gui=False)
    ctx.step('use', target=dict(pos=[0, Y, 6], face='east'), after=4)
    ctx.step('view', pos=[9.5, Y, 8.5], look_at=[11.0, Y + 0.5, 6.5], fly=True, hide_gui=False)
    ctx.step('wait', ticks=6)
    p = ctx.step('preview')
    shot = ctx.step('shot', file=ctx.shot_name('preview-blocked'))['image']['file']
    ctx.check('conveyors.preview-blocked', p.get('present') and p.get('success') is False,
              'preview present=%s success=%s' % (p.get('present'), p.get('success')), [shot])
    started = ctx.step('use', target=dict(pos=[11, Y, 6], face='west'), after=6)['started_ms']
    lines = chat_since(ctx, started)
    ctx.check('conveyors.blocked-message', any(t['blocked'] in l for l in lines) and not belts(ctx, [1, Y, 6], [10, Y, 6]),
              'chat %s' % lines)
    # hand switch clears the preview
    ctx.step('cmd', command='item replace entity @s hotbar.0 with %s 64' % WAND)
    ctx.step('key', key='key.keyboard.1', after=2)
    ctx.step('view', pos=[2.5, Y, 8.5], look_at=[1.0, Y + 0.5, 6.5], fly=True, hide_gui=False)
    ctx.step('use', target=dict(pos=[0, Y, 6], face='east'), after=4)
    ctx.step('wait', ticks=4)
    before = ctx.step('preview').get('present')
    ctx.step('key', key='key.keyboard.2', after=6)
    gone = ctx.step('preview').get('present')
    ctx.check('conveyors.hand-switch', before and not gone, 'preview before switch %s, after %s' % (before, gone))
    ctx.step('cmd', command='clear @s')
    # survival counting on a flat 10-belt route (z 20)
    ctx.step('cmd', command='gamemode survival')
    ctx.step('cmd', command='setblock 0 %d 20 minecraft:stone' % Y)
    ctx.step('cmd', command='setblock 11 %d 20 minecraft:stone' % Y)
    ctx.step('cmd', command='give @s %s 5' % WAND)
    ctx.step('key', key='key.keyboard.1', after=2)
    ctx.step('view', pos=[2.5, Y, 22.5], look_at=[1.0, Y + 0.5, 20.5], fly=False, hide_gui=False)
    ctx.step('use', target=dict(pos=[0, Y, 20], face='east'), after=4)
    ctx.step('view', pos=[9.5, Y, 22.5], look_at=[11.0, Y + 0.5, 20.5], fly=False, hide_gui=False)
    started = ctx.step('use', target=dict(pos=[11, Y, 20], face='west'), after=6)['started_ms']
    lines = chat_since(ctx, started)
    inv = ctx.step('inv')
    left = sum(s['count'] for s in inv['slots'] if s['item'] == WAND)
    ctx.check('conveyors.short-message', any(t['short'] in l for l in lines) and left == 5 and not belts(ctx, [1, Y, 20], [10, Y, 20]),
              'chat %s; wands left %d' % (lines, left))
    # recount: 20 wands at the first click, 16 dropped before the second
    ctx.step('cmd', command='give @s %s 15' % WAND)
    ctx.step('view', pos=[2.5, Y, 22.5], look_at=[1.0, Y + 0.5, 20.5], fly=False, hide_gui=False)
    ctx.step('use', target=dict(pos=[0, Y, 20], face='east'), after=4)
    ctx.step('cmd', command='clear @s %s 16' % WAND)
    ctx.step('view', pos=[9.5, Y, 22.5], look_at=[11.0, Y + 0.5, 20.5], fly=False, hide_gui=False)
    started = ctx.step('use', target=dict(pos=[11, Y, 20], face='west'), after=6)['started_ms']
    lines = chat_since(ctx, started)
    ctx.check('conveyors.recount', any(t['short'] in l for l in lines) and not belts(ctx, [1, Y, 20], [10, Y, 20]),
              'chat after dropping to 4 wands: %s' % lines)
    # consumption: 20 wands, route of 10
    ctx.step('cmd', command='give @s %s 16' % WAND)
    ctx.step('view', pos=[2.5, Y, 22.5], look_at=[1.0, Y + 0.5, 20.5], fly=False, hide_gui=False)
    ctx.step('use', target=dict(pos=[0, Y, 20], face='east'), after=4)
    ctx.step('view', pos=[9.5, Y, 22.5], look_at=[11.0, Y + 0.5, 20.5], fly=False, hide_gui=False)
    ctx.step('use', target=dict(pos=[11, Y, 20], face='west'), after=6)
    placed = len(belts(ctx, [1, Y, 20], [10, Y, 20]))
    inv = ctx.step('inv')
    left = sum(s['count'] for s in inv['slots'] if s['item'] == WAND)
    ctx.check('conveyors.consumption', placed == 10 and left == 20 - placed, '%d belts placed, %d of 20 wands left' % (placed, left))
    ctx.step('cmd', command='clear @s')
    ctx.step('cmd', command='gamemode creative')
    # empty hand on a belt: no look overlay
    ctx.step('view', pos=[5.5, Y + 1.5, 22.5], look_at=[5.5, Y + 0.1, 20.5], fly=True, hide_gui=False)
    ctx.step('wait', ticks=3)
    hud, problems = _lib.hud_on(ctx, (5, Y, 20))
    control = _lib.look_control(ctx, 5, Y, 26)
    ctx.check('conveyors.aim-overlay', not crosshair(ctx, hud) and bool(control) and not problems,
              'texts at the crosshair: %s; same read: %s; control (standard fluid duct, same view and read): %s'
              % (crosshair(ctx, hud), '; '.join(problems) or 'action-bar probe read, crosshair on the belt', control))
    # creative line break: 70 belts along +x at z 40 (input west, items travel east), break the 36th from the west
    ctx.step('cmd', command='kill @e[type=!minecraft:player,x=34,y=%d,z=40,distance=..45]' % Y, allow_error=True)
    ctx.step('wait', ticks=2)
    ctx.step('cmd', command='kill @e[type=minecraft:item,x=34,y=%d,z=40,distance=..45]' % Y, allow_error=True)
    ctx.step('cmd', command='fill 0 %d 40 69 %d 40 hbmsntm:conveyor[facing=west,shape=straight]' % (Y, Y))
    ctx.step('cmd', command='fill 0 %d 44 9 %d 44 hbmsntm:conveyor[facing=west,shape=straight]' % (Y, Y))
    ctx.step('cmd', command='item replace entity @s weapon.mainhand with %s' % WAND)
    ctx.step('view', pos=[35.5, Y, 42.5], look_at=[35.5, Y + 0.1, 40.5], fly=False, hide_gui=False)
    sneak(ctx, True)
    ctx.step('wait', ticks=3)
    hud = ctx.step('hud', frames=6)
    texts = crosshair(ctx, hud)
    ctx.check('conveyors.break-overlay', t['name'] in texts and t['break_line'] in texts, 'texts at the crosshair: %s' % texts)
    ctx.step('attack', target=dict(pos=[35, Y, 40], face='up', offset=[0, -0.8, 0]), any_hit=True, after=6)
    sneak(ctx, False)
    ctx.step('wait', ticks=10)
    left = sorted(b['pos'][0] for b in belts(ctx, [0, Y, 40], [69, Y, 40]))
    drops = [e for e in ctx.step('dump', **{'from': [-2, Y - 1, 38], 'to': [72, Y + 2, 42]}, entities=True)['entities'] if e['type'] == 'minecraft:item']
    want = list(range(0, 4)) + list(range(65, 70))
    ctx.check('conveyors.break-line', left == [float(x) for x in want] and not drops, 'belts left at x %s (want %s); drops %d' % (left, want, len(drops)))
    ctx.step('view', pos=[4.5, Y, 46.5], look_at=[4.5, Y + 0.1, 44.5], fly=False, hide_gui=False)
    ctx.step('attack', target=dict(pos=[4, Y, 44], face='up', offset=[0, -0.8, 0]), any_hit=True, after=6)
    ctx.step('wait', ticks=6)
    n = len(belts(ctx, [0, Y, 44], [9, Y, 44]))
    ctx.check('conveyors.break-single', n == 9, '%d of 10 belts left after a plain break' % n)
    look_names(ctx)
    preview_update(ctx)
    self_cross(ctx)


def look_names(ctx):
    names = NAMES[ctx.capture['lang']]
    z = 52
    ctx.step('cmd', command='fill -2 %d %d 30 %d %d minecraft:air' % (Y, z - 2, Y + 4, z + 4), allow_error=True)
    kinds = list(names)
    for i, k in enumerate(kinds):
        state = '[facing=west,shape=straight]' if k in ('conveyor', 'conveyor_express', 'conveyor_double', 'conveyor_triple') else ''
        ctx.step('cmd', command='setblock %d %d %d hbmsntm:%s%s' % (3 * i, Y, z, k, state))
    ctx.step('cmd', command='clear @s', allow_error=True)
    ctx.step('cmd', command='item replace entity @s weapon.mainhand with %s' % WAND)
    _lib.placed(ctx)
    got = {}
    sneak(ctx, True)
    for i, k in enumerate(kinds):
        ctx.step('view', pos=[3 * i + 0.5, Y, z + 2.5], look_at=[3 * i + 0.5, Y + 0.3, z + 0.5], fly=False, hide_gui=False)
        ctx.step('wait', ticks=3)
        got[k] = crosshair(ctx, ctx.step('hud', frames=6))
    # off hand only, same aim at the regular belt
    ctx.step('cmd', command='item replace entity @s weapon.mainhand with minecraft:air')
    ctx.step('cmd', command='item replace entity @s weapon.offhand with %s' % WAND)
    ctx.step('view', pos=[0.5, Y, z + 2.5], look_at=[0.5, Y + 0.3, z + 0.5], fly=False, hide_gui=False)
    ctx.step('wait', ticks=3)
    off = crosshair(ctx, ctx.step('hud', frames=6))
    sneak(ctx, False)
    ctx.step('cmd', command='item replace entity @s weapon.offhand with minecraft:air')
    ok = all(names[k] in got[k] for k in kinds)
    ctx.check('conveyors.look-names', ok, 'texts at the crosshair per block %s' % got)
    ctx.check('conveyors.offhand-text', not off and names['conveyor'] in got['conveyor'],
              'off-hand wand: texts at the crosshair %s; main-hand control %s' % (off, got['conveyor']))


def preview_update(ctx):
    z = 60
    ctx.step('cmd', command='fill -2 %d %d 30 %d %d minecraft:air' % (Y, z - 2, Y + 4, z + 8), allow_error=True)
    for x, zz in ((0, z), (8, z), (8, z + 5)):
        ctx.step('cmd', command='setblock %d %d %d minecraft:stone' % (x, Y, zz))
    ctx.step('cmd', command='item replace entity @s weapon.mainhand with %s 64' % WAND)
    ctx.step('key', key='key.keyboard.1', after=2)
    ctx.step('view', pos=[2.5, Y, z + 2.5], look_at=[1.0, Y + 0.5, z + 0.5], fly=True, hide_gui=False)
    ctx.step('use', target=dict(pos=[0, Y, z], face='east'), after=4)
    seen = []
    for label, look in (('A west', [8.0, Y + 0.5, z + 0.5]), ('B west', [8.0, Y + 0.5, z + 5.5]), ('sky', None), ('A west again', [8.0, Y + 0.5, z + 0.5])):
        if look is None:
            ctx.step('view', pos=[5.5, Y + 1, z + 2.5], pitch=-80.0, yaw=0.0, fly=True, hide_gui=False)
        else:
            ctx.step('view', pos=[5.5, Y + 1, z + 2.5], look_at=look, fly=True, hide_gui=False)
        ctx.step('wait', ticks=4)
        p = ctx.step('preview')
        cells = sorted(tuple(b['pos']) for b in p.get('blocks', []))
        seen.append((label, bool(p.get('present')), p.get('success'), cells))
    shot = ctx.step('shot', file=ctx.shot_name('preview-update'))['image']['file']
    ctx.step('key', key='key.keyboard.2', after=4)  # drop the start
    a, b, sky, back = seen
    ok = (a[1] and a[2] is True and b[1] and b[3] != a[3] and not sky[1] and back[1] and back[3] == a[3])
    ctx.check('conveyors.preview-update', ok, '; '.join('%s: present %s success %s cells %d' % (l, pr, su, len(c)) for l, pr, su, c in seen), [shot])


def self_cross(ctx):
    """Explorer-traced geometry (route walks A=(0,0,0) up to (0,1,0), down to A again, then south); built floating so
    the cell under A is air. Offsets from (bx, by, bz)."""
    bx, by, bz = 20, Y + 5, 60
    ctx.step('cmd', command='fill %d %d %d %d %d %d minecraft:air' % (bx - 4, by - 2, bz - 2, bx + 4, by + 3, bz + 6), allow_error=True)
    for dx, dy, dz in ((-1, 0, 0), (1, 0, 0), (0, 2, 0), (0, 0, 2)):
        ctx.step('cmd', command='setblock %d %d %d minecraft:stone' % (bx + dx, by + dy, bz + dz))
    ctx.step('cmd', command='setblock %d %d %d hbmsntm:crane_inserter[input=north,output=south]' % (bx, by, bz + 4))
    ctx.step('cmd', command='fill %d %d %d %d %d %d minecraft:stone' % (bx + 2, by - 1, bz + 2, bx + 3, by - 1, bz + 3))
    ctx.step('cmd', command='clear @s', allow_error=True)
    ctx.step('cmd', command='gamemode survival')
    ctx.step('cmd', command='give @s %s 20' % WAND)
    ctx.step('key', key='key.keyboard.1', after=2)
    # the player stands on a platform east of the route, so the start block's east face looks at it
    ctx.step('view', pos=[bx + 2.5, by, bz + 2.5], look_at=[bx, by + 0.5, bz + 0.5], fly=False, hide_gui=False)
    ctx.step('use', target=dict(pos=[bx - 1, by, bz], face='east'), after=4)
    ctx.step('view', pos=[bx + 2.5, by, bz + 2.5], look_at=[bx + 0.5, by + 1.0, bz + 4.5], fly=False, hide_gui=False)
    ctx.step('wait', ticks=6)
    p = ctx.step('preview')
    cells = sorted(tuple(b['pos']) for b in p.get('blocks', []))
    started = ctx.step('use', target=dict(pos=[bx, by, bz + 4], face='up'), any_hit=True, after=6)['started_ms']
    lines = chat_since(ctx, started)
    left = sum(s['count'] for s in ctx.step('inv')['slots'] if s['item'] == WAND)
    placed = [(tuple(int(c) - o for c, o in zip(b['pos'], (bx, by, bz))), b['block'].split(':')[1])
              for b in ctx.step('dump', **{'from': [bx - 1, by - 1, bz - 1], 'to': [bx + 1, by + 2, bz + 5]})['blocks'] if b['block'].startswith('hbmsntm:conveyor')]
    ctx.step('cmd', command='clear @s', allow_error=True)
    ctx.step('cmd', command='gamemode creative')
    ctx.review('conveyors.route-self-cross', 'preview present %s success %s with %d cells; chat %s; wands taken %d of 20; conveyor blocks placed %d: %s' % (
        p.get('present'), p.get('success'), len(cells), lines, 20 - left, len(placed), sorted(placed)))
