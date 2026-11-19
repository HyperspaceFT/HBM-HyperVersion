"""Main line, stage 8 (ZIRNOX): the reactor built in the assembly machine, its fuel rods crafted from empty rods and natural
uranium billets, carbon dioxide and water loaded, and its superheated steam turned into power by industrial turbines in a
closed water loop; one full core of 24 natural uranium rods is burned for real under /tick sprint. Survival player, real
crafting-table clicks, real placement, real GUI clicks; no meltdown in this file.

Sections (each fails alone; a later section that needs an earlier one's product turns its rows into not-run):
  A  assembly machine (placed by hand) on a wood burner over one red cable cell: the ZIRNOX from ass.cirnox.
  C  crafting table: the fluid identifier, 24 empty ZIRNOX rods, 24 natural uranium fuel rods.
  B  the rig: the reactor placed by hand facing south; east of it three industrial turbines in a row (placed by hand on a
     stone platform one block up, so their side ports meet the reactor's lower steam ports), then a steam condenser, and a
     fluid duct from the condenser back to the reactor's west port, typed water with the identifier:
       reactor --superheated steam--> T1 (lever twice) --hot steam--> T2 (lever once) --steam--> T3 --spent steam-->
       condenser --water--> duct --> reactor
     Ports touch directly (a machine pushes into the neighbour cell its port names, IFluidStandardSenderMK2.tryProvide),
     so the loop loses nothing: 1 mB superheated steam -> 10 hot -> 100 steam -> 1 spent -> 1 water (Fluids.java:611-613).
     Rods shift-clicked in, carbon dioxide from a 16,000 mB fluid barrel (预写), water from 8 buckets, switched on in the GUI.
  R  the run from switch-on, every count from a freeze and exact sprints: tick 10, tick 2,000 (equilibrium), ticks
     50,000/50,001 (first rods spent), the whole burn to the simulated last depletion, the resting state at tick 117,000.
Then the world is left and opened again and the resting readings are compared.
  L  after the reload: one spent rod taken out by hand, an LES rod crafted (empty rod + 2 LES billets, the billets 预写) and
     shift-clicked into the free slot, burned alone under sprint to its spent rod, which the crafting table turns into hot
     schrabidium waste.

Layout (Y = -60 the flat world's first air layer; everything faces south, so a machine's clockwise side is west):
  assembler core (AX, Y, AZ); wood burner core (AX - 2, Y, AZ + 2), its power cell (AX - 2, Y, AZ) is the cable;
  reactor core R = (RX, Y, RZ) (5 x 5, y .. y + 4); steam ports two cells east and west of the core at y + 1 and y + 3, their
  neighbour cells R +- 3 x (ReactorZirnoxBlockEntity.java:425-441, ReactorZirnoxBlock.java:67-85);
  turbine cores (RX + 4 / + 7 / + 10, Y + 1, RZ - 3) (7 long along z, 3 wide, dims {2,0,3,3,1,1}, offset 3), side ports at
  core +- 1 x, z = core + 3 and core - 1 (MachineIndustrialTurbineBlock.java:66-67,102-119); condenser (RX + 12, Y + 1, RZ);
  stone platform x RX + 3 .. RX + 12, z RZ - 6 .. RZ at Y; duct x = RX + 12 z RZ + 1 .. RZ + 6, z = RZ + 6 x RX - 3 .. RX + 11,
  x = RX - 3 z RZ .. RZ + 5, all at Y + 1.

Expected values are derived from the code (NEO file:line, the 1.7.10 original's file:line beside it) and simulated here in
the reactor's own float/int arithmetic. Readings are server data (`data get block` / `data get entity`), taken in the frozen
world after 80 client ticks (a frozen server still moves the duct net for about 3 s, NtmEventHandler.java:69-76,
PowerNetMK2.java:22). A sprint started in the frozen world runs one tick more than requested; exact tick counts come from
the freeze and _lib.advance_to, never from an `until` sprint.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

SCENARIO = dict(
    id='zirnox-reactor.mainline_stage8',
    feature='zirnox-reactor',
    title='Main line stage 8: ZIRNOX from the assembly machine, rods crafted, CO2 and water, a closed industrial-turbine loop, '
          'one natural uranium core burned under sprint (survival, real crafting, placement and GUI)',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

H = _lib.H
F = 'zirnox-reactor'
Y = -60
X0, Z0 = 8000, 8000
AX, AZ = X0, Z0                      # assembly machine core (placed from the south one cell south of it: offset 1)
BURNER = (AX - 2, Y, AZ + 2)         # wood burner core (offset 0)
CABLE = (AX - 2, Y, AZ)              # burner power cell (core + 2 north, MachineWoodBurnerBlockEntity.java:226-236) = assembler
                                     # port cell (core - 2 x, MachineAssemblyMachineBlockEntity.java:215-235)
TABLE = (X0 + 6, Y, Z0 + 3)
RX, RZ = X0 + 20, Z0
R = (RX, Y, RZ)
TURBINES = [(RX + 4, Y + 1, RZ - 3), (RX + 7, Y + 1, RZ - 3), (RX + 10, Y + 1, RZ - 3)]
COND = (RX + 12, Y + 1, RZ)
DUCTS = ([(RX + 12, Y + 1, z) for z in range(RZ + 1, RZ + 7)] + [(x, Y + 1, RZ + 6) for x in range(RX - 3, RX + 12)]
         + [(RX - 3, Y + 1, z) for z in range(RZ, RZ + 6)])
PARK = [X0 + 14.5, Y, Z0 + 12.5]     # where the player waits during sprints (the whole site within simulation distance)

# the stage-8 start list (closure report, stage_start_items "8"): exactly what the line uses
GIVE_ASM = [(H + 'shell_steel', 4), (H + 'pipe_steel', 8), (H + 'ingot_boron', 8), (H + 'ingot_rubber', 16), (H + 'concrete_smooth', 16),
            (H + 'circuit_integrated_board', 4), (H + 'machine_assembly_machine', 1)]
GIVE_CRAFT = [(H + 'nugget_zirconium', 36), (H + 'ingot_beryllium', 6), (H + 'billet_uranium', 48), (H + 'circuit_vacuum_tube', 1),
              (H + 'plate_iron', 1)]
# not on the stage-8 list, issued as items of earlier stages (needs_stage of the closure report): the graphite ingot (2:
# carbon from the crucible cast in the ingot mold), the wood burner (2), the industrial turbine (5: ass.iturbine), the
# steam condenser (2)
OUTSIDE = [(H + 'ingot_graphite', 16), (H + 'machine_wood_burner', 1), (H + 'machine_industrial_turbine', 3), (H + 'machine_condenser', 1)]
VANILLA = [('minecraft:oak_log', 1), ('minecraft:crafting_table', 1), ('minecraft:blue_dye', 1), ('minecraft:water_bucket', 8)]
# 预写: the carbon dioxide in the barrel (chem.co2 from natural gas, ChemicalPlantRecipes.java:68-70, is not played here)
CO2_ID, WATER_ID, STEAM_ID, HOT_ID, SHS_ID, SPENT_ID = 55, 1, 2, 3, 4, 48   # registration order, Fluids.java:250-305
CO2_BARREL = H + 'fluid_barrel_full'                                        # 16,000 mB, FluidContainerRegistry.java:55-56
BUCKETS = 8

# ReactorZirnoxBlockEntity.java:108-138 (original TileEntityReactorZirnox.java:161-191)
NEIGHBOURS = {0: (1, 7), 1: (0, 2, 8), 2: (1, 9), 3: (4, 10), 4: (3, 5, 11), 5: (4, 6, 12), 6: (5, 13), 7: (0, 8, 14),
              8: (1, 7, 9, 15), 9: (2, 8, 16), 10: (3, 11, 17), 11: (4, 10, 12, 18), 12: (5, 11, 13, 19), 13: (6, 12, 20),
              14: (7, 15, 21), 15: (8, 14, 16, 22), 16: (9, 15, 23), 17: (10, 18), 18: (11, 17, 19), 19: (12, 18, 20),
              20: (13, 19), 21: (14, 22), 22: (15, 21, 23), 23: (16, 22)}
ROD_HEAT, ROD_LIFE = 30, 250_000     # ZirnoxRodItem.java:81; original ItemZirnoxRod.java:102
MAX = 100_000                        # ReactorZirnoxBlockEntity.java:51,54
ROD = H + 'rod_zirnox'
SPENT_ROD = H + 'rod_zirnox_natural_uranium_fuel_depleted'
T_EQ, T_STATIC = 2000, 117_000
# the LES rod (ZirnoxRodItem.java:89; original ItemZirnoxRod.java:110): meta 8, life 150,000, 150 heat per decay
LES_META, LES_HEAT, LES_LIFE = 8, 150, 150_000
LES_SPENT = H + 'rod_zirnox_les_fuel_depleted'
ASM_TICKS, ASM_POWER = 600, 100      # AssemblyMachineRecipes.java:451; original AssemblyMachineRecipes.java:525

E = [
    ('assemble', '装配机（手放，在配方选择界面里选 ass.cirnox）：4 钢壳、8 钢管、8 硼锭、16 石墨锭、16 橡胶锭、16 光滑混凝土、4 集成电路板，'
                 '600 刻、每刻 100 HE。每个运行刻进度加 1/600（双精度），按代码模拟在第 600 刻累计到 1：最后一组原料放进去后第 599 刻'
                 '输出槽为空，第 600 刻出 1 台 ZIRNOX、7 组原料用尽；装配机与已关的木柴发电机合计存电恰好少 100 × 600 = 60,000 HE',
     'AssemblyMachineRecipes.java:451-458, ModuleMachineBase.java:115-127, MachineAssemblyMachineBlockEntity.java:97-101,112-113,122; '
     '原版 AssemblyMachineRecipes.java:525-527, ModuleMachineBase.java:117-130, TileEntityMachineAssemblyMachine.java:108-109,118'),
    ('craft-rods', '工作台真实点击：6 个锆粒围 1 个铍锭得 4 根空 ZIRNOX 棒，做 6 次共 24 根；1 根空棒加 2 个天然铀坯得 1 根天然铀燃料棒'
                   '（原版与 NEO 都用坯），做 24 次：24 根各占一格（不可堆叠）、meta 0、不带 life 数据，锆粒、铍锭、48 个铀坯与空棒全部用尽',
     'NtmRecipeProvider.java:525-540, NtmItems.java:693-695; 原版 RodRecipes.java:26-27,250-257'),
    ('place-load', '反应堆手放（玩家朝北，朝向南，核心在放置格以北 2 格）；24 根燃料棒逐根 Shift 点击进 0–23 槽（各 1 根）；'
                   '装 16,000 mB 二氧化碳的流体桶（预写：桶里的二氧化碳由命令发放）放进二氧化碳输入槽，走 1 刻后二氧化碳罐 16,000/16,000、'
                   '空桶进槽 26；8 桶水逐桶放进水输入槽、每桶走 1 刻：水罐 8,000/32,000，槽 27 有 8 个空桶；未开机时热量 0',
     'ReactorZirnoxBlockEntity.java:72-74,164-165, ReactorZirnoxMenu.java:25-55,63-84, ReactorZirnoxBlock.java:41-42, '
     'FluidContainerRegistry.java:37,56 (水桶与桶的容量 1,000、16,000 mB); '
     '原版 TileEntityReactorZirnox.java:94-96,224-225, ContainerReactorZirnox.java:23-52,66-93, FluidContainerRegistry.java:33,90'),
    ('turbine-levers', '三台工业汽轮机手放在反应堆东侧（命令搭建的石台上），默认收普通蒸汽 750,000、出乏汽 3,000,000；拉一次杆：收热蒸汽、'
                       '出蒸汽，两罐各缩到十分之一；再拉一次：收过热蒸汽、出热蒸汽，再缩十分之一。1 号拉两次：过热蒸汽 7,500／热蒸汽 30,000；'
                       '2 号拉一次：热蒸汽 75,000／蒸汽 300,000；3 号不拉：蒸汽 750,000／乏汽 3,000,000',
     'TurbineBaseBlockEntity.java:106-119, MachineIndustrialTurbineBlockEntity.java:28-29,50-51,163, MachineIndustrialTurbineBlock.java:80-95; '
     '原版 TileEntityTurbineBase.java:104-117, TileEntityMachineIndustrialTurbine.java:34-35,72-73,148, MachineIndustrialTurbine.java:56-60'),
    ('water-loop', '回路：1 号汽轮机的侧口贴着反应堆东侧下层蒸汽口外一格，1→2→3 号侧口相贴，3 号的出口贴蒸汽冷凝器，冷凝器出水经一条命令铺的'
                   '流体管道（27 节）回到反应堆西侧口。工作台做出流体识别器（染料、真空管、铁板），在它的界面里选水（不打字，未筛选列表第 4 项），'
                   '潜行右键其中一节管道一次，整条 27 节都标成水（类型 1）',
     'FluidDuctBaseBlock.java:52-80,96-113, NtmRecipeProvider.java:85-93, ReactorZirnoxBlockEntity.java:425-441, '
     'MachineIndustrialTurbineBlockEntity.java:122-137; 原版 FluidDuctBase.java:59,100,108-126, CraftingManager.java:854, '
     'TileEntityReactorZirnox.java:195-208'),
    ('switch-on', '（CO2 16,000 mB 为预写）界面开关（144,35，14×14）点一下：isOn 由 false 变 true；开机后第 10 刻热量 21,167、压力 54,384，等于按代码逐刻的单精度模拟'
                  '（每刻先按每根棒“邻棒数+1”次衰变、每次加 30 热；压力 = 2 × CO2 + (int)(热 × CO2/16,000)；水、CO2 都有且蒸汽罐未满时'
                  '扣 (int)(热 × 压力/1,000,000)）',
     'ReactorZirnoxScreen.java:81, ReactorZirnoxBlockEntity.java:167-191,320-336,450-454; '
     '原版 GUIReactorZirnox.java:67-70, TileEntityReactorZirnox.java:227-249,340-356,457-460'),
    ('equilibrium', '（CO2 16,000 mB 为预写）开机后第 2,000 刻：热量 36,159、压力 70,919（模拟在第 100 刻前已到这个不动点）。推导：24 根全是天然铀棒，每刻衰变'
                    ' Σ(邻棒数+1) = 24 + 68 = 92 次、每次 30 热，共加 2,760；CO2 满罐时压力 = 32,000 + 峰值热；不动点要 (int)(峰值 × (32,000'
                    ' + 峰值)/1,000,000) = 2,760，最小的峰值是 38,919（38,919 × 70,919 = 2.76010e9，单精度下 /1e6 = 2,760.10 → 2,760；'
                    '38,918 时 2,759.99 → 2,759），刻末存下 38,919 − 2,760 = 36,159，压力 70,919，都低于 100,000；每根棒的 life = 2,000 ×'
                    '（邻棒数+1）：2 个邻棒 6,000、3 个 8,000、4 个 10,000',
     'ReactorZirnoxBlockEntity.java:51-54,108-138,167-191,320-339, ZirnoxRodItem.java:81; '
     '原版 TileEntityReactorZirnox.java:61-64,161-191,227-249,340-361, ItemZirnoxRod.java:102'),
    ('turbine-power', '（CO2 16,000 mB 为预写）第 2,000 刻冻结读数：反应堆每刻产过热蒸汽 (int)((38,919 − 10,256)/100,000 × min(16,000/14,000, 1) × 25 × 7.5) = 53 mB；'
                      '1 号每刻用 ceil(20% × 存量) = 53（用之前的存量 261–265，刻末读到的要再减去这一刻进来的 53），功率 53 × 18 = 954 HE，maxPower 1,500 次 × 18 = 27,000（飞轮每刻'
                      '最多给 max(转速, 0.05) × maxPower，0.05 × 27,000 = 1,350 > 954，所以整刻给出）；2 号：热蒸汽 530 次 × 2 = 1,060 HE，'
                      'maxPower 15,000 × 2 = 30,000；3 号：蒸汽 5,300 = 53 次 × 100，功率 53 × 200 = 10,600 HE，maxPower 1,500 × 200 = 300,000',
     'ReactorZirnoxBlockEntity.java:276-291, TurbineBaseBlockEntity.java:59-82, MachineIndustrialTurbineBlockEntity.java:30,59-81,161, '
     'Fluids.java:609,611-613 (效率 1.0); 原版 TileEntityReactorZirnox.java:291-309, TileEntityTurbineBase.java:66-85, '
     'TileEntityMachineIndustrialTurbine.java:79-96,146, Fluids.java:635,637-639'),
    ('loop-conservation', '（CO2 16,000 mB 为预写）第 2,000 刻冻结静置后，按水当量把回路所有罐加起来（反应堆水与过热蒸汽、1 号输入、1 号输出/10、2 号输入/10、2 号输出/100、'
                          '3 号输入/100、3 号乏汽、冷凝器两罐）恰好等于装进去的 8,000 mB（过热蒸汽 1 → 热蒸汽 10 → 蒸汽 100 → 乏汽 1 → 水 1，'
                          '冷凝器 1:1）；反应堆水罐 > 0、蒸汽罐 < 8,000（蒸汽一直有去处）',
     'TurbineBaseBlockEntity.java:65-72, CondenserBaseBlockEntity.java:42-57, MachineCondenserBlockEntity.java:16-17, ReactorZirnoxBlockEntity.java:184-199,285-289, '
     'Fluids.java:611-613; 原版 TileEntityTurbineBase.java:71-77, TileEntityCondenser.java:36-37,73-83, Fluids.java:637-639'),
    ('center-rods', '（CO2 16,000 mB 为预写）开机后第 50,000 刻 24 格仍全是燃料棒（4 个中心棒 8、11、12、15 每刻 5 次、life 正好 250,000）；第 50,001 刻这 4 格换成'
                    '天然铀乏燃料棒（life 超过 250,000 时换成 fuelMap 的乏棒），其余 20 格仍是燃料棒',
     'ReactorZirnoxBlockEntity.java:76-77,320-336, ZirnoxRodItem.java:81; 原版 TileEntityReactorZirnox.java:79,340-356'),
    ('burnout', '（CO2 16,000 mB 为预写；燃耗本身真实冲刺）整盘用冲刺真实烧完：模拟的最后一根在第 116,668 刻耗尽。第 116,667 刻还剩 2、6、17、20、21、23 六格燃料棒，热量 6,053、压力 38,293；'
                '第 116,668 刻 24 格全是天然铀乏燃料棒，热量 5,995、压力 38,233（都是模拟值）；其间每次轮询热量与压力都低于 100,000、'
                '蒸汽罐低于 8,000、水罐大于 0，反应堆完好',
     'ReactorZirnoxBlockEntity.java:167-191,320-340; 原版 TileEntityReactorZirnox.java:227-249,340-361'),
    ('static-end', '（CO2 16,000 mB 为预写）最后一根耗尽后不再加热，热量每刻减 (int)(热 × (32,000 + 热)/1,000,000)，模拟在第 116,842 刻停在 31（31 × 32,031/1e6 = 0.99 → 0）：'
                   '第 117,000 刻热量 31、压力 32,031，隔 20 刻两次读数相同；1、2 号汽轮机输入罐 0，3 号剩下不够一次的蒸汽（20% 向上取整'
                   '不到 100，存量 ≤ 495，且是 100 的倍数），回路水当量仍是 8,000',
     'ReactorZirnoxBlockEntity.java:182-191, TurbineBaseBlockEntity.java:66-72; 原版 TileEntityReactorZirnox.java:240-249, '
     'TileEntityTurbineBase.java:71-77'),
    ('reload', '（CO2 16,000 mB 为预写）退出世界再打开：反应堆（热量 31、压力 32,031、开机、CO2 16,000、水、24 根乏燃料棒与两格空容器）、三台汽轮机（罐的类型、容量、存量、'
               'maxPower）、冷凝器与装配机的服务端读数与退出前相同，参与比对的非默认存储量至少一个',
     'ReactorZirnoxBlockEntity.java:219-241, TurbineBaseBlockEntity.java:148-162, MachineIndustrialTurbineBlockEntity.java:212-227, '
     'CondenserBaseBlockEntity.java:82-95, MachineAssemblyMachineBlockEntity.java:265-282, FluidTank.java:255-274; '
     '原版 TileEntityReactorZirnox.java:125-148, TileEntityTurbineBase.java:147-160, TileEntityMachineIndustrialTurbine.java:183-198, '
     'TileEntityCondenser.java:112-123, TileEntityMachineAssemblyMachine.java:235-252'),
    ('les-rod', '（预写：2 个 LES 坯由命令发放，施拉比只来自熔毁，这里不做；CO2 16,000 mB 仍是预写的那一桶；燃耗本身真实冲刺）重开之后：界面里 Shift 点击取出'
                '槽 0 的乏棒，工作台真实点击 1 根空棒加 2 个 LES 坯得 1 根 LES 燃料棒（rod_zirnox，meta 8，不带 life），Shift 点击进唯一的空槽 0。'
                '其余 23 格是乏棒（不算燃料棒），LES 棒没有邻棒，每刻 1 次衰变、加 150 热、life 加 1：放进去后第 150,000 刻槽 0 仍是 LES 棒、'
                'life 150,000；第 150,001 刻 life 超过 150,000，换成 LES 乏棒。热量按单精度逐刻模拟：从放入时的 31 起，峰值的不动点是 4,150'
                '（4,150 × 36,150 = 1.500225e8，/1e6 → 150；4,149 × 36,149 → 149.98 → 149），刻末存 4,000、压力 36,150，第 150,000 与'
                ' 150,001 刻都是 4,000／36,150（耗尽那一刻先加热再换棒），第 150,002 刻不再加热：4,000 − (int)(4,000 × 36,000/1e6) = 3,856、'
                '压力 36,000；热量低于 10,256，不产汽。取出 LES 乏棒在工作台合成：得 2 个热的废施拉比（waste_schrabidium，meta 1），空棒作为'
                '容器物品留下（+1），乏棒 −1',
     'ZirnoxRodItem.java:89, NtmRecipeProvider.java:1297-1303,1357,3061-3068, NtmItems.java:704, '
     'ReactorZirnoxBlockEntity.java:85,182-191,280-290,293-300,320-336; 原版 ItemZirnoxRod.java:110, RodRecipes.java:35,46, '
     'ModItems.java:2987, TileEntityReactorZirnox.java:87,240-249,295-308,311-320,340-356'),
]


def expectations():
    return [dict(id='%s.%s' % (F, i), text=t, source=s) for i, t, s in E]


def eid(name):
    return '%s.%s' % (F, name)


SEC_ASM = [eid('assemble')]
SEC_CRAFT = [eid('craft-rods')]
SEC_BUILD = [eid('place-load'), eid('turbine-levers'), eid('water-loop')]
SEC_RUN = [eid(n) for n in ('switch-on', 'equilibrium', 'turbine-power', 'loop-conservation', 'center-rods', 'burnout', 'static-end')]


# ---------------------------------------------------------------- simulation (the reactor's own arithmetic)

def steam_cycle(heat, co2=16000):
    """ReactorZirnoxBlockEntity.generateSteam (:280-286): (int)(((heat - 10256F) / 100000F) * min(co2 / 14000F, 1F) * 25F * 7.5F)."""
    if heat <= 10256:
        return 0
    v = _lib.f32(_lib.f32(_lib.f32(heat) - _lib.f32(10256.0)) / _lib.f32(100000.0))
    v = _lib.f32(v * min(_lib.f32(_lib.f32(co2) / _lib.f32(14000.0)), 1.0))
    v = _lib.f32(v * _lib.f32(25.0))
    return int(_lib.f32(v * _lib.f32(7.5)))


def simulate(limit=200_000):
    """The whole core from switch-on, tick by tick in the reactor's order (slots 0..23; a rod spent earlier in the tick no
    longer counts as a neighbour, ReactorZirnoxBlockEntity.hasFuelRod; the decay loop stops at the replacement) with water, CO2
    16,000 and room for steam every tick. Returns dict(heat, pressure, cycle lists indexed by ticks since switch-on,
    depleted={slot: tick}, last, static_from)."""
    life, fuel = [0] * 24, [True] * 24
    heat = 0
    heats, pressures, cycles, depleted = [0], [0], [0], {}
    last = static_from = None
    for t in range(1, limit + 1):
        for i in range(24):
            if not fuel[i]:
                continue
            d = 1 + sum(1 for n in NEIGHBOURS[i] if fuel[n])
            for _ in range(d):
                heat += ROD_HEAT
                life[i] += 1
                if life[i] > ROD_LIFE:
                    fuel[i] = False
                    depleted[i] = t
                    break
        pressure = 16000 * 2 + int(_lib.f32(_lib.f32(heat) * _lib.f32(_lib.f32(16000) / _lib.f32(16000))))
        cycle = 0
        if 0 < heat < MAX:
            cycle = steam_cycle(heat)
            heat -= int(_lib.f32(_lib.f32(_lib.f32(heat) * _lib.f32(pressure)) / _lib.f32(1000000.0)))
        heats.append(heat)
        pressures.append(pressure)
        cycles.append(cycle)
        if last is None and not any(fuel):
            last = t
        if last is not None and t > last + 2 and heats[-1] == heats[-2] == heats[-3]:
            static_from = next(k for k in range(t, 0, -1) if heats[k - 1] != heats[k])
            break
    return dict(heat=heats, pressure=pressures, cycle=cycles, depleted=depleted, last=last, static_from=static_from)


def simulate_single(heat0, ticks, rod_heat=LES_HEAT, life_max=LES_LIFE):
    """One fuel rod without fuel neighbours (one decay a tick) from a stored heat heat0, CO2 16,000 and room for steam: lists of
    heat and pressure indexed by ticks since the rod went in, and the tick it was replaced by its spent rod."""
    heat, life, fuel, depleted = heat0, 0, True, None
    heats, pressures = [heat0], [None]
    for t in range(1, ticks + 1):
        if fuel:
            heat += rod_heat
            life += 1
            if life > life_max:
                fuel, depleted = False, t
        pressure = 16000 * 2 + int(_lib.f32(_lib.f32(heat) * _lib.f32(_lib.f32(16000) / _lib.f32(16000))))
        if 0 < heat < MAX:
            heat -= int(_lib.f32(_lib.f32(_lib.f32(heat) * _lib.f32(pressure)) / _lib.f32(1000000.0)))
        heats.append(heat)
        pressures.append(pressure)
    return dict(heat=heats, pressure=pressures, depleted=depleted)


# ---------------------------------------------------------------- readings

def gt(ctx):
    return ctx.server()['game_time']


def rods(data):
    """{slot: (id, life)} of the reactor's slots 0..23."""
    out = {}
    for it in data.get('Items', []):
        s = it.get('Slot')
        if s is not None and s < 24:
            out[s] = (it.get('id'), (it.get('components') or {}).get('minecraft:custom_data', {}).get('life'))
    return out


