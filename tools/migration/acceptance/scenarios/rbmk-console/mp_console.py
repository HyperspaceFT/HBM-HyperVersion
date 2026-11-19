"""Dedicated server: start isolation of the client-only RBMK classes, and two players at one RBMK console.

Rig (player A, by hand; items put in the hand by command): one row of columns west to east at y = G, a manual control rod, a
blank column and a second manual control rod, and an RBMK console placed 6 blocks south of it. A links the console to the blank
column with the RBMK console linking device (right-click on the column, then sneak + right-click on the console). In each rod's own screen A clicks
the 100 % button and the red group button; the world then runs until both rods are out.

Expected (original 1.7.10 / NEO):
- a manual control rod moves towards its target by 0.00277 a tick (original TileEntityRBMKControl.java:76-112, speed :31;
  NEO RBMKControlBlockEntity.java:27,53-61): from 1 down to 0 it is 1 - n x 0.00277 after n ticks, in double arithmetic.
- the console's AZ-5 button (a lid to open first) sends level 0 for every manual control rod of the grid (original
  GUIRBMKConsole.java:222-239; NEO RBMKConsoleScreen.java:275-291, RBMKConsoleBlockEntity.buildAZ5Control :377-392); the shutdown
  sound is played by the clicking client only (original GUIRBMKConsole.java:226, a PositionedSoundRecord on the client's own sound
  handler; NEO RBMKConsoleScreen.java:283,376, SimpleSoundInstance.forUI). The scenario reads the play events each client's sound
  manager reports; whether a person hears the sound is the other half and belongs to a user station.
- each player opens the console screen for himself: the original opens its GuiScreen on the client (RBMKConsole.java:90-91), NEO
  opens a menu per player on the server (RBMKConsoleBlock.java:76-78, DummyableBlock.java:431-444), so two players have it open at
  the same time.
- a screen-type button sends "toggle" and the console stores the next type (original TileEntityRBMKConsole.receiveControl
  :256-337; NEO RBMKConsoleBlockEntity.java:309-320); the console's data reaches every client with its packets (NEO :188-256).
- the console takes controls only from players within 20 blocks (original :252-254; NEO RBMKConsoleBlockEntity.java:264-267).
  The original console screen is a plain GuiScreen without a container (GUIRBMKConsole.java:32), closed only by Esc or the
  inventory key (:444-455), so it stays open at any distance and its controls work up to 20 blocks; NEO's console screen has a
  menu whose stillValid is the block entity's interaction range (MachineBaseBlockEntity.java:64-65, Container.stillValidBlockEntity).
- a left click on a group key in the console screen selects that group's manual rods on the clicking client; a right click on a
  group key sends assignColor for the selected rods (original GUIRBMKConsole.java:183-208, TileEntityRBMKConsole.java:304-318;
  NEO RBMKConsoleScreen.java:248-271, RBMKConsoleBlockEntity.java:341-352). The grid tooltip names a rod's group (NEO
  RBMKConsoleScreen.java:155-160).
- the dedicated server registers no client classes: the console, crane and column screens and renderers and the RBMK particles
  are registered on the client only, so the server log has no NoClassDefFoundError or invalid-dist lines.
"""
import importlib.util
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402
import common  # noqa: E402

_spec = importlib.util.spec_from_file_location('rbmk_mp_rig', Path(__file__).resolve().parents[1] / 'rbmk-reactor' / 'mp_meltdown.py')
R = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R)
Z = R.Z

