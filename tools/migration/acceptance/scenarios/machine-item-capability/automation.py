"""Hoppers and cranes against existing machines: what goes in, what comes out, nothing lost or made.

Expected values follow the 1.7.10 original at cd0cff450:
- crucible (TileEntityCrucible.java:545-547, MachineCrucible.java:48): the outer cells are inventory proxies; a hopper over an
  outer cell feeds slots 1-9, one item each into empty slots only, so an unheated crucible takes 9 of 64 and the hopper
  keeps 55.
- electric furnace (TileEntityMachineElectricFurnace.java:63-93): every side reaches slots 0-2; slot 1 takes smeltable items
  only, slot 0 batteries only; only slot 2 (the result) can be taken out.
- iron crate (TileEntityCrateBase): every slot from every side, in and out.
- refinery (MachineRefinery: proxies only at the four bottom corners): a cell that is no port takes and gives nothing.
- vanilla furnace fuel slot: a bucket only goes into an empty fuel slot, and the original inserter fills the fuel slot, then
  the input slot, from any face (InventoryUtil.masquerade): 1 of 16 empty buckets as fuel, the other 15 as input
  (CraneInserter.java:61-96).
- assembly machine (TileEntityMachineAssemblyMachine.java:255-271) and chemical plant (TileEntityMachineChemicalPlant.java:
  230-248): automation reaches slots 4-16 and 4-9; only the outputs (16; 7-9) and input slots holding an item the
  recipe does not take ("clogged", ModuleMachineBase.java:235-242; with no recipe set every filled input) can be taken.
- heaters: the original lets nothing be taken from the firebox, oven, fluid burner or heat exchanger
  (TileEntityMachineBase.java:131-133, not overridden). A crane under the core reaches it only through the core's bottom
  face; inserting through that face first shows the face is reached. Whether automation can put items into the fluid
  burner is recorded without a pass line (NEO opens slots 0-2 to it on purpose, HeaterOilburnerBlockEntity.java:204-208).
- heat exchanger (TileEntityHeaterHeatex: no accessible slot, Goal32B): an inserter under the core cannot put a fluid
  identifier in (the item stays in the inserter, nothing lost), and an extractor takes nothing.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='machine-item-capability.automation',
    feature='machine-item-capability',
    title='Hoppers and cranes against existing machines: crucible, furnaces, crate, refinery, assembler, chemical plant, heaters',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70, hide_gui=True),
)

Y = -60
OX = 900


def expectations():
    E = [('crucible-hopper', 'a hopper over a crucible outer cell: the crucible takes 9 iron ingots, one per slot, the hopper keeps 55', 'TileEntityCrucible.java:545-547'),
         ('efurnace-hopper-in', 'electric furnace from above: raw iron goes into slot 1, dirt stays in the hopper', 'TileEntityMachineElectricFurnace.java:63-93'),
         ('efurnace-hopper-out', 'electric furnace from below: only the result slot is emptied', 'TileEntityMachineElectricFurnace.java:91-93'),
         ('crate-hopper', 'iron crate: a hopper above fills it, a hopper below empties it, totals unchanged', 'TileEntityCrateBase'),
         ('refinery-dummy', 'refinery cell without a port: a hopper above keeps its items, a hopper below gets nothing', 'MachineRefinery proxies'),
         ('furnace-bucket', 'an inserter feeding 16 empty buckets into a furnace side: 1 in the fuel slot, the other 15 in the input '
          'slot (the original fills fuel, then input, from any face), none lost', 'InventoryUtil.java:20-26; CraneInserter.java:61-96'),
         ('assembler-side', 'extractor at an assembly machine port takes the output and the clogged input; with a recipe set, the input that '
          'fits it stays, and so do the battery and upgrade slots', 'TileEntityMachineAssemblyMachine.java:255-271 (canExtractItem :264-266); ModuleMachineBase.java:235-242'),
         ('chemplant-side', 'extractor at a chemical plant port takes the output and the clogged input, not the battery or fluid slots',
          'TileEntityMachineChemicalPlant.java:230-248; ModuleMachineBase.java:235-242')]
    for h in ('firebox', 'oven', 'oilburner'):
        E.append(('heater-%s' % h, '%s: an extractor under the core takes nothing (after a control showing that face is reached)' % h,
                  'TileEntityMachineBase.java:131-133'))
    E.append(('heater-heatex', 'heat exchanger: an inserter under the core cannot put a fluid identifier in (it stays in the inserter, '
              'none lost) and an extractor under the core takes nothing', 'TileEntityHeaterHeatex (no accessible slot); TileEntityMachineBase.java:131-140'))
    E.append(('heater-insert-record', 'record: can an inserter under the core put a fluid identifier into the fluid burner',
              'record item, no pass line'))
    return [dict(id='machine-item-capability.' + i, text=t, source=s) for i, t, s in E]


def cmd(ctx, command, **kw):
    return ctx.step('cmd', command=command, **kw)


def items(ctx, pos, path='Items'):
    r = ctx.step('cmd', command='data get block %d %d %d %s' % (pos[0], pos[1], pos[2], path), wait_ticks=6, allow_error=True)
    text = ' '.join(m['text'] for m in r.get('messages', []))
    out = []
    for entry in re.findall(r'\{[^{}]*id:\s*"[^"]+"[^{}]*\}', text):
        slot = re.search(r'Slot:\s*(\d+)b', entry)
        count = re.search(r'count:\s*(\d+)', entry)
        out.append((int(slot.group(1)) if slot else None, re.search(r'id:\s*"([^"]+)"', entry).group(1), int(count.group(1)) if count else 1))
    return out


def total(lst, item=None):
    return sum(c for _, i, c in lst if item is None or i == item)


def place_multi(ctx, block, x, z, h=4):
    """Places a multiblock item by hand onto the ground at (x, z), the player looking north from 4 blocks south; returns the
    cells {pos: type} and the core position."""
    cmd(ctx, 'item replace entity @s weapon.mainhand with hbmsntm:%s' % block)
    ctx.step('view', pos=[x + 0.5, Y, z + 4.5], look_at=[x + 0.5, Y - 0.5, z + 0.5], fly=False, hide_gui=True)
    ctx.step('use', target=dict(pos=[x, Y - 1, z], face='up'), after=8)
    cmd(ctx, 'item replace entity @s weapon.mainhand with minecraft:air')
    d = ctx.step('dump', **{'from': [x - 4, Y, z - 4], 'to': [x + 4, Y + h, z + 4]})
    cells = {tuple(int(c) for c in b['pos']): b['props'].get('type', 'core') for b in d['blocks'] if b['block'] == 'hbmsntm:' + block}
    core = next((p for p, t in cells.items() if t == 'core'), None)
    return cells, core


def look(ctx, x, z, h=12):
    ctx.step('view', pos=[x + 0.5, Y + h, z + 0.5], pitch=90.0, yaw=180.0, fly=True, hide_gui=True)
    ctx.step('wait', ticks=40)


def hoppers(ctx):
    # crucible
    x = OX
    look(ctx, x, 0)
    cells, core = place_multi(ctx, 'machine_crucible', x, 0)
    if core is None:
        ctx.check('machine-item-capability.crucible-hopper', False, 'crucible not placed; cells %s' % cells)
    else:
        outer_top = max((p for p in cells if p[1] == core[1] + 1 and (p[0], p[2]) != (core[0], core[2])), default=None)
        hp = (outer_top[0], outer_top[1] + 1, outer_top[2])
        cmd(ctx, 'setblock %d %d %d minecraft:hopper[facing=down]' % hp)
        cmd(ctx, 'item replace block %d %d %d container.0 with minecraft:iron_ingot 64' % hp)
        ctx.step('wait', ticks=300)
        left = total(items(ctx, hp), 'minecraft:iron_ingot')
        got = total(items(ctx, core), 'minecraft:iron_ingot')
        ctx.check('machine-item-capability.crucible-hopper', (got, left) == (9, 55),
                  'hopper over outer cell %s gave %d, crucible core %s holds %d iron ingots' % (outer_top, 64 - left, core, got))
    # electric furnace
    x = OX + 10
    look(ctx, x, 0)
    cmd(ctx, 'setblock %d %d 0 hbmsntm:machine_electric_furnace' % (x, Y))
    cmd(ctx, 'item replace block %d %d 0 container.2 with minecraft:iron_ingot 4' % (x, Y))
    cmd(ctx, 'setblock %d %d 0 minecraft:hopper[facing=down]' % (x, Y + 1))
    cmd(ctx, 'item replace block %d %d 0 container.0 with minecraft:dirt 3' % (x, Y + 1))
    cmd(ctx, 'item replace block %d %d 0 container.1 with minecraft:raw_iron 5' % (x, Y + 1))
    ctx.step('wait', ticks=120)
    fur, top = items(ctx, (x, Y, 0)), items(ctx, (x, Y + 1, 0))
    ok = [(s, i, c) for s, i, c in fur if s == 1] == [(1, 'minecraft:raw_iron', 5)] and total(top, 'minecraft:dirt') == 3 and total(top, 'minecraft:raw_iron') == 0
    ctx.check('machine-item-capability.efurnace-hopper-in', ok, 'furnace %s; hopper above %s' % (fur, top))
    cmd(ctx, 'setblock %d %d 0 minecraft:hopper[facing=down]' % (x, Y - 1))
    ctx.step('wait', ticks=120)
    fur, below = items(ctx, (x, Y, 0)), items(ctx, (x, Y - 1, 0))
    ctx.check('machine-item-capability.efurnace-hopper-out', total(below, 'minecraft:iron_ingot') == 4 and total(below, 'minecraft:raw_iron') == 0
              and total(fur, 'minecraft:raw_iron') == 5, 'hopper below %s; furnace %s' % (below, fur))
    # iron crate
    x = OX + 14
    cmd(ctx, 'setblock %d %d 0 hbmsntm:crate_iron' % (x, Y))
    cmd(ctx, 'item replace block %d %d 0 container.0 with minecraft:dirt 5' % (x, Y))
    cmd(ctx, 'setblock %d %d 0 minecraft:hopper[facing=down]' % (x, Y + 1))
    cmd(ctx, 'item replace block %d %d 0 container.0 with minecraft:cobblestone 10' % (x, Y + 1))
    cmd(ctx, 'setblock %d %d 0 minecraft:hopper[facing=down]' % (x, Y - 1))
    ctx.step('wait', ticks=200)
    a, c, b = items(ctx, (x, Y + 1, 0)), items(ctx, (x, Y, 0)), items(ctx, (x, Y - 1, 0))
    tot = {k: total(a, k) + total(c, k) + total(b, k) for k in ('minecraft:dirt', 'minecraft:cobblestone')}
    ctx.check('machine-item-capability.crate-hopper', total(a) == 0 and total(b) > 0 and tot == {'minecraft:dirt': 5, 'minecraft:cobblestone': 10},
              'hopper above %s; crate %s; hopper below %s' % (a, c, b))
    # refinery cell without a port
    x = OX + 24
    look(ctx, x, 0, 16)
    cells, core = place_multi(ctx, 'machine_refinery', x, 0, h=10)
    if core is None:
        ctx.check('machine-item-capability.refinery-dummy', False, 'refinery not placed; cells %s' % cells)
    else:
        top_y = max(p[1] for p in cells)
        top_cell = (core[0] + 1, top_y, core[2])
        bottom_cell = (core[0] + 1, core[1], core[2])
        for slot in range(3):
            cmd(ctx, 'item replace block %d %d %d container.%d with minecraft:dirt 2' % (core[0], core[1], core[2], slot), allow_error=True)
        cmd(ctx, 'setblock %d %d %d minecraft:hopper[facing=down]' % (top_cell[0], top_y + 1, top_cell[2]))
        cmd(ctx, 'item replace block %d %d %d container.0 with minecraft:cobblestone 5' % (top_cell[0], top_y + 1, top_cell[2]))
        cmd(ctx, 'setblock %d %d %d minecraft:hopper[facing=down]' % (bottom_cell[0], Y - 1, bottom_cell[2]))
        ctx.step('wait', ticks=120)
        a = items(ctx, (top_cell[0], top_y + 1, top_cell[2]))
        b = items(ctx, (bottom_cell[0], Y - 1, bottom_cell[2]))
        # Both cells must be refinery cells without a port, or an empty hopper below proves nothing.
        is_dummy = cells.get(top_cell) == 'dummy' and cells.get(bottom_cell) == 'dummy'
        ctx.check('machine-item-capability.refinery-dummy', is_dummy and total(a, 'minecraft:cobblestone') == 5 and total(b) == 0,
                  'cells %s / %s are %s / %s; hopper above keeps %s; hopper below got %s' % (
                      top_cell, bottom_cell, cells.get(top_cell), cells.get(bottom_cell), a, b))


def furnace_bucket(ctx):
    x = OX + 40
    look(ctx, x, 0)
    cmd(ctx, 'setblock %d %d 0 minecraft:furnace[facing=south]' % (x, Y))
    cmd(ctx, 'setblock %d %d 0 hbmsntm:crane_inserter[input=east,output=west]' % (x + 1, Y))
    cmd(ctx, 'fill %d %d 0 %d %d 0 hbmsntm:conveyor[facing=east,shape=straight]' % (x + 2, Y, x + 4, Y))
    _lib.placed(ctx)
    cmd(ctx, 'summon minecraft:item %.1f %.2f 0.5 {Item:{id:"minecraft:bucket",count:16}}' % (x + 3.5, Y + 0.6))
    ctx.step('wait', ticks=120)
    fur, buf = items(ctx, (x, Y, 0)), items(ctx, (x + 1, Y, 0))
    ctx.check('machine-item-capability.furnace-bucket', [(s, i, c) for s, i, c in fur if s in (0, 1)] == [(0, 'minecraft:bucket', 15), (1, 'minecraft:bucket', 1)]
              and total(fur, 'minecraft:bucket') + total(buf, 'minecraft:bucket') == 16, 'furnace %s; inserter buffer %s' % (fur, buf))


def side_extraction(ctx, block, x, preload, want_taken, eid, recipe=None, want_kept=()):
    look(ctx, x, 0)
    cells, core = place_multi(ctx, block, x, 0)
    if core is None:
        ctx.check(eid, False, '%s not placed; cells %s' % (block, cells))
        return
    port = (core[0] + 1, core[1], core[2])
    ex = (core[0] + 2, core[1], core[2])
    for slot, item, n in preload:
        cmd(ctx, 'item replace block %d %d %d container.%d with %s %d' % (core[0], core[1], core[2], slot, item, n))
    if recipe:
        cmd(ctx, 'data merge block %d %d %d {recipe0:"%s"}' % (core[0], core[1], core[2], recipe))
    cmd(ctx, 'setblock %d %d %d hbmsntm:crane_extractor[input=east,output=west]' % ex)
    cmd(ctx, 'item replace block %d %d %d container.18 with hbmsntm:upgrade_stack_3' % ex)
    cmd(ctx, 'item replace block %d %d %d container.19 with hbmsntm:upgrade_ejector_3' % ex)
    ctx.step('wait', ticks=120)
    taken = sorted({i for s, i, c in items(ctx, ex) if 9 <= (s or 0) <= 17})
    left = items(ctx, core)
    kept = all(any(s == slot and i == item and c == n for s, i, c in left) for slot, item, n in want_kept)
    ctx.check(eid, taken == sorted(want_taken) and kept, 'port cell %s is %s; taken into the extractor %s, want %s; left in the machine %s (must keep %s)' % (
        port, cells.get(port), taken, sorted(want_taken), left, list(want_kept)))


def heater(ctx, block, x, ident):
    look(ctx, x, 0)
    cells, core = place_multi(ctx, block, x, 0)
    eid = 'machine-item-capability.heater-%s' % block.split('_')[1]
    if core is None:
        ctx.check(eid, False, '%s not placed; cells %s' % (block, cells))
        return None
    under = (core[0], core[1] - 1, core[2])
    belt = (core[0], core[1] - 1, core[2] - 1)
    item = 'hbmsntm:fluid_identifier_multi' if ident else 'minecraft:coal'
    # control: an inserter under the core, fed by a belt from the north, puts one item up through the core's bottom face
    cmd(ctx, 'setblock %d %d %d hbmsntm:crane_inserter[input=north,output=up]' % under)
    cmd(ctx, 'setblock %d %d %d hbmsntm:conveyor[facing=north,shape=straight]' % belt)
    _lib.placed(ctx)
    before = items(ctx, core)
    cmd(ctx, 'summon minecraft:item %.1f %.2f %.1f {Item:{id:"%s",count:1}}' % (belt[0] + 0.5, belt[1] + 0.3, belt[2] + 0.5, item))
    ctx.step('wait', ticks=60)
    buf = items(ctx, under)
    loose = [e for e in ctx.step('dump', **{'from': [core[0] - 2, core[1] - 2, core[2] - 3], 'to': [core[0] + 2, core[1] + 2, core[2] + 2]}, entities=True)['entities']
             if e['type'] in ('minecraft:item', 'hbmsntm:moving_item')]
    inserted = total(buf) == 0 and not loose
    after_insert = items(ctx, core)
    # the test: an extractor in the same place, items preloaded in every slot it could reach
    cmd(ctx, 'setblock %d %d %d minecraft:stone' % belt)
    cmd(ctx, 'setblock %d %d %d hbmsntm:crane_extractor[input=north,output=up]' % under)
    cmd(ctx, 'item replace block %d %d %d container.19 with hbmsntm:upgrade_ejector_3' % under)
    cmd(ctx, 'item replace block %d %d %d container.0 with %s 4' % (core[0], core[1], core[2], item))
    ctx.step('wait', ticks=100)
    taken = [(s, i, c) for s, i, c in items(ctx, under) if 9 <= (s or 0) <= 17]
    detail = 'control insert through the bottom face: %s (inserter buffer %s, loose %d; core before %s, after %s); extractor took %s' % (
        inserted, buf, len(loose), before, after_insert, taken)
    if block == 'heater_heatex':
        # the original exposes no slot: the identifier must stay in the inserter's buffer (not in the core, not on the floor)
        kept = total(buf) == 1 and not loose and after_insert == before
        ctx.check(eid, kept and not taken, detail)
    elif inserted:
        ctx.check(eid, not taken, detail)
    else:
        ctx.review(eid, 'the control insert did not go in, so reaching the face is not shown; ' + detail)
    return inserted


def run(ctx):
    _lib.setup_world(ctx, freeze=False)
    hoppers(ctx)
    furnace_bucket(ctx)
    side_extraction(ctx, 'machine_assembly_machine', OX + 50,
                    [(0, 'minecraft:dirt', 2), (2, 'minecraft:stone', 2), (4, 'hbmsntm:ingot_uranium', 5), (5, 'minecraft:cobblestone', 5),
                     (16, 'minecraft:iron_ingot', 3)],
                    ['minecraft:cobblestone', 'minecraft:iron_ingot'], 'machine-item-capability.assembler-side',
                    # the recipe takes uranium ingots in the first input slot: they fit it, the cobblestone beside them does not
                    recipe='ass.boytarget', want_kept=[(4, 'hbmsntm:ingot_uranium', 5)])
    side_extraction(ctx, 'machine_chemical_plant', OX + 60,
                    [(0, 'minecraft:dirt', 2), (10, 'minecraft:sand', 2), (4, 'minecraft:cobblestone', 5), (7, 'minecraft:iron_ingot', 3)],
                    ['minecraft:cobblestone', 'minecraft:iron_ingot'], 'machine-item-capability.chemplant-side')
    rec = {}
    for i, (block, ident) in enumerate((('heater_firebox', False), ('heater_oven', False), ('heater_oilburner', True), ('heater_heatex', True))):
        rec[block] = heater(ctx, block, OX + 70 + 10 * i, ident)
    ctx.review('machine-item-capability.heater-insert-record', 'fluid identifier put in through the core bottom: fluid burner %s' % (
        rec.get('heater_oilburner'),))
