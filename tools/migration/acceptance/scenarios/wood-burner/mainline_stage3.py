"""Main line, stage 3 (first electricity): wood burner, red copper cable, battery socket, Stirling engine, boiler with steam
engine and condenser, fluid burner. Survival player, real crafting-table and steel-anvil crafting, real placement and real
GUI clicks; every machine of the stage is made from the items a player has when the stage starts.

Each section builds and runs its own line, so a section that cannot be built turns only its own rows into not-run:
  W  wood burner alone: 2 oak logs, switched on in its GUI, burns to its 100,000 HE cap and pauses.
  C  wood burner -> 5 red copper cables -> battery socket with a redstone battery; 2 oak logs end as 240,000 HE.
  S  firebox with 1 coal -> Stirling engine on top -> cables -> socket with a battery; 100 HE/t in the steady state.
  B  firebox with 1 coal -> boiler on top; a steel barrel feeds water, the steam goes straight into a steam engine
     whose spent steam goes into a condenser, whose water goes into a second barrel; heat and water are counted.
     Then the second barrel is switched to take nothing and 3 planks burn: the condenser and the engine fill up and
     the rest of the steam stays in the boiler, the state at rest that the reload compares.
  F  firebox -> combination oven making coal tar oil (creosote) from 4 coal -> fluid burner beside it, 1 mB/t.
  R  firebox with 1 coal -> boiler on top, water from a steel barrel; the boiler's east port is a steam inlet of a rotary
     furnace, which makes one steel ingot's worth of molten steel from an iron ingot and a coal on that steam.
Then the world is left and opened again and the same server readings are compared. The tick freeze is not kept across
leaving and opening (the world runs some ticks before it is frozen again), so the comparison covers state at rest that
differs from a new block: stored power with nothing to take it, fluid with nowhere to go, burn time of an idle machine,
modes and settings changed in their screens.

Expected values come from the NEO code (which follows the 1.7.10 original; the original lines are named beside the NEO
ones) and vanilla 1.21.1 burn times (oak log and oak planks 300 ticks, coal 1,600). A sprint started in the frozen world runs one tick
more than requested; the checks use the game-time difference the server reports. Readings are server block data.
A frozen server still updates the power and fluid nets on every server tick event (NtmEventHandler.java:69-76) until
their provider and receiver entries expire after 3,000 ms without a refresh (PowerNetMK2.java:22,42,61), so the
sections with cables (C, S) wait 4 s of wall time after a sprint before they read several blocks or a battery. The
other sections connect machines directly, without pipes: a direct transfer happens in the sending machine's own tick
(IFluidStandardSenderMK2.java:47-54; the barrels here are in send or receive mode, which make no net node,
BarrelBlockEntity.java:84-112), so nothing moves while the world is frozen.

Start items (given by command): the stage's handover list - plate_steel, plate_iron, plate_copper, plate_polymer,
plate_cast (copper, meta 5), ingot_steel, ingot_copper, ingot_red_copper, ingot_titanium, coil_copper, wire_red_copper,
shell_steel, tank_steel, pipe_steel, reinforced_stone, furnace_combination, ingot_firebrick - and vanilla materials (logs,
planks, coal, iron ingots, stone bricks, furnace, crafting table, redstone blocks, water buckets, cobblestone). Not on that list but given as well:
the steel anvil (made in stage 2 by smithing an iron anvil with 10 steel ingots) and the fluid identifier (dye, vacuum
tube, iron plate). The identifier's fluid is chosen in its own screen (FluidScreen): with an empty search the screen
lists the first nine fluids (water and steam among them); coal tar oil needs a typed search, which the executor cannot
type, so the fluid burner's identifier is given already set to coal tar oil (the one pre-written state, marked 预写).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='wood-burner.mainline_stage3',
    feature='wood-burner',
    features=['wood-burner', 'red-cable', 'battery-storage', 'stirling-power', 'heat-boiler', 'steam-power', 'fluid-burner',
              'rotary-furnace'],
    title='Main line stage 3: wood burner, cables, battery, Stirling, boiler and steam engine, fluid burner, rotary furnace on boiler steam '
          '(survival, real crafting and GUI)',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

Y = -60          # the flat world's first air layer
Z0 = 1000
SECTION_X = dict(W=1000, C=1030, S=1060, B=1100, F=1140, R=1200)

# fluid ids (registration order, Fluids.java:250-331)
WATER, STEAM, SPENTSTEAM, COALCREOSOTE = 1, 2, 48, 80
MAT_STEEL = 30                             # Mats.java:46,141 (_AS + 0); orig Mats.java:60,153
INGOT_QUANTA = 72                          # MaterialShapes.java:25 (NUGGET 8 x 9); orig MaterialShapes.java:44

E = [
    # wood-burner
    ('wood-burner.craft', 'crafting table, real clicks: 3 steel plates, 2 copper coils, a furnace and 2 iron ingots make 1 wood burner',
     'NtmRecipeProvider.java:478-487; orig CraftingManager.java:252'),
    ('wood-burner.burn', 'wood burner placed by hand, 2 oak logs put in its fuel slot and switched on in its GUI: the first tick takes a log '
     '(burn time 300 x 4 = 1,200, no power yet), then 100 HE a tick: after n ticks power = 100 x (n - 1), burn time 1,200 - (n - 1), one log left',
     'MachineWoodBurnerBlockEntity.java:42-55,118-146 (ModuleBurnTime log x4); orig TileEntityMachineWoodBurner.java:40,49,96-121,142-143'),
    ('wood-burner.full', 'with nothing connected the burner stops burning at its 100,000 HE cap: power 100,000, burn time 1,200 - 1,000 = 200, '
     'wood ash level 1,200 (under the 2,000 that makes one ash)',
     'MachineWoodBurnerBlockEntity.java:42,44,139-145,112; orig TileEntityMachineWoodBurner.java:40,105-108,118'),
    ('wood-burner.reload', 'after leaving and opening the world: the same power, burn time, max burn time, on switch, ash level and fuel count',
     'MachineWoodBurnerBlockEntity.java:325-350; orig TileEntityMachineWoodBurner.java:183-200'),
    # red-cable
    ('red-cable.craft', 'crafting table: 3 red copper wires and 2 insulator plates make 16 red copper cables',
     'NtmRecipeProvider.java:1369-1376; orig CraftingManager.java:240'),
    ('red-cable.line', 'wood burner -> 5 cables placed by hand -> battery socket: after the first 1,001 ticks battery charge + burner power = '
     '100 x 1,000; after both logs (2 x 1,200 burning ticks) the battery holds 240,000 HE, the burner 0, and the ash slot 1 wood ash (2,400 >= 2,000)',
     'MachineWoodBurnerBlockEntity.java:97-99,139-146,163-166; IEnergyProviderMK2.tryProvide; orig TileEntityMachineWoodBurner.java:96-121'),
    # battery-storage
    ('battery-storage.craft', 'crafting table: 2 steel plates and a red copper ingot make 1 battery socket; 4 iron plates, 3 redstone blocks '
     'and 2 insulator plates make 1 redstone battery',
     'NtmRecipeProvider.java:1777-1794; orig CraftingManager.java:259-260'),
    ('battery-storage.charge', 'the redstone battery put into the socket by hand (socket in its default input mode, no redstone) charges from the cable: '
     'capacity 1,800,000, charge rate 1,000 HE/t, so it takes all 240,000 HE',
     'BatteryPackItem.java:28,47-52; BatteryBaseBlockEntity.java:29,33,170; BatterySocketBlockEntity.java:131-135; '
     'orig ItemBatteryPack.java:33,53-56; TileEntityBatteryBase.java:41,45; TileEntityBatterySocket.java:260-263'),
    ('battery-storage.reload', 'with the line spent, the socket\'s screen is used: 3 clicks on the low-redstone mode (input -> buffer -> '
     'output -> none) and 1 on the priority (LOW -> NORMAL) give RedLow 3, RedHigh 2 (default), Priority 2; after leaving and opening the '
     'world the battery in the socket still holds the same charge and the socket the same three settings',
     'BatteryBaseBlockEntity.java:28-35,143-150,181-197; BatterySocketScreen.java:105-107; BatterySocketBlockEntity.java:98-105 '
     '(charge in the pack\'s item data, BatteryPackItem.java:86-94); orig TileEntityBatteryBase.java:45-47,143-146,177-192, '
     'GUIBatterySocket.java:78-80'),
    # stirling-power
    ('stirling-power.craft', 'large gear from 8 iron plates and a copper ingot (crafting table); firebox (furnace, 8 steel plates, 8 copper ingots) '
     'and Stirling engine (16 planks, 6 steel plates, 8 copper ingots, 4 copper coils, the gear) on the steel anvil',
     'NtmRecipeProvider.java:488-495; AnvilRecipes.java:387-394,424-434; orig CraftingManager.java:919, AnvilRecipes.java:273-278,344-351'),
    ('stirling-power.steady', 'firebox with 1 coal (200 TU/t: 100 x 2; burn time 1,600 x 1.25 = 2,000) under the Stirling engine, which pulls '
     'int(10 %) of the firebox heat a tick and makes heat x 0.5 HE: after warming up, the battery gains exactly 100 HE every tick of a measured '
     'window (both ends read after the 4 s the frozen net needs to hand out the last tick\'s power), the firebox holds 1,800-1,809 or '
     '2,000-2,009 TU (int(10 %) = 200 before or after its own tick), no overspeed (200 <= 300), and the engine buffer reads 0 because the '
     'network takes all of it and lowers the provider by what it handed out',
     'HeaterFireboxBlockEntity.java:20-36,91-125; MachineStirlingBlockEntity.java:28-31,56-60,167-181; PowerNetMK2.java:94-96; '
     'IEnergyProviderMK2.java:17-19; orig TileEntityHeaterFirebox.java:22-34, TileEntityFireboxBase.java:73-123, '
     'TileEntityStirling.java:38-39,73-76,170-174, PowerNetMK2.java:92'),
    ('stirling-power.reload', 'after leaving and opening the world: the battery charge, the cog and the burnt-out firebox are unchanged; '
     'the firebox\'s non-default field at rest is its max burn time 2,000 (one coal: 1,600 x 1.25); its heat cannot stay above 0 at rest '
     '(without fuel it loses max(heat / 1,000, 1) a tick, while burning it changes every tick), so it reads 0',
     'MachineStirlingBlockEntity.java:207-221; HeaterFireboxBlockEntity.java:24-27,99-100,120-125,178-194; '
     'orig TileEntityFireboxBase.java:93,120-122,206-222'),
    # heat-boiler
    ('heat-boiler.craft', 'steel anvil: firebox and boiler (4 steel ingots, 16 copper plates, 8 insulator plates)',
     'AnvilRecipes.java:387-394,466-473; orig AnvilRecipes.java:273-278,386-392'),
    ('heat-boiler.line', 'firebox (1 coal, 200 TU/t) -> boiler on top, water from a steel barrel set to water with the identifier and filled with '
     '3 buckets: the boiler pulls ceil(10 %) of the difference and turns 200 TU and 1 mB water into 100 mB steam, so while the coal burns '
     '200 x (ticks burnt) = firebox heat + boiler heat + 200 x (water used)',
     'AbstractBoilerBlockEntity.java:133-151,181-208; HeaterFireboxBlockEntity.java:91-125; Fluids.java:603-604; '
     'orig TileEntityHeatBoiler.java:52-53,182-187,218, Fluids.java:629-630'),
    ('heat-boiler.reload', 'after leaving and opening the world, with the line at rest (see steam-power.reload): the boiler\'s water, '
     'steam and heat, the firebox\'s heat, burn time and max burn time and the water barrel are unchanged, the boiler holding steam '
     '(output > 0) and water, the firebox max burn time 300 (oak planks: 300 ticks, no wood bonus in the firebox, heat 100 TU/t); '
     'boiler and firebox heat read 0 (heat decays at rest), the barrel keeps water type and send mode',
     'AbstractBoilerBlockEntity.java:133-151,181-208,261-279; HeaterFireboxBlockEntity.java:24-36,99-101,120-125,178-194; '
     'ModuleBurnTime.java:40-44,78; BarrelBlockEntity.java:324-333; orig TileEntityHeatBoiler.java:192,276-289, '
     'TileEntityFireboxBase.java:120-122,206-222'),
    # steam-power
    ('steam-power.craft', 'steel anvil: steam engine (16 reinforced stone, 12 steel plates, 2 steel shells, 4 copper coils, a large gear); '
     'crafting table: condenser (4 steel ingots, 4 iron plates, copper cast plate) and 2 steel barrels',
     'AnvilRecipes.java:476-485; NtmRecipeProvider.java:103-110,505-513; orig AnvilRecipes.java:362-369, CraftingManager.java:716,845'),
    ('steam-power.line', 'boiler steam goes straight into the steam engine (100 mB steam -> 1 mB spent steam), the spent steam into the '
     'condenser (1:1 water) and the water into the second barrel: 100 x water used = steam in boiler and engine + 100 x (spent steam in '
     'engine and condenser + condenser water + barrel water), with the barrel holding most of it',
     'MachineSteamEngineBlockEntity.java:31-33,80-88,116-119; CondenserBaseBlockEntity.java:42-57; Fluids.java:611; '
     'orig TileEntitySteamEngine.java:45-47,99-104, TileEntityCondenser.java:36-37,73-77, Fluids.java:637'),
    ('steam-power.power', 'while it runs the steam engine makes 200 x 0.85 = 170 HE per 100 mB steam: its buffer is a positive multiple of 170',
     'MachineSteamEngineBlockEntity.java:33,80-88; Fluids.java:611; orig TileEntitySteamEngine.java:47,104'),
    ('steam-power.reload', 'after the line has run, the second barrel is switched to its fourth mode in its screen (3 clicks: receive -> '
     'buffer -> send -> none, no demand) and 3 oak planks go into the firebox (900 ticks x 100 TU = 90,000 TU, about 450 boilings): '
     'the condenser fills its water tank (100) and then its spent-steam tank (100), the engine its spent-steam tank (20) and stops, '
     'its steam tank fills (2,000) and the rest stays in the boiler: at rest engine s 2,000, w 20, acceleration 0, condenser 100 / '
     '100, the barrel unchanged in mode 3, and 100 x water used = boiler steam + engine steam + 100 x (engine spent + condenser '
     'spent + condenser water + barrel). After leaving and opening the world these readings are unchanged, with the engine '
     '(s, w), the condenser (both tanks) and the barrel (its water) each holding fluid',
     'MachineSteamEngineBlockEntity.java:31-32,83-96,173-189; CondenserBaseBlockEntity.java:25-26,42-57,81-95; '
     'BarrelBlockEntity.java:259-269,324-333; BarrelScreen.java:42; Fluids.java:603-604,611; orig TileEntitySteamEngine.java:45-46,'
     '52-53,107-112,167-183, TileEntityCondenser.java:31-37,73-83, TileEntityBarrel.java:49-50,79-81,211-219'),
    # fluid-burner
    ('fluid-burner.craft', 'steel anvil: fluid burner (4 steel tanks, 3 steel pipes, 12 titanium ingots, 8 copper ingots) and a firebox',
     'AnvilRecipes.java:549-556,387-394; orig AnvilRecipes.java:293-300,273-278'),
    ('fluid-burner.line', 'combination oven on a burning firebox: 4 coal -> 4 coke + 4 x 100 mB coal tar oil, pushed into the fluid burner '
     'beside it (identifier 预写: set to coal tar oil by command), switched on in its GUI at 1 mB/t: 250,000 / 1,000 = 250 TU per mB, '
     'no cooling while on, so its heat = 250 x mB burnt at every read and 100,000 TU with the tank empty at the end',
     'CombinationRecipes.java:30; MachineFurnaceCombinationBlockEntity.java:80-86; HeaterOilburnerBlockEntity.java:91-134; Fluids.java:737; '
     'orig CombinationRecipes.java:41, TileEntityHeaterOilburner.java:90-96, Fluids.java:763'),
    ('fluid-burner.reload', 'after leaving and opening the world: the burner heat, tank, fluid type, switch and burn setting and the oven\'s coke are unchanged',
     'HeaterOilburnerBlockEntity.java:291-307'),
    # rotary-furnace
    ('rotary-furnace.craft', 'steel anvil: rotary furnace from 8 stone bricks, 16 firebricks, 4 iron ingots and 8 copper plates (with a firebox '
     'and a boiler for its steam, and a steel barrel at the crafting table)',
     'AnvilRecipes.java:230-238; orig AnvilRecipes.java:336-342'),
    ('rotary-furnace.line', 'firebox (1 coal) -> boiler on top, water from a steel barrel (identifier set to water in its screen, 2 buckets); '
     'the boiler\'s east port is a back block of a rotary furnace facing east, one of its two steam inlets. The furnace takes steam while '
     'idle; with its 12,000 mB steam tank full, 1 iron ingot and 1 coal go into its inputs and 1 coal into its fuel slot (taken only with a '
     'recipe: 1,600 / 2 = 800 ticks, heat 1). It processes only while it has steam: each tick 100 mB steam (steam use x (10 log10(1) + 1) = 1), '
     'progress + 1/100 and 1 mB spent steam back, so after P = 100 processing ticks (101 when the float sum of 0.01 falls short of 1) it holds '
     '72 quanta of steel (one ingot) and nothing pours without a casting target: burn time 800 - P, spent steam P, inputs and fuel slot '
     'empty, and, with the boiler still boiling (water used > 0), 100 x water used = boiler steam gain + furnace steam gain + 100 x P',
     'MachineRotaryFurnaceBlockEntity.java:78-82,95-105,141-200,230-275; RotaryFurnaceRecipes.java:41; ModuleBurnTime.java:40-56; '
     'CrucibleUtil.java:27-44; MachineHeatBoilerBlockEntity.java:44-57; AbstractBoilerBlockEntity.java:71-76,133-151; Fluids.java:603-604; '
     'orig TileEntityMachineRotaryFurnace.java:58,67-82,101-112,150-223,331-350, RotaryFurnaceRecipes.java:39, Fluids.java:629-630'),
    ('rotary-furnace.reload', 'after leaving and opening the world, the idle furnace (no recipe left, so it neither burns nor progresses): its '
     'steel output type and amount, burn time, max burn time, burn heat, progress and spent steam, and the water barrel\'s fill, fluid type '
     'and send mode are unchanged',
     'MachineRotaryFurnaceBlockEntity.java:202-205,328-359; BarrelBlockEntity.java:324-333; orig TileEntityMachineRotaryFurnace.java:225-227,300-330, '
     'TileEntityBarrel.java:208-220'),
]


def expectations():
    return [dict(id=i, text=t, source=s) for i, t, s in E]


# ---------------------------------------------------------------- generic helpers (candidates for _lib.py)

def cmd(ctx, command, **kw):
    return ctx.step('cmd', command=command, **kw)


def inventory(ctx):
    inv = ctx.step('inv')
    return {s['slot']: (s.get('item'), s.get('count', 0), s.get('components')) for s in inv['slots']
            if s.get('item') and s.get('item') != 'minecraft:air' and s['slot'] < 36}


def count(ctx, item):
    return sum(c for i, c, _ in inventory(ctx).values() if i == item)


def table_slot(inv_slot):
    """Crafting table menu slot of a player inventory slot (hotbar 0-8 -> 37-45, main 9-35 -> 10-36)."""
    return 37 + inv_slot if inv_slot < 9 else 10 + (inv_slot - 9)


def menu_slot(n_machine, inv_slot):
    """Menu slot of a player inventory slot in a machine menu that adds its own n slots, then the 27 main slots, then the hotbar."""
    return n_machine + 27 + inv_slot if inv_slot < 9 else n_machine + (inv_slot - 9)


def craft(ctx, out, made, pattern, key):
    before = count(ctx, out)
    used = []
    for sym, item in key.items():
        cells = [1 + r * 3 + c for r, row in enumerate(pattern) for c, ch in enumerate(row) if ch == sym]
        src = next((s for s, (i, n, _) in sorted(inventory(ctx).items()) if i == item and n >= len(cells)), None)
        if src is None:
            return False, '%s: no stack of %s with %d items' % (out, item, len(cells))
        ctx.step('click', slot=table_slot(src), after=2)
        for cell in cells:
            ctx.step('click', slot=cell, button=1, after=2)
        ctx.step('click', slot=table_slot(src), after=2)
        used.append('%d %s' % (len(cells), item.split(':')[1]))
    ctx.step('mod', shift=True)
    ctx.step('click', slot=0, after=4)
    ctx.step('mod', shift=False)
    after = count(ctx, out)
    return after - before == made, '%s %d -> %d (want +%d) from %s' % (out.split(':')[1], before, after, made, ', '.join(used))


def hold(ctx, item):
    """Brings `item` into the first hotbar slot as a player does (inventory screen, number key 1 over its slot) and selects it."""
    src = next((s for s, (i, n, _) in sorted(inventory(ctx).items()) if i == item), None)
    if src is None:
        raise RuntimeError('no %s in the inventory' % item)
    if src != 0:
        ctx.step('key', key='key.keyboard.e', action='tap', after=4)
        ctx.step('screen', expect='Inventory')
        ctx.step('hover', slot=36 + src if src < 9 else src, frames=2)
        ctx.step('key', key='key.keyboard.1', action='tap', after=3)
        ctx.step('close')
    ctx.step('key', key='key.keyboard.1', action='tap', after=2)


def empty_hand(ctx):
    inv = inventory(ctx)
    free = next((s for s in range(9) if s not in inv), None)
    if free is None:
        main = next(s for s in range(9, 36) if s not in inv)
        ctx.step('key', key='key.keyboard.e', action='tap', after=4)
        ctx.step('screen', expect='Inventory')
        ctx.step('hover', slot=main, frames=2)
        ctx.step('key', key='key.keyboard.1', action='tap', after=3)
        ctx.step('close')
        free = 0
    ctx.step('key', key='key.keyboard.%d' % (free + 1), action='tap', after=2)


def sneak(ctx, on):
    ctx.step('key', key='key.keyboard.left.shift', action='press' if on else 'release', after=3)


def face_point(pos, face):
    d = _lib.VEC[face]
    return [pos[0] + 0.5 + d[0] * 0.499, pos[1] + 0.5 + d[1] * 0.499, pos[2] + 0.5 + d[2] * 0.499]


def use_on(ctx, pos, face, stand, crouch=False, offset=None):
    """Stands at `stand` (feet), looks at the face of the block at `pos` and right-clicks it (sneaking with crouch=True,
    so a machine's own interaction does not take the click and the held item is placed against it). `offset` moves the
    aim point from the face centre, for blocks whose shape is smaller than the cube."""
    look = face_point(pos, face)
    if offset:
        look = [look[i] + offset[i] for i in range(3)]
    ctx.step('view', pos=stand, look_at=look, fly=False, hide_gui=False)
    if crouch:
        sneak(ctx, True)
    target = dict(pos=list(pos), face=face)
    if offset:
        target['offset'] = list(offset)
    try:
        ctx.step('use', target=target, after=6)
    finally:
        if crouch:
            sneak(ctx, False)


def place(ctx, item, against, face, stand, crouch=False):
    hold(ctx, item)
    use_on(ctx, against, face, stand, crouch)


def open_gui(ctx, pos, face, stand, expect, offset=None):
    empty_hand(ctx)
    use_on(ctx, pos, face, stand, offset=offset)
    ctx.step('screen', expect=expect)


def put(ctx, n_machine, item, machine_slot, one=False):
    """Moves a stack (or one item with one=True) of `item` from the player inventory into a machine slot by clicks."""
    src = next((s for s, (i, n, _) in sorted(inventory(ctx).items()) if i == item), None)
    if src is None:
        raise RuntimeError('no %s to put into slot %d' % (item, machine_slot))
    ctx.step('click', slot=menu_slot(n_machine, src), after=2)
    c = ctx.step('click', slot=machine_slot, button=1 if one else 0, after=3)
    if c['after']['carried_count']:
        ctx.step('click', slot=menu_slot(n_machine, src), after=2)
    if c['after']['slot_item'] != item:
        raise RuntimeError('slot %d holds %s after putting %s' % (machine_slot, c['after']['slot_item'], item))
    return c['after']['slot_count']


def gui_origin(ctx):
    hud = ctx.step('hud', frames=2)
    return hud['gui_left'], hud['gui_top'], hud


def find_core(ctx, block, lo, hi):
    d = ctx.step('dump', **{'from': list(lo), 'to': list(hi)})
    cores = [b for b in d['blocks'] if b['block'] == block and b['props'].get('type', 'core') == 'core']
    if len(cores) != 1:
        raise RuntimeError('%s: expected one core in %s..%s, found %s' % (block, lo, hi, [c['pos'] for c in cores]))
    return tuple(int(c) for c in cores[0]['pos']), cores[0]['props']


def give(ctx, stacks):
    cmd(ctx, 'clear @s', allow_error=True)
    for item, n in stacks:
        cmd(ctx, 'give @s %s %d' % (item, n))


def slot_item(data, slot):
    return next((it for it in data.get('Items', []) if it.get('Slot') == slot), None)


def slot_count(data, slot, item=None):
    it = slot_item(data, slot)
    if it is None or (item and it.get('id') != item):
        return 0
    return it.get('count', 1)


def charge_of(ctx, socket):
    it = slot_item(_lib.block_data(ctx, socket), 0)
    if it is None:
        return None
    return it.get('components', {}).get('minecraft:custom_data', {}).get('Charge', 0)


def tank(data, name):
    t = _lib.tanks(data).get(name)
    return t['fill'] if t else None


def sprint(ctx, ticks, label, until=None):
    r = ctx.sprint(ticks, until=until, label=label, poll_s=1.0, timeout_s=900)
    return r


def settle(ctx, r=None):
    """After a sprint (or a reopen) in a section with cables: the world frozen, then 4 s of wall time, so the power net
    has handed out what the providers held and dropped its entries (NtmEventHandler.java:69-76, PowerNetMK2.java:22,42,61);
    readings of several blocks taken after it belong together."""
    if r is None or not r.get('frozen_after'):
        ctx.server('tick freeze')
    ctx.step('wait', ticks=80)


def shot(ctx, name, eye, look_at):
    ctx.step('view', pos=eye, look_at=look_at, fly=True, hide_gui=True)
    ctx.step('wait', ticks=10)
    path = ctx.shot_name(name)
    ctx.step('shot', file=path)
    ctx.step('view', pos=eye, look_at=look_at, fly=True, hide_gui=False)
    return path


# ---------------------------------------------------------------- the steel anvil

ANVIL = 'hbmsntm:anvil[hbmsntm:meta=2]'   # NTMAnvilBlock.Variant.STEEL, tier 2 (NTMAnvilBlock.java:57-73)
ANVIL_PAGE = 10                            # AnvilMenuScreen.java:30
# placed from the south the anvil faces south and is 12 px high, 8 px deep (z 4..12): aim at the middle of that face
ANVIL_AIM = (0.0, -0.25, -0.25)            # NTMAnvilBlock.java:93,114-116,131-132


def anvil_recipes(ctx):
    """The construction recipes a tier-2 anvil lists, in the anvil screen's order (AnvilMenuScreen.java:46-50)."""
    r = ctx.step('export', kind='anvil')
    path = Path(ctx.channels[ctx.default].dir) / r['file']
    rows = json.loads(path.read_text(encoding='utf-8'))['construction']
    return [x for x in rows if x['tier_lower'] <= 2 and (x['tier_upper'] == -1 or x['tier_upper'] >= 2)]


def anvil_build(ctx, anvil_pos, stand, recipes, out, need):
    """Opens the anvil by hand, pages to the recipe making `out` that takes `need`, selects it and presses construct.
    Returns (ok, detail)."""
    pos = next((p for p, x in enumerate(recipes) if x['outputs'][0]['id'] == out
                and any(a['id'] == need for alts in x['inputs'] for a in alts)), None)
    if pos is None:
        return False, 'no tier-2 anvil recipe for %s with %s' % (out, need)
    before = count(ctx, out)
    open_gui(ctx, anvil_pos, 'south', stand, 'Anvil', offset=ANVIL_AIM)
    size = max(0, -(-(len(recipes) - ANVIL_PAGE) // 2))
    index = min(pos // 2, size)
    left, top, _ = gui_origin(ctx)
    # the list scrolls one column per click on its right arrow (AnvilMenuScreen.java:225-230; the original's only paging
    # besides the wheel, GUIAnvil.mouseClicked); the screen opens on the first column
    for _ in range(index):
        ctx.step('click', at=[left + 106 + 4, top + 71 + 18], after=1)
    ind = pos - index * 2
    cell = [left + 16 + 18 * (ind // 2) + 9, top + 71 + 18 * (ind % 2) + 9]
    ctx.step('hover', at=cell, frames=3)
    tip = [t['text'] for t in ctx.step('hud', frames=3).get('texts', []) if t['text'].startswith('tooltip: ')]
    ctx.step('click', at=cell, after=3)
    ctx.step('click', at=[left + 52 + 9, top + 53 + 9], after=6)
    ctx.step('close')
    after = count(ctx, out)
    return after == before + 1, '%s %d -> %d (anvil list position %d of %d, page %d, cell %d, tooltip %s)' % (
        out.split(':')[1], before, after, pos, len(recipes), index, ind, tip[:1])


def set_identifier(ctx, item_index):
    """Holds the identifier and picks the fluid at `item_index` of its screen's unfiltered list (FluidScreen.java:174-190:
    backspace in the empty search fills the nine buttons in Fluids.metaOrder order) with a left click (primary type)."""
    hold(ctx, 'hbmsntm:fluid_identifier_multi')
    sneak(ctx, True)
    try:
        ctx.step('use', after=6)
    finally:
        sneak(ctx, False)
    ctx.step('screen', expect='FluidScreen')
    ctx.step('key', key='key.keyboard.backspace', action='tap', after=2)
    hud = ctx.step('hud', frames=2)
    left = (hud['gui_scaled_width'] - 176) // 2
    top = (hud['gui_scaled_height'] - 54) // 2
    ctx.step('click', at=[left + 7 + item_index * 18 + 9, top + 29 + 9], after=4)
    ctx.step('close')


# ---------------------------------------------------------------- sections

COMMON = [('minecraft:crafting_table', 1)]


def build_table(ctx, x, z):
    place(ctx, 'minecraft:crafting_table', (x, Y - 1, z), 'up', [x + 0.5, Y, z + 3.5])
    open_gui(ctx, (x, Y, z), 'south', [x + 0.5, Y, z + 2.5], 'Crafting')


def build_anvil(ctx, x, z):
    place(ctx, 'hbmsntm:anvil', (x, Y - 1, z), 'up', [x + 0.5, Y, z + 3.5])
    return (x, Y, z), [x + 0.5, Y, z + 2.5]


def wood_burner_rig(ctx, x, z):
    """Crafts and places a wood burner facing south at core (x, Y, z) (power ports at z - 2); returns the core."""
    build_table(ctx, x + 6, z + 6)
    ok, line = craft(ctx, 'hbmsntm:machine_wood_burner', 1, ['AAA', 'BDB', 'C C'],
                     dict(A='hbmsntm:plate_steel', B='hbmsntm:coil_copper', C='minecraft:iron_ingot', D='minecraft:furnace'))
    ctx.step('close')
    if not ok:
        raise RuntimeError('wood burner not crafted: ' + line)
    return line


def place_wood_burner(ctx, x, z):
    place(ctx, 'hbmsntm:machine_wood_burner', (x, Y - 1, z), 'up', [x + 0.5, Y, z + 3.5])
    core, props = find_core(ctx, 'hbmsntm:machine_wood_burner', (x - 2, Y, z - 2), (x + 2, Y + 1, z + 2))
    if core != (x, Y, z):
        raise RuntimeError('wood burner core at %s, expected %s' % (core, (x, Y, z)))
    return core


def load_wood_burner(ctx, core, logs):
    x, _, z = core
    open_gui(ctx, core, 'south', [x + 0.5, Y, z + 2.5], 'WoodBurner')
    put(ctx, 6, 'minecraft:oak_log', 0)
    left, top, _ = gui_origin(ctx)
    ctx.step('click', at=[left + 61, top + 24], after=4)   # on/off: MachineWoodBurnerScreen.java:93 (53, 17, 16 x 15)
    ctx.step('close')
    d = _lib.block_data(ctx, core)
    if not d.get('isOn') or slot_count(d, 0, 'minecraft:oak_log') != logs:
        raise RuntimeError('wood burner after the GUI: isOn %s, fuel %s' % (d.get('isOn'), slot_item(d, 0)))


def section_w(ctx, saved):
    x, z = SECTION_X['W'], Z0
    _lib.go_near(ctx, x, Y, z)
    give(ctx, COMMON + [('hbmsntm:plate_steel', 3), ('hbmsntm:coil_copper', 2), ('minecraft:iron_ingot', 2),
                        ('minecraft:furnace', 1), ('minecraft:oak_log', 2)])
    line = wood_burner_rig(ctx, x, z)
    ctx.check('wood-burner.craft', count(ctx, 'hbmsntm:machine_wood_burner') == 1 and count(ctx, 'hbmsntm:plate_steel') == 0
              and count(ctx, 'hbmsntm:coil_copper') == 0 and count(ctx, 'minecraft:furnace') == 0 and count(ctx, 'minecraft:iron_ingot') == 0,
              line)
    core = place_wood_burner(ctx, x, z)
    load_wood_burner(ctx, core, 2)
    r1 = sprint(ctx, 500, 'W-burn')
    n = r1['advanced']
    d = _lib.block_data(ctx, core)
    want_p, want_b = 100 * (n - 1), 1200 - (n - 1)
    ctx.check('wood-burner.burn', d['power'] == want_p and d['burnTime'] == want_b and d['maxBurnTime'] == 1200
              and slot_count(d, 0, 'minecraft:oak_log') == 1,
              '%d ticks: power %d (want %d), burnTime %d (want %d), maxBurnTime %d, logs left %d; %.0f ticks/s'
              % (n, d['power'], want_p, d['burnTime'], want_b, d['maxBurnTime'], slot_count(d, 0, 'minecraft:oak_log'), r1['ticks_per_s'] or 0))
    r2 = sprint(ctx, 800, 'W-full')
    d = _lib.block_data(ctx, core)
    burnt = min(1000, (n - 1) + r2['advanced'])
    ev = shot(ctx, 'W-wood-burner', [x + 4.5, Y + 3, z + 5.5], [x, Y + 1, z])
    ctx.check('wood-burner.full', burnt == 1000 and d['power'] == 100000 and d['burnTime'] == 200 and d['ashLevelWood'] == 1200
              and slot_count(d, 0, 'minecraft:oak_log') == 1 and d.get('isOn'),
              'after %d more ticks: power %d (want 100000), burnTime %d (want 200), ashLevelWood %d (want 1200), logs %d'
              % (r2['advanced'], d['power'], d['burnTime'], d['ashLevelWood'], slot_count(d, 0, 'minecraft:oak_log')), [ev])
    keys = ('power', 'burnTime', 'maxBurnTime', 'isOn', 'ashLevelWood')
    saved['W'] = (core, {k: d.get(k) for k in keys}, slot_count(d, 0, 'minecraft:oak_log'))


def socket_rig(ctx, x, z):
    """Places the crafted battery socket facing south with its core at (x, Y, z) and puts the battery in by hand."""
    place(ctx, 'hbmsntm:machine_battery_socket', (x, Y - 1, z), 'up', [x + 0.5, Y, z + 3.5])
    core, _ = find_core(ctx, 'hbmsntm:machine_battery_socket', (x - 2, Y, z - 2), (x + 2, Y + 1, z + 2))
    if core != (x, Y, z):
        raise RuntimeError('socket core at %s, expected %s' % (core, (x, Y, z)))
    open_gui(ctx, core, 'east', [x + 2.5, Y, z + 0.5], 'BatterySocket')
    put(ctx, 1, 'hbmsntm:battery_pack', 0)
    ctx.step('close')
    if charge_of(ctx, core) is None:
        raise RuntimeError('no battery in the socket')
    return core


def open_table(ctx, x, z):
    open_gui(ctx, (x, Y, z), 'south', [x + 0.5, Y, z + 2.5], 'Crafting')


def craft_power_parts(ctx, x, z, burner=True, table_placed=False):
    """Crafts at one table: (wood burner,) 16 cables, a socket and a redstone battery. Returns the check lines."""
    if table_placed:
        open_table(ctx, x, z)
    else:
        build_table(ctx, x, z)
    lines, ok = [], True
    plan = []
    if burner:
        plan.append(('hbmsntm:machine_wood_burner', 1, ['AAA', 'BDB', 'C C'],
                     dict(A='hbmsntm:plate_steel', B='hbmsntm:coil_copper', C='minecraft:iron_ingot', D='minecraft:furnace')))
    plan += [('hbmsntm:red_cable', 16, [' I ', 'WWW', ' I '], dict(I='hbmsntm:plate_polymer', W='hbmsntm:wire_red_copper')),
             ('hbmsntm:machine_battery_socket', 1, ['   ', 'ABA', '   '], dict(A='hbmsntm:plate_steel', B='hbmsntm:ingot_red_copper')),
             ('hbmsntm:battery_pack', 1, ['IRI', 'PRP', 'IRI'], dict(I='hbmsntm:plate_iron', R='minecraft:redstone_block', P='hbmsntm:plate_polymer'))]
    results = {}
    for out, made, pattern, key in plan:
        good, line = craft(ctx, out, made, pattern, key)
        results[out] = good
        ok = ok and good
        lines.append(line)
    ctx.step('close')
    return ok, results, lines


POWER_GIVE = [('hbmsntm:wire_red_copper', 3), ('hbmsntm:plate_polymer', 4), ('hbmsntm:ingot_red_copper', 1),
              ('hbmsntm:plate_iron', 4), ('minecraft:redstone_block', 3)]


def section_c(ctx, saved):
    x, z = SECTION_X['C'], Z0
    _lib.go_near(ctx, x, Y, z)
    give(ctx, COMMON + POWER_GIVE + [('hbmsntm:plate_steel', 5), ('hbmsntm:coil_copper', 2), ('minecraft:iron_ingot', 2),
                                     ('minecraft:furnace', 1), ('minecraft:oak_log', 2)])
    ok, results, lines = craft_power_parts(ctx, x + 6, z + 6)
    ctx.check('red-cable.craft', results.get('hbmsntm:red_cable', False), lines[1])
    ctx.check('battery-storage.craft', results.get('hbmsntm:machine_battery_socket', False) and results.get('hbmsntm:battery_pack', False),
              '; '.join(lines[2:]))
    if not ok:
        raise RuntimeError('crafting failed: ' + '; '.join(lines))
    # the socket north of the burner: core (x, Y, z - 7), its south connection (x, Y, z - 6) is the first cable
    socket = socket_rig(ctx, x, z - 7)
    for cz in (z - 6, z - 5, z - 4, z - 3, z - 2):
        place(ctx, 'hbmsntm:red_cable', (x, Y - 1, cz), 'up', [x + 1.5, Y, cz + 2.5])
    core = place_wood_burner(ctx, x, z)
    load_wood_burner(ctx, core, 2)
    r1 = sprint(ctx, 1000, 'C-cable-1')
    settle(ctx, r1)
    d, c = _lib.block_data(ctx, core), charge_of(ctx, socket)
    burnt1 = min(1200, r1['advanced'] - 1)
    mid_ok = c + d['power'] == 100 * burnt1 and c > 0 and d['power'] < 100 * burnt1
    mid = 'after %d ticks: battery %d + burner %d = %d (want %d)' % (r1['advanced'], c, d['power'], c + d['power'], 100 * burnt1)
    r2 = sprint(ctx, 2000, 'C-cable-2')
    settle(ctx, r2)
    d, c = _lib.block_data(ctx, core), charge_of(ctx, socket)
    ash = slot_item(d, 1)
    ev = shot(ctx, 'C-cable-line', [x + 5.5, Y + 4, z + 3.5], [x, Y, z - 4])
    total = r1['advanced'] + r2['advanced']
    ctx.check('red-cable.line', mid_ok and total >= 2402 and c == 240000 and d['power'] == 0 and d['burnTime'] == 0
              and slot_count(d, 0) == 0 and ash is not None and ash.get('id') == 'hbmsntm:powder_ash_wood' and ash.get('count', 1) == 1
              and d['ashLevelWood'] == 400,
              '%s; after %d ticks in all: battery %d (want 240000), burner power %d, burnTime %d, fuel %d, ash %s, ashLevelWood %d (want 400)'
              % (mid, total, c, d['power'], d['burnTime'], slot_count(d, 0), ash, d['ashLevelWood']), [ev])
    sd = _lib.block_data(ctx, socket)
    ctx.check('battery-storage.charge', c == 240000 and sd.get('RedLow') == 0 and slot_item(sd, 0).get('id') == 'hbmsntm:battery_pack',
              'socket item %s, Charge %d of 1,800,000, RedLow %s RedHigh %s Priority %s'
              % (slot_item(sd, 0).get('id'), c, sd.get('RedLow'), sd.get('RedHigh'), sd.get('Priority')))
    # settings changed in the socket's screen for the reload comparison (BatterySocketScreen.java:105-107: low mode 106, 16,
    # 18 x 18; priority 125, 35, 16 x 16): low 0 -> 1 -> 2 -> 3 (none, so the charge stays where it is), priority LOW -> NORMAL
    open_gui(ctx, socket, 'east', [socket[0] + 2.5, Y, socket[2] + 0.5], 'BatterySocket')
    left, top, _ = gui_origin(ctx)
    for _ in range(3):
        ctx.step('click', at=[left + 115, top + 25], after=4)
    ctx.step('click', at=[left + 133, top + 43], after=4)
    ctx.step('close')
    sd = _lib.block_data(ctx, socket)
    settings = {k: sd.get(k) for k in ('RedLow', 'RedHigh', 'Priority')}
    saved['C'] = (socket, charge_of(ctx, socket), settings)


def build_firebox(ctx, x, z):
    """Firebox facing south placed by hand from the south onto (x, Y - 1, z): core (x, Y, z - 1), 3 x 3 x 1."""
    place(ctx, 'hbmsntm:heater_firebox', (x, Y - 1, z), 'up', [x + 0.5, Y, z + 3.5])
    core, _ = find_core(ctx, 'hbmsntm:heater_firebox', (x - 2, Y, z - 3), (x + 2, Y, z + 1))
    if core != (x, Y, z - 1):
        raise RuntimeError('firebox core at %s, expected %s' % (core, (x, Y, z - 1)))
    return core


def stack_on_firebox(ctx, item, x, z):
    """A 3 x 3 machine with core offset 1 put on the firebox by sneaking and clicking the top of the firebox block in front
    of its core: its core lands right above the firebox core (DummyableBlock.setPlacedBy)."""
    place(ctx, 'hbmsntm:' + item, (x, Y, z), 'up', [x + 0.5, Y, z + 3.5], crouch=True)
    core, _ = find_core(ctx, 'hbmsntm:' + item, (x - 2, Y + 1, z - 3), (x + 2, Y + 4, z + 1))
    if core != (x, Y + 1, z - 1):
        raise RuntimeError('%s core at %s, expected %s' % (item, core, (x, Y + 1, z - 1)))
    return core


def fuel_firebox(ctx, firebox, face_block, face, stand, coal, one=False, item='minecraft:coal'):
    open_gui(ctx, face_block, face, stand, 'Firebox')
    put(ctx, 2, item, 0, one=one)
    ctx.step('close')
    d = _lib.block_data(ctx, firebox)
    if slot_count(d, 0, item) != coal:
        raise RuntimeError('firebox fuel slot %s' % slot_item(d, 0))


def section_s(ctx, saved):
    x, z = SECTION_X['S'], Z0
    _lib.go_near(ctx, x, Y, z)
    give(ctx, COMMON + POWER_GIVE + [('hbmsntm:plate_steel', 16), ('hbmsntm:plate_iron', 8), ('hbmsntm:ingot_copper', 17),
                                     ('hbmsntm:coil_copper', 4), ('minecraft:oak_planks', 16), ('minecraft:furnace', 1), (ANVIL, 1),
                                     ('minecraft:coal', 1)])
    # the large gear at the table, then the power parts
    build_table(ctx, x + 6, z + 6)
    gear_ok, gear_line = craft(ctx, 'hbmsntm:gear_large', 1, ['III', 'ICI', 'III'], dict(I='hbmsntm:plate_iron', C='hbmsntm:ingot_copper'))
    ctx.step('close')
    ok, results, lines = craft_power_parts(ctx, x + 6, z + 6, burner=False, table_placed=True) if gear_ok else (False, {}, [])
    anvil, stand = build_anvil(ctx, x - 6, z + 6)
    recipes = anvil_recipes(ctx)
    fb_ok, fb_line = anvil_build(ctx, anvil, stand, recipes, 'hbmsntm:heater_firebox', 'hbmsntm:ingot_copper')
    st_ok, st_line = anvil_build(ctx, anvil, stand, recipes, 'hbmsntm:machine_stirling', 'hbmsntm:ingot_copper')
    ctx.check('stirling-power.craft', gear_ok and fb_ok and st_ok and count(ctx, 'hbmsntm:gear_large') == 0,
              '; '.join([gear_line, fb_line, st_line]))
    if not (ok and fb_ok and st_ok):
        raise RuntimeError('parts missing: %s' % '; '.join(lines + [fb_line, st_line]))
    socket = socket_rig(ctx, x + 7, z - 1)                 # its west connection (x + 5, Y, z - 1) is the last cable
    firebox = build_firebox(ctx, x, z)
    fuel_firebox(ctx, firebox, (x, Y, z), 'south', [x + 0.5, Y, z + 2.5], 1)
    stirling = stack_on_firebox(ctx, 'machine_stirling', x, z)
    for cx in (x + 5, x + 4, x + 3, x + 2):
        place(ctx, 'hbmsntm:red_cable', (cx, Y - 1, z - 1), 'up', [cx + 0.5, Y, z + 2.5])
    # the Stirling engine's east connection is (x + 2, Y + 1, z - 1): a cable on top of the ground cable, whose top is
    # 10.5 px high (CableBlock.java:99-113), clicked from one block south of it
    hold(ctx, 'hbmsntm:red_cable')
    use_on(ctx, (x + 2, Y, z - 1), 'up', [x + 2.5, Y, z + 0.5], crouch=True, offset=(0.0, -0.35, 0.0))
    warm = sprint(ctx, 300, 'S-warmup')
    settle(ctx, warm)
    c1 = charge_of(ctx, socket)
    win = sprint(ctx, 1000, 'S-window')
    settle(ctx, win)
    c2 = charge_of(ctx, socket)
    sd, fd = _lib.block_data(ctx, stirling), _lib.block_data(ctx, firebox)
    n = win['advanced']
    heat = fd['heatEnergy']
    ev = shot(ctx, 'S-stirling-line', [x + 4.5, Y + 4, z + 5.5], [x + 2, Y + 1, z - 1])
    ctx.check('stirling-power.steady', c2 - c1 == 100 * n and sd['powerBuffer'] == 0 and sd.get('overspeed', 0) == 0 and sd.get('hasCog')
              and (1800 <= heat <= 1809 or 2000 <= heat <= 2009),
              'warm-up %d ticks; window %d ticks: battery %d -> %d (+%d, want %d); Stirling buffer %d, overspeed %d; firebox heat %d, burnTime %d; %.0f ticks/s'
              % (warm['advanced'], n, c1, c2, c2 - c1, 100 * n, sd['powerBuffer'], sd.get('overspeed', 0), heat, fd['burnTime'], win['ticks_per_s'] or 0),
              [ev])
    tail = sprint(ctx, 1200, 'S-tail')
    settle(ctx, tail)
    fd = _lib.block_data(ctx, firebox)
    c3 = charge_of(ctx, socket)
    saved['S'] = (socket, c3, firebox, dict(heatEnergy=fd['heatEnergy'], burnTime=fd['burnTime'], maxBurnTime=fd.get('maxBurnTime'),
                                            coal=slot_count(fd, 0)), stirling,
                  dict(hasCog=_lib.block_data(ctx, stirling).get('hasCog')), 'tail %d ticks: firebox heat %d, burnTime %d'
                  % (tail['advanced'], fd['heatEnergy'], fd['burnTime']))


def configure_barrel(ctx, barrel, face, stand, buckets, mode_clicks):
    """Barrel GUI by hand: the water identifier into slot 0 (BarrelBlockEntity.java:66 sets the type and moves it to slot 1),
    `mode_clicks` presses of the mode button (BarrelScreen: 151, 34, 18 x 18; 0 receive, 1 buffer, 2 send), and each water
    bucket into slot 2 with one server tick in between (loadTank, :69). The world stays frozen otherwise."""
    open_gui(ctx, barrel, face, stand, 'Barrel')
    put(ctx, 6, 'hbmsntm:fluid_identifier_multi', 0, one=True)
    left, top, _ = gui_origin(ctx)
    for _ in range(mode_clicks):
        ctx.step('click', at=[left + 160, top + 43], after=4)
    ctx.server('tick step 1')
    ctx.step('wait', ticks=5)
    for _ in range(buckets):
        put(ctx, 6, 'minecraft:water_bucket', 2)
        ctx.server('tick step 1')
        ctx.step('wait', ticks=5)
    ctx.step('close')
    return _lib.block_data(ctx, barrel)


def section_b(ctx, saved):
    x, z = SECTION_X['B'], Z0
    _lib.go_near(ctx, x, Y, z)
    give(ctx, COMMON + [('hbmsntm:plate_steel', 32), ('hbmsntm:ingot_copper', 9), ('hbmsntm:ingot_steel', 12), ('hbmsntm:plate_copper', 16),
                        ('hbmsntm:plate_polymer', 8), ('hbmsntm:reinforced_stone', 16), ('hbmsntm:shell_steel', 2),
                        ('hbmsntm:coil_copper', 4), ('hbmsntm:plate_iron', 12), ('hbmsntm:plate_cast[hbmsntm:meta=5]', 1),
                        ('minecraft:furnace', 1), ('hbmsntm:fluid_identifier_multi', 2), (ANVIL, 1),
                        ('minecraft:water_bucket', 3), ('minecraft:coal', 1), ('minecraft:oak_planks', 3)])
    build_table(ctx, x + 8, z + 8)
    lines, ok = [], True
    for out, made, pattern, key in [
            ('hbmsntm:gear_large', 1, ['III', 'ICI', 'III'], dict(I='hbmsntm:plate_iron', C='hbmsntm:ingot_copper')),
            ('hbmsntm:machine_condenser', 1, ['SIS', 'ICI', 'SIS'], dict(S='hbmsntm:ingot_steel', I='hbmsntm:plate_iron', C='hbmsntm:plate_cast')),
            ('hbmsntm:barrel_steel', 1, ['IPI', 'I I', 'IPI'], dict(I='hbmsntm:plate_steel', P='hbmsntm:ingot_steel')),
            ('hbmsntm:barrel_steel', 1, ['IPI', 'I I', 'IPI'], dict(I='hbmsntm:plate_steel', P='hbmsntm:ingot_steel'))]:
        good, line = craft(ctx, out, made, pattern, key)
        ok = ok and good
        lines.append(line)
    ctx.step('close')
    anvil, stand = build_anvil(ctx, x - 8, z + 8)
    recipes = anvil_recipes(ctx)
    fb_ok, fb_line = anvil_build(ctx, anvil, stand, recipes, 'hbmsntm:heater_firebox', 'hbmsntm:ingot_copper')
    bo_ok, bo_line = anvil_build(ctx, anvil, stand, recipes, 'hbmsntm:heat_boiler', 'hbmsntm:plate_copper')
    se_ok, se_line = anvil_build(ctx, anvil, stand, recipes, 'hbmsntm:machine_steam_engine', 'hbmsntm:reinforced_stone')
    ctx.check('heat-boiler.craft', fb_ok and bo_ok, '; '.join([fb_line, bo_line]))
    ctx.check('steam-power.craft', ok and se_ok and count(ctx, 'hbmsntm:barrel_steel') == 2, '; '.join(lines + [se_line]))
    if not (ok and fb_ok and bo_ok and se_ok):
        raise RuntimeError('parts missing')
    # identifiers: both set to water in their own screen (water is the fourth fluid, FluidScreen / Fluids.java:421-425)
    ctx.step('view', pos=[x + 0.5, Y, z + 12.5], pitch=-90.0, yaw=0.0, fly=False, hide_gui=False)
    set_identifier(ctx, 3)
    ident = [v for v in inventory(ctx).values() if v[0] == 'hbmsntm:fluid_identifier_multi']
    if not ident or 'Fluid1=%d' % WATER not in json.dumps(ident[0][2] or '').replace('\\"', '').replace('"', '').replace(':', '=').replace(' ', ''):
        raise RuntimeError('identifier not set to water: %s' % ident)
    firebox = build_firebox(ctx, x, z)                                     # core (x, Y, z - 1)
    boiler = stack_on_firebox(ctx, 'heat_boiler', x, z)                     # core (x, Y + 1, z - 1), side ports at x - 2 / x + 2
    # steam engine facing north (placed looking south) with its port side east: core (x - 3, Y, z); its upper proxy
    # (x - 2, Y + 1, z - 1) is the boiler's west port, its connection (x - 1, Y + 1, z + 1) takes the condenser
    place(ctx, 'hbmsntm:machine_steam_engine', (x - 3, Y - 1, z - 1), 'up', [x - 2.5, Y, z - 4.5])
    engine, eprops = find_core(ctx, 'hbmsntm:machine_steam_engine', (x - 5, Y, z - 3), (x - 1, Y + 1, z + 6))
    if engine != (x - 3, Y, z) or eprops.get('facing') != 'north':
        raise RuntimeError('steam engine core %s facing %s, expected %s facing north' % (engine, eprops.get('facing'), (x - 3, Y, z)))
    place(ctx, 'hbmsntm:machine_condenser', (x - 1, Y + 1, z), 'south', [x - 0.5, Y, z + 3.5], crouch=True)
    condenser = (x - 1, Y + 1, z + 1)
    place(ctx, 'hbmsntm:barrel_steel', (x, Y + 1, z), 'south', [x + 0.5, Y, z + 3.5], crouch=True)
    sink = (x, Y + 1, z + 1)
    place(ctx, 'hbmsntm:barrel_steel', (x + 1, Y + 1, z - 1), 'east', [x + 4.5, Y, z - 0.5], crouch=True)
    source = (x + 2, Y + 1, z - 1)
    for p, b in ((condenser, 'machine_condenser'), (sink, 'barrel'), (source, 'barrel')):
        if _lib.block_data(ctx, p).get('id') != 'hbmsntm:' + b:
            raise RuntimeError('%s not at %s' % (b, p))
    rd = configure_barrel(ctx, source, 'east', [x + 4.5, Y, z - 0.5], 3, 2)
    sd = configure_barrel(ctx, sink, 'south', [x + 0.5, Y, z + 3.5], 0, 0)
    if rd['tank_type'] != WATER or rd['mode'] != 2 or sd['tank_type'] != WATER or sd['mode'] != 0:
        raise RuntimeError('barrels: source type %s mode %s fill %s, sink type %s mode %s' % (rd['tank_type'], rd['mode'], rd['tank'], sd['tank_type'], sd['mode']))
    # coal through the firebox's north-east corner block (east face), clear of the source barrel
    fuel_firebox(ctx, firebox, (x + 1, Y, z - 2), 'east', [x + 3.5, Y, z - 2.5], 1)

    def state():
        f, b, e, c = (_lib.block_data(ctx, p) for p in (firebox, boiler, engine, condenser))
        r, s = _lib.block_data(ctx, source), _lib.block_data(ctx, sink)
        return dict(f=f, b=b, e=e, c=c, r=r, s=s)

    st = state()
    w0 = st['r']['tank'] + st['b']['input']
    if w0 != 3000 or st['b']['heat'] != 0 or st['f']['heatEnergy'] != 0:
        raise RuntimeError('start: water %d (want 3000), boiler heat %d, firebox heat %d' % (w0, st['b']['heat'], st['f']['heatEnergy']))

    def accounts(st):
        f, b, e, c, r, s = st['f'], st['b'], st['e'], st['c'], st['r'], st['s']
        used = w0 - r['tank'] - b['input']
        fired = (2000 - f['burnTime'] + 1) if f.get('maxBurnTime') == 2000 else None   # the load tick adds heat too
        heat_side = (200 * fired if fired is not None else None, f['heatEnergy'] + b['heat'] + 200 * used)
        steam_side = (100 * used, b['output'] + e['s'] + 100 * (e['w'] + c['water'] + c['steam'] + s['tank']))
        return used, fired, heat_side, steam_side

    r1 = sprint(ctx, 1499, 'B-steam-1')
    st = state()
    used, fired, heat_side, steam_side = accounts(st)
    ev = shot(ctx, 'B-steam-line', [x + 6.5, Y + 6, z + 7.5], [x - 1, Y + 1, z])
    ctx.check('heat-boiler.line', fired == r1['advanced'] and heat_side[0] == heat_side[1] and used > 1000,
              'after %d ticks: firebox burnt %s ticks (burnTime %d), 200 x %s = %s vs firebox heat %d + boiler heat %d + 200 x water used %d = %d; %.0f ticks/s'
              % (r1['advanced'], fired, st['f']['burnTime'], fired, heat_side[0], st['f']['heatEnergy'], st['b']['heat'], used, heat_side[1],
                 r1['ticks_per_s'] or 0), [ev])
    mid_steam = steam_side
    eb = st['e']['powerBuffer']
    ctx.check('steam-power.power', eb > 0 and eb % 170 == 0,
              'engine buffer %d HE this tick (170 per op), acceleration %s, engine steam %d mB, spent %d mB' % (eb, st['e'].get('acceleration'), st['e']['s'], st['e']['w']))
    r2 = sprint(ctx, 1500, 'B-steam-2')
    st = state()
    used2, _, _, steam_side = accounts(st)
    ctx.check('steam-power.line', mid_steam[0] == mid_steam[1] and steam_side[0] == steam_side[1] and st['s']['tank'] >= used2 - 21 and used2 > 1000,
              'after %d ticks: 100 x %d = %d vs %d; at rest after %d more: 100 x water used %d = %d vs boiler steam %d + engine steam %d + 100 x '
              '(engine spent %d + condenser spent %d + condenser water %d + barrel %d) = %d'
              % (r1['advanced'], used, mid_steam[0], mid_steam[1], r2['advanced'], used2, steam_side[0], st['b']['output'], st['e']['s'],
                 st['e']['w'], st['c']['water'], st['c']['steam'], st['s']['tank'], steam_side[1]))
    # the state at rest for the reload: the second barrel takes nothing in mode 3 (BarrelBlockEntity.java:259-269; BarrelScreen
    # mode button 151, 34, 18 x 18), then 3 oak planks (300 ticks each, 100 TU/t: HeaterFireboxBlockEntity.java:20,24-36,99-101;
    # ModuleBurnTime.java:40-44,78) boil about 450 mB of the boiler's water; the condenser (100 / 100, CondenserBaseBlockEntity.java:
    # 25-26,42-57) and the engine's spent steam (20) fill, the engine stops (MachineSteamEngineBlockEntity.java:83-96) and its
    # steam tank (2,000) and the boiler hold the rest. 2,000 ticks: 900 burning, then the residual heat decays (firebox :123,
    # boiler AbstractBoilerBlockEntity.java:207) and the engine's acceleration falls 0.1 a tick from 40 to 0.
    sink_before = st['s']['tank']
    open_gui(ctx, sink, 'south', [x + 0.5, Y, z + 3.5], 'Barrel')
    left, top, _ = gui_origin(ctx)
    for _ in range(3):
        ctx.step('click', at=[left + 160, top + 43], after=4)
    ctx.step('close')
    if _lib.block_data(ctx, sink).get('mode') != 3:
        raise RuntimeError('second barrel mode %s after 3 clicks (want 3)' % _lib.block_data(ctx, sink).get('mode'))
    fuel_firebox(ctx, firebox, (x + 1, Y, z - 2), 'east', [x + 3.5, Y, z - 2.5], 3, item='minecraft:oak_planks')
    r3 = sprint(ctx, 2000, 'B-rest')
    st = state()
    used3, _, _, steam_side = accounts(st)
    f, b, e, c, s = st['f'], st['b'], st['e'], st['c'], st['s']
    rest_ok = (e['s'] == 2000 and e['w'] == 20 and e.get('acceleration') == 0.0 and c['water'] == 100 and c['steam'] == 100
               and s['mode'] == 3 and s['tank'] == sink_before and steam_side[0] == steam_side[1] and b['output'] > 0 and b['input'] > 0
               and b['heat'] == 0 and f['heatEnergy'] == 0 and f['burnTime'] == 0 and f.get('maxBurnTime') == 300 and slot_count(f, 0) == 0
               and not b.get('hasExploded'))
    rest = ('at rest after %d more ticks (3 planks, second barrel mode %s): engine s %d (want 2000) w %d (want 20) acceleration %s (want 0); '
            'condenser water %d spent %d (want 100 / 100); barrel %d (before %d); boiler water %d steam %d heat %d; firebox heat %d burnTime %d '
            'maxBurnTime %s (want 300); 100 x water used %d = %d vs %d'
            % (r3['advanced'], s['mode'], e['s'], e['w'], e.get('acceleration'), c['water'], c['steam'], s['tank'], sink_before, b['input'],
               b['output'], b['heat'], f['heatEnergy'], f['burnTime'], f.get('maxBurnTime'), used3, steam_side[0], steam_side[1]))
    saved['B'] = dict(boiler=(boiler, {k: st['b'].get(k) for k in ('heat', 'input', 'output', 'hasExploded')}),
                      engine=(engine, {k: st['e'].get(k) for k in ('s', 'w', 'acceleration')}),
                      condenser=(condenser, {k: st['c'].get(k) for k in ('water', 'steam')}),
                      source=(source, {k: st['r'].get(k) for k in ('tank', 'tank_type', 'mode')}),
                      sink=(sink, {k: st['s'].get(k) for k in ('tank', 'tank_type', 'mode')}),
                      firebox=(firebox, {k: st['f'].get(k) for k in ('heatEnergy', 'burnTime', 'maxBurnTime')}),
                      rest=(rest_ok, rest))


def section_f(ctx, saved):
    x, z = SECTION_X['F'], Z0
    _lib.go_near(ctx, x, Y, z)
    # 预写: the identifier's fluid (custom data Fluid1 = coal tar oil, FluidIDMultiItem.java:94-104) - see the module notes
    give(ctx, [('hbmsntm:tank_steel', 4), ('hbmsntm:pipe_steel', 3), ('hbmsntm:ingot_titanium', 12), ('hbmsntm:ingot_copper', 16),
               ('hbmsntm:plate_steel', 8), ('minecraft:furnace', 1), ('hbmsntm:furnace_combination', 1), ('minecraft:cobblestone', 1), (ANVIL, 1),
               ('hbmsntm:fluid_identifier_multi[minecraft:custom_data={Fluid1:%d},hbmsntm:meta=%d]' % (COALCREOSOTE, COALCREOSOTE), 1),
               ('minecraft:coal', 5)])
    anvil, stand = build_anvil(ctx, x - 8, z + 8)
    recipes = anvil_recipes(ctx)
    ob_ok, ob_line = anvil_build(ctx, anvil, stand, recipes, 'hbmsntm:heater_oilburner', 'hbmsntm:ingot_copper')
    fb_ok, fb_line = anvil_build(ctx, anvil, stand, recipes, 'hbmsntm:heater_firebox', 'hbmsntm:ingot_copper')
    ctx.check('fluid-burner.craft', ob_ok and fb_ok, '; '.join([ob_line, fb_line]))
    if not (ob_ok and fb_ok):
        raise RuntimeError('parts missing')
    firebox = build_firebox(ctx, x, z)
    oven = stack_on_firebox(ctx, 'furnace_combination', x, z)              # core (x, Y + 1, z - 1)
    # the burner floats beside the oven: its west fluid proxy (x + 2, Y + 1, z - 1) is one of the oven's connections
    place(ctx, 'minecraft:cobblestone', (x + 3, Y - 1, z), 'up', [x + 3.5, Y, z + 3.5])
    place(ctx, 'hbmsntm:heater_oilburner', (x + 3, Y, z), 'up', [x + 3.5, Y, z + 3.5])
    burner, _ = find_core(ctx, 'hbmsntm:heater_oilburner', (x + 1, Y + 1, z - 3), (x + 5, Y + 2, z + 1))
    if burner != (x + 3, Y + 1, z - 1):
        raise RuntimeError('fluid burner core at %s, expected %s' % (burner, (x + 3, Y + 1, z - 1)))
    # firebox: 1 coal (right click puts one of the 5); oven: the other 4 into its input (both by hand, through the south faces)
    fuel_firebox(ctx, firebox, (x, Y, z), 'south', [x + 0.5, Y, z + 2.5], 1, one=True)
    open_gui(ctx, (x, Y + 1, z), 'south', [x + 0.5, Y, z + 2.5], 'Combination')
    put(ctx, 4, 'minecraft:coal', 0)
    ctx.step('close')
    od = _lib.block_data(ctx, oven)
    if slot_count(od, 0, 'minecraft:coal') != 4:
        raise RuntimeError('oven input %s' % slot_item(od, 0))
    # burner: the identifier into slot 2, switched on (HeaterOilburnerScreen: toggle 80, 54, 16 x 14); burn setting stays 1
    open_gui(ctx, (x + 3, Y + 1, z), 'south', [x + 3.5, Y, z + 2.5], 'Oilburner')
    put(ctx, 4, 'hbmsntm:fluid_identifier_multi', 2)
    left, top, _ = gui_origin(ctx)
    ctx.step('click', at=[left + 88, top + 61], after=4)
    ctx.step('close')
    ctx.server('tick step 1')
    ctx.step('wait', ticks=5)
    bd = _lib.block_data(ctx, burner)
    if not bd.get('isOn') or bd.get('tank_type') != COALCREOSOTE or bd.get('setting') != 1:
        raise RuntimeError('burner isOn %s type %s setting %s' % (bd.get('isOn'), bd.get('tank_type'), bd.get('setting')))

    def books():
        b, o = _lib.block_data(ctx, burner), _lib.block_data(ctx, oven)
        coke = slot_count(o, 1, 'hbmsntm:coke_coal')
        burnt = 100 * coke - o['tank'] - b['tank']
        return b, o, coke, burnt

    r1 = sprint(ctx, 600, 'F-oven-1')
    b, o, coke, burnt = books()
    mid_ok = b['heatEnergy'] == 250 * burnt
    mid = 'after %d ticks: coke %d, oven tank %d, burner tank %d, burnt %d mB, heat %d (want %d)' % (
        r1['advanced'], coke, o['tank'], b['tank'], burnt, b['heatEnergy'], 250 * burnt)

    def done(c):
        bb = _lib.block_data(c, burner)
        return bb['tank'] == 0 and bb['heatEnergy'] >= 100000
    r2 = sprint(ctx, 3000, 'F-oven-2', until=done)
    b, o, coke, burnt = books()
    ev = shot(ctx, 'F-fluid-burner', [x + 1.5, Y + 4, z + 6.5], [x + 2, Y + 1, z - 1])
    ctx.check('fluid-burner.line', mid_ok and coke == 4 and o['tank'] == 0 and b['tank'] == 0 and b['heatEnergy'] == 100000
              and slot_count(o, 0) == 0,
              '%s; after %d more: coke %d (want 4), oven input %d, oven tank %d, burner tank %d, heat %d (want 100000); %.0f ticks/s'
              % (mid, r2['advanced'], coke, slot_count(o, 0), o['tank'], b['tank'], b['heatEnergy'], r2['ticks_per_s'] or 0), [ev])
    saved['F'] = (burner, {k: b.get(k) for k in ('heatEnergy', 'tank', 'tank_type', 'isOn', 'setting')}, oven, coke)


ROTARY_KEYS = ('outType', 'outAmount', 'burn', 'maxBurn', 'heat', 'prog', 't2')


def section_r(ctx, saved):
    x, z = SECTION_X['R'], Z0
    _lib.go_near(ctx, x, Y, z)
    give(ctx, COMMON + [('hbmsntm:plate_steel', 14), ('hbmsntm:ingot_steel', 6), ('hbmsntm:ingot_copper', 8), ('hbmsntm:plate_copper', 24),
                        ('hbmsntm:plate_polymer', 8), ('hbmsntm:ingot_firebrick', 16), ('minecraft:stone_bricks', 8),
                        ('minecraft:iron_ingot', 5), ('minecraft:furnace', 1), ('hbmsntm:fluid_identifier_multi', 1), (ANVIL, 1),
                        ('minecraft:water_bucket', 2), ('minecraft:coal', 3), ('minecraft:cobblestone', 1)])
    build_table(ctx, x + 8, z + 8)
    ba_ok, ba_line = craft(ctx, 'hbmsntm:barrel_steel', 1, ['IPI', 'I I', 'IPI'], dict(I='hbmsntm:plate_steel', P='hbmsntm:ingot_steel'))
    ctx.step('close')
    anvil, stand = build_anvil(ctx, x - 8, z + 8)
    recipes = anvil_recipes(ctx)
    fb_ok, fb_line = anvil_build(ctx, anvil, stand, recipes, 'hbmsntm:heater_firebox', 'hbmsntm:ingot_copper')
    bo_ok, bo_line = anvil_build(ctx, anvil, stand, recipes, 'hbmsntm:heat_boiler', 'hbmsntm:plate_copper')
    rf_ok, rf_line = anvil_build(ctx, anvil, stand, recipes, 'hbmsntm:machine_rotary_furnace', 'hbmsntm:ingot_firebrick')
    left_over = dict(firebrick=count(ctx, 'hbmsntm:ingot_firebrick'), stone_bricks=count(ctx, 'minecraft:stone_bricks'),
                     iron=count(ctx, 'minecraft:iron_ingot'), plate_copper=count(ctx, 'hbmsntm:plate_copper'))
    ctx.check('rotary-furnace.craft', rf_ok and left_over == dict(firebrick=0, stone_bricks=0, iron=1, plate_copper=0),
              '%s; left: %s (want 0 firebricks, 0 stone bricks, 1 iron ingot for the recipe, 0 copper plates); parts: %s'
              % (rf_line, left_over, '; '.join([ba_line, fb_line, bo_line])))
    if not (ba_ok and fb_ok and bo_ok and rf_ok):
        raise RuntimeError('parts missing: %s' % '; '.join([ba_line, fb_line, bo_line, rf_line]))
    # the identifier set to water in its own screen (water is the fourth fluid, FluidScreen / Fluids.java:421-425)
    ctx.step('view', pos=[x + 0.5, Y, z + 12.5], pitch=-90.0, yaw=0.0, fly=False, hide_gui=False)
    set_identifier(ctx, 3)
    ident = [v for v in inventory(ctx).values() if v[0] == 'hbmsntm:fluid_identifier_multi']
    if not ident or 'Fluid1=%d' % WATER not in json.dumps(ident[0][2] or '').replace('\\"', '').replace('"', '').replace(':', '=').replace(' ', ''):
        raise RuntimeError('identifier not set to water: %s' % ident)
    firebox = build_firebox(ctx, x, z)                                     # core (x, Y, z - 1)
    boiler = stack_on_firebox(ctx, 'heat_boiler', x, z)                     # core (x, Y + 1, z - 1), side ports (x - 2 / x + 2, Y + 1, z - 1)
    # rotary furnace placed by a player looking west, so it faces east (DummyableBlock.java:71-73) with its core one block
    # behind the placed block (offset 1, :191-207): core (x + 3, Y + 1, z - 2), 3 along x by 5 across z, its back row at
    # x + 2. Its steam inlets are the back blocks at across +1 and +2 to the south (MachineRotaryFurnaceBlockEntity.java:90-105:
    # neighbours (x + 1, Y + 1, z - 1) and (x + 1, Y + 1, z), both boiler blocks), so the boiler's east port (x + 2, Y + 1, z - 1)
    # is the first of them. It stands on a cobblestone so that its back row is at the boiler's port height.
    place(ctx, 'minecraft:cobblestone', (x + 4, Y - 1, z - 2), 'up', [x + 7.5, Y, z - 1.5])
    place(ctx, 'hbmsntm:machine_rotary_furnace', (x + 4, Y, z - 2), 'up', [x + 7.5, Y, z - 1.5])
    furnace, fprops = find_core(ctx, 'hbmsntm:machine_rotary_furnace', (x + 1, Y + 1, z - 5), (x + 6, Y + 2, z + 1))
    if furnace != (x + 3, Y + 1, z - 2) or fprops.get('facing') != 'east':
        raise RuntimeError('rotary furnace core %s facing %s, expected %s facing east' % (furnace, fprops.get('facing'), (x + 3, Y + 1, z - 2)))
    # the water barrel on the boiler's west port, set to water and send mode, 2 buckets (2,000 mB: about 2,000 ticks of boiling,
    # as long as the coal burns, so the boiler still boils while the furnace runs)
    place(ctx, 'hbmsntm:barrel_steel', (x - 1, Y + 1, z - 1), 'west', [x - 3.5, Y, z - 0.5], crouch=True)
    source = (x - 2, Y + 1, z - 1)
    if _lib.block_data(ctx, source).get('id') != 'hbmsntm:barrel':
        raise RuntimeError('barrel not at %s' % (source,))
    rd = configure_barrel(ctx, source, 'west', [x - 3.5, Y, z - 0.5], 2, 2)
    if rd['tank_type'] != WATER or rd['mode'] != 2:
        raise RuntimeError('barrel type %s mode %s fill %s' % (rd['tank_type'], rd['mode'], rd['tank']))
    fuel_firebox(ctx, firebox, (x, Y, z), 'south', [x + 0.5, Y, z + 2.5], 1, one=True)

    def state():
        f, b, r = (_lib.block_data(ctx, p) for p in (furnace, boiler, source))
        return dict(f=f, b=b, r=r)

    st = state()
    if st['f'].get('t1') != 0 or st['f'].get('burn', 0) != 0:
        raise RuntimeError('furnace before the steam: steam %s, burn %s' % (st['f'].get('t1'), st['f'].get('burn')))

    # the boiler fills the idle furnace's steam tank (no recipe: no fuel is taken and no steam used, :145-158,202-205)
    def full(c):
        return _lib.block_data(c, furnace).get('t1', 0) >= 12000
    # polled often, so the fill stops soon after the tank is full and the coal and the water last through the furnace's run
    fill = ctx.sprint(1500, until=full, label='R-steam-fill', poll_s=0.2, timeout_s=900)
    st = state()
    if st['f'].get('t1') != 12000:
        ctx.check('rotary-furnace.line', False, 'after %d ticks of the boiler the furnace holds %s mB steam (want 12,000), boiler steam %s, '
                  'boiler water %s, barrel %s, boiler heat %s' % (fill['advanced'], st['f'].get('t1'), st['b']['output'], st['b']['input'],
                                                                  st['r']['tank'], st['b']['heat']))
        return
    # the inputs and the fuel by hand through the furnace screen (menu: 5 own slots, then the player inventory)
    open_gui(ctx, (x + 4, Y + 1, z - 2), 'east', [x + 6.5, Y, z - 1.5], 'RotaryFurnace')
    put(ctx, 5, 'minecraft:iron_ingot', 0, one=True)
    put(ctx, 5, 'minecraft:coal', 1, one=True)
    put(ctx, 5, 'minecraft:coal', 4, one=True)
    ctx.step('close')
    s0 = state()
    f0 = s0['f']
    if not (slot_count(f0, 0, 'minecraft:iron_ingot') == 1 and slot_count(f0, 1, 'minecraft:coal') == 1 and slot_count(f0, 4, 'minecraft:coal') == 1
            and f0.get('burn', 0) == 0 and f0.get('t2', 0) == 0 and 'outType' not in f0):
        raise RuntimeError('furnace after loading: slots %s, burn %s, spent %s' % (f0.get('Items'), f0.get('burn'), f0.get('t2')))
    run = sprint(ctx, 300, 'R-furnace')
    s1 = state()
    f1, b0, b1, r0, r1 = s1['f'], s0['b'], s1['b'], s0['r'], s1['r']
    p = 800 - f1.get('burn', 0)
    water = (r0['tank'] + b0['input']) - (r1['tank'] + b1['input'])
    steam_gain = (b1['output'] - b0['output']) + (f1['t1'] - f0['t1'])
    empty = all(slot_item(f1, s) is None for s in (0, 1, 4))
    ev = shot(ctx, 'R-rotary-furnace', [x + 9.5, Y + 6, z + 6.5], [x + 1, Y + 2, z - 2])
    ctx.check('rotary-furnace.line', p in (100, 101) and f1.get('maxBurn') == 800 and f1.get('heat') == 1.0 and f1.get('outType') == MAT_STEEL
              and f1.get('outAmount') == INGOT_QUANTA and f1.get('t2') == p and empty and water > 0 and 100 * water == steam_gain + 100 * p,
              'steam filled in %d ticks; then %d ticks: processing ticks P = 800 - burn %s = %d (want 100 or 101), maxBurn %s, heat %s; output type %s '
              'amount %s (want %d, %d); spent steam %s (want P); inputs and fuel empty %s; water used %d -> 100 x %d = %d vs boiler steam %d -> %d, '
              'furnace steam %d -> %d, + 100 x P = %d; %.0f ticks/s'
              % (fill['advanced'], run['advanced'], f1.get('burn'), p, f1.get('maxBurn'), f1.get('heat'), f1.get('outType'), f1.get('outAmount'),
                 MAT_STEEL, INGOT_QUANTA, f1.get('t2'), empty, water, water, 100 * water, b0['output'], b1['output'], f0['t1'], f1['t1'],
                 steam_gain + 100 * p, run['ticks_per_s'] or 0), [ev])
    saved['R'] = dict(furnace=(furnace, {k: f1.get(k) for k in ROTARY_KEYS}),
                      source=(source, {k: r1.get(k) for k in ('tank', 'tank_type', 'mode')}))


# ---------------------------------------------------------------- run

SECTIONS = [
    ('W', section_w, ['wood-burner.craft', 'wood-burner.burn', 'wood-burner.full', 'wood-burner.reload']),
    ('C', section_c, ['red-cable.craft', 'battery-storage.craft', 'red-cable.line', 'battery-storage.charge', 'battery-storage.reload']),
    ('S', section_s, ['stirling-power.craft', 'stirling-power.steady', 'stirling-power.reload']),
    ('B', section_b, ['heat-boiler.craft', 'steam-power.craft', 'heat-boiler.line', 'steam-power.power', 'steam-power.line',
                      'heat-boiler.reload', 'steam-power.reload']),
    ('F', section_f, ['fluid-burner.craft', 'fluid-burner.line', 'fluid-burner.reload']),
    ('R', section_r, ['rotary-furnace.craft', 'rotary-furnace.line', 'rotary-furnace.reload']),
]


def undecided(ctx, ids, reason):
    for eid in ids:
        if eid not in ctx.verdicts:
            ctx.not_run(eid, reason)


def run(ctx):
    _lib.setup_world(ctx, freeze=True)
    cmd(ctx, 'gamemode survival')
    saved = {}
    for name, fn, ids in SECTIONS:
        try:
            fn(ctx, saved)
        except Exception as e:
            for k in ('key.keyboard.left.shift',):
                ctx.step('key', key=k, action='release', after=0, allow_fail=True)
            ctx.step('close', allow_fail=True)
            ctx.step('mod', shift=False, allow_fail=True)
            undecided(ctx, ids, 'section %s stopped: %s' % (name, str(e)[:300]))
            saved.pop(name, None)
    # leave, open the same world again, freeze at once and read the same values
    before = ctx.server()['game_time']
    ctx.step('leave')
    ctx.step('openworld', world=ctx.run.world['name'])
    settle(ctx)
    after = ctx.server()['game_time']
    gap = 'game time %d before leaving, %d after opening and freezing' % (before, after)

    def reread(name, ids, fn):
        if name not in saved:
            undecided(ctx, ids, 'section %s did not finish, nothing to compare' % name)
            return
        try:
            fn(saved[name])
        except Exception as e:
            undecided(ctx, ids, 'reading after reopening failed: %s' % str(e)[:300])

    def w(s):
        core, vals, logs = s
        _lib.go_near(ctx, core[0], Y, core[2])
        d = _lib.block_data(ctx, core)
        now = {k: d.get(k) for k in vals}
        ctx.check('wood-burner.reload', now == vals and slot_count(d, 0, 'minecraft:oak_log') == logs,
                  '%s: before %s (logs %d), after %s (logs %d)' % (gap, vals, logs, now, slot_count(d, 0, 'minecraft:oak_log')))

    def c(s):
        socket, charge, settings = s
        _lib.go_near(ctx, socket[0], Y, socket[2])
        now = charge_of(ctx, socket)
        sd = _lib.block_data(ctx, socket)
        snow = {k: sd.get(k) for k in settings}
        ctx.check('battery-storage.reload', settings == dict(RedLow=3, RedHigh=2, Priority=2) and now == charge and snow == settings,
                  '%s: Charge before %d, after %s; settings set in the screen %s (want RedLow 3, RedHigh 2, Priority 2), after %s'
                  % (gap, charge, now, settings, snow))

    def s_(s):
        socket, charge, firebox, fvals, stirling, svals, note = s
        _lib.go_near(ctx, socket[0], Y, socket[2])
        now = charge_of(ctx, socket)
        fd = _lib.block_data(ctx, firebox)
        fnow = dict(heatEnergy=fd['heatEnergy'], burnTime=fd['burnTime'], maxBurnTime=fd.get('maxBurnTime'), coal=slot_count(fd, 0))
        snow = dict(hasCog=_lib.block_data(ctx, stirling).get('hasCog'))
        # non-default per block: the battery's charge, the cog, the firebox's max burn time (1,600 x 1.25, HeaterFireboxBlockEntity.java:26,99-100)
        ctx.check('stirling-power.reload', now == charge and fnow == fvals and snow == svals and fvals['heatEnergy'] == 0
                  and charge > 0 and svals['hasCog'] and fvals['maxBurnTime'] == 2000,
                  '%s; %s: battery %d -> %s, firebox %s -> %s, Stirling %s -> %s' % (note, gap, charge, now, fvals, fnow, svals, snow))

    def b(s):
        rest_ok, rest = s['rest']
        blocks = {k: v for k, v in s.items() if k != 'rest'}
        _lib.go_near(ctx, s['boiler'][0][0], Y, s['boiler'][0][2])
        diff = {}
        for part, (pos, vals) in blocks.items():
            d = _lib.block_data(ctx, pos)
            now = {k: d.get(k) for k in vals}
            if now != vals:
                diff[part] = (vals, now)
        v = {k: vals for k, (_, vals) in blocks.items()}
        # equal AND non-default per block: boiler water and steam, firebox max burn time, barrel type and send mode (heat-boiler);
        # engine steam and spent steam, both condenser tanks, the barrel's water (steam-power)
        boiler_nd = (v['boiler']['input'] > 0 and v['boiler']['output'] > 0 and v['firebox']['maxBurnTime'] == 300
                     and v['source']['tank_type'] == WATER and v['source']['mode'] == 2)
        steam_nd = (v['engine']['s'] > 0 and v['engine']['w'] > 0 and v['condenser']['water'] > 0 and v['condenser']['steam'] > 0
                    and v['sink']['tank'] > 0)
        boiler_ok = rest_ok and boiler_nd and not any(k in diff for k in ('boiler', 'source', 'firebox'))
        steam_ok = rest_ok and steam_nd and not any(k in diff for k in ('engine', 'condenser', 'sink'))
        detail = '%s; %s; boiler %s, firebox %s, barrels %s / %s; differences: %s' % (
            rest, gap, v['boiler'], v['firebox'], v['source'], v['sink'], diff or 'none')
        ctx.check('heat-boiler.reload', boiler_ok, detail)
        ctx.check('steam-power.reload', steam_ok, '%s; %s; engine %s, condenser %s, barrel %s; differences: %s'
                  % (rest, gap, v['engine'], v['condenser'], v['sink'], diff or 'none'))

    def f(s):
        burner, vals, oven, coke = s
        _lib.go_near(ctx, burner[0], Y, burner[2])
        d = _lib.block_data(ctx, burner)
        now = {k: d.get(k) for k in vals}
        cnow = slot_count(_lib.block_data(ctx, oven), 1, 'hbmsntm:coke_coal')
        ctx.check('fluid-burner.reload', now == vals and cnow == coke, '%s: burner %s -> %s, coke %d -> %d' % (gap, vals, now, coke, cnow))

    reread('W', ['wood-burner.reload'], w)
    reread('C', ['battery-storage.reload'], c)
    reread('S', ['stirling-power.reload'], s_)
    reread('B', ['heat-boiler.reload', 'steam-power.reload'], b)
    def r(s):
        _lib.go_near(ctx, s['furnace'][0][0], Y, s['furnace'][0][2])
        diff = {}
        for part, (pos, vals) in s.items():
            d = _lib.block_data(ctx, pos)
            now = {k: d.get(k) for k in vals}
            if now != vals:
                diff[part] = (vals, now)
        fv = s['furnace'][1]
        ctx.check('rotary-furnace.reload', not diff and fv['outAmount'] == INGOT_QUANTA and fv['burn'] not in (None, 0),
                  '%s; furnace %s, barrel %s; differences: %s' % (gap, fv, s['source'][1], diff or 'none'))

    reread('F', ['fluid-burner.reload'], f)
    reread('R', ['rotary-furnace.reload'], r)