SCENARIO = dict(
    id='rbmk-console.mp_console',
    feature='rbmk-console',
    title='Dedicated server: start isolation of client classes, two players at one RBMK console (toggle, AZ-5, reach)',
    group='mp',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

G = Z.G
H = Z.H
SITE = (-60, -60)
LAYOUT = [['rbmk_control', 'rbmk_blank', 'rbmk_control']]
SPEED = 0.00277
STEPS = 100
CX = 'rbmk-console.'
EXPECT = [
    ('mp-start-isolation', '专服：这次专服会话的全部服务端日志（含启动与每次重启）里没有 NoClassDefFoundError、'
     'invalid dist 或客户端类的加载错误，期间两名玩家打开过控制台、控制棒、燃料通道、辐照通道、装料机等界面',
     'client-only registration; server log'),
    ('mp-console-both-open', '专服：两人同时打开同一台手放、用连接装置连好的控制台的界面（两个客户端同时右键控制台，各开各的）：'
     '随后同时读两个客户端，A 与 B 的控制台界面都开着，后开的一方没有把先开的一方的界面挤掉',
     'RBMKConsole.java:90-91, GUIRBMKConsole.java:32; RBMKConsoleBlock.java:76-78, DummyableBlock.java:431-444'),
    ('mp-console-select-group', '专服：两人同时开着同一台手放、用连接装置连好的控制台界面（两根手动控制棒在各自界面设成红组）；A 在控制台上左键点红组键选中'
     '红组的棒（选择只在 A 的客户端里），再右键点黄组键把选中的棒改成黄组：服务端两根棒的颜色都是黄组（1），冻结世界走 11 刻（含一次刷新）后'
     'B 的控制台网格提示里两根棒都显示黄组',
     'GUIRBMKConsole.java:183-208, TileEntityRBMKConsole.java:304-318; RBMKConsoleScreen.java:155-160,248-271, RBMKConsoleBlockEntity.java:341-352'),
    ('mp-console-set-depth', '专服：A 给选中的组设深度、B 的网格竖条随之变化：深度要在控制台界面的文本框里输入数字再点保存键，执行器只能按键、不能输入字符，做不到',
     'GUIRBMKConsole.java:241-262; RBMKConsoleScreen.java:293-317'),
    ('mp-console-toggle', '专服：A 点第 1 块屏幕的类型键，冻结世界走 2 刻：服务端 t0 从 0 变 1，B 客户端的控制台副本也是 1（每刻都发数据包，但游戏时间 '
     '≡ 0 (mod 10) 那一刻的整包不带屏幕类型，2 刻里至少有一个带类型的包）',
     'TileEntityRBMKConsole.java:191-220,257-337; RBMKConsoleScreen.java:320-330, RBMKConsoleBlockEntity.java:191-221,309-320'),
    ('mp-console-visual', '专服（待人看，用户站点）：A 切换第 1 块屏幕的类型后，B 的界面图标与控制台模型上的屏幕随之改画；只能人看（B 的客户端副本里的类型'
     '在 mp-console-toggle 里判定）', 'GUIRBMKConsole, RenderRBMKConsole; RBMKConsoleScreen.java, RenderRBMKConsole.java'),
    ('mp-console-az5', '专服：两根控制棒先在各自界面点 100% 并升到 1.0，A 打开 AZ-5 盖子再按下：“只有 A 听到警报声”这里按客户端判，'
     '只有 A 的客户端声音管理器报出关机声的播放事件，B 的没有（原版只在点击的客户端上播放）；人是否真的听到（扬声器、音量、远近）是另一半，'
     '归用户站点，本行不判；'
     '冻结世界走 100 刻后两根棒在服务端都是 1 − 100×0.00277（双精度逐刻相减），两个客户端的棒副本相同，B 的控制台网格提示显示的百分比'
     '是最后一次刷新（游戏时间 ≡ 0 (mod 10) 的那一刻；控制棒放在控制台之前，同一刻先走）时的棒位 (int)((1 − n×0.00277)×100)%，n 是从 AZ-5 '
     '到那一刻的刻数',
     'TileEntityRBMKControl.java:76-112, GUIRBMKConsole.java:222-239; RBMKControlBlockEntity.java:27,53-61, RBMKConsoleScreen.java:164,276-291,376, '
     'RBMKConsoleBlockEntity.java:61-62,377-392; original TileEntityRBMKConsole.java:75,484'),
    ('mp-console-reach-12', '专服：B 开着控制台界面移到离控制台 12 格处（20 格的指令范围之内）：照原版界面仍开着（原版的控制台界面没有容器，'
     '不因距离关闭，指令到 20 格为止都被服务端接受），B 点第 2 块屏幕的类型键、冻结世界走 2 刻后服务端 t1 从 0 变 1',
     'GUIRBMKConsole.java:32,444-455, TileEntityRBMKConsole.java:252-254; RBMKConsoleBlockEntity.java:264-267, MachineBaseBlockEntity.java:64-65'),
    ('mp-console-reach-21', '专服：B 开着控制台界面移到离控制台 21 格处：它的控制台界面关闭，B 不能再从界面发指令。本行只证明界面被关掉；'
     '“界面开着时 21 格外的指令被服务端拒绝”（原版的情形）这里到不了，服务端的 20 格判定只由 GameTest 覆盖',
     'TileEntityRBMKConsole.java:252-254; RBMKConsoleBlockEntity.java:264-267, MachineBaseBlockEntity.java:64-65, RBMKConsoleGameTests.java:633-640'),
    ('mp-console-restart', '专服重启后（两根控制棒先在各自界面点 50% 并停在 0.5；静止、非默认的服务端读数）：控制台的连接目标、第 1 与第 2 块屏幕的类型、两根控制棒的位置与重启前相同',
     'RBMKConsoleBlockEntity.java:408-436, RBMKControlBlockEntity.java:85-97'),
]


def expectations():
    return [dict(id=CX + k, text=t, source=s) for k, t, s in EXPECT]


def client_nbt(ctx, who, pos):
    d = ctx.step('dump', client=who, **{'from': list(pos)})
    return _lib.parse_snbt(d['blocks'][0]['nbt']) if d['blocks'] and d['blocks'][0].get('nbt') else {}


def run_logs(ctx):
    """Every server log of this run's tag (server.py writes a new one for each start)."""
    tag = getattr(getattr(ctx.run, 'args', None), 'tag', None)
    logs = sorted((common.STATE / 'logs').glob('server-%s-*.log' % tag)) if tag else []
    lines = []
    for p in logs:
        lines += p.read_text(encoding='utf-8', errors='replace').splitlines()
    return logs, lines


def run(ctx):
    a, b = list(ctx.channels)
    Z.setup_world(ctx, a, b)
    x0, z0 = SITE
    cells, built = R.build(ctx, a, SITE, LAYOUT)
    rods = [cells[(0, 0)], cells[(2, 0)]]
    blank = cells[(1, 0)]
    # the console 6 blocks south of the blank column, placed from the south
    console = Z.place_by_hand(ctx, a, H + 'rbmk_console', blank[0], blank[2] + 6, H + 'rbmk_console',
                              ((blank[0] - 4, G, blank[2] + 2), (blank[0] + 4, G + 4, blank[2] + 10)))
    # link: the device on the blank column, then on the console
    Z.hand(ctx, a, H + 'rbmk_tool')
    R.use_top(ctx, a, blank[0], blank[2])
    # sneaking: a plain right-click opens the console's screen
    R.sneak_use(ctx, a, (console[0], G + 1, console[2]), 'south', stand=(console[0] + 0.5, G, console[2] + 3.5),
                look=(console[0] + 0.5, G + 1, console[2] + 0.5), fly=True, any_hit=True)
    ctx.rcon('item replace entity %s hotbar.0 with minecraft:air' % a)
    cdata = _lib.block_data(ctx, console)
    linked = (cdata.get('tX'), cdata.get('tY'), cdata.get('tZ')) == tuple(blank)
    # the rods out: 100 % and the red group in each rod's screen
    for rx, _, rz in rods:
        hud = R.open_column(ctx, a, rx, rz, 'RBMKControlScreen')
        Z.click_at(ctx, a, hud, 133, 31)     # RBMKControlScreen.mouseClicked: level buttons at (118, 26 + 11k), k = 0 is 100 %
        Z.click_at(ctx, a, hud, 34, 31)      # colour buttons at (28, 26 + 11k), k = 0 is red
        ctx.step('close', client=a)
    rec = ctx.sprint(400, label='rods-out', timeout_s=120)
    _lib.still(ctx, rec)
    _lib.server_idle(ctx, a)                   # the clients may lag behind a sprint: both screens open once the server idles
    out = [_lib.block_data(ctx, p).get('level') for p in rods]

    # both at the console
    stand_b = [console[0] + 1.5, G, console[2] + 3.5]
    # both open the console at the same time (two threads, one step channel per client), then both screens are read at once
    stands = {a: [console[0] - 0.5, G, console[2] + 3.5], b: stand_b}
    huds = Z.both(ctx, lambda n: Z.open_screen(ctx, n, (console[0], G + 1, console[2]), 'south', stands[n], 'RBMKConsoleScreen'))
    hud_a, hud_b = huds[a], huds[b]
    open_now = Z.both(ctx, lambda n: ctx.step('screen', client=n, expect='RBMKConsoleScreen', allow_fail=True))
    ctx.check(CX + 'mp-console-both-open', all(open_now[n]['status'] == 'ok' for n in (a, b)),
              'opened by both clients at once; screens read together afterwards: A %s (%s), B %s (%s)'
              % (open_now[a]['status'], open_now[a].get('screen') or open_now[a].get('reason'), open_now[b]['status'],
                 open_now[b].get('screen') or open_now[b].get('reason')))

    def b_grid():
        """B's console grid: the tooltips of the three columns around the centre of the grid (index 7 + 7 * 15)."""
        out = []
        for gx in (6, 7, 8):
            ctx.step('hover', client=b, at=[hud_b['gui_left'] + 86 + 10 * gx + 5, hud_b['gui_top'] + 11 + 10 * 7 + 5], frames=3)
            out.append([t['text'][9:] for t in ctx.step('hud', client=b, frames=3)['texts'] if t['text'].startswith('tooltip: ')])
        return out

    # (a) select a group: a left click on the red group key selects the red rods on A's client only; a right click on the yellow key
    # sends assignColor 1 for the selected rods (GUIRBMKConsole.java:183-208; RBMKConsoleScreen.java:248-271), so the rods' new
    # colour shows what the selection held; B sees it in the grid after the next rescan (game time = 0 (mod 10))
    colours = ctx.step('i18n', client=b, keys=['rbmk.control.red', 'rbmk.control.yellow'])['texts']
    yellow = re.sub('§.', '', colours['rbmk.control.yellow'])
    Z.click_at(ctx, a, hud_a, 11, 75)          # group keys at (6 + 11k, 70), 10 x 10; k = 0 red
    Z.click_at(ctx, a, hud_a, 22, 75, button=1)  # k = 1 yellow, right click
    _lib.server_steps(ctx, 11)
    ctx.step('wait', client=b, ticks=10)
    col_srv = [_lib.block_data(ctx, p).get('color') for p in rods]
    grid_sel = b_grid()
    rod_tips = [grid_sel[0], grid_sel[2]]
    ctx.check(CX + 'mp-console-select-group', built and linked and col_srv == [1, 1] and all(yellow in tips for tips in rod_tips),
              'built %s, linked %s; server rod colours after A\'s left click on red and right click on yellow %s (want [1, 1]); B grid tooltips %s '
              '(want %r on both rods)' % (built, linked, col_srv, grid_sel, yellow))
    ctx.not_run(CX + 'mp-console-set-depth', 'setting the depth needs a number typed into the console screen\'s text field before the save key '
                '(RBMKConsoleScreen.java:293-317); the executor\'s key step presses keys only and types no characters')

    # (b) screen type
    t_before = _lib.block_data(ctx, console).get('t0')
    Z.click_at(ctx, a, hud_a, 15, 17)          # screen 1 type button (6, 8), 18 x 18
    # the console sends a packet every tick, but the full packet of a game time = 0 (mod 10) tick carries no screen types (original
    # TileEntityRBMKConsole.java:191-220; NEO RBMKConsoleBlockEntity.java:191-221): two steps always include a packet with them
    _lib.server_steps(ctx, 2)
    ctx.step('wait', client=b, ticks=10)
    t_after = _lib.block_data(ctx, console).get('t0')
    t_b = client_nbt(ctx, b, console).get('t0')
    ctx.check(CX + 'mp-console-toggle', t_before == 0 and t_after == 1 and t_b == 1,
              't0 before %s, after A\'s click and 2 ticks %s, B client %s' % (t_before, t_after, t_b))
    ctx.review(CX + 'mp-console-visual', 'for a person at the user station: B\'s screen-type icon and the console model\'s screen after A\'s toggle')

    # (c) AZ-5: lid, then the button; sounds recorded on both clients
    for who in (a, b):
        ctx.step('sounds', client=who, action='start')
    Z.click_at(ctx, a, hud_a, 44, 152)         # AZ-5 at (30, 138), 28 x 28: the first click opens the lid
    Z.click_at(ctx, a, hud_a, 44, 152)
    ctx.step('wait', client=a, ticks=10)
    snd = {who: ctx.step('sounds', client=who, action='stop') for who in (a, b)}
    names = {who: sorted({str(e.get('event') or e.get('sound') or e) for e in snd[who].get('sounds', [])}) for who in (a, b)}
    targets = [_lib.block_data(ctx, p).get('targetLevel') for p in rods]
    t_az = ctx.server()['game_time']            # frozen: the rods move from the next step on
    _lib.server_steps(ctx, STEPS)
    ctx.step('wait', client=b, ticks=10)
    want = 1.0
    for _ in range(STEPS):
        want -= SPEED
    srv = [_lib.block_data(ctx, p).get('level') for p in rods]
    cli = {who: [client_nbt(ctx, who, p).get('level') for p in rods] for who in (a, b)}
    grid = b_grid()
    pct = [int(m) for tips in grid for t in tips for m in re.findall(r'(\d+)%', t)]
    # the console rescans every game time = 0 (mod 10) (RBMKConsoleBlockEntity.java:61-62); the rods were added first and tick
    # before it in the same game tick, so the last rescan holds the level after n = t_r - t_az decrements
    t_end = t_az + STEPS
    t_r = t_end - t_end % 10
    lvl = 1.0
    for _ in range(t_r - t_az):
        lvl -= SPEED
    want_pct = int(lvl * 100)
    snd_ok = (any('shutdown' in n for n in names[a]) and not any('shutdown' in n or 'az5' in n for n in names[b])
              and snd[a].get('engine_loaded', True))
    ok = (all(abs((v or 0) - 1.0) < 1e-12 for v in out) and targets == [0.0, 0.0] and srv == [want, want] and cli[a] == srv
          and cli[b] == srv and pct == [want_pct, want_pct] and snd_ok)
    ctx.check(CX + 'mp-console-az5', ok,
              'rods out %s; sounds A %s, B %s (engine loaded A %s, B %s); rod targets after AZ-5 %s at game time %d; after %d ticks: server %s '
              '(want %r), clients %s; B grid tooltips %s (last rescan at %d, %d decrements, want %d%%)'
              % (out, names[a], names[b], snd[a].get('engine_loaded'), snd[b].get('engine_loaded'), targets, t_az, STEPS, srv, want, cli, grid,
                 t_r, t_r - t_az, want_pct))

    # (d) reach: B 12 blocks away (inside the console's 20 blocks), then 21
    ctx.step('close', client=a)
    look_c = [console[0] + 0.5, G + 1, console[2] + 0.5]
    ctx.step('view', client=b, pos=[console[0] + 0.5, G, console[2] + 12.5], look_at=look_c, fly=True, hide_gui=False)
    ctx.step('wait', client=b, ticks=10)
    open12 = ctx.step('screen', client=b, expect='RBMKConsoleScreen', allow_fail=True)['status'] == 'ok'
    t1_before = _lib.block_data(ctx, console).get('t1')
    if open12:
        Z.click_at(ctx, b, hud_b, 55, 17)      # screen 2 type button (46, 8), 18 x 18
    _lib.server_steps(ctx, 2)
    t1_after = _lib.block_data(ctx, console).get('t1')
    ctx.check(CX + 'mp-console-reach-12', open12 and t1_before == 0 and t1_after == 1,
              'B at 12.0 blocks south of the console: screen open %s; t1 before %s, after B\'s click and 2 ticks %s'
              % (open12, t1_before, t1_after))
    reopened = False
    if not open12:                              # back to the console to open it again for the 21-block move
        Z.open_screen(ctx, b, (console[0], G + 1, console[2]), 'south', stand_b, 'RBMKConsoleScreen')
        reopened = True
    ctx.step('view', client=b, pos=[console[0] + 0.5, G, console[2] + 21.5], look_at=look_c, fly=True, hide_gui=False)
    ctx.step('wait', client=b, ticks=10)
    b_closed = ctx.step('screen', client=b, expect='none', allow_fail=True)['status'] == 'ok'
    ctx.check(CX + 'mp-console-reach-21', b_closed,
              'B (screen open again before the move: %s) at 21.0 blocks south of the console: screen closed %s' % (reopened, b_closed))

    # a still state for the restart: both rods at 50 % (rod screen level key k = 2 sets 1 - 2 x 0.25), reached and resting
    for rx, _, rz in rods:
        hud = R.open_column(ctx, a, rx, rz, 'RBMKControlScreen')
        Z.click_at(ctx, a, hud, 133, 53)     # level keys at (118, 26 + 11k), 30 x 10
        ctx.step('close', client=a)
    _lib.still(ctx, ctx.sprint(300, label='rods-half', timeout_s=120))
    pre_c = _lib.block_data(ctx, console)
    pre = dict(target=[pre_c.get('tX'), pre_c.get('tY'), pre_c.get('tZ')], t0=pre_c.get('t0'), t1=pre_c.get('t1'),
               rods=[_lib.block_data(ctx, p).get('level') for p in rods])
    _lib.server_idle(ctx, a)
    ctx.restart_server()
    ctx.server('tick freeze')
    ctx.step('wait', client=a, ticks=80)
    post_c = _lib.block_data(ctx, console)
    post = dict(target=[post_c.get('tX'), post_c.get('tY'), post_c.get('tZ')], t0=post_c.get('t0'), t1=post_c.get('t1'),
                rods=[_lib.block_data(ctx, p).get('level') for p in rods])
    cmp = _lib.compare_static(pre, post, not_quantity=('t0', 't1'))
    ctx.check(CX + 'mp-console-restart', cmp['ok'] and pre['rods'] == [0.5, 0.5], 'before %s, after %s; %s' % (pre, post, cmp['detail']))

    logs, lines = run_logs(ctx)
    client_lines, other = Z.bad_log_lines(lines)
    ctx.check(CX + 'mp-start-isolation', bool(logs) and not client_lines,
              'server logs of tag %s: %s (%d lines); client-class lines %s; other error lines (listed, not judged here) %s'
              % (getattr(ctx.run.args, 'tag', None), [p.name for p in logs], len(lines), client_lines[:5], other[:5]))
    _lib.server_idle(ctx, a)
    ctx.server('tick unfreeze')
