"""Dedicated server: two players operate one RT generator at the same time.

A places the generator by hand; both open its screen. One plutonium-238 RTG pellet is given to A by command.

Expected (original 1.7.10 TileEntityMachineRTG / NEO MachineRTGBlockEntity):
- every tick heat = the summed heat of the pellets (pellet_rtg: 10, original ModItems.java:2655, NEO NtmItems.java:538;
  RTGUtil.updateRTGs) and power += heat x 5, capped at 100,000 (original TileEntityMachineRTG.java:100-108; NEO
  MachineRTGBlockEntity.java:71-75). In a frozen world `tick step 20` with one pellet gives heat 10 and power 20 x 50 = 1,000;
  without a pellet heat 0 and the power stays (nothing draws it).
- each player opens the screen for himself on the server (original MachineRTG.java:56-67; NEO MachineRTGBlock.java:43-51), so
  two players have it open at the same time.
- the screen shows the pellets through the menu and the heat and power bars from the synced block entity (original
  ContainerMachineRTG / GUIMachineRTG; NEO MachineRTGMenu, MachineRTGBlockEntity.serialize :151-164), so the other player's screen
  follows a change.
- a click in a container screen is handled on the server one after the other: two players taking the same pellet at once get
  one pellet between them.
- breaking the generator drops its pellets once (original MachineRTG.breakBlock :77-125; NEO MachineRTGBlock.onRemove :54-58)
  and closes every open screen of it (the menu's stillValid fails once the block is gone).
"""
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

_spec = importlib.util.spec_from_file_location('zirnox_mp_rig', Path(__file__).resolve().parents[1] / 'zirnox-reactor' / 'mp_meltdown.py')
Z = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(Z)

