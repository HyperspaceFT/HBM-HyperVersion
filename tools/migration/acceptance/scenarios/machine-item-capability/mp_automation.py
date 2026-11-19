"""Dedicated server: one automation pass on each machine whose item rules changed, both clients' view of the result, a restart.

Every machine is placed by hand by player A; hoppers, machine arms (crane inserter / extractor) and the stone they stand on are set
by command. A machine arm or a hopper is filled by A through its screen (shift-click) unless it sits where no player reaches it,
then its items are put in by command (预写). Readings come from the server's block data; the clients' view is each machine's
own screen, read slot by slot with a middle click in survival (a middle click changes nothing there: AbstractContainerMenu CLONE
needs infinite materials).

Rules (original 1.7.10 / NEO; NEO's SidedInvWrapper asks getSlotsForFace, canPlaceItemThroughFace and canTakeItemThroughFace,
CommonEvents.java:152-170; vanilla hoppers ask the same through WorldlyContainer; a multiblock proxy with an inventory passes them to
the core, ProxyComboBlockEntity.java:358-397):
- barrel and fluid tank: every face reaches 2-5; slot 2 takes a container holding the tank's fluid within capacity, slot 4 an
  empty container the tank's fluid fills; only 3 and 5 can be taken; the tank empties slot 2 into 3 and fills 4 into 5 every tick
  (original TileEntityBarrel.java:109-111,139-164, TileEntityMachineFluidTank extends it; NEO BarrelBlockEntity.java:66-70,
  217-251, MachineFluidTankBlockEntity.java:137,178,440-471);
- blast furnace: an input slot refuses an item equal to the other input slot's content, otherwise takes a recipe input; faces
  reach 1, 2, 0, 3, 4 (original TileEntityMachineBlastFurnace.java:221-258; NEO MachineBlastFurnaceBlockEntity.java:203-225);
- wood burner: faces reach 0 and 1 only; 0 takes fuel; only 1 (ash) can be taken; a log burns 300 x 4 = 1,200 ticks and the
  first fuel item is taken even while the burner is off (original TileEntityMachineWoodBurner.java:49,94-115,247-260; NEO
  MachineWoodBurnerBlockEntity.java:53-55,118-138,284-303);
- satellite linker: faces reach 1 only; a chip goes in; a chip in 1 gets the frequency of the chip in 0; taking needs both
  frequencies equal; a chip in 2 gets a random frequency below 10,000,000 (original TileEntityMachineSatLinker.java:20,31-61; NEO
  MachineSatLinkerBlockEntity.java:20,31-62);
- tungsten crate: no taking of polonium billets or smeltable items (original TileEntityCrateTungsten.java:62-76; NEO
  CrateTungstenBlockEntity.java:22-27);
- launch pads: faces reach 0; it takes a launchable missile; nothing can be taken (original TileEntityLaunchPadBase.java:134-146,314-316;
  NEO LaunchPadBaseBlockEntity.java:125-143,300-302);
- Soyuz launcher and heat exchanging heater: no slot is reachable (original TileEntityMachineBase.java:127-140, not overridden by
  TileEntitySoyuzLauncher or TileEntityHeaterHeatex; NEO SoyuzLauncherBlockEntity.java:374-388, HeaterHeatexBlockEntity.java:
  186-190).
"""
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402
import common  # noqa: E402

_spec = importlib.util.spec_from_file_location('zirnox_mp_rig', Path(__file__).resolve().parents[1] / 'zirnox-reactor' / 'mp_meltdown.py')
Z = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(Z)

