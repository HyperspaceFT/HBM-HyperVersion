#!/usr/bin/env python3
"""User-station world: builds the stations of station scenarios into a flat corridor world through the dev client and the
acceptance executor, saves it, packs it with a checklist, and reopens it once to check that it loads.

Run from the NEO root:
  python3 -B -X utf8 tools/migration/acceptance/stations.py build --run stations1 conveyors/stations_sample

Each station sits 16 blocks further east along z = 0 and gets: an oak sign with its number and three short lines, the
station content (built by the scenario's build(ctx, x, z) with commands and executor steps), a copy of the station kept
150 blocks above it as the template, and a command block with a stone button that clones the template back (reset).
The world is saved (the executor leaves the world), zipped to <run>/<world>.zip, and STATIONS.md lists every station
with what to do, what to expect and an empty result column (pass / fail with what happened / skipped): a station
without a reported result counts as not run. Then the world is opened again in the dev client and every station's
sign and reset command block are read back on the server side (reload check); a station's optional probe(ctx, x, z)
checks that it works after the reload, and the station is cleared and its reset button pressed like a player, the
rebuilt blocks compared with the template. Sign lines must be ASCII. The zip is what goes to the user; the
world in the client's saves/ is disposable (client.py clean removes it with the client). Nothing else is written outside
the run directory and the client's own directory.
"""
import argparse
import json
import re
import sys
import time
import traceback
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import drive  # noqa: E402

SPACING = 16
TEMPLATE_DY = 150
G = -60


def sign_command(x, z, number, short):
    lines = ['S%d' % number] + list(short[:3])
    if not all(line.isascii() for line in lines):
        raise SystemExit('station %d: sign lines must be ASCII (a sign shows what the player\'s font has): %s' % (number, lines))
    messages = ','.join("'%s'" % json.dumps(line[:15]) for line in lines + [''] * (4 - len(lines)))
    return 'setblock %d %d %d minecraft:oak_sign[rotation=8]{front_text:{messages:[%s]}}' % (x, G, z, messages)


def build_station(ctx, number, station):
    x0 = (number - 1) * SPACING
    sx, sy, sz = station.get('size', (4, 2, 4))
    content_x, content_z = x0, 4
    ctx.step('view', pos=[x0 + 0.5, G + 6, -6.5], pitch=45.0, yaw=0.0, hide_gui=False)
    ctx.step('wait', ticks=10)
    station['build'](ctx, content_x, content_z)
    lo = (content_x - 2, G, content_z - 2)
    hi = (content_x + sx + 1, G + sy + 1, content_z + sz + 1)
    # the template is a working copy: keep it still, or its extractors empty its chests before anyone presses reset. A
    # redstone block under each extractor of the bottom layer, put there before the clone, powers it from outside the
    # cloned volume.
    for x, y, z in extractors(ctx, lo, hi):
        ctx.step('cmd', command='setblock %d %d %d minecraft:redstone_block' % (x, y + TEMPLATE_DY - 1, z))
    ctx.step('cmd', command='clone %d %d %d %d %d %d %d %d %d replace' % (lo + hi + (lo[0], lo[1] + TEMPLATE_DY, lo[2])))
    reset = 'clone %d %d %d %d %d %d %d %d %d replace' % ((lo[0], lo[1] + TEMPLATE_DY, lo[2]) + (hi[0], hi[1] + TEMPLATE_DY, hi[2]) + lo)
    ctx.step('cmd', command='setblock %d %d %d minecraft:command_block{Command:%s}' % (x0 - 3, G, 0, json.dumps(reset)))
    ctx.step('cmd', command='setblock %d %d %d minecraft:stone_button[face=floor]' % (x0 - 3, G + 1, 0))
    ctx.step('cmd', command=sign_command(x0 - 1, 0, number, station['short']))
    return dict(number=number, id=station['id'], todo=station['todo'], expect=station['expect'], sign=[x0 - 1, G, 0],
                reset_block=[x0 - 3, G, 0], content=[list(lo), list(hi)], template=[[lo[0], lo[1] + TEMPLATE_DY, lo[2]], [hi[0], hi[1] + TEMPLATE_DY, hi[2]]])


def extractors(ctx, lo, hi):
    """positions of the extractors in a station; each must stand on its bottom layer (see build_station)"""
    ctx.step('wait', ticks=2)
    out = []
    for b in ctx.step('dump', **{'from': list(lo), 'to': list(hi)})['blocks']:
        if b['block'] == 'hbmsntm:crane_extractor':
            x, y, z = (int(v) for v in b['pos'])
            if y != lo[1]:
                raise SystemExit('an extractor above the bottom layer of a station cannot be held still: %s' % ((x, y, z),))
            out.append((x, y, z))
    return out


