"""Dedicated server: a radio torch receiver destroys itself when its channel carries "selfdestruct".

Layout (flat world, feet at y = -60; SITE = (x, z)):
- a stone block S at (x, -60, z) (command); A places the sender by hand on its west face, so the sender stands at (x - 1, -60, z)
  facing west and reads the stone behind it; A places a lever by hand on top of S;
- receiver R1 on the ground 6 blocks east of S, receiver R2 16 blocks east of S (outside the blast), both placed by hand;
- a pig without AI 3 blocks east of R1 (command) shows the blast's entity damage.
The executor cannot type into the radio torch screens, so the channels and the custom mapping are written into the block data
by command (预写): sender channel alpha, custom mapping on, entry 15 "selfdestruct"; R1 channel alpha; R2 channel alpha-b.

Expected (original 1.7.10 / NEO):
- the sender reads the strong power of the block behind it (the lever powers S: 15) and, with the custom mapping on, broadcasts
  mapping[15] on its channel (original TileEntityRadioTorchSender.java:15-32; NEO RadioTorchSenderBlockEntity.java:20-41);
- a receiver on that channel that reads "selfdestruct" removes its block without drops and sets off an explosion of size 5 whose
  entity processor (EntityProcessorCrossSmooth(1, 50), range 2 x 5 = 10 blocks, damage 50 x (1 - distance / 10)) hurts the
  entities around it; no block is destroyed, since the explosion has no block processor (original
  TileEntityRadioTorchReceiver.java:21-33; NEO RadioTorchReceiverBlockEntity.java:24-42, EntityProcessorCross.java:54,93,
  EntityProcessorCrossSmooth.java:52-55). The pig 3 blocks away takes 50 x 0.7 = 35 > its 10 health and dies;
- a receiver on another channel does not react.
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
    id='radio-torch.mp_selfdestruct',
    feature='radio-torch',
    title='Dedicated server: radio torch receiver self-destruct (block removed without drops, blast, other channel untouched)',
    group='mp',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

G = _lib.FLAT_FEET
H = _lib.H
SITE = (-40, -30)
CHANNEL = 'alpha'
RT = 'radio-torch.'
SENDER = H + 'radio_torch_sender'
RECEIVER = H + 'radio_torch_receiver'
EXPECT = [
    ('mp-selfdestruct', '专服：发射器（手放在石块西面）开自定义映射，第 15 行为 selfdestruct，频道与映射用命令写进方块数据（预写）；A 手放拉杆在石块上并拉下：'
     '石块被强充能 15，发射器存下的状态为 15；同频道接收器 R1 的方块变成空气，地上没有接收器物品；R1 东 3 格的猪死亡（爆炸实体伤害 50×(1−3/10)=35 大于 10 点生命）；'
     '另一频道的接收器 R2 还在；A、B 两个客户端看到的 R1、R2 与服务端相同',
     'TileEntityRadioTorchSender.java:15-32, TileEntityRadioTorchReceiver.java:21-33; RadioTorchSenderBlockEntity.java:20-41, '
     'RadioTorchReceiverBlockEntity.java:24-42, EntityProcessorCross.java:54,93, EntityProcessorCrossSmooth.java:52-55'),
    ('mp-selfdestruct-server', '专服：自毁之后服务端照常运行：RCON 的 list 仍列出两名玩家，平均刻耗时回到 50 ms 以下，两个客户端仍在世界里；'
     '从拉杆之前到这里的服务端日志没有 Exception 或 ERROR 行',
     'RadioTorchReceiverBlockEntity.java:32-42'),
    ('mp-selfdestruct-restart', '专服重启后比对静止的服务端读数：发射器存下的状态 15 与频道、映射第 15 行，R2 的频道，R1 处仍是空气，与重启前相同',
     'RadioTorchBaseBlockEntity.java:55-76'),
]


def expectations():
    return [dict(id=RT + k, text=t, source=s) for k, t, s in EXPECT]


def place_on(ctx, who, item, pos, face, stand):
    """`who` holds `item` (hotbar slot 1, by command) and right-clicks `face` of the block at pos from stand (feet): real placement."""
    Z.hand(ctx, who, item)
    ctx.step('view', client=who, pos=list(stand), look_at=_lib.face_point(pos, face), fly=True, hide_gui=False)
    r = ctx.step('use', client=who, target=dict(pos=list(pos), face=face), after=8)
    ctx.rcon('item replace entity %s hotbar.0 with minecraft:air' % who)
    return r


def client_blocks(ctx, who, positions):
    """{pos: block id or None} as the client sees them (dump of each position)."""
    out = {}
    for p in positions:
        d = ctx.step('dump', client=who, **{'from': list(p)})
        out[p] = d['blocks'][0]['block'] if d['blocks'] else None
    return out


def readings(ctx, sender, r1, r2):
    s = _lib.block_data(ctx, sender)
    r = _lib.block_data(ctx, r2)
    return dict(sender_state=s.get('l'), sender_channel=s.get('c'), sender_map15=s.get('m15'), r2_channel=r.get('c'),
                r1_air=Z.block_is(ctx, r1, 'minecraft:air'))


def run(ctx):
    a, b = list(ctx.channels)
    Z.setup_world(ctx, a, b)
    ctx.rcon('tick unfreeze')
    x, z = SITE
    stone = (x, G, z)
    sender = (x - 1, G, z)
    lever = (x, G + 1, z)
    r1 = (x + 6, G, z)
    r2 = (x + 16, G, z)
    pig = (x + 9, G, z)
    ctx.rcon('fill %d %d %d %d %d %d minecraft:air' % (x - 4, G, z - 4, x + 20, G + 4, z + 4),
             'kill @e[type=!minecraft:player,x=%d,y=%d,z=%d,distance=..30]' % (x, G, z),
             'setblock %d %d %d minecraft:stone' % stone)
    ctx.step('wait', client=a, ticks=5)

    # real placement: sender on the stone's west face, the two receivers on the ground, the lever on the stone
    place_on(ctx, a, SENDER, stone, 'west', [x - 2.5, G, z + 1.5])
    place_on(ctx, a, RECEIVER, (r1[0], G - 1, r1[2]), 'up', [r1[0] + 0.5, G, r1[2] + 2.5])
    place_on(ctx, a, RECEIVER, (r2[0], G - 1, r2[2]), 'up', [r2[0] + 0.5, G, r2[2] + 2.5])
    place_on(ctx, a, 'minecraft:lever', stone, 'up', [x + 0.5, G, z + 3.5])
    placed = dict(sender=Z.block_is(ctx, sender, SENDER + '[facing=west]'), r1=Z.block_is(ctx, r1, RECEIVER),
                  r2=Z.block_is(ctx, r2, RECEIVER), lever=Z.block_is(ctx, lever, 'minecraft:lever[powered=false]'))
    if not all(placed.values()):
        raise RuntimeError('placement by hand failed: %s' % placed)

    # 预写: channels and the custom mapping (the screens need typing)
    ctx.rcon('data merge block %d %d %d {c:"%s",m:1b,m15:"selfdestruct"}' % (sender + (CHANNEL,)),
             'data merge block %d %d %d {c:"%s"}' % (r1 + (CHANNEL,)),
             'data merge block %d %d %d {c:"%s-b"}' % (r2 + (CHANNEL,)),
             'summon minecraft:pig %d %d %d {NoAI:1b,PersistenceRequired:1b}' % (pig[0], G, pig[2]))
    ctx.step('wait', client=a, ticks=10)
    pigs_before = Z.entity_count(ctx, '@e[type=minecraft:pig,x=%d,y=%d,z=%d,distance=..4]' % pig)
    ctx.step('view', client=b, pos=[x + 4.5, G, z + 14.5], look_at=[r1[0] + 0.5, G + 0.5, r1[2] + 0.5], fly=True, hide_gui=False)
    mark = Z.log_mark()

    # A pulls the lever from 4 blocks south (empty hand)
    ctx.step('key', client=a, key='key.keyboard.9', action='tap', after=2)
    ctx.step('view', client=a, pos=[x + 0.5, G, z + 4.5], look_at=[x + 0.5, G + 1.15, z + 0.5], fly=True, hide_gui=False)
    # the use step aims at the target face's centre plus `offset`: the floor lever is a small box in the lower half of its cell
    use = ctx.step('use', client=a, target=dict(pos=list(lever), face='south', offset=[0.0, -0.35, -0.45]), any_hit=True, after=10)
    ctx.step('wait', client=b, ticks=20)

    lever_on = Z.block_is(ctx, lever, 'minecraft:lever[powered=true]')
    s = _lib.block_data(ctx, sender)
    r1_gone = Z.block_is(ctx, r1, 'minecraft:air')
    r2_there = Z.block_is(ctx, r2, RECEIVER)
    drops = Z.entity_count(ctx, '@e[type=minecraft:item,nbt={Item:{id:"%s"}}]' % RECEIVER)
    pigs_after = Z.entity_count(ctx, '@e[type=minecraft:pig,x=%d,y=%d,z=%d,distance=..6]' % pig)
    seen = {who: client_blocks(ctx, who, (r1, r2)) for who in (a, b)}
    clients_ok = all(v[r1] is None and v[r2] == RECEIVER for v in seen.values())
    ok = (lever_on and s.get('l') == 15 and r1_gone and r2_there and drops == 0 and pigs_before == 1 and pigs_after == 0 and clients_ok)
    ctx.check(RT + 'mp-selfdestruct', ok,
              '预写 channels/mapping; lever hit %s, powered %s; sender state %s (map15 %r); R1 air %s; receiver items on the ground %d; '
              'pigs %d before, %d after; R2 still a receiver %s; clients see %s'
              % (use.get('hit'), lever_on, s.get('l'), s.get('m15'), r1_gone, drops, pigs_before, pigs_after, r2_there,
                 {w: {str(p): v for p, v in d.items()} for w, d in seen.items()}),
              ['rcon log', 'use seq %s' % use['seq']])

    # the server keeps running
    listed = Z.rcon1(ctx, 'list')
    idle = _lib.server_idle(ctx, a)
    lines, logs = Z.log_lines(mark)
    client_cls, other = Z.bad_log_lines(lines)
    in_world = {}
    for who, ch in ctx.channels.items():
        st = common.read_json(ch.dir / 'status.json') or {}
        in_world[who] = bool(st.get('in_world'))
    ok2 = (a in listed and b in listed and all(in_world.values()) and not client_cls and not other)
    ctx.check(RT + 'mp-selfdestruct-server', ok2,
              'list: %s; tick query after idle: %s; clients in world %s; server log lines since the lever %d (%s): client-class %s, other %s'
              % (listed[:120], idle[-1] if idle else None, in_world, len(lines), ', '.join(logs), client_cls[:3], other[:5]),
              ['rcon log'])

    # restart: static stored readings
    pre = readings(ctx, sender, r1, r2)
    for who in (a, b):
        ctx.step('close', client=who, allow_fail=True)
    _lib.reopen(ctx, who=a)
    _lib.server_idle(ctx, a)
    post = readings(ctx, sender, r1, r2)
    cmp = _lib.compare_static(pre, post, not_quantity=('sender_channel', 'sender_map15', 'r2_channel', 'r1_air'))
    ctx.check(RT + 'mp-selfdestruct-restart', cmp['ok'], 'before %s, after %s; %s' % (pre, post, cmp['detail']), ['rcon log'])
    ctx.rcon('kill @e[type=minecraft:item]', 'tick unfreeze')
