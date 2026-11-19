"""Main line, stage 9 (RBMK): structural columns from the assembly machine, the columns and consoles from the crafting table, the
fuel rods (empty rod + 8 billets), a small fixed reactor whose MEU rod is burned for real under /tick sprint until it can be taken
apart, its steam turned into power by a steam engine in a closed water loop, the autoloader, the crane, the storage column, the
irradiation channel and the waste drum. Real crafting-table clicks, real placement, real GUI clicks and real crane keys; no
meltdown in this file.

Game mode: survival for the assembly, the crafting and the placement of every block; creative from the moment the radioactive
fuel is handed out. A survival player would not live through the line: eight radium-226-beryllium billets or the rod made from
them radiate 90 RAD/s (HazardRegistry.java:88,118,120,148,153,388,455; HazardTypeRadiation.java:39-50), the open columns feed
the chunk radiation every tick (RBMKRodBlockEntity.java:139-141, RBMKNeutronHandler.java:285-296,309-310), a player takes a
twentieth of the chunk value per tick (EntityEffectHandler.java:189-195) and dies at 1,000 RAD (EntityEffectHandler.java:157-158);
creative players take neither (ContaminationUtil.java:179).

Sections (each fails alone; a later section that needs an earlier one's product turns its rows into not-run):
  A  assembly machine (placed by hand) on a wood burner: 11 structural columns (ass.rbmk), then the autoloader
     (ass.rbmkautoloader).
  C  crafting table: deco blocks, 2 fuel channels, 3 absorbers, 2 control rods, reflector, moderator, boiler, irradiation
     channel, storage column, RBMK console, crane console, linking device, 2 fluid identifiers, a steel barrel, a steam
     condenser and a battery socket.
  B  everything placed by hand: the ten columns, the steam rig (ducts typed with the identifiers, barrel filled with 4 buckets),
     the consoles linked with the linking device, the autoloader on S (cycle 40 %), the waste drum and a chest. Then creative.
  F  fuel (creative): 4 empty rods, 3 MEU rods and 1 Ra226Be rod in the crafting table; 16 thorium-232 billets into the
     irradiation channel, one MEU rod into the storage column, the Ra226Be rod and two spare MEU rods into the autoloader (it
     fills the empty channel S); the crane moves the MEU rod from the storage column into F.
  R  the run from the moment both control rods are set to 100 % in their screens: every count from a freeze and exact sprints,
     derived by simulating the columns in their own double arithmetic, seeded from the server readings at that moment.
     AZ-5 on the console once F's rod is burned to 99 % enrichment; then the crane moves the rod into the storage column.
  W  recycling: the spent rod into the waste drum (water under it) until core and hull are below 50, taken apart in the
     crafting table into 8 MEU pellets that go into the chest. The empty rod it gives back and 8 more MEU billets make one
     fresh MEU rod (core and hull 20, which the drum leaves as it is, MachineWasteDrumBlockEntity.java:63-70,
     RBMKRodItem.java:212-260; original TileEntityWasteDrum.java:212-216), left in the drum as the drum's own static store.
  rest: the Ra226Be rod is taken out of S by hand into the storage column; the autoloader refills S with its first spare MEU rod.
     Once the line rests, an RBMK lid is put on the reflector column R by hand (RBMKLidItem.java:30-54: the core's lid state,
     RBMKBaseBlock.java:50,62,68; original ItemRBMKLid.java:22-66), after every neutron and heat count, so no path above is
     touched by it.
Then the world is left and opened again and every feature's resting readings are compared. A column's heat at rest is 20.0, the
floor every tick re-imposes (RBMKBaseBlockEntity.java:216-218), and hasRod is recomputed every tick (RBMKRodBlockEntity.java:170,182):
neither is a stored quantity. rbmk-core compares the lid state of R (its column heats are named, not compared); rbmk-reactor
compares the rod item and custom data in S, and its heat, hasRod and flux readings count as no stored quantity.

Layout (x east, z south; Y = -60 the flat world's first air layer; X0 = Z0 = 5000; every column core at Y, the column 4 blocks
tall, Y .. Y+3 (dialColumnHeight 4, RBMKDials.java:58-60, CommonConfig.java:575-578, RBMKBaseBlock.java:76)):

         z0-3      O                 irradiation channel (16 thorium-232 billets)
         z0-1      B                 boiler (water duct under it at Y-1, steam duct over it at Y+4)
         z0     A  S  C1 F  C2 M  R  absorber, Ra226Be channel (autoloader on top, Y+4 .. Y+12), control, MEU channel, control,
                                     moderator, reflector
         z0+2         ST             storage column
              x0-3 .. x0 .. x0+3

  Placement (= block-entity tick) order A, S, C1, F, C2, M, R, B, O, ST. F's four streams: west through C1 into S, east through
  C2 and M to the reflector R and back into F, north through B (passes) to O, south past ST. S's streams: east through C1 into F,
  west into the absorber A. No moderated fuel channel or control rod (no bismuth parts).
  Steam side: steam engine core (x0+6, Y, z0-2) facing north, connections at x0+8, Y+1, z0-3 .. z0-1: steam duct from the
  boiler's top port (x0 .. x0+8 at Y+4, z0-1, down to Y+1), red cable to the battery socket (core x0+12, z0-3), the steam
  condenser on a stone block; its water runs in a duct (x0+9 down to Y-1, west along z0-3, to x0+1, then to the boiler's
  bottom port (x0, Y-1, z0-1)); the steel barrel (send mode) stands on that duct at (x0+3, Y, z0-3).
  RBMK console near (x0-8, Y, z0+7), crane console near (x0, Y, z0+7) facing south, waste drum (x0-14, Y, z0+8) with a water
  source under it, chest (x0-16, Y, z0+8). Crane girder level Y+10: stone at (x0, Y+10, z0-1) and (x0, Y+10, z0+3) make the
  crane's front span 0 and back span 2, so the crane stops exactly over F and over ST.

命令搭建 (by command, listed in the report): clearing the site; the red cable cells and the fluid ducts (setblock; their fluid
types are then set by hand with the identifiers); the stone under the condenser, the stone the player stands on to reach the
top of S, the two girder stones; the water source under the waste drum; the switch to creative before the fuel. Start items
and the materials are given by command. Not on the stage-9 start list but given as items of earlier stages (needs_stage of the
closure report): graphite ingots and blocks (stage 2), the welded steel plates (stage 4), the wood burner (2), the steam engine
(2), the redstone battery (2), the RBMK lid (4), vanilla materials. The 8 extra MEU billets of the drum's rod are stage-9 start
items.

Expected values are derived from the code (NEO file:line, the 1.7.10 original's file:line beside it). Readings are server data
(`data get block` / `data get entity`), taken in the frozen world after 80 client ticks. A sprint started in the frozen world
runs one tick more than requested; exact tick counts come from the freeze and _lib.advance_to, never from an `until` sprint.
Floating readings are compared with the simulation within 1e-9 relative (the simulation repeats the Java double arithmetic;
only Math.sin/log10 may differ in the last bit); tick counts and item counts are compared exactly.
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

FEATURES = ['rbmk-core', 'rbmk-fuel', 'rbmk-reactor', 'rbmk-control', 'rbmk-steam', 'rbmk-console', 'rbmk-storage', 'rbmk-recycling',
            'rbmk-outgasser', 'rbmk-autoloader', 'rbmk-crane']

SCENARIO = dict(
    id='rbmk-reactor.mainline_stage9',
    feature='rbmk-reactor',
    features=FEATURES,
    title='Main line stage 9: RBMK columns from the assembly machine, a small reactor burned under sprint, steam to power, '
          'autoloader, crane, storage, irradiation channel and waste drum (real crafting, placement, GUI and crane keys)',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

H = _lib.H
Y = -60
X0, Z0 = 5000, 5000
TOP = Y + 3                          # the column's top block (core + 3 dummies, RBMKDials.java:58-60)

# columns in placement order: (name, core, block, kind)
COLS = [('A', (X0 - 3, Y, Z0), 'rbmk_absorber', 'absorber'), ('S', (X0 - 2, Y, Z0), 'rbmk_rod', 'rod'),
        ('C1', (X0 - 1, Y, Z0), 'rbmk_control', 'control'), ('F', (X0, Y, Z0), 'rbmk_rod', 'rod'),
        ('C2', (X0 + 1, Y, Z0), 'rbmk_control', 'control'), ('M', (X0 + 2, Y, Z0), 'rbmk_moderator', 'moderator'),
        ('R', (X0 + 3, Y, Z0), 'rbmk_reflector', 'reflector'), ('B', (X0, Y, Z0 - 1), 'rbmk_boiler', 'boiler'),
        ('O', (X0, Y, Z0 - 3), 'rbmk_outgasser', 'outgasser'), ('ST', (X0, Y, Z0 + 2), 'rbmk_storage', 'storage')]
POS = {n: p for n, p, _, _ in COLS}
# where the player stands to place each column on the grass under its core (reach <= 4.5 blocks)
PLACE_FROM = {n: [p[0] + 0.5, Y, p[2] + 3.5] for n, p, _, _ in COLS if p[2] == Z0}
PLACE_FROM.update(B=[X0 + 1.5, Y, Z0 - 2.5], O=[X0 + 0.5, Y, Z0 - 5.5], ST=[X0 + 0.5, Y, Z0 + 5.5])
AUTOLOADER = (X0 - 2, TOP + 1, Z0)  # 9 blocks tall (RBMKAutoloaderBlock.java:37)
PLATFORM = (X0 - 2, TOP, Z0 + 1)
ON_PLATFORM = [X0 - 1.5, TOP + 1, Z0 + 1.5]
# stone cells in the neutron paths, by (x, z): solid blocks among the column-height cells over Y (getHits)
SOLID = {(PLATFORM[0], PLATFORM[2]): 1}

AX, AZ = X0 - 20, Z0 - 10            # ground cell clicked for the assembly machine
BURNER_AT = (AX - 8, AZ)             # ground cell clicked for the wood burner
BUS_Z = AZ + 6                       # the cable bus under the ground
TABLE = (X0 - 12, Y, Z0 - 6)
ENGINE = (X0 + 6, Y, Z0 - 2)
SUPPORT = (X0 + 8, Y, Z0 - 3)
COND = (X0 + 8, Y + 1, Z0 - 3)
SOCKET = (X0 + 12, Y, Z0 - 3)
BARREL = (X0 + 3, Y, Z0 - 3)
STEAM_DUCTS = [(X0 + i, TOP + 1, Z0 - 1) for i in range(9)] + [(X0 + 8, Y + j, Z0 - 1) for j in range(1, 4)]
WATER_DUCTS = ([(X0 + 9, Y + 1, Z0 - 3), (X0 + 9, Y, Z0 - 3)] + [(x, Y - 1, Z0 - 3) for x in range(X0 + 9, X0, -1)]
               + [(X0 + 1, Y - 1, Z0 - 2), (X0 + 1, Y - 1, Z0 - 1), (X0, Y - 1, Z0 - 1)])
CABLES = [(x, Y + 1, Z0 - 2) for x in range(X0 + 8, X0 + 13)] + [(X0 + 12, Y, Z0 - 2)]
CONSOLE_CELL = (X0 - 8, Y, Z0 + 7)
CRANE_CELL = (X0, Y, Z0 + 7)
GIRDER_Y = TOP + 1 + 6               # centerY = core y + 3 + 1, girders 6 above (RBMKCraneConsoleBlockEntity.java:356-361)
BLOCKERS = [(X0, GIRDER_Y, Z0 - 1), (X0, GIRDER_Y, Z0 + 3)]
DRUM = (X0 - 14, Y, Z0 + 8)
CHEST = (X0 - 16, Y, Z0 + 8)
PARK = [X0 - 2.5, Y, Z0 + 12.5]      # where the player waits during sprints (the whole site within simulation distance)

# start items of the stage-9 list, exactly what the line uses
GIVE_ASM = [(H + 'concrete_asbestos', 44), (H + 'plate_cast[hbmsntm:meta=11]', 22), (H + 'plate_copper', 44), (H + 'ingot_rubber', 22),
            (H + 'machine_assembly_machine', 1)]
GIVE_AUTO = [(H + 'plate_cast[hbmsntm:meta=8]', 4), (H + 'ingot_boron', 4), (H + 'motor', 3)]
GIVE_COLS = [(H + 'shell_steel', 4), (H + 'ingot_boron', 28), (H + 'motor', 4), (H + 'neutron_reflector', 8), (H + 'pipe_copper', 6),
             (H + 'shell_copper', 2), (H + 'steel_grate', 6), (H + 'tank_steel', 1), (H + 'crate_steel', 2), (H + 'circuit_analog_board', 2),
             (H + 'ingot_lead', 2)]
GIVE_RIG = [(H + 'circuit_vacuum_tube', 2), (H + 'plate_iron', 6), (H + 'plate_steel', 8), (H + 'ingot_steel', 6),
            (H + 'plate_cast[hbmsntm:meta=5]', 1), (H + 'ingot_red_copper', 1)]
GIVE_FUEL = [(H + 'ingot_zirconium', 24), (H + 'rod_quad_empty', 8), (H + 'billet_uranium_fuel', 24), (H + 'billet_ra226be', 8),
             (H + 'billet_th232', 16)]
GIVE_LINE = [(H + 'machine_waste_drum', 1)]
# not on the stage-9 list, issued as items of earlier stages (needs_stage of the closure report)
OUTSIDE = [(H + 'machine_wood_burner', 1), (H + 'plate_welded[hbmsntm:meta=11]', 4), (H + 'ingot_graphite', 4), (H + 'block_graphite', 4),
           (H + 'machine_steam_engine', 1), (H + 'battery_pack', 1), (H + 'rbmk_lid', 1)]
VANILLA = [('minecraft:oak_log', 3), ('minecraft:crafting_table', 1), ('minecraft:hopper', 1), ('minecraft:glass_pane', 1),
           ('minecraft:iron_ingot', 2), ('minecraft:blue_dye', 2), ('minecraft:water_bucket', 4), ('minecraft:chest', 1)]
BUCKETS = 4
WATER_ID, STEAM_ID = 1, 2              # Fluids.java:250-252 registration order (NONE, WATER, STEAM)
WATER_IDX, STEAM_IDX = 3, 7            # FluidScreen unfiltered list (Fluids.java:421-430 metaOrder): NONE, AIR, AIRBLAST, WATER, ..., STEAM
TH_BILLETS = 16
MEU, RA = H + 'rbmk_fuel_meu', H + 'rbmk_fuel_ra226be'

# ---------------------------------------------------------------- dials and constants (CommonConfig defaults = RBMKDials)
PASSIVE, PASSIVE_INNER, FLOW, DIFF_MOD, PROVISION = 2.5, 0.1, 0.2, 1.0, 0.2   # CommonConfig.java:555-574; original RBMKDials.java:19-26
COLUMN_HITS = 4                        # RBMKNeutronHandler.columnHeight = getColumnHeight() + 1 (NeutronHandler.java:43)
FLUX_RANGE = 5                         # CommonConfig.java:604-607; original RBMKDials.java:31
HEAT_PER_MB = 0.1                      # boiler heat per mB of water, CommonConfig.java:583-586; original RBMKDials.java:26
CTRL_SPEED = 0.00277                   # RBMKControlBlockEntity.java:27; original TileEntityRBMKControl.java:31
OUTGASSER_DURATION = 10000             # RBMKOutgasserBlockEntity.java:35; original TileEntityRBMKOutgasser.java:38
ABSORB = 0.05                          # absorber heat per flux, CommonConfig.java:636-639; original RBMKDials.java:42
ENRICH_LIMIT = 0.99                    # RBMKRodDisassemblyRecipe.java:45; original RBMKFuelCraftingHandler.java:48
OP_HE = 170                            # steam engine: 200 HE x 0.85 per 100 mB steam (MachineSteamEngineBlockEntity.java:31-33,83-88)

FUELS = {
    # RBMK_FUEL_MEU NtmItems.java:792-799 (original ModItems.java:3091-3098): LOG_TEN 20, RAISING_SLOPE, heat 0.65, defaults
    # diffusion 0.02, SLOW in, FAST out, xenon 0.5 / 50 (RBMKRodItem.java:31-42)
    MEU: dict(yld=1e8, react=20.0, self=0.0, func='log', dep='raising', heat=0.65, diff=0.02, n='slow', r='fast', xgen=0.5, xburn=50.0),
    # RBMK_FUEL_RA226BE NtmItems.java:962-972 (original ModItems.java:3260-3270): PASSIVE 20, LINEAR, heat 0.035, diffusion 0.5,
    # SLOW in, SLOW out, xenon 0 / 50
    RA: dict(yld=1e8, react=0.0, self=20.0, func='passive', dep='linear', heat=0.035, diff=0.5, n='slow', r='slow', xgen=0.0, xburn=50.0),
}

E = [
    ('rbmk-core', 'assemble', '装配机（手放，配方选择界面里选 ass.rbmk）：每根结构柱 4 石棉混凝土、2 钢铸板、4 铜板、2 橡胶锭，100 刻、每刻 100 HE。'
     '一次放进 11 根的料，木柴发电机一直开着：第 1,099 刻输出槽 10 根，第 1,100 刻 11 根，四种原料全部用尽（进度每刻加 1/100，满 1 出一根）',
     'AssemblyMachineRecipes.java:462-466, ModuleMachineBase.java:115-127; 原版 AssemblyMachineRecipes.java:528-530'),
    ('rbmk-core', 'craft-columns', '工作台真实点击：1 根结构柱 → 8 块 RBMK 装饰块；钢壳/结构柱/钢壳 → 燃料通道（做 2）；8 硼锭围结构柱 → 吸收柱（做 3）；'
     '马达、石墨锭围吸收柱 → 控制棒（做 2，用掉 2 根吸收柱）；8 中子反射板 → 反射柱；4 石墨块 → 慢化柱；铜管与铜壳 → 锅炉柱；钢格栅、漏斗、钢罐 → '
     '辐照通道；2 钢箱 → 存储柱；硼锭、4 装饰块、玻璃板、模拟电路板 → RBMK 控制台；硼锭、电路板、4 装饰块 → 吊车控制台；铅锭与铁锭 → 连接装置。'
     '做完 11 根结构柱、8 块装饰块全部用尽，各成品数量正确',
     'NtmRecipeProvider.java:934-961,985-992,1007-1015,1050-1058,1080-1099,1106-1133; 原版 CraftingManager.java:757-761,770-771,789,990-994, '
     'ToolRecipes.java:133'),
    ('rbmk-core', 'heat-field', '控制棒拉到 100% 后的第 T+2,000 刻（T = 首次产汽刻），10 根柱子的热量都等于按代码逐刻模拟的值（相对误差 1e-9）：'
     '每刻每根柱子与东南西北的 RBMK 邻柱求平均，按 0.2 的步长向平均靠拢（就地修改邻柱，结果依赖放置顺序），再按邻柱数 n 被动散热 '
     '0.1 + 2.4 × (4 − n)/4，最低 20；吸收柱每吸收 1 中子流加 0.05 热；中子流在下一刻开头（冻结中也照样）处理',
     'RBMKBaseBlockEntity.java:133-137,155-219, RBMKNeutronHandler.java:371-376, NeutronHandler.java:20-51; 原版 TileEntityRBMKBase.java:91-95,'
     '159-259, RBMKNeutronHandler.java:358'),
    ('rbmk-fuel', 'craft-rods', '（创造模式）工作台真实点击：6 个锆锭与 2 根四联空棒 → 1 根 RBMK 空燃料棒（做 4）；1 根空燃料棒 + 8 个 MEU 燃料坯 → '
     'MEU 燃料棒（做 3），1 根空燃料棒 + 8 个镭-226-铍坯 → 镭-226-铍中子源棒（做 1）：新棒不带燃耗数据（读数取默认：产额 1e8、氙 0、芯/壳 20），'
     '坯、锆锭、四联空棒与空燃料棒全部用尽',
     'NtmRecipeProvider.java:1137-1146,1163,3008-3014, RBMKRodItem.java:567-583; 原版 RodRecipes.java:89-91,108,245-247'),
    ('rbmk-fuel', 'burnup', 'F 里的 MEU 棒真实燃烧：每刻产额减去进入的中子流，模拟给出产额首次 ≤ 0.99 × 1e8 的刻 Te；第 Te − 1 刻产额 > 99,000,000，'
     '第 Te 刻 ≤ 99,000,000（可以拆解），产额、氙、芯温、壳温与模拟一致（相对 1e-9；氙在预热时入射流不到 25 时积累，之后每刻烧掉 流²/50 多于'
     '生成的 0.5 × 流）',
     'RBMKRodItem.java:152-198,212-260; 原版 ItemRBMKRod.java:152-260'),
    ('rbmk-reactor', 'warmup', '两根控制棒在各自界面点 100% 后（冻结中）开始计刻，模拟给出锅炉第一次产汽的刻 T：第 T − 1 刻锅炉与蒸汽机蒸汽都是 0、'
     '电池 0；第 T 刻锅炉+蒸汽机蒸汽 = 100 × 模拟当刻用水（锅炉热量超过 100 的部分每 0.1 用 1 mB 水，向下取整）',
     'RBMKBoilerBlockEntity.java:73-105, RBMKRodBlockEntity.java:104-186; 原版 TileEntityRBMKBoiler.java:67-100, TileEntityRBMKRod.java:117-197'),
    ('rbmk-reactor', 'flux', '第 T+2,000 刻 F 与 S 记录的入射中子流（fluxQuantity）等于模拟值（相对 1e-9）：F 收到 S 经 C1 的流与自己经 C2、慢化柱、'
     '反射柱折返的流，控制棒按插入度乘流，慢化柱把快中子比例归零，反射柱把流送回源头',
     'RBMKRodBlockEntity.java:162-168,204-248,269-274, RBMKNeutronHandler.java:240-393; 原版 TileEntityRBMKRod.java:199-240, '
     'RBMKNeutronHandler.java:300-348'),
    ('rbmk-control', 'raise', 'C1、C2 各在自己的界面点“100%”（GUI 118,26），并点第 3 个颜色（GUI 28,48）：目标 1.0；插入度每刻 +0.00277，'
     '第 361 刻 < 1、第 362 刻 = 1.0（两根都是），颜色 2',
     'RBMKControlScreen.java:45-71, RBMKControlBlockEntity.java:27,42-61, RBMKControlManualBlockEntity.java:46-50,83-95; '
     '原版 GUIRBMKControl.java:44-67, TileEntityRBMKControl.java:31,76-90,95-102, TileEntityRBMKControlManual.java:52-61,70-87'),
    ('rbmk-steam', 'rig', '流体识别器在自己的界面里选水（不打字，未筛选列表第 4 项），潜行右键水管一次，整条 14 节都标成水；另一个选蒸汽，潜行右键'
     '蒸汽管一次，12 节都标成蒸汽；钢桶界面放 1 个识别器（水）、点模式键 2 次（发送）、倒进 4 桶水：桶加锅炉进水共 4,000 mB',
     'FluidScreen.java:128-188, FluidDuctBaseBlock.java:52-113, BarrelBlockEntity.java:259-263,295-300, RBMKBaseBlockEntity.java:524-552; '
     '原版 FluidDuctBase.java:59-126'),
    ('rbmk-steam', 'loop', '闭合水循环：锅炉进水 + 桶 + (锅炉蒸汽 + 蒸汽机蒸汽)/100 + 蒸汽机乏汽 + 冷凝器两罐，在第 T+2,000 刻与第 Te 刻都恰好 4,000'
     '（1 mB 水 → 100 mB 蒸汽 → 1 mB 乏汽 → 1 mB 水）；锅炉进水一直多于 0',
     'RBMKBoilerBlockEntity.java:85-103, MachineSteamEngineBlockEntity.java:83-88, CondenserBaseBlockEntity.java:42-51; '
     '原版 TileEntityRBMKBoiler.java:96-100, TileEntitySteamEngine.java:99-104, TileEntityCondenser.java:73-77'),
    ('rbmk-steam', 'power', '第 T+2,000 刻电池电量 = 170 × 蒸汽机做功次数，做功次数 = 模拟累计用水 − (锅炉蒸汽 + 蒸汽机蒸汽)/100（每 100 mB 蒸汽 '
     '200 × 0.85 = 170 HE；红石电池每刻收 1,000 HE、容量 1,800,000，没满）',
     'MachineSteamEngineBlockEntity.java:31-33,83-88, Fluids.java:611, BatteryPackItem.java:28,47-52, BatterySocketBlockEntity.java:116-118,134; 原版 TileEntitySteamEngine.java:45-47,99-104'),
    ('rbmk-console', 'az5', '连接装置先潜行右键 F 再潜行右键控制台：控制台目标 = F。F 的棒燃到 Te 后在控制台界面点 AZ-5（第一下掀盖，第二下按下）：'
     '两根控制棒目标 0、起始插入度 1.0；插入度每刻 −0.00277，按代码在第 k0 − 1 刻 > 0、第 k0 刻 = 0',
     'RBMKToolItem.java:49-85, RBMKConsoleScreen.java:275-291, RBMKConsoleBlockEntity.java:275-305,380-391, RBMKControlBlockEntity.java:42-61; '
     '原版 ItemRBMKTool.java:43-63, GUIRBMKConsole.java:219-240, TileEntityRBMKConsole.java:257-280'),
    ('rbmk-crane', 'link', '吊车控制台手放（朝南），大梁层（柱顶上 7 格，Y+10）放两块石头：连接装置潜行右键 F 后潜行右键吊车台：中心 (x0, Y+4, z0)，'
     '前跨 0、后跨 2（从中心沿梁数到第一块挡物），已设置',
     'RBMKCraneConsoleBlockEntity.java:356-387, RBMKToolItem.java:93-107; 原版 TileEntityCraneConsole.java:298-319, ItemRBMKTool.java:78-95'),
    ('rbmk-crane', 'load-f', '玩家站在操作区内：按住“下”45 刻，吊车位置每刻 −0.05，夹到 −2（存储柱上方）；回车：吊钩每刻下 0.04，到底取出存储柱 0 号格的'
     ' MEU 棒，再升回；按住“上”45 刻回到 0（F 上方）；回车：棒装进 F，吊车空手、存储柱空',
     'RBMKCraneConsoleBlockEntity.java:60,101-125,146-176,202-217,232-234,271-297, RBMKStorageBlockEntity.java:79-102, RBMKRodBlockEntity.java:418-441; '
     '原版 TileEntityCraneConsole.java:57,101-171,224-245'),
    ('rbmk-crane', 'unload-f', 'AZ-5 后插入度归零时，吊车在 F 上方回车：取出燃过的 MEU 棒（吊车读数 held 是它）；按住“下”回到存储柱上方再回车：棒进存储柱'
     ' 11 号格，吊车空手。回车那一刻 t1 之后吊钩每刻下 0.04，25 次后到底（−3.5e-16），第 t1 + 26 刻交换；存储柱先于吊车台放置、先更新，所以放入后'
     '读数时（t1 + 60 刻）棒在 11 − （t1 + 26, t1 + 60] 里 10 的倍数个数 号格',
     'RBMKCraneConsoleBlockEntity.java:103-125, RBMKStorageBlockEntity.java:36-48,84-88; 原版 TileEntityCraneConsole.java:98-131, '
     'TileEntityRBMKStorage.java:29-41,74-76'),
    ('rbmk-storage', 'shift', '存储柱每逢游戏时间为 10 的倍数做一次前移（空格后面的物品前移一格，一次一格）：放进 11 号格的棒，从放入时所在格 s 起，'
     '经过 5 次前移在 s − 5 格，经过 s − 1 次前移在 1 号格，经过 s 次前移在 0 号格（s 次到 0 号格后不再动，读数停在 s − 1 与 s 次才分得出恰好 s 次）',
     'RBMKStorageBlockEntity.java:31-53; 原版 TileEntityRBMKStorage.java:29-36'),
    ('rbmk-autoloader', 'assemble', '同一台装配机改选 ass.rbmkautoloader：4 钢焊接板、4 铅铸板、4 硼锭、3 马达，100 刻：第 99 刻输出槽空，第 100 刻出 1 台自动装填机',
     'AssemblyMachineRecipes.java:470-474; 原版 AssemblyMachineRecipes.java:532-535'),
    ('rbmk-autoloader', 'swap', '自动装填机潜行放在 S 顶上，界面里“−”点两下（50% → 40%），镭-226-铍棒放进 0 号格、两根备用 MEU 棒放进 1、2 号格'
     '（冻结中）：此后第一个游戏时间为 20 的倍数的刻 k1 开始下降（S 空），活塞每刻 +0.005（200 次后 1.0000000000000007 ≥ 1）；第 k1 + 198 刻 S'
     ' 仍空，第 k1 + 199 刻活塞到 1、镭-226-铍棒进 S、装填机 0 号格空，1、2 号格仍是 MEU 棒',
     'RBMKAutoloaderBlockEntity.java:52-54,69-145,213-226,309-314; 原版 TileEntityRBMKAutoloader.java:37-39,53-130,260-266'),
    ('rbmk-autoloader', 'refill', '线尾手工把镭-226-铍棒从 S 取出后（冻结中），第一个游戏时间为 20 的倍数的刻 k1 开始下降：第 k1 + 198 刻 S 仍空，'
     '第 k1 + 199 刻装填机把 1 号格的备用 MEU 棒装进 S，2 号格的仍在',
     'RBMKAutoloaderBlockEntity.java:88-96,98-104,106-142; 原版 TileEntityRBMKAutoloader.java:68-118'),
    ('rbmk-outgasser', 'irradiate', '辐照通道（F 北面第 3 格）放 16 个钍-232 坯：F 的北向中子流穿过锅炉柱进入通道，进度 += 流 × min(1 − 快中子比 × 0.8, 1)，'
     '超过 10,000 出 1 个钍燃料坯、进度归零。第 T+2,000 刻与第 Te 刻，出坯数、剩余钍坯与进度都等于模拟值（进度相对 1e-9）',
     'RBMKOutgasserBlockEntity.java:35,52-133, OutgasserRecipes.java:167; 原版 TileEntityRBMKOutgasser.java:38,69-129'),
    ('rbmk-recycling', 'drum', '燃过的 MEU 棒手放进废料桶（下面一格是水，有水才做，MachineWasteDrumBlockEntity.java:52、原版 TileEntityWasteDrum.java:204）：每刻芯→壳扩散按 0.025 倍（再乘棒的扩散基数 diffusion，默认 0.02，RBMKRodItem.java:40,221-222）、壳向 20 °C 散热按 0.025 倍（再乘热量提供系数 getFuelHeatProvision()，RBMKRodItem.java:254）；模拟给出芯与壳都 < 50 的刻 '
     'Tc：第 Tc − 1 刻还不满足，第 Tc 刻满足，芯、壳与模拟一致（相对 1e-9）',
     'MachineWasteDrumBlockEntity.java:48-71,135-138, RBMKRodItem.java:212-260; 原版 TileEntityWasteDrum.java:185-228'),
    ('rbmk-recycling', 'pellets', '冷却后的棒（产额 ≤ 99%）在工作台单独拆解：得 8 个 MEU 燃料芯块，meta = 4 − clamp(ceil(浓缩度 × 5 − 1), 0, 4) = 0'
     '（氙 < 50 不加 5），空燃料棒退回 1 根；芯块放进箱子',
     'RBMKRodDisassemblyRecipe.java:29-52, NtmItems.java:1481-1482 (空燃料棒作为容器物品退回); 原版 RBMKFuelCraftingHandler.java:25-54, ItemRBMKRod.java:75'),
]
for _f in FEATURES:
    E.append((_f, 'reload', '退出世界再打开：该功能组静置后的服务端读数（见 detail）与退出前相同，参与比对的非默认存储读数至少一个',
              'RBMKBaseBlockEntity.java:225-238 及各方块实体 saveAdditional/loadAdditional; 原版 TileEntityRBMKBase.java:268-290 及各 TileEntity readFromNBT/writeToNBT'))


def expectations():
    return [dict(id='%s.%s' % (f, i), text=t, source=s) for f, i, t, s in E]


def eid(f, name):
    return '%s.%s' % (f, name)


SEC_A = [eid('rbmk-core', 'assemble'), eid('rbmk-autoloader', 'assemble')]
SEC_C = [eid('rbmk-core', 'craft-columns')]
SEC_B = [eid('rbmk-steam', 'rig'), eid('rbmk-crane', 'link')]
SEC_F = [eid('rbmk-fuel', 'craft-rods'), eid('rbmk-autoloader', 'swap'), eid('rbmk-crane', 'load-f')]
SEC_R = [eid('rbmk-control', 'raise'), eid('rbmk-reactor', 'warmup'), eid('rbmk-core', 'heat-field'), eid('rbmk-reactor', 'flux'),
         eid('rbmk-steam', 'power'), eid('rbmk-steam', 'loop'), eid('rbmk-outgasser', 'irradiate'), eid('rbmk-fuel', 'burnup'),
         eid('rbmk-console', 'az5'), eid('rbmk-crane', 'unload-f'), eid('rbmk-storage', 'shift')]
SEC_W = [eid('rbmk-recycling', 'drum'), eid('rbmk-recycling', 'pellets')]
SEC_REST = [eid('rbmk-autoloader', 'refill')]


# ---------------------------------------------------------------- simulation (the columns' own double arithmetic)

def rectify(v):
    # RBMKRodItem.rectify (RBMKRodItem.java:200-206; original ItemRBMKRod.java:200-206)
    if v > 1_000_000.0:
        v = 1_000_000.0
    if v < 20.0 or v != v:
        v = 20.0
    return v


class Rod:
    """An RBMK fuel rod item: burn (RBMKRodItem.java:152-198), updateHeat (:212-227), provideHeat (:234-260); original
    ItemRBMKRod.java:152-234. The depletion and reactivity functions follow :292-309 and :350-360."""

    def __init__(self, item, y, x, core, hull):
        self.item, self.f = item, FUELS[item]
        self.y, self.x, self.core, self.hull = y, x, core, hull

    def enrichment(self):
        return self.y / self.f['yld']

    def burn(self, influx):
        f = self.f
        influx += f['self']
        x = self.x
        x -= influx * influx / f['xburn']
        influx *= (1.0 - self.x / 100.0)
        x += influx * f['xgen']
        self.x = min(max(x, 0.0), 100.0)
        e = self.enrichment()
        if f['func'] == 'passive':
            out = f['self'] * e
        else:
            m = e + math.sin(e * math.pi) / 2.0 if f['dep'] == 'raising' else e
            out = math.log10(influx * m + 1) * 0.5 * f['react']
        self.y = max(self.y - influx, 0.0)
        self.core = rectify(self.core + out * f['heat'])
        return out

    def update_heat(self, mod=1.0):
        if self.core > self.hull:
            mid = (self.core - self.hull) / 2.0
            c = self.core - mid * self.f['diff'] * DIFF_MOD * mod
            h = self.hull + mid * self.f['diff'] * DIFF_MOD * mod
            self.core, self.hull = rectify(c), rectify(h)

    def provide(self, heat, mod=1.0):
        if self.hull <= heat:
            return 0.0
        ret = (self.hull - heat) / 2.0
        ret *= PROVISION * mod
        self.hull -= ret
        return ret


class Col:
    def __init__(self, sim, name, pos, kind):
        self.sim, self.name, self.pos, self.kind = sim, name, pos, kind
        self.heat = 0.0
        self.rod = None
        self.has_rod = False
        self.q = self.r = self.last_q = 0.0
        self.level = self.target = self.start = 0.0
        self.progress, self.done, self.inputs = 0.0, 0, 0
        self.cache = None

    def can_process(self):
        return self.inputs > 0

    def mult(self):
        # RBMKControlManualBlockEntity.getMult (:52-61): the surge while a rod goes in from above its starting level
        surge = 0.0
        if self.target < self.start and abs(self.level - self.target) > 0.01:
            surge = math.sin(math.pow(1 - self.level, 15) * math.pi) * (self.start - self.target)
        return self.level + surge

    def move_heat(self):
        # RBMKBaseBlockEntity.moveHeat / coolPassively (:167-219); original TileEntityRBMKBase.java:159-259
        if self.cache is None:
            self.cache = [self.sim.cols.get((self.pos[0] + dx, self.pos[2] + dz)) for dx, dz in ((0, -1), (1, 0), (0, 1), (-1, 0))]
        rec = [self] + [c for c in self.cache if c is not None]
        if len(rec) > 1:
            t = sum(c.heat for c in rec) / len(rec)
            for c in rec:
                c.heat += (t - c.heat) * FLOW
        n = min(max(len(rec) - 1, 0), 4)
        self.heat -= PASSIVE_INNER + (PASSIVE - PASSIVE_INNER) * ((4 - n) / 4.0)
        if self.heat < 20:
            self.heat = 20.0

    def tick(self):
        k = self.kind
        if k == 'rod':
            if self.rod is not None:
                rod = self.rod
                fast, slow = self.q * self.r, self.q * (1 - self.r)
                fin = slow + fast * 0.5 if rod.f['n'] == 'slow' else fast + slow * 0.3
                ratio = 0.0 if rod.f['r'] == 'slow' else 1.0
                out = rod.burn(fin)
                rod.update_heat()
                self.heat += rod.provide(self.heat)
                self.move_heat()
                self.last_q = self.q
                self.q = self.r = 0.0
                for d in ((0, -1), (1, 0), (0, 1), (-1, 0)):
                    self.sim.streams.append((self, d, out, ratio))
                self.has_rod = True
            else:
                self.last_q = self.q = self.r = 0.0
                self.has_rod = False
                self.move_heat()
        elif k == 'control':
            if self.level < self.target:
                self.level += CTRL_SPEED
                if self.level > self.target:
                    self.level = self.target
            if self.level > self.target:
                self.level -= CTRL_SPEED
                if self.level < self.target:
                    self.level = self.target
            self.move_heat()
        elif k == 'boiler':
            hp = self.heat - 100.0
            if hp > 0:
                w = int(math.floor(hp / HEAT_PER_MB))
                self.sim.w_tick += w
                self.heat -= w * HEAT_PER_MB
            self.move_heat()
        elif k == 'outgasser':
            if not self.can_process():
                self.progress = 0.0
            self.move_heat()
        else:
            self.move_heat()

    def receive(self, flux, ratio):
        fast = self.q * self.r
        self.q += flux
        self.r = (fast + flux * ratio) / self.q


class Sim:
    """The ten columns in placement order. The neutron streams the rods queue in a tick run at the start of the next server
    tick, before any block entity ticks (NeutronHandler.java:12-51 on ServerTickEvent.Pre), also in a frozen tick; so a reading
    taken in the frozen world already holds them. One step here = the column ticks, then the streams of that tick
    (RBMKNeutronHandler.RBMKNeutronStream.runStreamInteraction, RBMKNeutronHandler.java:240-393; original
    RBMKNeutronHandler.java:300-430)."""

    def __init__(self, seed):
        self.cols, self.order, self.streams, self.t, self.W, self.w_tick = {}, [], [], 0, 0, 0
        for name, pos, _, kind in COLS:
            c = Col(self, name, pos, kind)
            s = seed[name]
            c.heat = s['heat']
            if kind == 'rod' and s.get('rod'):
                c.rod = Rod(*s['rod'])
                c.has_rod = s['has_rod']
            if kind == 'control':
                c.level, c.target, c.start = s['level'], s['target'], s['start']
            if kind == 'outgasser':
                c.progress, c.inputs = s['progress'], s['inputs']
            self.cols[(pos[0], pos[2])] = c
            self.order.append(c)
        self.by = {c.name: c for c in self.order}

    def run_streams(self):
        for origin, d, flux, ratio in self.streams:
            mods = 0
            for i in range(1, FLUX_RANGE + 1):
                if flux == 0:
                    break
                cell = (origin.pos[0] + d[0] * i, origin.pos[2] + d[1] * i)
                c = self.cols.get(cell)
                if c is None:
                    hits = SOLID.get(cell, 0)        # getHits: solid blocks among the column-height cells (:283-296,419-436)
                    if hits == COLUMN_HITS:
                        break
                    if hits > 0:
                        flux *= 1 - hits / COLUMN_HITS
                    continue
                if c.kind in ('boiler', 'storage'):  # RBMKType.OTHER: passes
                    continue
                if c.kind == 'moderator':
                    mods += 1
                    ratio *= (1 - 1.0)
                    continue
                if c.kind == 'rod':
                    if c.has_rod:
                        c.receive(flux, ratio)
                        break
                    continue
                if c.kind == 'outgasser':
                    if c.can_process():
                        c.progress += flux * min(1 - ratio * 0.8, 1)
                        if c.progress > OUTGASSER_DURATION:
                            c.progress = 0.0
                            c.done += 1
                            c.inputs -= 1
                        break
                    continue
                if c.kind == 'control':
                    if c.level > 0:
                        flux *= c.mult()
                        continue
                    break
                if c.kind == 'reflector':
                    if ratio > 0 and mods > 0:
                        for _ in range(mods):
                            ratio *= (1 - 1.0)
                    origin.receive(flux, ratio)
                    break
                if c.kind == 'absorber':
                    c.heat += ABSORB * flux
                    break
                break
        self.streams = []

    def step(self):
        self.t += 1
        self.w_tick = 0
        for c in self.order:
            c.tick()
        self.run_streams()
        self.W += self.w_tick

    def snap(self):
        b = self.by
        return dict(t=self.t, heat={c.name: c.heat for c in self.order}, W=self.W, w=self.w_tick,
                    F=(b['F'].rod.y, b['F'].rod.x, b['F'].rod.core, b['F'].rod.hull) if b['F'].rod else None,
                    S=(b['S'].rod.y, b['S'].rod.x, b['S'].rod.core, b['S'].rod.hull) if b['S'].rod else None,
                    qF=b['F'].last_q, qS=b['S'].last_q, og=(b['O'].done, b['O'].progress, b['O'].inputs),
                    levels=(b['C1'].level, b['C2'].level))


def close(a, b, rel=1e-9):
    return isinstance(a, (int, float)) and isinstance(b, (int, float)) and abs(a - b) <= rel * max(1.0, abs(b))


# ---------------------------------------------------------------- readings

def gt(ctx):
    return ctx.server()['game_time']


def park(ctx):
    ctx.step('view', pos=PARK, pitch=20.0, yaw=180.0, fly=False, hide_gui=False)


def advance_to(ctx, t0, target, label):
    park(ctx)
    _lib.advance_to(ctx, t0, target, label)


def custom(it):
    return ((it or {}).get('components') or {}).get('minecraft:custom_data') or {}


def rod_state(it):
    """(item, yield, xenon, core, hull) of a rod item compound; a missing key reads as its default (RBMKRodItem.java:567-583)."""
    if it is None or it.get('id') not in FUELS:
        return None
    cd, f = custom(it), FUELS[it['id']]
    return (it['id'], float(cd.get('yield', f['yld'])), float(cd.get('xenon', 0.0)), float(cd.get('core', 20.0)), float(cd.get('hull', 20.0)))


def column_data(ctx):
    return {n: _lib.block_data(ctx, p) for n, p, _, _ in COLS}


def seed_from(data):
    seed = {}
    for n, _, _, kind in COLS:
        d = data[n]
        s = dict(heat=float(d.get('heat', 0.0)))
        if kind == 'rod':
            st = rod_state(_lib.slot_item(d, 0))
            s['rod'] = st
            s['has_rod'] = bool(d.get('hasRod'))
        if kind == 'control':
            s.update(level=float(d.get('level', 0.0)), target=float(d.get('targetLevel', 0.0)), start=float(d.get('startingLevel', 0.0)))
        if kind == 'outgasser':
            s.update(progress=float(d.get('progress', 0.0)), inputs=_lib.slot_count(d, 0, H + 'billet_th232'))
        seed[n] = s
    return seed


def tank(data, name):
    t = _lib.tanks(data).get(name, {})
    return t.get('fill', 0), t.get('max'), t.get('type')


def charge_of(data):
    """The battery's stored HE (custom data Charge, absent = 0), None without a battery."""
    it = _lib.slot_item(data, 0)
    return None if it is None else custom(it).get('Charge', 0)


