#!/usr/bin/env python3
"""Long run of a representative base on the loopback dedicated server: tick time, heap, network nodes, forced chunks and log errors at
the start, the middle and the end, with one server restart in between and one server profile.

Run from the NEO root, in the background (it takes about an hour with the defaults), with the display kept awake:
  caffeinate -d -i python3 -B -X utf8 tools/migration/acceptance/longrun.py --run g32g-longrun
Options: --tag (server world tag, default the run name), --players A B (client names, default acc_a acc_b), --wall-minutes (real-time
running without a sprint, default 30, half before and half after the restart), --sprint-ticks (server ticks run as /tick sprint, default
240,000, half before and half after the restart), --sprint-chunk (ticks per sprint command, default 20,000), --sample-minutes (light
samples during the real-time phases, default 5), --origin X Z (where the base is built, default 12000 12000), --out (directory for the
curve and the profile, default build/migration/goal32g/stability), --timeout (client and server start timeout, default 600).

It is drive.py's mp run (server.py start with a disposable world, two dev clients joined, run/ restored and the world deleted at the
end; results.json, steps.json and results.md under build/migration/acceptance-runs/<run>/) with one built-in scenario,
network-architecture/longrun, that is not a scenario file: the long run belongs to this batch only and is not part of the unified
acceptance. The base is the six rigs of scenarios/power-transmission/mp_stability_unload.py (power with a battery and a gauge, an
electric pump into a barrel, a belt ring fed by an extractor, a small running RBMK with its console, the long power and fluid line
across 12 chunks whose far electric furnace smelts cobblestone, a chunk with radiation set once), built in the same way.

Samples: mean tick time and percentiles (`tick query`), forced chunks (`forceload query`), error and "Can't keep up" lines of the
session's server logs, and from the server JVM (jcmd beside its own java): at start, middle and end GC.class_histogram (a full
collection, then live instance counts of the HBM node and net classes; NEO has no command that counts UniNodespace nodes) and
GC.heap_info (used heap after that collection); the light samples take GC.heap_info only (used heap with garbage). One server profile
(`perf start`, about 12 s, `perf stop`; the report zip from run/debug/profiling/ is moved to --out and the run directory). A stop that
hangs (server.py restart dumps the heap of the server JVM before giving up) ends the run; that is recorded, not repaired here.
Nothing here edits run/config or any tracked file; the base and every reading are server-side commands, steps of the executor and jcmd.
"""
import argparse
import importlib.util
import shutil
import statistics
import sys
import time
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / 'scenarios'))
import common  # noqa: E402
import drive  # noqa: E402
import _lib  # noqa: E402

REF = 'network-architecture/longrun'
OPTS = dict(wall_minutes=30.0, sprint_ticks=240000, sprint_chunk=20000, sample_minutes=5.0, origin=(12000, 12000),
            out=common.REPO / 'build' / 'migration' / 'goal32g' / 'stability')
NA = 'network-architecture.'
EXPECT = [
    ('longrun-duration', 'record and check: at least the asked real-time minutes without a sprint and the asked sprint ticks ran, with exactly one '
     'server restart in between', 'record'),
    ('longrun-tick', 'record: mean tick time and percentiles at start, middle and end and at every light sample (the curve is in the --out json)', 'record'),
    ('longrun-heap', 'record: used heap after a full collection at start, middle and end, and the used heap at every light sample', 'record'),
    ('longrun-nodes', 'record: live instances of the HBM node and net classes at start, middle and end (jcmd GC.class_histogram)', 'record'),
    ('longrun-growth', 'record: whether tick time or heap after a collection grew persistently (end against start, and the light samples of '
     'each half), with the most suspicious node or net class when they did', 'record'),
    ('longrun-forced', 'the forced chunk count is the same at every sample (the base forces none)', 'forceload query'),
    ('longrun-errors', 'no Exception or ERROR line in any server log of the session (a client socket reset on the restart left out; the '
     '"Negative index in crash report handler" lines the profile itself logs while it writes its system report inside the perf window '
     'are listed apart: PerfCommand.java:83 fills a SystemReport, CrashReport.java:175 in the 21.1.228 sources)', 'server log'),
    ('longrun-base', 'the base still works at the end: the battery holds more than at the start, the six ring items are all on the ring or in '
     'its chest, the RBMK control column still stands, the far furnace on the long line has smelted', 'record of the rigs'),
    ('longrun-profile', 'record: the perf report of the server (perf start / perf stop) moved out of run/debug/profiling', 'record'),
]


