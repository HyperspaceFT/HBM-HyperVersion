"""Dedicated server, RBMK meltdown with the overpressure dial on: the overpressure branch fetches the block entities of the steam
network's pipes, some of them in chunks that are not loaded; lag and errors around it are watched.

Run it in its own mp run (it turns the dial on for the rest of the server session). At its start the scenario sets
dialEnableMeltdownOverpressure = true in run/config/hbmsntm-common.toml and restarts the server (server.py restart: run/ is not
restored in between; server.py stop restores the whole of run/config at the end of the session). The file's SHA-256 before and after
the edit goes to the EVIDENCE file below (overpressure-config.json); compare it with the file after the session's stop.

Rig (player A by hand, items put in the hand by command, as rbmk-reactor/mp_meltdown.py builds it): a 3 x 3 reactor, a steam channel
(boiler) at the north middle, the fuel channel in the centre holding one natural uranium RBMK rod, blanks around. A steam duct line
starts on the boiler's top port (core + 4 up: RBMKBaseBlockEntity.getPortConnections :524-530, column height dial 4) and runs
LENGTH blocks east at that height, typed steam. It is built with the world frozen, then the world runs while A flies from the far end
back to the reactor, so the far ducts make their nodes first; behind A the far chunks unload and keep their nodes (UniNodespace.java:58).
The meltdown is started by writing 10,000 °C into the fuel channel's heat (预写) and running one tick (mp_meltdown.py writes 3,000 °C;
here the columns were unloaded and loaded again during the walk, so their tick order is that of the reloaded chunk, and the four
neighbours that tick before the fuel channel each move a fifth of the difference out of it first (RBMKBaseBlockEntity.moveHeat
:167-210, dialColumnHeatFlow 0.2): a first run measured 3,000 -> 1,369.6 °C after the tick, under the 1,500 °C limit (:124-126)).

Expected (original 1.7.10 / NEO):
- with the dial on, the meltdown collects the steam networks of the melting boilers (original TileEntityRBMKBoiler; NEO
  RBMKBoilerBlockEntity.collectOverpressurePipes :226-234) and removes the blocks of min(nodes / 5, 100) of their pipe nodes, every
  one fetched with getTileEntity / getBlockEntity, then blows up the subscribed receivers (original TileEntityRBMKBase.java:501-538,
  :520; NEO RBMKBaseBlockEntity.java:409-410,440-479, :458). A position in a chunk that is not loaded is loaded on the server thread
  by that fetch (1.7.10 ChunkProviderServer.provideChunk; Level.getBlockEntity -> getChunkAt). Here: LENGTH + 1 ducts in one
  network, so 100 ducts go; the steam network has no receivers.
- the dial is false by default (original RBMKDials.java:36; NEO CommonConfig.java:612-615, RBMKDials.java:129-131).
"""
import hashlib
import importlib.util
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402
import common  # noqa: E402
import fluidids  # noqa: E402

_spec = importlib.util.spec_from_file_location('overpressure_rbmk_rig', Path(__file__).with_name('mp_meltdown.py'))
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)
Z = R.Z

