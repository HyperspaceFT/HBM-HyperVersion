"""Survival: every Goal 31 item crafted by hand in a crafting table, a line placed by hand and run, a bare-hand belt break.

The 1.7.10 original's recipes (CraftingManager / ToolRecipes, cd0cff450) make these items from ordinary materials:
pneumatic piston (part_generic 0), conveyor placing tool (leather), inserter, extractor, grabber, boxer, unboxer, sorter,
splitter, partitioner, settings tool. The player gets only base materials and upstream parts by command (listed in the
detail of survival-materials; their survival sources are checked separately with closure.py). Every Goal 31 item is
crafted in the crafting table by real clicks, placed by the player in survival and run.

- placement by hand (BlockCraneBase.onBlockPlacedBy; the wand's single placement): a crane placed from beside gets its input
  side toward the player; a belt from the wand faces away from where the player looks.
- the line: a chest, an extractor, belts, a sorter sending iron east, a grabber over the east belt, an inserter and two
  chests; every item put in arrives in one of the two end chests. The sorter's south side (wildcard) takes the oil scrap
  down a branch placed by hand as in conveyor-cranes.line: boxer (4 full stacks per package), unboxer, splitter 1:1, one
  lane into an inserter and a chest, the other into the partitioner (batches of 16), an inserter and the acidizer
  (16 oil scrap and 100 mB radiosolvent per arsenic nugget, CrystallizerRecipes.java:109); the acidizer's radiosolvent and
  power and the upgrades of the extractor and the unboxer are put in by command (the line is about the cranes).
- a belt broken by a bare hand in survival drops nothing, one broken with a wooden pickaxe drops one regular placing tool, as
  in the original: it drops the wand with the type as damage (BlockConveyor.java:19-21) only when harvestable, and its
  Material.iron (BlockConveyorBase.java:34) needs a tool.
- the settings tool copies an extractor's switch to another extractor in survival.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='conveyor-cranes.survival',
    feature='conveyor-cranes',
    title='Survival: craft every Goal 31 item by hand, place a line by hand and run it, bare-hand belt break',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70, hide_gui=False),
)

Y = -60
OX = 1200
IRON, COPPER = 'minecraft:iron_ingot', 'minecraft:copper_ingot'
# what the player is given: base materials and upstream parts (their survival sources are a separate closure.py record)
GIVE = [(IRON, 64), (COPPER, 8), ('hbmsntm:plate_iron', 16), ('minecraft:leather', 18), ('minecraft:oak_planks', 8),
        ('minecraft:stick', 8), ('minecraft:shears[damage=40]', 1), ('hbmsntm:plate_polymer', 8), ('hbmsntm:circuit_integrated_board', 1),
        ('hbmsntm:circuit_vacuum_tube', 1), ('hbmsntm:circuit_analog_board', 1), ('hbmsntm:ingot_steel', 8),
        ('hbmsntm:crate_steel', 1), ('hbmsntm:circuit_microchip', 1), ('minecraft:chest', 4), ('minecraft:crafting_table', 1),
        ('hbmsntm:machine_crystallizer', 1)]
SCRAP = 'hbmsntm:scrap_oil'
NUGGET = 'hbmsntm:nugget_arsenic'
PISTON = 'hbmsntm:part_generic'
WAND = 'hbmsntm:conveyor_wand'
# output, count made, pattern rows, key (item ids; the piston and the wand are the ones crafted here)
RECIPES = [('piston-1', PISTON, 4, [' I ', 'CPC', ' I '], dict(I=IRON, C=COPPER, P='hbmsntm:plate_iron')),
           ('piston-2', PISTON, 4, [' I ', 'CPC', ' I '], dict(I=IRON, C=COPPER, P='hbmsntm:plate_iron')),
           ('piston-3', PISTON, 4, [' I ', 'CPC', ' I '], dict(I=IRON, C=COPPER, P='hbmsntm:plate_iron')),
           ('wand-1', WAND, 16, ['LLL', 'I I', 'LLL'], dict(L='minecraft:leather', I=IRON)),
           ('wand-2', WAND, 16, ['LLL', 'I I', 'LLL'], dict(L='minecraft:leather', I=IRON)),
           ('wand-3', WAND, 16, ['LLL', 'I I', 'LLL'], dict(L='minecraft:leather', I=IRON)),
           ('crane_inserter', 'hbmsntm:crane_inserter', 2, ['CCC', 'C C', 'CBC'], dict(C=IRON, B=WAND)),
           ('crane_inserter-2', 'hbmsntm:crane_inserter', 2, ['CCC', 'C C', 'CBC'], dict(C=IRON, B=WAND)),
           ('crane_extractor', 'hbmsntm:crane_extractor', 2, ['CCC', 'CPC', 'CBC'], dict(C=IRON, P=PISTON, B=WAND)),
           ('crane_grabber', 'hbmsntm:crane_grabber', 2, ['C C', 'P P', 'CBC'], dict(C=IRON, P=PISTON, B=WAND)),
           ('crane_boxer', 'hbmsntm:crane_boxer', 1, ['WWW', 'WPW', 'CCC'], dict(W='minecraft:oak_planks', P=PISTON, C=WAND)),
           ('crane_unboxer', 'hbmsntm:crane_unboxer', 1, ['WWW', 'WPW', 'CCC'], dict(W='minecraft:stick', P='minecraft:shears', C=WAND)),
           ('crane_router', 'hbmsntm:crane_router', 1, ['PIP', 'ICI', 'PIP'], dict(P=PISTON, I='hbmsntm:plate_polymer', C='hbmsntm:circuit_integrated_board')),
           ('crane_splitter', 'hbmsntm:crane_splitter', 1, ['III', 'PCP', 'III'], dict(I='hbmsntm:ingot_steel', P=PISTON, C='hbmsntm:circuit_vacuum_tube')),
           ('crane_partitioner', 'hbmsntm:crane_partitioner', 1, [' M ', 'BCB'], dict(M='hbmsntm:circuit_microchip', B=WAND, C='hbmsntm:crate_steel')),
           ('settings_tool', 'hbmsntm:settings_tool', 1, [' P ', 'PCP', 'III'], dict(P='hbmsntm:plate_iron', C='hbmsntm:circuit_analog_board', I='hbmsntm:plate_polymer'))]


def expectations():
    E = [('survival-materials', 'record: what the player was given by command (base materials and upstream parts; survival sources: closure.py)', 'closure.py (survival sources of the given items)'),
         ('survival-craft', 'every Goal 31 item comes out of the crafting table by real clicks in survival', 'CraftingManager / ToolRecipes (1.7.10)'),
         ('survival-place', 'extractor, inserter, grabber, sorter, boxer, unboxer, splitter, partitioner and wand belts are placed by hand in survival',
          'BlockCraneBase.onBlockPlacedBy; wand single placement'),
         ('survival-line', 'the hand-built line empties the start chest and all 32 iron ingots arrive in the grabber chest and the end chest together (the grabber has no filter, so it may take all of them)', 'line conservation'),
         ('survival-chain', 'the south branch placed by hand runs: 256 oil scrap through the wildcard side, boxer, unboxer and a 1:1 '
          'splitter: 128 in the lane chest, the other 128 through the partitioner and an inserter into the acidizer as 8 arsenic nuggets; '
          'nothing left in the boxer, unboxer or partitioner', 'TileEntityCraneBoxer/Unboxer/Splitter/Partitioner; CrystallizerRecipes.java:109'),
         ('survival-settings-copy', 'the settings tool made in survival copies an extractor\'s filter item onto another extractor', 'TileEntityCraneBase.java:113-175'),
         ('bare-hand-belt', 'a belt broken by a bare hand in survival drops nothing (the belt is gone); the same belt broken with a wooden pickaxe drops one regular placing tool',
          'BlockConveyorBase.java:34 (Material.iron needs a tool to drop anything), BlockConveyor.java:19-21 (the drop is the wand) (original); '
          'NtmBlocks.java:581-583 (requiresCorrectToolForDrops)')]
    return [dict(id='conveyor-cranes.' + i, text=t, source=s) for i, t, s in E]


def cmd(ctx, command, **kw):
    return ctx.step('cmd', command=command, **kw)


def inventory(ctx):
    inv = ctx.step('inv')
    return {s['slot']: (s.get('item'), s.get('count', 0), s.get('components')) for s in inv['slots'] if s.get('item') and s.get('item') != 'minecraft:air'}


def count(ctx, item):
    return sum(c for i, c, _ in inventory(ctx).values() if i == item)


def menu_slot(inv_slot):
    """Crafting table menu slot of a player inventory slot (hotbar 0-8 -> 37-45, main 9-35 -> 10-36)."""
    return 37 + inv_slot if inv_slot < 9 else 10 + (inv_slot - 9)


def craft(ctx, name, out, made, pattern, key):
    before = count(ctx, out)
    used = []
    for sym, item in key.items():
        cells = [1 + r * 3 + c for r, row in enumerate(pattern) for c, ch in enumerate(row) if ch == sym]
        src = next((s for s, (i, n, _) in sorted(inventory(ctx).items()) if i == item and n >= len(cells)), None)
        if src is None:
            return False, '%s: no stack of %s with %d items' % (name, item, len(cells))
        ctx.step('click', slot=menu_slot(src), after=2)
        for cell in cells:
            ctx.step('click', slot=cell, button=1, after=2)
        ctx.step('click', slot=menu_slot(src), after=2)
        used.append((item, len(cells)))
    ctx.step('mod', shift=True)
    ctx.step('click', slot=0, after=4)
    ctx.step('mod', shift=False)
    after = count(ctx, out)
    return after - before == made, '%s: %s %d -> %d (made %d) from %s' % (name, out, before, after, made, used)


def hold(ctx, item):
    """Brings `item` into the first hotbar slot as a player does: in the inventory screen, the number key 1 over its slot
    swaps it with whatever the first hotbar slot held (nothing is lost). Returns False when the player has none."""
    src = next((s for s, (i, n, _) in sorted(inventory(ctx).items()) if i == item), None)
    if src is None:
        return False
    if src != 0:
        ctx.step('key', key='key.keyboard.e', action='tap', after=4)
        ctx.step('screen', expect='Inventory')
        ctx.step('hover', slot=36 + src if src < 9 else src, frames=2)
        ctx.step('key', key='key.keyboard.1', action='tap', after=3)
        ctx.step('close')
    ctx.step('key', key='key.keyboard.1', action='tap', after=2)
    return True


def empty_hand(ctx):
    """Selects an empty hotbar slot; when the hotbar is full, swaps an empty inventory slot into the first one."""
    inv = inventory(ctx)
    free = next((s for s in range(9) if s not in inv), None)
    if free is None:
        main = next((s for s in range(9, 36) if s not in inv), None)
        ctx.step('key', key='key.keyboard.e', action='tap', after=4)
        ctx.step('screen', expect='Inventory')
        ctx.step('hover', slot=main, frames=2)
        ctx.step('key', key='key.keyboard.1', action='tap', after=3)
        ctx.step('close')
        free = 0
    ctx.step('key', key='key.keyboard.%d' % (free + 1), action='tap', after=2)


def place_by_hand(ctx, item, cell, stand, target_face='up'):
    """Takes `item` into the hand, stands at `stand` (feet) and right-clicks the top of the block below `cell`."""
    if not hold(ctx, item):
        return None
    ctx.step('view', pos=stand, look_at=[cell[0] + 0.5, cell[1] - 0.5, cell[2] + 0.5], fly=False, hide_gui=False)
    ctx.step('use', target=dict(pos=[cell[0], cell[1] - 1, cell[2]], face=target_face), after=6)
    d = ctx.step('dump', **{'from': list(cell)})['blocks']
    return d[0] if d else None


def wand_belt(ctx, cell, stand):
    ctx.step('view', pos=stand, look_at=[cell[0] + 0.5, cell[1] - 0.5, cell[2] + 0.5], fly=False, hide_gui=False)
    ctx.step('key', key='key.keyboard.left.shift', action='press', after=3)
    ctx.step('use', target=dict(pos=[cell[0], cell[1] - 1, cell[2]], face='up'), after=4)
    ctx.step('key', key='key.keyboard.left.shift', action='release', after=3)
    d = ctx.step('dump', **{'from': list(cell)})['blocks']
    return d[0] if d else None


def side_belt(ctx, cell, west=False):
    """A wand belt facing north (items travelling south): the player looks mostly south from the column east of the cell
    (west of it with west=True), two cells back, so it never stands on a belt of the branch."""
    x, y, z = cell
    stand = [x - 0.6, Y, z - 1.5] if west else [x + 1.6, Y, z - 1.5]
    if z - 1.5 < 1:  # next to the line at z = 0 (and the grabber north of it): stand in the free row north of the line
        stand = [x - 0.6, Y, -0.5]
    return wand_belt(ctx, cell, stand)


def run(ctx):
    _lib.setup_world(ctx, freeze=False)
    x0 = OX
    ctx.step('view', pos=[x0 + 5.5, Y + 8, 2.5], pitch=80.0, yaw=180.0, fly=True, hide_gui=False)
    ctx.step('wait', ticks=60)
    cmd(ctx, 'clear @s', allow_error=True)
    cmd(ctx, 'gamemode survival')
    for item, n in GIVE:
        cmd(ctx, 'give @s %s %d' % (item, n))
    ctx.review('conveyor-cranes.survival-materials', 'given by command: %s; survival sources of these parts: closure.py record' % ', '.join('%s x%d' % g for g in GIVE))
    # crafting table by hand
    cmd(ctx, 'setblock %d %d 6 minecraft:crafting_table' % (x0, Y))
    ctx.step('view', pos=[x0 + 0.5, Y, 8.5], look_at=[x0 + 0.5, Y + 0.5, 6.5], fly=False, hide_gui=False)
    ctx.step('use', target=dict(pos=[x0, Y, 6], face='south'), after=6)
    ctx.step('screen', expect='Crafting')
    log, ok = [], True
    for name, out, made, pattern, key in RECIPES:
        good, line = craft(ctx, name, out, made, pattern, key)
        ok = ok and good
        log.append(line)
    ctx.step('close')
    ctx.check('conveyor-cranes.survival-craft', ok, '; '.join(log))
    # the line along +x at z = 0: chest x0, extractor x0+1, belts x0+2..4, sorter x0+5, belts x0+6..7, inserter x0+8, chest x0+9;
    # a grabber north of the belt at x0+6 with a chest behind it
    placed = {}
    placed['chest_start'] = place_by_hand(ctx, 'minecraft:chest', (x0, Y, 0), [x0 + 0.5, Y, 2.5])
    # belts first (nothing in the way of the aim), from the wand, the player looking mostly east from the row north of
    # the line, so each belt faces west (input west, travelling east): the block takes the opposite of the player's facing
    hold(ctx, WAND)
    for bx in (x0 + 2, x0 + 3, x0 + 4, x0 + 6, x0 + 7):
        placed['belt_%d' % (bx - x0)] = wand_belt(ctx, (bx, Y, 0), [bx - 1.5, Y, -0.6])
    # the first belts of the south branch too, while the sorter's cell is still free to look across
    for z in (3, 2, 1):  # far to near: a placed belt would catch the aim at the next one
        placed['belt_s%d' % z] = side_belt(ctx, (x0 + 5, Y, z))
    # the cranes from the same free row (not standing on a belt): looking west at the extractor, east at the inserter
    placed['extractor'] = place_by_hand(ctx, 'hbmsntm:crane_extractor', (x0 + 1, Y, 0), [x0 + 3.5, Y, -0.6])
    placed['sorter'] = place_by_hand(ctx, 'hbmsntm:crane_router', (x0 + 5, Y, 0), [x0 + 6.5, Y, 2.5])
    placed['inserter'] = place_by_hand(ctx, 'hbmsntm:crane_inserter', (x0 + 8, Y, 0), [x0 + 6.5, Y, -0.6])
    placed['chest_end'] = place_by_hand(ctx, 'minecraft:chest', (x0 + 9, Y, 0), [x0 + 9.5, Y, 2.5])
    placed['grabber'] = place_by_hand(ctx, 'hbmsntm:crane_grabber', (x0 + 6, Y, -1), [x0 + 6.5, Y, 1.6])
    placed['chest_grab'] = place_by_hand(ctx, 'minecraft:chest', (x0 + 6, Y, -2), [x0 + 8.5, Y, -2.5])
    # the south branch from the sorter at sx (conveyor-cranes.line's layout): the acidizer first (a multiblock), then the belts
    # (far to near), then the splitter and the cranes, so nothing placed stands in the aim at the next cell; each is looked
    # at mostly south or north
    sx = x0 + 5
    placed['acidizer'] = place_by_hand(ctx, 'hbmsntm:machine_crystallizer', (sx - 1, Y, 18), [sx - 1.5, Y, 15.8])
    acid = {tuple(int(c) for c in b['pos']): b['props'].get('type') for b in ctx.step('dump', **{'from': [sx - 2, Y, 18], 'to': [sx, Y, 20]})['blocks']
            if b['block'] == 'hbmsntm:machine_crystallizer'}
    hold(ctx, WAND)
    for z in (16, 15, 13, 12, 10, 9, 7, 6, 5):
        placed['belt_s%d' % z] = side_belt(ctx, (sx, Y, z))
    for z in (13, 12):
        placed['belt_w%d' % z] = side_belt(ctx, (sx - 1, Y, z), west=True)
    placed['splitter'] = place_by_hand(ctx, 'hbmsntm:crane_splitter', (sx, Y, 11), [sx + 1.6, Y, 9.5])
    split = {tuple(int(c) for c in b['pos']): b['props'] for b in ctx.step('dump', **{'from': [sx - 1, Y, 11], 'to': [sx + 1, Y, 11]})['blocks']
             if b['block'] == 'hbmsntm:crane_splitter'}
    placed['boxer'] = place_by_hand(ctx, 'hbmsntm:crane_boxer', (sx, Y, 4), [sx + 1.6, Y, 2.5])
    placed['unboxer'] = place_by_hand(ctx, 'hbmsntm:crane_unboxer', (sx, Y, 8), [sx + 1.6, Y, 10.5])
    placed['partitioner'] = place_by_hand(ctx, 'hbmsntm:crane_partitioner', (sx, Y, 14), [sx + 1.6, Y, 12.5])
    placed['inserter_lane'] = place_by_hand(ctx, 'hbmsntm:crane_inserter', (sx - 1, Y, 14), [sx - 1.6, Y, 12.5])
    placed['chest_lane'] = place_by_hand(ctx, 'minecraft:chest', (sx - 1, Y, 15), [sx - 1.6, Y, 17.5])
    placed['inserter_acid'] = place_by_hand(ctx, 'hbmsntm:crane_inserter', (sx, Y, 17), [sx + 1.6, Y, 15.5])
    summary = {k: (v['block'].split(':')[1], {p: v['props'].get(p) for p in ('input', 'output', 'facing') if p in v.get('props', {})}) if v else None
               for k, v in placed.items()}
    branch = (all(placed['belt_%s' % k] and placed['belt_%s' % k]['props'].get('facing') == 'north'
                  for k in ['s%d' % z for z in (1, 2, 3, 5, 6, 7, 9, 10, 12, 13, 15, 16)] + ['w12', 'w13'])
              and placed['boxer'] and placed['boxer']['props'].get('input') == 'north'
              and placed['unboxer'] and placed['unboxer']['props'].get('input') == 'south'
              and placed['partitioner'] and placed['partitioner']['props'].get('facing') == 'north'
              and all(placed[k] and placed[k]['props'].get('input') == 'north' for k in ('inserter_lane', 'inserter_acid'))
              and split.get((sx, Y, 11), {}).get('facing') == 'north' and (sx - 1, Y, 11) in split
              and sum(1 for v in acid.values() if v == 'extra') == 4)
    want_line = (placed['extractor'] and placed['extractor']['props'].get('input') == 'east'
                 and placed['inserter'] and placed['inserter']['props'].get('input') == 'west'
                 and placed['grabber'] and placed['grabber']['props'].get('input') == 'south'
                 and all(placed['belt_%d' % (bx - x0)] and placed['belt_%d' % (bx - x0)]['props'].get('facing') == 'west' for bx in (x0 + 2, x0 + 3, x0 + 4, x0 + 6, x0 + 7)))
    ctx.check('conveyor-cranes.survival-place', bool(want_line) and bool(branch) and all(summary.values()),
              'placed %s; splitter cells %s; acidizer bottom cells %s' % (summary, split, acid))
    core = (sx - 1, Y, 19)
    cmd(ctx, 'data merge block %d %d %d {tank:8000,tank_type:"RADIOSOLVENT",power:1000000L}' % core)
    cmd(ctx, 'item replace block %d %d 0 container.18 with hbmsntm:upgrade_stack_3' % (x0 + 1, Y))
    cmd(ctx, 'item replace block %d %d 0 container.19 with hbmsntm:upgrade_ejector_3' % (x0 + 1, Y))
    cmd(ctx, 'item replace block %d %d 8 container.21 with hbmsntm:upgrade_stack_2' % (sx, Y))
    # the sorter: iron into the east side's first filter slot (menu slot 25), its mode button (right column, third row) once
    empty_hand(ctx)
    ctx.step('view', pos=[x0 + 6.5, Y, 2.5], look_at=[x0 + 5.5, Y + 0.5, 0.5], fly=False, hide_gui=False)
    ctx.step('use', target=dict(pos=[x0 + 5, Y, 0], face='south'), after=6)
    ctx.step('screen', expect='Router')
    iron_src = next((s for s, (i, n, _) in sorted(inventory(ctx).items()) if i == IRON), None)
    hud = ctx.step('hud', frames=3)
    if iron_src is not None:
        ctx.step('click', slot=30 + (iron_src - 9) if iron_src >= 9 else 57 + iron_src, after=2)
        ctx.step('click', slot=25, after=2)
        ctx.step('click', slot=30 + (iron_src - 9) if iron_src >= 9 else 57 + iron_src, after=2)
    ctx.step('click', at=[hud['gui_left'] + 7 + 222 + 9, hud['gui_top'] + 16 + 52 + 9], button=0, after=4)
    for _ in range(3):  # the south side's button (right column, first row): off, whitelist, blacklist, wildcard
        ctx.step('click', at=[hud['gui_left'] + 7 + 222 + 9, hud['gui_top'] + 16 + 9], button=0, after=4)
    ctx.step('close')
    # 32 iron ingots into the start chest by hand: open it and shift-click a stack in
    cmd(ctx, 'clear @s %s' % IRON, allow_error=True)
    cmd(ctx, 'give @s %s 32' % IRON)
    cmd(ctx, 'give @s %s 256' % SCRAP)
    ctx.step('view', pos=[x0 + 0.5, Y, 2.5], look_at=[x0 + 0.5, Y + 0.4, 0.5], fly=False, hide_gui=False)
    ctx.step('use', target=dict(pos=[x0, Y, 0], face='south'), after=6)
    ctx.step('screen', expect='Container')
    inv = inventory(ctx)
    moved = sorted(s for s, (i, n, _) in inv.items() if (i == IRON and n == 32) or (i == SCRAP and n == 64))
    ctx.step('mod', shift=True)
    for s in moved:
        ctx.step('click', slot=27 + (s - 9) if s >= 9 else 54 + s, after=3)
    ctx.step('mod', shift=False)
    ctx.step('close')
    ctx.step('view', pos=[x0 + 6.5, Y + 6, 3.5], pitch=70.0, yaw=180.0, fly=False, hide_gui=False)
    ctx.step('wait', ticks=900)
    # eight acidizer cycles of 101 ticks follow the last batch
    for _ in range(20):
        r = cmd(ctx, 'data get block %d %d %d Items' % core, wait_ticks=6, allow_error=True)
        entries = re.findall(r'\{[^{}]*id:\s*"%s"[^{}]*\}' % re.escape(NUGGET), ' '.join(x['text'] for x in r.get('messages', [])))
        if sum(int((re.search(r'count:\s*(\d+)', e) or re.search('()', '1')).group(1) or 1) for e in entries) >= 8:
            break
        ctx.step('wait', ticks=100)
    def chest(pos, item=IRON):
        r = cmd(ctx, 'data get block %d %d %d Items' % pos, wait_ticks=6, allow_error=True)
        text = ' '.join(m['text'] for m in r.get('messages', []))
        n = 0
        for entry in re.findall(r'\{[^{}]*id:\s*"%s"[^{}]*\}' % re.escape(item), text):
            m = re.search(r'count:\s*(\d+)', entry)
            n += int(m.group(1)) if m else 1
        return n
    got = dict(start=chest((x0, Y, 0)), end=chest((x0 + 9, Y, 0)), grabber=chest((x0 + 6, Y, -2)))
    ctx.check('conveyor-cranes.survival-line', got['start'] == 0 and got['end'] + got['grabber'] == 32 and got['grabber'] > 0,
              'iron ingots: start chest %(start)d, end chest %(end)d, grabber chest %(grabber)d' % got)
    chain = dict(start=chest((x0, Y, 0), SCRAP), lane=chest((sx - 1, Y, 15), SCRAP), nuggets=chest(core, NUGGET), acid_in=chest(core, SCRAP),
                 partitioner=chest((sx, Y, 14), SCRAP), boxer=chest((sx, Y, 4), SCRAP), unboxer=chest((sx, Y, 8), SCRAP))
    ctx.check('conveyor-cranes.survival-chain', (chain['start'], chain['lane'], chain['nuggets'], chain['acid_in'], chain['partitioner'], chain['boxer'],
                                                 chain['unboxer']) == (0, 128, 8, 0, 0, 0, 0),
              'oil scrap: start chest %(start)d, lane chest %(lane)d, acidizer input %(acid_in)d, partitioner %(partitioner)d, boxer %(boxer)d, '
              'unboxer %(unboxer)d; arsenic nuggets %(nuggets)d' % chain)
    # settings tool: copy the extractor's filter to a second extractor (the original copies sides and filter items,
    # TileEntityCraneBase.java:113-175)
    cmd(ctx, 'item replace block %d %d 0 container.0 with %s' % (x0 + 1, Y, IRON))
    placed2 = place_by_hand(ctx, 'hbmsntm:crane_extractor', (x0 + 1, Y, 4), [x0 + 1.5, Y, 6.5])
    hold(ctx, 'hbmsntm:settings_tool')
    ctx.step('view', pos=[x0 + 1.5, Y, 2.5], look_at=[x0 + 1.5, Y + 0.5, 0.5], fly=False, hide_gui=False)
    ctx.step('key', key='key.keyboard.left.shift', action='press', after=3)
    ctx.step('use', target=dict(pos=[x0 + 1, Y, 0], face='south'), after=6)
    ctx.step('key', key='key.keyboard.left.shift', action='release', after=3)
    ctx.step('view', pos=[x0 + 1.5, Y, 6.5], look_at=[x0 + 1.5, Y + 0.5, 4.5], fly=False, hide_gui=False)
    ctx.step('use', target=dict(pos=[x0 + 1, Y, 4], face='south'), after=6)
    r = cmd(ctx, 'data get block %d %d 4 Items' % (x0 + 1, Y), wait_ticks=6, allow_error=True)
    text = ' '.join(m['text'] for m in r.get('messages', []))
    ok = bool(placed2) and re.search(r'\{[^{}]*Slot:\s*0b[^{}]*id:\s*"%s"' % re.escape(IRON), text) is not None
    ctx.check('conveyor-cranes.survival-settings-copy', ok, 'second extractor %s; its items %s' % (placed2 and placed2['props'], text[-120:]))
    # bare-hand belt break: the original's belt is Material.iron (BlockConveyorBase.java:34), which drops nothing without a tool
    # but still breaks, and drops the wand (BlockConveyor.java:19-21); a wooden pickaxe is a tool for it
    def break_belt(hold_ticks):
        cmd(ctx, 'setblock %d %d 14 hbmsntm:conveyor[facing=west,shape=straight]' % (x0, Y))
        wands_before = count(ctx, WAND)
        ctx.step('view', pos=[x0 + 0.5, Y, 16.5], look_at=[x0 + 0.5, Y + 0.1, 14.5], fly=False, hide_gui=False)
        ctx.step('attack', target=dict(pos=[x0, Y, 14], face='up', offset=[0, -0.8, 0]), any_hit=True, hold=hold_ticks, after=10)
        es = ctx.step('dump', **{'from': [x0 - 2, Y - 1, 12], 'to': [x0 + 2, Y + 2, 17]}, entities=True)['entities']
        # a held attack goes on to the ground block under the belt once the belt is gone: its dirt is not the belt's drop
        drops = [(e.get('item'), e.get('count')) for e in es if e['type'] == 'minecraft:item' and e.get('item') != 'minecraft:dirt']
        left = ctx.step('dump', **{'from': [x0, Y, 14]})['blocks']
        picked = count(ctx, WAND) - wands_before  # the drop may already be picked up
        got = sum(c for i, c in drops if i == WAND) + picked
        return drops, picked, got, (left[0]['block'] if left else None)
    empty_hand(ctx)
    # no correct tool: 2.0 hardness at 1/100 a tick is 200 ticks
    hand_drops, hand_picked, hand_got, hand_left = break_belt(240)
    cmd(ctx, 'item replace entity @s weapon.mainhand with minecraft:wooden_pickaxe')
    wood_drops, wood_picked, wood_got, wood_left = break_belt(60)
    ctx.check('conveyor-cranes.bare-hand-belt', hand_got == 0 and not hand_drops and hand_left != 'hbmsntm:conveyor'
              and wood_got == 1 and all(i == WAND for i, _ in wood_drops) and wood_left != 'hbmsntm:conveyor',
              'bare hand: drops on the ground %s, placing tools picked up %d, block left %s; wooden pickaxe: drops on the ground %s, '
              'placing tools picked up %d, block left %s' % (hand_drops, hand_picked, hand_left, wood_drops, wood_picked, wood_left))
    cmd(ctx, 'gamemode creative')
