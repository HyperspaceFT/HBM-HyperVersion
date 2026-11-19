"""Dedicated server, stability matrix, situation "stop the server and start it again": the six networks of
power-transmission/mp_stability_unload.py (its rigs and readings, built here at another origin) read before the stop and after the
start.

At the stop both scenes are loaded (A stands in the radiation chunk T, about seven chunks from the rigs; B over the middle of the long
line). The stop turns saving on (MinecraftServer.stopServer :606-612), removes every chunk ticket but the UNKNOWN and POST_TELEPORT
ones (DistanceManager.removeTicketsOnClosing :320-331), times those out (its ServerChunkCache.tick passes tickChunks false, so
purgeStaleTickets runs, :315-319) and loops until no ticket is left (stopServer :614-623, ChunkMap.hasWork :481-489): every chunk
unloads, and each one still unsaved is saved as it unloads (ChunkMap.scheduleUnload :532-556, ChunkMap.save :769-771), the rest at
:625. Both restarts stop the server first, with the players still in the world, and read the region file while no server runs
(stop_read_start); then the clients quit, the server starts again, the world is frozen over RCON as soon as it answers and the
clients join again (a frozen world does not survive a restart), so nothing the players load on joining ticks before the readings.
Readings, the comparison of static readings and the resume window are those of the unload file.

The known asymmetry is read on the long line: after the restart no network node exists until its block entity ticks once (the
original makes nodes only in updateEntity: TileEntityCableBaseNT.java:16-30, TileEntityPipeBaseNT.java:40-53; NEO
CableBaseBlockEntity.java:25-42, PipeBaseBlockEntity.java:40-60), while a chunk unload keeps them (TileEntityCableBaseNT.java:36-45;
UniNodespace.java:58). So with only the line's end chunks force-loaded and its middle never ticked since the start, the far end
receives nothing; after B has flown along the line once (every chunk ticking for a moment) and left again, it does.

Expected (original 1.7.10 / NEO): as in the unload file for the saved data. Chunk radiation: the stop saves every chunk with its map
value (the original's save :160-171; NEO :160-177), and the start reads it back (original :148-158; NEO :145-158). In NEO the stop
posts ChunkEvent.Unload before that save (ChunkMap.scheduleUnload :541-544); the unload handler keeps the map entry and marks the
chunk unsaved when its value differs from the one it last loaded or saved (:179-201), so the stop writes the value; the original's
unload removes nothing (:172-183). Both stops come right after a `forceload query` (recorded).
A saved value is judged as the unload file's polonium row judges its own ("Polonium block" there): the region save time not before
a Geiger reading taken just before the stop, the value at least the no-emission floor from that reading over the map updates the
save time allows and at most a cap. Such a row passes only when that floor is above 0 and is not-run when it is 0. T holds no
emitter, and its cap is the set value (x 1.001 for float rounding): after an update every value is at most the weighted sum of its
3 x 3 before it, the weights adding up to 1 (an add step (S + share) x 0.99 - 0.05 <= S + share, an overwrite takes one share;
original ChunkRadiationHandlerSimple.java:71-122, NEO :72-118), so no update raises the largest value near T, and nothing near T
holds more than the set value (the rigs are about seven chunks away). T's own reading is no cap: the rule bounds a chunk's next
value by the largest value of its 3 x 3, which it does not keep at T.

A real source (row mp-restart-radiation-source), after the other rows, with a second restart: the polonium block of the unload
file's docstring ("Polonium block": the rate, the update rule, the floor x_E, the no-emission floor, the cap and the Geiger's one
decimal) is set in chunk P with B in it (A parked), the world runs PO_EMIT ticks and then server_idle's 200 ticks with B still in
P, `forceload query` and P's status are recorded, B reads the Geiger counter, the world is frozen and the server is stopped at once
with B still in P: P unloads and saves at the stop. The original's block takes `rad` only in onBlockAdded (BlockHazard.java:138-146), a field of the block
object that a new server process starts at 0, and updateTick neither adds nor schedules again while `rad` is not above 0
(:120-127); NEO HazardBlock.java:24,37-51 the same. So after the restart the saved value is read back but the block no longer
emits. Expected: the reading before the stop within [x_E - 0.1, cap]; the value saved at the stop, read before the restart, above 0,
saved at or after that reading, at least the no-emission floor from the reading over the updates the save time allows, at most
the cap; after the restart B (rejoining last, so P loads just before the reading) reads above 0 in the frozen world; then the world
runs PO_AFTER ticks with B in P and the reading stays under x_E - 0.1 for the emissions an emitting block would have made in that
time (about 90): a block that kept emitting after a restart reads at least that, a stop that writes 0 reads 0 after the restart.
"""
import importlib.util
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _lib  # noqa: E402

