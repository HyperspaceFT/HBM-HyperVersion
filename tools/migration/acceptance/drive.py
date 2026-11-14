#!/usr/bin/env python3
"""Scripted acceptance runs: scenarios (scenarios/<feature>/<name>.py) sent as steps to the acceptance executor.

Run from the NEO root:
  python3 -B -X utf8 tools/migration/acceptance/drive.py list
  python3 -B -X utf8 tools/migration/acceptance/drive.py run --run pilot1 --group solo conveyor-cranes/crane_faces
  python3 -B -X utf8 tools/migration/acceptance/drive.py run --run mp1 --group mp smoke/multiplayer
  python3 -B -X utf8 tools/migration/acceptance/drive.py judge build/migration/acceptance-runs/pilot1 ID --verdict pass --note "..."
  python3 -B -X utf8 tools/migration/acceptance/drive.py report build/migration/acceptance-runs/pilot1

run      solo: starts one dev client (client.py start with -Dhbm.accept.dir and the run's window size, GUI scale and
         language), creates the run's flat creative world through the executor (or opens it when it exists), runs the
         scenarios in order, quits the client and writes results.json and results.md into the run directory
         (default build/migration/acceptance-runs/<run>). mp: starts a loopback dedicated server (server.py start), two
         clients joined to it, runs the scenarios (steps go to a named client, server commands over RCON), then stops
         the clients and the server, restores run/ and deletes the server world. The client names, the world names
         and the server tag come from the options; they must not be ones another session uses.
judge    records the reviewer's verdict for an expectation the run left "review" (or overrides one with a note);
         judgments.json is kept apart from the machine verdicts and both are shown by report.
report   rewrites results.md from results.json and judgments.json.

The exit code of run is 1 when the run itself failed (a client or the server did not start, a client died); failed
expectations are in the results, not in the exit code.

Verdicts: pass, fail, review (no assertion, only evidence for a person), not-run (with the reason). A step that fails
ends its scenario: the expectations it had not decided become not-run with that step's reason. Python standard
library only; nothing here drives the window through the operating system.
"""
import argparse
import importlib.util
import json
import re
import statistics
import subprocess
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

HERE = Path(__file__).resolve().parent
SCENARIOS = HERE / 'scenarios'
RUNS = common.REPO / 'build' / 'migration' / 'acceptance-runs'
VERDICTS = ('pass', 'fail', 'review', 'not-run')
VERDICT_ZH = {'pass': '通过', 'fail': '不通过', 'review': '待人看', 'not-run': '未执行'}
# The fixed capture parameters of a run: every scenario's CAPTURE must agree with them or it is not run.
HELD_KEYS = ('key.keyboard.left.shift', 'key.keyboard.left.control', 'key.keyboard.left.alt')
DEFAULT_CAPTURE = dict(window=[854, 480], gui_scale=2, lang='zh_cn', fov=70)


class StepFailed(Exception):
    def __init__(self, result):
        super().__init__('%s failed: %s' % (result.get('op'), result.get('reason')))
        self.result = result


class ClientGone(Exception):
    pass


def tool(script, *argv):
    """Runs client.py or server.py as its own process: the Gradle or JVM process it starts must not become a child of
    this one (an unreaped child stays a zombie that the tools' pid checks take for a running process)."""
    return subprocess.run([sys.executable, '-B', '-X', 'utf8', str(HERE / script), *argv], cwd=common.REPO).returncode


# ---------------------------------------------------------------- talking to one executor