def fuel_slots(data):
    return sorted(s for s, (i, _) in rods(data).items() if i == ROD)


def tank(data, name):
    t = _lib.tanks(data).get(name, {})
    return t.get('fill', 0), t.get('max'), t.get('type')


def loop_state(ctx, core, turbines):
    """Server readings of the loop: reactor, three turbines, condenser."""
    r = _lib.block_data(ctx, core)
    out = dict(heat=r.get('heat'), pressure=r.get('pressure'), isOn=r.get('isOn'), r_water=tank(r, 'water')[0],
               r_steam=tank(r, 'steam')[0], r_co2=tank(r, 'carbondioxide')[0], rods=rods(r), data=r)
    for n, pos in enumerate(turbines, 1):
        d = _lib.block_data(ctx, pos)
        out['t%d' % n] = dict(power=d.get('power'), maxPower=d.get('maxPower'), flywheel=d.get('flywheel_energy'),
                              inp=tank(d, 'water'), out=tank(d, 'steam'))
    c = _lib.block_data(ctx, COND)
    out['cond'] = dict(inp=tank(c, 'water'), out=tank(c, 'steam'))
    return out


def water_units_x100(s):
    """The loop's water in hundredths of a mB: superheated steam 1 = water 1, hot steam 10, steam 100 per water mB."""
    return (100 * (s['r_water'] + s['r_steam']) + 100 * s['t1']['inp'][0] + 10 * s['t1']['out'][0] + 10 * s['t2']['inp'][0]
            + s['t2']['out'][0] + s['t3']['inp'][0] + 100 * s['t3']['out'][0] + 100 * (s['cond']['inp'][0] + s['cond']['out'][0]))