def loop_state(ctx):
    b, e, c, r, s = (_lib.block_data(ctx, p) for p in (POS['B'], ENGINE, COND, BARREL, SOCKET))
    out = dict(feed=tank(b, 'feed')[0], bsteam=tank(b, 'steam')[0], es=tank(e, 's')[0], ew=tank(e, 'w')[0], cw=tank(c, 'water')[0],
               cs=tank(c, 'steam')[0], barrel=tank(r, 'tank')[0], charge=charge_of(s))
    out['units'] = out['feed'] + out['barrel'] + out['ew'] + out['cw'] + out['cs']
    out['steam'] = out['bsteam'] + out['es']
    return out


def water_ok(ls):
    return ls['steam'] % 100 == 0 and ls['units'] + ls['steam'] // 100 == BUCKETS * 1000


def open_col(ctx, name, expect):
    p = POS[name]
    face, stand = ('west', [p[0] - 1.5, Y, p[2] + 0.5]) if name == 'O' else ('south', [p[0] + 0.5, Y, p[2] + (1.5 if name == 'ST' else 2.5)])
    return _lib.open_gui(ctx, p, face, stand, expect)


def sneak_use_center(ctx, pos, face, stand):
    """Sneaking right-click aimed at the middle of the block at pos: the held item, not the block, takes the click."""
    _lib.sneak(ctx, True)
    try:
        return _lib.use_center(ctx, pos, face, stand)
    finally:
        _lib.sneak(ctx, False)