class Channel:
    """The step directory of one client: in/<seq>.json written atomically, out/<seq>.json read back."""

    def __init__(self, name, directory, alive=lambda: True):
        self.name = name
        self.dir = Path(directory)
        self.alive = alive
        (self.dir / 'in').mkdir(parents=True, exist_ok=True)
        (self.dir / 'out').mkdir(parents=True, exist_ok=True)
        done = [int(p.stem) for p in (self.dir / 'out').glob('*.json') if p.stem.isdigit()]
        sent = [int(p.stem) for p in (self.dir / 'in').glob('*.json') if p.stem.isdigit()]
        self.seq = max(done + sent + [0])
        self.log = []

    def hello(self, timeout):
        end = time.time() + timeout
        path = self.dir / 'hello.json'
        while time.time() < end:
            if path.is_file():
                return json.loads(path.read_text(encoding='utf-8'))
            if not self.alive():
                raise ClientGone('%s exited before the executor started' % self.name)
            time.sleep(0.25)
        raise ClientGone('%s: no hello.json within %ds' % (self.name, timeout))

    def send(self, spec, timeout=None):
        self.seq += 1
        name = '%06d.json' % self.seq
        tmp = self.dir / 'in' / (name + '.tmp')
        tmp.write_text(json.dumps(spec, ensure_ascii=False), encoding='utf-8')
        sent = time.time()
        tmp.replace(self.dir / 'in' / name)
        out = self.dir / 'out' / name
        limit = timeout or (spec.get('timeout_ticks', 20 * 600) / 20.0 + 60)
        checked = sent
        while not out.is_file():
            time.sleep(0.02)
            now = time.time()
            if now - checked > 5:
                checked = now
                if not self.alive():
                    raise ClientGone('%s exited during step %d (%s)' % (self.name, self.seq, spec.get('op')))
            if now - sent > limit:
                raise ClientGone('%s: no result for step %d (%s) within %ds' % (self.name, self.seq, spec.get('op'), limit))
        for _ in range(50):
            try:
                result = json.loads(out.read_text(encoding='utf-8'))
                break
            except json.JSONDecodeError:
                time.sleep(0.02)
        result['wall_ms'] = round((time.time() - sent) * 1000)
        result['client'] = self.name
        self.log.append(result)
        return result


# ---------------------------------------------------------------- scenario context

class Context:
    """What a scenario's run(ctx) sees. Steps return the executor's result; a failed step raises StepFailed unless
    allow_fail=True. Verdicts: check (assertion), review (evidence for a person), not_run (with the reason)."""

    def __init__(self, run, scenario, channels, rcon=None):
        self.run = run
        self.scenario = scenario
        self.meta = scenario.SCENARIO
        self.channels = channels
        self.default = next(iter(channels))
        self._rcon = rcon
        self.verdicts = {}
        self.capture = dict(DEFAULT_CAPTURE, **self.meta.get('capture', {}))
        if getattr(getattr(run, 'args', None), 'scenario_lang', None):  # the one English pass over scenarios written for Chinese
            self.capture['lang'] = run.args.scenario_lang
        self.prefix = self.meta['id'].replace('.', '/')

    def step(self, op, client=None, allow_fail=False, timeout=None, **fields):
        spec = dict(op=op, **fields)
        result = self.channels[client or self.default].send(spec, timeout)
        if result.get('status') != 'ok' and not allow_fail:
            raise StepFailed(result)
        return result

    def restart_server(self):
        """mp only: stops both clients, restarts the dedicated server on the same world (server.py restart) and joins
        the clients again; their step directories continue where they stopped."""
        if self._rcon is None:
            raise StepFailed(dict(op='restart', reason='no dedicated server in a solo run'))
        restart_mp(self.run, self.channels)

    def shot_name(self, name):
        return '%s/%s' % (self.prefix, name)

    def rcon(self, *commands):
        if self._rcon is None:
            raise StepFailed(dict(op='rcon', reason='no dedicated server in a solo run'))
        replies = []
        client = self._rcon()
        try:
            for command in commands:
                started = time.time()
                reply = client.command(command)
                replies.append(reply)
                self.run.rcon_log.append(dict(command=command, reply=reply, wall_ms=round((time.time() - started) * 1000)))
        finally:
            client.close()
        return replies

    def _set(self, eid, verdict, detail, evidence):
        if eid in self.verdicts:
            raise ValueError('expectation decided twice: ' + eid)
        self.verdicts[eid] = dict(verdict=verdict, detail=detail, evidence=list(evidence or []))

    def check(self, eid, ok, detail='', evidence=()):
        self._set(eid, 'pass' if ok else 'fail', detail, evidence)
        return ok

    def review(self, eid, detail='', evidence=()):
        self._set(eid, 'review', detail, evidence)

    def not_run(self, eid, reason):
        self._set(eid, 'not-run', reason, ())


# ---------------------------------------------------------------- scenarios

def scenario_files():
    return sorted(p for p in SCENARIOS.glob('*/*.py') if not p.name.startswith('_'))