def flat(s):
    """Readings compared across the reload: {name: value}."""
    out = dict(heat=s['heat'], pressure=s['pressure'], isOn=s['isOn'], r_water=s['r_water'], r_steam=s['r_steam'], r_co2=s['r_co2'],
               r_items=sorted((it.get('Slot'), it.get('id'), it.get('count', 1)) for it in s['data'].get('Items', [])))
    for n in ('t1', 't2', 't3'):
        t = s[n]
        out.update({n + '_in': t['inp'][0], n + '_in_max': t['inp'][1], n + '_in_type': t['inp'][2], n + '_out': t['out'][0],
                    n + '_out_max': t['out'][1], n + '_out_type': t['out'][2], n + '_maxPower': t['maxPower'], n + '_power': t['power']})
    out.update(cond_in=s['cond']['inp'][0], cond_out=s['cond']['out'][0])
    return out


def park(ctx):
    ctx.step('view', pos=PARK, pitch=20.0, yaw=0.0, fly=False, hide_gui=False)


def advance_to(ctx, t0, target, label):
    park(ctx)
    _lib.advance_to(ctx, t0, target, label)


# ---------------------------------------------------------------- sections

def section_assembly(ctx, S):
    _lib.give(ctx, *GIVE_ASM)
    _lib.give(ctx, (H + 'ingot_graphite', 16), (H + 'machine_wood_burner', 1), ('minecraft:oak_log', 1))
    _lib.place(ctx, H + 'machine_assembly_machine', (AX, Y - 1, AZ + 1), 'up', [AX + 0.5, Y, AZ + 4.5])
    core, _ = _lib.core_of(ctx, H + 'machine_assembly_machine', (AX - 3, Y, AZ - 3), (AX + 3, Y + 3, AZ + 3))
    if core != (AX, Y, AZ):
        raise RuntimeError('assembly machine core %s, planned %s' % (core, (AX, Y, AZ)))
    _lib.place(ctx, H + 'machine_wood_burner', (BURNER[0], Y - 1, BURNER[2]), 'up', [BURNER[0] + 0.5, Y, BURNER[2] + 3.5])
    bcore, props = _lib.core_of(ctx, H + 'machine_wood_burner', (AX - 5, Y, AZ), (AX - 1, Y + 2, AZ + 4))
    if bcore != BURNER or props.get('facing') != 'south':
        raise RuntimeError('wood burner core %s facing %s, planned %s south' % (bcore, props.get('facing'), BURNER))
    _lib.cmd(ctx, 'setblock %d %d %d hbmsntm:red_cable' % CABLE)     # 命令搭建: the one cable cell
    # the log into the burner's fuel slot, switched on with its button (GUI 53,17 16x15, MachineWoodBurnerScreen.java:93-95)
    hud = _lib.open_gui(ctx, BURNER, 'south', [BURNER[0] + 0.5, Y, BURNER[2] + 2.5], 'MachineWoodBurnerScreen', center=True)
    _lib.put_stack(ctx, 6, 'minecraft:oak_log', 0)
    ctx.step('click', at=[hud['gui_left'] + 61, hud['gui_top'] + 24], button=0, after=4)
    ctx.step('close')
    if not _lib.block_data(ctx, BURNER).get('isOn'):
        raise RuntimeError('the wood burner did not switch on')
    _lib.open_gui(ctx, (AX, Y, AZ + 1), 'south', [AX + 0.5, Y, AZ + 4.0], 'MachineAssemblyMachineScreen', center=True)
    got = _lib.pick_recipe(ctx, core, 'hbmAssemblyMachine.json', 'ass.cirnox', 'block.hbmsntm.machine_zirnox')
    ctx.step('close')
    if got != 'ass.cirnox':
        raise RuntimeError('server recipe after the selector: %r' % got)
    # charge: the burner runs until the assembler holds its 100,000 HE, then it is switched off (an idle burner still hands its
    # buffer to the cable, MachineWoodBurnerBlockEntity.java:96-99, but makes nothing)
    park(ctx)
    ctx.sprint(4000, until=lambda c: _lib.block_data(c, core).get('power', 0) >= 100_000, poll_s=0.5, label='stage8-charge', timeout_s=300)
    ctx.server('tick freeze')
    hud = _lib.open_gui(ctx, BURNER, 'south', [BURNER[0] + 0.5, Y, BURNER[2] + 2.5], 'MachineWoodBurnerScreen', center=True)
    ctx.step('click', at=[hud['gui_left'] + 61, hud['gui_top'] + 24], button=0, after=4)
    ctx.step('close')
    _lib.still(ctx)
    a0, b0 = _lib.block_data(ctx, core), _lib.block_data(ctx, BURNER)
    if b0.get('isOn') or a0.get('power', 0) < ASM_POWER * ASM_TICKS:
        raise RuntimeError('charge: burner on %s, assembler %s HE' % (b0.get('isOn'), a0.get('power')))
    e0 = a0.get('power', 0) + b0.get('power', 0)
    # the seven stacks shift-clicked in (the selected recipe routes each to its slot, ModuleMachineBase.isItemValid)
    _lib.open_gui(ctx, (AX, Y, AZ + 1), 'south', [AX + 0.5, Y, AZ + 4.0], 'MachineAssemblyMachineScreen', center=True)
    items = _lib.inventory(ctx)
    srcs = [_lib.find_slot(items, it) for it, _ in GIVE_ASM[:6]] + [_lib.find_slot(items, H + 'ingot_graphite')]
    if None in srcs:
        raise _lib.Missing('assembly inputs missing: %s' % srcs)
    for s in srcs:
        _lib.shift_click(ctx, _lib.menu_slot(17, s))
    ctx.step('close')
    t0 = gt(ctx)
    loaded = _lib.items_of(_lib.block_data(ctx, core))
    d1 = d2 = None
    advance_to(ctx, t0, ASM_TICKS - 1, 'stage8-assembler')
    d1 = _lib.block_data(ctx, core)
    advance_to(ctx, t0, ASM_TICKS, 'stage8-assembler')
    d2 = _lib.block_data(ctx, core)
    _lib.still(ctx)
    a1, b1 = _lib.block_data(ctx, core), _lib.block_data(ctx, BURNER)
    used = e0 - (a1.get('power', 0) + b1.get('power', 0))
    out1, out2 = _lib.slot_item(d1, 16), _lib.slot_item(d2, 16)
    left = {s: v for s, v in _lib.items_of(d2).items() if 4 <= s <= 15}
    ok = (out1 is None and out2 is not None and out2.get('id') == H + 'machine_zirnox' and out2.get('count', 1) == 1 and not left
          and len([s for s in loaded if 4 <= s <= 15]) == 7 and used == ASM_POWER * ASM_TICKS)
    ctx.check(eid('assemble'), ok, 'inputs loaded in slots %s; tick %d output %s; tick %d output %s, inputs left %s; stored energy %d -> %d, '
              'used %d (want %d)' % (sorted(s for s in loaded if 4 <= s <= 15), ASM_TICKS - 1, out1, ASM_TICKS, out2, left, e0,
                                     e0 - used, used, ASM_POWER * ASM_TICKS))
    _lib.open_gui(ctx, (AX, Y, AZ + 1), 'south', [AX + 0.5, Y, AZ + 4.0], 'MachineAssemblyMachineScreen', center=True)
    _lib.shift_click(ctx, 16)
    ctx.step('close')
    if _lib.count(ctx, H + 'machine_zirnox') != 1:
        raise _lib.Missing('the ZIRNOX did not reach the inventory')
    S['reactor_item'] = True
    S['assembler'] = core