def block_set(ctx, lo, hi, dy=0):
    """(relative position, block, properties) of every non-air block from lo to hi, as the client sees them."""
    d = ctx.step('dump', **{'from': list(lo), 'to': list(hi)})
    return sorted((b['pos'][0] - lo[0], b['pos'][1] - lo[1], b['pos'][2] - lo[2], b['block'], json.dumps(b.get('props', {}), sort_keys=True))
                  for b in d['blocks'])


CONTAINERS = ('minecraft:chest', 'hbmsntm:crane_extractor', 'hbmsntm:crane_inserter', 'hbmsntm:crane_router', 'hbmsntm:fluid_duct_neo')


def contents(ctx, pos):
    """the server's block entity data of one block, without the position the reply starts with"""
    r = ctx.step('cmd', command='data get block %d %d %d' % tuple(pos), allow_error=True, wait_ticks=2)
    text = ' '.join(m.get('text', '') for m in r.get('messages', []))
    text = re.sub(r'^.*?(has the following block data|拥有以下方块数据)[:：]\s*', '', text)
    # the block entity's own x, y, z differ between the template and the station by design
    return re.sub(r'\b[xyz]: -?\d+, ', '', text)


def reset_check(ctx, r):
    """Clears the station, presses its reset button like a player and compares the station with its template."""
    lo, hi = r['content']
    tlo, thi = r['template']
    bx, by, bz = r['reset_block']
    ctx.step('view', pos=[bx + 0.5, G, bz - 2.5], look_at=[bx + 0.5, G + 1.05, bz + 0.5], fly=False, hide_gui=False)
    ctx.step('wait', ticks=10)
    template = block_set(ctx, tlo, thi)
    ctx.step('cmd', command='fill %d %d %d %d %d %d minecraft:air' % (tuple(lo) + tuple(hi)))
    # items the probe left moving on the belts are entities, which neither the clear nor the clone touches
    box = 'x=%d,y=%d,z=%d,dx=%d,dy=%d,dz=%d' % (tuple(lo) + tuple(h - l + 1 for h, l in zip(hi, lo)))
    for kind in ('minecraft:item', 'hbmsntm:moving_item', 'hbmsntm:moving_package'):
        ctx.step('cmd', command='kill @e[type=%s,%s]' % (kind, box), allow_error=True)
    ctx.step('wait', ticks=4)
    cleared = len(block_set(ctx, lo, hi))
    # the restored extractors are held still the template's way while the contents are compared (the ground under them
    # is put back afterwards)
    held = [(x - tlo[0] + lo[0], y - tlo[1] + lo[1], z - tlo[2] + lo[2]) for x, y, z in extractors(ctx, tlo, thi)]
    ground = {}
    for x, y, z in held:
        below = ctx.step('dump', **{'from': [x, y - 1, z]})['blocks']
        ground[(x, y, z)] = below[0]['block'] if below else 'minecraft:air'
        ctx.step('cmd', command='setblock %d %d %d minecraft:redstone_block' % (x, y - 1, z))
    # the ray may enter the small floor button through a side; any face of the button presses it
    press = ctx.step('use', target=dict(pos=[bx, by + 1, bz], face='up', offset=[0, -0.9, 0]), any_hit=True, after=10)
    after = block_set(ctx, lo, hi)
    hit = press.get('hit') or {}
    # the contents too (feed chests, filters, duct types), read on the server: the template against the restored station
    differ = []
    for dx, dy, dz, block, _ in template:
        if block in CONTAINERS:
            t = contents(ctx, (tlo[0] + dx, tlo[1] + dy, tlo[2] + dz))
            live = contents(ctx, (lo[0] + dx, lo[1] + dy, lo[2] + dz))
            if t != live:
                differ.append(dict(at=[dx, dy, dz], block=block, template=t[:160], restored=live[:160]))
    for (x, y, z), block in ground.items():
        ctx.step('cmd', command='setblock %d %d %d %s' % (x, y - 1, z, block))
    return dict(template_blocks=len(template), cleared_blocks=cleared, after_press_blocks=len(after), contents_differ=differ,
                same_as_template=after == template and not differ and hit.get('pos') == [bx, by + 1, bz], press_hit=hit)


def reply_has(result, text):
    return result.get('status') == 'ok' and any(text in m.get('text', '') for m in result.get('messages', []))


