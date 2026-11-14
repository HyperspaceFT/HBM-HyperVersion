"""Two players on a dedicated server: what one does the other sees, state across chunk unloading and a server restart.

Expected values follow the 1.7.10 original at cd0cff450 and the NEO port:
- moving items and packages are server entities every client sees at the same place (NEO syncs every 3 ticks and
  interpolates, deliberate NEO difference); a package's contents are not sent to clients (EntityMovingPackage has no watched data).
- belts built with the placing tool are ordinary blocks every client gets; the route preview is drawn only by the client
  holding the tool (NEO draws the preview on the client).
- crane filters, modes and upgrades, sorter modes, splitter ratios and moving items are saved with their chunks
  (TileEntityCrane*.writeToNBT, EntityMovingConveyorObject) and survive unloading and a restart.
- screens: a change made in one player's screen goes to the server and is what another player sees (IControlReceiver);
  the sorter screen closes when its player walks away (Container.canInteractWith, about 8 blocks).
- the settings tool pastes on the server for everyone; its hint is drawn only for its holder; an adventure-mode player
  cannot paste (ItemSettingsTool, NEO: the paste needs a player allowed to build).
- the splitter's ratio text comes from the synced block entity every tick (CraneSplitter.printHook).
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402
import common  # noqa: E402

SCENARIO = dict(
    id='conveyor-cranes.multiplayer',
    feature='conveyor-cranes',
    title='Two players: same items and packages, wand build, unload and restart, removals, screens, settings tool, ratio text',
    group='mp',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

G = -60
X0 = 200
RING = [(0, 0, 'south', 'right'), (1, 0, 'west', 'straight'), (2, 0, 'west', 'right'), (2, 1, 'north', 'straight'),
        (2, 2, 'north', 'right'), (1, 2, 'east', 'straight'), (0, 2, 'east', 'right'), (0, 1, 'south', 'straight')]
T = dict(ratio='分离比例：', max_eject='只取满额', destroy='销毁溢出物品', on='开', off='关', modes=['关闭', '白名单', '黑名单', '通配'],
         exact='物品与元数据相同', iron='铁锭', hint=('过滤器', '方向'), wild='物品相同', tag='物品标签匹配：', copied='已复制')


def expectations():
    E = [('conveyor-cranes.mp-belt-same-position', 'both clients see a moving item at the same place (within half a block)', 'NEO sends positions every 3 ticks'),
         ('conveyor-cranes.mp-belt-smooth', 'both clients draw the moving item forward only, steps under 0.2 block per frame', 'NEO interpolates between updates'),
         ('conveyor-cranes.mp-package-both', 'both clients see the package at the same place; neither gets its contents', 'EntityMovingPackage (no watched data)'),
         ('conveyor-cranes.mp-belt-wand-build', 'alice builds a line with the placing tool, bob sees the belts; the preview exists only on alice\'s client', 'client-side preview'),
         ('conveyor-cranes.mp-unload', 'after both players leave 400 blocks away (chunk unloaded: two "not loaded" answers in a row, and the entity '
          'chunk file written after a flush) and return: the ring item still there and moving, '
          'extractor filter, whitelist, upgrades, sorter modes and splitter ratio kept', 'writeToNBT of the cranes; EntityMovingConveyorObject'),
         ('conveyor-cranes.mp-restart', 'after a server restart the same state is kept and the ring item moves', 'writeToNBT; entity save'),
         ('conveyor-cranes.mp-package-removal', 'alice breaks a package: bob sees it gone and its items on the ground', 'EntityMovingPackage.attackEntityFrom'),
         ('conveyor-cranes.mp-screen-sync', 'alice toggles the extractor switches, a filter mode, the inserter destroyer and a sorter mode; bob opens them and reads the same',
          'IControlReceiver; GUICrane* hover texts'),
         ('conveyor-cranes.mp-settings-copy-paste', 'alice copies an extractor and pastes it onto another; bob opens it and sees the pasted '
          'filter (the copy carries the sides and the filter items, not the switches)', 'TileEntityCraneBase.java:112-175'),
         ('conveyor-cranes.mp-settings-hint-own', 'the settings tool hint is drawn on alice\'s screen only', 'hint overlay (client side)'),
         ('conveyor-cranes.mp-router-far', 'alice\'s sorter screen closes when she is moved 12 blocks away', 'Container.canInteractWith'),
         ('conveyor-cranes.mp-splitter-ratio', 'alice changes a splitter ratio with the screwdriver, bob aiming at it reads the new ratio', 'CraneSplitter.printHook'),
         ('conveyor-cranes.mp-settings-adventure', 'bob in adventure mode: sneak-use copies a sorter and an extractor (one "copied" line each, '
          'no screen); use with that data on another sorter and another extractor is refused (settings unchanged, no screen); use on '
          'a chest goes to the chest (its screen opens)', 'ItemSettingsTool.onItemUseFirst:81-122 runs before the block; NEO: copying '
          'needs no build permission, pasting does'),
         ('conveyor-cranes.mp-settings-once', 'bob in survival and in creative: one sneak-use copies a sorter with exactly one "copied" line and '
          'no screen, one use pastes it onto another sorter (modes and the filter item as copied), no screen', 'ItemSettingsTool.onItemUseFirst:81-122'),
         ('conveyor-cranes.mp-duct-ctrl', 'alice copies a water duct with the settings tool and pastes it with Ctrl held on one of six connected '
          'fluid ducts: the server sets all six to water and bob\'s client holds water on all six; the same paste without Ctrl on another run '
          'changes one duct only', 'TileEntityPipeBaseNT.pasteSettings:145-162 (TOOL_CTRL: changeTypeRecursively)'),
         ('conveyor-cranes.mp-belt-edge-pileup', 'record: items sent every 20 ticks along a 200-block belt while alice stays at the start: pile-up or tiny explosions at a chunk edge',
          'record item, no pass line'),
         ('conveyor-cranes.mp-belt-log', 'the server log of the session has no Exception or Error line (a connection reset by a client '
          'quitting for the restart is listed, not counted)', 'server log')]
    return [dict(id=i, text=t, source=s) for i, t, s in E]


def text_of(r):
    return ' '.join(m['text'] for m in r.get('messages', []))


def moving(ctx, who, a, b, kind='hbmsntm:moving_item'):
    return [e for e in ctx.step('dump', client=who, **{'from': a, 'to': b}, entities=True)['entities'] if e['type'] == kind]


def tips(ctx, who):
    return [x['text'][len('tooltip: '):] for x in ctx.step('hud', client=who, frames=4)['texts'] if x['text'].startswith('tooltip: ')]


def open_block(ctx, who, pos, face='south', expect='Screen'):
    off = _lib.VEC[face]
    ctx.step('view', client=who, pos=[pos[0] + 0.5 + 2 * off[0], G, pos[2] + 0.5 + 2 * off[2]], look_at=[pos[0] + 0.5, pos[1] + 0.5, pos[2] + 0.5],
             fly=False, hide_gui=False)
    ctx.step('use', client=who, target=dict(pos=list(pos), face=face), after=6)
    return ctx.step('screen', client=who, expect=expect, allow_fail=True)


def aside(ctx, who):
    """moves a player out of the other player's line of sight (a use aimed through a player hits the player)"""
    ctx.rcon('tp %s %d %d 14' % (who, X0 + 4, G))


