"""Dedicated server, ZIRNOX meltdown in its own disposable world: the contamination and the wreck are the same for two players,
and the wreck's radiation is worked out for each player on his own.

The reactor rig and the meltdown are those of zirnox-reactor/mp_meltdown.py (its build_and_melt). Then the debris fly for
120 ticks and the world is frozen again.

Expected (original 1.7.10 / NEO):
- the wreck (zirnox_destroyed, the reactor's 5 x 5 x 2 box: dimensions {1, 0, 2, 2, 2, 2}, original
  TileEntityReactorZirnox.java:411-413, NEO ReactorZirnoxBlockEntity.java:404-407) and the ground the waste sphere converted
  (grass -> waste earth, original ExplosionNukeGeneric.java:246-247, NEO ExplosionNukeGeneric.java:175-176) are ordinary blocks:
  both clients hold the same blocks as the server.
- the wreck radiates every living entity within 100 blocks each tick with rads / res / len^2, where len is the distance from
  the wreck's centre to the entity's eyes and res the summed explosion resistance of the blocks at whole-block steps along that
  line (original TileEntityZirnoxDestroyed.java:58-95; NEO ZirnoxDestroyedBlockEntity.java:77-111). Two survival players on lines
  that cross the same blocks (two wreck cells, then air) therefore gain wreck radiation in the ratio lenB^2 / lenA^2, whatever the
  wreck's resistance and fire state; creative players gain nothing (original ContaminationUtil.java:284-285, NEO
  ContaminationUtil.java:177-180).
- the wreck also lets meltdown gas out (original ZirnoxDestroyed.updateTick, NEO ZirnoxDestroyedBlock.java:62-79); the gas raises
  chunk radiation (NEO GasMeltdownBlock.java:78-80), which spreads chunk by chunk every 20 ticks and reaches every living entity
  as chunk value / 20 a tick (NEO EntityEffectHandler.java:189-195), and gas a player stands in adds 0.5 a tick (NEO
  GasMeltdownBlock.java:33-36). Near the wreck both swamp the ratio, so the two players stand 48 and 96 blocks out, where the
  Geiger counter reads no chunk radiation before and after, with no gas block in their own cells.
"""
import importlib.util
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

_spec = importlib.util.spec_from_file_location('zirnox_mp_rig', Path(__file__).with_name('mp_meltdown.py'))
Z = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(Z)

