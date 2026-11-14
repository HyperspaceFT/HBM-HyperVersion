"""Crane filter slots and upgrade slots as a player handles them: clicks, keys, drags, JEI drops, upgrade plugs.

Expected values follow the 1.7.10 original at cd0cff450:
- filter slots are phantom slots (ContainerCraneExtractor.java:84-113, ContainerCraneGrabber.java:79-108): a click puts a
  one-item copy and the cursor keeps its stack; a right click on a filled slot cycles the mode; any other click type sets
  the slot to the cursor (an empty cursor clears it); no click takes an item out, and double-click collecting skips them.
- mode cycle (ModulePatternMatcher.nextMode, :86-131): exact, wildcard, then every tag of the item in sorted order, back to
  exact; an item without subtypes starts at wildcard (initPattern :30-37). NEO lists tags where the original lists ore
  dictionary names (a deliberate NEO difference). Hovering a filled slot shows the red "right click to change" line and the mode line.
- breaking an extractor drops its buffer and upgrades, never the filter copies (TileEntityMachineBase drops; the filter
  slots are cleared copies).
- shift-clicking a stack from the player inventory into an extractor reaches the buffer only when the filter lets it pass
  (a deliberate NEO difference).
- JEI drops (IControlReceiverFilter.java:29-41): targets are the filter slots only; the dropped item lands as the next mode
  of the slot (exact for an empty slot), for the sorter as for the cranes (TileEntityCraneRouter.java:86-92 sets an
  empty pattern to exact).
- upgrade slots: the stack upgrade goes in the upper slot, the ejector upgrade in the lower one, each with the plug sound
  (TileEntityCraneExtractor.java:47-57); NEO takes only the matching upgrade in each slot (a deliberate NEO difference).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='crane-filter-upgrades.filters',
    feature='crane-filter-upgrades',
    title='Filter slots by hand and by JEI, mode cycle, nothing taken out, upgrade slots and plug sound',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70, hide_gui=False),
)

Y = -60
T = dict(zh_cn=dict(right='右键切换', tag='物品标签匹配：', exact='物品与元数据相同', wild='物品相同'),
         en_us=dict(right='Right click to change', tag='Item tag matches: ', exact='Item and meta match', wild='Item matches'))
# filter slots, upgrade slots (stack, ejector), first main-inventory slot, first hotbar slot in the menu
CRANES = dict(crane_extractor=dict(filters=9, upgrades=(18, 19), main=20, hotbar=47, screen='Extractor'),
              crane_grabber=dict(filters=9, upgrades=(9, 10), main=11, hotbar=38, screen='Grabber'),
              crane_unboxer=dict(filters=0, upgrades=(21, 22), main=23, hotbar=50, screen='Unboxer'))


def expectations():
    E = []
    for c in ('extractor', 'grabber'):
        E += [('%s-put' % c, '%s: a click puts one copy, the cursor keeps its 8; an empty cursor clears' % c, 'Container%s :84-113' % c.capitalize()),
              ('%s-cycle' % c, '%s: right clicks run wildcard, the tags in sorted order, exact, back to wildcard; hover shows the red line' % c,
               'ModulePatternMatcher.nextMode :86-131'),
              ('%s-no-take' % c, '%s: shift click, number key, Q, drag and double click never take an item out of a filter slot' % c,
               'Container%s :84-113' % c.capitalize()),
              ('%s-jei' % c, '%s: JEI drop targets are the 9 filter slots; the dropped item lands as exact' % c, 'IControlReceiverFilter.java:29-41')]
    E += [('jei-sorter', 'sorter: JEI drop targets are the 30 filter slots; an iron ingot dropped on an empty slot lands as exact', 'IControlReceiverFilter.java:29-41; TileEntityCraneRouter.java:86-92'),
          ('jei-highlight', 'while dragging from JEI the filter slots light up', 'JEI ghost ingredient handler'),
          ('extractor-shift-in', 'extractor whitelisting iron: shift-clicked cobblestone stays in the inventory, iron goes into the buffer', 'deliberate NEO difference'),
          ('extractor-break-drops', 'breaking an extractor drops buffer, upgrades and itself, no filter copy', 'TileEntityMachineBase drops')]
    for c in CRANES:
        n = c[6:]
        sound = 'each plug with a sound' if c == 'crane_extractor' else 'go in without a sound (the original plays it only for the extractor)'
        E += [('%s-upgrades' % n, '%s: stack upgrade into the upper slot and ejector into the lower %s; swapped or other items refused' % (n, sound),
               'TileEntityCraneExtractor.java:47-57 (TileEntityCraneGrabber/Unboxer play none); deliberate NEO difference')]
    E += [('grabber-shift', 'grabber screen: Shift-clicking a stack upgrade puts it in the upper slot, an ejector upgrade in the lower slot; '
           'an iron ingot stays in the player inventory', 'ContainerCraneGrabber.java:36-76 (NEO also returns after the merge)'),
          ('upgrade-items', 'the six upgrades (stack and ejection speed, Mk.I-III) each have their own icon and their name in the client language',
           'ItemMachineUpgrade; textures upgrade_stack/upgrade_ejector')]
    return [dict(id='crane-filter-upgrades.' + i, text=t, source=s) for i, t, s in E]


def cmd(ctx, command, **kw):
    return ctx.step('cmd', command=command, **kw)


def slots_of(ctx, pos):
    r = ctx.step('cmd', command='data get block %d %d %d Items' % pos, wait_ticks=6)
    text = ' '.join(m['text'] for m in r.get('messages', []))
    out = []
    for entry in re.findall(r'\{[^{}]*id:\s*"[^"]+"[^{}]*\}', text):
        sl, it, ct = re.search(r'Slot:\s*(\d+)b', entry), re.search(r'id:\s*"([^"]+)"', entry), re.search(r'count:\s*(\d+)', entry)
        out.append((int(sl.group(1)) if sl else -1, it.group(1), int(ct.group(1)) if ct else 1))
    return out


def tooltips(ctx):
    return [x['text'][len('tooltip: '):] for x in ctx.step('hud', frames=4)['texts'] if x['text'].startswith('tooltip: ')]


def inv_total(ctx, item):
    inv = ctx.step('inv')
    n = sum(s.get('count', 0) for s in inv['slots'] if s.get('item') == item)
    carried = inv.get('carried') or {}
    return n + (carried.get('count', 0) if carried.get('item') == item else 0)


def slot(ctx, i):
    r = ctx.step('hover', slot=i, frames=2)
    return r.get('item'), r


def mode_line(ctx, t):
    tips = tooltips(ctx)
    return next((l for l in tips if l.startswith(t['tag']) or l in (t['exact'], t['wild'])), None), t['right'] in tips


def open_crane(ctx, c, x):
    ctx.step('cmd', command='setblock %d %d 0 hbmsntm:%s[input=north,output=south]' % (x, Y, c))
    ctx.step('view', pos=[x + 0.5, Y, 2.5], look_at=[x + 0.5, Y + 0.5, 0.5], fly=False, hide_gui=False)
    ctx.step('key', key='key.keyboard.1', action='tap', after=2)
    ctx.step('use', target=dict(pos=[x, Y, 0], face='south'), after=6)
    ctx.step('screen', expect=CRANES[c]['screen'] if c in CRANES else 'Router')


def stock(ctx):
    cmd(ctx, 'clear @s', allow_error=True)
    cmd(ctx, 'item replace entity @s hotbar.1 with minecraft:iron_ingot 8')
    cmd(ctx, 'item replace entity @s hotbar.2 with minecraft:cobblestone 8')
    cmd(ctx, 'item replace entity @s inventory.0 with minecraft:iron_ingot 5')


def phantom(ctx, t, c, x):
    n = c[6:]
    cfg = CRANES[c]
    hb = cfg['hotbar']
    stock(ctx)
    open_crane(ctx, c, x)
    # put and clear
    ctx.step('click', slot=hb + 1, after=3)
    put = ctx.step('click', slot=0, after=3)['after']
    ctx.step('click', slot=hb + 1, after=3)
    ctx.step('click', slot=1, after=3)  # empty cursor on an empty slot: nothing
    ctx.step('click', slot=hb + 1, after=3)
    ctx.step('click', slot=1, after=3)
    ctx.step('click', slot=hb + 1, after=3)
    cleared = ctx.step('click', slot=1, after=3)['after']
    ctx.check('crane-filter-upgrades.%s-put' % n, (put['slot_count'], put['carried_count']) == (1, 8) and cleared['slot_count'] == 0,
              'after a put: slot %d, cursor %d; after an empty-cursor click: slot %d' % (put['slot_count'], put['carried_count'], cleared['slot_count']))
    # mode cycle on slot 0 (iron ingot)
    ctx.step('hover', slot=0, frames=3)
    labels, reds = [], []
    line, red = mode_line(ctx, t)
    labels.append(line)
    reds.append(red)
    for _ in range(12):
        ctx.step('click', slot=0, button=1, after=3)
        ctx.step('hover', slot=0, frames=3)
        line, red = mode_line(ctx, t)
        labels.append(line)
        reds.append(red)
        if line == labels[0]:
            break
    tags = [l[len(t['tag']):] for l in labels[1:-2]]
    ok = (len(labels) >= 4 and labels[0] == t['wild'] and labels[-1] == labels[0] and labels[-2] == t['exact'] and tags and tags == sorted(tags)
          and all(l.startswith(t['tag']) for l in labels[1:-2]) and all(reds))
    ctx.check('crane-filter-upgrades.%s-cycle' % n, ok, 'mode lines in order %s; red line shown each time %s' % (labels, all(reds)))
    # nothing comes out: shift click, number key, Q, drag, double click
    before = inv_total(ctx, 'minecraft:iron_ingot')
    events = []
    ctx.step('mod', shift=True)
    ctx.step('click', slot=0, after=3)
    ctx.step('mod', shift=False)
    events.append(('shift', inv_total(ctx, 'minecraft:iron_ingot')))
    for key, label in (('key.keyboard.3', 'number key'), ('key.keyboard.q', 'Q')):
        ctx.step('click', slot=hb + 1, after=3)
        ctx.step('click', slot=0, after=3)
        ctx.step('click', slot=hb + 1, after=3)
        ctx.step('hover', slot=0, frames=2)
        ctx.step('key', key=key, action='tap', after=4)
        events.append((label, inv_total(ctx, 'minecraft:iron_ingot')))
    ctx.step('click', slot=hb + 1, after=3)
    ctx.step('hover', slot=2, frames=2)
    ctx.step('mouse', action='press', button=0, after=2)
    ctx.step('hover', slot=3, frames=2)
    ctx.step('hover', slot=cfg['main'] + 5, frames=2)
    ctx.step('mouse', action='release', button=0, after=4)
    inv = ctx.step('inv')
    if (inv.get('carried') or {}).get('count'):
        ctx.step('click', slot=hb + 1, after=3)
    events.append(('drag', inv_total(ctx, 'minecraft:iron_ingot')))
    # the drag spreads the cursor over the player slot it crossed; put the 8 back on the hotbar for the double click
    if not ctx.step('hover', slot=hb + 1, frames=2).get('item'):
        ctx.step('click', slot=cfg['main'] + 5, after=3)
        ctx.step('click', slot=hb + 1, after=3)
    ctx.step('click', slot=hb + 1, after=3)
    ctx.step('click', slot=4, after=3)
    ctx.step('click', slot=hb + 1, after=3)
    # a double click is two presses within 250 ms (AbstractContainerScreen), quicker than two click steps
    at = ctx.step('hover', slot=hb + 1, frames=2)['at']
    ctx.step('mouse', action='click', button=0, at=at, hold=1, after=0)
    ctx.step('mouse', action='click', button=0, at=at, hold=1, after=3)
    carried = (ctx.step('inv').get('carried') or {}).get('count', 0)
    ctx.step('click', slot=hb + 1, after=3)
    events.append(('double click', inv_total(ctx, 'minecraft:iron_ingot')))
    filters = [slot(ctx, i)[1] for i in range(5)]
    dropped = [e for e in ctx.step('dump', **{'from': [x - 3, Y - 1, -1], 'to': [x + 3, Y + 3, 5]}, entities=True)['entities'] if e['type'] == 'minecraft:item']
    ok = all(v == before for _, v in events) and not dropped and carried == 13
    ctx.check('crane-filter-upgrades.%s-no-take' % n, ok, 'iron in the player inventory before %d, after each method %s; double click collected %d (13 = 8 + 5, '
              'none from the filter); items dropped %d; filter slot items %s' % (before, events, carried, len(dropped), [f.get('item') for f in filters]))
    ctx.step('close')


def jei(ctx, c, x, n_filters, want_line, t):
    open_crane(ctx, c, x)
    r = ctx.step('jei', action='ghost', item='minecraft:iron_ingot', target=0, allow_fail=True)
    ctx.step('hover', slot=0, frames=3)
    line, _ = mode_line(ctx, t)
    item = ctx.step('hover', slot=0, frames=2).get('item')
    ctx.step('close')
    return r.get('targets'), item, line, r


def upgrades(ctx, c, x):
    cfg = CRANES[c]
    hb = cfg['hotbar']
    cmd(ctx, 'clear @s', allow_error=True)
    for i, item in enumerate(('hbmsntm:upgrade_stack_1', 'hbmsntm:upgrade_ejector_1', 'minecraft:iron_ingot')):
        cmd(ctx, 'item replace entity @s hotbar.%d with %s 1' % (i + 1, item))
    open_crane(ctx, c, x)
    up, low = cfg['upgrades']
    ctx.step('sounds', action='start')
    refused = []
    for src, dst in ((hb + 2, up), (hb + 1, low), (hb + 3, up)):  # ejector into the upper slot, stack into the lower, iron into the upper
        ctx.step('click', slot=src, after=3)
        r = ctx.step('click', slot=dst, after=3)['after']
        refused.append(r['slot_count'] == 0)
        ctx.step('click', slot=src, after=3)
    ctx.step('click', slot=hb + 1, after=3)
    a = ctx.step('click', slot=up, button=1, after=6)['after']
    ctx.step('click', slot=hb + 1, after=3)
    ctx.step('click', slot=hb + 2, after=3)
    b = ctx.step('click', slot=low, button=1, after=6)['after']
    ctx.step('click', slot=hb + 2, after=3)
    ctx.step('wait', ticks=6)
    plugs = [s for s in ctx.step('sounds', action='stop').get('sounds', []) if 'upgrade_plug' in s['event']]
    ctx.step('close')
    want_plugs = 2 if c == 'crane_extractor' else 0
    ok = all(refused) and (a['slot_item'], a['slot_count'], b['slot_item'], b['slot_count']) == ('hbmsntm:upgrade_stack_1', 1, 'hbmsntm:upgrade_ejector_1', 1) and len(plugs) == want_plugs
    ctx.check('crane-filter-upgrades.%s-upgrades' % c[6:], ok, 'refused (ejector up, stack down, iron up) %s; upper %s x%d, lower %s x%d; plug sounds %d (want %d)' % (
        refused, a['slot_item'], a['slot_count'], b['slot_item'], b['slot_count'], len(plugs), want_plugs))


UPGRADE_NAMES = dict(
    zh_cn=dict(upgrade_stack_1='一级堆叠弹出升级', upgrade_stack_2='二级堆叠弹出升级', upgrade_stack_3='三级堆叠弹出升级',
               upgrade_ejector_1='一级弹射速度升级', upgrade_ejector_2='二级弹射速度升级', upgrade_ejector_3='三级弹射速度升级'),
    en_us=dict(upgrade_stack_1='Stack Ejection Upgrade Mk.I', upgrade_stack_2='Stack Ejection Upgrade Mk.II', upgrade_stack_3='Stack Ejection Upgrade Mk.III',
               upgrade_ejector_1='Ejection Speed Upgrade Mk.I', upgrade_ejector_2='Ejection Speed Upgrade Mk.II', upgrade_ejector_3='Ejection Speed Upgrade Mk.III'))


def upgrade_items(ctx):
    names = UPGRADE_NAMES[ctx.capture['lang']]
    got, ok = {}, True
    for u, want in names.items():
        sprites = sorted(set(ctx.step('itemmodel', item='hbmsntm:' + u)['sprites']))
        tip = ctx.step('itemtip', item='hbmsntm:' + u)['tooltip']
        got[u] = (tip[0] if tip else None, sprites)
        ok = ok and bool(tip) and tip[0] == want and sprites == ['hbmsntm:item/' + u]
    ctx.check('crane-filter-upgrades.upgrade-items', ok, '(name, item model sprites) %s' % got)


def grabber_shift(ctx, x):
    hb = CRANES['crane_grabber']['hotbar']
    cmd(ctx, 'clear @s', allow_error=True)
    for i, item in enumerate(('hbmsntm:upgrade_stack_1', 'hbmsntm:upgrade_ejector_1', 'minecraft:iron_ingot')):
        cmd(ctx, 'item replace entity @s hotbar.%d with %s 1' % (i + 1, item))
    open_crane(ctx, 'crane_grabber', x)
    ctx.step('mod', shift=True)
    for src in (hb + 1, hb + 2, hb + 3):
        ctx.step('click', slot=src, after=4)
    ctx.step('mod', shift=False)
    up, low = slot(ctx, 9)[0], slot(ctx, 10)[0]
    iron = slot(ctx, hb + 3)[0]
    filters = [slot(ctx, i)[0] for i in range(9)]
    ctx.step('close')
    ok = (up, low, iron) == ('hbmsntm:upgrade_stack_1', 'hbmsntm:upgrade_ejector_1', 'minecraft:iron_ingot') and not any(filters)
    ctx.check('crane-filter-upgrades.grabber-shift', ok, 'upper slot %s, lower slot %s, hotbar 4 %s, filter slots %s' % (up, low, iron, filters))


def run(ctx):
    t = T[ctx.capture['lang']]
    _lib.setup_world(ctx, freeze=False)
    base = 800
    ctx.step('view', pos=[base + 10.5, Y + 4, 6.5], pitch=60.0, yaw=180.0, fly=True, hide_gui=False)
    ctx.step('wait', ticks=60)
    phantom(ctx, t, 'crane_extractor', base)
    phantom(ctx, t, 'crane_grabber', base + 4)
    # JEI drops
    for c, x, n in (('crane_extractor', base + 8, 'extractor'), ('crane_grabber', base + 12, 'grabber')):
        targets, item, line, raw = jei(ctx, c, x, 9, t['exact'], t)
        ctx.check('crane-filter-upgrades.%s-jei' % n, targets == 9 and item == 'minecraft:iron_ingot' and line == t['exact'],
                  'ghost targets %s; slot 0 now %s with mode line %s; step %s' % (targets, item, line, raw.get('status')))
    cmd(ctx, 'setblock %d %d 0 hbmsntm:crane_router' % (base + 16, Y))
    ctx.step('view', pos=[base + 16.5, Y, 2.5], look_at=[base + 16.5, Y + 0.5, 0.5], fly=False, hide_gui=False)
    ctx.step('use', target=dict(pos=[base + 16, Y, 0], face='south'), after=6)
    ctx.step('screen', expect='Router')
    r = ctx.step('jei', action='ghost', item='minecraft:iron_ingot', target=0, allow_fail=True)
    ctx.step('hover', slot=0, frames=3)
    line, _ = mode_line(ctx, t)
    ctx.step('close')
    ctx.check('crane-filter-upgrades.jei-sorter', r.get('targets') == 30 and line == t['exact'], 'ghost targets %s; mode line %s' % (r.get('targets'), line))
    ctx.not_run('crane-filter-upgrades.jei-highlight', 'JEI draws the target highlight only during a real mouse drag from its list; the executor drops '
                'through the ghost handler, so the highlight is left to a station')
    # shift click into the extractor buffer with a whitelist of iron
    x = base + 20
    stock(ctx)
    cmd(ctx, 'setblock %d %d 0 hbmsntm:crane_extractor[input=north,output=south]' % (x, Y))
    cmd(ctx, 'item replace block %d %d 0 container.0 with minecraft:iron_ingot' % (x, Y))
    cmd(ctx, 'data merge block %d %d 0 {isWhitelist:1b}' % (x, Y))
    ctx.step('view', pos=[x + 0.5, Y, 2.5], look_at=[x + 0.5, Y + 0.5, 0.5], fly=False, hide_gui=False)
    ctx.step('use', target=dict(pos=[x, Y, 0], face='south'), after=6)
    ctx.step('screen', expect='Extractor')
    ctx.step('mod', shift=True)
    ctx.step('click', slot=47 + 2, after=4)
    ctx.step('click', slot=47 + 1, after=4)
    ctx.step('mod', shift=False)
    ctx.step('close')
    held = slots_of(ctx, (x, Y, 0))
    iron = sum(c for sl, i, c in held if 9 <= sl <= 17 and i == 'minecraft:iron_ingot')
    cobble = sum(c for sl, i, c in held if i == 'minecraft:cobblestone')
    ctx.check('crane-filter-upgrades.extractor-shift-in', iron == 8 and not cobble and inv_total(ctx, 'minecraft:cobblestone') == 8,
              'buffer iron %d, cobblestone in the extractor %d, cobblestone kept %d; slots %s' % (iron, cobble, inv_total(ctx, 'minecraft:cobblestone'), held))
    # break drops: buffer 3 dirt, two upgrades, the filter copy must not drop
    cmd(ctx, 'item replace block %d %d 0 container.10 with minecraft:dirt 3' % (x, Y))
    cmd(ctx, 'item replace block %d %d 0 container.18 with hbmsntm:upgrade_stack_1' % (x, Y))
    cmd(ctx, 'item replace block %d %d 0 container.19 with hbmsntm:upgrade_ejector_1' % (x, Y))
    held = slots_of(ctx, (x, Y, 0))
    want = {}
    for sl, i, c in held:
        if sl >= 9:  # buffer and upgrades; slots 0-8 hold the filter copies
            want[i] = want.get(i, 0) + c
    want['hbmsntm:crane_extractor'] = 1
    # the held attack outlasts the extractor; the line of sight behind it ends in bedrock so no second block breaks
    cmd(ctx, 'fill %d %d -1 %d %d 0 minecraft:bedrock' % (x - 1, Y - 1, x + 1, Y - 1))
    cmd(ctx, 'setblock %d %d -1 minecraft:bedrock' % (x, Y))
    cmd(ctx, 'clear @s', allow_error=True)
    cmd(ctx, 'gamemode survival')
    cmd(ctx, 'item replace entity @s weapon.mainhand with minecraft:diamond_pickaxe')
    ctx.step('key', key='key.keyboard.1', action='tap', after=2)
    ctx.step('attack', target=dict(pos=[x, Y, 0], face='south'), any_hit=True, hold=40, after=10)
    got = {}
    for e in ctx.step('dump', **{'from': [x - 3, Y - 1, -2], 'to': [x + 3, Y + 2, 4]}, entities=True)['entities']:
        if e['type'] == 'minecraft:item':
            got[e['item']] = got.get(e['item'], 0) + e['count']
    for s in ctx.step('inv')['slots']:  # drops the survival player walked into
        if s['item'] != 'minecraft:diamond_pickaxe':
            got[s['item']] = got.get(s['item'], 0) + s['count']
    cmd(ctx, 'gamemode creative')
    ctx.check('crane-filter-upgrades.extractor-break-drops', got == want, 'drops %s; want buffer, upgrades and the extractor %s (slots before %s)' % (got, want, held))
    cmd(ctx, 'kill @e[type=minecraft:item,distance=..30]', allow_error=True)
    for i, c in enumerate(CRANES):
        upgrades(ctx, c, base + 24 + 4 * i)
    grabber_shift(ctx, base + 40)
    upgrade_items(ctx)
