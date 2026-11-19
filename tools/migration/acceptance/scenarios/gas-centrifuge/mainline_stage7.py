"""Main line, stage 7 (uranium processing and enrichment), played in survival on the flat world.

The line: two uranium ores smelt in a furnace, two ingots give three uranium billets on the crafting table; a chemical plant
on a wood-burner cable bus makes hydrogen peroxide from a water bucket (unloaded into a universal fluid tank and loaded back
for the next recipe), yellowcake from two billets, two sulfur and 500 mB peroxide, then uranium hexafluoride from the
yellowcake, four fluorite and a water bucket. The assembly machine builds two gas centrifuges; the first stands at the
plant's east port and takes the 1,200 mB UF6 straight from the plant's output tank, the second stands behind it (the
"behind" neighbour, one block south) and is the end of the two-machine cascade, which turns the last 600 mB of its output
into six uranium fuel nuggets and a fluorite. The fuel nuggets make a fuel billet. The six U-238 nuggets of the cascade and
two steel ingots are alloyed into ferrouranium in a crucible on a firebox and cast in an ingot mold made on an iron anvil;
an iron anvil smithed with ten ferrouranium ingots becomes the tier-4 anvil, which builds gold wire for the gold coils of the
gas centrifuge overclocking upgrade. A third gas centrifuge shows that the high-enrichment step only runs with that upgrade.
Afterwards the world is left and opened again and the same server readings are compared.

Layout (y = -60 is the floor the machines stand on; the cable bus runs in the grass layer below at z = OZ + 6):
    plant core P (3 x 3), its power riser at P - 2x; GC1 at P + 2x (the plant's east port P + (2, 0, 0)), facing north, so the
    block behind it is P + (2, 0, 1), where GC2 stands, facing east (behind GC2 is the plant's corner, not a centrifuge, so GC2
    is the end of the cascade); GC3 at P + 6x on its own. The centrifuges stand on cable cells that are replaced by grass once
    they are charged: from then on their stored energy only falls by what they spend.

Expected values are derived from the code (NEO file:line, the 1.7.10 original's file:line where NEO ports it); readings are
server data (`data get block` / `data get entity`). The gas centrifuge cascade is simulated tick by tick here (cascade_sim)
with the original's update order (TileEntityMachineGasCent.java:180-231): conversion of the real UF6, progress and power,
the enrichment step, then every 10 game ticks the hand-over to the machine behind or, at the end of a cascade holding LEUF6,
the conversion of 600 mB into six fuel nuggets and a fluorite. Machines tick in the order they were placed (the plant before
GC1 before GC2), so the plant's provide in tick U + 1 (MachineChemicalPlantBlockEntity.java:112-126, before its own recipe
step at :147) lands in GC1's tank before GC1 ticks in the same game tick.
"""
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

H = _lib.H
GC, CP, CA = 'gas-centrifuge', 'chemical-plant', 'crucible-alloying'

