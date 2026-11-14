"""The whole creative line: extractor, sorter, inserter, boxer, unboxer, splitter, partitioner; counts at both ends.

Expected values follow the 1.7.10 original at cd0cff450:
- extractor (TileEntityCraneExtractor.java:59-166): takes from the inventory on its output side and puts onto the belt on its
  input side, 64 items per action with the stack upgrade III, every 2 ticks with the ejector upgrade III (:64-83).
- sorter (CraneRouter.java:122-136, 212-261): iron ingots to the whitelisted east side, everything else to the south side
  (blacklist iron); a package is unpacked per stack and leaves as one package per side (:159-188).
- inserter (CraneInserter.java:61-96): puts what enters its input side into the inventory on its output side.
- boxer (TileEntityCraneBoxer.java:41-149): in the 4-stack mode packs 4 full stacks into one package onto the output belt.
- unboxer (CraneUnboxer.java:100-118; TileEntityCraneUnboxer.java:30-92): packages enter through its output side, the
  contents leave onto the belt on the input side, as many items per action as the stack upgrade gives (16 for II).
- splitter (TileEntityCraneSplitter.java:19-46): a stack entering is split by the ratio, 1:1 halves it.
- partitioner (TileEntityCranePartitioner.java:124-138): acidizer inputs leave in batches of one recipe's amount (16 oil
  scrap), onto a belt, into an inserter whose output side is a bottom corner port of the acidizer (MachineCrystallizer.java:53-64).
- acidizer (CrystallizerRecipes.java:109; TileEntityMachineCrystallizer.java:193-213): 16 oil scrap and 100 mB radiosolvent
  make 1 arsenic nugget; it is filled with radiosolvent and power by command (the line is about the cranes).
- nothing is lost or made on the way: the items put in at the start equal the items found at the ends.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='conveyor-cranes.line',
    feature='conveyor-cranes',
    title='Whole creative line: extractor to sorter, inserter, boxer, unboxer, splitter, partitioner, acidizer; counts at both ends',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70, hide_gui=True),
)

Y = -60
OX = 600  # the line starts here, along +x at z = 0, the south branch along +z at x = OX + 5
SCRAP = 'hbmsntm:scrap_oil'
NUGGET = 'hbmsntm:nugget_arsenic'


def expectations():
    E = [('line-iron-branch', 'all 128 iron ingots reach the chest behind the inserter on the whitelisted east side', 'CraneRouter.java:212-261; CraneInserter.java:61-96'),
         ('line-unboxer-pace', 'the unboxer with the stack upgrade II puts the contents onto its belt 16 items at a time', 'TileEntityCraneUnboxer.java:30-92 (:55-63)'),
         ('line-split-lanes', 'the 1:1 splitter sends half of the oil scrap to each lane: 128 toward the partitioner, 128 into the chest', 'TileEntityCraneSplitter.java:19-46'),
         ('line-acidizer', 'partitioner, belt and inserter feed the acidizer: 8 arsenic nuggets from 128 oil scrap, 800 mB radiosolvent used, '
          'nothing left in the partitioner or the acidizer input', 'CrystallizerRecipes.java:109; TileEntityCranePartitioner.java:124-138'),
         ('line-conserved', 'the 384 items taken from the start chest are all found at the ends (16 oil scrap per nugget); none on the ground, none left on the belts',
          'CraneInserter.java:61-96; TileEntityCranePartitioner.java:124-138'),
         ('line-sorter-package', 'a package with iron and cobblestone entering the sorter leaves as one package per side: iron east, cobblestone south',
          'CraneRouter.java:159-188')]
    return [dict(id='conveyor-cranes.' + i, text=t, source=s) for i, t, s in E]


def cmd(ctx, command, **kw):
    return ctx.step('cmd', command=command, **kw)


def data(ctx, x, y, z, path=''):
    r = ctx.step('cmd', command=('data get block %d %d %d %s' % (x, y, z, path)).strip(), wait_ticks=6)
    return ' '.join(m['text'] for m in r.get('messages', []))


def counts(text, item):
    n = 0
    for entry in re.findall(r'\{[^{}]*id:\s*"%s"[^{}]*\}' % re.escape(item), text):
        m = re.search(r'count:\s*(\d+)', entry)
        n += int(m.group(1)) if m else 1
    return n


def belts(ctx, a, b, facing):
    cmd(ctx, 'fill %d %d %d %d %d %d hbmsntm:conveyor[facing=%s,shape=straight]' % (a[0], Y, a[1], b[0], Y, b[1], facing))


def build(ctx, ox, with_sorter_filter=True):
    sx = ox + 5
    cmd(ctx, 'setblock %d %d 0 minecraft:chest' % (ox, Y))
    cmd(ctx, 'setblock %d %d 0 hbmsntm:crane_extractor[input=east,output=west]' % (ox + 1, Y))
    cmd(ctx, 'item replace block %d %d 0 container.18 with hbmsntm:upgrade_stack_3' % (ox + 1, Y))
    cmd(ctx, 'item replace block %d %d 0 container.19 with hbmsntm:upgrade_ejector_3' % (ox + 1, Y))
    belts(ctx, (ox + 2, 0), (ox + 4, 0), 'west')
    cmd(ctx, 'setblock %d %d 0 hbmsntm:crane_router' % (sx, Y))
    cmd(ctx, 'item replace block %d %d 0 container.25 with minecraft:iron_ingot' % (sx, Y))  # east side, first filter slot
    cmd(ctx, 'item replace block %d %d 0 container.15 with minecraft:iron_ingot' % (sx, Y))  # south side, first filter slot
    cmd(ctx, 'data merge block %d %d 0 {modes:[I;0,0,0,2,0,1]}' % (sx, Y))  # south blacklist, east whitelist
    # east branch
    belts(ctx, (sx + 1, 0), (sx + 3, 0), 'west')
    cmd(ctx, 'setblock %d %d 0 hbmsntm:crane_inserter[input=west,output=east]' % (sx + 4, Y))
    cmd(ctx, 'setblock %d %d 0 minecraft:chest' % (sx + 5, Y))
    # south branch
    belts(ctx, (sx, 1), (sx, 3), 'north')
    cmd(ctx, 'setblock %d %d 4 hbmsntm:crane_boxer[input=north,output=south]' % (sx, Y))
    belts(ctx, (sx, 5), (sx, 7), 'north')
    cmd(ctx, 'setblock %d %d 8 hbmsntm:crane_unboxer[input=south,output=north]' % (sx, Y))
    cmd(ctx, 'item replace block %d %d 8 container.21 with hbmsntm:upgrade_stack_2' % (sx, Y))
    belts(ctx, (sx, 9), (sx, 10), 'north')


def run(ctx):
    _lib.setup_world(ctx, freeze=False)
    sx = OX + 5
    ctx.step('view', pos=[sx + 0.5, Y + 12, 7.5], pitch=90.0, yaw=180.0, fly=True, hide_gui=True)
    ctx.step('wait', ticks=60)
    # the splitter is a two-block structure: placed by hand first (a belt under the player would carry it away), looking
    # south onto (sx, 11), so it faces north (items from the north), the second block on the west
    ctx.step('cmd', command='item replace entity @s weapon.mainhand with hbmsntm:crane_splitter')
    ctx.step('view', pos=[sx + 0.5, Y, 9.0], look_at=[sx + 0.5, Y - 0.5, 11.5], fly=False, hide_gui=True)
    ctx.step('use', target=dict(pos=[sx, Y - 1, 11], face='up'), after=6)
    split = {tuple(int(c) for c in b['pos']): b['props'] for b in ctx.step('dump', **{'from': [sx - 1, Y, 11], 'to': [sx + 1, Y, 11]})['blocks']
             if b['block'] == 'hbmsntm:crane_splitter'}
    # the acidizer, also by hand: looking south onto (sx - 1, 18) puts its core at (sx - 1, 19), facing north, the four
    # bottom corners (its item ports) at x sx - 2 and sx, z 18 and 20
    ctx.step('cmd', command='item replace entity @s weapon.mainhand with hbmsntm:machine_crystallizer')
    ctx.step('view', pos=[sx - 1.5, Y, 15.8], look_at=[sx - 0.5, Y - 0.5, 18.5], fly=False, hide_gui=True)
    ctx.step('use', target=dict(pos=[sx - 1, Y - 1, 18], face='up'), after=8)
    acid = {tuple(int(c) for c in b['pos']): b['props'].get('type') for b in ctx.step('dump', **{'from': [sx - 2, Y, 18], 'to': [sx, Y, 20]})['blocks']
            if b['block'] == 'hbmsntm:machine_crystallizer'}
    core = (sx - 1, Y, 19)
    cmd(ctx, 'data merge block %d %d %d {tank:8000,tank_type:"RADIOSOLVENT",power:1000000L}' % core)
    build(ctx, OX)
    belts(ctx, (sx - 1, 12), (sx, 13), 'north')
    cmd(ctx, 'setblock %d %d 14 hbmsntm:crane_partitioner[facing=north]' % (sx, Y))
    cmd(ctx, 'setblock %d %d 14 hbmsntm:crane_inserter[input=north,output=south]' % (sx - 1, Y))
    cmd(ctx, 'setblock %d %d 15 minecraft:chest' % (sx - 1, Y))
    belts(ctx, (sx, 15), (sx, 16), 'north')
    cmd(ctx, 'setblock %d %d 17 hbmsntm:crane_inserter[input=north,output=south]' % (sx, Y))
    ctx.step('cmd', command='item replace entity @s weapon.mainhand with minecraft:air')
    ctx.step('view', pos=[sx + 0.5, Y + 14, 7.5], pitch=90.0, yaw=180.0, fly=True, hide_gui=True)
    _lib.placed(ctx)
    # start: 2 stacks of iron ingots and 4 of oil scrap in the start chest
    for slot, item in enumerate(['minecraft:iron_ingot'] * 2 + [SCRAP] * 4):
        cmd(ctx, 'item replace block %d %d 0 container.%d with %s 64' % (OX, Y, slot, item))
    sizes = []
    for _ in range(90):
        ctx.step('wait', ticks=10)
        es = ctx.step('dump', **{'from': [sx, Y, 9], 'to': [sx, Y, 10]}, entities=True)['entities']
        sizes += [e.get('count') for e in es if e['type'] == 'hbmsntm:moving_item']
    ctx.step('wait', ticks=200)
    # eight acidizer cycles of 101 ticks follow the last batch
    for _ in range(16):
        if counts(data(ctx, *core, 'Items'), NUGGET) >= 8:
            break
        ctx.step('wait', ticks=100)
    acid_items, tank = data(ctx, *core, 'Items'), data(ctx, *core, 'tank')
    start = data(ctx, OX, Y, 0, 'Items')
    chest_a = data(ctx, sx + 5, Y, 0, 'Items')
    chest_b = data(ctx, sx - 1, Y, 15, 'Items')
    part = data(ctx, sx, Y, 14, 'Items')
    ground = ctx.step('dump', **{'from': [OX - 2, Y - 1, -3], 'to': [sx + 7, Y + 2, 21]}, entities=True)['entities']
    left = [(e['type'], e.get('item'), e.get('count')) for e in ground if e['type'] in ('minecraft:item', 'hbmsntm:moving_item', 'hbmsntm:moving_package')]
    iron_a = counts(chest_a, 'minecraft:iron_ingot')
    scrap_b, scrap_p = counts(chest_b, SCRAP), counts(part, SCRAP)
    nuggets, scrap_in = counts(acid_items, NUGGET), counts(acid_items, SCRAP)
    tank_mb = re.search(r'[:：]\s*(\d+)\s*$', tank)
    tank_mb = int(tank_mb.group(1)) if tank_mb else None
    ctx.check('conveyor-cranes.line-iron-branch', iron_a == 128 and counts(chest_a, SCRAP) == 0,
              'chest behind the east inserter: iron %d, oil scrap %d' % (iron_a, counts(chest_a, SCRAP)))
    ctx.check('conveyor-cranes.line-unboxer-pace', bool(sizes) and set(sizes) == {16},
              'stack sizes seen on the belt after the unboxer (sampled every 10 ticks): %s' % sorted(set(sizes)) if sizes else 'no moving item seen after the unboxer')
    ctx.check('conveyor-cranes.line-split-lanes', scrap_b == 128 and scrap_p + scrap_in + 16 * nuggets == 128,
              'oil scrap in the chest behind the second lane %d; toward the partitioner %d (partitioner %d, acidizer input %d, nuggets %d x 16); splitter cells %s' % (
                  scrap_b, scrap_p + scrap_in + 16 * nuggets, scrap_p, scrap_in, nuggets, split))
    ports = sum(1 for v in acid.values() if v == 'extra')
    ctx.check('conveyor-cranes.line-acidizer', ports == 4 and nuggets == 8 and scrap_p == 0 and scrap_in == 0 and tank_mb == 7200,
              'acidizer cells on the bottom layer %s; nuggets %d, oil scrap in its input %d, in the partitioner %d; radiosolvent %s mB (8000 at the start)' % (
                  acid, nuggets, scrap_in, scrap_p, tank_mb))
    got = iron_a + scrap_b + scrap_p + scrap_in + 16 * nuggets + counts(chest_a, SCRAP) + counts(chest_b, 'minecraft:iron_ingot')
    ctx.check('conveyor-cranes.line-conserved', got == 384 and not left and counts(start, 'minecraft:iron_ingot') + counts(start, SCRAP) == 0,
              'found at the ends %d of 384 (nuggets counted as 16 oil scrap); left in the start chest %d; on the ground or belts %s' % (
                  got, counts(start, 'minecraft:iron_ingot') + counts(start, SCRAP), left))
    # a package through a sorter: east whitelist iron into an inserter and chest, south blacklist iron likewise
    px = OX + 30
    cmd(ctx, 'setblock %d %d 0 hbmsntm:crane_router' % (px, Y))
    cmd(ctx, 'item replace block %d %d 0 container.25 with minecraft:iron_ingot' % (px, Y))
    cmd(ctx, 'item replace block %d %d 0 container.15 with minecraft:iron_ingot' % (px, Y))
    cmd(ctx, 'data merge block %d %d 0 {modes:[I;0,0,0,2,0,1]}' % (px, Y))
    belts(ctx, (px - 4, 0), (px - 1, 0), 'west')
    belts(ctx, (px + 1, 0), (px + 2, 0), 'west')
    cmd(ctx, 'setblock %d %d 0 hbmsntm:crane_inserter[input=west,output=east]' % (px + 3, Y))
    cmd(ctx, 'setblock %d %d 0 minecraft:chest' % (px + 4, Y))
    belts(ctx, (px, 1), (px, 2), 'north')
    cmd(ctx, 'setblock %d %d 3 hbmsntm:crane_inserter[input=north,output=south]' % (px, Y))
    cmd(ctx, 'setblock %d %d 4 minecraft:chest' % (px, Y))
    ctx.step('view', pos=[px + 0.5, Y + 10, 1.5], pitch=90.0, yaw=180.0, fly=True, hide_gui=True)
    _lib.placed(ctx, 40)
    cmd(ctx, 'summon hbmsntm:moving_package %.1f %.2f 0.5 {count:2,contents:[{slot:0b,id:"minecraft:iron_ingot",count:10},'
             '{slot:1b,id:"minecraft:cobblestone",count:12}]}' % (px - 3.5, Y + 0.25))
    seen = []
    for _ in range(12):
        ctx.step('wait', ticks=10)
        es = ctx.step('dump', **{'from': [px - 1, Y, -1], 'to': [px + 3, Y + 1, 3]}, entities=True)['entities']
        seen.append(sum(1 for e in es if e['type'] == 'hbmsntm:moving_package'))
    east, south = data(ctx, px + 4, Y, 0, 'Items'), data(ctx, px, Y, 4, 'Items')
    got = dict(east=(counts(east, 'minecraft:iron_ingot'), counts(east, 'minecraft:cobblestone')),
               south=(counts(south, 'minecraft:iron_ingot'), counts(south, 'minecraft:cobblestone')))
    ctx.check('conveyor-cranes.line-sorter-package', got == dict(east=(10, 0), south=(0, 12)) and max(seen) >= 1,
              '(iron, cobblestone) per side chest %s; packages seen around the sorter per 10 ticks %s' % (got, seen))