def server_value(ctx, pos, path):
    r = ctx.rcon(('data get block %d %d %d %s' % (pos[0], pos[1], pos[2], path)).strip())
    return r[0] if r else ''


def state(ctx, ex, router, split_core):
    return dict(filter=server_value(ctx, ex, 'Items[{Slot:0b}].id'), whitelist=server_value(ctx, ex, 'isWhitelist'),
                upgrade=server_value(ctx, ex, 'Items[{Slot:18b}].id'), modes=server_value(ctx, router, 'modes'),
                left=server_value(ctx, split_core, 'left'), right=server_value(ctx, split_core, 'right'))


# what state() must read before the unload: the values set by the commands above (a failed read would make before,
# after and restart all equal and pass without testing anything)
SET = dict(filter='"minecraft:iron_ingot"', whitelist='1b', upgrade='"hbmsntm:upgrade_stack_2"', modes='[I; 1, 2, 3, 0, 1, 2]', left='3b', right='2b')


def strip_pos(s):
    return {k: re.sub(r'^.*?(has the following block data|拥有以下方块数据)[:：]\s*', '', v) for k, v in s.items()}


def ring_item(ctx):
    r = ctx.rcon('data get entity @e[type=hbmsntm:moving_item,x=%d,y=%d,z=0,distance=..3,limit=1] Pos' % (X0 + 1, G))
    m = re.findall(r'(-?\d+\.\d+)d', r[0] if r else '')
    return [float(v) for v in m] if m else None


