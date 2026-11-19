"""Main line, stage 6 (base infrastructure): power over pylon and substation spans, power control, a network separator, and
a fluid line of barrels, ducts, valves, a counter valve and a long pipe between pipe anchors, played in survival.

The player gets the stage's start items by command (HANDOVER below is the stage-6 start list: everything obtainable before
this stage; GIVE takes from it, VANILLA and TOOLS list what is given besides, with the reason). Every block of the lines is
crafted here in the crafting table by real clicks, except the two substations and the large pylon, which are built on a
steel anvil placed by hand (the anvil screen paged by clicks on its right arrow to the recipe, the recipe's tooltip read,
the recipe selected and constructed), and the red cables and standard ducts between the parts (set as real blocks by
command). The parts are placed by hand, machines are loaded and set by real right-clicks and slot clicks, the separator's
limit by editing its text field (two backspaces: 1000 -> 10).

Power line (z = BZ - 4 unless noted): wood burner -> red cable -> pylon A ~25 m wire~ pylon B -> cable -> substation 1
~wire~ large pylon ~wire~ substation 2 -> cable -> power switch -> power gauge -> cable -> network separator (limit 10 HE/t)
-> cable -> battery socket with a redstone battery pack. Wire rule checks: pylon A -> pylon C 26 m away is refused (too far),
pylon B -> substation 1 is refused (different wire types).
Fluid line (z = FZ): steel barrel A (4 water buckets loaded through its slot, send mode) -> duct -> valve -> duct gauge ->
counter valve -> duct -> pipe anchor A1 ~10 m pipe~ anchor A2 -> duct -> steel barrel B (receive mode). Anchor A1 -> A3
11 m away is refused (too far). The whole run of pipes is typed water with one sneaking click of the fluid identifier.

Expected values are derived from the code (NEO file:line, the 1.7.10 original's file:line where NEO ports it); readings are
server data (`data get block`). After the line the world is left and opened again and the same readings are compared; the
lines are first brought to a state that holds still while the world is closed (switch off, separator drained, the burner
full and idle, the fluid moved), every reading non-default.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='power-transmission.mainline_stage6',
    feature='power-transmission',
    features=['power-transmission', 'power-control', 'fluid-pipelines', 'fluid-logistics', 'fluid-control', 'network-flow-control'],
    title='Main line stage 6: pylon and substation spans, power control and separator, a fluid line of barrels, valves and anchors',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

# The stage-6 start list: items obtainable before stage 6 (item, the stage it is first obtainable in); "block:" rows are
# world-generation blocks.
HANDOVER = [
    ('block:hbmsntm:ore_oil', 1), ('hbmsntm:arc_electrode_graphite', 2), ('hbmsntm:ball_fireclay', 2), ('hbmsntm:billet_silicon', 4),
    ('hbmsntm:cinnabar', 1), ('hbmsntm:circuit_analog_board', 4), ('hbmsntm:circuit_capacitor', 4), ('hbmsntm:circuit_integrated_board', 4),
    ('hbmsntm:circuit_microchip', 4), ('hbmsntm:circuit_printed_board', 4), ('hbmsntm:circuit_printed_silicon_wafer', 4),
    ('hbmsntm:circuit_vacuum_tube', 4), ('hbmsntm:coil_copper', 2), ('hbmsntm:coil_copper_ring', 2), ('hbmsntm:coil_tungsten', 1),
    ('hbmsntm:concrete_asbestos', 4), ('hbmsntm:concrete_smooth', 4), ('hbmsntm:conveyor_wand@0', 1), ('hbmsntm:conveyor_wand@1', 1),
    ('hbmsntm:conveyor_wand@2', 1), ('hbmsntm:conveyor_wand@3', 1), ('hbmsntm:crate_steel', 2), ('hbmsntm:drill_titanium', 4),
    ('hbmsntm:furnace_combination', 2), ('hbmsntm:heat_boiler', 3), ('hbmsntm:heater_firebox', 3), ('hbmsntm:ingot_aluminium', 1),
    ('hbmsntm:ingot_copper', 1), ('hbmsntm:ingot_desh', 5), ('hbmsntm:ingot_dura_steel', 2), ('hbmsntm:ingot_firebrick', 2),
    ('hbmsntm:ingot_lead', 1), ('hbmsntm:ingot_niobium', 4), ('hbmsntm:ingot_polymer', 5), ('hbmsntm:ingot_raw@41', 2),
    ('hbmsntm:ingot_red_copper', 2), ('hbmsntm:ingot_rubber', 5), ('hbmsntm:ingot_steel', 2), ('hbmsntm:ingot_titanium', 1),
    ('hbmsntm:ingot_tungsten', 1), ('hbmsntm:machine_arc_furnace', 4), ('hbmsntm:machine_arc_welder', 4),
    ('hbmsntm:machine_assembly_machine', 4), ('hbmsntm:machine_blast_furnace', 2), ('hbmsntm:machine_catalytic_cracker', 5),
    ('hbmsntm:machine_chemical_plant', 4), ('hbmsntm:machine_crucible', 2), ('hbmsntm:machine_crystallizer', 4),
    ('hbmsntm:machine_mixer', 4), ('hbmsntm:machine_press', 2), ('hbmsntm:machine_refinery', 5), ('hbmsntm:machine_shredder', 4),
    ('hbmsntm:machine_soldering_station', 4), ('hbmsntm:machine_well', 5), ('hbmsntm:mold_base', 2), ('hbmsntm:motor', 2),
    ('hbmsntm:ore_cobalt', 1), ('hbmsntm:ore_lead_deepslate', 1), ('hbmsntm:ore_titanium_deepslate', 1), ('hbmsntm:part_generic@0', 1),
    ('hbmsntm:pipe_copper', 1), ('hbmsntm:pipe_steel', 2), ('hbmsntm:plate_aluminium', 1), ('hbmsntm:plate_cast@0', 2),
    ('hbmsntm:plate_cast@11', 2), ('hbmsntm:plate_cast@12', 2), ('hbmsntm:plate_cast@5', 2), ('hbmsntm:plate_copper', 1),
    ('hbmsntm:plate_iron', 1), ('hbmsntm:plate_lead', 1), ('hbmsntm:plate_polymer', 1), ('hbmsntm:plate_steel', 2),
    ('hbmsntm:plate_titanium', 1), ('hbmsntm:powder_aluminium', 2), ('hbmsntm:powder_coal', 4), ('hbmsntm:powder_desh_mix', 4),
    ('hbmsntm:red_wire_coated', 3), ('hbmsntm:resource_limestone', 1), ('hbmsntm:shell_steel', 2), ('hbmsntm:shell_titanium', 1),
    ('hbmsntm:stamp_stone_flat', 2), ('hbmsntm:steel_grate', 2), ('hbmsntm:steel_scaffold', 2), ('hbmsntm:sulfur', 1),
    ('hbmsntm:tank_steel', 2), ('hbmsntm:transformer', 4), ('hbmsntm:wire_copper', 1), ('hbmsntm:wire_gold', 1), ('hbmsntm:wire_lead', 1),
    ('hbmsntm:wire_red_copper', 2), ('hbmsntm:wire_tungsten', 1),
]
# from the start list: exactly what the recipes below use
GIVE = [('hbmsntm:coil_copper', 19), ('hbmsntm:plate_polymer', 35), ('hbmsntm:plate_steel', 31), ('hbmsntm:ingot_steel', 23),
        ('hbmsntm:wire_red_copper', 4), ('hbmsntm:ingot_red_copper', 1), ('hbmsntm:circuit_integrated_board', 4), ('hbmsntm:transformer', 1),
        ('hbmsntm:plate_iron', 5), ('hbmsntm:plate_aluminium', 6), ('hbmsntm:circuit_microchip', 1), ('hbmsntm:pipe_steel', 4),
        ('hbmsntm:circuit_vacuum_tube', 1), ('hbmsntm:concrete_smooth', 10), ('hbmsntm:steel_scaffold', 8)]
# vanilla materials (always obtainable)
VANILLA = [('minecraft:oak_planks', 2), ('minecraft:cobblestone', 1), ('minecraft:lever', 2), ('minecraft:iron_ingot', 4),
           ('minecraft:furnace', 1), ('minecraft:redstone_block', 3), ('minecraft:redstone', 1), ('minecraft:blue_dye', 1),
           ('minecraft:oak_log', 1)]
BUCKETS = 4
# not on the start list but given as well: the steel anvil (tier 2), made in stage 2 by smithing an iron anvil with 10 steel
# ingots; the substations and the large pylon are construction recipes of tier 2 (AnvilRecipes.java:488-507; original
# AnvilRecipes.java:486-502)
ANVIL = 'hbmsntm:anvil[hbmsntm:meta=2]'   # NTMAnvilBlock.Variant.STEEL, tier 2 (NTMAnvilBlock.java:57-73)
TOOLS = [(ANVIL, 1)]
ANVIL_TIER = 2
ANVIL_PAGE = 10                            # AnvilMenuScreen.java:30
# placed from the south the anvil faces south and is 12 px high, 8 px deep (z 4..12): aim at the middle of that face
ANVIL_AIM = (0.0, -0.25, -0.25)            # NTMAnvilBlock.java:93,114-116,131-132
# (name, output, an input that picks the recipe, outputs per construction, the name the recipe's tooltip shows in zh_cn):
# AnvilRecipes.java:489-497 (2 any concrete, 8 steel scaffolds, 8 polymer plates, 4 copper coils -> 1 large pylon) and
# :499-507 (8 any concrete, 8 steel ingots, 12 polymer plates, 8 copper coils -> 2 substations); names zh_cn.json:550,585
CONSTRUCT = [('substations', 'hbmsntm:substation', 'hbmsntm:ingot_steel', 2, '变电站'),
             ('large pylon', 'hbmsntm:red_pylon_large', 'hbmsntm:steel_scaffold', 1, '大型输电塔')]

Y = -60
X0, Z0 = 3000, 3000
BX, BZ = X0, Z0                 # wood burner core (clicked from the south: facing south)
PA = (BX, Y, BZ - 4)            # pylon A
PB = (BX + 25, Y, BZ - 4)       # pylon B: 25 blocks east of A, both wire mounts 5.5 above the core
PC = (BX - 26, Y, BZ - 4)       # pylon C: 26 blocks west of A
SUB1 = (BX + 28, Y, BZ - 2)     # substation 1 core: its port (x - 1, z - 2) is two cells east of pylon B
LARGE = (BX + 40, Y, BZ - 2)    # large pylon core
SUB2 = (BX + 52, Y, BZ - 2)     # substation 2 core: its port (x + 1, z - 2) starts the run to the battery
P2 = (SUB2[0] + 1, Y, SUB2[2] - 2)
SWITCH = (P2[0] + 1, Y, P2[2])
GAUGE = (P2[0] + 2, Y, P2[2])
SEP_IN = (P2[0] + 3, Y, P2[2])
SEP = (P2[0] + 5, Y, P2[2])     # separator core, facing south: output side east (counter-clockwise), input side west
SEP_OUT = (P2[0] + 7, Y, P2[2])
BAT = (P2[0] + 8, Y, P2[2] - 1)  # battery socket core, facing south: port core + south
BAT_PORT = (BAT[0], Y, BAT[2] + 1)
CABLES = [(BX, Y, BZ - 2), (BX, Y, BZ - 3), (PB[0] + 1, Y, PB[2]), (PB[0] + 2, Y, PB[2]), P2, SEP_IN, SEP_OUT, BAT_PORT]

FX, FZ = X0, Z0 + 20
BAR_A = (FX, Y, FZ)
BAR_B = (FX + 18, Y, FZ)
VALVE = (FX + 2, Y, FZ)
FGAUGE = (FX + 3, Y, FZ)
COUNTER = (FX + 4, Y, FZ)
A1 = (FX + 6, Y, FZ)            # on the east face of the duct at FX + 5
A2 = (FX + 16, Y, FZ)           # on the west face of the duct at FX + 17: 10 blocks from A1
A3 = (FX + 6, Y, FZ + 11)       # on the north face of a stone block: 11 blocks from A1
DUCTS = [(FX + 1, Y, FZ), (FX + 5, Y, FZ), (FX + 17, Y, FZ)]
TABLE = (X0 - 8, Y, Z0 + 10)
ANVIL_POS = (X0 - 12, Y, Z0 + 10)
MID = [X0 + 30.5, Y, Z0 + 10.5]  # where the player waits during sprints (both lines in simulation distance)

WATER_ID = 1        # Fluids.java:250-251 (NONE is registered first, WATER second; registerSelf gives the registration index)
BURNER_GEN = 100    # MachineWoodBurnerBlockEntity.java:43,139-141; TileEntityMachineWoodBurner.java:118-120
BURNER_MAX = 100000  # MachineWoodBurnerBlockEntity.java:42,112; TileEntityMachineWoodBurner.java:40,143
LOG_TICKS = 300 * 4  # vanilla log burn time 300 x log time mod 4: MachineWoodBurnerBlockEntity.java:53-55,123,134, ModuleBurnTime.java:40-43,67; TileEntityMachineWoodBurner.java:49,110
LIMIT = 10          # 1000 (NetworkSeparatorBlockEntity.java:43) with two characters deleted
BUCKET_MB = 1000    # FluidContainerRegistry.java:37; original FluidContainerRegistry.java:33
BARREL_MAX = 16000  # NtmBlocks.java:427; original ModBlocks.java:1953

PT, PC_, FP, FL, FC, NF = ('power-transmission', 'power-control', 'fluid-pipelines', 'fluid-logistics', 'fluid-control', 'network-flow-control')

E = [
    (PT, 'start-items', 'record: what the player gets by command: the stage-6 start list items the recipes use, vanilla materials, '
                        'the steel anvil (a stage-2 product not on the list), and how many items of the start list there are',
     'stage-6 start list (in this file)'),
    (PT, 'craft', 'crafting table by real clicks: 2 copper coils + 2 planks + 2 polymer plates + 1 cobblestone -> 4 pylons; '
                  '8 steel plates + 1 steel ingot -> 1 cable drum',
     'NtmRecipeProvider.java:1709-1718,1761-1768; CraftingManager.java:246,540'),
    (PT, 'construct', 'steel anvil (tier 2) placed by hand, its screen paged by clicks to each recipe (the tooltip names it): '
                      '8 concrete + 8 steel ingots + 12 polymer plates + 8 copper coils -> 2 substations; '
                      '2 concrete + 8 steel scaffolds + 8 polymer plates + 4 copper coils -> 1 large pylon',
     'AnvilRecipes.java:488-507, AnvilMenuScreen.java:30,46-50,225-230, NTMAnvilBlock.java:57-73; AnvilRecipes.java:486-502 (original)'),
    (PT, 'span', 'cable drum on pylon A then pylon B 25 blocks away (both mounts 5.5 up, max wire 25, 25 >= 25): both record the '
                 'other; A then pylon C 26 away: refused, no record; B then substation 1: refused (single vs quad wire), no record',
     'PylonBaseBlockEntity.java:43-52, PylonBlockEntity.java:20-21, WiringItem.java:61-91; TileEntityPylonBase.java:30-49, TileEntityPylon.java:31-37'),
    (PT, 'quad-span', 'substation 1 -> large pylon -> substation 2: both wires made (quad, max min(20, 100) = 20; the computed '
                      'mount distances are below 20), each end records the other',
     'SubstationBlockEntity.java:22-48, PylonLargeBlockEntity.java:11-35; TileEntitySubstation.java:48, TileEntityPylonLarge.java:38'),
    (PT, 'line', 'the battery charges only over the two spans: after the switch-on window and the gauge, in the frozen world read after '
                 '4 s, battery charge + separator buffer + burner buffer = 100 HE x the ticks the log has burned (maxBurnTime - burnTime), '
                 'no loss on cables, wires or substations',
     'MachineWoodBurnerBlockEntity.java:97-99,139-141; PowerNetMK2.java:27-116; TileEntityMachineWoodBurner.java:110,118-120'),
    (PT, 'reload', 'after leaving and opening the world: the wire records of pylons A, B, C, both substations and the large pylon are the same',
     'PylonBaseBlockEntity.java:141-160; TileEntityPylonBase (NBT)'),
    (PT, 'after-reload', 'after opening the world again, switch on: the battery again gains 10 HE x the game ticks between two '
                         'readings around a 200-tick window',
     'NetworkSeparatorBlockEntity.java:80-151; BlockNetworkSeparator.java:149-222'),
    (PC_, 'craft', 'crafting table: 4 polymer plates + 4 red copper wires + 1 red copper ingot -> 16 sealed wires; lever + sealed wire '
                   '-> 1 power switch; sealed wire + steel ingot + integrated circuit -> 1 power gauge',
     'NtmRecipeProvider.java:1378-1386,1396-1402,1420-1425; CraftingManager.java:232,236,243'),
    (PC_, 'switch-off', 'the placed switch is off: over a 100-tick window with the burner on, the battery stays 0 and the burner gains '
                        '100 HE x the game ticks between its two readings (nothing draws)',
     'CableSwitchBlock.java:29, CableSwitchBlockEntity.java:16-28; TileEntityCableSwitch.java:18'),
    (PC_, 'switch-on', 'after a right-click on the switch the battery gains 10 HE x the game ticks between two readings around a '
                       '200-tick window (the separator\'s limit)',
     'CableSwitchBlock.java:48-53; CableSwitch.java:49-51'),
    (PC_, 'gauge', 'the power gauge on the input side, looked at from 1.6 blocks in the running world, shows 10HE/t and 200HE/s '
                   '(the burner loses 10 HE a tick to the separator; the synced 20-tick sum)',
     'CableGaugeBlockEntity.java:20-38, CableGaugeBlock.java:77-79, PowerNetMK2.java:113-116; BlockCableGauge.java:102-104,124-140, PowerNetMK2.java:109-122 (original)'),
    (PC_, 'reload', 'after leaving and opening the world: the switch is still off and the burner keeps power 100,000, isOn and its burn time',
     'CableSwitchBlock.java:62; MachineWoodBurnerBlockEntity.java:325-350'),
    (NF, 'craft', 'crafting table: 4 steel plates + 2 copper coils + 2 integrated circuits + 1 transformer -> 1 network separator',
     'NtmRecipeProvider.java:1508-1517; CraftingManager.java:239'),
    (NF, 'limit', 'two backspaces in the separator\'s limit field (1000 -> 10) and closing the screen set configuredLimit 10 on the server; '
                  'with the burner making 100 HE/t, the battery gains exactly 10 HE x the game ticks of a 200-tick window',
     'NetworkSeparatorScreen.java:33-37,70-78, NetworkSeparatorBlockEntity.java:80-151,161-166; GUIDiode.java:59-69, BlockNetworkSeparator.java:149-222,268-275'),
    (NF, 'reload', 'after leaving and opening the world: configuredLimit 10 and the drained buffer are the same',
     'NetworkSeparatorBlockEntity.java:170-185; BlockNetworkSeparator.java:229-239'),
    (FL, 'craft', 'crafting table: 4 steel plates + 2 aluminium plates -> 8 ducts; 6 steel plates + 2 steel ingots -> 1 steel barrel (twice)',
     'NtmRecipeProvider.java:95-110; CraftingManager.java:569,716'),
    (FL, 'barrel-load', 'identifier set to water in slot 0 (moves to slot 1), then 4 water buckets one by one into slot 2: barrel A holds '
                        '4,000 mB water of 16,000, 4 empty buckets in slot 3; two clicks on the mode button: mode 0 -> 2 (send)',
     'BarrelBlockEntity.java:38,66-73,259-263, FluidTank.java:141-161, FluidContainerRegistry.java:37, NtmBlocks.java:427; '
     'TileEntityBarrel.java:109-111, AuxButtonPacket.java:110, FluidContainerRegistry.java:33, ModBlocks.java:1953'),
    (FL, 'line', 'valve opened: within 40 ticks barrel B (receive) holds all 4,000 mB water and barrel A 0',
     'BarrelBlockEntity.java:84-116,267-279; TileEntityBarrel.java:234-239'),
    (FL, 'reload', 'after leaving and opening the world: both barrels keep fill, type and mode',
     'BarrelBlockEntity.java:324-335; TileEntityBarrel.java:211-219'),
    (FC, 'craft', 'crafting table: 4 steel ingots + 4 aluminium plates -> 8 paintable ducts; lever + duct -> valve; redstone + duct -> '
                  'fluid switch; microchip + fluid switch -> counter valve; duct + steel ingot + integrated circuit -> duct gauge',
     'NtmRecipeProvider.java:1426-1460; CraftingManager.java:572,574-577'),
    (FC, 'valve-closed', 'with the placed valve closed and the counter valve open, 40 ticks: barrel B 0, barrel A 4,000, counter 0',
     'FluidValveBlock.java:38, FluidValveBlockEntity.java:21-27; TileEntityFluidValve.java:11'),
    (FC, 'counter', 'after the valve is opened the counter valve has counted 4,000 mB',
     'FluidCounterValveBlockEntity.java:26-45; TileEntityFluidCounterValve.java:20-44'),
    (FC, 'reload', 'after leaving and opening the world: both valves open, counter 4,000',
     'FluidCounterValveBlockEntity.java:63-73; TileEntityFluidCounterValve.java:74-80'),
    (FP, 'craft', 'crafting table: 2 steel pipes + 1 steel ingot -> 2 pipe anchors (twice); 2 steel ingots + 2 iron ingots -> 1 wrench',
     'NtmRecipeProvider.java:1483-1498; CraftingManager.java:207,582'),
    (FP, 'span', 'wrench on anchor A1 then A3 11 blocks away: refused (max 10), no record; A1 then A2 10 blocks away: both record the other',
     'PipeAnchorBlockEntity.java:48-64, WrenchItem.java:82-90; TileEntityPipelineBase.java:69-75,133-153'),
    (FP, 'typed', 'one sneaking right-click of the water identifier on the first duct types the whole run, across the long pipe to the duct before barrel B',
     'FluidDuctBaseBlock.java:51-83,96-113, FluidPipeAnchorBlock.java:84-96; FluidDuctBase.java:100-126'),
    (FP, 'line', 'the 4,000 mB reach barrel B through the long pipe (the only path)', 'PipeAnchorBlockEntity.java:81-91; TileEntityPipelineBase.java:45-52'),
    (FP, 'reload', 'after leaving and opening the world: the anchors keep their pipe records and water type', 'PipeAnchorBlockEntity.java:138-155'),
]


def expectations():
    return [dict(id='%s.%s' % (f, i), text=t, source=s) for f, i, t, s in E]


GROUP_IDS = {}
for _f, _i, _t, _s in E:
    GROUP_IDS.setdefault(_f, []).append('%s.%s' % (_f, _i))


class Rows:
    """Verdicts with bookkeeping, so that a failed section turns only its own undecided rows into not-run."""

    def __init__(self, ctx):
        self.ctx, self.done = ctx, set()

    def check(self, eid, ok, detail):
        if eid not in self.done:
            self.done.add(eid)
            self.ctx.check(eid, bool(ok), detail)
        return ok

    def review(self, eid, detail):
        if eid not in self.done:
            self.done.add(eid)
            self.ctx.review(eid, detail)

    def not_run(self, ids, reason):
        for eid in ids:
            if eid not in self.done:
                self.done.add(eid)
                self.ctx.not_run(eid, reason[:400])


def cmd(ctx, command, **kw):
    return ctx.step('cmd', command=command, **kw)


def inventory(ctx):
    inv = ctx.step('inv')
    return {s['slot']: (s.get('item'), s.get('count', 0)) for s in inv['slots'] if s.get('item') and s.get('item') != 'minecraft:air'}


def count(ctx, item):
    return sum(c for i, c in inventory(ctx).values() if i == item)


def slot_of(ctx, item):
    return next((s for s, (i, n) in sorted(inventory(ctx).items()) if i == item and s < 36), None)


def free_slot(ctx):
    inv = inventory(ctx)
    return next((s for s in list(range(9, 36)) + list(range(9)) if s not in inv), None)


def menu_index(n_be, inv_slot):
    """Menu slot of a player inventory slot in a menu whose n_be machine slots come first (MenuBase.playerInv order)."""
    return n_be + (inv_slot - 9) if inv_slot >= 9 else n_be + 27 + inv_slot


def craft(ctx, name, out, made, pattern, key):
    """One craft in the open crafting table: one item per grid cell by right-clicks from the stack, Shift-click on the result."""
    before = count(ctx, out)
    used = []
    for sym, item in key.items():
        cells = [1 + r * 3 + c for r, row in enumerate(pattern) for c, ch in enumerate(row) if ch == sym]
        src = next((s for s, (i, n) in sorted(inventory(ctx).items()) if i == item and n >= len(cells)), None)
        if src is None:
            return False, '%s: no stack of %s with %d items' % (name, item, len(cells))
        ctx.step('click', slot=menu_index(10, src), after=2)
        for cell in cells:
            ctx.step('click', slot=cell, button=1, after=2)
        ctx.step('click', slot=menu_index(10, src), after=2)
        used.append('%d %s' % (len(cells), item.split(':')[1]))
    ctx.step('mod', shift=True)
    ctx.step('click', slot=0, after=4)
    ctx.step('mod', shift=False)
    after = count(ctx, out)
    return after - before == made, '%s: %s %d -> %d (want +%d) from %s' % (name, out.split(':')[1], before, after, made, ', '.join(used))


def hold(ctx, item):
    """Brings `item` into the first hotbar slot as a player does (inventory screen, number key 1 over its slot) and selects it."""
    src = slot_of(ctx, item)
    if src is None:
        raise RuntimeError('the player has no %s' % item)
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
        main = next((s for s in range(9, 36) if s not in inv), None)
        ctx.step('key', key='key.keyboard.e', action='tap', after=4)
        ctx.step('screen', expect='Inventory')
        ctx.step('hover', slot=main, frames=2)
        ctx.step('key', key='key.keyboard.1', action='tap', after=3)
        ctx.step('close')
        free = 0
    ctx.step('key', key='key.keyboard.%d' % (free + 1), action='tap', after=2)


def stand(ctx, pos, look):
    ctx.step('view', pos=list(pos), look_at=list(look), fly=False, hide_gui=False)


def face_point(pos, face):
    d = _lib.VEC[face]
    return [pos[0] + 0.5 + 0.5 * d[0], pos[1] + 0.5 + 0.5 * d[1], pos[2] + 0.5 + 0.5 * d[2]]


def use_on(ctx, pos, face, at, after=6):
    """Stands at `at` (feet), looks at the centre of `face` of the block at `pos` and right-clicks it."""
    stand(ctx, at, face_point(pos, face))
    return ctx.step('use', target=dict(pos=list(pos), face=face), after=after)


def use_center(ctx, pos, face, at, after=6, low=0.0):
    """Right-click aimed through `face` towards the middle of the block at `pos` (`low` lowers the aim): for blocks whose
    outline is smaller than the cell (posts, anchors, multiblock parts), where the face plane of the cell holds nothing. Any
    block hit is accepted; the step result records which one (the readings afterwards show whether the click took)."""
    d = _lib.VEC[face]
    stand(ctx, at, [pos[0] + 0.5 + 0.05 * d[0], pos[1] + 0.5 - low + 0.05 * d[1], pos[2] + 0.5 + 0.05 * d[2]])
    return ctx.step('use', target=dict(pos=list(pos), face=face, offset=[-0.449 * d[0], -0.449 * d[1] - low, -0.449 * d[2]]),
                    any_hit=True, after=after)


def place(ctx, item, ground, at):
    """Places `item` from the hand on top of the block `ground` (one below the cell it goes into)."""
    hold(ctx, item)
    use_on(ctx, ground, 'up', at)


def core_of(ctx, block, lo, hi):
    """The multiblock core in a box from the client's view of the placed blocks (position only; readings are server data)."""
    d = ctx.step('dump', **{'from': list(lo), 'to': list(hi)})
    cores = [(tuple(int(c) for c in b['pos']), b['props'].get('facing')) for b in d['blocks']
             if b['block'] == block and b['props'].get('type', 'core') == 'core']
    if len(cores) != 1:
        raise RuntimeError('%s: expected one core in %s..%s, found %s' % (block, lo, hi, cores))
    return cores[0]