SCENARIO = dict(
    id='zirnox-reactor.mp_contamination',
    feature='zirnox-reactor',
    title='Dedicated server: ZIRNOX wreck and waste ground the same on both clients, wreck radiation per player',
    group='mp',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

G = Z.G
H = Z.H
WASTE = 27          # the ground layer core +-27 holds every cell the waste sphere can reach (612 + 121 < 28^2)
DIST = (48, 96)     # A's and B's distance from the core along an axis: three and six chunks out, inside the wreck's 100 blocks
TICKS = 100
EYE = 1.62

ZX = 'zirnox-reactor.'
EXPECT = [
    ('mp-contamination', '专服：熔毁后两个客户端看到的残骸（zirnox_destroyed，5×5×2 共 50 格）与地面污染'
     '（核心 ±27 的地面层里的废土）逐格相同，并与服务端的格数相同',
     'TileEntityReactorZirnox.java:411-413, ExplosionNukeGeneric.java:246-247; ReactorZirnoxBlockEntity.java:404-407, ExplosionNukeGeneric.java:175-176'),
    ('mp-wreck-radiation', '专服：两人切到生存，A 站在核心一侧 48 格、B 站在 96 格（残骸的 100 格辐射范围内、'
     '离气体与区块辐射较远），两条视线都只穿过两格残骸、其余是空气（逐格在服务端核对），旁边 4 格内没有燃料元件与石墨碎片，两人所在格没有熔毁气体，'
     '盖革计数器在走刻前后读到两人所在区块的辐射都是 0.0；先清掉两人身上的状态效果，冻结世界里先静置 100 个玩家刻量本底，'
     '再走 100 刻（残骸着火状态前后相同），两人的辐射（减去本底）都上涨，B 的涨幅'
     '等于 A 的涨幅乘 lenA²/lenB²（len 是残骸中心到眼睛的距离，按两人的服务端位置算；单精度累加，相对误差不超过 0.1%），说明每人各算各的',
     'TileEntityZirnoxDestroyed.java:58-95; ZirnoxDestroyedBlockEntity.java:77-111, ContaminationUtil.java:167-189, EntityEffectHandler.java:189-195'),
    ('mp-contamination-restart', '专服重启后（两人先移到 100 格外，静止、非默认的服务端读数）：残骸格数与两人的辐射值与重启前相同（废土会被区块辐射继续转化，不是静止量）',
     'block and player save'),
]


def expectations():
    return [dict(id=ZX + k, text=t, source=s) for k, t, s in EXPECT]


def blocks_of(dump):
    return sorted((tuple(int(c) for c in d['pos']), d['block']) for d in dump['blocks'])


def server_pos(ctx, name):
    p = Z.server_positions(ctx, name)
    return p[0] if p else None


def ray_cells(center, eye):
    """The block cells at whole-block steps i = 1 .. len-1 along the line (ZirnoxDestroyedBlockEntity.radiate)."""
    v = [eye[i] - center[i] for i in range(3)]
    n = math.sqrt(sum(c * c for c in v))
    u = [c / n for c in v]
    cells = []
    i = 1
    while i < n:
        cells.append(tuple(math.floor(center[k] + u[k] * i) for k in range(3)))
        i += 1
    return n, cells


def ray_ok(ctx, core, cells):
    """Two wreck cells first, then air: checked on the server cell by cell."""
    wreck = [c for c in cells if abs(c[0] - core[0]) <= 2 and abs(c[2] - core[2]) <= 2 and core[1] <= c[1] <= core[1] + 1]
    rest = [c for c in cells if c not in wreck]
    return (len(wreck) == 2 and all(Z.block_is(ctx, c, H + 'zirnox_destroyed') for c in wreck)
            and all(Z.block_is(ctx, c, 'minecraft:air') for c in rest)), len(wreck), len(rest)


def chunk_reading(ctx, who, prefix):
    """Uses the Geiger counter in hotbar slot 1 and returns the chunk radiation number of the reply (ContaminationUtil.java:72-95)."""
    ctx.step('key', client=who, key='key.keyboard.1', action='tap', after=2)
    said = ctx.step('use', client=who, after=6)
    c = ctx.step('chat', client=who, count=12, since_ms=said['started_ms'], allow_fail=True)
    for line in [m['text'] for m in c.get('messages', [])]:
        if prefix and prefix in line:
            found = re.search(r'(-?\d+(?:\.\d+)?)', line[line.index(prefix) + len(prefix):])
            if found:
                return float(found.group(1)), line
    return None, None


def run(ctx):
    a, b = list(ctx.channels)
    Z.setup_world(ctx, a, b)
    m = Z.build_and_melt(ctx, a, b)
    core = m['core']
    cx, cy, cz = core
    ctx.server('tick unfreeze')
    ctx.step('wait', client=a, ticks=120)
    ctx.server('tick freeze')
    for who, dx in ((a, Z.NEAR), (b, -Z.NEAR)):
        ctx.step('view', client=who, pos=[cx + dx + 0.5, G + 4, cz + 0.5], look_at=[cx + 0.5, G + 4, cz + 0.5], fly=True, hide_gui=False)
    ctx.step('wait', client=a, ticks=80)

    wreck_box = dict(**{'from': [cx - 3, cy, cz - 3], 'to': [cx + 3, cy + 2, cz + 3]})
    ground_box = dict(**{'from': [cx - WASTE, G - 1, cz - WASTE], 'to': [cx + WASTE, G - 1, cz + WASTE]})
    wreck = Z.both(ctx, lambda n: blocks_of(ctx.step('dump', client=n, **wreck_box)))
    ground = Z.both(ctx, lambda n: blocks_of(ctx.step('dump', client=n, **ground_box)))
    wreck_server = Z.clone_count(ctx, (cx - 3, cy, cz - 3), (cx + 3, cy + 2, cz + 3), H + 'zirnox_destroyed')
    waste_server = Z.clone_count(ctx, (cx - WASTE, G - 1, cz - WASTE), (cx + WASTE, G - 1, cz + WASTE), H + 'waste_earth')
    wreck_client = {n: sum(1 for _, blk in wreck[n] if blk == H + 'zirnox_destroyed') for n in (a, b)}
    waste_client = {n: sum(1 for _, blk in ground[n] if blk == H + 'waste_earth') for n in (a, b)}
    same_blocks = wreck[a] == wreck[b] and ground[a] == ground[b] and wreck_client[a] == wreck_server == 50 and waste_client[a] == waste_server > 0

    ctx.check(ZX + 'mp-contamination', m['ok'] and same_blocks,
              '%s; wreck cells: clients %s, server %d (want 50); waste earth: clients %s, server %d; client block lists equal: wreck %s, ground %s'
              % (m['detail'], wreck_client, wreck_server, waste_client, waste_server, wreck[a] == wreck[b], ground[a] == ground[b]))

    # two standing places on axis lines, clear of radiating debris (element and graphite give a radiation effect within 2.5 blocks)
    center = (cx + 0.5, cy + 0.5, cz + 0.5)
    chosen = {}
    for who, dist in ((a, DIST[0]), (b, DIST[1])):
        for d in ((1, 0), (0, 1), (-1, 0), (0, -1)):
            spot = (cx + d[0] * dist + 0.5, G, cz + d[1] * dist + 0.5)
            hot = sum(Z.entity_count(ctx, '@e[type=%szirnox_debris,nbt={debtype:%d},x=%.1f,y=%d,z=%.1f,distance=..4]' % (H, t, spot[0], G, spot[2]))
                      for t in (1, 3))
            n, cells = ray_cells(center, (spot[0], G + EYE, spot[2]))
            good, nw, na = ray_ok(ctx, core, cells)
            if hot == 0 and good:
                chosen[who] = (d, spot)
                break
    ctx.rcon('gamemode survival %s' % a, 'gamemode survival %s' % b)
    for who in (a, b):
        if who in chosen:
            spot = chosen[who][1]
            ctx.step('view', client=who, pos=list(spot), look_at=[cx + 0.5, cy + 0.5, cz + 0.5], fly=False, hide_gui=False)
    ctx.step('wait', client=a, ticks=40)
    places = {n: server_pos(ctx, n) for n in (a, b)}
    rays = {}
    for n in (a, b):
        p = places[n]
        if p is None:
            continue
        ln, cells = ray_cells(center, (p[0], p[1] + EYE, p[2]))
        rays[n] = (ln,) + ray_ok(ctx, core, cells)
    # meltdown gas in the players' own cells (0.5 a tick each, GasMeltdownBlock.java:33-36) and the chunk radiation where they stand
    gas = {n: [c for c in ((math.floor(places[n][0]), math.floor(places[n][1]) + k, math.floor(places[n][2])) for k in (0, 1))
               if not Z.block_is(ctx, c, 'minecraft:air')] if places[n] else None for n in (a, b)}
    # I18n.get without arguments answers 'Format error: <pattern>'; the text before the placeholder is what the chat line starts with
    prefix = ctx.step('i18n', client=a, keys=['geiger.chunkRad'])['texts']['geiger.chunkRad'].split('Format error: ')[-1].split('%s')[0]
    for who in (a, b):
        ctx.rcon('item replace entity %s hotbar.0 with %sgeiger_counter' % (who, H))
    chunk_before = {n: chunk_reading(ctx, n, prefix) for n in (a, b)}
    # potion effects picked up near radiating debris earlier (RadiationEffect contaminates every player tick, also in a frozen
    # world) are cleared; what still comes in while the world stands frozen is measured over as many player ticks and taken off
    effects = {n: Z.rcon1(ctx, 'data get entity %s active_effects' % n)[-160:] for n in (a, b)}
    ctx.rcon('effect clear %s' % a, 'effect clear %s' % b, 'ntmprops set %s radiation 0' % a, 'ntmprops set %s radiation 0' % b)
    r0 = {n: Z.radiation(ctx, n) for n in (a, b)}
    ctx.step('wait', client=a, ticks=TICKS)
    rb = {n: Z.radiation(ctx, n) for n in (a, b)}
    fire0 = _lib.block_data(ctx, core).get('onFire')
    _lib.server_steps(ctx, TICKS)
    fire1 = _lib.block_data(ctx, core).get('onFire')
    r1 = {n: Z.radiation(ctx, n) for n in (a, b)}
    chunk_after = {n: chunk_reading(ctx, n, prefix) for n in (a, b)}
    background = {n: rb[n] - r0[n] for n in (a, b)}
    gain = {n: (r1[n] - rb[n]) - background[n] for n in (a, b)}
    no_chunk = all(chunk_before[n][0] == 0.0 and chunk_after[n][0] == 0.0 for n in (a, b))
    no_gas = all(gas[n] == [] for n in (a, b))
    ratio_ok = False
    want = None
    if len(rays) == 2 and gain[a] > 0:
        want = gain[a] * rays[a][0] ** 2 / rays[b][0] ** 2
        ratio_ok = gain[b] > 0 and abs(gain[b] - want) <= 1e-3 * want
    # for the record only: the wreck term per player from the formula, with the original's effective 1.7.10 resistance
    # 800 * 3 / 5 = 480 per wreck cell (setResistance(800), ModBlocks.java:2241), which NEO's block has too (NtmBlocks.java:434)
    rads = 500000.0 if fire0 in (1, True) else 75000.0
    formula = {n: round(TICKS * rads / 960 / rays[n][0] ** 2, 4) for n in rays}
    ctx.check(ZX + 'mp-wreck-radiation', m['ok'] and len(chosen) == 2 and all(r[1] for r in rays.values()) and no_gas
              and no_chunk and fire0 == fire1 and ratio_ok,
              'places (direction, spot) %s; server positions %s; rays (len, clear, wreck cells, air cells) %s; non-air in the '
              'players\' cells %s; Geiger chunk radiation before %s, after %s; wreck onFire before %s, after %s; effects before clearing %s; '
              'radiation %s, after %d frozen player ticks %s (background %s), after %d world ticks %s: gains %s; B expected %s; '
              'formula wreck terms (not judged) %s'
              % (chosen, places, {n: (round(r[0], 3),) + r[1:] for n, r in rays.items()}, gas, chunk_before, chunk_after, fire0, fire1, effects,
                 r0, TICKS, rb, background, TICKS, r1, gain, want, formula))

    # a still state for the restart: both players beyond the wreck's 100-block range, in creative
    ctx.rcon('gamemode creative %s' % a, 'gamemode creative %s' % b)
    for who, dx in ((a, 130), (b, -130)):
        ctx.step('view', client=who, pos=[cx + dx + 0.5, G + 4, cz + 0.5], look_at=[cx + 0.5, G + 4, cz + 0.5], fly=True, hide_gui=False)
    ctx.step('wait', client=a, ticks=40)

    def reads():
        return dict(wreck=Z.clone_count(ctx, (cx - 3, cy, cz - 3), (cx + 3, cy + 2, cz + 3), H + 'zirnox_destroyed'),
                    rad_a=Z.radiation(ctx, a), rad_b=Z.radiation(ctx, b))
    pre = reads()
    _lib.server_idle(ctx, a)
    ctx.restart_server()
    ctx.server('tick freeze')
    for who, dx in ((a, 130), (b, -130)):
        ctx.step('view', client=who, pos=[cx + dx + 0.5, G + 4, cz + 0.5], look_at=[cx + 0.5, G + 4, cz + 0.5], fly=True, hide_gui=False)
    ctx.step('wait', client=a, ticks=80)
    post = reads()
    cmp = _lib.compare_static(pre, post)
    ctx.check(ZX + 'mp-contamination-restart', cmp['ok'], 'before %s, after %s; %s' % (pre, post, cmp['detail']))
    _lib.server_idle(ctx, a)