SCENARIO = dict(
    id='gas-centrifuge.mainline_stage7',
    feature=GC,
    features=[GC, CP, CA],
    title='Main line stage 7: uranium to yellowcake and UF6, a two-machine gas centrifuge cascade to uranium fuel, ferrouranium '
          'and the tier-4 anvil, the overclocking upgrade for the high-enrichment step',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

# The stage-7 start list: items obtainable before stage 7 (item, the stage it is first obtainable in); "block:" rows are
# world-generation blocks.
HANDOVER = [
    ('block:hbmsntm:ore_oil', 1), ('hbmsntm:arc_electrode_graphite', 2), ('hbmsntm:ball_fireclay', 2),
    ('hbmsntm:billet_silicon', 4), ('hbmsntm:centrifuge_element', 4), ('hbmsntm:cinnabar', 1),
    ('hbmsntm:circuit_analog_board', 4), ('hbmsntm:circuit_capacitor', 4), ('hbmsntm:circuit_integrated_board', 4),
    ('hbmsntm:circuit_microchip', 4), ('hbmsntm:circuit_printed_board', 4), ('hbmsntm:circuit_printed_silicon_wafer', 4),
    ('hbmsntm:circuit_vacuum_tube', 4), ('hbmsntm:coil_copper', 2), ('hbmsntm:coil_copper_ring', 2),
    ('hbmsntm:coil_tungsten', 1), ('hbmsntm:concrete_asbestos', 4), ('hbmsntm:concrete_smooth', 4),
    ('hbmsntm:drill_titanium', 4), ('hbmsntm:furnace_combination', 2), ('hbmsntm:heat_boiler', 3), ('hbmsntm:heater_firebox', 3),
    ('hbmsntm:ingot_aluminium', 1), ('hbmsntm:ingot_beryllium', 1), ('hbmsntm:ingot_boron', 4), ('hbmsntm:ingot_copper', 1),
    ('hbmsntm:ingot_desh', 5), ('hbmsntm:ingot_firebrick', 2), ('hbmsntm:ingot_lead', 1), ('hbmsntm:ingot_niobium', 4),
    ('hbmsntm:ingot_polymer', 5), ('hbmsntm:ingot_raw@41', 2), ('hbmsntm:ingot_red_copper', 2), ('hbmsntm:ingot_rubber', 5),
    ('hbmsntm:ingot_steel', 2), ('hbmsntm:ingot_titanium', 1), ('hbmsntm:ingot_tungsten', 1), ('hbmsntm:machine_arc_furnace', 4),
    ('hbmsntm:machine_arc_welder', 4), ('hbmsntm:machine_assembly_machine', 4), ('hbmsntm:machine_blast_furnace', 2),
    ('hbmsntm:machine_catalytic_cracker', 5), ('hbmsntm:machine_centrifuge', 4), ('hbmsntm:machine_chemical_plant', 4),
    ('hbmsntm:machine_crucible', 2), ('hbmsntm:machine_crystallizer', 4), ('hbmsntm:machine_fraction_tower', 5),
    ('hbmsntm:machine_press', 2), ('hbmsntm:machine_refinery', 5), ('hbmsntm:machine_shredder', 4),
    ('hbmsntm:machine_soldering_station', 4), ('hbmsntm:machine_well', 5), ('hbmsntm:mold_base', 2), ('hbmsntm:motor', 2),
    ('hbmsntm:motor_desh', 5), ('hbmsntm:niter', 1), ('hbmsntm:nugget_beryllium', 1), ('hbmsntm:nugget_zirconium', 1),
    ('hbmsntm:ore_beryllium', 1), ('hbmsntm:ore_cobalt', 1), ('hbmsntm:ore_lead_deepslate', 1), ('hbmsntm:ore_thorium', 1),
    ('hbmsntm:ore_titanium_deepslate', 1), ('hbmsntm:ore_uranium', 1), ('hbmsntm:pipe_copper', 1), ('hbmsntm:pipe_rubber', 5),
    ('hbmsntm:pipe_steel', 2), ('hbmsntm:plate_cast@0', 2), ('hbmsntm:plate_cast@11', 2), ('hbmsntm:plate_cast@12', 2),
    ('hbmsntm:plate_cast@5', 2), ('hbmsntm:plate_cast@8', 2), ('hbmsntm:plate_copper', 1), ('hbmsntm:plate_dura_steel', 2),
    ('hbmsntm:plate_iron', 1), ('hbmsntm:plate_lead', 1), ('hbmsntm:plate_polymer', 1), ('hbmsntm:plate_steel', 2),
    ('hbmsntm:plate_titanium', 1), ('hbmsntm:powder_aluminium', 2), ('hbmsntm:powder_coal', 4), ('hbmsntm:powder_desh_mix', 4),
    ('hbmsntm:resource_limestone', 1), ('hbmsntm:rod_empty', 2), ('hbmsntm:rod_quad_empty', 2), ('hbmsntm:shell_steel', 2),
    ('hbmsntm:shell_titanium', 1), ('hbmsntm:stamp_stone_flat', 2), ('hbmsntm:steel_grate', 2), ('hbmsntm:steel_scaffold', 2),
    ('hbmsntm:sulfur', 1), ('hbmsntm:tank_steel', 2), ('hbmsntm:transformer', 4), ('hbmsntm:upgrade_template', 4),
    ('hbmsntm:wire_copper', 1), ('hbmsntm:wire_gold', 1), ('hbmsntm:wire_lead', 1), ('hbmsntm:wire_red_copper', 2),
    ('hbmsntm:wire_tungsten', 1),
]
# From the start list, exactly what the line uses (given right before the section that uses it).
GIVE = {
    'smelt': [(H + 'ore_uranium', 2)],
    'plant': [(H + 'machine_chemical_plant', 1), (H + 'sulfur', 2)],
    'assembly': [(H + 'machine_assembly_machine', 1), (H + 'centrifuge_element', 8), (H + 'ingot_polymer', 16), (H + 'ingot_desh', 4),
                 (H + 'plate_steel', 16)],
    'crucible': [(H + 'heater_firebox', 1), (H + 'machine_crucible', 1), (H + 'ingot_steel', 3), (H + 'mold_base', 1)],
    'upgrade': [(H + 'ingot_niobium', 1), (H + 'ingot_rubber', 2), (H + 'upgrade_template', 1), (H + 'motor', 1)],
}
# Vanilla materials (always obtainable).
VANILLA = {
    'smelt': [('minecraft:crafting_table', 1), ('minecraft:furnace', 1), ('minecraft:coal', 1)],
    'plant': [('minecraft:water_bucket', 1), ('minecraft:water_bucket', 1), ('minecraft:oak_log', 16)],
    'crucible': [('minecraft:coal', 8)],
    'anvil': [('minecraft:gold_ingot', 4), ('minecraft:iron_ingot', 4)],
}
# Not on the stage-7 start list but used by the line, with the basis that they are obtainable before stage 7 (or 预写).
OUTSIDE = {
    'smelt': [],
    'plant': [(H + 'machine_wood_burner', 1, 'obtainable from stage 2 (the wood-burner line), the power source of the bus'),
              (H + 'fluid_tank_empty', 1, 'universal fluid tank, 8 from 6 aluminium plates + 2 iron plates + 1 glass pane '
                                         '(NtmRecipeProvider.java:76-84), stage-1 materials')],
    'fluorite': [(H + 'fluorite', 4, 'dropped by fluorite ore, obtainable from the start (world generation)')],
    'assembly': [(H + 'circuit_military_grade_board', 2, 'a stage-7 checkpoint whose recipe (soldering station) is open from stage 5; '
                                                         'the soldering chain is not replayed here')],
    'centrifuge3': [(H + 'machine_gas_centrifuge', 1, 'a third gas centrifuge for the high-enrichment check, a machine handed out '
                                                      'directly (command-built; the same assembly recipe as the two built on the line)')],
    'crucible': [(H + 'foundry_mold', 1, 'stage-2 foundry part (crafted from firebricks and a stone slab)')],
    'anvil': [(H + 'anvil', 2, 'iron anvil, obtainable from the start (crafted from iron blocks): one to work on, one smithed '
                               'into the tier-4 anvil')],
}
# State written by command instead of produced on the line; the expectation texts that rest on it say 预写.
FERRO_PREWRITTEN = 8
PREWRITTEN = [
    '预写 8 ferrouranium ingots for the tier-4 anvil (10 needed, AnvilRecipes.java:107): the line casts 2 from the 6 U-238 nuggets '
    'of one cascade, and no source before stage 7 makes the rest',
    '预写 the third gas centrifuge\'s input tank set to 300 mB HEUF6 (data merge): the four-machine cascade that makes HEUF6 is not '
    'played',
]

Y = -60
OX, OZ = 3000, 3000
BUS_Z = OZ + 6
BUS_X = (OX - 12, OX + 16)
BURNER_AT = (OX - 8, OZ)          # ground cell clicked (from the south)
PLANT_AT = (OX, OZ)
ASSEMBLER_AT = (OX + 13, OZ)
WZ = OZ + 10                      # the workshop row
CT, VF, A1, A4 = (OX - 4, Y, WZ), (OX - 2, Y, WZ), (OX, Y, WZ), (OX + 2, Y, WZ)
FIRE_AT = (OX + 10, OZ + 13)      # ground cell clicked for the firebox; the crucible goes on top of it

# --- numbers from the code -----------------------------------------------------------------------------------------------
WATER_ID, UF6_ID, PEROXIDE_ID = 1, 29, 35   # Fluids.java:250-251,279,285: NONE is id 0, ids follow the registration order
GC_MAX = 100_000                  # MachineGasCentrifugeBlockEntity.java:54; TileEntityMachineGasCent.java:46
GC_STEP, GC_STEP_FAST = 150, 80   # :56-57; original :47, :327-332
GC_HE, GC_HE_FAST = 200, 300      # :59-60, :135; original :199-202
PSEUDO = {                        # name: (consumed, produced, next, outputs) GasCentrifugeRecipes.java:28-31,77-80; original :26-29
    'NUF6': (400, 300, 'LEUF6', {'nugget_u238': 1}),
    'LEUF6': (300, 200, 'MEUF6', {'nugget_u238': 1, 'fluorite': 1}),
    'MEUF6': (200, 100, 'HEUF6', {'nugget_u238': 1}),
    'HEUF6': (300, 0, 'NONE', {'nugget_u238': 2, 'nugget_u235': 1, 'fluorite': 1}),
}
PSEUDO_MAX = 8000                 # MachineGasCentrifugeBlockEntity.java:62; original :61-62
TAIL_MB, TAIL_FUEL = 600, 6       # :64,:158-166; original :222-229
UF6_MB = 1200                     # ChemicalPlantRecipes.java:292-297; original :385-389
PHASE = 3                         # the UF6 run is started so that it completes at a game time = 3 (mod 10)
FERRO_RUN = (16, 8, 24)           # steel, U-238, ferrouranium quanta of one crucible.ferro run: CrucibleRecipes.java:71-73
                                  # (2 + 1 -> 3 nuggets of 8 quanta, MaterialShapes NUGGET); original CrucibleRecipes.java:95-97
INGOT_Q, NUGGET_Q = 72, 8
MAT_STEEL, MAT_U238, MAT_FERRO = 30, 9238, 37   # Mats.java:46,80,141,147 (_AS = 30)


def module_ticks(duration, cycles=1):
    """ModuleMachineBase.process (ModuleMachineBase.java:115-128; original ModuleMachineBase.java:117-131): with power each tick
    adds min(1 / duration, 1) to a double; the output comes in the tick the sum reaches 1. Returns the completion ticks."""
    p, t, out = 0.0, 0, []
    while len(out) < cycles:
        t += 1
        p += min(1.0 / duration, 1.0)
        if p >= 1.0:
            out.append(t)
            p = p - 1.0 if len(out) < cycles else 0.0
    return out


def cascade_sim(u):
    """The two-machine cascade after the plant has made 1,200 mB UF6 at game time u (the plant hands it to GC1 in tick u + 1,
    before GC1 ticks). Original TileEntityMachineGasCent.java:180-231 (NEO MachineGasCentrifugeBlockEntity.java:97-175), GC1
    before GC2 in every tick. Returns dict(first_step, t1 (first hand-over of LEUF6), steps, fuel_at, items per machine,
    working ticks per machine, outputs)."""
    gcs = [dict(tank=0, inp='NUF6', inf=0, out='LEUF6', outf=0, prog=0, power=GC_MAX, items=Counter(), work=0, steps=[]),
           dict(tank=0, inp='LEUF6', inf=0, out='MEUF6', outf=0, prog=0, power=GC_MAX, items=Counter(), work=0, steps=[])]
    t1 = fuel_at = None
    for t in range(u + 1, u + 3000):
        if t == u + 1:
            gcs[0]['tank'] = UF6_MB
        for i, g in enumerate(gcs):
            if g['inp'] == 'NUF6' and g['tank'] > 0:                      # attemptConversion (original :142-149)
                moved = min(PSEUDO_MAX - g['inf'], g['tank'])
                g['tank'] -= moved
                g['inf'] += moved
            used, made, _, outs = PSEUDO[g['inp']]
            if g['power'] > 0 and g['inf'] >= used and g['outf'] + made <= PSEUDO_MAX:   # canEnrich (original :109-129)
                g['prog'] += 1
                g['work'] += 1
                g['power'] -= GC_HE
                if g['prog'] >= GC_STEP:                                    # enrich (original :131-140)
                    g['prog'] = 0
                    g['inf'] -= used
                    g['outf'] += made
                    g['items'].update(outs)
                    g['steps'].append(t)
            else:
                g['prog'] = 0
            if t % 10 == 0:                                                 # original :217-231
                if i == 0:
                    nxt = gcs[1]
                    if nxt['inf'] < PSEUDO_MAX and g['outf'] > 0:
                        moved = min(PSEUDO_MAX - nxt['inf'], g['outf'])
                        g['outf'] -= moved
                        nxt['inf'] += moved
                        if t1 is None:
                            t1 = t
                elif g['inp'] == 'LEUF6' and g['outf'] >= TAIL_MB:
                    g['outf'] -= TAIL_MB
                    g['items'].update({'nugget_uranium_fuel': TAIL_FUEL, 'fluorite': 1})
                    fuel_at = t
        if fuel_at is not None:
            break
    return dict(t1=t1, fuel_at=fuel_at, gc1=gcs[0], gc2=gcs[1])


def ceil10(x):
    return -(-x // 10) * 10


_SIM = cascade_sim(1000 + PHASE)
SIM_T1 = _SIM['t1'] - (1000 + PHASE)          # ticks after the UF6 is made
SIM_F = _SIM['fuel_at'] - (1000 + PHASE)
assert SIM_T1 == ceil10(PHASE + GC_STEP) - PHASE and SIM_F == SIM_T1 + 3 * GC_STEP, (SIM_T1, SIM_F)
SIM_WORK = (_SIM['gc1']['work'], _SIM['gc2']['work'])
K_PEROXIDE = module_ticks(50)[0]
K_YELLOW = module_ticks(250)[0]
K_UF6 = module_ticks(100)[0]
K_GASCENT = module_ticks(400, 2)

E = [
    (GC, 'start-items', '记录：起点物品取自阶段 7 的交接清单，只发放这条线用到的；清单之外发放的（烧木发电机、通用流体罐、4 个萤石、2 块军用级电路板、'
                        '坩埚的铸模、2 个铁砧）各有更早阶段的来源，第三台气体离心机是直接发放的机器（命令搭建），都写在文件的 OUTSIDE 里；'
                        '预写的状态另列（PREWRITTEN）',
     'stage-7 start list (in this file)'),
    (GC, 'smelt', '熔炉里 2 块铀矿加 1 块煤：每块 200 刻，第 200 刻出第 1 个铀锭、第 400 刻出第 2 个：第 399 刻输出槽里 1 个，第 400 刻 2 个',
     'NtmRecipeProvider.java:2651,3080-3087 (cooking time 200), the vanilla furnace; SmeltingRecipes.java:31 (original)'),
    (GC, 'billets', '工作台：2 个铀锭横排一行，得 3 个铀坯',
     'NtmRecipeProvider.java:3274,3599-3602; MineralRecipes.java:115,534 (original)'),
    (GC, 'build', '装配机选“气体离心机”配方，放入 8 个离心机元件、16 个聚合物锭、4 个 Desh 锭、16 块钢板、2 块军用级电路板：每台 400 刻、'
                  '每刻 100 HE，按双精度累加进度，第 %d 刻出第 1 台（第 %d 刻还没有），第 %d 刻出第 2 台，输入用完'
                  % (K_GASCENT[0], K_GASCENT[0] - 1, K_GASCENT[1]),
     'AssemblyMachineRecipes.java:303-308, ModuleMachineBase.java:115-128; AssemblyMachineRecipes.java:282-283, ModuleMachineBase.java:117-131 (original)'),
    (GC, 'uf6-transfer', '化工厂在第 U 刻做出 1,200 mB 六氟化铀后，第 U+1 刻化工厂直接交给东侧口上的第一台气体离心机（离心机默认收六氟化铀，不用识别器），'
                         '同一刻第一台已把它转成 1,200 mB 天然六氟化铀（NUF6）并走了第 1 刻：进度 1、电量 %d、化工厂输出罐为 0' % (GC_MAX - GC_HE),
     'MachineChemicalPlantBlockEntity.java:112-126,147, MachineGasCentrifugeBlockEntity.java:78-80,128-150,245-252; '
     'TileEntityMachineGasCent.java:60-62,142-149,190-215 (original)'),
    (GC, 'align', '第一台每步吃 400 mB NUF6、出 300 mB LEUF6，每步 %d 刻：第 U+%d 刻出第一批；交给身后第二台只在游戏时间是 10 的倍数的刻里发生，'
                  'U 取模 10 余 %d 时第一次交接在第 U+%d 刻（ceil10(U+150)）：前一刻第一台输出罐 300、第二台输入 0，这一刻第一台输出 0、第二台输入 300 且已走 1 刻'
                  % (GC_STEP, GC_STEP, PHASE, SIM_T1),
     'MachineGasCentrifugeBlockEntity.java:152-158,259-282, GasCentrifugeRecipes.java:30-31; TileEntityMachineGasCent.java:151-174,217-222, '
     'GasCentrifugeRecipes.java:28-29 (original)'),
    (GC, 'fuel', '两台串联的末端：第二台每步吃 300 mB LEUF6、出 200 mB MEUF6 加 1 个 U-238 粒和 1 个萤石；三步之后存满 600 mB，'
                 '在下一个 10 的倍数刻换成 6 个铀燃料粒和 1 个萤石。按原版更新顺序逐刻模拟：第 U+%d 刻出齐（第 U+%d 刻还没有），'
                 '整条串联共出 6 个 U-238 粒、6 个铀燃料粒、4 个萤石' % (SIM_F, SIM_F - 1),
     'MachineGasCentrifugeBlockEntity.java:64,152-166, GasCentrifugeRecipes.java:30,79,93; TileEntityMachineGasCent.java:217-231, '
     'GasCentrifugeRecipes.java:28,99 (original)'),
    (GC, 'power', '两台离心机充满 %d HE 后断开电缆：各工作 %d 刻、每刻 %d HE，出齐时各剩 %d HE'
                  % (GC_MAX, SIM_WORK[0], GC_HE, GC_MAX - GC_HE * SIM_WORK[0]),
     'MachineGasCentrifugeBlockEntity.java:54,59,132-141; TileEntityMachineGasCent.java:46,194-207 (original)'),
    (GC, 'fuel-billet', '工作台：6 个铀燃料粒（两行三列）得 1 个铀燃料坯',
     'NtmRecipeProvider.java:3275,3587-3592; MineralRecipes.java:139,521-522 (original)'),
    (GC, 'tier4-anvil', '铁砧锻造：铁铁砧加 10 个铀铁合金锭（2 个本线浇铸，8 个预写）得铀铁合金铁砧（meta 4，4 级）',
     'AnvilRecipes.java:107,160-170, NTMAnvilBlock.java:60,71; AnvilRecipes.java:69 (original)'),
    (GC, 'tier4-wire', '放下 4 级铁砧，翻页到“1 个金锭 → 8 根金线”（4 级配方，3 级铁砧的列表里没有），悬停核对后造 4 次：金线 +32，金锭 -4',
     'AnvilRecipes.java:190,752-757, AnvilMenuScreen.java:30,45-50; AnvilRecipes.java:166-168 (original)'),
    (GC, 'upgrade-craft', '工作台：每个金线圈 8 根金线加 1 个铁锭（做 4 个）；4 个金线圈、1 个铌锭、2 个橡胶锭、1 个升级模板、1 个电动机得 1 个气体离心机超频升级',
     'NtmRecipeProvider.java:236-245,1913-1920; CraftingManager.java:163,729 (original)'),
    (GC, 'high-speed', '预写：第三台离心机输入罐写成 300 mB 高浓缩六氟化铀（HEUF6）。不装超频升级时 160 刻里不走、不耗电、不出料；'
                       '装上升级后每步 %d 刻、每刻 %d HE：第 %d 刻还没有，第 %d 刻出 2 个 U-238 粒、1 个 U-235 粒、1 个萤石，电量少 %d'
                       % (GC_STEP_FAST, GC_HE_FAST, GC_STEP_FAST - 1, GC_STEP_FAST, GC_HE_FAST * GC_STEP_FAST),
     'MachineGasCentrifugeBlockEntity.java:56-60,135,208-214,223, GasCentrifugeRecipes.java:28,77; '
     'TileEntityMachineGasCent.java:114-116,199-202,327-332, GasCentrifugeRecipes.java:26 (original)'),
    (GC, 'reload', '退出世界再打开：三台离心机的电量、罐量与罐的类型、输出槽物品与重开前相同（只比两次读数之间不动、且至少一个非默认的存储量）',
     'MachineGasCentrifugeBlockEntity.java:422-458; TileEntityMachineGasCent.java:81-99 (original)'),
    (CP, 'peroxide', '化工厂选“过氧化氢生产”：1 桶水 → 第 %d 刻输出罐 1,000 mB 过氧化氢（前一刻为 0）；空的通用流体罐放进装罐槽，下一刻装满（槽 19，meta %d）'
                     % (K_PEROXIDE, PEROXIDE_ID),
     'ChemicalPlantRecipes.java:214-216, MachineChemicalPlantBlockEntity.java:104-110, FluidContainerRegistry.java:43-57, '
     'Fluids.java:285 (id 35); ChemicalPlantRecipes.java:288-290, Fluids.java:296 (original)'),
    (CP, 'yellowcake', '换“黄饼生产”，装满过氧化氢的通用罐放进进料槽，加 2 个铀坯、2 个硫：第 %d 刻出 1 份黄饼（前一刻没有），输入罐剩 500 mB 过氧化氢'
                       % K_YELLOW,
     'ChemicalPlantRecipes.java:288-291, ModuleMachineBase.java:40-44,115-145; ChemicalPlantRecipes.java:380-383 (original)'),
    (CP, 'uf6', '换“六氟化铀生产”，黄饼、4 个萤石、1 桶水：第 %d 刻输出罐 1,200 mB 六氟化铀（id %d）并出 2 个硫（前一刻都没有）' % (K_UF6, UF6_ID),
     'ChemicalPlantRecipes.java:292-297, Fluids.java:279 (id 29); ChemicalPlantRecipes.java:385-389, Fluids.java:290 (original)'),
    (CP, 'reload', '退出世界再打开：化工厂的配方、电量、罐与槽里的物品与重开前相同（至少一个非默认的存储量）',
     'MachineChemicalPlantBlockEntity.java:253-275, ModuleMachineBase.java:242-250'),
    (CA, 'ferro', '坩埚选“铀铁合金”配方，放入 2 个钢锭（144 份）和本线离心机出的 6 个 U-238 粒（48 份）：每 3 刻一轮 16 份钢 + 8 份 U-238 → 24 份铀铁合金，'
                  '6 轮后 U-238 用完，144 份铀铁合金从前口浇进锭模，得 2 个铀铁合金锭，坩埚里剩 48 份钢；锭模在铁铁砧上由 1 个钢锭（保留）加模具底座锻出',
     'CrucibleRecipes.java:71-73, MachineCrucibleBlockEntity.java:74-75,126-149,164-166, AnvilSmithingIngotMoldRecipe.java:17-32, '
     'AnvilRecipes.java:131; CrucibleRecipes.java:95-97, TileEntityCrucible.java:189-209,412, AnvilRecipes.java:102 (original)'),
    (CA, 'reload', '退出世界再打开：坩埚的配方与剩下的 48 份钢不变',
     'MachineCrucibleBlockEntity.java:294-310'),
]


def expectations():
    return [dict(id='%s.%s' % (f, i), text=t, source=s) for f, i, t, s in E]


S = {}
GIVEN = []
ISSUED = []


def cmd(ctx, command, **kw):
    return ctx.step('cmd', command=command, **kw)


def give(ctx, *pairs):
    for item, n in pairs:
        cmd(ctx, 'give @s %s %d' % (item, n))
        GIVEN.append((item, n))


def issue(ctx, key):
    for item, n, why in OUTSIDE.get(key, []):
        cmd(ctx, 'give @s %s %d' % (item, n))
        ISSUED.append((item, n, why))


def stock(ctx, key):
    give(ctx, *GIVE.get(key, []))
    give(ctx, *VANILLA.get(key, []))
    issue(ctx, key)


def need(flag, what):
    if not S.get(flag):
        raise _lib.Missing('needs %s from an earlier section, which did not finish' % what)


def front(pos, back=2.5):
    return [pos[0] + 0.5, Y, pos[2] + back]


def place_on_ground(ctx, item, cell, stand, meta=None):
    """Holds `item` and right-clicks the top of the grass under `cell` from `stand` (feet): real placement."""
    _lib.place(ctx, item, (cell[0], Y - 1, cell[1]), 'up', stand, meta=meta)


def core_near(ctx, block, x, z, up=3):
    return _lib.core_of(ctx, block, (x - 3, Y, z - 3), (x + 3, Y + up, z + 3))[0]


def gc_read(ctx, pos):
    d = _lib.block_data(ctx, pos)
    t = _lib.tanks(d)
    items = Counter()
    for s, e in _lib.items_of(d).items():
        if 0 <= s <= 3:
            items[e['id'].split(':')[1]] += e['count']
    return dict(power=d.get('power'), progress=d.get('progress'), tank=(t.get('tank') or {}).get('fill'),
                inp=((t.get('inputTank') or {}).get('fill'), (t.get('inputTank') or {}).get('type')),
                out=((t.get('outputTank') or {}).get('fill'), (t.get('outputTank') or {}).get('type')), items=dict(items))


def plant_tanks(d):
    return {n: (v['fill'], v['type']) for n, v in _lib.tanks(d).items() if v['fill']}


def stack_list(arr):
    return {arr[i]: arr[i + 1] for i in range(0, len(arr) - 1, 2)}


def open_plant(ctx):
    p = S['plant']
    return _lib.open_gui(ctx, (p[0], Y, p[2] + 1), 'south', front((p[0], Y, p[2] + 1)), 'MachineChemicalPlantScreen')


def open_gc(ctx, key):
    pos = S[key]
    face, stand = {'gc1': ('north', [pos[0] + 0.5, Y, pos[2] - 2.5])}.get(key, ('south', [pos[0] + 0.5, Y, pos[2] + 2.5]))
    return _lib.open_gui(ctx, pos, face, stand, 'MachineGasCentrifugeScreen', center=True)


def move(ctx, a, b):
    _lib.click(ctx, a)
    _lib.click(ctx, b)


def burner_on(ctx):
    """Switches the wood burner on with the button in its screen (GUI 53,17, 16 x 15; MachineWoodBurnerBlockEntity.receiveControl)."""
    b = S['burner']
    if _lib.block_data(ctx, b).get('isOn'):
        return
    hud = _lib.open_gui(ctx, b, 'south', front(b), 'MachineWoodBurnerScreen')
    ctx.step('click', at=[hud['gui_left'] + 61, hud['gui_top'] + 24], button=0, after=4)
    ctx.step('close')
    if not _lib.block_data(ctx, b).get('isOn'):
        raise RuntimeError('the wood burner did not switch on')


def charge(ctx, nodes, label):
    """With the burner on, sprints until every block in `nodes` holds its full buffer (maxPower where the block saves it)."""
    def full(c):
        for p in nodes:
            d = _lib.block_data(c, p)
            if d.get('power', 0) < d.get('maxPower', GC_MAX):
                return False
        return True
    ctx.server('tick freeze')
    rec = ctx.sprint(60000, until=full, poll_s=0.5, label='charge-' + label, timeout_s=600)
    ctx.server('tick freeze')
    if not full(ctx):
        raise RuntimeError('charge %s: buffers not full after %s ticks' % (label, rec.get('advanced')))


def lay_cable(ctx, x, z0, riser):
    if riser:
        cmd(ctx, 'setblock %d %d %d hbmsntm:red_cable' % (x, Y, z0))
    cmd(ctx, 'fill %d %d %d %d %d %d hbmsntm:red_cable' % (x, Y - 1, z0, x, Y - 1, BUS_Z))


# ---------------------------------------------------------------- sections

def sec_smelt(ctx):
    stock(ctx, 'smelt')
    place_on_ground(ctx, 'minecraft:crafting_table', CT[::2], front(CT))
    place_on_ground(ctx, 'minecraft:furnace', VF[::2], front(VF))
    _lib.open_gui(ctx, VF, 'south', front(VF), 'Furnace')
    _lib.put_stack(ctx, 3, H + 'ore_uranium', 0)
    t0 = ctx.server()['game_time']
    _lib.put_stack(ctx, 3, 'minecraft:coal', 1)
    ctx.step('close')
    got = {}
    for t in (399, 400):
        _lib.advance_to(ctx, t0, t, 'furnace-uranium')
        got[t] = _lib.slot_count(_lib.block_data(ctx, VF), 2, H + 'ingot_uranium')
    ctx.check(GC + '.smelt', got == {399: 1, 400: 2}, 'uranium ingots in the furnace output at tick 399 / 400 after loading: %s (want 1 / 2)'
              % [got[399], got[400]])
    _lib.open_gui(ctx, VF, 'south', front(VF), 'Furnace')
    _lib.shift_click(ctx, 2)
    ctx.step('close')
    _lib.open_gui(ctx, CT, 'south', front(CT), 'Crafting')
    before = _lib.count(ctx, H + 'billet_uranium')
    _lib.craft(ctx, ['XX'], dict(X=H + 'ingot_uranium'))
    ctx.step('close')
    items = _lib.inventory(ctx)
    made, ingots = _lib.count(ctx, H + 'billet_uranium', items=items) - before, _lib.count(ctx, H + 'ingot_uranium', items=items)
    ctx.check(GC + '.billets', made == 3 and ingots == 0, 'uranium billets +%d (want 3), uranium ingots left %d' % (made, ingots))
    S['billets'] = made >= 2


def sec_plant(ctx):
    need('billets', 'two uranium billets')
    stock(ctx, 'plant')
    cmd(ctx, 'fill %d %d %d %d %d %d hbmsntm:red_cable' % (BUS_X[0], Y - 1, BUS_Z, BUS_X[1], Y - 1, BUS_Z))
    place_on_ground(ctx, H + 'machine_wood_burner', BURNER_AT, [BURNER_AT[0] + 0.5, Y, BURNER_AT[1] + 3.5])
    b = core_near(ctx, H + 'machine_wood_burner', *BURNER_AT, up=2)
    S['burner'] = b
    lay_cable(ctx, b[0], b[2] - 2, True)          # its power ports: two blocks behind the core (MachineWoodBurnerBlockEntity.java:226-236)
    _lib.open_gui(ctx, b, 'south', front(b), 'MachineWoodBurnerScreen')
    _lib.put_stack(ctx, 6, 'minecraft:oak_log', 0)
    ctx.step('close')
    place_on_ground(ctx, H + 'machine_chemical_plant', PLANT_AT, [PLANT_AT[0] + 0.5, Y, PLANT_AT[1] + 4.5])
    p = core_near(ctx, H + 'machine_chemical_plant', *PLANT_AT)
    S['plant'] = p
    lay_cable(ctx, p[0] - 2, p[2], True)          # port (x - 2, z) (MachineChemicalPlantBlockEntity.java:210-226)
    burner_on(ctx)
    open_plant(ctx)
    got = _lib.pick_recipe(ctx, p, 'hbmChemicalPlant.json', 'chem.peroxide', 'chem.peroxide')
    ctx.step('close')
    if got != 'chem.peroxide':
        raise RuntimeError('plant recipe after the selector: %r' % got)
    charge(ctx, [p], 'plant')
    # peroxide: the bucket loads in the plant's next tick (loadTank before the recipe step, :104-110,147), so that tick is
    # the recipe's first
    open_plant(ctx)
    bucket = _lib.find_slot(_lib.inventory(ctx), 'minecraft:water_bucket')
    move(ctx, _lib.menu_slot(22, bucket), 10)
    t0 = ctx.server()['game_time']
    ctx.step('close')
    reads = {}
    for t in (K_PEROXIDE - 1, K_PEROXIDE):
        _lib.advance_to(ctx, t0, t, 'plant-peroxide')
        reads[t] = plant_tanks(_lib.block_data(ctx, p))
    open_plant(ctx)
    _lib.put_stack(ctx, 22, H + 'fluid_tank_empty', 16)
    ctx.step('close')
    _lib.server_steps(ctx, 1)
    d = _lib.block_data(ctx, p)
    full = _lib.slot_item(d, 19)
    want = {K_PEROXIDE - 1: {'i0': (1000, WATER_ID)}, K_PEROXIDE: {'o0': (1000, PEROXIDE_ID)}}
    ok = (reads == want and full is not None and full.get('id') == H + 'fluid_tank_full'
          and _lib.meta_of(full) == PEROXIDE_ID and 'o0' not in plant_tanks(d))
    ctx.check(CP + '.peroxide', ok, 'tank fills at tick %d / %d: %s (want %s); one tick after the empty universal tank: slot 19 %s, tanks %s'
              % (K_PEROXIDE - 1, K_PEROXIDE, reads.get(K_PEROXIDE - 1), want, full and (full.get('id'), _lib.meta_of(full)),
                 plant_tanks(d)))
    # yellowcake
    open_plant(ctx)
    got = _lib.pick_recipe(ctx, p, 'hbmChemicalPlant.json', 'chem.yellowcake', 'chem.yellowcake')
    if got != 'chem.yellowcake':
        raise RuntimeError('plant recipe after the selector: %r' % got)
    _lib.server_steps(ctx, 2)                      # the recipe types the input tank (setupTanks) before a container can load
    _lib.shift_click(ctx, 13)                      # the emptied water bucket out, so the emptied universal tank can go there
    move(ctx, 19, 10)
    _lib.put_n(ctx, 22, H + 'billet_uranium', [4], k=2)
    sulfur = _lib.find_slot(_lib.inventory(ctx), H + 'sulfur', at_least=2)
    move(ctx, _lib.menu_slot(22, sulfur), 5)
    t0 = ctx.server()['game_time']
    ctx.step('close')
    reads = {}
    for t in (K_YELLOW - 1, K_YELLOW):
        _lib.advance_to(ctx, t0, t, 'plant-yellowcake')
        d = _lib.block_data(ctx, p)
        reads[t] = (_lib.slot_count(d, 7, H + 'powder_yellowcake'), plant_tanks(d), _lib.slot_count(d, 4), _lib.slot_count(d, 5))
    empty = _lib.slot_item(d, 13)
    ok = (reads[K_YELLOW - 1][0] == 0 and reads[K_YELLOW] == (1, {'i0': (500, PEROXIDE_ID)}, 0, 0)
          and empty is not None and empty.get('id') == H + 'fluid_tank_empty')
    ctx.check(CP + '.yellowcake', ok, '(yellowcake, tanks, billets left, sulfur left) at tick %d: %s; at tick %d: %s (want 1, i0 500 '
              'peroxide, 0, 0); emptied universal tank in slot 13: %s' % (K_YELLOW - 1, reads[K_YELLOW - 1], K_YELLOW, reads[K_YELLOW],
                                                                          empty and empty.get('id')))
    S['yellowcake'] = reads[K_YELLOW][0] == 1


def sec_assembly(ctx):
    need('plant', 'the cable bus')
    stock(ctx, 'assembly')
    place_on_ground(ctx, H + 'machine_assembly_machine', ASSEMBLER_AT, [ASSEMBLER_AT[0] + 0.5, Y, ASSEMBLER_AT[1] + 4.5])
    a = core_near(ctx, H + 'machine_assembly_machine', *ASSEMBLER_AT)
    S['assembler'] = a
    lay_cable(ctx, a[0] - 2, a[2], True)          # port (x - 2, z) (MachineAssemblyMachineBlockEntity.java:215-234)
    face = (a[0], Y, a[2] + 1)
    _lib.open_gui(ctx, face, 'south', front(face), 'MachineAssemblyMachineScreen')
    got = _lib.pick_recipe(ctx, a, 'hbmAssemblyMachine.json', 'ass.gascent', 'block.hbmsntm.machine_gas_centrifuge')
    ctx.step('close')
    if got != 'ass.gascent':
        raise RuntimeError('assembler recipe after the selector: %r' % got)
    charge(ctx, [a, S['plant']], 'assembler')
    _lib.open_gui(ctx, face, 'south', front(face), 'MachineAssemblyMachineScreen')
    order = [H + 'centrifuge_element', H + 'ingot_polymer', H + 'ingot_desh', H + 'plate_steel', H + 'circuit_military_grade_board']
    for item in order[:-1]:
        _lib.shift_click(ctx, _lib.menu_slot(17, _lib.find_slot(_lib.inventory(ctx), item)))
    _lib.shift_click(ctx, _lib.menu_slot(17, _lib.find_slot(_lib.inventory(ctx), order[-1])))
    t0 = ctx.server()['game_time']
    ctx.step('close')
    out = {}
    for t in (K_GASCENT[0] - 1, K_GASCENT[0], K_GASCENT[1] - 1, K_GASCENT[1]):
        _lib.advance_to(ctx, t0, t, 'assembler-gascent')
        d = _lib.block_data(ctx, a)
        out[t] = _lib.slot_count(d, 16, H + 'machine_gas_centrifuge')
    left = {s: (e['id'], e['count']) for s, e in _lib.items_of(d).items() if 4 <= s <= 15}
    want = {K_GASCENT[0] - 1: 0, K_GASCENT[0]: 1, K_GASCENT[1] - 1: 1, K_GASCENT[1]: 2}
    ctx.check(GC + '.build', out == want and not left, 'gas centrifuges in the output slot at ticks %s: %s (want %s); inputs left %s'
              % (sorted(out), [out[t] for t in sorted(out)], [want[t] for t in sorted(want)], left))
    _lib.open_gui(ctx, face, 'south', front(face), 'MachineAssemblyMachineScreen')
    _lib.shift_click(ctx, 16)
    ctx.step('close')
    S['gascent'] = _lib.count(ctx, H + 'machine_gas_centrifuge') >= 2


def sec_centrifuges(ctx):
    need('gascent', 'two gas centrifuges from the assembly machine')
    p = S['plant']
    g1, g2, g3 = (p[0] + 2, Y, p[2]), (p[0] + 2, Y, p[2] + 1), (p[0] + 6, Y, p[2])
    # GC1 from the north (the player looks south: facing north, so the block behind it is south, where GC2 goes); GC2 from the
    # east (facing east: behind it is the plant's corner, not a centrifuge)
    place_on_ground(ctx, H + 'machine_gas_centrifuge', g1[::2], [g1[0] + 0.5, Y, g1[2] - 3.5])
    place_on_ground(ctx, H + 'machine_gas_centrifuge', g2[::2], [g2[0] + 3.5, Y, g2[2] + 0.5])
    issue(ctx, 'centrifuge3')
    place_on_ground(ctx, H + 'machine_gas_centrifuge', g3[::2], [g3[0] + 0.5, Y, g3[2] + 3.5])
    d = ctx.step('dump', **{'from': [g1[0], Y, g1[2]], 'to': [g3[0], Y, g2[2]]})
    facing = {tuple(int(c) for c in b['pos']): b['props'].get('facing') for b in d['blocks'] if b['block'] == H + 'machine_gas_centrifuge'}
    if facing.get(g1) != 'north' or facing.get(g2) != 'east' or g3 not in facing:
        raise RuntimeError('gas centrifuges placed as %s, the layout needs GC1 north, GC2 east' % facing)
    S.update(gc1=g1, gc2=g2, gc3=g3)
    for g in (g1, g3):
        cmd(ctx, 'fill %d %d %d %d %d %d hbmsntm:red_cable' % (g[0], Y - 1, g[2], g[0], Y - 1, BUS_Z))
    charge(ctx, [g1, g2, g3, S['plant']], 'centrifuges')
    for g in (g1, g2, g3):                          # off the bus: from here on they only spend what they hold
        cmd(ctx, 'setblock %d %d %d minecraft:grass_block' % (g[0], Y - 1, g[2]))
    _lib.still(ctx)
    S['gc_start'] = {k: gc_read(ctx, S[k]) for k in ('gc1', 'gc2', 'gc3')}
    if any(v['power'] != GC_MAX for v in S['gc_start'].values()):
        raise RuntimeError('centrifuges not full after the charge: %s' % S['gc_start'])
    S['centrifuges'] = True


def sec_cascade(ctx):
    need('yellowcake', 'the yellowcake')
    need('centrifuges', 'the charged centrifuges')
    p = S['plant']
    issue(ctx, 'fluorite')
    open_plant(ctx)
    got = _lib.pick_recipe(ctx, p, 'hbmChemicalPlant.json', 'chem.uf6', 'chem.uf6')
    if got != 'chem.uf6':
        raise RuntimeError('plant recipe after the selector: %r' % got)
    _lib.server_steps(ctx, 2)
    _lib.shift_click(ctx, 13)                      # the emptied universal tank out, so the bucket can go there
    move(ctx, 7, 4)                                # the yellowcake from the output into the first input
    move(ctx, _lib.menu_slot(22, _lib.find_slot(_lib.inventory(ctx), H + 'fluorite', at_least=4)), 5)
    bucket = _lib.find_slot(_lib.inventory(ctx), 'minecraft:water_bucket')
    _lib.align(ctx, 10, (PHASE - K_UF6) % 10, 'align-uf6')
    move(ctx, _lib.menu_slot(22, bucket), 10)
    t0 = ctx.server()['game_time']
    ctx.step('close')
    u = t0 + K_UF6
    reads = {}
    for t in (K_UF6 - 1, K_UF6):
        _lib.advance_to(ctx, t0, t, 'plant-uf6')
        d = _lib.block_data(ctx, p)
        reads[t] = (plant_tanks(d).get('o0'), _lib.slot_count(d, 7, H + 'sulfur'))
    ok = reads == {K_UF6 - 1: (None, 0), K_UF6: ((UF6_MB, UF6_ID), 2)}
    ctx.check(CP + '.uf6', ok, '(output tank, sulfur) at tick %d: %s, at tick %d: %s (want none, 0 / (1200, %d), 2); game time of the '
              'UF6: %d (= %d mod 10)' % (K_UF6 - 1, reads[K_UF6 - 1], K_UF6, reads[K_UF6], UF6_ID, u, u % 10))
    if not ok:
        raise RuntimeError('no UF6 at the expected tick: %s' % reads)
    sim = cascade_sim(u)
    t1, f = sim['t1'] - u, sim['fuel_at'] - u

    _lib.advance_to(ctx, t0, K_UF6 + 1, 'cascade')
    a, o = gc_read(ctx, S['gc1']), plant_tanks(_lib.block_data(ctx, p)).get('o0')
    ok = (a['tank'] == 0 and a['inp'] == (UF6_MB, 'NUF6') and a['progress'] == 1 and a['power'] == GC_MAX - GC_HE and o is None)
    ctx.check(GC + '.uf6-transfer', ok, 'tick U+1 (game time %d): GC1 tank %s, input %s, progress %s, power %s; plant output tank %s'
              % (u + 1, a['tank'], a['inp'], a['progress'], a['power'], o))
    rd = {}
    for t in (GC_STEP, t1 - 1, t1):
        _lib.advance_to(ctx, t0, K_UF6 + t, 'cascade')
        rd[t] = (gc_read(ctx, S['gc1']), gc_read(ctx, S['gc2']))
    first, before, at = rd[GC_STEP][0], rd[t1 - 1], rd[t1]
    ok = (first['out'] == (300, 'LEUF6') and first['items'] == {'nugget_u238': 1} and u % 10 == PHASE and t1 == SIM_T1
          and before[0]['out'][0] == 300 and before[1]['inp'] == (0, 'LEUF6')
          and at[0]['out'][0] == 0 and at[1]['inp'] == (300, 'LEUF6') and at[1]['progress'] == 1)
    ctx.check(GC + '.align', ok, 'U = %d (mod 10 = %d); U+%d: GC1 output %s, items %s; U+%d: GC1 output %s, GC2 input %s; U+%d: GC1 output %s, '
              'GC2 input %s, progress %s' % (u, u % 10, GC_STEP, first['out'], first['items'], t1 - 1, before[0]['out'], before[1]['inp'],
                                            t1, at[0]['out'], at[1]['inp'], at[1]['progress']))
    rd = {}
    for t in (f - 1, f):
        _lib.advance_to(ctx, t0, K_UF6 + t, 'cascade')
        rd[t] = (gc_read(ctx, S['gc1']), gc_read(ctx, S['gc2']))
    g1, g2 = rd[f]
    total = Counter(g1['items']) + Counter(g2['items'])
    ok = (f == SIM_F and rd[f - 1][1]['items'].get('nugget_uranium_fuel', 0) == 0 and rd[f - 1][1]['out'][0] == TAIL_MB
          and g2['items'].get('nugget_uranium_fuel') == TAIL_FUEL and g2['out'][0] == 0
          and dict(total) == {'nugget_u238': 6, 'nugget_uranium_fuel': 6, 'fluorite': 4})
    ctx.check(GC + '.fuel', ok, 'U+%d: GC2 items %s, output %s; U+%d: GC1 items %s, GC2 items %s, output %s; cascade total %s (want 6 U-238, '
              '6 fuel, 4 fluorite)' % (f - 1, rd[f - 1][1]['items'], rd[f - 1][1]['out'], f, g1['items'], g2['items'], g2['out'], dict(total)))
    want = GC_MAX - GC_HE * SIM_WORK[0]
    ctx.check(GC + '.power', g1['power'] == want and g2['power'] == GC_MAX - GC_HE * SIM_WORK[1],
              'GC1 power %s, GC2 power %s at U+%d (want %d each: %d working ticks x %d HE from %d)'
              % (g1['power'], g2['power'], f, want, SIM_WORK[0], GC_HE, GC_MAX))
    # the products into the inventory, the fuel billet on the crafting table
    for k in ('gc1', 'gc2'):
        open_gc(ctx, k)
        for s in range(4):
            _lib.shift_click(ctx, s)
        ctx.step('close')
    _lib.open_gui(ctx, CT, 'south', front(CT), 'Crafting')
    before = _lib.count(ctx, H + 'billet_uranium_fuel')
    _lib.craft(ctx, ['nnn', 'nnn'], dict(n=H + 'nugget_uranium_fuel'))
    ctx.step('close')
    items = _lib.inventory(ctx)
    made, left = _lib.count(ctx, H + 'billet_uranium_fuel', items=items) - before, _lib.count(ctx, H + 'nugget_uranium_fuel', items=items)
    ctx.check(GC + '.fuel-billet', made == 1 and left == 0, 'uranium fuel billets +%d (want 1), fuel nuggets left %d' % (made, left))
    S['u238'] = _lib.count(ctx, H + 'nugget_u238', items=items) >= 6


def sec_crucible(ctx):
    need('u238', 'the six U-238 nuggets of the cascade')
    stock(ctx, 'crucible')
    issue(ctx, 'anvil')
    # the iron anvil (placed from the south: faces south) and the ingot mold: 1 steel ingot (kept) + mold base
    place_on_ground(ctx, H + 'anvil', A1[::2], front(A1, 3.5), meta=0)
    hud = _lib.open_gui(ctx, A1, 'south', front(A1), 'Anvil', offset=_lib.ANVIL_AIM)
    _lib.put_n(ctx, 3, H + 'ingot_steel', [0], k=1)
    _lib.put_stack(ctx, 3, H + 'mold_base', 1)
    _lib.click(ctx, 2, after=4)
    _lib.click(ctx, _lib.menu_slot(3, _lib.free_slots(_lib.inventory(ctx))[0]))
    _lib.shift_click(ctx, 0)
    ctx.step('close')
    S['mold'] = _lib.count(ctx, H + 'mold_ingot') == 1
    if not S['mold']:
        raise RuntimeError('no ingot mold from the anvil (hud %s)' % hud.get('screen'))
    # firebox, crucible on it (facing south: the recipe spout is south), coal; the foundry mold under the spout comes last, it
    # stands in front of the firebox
    stand = [FIRE_AT[0] + 0.5, Y, FIRE_AT[1] + 3.5]
    place_on_ground(ctx, H + 'heater_firebox', FIRE_AT, stand)
    _lib.place(ctx, H + 'machine_crucible', (FIRE_AT[0], Y, FIRE_AT[1]), 'up', stand, crouch=True)
    c, props = _lib.core_of(ctx, H + 'machine_crucible', (FIRE_AT[0] - 3, Y + 1, FIRE_AT[1] - 3), (FIRE_AT[0] + 3, Y + 2, FIRE_AT[1] + 3))
    f = core_near(ctx, H + 'heater_firebox', *FIRE_AT, up=0)
    if props.get('facing') != 'south':
        raise RuntimeError('crucible facing %s, the layout needs south' % props.get('facing'))
    _lib.open_gui(ctx, (f[0], Y, f[2] + 1), 'south', [f[0] + 0.5, Y, f[2] + 3.5], 'Firebox')
    _lib.put_stack(ctx, 2, 'minecraft:coal', 0)
    ctx.step('close')
    # recipe, then 2 steel ingots and the 6 U-238 nuggets (one item a slot), from the north side
    cpos, cstand = (c[0], c[1], c[2] - 1), [c[0] + 0.5, Y, c[2] - 3.5]
    hud = _lib.open_gui(ctx, cpos, 'north', cstand, 'Crucible', offset=[0, -0.25, 0])
    try:
        idx, n = _lib.recipe_index('hbmCrucible.json', 'crucible.ferro', ctx.default)
    except FileNotFoundError:
        idx, n = 5, None                           # CrucibleRecipes.java:50-71 register order: steel, hematite, malachite, redcopper, hss, ferro
    if idx is None:
        raise RuntimeError('crucible.ferro is not in the selector list (%d entries)' % n)
    ctx.step('click', at=[hud['gui_left'] + 16 + 9, hud['gui_top'] + 35 + 9], button=0, after=4)
    ctx.step('screen', expect='RecipeSelector')
    sel = ctx.step('hud', frames=2)
    sl, stp = (sel['gui_scaled_width'] - 176) // 2, (sel['gui_scaled_height'] - 132) // 2
    ctx.step('click', at=[sl + 7 + 18 * (idx % 8) + 9, stp + 17 + 18 * (idx // 8) + 9], button=0, after=3)
    ctx.step('click', at=[sl + 152 + 8, stp + 90 + 8], button=0, after=4)   # close: sends the selection
    ctx.step('screen', expect='Crucible')
    _lib.put_n(ctx, 9, H + 'ingot_steel', [0, 1])
    _lib.put_n(ctx, 9, H + 'nugget_u238', [2, 3, 4, 5, 6, 7])
    ctx.step('close')
    cd = _lib.block_data(ctx, c)
    loaded = sorted(e['id'].split(':')[1] for e in _lib.items_of(cd).values())
    if cd.get('recipe') != 'crucible.ferro':
        raise RuntimeError('crucible recipe %r after the selector' % cd.get('recipe'))
    mold = (c[0], Y, c[2] + 2)                     # the spout: core + 1.875 in the facing (MachineCrucibleBlockEntity.java:155-166)
    mstand = [mold[0] + 0.5, Y, mold[2] + 3.5]
    place_on_ground(ctx, H + 'foundry_mold', mold[::2], mstand)
    _lib.hold(ctx, H + 'mold_ingot')
    _lib.use_on(ctx, mold, 'south', mstand, offset=[0, -0.25, 0])
    if _lib.items_of(_lib.block_data(ctx, mold)).get(0, {}).get('id') != H + 'mold_ingot':
        raise RuntimeError('the foundry mold does not hold the ingot mold')
    S.update(crucible=c, firebox=f, foundry=mold)
    casts = []
    for k in range(2):
        ctx.sprint(30000, until=lambda cc: bool(_lib.items_of(_lib.block_data(cc, mold)).get(1)), poll_s=0.5, label='crucible-ferro-%d' % k,
                   timeout_s=600)
        ctx.server('tick freeze')
        before = _lib.count(ctx, H + 'ingot_ferrouranium')
        _lib.empty_hand(ctx)
        _lib.use_on(ctx, mold, 'south', mstand, offset=[0, -0.25, 0])
        casts.append(_lib.count(ctx, H + 'ingot_ferrouranium') - before)
    _lib.advance(ctx, 40, 'crucible-settle')
    cd = _lib.block_data(ctx, c)
    rec, was = stack_list(cd.get('rec', [])), stack_list(cd.get('was', []))
    steel_left = 2 * INGOT_Q - 6 * FERRO_RUN[0]
    ok = (loaded == sorted(['ingot_steel'] * 2 + ['nugget_u238'] * 6) and casts == [1, 1] and rec == {MAT_STEEL: steel_left}
          and not was and not _lib.items_of(cd))
    ctx.check(CA + '.ferro', ok, 'loaded %s; ferrouranium ingots taken per cast %s (want [1, 1]); crucible recipe stack %s (want {%d: %d}), '
              'waste %s, slots %s' % (loaded, casts, rec, MAT_STEEL, steel_left, was, _lib.items_of(cd)))
    S['ferro'] = _lib.count(ctx, H + 'ingot_ferrouranium') == 2


def sec_anvil(ctx):
    need('ferro', 'two ferrouranium ingots from the crucible')
    # 预写: the other 8 ferrouranium ingots (see PREWRITTEN)
    cmd(ctx, 'give @s %s %d' % (H + 'ingot_ferrouranium', FERRO_PREWRITTEN))
    give(ctx, *VANILLA['anvil'])
    hud = _lib.open_gui(ctx, A1, 'south', front(A1), 'Anvil', offset=_lib.ANVIL_AIM)
    _lib.put_n(ctx, 3, H + 'anvil', [0], k=1, meta=0)
    _lib.put_stack(ctx, 3, H + 'ingot_ferrouranium', 1)
    _lib.click(ctx, 2, after=4)
    _lib.click(ctx, _lib.menu_slot(3, _lib.free_slots(_lib.inventory(ctx))[0]))
    ctx.step('close')
    items = _lib.inventory(ctx)
    tier4, ferro = _lib.count(ctx, H + 'anvil', 4, items=items), _lib.count(ctx, H + 'ingot_ferrouranium', items=items)
    ctx.check(GC + '.tier4-anvil', tier4 == 1 and ferro == 0, '预写 8 of the 10 ferrouranium ingots; anvils of meta 4 in the inventory %d '
              '(want 1), ferrouranium ingots left %d (want 0)' % (tier4, ferro))
    if tier4 != 1:
        raise RuntimeError('no tier-4 anvil')
    place_on_ground(ctx, H + 'anvil', A4[::2], front(A4, 3.5), meta=4)
    if not _lib.is_block(ctx, A4, H + 'anvil[subtype=4]'):
        raise RuntimeError('the placed anvil is not the ferrouranium one')
    rec4, rec3 = _lib.anvil_recipes(ctx, 4), _lib.anvil_recipes(ctx, 3)
    in3 = _lib.anvil_position(rec3, H + 'wire_gold', 'minecraft:gold_ingot')
    want = ctx.step('i18n', keys=['item.hbmsntm.wire_gold'])['texts']['item.hbmsntm.wire_gold']
    before = (_lib.count(ctx, H + 'wire_gold'), _lib.count(ctx, 'minecraft:gold_ingot'))
    hud = _lib.open_gui(ctx, A4, 'south', front(A4), 'Anvil', offset=_lib.ANVIL_AIM)
    try:
        r = _lib.anvil_construct(ctx, hud, rec4, H + 'wire_gold', 'minecraft:gold_ingot', times=4, state={}, want=want)
    finally:
        ctx.step('close')
    after = (_lib.count(ctx, H + 'wire_gold'), _lib.count(ctx, 'minecraft:gold_ingot'))
    ok = r['named'] and in3 is None and after[0] - before[0] == 32 and before[1] - after[1] == 4
    ctx.check(GC + '.tier4-wire', ok, 'tier-4 list position %d of %d (page %d, cell %d, tooltip %s); in the tier-3 list: %s; gold wire %d -> %d, '
              'gold ingots %d -> %d' % (r['position'], r['total'], r['page'], r['cell'], r['tooltip'][:1], in3, before[0], after[0],
                                        before[1], after[1]))
    stock(ctx, 'upgrade')
    _lib.open_gui(ctx, CT, 'south', front(CT), 'Crafting')
    _lib.craft(ctx, ['AAA', 'ABA', 'AAA'], dict(A=H + 'wire_gold', B='minecraft:iron_ingot'), times=4)
    coils = _lib.count(ctx, H + 'coil_gold')
    _lib.craft(ctx, ['GNG', 'RUR', 'GMG'], dict(G=H + 'coil_gold', N=H + 'ingot_niobium', R=H + 'ingot_rubber', U=H + 'upgrade_template',
                                                M=H + 'motor'))
    ctx.step('close')
    items = _lib.inventory(ctx)
    up = _lib.count(ctx, H + 'upgrade_gc_speed', items=items)
    ctx.check(GC + '.upgrade-craft', coils == 4 and up == 1 and _lib.count(ctx, H + 'coil_gold', items=items) == 0,
              'gold coils made %d (want 4); overclocking upgrades %d (want 1), coils left %d' % (coils, up, _lib.count(ctx, H + 'coil_gold', items=items)))
    S['upgrade'] = up == 1


def sec_high_speed(ctx):
    need('upgrade', 'the overclocking upgrade')
    need('centrifuges', 'the charged third centrifuge')
    g3 = S['gc3']
    # 预写: 300 mB HEUF6 in the third centrifuge (see PREWRITTEN)
    cmd(ctx, 'data merge block %d %d %d {inputTank:300,inputTank_type:"HEUF6",outputTank:0,outputTank_type:"NONE"}' % g3)
    a = gc_read(ctx, g3)
    _lib.advance(ctx, 160, 'gc3-no-upgrade')
    b = gc_read(ctx, g3)
    idle = (a['inp'] == (300, 'HEUF6') and b['inp'] == (300, 'HEUF6') and b['progress'] == 0 and b['power'] == a['power'] and not b['items'])
    open_gc(ctx, 'gc3')
    move(ctx, _lib.menu_slot(7, _lib.find_slot(_lib.inventory(ctx), H + 'upgrade_gc_speed')), 6)
    t0 = ctx.server()['game_time']
    ctx.step('close')
    rd = {}
    for t in (GC_STEP_FAST - 1, GC_STEP_FAST):
        _lib.advance_to(ctx, t0, t, 'gc3-upgrade')
        rd[t] = gc_read(ctx, g3)
    c, e = rd[GC_STEP_FAST - 1], rd[GC_STEP_FAST]
    ok = (idle and not c['items'] and c['progress'] == GC_STEP_FAST - 1
          and e['items'] == {'nugget_u238': 2, 'nugget_u235': 1, 'fluorite': 1} and e['inp'][0] == 0
          and b['power'] - e['power'] == GC_HE_FAST * GC_STEP_FAST)
    ctx.check(GC + '.high-speed', ok, '预写 HEUF6 300 mB; without the upgrade, 160 ticks: input %s -> %s, progress %s, power %s -> %s, items %s; '
              'with it: tick %d progress %s items %s; tick %d items %s, input %s, power %s (spent %d, want %d)'
              % (a['inp'], b['inp'], b['progress'], a['power'], b['power'], b['items'], GC_STEP_FAST - 1, c['progress'], c['items'],
                 GC_STEP_FAST, e['items'], e['inp'], e['power'], b['power'] - e['power'], GC_HE_FAST * GC_STEP_FAST))


# ---------------------------------------------------------------- leaving and opening the world

def readings(ctx):
    """Flat readings per group: stored quantities and settings of the three centrifuges, the plant and the crucible."""
    out = {GC: {}, CP: {}, CA: {}}
    for k in ('gc1', 'gc2', 'gc3'):
        if k in S:
            d = _lib.block_data(ctx, S[k])
            out[GC]['%s.power' % k] = d.get('power')
            for n, v in _lib.tanks(d).items():
                out[GC]['%s.%s' % (k, n)] = v['fill']
                out[GC]['%s.%s_type' % (k, n)] = v['type']
            out[GC]['%s.items' % k] = sorted((s, e['id'], e['count']) for s, e in _lib.items_of(d).items())
    if 'plant' in S:
        d = _lib.block_data(ctx, S['plant'])
        out[CP]['plant.power'] = d.get('power')
        out[CP]['plant.recipe0'] = d.get('recipe0')
        for n, v in _lib.tanks(d).items():
            out[CP]['plant.%s' % n] = v['fill']
            out[CP]['plant.%s_type' % n] = v['type']
        out[CP]['plant.items'] = sorted((s, e['id'], e['count'], e['meta']) for s, e in _lib.items_of(d).items())
    if 'crucible' in S:
        d = _lib.block_data(ctx, S['crucible'])
        out[CA]['crucible.recipe'] = d.get('recipe')
        out[CA]['crucible.rec'] = sorted(stack_list(d.get('rec', [])).items())
        out[CA]['crucible.was'] = sorted(stack_list(d.get('was', [])).items())
        out[CA]['crucible.items'] = sorted((s, e['id'], e['count']) for s, e in _lib.items_of(d).items())
    return out


def sec_reload(ctx):
    ids = {GC: GC + '.reload', CP: CP + '.reload', CA: CA + '.reload'}
    _lib.still(ctx)
    first = readings(ctx)
    _lib.advance(ctx, 40, 'before-reload')
    _lib.still(ctx)
    second = readings(ctx)
    p = S.get('plant') or (OX, Y, OZ)
    _lib.reopen(ctx, near=(p[0], Y, p[2] + 4))
    after = readings(ctx)
    for g, eid in ids.items():
        if not first[g]:
            ctx.not_run(eid, 'the section that builds this group did not finish, nothing to compare')
            continue
        same, moved = _lib.static_readings(first[g], second[g])
        r = _lib.compare_static(same, after[g], not_quantity=('plant.recipe0', 'crucible.recipe'))
        ctx.check(eid, r['ok'], '%s; moved between the two reads before leaving (not compared): %s' % (r['detail'], moved or 'none'))


# ---------------------------------------------------------------- the line

def run(ctx):
    _lib.setup_world(ctx)
    cmd(ctx, 'clear @s', allow_error=True)
    cmd(ctx, 'gamemode survival')
    _lib.go_near(ctx, OX, Y, OZ + 4)
    corners = [(x, z) for x in (OX - 14, OX + 22) for z in (OZ - 8, OZ + 18)]
    for _ in range(60):
        if all(ctx.server('execute if loaded %d %d %d' % (x, Y, z), allow_error=True)['result'] == 1 for x, z in corners):
            break
        ctx.step('wait', ticks=10)
    else:
        raise RuntimeError('the chunks of the line did not load: %s' % corners)
    cmd(ctx, 'fill %d %d %d %d %d %d minecraft:air' % (OX - 14, Y, OZ - 8, OX + 22, Y + 8, OZ + 18), allow_error=True)
    cmd(ctx, 'fill %d %d %d %d %d %d minecraft:grass_block' % (OX - 14, Y - 1, OZ - 8, OX + 22, Y - 1, OZ + 18), allow_error=True)
    ctx.step('view', pos=[OX + 0.5, Y, OZ + 8.5], yaw=180.0, pitch=20.0, fly=False, hide_gui=False)
    ctx.step('wait', ticks=20)

    sections = [
        (sec_smelt, [GC + '.smelt', GC + '.billets'], 'furnace and billets'),
        (sec_plant, [CP + '.peroxide', CP + '.yellowcake'], 'chemical plant (peroxide, yellowcake)'),
        (sec_assembly, [GC + '.build'], 'assembly of the gas centrifuges'),
        (sec_centrifuges, [GC + '.uf6-transfer', GC + '.align', GC + '.fuel', GC + '.power', GC + '.fuel-billet', CP + '.uf6'],
         'placing and charging the gas centrifuges'),
        (sec_cascade, [CP + '.uf6', GC + '.uf6-transfer', GC + '.align', GC + '.fuel', GC + '.power', GC + '.fuel-billet'], 'UF6 and the cascade'),
        (sec_crucible, [CA + '.ferro'], 'crucible and ferrouranium'),
        (sec_anvil, [GC + '.tier4-anvil', GC + '.tier4-wire', GC + '.upgrade-craft'], 'tier-4 anvil and the upgrade'),
        (sec_high_speed, [GC + '.high-speed'], 'the high-enrichment step'),
    ]
    for body, rows, name in sections:
        _lib.section(ctx, rows, lambda b=body: b(ctx), 'section %s stopped' % name)
    _lib.section(ctx, [GC + '.reload', CP + '.reload', CA + '.reload'], lambda: sec_reload(ctx), 'leaving and opening the world')

    handover = dict(HANDOVER)
    stray = sorted({i for i, _ in GIVEN if i.startswith(H) and i not in handover})
    outside_on_list = sorted({i for i, _, _ in ISSUED if i in handover})
    ctx.check(GC + '.start-items', not stray and not outside_on_list,
              'from the stage-7 list (%d items): %s; vanilla: %s; outside the list: %s; 预写 states: %d (PREWRITTEN); given as list items '
              'but not on it: %s; issued as outside the list but on it: %s' % (
                  len(HANDOVER), sorted('%s x%d' % (i.split(':')[1], n) for i, n in GIVEN if i in handover),
                  sorted('%s x%d' % (i.split(':')[1], n) for i, n in GIVEN if i.startswith('minecraft:')),
                  ['%s x%d (%s)' % (i.split(':')[1], n, w) for i, n, w in ISSUED], len(PREWRITTEN), stray or 'none',
                  outside_on_list or 'none'))
