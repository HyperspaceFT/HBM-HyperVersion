"""Dedicated server, ZIRNOX meltdown in its own disposable world: start isolation, the meltdown, its 72 debris on both clients,
a pickup on the server, and the schrabidium ore the meltdown makes out of uranium ore laid around the reactor.

Rig (one reactor, nothing else that ticks): the reactor is placed by hand (right-click, item put in the hand by command); 24
natural uranium rods are given by command and moved into the reactor by shift-clicks in its screen; the reactor has no
water and no CO2. It is switched on with the screen's control button in a frozen world, then the server runs `tick step`.

Expected values (original 1.7.10 TileEntityReactorZirnox / NEO ReactorZirnoxBlockEntity):
- every tick each rod decays (neighbouring rods + 1) times, 30 heat each (original TileEntityReactorZirnox.java:340-355,
  ItemZirnoxRod.java:102; NEO ReactorZirnoxBlockEntity.java:320-336, ZirnoxRodItem.java:81): a full core has 24 rods whose
  neighbour counts sum to 68, 92 decays, 2,760 heat a tick.
- without water or CO2 no steam is made and the heat drops by 10 a tick (original :240-249; NEO :182-191); pressure =
  2 x CO2 + heat x CO2 / 16,000 = 0. Heat after n ticks: 2,750 n while it is below 100,000. After 36 ticks 99,000; in tick 37
  the decay brings it to 101,760, the -10 is skipped (heat not below 100,000) and the meltdown follows (original :358-361;
  NEO :338-340).
- the meltdown replaces the reactor with zirnox_destroyed, explodes (12) and throws 72 debris: 2 exchanger, 20 concrete,
  20 blank, 10 element, 10 graphite, 10 shrapnel (original :386-417; NEO :366-416), then converts a jittered sphere of radius
  35 (ExplosionNukeGeneric.waste: cells with x^2 + y^2 + z^2 < 612 + rand(122); original ExplosionNukeGeneric.java:216-236,
  NEO ExplosionNukeGeneric.java:124-147): every uranium ore cell in it becomes schrabidium ore with chance 1/250, otherwise
  scorched uranium ore (original :306-312, NEO :248-255).
- debris pickup: right-click gives the matching debris item and removes the entity, on the server (original
  EntityZirnoxDebris.java:29-41; NEO ZirnoxDebris.java:66-73).
"""
import re
import sys
import threading
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402
import common  # noqa: E402