def run(ctx):
    a, b = list(ctx.channels)
    session = common.read_json(common.SESSION)
    log = Path(session['log']) if session else None
    first_line = len(log.read_text(encoding='utf-8', errors='replace').splitlines()) if log and log.exists() else 0
    ctx.rcon('gamemode creative %s' % a, 'gamemode creative %s' % b, 'time set 6000', 'weather clear', 'gamerule doDaylightCycle false',
             'gamerule doMobSpawning false', 'tp %s %d %d 6' % (a, X0 + 2, G), 'tp %s %d %d 8' % (b, X0 + 4, G))
    for who in (a, b):
        ctx.step('view', client=who, pos=[X0 + 6.5, G + 6, 8.5], pitch=60.0, yaw=180.0, fly=True, hide_gui=False)
    ctx.step('wait', client=a, ticks=60)
    # 9.1: a straight belt, one item and one package
    ctx.rcon('fill %d %d 20 %d %d 20 hbmsntm:conveyor[facing=west,shape=straight]' % (X0, G, X0 + 30, G))
    ctx.step('wait', client=a, ticks=10)
    ctx.rcon('summon minecraft:item %d.5 %.1f 20.5 {Item:{id:"minecraft:iron_ingot",count:1}}' % (X0, G + 0.6))
    ctx.step('wait', client=a, ticks=30)
    pa = moving(ctx, a, [X0, G - 1, 19], [X0 + 30, G + 1, 21])
    pb = moving(ctx, b, [X0, G - 1, 19], [X0 + 30, G + 1, 21])
    diff = abs(pa[0]['pos'][0] - pb[0]['pos'][0]) if pa and pb else None
    ctx.check('conveyor-cranes.mp-belt-same-position', diff is not None and diff < 0.5, '%s x %s, %s x %s' % (a, pa and pa[0]['pos'], b, pb and pb[0]['pos']))
    tracks = {who: ctx.step('track', client=who, center=[X0 + 15, G + 0.5, 20], radius=20, type='hbmsntm:moving_item', ticks=40) for who in (a, b)}
    smooth = {who: [(e['reversals'], round(e['max_step'], 3)) for e in t.get('entities', [])] for who, t in tracks.items()}
    ok = all(v and all(r == 0 and m < 0.2 for r, m in v) for v in smooth.values())
    ctx.check('conveyor-cranes.mp-belt-smooth', ok, '(reversals, max step) per client %s; window active %s' % (
        smooth, {who: t.get('window_active') for who, t in tracks.items()}))
    ctx.rcon('summon hbmsntm:moving_package %d.5 %.2f 20.5 {count:1,contents:[{slot:0b,id:"minecraft:dirt",count:5}]}' % (X0 + 2, G + 0.25))
    ctx.step('wait', client=a, ticks=20)
    ka = moving(ctx, a, [X0, G - 1, 19], [X0 + 30, G + 1, 21], 'hbmsntm:moving_package')
    kb = moving(ctx, b, [X0, G - 1, 19], [X0 + 30, G + 1, 21], 'hbmsntm:moving_package')
    ok = len(ka) == 1 and len(kb) == 1 and abs(ka[0]['pos'][0] - kb[0]['pos'][0]) < 0.5
    ctx.check('conveyor-cranes.mp-package-both', ok, 'packages seen: %s %s, %s %s (contents are server-side only)' % (a, [e['pos'] for e in ka], b, [e['pos'] for e in kb]))
    # 9.4: alice breaks the package (ticks frozen so it stays put)
    ctx.rcon('tick freeze')
    if ka:
        px, py, pz = ka[0]['pos']
        ctx.step('view', client=a, eye=[px, py + 1.8, pz + 1.8], look_at=[px, py + 0.2, pz], fly=True, hide_gui=False)
        ctx.step('attack', client=a, target=dict(pos=[int(px), G, int(pz)], face='up', offset=[px - int(px) - 0.5, -0.75, pz - int(pz) - 0.5]), any_hit=True, after=6)
    ctx.step('wait', client=b, ticks=6)
    gone = moving(ctx, b, [X0, G - 1, 19], [X0 + 30, G + 1, 21], 'hbmsntm:moving_package')
    drops = [e for e in ctx.step('dump', client=b, **{'from': [X0, G - 1, 18], 'to': [X0 + 30, G + 2, 22]}, entities=True)['entities']
             if e['type'] == 'minecraft:item' and e.get('item') == 'minecraft:dirt']
    ctx.rcon('tick unfreeze')
    ctx.check('conveyor-cranes.mp-package-removal', not gone and sum(e['count'] for e in drops) == 5, 'packages left on bob\'s client %d; dirt on the ground %s' % (
        len(gone), [e['count'] for e in drops]))
    ctx.rcon('kill @e[type=minecraft:item]', 'kill @e[type=hbmsntm:moving_item]')
    # 9.2: alice builds with the placing tool
    ctx.rcon('setblock %d %d 30 minecraft:stone' % (X0, G), 'setblock %d %d 30 minecraft:stone' % (X0 + 10, G),
             'item replace entity %s weapon.mainhand with hbmsntm:conveyor_wand 64' % a)
    ctx.step('view', client=a, pos=[X0 + 2.5, G, 32.5], look_at=[X0 + 1.0, G + 0.5, 30.5], fly=True, hide_gui=False)
    ctx.step('use', client=a, target=dict(pos=[X0, G, 30], face='east'), after=4)
    ctx.step('view', client=a, pos=[X0 + 8.5, G, 32.5], look_at=[X0 + 10.0, G + 0.5, 30.5], fly=True, hide_gui=False)
    ctx.step('wait', client=a, ticks=6)
    prev_a, prev_b = ctx.step('preview', client=a), ctx.step('preview', client=b)
    ctx.step('use', client=a, target=dict(pos=[X0 + 10, G, 30], face='west'), after=6)
    ctx.step('wait', client=b, ticks=10)
    belts_b = [x for x in ctx.step('dump', client=b, **{'from': [X0, G, 29], 'to': [X0 + 10, G + 1, 31]})['blocks'] if x['block'].startswith('hbmsntm:conveyor')]
    ctx.check('conveyor-cranes.mp-belt-wand-build', prev_a.get('present') and not prev_b.get('present') and len(belts_b) >= 8,
              'preview on %s %s, on %s %s; belts bob sees %d' % (a, prev_a.get('present'), b, prev_b.get('present'), len(belts_b)))
    # 9.3: a ring with an item, an extractor, a sorter and a splitter near it; unload, return, restart
    for dx, dz, facing, shape in RING:
        ctx.rcon('setblock %d %d %d hbmsntm:conveyor[facing=%s,shape=%s]' % (X0 + dx, G, dz, facing, shape))
    ex, router = (X0 + 6, G, 0), (X0 + 8, G, 0)
    ctx.rcon('setblock %d %d %d hbmsntm:crane_extractor[input=north,output=south]' % ex,
             'item replace block %d %d %d container.0 with minecraft:iron_ingot' % ex,
             'item replace block %d %d %d container.18 with hbmsntm:upgrade_stack_2' % ex,
             'data merge block %d %d %d {isWhitelist:1b}' % ex,
             'setblock %d %d %d hbmsntm:crane_router' % router,
             'data merge block %d %d %d {modes:[I;1,2,3,0,1,2]}' % router,
             'summon minecraft:item %d.5 %.1f 0.5 {Item:{id:"minecraft:gold_ingot",count:1}}' % (X0 + 1, G + 0.6),
             'item replace entity %s weapon.mainhand with hbmsntm:crane_splitter' % a)
    ctx.step('view', client=a, pos=[X0 + 12.5, G, 3.5], look_at=[X0 + 12.5, G - 0.5, 0.5], fly=False, hide_gui=False)
    ctx.step('use', client=a, target=dict(pos=[X0 + 12, G - 1, 0], face='up'), after=6)
    split_core = (X0 + 12, G, 0)
    ctx.rcon('data merge block %d %d %d {left:3b,right:2b}' % split_core)
    ctx.step('wait', client=a, ticks=20)
    before = strip_pos(state(ctx, ex, router, split_core))
    # unloading and saving shown from the files: everything is flushed now, the ring item keeps moving, so the entity
    # chunk holding it is written again only when its chunk is saved on unloading
    ctx.rcon('save-all flush')
    world = Path(common.read_json(common.SESSION)['world'])
    files = [world / 'entities' / 'r.0.0.mca', world / 'region' / 'r.0.0.mca']
    flushed = {f.name + ' ' + f.parent.name: f.stat().st_mtime if f.exists() else None for f in files}
    item_before = ring_item(ctx)
    ctx.rcon('tp %s %d %d 0' % (a, X0 + 400, G + 5), 'tp %s %d %d 4' % (b, X0 + 400, G + 5))
    unloaded, misses = None, 0
    for _ in range(20):
        ctx.step('wait', client=a, ticks=40)
        r = ctx.rcon('execute if loaded %d %d 0' % (X0 + 1, G))
        if r and ('failed' in r[0].lower() or '失败' in r[0]):
            misses += 1
            # two answers in a row 40 ticks apart, so a chunk that is only between tickets does not count
            if misses == 2:
                unloaded = r[0]
                break
        else:
            misses = 0
    ent = files[0]
    saved_at = ent.stat().st_mtime if ent.exists() else None
    saved = unloaded is not None and saved_at is not None and flushed[ent.name + ' ' + ent.parent.name] is not None and saved_at > flushed[ent.name + ' ' + ent.parent.name]
    forced = ctx.rcon('forceload query')
    not_forced = any('No force loaded chunks' in x for x in forced)
    region = files[1]
    region_at = region.stat().st_mtime if region.exists() else None
    ctx.rcon('tp %s %d %d 6' % (a, X0 + 2, G), 'tp %s %d %d 8' % (b, X0 + 4, G))
    ctx.step('wait', client=a, ticks=60)
    idle_back = _lib.server_idle(ctx, a)
    after = strip_pos(state(ctx, ex, router, split_core))
    item_after = ring_item(ctx)
    ctx.step('wait', client=a, ticks=20)
    item_later = ring_item(ctx)
    moved = item_after is not None and item_later is not None and item_after != item_later
    set_ok = all(before.get(k, '').strip() == v for k, v in SET.items())
    region_flush = flushed[region.name + ' ' + region.parent.name]
    region_saved = region_at is not None and region_flush is not None and region_at > region_flush
    ctx.check('conveyor-cranes.mp-unload', set_ok and unloaded is not None and saved and region_saved and not_forced and after == before and moved,
              'unloaded (two misses in a row): %s; entity chunk file written after the flush %s (flush %s, after unloading %s); region file written after the flush %s (%s); forceload %s; '
              'state before %s, after %s; ring item %s -> %s -> %s; tick query after the return %s' % (
                  unloaded, saved, flushed, saved_at, region_saved, region_at, forced, before if set_ok else ('NOT AS SET %s' % before), after, item_before, item_after, item_later, idle_back[-1:]))
    idle_restart = _lib.server_idle(ctx, a)
    ctx.restart_server()
    for who in (a, b):
        ctx.step('view', client=who, pos=[X0 + 6.5, G + 6, 8.5], pitch=60.0, yaw=180.0, fly=True, hide_gui=False)
    ctx.step('wait', client=a, ticks=60)
    ctx.rcon('gamemode creative %s' % a, 'gamemode creative %s' % b)
    restarted = strip_pos(state(ctx, ex, router, split_core))
    i1 = ring_item(ctx)
    ctx.step('wait', client=a, ticks=20)
    i2 = ring_item(ctx)
    ctx.check('conveyor-cranes.mp-restart', set_ok and restarted == before and i1 is not None and i1 != i2, 'state after the restart %s (before %s); ring item %s -> %s' % (
        restarted, before, i1, i2))
    # screens: alice changes, bob reads
    ins = (X0 + 14, G, 6)
    ex2 = (X0 + 16, G, 6)
    ctx.rcon('setblock %d %d %d hbmsntm:crane_inserter[input=north,output=south]' % ins,
             'setblock %d %d %d hbmsntm:crane_extractor[input=north,output=south]' % ex2,
             'item replace entity %s weapon.mainhand with minecraft:air' % a, 'item replace entity %s weapon.mainhand with minecraft:air' % b)
    seen = {}
    if open_block(ctx, a, ex2, expect='Extractor')['status'] == 'ok':
        hud = ctx.step('hud', client=a, frames=3)
        L, Tp = hud['gui_left'], hud['gui_top']
        ctx.step('jei', client=a, action='ghost', item='minecraft:iron_ingot', target=0, allow_fail=True)
        ctx.step('click', client=a, slot=0, button=1, after=4)
        ctx.step('click', client=a, at=[L + 128 + 7, Tp + 30 + 13], button=0, after=4)   # whitelist
        ctx.step('click', client=a, at=[L + 187 + 9, Tp + 34 + 9], button=0, after=4)    # max eject
        ctx.step('close', client=a)
    if open_block(ctx, a, ins, expect='Inserter')['status'] == 'ok':
        hud = ctx.step('hud', client=a, frames=3)
        ctx.step('click', client=a, at=[hud['gui_left'] + 151 + 9, hud['gui_top'] + 34 + 9], button=0, after=4)
        ctx.step('close', client=a)
    if open_block(ctx, a, router, face='east', expect='Router')['status'] == 'ok':
        hud = ctx.step('hud', client=a, frames=3)
        ctx.step('click', client=a, at=[hud['gui_left'] + 16, hud['gui_top'] + 25], button=0, after=4)  # down side: 1 -> 2
        ctx.step('close', client=a)
    aside(ctx, a)
    if open_block(ctx, b, ex2, expect='Extractor')['status'] == 'ok':
        hud = ctx.step('hud', client=b, frames=3)
        ctx.step('hover', client=b, slot=0, frames=3)
        seen['filter'] = [l for l in tips(ctx, b) if l in (T['exact'], T['wild']) or l.startswith(T['tag'])]
        ctx.step('hover', client=b, at=[hud['gui_left'] + 187 + 9, hud['gui_top'] + 34 + 9], frames=3)
        seen['max_eject'] = [l for l in tips(ctx, b) if T['max_eject'] in l]
        ctx.step('close', client=b)
    if open_block(ctx, b, ins, expect='Inserter')['status'] == 'ok':
        hud = ctx.step('hud', client=b, frames=3)
        ctx.step('hover', client=b, at=[hud['gui_left'] + 151 + 9, hud['gui_top'] + 34 + 9], frames=3)
        seen['destroyer'] = [l for l in tips(ctx, b) if T['destroy'] in l]
        ctx.step('close', client=b)
    if open_block(ctx, b, router, face='east', expect='Router')['status'] == 'ok':
        hud = ctx.step('hud', client=b, frames=3)
        ctx.step('hover', client=b, at=[hud['gui_left'] + 16, hud['gui_top'] + 25], frames=3)
        seen['router_down'] = tips(ctx, b)[:1]
        ctx.step('close', client=b)
    server = dict(whitelist=server_value(ctx, ex2, 'isWhitelist'), max_eject=server_value(ctx, ex2, 'maxEject'), destroyer=server_value(ctx, ins, 'destroyer'))
    ok = (seen.get('filter') == [T['wild']] and seen.get('max_eject') and seen['max_eject'][0].endswith(T['on'])
          and seen.get('destroyer') and seen['destroyer'][0].endswith(T['off']) and seen.get('router_down') == [T['modes'][2]])
    ctx.check('conveyor-cranes.mp-screen-sync', bool(ok), 'bob reads %s; server %s' % (seen, server))
    # 9.6: settings tool copy and paste across clients; hint only on alice
    ex3 = (X0 + 18, G, 6)
    ctx.rcon('setblock %d %d %d hbmsntm:crane_extractor[input=north,output=south]' % ex3,
             'item replace entity %s weapon.mainhand with hbmsntm:settings_tool' % a)
    ctx.step('view', client=a, pos=[ex2[0] + 0.5, G, 8.5], look_at=[ex2[0] + 0.5, G + 0.5, 6.5], fly=False, hide_gui=False)
    ctx.step('key', client=a, key='key.keyboard.left.shift', action='press', after=3)
    ctx.step('use', client=a, target=dict(pos=list(ex2), face='south'), after=6)
    ctx.step('key', client=a, key='key.keyboard.left.shift', action='release', after=3)
    # the hint lists the copied entries (copytool.filter, copytool.orientation); the chat line naming the extractor is not it
    hint_a = [x['text'] for x in ctx.step('hud', client=a, frames=5)['texts'] if x['text'] in T['hint']]
    # bob looks at the same extractor without the tool: no hint may be drawn for him
    ctx.step('view', client=b, pos=[ex2[0] + 0.5, G + 1, 9.5], look_at=[ex2[0] + 0.5, G + 0.5, 6.5], fly=True, hide_gui=False)
    ctx.step('wait', client=b, ticks=4)
    hint_b = [x['text'] for x in ctx.step('hud', client=b, frames=5)['texts'] if x['text'] in T['hint']]
    ctx.step('view', client=a, pos=[ex3[0] + 0.5, G, 8.5], look_at=[ex3[0] + 0.5, G + 0.5, 6.5], fly=False, hide_gui=False)
    ctx.step('use', client=a, target=dict(pos=list(ex3), face='south'), after=6)
    aside(ctx, a)
    pasted = []
    if open_block(ctx, b, ex3, expect='Extractor')['status'] == 'ok':
        hud = ctx.step('hud', client=b, frames=3)
        ctx.step('hover', client=b, slot=0, frames=3)
        pasted = tips(ctx, b)
        ctx.step('close', client=b)
    filt = server_value(ctx, ex3, 'Items[{Slot:0b}].id')
    ctx.check('conveyor-cranes.mp-settings-copy-paste', any(T['iron'] in l for l in pasted) and 'minecraft:iron_ingot' in filt,
              'bob hovers filter slot 0 of the pasted extractor: %s; server filter slot 0 %s' % (pasted, filt))
    ctx.check('conveyor-cranes.mp-settings-hint-own', bool(hint_a) and not hint_b, 'hint entries drawn: on %s %s, on %s (same extractor, no tool) %s' % (a, hint_a, b, hint_b))
    # 9.6d: the sorter screen closes when alice is moved away
    ctx.rcon('item replace entity %s weapon.mainhand with minecraft:air' % a)
    far = 'the sorter screen never opened'
    if open_block(ctx, a, router, face='east', expect='Router')['status'] == 'ok':
        ctx.rcon('tp %s %d %d 0' % (a, router[0] + 12, G))
        ctx.step('wait', client=a, ticks=20)
        far = ctx.step('hud', client=a, frames=2).get('screen')
    ctx.check('conveyor-cranes.mp-router-far', far is None, 'screen on %s after the move: %s' % (a, far))
    # 9.7: splitter ratio, alice with the screwdriver, bob reads
    ctx.rcon('item replace entity %s weapon.mainhand with hbmsntm:screwdriver' % a, 'tp %s %d %d 3' % (a, split_core[0], G))
    ctx.step('view', client=a, pos=[split_core[0] + 0.5, G, 2.5], look_at=[split_core[0] + 0.5, G + 0.2, 0.5], fly=False, hide_gui=False)
    ctx.step('use', client=a, target=dict(pos=list(split_core), face='up', offset=[0, -0.6, 0]), any_hit=True, after=6)
    aside(ctx, a)
    ctx.step('view', client=b, pos=[split_core[0] + 0.5, G, 2.8], look_at=[split_core[0] + 0.5, G + 0.2, 0.5], fly=False, hide_gui=False)
    ctx.step('wait', client=b, ticks=6)
    ratio = [x['text'] for x in ctx.step('hud', client=b, frames=5)['texts'] if T['ratio'] in x['text']]
    ctx.check('conveyor-cranes.mp-splitter-ratio', ratio == [T['ratio'] + '4:2'], 'bob reads %s (3:2 before alice\'s click)' % ratio)
    settings_tool_modes(ctx, b, router, ex2)
    duct_ctrl(ctx, a, b)
    # a 200-block belt fed every 20 ticks while alice stays at its start
    ctx.rcon('fill %d %d 60 %d %d 60 hbmsntm:conveyor[facing=west,shape=straight]' % (X0, G, X0 + 199, G),
             'setblock %d %d 60 minecraft:chest' % (X0 - 2, G),
             'setblock %d %d 60 hbmsntm:crane_extractor[input=east,output=west]' % (X0 - 1, G),
             'item replace block %d %d 60 container.0 with minecraft:cobblestone 64' % (X0 - 2, G),
             'tp %s %d %d 62' % (a, X0, G), 'tp %s %d %d 62' % (b, X0 + 2, G))
    ctx.step('wait', client=a, ticks=2400)
    ctx.rcon('tp %s %d %d 62' % (b, X0 + 199, G + 3))
    ctx.step('wait', client=b, ticks=80)
    far_items = moving(ctx, b, [X0 + 150, G - 1, 59], [X0 + 205, G + 2, 61])
    ground = [e for e in ctx.step('dump', client=b, **{'from': [X0 + 150, G - 1, 57], 'to': [X0 + 205, G + 2, 63]}, entities=True)['entities']
              if e['type'] == 'minecraft:item']
    counts = ctx.rcon('execute if entity @e[type=hbmsntm:moving_item,x=%d,y=%d,z=60,dx=200,dy=2,dz=1]' % (X0, G - 1))
    xs = sorted(round(e['pos'][0]) for e in far_items)
    ctx.review('conveyor-cranes.mp-belt-edge-pileup', 'after 2 minutes: moving items over the belt (server) %s; bob at the far end sees %d moving items at x %s and %d on the ground' % (
        counts, len(far_items), xs[:40], len(ground)))
    # 9.9: the server log lines written while this scenario ran: the rest of the log it started with, and the whole log
    # of the server started by the restart (server.py writes a new log file for it)
    session = common.read_json(common.SESSION)
    logs = [(log, first_line)] if log else []
    new_log = Path(session['log']) if session else None
    if new_log and new_log != log:
        logs.append((new_log, 0))
    bad, resets = [], []
    for path, start in logs:
        if path.exists():
            lines = path.read_text(encoding='utf-8', errors='replace').splitlines()[start:]
            for i, line in enumerate(lines):
                if not re.search(r'Exception|\bERROR\b|/ERROR\]', line):
                    continue
                # a client that quits for the restart closes its socket: the vanilla connection handler logs the reset
                reset = 'java.net.SocketException: Connection reset' in line or (
                    'Exception caught in connection' in line and i + 1 < len(lines) and 'SocketException: Connection reset' in lines[i + 1])
                (resets if reset else bad).append(line[:200])
    ctx.check('conveyor-cranes.mp-belt-log', bool(logs) and all(p.exists() for p, _ in logs) and not bad,
              'logs %s; %d bad lines: %s; connection resets listed apart: %s' % ([str(p) for p, _ in logs], len(bad), bad[:5], resets[:4]))
    ctx.rcon('kill @e[type=hbmsntm:moving_item]', 'kill @e[type=minecraft:item]')
    _lib.server_idle(ctx, a)  # the group's closing stop or the next scenario's restart may come next