_spec = importlib.util.spec_from_file_location('stability_unload_rigs', Path(__file__).with_name('mp_stability_unload.py'))
U = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(U)
Z = U.Z

SCENARIO = dict(
    id='power-transmission.mp_stability_restart',
    feature='power-transmission',
    features=['power-transmission', 'fluid-pipelines', 'conveyors', 'conveyor-cranes', 'rbmk-reactor', 'rbmk-console', 'hazard-system',
              'network-architecture', 'battery-storage', 'rtg-power'],
    title='Dedicated server: stability matrix, stop and restart the server (six networks)',
    group='mp',
    capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70),
)

ORIGIN = (6000, 6000)
PO_AFTER = 400            # client ticks the world runs after the second restart with B in chunk P
WALK_STEP = 32            # B flies along the long line in steps of this many blocks
WALK_TICKS = 40           # and stays this many client ticks at each step
PT, FP, CV, RX, HZ, NA = U.PT, U.FP, U.CV, U.RX, U.HZ, U.NA
NODES = ('TileEntityCableBaseNT.java:16-45, TileEntityPipeBaseNT.java:40-53,86-95; CableBaseBlockEntity.java:25-57, '
         'PipeBaseBlockEntity.java:40-60,94-102, UniNodespace.java:58')
EXPECT = [
    (PT, 'mp-restart-power', '停服重启（停服时两处场景都已加载，重启后先冻结再让客户端重进，静置 80 刻后读）：RTG 与电池座（电池组电量）的服务端数据与停服前逐项相同',
     'TileEntityMachineRTG.java:44-55, TileEntityBatterySocket.java:200-215; MachineRTGBlockEntity.java:138-149, BatteryBaseBlockEntity.java:143-160'),
    (FP, 'mp-restart-fluid', '停服重启：电动泵、管道与钢桶的服务端数据与停服前逐项相同',
     'TileEntityBarrel.java:208-221, TileEntityPipeBaseNT.java:110-119; BarrelBlockEntity.java:324-335, PipeBaseBlockEntity.java:123-131'),
    (CV, 'mp-restart-belts', '停服重启：环形皮带上运动物品的个数与服务端位置、箱子与抽取器的数据与停服前相同', 'EntityMovingItem.java:90-106; MovingItem.java:124-137'),
    (RX, 'mp-restart-rbmk', '停服重启：运行中的 3×3 小堆九根柱与控制台的服务端数据与停服前逐项相同',
     'TileEntityRBMKBase.java:268-289, TileEntityRBMKConsole.java:358-385; RBMKBaseBlockEntity.java:226-237, RBMKConsoleBlockEntity.java:415-444'),
    (PT, 'mp-restart-line', '停服重启：跨 12 个区块的长线（导线与管线记录、管锚类型、抽样管道、两端）与停服前逐项相同',
     'TileEntityPylonBase.java:144-167, TileEntityPipelineBase.java:169-190; PylonBaseBlockEntity.java:142-160, PipeAnchorBlockEntity.java:139-155'),
    (HZ, 'mp-restart-radiation-saved', '停服时 A 站在设成 20,000 的辐射区块 T 里（周期存盘写下之后执行 save-off 并放一块玻璃，区块带着未存的改动停服）：'
     'A 读盖革后随即先停服务端（玩家仍在世界里），停服后、重启前读区域文件的 hfr_simple_radiation：写入时间不早于这次读数，'
     '值不低于读数按“不放辐射”下限 max(0, 0.548v − 0.433) 走过写入时间允许的更新次数后的值、不高于设定值 20,000×1.001'
     '（这一下限为 0 时记未执行）',
     'ChunkRadiationHandlerSimple.java:71-122,160-171; ChunkRadiationHandlerSimple.java:72-118,160-201, MinecraftServer.java:606-625, '
     'DistanceManager.java:320-331'),
    (HZ, 'mp-restart-radiation', '重启后 A 在该区块用盖革计数器读到的区块辐射大于 0（区块辐射冻结时也每 20 刻衰减，没有静止读数，只比在不在）',
     'ChunkRadiationHandlerSimple.java:148-158; ChunkRadiationHandlerSimple.java:145-158'),
    (HZ, 'mp-restart-radiation-source', '真的辐射源（其余各行之后、第二次重启）：离 T 与装置约 30 个区块的区块 P（盖革先读 0）里用 RCON setblock 放一块钋块，'
     'B 留在 P、A 停到远处，世界走 300 刻再走 server_idle 的 200 刻，B 读盖革：读数在 [x_E − 0.1, 75×(可能的放辐射次数)×1.001] 内'
     '（x_0 = 0，x_(k+1) = max(0, 0.548×(x_k+75) − 0.433)）；读数前强制加载的区块数为 0；随即冻结并先停服务端（B 仍在 P），'
     '停服后、重启前读区域文件：P 存下的值大于 0、写入时间不早于这次读数、'
     '不低于读数按“不放辐射”下限 max(0, 0.548v − 0.433) 走过存盘时间允许的更新次数后的值、不高于上限（这一下限为 0 时记未执行）；'
     '重启后 B（最后进服，P 在读数前才载入）在冻结的世界里读到大于 0；再让世界走 400 刻，读数低于一块仍在放辐射的方块必然达到的 x_E − 0.1（约 90）。'
     '原版：rad 只在 onBlockAdded 里赋值，是方块对象的字段，新进程里为 0，updateTick 在 rad 不大于 0 时既不加也不再排，所以重启后这块方块不再放辐射',
     'BlockHazard.java:120-127,138-146, ModBlocks.java:1349, HazardRegistry.java:83,142, ChunkRadiationHandlerSimple.java:71-122,148-171; '
     'HazardBlock.java:24,37-51, NtmBlocks.java:193, ChunkRadiationHandlerSimple.java:72-118,145-201, DistanceManager.java:320-331'),
    (NA, 'mp-restart-resume', '重启后让世界走 200 刻：电池组电量上升、清空的钢桶重新有水、皮带上的物品在动且总数不变、源棒的物品数据在变', NODES),
    (NA, 'mp-restart-line-before-load', '重启后长线中段的方块实体一次也没走过刻（世界冻结中为读数加载过，B 在原地重进、不再传送）：两人都在远处、只强制加载两端区块，'
     '清空末端电炉与钢桶后走 200 刻，两者都没收到（中段的节点要等方块实体走一刻才建，原版同样）', NODES),
    (NA, 'mp-restart-line-after-load', '然后 B 沿长线飞一遍（每个区块都走过刻）再离开，同样只强制加载两端：末端电炉与钢桶都收到了电与水（卸载保留节点）', NODES),
    (PT, 'mp-restart-log', '这个场景期间（含重启）服务端日志里没有 Exception 或 ERROR 行（客户端为重连断开的连接重置除外）', 'server log'),
]


