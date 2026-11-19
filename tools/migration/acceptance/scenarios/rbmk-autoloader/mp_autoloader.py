"""Dedicated server: the RBMK autoloader loads a fuel channel on its own, and the irradiation channel (outgasser) makes tritium
that leaves through a duct; both players see the same values.

Rig (player A, by hand; items put in the hand by command), one row west to east at y = G:

    fuel channel + autoloader on top | fuel channel with the Ra-226/Be neutron source | irradiation channel -> duct -> steel barrel

The source rod and the lithium are given by command and shift-clicked into the channels' screens; the fresh natural uranium rod
is shift-clicked into the autoloader. The duct and the barrel above the irradiation channel are set by command; their fluid
type (tritium) is written by command (预写, the executor cannot type in the identifier's screen).

Expected (original 1.7.10 / NEO):
- the autoloader checks the channel below every 20 ticks (game time % 20 == 0) while it is not extending; with a rod of at least
  `cycle` % (50) in its slots and an empty channel below it starts in that tick and raises the piston by 0.005 a tick (original
  TileEntityRBMKAutoloader.java:53-173; NEO RBMKAutoloaderBlockEntity.java:67-142): in double arithmetic 200 additions of 0.005
  reach 1.0000000000000007, so the rod moves into the channel in the 200th tick counted from the starting tick, not earlier.
- the irradiation channel adds the neutron flux it receives to its progress and at 10,000 turns one lithium into 1,000 mB of
  tritium (original TileEntityRBMKOutgasser.java:38,69-129, OutgasserRecipes.java:36; NEO RBMKOutgasserBlockEntity.java:35,70-125,
  OutgasserRecipes.java:157), which it offers at the port above the column (NEO RBMKBaseBlockEntity.getPortConnections :524-530).
- the tank values reach the clients with the block entity packets (NEO RBMKOutgasserBlockEntity.serialize, barrel sync).
"""
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

_spec = importlib.util.spec_from_file_location('rbmk_mp_rig', Path(__file__).resolve().parents[1] / 'rbmk-reactor' / 'mp_meltdown.py')
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)
Z = R.Z

