"""Dedicated server, stability matrix, situation "walk away until the chunks unload, then come back": six networks in one disposable
world, each read before the players leave and after they come back (power-transmission/mp_stability_restart.py is the other
situation and imports the rigs of this file).

Rigs (player A builds; single blocks by command, multiblocks by hand with the item put in the hand by command; the world is frozen
while it is built and runs 300 ticks before the readings):
- power: RTG (two RTG pellets) -> red cable -> power gauge -> red cable -> battery socket with a battery pack (input mode, the
  default). Reading: server data of the RTG and the socket (the pack's charge).
- fluid: electric pump on the flat ground, powered through a cable on its east port by an RTG; ducts typed water from its west
  port to a steel barrel in receive mode. Reading: server data of the barrel and the ducts.
- belts and arms: an eight-belt ring (conveyors/cram.py) fed by an extractor with the ejector upgrade III from a chest of six
  cobblestone; the items circulate. Reading: chest and extractor data, number and server positions of the moving items.
- RBMK: a hand-built 3 x 3 reactor (row 1: a radium-beryllium source rod, a manual control rod, a natural uranium rod; blanks
  around), a console placed by hand and linked to the control column. Reading: server data of the nine columns and the console.
- long line across chunks: power RTG -> cable -> heavy connector C1 ~96 m wire~ C2 ~96 m wire~ C3 -> cable -> electric furnace,
  C1 and C3 twelve chunks apart, C2 six chunks from both; fluid: steel barrel with an infinite water barrel (send mode) -> duct ->
  pipe anchor A1 ~10 m~ A2 -> 169 ducts -> A3 ~10 m~ A4 -> duct -> steel barrel (receive mode). Reading: server data of the
  connectors, anchors, sample ducts and both ends.
- chunk radiation: chunk T, about seven chunks east of the rigs, set to 20,000 by `ntmchunkrad set` with A standing in it.
  Chunk radiation is redistributed and decays every 20 server ticks also in a frozen world, so it has no static reading: the cell
  reads the value saved with the chunk when it unloads (region file, key hfr_simple_radiation) and A's Geiger reading on coming back.
  The saved value is read in a sequence of its own (radiation_unload): vanilla 1.21.1 saves a chunk on unload only when it is
  unsaved (ChunkMap.save :771) and saves unsaved chunks every tick with a 10 s cooldown per chunk (ChunkMap.saveChunkIfNeeded
  :743-767), and the radiation update does not mark chunks unsaved (ChunkRadiationHandlerSimple.updateSystem :73-118). So the set
  value is saved at once by the periodic save; a block placed in T right after that save marks T unsaved again, and T is unloaded
  within the cooldown, so the save that follows the unload event is the one that writes T.

Method: freeze, wait 80 client ticks, read; both players fly to the parking spot and wait 40 ticks frozen (their tickets go, so the
chunks leave block-ticking range: DistanceManager.inBlockTickingRange :260-262 in the 21.1.228 sources); then the world runs until no
probe position is in a chunk at full status and 100 more ticks, and is frozen again: every reading or probe fetches its chunk with an
UNKNOWN ticket (ServerChunkCache.getChunkFutureMainThread :233) that only a running world purges (ServerChunkCache.tick :317-319), so a
frozen world never unloads a chunk that was read. Nothing in the scenes ticks while they are out of range (the UNKNOWN ticket does not
enter the ticking tracker). Come back frozen, wait until the probes are at full status, wait 80 ticks, read again.
Only static readings are compared (the world is frozen between the two readings, so every saved value must come back), and each
comparison needs at least one non-default quantity (_lib.compare_static). Afterwards the networks run again (resume), the long
line is run with only its end chunks force-loaded, a power gauge's zero reading after its chunk reloads is timed, and a pylon and a
pipe anchor are broken while the other end of their wire or pipe is in a chunk that is not loaded. Last, with the world running,
the polonium block in chunk P (below): read, walked away from until P unloads, read in the region file, come back to.

Expected (original 1.7.10 / NEO):
- a chunk unload keeps the network nodes: the original makes a node in updateEntity and destroys it only in invalidate, which a
  1.7.10 chunk unload does not call (TileEntityCableBaseNT.java:16-45, TileEntityPipeBaseNT.java:40-53,86-95); NEO keeps the node
  on onChunkUnloaded (CableBaseBlockEntity.java:25-57, PipeBaseBlockEntity.java:94-102, UniNodespace.java:58). So the two ends of
  the long line keep delivering while its middle is unloaded.
- saved block-entity data comes back unchanged: RTG (TileEntityMachineRTG.java:44-55; MachineRTGBlockEntity.java:138-149),
  barrel (TileEntityBarrel.java:208-221; BarrelBlockEntity.java:324-335), battery socket (TileEntityBatterySocket.java:200-215;
  BatteryBaseBlockEntity.java:143-160), RBMK columns and console (TileEntityRBMKBase.java:268-289, TileEntityRBMKConsole.java:358-385;
  RBMKBaseBlockEntity.java:226-237, RBMKConsoleBlockEntity.java:415-444), pylons and anchors (TileEntityPylonBase.java:144-167,
  TileEntityPipelineBase.java:169-190; PylonBaseBlockEntity.java:142-160, PipeAnchorBlockEntity.java:139-155), ducts
  (TileEntityPipeBaseNT.java:110-119; PipeBaseBlockEntity.java:123-131), moving items (EntityMovingItem.java:90-106; MovingItem.java:124-137).
- chunk radiation: the original's unload handler removes the map entry by the Chunk object from a map keyed by chunk coordinates,
  which removes nothing, and the save that follows writes the value (ChunkRadiationHandlerSimple.java:160-183,187). NEO keeps the
  entry on ChunkEvent.Unload, which vanilla posts before it saves the chunk (ChunkMap.scheduleUnload), and marks the chunk unsaved
  when its value differs from the one it last loaded or saved, so the save that follows writes the value
  (ChunkRadiationHandlerSimple.java:160-201).
- a real source (row mp-unload-radiation-source): see "Polonium block" below.

Polonium block: a block_polonium set over RCON in chunk P, about 30 chunks north of the rigs and of T, adds 75 to its chunk every 20
ticks: the original's BlockHazard.onBlockAdded takes the item's radiation hazard x 0.1 into the block's `rad` and schedules a tick in
20, updateTick adds `rad` to the chunk and schedules the next (BlockHazard.java:120-127,138-146; block_polonium is a BlockHotHazard,
ModBlocks.java:1349; hazard po210 75 x block 10, HazardRegistry.java:83,142); NEO HazardBlock.java:37-51, NtmBlocks.java:193. The
chunk map is updated every 20 server ticks (original ChunkRadiationManager.java:44-54; NEO ChunkRadiationManager.java:58-66), also in
a frozen world; block ticks run only while the world runs and the chunk ticks. The windows the row checks come from the update
rule (original ChunkRadiationHandlerSimple.java:71-122; NEO :72-118): an update rebuilds the map from a copy; every nonzero chunk c
hands 0.6 of its value to itself, 0.075 to each side neighbour and 0.025 to each corner (shares that add up to 1); a share landing on
a chunk that had an entry is added as S <- max(0, (S + share) x 0.99 - 0.05), one share landing on a chunk without an entry
overwrites it.
- floor: a chunk with value v gets at most nine shares, its own 0.6 v among them, and each step only adds a share >= 0, so after one
  update it holds at least 0.6 x 0.99^9 v - 0.05 x (1 + 0.99 + ... + 0.99^8) = 0.54811 v - 0.43241 (the own share first, eight
  shares of 0 after it). FLOOR_MUL = 0.548 and FLOOR_SUB = 0.433 round that against the reading; with exactly one update between
  two block ticks, E emissions from any start leave at least x_E, x_0 = 0, x_(k+1) = max(0, 0.548 (x_k + 75) - 0.433): 40.7,
  63.0, 75.2, ..., 89.8 after 10 and 89.97 at the limit. With no emission k updates leave at least max(0, 0.548 v - 0.433)
  applied k times (from 150: 81.8, 44.4, 23.9, 12.7, 6.5, 3.1, 1.3, 0.3, 0).
- cap: no update adds to the sum of all values (each chunk hands out exactly its value, the 0.99 and the 0.05 only take, an
  overwrite drops a share), so with P's neighbourhood clean before the block (Geiger 0 in P, T 30 chunks away) no chunk holds more
  than 75 x the emissions so far (x 1.001 for float rounding).
- the Geiger counter prints the value cut to one decimal (original ContaminationUtil.java:161; NEO ContaminationUtil.java:78), so a
  reading may be 0.1 under the floor.
- updates between two wall-clock moments: one per 20 server ticks, at most 20 ticks a second plus the server's catch-up after a
  slow tick (at most 2 s): updates in t seconds <= ceil(t) + 3. The region file's save time is in whole seconds (the write came
  before stamp + 1).
Expected: the reading after PO_EMIT ticks is at least x_E (E = the emissions the game time since the placement guarantees) and at
most the cap; the value saved when P unloads is above 0, at least the no-emission floor from the reading taken just before leaving
over the updates the save time allows, and at most the cap; back in P the reading is above 0 and after PO_BACK running ticks at
least x_E again and above the first reading (the block keeps its `rad` in the same server process and its scheduled tick is saved
with the chunk). A build that saves 0 at the unload (the entry dropped before the save) fails the saved value; a block that does
not emit, or emits a tenth or ten times as much, fails the reading windows.
- breaking a pylon or an anchor removes the wire or pipe record at the other end, fetching that block entity even when its chunk is
  not loaded (TileEntityPylonBase.java:92-124, TileEntityPipelineBase.java:89-117; PylonBaseBlockEntity.java:101-116,
  PipeAnchorBlockEntity.java:110-125): Level.getBlockEntity loads that chunk on the server thread.
"""
import importlib.util
import math
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402
import fluidids  # noqa: E402


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parents[1] / rel)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R = _load('stability_rbmk_rig', 'rbmk-reactor/mp_meltdown.py')        # RBMK building helpers; R.Z: the dedicated-server helpers
Z = R.Z
CHUNK = _load('stability_chunk_rad', 'rbmk-reactor/mp_meltdown_chunk.py')  # chunk_reading: the Geiger counter's chunk value