def type_run(ctx, duct, face, stand):
    _lib.hold(ctx, H + 'fluid_identifier_multi')
    sneak_use_center(ctx, duct, face, stand)


# crane keys (HbmKeybinds.java:41-45: arrow keys and enter). On each key event the client sends KeyMapping.isDown() of a crane key
# that changed (HbmKeybinds.java:82-85,148-166,189-193); unlike a held attack this needs neither the window focus nor a grabbed mouse.
def crane_hold(ctx, S, key, ticks, label):
    ctx.step('view', pos=S['op_stand'], yaw=180.0, pitch=10.0, fly=False, hide_gui=False)
    ctx.step('key', key=key, action='press', after=4)
    try:
        _lib.advance(ctx, ticks, label)
    finally:
        ctx.step('key', key=key, action='release', after=4)


def crane_load(ctx, S, label):
    """Enter for one server tick (the lift starts down, RBMKCraneConsoleBlockEntity.java:175-177,232-234), released, then 60 ticks:
    25 ticks of -0.04 leave -3.5e-16, the exchange in the 26th tick, 25 ticks up to 1 (:101-125)."""
    crane_hold(ctx, S, 'key.keyboard.enter', 1, label + '-key')
    _lib.still(ctx, ticks=10)
    _lib.advance(ctx, 60, label)
    _lib.still(ctx)


