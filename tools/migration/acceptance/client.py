#!/usr/bin/env python3
"""Dev clients for Goal 29 acceptance, each with its own game directory and offline name. Never drives the window.

Run from the NEO root:
  python3 -B -X utf8 tools/migration/acceptance/client.py capture
  python3 -B -X utf8 tools/migration/acceptance/client.py start alice --server 127.0.0.1:25565 --wait-join
  python3 -B -X utf8 tools/migration/acceptance/client.py start solo --world MyWorld --lang zh_cn
  python3 -B -X utf8 tools/migration/acceptance/client.py stop alice
  python3 -B -X utf8 tools/migration/acceptance/client.py status | clean alice

capture  starts `tools/migration/build.sh --offline runClient` once, reads the client JVM's full command line with
         `ps -ww -o args=` (java, -Dfml.modFolders, @build/moddev/clientRunVmArgs.txt, -cp <classpath>,
         net.neoforged.devlaunch.Main, @build/moddev/clientRunProgramArgs.txt), saves it to
         build/migration/accept-goal29/client-cmdline.txt (and the split argv to client-argv.json), then ends that
         client with TERM. It writes run/options.txt and run/logs like any runClient,
         so it refuses to run unless server.py has a session open (whose stop restores run/).
start    launches java with the captured argv directly, the program-argument file swapped for
         clients/<name>/program-args.txt: a copy with --gameDir build/migration/accept-goal29/clients/<name> (own
         logs/latest.log, options.txt, saves; also the working directory), --username <name>, and
         --quickPlayMultiplayer host:port or --quickPlaySingleplayer <world> (client Main.java:66-69); without
         either it stops at the title screen. Quick-play singleplayer only opens an existing world of that client
         (QuickPlay.joinSingleplayerWorld shows an error otherwise): create the world in the game first. options.txt is
         preset with pauseOnLostFocus:false and onboardAccessibility:false (without the latter the first start sits on
         the accessibility screen) plus --lang/--option values. --xmx caps the heap (default 2G, two clients and a server
         share 16 GB).
stop     kicks the player over RCON when a server session exists (the client drops back to a menu), then TERMs the JVM
         and records its exit code in clients/<name>/client.json.
"""
import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

CMDLINE = common.STATE / 'client-cmdline.txt'
ARGV = common.STATE / 'client-argv.json'
DATA_VERSION = '3955'  # Minecraft 1.21.1; options.txt without "version" would be run through the data fixers as version 0
BASE_OPTIONS = dict(version=DATA_VERSION, pauseOnLostFocus='false', onboardAccessibility='false',
                    skipMultiplayerWarning='true', joinedFirstServer='true', tutorialStep='none')


VM_ARGS = '@' + str(common.REPO / 'build' / 'moddev' / 'clientRunVmArgs.txt')
PROGRAM_ARGS = '@' + str(common.REPO / 'build' / 'moddev' / 'clientRunProgramArgs.txt')


def client_jvms():
    """ModDevGradle starts the client as `java ... @clientRunVmArgs.txt ... net.neoforged.devlaunch.Main
    @clientRunProgramArgs.txt`; the launch target and --gameDir live in those files, not on the command line."""
    out = subprocess.run(['ps', '-ww', '-axo', 'pid=,args='], capture_output=True, text=True).stdout
    found = []
    for line in out.splitlines():
        pid, _, args = line.strip().partition(' ')
        words = args.split(' ')
        # The java process itself; the wrapper shell of `start` carries the same argv after "sh -c ..." and must not
        # be TERMed, or it cannot record the exit code.
        if words[0].endswith('/java') and VM_ARGS in words:
            found.append((int(pid), args))
    return found


def program_args(source, home, name, quick):
    """The run's program-argument file (one argument per line, "#" comments; DevLaunch reads the main class from its
    first line) with --gameDir pointed at the client directory, plus --username and the quick-play arguments."""
    lines = Path(source).read_text(encoding='utf-8').splitlines()
    i = lines.index('--gameDir')
    lines[i + 1] = str(home)
    if '--username' in lines:
        lines[lines.index('--username') + 1] = name
    else:
        lines += ['--username', name]
    return '\n'.join(lines + list(quick)) + '\n'


def name_ok(name):
    if not re.fullmatch(r'[A-Za-z0-9_]{3,16}', name):
        raise SystemExit('player name: 3-16 letters, digits or "_"')
    return name


def write_options(path, values):
    current = {}
    order = []
    if path.is_file():
        for line in path.read_text(encoding='utf-8').splitlines():
            key, sep, value = line.partition(':')
            if sep:
                current[key] = value
                order.append(key)
    for key, value in values.items():
        if key not in current:
            order.append(key)
        current[key] = value
    path.write_text(''.join('%s:%s\n' % (k, current[k]) for k in order), encoding='utf-8')


