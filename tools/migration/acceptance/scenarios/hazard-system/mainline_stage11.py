"""Main line, stage 11 (protection): Geiger counter and dosimeter, the player decontaminator, hazmat suits of three grades,
the gas mask and its filters, Rad-X and RadAway, played in survival, each protection paired with the same hazard unprotected.

The player gets the stage's start items by command (HANDOVER below is the stage-11 start list; GIVE takes from it right before
each use, so a stack holds exactly what the next step needs; ISSUED lists what is handed out besides, with the reason). Every
protection item of the stage is crafted in a crafting table by real clicks (red and grey hazmat cloth, the twelve suit pieces,
the Geiger counter, the dosimeter, the radiation absorber and the decontaminator, the gas mask and two filters, Rad-X, the IV
bag and RadAway). Armour is put on by a right-click with the piece in hand and taken off by a shift-click on the armour slot,
filters are screwed in by a right-click while the mask is worn, pills and bags are used by a right-click. The decontaminator
and the ores are placed by hand (the nether coal ore by command: it comes only from Nether world generation) and the ores are
mined with an iron pickaxe, which leaves their gas where they stood.

Survival matters: a creative or spectator player takes no radiation (original ContaminationUtil.java:284-285; NEO
ContaminationUtil.java:179), so the world is created in survival (drive.py --gamemode survival --difficulty normal) and the
run checks the game mode on the server. Natural regeneration is switched off so that health and food readings move only with
the hazards.

Timing: a player keeps ticking while the world is frozen (vanilla TickRateManager.isEntityFrozen exempts players), so the
hazards of carried items, potion effects and gas contacts go on in a frozen world, while block entities (the decontaminator)
and block ticks (gas drifting and decaying) stop. Hence:
- dose windows run in the unfrozen world: read A (server data and game time in one server task), /tick sprint from the
  unfrozen world, read B; every game tick between A and B is one player tick, and the expected value is the original's
  per-tick arithmetic (Java float) repeated (B.game_time - A.game_time) times;
- gas pairs run in the frozen world, so the gas stays in the cell where the ore was mined; a stationary player touches the gas
  only when its client sends a position packet, so the number of contacts is not fixed by code and those checks are
  relations (each radon contact adds 0.05 RAD and 1 asbestos together) and signs, not tick counts;
- the decontaminator is timed with freeze + tick step (exactly 100 block-entity ticks).

Readings are the player's server data (`data get entity @p`: the living attachment hfr_radiation / hfr_asbestos /
hfr_blacklung, Health, Fire, food, active effects, inventory and armour slots); the Geiger counter and dosimeter readouts are
the chat lines the server sends. After the line the world is left and opened again and the static readings of every group
are compared.

Positions (flat world, feet at y = -60): crafting table T, dose site M (no ore within 30 blocks while ingots are carried),
decontaminator D, ore row R (uranium, asbestos, nether coal 4 blocks apart), water cell W for the hot pair.
"""
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

f32 = _lib.f32
H = _lib.H
cmd = _lib.cmd

