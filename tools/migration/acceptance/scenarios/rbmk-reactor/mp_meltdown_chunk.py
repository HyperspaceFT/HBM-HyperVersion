"""Dedicated server, RBMK meltdown and chunk radiation in its own disposable world (a second meltdown world, apart from
rbmk-reactor/mp_meltdown.py).

The rig and the meltdown are those of rbmk-reactor/mp_meltdown.py (its melt(): a hand-built 3 x 3 reactor, one natural uranium
rod shift-clicked into the fuel channel, 3,000 °C written into the fuel channel's heat (预写), one tick). Then the world runs
T ticks (a sprint from the frozen world), so the wreck works on its surroundings, and is frozen again. T is worked out from the
code so that the chance that the radiating wreck has let out no meltdown gas at all is at most 1e-9 (see the next paragraph).

Waiting time (original RBMKDebrisRadiating.java:29-33,52-58, BlockGasBase.java:80-87, BlockGasMeltdown.java:81-83; NEO
RBMKDebrisRadiatingBlock.java:44-47,60-64, GasBaseBlock.java:44-49, GasMeltdownBlock.java:78-80):
- a radiating wreck block ticks every 20-39 ticks, from 20-39 ticks after it is placed; each tick picks one of its six sides at
  random and, with chance 1/10, puts a meltdown gas cell there when that side is air. Wreck cells around the corium become
  radiating with chance 1/3 (original TileEntityRBMKBase.java:477-498; NEO RBMKBaseBlockEntity.java:384-405); in this 3 x 3 rig
  the candidates are the 16 wreck cells at y = G and G + 1 of the eight outer columns, and each of them has at least one side on
  the outside of the reactor, air under the open sky until the first gas cell is let out. So every tick of every radiating block
  lets out gas with chance at least 1/60, and N radiating blocks get at least N x floor(T / 39) such ticks in T ticks: the chance
  of no gas at all is at most (59/60)^(N x floor(T / 39)). ln(1e-9) / ln(59/60) = 1,233.005, so T = 39 x ceil(1,234 / N) keeps
  it at or below 9.9e-10 (N = 1: 48,126 ticks; 3: 16,068; 6: 8,034; 16: 3,042).
- a gas cell first ticks 10 ticks after it is placed and then adds 5 to its chunk's radiation on every tick while it sees the sky;
  it vanishes with chance 1/350 a tick (original BlockGasMeltdown.java:85-88; NEO GasMeltdownBlock.java:82-85) and moves about
  every 10 ticks, so a cell lives about 3,500 ticks on average. The burning wreck lets out gas the same way every 100-119 ticks but
  goes out with chance 1/100 a tick (original RBMKDebrisBurning.java:21-58; NEO RBMKDebrisBurningBlock.java:54-69): it is left out of
  the bound. With no radiating block (chance (2/3)^16 = 0.15 %) the bound does not hold.
- a survey that finds every chunk at 0 met a moment with no live gas cell: the world then runs 3,600 more ticks (about one gas
  lifetime) and the survey is read again, at most SURVEYS times. This repeats the reading, it does not change what is asserted.

Expected (original 1.7.10 / NEO):
- debris and wreck are server entities and blocks that every client in range holds as the server does (see mp_meltdown.py).
- chunk radiation is server data per chunk (original ChunkRadiationHandlerSimple, NEO ChunkRadiationHandlerSimple); the
  meltdown gas the burning and radiating wreck lets out adds to it (original BlockGasMeltdown, NEO GasMeltdownBlock). The Geiger
  counter prints the chunk value of the block the player stands in, from the server, to that player (original
  ContaminationUtil.printGeigerData :155-195; NEO ContaminationUtil.java:72-95), so two players in the same chunk read the same
  value at the same moment. The values are redistributed every 20 server ticks by the server tick event, which a frozen world does
  not stop, and each update takes 0.05 off every contribution, so frozen they drain to 0 within seconds (original
  ChunkRadiationManager.java:45-53, ChunkRadiationHandlerSimple.java:71-98; NEO ChunkRadiationManager.java:59-65,
  ChunkRadiationHandlerSimple.java:73-100): the readings are taken with the world running.
"""
import importlib.util
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

