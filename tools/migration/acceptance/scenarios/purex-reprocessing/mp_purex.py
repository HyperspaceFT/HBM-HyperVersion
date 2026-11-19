"""Dedicated server: the PUREX on a server, two players at one PUREX, and a reprocessing alloy recipe crafted on the server.

A places the PUREX by hand; both players open its screen. A picks the natural uranium ZIRNOX row in the recipe selector (the
recipe button, the selector paged and clicked). The machine's power and its two input fluids are written into it by command
(预写); one cold natural uranium waste is given to A by command and shift-clicked in by A.

Expected (original 1.7.10 / NEO):
- purex.zirnoxnu: 1 cold natural uranium waste, 500 mB kerosene, 250 mB nitric acid, 100 ticks at 1,000 HE a tick ->
  1 U238 nugget, 2 reactor-grade plutonium nuggets, 1 Pu239 nugget, 2 tiny nuclear waste (original PUREXRecipes.java:89-97;
  NEO PUREXRecipes.java:50-57). The progress grows by speed / duration = 1/100 a tick (original ModuleMachineBase.java:117-130,
  NEO ModuleMachineBase.java:115-128): 0.5 after 50 ticks, done in tick 100; the machine's power then holds
  100,000 - 100 x 1,000 = 0.
- the recipe and the progress go to every client with the block entity packet (original TileEntityMachinePUREX.java:117,172-180;
  NEO MachinePUREXBlockEntity.serialize :246-254); the screen draws the progress bar from the client's copy, ceil(70 x progress)
  pixels (original GUIMachinePUREX.java:80-81; NEO MachinePUREXScreen.java:77-79); the slots go to every open screen through the menu.
- each player opens the screen for himself (original MachinePUREX.java:31-32, BlockDummyable.java:372-383; NEO
  MachinePUREXBlock.java:54-55, DummyableBlock.java:431-444), so two players have it open at the same time.
- a click in a container screen is handled on the server one after the other: two players taking the same output stack at
  once get it once between them; breaking the machine drops its contents once and closes every open screen of it.
- the server reads a custom recipe table only from config/hbmRecipes/hbmPUREX.json (NEO SerializableRecipe.java:91-112,126-140,
  PUREXRecipes.java:39); the shipped templates carry a leading underscore and are not read. Shift-clicked items go to the recipe
  inputs where the selected recipe (or its auto-switch group) accepts them, upgrades to slots 2-3 (original
  ContainerMachinePUREX.java:37-59; NEO MachinePUREXMenu.java:34-84).
- the reprocessing alloy row 2 reactor-grade plutonium nuggets + 4 U238 nuggets -> 1 plutonium fuel billet (shapeless, original
  MineralRecipes.java:163; NEO NtmRecipeProvider.java:3359-3363) crafts on the server's crafting table, and a client on the server
  finds it in JEI.
"""
import importlib.util
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402
import common  # noqa: E402

_spec = importlib.util.spec_from_file_location('zirnox_mp_rig', Path(__file__).resolve().parents[1] / 'zirnox-reactor' / 'mp_meltdown.py')
Z = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(Z)

