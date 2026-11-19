"""Main line, stage 10 (spent fuel and reprocessing): a ZIRNOX burns natural uranium rods for real under /tick sprint, the
depleted rods are taken apart into hot waste at the crafting table, the waste cools in a spent fuel pool drum, a PUREX
reprocesses cold waste on power from an RTG generator, an RBMK rod is taken apart into pellets, and schrabidium nuggets are
made into the three schrabidium RBMK rods.

The player is in creative mode: the rods, the waste and the plutonium pellets are radioactive, and a survival player
carrying them through the long sprints would be killed (creative players take no radiation, ContaminationUtil.java:56,179;
original ContaminationUtil.java:93,284); the protection itself is the next stage's subject. Items are issued by command into
main-inventory slots (HANDOVER below is the stage-10 start list; ISSUED lists what is issued besides, with the reason).
Machines are put into the hand by command and placed with a real right-click; screens are opened by real right-clicks and
loaded by real slot clicks; the PUREX recipe is chosen in the recipe selector by clicks.

Site (flat world, feet at Y = -60), all frozen except the measured windows:
- ZIRNOX core ZX (clicked from the south: facing south). Slots 24/25 hold infinite fluid barrels for CO2 and water (预写);
  a steel barrel with an infinite barrel in its drain slot sits on the steam port (core + 3 x clockwise(facing), 1 up,
  ReactorZirnoxBlockEntity.java:425-441) and swallows the superhot steam, so the reactor always cools by pressure.
- crafting table TABLE.
- spent fuel pool: the drum DRUM in a 3 x 3 x 3 pool of water inside a stone shell, water on all six faces.
- PUREX core PX; the RTG generator RTG six blocks east of it; red cables PX + 3 .. PX + 5 (the PUREX port at core + 3,
  MachinePUREXBlockEntity.java:217-243) join them for the charging window and are cut before the PUREX runs.

Expected values are derived from the code (NEO file:line, and the 1.7.10 original's file:line where NEO ports it);
readings are server data (`data get block` / `data get entity`). After the line the world is left and opened again and
each feature group's static, non-default readings are compared (the pool holds only cooled waste, the PUREX has no input,
the RTG is at its power cap).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='spent-fuel.mainline_stage10',
    feature='spent-fuel',
    features=['spent-fuel', 'purex-reprocessing', 'rtg-power', 'rbmk-fuel', 'rbmk-recycling'],
    title='Main line stage 10: ZIRNOX burn-up, hot waste, spent fuel pool, PUREX on RTG power, RBMK pellets and schrabidium rods',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

# The stage-10 start list (items obtainable before stage 10; "block:" rows are world-generation blocks).
HANDOVER = [
    'block:hbmsntm:ore_oil', 'hbmsntm:arc_electrode_graphite', 'hbmsntm:ball_fireclay', 'hbmsntm:billet_plutonium_fuel',
    'hbmsntm:billet_pu_mix', 'hbmsntm:billet_th232', 'hbmsntm:billet_u233', 'hbmsntm:billet_u238',
    'hbmsntm:billet_uranium', 'hbmsntm:billet_uranium_fuel', 'hbmsntm:billet_zirconium', 'hbmsntm:centrifuge_element',
    'hbmsntm:cinnabar', 'hbmsntm:circuit_analog_board', 'hbmsntm:circuit_capacitor', 'hbmsntm:circuit_integrated_board',
    'hbmsntm:circuit_printed_board', 'hbmsntm:circuit_vacuum_tube', 'hbmsntm:coil_copper', 'hbmsntm:coil_copper_ring',
    'hbmsntm:coil_tungsten', 'hbmsntm:concrete_asbestos', 'hbmsntm:concrete_smooth', 'hbmsntm:drill_titanium',
    'hbmsntm:fluorite', 'hbmsntm:furnace_combination', 'hbmsntm:heat_boiler', 'hbmsntm:heater_firebox',
    'hbmsntm:ingot_aluminium', 'hbmsntm:ingot_beryllium', 'hbmsntm:ingot_boron', 'hbmsntm:ingot_copper',
    'hbmsntm:ingot_desh', 'hbmsntm:ingot_firebrick', 'hbmsntm:ingot_graphite', 'hbmsntm:ingot_lead',
    'hbmsntm:ingot_niobium', 'hbmsntm:ingot_polymer', 'hbmsntm:ingot_raw@41', 'hbmsntm:ingot_red_copper',
    'hbmsntm:ingot_rubber', 'hbmsntm:ingot_steel', 'hbmsntm:ingot_th232', 'hbmsntm:ingot_titanium',
    'hbmsntm:ingot_tungsten', 'hbmsntm:ingot_uranium', 'hbmsntm:ingot_zirconium', 'hbmsntm:machine_arc_welder',
    'hbmsntm:machine_assembly_machine', 'hbmsntm:machine_blast_furnace', 'hbmsntm:machine_catalytic_cracker',
    'hbmsntm:machine_centrifuge', 'hbmsntm:machine_chemical_plant', 'hbmsntm:machine_crucible',
    'hbmsntm:machine_fraction_tower', 'hbmsntm:machine_press', 'hbmsntm:machine_refinery', 'hbmsntm:machine_shredder',
    'hbmsntm:machine_soldering_station', 'hbmsntm:machine_waste_drum', 'hbmsntm:machine_well', 'hbmsntm:machine_zirnox',
    'hbmsntm:mold_base', 'hbmsntm:motor', 'hbmsntm:motor_desh', 'hbmsntm:niter', 'hbmsntm:nugget_beryllium',
    'hbmsntm:nugget_u235', 'hbmsntm:nugget_u238', 'hbmsntm:nugget_uranium', 'hbmsntm:nugget_zirconium',
    'hbmsntm:ore_beryllium', 'hbmsntm:ore_cobalt', 'hbmsntm:ore_gneiss_uranium', 'hbmsntm:ore_lead_deepslate',
    'hbmsntm:ore_thorium', 'hbmsntm:ore_titanium_deepslate', 'hbmsntm:ore_uranium_deepslate', 'hbmsntm:pipe_copper',
    'hbmsntm:pipe_rubber', 'hbmsntm:pipe_steel', 'hbmsntm:plate_cast@0', 'hbmsntm:plate_cast@11',
    'hbmsntm:plate_cast@12', 'hbmsntm:plate_cast@5', 'hbmsntm:plate_cast@8', 'hbmsntm:plate_copper',
    'hbmsntm:plate_dura_steel', 'hbmsntm:plate_iron', 'hbmsntm:plate_lead', 'hbmsntm:plate_polymer',
    'hbmsntm:plate_steel', 'hbmsntm:plate_titanium', 'hbmsntm:powder_aluminium', 'hbmsntm:powder_coal',
    'hbmsntm:powder_desh_mix', 'hbmsntm:rbmk_blank', 'hbmsntm:rbmk_fuel_empty', 'hbmsntm:rbmk_rod',
    'hbmsntm:resource_limestone', 'hbmsntm:rod_empty', 'hbmsntm:rod_quad_empty', 'hbmsntm:rod_zirnox@0',
    'hbmsntm:rod_zirnox@2', 'hbmsntm:rod_zirnox@3', 'hbmsntm:rod_zirnox@5', 'hbmsntm:rod_zirnox@6',
    'hbmsntm:rod_zirnox_empty', 'hbmsntm:rod_zirnox_natural_uranium_fuel_depleted',
    'hbmsntm:rod_zirnox_plutonium_fuel_depleted', 'hbmsntm:rod_zirnox_thorium_fuel_depleted',
    'hbmsntm:rod_zirnox_u233_fuel_depleted', 'hbmsntm:shell_steel', 'hbmsntm:stamp_stone_flat', 'hbmsntm:steel_grate',
    'hbmsntm:steel_scaffold', 'hbmsntm:sulfur', 'hbmsntm:transformer', 'hbmsntm:waste_natural_uranium@0',
    'hbmsntm:waste_natural_uranium@1', 'hbmsntm:waste_plutonium@0', 'hbmsntm:waste_plutonium@1',
    'hbmsntm:waste_thorium@0', 'hbmsntm:waste_thorium@1', 'hbmsntm:waste_u233@0', 'hbmsntm:waste_u233@1',
    'hbmsntm:wire_copper', 'hbmsntm:wire_gold', 'hbmsntm:wire_lead', 'hbmsntm:wire_red_copper', 'hbmsntm:wire_tungsten',
]
H = 'hbmsntm:'
ROD = H + 'rod_zirnox'                                   # meta 0 = NATURAL_URANIUM_FUEL (ZirnoxRodItem.java:81)
DEPLETED = H + 'rod_zirnox_natural_uranium_fuel_depleted'
WASTE = H + 'waste_natural_uranium'                      # meta 1 hot, 0 cold (DepletedFuelItem.java:21-22)
# from the start list, with the amounts the line uses
GIVE = [(H + 'machine_zirnox', 1), (ROD, 24), (H + 'machine_waste_drum', 1), (H + 'plate_iron', 2), (H + 'billet_uranium', 8),
        (H + 'rbmk_fuel_empty', 4), (H + 'nugget_beryllium', 52)]
# given besides, with the reason (not 预写 unless marked):
ISSUED = [
    (H + 'nugget_pu238', 36, 'obtainable from stage 7: plutonium powder (obtainable from stage 4: shredded plutonium ingot or crystal, '
                             'ShredderRecipes.java:251,306) + 3 fluorite + 1,000 mB water in the chemical plant (from stage 4, recipe chem.puf6, '
                             'ChemicalPlantRecipes.java:298-301) give PUF6, and the gas centrifuge on PUF6 gives plutonium-238 nuggets '
                             '(GasCentrifugeRecipes.java:81,87,94); not on the start list because no checkpoint item before stage 10 needs it'),
    (H + 'machine_purex', 1, 'obtainable from stage 5: the assembly machine makes it (AssemblyMachineRecipes.java:368); handed out (命令搭建)'),
    (H + 'machine_rtg', 1, 'obtainable from stage 5: the assembly machine makes it (AssemblyMachineRecipes.java:347); handed out (命令搭建)'),
    ('minecraft:crafting_table', 1, 'vanilla'),
    (H + 'nugget_schrabidium', 52, '预写: schrabidium only comes from uranium ore scorched by a meltdown, 1 in 250 per ore block '
                                   '(ExplosionNukeGeneric.java:150-151,248-274, ReactorZirnoxBlockEntity.java:415; original '
                                   'ExplosionNukeGeneric.java:306-330, TileEntityReactorZirnox.java:417)'),
    (H + 'nugget_neptunium', 52, '预写: neptunium first comes from this stage\'s PUREX (cold U-233 / U-235 waste, PUREXRecipes.java:94-110), '
                                 'one nugget per run; 52 runs are beyond this line, and no earlier stage yields it'),
]

Y = -60
X0, Z0 = 4000, 4000
ZX = (X0, Y, Z0)                       # ZIRNOX core: the cell clicked is ZX + 2 south, the core goes 2 further (ReactorZirnoxBlock.java:41-42)
TABLE = (X0 - 8, Y, Z0 + 10)
DRUM = (X0 + 10, Y + 1, Z0 + 10)       # in a pool: shell x/z +-2, y Y-1..Y+2; water x/z +-1, y Y..Y+2
PX = (X0 + 12, Y, Z0 - 12)             # PUREX core (MachinePUREXBlock.java:58-59)
MID = [X0 + 4.5, Y, Z0 + 5.5]          # where the player waits during sprints (everything within 20 blocks)

# ---- numbers from the code
NEIGHBOURS = {0: (1, 7), 1: (0, 2, 8), 2: (1, 9), 3: (4, 10), 4: (3, 5, 11), 5: (4, 6, 12), 6: (5, 13), 7: (0, 8, 14),
              8: (1, 7, 9, 15), 9: (2, 8, 16), 10: (3, 11, 17), 11: (4, 10, 12, 18), 12: (5, 11, 13, 19), 13: (6, 12, 20),
              14: (7, 15, 21), 15: (8, 14, 16, 22), 16: (9, 15, 23), 17: (10, 18), 18: (11, 17, 19), 19: (12, 18, 20),
              20: (13, 19), 21: (14, 22), 22: (15, 21, 23), 23: (16, 22)}   # ReactorZirnoxBlockEntity.java:108-138; original TileEntityReactorZirnox.java:161-190
ROD_LIFE = 250_000                     # ZirnoxRodItem.java:81; original ItemZirnoxRod.java:102
MELTDOWN = 100_000                     # ReactorZirnoxBlockEntity.java:51,54,338-340
TAKE = [8, 11, 12, 15, 1, 4, 5]        # depleted rods taken out (7 rods -> 14 hot waste: 12 for the pool, 2 for the PUREX check)
POOL_SLOTS = 12                        # MachineWasteDrumBlockEntity.java:30; original TileEntityWasteDrum (12 slots)
DECAY_TICKS = 72_000                   # MachineWasteDrumBlockEntity.java:32,54; original TileEntityWasteDrum.java:206
WATER_FACES = 6
POOL_TICKS = 60_000
ALPHA = 1e-9
RTG_TICKS = 500
PELLET_HEAT = 10                       # NtmItems.java:538; original ModItems.java:2655
PELLET_LIFE = int(int(_lib.f32(_lib.f32(48000 * 100) * _lib.f32(87.7))) * 1.5)   # RTGUtil.java:76-91 MEDIUM; original RTGUtil.java:54-69
RTG_MAX = 100_000                      # MachineRTGBlockEntity.java:30; original TileEntityMachineRTG.java:30
CHARGE_TICKS = 2000
PUREX_TICKS, PUREX_POWER = 100, 1_000  # PUREXRecipes.java:46,50; original PUREXRecipes.java:38,91
KEROSENE, NITRIC = 22, 82              # FluidType ids in declaration order (Fluids.java:272,332); the tanks save the id (FluidTank.java:255-258)
KERO_FILL, ACID_FILL = 1000, 500       # 预写: two batches' worth, one batch is used
PUREX_OUT = [(7, H + 'nugget_u238', 1), (8, H + 'nugget_pu_mix', 2), (9, H + 'nugget_pu239', 1), (10, H + 'nuclear_waste_tiny', 2)]
FINAL_TICKS = 1100                     # brings the RTG from whatever it kept to its cap (100 HE/t x 1,000 ticks) before the reload
ROD_YIELD = 100_000_000                # NtmItems.java:785; original ModItems.java:3083-3084
PREWRITTEN_YIELD = 50_000_000          # 预写: half burnt

SF, PX_, RT, RF, RR = 'spent-fuel', 'purex-reprocessing', 'rtg-power', 'rbmk-fuel', 'rbmk-recycling'


def depletion(limit):
    """ReactorZirnoxBlockEntity.decay in its own order for a full core of natural uranium rods: slots 0..23 each tick, a rod
    decays (fuel neighbours + 1) times, one life point each, and is replaced once its life passes 250,000 (the loop breaks
    there); a rod replaced earlier in the tick no longer counts as a neighbour. Returns ({slot: tick it depleted}, life by tick
    requested in `at`)."""
    life, fuel, dep = [0] * 24, [True] * 24, {}
    for t in range(1, limit + 1):
        for i in range(24):
            if not fuel[i]:
                continue
            d = 1 + sum(1 for n in NEIGHBOURS[i] if fuel[n])
            room = ROD_LIFE + 1 - life[i]
            if d >= room:
                life[i] += room
                fuel[i] = False
                dep[i] = t
            else:
                life[i] += d
    return dep, life


def p_cooled(ticks):
    return 1 - (1 - 1 / (DECAY_TICKS // WATER_FACES)) ** ticks


POOL_MIN = _lib.binomial_lower(POOL_SLOTS, p_cooled(POOL_TICKS), ALPHA)

E = [
    (SF, 'start-items', '发放的起点物品都在阶段 10 的交接清单上；清单外发放的（钚-238 粒、PUREX 与 RTG 发电机两台机器、工作台、预写的施拉比粒与镎粒）'
                        '在本文件 ISSUED 里逐件写明来源',
     'stage-10 start list (in this file)'),
    (SF, 'burnup', 'ZIRNOX 装满 24 根天然铀棒（每根寿命 250,000，每刻衰变“燃料邻居数 + 1”次，寿命超过 250,000 换成乏棒），开机后按反应堆自己的'
                   '槽序逐刻模拟：第 50,000 刻没有乏棒；第 50,001 刻正好 8、11、12、15 四槽是乏棒；第 66,667 刻再加 1、4、5、7、9、10、13、14、18、22；'
                   '第 66,668 刻再加 16、19，其余 8 根的寿命与模拟相同；全程热与压力低于 100,000、反应堆完好。燃烧照冲刺真实跑完；'
                   '预写：CO2 与水由命令放进 24、25 槽的无限流体桶供给，蒸汽由命令放的钢桶排掉',
     'ReactorZirnoxBlockEntity.java:108-138,167-179,320-336,338-340, ZirnoxRodItem.java:81; '
     'TileEntityReactorZirnox.java:161-190,227-237,340-356 (original), ItemZirnoxRod.java:102 (original)'),
    (SF, 'rod-to-waste', '工作台：7 根天然铀乏棒每根单独拆成 2 个热废料（meta 1），空锆诺克斯棒作为容器物品退回：热废料 +14、乏棒 -7、空棒 +7',
     'NtmRecipeProvider.java:1350,3061-3070, NtmItems.java:697; RodRecipes.java:39 (original), ModItems.java:2980 (original)'),
    (SF, 'pool-insert', '乏燃料池放在六面都是水的位置；12 个热废料逐个右键放进 12 个槽，每槽 1 个（池的堆叠上限是 1）',
     'MachineWasteDrumBlockEntity.java:30,93-103,118-124; TileEntityWasteDrum.java:82-84,103-105,194-202 (original)'),
    (SF, 'cooling', '六面贴水，每个热废料槽每刻以 1/(72,000÷6) = 1/12,000 的概率转冷（nextInt(12000) == 0）。冲刺 %d 刻后：12 槽仍是天然铀废料，'
                    '冷的（meta 0）不少于 %d 个。下限的算法：单槽 N 刻后仍热的概率 (1 - 1/12000)^N，冷的个数服从二项分布 B(12, p)，'
                    'p = 1 - (1 - 1/12000)^N；下限取满足 P(X ≤ M - 1) ≤ 1e-9 的最大 M（用对数伽马逐项累加二项分布的概率），N 取实际走过的刻数'
     % (POOL_TICKS, POOL_MIN),
     'MachineWasteDrumBlockEntity.java:51-81; TileEntityWasteDrum.java:192-228 (original), FuelPoolRecipes.java:27 (original)'),
    (SF, 'reload', '退出重开：池里只剩冷废料，各槽的物品与数量相同（非默认的存储量）',
     'MachineBaseBlockEntity.java:116-132, MachineWasteDrumBlockEntity.java:30,118; TileEntityWasteDrum.java:82-84,130-165 (original)'),
    (RT, 'craft', '工作台：36 个钚-238 粒拼成 6 个钚-238 坯（每 6 粒一坯）；3 坯加 1 块铁板合成 1 个钚-238 放射性同位素燃料靶丸，做 2 个',
     'NtmRecipeProvider.java:3258,3283,3306-3315,3579-3593; MineralRecipes.java:121,205,512-528 (original)'),
    (RT, 'output', 'RTG 发电机放入 2 个钚-238 靶丸、不接任何东西，冻结后走 500 刻：电量从 0 到 50,000（每刻加“靶丸热量之和 10 × 2”× 5 = 100），'
                   '热量读数 20（上限 600，衰变开着）',
     'MachineRTGBlockEntity.java:30,42-44,69-75, RTGUtil.java:45-66, NtmItems.java:538; TileEntityMachineRTG.java:28-30,100-107 (original), '
     'RTGUtil.java:27-44 (original), ModItems.java:2655 (original)'),
    (RT, 'decay', 'doRTGsDecay 为真（默认）时每块靶丸每刻寿命减 1：寿命上限 = (long)(float(4,800,000 × 87.7f)) × 1.5 = %s，'
                  '500 刻后每块的 PELLET_DEPLETION = %s；scaleRTGPower 为假（默认）时热量不随寿命变' % (format(PELLET_LIFE, ','), format(PELLET_LIFE - RTG_TICKS, ',')),
     'RTGPelletItem.java:93-125, RTGUtil.java:13-21,76-91, CommonConfig.java:539-546; ItemRTGPellet.java:83-125 (original), '
     'RTGUtil.java:54-69 (original), VersatileConfig.java:30-36 (original), MachineConfig.java:7-8,14-15 (original)'),
    (RT, 'reload', '退出重开：RTG 断开电缆后电量停在上限 100,000，热量 20，两块靶丸仍在',
     'MachineRTGBlockEntity.java:30,74-75,137-149; TileEntityMachineRTG.java:30,44-55,105-107 (original)'),
    (PX_, 'cold-only', 'PUREX 选“再处理 天然铀废料”后：热废料（meta 1）点不进输入槽，冷废料（meta 0）放得进',
     'PUREXRecipes.java:50-51,158-164, ModuleMachineBase.java:200-220, MachinePUREXBlockEntity.java:291-297, MachinePUREXMenu.java:29, '
     'SlotNonRetarded.java:24-26; PUREXRecipes.java:91-92 (original: ComparableStack(item) = damage 0), RecipesCommon.java:260-268 (original), '
     'TileEntityMachinePUREX.java:222-227 (original), ContainerMachinePUREX.java:29 (original), ContainerBase.java:101-106 (original)'),
    (PX_, 'process', 'PUREX 的电只经电缆来自 RTG，加工前电缆拆断；预写：煤油 1,000 mB、硝酸 500 mB 用命令写进输入罐。放入 1 个冷废料后，'
                     '第 99 刻还没有产出、电量少 99,000；第 100 刻（进度每刻加 0.01，100 次后 ≥ 1）产出 1 个铀-238 粒、2 个反应堆级钚粒、'
                     '1 个钚-239 粒、2 个小撮核废料，废料用掉，煤油剩 500、硝酸剩 250，电量正好少 100,000（每刻 1,000 HE）',
     'PUREXRecipes.java:46-57, ModuleMachineBase.java:47-70,115-168,176-197, MachinePUREXBlockEntity.java:114-120,142, '
     'Fluids.java:272,332,950-953 (流体 id 22 与 82 按声明顺序); '
     'PUREXRecipes.java:38,91-98 (original), ModuleMachineBase.java:118-130,188-210 (original), TileEntityMachinePUREX.java:94-113 (original)'),
    (PX_, 'reload', '退出重开：PUREX 的电量、两罐余量、四个产出槽与所选配方相同',
     'MachinePUREXBlockEntity.java:267-289, ModuleMachineBase.java:242-250; TileEntityMachinePUREX.java:194-219 (original), ModuleMachineBase.java:256-266 (original)'),
    (RR, 'fresh-rod', '新做的天然铀 RBMK 燃料棒（空棒 + 8 个天然铀坯）单独放进工作台：浓度 1 > 0.99，没有产物',
     'RBMKRodDisassemblyRecipe.java:31-35,40-45, NtmRecipeProvider.java:1145,3008-3014; RBMKFuelCraftingHandler.java:17-26,48-49 (original), '
     'RodRecipes.java:90,245-247 (original)'),
    (RR, 'cold-rod', '预写：把那根燃料棒的 yield 写成 50,000,000（浓度 0.5）、核心与外壳 20 °C、氙 0。单独放进工作台：'
                     '出 8 个天然铀 RBMK 芯块，meta = 4 - clamp(ceil(0.5 × 5 - 1), 0, 4) = 2（毒化度 < 0.5（氙 < 50）不加 5），空燃料棒作为容器物品退回',
     'RBMKRodDisassemblyRecipe.java:47-50, NtmItems.java:784-791,1481-1483, RBMKRodItem.java:384-394,567-583; '
     'RBMKFuelCraftingHandler.java:51-56 (original), ItemRBMKRod.java:75 (original)'),
    (RR, 'reload-stage10', '退出重开：玩家物品栏里的 8 个芯块与空燃料棒数量相同', 'the player inventory is saved with the player (vanilla); RBMKRodItem.java:22-26,484-487 (custom data travels with the stack)'),
    (RF, 'schrabidium', '预写：施拉比粒与镎粒用命令发放（施拉比只来自熔毁烧焦的铀矿）。工作台：2 施拉比粒 + 2 镎粒 + 2 铍粒 -> 1 施拉比燃料坯，做 8 个，'
                        '空燃料棒 + 8 坯 -> MES 燃料棒；5 施拉比 + 2 镎 + 2 铍 -> 1 HES 锭，做 6 个，2 锭 -> 3 HES 坯（做 9 个），8 坯 -> HES 燃料棒；'
                        '1 施拉比 + 4 镎 + 4 铍 -> 1 LES 锭，做 6 个，2 锭 -> 3 LES 坯（做 9 个），8 坯 -> LES 燃料棒。52 个施拉比粒、52 个镎粒、'
                        '52 个铍粒正好用完，各剩 1 个 HES 坯与 LES 坯',
     'NtmRecipeProvider.java:1168-1170,3008-3014,3248-3249,3396-3423,3579-3600; MineralRecipes.java:144,146,180,417-418,526-534 (original), '
     'RodRecipes.java:113-115,245-247 (original)'),
    (RF, 'reload-stage10', '退出重开：玩家物品栏里的 MES、HES、LES 燃料棒与剩下的坯数量相同', 'the player inventory is saved with the player (vanilla); RBMKRodItem.java:22-26,484-487 (custom data travels with the stack)'),
]


def expectations():
    return [dict(id='%s.%s' % (f, i), text=t, source=s) for f, i, t, s in E]


def rid(f, i):
    return '%s.%s' % (f, i)


# ---------------------------------------------------------------- small helpers (creative inventory: no inventory-screen moves)

cmd = _lib.cmd


def slot_name(s):
    return 'hotbar.%d' % s if s < 9 else 'inventory.%d' % (s - 9)


def issue(ctx, item, n):
    """Issues `n` of `item` into free main-inventory slots (`item replace`), one stack per slot as the item stacks: the hotbar
    stays free for the hand. Rods stack to one, so each takes a slot."""
    per = 1 if item in (ROD,) else 64
    left = n
    while left > 0:
        free = _lib.free_slots(_lib.inventory(ctx), 1, start=9)
        if not free:
            raise RuntimeError('no free inventory slot for %s' % item)
        k = min(per, left)
        cmd(ctx, 'item replace entity @s %s with %s %d' % (slot_name(free[0]), item, k))
        left -= k


def free_hand(ctx):
    """Selects an empty hotbar slot (creative: the inventory screen is the creative screen, so nothing is moved by hand)."""
    items = _lib.inventory(ctx)
    free = next((s for s in range(9) if s not in items), None)
    if free is None:
        raise RuntimeError('no empty hotbar slot')
    ctx.step('key', key='key.keyboard.%d' % (free + 1), action='tap', after=2)


def place_block(ctx, block, against, stand):
    """A machine put into the empty hand by command and placed with a real right-click on top of `against` from `stand`."""
    free_hand(ctx)
    cmd(ctx, 'item replace entity @s weapon.mainhand with %s' % block)
    try:
        _lib.use_on(ctx, against, 'up', stand)
    finally:
        cmd(ctx, 'item replace entity @s weapon.mainhand with minecraft:air')


def open_screen(ctx, pos, face, stand, expect, center=False):
    free_hand(ctx)
    if center:
        _lib.use_center(ctx, pos, face, stand)
    else:
        _lib.use_on(ctx, pos, face, stand)
    ctx.step('screen', expect=expect)
    return ctx.step('hud', frames=2)


def items_by_slot(data):
    return _lib.items_of(data)


def zirnox_rods(data):
    """(depleted slots, {fresh slot: life}) of the reactor's 24 rod slots."""
    dep, fresh = [], {}
    for s, e in items_by_slot(data).items():
        if s is None or s >= 24:
            continue
        if e['id'] == DEPLETED:
            dep.append(s)
        elif e['id'] == ROD:
            fresh[s] = (e['components'].get('minecraft:custom_data') or {}).get('life', 0)
    return sorted(dep), fresh