SCENARIO = dict(
    id='hazard-system.mainline_stage11',
    feature='hazard-system',
    features=['hazard-system', 'radiation-detection', 'gas-masks', 'hazmat-suits', 'radiation-medicine'],
    title='Main line stage 11: protection - Geiger counter, dosimeter, decontaminator, hazmat suits, gas masks and filters, Rad-X, RadAway',
    group='solo',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

# The stage-11 start list (item, the stage it is first obtainable in); "block:" rows are world-generation blocks.
HANDOVER = [
    ('block:hbmsntm:ore_oil', 1), ('hbmsntm:arc_electrode_graphite', 2), ('hbmsntm:ball_fireclay', 2), ('hbmsntm:billet_silicon', 4),
    ('hbmsntm:catalyst_clay', 4), ('hbmsntm:centrifuge_element', 4), ('hbmsntm:cinnabar', 1), ('hbmsntm:circuit_analog_board', 4),
    ('hbmsntm:circuit_capacitor', 4), ('hbmsntm:circuit_integrated_board', 4), ('hbmsntm:circuit_printed_board', 4),
    ('hbmsntm:circuit_printed_silicon_wafer', 4), ('hbmsntm:circuit_vacuum_tube', 4), ('hbmsntm:coil_copper', 2),
    ('hbmsntm:coil_copper_ring', 2), ('hbmsntm:coil_tungsten', 1), ('hbmsntm:concrete_asbestos', 4), ('hbmsntm:concrete_smooth', 4),
    ('hbmsntm:drill_titanium', 4), ('hbmsntm:fluorite', 7), ('hbmsntm:furnace_combination', 2), ('hbmsntm:heat_boiler', 3),
    ('hbmsntm:heater_firebox', 3), ('hbmsntm:ingot_aluminium', 1), ('hbmsntm:ingot_beryllium', 1), ('hbmsntm:ingot_copper', 1),
    ('hbmsntm:ingot_desh', 5), ('hbmsntm:ingot_firebrick', 2), ('hbmsntm:ingot_graphite', 9), ('hbmsntm:ingot_lead', 1),
    ('hbmsntm:ingot_niobium', 4), ('hbmsntm:ingot_polymer', 5), ('hbmsntm:ingot_raw@41', 2), ('hbmsntm:ingot_red_copper', 2),
    ('hbmsntm:ingot_rubber', 5), ('hbmsntm:ingot_saturnite', 5), ('hbmsntm:ingot_steel', 2), ('hbmsntm:ingot_titanium', 1),
    ('hbmsntm:ingot_tungsten', 1), ('hbmsntm:ingot_uranium', 7), ('hbmsntm:ingot_zirconium', 1), ('hbmsntm:machine_arc_furnace', 4),
    ('hbmsntm:machine_arc_welder', 4), ('hbmsntm:machine_assembly_machine', 4), ('hbmsntm:machine_blast_furnace', 2),
    ('hbmsntm:machine_catalytic_cracker', 5), ('hbmsntm:machine_centrifuge', 4), ('hbmsntm:machine_chemical_plant', 4),
    ('hbmsntm:machine_crucible', 2), ('hbmsntm:machine_crystallizer', 4), ('hbmsntm:machine_press', 2), ('hbmsntm:machine_refinery', 5),
    ('hbmsntm:machine_shredder', 4), ('hbmsntm:machine_soldering_station', 4), ('hbmsntm:machine_vacuum_distill', 5),
    ('hbmsntm:machine_well', 5), ('hbmsntm:mold_base', 2), ('hbmsntm:motor', 2), ('hbmsntm:motor_desh', 5), ('hbmsntm:nugget_uranium', 7),
    ('hbmsntm:nugget_zirconium', 1), ('hbmsntm:ore_beryllium', 1), ('hbmsntm:ore_cobalt', 1), ('hbmsntm:ore_lead', 1),
    ('hbmsntm:ore_lead_deepslate', 1), ('hbmsntm:ore_titanium_deepslate', 1), ('hbmsntm:ore_uranium_deepslate', 7),
    ('hbmsntm:pipe_copper', 1), ('hbmsntm:pipe_steel', 2), ('hbmsntm:plate_cast@0', 2), ('hbmsntm:plate_cast@11', 2),
    ('hbmsntm:plate_cast@12', 2), ('hbmsntm:plate_cast@5', 2), ('hbmsntm:plate_copper', 1), ('hbmsntm:plate_dura_steel', 2),
    ('hbmsntm:plate_iron', 1), ('hbmsntm:plate_lead', 1), ('hbmsntm:plate_polymer', 1), ('hbmsntm:plate_steel', 2),
    ('hbmsntm:plate_titanium', 1), ('hbmsntm:powder_aluminium', 2), ('hbmsntm:powder_coal', 4), ('hbmsntm:powder_desh_mix', 4),
    ('hbmsntm:powder_lead', 4), ('hbmsntm:powder_nitan_mix', 4), ('hbmsntm:rbmk_blank', 9), ('hbmsntm:rbmk_outgasser', 9),
    ('hbmsntm:resource_limestone', 1), ('hbmsntm:shell_steel', 2), ('hbmsntm:shell_titanium', 1), ('hbmsntm:sphere_steel', 2),
    ('hbmsntm:stamp_stone_flat', 2), ('hbmsntm:steel_grate', 2), ('hbmsntm:steel_scaffold', 2), ('hbmsntm:sulfur', 1),
    ('hbmsntm:tank_steel', 2), ('hbmsntm:transformer', 4), ('hbmsntm:wire_copper', 1), ('hbmsntm:wire_gold', 1), ('hbmsntm:wire_lead', 1),
    ('hbmsntm:wire_red_copper', 2), ('hbmsntm:wire_tungsten', 1),
]
# Not on the start list, handed out where the line needs them; each was obtainable at an earlier stage (the stage named) or is
# vanilla. hazmat_cloth and filter_coal are assembly-machine products (AssemblyMachineRecipes.java:477-485; original
# AssemblyMachineRecipes.java:118-123), powder_asbestos a shredder product, ore_asbestos a world-generation ore taken with
# silk touch, the hot natural-uranium waste comes out of a burnt-up ZIRNOX rod (DepletedFuelItem.java:15-22).
# (item, the stage it is obtainable in, the count handed out; the note prints the count first)
ISSUED = [('hbmsntm:hazmat_cloth', 4, 124), ('hbmsntm:filter_coal', 4, 1), ('hbmsntm:powder_asbestos', 4, 2),
          ('hbmsntm:ore_asbestos', 0, 1), ('hbmsntm:waste_natural_uranium[hbmsntm:meta=1]', 8, 1)]
VANILLA = ['gold_ingot', 'oak_planks', 'glass_pane', 'iron_bars', 'redstone', 'pumpkin_seeds', 'iron_pickaxe', 'water_bucket']
# 预写: the only state written by command that the line could not make itself. The nether coal ore (carbon monoxide source,
# OutgasBlock.java:49-51; original BlockOutgas.java:53-55) comes only from Nether world generation; it is set by command.
PREWRITES = ['预写 the nether coal ore of the monoxide pair is set by command (no earlier stage yields the ore as an item)']

Y = -60                          # feet on the flat world
X0, Z0 = 6000, 6000
TABLE = (X0, Y, Z0)              # crafting table (set by command, as on every stage)
AT_TABLE = [X0 + 0.5, Y, Z0 + 2.5]
M = [X0 + 0.5, Y, Z0 + 30.5]     # dose site: 30 blocks from the ores
DECON = (X0 + 8, Y, Z0 + 30)     # placed by hand on the ground
ON_DECON = [DECON[0] + 0.5, Y + 1, DECON[2] + 0.5]
NEAR_DECON = [DECON[0] + 0.5, Y, DECON[2] + 3.5]
U_ORE = (X0 - 40, Y, Z0)         # uranium ore, placed by hand
A_ORE = (X0 - 44, Y, Z0)         # asbestos ore, placed by hand
C_ORE = (X0 - 48, Y, Z0)         # nether coal ore, set by command (预写)
WATER = (X0 + 30, Y, Z0 + 30)    # water bucket emptied on the ground for the hot pair
DRY = [X0 + 26.5, Y, Z0 + 30.5]
NEUTRAL = [X0 + 0.5, Y, Z0 + 15.5]

# ---- numbers from the code (original first, NEO second)
U_LEVEL = f32(0.35)               # u * ingot: HazardRegistry.java:88,134, OreDictManager.java:347; NEO HazardRegistry.java:92,138,332
N_INGOTS = 16
POWDER = 3                        # powder = ingot * powder_mult = 3: HazardRegistry.java:134,138-139; NEO HazardRegistry.java:138,142-143
COAL_N = 4                        # coal dust stack: level 3 x 4 = 12 -> min(12, 10) = 10 per tick
MAX_FILTER = 20000                # ItemFilter.java:17; NEO NtmItems.java:1043-1045
MAX_BLACKLUNG = 2 * 60 * 60 * 20  # HbmLivingProps.java:46; NEO HbmLivingAttachments.java:53
SUIT = dict(helmet=0.2, chest=0.4, legs=0.3, boots=0.1)        # HazmatRegistry.java:34-37; NEO HazmatRegistry.java:40-43
GRADE = dict(yellow=0.6, red=1.0, grey=2.0)                    # HazmatRegistry.java:56-58; NEO HazmatRegistry.java:59-61
PIECES = dict(
    yellow=dict(helmet='hazmat_helmet', chest='hazmat_plate', legs='hazmat_legs', boots='hazmat_boots'),
    red=dict(helmet='hazmat_helmet_red', chest='hazmat_plate_red', legs='hazmat_legs_red', boots='hazmat_boots_red'),
    grey=dict(helmet='hazmat_helmet_grey', chest='hazmat_plate_grey', legs='hazmat_legs_grey', boots='hazmat_boots_grey'))
ARMOR_SLOT = dict(boots=100, legs=101, chest=102, helmet=103)  # player NBT Inventory slots of the armour
MENU_SLOT = dict(helmet=5, chest=6, legs=7, boots=8)           # InventoryMenu armour slots
RADX_RES = f32(0.2)              # HazmatRegistry.java:213-214; NEO HazmatRegistry.java:139-140
RADX_TICKS = 3 * 60 * 20         # ItemPill.java:57-59; NEO PillItem.java:36-38
RADX_USE_TICKS = 10              # ItemPill.java:123-125; NEO PillItem.java:75
RADAWAY_TICKS = 140              # ItemSimpleConsumable.java:139-141; NEO SimpleConsumableItem.java:104-106
DECON_STEP = f32(-0.5)           # TileEntityDecon.java:22-29; NEO DecontaminatorBlockEntity.java:31-38
HOT_TIME = 5                     # registerOtherWaste: hot waste HOT 5: HazardRegistry.java:629-636; NEO HazardRegistry.java:598-606

HS, RD, GM, HZ, RM = 'hazard-system', 'radiation-detection', 'gas-masks', 'hazmat-suits', 'radiation-medicine'

E = [
    (HS, 'start-items', '记录：命令发放的起点物品（阶段 11 交接清单里本线用到的、清单之外按更早阶段可得发放的、原版材料），以及预写的一项',
     '阶段 11 交接清单（本文件 HANDOVER、ISSUED、VANILLA、PREWRITES）'),
    (HS, 'survival', '服务端读到玩家是生存模式（playerGameType 0）：创造与旁观的玩家不受辐射，本阶段的成对读数只在生存下有意义',
     '原版 ContaminationUtil.java:284-285；NEO ContaminationUtil.java:179'),
    (HS, 'dose-unprotected', '不穿防护，物品栏里 16 个铀锭（每个 0.35 RAD/s）：在不冻结的世界里两次读数之间，每个游戏刻剂量加 f32(f32(0.35×16)/20)=0.28，'
                             '按 Java float 逐刻累加 Δg 次后与读数 B 完全相等（Δg 为两次读数的游戏时间差）',
     '原版 HazardTypeRadiation.java:25-45、ContaminationUtil.java:34-44,265-300、HbmLivingProps.java:89-101、HazardSystem.java:197-215、'
     'ModEventHandler.java:984,1032、HazardRegistry.java:88,134；NEO HazardTypeRadiation.java:23-52、ContaminationUtil.java:63-67,167-189、'
     'HbmLivingAttachments.java:85-93、CommonEvents.java:172-182'),
    (HS, 'coal-dust-pair', '煤粉成对：不戴面具时物品栏里 4 个煤粉（每刻 min(3×4,10)=10 黑肺，玩家的黑肺在 0 与上限一半之间时每刻再减 1），'
                           'Δg 刻后黑肺按逐刻模拟（每刻 +10 −1）等于读数 B；戴面具加标准滤芯（粗颗粒）时黑肺只按每刻 −1 衰减、不增加',
     '原版 HazardRegistry.java:175-178、OreDictManager.java:335、HazardTypeCoal.java:22-34、EntityEffectHandler.java:505-509、ArmorUtil.java:39；'
     'NEO HazardRegistry.java:170-172（粉末等级 3）、HazardTypeCoal.java:23-33、EntityEffectHandler.java:270-284、ArmorUtil.java:36'),
    (HS, 'asbestos-dust-pair', '石棉粉成对：不戴面具时物品栏里 1 个石棉粉（等级 3），每刻石棉 +3，Δg 刻后增量正好 3×Δg；戴面具加标准滤芯（细颗粒）时石棉不变，'
                               '滤芯每刻损耗 3，Δg 刻后滤芯耐久损耗正好 3×Δg',
     '原版 HazardTypeAsbestos.java:21-31、OreDictManager.java:424、HazardRegistry.java:134,138-139、ArmorUtil.java:39,332-353；'
     'NEO HazardTypeAsbestos.java:23-31、HazardRegistry.java:403、ArmorUtil.java:36,206-231'),
    (HS, 'hot-pair', '烫手物品成对：穿整套灰色防护服手持热的天然铀废料（HOT 5），在干地上每刻被点燃 ceil(5)×20=100 刻、同一刻玩家自身刻减 1，读到 Fire=99；'
                     '站进水里（水桶倒出的水源）时不再被点燃，Fire≤0',
     '原版 HazardTypeHot.java:20-32、HazardRegistry.java:629-636、ModEventHandler.java:984；NEO HazardTypeHot.java:19-39、HazardRegistry.java:598-606'),
    (HS, 'sickness-pair', '辐射病成对：穿整套灰色防护服拿 64 个铀锭冲刺不少于 1,260 刻，剂量按灰色倍率逐刻算准、始终低于 200，食物能量（4×饱和+4×饥饿−消耗）不变；'
                          '不穿防护拿同样 64 个铀锭直到剂量超过 200 后拿走，再冲刺不少于 1,260 刻，剂量高于 200 时每 1,200 刻必有一刻加饥饿 19 级 60 刻，'
                          '窗口里至少有一次完整的 60 刻（1.21 原版饥饿效果每刻消耗 0.005×20），食物能量至少下降 6',
     '原版 EntityEffectHandler.java:233,267-269,300,318-329；NEO EntityEffectHandler.java:153,175-178,200-203,219-230'),
    (HS, 'reload', '退出并重开世界后：玩家存档里的剂量与石棉量（非默认、静止）与退出前相同',
     '原版 HbmLivingProps.java:328-352,356-380（saveNBTData、loadNBTData）；NEO HbmLivingAttachments.java:237-281、ModAttachments.java:16-21'),

    (RD, 'craft', '工作台真实点击：金锭、2 橡胶、2 金线、集成电路板、钢板、2 铍锭 -> 手持盖革计数器；6 木板、玻璃板、真空管、铍锭 -> 剂量计；'
                  '4 铜锭、4 煤粉、铅粉 -> 辐射吸收器；4 铍锭、铁栏杆、3 钢锭、吸收器 -> 玩家去污器',
     '原版 ToolRecipes.java:113-114、CraftingManager.java:627,631；NEO 生成配方 geiger_counter、dosimeter、rad_absorber、decontaminator'),
    (RD, 'geiger-unprotected', '不穿防护拿 16 个铀锭，右键盖革计数器：环境总辐射量 5.6 RAD/s（20 刻的 0.28 按 float 累加后截到 0.1），玩家污染量为当时剂量截到 0.1，'
                               '玩家辐射抗性 0.0% (0.0)',
     '原版 ContaminationUtil.java:155-195、EntityEffectHandler.java:68-70；NEO ContaminationUtil.java:76-95、EntityEffectHandler.java:52-55、GeigerCounterItem.java:69-79'),
    (RD, 'geiger-suits', '同样 16 个铀锭，穿整套黄色与整套灰色防护服各右键一次盖革计数器：环境总辐射量仍是 5.6（未乘抗性）；抗性显示按原版的 float 累加：'
                         '黄色 74.88% (0.59)，灰色 99.0% (2.0)',
     '原版 ContaminationUtil.java:164-165,190-194、HazmatRegistry.java:168-181,201-218；NEO ContaminationUtil.java:80-81,94、HazmatRegistry.java:129-143'),
    (RD, 'dosimeter', '同样 16 个铀锭，右键剂量计：环境辐射超过 3.6 时显示 >3.6 RAD/s',
     '原版 ContaminationUtil.java:197-211；NEO ContaminationUtil.java:97-110、DosimeterItem.java:62-72'),
    (RD, 'decontaminator', '去污器成对：冻结的世界里站在去污器旁 100 刻剂量不变；站在去污器上 100 刻（冻结再步进），剂量按每刻 −0.5 正好减 50',
     '原版 TileEntityDecon.java:18-30；NEO DecontaminatorBlockEntity.java:25-39'),
    (RD, 'reload', '退出并重开世界后：物品栏里的盖革计数器与剂量计各 1 个、去污器方块仍在',
     '原版 TileEntityDecon（无存档字段）；NEO DecontaminatorBlock.java:15'),

    (GM, 'craft', '工作台真实点击：4 钢板、2 玻璃板、铁板 -> 防毒面具；铁板、活性炭滤芯 -> 标准滤芯；8 锆粒、催化黏土 -> 一氧化碳滤芯；'
                  '戴上面具后手持滤芯右键，滤芯装进面具（面具数据里有 hfr_Filter）',
     '原版 ArmorRecipes.java:154、ConsumableRecipes.java:217-218、ItemFilter.java:23-72；NEO 生成配方 gas_mask、gas_mask_filter、gas_mask_filter_mono、'
     'GasMaskFilterItem.java:31-80、ArmorUtil.java:102-112'),
    (GM, 'radon-pair', '氡气成对：用铁镐挖开手放的铀矿，原位留下氡气（冻结的世界里不飘散）；不戴面具站进去，每次接触剂量 +0.05（不计抗性）、石棉 +1，'
                       '读数 B 的剂量增量正好是 0.05 按 float 累加石棉增量那么多次，且至少接触一次；戴面具加标准滤芯（细颗粒）后，剂量与石棉都不变，滤芯损耗至少 1',
     '原版 BlockGasRadon.java:25-38、BlockOutgas.java:40-48,94-101、ContaminationUtil.java:295；NEO GasRadonBlock.java:28-37、OutgasBlock.java:41-47,89-93'),
    (GM, 'asbestos-gas-pair', '石棉粉尘成对：挖开手放的石棉矿，原位留下石棉粉尘；不戴面具站进去石棉至少 +1；戴面具加标准滤芯后石棉不变，而且石棉粉尘不损耗滤芯',
     '原版 BlockGasAsbestos.java:32-41、BlockOutgas.java:57-60,94-101；NEO GasAsbestosBlock.java:37-43、OutgasBlock.java:53-56,89-93'),
    (GM, 'monoxide-pair', '一氧化碳成对（预写：下界煤矿用命令放置）：挖开后原位留下一氧化碳；面具装标准滤芯（类型不对，没有一氧化碳防护）站进去，'
                          '每次接触扣 1 点生命（无视护甲），至少扣 1；换装一氧化碳滤芯后生命不变，一氧化碳滤芯损耗至少 1',
     '原版 BlockGasMonoxide.java:22-33、ModDamageSource.java:39、ArmorUtil.java:39-40、BlockOutgas.java:53-55；NEO GasMonoxideBlock.java:25-34、'
     'ArmorUtil.java:36-37、OutgasBlock.java:49-51'),
    (GM, 'filter-used-up', '滤芯用尽：戴面具装标准滤芯、拿 1 个石棉粉，从不冻结的世界冲刺；滤芯每刻损耗 3，损耗加 3 后超过 20,000 的那一刻被卸下，此后每刻石棉 +3；'
                           '按读数 A 的损耗与石棉逐刻模拟 Δg 刻，读数 B 的石棉与“滤芯已卸下”都与模拟相同',
     '原版 ArmorUtil.java:332-353、ItemFilter.java:17、HazardTypeAsbestos.java:27-30；NEO ArmorUtil.java:206-231、NtmItems.java:1043、HazardTypeAsbestos.java:26-30'),
    (GM, 'reload', '退出并重开世界后：一氧化碳滤芯的耐久损耗（非默认）与面具都与退出前相同',
     '原版 ArmorUtil.java:250-310（滤芯存在面具 NBT）；NEO ArmorUtil.java:100-124'),

    (HZ, 'craft', '工作台真实点击：2 防护布+红石 -> 红色防护布（做 50 个）；红色防护布、2 橡胶、铁板、铅板 -> 灰色防护布（做 25 个）；'
                  '三种布各做头盔、胸甲、护腿、靴子（5/8/7/4 黄布，6/8/7/4 红布或灰布）',
     '原版 CraftingManager.java:101-102、ArmorRecipes.java:122-133；NEO 生成配方 hazmat_cloth_red、hazmat_cloth_grey 与十二件防护服'),
    (HZ, 'yellow', '整套黄色防护服，16 个铀锭：抗性按原版 float 累加（靴、腿、胸、头的顺序，每次 float += double）为 0.59999996，倍率 (float)10^-抗性 = 0.25118867，'
                   '每刻剂量 f32(0.28×倍率)，Δg 刻逐刻累加后等于读数 B（行内注释的 50% 不是减免）',
     '原版 HazmatRegistry.java:34-37,56-58,68-71,168-181,201-218、ContaminationUtil.java:34-44,295；NEO HazmatRegistry.java:40-43,58-67,129-143、ContaminationUtil.java:63-67,186'),
    (HZ, 'red', '整套红色防护服，16 个铀锭：抗性 1.0，倍率 0.1，Δg 刻逐刻累加后等于读数 B',
     '原版 HazmatRegistry.java:73-76,201-218；NEO HazmatRegistry.java:69-72,129-143'),
    (HZ, 'grey', '整套灰色防护服，16 个铀锭：抗性 2.0，倍率 0.01，Δg 刻逐刻累加后等于读数 B',
     '原版 HazmatRegistry.java:78-81,201-218；NEO HazmatRegistry.java:74-77,129-143'),
    (HZ, 'partial', '只戴灰色头盔，16 个铀锭：先把各件抗性相加再取幂，抗性 0.4，倍率 (float)10^-0.4，Δg 刻逐刻累加后等于读数 B',
     '原版 HazmatRegistry.java:78,201-218；NEO HazmatRegistry.java:74,129-143'),
    (HZ, 'reload', '退出并重开世界后：十二件防护服仍在物品栏里，数量与耐久与退出前相同',
     '原版 ArmorHazmat（物品）；NEO HazmatArmorItem.java'),

    (RM, 'craft', '工作台真实点击：2 煤粉、萤石 -> 防辐射药；2 橡胶、铁板 -> 4 个空血袋；右键空血袋：生命 −5、得到血袋；血袋、煤粉、南瓜种子 -> 消辐宁',
     '原版 ConsumableRecipes.java:120,143,147、ItemSimpleConsumable.java:113-118；NEO 生成配方 radx、iv_empty、radaway、SimpleConsumableItem.java:108-116'),
    (RM, 'radx', '吃防辐射药：效果从 3,600 刻起、每刻减 1，读数时已过的刻数在 0 与（读数与进食前的游戏刻之差 − 食用 10 刻 + 1）之间，剂量窗口 Δ 刻后剩余时长恰少 Δ；'
                 '不穿防护拿 16 个铀锭，抗性 0.2，倍率 (float)10^-0.2 = 0.63095737，Δg 刻逐刻累加后等于读数 B（对照 dose-unprotected）',
     '原版 ItemPill.java:30-34,57-59,123-125、HazmatRegistry.java:213-214；NEO PillItem.java:36-38,61-75、HazmatRegistry.java:139-140'),
    (RM, 'radaway', '右键消辐宁：消辐宁效果 140 刻，每刻剂量 −1；没有别的辐射源时，效果结束后剂量正好比用之前少 140（float 逐刻相减），空血袋还回 1 个',
     '原版 ItemSimpleConsumable.java:61-65,86-89,139-141、HbmPotion.java:125-127,160；NEO SimpleConsumableItem.java:68-72,93-106、RadawayEffect.java:14-23'),
    (RM, 'reload', '退出并重开世界后：空血袋与剩下的血液药品数量与退出前相同', '原版 ItemSimpleConsumable；NEO SimpleConsumableItem.java'),
]


def expectations():
    return [dict(id='%s.%s' % (f, i), text=t, source=s) for f, i, t, s in E]


def eid(f, i):
    return '%s.%s' % (f, i)


GROUP_IDS = {}
for _f, _i, _t, _s in E:
    GROUP_IDS.setdefault(_f, []).append(eid(_f, _i))


# ---------------------------------------------------------------- the original's arithmetic (Java float)

def resistance(pieces, radx=False):
    """HazmatRegistry.getResistance(EntityPlayer) of the original (:201-218): res is a float, every armour slot from boots to
    helmet adds its double resistance with `res += double`, i.e. (float)(res + d); Rad-X adds 0.2F."""
    res = 0.0
    for slot in ('boots', 'legs', 'chest', 'helmet'):
        grade = pieces.get(slot)
        d = GRADE[grade] * SUIT[slot] if grade else 0.0
        res = f32(res + d)
    if radx:
        res = f32(res + RADX_RES)
    return res


def mod_of(res):
    """calculateRadiationMod (original ContaminationUtil.java:34-44): (float) Math.pow(10.0F, -res)."""
    return f32(10.0 ** (-res))


def per_tick(n_ingots):
    """HazardTypeRadiation.onUpdate (original :25-45): level *= stackSize; rad = level / 20F."""
    return f32(f32(U_LEVEL * n_ingots) / 20.0)


def sim_add(value, n, inc, lo=0.0, hi=2500.0):
    """HbmLivingProps.incrementRadiation (original :89-101): float add, then clamped to 0..2500, n times."""
    for _ in range(n):
        value = f32(value + inc)
        value = hi if value > hi else lo if value < lo else value
    return value


def rad_after(r0, ticks, n_ingots, mod):
    return sim_add(r0, ticks, f32(per_tick(n_ingots) * mod))


def env_readout(n_ingots):
    """radBuf = radEnv of the last 20 ticks (EntityEffectHandler.java:68-70): 20 float adds of the unmodified amount; the
    readout truncates to 0.1 (ContaminationUtil.java:162)."""
    s = 0.0
    for _ in range(20):
        s = f32(s + per_tick(n_ingots))
    return int(s * 10) / 10.0


def res_readout(res):
    """ContaminationUtil.java:164-165: res % = ((int)(10000 - mod*10000)) / 100, coefficient = ((int)(res*100)) / 100."""
    m = mod_of(res)
    return int(10000.0 - m * 10000.0) / 100.0, int(res * 100.0) / 100.0


def jstr(d):
    """Java Double.toString for the short values the readouts print."""
    return '%d.0' % d if d == int(d) else repr(d)


def sim_filter_asbestos(dmg, asb, ticks, level=POWDER):
    """HazardTypeAsbestos with a filter (original :27-30, ArmorUtil.java:332-353): while a filter is installed it takes `level`
    damage a tick and is removed on the tick its damage would exceed the maximum; without one asbestos rises by min(level, 10)."""
    removed_at = None
    for t in range(1, ticks + 1):
        if dmg is not None:
            dmg += level
            if dmg > MAX_FILTER:
                dmg, removed_at = None, t
        else:
            asb += min(level, 10)
    return dmg, asb, removed_at


def sim_blacklung(bl, ticks, add):
    """Per player tick: the coal hazard adds `add` (HazardTypeCoal.java:27-28), then handleLungDisease takes 1 off while
    0 < bl < maxBlacklung / 2 (EntityEffectHandler.java:505-509)."""
    for _ in range(ticks):
        bl += add
        if 0 < bl < MAX_BLACKLUNG * 0.5:
            bl -= 1
    return bl


# ---------------------------------------------------------------- server readings of the player

LIVING = 'hbmsntm:ntm_living_attachments'


def pdata(ctx):
    """The player's server data in one server task: dict(g, rad, asb, bl, health, fire, food, sat, exh, mode, effects, inv)."""
    r = ctx.server('data get entity @p')
    lines = [m for m in r['messages'] if m.strip()]
    # the reply folds lists longer than 128 entries into "<...>" (vanilla TextComponentTagVisitor): only the recipe book is
    # that long, and it is not read
    d = _lib.data_value(lines[-1].replace(', <...>', '').replace('<...>', ''))
    att = (d.get('neoforge:attachments') or {}).get(LIVING) or {}
    effects = {e.get('id'): (e.get('duration'), e.get('amplifier', 0)) for e in d.get('active_effects', [])}
    inv = {e.get('Slot'): e for e in d.get('Inventory', [])}
    return dict(g=r['game_time'], frozen=r['frozen'], rad=f32(float(att.get('hfr_radiation', 0.0))), asb=int(att.get('hfr_asbestos', 0)),
                bl=int(att.get('hfr_blacklung', 0)), health=f32(float(d.get('Health', 0.0))), fire=int(d.get('Fire', 0)),
                food=int(d.get('foodLevel', 0)), sat=f32(float(d.get('foodSaturationLevel', 0.0))),
                exh=f32(float(d.get('foodExhaustionLevel', 0.0))), mode=d.get('playerGameType'), effects=effects, inv=inv)


def energy(p):
    return 4.0 * p['sat'] + 4.0 * p['food'] - p['exh']


def worn(p, slot):
    e = p['inv'].get(ARMOR_SLOT[slot])
    return e.get('id') if e else None


def mask_filter(p):
    """(filter id, damage) of the filter in the worn helmet's custom data hfr_Filter (ArmorUtil.java:100-112), or None."""
    e = p['inv'].get(ARMOR_SLOT['helmet'])
    if not e:
        return None
    f = ((e.get('components') or {}).get('minecraft:custom_data') or {}).get('hfr_Filter')
    if not f:
        return None
    return f.get('id'), int((f.get('components') or {}).get('minecraft:damage', 0))


def item_damage(p, item):
    """Damage of the first stack of `item` in slots 0-35 (None when there is none)."""
    for s in sorted(k for k in p['inv'] if isinstance(k, int) and 0 <= k <= 35):
        e = p['inv'][s]
        if e.get('id') == item:
            return int((e.get('components') or {}).get('minecraft:damage', 0))
    return None


def counts(p):
    c = {}
    for s, e in p['inv'].items():
        c[e.get('id')] = c.get(e.get('id'), 0) + e.get('count', 1)
    return c


def brief(p):
    return 'g=%d rad=%r asb=%d bl=%d health=%r fire=%d' % (p['g'], p['rad'], p['asb'], p['bl'], p['health'], p['fire'])


# ---------------------------------------------------------------- actions

def freeze(ctx):
    ctx.server('tick freeze')


def unfreeze(ctx):
    ctx.server('tick unfreeze')


def run_ticks(ctx, ticks, label):
    """/tick sprint from the unfrozen world: the world keeps running afterwards, so every tick until the next read is counted
    in its game time."""
    return ctx.sprint(ticks, label=label, poll_s=0.2, timeout_s=300)


def stand(ctx, pos, pitch=-90.0):
    ctx.step('view', pos=list(pos), pitch=pitch, yaw=0.0, fly=False, hide_gui=False)


def use_in_air(ctx, pos, hold=0, after=6):
    """Right-click with the held item looking straight up (nothing to hit): ArmorItem.use equips, the filter screws in, the
    consumables run their use action; `hold` keeps the key down (eating)."""
    stand(ctx, pos)
    return ctx.step('use', hold=hold, after=after)


def wear(ctx, item, pos, slot):
    """Puts on an armour piece by a right-click with it in hand (a worn piece in that slot comes back into the hand)."""
    _lib.hold(ctx, H + item)
    use_in_air(ctx, pos)
    p = pdata(ctx)
    if worn(p, slot) != H + item:
        raise RuntimeError('%s not worn after the right-click (slot %s holds %s)' % (item, slot, worn(p, slot)))


def take_off(ctx, slots):
    """Takes armour off by shift-clicks on the inventory screen's armour slots."""
    ctx.step('key', key='key.keyboard.e', action='tap', after=4)
    ctx.step('screen', expect='Inventory')
    for slot in slots:
        _lib.shift_click(ctx, MENU_SLOT[slot])
    ctx.step('close')
    p = pdata(ctx)
    left = [s for s in slots if worn(p, s)]
    if left:
        raise RuntimeError('armour still worn after shift-clicks: %s' % left)


def suit(ctx, grade, pos):
    for slot in ('helmet', 'chest', 'legs', 'boots'):
        wear(ctx, PIECES[grade][slot], pos, slot)


def install(ctx, filt, pos):
    """Screws a filter into the worn mask by a right-click with it in hand."""
    _lib.hold(ctx, H + filt)
    use_in_air(ctx, pos)
    f = mask_filter(pdata(ctx))
    if not f or f[0] != H + filt:
        raise RuntimeError('filter %s not installed (mask holds %s)' % (filt, f))


def craft_one(ctx, name, out, made, pattern, key, gives, times=1):
    """Gives the exact inputs, crafts in the open crafting table (_lib.craft) and returns (ok, detail) on the output count."""
    _lib.give(ctx, *gives)
    before = _lib.count(ctx, out)
    _lib.craft(ctx, pattern, key, times)
    after = _lib.count(ctx, out)
    return after - before == made, '%s: %s %d -> %d (want +%d)' % (name, out.split(':')[1], before, after, made)


def crafting(ctx, recipes):
    """One opening of the crafting table for a list of craft_one argument tuples; returns (all ok, details)."""
    _lib.use_on(ctx, TABLE, 'south', AT_TABLE)
    ctx.step('screen', expect='Crafting')
    log, good = [], True
    try:
        for r in recipes:
            ok, line = craft_one(ctx, *r)
            good = good and ok
            log.append(line)
    finally:
        ctx.step('close', allow_fail=True)
    return good, '; '.join(log)


def place_by_hand(ctx, item, pos):
    """Real placement of a block item on the ground top face from two blocks south."""
    _lib.place(ctx, H + item if ':' not in item else item, (pos[0], pos[1] - 1, pos[2]), 'up', [pos[0] + 0.5, Y, pos[2] + 2.5])
    if not _lib.is_block(ctx, pos, H + item if ':' not in item else item):
        raise RuntimeError('%s not placed at %s' % (item, pos))


def mine_frozen(ctx, pos, ore, gas):
    """Mines the ore at pos (feet level) with the iron pickaxe in hand from the south, in the frozen world, and checks the gas
    it leaves in its cell (OutgasBlock.java:89-93; original BlockOutgas.java:94-101)."""
    _lib.hold(ctx, 'minecraft:iron_pickaxe')
    for _ in range(3):
        _lib.focused(ctx)   # a held attack mines only in the focused window (see _lib.focused)
        ctx.step('view', pos=[pos[0] + 0.5, Y, pos[2] + 1.5], look_at=[pos[0] + 0.5, pos[1] + 0.5, pos[2] + 1.0], fly=False, hide_gui=False)
        ctx.step('attack', target=dict(pos=list(pos), face='south'), hold=45, after=4)
        if not _lib.is_block(ctx, pos, ore):
            break
    if _lib.is_block(ctx, pos, ore):
        raise RuntimeError('%s at %s not mined after three holds' % (ore, pos))
    if not _lib.is_block(ctx, pos, gas):
        raise RuntimeError('no %s where %s was mined at %s' % (gas, ore, pos))


def gas_window(ctx, pos, ticks=100):
    """Stands in the gas cell (feet) and reads the player before and after `ticks` client ticks in the frozen world."""
    stand(ctx, [pos[0] + 0.5, Y, pos[2] + 0.5], pitch=0.0)
    a = pdata(ctx)
    ctx.step('wait', ticks=ticks)
    b = pdata(ctx)
    stand(ctx, [pos[0] + 0.5, Y, pos[2] + 3.5], pitch=0.0)
    return a, b


def dose_window(ctx, label, n=N_INGOTS, ticks=100):
    """N uranium ingots into the inventory, read A, sprint `ticks` from the unfrozen world, read B. The ingots stay."""
    _lib.give(ctx, (H + 'ingot_uranium', n))
    a = pdata(ctx)
    run_ticks(ctx, ticks, label)
    b = pdata(ctx)
    return a, b


def clear_item(ctx, item):
    cmd(ctx, 'clear @s %s' % item, allow_error=True)


def geiger(ctx, pos, key):
    """Right-click with a detector in hand; returns its readout lines (texts) from the chat."""
    _lib.hold(ctx, H + key)
    stand(ctx, pos)
    r = ctx.step('use', after=6)
    lines = [m.get('text', '') for m in ctx.step('chat', count=12, since_ms=r['started_ms'], expect='RAD/s').get('messages', [])]
    return [l for l in lines if l]


def parse_geiger(lines):
    """The Geiger readout in its order (original ContaminationUtil.java:190-194): chunk and environment lines end in RAD/s, the player
    line in RAD, the resistance line holds "x% (k)". Returns (env, player, (res %, coefficient)) as printed, None when absent."""
    per_s = [re.search(r'(>?[\d.]+) RAD/s', l) for l in lines]
    per_s = [m.group(1) for m in per_s if m]
    player = [re.search(r'([\d.]+) RAD(?!/)', l) for l in lines]
    player = [m.group(1) for m in player if m]
    res = [re.search(r'([\d.]+)% \(([\d.]+)\)', l) for l in lines]
    res = [m.groups() for m in res if m]
    return (per_s[1] if len(per_s) > 1 else None), (player[-1] if player else None), (res[-1] if res else None)


# ---------------------------------------------------------------- the line

HAZARDOUS = ('hbmsntm:ingot_uranium', 'hbmsntm:waste_natural_uranium', 'hbmsntm:powder_asbestos', 'hbmsntm:powder_coal')


def section(ctx, ids, body, prefix):
    """_lib.section, and afterwards (also after an error) no hazardous item is left in the inventory, so a broken section
    does not go on dosing or burning the player through the next ones."""
    reason = _lib.section(ctx, ids, body, prefix)
    for item in HAZARDOUS:
        try:
            clear_item(ctx, item)
        except Exception:  # noqa: BLE001
            pass
    return reason


class Rows:
    def __init__(self, ctx):
        self.ctx = ctx

    def check(self, eid_, ok, detail):
        if eid_ not in self.ctx.verdicts:
            self.ctx.check(eid_, bool(ok), detail[:1500])
        return ok

    def review(self, eid_, detail):
        if eid_ not in self.ctx.verdicts:
            self.ctx.review(eid_, detail[:1500], evidence=[])

    def not_run(self, ids, reason):
        for i in ids:
            if i not in self.ctx.verdicts:
                self.ctx.not_run(i, reason[:400])


def setup(ctx):
    for command in ('gamerule doDaylightCycle false', 'gamerule doWeatherCycle false', 'gamerule doMobSpawning false',
                    'gamerule naturalRegeneration false', 'time set 6000', 'weather clear', 'tick unfreeze'):
        cmd(ctx, command)
    cmd(ctx, 'gamemode survival')
    cmd(ctx, 'clear @s', allow_error=True)
    stand(ctx, AT_TABLE, pitch=30.0)
    ctx.step('wait', ticks=40)
    cmd(ctx, 'setblock %d %d %d minecraft:crafting_table' % TABLE)
    ctx.step('wait', ticks=10)


def run(ctx):
    rows = Rows(ctx)
    have = {}
    setup(ctx)
    handover = {i.split('@')[0] for i, _ in HANDOVER}
    used = ['hbmsntm:ingot_beryllium', 'hbmsntm:ingot_rubber', 'hbmsntm:wire_gold', 'hbmsntm:circuit_integrated_board', 'hbmsntm:plate_steel',
            'hbmsntm:circuit_vacuum_tube', 'hbmsntm:ingot_copper', 'hbmsntm:powder_coal', 'hbmsntm:powder_lead', 'hbmsntm:ingot_steel',
            'hbmsntm:plate_iron', 'hbmsntm:nugget_zirconium', 'hbmsntm:catalyst_clay', 'hbmsntm:plate_lead', 'hbmsntm:fluorite',
            'hbmsntm:ingot_uranium', 'hbmsntm:ore_uranium_deepslate']
    missing = [i for i in used if i not in handover]
    outside_on_list = sorted({i.split('[')[0] for i, _, _ in ISSUED if i.split('[')[0] in handover})
    rows.check(eid(HS, 'start-items'), not missing and not outside_on_list,
                '阶段 11 交接清单 %d 项（世界生成 %d 行）；本线从清单取用：%s%s；清单之外按更早阶段发放：%s；原版材料：%s；清单之外发放而在清单上的：%s；%s'
                % (len(HANDOVER), sum(1 for i, _ in HANDOVER if i.startswith('block:')), ', '.join(i.split(':')[1] for i in used),
                   '（不在清单上：%s）' % missing if missing else '', ', '.join('%s 发放 %d 件（阶段 %d 可得）' % (i.split(':', 1)[1], n, st) for i, st, n in ISSUED),
                   ', '.join(VANILLA), outside_on_list or '无', '; '.join(PREWRITES)))
    p = pdata(ctx)
    rows.check(eid(HS, 'survival'), p['mode'] == 0, 'playerGameType %s (0 = survival)' % p['mode'])

    # ---------------------------------------------------------------- crafting, one table opening per group
    def craft_rd():
        ok, detail = crafting(ctx, [
            ('geiger counter', H + 'geiger_counter', 1, ['GPP', 'WCS', 'WBB'],
             dict(G='minecraft:gold_ingot', P=H + 'ingot_rubber', W=H + 'wire_gold', C=H + 'circuit_integrated_board', S=H + 'plate_steel', B=H + 'ingot_beryllium'),
             [('minecraft:gold_ingot', 1), (H + 'ingot_rubber', 2), (H + 'wire_gold', 2), (H + 'circuit_integrated_board', 1), (H + 'plate_steel', 1), (H + 'ingot_beryllium', 2)]),
            ('dosimeter', H + 'dosimeter', 1, ['WGW', 'WCW', 'WBW'],
             dict(W='minecraft:oak_planks', G='minecraft:glass_pane', C=H + 'circuit_vacuum_tube', B=H + 'ingot_beryllium'),
             [('minecraft:oak_planks', 6), ('minecraft:glass_pane', 1), (H + 'circuit_vacuum_tube', 1), (H + 'ingot_beryllium', 1)]),
            ('radiation absorber', H + 'rad_absorber', 1, ['ICI', 'CPC', 'ICI'], dict(I=H + 'ingot_copper', C=H + 'powder_coal', P=H + 'powder_lead'),
             [(H + 'ingot_copper', 4), (H + 'powder_coal', 4), (H + 'powder_lead', 1)]),
            ('decontaminator', H + 'decontaminator', 1, ['BGB', 'SAS', 'BSB'],
             dict(B=H + 'ingot_beryllium', G='minecraft:iron_bars', S=H + 'ingot_steel', A=H + 'rad_absorber'),
             [(H + 'ingot_beryllium', 4), ('minecraft:iron_bars', 1), (H + 'ingot_steel', 3)]),
        ])
        have['rd'] = ok
        rows.check(eid(RD, 'craft'), ok, detail)

    def craft_gm():
        _lib.give(ctx, (H + 'filter_coal', 1))
        ok, detail = crafting(ctx, [
            ('gas mask', H + 'gas_mask', 1, ['PPP', 'GPG', ' F '], dict(P=H + 'plate_steel', G='minecraft:glass_pane', F=H + 'plate_iron'),
             [(H + 'plate_steel', 4), ('minecraft:glass_pane', 2), (H + 'plate_iron', 1)]),
            ('filter', H + 'gas_mask_filter', 1, ['I', 'F'], dict(I=H + 'plate_iron', F=H + 'filter_coal'), [(H + 'plate_iron', 1)]),
            ('mono filter', H + 'gas_mask_filter_mono', 1, ['ZZZ', 'ZCZ', 'ZZZ'], dict(Z=H + 'nugget_zirconium', C=H + 'catalyst_clay'),
             [(H + 'nugget_zirconium', 8), (H + 'catalyst_clay', 1)]),
        ])
        have['gm'] = ok
        if not ok:
            rows.check(eid(GM, 'craft'), False, detail)
        else:
            have['gm_detail'] = detail

    def craft_hz():
        red = (H + 'hazmat_cloth_red')
        grey = (H + 'hazmat_cloth_grey')
        recipes = [
            ('red cloth 1', red, 25, ['C', 'R', 'C'], dict(C=H + 'hazmat_cloth', R='minecraft:redstone'), [(H + 'hazmat_cloth', 50), ('minecraft:redstone', 25)], 25),
            ('red cloth 2', red, 25, ['C', 'R', 'C'], dict(C=H + 'hazmat_cloth', R='minecraft:redstone'), [(H + 'hazmat_cloth', 50), ('minecraft:redstone', 25)], 25),
            ('grey cloth', grey, 25, [' P ', 'ICI', ' L '], dict(P=H + 'plate_iron', I=H + 'ingot_rubber', C=red, L=H + 'plate_lead'),
             [(H + 'plate_iron', 25), (H + 'ingot_rubber', 50), (H + 'plate_lead', 25)], 25),
            ('yellow helmet', H + 'hazmat_helmet', 1, ['EEE', 'EIE', ' P '], dict(E=H + 'hazmat_cloth', I='minecraft:glass_pane', P=H + 'plate_iron'),
             [(H + 'hazmat_cloth', 24), ('minecraft:glass_pane', 1), (H + 'plate_iron', 1)]),
            ('yellow chest', H + 'hazmat_plate', 1, ['E E', 'EEE', 'EEE'], dict(E=H + 'hazmat_cloth'), []),
            ('yellow legs', H + 'hazmat_legs', 1, ['EEE', 'E E', 'E E'], dict(E=H + 'hazmat_cloth'), []),
            ('yellow boots', H + 'hazmat_boots', 1, ['E E', 'E E'], dict(E=H + 'hazmat_cloth'), []),
        ]
        for grade, cloth in (('red', red), ('grey', grey)):
            recipes += [
                ('%s helmet' % grade, H + PIECES[grade]['helmet'], 1, ['EEE', 'IEI', 'EFE'], dict(E=cloth, I='minecraft:glass_pane', F=H + 'plate_iron'),
                 [('minecraft:glass_pane', 2), (H + 'plate_iron', 1)]),
                ('%s chest' % grade, H + PIECES[grade]['chest'], 1, ['E E', 'EEE', 'EEE'], dict(E=cloth), []),
                ('%s legs' % grade, H + PIECES[grade]['legs'], 1, ['EEE', 'E E', 'E E'], dict(E=cloth), []),
                ('%s boots' % grade, H + PIECES[grade]['boots'], 1, ['E E', 'E E'], dict(E=cloth), []),
            ]
        ok, detail = crafting(ctx, recipes)
        have['hz'] = ok
        rows.check(eid(HZ, 'craft'), ok, detail)

    def craft_rm():
        ok, detail = crafting(ctx, [
            ('rad-x', H + 'radx', 1, ['CCF'], dict(C=H + 'powder_coal', F=H + 'fluorite'), [(H + 'powder_coal', 2), (H + 'fluorite', 1)]),
            ('iv bags', H + 'iv_empty', 4, ['S', 'I', 'S'], dict(S=H + 'ingot_rubber', I=H + 'plate_iron'), [(H + 'ingot_rubber', 2), (H + 'plate_iron', 1)]),
        ])
        have['rm'] = ok
        have['rm_detail'] = detail
        if not ok:
            rows.check(eid(RM, 'craft'), False, detail)

    for name, body, ids in (('rd', craft_rd, [eid(RD, 'craft')]), ('gm', craft_gm, [eid(GM, 'craft')]), ('hz', craft_hz, [eid(HZ, 'craft')]),
                            ('rm', craft_rm, [eid(RM, 'craft')])):
        if section(ctx, ids, body, 'crafting (%s)' % name):
            have[name] = False

    # tools of the line
    _lib.give(ctx, ('minecraft:iron_pickaxe', 1), ('minecraft:water_bucket', 1))

    # ---------------------------------------------------------------- the decontaminator, placed by hand
    def place_decon():
        place_by_hand(ctx, 'decontaminator', DECON)
        have['decon'] = True
    if have.get('rd'):
        section(ctx, [], place_decon, 'placing the decontaminator')

    # ---------------------------------------------------------------- radiation doses: unprotected, three suits, Rad-X later
    dose = {}
    rate_ids = [eid(HS, 'dose-unprotected'), eid(RD, 'geiger-unprotected'), eid(RD, 'dosimeter'), eid(RD, 'geiger-suits'),
                eid(HZ, 'yellow'), eid(HZ, 'red'), eid(HZ, 'grey'), eid(HZ, 'partial'), eid(HS, 'hot-pair'), eid(HS, 'sickness-pair')]

    def check_dose(row, label, a, b, pieces, radx=False):
        res = resistance(pieces, radx)
        m = mod_of(res)
        n = b['g'] - a['g']
        want = rad_after(a['rad'], n, N_INGOTS, m)
        neo_res = 0.0
        for slot in ('boots', 'legs', 'chest', 'helmet'):
            grade = pieces.get(slot)
            neo_res = f32(neo_res + f32(GRADE[grade] * SUIT[slot] if grade else 0.0))
        if radx:
            neo_res = f32(neo_res + RADX_RES)
        neo_want = rad_after(a['rad'], n, N_INGOTS, mod_of(neo_res))
        dose[label] = (a, b)
        ok = b['rad'] == want and n > 0
        rows.check(row, ok, '%s: resistance %r, modifier %r, per tick %r; %d ticks (game time %d -> %d): rad %r -> %r, want %r%s'
                   % (label, res, m, f32(per_tick(N_INGOTS) * m), n, a['g'], b['g'], a['rad'], b['rad'], want,
                      '' if neo_res == res else ' (with the resistance summed as (float) per piece, %r -> modifier %r, the value would be %r)'
                      % (neo_res, mod_of(neo_res), neo_want)))
        return ok

    def check_geiger(label, pieces, a_rad):
        lines = geiger(ctx, M, 'geiger_counter')
        after = pdata(ctx)
        env, pr, rs = parse_geiger(lines)
        want_env = jstr(env_readout(N_INGOTS))
        want_res = res_readout(resistance(pieces))
        lo, hi = int(a_rad * 10) / 10.0, int(after['rad'] * 10) / 10.0
        ok = (env == want_env and rs is not None and rs[0] == jstr(want_res[0]) and rs[1] == jstr(want_res[1])
              and pr is not None and lo <= float(pr) <= hi)
        return ok, '%s: env %s (want %s), player %s (want %s..%s, the dose at the click), resistance %s (want %s%% (%s)); lines %s' % (
            label, env, want_env, pr, jstr(lo), jstr(hi), rs, jstr(want_res[0]), jstr(want_res[1]), lines[-5:])

    def doses():
        unfreeze(ctx)
        stand(ctx, M)
        # unprotected
        a, b = dose_window(ctx, 'dose unprotected')
        check_dose(eid(HS, 'dose-unprotected'), 'unprotected', a, b, {})
        if have.get('rd'):
            ok, detail = check_geiger('unprotected', {}, b['rad'])
            rows.check(eid(RD, 'geiger-unprotected'), ok, detail)
            lines = geiger(ctx, M, 'dosimeter')
            v = [m.group(1) for m in (re.search(r'(>?[\d.]+) RAD/s', l) for l in lines) if m]
            rows.check(eid(RD, 'dosimeter'), v == ['>3.6'], 'dosimeter env %s (want >3.6: %s > 3.6); lines %s'
                       % (v, jstr(env_readout(N_INGOTS)), lines[-3:]))
        clear_item(ctx, H + 'ingot_uranium')
        if not have.get('hz'):
            return
        suits_detail = []
        for grade in ('yellow', 'red', 'grey'):
            suit(ctx, grade, M)
            a, b = dose_window(ctx, 'dose %s' % grade)
            check_dose(eid(HZ, grade), grade, a, b, {s: grade for s in SUIT})
            if have.get('rd') and grade in ('yellow', 'grey'):
                ok, detail = check_geiger(grade, {s: grade for s in SUIT}, b['rad'])
                suits_detail.append((ok, detail))
            clear_item(ctx, H + 'ingot_uranium')
        if suits_detail:
            rows.check(eid(RD, 'geiger-suits'), all(o for o, _ in suits_detail), ' | '.join(d for _, d in suits_detail))
        have['grey_on'] = True

    section(ctx, rate_ids[:8], doses, 'dose windows')
    clear_item(ctx, H + 'ingot_uranium')

    # ---------------------------------------------------------------- hot item pair (frozen; grey suit keeps the dose small)
    def hot():
        freeze(ctx)
        stand(ctx, DRY, pitch=0.0)
        _lib.hold(ctx, 'minecraft:water_bucket')
        _lib.give(ctx, ('hbmsntm:waste_natural_uranium[hbmsntm:meta=1]', 1))
        ctx.step('wait', ticks=5)
        dry = pdata(ctx)
        _lib.use_on(ctx, (WATER[0], Y - 1, WATER[2]), 'up', [WATER[0] + 0.5, Y, WATER[2] + 2.5])
        if not _lib.is_block(ctx, WATER, 'minecraft:water'):
            raise RuntimeError('no water at %s after emptying the bucket' % (WATER,))
        stand(ctx, [WATER[0] + 0.5, Y, WATER[2] + 0.5], pitch=0.0)
        ctx.step('wait', ticks=10)
        wet = pdata(ctx)
        clear_item(ctx, 'hbmsntm:waste_natural_uranium')
        stand(ctx, DRY, pitch=0.0)
        cmd(ctx, 'setblock %d %d %d minecraft:air' % WATER)
        want_dry = HOT_TIME * 20 - 1
        rows.check(eid(HS, 'hot-pair'), dry['fire'] == want_dry and wet['fire'] <= 0,
                   'dry: Fire %d (want %d = ceil(5) x 20 set by the hazard, minus 1 in the player tick that follows); in water: Fire %d (want <= 0); '
                   'grey suit worn: %s' % (dry['fire'], want_dry, wet['fire'], worn(dry, 'helmet')))
    if have.get('grey_on'):
        section(ctx, [eid(HS, 'hot-pair')], hot, 'hot pair')
    else:
        rows.not_run([eid(HS, 'hot-pair')], 'the grey suit was not worn (crafting or the dose windows failed)')

    # ---------------------------------------------------------------- radiation sickness pair, then the partial suit
    def sickness():
        unfreeze(ctx)
        stand(ctx, M)
        # protected half: the grey suit is worn
        a, b = dose_window(ctx, 'sickness grey', n=64, ticks=1300)
        m = mod_of(resistance({s: 'grey' for s in SUIT}))
        want = sim_add(a['rad'], b['g'] - a['g'], f32(per_tick(64) * m))
        prot_ok = b['rad'] == want and b['rad'] < 200 and energy(b) == energy(a) and b['g'] - a['g'] >= 1260
        prot = 'grey: %d ticks, rad %r -> %r (want %r, < 200), food energy %r -> %r (want unchanged)' % (
            b['g'] - a['g'], a['rad'], b['rad'], want, energy(a), energy(b))
        clear_item(ctx, H + 'ingot_uranium')
        # the partial suit: only the grey helmet
        take_off(ctx, ['chest', 'legs', 'boots'])
        a2, b2 = dose_window(ctx, 'dose grey helmet')
        check_dose(eid(HZ, 'partial'), 'grey helmet only', a2, b2, {'helmet': 'grey'})
        clear_item(ctx, H + 'ingot_uranium')
        take_off(ctx, ['helmet'])
        # unprotected half: 64 ingots until the dose is over 200, then away
        p0 = pdata(ctx)
        need = max(1, int(math.ceil((230.0 - p0['rad']) / per_tick(64))))
        a3, b3 = dose_window(ctx, 'sickness dose', n=64, ticks=need)
        clear_item(ctx, H + 'ingot_uranium')
        c = pdata(ctx)
        run_ticks(ctx, 1300, 'sickness window')
        d = pdata(ctx)
        drop = energy(c) - energy(d)
        unp_ok = 200 < c['rad'] < 400 and d['rad'] == c['rad'] and d['g'] - c['g'] >= 1260 and drop >= 6.0 - 1e-3
        unp = 'unprotected: rad %r over %d ticks without a source (want > 200, unchanged), food energy %r -> %r, drop %r (want >= 6); effects %s' % (
            c['rad'], d['g'] - c['g'], energy(c), energy(d), drop, d['effects'])
        rows.check(eid(HS, 'sickness-pair'), prot_ok and unp_ok, prot + ' | ' + unp)
        have['sick'] = d
    if have.get('grey_on'):
        section(ctx, [eid(HS, 'sickness-pair'), eid(HZ, 'partial')], sickness, 'sickness pair')
    else:
        rows.not_run([eid(HS, 'sickness-pair'), eid(HZ, 'partial')], 'the grey suit was not worn (crafting or the dose windows failed)')
    clear_item(ctx, H + 'ingot_uranium')

    # ---------------------------------------------------------------- IV bag, RadAway, Rad-X
    def medicine():
        unfreeze(ctx)
        stand(ctx, M)
        h0 = pdata(ctx)
        _lib.hold(ctx, H + 'iv_empty')
        use_in_air(ctx, M)
        h1 = pdata(ctx)
        iv_ok = h1['health'] == f32(max(h0['health'] - 5.0, 0.0)) and counts(h1).get(H + 'iv_blood', 0) == 1
        ok, detail = crafting(ctx, [('radaway', H + 'radaway', 1, ['BCS'], dict(B=H + 'iv_blood', C=H + 'powder_coal', S='minecraft:pumpkin_seeds'),
                                     [(H + 'powder_coal', 1), ('minecraft:pumpkin_seeds', 1)])])
        rows.check(eid(RM, 'craft'), have.get('rm') and iv_ok and ok,
                   '%s; IV bag: health %r -> %r (want -5), blood bags %d; %s' % (have.get('rm_detail'), h0['health'], h1['health'],
                                                                              counts(h1).get(H + 'iv_blood', 0), detail))
        # RadAway: no radiation source is carried
        a = pdata(ctx)
        _lib.hold(ctx, H + 'radaway')
        use_in_air(ctx, M)
        run_ticks(ctx, RADAWAY_TICKS + 40, 'radaway')
        b = pdata(ctx)
        want = sim_add(a['rad'], RADAWAY_TICKS, -1.0)
        ca, cb = counts(a), counts(b)
        rows.check(eid(RM, 'radaway'), b['rad'] == want and cb.get(H + 'iv_empty', 0) == ca.get(H + 'iv_empty', 0) + 1
                   and cb.get(H + 'radaway', 0) == ca.get(H + 'radaway', 0) - 1 and 'hbmsntm:radaway' not in b['effects'],
                   'rad %r -> %r (want %r: 140 float subtractions of 1); iv_empty %d -> %d, radaway %d -> %d; effects after %s'
                   % (a['rad'], b['rad'], want, ca.get(H + 'iv_empty', 0), cb.get(H + 'iv_empty', 0), ca.get(H + 'radaway', 0),
                      cb.get(H + 'radaway', 0), b['effects']))
        # Rad-X: eaten (10 ticks), then the dose window with no armour
        _lib.hold(ctx, H + 'radx')
        p0 = pdata(ctx)
        use_in_air(ctx, M, hold=16, after=4)
        e = pdata(ctx)
        fx = e['effects'].get('hbmsntm:radx')
        a2, b2 = dose_window(ctx, 'dose rad-x')
        clear_item(ctx, H + 'ingot_uranium')
        res = resistance({}, radx=True)
        m = mod_of(res)
        n = b2['g'] - a2['g']
        want2 = rad_after(a2['rad'], n, N_INGOTS, m)
        unp = dose.get('unprotected')
        base = ' (unprotected window: %r a tick)' % per_tick(N_INGOTS) if unp else ''
        # The effect starts at RADX_TICKS (ItemPill.java:57-59; NEO PillItem.java:36-38) when the pill is finished, RADX_USE_TICKS
        # after the use began (ItemPill.java:123-125; NEO PillItem.java:75), and loses one tick per game tick. The use began no
        # earlier than the game time p0 read before the key went down, so the ticks the effect has run at the reading e
        # (RADX_TICKS - duration) are at most the ticks between p0 and e minus the use ticks, plus one for the tick on which it
        # was added; they are not negative. The world runs (not frozen) from p0 to b2, so after the dose window the duration
        # has dropped by exactly the game ticks between e and b2.
        run_for = e['g'] - p0['g']
        fx2 = b2['effects'].get('hbmsntm:radx')
        ran = RADX_TICKS - fx[0] if fx is not None else None
        ran_max = run_for - RADX_USE_TICKS + 1
        counted = fx is not None and fx2 is not None and fx[0] - fx2[0] == b2['g'] - e['g']
        timing_ok = ran is not None and 0 <= ran <= ran_max and counted and not p0['frozen'] and not e['frozen'] and not b2['frozen']
        rows.check(eid(RM, 'radx'), timing_ok and fx[1] == 0 and b2['rad'] == want2,
                   'effect %s at game time %d (before eating %d; want ran 0..%d of %d ticks: RADX_TICKS - duration = %s), after the window %s at %d '
                   '(want the drop %s = the ticks between the readings %d), amplifier 0, frozen %s/%s/%s; resistance %r, modifier %r, %d ticks: '
                   'rad %r -> %r, want %r%s'
                   % (fx, e['g'], p0['g'], ran_max, run_for, ran, fx2, b2['g'], (fx[0] - fx2[0]) if fx and fx2 else None, b2['g'] - e['g'],
                      p0['frozen'], e['frozen'], b2['frozen'], res, m, n, a2['rad'], b2['rad'], want2, base))
    if have.get('rm') is not False:
        section(ctx, [eid(RM, 'craft'), eid(RM, 'radaway'), eid(RM, 'radx')], medicine, 'medicine')
    clear_item(ctx, H + 'ingot_uranium')

    # ---------------------------------------------------------------- decontaminator (frozen, exact block-entity ticks)
    def decon():
        freeze(ctx)
        stand(ctx, NEAR_DECON, pitch=0.0)
        ctx.step('wait', ticks=10)
        a = pdata(ctx)
        _lib.advance(ctx, 100, 'beside the decontaminator')
        b = pdata(ctx)
        stand(ctx, ON_DECON, pitch=0.0)
        ctx.step('wait', ticks=10)
        c = pdata(ctx)
        _lib.advance(ctx, 100, 'on the decontaminator')
        d = pdata(ctx)
        stand(ctx, NEAR_DECON, pitch=0.0)
        want = sim_add(c['rad'], 100, DECON_STEP)
        rows.check(eid(RD, 'decontaminator'), b['rad'] == a['rad'] and d['rad'] == want and b['g'] - a['g'] == 100 and d['g'] - c['g'] == 100,
                   'beside: rad %r -> %r over %d ticks (want unchanged); on top: rad %r -> %r over %d ticks (want %r = 100 x -0.5)'
                   % (a['rad'], b['rad'], b['g'] - a['g'], c['rad'], d['rad'], d['g'] - c['g'], want))
    if have.get('decon'):
        section(ctx, [eid(RD, 'decontaminator')], decon, 'decontaminator')
    else:
        rows.not_run([eid(RD, 'decontaminator')], 'the decontaminator was not crafted or placed')

    # ---------------------------------------------------------------- gases from mined ores (frozen world)
    gas_ids = [eid(GM, 'craft'), eid(GM, 'radon-pair'), eid(GM, 'asbestos-gas-pair'), eid(GM, 'monoxide-pair')]

    def gases():
        freeze(ctx)
        _lib.give(ctx, (H + 'ore_uranium_deepslate', 1), (H + 'ore_asbestos', 1))
        place_by_hand(ctx, 'ore_uranium_deepslate', U_ORE)
        place_by_hand(ctx, 'ore_asbestos', A_ORE)
        cmd(ctx, 'setblock %d %d %d hbmsntm:ore_nether_coal' % C_ORE)   # 预写
        out = [U_ORE[0] + 0.5, Y, U_ORE[2] + 6.5]
        # radon
        mine_frozen(ctx, U_ORE, H + 'ore_uranium_deepslate', H + 'gas_radon')
        a, b = gas_window(ctx, U_ORE)
        n = b['asb'] - a['asb']
        want = sim_add(a['rad'], n, f32(0.05))
        unp_ok = n >= 1 and b['rad'] == want
        unp = 'unprotected: asbestos %d -> %d (%d contacts), rad %r -> %r (want %r = %d x 0.05)' % (a['asb'], b['asb'], n, a['rad'], b['rad'], want, n)
        wear(ctx, 'gas_mask', out, 'helmet')
        install(ctx, 'gas_mask_filter', out)
        rows.check(eid(GM, 'craft'), have.get('gm'), '%s; filter installed: %s' % (have.get('gm_detail'), mask_filter(pdata(ctx))))
        a2, b2 = gas_window(ctx, U_ORE)
        fa, fb = mask_filter(a2), mask_filter(b2)
        prot_ok = b2['asb'] == a2['asb'] and b2['rad'] == a2['rad'] and fa and fb and fb[1] - fa[1] >= 1
        rows.check(eid(GM, 'radon-pair'), unp_ok and prot_ok, unp + ' | mask + filter: asbestos %d -> %d, rad %r -> %r (want both unchanged), filter %s -> %s (want +>=1)'
                   % (a2['asb'], b2['asb'], a2['rad'], b2['rad'], fa, fb))
        # asbestos dust
        mine_frozen(ctx, A_ORE, H + 'ore_asbestos', H + 'gas_asbestos')
        a3, b3 = gas_window(ctx, A_ORE)
        fa, fb = mask_filter(a3), mask_filter(b3)
        prot_ok = b3['asb'] == a3['asb'] and fa == fb and fa is not None
        prot = 'mask + filter: asbestos %d -> %d (want unchanged), filter %s -> %s (want unchanged)' % (a3['asb'], b3['asb'], fa, fb)
        take_off(ctx, ['helmet'])
        a4, b4 = gas_window(ctx, A_ORE)
        unp_ok = b4['asb'] - a4['asb'] >= 1
        rows.check(eid(GM, 'asbestos-gas-pair'), unp_ok and prot_ok, 'unprotected: asbestos %d -> %d (want +>=1) | %s' % (a4['asb'], b4['asb'], prot))
        # carbon monoxide: wrong filter type, then the mono filter
        wear(ctx, 'gas_mask', out, 'helmet')
        mine_frozen(ctx, C_ORE, H + 'ore_nether_coal', H + 'gas_monoxide')
        a5, b5 = gas_window(ctx, C_ORE, ticks=50)
        hurt = a5['health'] - b5['health']
        wrong_ok = hurt >= 1 and hurt == int(hurt)
        install(ctx, 'gas_mask_filter_mono', out)
        a6, b6 = gas_window(ctx, C_ORE, ticks=50)
        fa, fb = mask_filter(a6), mask_filter(b6)
        mono_ok = b6['health'] == a6['health'] and fa and fb and fa[0] == H + 'gas_mask_filter_mono' and fb[1] - fa[1] >= 1
        rows.check(eid(GM, 'monoxide-pair'), wrong_ok and mono_ok,
                   '预写 ore; standard filter %s: health %r -> %r (want -n, n >= 1) | mono filter: health %r -> %r (want unchanged), filter %s -> %s (want +>=1)'
                   % (mask_filter(a5), a5['health'], b5['health'], a6['health'], b6['health'], fa, fb))
        # the standard filter back in for the dust pairs; the gas and the drops cleared
        install(ctx, 'gas_mask_filter', out)
        for pos in (U_ORE, A_ORE, C_ORE):
            cmd(ctx, 'setblock %d %d %d minecraft:air' % pos)
        cmd(ctx, 'kill @e[type=minecraft:item,distance=..20]', allow_error=True)
        have['mask'] = True
    if have.get('gm'):
        section(ctx, gas_ids, gases, 'gases')
    else:
        rows.not_run(gas_ids[1:], 'the gas mask or the filters were not crafted')

    # ---------------------------------------------------------------- dust items: asbestos and coal, and the filter used up
    dust_ids = [eid(HS, 'asbestos-dust-pair'), eid(HS, 'coal-dust-pair'), eid(GM, 'filter-used-up')]

    def dusts():
        unfreeze(ctx)
        stand(ctx, M)
        take_off(ctx, ['helmet'])
        # asbestos, unprotected
        _lib.give(ctx, (H + 'powder_asbestos', 1))
        a = pdata(ctx)
        run_ticks(ctx, 60, 'asbestos unprotected')
        b = pdata(ctx)
        clear_item(ctx, H + 'powder_asbestos')
        n1 = b['g'] - a['g']
        unp = 'unprotected: asbestos %d -> %d over %d ticks (want +%d)' % (a['asb'], b['asb'], n1, POWDER * n1)
        unp_ok = b['asb'] - a['asb'] == POWDER * n1
        # coal dust, unprotected then protected
        _lib.give(ctx, (H + 'powder_coal', COAL_N))
        c = pdata(ctx)
        run_ticks(ctx, 60, 'coal unprotected')
        d = pdata(ctx)
        n2 = d['g'] - c['g']
        want_bl = sim_blacklung(c['bl'], n2, min(POWDER * COAL_N, 10))
        coal_unp = 'unprotected: black lung %d -> %d over %d ticks (want %d: +10 -1 a tick)' % (c['bl'], d['bl'], n2, want_bl)
        coal_unp_ok = d['bl'] == want_bl
        wear(ctx, 'gas_mask', M, 'helmet')
        e = pdata(ctx)
        run_ticks(ctx, 60, 'coal protected')
        f = pdata(ctx)
        clear_item(ctx, H + 'powder_coal')
        n3 = f['g'] - e['g']
        want_bl2 = sim_blacklung(e['bl'], n3, 0)
        fe, ff = mask_filter(e), mask_filter(f)
        coal_prot_ok = f['bl'] == want_bl2 and fe and ff and (ff[1] - fe[1]) % 3 == 0
        coal_prot = 'mask + filter: black lung %d -> %d over %d ticks (want %d: decay only), filter %s -> %s (random +3 steps)' % (
            e['bl'], f['bl'], n3, want_bl2, fe, ff)
        rows.check(eid(HS, 'coal-dust-pair'), coal_unp_ok and coal_prot_ok, coal_unp + ' | ' + coal_prot)
        # asbestos, protected, then on until the filter is used up
        _lib.give(ctx, (H + 'powder_asbestos', 1))
        g = pdata(ctx)
        run_ticks(ctx, 60, 'asbestos protected')
        h = pdata(ctx)
        n4 = h['g'] - g['g']
        fg, fh = mask_filter(g), mask_filter(h)
        prot_ok = h['asb'] == g['asb'] and fg and fh and fh[1] - fg[1] == POWDER * n4
        rows.check(eid(HS, 'asbestos-dust-pair'), unp_ok and prot_ok, unp + ' | mask + filter: asbestos %d -> %d (want unchanged), filter %s -> %s over %d ticks (want +%d)'
                   % (g['asb'], h['asb'], fg, fh, n4, POWDER * n4))
        left = int(math.ceil((MAX_FILTER - fh[1]) / float(POWDER))) + 200
        run_ticks(ctx, left, 'filter used up')
        k = pdata(ctx)
        clear_item(ctx, H + 'powder_asbestos')
        n5 = k['g'] - h['g']
        dmg, asb, removed_at = sim_filter_asbestos(fh[1], h['asb'], n5)
        rows.check(eid(GM, 'filter-used-up'), mask_filter(k) is None and dmg is None and k['asb'] == asb,
                   'from filter damage %d and asbestos %d, %d ticks: the filter goes on tick %s, asbestos want %d; read: filter %s, asbestos %d'
                   % (fh[1], h['asb'], n5, removed_at, asb, mask_filter(k), k['asb']))
    if have.get('mask'):
        section(ctx, dust_ids, dusts, 'dust pairs')
    else:
        rows.not_run(dust_ids, 'the gas mask with its filter was not worn (crafting or the gas section failed)')
    for item in ('ingot_uranium', 'powder_asbestos', 'powder_coal'):
        clear_item(ctx, H + item)

    # ---------------------------------------------------------------- leave, open again, compare static readings
    reload_ids = [eid(f, 'reload') for f in (HS, RD, GM, HZ, RM)]

    def readings():
        p = pdata(ctx)
        c = counts(p)
        out = {HS: dict(rad=p['rad'], asb=p['asb']),
               RD: dict(geiger=c.get(H + 'geiger_counter', 0), dosimeter=c.get(H + 'dosimeter', 0),
                        decon_block=_lib.is_block(ctx, DECON, H + 'decontaminator') if have.get('decon') else None),
               GM: dict(mask=c.get(H + 'gas_mask', 0), mono_damage=item_damage(p, H + 'gas_mask_filter_mono')),
               HZ: {piece: c.get(H + piece, 0) for g in PIECES for piece in PIECES[g].values()},
               RM: dict(iv_empty=c.get(H + 'iv_empty', 0), radx=c.get(H + 'radx', 0), radaway=c.get(H + 'radaway', 0))}
        return out

    def reload():
        freeze(ctx)
        stand(ctx, NEUTRAL, pitch=0.0)
        ctx.step('wait', ticks=80)
        first = readings()
        ctx.step('wait', ticks=20)
        second = readings()
        _lib.reopen(ctx)
        after = readings()
        for f in (HS, RD, GM, HZ, RM):
            same, moved = _lib.static_readings(first[f], second[f])
            r = _lib.compare_static(same, {k: after[f].get(k) for k in same}, not_quantity=('decon_block',))
            rows.check(eid(f, 'reload'), r['ok'], '%s; moved before leaving: %s; after: %s' % (r['detail'], moved or 'none', after[f]))
    section(ctx, reload_ids, reload, 'leaving and opening the world')
    rows.not_run([e['id'] for e in expectations()], 'not reached: an earlier section it needs did not run or failed (see the rows before it)')
