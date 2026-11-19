"""Dedicated server, RBMK meltdown in its own disposable world: debris and wreck on both clients, a pickup on the server, and the
radiation of the wreck worked out for each player.

Rig (built by hand by player A; items put in the hand by command): a 3 x 3 reactor at y = G, every column placed by a right-click
on the ground from the south, rows north to south, drawn north up (x to the right):

    blank(lid)  blank  blank
    blank       fuel   control
    blank       blank  blank

The standard lid is put on the north-west blank column with the lid item; the fuel channel gets one natural uranium RBMK rod
(rbmk_fuel_ueu, given by command, shift-clicked into the channel's screen). The meltdown is started by writing 3,000 °C into the
fuel channel's heat (预写): above the column's maximum heat the rod column melts the whole connected reactor on its next tick
(original TileEntityRBMKRod.updateEntity :158-169 with TileEntityRBMKBase.meltdown :439-573; NEO RBMKRodBlockEntity.java:145-157,
RBMKBaseBlockEntity.java:323-427).

Expected (original 1.7.10 / NEO):
- the fuel column holding a rod becomes corium (all four blocks) and throws 1-3 fuel debris, one element and (lid) one lid debris;
  every other column becomes wreck (pribris, one burning block when it collapses by more than one) and a blank throws one or two blank
  debris (1 + rand(2)), a lidded column its lid (original TileEntityRBMKRod.onMelt :329-361, TileEntityRBMKBlank.onMelt :9-17,
  TileEntityRBMKBase.onMelt :385-391 and standardMelt :393;
  NEO RBMKRodBlockEntity.java:336-388, RBMKBlankBlockEntity.java:16-25, RBMKBaseBlockEntity.java:261-320). Wreck cells around the
  corium become radiating wreck with chance 1/3 (original :477-498; NEO :384-405).
- debris and wreck are server entities and blocks: every client in range holds them as the server does; a right-click gives the
  debris item and removes the entity (original EntityRBMKDebris.java:35; NEO RBMKDebris.java:40-63).
- radiating wreck irradiates every living entity within 100 blocks with 1,000,000 / res / len^2 every 20-39 ticks, creative
  players excepted (original RBMKDebrisRadiating.java:80-125; NEO RBMKDebrisRadiatingBlock.java:45-53,92-118): each survival player gains
  his own amount; two players on one line from the reactor share the shielding, so one block's hit gives them amounts in the
  ratio of 1/len^2. A radiation of 1,000 kills (EntityEffectHandler.java:157): an unshielded block kills a player within about 31
  blocks in one hit.
- the overpressure branch (pipes and turbines of the steam channels blown up) runs only with the dial dialEnableMeltdownOverpressure,
  false by default (original RBMKDials.java:36; NEO CommonConfig.java:612-615).
"""
import importlib.util
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

_spec = importlib.util.spec_from_file_location('zirnox_mp_rig', Path(__file__).resolve().parents[1] / 'zirnox-reactor' / 'mp_meltdown.py')
Z = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(Z)