def crane_read(ctx, S):
    d = _lib.block_data(ctx, S['crane'])
    return d, (d.get('held') or {}).get('id')


def open_autoloader(ctx):
    """From the platform: the loader's lower part is a thin shaft (RBMKAutoloaderBlock.java:30-33), so the click aims at the shaft's
    middle one block above the core, at eye height; any part opens the core's screen."""
    return _lib.open_gui(ctx, (AUTOLOADER[0], AUTOLOADER[1] + 1, AUTOLOADER[2]), 'south', ON_PLATFORM, 'RBMKAutoloader', center=True)


def swap_ticks(g):
    """k1: the first tick after game time g whose game time is a multiple of 20 (the autoloader's check, RBMKAutoloaderBlockEntity.java:89)."""
    return next(k for k in range(1, 21) if (g + k) % 20 == 0)


# ---------------------------------------------------------------- sections

def place_ground(ctx, item, cell, stand):
    _lib.place(ctx, item, (cell[0], Y - 1, cell[1]), 'up', stand)


def core_near(ctx, block, x, z, up=3):
    return _lib.core_of(ctx, block, (x - 3, Y, z - 3), (x + 3, Y + up, z + 3))


def section_assembly(ctx, S):
    _lib.give(ctx, *GIVE_ASM)
    _lib.give(ctx, (H + 'machine_wood_burner', 1), ('minecraft:oak_log', 3))
    _lib.cmd(ctx, 'fill %d %d %d %d %d %d hbmsntm:red_cable' % (BURNER_AT[0] - 4, Y - 1, BUS_Z, AX + 2, Y - 1, BUS_Z))   # 命令搭建
    place_ground(ctx, H + 'machine_assembly_machine', (AX, AZ), [AX + 0.5, Y, AZ + 4.5])
    core, _ = core_near(ctx, H + 'machine_assembly_machine', AX, AZ)
    # its power port (x - 2, z) (MachineAssemblyMachineBlockEntity.java:215-234): a riser there and the column down to the bus
    _lib.cmd(ctx, 'setblock %d %d %d hbmsntm:red_cable' % (core[0] - 2, Y, core[2]))                                      # 命令搭建
    _lib.cmd(ctx, 'fill %d %d %d %d %d %d hbmsntm:red_cable' % (core[0] - 2, Y - 1, core[2], core[0] - 2, Y - 1, BUS_Z))   # 命令搭建
    place_ground(ctx, H + 'machine_wood_burner', BURNER_AT, [BURNER_AT[0] + 0.5, Y, BURNER_AT[1] + 3.5])
    burner, props = core_near(ctx, H + 'machine_wood_burner', *BURNER_AT, up=2)
    # its power ports two blocks behind the core (MachineWoodBurnerBlockEntity.java:226-236)
    _lib.cmd(ctx, 'setblock %d %d %d hbmsntm:red_cable' % (burner[0], Y, burner[2] - 2))                                  # 命令搭建
    _lib.cmd(ctx, 'fill %d %d %d %d %d %d hbmsntm:red_cable' % (burner[0], Y - 1, burner[2] - 2, burner[0], Y - 1, BUS_Z))  # 命令搭建
    hud = _lib.open_gui(ctx, burner, 'south', [burner[0] + 0.5, Y, burner[2] + 2.5], 'MachineWoodBurnerScreen')
    _lib.put_stack(ctx, 6, 'minecraft:oak_log', 0)
    ctx.step('click', at=[hud['gui_left'] + 61, hud['gui_top'] + 24], button=0, after=4)
    ctx.step('close')
    if not _lib.block_data(ctx, burner).get('isOn'):
        raise RuntimeError('the wood burner did not switch on')
    face = (core[0], Y, core[2] + 1)
    stand = [face[0] + 0.5, Y, face[2] + 2.5]
    _lib.open_gui(ctx, face, 'south', stand, 'MachineAssemblyMachineScreen')
    got = _lib.pick_recipe(ctx, core, 'hbmAssemblyMachine.json', 'ass.rbmk', 'block.hbmsntm.rbmk_blank')
    ctx.step('close')
    if got != 'ass.rbmk':
        raise RuntimeError('server recipe after the selector: %r' % got)
    park(ctx)
    ctx.server('tick freeze')
    ctx.sprint(4000, until=lambda c: _lib.block_data(c, core).get('power', 0) >= _lib.block_data(c, core).get('maxPower', 100_000),
               poll_s=0.5, label='s9-charge', timeout_s=300)
    _lib.still(ctx)
    # the four stacks shift-clicked in (the selected recipe routes each to its slot); the burner stays on (100 HE/t in, 100 out)
    _lib.open_gui(ctx, face, 'south', stand, 'MachineAssemblyMachineScreen')
    items = _lib.inventory(ctx)
    srcs = [_lib.find_slot(items, H + 'concrete_asbestos'), _lib.find_slot(items, H + 'plate_cast', 11),
            _lib.find_slot(items, H + 'plate_copper'), _lib.find_slot(items, H + 'ingot_rubber')]
    if None in srcs:
        raise _lib.Missing('assembly inputs missing: %s' % srcs)
    for s in srcs:
        _lib.shift_click(ctx, _lib.menu_slot(17, s))
    ctx.step('close')
    t0 = gt(ctx)
    advance_to(ctx, t0, 1099, 's9-blanks')
    d1 = _lib.block_data(ctx, core)
    advance_to(ctx, t0, 1100, 's9-blanks')
    d2 = _lib.block_data(ctx, core)
    _lib.still(ctx)
    left = {s: v for s, v in _lib.items_of(d2).items() if 4 <= s <= 15}
    n1, n2 = _lib.slot_count(d1, 16, H + 'rbmk_blank'), _lib.slot_count(d2, 16, H + 'rbmk_blank')
    ctx.check(eid('rbmk-core', 'assemble'), n1 == 10 and n2 == 11 and not left,
              'tick 1099: %d structural columns in the output (want 10); tick 1100: %d (want 11), inputs left %s; assembler power %s'
              % (n1, n2, left or 'none', d2.get('power')))
    _lib.open_gui(ctx, face, 'south', stand, 'MachineAssemblyMachineScreen')
    _lib.shift_click(ctx, 16)
    got = _lib.pick_recipe(ctx, core, 'hbmAssemblyMachine.json', 'ass.rbmkautoloader', 'block.hbmsntm.rbmk_autoloader')
    ctx.step('close')
    if got != 'ass.rbmkautoloader':
        raise RuntimeError('server recipe after the selector: %r' % got)
    if _lib.count(ctx, H + 'rbmk_blank') != 11:
        raise _lib.Missing('the 11 structural columns did not reach the inventory')
    S['blanks'] = True
    _lib.give(ctx, *GIVE_AUTO)
    _lib.give(ctx, (H + 'plate_welded[hbmsntm:meta=11]', 4))
    _lib.open_gui(ctx, face, 'south', stand, 'MachineAssemblyMachineScreen')
    items = _lib.inventory(ctx)
    srcs = [_lib.find_slot(items, H + 'plate_welded', 11), _lib.find_slot(items, H + 'plate_cast', 8), _lib.find_slot(items, H + 'ingot_boron'),
            _lib.find_slot(items, H + 'motor')]
    if None in srcs:
        raise _lib.Missing('autoloader inputs missing: %s' % srcs)
    for s in srcs:
        _lib.shift_click(ctx, _lib.menu_slot(17, s))
    ctx.step('close')
    t0 = gt(ctx)
    advance_to(ctx, t0, 99, 's9-autoloader')
    d1 = _lib.block_data(ctx, core)
    advance_to(ctx, t0, 100, 's9-autoloader')
    d2 = _lib.block_data(ctx, core)
    _lib.still(ctx)
    o1, o2 = _lib.slot_item(d1, 16), _lib.slot_item(d2, 16)
    left = {s: v for s, v in _lib.items_of(d2).items() if 4 <= s <= 15}
    ctx.check(eid('rbmk-autoloader', 'assemble'), o1 is None and (o2 or {}).get('id') == H + 'rbmk_autoloader' and not left,
              'tick 99 output %s; tick 100 output %s; inputs left %s' % ((o1 or {}).get('id'), (o2 or {}).get('id'), left or 'none'))
    _lib.open_gui(ctx, face, 'south', stand, 'MachineAssemblyMachineScreen')
    _lib.shift_click(ctx, 16)
    ctx.step('close')
    S['autoloader_item'] = _lib.count(ctx, H + 'rbmk_autoloader') == 1


