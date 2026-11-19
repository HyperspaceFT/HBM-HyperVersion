#!/usr/bin/env python3
"""Goal 32 two-person world for the dedicated-server rows a person has to hear or type (not a scenario: drive.py skips names starting
with "_", and stations.py builds single-player worlds only). One executor client builds four arrangements in a loopback
dedicated-server world; the world is zipped for a later session in which the user's own client and the executor client play the
rows together (the checklist with the user's part is kept with the migration records, not here).

Arrangements (flat world, feet at y = G = -60; the spawn is set to (0, G, -10), a sign with the arrangement's number at each):
1. RBMK console: a manual control rod, a blank column and a second control rod west to east at z = 0 (x = -4 .. -2), a console 6
   blocks south of the blank column, linked to it with the console linking device; the rig of rbmk-console/stations_g32.py and
   rbmk-console/mp_console.py. Rows: a depth typed into the console screen's text field and saved for the selected rods
   (original GUIRBMKConsole.java:152-162 select all control rods, :243-262 save; NEO RBMKConsoleScreen.java:225-235,293-317),
   watched by the other player's console grid; and AZ-5, whose shutdown sound plays on the clicking client only (original
   GUIRBMKConsole.java:219-239; NEO RBMKConsoleScreen.java:275-291,376).
2. a power switch at (6, G, 2) (power-control/stations_g32.py): the reactor-start sound at pitch 1.0 on and 0.85 off, sent by the
   server to the players near it (original CableSwitch.java:52,55; NEO CableSwitchBlock.java:55-64).
3. the cram ring of conveyors/stations_g31.py at x = 12 .. 14 (conveyors/cram.py's ring): two extractors with the Mk.III ejector
   held by a lever; flipped, the ring crams and pops with the tiny explosion's sound (original ServerConfig.java:29-30,
   EntityMovingConveyorObject.java:88-97; NEO MovingConveyorObject.java:173-187).

Run from the NEO root, against a server session started for it (both names opped):
  python3 -B -X utf8 tools/migration/acceptance/server.py start --tag g32u2p --op acc_a
  python3 -B -X utf8 tools/migration/acceptance/scenarios/_two_person_g32.py build --run g32u-two-person
  python3 -B -X utf8 tools/migration/acceptance/server.py stop
  python3 -B -X utf8 tools/migration/acceptance/scenarios/_two_person_g32.py pack --run g32u-two-person --tag g32u2p
  python3 -B -X utf8 tools/migration/acceptance/server.py delete-world --tag g32u2p
build    joins the executor client, builds the arrangements, reads them back, writes arrangements.json and quits the client.
pack     zips run/accept-<tag> (after server.py stop) into <run>/accept-<tag>.zip; the server world itself is deleted afterwards.
During the two-person session (server.py start --from-world <unzipped world> --op acc_a --op <user>):
join     starts the executor client against the running server and leaves it running.
act      the executor's part of a row, printed as JSON: depth-watch (opens the console, waits until a depth is saved for the rods,
         reads the server, its own client copy and grid, takes a screenshot), switch (flips the switch on and off), az5 (opens the
         console, lid and AZ-5, records its own sounds), sounds N [--near console|switch|ring] (records its sounds for N client
         ticks while the user acts),
         cram-reset (rebuilds the ring and its feed).
leave    quits the executor client.
Nothing here starts a server or the user's client; standard library only.
"""
import argparse
import importlib.util
import json
import re
import sys
import time
import types
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import common  # noqa: E402
import drive  # noqa: E402
import _lib  # noqa: E402
import _stations_g32 as S  # noqa: E402


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, HERE / rel)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


G, H = S.G, S.H
SPAWN = (0, G, -10)
CONSOLE_ROW = (-4, 0)            # first column (x, z); the row runs east
SWITCH = (6, G, 2)
RING = (12, 0)                   # conveyors/stations_g31.py _cram(ctx, x, z)
SIGNS = [((-6, -3), 1, ['DEPTH + AZ-5', 'RBMK console', 'two players']), ((5, -3), 2, ['SWITCH SOUND', 'both hear', '']),
         ((11, -3), 3, ['CRAM BANG', 'flip lever', 'both hear'])]