def tool_click(ctx, who, pos, sneak, face='south'):
    """one right click with the settings tool from two blocks off the given face; returns the copy lines the player got
    from it, the screen open afterwards (closed again) and whether the click hit that block"""
    off = _lib.VEC[face]
    ctx.step('view', client=who, pos=[pos[0] + 0.5 + 2 * off[0], G, pos[2] + 0.5 + 2 * off[2]], look_at=[pos[0] + 0.5, pos[1] + 0.5, pos[2] + 0.5],
             fly=False, hide_gui=False)
    if sneak:
        ctx.step('key', client=who, key='key.keyboard.left.shift', action='press', after=3)
    started = int(time.time() * 1000)
    hit = ctx.step('use', client=who, target=dict(pos=list(pos), face=face), any_hit=True, after=6).get('hit') or {}
    on_target = hit.get('type') == 'BLOCK' and [int(v) for v in hit.get('pos', [])] == list(pos)
    if sneak:
        ctx.step('key', client=who, key='key.keyboard.left.shift', action='release', after=3)
    lines = [m.get('text', '') for m in ctx.step('chat', client=who, count=20, since_ms=started).get('messages', [])]
    screen = ctx.step('hud', client=who, frames=2).get('screen')
    if screen:
        ctx.step('close', client=who)
    return [l for l in lines if T['copied'] in l], screen, on_target