def expectations():
    return [dict(id=NA + k, text=t, source=s) for k, t, s in EXPECT]


def rigs():
    path = HERE / 'scenarios' / 'power-transmission' / 'mp_stability_unload.py'
    spec = importlib.util.spec_from_file_location('longrun_rigs', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sample(ctx, label, full, start):
    state = ctx.server()
    forced, forced_text = _lib.forced_chunks(ctx)
    return dict(label=label, wall_s=round(time.time() - start, 1), game_time=state['game_time'], sprinting=state['sprinting'],
                tick=_lib.tick_state(ctx), forced=forced, forced_text=forced_text, log=_lib.server_log_errors(),
                jvm=_lib.jvm_sample(_lib.server_jvm_pid(), full=full))


def real_time(ctx, who, minutes, samples, start, label):
    """The world runs for `minutes` of wall clock without a sprint; a light sample every --sample-minutes. Returns the seconds run."""
    began = time.time()
    end = began + minutes * 60
    next_sample = began + OPTS['sample_minutes'] * 60
    while time.time() < end:
        ctx.step('wait', client=who, ticks=max(20, min(600, int((end - time.time()) * 20))))
        if time.time() >= next_sample:
            samples.append(sample(ctx, label, False, start))
            next_sample += OPTS['sample_minutes'] * 60
    return round(time.time() - began, 1)


def sprints(ctx, total, samples, start, label):
    """`total` server ticks as /tick sprint in --sprint-chunk pieces, a light sample after each. Returns (ticks advanced, sprint records)."""
    done, recs = 0, []
    while done < total:
        n = min(OPTS['sprint_chunk'], total - done)
        r = ctx.sprint(n, label='%s-%d' % (label, done), poll_s=2.0, timeout_s=3600)
        recs.append(dict(requested=r['requested'], advanced=r['advanced'], wall_s=r['wall_s'], ticks_per_s=r['ticks_per_s']))
        done += max(r['advanced'], 0)
        samples.append(sample(ctx, label, False, start))
    return done, recs


def profile(ctx, who, out_dir):
    """perf start, about 12 s, perf stop; the report zips written under run/debug/ since the start are moved to out_dir and the run
    directory (conveyors/stress.py collects them the same way); directories this created and left empty are removed again."""
    run_dir = common.REPO / 'run'
    debug = run_dir / 'debug'
    existed = debug.exists(), (debug / 'profiling').exists()
    since = time.time()
    began = time.strftime('%H:%M:%S')
    started = ctx.rcon('perf start')
    ctx.step('wait', client=who, ticks=240)
    stopped = ctx.rcon('perf stop')
    ctx.step('wait', client=who, ticks=100)
    found = [p for p in debug.rglob('*') if p.is_file() and p.stat().st_mtime >= since] if debug.exists() else []
    moved = []
    for p in found:
        for dest in (Path(out_dir), ctx.run.dir / 'server-profile'):
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest / p.name)
        moved.append(common.rel(Path(out_dir) / p.name))
        p.unlink()
    for path, was in ((debug / 'profiling', existed[1]), (debug, existed[0])):
        if not was and path.is_dir() and not any(path.iterdir()):
            path.rmdir()
    return dict(perf_start=started, perf_stop=stopped, reports=moved, window=[began, time.strftime('%H:%M:%S')])


def log_errors_split(window):
    """The session's server logs (as _lib.server_log_errors reads them): ERROR / Exception lines, without the client socket resets,
    split into the profile's own CrashReport lines inside the perf window [HH:MM:SS, HH:MM:SS] and every other one."""
    import re
    session = common.read_json(common.SESSION) or {}
    pattern = re.compile(r'server-%s-\d{8}-\d{6}\.log$' % re.escape(session.get('tag') or ''))
    perf, other = [], []
    for p in sorted(x for x in (common.STATE / 'logs').glob('server-*.log') if pattern.search(x.name)):
        text = p.read_text(encoding='utf-8', errors='replace').splitlines()
        for i, line in enumerate(text):
            if not re.search(r'Exception|\bERROR\b|/ERROR\]', line):
                continue
            if 'Connection reset' in line or (i + 1 < len(text) and 'Connection reset' in text[i + 1]):
                continue
            stamp = line[1:9]
            if window and 'Negative index in crash report handler' in line and window[0] <= stamp <= window[1]:
                perf.append(line[:200])
            else:
                other.append(line[:200])
    return dict(other=len(other), other_sample=other[:8], perf_report_lines=len(perf), perf_sample=perf[:3])