SCENARIO = dict(
    id='rbmk-autoloader.mp_autoloader',
    feature='rbmk-autoloader',
    features=['rbmk-autoloader', 'rbmk-outgasser'],
    title='Dedicated server: autoloader loads a channel by itself, irradiation channel makes tritium through a duct, both clients agree',
    group='mp',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

G = Z.G
H = Z.H
SITE = (-60, 60)
LAYOUT = [['rbmk_rod', 'rbmk_rod', 'rbmk_outgasser']]
TRITIUM_ID = 9                # the numeric id of Fluids.TRITIUM
EXTEND = 200                  # ticks from the starting tick to the swap

EXPECT = [
    ('rbmk-autoloader.mp-autoloader-swap', '专服：装料机装着 1 根新的天然铀 RBMK 燃料棒（命令发放）、下方燃料通道空着；冻结世界走到'
     '游戏时间 ≡ 0 (mod 20) 的那一刻装料机开始下行，从那一刻算起第 199 刻燃料通道仍空、活塞 0.995，第 200 刻燃料棒进入通道、装料机的格子空了',
     'TileEntityRBMKAutoloader.java:53-173; RBMKAutoloaderBlockEntity.java:67-142'),
    ('rbmk-outgasser.mp-outgasser-tritium', '专服：辐照通道（旁边是镭-226/铍中子源，命令发放）把 1 个锂（不在主线阶段清单里，用命令发给 A，预写）变成 '
     '1,000 mB 氚，经管道进入钢桶（管道与桶用命令放下，命令搭建；两者的流体类型用命令写成氚，预写）：冲刺到桶里有 1,000 mB 为止，服务端的桶里是 1,000 mB 氚',
     'TileEntityRBMKOutgasser.java:38,69-129, OutgasserRecipes.java:36; RBMKOutgasserBlockEntity.java:35,70-125, OutgasserRecipes.java:157'),
    ('rbmk-outgasser.mp-outgasser-clients', '专服：冲刺结束、服务端空转稳定之后，两个客户端各自的桶与辐照通道罐量副本相同，并与服务端相同'
     '（活塞位置不在本行：客户端把同步来的值放进只用于绘制的字段，执行器读不到，见 mp-autoloader-piston）',
     'RBMKOutgasserBlockEntity serialize, barrel sync'),
    ('rbmk-autoloader.mp-autoloader-piston', '专服（待人看）：活塞行程走到一半时冻结，两个客户端各截一张图，两张图上装料机的活塞位置相同'
     '（客户端把同步来的活塞值写进 syncPiston 并插值成 renderPiston，只用于绘制；执行器导出的客户端方块实体数据里的 piston 是区块载入时的值，'
     '比不出同步，所以只能看图）', 'TileEntityRBMKAutoloader.java:131-140; RBMKAutoloaderBlockEntity.java:43,150-158,238-252'),
    ('rbmk-autoloader.mp-autoloader-restart', '专服重启后（静止、非默认的服务端读数）：燃料通道里的燃料棒、桶里的氚、装料机的设定与重启前相同',
     'RBMKAutoloaderBlockEntity.java:270-286, block entity save'),
]


def expectations():
    return [dict(id=i, text=t, source=s) for i, t, s in EXPECT]


def inv_slot(ctx, name, item):
    r = Z.rcon1(ctx, 'data get entity %s Inventory' % name)
    for e in _lib.data_value(r) if r and '[' in r else []:
        if e.get('id') == item and 0 <= e.get('Slot', -1) <= 35:
            return e['Slot']
    return None


def give_and_click(ctx, who, item, n_machine):
    ctx.rcon('give %s %s 1' % (who, item))
    ctx.step('wait', client=who, ticks=6)
    s = inv_slot(ctx, who, item)
    if s is None:
        raise RuntimeError('%s did not get %s' % (who, item))
    Z.shift_click(ctx, who, _lib.menu_slot(n_machine, s))
    ctx.step('close', client=who)


def client_tank(ctx, who, pos, key):
    d = ctx.step('dump', client=who, **{'from': list(pos)})
    nbt = _lib.parse_snbt(d['blocks'][0]['nbt']) if d['blocks'] and d['blocks'][0].get('nbt') else {}
    return nbt.get(key)


def run(ctx):
    a, b = list(ctx.channels)
    Z.setup_world(ctx, a, b)
    cells, built = R.build(ctx, a, SITE, LAYOUT)
    fuel, src, out = cells[(0, 0)], cells[(1, 0)], cells[(2, 0)]
    # the autoloader on the first fuel channel, by hand
    Z.hand(ctx, a, H + 'rbmk_autoloader')
    # sneaking (a plain right-click opens the fuel channel's screen), standing on the source column's top, outside the nine cells
    # straight above the channel that the autoloader takes
    R.sneak_use(ctx, a, (fuel[0], G + 3, fuel[2]), 'up', stand=(src[0] + 0.5, G + 4, src[2] + 0.5), look=(fuel[0] + 0.5, G + 3.999, fuel[2] + 0.5))
    ctx.rcon('item replace entity %s hotbar.0 with minecraft:air' % a)
    loader = (fuel[0], G + 4, fuel[2])
    placed = Z.block_is(ctx, loader, H + 'rbmk_autoloader')
    ctx.server('tick freeze')
    # the source and the lithium by their screens (opened from above, before the duct and the barrel cover the irradiation channel)
    R.open_column(ctx, a, src[0], src[2], 'RBMKRodScreen')
    give_and_click(ctx, a, H + 'rbmk_fuel_ra226be', 1)
    R.open_column(ctx, a, out[0], out[2], 'RBMKOutgasserScreen')
    give_and_click(ctx, a, H + 'lithium', 2)
    # duct and barrel above the irradiation channel's port (core + column height + 1)
    duct, barrel = (out[0], G + 4, out[2]), (out[0], G + 5, out[2])
    ctx.rcon('setblock %d %d %d %sfluid_duct_neo{Type:%d}' % (duct + (H, TRITIUM_ID)), 'setblock %d %d %d %sbarrel_steel' % (barrel + (H,)))
    ctx.step('wait', client=a, ticks=4)
    ctx.server('data merge block %d %d %d {mode:0s,tank_type:"TRITIUM"}' % barrel)
    # start at a known phase: game time = 19 (mod 20), then the fresh rod into the autoloader
    _lib.align(ctx, 20, 19, 'autoloader-align')
    ctx.step('key', client=a, key='key.keyboard.9', action='tap', after=2)
    ctx.step('view', client=a, pos=[loader[0] + 0.5, G + 4, loader[2] + 3.5], look_at=[loader[0] + 0.5, G + 5.5, loader[2] + 0.5], fly=True, hide_gui=False)
    ctx.step('use', client=a, target=dict(pos=[loader[0], G + 5, loader[2]], face='south'), any_hit=True, after=6)
    ctx.step('screen', client=a, expect='RBMKAutoloaderScreen')
    give_and_click(ctx, a, H + 'rbmk_fuel_ueu', 18)
    l0 = _lib.block_data(ctx, loader)
    t0 = ctx.server()['game_time']
    _lib.server_steps(ctx, 1)                       # game time = 0 (mod 20): the check starts the stroke
    _lib.server_steps(ctx, EXTEND // 2 - 1)
    for who in (a, b):                              # half way: the same moment on both clients, frozen
        ctx.step('view', client=who, pos=[loader[0] + (2.5 if who == a else -1.5), G + 6, loader[2] + 4.5],
                 look_at=[loader[0] + 0.5, G + 5, loader[2] + 0.5], fly=True, hide_gui=True)
    ctx.step('wait', client=a, ticks=10)
    shots = [ctx.step('shot', client=who, file=ctx.shot_name('piston-half-%s' % who)).get('image', {}).get('file') for who in (a, b)]
    mid = _lib.block_data(ctx, loader)
    _lib.server_steps(ctx, EXTEND // 2 - 1)
    l199 = _lib.block_data(ctx, loader)
    c199 = _lib.slot_count(_lib.block_data(ctx, fuel), 0)
    _lib.server_steps(ctx, 1)
    t200 = ctx.server()['game_time']
    l200 = _lib.block_data(ctx, loader)
    c200 = _lib.slot_count(_lib.block_data(ctx, fuel), 0, H + 'rbmk_fuel_ueu')
    ok_loader = (built and placed and (t0 + 1) % 20 == 0 and _lib.slot_count(l0, 0, H + 'rbmk_fuel_ueu') == 1 and c199 == 0
                 and abs(l199.get('piston', 0) - 0.995) < 1e-9 and c200 == 1 and _lib.slot_count(l200, 0) == 0 and t200 - t0 == EXTEND)
    ctx.check('rbmk-autoloader.mp-autoloader-swap', ok_loader,
              'built %s, autoloader placed %s; rod in the autoloader %d at game time %d (next tick %% 20 = %d); piston half way %s; after 199 ticks: '
              'piston %s, channel %d; after 200 (game time +%d): channel rod %d, autoloader slot 0 %d'
              % (built, placed, _lib.slot_count(l0, 0), t0, (t0 + 1) % 20, mid.get('piston'), l199.get('piston'), c199, t200 - t0, c200,
                 _lib.slot_count(l200, 0)))

    # the outgasser: run until the barrel holds tritium, then freeze and settle
    def full(c):
        return _lib.tanks(_lib.block_data(c, barrel)).get('tank', {}).get('fill', 0) >= 1000
    rec = ctx.sprint(20000, until=full, label='outgasser', poll_s=1.0, timeout_s=300)
    _lib.still(ctx, rec)
    sb = _lib.tanks(_lib.block_data(ctx, barrel)).get('tank', {})
    so = _lib.block_data(ctx, out)
    sgas = _lib.tanks(so).get('gas', {}).get('fill')
    ctx.check('rbmk-outgasser.mp-outgasser-tritium', sb.get('fill') == 1000 and sb.get('type') in ('TRITIUM', TRITIUM_ID),
              'outgasser sprint %s ticks in %s s; barrel %s; outgasser tank %s, progress %s' % (rec.get('advanced'), rec.get('wall_s'), sb, sgas,
                                                                                               so.get('progress')))
    _lib.server_idle(ctx, a)                        # the clients may lag behind a sprint: compared once the server idles
    for who in (a, b):
        ctx.step('view', client=who, pos=[out[0] + 0.5, G + 6, out[2] + 4.5], look_at=[out[0] + 0.5, G + 4, out[2] + 0.5], fly=True, hide_gui=False)
    ctx.step('wait', client=a, ticks=20)
    sb2 = _lib.tanks(_lib.block_data(ctx, barrel)).get('tank', {}).get('fill')
    sgas2 = _lib.tanks(_lib.block_data(ctx, out)).get('gas', {}).get('fill')
    cb = {n: client_tank(ctx, n, barrel, 'tank') for n in (a, b)}
    co = {n: client_tank(ctx, n, out, 'gas') for n in (a, b)}
    ctx.check('rbmk-outgasser.mp-outgasser-clients', sb2 is not None and cb[a] == cb[b] == sb2 and co[a] == co[b] == sgas2,
              'server after idling: barrel %s, outgasser tank %s; clients: barrel %s, outgasser %s' % (sb2, sgas2, cb, co))
    ctx.review('rbmk-autoloader.mp-autoloader-piston', 'piston on the server half way %s; one picture per client, taken in the same frozen tick'
               % mid.get('piston'), [s for s in shots if s])

    def reads():
        lo = _lib.block_data(ctx, loader)
        return dict(channel=_lib.slot_count(_lib.block_data(ctx, fuel), 0, H + 'rbmk_fuel_ueu'),
                    tritium=_lib.tanks(_lib.block_data(ctx, barrel)).get('tank', {}).get('fill'), cycle=lo.get('cycle'))
    # a still state: the source rod out of its channel (no flux, no burning), the world frozen
    R.open_column(ctx, a, src[0], src[2], 'RBMKRodScreen')
    Z.shift_click(ctx, a, 0)
    ctx.step('close', client=a)
    pre = reads()
    _lib.server_idle(ctx, a)
    ctx.restart_server()
    ctx.server('tick freeze')
    ctx.step('wait', client=a, ticks=80)
    post = reads()
    cmp = _lib.compare_static(pre, post, not_quantity=('cycle',))
    ctx.check('rbmk-autoloader.mp-autoloader-restart', cmp['ok'], 'before %s, after %s; %s' % (pre, post, cmp['detail']))
    _lib.server_idle(ctx, a)