def data(ctx, pos):
    return _lib.block_data(ctx, pos)


def state_is(ctx, pos, block_state):
    r = ctx.server('execute if block %d %d %d %s' % (tuple(pos) + (block_state,)), allow_error=True)
    return r['result'] == 1


def charge(bat):
    for it in bat.get('Items', []):
        if it.get('Slot', 0) == 0:
            return it.get('components', {}).get('minecraft:custom_data', {}).get('Charge', 0)
    return None


def cons(d):
    return sorted(tuple(c) for c in d.get('connections', []))


def open_gui(ctx, pos, face, at, screen):
    empty_hand(ctx)
    use_center(ctx, pos, face, at)
    ctx.step('screen', expect=screen)
    return ctx.step('hud', frames=2)


def put(ctx, n_be, item, target, after=4):
    """In an open machine screen: picks up the player's stack of `item` and puts it whole into machine slot `target`."""
    src = slot_of(ctx, item)
    if src is None:
        raise RuntimeError('the player has no %s' % item)
    ctx.step('click', slot=menu_index(n_be, src), after=2)
    ctx.step('click', slot=target, after=after)


def take(ctx, n_be, slot):
    """In an open machine screen: takes the stack from machine slot `slot` back into a free inventory slot."""
    free = free_slot(ctx)
    ctx.step('click', slot=slot, after=2)
    ctx.step('click', slot=menu_index(n_be, free), after=2)