def expectations():
    return [dict(id=f + k, text=t, source=s) for f, k, t, s in EXPECT]


def walk_line(ctx, b, s):
    """The world runs while B flies along the long line from end to end, stopping WALK_TICKS client ticks every WALK_STEP blocks, so
    every chunk of the line is loaded and ticks for a moment."""
    L = s['line']
    ctx.server('tick unfreeze')
    stops = []
    for x in range(L['lx'], L['lx'] + 193, WALK_STEP):
        ctx.step('view', client=b, pos=[x + 0.5, U.Y + 8, L['zl'] + 4.5], yaw=0.0, pitch=60.0, fly=True, hide_gui=False)
        ctx.step('wait', client=b, ticks=WALK_TICKS)
        stops.append(x)
    return stops


# server.py restart's second half (cmd_restart after the stop), run as its own process like drive.tool runs server.py: the
# Gradle process it starts must not become a child of the driver
START = """
import sys
sys.path.insert(0, sys.argv[1])
import common
import server
session = common.read_json(common.SESSION)
for port in (session['port'], session['rcon_port']):
    if not server.wait_for(lambda: common.port_free(port), 30):
        sys.exit('Port %d is still in use; session kept, run `server.py restore`.' % port)
server.launch(session, common.now_tag())
print('restarted: tag=%s pid=%d' % (session['tag'], session['pid']))
sys.exit(server.wait_ready(session, 600))
"""


