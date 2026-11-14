"""Stress record: rings of belts filled through extractors to about 2,000 and 10,000 moving items; server tick time and
client frame rates. A record without pass lines.

The cram limit is raised to 200 and the belt break switched off in the dedicated server's config (restored when the
session stops); items reach the belts only through extractors (no stack upgrade, the ejector upgrade III: one item
every 2 ticks per extractor). Server, both clients and the driver run on the same Mac. Network traffic has no reading
in the executor (not measured).
"""
import re
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402
import common  # noqa: E402

SCENARIO = dict(
    id='conveyors.stress',
    feature='conveyors',
    title='Stress record: about 2,000 and 10,000 moving items on rings; tick time and frame rates',
    group='mp',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

G = -60
X0, Z0 = 600, 0
W = 40          # ring length along x
RINGS = 12      # one extractor each, rings 6 blocks apart
CONFIG = common.REPO / 'run' / 'config' / 'hbmsntm-server.toml'


def expectations():
    return [dict(id='conveyors.stress-2000', text='record: tick time and client frame rates with about 2,000 moving items', source='record, no pass line'),
            dict(id='conveyors.stress-10000', text='record: tick time and client frame rates with about 10,000 moving items', source='record, no pass line'),
            dict(id='conveyors.stress-profile', text='record: a 30-second server profile (debug start/stop) at the higher load', source='record, no pass line')]


def ring_blocks(x, z):
    cells = [(x, z, 'south', 'right'), (x + W - 1, z, 'west', 'right'), (x + W - 1, z + 2, 'north', 'right'), (x, z + 2, 'east', 'right'),
             (x + W - 1, z + 1, 'north', 'straight'), (x, z + 1, 'south', 'straight')]
    fills = [((x + 1, z), (x + W - 2, z), 'west'), ((x + 1, z + 2), (x + W - 2, z + 2), 'east')]
    return cells, fills


def count(ctx):
    r = ctx.rcon('execute if entity @e[type=hbmsntm:moving_item]')
    m = re.search(r'(\d+)\s*$', r[0] if r else '')
    return int(m.group(1)) if m else 0, (r[0] if r else '')


def measure(ctx, a, b):
    tick = ctx.rcon('tick query')
    perf = {who: ctx.step('perf', client=who, ticks=100) for who in (a, b)}
    return dict(tick_query=' | '.join(tick), clients={who: dict(fps_mean=round(p.get('fps_mean', 0), 1), fps_min=p.get('fps_min'),
                                                                frame_ms_max=round(p.get('frame_ms_max', 0), 1), window_active=p.get('window_active'))
                                                     for who, p in perf.items()})


def run(ctx):
    a, b = list(ctx.channels)
    text = CONFIG.read_text(encoding='utf-8')
    text = re.sub(r'(?m)^(\s*conveyor_cram_max\s*=\s*)\S+', r'\g<1>200', text)
    text = re.sub(r'(?m)^(\s*conveyor_cram_explode\s*=\s*)\S+', r'\g<1>false', text)
    CONFIG.write_text(text, encoding='utf-8')
    _lib.server_idle(ctx, a)
    ctx.restart_server()
    ctx.rcon('gamemode creative %s' % a, 'gamemode creative %s' % b, 'gamerule doMobSpawning false', 'time set 6000',
             'tp %s %d %d %d' % (a, X0 + W // 2, G + 30, Z0 + 3 * RINGS), 'tp %s %d %d %d' % (b, X0 + W // 2 + 4, G + 30, Z0 + 3 * RINGS))
    for who in (a, b):
        ctx.step('view', client=who, pos=[X0 + W / 2 + (4 if who == b else 0), G + 30, Z0 + 3 * RINGS], pitch=80.0, yaw=180.0, fly=True, hide_gui=False)
    ctx.step('wait', client=a, ticks=100)
    for i in range(RINGS):
        z = Z0 + 6 * i
        cells, fills = ring_blocks(X0, z)
        cmds = ['fill %d %d %d %d %d %d hbmsntm:conveyor[facing=%s,shape=straight]' % (p[0], G, p[1], q[0], G, q[1], f) for p, q, f in fills]
        cmds += ['setblock %d %d %d hbmsntm:conveyor[facing=%s,shape=%s]' % (x, G, zz, f, s) for x, zz, f, s in cells]
        ex = (X0 + W // 2, G, z - 1)
        cmds += ['setblock %d %d %d minecraft:chest' % (ex[0], G, z - 2),
                 'setblock %d %d %d hbmsntm:crane_extractor[input=south,output=north]' % ex,
                 'item replace block %d %d %d container.19 with hbmsntm:upgrade_ejector_3' % ex]
        ctx.rcon(*cmds)
    for i in range(RINGS):
        z = Z0 + 6 * i
        ctx.rcon(*['item replace block %d %d %d container.%d with minecraft:cobblestone 64' % (X0 + W // 2, G, z - 2, s) for s in range(15)])
    results = {}
    for target, eid in ((2000, 'conveyors.stress-2000'), (10000, 'conveyors.stress-10000')):
        n, reply = count(ctx)
        for _ in range(60):
            if n >= target:
                break
            ctx.step('wait', client=a, ticks=100)
            n, reply = count(ctx)
        m = measure(ctx, a, b)
        shots = [ctx.step('shot', client=who, file=ctx.shot_name('stress-%d-%s' % (target, who)))['image']['file'] for who in (a, b)]
        results[target] = m
        ctx.review(eid, 'moving items %d (%s); %s; server, two clients and driver on one Mac; network traffic not read' % (n, reply, m), shots)
    run_dir = common.REPO / 'run'
    since = time.time()
    ctx.rcon('debug start')
    ctx.step('wait', client=a, ticks=600)
    stop = ctx.rcon('debug stop')
    ctx.step('wait', client=a, ticks=60)   # the report is written after the reply
    found = [p for p in run_dir.rglob('*') if p.is_file() and 'profil' in str(p.relative_to(run_dir)).lower() and p.stat().st_mtime >= since]
    copied = []
    dest = ctx.run.dir / 'server-debug'
    for p in found:
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest / p.name)
        copied.append('%s (from run/%s)' % (p.name, p.relative_to(run_dir)))
        p.unlink()
    debug = run_dir / 'debug'
    if debug.exists() and not any(debug.rglob('*')):
        shutil.rmtree(debug)
    ctx.review('conveyors.stress-profile', 'debug stop: %s; report files copied into the run directory: %s' % (stop, copied or 'none found under run/'))
    ctx.rcon('kill @e[type=hbmsntm:moving_item]')
    _lib.server_idle(ctx, a)  # the closing stop of the group comes next