def window(ctx, ticks, label):
    ctx.step('view', pos=MID, pitch=30.0, yaw=0.0, fly=False, hide_gui=False)
    return ctx.sprint(ticks, label=label, poll_s=0.3, timeout_s=300)


def power_state(ctx, nodes):
    b, s, t = data(ctx, nodes['burner']), data(ctx, SEP), data(ctx, BAT)
    return dict(burner=b.get('power'), burn=b.get('burnTime'), maxburn=b.get('maxBurnTime'), on=b.get('isOn'),
                sep=s.get('power'), limit=s.get('configuredLimit'), battery=charge(t), game=ctx.server()['game_time'])


def read_at(ctx, pos):
    """Server data of the block entity at pos and the game time the reply was made at (the server runs the command
    between two ticks, so the data is the state after that tick)."""
    r = ctx.server('data get block %d %d %d' % tuple(pos))
    lines = [m for m in r['messages'] if m.strip()]
    if not lines:
        raise RuntimeError('no reply to data get block at %s' % (pos,))
    return _lib.data_value(lines[-1]), r['game_time']


def freeze_still(ctx):
    """Freezes the world and waits 4 s of wall time. The power and fluid nets are updated on every server tick event,
    which a frozen server still fires (NtmEventHandler.java:69-76); their provider and receiver entries are dropped
    only after 3,000 ms without a refresh from a ticking block entity (PowerNetMK2.java:22,42,61). After the wait
    nothing moves, so readings of several blocks taken one after another belong together."""
    ctx.server('tick freeze')
    ctx.step('wait', ticks=80)


