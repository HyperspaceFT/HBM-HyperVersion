"""Conveyor sorter, splitter and acidizer input partitioner: looks, screen, filter modes, routing, ratio, batches, texts.

Expected values follow the 1.7.10 original at cd0cff450 and the deliberate NEO differences stated in the NEO port:
- sorter faces: the inserter's input icon with the crane_router_overlay drawn once per face, tinted by face index 0-5 red
  ff0000, orange ff8000, yellow ffff00, green 00ff00, blue 0080ff, purple 8000ff (CraneRouter.java:80-92); NEO's item icon
  is the untinted input icon (deliberate).
- sorter screen 256x201, title centred (GUICraneRouter.java:33-34,96); a mode button cycles OFF, WHITELIST, BLACKLIST,
  WILDCARD and shows the mode name on hover (GUICraneRouter.java:41-72); NEO answers the left button only (deliberate).
- filter slots take a one-item copy; the first mode is the first ingot, block, dust, nugget or plate entry of the item
  (ContainerCraneRouter / ModulePatternMatcher.initPatternSmart; NEO: c:ingots/<m>, c:storage_blocks/<m>, c:dusts/<m>,
  c:nuggets/<m>, c:plates/<m> tags, deliberate); otherwise exact for items with subtypes, wildcard for the rest. The
  original iron powder is dustIron; NEO's iron powder has no c:dusts/iron tag (S:32), so its first mode is recorded, not
  judged. An empty cursor clears a slot.
- routing (CraneRouter.java:122-136, 212-261): whitelist sides whose filter matches and blacklist sides whose filter does not
  match count; wildcard sides only when none counts; with no side the item drops at the centre; a side without a belt
  drops the item 0.55 blocks out on that side (below the block for the down side).
- splitter (CraneSplitter.java): placed facing the placer, the second block to the core's right as seen along travel; the
  look overlay names the block and "ratio l:r", 1:1 by default (:189-203); the screwdriver raises the clicked block's
  share, sneaking lowers it (:164-187); a new splitter at 3:2 sends 5 of 7 items to the core lane and 2 to the other; the ratio survives a
  reload (:54-63); breaking one block removes both and drops one splitter.
- partitioner (CranePartitioner.java): items enter from the input side only; acidizer inputs leave in batches of one cycle
  (16 oil scrap per CrystallizerRecipes), 40 give two batches and keep 8; other items are stored apart and only those can
  be taken out (:189-209); breaking drops everything (:219-247).
- descriptions: the partitioner says it holds up to 45 inputs; the Chinese splitter description has no English "Ratio".
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='conveyor-cranes.sorter-splitter-partitioner',
    feature='conveyor-cranes',
    title='Sorter, splitter, partitioner: looks, screen, filter modes, routing, ratio, batches, texts',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70, hide_gui=False),
)

Y = -60
TINT = dict(down='ff0000', up='ff8000', north='ffff00', south='00ff00', west='0080ff', east='8000ff')
# the screen title is the inventory name container.craneRouter (TileEntityCraneRouter.java:42), "Conveyor Router" in
# en_US.lang:656, not the block name "Conveyor Sorter"
T = dict(zh_cn=dict(modes=['关闭', '白名单', '黑名单', '通配'], title='输送带分拣机', tag='物品标签匹配：', exact='物品与元数据相同', wild='物品相同',
                    ratio='分离比例：', splitter='输送带分离器', part45='至多45份'),
         en_us=dict(modes=['OFF', 'WHITELIST', 'BLACKLIST', 'WILDCARD'], title='Conveyor Router', tag='Item tag matches: ',
                    exact='Item and meta match', wild='Item matches', ratio='Splitter ratio: ', splitter='Conveyor Splitter', part45='45'))
# filter item, expected first mode ('tag' with the tag, or 'wild')
FILTER_ITEMS = [('minecraft:iron_ingot', 'tag', 'c:ingots/iron'), ('minecraft:iron_block', 'tag', 'c:storage_blocks/iron'),
                ('hbmsntm:powder_iron', 'record', 'c:dusts/iron'), ('minecraft:iron_nugget', 'tag', 'c:nuggets/iron'),
                ('hbmsntm:plate_steel', 'tag', 'c:plates/steel'), ('minecraft:cobblestone', 'wild', None)]
SIDE = dict(down=0, up=1, north=2, south=3, west=4, east=5)


def expectations():
    E = [('sorter-faces', 'each sorter face shows the input icon plus the overlay tinted by face index', 'CraneRouter.java:80-92'),
         ('sorter-icon', 'sorter item icon: the input icon only, untinted (NEO deliberate)', 'deliberate NEO difference'),
         ('sorter-look', 'sorter from six sides: overlay colours over the base, no dark or missing faces', 'CraneRouter.java:80-92'),
         ('sorter-screen', 'sorter screen 256x201 with the title centred', 'GUICraneRouter.java:33-34,96'),
         ('sorter-buttons', 'a mode button cycles OFF, WHITELIST, BLACKLIST, WILDCARD with those hover names; right click does nothing',
          'GUICraneRouter.java:41-72; NEO left button only'),
         ('sorter-filter-modes', 'first filter mode: iron ingot, iron block, iron nugget, steel plate their c: material tag; cobblestone wildcard',
          'ModulePatternMatcher.initPatternSmart; NEO tags for the ore dictionary prefixes of the original'),
         ('sorter-filter-powder', 'record: the first filter mode of iron powder (the original registers it as dustIron, OreDictManager.java:336; '
          'NEO gives no powder but aluminium a c:dusts tag, so it falls back to exact or wildcard)', 'record item, no pass line'),
         ('sorter-filter-take', 'putting into a filter slot leaves the cursor stack whole and the slot holds one item; an empty cursor clears it',
          'ContainerCraneRouter.java:31-58'),
         ('sorter-route', 'east whitelist iron, west blacklist iron, south wildcard: iron goes east only, cobblestone west only, nothing south',
          'CraneRouter.java:212-261'),
         ('sorter-route-random', 'east and west both whitelist iron, south wildcard: twenty iron ingots spread over east and west (each gets '
          'some), none south; a gold ingot matches no filter and goes south (the wildcard side is used only when no other side is valid)',
          'CraneRouter.java:212-261 (world random among the valid sides, :259; wildcard only when none, :247-253)'),
         ('sorter-route-down', 'a whitelisted down side without a belt drops the item below the sorter', 'CraneRouter.java:138-157'),
         ('sorter-route-none', 'no valid side: the item drops at the sorter centre', 'CraneRouter.java:122-136'),
         ('splitter-place', 'placed looking each of four directions: facing the placer, second block on the core\'s right along travel',
          'CraneSplitter.java:58-65; DummyableBlock placement'),
         ('splitter-overlay', 'aiming at either splitter block shows the name and ratio 1:1', 'CraneSplitter.java:189-203'),
         ('splitter-ratio', 'core x3, core sneaking x1, other block x1 gives 3:2', 'CraneSplitter.java:164-187'),
         ('splitter-split', 'a new splitter at 3:2 sends seven items 5 to the core lane and 2 to the other (3:3 would give 4 and 3)',
          'TileEntityCraneSplitter.splitStack'),
         ('splitter-reload', 'after leaving and reopening the world the ratio still reads 3:2', 'TileEntityCraneSplitter.java:54-63'),
         ('splitter-break', 'survival: breaking the second block removes both and drops one splitter', 'DummyableBlock.breakBlock'),
         ('splitter-look', 'splitter: walls along the belt, transparent back, belt texture moving with the items', 'RenderSplitter.java:24-52'),
         ('partitioner-batches', '40 oil scrap give two batches of 16 out of the back into the chest, 8 stay; cobblestone stays stored',
          'TileEntityCranePartitioner.java:150-178'),
         ('partitioner-extract', 'a hopper below takes the stored cobblestone and no oil scrap', 'CranePartitioner.java:189-209'),
         ('partitioner-break', 'survival: breaking the partitioner drops the kept oil scrap', 'CranePartitioner.java:219-247'),
         ('partitioner-cram', 'record: 45 full stacks of oil scrap at once, does the cram clear of 2.5 pop (limit 25)', 'record item, no pass line'),
         ('partitioner-look', 'partitioner: 12/16 high, faces complete, transparent sides', 'RenderPartitioner.java:25,44-48'),
         ('sorter-layout', 'sorter screen: 30 filter slots in two columns of three groups of five at (34 + 18k + 98j, 17 + 26i), player inventory '
          'at (47, 119), hotbar at (47, 177); the picture shows the six group colours and the mode buttons', 'ContainerCraneRouter.java:19-22; GUICraneRouter.java'),
         ('sorter-desc', 'sorter item tooltip: without Shift the hold-Shift hint, with Shift the three description lines in the client language',
          'CraneRouter (ITooltipProvider); block.hbmsntm.crane_router.desc'),
         ('splitter-orient', 'the four placed splitters seen from above: walls, belt and halves turn with the placement', 'RenderSplitter.java'),
         ('partitioner-orient', 'partitioners facing north, east, south and west seen from above: the shape turns with the facing', 'RenderPartitioner.java:44-48'),
         ('partitioner-package', 'a package with oil scrap carried into the partitioner\'s input does not enter; its contents end up outside', 'CranePartitioner (canPackageEnter false)'),
         ('partitioner-faces', 'an inserter from the east side, a hopper above and a hopper on the west side all put oil scrap in (13 kept, under one batch)',
          'TileEntityCranePartitioner getAccessibleSlotsFromSide (all slots on every side)'),
         ('desc-texts', 'partitioner description says up to 45; Chinese splitter description has no English "Ratio"', 'en_US.lang:5433-5448; NEO local wording')]
    return [dict(id='conveyor-cranes.' + i, text=t, source=s) for i, t, s in E]


def data(ctx, x, y, z, path=''):
    r = ctx.step('cmd', command=('data get block %d %d %d %s' % (x, y, z, path)).strip(), wait_ticks=6)
    return ' '.join(m['text'] for m in r.get('messages', []))


def counts(text, item):
    """Items of `item` in a `data get` reply (component-free entries; a missing count is 1)."""
    n = 0
    for entry in re.findall(r'\{[^{}]*id:\s*"%s"[^{}]*\}' % re.escape(item), text):
        m = re.search(r'count:\s*(\d+)', entry)
        n += int(m.group(1)) if m else 1
    return n


def entities(ctx, a, b):
    return ctx.step('dump', **{'from': a, 'to': b}, entities=True)['entities']


def drops(ctx, a, b, item=None):
    return [e for e in entities(ctx, a, b) if e['type'] == 'minecraft:item' and (item is None or e.get('item') == item)]


def total(es):
    out = {}
    for e in es:
        out[e['item']] = out.get(e['item'], 0) + e.get('count', 1)
    return out


def summon_item(ctx, x, y, z, item, count=1):
    ctx.step('cmd', command='summon minecraft:item %.1f %.1f %.1f {Item:{id:"%s",count:%d}}' % (x, y, z, item, count))


def tooltips(ctx):
    return [x['text'][len('tooltip: '):] for x in ctx.step('hud', frames=4)['texts'] if x['text'].startswith('tooltip: ')]


def shots(ctx, name, x, y, z):
    files = []
    for label, eye, yaw, pitch in _lib.views(x, y, z, distance=2.4):
        ctx.step('view', eye=eye, yaw=yaw, pitch=pitch, hide_gui=True)
        ctx.step('settle', **{'from': [x - 2, y - 1, z - 2], 'to': [x + 2, y + 1, z + 2]}, ticks=2)
        files.append(ctx.step('shot', file=ctx.shot_name('%s-%s' % (name, label)))['image']['file'])
    return files


def overlay(ctx, t, cell):
    ctx.step('view', pos=[cell[0] + 0.5, Y, cell[2] + 2.5], look_at=[cell[0] + 0.5, Y + 0.2, cell[2] + 0.5], fly=False, hide_gui=False)
    ctx.step('wait', ticks=3)
    return [x['text'] for x in ctx.step('hud', frames=5)['texts'] if t['ratio'] in x['text'] or x['text'] == t['splitter']]


def splitter_cells(ctx, x, z):
    d = ctx.step('dump', **{'from': [x - 1, Y, z - 1], 'to': [x + 1, Y, z + 1]})
    return {tuple(int(c) for c in b['pos']): b['props'] for b in d['blocks'] if b['block'] == 'hbmsntm:crane_splitter'}


def sorter(ctx, t):
    rx = 400
    ctx.step('cmd', command='setblock %d %d 0 hbmsntm:crane_router' % (rx, Y + 2))
    _lib.placed(ctx)
    d = ctx.step('dump', **{'from': [rx, Y + 2, 0]}, faces=True)['blocks'][0]['faces']
    got = {f: sorted((q['sprite'].split('/')[-1], q.get('tint')) for q in d[f]) for f in _lib.DIRS}
    want = {f: [('crane_in', None), ('crane_router_overlay', TINT[f])] for f in _lib.DIRS}
    ctx.check('conveyor-cranes.sorter-faces', got == want, 'faces (sprite, tint) %s' % got)
    m = ctx.step('itemmodel', item='hbmsntm:crane_router')
    tinted = sorted({q.get('tint') for f in _lib.DIRS for q in m['faces'][f] if q.get('tint') not in (None, -1)})
    ctx.check('conveyor-cranes.sorter-icon', set(m['sprites']) == {'hbmsntm:block/crane_in'}, 'item sprites %s; tints %s' % (sorted(set(m['sprites'])), tinted))
    ctx.review('conveyor-cranes.sorter-look', 'sorter at y %d from six sides' % (Y + 2), shots(ctx, 'sorter', rx, Y + 2, 0))
    # screen: an empty first hotbar slot in hand, the filter items in hotbar slots 1-6 (menu slots 58-63)
    ctx.step('cmd', command='clear @s', allow_error=True)
    for n, (item, _, _) in enumerate(FILTER_ITEMS):
        ctx.step('cmd', command='item replace entity @s hotbar.%d with %s 8' % (n + 1, item))
    ctx.step('cmd', command='setblock %d %d 4 hbmsntm:crane_router' % (rx, Y))
    ctx.step('view', pos=[rx + 0.5, Y, 6.5], look_at=[rx + 0.5, Y + 0.5, 4.5], fly=False, hide_gui=False)
    ctx.step('key', key='key.keyboard.1', action='tap', after=2)
    ctx.step('use', target=dict(pos=[rx, Y, 4], face='south'), after=6)
    ctx.step('screen', expect='Router')
    hud = ctx.step('hud', frames=4)
    left, top = hud['gui_left'], hud['gui_top']
    title = [x for x in hud['texts'] if x['text'] == t['title']]
    ok = (hud.get('image_width'), hud.get('image_height')) == (256, 201) and title and abs(title[0]['x'] - (128 - title[0]['width'] // 2)) <= 1
    ctx.check('conveyor-cranes.sorter-screen', bool(ok), 'size %sx%s title %s' % (hud.get('image_width'), hud.get('image_height'), [(x['x'], x['y'], x['width']) for x in title]))
    sorter_layout(ctx, left, top)
    centre = [left + 7 + 9, top + 16 + 9]  # the down side's button
    before = data(ctx, rx, Y, 4, 'modes')
    ctx.step('click', at=centre, button=1, after=4)
    right_same = data(ctx, rx, Y, 4, 'modes') == before
    names = []
    for _ in range(4):
        ctx.step('hover', at=centre, frames=3)
        tips = tooltips(ctx)
        names.append(tips[0] if tips else None)
        ctx.step('click', at=centre, button=0, after=4)
    ctx.step('hover', at=[left + 128, top + 100], frames=2)
    ctx.check('conveyor-cranes.sorter-buttons', names == t['modes'] and right_same,
              'hover names in order %s; right click left the modes as they were: %s (%s)' % (names, right_same, before))
    modes, take = [], []
    for n, (item, kind, tag) in enumerate(FILTER_ITEMS):
        ctx.step('click', slot=58 + n, after=3)
        put = ctx.step('click', slot=n, after=3)
        ctx.step('click', slot=58 + n, after=3)
        take.append((put['after']['slot_count'], put['after']['carried_count']))
        ctx.step('hover', slot=n, frames=3)
        tips = tooltips(ctx)
        line = next((l for l in tips if l.startswith(t['tag']) or l in (t['exact'], t['wild'])), None)
        if kind == 'record':
            powder = (item, line)
            continue
        good = line == (t['tag'] + tag if kind == 'tag' else t['wild'])
        modes.append((item, line, good))
    cleared = ctx.step('click', slot=5, after=3)['after']['slot_count']
    ctx.check('conveyor-cranes.sorter-filter-modes', all(g for _, _, g in modes), 'mode line per item %s' % [(i, l) for i, l, _ in modes])
    ctx.review('conveyor-cranes.sorter-filter-powder', 'first mode line of %s: %s' % powder)
    ctx.check('conveyor-cranes.sorter-filter-take', all(s == 1 and c == 8 for s, c in take) and cleared == 0,
              '(slot count, cursor count) after each put %s; slot count after an empty-cursor click %s' % (take, cleared))
    ctx.step('close')
    ctx.step('cmd', command='clear @s', allow_error=True)
    # routing: a belt from the north into the sorter; east whitelist iron, west blacklist iron, south wildcard, no belts out
    ctx.step('cmd', command='setblock %d %d 10 hbmsntm:crane_router' % (rx, Y))
    ctx.step('cmd', command='fill %d %d 6 %d %d 9 hbmsntm:conveyor[facing=north,shape=straight]' % (rx, Y, rx, Y))
    ctx.step('cmd', command='item replace block %d %d 10 container.%d with minecraft:iron_ingot' % (rx, Y, SIDE['east'] * 5))
    ctx.step('cmd', command='item replace block %d %d 10 container.%d with minecraft:iron_ingot' % (rx, Y, SIDE['west'] * 5))
    modes6 = [0] * 6
    modes6[SIDE['east']], modes6[SIDE['west']], modes6[SIDE['south']] = 1, 2, 3
    ctx.step('cmd', command='data merge block %d %d 10 {modes:[I;%s]}' % (rx, Y, ','.join(map(str, modes6))))
    # each counted side: a belt away from the sorter into an inserter and a chest
    for side, (dx, dz) in dict(east=(1, 0), west=(-1, 0), south=(0, 1)).items():
        facing = _lib.opposite(side)
        for k in (1, 2):
            ctx.step('cmd', command='setblock %d %d %d hbmsntm:conveyor[facing=%s,shape=straight]' % (rx + k * dx, Y, 10 + k * dz, facing))
        ctx.step('cmd', command='setblock %d %d %d hbmsntm:crane_inserter[input=%s,output=%s]' % (rx + 3 * dx, Y, 10 + 3 * dz, facing, side))
        ctx.step('cmd', command='setblock %d %d %d minecraft:chest' % (rx + 4 * dx, Y, 10 + 4 * dz))
    # whitelisted down side, nothing below: a sorter raised to Y + 3
    ctx.step('cmd', command='setblock %d %d 20 hbmsntm:crane_router' % (rx, Y + 3))
    ctx.step('cmd', command='setblock %d %d 19 hbmsntm:conveyor[facing=north,shape=straight]' % (rx, Y + 3))
    ctx.step('cmd', command='item replace block %d %d 20 container.0 with minecraft:iron_ingot' % (rx, Y + 3))
    ctx.step('cmd', command='data merge block %d %d 20 {modes:[I;1,0,0,0,0,0]}' % (rx, Y + 3))
    # no valid side: all off
    ctx.step('cmd', command='setblock %d %d 26 hbmsntm:crane_router' % (rx, Y))
    ctx.step('cmd', command='setblock %d %d 25 hbmsntm:conveyor[facing=north,shape=straight]' % (rx, Y))
    ctx.step('view', pos=[rx + 4.5, Y + 5, 16.5], look_at=[rx + 0.5, Y, 16.5], fly=True, hide_gui=True)
    _lib.placed(ctx)
    for i in range(4):
        summon_item(ctx, rx + 0.5, Y + 0.6, 6.5, 'minecraft:iron_ingot')
        ctx.step('wait', ticks=12)
        summon_item(ctx, rx + 0.5, Y + 0.6, 6.5, 'minecraft:cobblestone')
        ctx.step('wait', ticks=12)
    summon_item(ctx, rx + 0.5, Y + 3.6, 19.5, 'minecraft:iron_ingot')
    summon_item(ctx, rx + 0.5, Y + 0.6, 25.5, 'minecraft:gold_ingot')
    # the first position the client sees of each dropped item is where the sorter put it (before it falls or rolls)
    tracked = ctx.step('track', center=[rx + 0.5, Y + 2, 23], radius=7, type='minecraft:item', ticks=80)
    firsts = [[round(c, 2) for c in e['first']] for e in tracked.get('entities', [])]
    sides = {}
    for side, (dx, dz) in dict(east=(1, 0), west=(-1, 0), south=(0, 1)).items():
        items = data(ctx, rx + 4 * dx, Y, 10 + 4 * dz, 'Items')
        sides[side] = {k: v for k, v in (('minecraft:iron_ingot', counts(items, 'minecraft:iron_ingot')),
                                         ('minecraft:cobblestone', counts(items, 'minecraft:cobblestone'))) if v}
    ctx.check('conveyor-cranes.sorter-route', sides == dict(east={'minecraft:iron_ingot': 4}, west={'minecraft:cobblestone': 4}, south={}),
              'items in the chest at the end of each side %s' % sides)
    # an item spawned inside a block is pushed out by vanilla physics, so the drop point shows as "near"
    loose = [(e['item'], [round(c, 2) for c in e['pos']]) for e in drops(ctx, [rx - 6, Y - 1, 15], [rx + 6, Y + 4, 30])]
    # a spawned item entity also gets a small random push (vanilla ItemEntity, as EntityItem in 1.7.10), so it may roll a few
    # blocks while falling or leaving the block
    # down side (CraneRouter.java:152, 0.55 below the centre): under the sorter, centred; no valid side (:130): the centre
    below = [p for p in firsts if abs(p[0] - (rx + 0.5)) <= 0.6 and abs(p[2] - 20.5) <= 0.6 and p[1] < Y + 3]
    ctx.check('conveyor-cranes.sorter-route-down', len(below) == 1 and any(i == 'minecraft:iron_ingot' for i, _ in loose),
              'first positions of dropped items %s (raised sorter at %s, %d, 20); where they lie after 80 ticks %s' % (firsts, rx, Y + 3, loose))
    near = [p for p in firsts if abs(p[0] - (rx + 0.5)) <= 0.6 and abs(p[2] - 26.5) <= 0.6 and Y <= p[1] <= Y + 1.2]
    ctx.check('conveyor-cranes.sorter-route-none', len(near) == 1 and any(i == 'minecraft:gold_ingot' for i, _ in loose),
              'first positions of dropped items %s (unset sorter at %s, %d, 26); where they lie after 80 ticks %s' % (firsts, rx, Y, loose))
    sorter_random(ctx, rx + 12)


def sorter_random(ctx, rx):
    ctx.step('cmd', command='setblock %d %d 10 hbmsntm:crane_router' % (rx, Y))
    ctx.step('cmd', command='fill %d %d 6 %d %d 9 hbmsntm:conveyor[facing=north,shape=straight]' % (rx, Y, rx, Y))
    for side in ('east', 'west'):
        ctx.step('cmd', command='item replace block %d %d 10 container.%d with minecraft:iron_ingot' % (rx, Y, SIDE[side] * 5))
    modes6 = [0] * 6
    modes6[SIDE['east']], modes6[SIDE['west']], modes6[SIDE['south']] = 1, 1, 3
    ctx.step('cmd', command='data merge block %d %d 10 {modes:[I;%s]}' % (rx, Y, ','.join(map(str, modes6))))
    for side, (dx, dz) in dict(east=(1, 0), west=(-1, 0), south=(0, 1)).items():
        facing = _lib.opposite(side)
        for k in (1, 2):
            ctx.step('cmd', command='setblock %d %d %d hbmsntm:conveyor[facing=%s,shape=straight]' % (rx + k * dx, Y, 10 + k * dz, facing))
        ctx.step('cmd', command='setblock %d %d %d hbmsntm:crane_inserter[input=%s,output=%s]' % (rx + 3 * dx, Y, 10 + 3 * dz, facing, side))
        ctx.step('cmd', command='setblock %d %d %d minecraft:chest' % (rx + 4 * dx, Y, 10 + 4 * dz))
    ctx.step('view', pos=[rx + 0.5, Y + 8, 10.5], pitch=89.0, yaw=180.0, fly=True, hide_gui=True)
    _lib.placed(ctx)
    # single items, one random draw each (one draw per entering stack)
    for i in range(20):
        summon_item(ctx, rx + 0.5, Y + 0.6, 6.5, 'minecraft:iron_ingot')
        ctx.step('wait', ticks=10)
    summon_item(ctx, rx + 0.5, Y + 0.6, 6.5, 'minecraft:gold_ingot')
    ctx.step('wait', ticks=100)
    got = {}
    for side, (dx, dz) in dict(east=(1, 0), west=(-1, 0), south=(0, 1)).items():
        items = data(ctx, rx + 4 * dx, Y, 10 + 4 * dz, 'Items')
        got[side] = (counts(items, 'minecraft:iron_ingot'), counts(items, 'minecraft:gold_ingot'))
    ok = (got['east'][0] >= 1 and got['west'][0] >= 1 and got['east'][0] + got['west'][0] == 20 and got['south'] == (0, 1)
          and got['east'][1] == 0 and got['west'][1] == 0)
    ctx.check('conveyor-cranes.sorter-route-random', ok, '(iron, gold) in the chest at the end of each side %s (all twenty on one side by chance: 1 in 2^19)' % got)


def sorter_layout(ctx, left, top):
    pos = {}
    for n in list(range(30)) + [30, 57]:
        at = ctx.step('hover', slot=n, frames=1)['at']
        pos[n] = (round(at[0] - left), round(at[1] - top))
    off = (pos[0][0] - 34, pos[0][1] - 17)  # the hover point inside a slot, the same for every slot
    want = {n: (34 + 18 * (n % 5) + 98 * (n // 15) + off[0], 17 + 26 * ((n % 15) // 5) + off[1]) for n in range(30)}
    want[30], want[57] = (47 + off[0], 119 + off[1]), (47 + off[0], 177 + off[1])
    bad = {n: (pos[n], want[n]) for n in pos if pos[n] != want[n]}
    shot = ctx.step('shot', file=ctx.shot_name('sorter-screen'))['image']['file']
    ctx.check('conveyor-cranes.sorter-layout', not bad and 0 <= off[0] <= 16 and 0 <= off[1] <= 16,
              'hover point inside a slot %s; slots off the pattern %s' % (off, bad or 'none'), [shot])


def sorter_desc(ctx):
    lang = ctx.capture['lang']
    want = dict(zh_cn=['根据设定的条件分拣物品', '各面可以设为黑名单、白名单或通配', '只有在没有其他过滤器匹配时才选择通配面'],
                en_us=['Sorts item based on defined criteria', 'Sides can be defined as blacklist, whitelist or wildcard',
                       'Wildcard sides are only chosen if no other filter matches'])[lang]
    hint = dict(zh_cn='按住', en_us='Hold')[lang]
    ctx.step('mod', shift=False)
    plain = ctx.step('itemtip', item='hbmsntm:crane_router')['tooltip']
    ctx.step('mod', shift=True)
    full = ctx.step('itemtip', item='hbmsntm:crane_router')['tooltip']
    ctx.step('mod', shift=False)
    ok = any(hint in l for l in plain[1:]) and not any(w in plain for w in want) and all(w in full for w in want)
    ctx.check('conveyor-cranes.sorter-desc', ok, 'without Shift %s; with Shift %s' % (plain[1:], full[1:]))


def splitter(ctx, t):
    sx = 420
    ctx.step('view', pos=[sx + 10.5, Y + 4, 6.5], pitch=60.0, yaw=180.0, fly=True, hide_gui=True)
    ctx.step('wait', ticks=40)
    ctx.step('cmd', command='item replace entity @s weapon.mainhand with hbmsntm:crane_splitter 8')
    placed = {}
    # stand so the player looks along d onto the ground cell (x, z); the core faces opposite(d), its second block lies to
    # its facing's counter-clockwise side
    for i, d in enumerate(('north', 'east', 'south', 'west')):
        x, z = sx + 6 * i, 0
        vx, vz = _lib.VEC[d][0], _lib.VEC[d][2]
        ctx.step('view', pos=[x + 0.5 - 2 * vx, Y, z + 0.5 - 2 * vz], look_at=[x + 0.5, Y - 0.5, z + 0.5], fly=False, hide_gui=True)
        ctx.step('use', target=dict(pos=[x, Y - 1, z], face='up'), after=6)
        cells = splitter_cells(ctx, x, z)
        facing = _lib.opposite(d)
        ccw = _lib.counter_clockwise(facing)
        want = {(x, Y, z): (facing, 'core'), (x + _lib.VEC[ccw][0], Y, z + _lib.VEC[ccw][2]): (ccw, None)}
        got = {c: (p.get('facing'), 'core' if p.get('type') == 'core' else None) for c, p in cells.items()}
        placed[d] = (got == want, got)
    ctx.check('conveyor-cranes.splitter-place', all(v[0] for v in placed.values()), 'per look direction: (as expected, cells) %s' % placed)
    ctx.step('view', eye=[sx + 9.5, Y + 6, 4.5], look_at=[sx + 9.5, Y, 0.5], hide_gui=True)
    ctx.step('wait', ticks=4)
    ctx.review('conveyor-cranes.splitter-orient', 'splitters placed looking north, east, south, west (left to right), seen from above the south',
               [ctx.step('shot', file=ctx.shot_name('splitter-orient'))['image']['file']])
    # the north-looking one: core (sx, 0) faces south, items come from the south and travel north, second block east
    core, other = (sx, Y, 0), (sx + 1, Y, 0)
    ctx.step('cmd', command='item replace entity @s weapon.mainhand with minecraft:air')
    texts = {c: overlay(ctx, t, c) for c in (core, other)}
    ctx.check('conveyor-cranes.splitter-overlay', all(t['splitter'] in v and t['ratio'] + '1:1' in v for v in texts.values()), 'overlay texts %s' % texts)
    ctx.step('cmd', command='item replace entity @s weapon.mainhand with hbmsntm:screwdriver')
    for c, sneak in [(core, False)] * 3 + [(core, True), (other, False)]:
        ctx.step('view', pos=[c[0] + 0.5, Y, c[2] + 2.5], look_at=[c[0] + 0.5, Y + 0.2, c[2] + 0.5], fly=False, hide_gui=True)
        if sneak:
            ctx.step('key', key='key.keyboard.left.shift', action='press', after=3)
        ctx.step('use', target=dict(pos=list(c), face='up', offset=[0, -0.6, 0]), any_hit=True, after=4)
        if sneak:
            ctx.step('key', key='key.keyboard.left.shift', action='release', after=3)
    ratio = [x for x in overlay(ctx, t, core) if t['ratio'] in x]
    ctx.check('conveyor-cranes.splitter-ratio', ratio == [t['ratio'] + '3:2'], 'ratio text %s' % ratio)
    # seven items from the south into the core block; two output belts north of the cells. Seven tells 3:2 (5 and 2) from
    # 3:3 (4 and 3); ten would give 6 and 4 for both
    ctx.step('cmd', command='fill %d %d 1 %d %d 8 hbmsntm:conveyor[facing=south,shape=straight]' % (sx, Y, sx, Y))
    for c in (core, other):
        ctx.step('cmd', command='fill %d %d -6 %d %d -1 hbmsntm:conveyor[facing=south,shape=straight]' % (c[0], Y, c[0], Y))
    ctx.step('view', pos=[sx + 4.5, Y + 5, -1.5], look_at=[sx + 0.5, Y, -1.5], fly=True, hide_gui=True)
    _lib.placed(ctx)
    for _ in range(7):
        summon_item(ctx, sx + 0.5, Y + 0.6, 8.5, 'minecraft:iron_ingot')
        ctx.step('wait', ticks=12)
    ctx.step('wait', ticks=200)
    lanes = {}
    for c in (core, other):
        es = entities(ctx, [c[0], Y - 1, -10], [c[0], Y + 1, -1])
        lanes['core' if c == core else 'other'] = sum(e.get('count', 1) for e in es if e['type'] in ('minecraft:item', 'hbmsntm:moving_item'))
    ctx.check('conveyor-cranes.splitter-split', lanes == dict(core=5, other=2), 'items per output lane %s' % lanes)
    ctx.review('conveyor-cranes.splitter-look', 'splitter facing south (core west, second block east), items travelling north',
               shots(ctx, 'splitter', sx, Y, 0) + shots(ctx, 'splitter-second', sx + 1, Y, 0))
    ctx.step('leave')
    ctx.step('openworld', world=ctx.run.args.world)
    ctx.step('wait', ticks=40)
    ratio = [x for x in overlay(ctx, t, other) if t['ratio'] in x]
    ctx.check('conveyor-cranes.splitter-reload', ratio == [t['ratio'] + '3:2'], 'ratio text after reopening %s' % ratio)
    ctx.step('cmd', command='gamemode survival')
    ctx.step('cmd', command='item replace entity @s weapon.mainhand with minecraft:diamond_pickaxe')
    ctx.step('view', pos=[other[0] + 0.5, Y, other[2] + 2.5], look_at=[other[0] + 0.5, Y + 0.2, other[2] + 0.5], fly=False, hide_gui=True)
    ctx.step('attack', target=dict(pos=list(other), face='up', offset=[0, -0.6, 0]), any_hit=True, hold=40, after=10)
    left_cells = splitter_cells(ctx, sx, 0)
    got = total(drops(ctx, [sx - 3, Y - 1, -3], [sx + 3, Y + 2, 3], 'hbmsntm:crane_splitter'))
    ctx.check('conveyor-cranes.splitter-break', not left_cells and got == {'hbmsntm:crane_splitter': 1},
              'splitter blocks left %s; splitter items dropped %s' % (sorted(left_cells), got))
    ctx.step('cmd', command='gamemode creative')
    ctx.step('cmd', command='kill @e[type=minecraft:item,distance=..20]', allow_error=True)


def partitioner(ctx):
    px = 460
    ctx.step('view', pos=[px + 4.5, Y + 5, 0.5], look_at=[px + 0.5, Y, 0.5], fly=True, hide_gui=True)
    ctx.step('wait', ticks=40)
    # input side south: items come from the south, batches leave north onto a belt into an inserter and a chest
    ctx.step('cmd', command='setblock %d %d 0 hbmsntm:crane_partitioner[facing=south]' % (px, Y))
    ctx.step('cmd', command='fill %d %d 1 %d %d 6 hbmsntm:conveyor[facing=south,shape=straight]' % (px, Y, px, Y))
    ctx.step('cmd', command='fill %d %d -4 %d %d -1 hbmsntm:conveyor[facing=south,shape=straight]' % (px, Y, px, Y))
    ctx.step('cmd', command='setblock %d %d -5 hbmsntm:crane_inserter[input=south,output=north]' % (px, Y))
    ctx.step('cmd', command='setblock %d %d -6 minecraft:chest' % (px, Y))
    _lib.placed(ctx)
    for _ in range(40):
        summon_item(ctx, px + 0.5, Y + 0.6, 6.5, 'hbmsntm:scrap_oil')
        ctx.step('wait', ticks=4)
    summon_item(ctx, px + 0.5, Y + 0.6, 6.5, 'minecraft:cobblestone', 3)
    ctx.step('wait', ticks=200)
    chest, kept = data(ctx, px, Y, -6, 'Items'), data(ctx, px, Y, 0, 'Items')
    got = (counts(chest, 'hbmsntm:scrap_oil'), counts(kept, 'hbmsntm:scrap_oil'), counts(kept, 'minecraft:cobblestone'))
    ctx.check('conveyor-cranes.partitioner-batches', got == (32, 8, 3), 'chest oil scrap %d; partitioner keeps oil scrap %d, cobblestone %d' % got)
    ctx.review('conveyor-cranes.partitioner-look', 'partitioner, input side south', shots(ctx, 'partitioner', px, Y, 0))
    ctx.step('cmd', command='setblock %d %d 0 minecraft:hopper' % (px, Y - 1))
    ctx.step('wait', ticks=100)
    hopper, kept = data(ctx, px, Y - 1, 0, 'Items'), data(ctx, px, Y, 0, 'Items')
    got = (counts(hopper, 'minecraft:cobblestone'), counts(hopper, 'hbmsntm:scrap_oil'), counts(kept, 'hbmsntm:scrap_oil'))
    ctx.check('conveyor-cranes.partitioner-extract', got == (3, 0, 8), 'hopper cobblestone %d, oil scrap %d; partitioner keeps oil scrap %d' % got)
    # clear the hopper, the belts and the inserter first: dropped items would be carried back in or on to the chest
    ctx.step('cmd', command='data merge block %d %d 0 {Items:[]}' % (px, Y - 1))
    ctx.step('cmd', command='setblock %d %d 0 minecraft:stone' % (px, Y - 1))
    ctx.step('cmd', command='fill %d %d 1 %d %d 6 minecraft:air' % (px, Y, px, Y))
    ctx.step('cmd', command='fill %d %d -5 %d %d -1 minecraft:air' % (px, Y, px, Y))
    ctx.step('cmd', command='kill @e[type=minecraft:item,distance=..30]', allow_error=True)
    ctx.step('cmd', command='clear @s', allow_error=True)
    ctx.step('cmd', command='gamemode survival')
    ctx.step('cmd', command='item replace entity @s weapon.mainhand with minecraft:diamond_pickaxe')
    # a survival player picks up drops that fly within about a block of it: stand back and count the inventory too
    ctx.step('view', pos=[px + 3.5, Y, 0.5], look_at=[px + 0.5, Y + 0.3, 0.5], fly=False, hide_gui=True)
    ctx.step('attack', target=dict(pos=[px, Y, 0], face='east'), any_hit=True, hold=40, after=10)
    got = total(drops(ctx, [px - 3, Y - 1, -3], [px + 4, Y + 2, 3]))
    picked = total([s for s in ctx.step('inv').get('slots', []) if s['item'] != 'minecraft:diamond_pickaxe'])
    both = {k: got.get(k, 0) + picked.get(k, 0) for k in set(got) | set(picked)}
    ctx.check('conveyor-cranes.partitioner-break', both.get('hbmsntm:scrap_oil') == 8 and both.get('hbmsntm:crane_partitioner') == 1,
              'drops after breaking %s; picked up by the player %s' % (got, picked))
    ctx.step('cmd', command='gamemode creative')
    partitioner_more(ctx, px)
    # record: 45 full stacks at once, no output belt (the batches leave onto the partitioner itself and fall off north)
    ctx.step('cmd', command='setblock %d %d 20 hbmsntm:crane_partitioner[facing=south]' % (px, Y))
    ctx.step('view', pos=[px + 6.5, Y + 6, 20.5], look_at=[px + 0.5, Y, 20.5], fly=True, hide_gui=True)
    _lib.placed(ctx)
    ctx.step('sounds', action='start')
    for slot in range(45):
        ctx.step('cmd', command='item replace block %d %d 20 container.%d with hbmsntm:scrap_oil 64' % (px, Y, slot))
    ctx.step('wait', ticks=420)
    pops = [s for s in ctx.step('sounds', action='stop').get('sounds', []) if 'explosion_tiny' in s['event']]
    left = counts(data(ctx, px, Y, 20, 'Items'), 'hbmsntm:scrap_oil')
    ground = total(drops(ctx, [px - 4, Y - 1, 14], [px + 4, Y + 2, 21]))
    ctx.review('conveyor-cranes.partitioner-cram', '45 stacks of 64 put in: %d tiny explosions heard, %d oil scrap left inside, items on the ground %s' % (
        len(pops), left, ground))


def partitioner_more(ctx, px):
    # four facings in a row, seen from above
    for i, f in enumerate(('north', 'east', 'south', 'west')):
        ctx.step('cmd', command='setblock %d %d 40 hbmsntm:crane_partitioner[facing=%s]' % (px + 3 * i, Y, f))
    ctx.step('view', eye=[px + 4.5, Y + 5, 44.5], look_at=[px + 4.5, Y, 40.5], fly=True, hide_gui=True)
    _lib.placed(ctx)
    ctx.review('conveyor-cranes.partitioner-orient', 'partitioners facing north, east, south, west (left to right), seen from above the south',
               [ctx.step('shot', file=ctx.shot_name('partitioner-orient'))['image']['file']])
    # a package on the belt into the input side
    x = px + 16
    ctx.step('cmd', command='setblock %d %d 30 hbmsntm:crane_partitioner[facing=south]' % (x, Y))
    ctx.step('cmd', command='fill %d %d 31 %d %d 35 hbmsntm:conveyor[facing=south,shape=straight]' % (x, Y, x, Y))
    ctx.step('view', pos=[x + 4.5, Y + 5, 32.5], look_at=[x + 0.5, Y, 32.5], fly=True, hide_gui=True)
    _lib.placed(ctx)
    ctx.step('cmd', command='summon hbmsntm:moving_package %.1f %.2f %.1f {count:1,contents:[{slot:0b,id:"hbmsntm:scrap_oil",count:20}]}' % (x + 0.5, Y + 0.25, 35.5))
    ctx.step('wait', ticks=140)
    inside = counts(data(ctx, x, Y, 30, 'Items'), 'hbmsntm:scrap_oil')
    loose = total(drops(ctx, [x - 2, Y - 1, 28], [x + 2, Y + 2, 36])).get('hbmsntm:scrap_oil', 0)
    pk = [e for e in entities(ctx, [x - 2, Y - 1, 28], [x + 2, Y + 2, 36]) if e['type'] == 'hbmsntm:moving_package']
    # the refused package rides on to the belt's end against the input side and opens there: all 20 lie loose, no package left
    ctx.check('conveyor-cranes.partitioner-package', inside == 0 and loose == 20 and not pk,
              'oil scrap inside the partitioner %d; loose oil scrap %d; packages left %d' % (inside, loose, len(pk)))
    # other faces: inserter from the east, hopper above, hopper on the west side
    x = px + 24
    ctx.step('cmd', command='setblock %d %d 30 hbmsntm:crane_partitioner[facing=south]' % (x, Y))
    ctx.step('cmd', command='setblock %d %d 30 hbmsntm:crane_inserter[input=east,output=west]' % (x + 1, Y))
    ctx.step('cmd', command='fill %d %d 30 %d %d 30 hbmsntm:conveyor[facing=east,shape=straight]' % (x + 2, Y, x + 4, Y))
    ctx.step('cmd', command='setblock %d %d 30 minecraft:hopper[facing=down]' % (x, Y + 1))
    ctx.step('cmd', command='setblock %d %d 30 minecraft:hopper[facing=east]' % (x - 1, Y))
    ctx.step('view', pos=[x + 2.5, Y + 6, 34.5], look_at=[x + 1.5, Y, 30.5], fly=True, hide_gui=True)
    _lib.placed(ctx)
    ctx.step('cmd', command='item replace block %d %d 30 container.0 with hbmsntm:scrap_oil 4' % (x, Y + 1))
    ctx.step('cmd', command='item replace block %d %d 30 container.0 with hbmsntm:scrap_oil 3' % (x - 1, Y))
    for _ in range(6):
        summon_item(ctx, x + 4.5, Y + 0.6, 30.5, 'hbmsntm:scrap_oil')
        ctx.step('wait', ticks=8)
    ctx.step('wait', ticks=120)
    inside = counts(data(ctx, x, Y, 30, 'Items'), 'hbmsntm:scrap_oil')
    left = (counts(data(ctx, x, Y + 1, 30, 'Items'), 'hbmsntm:scrap_oil'), counts(data(ctx, x - 1, Y, 30, 'Items'), 'hbmsntm:scrap_oil'),
            counts(data(ctx, x + 1, Y, 30, 'Items'), 'hbmsntm:scrap_oil'))
    ctx.check('conveyor-cranes.partitioner-faces', inside == 13 and left == (0, 0, 0),
              'oil scrap kept in the partitioner %d of 13; left in the top hopper, side hopper, inserter %s' % (inside, left))
    for dx in (-1, 0, 1, 2, 3, 4):
        ctx.step('cmd', command='setblock %d %d 30 minecraft:air' % (x + dx, Y))
    ctx.step('cmd', command='setblock %d %d 30 minecraft:air' % (x, Y + 1))


def run(ctx):
    t = T[ctx.capture['lang']]
    _lib.setup_world(ctx, freeze=False)
    ctx.step('view', pos=[410.5, Y + 4, 10.5], pitch=60.0, yaw=180.0, fly=True, hide_gui=True)
    ctx.step('wait', ticks=60)  # the chunks over there load first
    sorter(ctx, t)
    splitter(ctx, t)
    partitioner(ctx)
    ctx.step('mod', shift=True)
    part = ctx.step('itemtip', item='hbmsntm:crane_partitioner')['tooltip']
    split = ctx.step('itemtip', item='hbmsntm:crane_splitter')['tooltip']
    ctx.step('mod', shift=False)
    ok = any(t['part45'] in l for l in part) and (ctx.capture['lang'] != 'zh_cn' or not any('Ratio' in l for l in split))
    ctx.check('conveyor-cranes.desc-texts', ok, 'partitioner %s; splitter %s' % (part[1:], split[1:]))
    sorter_desc(ctx)