def section_crafting(ctx, S):
    _lib.give(ctx, *GIVE_CRAFT)
    _lib.give(ctx, ('minecraft:crafting_table', 1), ('minecraft:blue_dye', 1))
    _lib.place(ctx, 'minecraft:crafting_table', (TABLE[0], Y - 1, TABLE[2]), 'up', [TABLE[0] + 0.5, Y, TABLE[2] + 3.5])
    _lib.open_gui(ctx, TABLE, 'south', [TABLE[0] + 0.5, Y, TABLE[2] + 2.5], 'Crafting')
    _lib.craft(ctx, ['D', 'C', 'P'], dict(D='minecraft:blue_dye', C=H + 'circuit_vacuum_tube', P=H + 'plate_iron'))
    _lib.craft(ctx, ['Z Z', 'ZBZ', 'Z Z'], dict(Z=H + 'nugget_zirconium', B=H + 'ingot_beryllium'), times=6)
    empties = _lib.count(ctx, H + 'rod_zirnox_empty')
    _lib.craft(ctx, ['EUU'], dict(E=H + 'rod_zirnox_empty', U=H + 'billet_uranium'), times=24)
    ctx.step('close')
    items = _lib.inventory(ctx)
    made = {s: e for s, e in items.items() if e['id'] == ROD}
    good = [s for s, e in made.items() if e['count'] == 1 and e['meta'] == 0 and 'life' not in (e['components'].get('minecraft:custom_data') or {})]
    rest = {k: _lib.count(ctx, H + k, items=items) for k in ('nugget_zirconium', 'ingot_beryllium', 'billet_uranium', 'rod_zirnox_empty')}
    ident = _lib.count(ctx, H + 'fluid_identifier_multi', items=items)
    ctx.check(eid('craft-rods'), empties == 24 and len(made) == 24 and len(good) == 24 and not any(rest.values()),
              'empty rods after 6 crafts: %d (want 24); fuel rods %d in %d slots, %d of them single, meta 0, without life data (want 24); '
              'left over %s (want all 0); fluid identifier %d' % (empties, sum(e['count'] for e in made.values()), len(made), len(good), rest, ident))
    if len(made) != 24:
        raise _lib.Missing('24 fuel rods were not made')
    S['rods'] = True
    S['identifier'] = ident == 1