def rate_window(ctx, ticks, label):
    """A measured window in the running world: the battery's charge and the reply's game time before and after a
    sprint of `ticks`; the gain is compared with the limit times the game ticks between the two replies."""
    t0, g0 = read_at(ctx, BAT)
    window(ctx, ticks, label)
    t1, g1 = read_at(ctx, BAT)
    return charge(t0), g0, charge(t1), g1


def run(ctx):
    rows = Rows(ctx)
    ok = dict(craft_pt=False, construct=False, craft_pc=False, craft_nf=False, craft_fl=False, craft_fc=False, craft_fp=False,
              power=False, fluid=False, identifier=False)
    nodes = {}
    _lib.setup_world(ctx, freeze=False)
    ctx.step('view', pos=[TABLE[0] + 0.5, Y, TABLE[2] + 2.5], look_at=[TABLE[0] + 0.5, Y + 0.5, TABLE[2] + 0.5], fly=False, hide_gui=False)
    ctx.step('wait', ticks=40)
    cmd(ctx, 'clear @s', allow_error=True)
    cmd(ctx, 'gamemode survival')
    handover = dict(HANDOVER)
    missing = [i for i, n in GIVE if i not in handover]
    for item, n in GIVE + VANILLA + TOOLS:
        cmd(ctx, 'give @s %s %d' % (item, n))
    rows.review(PT + '.start-items', 'from the stage-6 start list (%d items, %d world-generation rows): %s%s; vanilla: %s; not on the list '
                '(a stage-2 product): %s; water buckets: %d (vanilla bucket and water)'
                % (len(HANDOVER), sum(1 for i, _ in HANDOVER if i.startswith('block:')), ', '.join('%s x%d' % g for g in GIVE),
                   ' (NOT on the list: %s)' % missing if missing else '', ', '.join('%s x%d' % g for g in VANILLA),
                   ', '.join('%s x%d' % g for g in TOOLS), BUCKETS))

    # ---------------------------------------------------------------- crafting, one section per feature group
    cmd(ctx, 'setblock %d %d %d minecraft:crafting_table' % TABLE)
    crafts = [
        ('craft_pt', PT, [('pylons', 'hbmsntm:red_pylon', 4, ['CWC', 'PWP', ' S '], dict(C='hbmsntm:coil_copper', W='minecraft:oak_planks',
                                                                                         P='hbmsntm:plate_polymer', S='minecraft:cobblestone')),
                          ('cable drum', 'hbmsntm:wiring_red_copper', 1, ['PPP', 'PIP', 'PPP'], dict(P='hbmsntm:plate_steel', I='hbmsntm:ingot_steel'))]),
        ('craft_pc', PC_, [('sealed wire', 'hbmsntm:red_wire_coated', 16, ['WRW', 'RIR', 'WRW'],
                            dict(W='hbmsntm:plate_polymer', I='hbmsntm:ingot_red_copper', R='hbmsntm:wire_red_copper')),
                           ('power switch', 'hbmsntm:cable_switch', 1, ['S', 'W'], dict(S='minecraft:lever', W='hbmsntm:red_wire_coated')),
                           ('power gauge', 'hbmsntm:red_cable_gauge', 1, ['WIC'], dict(W='hbmsntm:red_wire_coated', I='hbmsntm:ingot_steel',
                                                                                         C='hbmsntm:circuit_integrated_board'))]),
        ('craft_nf', NF, [('separator', 'hbmsntm:network_separator', 1, ['SCS', 'DTD', 'SCS'],
                           dict(S='hbmsntm:plate_steel', C='hbmsntm:circuit_integrated_board', D='hbmsntm:coil_copper', T='hbmsntm:transformer'))]),
        ('craft_line', None, [('wood burner', 'hbmsntm:machine_wood_burner', 1, ['AAA', 'BDB', 'C C'],
                               dict(A='hbmsntm:plate_steel', B='hbmsntm:coil_copper', C='minecraft:iron_ingot', D='minecraft:furnace')),
                              ('battery socket', 'hbmsntm:machine_battery_socket', 1, ['A A', 'A A', 'ABA'], dict(A='hbmsntm:plate_polymer', B='hbmsntm:coil_copper')),
                              ('redstone battery', 'hbmsntm:battery_pack', 1, ['IRI', 'PRP', 'IRI'],
                               dict(I='hbmsntm:plate_iron', R='minecraft:redstone_block', P='hbmsntm:plate_polymer')),
                              ('fluid identifier', 'hbmsntm:fluid_identifier_multi', 1, ['D', 'C', 'P'],
                               dict(D='minecraft:blue_dye', C='hbmsntm:circuit_vacuum_tube', P='hbmsntm:plate_iron'))]),
        ('craft_fl', FL, [('ducts', 'hbmsntm:fluid_duct_neo', 8, ['SAS', '   ', 'SAS'], dict(S='hbmsntm:plate_steel', A='hbmsntm:plate_aluminium')),
                          ('steel barrel 1', 'hbmsntm:barrel_steel', 1, ['IPI', 'I I', 'IPI'], dict(I='hbmsntm:plate_steel', P='hbmsntm:ingot_steel')),
                          ('steel barrel 2', 'hbmsntm:barrel_steel', 1, ['IPI', 'I I', 'IPI'], dict(I='hbmsntm:plate_steel', P='hbmsntm:ingot_steel'))]),
        ('craft_fc', FC, [('paintable ducts', 'hbmsntm:fluid_duct_paintable', 8, ['SAS', 'A A', 'SAS'], dict(S='hbmsntm:ingot_steel', A='hbmsntm:plate_aluminium')),
                          ('valve', 'hbmsntm:fluid_valve', 1, ['S', 'W'], dict(S='minecraft:lever', W='hbmsntm:fluid_duct_paintable')),
                          ('fluid switch', 'hbmsntm:fluid_switch', 1, ['S', 'W'], dict(S='minecraft:redstone', W='hbmsntm:fluid_duct_paintable')),
                          ('counter valve', 'hbmsntm:fluid_counter_valve', 1, ['S', 'W'], dict(S='hbmsntm:circuit_microchip', W='hbmsntm:fluid_switch')),
                          ('duct gauge', 'hbmsntm:fluid_duct_gauge', 1, ['WIC'], dict(W='hbmsntm:fluid_duct_paintable', I='hbmsntm:ingot_steel',
                                                                                     C='hbmsntm:circuit_integrated_board'))]),
        ('craft_fp', FP, [('anchors 1', 'hbmsntm:pipe_anchor', 2, ['P', 'P', 'S'], dict(P='hbmsntm:pipe_steel', S='hbmsntm:ingot_steel')),
                          ('anchors 2', 'hbmsntm:pipe_anchor', 2, ['P', 'P', 'S'], dict(P='hbmsntm:pipe_steel', S='hbmsntm:ingot_steel')),
                          ('wrench', 'hbmsntm:wrench', 1, [' S ', ' IS', 'I  '], dict(S='hbmsntm:ingot_steel', I='minecraft:iron_ingot'))]),
    ]
    line_parts = []
    for flag, group, recipes in crafts:
        try:
            use_on(ctx, TABLE, 'south', [TABLE[0] + 0.5, Y, TABLE[2] + 2.5])
            ctx.step('screen', expect='Crafting')
            log, good = [], True
            for name, out, made, pattern, key in recipes:
                g, line = craft(ctx, name, out, made, pattern, key)
                good = good and g
                log.append(line)
            ctx.step('close')
            ok[flag] = good
            if group:
                rows.check(group + '.craft', good, '; '.join(log))
            else:
                line_parts.append('; '.join(log))
                ok['power'] = good  # the burner, the socket, the battery and the identifier carry both lines
                ok['identifier'] = good
        except Exception as e:  # noqa: BLE001
            cleanup(ctx)
            if group:
                rows.not_run([group + '.craft'], 'crafting failed: %r' % e)
            else:
                line_parts.append('crafting failed: %r' % e)
    line_items_ok = ok['power']

    # ---------------------------------------------------------------- the steel anvil: substations and the large pylon
    try:
        ok['construct'] = construct(ctx, rows)
    except Exception as e:  # noqa: BLE001
        cleanup(ctx)
        ok['construct'] = False
        rows.not_run([PT + '.construct'], 'the anvil construction failed: %r' % e)
    if not ok['construct']:
        line_parts.append('the substations and the large pylon were not built on the anvil')

    # ---------------------------------------------------------------- power line
    power_ids = GROUP_IDS[PT][3:] + GROUP_IDS[PC_][1:] + GROUP_IDS[NF][1:]
    built_power = False
    if not (line_items_ok and ok['craft_pt'] and ok['construct'] and ok['craft_pc'] and ok['craft_nf']):
        rows.not_run(power_ids, 'a part of the power line was not crafted (%s)' % ' / '.join(line_parts))
    else:
        try:
            build_power(ctx, rows, nodes)
            built_power = True
        except Exception as e:  # noqa: BLE001
            cleanup(ctx)
            rows.not_run(power_ids, 'building the power line failed: %r' % e)

    # ---------------------------------------------------------------- fluid line
    fluid_ids = GROUP_IDS[FL][1:] + GROUP_IDS[FC][1:] + GROUP_IDS[FP][1:]
    built_fluid = False
    if not (ok['identifier'] and ok['craft_fl'] and ok['craft_fc'] and ok['craft_fp']):
        rows.not_run(fluid_ids, 'a part of the fluid line was not crafted (%s)' % ' / '.join(line_parts))
    else:
        try:
            build_fluid(ctx, rows)
            built_fluid = True
        except Exception as e:  # noqa: BLE001
            cleanup(ctx)
            rows.not_run(fluid_ids, 'building the fluid line failed: %r' % e)

    freeze_still(ctx)
    before = {}
    if built_power:
        try:
            before['power'] = run_power(ctx, rows, nodes)
        except Exception as e:  # noqa: BLE001
            cleanup(ctx)
            built_power = False
            rows.not_run(power_ids, 'running the power line failed: %r' % e)
    if built_fluid:
        try:
            ctx.server('tick freeze')
            before['fluid'] = run_fluid(ctx, rows)
        except Exception as e:  # noqa: BLE001
            cleanup(ctx)
            built_fluid = False
            rows.not_run(fluid_ids, 'running the fluid line failed: %r' % e)

    # ---------------------------------------------------------------- leave, open again, the same readings
    reload_ids = [i for i in power_ids + fluid_ids if i.endswith('.reload') or i.endswith('.after-reload')]
    if not before:
        rows.not_run(reload_ids, 'no line ran')
        return
    try:
        ctx.step('view', pos=MID, pitch=30.0, yaw=0.0, fly=False, hide_gui=False)
        ctx.step('leave')
        ctx.step('openworld', world=ctx.run.world['name'])
        freeze_still(ctx)
        if 'power' in before:
            reload_power(ctx, rows, nodes, before['power'])
        if 'fluid' in before:
            reload_fluid(ctx, rows, before['fluid'])
    except Exception as e:  # noqa: BLE001
        cleanup(ctx)
        rows.not_run(reload_ids, 'leaving and opening the world failed: %r' % e)
    finally:
        try:
            ctx.server('tick unfreeze')
        except Exception:  # noqa: BLE001
            pass