SCENARIO = dict(
    id='purex-reprocessing.mp_purex',
    feature='purex-reprocessing',
    title='Dedicated server: PUREX recipe selection and progress on both clients, two players at one PUREX, alloy crafting',
    group='mp',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

G = Z.G
H = Z.H
SITE = (-40, -40)
N = 13                      # PUREX menu: 13 machine slots, then the player's main inventory and hotbar
OUT = {7: (H + 'nugget_u238', 1), 8: (H + 'nugget_pu_mix', 2), 9: (H + 'nugget_pu239', 1), 10: (H + 'nuclear_waste_tiny', 2)}
PX = 'purex-reprocessing.'
EXPECT = [
    ('mp-purex-select', '专服：服务端的配置目录里没有自定义的 hbmRecipes/hbmPUREX.json（只有带下划线、不读的模板），配方表是内置的；'
     'A 在专服上用选择器点天然铀 ZIRNOX 行，服务端 recipe0 是 purex.zirnoxnu，B 的客户端'
     '（同步的方块实体）也是它；电量 100,000 与煤油 500 mB、硝酸 250 mB 用命令写进机器（预写），A 把 1 个冷天然铀废料（命令发放）Shift 点进去；冻结世界走'
     ' 50 刻：服务端进度 0.5，B 客户端的进度相同；再走 50 刻：输入的废料与两种流体用完，产物 1 个铀-238 粒、2 个反应堆级钚粒、1 个钚-239 粒、'
     '2 个小撮核废料，电量 0，B 的界面里四个产物格与服务端相同',
     'PUREXRecipes.java:89-97, ModuleMachineBase.java:117-130; PUREXRecipes.java:39,50-57, SerializableRecipe.java:91-112,126-140, ModuleMachineBase.java:115-128, '
     'MachinePUREXBlockEntity.java:246-254'),
    ('mp-purex-both-open', '专服：两人同时打开同一台手放的 PUREX 的界面（两个客户端同时右键，A 在南面、B 在北面，各开各的）：'
     '随后同时读两个客户端，A 与 B 的 PUREX 界面都开着，后开的一方没有把先开的一方的界面挤掉',
     'MachinePUREX.java:31-32, BlockDummyable.java:372-383; MachinePUREXBlock.java:54-55, DummyableBlock.java:431-444'),
    ('mp-purex-progress-sync', '专服：进度同步到客户端（两人都开着界面）：上一行冻结世界走 50 刻时服务端进度 0.5，A、B 两个客户端的方块实体副本里的进度'
     '都与服务端相同（界面的进度条按这个副本画 ⌈70×进度⌉ 像素：进度是双精度数，每刻加 1/100，50 刻后是 0.5000000000000002，70 倍略大于 35，所以原版与 NEO 都画 36 像素）；走满 100 刻配方完成后服务端进度回到 0，两个客户端的副本也是 0',
     'GUIMachinePUREX.java:80-81, TileEntityMachinePUREX.java:117,172-180, ModuleMachineBase.java:117-130; '
     'MachinePUREXScreen.java:77-79, MachinePUREXBlockEntity.java:246-254, ModuleMachineBase.java:115-128'),
    ('mp-purex-recipe-sync', '专服：两人都开着界面；A 改选铀燃料 ZIRNOX 行，冻结世界走 1 刻：服务端与 B 客户端的配方都是 purex.zirnoxmeu',
     'MachinePUREXBlockEntity.java:246-254'),
    ('mp-purex-simultaneous-take', '专服：两人都开着界面，同时 Shift 取同一格反应堆级钚粒（2 个）：机器里没有了，两人一共多 2 个',
     'ContainerMachinePUREX.java:37-47; MachinePUREXMenu.java:34-47; container clicks on the server thread'),
    ('mp-purex-simultaneous-put', '专服：重启后两人再开界面（冻结），各拿 1 个冷天然铀废料（命令发放）同时 Shift 点进机器：输入格里有 2 个，两人手里都没有了',
     'ContainerMachinePUREX.java:59; MachinePUREXMenu.java:48-57,70-84, ModuleMachineBase.java:200-216'),
    ('mp-purex-simultaneous-upgrade', '专服：两人开着界面，A 拿 1 个速度升级 I、B 拿 1 个能耗升级 I（都不在主线阶段清单里，用命令发放，预写）同时 Shift 点进机器：'
     '两个升级格各有 1 个，两人手里都没有了',
     'ContainerMachinePUREX.java:57; MachinePUREXMenu.java:53-54, MachinePUREXBlockEntity.java:292-297'),
    ('mp-purex-break', '专服：B 开着界面、A 破坏机器：B 的界面关闭，地上的小撮核废料一共 2 个（机器里留下的那 2 个），没有复制',
     'MachinePUREXBlock drops; menu stillValid'),
    ('mp-purex-craft', '专服：在命令放下的工作台里，2 个反应堆级钚粒加 4 个铀-238 粒（缺的 3 个命令发放）无序合成 1 个钚燃料坯料，'
     '服务端背包多 1 个 billet_plutonium_fuel，原料少 2 与 4',
     'MineralRecipes.java:163; NtmRecipeProvider.java:3359-3363'),
    ('mp-purex-craft-jei', '专服：连在专服上的 B 客户端的 JEI 里，钚燃料坯料作为产物的合成配方里有 hbmsntm:billet_plutonium_fuel_from_nuggets，'
     '原料是 2 个反应堆级钚粒与 4 个铀-238 粒（配方表由服务端同步到客户端）',
     'MineralRecipes.java:163; NtmRecipeProvider.java:3359-3363'),
    ('mp-purex-restart', '专服重启后（静止、非默认的服务端读数）：配方、电量、两个输入罐与机器里留下的小撮核废料与重启前相同',
     'MachinePUREXBlockEntity.java:268-289'),
]


def expectations():
    return [dict(id=PX + k, text=t, source=s) for k, t, s in EXPECT]


def inv_slot(ctx, name, item):
    r = Z.rcon1(ctx, 'data get entity %s Inventory' % name)
    try:
        value = _lib.data_value(r)
    except Exception:  # noqa: BLE001
        return None
    for e in value if isinstance(value, list) else []:
        if e.get('id') == item and 0 <= e.get('Slot', -1) <= 35:
            return e['Slot'], e.get('count', 1)
    return None


def pick(ctx, who, core, name):
    """The recipe button, then the selector (as _lib.pick_recipe, for one client): returns (server recipe0, the hovered tooltip)."""
    idx, n = _lib.recipe_index('hbmPUREX.json', name, who)
    if idx is None:
        raise RuntimeError('%s is not in the selector list (%d entries)' % (name, n))
    hud = ctx.step('hud', client=who, frames=2)
    ctx.step('click', client=who, at=[hud['gui_left'] + 16, hud['gui_top'] + 134], after=4)
    ctx.step('screen', client=who, expect='RecipeSelectorScreen')
    hud = ctx.step('hud', client=who, frames=2)
    left, top = (hud['gui_scaled_width'] - 176) // 2, (hud['gui_scaled_height'] - 132) // 2
    size = max(0, math.ceil((n - 40) / 8.0))
    page = min(idx // 8, size)
    ctx.step('key', client=who, key='key.keyboard.enter', after=1)
    for _ in range(page // 5):
        ctx.step('key', client=who, key='key.keyboard.page.down', after=1)
    for _ in range(page % 5):
        ctx.step('key', client=who, key='key.keyboard.down', after=1)
    ind = idx - page * 8
    at = [left + 7 + 18 * (ind % 8) + 9, top + 17 + 18 * (ind // 8) + 9]
    ctx.step('hover', client=who, at=at, frames=3)
    tips = [t['text'] for t in ctx.step('hud', client=who, frames=3)['texts'] if t['text'].startswith('tooltip: ')]
    ctx.step('click', client=who, at=at, after=2)
    ctx.step('click', client=who, at=[left + 160, top + 98], after=4)
    ctx.step('screen', client=who, expect='MachinePUREXScreen')
    return _lib.block_data(ctx, core).get('recipe0'), tips[:1]


def client_nbt(ctx, who, pos):
    d = ctx.step('dump', client=who, **{'from': list(pos)})
    return _lib.parse_snbt(d['blocks'][0]['nbt']) if d['blocks'] and d['blocks'][0].get('nbt') else {}


def hovered(ctx, who, slot):
    r = ctx.step('hover', client=who, slot=slot, frames=3)
    return r.get('item')


def open_both(ctx, a, b, core):
    """Both players open the PUREX at the same time (two threads, one step channel per client), A from the south, B from the north;
    then both screens are read at once. Returns {name: screen step result}."""
    cx, cy, cz = core
    spec = {a: ((cx, cy, cz + 2), 'south', [cx + 0.5, G, cz + 5.5]), b: ((cx, cy, cz - 2), 'north', [cx + 0.5, G, cz - 4.5])}
    Z.both(ctx, lambda n: Z.open_screen(ctx, n, spec[n][0], spec[n][1], spec[n][2], 'MachinePUREXScreen'))
    return Z.both(ctx, lambda n: ctx.step('screen', client=n, expect='MachinePUREXScreen', allow_fail=True))


def run(ctx):
    a, b = list(ctx.channels)
    Z.setup_world(ctx, a, b)
    x, z = SITE
    core = Z.place_by_hand(ctx, a, H + 'machine_purex', x, z, H + 'machine_purex', ((x - 6, G, z - 8), (x + 6, G + 5, z + 2)))
    ctx.server('tick freeze')
    open_now = open_both(ctx, a, b, core)
    ctx.check(PX + 'mp-purex-both-open', all(open_now[n]['status'] == 'ok' for n in (a, b)),
              'opened by both clients at once; screens read together afterwards: A %s (%s), B %s (%s)'
              % (open_now[a]['status'], open_now[a].get('screen') or open_now[a].get('reason'), open_now[b]['status'],
                 open_now[b].get('screen') or open_now[b].get('reason')))
    rec, tips = pick(ctx, a, core, 'purex.zirnoxnu')
    _lib.server_steps(ctx, 1)          # the module types the input tanks for the recipe on its next tick
    d0 = _lib.block_data(ctx, core)
    tanks0 = _lib.tanks(d0)
    ctx.server('data merge block %d %d %d {power:100000L,i0:500,i1:250}' % core)
    ctx.rcon('give %s %swaste_natural_uranium 1' % (a, H))
    ctx.step('wait', client=a, ticks=6)
    s = inv_slot(ctx, a, H + 'waste_natural_uranium')
    Z.shift_click(ctx, a, _lib.menu_slot(N, s[0]))
    d1 = _lib.block_data(ctx, core)
    b_rec = client_nbt(ctx, b, core).get('recipe0')
    _lib.server_steps(ctx, 50)
    ctx.step('wait', client=b, ticks=10)
    d50 = _lib.block_data(ctx, core)
    b50 = client_nbt(ctx, b, core).get('progress0')
    a50 = client_nbt(ctx, a, core).get('progress0')
    _lib.server_steps(ctx, 50)
    ctx.step('wait', client=b, ticks=10)
    d100 = _lib.block_data(ctx, core)
    prog100 = {'server': d100.get('progress0'), a: client_nbt(ctx, a, core).get('progress0'), b: client_nbt(ctx, b, core).get('progress0')}
    outs = {slot: (_lib.slot_item(d100, slot) or {}).get('id') and (_lib.slot_item(d100, slot)['id'], _lib.slot_count(d100, slot)) for slot in OUT}
    b_view = {slot: hovered(ctx, b, slot) for slot in OUT}
    t100 = _lib.tanks(d100)
    session = common.read_json(common.SESSION) or {}
    recipe_dir = Path(session.get('run') or (common.REPO / 'run')) / 'config' / 'hbmRecipes'
    custom = (recipe_dir / 'hbmPUREX.json').exists()
    ok1 = (not custom and recipe_dir.is_dir() and rec == 'purex.zirnoxnu' and b_rec == 'purex.zirnoxnu' and _lib.slot_count(d1, 4, H + 'waste_natural_uranium') == 1
           and abs(d50.get('progress0', 0) - 0.5) < 1e-9 and b50 == d50.get('progress0') and outs == OUT and _lib.slot_count(d100, 4) == 0
           and d100.get('power') == 0 and t100.get('i0', {}).get('fill') == 0 and t100.get('i1', {}).get('fill') == 0
           and b_view == {k: v[0] for k, v in OUT.items()})
    ctx.check(PX + 'mp-purex-select', ok1,
              'server recipe directory %s: custom hbmPUREX.json %s; selector tooltip %s; server recipe0 %s, B client %s; tanks after the recipe %s; input slot 4 after the click %s; after 50 ticks '
              'progress %s (B client %s); after 100: outputs %s (want %s), input %d, power %s, tanks %s; B screen output slots %s'
              % (recipe_dir, custom, tips, rec, b_rec, {k: (v['type'], v['max']) for k, v in tanks0.items()}, _lib.slot_count(d1, 4), d50.get('progress0'), b50, outs, OUT,
                 _lib.slot_count(d100, 4), d100.get('power'), {k: v['fill'] for k, v in t100.items()}, b_view))
    p50 = d50.get('progress0')
    # the progress is a double that grows by min(speed / duration, 1) = 1/100 each tick (original ModuleMachineBase.java:117-130); fifty
    # such additions give 0.5000000000000002, not 0.5, so the bar of GUIMachinePUREX.java:80-81, ceil(70 x progress), is 36 pixels
    want50 = 0.0
    for _ in range(50):
        want50 += min(1 / 100, 1.0)
    want_bar = math.ceil(70 * want50)
    bar = {n: (math.ceil(70 * v) if isinstance(v, (int, float)) else None) for n, v in ((a, a50), (b, b50))}
    ctx.check(PX + 'mp-purex-progress-sync', p50 is not None and abs(p50 - 0.5) < 1e-9 and a50 == p50 and b50 == p50
              and all(v == want_bar for v in bar.values()) and prog100 == {'server': 0.0, a: 0.0, b: 0.0},
              'after 50 ticks: server progress %r, client copies A %r, B %r (progress bar ceil(70 x progress) px: %s, want %d from the '
              'original\'s accumulated %r); after 100 ticks (recipe done): %s (want 0 everywhere)' % (p50, a50, b50, bar, want_bar, want50, prog100))

    # two players: A changes the recipe, B's copy follows; both take slot 8 (2 Pu mix) at once
    rec2, _ = pick(ctx, a, core, 'purex.zirnoxmeu')
    _lib.server_steps(ctx, 1)          # the block entity packet goes out on the machine's tick; the world stands frozen
    ctx.step('wait', client=b, ticks=10)
    b_rec2 = client_nbt(ctx, b, core).get('recipe0')
    inv0 = {n: Z.inventory(ctx, n).get(H + 'nugget_pu_mix', 0) for n in (a, b)}
    Z.both(ctx, lambda n: Z.shift_click(ctx, n, 8))
    ctx.step('wait', client=a, ticks=10)
    d2 = _lib.block_data(ctx, core)
    inv1 = {n: Z.inventory(ctx, n).get(H + 'nugget_pu_mix', 0) for n in (a, b)}
    gained = sum(inv1.values()) - sum(inv0.values())
    took = _lib.slot_count(d2, 8) == 0 and gained == 2
    ctx.check(PX + 'mp-purex-recipe-sync', rec2 == 'purex.zirnoxmeu' and b_rec2 == rec2, 'A selected, server %s, B client %s' % (rec2, b_rec2))
    ctx.check(PX + 'mp-purex-simultaneous-take', took, 'Pu mix per player before %s, after %s (gained %d), slot 8 left %d'
              % (inv0, inv1, gained, _lib.slot_count(d2, 8)))
    # A takes the U238 and Pu239 nuggets; the tiny waste stays in the machine for the restart and the break
    Z.shift_click(ctx, a, 7)
    Z.shift_click(ctx, a, 9)
    ctx.server('data merge block %d %d %d {power:5000L,i0:300,i1:200}' % core)
    for who in (a, b):
        ctx.step('close', client=who)
    keep = ('recipe0', 'power')
    pre_d = _lib.block_data(ctx, core)
    pre = dict({k: pre_d.get(k) for k in keep}, tanks={k: v['fill'] for k, v in _lib.tanks(pre_d).items()}, tiny=_lib.slot_count(pre_d, 10))
    _lib.server_idle(ctx, a)
    ctx.restart_server()
    ctx.server('tick freeze')
    ctx.step('wait', client=a, ticks=80)
    post_d = _lib.block_data(ctx, core)
    post = dict({k: post_d.get(k) for k in keep}, tanks={k: v['fill'] for k, v in _lib.tanks(post_d).items()}, tiny=_lib.slot_count(post_d, 10))
    cmp = _lib.compare_static(pre, post, not_quantity=('recipe0',))
    ctx.check(PX + 'mp-purex-restart', cmp['ok'], 'before %s, after %s; %s' % (pre, post, cmp['detail']))

    # both open again, A breaks the machine
    open_both(ctx, a, b, core)
    # both put one cold natural uranium waste each into the machine at once: a shift-click from the player inventory tops up the
    # input slot 4 where the machine accepts it (original ContainerMachinePUREX.java:59; NEO MachinePUREXMenu.java:73-84; the selected
    # uranium fuel row's auto-switch group accepts the natural uranium waste, ModuleMachineBase.java:209-216). Done here, in the frozen
    # world after the restart, because a machine tick with this waste in slot 4 switches the recipe back to purex.zirnoxnu
    waste = H + 'waste_natural_uranium'
    for who in (a, b):
        ctx.rcon('give %s %s 1' % (who, waste))
    ctx.step('wait', client=a, ticks=6)
    put_from = {n: inv_slot(ctx, n, waste) for n in (a, b)}
    Z.both(ctx, lambda n: Z.shift_click(ctx, n, _lib.menu_slot(N, put_from[n][0])))
    ctx.step('wait', client=a, ticks=10)
    put_in = _lib.slot_count(_lib.block_data(ctx, core), 4, waste)
    put_left = {n: Z.inventory(ctx, n).get(waste, 0) for n in (a, b)}
    put_ok = put_in == 2 and sum(put_left.values()) == 0
    ctx.check(PX + 'mp-purex-simultaneous-put', put_ok, 'from inventory slots %s: input slot 4 holds %d, waste left per player %s'
              % (put_from, put_in, put_left))
    # both put an upgrade in at once: shift-clicked upgrades go to slots 2-3 (original ContainerMachinePUREX.java:57; NEO
    # MachinePUREXMenu.java:53-54); two different kinds, so each takes a slot of its own
    ups = {a: H + 'upgrade_speed_1', b: H + 'upgrade_power_1'}
    for who in (a, b):
        ctx.rcon('give %s %s 1' % (who, ups[who]))
    ctx.step('wait', client=a, ticks=6)
    up_from = {n: inv_slot(ctx, n, ups[n]) for n in (a, b)}
    Z.both(ctx, lambda n: Z.shift_click(ctx, n, _lib.menu_slot(N, up_from[n][0])))
    ctx.step('wait', client=a, ticks=10)
    du = _lib.block_data(ctx, core)
    up_slots = {k: (_lib.slot_item(du, k) or {}).get('id') for k in (2, 3)}
    up_left = {n: Z.inventory(ctx, n).get(ups[n], 0) for n in (a, b)}
    ctx.check(PX + 'mp-purex-simultaneous-upgrade', sorted(v for v in up_slots.values() if v) == sorted(ups.values())
              and all(_lib.slot_count(du, k) == 1 for k in (2, 3)) and sum(up_left.values()) == 0,
              'from inventory slots %s: upgrade slots %s, left per player %s' % (up_from, up_slots, up_left))

    ctx.step('close', client=a)
    cx, cy, cz = core
    ctx.step('key', client=a, key='key.keyboard.9', action='tap', after=2)
    ctx.step('view', client=a, pos=[cx + 0.5, G, cz + 5.5], look_at=_lib.face_point((cx, cy, cz + 2), 'south'), fly=True, hide_gui=False)
    hit = ctx.step('attack', client=a, target=dict(pos=[cx, cy, cz + 2], face='south'), any_hit=True, after=6)
    ctx.step('wait', client=b, ticks=10)
    gone = Z.block_is(ctx, core, 'minecraft:air')
    b_screen = ctx.step('screen', client=b, expect='none', allow_fail=True)
    drops = Z.rcon1(ctx, 'execute as @e[type=minecraft:item,nbt={Item:{id:"%snuclear_waste_tiny"}}] run data get entity @s Item.count' % H)
    tiny_dropped = sum(int(v) for v in re.findall(r'entity data:\s*(\d+)', drops))
    ctx.check(PX + 'mp-purex-break', gone and b_screen['status'] == 'ok' and tiny_dropped == 2,
              'break hit %s, block gone %s, B screen closed %s (%s); tiny waste dropped %d (%r)'
              % (hit.get('hit'), gone, b_screen['status'] == 'ok', b_screen.get('reason'), tiny_dropped, drops[:200]))
    ctx.rcon('kill @e[type=minecraft:item]')

    # crafting: whoever holds the 2 Pu mix nuggets crafts with 4 U238 nuggets (A has 1 from the machine, 3 more given)
    holder = a if Z.inventory(ctx, a).get(H + 'nugget_pu_mix', 0) >= 2 else b
    ctx.rcon('give %s %snugget_u238 %d' % (holder, H, 4 - Z.inventory(ctx, holder).get(H + 'nugget_u238', 0)))
    if holder != a:
        ctx.rcon('clear %s %snugget_u238' % (a, H))
    table = (x + 8, G, z)
    ctx.rcon('setblock %d %d %d minecraft:crafting_table' % table)
    before = Z.inventory(ctx, holder)
    Z.open_screen(ctx, holder, table, 'south', [table[0] + 0.5, G, table[2] + 2.5], 'CraftingScreen')
    for item, cells in ((H + 'nugget_pu_mix', (1, 2)), (H + 'nugget_u238', (4, 5, 6, 7))):
        s = inv_slot(ctx, holder, item)
        src = _lib.menu_slot(10, s[0])
        ctx.step('click', client=holder, slot=src, after=2)
        for c in cells:
            ctx.step('click', client=holder, slot=c, button=1, after=2)
        ctx.step('click', client=holder, slot=src, after=2)
    Z.shift_click(ctx, holder, 0)
    ctx.step('close', client=holder)
    gain = _lib.delta(Z.inventory(ctx, holder), before)
    want = {H + 'billet_plutonium_fuel': 1, H + 'nugget_pu_mix': -2, H + 'nugget_u238': -4}
    ctx.check(PX + 'mp-purex-craft', gain == want, '%s crafted at %s: inventory change %s (want %s)' % (holder, table, gain, want))
    found = ctx.step('jei', client=b, action='lookup', item=H + 'billet_plutonium_fuel', role='output').get('crafting', [])
    rec_j = [r for r in found if r.get('id') == H + 'billet_plutonium_fuel_from_nuggets']
    ins = sorted(tuple(alts) for alts in rec_j[0].get('ingredients', [])) if rec_j else []
    want_ins = sorted([(H + 'nugget_pu_mix',)] * 2 + [(H + 'nugget_u238',)] * 4)
    ctx.check(PX + 'mp-purex-craft-jei', bool(rec_j) and ins == want_ins,
              'B client JEI crafting recipes for billet_plutonium_fuel: %s; the nugget recipe ingredients %s (want %s)'
              % ([r.get('id') for r in found], ins, want_ins))
    _lib.server_idle(ctx, a)