def counts_delta(ctx, before):
    return _lib.delta(_lib.inventory_counts(ctx), before)


def park(ctx):
    ctx.step('view', pos=MID, pitch=20.0, yaw=0.0, fly=False, hide_gui=False)


def config_switches(ctx):
    """doRTGsDecay / scaleRTGPower / enable528 from the client's common config (the integrated server reads the same file)."""
    try:
        import common
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import common
    out = {}
    path = common.CLIENTS / ctx.default / 'config' / 'hbmsntm-common.toml'
    try:
        for line in path.read_text(encoding='utf-8').splitlines():
            k, _, v = line.strip().partition('=')
            if k.strip() in ('doRTGsDecay', 'scaleRTGPower', 'enable528'):
                out[k.strip()] = v.strip()
    except OSError as e:
        out['error'] = repr(e)
    return out


# ---------------------------------------------------------------- the line

def run(ctx):
    S = {}   # state handed from section to section
    _lib.setup_world(ctx)                  # creative, frozen
    park(ctx)
    ctx.step('wait', ticks=40)
    cmd(ctx, 'clear @s', allow_error=True)

    # ---------------------------------------------------------------- start items
    handover = set(HANDOVER)
    on_list = [i for i, _ in GIVE if i in handover or i + '@0' in handover]
    ctx.check(rid(SF, 'start-items'), len(on_list) == len(GIVE) and not any(i in handover for i, _, _ in ISSUED),
              'from the stage-10 start list (%d items): %s; besides: %s'
              % (len(HANDOVER), ', '.join('%s x%d' % g for g in GIVE), '; '.join('%s x%d (%s)' % (i, n, r[:60]) for i, n, r in ISSUED)))

    # ---------------------------------------------------------------- site (命令搭建: stone shell, water, barrels, cables)
    def site():
        for item, n in [(ROD, 24)]:
            issue(ctx, item, n)
        # ZIRNOX, placed by hand
        place_block(ctx, H + 'machine_zirnox', (ZX[0], Y - 1, ZX[2] + 2), [ZX[0] + 0.5, Y, ZX[2] + 6.5])
        core, props = _lib.core_of(ctx, H + 'machine_zirnox', (ZX[0] - 3, Y, ZX[2] - 4), (ZX[0] + 3, Y + 2, ZX[2] + 4))
        rot = _lib.clockwise(props['facing'])
        d = _lib.VEC[rot]
        port = (core[0] + 3 * d[0], core[1] + 1, core[2] + 3 * d[2])
        cmd(ctx, 'setblock %d %d %d hbmsntm:barrel_steel' % port)
        _lib.placed(ctx, 4)
        cmd(ctx, 'data merge block %d %d %d {mode:0s,tank_type:"SUPERHOTSTEAM"}' % port)
        cmd(ctx, 'item replace block %d %d %d container.4 with hbmsntm:fluid_barrel_infinite' % port)
        cmd(ctx, 'item replace block %d %d %d container.24 with hbmsntm:fluid_barrel_infinite' % core)   # 预写: CO2
        cmd(ctx, 'item replace block %d %d %d container.25 with hbmsntm:fluid_barrel_infinite' % core)   # 预写: water
        S['zirnox'], S['port'] = core, port
        # crafting table
        place_block(ctx, 'minecraft:crafting_table', (TABLE[0], Y - 1, TABLE[2]), [TABLE[0] + 0.5, Y, TABLE[2] + 2.5])
        if not _lib.is_block(ctx, TABLE, 'minecraft:crafting_table'):
            raise RuntimeError('the crafting table was not placed at %s' % (TABLE,))
        # spent fuel pool: stone shell, open interior, a stone to place the drum on
        dx, dy, dz = DRUM
        cmd(ctx, 'fill %d %d %d %d %d %d minecraft:stone' % (dx - 2, Y - 1, dz - 2, dx + 2, Y + 2, dz + 2))
        cmd(ctx, 'fill %d %d %d %d %d %d minecraft:air' % (dx - 1, Y, dz - 1, dx + 1, Y + 2, dz + 1))
        cmd(ctx, 'setblock %d %d %d minecraft:stone' % (dx, Y, dz))
        rim = [dx + 0.5, Y + 3, dz + 2.5]   # on the shell, within reach of the drum's top face
        S['rim'] = rim
        place_block(ctx, H + 'machine_waste_drum', (dx, Y, dz), rim)
        if not _lib.is_block(ctx, DRUM, H + 'machine_waste_drum'):
            raise RuntimeError('the drum was not placed at %s' % (DRUM,))
        cmd(ctx, 'fill %d %d %d %d %d %d minecraft:water replace minecraft:air' % (dx - 1, Y, dz - 1, dx + 1, Y + 2, dz + 1))
        cmd(ctx, 'setblock %d %d %d minecraft:water' % (dx, Y, dz))
        wet = [n for n, v in _lib.VEC.items() if _lib.is_block(ctx, (dx + v[0], dy + v[1], dz + v[2]), 'minecraft:water')]
        if len(wet) != WATER_FACES:
            raise RuntimeError('water on %s only' % wet)
        S['wet'] = wet
        # PUREX and the RTG
        place_block(ctx, H + 'machine_purex', (PX[0], Y - 1, PX[2] + 2), [PX[0] + 0.5, Y, PX[2] + 6.5])
        pcore, _ = _lib.core_of(ctx, H + 'machine_purex', (PX[0] - 3, Y, PX[2] - 4), (PX[0] + 3, Y + 1, PX[2] + 4))
        rtg = (pcore[0] + 6, Y, pcore[2])
        place_block(ctx, H + 'machine_rtg', (rtg[0], Y - 1, rtg[2]), [rtg[0] + 0.5, Y, rtg[2] + 2.5])
        if not _lib.is_block(ctx, rtg, H + 'machine_rtg'):
            raise RuntimeError('the RTG was not placed at %s' % (rtg,))
        S['purex'], S['rtg'] = pcore, rtg
        S['cables'] = [(pcore[0] + k, Y, pcore[2]) for k in (3, 4, 5)]
        park(ctx)

    all_rows = [rid(f, i) for f, i, _, _ in E if (f, i) != (SF, 'start-items')]
    if _lib.section(ctx, all_rows, site, 'building the site failed'):
        return

    # ---------------------------------------------------------------- ZIRNOX burn-up
    def burn():
        core = S['zirnox']
        hud = open_screen(ctx, (core[0], Y, core[2] + 2), 'south', [core[0] + 0.5, Y, core[2] + 4.5], 'ReactorZirnox', center=True)
        items = _lib.inventory(ctx)
        rods = [s for s, e in sorted(items.items()) if e['id'] == ROD]
        ctx.step('mod', shift=True)
        try:
            for s in rods:
                _lib.click(ctx, _lib.menu_slot(28, s), after=2)
        finally:
            ctx.step('mod', shift=False)
        ctx.step('click', at=[hud['gui_left'] + 151, hud['gui_top'] + 42], after=4)   # ReactorZirnoxScreen.java:81: the switch
        ctx.step('close')
        d0 = _lib.block_data(ctx, core)
        dep0, fresh0 = zirnox_rods(d0)
        if len(fresh0) != 24 or any(fresh0.values()) or not d0.get('isOn'):
            raise RuntimeError('reactor not ready: %d fresh rods, lives %s, isOn %s' % (len(fresh0), sorted(set(fresh0.values())), d0.get('isOn')))
        t_on = ctx.server()['game_time']
        sched, life_end = depletion(66668)
        peaks = dict(heat=0, pressure=0, steam=0, reads=0)

        def watch(c):
            d = _lib.block_data(c, core)
            peaks['reads'] += 1
            for k in ('heat', 'pressure', 'steam'):
                peaks[k] = max(peaks[k], d.get(k, 0))
            return d.get('heat', 0) > 90_000 or d.get('pressure', 0) > 90_000 or d.get('steam', 0) >= 7_900

        def to_tick(target, label):
            need = target - (ctx.server()['game_time'] - t_on)
            if need >= 2:
                park(ctx)
                r = ctx.sprint(need - 1, until=watch, label=label, poll_s=1.0, timeout_s=900)
                if r.get('stopped_early'):
                    cmd(ctx, 'data merge block %d %d %d {isOn:0b}' % core)
                    raise RuntimeError('the reactor came close to its limits (peaks %s); switched off' % peaks)
            elif need == 1:
                _lib.server_steps(ctx, 1)
            got = ctx.server()['game_time'] - t_on
            if got != target:
                raise RuntimeError('%s: %d ticks since switch-on, wanted %d' % (label, got, target))
            data = _lib.block_data(ctx, core)
            return data

        # a short first window: the steam must leave through the barrel (a full steam tank stops the pressure cooling,
        # ReactorZirnoxBlockEntity.java:184-191), checked before the long sprints
        warm = to_tick(400, 'zirnox-warmup')
        if warm.get('steam', 0) >= 4000 or warm.get('heat', 0) >= 50_000:
            cmd(ctx, 'data merge block %d %d %d {isOn:0b}' % core)
            raise RuntimeError('after 400 ticks: steam %s, heat %s, pressure %s; switched off' % (warm.get('steam'), warm.get('heat'), warm.get('pressure')))
        log, good = [], True
        for target, label in ((50000, 'zirnox-50000'), (50001, 'zirnox-50001'), (66667, 'zirnox-66667'), (66668, 'zirnox-66668')):
            data = to_tick(target, label)
            dep, fresh = zirnox_rods(data)
            want = sorted(s for s, t in sched.items() if t <= target)
            sim_life = life_end if target == 66668 else None
            lives_ok = True
            if sim_life is not None:
                lives_ok = all(fresh.get(s) == sim_life[s] for s in range(24) if s not in want) and len(fresh) == 24 - len(want)
            good = good and dep == want and lives_ok and data.get('heat', 0) < MELTDOWN and data.get('pressure', 0) < MELTDOWN
            log.append('tick %d: depleted %s (simulated %s)%s; heat %s pressure %s'
                       % (target, dep, want, '' if sim_life is None else ', fresh lives %s (simulated %s)'
                          % (sorted(fresh.items()), sorted((s, sim_life[s]) for s in range(24) if s not in want)),
                          data.get('heat'), data.get('pressure')))
        good = good and peaks['heat'] < MELTDOWN and peaks['pressure'] < MELTDOWN and peaks['reads'] > 0
        ctx.check(rid(SF, 'burnup'), good, '; '.join(log) + '; peaks over %d reads during the sprints: heat %d, pressure %d, steam %d of 8000; '
                  '预写: CO2 and water from infinite barrels in slots 24/25' % (peaks['reads'], peaks['heat'], peaks['pressure'], peaks['steam']))
        # switch off and take the rods out by hand
        hud = open_screen(ctx, (core[0], Y, core[2] + 2), 'south', [core[0] + 0.5, Y, core[2] + 4.5], 'ReactorZirnox', center=True)
        ctx.step('click', at=[hud['gui_left'] + 151, hud['gui_top'] + 42], after=4)
        ctx.step('mod', shift=True)
        try:
            for s in TAKE:
                _lib.click(ctx, s, after=2)
        finally:
            ctx.step('mod', shift=False)
        ctx.step('close')
        d1 = _lib.block_data(ctx, core)
        if d1.get('isOn') or _lib.count(ctx, DEPLETED) != len(TAKE):
            raise RuntimeError('after the burn: isOn %s, depleted rods in the inventory %d' % (d1.get('isOn'), _lib.count(ctx, DEPLETED)))
        S['burnt'] = True

    _lib.section(ctx, [rid(SF, 'burnup')], burn, 'the ZIRNOX burn failed')

    # ---------------------------------------------------------------- hot waste at the crafting table
    def open_table():
        open_screen(ctx, TABLE, 'south', [TABLE[0] + 0.5, Y, TABLE[2] + 2.5], 'Crafting')

    def waste():
        if not S.get('burnt'):
            raise _lib.Missing('no depleted rods from the burn')
        before = _lib.inventory_counts(ctx)
        open_table()
        _lib.craft(ctx, ['d'], {'d': DEPLETED}, times=len(TAKE))
        ctx.step('close')
        d = counts_delta(ctx, before)
        n = len(TAKE)
        ok = d.get(WASTE + '@1', 0) == 2 * n and d.get(DEPLETED, 0) == -n and d.get(H + 'rod_zirnox_empty', 0) == n
        ctx.check(rid(SF, 'rod-to-waste'), ok, 'inventory change %s (want hot waste +%d, depleted rods -%d, empty ZIRNOX rods +%d)'
                  % (d, 2 * n, n, n))
        S['hot'] = ok

    _lib.section(ctx, [rid(SF, 'rod-to-waste')], waste, 'the depleted rods were not taken apart')

    # ---------------------------------------------------------------- spent fuel pool
    def pool():
        if not S.get('hot'):
            raise _lib.Missing('no hot waste')
        free_hand(ctx)
        _lib.use_on(ctx, DRUM, 'up', S['rim'])
        ctx.step('screen', expect='WasteDrum')
        _lib.put_n(ctx, POOL_SLOTS, WASTE, list(range(POOL_SLOTS)), k=1, meta=1)
        ctx.step('close')
        g0 = ctx.server()['game_time']
        items = items_by_slot(_lib.block_data(ctx, DRUM))
        ok = sorted(items) == list(range(POOL_SLOTS)) and all(e['id'] == WASTE and e['meta'] == 1 and e['count'] == 1 for e in items.values())
        ctx.check(rid(SF, 'pool-insert'), ok, 'water on %s; drum slots %s'
                  % (S['wet'], ', '.join('%d:%s@%d x%d' % (s, e['id'].split(':')[1], e['meta'], e['count']) for s, e in sorted(items.items()))))
        if not ok:
            raise _lib.Missing('the pool was not filled')
        park(ctx)
        _lib.advance(ctx, POOL_TICKS, 'pool', poll_s=1.0)
        g1 = ctx.server()['game_time']
        items = items_by_slot(_lib.block_data(ctx, DRUM))
        cold = [s for s, e in items.items() if e['id'] == WASTE and e['meta'] == 0]
        hot = [s for s, e in items.items() if e['id'] == WASTE and e['meta'] == 1]
        n = g1 - g0
        p = p_cooled(n)
        m = _lib.binomial_lower(POOL_SLOTS, p, ALPHA)
        ctx.check(rid(SF, 'cooling'), len(cold) + len(hot) == POOL_SLOTS and len(cold) >= m,
                  '%d ticks: %d of 12 cold (slots %s), %d hot; p = %.5f, lower bound M = %d (alpha %g)'
                  % (n, len(cold), sorted(cold), len(hot), p, m, ALPHA))
        S['cold'], S['hot_left'] = sorted(cold), sorted(hot)

    _lib.section(ctx, [rid(SF, 'pool-insert'), rid(SF, 'cooling')], pool, 'the spent fuel pool failed')

    # ---------------------------------------------------------------- RTG pellets and the generator
    def rtg():
        issue(ctx, H + 'nugget_pu238', 36)
        issue(ctx, H + 'plate_iron', 2)
        before = _lib.inventory_counts(ctx)
        open_table()
        _lib.craft(ctx, ['nnn', 'nnn'], {'n': H + 'nugget_pu238'}, times=6)
        _lib.craft(ctx, ['bbb', 'p'], {'b': H + 'billet_pu238', 'p': H + 'plate_iron'}, times=2)
        ctx.step('close')
        d = counts_delta(ctx, before)
        ok = d.get(H + 'pellet_rtg', 0) == 2 and d.get(H + 'nugget_pu238', 0) == -36 and d.get(H + 'plate_iron', 0) == -2 \
            and d.get(H + 'billet_pu238', 0) == 0
        ctx.check(rid(RT, 'craft'), ok, 'inventory change %s (want pellet_rtg +2, nugget_pu238 -36, plate_iron -2, billets +6 -6)' % d)
        if not ok:
            raise _lib.Missing('no plutonium-238 pellets')
        pos = S['rtg']
        open_screen(ctx, pos, 'south', [pos[0] + 0.5, Y, pos[2] + 2.5], 'RTG')
        items = _lib.inventory(ctx)
        pellets = [s for s, e in sorted(items.items()) if e['id'] == H + 'pellet_rtg']
        for k, s in enumerate(pellets[:2]):
            _lib.click(ctx, _lib.menu_slot(15, s))
            _lib.click(ctx, k)
        ctx.step('close')
        r0 = _lib.block_data(ctx, pos)
        if [e['id'] for e in items_by_slot(r0).values()] != [H + 'pellet_rtg'] * 2:
            raise RuntimeError('RTG slots: %s' % items_by_slot(r0))
        g0 = ctx.server()['game_time']
        park(ctx)
        _lib.advance(ctx, RTG_TICKS, 'rtg')
        g1 = ctx.server()['game_time']
        r1 = _lib.block_data(ctx, pos)
        n = g1 - g0
        heat = 2 * PELLET_HEAT
        p0, p1 = r0.get('power', 0), r1.get('power', 0)
        ctx.check(rid(RT, 'output'), n == RTG_TICKS and p1 - p0 == heat * 5 * n and r1.get('heat') == heat,
                  '%d ticks: power %d -> %d (want +%d = %d x 5 x %d), heat %s (want %d)' % (n, p0, p1, heat * 5 * n, heat, n, r1.get('heat'), heat))
        lives = [(e['components'].get('minecraft:custom_data') or {}).get('PELLET_DEPLETION') for e in items_by_slot(r1).values()]
        sw = config_switches(ctx)
        ctx.check(rid(RT, 'decay'), sw.get('doRTGsDecay') == 'true' and sw.get('scaleRTGPower') == 'false'
                  and lives == [PELLET_LIFE - n] * 2,
                  'config %s; pellet lives %s after %d ticks (want %d - %d = %d each)' % (sw, lives, n, PELLET_LIFE, n, PELLET_LIFE - n))
        S['rtg_ok'] = True

    _lib.section(ctx, [rid(RT, 'craft'), rid(RT, 'output'), rid(RT, 'decay')], rtg, 'the RTG part failed')

    # ---------------------------------------------------------------- PUREX
    def purex():
        if not S.get('rtg_ok'):
            raise _lib.Missing('no RTG to power the PUREX')
        if not S.get('cold'):
            raise _lib.Missing('no cold waste from the pool')
        core = S['purex']
        stand = [core[0] + 0.5, Y, core[2] + 4.5]
        open_screen(ctx, (core[0], Y, core[2] + 2), 'south', stand, 'PUREX', center=True)
        # the selector entry is named "再处理 %s" around the first input's name (PUREXRecipes.java:50, MachinePUREXScreen.java:57-61)
        tip = 'item.hbmsntm.waste_natural_uranium'
        recipe = _lib.pick_recipe(ctx, core, 'hbmPUREX.json', 'purex.zirnoxnu', tip)
        ctx.step('close', allow_fail=True)
        if recipe != 'purex.zirnoxnu':
            raise RuntimeError('recipe0 is %r after the selector' % recipe)
        cmd(ctx, 'data merge block %d %d %d {i0:%d,i0_type:"KEROSENE",i1:%d,i1_type:"NITRIC_ACID"}' % (core + (KERO_FILL, ACID_FILL)))   # 预写 (FluidTank.java:263-271 reads a name)
        # charge over the cable from the RTG, then cut it
        for c in S['cables']:
            cmd(ctx, 'setblock %d %d %d hbmsntm:red_cable' % c)
        park(ctx)
        _lib.advance(ctx, CHARGE_TICKS, 'purex-charge')
        cmd(ctx, 'setblock %d %d %d minecraft:air' % S['cables'][1])
        _lib.still(ctx)
        # waste out of the pool: every hot one (the pool keeps only cold waste) and one cold
        free_hand(ctx)
        _lib.use_on(ctx, DRUM, 'up', S['rim'])
        ctx.step('screen', expect='WasteDrum')
        ctx.step('mod', shift=True)
        try:
            for s in S['hot_left'] + S['cold'][:1]:
                _lib.click(ctx, s, after=2)
        finally:
            ctx.step('mod', shift=False)
        ctx.step('close')
        # hot waste is refused, cold waste goes in
        open_screen(ctx, (core[0], Y, core[2] + 2), 'south', stand, 'PUREX', center=True)
        items = _lib.inventory(ctx)
        hot_src = _lib.find_slot(items, WASTE, 1)
        if hot_src is None:
            raise _lib.Missing('no hot waste in the inventory')
        _lib.click(ctx, _lib.menu_slot(13, hot_src))
        r = _lib.click(ctx, 4)
        if _lib.carried(r):
            _lib.click(ctx, _lib.menu_slot(13, hot_src))
        hot_in = _lib.slot_item(_lib.block_data(ctx, core), 4)
        _lib.put_n(ctx, 13, WASTE, [4], k=1, meta=0)
        ctx.step('close')
        d0 = _lib.block_data(ctx, core)
        cold_in = _lib.slot_item(d0, 4)
        ctx.check(rid(PX_, 'cold-only'), hot_in is None and cold_in is not None and cold_in.get('id') == WASTE
                  and _lib.meta_of(cold_in) == 0 and cold_in.get('count') == 1,
                  'recipe %s (selector entry hovered and checked against %s); after clicking hot waste on input slot 4: %s; after the cold one: %s'
                  % (recipe, tip, hot_in, cold_in))
        if cold_in is None:
            raise _lib.Missing('no cold waste in the PUREX')
        p0 = d0.get('power', 0)
        if p0 < PUREX_TICKS * PUREX_POWER:
            raise RuntimeError('the PUREX holds only %d HE after %d ticks on the RTG' % (p0, CHARGE_TICKS))
        tanks0 = _lib.tanks(d0)
        g0 = ctx.server()['game_time']
        park(ctx)
        _lib.advance(ctx, PUREX_TICKS - 1, 'purex-99')
        d99 = _lib.block_data(ctx, core)
        _lib.server_steps(ctx, 1)
        d100 = _lib.block_data(ctx, core)
        n = ctx.server()['game_time'] - g0
        out99 = [(s, e['id'], e['count']) for s, e in sorted(items_by_slot(d99).items()) if 7 <= s <= 12]
        out100 = [(s, e['id'], e['count']) for s, e in sorted(items_by_slot(d100).items()) if 7 <= s <= 12]
        t100 = _lib.tanks(d100)
        ok = (n == PUREX_TICKS and not out99 and _lib.slot_item(d99, 4) is not None and d99.get('power') == p0 - (PUREX_TICKS - 1) * PUREX_POWER
              and out100 == PUREX_OUT and _lib.slot_item(d100, 4) is None and d100.get('power') == p0 - PUREX_TICKS * PUREX_POWER
              and t100.get('i0', {}).get('fill') == KERO_FILL - 500 and t100.get('i0', {}).get('type') == KEROSENE
              and t100.get('i1', {}).get('fill') == ACID_FILL - 250 and t100.get('i1', {}).get('type') == NITRIC)
        ctx.check(rid(PX_, 'process'), ok,
                  'power before %d (over the cable from the RTG, %d ticks); tanks before %s; tick 99: outputs %s, progress %s, power %s; '
                  'tick %d: outputs %s (want %s), input %s, tanks %s, power %s (want %d); 预写: kerosene %d mB and nitric acid %d mB'
                  % (p0, CHARGE_TICKS, {k: (v['fill'], v['type']) for k, v in tanks0.items()}, out99, d99.get('progress0'), d99.get('power'),
                     n, out100, PUREX_OUT, _lib.slot_item(d100, 4), {k: (v['fill'], v['type']) for k, v in t100.items()},
                     d100.get('power'), p0 - PUREX_TICKS * PUREX_POWER, KERO_FILL, ACID_FILL))
        S['purex_ok'] = True

    _lib.section(ctx, [rid(PX_, 'cold-only'), rid(PX_, 'process')], purex, 'the PUREX part failed')

    # ---------------------------------------------------------------- RBMK rod taken apart
    def rbmk():
        issue(ctx, H + 'billet_uranium', 8)
        issue(ctx, H + 'rbmk_fuel_empty', 4)
        open_table()
        _lib.craft(ctx, ['ebb', 'bbb', 'bbb'], {'e': H + 'rbmk_fuel_empty', 'b': H + 'billet_uranium'})
        ctx.step('close')
        items = _lib.inventory(ctx)
        src = _lib.find_slot(items, H + 'rbmk_fuel_ueu')
        if src is None:
            raise _lib.Missing('the RBMK rod was not crafted')
        before = _lib.inventory_counts(ctx)
        open_table()
        _lib.click(ctx, _lib.menu_slot(10, src))
        _lib.click(ctx, 5)
        r = _lib.click(ctx, 0)
        result = (r.get('before') or {}).get('slot_item')
        ctx.step('close')
        d = counts_delta(ctx, before)
        ctx.check(rid(RR, 'fresh-rod'), result == 'minecraft:air' and not d,
                  'result slot with the fresh rod alone in the grid: %s; inventory change after closing %s' % (result, d or 'none'))
        # 预写: the rod half burnt and cold
        src = _lib.find_slot(_lib.inventory(ctx), H + 'rbmk_fuel_ueu')
        cmd(ctx, 'item replace entity @s %s with hbmsntm:rbmk_fuel_ueu[minecraft:custom_data={yield:%.1fd,xenon:0.0d,core:20.0d,hull:20.0d}]'
            % (slot_name(src), float(PREWRITTEN_YIELD)))
        before = _lib.inventory_counts(ctx)
        open_table()
        _lib.click(ctx, _lib.menu_slot(10, src))
        _lib.click(ctx, 5)
        _lib.shift_click(ctx, 0)
        ctx.step('close')
        d = counts_delta(ctx, before)
        enrich = PREWRITTEN_YIELD / ROD_YIELD
        meta = 4 - min(4, max(0, -int(-(enrich * 5 - 1) // 1)))
        ctx.check(rid(RR, 'cold-rod'), d.get(H + 'rbmk_pellet_ueu@%d' % meta, 0) == 8 and d.get(H + 'rbmk_fuel_ueu', 0) == -1
                  and d.get(H + 'rbmk_fuel_empty', 0) == 1 and len(d) == 3,
                  '预写 yield %d (enrichment %.2f): inventory change %s (want rbmk_pellet_ueu@%d +8, rbmk_fuel_ueu -1, rbmk_fuel_empty +1)'
                  % (PREWRITTEN_YIELD, enrich, d, meta))

    _lib.section(ctx, [rid(RR, 'fresh-rod'), rid(RR, 'cold-rod')], rbmk, 'the RBMK rod part failed')

    # ---------------------------------------------------------------- schrabidium rods
    def schrab():
        issue(ctx, H + 'nugget_schrabidium', 52)    # 预写
        issue(ctx, H + 'nugget_neptunium', 52)      # 预写
        issue(ctx, H + 'nugget_beryllium', 52)
        if _lib.count(ctx, H + 'rbmk_fuel_empty') < 3:
            issue(ctx, H + 'rbmk_fuel_empty', 3 - _lib.count(ctx, H + 'rbmk_fuel_empty'))
        empty0 = _lib.count(ctx, H + 'rbmk_fuel_empty')
        before = _lib.inventory_counts(ctx)
        s, n_, b = H + 'nugget_schrabidium', H + 'nugget_neptunium', H + 'nugget_beryllium'
        open_table()
        _lib.craft(ctx, ['ssn', 'nbb'], {'s': s, 'n': n_, 'b': b}, times=8)
        _lib.craft(ctx, ['ebb', 'bbb', 'bbb'], {'e': H + 'rbmk_fuel_empty', 'b': H + 'billet_schrabidium_fuel'})
        _lib.craft(ctx, ['sss', 'ssn', 'nbb'], {'s': s, 'n': n_, 'b': b}, times=6)
        _lib.craft(ctx, ['ii'], {'i': H + 'ingot_hes'}, times=3)
        _lib.craft(ctx, ['ebb', 'bbb', 'bbb'], {'e': H + 'rbmk_fuel_empty', 'b': H + 'billet_hes'})
        _lib.craft(ctx, ['snn', 'nnb', 'bbb'], {'s': s, 'n': n_, 'b': b}, times=6)
        _lib.craft(ctx, ['ii'], {'i': H + 'ingot_les'}, times=3)
        _lib.craft(ctx, ['ebb', 'bbb', 'bbb'], {'e': H + 'rbmk_fuel_empty', 'b': H + 'billet_les'})
        ctx.step('close')
        d = counts_delta(ctx, before)
        want = {H + 'rbmk_fuel_mes': 1, H + 'rbmk_fuel_hes': 1, H + 'rbmk_fuel_les': 1, H + 'billet_hes': 1, H + 'billet_les': 1,
                s: -52, n_: -52, b: -52, H + 'rbmk_fuel_empty': -3}
        ctx.check(rid(RF, 'schrabidium'), d == want, '预写 52 schrabidium and 52 neptunium nuggets; empty rods before %d; inventory change %s (want %s)'
                  % (empty0, d, want))

    _lib.section(ctx, [rid(RF, 'schrabidium')], schrab, 'the schrabidium rods failed')

    # ---------------------------------------------------------------- leave, reopen, compare
    def reload():
        park(ctx)
        _lib.advance(ctx, FINAL_TICKS, 'rtg-cap')
        _lib.still(ctx)
        first = readings(ctx, S)
        _lib.server_steps(ctx, 20)
        second = readings(ctx, S)
        static = {g: _lib.static_readings(first[g], second[g]) for g in first}
        _lib.reopen(ctx, near=(int(MID[0]), Y, int(MID[2])))
        park(ctx)
        _lib.still(ctx)
        after = readings(ctx, S)
        for g, eid, nq in ((SF, rid(SF, 'reload'), ()), (PX_, rid(PX_, 'reload'), ('recipe0',)), (RT, rid(RT, 'reload'), ()),
                           (RR, rid(RR, 'reload-stage10'), ()), (RF, rid(RF, 'reload-stage10'), ())):
            same, moved = static[g]
            if not same:
                ctx.not_run(eid, 'no static reading in this group (moved: %s)' % moved)
                continue
            res = _lib.compare_static(same, {k: after[g].get(k) for k in same}, not_quantity=nq)
            extra = ''
            if g == RT:
                extra = '; RTG power %s (cap %d)' % (same.get('power'), RTG_MAX)
                res['ok'] = res['ok'] and same.get('power') == RTG_MAX
            ctx.check(eid, res['ok'], '%s; moved between two reads 20 ticks apart (not compared): %s; values %s%s'
                      % (res['detail'], moved or 'none', same, extra))

    reload_rows = [rid(SF, 'reload'), rid(PX_, 'reload'), rid(RT, 'reload'), rid(RR, 'reload-stage10'), rid(RF, 'reload-stage10')]
    _lib.section(ctx, reload_rows, reload, 'the reload comparison failed')


def readings(ctx, S):
    out = {SF: {}, PX_: {}, RT: {}, RR: {}, RF: {}}
    drum = items_by_slot(_lib.block_data(ctx, DRUM))
    out[SF] = dict(drum_items=tuple(sorted((s, e['id'], e['meta'], e['count']) for s, e in drum.items())),
                   drum_cold=sum(1 for e in drum.values() if e['meta'] == 0))
    if S.get('purex'):
        d = _lib.block_data(ctx, S['purex'])
        t = _lib.tanks(d)
        out[PX_] = dict(power=d.get('power'), recipe0=d.get('recipe0'),
                        i0=t.get('i0', {}).get('fill'), i0_type=t.get('i0', {}).get('type'),
                        i1=t.get('i1', {}).get('fill'), i1_type=t.get('i1', {}).get('type'),
                        outputs=tuple((s, e['id'], e['count']) for s, e in sorted(items_by_slot(d).items()) if 7 <= s <= 12))
    if S.get('rtg'):
        d = _lib.block_data(ctx, S['rtg'])
        out[RT] = dict(power=d.get('power'), heat=d.get('heat'), pellets=tuple(e['id'] for _, e in sorted(items_by_slot(d).items())))
    inv = _lib.inventory_counts(ctx)
    out[RR] = {k: inv.get(k, 0) for k in (H + 'rbmk_pellet_ueu@2', H + 'rbmk_fuel_empty')}
    out[RF] = {k: inv.get(k, 0) for k in (H + 'rbmk_fuel_mes', H + 'rbmk_fuel_hes', H + 'rbmk_fuel_les', H + 'billet_hes', H + 'billet_les')}
    return out