def settings_tool_modes(ctx, b, router, ex):
    """D5 retest: the settings tool acts before the block in every game mode; copying needs no build permission, pasting does"""
    targets = dict(survival=(X0 + 20, G, 6), creative=(X0 + 22, G, 6), adventure=(X0 + 24, G, 6))
    ex_target, chest = (X0 + 26, G, 6), (X0 + 28, G, 6)
    ctx.rcon(*['setblock %d %d %d hbmsntm:crane_router' % t for t in targets.values()])
    ctx.rcon('data merge block %d %d %d {modes:[I;3,3,3,3,3,3]}' % targets['adventure'],
             'setblock %d %d %d hbmsntm:crane_extractor[input=north,output=south]' % ex_target,
             'item replace block %d %d %d container.0 with minecraft:gold_ingot' % ex_target,
             'setblock %d %d %d minecraft:chest' % chest,
             'item replace entity %s weapon.mainhand with hbmsntm:settings_tool' % b,
             # a sorter copy pastes its modes only together with filter items (TileEntityCraneRouter.java:177: listSize > 0)
             'item replace block %d %d %d container.1 with minecraft:iron_ingot' % router)
    src_modes = server_value(ctx, router, 'modes')
    once = {}
    for mode in ('survival', 'creative'):
        ctx.rcon('gamemode %s %s' % (mode, b))
        copied, screen_copy, hit_copy = tool_click(ctx, b, router, True, face='east')
        _, screen_paste, hit_paste = tool_click(ctx, b, targets[mode], False)
        pasted = server_value(ctx, targets[mode], 'modes')
        filt = server_value(ctx, targets[mode], 'Items[{Slot:1b}].id')
        # each pasted filter slot steps its matcher mode once (TileEntityCraneRouter.java:183-185): a fresh sorter reads "exact"
        # after one paste and "wildcard" after two
        slot_mode = server_value(ctx, targets[mode], 'pattern0.mode1')
        once[mode] = dict(copy_lines=len(copied), screen_copy=screen_copy, screen_paste=screen_paste, hits=hit_copy and hit_paste,
                          pasted=strip_pos(dict(v=pasted))['v'] == strip_pos(dict(v=src_modes))['v'] and 'minecraft:iron_ingot' in filt,
                          slot_mode=strip_pos(dict(v=slot_mode))['v'].strip())
    ctx.check('conveyor-cranes.mp-settings-once', all(v['copy_lines'] == 1 and not v['screen_copy'] and not v['screen_paste'] and v['pasted'] and v['hits']
                                                      and v['slot_mode'] == '"exact"' for v in once.values()),
              'per game mode %s (slot_mode: the pasted slot\'s matcher mode, "exact" after one paste); source modes %s' % (once, src_modes[-40:]))
    ctx.rcon('gamemode adventure %s' % b)
    # a fresh tool, so the data read after the adventure copy comes from that copy
    ctx.rcon('item replace entity %s weapon.mainhand with hbmsntm:settings_tool' % b)
    adv = {}
    copied, screen, hit = tool_click(ctx, b, router, True, face='east')
    held = ctx.rcon('data get entity %s SelectedItem.components' % b)
    adv['copy_sorter'] = dict(lines=len(copied), screen=screen, data='modes' in (held[0] if held else ''), hit=hit)
    before = server_value(ctx, targets['adventure'], 'modes')
    _, screen, hit = tool_click(ctx, b, targets['adventure'], False)
    adv['paste_sorter'] = dict(unchanged=server_value(ctx, targets['adventure'], 'modes') == before, screen=screen, hit=hit)
    source_filter = server_value(ctx, ex, 'Items[{Slot:0b}].id')
    copied, screen, hit = tool_click(ctx, b, ex, True)
    # the refused paste only means something when the copied filter differs from the target's gold ingot
    adv['copy_extractor'] = dict(lines=len(copied), screen=screen, source_filter=strip_pos(dict(v=source_filter))['v'].strip(), hit=hit)
    before = server_value(ctx, ex_target, 'Items[{Slot:0b}].id')
    _, screen, hit = tool_click(ctx, b, ex_target, False)
    adv['paste_extractor'] = dict(unchanged=server_value(ctx, ex_target, 'Items[{Slot:0b}].id') == before, screen=screen, hit=hit)
    _, screen, hit = tool_click(ctx, b, chest, False)
    adv['chest'] = dict(screen=screen, hit=hit)
    ctx.rcon('gamemode creative %s' % b)
    # every click must have hit its block: a missed paste would also leave the settings unchanged and no screen open
    ok = (all(v['hit'] for v in adv.values()) and adv['copy_sorter']['lines'] == 1 and not adv['copy_sorter']['screen'] and adv['copy_sorter']['data']
          and adv['paste_sorter']['unchanged'] and not adv['paste_sorter']['screen']
          and adv['copy_extractor']['lines'] == 1 and not adv['copy_extractor']['screen']
          and adv['copy_extractor']['source_filter'].startswith('"') and 'gold_ingot' not in adv['copy_extractor']['source_filter']
          and adv['paste_extractor']['unchanged'] and not adv['paste_extractor']['screen'] and bool(adv['chest']['screen']))
    ctx.check('conveyor-cranes.mp-settings-adventure', ok, 'bob in adventure mode: %s' % adv)