SCENARIO = dict(
    id='rbmk-reactor.mp_meltdown',
    feature='rbmk-reactor',
    title='Dedicated server: RBMK meltdown, debris and wreck on both clients, pickup, wreck radiation per player',
    group='mp',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

G = Z.G
H = Z.H
SITE = (60, -60)                       # north-west column of the 3 x 3 reactor
LAYOUT = [['rbmk_blank', 'rbmk_blank', 'rbmk_blank'],
          ['rbmk_blank', 'rbmk_rod', 'rbmk_control'],
          ['rbmk_blank', 'rbmk_blank', 'rbmk_blank']]
LID_AT = (0, 0)
FUEL_AT = (1, 1)
WRECK = ('pribris', 'pribris_burning', 'pribris_radiating', 'corium_block')
DEB = '@e[type=%srbmk_debris]' % H
DEB_ITEMS = {H + 'debris_metal', H + 'debris_fuel', H + 'debris_graphite', H + 'rbmk_lid'}
NEAR = 20
RAD_AT = (48, 96)                     # A's and B's distance east of the reactor centre for the radiation reading
RAD_STEPS = 40                        # single server ticks at most: every radiating block fires every 20-39 ticks

RX = 'rbmk-reactor.'
EXPECT = [
    ('mp-meltdown-sync', '专服：一次性世界里手搭的 3×3 小堆（燃料通道装天然铀 RBMK 燃料棒（命令发放），一根手动控制棒，一个加盖的空白柱），'
     '把燃料通道的热写成 3,000 °C（预写）后走 1 刻：燃料柱变成堆芯熔融物，其余柱变成残骸；服务端的碎片与两个客户端（离核心 20 格、'
     '飞行 120 刻后冻结）所持的碎片个数与位置一致（位置差不到 0.5 格，按跟踪距离 126 格）；反应堆范围里四种残骸方块在两个客户端上逐格相同，'
     '并与服务端各自的格数相同',
     'TileEntityRBMKBase.java:439-573, TileEntityRBMKRod.java:329-361; RBMKBaseBlockEntity.java:323-427, RBMKRodBlockEntity.java:336-388'),
    ('mp-debris-pickup', '专服：A 右键拾取一个碎片：服务端少一个，A 的服务端与客户端背包多一个对应的物品',
     'EntityRBMKDebris.java:35; RBMKDebris.java:40-63'),
    ('mp-wreck-radiation', '专服：两人切到生存，A 与 B 站在核心东边同一条线上的 48 格与 96 格'
     '（放射性残骸的 100 格范围内；两条视线在反应堆里穿过相同的格子，外面是空气），清掉状态效果、辐射置 0，冻结世界里一刻一刻地走（每刻前两人的辐射'
     '置 0，单次读数远低于致死的 1,000），至多 40 刻：A 第一次被放射性残骸照到的那一刻 B 也涨了，B 的涨幅与 A 的之比落在各放射性残骸块的 '
     '(lenA/lenB)² 之间（len 是块中心到眼睛的距离，按两人的服务端位置算；同一块照两人时屏蔽相同、只差 1/len²；相对误差不超过 0.1%，'
     '另扣冻结时量到的区块辐射本底），说明每人各算各的；两人都没有死',
     'RBMKDebrisRadiating.java:80-125; RBMKDebrisRadiatingBlock.java:45-53,92-118'),
    ('mp-overpressure-observe', '记录：RBMK 过压分支对管线另一端可能未加载的位置取方块实体（RBMKBaseBlockEntity.java:458）有没有在熔毁时造成卡顿或报错',
     'RBMKDials.java:36; RBMKDials.java:129-131, CommonConfig.java:612-615, RBMKBaseBlockEntity.java:409-410,440-479'),
    ('mp-meltdown-restart', '专服重启后（两人切回创造、回到离核心 20 格处；静止、非默认的服务端读数）：堆芯熔融物的格数、三种残骸的格数之和、碎片个数'
     '与两人的辐射值与重启前相同',
     'block, entity and player save'),
]


def expectations():
    return [dict(id=RX + k, text=t, source=s) for k, t, s in EXPECT]


# ---------------------------------------------------------------- RBMK helpers (the sibling RBMK mp files import these)

def place_column(ctx, who, item, x, z):
    """`who` stands 4.5 blocks south of (x, z) on the ground and right-clicks the ground's top face with the column item: the column
    stands on it. Layouts are built north to south, so the cells between the player and the target are still empty."""
    Z.hand(ctx, who, H + item)
    ctx.step('view', client=who, pos=[x + 0.5, G, z + 4.5], look_at=[x + 0.5, G - 0.5, z + 0.5], fly=True, hide_gui=False)
    return ctx.step('use', client=who, target=dict(pos=[x, G - 1, z], face='up'), after=6)


def use_top(ctx, who, x, z, top=G + 3, after=6):
    """Right-click on the top face of the column at (x, z) from 4 blocks above (opens the column's screen with an empty hand)."""
    ctx.step('view', client=who, eye=[x + 0.5, top + 4, z + 0.5], yaw=180.0, pitch=90.0, fly=True, hide_gui=False)
    return ctx.step('use', client=who, target=dict(pos=[x, top, z], face='up'), after=after)


def sneak_use(ctx, who, target, face, stand, look, fly=False, any_hit=False):
    """Right-click while sneaking: a column or console with a screen of its own opens it on a plain right-click, so a held item
    meant for the block (the linking device, the autoloader) is used with the sneak key held, as a player does. `stand` is where
    the feet go (on a block, fly=False, so the sneak key does not lower a flying player), `look` the aim point."""
    ctx.step('view', client=who, pos=list(stand), look_at=list(look), fly=fly, hide_gui=False)
    ctx.step('key', client=who, key='key.keyboard.left.shift', action='press', after=3)
    try:
        return ctx.step('use', client=who, target=dict(pos=list(target), face=face), any_hit=any_hit, after=6)
    finally:
        ctx.step('key', client=who, key='key.keyboard.left.shift', action='release', after=3)


def open_column(ctx, who, x, z, expect):
    ctx.step('key', client=who, key='key.keyboard.9', action='tap', after=2)
    use_top(ctx, who, x, z)
    ctx.step('screen', client=who, expect=expect)
    return ctx.step('hud', client=who, frames=2)


def build(ctx, a, site, layout):
    """Places the layout (rows north to south) by hand; returns {(col, row): (x, G, z)} and whether every
    column stands four blocks tall."""
    x0, z0 = site
    cells = {}
    for r, row in enumerate(layout):
        for c, item in enumerate(row):
            if item:
                place_column(ctx, a, item, x0 + c, z0 + r)
                cells[(c, r)] = (x0 + c, G, z0 + r)
    ctx.rcon('item replace entity %s hotbar.0 with minecraft:air' % a)
    ok = all(Z.block_is(ctx, p, H + layout[r][c]) and Z.block_is(ctx, (p[0], G + 3, p[2]), H + layout[r][c]) for (c, r), p in cells.items())
    return cells, ok


def wreck_counts(ctx, lo, hi):
    return {w: Z.clone_count(ctx, lo, hi, H + w) for w in WRECK}


def still_counts(ctx, box):
    """Wreck readings that hold still across a restart: the corium cells and the sum of the three wreck kinds (burning wreck turns
    into plain wreck with chance 1/100 every 100-119 ticks, RBMKDebrisBurningBlock.java:61-69, while the world runs)."""
    c = wreck_counts(ctx, *box)
    return dict(corium=c['corium_block'], wreck=c['pribris'] + c['pribris_burning'] + c['pribris_radiating'])


def ray_cells(center, eye):
    """(len, block cells at whole-block steps i = 1 .. len-1) along the line from a block centre to the eyes, as the radiating wreck
    walks it (RBMKDebrisRadiatingBlock.java:100-110)."""
    v = [eye[i] - center[i] for i in range(3)]
    n = math.sqrt(sum(c * c for c in v))
    u = [c / n for c in v]
    cells, i = [], 1
    while i < n:
        cells.append(tuple(math.floor(center[k] + u[k] * i) for k in range(3)))
        i += 1
    return n, cells


def blocks_of(dump):
    return sorted((tuple(int(c) for c in d['pos']), d['block']) for d in dump['blocks'])


def tick_ms(ctx):
    m = re.search(r'([\d.]+)\s*ms', Z.rcon1(ctx, 'tick query'))
    return float(m.group(1)) if m else None


def load_fuel(ctx, a, cells):
    """A opens the fuel channel and shift-clicks one natural uranium RBMK rod in (rod menu: 1 slot, then the player's inventory)."""
    fx, _, fz = cells[FUEL_AT]
    open_column(ctx, a, fx, fz, 'RBMKRodScreen')
    ctx.rcon('give %s %srbmk_fuel_ueu 1' % (a, H))
    ctx.step('wait', client=a, ticks=6)
    s = Z.inventory(ctx, a)
    slot = None
    r = Z.rcon1(ctx, 'data get entity %s Inventory' % a)
    for e in _lib.data_value(r) if r and '[' in r else []:
        if e.get('id') == H + 'rbmk_fuel_ueu':
            slot = e.get('Slot')
    Z.shift_click(ctx, a, _lib.menu_slot(1, slot))
    ctx.step('close', client=a)
    return _lib.slot_count(_lib.block_data(ctx, cells[FUEL_AT]), 0, H + 'rbmk_fuel_ueu'), s


def melt(ctx, a, b, site=SITE):
    """Builds the rig of the module docstring and melts it: returns dict(cells, ok, detail, box, ms) in a frozen world."""
    cells, built = build(ctx, a, site, LAYOUT)
    lx, _, lz = cells[LID_AT]
    Z.hand(ctx, a, H + 'rbmk_lid')
    use_top(ctx, a, lx, lz)
    ctx.rcon('item replace entity %s hotbar.0 with minecraft:air' % a)
    lid = Z.block_is(ctx, cells[LID_AT], '%srbmk_blank[lid=standard]' % H)
    fuel, _ = load_fuel(ctx, a, cells)
    ctx.server('tick freeze')
    x0, z0 = site
    for who, dx in ((a, NEAR + 1), (b, -NEAR + 1)):
        ctx.step('view', client=who, pos=[x0 + 1.5 + dx, G + 6, z0 + 1.5], look_at=[x0 + 1.5, G + 2, z0 + 1.5], fly=True, hide_gui=False)
    fc = cells[FUEL_AT]
    ctx.server('data merge block %d %d %d {heat:3000.0d}' % fc)
    ms0 = tick_ms(ctx)
    _lib.server_steps(ctx, 1)
    ms1 = tick_ms(ctx)
    corium = Z.block_is(ctx, fc, H + 'corium_block') and Z.block_is(ctx, (fc[0], G + 3, fc[2]), H + 'corium_block')
    box = ((x0 - 1, G - 1, z0 - 1), (x0 + 3, G + 4, z0 + 3))
    counts = wreck_counts(ctx, *box)
    debris = Z.entity_count(ctx, DEB)
    others_gone = all(not Z.block_is(ctx, p, H + LAYOUT[r][c]) for (c, r), p in cells.items())
    ok = built and lid and fuel == 1 and corium and others_gone and debris > 0
    detail = ('columns built %s, lid %s, rod in the fuel channel %d; after one tick: fuel column corium %s, no column left %s; wreck counts %s; '
              'debris %d' % (built, lid, fuel, corium, others_gone, counts, debris))
    return dict(cells=cells, ok=ok, detail=detail, box=box, counts=counts, ms=(ms0, ms1))


def sync_after_flight(ctx, a, b, site, box):
    """Unfreezes for 120 ticks, freezes, brings both players to NEAR blocks east and west of the reactor and compares their debris
    and wreck blocks with the server. Returns (ok, detail, server debris positions)."""
    x0, z0 = site
    centre = (x0 + 1.5, G + 4, z0 + 1.5)
    ctx.server('tick unfreeze')
    ctx.step('wait', client=a, ticks=120)
    ctx.server('tick freeze')
    seat = {a: (x0 + 1.5 + NEAR, z0 + 1.5), b: (x0 + 1.5 - NEAR, z0 + 1.5)}
    for who in (a, b):
        ctx.step('view', client=who, pos=[seat[who][0], G + 4, seat[who][1]], look_at=list(centre), fly=True, hide_gui=False)
    ctx.step('wait', client=a, ticks=80)
    pos = Z.server_positions(ctx, DEB)
    held = Z.both(ctx, lambda n: Z.client_entities(ctx, n, centre, 200, H + 'rbmk_debris'))
    tracked = {n: Z.in_range(pos, seat[n]) for n in (a, b)}
    dev = {n: Z.match_positions(tracked[n][0], [tuple(e['last']) for e in held[n]]) for n in (a, b)}
    spec = {'from': list(box[0]), 'to': list(box[1])}
    blocks = Z.both(ctx, lambda n: blocks_of(ctx.step('dump', client=n, **spec)))
    server = wreck_counts(ctx, *box)
    client = {n: {w: sum(1 for _, blk in blocks[n] if blk == H + w) for w in WRECK} for n in (a, b)}
    ok = (bool(pos) and all(len(tracked[n][0]) <= len(held[n]) <= len(tracked[n][0]) + tracked[n][1] for n in (a, b))
          and all(dev[n] is not None and dev[n] < 0.5 for n in (a, b)) and blocks[a] == blocks[b] and client[a] == server)
    detail = ('server debris %d; clients hold %s (server within 126 / 126-130 blocks %s), largest distance %s; wreck: client block lists equal %s, '
              'client counts %s, server %s' % (len(pos), {n: len(held[n]) for n in (a, b)}, {n: (len(tracked[n][0]), tracked[n][1]) for n in (a, b)},
                                              {n: dev[n] and round(dev[n], 3) for n in (a, b)}, blocks[a] == blocks[b], client[a], server))
    return ok, detail, pos


# ---------------------------------------------------------------- the scenario

def run(ctx):
    a, b = list(ctx.channels)
    mark = Z.log_mark()
    Z.setup_world(ctx, a, b)
    m = melt(ctx, a, b)
    x0, z0 = SITE
    ok_sync, sync_detail, pos = sync_after_flight(ctx, a, b, SITE, m['box'])

    # pickup by A: the debris nearest to the reactor among those on the ground (one resting on the wreck, y G + 4, puts A's body in
    # the wreck and the client pushes A off the seat), seen from 2 blocks further out on the line from the reactor centre, where the
    # two cells of A's body are air
    cx, cz = x0 + 1.5, z0 + 1.5
    target = eye = None
    for p in sorted((p for p in pos if abs(p[1] - G) < 0.01), key=lambda p: (p[0] - cx) ** 2 + (p[2] - cz) ** 2):
        d = math.hypot(p[0] - cx, p[2] - cz) or 1.0
        e = [p[0] + 2.0 * (p[0] - cx) / d, p[1] + 0.3, p[2] + 2.0 * (p[2] - cz) / d]
        if all(Z.block_is(ctx, (math.floor(e[0]), y, math.floor(e[2])), 'minecraft:air') for y in (G, G + 1)):
            target, eye = p, e
            break
    if target is None:
        raise RuntimeError('no RBMK debris on the ground with air on its far side; server debris %s'
                           % [tuple(round(v, 2) for v in p) for p in pos])
    inv0 = Z.inventory(ctx, a)
    n0 = Z.entity_count(ctx, DEB)
    ctx.step('key', client=a, key='key.keyboard.9', action='tap', after=2)
    ctx.step('view', client=a, eye=eye, look_at=[target[0], target[1] + 0.2, target[2]], fly=True, hide_gui=False)
    use = ctx.step('use', client=a, after=6)
    n1 = Z.entity_count(ctx, DEB)
    gained = _lib.delta(Z.inventory(ctx, a), inv0)
    picked = [k for k, v in gained.items() if v == 1 and k in DEB_ITEMS]
    client_items = {s['item'] for s in ctx.step('inv', client=a)['slots'] if s.get('item')}
    ok_pick = n1 == n0 - 1 and len(picked) == 1 and picked[0] in client_items

    # radiation per player (survival): A 48 and B 96 blocks east of the reactor centre on one line, so the ray from any wreck block
    # to either player's eyes crosses the same cells inside the reactor and only air outside; one radiating block that fires gives
    # B the share (lenA / lenB)^2 of A's gain (RBMKDebrisRadiatingBlock.java:92-118). One server tick at a time with both values
    # set to 0 before it, so no single reading comes near the lethal 1,000 (EntityEffectHandler.java:157; at 12 and 30 blocks an
    # unshielded block kills in one hit).
    ctx.rcon('clear %s' % a, 'clear %s' % b, 'gamemode survival %s' % a, 'gamemode survival %s' % b)
    spots = {a: (cx + RAD_AT[0], cz), b: (cx + RAD_AT[1], cz)}
    for who in (a, b):
        ctx.step('view', client=who, pos=[spots[who][0], G, spots[who][1]], look_at=[cx, G + 1, cz], fly=False, hide_gui=False)
    ctx.step('wait', client=a, ticks=40)
    near = {n: Z.entity_count(ctx, '@e[type=%srbmk_debris,x=%.1f,y=%d,z=%.1f,distance=..4]' % (H, spots[n][0], G, spots[n][1])) for n in (a, b)}
    places = {n: (Z.server_positions(ctx, n) or [None])[0] for n in (a, b)}
    eyes = {n: (places[n][0], places[n][1] + 1.62, places[n][2]) for n in (a, b) if places[n]}
    lo, hi = m['box']
    radiating = [(x, y, z) for x in range(lo[0], hi[0] + 1) for y in range(lo[1], hi[1] + 1) for z in range(lo[2], hi[2] + 1)
                 if Z.block_is(ctx, (x, y, z), H + 'pribris_radiating')]
    cands, same_cells = [], True
    for blk in radiating:
        c = (blk[0] + 0.5, blk[1] + 0.5, blk[2] + 0.5)
        la, ca = ray_cells(c, eyes[a])
        lb, cb = ray_cells(c, eyes[b])
        zone = lambda cells: [q for q in cells if lo[0] <= q[0] <= hi[0] and lo[2] <= q[2] <= hi[2]]
        same_cells = same_cells and zone(ca) == zone(cb)
        cands.append((blk, round(la, 4), round(lb, 4), (la / lb) ** 2))
    # potion effects from debris passed earlier contaminate every player tick, also in a frozen world: cleared first; what still comes
    # in while the world stands frozen (chunk radiation) is measured over 20 player ticks
    ctx.rcon('effect clear %s' % a, 'effect clear %s' % b, 'ntmprops set %s radiation 0' % a, 'ntmprops set %s radiation 0' % b)
    ctx.step('wait', client=a, ticks=20)
    bg = {n: Z.radiation(ctx, n) / 20.0 for n in (a, b)}
    first, steps, peak = None, 0, {a: 0.0, b: 0.0}
    for i in range(1, RAD_STEPS + 1):
        ctx.rcon('ntmprops set %s radiation 0' % a, 'ntmprops set %s radiation 0' % b)
        _lib.server_steps(ctx, 1)
        g = {n: Z.radiation(ctx, n) for n in (a, b)}
        peak = {n: max(peak[n], g[n]) for n in (a, b)}
        steps = i
        if first is None and g[a] > 20 * bg[a] + 1e-6:
            first = (i, g)
            break
    lines_now, _ = Z.log_lines(mark)
    deaths = [ln[:160] for ln in lines_now if ' died' in ln or 'was killed' in ln]
    ratio, ok_rad = None, False
    if first and cands:
        ga, gb = first[1][a], first[1][b]
        ratio = gb / ga if ga else None
        lo_r, hi_r = min(c[3] for c in cands), max(c[3] for c in cands)
        slack = 20 * bg[b] / ga if ga else 0
        ok_rad = (gb > 0 and ratio is not None and lo_r * (1 - 1e-3) - slack <= ratio <= hi_r * (1 + 1e-3) + slack and same_cells and not deaths)
    ctx.check(RX + 'mp-meltdown-sync', m['ok'] and ok_sync, '%s; %s' % (m['detail'], sync_detail))
    ctx.check(RX + 'mp-debris-pickup', ok_pick, 'pickup hit %s: server debris %d -> %d, A gained %s, A client holds %s'
              % (use.get('hit'), n0, n1, gained, sorted(client_items & DEB_ITEMS)))
    ctx.check(RX + 'mp-wreck-radiation', ok_rad,
              'server places %s, debris within 4 blocks of the spots %s, background per player tick %s, radiating wreck blocks with '
              '(lenA, lenB, (lenA/lenB)^2) %s, rays cross the same reactor cells %s; first tick with a wreck hit on A: step %s (limit %d '
              'single ticks, %d run), gains %s, B/A %s; highest single-tick readings %s; death lines in the server log %s'
              % (places, near, bg, [(c[0], c[1], c[2], round(c[3], 6)) for c in cands], same_cells, first and first[0], RAD_STEPS, steps,
                 first and first[1], ratio and round(ratio, 6), peak, deaths[:3]))

    lines, paths = Z.log_lines(mark)
    client_lines, other = Z.bad_log_lines(lines)
    ctx.not_run(RX + 'mp-overpressure-observe',
                'the overpressure branch (RBMKBaseBlockEntity.java:409-410 -> handleOverpressure :440-479, getBlockEntity at :458) runs only with '
                'dialEnableMeltdownOverpressure (RBMKDials.getOverpressure :129-131), false by default (CommonConfig.java:612-615; the original gamerule '
                'RBMKDials.java:36 is false too); turning it on needs an edit of the server\'s common config, which the authorization of these runs '
                'does not cover, so :458 was not reached. Observed around this meltdown '
                'without it: mean tick time %s ms before, %s ms after the meltdown tick; server log error lines %s, client-class lines %s'
                % (m['ms'][0], m['ms'][1], other[:3], client_lines[:3]))

    # a still state for the restart
    ctx.rcon('gamemode creative %s' % a, 'gamemode creative %s' % b)
    for who, dx in ((a, NEAR), (b, -NEAR)):
        ctx.step('view', client=who, pos=[cx + dx, G + 4, cz], look_at=[cx, G + 4, cz], fly=True, hide_gui=False)
    ctx.step('wait', client=a, ticks=40)

    def reads():
        out = still_counts(ctx, m['box'])
        out.update(debris=Z.entity_count(ctx, DEB), rad_a=Z.radiation(ctx, a), rad_b=Z.radiation(ctx, b))
        return out
    pre = reads()
    _lib.server_idle(ctx, a)
    ctx.restart_server()
    ctx.server('tick freeze')
    ctx.step('wait', client=a, ticks=80)
    post = reads()
    cmp = _lib.compare_static(pre, post)
    ctx.check(RX + 'mp-meltdown-restart', cmp['ok'], 'before %s, after %s; %s' % (pre, post, cmp['detail']))
    _lib.server_idle(ctx, a)
