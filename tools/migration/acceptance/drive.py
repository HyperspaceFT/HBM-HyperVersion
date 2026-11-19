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
FEATURE_ID = re.compile(r'[a-z0-9][a-z0-9-]*')
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


# Command replies over RCON are the dedicated server's English (the `cmd` step has its own list for chat replies).
REJECTED_REPLY = re.compile(r'Unknown or incomplete command|Incorrect argument|Unknown command|<--\[HERE\]|No player was found|'
                            r'No entity was found|Could not set the block|You do not have permission|is not a valid|not loaded|'
                            r'is not a block entity')


def parse_rcon_state(tick_query, time_query):
    """State of a dedicated server from the English replies of `tick query` and `time query gametime`."""
    m = re.search(r'(\d+)\s*$', (time_query or '').strip())
    if not m:
        raise StepFailed(dict(op='rcon', reason='no game time in %r' % (time_query or '')[:120]))
    text = (tick_query or '').lower()
    ms = re.search(r'([\d.]+)\s*ms', text)
    return dict(game_time=int(m.group(1)), sprinting='sprinting' in text, frozen='frozen' in text,
                mean_tick_ms=float(ms.group(1)) if ms else None)


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

    def server(self, command=None, allow_error=False, client=None):
        """Server-side data, never the client's copy: in a single-player run the executor's `server` step runs `command`
        (if any) on the integrated server's thread and reads its tick state there; with a dedicated server the command
        goes over RCON and the state is read with `tick query` and `time query gametime`. Returns
        dict(messages, result, game_time, sprinting, frozen); `result` is the command's result value (single player only,
        None over RCON)."""
        if self._rcon is None:
            fields = dict(command=command, allow_error=allow_error) if command else {}
            r = self.step('server', client=client, **fields)
            return dict(messages=r.get('messages', []), result=r.get('result'), game_time=r['game_time'],
                        sprinting=r['sprinting'], frozen=r['frozen'], mean_tick_ms=r.get('mean_tick_ms'))
        replies = self.rcon(*([command] if command else []), 'tick query', 'time query gametime')
        out = dict(messages=[replies[0]] if command else [], result=None)
        out.update(parse_rcon_state(replies[-2], replies[-1]))
        if command and not allow_error and REJECTED_REPLY.search(replies[0] or ''):
            raise StepFailed(dict(op='rcon', reason='command rejected: %s' % replies[0][:160]))
        return out

    def sprint(self, ticks, until=None, poll_s=1.0, timeout_s=900, label=None, client=None):
        """Runs `ticks` server ticks as fast as the server can (`/tick sprint`, permission 3: the integrated server's own
        source in single player, RCON on a dedicated server) and returns when the server reports the sprint over, read from
        server state, not from client ticks (the client keeps its 20 ticks a second and does not follow a sprint).
        `until(ctx)` is checked after every poll; when it holds the sprint is stopped early. The wall-clock `timeout_s`
        stops the sprint and fails the scenario. Returns and records (results.json "sprints") the requested and the
        advanced game ticks, the wall time, the ticks per second and every poll's reply time."""
        before = self.server(client=client)
        polls = []
        started = time.time()
        self.server('tick sprint %d' % int(ticks), client=client)
        state = before
        try:
            while True:
                time.sleep(poll_s)
                t = time.time()
                state = self.server(client=client)
                polls.append(dict(at_s=round(t - started, 2), reply_ms=round((time.time() - t) * 1000), game_time=state['game_time'],
                                  sprinting=state['sprinting']))
                if not state['sprinting']:
                    break
                if until is not None and until(self):
                    self.server('tick sprint stop', client=client)
                    state = self.server(client=client)
                    break
                if time.time() - started > timeout_s:
                    self.server('tick sprint stop', client=client)
                    state = self.server(client=client)
                    record = self._record_sprint(label, ticks, before, state, started, polls, timed_out=True)
                    # it may have ended between the last poll and the stop: from a frozen world that is more than `ticks`
                    if not (before['frozen'] and record['advanced'] > int(ticks)):
                        raise StepFailed(dict(op='sprint', reason='sprint of %d ticks not over after %d s (advanced %d)'
                                              % (ticks, timeout_s, record['advanced'])))
                    return record
        except BaseException as e:
            if not isinstance(e, StepFailed) or e.result.get('op') != 'sprint':
                # whatever failed, the server must not go on sprinting into the next scenario or the stop
                try:
                    self.server('tick sprint stop', allow_error=True, client=client)
                except Exception:
                    pass
                self.run.sprints.append(dict(scenario=self.meta['id'], label=label, requested=int(ticks), error=repr(e)[:200],
                                             wall_s=round(time.time() - started, 2), polls=len(polls)))
            raise
        return self._record_sprint(label, ticks, before, state, started, polls, timed_out=False)

    def _record_sprint(self, label, ticks, before, after, started, polls, timed_out):
        """The wall time runs to the poll that saw the sprint over, so ticks_per_s is low by up to one poll interval;
        advanced counts every game tick between the reads before and after (from a frozen world, the sprint's alone)."""
        wall = time.time() - started
        advanced = after['game_time'] - before['game_time']
        record = dict(scenario=self.meta['id'], label=label, requested=int(ticks), advanced=advanced, wall_s=round(wall, 2),
                      ticks_per_s=round(advanced / wall, 1) if wall > 0 else None, stopped_early=advanced < int(ticks),
                      timed_out=timed_out, frozen_before=before['frozen'], frozen_after=after['frozen'],
                      poll_reply_ms_max=max((p['reply_ms'] for p in polls), default=None), polls=len(polls))
        self.run.sprints.append(record)
        return record

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
    extra = meta.get('features', [])
    if not isinstance(extra, (list, tuple)) or not all(isinstance(f, str) and FEATURE_ID.fullmatch(f) for f in extra):
        raise SystemExit('%s: SCENARIO features must be a list of feature ids' % ref)
    module.REF = ref
    return module