def duct_ctrl(ctx, a, b):
    """two runs of six universal fluid ducts along x and a single water duct apart from them; alice copies the water duct with
    the settings tool and pastes on the first duct of each run, with Ctrl held on the first run only; the server and bob's
    client copy are read per duct"""
    x0 = X0 + 40
    src = (x0 + 9, G, 10)
    ctx.rcon('fill %d %d 10 %d %d 10 hbmsntm:fluid_duct_neo' % (x0, G, x0 + 5, G), 'fill %d %d 14 %d %d 14 hbmsntm:fluid_duct_neo' % (x0, G, x0 + 5, G),
             'setblock %d %d %d hbmsntm:fluid_duct_neo' % src, 'data merge block %d %d %d {Type:1}' % src,
             'item replace entity %s weapon.mainhand with hbmsntm:settings_tool' % a,
             'tp %s %d %d 17' % (b, x0 + 3, G))
    ctx.step('wait', client=a, ticks=10)
    before = [server_value(ctx, (x0 + i, G, 10), '') for i in range(6)]
    # the duct is a thin pipe: the crosshair on its centre, then a plain click on whatever it holds
    # aimed 0.35 higher: view aims from the standing eye, and sneaking lowers the eye by that much before the click
    ctx.step('view', client=a, pos=[src[0] + 0.5, G, src[2] + 2.5], look_at=[src[0] + 0.5, G + 0.85, src[2] + 0.5], fly=False, hide_gui=False)
    ctx.step('key', client=a, key='key.keyboard.left.shift', action='press', after=3)
    started = int(time.time() * 1000)
    hits = [ctx.step('use', client=a, after=6).get('hit')]
    ctx.step('key', client=a, key='key.keyboard.left.shift', action='release', after=3)
    copied = [m.get('text', '') for m in ctx.step('chat', client=a, count=20, since_ms=started).get('messages', []) if T['copied'] in m.get('text', '')]
    for z, ctrl in ((10, True), (14, False)):
        ctx.step('view', client=a, pos=[x0 + 0.5, G, z + 2.5], look_at=[x0 + 0.5, G + 0.5, z + 0.5], fly=False, hide_gui=False)
        if ctrl:
            ctx.step('key', client=a, key='key.keyboard.left.control', action='press', after=4)
        hits.append(ctx.step('use', client=a, after=6).get('hit'))
        if ctrl:
            ctx.step('key', client=a, key='key.keyboard.left.control', action='release', after=3)
    ctx.rcon('item replace entity %s weapon.mainhand with minecraft:air' % a)
    aside(ctx, a)
    ctx.step('view', client=b, pos=[x0 + 2.5, G + 2, 17.5], look_at=[x0 + 2.5, G, 12], fly=True, hide_gui=False)
    ctx.step('wait', client=b, ticks=10)

    def typ(text):
        m = re.search(r'Type:\s*(-?\d+)', text or '')
        return int(m.group(1)) if m else None
    server = {z: [typ(server_value(ctx, (x0 + i, G, z), '')) for i in range(6)] for z in (10, 14)}
    seen = {z: [typ(blk.get('nbt')) for blk in sorted(ctx.step('dump', client=b, **{'from': [x0, G, z], 'to': [x0 + 5, G, z]})['blocks'],
                                                      key=lambda v: v['pos'][0])] for z in (10, 14)}
    new = typ(server_value(ctx, src, ''))
    ok = (len(copied) == 1 and new == 1 and all(v == new for v in server[10]) and seen[10] == server[10]
          and server[14][0] == new and all(v != new for v in server[14][1:]) and seen[14] == server[14])
    ctx.check('conveyor-cranes.mp-duct-ctrl', ok, 'copy message %s; source Type %s; Type per duct, Ctrl run: server %s, bob %s (before %s); '
              'plain run: server %s, bob %s; clicks hit (copy, Ctrl paste, plain paste) %s' % (
                  copied, new, server[10], seen[10], [typ(v) for v in before], server[14], seen[14], hits))
    ctx.rcon('fill %d %d 10 %d %d 14 minecraft:air' % (x0, G, x0 + 9, G))