SCENARIO = dict(
    id='rtg-power.mp_rtg',
    feature='rtg-power',
    title='Dedicated server: two players at one RT generator (slots, bars, simultaneous take, breaking)',
    group='mp',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

G = Z.G
H = Z.H
SITE = (-40, 40)
PELLET = H + 'pellet_rtg'
STEP = 20
RT = 'rtg-power.'
EXPECT = [
    ('mp-rtg-both-open', '专服：两人同时打开同一台手放的 RT 发电机的界面（两个客户端同时右键，A 在南面、B 在北面，各开各的）：'
     '随后同时读两个客户端，A 与 B 的发电机界面都开着，后开的一方没有把先开的一方的界面挤掉',
     'MachineRTG.java:56-67; MachineRTGBlock.java:43-51'),
    ('mp-rtg-sync', '专服：两人同时打开同一台手放的 RT 发电机的界面；A 放入一个钚 238 RTG 粒（不在主线阶段清单里，用命令发给 A，预写），冻结世界走 20 刻：'
     '服务端热量 10、电量 1,000，B 的界面第 1 格是这个粒，B 客户端的热量与电量（同步的方块实体）也是 10 与 1,000；A 取出粒，再走 20 刻：'
     '服务端热量 0、电量仍 1,000，B 的第 1 格空了，B 的读数 0 与 1,000',
     'TileEntityMachineRTG.java:100-108; MachineRTGBlockEntity.java:71-75,151-164'),
    ('mp-rtg-simultaneous-take', '专服：粒放回、B 的界面里看到它之后，两人同时 Shift 点它：发电机里没有了，两人一共只有 1 个粒',
     'container clicks on the server thread; MachineRTGMenu'),
    ('mp-rtg-break', '专服：粒放回后 B 开着界面、A 破坏发电机：B 的界面关闭，地上只掉 1 个粒，两人背包里没有粒',
     'MachineRTG.java:77-125; MachineRTGBlock.java:54-58'),
    ('mp-rtg-restart', '专服重启后（静止、非默认的服务端读数，粒在玩家背包里，发电机不再升电）：发电机的电量与两人背包里的粒数与重启前相同',
     'MachineRTGBlockEntity.java:138-149, player save'),
]


def expectations():
    return [dict(id=RT + k, text=t, source=s) for k, t, s in EXPECT]


def pellets(ctx, name):
    return Z.inventory(ctx, name).get(PELLET, 0)


def slot_of(ctx, name):
    """Inventory slot of the pellet (server data), or None."""
    r = Z.rcon1(ctx, 'data get entity %s Inventory' % name)
    try:
        value = _lib.data_value(r)
    except Exception:  # noqa: BLE001
        return None
    for e in value if isinstance(value, list) else []:
        if e.get('id') == PELLET and 0 <= e.get('Slot', -1) <= 35:
            return e['Slot']
    return None


def client_bars(ctx, who, pos):
    d = ctx.step('dump', client=who, **{'from': list(pos)})
    nbt = _lib.parse_snbt(d['blocks'][0]['nbt']) if d['blocks'] and d['blocks'][0].get('nbt') else {}
    return nbt.get('heat'), nbt.get('power')


def b_slot0(ctx, who):
    return ctx.step('hover', client=who, slot=0, frames=3).get('item')


def put_in(ctx, who):
    s = slot_of(ctx, who)
    if s is None:
        raise RuntimeError('%s holds no pellet' % who)
    Z.shift_click(ctx, who, _lib.menu_slot(15, s))


def run(ctx):
    a, b = list(ctx.channels)
    Z.setup_world(ctx, a, b)
    x, z = SITE
    Z.hand(ctx, a, H + 'machine_rtg')
    ctx.step('view', client=a, pos=[x + 0.5, G, z + 3.5], look_at=[x + 0.5, G - 0.5, z + 0.5], fly=False, hide_gui=False)
    ctx.step('use', client=a, target=dict(pos=[x, G - 1, z], face='up'), after=8)
    ctx.rcon('item replace entity %s hotbar.0 with minecraft:air' % a)
    rtg = (x, G, z)
    placed = Z.block_is(ctx, rtg, H + 'machine_rtg')
    ctx.server('tick freeze')
    # both open the generator at the same time (two threads, one step channel per client), then both screens are read at once
    spec = {a: ('south', [x + 0.5, G, z + 2.5]), b: ('north', [x + 0.5, G, z - 1.5])}
    Z.both(ctx, lambda n: Z.open_screen(ctx, n, rtg, spec[n][0], spec[n][1], 'MachineRTGScreen'))
    open_now = Z.both(ctx, lambda n: ctx.step('screen', client=n, expect='MachineRTGScreen', allow_fail=True))
    ctx.check(RT + 'mp-rtg-both-open', placed and all(open_now[n]['status'] == 'ok' for n in (a, b)),
              'placed %s; opened by both clients at once; screens read together afterwards: A %s (%s), B %s (%s)'
              % (placed, open_now[a]['status'], open_now[a].get('screen') or open_now[a].get('reason'), open_now[b]['status'],
                 open_now[b].get('screen') or open_now[b].get('reason')))
    ctx.rcon('give %s %s 1' % (a, PELLET))
    ctx.step('wait', client=a, ticks=10)

    # A puts the pellet in; 20 ticks
    put_in(ctx, a)
    _lib.server_steps(ctx, STEP)
    ctx.step('wait', client=b, ticks=10)
    s1 = _lib.block_data(ctx, rtg)
    b1 = (b_slot0(ctx, b), client_bars(ctx, b, rtg))
    in1 = _lib.slot_count(s1, 0, PELLET)
    # A takes it out; 20 ticks
    Z.shift_click(ctx, a, 0)
    _lib.server_steps(ctx, STEP)
    ctx.step('wait', client=b, ticks=10)
    s2 = _lib.block_data(ctx, rtg)
    b2 = (b_slot0(ctx, b), client_bars(ctx, b, rtg))
    part1 = (placed and in1 == 1 and (s1.get('heat'), s1.get('power')) == (10, 1000) and b1 == (PELLET, (10, 1000))
             and _lib.slot_count(s2, 0) == 0 and (s2.get('heat'), s2.get('power')) == (0, 1000) and b2 == (None, (0, 1000)) and pellets(ctx, a) == 1)

    ctx.check(RT + 'mp-rtg-sync', part1,
              'placed %s; in: server slot %d, heat/power %s/%s; B sees slot %s, bars %s; out: server slot %d, heat/power %s/%s; B sees %s, %s; '
              'A holds %d pellet' % (placed, in1, s1.get('heat'), s1.get('power'), b1[0], b1[1], _lib.slot_count(s2, 0), s2.get('heat'),
                                     s2.get('power'), b2[0], b2[1], pellets(ctx, a)))

    # back in, then both take it at once
    put_in(ctx, a)
    ctx.step('wait', client=b, ticks=10)
    seen = b_slot0(ctx, b)
    Z.both(ctx, lambda n: Z.shift_click(ctx, n, 0))
    ctx.step('wait', client=a, ticks=10)
    s3 = _lib.block_data(ctx, rtg)
    got = {n: pellets(ctx, n) for n in (a, b)}
    part2 = seen == PELLET and _lib.slot_count(s3, 0) == 0 and sum(got.values()) == 1

    ctx.check(RT + 'mp-rtg-simultaneous-take', part2,
              'B saw %s before; after both clicked: generator slot %d, pellets per player %s' % (seen, _lib.slot_count(s3, 0), got))

    # restart with the pellet in a player's inventory: nothing in the generator changes
    pre = dict(power=s3.get('power'), a=got[a], b=got[b])
    for who in (a, b):
        ctx.step('close', client=who)
    _lib.server_idle(ctx, a)
    ctx.restart_server()
    ctx.server('tick freeze')
    ctx.step('wait', client=a, ticks=80)
    post = dict(power=_lib.block_data(ctx, rtg).get('power'), a=pellets(ctx, a), b=pellets(ctx, b))
    cmp = _lib.compare_static(pre, post)
    ctx.check(RT + 'mp-rtg-restart', cmp['ok'], 'before %s, after %s; %s' % (pre, post, cmp['detail']))

    # both open again; whoever holds the pellet puts it in; A breaks the generator while B's screen is open
    holder = a if pellets(ctx, a) else b
    Z.open_screen(ctx, holder, rtg, 'south' if holder == a else 'north', [x + 0.5, G, z + (2.5 if holder == a else -1.5)], 'MachineRTGScreen')
    put_in(ctx, holder)
    ctx.step('close', client=holder)
    Z.open_screen(ctx, b, rtg, 'north', [x + 0.5, G, z - 1.5], 'MachineRTGScreen')
    in4 = _lib.slot_count(_lib.block_data(ctx, rtg), 0, PELLET)
    ctx.step('key', client=a, key='key.keyboard.9', action='tap', after=2)
    ctx.step('view', client=a, pos=[x + 0.5, G, z + 2.5], look_at=_lib.face_point(rtg, 'south'), fly=False, hide_gui=False)
    hit = ctx.step('attack', client=a, target=dict(pos=list(rtg), face='south'), after=6)
    ctx.step('wait', client=b, ticks=10)
    gone = Z.block_is(ctx, rtg, 'minecraft:air')
    b_screen = ctx.step('screen', client=b, expect='none', allow_fail=True)
    drops = Z.entity_count(ctx, '@e[type=minecraft:item,nbt={Item:{id:"%s"}}]' % PELLET)
    held = {n: pellets(ctx, n) for n in (a, b)}
    part3 = in4 == 1 and gone and b_screen['status'] == 'ok' and drops == 1 and sum(held.values()) == 0
    ctx.check(RT + 'mp-rtg-break', part3,
              'pellet in %d; A attack hit %s; block gone %s; B screen closed %s (%s); pellet item entities %d; pellets per player %s'
              % (in4, hit.get('hit'), gone, b_screen['status'] == 'ok', b_screen.get('reason'), drops, held))
    ctx.rcon('kill @e[type=minecraft:item]')
    _lib.server_idle(ctx, a)