SCENARIO = dict(
    id='machine-item-capability.mp_automation',
    feature='machine-item-capability',
    title='Dedicated server: automation pass on the machines whose item rules changed, both clients, restart',
    group='mp',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

G = _lib.FLAT_FEET
H = _lib.H
MI = 'machine-item-capability.'
BARREL = (20, 40)
TANK = (34, 40)
FURNACE = (52, 40)
BURNER = (68, 40)
LINKER = (20, 60)
CRATE = (32, 60)
PAD = (48, 60)
PAD_LARGE = (66, 62)
HEATEX = (20, 82)
SOYUZ = (60, 102)
PARK = (4.5, 8.5)                 # x where reader A / B waits while the other one reads (z 25.5)
HOPPER, INSERTER, EXTRACTOR = 'minecraft:hopper', H + 'crane_inserter', H + 'crane_extractor'
CHIP, IDENT, MISSILE = H + 'sat_chip', H + 'fluid_identifier_multi', H + 'missile_generic'

EXPECT = [
    ('mp-barrel', '钢桶（手放，罐的流体类型用命令写成水：预写）：上方漏斗（A 经界面放入水桶、空桶、石头）往下送，下方漏斗往外抽：水桶进 2 号倒进罐、空桶落到 3 号，'
     '空桶进 4 号灌满落到 5 号，3、5 号被下方漏斗抽走；石头留在上方漏斗。结果罐量 0、桶的槽全空、下方漏斗 1 个空桶 1 个水桶、上方漏斗 1 个石头，物品总数 3 不变',
     'TileEntityBarrel.java:109-111,139-164; BarrelBlockEntity.java:66-70,217-251'),
    ('mp-fluid-tank', '储罐（手放，流体类型写成水：预写）：核心底下的机械臂（命令放入水桶、空桶、石头：预写）往上送：罐量 0、3 号 1 个空桶、5 号 1 个水桶，石头留在机械臂；'
     '再把机械臂换成漏斗：3、5 号被抽空，漏斗里 1 个空桶 1 个水桶',
     'TileEntityMachineFluidTank extends TileEntityBarrel, TileEntityBarrel.java:109-111,139-164; MachineFluidTankBlockEntity.java:137,178,440-471'),
    ('mp-blast-furnace', '高炉：A 手放 64 个铁锭进 1 号；东侧接口外的机械臂（A 经界面放入 8 个铁锭、8 个沙子）：铁锭不进 2 号（1 号已有同种）、1 号已满，留在机械臂；'
     '沙子进 2 号。结果 1 号 64 铁锭、2 号 8 沙子、机械臂 8 铁锭',
     'TileEntityMachineBlastFurnace.java:221-258; MachineBlastFurnaceBlockEntity.java:203-225'),
    ('mp-wood-burner', '烧木发电机（关着）：机械臂（A 经界面放入 4 个原木、1 个多用流体标识符）：原木进 0 号，第一根立即被取走烧（燃烧时间 300×4=1,200），0 号剩 3；'
     '标识符留在机械臂（各面只开放 0、1 号）；1 号放 1 个木灰（命令：预写），核心下的漏斗只抽走木灰，0 号的 3 根原木不动',
     'TileEntityMachineWoodBurner.java:49,94-115,247-260; MachineWoodBurnerBlockEntity.java:53-55,118-138,284-303'),
    ('mp-sat-linker', '卫星链接器：A 手放芯片进 2 号得到随机频率 F（0 < F < 10,000,000），再手放进 0 号；机械臂（A 经界面放入第二个芯片与石头）：芯片进 1 号、频率被改成 F，'
     '两槽频率相同，下方漏斗把它抽走；石头留在机械臂。结果 0 号是频率 F 的芯片、1 号空、漏斗里 1 个频率 F 的芯片',
     'TileEntityMachineSatLinker.java:20,31-61; MachineSatLinkerBlockEntity.java:20,31-62'),
    ('mp-crate-tungsten', '钨板条箱：上方漏斗（A 经界面放入 4 个粗铁、4 个泥土）全部送进箱子；下方漏斗只抽走不能熔炼的泥土 4 个，能熔炼的粗铁 4 个留在箱里',
     'TileEntityCrateTungsten.java:62-76; CrateTungstenBlockEntity.java:22-27'),
    ('mp-launch-pad', '小型发射台：角上接口外的机械臂（A 经界面放入 1 枚通用导弹、1 个石头）：导弹进 0 号，石头留在机械臂；另一角接口下的漏斗抽不出导弹',
     'TileEntityLaunchPadBase.java:134-146,314-316; LaunchPadBaseBlockEntity.java:125-143,300-302'),
    ('mp-launch-pad-large', '大型发射台：接口外的机械臂（A 经界面放入 1 枚通用导弹、1 个石头）：导弹进 0 号，石头留在机械臂；另一接口下的漏斗抽不出导弹',
     'TileEntityLaunchPadBase.java:134-146,314-316; LaunchPadBaseBlockEntity.java:125-143,300-302'),
    ('mp-soyuz', '联盟号发射台：核心顶上的机械臂（A 经界面放入 1 个石头）放不进去，核心各槽仍空；1 号槽放 1 个卫星芯片（命令：预写），核心顶上换成提取器：什么也取不出，芯片仍在 1 号',
     'TileEntityMachineBase.java:127-140; SoyuzLauncherBlockEntity.java:374-388'),
    ('mp-heatex', '热交换加热器：A 手放 1 个多用流体标识符进 0 号；核心上方漏斗（A 经界面放入标识符与石头）放不进去，两件都留在漏斗；核心下方漏斗抽不出 0 号的标识符',
     'TileEntityMachineBase.java:127-140; HeaterHeatexBlockEntity.java:182-190'),
    ('mp-clients-same', '两个客户端（生存模式下中键读各机器自己的界面）看到的上述各机器读的槽的物品与数量相同，并与服务端的方块数据相同',
     'AbstractContainerMenu CLONE; NEO menus'),
    ('mp-restart', '专服重启后比对静止的服务端读数：上面各机器与漏斗、机械臂里的物品与数量、罐量、烧木发电机的燃烧时间，与重启前相同',
     'block entity save/load of each machine'),
]


def expectations():
    return [dict(id=MI + k, text=t, source=s) for k, t, s in EXPECT]


# ---------------------------------------------------------------- helpers (dedicated server, explicit client)

def items(ctx, pos):
    """{slot: (id, count)} of a block entity's items, server data."""
    data = _lib.block_data(ctx, pos)
    return {e.get('Slot'): (e.get('id'), e.get('count', 1)) for e in data.get('Items', [])}


def total(content, item=None):
    return sum(c for i, c in content.values() if item is None or i == item)


def inv_slot(ctx, who, item):
    inv = _lib.inventory(ctx, who)
    return _lib.find_slot(inv, item)


def give(ctx, who, *pairs):
    for item, n in pairs:
        ctx.rcon('give %s %s %d' % (who, item, n))
    ctx.step('wait', client=who, ticks=4)


def click(ctx, who, slot, button=0, after=2):
    return ctx.step('click', client=who, slot=slot, button=button, after=after)


def load(ctx, who, n, item_ids):
    """Shift-clicks each item's stack from the open screen's player inventory into the container (n machine slots)."""
    for item in item_ids:
        s = inv_slot(ctx, who, item)
        if s is None:
            raise RuntimeError('%s has no %s' % (who, item))
        Z.shift_click(ctx, who, _lib.menu_slot(n, s))


def put(ctx, who, n, item, dst):
    """Picks up the first stack of `item` and puts it whole into machine slot dst of the open screen."""
    s = inv_slot(ctx, who, item)
    if s is None:
        raise RuntimeError('%s has no %s' % (who, item))
    click(ctx, who, _lib.menu_slot(n, s))
    r = click(ctx, who, dst)
    if (r.get('after') or {}).get('carried_count'):
        click(ctx, who, _lib.menu_slot(n, s))


def opener(pos, face='south', stand=None, expect=''):
    """How to open a block's screen: the face clicked, where the player stands, the screen class expected. A side face is aimed at
    0.45 block inside the cell, since a multiblock edge cell can be narrower than the cell (LaunchPadLargeBlock.java:27-29)."""
    stand = stand or [pos[0] + 0.5, G, pos[2] + (2.5 if face == 'south' else -1.5)]
    v = _lib.VEC[face]
    offset = [0.0, 0.0, 0.0] if face in ('up', 'down') else [-0.45 * v[0], 0.0, -0.45 * v[2]]
    return dict(pos=pos, face=face, stand=stand, expect=expect, offset=offset)


def open_(ctx, who, o):
    """Empty hand (hotbar slot 9), right-click aimed at the face point plus the offset, wait for the screen; returns a hud read."""
    ctx.step('key', client=who, key='key.keyboard.9', action='tap', after=2)
    look = [c + d for c, d in zip(_lib.face_point(o['pos'], o['face']), o['offset'])]
    ctx.step('view', client=who, pos=list(o['stand']), look_at=look, fly=True, hide_gui=False)
    target = dict(pos=list(o['pos']), face=o['face'])
    if any(o['offset']):
        target['offset'] = list(o['offset'])
    ctx.step('use', client=who, target=target, any_hit=True, after=6)
    ctx.step('screen', client=who, expect=o['expect'])
    return ctx.step('hud', client=who, frames=2)


def cells_of(ctx, who, block, lo, hi):
    d = ctx.step('dump', client=who, **{'from': list(lo), 'to': list(hi)})
    return {tuple(int(c) for c in b['pos']): b['props'].get('type', 'core') for b in d['blocks'] if b['block'] == block}


def south_cell(cells, y=G):
    """The multiblock cell at height y furthest south (then nearest the middle): its south face is open to a player standing there."""
    row = [p for p in cells if p[1] == y]
    zmax = max(p[2] for p in row)
    xs = sorted((p for p in row if p[2] == zmax), key=lambda p: p[0])
    return xs[len(xs) // 2]


def exposed(cells, cell):
    """A horizontal direction whose neighbour of `cell` is not part of the multiblock."""
    for d in ('east', 'west', 'north', 'south'):
        v = _lib.VEC[d]
        if (cell[0] + v[0], cell[1], cell[2] + v[2]) not in cells:
            return d
    return None


def setblock(ctx, pos, spec):
    r = Z.rcon1(ctx, 'setblock %d %d %d %s' % (pos[0], pos[1], pos[2], spec))
    if 'Changed' not in r and 'changed' not in r:
        raise RuntimeError('setblock %s at %s: %s' % (spec, pos, r))


def crane(kind, out):
    """A crane block state with its output (inserter: where it puts; extractor: where it takes from) towards `out`."""
    return '%s[input=%s,output=%s]' % (kind, _lib.opposite(out), out)


def clear_block(ctx, pos, n):
    for i in range(n):
        ctx.rcon('item replace block %d %d %d container.%d with minecraft:air' % (pos[0], pos[1], pos[2], i))


def custom_data(ctx, pos, slot):
    it = _lib.slot_item(_lib.block_data(ctx, pos), slot)
    return None if it is None else (it.get('id'), it.get('count', 1), (it.get('components') or {}).get('minecraft:custom_data'))


# ---------------------------------------------------------------- the passes

def run(ctx):
    a, b = list(ctx.channels)
    Z.setup_world(ctx, a, b)
    ctx.rcon('tick unfreeze')
    ctx.rcon('fill 10 %d 30 80 %d 115 minecraft:air' % (G, G + 12), 'kill @e[type=minecraft:item]')
    S = dict(views={}, snap={}, results={})

    def pause(t=40):
        ctx.step('wait', client=a, ticks=t)

    def barrel():
        x, z = BARREL
        pos = Z.place_by_hand(ctx, a, H + 'barrel_steel', x, z, H + 'barrel_steel', ((x, G, z), (x, G, z)))
        top, bottom = (x, G + 1, z), (x, G - 1, z)
        ctx.rcon('data merge block %d %d %d {tank_type:"WATER"}' % pos)  # 预写
        setblock(ctx, bottom, HOPPER + '[facing=north]')
        setblock(ctx, top, HOPPER + '[facing=down]')
        give(ctx, a, ('minecraft:water_bucket', 1), ('minecraft:bucket', 1), ('minecraft:stone', 1))
        open_(ctx, a, opener(top, expect='HopperScreen'))
        load(ctx, a, 5, ['minecraft:water_bucket', 'minecraft:bucket', 'minecraft:stone'])
        ctx.step('close', client=a)
        ctx.rcon('clear %s' % a)
        pause(120)
        data = _lib.block_data(ctx, pos)
        r = dict(tank=data.get('tank'), barrel=items(ctx, pos), top=items(ctx, top), bottom=items(ctx, bottom))
        ok = (r['tank'] == 0 and not r['barrel'] and sorted(r['top'].values()) == [('minecraft:stone', 1)]
              and sorted(r['bottom'].values()) == [('minecraft:bucket', 1), ('minecraft:water_bucket', 1)])
        ctx.check(MI + 'mp-barrel', ok, '预写 tank type water; %s' % r, ['rcon log'])
        S['views']['barrel'] = (opener(pos, expect='BarrelScreen'), pos, [2, 3, 4, 5])
        S['snap'].update(barrel_tank=r['tank'], barrel_top=r['top'], barrel_bottom=r['bottom'])

    def tank():
        x, z = TANK
        core = Z.place_by_hand(ctx, a, H + 'machine_fluid_tank', x, z, H + 'machine_fluid_tank', ((x - 4, G, z - 4), (x + 4, G + 3, z + 4)))
        cells = cells_of(ctx, a, H + 'machine_fluid_tank', (x - 4, G, z - 4), (x + 4, G + 3, z + 4))
        under = (core[0], G - 1, core[2])
        ctx.rcon('data merge block %d %d %d {Tank_type:"WATER"}' % core)  # 预写 (the tank block entity saves its tank as "Tank")
        setblock(ctx, under, crane(INSERTER, 'up'))
        for i, item in enumerate(('minecraft:water_bucket', 'minecraft:bucket', 'minecraft:stone')):  # 预写: nobody reaches this arm
            ctx.rcon('item replace block %d %d %d container.%d with %s 1' % (under + (i, item)))
        pause(60)
        data = _lib.block_data(ctx, core)
        first = dict(tank=data.get('Tank'), tank_type=data.get('Tank_type'), core=items(ctx, core), arm=items(ctx, under))
        clear_block(ctx, under, 21)
        setblock(ctx, under, HOPPER + '[facing=north]')
        pause(60)
        second = dict(core=items(ctx, core), hopper=items(ctx, under))
        ok = (first['tank'] == 0 and first['core'] == {3: ('minecraft:bucket', 1), 5: ('minecraft:water_bucket', 1)}
              and sorted(first['arm'].values()) == [('minecraft:stone', 1)]
              and not second['core'] and sorted(second['hopper'].values()) == [('minecraft:bucket', 1), ('minecraft:water_bucket', 1)])
        ctx.check(MI + 'mp-fluid-tank', ok, '预写 tank type and arm contents; core %s; after the arm pass %s; after the hopper %s'
                  % (core, first, second), ['rcon log'])
        S['views']['tank'] = (opener(south_cell(cells), expect='MachineFluidTankScreen'), core, [2, 3, 4, 5])
        S['snap'].update(tank_tank=first['tank'], tank_hopper=second['hopper'])

    def furnace():
        x, z = FURNACE
        core = Z.place_by_hand(ctx, a, H + 'machine_blast_furnace', x, z, H + 'machine_blast_furnace', ((x - 3, G, z - 3), (x + 3, G + 6, z + 3)))
        cells = cells_of(ctx, a, H + 'machine_blast_furnace', (x - 3, G, z - 3), (x + 3, G + 6, z + 3))
        port = (core[0] + 1, G, core[2])
        if cells.get(port) != 'extra':
            raise RuntimeError('no port east of the core: %s' % cells.get(port))
        arm = (core[0] + 2, G, core[2])
        view = opener(south_cell(cells), expect='MachineBlastFurnaceScreen')
        give(ctx, a, ('minecraft:iron_ingot', 72), ('minecraft:sand', 8))
        open_(ctx, a, view)
        put(ctx, a, 5, 'minecraft:iron_ingot', 1)
        ctx.step('close', client=a)
        setblock(ctx, arm, crane(INSERTER, 'west'))
        open_(ctx, a, opener(arm, face='up', stand=[arm[0] + 0.5, G, arm[2] + 2.5], expect='CraneInserterScreen'))
        load(ctx, a, 21, ['minecraft:iron_ingot', 'minecraft:sand'])
        ctx.step('close', client=a)
        ctx.rcon('clear %s' % a)
        pause(60)
        r = dict(core=items(ctx, core), arm=items(ctx, arm))
        ok = (r['core'] == {1: ('minecraft:iron_ingot', 64), 2: ('minecraft:sand', 8)} and sorted(r['arm'].values()) == [('minecraft:iron_ingot', 8)])
        ctx.check(MI + 'mp-blast-furnace', ok, 'core %s; %s' % (core, r), ['rcon log'])
        S['views']['furnace'] = (view, core, [1, 2])
        S['snap'].update(furnace_core=r['core'], furnace_arm=r['arm'])

    def burner():
        x, z = BURNER
        core = Z.place_by_hand(ctx, a, H + 'machine_wood_burner', x, z, H + 'machine_wood_burner', ((x - 2, G, z - 2), (x + 2, G + 1, z + 2)))
        cells = cells_of(ctx, a, H + 'machine_wood_burner', (x - 2, G, z - 2), (x + 2, G + 1, z + 2))
        side = exposed(cells, core)
        v = _lib.VEC[side]
        arm = (core[0] + v[0], G, core[2] + v[2])
        setblock(ctx, arm, crane(INSERTER, _lib.opposite(side)))
        give(ctx, a, ('minecraft:oak_log', 4), (IDENT, 1))
        open_(ctx, a, opener(arm, face='up', stand=[arm[0] + 0.5 + 2 * v[0], G, arm[2] + 0.5 + 2 * v[2]], expect='CraneInserterScreen'))
        load(ctx, a, 21, ['minecraft:oak_log', IDENT])
        ctx.step('close', client=a)
        ctx.rcon('clear %s' % a)
        pause(60)
        data = _lib.block_data(ctx, core)
        first = dict(core=items(ctx, core), arm=items(ctx, arm), burnTime=data.get('burnTime'), isOn=data.get('isOn'))
        under = (core[0], G - 1, core[2])
        ctx.rcon('item replace block %d %d %d container.1 with %spowder_ash_wood 1' % (core + (H,)))  # 预写
        setblock(ctx, under, HOPPER + '[facing=north]')
        pause(60)
        second = dict(core=items(ctx, core), hopper=items(ctx, under))
        ok = (first['core'] == {0: ('minecraft:oak_log', 3)} and first['burnTime'] == 1200 and first['isOn'] in (0, False)
              and sorted(first['arm'].values()) == [(IDENT, 1)]
              and second['core'] == {0: ('minecraft:oak_log', 3)} and sorted(second['hopper'].values()) == [(H + 'powder_ash_wood', 1)])
        ctx.check(MI + 'mp-wood-burner', ok, 'core %s, arm on the %s side; after the arm %s; 预写 ash, after the hopper %s' % (core, side, first, second),
                  ['rcon log'])
        S['views']['burner'] = (opener(south_cell(cells), expect='MachineWoodBurnerScreen'), core, [0, 1, 2])
        S['snap'].update(burner_core=second['core'], burner_burn=first['burnTime'], burner_hopper=second['hopper'], burner_arm=first['arm'])

    def linker():
        x, z = LINKER
        pos = Z.place_by_hand(ctx, a, H + 'machine_satlinker', x, z, H + 'machine_satlinker', ((x, G, z), (x, G, z)))
        under, arm = (x, G - 1, z), (x + 1, G, z)
        setblock(ctx, under, HOPPER + '[facing=north]')
        setblock(ctx, arm, crane(INSERTER, 'west'))
        give(ctx, a, (CHIP, 1))
        view = opener(pos, expect='MachineSatLinkerScreen')
        open_(ctx, a, view)
        put(ctx, a, 3, CHIP, 2)
        ctx.step('wait', client=a, ticks=6)
        click(ctx, a, 2)
        click(ctx, a, 0)
        ctx.step('close', client=a)
        f = _lib.block_data(ctx, pos)
        freq0 = (( _lib.slot_item(f, 0) or {}).get('components') or {}).get('minecraft:custom_data', {}).get('freq')
        give(ctx, a, (CHIP, 1), ('minecraft:stone', 1))
        open_(ctx, a, opener(arm, face='up', stand=[arm[0] + 0.5, G, arm[2] + 2.5], expect='CraneInserterScreen'))
        load(ctx, a, 21, [CHIP, 'minecraft:stone'])
        ctx.step('close', client=a)
        ctx.rcon('clear %s' % a)
        pause(60)
        r = dict(slot0=custom_data(ctx, pos, 0), slot1=custom_data(ctx, pos, 1), slot2=custom_data(ctx, pos, 2),
                 hopper=custom_data(ctx, under, 0), arm=items(ctx, arm))
        ok = (isinstance(freq0, int) and 0 < freq0 < 10_000_000 and r['slot0'] == (CHIP, 1, {'freq': freq0}) and r['slot1'] is None
              and r['slot2'] is None and r['hopper'] == (CHIP, 1, {'freq': freq0}) and sorted(r['arm'].values()) == [('minecraft:stone', 1)])
        ctx.check(MI + 'mp-sat-linker', ok, 'frequency from slot 2: %s; %s' % (freq0, r), ['rcon log'])
        S['views']['linker'] = (view, pos, [0, 1, 2])
        S['snap'].update(linker_slot0=r['slot0'], linker_hopper=r['hopper'])

    def crate():
        x, z = CRATE
        pos = Z.place_by_hand(ctx, a, H + 'crate_tungsten', x, z, H + 'crate_tungsten', ((x, G, z), (x, G, z)))
        top, bottom = (x, G + 1, z), (x, G - 1, z)
        setblock(ctx, bottom, HOPPER + '[facing=north]')
        setblock(ctx, top, HOPPER + '[facing=down]')
        give(ctx, a, ('minecraft:raw_iron', 4), ('minecraft:dirt', 4))
        open_(ctx, a, opener(top, expect='HopperScreen'))
        load(ctx, a, 5, ['minecraft:raw_iron', 'minecraft:dirt'])
        ctx.step('close', client=a)
        ctx.rcon('clear %s' % a)
        pause(200)
        r = dict(crate=items(ctx, pos), top=items(ctx, top), bottom=items(ctx, bottom))
        ok = (sorted(r['crate'].values()) == [('minecraft:raw_iron', 4)] and not r['top'] and sorted(r['bottom'].values()) == [('minecraft:dirt', 4)])
        ctx.check(MI + 'mp-crate-tungsten', ok, '%s' % r, ['rcon log'])
        S['views']['crate'] = (opener(pos, expect='CrateScreen'), pos, [0, 1])
        S['snap'].update(crate=r['crate'], crate_bottom=r['bottom'])

    def pad(name, eid, block, site, box, view_cls):
        # the pad is placed north of the clicked block (offset 1 small, 4 large; LaunchPadBlock.java:62, LaunchPadLargeBlock.java:72)
        x, z = site
        lo, hi = (x - box, G, z - 2 * box), (x + box, G, z + 1)
        core = Z.place_by_hand(ctx, a, block, x, z, block, (lo, hi))
        cells = cells_of(ctx, a, block, lo, hi)
        extras = sorted(p for p, t in cells.items() if t == 'extra')
        east = max(extras, key=lambda p: (p[0], p[2]))
        west = min(extras, key=lambda p: (p[0], p[2]))
        arm = (east[0] + 1, G, east[2])
        under = (west[0], G - 1, west[2])
        setblock(ctx, arm, crane(INSERTER, 'west'))
        setblock(ctx, under, HOPPER + '[facing=north]')
        give(ctx, a, (MISSILE, 1), ('minecraft:stone', 1))
        open_(ctx, a, opener(arm, face='up', stand=[arm[0] + 2.5, G, arm[2] + 0.5], expect='CraneInserterScreen'))
        load(ctx, a, 21, [MISSILE, 'minecraft:stone'])
        ctx.step('close', client=a)
        ctx.rcon('clear %s' % a)
        pause(80)
        r = dict(core=items(ctx, core), arm=items(ctx, arm), hopper=items(ctx, under))
        ok = r['core'] == {0: (MISSILE, 1)} and sorted(r['arm'].values()) == [('minecraft:stone', 1)] and not r['hopper']
        ctx.check(MI + eid, ok, 'core %s, arm at %s (into the port %s), hopper under the port %s; %s' % (core, arm, east, west, r), ['rcon log'])
        # the large pad's middle strip is only a thin top plate (LaunchPadLargeBlock.java:27-29), so its screen is opened two cells off it
        cell = south_cell(cells)
        if (cell[0] + 2, cell[1], cell[2]) in cells:
            cell = (cell[0] + 2, cell[1], cell[2])
        S['views'][name] = (opener(cell, expect=view_cls), core, [0])
        S['snap'].update(**{name + '_core': r['core'], name + '_arm': r['arm']})

    def heatex():
        x, z = HEATEX
        core = Z.place_by_hand(ctx, a, H + 'heater_heatex', x, z, H + 'heater_heatex', ((x - 2, G, z - 2), (x + 2, G, z + 2)))
        cells = cells_of(ctx, a, H + 'heater_heatex', (x - 2, G, z - 2), (x + 2, G, z + 2))
        top, bottom = (core[0], G + 1, core[2]), (core[0], G - 1, core[2])
        view = opener(south_cell(cells), expect='HeaterHeatexScreen')
        give(ctx, a, (IDENT, 1))
        open_(ctx, a, view)
        put(ctx, a, 1, IDENT, 0)
        ctx.step('close', client=a)
        setblock(ctx, bottom, HOPPER + '[facing=north]')
        setblock(ctx, top, HOPPER + '[facing=down]')
        give(ctx, a, (IDENT, 1), ('minecraft:stone', 1))
        open_(ctx, a, opener(top, face='east', stand=[top[0] + 2.5, G, top[2] + 0.5], expect='HopperScreen'))
        load(ctx, a, 5, [IDENT, 'minecraft:stone'])
        ctx.step('close', client=a)
        ctx.rcon('clear %s' % a)
        pause(80)
        r = dict(core=items(ctx, core), top=items(ctx, top), bottom=items(ctx, bottom))
        ok = (r['core'] == {0: (IDENT, 1)} and sorted(r['top'].values()) == sorted([(IDENT, 1), ('minecraft:stone', 1)]) and not r['bottom'])
        ctx.check(MI + 'mp-heatex', ok, 'core %s; %s' % (core, r), ['rcon log'])
        S['views']['heatex'] = (view, core, [0])
        S['snap'].update(heatex_core=r['core'], heatex_top=r['top'])

    def soyuz():
        x, z = SOYUZ
        lo, hi = (x - 10, G, z - 10), (x + 10, G + 6, z + 10)
        core = Z.place_by_hand(ctx, a, H + 'soyuz_launcher', x, z, H + 'soyuz_launcher', (lo, hi))
        cells = cells_of(ctx, a, H + 'soyuz_launcher', lo, hi)
        above = (core[0], core[1] + 1, core[2])
        if above in cells:
            raise RuntimeError('the cell above the Soyuz core %s is part of the launcher' % (core,))
        setblock(ctx, above, crane(INSERTER, 'down'))
        give(ctx, a, ('minecraft:stone', 1))
        open_(ctx, a, opener(above, face='up', stand=[above[0] + 0.5, above[1] + 1, above[2] + 2.5], expect='CraneInserterScreen'))
        load(ctx, a, 21, ['minecraft:stone'])
        ctx.step('close', client=a)
        ctx.rcon('clear %s' % a)
        pause(40)
        first = dict(core=items(ctx, core), arm=items(ctx, above))
        clear_block(ctx, above, 21)
        ctx.rcon('item replace block %d %d %d container.1 with %s 1' % (core + (CHIP,)))  # 预写
        setblock(ctx, above, crane(EXTRACTOR, 'down'))
        pause(80)
        second = dict(core=items(ctx, core), extractor=items(ctx, above))
        ok = (not first['core'] and sorted(first['arm'].values()) == [('minecraft:stone', 1)]
              and second['core'] == {1: (CHIP, 1)} and not second['extractor'])
        ctx.check(MI + 'mp-soyuz', ok, 'core %s; after the arm %s; 预写 chip, after the extractor %s' % (core, first, second), ['rcon log'])
        S['views']['soyuz'] = (opener(south_cell(cells), expect='SoyuzLauncherScreen'), core, [0, 1])
        S['snap'].update(soyuz_core=second['core'])

    rows = {
        'barrel': ['mp-barrel'], 'tank': ['mp-fluid-tank'], 'furnace': ['mp-blast-furnace'], 'burner': ['mp-wood-burner'],
        'linker': ['mp-sat-linker'], 'crate': ['mp-crate-tungsten'], 'pad': ['mp-launch-pad'], 'pad_large': ['mp-launch-pad-large'],
        'heatex': ['mp-heatex'], 'soyuz': ['mp-soyuz'],
    }
    bodies = dict(barrel=barrel, tank=tank, furnace=furnace, burner=burner, linker=linker, crate=crate,
                  pad=lambda: pad('pad', 'mp-launch-pad', H + 'launch_pad', PAD, 2, 'LaunchPad'),
                  pad_large=lambda: pad('pad_large', 'mp-launch-pad-large', H + 'launch_pad_large', PAD_LARGE, 5, 'LaunchPad'),
                  heatex=heatex, soyuz=soyuz)
    for name, body in bodies.items():
        ctx.rcon('tick unfreeze')  # a failed section freezes the world (_lib.section); hoppers and arms need it running
        _lib.section(ctx, [MI + r for r in rows[name]], body, name)
        ctx.rcon('clear %s' % a)
        ctx.step('close', client=a, allow_fail=True)

    # both clients read every machine's screen (survival: a middle click changes nothing)
    def read_all():
        ctx.rcon('gamemode survival %s' % a, 'gamemode survival %s' % b)
        seen, server, unread = {}, {}, {}
        for name, (o, core, slots) in S['views'].items():
            content = items(ctx, core)
            server[name] = {s: content.get(s, ('minecraft:air', 0)) for s in slots}
            for who in (a, b):
                try:
                    open_(ctx, who, o)
                    got = {}
                    for s in slots:
                        r = click(ctx, who, s, button=2)
                        bf = r.get('before') or {}
                        got[s] = (bf.get('slot_item'), bf.get('slot_count', 0) if bf.get('slot_item') != 'minecraft:air' else 0)
                    seen.setdefault(name, {})[who] = got
                except Exception as e:  # noqa: BLE001 - a screen that does not open leaves this machine unread, not the others
                    result = getattr(e, 'result', None) or {}
                    unread.setdefault(name, {})[who] = 'step %s (%s): %s' % (result.get('seq'), result.get('op'), result.get('reason') or repr(e)[:120])
                ctx.step('close', client=who, allow_fail=True)
                # out of the next reader's line of sight (a player in front of the block takes the click)
                ctx.step('view', client=who, pos=[PARK[who == b], G, 25.5], pitch=0.0, yaw=0.0, fly=False, hide_gui=False)
        ctx.rcon('gamemode creative %s' % a, 'gamemode creative %s' % b)
        norm = {n: {s: (i, c if i != 'minecraft:air' else 0) for s, (i, c) in v.items()} for n, v in server.items()}
        complete = {n: v for n, v in seen.items() if len(v) == 2}
        bad = {n: dict(server=norm[n], **v) for n, v in complete.items() if not all(v[w] == norm[n] for w in (a, b))}
        detail = 'machines read by both %s; differing %s; unread %s; all reads %s' % (sorted(complete), bad or 'none', unread or 'none', seen)
        if bad or not unread:
            ctx.check(MI + 'mp-clients-same', bool(complete) and not bad, detail, ['click steps (middle button)'])
        else:
            ctx.not_run(MI + 'mp-clients-same', 'the screens of %s did not open for the scripted click, so not every machine was read; %s'
                        % (sorted(unread), detail))
    _lib.section(ctx, [MI + 'mp-clients-same'], read_all, 'client reads')

    def restart():
        pre = restart_readings(ctx, S)
        ctx.step('close', client=b, allow_fail=True)
        _lib.reopen(ctx, who=a)
        _lib.server_idle(ctx, a)
        post = restart_readings(ctx, S)
        cmp = _lib.compare_static(pre, post)
        ctx.check(MI + 'mp-restart', cmp['ok'], 'before %s; after %s; %s' % (pre, post, cmp['detail']), ['rcon log'])
    _lib.section(ctx, [MI + 'mp-restart'], restart, 'restart')
    ctx.rcon('tick unfreeze')
    _lib.server_idle(ctx, a)


def restart_readings(ctx, S):
    """Static stored readings of every machine and buffer the passes left (server data)."""
    out = {}
    for name, (o, core, slots) in S['views'].items():
        data = _lib.block_data(ctx, core)
        out[name + '_items'] = sorted((e.get('Slot'), e.get('id'), e.get('count', 1)) for e in data.get('Items', []))
        for key in ('tank', 'Tank'):
            if key in data:
                out[name + '_tank'] = data[key]
        if name == 'burner':
            out['burner_burnTime'] = data.get('burnTime')
    return out
