"""Main line, oil stage: the oil well drills down to an oil deposit and pumps it, a heat boiler on a firebox heats the oil, the
refinery splits the hot oil, the fractioning tower splits its heavy oil and the catalytic cracker cracks the tower's bitumen,
all connected by real fluid ducts typed with a fluid identifier. The well, the refinery, the chemical plant and the vacuum
refinery take their power from wood burners on red cable. Beside the line: the coker, the vacuum refinery, the fluid
containers that carry light oil and mercury (combination oven, cinnabar) into the chemical plant for ten desh ingots, the
iron anvil upgraded with them to the desh anvil (tier 3), the industrial boiler, the electric pump and the electric heater
built on that anvil, and the power groups the oil products feed: diesel generator, combustion engine, turbofan, and the
electric pump, industrial boiler and industrial turbine chained by real pipes and a red cable.

Every expected number comes from the NEO code and, for a port, the 1.7.10 original (the source column of each expectation).
Machines are placed by hand (item in the main hand, use on a face; on a firebox or heater while sneaking), opened by
right-click and loaded with slot clicks; recipes are chosen in the machine's recipe selector and anvil constructions by
paging the anvil's list. Start items are handed out by command. A state written by command
instead of being produced on the line is 预写; its expectation text says so ("预写") and PREWRITES lists all.
Readings are the server's block-entity data. The power and fluid networks keep moving energy and fluid for up to 3 s of
wall time after the world is frozen (they run on the server tick event, which a frozen server still fires,
NtmEventHandler.java:69-76; provider entries expire after 3,000 ms, PowerNetMK2.java:22,42,61), so a set of readings of
several connected blocks is taken only after 4 s in the frozen world. At the end the world is left and opened again and
every section's readings are compared with the ones taken before leaving.
"""
import json
import math
import sys
from math import comb
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import _lib  # noqa: E402
import common  # noqa: E402

FEATURES = ['oil-extraction', 'oil-refining', 'fractionation', 'catalytic-cracking', 'oil-coking', 'vacuum-refinery',
            'fluid-container-transfer', 'diesel-power', 'combustion-power', 'turbofan-power', 'industrial-turbine',
            'industrial-steam', 'heaters']