def features_of(module):
    """The scenario's feature (its directory) and the optional SCENARIO["features"]: a stage scenario that runs a line across
    several features registers expectations under each of them."""
    meta = module.SCENARIO
    return [meta['feature']] + [f for f in meta.get('features', []) if f != meta['feature']]


def expectation_list(module):
    items = module.expectations()
    ids = [e['id'] for e in items]
    if len(ids) != len(set(ids)):
        raise SystemExit('%s: duplicate expectation ids' % module.REF)
    prefixes = tuple(f + '.' for f in features_of(module))
    bad = [i for i in ids if not i.startswith(prefixes)]
    if bad:
        raise SystemExit('%s: expectation ids must start with one of %s: %s' % (module.REF, ', '.join(prefixes), bad[:3]))
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
        self.sprints = []
        self.records = []
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
    """Runs the scenarios in order; each finished scenario's record goes into run.records at once, so a client that dies
    later in the run does not take the verdicts already reached with it."""
    records = run.records
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
                if error:
                    # a scenario that ended early may have left the client in another language; the next one sets its own
                    run.current_lang = None
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
        records.append(dict(ref=module.REF, id=meta['id'], feature=meta['feature'], features=features_of(module), title=meta.get('title', ''),
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
    records = run.records
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
            spec = dict(op=op, world=args.world)
            if op == 'newworld':
                spec.update(world_settings(args))
            elif world_settings(args):
                raise StepFailed(dict(op='openworld', reason='world settings given, but %s exists: settings only apply to a new world' % args.world))
            opened = channels[args.client].send(spec)
            run.mark('%s_s' % op, t)
            if opened.get('status') != 'ok':
                raise StepFailed(opened)
            run.world = dict(name=args.world, op=op, **{k: opened[k] for k in WORLD_KEYS if k in opened})
            run_scenarios(run, modules, channels)
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
            run_scenarios(run, modules, channels, rcon=lambda: rcon_tool.connect())
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
            records.append(dict(ref=module.REF, id=module.SCENARIO['id'], feature=module.SCENARIO['feature'], features=features_of(module),
                                title=module.SCENARIO.get('title', ''), capture=module.SCENARIO.get('capture', {}),
                                station=bool(module.SCENARIO.get('station')), error=failure or 'not reached',
                                started=None, duration_s=0,
                                expectations=[dict(e, verdict='not-run', detail=failure or 'not reached', evidence=[])
                                              for e in expectation_list(module)]))
    steps = [r for c in channels.values() for r in c.log]
    data = dict(run=run.dir.name, group=args.group, started=run.started, ended=time.time(),
                total_s=round(time.time() - run.started, 2), capture=run.capture, world=getattr(run, 'world', None),
                clients=names, hello=run.hello, timings=dict(run.timings, server_restarts_s=run.restarts), failure=failure,
                step_stats=step_stats(steps), rcon=run.rcon_log, sprints=run.sprints, scenarios=records)
    common.write_json(run.dir / 'results.json', data)
    common.write_json(run.dir / 'steps.json', steps)
    write_report(run.dir)
    print('results: %s' % common.rel(run.dir / 'results.md'))
    return 1 if failure else 0


WORLD_KEYS = ('gamemode', 'difficulty', 'cheats', 'seed', 'preset')


def world_settings(args):
    """The newworld fields given on the command line; none given keeps the executor's defaults (creative, peaceful,
    commands on, seed 31, flat), which every scenario written before these options assumes."""
    out = {}
    for key in ('gamemode', 'difficulty', 'seed', 'preset'):
        if getattr(args, key, None) is not None:
            out[key] = getattr(args, key)
    if getattr(args, 'no_cheats', False):
        out['cheats'] = False
    return out


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
    p.add_argument('--client', default='solo', help='solo client name (its game directory under clients/)')
    p.add_argument('--world', default=common.WORLD_PREFIX + 'solo', help='solo world name')
    p.add_argument('--tag', default='mp', help='mp: server world tag')
    p.add_argument('--players', nargs=2, default=['acc_a', 'acc_b'], help='mp: two client names')
    p.add_argument('--argv', default='build/migration/accept/client-argv.json', help='captured client command line')
    p.add_argument('--window', default='854x480')
    p.add_argument('--gui-scale', type=int, default=2)
    p.add_argument('--lang', default='zh_cn')
    p.add_argument('--scenario-lang', help='language for every scenario, in place of each scenario\'s own (e.g. en_us for the English pass)')
    p.add_argument('--fov', type=int, default=70)
    p.add_argument('--option', action='append', default=[], help='extra options.txt key:value for the clients')
    p.add_argument('--timeout', type=int, default=600)
    p.add_argument('--gamemode', choices=('survival', 'creative', 'adventure', 'spectator'), help='solo: game mode of a new world (default creative)')
    p.add_argument('--difficulty', choices=('peaceful', 'easy', 'normal', 'hard'), help='solo: difficulty of a new world (default peaceful)')
    p.add_argument('--seed', type=int, help='solo: seed of a new world (default 31)')
    p.add_argument('--preset', choices=('flat', 'normal'), help='solo: flat or the default terrain for a new world (default flat)')
    p.add_argument('--no-cheats', action='store_true', help='solo: a new world without commands (scenarios that send commands fail)')
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