def cmd_capture(args):
    session = common.read_json(common.SESSION)
    if not args.without_session and (not session or Path(session['run']).resolve() != (common.REPO / 'run').resolve()):
        raise SystemExit('capture writes run/options.txt, run/logs and run/config of this checkout; start server.py here '
                         'first (not with --root) so its stop restores run/.')
    if client_jvms():
        raise SystemExit('A dev client from this checkout is already running.')
    logs = common.STATE / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    stamp = common.now_tag()
    log = logs / ('capture-runClient-%s.log' % stamp)
    with open(log, 'wb') as out:
        gradle = subprocess.Popen(['sh', str(common.BUILD_SH), '--offline', 'runClient'], cwd=common.REPO, stdout=out,
                                  stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
    print('runClient pid=%d log=%s' % (gradle.pid, common.rel(log)))
    found = []
    try:
        end = time.time() + args.timeout
        while time.time() < end and not found and gradle.poll() is None:
            time.sleep(2)
            found = client_jvms()
        if not found:
            raise SystemExit('No client JVM appeared; see ' + common.rel(log))
        pid, _ = found[0]
        raw = subprocess.run(['ps', '-ww', '-o', 'args=', '-p', str(pid)], capture_output=True, text=True).stdout.strip()
        cwd = subprocess.run(['lsof', '-a', '-p', str(pid), '-d', 'cwd', '-Fn'], capture_output=True, text=True).stdout
        cwd = [l[1:] for l in cwd.splitlines() if l.startswith('n')]
        argv = raw.split(' ')
        # ps joins argv with single spaces; the split is exact only if no argument contains a space. Check the paths.
        problems = [a for a in argv if a.startswith('/') and ':' not in a and not Path(a).exists()]
        if not Path(argv[0]).is_file() or problems or VM_ARGS not in argv or PROGRAM_ARGS not in argv:
            raise SystemExit('captured command line does not split cleanly or lacks the run argument files: ' + repr(problems[:3]))
        if args.wait_title:
            title = wait_log(common.REPO / 'run' / 'logs' / 'latest.log', re.compile(r'Sound engine started|Loaded \d+ advancements'), args.timeout)
            print('client reached: %s' % (title or 'timeout'))
        CMDLINE.write_text(raw + '\n', encoding='utf-8')
        common.write_json(ARGV, dict(argv=argv, captured=stamp, pid=pid, cwd=cwd[0] if cwd else None,
                                     note='ps -ww -o args= of the runClient JVM; split on single spaces (no argument has one)'))
        print('captured %d arguments to %s' % (len(argv), common.rel(CMDLINE)))
    finally:
        # Whatever happened, end this runClient: its client JVM, then Gradle itself if it is still waiting.
        for pid, _ in client_jvms():
            os.kill(pid, signal.SIGTERM)
        try:
            code = gradle.wait(timeout=180)
        except subprocess.TimeoutExpired:
            os.killpg(gradle.pid, signal.SIGTERM)
            code = gradle.wait(timeout=60)
        print('runClient ended by TERM, Gradle exit %s' % code)
    return 0


def wait_log(path, pattern, timeout):
    end = time.time() + timeout
    while time.time() < end:
        if Path(path).is_file():
            match = pattern.search(Path(path).read_text(encoding='utf-8', errors='replace'))
            if match:
                return match.group(0)
        time.sleep(2)
    return None


def wait_listed(name, timeout):
    import rcon
    end = time.time() + timeout
    while time.time() < end:
        time.sleep(3)
        try:
            client = rcon.connect(timeout=10)
            try:
                reply = client.command('list')
            finally:
                client.close()
        except (OSError, PermissionError):
            continue
        players = reply.split(':', 1)[1] if ':' in reply else ''
        if name in [p.strip() for p in players.split(',')]:
            return 'listed by the server: ' + reply
    return None


def cmd_start(args):
    name = name_ok(args.name)
    captured = common.read_json(ARGV)
    if not captured:
        raise SystemExit('Run `client.py capture` first.')
    if args.server and args.world:
        raise SystemExit('give at most one of --server HOST:PORT or --world NAME')
    if args.server and not args.server.startswith(common.LOOPBACK + ':'):
        raise SystemExit('--server must be 127.0.0.1:<port>')
    home = common.CLIENTS / name
    record = common.read_json(home / 'client.json')
    if jvm_of(name):
        raise SystemExit('%s is already running' % name)
    home.mkdir(parents=True, exist_ok=True)
    options = dict(BASE_OPTIONS, lang=args.lang)
    if args.mute:
        options['soundCategory_master'] = '0.0'
    if args.render_distance:
        options['renderDistance'] = str(args.render_distance)
    for item in args.option:
        key, sep, value = item.partition(':')
        if not sep:
            raise SystemExit('--option needs key:value')
        options[key] = value
    write_options(home / 'options.txt', options)

    argv = list(captured['argv'])
    quick = (['--quickPlayMultiplayer', args.server] if args.server else
             ['--quickPlaySingleplayer', args.world] if args.world else [])
    own = home / 'program-args.txt'
    own.write_text(program_args(PROGRAM_ARGS[1:], home, name, quick), encoding='utf-8')
    argv[argv.index(PROGRAM_ARGS)] = '@' + str(own)
    if not any(a.startswith('-Xmx') for a in argv):
        argv.insert(1, '-Xmx' + args.xmx)
    exit_file = home / 'exit-code.txt'
    if exit_file.exists():
        exit_file.unlink()
    with open(home / 'stdout.log', 'wb') as out:
        proc = subprocess.Popen(['/bin/sh', '-c', '"$@"; echo "$?" > exit-code.txt', 'sh', *argv], cwd=home, stdout=out,
                                stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
    record = dict(name=name, pid=proc.pid, started=common.now_tag(), lang=args.lang, server=args.server, world=args.world,
                  home=str(home), log=str(home / 'logs' / 'latest.log'))
    common.write_json(home / 'client.json', record)
    print('started %s pid=%d dir=%s' % (name, proc.pid, common.rel(home)))
    if args.wait_join:
        if args.server:
            # The joining client does not log its own "joined the game"; ask the server instead.
            hit = wait_listed(name, args.timeout)
        elif not args.world:
            raise SystemExit('--wait-join needs --server or --world')
        else:
            hit = wait_log(home / 'logs' / 'latest.log', re.compile(r'\[CHAT\] .*|Loaded \d+ advancements'), args.timeout)
        print('%s: %s' % (name, hit or 'not joined within %ds' % args.timeout))
        record['joined'] = hit
        common.write_json(home / 'client.json', record)
        return 0 if hit else 1
    return 0


def jvm_of(name):
    """This client's JVM: a dev client whose command line names clients/<name>/program-args.txt. Matching the command
    line (not the recorded shell pid's children) keeps a reused pid from directing TERM at another process."""
    own = '@' + str(common.CLIENTS / name / 'program-args.txt')
    return [pid for pid, args in client_jvms() if own in args.split(' ')]


def cmd_stop(args):
    name = name_ok(args.name)
    home = common.CLIENTS / name
    record = common.read_json(home / 'client.json')
    if not record or not jvm_of(name):
        raise SystemExit('%s is not running' % name)
    steps = []
    if common.read_json(common.SESSION) and not args.no_kick:
        import rcon
        client = rcon.connect()
        try:
            steps.append('kick: ' + client.command('kick %s acceptance stop' % name))
        finally:
            client.close()
        hit = wait_log(home / 'logs' / 'latest.log', re.compile(r'acceptance stop|Disconnected|lost connection', re.I), 30)
        steps.append('client log after kick: %s' % hit)
    for pid in jvm_of(name):
        os.kill(pid, signal.SIGTERM)
    end = time.time() + args.timeout
    while time.time() < end and (jvm_of(name) or not (home / 'exit-code.txt').is_file()):
        time.sleep(1)
    code = (home / 'exit-code.txt').read_text().strip() if (home / 'exit-code.txt').is_file() else None
    record.update(stopped=common.now_tag(), stop_steps=steps, exit_code=code, alive_after=bool(jvm_of(name)))
    common.write_json(home / 'client.json', record)
    for step in steps:
        print(step)
    print('%s stopped by TERM; exit code %s' % (name, code))
    return 0 if code is not None else 1


def cmd_status(args):
    if CMDLINE.is_file():
        print('captured command line: %s' % common.rel(CMDLINE))
    if common.CLIENTS.is_dir():
        for home in sorted(common.CLIENTS.iterdir()):
            record = common.read_json(home / 'client.json') or {}
            print('%-16s pid=%s alive=%s joined=%s exit=%s' % (home.name, record.get('pid'), bool(jvm_of(home.name)),
                                                         bool(record.get('joined')), record.get('exit_code')))
    return 0


def cmd_clean(args):
    name = name_ok(args.name)
    home = common.CLIENTS / name
    record = common.read_json(home / 'client.json')
    if jvm_of(name):
        raise SystemExit('%s is still running' % name)
    if home.is_symlink() or not home.is_dir() or home.parent.resolve() != common.CLIENTS.resolve():
        raise SystemExit('refusing: %s is not a client directory' % home)
    shutil.rmtree(home)
    print('removed ' + common.rel(home))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    p = sub.add_parser('capture')
    p.add_argument('--timeout', type=int, default=900)
    p.add_argument('--wait-title', action='store_true', help='wait for the client to finish loading before TERM')
    p.add_argument('--without-session', action='store_true', help='allow capture without a server session (run/ is not restored)')
    p.set_defaults(func=cmd_capture)
    p = sub.add_parser('start')
    p.add_argument('name')
    p.add_argument('--server')
    p.add_argument('--world')
    p.add_argument('--lang', default='en_us')
    p.add_argument('--mute', action='store_true')
    p.add_argument('--render-distance', type=int)
    p.add_argument('--option', action='append', default=[], help='extra options.txt key:value; repeatable (key rebinds too)')
    p.add_argument('--xmx', default='2G')
    p.add_argument('--wait-join', action='store_true')
    p.add_argument('--timeout', type=int, default=600)
    p.set_defaults(func=cmd_start)
    p = sub.add_parser('stop')
    p.add_argument('name')
    p.add_argument('--no-kick', action='store_true')
    p.add_argument('--timeout', type=int, default=60)
    p.set_defaults(func=cmd_stop)
    sub.add_parser('status').set_defaults(func=cmd_status)
    p = sub.add_parser('clean')
    p.add_argument('name')
    p.set_defaults(func=cmd_clean)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