def section_build(ctx, S):
    if not S.get('reactor_item') or not S.get('rods'):
        raise _lib.Missing('the reactor (section A) or the rods (section C) are missing')
    _lib.place(ctx, H + 'machine_zirnox', (RX, Y - 1, RZ + 2), 'up', [RX + 0.5, Y, RZ + 5.5])
    core, props = _lib.core_of(ctx, H + 'machine_zirnox', (RX - 3, Y, RZ - 3), (RX + 3, Y + 4, RZ + 3))
    if core != R or props.get('facing') != 'south':
        raise RuntimeError('reactor core %s facing %s, planned %s south' % (core, props.get('facing'), R))
    S['reactor'] = core
    _lib.cmd(ctx, 'fill %d %d %d %d %d %d minecraft:stone' % (RX + 3, Y, RZ - 6, RX + 12, Y, RZ))   # 命令搭建: the turbine platform
    _lib.give(ctx, (H + 'machine_industrial_turbine', 3), (H + 'machine_condenser', 1))
    for pos in TURBINES:
        _lib.place(ctx, H + 'machine_industrial_turbine', (pos[0], Y, RZ), 'up', [pos[0] + 0.5, Y, RZ + 3.5])
        got, tp = _lib.core_of(ctx, H + 'machine_industrial_turbine', (pos[0] - 1, Y + 1, RZ - 7), (pos[0] + 1, Y + 3, RZ + 1))
        if got != pos or tp.get('facing') != 'south':
            raise RuntimeError('turbine core %s facing %s, planned %s south' % (got, tp.get('facing'), pos))
    _lib.place(ctx, H + 'machine_condenser', (COND[0], Y, COND[2]), 'up', [COND[0] + 0.5, Y, COND[2] + 3.5])
    if not _lib.is_block(ctx, COND, H + 'machine_condenser'):
        raise RuntimeError('no condenser at %s' % (COND,))

    # levers (core + 3 south + 1 up): T1 twice, T2 once
    _lib.empty_hand(ctx)
    for pos, pulls in zip(TURBINES, (2, 1, 0)):
        lever = (pos[0], pos[1] + 1, pos[2] + 3)
        for _ in range(pulls):
            _lib.use_on(ctx, lever, 'south', [pos[0] + 0.5, Y, RZ + 2.5])
    tk = [(tank(d, 'water'), tank(d, 'steam')) for d in (_lib.block_data(ctx, p) for p in TURBINES)]
    want = [((0, 7500, SHS_ID), (0, 30000, HOT_ID)), ((0, 75000, HOT_ID), (0, 300000, STEAM_ID)), ((0, 750000, STEAM_ID), (0, 3000000, SPENT_ID))]
    ctx.check(eid('turbine-levers'), tk == want, 'turbines (input (fill, max, type), output (fill, max, type)): %s; want %s' % (tk, want))
    if tk != want:
        raise RuntimeError('the turbines are not set for the loop')

    # the return duct: laid by command (命令搭建), typed water with the identifier made in section C
    if not S.get('identifier'):
        raise _lib.Missing('no fluid identifier from the crafting section')
    for a, b in ((DUCTS[0], DUCTS[5]), (DUCTS[6], DUCTS[20]), (DUCTS[21], DUCTS[26])):
        _lib.cmd(ctx, 'fill %d %d %d %d %d %d hbmsntm:fluid_duct_neo' % (a + b))
    # Fluids.java:421-425 (metaOrder): NONE, AIR, AIRBLAST, WATER: water is the fourth entry of the unfiltered list
    _lib.pick_fluid(ctx, 3, [X0 + 12.5, Y, Z0 + 14.5], pitch=-60.0, yaw=0.0)
    mid = DUCTS[12]
    _lib.sneak(ctx, True)
    try:
        _lib.use_center(ctx, mid, 'south', [mid[0] + 0.5, Y, mid[2] + 2.5])
    finally:
        _lib.sneak(ctx, False)
    types = [_lib.block_data(ctx, p).get('Type') for p in DUCTS]
    ctx.check(eid('water-loop'), all(t == WATER_ID for t in types) and len(DUCTS) == 27,
              '%d ducts, types after one sneaking click: %s (want all %d)' % (len(DUCTS), sorted(set(types)), WATER_ID))
    if not all(t == WATER_ID for t in types):
        raise RuntimeError('the return duct is not typed water')

    # loading: rods by shift-click, CO2 barrel and 8 buckets one tick each
    _lib.give(ctx, (CO2_BARREL + '[hbmsntm:meta=%d]' % CO2_ID, 1))   # 预写
    _lib.give(ctx, ('minecraft:water_bucket', BUCKETS))
    _lib.open_gui(ctx, (RX, Y, RZ + 2), 'south', [RX + 0.5, Y, RZ + 4.5], 'ReactorZirnoxScreen', center=True)
    for s in sorted(s for s, e in _lib.inventory(ctx).items() if e['id'] == ROD):
        _lib.shift_click(ctx, _lib.menu_slot(28, s))
    _lib.put_stack(ctx, 28, CO2_BARREL, 24, meta=CO2_ID)
    _lib.server_steps(ctx, 1)
    for _ in range(BUCKETS):
        _lib.put_stack(ctx, 28, 'minecraft:water_bucket', 26)
        _lib.server_steps(ctx, 1)
    d = _lib.block_data(ctx, core)
    rd = rods(d)
    co2, water = tank(d, 'carbondioxide'), tank(d, 'water')
    barrel = _lib.slot_item(d, 26)
    buckets = _lib.slot_count(d, 27, 'minecraft:bucket')
    ok = (sorted(rd) == list(range(24)) and all(i == ROD and life is None for i, life in rd.values())
          and co2 == (16000, 16000, CO2_ID) and (barrel or {}).get('id') == H + 'fluid_barrel_empty' and water == (BUCKETS * 1000, 32000, WATER_ID)
          and buckets == BUCKETS and d.get('heat', 0) == 0 and not d.get('isOn'))
    ctx.check(eid('place-load'), ok, 'reactor core %s; rods in slots %s (%s); CO2 (fill, max, type) %s; slot 26 %s; water %s; empty buckets in '
              'slot 27: %d; heat %s, on %s' % (core, sorted(rd), sorted({i for i, _ in rd.values()}), co2, (barrel or {}).get('id'), water,
                                                 buckets, d.get('heat'), d.get('isOn')))
    if not ok:
        raise RuntimeError('the reactor is not loaded as planned')
    S['built'] = True