SCENARIO = dict(
    id='oil-extraction.mainline_stage5',
    feature='oil-extraction',
    features=FEATURES,
    title='Main line, oil stage: well, heater, refinery, tower, cracker, coker, vacuum refinery, desh, tier-3 anvil machines, '
          'power from oil products',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

# Items the line uses besides the ones a player has before the oil stage. The first group are earlier-stage items (ducts, identifier,
# cable, wood burners and their logs, coal, containers, the iron anvil, the steel piston set, the screwdriver, lead pipes,
# stone bricks) that no oil-stage recipe consumes; the second are this stage's own
# machines and intermediates whose making is not played here.
EXTRA_EARLIER = ['hbmsntm:fluid_duct_neo', 'hbmsntm:fluid_identifier_multi', 'hbmsntm:red_cable', 'hbmsntm:machine_wood_burner',
                 'minecraft:oak_log', 'minecraft:coal', 'hbmsntm:fluid_tank_empty', 'hbmsntm:anvil (iron)', 'hbmsntm:piston_set (steel)',
                 'hbmsntm:screwdriver', 'hbmsntm:pipe_lead', 'minecraft:stone_bricks', 'minecraft:dirt', 'minecraft:redstone_block']
EXTRA_THIS_STAGE = [
    ('hbmsntm:machine_well', 'AssemblyMachineRecipes.java:62 (original AssemblyMachineRecipes.java:297)'),
    ('hbmsntm:machine_refinery', 'AssemblyMachineRecipes.java:44 (original :313)'),
    ('hbmsntm:machine_fraction_tower', 'NtmRecipeProvider.java:2325 (original CraftingManager.java:298)'),
    ('hbmsntm:machine_catalytic_cracker', 'AssemblyMachineRecipes.java:378 (original :316)'),
    ('hbmsntm:machine_coker', 'AssemblyMachineRecipes.java:268 (original :323)'),
    ('hbmsntm:machine_vacuum_distill', 'AssemblyMachineRecipes.java:633 (original :327)'),
    ('hbmsntm:machine_diesel', 'AssemblyMachineRecipes.java:342 (original :411)'),
    ('hbmsntm:machine_combustion_engine', 'AssemblyMachineRecipes.java:318 (original :414)'),
    ('hbmsntm:machine_turbofan', 'AssemblyMachineRecipes.java:311 (original :425)'),
    ('hbmsntm:machine_industrial_turbine', 'AssemblyMachineRecipes.java:439 (original :434)'),
    # the plastic the three tier-3 anvil constructions take: chem.polymer needs fluorite, which a player does not have before this stage
    ('hbmsntm:ingot_polymer', 'ChemicalPlantRecipes.java:175 (original ChemicalPlantRecipes.java:209)'),
]
# Every state written by command instead of produced on the line (each expectation that rests on one says "预写").
PREWRITES = [
    '预写 catalytic cracker: 8,000 mB steam (a steam boiler line with its own water source is not part of this line)',
    '预写 coker: 11,000 mB heavy oil, one batch (the line makes far less heavy oil than one coker batch)',
    '预写 vacuum refinery: 1,000 mB crude oil at pressure 2 (the compressor line is not played; its power comes from a wood burner)',
    '预写 diesel generator: 8,000 mB diesel (no diesel is made on this line; it also powers the electric pump later)',
    '预写 combustion engine: 300 mB diesel (no diesel is made on this line)',
    '预写 turbofan: 100 mB kerosene (no kerosene is made on this line)',
]

Y = -45          # machine level; the floor is one block below
PARK = [20.5, Y + 10, 20.5]
WELL = (0, Y, 0)
FIRE1, BOIL = (6, Y, 0), (6, Y + 1, 0)
REFI = (12, Y, 0)
TOWER = (16, Y, 1)
CRACK = (23, Y, -1)
FIRE2, COKER = (0, Y, 20), (0, Y + 1, 20)
VAC = (10, Y, 20)
FIRE3, OVEN = (20, Y, 20), (20, Y + 1, 20)
CHEM = (28, Y, 20)
ANVIL = (34, Y, 20)
ANVIL3 = (38, Y, 20)
DIESEL = (0, Y, 40)
PUMP = (6, Y, 40)
FIRE4, IBOIL = (12, Y, 40), (12, Y + 1, 40)
TURB = (19, Y, 41)
COMB = (27, Y, 40)
FAN = (38, Y, 44)
HEATER, HOVEN = (30, Y, 60), (30, Y + 1, 60)
# Wood burners (core facing south; power ports two blocks behind the core and one further clockwise,
# MachineWoodBurnerBlockEntity.java:222-231) and the red cable from a port to the consumer's port.
BURN_WELL = (-3, Y, 4)       # well port (-1, Y, 0): MachineOilWellBlockEntity.java:104-114
CABLE_WELL = [(-3, Y, 2), (-3, Y, 1), (-3, Y, 0), (-2, Y, 0), (-1, Y, 0)]
BURN_REFI = (11, Y, 6)       # refinery port (11, Y, 2): MachineRefineryBlockEntity.java:230-240
CABLE_REFI = [(11, Y, 4), (11, Y, 3), (11, Y, 2)]
BURN_CHEM = (26, Y, 25)      # chemical plant port (26, Y, 21): MachineChemicalPlantBlockEntity.java:210-226
CABLE_CHEM = [(26, Y, 23), (26, Y, 22), (26, Y, 21)]
BURN_VAC = (9, Y, 26)        # vacuum refinery port (9, Y, 22): MachineVacuumDistillBlockEntity.java:160-171
CABLE_VAC = [(9, Y, 24), (9, Y, 23), (9, Y, 22)]
BURN_HEAT = [(28, Y, 67), (33, Y, 67)]
CABLE_HEAT = [(30, Y, 63), (30, Y, 64)] + [(x, Y, 65) for x in range(27, 34)]   # heater port: core + 3 x facing (HeaterElectricBlockEntity.java:47-50)

# FluidType ids are registration order (Fluids.registerSelf, Fluids.java:950-956; declarations Fluids.java:250-356)
FL = dict(NONE=0, WATER=1, STEAM=2, OIL=10, HOTOIL=11, HEAVYOIL=12, BITUMEN=13, SMEAR=14, NAPHTHA=19, DIESEL=20, LIGHTOIL=21,
          KEROSENE=22, GAS=23, PETROLEUM=24, MERCURY=42, SPENTSTEAM=48, AROMATICS=67, HEAVYOIL_VACUUM=90, REFORMATE=91,
          LIGHTOIL_VACUUM=92, SOURGAS=93, OIL_COKER=104)

# ---- numbers from the code
BURNER_MAX, BURNER_GEN = 100_000, 100                 # MachineWoodBurnerBlockEntity.java:42-43 (original TileEntityMachineWoodBurner.java:40,49)
LOG_TICKS = 300 * 4                                  # vanilla log burn time 300 x log time mod 4 (MachineWoodBurnerBlockEntity.java:53-55; original :49,110)
WELL_POWER, WELL_USE, WELL_DELAY = 100_000, 100, 50   # MachineOilWellBlockEntity.java:31-33 (original TileEntityMachineOilWell.java:32-34)
OIL_PER_PUMP, GAS_MIN, GAS_MAX, DRAIN = 500, 100, 500, 0.05  # :34-37,93-100 (original :35-38,97-104)
WELL_PHASE = 40                                      # the frozen world is brought to game time 40 mod 50: each 50-tick window holds the well's cycle at its 10th tick
LINE_WINDOWS = 24                                    # 8 pumps before the line + 24 = 16,000 mB crude oil, enough refined light oil for two tanks
REF_POWER, REF_USE, REF_IN = 1_000, 5, 100           # MachineRefineryBlockEntity.java:49,186,197,226 (original TileEntityMachineRefinery.java:54,282,291,318)
REF_OUT = dict(heavy=50, naphtha=25, light=15, petroleum=10)  # RefineryRecipes.java:15-18 (original RefineryRecipes.java:26-29)
SULFUR_EVERY = 10                                   # MachineRefineryBlockEntity.java:48,205 (original :53,297)
FRAC_IN, FRAC_BIT, FRAC_SMEAR = 100, 30, 70          # MachineFractionTowerBlockEntity.java:55,97-102; FractionRecipes.java:28 (original TileEntityMachineFractionTower.java:69,101-111; FractionRecipes.java:26)
CRACK_STEAM0 = 8000                                  # 预写 steam, the cracker's steam tank size (MachineCatalyticCrackerBlockEntity.java:37)
CRACK_IN, CRACK_STEAM, CRACK_OIL, CRACK_AROMA, CRACK_SPENT = 100, 200, 80, 20, 2  # MachineCatalyticCrackerBlockEntity.java:58,82-88; CrackingRecipes.java:22-23,42 (original TileEntityMachineCatalyticCracker.java:45,72-78)
# Coker auto recipe: 820,000 TU * 1000 / max(flammable, combustible) of heavy oil; heavy oil's final traits come from
# registerCalculatedFuel(HEAVYOIL, 100,000 / 0.5 * 0.25 * 1.0 * 1.1, 1.25) = flammable 55,000, combustible 68,700 after
# rounding (Fluids.java:686,910-932; original Fluids.java:712,935). 820,000,000 / 68,700 = 11,935 -> above 10,000 rounded down
# to 11,000; byproduct max(10, 11,000 / 10) = 1,100 coker oil (CokerRecipes.java:106-131; original CokerRecipes.java:71-91).
COKE_IN, COKE_BY, COKE_TIME = 11_000, 1_100, 20_000  # MachineCokerBlockEntity.java:44 (original TileEntityMachineCoker.java:43)
VAC_IN0 = 1_000
VAC_USE, VAC_PER = 10_000, 100                       # MachineVacuumDistillBlockEntity.java:39-41 (original TileEntityMachineVacuumDistill.java:165-171)
VAC_OUT = dict(heavy=40, reformate=25, light=20, gas=15)  # VacuumRefineryRecipes.java:17-20 (original VacuumRefineryRecipes.java:20-23)
CINNABAR, HG_PER = 20, 100                           # CombinationRecipes.java:40 (original CombinationRecipes.java:51)
TANK_CAP = 1000                                      # universal fluid tank, FluidContainerRegistry.java:55
TANKS = 2                                            # two tanks each of light oil and mercury
DESH_N, DESH_LIGHT, DESH_HG = 10, 200, 200           # ChemicalPlantRecipes.java:167-170 (original ChemicalPlantRecipes.java:202-207)
CHEM_USE, CHEM_TICKS = 100, 100                      # chem.desh setupNamed(100, 100L): 100 ticks at 100 HE a tick (ChemicalPlantRecipes.java:167)
# Diesel: registerCalculatedFuel(DIESEL, 100,000 / 0.21 * 1.0 * 1.0 * 1.1 * 1.05, 2.5) -> combustible 1,370,000 HE/bucket
# (Fluids.java:698,910-932; original Fluids.java:724,935); the generator gives 1,370,000 / 1000 * 0.75 (HIGH) per mB, one mB a tick
# (MachineDieselBlockEntity.java:74-88,135-145; original TileEntityMachineDiesel.java:59,243-251,266-275).
DIESEL_FUEL, DIESEL_HE, DIESEL_CAP, DIESEL_N = 8000, 1027, 50_000, 40
# Combustion engine: per tick setting * 2 tenths of a mB, each giving combustible / 10,000 HE * piston efficiency; steel
# pistons burn HIGH grade at 0.25 (MachineCombustionEngineBlockEntity.java:136-151, PistonSetItem.java:29; original
# TileEntityMachineCombustionEngine.java:87-110, ItemPistons.java:54): 60 * 137 * 0.25 = 2,055 HE and 6 mB a tick at setting 30.
COMB_FUEL, COMB_SET, COMB_HE, COMB_MB, COMB_N = 300, 30, 2055, 6, 50
# Turbofan: kerosene combustible = registerCalculatedFuel(KEROSENE, 100,000 / 0.09 * 1.0 * 2.0 * 1.1 * 1.05, 1.5) = 3,850,000
# (Fluids.java:703; original Fluids.java:729); 3,850 HE per mB, one mB a tick without afterburner
# (MachineTurbofanBlockEntity.java:125-130,166-176; original TileEntityMachineTurbofan.java:188,204-211).
FAN_FUEL, FAN_HE, FAN_N = 100, 3850, 60
PUMP_SPEED, PUMP_USE = 10_000, 1_000                 # MachinePumpElectricBlockEntity.java:39,128-131 (original TileEntityMachinePumpElectric.java:16,33-39)
STEAM_PER_WATER, HEAT_PER_WATER = 100, 200           # Fluids.java:603-604 WATER addStep(200, 1, STEAM, 100) (original Fluids.java:629-630)
TURB_SPENT_PER, TURB_TU_PER_OP = 100, 200                                 # Fluids.java:611 STEAM FT_Coolable(SPENTSTEAM, 100, 1, 200) (original :637)
TURB_MAXPOWER = 1500 * 200                           # ceil(750,000 * 0.2 / 100) ops * 200 TU (MachineIndustrialTurbineBlockEntity.java:28,63-64,161; original TileEntityMachineIndustrialTurbine.java:34,84-85)
# Electric heater: one screwdriver click from the default 0 gives setting 1; it draws (long) (1^1.4 * 200) = 200 HE and makes
# 1 * 100 = 100 TU in every tick it has the power (HeaterElectricBlockEntity.java:32,56-60,120-138; original
# TileEntityHeaterElectric.java:61-63,161-162,173-183); two wood burners give exactly those 200 HE a tick.
HEAT_SET, HEAT_USE, HEAT_GEN, HEAT_CINNABAR = 1, 200, 100, 5
STEEL_CAST = 11                                      # CastPlateItem.Type.STEEL is the 12th type (CastPlateItem.java:37-49)
ANVIL_TIER = 3                                       # NTMAnvilBlock.Variant.DESH (NTMAnvilBlock.java:57-77)
ANVIL_PAGE = 10                                      # AnvilMenuScreen.java:30
# placed from the south the anvil faces south and is 12 px high, 8 px deep (z 4..12): aim at the middle of that face
ANVIL_AIM = (0.0, -0.25, -0.25)                      # NTMAnvilBlock.java:93,114-116,131-132

SRC = dict(
    well='MachineOilWellBlockEntity.java:31-37,93-100; OilDrillBaseBlockEntity.java:133-165,220-232; MachineWoodBurnerBlockEntity.java:42-43,'
         '118-141 (original TileEntityMachineOilWell.java:32-38,97-104; TileEntityOilDrillBase.java:123-140; TileEntityMachineWoodBurner.java:40,49,'
         '110,118-120)',
    boiler='MachineHeatBoiler.java:99-125; AbstractBoilerBlockEntity.java:133-151; Fluids.java:616 OIL addStep(10, 1, HOTOIL, 1) (original '
           'TileEntityHeatBoiler.java:202,218-227; Fluids.java:642)',
    refinery='MachineRefineryBlockEntity.java:48-49,165-228; RefineryRecipes.java:15-18 (original TileEntityMachineRefinery.java:53-54,282-318; '
             'RefineryRecipes.java:26-29,48)',
    tower='MachineFractionTowerBlockEntity.java:55,91-103; FractionRecipes.java:28 (original TileEntityMachineFractionTower.java:69,101-111; '
          'FractionRecipes.java:26)',
    cracker='MachineCatalyticCrackerBlockEntity.java:35-40,58,74-88; CrackingRecipes.java:22-23,42 (original TileEntityMachineCatalyticCracker.java:'
            '45,72-78; CrackingRecipes.java:44)',
    coker='MachineCokerBlockEntity.java:44,120-127; CokerRecipes.java:69,106-131; Fluids.java:686,910-932 (original TileEntityMachineCoker.java:43,'
          '87-89; CokerRecipes.java:33,71-91; Fluids.java:712,935)',
    vacuum='MachineVacuumDistillBlockEntity.java:39-41,54,130-167; VacuumRefineryRecipes.java:17-20,26-30; MachineWoodBurnerBlockEntity.java:42-43 '
           '(original TileEntityMachineVacuumDistill.java:36,165-171; VacuumRefineryRecipes.java:20-23,30)',
    containers='FluidContainerRegistry.java:55; FluidTank.java:120-132; MachineFurnaceCombinationBlockEntity.java:39,78,91-101; CombinationRecipes.java:40; '
               'MachineRefineryBlockEntity.java:108; MachineChemicalPlantBlockEntity.java:104-105 (original CombinationRecipes.java:51; '
               'TileEntityFurnaceCombination.java:38,71-83)',
    desh='ChemicalPlantRecipes.java:167-170; ModuleMachineBase.java:64-65,115-127; MachineChemicalPlantBlockEntity.java:53,73-77,96-99; '
         'MachineChemicalPlantScreen.java:44-59; MachineWoodBurnerBlockEntity.java:42-43 (original ChemicalPlantRecipes.java:202-207)',
    anvil='AnvilRecipes.java:104,160-169; NTMAnvilBlock.java:57-70 (original AnvilRecipes.java:63-67)',
    build='AnvilRecipes.java:559-588; AnvilMenuScreen.java:45-50,93,125-136,225-240 (original AnvilRecipes.java:263-271,409-415)',
    diesel='MachineDieselBlockEntity.java:47,74-88,135-145; Fluids.java:698,910-932; MachineDieselScreen.java:85-91 (original '
           'TileEntityMachineDiesel.java:59,243-251,266-275; Fluids.java:724)',
    combustion='MachineCombustionEngineBlockEntity.java:82-86,136-151,296-301; PistonSetItem.java:29; MachineCombustionEngineScreen.java:99-141 '
               '(original TileEntityMachineCombustionEngine.java:87-110; ItemPistons.java:54)',
    turbofan='MachineTurbofanBlockEntity.java:125-130,166-176; Fluids.java:703 (original TileEntityMachineTurbofan.java:188,204-211; Fluids.java:729)',
    pump='MachinePumpElectricBlockEntity.java:39,97-99,128-131,171-178 (original TileEntityMachinePumpElectric.java:16,33-39)',
    iboiler='MachineIndustrialBoilerBlockEntity.java:26-44; AbstractBoilerBlockEntity.java:133-151; Fluids.java:603-604 (original '
            'TileEntityHeatBoilerIndustrial.java:45; TileEntityHeatBoiler.java:218-227; Fluids.java:629-630)',
    turbine='TurbineBaseBlockEntity.java:66-72; MachineIndustrialTurbineBlockEntity.java:28,36,60-75,161; Fluids.java:611 (original '
            'TileEntityTurbineBase.java:71-77; TileEntityMachineIndustrialTurbine.java:34,84-85,90-95; Fluids.java:637)',
    heater_build='AnvilRecipes.java:602-622; AnvilMenuScreen.java:45-50,93,125-136,225-240 (original AnvilRecipes.java:302-309)',
    heater='HeaterElectricBlockEntity.java:32,47-60,111-138,146-148; HeaterElectricBlock.java:103-121; MachineFurnaceCombinationBlockEntity.java:39,'
           '90-104,184-197; CombinationRecipes.java:40; MachineWoodBurnerBlockEntity.java:42-43 (original TileEntityHeaterElectric.java:56-63,156,'
           '161-162,173-183; TileEntityFurnaceCombination.java:38,74-83; CombinationRecipes.java:51)',
)

EXPECTED = [
    ('oil-extraction', 'well-drill', 'the well on a wood burner drills one block a 50-tick cycle: the first two cycles turn the floor and the stone '
                                     'below it into oil pipe and add no fluid', 'well'),
    ('oil-extraction', 'well-pump', 'every later 50-tick cycle pumps the deposit: crude oil exactly +500 mB, natural gas +100..500 mB (random) per cycle; '
                                    'with nothing connected to take them yet, both stay in the well', 'well'),
    ('oil-extraction', 'well-power', 'one wood burner (100 HE a tick) on red cable is the well\'s whole supply and its need: the energy the burner '
                                     'made (100 HE per burnt tick) less what burner and well still hold is 100 HE for each tick the well ran, and it '
                                     'ran every tick of the windows but the burner\'s start-up (N-4..N-1 of N)', 'well'),
    ('oil-extraction', 'well-drain', 'each pump empties the pumped deposit block with chance 5 %: the emptied blocks of the 27-block deposit lie in the '
                                     '99.9 % binomial range of the pumps run', 'well'),
    ('oil-extraction', 'reload', 'after leaving and reopening the world the well and its burner have the same tanks, power, burn time and logs', 'well'),
    ('oil-refining', 'heater-type', 'a right-click with a fluid identifier set to crude oil switches the heat boiler from water to crude oil in and '
                                    'hot oil out', 'boiler'),
    ('oil-refining', 'oil-balance', 'all crude oil the well pumped (500 mB x pumps, counted by the gas increments) is in the well, the boiler (as oil or '
                                    'hot oil, 1 mB hot oil per mB oil) or the refinery input, or refined at 100 mB per run, the runs counted by the '
                                    'energy the refinery and its wood burner (switched off after charging the refinery\'s 1,000 HE) gave up, 5 HE a run', 'boiler'),
    ('oil-refining', 'fractions', 'per refinery run: heavy oil 50, naphtha 25, light oil 15, petroleum gas 10 mB (heavy oil counted with what the tower '
                                  'took, light oil with the filled universal tanks)', 'refinery'),
    ('oil-refining', 'sulfur', 'one sulfur in the byproduct slot per 10 refinery runs', 'refinery'),
    ('oil-refining', 'reload', 'after reopening the boiler keeps crude oil as input type and the refinery and its burner their tanks, power and sulfur',
     'refinery'),
    ('fractionation', 'heavy-oil', 'the tower takes the refinery\'s heavy oil through a heavy-oil duct; each run 100 mB heavy oil -> 30 bitumen + 70 '
                                   'smear, at most one run every 10 ticks', 'tower'),
    ('fractionation', 'reload', 'after reopening the tower has the same three tanks', 'tower'),
    ('catalytic-cracking', 'bitumen', 'the cracker takes the tower\'s bitumen through a bitumen duct; each run 100 mB bitumen + 200 mB steam (8,000 mB '
                                      '预写) -> 80 crude oil + 20 aromatics + 2 spent steam', 'cracker'),
    ('catalytic-cracking', 'reload', 'after reopening the cracker has the same five tanks', 'cracker'),
    ('oil-coking', 'one-batch', 'the coker on a coal firebox turns 11,000 mB heavy oil (预写, one batch) into 1 petroleum coke and 1,100 mB '
                                'coker oil after 20,000 heat units of progress', 'coker'),
    ('oil-coking', 'reload', 'after reopening the coker has the same tanks, progress and coke', 'coker'),
    ('vacuum-refinery', 'ten-runs', '预写 1,000 mB crude oil at pressure 2, power from a wood burner on red cable: 10 runs of 100 mB and '
                                    '10,000 HE -> vacuum heavy oil 400, reformate 250, vacuum light oil 200, sour gas 150 mB; the energy the burner '
                                    'made less what burner and refinery still hold is 100,000 HE', 'vacuum'),
    ('vacuum-refinery', 'reload', 'after reopening the vacuum refinery and its burner have the same tanks and power', 'vacuum'),
    ('fluid-container-transfer', 'light-oil-tank', 'two empty universal tanks clicked into the refinery\'s light-oil slot come out full: 2,000 mB light '
                                                   'oil moved from the tank', 'containers'),
    ('fluid-container-transfer', 'mercury-tank', '20 cinnabar clicked into the combination oven on a coal firebox give 20 sulfur and 2,000 mB mercury, '
                                                 'which two empty universal tanks in its fluid slot take whole', 'containers'),
    ('fluid-container-transfer', 'desh-chain', 'chem.desh chosen in the chemical plant\'s recipe selector; the plant on a wood burner (100 HE a tick, '
                                               'its need) empties the two light-oil and two mercury tanks clicked in and makes 10 desh ingots from 10 '
                                               'desh mix, 2,000 mB light oil and 2,000 mB mercury (200 + 200 mB each), 100 ticks and 100 HE a tick each: '
                                               'the energy the burner made less what burner and plant still hold is 100,000 HE', 'desh'),
    ('fluid-container-transfer', 'reload', 'after reopening the oven, the chemical plant and its burner have the same tanks, slots and recipe', 'containers'),
    ('diesel-power', 'burn', 'the diesel generator (8,000 mB diesel 预写), switched on with its screen button, makes 1,027 HE from '
                              '1 mB diesel every tick', 'diesel'),
    ('diesel-power', 'reload', 'after reopening the generator (stopped by a redstone block placed beside it) is still switched on with the '
                               'same fuel', 'diesel'),
    ('combustion-power', 'burn', 'the combustion engine with a steel piston set clicked in, switched on and set to throttle 30 in its screen '
                                 '(300 mB diesel 预写) makes 2,055 HE from 6 mB diesel every tick', 'combustion'),
    ('combustion-power', 'reload', 'after reopening the engine has the same throttle, on state, fuel and power', 'combustion'),
    ('turbofan-power', 'burn', 'the turbofan (100 mB kerosene 预写) makes 3,850 HE from 1 mB kerosene every tick; burnt out it '
                                 'holds 385,000 HE', 'turbofan'),
    ('turbofan-power', 'reload', 'after reopening the burnt-out turbofan has the same power and fuel type', 'turbofan'),
    ('industrial-steam', 'desh-anvil', 'in the iron anvil an iron anvil and the 10 desh ingots of the chemical plant make the desh anvil (tier 3, the '
                                       'tier the industrial boiler and electric pump need)', 'anvil'),
    ('industrial-steam', 'anvil-build', 'on the desh anvil, found by paging its list (right arrow) and checked by its tooltip, 8 steel cast plates, '
                                        '8 copper ingots and 4 polymer ingots make the industrial boiler; 8 stone bricks, 16 steel plates, 4 lead '
                                        'pipes, 2 motors and 4 vacuum tubes make the electric pump', 'build'),
    ('industrial-steam', 'pump-water', 'the electric pump on dirt ground, powered from the diesel generator through red cable, is the only water source of '
                                       'the industrial boiler: water reaches the boiler through a water duct', 'pump'),
    ('industrial-steam', 'boiler-steam', 'the industrial boiler on a coal firebox turns 1 mB water into 100 mB steam: all steam made (boiler, turbine '
                                         'input, 100 x turbine spent steam) is a positive multiple of 100', 'iboiler'),
    ('industrial-steam', 'reload', 'after the line is stopped (coal taken out of the firebox) and the world reopened the industrial boiler has '
                                   'the same tanks and heat', 'iboiler'),
    ('industrial-turbine', 'steam', 'the industrial turbine takes the boiler\'s steam through a steam duct and leaves 1 mB spent steam per 100 mB; its '
                                    'power target is set for 1,500 runs of 200 TU (300,000); spun up below 5 % it hands its whole flywheel '
                                    '(200 TU a run) out as power each tick, so the flywheel is empty and the power a multiple of 200', 'turbine'),
    ('industrial-turbine', 'reload', 'after the line is stopped and the world reopened the turbine has the same tanks, flywheel, power and '
                                     'power target', 'turbine'),
    ('heaters', 'electric-build', 'on the desh anvil, found by paging its list and checked by its tooltip, 4 polymer ingots, 8 copper ingots, 8 steel '
                                  'plates, 8 tungsten coils and 1 integrated circuit board make the electric heater', 'heater_build'),
    ('heaters', 'electric-line', 'the electric heater set to 1 by one screwdriver click draws 200 HE and makes 100 TU in every tick it has the power; '
                                 'two wood burners (2 x 100 HE a tick) on red cable feed it, so it runs every tick but the start-up and the energy the '
                                 'burners made less what burners and heater still hold is 200 HE per run; the combination oven on it turns 5 cinnabar '
                                 'into 5 sulfur and 500 mB mercury', 'heater'),
    ('heaters', 'reload', 'after reopening the heater has the same setting and power and the oven on it the same mercury and sulfur', 'heater'),
]


def expectations():
    return [dict(id='%s.%s' % (f, i), text=t, source=SRC[s]) for f, i, t, s in EXPECTED]


def eid(feature, name):
    return '%s.%s' % (feature, name)


# ---------------------------------------------------------------- helpers

def cmd(ctx, command, **kw):
    return ctx.step('cmd', command=command, **kw)


def srv(ctx, command, allow_error=False):
    return ctx.server(command, allow_error=allow_error)


def data(ctx, pos):
    return _lib.block_data(ctx, pos)


def is_block(ctx, pos, block):
    r = srv(ctx, 'execute if block %d %d %d %s' % (pos[0], pos[1], pos[2], block), allow_error=True)
    return bool(r.get('result'))


def items_of(d):
    return {it.get('Slot'): it for it in d.get('Items', [])}


def slot_item(d, slot):
    it = items_of(d).get(slot)
    if not it:
        return None, 0, None
    return it.get('id'), it.get('count', 1), it.get('components', {}).get('hbmsntm:meta')


def tank(d, key):
    return dict(fill=d.get(key, 0), type=d.get(key + '_type'), p=d.get(key + '_p', 0))


def hold(ctx, item):
    cmd(ctx, 'item replace entity @s weapon.mainhand with %s' % item)


def park(ctx):
    ctx.step('view', pos=PARK, pitch=60.0, yaw=0.0, fly=True, hide_gui=True)


def inventory(ctx):
    """The player's inventory as the client has it: {inventory index (0-8 hotbar, 9-35 main): (item, count)}."""
    inv = ctx.step('inv')
    return {s['slot']: (s.get('item'), s.get('count', 0)) for s in inv['slots']
            if s.get('item') and s.get('item') != 'minecraft:air' and s['slot'] < 36}


def count(ctx, item):
    return sum(n for i, n in inventory(ctx).values() if i == item)


def to_hand(ctx, item):
    """Selects the hotbar slot that holds the player's own `item` (a product of this line, which lands in the first empty
    hotbar slot: the inputs and other items are kept in the main inventory) with its number key."""
    src = next((s for s, (i, n) in sorted(inventory(ctx).items()) if i == item), None)
    if src is None or src >= 9:
        raise RuntimeError('%s is not in the hotbar (inventory slot %s)' % (item, src))
    ctx.step('key', key='key.keyboard.%d' % (src + 1), action='tap', after=2)


def empty_hand(ctx):
    """Selects an empty hotbar slot with its number key (a player's products stay where they are)."""
    free = next((s for s in range(9) if s not in inventory(ctx)), None)
    if free is None:
        raise RuntimeError('no empty hotbar slot')
    ctx.step('key', key='key.keyboard.%d' % (free + 1), action='tap', after=2)


def place_machine(ctx, block, core, offset, sneak=False, item=None, dist=3.5, held=False):
    """Places a machine by hand, the player south of it looking north (the machine faces south): the item is used on the top
    face of the block under P = core + offset south (DummyableBlock puts the core `offset` blocks behind the clicked
    position). On a firebox or heater the player sneaks so the use places instead of opening it. held=True: the item is
    already in the main hand (a product of this line, to_hand)."""
    px, py, pz = core[0], core[1], core[2] + offset
    if not held:
        hold(ctx, item or 'hbmsntm:' + block)
    ctx.step('view', pos=[px + 0.5, py, pz + 0.5 + dist], look_at=[px + 0.5, py, pz + 0.5], fly=True, hide_gui=True)
    if sneak:
        ctx.step('key', key='key.keyboard.left.shift', action='press')
        ctx.step('wait', ticks=3)
    try:
        ctx.step('use', target=dict(pos=[px, py - 1, pz], face='up'), after=8)
    finally:
        if sneak:
            ctx.step('key', key='key.keyboard.left.shift', action='release')
    hold(ctx, 'minecraft:air')
    if not is_block(ctx, core, 'hbmsntm:' + block):
        raise RuntimeError('%s: no %s at the expected core %s after placing by hand' % (block, block, core))


def open_and_load(ctx, target, face, n_slots, loads, eye, then=None):
    """Right-clicks a machine open with an empty hand and moves each (machine slot, item, count) from the player's inventory
    into the machine with two slot clicks; returns the click results. Inventory slot k is menu slot n_slots + k. `then`
    (ctx, hud) runs before the screen closes, with a HUD read that holds the screen's GUI origin (gui_left, gui_top)."""
    for k, (slot, item, n) in enumerate(loads):
        cmd(ctx, 'item replace entity @s inventory.%d with %s %d' % (k, item, n))
    hold(ctx, 'minecraft:air')
    ctx.step('view', pos=eye, look_at=[target[0] + 0.5 + 0.5 * _lib.VEC[face][0], target[1] + 0.5, target[2] + 0.5 + 0.5 * _lib.VEC[face][2]],
             fly=True, hide_gui=False)
    ctx.step('use', target=dict(pos=list(target), face=face), after=6)
    ctx.step('screen', expect='Screen')
    out = []
    try:
        for k, (slot, item, n) in enumerate(loads):
            ctx.step('click', slot=n_slots + k)
            out.append(ctx.step('click', slot=slot))
        if then:
            then(ctx, ctx.step('hud', frames=2))
    finally:
        ctx.step('close')
    return out


def take_out(ctx, target, face, n_slots, slot, inv_k, eye):
    """Opens the machine and moves the stack of a machine slot into inventory slot inv_k with two clicks."""
    hold(ctx, 'minecraft:air')
    ctx.step('view', pos=eye, look_at=[target[0] + 0.5 + 0.5 * _lib.VEC[face][0], target[1] + 0.5, target[2] + 0.5 + 0.5 * _lib.VEC[face][2]],
             fly=True, hide_gui=False)
    ctx.step('use', target=dict(pos=list(target), face=face), after=6)
    ctx.step('screen', expect='Screen')
    try:
        a = ctx.step('click', slot=slot)
        b = ctx.step('click', slot=n_slots + inv_k)
    finally:
        ctx.step('close')
    return a, b


def ducts(ctx, positions, fluid):
    """Real duct blocks, each typed by a right-click with a fluid identifier set to `fluid` (FluidDuctBaseBlock.useItemOn)."""
    for p in positions:
        srv(ctx, 'setblock %d %d %d hbmsntm:fluid_duct_neo' % tuple(p))
    _lib.placed(ctx, 4)
    hold(ctx, 'hbmsntm:fluid_identifier_multi[minecraft:custom_data={Fluid1:%d}]' % FL[fluid])
    for p in positions:
        # the duct is a thin pipe whose arms follow its neighbours: aim at its centre from steeply above and accept any
        # face of that duct (any_hit), but not another block
        ctx.step('view', pos=[p[0] + 0.5, p[1] + 1.5, p[2] + 1.8], look_at=[p[0] + 0.5, p[1] + 0.5, p[2] + 0.5], fly=True, hide_gui=True)
        r = ctx.step('use', target=dict(pos=list(p), face='up', offset=[0, -0.45, 0]), after=3, any_hit=True)
        if (r.get('hit') or {}).get('pos') != [float(c) for c in p] and (r.get('hit') or {}).get('pos') != list(p):
            hold(ctx, 'minecraft:air')
            raise RuntimeError('the identifier click on the duct at %s hit %s' % (p, r.get('hit')))
    hold(ctx, 'minecraft:air')
    bad = [p for p in positions if data(ctx, p).get('Type') != FL[fluid]]
    if bad:
        raise RuntimeError('ducts not typed %s after the identifier right-click: %s' % (fluid, bad))


def cables(ctx, positions):
    """Real red cable blocks (they connect to the power ports beside them)."""
    for p in positions:
        srv(ctx, 'setblock %d %d %d hbmsntm:red_cable' % tuple(p))


def sprint(ctx, ticks, label, until=None, poll_s=0.5, timeout_s=900):
    park(ctx)
    return ctx.sprint(ticks, until=until, label=label, poll_s=poll_s, timeout_s=timeout_s)


def game_time(ctx):
    return ctx.server()['game_time']


def server_steps(ctx, n):
    """`tick step n` in the frozen world, waiting until the server's game time moved n ticks."""
    t0 = game_time(ctx)
    ctx.server('tick step %d' % n)
    for _ in range(200):
        ctx.step('wait', ticks=2)
        if game_time(ctx) >= t0 + n:
            return
    raise RuntimeError('tick step %d did not finish' % n)


def align(ctx, mod, phase, label):
    """Runs the frozen world on to a game time equal to `phase` modulo `mod` (a sprint from the frozen world runs one tick
    more than asked; a single tick is a tick step)."""
    need = (phase - game_time(ctx)) % mod
    if need >= 2:
        sprint(ctx, need - 1, label, poll_s=0.2)
    elif need == 1:
        server_steps(ctx, 1)
    if game_time(ctx) % mod != phase:
        raise RuntimeError('%s: game time %d, wanted %d mod %d' % (label, game_time(ctx), phase, mod))


def still(ctx):
    """Freezes the world and waits 4 s of wall time: the power and fluid networks run on the server tick event, which a
    frozen server still fires (NtmEventHandler.java:69-76), and drop a provider or receiver only 3,000 ms after its block
    entity last refreshed it (PowerNetMK2.java:22,42,61; NodeNet.java:27,32). After the wait readings of several connected
    blocks taken one after another belong together."""
    ctx.server('tick freeze')
    ctx.step('wait', ticks=80)


def binomial_range(n, p, alpha=0.001):
    pmf = [comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(n + 1)]
    lo, acc = 0, 0.0
    for k in range(n + 1):
        acc += pmf[k]
        if acc > alpha / 2:
            lo = k
            break
    hi, acc = n, 0.0
    for k in range(n, -1, -1):
        acc += pmf[k]
        if acc > alpha / 2:
            hi = k
            break
    return lo, hi


# ---------------------------------------------------------------- wood burners

def build_burner(ctx, core, cable, logs):
    """A wood burner placed by hand facing south, the red cable from its port to the consumer, logs loaded by slot clicks."""
    place_machine(ctx, 'machine_wood_burner', core, 0)
    cables(ctx, cable)
    open_and_load(ctx, core, 'south', 6, [(0, 'minecraft:oak_log', logs)], [core[0] + 0.5, Y, core[2] + 2.5])
    d = data(ctx, core)
    if slot_item(d, 0)[:2] != ('minecraft:oak_log', logs):
        raise RuntimeError('wood burner at %s fuel slot after loading: %s' % (core, items_of(d)))


def burner_set(ctx, core, on):
    """Switches a wood burner with the button in its screen (GUI 53,17, 16x15; MachineWoodBurnerBlockEntity.receiveControl)."""
    if bool(data(ctx, core).get('isOn')) == on:
        return
    hold(ctx, 'minecraft:air')
    ctx.step('view', pos=[core[0] + 0.5, Y, core[2] + 2.5], look_at=[core[0] + 0.5, Y + 0.5, core[2] + 1.0], fly=True, hide_gui=False)
    ctx.step('use', target=dict(pos=list(core), face='south'), after=6)
    ctx.step('screen', expect='WoodBurner')
    try:
        hud = ctx.step('hud', frames=2)
        ctx.step('click', at=[hud['gui_left'] + 61, hud['gui_top'] + 24], button=0, after=4)
    finally:
        ctx.step('close')
    if bool(data(ctx, core).get('isOn')) != on:
        raise RuntimeError('the burner at %s did not switch %s' % (core, 'on' if on else 'off'))


def made_by(ctx, core, logs):
    """Energy a burner has made: 100 HE for each tick burnt, 1,200 per log taken from the fuel slot less the current log's rest."""
    d = data(ctx, core)
    _, left, _ = slot_item(d, 0)
    return BURNER_GEN * (LOG_TICKS * (logs - left) - d.get('burnTime', 0)), d


def stored(ctx, positions):
    return sum(data(ctx, p).get('power', 0) for p in positions)


# ---------------------------------------------------------------- recipe selector and anvil

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


def anvil_recipes(ctx, tier):
    """The construction recipes an anvil of `tier` lists, in the anvil screen's order (AnvilMenuScreen.java:45-50,
    AnvilRecipes.isTierValid)."""
    r = ctx.step('export', kind='anvil')
    path = Path(ctx.channels[ctx.default].dir) / r['file']
    rows = json.loads(path.read_text(encoding='utf-8'))['construction']
    return [x for x in rows if x['tier_lower'] <= tier and (x['tier_upper'] == -1 or x['tier_upper'] >= tier)]


def anvil_build(ctx, anvil_pos, recipes, out, need, label_key):
    """Opens the anvil by hand, pages to the recipe making `out` that takes `need` with the list's right arrow, checks the
    entry's tooltip names the output, selects it and presses construct. Returns (ok, detail)."""
    pos = next((p for p, x in enumerate(recipes) if x['outputs'][0]['id'] == out
                and any(a['id'] == need for alts in x['inputs'] for a in alts)), None)
    if pos is None:
        return False, 'no tier-%d anvil recipe for %s with %s' % (ANVIL_TIER, out, need)
    want = ctx.step('i18n', keys=[label_key])['texts'][label_key]
    before = count(ctx, out)
    empty_hand(ctx)
    x, y, z = anvil_pos
    look = [x + 0.5 + ANVIL_AIM[0], y + 0.5 + ANVIL_AIM[1], z + 0.5 + 0.499 + ANVIL_AIM[2]]
    ctx.step('view', pos=[x + 0.5, Y, z + 2.5], look_at=look, fly=True, hide_gui=False)
    ctx.step('use', target=dict(pos=list(anvil_pos), face='south', offset=list(ANVIL_AIM)), after=6)
    ctx.step('screen', expect='Anvil')
    try:
        hud = ctx.step('hud', frames=2)
        left, top = hud['gui_left'], hud['gui_top']
        size = max(0, -(-(len(recipes) - ANVIL_PAGE) // 2))
        index = min(pos // 2, size)
        # the list scrolls one column per click on its right arrow (AnvilMenuScreen.java:225-230; the original's only
        # paging besides the wheel, GUIAnvil.mouseClicked); the screen opens on the first column
        for _ in range(index):
            ctx.step('click', at=[left + 106 + 4, top + 71 + 18], after=1)
        ind = pos - index * 2
        cell = [left + 16 + 18 * (ind // 2) + 9, top + 71 + 18 * (ind % 2) + 9]
        ctx.step('hover', at=cell, frames=3)
        tip = [t['text'] for t in ctx.step('hud', frames=3).get('texts', []) if t['text'].startswith('tooltip: ')]
        if not tip or want not in tip[0]:
            return False, 'anvil list position %d (page %d, cell %d) shows %r, not %s (%r)' % (pos, index, ind, tip[:1], out, want)
        ctx.step('click', at=cell, after=3)
        ctx.step('click', at=[left + 52 + 9, top + 53 + 9], after=6)
    finally:
        ctx.step('close')
    after = count(ctx, out)
    return after == before + 1, '%s %d -> %d (anvil list position %d of %d, %d right-arrow clicks, cell %d, tooltip %r)' % (
        out.split(':')[1], before, after, pos, len(recipes), index, ind, tip[0])


def give_inputs(ctx, stacks):
    """Empties the inventory and puts the construction inputs into the main inventory (the hotbar stays free)."""
    cmd(ctx, 'clear @s', allow_error=True)
    for k, (item, n) in enumerate(stacks):
        cmd(ctx, 'item replace entity @s inventory.%d with %s %d' % (k, item, n))


class Section:
    """One feature group's build and checks: an exception turns the section's undecided rows into not-run with the reason,
    the following sections still run."""

    def __init__(self, ctx, state, ids):
        self.ctx, self.state, self.ids = ctx, state, ids

    def __enter__(self):
        return self

    def __exit__(self, kind, exc, tb):
        if exc is None:
            return False
        detail = getattr(exc, 'result', None)
        if isinstance(detail, dict):
            detail = 'step %s failed: %s' % (detail.get('op'), detail.get('reason'))
        reason = '%s: %s' % (kind.__name__, str(detail or exc)[:300])
        for i in self.ids:
            if i not in self.ctx.verdicts:
                self.ctx.not_run(i, reason)
        self.state.setdefault('failed', []).append(reason)
        try:
            self.ctx.server('tick freeze')
        except Exception:
            pass
        return True


def need(state, key, what):
    if key not in state:
        raise RuntimeError('prerequisite missing: %s' % what)
    return state[key]


# ---------------------------------------------------------------- sections

def build_floor(ctx):
    _lib.setup_world(ctx)
    cmd(ctx, 'gamemode creative')
    srv(ctx, 'fill -12 %d -10 45 %d 70 minecraft:stone' % (Y - 1, Y - 1))
    srv(ctx, 'fill -12 %d -10 45 %d 70 minecraft:air' % (Y, Y), allow_error=True)  # fails when nothing was there to clear
    # the oil deposit: a 3x3x3 block of oil ore two blocks under the floor (world generation places ore_oil, OilBubbleFeature)
    srv(ctx, 'setblock 0 %d 0 minecraft:stone' % (Y - 2))
    srv(ctx, 'fill -1 %d -1 1 %d 1 hbmsntm:ore_oil' % (Y - 5, Y - 3))
    # dirt ground under the electric pump: 3x3 columns 4 deep (MachinePumpElectricBlockEntity.checkGround)
    srv(ctx, 'fill %d %d %d %d %d %d minecraft:dirt' % (PUMP[0] - 1, Y - 4, PUMP[2] - 1, PUMP[0] + 1, Y - 1, PUMP[2] + 1))
    _lib.go_near(ctx, 15, Y, 20)


WELL_LOGS = 4


def section_well(ctx, st):
    ids = [eid('oil-extraction', i) for i in ('well-drill', 'well-pump', 'well-power', 'well-drain')]
    with Section(ctx, st, ids):
        # the duct east of the well core and the cable west of it lie under the well's body between two legs, out of reach
        # once the well stands: they are laid (the duct typed for crude oil) first; the duct leads nowhere until the line is built
        ducts(ctx, [(1, Y, 0)], 'OIL')
        cables(ctx, CABLE_WELL[-1:])
        place_machine(ctx, 'machine_well', WELL, 0)
        build_burner(ctx, BURN_WELL, CABLE_WELL[:-1], WELL_LOGS)
        # unpowered, the well does nothing while the world is brought to the phase at which each later 50-tick window holds
        # one cycle at its 10th tick (OilDrillBaseBlockEntity.java:133-136); the burner takes its first log meanwhile
        align(ctx, WELL_DELAY, WELL_PHASE, 'well-align')
        still(ctx)
        e0 = stored(ctx, [BURN_WELL, WELL])
        m0, _ = made_by(ctx, BURN_WELL, WELL_LOGS)
        burner_set(ctx, BURN_WELL, True)
        d0 = data(ctx, WELL)
        t_start = game_time(ctx)
        windows = []
        prev = d0
        for w in range(10):
            sprint(ctx, WELL_DELAY - 1, 'well-cycle-%d' % w, poll_s=0.2)
            d = data(ctx, WELL)
            windows.append(dict(oil=d.get('t0', 0) - prev.get('t0', 0), gas=d.get('t1', 0) - prev.get('t1', 0),
                                pipes=[is_block(ctx, (0, Y - k, 0), 'hbmsntm:oil_pipe') for k in (1, 2)]))
            prev = d
        ticks = game_time(ctx) - t_start
        still(ctx)
        m1, bd = made_by(ctx, BURN_WELL, WELL_LOGS)
        e1 = stored(ctx, [BURN_WELL, WELL])
        drill_ok = all(w['oil'] == 0 and w['gas'] == 0 for w in windows[:2]) and windows[0]['pipes'] == [True, False] \
            and windows[1]['pipes'] == [True, True]
        ctx.check(eid('oil-extraction', 'well-drill'), drill_ok,
                  'first two windows: %s' % windows[:2], [SRC['well']])
        pumps = windows[2:]
        pump_ok = all(w['oil'] == OIL_PER_PUMP and GAS_MIN <= w['gas'] <= GAS_MAX for w in pumps)
        ctx.check(eid('oil-extraction', 'well-pump'), pump_ok and len(pumps) == 8,
                  'per-cycle increments oil/gas: %s' % [(w['oil'], w['gas']) for w in pumps])
        made = m1 - m0
        used = made - (e1 - e0)
        runs = used // WELL_USE
        ctx.check(eid('oil-extraction', 'well-power'), used % WELL_USE == 0 and ticks - 4 <= runs <= ticks - 1 and bd.get('isOn') == 1,
                  '%d ticks (game time %d mod 50 at the start): burner made %d HE (burnTime %s, logs left %s of %d); stored burner + well %d -> %d; '
                  'used %d = %d well ticks x 100 (expected %d..%d ticks)'
                  % (ticks, t_start % WELL_DELAY, made, bd.get('burnTime'), slot_item(bd, 0)[1], WELL_LOGS, e0, e1, used, runs, ticks - 4, ticks - 1))
        # the well stops while the line is built: its burner is switched off; what burner and well still hold lasts the well a
        # tick or two, far from its next cycle tick (the windows end at game time 40 mod 50, the cycle is at 0 mod 50)
        burner_set(ctx, BURN_WELL, False)
        st['well_pumps_a'] = len([w for w in pumps if w['oil'] == OIL_PER_PUMP])
        st['well_a'] = prev
        st['well'] = True


REFI_LOGS = 2


def section_line(ctx, st):
    """Heater, refinery, tower and cracker: built and connected, then the well pumps on into the line."""
    ids = [eid('oil-refining', i) for i in ('heater-type', 'oil-balance', 'fractions', 'sulfur')] + \
          [eid('fractionation', 'heavy-oil'), eid('catalytic-cracking', 'bitumen'), eid('fluid-container-transfer', 'light-oil-tank'),
           eid('oil-extraction', 'well-drain')]
    with Section(ctx, st, ids):
        need(st, 'well_a', 'the oil well section')
        place_machine(ctx, 'heater_firebox', FIRE1, 1)
        place_machine(ctx, 'heat_boiler', BOIL, 1, sneak=True)
        place_machine(ctx, 'machine_refinery', REFI, 1)
        place_machine(ctx, 'machine_fraction_tower', TOWER, 1)
        place_machine(ctx, 'machine_catalytic_cracker', CRACK, 3)
        # boiler input type: a right-click with an identifier set to crude oil (MachineHeatBoiler.useItemOn)
        b0 = data(ctx, BOIL)
        hold(ctx, 'hbmsntm:fluid_identifier_multi[minecraft:custom_data={Fluid1:%d}]' % FL['OIL'])
        ctx.step('view', pos=[BOIL[0] + 0.5, BOIL[1] + 1, BOIL[2] + 4.5], look_at=[BOIL[0] + 0.5, BOIL[1] + 1.5, BOIL[2] + 2.0], fly=True, hide_gui=True)
        ctx.step('use', target=dict(pos=[BOIL[0], BOIL[1] + 1, BOIL[2] + 1], face='south'), after=6)
        hold(ctx, 'minecraft:air')
        b1 = data(ctx, BOIL)
        # pipes: well -> boiler (oil), boiler -> refinery (hot oil), refinery -> tower (heavy oil, one shared port), tower -> cracker (bitumen)
        ducts(ctx, [(2, Y, 0), (3, Y, 0), (4, Y, 0), (4, Y + 1, 0)], 'OIL')
        ducts(ctx, [(8, Y + 1, 0), (8, Y, 0), (9, Y, 0), (9, Y, 1), (10, Y, 1)], 'HOTOIL')
        ducts(ctx, [(14, Y, 1)], 'HEAVYOIL')
        ducts(ctx, [(18, Y, 1), (19, Y, 1), (20, Y, 1)], 'BITUMEN')
        srv(ctx, 'data merge block %d %d %d {tank1:%d,tank1_type:%d}' % (CRACK + (CRACK_STEAM0, FL['STEAM'])))  # 预写
        # the refinery's power: a wood burner on red cable charges its 1,000 HE and is switched off again; the runs below are
        # counted by the energy refinery and burner give up (the refinery takes 5 HE a run, far below the burner's 100 a tick,
        # so a burner left on would fill to its cap and lose what it burns)
        build_burner(ctx, BURN_REFI, CABLE_REFI, REFI_LOGS)
        burner_set(ctx, BURN_REFI, True)
        sprint(ctx, 400, 'refinery-charge', until=lambda c: data(c, REFI).get('power', 0) >= REF_POWER, poll_s=0.3)
        burner_set(ctx, BURN_REFI, False)
        # coal into the firebox, two empty universal tanks into the refinery's light-oil slot (7), by slot clicks
        open_and_load(ctx, (FIRE1[0], FIRE1[1], FIRE1[2] + 1), 'south', 2, [(0, 'minecraft:coal', 10)],
                      [FIRE1[0] + 0.5, Y, FIRE1[2] + 4.5])
        open_and_load(ctx, (REFI[0], REFI[1], REFI[2] + 1), 'south', 13, [(7, 'hbmsntm:fluid_tank_empty', TANKS)],
                      [REFI[0] + 0.5, Y, REFI[2] + 4.5])
        still(ctx)
        r_e0 = stored(ctx, [BURN_REFI, REFI])
        r_charged = data(ctx, REFI).get('power', 0)
        # the well pumps on into the line on its burner, switched on again at the same phase: more windows, each pump seen as
        # a gas increment (gas has no pipe)
        align(ctx, WELL_DELAY, WELL_PHASE, 'line-align')
        prev = data(ctx, WELL)
        burner_set(ctx, BURN_WELL, True)
        gas_steps = []
        for w in range(LINE_WINDOWS):
            sprint(ctx, WELL_DELAY - 1, 'well-line-%d' % w, poll_s=0.2)
            d = data(ctx, WELL)
            gas_steps.append(d.get('t1', 0) - prev.get('t1', 0))
            prev = d
        # the well stops: its burner is switched off (what the burner still holds lasts the well a tick or two, before the
        # next cycle tick at the 10th tick of the following 50)
        burner_set(ctx, BURN_WELL, False)
        pumps_b = len([g for g in gas_steps if g > 0])
        bad_steps = [g for g in gas_steps if g and not GAS_MIN <= g <= GAS_MAX]
        pumps = st['well_pumps_a'] + pumps_b

        def settled(c):
            r, b, t = data(c, REFI), data(c, BOIL), data(c, TOWER)
            k = data(c, CRACK)
            return (b.get('input', 0) == 0 and b.get('output', 0) < REF_IN and r.get('input', 0) < REF_IN
                    and t.get('tank0', 0) < FRAC_IN and (k.get('tank0', 0) < CRACK_IN or k.get('tank1', 0) < CRACK_STEAM))
        run = sprint(ctx, 6000, 'oil-line', until=settled, poll_s=1.0, timeout_s=900)
        st['line_sprint'] = run
        still(ctx)
        w, b, r, t, k = data(ctx, WELL), data(ctx, BOIL), data(ctx, REFI), data(ctx, TOWER), data(ctx, CRACK)
        r_e1 = stored(ctx, [BURN_REFI, REFI])
        ctx.check(eid('oil-refining', 'heater-type'), b0.get('input_type') == FL['WATER'] and b1.get('input_type') == FL['OIL']
                  and b.get('input_type') == FL['OIL'] and b.get('output_type') == FL['HOTOIL'],
                  'boiler input type when placed %s, after the identifier click %s; after the run input/output %s/%s '
                  '(ids WATER %d, OIL %d, HOTOIL %d)' % (b0.get('input_type'), b1.get('input_type'), b.get('input_type'), b.get('output_type'),
                                                       FL['WATER'], FL['OIL'], FL['HOTOIL']))
        ops = (r_e0 - r_e1) // REF_USE
        power_whole = (r_e0 - r_e1) % REF_USE == 0
        oil_now = w.get('t0', 0) + b.get('input', 0) + b.get('output', 0) + r.get('input', 0) + REF_IN * ops
        ctx.check(eid('oil-refining', 'oil-balance'), not bad_steps and power_whole and ops > 0 and r_charged == REF_POWER
                  and oil_now == OIL_PER_PUMP * pumps,
                  '%d pumps (8 before the pipe, %d after; gas steps %s): %d mB pumped; well %d + boiler oil %d + hot oil %d + refinery input %d '
                  '+ %d runs x 100 = %d; refinery charged by its burner to %d; stored refinery + burner %d -> %d (= 5 x %d runs)'
                  % (pumps, pumps_b, gas_steps, OIL_PER_PUMP * pumps, w.get('t0', 0), b.get('input', 0), b.get('output', 0), r.get('input', 0),
                     ops, oil_now, r_charged, r_e0, r_e1, ops))
        # tower runs from its smear (not piped anywhere); cracker runs from its steam
        t_ops, t_rem = divmod(t.get('tank2', 0), FRAC_SMEAR)
        c_runs, c_rem = divmod(CRACK_STEAM0 - k.get('tank1', 0), CRACK_STEAM)
        bitumen_made = t.get('tank1', 0) + k.get('tank0', 0) + CRACK_IN * c_runs
        heavy_made = r.get('heavy', 0) + t.get('tank0', 0) + FRAC_IN * t_ops
        sl_id, sl_n, sl_meta = slot_item(r, 8)
        light_tanks = sl_n if (sl_id == 'hbmsntm:fluid_tank_full' and sl_meta == FL['LIGHTOIL']) else 0
        light_made = r.get('light', 0) + TANK_CAP * light_tanks
        got = dict(heavy=heavy_made, naphtha=r.get('naphtha', 0), light=light_made, petroleum=r.get('petroleum', 0))
        want = {key: ops * v for key, v in REF_OUT.items()}
        ctx.check(eid('oil-refining', 'fractions'), got == want and t_rem == 0 and c_rem == 0,
                  '%d runs: made %s, expected %s (heavy = refinery %d + tower input %d + %d tower runs x 100; light = refinery %d + %d full tank(s))'
                  % (ops, got, want, r.get('heavy', 0), t.get('tank0', 0), t_ops, r.get('light', 0), light_tanks))
        s_id, s_n, _ = slot_item(r, 11)
        sulfur = s_n if s_id == 'hbmsntm:sulfur' else 0
        ctx.check(eid('oil-refining', 'sulfur'), sulfur == ops // SULFUR_EVERY and r.get('sulfur') == ops % SULFUR_EVERY,
                  'slot 11 %s x%d after %d runs (expected %d), counter %s (expected %d)' % (s_id, s_n, ops, ops // SULFUR_EVERY, r.get('sulfur'), ops % SULFUR_EVERY))
        ctx.check(eid('fractionation', 'heavy-oil'), t_ops > 0 and t_rem == 0 and bitumen_made == FRAC_BIT * t_ops
                  and t.get('tank1_type') == FL['BITUMEN'] and t.get('tank2_type') == FL['SMEAR'],
                  '%d tower runs (smear %d = 70 x runs): bitumen made %d = tower %d + cracker input %d + %d cracker runs x 100 (expected %d); '
                  'tower input %d' % (t_ops, t.get('tank2', 0), bitumen_made, t.get('tank1', 0), k.get('tank0', 0), c_runs, FRAC_BIT * t_ops,
                                      t.get('tank0', 0)))
        ctx.check(eid('catalytic-cracking', 'bitumen'), c_runs > 0 and c_rem == 0 and k.get('tank2', 0) == CRACK_OIL * c_runs
                  and k.get('tank3', 0) == CRACK_AROMA * c_runs and k.get('tank4', 0) == CRACK_SPENT * c_runs
                  and k.get('tank2_type') == FL['OIL'] and k.get('tank3_type') == FL['AROMATICS'],
                  '%d runs (steam %d of %d 预写): oil %d, aromatics %d, spent steam %d (expected %d, %d, %d); bitumen left %d'
                  % (c_runs, k.get('tank1', 0), CRACK_STEAM0, k.get('tank2', 0), k.get('tank3', 0), k.get('tank4', 0), CRACK_OIL * c_runs,
                     CRACK_AROMA * c_runs, CRACK_SPENT * c_runs, k.get('tank0', 0)))
        ctx.check(eid('fluid-container-transfer', 'light-oil-tank'), light_tanks == TANKS and slot_item(r, 7)[0] is None
                  and r.get('light', 0) == REF_OUT['light'] * ops - TANKS * TANK_CAP,
                  'refinery slot 7 %s, slot 8 %s x%d meta %s; light oil left %d of %d made (expected made - 2,000)'
                  % (slot_item(r, 7)[0], sl_id, sl_n, sl_meta, r.get('light', 0), REF_OUT['light'] * ops))
        # exhausted deposit blocks
        empty = sum(1 for x in (-1, 0, 1) for yy in (Y - 5, Y - 4, Y - 3) for z in (-1, 0, 1)
                    if is_block(ctx, (x, yy, z), 'hbmsntm:ore_oil_empty'))
        lo, hi = binomial_range(pumps, DRAIN)
        ctx.check(eid('oil-extraction', 'well-drain'), lo <= empty <= hi,
                  '%d of 27 deposit blocks emptied after %d pumps; 99.9 %% range %d..%d' % (empty, pumps, lo, hi))
        st['line'] = True
        st['light_tanks'] = light_tanks


def section_coker(ctx, st):
    with Section(ctx, st, [eid('oil-coking', 'one-batch')]):
        place_machine(ctx, 'heater_firebox', FIRE2, 1)
        place_machine(ctx, 'machine_coker', COKER, 1, sneak=True)
        srv(ctx, 'data merge block %d %d %d {t0:%d,t0_type:%d}' % (COKER + (COKE_IN, FL['HEAVYOIL'])))  # 预写
        open_and_load(ctx, (FIRE2[0], FIRE2[1], FIRE2[2] + 1), 'south', 2, [(0, 'minecraft:coal', 4)], [FIRE2[0] + 0.5, Y, FIRE2[2] + 4.5])
        run = sprint(ctx, 20000, 'coker', until=lambda c: data(c, COKER).get('t0', 0) == 0, poll_s=1.0, timeout_s=600)
        d = data(ctx, COKER)
        c_id, c_n, _ = slot_item(d, 1)
        ctx.check(eid('oil-coking', 'one-batch'), d.get('t0', 0) == 0 and d.get('t1', 0) == COKE_BY and d.get('t1_type') == FL['OIL_COKER']
                  and c_id == 'hbmsntm:coke_petroleum' and c_n == 1,
                  'after %d ticks: heavy oil %d (of %d), coker oil %d (expected %d), output %s x%d, progress %s'
                  % (run['advanced'], d.get('t0', 0), COKE_IN, d.get('t1', 0), COKE_BY, c_id, c_n, d.get('prog')))
        st['coker'] = True


VAC_LOGS = 2


def section_vacuum(ctx, st):
    with Section(ctx, st, [eid('vacuum-refinery', 'ten-runs')]):
        place_machine(ctx, 'machine_vacuum_distill', VAC, 1)
        srv(ctx, 'data merge block %d %d %d {input:%d,input_type:%d,input_p:2s}' % (VAC + (VAC_IN0, FL['OIL'])))  # 预写
        build_burner(ctx, BURN_VAC, CABLE_VAC, VAC_LOGS)
        still(ctx)
        e0 = stored(ctx, [BURN_VAC, VAC])
        m0, _ = made_by(ctx, BURN_VAC, VAC_LOGS)
        burner_set(ctx, BURN_VAC, True)
        run = sprint(ctx, 3000, 'vacuum', until=lambda c: data(c, VAC).get('input', 0) == 0, poll_s=0.5, timeout_s=600)
        burner_set(ctx, BURN_VAC, False)
        still(ctx)
        d = data(ctx, VAC)
        m1, bd = made_by(ctx, BURN_VAC, VAC_LOGS)
        e1 = stored(ctx, [BURN_VAC, VAC])
        used = (m1 - m0) - (e1 - e0)
        runs = VAC_IN0 // VAC_PER
        got = dict(heavy=d.get('heavy', 0), reformate=d.get('reformate', 0), light=d.get('light', 0), gas=d.get('gas', 0))
        want = {k: v * runs for k, v in VAC_OUT.items()}
        ctx.check(eid('vacuum-refinery', 'ten-runs'), d.get('input', 0) == 0 and got == want and used == runs * VAC_USE,
                  'after %d ticks: input %d, outputs %s (expected %s); burner made %d HE (burnTime %s), stored burner + refinery %d -> %d: used %d '
                  '(expected %d)' % (run['advanced'], d.get('input', 0), got, want, m1 - m0, bd.get('burnTime'), e0, e1, used, runs * VAC_USE))
        st['vacuum'] = True


CHEM_LOGS = 2


def section_containers(ctx, st):
    ids = [eid('fluid-container-transfer', 'mercury-tank'), eid('fluid-container-transfer', 'desh-chain'), eid('industrial-steam', 'desh-anvil')]
    with Section(ctx, st, ids):
        place_machine(ctx, 'heater_firebox', FIRE3, 1)
        place_machine(ctx, 'furnace_combination', OVEN, 1, sneak=True)
        open_and_load(ctx, (FIRE3[0], FIRE3[1], FIRE3[2] + 1), 'south', 2, [(0, 'minecraft:coal', 10)], [FIRE3[0] + 0.5, Y, FIRE3[2] + 4.5])
        open_and_load(ctx, (OVEN[0], OVEN[1], OVEN[2] + 1), 'south', 4,
                      [(0, 'hbmsntm:cinnabar', CINNABAR), (2, 'hbmsntm:fluid_tank_empty', TANKS)], [OVEN[0] + 0.5, OVEN[1], OVEN[2] + 4.5])

        def oven_done(c):
            o = data(c, OVEN)
            return slot_item(o, 0)[0] is None and slot_item(o, 3)[1] == TANKS
        run = sprint(ctx, 20000, 'oven', until=oven_done, poll_s=1.0, timeout_s=600)
        o = data(ctx, OVEN)
        s_id, s_n, _ = slot_item(o, 1)
        f_id, f_n, f_meta = slot_item(o, 3)
        ctx.check(eid('fluid-container-transfer', 'mercury-tank'), s_id == 'hbmsntm:sulfur' and s_n == CINNABAR and f_id == 'hbmsntm:fluid_tank_full'
                  and f_n == TANKS and f_meta == FL['MERCURY'] and o.get('tank', 0) == CINNABAR * HG_PER - TANKS * TANK_CAP
                  and slot_item(o, 0)[0] is None and slot_item(o, 2)[0] is None,
                  'after %d ticks: output %s x%d, fluid slot out %s x%d meta %s (mercury id %d), tank %d mB left'
                  % (run['advanced'], s_id, s_n, f_id, f_n, f_meta, FL['MERCURY'], o.get('tank', 0)))
        if not st.get('line'):
            raise RuntimeError('prerequisite missing: the light-oil tanks of the refinery section')
        # tanks to the player: refinery slot 8 -> inventory 5, oven slot 3 -> inventory 6
        take_out(ctx, (REFI[0], REFI[1], REFI[2] + 1), 'south', 13, 8, 5, [REFI[0] + 0.5, Y, REFI[2] + 4.5])
        take_out(ctx, (OVEN[0], OVEN[1], OVEN[2] + 1), 'south', 4, 3, 6, [OVEN[0] + 0.5, OVEN[1], OVEN[2] + 4.5])
        place_machine(ctx, 'machine_chemical_plant', CHEM, 1)
        build_burner(ctx, BURN_CHEM, CABLE_CHEM, CHEM_LOGS)
        eye = [CHEM[0] + 0.5, Y, CHEM[2] + 4.5]

        def open_chem():
            hold(ctx, 'minecraft:air')
            ctx.step('view', pos=eye, look_at=[CHEM[0] + 0.5, Y + 0.5, CHEM[2] + 2.0], fly=True, hide_gui=False)
            ctx.step('use', target=dict(pos=[CHEM[0], Y, CHEM[2] + 1], face='south'), after=6)
            ctx.step('screen', expect='ChemicalPlant')
        open_chem()
        try:
            recipe = pick_recipe(ctx, CHEM, 'hbmChemicalPlant.json', 'chem.desh', 'chem.desh')
        finally:
            ctx.step('close')
        if recipe != 'chem.desh':
            raise RuntimeError('server recipe after the selector: %r' % recipe)
        cmd(ctx, 'item replace entity @s inventory.4 with hbmsntm:powder_desh_mix %d' % DESH_N)
        open_chem()
        try:
            for inv_k, slot in ((4, 4), (5, 10), (6, 11)):
                ctx.step('click', slot=22 + inv_k)
                ctx.step('click', slot=slot)
        finally:
            ctx.step('close')
        still(ctx)
        e0 = stored(ctx, [BURN_CHEM, CHEM])
        m0, _ = made_by(ctx, BURN_CHEM, CHEM_LOGS)
        burner_set(ctx, BURN_CHEM, True)
        run = sprint(ctx, 3000, 'desh', until=lambda c: slot_item(data(c, CHEM), 7)[1] == DESH_N, poll_s=0.5, timeout_s=600)
        burner_set(ctx, BURN_CHEM, False)
        still(ctx)
        c1 = data(ctx, CHEM)
        m1, bd = made_by(ctx, BURN_CHEM, CHEM_LOGS)
        e1 = stored(ctx, [BURN_CHEM, CHEM])
        used = (m1 - m0) - (e1 - e0)
        o_id, o_n, _ = slot_item(c1, 7)
        e13, e14 = slot_item(c1, 13), slot_item(c1, 14)
        light_in, hg_in = TANKS * TANK_CAP, TANKS * TANK_CAP
        ctx.check(eid('fluid-container-transfer', 'desh-chain'), recipe == 'chem.desh' and o_id == 'hbmsntm:ingot_desh' and o_n == DESH_N
                  and c1.get('i0', 0) == light_in - DESH_N * DESH_LIGHT and c1.get('i1', 0) == hg_in - DESH_N * DESH_HG
                  and e13[:2] == ('hbmsntm:fluid_tank_empty', TANKS) and e14[:2] == ('hbmsntm:fluid_tank_empty', TANKS)
                  and used == DESH_N * CHEM_TICKS * CHEM_USE,
                  'recipe from the selector %s; after %d ticks output %s x%d; light oil %s/%s, mercury %s/%s left (types %s/%s); empty tanks back '
                  '%s/%s; burner made %d HE (burnTime %s), stored burner + plant %d -> %d: used %d (expected 10 runs x 100 ticks x 100 HE = 100,000)'
                  % (recipe, run['advanced'], o_id, o_n, c1.get('i0'), light_in - DESH_N * DESH_LIGHT, c1.get('i1'), hg_in - DESH_N * DESH_HG,
                     c1.get('i0_type'), c1.get('i1_type'), e13[:2], e14[:2], m1 - m0, bd.get('burnTime'), e0, e1, used))
        # the desh anvil: an iron anvil placed by hand, smithing in its screen with the ten desh ingots of the plant
        take_out(ctx, (CHEM[0], CHEM[1], CHEM[2] + 1), 'south', 22, 7, 7, eye)
        hold(ctx, 'hbmsntm:anvil[hbmsntm:meta=0]')
        ctx.step('view', pos=[ANVIL[0] + 0.5, Y, ANVIL[2] + 3.5], look_at=[ANVIL[0] + 0.5, Y, ANVIL[2] + 0.5], fly=True, hide_gui=True)
        ctx.step('use', target=dict(pos=[ANVIL[0], Y - 1, ANVIL[2]], face='up'), after=8)
        hold(ctx, 'minecraft:air')
        cmd(ctx, 'item replace entity @s inventory.0 with hbmsntm:anvil[hbmsntm:meta=0] 1')
        ctx.step('view', pos=[ANVIL[0] + 0.5, Y, ANVIL[2] + 3.5], look_at=[ANVIL[0] + 0.5, Y + 0.5, ANVIL[2] + 1.0], fly=True, hide_gui=False)
        ctx.step('use', target=dict(pos=list(ANVIL), face='south'), after=6)
        ctx.step('screen', expect='Screen')
        try:
            ctx.step('click', slot=3 + 0)
            ctx.step('click', slot=0)
            ctx.step('click', slot=3 + 7)
            ctx.step('click', slot=1)
            ctx.step('wait', ticks=3)
            take = ctx.step('click', slot=2)
            ctx.step('click', slot=3 + 27 + 0)          # hotbar slot 1 (menu: 3 anvil slots, 27 main, then the hotbar)
        finally:
            ctx.step('close')
        inv = _lib.data_value(ctx.server('data get entity @p Inventory')['messages'][-1])
        got = [(it.get('id'), it.get('count'), it.get('components', {}).get('hbmsntm:meta')) for it in inv if it.get('Slot') == 0]
        ctx.check(eid('industrial-steam', 'desh-anvil'), got == [('hbmsntm:anvil', 1, 3)],
                  'hotbar slot 1 after taking the smithing output: %s (anvil DESH is meta 3, tier 3); output click %s'
                  % (got, take.get('before')))
        st['containers'] = True
        # the desh anvil placed by hand for the tier-3 constructions of the later sections
        to_hand(ctx, 'hbmsntm:anvil')
        ctx.step('view', pos=[ANVIL3[0] + 0.5, Y, ANVIL3[2] + 3.5], look_at=[ANVIL3[0] + 0.5, Y, ANVIL3[2] + 0.5], fly=True, hide_gui=True)
        ctx.step('use', target=dict(pos=[ANVIL3[0], Y - 1, ANVIL3[2]], face='up'), after=8)
        hold(ctx, 'minecraft:air')
        if not is_block(ctx, ANVIL3, 'hbmsntm:anvil'):
            raise RuntimeError('no desh anvil at %s after placing it by hand' % (ANVIL3,))
        st['anvil3'] = ANVIL3
        st['anvil_recipes'] = anvil_recipes(ctx, ANVIL_TIER)


def stop_diesel(ctx, st):
    """A redstone block placed by hand west of the generator stops it (MachineDieselBlockEntity.java:135-138: generate returns
    while the block has a neighbour signal), so that its fuel stays put; the generator burns 1 mB a tick while it is on, even
    with a full buffer (MachineDieselBlockEntity.java:139-144; original TileEntityMachineDiesel.java:258-266), so it is stopped while
    diesel is left for the reload comparison."""
    hold(ctx, 'minecraft:redstone_block')
    ctx.step('view', pos=[DIESEL[0] - 0.5, Y, DIESEL[2] + 3.5], look_at=[DIESEL[0] - 0.5, Y - 0.5, DIESEL[2] + 0.5], fly=True, hide_gui=True)
    ctx.step('use', target=dict(pos=[DIESEL[0] - 1, Y - 1, DIESEL[2]], face='up'), after=6)
    hold(ctx, 'minecraft:air')
    if not is_block(ctx, (DIESEL[0] - 1, Y, DIESEL[2]), 'minecraft:redstone_block'):
        raise RuntimeError('no redstone block beside the diesel generator after placing it by hand')
    st['diesel_stopped'] = True


def section_diesel(ctx, st):
    with Section(ctx, st, [eid('diesel-power', 'burn')]):
        place_machine(ctx, 'machine_diesel', DIESEL, 0)
        srv(ctx, 'data merge block %d %d %d {fuel:%d,fuel_type:%d}' % (DIESEL + (DIESEL_FUEL, FL['DIESEL'])))  # 预写
        # the on switch of the generator's screen (MachineDieselScreen.mouseClicked: 16x14 at 89,61)
        open_and_load(ctx, DIESEL, 'south', 4, [], [DIESEL[0] + 0.5, Y, DIESEL[2] + 3.5],
                      then=lambda c, h: c.step('click', at=[h['gui_left'] + 97, h['gui_top'] + 68], after=4))
        d0 = data(ctx, DIESEL)
        sprint(ctx, DIESEL_N - 1, 'diesel', poll_s=0.3)
        d1 = data(ctx, DIESEL)
        used = d0.get('fuel', 0) - d1.get('fuel', 0)
        made = d1.get('powerTime', 0) - d0.get('powerTime', 0)
        ctx.check(eid('diesel-power', 'burn'), d0.get('isOn') == 1 and used == DIESEL_N and made == DIESEL_HE * DIESEL_N,
                  'switched on by the screen button: %s; %d ticks: %d mB used (expected %d), %d HE made (expected %d)'
                  % (d0.get('isOn'), DIESEL_N, used, DIESEL_N, made, DIESEL_HE * DIESEL_N))
        st['diesel'] = True


def section_combustion(ctx, st):
    with Section(ctx, st, [eid('combustion-power', 'burn')]):
        place_machine(ctx, 'machine_combustion_engine', COMB, 0)
        srv(ctx, 'data merge block %d %d %d {tank:%d,tank_type:%d}' % (COMB + (COMB_FUEL, FL['DIESEL'])))  # 预写

        def switches(c, h):
            # MachineCombustionEngineScreen.mouseClicked: the on switch 16x14 at 89,13; the throttle bar 36x8 at 79,38, where
            # setting = (mouseX - left - 81) * 30 / 32 clamped to 0..30, so x = left + 114 gives 30
            c.step('click', at=[h['gui_left'] + 97, h['gui_top'] + 20], after=4)
            c.step('click', at=[h['gui_left'] + 114, h['gui_top'] + 42], after=4)
        open_and_load(ctx, (COMB[0], COMB[1], COMB[2]), 'south', 5, [(2, 'hbmsntm:piston_set[hbmsntm:meta=0]', 1)],
                      [COMB[0] + 0.5, Y, COMB[2] + 3.5], then=switches)
        d0 = data(ctx, COMB)
        sprint(ctx, COMB_N - 1, 'combustion', poll_s=0.3)
        d1 = data(ctx, COMB)
        used = d0.get('tank', 0) - d1.get('tank', 0)
        made = d1.get('power', 0) - d0.get('power', 0)
        p_id, _, p_meta = slot_item(d1, 2)
        ctx.check(eid('combustion-power', 'burn'), p_id == 'hbmsntm:piston_set' and p_meta in (None, 0) and d0.get('isOn') == 1
                  and d0.get('setting') == COMB_SET and used == COMB_MB * COMB_N and made == COMB_HE * COMB_N and d1.get('tenth') == 0,
                  'piston %s meta %s (none = 0, steel); on %s and throttle %s by the screen; %d ticks: %d mB used (expected %d), '
                  '%d HE made (expected %d), tenth %s' % (p_id, p_meta, d0.get('isOn'), d0.get('setting'), COMB_N, used, COMB_MB * COMB_N,
                                                          made, COMB_HE * COMB_N, d1.get('tenth')))
        st['combustion'] = True


def section_turbofan(ctx, st):
    with Section(ctx, st, [eid('turbofan-power', 'burn')]):
        place_machine(ctx, 'machine_turbofan', FAN, 1)
        park(ctx)
        srv(ctx, 'data merge block %d %d %d {fuel:%d,fuel_type:%d}' % (FAN + (FAN_FUEL, FL['KEROSENE'])))  # 预写
        d0 = data(ctx, FAN)
        sprint(ctx, FAN_N - 1, 'turbofan', poll_s=0.3)
        d1 = data(ctx, FAN)
        used = d0.get('fuel', 0) - d1.get('fuel', 0)
        made = d1.get('powerTime', 0) - d0.get('powerTime', 0)
        # the rest of the fuel burns out, so that the stored power stays put for the reload comparison (nothing takes it)
        sprint(ctx, FAN_FUEL, 'turbofan-out', until=lambda c: data(c, FAN).get('fuel', 0) == 0, poll_s=0.3)
        d2 = data(ctx, FAN)
        ctx.check(eid('turbofan-power', 'burn'), used == FAN_N and made == FAN_HE * FAN_N and d2.get('fuel', 0) == 0
                  and d2.get('powerTime', 0) - d0.get('powerTime', 0) == FAN_HE * FAN_FUEL,
                  '%d ticks: %d mB kerosene used (expected %d), %d HE made (expected %d); burnt out: fuel %s, %s HE made in all (expected %d)'
                  % (FAN_N, used, FAN_N, made, FAN_HE * FAN_N, d2.get('fuel'), d2.get('powerTime', 0) - d0.get('powerTime', 0), FAN_HE * FAN_FUEL))
        st['turbofan'] = True


def section_steam(ctx, st):
    ids = [eid('industrial-steam', 'anvil-build'), eid('industrial-steam', 'pump-water'), eid('industrial-steam', 'boiler-steam'),
           eid('industrial-turbine', 'steam')]
    with Section(ctx, st, ids):
        anvil = need(st, 'anvil3', 'the desh anvil of the container section')
        recipes = st['anvil_recipes']
        give_inputs(ctx, [('hbmsntm:plate_cast[hbmsntm:meta=%d]' % STEEL_CAST, 8), ('hbmsntm:ingot_copper', 8), ('hbmsntm:ingot_polymer', 4)])
        ok_b, line_b = anvil_build(ctx, anvil, recipes, 'hbmsntm:machine_industrial_boiler', 'hbmsntm:ingot_copper',
                                   'block.hbmsntm.machine_industrial_boiler')
        left_b = {i: count(ctx, i) for i in ('hbmsntm:plate_cast', 'hbmsntm:ingot_copper', 'hbmsntm:ingot_polymer')}
        pump_in = [('minecraft:stone_bricks', 8), ('hbmsntm:plate_steel', 16), ('hbmsntm:pipe_lead', 4), ('hbmsntm:motor', 2),
                   ('hbmsntm:circuit_vacuum_tube', 4)]
        for k, (item, n) in enumerate(pump_in):
            cmd(ctx, 'item replace entity @s inventory.%d with %s %d' % (10 + k, item, n))
        ok_p, line_p = anvil_build(ctx, anvil, recipes, 'hbmsntm:pump_electric', 'minecraft:stone_bricks', 'block.hbmsntm.pump_electric')
        left_p = {i: count(ctx, i) for i, _ in pump_in}
        ctx.check(eid('industrial-steam', 'anvil-build'), ok_b and ok_p and not any(left_b.values()) and not any(left_p.values()),
                  'industrial boiler: %s, inputs left %s; electric pump: %s, inputs left %s' % (line_b, left_b, line_p, left_p))
        need(st, 'diesel', 'the diesel generator of the diesel section (it powers the pump)')
        if not (ok_b and ok_p):
            raise RuntimeError('the tier-3 anvil constructions failed: %s; %s' % (line_b, line_p))
        to_hand(ctx, 'hbmsntm:pump_electric')
        place_machine(ctx, 'pump_electric', PUMP, 1, held=True)
        place_machine(ctx, 'heater_firebox', FIRE4, 1)
        to_hand(ctx, 'hbmsntm:machine_industrial_boiler')
        place_machine(ctx, 'machine_industrial_boiler', IBOIL, 1, sneak=True, held=True)
        place_machine(ctx, 'machine_industrial_turbine', TURB, 3)
        cables(ctx, [(x, Y, PUMP[2]) for x in range(1, 5)])
        ducts(ctx, [(8, Y, 40), (9, Y, 40), (10, Y, 40), (10, Y + 1, 40)], 'WATER')
        ducts(ctx, [(14, Y + 1, 40), (15, Y + 1, 40), (16, Y + 1, 40), (17, Y + 1, 40), (17, Y, 40)], 'STEAM')
        open_and_load(ctx, (FIRE4[0], FIRE4[1], FIRE4[2] + 1), 'south', 2, [(0, 'minecraft:coal', 4)], [FIRE4[0] + 0.5, Y, FIRE4[2] + 4.5])
        i0 = data(ctx, IBOIL)
        run = sprint(ctx, 1500, 'industrial-steam', poll_s=1.0)
        still(ctx)
        i1, t1 = data(ctx, IBOIL), data(ctx, TURB)
        water_seen = i1.get('input', 0) + i1.get('output', 0) + t1.get('water', 0) + t1.get('steam', 0) > 0
        ctx.check(eid('industrial-steam', 'pump-water'), i0.get('input', 0) == 0 and i1.get('input_type') == FL['WATER'] and water_seen,
                  'boiler water before %d, after %d (type %s); steam in boiler %d, turbine %d, spent %d after %d ticks'
                  % (i0.get('input', 0), i1.get('input', 0), i1.get('input_type'), i1.get('output', 0), t1.get('water', 0), t1.get('steam', 0),
                     run['advanced']))
        steam_total = i1.get('output', 0) + t1.get('water', 0) + TURB_SPENT_PER * t1.get('steam', 0)
        ctx.check(eid('industrial-steam', 'boiler-steam'), steam_total > 0 and steam_total % STEAM_PER_WATER == 0 and i1.get('output_type') == FL['STEAM'],
                  'steam made %d = boiler %d + turbine input %d + 100 x spent %d (water turned to steam %s; read 4 s after freezing)'
                  % (steam_total, i1.get('output', 0), t1.get('water', 0), t1.get('steam', 0), steam_total / STEAM_PER_WATER))
        ctx.check(eid('industrial-turbine', 'steam'), t1.get('steam', 0) > 0 and t1.get('steam_type') == FL['SPENTSTEAM']
                  and t1.get('maxPower') == TURB_MAXPOWER and t1.get('flywheel_energy') == 0
                  and t1.get('power', 0) > 0 and t1.get('power', 0) % TURB_TU_PER_OP == 0,
                  'turbine: input %d steam, spent %d, maxPower %s (expected %d), flywheel %s (expected 0), power out %s (expected a positive '
                  'multiple of 200), spin %s' % (t1.get('water', 0), t1.get('steam', 0), t1.get('maxPower'), TURB_MAXPOWER,
                                                 t1.get('flywheel_energy'), t1.get('power'), t1.get('spin')))
        # stop the line for the reload comparison: the rest of the coal is taken out of the firebox by slot clicks; the
        # firebox burns out its current coal, the boiler stops when its heat is below one operation (200 TU) and the turbine
        # when less than 500 mB steam is left (ceil(fill * 0.2) / 100 = 0 operations, TurbineBaseBlockEntity.java:66)
        # the diesel generator, the pump's only supply, is stopped first: it burns its last 预写 diesel otherwise (1 mB a tick while on,
        # MachineDieselBlockEntity.java:139-144) and has none left to compare after the reload
        stop_diesel(ctx, st)
        take_out(ctx, (FIRE4[0], FIRE4[1], FIRE4[2] + 1), 'south', 2, 0, 20, [FIRE4[0] + 0.5, Y, FIRE4[2] + 4.5])

        def stopped(c):
            f, i, t = data(c, FIRE4), data(c, IBOIL), data(c, TURB)
            return (f.get('burnTime', 0) == 0 and f.get('heatEnergy', 0) == 0 and i.get('heat', 0) < HEAT_PER_WATER and i.get('output', 0) == 0
                    and t.get('water', 0) < 500)
        stop = sprint(ctx, 12000, 'industrial-steam-stop', until=stopped, poll_s=1.0, timeout_s=300)
        st['steam_stop'] = stop['advanced']
        st['steam'] = True


HEAT_LOGS = 8


def section_heaters(ctx, st):
    ids = [eid('heaters', 'electric-build'), eid('heaters', 'electric-line')]
    with Section(ctx, st, ids):
        anvil = need(st, 'anvil3', 'the desh anvil of the container section')
        stacks = [('hbmsntm:ingot_polymer', 4), ('hbmsntm:ingot_copper', 8), ('hbmsntm:plate_steel', 8), ('hbmsntm:coil_tungsten', 8),
                  ('hbmsntm:circuit_integrated_board', 1)]
        give_inputs(ctx, stacks)
        ok, line = anvil_build(ctx, anvil, st['anvil_recipes'], 'hbmsntm:heater_electric', 'hbmsntm:ingot_copper', 'block.hbmsntm.heater_electric')
        left = {i: count(ctx, i) for i, _ in stacks}
        ctx.check(eid('heaters', 'electric-build'), ok and not any(left.values()), '%s; inputs left %s' % (line, left))
        if not ok:
            raise RuntimeError('the electric heater was not built: %s' % line)
        to_hand(ctx, 'hbmsntm:heater_electric')
        place_machine(ctx, 'heater_electric', HEATER, 2, held=True)
        d = ctx.step('dump', **{'from': [HEATER[0] - 2, Y, HEATER[2] - 3], 'to': [HEATER[0] + 2, Y, HEATER[2] + 3]})
        cores = [(tuple(int(c) for c in b['pos']), b['props'].get('facing')) for b in d['blocks']
                 if b['block'] == 'hbmsntm:heater_electric' and b['props'].get('type', 'core') == 'core']
        if len(cores) != 1 or cores[0][0] != HEATER:
            raise RuntimeError('electric heater core after placing: %s (expected %s)' % (cores, HEATER))
        port = tuple(HEATER[i] + 3 * _lib.VEC[cores[0][1]][i] for i in range(3))
        if port != CABLE_HEAT[0]:
            raise RuntimeError('electric heater facing %s: power port %s, not %s' % (cores[0][1], port, CABLE_HEAT[0]))
        # one screwdriver right-click: setting 0 -> 1 (HeaterElectricBlock.onScrew -> toggleSettingUp)
        h0 = data(ctx, HEATER)
        hold(ctx, 'hbmsntm:screwdriver')
        ctx.step('view', pos=[HEATER[0] + 0.5, Y + 1.5, HEATER[2] + 3.5], look_at=[HEATER[0] + 0.5, Y + 1.0, HEATER[2] + 1.5], fly=True, hide_gui=True)
        ctx.step('use', target=dict(pos=[HEATER[0], Y, HEATER[2] + 1], face='up'), after=6)
        hold(ctx, 'minecraft:air')
        h1 = data(ctx, HEATER)
        if h1.get('setting') != HEAT_SET:
            raise RuntimeError('heater setting %s -> %s after one screwdriver click' % (h0.get('setting'), h1.get('setting')))
        place_machine(ctx, 'furnace_combination', HOVEN, 1, sneak=True)
        for b in BURN_HEAT:
            build_burner(ctx, b, [], HEAT_LOGS)
        cables(ctx, CABLE_HEAT)
        open_and_load(ctx, (HOVEN[0], HOVEN[1], HOVEN[2] + 1), 'south', 4, [(0, 'hbmsntm:cinnabar', HEAT_CINNABAR)],
                      [HOVEN[0] + 0.5, HOVEN[1], HOVEN[2] + 4.5])
        still(ctx)
        nodes = BURN_HEAT + [HEATER]
        e0 = stored(ctx, nodes)
        m0 = sum(made_by(ctx, b, HEAT_LOGS)[0] for b in BURN_HEAT)
        for b in BURN_HEAT:
            burner_set(ctx, b, True)
        g_on = game_time(ctx)
        run = sprint(ctx, 8000, 'heater-oven', until=lambda c: slot_item(data(c, HOVEN), 1)[1] == HEAT_CINNABAR, poll_s=0.5, timeout_s=600)
        for b in BURN_HEAT:
            burner_set(ctx, b, False)
        g_off = game_time(ctx)
        # the heater works off what it and the burners still hold (less than 200 HE is left for good)
        sprint(ctx, 100, 'heater-drain', poll_s=0.3)
        still(ctx)
        m1 = sum(made_by(ctx, b, HEAT_LOGS)[0] for b in BURN_HEAT)
        e1 = stored(ctx, nodes)
        h2, o = data(ctx, HEATER), data(ctx, HOVEN)
        used = (m1 - m0) - (e1 - e0)
        runs = used // HEAT_USE
        on_ticks = g_off - g_on
        s_id, s_n, _ = slot_item(o, 1)
        ctx.check(eid('heaters', 'electric-line'), h1.get('setting') == HEAT_SET and h0.get('setting') == 0 and used % HEAT_USE == 0
                  and on_ticks - 6 <= runs <= on_ticks + 100 and h2.get('power', 0) < HEAT_USE and slot_item(o, 0)[0] is None
                  and s_id == 'hbmsntm:sulfur' and s_n == HEAT_CINNABAR and o.get('tank', 0) == HEAT_CINNABAR * HG_PER
                  and o.get('tank_type') == FL['MERCURY'],
                  'setting %s -> %s by one screwdriver click; burners on for %d ticks (oven done after %d sprinted): made %d HE, stored '
                  'burners + heater %d -> %d, used %d = %d heater runs x 200 (expected %d..%d); heater power left %s; oven: input %s, %s x%d, '
                  'mercury %s mB type %s (expected 5 sulfur, 500 mB)'
                  % (h0.get('setting'), h1.get('setting'), on_ticks, run['advanced'], m1 - m0, e0, e1, used, runs, on_ticks - 6, on_ticks + 100,
                     h2.get('power'), slot_item(o, 0)[0], s_id, s_n, o.get('tank', 0), o.get('tank_type')))
        st['heaters'] = True


# ---------------------------------------------------------------- the reload comparison

BURNER_FIELDS = ('isOn', 'burnTime', 'power', 'Items')
# compared fields that are a setting, a switch or a recipe rather than a stored quantity (fluid types end in _type)
NOT_QUANTITY = ('isOn', 'setting', 'recipe0', 'maxPower', 'input_p')
RELOAD = [
    ('oil-extraction', 'well', WELL, ('t0', 't0_type', 't1', 't1_type', 'power')),
    ('oil-extraction', 'well', BURN_WELL, BURNER_FIELDS),
    ('oil-refining', 'line', BOIL, ('input_type', 'output_type')),
    ('oil-refining', 'line', REFI, ('input', 'heavy', 'naphtha', 'light', 'petroleum', 'heavy_type', 'power', 'sulfur', 'Items')),
    ('oil-refining', 'line', BURN_REFI, BURNER_FIELDS),
    ('fractionation', 'line', TOWER, ('tank0', 'tank1', 'tank2', 'tank1_type', 'tank2_type')),
    ('catalytic-cracking', 'line', CRACK, ('tank0', 'tank1', 'tank2', 'tank3', 'tank4', 'tank2_type', 'tank3_type')),
    ('oil-coking', 'coker', COKER, ('t0', 't1', 't1_type', 'prog', 'Items')),
    ('vacuum-refinery', 'vacuum', VAC, ('input', 'input_p', 'heavy', 'reformate', 'light', 'gas', 'power')),
    ('vacuum-refinery', 'vacuum', BURN_VAC, BURNER_FIELDS),
    ('fluid-container-transfer', 'containers', OVEN, ('tank', 'tank_type', 'Items')),
    ('fluid-container-transfer', 'containers', CHEM, ('recipe0', 'i0', 'i1', 'i0_type', 'i1_type', 'power', 'Items')),
    ('fluid-container-transfer', 'containers', BURN_CHEM, BURNER_FIELDS),
    ('diesel-power', 'diesel', DIESEL, ('isOn', 'fuel', 'fuel_type')),
    ('combustion-power', 'combustion', COMB, ('isOn', 'setting', 'tank', 'tenth', 'power', 'Items')),
    ('turbofan-power', 'turbofan', FAN, ('fuel', 'fuel_type', 'powerTime')),
    ('industrial-steam', 'steam', IBOIL, ('input', 'input_type', 'output', 'output_type', 'heat')),
    ('industrial-turbine', 'steam', TURB, ('water', 'steam', 'steam_type', 'flywheel_energy', 'maxPower', 'power')),
    ('heaters', 'heaters', HEATER, ('setting', 'power')),
    ('heaters', 'heaters', HOVEN, ('tank', 'tank_type', 'Items')),
    ('heaters', 'heaters', BURN_HEAT[0], BURNER_FIELDS),
    ('heaters', 'heaters', BURN_HEAT[1], BURNER_FIELDS),
]


def snapshot(ctx, st):
    out = {}
    for feature, key, pos, fields in RELOAD:
        if not st.get(key):
            continue
        d = data(ctx, pos)
        out[(feature, pos)] = {f: d.get(f) for f in fields}
    return out


def reload_compare(ctx, st):
    groups = {}
    for feature, key, pos, fields in RELOAD:
        groups.setdefault(feature, []).append(key)
    reload_ids = [eid(f, 'reload') for f in groups]
    with Section(ctx, st, reload_ids):
        for f, keys in groups.items():
            if not all(st.get(k) for k in keys):
                ctx.not_run(eid(f, 'reload'), 'the section that builds this machine did not finish')
        cmd(ctx, 'tick freeze')
        if st.get('diesel') and not st.get('diesel_stopped'):
            stop_diesel(ctx, st)
        # stable readings only: two reads 20 ticks apart, each 4 s after freezing; a reading that moved is left out and named
        still(ctx)
        a = snapshot(ctx, st)
        sprint(ctx, 19, 'reload-settle', poll_s=0.3)
        still(ctx)
        b = snapshot(ctx, st)
        before = {}
        moved = {}
        for k, fields in b.items():
            before[k] = {f: v for f, v in fields.items() if a.get(k, {}).get(f) == v}
            moved[k] = sorted(f for f, v in fields.items() if a.get(k, {}).get(f) != v)
        g0 = game_time(ctx)
        ctx.step('leave')
        ctx.step('openworld', world=ctx.run.world['name'])
        ctx.server('tick freeze')
        g1 = game_time(ctx)
        ctx.step('wait', ticks=80)
        after = snapshot(ctx, st)
        for f in groups:
            if eid(f, 'reload') in ctx.verdicts:
                continue
            rows = [(k, before[k]) for k in before if k[0] == f]
            diffs = {}
            for k, fields in rows:
                for field, v in fields.items():
                    if after.get(k, {}).get(field) != v:
                        diffs['%s %s' % (k[1], field)] = (v, after.get(k, {}).get(field))
            compared = sum(len(fields) for k, fields in rows)
            # a reload that compares only default readings proves nothing: at least one compared stored quantity of the
            # group (power, a tank fill, burn time, heat, progress, items) must be non-default
            held = ['%s %s' % (k[1], field) for k, fields in rows for field, v in fields.items() if field not in NOT_QUANTITY
                    and not field.endswith('_type') and v not in (None, 0, [], {}, '')]
            ctx.check(eid(f, 'reload'), compared > 0 and not diffs and bool(held),
                      'reopened %d ticks after leaving; %d readings compared %s; differences %s; non-default quantities compared: %s; '
                      'left out as still moving: %s'
                      % (g1 - g0, compared, {str(k[1]): fields for k, fields in rows}, diffs or 'none', held or 'none',
                         {str(k[1]): moved[k] for k in moved if k[0] == f and moved[k]} or 'none'))


def run(ctx):
    st = {}
    build_floor(ctx)
    for section in (section_well, section_line, section_coker, section_vacuum, section_containers, section_diesel, section_combustion,
                    section_turbofan, section_steam, section_heaters):
        section(ctx, st)
        # a section that stopped half-way must not leave a screen open or the sneak key down for the next one
        ctx.step('close', allow_fail=True)
        ctx.step('key', key='key.keyboard.left.shift', action='release', allow_fail=True)
    reload_compare(ctx, st)