def stop_read_start(ctx, read):
    """A server restart in the same session as server.py restart (run/ is not restored in between), split so that `read()` runs
    while no server runs: the server is stopped first (RCON `stop`, server.stop_server), with the players still in the world, which
    the stop disconnects; then `read()`, then both clients quit (drive.stop_client), the server starts again, the world is frozen
    over RCON as soon as it answers and the clients join again (drive.join), as _lib.restart_frozen does. Returns (wall seconds
    of the restart, read's result, dict(stopped_s: wall seconds from the call to the server's exit, stopped_at, stopped_by))."""
    import common
    import server as srv
    drv = sys.modules.get('__main__')
    if not hasattr(drv, 'restart_mp'):
        import drive as drv  # longrun.py runs drive as a module
    started = time.time()
    session = common.read_json(common.SESSION)
    if not session or session.get('status') != 'running':
        raise drv.ClientGone('no running server session to restart')
    try:
        how, code, _ = srv.stop_server(session, False, 600)
    except SystemExit as error:
        raise drv.ClientGone('server stop failed: %s' % error)
    stopped = time.time()
    session.setdefault('restarts', []).append(dict(at=common.now_tag(), stopped_by=how, gradle_exit=code))
    common.write_json(common.SESSION, session)
    result = read()
    for name, channel in list(ctx.channels.items()):
        drv.stop_client(name, channel)
    here = str(Path(__file__).resolve().parents[2])
    if subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', START, here], cwd=common.REPO).returncode != 0:
        raise drv.ClientGone('server start after the stop failed')
    ctx.rcon('tick freeze')
    for name, channel in list(ctx.channels.items()):
        drv.join(ctx.run, name, ctx.channels, old=channel)
    took = round(time.time() - started, 2)
    ctx.run.restarts.append(took)
    return took, result, dict(stopped_s=round(stopped - started, 2), stopped_at=round(stopped, 2), stopped_by=how)


def t_saved(saved, stamp, reading, wall, cap):
    """T's value in the region file judged as U.po_saved judges P's: the save time not before `wall` (taken just before the
    reading), the value at least the no-emission floor from `reading` over the updates the save time allows and at most `cap`.
    decisive: that floor is above 0."""
    k = U.updates_within(stamp + 1 - wall) if stamp is not None else None
    lo = U.floor_decay(reading or 0.0, k) if k is not None else 0.0
    after = stamp is not None and stamp >= int(wall)
    ok = saved is not None and after and saved > 0 and saved >= lo - 1e-3 and saved <= cap
    return dict(saved=saved, stamp=stamp, gap_s=round(stamp + 1 - wall, 2) if stamp is not None else None, after_reading=after,
                updates_max=k, floor=round(lo, 3), cap=round(cap, 1), decisive=lo > 0, ok=ok,
                bounded=saved is not None and after and saved <= cap)