SCENARIO = dict(
    id='zirnox-reactor.mp_meltdown',
    feature='zirnox-reactor',
    title='Dedicated server: ZIRNOX meltdown, 72 debris on both clients, pickup, schrabidium ore from uranium ore',
    group='mp',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

G = _lib.FLAT_FEET
H = _lib.H
SITE = (40, 40)          # the block the reactor item is used on is (x, G - 1, z)
FIELD = 24               # uranium ore under the reactor: core x/z +-24, y = G - 3 .. G - 2 (the two dirt layers)
FAR = 100                # both players watch from this many blocks east and west of the core
NEAR = 20                # and come this close after the debris have landed
STEPS_BEFORE = 36        # ticks after switch-on with the reactor intact (heat 99,000)
HEAT_PER_TICK = 92 * 30 - 10
DEBRIS = dict(BLANK=20, ELEMENT=10, SHRAPNEL=10, GRAPHITE=10, CONCRETE=20, EXCHANGER=2)  # ZirnoxDebris.DebrisType order
DEBRIS_TYPES = list(DEBRIS)
DEBRIS_ITEMS = {H + 'debris_metal', H + 'debris_element', H + 'debris_shrapnel', H + 'debris_graphite', H + 'debris_concrete',
                H + 'debris_exchanger'}
CLIENT_ONLY = re.compile(r'NoClassDefFoundError|invalid dist|RuntimeDistCleaner|Attempted to load class .* for invalid dist|ClassNotFoundException')

ZX = 'zirnox-reactor.'
EXPECT = [
    ('mp-start-isolation', '专服：这个专服世界从开局到重启后的服务端日志里都没有 NoClassDefFoundError／invalid dist 或客户端类的加载错误'
     '（碎片渲染器、RT 发电机界面与渲染器只在客户端注册），期间两名客户端看着碎片飞行',
     'client-only registration; server log'),
    ('mp-meltdown-sync', '专服：手放的 ZIRNOX 装 24 根天然铀棒（命令发放）、无水无 CO2，控制键开机后第 36 刻热 99,000、仍完好，第 37 刻熔毁成 '
     'zirnox_destroyed；服务端有 72 个碎片（交换器 2、混凝土 20、空白 20、燃料元件 10、石墨 10、钢片 10），两个客户端各自看到 72 个；'
     '解冻飞行、再冻结、两人移到离核心 20 格处静置之后，每个客户端都有服务端上离它水平 126 格以内的每个碎片（客户端只收跟踪距离 128 格以内的碎片），'
     '位置与服务端相差不到 0.5 格，没有多出的碎片（飞行时每个客户端每帧的最大步长与回头次数写进说明）',
     'TileEntityReactorZirnox.java:218-258,340-361,386-417; ReactorZirnoxBlockEntity.java:141-211,320-340,366-416'),
    ('mp-debris-smooth', '专服（待人看，用户站点）：碎片在客户端上飞行与落地时平滑校正、不跳不抖；这只能人看，执行器只把两个客户端每帧的最大步长与回头次数'
     '写进说明，不判定。要人看的原因：原版碎片没有自己的客户端插值代码，客户端上的位置由原版的实体跟踪包与客户端插值决定（以跟踪距离 1000、'
     '带速度更新注册），NEO 用 1.21 的实体跟踪；两版都没有给“平滑”定一个数，每帧步长多大、回头几次算跳或抖，从代码推不出可以自动判定的界限，'
     '只能看画面判断', 'EntityMappings.java:134, EntityDebrisBase.java:219-225; NtmEntityTypes.java:108, DebrisBase.java:43-48'),
    ('mp-debris-pickup', '专服：A 右键一个落地的碎片：服务端少一个碎片、A 的服务端背包多一个对应的碎片物品，A 的客户端背包也有它',
     'EntityZirnoxDebris.java:29-41; ZirnoxDebris.java:66-73'),
    ('mp-schrab-ore', '熔毁世界里顺带数施拉比矿：反应堆下方两层泥土换成铀矿（命令搭建），熔毁后数这一区里的施拉比矿、烧焦铀矿与剩下的铀矿；'
     '被转换的格数 N = 施拉比矿 + 烧焦铀矿至少 3,000（转换球取 x²+y²+z² < 612 + rand(122)，两层矿 y = −2、−3、|x|,|z| ≤ 24 里一定在球内的有 1,901 + 1,893 = 3,794 格，'
     '再给 12 级爆炸可能炸掉的格子留出余量），每格 1/250 变成施拉比矿，期望至少 1 块；'
     '一块都不变的概率是 (249/250)^N（N = 3,000 时约 6e-6），写进说明',
     'ExplosionNukeGeneric.java:216-236,306-312; NEO ExplosionNukeGeneric.java:124-147,248-255'),
    ('mp-meltdown-restart', '专服重启后（静止、非默认的服务端读数）：核心仍是 zirnox_destroyed，碎片个数、施拉比矿、烧焦铀矿与铀矿的个数与重启前相同',
     'entity and chunk save'),
]


def expectations():
    return [dict(id=ZX + k, text=t, source=s) for k, t, s in EXPECT]


# ---------------------------------------------------------------- dedicated-server helpers (the sibling mp files import these)

def rcon1(ctx, command):
    return (ctx.rcon(command)[0] or '').strip()


def entity_count(ctx, selector):
    """Number of entities a selector finds on the server (`execute if entity`: "Test passed, count: N" / "Test failed")."""
    m = re.search(r'count:\s*(\d+)', rcon1(ctx, 'execute if entity %s' % selector))
    return int(m.group(1)) if m else 0


def server_positions(ctx, selector):
    """Server positions of every entity the selector finds."""
    r = rcon1(ctx, 'execute as %s run data get entity @s Pos' % selector)
    return [tuple(float(v) for v in m) for m in re.findall(r'\[(-?[\d.Ee+-]+)d, (-?[\d.Ee+-]+)d, (-?[\d.Ee+-]+)d\]', r)]


def block_is(ctx, pos, spec):
    """`execute if block` over RCON (ctx.server gives no result value on a dedicated server)."""
    return 'passed' in rcon1(ctx, 'execute if block %d %d %d %s' % (pos[0], pos[1], pos[2], spec))


def inventory(ctx, name):
    """Counter(item id[@meta] -> count) of a player's server inventory."""
    r = rcon1(ctx, 'data get entity %s Inventory' % name)
    out = Counter()
    try:
        value = _lib.data_value(r)
    except Exception:  # noqa: BLE001 - an empty or unexpected reply is an empty inventory
        return out
    for entry in value if isinstance(value, list) else []:
        out[_lib.stack_key(entry)] += entry.get('count', 1)
    return out


def radiation(ctx, name):
    """The player's radiation (HbmLivingAttachments) from `ntmprops get NAME radiation`: the last number of the reply."""
    nums = re.findall(r'-?\d+(?:\.\d+)?(?:[Ee]-?\d+)?', rcon1(ctx, 'ntmprops get %s radiation' % name).split(' ')[-1])
    if not nums:
        raise RuntimeError('no radiation value for %s' % name)
    return float(nums[-1])


def hand(ctx, who, item):
    """Selects hotbar slot 1 on the client and puts `item` there by command (a machine handed out directly)."""
    ctx.step('key', client=who, key='key.keyboard.1', action='tap', after=2)
    ctx.rcon('item replace entity %s hotbar.0 with %s' % (who, item))
    ctx.step('wait', client=who, ticks=4)


def place_by_hand(ctx, who, item, x, z, find, box):
    """`who` stands 4.5 blocks south of (x, G - 1, z), looks at its top and right-clicks with `item` in the hand; returns the core
    of `find` in the box (client view of the placed blocks)."""
    hand(ctx, who, item)
    ctx.step('view', client=who, pos=[x + 0.5, G, z + 4.5], look_at=[x + 0.5, G - 0.5, z + 0.5], fly=True, hide_gui=False)
    ctx.step('use', client=who, target=dict(pos=[x, G - 1, z], face='up'), after=8)
    ctx.rcon('item replace entity %s hotbar.0 with minecraft:air' % who)
    d = ctx.step('dump', client=who, **{'from': list(box[0]), 'to': list(box[1])})
    cores = [tuple(int(c) for c in b['pos']) for b in d['blocks'] if b['block'] == find and b['props'].get('type', 'core') == 'core']
    if len(cores) != 1:
        raise RuntimeError('%s: expected one core, found %s' % (find, cores))
    return cores[0]


def open_screen(ctx, who, pos, face, stand, expect):
    """Empty hand (hotbar slot 9 kept empty), right-click aimed at `face` of the block at pos from `stand` (any part of a
    multiblock opens the core's screen), wait for the screen; returns the hud read (gui_left / gui_top)."""
    ctx.step('key', client=who, key='key.keyboard.9', action='tap', after=2)
    look = _lib.face_point(pos, face)
    ctx.step('view', client=who, pos=list(stand), look_at=look, fly=True, hide_gui=False)
    ctx.step('use', client=who, target=dict(pos=list(pos), face=face), any_hit=True, after=6)
    ctx.step('screen', client=who, expect=expect)
    return ctx.step('hud', client=who, frames=2)


def click_at(ctx, who, hud, dx, dy, button=0):
    """A click at GUI coordinates relative to the screen's origin."""
    return ctx.step('mouse', client=who, at=[hud['gui_left'] + dx, hud['gui_top'] + dy], button=button, action='click', after=4)


def shift_click(ctx, who, slot):
    ctx.step('mod', client=who, shift=True)
    try:
        return ctx.step('click', client=who, slot=slot, after=4)
    finally:
        ctx.step('mod', client=who, shift=False)


def both(ctx, fn):
    """Runs fn(name) for both clients at the same time (two threads; each client has its own step channel)."""
    names = list(ctx.channels)
    out, errors = {}, {}

    def go(n):
        try:
            out[n] = fn(n)
        except Exception as e:  # noqa: BLE001 - re-raised below
            errors[n] = e
    threads = [threading.Thread(target=go, args=(n,)) for n in names]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    if errors:
        raise next(iter(errors.values()))
    return out


def client_entities(ctx, who, center, radius, etype, ticks=3):
    """The entities of `etype` the client holds within `radius` of center (a short track step): [dict(id, last, max_step, reversals)]."""
    r = ctx.step('track', client=who, center=list(center), radius=radius, type=etype, ticks=ticks)
    return r.get('entities', [])


def log_mark():
    """(log path, line count) of the dedicated server's log now."""
    session = common.read_json(common.SESSION)
    log = Path(session['log']) if session else None
    return log, (len(log.read_text(encoding='utf-8', errors='replace').splitlines()) if log and log.exists() else 0)


def log_lines(mark):
    """Server log lines written since `mark`, including the whole log of a server started by a restart."""
    log, start = mark
    session = common.read_json(common.SESSION)
    out = []
    paths = [(log, start)] if log else []
    new = Path(session['log']) if session else None
    if new and new != log:
        paths.append((new, 0))
    for path, first in paths:
        if path.exists():
            out += path.read_text(encoding='utf-8', errors='replace').splitlines()[first:]
    return out, [str(p) for p, _ in paths]


def bad_log_lines(lines):
    """(client-class lines, other Exception/ERROR lines) of a server log; a client that quits for a restart resets its socket,
    those lines are left out."""
    client, other = [], []
    for i, line in enumerate(lines):
        if CLIENT_ONLY.search(line):
            client.append(line[:200])
        elif re.search(r'Exception|\bERROR\b|/ERROR\]', line):
            reset = 'Connection reset' in line or (i + 1 < len(lines) and 'Connection reset' in lines[i + 1])
            if not reset:
                other.append(line[:200])
    return client, other


def nearest(points, p):
    return min((sum((a - b) ** 2 for a, b in zip(q, p)) ** 0.5 for q in points), default=None)


def match_positions(server, client):
    """Largest distance from a server position to the nearest client position (None when either list is empty)."""
    if not server or not client:
        return None
    return max(nearest(client, s) for s in server)


def in_range(points, seat, near=126, far=130):
    """(points within `near` blocks horizontally of seat (x, z), number between near and far): a client is sent the entities within
    its tracking range (ChunkMap.TrackedEntity.updatePlayer measures the horizontal distance), so the ones in the band may or may
    not be there."""
    d = [((p[0] - seat[0]) ** 2 + (p[2] - seat[1]) ** 2) ** 0.5 for p in points]
    return [p for p, x in zip(points, d) if x <= near], sum(1 for x in d if near < x <= far)


def clone_count(ctx, lo, hi, block):
    """Number of `block` cells in lo..hi on the server: a filtered clone to the air 60 blocks up counts them without touching the
    source; the copy is cleared again."""
    dy = 60
    r = rcon1(ctx, 'clone %d %d %d %d %d %d %d %d %d filtered %s' % (lo + hi + (lo[0], lo[1] + dy, lo[2], block)))
    ctx.rcon('fill %d %d %d %d %d %d minecraft:air' % (lo[0], lo[1] + dy, lo[2], hi[0], hi[1] + dy, hi[2]))
    m = re.search(r'cloned (\d+)', r)
    return int(m.group(1)) if m else 0


# ---------------------------------------------------------------- the scenario

def debris_by_type(ctx):
    return {t: entity_count(ctx, '@e[type=%szirnox_debris,nbt={debtype:%d}]' % (H, i)) for i, t in enumerate(DEBRIS_TYPES)}


def ore_counts(ctx, core):
    lo = (core[0] - FIELD, G - 3, core[2] - FIELD)
    hi = (core[0] + FIELD, G - 2, core[2] + FIELD)
    return {b: clone_count(ctx, lo, hi, H + b) for b in ('ore_schrabidium', 'ore_uranium_scorched', 'ore_uranium')}


def setup_world(ctx, a, b):
    ctx.rcon('gamemode creative %s' % a, 'gamemode creative %s' % b, 'time set 6000', 'weather clear', 'gamerule doDaylightCycle false',
             'gamerule doMobSpawning false', 'gamerule doWeatherCycle false', 'clear %s' % a, 'clear %s' % b)


def build_and_melt(ctx, a, b, site=SITE, ore=False):
    """The rig of the module docstring up to the meltdown: A places the reactor and loads 24 rods by shift-clicks, the world is
    frozen, the control button switches it on, both players go FAR blocks east and west, then 36 ticks (intact, heat 99,000) and
    one more (meltdown). Returns the readings as a dict; the world stays frozen."""
    x, z = site
    ctx.step('view', client=b, pos=[x + 0.5, G, z + 12.5], look_at=[x + 0.5, G, z + 0.5], fly=True, hide_gui=False)
    core = place_by_hand(ctx, a, H + 'machine_zirnox', x, z, H + 'machine_zirnox', ((x - 6, G, z - 8), (x + 6, G + 5, z + 2)))
    cx, cy, cz = core
    filled = None
    if ore:
        filled = rcon1(ctx, 'fill %d %d %d %d %d %d %sore_uranium' % (cx - FIELD, G - 3, cz - FIELD, cx + FIELD, G - 2, cz + FIELD, H))
    # the reactor occupies core +-2 in x and z; the screen opens from any of its blocks
    hud = open_screen(ctx, a, (cx, cy, cz + 2), 'south', [cx + 0.5, G, cz + 5.5], 'ReactorZirnoxScreen')
    ctx.rcon('give %s %srod_zirnox 24' % (a, H))
    ctx.step('wait', client=a, ticks=10)
    for s in range(24):  # player slots 0-23 hold one rod each; menu: 28 reactor slots, main 28-54, hotbar 55-63
        shift_click(ctx, a, _lib.menu_slot(28, s))
    data = _lib.block_data(ctx, core)
    rods = sum(1 for it in data.get('Items', []) if it.get('Slot', 99) < 24 and it.get('id') == H + 'rod_zirnox')
    ctx.server('tick freeze')
    click_at(ctx, a, hud, 151, 42)  # ReactorZirnoxScreen.mouseClicked: the control button at (144, 35), 14 x 14
    on = _lib.block_data(ctx, core).get('isOn')
    ctx.step('close', client=a)
    for who, dx in ((a, FAR), (b, -FAR)):
        ctx.step('view', client=who, pos=[cx + dx + 0.5, G + 4, cz + 0.5], look_at=[cx + 0.5, G + 4, cz + 0.5], fly=True, hide_gui=False)
    ctx.step('wait', client=a, ticks=20)
    t0 = ctx.server()['game_time']
    _lib.server_steps(ctx, STEPS_BEFORE)
    before = _lib.block_data(ctx, core)
    intact = block_is(ctx, core, H + 'machine_zirnox')
    t1 = ctx.server()['game_time']
    _lib.server_steps(ctx, 1)
    t2 = ctx.server()['game_time']
    melted = block_is(ctx, core, H + 'zirnox_destroyed')
    kinds = debris_by_type(ctx)
    total = entity_count(ctx, '@e[type=%szirnox_debris]' % H)
    ok = (rods == 24 and bool(on) and t1 - t0 == STEPS_BEFORE and before.get('heat') == STEPS_BEFORE * HEAT_PER_TICK
          and before.get('pressure') == 0 and intact and t2 - t1 == 1 and melted and kinds == DEBRIS and total == 72)
    detail = ('rods in the reactor %d; isOn after the button %s; after %d ticks heat %s pressure %s (expected %d, 0), intact %s; tick %d: '
              'destroyed %s; debris by type %s (expected %s), total %d'
              % (rods, on, t1 - t0, before.get('heat'), before.get('pressure'), STEPS_BEFORE * HEAT_PER_TICK, intact, t2 - t0, melted, kinds,
                 DEBRIS, total))
    return dict(core=core, ok=ok, detail=detail, filled=filled, total=total)


def run(ctx):
    a, b = list(ctx.channels)
    mark = log_mark()
    setup_world(ctx, a, b)
    m = build_and_melt(ctx, a, b, ore=True)
    core = m['core']
    cx, cy, cz = core
    filled = m['filled']
    ctx.step('wait', client=a, ticks=20)
    above = (cx + 0.5, cy + 4, cz + 0.5)
    seen0 = both(ctx, lambda n: len(client_entities(ctx, n, above, 6, H + 'zirnox_debris')))

    # flight: unfrozen for 120 ticks while both clients record the debris, then frozen and settled
    def fly(n):
        return client_entities(ctx, n, above, 90, H + 'zirnox_debris', ticks=120)
    ctx.server('tick unfreeze')
    flight = both(ctx, fly)
    ctx.server('tick freeze')
    # a client holds only the debris within 128 blocks of it (EntityType clientTrackingRange 8 chunks; the original renders debris
    # only within 128 blocks, EntityDebrisBase.java:221-225): both players come to 20 blocks from the core before the comparison
    for who, dx in ((a, NEAR), (b, -NEAR)):
        ctx.step('view', client=who, pos=[cx + dx + 0.5, G + 4, cz + 0.5], look_at=[cx + 0.5, G + 4, cz + 0.5], fly=True, hide_gui=False)
    ctx.step('wait', client=a, ticks=80)
    server_pos = server_positions(ctx, '@e[type=%szirnox_debris]' % H)
    spread = max(((p[0] - cx) ** 2 + (p[2] - cz) ** 2) ** 0.5 for p in server_pos) if server_pos else None
    rest = both(ctx, lambda n: client_entities(ctx, n, above, 200, H + 'zirnox_debris'))
    seat = {a: (cx + NEAR + 0.5, cz + 0.5), b: (cx - NEAR + 0.5, cz + 0.5)}
    tracked = {n: in_range(server_pos, seat[n]) for n in (a, b)}
    dev = {n: match_positions(tracked[n][0], [tuple(e['last']) for e in rest[n]]) for n in (a, b)}
    flight_stats = {n: (max((e['max_step'] for e in flight[n]), default=0), sum(e['reversals'] for e in flight[n])) for n in (a, b)}

    # pickup by A: the debris nearest to the core on the ground
    target = min(server_pos, key=lambda p: (p[0] - cx) ** 2 + (p[2] - cz) ** 2)
    inv0 = inventory(ctx, a)
    n0 = len(server_pos)
    ctx.step('key', client=a, key='key.keyboard.9', action='tap', after=2)
    ctx.step('view', client=a, eye=[target[0] + 2.0, target[1] + 0.25, target[2]], look_at=[target[0], target[1] + 0.2, target[2]], fly=True,
             hide_gui=False)
    use = ctx.step('use', client=a, after=6)
    n1 = entity_count(ctx, '@e[type=%szirnox_debris]' % H)
    gained = _lib.delta(inventory(ctx, a), inv0)
    client_inv = ctx.step('inv', client=a)
    client_items = {s['item'] for s in client_inv['slots'] if s.get('item')}
    picked = [k for k, v in gained.items() if v == 1 and k in DEBRIS_ITEMS]

    sync_ok = (m['ok'] and seen0 == {a: 72, b: 72}
               and all(len(tracked[n][0]) <= len(rest[n]) <= len(tracked[n][0]) + tracked[n][1] for n in (a, b))
               and all(dev[n] is not None and dev[n] < 0.5 for n in (a, b)))
    ctx.check(ZX + 'mp-meltdown-sync', sync_ok,
              '%s; clients right after: %s; after the flight and settling: server %d, clients %s, server debris within 126 / between 126 and '
              '130 blocks of each client %s, largest distance to the server position %s (debris lie up to %s blocks from the core); '
              'flight max step / reversals per client %s'
              % (m['detail'], seen0, len(server_pos), {n: len(rest[n]) for n in (a, b)}, {n: (len(tracked[n][0]), tracked[n][1]) for n in (a, b)},
                 {n: dev[n] and round(dev[n], 3) for n in (a, b)}, spread and round(spread, 1),
                 {n: (round(mx, 3), r) for n, (mx, r) in flight_stats.items()}))
    ctx.check(ZX + 'mp-debris-pickup', n1 == n0 - 1 and len(picked) == 1 and picked[0] in client_items,
              'pickup hit %s: server debris %d -> %d, A gained %s, A client holds %s'
              % (use.get('hit'), n0, n1, gained, sorted(client_items & DEBRIS_ITEMS)))
    ctx.review(ZX + 'mp-debris-smooth', 'for a person at the user station: neither version has client code or a number of its own for smooth '
               'debris motion (vanilla entity tracking and interpolation), so no bound for a step or a reversal follows from the code; '
               'flight max step / reversals per client recorded by the executor %s'
               % {n: (round(mx, 3), r) for n, (mx, r) in flight_stats.items()})

    counts = ore_counts(ctx, core)
    n_conv = counts['ore_schrabidium'] + counts['ore_uranium_scorched']
    p_none = (249 / 250.0) ** n_conv
    ctx.check(ZX + 'mp-schrab-ore', n_conv >= 3000 and counts['ore_schrabidium'] >= 1,
              'ore laid: %s; after the meltdown: schrabidium ore %d, scorched uranium ore %d, uranium ore left %d; converted N = %d; '
              '(want N >= 3000); expected about N / 250 = %.1f schrabidium ore; P(none) = (249/250)^N = %.3g'
              % (filled, counts['ore_schrabidium'], counts['ore_uranium_scorched'], counts['ore_uranium'], n_conv, n_conv / 250.0, p_none))

    pre = dict(core=block_is(ctx, core, H + 'zirnox_destroyed'), debris=entity_count(ctx, '@e[type=%szirnox_debris]' % H), **counts)
    _lib.server_idle(ctx, a)
    ctx.restart_server()
    ctx.server('tick freeze')
    for who, dx in ((a, FAR), (b, -FAR)):
        ctx.step('view', client=who, pos=[cx + dx + 0.5, G + 4, cz + 0.5], look_at=[cx + 0.5, G + 4, cz + 0.5], fly=True, hide_gui=False)
    ctx.step('wait', client=a, ticks=80)
    post = dict(core=block_is(ctx, core, H + 'zirnox_destroyed'), debris=entity_count(ctx, '@e[type=%szirnox_debris]' % H), **ore_counts(ctx, core))
    cmp = _lib.compare_static({k: int(v) for k, v in pre.items()}, {k: int(v) for k, v in post.items()}, not_quantity=('core',))
    ctx.check(ZX + 'mp-meltdown-restart', cmp['ok'] and pre['core'], 'before %s, after %s; %s' % (pre, post, cmp['detail']))
    lines, paths = log_lines(mark)
    client_lines, other = bad_log_lines(lines)
    ctx.check(ZX + 'mp-start-isolation', bool(paths) and bool(lines) and not client_lines,
              'server logs %s (%d lines from the start of this world through the restart): client-class lines %s; other error lines (listed, '
              'not judged here) %s' % (paths, len(lines), client_lines[:3], other[:5]))
    _lib.server_idle(ctx, a)