PRODUCTS = {'rbmk_rod': 2, 'rbmk_absorber': 1, 'rbmk_control': 2, 'rbmk_reflector': 1, 'rbmk_moderator': 1, 'rbmk_boiler': 1,
            'rbmk_outgasser': 1, 'rbmk_storage': 1, 'rbmk_console': 1, 'rbmk_crane_console': 1, 'rbmk_tool': 1, 'rbmk_blank': 0,
            'deco_rbmk': 0}


def section_crafting(ctx, S):
    if not S.get('blanks'):
        raise _lib.Missing('no structural columns from section A')
    _lib.give(ctx, *GIVE_COLS)
    _lib.give(ctx, (H + 'ingot_graphite', 4), (H + 'block_graphite', 4))
    _lib.give(ctx, ('minecraft:crafting_table', 1), ('minecraft:hopper', 1), ('minecraft:glass_pane', 1), ('minecraft:iron_ingot', 2))
    place_ground(ctx, 'minecraft:crafting_table', TABLE[::2], [TABLE[0] + 0.5, Y, TABLE[2] + 3.5])
    _lib.open_gui(ctx, TABLE, 'south', [TABLE[0] + 0.5, Y, TABLE[2] + 2.5], 'Crafting')
    b = H + 'rbmk_blank'
    _lib.craft(ctx, ['R'], dict(R=b))
    _lib.craft(ctx, ['C', 'R', 'C'], dict(C=H + 'shell_steel', R=b), times=2)
    _lib.craft(ctx, ['GGG', 'GRG', 'GGG'], dict(G=H + 'ingot_boron', R=b), times=3)
    _lib.craft(ctx, [' B ', 'GRG', ' B '], dict(B=H + 'motor', G=H + 'ingot_graphite', R=H + 'rbmk_absorber'), times=2)
    _lib.craft(ctx, ['GGG', 'GRG', 'GGG'], dict(G=H + 'neutron_reflector', R=b))
    _lib.craft(ctx, [' G ', 'GRG', ' G '], dict(G=H + 'block_graphite', R=b))
    _lib.craft(ctx, ['CPC', 'CRC', 'CPC'], dict(C=H + 'pipe_copper', P=H + 'shell_copper', R=b))
    _lib.craft(ctx, ['GHG', 'GRG', 'GTG'], dict(G=H + 'steel_grate', H='minecraft:hopper', T=H + 'tank_steel', R=b))
    _lib.craft(ctx, ['C', 'R', 'C'], dict(C=H + 'crate_steel', R=b))
    _lib.craft(ctx, ['BBB', 'DGD', 'DCD'], dict(B=H + 'ingot_boron', D=H + 'deco_rbmk', G='minecraft:glass_pane', C=H + 'circuit_analog_board'))
    _lib.craft(ctx, ['BCD', 'DDD'], dict(B=H + 'ingot_boron', C=H + 'circuit_analog_board', D=H + 'deco_rbmk'))
    _lib.craft(ctx, [' A ', ' IA', 'I  '], dict(A=H + 'ingot_lead', I='minecraft:iron_ingot'))
    items = _lib.inventory(ctx)
    got = {k: _lib.count(ctx, H + k, items=items) for k in PRODUCTS}
    rest = {k: _lib.count(ctx, H + k, items=items) for k in ('ingot_boron', 'motor', 'ingot_graphite', 'block_graphite', 'neutron_reflector', 'shell_steel')}
    ok = got == PRODUCTS and not any(rest.values())
    ctx.check(eid('rbmk-core', 'craft-columns'), ok, 'products %s (want %s); left over %s (want all 0)' % (got, PRODUCTS, rest))
    S['columns'] = all(got[k] >= v for k, v in PRODUCTS.items())

    _lib.give(ctx, *GIVE_RIG)
    _lib.give(ctx, ('minecraft:blue_dye', 2))
    _lib.craft(ctx, ['D', 'C', 'P'], dict(D='minecraft:blue_dye', C=H + 'circuit_vacuum_tube', P=H + 'plate_iron'), times=2)
    _lib.craft(ctx, ['IPI', 'I I', 'IPI'], dict(I=H + 'plate_steel', P=H + 'ingot_steel'))
    _lib.craft(ctx, ['SIS', 'ICI', 'SIS'], dict(S=H + 'ingot_steel', I=H + 'plate_iron', C=(H + 'plate_cast', 5)))
    _lib.craft(ctx, ['ABA'], dict(A=H + 'plate_steel', B=H + 'ingot_red_copper'))
    ctx.step('close')
    items = _lib.inventory(ctx)
    rig = {k: _lib.count(ctx, H + k, items=items) for k in ('fluid_identifier_multi', 'barrel_steel', 'machine_condenser', 'machine_battery_socket')}
    if rig != {'fluid_identifier_multi': 2, 'barrel_steel': 1, 'machine_condenser': 1, 'machine_battery_socket': 1}:
        raise RuntimeError('rig parts: %s' % rig)
    S['rig_parts'] = True


def place_column(ctx, name, block):
    p = POS[name]
    _lib.place(ctx, H + block, (p[0], Y - 1, p[2]), 'up', PLACE_FROM[name])
    d = _lib.block_data(ctx, p)
    if 'heat' not in d:
        raise RuntimeError('%s: no column core at %s (%s)' % (name, p, d.get('id')))


def section_build(ctx, S):
    """Survival: every block placed by hand, before any radioactive fuel exists."""
    if not (S.get('columns') and S.get('rig_parts') and S.get('autoloader_item')):
        raise _lib.Missing('parts from sections A or C are missing')
    for n, _, block, _ in COLS:
        place_column(ctx, n, block)

    # ---- steam side
    _lib.give(ctx, (H + 'machine_steam_engine', 1), (H + 'battery_pack', 1), ('minecraft:water_bucket', BUCKETS))
    _lib.place(ctx, H + 'machine_steam_engine', (ENGINE[0], Y - 1, ENGINE[2] - 1), 'up', [ENGINE[0] + 0.5, Y, ENGINE[2] - 4.5])
    core, props = _lib.core_of(ctx, H + 'machine_steam_engine', (X0 + 4, Y, Z0 - 6), (X0 + 8, Y + 1, Z0 + 2))
    if core != ENGINE or props.get('facing') != 'north':
        raise RuntimeError('steam engine core %s facing %s, planned %s north' % (core, props.get('facing'), ENGINE))
    _lib.cmd(ctx, 'setblock %d %d %d minecraft:stone' % SUPPORT)        # 命令搭建
    _lib.place(ctx, H + 'machine_condenser', SUPPORT, 'up', [SUPPORT[0] + 0.5, Y, SUPPORT[2] - 2.5])
    _lib.place(ctx, H + 'machine_battery_socket', (SOCKET[0], Y - 1, SOCKET[2]), 'up', [SOCKET[0] + 0.5, Y, SOCKET[2] + 3.5])
    score, sprops = _lib.core_of(ctx, H + 'machine_battery_socket', (SOCKET[0] - 2, Y, SOCKET[2] - 2), (SOCKET[0] + 2, Y + 1, SOCKET[2] + 2))
    if score != SOCKET or sprops.get('facing') != 'south':
        raise RuntimeError('socket core %s facing %s, planned %s south' % (score, sprops.get('facing'), SOCKET))
    _lib.open_gui(ctx, SOCKET, 'east', [SOCKET[0] + 2.5, Y, SOCKET[2] + 0.5], 'BatterySocket')
    _lib.put_stack(ctx, 1, H + 'battery_pack', 0)
    ctx.step('close')
    _lib.place(ctx, H + 'barrel_steel', (BARREL[0], Y - 1, BARREL[2]), 'up', [BARREL[0] + 0.5, Y, BARREL[2] - 2.5])
    for p in (COND, BARREL):
        if 'id' not in _lib.block_data(ctx, p):
            raise RuntimeError('nothing placed at %s' % (p,))
    for p in STEAM_DUCTS + WATER_DUCTS:                             # 命令搭建
        _lib.cmd(ctx, 'setblock %d %d %d hbmsntm:fluid_duct_neo' % p)
    for p in CABLES:                                                # 命令搭建
        _lib.cmd(ctx, 'setblock %d %d %d hbmsntm:red_cable' % p)
    _lib.pick_fluid(ctx, WATER_IDX, PARK)
    type_run(ctx, WATER_DUCTS[0], 'north', [WATER_DUCTS[0][0] + 0.5, Y, WATER_DUCTS[0][2] - 2.5])
    # the barrel: one identifier (water) into slot 0, mode button twice (receive -> buffer -> send), 4 buckets one tick each
    _lib.open_gui(ctx, BARREL, 'north', [BARREL[0] + 0.5, Y, BARREL[2] - 2.5], 'Barrel')
    _lib.put_n(ctx, 6, H + 'fluid_identifier_multi', [0], 1)
    hud = ctx.step('hud', frames=2)
    for _ in range(2):
        ctx.step('click', at=[hud['gui_left'] + 160, hud['gui_top'] + 43], after=4)
    _lib.server_steps(ctx, 1)
    for _ in range(BUCKETS):
        _lib.put_stack(ctx, 6, 'minecraft:water_bucket', 2)
        _lib.server_steps(ctx, 1)
    ctx.step('close')
    _lib.pick_fluid(ctx, STEAM_IDX, PARK)
    sd = STEAM_DUCTS[9]
    type_run(ctx, sd, 'east', [sd[0] + 2.5, Y, sd[2] + 0.5])
    _lib.server_steps(ctx, 5)
    _lib.still(ctx)
    wt = [_lib.block_data(ctx, p).get('Type') for p in WATER_DUCTS]
    st = [_lib.block_data(ctx, p).get('Type') for p in STEAM_DUCTS]
    bd = _lib.block_data(ctx, BARREL)
    ls = loop_state(ctx)
    ok = (all(t == WATER_ID for t in wt) and all(t == STEAM_ID for t in st) and bd.get('mode') == 2 and tank(bd, 'tank')[2] == WATER_ID
          and ls['feed'] + ls['barrel'] == BUCKETS * 1000 and ls['charge'] is not None)
    ctx.check(eid('rbmk-steam', 'rig'), ok, '%d water ducts types %s (want %d); %d steam ducts types %s (want %d); barrel mode %s type %s; '
              'barrel %d + boiler feed %d = %d (want %d); battery charge %s'
              % (len(wt), sorted(set(wt), key=str), WATER_ID, len(st), sorted(set(st), key=str), STEAM_ID, bd.get('mode'),
                 tank(bd, 'tank')[2], ls['barrel'], ls['feed'], ls['barrel'] + ls['feed'], BUCKETS * 1000, ls['charge']))
    S['steam_rig'] = ok

    # ---- consoles: the linking device on F, then on each console (sneaking: the item, not the block, takes the click)
    for cell in BLOCKERS:                                           # 命令搭建: girder-level stops
        _lib.cmd(ctx, 'setblock %d %d %d minecraft:stone' % cell)
    _lib.place(ctx, H + 'rbmk_console', (CONSOLE_CELL[0], Y - 1, CONSOLE_CELL[2]), 'up', [CONSOLE_CELL[0] + 0.5, Y, CONSOLE_CELL[2] + 3.5])
    con, cprops = _lib.core_of(ctx, H + 'rbmk_console', (X0 - 11, Y, Z0 + 4), (X0 - 5, Y + 4, Z0 + 11))
    _lib.place(ctx, H + 'rbmk_crane_console', (CRANE_CELL[0], Y - 1, CRANE_CELL[2]), 'up', [CRANE_CELL[0] + 0.5, Y, CRANE_CELL[2] + 3.5])
    crane, kprops = _lib.core_of(ctx, H + 'rbmk_crane_console', (X0 - 2, Y, Z0 + 4), (X0 + 2, Y + 2, Z0 + 11))
    if kprops.get('facing') != 'south':
        raise RuntimeError('crane console facing %s, planned south' % kprops.get('facing'))
    S['console'], S['crane'] = con, crane
    S['op_stand'] = [crane[0] + 0.5, Y, crane[2] + 0.5 + 1.85]    # inside the operator box (RBMKCraneConsoleBlockEntity.java:140-154)
    _lib.hold(ctx, H + 'rbmk_tool')
    _lib.use_on(ctx, POS['F'], 'south', [X0 + 0.5, Y, Z0 + 1.6], crouch=True)
    sneak_use_center(ctx, (con[0], Y + 1, con[2]), 'south', [con[0] + 0.5, Y, con[2] + 3.0])
    _lib.hold(ctx, H + 'rbmk_tool')
    sneak_use_center(ctx, (crane[0], Y + 1, crane[2]), 'south', [crane[0] + 0.5, Y, crane[2] + 3.0])
    _lib.still(ctx, ticks=20)
    cd = _lib.block_data(ctx, con)
    kd, held = crane_read(ctx, S)
    S['console_ok'] = (cd.get('tX'), cd.get('tY'), cd.get('tZ')) == POS['F']
    want = dict(crane=1, centerX=X0, centerY=TOP + 1, centerZ=Z0, spanF=0, spanB=2)
    got = {k: (int(kd.get(k)) if isinstance(kd.get(k), (bool, int)) else kd.get(k)) for k in want}
    ok = got == want
    ctx.check(eid('rbmk-crane', 'link'), ok, 'crane console core %s facing %s: %s (want %s), spanL %s spanR %s; RBMK console core %s target %s'
              % (crane, kprops.get('facing'), got, want, kd.get('spanL'), kd.get('spanR'), con, (cd.get('tX'), cd.get('tY'), cd.get('tZ'))))
    if not ok:
        raise RuntimeError('the crane is not linked as planned')

    # ---- autoloader on S: from the stone the player stands on; cycle 50 -> 40 (minus button GUI 74,36, 12 x 12,
    # RBMKAutoloaderScreen.java:42-51; RBMKAutoloaderBlockEntity.java:309-314)
    _lib.cmd(ctx, 'setblock %d %d %d minecraft:stone' % PLATFORM)         # 命令搭建
    _lib.hold(ctx, H + 'rbmk_autoloader')
    _lib.use_on(ctx, (POS['S'][0], TOP, POS['S'][2]), 'up', ON_PLATFORM, crouch=True)
    if 'piston' not in _lib.block_data(ctx, AUTOLOADER):
        raise RuntimeError('no autoloader at %s' % (AUTOLOADER,))
    hud = open_autoloader(ctx)
    for _ in range(2):
        ctx.step('click', at=[hud['gui_left'] + 80, hud['gui_top'] + 42], after=4)
    ctx.step('close')
    if _lib.block_data(ctx, AUTOLOADER).get('cycle') != 40:
        raise RuntimeError('autoloader cycle %s, wanted 40' % _lib.block_data(ctx, AUTOLOADER).get('cycle'))

    # ---- waste drum (a water source under it) and the chest for the pellets
    _lib.give(ctx, *GIVE_LINE)
    _lib.give(ctx, ('minecraft:chest', 1))
    place_ground(ctx, H + 'machine_waste_drum', DRUM[::2], [DRUM[0] + 0.5, Y, DRUM[2] + 3.5])
    _lib.cmd(ctx, 'setblock %d %d %d minecraft:water' % (DRUM[0], Y - 1, DRUM[2]))    # 命令搭建
    place_ground(ctx, 'minecraft:chest', CHEST[::2], [CHEST[0] + 0.5, Y, CHEST[2] + 3.5])
    for p in (DRUM, CHEST):
        if 'id' not in _lib.block_data(ctx, p):
            raise RuntimeError('nothing placed at %s' % (p,))
    clear_hotbar(ctx)
    S['placed'] = True