SCENARIO = dict(
    id='rbmk-reactor.mp_overpressure',
    feature='rbmk-reactor',
    features=['rbmk-reactor', 'rbmk-steam', 'fluid-pipelines', 'network-architecture'],
    title='Dedicated server: RBMK meltdown with the overpressure dial on, pipes in unloaded chunks fetched, lag and errors watched',
    group='mp',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

G = Z.G
H = Z.H
CONFIG = common.REPO / 'run' / 'config' / 'hbmsntm-common.toml'
KEY = 'dialEnableMeltdownOverpressure'
EVIDENCE = common.REPO / 'build' / 'migration' / 'goal32g' / 'stability' / 'overpressure-config.json'
SITE = (-6000, 6000)
LAYOUT = [['rbmk_blank', 'rbmk_boiler', 'rbmk_blank'],
          ['rbmk_blank', 'rbmk_rod', 'rbmk_blank'],
          ['rbmk_blank', 'rbmk_blank', 'rbmk_blank']]
BOILER_AT = (1, 0)
LENGTH = 800              # ducts east of the one on the boiler
SEGMENT = 96              # blocks filled per stop while building, and per stop of the walk back
PICKED = min((LENGTH + 1) // 5, 100)
STEAM = fluidids.fluid_ids()['STEAM']
NEAR = 20

RX = 'rbmk-reactor.'
SRC = 'TileEntityRBMKBase.java:501-538 (:520); RBMKBaseBlockEntity.java:409-410,440-479 (:458), RBMKBoilerBlockEntity.java:226-234'
EXPECT = [
    ('mp-overpressure-config', '本会话把 run/config/hbmsntm-common.toml 的 dialEnableMeltdownOverpressure 改成 true 并重启专服：改后文件里是 true，'
     '重启成功；改前与改后的 SHA-256 记进 overpressure-config.json（停服后 server.py 还原整个 run/config，由运行者核对哈希）',
     'RBMKDials.java:36; CommonConfig.java:612-615, RBMKDials.java:129-131'),
    ('mp-overpressure-setup', '熔毁前：锅炉顶上起头、向东 %d 格的蒸汽管道都在（逐区块数），其中有的区块不在完整加载状态（A 在反应堆旁）' % LENGTH,
     'UniNodespace.java:58; record'),
    ('mp-overpressure-effect', '过压分支照原版拿走 min(节点数/5, 100) = %d 个管道节点的方块：熔毁后反应堆外少了 %d 格管道' % (PICKED, PICKED), SRC),
    ('mp-overpressure-unloaded', '被拿走的管道里至少有一格在熔毁前未加载的区块里（这次熔毁确实对未加载的位置取了方块实体，同步加载了那个区块）', SRC),
    ('mp-overpressure-errors', '从熔毁那一刻到之后 100 刻，服务端日志里没有 Exception 或 ERROR 行', SRC),
    ('mp-overpressure-lag', '记录：熔毁前后的每刻耗时（tick query 的均值与百分位）、熔毁那一刻的墙钟、日志里的 Can\'t keep up 行；由人判断有没有卡顿', SRC),
]


def expectations():
    return [dict(id=RX + k, text=t, source=s) for k, t, s in EXPECT]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def enable_dial():
    """Sets KEY = true in the server's common config; returns the evidence record (also written to EVIDENCE)."""
    text = CONFIG.read_text(encoding='utf-8')
    m = re.search(r'(?m)^(\s*%s\s*=\s*)(\S+)\s*$' % KEY, text)
    if not m:
        raise RuntimeError('%s has no %s line' % (common.rel(CONFIG), KEY))
    before = sha256(CONFIG)
    record = dict(path=common.rel(CONFIG), key=KEY, value_before=m.group(2), sha256_before_edit=before, edited_at=common.now_tag(),
                  session=(common.read_json(common.SESSION) or {}).get('tag'))
    if m.group(2) != 'true':
        CONFIG.write_text(text[:m.start(2)] + 'true' + text[m.end(2):], encoding='utf-8')
    after_text = CONFIG.read_text(encoding='utf-8')
    record['sha256_after_edit'] = sha256(CONFIG)
    record['value_after'] = re.search(r'(?m)^\s*%s\s*=\s*(\S+)\s*$' % KEY, after_text).group(1)
    record['note'] = 'server.py stop restores run/config from its start backup; compare the file after the stop with sha256_before_edit'
    common.write_json(EVIDENCE, record)
    return record


def count_pieces(ctx, z, lo_x, hi_x, out):
    """Adds the ducts at height G + 4 between lo_x and hi_x (loaded) to out, per chunk x (filtered clones, Z.clone_count)."""
    piece = lo_x
    while piece <= hi_x:
        end = min(((piece >> 4) << 4) + 15, hi_x)
        out[piece >> 4] = out.get(piece >> 4, 0) + Z.clone_count(ctx, (piece, G + 4, z), (end, G + 4, z), H + 'fluid_duct_neo')
        piece = end + 1
    return out


def duct_counts(ctx, a, z, lo_x, hi_x):
    """Ducts at height G + 4 per chunk between lo_x and hi_x: A flies over each SEGMENT and counts. Returns {chunk x: count}."""
    out = {}
    x = lo_x
    while x <= hi_x:
        seg_end = min(x + SEGMENT - 1, hi_x)
        ctx.step('view', client=a, pos=[(x + seg_end) / 2.0 + 0.5, G + 12, z + 4.5], yaw=0.0, pitch=60.0, fly=True, hide_gui=False)
        _lib.wait_full(ctx, a, [(x, G + 4, z), (seg_end, G + 4, z)])
        count_pieces(ctx, z, x, seg_end, out)
        x = seg_end + 1
    return out


def run(ctx):
    a, b = list(ctx.channels)
    cfg = enable_dial()
    _lib.server_idle(ctx, a)
    ctx.restart_server()
    restarted = bool(ctx.run.restarts)
    ctx.check(RX + 'mp-overpressure-config', cfg['value_after'] == 'true' and restarted, json.dumps(cfg, ensure_ascii=False))

    Z.setup_world(ctx, a, b)
    _lib.park(ctx, [b])
    ctx.server('tick freeze')
    x0, z0 = SITE
    # the site is far from the spawn: A flies there and waits until the client has the chunks before placing by hand
    ctx.step('view', client=a, pos=[x0 + 1.5, G + 8, z0 + 6.5], yaw=180.0, pitch=45.0, fly=True, hide_gui=False)
    _lib.wait_full(ctx, a, [(x0, G, z0), (x0 + 2, G, z0 + 2)])
    ctx.step('wait', client=a, ticks=40)
    cells, built = R.build(ctx, a, SITE, LAYOUT)
    fuel, _ = R.load_fuel(ctx, a, cells)
    boiler = cells[BOILER_AT]
    bx, _, bz = boiler
    top = (bx, G + 4, bz)
    # the steam line, built frozen while A flies out; counted per chunk outside the reactor's own columns (x > x0 + 2), where the
    # meltdown itself changes blocks
    lo = x0 + 3
    before_counts = {}
    x = bx
    while x <= bx + LENGTH:
        end = min(x + SEGMENT - 1, bx + LENGTH)
        ctx.step('view', client=a, pos=[(x + end) / 2.0 + 0.5, G + 12, bz + 4.5], yaw=0.0, pitch=60.0, fly=True, hide_gui=False)
        _lib.wait_full(ctx, a, [(x, G + 4, bz), (end, G + 4, bz)])
        Z.rcon1(ctx, 'fill %d %d %d %d %d %d %sfluid_duct_neo{Type:%d}' % (x, G + 4, bz, end, G + 4, bz, H, STEAM))
        count_pieces(ctx, bz, max(x, lo), end, before_counts)
        x = end + 1
    # the world runs while A flies back from the far end: the far ducts make their nodes and join first
    ctx.server('tick unfreeze')
    walk = []
    x = bx + LENGTH
    while x > bx:
        ctx.step('view', client=a, pos=[x + 0.5, G + 12, bz + 4.5], yaw=0.0, pitch=60.0, fly=True, hide_gui=False)
        ctx.step('wait', client=a, ticks=40)
        walk.append(x)
        x -= SEGMENT
    cx, cz = x0 + 1.5, z0 + 1.5
    for who, dx in ((a, NEAR + 1), (b, -NEAR + 1)):
        ctx.step('view', client=who, pos=[cx + dx, G + 6, cz], look_at=[cx, G + 2, cz], fly=True, hide_gui=False)
    ctx.step('wait', client=a, ticks=200)
    _lib.still(ctx)
    full = {k: _lib.chunk_full(ctx, ((k << 4) + 8, G + 4, bz)) for k in range(bx >> 4, ((bx + LENGTH) >> 4) + 1)}
    unloaded = sorted(k for k, v in full.items() if not v)
    loaded = sorted(k for k, v in full.items() if v)
    laid = sum(before_counts.values())
    ctx.check(RX + 'mp-overpressure-setup', built and fuel == 1 and bool(unloaded) and laid == bx + LENGTH - lo + 1,
              'reactor built %s, rod in the fuel channel %s; boiler %s, top port duct %s; ducts counted while building east of x %d: %d (want %d); '
              'walk-back stops %s; chunks at full status %s, not %s' % (built, fuel, boiler, top, lo, laid, bx + LENGTH - lo + 1, walk, loaded, unloaded))

    # the meltdown
    mark = Z.log_mark()
    ts0 = _lib.tick_state(ctx)
    fc = cells[R.FUEL_AT]
    ctx.server('data merge block %d %d %d {heat:10000.0d}' % fc)
    pick = lambda d: {k: d.get(k) for k in ('heat', 'hasRod', 'id')}
    fuel_before = pick(_lib.block_data(ctx, fc))
    g0 = ctx.server()['game_time']
    t0 = time.time()
    ctx.server('tick step 1')
    while ctx.server()['game_time'] <= g0 and time.time() - t0 < 120:
        time.sleep(0.05)
    melt_wall_ms = round((time.time() - t0) * 1000)
    ts1 = _lib.tick_state(ctx)
    corium = Z.block_is(ctx, fc, H + 'corium_block')
    fuel_after = Z.rcon1(ctx, 'data get block %d %d %d heat' % fc)[:120]
    ctx.server('tick unfreeze')
    ctx.step('wait', client=a, ticks=100)
    ts2 = _lib.tick_state(ctx)
    ctx.server('tick freeze')
    lines, paths = Z.log_lines(mark)
    client_lines, other = Z.bad_log_lines(lines)
    slow = [ln[:160] for ln in lines if "Can't keep up" in ln]

    after = duct_counts(ctx, a, bz, lo, bx + LENGTH)
    missing = {k: before_counts[k] - after.get(k, 0) for k in before_counts if before_counts[k] - after.get(k, 0)}
    total = sum(missing.values())
    in_unloaded = sum(v for k, v in missing.items() if k in unloaded)
    ctx.check(RX + 'mp-overpressure-effect', corium and total == PICKED,
              'fuel column before the tick %s, after it %r; corium %s; ducts east of x %d missing per chunk x %s, total %d (want %d; a picked duct over the reactor\'s own '
              'columns would not be counted here)' % (fuel_before, fuel_after, corium, lo, missing, total, PICKED))
    ctx.check(RX + 'mp-overpressure-unloaded', in_unloaded > 0, 'missing ducts in chunks that were not at full status before the meltdown: %d '
              '(chunks %s)' % (in_unloaded, sorted(k for k in missing if k in unloaded)))
    ctx.check(RX + 'mp-overpressure-errors', not other and not client_lines, 'server log lines since the meltdown (%s): error lines %s, client-class lines %s'
              % (paths, other[:5], client_lines[:3]))
    ctx.review(RX + 'mp-overpressure-lag', 'tick query before %s; right after the meltdown tick %s; after 100 more ticks %s; wall time from tick step 1 '
               'to the game time moving %d ms; Can\'t keep up lines %s' % (ts0, ts1, ts2, melt_wall_ms, slow[:3]))
    ctx.step('view', client=a, pos=[cx + NEAR, G + 6, cz], look_at=[cx, G + 2, cz], fly=True, hide_gui=False)
    _lib.server_idle(ctx, a)