def base_state(ctx, U, s):
    Z = U.Z
    L = s['line']
    sock = U.data(ctx, s['socket'])
    furnace = U.data(ctx, L['furnace'])
    ring = Z.entity_count(ctx, U.ring_selector(s))
    chest = sum(it.get('count', 1) for it in U.data(ctx, s['chest']).get('Items', []))
    smelted = sum(it.get('count', 1) for it in furnace.get('Items', []) if it.get('Slot') == 2)
    control = Z.block_is(ctx, s['cells'][U.CONTROL_AT], U.H + 'rbmk_control')
    return dict(charge=U.charge(sock), ring=ring, chest=chest, rbmk_control=control, furnace_power=furnace.get('power'), smelted=smelted,
                source_heat=U.data(ctx, s['cells'][U.SOURCE_AT]).get('heat'))


def growth(samples):
    """Persistent growth: the light samples of each half are compared first against last, and the full samples end against start."""
    full = [x for x in samples if x['jvm'].get('full')]
    out = {}
    tick = [x['tick']['mean_ms'] for x in samples if x['tick']['mean_ms'] is not None]
    heap = [x['jvm']['heap_used_kb'] for x in full if x['jvm'].get('heap_used_kb')]
    if len(tick) >= 4:
        q = max(1, len(tick) // 4)
        out['tick_first_quarter_ms'] = round(statistics.mean(tick[:q]), 2)
        out['tick_last_quarter_ms'] = round(statistics.mean(tick[-q:]), 2)
    if len(heap) >= 2:
        out['heap_after_gc_kb'] = heap
        out['heap_end_over_start'] = round(heap[-1] / heap[0], 3)
    if len(full) >= 2:
        first, last = full[0]['jvm'].get('node_classes', {}), full[-1]['jvm'].get('node_classes', {})
        diff = {k: (first.get(k, 0), last.get(k, 0)) for k in set(first) | set(last) if first.get(k, 0) != last.get(k, 0)}
        out['node_class_changes'] = diff
        if diff:
            out['most_growth'] = max(diff, key=lambda k: diff[k][1] - diff[k][0])
    return out


def run(ctx):
    a, b = list(ctx.channels)
    U = rigs()
    Z = U.Z
    start = time.time()
    Z.setup_world(ctx, a, b)
    s = U.layout(*OPTS['origin'])
    built = U.build_all(ctx, a, s, line_items=True)
    rad = U.set_radiation(ctx, a, s)
    U.view(ctx, a, s['spot_a'])
    U.view(ctx, b, s['line']['spot_b'])
    ctx.server('tick unfreeze')
    ctx.step('wait', client=a, ticks=200)
    samples = [sample(ctx, 'start', True, start)]
    base0 = base_state(ctx, U, s)

    wall1 = real_time(ctx, a, OPTS['wall_minutes'] / 2.0, samples, start, 'real-time-1')
    spr1, recs1 = sprints(ctx, OPTS['sprint_ticks'] // 2, samples, start, 'sprint-1')
    samples.append(sample(ctx, 'middle', True, start))
    prof = profile(ctx, a, OPTS['out'])
    _lib.server_idle(ctx, a)
    t = time.time()
    ctx.restart_server()
    restart_s = round(time.time() - t, 1)
    ctx.step('wait', client=a, ticks=200)
    samples.append(sample(ctx, 'after-restart', False, start))
    wall2 = real_time(ctx, a, OPTS['wall_minutes'] / 2.0, samples, start, 'real-time-2')
    spr2, recs2 = sprints(ctx, OPTS['sprint_ticks'] - OPTS['sprint_ticks'] // 2, samples, start, 'sprint-2')
    samples.append(sample(ctx, 'end', True, start))
    base1 = base_state(ctx, U, s)
    grow = growth(samples)

    curve = dict(run=ctx.run.dir.name, options={k: (str(v) if isinstance(v, Path) else v) for k, v in OPTS.items()}, built=built, radiation=rad,
                 wall_real_time_s=[wall1, wall2], sprint_ticks=[spr1, spr2], sprints=recs1 + recs2, restart_s=restart_s, profile=prof,
                 base_start=base0, base_end=base1, growth=grow, samples=samples)
    out = Path(OPTS['out']) / ('longrun-%s.json' % ctx.run.dir.name)
    common.write_json(out, curve)
    common.write_json(ctx.run.dir / 'longrun.json', curve)

    full = [x for x in samples if x['jvm'].get('full')]
    ctx.check(NA + 'longrun-duration', wall1 + wall2 >= OPTS['wall_minutes'] * 60 - 30 and spr1 + spr2 >= OPTS['sprint_ticks'] and len(ctx.run.restarts) == 1,
              'real time without a sprint %s s (asked %s min); sprint ticks advanced %s (asked %s); restarts %s; curve %s'
              % ([wall1, wall2], OPTS['wall_minutes'], [spr1, spr2], OPTS['sprint_ticks'], ctx.run.restarts, common.rel(out)))
    ctx.review(NA + 'longrun-tick', '; '.join('%s %s ms %s' % (x['label'], x['tick']['mean_ms'], x['tick']['percentiles']) for x in samples))
    ctx.review(NA + 'longrun-heap', '; '.join('%s %s KB%s' % (x['label'], x['jvm'].get('heap_used_kb'), ' (after a full GC)' if x['jvm'].get('full') else '')
                                            for x in samples))
    ctx.review(NA + 'longrun-nodes', '; '.join('%s nodes %s nets %s %s' % (x['label'], x['jvm'].get('nodes'), x['jvm'].get('nets'), x['jvm'].get('node_classes'))
                                             for x in full))
    ctx.review(NA + 'longrun-growth', str(grow))
    forced = sorted({x['forced'] for x in samples}, key=str)
    ctx.check(NA + 'longrun-forced', len(forced) == 1, 'forced chunk counts seen %s' % forced)
    last_log = samples[-1]['log']
    split = log_errors_split(prof.get('window'))
    ctx.check(NA + 'longrun-errors', split['other'] == 0, '%s; all error lines counted by the samples %s' % (split, last_log))
    ctx.check(NA + 'longrun-base', (base1['charge'] or 0) > (base0['charge'] or 0) and base1['ring'] + base1['chest'] == U.RING_ITEMS
              and base1['rbmk_control'] and base1['smelted'] > 0, 'start %s; end %s' % (base0, base1))
    ctx.review(NA + 'longrun-profile', str(prof))
    _lib.server_idle(ctx, a)


def scenario_module():
    module = types.ModuleType('longrun_scenario')
    module.SCENARIO = dict(id=REF.replace('/', '.'), feature='network-architecture',
                           features=['network-architecture', 'power-transmission', 'fluid-pipelines', 'conveyors', 'rbmk-reactor', 'hazard-system'],
                           title='Long run of a representative base: tick time, heap, nodes, forced chunks, log errors; one restart; one profile',
                           group='mp', capture=dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70))
    module.expectations = expectations
    module.run = run
    module.REF = REF
    return module


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--run', required=True, help='run name (build/migration/acceptance-runs/<run>)')
    ap.add_argument('--tag', help='server world tag (default: the run name)')
    ap.add_argument('--players', nargs=2, default=['acc_a', 'acc_b'])
    ap.add_argument('--wall-minutes', type=float, default=30.0)
    ap.add_argument('--sprint-ticks', type=int, default=240000)
    ap.add_argument('--sprint-chunk', type=int, default=20000)
    ap.add_argument('--sample-minutes', type=float, default=5.0)
    ap.add_argument('--origin', type=int, nargs=2, default=[12000, 12000])
    ap.add_argument('--out', default='build/migration/goal32g/stability')
    ap.add_argument('--timeout', type=int, default=600)
    args = ap.parse_args(argv)
    OPTS.update(wall_minutes=args.wall_minutes, sprint_ticks=args.sprint_ticks, sprint_chunk=args.sprint_chunk,
                sample_minutes=args.sample_minutes, origin=tuple(args.origin), out=common.resolve(args.out))
    module = scenario_module()
    original_load = drive.load

    def load(ref):
        return module if ref == REF else original_load(ref)
    drive.load = load
    return drive.main(['run', '--run', args.run, '--group', 'mp', '--tag', args.tag or args.run, '--players', *args.players,
                       '--timeout', str(args.timeout), REF])


if __name__ == '__main__':
    sys.exit(main())