def clear_hotbar(ctx):
    """Survival inventory screen: every hotbar stack shift-clicked into the main inventory (InventoryMenu hotbar slots 36-44), so
    that in creative, where the inventory key opens the creative screen, a free hotbar slot for an empty hand is always found
    with the number keys alone."""
    items = _lib.inventory(ctx)
    used = [s for s in range(9) if s in items]
    if not used:
        return
    ctx.step('key', key='key.keyboard.e', action='tap', after=4)
    ctx.step('screen', expect='InventoryScreen')
    for s in used:
        _lib.shift_click(ctx, 36 + s)
    ctx.step('close')
    left = [s for s in range(9) if s in _lib.inventory(ctx)]
    if left:
        raise RuntimeError('hotbar slots still used: %s' % left)


def section_fuel(ctx, S):
    """Creative from here on (see the docstring): the fuel rods, the loading of the irradiation channel, the storage column and the
    autoloader, and the crane run from the storage column into F."""
    if not S.get('placed'):
        raise _lib.Missing('the reactor was not placed')
    _lib.cmd(ctx, 'gamemode creative')                                   # 命令搭建
    _lib.give(ctx, *GIVE_FUEL[:4])
    items = _lib.inventory(ctx)
    if sum(1 for s in range(9) if s not in items) < 3:
        raise RuntimeError('fewer than three free hotbar slots for the creative part: %s' % sorted(items))
    _lib.open_gui(ctx, TABLE, 'south', [TABLE[0] + 0.5, Y, TABLE[2] + 2.5], 'Crafting')
    _lib.craft(ctx, ['ZRZ', 'Z Z', 'ZRZ'], dict(Z=H + 'ingot_zirconium', R=H + 'rod_quad_empty'), times=4)
    empties = _lib.count(ctx, H + 'rbmk_fuel_empty')
    _lib.craft(ctx, ['EBB', 'BBB', 'BBB'], dict(E=H + 'rbmk_fuel_empty', B=H + 'billet_uranium_fuel'), times=3)
    _lib.craft(ctx, ['EBB', 'BBB', 'BBB'], dict(E=H + 'rbmk_fuel_empty', B=H + 'billet_ra226be'))
    ctx.step('close')
    items = _lib.inventory(ctx)
    rods = {k: [e for e in items.values() if e['id'] == k] for k in (MEU, RA)}
    fresh = all(e['count'] == 1 and not custom(dict(components=e['components'])) for v in rods.values() for e in v)
    rest = {k: _lib.count(ctx, H + k, items=items) for k in ('ingot_zirconium', 'rod_quad_empty', 'billet_uranium_fuel', 'billet_ra226be', 'rbmk_fuel_empty')}
    ok = empties == 4 and len(rods[MEU]) == 3 and len(rods[RA]) == 1 and fresh and not any(rest.values())
    ctx.check(eid('rbmk-fuel', 'craft-rods'), ok,
              'empty rods after 4 crafts: %d (want 4); MEU rods %d (want 3), Ra226Be rods %d (want 1), custom data %s (want none); left over %s '
              '(want 0)' % (empties, len(rods[MEU]), len(rods[RA]), [custom(dict(components=e['components'])) for v in rods.values() for e in v], rest))
    if len(rods[MEU]) < 3 or not rods[RA]:
        raise RuntimeError('rods missing for the line')

    _lib.give(ctx, GIVE_FUEL[4])
    open_col(ctx, 'O', 'RBMKOutgasser')
    _lib.put_stack(ctx, 2, H + 'billet_th232', 0)
    ctx.step('close')
    open_col(ctx, 'ST', 'RBMKStorage')
    _lib.put_stack(ctx, 12, MEU, 0)
    ctx.step('close')

    # ---- autoloader: the Ra226Be rod into slot 0, the two spare MEU rods into slots 1 and 2
    open_autoloader(ctx)
    _lib.put_stack(ctx, 18, RA, 0)
    _lib.put_stack(ctx, 18, MEU, 1)
    _lib.put_stack(ctx, 18, MEU, 2)
    ctx.step('close')
    g = gt(ctx)
    k1 = swap_ticks(g)
    ad0 = _lib.block_data(ctx, AUTOLOADER)
    advance_to(ctx, g, k1 + 198, 's9-autoloader-swap')
    s1, a1 = _lib.block_data(ctx, POS['S']), _lib.block_data(ctx, AUTOLOADER)
    advance_to(ctx, g, k1 + 199, 's9-autoloader-swap')
    s2, a2 = _lib.block_data(ctx, POS['S']), _lib.block_data(ctx, AUTOLOADER)
    i1, i2 = (_lib.slot_item(s1, 0) or {}).get('id'), (_lib.slot_item(s2, 0) or {}).get('id')
    loader0 = {s: v['id'] for s, v in _lib.items_of(ad0).items()}
    loader2 = {s: v['id'] for s, v in _lib.items_of(a2).items()}
    ok = (ad0.get('cycle') == 40 and loader0 == {0: RA, 1: MEU, 2: MEU} and i1 is None and i2 == RA and loader2 == {1: MEU, 2: MEU}
          and a2.get('piston') == 1.0 and a1.get('piston', 1) < 1)
    ctx.check(eid('rbmk-autoloader', 'swap'), ok, 'cycle %s, slots %s at game time %d; k1 = %d; tick k1+198: S %s, piston %s; tick k1+199: '
              'S %s, piston %s, loader slots %s' % (ad0.get('cycle'), loader0, g, k1, i1, a1.get('piston'), i2, a2.get('piston'), loader2))
    if i2 != RA:
        raise RuntimeError('S was not loaded')
    S['autoloader'] = True

    # ---- crane: storage -> F
    crane_hold(ctx, S, 'key.keyboard.down', 45, 's9-crane-back')
    _lib.still(ctx, ticks=10)
    k1d, _ = crane_read(ctx, S)
    crane_load(ctx, S, 's9-crane-lift1')
    k2d, h2 = crane_read(ctx, S)
    crane_hold(ctx, S, 'key.keyboard.up', 45, 's9-crane-front')
    _lib.still(ctx, ticks=10)
    k3d, _ = crane_read(ctx, S)
    crane_load(ctx, S, 's9-crane-lift2')
    k4d, h4 = crane_read(ctx, S)
    f, st = _lib.block_data(ctx, POS['F']), _lib.block_data(ctx, POS['ST'])
    fi = (_lib.slot_item(f, 0) or {}).get('id')
    ok = (k1d.get('posFront') == -2.0 and h2 == MEU and k3d.get('posFront') == 0.0 and h4 is None and fi == MEU and not st.get('Items'))
    ctx.check(eid('rbmk-crane', 'load-f'), ok, 'after holding down: posFront %s (want -2.0); after the first enter: held %s (want %s); '
              'after holding up: posFront %s (want 0.0); after the second enter: held %s, F slot 0 %s, storage items %s'
              % (k1d.get('posFront'), h2, MEU, k3d.get('posFront'), h4, fi, st.get('Items') or 'none'))
    if fi != MEU:
        raise RuntimeError('F was not loaded by the crane')
    S['built'] = True