def section_run(ctx, S):
    if not S.get('built'):
        raise _lib.Missing('the rig was not built')
    core = S['reactor']
    sim = S['sim']
    hud = _lib.open_gui(ctx, (RX, Y, RZ + 2), 'south', [RX + 0.5, Y, RZ + 4.5], 'ReactorZirnoxScreen', center=True)
    on0 = _lib.block_data(ctx, core).get('isOn')
    ctx.step('click', at=[hud['gui_left'] + 151, hud['gui_top'] + 42], button=0, after=4)
    ctx.step('close')
    g0 = gt(ctx)
    on1 = _lib.block_data(ctx, core).get('isOn')
    advance_to(ctx, g0, 10, 'stage8-tick10')
    d = _lib.block_data(ctx, core)
    ctx.check(eid('switch-on'), not on0 and on1 and (d.get('heat'), d.get('pressure')) == (sim['heat'][10], sim['pressure'][10]),
              'isOn %s -> %s; tick 10: heat %s pressure %s (simulated %d, %d)' % (on0, on1, d.get('heat'), d.get('pressure'), sim['heat'][10], sim['pressure'][10]))

    advance_to(ctx, g0, T_EQ, 'stage8-equilibrium')
    _lib.still(ctx)
    s = loop_state(ctx, core, TURBINES)
    lives = {k: life for k, (i, life) in s['rods'].items()}
    bad = {k: (lives.get(k), T_EQ * (len(NEIGHBOURS[k]) + 1)) for k in range(24) if lives.get(k) != T_EQ * (len(NEIGHBOURS[k]) + 1)}
    ctx.check(eid('equilibrium'), (s['heat'], s['pressure']) == (36159, 70919) == (sim['heat'][T_EQ], sim['pressure'][T_EQ]) and not bad,
              'tick %d: heat %s pressure %s (simulated %d, %d; fixed point 36,159 / 70,919); rod lives off 2,000 x (neighbours + 1): %s'
              % (T_EQ, s['heat'], s['pressure'], sim['heat'][T_EQ], sim['pressure'][T_EQ], bad or 'none'))
    cyc = sim['cycle'][T_EQ]
    t1, t2, t3 = s['t1'], s['t2'], s['t3']
    want = dict(t1=(18 * cyc, 1500 * 18), t2=(2 * 10 * cyc, 15000 * 2), t3=(200 * cyc, 1500 * 200))
    got = dict(t1=(t1['power'], t1['maxPower']), t2=(t2['power'], t2['maxPower']), t3=(t3['power'], t3['maxPower']))
    ctx.check(eid('turbine-power'), cyc == 53 and got == want,
              'superheated steam a tick (simulated) %d (want 53); turbines (power, maxPower) %s, want %s; tanks T1 %s/%s, T2 %s/%s, T3 %s/%s'
              % (cyc, got, want, t1['inp'], t1['out'], t2['inp'], t2['out'], t3['inp'], t3['out']))
    units = water_units_x100(s)
    ctx.check(eid('loop-conservation'), units == BUCKETS * 1000 * 100 and s['r_water'] > 0 and s['r_steam'] < 8000,
              'water units x100 %d (want %d): reactor water %d steam %d, T1 %s/%s, T2 %s/%s, T3 %s/%s, condenser %s/%s'
              % (units, BUCKETS * 100000, s['r_water'], s['r_steam'], t1['inp'][0], t1['out'][0], t2['inp'][0], t2['out'][0],
                 t3['inp'][0], t3['out'][0], s['cond']['inp'][0], s['cond']['out'][0]))

    first = min(sim['depleted'].values())
    centre = sorted(k for k, t in sim['depleted'].items() if t == first)
    advance_to(ctx, g0, first - 1, 'stage8-before-first')
    a = fuel_slots(_lib.block_data(ctx, core))
    advance_to(ctx, g0, first, 'stage8-first')
    rb = rods(_lib.block_data(ctx, core))
    spent = sorted(k for k, (i, _) in rb.items() if i == SPENT_ROD)
    fuel = sorted(k for k, (i, _) in rb.items() if i == ROD)
    ctx.check(eid('center-rods'), first == 50001 and centre == [8, 11, 12, 15] and a == list(range(24)) and spent == centre
              and fuel == [k for k in range(24) if k not in centre],
              'simulated first depletion tick %d slots %s; tick %d fuel slots %s; tick %d spent %s, fuel %s'
              % (first, centre, first - 1, a, first, spent, fuel))

    last = sim['last']
    peaks = dict(heat=0, pressure=0, steam=0, water=None, reads=0, failed=0)

    def watch(c):
        try:
            w = _lib.block_data(c, core)
        except Exception:  # noqa: BLE001 - a missed poll is counted, not fatal
            peaks['failed'] += 1
            return False
        peaks['reads'] += 1
        peaks['heat'] = max(peaks['heat'], w.get('heat', 0))
        peaks['pressure'] = max(peaks['pressure'], w.get('pressure', 0))
        peaks['steam'] = max(peaks['steam'], tank(w, 'steam')[0])
        wt = tank(w, 'water')[0]
        peaks['water'] = wt if peaks['water'] is None else min(peaks['water'], wt)
        return False

    park(ctx)
    need = (last - 1) - (gt(ctx) - g0)
    burn = ctx.sprint(need - 1, until=watch, poll_s=1.0, label='stage8-burn', timeout_s=900)
    e1 = gt(ctx) - g0
    if e1 != last - 1:
        raise RuntimeError('burn sprint ended at tick %d since switch-on, wanted %d' % (e1, last - 1))
    S['burn'] = burn
    b1 = _lib.block_data(ctx, core)
    left = fuel_slots(b1)
    want_left = sorted(k for k, t in sim['depleted'].items() if t == last)
    advance_to(ctx, g0, last, 'stage8-last')
    b2 = _lib.block_data(ctx, core)
    ids2 = [i for k, (i, _) in sorted(rods(b2).items())]
    ok = (left == want_left == [2, 6, 17, 20, 21, 23] and (b1.get('heat'), b1.get('pressure')) == (sim['heat'][last - 1], sim['pressure'][last - 1])
          and last == 116668 and len(ids2) == 24 and set(ids2) == {SPENT_ROD} and (b2.get('heat'), b2.get('pressure')) == (sim['heat'][last], sim['pressure'][last])
          and peaks['reads'] > 0 and peaks['heat'] < MAX and peaks['pressure'] < MAX and peaks['steam'] < 8000 and (peaks['water'] or 0) > 0
          and _lib.is_block(ctx, core, H + 'machine_zirnox'))
    ctx.check(eid('burnout'), ok, 'simulated last depletion %d; tick %d fuel slots %s (simulated %s), heat %s pressure %s (simulated %d, %d); '
              'tick %d: %d rods %s, heat %s pressure %s (simulated %d, %d); polls %d (failed %d): max heat %d, max pressure %d, max steam %d, '
              'min water %s; burn sprint %s ticks in %s s (%s ticks/s)'
              % (last, last - 1, left, want_left, b1.get('heat'), b1.get('pressure'), sim['heat'][last - 1], sim['pressure'][last - 1], last,
                 len(ids2), sorted(set(ids2)), b2.get('heat'), b2.get('pressure'), sim['heat'][last], sim['pressure'][last], peaks['reads'],
                 peaks['failed'], peaks['heat'], peaks['pressure'], peaks['steam'], peaks['water'], burn.get('advanced'), burn.get('wall_s'),
                 burn.get('ticks_per_s')))

    advance_to(ctx, g0, T_STATIC, 'stage8-rest')
    _lib.still(ctx)
    s1 = loop_state(ctx, core, TURBINES)
    _lib.advance(ctx, 20, 'stage8-rest-check')
    _lib.still(ctx)
    s2 = loop_state(ctx, core, TURBINES)
    f1, f2 = flat(s1), flat(s2)
    same, moved = _lib.static_readings(f1, f2)
    resid = s2['t3']['inp'][0]
    ok = (sim['static_from'] == 116842 and sim['heat'][-1] == 31 and (s2['heat'], s2['pressure']) == (31, 32031) and not moved
          and s2['t1']['inp'][0] == 0 and s2['t2']['inp'][0] == 0 and resid <= 495 and resid % 100 == 0
          and water_units_x100(s2) == BUCKETS * 100000)
    ctx.check(eid('static-end'), ok, 'simulated rest from tick %s at heat %d; tick %d: heat %s pressure %s; readings that moved over 20 ticks: %s; '
              'T1 in %s, T2 in %s, T3 in %s; water units x100 %d (want %d)'
              % (sim['static_from'], sim['heat'][-1], T_STATIC, s2['heat'], s2['pressure'], moved or 'none', s2['t1']['inp'], s2['t2']['inp'],
                 s2['t3']['inp'], water_units_x100(s2), BUCKETS * 100000))
    if moved:
        raise RuntimeError('the rig is not at rest: %s' % moved)
    rest = dict(f2)
    if S.get('assembler'):
        rest['assembler_power'] = _lib.block_data(ctx, S['assembler']).get('power')
    S['rest'] = rest