SCENARIO = types.SimpleNamespace(SCENARIO=dict(id='rbmk-console.two-person-g32', feature='rbmk-console',
                                               capture=dict(drive.DEFAULT_CAPTURE)))
# console screen coordinates (original GUIRBMKConsole.mouseClicked; rbmk-console/mp_console.py): AZ-5 at (30, 138), 28 x 28
AZ5_AT = (44, 152)


def make_run(args):
    run = drive.Run(argparse.Namespace(out=args.out, run=args.run, argv=args.argv, option=[], timeout=args.timeout, scenario_lang=None,
                                       tag=getattr(args, 'tag', None)))
    run.capture = dict(drive.DEFAULT_CAPTURE)
    run.current_lang = run.capture['lang']
    return run


def context(run, channels):
    import rcon as rcon_tool
    return drive.Context(run, SCENARIO, channels, rcon=lambda: rcon_tool.connect())


def channel_of(run, name):
    exit_file = common.CLIENTS / name / 'exit-code.txt'
    return drive.Channel(name, run.dir / name, alive=lambda: not exit_file.exists())


def sign(ctx, x, z, number, short):
    lines = ['%d' % number] + list(short[:3])
    messages = ','.join("'%s'" % json.dumps(line[:15]) for line in lines + [''] * (4 - len(lines)))
    ctx.rcon('setblock %d %d %d minecraft:oak_sign[rotation=8]{front_text:{messages:[%s]}}' % (x, G, z, messages))


# ---------------------------------------------------------------- build

def cmd_build(args):
    run = make_run(args)
    channels = {}
    rec = dict(world=common.WORLD_PREFIX + (args.tag or ''), player=args.player)
    try:
        drive.join(run, args.player, channels)
        ctx = context(run, channels)
        ctx.rcon('gamemode creative %s' % args.player, 'defaultgamemode creative', 'time set 6000', 'weather clear',
                 'gamerule doDaylightCycle false', 'gamerule doWeatherCycle false', 'gamerule doMobSpawning false',
                 'setworldspawn %d %d %d' % SPAWN, 'clear %s' % args.player)
        for (x, z), number, short in SIGNS:
            sign(ctx, x, z, number, short)
        # 1. the console row (rbmk-console/stations_g32.py), placed and linked by hand
        cells, core, facing = S.build_rbmk_row(ctx, CONSOLE_ROW[0], CONSOLE_ROW[1], ['rbmk_control', 'rbmk_blank', 'rbmk_control'], 'rbmk_console')
        S.link_console(ctx, cells[1], core, facing)
        text = S.block_data_text(ctx, core)
        rec['console'] = dict(core=list(core), facing=facing, rods=[list(cells[0]), list(cells[2])], blank=list(cells[1]),
                              linked=(S.number_after(text, 'tX'), S.number_after(text, 'tZ')) == (cells[1][0], cells[1][2]))
        # 2. the switch
        S.cmd(ctx, 'setblock %d %d %d hbmsntm:cable_switch' % SWITCH)
        rec['switch'] = list(SWITCH)
        # 3. the cram ring, held by its lever
        build_ring(ctx)
        rec['ring'] = dict(origin=list(RING), lever=[RING[0] + 1, G, RING[1] + 1])
        d = ctx.step('dump', **{'from': [RING[0], G, RING[1]], 'to': [RING[0] + 2, G, RING[1] + 4]})
        rec['ring']['belts'] = len([b for b in d['blocks'] if b['block'] == H + 'conveyor'])
        ctx.step('view', pos=[SPAWN[0] + 0.5, G, SPAWN[2] + 0.5], yaw=0.0, pitch=0.0, fly=False, hide_gui=False)
        _lib.server_idle(ctx, args.player)
        rec['ok'] = rec['console']['linked'] and rec['ring']['belts'] == 8
    finally:
        drive.stop_client(args.player, channels.get(args.player))
    common.write_json(run.dir / 'arrangements.json', rec)
    print(json.dumps(rec, ensure_ascii=False))
    return 0 if rec.get('ok') else 1