def section_run(ctx, S):
    if not S.get('built'):
        raise _lib.Missing('the reactor was not built')
    _lib.still(ctx)
    # control rods: 100 % (GUI 118,26, 30 x 10) and colour 2 (GUI 28,48, 12 x 10) in each screen (RBMKControlScreen.java:45-71)
    for n in ('C1', 'C2'):
        hud = open_col(ctx, n, 'RBMKControl')
        ctx.step('click', at=[hud['gui_left'] + 133, hud['gui_top'] + 31], after=4)
        ctx.step('click', at=[hud['gui_left'] + 34, hud['gui_top'] + 31 + 2 * 11], after=4)
        ctx.step('close')
    _lib.still(ctx, ticks=20)
    g0 = gt(ctx)
    data = column_data(ctx)
    seed = seed_from(data)
    if (seed['C1']['target'], seed['C2']['target']) != (1.0, 1.0) or seed['F']['rod'] is None or seed['S']['rod'] is None:
        raise RuntimeError('start state: targets %s / %s, F %s, S %s' % (seed['C1']['target'], seed['C2']['target'], seed['F']['rod'], seed['S']['rod']))
    colours = (data['C1'].get('color'), data['C2'].get('color'))
    sim = Sim(seed)
    snaps, prev, ts, te = {}, sim.snap(), None, None
    while te is None and sim.t < 90_000:
        sim.step()
        cur = sim.snap()
        if sim.t in (361, 362):
            snaps[sim.t] = cur
        if ts is None and sim.W > 0:
            ts = sim.t
            snaps[ts - 1], snaps[ts] = prev, cur
        if ts is not None and sim.t == ts + 2000:
            snaps[sim.t] = cur
        if sim.by['F'].rod.enrichment() <= ENRICH_LIMIT:
            te = sim.t
            snaps[te - 1], snaps[te] = prev, cur
        prev = cur
    if ts is None or te is None or te <= ts + 2000:
        raise RuntimeError('simulation: first steam %s, enrichment limit %s' % (ts, te))
    S.update(ts=ts, te=te)

    lv = {}
    for k in (361, 362):
        advance_to(ctx, g0, k, 's9-raise')
        lv[k] = tuple(_lib.block_data(ctx, POS[n]).get('level') for n in ('C1', 'C2'))
    ok = lv[361][0] < 1 and lv[361][1] < 1 and lv[362] == (1.0, 1.0) and snaps[362]['levels'] == (1.0, 1.0) and colours == (2, 2)
    ctx.check(eid('rbmk-control', 'raise'), ok, 'levels tick 361 %s, tick 362 %s (simulated %s / %s); colours %s'
              % (lv[361], lv[362], snaps[361]['levels'], snaps[362]['levels'], colours))

    advance_to(ctx, g0, ts - 1, 's9-warmup')
    _lib.still(ctx)
    w1 = loop_state(ctx)
    advance_to(ctx, g0, ts, 's9-warmup')
    _lib.still(ctx)
    w2 = loop_state(ctx)
    want = 100 * snaps[ts]['w']
    ok = w1['steam'] == 0 and not w1['charge'] and w2['steam'] + 100 * (w2['ew'] + w2['cw'] + w2['cs']) == want > 0
    ctx.check(eid('rbmk-reactor', 'warmup'), ok, 'simulated first steam at tick %d (water %d mB); tick %d: boiler + engine steam %d, battery %s; '
              'tick %d: steam %d + 100 x spent/water in engine and condenser %d = %d (want %d)'
              % (ts, snaps[ts]['w'], ts - 1, w1['steam'], w1['charge'], ts, w2['steam'], 100 * (w2['ew'] + w2['cw'] + w2['cs']),
                 w2['steam'] + 100 * (w2['ew'] + w2['cw'] + w2['cs']), want))

    tp = ts + 2000
    advance_to(ctx, g0, tp, 's9-power')
    _lib.still(ctx)
    data, ls, sp = column_data(ctx), loop_state(ctx), snaps[tp]
    off = {n: (data[n].get('heat'), sp['heat'][n]) for n in sp['heat'] if not close(data[n].get('heat'), sp['heat'][n])}
    ctx.check(eid('rbmk-core', 'heat-field'), not off, 'tick %d: column heats %s; differing from the simulation: %s'
              % (tp, {n: round(data[n].get('heat', 0), 6) for n in sp['heat']}, off or 'none'))
    qf, qs = data['F'].get('fluxQuantity'), data['S'].get('fluxQuantity')
    ctx.check(eid('rbmk-reactor', 'flux'), close(qf, sp['qF']) and close(qs, sp['qS']) and sp['qF'] > 0,
              'tick %d: F fluxQuantity %r (simulated %r), S %r (simulated %r)' % (tp, qf, sp['qF'], qs, sp['qS']))
    ops = sp['W'] - ls['steam'] // 100
    ok = ls['steam'] % 100 == 0 and ls['charge'] == OP_HE * ops and ops > 0 and ls['charge'] < 1_800_000
    ctx.check(eid('rbmk-steam', 'power'), ok, 'tick %d: simulated water boiled %d mB, steam left %d (boiler %d + engine %d) -> %d engine '
              'operations; battery %s HE (want %d x %d = %d)' % (tp, sp['W'], ls['steam'], ls['bsteam'], ls['es'], ops, ls['charge'], OP_HE, ops,
                                                               OP_HE * ops))
    og1 = data['O']
    loop1 = ls

    advance_to(ctx, g0, te - 1, 's9-burn')
    f1 = rod_state(_lib.slot_item(_lib.block_data(ctx, POS['F']), 0))
    advance_to(ctx, g0, te, 's9-burn')
    _lib.still(ctx)
    data, ls = column_data(ctx), loop_state(ctx)
    f2 = rod_state(_lib.slot_item(data['F'], 0))
    se = snaps[te]
    ok = (f1 and f2 and f1[1] / 1e8 > ENRICH_LIMIT >= f2[1] / 1e8 and close(f1[1], snaps[te - 1]['F'][0]) and close(f2[1], se['F'][0])
          and close(f2[2], se['F'][1]) and close(f2[3], se['F'][2]) and close(f2[4], se['F'][3]))
    ctx.check(eid('rbmk-fuel', 'burnup'), ok, 'simulated limit tick %d; tick %d F yield %r (sim %r); tick %d yield %r (sim %r), xenon %r (sim %r), '
              'core %r (sim %r), hull %r (sim %r)' % (te, te - 1, f1 and f1[1], snaps[te - 1]['F'][0], te, f2 and f2[1], se['F'][0], f2 and f2[2],
                                                      se['F'][1], f2 and f2[3], se['F'][2], f2 and f2[4], se['F'][3]))
    ctx.check(eid('rbmk-steam', 'loop'), water_ok(loop1) and water_ok(ls) and loop1['feed'] > 0 and ls['feed'] > 0,
              'water units at tick %d: %d + steam %d / 100 = %d; at tick %d: %d + %d / 100 = %d (want %d); feed %d / %d'
              % (tp, loop1['units'], loop1['steam'], loop1['units'] + loop1['steam'] // 100, te, ls['units'], ls['steam'],
                 ls['units'] + ls['steam'] // 100, BUCKETS * 1000, loop1['feed'], ls['feed']))
    og2 = data['O']

    def og(d):
        return (_lib.slot_count(d, 1, H + 'billet_thorium_fuel'), _lib.slot_count(d, 0, H + 'billet_th232'), d.get('progress'))
    o1, o2 = og(og1), og(og2)
    ok = (o1[0] == sp['og'][0] and o1[1] == TH_BILLETS - sp['og'][0] and close(o1[2], sp['og'][1]) and o2[0] == se['og'][0]
          and o2[1] == TH_BILLETS - se['og'][0] and close(o2[2], se['og'][1]) and se['og'][0] > 0)
    ctx.check(eid('rbmk-outgasser', 'irradiate'), ok, '(thorium fuel billets, thorium-232 left, progress): tick %d %s (simulated %d done, '
              'progress %r); tick %d %s (simulated %d, %r)' % (tp, o1, sp['og'][0], sp['og'][1], te, o2, se['og'][0], se['og'][1]))

    # AZ-5 on the console: lid, then the button (GUI 30,138, 28 x 28; RBMKConsoleScreen.java:275-291)
    con = S['console']
    hud = _lib.open_gui(ctx, (con[0], Y + 1, con[2]), 'south', [con[0] + 0.5, Y, con[2] + 3.0], 'RBMKConsole', center=True)
    for _ in range(2):
        ctx.step('click', at=[hud['gui_left'] + 44, hud['gui_top'] + 152], after=6)
    ctx.step('close')
    _lib.still(ctx, ticks=20)
    g1 = gt(ctx)
    c0 = {n: _lib.block_data(ctx, POS[n]) for n in ('C1', 'C2')}
    tg = {n: (d.get('targetLevel'), d.get('startingLevel'), d.get('level')) for n, d in c0.items()}
    level, k0 = c0['C1'].get('level', 0.0), 0
    while level > 0.0:
        level -= CTRL_SPEED
        if level < 0.0:
            level = 0.0
        k0 += 1
    advance_to(ctx, g1, k0 - 1, 's9-az5')
    l1 = tuple(_lib.block_data(ctx, POS[n]).get('level') for n in ('C1', 'C2'))
    advance_to(ctx, g1, k0, 's9-az5')
    l2 = tuple(_lib.block_data(ctx, POS[n]).get('level') for n in ('C1', 'C2'))
    ok = S.get('console_ok') and all(v[0] == 0.0 and v[1] == 1.0 for v in tg.values()) and l1[0] > 0 and l1[1] > 0 and l2 == (0.0, 0.0)
    ctx.check(eid('rbmk-console', 'az5'), ok, 'console linked to F: %s; after AZ-5 (target, startingLevel, level): %s; k0 = %d; '
              'tick k0-1 levels %s, tick k0 %s' % (S.get('console_ok'), tg, k0, l1, l2))

    # crane: F -> storage
    crane_load(ctx, S, 's9-crane-lift3')
    k5d, h5 = crane_read(ctx, S)
    f_after = _lib.slot_item(_lib.block_data(ctx, POS['F']), 0)
    crane_hold(ctx, S, 'key.keyboard.down', 45, 's9-crane-back2')
    _lib.still(ctx, ticks=10)

    def passes(a, b):
        return sum(1 for t in range(a + 1, b + 1) if t % 10 == 0)
    g_in = gt(ctx)
    crane_load(ctx, S, 's9-crane-lift4')
    k6d, h6 = crane_read(ctx, S)
    sd = _lib.block_data(ctx, POS['ST'])
    slots = {s: v['id'] for s, v in _lib.items_of(sd).items()}
    g2 = gt(ctx)
    # enter tick t1 = g_in + 1, the exchange 26 ticks later; the storage column ticks before the crane console (placed earlier)
    gx = g_in + 1 + 26
    s_want = 11 - passes(gx, g2)
    ok = (h5 == MEU and f_after is None and h6 is None and slots == {s_want: MEU} and k6d.get('posFront') == -2.0
          and g2 - g_in == 61)
    ctx.check(eid('rbmk-crane', 'unload-f'), ok, 'after enter over F: held %s, F slot 0 %s; after down + enter: held %s, posFront %s, storage %s '
              '(enter at game time %d, exchange %d, read at %d = enter + %d: want slot 11 - %d passes = %d)'
              % (h5, (f_after or {}).get('id'), h6, k6d.get('posFront'), slots, g_in + 1, gx, g2, g2 - g_in - 1, passes(gx, g2), s_want))
    if not slots:
        raise RuntimeError('the rod is not in the storage column')
    s0 = min(slots)
    # one pass moves the rod one slot, so it reaches slot 0 on pass s0 and stays: the readings after s0 - 1 passes (slot 1) and
    # after s0 passes (slot 0) tell exactly s0 passes from s0 - 1 or from one more
    reads = []
    for n in sorted({5, s0 - 1, s0} - {0}):
        dn = next(d for d in range(1, 200) if passes(g2, g2 + d) == n)
        advance_to(ctx, g2, dn, 's9-storage')
        reads.append((n, dn, sorted(_lib.items_of(_lib.block_data(ctx, POS['ST'])))))
    ok = bool(reads) and all(m == [max(s0 - n, 0)] for n, _, m in reads) and reads[-1][2] == [0]
    ctx.check(eid('rbmk-storage', 'shift'), ok, 'rod in slot %d at game time %d; %s' % (
        s0, g2, '; '.join('after %d passes (tick +%d) slot %s (want %d)' % (n, dn, m, max(s0 - n, 0)) for n, dn, m in reads)))
    S['spent_in_storage'] = bool(reads) and reads[-1][2] == [0]


def section_recycle(ctx, S):
    if not S.get('spent_in_storage'):
        raise _lib.Missing('the spent rod is not in the storage column')
    open_col(ctx, 'ST', 'RBMKStorage')
    _lib.shift_click(ctx, 0)
    ctx.step('close')
    _lib.open_gui(ctx, DRUM, 'south', [DRUM[0] + 0.5, Y, DRUM[2] + 2.5], 'WasteDrum')
    _lib.put_stack(ctx, 12, MEU, 0)
    ctx.step('close')
    _lib.still(ctx, ticks=20)
    g = gt(ctx)
    st = rod_state(_lib.slot_item(_lib.block_data(ctx, DRUM), 0))
    if st is None:
        raise RuntimeError('no rod in the drum')
    rod, tc, prev = Rod(*st), 0, None
    while not (rod.core < 50 and rod.hull < 50):
        prev = (rod.core, rod.hull)
        rod.update_heat(0.025)
        rod.provide(20.0, 0.025)
        tc += 1
    advance_to(ctx, g, tc - 1, 's9-drum')
    r1 = rod_state(_lib.slot_item(_lib.block_data(ctx, DRUM), 0))
    advance_to(ctx, g, tc, 's9-drum')
    r2 = rod_state(_lib.slot_item(_lib.block_data(ctx, DRUM), 0))
    ok = (r1 and r2 and not (r1[3] < 50 and r1[4] < 50) and r2[3] < 50 and r2[4] < 50 and close(r1[3], prev[0]) and close(r1[4], prev[1])
          and close(r2[3], rod.core) and close(r2[4], rod.hull))
    ctx.check(eid('rbmk-recycling', 'drum'), ok, 'rod in at game time %d: core %r hull %r; simulated Tc = %d; tick Tc-1 core %r hull %r (sim %r); '
              'tick Tc core %r hull %r (sim %r, %r)' % (g, st[3], st[4], tc, r1 and r1[3], r1 and r1[4], prev, r2 and r2[3], r2 and r2[4],
                                                        rod.core, rod.hull))
    _lib.still(ctx)
    _lib.open_gui(ctx, DRUM, 'south', [DRUM[0] + 0.5, Y, DRUM[2] + 2.5], 'WasteDrum')
    _lib.shift_click(ctx, 0)
    ctx.step('close')
    before = _lib.inventory_counts(ctx)
    e = r2[1] / 1e8 if r2 else 1.0
    meta = 4 - min(max(int(math.ceil(e * 5 - 1)), 0), 4) + (5 if r2 and r2[2] >= 50 else 0)
    _lib.open_gui(ctx, TABLE, 'south', [TABLE[0] + 0.5, Y, TABLE[2] + 2.5], 'Crafting')
    _lib.craft(ctx, ['R'], dict(R=MEU))
    ctx.step('close')
    dl = _lib.delta(_lib.inventory_counts(ctx), before)
    pel = H + 'rbmk_pellet_meu' + ('@%d' % meta if meta else '')
    _lib.open_gui(ctx, CHEST, 'south', [CHEST[0] + 0.5, Y, CHEST[2] + 2.5], 'Container')
    _lib.put_stack(ctx, 27, H + 'rbmk_pellet_meu', 0)
    ctx.step('close')
    chest = {s: (v['id'], v['count'], v['meta']) for s, v in _lib.items_of(_lib.block_data(ctx, CHEST)).items()}
    ok = meta == 0 and dl == {pel: 8, MEU: -1, H + 'rbmk_fuel_empty': 1} and chest == {0: (H + 'rbmk_pellet_meu', 8, 0)}
    ctx.check(eid('rbmk-recycling', 'pellets'), ok, 'enrichment %r -> meta %d; inventory change %s (want %s +8, %s -1, empty rod +1); chest %s'
              % (e, meta, dl, pel, MEU, chest))
    # the drum's own static store: the empty rod given back + 8 MEU billets (stage-9 start items) -> a fresh MEU rod at 20 / 20,
    # which the drum's cooling leaves unchanged (MachineWasteDrumBlockEntity.java:63-70; original TileEntityWasteDrum.java:212-216)
    _lib.give(ctx, (H + 'billet_uranium_fuel', 8))
    _lib.open_gui(ctx, TABLE, 'south', [TABLE[0] + 0.5, Y, TABLE[2] + 2.5], 'Crafting')
    _lib.craft(ctx, ['EBB', 'BBB', 'BBB'], dict(E=H + 'rbmk_fuel_empty', B=H + 'billet_uranium_fuel'))
    ctx.step('close')
    _lib.open_gui(ctx, DRUM, 'south', [DRUM[0] + 0.5, Y, DRUM[2] + 2.5], 'WasteDrum')
    _lib.put_stack(ctx, 12, MEU, 0)
    ctx.step('close')
    kept = rod_state(_lib.slot_item(_lib.block_data(ctx, DRUM), 0))
    if kept != (MEU, 1e8, 0.0, 20.0, 20.0):
        raise RuntimeError('the fresh MEU rod for the drum: %s' % (kept,))
    S['recycled'] = True


def section_rest(ctx, S):
    """The Ra226Be rod out of S by hand (hull <= 200, RBMKRodBlockEntity.java:94-99) into the storage column; the autoloader then
    refills the empty channel with its first spare rod and keeps the second; the line comes to rest."""
    open_col(ctx, 'S', 'RBMKRod')
    _lib.shift_click(ctx, 0)
    ctx.step('close')
    open_col(ctx, 'ST', 'RBMKStorage')
    _lib.put_stack(ctx, 12, RA, 0)
    ctx.step('close')
    _lib.still(ctx, ticks=10)
    g = gt(ctx)
    k1 = swap_ticks(g)
    a0 = {s: v['id'] for s, v in _lib.items_of(_lib.block_data(ctx, AUTOLOADER)).items()}
    s0 = (_lib.slot_item(_lib.block_data(ctx, POS['S']), 0) or {}).get('id')
    advance_to(ctx, g, k1 + 198, 's9-refill')
    s1 = (_lib.slot_item(_lib.block_data(ctx, POS['S']), 0) or {}).get('id')
    advance_to(ctx, g, k1 + 199, 's9-refill')
    s2 = (_lib.slot_item(_lib.block_data(ctx, POS['S']), 0) or {}).get('id')
    a2 = {s: v['id'] for s, v in _lib.items_of(_lib.block_data(ctx, AUTOLOADER)).items()}
    ctx.check(eid('rbmk-autoloader', 'refill'), s0 is None and a0 == {1: MEU, 2: MEU} and s1 is None and s2 == MEU and a2 == {2: MEU},
              'S after the hand removal %s, loader slots %s at game time %d; k1 = %d; tick k1+198: S %s; tick k1+199: S %s, loader slots %s'
              % (s0, a0, g, k1, s1, s2, a2))
    put_lid(ctx)
    park(ctx)
    _lib.advance(ctx, 600, 's9-rest')
    _lib.still(ctx)
    r1 = readings(ctx, S)
    _lib.advance(ctx, 20, 's9-rest-check')
    _lib.still(ctx)
    r2 = readings(ctx, S)
    S['rest'] = {f: _lib.static_readings(r1[f], r2[f]) for f in r1}


LIDS = ('none', 'standard', 'glass')   # RBMKBaseBlock.LidType serialized names (RBMKBaseBlock.java:219-223)
LID_COLUMN = 'R'


def lid_of(ctx, name):
    """The lid state of a column's core, read on the server with `execute if block` (RBMKBaseBlock.java:50,62,68)."""
    p, block = POS[name], next(b for n, _, b, _ in COLS if n == name)
    return next((v for v in LIDS if _lib.is_block(ctx, p, '%s%s[lid=%s]' % (H, block, v))), None)


def put_lid(ctx):
    """Creative, the line at rest: an RBMK lid (an item of stage 4) given into the lowest free hotbar slot, held, and right-clicked
    onto the top of column R from the air south of it (RBMKLidItem.java:30-54, RBMKBaseBlock.java:119-122; original
    ItemRBMKLid.java:22-66)."""
    if lid_of(ctx, LID_COLUMN) != 'none':
        raise RuntimeError('column %s has a lid before the lid is put on' % LID_COLUMN)
    _lib.give(ctx, (H + 'rbmk_lid', 1))
    slot = _lib.find_slot(_lib.inventory(ctx), H + 'rbmk_lid')
    if slot is None or slot > 8:
        raise RuntimeError('the lid is not in the hotbar (slot %s)' % slot)
    _lib.hold(ctx, H + 'rbmk_lid', hotbar=slot)
    p = POS[LID_COLUMN]
    _lib.use_on(ctx, (p[0], TOP, p[2]), 'up', [p[0] + 0.5, TOP + 2, p[2] + 2.5], fly=True)
    _lib.still(ctx, ticks=20)
    # (a creative player keeps the used item, so the lid's stack count is not checked)
    if lid_of(ctx, LID_COLUMN) != 'standard':
        raise RuntimeError('column %s lid %s after the click' % (LID_COLUMN, lid_of(ctx, LID_COLUMN)))


# heat sits on the floor of 20 every column re-imposes each tick (RBMKBaseBlockEntity.java:216-218) and hasRod / fluxQuantity are
# recomputed each tick (RBMKRodBlockEntity.java:162-182): compared where listed, but never the stored quantity a group relies on
RECOMPUTED = tuple('%s_%s' % (n, k) for n in ('F', 'S') for k in ('heat', 'hasRod', 'flux'))


def readings(ctx, S):
    """{feature: {name: value}} of the resting rig, server data."""
    d = {n: _lib.block_data(ctx, p) for n, p, _, _ in COLS}
    out = {}
    out['rbmk-core'] = {'%s_heat' % n: d[n].get('heat') for n in ('A', 'M', 'R', 'C1', 'C2', 'B', 'O', 'ST')}
    out['rbmk-core']['%s_lid' % LID_COLUMN] = lid_of(ctx, LID_COLUMN)
    st_items = _lib.items_of(d['ST'])
    rs = rod_state(_lib.slot_item(d['ST'], 0))
    out['rbmk-fuel'] = dict(ra_yield=rs and rs[1], ra_xenon=rs and rs[2], ra_core=rs and rs[3], ra_hull=rs and rs[4])
    out['rbmk-reactor'] = {k: v for n in ('F', 'S') for k, v in (('%s_heat' % n, d[n].get('heat')), ('%s_hasRod' % n, d[n].get('hasRod')),
                                                                ('%s_flux' % n, d[n].get('fluxQuantity')))}
    s_rod = _lib.slot_item(d['S'], 0)
    out['rbmk-reactor']['S_rod'] = s_rod and (s_rod.get('id'), json.dumps(custom(s_rod), sort_keys=True))
    out['rbmk-control'] = {'%s_%s' % (n, k): d[n].get(k) for n in ('C1', 'C2') for k in ('level', 'targetLevel', 'startingLevel', 'color')}
    if S.get('steam_rig'):
        ls = loop_state(ctx)
        out['rbmk-steam'] = {k: ls[k] for k in ('feed', 'bsteam', 'es', 'ew', 'cw', 'cs', 'barrel', 'charge')}
    if S.get('console'):
        c = _lib.block_data(ctx, S['console'])
        out['rbmk-console'] = {k: c.get(k) for k in ('tX', 'tY', 'tZ')}
    out['rbmk-storage'] = {'items': sorted((s, v['id'], v['count']) for s, v in st_items.items())}
    if S.get('recycled'):
        out['rbmk-recycling'] = {'chest': sorted((s, v['id'], v['count'], v['meta']) for s, v in _lib.items_of(_lib.block_data(ctx, CHEST)).items()),
                                 'drum': sorted((s, v['id'], v['count'], json.dumps(v['components'], sort_keys=True))
                                                for s, v in _lib.items_of(_lib.block_data(ctx, DRUM)).items())}
    out['rbmk-outgasser'] = dict(progress=d['O'].get('progress'), items=sorted((s, v['id'], v['count']) for s, v in _lib.items_of(d['O']).items()),
                                 gas=tank(d['O'], 'gas')[0])
    if S.get('autoloader'):
        a = _lib.block_data(ctx, AUTOLOADER)
        out['rbmk-autoloader'] = dict(cycle=a.get('cycle'), piston=a.get('piston'), ret=a.get('ret'), delay=a.get('delay'),
                                      items=sorted((s, v['id']) for s, v in _lib.items_of(a).items()))
    if S.get('crane'):
        k = _lib.block_data(ctx, S['crane'])
        out['rbmk-crane'] = {x: k.get(x) for x in ('posFront', 'posLeft', 'spanF', 'spanB', 'spanL', 'spanR', 'centerX', 'centerY', 'centerZ', 'crane')}
    return out


def section_reload(ctx, S):
    rest = S['rest']
    g = _lib.reopen(ctx, near=(X0, Y, Z0))
    after = readings(ctx, S)
    settings = ('cycle', 'ret', 'C1_targetLevel', 'C2_targetLevel', 'C1_color', 'C2_color', 'crane')
    for f in FEATURES:
        if f not in rest:
            ctx.not_run(eid(f, 'reload'), 'no resting readings of this group (its section stopped)')
            continue
        same, moved = rest[f]
        before = dict(same)
        # rbmk-core: the column heats are only named; the lid of R is the group's compared stored state
        floor = {k: before.pop(k) for k in list(before) if f == 'rbmk-core' and k.endswith('_heat')}
        res = _lib.compare_static(before, {k: after.get(f, {}).get(k) for k in before}, not_quantity=settings + RECOMPUTED)
        ctx.check(eid(f, 'reload'), res['ok'], 'game time %d before leaving, %d after; readings that moved at rest (not compared): '
                  '%s; heats on the floor of 20 (not compared): %s; %s; values %s'
                  % (g[0], g[1], moved or 'none', floor or 'none', res['detail'], {k: before[k] for k in list(before)[:12]}))


def run(ctx):
    _lib.setup_world(ctx, freeze=True)
    _lib.cmd(ctx, 'gamemode survival')
    _lib.cmd(ctx, 'clear @s', allow_error=True)
    _lib.go_near(ctx, X0 - 4, Y, Z0)
    corners = [(x, z) for x in (X0 - 32, X0 + 14) for z in (Z0 - 13, Z0 + 13)]
    for _ in range(60):
        if all(ctx.server('execute if loaded %d %d %d' % (x, Y, z), allow_error=True)['result'] == 1 for x, z in corners):
            break
        ctx.step('wait', ticks=10)
    else:
        raise RuntimeError('the chunks of the site did not load: %s' % corners)
    _lib.cmd(ctx, 'fill %d %d %d %d %d %d minecraft:air' % (X0 - 32, Y, Z0 - 13, X0 + 14, Y + 13, Z0 + 13), allow_error=True)
    S = {}
    for name, fn, ids in (('A (assembly)', section_assembly, SEC_A), ('C (crafting)', section_crafting, SEC_C),
                          ('B (build)', section_build, SEC_B), ('F (fuel)', section_fuel, SEC_F), ('R (run)', section_run, SEC_R),
                          ('W (recycling)', section_recycle, SEC_W)):
        _lib.section(ctx, ids, lambda fn=fn: fn(ctx, S), 'section %s stopped' % name)
        _lib.sneak(ctx, False)
    if not S.get('built'):
        for f in FEATURES:
            ctx.not_run(eid(f, 'reload'), 'the reactor was not built, so nothing at rest to compare')
        for i in SEC_REST:
            ctx.not_run(i, 'the reactor was not built')
        return
    reason = _lib.section(ctx, SEC_REST, lambda: section_rest(ctx, S), 'rest stopped')
    if reason or 'rest' not in S:
        for f in FEATURES:
            ctx.not_run(eid(f, 'reload'), reason or 'no resting readings')
        return
    _lib.section(ctx, [eid(f, 'reload') for f in FEATURES], lambda: section_reload(ctx, S), 'reload stopped')