def section_reload(ctx, S):
    before = S['rest']
    g = _lib.reopen(ctx, near=(RX, Y, RZ))
    s = loop_state(ctx, S['reactor'], TURBINES)
    after = flat(s)
    if 'assembler_power' in before:
        after['assembler_power'] = _lib.block_data(ctx, S['assembler']).get('power')
    res = _lib.compare_static(before, after, not_quantity=('isOn',))
    ctx.check(eid('reload'), res['ok'], 'game time %d before leaving, %d after opening and freezing; %s' % (g[0], g[1], res['detail']))


def les_slot0(data):
    it = _lib.slot_item(data, 0)
    if it is None:
        return None
    comps = it.get('components') or {}
    return it.get('id'), _lib.meta_of(it), (comps.get('minecraft:custom_data') or {}).get('life')


def section_les(ctx, S):
    """The LES rod after the reload (the world is frozen from the reopen on)."""
    core = S['reactor']
    open_reactor = lambda: _lib.open_gui(ctx, (RX, Y, RZ + 2), 'south', [RX + 0.5, Y, RZ + 4.5], 'ReactorZirnoxScreen', center=True)
    # one spent rod out by hand (menu slot 0 = reactor slot 0); it is cleared from the inventory afterwards so the survival
    # player does not carry it through the sprint
    open_reactor()
    _lib.shift_click(ctx, 0)
    ctx.step('close')
    if _lib.slot_item(_lib.block_data(ctx, core), 0) is not None:
        raise RuntimeError('reactor slot 0 is not empty after the shift-click')
    _lib.cmd(ctx, 'clear @s %s' % SPENT_ROD)
    # the rod crafted: an empty rod (made in section C's recipe; one more issued, needs_stage 0) and 2 LES billets (预写)
    _lib.give(ctx, (H + 'rod_zirnox_empty', 1), (H + 'billet_les', 2))
    _lib.open_gui(ctx, TABLE, 'south', [TABLE[0] + 0.5, Y, TABLE[2] + 2.5], 'Crafting')
    _lib.craft(ctx, ['ELL'], dict(E=H + 'rod_zirnox_empty', L=H + 'billet_les'))
    ctx.step('close')
    items = _lib.inventory(ctx)
    les = [(s, e) for s, e in items.items() if e['id'] == ROD and e['meta'] == LES_META]
    made = (len(les) == 1 and les[0][1]['count'] == 1 and 'life' not in (les[0][1]['components'].get('minecraft:custom_data') or {})
            and _lib.count(ctx, H + 'billet_les', items=items) == 0 and _lib.count(ctx, H + 'rod_zirnox_empty', items=items) == 0)
    if not les:
        raise _lib.Missing('no LES rod was crafted')
    open_reactor()
    _lib.shift_click(ctx, _lib.menu_slot(28, les[0][0]))
    ctx.step('close')
    d0 = _lib.block_data(ctx, core)
    g1 = gt(ctx)
    in0 = les_slot0(d0)
    h0 = d0.get('heat')
    others = sorted({i.get('id') for i in d0.get('Items', []) if 1 <= i.get('Slot', -1) <= 23})
    sim = simulate_single(h0, LES_LIFE + 2)
    advance_to(ctx, g1, LES_LIFE, 'stage8-les')
    a = _lib.block_data(ctx, core)
    advance_to(ctx, g1, LES_LIFE + 1, 'stage8-les-spent')
    b = _lib.block_data(ctx, core)
    advance_to(ctx, g1, LES_LIFE + 2, 'stage8-les-after')
    c = _lib.block_data(ctx, core)
    hp = [(x.get('heat'), x.get('pressure')) for x in (a, b, c)]
    want_hp = [(sim['heat'][t], sim['pressure'][t]) for t in (LES_LIFE, LES_LIFE + 1, LES_LIFE + 2)]
    # the spent rod out and into the crafting table
    open_reactor()
    _lib.shift_click(ctx, 0)
    ctx.step('close')
    before = _lib.inventory_counts(ctx)
    _lib.open_gui(ctx, TABLE, 'south', [TABLE[0] + 0.5, Y, TABLE[2] + 2.5], 'Crafting')
    _lib.craft(ctx, ['W'], dict(W=LES_SPENT))
    ctx.step('close')
    got = _lib.delta(_lib.inventory_counts(ctx), before)
    want_craft = {H + 'waste_schrabidium@1': 2, H + 'rod_zirnox_empty': 1, LES_SPENT: -1}
    ok = (made and in0 == (ROD, LES_META, None) and others == [SPENT_ROD] and h0 == 31 and sim['depleted'] == LES_LIFE + 1
          and les_slot0(a) == (ROD, LES_META, LES_LIFE) and les_slot0(b) == (LES_SPENT, 0, None)
          and hp == want_hp == [(4000, 36150), (4000, 36150), (3856, 36000)] and got == want_craft)
    ctx.check(eid('les-rod'), ok, 'LES rod crafted %s (inventory %s); slot 0 after the shift-click %s, slots 1-23 %s, heat %s; tick %d slot 0 %s; '
              'tick %d slot 0 %s; ticks %d/%d/%d (heat, pressure) %s, simulated %s (spent at %s); crafting the spent rod: %s (want %s)'
              % (made, les, in0, others, h0, LES_LIFE, les_slot0(a), LES_LIFE + 1, les_slot0(b), LES_LIFE, LES_LIFE + 1, LES_LIFE + 2,
                 hp, want_hp, sim['depleted'], got, want_craft))