def po_restart(ctx, a, b, s, prefix):
    """The polonium block with a stop right after the reading (module docstring). The world runs until the reading, is frozen
    for the stop, runs PO_AFTER ticks after the restart and ends frozen, as the line delivery before it leaves it."""
    ctx.server('tick unfreeze')
    _lib.park(ctx, [a])
    p = U.po_place(ctx, b, s, prefix)
    ctx.step('wait', client=b, ticks=U.PO_EMIT)
    _lib.server_idle(ctx, b)                   # the stop needs an idle server; B stays in P, so the block keeps emitting
    loaded_at_stop = _lib.chunk_full(ctx, s['po_probe'])
    forced = _lib.forced_chunks(ctx)
    r0 = U.po_reading(ctx, b, prefix, p)
    # frozen and stopped at once with B in P: P stays loaded up to the stop, unloads in it and saves (module docstring); the
    # block stops with the world, the map updates go on until the stop and are counted by the save time
    frozen_at = ctx.server('tick freeze')['game_time']
    took, sv, stop = stop_read_start(ctx, lambda: U.po_saved(s, r0, r0['wall'], p, frozen_at))
    sv.update(gap_s=round(sv['stamp'] + 1 - r0['wall'], 2) if sv['stamp'] is not None else None, stopped_after_reading_s=round(stop['stopped_at'] - r0['wall'], 2))
    # B is in the world (status in_world) while its client may still show the level-loading screen, which refuses a use
    ctx.step('screen', client=b, expect='none', timeout_ticks=600)
    full = _lib.chunk_full(ctx, s['po_probe'])
    r1, r1_line = U.geiger(ctx, b, prefix)
    ctx.server('tick unfreeze')
    g0 = ctx.server()['game_time']
    ctx.step('wait', client=b, ticks=PO_AFTER)
    g1 = ctx.server()['game_time']
    r2, r2_line = U.geiger(ctx, b, prefix)
    _lib.still(ctx)
    # what a block still emitting would have reached: block ticks the game time guarantees, one off for the tick in progress
    e_would = (g1 - g0) // U.PO_TICK - 1
    floor_would = U.floor_emitting(e_would)
    after = dict(first=r1, first_line=str(r1_line)[:120], after=r2, after_line=str(r2_line)[:120], game=(g0, g1), e_would=e_would,
                 floor_would=round(floor_would, 3), first_up=r1 is not None and r1 > 0,
                 not_rising=r2 is not None and r2 < floor_would - U.GEIGER_STEP)
    return dict(place=p, before_stop=r0, loaded_at_stop=loaded_at_stop, forced=forced[0], forced_reply=forced[1][:120], restart_s=took,
                saved=sv, p_loaded_after=full, after=after)


def po_check(ctx, rec):
    p, r0, sv, after = rec['place'], rec['before_stop'], rec['saved'], rec['after']
    pre = p['full'] and p['placed'] and p['base'] == 0.0
    rest = pre and r0['ok'] and rec['loaded_at_stop'] and rec['forced'] == 0 and rec['p_loaded_after'] and after['not_rising']
    if not sv['decisive']:
        # the save came so late after the reading that the floor is 0: no saved value then separates a wrong save from decay
        bounded = sv['saved'] is not None and sv['after_leaving'] and sv['saved'] <= sv['cap']
        if rest and bounded and (after['first_up'] or sv['saved'] == 0):
            ctx.not_run(HZ + 'mp-restart-radiation-source', 'the save was not decisive (floor 0 over %s updates): %s' % (sv['updates_max'], rec))
            return
    ctx.check(HZ + 'mp-restart-radiation-source', sv['decisive'] and rest and sv['ok'] and after['first_up'], str(rec))