def build_ring(ctx):
    g31 = _load('conveyors_stations_g31', 'conveyors/stations_g31.py')
    x, z = RING
    ctx.rcon('kill @e[type=%smoving_item,x=%d,y=%d,z=%d,dx=4,dy=2,dz=6]' % (H, x - 1, G - 1, z - 1))
    g31._cram(ctx, x, z)


# ---------------------------------------------------------------- pack

def cmd_pack(args):
    if common.read_json(common.SESSION):
        raise SystemExit('a server session is recorded: server.py stop first')
    world = common.REPO / 'run' / (common.WORLD_PREFIX + args.tag)
    if not (world / 'level.dat').is_file():
        raise SystemExit('no world at ' + common.rel(world))
    run = make_run(args)
    archive = run.dir / ('%s.zip' % world.name)
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for path in sorted(world.rglob('*')):
            if path.is_file() and path.name != 'session.lock':
                z.write(path, Path(world.name) / path.relative_to(world))
    print(json.dumps(dict(archive=common.rel(archive), files=len(zipfile.ZipFile(archive).namelist()))))
    return 0


# ---------------------------------------------------------------- the two-person session

def cmd_join(args):
    run = make_run(args)
    channels = {}
    # old=: the run directory keeps the build's hello.json and status.json (in_world true), which join must not take for this client
    took = drive.join(run, args.player, channels, old=channel_of(run, args.player))
    print(json.dumps(dict(joined=args.player, seconds=took)))
    return 0


def cmd_leave(args):
    run = make_run(args)
    drive.stop_client(args.player, channel_of(run, args.player))
    return 0


def open_console(ctx, rec):
    core, facing = tuple(rec['console']['core']), rec['console']['facing']
    v = S.facing_vec(facing)
    S.use_face(ctx, core, facing, [core[0] + 0.5 + v[0] * 2.5, G, core[2] + 0.5 + v[1] * 2.5], offset=[0.0, 0.5, 0.0], fly=True, after=8)
    ctx.step('screen', expect='RBMKConsoleScreen')
    return ctx.step('hud', frames=2)


def sound_names(result, *needles):
    return [dict(event=s.get('event'), pitch=round(s.get('pitch', 0), 2)) for s in result.get('sounds', [])
            if not needles or any(n in str(s.get('event')) for n in needles)]


def act_depth_watch(ctx, rec, args):
    rods = [tuple(p) for p in rec['console']['rods']]
    hud = open_console(ctx, rec)
    start = [_lib.block_data(ctx, p).get('targetLevel') for p in rods]
    t0, seen = time.time(), start
    while time.time() - t0 < args.timeout:
        seen = [_lib.block_data(ctx, p).get('targetLevel') for p in rods]
        if seen != start:
            break
        ctx.step('wait', ticks=20)
    ctx.step('wait', ticks=400)          # 0.00277 a tick: a full stroke in 361 ticks
    server = [(_lib.block_data(ctx, p).get('targetLevel'), _lib.block_data(ctx, p).get('level')) for p in rods]
    client = []
    for p in rods:
        d = ctx.step('dump', **{'from': list(p)})
        nbt = _lib.parse_snbt(d['blocks'][0]['nbt']) if d['blocks'] and d['blocks'][0].get('nbt') else {}
        client.append(nbt.get('level'))
    tips = []
    for gx in (6, 7, 8):
        ctx.step('hover', at=[hud['gui_left'] + 86 + 10 * gx + 5, hud['gui_top'] + 11 + 10 * 7 + 5], frames=3)
        tips.append([t['text'][9:] for t in ctx.step('hud', frames=3)['texts'] if t['text'].startswith('tooltip: ')])
    shot = ctx.step('shot', file=ctx.shot_name('depth-watch'), allow_fail=True)
    ctx.step('close', allow_fail=True)
    return dict(target_before=start, target_after=seen, changed=seen != start, server_target_level=server, client_level=client,
                grid_tooltips=tips, shot=shot.get('path'))