SCENARIO = dict(
    id='power-transmission.mp_stability_unload',
    feature='power-transmission',
    features=['power-transmission', 'fluid-pipelines', 'conveyors', 'conveyor-cranes', 'rbmk-reactor', 'rbmk-console', 'hazard-system',
              'network-architecture', 'battery-storage', 'rtg-power'],
    title='Dedicated server: stability matrix, walk away until the chunks unload and come back (six networks)',
    group='mp',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

G = Z.G
Y = G
H = Z.H
ORIGIN = (3000, 3000)
RAD = 20000.0
PRE_RUN = 300            # client ticks the built world runs before the readings
RESUME = 200             # client ticks of the resume window
LINE_RUN = 200           # client ticks of a long-line delivery window
WATER = fluidids.fluid_ids()['WATER']
MOVING = H + 'moving_item'
# the eight belts of conveyors/cram.py RING: (dx, dz, facing, shape)
RING = [(0, 0, 'south', 'right'), (1, 0, 'west', 'straight'), (2, 0, 'west', 'right'), (2, 1, 'north', 'straight'),
        (2, 2, 'north', 'right'), (1, 2, 'east', 'straight'), (0, 2, 'east', 'right'), (0, 1, 'south', 'straight')]
RING_ITEMS = 6
PO_BLOCK = H + 'block_polonium'
PO_RATE = 75.0           # chunk radiation per block tick (module docstring, "Polonium block")
PO_TICK = 20             # block tick and chunk map update interval
PO_EMIT = 300            # client ticks the block runs before the reading
PO_BACK = 300            # client ticks it runs again after coming back
FLOOR_MUL, FLOOR_SUB = 0.548, 0.433
GEIGER_STEP = 0.1
RBMK_LAYOUT = [['rbmk_blank', 'rbmk_blank', 'rbmk_blank'],
               ['rbmk_rod', 'rbmk_control', 'rbmk_rod'],
               ['rbmk_blank', 'rbmk_blank', 'rbmk_blank']]
SOURCE_AT, CONTROL_AT, FUEL_AT = (0, 1), (1, 1), (2, 1)

PT, FP, CV, RX, HZ, NA = 'power-transmission.', 'fluid-pipelines.', 'conveyors.', 'rbmk-reactor.', 'hazard-system.', 'network-architecture.'
KEEP = 'TileEntityCableBaseNT.java:16-45, TileEntityPipeBaseNT.java:40-53,86-95; CableBaseBlockEntity.java:25-57, PipeBaseBlockEntity.java:94-102, UniNodespace.java:58'
EXPECT = [
    (PT, 'mp-unload-power', '走开到区块卸载再回来（冻结、静置 80 刻后读）：RTG 与电池座（电池组电量）的服务端数据与离开前逐项相同，且有非默认的量',
     'TileEntityMachineRTG.java:44-55, TileEntityBatterySocket.java:200-215; MachineRTGBlockEntity.java:138-149, BatteryBaseBlockEntity.java:143-160'),
    (FP, 'mp-unload-fluid', '走开到区块卸载再回来：电动泵、管道与钢桶（水量、类型、模式）的服务端数据与离开前逐项相同',
     'TileEntityBarrel.java:208-221, TileEntityPipeBaseNT.java:110-119; BarrelBlockEntity.java:324-335, PipeBaseBlockEntity.java:123-131'),
    (CV, 'mp-unload-belts', '走开到区块卸载再回来：环形皮带上运动物品的个数与服务端位置、箱子与抽取器的数据与离开前相同',
     'EntityMovingItem.java:90-106; MovingItem.java:124-137'),
    (RX, 'mp-unload-rbmk', '走开到区块卸载再回来：运行中的 3×3 小堆九根柱与控制台（连接的柱）的服务端数据与离开前逐项相同',
     'TileEntityRBMKBase.java:268-289, TileEntityRBMKConsole.java:358-385; RBMKBaseBlockEntity.java:226-237, RBMKConsoleBlockEntity.java:415-444'),
    (PT, 'mp-unload-line', '走开到区块卸载再回来：跨 12 个区块的长线（重型接线器的导线记录、管锚的管线记录与类型、抽样管道、两端的电炉与钢桶）与离开前逐项相同',
     'TileEntityPylonBase.java:144-167, TileEntityPipelineBase.java:169-190; PylonBaseBlockEntity.java:142-160, PipeAnchorBlockEntity.java:139-155'),
    (HZ, 'mp-unload-radiation-saved', '有辐射的区块（A 站在区块里用 ntmchunkrad set 设成 20,000，周期存盘写下之后在区块里放一块玻璃使它有未存的改动，'
     'A 随即离开，区块在 10 秒存盘冷却内卸载）卸载时存进区块的值大于 0（读区域文件的 hfr_simple_radiation，且写入时间在冷却内，证明是卸载那次存盘写的）：'
     '原版卸载时按 Chunk 对象去删以区块坐标为键的表，什么也没删，随后的存盘写进当时的值',
     'ChunkRadiationHandlerSimple.java:160-183,187; ChunkRadiationHandlerSimple.java:160-201'),
    (HZ, 'mp-unload-radiation', '回来后 A 在该区块用盖革计数器读到的区块辐射大于 0（区块辐射冻结时也每 20 刻重新分配并衰减，没有静止读数，所以只比在不在）',
     'ChunkRadiationHandlerSimple.java:148-158, ChunkRadiationManager.java:45-53; ChunkRadiationHandlerSimple.java:145-158, ChunkRadiationManager.java:58-66'),
    (HZ, 'mp-unload-radiation-source', '真的辐射源：离 T 与装置约 30 个区块的区块 P（离开前盖革读 0）里用 RCON setblock 放一块钋块，世界走 300 刻后'
     '盖革读数在窗口内：下限 x_E（x_0 = 0，x_(k+1) = max(0, 0.548×(x_k+75) − 0.433)，E 是游戏时间保证的放辐射次数；读数截到一位小数，可低 0.1），'
     '上限 75×(可能的放辐射次数)×1.001（一次更新不增加全部区块值之和）；强制加载的区块数为 0；A 随即离开，P 卸载；区域文件里 P 的 hfr_simple_radiation '
     '大于 0，写入时间不早于离开，值不低于离开前读数按“不放辐射”下限 max(0, 0.548v − 0.433) 走过存盘时间允许的更新次数（秒数取整加 3）后的值，'
     '不高于上限（这一下限为 0 而存下的值是 0 时记未执行：分不清存盘缺陷与衰减）；回来后第一次读数大于 0，再走 300 刻后读数不低于 x_E 且高于第一次读数'
     '（同一进程里方块的 rad 还在，排着的更新随区块存盘）。原版：放下时取物品辐射危害 ×0.1（钋 75×10×0.1 = 75），每 20 刻给所在区块加一次；'
     '区块表每 20 刻按本身 0.6、四邻各 0.075、四角各 0.025 重新分配，每加一份乘 0.99 减 0.05',
     'BlockHazard.java:120-127,138-146, ModBlocks.java:1349, HazardRegistry.java:83,142, ChunkRadiationManager.java:44-54, '
     'ChunkRadiationHandlerSimple.java:71-122,160-183, ContaminationUtil.java:161; HazardBlock.java:37-51, NtmBlocks.java:193, '
     'ChunkRadiationManager.java:58-66, ChunkRadiationHandlerSimple.java:72-118,145-201, ContaminationUtil.java:78'),
    (NA, 'mp-unload-unloaded', '离开期间每个探测位置所在的区块都不在完整加载状态（execute if block 答“该位置未加载”），之后再等 100 刻',
     'ChunkMap.scheduleUnload; record'),
    (NA, 'mp-unload-resume', '回来后让世界走 200 刻：电池组电量上升、清空的钢桶重新有水、皮带上的物品在动且总数不变、源棒的物品数据在变（反应堆在运行）',
     KEEP),
    (NA, 'mp-unload-line-delivers', '两人都在远处、只强制加载长线两端的区块（中间的接线器与管道所在区块未加载）：清空末端电炉与钢桶后走 200 刻，两者都收到了电与水'
     '（区块卸载保留节点）', KEEP),
    (PT, 'mp-unload-gauge-zero', '记录：功率计所在区块卸载再重新加载后（世界在走），功率计的读数为 0 持续多久（客户端刻、墙钟与服务端刻）', 'CableGaugeBlockEntity.java:20-40; record'),
    (PT, 'mp-unload-break-pylon', '强制加载一个区块，输电塔在它两格外（完整加载、不走刻），导线另一端的输电塔在三格外（未加载）：拆掉前者，另一端的导线记录被清掉，'
     '日志里没有异常；记录这一刻前后的每刻耗时', 'TileEntityPylonBase.java:92-124; PylonBaseBlockEntity.java:101-116, PylonDummyableBlock.java:43-45'),
    (FP, 'mp-unload-break-anchor', '同样拆一个管锚，管线另一端的管锚在未加载的区块里：另一端的管线记录被清掉，日志里没有异常；记录每刻耗时',
     'TileEntityPipelineBase.java:89-117; PipeAnchorBlockEntity.java:110-125, FluidPipeAnchorBlock.java:75-77'),
    (PT, 'mp-unload-log', '这个场景期间服务端日志里没有 Exception 或 ERROR 行（客户端为重连断开的连接重置除外）', 'server log'),
]


def expectations():
    return [dict(id=f + k, text=t, source=s) for f, k, t, s in EXPECT]


# ---------------------------------------------------------------- positions

def layout(ox, oz):
    """Every position of the rigs for an origin; the cluster spans about 25 x 25 blocks, the radiation chunk is about seven chunks
    east of it, the long line 40 chunks south, the break pairs 80 chunks south."""
    s = dict(origin=(ox, oz))
    s['rtg'] = (ox, Y, oz + 1)
    s['gauge'] = (ox + 3, Y, oz + 1)
    s['cables'] = [(ox + 1, Y, oz + 1), (ox + 2, Y, oz + 1), (ox + 4, Y, oz + 1), (ox + 5, Y, oz + 1), (ox + 6, Y, oz + 1)]
    s['socket_click'] = (ox + 6, oz)            # facing south; its port is the cell south of the core, (ox + 6, oz + 1)
    s['gauge_eye'] = [ox + 3.5, Y, oz + 3.1]
    s['pump_click'] = (ox + 6, oz + 14)
    s['ring'] = (ox + 20, oz + 2)
    s['chest'] = (ox + 21, Y, oz)
    s['extractor'] = (ox + 21, Y, oz + 1)
    s['rbmk'] = (ox + 20, oz + 14)
    s['console_click'] = (ox + 21, oz + 21)
    s['spot_a'] = [ox + 12.5, Y + 8, oz + 10.5]
    tcx, tcz = (ox + 112) >> 4, (oz + 8) >> 4
    s['rad_chunk'] = (tcx, tcz)
    s['rad_spot'] = [tcx * 16 + 8.5, Y + 5, tcz * 16 + 8.5]
    pcx, pcz = (ox + 8) >> 4, (oz - 480) >> 4
    s['po_chunk'] = (pcx, pcz)
    s['po_spot'] = [pcx * 16 + 8.5, Y + 5, pcz * 16 + 8.5]
    s['po_block'] = (pcx * 16 + 3, Y, pcz * 16 + 3)
    s['po_probe'] = (pcx * 16 + 8, Y, pcz * 16 + 8)
    l0 = ox >> 4
    lx = l0 * 16 + 8
    zl = ((oz + 640) >> 4) * 16 + 4
    zf = zl + 8
    s['line'] = dict(lx=lx, zl=zl, zf=zf, rtg=(lx - 1, Y, zl), cable1=(lx, Y, zl), c1=(lx, Y + 1, zl), stone=(lx + 96, Y, zl),
                     c2=(lx + 96, Y + 1, zl), cable3=(lx + 192, Y, zl), c3=(lx + 192, Y + 1, zl), furnace=(lx + 193, Y, zl),
                     src=(lx - 1, Y, zf), duct0=(lx, Y, zf), a1=(lx + 1, Y, zf), duct_a2=(lx + 12, Y, zf), a2=(lx + 11, Y, zf),
                     run=((lx + 12, Y, zf), (lx + 180, Y, zf)), a3=(lx + 181, Y, zf), a4=(lx + 191, Y, zf), duct_a4=(lx + 192, Y, zf),
                     dst=(lx + 193, Y, zf), mid=(lx + 96, Y, zf), spot_b=[lx + 96.5, Y + 8, zl + 4.5],
                     ends=((lx, zl), (lx + 192, zl)), samples=[(lx + 12, Y, zf), (lx + 40, Y, zf), (lx + 96, Y, zf), (lx + 152, Y, zf), (lx + 180, Y, zf)])
    kc, kzc = ox >> 4, (oz + 1300) >> 4
    zb, zq = kzc * 16 + 4, kzc * 16 + 12
    s['brk'] = dict(force=(kc * 16 + 8, kzc * 16 + 8), p1=(16 * (kc + 2) + 12, Y, zb), p2=(16 * (kc + 3) + 4, Y, zb),
                    d1=(16 * (kc + 2) + 13, Y, zq), q1=(16 * (kc + 2) + 14, Y, zq), d2=(16 * (kc + 3) + 3, Y, zq), q2=(16 * (kc + 3) + 2, Y, zq),
                    zb=zb, zq=zq, spot=[16 * (kc + 2) + 16.5, Y + 6, kzc * 16 + 8.5])
    return s


def cluster_probes(s):
    out = [s['rtg'], s['chest'], s['extractor'], (s['rbmk'][0] + 1, Y, s['rbmk'][1] + 1), s['rad_spot'][:1] + [Y] + s['rad_spot'][2:]]
    out += [p for p in (s.get('socket'), s.get('pump'), s.get('barrel'), s.get('console')) if p]
    return [tuple(int(c) for c in p) for p in out]


def line_probes(s):
    L = s['line']
    return [L['c1'], L['c2'], L['c3'], L['src'], L['dst'], L['mid']]


# ---------------------------------------------------------------- small helpers

def cmd(ctx, command):
    """A command over RCON; a rejected one (unknown, not loaded, no block entity) stops the scenario."""
    reply = Z.rcon1(ctx, command)
    if re.search(r'Unknown|Incorrect|not loaded|<--\[HERE\]|Could not set|is not a block entity|No entity', reply):
        raise RuntimeError('%s -> %s' % (command, reply[:160]))
    return reply


def setblock(ctx, pos, block):
    return Z.rcon1(ctx, 'setblock %d %d %d %s' % (tuple(pos) + (block,)))


def data(ctx, pos):
    return _lib.block_data(ctx, pos)


def charge(d):
    for it in d.get('Items', []):
        if it.get('Slot', 0) == 0:
            return (it.get('components') or {}).get('minecraft:custom_data', {}).get('Charge', 0)
    return None


def cons(d):
    return sorted(tuple(c) for c in d.get('connections', []))


def flat(parts):
    """{'name.key': value} of {name: block data}, the readings compare_static takes."""
    return {'%s.%s' % (name, k): v for name, d in parts.items() for k, v in (d.items() if isinstance(d, dict) else [('value', d)])}


def view(ctx, who, pos, look=None, fly=True):
    if look is None:
        return ctx.step('view', client=who, pos=list(pos), yaw=0.0, pitch=60.0, fly=fly, hide_gui=False)
    return ctx.step('view', client=who, pos=list(pos), look_at=list(look), fly=fly, hide_gui=False)


def ring_selector(s):
    bx, bz = s['ring']
    return '@e[type=%s,x=%d,y=%d,z=%d,dx=4,dy=3,dz=6]' % (MOVING, bx - 1, Y - 1, bz - 3)


# ---------------------------------------------------------------- building (A, frozen world)

def build_power(ctx, a, s):
    x, z = s['socket_click']
    core = Z.place_by_hand(ctx, a, H + 'machine_battery_socket', x, z, H + 'machine_battery_socket', ((x - 3, Y, z - 3), (x + 3, Y + 2, z + 3)))
    if core != (x, Y, z):
        raise RuntimeError('battery socket core at %s, expected %s' % (core, (x, Y, z)))
    s['socket'] = core
    setblock(ctx, s['rtg'], H + 'machine_rtg')
    for c in s['cables']:
        setblock(ctx, c, H + 'red_cable')
    setblock(ctx, s['gauge'], H + 'red_cable_gauge')
    ctx.step('wait', client=a, ticks=4)
    for slot in (0, 1):
        cmd(ctx, 'item replace block %d %d %d container.%d with %spellet_rtg' % (s['rtg'] + (slot, H)))
    cmd(ctx, 'item replace block %d %d %d container.0 with %sbattery_pack' % (core + (H,)))


def build_fluid(ctx, a, s):
    x, z = s['pump_click']
    core = Z.place_by_hand(ctx, a, H + 'pump_electric', x, z, H + 'pump_electric', ((x - 4, Y, z - 4), (x + 4, Y + 4, z + 4)))
    s['pump'] = core
    cx, _, cz = core
    s['pump_cable'] = (cx + 2, Y, cz)
    s['pump_rtg'] = (cx + 3, Y, cz)
    s['ducts'] = [(cx - 2, Y, cz), (cx - 3, Y, cz)]
    s['barrel'] = (cx - 4, Y, cz)
    setblock(ctx, s['pump_cable'], H + 'red_cable')
    setblock(ctx, s['pump_rtg'], H + 'machine_rtg')
    for d in s['ducts']:
        setblock(ctx, d, '%sfluid_duct_neo{Type:%d}' % (H, WATER))
    setblock(ctx, s['barrel'], H + 'barrel_steel')
    ctx.step('wait', client=a, ticks=4)
    for slot in (0, 1):
        cmd(ctx, 'item replace block %d %d %d container.%d with %spellet_rtg' % (s['pump_rtg'] + (slot, H)))
    cmd(ctx, 'data merge block %d %d %d {mode:0s,tank_type:"WATER"}' % s['barrel'])


def build_belts(ctx, a, s):
    bx, bz = s['ring']
    for dx, dz, facing, shape in RING:
        setblock(ctx, (bx + dx, Y, bz + dz), '%sconveyor[facing=%s,shape=%s]' % (H, facing, shape))
    setblock(ctx, s['chest'], 'minecraft:chest')
    setblock(ctx, s['extractor'], H + 'crane_extractor[input=south,output=north]')
    ctx.step('wait', client=a, ticks=4)
    cmd(ctx, 'item replace block %d %d %d container.19 with %supgrade_ejector_3' % (s['extractor'] + (H,)))
    cmd(ctx, 'item replace block %d %d %d container.0 with minecraft:cobblestone %d' % (s['chest'] + (RING_ITEMS,)))


def load_rod(ctx, a, pos, item):
    """A opens the rod column's screen and shift-clicks one `item` in (as mp_meltdown.load_fuel does with natural uranium)."""
    R.open_column(ctx, a, pos[0], pos[2], 'RBMKRodScreen')
    ctx.rcon('give %s %s 1' % (a, item))
    ctx.step('wait', client=a, ticks=6)
    slot = None
    reply = Z.rcon1(ctx, 'data get entity %s Inventory' % a)
    for e in _lib.data_value(reply) if reply and '[' in reply else []:
        if e.get('id') == item:
            slot = e.get('Slot')
    if slot is None:
        raise RuntimeError('%s did not get %s' % (a, item))
    Z.shift_click(ctx, a, _lib.menu_slot(1, slot))
    ctx.step('close', client=a)
    return _lib.slot_count(_lib.block_data(ctx, pos), 0, item)


def build_rbmk(ctx, a, s):
    cells, built = R.build(ctx, a, s['rbmk'], RBMK_LAYOUT)
    s['cells'] = cells
    src = load_rod(ctx, a, cells[SOURCE_AT], H + 'rbmk_fuel_ra226be')
    fuel = load_rod(ctx, a, cells[FUEL_AT], H + 'rbmk_fuel_ueu')
    cx, cz = s['console_click']
    console = Z.place_by_hand(ctx, a, H + 'rbmk_console', cx, cz, H + 'rbmk_console', ((cx - 4, Y, cz - 4), (cx + 4, Y + 4, cz + 4)))
    s['console'] = console
    # link on the blank column north of the control column (rbmk-console/mp_console.py): a plain right-click on a column with a screen
    # opens it (original RBMKBase.openInv :105-125, NEO RBMKRodBlock), a blank has none, so the device's own use runs
    centre = cells[(1, 0)]
    Z.hand(ctx, a, H + 'rbmk_tool')
    R.use_top(ctx, a, centre[0], centre[2])
    R.sneak_use(ctx, a, (console[0], Y + 1, console[2]), 'south', stand=(console[0] + 0.5, Y, console[2] + 3.5),
                look=(console[0] + 0.5, Y + 1, console[2] + 0.5), fly=True, any_hit=True)
    ctx.rcon('item replace entity %s hotbar.0 with minecraft:air' % a)
    cd = data(ctx, console)
    linked = (cd.get('tX'), cd.get('tY'), cd.get('tZ')) == tuple(centre)
    return dict(built=built, source=src, fuel=fuel, linked=linked)


def wire(ctx, a, first, second, face_first, stand_first, face_second, stand_second):
    """The cable drum on two wire ends (a pylon or connector each): right-click the first, then the second."""
    Z.hand(ctx, a, H + 'wiring_red_copper')
    _lib.use_center(ctx, first, face_first, stand_first, fly=True)
    _lib.use_center(ctx, second, face_second, stand_second, fly=True)
    ctx.rcon('item replace entity %s hotbar.0 with minecraft:air' % a)


def build_line(ctx, a, s, with_items=False):
    L = s['line']
    lx, zl, zf = L['lx'], L['zl'], L['zf']
    view(ctx, a, L['spot_b'])
    ctx.step('wait', client=a, ticks=40)
    setblock(ctx, L['rtg'], H + 'machine_rtg')
    setblock(ctx, L['cable1'], H + 'red_cable')
    setblock(ctx, L['c1'], H + 'red_connector_super[facing=up]')
    setblock(ctx, L['stone'], 'minecraft:stone')
    setblock(ctx, L['c2'], H + 'red_connector_super[facing=up]')
    setblock(ctx, L['cable3'], H + 'red_cable')
    setblock(ctx, L['c3'], H + 'red_connector_super[facing=up]')
    setblock(ctx, L['furnace'], H + 'machine_electric_furnace')
    setblock(ctx, L['src'], H + 'barrel_steel')
    setblock(ctx, L['duct0'], '%sfluid_duct_neo{Type:%d}' % (H, WATER))
    cmd(ctx, 'fill %d %d %d %d %d %d %sfluid_duct_neo{Type:%d}' % (L['run'][0] + L['run'][1] + (H, WATER)))
    setblock(ctx, L['duct_a4'], '%sfluid_duct_neo{Type:%d}' % (H, WATER))
    setblock(ctx, L['dst'], H + 'barrel_steel')
    ctx.step('wait', client=a, ticks=4)
    for slot in (0, 1):
        cmd(ctx, 'item replace block %d %d %d container.%d with %spellet_rtg' % (L['rtg'] + (slot, H)))
    cmd(ctx, 'data merge block %d %d %d {mode:2s,tank_type:"WATER"}' % L['src'])
    cmd(ctx, 'item replace block %d %d %d container.2 with %sfluid_barrel_infinite' % (L['src'] + (H,)))
    cmd(ctx, 'data merge block %d %d %d {mode:0s,tank_type:"WATER"}' % L['dst'])
    if with_items:
        cmd(ctx, 'item replace block %d %d %d container.1 with minecraft:cobblestone 64' % L['furnace'])
    # anchors as a placement leaves them (FACING = the clicked face, the attached duct behind it: FluidPipeAnchorBlock.java:47-49,
    # PipeAnchorBlockEntity.java:76-90): A1 on the east face of the first duct, A2 on the west face of the duct at lx + 12, A3 / A4
    # the same at the far end; typed water like the ducts
    for p, facing in ((L['a1'], 'east'), (L['a2'], 'west'), (L['a3'], 'east'), (L['a4'], 'west')):
        setblock(ctx, p, '%spipe_anchor[facing=%s]{Type:%d}' % (H, facing, WATER))
    ctx.step('wait', client=a, ticks=4)
    Z.hand(ctx, a, H + 'wrench')
    for first, second in ((L['a1'], L['a2']), (L['a3'], L['a4'])):
        _lib.use_center(ctx, first, 'south', [first[0] + 0.5, Y, zf + 2.5], fly=True)
        _lib.use_center(ctx, second, 'south', [second[0] + 0.5, Y, zf + 2.5], fly=True)
    ctx.rcon('item replace entity %s hotbar.0 with minecraft:air' % a)
    # wires C1 - C2 - C3 (96 blocks each, the heavy connector reaches 100: ConnectorSuperBlockEntity.java:22)
    above = lambda c: [c[0] + 0.5, Y + 3, c[2] + 1.5]
    wire(ctx, a, L['c1'], L['c2'], 'up', above(L['c1']), 'up', above(L['c2']))
    wire(ctx, a, L['c2'], L['c3'], 'up', above(L['c2']), 'up', above(L['c3']))
    d1, d2, d3 = data(ctx, L['c1']), data(ctx, L['c2']), data(ctx, L['c3'])
    a1, a3 = data(ctx, L['a1']), data(ctx, L['a3'])
    ok = (cons(d1) == [L['c2']] and cons(d2) == sorted([L['c1'], L['c3']]) and cons(d3) == [L['c2']]
          and cons(a1) == [L['a2']] and cons(a3) == [L['a4']])
    return dict(ok=ok, wires=(cons(d1), cons(d2), cons(d3)), pipes=(cons(a1), cons(a3)))


def build_break_pairs(ctx, a, s):
    B = s['brk']
    view(ctx, a, B['spot'])
    ctx.step('wait', client=a, ticks=40)
    p1, p2, zb, zq = B['p1'], B['p2'], B['zb'], B['zq']
    Z.hand(ctx, a, H + 'red_pylon')
    for p in (p1, p2):
        _lib.use_on(ctx, (p[0], Y - 1, p[2]), 'up', [p[0] - 2.5, Y, zb + 0.5], fly=True)
        Z.hand(ctx, a, H + 'red_pylon')
    ctx.rcon('item replace entity %s hotbar.0 with minecraft:air' % a)
    wire(ctx, a, p1, p2, 'west', [p1[0] - 2.5, Y, zb + 0.5], 'west', [p2[0] - 2.5, Y, zb + 0.5])
    for d in (B['d1'], B['d2']):
        setblock(ctx, d, '%sfluid_duct_neo{Type:%d}' % (H, WATER))
    setblock(ctx, B['q1'], '%spipe_anchor[facing=east]{Type:%d}' % (H, WATER))
    setblock(ctx, B['q2'], '%spipe_anchor[facing=west]{Type:%d}' % (H, WATER))
    ctx.step('wait', client=a, ticks=4)
    Z.hand(ctx, a, H + 'wrench')
    _lib.use_center(ctx, B['q1'], 'south', [B['q1'][0] + 0.5, Y, zq + 2.5], fly=True)
    _lib.use_center(ctx, B['q2'], 'south', [B['q2'][0] + 0.5, Y, zq + 2.5], fly=True)
    ctx.rcon('item replace entity %s hotbar.0 with minecraft:air' % a)
    ok = cons(data(ctx, p1)) == [p2] and cons(data(ctx, p2)) == [p1] and cons(data(ctx, B['q1'])) == [B['q2']] and cons(data(ctx, B['q2'])) == [B['q1']]
    return dict(ok=ok)


def build_all(ctx, a, s, line_items=False, break_pairs=False):
    """Builds every rig of `s` in a frozen world; returns the build record (each part's own check)."""
    ctx.server('tick freeze')
    view(ctx, a, s['spot_a'])
    ctx.step('wait', client=a, ticks=40)
    rec = {}
    build_power(ctx, a, s)
    build_fluid(ctx, a, s)
    build_belts(ctx, a, s)
    view(ctx, a, s['spot_a'])
    rec['rbmk'] = build_rbmk(ctx, a, s)
    rec['line'] = build_line(ctx, a, s, with_items=line_items)
    if break_pairs:
        rec['break_pairs'] = build_break_pairs(ctx, a, s)
    return rec


# ---------------------------------------------------------------- readings

def read_power(ctx, s):
    return flat(dict(rtg=data(ctx, s['rtg']), socket=data(ctx, s['socket'])))


def read_fluid(ctx, s):
    parts = dict(barrel=data(ctx, s['barrel']), pump=data(ctx, s['pump']))
    for i, d in enumerate(s['ducts']):
        parts['duct%d' % i] = data(ctx, d)
    return flat(parts)


def read_belts(ctx, s):
    sel = ring_selector(s)
    pos = sorted(tuple(round(c, 4) for c in p) for p in Z.server_positions(ctx, sel))
    return flat(dict(chest=data(ctx, s['chest']), extractor=data(ctx, s['extractor']), moving=dict(count=Z.entity_count(ctx, sel), positions=pos)))


def read_rbmk(ctx, s):
    parts = {'col%d%d' % k: data(ctx, p) for k, p in s['cells'].items()}
    parts['console'] = data(ctx, s['console'])
    return flat(parts)


def read_line(ctx, s):
    L = s['line']
    parts = {k: data(ctx, L[k]) for k in ('rtg', 'c1', 'c2', 'c3', 'furnace', 'src', 'dst', 'a1', 'a2', 'a3', 'a4')}
    for i, p in enumerate(L['samples']):
        parts['duct%d' % i] = data(ctx, p)
    return flat(parts)


READERS = (('power', read_power), ('fluid', read_fluid), ('belts', read_belts), ('rbmk', read_rbmk), ('line', read_line))


def read_all(ctx, s):
    return {name: fn(ctx, s) for name, fn in READERS}


def compare_cells(before, after):
    return {name: _lib.compare_static(before[name], after[name]) for name in before}


def cell_detail(c, limit=600):
    text = c['detail']
    return text if len(text) <= limit else text[:limit] + ' ...'


# ---------------------------------------------------------------- radiation

def geiger_prefix(ctx, who):
    return ctx.step('i18n', client=who, keys=['geiger.chunkRad'])['texts']['geiger.chunkRad'].split('Format error: ')[-1].split('%s')[0]


def geiger(ctx, who, prefix):
    """The chunk radiation of the block the player stands in, from the Geiger counter's chat line (CHUNK.chunk_reading)."""
    ctx.rcon('item replace entity %s hotbar.0 with %sgeiger_counter' % (who, H))
    ctx.step('wait', client=who, ticks=2)
    return CHUNK.chunk_reading(ctx, who, prefix)


def to_rad_spot(ctx, a, s):
    """A hovers in the middle of chunk T looking up, so a use of the Geiger counter hits no block."""
    ctx.step('view', client=a, pos=list(s['rad_spot']), yaw=0.0, pitch=-90.0, fly=True, hide_gui=False)


def set_radiation(ctx, a, s, value=RAD):
    to_rad_spot(ctx, a, s)
    full = _lib.wait_full(ctx, a, [tuple(int(c) for c in s['rad_spot'])])
    reply = Z.rcon1(ctx, 'execute as %s at %s run ntmchunkrad set %s' % (a, a, value))
    return dict(full=full['ok'], reply=reply[:160])


def radiation_unload(ctx, a, b, s, value=RAD):
    """From a frozen world: B parks, the world runs, A sets chunk T, waits for the periodic save to write it, places a glass block in
    T (T unsaved again; the periodic save of T is in its 10 s cooldown), parks, and T unloads. Returns the record: saved value and
    region save time before the glass and after the unload; decisive when the first write came after the set and the second within
    10 s of it (so the unload's save wrote it, not a later periodic save)."""
    _lib.park(ctx, [b])
    ctx.server('tick unfreeze')
    t_set = time.time()
    rad_set = set_radiation(ctx, a, s, value)
    ctx.step('wait', client=a, ticks=20)
    saved0, stamp0 = saved_radiation(s)
    tx, tz = s['rad_chunk']
    glass = (tx * 16 + 3, Y + 2, tz * 16 + 3)
    reply = Z.rcon1(ctx, 'setblock %d %d %d minecraft:glass' % glass)
    t_dirty = time.time()
    forced = _lib.forced_chunks(ctx)
    _lib.park(ctx, [a, b])
    probe = (tx * 16 + 8, Y, tz * 16 + 8)
    w = _lib.wait_unloaded(ctx, a, [probe], settle_ticks=100)
    saved1, stamp1 = saved_radiation(s)
    ctx.server('tick freeze')
    decisive = (stamp0 is not None and stamp0 >= int(t_set) and stamp1 is not None and 0 < stamp1 - stamp0 < 10)
    return dict(decisive=decisive, set=rad_set, saved_before_glass=saved0, save_time_before_glass=stamp0, glass=glass, glass_reply=reply[:80],
                glass_after_set_s=round(t_dirty - t_set, 2), forced_chunks_before_leaving=forced[0], forced_reply=forced[1][:120], unloaded=w,
                saved_after=saved1, save_time_after=stamp1)


def saved_radiation(s, key='rad_chunk'):
    root, stamp = _lib.saved_chunk(*s[key])
    return (root.get('hfr_simple_radiation') if isinstance(root, dict) else None), stamp


# ---------------------------------------------------------------- a real source: the polonium block (module docstring)

def floor_emitting(emissions):
    """Least chunk value after `emissions` block ticks of 75 with one map update after each, from any start >= 0: x_E."""
    x = 0.0
    for _ in range(max(emissions, 0)):
        x = max(0.0, FLOOR_MUL * (x + PO_RATE) - FLOOR_SUB)
    return x


def floor_decay(value, updates):
    """Least chunk value `updates` map updates after it held `value`, with no emission in between."""
    x = value
    for _ in range(max(updates, 0)):
        x = max(0.0, FLOOR_MUL * x - FLOOR_SUB)
    return x


def cap(emissions):
    """Most any chunk can hold after `emissions` block ticks of 75 in a clean neighbourhood: the sum of all values."""
    return PO_RATE * max(emissions, 0) * 1.001


def updates_within(seconds):
    """Most map updates in `seconds` of wall time: one per 20 server ticks, 20 ticks a second plus up to 2 s of catch-up."""
    return math.ceil(max(seconds, 0.0)) + 3


def to_po_spot(ctx, who, s):
    """`who` hovers in the middle of chunk P looking up (a use of the Geiger counter hits no block)."""
    ctx.step('view', client=who, pos=list(s['po_spot']), yaw=0.0, pitch=-90.0, fly=True, hide_gui=False)


def po_place(ctx, who, s, prefix):
    """World running: `who` goes to chunk P, reads the Geiger baseline there and the block is set over RCON. Returns the record
    with the game time just before and just after the setblock."""
    to_po_spot(ctx, who, s)
    full = _lib.wait_full(ctx, who, [s['po_probe']])
    base = geiger(ctx, who, prefix)
    t0 = ctx.server()['game_time']
    reply = Z.rcon1(ctx, 'setblock %d %d %d %s' % (s['po_block'] + (PO_BLOCK,)))
    t1 = ctx.server()['game_time']
    return dict(full=full['ok'], base=base[0], base_line=str(base[1])[:120], reply=reply[:80], placed='Changed' in reply,
                t_before=t0, t_after=t1)


def po_reading(ctx, who, prefix, p):
    """A Geiger reading in chunk P with its window: E_min emissions the game time since the placement guarantees (the first
    block tick comes 20 ticks after the placement, one less for the tick in progress), E_max the most it allows."""
    g0 = ctx.server()['game_time']
    wall = time.time()
    value, line = geiger(ctx, who, prefix)
    g1 = ctx.server()['game_time']
    e_min = (g0 - p['t_after']) // PO_TICK - 1
    e_max = (g1 - p['t_before']) // PO_TICK + 1
    lo, hi = floor_emitting(e_min), cap(e_max)
    ok = value is not None and lo - GEIGER_STEP <= value <= hi
    return dict(value=value, line=str(line)[:120], wall=wall, game=(g0, g1), e_min=e_min, e_max=e_max, floor=round(lo, 3),
                cap=round(hi, 1), ok=ok)


def po_saved(s, r0, t_leave, p, game_now):
    """The value the region file holds for chunk P, checked against the reading r0 taken before it was saved: the save time not
    before `t_leave`, the value at least the no-emission floor from r0 over the updates the save time allows and at most the cap
    of the emissions up to `game_now`. decisive: that floor is above 0 (a 0 then is a wrong save, not decay)."""
    saved, stamp = saved_radiation(s, 'po_chunk')
    k = updates_within(stamp + 1 - r0['wall']) if stamp is not None else None
    lo = floor_decay(r0['value'] or 0.0, k) if k is not None else 0.0
    hi = cap((game_now - p['t_before']) // PO_TICK + 1)
    ok = (saved is not None and stamp is not None and stamp >= int(t_leave) and saved > 0 and saved >= lo - 1e-3 and saved <= hi)
    return dict(saved=saved, stamp=stamp, after_leaving=stamp is not None and stamp >= int(t_leave), updates_max=k, floor=round(lo, 3),
                cap=round(hi, 1), decisive=lo > 0, ok=ok)


def po_unload(ctx, a, b, s, prefix):
    """The polonium block of the module docstring in the walk-away situation. The world runs throughout (it already runs after the
    break test) and is left running."""
    ctx.server('tick unfreeze')
    _lib.park(ctx, [b])
    p = po_place(ctx, a, s, prefix)
    ctx.step('wait', client=a, ticks=PO_EMIT)
    r0 = po_reading(ctx, a, prefix, p)
    forced = _lib.forced_chunks(ctx)
    t_leave = time.time()
    _lib.park(ctx, [a])
    w = _lib.wait_unloaded(ctx, a, [s['po_probe']], settle_ticks=100)
    sv = po_saved(s, r0, t_leave, p, ctx.server()['game_time'])
    to_po_spot(ctx, a, s)
    back = _lib.wait_full(ctx, a, [s['po_probe']])
    t_back = ctx.server()['game_time']
    r1, r1_line = geiger(ctx, a, prefix)
    ctx.step('wait', client=a, ticks=PO_BACK)
    t_r2 = ctx.server()['game_time']
    r2, r2_line = geiger(ctx, a, prefix)
    # the block ticks again once P ticks with A in it: two block ticks off for the load and the tick in progress
    e_back = (t_r2 - t_back) // PO_TICK - 2
    floor_back = floor_emitting(e_back)
    first_up = r1 is not None and r1 > 0
    rising = r1 is not None and r2 is not None and r2 >= floor_back - GEIGER_STEP and r2 > r1
    return dict(place=p, before_leaving=r0, forced=forced[0], forced_reply=forced[1][:120], unloaded=w, saved=sv,
                back=dict(back_full=back['ok'], first=r1, first_line=str(r1_line)[:120], after=r2, after_line=str(r2_line)[:120], game=(t_back, t_r2),
                          e_min=e_back, floor=round(floor_back, 3), first_up=first_up, rising=rising))


def po_unload_check(ctx, rec):
    p, r0, sv, back = rec['place'], rec['before_leaving'], rec['saved'], rec['back']
    pre = p['full'] and p['placed'] and p['base'] == 0.0
    rest = pre and r0['ok'] and rec['forced'] == 0 and rec['unloaded']['ok'] and back['back_full'] and back['rising']
    ok = rest and sv['ok'] and back['first_up']
    if rest and not sv['ok'] and not sv['decisive'] and sv['saved'] == 0 and sv['after_leaving']:
        # the save came so late after the reading that the floor is 0: a 0 does not separate a wrong save from decay (and the
        # first reading after coming back is then 0 as well)
        ctx.not_run(HZ + 'mp-unload-radiation-source', 'the save was not decisive (floor 0 over %s updates): %s' % (sv['updates_max'], rec))
        return
    ctx.check(HZ + 'mp-unload-radiation-source', ok, str(rec))


# ---------------------------------------------------------------- running, resume and the long line

def run_for(ctx, who, ticks):
    """Unfreezes, waits `ticks` client ticks, freezes and waits 80 client ticks (the nets keep transferring about 3 s after a freeze)."""
    ctx.server('tick unfreeze')
    ctx.step('wait', client=who, ticks=ticks)
    _lib.still(ctx)


def resume(ctx, a, s, before_total=RING_ITEMS):
    """Runs the cluster RESUME ticks after the comparison and reports whether every network still works."""
    sel = ring_selector(s)
    c0 = charge(data(ctx, s['socket']))
    cmd(ctx, 'data merge block %d %d %d {tank:0}' % s['barrel'])
    p0 = sorted(Z.server_positions(ctx, sel))
    src0 = data(ctx, s['cells'][SOURCE_AT])
    view(ctx, a, s['spot_a'])
    run_for(ctx, a, RESUME)
    c1 = charge(data(ctx, s['socket']))
    fill = _lib.tanks(data(ctx, s['barrel'])).get('tank', {}).get('fill')
    p1 = sorted(Z.server_positions(ctx, sel))
    chest = sum(it.get('count', 1) for it in data(ctx, s['chest']).get('Items', []))
    src1 = data(ctx, s['cells'][SOURCE_AT])
    rod_moved = src0.get('Items') != src1.get('Items') or src0.get('heat') != src1.get('heat')
    parts = dict(power=c1 is not None and c0 is not None and c1 > c0, fluid=bool(fill), belts=len(p1) + chest == before_total and p1 != p0 and len(p1) > 0,
                 rbmk=rod_moved)
    detail = ('battery charge %s -> %s; drained barrel after %d ticks %s mB; moving items %d -> %d (chest %d, total %d of %d), positions changed %s; '
              'source rod heat %s -> %s, item data changed %s' % (c0, c1, RESUME, fill, len(p0), len(p1), chest, len(p1) + chest, before_total, p1 != p0,
                                                                src0.get('heat'), src1.get('heat'), src0.get('Items') != src1.get('Items')))
    return all(parts.values()), parts, detail


def line_delivery(ctx, a, b, s, label):
    """Both players parked (the line not at full status), the two end chunks force-loaded; the far furnace and barrel drained; LINE_RUN
    ticks; returns (power gained, water gained, detail). The force-loads are removed again."""
    L = s['line']
    for x, z in L['ends']:
        cmd(ctx, 'forceload add %d %d' % (x, z))
    ctx.step('wait', client=a, ticks=40)
    state = {k: _lib.chunk_full(ctx, L[k]) for k in ('c1', 'c2', 'c3', 'src', 'dst', 'mid')}
    cmd(ctx, 'data merge block %d %d %d {power:0L}' % L['furnace'])
    cmd(ctx, 'data merge block %d %d %d {tank:0}' % L['dst'])
    run_for(ctx, a, LINE_RUN)
    power = data(ctx, L['furnace']).get('power')
    water = _lib.tanks(data(ctx, L['dst'])).get('tank', {}).get('fill')
    cmd(ctx, 'forceload remove all')
    middle_unloaded = not state['c2'] and not state['mid']
    ends_loaded = state['c1'] and state['c3'] and state['src'] and state['dst']
    detail = ('%s: full status during the window %s (middle not loaded %s, ends loaded %s); after %d ticks the drained furnace holds %s HE, '
              'the drained barrel %s mB' % (label, state, middle_unloaded, ends_loaded, LINE_RUN, power, water))
    return dict(power=power, water=water, middle_unloaded=middle_unloaded, ends_loaded=ends_loaded, detail=detail)


# ---------------------------------------------------------------- the power gauge after a reload

HE_T = re.compile(r'([\d.,]+)\s*([kMGTP]?)\s*HE/t')


def gauge_text(ctx, a, s):
    hud = ctx.step('hud', client=a, frames=2)
    texts = _lib.crosshair_texts(hud)
    hit = hud.get('hit') == [float(c) for c in s['gauge']]
    for t in texts:
        m = HE_T.search(t)
        if m:
            return hit, t, bool(re.search(r'[1-9]', m.group(1)))
    return hit, None, False


def gauge_zero_time(ctx, a, b, s, limit_ticks=600):
    """The world runs: A looks at the gauge until it shows power (baseline), both park until the power rig is not at full status,
    A comes back and reads the gauge every few client ticks until it shows power again. Returns the record."""
    ctx.server('tick unfreeze')
    view(ctx, a, s['gauge_eye'], look=[s['gauge'][0] + 0.5, Y + 0.5, s['gauge'][2] + 0.5])
    base = None
    for _ in range(60):
        hit, text, nonzero = gauge_text(ctx, a, s)
        if nonzero:
            base = text
            break
        ctx.step('wait', client=a, ticks=4)
    _lib.park(ctx, [a, b])
    w = _lib.wait_unloaded(ctx, a, [s['gauge'], s['rtg'], s['socket']], settle_ticks=60)
    g0 = ctx.server()['game_time']
    t0 = time.time()
    view(ctx, a, s['gauge_eye'], look=[s['gauge'][0] + 0.5, Y + 0.5, s['gauge'][2] + 0.5])
    ticks, reads, first, zero_reads, misses = 0, 0, None, 0, 0
    while ticks < limit_ticks:
        hit, text, nonzero = gauge_text(ctx, a, s)
        reads += 1
        if not hit or text is None:
            misses += 1
        elif nonzero:
            first = dict(text=text, wall_s=round(time.time() - t0, 2), game_ticks=ctx.server()['game_time'] - g0, client_ticks=ticks)
            break
        else:
            zero_reads += 1
        r = ctx.step('wait', client=a, ticks=2)
        ticks += r.get('ticks', 2) or 2
    return dict(baseline=base, unloaded=w, reads=reads, zero_reads=zero_reads, no_text_or_other_block=misses, first_nonzero=first,
                gave_up_after_client_ticks=None if first else ticks)


# ---------------------------------------------------------------- breaking a wire end next to an unloaded chunk

def break_test(ctx, a, s):
    B = s['brk']
    out = {}
    cmd(ctx, 'forceload add %d %d' % B['force'])
    ctx.step('wait', client=a, ticks=60)
    state = {k: _lib.chunk_full(ctx, B[k]) for k in ('p1', 'p2', 'q1', 'q2')}
    out['state'] = state
    mark = Z.log_mark()
    for near, far in (('p1', 'p2'), ('q1', 'q2')):
        before = _lib.tick_state(ctx)
        t = time.time()
        reply = Z.rcon1(ctx, 'setblock %d %d %d minecraft:air destroy' % B[near])
        took = round((time.time() - t) * 1000)
        after_full = _lib.chunk_full(ctx, B[far])
        ctx.step('wait', client=a, ticks=40)
        out[near] = dict(reply=reply[:120], rcon_ms=took, tick_before=before, tick_after=_lib.tick_state(ctx), far_full_right_after=after_full)
    for far in ('p2', 'q2'):
        cmd(ctx, 'forceload add %d %d' % (B[far][0], B[far][2]))
    ctx.step('wait', client=a, ticks=40)
    out['p2_cons'] = cons(data(ctx, B['p2']))
    out['q2_cons'] = cons(data(ctx, B['q2']))
    cmd(ctx, 'forceload remove all')
    lines, _ = Z.log_lines(mark)
    client_lines, other = Z.bad_log_lines(lines)
    out['errors'] = other[:5] + client_lines[:3]
    out['cant_keep_up'] = [ln[:160] for ln in lines if "Can't keep up" in ln][:3]
    return out


# ---------------------------------------------------------------- the scenario

def pre_run(ctx, a, b, s):
    view(ctx, a, s['spot_a'])
    view(ctx, b, s['line']['spot_b'])
    ctx.step('wait', client=a, ticks=40)
    run_for(ctx, a, PRE_RUN)


def come_back(ctx, a, b, s):
    view(ctx, a, s['spot_a'])
    view(ctx, b, s['line']['spot_b'])
    return _lib.wait_full(ctx, a, cluster_probes(s) + line_probes(s))


def leave(ctx, who, names, probes, settle=40):
    """From a frozen world: `names` fly to the parking spot, `settle` client ticks frozen (the scenes drop out of block-ticking range),
    then the world runs until no probe is at full status (_lib.wait_unloaded) and is frozen again (see the docstring: a frozen world
    keeps the readings' UNKNOWN tickets). Returns wait_unloaded's record."""
    _lib.park(ctx, names)
    ctx.step('wait', client=who, ticks=settle)
    ctx.server('tick unfreeze')
    try:
        return _lib.wait_unloaded(ctx, who, probes)
    finally:
        ctx.server('tick freeze')


def wait_moving(ctx, who, s, count, tries=10):
    """Entities load with their chunk's entity section, which can come a little after the blocks: polls the moving items on the ring
    until there are `count` of them (at most `tries` x 20 client ticks). Returns the counts seen."""
    seen = []
    for _ in range(tries):
        n = Z.entity_count(ctx, ring_selector(s))
        seen.append(n)
        if n == count:
            break
        ctx.step('wait', client=who, ticks=20)
    return seen


def check_cells(ctx, prefix, cmp, before, after, extra=''):
    ids = dict(power=PT, fluid=FP, belts=CV, rbmk=RX, line=PT)
    for name in ('power', 'fluid', 'belts', 'rbmk', 'line'):
        c = cmp[name]
        ctx.check(ids[name] + '%s-%s' % (prefix, name), c['ok'], '%s%s' % (extra, cell_detail(c)))


def run(ctx):
    a, b = list(ctx.channels)
    log0 = _lib.log_counts()
    Z.setup_world(ctx, a, b)
    s = layout(*ORIGIN)
    rec = build_all(ctx, a, s, break_pairs=True)
    pre_run(ctx, a, b, s)
    before = read_all(ctx, s)

    # radiation: A sets chunk T and reads it, then both leave at once (the saved value is read in radiation_unload below)
    prefix = geiger_prefix(ctx, a)
    rad_set = set_radiation(ctx, a, s)
    g0 = geiger(ctx, a, prefix)
    away = leave(ctx, a, [a, b], cluster_probes(s) + line_probes(s))
    ctx.check(NA + 'mp-unload-unloaded', away['ok'], 'build %s; %s' % (rec, away))
    if not away['ok']:
        raise RuntimeError('the scenes did not unload: %s' % away)
    saved_m, stamp_m = saved_radiation(s)

    # back: A first into chunk T for the Geiger reading, B to the line
    to_rad_spot(ctx, a, s)
    _lib.wait_full(ctx, a, [tuple(int(c) for c in s['rad_spot'])])
    g1 = geiger(ctx, a, prefix)
    back = come_back(ctx, a, b, s)
    back['moving'] = wait_moving(ctx, a, s, before['belts']['moving.count'])
    _lib.still(ctx)
    after = read_all(ctx, s)
    cmp = compare_cells(before, after)
    check_cells(ctx, 'mp-unload', cmp, before, after, extra='back at full status %s; ' % back)
    ctx.check(HZ + 'mp-unload-radiation', g1[0] is not None and g1[0] > 0, 'Geiger before leaving %s, first reading after coming back %s (%r); '
              'region file after that unload %s (save time %s)' % (g0[0], g1[0], g1[1], saved_m, stamp_m))

    ok, parts, detail = resume(ctx, a, s)
    ctx.check(NA + 'mp-unload-resume', ok, '%s; %s' % (parts, detail))

    ru = radiation_unload(ctx, a, b, s)
    if ru['decisive']:
        ctx.check(HZ + 'mp-unload-radiation-saved', ru['saved_after'] is not None and ru['saved_after'] > 0, str(ru))
    else:
        # the unload did not have to write T (no periodic save after the set, or the unload came outside the save cooldown)
        ctx.not_run(HZ + 'mp-unload-radiation-saved', 'the sequence was not decisive: %s' % ru)

    # the long line with its middle unloaded (nodes kept since the unload)
    leave(ctx, a, [a, b], line_probes(s) + cluster_probes(s))
    d1 = line_delivery(ctx, a, b, s, 'walk-away')
    ctx.check(NA + 'mp-unload-line-delivers', rec['line']['ok'] and d1['middle_unloaded'] and d1['ends_loaded'] and bool(d1['power']) and bool(d1['water']),
              'line built %s; %s' % (rec['line'], d1['detail']))

    g = gauge_zero_time(ctx, a, b, s)
    ctx.review(PT + 'mp-unload-gauge-zero', 'power gauge after its chunk reloaded in the running world: %s' % g)

    _lib.park(ctx, [a, b])
    bt = break_test(ctx, a, s)
    B = s['brk']
    st = bt['state']
    layout_ok = rec['break_pairs']['ok'] and st['p1'] and st['q1'] and not st['p2'] and not st['q2']
    ctx.check(PT + 'mp-unload-break-pylon', layout_ok and B['p1'] not in bt['p2_cons'] and not bt['errors'],
              'pairs wired %s; full status before (p1, p2, q1, q2) %s; pylon %s broken: %s; other end %s records afterwards %s; error lines %s; '
              'slow-tick lines %s' % (rec['break_pairs'], st, B['p1'], bt['p1'], B['p2'], bt['p2_cons'], bt['errors'], bt['cant_keep_up']))
    ctx.check(FP + 'mp-unload-break-anchor', layout_ok and B['q1'] not in bt['q2_cons'] and not bt['errors'],
              'anchor %s broken: %s; other end %s records afterwards %s; error lines %s' % (B['q1'], bt['q1'], B['q2'], bt['q2_cons'], bt['errors']))

    # a real source in chunk P: placed, read, walked away from until P unloads, read in the region file, come back to
    po_unload_check(ctx, po_unload(ctx, a, b, s, prefix))

    errs = _lib.server_log_errors(since=log0)
    ctx.check(PT + 'mp-unload-log', errs['errors'] == 0, str(errs))
    view(ctx, a, s['spot_a'])
    view(ctx, b, s['spot_a'])
    _lib.server_idle(ctx, a)