def run(ctx):
    a, b = list(ctx.channels)
    log0 = _lib.log_counts()
    Z.setup_world(ctx, a, b)
    s = U.layout(*ORIGIN)
    rec = U.build_all(ctx, a, s)
    U.pre_run(ctx, a, b, s)
    before = U.read_all(ctx, s)

    # radiation: the periodic save writes the set value at once; then `save-off` (ServerLevel.noSave: no periodic save and no unload,
    # ChunkMap.tick :474) and a glass block placed in T mark T unsaved until the stop, which turns saving on again, unloads every chunk
    # (MinecraftServer.stopServer :614-623: removeTicketsOnClosing, then the chunk unloads of ChunkMap.scheduleUnload) and saves
    # (:625); so the stop is what writes T. A reads the Geiger counter in T and the server is stopped at once, A still in T.
    prefix = U.geiger_prefix(ctx, a)
    loaded_at_stop = {str(p): _lib.chunk_full(ctx, p) for p in U.cluster_probes(s) + U.line_probes(s)}
    _lib.server_idle(ctx, a)
    t_set = time.time()
    rad_set = U.set_radiation(ctx, a, s)
    ctx.step('wait', client=a, ticks=20)
    saved0, stamp0 = U.saved_radiation(s)
    save_off = Z.rcon1(ctx, 'save-off')
    tx, tz = s['rad_chunk']
    glass = Z.rcon1(ctx, 'setblock %d %d %d minecraft:glass' % (tx * 16 + 3, U.Y + 2, tz * 16 + 3))
    forced = _lib.forced_chunks(ctx)
    wall0 = time.time()
    g0 = U.geiger(ctx, a, prefix)
    took, (saved, stamp), stop = stop_read_start(ctx, lambda: U.saved_radiation(s))
    tv = t_saved(saved, stamp, g0[0], wall0, U.RAD * 1.001)
    decisive = stamp0 is not None and stamp0 >= int(t_set) and 'disabled' in save_off and 'Changed' in glass
    U.to_rad_spot(ctx, a, s)
    g1 = U.geiger(ctx, a, prefix)
    # B rejoined where it stood at the stop, over the middle of the line; it is not teleported there again: a /tp (the executor's
    # view step) adds a POST_TELEPORT region ticket at the destination (ServerPlayer.teleportTo :1539, TicketType.POST_TELEPORT 5 ticks)
    # that is block ticking and only a running world purges, so the middle would tick a few ticks when the world runs again
    U.view(ctx, a, s['spot_a'])
    back = _lib.wait_full(ctx, a, U.cluster_probes(s) + U.line_probes(s))
    back['moving'] = U.wait_moving(ctx, a, s, before['belts']['moving.count'])
    _lib.still(ctx)
    after = U.read_all(ctx, s)
    cmp = U.compare_cells(before, after)
    U.check_cells(ctx, 'mp-restart', cmp, before, after,
                  extra='build %s; full status at the stop %s; restart %s s; back at full status %s; ' % (rec, loaded_at_stop, took, back))
    detail = ('set %s (%s); periodic save before save-off %s at %s; %s; glass %s; Geiger before the stop %s at %.2f; server stopped %s s '
              'later (%s, at %s); value in the region file between the stop and the start %s; T unsaved at the stop %s; '
              'force-loaded chunks right before the reading %s (%s)'
              % (U.RAD, rad_set, saved0, stamp0, save_off[:60], glass[:60], g0[0], wall0, round(stop['stopped_at'] - wall0, 2),
                 stop['stopped_by'], stop['stopped_at'], tv, decisive, forced[0], forced[1][:120]))
    if not decisive:
        # no periodic save after the set, save-off refused, or the glass not placed: the stop did not have to write T
        ctx.not_run(HZ + 'mp-restart-radiation-saved', 'the sequence was not decisive: ' + detail)
    elif not tv['decisive'] and tv['bounded']:
        # the save came so late after the reading that the floor is 0: no saved value then separates a wrong save from decay
        ctx.not_run(HZ + 'mp-restart-radiation-saved', 'the save was not decisive (floor 0 over %s updates): %s' % (tv['updates_max'], detail))
    else:
        ctx.check(HZ + 'mp-restart-radiation-saved', tv['ok'] and tv['decisive'], detail)
    ctx.check(HZ + 'mp-restart-radiation', g1[0] is not None and g1[0] > 0,
              'Geiger before the stop %s, first reading after the restart %s (%r)' % (g0[0], g1[0], g1[1]))

    # B leaves the line before anything runs: since the restart no block entity of the line has ticked, so it has no node
    gone = U.leave(ctx, a, [b], U.line_probes(s))
    ok, parts, detail = U.resume(ctx, a, s)
    ctx.check(NA + 'mp-restart-resume', ok, '%s; %s' % (parts, detail))

    U.leave(ctx, a, [a, b], U.cluster_probes(s) + U.line_probes(s))
    d2 = U.line_delivery(ctx, a, b, s, 'after the restart, middle never ticked')
    ctx.check(NA + 'mp-restart-line-before-load', rec['line']['ok'] and gone['ok'] and d2['middle_unloaded'] and d2['ends_loaded'] and not d2['power'] and not d2['water'],
              'line left before the world ran: %s; %s' % (gone, d2['detail']))

    stops = walk_line(ctx, b, s)
    _lib.park(ctx, [b])
    left = _lib.wait_unloaded(ctx, a, U.line_probes(s))
    d3 = U.line_delivery(ctx, a, b, s, 'after B flew along the line')
    ctx.check(NA + 'mp-restart-line-after-load', rec['line']['ok'] and left['ok'] and d3['middle_unloaded'] and d3['ends_loaded'] and bool(d3['power']) and bool(d3['water']),
              'B stopped at x %s; line unloaded again %s; %s' % (stops, left, d3['detail']))

    # a real source in chunk P, stopped and started again
    po_check(ctx, po_restart(ctx, a, b, s, prefix))

    errs = _lib.server_log_errors(since=log0)
    ctx.check(PT + 'mp-restart-log', errs['errors'] == 0, str(errs))
    U.view(ctx, a, s['spot_a'])
    U.view(ctx, b, s['spot_a'])
    _lib.server_idle(ctx, a)