def run(ctx):
    _lib.setup_world(ctx, freeze=True)
    _lib.cmd(ctx, 'gamemode survival')
    _lib.cmd(ctx, 'clear @s', allow_error=True)
    _lib.go_near(ctx, X0 + 14, Y, Z0)
    corners = [(x, z) for x in (X0 - 8, RX + 16) for z in (Z0 - 10, Z0 + 16)]
    for _ in range(60):
        if all(ctx.server('execute if loaded %d %d %d' % (x, Y, z), allow_error=True)['result'] == 1 for x, z in corners):
            break
        ctx.step('wait', ticks=10)
    else:
        raise RuntimeError('the chunks of the site did not load: %s' % corners)
    _lib.cmd(ctx, 'fill %d %d %d %d %d %d minecraft:air' % (X0 - 8, Y, Z0 - 10, RX + 16, Y + 8, Z0 + 16), allow_error=True)
    S = dict(sim=simulate())
    for name, fn, ids in (('A (assembly)', section_assembly, SEC_ASM), ('C (crafting)', section_crafting, SEC_CRAFT),
                          ('B (rig)', section_build, SEC_BUILD), ('R (run)', section_run, SEC_RUN)):
        _lib.section(ctx, ids, lambda fn=fn: fn(ctx, S), 'section %s stopped' % name)
        _lib.sneak(ctx, False)
    if 'rest' not in S:
        ctx.not_run(eid('reload'), 'the rig did not reach its resting state (section R stopped or never started), so nothing static to compare')
        ctx.not_run(eid('les-rod'), 'the rig did not reach its resting state (section R stopped or never started), so no free slot for the LES rod')
        return
    _lib.section(ctx, [eid('reload')], lambda: section_reload(ctx, S), 'reload stopped')
    _lib.section(ctx, [eid('les-rod')], lambda: section_les(ctx, S), 'section L (LES rod) stopped')
    _lib.sneak(ctx, False)
