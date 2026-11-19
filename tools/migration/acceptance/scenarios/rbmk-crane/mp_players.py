"""Dedicated server: two players and the RBMK crane.

Rig (player A, by hand; items put in the hand by command): three fuel channels in a row west to east at y = G, a natural uranium
RBMK rod shift-clicked into the western one, and a crane console placed 6 blocks south of the middle channel, linked to it with
the RBMK console linking device (sneak + right-click on the column, then on the crane console).

Expected (original 1.7.10 TileEntityCraneConsole / NEO RBMKCraneConsoleBlockEntity):
- the crane is centred over the linked column; the column under the lift is centre - facing x posFront - left x posLeft,
  rounded (original :224-245; NEO :270-297). The first player found in the box in front of the console (three blocks wide,
  two high, two blocks towards the facing) steers it: while a crane key is held the position moves by 0.05 a server tick
  (original :132-176, speed :57; NEO :141-178,202-218); a player outside the box moves nothing.
- the load key lowers the lift by 0.04 a tick; at the bottom it takes the rod out of an IRBMKLoadable column or puts the held rod
  in, then rises again (original :98-129; NEO :104-136). Twenty ticks of a held key move the lift over the next column
  (0.05 x 20 = 1, rounded to the column even with a tick more or less).
- the crane's position and lift reach every client with the block entity packets (original/NEO serialize, NEO :306-350).
- with two players in the box only the first one of the server's entity list steers (original :139-150, "as the original,
  only the first player found steers the crane"); which one that is, is recorded.
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
    id='rbmk-crane.mp_players',
    feature='rbmk-crane',
    title='Dedicated server: two players and the RBMK crane (steering, unloading and loading, out of range, two in range)',
    group='mp',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

G = Z.G
H = Z.H
SITE = (60, -100)
LAYOUT = [['rbmk_rod', 'rbmk_rod', 'rbmk_rod']]
ROD = H + 'rbmk_fuel_ueu'
KEYS = dict(up='key.keyboard.up', down='key.keyboard.down', left='key.keyboard.left', right='key.keyboard.right', load='key.keyboard.enter')
CR = 'rbmk-crane.'
EXPECT = [
    ('mp-crane-drive', '专服：A 站在吊车控制台前按住方向键 20 刻，吊车移到西边的燃料通道上方，按装卸键取出燃料棒（天然铀 RBMK 燃料棒，命令发放后 Shift 点进西边通道）；'
     '再按住反方向 40 刻移到东边的通道，按装卸键放进去：服务端西边通道空、东边通道有这根棒、吊车不再持有',
     'TileEntityCraneConsole.java:72-245; RBMKCraneConsoleBlockEntity.java:83-297'),
    ('mp-crane-b-sync', '专服：A 每次移动吊车之后，B 客户端的吊车位置（同步的方块实体，指示灯与吊钩的画面由它画出）与服务端相同',
     'TileEntityCraneConsole.java:96; RBMKCraneConsoleBlockEntity.java:106,306-350'),
    ('mp-crane-visual', '专服（待人看，用户站点）：B 在吊车控制台的网格上看到指示灯随吊车移动，看到吊车与吊钩的动画；只能人看（B 的副本数值在 mp-crane-b-sync 里判定）',
     'TileEntityCraneConsole.java:96, RenderCraneConsole; RBMKCraneConsoleBlockEntity.java:106'),
    ('mp-crane-out-of-range', '专服：B 站在检测范围外（控制台前方 6.5 格）按住方向键 20 刻，服务端吊车位置不变',
     'TileEntityCraneConsole.java:132-150; RBMKCraneConsoleBlockEntity.java:141-178'),
    ('mp-crane-two-in-range', '专服（待人看，只记录）：两人都站进检测范围、B 先按、A 后按方向键各 10 刻，记录实际由谁控制吊车（原版只认检测列表里的第一名，'
     '谁是第一名不固定）。要人看的原因：原版与 NEO 都取范围内玩家列表的第一名（原版 getEntitiesWithinAABB 的 players.get(0)，NEO '
     'getEntitiesOfClass 的 players.get(0)），列表的先后由玩家进入区块实体表的先后决定，代码里没有固定答案，推不出一个可以自动判定的期望值；'
     '记下的“谁在控制”是否可以接受，要由人站在两人的位置上操作一次，看另一人按键时吊车与指示灯是否抖动、乱跳，再下结论',
     'TileEntityCraneConsole.java:139-150; RBMKCraneConsoleBlockEntity.java:141-178'),
    ('mp-crane-restart', '专服重启后（静止、非默认的服务端读数）：吊车的位置与连接、东边通道里的燃料棒与重启前相同',
     'RBMKCraneConsoleBlockEntity.java:396-435'),
]


def expectations():
    return [dict(id=CR + k, text=t, source=s) for k, t, s in EXPECT]


def crane(ctx, pos):
    d = _lib.block_data(ctx, pos)
    return dict(front=d.get('posFront'), left=d.get('posLeft'), held=(d.get('held') or {}).get('id'), crane=d.get('crane'),
                center=(d.get('centerX'), d.get('centerY'), d.get('centerZ')))


def client_crane(ctx, who, pos):
    d = ctx.step('dump', client=who, **{'from': list(pos)})
    nbt = _lib.parse_snbt(d['blocks'][0]['nbt']) if d['blocks'] and d['blocks'][0].get('nbt') else {}
    return nbt.get('posFront'), nbt.get('posLeft')


def hold_key(ctx, who, key, ticks):
    ctx.step('key', client=who, key=KEYS[key], action='tap', hold=ticks, after=10)


def rod_in(ctx, pos):
    return _lib.slot_count(_lib.block_data(ctx, pos), 0, ROD)


def run(ctx):
    a, b = list(ctx.channels)
    Z.setup_world(ctx, a, b)
    ctx.server('tick unfreeze')
    cells, built = R.build(ctx, a, SITE, LAYOUT)
    west, mid, east = cells[(0, 0)], cells[(1, 0)], cells[(2, 0)]
    R.open_column(ctx, a, west[0], west[2], 'RBMKRodScreen')
    ctx.rcon('give %s %s 1' % (a, ROD))
    ctx.step('wait', client=a, ticks=6)
    r = Z.rcon1(ctx, 'data get entity %s Inventory' % a)
    slot = next((e['Slot'] for e in (_lib.data_value(r) if '[' in r else []) if e.get('id') == ROD), None)
    Z.shift_click(ctx, a, _lib.menu_slot(1, slot))
    ctx.step('close', client=a)
    core = Z.place_by_hand(ctx, a, H + 'rbmk_crane_console', mid[0], mid[2] + 6, H + 'rbmk_crane_console',
                           ((mid[0] - 4, G, mid[2] + 2), (mid[0] + 4, G + 3, mid[2] + 10)))
    facing = ctx.step('dump', client=a, **{'from': list(core)})['blocks'][0]['props'].get('facing')
    # link: the device on the middle column (standing on the western column's top), then on the crane console (from its front),
    # both sneaking (a plain right-click opens the fuel channel's screen)
    Z.hand(ctx, a, H + 'rbmk_tool')
    R.sneak_use(ctx, a, (mid[0], G + 3, mid[2]), 'up', stand=(west[0] + 0.5, G + 4, west[2] + 0.5), look=(mid[0] + 0.5, G + 3.999, mid[2] + 0.5))
    d = _lib.VEC[facing]
    front = [core[0] + 0.5 + d[0] * 2.5, G, core[2] + 0.5 + d[2] * 2.5]
    R.sneak_use(ctx, a, core, facing, stand=front, look=(core[0] + 0.5, G + 0.5, core[2] + 0.5), fly=True, any_hit=True)
    ctx.rcon('item replace entity %s hotbar.0 with minecraft:air' % a)
    c0 = crane(ctx, core)
    linked = c0['crane'] in (1, True) and c0['center'][0] == mid[0] and c0['center'][2] == mid[2]
    # which key moves the lift one column west: column = centre - facing * front - left * left (left = counter-clockwise of facing)
    left = _lib.VEC[_lib.counter_clockwise(facing)]
    west_v = (-1, 0, 0)
    if left[0]:
        key_w = 'left' if -left[0] * 1 == west_v[0] else 'right'
        axis = 'left'
    else:
        key_w = 'up' if -d[0] * 1 == west_v[0] else 'down'
        axis = 'front'
    key_e = dict(left='right', right='left', up='down', down='up')[key_w]
    # A in the box: 1.5 blocks in front of the core; B 5 blocks further out (outside)
    seat_a = [core[0] + 0.5 + d[0] * 1.5, G, core[2] + 0.5 + d[2] * 1.5]
    seat_out = [core[0] + 0.5 + d[0] * 6.5, G, core[2] + 0.5 + d[2] * 6.5]
    ctx.step('view', client=a, pos=seat_a, look_at=[mid[0] + 0.5, G + 3, mid[2] + 0.5], fly=False, hide_gui=False)
    ctx.step('view', client=b, pos=seat_out, look_at=[mid[0] + 0.5, G + 3, mid[2] + 0.5], fly=False, hide_gui=False)
    ctx.step('wait', client=a, ticks=10)

    hold_key(ctx, a, key_w, 20)
    c1 = crane(ctx, core)
    b1 = client_crane(ctx, b, core)
    hold_key(ctx, a, 'load', 3)
    ctx.step('wait', client=a, ticks=70)
    c2 = crane(ctx, core)
    west_after = rod_in(ctx, west)
    hold_key(ctx, a, key_e, 40)
    c3 = crane(ctx, core)
    b3 = client_crane(ctx, b, core)
    hold_key(ctx, a, 'load', 3)
    ctx.step('wait', client=a, ticks=70)
    c4 = crane(ctx, core)
    east_after = rod_in(ctx, east)
    # B outside the box presses a direction key
    hold_key(ctx, b, key_w, 20)
    c5 = crane(ctx, core)
    pos_of = (lambda c: c[axis])
    moved_a = abs(pos_of(c1)) >= 0.9 and abs(pos_of(c3) + pos_of(c1)) <= 0.2
    ctx.check(CR + 'mp-crane-drive', built and linked and moved_a and c2['held'] == ROD and west_after == 0 and c4['held'] is None and east_after == 1,
              'built %s; crane console %s facing %s, linked %s (centre %s); key west %s, east %s on the %s axis; after A held %s 20 ticks: server %s; '
              'after load: held %s, west channel %d; after %s 40 ticks: %s; after load: held %s, east channel %d'
              % (built, core, facing, linked, c0['center'], key_w, key_e, axis, key_w, (c1['front'], c1['left']), c2['held'], west_after, key_e,
                 (c3['front'], c3['left']), c4['held'], east_after))
    ctx.check(CR + 'mp-crane-b-sync', b1 == (c1['front'], c1['left']) and b3 == (c3['front'], c3['left']),
              'after the first move: server %s, B client %s; after the second: server %s, B client %s'
              % ((c1['front'], c1['left']), b1, (c3['front'], c3['left']), b3))
    ctx.check(CR + 'mp-crane-out-of-range', c5[axis] == c4[axis],
              'B %.1f blocks in front of the console pressed %s 20 ticks: %s %.3f -> %.3f' % (6.5, key_w, axis, c4[axis], c5[axis]))
    # both in the box: B one block to the side of A; B presses first, then A
    side = _lib.VEC[_lib.clockwise(facing)]
    ctx.step('view', client=b, pos=[seat_a[0] + side[0], G, seat_a[2] + side[2]], look_at=[mid[0] + 0.5, G + 3, mid[2] + 0.5], fly=False, hide_gui=False)
    ctx.step('wait', client=b, ticks=10)
    hold_key(ctx, b, key_w, 10)
    c6 = crane(ctx, core)
    hold_key(ctx, a, key_w, 10)
    c7 = crane(ctx, core)
    ctx.review(CR + 'mp-crane-two-in-range', 'for a person: the first player of the in-range list steers (original players.get(0), NEO :160), and '
               'that list\'s order is not fixed by the code, so no expected value can be asserted; a person judges whether the recorded '
               'behaviour is acceptable in play. Recorded: B pressed %s 10 ticks: %s %.3f -> %.3f (%s); then A pressed: -> %.3f (%s)'
               % (key_w, axis, c5[axis], c6[axis], 'B steers' if c6[axis] != c5[axis] else 'B does not steer', c7[axis],
                  'A steers' if c7[axis] != c6[axis] else 'A does not steer'))

    ctx.review(CR + 'mp-crane-visual', 'for a person at the user station: the indicator lights and the crane and hook animation as B sees them')
    pre = dict(front=c7['front'], left=c7['left'], center=list(c7['center']), east=rod_in(ctx, east))
    ctx.step('view', client=b, pos=seat_out, look_at=[mid[0] + 0.5, G + 3, mid[2] + 0.5], fly=False, hide_gui=False)
    ctx.step('view', client=a, pos=[seat_out[0] + 2, G, seat_out[2]], look_at=[mid[0] + 0.5, G + 3, mid[2] + 0.5], fly=False, hide_gui=False)
    _lib.server_idle(ctx, a)
    ctx.restart_server()
    ctx.server('tick freeze')
    ctx.step('wait', client=a, ticks=80)
    c8 = crane(ctx, core)
    post = dict(front=c8['front'], left=c8['left'], center=list(c8['center']), east=rod_in(ctx, east))
    cmp = _lib.compare_static(pre, post)
    ctx.check(CR + 'mp-crane-restart', cmp['ok'], 'before %s, after %s; %s' % (pre, post, cmp['detail']))
    _lib.server_idle(ctx, a)
