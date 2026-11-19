"""Mainline stage 4 (assembly and chemistry) as one line played by a player, powered by a wood burner over red cable.

The line: a wood burner (placed by hand, logs loaded in its screen, switched on there) feeds a red cable bus under the
ground; every machine hangs on the bus. The assembly machine builds the shredder, the shredder grinds ingots and ores, the
crafting table makes the circuit parts, the electric furnace and the mixer, the soldering station solders analog boards,
the assembly machine builds the chemical plant (and hazmat cloth from the shredded lead), the chemical plant makes hydrogen
peroxide from bucketed water; two steel barrels on typed fluid ducts at the plant's north ports take its peroxide and the
hydrogen it then makes from coal and water, and feed both back into its input tanks for the coltan cleaning; shredded
limestone becomes cement on the crafting table and smooth concrete in the plant, and a block of it is placed. The electric
furnace smelts ore and the mixer presses sunflower oil. The tail of the line is
played after the oil stage (start items of the infrastructure stage): the assembly machine builds the arc furnace, which
melts sand into silicon nuggets, a microchip from a printed silicon wafer, the centrifuge element and the centrifuge, which
separates lead ore; the ore acidizer takes the plant's peroxide through its corner port and crystallises an ore.
Afterwards the world is left and opened again and the same server readings are compared.

Power: before each measured window the burner is switched on and the world sprints until every machine's buffer is full
(or holds what the window needs), then the burner is switched off. In the window the line runs on stored energy alone (a
switched-off burner still hands its buffer to the cable, MachineWoodBurnerBlockEntity.java:96-98, but makes nothing), so
the line's stored energy (burner + every machine buffer) drops by exactly what the recipe spends. The power and fluid nets
keep moving energy and fluid on the server tick event while the world is frozen (NtmEventHandler.java:69-76) until their
provider and receiver entries are 3,000 ms old (PowerNetMK2.java:22,42,61; FluidNetMK2.java:17,59,76; NodeNet.java:27,32):
readings of several blocks that belong together are taken 80 client ticks (4 s) after the last server tick.

Expected values come from the NEO code, which ports the 1.7.10 original; each expectation names both. Tick counts:
- assembly machine and chemical plant (ModuleMachineBase.process, original ModuleMachineBase.java:115-131): a tick with
  power >= recipe power adds 1/duration (a double) to progress and takes the recipe power; the item appears in the tick the
  sum reaches 1. The sum is simulated here in the same double arithmetic.
- shredder (MachineShredderBlockEntity.java:93-111; original TileEntityMachineShredder.java:236-281): every running tick
  costs 5 HE, every 60th running tick each input slot gives up one item and both blades take one point of damage.
- soldering station (original TileEntityMachineSolderingStation.java:93-118), electric furnace (original
  TileEntityMachineElectricFurnace.java:145-180), centrifuge, mixer: integer progress, one per tick with enough power.
- arc furnace (MachineArcFurnaceBlockEntity.java:136-155, original TileEntityMachineArcFurnaceLarge.java:120-155): the lid
  closes by 1/60 a tick and the progress grows by 1F/400 a tick, both in float arithmetic, simulated here.
- ore acidizer (MachineCrystallizerBlockEntity.java:156-168, original TileEntityMachineCrystallizer.java:88-99): the item
  comes when progress exceeds the duration (600), 1,000 HE per progress tick.
Readings are server data (`data get block` / `data get entity`), never the client copy.
"""
import json
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import _lib  # noqa: E402
import common  # noqa: E402

FEATURES = ['basic-assembly', 'shredder', 'electrical-components', 'soldering-chain', 'electric-furnace', 'arc-furnace',
            'silicon-chips', 'chemical-plant', 'centrifuge', 'crystallization', 'fluid-mixing', 'fluid-compression',
            'coltan-niobium', 'recipe-completion', 'concrete']