def act_az5(ctx, rec, args):
    hud = open_console(ctx, rec)
    ctx.step('sounds', action='start')
    for _ in range(2):              # the first click lifts the lid, the second presses AZ-5
        ctx.step('mouse', at=[hud['gui_left'] + AZ5_AT[0], hud['gui_top'] + AZ5_AT[1]], button=0, action='click', after=6)
    ctx.step('wait', ticks=20)
    snd = ctx.step('sounds', action='stop')
    ctx.step('close', allow_fail=True)
    targets = [_lib.block_data(ctx, tuple(p)).get('targetLevel') for p in rec['console']['rods']]
    return dict(sounds=sound_names(snd), rod_targets_after=targets)


def act_switch(ctx, rec, args):
    pos = tuple(rec['switch'])
    hits = []
    ctx.step('sounds', action='start')
    for _ in range(2):
        # from the east, so the user can stay where the checklist puts them (3 blocks south of the switch)
        r = S.use_face(ctx, pos, 'east', [pos[0] + 3.5, G, pos[2] + 0.5], after=40)
        hits.append((r.get('hit') or {}).get('pos'))
    snd = ctx.step('sounds', action='stop')
    return dict(hits=hits, want=list(pos), sounds=sound_names(snd, 'reactor_start'))


def near_spot(rec, what):
    """a standing spot 4 blocks south of an arrangement (inside every sound's range), or None"""
    if what == 'console':
        x, _, z = rec['console']['core']
    elif what == 'switch':
        x, _, z = rec['switch']
    elif what == 'ring':
        x, z = RING[0] + 1, RING[1] + 3
    else:
        return None
    return [x + 1.5, G, z + 4.5]


def act_sounds(ctx, rec, args):
    spot = near_spot(rec, args.near)
    if spot:
        ctx.step('view', pos=spot, yaw=180.0, pitch=0.0, fly=True, hide_gui=False)
    ctx.step('sounds', action='start')
    ctx.step('wait', ticks=args.ticks)
    snd = ctx.step('sounds', action='stop')
    return dict(ticks=args.ticks, near=args.near, stand=spot, sounds=sound_names(snd, 'reactor_start', 'explosion', 'shutdown', 'az5'))


def act_cram_reset(ctx, rec, args):
    build_ring(ctx)
    d = ctx.step('dump', **{'from': [RING[0], G, RING[1]], 'to': [RING[0] + 2, G, RING[1] + 4]})
    return dict(belts=len([b for b in d['blocks'] if b['block'] == H + 'conveyor']))


ACTS = {'depth-watch': act_depth_watch, 'az5': act_az5, 'switch': act_switch, 'sounds': act_sounds, 'cram-reset': act_cram_reset}


def cmd_act(args):
    run = make_run(args)
    rec = common.read_json(run.dir / 'arrangements.json')
    if not rec:
        raise SystemExit('no arrangements.json in ' + common.rel(run.dir))
    ctx = context(run, {args.player: channel_of(run, args.player)})
    out = ACTS[args.name](ctx, rec, args)
    out = dict(act=args.name, at=common.now_tag(), **out)
    path = run.dir / 'acts.json'
    acts = common.read_json(path, [])
    acts.append(out)
    common.write_json(path, acts)
    print(json.dumps(out, ensure_ascii=False))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    for name, func in (('build', cmd_build), ('pack', cmd_pack), ('join', cmd_join), ('leave', cmd_leave), ('act', cmd_act)):
        p = sub.add_parser(name)
        if name == 'act':
            p.add_argument('name', choices=sorted(ACTS))
            p.add_argument('ticks', nargs='?', type=int, default=600, help='sounds: client ticks to record')
            p.add_argument('--near', choices=('console', 'switch', 'ring'), help='sounds: stand 4 blocks south of it first')
        p.add_argument('--run', required=True)
        p.add_argument('--out')
        p.add_argument('--tag', default='g32u2p')
        p.add_argument('--player', default='acc_a', help='the executor client')
        p.add_argument('--argv', default='build/migration/accept/client-argv.json')
        p.add_argument('--timeout', type=int, default=600)
        p.set_defaults(func=func)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