def cleanup(ctx):
    for step in (dict(op='close'), dict(op='mod', shift=False), dict(op='key', key='key.keyboard.left.shift', action='release')):
        op = step.pop('op')
        try:
            ctx.step(op, allow_fail=True, **step)
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------- the steel anvil

def anvil_recipes(ctx):
    """The construction recipes a tier-2 anvil lists, in the anvil screen's order (AnvilMenuScreen.java:46-50)."""
    r = ctx.step('export', kind='anvil')
    path = Path(ctx.channels[ctx.default].dir) / r['file']
    rows = json.loads(path.read_text(encoding='utf-8'))['construction']
    return [x for x in rows if x['tier_lower'] <= ANVIL_TIER and (x['tier_upper'] == -1 or x['tier_upper'] >= ANVIL_TIER)]


def open_anvil(ctx):
    """Right-clicks the anvil from the south with an empty hand, aimed at the middle of its smaller front face."""
    empty_hand(ctx)
    x, y, z = ANVIL_POS
    look = [x + 0.5 + ANVIL_AIM[0], y + 0.5 + ANVIL_AIM[1], z + 0.5 + 0.499 + ANVIL_AIM[2]]
    stand(ctx, [x + 0.5, Y, z + 2.5], look)
    ctx.step('use', target=dict(pos=list(ANVIL_POS), face='south', offset=list(ANVIL_AIM)), after=6)
    ctx.step('screen', expect='Anvil')
    return ctx.step('hud', frames=2)