_spec = importlib.util.spec_from_file_location('rbmk_mp_rig', Path(__file__).with_name('mp_meltdown.py'))
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)
Z = R.Z

SCENARIO = dict(
    id='rbmk-reactor.mp_meltdown_chunk',
    feature='rbmk-reactor',
    title='Dedicated server: RBMK meltdown, debris and wreck on both clients, chunk radiation read by both players',
    group='mp',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

G = Z.G
H = Z.H
SITE = (60, 60)
GAS_P = 1 / 60.0                 # least chance a radiating wreck tick lets out gas before the first release (1/10 x 1/6 sides)
TICK_MAX = 39                    # longest interval of a radiating wreck tick (20 + rand(20))
P_TARGET = 1e-9                  # chance of no gas at all that the wait allows
GAS_TICKS = math.ceil(math.log(P_TARGET) / math.log(1 - GAS_P))    # 1,234 radiating ticks in all
WARM = 60                        # running ticks after an unfreeze before a survey: three chunk-radiation updates
RETRY = 3600                     # further ticks before a survey is read again: about one gas cell's lifetime (350 moves x 10 ticks)
SURVEYS = 4
RX = 'rbmk-reactor.'
EXPECT = [
    ('mp-meltdown-chunk-sync', '专服：另一个一次性世界里同样熔毁一座手搭的 3×3 小堆（燃料棒命令发放，热量预写）：服务端的碎片与两个客户端所持的碎片'
     '个数与位置一致（跟踪距离 126 格内，位置差不到 0.5 格），反应堆范围里的残骸方块在两个客户端上逐格相同并与服务端的格数相同',
     'TileEntityRBMKBase.java:439-573; RBMKBaseBlockEntity.java:323-427'),
    ('mp-meltdown-chunk', '专服：熔毁后先按代码算出要等的刻数 T 再读。辐射残骸放下后 20–39 刻起每 20–39 刻走一次，每次随机挑六个面之一，'
     '挑中的面是空气时以 1/10 放一格熔毁气体；这座 3×3 小堆里候选的 16 格残骸（外圈八根柱子 G 与 G+1 两层，各以 1/3 变成辐射残骸）'
     '每格至少有一面朝堆外、头顶是天空的空气，所以放第一格气体之前每走一次至少有 1/60 的机会放气；N 块辐射残骸在 T 刻里至少走 N×⌊T/39⌋ 次，'
     '一格气体都没放的概率不超过 (59/60)^(N×⌊T/39⌋)。ln(1e-9)/ln(59/60) = 1,233.005，取 T = 39×⌈1,234/N⌉，'
     '这一概率不超过 9.9e-10（N=1 时 48,126 刻，3 时 16,068，6 时 8,034，16 时 3,042）；N 是熔毁后服务端数的辐射残骸格数，'
     '世界从冻结冲刺走 T 刻。燃烧残骸也放气但会熄灭，不计入；N = 0（概率 (2/3)^16 ≈ 0.15%）时上式不成立，读数若全为 0 记未执行。'
     '气体放下 10 刻后第一次走，此后每走一次只要能见天空就给所在区块加 5，每次以 1/350 消失，约每 10 刻挪一格，平均约活 3,500 刻。'
     '冲刺之后解冻、先让世界走 60 刻（区块辐射每 20 个服务端刻重新分配一次，冻结的世界里也照样每次减 0.05，几秒内就归零，所以读的时候让世界走着、'
     '活着的气体继续加），A 在反应堆所在区块及周围共 3×3 个区块的中心各用一次盖革计数器；九格全为 0 说明此刻没有活着的气体，'
     '再冲刺 3,600 刻（约一格气体的平均寿命）重读，至多读 4 轮（只是重读，判定不变）。两人再站进读数最大的那个区块（相隔一格）同时各用一次：'
     '两人读到的区块辐射值相同且大于 0（服务端按区块存的值，对站在同一区块的人相同；一对读数若正好跨了一次更新就再读，至多 3 次）',
     'RBMKDebrisRadiating.java:29-33,52-58, TileEntityRBMKBase.java:477-498, BlockGasBase.java:80-87, BlockGasMeltdown.java:81-88, '
     'ContaminationUtil.java:155-195, ChunkRadiationManager.java:45-53, ChunkRadiationHandlerSimple.java:71-98; '
     'RBMKDebrisRadiatingBlock.java:44-47,60-64, RBMKBaseBlockEntity.java:384-405, GasBaseBlock.java:44-49, GasMeltdownBlock.java:78-85, '
     'ContaminationUtil.java:72-95, ChunkRadiationManager.java:59-65, ChunkRadiationHandlerSimple.java:73-100'),
    ('mp-meltdown-chunk-restart', '专服重启后（静止、非默认的服务端读数）：堆芯熔融物的格数、三种残骸的格数之和与碎片个数与重启前相同', 'block and entity save'),
]


def expectations():
    return [dict(id=RX + k, text=t, source=s) for k, t, s in EXPECT]


def chunk_reading(ctx, who, prefix):
    """Uses the Geiger counter in the hand (looking up) and returns the chunk radiation number of the reply."""
    ctx.step('key', client=who, key='key.keyboard.1', action='tap', after=2)
    said = ctx.step('use', client=who, after=6)
    c = ctx.step('chat', client=who, count=12, since_ms=said['started_ms'], allow_fail=True)
    lines = [m['text'] for m in c.get('messages', [])]
    for line in lines:
        if prefix and prefix in line:
            m = re.search(r'(-?\d+(?:\.\d+)?)', line[line.index(prefix) + len(prefix):])
            if m:
                return float(m.group(1)), line
    return None, lines[-6:]


def wait_ticks(n_rad):
    """T = 39 x ceil(1,234 / N): with N radiating wreck blocks the chance that no gas cell at all has been let out after T ticks
    is at most (59/60)^(N x floor(T / 39)) <= 1e-9 (module docstring). Without a radiating block the wait of N = 1 is used and the
    bound does not hold."""
    n = max(n_rad, 1)
    return TICK_MAX * math.ceil(GAS_TICKS / n)


def no_gas_bound(n_rad, ticks):
    return (1 - GAS_P) ** (n_rad * (ticks // TICK_MAX)) if n_rad else None


def run(ctx):
    a, b = list(ctx.channels)
    Z.setup_world(ctx, a, b)
    m = R.melt(ctx, a, b, site=SITE)
    ok_sync, sync_detail, _ = R.sync_after_flight(ctx, a, b, SITE, m['box'])
    # the wait worked out from the code (module docstring): N radiating wreck blocks counted on the server right after the meltdown
    n_rad = m['counts'].get('pribris_radiating', 0)
    wait_t = wait_ticks(n_rad)
    wait_rec = _lib.advance(ctx, wait_t, 'gas-wait')     # from the frozen world, exactly wait_t ticks, frozen again
    ctx.server('tick freeze')
    ctx.step('wait', client=a, ticks=80)
    x0, z0 = SITE
    # chunk radiation is redistributed every 20 server ticks by the server tick event, also in a frozen world, and every update takes
    # 0.05 off each contribution (ChunkRadiationManager.java:59-65, ChunkRadiationHandlerSimple.java:73-100; original
    # ChunkRadiationManager.java:45-53, ChunkRadiationHandlerSimple.java:71-98): frozen, the values drain to 0 within seconds. So the
    # world runs (the wreck keeps feeding meltdown gas) while A reads the Geiger counter in the middle of each of the 3 x 3 chunks
    # around the reactor's chunk; both players then stand one block apart in the chunk with the highest reading and read it at the
    # same moment (two threads); a pair that straddles an update is read again, at most 3 times.
    # I18n.get without arguments answers 'Format error: <pattern>'; the text before the placeholder is what the chat line starts with
    prefix = ctx.step('i18n', client=a, keys=['geiger.chunkRad'])['texts']['geiger.chunkRad'].split('Format error: ')[-1].split('%s')[0]
    for who in (a, b):
        ctx.rcon('item replace entity %s hotbar.0 with %sgeiger_counter' % (who, H))
    kx, kz = x0 >> 4, z0 >> 4
    # a survey that reads 0 everywhere met a moment without a live gas cell: the world runs RETRY more ticks and the survey is read
    # again, at most SURVEYS times (a repeated reading; what is asserted does not change)
    surveys, retries = [], []
    for k in range(SURVEYS):
        if k:
            ctx.server('tick freeze')
            retries.append(_lib.advance(ctx, RETRY, 'gas-retry-%d' % k).get('advanced'))
        ctx.server('tick unfreeze')
        ctx.step('wait', client=a, ticks=WARM)
        survey = {}
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                c = (kx + dx, kz + dz)
                ctx.step('view', client=a, pos=[c[0] * 16 + 8.5, G + 5, c[1] * 16 + 8.5], yaw=0.0, pitch=-90.0, fly=True, hide_gui=False)
                ctx.step('wait', client=a, ticks=4)
                survey[c] = chunk_reading(ctx, a, prefix)[0]
        surveys.append({'%d,%d' % c: v for c, v in survey.items()})
        if any((v or 0) > 0 for v in survey.values()):
            break
    best = max(survey, key=lambda c: (survey[c] or 0.0))
    spots = {a: (best[0] * 16 + 7.5, best[1] * 16 + 8.5), b: (best[0] * 16 + 9.5, best[1] * 16 + 8.5)}
    same_chunk = len({(int(s[0]) >> 4, int(s[1]) >> 4) for s in spots.values()} | {best}) == 1
    for who in (a, b):
        ctx.step('view', client=who, pos=[spots[who][0], G + 5, spots[who][1]], yaw=0.0, pitch=-90.0, fly=True, hide_gui=False)
    ctx.step('wait', client=a, ticks=4)
    pairs = []
    for _ in range(3):
        reads = Z.both(ctx, lambda n: chunk_reading(ctx, n, prefix))
        pairs.append((reads[a][0], reads[b][0]))
        if reads[a][0] is not None and reads[a][0] == reads[b][0]:
            break
    ctx.server('tick freeze')
    va, vb = pairs[-1]
    ctx.check(RX + 'mp-meltdown-chunk-sync', m['ok'] and ok_sync, '%s; %s' % (m['detail'], sync_detail))
    bound = no_gas_bound(n_rad, wait_t)
    detail = ('radiating wreck N = %d, wait T = 39 x ceil(%d / max(N, 1)) = %d ticks (sprint advanced %s in %s s; the flight\'s 120 ticks '
              'before it not counted): chance of no gas at all <= %s; Geiger surveys (world running, %d ticks after each unfreeze) of the chunks around '
              'the reactor\'s chunk %s: %s (further sprints before a repeated survey: %s); both players in chunk %s at %s (one chunk %s); '
              'simultaneous readings (A, B) per try %s; last line A %r, B %r'
              % (n_rad, GAS_TICKS, wait_t, wait_rec.get('advanced'), wait_rec.get('wall_s'),
                 ('%.2e' % bound) if bound is not None else 'no bound (no radiating wreck)', WARM, (kx, kz), surveys, retries or 'none',
                 best, spots, same_chunk, pairs, reads[a][1], reads[b][1]))
    if n_rad == 0 and not any((v or 0) > 0 for v in survey.values()) and not (va and va > 0):
        ctx.not_run(RX + 'mp-meltdown-chunk', 'this meltdown left no radiating wreck (chance (2/3)^16 = 0.15 %), so the waiting bound does '
                    'not hold and no gas cell was alive at any survey: ' + detail)
    else:
        ctx.check(RX + 'mp-meltdown-chunk', m['ok'] and same_chunk and va is not None and va > 0 and va == vb, detail)
    ctx.step('wait', client=a, ticks=80)

    def counts():
        out = R.still_counts(ctx, m['box'])
        out['debris'] = Z.entity_count(ctx, R.DEB)
        return out
    pre = counts()
    _lib.server_idle(ctx, a)
    ctx.restart_server()
    ctx.server('tick freeze')
    ctx.step('wait', client=a, ticks=80)
    post = counts()
    cmp = _lib.compare_static(pre, post)
    ctx.check(RX + 'mp-meltdown-chunk-restart', cmp['ok'], 'before %s, after %s; %s' % (pre, post, cmp['detail']))
    _lib.server_idle(ctx, a)