def cmd_build(args):
    modules = [drive.load(ref) for ref in args.scenarios]
    stations = [s for m in modules if m.SCENARIO.get('station') for s in m.STATIONS]
    if not stations:
        raise SystemExit('no station scenarios given')
    if len(stations) > 25:
        raise SystemExit('more than 25 stations (the user budget)')
    run = drive.Run(argparse.Namespace(out=args.out, run=args.run, argv=args.argv, option=[]))
    capture = dict(drive.DEFAULT_CAPTURE, lang=args.lang)
    saves = common.CLIENTS / args.client / 'saves' / args.world
    if saves.exists():
        raise SystemExit('world %s already exists in client %s' % (args.world, args.client))
    records, failure, channel = [], None, None
    t0 = time.time()
    try:
        channel = drive.start_client(run, args.client, capture)
        channel.hello(args.timeout)
        ctx = drive.Context(run, modules[0], {args.client: channel})
        ctx.step('newworld', world=args.world)
        for command in ('gamerule doDaylightCycle false', 'gamerule doWeatherCycle false', 'gamerule doMobSpawning false', 'time set 6000',
                        'weather clear', 'setworldspawn 0 -60 -6'):
            ctx.step('cmd', command=command)
        for number, station in enumerate(stations, 1):
            records.append(build_station(ctx, number, station))
        ctx.step('view', pos=[0.5, G, -6.5], yaw=0.0, pitch=0.0, fly=False, hide_gui=False)
        ctx.step('leave')
        # pack the saved world
        archive = run.dir / ('%s.zip' % args.world)
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
            for path in sorted(saves.rglob('*')):
                if path.is_file() and path.name != 'session.lock':
                    z.write(path, Path(args.world) / path.relative_to(saves))
        # reload check
        ctx.step('openworld', world=args.world)
        for r in records:
            # read back on the server side: the client is never sent a command block's command
            sign = ctx.step('cmd', command='data get block %d %d %d front_text' % tuple(r['sign']), allow_fail=True)
            reset = ctx.step('cmd', command='data get block %d %d %d Command' % tuple(r['reset_block']), allow_fail=True)
            r['reload_check'] = dict(sign_text_ok=reply_has(sign, '"S%d"' % r['number']), reset_command_ok=reply_has(reset, 'clone '))
        # each station works after the reload (its probe), then its reset button really restores it
        by_id = {s['id']: s for s in stations}
        for r in records:
            x0 = (r['number'] - 1) * SPACING
            probe = by_id[r['id']].get('probe')
            if probe:
                ctx.step('view', pos=[x0 + 0.5, G + 6, -6.5], pitch=45.0, yaw=0.0, fly=True, hide_gui=False)
                ok, detail = probe(ctx, x0, 4)
                r['probe'] = dict(ok=bool(ok), detail=detail)
            r['reset_check'] = reset_check(ctx, r)
    except (drive.ClientGone, drive.StepFailed) as e:
        failure = str(e)
    except Exception:
        failure = 'station build error: ' + traceback.format_exc(limit=3).strip().splitlines()[-1]
        traceback.print_exc()
    finally:
        drive.stop_client(args.client, channel)
    ok = not failure and all(r.get('reload_check', {}).get('sign_text_ok') and r['reload_check'].get('reset_command_ok')
                             and r.get('reset_check', {}).get('same_as_template') and r.get('probe', {}).get('ok', True) for r in records)
    data = dict(world=args.world, client=args.client, archive=common.rel(run.dir / ('%s.zip' % args.world)), stations=records,
                failure=failure, reload_ok=ok, seconds=round(time.time() - t0, 1),
                needs='NeoForge 21.1.228 or later with the release jar of this mod (and JEI where a station uses it)')
    common.write_json(run.dir / 'stations.json', data)
    lines = ['# 站点：%s' % args.world, '',
             '把 `%s` 解压进 NeoForge 21.1.228 或更新版本、装着本模组发布版 JAR（站点用到 JEI 时也装 JEI）的实例的 `saves/`，打开世界 `%s`。'
             '载入时若出现任何警告或报错（实验性设置、缺少方块、日志里的红字），请原样记下来一起回报。'
             '沿走廊往东走，每个站点有一块写着编号的牌子，旁边命令方块上的石头按钮会把这个站点复原。'
             '每个站点回报一项：通过、不通过（写看到了什么）或跳过。没有回报的站点算未执行；到场时已经坏了的站点也算未执行（先按复位按钮再做）。'
             % (Path(data['archive']).name, args.world), '',
             '| 站点 | 怎么做 | 应该看到或听到 | 结果 |', '| --- | --- | --- | --- |']
    for r in records:
        lines.append('| S%d `%s` | %s | %s |  |' % (r['number'], r['id'], r['todo'], r['expect']))
    (run.dir / 'STATIONS.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps(dict(stations=len(records), reload_ok=ok, failure=failure, seconds=data['seconds'], archive=data['archive'])))
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    p = sub.add_parser('build')
    p.add_argument('scenarios', nargs='+')
    p.add_argument('--run', required=True)
    p.add_argument('--out')
    p.add_argument('--client', default='g31e_solo')
    p.add_argument('--world', default=common.WORLD_PREFIX + 'g31e-stations')
    p.add_argument('--argv', default='build/migration/accept-goal29/client-argv-g31e.json')
    p.add_argument('--lang', default='zh_cn')
    p.add_argument('--timeout', type=int, default=600)
    p.set_defaults(func=cmd_build)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