def anvil_build(ctx, recipes, name, out, need, made, tooltip):
    """Opens the anvil by hand, pages to the recipe making `out` that takes `need` with clicks on the list's right arrow,
    reads the recipe's tooltip, selects it and presses construct once. Returns (ok, detail)."""
    pos = next((p for p, x in enumerate(recipes) if x['outputs'][0]['id'] == out
                and any(a['id'] == need for alts in x['inputs'] for a in alts)), None)
    if pos is None:
        return False, '%s: no tier-%d anvil recipe for %s with %s' % (name, ANVIL_TIER, out, need)
    before = count(ctx, out)
    hud = open_anvil(ctx)
    left, top = hud['gui_left'], hud['gui_top']
    size = max(0, -(-(len(recipes) - ANVIL_PAGE) // 2))
    index = min(pos // 2, size)
    # the list scrolls one column per click on its right arrow (AnvilMenuScreen.java:225-230; the original's only paging
    # besides the wheel, GUIAnvil.mouseClicked); the screen opens on the first column
    for _ in range(index):
        ctx.step('click', at=[left + 106 + 4, top + 71 + 18], after=1)
    ind = pos - index * 2
    cell = [left + 16 + 18 * (ind // 2) + 9, top + 71 + 18 * (ind % 2) + 9]
    ctx.step('hover', at=cell, frames=3)
    tip = [t['text'] for t in ctx.step('hud', frames=3).get('texts', []) if t['text'].startswith('tooltip: ')]
    named = tip[:1] == ['tooltip: ' + tooltip]
    if named:
        ctx.step('click', at=cell, after=3)
        ctx.step('click', at=[left + 52 + 9, top + 53 + 9], after=6)
    ctx.step('close')
    after = count(ctx, out)
    return named and after == before + made, ('%s: %s %d -> %d (want +%d; anvil list position %d of %d, %d arrow clicks, cell %d, '
                                              'tooltip %s, want %s)' % (name, out.split(':')[1], before, after, made, pos,
                                                                        len(recipes), index, ind, tip[:1], tooltip))


def construct(ctx, rows):
    place(ctx, 'hbmsntm:anvil', (ANVIL_POS[0], Y - 1, ANVIL_POS[2]), [ANVIL_POS[0] + 0.5, Y, ANVIL_POS[2] + 3.5])
    if not state_is(ctx, ANVIL_POS, 'hbmsntm:anvil[subtype=2]'):
        raise RuntimeError('no steel anvil (subtype 2) at %s after placing it' % (ANVIL_POS,))
    recipes = anvil_recipes(ctx)
    good, log = True, []
    for name, out, need, made, tooltip in CONSTRUCT:
        g, line = anvil_build(ctx, recipes, name, out, need, made, tooltip)
        good = good and g
        log.append(line)
    rows.check(PT + '.construct', good, '; '.join(log))
    return good


# ---------------------------------------------------------------- power

def build_power(ctx, rows, nodes):
    # wood burner, clicked from the south (facing south)
    place(ctx, 'hbmsntm:machine_wood_burner', (BX, Y - 1, BZ), [BX + 0.5, Y, BZ + 3.5])
    burner, facing = core_of(ctx, 'hbmsntm:machine_wood_burner', (BX - 2, Y, BZ - 2), (BX + 2, Y + 2, BZ + 2))
    if burner != (BX, Y, BZ) or facing != 'south':
        raise RuntimeError('wood burner core %s facing %s, expected (%d, %d, %d) south' % (burner, facing, BX, Y, BZ))
    nodes['burner'] = burner
    # its power ports: core + 2 x back, and one more clockwise (MachineWoodBurnerBlockEntity.java:226-236): (BX, BZ - 2), (BX - 1, BZ - 2)
    for name, p, at in (('pylon A', PA, [PA[0] - 2.5, Y, PA[2] + 0.5]), ('pylon B', PB, [PB[0] - 2.5, Y, PB[2] + 0.5]),
                        ('pylon C', PC, [PC[0] + 3.5, Y, PC[2] + 0.5])):
        place(ctx, 'hbmsntm:red_pylon', (p[0], Y - 1, p[2]), at)
        core_of(ctx, 'hbmsntm:red_pylon', p, (p[0], Y + 4, p[2]))
    for name, c, block in (('substation 1', SUB1, 'hbmsntm:substation'), ('large pylon', LARGE, 'hbmsntm:red_pylon_large'),
                           ('substation 2', SUB2, 'hbmsntm:substation')):
        click = (c[0], Y - 1, c[2] + 1) if block == 'hbmsntm:substation' else (c[0], Y - 1, c[2])
        place(ctx, block, click, [c[0] + 0.5, Y, click[2] + 3.5])
        got, f = core_of(ctx, block, (c[0] - 3, Y, c[2] - 3), (c[0] + 3, Y + 1, c[2] + 3))
        if got != c:
            raise RuntimeError('%s core at %s (facing %s), expected %s' % (name, got, f, c))
        nodes[name] = f
    place(ctx, 'hbmsntm:network_separator', (SEP[0], Y - 1, SEP[2]), [SEP[0] + 0.5, Y, SEP[2] + 3.5])
    got, f = core_of(ctx, 'hbmsntm:network_separator', (SEP[0] - 2, Y, SEP[2] - 2), (SEP[0] + 2, Y + 1, SEP[2] + 2))
    if got != SEP or f != 'south':
        raise RuntimeError('separator core %s facing %s, expected %s south' % (got, f, SEP))
    place(ctx, 'hbmsntm:machine_battery_socket', (BAT[0], Y - 1, BAT[2]), [BAT[0] + 0.5, Y, BAT[2] + 3.5])
    got, f = core_of(ctx, 'hbmsntm:machine_battery_socket', (BAT[0] - 2, Y, BAT[2] - 2), (BAT[0] + 2, Y + 1, BAT[2] + 2))
    if got != BAT or f != 'south':
        raise RuntimeError('battery socket core %s facing %s, expected %s south' % (got, f, BAT))
    # the switch and the gauge from the north (south of them is substation 2)
    place(ctx, 'hbmsntm:cable_switch', (SWITCH[0], Y - 1, SWITCH[2]), [SWITCH[0] + 0.5, Y, SWITCH[2] - 2.5])
    place(ctx, 'hbmsntm:red_cable_gauge', (GAUGE[0], Y - 1, GAUGE[2]), [GAUGE[0] + 0.5, Y, GAUGE[2] - 2.5])

    # battery into the socket, the log into the burner (it takes the fuel at once; it only burns while on), before the cables
    # stand between the player and the machines
    open_gui(ctx, BAT, 'south', [BAT[0] + 0.5, Y, BAT[2] + 2.5], 'BatterySocketScreen')
    put(ctx, 1, 'hbmsntm:battery_pack', 0)
    ctx.step('close')
    open_gui(ctx, (BX, Y, BZ), 'south', [BX + 0.5, Y, BZ + 2.5], 'MachineWoodBurnerScreen')
    put(ctx, 6, 'minecraft:oak_log', 0)
    ctx.step('close')
    # the separator's limit: click into the text field, delete two characters, close (the screen sends on close)
    empty_hand(ctx)
    use_center(ctx, SEP, 'south', [SEP[0] + 0.5, Y, SEP[2] + 2.5])
    ctx.step('screen', expect='NetworkSeparatorScreen')
    ctx.step('widget', **{'class': 'EditBox'})
    for _ in range(2):
        ctx.step('key', key='key.keyboard.backspace', action='tap', after=2)
    ctx.step('close')
    ctx.step('wait', ticks=5)

    for c in CABLES:
        r = ctx.server('execute if block %d %d %d minecraft:air' % c, allow_error=True)
        if r['result'] != 1:
            raise RuntimeError('cable cell %s is not free: %s' % (c, r['messages']))
        cmd(ctx, 'setblock %d %d %d hbmsntm:red_cable' % c)

    # wires: A -> C (too far), A -> B, B -> substation 1 (other type), substation 1 -> large -> substation 2
    hold(ctx, 'hbmsntm:wiring_red_copper')
    near = {PA: [PA[0] - 2.5, Y, PA[2] + 0.5], PB: [PB[0] - 2.5, Y, PB[2] + 0.5], PC: [PC[0] + 3.5, Y, PC[2] + 0.5]}
    for first, second in ((PA, PC), (PA, PB), (PB, SUB1)):
        use_center(ctx, first, 'west' if first != PC else 'east', near[first])
        if second == SUB1:
            use_center(ctx, (SUB1[0], Y, SUB1[2] + 1), 'south', [SUB1[0] + 0.5, Y, SUB1[2] + 3.5], low=0.3)
        else:
            use_center(ctx, second, 'west' if second != PC else 'east', near[second])
    da, db, dc, ds1 = data(ctx, PA), data(ctx, PB), data(ctx, PC), data(ctx, SUB1)
    rows.check(PT + '.span', cons(da) == [PB] and cons(db) == [PA] and cons(dc) == [] and cons(ds1) == [],
               'pylon A records %s (want [B %s]); B records %s (want [A]); C (26 m from A) %s (want none); substation 1 after B %s (want none)'
               % (cons(da), PB, cons(db), cons(dc), cons(ds1)))
    lf = nodes['large pylon']
    vec = {'north': (3.375, 0.0), 'west': (2.3865, -2.3865), 'south': (0.0, -3.375), 'east': (-2.3865, -2.3865)}[lf]
    lp = (LARGE[0] + 0.5 + vec[0], Y + 12.3125, LARGE[2] + 0.5 + vec[1])
    dist = [round(sum((a - b) ** 2 for a, b in zip((s[0] + 0.5, Y + 5.25, s[2] + 0.5), lp)) ** 0.5, 2) for s in (SUB1, SUB2)]
    for first, second in ((SUB1, LARGE), (LARGE, SUB2)):
        for c in (first, second):
            use_center(ctx, (c[0], Y, c[2] + 1), 'south', [c[0] + 0.5, Y, c[2] + 3.5], low=0.3)
    d1, dl, d2 = data(ctx, SUB1), data(ctx, LARGE), data(ctx, SUB2)
    rows.check(PT + '.quad-span', max(dist) <= 20 and cons(d1) == [LARGE] and cons(dl) == sorted([SUB1, SUB2]) and cons(d2) == [LARGE],
               'mount distances substation 1 / 2 to the large pylon (facing %s) %s (max 20); records: substation 1 %s, large pylon %s, substation 2 %s'
               % (lf, dist, cons(d1), cons(dl), cons(d2)))


def run_power(ctx, rows, nodes):
    # the world is frozen: the burner is switched on in its screen
    hud = open_gui(ctx, (BX, Y, BZ), 'south', [BX + 0.5, Y, BZ + 2.5], 'MachineWoodBurnerScreen')
    ctx.step('click', at=[hud['gui_left'] + 61, hud['gui_top'] + 24], button=0, after=4)
    ctx.step('close')
    sep = data(ctx, SEP)
    # the measured windows run in the running world, each reading with its own game time (see freeze_still)
    ctx.server('tick unfreeze')
    b0, g0 = read_at(ctx, nodes['burner'])
    c0 = charge(read_at(ctx, BAT)[0])
    window(ctx, 100, 'stage6-switch-off')
    c1 = charge(read_at(ctx, BAT)[0])
    b1, g1 = read_at(ctx, nodes['burner'])
    t1 = g1 - g0
    rows.check(PC_ + '.switch-off', c1 == c0 == 0 and b1.get('power') - b0.get('power') == BURNER_GEN * t1 and b0.get('isOn') == 1,
               'switch off, %d game ticks between the burner readings: battery %s -> %s (want 0 -> 0); burner on %s, %s -> %s (want +%d = 100 x %d)'
               % (t1, c0, c1, b0.get('isOn'), b0.get('power'), b1.get('power'), BURNER_GEN * t1, t1))
    empty_hand(ctx)
    use_center(ctx, SWITCH, 'up', [SWITCH[0] + 0.5, Y, SWITCH[2] - 2.5])
    on = state_is(ctx, SWITCH, 'hbmsntm:cable_switch[enabled=true]')
    window(ctx, 20, 'stage6-settle')
    c2, g2, c3, g3 = rate_window(ctx, 200, 'stage6-switch-on')
    t3, gain = g3 - g2, c3 - c2
    rows.check(PC_ + '.switch-on', on and gain == LIMIT * t3, 'switch on (server state %s); %d game ticks between the battery readings: battery %s -> %s, +%d (want %d x %d = %d)'
               % (on, t3, c2, c3, gain, LIMIT, t3, LIMIT * t3))
    rows.check(NF + '.limit', sep.get('configuredLimit') == LIMIT and gain == LIMIT * t3,
               'configuredLimit after the screen %s (want %d), actualLimit %s; battery +%d in %d game ticks (want %d) while the burner makes %d HE/t'
               % (sep.get('configuredLimit'), LIMIT, sep.get('actualLimit'), gain, t3, LIMIT * t3, BURNER_GEN))
    # the gauge as a player sees it, in the running world within the gauge's 25-block sync range (CableGaugeBlockEntity.java:38)
    stand(ctx, [GAUGE[0] + 0.5, Y, GAUGE[2] - 1.6], [GAUGE[0] + 0.5, Y + 0.5, GAUGE[2] + 0.5])
    empty_hand(ctx)
    ctx.step('wait', ticks=50)
    texts = _lib.crosshair_texts(ctx.step('hud', frames=6))
    rows.check(PC_ + '.gauge', any('10HE/t' in t for t in texts) and any('200HE/s' in t for t in texts),
               'look overlay texts: %s (want 10HE/t and 200HE/s)' % texts)
    # energy balance in a still frozen world: everything the log has burned is in the burner, the separator or the battery
    freeze_still(ctx)
    r3 = power_state(ctx, nodes)
    burned = r3['maxburn'] - r3['burn']
    total = r3['battery'] + r3['sep'] + r3['burner']
    rows.check(PT + '.line', r3['maxburn'] == LOG_TICKS and total == BURNER_GEN * burned and r3['burner'] < BURNER_MAX
               and r3['battery'] > 0,
               'log burn time %s (want %d); burned %d ticks -> %d HE made; battery %s + separator %s + burner %s = %d (frozen, read after 4 s)'
               % (r3['maxburn'], LOG_TICKS, burned, BURNER_GEN * burned, r3['battery'], r3['sep'], r3['burner'], total))
    ctx.server('tick unfreeze')
    # a state that holds still while the world is closed: switch off, separator drained, burner full (it stops burning)
    use_center(ctx, SWITCH, 'up', [SWITCH[0] + 0.5, Y, SWITCH[2] - 2.5])
    off = state_is(ctx, SWITCH, 'hbmsntm:cable_switch[enabled=false]')
    window(ctx, 20, 'stage6-drain')
    need = (BURNER_MAX - power_state(ctx, nodes)['burner'] + BURNER_GEN - 1) // BURNER_GEN
    window(ctx, need + 40, 'stage6-fill-burner')
    freeze_still(ctx)
    r4 = power_state(ctx, nodes)
    window(ctx, 20, 'stage6-still')
    ctx.step('wait', ticks=80)
    r5 = power_state(ctx, nodes)
    if not (off and r4['burner'] == BURNER_MAX and r4['sep'] == 0 and {k: v for k, v in r4.items() if k != 'game'} == {k: v for k, v in r5.items() if k != 'game'}):
        raise RuntimeError('the power line does not hold still before leaving: switch off %s, %s then %s' % (off, r4, r5))
    return dict(state=r5, wires={p: cons(data(ctx, p)) for p in (PA, PB, PC, SUB1, LARGE, SUB2)}, off=off)


def reload_power(ctx, rows, nodes, before):
    r = power_state(ctx, nodes)
    wires = {p: cons(data(ctx, p)) for p in (PA, PB, PC, SUB1, LARGE, SUB2)}
    off = state_is(ctx, SWITCH, 'hbmsntm:cable_switch[enabled=false]')
    b, a = before['state'], r
    rows.check(PT + '.reload', wires == before['wires'], 'wire records before %s, after %s' % (before['wires'], wires))
    rows.check(PC_ + '.reload', off and all(a[k] == b[k] for k in ('burner', 'burn', 'maxburn', 'on', 'battery')),
               'switch off %s; burner power %s/%s, burnTime %s/%s, isOn %s/%s; battery %s/%s (before/after)'
               % (off, b['burner'], a['burner'], b['burn'], a['burn'], b['on'], a['on'], b['battery'], a['battery']))
    rows.check(NF + '.reload', a['limit'] == b['limit'] == LIMIT and a['sep'] == b['sep'],
               'configuredLimit %s/%s, buffer %s/%s (before/after)' % (b['limit'], a['limit'], b['sep'], a['sep']))
    ctx.server('tick unfreeze')
    empty_hand(ctx)
    use_center(ctx, SWITCH, 'up', [SWITCH[0] + 0.5, Y, SWITCH[2] - 2.5])
    window(ctx, 20, 'stage6-reload-settle')
    c0, g0, c1, g1 = rate_window(ctx, 200, 'stage6-reload-window')
    t = g1 - g0
    rows.check(PT + '.after-reload', c1 - c0 == LIMIT * t,
               'after opening the world, switch on, %d game ticks between the battery readings: battery %s -> %s, +%d (want +%d)'
               % (t, c0, c1, c1 - c0, LIMIT * t))


# ---------------------------------------------------------------- fluid

def build_fluid(ctx, rows):
    place(ctx, 'hbmsntm:barrel_steel', (BAR_A[0], Y - 1, FZ), [BAR_A[0] + 0.5, Y, FZ + 2.5])
    place(ctx, 'hbmsntm:barrel_steel', (BAR_B[0], Y - 1, FZ), [BAR_B[0] + 0.5, Y, FZ + 2.5])
    for item, p in (('hbmsntm:fluid_valve', VALVE), ('hbmsntm:fluid_duct_gauge', FGAUGE), ('hbmsntm:fluid_counter_valve', COUNTER)):
        place(ctx, item, (p[0], Y - 1, FZ), [p[0] + 0.5, Y, FZ + 2.5])
    for d in DUCTS:
        cmd(ctx, 'setblock %d %d %d hbmsntm:fluid_duct_neo' % d)
    cmd(ctx, 'setblock %d %d %d minecraft:stone' % (A3[0], Y, A3[2] + 1))
    hold(ctx, 'hbmsntm:pipe_anchor')
    use_on(ctx, (FX + 5, Y, FZ), 'east', [FX + 7.5, Y, FZ + 1.5])
    use_on(ctx, (FX + 17, Y, FZ), 'west', [FX + 15.5, Y, FZ + 1.5])
    use_on(ctx, (A3[0], Y, A3[2] + 1), 'north', [A3[0] + 0.5, Y, A3[2] - 1.5])
    # wrench: A1 -> A3 (too far), A1 -> A2
    hold(ctx, 'hbmsntm:wrench')
    use_center(ctx, A1, 'south', [A1[0] + 0.5, Y, A1[2] + 2.5])
    use_center(ctx, A3, 'north', [A3[0] + 0.5, Y, A3[2] - 2.5])
    use_center(ctx, A1, 'south', [A1[0] + 0.5, Y, A1[2] + 2.5])
    use_center(ctx, A2, 'south', [A2[0] + 0.5, Y, A2[2] + 2.5])
    d1, d2, d3 = data(ctx, A1), data(ctx, A2), data(ctx, A3)
    rows.check(FP + '.span', cons(d1) == [A2] and cons(d2) == [A1] and cons(d3) == [],
               'A1 records %s (want [A2 %s]); A2 records %s (want [A1]); A3 (11 from A1) records %s (want none)' % (cons(d1), A2, cons(d2), cons(d3)))

    # the identifier set to water in its own screen (Shift + use in the air), the search list filled by a key press
    hold(ctx, 'hbmsntm:fluid_identifier_multi')
    ctx.step('view', pos=[FX + 1.5, Y, FZ + 3.5], pitch=-60.0, yaw=0.0, fly=False, hide_gui=False)
    ctx.step('key', key='key.keyboard.left.shift', action='press', after=3)
    ctx.step('mouse', button=1, action='click', after=4)
    ctx.step('key', key='key.keyboard.left.shift', action='release', after=2)
    ctx.step('screen', expect='FluidScreen')
    ctx.step('key', key='key.keyboard.backspace', action='tap', after=2)
    hud = ctx.step('hud', frames=2)
    left, top = (hud['gui_scaled_width'] - 176) // 2, (hud['gui_scaled_height'] - 54) // 2
    # Fluids.java:421-425: NONE, AIR, AIRBLAST, WATER: water is the fourth entry of the unfiltered list (FluidScreen.java:130-150,173-189)
    ctx.step('click', at=[left + 7 + 3 * 18 + 9, top + 29 + 9], button=0, after=4)
    ctx.step('close')
    # one sneaking click on the first duct types the whole run
    stand(ctx, [FX + 1.5, Y, FZ + 2.5], [FX + 1.5, Y + 0.5, FZ + 0.5])
    ctx.step('key', key='key.keyboard.left.shift', action='press', after=3)
    use_center(ctx, DUCTS[0], 'south', [FX + 1.5, Y, FZ + 2.5])
    ctx.step('key', key='key.keyboard.left.shift', action='release', after=3)
    types = {name: data(ctx, p).get('Type') for name, p in (('duct 1', DUCTS[0]), ('valve', VALVE), ('gauge', FGAUGE), ('counter', COUNTER),
                                                             ('A1', A1), ('A2', A2), ('duct before B', DUCTS[2]), ('A3', A3))}
    rows.check(FP + '.typed', all(v == WATER_ID for k, v in types.items() if k != 'A3') and types['A3'] != WATER_ID,
               'fluid type ids after one sneaking click: %s (want %d everywhere but the unconnected A3)' % (types, WATER_ID))

    # barrel A: identifier, 4 water buckets, mode 0 -> 2
    cmd(ctx, 'give @s minecraft:water_bucket %d' % BUCKETS)
    hud = open_gui(ctx, BAR_A, 'south', [BAR_A[0] + 0.5, Y, FZ + 2.5], 'BarrelScreen')
    put(ctx, 6, 'hbmsntm:fluid_identifier_multi', 0)
    take(ctx, 6, 1)
    for _ in range(BUCKETS):
        put(ctx, 6, 'minecraft:water_bucket', 2)
    for _ in range(2):
        ctx.step('click', at=[hud['gui_left'] + 160, hud['gui_top'] + 43], button=0, after=4)
    ctx.step('close')
    da = data(ctx, BAR_A)
    ta = _lib.tanks(da).get('tank', {})
    buckets = sum(it.get('count', 0) for it in da.get('Items', []) if it.get('Slot') == 3 and it.get('id') == 'minecraft:bucket')
    rows.check(FL + '.barrel-load', ta.get('fill') == BUCKETS * BUCKET_MB and ta.get('max') == BARREL_MAX and ta.get('type') == WATER_ID
               and buckets == BUCKETS and da.get('mode') == 2,
               'barrel A tank %s (want %d of %d, type %d); empty buckets in slot 3: %d (want %d); mode %s (want 2)'
               % (ta, BUCKETS * BUCKET_MB, BARREL_MAX, WATER_ID, buckets, BUCKETS, da.get('mode')))
    # barrel B: identifier only (receive mode, the default)
    open_gui(ctx, BAR_B, 'south', [BAR_B[0] + 0.5, Y, FZ + 2.5], 'BarrelScreen')
    put(ctx, 6, 'hbmsntm:fluid_identifier_multi', 0)
    take(ctx, 6, 1)
    ctx.step('close')


def fluid_state(ctx):
    a, b, c = data(ctx, BAR_A), data(ctx, BAR_B), data(ctx, COUNTER)
    ta, tb = _lib.tanks(a).get('tank', {}), _lib.tanks(b).get('tank', {})
    return dict(a=ta.get('fill'), a_type=ta.get('type'), a_mode=a.get('mode'), b=tb.get('fill'), b_type=tb.get('type'), b_mode=b.get('mode'),
                counter=c.get('counter'), valve=state_is(ctx, VALVE, 'hbmsntm:fluid_valve[enabled=true]'),
                counter_open=state_is(ctx, COUNTER, 'hbmsntm:fluid_counter_valve[enabled=true]'))


def run_fluid(ctx, rows):
    empty_hand(ctx)
    use_center(ctx, COUNTER, 'up', [COUNTER[0] + 0.5, Y, FZ + 2.5])
    f0 = fluid_state(ctx)
    window(ctx, 40, 'stage6-valve-closed')
    f1 = fluid_state(ctx)
    rows.check(FC + '.valve-closed', f1['counter_open'] and not f1['valve'] and f1['b'] == 0 and f1['a'] == BUCKETS * BUCKET_MB and f1['counter'] == 0,
               'valve open %s, counter valve open %s; barrel A %s, barrel B %s, counter %s (want 4000, 0, 0)'
               % (f1['valve'], f1['counter_open'], f1['a'], f1['b'], f1['counter']))
    empty_hand(ctx)
    use_center(ctx, VALVE, 'up', [VALVE[0] + 0.5, Y, FZ + 2.5])
    window(ctx, 40, 'stage6-valve-open')
    f2 = fluid_state(ctx)
    moved = f2['b'] == BUCKETS * BUCKET_MB and f2['b_type'] == WATER_ID and f2['a'] == 0
    rows.check(FL + '.line', moved, 'valve open %s; barrel A %s -> %s, barrel B %s -> %s (type %s) (want 0 and %d water)'
               % (f2['valve'], f1['a'], f2['a'], f1['b'], f2['b'], f2['b_type'], BUCKETS * BUCKET_MB))
    rows.check(FC + '.counter', f2['counter'] == BUCKETS * BUCKET_MB, 'counter %s (want %d)' % (f2['counter'], BUCKETS * BUCKET_MB))
    rows.check(FP + '.line', moved and cons(data(ctx, A1)) == [A2], 'barrel B %s mB arrived; the only path is the long pipe A1-A2 %s'
               % (f2['b'], cons(data(ctx, A1))))
    window(ctx, 20, 'stage6-fluid-still')
    f3 = fluid_state(ctx)
    if f3 != f2:
        raise RuntimeError('the fluid line does not hold still before leaving: %s then %s' % (f2, f3))
    return dict(state=f3, anchors={p: (cons(data(ctx, p)), data(ctx, p).get('Type')) for p in (A1, A2, A3)}, f0=f0)


def reload_fluid(ctx, rows, before):
    f = fluid_state(ctx)
    b = before['state']
    rows.check(FL + '.reload', all(f[k] == b[k] for k in ('a', 'a_type', 'a_mode', 'b', 'b_type', 'b_mode')) and b['b'] == BUCKETS * BUCKET_MB,
               'before %s, after %s' % ({k: b[k] for k in ('a', 'a_type', 'a_mode', 'b', 'b_type', 'b_mode')},
                                        {k: f[k] for k in ('a', 'a_type', 'a_mode', 'b', 'b_type', 'b_mode')}))
    rows.check(FC + '.reload', f['valve'] and f['counter_open'] and f['counter'] == b['counter'] == BUCKETS * BUCKET_MB,
               'valve open %s, counter valve open %s, counter %s/%s (before/after)' % (f['valve'], f['counter_open'], b['counter'], f['counter']))
    anchors = {p: (cons(data(ctx, p)), data(ctx, p).get('Type')) for p in (A1, A2, A3)}
    rows.check(FP + '.reload', anchors == before['anchors'], 'anchors (pipes, type) before %s, after %s' % (before['anchors'], anchors))