def load(ref):
    """ref: <feature>/<name> (file scenarios/<feature>/<name>.py)."""
    path = SCENARIOS / (ref + '.py')
    if not path.is_file():
        raise SystemExit('no scenario ' + ref)
    spec = importlib.util.spec_from_file_location('scenario_' + re.sub(r'\W', '_', ref), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    meta = module.SCENARIO
    feature = path.parent.name
    if meta.get('feature') != feature or not meta.get('id', '').startswith(feature + '.'):
        raise SystemExit('%s: SCENARIO feature/id must match the directory %s' % (ref, feature))
    module.REF = ref
    return module


def expectation_list(module):
    items = module.expectations()
    ids = [e['id'] for e in items]
    if len(ids) != len(set(ids)):
        raise SystemExit('%s: duplicate expectation ids' % module.REF)
    prefix = module.SCENARIO['feature'] + '.'
    bad = [i for i in ids if not i.startswith(prefix)]
    if bad:
        raise SystemExit('%s: expectation ids must start with %s: %s' % (module.REF, prefix, bad[:3]))
    return items


# ---------------------------------------------------------------- runs

class Run:
    def __init__(self, args):
        self.args = args
        self.dir = common.resolve(args.out) if args.out else RUNS / args.run
        self.dir.mkdir(parents=True, exist_ok=True)
        self.timings = {}
        self.rcon_log = []
        self.restarts = []
        self.hello = {}
        self.started = time.time()

    def mark(self, key, since):
        self.timings[key] = round(time.time() - since, 2)


def start_client(run, name, capture, server=None):
    directory = run.dir / name
    directory.mkdir(parents=True, exist_ok=True)
    w, h = capture['window']
    argv = ['start', name, '--argv', run.args.argv, '--jvm-prop', 'hbm.accept.dir=%s' % directory, '--size', '%dx%d' % (w, h),
            '--lang', capture['lang'], '--option', 'guiScale:%d' % capture['gui_scale'],
            '--option', 'fov:%s' % ((capture['fov'] - 70) / 40.0)]
    for option in run.args.option:
        argv += ['--option', option]
    if server:
        argv += ['--server', server]
    if tool('client.py', *argv) != 0:
        raise ClientGone('client.py start %s failed' % name)
    # The start wrapper writes exit-code.txt when the JVM ends (client.py removes it before the start); the JVM itself
    # shows up in the process list only a moment after the wrapper.
    exit_file = common.CLIENTS / name / 'exit-code.txt'
    return Channel(name, directory, alive=lambda: not exit_file.exists())


def stop_client(name, channel, timeout=120):
    """Ends the client through the executor (Minecraft.stop after leaving the world, so the world is saved), then
    falls back to client.py stop (TERM)."""
    import client as client_tool
    if channel is not None and client_tool.jvm_of(name):
        try:
            channel.send(dict(op='quit'), timeout=timeout)
        except ClientGone:
            pass
        end = time.time() + timeout
        while time.time() < end and client_tool.jvm_of(name):
            time.sleep(0.5)
    if client_tool.jvm_of(name):
        tool('client.py', 'stop', name, '--no-kick')


def join(run, name, channels, old=None):
    """Starts client `name` against the loopback server and waits until it is in the world."""
    t = time.time()
    if old is not None:
        for stale in ('hello.json', 'status.json'):
            (old.dir / stale).unlink(missing_ok=True)
    channel = start_client(run, name, run.capture, server='%s:25565' % common.LOOPBACK)
    if old is not None:
        channel.log = old.log
    channels[name] = channel
    run.hello.setdefault(name, channel.hello(run.args.timeout))
    end = time.time() + run.args.timeout
    while time.time() < end:
        status = common.read_json(channel.dir / 'status.json') or {}
        if status.get('in_world'):
            break
        time.sleep(1)
    else:
        raise ClientGone('%s did not join' % name)
    return round(time.time() - t, 2)


def restart_mp(run, channels):
    t = time.time()
    for name, channel in list(channels.items()):
        stop_client(name, channel)
    if tool('server.py', 'restart') != 0:
        raise ClientGone('server.py restart failed')
    for name, channel in list(channels.items()):
        join(run, name, channels, old=channel)
    run.restarts.append(round(time.time() - t, 2))


def run_scenarios(run, modules, channels, rcon=None):
    records = []
    for module in modules:
        meta = module.SCENARIO
        items = expectation_list(module)
        ctx = Context(run, module, channels, rcon)
        started = time.time()
        error = None
        mismatch = [k for k in ('window', 'gui_scale', 'fov') if ctx.capture[k] != run.capture[k]]
        if mismatch:
            error = 'capture parameters differ from the run (%s); run it in a run with the same values' % ', '.join(mismatch)
        else:
            try:
                if ctx.capture['lang'] != run.current_lang:
                    ctx.step('lang', code=ctx.capture['lang'])
                    run.current_lang = ctx.capture['lang']
                module.run(ctx)
            except StepFailed as e:
                error = 'step %s (%s) failed: %s' % (e.result.get('seq'), e.result.get('op'), e.result.get('reason'))
            except ClientGone:
                raise
            except Exception:
                error = 'scenario error: ' + traceback.format_exc(limit=3).strip().splitlines()[-1]
                traceback.print_exc()
            finally:
                # Modifier flags and keys a scenario held with the key step (sneak, the settings tool's two keys) are
                # released here as well, so a scenario that ended early does not leave the next one sneaking.
                for channel in channels.values():
                    channel.send(dict(op='mod', shift=False, control=False, alt=False))
                    for key in HELD_KEYS:
                        channel.send(dict(op='key', key=key, action='release', after=0))
        expectations = []
        for item in items:
            v = ctx.verdicts.pop(item['id'], None)
            if v is None:
                v = dict(verdict='not-run', detail=error or 'the scenario did not decide it', evidence=[])
            expectations.append(dict(item, **v))
        if ctx.verdicts:
            raise SystemExit('%s decided undeclared expectations: %s' % (module.REF, sorted(ctx.verdicts)[:5]))
        records.append(dict(ref=module.REF, id=meta['id'], feature=meta['feature'], title=meta.get('title', ''),
                            capture=ctx.capture, station=bool(meta.get('station')), error=error,
                            started=started, duration_s=round(time.time() - started, 2), expectations=expectations))
        print('%-40s %6.1fs  %s' % (module.REF, time.time() - started,
                                     ' '.join('%s=%d' % (k, sum(1 for e in expectations if e['verdict'] == k)) for k in VERDICTS)))
    return records


def cmd_run(args):
    modules = [load(ref) for ref in args.scenarios]
    run = Run(args)
    run.capture = dict(DEFAULT_CAPTURE, window=[int(x) for x in args.window.split('x')], gui_scale=args.gui_scale,
                       lang=args.lang, fov=args.fov)
    run.current_lang = args.lang
    channels = {}
    names = []
    session = None
    records = []
    failure = None
    try:
        if args.group == 'solo':
            t = time.time()
            channels[args.client] = start_client(run, args.client, run.capture)
            names.append(args.client)
            hello = channels[args.client].hello(args.timeout)
            run.mark('client_start_to_executor_s', t)
            run.hello[args.client] = hello
            t = time.time()
            saves = common.CLIENTS / args.client / 'saves' / args.world
            op = 'openworld' if saves.is_dir() else 'newworld'
            opened = channels[args.client].send(dict(op=op, world=args.world))
            run.mark('%s_s' % op, t)
            if opened.get('status') != 'ok':
                raise StepFailed(opened)
            run.world = dict(name=args.world, op=op)
            records = run_scenarios(run, modules, channels)
        else:
            import rcon as rcon_tool
            t = time.time()
            argv = ['start', '--tag', args.tag]
            for name in args.players:
                argv += ['--op', name]
            if tool('server.py', *argv) != 0:
                raise ClientGone('server.py start failed')
            session = args.tag
            run.mark('server_start_s', t)
            for name in args.players:
                names.append(name)
                run.timings['client_%s_join_s' % name] = join(run, name, channels)
            run.world = dict(name=common.WORLD_PREFIX + args.tag, op='server')
            records = run_scenarios(run, modules, channels, rcon=lambda: rcon_tool.connect())
    except (ClientGone, StepFailed) as e:
        failure = str(e)
        print('RUN FAILED: ' + failure)
    finally:
        t = time.time()
        for name in names:
            stop_client(name, channels.get(name))
            log = common.CLIENTS / name / 'logs' / 'latest.log'
            if log.is_file():
                (run.dir / name).mkdir(parents=True, exist_ok=True)
                (run.dir / name / 'client-latest.log').write_bytes(log.read_bytes())
        run.mark('clients_stop_s', t)
        if session:
            t = time.time()
            stopped = tool('server.py', 'stop')
            deleted = tool('server.py', 'delete-world', '--tag', session) if stopped == 0 else None
            run.mark('server_stop_s', t)
            if stopped != 0 or deleted != 0:
                failure = (failure + '; ' if failure else '') + 'server.py stop exit %s, delete-world exit %s' % (stopped, deleted)
    done = {r['ref'] for r in records}
    for module in modules:
        if module.REF not in done:
            records.append(dict(ref=module.REF, id=module.SCENARIO['id'], feature=module.SCENARIO['feature'],
                                title=module.SCENARIO.get('title', ''), capture=module.SCENARIO.get('capture', {}),
                                station=bool(module.SCENARIO.get('station')), error=failure or 'not reached',
                                started=None, duration_s=0,
                                expectations=[dict(e, verdict='not-run', detail=failure or 'not reached', evidence=[])
                                              for e in expectation_list(module)]))
    steps = [r for c in channels.values() for r in c.log]
    data = dict(run=run.dir.name, group=args.group, started=run.started, ended=time.time(),
                total_s=round(time.time() - run.started, 2), capture=run.capture, world=getattr(run, 'world', None),
                clients=names, hello=run.hello, timings=dict(run.timings, server_restarts_s=run.restarts), failure=failure,
                step_stats=step_stats(steps), rcon=run.rcon_log, scenarios=records)
    common.write_json(run.dir / 'results.json', data)
    common.write_json(run.dir / 'steps.json', steps)
    write_report(run.dir)
    print('results: %s' % common.rel(run.dir / 'results.md'))
    return 1 if failure else 0


def step_stats(steps):
    by_op = {}
    for s in steps:
        by_op.setdefault(s.get('op', '?'), []).append(s)
    out = {}
    for op, items in sorted(by_op.items()):
        ms = [i.get('duration_ms', 0) for i in items]
        wall = [i.get('wall_ms', 0) for i in items]
        out[op] = dict(count=len(items), failed=sum(1 for i in items if i.get('status') != 'ok'),
                       mean_ms=round(statistics.mean(ms), 1), max_ms=max(ms),
                       wall_mean_ms=round(statistics.mean(wall), 1), wall_max_ms=max(wall))
    return out


# ---------------------------------------------------------------- report and judgments

def effective(e, judgments):
    j = judgments.get(e['id'])
    return (j['verdict'], j) if j else (e['verdict'], None)


def write_report(directory):
    directory = Path(directory)
    data = common.read_json(directory / 'results.json')
    judgments = common.read_json(directory / 'judgments.json', {})
    lines = ['# Acceptance run %s' % data['run'], '',
             'Group `%s`, clients %s, world `%s`; total %.1f s; capture %s.' % (
                 data['group'], ', '.join(data['clients']) or '-', (data.get('world') or {}).get('name'), data['total_s'],
                 json.dumps(data['capture'], ensure_ascii=False)), '']
    if data.get('failure'):
        lines += ['**Run failure:** %s' % data['failure'], '']
    lines += ['| Timing | s |', '| --- | --- |'] + ['| %s | %s |' % (k, v) for k, v in data['timings'].items()] + ['']
    lines += ['| Step | count | failed | mean ms | max ms | wall mean ms | wall max ms |', '| --- | --- | --- | --- | --- | --- | --- |']
    for op, s in data['step_stats'].items():
        lines.append('| %s | %d | %d | %s | %s | %s | %s |' % (op, s['count'], s['failed'], s['mean_ms'], s['max_ms'], s['wall_mean_ms'], s['wall_max_ms']))
    lines.append('')
    for sc in data['scenarios']:
        counts = {}
        for e in sc['expectations']:
            v, _ = effective(e, judgments)
            counts[v] = counts.get(v, 0) + 1
        lines += ['## %s (`%s`, %.1f s)' % (sc['title'] or sc['id'], sc['ref'], sc['duration_s']), '',
                  ' '.join('%s %d' % (VERDICT_ZH[k], counts.get(k, 0)) for k in VERDICTS)]
        if sc.get('error'):
            lines.append('Scenario stopped: %s' % sc['error'])
        lines += ['', '| ID | Expectation | Verdict | Detail | Evidence |', '| --- | --- | --- | --- | --- |']
        for e in sc['expectations']:
            v, j = effective(e, judgments)
            detail = e.get('detail') or ''
            if j:
                detail = 'reviewer: %s (machine: %s %s)' % (j.get('note', ''), VERDICT_ZH[e['verdict']], e.get('detail') or '')
            lines.append('| %s | %s | %s | %s | %s |' % (e['id'], e.get('text', '').replace('|', '/'), VERDICT_ZH[v],
                                                         str(detail).replace('|', '/').replace('\n', ' '),
                                                         ', '.join(e.get('evidence', []))))
        lines.append('')
    (directory / 'results.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def cmd_judge(args):
    directory = common.resolve(args.run_dir)
    data = common.read_json(directory / 'results.json')
    ids = {e['id']: e for sc in data['scenarios'] for e in sc['expectations']}
    if args.id not in ids:
        raise SystemExit('no expectation %s in this run' % args.id)
    if args.verdict not in ('pass', 'fail', 'not-run'):
        raise SystemExit('--verdict pass, fail or not-run')
    if not args.note.strip():
        raise SystemExit('--note is required: say what the verdict rests on')
    judgments = common.read_json(directory / 'judgments.json', {})
    judgments[args.id] = dict(verdict=args.verdict, note=args.note, by=args.by, time=common.now_tag(),
                              machine=ids[args.id]['verdict'])
    common.write_json(directory / 'judgments.json', judgments)
    write_report(directory)
    return 0


def cmd_report(args):
    write_report(common.resolve(args.run_dir))
    return 0


def cmd_list(args):
    for path in scenario_files():
        ref = '%s/%s' % (path.parent.name, path.stem)
        module = load(ref)
        print('%-40s %-6s %4d expectations  %s' % (ref, module.SCENARIO.get('group', 'solo'), len(expectation_list(module)),
                                                   module.SCENARIO.get('title', '')))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    sub.add_parser('list').set_defaults(func=cmd_list)
    p = sub.add_parser('run')
    p.add_argument('scenarios', nargs='+', help='<feature>/<name>')
    p.add_argument('--run', required=True, help='run name (directory under build/migration/acceptance-runs)')
    p.add_argument('--out', help='run directory instead of build/migration/acceptance-runs/<run>')
    p.add_argument('--group', choices=('solo', 'mp'), default='solo')
    p.add_argument('--client', default='g31e_solo', help='solo client name (its game directory under clients/)')
    p.add_argument('--world', default=common.WORLD_PREFIX + 'g31e-solo', help='solo world name')
    p.add_argument('--tag', default='g31e-mp', help='mp: server world tag')
    p.add_argument('--players', nargs=2, default=['g31e_a', 'g31e_b'], help='mp: two client names')
    p.add_argument('--argv', default='build/migration/accept-goal29/client-argv-g31e.json', help='captured client command line')
    p.add_argument('--window', default='854x480')
    p.add_argument('--gui-scale', type=int, default=2)
    p.add_argument('--lang', default='zh_cn')
    p.add_argument('--scenario-lang', help='language for every scenario, in place of each scenario\'s own (e.g. en_us for the English pass)')
    p.add_argument('--fov', type=int, default=70)
    p.add_argument('--option', action='append', default=[], help='extra options.txt key:value for the clients')
    p.add_argument('--timeout', type=int, default=600)
    p.set_defaults(func=cmd_run)
    p = sub.add_parser('judge')
    p.add_argument('run_dir')
    p.add_argument('id')
    p.add_argument('--verdict', required=True)
    p.add_argument('--note', default='')
    p.add_argument('--by', default='agent')
    p.set_defaults(func=cmd_judge)
    p = sub.add_parser('report')
    p.add_argument('run_dir')
    p.set_defaults(func=cmd_report)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