SCENARIO = dict(
    id='basic-assembly.mainline_stage4',
    feature='basic-assembly',
    features=FEATURES,
    title='Mainline stage 4: wood-burner line with assembly machine, shredder, circuits, soldering, chemical plant (peroxide, '
          'coltan cleaning from two barrels, concrete), furnaces, mixer, arc furnace, centrifuge and ore acidizer',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

Y = -60            # machines stand on the flat world's grass at y = -61; the cable bus runs in the grass layer
OX, OZ = 3000, 3000
BUS_Z = OZ + 6
BUS_X = (OX - 10, OX + 56)
BX = OX - 8        # wood burner
X_ASSEMBLER, X_SHREDDER, X_TABLE, X_SOLDER, X_PLANT, X_EFURNACE, X_MIXER, X_ARC, X_CENTRIFUGE = (
    OX, OX + 6, OX + 9, OX + 12, OX + 17, OX + 26, OX + 29, OX + 36, OX + 41)
X_BURNER2, X_COMPRESSOR = OX + 47, OX + 52
WATER_ID = 1             # Fluids.java:250-251 (NONE first, WATER second)
LOGS = 64
LOG_TICKS = 300 * 4      # ModuleBurnTime: vanilla log burn time 300 x setLogTimeMod(4.0) (MachineWoodBurnerBlockEntity.java:52-54)
BURNER_MAX = 100_000     # MachineWoodBurnerBlockEntity.java:42 (original TileEntityMachineWoodBurner.java:40)
BURNER_GEN = 100         # MachineWoodBurnerBlockEntity.java:43 (original TileEntityMachineWoodBurner.java:49)
PEROXIDE_ID = 35         # Fluids.java:285: PEROXIDE is the 36th FluidType registered (registerSelf gives the registration index)
HYDROGEN_ID = 38         # Fluids.java:288, the 39th FluidType registered
SUNFLOWEROIL_ID = 111    # Fluids.java:361, the 112th FluidType registered
ARC_NEED, CRYSTAL_NEED = 410_000, 610_000

# Items earlier stages hand over at the start of stage 4 (world-generation blocks marked block:). The scene gives the ones
# its line needs; EXTRA lists what it gives beyond this list and why.
START_ITEMS = [
    'block:hbmsntm:ore_oil', 'hbmsntm:arc_electrode_graphite', 'hbmsntm:ball_fireclay', 'hbmsntm:cinnabar', 'hbmsntm:coil_copper',
    'hbmsntm:coil_copper_ring', 'hbmsntm:coil_tungsten', 'hbmsntm:furnace_combination', 'hbmsntm:heat_boiler',
    'hbmsntm:heater_firebox', 'hbmsntm:ingot_aluminium', 'hbmsntm:ingot_beryllium', 'hbmsntm:ingot_copper',
    'hbmsntm:ingot_dura_steel', 'hbmsntm:ingot_firebrick', 'hbmsntm:ingot_lead', 'hbmsntm:ingot_raw@41',
    'hbmsntm:ingot_red_copper', 'hbmsntm:ingot_steel', 'hbmsntm:ingot_titanium', 'hbmsntm:ingot_tungsten',
    'hbmsntm:machine_blast_furnace', 'hbmsntm:machine_crucible', 'hbmsntm:machine_press', 'hbmsntm:mold_base', 'hbmsntm:motor',
    'hbmsntm:nugget_beryllium', 'hbmsntm:ore_asbestos', 'hbmsntm:ore_beryllium', 'hbmsntm:ore_cobalt', 'hbmsntm:ore_lead',
    'hbmsntm:ore_lead_deepslate', 'hbmsntm:ore_titanium_deepslate', 'hbmsntm:ore_uranium', 'hbmsntm:pipe_copper',
    'hbmsntm:pipe_steel', 'hbmsntm:plate_cast@0', 'hbmsntm:plate_cast@11', 'hbmsntm:plate_cast@12', 'hbmsntm:plate_cast@5',
    'hbmsntm:plate_copper', 'hbmsntm:plate_dura_steel', 'hbmsntm:plate_iron', 'hbmsntm:plate_polymer', 'hbmsntm:plate_steel',
    'hbmsntm:plate_titanium', 'hbmsntm:powder_aluminium', 'hbmsntm:resource_limestone', 'hbmsntm:shell_steel', 'hbmsntm:shell_titanium',
    'hbmsntm:stamp_stone_flat', 'hbmsntm:steel_scaffold', 'hbmsntm:sulfur', 'hbmsntm:wire_copper', 'hbmsntm:wire_gold',
    'hbmsntm:wire_lead', 'hbmsntm:wire_red_copper', 'hbmsntm:wire_tungsten',
]
# The tail is played after the oil stage: it takes its items from the list the infrastructure stage starts with.
TAIL_ITEMS = [
    'hbmsntm:arc_electrode_graphite', 'hbmsntm:circuit_analog_board', 'hbmsntm:circuit_printed_silicon_wafer',
    'hbmsntm:concrete_smooth', 'hbmsntm:ingot_firebrick', 'hbmsntm:ingot_polymer', 'hbmsntm:machine_crystallizer', 'hbmsntm:motor',
    'hbmsntm:ore_lead_deepslate', 'hbmsntm:plate_cast@11', 'hbmsntm:plate_copper', 'hbmsntm:plate_polymer',
    'hbmsntm:plate_steel', 'hbmsntm:plate_titanium', 'hbmsntm:transformer', 'hbmsntm:wire_gold',
]
EXTRA = {
    'hbmsntm:machine_assembly_machine': 'a stage-4 item built on the steel anvil (AnvilRecipes construction); handed out instead of the anvil screen',
    'hbmsntm:machine_soldering_station': 'a stage-4 item built on the steel anvil (AnvilRecipes construction); handed out instead of the anvil screen',
    'hbmsntm:machine_wood_burner': 'stage-3 machine (crafted there), the line\'s generators (two)',
    'hbmsntm:red_cable': 'stage-3 item (crafted there), the cable bus, laid as blocks',
    'hbmsntm:blades_steel': 'stage-2 item (crafted), the shredder\'s blades',
    'hbmsntm:ore_coltan': 'world-generation block (coltan deposit), mined',
    'hbmsntm:ore_aluminium': 'world-generation block, mined; no mainline recipe consumes it, so the hand-over list does not name it; '
                             'the shredder and crystallizer rows take it',
    'hbmsntm:plate_dura_steel': 'stage-2 item of the stage-4 list, for the centrifuge element in the tail',
    'hbmsntm:fluid_identifier_multi': 'the mixer\'s identifier, given with its fluid 预写 (see PREWRITTEN); the compressor\'s '
                                      'identifier is crafted in the line (dye, vacuum tube, iron plate) and set in its own screen',
    'minecraft:blue_dye': 'vanilla, for the crafted fluid identifier',
    'hbmsntm:barrel_steel': 'crafted in the line (6 steel plates, 2 steel ingots), for the compressor\'s water; the two barrels of '
                            'the coltan cleaning are given (the same stage-2 recipe)',
    'hbmsntm:fluid_duct_neo': 'stage-6 item (crafting table: 4 steel plates + 2 aluminium plates -> 8, stage-1/2 inputs), laid as '
                              'blocks like the cable and typed by hand with the identifiers',
    'minecraft:coal': 'vanilla, for the hydrogen and the shredded coal powder', 'minecraft:clay_ball': 'vanilla, for the cement',
    'minecraft:gravel': 'vanilla, for the concrete',
    'minecraft:oak_log': 'vanilla fuel of both burners', 'minecraft:crafting_table': 'vanilla', 'minecraft:glass_pane': 'vanilla',
    'minecraft:string': 'vanilla', 'minecraft:water_bucket': 'vanilla', 'minecraft:furnace': 'vanilla', 'minecraft:sand': 'vanilla',
    'minecraft:sunflower': 'vanilla', 'minecraft:stick': 'vanilla, keeps the hotbar slots occupied',
}
PREWRITTEN = ['预写 the mixer\'s fluid identifier is given set to sunflower oil (custom data Fluid1 = %d): the identifier\'s own '
              'screen selects a fluid by typed search text beyond the first nine entries (FluidScreen), and the executor has '
              'no typed-character input' % SUNFLOWEROIL_ID,
              '预写 the coltan cleaning\'s two fluid identifiers are given set to hydrogen peroxide (Fluid1 = %d) and hydrogen (Fluid1 = %d), '
              'for the same reason; they type the ducts and the barrels by hand' % (PEROXIDE_ID, HYDROGEN_ID)]



def expectations():
    E = [
        # basic-assembly
        ('basic-assembly.power-line',
         'wood burner placed by hand, %d logs in its fuel slot, switched on in its screen, red cable under the ground to the '
         'assembly machine (no battery): the machine fills to its 100,000 HE (max(100 x 100, 100,000)); the line\'s stored energy '
         'equals 100 HE x the ticks burned (1,200 per log), less at most 99 HE the burner clips at its own 100,000 cap' % LOGS,
         'MachineWoodBurnerBlockEntity.java:42-43,113,123-141, MachineAssemblyMachineBlockEntity.java:97-103 (original '
         'TileEntityMachineWoodBurner.java:40,49,96-121, TileEntityMachineAssemblyMachine.java:105-112)'),
        ('basic-assembly.shredder-build',
         'assembly machine placed by hand, ass.shredder picked in the recipe selector, 8 steel plates + 4 copper plates + 2 motors '
         'shift-clicked in: no shredder after 99 ticks, 1 shredder and empty inputs at tick 100 (100 ticks, 100 HE/t); the line\'s '
         'stored energy drops by 10,000 HE',
         'AssemblyMachineRecipes.java:254-257, ModuleMachineBase.java:115-128 (original AssemblyMachineRecipes.java:259-260, '
         'ModuleMachineBase.java:115-131)'),
        ('basic-assembly.chemplant-build',
         'ass.chemplant: 8 steel ingots + 2 copper pipes + 16 polymer plates + 2 motors + 2 tungsten coils + 1 analog board from '
         'the soldering station: no plant after 199 ticks, 1 chemical plant at tick 200 (200 ticks, 100 HE/t); stored energy -20,000 HE',
         'AssemblyMachineRecipes.java:359-365 (original AssemblyMachineRecipes.java:264-265)'),
        ('basic-assembly.reload', 'after leaving and opening the world: the burner (fuel, burn time, switch) and the assembly '
         'machine (recipe, stored power, slots) read the same', 'MachineWoodBurnerBlockEntity.java, MachineAssemblyMachineBlockEntity.java:264-282'),
        ('basic-assembly.overview', 'picture of the finished line (for a person)', 'review'),
        # shredder
        ('shredder.batch',
         'shredder from the assembly machine placed by hand, full buffer; 2 steel blades, 2 aluminium ingots, 2 lead ores, 1 coltan '
         'ore shift-clicked in: nothing at tick 59; at tick 60 one round (1 aluminium powder, 2 lead powder, 2 crushed coltan ore, '
         'blades 1 damage); at tick 120 two rounds (2 aluminium powder, 4 lead powder, inputs empty, blades 2 damage); stored '
         'energy -600 HE (5 x 120)',
         'MachineShredderBlockEntity.java:28,93-111, ShredderRecipes.java:105-129,263 (original TileEntityMachineShredder.java:35,'
         '247-260, ShredderRecipes.java:62-66: ingot -> 1 dust, ore -> 2 dust)'),
        ('shredder.ore-aluminium',
         'one aluminium ore through the shredder gives 2 cryolite chunks (the original\'s explicit row wins over the ore rule)',
         'original ShredderRecipes.java:211 (registerDefaults runs before registerPost, SerializableRecipe.java:148,160; setRecipe '
         'keeps the first row, :417-421); NEO ShredderRecipes.java:166-182,459-470'),
        ('shredder.reload', 'after leaving and opening the world: shredder power, blade damage and slots read the same',
         'MachineShredderBlockEntity.java'),
        # electrical-components
        ('electrical-components.vacuum-tube',
         'crafting table: 7 glass panes over 7 tungsten wires over 7 polymer plates, shift-click on the result: 7 vacuum tubes',
         'NtmRecipeProvider.java:317-325 (original CraftingManager.java:113)'),
        ('electrical-components.printed-board',
         'crafting table: 8 polymer plates over 8 copper plates: 8 printed circuit boards',
         'NtmRecipeProvider.java:247-254 (original CraftingManager.java:122)'),
        ('electrical-components.capacitor',
         'crafting table: polymer / shredded aluminium powder / polymer over copper wire _ copper wire, two crafts: 4 capacitors '
         'from 4 polymer plates, 2 aluminium powder, 4 copper wires',
         'NtmRecipeProvider.java:263-271 (original CraftingManager.java:119)'),
        # soldering-chain
        ('soldering-chain.analog-board',
         'soldering station placed by hand; 6 vacuum tubes, 4 capacitors, 8 printed boards, 8 lead wires shift-clicked in: no '
         'board at tick 99, 1 analog board at tick 100, 2 at tick 200 with all inputs used (100 ticks, 100 HE/t each); stored energy -20,000 HE',
         'SolderingRecipes.java:33-48, MachineSolderingStationBlockEntity.java:73-125 (original SolderingRecipes.java:44-52, '
         'TileEntityMachineSolderingStation.java:93-118)'),
        ('soldering-chain.reload', 'after leaving and opening the world: soldering station power and slots read the same',
         'MachineSolderingStationBlockEntity.java:296-322'),
        # chemical-plant
        ('chemical-plant.peroxide',
         'chemical plant from the assembly machine placed by hand, chem.peroxide picked in the selector, 2 water buckets clicked '
         'into the fluid slot: 2,000 mB water and 2 empty buckets; then 1,000 mB water + 1,000 mB peroxide (type %d) at tick 50, '
         '2,000 mB peroxide and no water at tick 100 (50 ticks, 100 HE/t, 1,000 mB water -> 1,000 mB peroxide); stored energy -10,000 HE' % PEROXIDE_ID,
         'ChemicalPlantRecipes.java:214-216, MachineChemicalPlantBlockEntity.java:57-63 (original ChemicalPlantRecipes.java:288-290, '
         'TileEntityMachineChemicalPlant.java:105-126)'),
        ('chemical-plant.reload', 'after leaving and opening the world: the plant\'s recipe, tanks and power read the same',
         'MachineChemicalPlantBlockEntity.java:254-276'),
        # recipe-completion
        ('recipe-completion.hazcloth',
         'assembly machine, ass.hazcloth: the 4 lead powder from the shredder + 8 string: nothing at tick 49, 4 hazmat cloth at tick 50 '
         '(50 ticks, 100 HE/t); stored energy -5,000 HE', 'AssemblyMachineRecipes.java:483-485 (original AssemblyMachineRecipes.java:118-119)'),
        # electric-furnace
        ('electric-furnace.craft',
         'crafting table: 3 beryllium ingots / copper cast plate, furnace, copper cast plate / 3 tungsten coils: 1 electric furnace',
         'NtmRecipeProvider.java:515-524 (original CraftingManager.java:230)'),
        ('electric-furnace.smelt',
         'the crafted electric furnace placed by hand on the bus, full buffer; 2 lead ores shift-clicked in: nothing at tick 99, 1 lead '
         'ingot at tick 100, 2 at tick 200 (100 ticks, 50 HE/t); stored energy -10,000 HE',
         'MachineElectricFurnaceBlockEntity.java:50-54,86-120 (original TileEntityMachineElectricFurnace.java:42-43,145-180)'),
        ('electric-furnace.reload', 'after leaving and opening the world: electric furnace power and slots read the same',
         'MachineElectricFurnaceBlockEntity.java'),
        # coltan-niobium
        ('coltan-niobium.shred', 'coltan ore (world generation) through the shredder: 2 crushed coltan ore per ore',
         'ShredderRecipes.java:129 (original ShredderRecipes.java:66 with OreDictManager COLTAN.dust = powder_coltan_ore)'),
        ('coltan-niobium.cleaning',
         'two steel barrels placed by hand north of the chemical plant, each on one fluid duct at a plant port, ducts and barrels '
         'typed by hand with the identifiers (预写: peroxide, hydrogen); the plant\'s 2,000 mB peroxide goes into barrel P; '
         'chem.hydrogen with 8 water buckets and 1 coal makes 500 mB hydrogen (20 ticks, 400 HE/t) that goes into barrel H; 1 coal '
         'shredded into 1 coal powder; chem.coltancleaning picked and both barrels set to send: the plant\'s input tanks take '
         'peroxide (type %d) and hydrogen (type %d) from the barrels; 2 crushed coltan ore (from the shredder) + 1 coal powder '
         'clicked in: nothing at tick 59, at tick 60 1 purified tantalite, 1 niobium powder, 1 dust and 500 mB water, peroxide '
         '(plant + barrel) -250 mB, hydrogen -500 mB, inputs used (60 ticks, 100 HE/t); stored energy -6,000 HE' % (PEROXIDE_ID, HYDROGEN_ID),
         'ChemicalPlantRecipes.java:41-45,238-242, MachineChemicalPlantBlockEntity.java:68-71,101-123,209-224, ModuleMachineBase.java:40-44, '
         'BarrelBlockEntity.java:66-67,104-114,199-208, FluidDuctBaseBlock.java:52-80, ShredderRecipes.java:337 (original '
         'ChemicalPlantRecipes.java:45-48,317-321, ShredderRecipes.java:62 gem -> 1 dust)'),
        # concrete
        ('concrete.cement',
         'shredder: 1 limestone (stage-1 resource) shift-clicked in: nothing at tick 59, 4 limestone powder at tick 60; crafting table: '
         'the limestone powder + 3 clay balls, shift-click on the result: 4 cement, 1 limestone powder and 3 clay balls used',
         'ShredderRecipes.java:329, MachineShredderBlockEntity.java:93-111, NtmRecipeProvider.java:2580-2585 (original '
         'ShredderRecipes.java:175, PowderRecipes.java:36)'),
        ('concrete.line',
         'chemical plant: chem.concrete picked, 2 water buckets clicked in (2,000 mB water), the 4 cement + 8 gravel + 8 sand '
         'shift-clicked in: none at tick 99, 16 smooth concrete at tick 100 with the water, gravel and sand used and 3 cement left '
         '(100 ticks, 100 HE/t); stored energy -10,000 HE; one smooth concrete block placed by hand stands in the world (server)',
         'ChemicalPlantRecipes.java:126-129, ModuleMachineBase.java:115-128 (original ChemicalPlantRecipes.java:146-148)'),
        # fluid-mixing
        ('fluid-mixing.craft', 'crafting table: steel plate, Dura ingot, steel plate / glass pane, vacuum tube, glass pane / steel '
         'plate, motor, steel plate: 1 mixer', 'NtmRecipeProvider.java:2329-2337 (original CraftingManager mixer row)'),
        ('fluid-mixing.line',
         'the crafted mixer placed by hand on the bus, full buffer; the identifier (预写: sunflower oil) and 1 sunflower clicked '
         'in: no oil at tick 49, 100 mB sunflower oil (type %d) at tick 50 (50 ticks, 50 HE/t); stored energy -2,500 HE' % SUNFLOWEROIL_ID,
         'MixerRecipes.java:148, MachineMixerBlockEntity.java:115-125,145-176 (original MixerRecipes.java:53, TileEntityMachineMixer.java:85-104)'),
        ('fluid-mixing.reload', 'after leaving and opening the world: mixer power, identifier and output tank read the same',
         'MachineMixerBlockEntity.java'),
        # fluid-compression
        ('fluid-compression.build',
         'ass.compressor: 8 steel cast plates + 4 copper plates + 2 steel shells + 3 motors + the second analog board: no compressor '
         'after 199 ticks, 1 compressor at tick 200; stored energy -20,000 HE',
         'AssemblyMachineRecipes.java:259-265 (original AssemblyMachineRecipes.java:348)'),
        ('fluid-compression.line',
         'compressor placed by hand, cable at its west port; a crafted steel barrel at its east port, the crafted identifier set to '
         'water in its own screen, 1 water bucket and send mode in the barrel; a second wood burner on the bus, both burners and the '
         'compressor full (300,000 HE: a 2,500 HE/t window of 100 ticks is more than one 100,000 HE buffer); the identifier into the '
         'compressor (its input tank empty and untyped before): no output at ticks 99 and 100, 1,000 mB water at pressure 1 at tick '
         '101; stored energy -250,000 HE (2,500 x 100). Tick 101: in tick 1 the compressor takes the water type from the identifier '
         'before it tests canProcess (empty tank, no progress); the barrel hands its 1,000 mB over directly in its own tick, in tick 1 '
         'if it ticks after the compressor or in tick 2 before it, so with either block-entity order the first compressing tick is '
         'tick 2 and the 100th (progress >= 100, then process) is tick 101; this holds while the power net keeps the compressor\'s '
         'buffer above 2,500 HE (canProcess needs power > 2,500)',
         'MachineCompressorBlockEntity.java:55-58,86-96,126-137,172-185, FluidTank.java:141-151, BarrelBlockEntity.java:107-113, '
         'IFluidStandardSenderMK2.java:47-54, ProxyComboBlockEntity.java:209-225 (original TileEntityMachineCompressorBase.java:'
         '72-73,95-104,142-149: 2,500 HE/t, 100 ticks, pressure +1 for 1,000 mB without a special recipe)'),
        ('fluid-compression.reload', 'after leaving and opening the world: compressor power, tanks with pressure, identifier and the '
         'second burner read the same', 'MachineCompressorBlockEntity.java:290-300,360-372'),
        # arc-furnace (tail)
        ('arc-furnace.build',
         'tail: ass.arcfurnace: 12 smooth concrete + 8 polymer ingots + 16 firebricks + 8 steel cast plates + 1 transformer + 1 analog '
         'board: no furnace after 199 ticks, 1 arc furnace at tick 200; stored energy -20,000 HE',
         'AssemblyMachineRecipes.java:418-424 (original AssemblyMachineRecipes.java:286-288)'),
        ('arc-furnace.line',
         'arc furnace placed by hand, wired at its south port, buffer charged to at least %d HE by the burner; 3 graphite electrodes '
         'and 8 sand shift-clicked in (the sand enters the grid one per slot without upgrades): the lid closes in 61 ticks, 401 '
         'progress ticks follow (float sums), 8 silicon nuggets at tick 462 and none at 461; stored energy -401,000 HE (1,000 x 401)' % ARC_NEED,
         'ArcFurnaceRecipes.java:38, MachineArcFurnaceBlockEntity.java:90-92,104-106,136-155 (original ArcFurnaceRecipes.java:53, '
         'TileEntityMachineArcFurnaceLarge.java:120-145)'),
        ('arc-furnace.reload', 'after leaving and opening the world: arc furnace power, lid and slots read the same',
         'MachineArcFurnaceBlockEntity.java'),
        # silicon-chips (tail)
        ('silicon-chips.chip',
         'tail: ass.chip is listed in the selector (528 mode off by default) and makes 1 microchip from 1 polymer plate + 1 printed '
         'silicon wafer + 1 gold wire: none after 49 ticks, 1 at tick 50 (50 ticks, 250 HE/t); stored energy -12,500 HE',
         'AssemblyMachineRecipes.java:389-395 (original AssemblyMachineRecipes.java:127-128)'),
        # centrifuge (tail)
        ('centrifuge.build',
         'tail: ass.centrifugetower (4 Dura plates + 4 titanium plates + 1 motor) gives 1 centrifuge element at tick 100, then '
         'ass.centrifuge (element + 4 polymer ingots + 8 steel plates + 4 copper plates + 1 analog board) 1 centrifuge at tick 200; '
         'stored energy -10,000 and -20,000 HE',
         'AssemblyMachineRecipes.java:277-286 (original AssemblyMachineRecipes.java:151,279)'),
        ('centrifuge.line',
         'centrifuge placed by hand on the bus, full buffer; 1 deepslate lead ore shift-clicked in: nothing at tick 199; at tick 200 '
         '2 lead powder, 1 gold powder, 1 gravel (200 ticks, 200 HE/t); stored energy -40,000 HE',
         'CentrifugeRecipes.java:172, MachineCentrifugeBlockEntity.java:46-47,107-116 (original CentrifugeRecipes.java:120-124 '
         'without the lbs option, TileEntityMachineCentrifuge.java:55-56)'),
        ('centrifuge.reload', 'after leaving and opening the world: centrifuge power and slots read the same', 'MachineCentrifugeBlockEntity.java'),
        # crystallization (tail)
        ('crystallization.line',
         'tail: ore acidizer from the handover placed by hand east of the chemical plant, so the plant\'s corner port feeds its '
         'peroxide tank (default type peroxide; the plant, which ran other recipes since, makes 1,000 mB peroxide again from one '
         'water bucket when its output holds less than 500 mB); buffer charged to at least %d HE; 1 aluminium ore shift-clicked in: nothing at '
         'tick 600, 1 aluminium crystal at tick 601 with 500 mB peroxide used and the ore used (no effect upgrade); stored energy '
         '-601,000 HE (1,000 x 601). The acidizer\'s tank drops by exactly 500 mB only because no peroxide can follow in the window: '
         'at its start the plant\'s output tanks hold no peroxide and its input tanks no water (its tanks i0-i2 and o0-o2 read from '
         'server data; the plant hands only output tanks over and makes peroxide only from water)' % CRYSTAL_NEED,
         'CrystallizerRecipes.java:60-61,174-179,198, MachineCrystallizerBlockEntity.java:69-71,93,156-168,236-256, '
         'MachineChemicalPlantBlockEntity.java:104-123,265-270, ChemicalPlantRecipes.java:214-216 (original '
         'CrystallizerRecipes.java:56,75, TileEntityMachineCrystallizer.java:45,88-99,271-274, ChemicalPlantRecipes.java:288-290)'),
        ('crystallization.reload', 'after leaving and opening the world: acidizer power, tank and slots read the same',
         'MachineCrystallizerBlockEntity.java'),
    ]
    return [dict(id=i, text=t, source=s) for i, t, s in E]


# ---------------------------------------------------------------- helpers (candidates for _lib.py)

def cmd(ctx, command, **kw):
    return ctx.step('cmd', command=command, **kw)


def f32(x):
    return struct.unpack('f', struct.pack('f', x))[0]


def module_ticks(duration, cycles=1):
    """ModuleMachineBase.process: progress += min(1 / duration, 1) in double arithmetic each running tick; the item comes in the
    tick the sum reaches 1, then progress -= 1 when the next cycle can run. Returns the completion ticks."""
    p, t, out = 0.0, 0, []
    while len(out) < cycles:
        t += 1
        p += min(1.0 / duration, 1.0)
        if p >= 1.0:
            out.append(t)
            p = p - 1.0 if len(out) < cycles else 0.0
    return out


def arc_ticks():
    """MachineArcFurnaceBlockEntity.java:136-155 without upgrades, from an open lid (1F): lid = (float)(lid - 1F / 60.0) until it
    is not above 0, then progress = progress + 1F/400 in float until >= 1F. Returns (lid ticks, progress ticks)."""
    lid, close = 1.0, 0
    while lid > 0:
        close += 1
        lid = f32(lid - 1.0 / 60.0)
        if lid < 0:
            lid = 0.0
    p, n, step = 0.0, 0, f32(1.0 / 400)
    while p < 1.0:
        n += 1
        p = f32(p + step)
    return close, n


def inventory(ctx):
    """The player's inventory from server data: {NBT slot: item compound} (0-8 hotbar, 9-35 main)."""
    r = ctx.server('data get entity @p Inventory')
    lines = [m for m in r['messages'] if m.strip()]
    items = _lib.data_value(lines[-1]) if lines else []
    return {int(i['Slot']): i for i in items}


def count(inv, item):
    return sum(i.get('count', 1) for i in inv.values() if i.get('id') == item)


def slots_of(inv, item):
    return sorted(s for s, i in inv.items() if i.get('id') == item)


def menu_index(base, nbt_slot):
    """Menu slot of a player inventory slot in MenuBase.playerInv (main rows first, then the hotbar) and vanilla CraftingMenu."""
    return base + 27 + nbt_slot if nbt_slot < 9 else base + nbt_slot - 9


def items_of(data):
    """{slot: (id, count)} of a block entity's Items list."""
    return {int(i['Slot']): (i.get('id'), i.get('count', 1)) for i in data.get('Items', [])}


def item_at(data, slot):
    for i in data.get('Items', []):
        if int(i['Slot']) == slot:
            return i
    return None


def n_of(data, slot, item):
    i = item_at(data, slot)
    return 0 if i is None or i.get('id') != item else i.get('count', 1)


def put(ctx, k, item, n=1):
    cmd(ctx, 'item replace entity @s inventory.%d with %s %d' % (k, item, n))


def server_steps(ctx, n):
    """`tick step n` in the frozen world, waiting until the server's game time moved n ticks."""
    t0 = ctx.server()['game_time']
    ctx.server('tick step %d' % n)
    for _ in range(200):
        ctx.step('wait', ticks=2)
        if ctx.server()['game_time'] >= t0 + n:
            return
    raise RuntimeError('tick step %d did not finish' % n)


def advance_to(ctx, t0, target, label):
    """Runs the frozen world on until `target` ticks have passed since game time t0 (a sprint from the frozen world runs one
    tick more than asked, so it asks for one less; a single tick is a tick step)."""
    need = target - (ctx.server()['game_time'] - t0)
    if need >= 2:
        ctx.sprint(need - 1, label=label, poll_s=0.3, timeout_s=600)
    elif need == 1:
        server_steps(ctx, 1)
    got = ctx.server()['game_time'] - t0
    if got != target:
        raise RuntimeError('%s: %d ticks since start, wanted %d' % (label, got, target))


def shift_click(ctx, index):
    ctx.step('mod', shift=True)
    try:
        ctx.step('click', slot=index, after=3)
    finally:
        ctx.step('mod', shift=False)


def move(ctx, a, b):
    ctx.step('click', slot=a, after=2)
    ctx.step('click', slot=b, after=2)


def select_hotbar(ctx, h):
    ctx.step('key', key='key.keyboard.%d' % (h + 1), after=2)


HAND = 8   # the hotbar slot items are placed from; the other hotbar slots hold sticks, so shift-clicked products go to the
           # main inventory (MenuBase.quickMoveStack and CraftingMenu fill the player slots from the hotbar's right end)


def stock(ctx, pairs):
    """Gives start items into the lowest empty main-inventory slots (products of earlier sections sit at the top end);
    returns their NBT slots."""
    inv = inventory(ctx)
    free = [s for s in range(9, 36) if s not in inv]
    if len(free) < len(pairs):
        raise RuntimeError('player inventory full: %d free slots for %d stacks' % (len(free), len(pairs)))
    out = []
    for s, (item, n) in zip(free, pairs):
        put(ctx, s - 9, item, n)
        out.append(s)
    return out


def hand_air(ctx, h=HAND):
    cmd(ctx, 'item replace entity @s hotbar.%d with minecraft:air' % h)


def place(ctx, x, z, block, h=4, dz=4.5, hand=HAND, r=3):
    """Places the block item in hotbar slot `hand` by hand onto the ground at (x, Y-1, z), the player looking north from
    `dz` blocks south; returns (core, facing) as the client sees the block states (positions only; readings are server data)."""
    select_hotbar(ctx, hand)
    ctx.step('view', pos=[x + 0.5, Y + 1, z + dz], look_at=[x + 0.5, Y - 0.5, z + 0.5], fly=True, hide_gui=True)
    ctx.step('use', target=dict(pos=[x, Y - 1, z], face='up'), after=8)
    d = ctx.step('dump', **{'from': [x - r, Y, z - r], 'to': [x + r, Y + h, z + r]})
    cores = [(tuple(int(c) for c in b['pos']), b['props'].get('facing')) for b in d['blocks']
             if b['block'] == block and b['props'].get('type', 'core') == 'core']
    if len(cores) != 1:
        raise RuntimeError('%s: expected one core after placing, found %s' % (block, cores))
    # creative placement keeps the item: take it away as survival placement would
    cmd(ctx, 'item replace entity @s hotbar.%d with minecraft:stick' % hand)
    select_hotbar(ctx, 0)
    return cores[0]


def open_block(ctx, pos, screen, face='south', back=3.5, up=0.5):
    """Right-click on the block with a stick (no use of its own) selected, then waits for the screen."""
    select_hotbar(ctx, 0)
    x, y, z = pos
    if face == 'up':
        ctx.step('view', pos=[x + 0.5, y + 1.6, z + 0.5 + back], look_at=[x + 0.5, y + 1.0, z + 0.5], fly=True, hide_gui=True)
    else:
        ctx.step('view', pos=[x + 0.5, y + up + 0.7, z + 0.5 + back], look_at=[x + 0.5, y + 0.5, z + 1.0], fly=True, hide_gui=True)
    ctx.step('use', target=dict(pos=list(pos), face=face), after=6)
    ctx.step('screen', expect=screen)


def open_any(ctx, pos, screen, face='south', back=3.5, up=0.5):
    """Right-click aimed through `face` towards the middle of the block at `pos`, any block of the machine accepted (multiblock
    parts whose outline is smaller than the cell); then waits for the screen."""
    select_hotbar(ctx, 0)
    d = _lib.VEC[face]
    x, y, z = pos
    eye = [x + 0.5 + d[0] * back, y + up, z + 0.5 + d[2] * back]
    ctx.step('view', pos=eye, look_at=[x + 0.5 + 0.05 * d[0], y + 0.5, z + 0.5 + 0.05 * d[2]], fly=True, hide_gui=True)
    ctx.step('use', target=dict(pos=list(pos), face=face, offset=[-0.449 * d[0], 0.0, -0.449 * d[2]]), any_hit=True, after=6)
    ctx.step('screen', expect=screen)


def recipe_index(file_name, name, client):
    """Index of a recipe among the selector's entries: the recipe list in registration order (the client writes it as the
    `_<file>` template on start-up, SerializableRecipe) without the blueprint-pool rows (RecipeSelectorScreen.regenerateRecipes)."""
    path = common.CLIENTS / client / 'config' / 'hbmRecipes' / ('_' + file_name)
    rows = json.loads(path.read_text(encoding='utf-8'))['recipes']
    names = [r['name'] for r in rows if not r.get('blueprintpool')]
    return (names.index(name) if name in names else None), len(names)


def pick_recipe(ctx, core, file_name, name, label_key):
    """In an open machine screen: the recipe button (GUI 7,125), then the selector (RecipeSelectorScreen): Enter leaves the
    search box, Page Down / Down scroll by 5 / 1 rows, the entry is hovered (its tooltip must name the recipe) and clicked,
    and the close button sends the choice. Returns the server's recipe0 afterwards."""
    idx, n = recipe_index(file_name, name, ctx.default)
    if idx is None:
        raise RuntimeError('%s is not in the selector list (%d entries)' % (name, n))
    want = ctx.step('i18n', keys=[label_key])['texts'][label_key]
    hud = ctx.step('hud', frames=2)
    ctx.step('click', at=[hud['gui_left'] + 16, hud['gui_top'] + 134], after=4)
    ctx.step('screen', expect='RecipeSelectorScreen')
    hud = ctx.step('hud', frames=2)
    left, top = (hud['gui_scaled_width'] - 176) // 2, (hud['gui_scaled_height'] - 132) // 2
    size = max(0, math.ceil((n - 40) / 8.0))
    page = min(idx // 8, size)
    ctx.step('key', key='key.keyboard.enter', after=1)
    for _ in range(page // 5):
        ctx.step('key', key='key.keyboard.page.down', after=1)
    for _ in range(page % 5):
        ctx.step('key', key='key.keyboard.down', after=1)
    ind = idx - page * 8
    at = [left + 7 + 18 * (ind % 8) + 9, top + 17 + 18 * (ind // 8) + 9]
    ctx.step('hover', at=at, frames=3)
    tips = [t['text'] for t in ctx.step('hud', frames=3)['texts'] if t['text'].startswith('tooltip: ')]
    if not tips or want not in tips[0]:
        raise RuntimeError('selector entry %d (page %d) is %r, not %s (%r)' % (idx, page, tips[:1], name, want))
    ctx.step('click', at=at, after=2)
    ctx.step('click', at=[left + 160, top + 98], after=4)
    return _lib.block_data(ctx, core).get('recipe0')


KEEP = ('power', 'maxPower', 'recipe0', 'progress0', 'progress', 'burnTime', 'maxBurnTime', 'isOn', 'lid', 'delay', 'recipe',
        'compression', '0_p', '1_p', 'mode')


def snapshot(ctx, pos):
    """The readings compared across leaving and opening the world."""
    data = _lib.block_data(ctx, pos)
    keep = {k: data[k] for k in KEEP if k in data}
    keep['tanks'] = _lib.tanks(data)
    keep['items'] = sorted((int(i['Slot']), i.get('id'), i.get('count', 1), json.dumps(i.get('components', {}), sort_keys=True))
                           for i in data.get('Items', []))
    return keep


# ---------------------------------------------------------------- the power line

def lay_cable(ctx, riser, x, z0):
    """A riser cable at (x, Y, z0) when `riser` (a machine port beside the machine), then cable in the grass layer from
    (x, Y-1, z0) south to the bus."""
    if riser:
        r = ctx.server('execute if block %d %d %d minecraft:air' % (x, Y, z0), allow_error=True)
        if r['result'] != 1:
            raise RuntimeError('cable cell %s is not free: %s' % ((x, Y, z0), r['messages']))
        cmd(ctx, 'setblock %d %d %d hbmsntm:red_cable' % (x, Y, z0))
    cmd(ctx, 'fill %d %d %d %d %d %d hbmsntm:red_cable' % (x, Y - 1, z0, x, Y - 1, BUS_Z))


def power_of(ctx, pos):
    return _lib.block_data(ctx, pos).get('power', 0)


def full_of(data, need=None):
    """The buffer a charge waits for: `need`, else the machine's own maxPower (saved by the assembly machine, chemical plant,
    shredder and soldering station), else the fixed capacities (electric furnace, centrifuge 100,000; mixer 10,000)."""
    if need is not None:
        return need
    if 'maxPower' in data:
        return data['maxPower']
    return {'hbmsntm:machine_mixer': 10_000}.get(data.get('id'), 100_000)


def still(ctx):
    """Freezes the world and waits 80 client ticks (4 s of wall time). A frozen server still fires the server tick event that
    updates the power and fluid nets (NtmEventHandler.java:69-76); their provider and receiver entries are dropped only 3,000 ms
    after the last refresh by a ticking block entity (PowerNetMK2.java:22,42,61; FluidNetMK2.java:17,59,76; NodeNet.java:27,32).
    After the wait nothing moves, so readings of several blocks taken one after another belong together."""
    ctx.server('tick freeze')
    ctx.step('wait', ticks=80)


def stored(ctx, line):
    """The line's stored energy: the burner's buffer and every machine buffer on the bus, read once the nets are still."""
    still(ctx)
    parts = {k: power_of(ctx, p) for k, p in line['nodes'].items()}
    parts['burner'] = power_of(ctx, line['burner'])
    for i, b in enumerate(line.get('more_burners', [])):
        parts['burner%d' % (i + 2)] = power_of(ctx, b)
    return sum(parts.values()), parts


def burner_set(ctx, line, on, pos=None):
    """Switches a wood burner with the button in its screen (GUI 53,17, 16x15; MachineWoodBurnerBlockEntity.receiveControl)."""
    pos = pos or line['burner']
    d = _lib.block_data(ctx, pos)
    if bool(d.get('isOn')) == on:
        return
    open_block(ctx, pos, 'MachineWoodBurnerScreen', back=2.5, up=0.0)
    hud = ctx.step('hud', frames=2)
    ctx.step('click', at=[hud['gui_left'] + 61, hud['gui_top'] + 24], button=0, after=4)
    ctx.step('close')
    if bool(_lib.block_data(ctx, pos).get('isOn')) != on:
        raise RuntimeError('the burner at %s did not switch %s' % (pos, 'on' if on else 'off'))


def charge(ctx, line, label, needs=None, burners=None):
    """Burner on, sprint until every machine on the bus holds its full buffer (or `needs[pos]`), burner off. `burners`: more
    burners switched on with it, which must also fill their own 100,000 HE."""
    needs = needs or {}
    burners = burners or []
    burner_set(ctx, line, True)
    for b in burners:
        burner_set(ctx, line, True, b)

    def full(c):
        for k, p in line['nodes'].items():
            d = _lib.block_data(c, p)
            if d.get('power', 0) < full_of(d, needs.get(p)):
                return False
        return all(power_of(c, b) >= BURNER_MAX for b in burners)

    ctx.server('tick freeze')
    rec = ctx.sprint(40000, until=full, poll_s=0.5, label='charge-' + label, timeout_s=600)
    ctx.server('tick freeze')
    burner_set(ctx, line, False)
    for b in burners:
        burner_set(ctx, line, False, b)
    if not full(ctx):
        raise RuntimeError('charge %s: buffers not full after %s ticks' % (label, rec.get('advanced')))
    return rec


def burned(ctx, line):
    """Ticks the burner has burned: 1,200 per log taken from the fuel slot, less what is left of the current log."""
    d = _lib.block_data(ctx, line['burner'])
    left = sum(i.get('count', 1) for i in d.get('Items', []) if int(i['Slot']) == 0 and i.get('id') == 'minecraft:oak_log')
    return LOG_TICKS * (LOGS - left) - d.get('burnTime', 0), d


# ---------------------------------------------------------------- the line

def run(ctx):
    _lib.setup_world(ctx)
    cmd(ctx, 'clear @s', allow_error=True)
    for h in range(9):
        cmd(ctx, 'item replace entity @s hotbar.%d with minecraft:stick' % h)
    _lib.go_near(ctx, OX + 17, Y, OZ)
    # the commands below need every chunk of the line loaded (a fill into an unloaded chunk is refused)
    corners = [(x, z) for x in (OX - 12, OX + 58) for z in (OZ - 6, OZ + 7)]
    for _ in range(60):
        if all(ctx.server('execute if loaded %d %d %d' % (x, Y, z), allow_error=True)['result'] == 1 for x, z in corners):
            break
        ctx.step('wait', ticks=10)
    else:
        raise RuntimeError('the chunks of the line did not load: %s' % corners)
    cmd(ctx, 'fill %d %d %d %d %d %d minecraft:air' % (OX - 12, Y, OZ - 6, OX + 58, Y + 8, OZ + 6), allow_error=True)
    cmd(ctx, 'fill %d %d %d %d %d %d minecraft:grass_block' % (OX - 12, Y - 1, OZ - 6, OX + 58, Y - 1, OZ + 7), allow_error=True)

    state = {}
    line = dict(nodes={}, burner=None)
    reads = {}
    sections = [('power', section_power, ['basic-assembly.power-line']),
                ('assembly', section_assembly, ['basic-assembly.shredder-build']),
                ('shredder', section_shredder, ['shredder.batch', 'shredder.ore-aluminium', 'coltan-niobium.shred']),
                ('crafting', section_crafting, ['electrical-components.vacuum-tube', 'electrical-components.printed-board',
                                                'electrical-components.capacitor', 'electric-furnace.craft', 'fluid-mixing.craft']),
                ('soldering', section_soldering, ['soldering-chain.analog-board']),
                ('chemplant', section_chemplant_build, ['basic-assembly.chemplant-build']),
                ('hazcloth', section_hazcloth, ['recipe-completion.hazcloth']),
                ('peroxide', section_peroxide, ['chemical-plant.peroxide']),
                ('coltan', section_coltan, ['coltan-niobium.cleaning']),
                ('concrete', section_concrete, ['concrete.cement', 'concrete.line']),
                ('efurnace', section_efurnace, ['electric-furnace.smelt']),
                ('mixer', section_mixer, ['fluid-mixing.line']),
                ('compressor', section_compressor, ['fluid-compression.build', 'fluid-compression.line']),
                ('arc', section_arc, ['arc-furnace.build', 'arc-furnace.line']),
                ('chip', section_chip, ['silicon-chips.chip']),
                ('centrifuge', section_centrifuge, ['centrifuge.build', 'centrifuge.line']),
                ('crystallizer', section_crystallizer, ['crystallization.line'])]
    for name, fn, ids in sections:
        try:
            fn(ctx, state, line, reads)
        except Exception as e:  # one broken section turns only its own undecided rows into not-run
            reason = 'section %s stopped: %s' % (name, str(getattr(e, 'result', None) or e)[:400])
            state.setdefault('failed', []).append(name)
            for eid in ids:
                if eid not in ctx.verdicts:
                    ctx.not_run(eid, reason)
            try:
                ctx.step('close', allow_fail=True)
                ctx.step('mod', shift=False)
                ctx.server('tick freeze')
            except Exception:
                pass

    try:
        ctx.server('tick freeze')
        ctx.step('view', pos=[OX + 18.5, Y + 9, OZ + 16.5], look_at=[OX + 16.5, Y + 1, OZ + 0.5], fly=True, hide_gui=True)
        _lib.placed(ctx, 10)
        shot = ctx.step('shot', file=ctx.shot_name('overview'))
        ctx.review('basic-assembly.overview', 'wood burner, assembly machine, shredder, crafting table, soldering station, chemical plant '
                   'with the ore acidizer, electric furnace, mixer, arc furnace and centrifuge from the south',
                   evidence=[(shot.get('image') or {}).get('file') or shot.get('file') or 'overview.png'])
    except Exception as e:
        ctx.not_run('basic-assembly.overview', 'picture failed: %s' % e)

    reload_check(ctx, line, reads, state.get('failed', []))


def reload_check(ctx, line, reads, failed=()):
    ids = {'basic-assembly.reload': ['burner', 'assembler'], 'shredder.reload': ['shredder'], 'soldering-chain.reload': ['soldering'],
           'chemical-plant.reload': ['chemplant'], 'electric-furnace.reload': ['efurnace'], 'fluid-mixing.reload': ['mixer'],
           'arc-furnace.reload': ['arc'], 'fluid-compression.reload': ['compressor', 'burner2'], 'centrifuge.reload': ['centrifuge'], 'crystallization.reload': ['crystallizer']}
    # the sections that give each machine the non-default state the comparison needs
    made_by = {'basic-assembly.reload': ['power', 'assembly'], 'shredder.reload': ['shredder'], 'soldering-chain.reload': ['soldering'],
               'chemical-plant.reload': ['peroxide'], 'electric-furnace.reload': ['efurnace'], 'fluid-mixing.reload': ['mixer'],
               'arc-furnace.reload': ['arc'], 'fluid-compression.reload': ['compressor'], 'centrifuge.reload': ['centrifuge'],
               'crystallization.reload': ['crystallizer']}
    present = {k: v for k, v in reads.items()}
    todo = {}
    for eid, keys in ids.items():
        broken = [n for n in made_by[eid] if n in failed]
        if broken:
            ctx.not_run(eid, 'the section that runs this machine stopped (%s), so it holds no state to compare' % ', '.join(broken))
        elif all(k in present for k in keys):
            todo[eid] = keys
        else:
            ctx.not_run(eid, 'the machine was not built in this run (see its section): %s' % [k for k in keys if k not in present])
    if not todo:
        return
    try:
        # the switched-off burner hands its buffer to the machines that are not full; the readings are taken once nothing moves
        ctx.server('tick freeze')
        if line['burner']:
            burner_set(ctx, line, False)
        ctx.sprint(600, label='settle-before-reload', poll_s=0.5, timeout_s=600)
        still(ctx)
        a = {k: snapshot(ctx, pos) for k, pos in present.items()}
        ctx.sprint(40, label='settle-check', poll_s=0.3, timeout_s=600)
        still(ctx)
        before = {k: snapshot(ctx, pos) for k, pos in present.items()}
        moving = [k for k in present if a[k] != before[k]]
        ctx.step('close', allow_fail=True)
        ctx.step('leave')
        ctx.step('openworld', world=ctx.run.world['name'])
        ctx.server('tick freeze')
        _lib.go_near(ctx, OX + 12, Y, OZ)
        still(ctx)
        after = {k: snapshot(ctx, pos) for k, pos in present.items()}
    except Exception as e:
        for eid in todo:
            ctx.not_run(eid, 'reload step failed: %s' % str(getattr(e, 'result', None) or e)[:300])
        return
    for eid, keys in todo.items():
        same = all(before[k] == after[k] for k in keys)
        nondefault = all(bool(before[k].get('power')) or any(t['fill'] for t in before[k]['tanks'].values()) or bool(before[k]['items'])
                         for k in keys)
        ctx.check(eid, same and nondefault, '; '.join('%s at %s before %s / after %s%s' % (
            k, list(present[k]), json.dumps(before[k])[:500], json.dumps(after[k])[:500], ' (still changing before the reload)' if k in moving else '')
            for k in keys))


# ---------------------------------------------------------------- sections

def section_power(ctx, state, line, reads):
    cmd(ctx, 'fill %d %d %d %d %d %d hbmsntm:red_cable' % (BUS_X[0], Y - 1, BUS_Z, BUS_X[1], Y - 1, BUS_Z))
    cmd(ctx, 'item replace entity @s hotbar.%d with hbmsntm:machine_wood_burner' % HAND)
    core, facing = place(ctx, BX, OZ, 'hbmsntm:machine_wood_burner', h=2, dz=3.5)
    if facing != 'south':
        raise RuntimeError('wood burner core %s facing %s, expected south' % (core, facing))
    line['burner'] = core
    reads['burner'] = core
    # its power ports: two blocks behind the core and one further clockwise (MachineWoodBurnerBlockEntity.java:226-236)
    lay_cable(ctx, True, core[0], core[2] - 2)
    logs = stock(ctx, [('minecraft:oak_log', LOGS)])[0]
    open_block(ctx, core, 'MachineWoodBurnerScreen', back=2.5, up=0.0)
    move(ctx, menu_index(6, logs), 0)
    ctx.step('close')
    d = _lib.block_data(ctx, core)
    if n_of(d, 0, 'minecraft:oak_log') != LOGS:
        raise RuntimeError('fuel slot after loading: %s' % items_of(d))


def section_assembly(ctx, state, line, reads):
    if not line['burner']:
        raise RuntimeError('no wood burner')
    cmd(ctx, 'item replace entity @s hotbar.%d with hbmsntm:machine_assembly_machine' % HAND)
    core, facing = place(ctx, X_ASSEMBLER, OZ, 'hbmsntm:machine_assembly_machine')
    reads['assembler'] = core
    state['assembler'] = core
    lay_cable(ctx, True, core[0] - 2, core[2])          # port (x - 2, z) (MachineAssemblyMachineBlockEntity.java:225-227)
    line['nodes']['assembler'] = core
    open_block(ctx, (core[0], core[1], core[2] + 1), 'MachineAssemblyMachineScreen', back=3.5)
    got = pick_recipe(ctx, core, 'hbmAssemblyMachine.json', 'ass.shredder', 'block.hbmsntm.machine_shredder')
    ctx.step('close')
    if got != 'ass.shredder':
        raise RuntimeError('server recipe after the selector: %r' % got)
    rec = charge(ctx, line, 'assembler')
    total, parts = stored(ctx, line)
    ticks, bd = burned(ctx, line)
    d = _lib.block_data(ctx, core)
    ok = (d.get('power') == 100_000 and item_at(d, 0) is None and BURNER_GEN * ticks - 99 <= total <= BURNER_GEN * ticks)
    ctx.check('basic-assembly.power-line', ok, 'after %s sprinted ticks: assembly machine %s HE (max %s, battery slot %s); burned %d ticks '
              '-> 100 x %d = %d HE made; stored %d (%s); burner burnTime %s, isOn %s'
              % (rec.get('advanced'), d.get('power'), d.get('maxPower'), item_at(d, 0), ticks, ticks, BURNER_GEN * ticks, total, parts,
                 bd.get('burnTime'), bd.get('isOn')))

    slots = stock(ctx, [('hbmsntm:plate_steel', 8), ('hbmsntm:plate_copper', 4), ('hbmsntm:motor', 2)])
    d1, d2, k, used = assembler_run(ctx, state, line, None, None, slots, 100, 'assembler-shredder')
    out1, out2 = item_at(d1, 16), item_at(d2, 16)
    inputs_left = {s: v for s, v in items_of(d2).items() if 4 <= s <= 15}
    ok = (out1 is None and out2 is not None and out2.get('id') == 'hbmsntm:machine_shredder' and out2.get('count', 1) == 1
          and not inputs_left and used == 100 * k)
    ctx.check('basic-assembly.shredder-build', ok, 'tick %d output %s; tick %d output %s, inputs left %s; stored energy -%d (want 100 x %d = %d)'
              % (k - 1, out1, k, out2, inputs_left, used, k, 100 * k))
    take_output(ctx, state, 'hbmsntm:machine_shredder')


def take_output(ctx, state, item, hand=HAND):
    """Shift-clicks the assembly machine's output into the emptied hand slot (the right end of the hotbar)."""
    core = state['assembler']
    hand_air(ctx, hand)
    open_block(ctx, (core[0], core[1], core[2] + 1), 'MachineAssemblyMachineScreen', back=3.5)
    shift_click(ctx, 16)
    ctx.step('close')
    inv = inventory(ctx)
    if inv.get(hand, {}).get('id') != item:
        raise RuntimeError('%s is not in the hand slot after the shift-click: %s' % (item, slots_of(inv, item)))


def assembler_run(ctx, state, line, recipe, label_key, inputs, duration, label):
    """Selects `recipe` (None keeps the selected one) on the placed assembly machine, charges the line, shift-clicks the
    inputs (nbt slots) in and runs it to its completion tick; returns (reading one tick before, reading at completion,
    completion tick, stored energy used)."""
    core = state['assembler']
    if recipe:
        open_block(ctx, (core[0], core[1], core[2] + 1), 'MachineAssemblyMachineScreen', back=3.5)
        got = pick_recipe(ctx, core, 'hbmAssemblyMachine.json', recipe, label_key)
        ctx.step('close')
        if got != recipe:
            raise RuntimeError('server recipe after the selector: %r' % got)
        charge(ctx, line, label)
    open_block(ctx, (core[0], core[1], core[2] + 1), 'MachineAssemblyMachineScreen', back=3.5)
    for s in inputs[:-1]:
        shift_click(ctx, menu_index(17, s))
    e0, _ = stored(ctx, line)
    t0 = ctx.server()['game_time']
    shift_click(ctx, menu_index(17, inputs[-1]))
    ctx.step('close')
    k = module_ticks(duration)[0]
    advance_to(ctx, t0, k - 1, label)
    d1 = _lib.block_data(ctx, core)
    advance_to(ctx, t0, k, label)
    d2 = _lib.block_data(ctx, core)
    e1, _ = stored(ctx, line)
    return d1, d2, k, e0 - e1


def section_shredder(ctx, state, line, reads):
    if 'assembler' not in state:
        raise RuntimeError('no shredder: the assembly section did not make one')
    pos, _ = place(ctx, X_SHREDDER, OZ, 'hbmsntm:machine_shredder', h=1)
    reads['shredder'] = pos
    state['shredder'] = pos
    lay_cable(ctx, False, pos[0], pos[2])              # the bottom port (MachineShredderBlockEntity.java:240-249)
    line['nodes']['shredder'] = pos
    charge(ctx, line, 'shredder')
    give = [('hbmsntm:blades_steel', 1), ('hbmsntm:blades_steel', 1), ('hbmsntm:ingot_aluminium', 2), ('hbmsntm:ore_lead', 2),
            ('hbmsntm:ore_coltan', 1)]
    slots = stock(ctx, give)
    open_block(ctx, pos, 'MachineShredderScreen', face='up', back=1.5)
    for s in slots[:4]:
        shift_click(ctx, menu_index(30, s))
    e0, _ = stored(ctx, line)
    t0 = ctx.server()['game_time']
    shift_click(ctx, menu_index(30, slots[4]))
    ctx.step('close')
    rounds = {}
    for t in (59, 60, 120):
        advance_to(ctx, t0, t, 'shredder')
        rounds[t] = _lib.block_data(ctx, pos)
    e1, _ = stored(ctx, line)

    def outputs(d):
        out = {}
        for s, (i, n) in items_of(d).items():
            if 9 <= s <= 26:
                out[i] = out.get(i, 0) + n
        return out

    def damage(d):
        return [(item_at(d, s) or {}).get('components', {}).get('minecraft:damage', 0) for s in (27, 28)]

    o59, o60, o120 = outputs(rounds[59]), outputs(rounds[60]), outputs(rounds[120])
    left = {s: v for s, v in items_of(rounds[120]).items() if s < 9}
    want60 = {'hbmsntm:powder_aluminium': 1, 'hbmsntm:powder_lead': 2, 'hbmsntm:powder_coltan_ore': 2}
    want120 = {'hbmsntm:powder_aluminium': 2, 'hbmsntm:powder_lead': 4, 'hbmsntm:powder_coltan_ore': 2}
    ok = (o59 == {} and o60 == want60 and damage(rounds[60]) == [1, 1] and o120 == want120 and not left
          and damage(rounds[120]) == [2, 2] and e0 - e1 == 5 * 120)
    ctx.check('shredder.batch', ok, 'tick 59 %s; tick 60 %s blades %s; tick 120 %s blades %s, inputs left %s; stored energy -%d (want 600)'
              % (o59, o60, damage(rounds[60]), o120, damage(rounds[120]), left, e0 - e1))
    ctx.check('coltan-niobium.shred', o120.get('hbmsntm:powder_coltan_ore') == 2 and 'hbmsntm:ore_coltan' not in {i for i, n in left.values()},
              '1 coltan ore -> %s crushed coltan ore' % o120.get('hbmsntm:powder_coltan_ore'))
    open_block(ctx, pos, 'MachineShredderScreen', face='up', back=1.5)
    for s in sorted(s for s in items_of(rounds[120]) if 9 <= s <= 26):
        shift_click(ctx, s)
    ore = stock(ctx, [('hbmsntm:ore_aluminium', 1)])[0]
    shift_click(ctx, menu_index(30, ore))
    ctx.step('close')
    t1 = ctx.server()['game_time']
    advance_to(ctx, t1, 60, 'shredder-ore-aluminium')
    d = _lib.block_data(ctx, pos)
    o = outputs(d)
    ctx.check('shredder.ore-aluminium', o == {'hbmsntm:chunk_cryolite': 2},
              '1 aluminium ore after 60 ticks: outputs %s (the original gives 2 hbmsntm:chunk_cryolite)' % o)
    open_block(ctx, pos, 'MachineShredderScreen', face='up', back=1.5)
    for s in sorted(s for s in items_of(d) if 9 <= s <= 26):
        shift_click(ctx, s)
    ctx.step('close')


def craft_stacks(ctx, grid):
    """Puts whole stacks from the player inventory into the crafting grid: grid = {cell 1..9: nbt slot}."""
    for cell, nbt_slot in grid.items():
        move(ctx, menu_index(10, nbt_slot), cell)


def section_crafting(ctx, state, line, reads):
    cmd(ctx, 'item replace entity @s hotbar.%d with minecraft:crafting_table' % HAND)
    table, _ = place(ctx, X_TABLE, OZ, 'minecraft:crafting_table', h=1)
    state['table'] = table
    batches = [
        [('pane', 'minecraft:glass_pane', 8), ('wire_w', 'hbmsntm:wire_tungsten', 8), ('poly7', 'hbmsntm:plate_polymer', 8),
         ('poly8', 'hbmsntm:plate_polymer', 8), ('cu8', 'hbmsntm:plate_copper', 8), ('poly2a', 'hbmsntm:plate_polymer', 2),
         ('poly2b', 'hbmsntm:plate_polymer', 2), ('wire_cu_a', 'hbmsntm:wire_copper', 2), ('wire_cu_b', 'hbmsntm:wire_copper', 2)],
        [('be1', 'hbmsntm:ingot_beryllium', 1), ('be2', 'hbmsntm:ingot_beryllium', 1), ('be3', 'hbmsntm:ingot_beryllium', 1),
         ('cast_a', 'hbmsntm:plate_cast[hbmsntm:meta=5]', 1), ('furnace', 'minecraft:furnace', 1),
         ('cast_b', 'hbmsntm:plate_cast[hbmsntm:meta=5]', 1), ('coil1', 'hbmsntm:coil_tungsten', 1),
         ('coil2', 'hbmsntm:coil_tungsten', 1), ('coil3', 'hbmsntm:coil_tungsten', 1)],
        [('ps1', 'hbmsntm:plate_steel', 1), ('ps2', 'hbmsntm:plate_steel', 1), ('ps3', 'hbmsntm:plate_steel', 1),
         ('ps4', 'hbmsntm:plate_steel', 1), ('dura', 'hbmsntm:ingot_dura_steel', 1), ('gp1', 'minecraft:glass_pane', 1),
         ('gp2', 'minecraft:glass_pane', 1), ('motor', 'hbmsntm:motor', 1)],
        [('b1', 'hbmsntm:plate_steel', 1), ('b2', 'hbmsntm:plate_steel', 1), ('b3', 'hbmsntm:plate_steel', 1),
         ('b4', 'hbmsntm:plate_steel', 1), ('b5', 'hbmsntm:plate_steel', 1), ('b6', 'hbmsntm:plate_steel', 1),
         ('bi1', 'hbmsntm:ingot_steel', 1), ('bi2', 'hbmsntm:ingot_steel', 1), ('dye', 'minecraft:blue_dye', 1),
         ('iron', 'hbmsntm:plate_iron', 1)]]
    at = {}

    def give(batch):
        at.update(dict(zip([n for n, i, c in batch], stock(ctx, [(i, c) for n, i, c in batch]))))

    give(batches[0])
    open_block(ctx, table, 'CraftingScreen', face='up', back=1.5)

    def craft(eid, grid, product, want, used):
        before = inventory(ctx)
        craft_stacks(ctx, grid)
        shift_click(ctx, 0)
        after = inventory(ctx)
        made = count(after, product) - count(before, product)
        gone = {i: count(before, i) - count(after, i) for i in used}
        ctx.check(eid, made == want and gone == used, '%s made %d (want %d); inputs used %s (want %s)' % (product, made, want, gone, used))

    craft('electrical-components.vacuum-tube', {2: at['pane'], 5: at['wire_w'], 8: at['poly7']}, 'hbmsntm:circuit_vacuum_tube', 8,
          {'minecraft:glass_pane': 8, 'hbmsntm:wire_tungsten': 8, 'hbmsntm:plate_polymer': 8})
    craft('electrical-components.printed-board', {2: at['poly8'], 5: at['cu8']}, 'hbmsntm:circuit_printed_board', 8,
          {'hbmsntm:plate_polymer': 8, 'hbmsntm:plate_copper': 8})
    inv = inventory(ctx)
    powder = slots_of(inv, 'hbmsntm:powder_aluminium')
    if powder and inv[powder[0]].get('count', 1) >= 2:
        before = inventory(ctx)
        craft_stacks(ctx, {4: at['poly2a'], 6: at['poly2b'], 7: at['wire_cu_a'], 9: at['wire_cu_b']})
        ctx.step('click', slot=menu_index(10, powder[0]), after=2)      # two powder by right-clicks from the stack
        for _ in range(2):
            ctx.step('click', slot=5, button=1, after=2)
        ctx.step('click', slot=menu_index(10, powder[0]), after=2)
        shift_click(ctx, 0)
        after = inventory(ctx)
        made = count(after, 'hbmsntm:circuit_capacitor') - count(before, 'hbmsntm:circuit_capacitor')
        gone = {i: count(before, i) - count(after, i) for i in ('hbmsntm:plate_polymer', 'hbmsntm:powder_aluminium', 'hbmsntm:wire_copper')}
        want = {'hbmsntm:plate_polymer': 4, 'hbmsntm:powder_aluminium': 2, 'hbmsntm:wire_copper': 4}
        ctx.check('electrical-components.capacitor', made == 4 and gone == want,
                  'hbmsntm:circuit_capacitor made %d (want 4); inputs used %s (want %s)' % (made, gone, want))
    else:
        ctx.not_run('electrical-components.capacitor', 'no stack of at least 2 aluminium powder from the shredder (slots %s)'
                    % [(s, inv[s].get('count')) for s in powder])
    # the electric furnace lands in hotbar slot 7 and the mixer in slot 6 (the right-most empty hotbar slots)
    give(batches[1])
    hand_air(ctx, 7)
    craft('electric-furnace.craft', {1: at['be1'], 2: at['be2'], 3: at['be3'], 4: at['cast_a'], 5: at['furnace'], 6: at['cast_b'],
                                     7: at['coil1'], 8: at['coil2'], 9: at['coil3']}, 'hbmsntm:machine_electric_furnace', 1,
          {'hbmsntm:ingot_beryllium': 3, 'hbmsntm:plate_cast': 2, 'minecraft:furnace': 1, 'hbmsntm:coil_tungsten': 3})
    give(batches[2])
    hand_air(ctx, 6)
    inv = inventory(ctx)
    tube = slots_of(inv, 'hbmsntm:circuit_vacuum_tube')[0]
    before = inv
    craft_stacks(ctx, {1: at['ps1'], 2: at['dura'], 3: at['ps2'], 4: at['gp1'], 6: at['gp2'], 7: at['ps3'], 8: at['motor'], 9: at['ps4']})
    ctx.step('click', slot=menu_index(10, tube), after=2)       # one vacuum tube by a right-click from its stack
    ctx.step('click', slot=5, button=1, after=2)
    ctx.step('click', slot=menu_index(10, tube), after=2)
    shift_click(ctx, 0)
    after = inventory(ctx)
    used = {'hbmsntm:plate_steel': 4, 'hbmsntm:ingot_dura_steel': 1, 'minecraft:glass_pane': 2, 'hbmsntm:circuit_vacuum_tube': 1, 'hbmsntm:motor': 1}
    gone = {i: count(before, i) - count(after, i) for i in used}
    made = count(after, 'hbmsntm:machine_mixer') - count(before, 'hbmsntm:machine_mixer')
    ctx.check('fluid-mixing.craft', made == 1 and gone == used, 'hbmsntm:machine_mixer made %d (want 1); inputs used %s (want %s)' % (made, gone, used))
    # for the compressor: a steel barrel (hotbar slot 5) and a fluid identifier (hotbar slot 4)
    give(batches[3])
    hand_air(ctx, 5)
    craft_stacks(ctx, {1: at['b1'], 2: at['bi1'], 3: at['b2'], 4: at['b3'], 6: at['b4'], 7: at['b5'], 8: at['bi2'], 9: at['b6']})
    shift_click(ctx, 0)
    hand_air(ctx, 4)
    inv = inventory(ctx)
    tube = slots_of(inv, 'hbmsntm:circuit_vacuum_tube')[0]
    craft_stacks(ctx, {2: at['dye'], 8: at['iron']})
    ctx.step('click', slot=menu_index(10, tube), after=2)
    ctx.step('click', slot=5, button=1, after=2)
    ctx.step('click', slot=menu_index(10, tube), after=2)
    shift_click(ctx, 0)
    ctx.step('close')
    inv = inventory(ctx)
    state['efurnace_slot'] = next((s for s in slots_of(inv, 'hbmsntm:machine_electric_furnace') if s < 9), None)
    state['mixer_slot'] = next((s for s in slots_of(inv, 'hbmsntm:machine_mixer') if s < 9), None)


def section_soldering(ctx, state, line, reads):
    inv = inventory(ctx)
    need = {'hbmsntm:circuit_vacuum_tube': 6, 'hbmsntm:circuit_capacitor': 4, 'hbmsntm:circuit_printed_board': 8}
    short = {i: count(inv, i) for i, n in need.items() if count(inv, i) < n}
    if short:
        raise RuntimeError('circuit parts missing from the crafting section: %s' % short)
    cmd(ctx, 'item replace entity @s hotbar.%d with hbmsntm:machine_soldering_station' % HAND)
    core, facing = place(ctx, X_SOLDER, OZ, 'hbmsntm:machine_soldering_station', h=1)
    reads['soldering'] = core
    # port two blocks clockwise of the core (MachineSolderingStationBlockEntity.java:266)
    rot = _lib.VEC[_lib.clockwise(facing)]
    lay_cable(ctx, True, core[0] + 2 * rot[0], core[2] + 2 * rot[2])
    line['nodes']['soldering'] = core
    charge(ctx, line, 'soldering')
    wire = stock(ctx, [('hbmsntm:wire_lead', 8)])[0]
    open_block(ctx, core, 'MachineSolderingStationScreen', face='up', back=1.5)
    inv = inventory(ctx)
    for item in ('hbmsntm:circuit_vacuum_tube', 'hbmsntm:circuit_capacitor', 'hbmsntm:circuit_printed_board'):
        shift_click(ctx, menu_index(11, slots_of(inv, item)[0]))
    e0, _ = stored(ctx, line)
    t0 = ctx.server()['game_time']
    shift_click(ctx, menu_index(11, wire))
    ctx.step('close')
    reads_at = {}
    for t in (99, 100, 200):
        advance_to(ctx, t0, t, 'soldering')
        reads_at[t] = _lib.block_data(ctx, core)
    e1, _ = stored(ctx, line)
    boards = {t: n_of(d, 6, 'hbmsntm:circuit_analog_board') for t, d in reads_at.items()}
    left = {s: v for s, v in items_of(reads_at[200]).items() if s < 6}
    ok = boards == {99: 0, 100: 1, 200: 2} and not left and e0 - e1 == 100 * 200
    ctx.check('soldering-chain.analog-board', ok, 'boards at 99/100/200: %s; inputs left %s; stored energy -%d (want 20000)' % (boards, left, e0 - e1))
    open_block(ctx, core, 'MachineSolderingStationScreen', face='up', back=1.5)
    shift_click(ctx, 6)
    ctx.step('close')


def section_chemplant_build(ctx, state, line, reads):
    if 'assembler' not in state:
        raise RuntimeError('no assembly machine placed')
    inv = inventory(ctx)
    if count(inv, 'hbmsntm:circuit_analog_board') < 1:
        raise RuntimeError('no analog board from the soldering section')
    given = stock(ctx, [('hbmsntm:ingot_steel', 8), ('hbmsntm:pipe_copper', 2), ('hbmsntm:plate_polymer', 16), ('hbmsntm:motor', 2),
                        ('hbmsntm:coil_tungsten', 2)])
    analog = slots_of(inventory(ctx), 'hbmsntm:circuit_analog_board')[0]
    d1, d2, k, used = assembler_run(ctx, state, line, 'ass.chemplant', 'block.hbmsntm.machine_chemical_plant', given + [analog], 200,
                                    'assembler-chemplant')
    out1, out2 = item_at(d1, 16), item_at(d2, 16)
    left = {s: v for s, v in items_of(d2).items() if 4 <= s <= 15}
    ok = (out1 is None and out2 is not None and out2.get('id') == 'hbmsntm:machine_chemical_plant' and out2.get('count', 1) == 1
          and all(v[0] == 'hbmsntm:circuit_analog_board' for v in left.values()) and used == 100 * k)
    ctx.check('basic-assembly.chemplant-build', ok, 'tick %d output %s; tick %d output %s; inputs left %s (a second analog board may stay); '
              'stored energy -%d (want 100 x %d)' % (k - 1, out1, k, out2, left, used, k))
    core = state['assembler']
    hand_air(ctx)
    open_block(ctx, (core[0], core[1], core[2] + 1), 'MachineAssemblyMachineScreen', back=3.5)
    shift_click(ctx, 16)
    for s in sorted(left):
        shift_click(ctx, s)
    ctx.step('close')
    if inventory(ctx).get(HAND, {}).get('id') != 'hbmsntm:machine_chemical_plant':
        raise RuntimeError('chemical plant not in the hand slot after the shift-click')
    state['chemplant_item'] = True


def section_hazcloth(ctx, state, line, reads):
    if 'assembler' not in state:
        raise RuntimeError('no assembly machine placed')
    inv = inventory(ctx)
    lead = slots_of(inv, 'hbmsntm:powder_lead')
    if count(inv, 'hbmsntm:powder_lead') < 4 or len(lead) != 1:
        raise RuntimeError('no single stack of 4 lead powder from the shredder: %s' % [(s, inv[s].get('count')) for s in lead])
    string = stock(ctx, [('minecraft:string', 8)])[0]
    d1, d2, k, used = assembler_run(ctx, state, line, 'ass.hazcloth', 'item.hbmsntm.hazmat_cloth', [lead[0], string], 50, 'assembler-hazcloth')
    out1, out2 = item_at(d1, 16), item_at(d2, 16)
    left = {s: v for s, v in items_of(d2).items() if 4 <= s <= 15}
    ok = (out1 is None and out2 is not None and out2.get('id') == 'hbmsntm:hazmat_cloth' and out2.get('count') == 4 and not left
          and used == 100 * k)
    ctx.check('recipe-completion.hazcloth', ok, 'tick %d output %s; tick %d output %s; inputs left %s; stored energy -%d (want 100 x %d)'
              % (k - 1, out1, k, out2, left, used, k))
    core = state['assembler']
    open_block(ctx, (core[0], core[1], core[2] + 1), 'MachineAssemblyMachineScreen', back=3.5)
    shift_click(ctx, 16)
    ctx.step('close')


def section_peroxide(ctx, state, line, reads):
    if not state.get('chemplant_item'):
        raise RuntimeError('no chemical plant item from the assembly machine')
    core, _ = place(ctx, X_PLANT, OZ, 'hbmsntm:machine_chemical_plant')
    reads['chemplant'] = core
    state['chemplant'] = core
    lay_cable(ctx, True, core[0] - 2, core[2])          # port (x - 2, z) (MachineChemicalPlantBlockEntity.java:209-224)
    line['nodes']['chemplant'] = core
    b1, b2 = stock(ctx, [('minecraft:water_bucket', 1), ('minecraft:water_bucket', 1)])
    open_block(ctx, (core[0], core[1], core[2] + 1), 'MachineChemicalPlantScreen', back=3.5)
    got = pick_recipe(ctx, core, 'hbmChemicalPlant.json', 'chem.peroxide', 'chem.peroxide')
    if got != 'chem.peroxide':
        raise RuntimeError('server recipe after the selector: %r' % got)
    ctx.step('close')
    charge(ctx, line, 'chemplant')
    # the recipe has typed the tanks (setupTanks); a bucket loads in the plant's next tick (loadTank, :62) and the same tick
    # already runs the recipe (1,000 mB is one cycle's water), so the window starts with the first bucket
    open_block(ctx, (core[0], core[1], core[2] + 1), 'MachineChemicalPlantScreen', back=3.5)
    e0, _ = stored(ctx, line)
    t0 = ctx.server()['game_time']
    move(ctx, menu_index(22, b1), 10)
    server_steps(ctx, 1)
    reads_at = {1: _lib.block_data(ctx, core)}
    move(ctx, menu_index(22, b2), 10)
    ctx.step('close')
    ticks = module_ticks(50, 2)
    for t in (ticks[0] - 1, ticks[0], ticks[1]):
        advance_to(ctx, t0, t, 'chemplant-peroxide')
        reads_at[t] = _lib.block_data(ctx, core)
    e1, _ = stored(ctx, line)

    def fills(d):
        return {n: (v['fill'], v['type']) for n, v in _lib.tanks(d).items() if v['fill']}

    want = {1: {'i0': (1000, 1)}, ticks[0] - 1: {'i0': (2000, 1)}, ticks[0]: {'i0': (1000, 1), 'o0': (1000, PEROXIDE_ID)},
            ticks[1]: {'o0': (2000, PEROXIDE_ID)}}
    got = {t: fills(reads_at[t]) for t in want}
    buckets = item_at(reads_at[ticks[1]], 13)
    ok = (got == want and buckets is not None and buckets.get('id') == 'minecraft:bucket' and buckets.get('count') == 2
          and e0 - e1 == 100 * ticks[1])
    ctx.check('chemical-plant.peroxide', ok, 'first bucket at tick 0, second after tick 1; tank fills by tick %s (want %s); empty buckets '
              'in slot 13: %s; stored energy -%d (want 100 x %d)' % (got, want, buckets, e0 - e1, ticks[1]))


def use_any(ctx, pos, face, back=2.5, up=0.0):
    """Right-click with the selected item aimed through `face` at the middle of the block at `pos` (ducts, whose outline is
    smaller than the cell); the readings afterwards show whether the click took."""
    d = _lib.VEC[face]
    x, y, z = pos
    eye = [x + 0.5 + d[0] * back, y + up, z + 0.5 + d[2] * back]
    ctx.step('view', pos=eye, look_at=[x + 0.5 + 0.05 * d[0], y + 0.5, z + 0.5 + 0.05 * d[2]], fly=True, hide_gui=True)
    return ctx.step('use', target=dict(pos=list(pos), face=face, offset=[-0.449 * d[0], 0.0, -0.449 * d[2]]), any_hit=True, after=6)


def shred(ctx, pos, pairs, label):
    """Shift-clicks start items into the shredder at `pos` and runs it 60 ticks (one round, MachineShredderBlockEntity.java:93-111);
    returns (outputs at tick 59, outputs at tick 60) and takes the outputs into the player inventory."""
    slots = stock(ctx, pairs)
    open_block(ctx, pos, 'MachineShredderScreen', face='up', back=1.5)
    for s in slots[:-1]:
        shift_click(ctx, menu_index(30, s))
    t0 = ctx.server()['game_time']
    shift_click(ctx, menu_index(30, slots[-1]))
    ctx.step('close')
    got = {}
    for t in (59, 60):
        advance_to(ctx, t0, t, label)
        d = _lib.block_data(ctx, pos)
        got[t] = {}
        for s, (i, n) in items_of(d).items():
            if 9 <= s <= 26:
                got[t][i] = got[t].get(i, 0) + n
    open_block(ctx, pos, 'MachineShredderScreen', face='up', back=1.5)
    for s in sorted(s for s in items_of(d) if 9 <= s <= 26):
        shift_click(ctx, s)
    ctx.step('close')
    return got[59], got[60]


def plant_recipe(ctx, core, name):
    open_block(ctx, (core[0], core[1], core[2] + 1), 'MachineChemicalPlantScreen', back=3.5)
    got = pick_recipe(ctx, core, 'hbmChemicalPlant.json', name, name)
    ctx.step('close')
    if got != name:
        raise RuntimeError('plant recipe after the selector: %r, wanted %s' % (got, name))


def tank_of(data, name='tank'):
    return _lib.tanks(data).get(name) or {}


def barrel_type(ctx, barrel, hotbar):
    """Puts the identifier from `hotbar` into the barrel's slot 0; the barrel takes its type and moves it to slot 1
    (FluidTank.setType, BarrelBlockEntity.java:66-67); it goes back to the same hotbar slot."""
    open_any(ctx, barrel, 'BarrelScreen', face='north', back=2.5, up=0.0)
    move(ctx, menu_index(6, hotbar), 0)
    server_steps(ctx, 1)
    move(ctx, 1, menu_index(6, hotbar))
    ctx.step('close')


def barrel_mode(ctx, barrel, mode):
    """Clicks the barrel's mode button (GUI 160,43; BarrelBlockEntity.java:261) until the server reads `mode`."""
    for _ in range(4):
        if _lib.block_data(ctx, barrel).get('mode', 0) == mode:
            return
        open_any(ctx, barrel, 'BarrelScreen', face='north', back=2.5, up=0.0)
        hud = ctx.step('hud', frames=2)
        ctx.step('click', at=[hud['gui_left'] + 160, hud['gui_top'] + 43], button=0, after=4)
        ctx.step('close')
    if _lib.block_data(ctx, barrel).get('mode', 0) != mode:
        raise RuntimeError('barrel %s did not reach mode %d' % (barrel, mode))


def section_coltan(ctx, state, line, reads):
    plant, shredder = state.get('chemplant'), state.get('shredder')
    if not plant or not shredder:
        raise RuntimeError('no chemical plant or shredder placed')
    dp = _lib.block_data(ctx, plant)
    o0 = tank_of(dp, 'o0')
    if dp.get('recipe0') != 'chem.peroxide' or o0.get('type') != PEROXIDE_ID or o0.get('fill', 0) < 250:
        raise RuntimeError('the plant holds no peroxide from its peroxide section: recipe %s, o0 %s' % (dp.get('recipe0'), o0))
    perox0 = o0['fill']
    # coal powder (and crushed coltan ore when the shredder section left none) from the shredder
    inv = inventory(ctx)
    give = [('minecraft:coal', 1)] + ([('hbmsntm:ore_coltan', 1)] if count(inv, 'hbmsntm:powder_coltan_ore') < 2 else [])
    o59, o60 = shred(ctx, shredder, give, 'shredder-coal')
    if o59 or o60.get('hbmsntm:powder_coal') != 1:
        raise RuntimeError('coal through the shredder: tick 59 %s, tick 60 %s (want 1 hbmsntm:powder_coal)' % (o59, o60))
    # two ducts at the plant's north ports (MachineChemicalPlantBlockEntity.java:209-224) and a barrel north of each
    px, py, pz = plant
    duct_p, duct_h = (px - 1, py, pz - 2), (px + 1, py, pz - 2)
    bar_p, bar_h = (px - 1, py, pz - 3), (px + 1, py, pz - 3)
    for c in (duct_p, duct_h, bar_p, bar_h):
        if ctx.server('execute if block %d %d %d minecraft:air' % c, allow_error=True)['result'] != 1:
            raise RuntimeError('cell %s is not free' % (c,))
    for c in (duct_p, duct_h):
        cmd(ctx, 'setblock %d %d %d hbmsntm:fluid_duct_neo' % c)
    for b in (bar_p, bar_h):
        cmd(ctx, 'item replace entity @s hotbar.%d with hbmsntm:barrel_steel' % HAND)
        got, _ = place(ctx, b[0], b[2], 'hbmsntm:barrel_steel', h=1, dz=-3.5, r=1)
        if got != b:
            raise RuntimeError('barrel placed at %s, wanted %s' % (got, b))
    # 预写: both identifiers' fluids (custom data Fluid1), see PREWRITTEN
    cmd(ctx, 'item replace entity @s hotbar.1 with hbmsntm:fluid_identifier_multi[minecraft:custom_data={Fluid1:%d}]' % PEROXIDE_ID)
    cmd(ctx, 'item replace entity @s hotbar.2 with hbmsntm:fluid_identifier_multi[minecraft:custom_data={Fluid1:%d}]' % HYDROGEN_ID)
    # each duct typed with one plain right-click of its identifier (FluidDuctBaseBlock.java:69-74), from outside the pair
    select_hotbar(ctx, 1)
    use_any(ctx, duct_p, 'west')
    select_hotbar(ctx, 2)
    use_any(ctx, duct_h, 'east')
    select_hotbar(ctx, 0)
    types = (_lib.block_data(ctx, duct_p).get('Type'), _lib.block_data(ctx, duct_h).get('Type'))
    if types != (PEROXIDE_ID, HYDROGEN_ID):
        raise RuntimeError('duct types after the clicks: %s (want %s)' % (types, (PEROXIDE_ID, HYDROGEN_ID)))
    barrel_type(ctx, bar_p, 1)
    barrel_type(ctx, bar_h, 2)
    for h in (1, 2):
        cmd(ctx, 'item replace entity @s hotbar.%d with minecraft:stick' % h)
    # receive mode (0, the default): the plant hands its peroxide to barrel P through the duct
    ctx.sprint(39, label='coltan-peroxide-to-barrel', poll_s=0.3, timeout_s=300)
    still(ctx)
    bp, dp = tank_of(_lib.block_data(ctx, bar_p)), _lib.block_data(ctx, plant)
    if bp.get('fill') != perox0 or bp.get('type') != PEROXIDE_ID or tank_of(dp, 'o0').get('fill', 0) != 0:
        raise RuntimeError('peroxide into barrel P: barrel %s, plant o0 %s (want all %d mB moved)' % (bp, tank_of(dp, 'o0'), perox0))
    # chem.hydrogen: 1 coal + 8,000 mB water -> 500 mB hydrogen (ChemicalPlantRecipes.java:41-45), into barrel H
    plant_recipe(ctx, plant, 'chem.hydrogen')
    given = stock(ctx, [('minecraft:coal', 1)] + [('minecraft:water_bucket', 1)] * 8)
    open_block(ctx, (px, py, pz + 1), 'MachineChemicalPlantScreen', back=3.5)
    shift_click(ctx, menu_index(22, given[0]))
    for b in given[1:]:          # one bucket a tick through the fluid slot (loadTank, :104)
        move(ctx, menu_index(22, b), 10)
        server_steps(ctx, 1)
    ctx.step('close')
    ctx.sprint(39, label='coltan-hydrogen', poll_s=0.3, timeout_s=300)
    still(ctx)
    bh, dp = tank_of(_lib.block_data(ctx, bar_h)), _lib.block_data(ctx, plant)
    if bh.get('fill') != 500 or bh.get('type') != HYDROGEN_ID:
        raise RuntimeError('hydrogen into barrel H: barrel %s, plant tanks %s (want 500 mB of type %d)' % (bh, _lib.tanks(dp), HYDROGEN_ID))
    # chem.coltancleaning: the plant's tanks take the recipe's types (ModuleMachineBase.setupTanks); both barrels send
    plant_recipe(ctx, plant, 'chem.coltancleaning')
    barrel_mode(ctx, bar_p, 2)
    barrel_mode(ctx, bar_h, 2)
    charge(ctx, line, 'coltan')
    inv = inventory(ctx)
    ore, cp = slots_of(inv, 'hbmsntm:powder_coltan_ore'), slots_of(inv, 'hbmsntm:powder_coal')
    if count(inv, 'hbmsntm:powder_coltan_ore') < 2 or not cp:
        raise RuntimeError('crushed coltan ore %s / coal powder %s missing' % (ore, cp))

    def fluids():
        d = _lib.block_data(ctx, plant)
        t = _lib.tanks(d)
        a, b = tank_of(_lib.block_data(ctx, bar_p)), tank_of(_lib.block_data(ctx, bar_h))
        return d, dict(i0=t.get('i0'), i1=t.get('i1'), o0=t.get('o0'), barrel_p=a, barrel_h=b,
                       perox=(t.get('i0') or {}).get('fill', 0) + a.get('fill', 0), hydro=(t.get('i1') or {}).get('fill', 0) + b.get('fill', 0))

    open_block(ctx, (px, py, pz + 1), 'MachineChemicalPlantScreen', back=3.5)
    shift_click(ctx, menu_index(22, cp[0]))
    e0, _ = stored(ctx, line)
    _, f0 = fluids()
    t0 = ctx.server()['game_time']
    shift_click(ctx, menu_index(22, ore[0]))
    ctx.step('close')
    k = module_ticks(60)[0]
    advance_to(ctx, t0, k - 1, 'coltan-cleaning')
    d1 = _lib.block_data(ctx, plant)
    advance_to(ctx, t0, k, 'coltan-cleaning')
    e1, _ = stored(ctx, line)
    d2, f2 = fluids()

    def outs(d):
        o = {}
        for s, (i, n) in items_of(d).items():
            if 7 <= s <= 9:
                o[i] = o.get(i, 0) + n
        return o

    want = {'hbmsntm:powder_coltan': 1, 'hbmsntm:powder_niobium': 1, 'hbmsntm:dust': 1}
    left = {s: v for s, v in items_of(d2).items() if 4 <= s <= 6}
    typed = ((f0['i0'] or {}).get('type'), (f0['i1'] or {}).get('type'))
    ok = (typed == (PEROXIDE_ID, HYDROGEN_ID) and f0['perox'] == perox0 and f0['hydro'] == 500 and (f0['i0'] or {}).get('fill', 0) >= 250
          and (f0['i1'] or {}).get('fill', 0) >= 500 and outs(d1) == {} and outs(d2) == want and f2['perox'] == perox0 - 250
          and f2['hydro'] == 0 and (f2['o0'] or {}).get('fill') == 500 and (f2['o0'] or {}).get('type') == WATER_ID and not left
          and e0 - e1 == 100 * k)
    ctx.check('coltan-niobium.cleaning', ok, 'ducts typed %s; barrel P took %d mB peroxide, barrel H 500 mB hydrogen; before the window: %s; '
              'outputs at tick %d: %s, at tick %d: %s (want %s); after: %s (want peroxide %d, hydrogen 0, o0 500 water); inputs left %s; '
              'stored energy -%d (want 100 x %d)' % (types, perox0, json.dumps(f0), k - 1, outs(d1), k, outs(d2), want, json.dumps(f2),
                                                     perox0 - 250, left, e0 - e1, k))
    open_block(ctx, (px, py, pz + 1), 'MachineChemicalPlantScreen', back=3.5)
    for s in sorted(s for s in items_of(d2) if 7 <= s <= 9):
        shift_click(ctx, s)
    ctx.step('close')


def section_concrete(ctx, state, line, reads):
    plant, shredder, table = state.get('chemplant'), state.get('shredder'), state.get('table')
    if not plant or not shredder or not table:
        raise RuntimeError('no chemical plant, shredder or crafting table placed')
    o59, o60 = shred(ctx, shredder, [('hbmsntm:resource_limestone', 1)], 'shredder-limestone')
    inv = inventory(ctx)
    lime = slots_of(inv, 'hbmsntm:powder_limestone')
    clay = stock(ctx, [('minecraft:clay_ball', 1)] * 3)
    if not lime:
        ctx.check('concrete.cement', False, 'limestone through the shredder: tick 59 %s, tick 60 %s (want 4 hbmsntm:powder_limestone)' % (o59, o60))
        raise RuntimeError('no limestone powder from the shredder')
    before = inventory(ctx)
    open_block(ctx, table, 'CraftingScreen', face='up', back=1.5)
    craft_stacks(ctx, {1: lime[0], 2: clay[0], 3: clay[1], 4: clay[2]})
    shift_click(ctx, 0)
    ctx.step('close')
    after = inventory(ctx)
    made = count(after, 'hbmsntm:powder_cement') - count(before, 'hbmsntm:powder_cement')
    gone = {i: count(before, i) - count(after, i) for i in ('hbmsntm:powder_limestone', 'minecraft:clay_ball')}
    ctx.check('concrete.cement', o59 == {} and o60 == {'hbmsntm:powder_limestone': 4} and made == 4
              and gone == {'hbmsntm:powder_limestone': 1, 'minecraft:clay_ball': 3},
              'limestone through the shredder: tick 59 %s, tick 60 %s (want 4 hbmsntm:powder_limestone); cement made %d (want 4), '
              'inputs used %s (want 1 limestone powder, 3 clay balls)' % (o59, o60, made, gone))
    cement = slots_of(after, 'hbmsntm:powder_cement')
    if not cement:
        raise RuntimeError('no cement for the plant')
    plant_recipe(ctx, plant, 'chem.concrete')
    b1, b2, gravel, sand = stock(ctx, [('minecraft:water_bucket', 1), ('minecraft:water_bucket', 1), ('minecraft:gravel', 8),
                                       ('minecraft:sand', 8)])
    charge(ctx, line, 'concrete')
    px, py, pz = plant
    open_block(ctx, (px, py, pz + 1), 'MachineChemicalPlantScreen', back=3.5)
    move(ctx, menu_index(22, b1), 10)
    server_steps(ctx, 1)
    move(ctx, menu_index(22, b2), 10)
    server_steps(ctx, 1)
    for s in (cement[0], gravel):
        shift_click(ctx, menu_index(22, s))
    e0, _ = stored(ctx, line)
    w0 = tank_of(_lib.block_data(ctx, plant), 'i0')
    t0 = ctx.server()['game_time']
    shift_click(ctx, menu_index(22, sand))
    ctx.step('close')
    k = module_ticks(100)[0]
    advance_to(ctx, t0, k - 1, 'concrete')
    d1 = _lib.block_data(ctx, plant)
    advance_to(ctx, t0, k, 'concrete')
    d2 = _lib.block_data(ctx, plant)
    e1, _ = stored(ctx, line)
    out1, out2 = item_at(d1, 7), item_at(d2, 7)
    left = {}
    for s, (i, n) in items_of(d2).items():
        if 4 <= s <= 6:
            left[i] = left.get(i, 0) + n
    w2 = tank_of(d2, 'i0')
    made_ok = (out1 is None and out2 is not None and out2.get('id') == 'hbmsntm:concrete_smooth' and out2.get('count') == 16
               and w0.get('fill') == 2000 and w0.get('type') == WATER_ID and w2.get('fill', 0) == 0
               and left == {'hbmsntm:powder_cement': 3} and e0 - e1 == 100 * k)
    # the 16 blocks into the hand slot, one placed by hand
    hand_air(ctx)
    open_block(ctx, (px, py, pz + 1), 'MachineChemicalPlantScreen', back=3.5)
    shift_click(ctx, 7)
    ctx.step('close')
    cx, cz = px + 4, pz - 4
    try:
        pos, _ = place(ctx, cx, cz, 'hbmsntm:concrete_smooth', h=1, r=1)
        stands = ctx.server('execute if block %d %d %d hbmsntm:concrete_smooth' % pos, allow_error=True)['result'] == 1
    except Exception as e:  # the placement is part of the expectation
        pos, stands = str(e)[:200], False
    ctx.check('concrete.line', made_ok and stands, 'water before %s (want 2000 of type %d); tick %d output %s; tick %d output %s (want 16 '
              'hbmsntm:concrete_smooth); water after %s; inputs left %s (want 3 cement); stored energy -%d (want 100 x %d); placed block '
              'at %s stands (server): %s' % (w0, WATER_ID, k - 1, out1, k, out2, w2, left, e0 - e1, k, pos, stands))


def section_efurnace(ctx, state, line, reads):
    hand = state.get('efurnace_slot')
    if hand is None:
        raise RuntimeError('no electric furnace in the hotbar from the crafting section')
    pos, _ = place(ctx, X_EFURNACE, OZ, 'hbmsntm:machine_electric_furnace', h=1, hand=hand)
    reads['efurnace'] = pos
    lay_cable(ctx, False, pos[0], pos[2])              # bottom port (MachineElectricFurnaceBlockEntity.java:205-214)
    line['nodes']['efurnace'] = pos
    charge(ctx, line, 'efurnace')
    ore = stock(ctx, [('hbmsntm:ore_lead', 2)])[0]
    open_block(ctx, pos, 'MachineElectricFurnaceScreen', face='up', back=1.5)
    e0, _ = stored(ctx, line)
    t0 = ctx.server()['game_time']
    shift_click(ctx, menu_index(4, ore))
    ctx.step('close')
    reads_at = {}
    for t in (99, 100, 200):
        advance_to(ctx, t0, t, 'electric-furnace')
        reads_at[t] = _lib.block_data(ctx, pos)
    e1, _ = stored(ctx, line)
    ingots = {t: n_of(d, 2, 'hbmsntm:ingot_lead') for t, d in reads_at.items()}
    ok = ingots == {99: 0, 100: 1, 200: 2} and item_at(reads_at[200], 1) is None and e0 - e1 == 50 * 200
    ctx.check('electric-furnace.smelt', ok, 'lead ingots at 99/100/200: %s; input left %s; stored energy -%d (want 50 x 200 = 10000)'
              % (ingots, item_at(reads_at[200], 1), e0 - e1))


def section_mixer(ctx, state, line, reads):
    hand = state.get('mixer_slot')
    if hand is None:
        raise RuntimeError('no mixer in the hotbar from the crafting section')
    pos, _ = place(ctx, X_MIXER, OZ, 'hbmsntm:machine_mixer', h=3, hand=hand)
    reads['mixer'] = pos
    lay_cable(ctx, False, pos[0], pos[2])              # bottom port (MachineMixerBlockEntity.java:82-87)
    line['nodes']['mixer'] = pos
    charge(ctx, line, 'mixer')
    # 预写: the identifier's fluid (custom data Fluid1 = sunflower oil), see PREWRITTEN
    ident, flower = stock(ctx, [('hbmsntm:fluid_identifier_multi[minecraft:custom_data={Fluid1:%d}]' % SUNFLOWEROIL_ID, 1),
                                ('minecraft:sunflower', 1)])
    open_block(ctx, pos, 'MachineMixerScreen', back=2.5, up=0.0)
    move(ctx, menu_index(5, ident), 2)
    server_steps(ctx, 1)
    e0, _ = stored(ctx, line)
    t0 = ctx.server()['game_time']
    move(ctx, menu_index(5, flower), 1)
    ctx.step('close')
    reads_at = {}
    for t in (49, 50):
        advance_to(ctx, t0, t, 'mixer')
        reads_at[t] = _lib.block_data(ctx, pos)
    e1, _ = stored(ctx, line)
    out = {t: {n: (v['fill'], v['type']) for n, v in _lib.tanks(d).items() if v['fill']} for t, d in reads_at.items()}
    oil = [v for v in out[50].values() if v == (100, SUNFLOWEROIL_ID)]
    ok = out[49] == {} and len(oil) == 1 and len(out[50]) == 1 and item_at(reads_at[50], 1) is None and e0 - e1 == 50 * 50
    ctx.check('fluid-mixing.line', ok, 'tanks at 49: %s, at 50: %s (want one tank 100 mB of type %d); sunflower left %s; stored energy -%d '
              '(want 2500); 预写 identifier' % (out[49], out[50], SUNFLOWEROIL_ID, item_at(reads_at[50], 1), e0 - e1))


def tail_start(ctx, state):
    """The tail starts with the list the infrastructure stage starts with: the inventory is emptied of the earlier products."""
    if state.get('tail'):
        return
    cmd(ctx, 'clear @s', allow_error=True)
    for h in range(9):
        cmd(ctx, 'item replace entity @s hotbar.%d with minecraft:stick' % h)
    state['tail'] = True


def section_arc(ctx, state, line, reads):
    if 'assembler' not in state:
        raise RuntimeError('no assembly machine placed')
    tail_start(ctx, state)
    given = stock(ctx, [('hbmsntm:concrete_smooth', 12), ('hbmsntm:ingot_polymer', 8), ('hbmsntm:ingot_firebrick', 16),
                        ('hbmsntm:plate_cast[hbmsntm:meta=11]', 8), ('hbmsntm:transformer', 1), ('hbmsntm:circuit_analog_board', 1)])
    d1, d2, k, used = assembler_run(ctx, state, line, 'ass.arcfurnace', 'block.hbmsntm.machine_arc_furnace', given, 200, 'assembler-arc')
    out1, out2 = item_at(d1, 16), item_at(d2, 16)
    left = {s: v for s, v in items_of(d2).items() if 4 <= s <= 15}
    ok = (out1 is None and out2 is not None and out2.get('id') == 'hbmsntm:machine_arc_furnace' and not left and used == 100 * k)
    ctx.check('arc-furnace.build', ok, 'tick %d output %s; tick %d output %s; inputs left %s; stored energy -%d (want 100 x %d)'
              % (k - 1, out1, k, out2, left, used, k))
    take_output(ctx, state, 'hbmsntm:machine_arc_furnace')
    core, facing = place(ctx, X_ARC, OZ, 'hbmsntm:machine_arc_furnace', h=5, r=4)
    reads['arc'] = core
    d, r = _lib.VEC[facing], _lib.VEC[_lib.clockwise(facing)]
    # the first port proxy (core + 2 x facing + clockwise) and the cell outside it (MachineArcFurnaceBlockEntity.java:421-430,436-447)
    px, pz = core[0] + 2 * d[0] + r[0] + d[0], core[2] + 2 * d[2] + r[2] + d[2]
    lay_cable(ctx, True, px, pz)
    line['nodes']['arc'] = core
    charge(ctx, line, 'arc', needs={core: ARC_NEED})
    stocked = stock(ctx, [('hbmsntm:arc_electrode_graphite', 1), ('hbmsntm:arc_electrode_graphite', 1),
                          ('hbmsntm:arc_electrode_graphite', 1), ('minecraft:sand', 8)])
    front = (core[0] + 2 * d[0], core[1], core[2] + 2 * d[2])
    open_any(ctx, front, 'MachineArcFurnaceScreen', back=4.0, up=0.0)
    for s in stocked[:3]:
        shift_click(ctx, menu_index(30, s))
    da = _lib.block_data(ctx, core)
    e0, _ = stored(ctx, line)
    t0 = ctx.server()['game_time']
    shift_click(ctx, menu_index(30, stocked[3]))
    ctx.step('close')
    close, prog = arc_ticks()
    done = close + prog
    reads_at = {}
    for t in (done - 1, done):
        advance_to(ctx, t0, t, 'arc-furnace')
        reads_at[t] = _lib.block_data(ctx, core)
    e1, _ = stored(ctx, line)

    def nuggets(dd):
        return sum(n for s, (i, n) in items_of(dd).items() if 5 <= s <= 24 and i == 'hbmsntm:nugget_silicon')

    sand_left = sum(n for s, (i, n) in items_of(reads_at[done]).items() if i == 'minecraft:sand')
    ok = (da.get('lid') == 1.0 and nuggets(reads_at[done - 1]) == 0 and nuggets(reads_at[done]) == 8 and sand_left == 0
          and e0 - e1 == 1000 * prog)
    ctx.check('arc-furnace.line', ok, 'lid before %s (want 1.0); simulated %d lid ticks + %d progress ticks = %d; silicon nuggets at %d: %d, at %d: '
              '%d (want 8), sand left %d; stored energy -%d (want 1000 x %d)'
              % (da.get('lid'), close, prog, done, done - 1, nuggets(reads_at[done - 1]), done, nuggets(reads_at[done]), sand_left,
                 e0 - e1, prog))


def section_chip(ctx, state, line, reads):
    if 'assembler' not in state:
        raise RuntimeError('no assembly machine placed')
    tail_start(ctx, state)
    given = stock(ctx, [('hbmsntm:plate_polymer', 1), ('hbmsntm:circuit_printed_silicon_wafer', 1), ('hbmsntm:wire_gold', 1)])
    d1, d2, k, used = assembler_run(ctx, state, line, 'ass.chip', 'item.hbmsntm.circuit_microchip', given, 50, 'assembler-chip')
    out1, out2 = item_at(d1, 16), item_at(d2, 16)
    left = {s: v for s, v in items_of(d2).items() if 4 <= s <= 15}
    ok = (out1 is None and out2 is not None and out2.get('id') == 'hbmsntm:circuit_microchip' and out2.get('count', 1) == 1
          and not left and used == 250 * k)
    ctx.check('silicon-chips.chip', ok, 'ass.chip in the selector list; tick %d output %s; tick %d output %s; inputs left %s; stored '
              'energy -%d (want 250 x %d)' % (k - 1, out1, k, out2, left, used, k))
    core = state['assembler']
    open_block(ctx, (core[0], core[1], core[2] + 1), 'MachineAssemblyMachineScreen', back=3.5)
    shift_click(ctx, 16)
    ctx.step('close')


def section_centrifuge(ctx, state, line, reads):
    if 'assembler' not in state:
        raise RuntimeError('no assembly machine placed')
    tail_start(ctx, state)
    given = stock(ctx, [('hbmsntm:plate_dura_steel', 4), ('hbmsntm:plate_titanium', 4), ('hbmsntm:motor', 1)])
    a1, a2, ka, used_a = assembler_run(ctx, state, line, 'ass.centrifugetower', 'item.hbmsntm.centrifuge_element', given, 100,
                                       'assembler-tower')
    core = state['assembler']
    open_block(ctx, (core[0], core[1], core[2] + 1), 'MachineAssemblyMachineScreen', back=3.5)
    shift_click(ctx, 16)
    ctx.step('close')
    element = slots_of(inventory(ctx), 'hbmsntm:centrifuge_element')
    given = stock(ctx, [('hbmsntm:ingot_polymer', 4), ('hbmsntm:plate_steel', 8), ('hbmsntm:plate_copper', 4),
                        ('hbmsntm:circuit_analog_board', 1)])
    if not element:
        raise RuntimeError('no centrifuge element after ass.centrifugetower: tick %d output %s' % (ka, item_at(a2, 16)))
    b1, b2, kb, used_b = assembler_run(ctx, state, line, 'ass.centrifuge', 'block.hbmsntm.machine_centrifuge', element[:1] + given, 200,
                                       'assembler-centrifuge')
    ok = (item_at(a1, 16) is None and (item_at(a2, 16) or {}).get('id') == 'hbmsntm:centrifuge_element' and used_a == 100 * ka
          and item_at(b1, 16) is None and (item_at(b2, 16) or {}).get('id') == 'hbmsntm:machine_centrifuge' and used_b == 100 * kb
          and not {s: v for s, v in items_of(b2).items() if 4 <= s <= 15})
    ctx.check('centrifuge.build', ok, 'tower: tick %d %s, tick %d %s, stored -%d (want 100 x %d); centrifuge: tick %d %s, tick %d %s, stored -%d '
              '(want 100 x %d)' % (ka - 1, item_at(a1, 16), ka, item_at(a2, 16), used_a, ka, kb - 1, item_at(b1, 16), kb, item_at(b2, 16),
                                   used_b, kb))
    take_output(ctx, state, 'hbmsntm:machine_centrifuge')
    pos, _ = place(ctx, X_CENTRIFUGE, OZ, 'hbmsntm:machine_centrifuge', h=4)
    reads['centrifuge'] = pos
    lay_cable(ctx, False, pos[0], pos[2])              # bottom port (MachineCentrifugeBlockEntity.java:234-243)
    line['nodes']['centrifuge'] = pos
    charge(ctx, line, 'centrifuge')
    ore = stock(ctx, [('hbmsntm:ore_lead_deepslate', 1)])[0]
    open_block(ctx, pos, 'MachineCentrifugeScreen', back=2.5, up=0.0)
    e0, _ = stored(ctx, line)
    t0 = ctx.server()['game_time']
    shift_click(ctx, menu_index(8, ore))
    ctx.step('close')
    reads_at = {}
    for t in (199, 200):
        advance_to(ctx, t0, t, 'centrifuge')
        reads_at[t] = _lib.block_data(ctx, pos)
    e1, _ = stored(ctx, line)

    def outs(dd):
        o = {}
        for s, (i, n) in items_of(dd).items():
            if 2 <= s <= 5:
                o[i] = o.get(i, 0) + n
        return o

    want = {'hbmsntm:powder_lead': 2, 'hbmsntm:powder_gold': 1, 'minecraft:gravel': 1}
    ok = outs(reads_at[199]) == {} and outs(reads_at[200]) == want and item_at(reads_at[200], 0) is None and e0 - e1 == 200 * 200
    ctx.check('centrifuge.line', ok, 'outputs at 199: %s, at 200: %s (want %s); input left %s; stored energy -%d (want 40000)'
              % (outs(reads_at[199]), outs(reads_at[200]), want, item_at(reads_at[200], 0), e0 - e1))


def section_crystallizer(ctx, state, line, reads):
    if 'chemplant' not in state:
        raise RuntimeError('no chemical plant with peroxide')
    tail_start(ctx, state)
    plant = state['chemplant']
    cmd(ctx, 'item replace entity @s hotbar.%d with hbmsntm:machine_crystallizer' % HAND)
    # the acidizer's core three blocks east of the plant's: its corner proxies (core -1, z +-1) are the plant's ports (x + 2, z +-1)
    core, facing = place(ctx, plant[0] + 3, plant[2] + 1, 'hbmsntm:machine_crystallizer', h=6)
    if core != (plant[0] + 3, plant[1], plant[2]):
        raise RuntimeError('acidizer core %s, expected %s' % (core, (plant[0] + 3, plant[1], plant[2])))
    reads['crystallizer'] = core
    lay_cable(ctx, True, core[0] + 2, core[2] + 1)     # port (x + 2, z + 1) (MachineCrystallizerBlockEntity.java:115-121)
    line['nodes']['crystallizer'] = core
    # the plant ran other recipes after its peroxide (coltan cleaning, concrete): chem.peroxide again and one water bucket give
    # 1,000 mB (ChemicalPlantRecipes.java:214-216), which the plant hands to the acidizer while the line charges
    dp = _lib.block_data(ctx, plant)
    o0 = _lib.tanks(dp).get('o0') or {}
    if dp.get('recipe0') != 'chem.peroxide' or o0.get('type') != PEROXIDE_ID or o0.get('fill', 0) < 500:
        bucket = stock(ctx, [('minecraft:water_bucket', 1)])[0]
        if dp.get('recipe0') != 'chem.peroxide':
            open_block(ctx, (plant[0], plant[1], plant[2] + 1), 'MachineChemicalPlantScreen', back=3.5)
            got = pick_recipe(ctx, plant, 'hbmChemicalPlant.json', 'chem.peroxide', 'chem.peroxide')
            ctx.step('close')
            if got != 'chem.peroxide':
                raise RuntimeError('plant recipe after the selector: %r' % got)
        open_block(ctx, (plant[0], plant[1], plant[2] + 1), 'MachineChemicalPlantScreen', back=3.5)
        move(ctx, menu_index(22, bucket), 10)
        ctx.step('close')
    charge(ctx, line, 'crystallizer', needs={core: CRYSTAL_NEED})
    d0 = _lib.block_data(ctx, core)
    acid0 = _lib.tanks(d0)
    ore = stock(ctx, [('hbmsntm:ore_aluminium', 1)])[0]
    open_block(ctx, (core[0], core[1], core[2] + 1), 'MachineCrystallizerScreen', back=3.5)
    e0, _ = stored(ctx, line)
    # the plant's tanks at the start of the window: a source of peroxide (in its output tanks, or water it would still turn into
    # peroxide) would keep flowing into the acidizer during the 601 ticks (MachineChemicalPlantBlockEntity.java:104-123)
    plant0 = _lib.tanks(_lib.block_data(ctx, plant))
    t0 = ctx.server()['game_time']
    shift_click(ctx, menu_index(8, ore))
    ctx.step('close')
    reads_at = {}
    for t in (600, 601):
        advance_to(ctx, t0, t, 'acidizer')
        reads_at[t] = _lib.block_data(ctx, core)
    e1, _ = stored(ctx, line)
    plant1 = _lib.tanks(_lib.block_data(ctx, plant))

    def plant_source(tk):
        return (sum(v['fill'] for k, v in tk.items() if k in ('o0', 'o1', 'o2') and v['type'] == PEROXIDE_ID)
                + sum(v['fill'] for k, v in tk.items() if k in ('i0', 'i1', 'i2') and v['type'] == WATER_ID))

    def plant_show(tk):
        return {k: (v['fill'], v['type']) for k, v in sorted(tk.items()) if k in ('i0', 'i1', 'i2', 'o0', 'o1', 'o2')}

    tank0 = next(iter(acid0.values()), {})
    tank1 = next(iter(_lib.tanks(reads_at[601]).values()), {})
    crystals = {t: n_of(dd, 2, 'hbmsntm:crystal_aluminium') for t, dd in reads_at.items()}
    ok = (tank0.get('fill', 0) >= 500 and tank0.get('type') == PEROXIDE_ID and crystals == {600: 0, 601: 1}
          and len(plant0) == 6 and plant_source(plant0) == 0
          and tank1.get('fill') == tank0.get('fill', 0) - 500 and item_at(reads_at[601], 0) is None and e0 - e1 == 1000 * 601)
    ctx.check('crystallization.line', ok, 'peroxide fed from the plant before %s; plant tanks (fill, type) at the start %s, peroxide or water '
              'there %d mB (want 0), after %s; crystals at 600/601 %s; tank after %s (want -500); ore left %s; '
              'stored energy -%d (want 1000 x 601)' % (tank0, plant_show(plant0), plant_source(plant0), plant_show(plant1), crystals,
                                                      tank1, item_at(reads_at[601], 0), e0 - e1))


def section_compressor(ctx, state, line, reads):
    if 'assembler' not in state:
        raise RuntimeError('no assembly machine placed')
    inv = inventory(ctx)
    if count(inv, 'hbmsntm:circuit_analog_board') < 1:
        raise RuntimeError('no second analog board from the soldering section')
    if inv.get(5, {}).get('id') != 'hbmsntm:barrel_steel' or inv.get(4, {}).get('id') != 'hbmsntm:fluid_identifier_multi':
        raise RuntimeError('barrel / identifier not in hotbar slots 5 / 4: %s / %s' % (inv.get(5), inv.get(4)))
    given = stock(ctx, [('hbmsntm:plate_cast[hbmsntm:meta=11]', 8), ('hbmsntm:plate_copper', 4), ('hbmsntm:shell_steel', 2),
                        ('hbmsntm:motor', 3)])
    analog = slots_of(inventory(ctx), 'hbmsntm:circuit_analog_board')[0]
    d1, d2, k, used = assembler_run(ctx, state, line, 'ass.compressor', 'block.hbmsntm.machine_compressor', given + [analog], 200,
                                    'assembler-compressor')
    out1, out2 = item_at(d1, 16), item_at(d2, 16)
    left = {s: v for s, v in items_of(d2).items() if 4 <= s <= 15}
    ctx.check('fluid-compression.build', out1 is None and (out2 or {}).get('id') == 'hbmsntm:machine_compressor' and not left
              and used == 100 * k, 'tick %d output %s; tick %d output %s; inputs left %s; stored energy -%d (want 100 x %d)'
              % (k - 1, out1, k, out2, left, used, k))
    take_output(ctx, state, 'hbmsntm:machine_compressor')
    core, facing = place(ctx, X_COMPRESSOR, OZ, 'hbmsntm:machine_compressor', h=8)
    side = _lib.VEC[_lib.clockwise(facing)]
    # ports: one block outside the proxies beside the core and behind it (MachineCompressorBlockEntity.java:86-96)
    west = (core[0] + 2 * side[0], core[2] + 2 * side[2])
    east = (core[0] - 2 * side[0], core[2] - 2 * side[2])
    lay_cable(ctx, True, west[0], west[1])
    reads['compressor'] = core
    line['nodes']['compressor'] = core
    # the second wood burner
    cmd(ctx, 'item replace entity @s hotbar.%d with hbmsntm:machine_wood_burner' % HAND)
    b2, f2 = place(ctx, X_BURNER2, OZ, 'hbmsntm:machine_wood_burner', h=2, dz=3.5)
    if f2 != 'south':
        raise RuntimeError('second burner facing %s' % f2)
    lay_cable(ctx, True, b2[0], b2[2] - 2)
    logs = stock(ctx, [('minecraft:oak_log', 16)])[0]
    open_block(ctx, b2, 'MachineWoodBurnerScreen', back=2.5, up=0.0)
    move(ctx, menu_index(6, logs), 0)
    ctx.step('close')
    line.setdefault('more_burners', []).append(b2)
    reads['burner2'] = b2
    # the barrel at the east port
    place(ctx, east[0], east[1], 'hbmsntm:barrel_steel', h=1, hand=5)
    barrel = (east[0], Y, east[1])
    # the identifier set to water in its own screen (Shift + use in the air); WATER is the fourth entry of the unfiltered list
    # (Fluids.java:421-425, FluidScreen)
    select_hotbar(ctx, 4)
    ctx.step('view', pos=[east[0] + 0.5, Y, east[1] + 4.5], pitch=-60.0, yaw=0.0, fly=True, hide_gui=False)
    ctx.step('key', key='key.keyboard.left.shift', action='press', after=3)
    ctx.step('mouse', button=1, action='click', after=4)
    ctx.step('key', key='key.keyboard.left.shift', action='release', after=2)
    ctx.step('screen', expect='FluidScreen')
    ctx.step('key', key='key.keyboard.backspace', action='tap', after=2)
    hud = ctx.step('hud', frames=2)
    left_, top_ = (hud['gui_scaled_width'] - 176) // 2, (hud['gui_scaled_height'] - 54) // 2
    ctx.step('click', at=[left_ + 7 + 3 * 18 + 9, top_ + 29 + 9], button=0, after=4)
    ctx.step('close')
    ident = inventory(ctx).get(4, {})
    if ident.get('components', {}).get('minecraft:custom_data', {}).get('Fluid1') != WATER_ID:
        raise RuntimeError('identifier after its screen: %s' % ident)
    bucket = stock(ctx, [('minecraft:water_bucket', 1)])[0]
    open_block(ctx, barrel, 'BarrelScreen', back=2.5, up=0.0)
    move(ctx, menu_index(6, 4), 0)
    server_steps(ctx, 1)
    move(ctx, 1, menu_index(6, 4))
    move(ctx, menu_index(6, bucket), 2)
    server_steps(ctx, 1)
    hud = ctx.step('hud', frames=2)
    for _ in range(2):
        ctx.step('click', at=[hud['gui_left'] + 160, hud['gui_top'] + 43], button=0, after=4)
    ctx.step('close')
    db = _lib.block_data(ctx, barrel)
    tb = _lib.tanks(db).get('tank', {})
    if tb.get('fill') != 1000 or tb.get('type') != WATER_ID or db.get('mode') != 2:
        raise RuntimeError('barrel not loaded: tank %s, mode %s' % (tb, db.get('mode')))
    charge(ctx, line, 'compressor', burners=[b2])
    total, parts = stored(ctx, line)
    open_any(ctx, (core[0], core[1], OZ), 'MachineCompressorScreen', back=3.0, up=0.0)
    e0 = total
    # the input tank before the identifier goes in: untyped, so the barrel's water had no demand to go to (getDemand by type)
    d_start = _lib.block_data(ctx, core)
    t0 = ctx.server()['game_time']
    move(ctx, menu_index(4, 4), 0)
    ctx.step('close')
    reads_at = {}
    for t in (99, 100, 101):
        advance_to(ctx, t0, t, 'compressor')
        reads_at[t] = _lib.block_data(ctx, core)
    e1, parts1 = stored(ctx, line)
    dd = reads_at[101]
    ok = (d_start.get('0', 0) == 0 and reads_at[99].get('1', 0) == 0 and reads_at[100].get('1', 0) == 0 and dd.get('1') == 1000
          and dd.get('1_type') == WATER_ID and dd.get('1_p') == 1 and dd.get('0', 0) == 0 and e0 - e1 == 2500 * 100)
    ctx.check('fluid-compression.line', ok, 'stored before %d (%s); input before the identifier %s mB type %s; output at 99: %s mB, at 100: '
              '%s mB (want 0, 0); at 101: %s mB type %s pressure %s (want 1000, %d, 1), input left %s; stored energy -%d '
              '(want 2500 x 100 = 250000)'
              % (e0, parts, d_start.get('0'), d_start.get('0_type'), reads_at[99].get('1'), reads_at[100].get('1'), dd.get('1'),
                 dd.get('1_type'), dd.get('1_p'), WATER_ID, dd.get('0'), e0 - e1))
