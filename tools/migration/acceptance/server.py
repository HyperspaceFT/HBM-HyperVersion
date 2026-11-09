#!/usr/bin/env python3
"""Disposable loopback dedicated server for Goal 29 acceptance (offline runServer, RCON, flat world).

Run from the NEO root:
  python3 -B -X utf8 tools/migration/acceptance/server.py start --tag smoke --op alice --op bob
  python3 -B -X utf8 tools/migration/acceptance/server.py status
  python3 -B -X utf8 tools/migration/acceptance/server.py stop
  python3 -B -X utf8 tools/migration/acceptance/server.py delete-world --tag smoke

start  backs up the files under <root>/run that a run changes (server.properties, ops.json, usercache.json,
       usernamecache.json, options.txt, eula.txt and every file under config/ and defaultconfigs/; a file that does
       not exist is recorded as absent) to build/migration/accept-goal29/backup-<time>/, writes a one-off
       server.properties (server-ip=127.0.0.1, online-mode=false, world accept-goal29-<tag>, flat unless
       --world-type normal (world-generation checks), peaceful (slimes kill
       a survival player on a flat world; `difficulty` over RCON changes it), RCON on with a random
       password stored only in build/migration/accept-goal29/rcon.password) and ops.json (offline UUIDs), starts
       `tools/migration/build.sh --offline runServer` in the background with its output in
       build/migration/accept-goal29/logs/server-<tag>-<time>.log, and waits for "Done" and "RCON running on
       127.0.0.1:<port>" (anything else: it stops the server and restores run/). That Gradle-output log is the
       server's evidence: any other run in the same run/ (a capture's runClient, a GameTest server) rotates
       run/logs/latest.log away from the running server.
stop   sends `stop` over RCON (Gradle does not pass stdin to runServer, and TERM ends it with exit 143 and BUILD
       FAILED), waits for Gradle to finish, keeps a copy of run/logs/latest.log, then restores every backed-up file
       byte for byte, removes files that were absent at backup time and new files under config/ and defaultconfigs/,
       and checks the hashes (a mismatch keeps the session for `restore`). --force TERMs the server JVM when RCON does
       not answer or the server does not exit. Other files a run creates under run/ (logs/, downloads/, crash-reports/,
       and banned-*.json or whitelist.json when absent) are not restored; `start` refuses while any run of the checkout
       (client, server, GameTest, data) is using run/.
restart stops the server over RCON and starts it again on the same world without restoring run/ in between: edit
       run/config files during a session, then restart, and the final stop still restores the start state.
restore repeats the restore of the last session (after a crash of this tool, or when a restore reported mismatches).
delete-world removes <root>/run/accept-goal29-<tag> only when this tool created it (worlds.json) and no server runs.
start --from-world DIR copies an existing world (for example build/migration/accept-goal29/old-world) in as the
       session's world, so the kept original is never written.

--root runs another checkout (the old-version tree under build/migration/accept-goal29/); its Gradle uses this
repository's .gradle/user-home. EULA: NeoForge's dev runs agree automatically (Eula.java:20, IS_RUNNING_IN_IDE), so
no eula.txt is written. No network beyond 127.0.0.1, no download, no real world.
"""
import argparse
import os
import re
import secrets
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

BACKUP_FILES = ('server.properties', 'ops.json', 'usercache.json', 'usernamecache.json', 'options.txt', 'eula.txt')
BACKUP_TREES = ('config', 'defaultconfigs')
DONE = re.compile(r'\]: Done \([0-9.,]+s\)!')
FLAT_PRESET = ('{"layers":[{"block":"minecraft:bedrock","height":1},{"block":"minecraft:dirt","height":2},'
               '{"block":"minecraft:grass_block","height":1}],"biome":"minecraft:plains"}')


# ---------------------------------------------------------------- backup and restore of <root>/run

def run_dir(root):
    return Path(root) / 'run'


def backup_scope(run):
    paths = list(BACKUP_FILES)
    for tree in BACKUP_TREES:
        base = run / tree
        if base.is_dir():
            paths += sorted(p.relative_to(run).as_posix() for p in base.rglob('*') if p.is_file() and not p.is_symlink())
    return paths


def backup(run, dest):
    """Copy the run files a session changes; returns {relative path: sha256 or None when absent}."""
    manifest = {}
    for name in backup_scope(run):
        src = run / name
        if src.is_file():
            target = dest / 'files' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
            manifest[name] = common.sha256(src)
            if common.sha256(target) != manifest[name]:
                raise SystemExit('backup copy differs: ' + name)
        else:
            manifest[name] = None
    common.write_json(dest / 'manifest.json', dict(run=str(run), files=manifest))
    return manifest


def restore(run, dest):
    """Put every backed-up file back, drop files that were absent, verify; returns a report dict."""
    manifest = common.read_json(dest / 'manifest.json')['files']
    restored, removed, mismatched = [], [], []
    for name, digest in sorted(manifest.items()):
        target = run / name
        if digest is None:
            if target.exists():
                target.unlink()
                removed.append(name)
            continue
        if not target.is_file() or common.sha256(target) != digest:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest / 'files' / name, target)
            restored.append(name)
    extra = []
    for tree in BACKUP_TREES:
        base = run / tree
        if base.is_dir():
            for p in sorted(base.rglob('*')):
                name = p.relative_to(run).as_posix()
                if p.is_file() and not p.is_symlink() and name not in manifest:
                    p.unlink()
                    extra.append(name)
    for name, digest in manifest.items():
        target = run / name
        if (digest is None and target.exists()) or (digest is not None and (not target.is_file() or common.sha256(target) != digest)):
            mismatched.append(name)
    report = dict(backup=common.rel(dest), checked=len(manifest), restored=restored, removed_absent=removed,
                  removed_new_config_files=extra, mismatched=mismatched, ok=not mismatched)
    common.write_json(dest / 'restore-report.json', report)
    return report


# ---------------------------------------------------------------- server.properties and ops.json

def write_properties(path, values):
    """Set keys in a Java properties file in place; other lines stay as they are."""
    lines = path.read_text(encoding='utf-8').splitlines() if path.is_file() else []
    seen = set()
    out = []
    for line in lines:
        key = line.split('=', 1)[0].strip() if '=' in line and not line.lstrip().startswith('#') else None
        if key in values:
            out.append('%s=%s' % (key, values[key]))
            seen.add(key)
        else:
            out.append(line)
    out += ['%s=%s' % (k, v) for k, v in values.items() if k not in seen]
    path.write_text('\n'.join(out) + '\n', encoding='utf-8')


def ops_entries(names):
    return [dict(uuid=common.offline_uuid(n), name=n, level=4, bypassesPlayerLimit=False) for n in names]


# ---------------------------------------------------------------- world registry

def worlds():
    return common.read_json(common.WORLDS, dict(worlds=[]))


def register_world(path, tag, status='created'):
    data = worlds()
    data['worlds'] = [w for w in data['worlds'] if w['path'] != str(path)]
    data['worlds'].append(dict(path=str(path), tag=tag, status=status, at=common.now_tag()))
    common.write_json(common.WORLDS, data)


def world_status(path):
    for w in worlds()['worlds']:
        if w['path'] == str(path):
            return w['status']
    return None


# ---------------------------------------------------------------- process helpers

def server_jvms(root):
    """PIDs of runServer JVMs started from <root>: ModDevGradle passes their arguments as
    @<root>/build/moddev/serverRunVmArgs.txt, so the launch target itself is not on the command line."""
    marker = '@' + str(Path(root) / 'build' / 'moddev' / 'serverRunVmArgs.txt')
    out = subprocess.run(['ps', '-ww', '-axo', 'pid=,args='], capture_output=True, text=True).stdout
    pids = []
    for line in out.splitlines():
        pid, _, args = line.strip().partition(' ')
        if marker in args.split(' '):
            pids.append(int(pid))
    return pids


def any_run_jvms(root):
    """PIDs of any ModDevGradle run (client, server, GameTest, data) of <root>; they all share <root>/run."""
    prefix = '@' + str(Path(root) / 'build' / 'moddev') + '/'
    out = subprocess.run(['ps', '-ww', '-axo', 'pid=,args='], capture_output=True, text=True).stdout
    pids = []
    for line in out.splitlines():
        pid, _, args = line.strip().partition(' ')
        if any(a.startswith(prefix) and a.endswith('RunVmArgs.txt') for a in args.split(' ')):
            pids.append(int(pid))
    return pids


def wait_for(predicate, timeout, step=2.0):
    end = time.time() + timeout
    while time.time() < end:
        result = predicate()
        if result:
            return result
        time.sleep(step)
    return predicate()


def tail(path, n=40):
    try:
        return '\n'.join(Path(path).read_text(encoding='utf-8', errors='replace').splitlines()[-n:])
    except OSError:
        return ''


# ---------------------------------------------------------------- commands

def cmd_start(args):
    session = common.read_json(common.SESSION)
    if session:
        raise SystemExit('A session is already recorded (%s, tag %s); stop or restore it first.' % (common.rel(common.SESSION), session['tag']))
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,40}', args.tag):
        raise SystemExit('--tag: lowercase letters, digits and "-" only')
    root = common.resolve(args.root).resolve()
    run = run_dir(root)
    build_sh = root / 'tools' / 'migration' / 'build.sh'
    if not build_sh.is_file():
        raise SystemExit('No tools/migration/build.sh in ' + str(root))
    level = common.WORLD_PREFIX + args.tag
    world = run / level
    if world.exists():
        raise SystemExit('World directory already exists: %s (delete-world first, or pick another --tag)' % world)
    if any_run_jvms(root):
        raise SystemExit('A run of this checkout (client, server, GameTest or data) is already using run/; stop it first.')
    for port in (args.port, args.rcon_port):
        if not common.port_free(port):
            raise SystemExit('Port %d on 127.0.0.1 is in use.' % port)

    source_world = None
    if args.from_world:
        source_world = common.resolve(args.from_world).resolve()
        if not (source_world / 'level.dat').is_file():
            raise SystemExit('--from-world has no level.dat: ' + str(source_world))

    stamp = common.now_tag()
    common.STATE.mkdir(parents=True, exist_ok=True)
    run.mkdir(parents=True, exist_ok=True)
    backup_dir = common.STATE / ('backup-' + stamp)
    manifest = backup(run, backup_dir)
    # Record the session before anything under run/ changes, so `restore` can undo an interrupted start.
    session = dict(tag=args.tag, root=str(root), run=str(run), level=level, world=str(world), port=args.port,
                   rcon_port=args.rcon_port, ops=args.op, backup=str(backup_dir), backed_up=len(manifest),
                   log=None, exit_file=None, pid=None, started=stamp, status='backed-up')
    common.write_json(common.SESSION, session)
    register_world(world, args.tag)
    if source_world:
        # A copy, so the kept world (for example the old-version world) stays as generated.
        shutil.copytree(source_world, world, symlinks=False)
        (world / 'session.lock').unlink(missing_ok=True)

    password = secrets.token_urlsafe(24)
    fd = os.open(common.PASSWORD, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(password + '\n')
    os.chmod(common.PASSWORD, 0o600)
    write_properties(run / 'server.properties', {
        'server-ip': common.LOOPBACK, 'server-port': str(args.port), 'online-mode': 'false',
        'enforce-secure-profile': 'false', 'level-name': level, 'level-type': 'minecraft\\:' + args.world_type,
        # An empty generator-settings with the flat type logs "No key layers in MapLike[{}]" and falls back to the
        # default preset; spell that preset out (surface block at y=-61, players stand on y=-60).
        'generator-settings': FLAT_PRESET if args.world_type == 'flat' else '{}',
        'generate-structures': 'false' if args.world_type == 'flat' else 'true',
        'spawn-protection': '0', 'difficulty': 'peaceful', 'motd': 'HBM acceptance ' + args.tag,
        'enable-rcon': 'true', 'rcon.port': str(args.rcon_port), 'rcon.password': password,
        'broadcast-rcon-to-ops': 'false', 'broadcast-console-to-ops': 'false'})
    common.write_json(run / 'ops.json', ops_entries(args.op))

    session['status'] = 'starting'
    common.write_json(common.SESSION, session)
    launch(session, stamp)
    print('started: tag=%s pid=%d log=%s backup=%s (%d paths)' % (args.tag, session['pid'], common.rel(session['log']),
                                                                 common.rel(backup_dir), len(manifest)))
    return wait_ready(session, args.timeout)


def launch(session, stamp):
    """Start runServer for the session in the background; the wrapper shell records Gradle's exit code, so a later
    `stop` from another process can still read it."""
    root = Path(session['root'])
    logs = common.STATE / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    log = logs / ('server-%s-%s.log' % (session['tag'], stamp))
    exit_file = logs / ('server-%s-%s.exit' % (session['tag'], stamp))
    script = 'sh "$1" --offline --gradle-user-home "$2" runServer; echo "$?" > "$3"'
    with open(log, 'wb') as out:
        proc = subprocess.Popen(['/bin/sh', '-c', script, 'sh', str(root / 'tools' / 'migration' / 'build.sh'),
                                 str(common.GRADLE_USER_HOME), str(exit_file)],
                                cwd=root, stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                start_new_session=True)
    session.update(log=str(log), exit_file=str(exit_file), pid=proc.pid, status='launched')
    session.setdefault('logs', []).append(str(log))
    common.write_json(common.SESSION, session)
    return proc


def wait_ready(session, timeout):
    """Wait for "Done" and for RCON on 127.0.0.1:<rcon port>; on any other outcome stop the server and restore."""
    log = Path(session['log'])
    expected = '%s:%d' % (common.LOOPBACK, session['rcon_port'])

    def state():
        text = log.read_text(encoding='utf-8', errors='replace')
        bound = re.search(r'RCON running on (\S+)', text)
        if DONE.search(text) and bound:
            return 'ready:' + bound.group(1)
        if not common.pid_alive(session['pid']):
            return 'exited'
        return None
    result = wait_for(state, timeout)
    if result and result.startswith('ready:'):
        bound = result[6:]
        session.update(done=common.now_tag(), rcon_bound=bound, status='running')
        common.write_json(common.SESSION, session)
        print('Done reached; RCON running on ' + bound)
        if bound == expected:
            return 0
        print('RCON is bound to %s, not %s; stopping and restoring.' % (bound, expected))
    else:
        print(tail(log))
        print('Server did not reach "Done" with RCON (%s); stopping and restoring.' % (result or 'timeout'))
    stop_and_restore(session, force=True, timeout=300)
    return 1


def finish(session, report_extra):
    run = Path(session['run'])
    latest = run / 'logs' / 'latest.log'
    kept = None
    if latest.is_file():
        kept = common.STATE / 'logs' / ('server-%s-%s-latest.log' % (session['tag'], session['started']))
        shutil.copy2(latest, kept)
    report = restore(run, Path(session['backup']))
    report.update(report_extra, latest_log_copy=common.rel(kept) if kept else None, tag=session['tag'])
    history = common.STATE / 'sessions'
    history.mkdir(parents=True, exist_ok=True)
    session.update(stopped=common.now_tag(), result=report)
    common.write_json(history / ('%s-%s.json' % (session['tag'], session['started'])), session)
    if report['mismatched']:
        # Keep the session so `restore` can be repeated after the cause is fixed.
        print('restore mismatched %s; session kept for `server.py restore`' % report['mismatched'])
        return report
    common.SESSION.unlink()
    if common.PASSWORD.exists():
        common.PASSWORD.unlink()
    return report


def stop_server(session, force, timeout):
    """Stop the session's server (RCON `stop`, TERM with force); returns (how, gradle exit code, outcome) or raises."""
    import rcon
    how = None
    if session.get('pid') and (common.pid_alive(session['pid']) or server_jvms(session['root'])):
        try:
            client = rcon.connect(session['rcon_port'], timeout=15)
            try:
                print(client.command('stop') or '(stop sent)')
            except (ConnectionError, OSError):
                pass
            finally:
                client.close()
            how = 'rcon stop'
        except (OSError, PermissionError, SystemExit) as error:
            print('RCON failed: %s' % error)
            if not force:
                raise SystemExit('Server not stopped; use --force to TERM the server JVM.')
    else:
        how = 'not running'
    gone = lambda: not common.pid_alive(session.get('pid')) and not server_jvms(session['root'])
    if how is None or (not wait_for(gone, timeout) and force):
        for pid in server_jvms(session['root']):
            os.kill(pid, signal.SIGTERM)
        how = (how + ', then ' if how else '') + 'TERM (forced)'
    if not wait_for(gone, 60 if force else 1):
        raise SystemExit('Gradle is still running after %ds; nothing restored.' % timeout)
    code = outcome = None
    if session.get('exit_file'):
        exit_file = Path(session['exit_file'])
        code = exit_file.read_text().strip() if exit_file.is_file() else None
        log_text = Path(session['log']).read_text(encoding='utf-8', errors='replace')
        outcome = 'BUILD SUCCESSFUL' if 'BUILD SUCCESSFUL' in log_text else ('BUILD FAILED' if 'BUILD FAILED' in log_text else None)
    return how, code, outcome


def stop_and_restore(session, force, timeout):
    how, code, outcome = stop_server(session, force, timeout)
    report = finish(session, dict(stopped_by=how, gradle_exit=code, gradle_outcome=outcome))
    print('stopped by %s; Gradle exit %s, %s' % (how, code, outcome))
    print('restore: checked %d, restored %d, removed %d absent and %d new config files, mismatched %s'
          % (report['checked'], len(report['restored']), len(report['removed_absent']),
             len(report['removed_new_config_files']), report['mismatched'] or 'none'))
    return report, code


def cmd_stop(args):
    session = common.read_json(common.SESSION)
    if not session:
        raise SystemExit('No server session recorded.')
    report, code = stop_and_restore(session, args.force, args.timeout)
    return 0 if report['ok'] and code == '0' else 1


def cmd_restart(args):
    """Stop and start the same world inside one session: run/ is not restored in between, so files edited during the
    session (run/config/hbmsntm-common.toml, run/config/hbmRecipes/*.json) take effect, and the final `stop` still
    restores the state backed up at `start`."""
    session = common.read_json(common.SESSION)
    if not session or session.get('status') != 'running':
        raise SystemExit('No running server session to restart.')
    how, code, outcome = stop_server(session, args.force, args.timeout)
    print('stopped by %s; Gradle exit %s, %s' % (how, code, outcome))
    session.setdefault('restarts', []).append(dict(at=common.now_tag(), stopped_by=how, gradle_exit=code))
    for port in (session['port'], session['rcon_port']):
        if not wait_for(lambda: common.port_free(port), 30):
            raise SystemExit('Port %d is still in use; session kept, run `server.py restore`.' % port)
    launch(session, common.now_tag())
    print('restarted: tag=%s pid=%d log=%s' % (session['tag'], session['pid'], common.rel(session['log'])))
    return wait_ready(session, args.timeout)


def cmd_restore(args):
    session = common.read_json(common.SESSION)
    if not session:
        raise SystemExit('No server session recorded.')
    if (session.get('pid') and common.pid_alive(session['pid'])) or server_jvms(session['root']):
        raise SystemExit('The server is still running; stop it first.')
    report = finish(session, dict(stopped_by='restore only'))
    print(report)
    return 0 if report['ok'] else 1


def cmd_status(args):
    session = common.read_json(common.SESSION)
    if not session:
        print('no session')
    else:
        alive = common.pid_alive(session.get('pid'))
        print('tag=%s status=%s level=%s port=%d rcon=%d pid=%s alive=%s jvms=%s log=%s'
              % (session['tag'], session.get('status'), session['level'], session['port'], session['rcon_port'],
                 session.get('pid'), alive, server_jvms(session['root']),
                 common.rel(session['log']) if session.get('log') else None))
    for w in worlds()['worlds']:
        print('world %-9s %s' % (w['status'], common.rel(w['path'])))
    return 0


def cmd_delete_world(args):
    root = common.resolve(args.root).resolve()
    run = run_dir(root).resolve()
    target = run_dir(root) / (common.WORLD_PREFIX + args.tag)
    if not target.name.startswith(common.WORLD_PREFIX) or target.parent.resolve() != run:
        raise SystemExit('refusing: not an accept-goal29- world directly under run/')
    if world_status(target) != 'created':
        raise SystemExit('refusing: %s was not created by this tool (or is already deleted/kept)' % common.rel(target))
    session = common.read_json(common.SESSION)
    if session and session['world'] == str(target):
        raise SystemExit('refusing: the current session uses this world; stop the server first')
    if target.is_symlink() or not target.is_dir():
        if not target.exists():
            register_world(target, args.tag, 'deleted')
            print('already gone: ' + common.rel(target))
            return 0
        raise SystemExit('refusing: not a plain directory')
    shutil.rmtree(target)
    register_world(target, args.tag, 'deleted')
    print('deleted ' + common.rel(target))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    p = sub.add_parser('start')
    p.add_argument('--tag', required=True)
    p.add_argument('--root', default=str(common.REPO))
    p.add_argument('--op', action='append', default=[], help='player name to pre-op (offline UUID); repeatable')
    p.add_argument('--port', type=int, default=25565)
    p.add_argument('--rcon-port', type=int, default=25575)
    p.add_argument('--timeout', type=int, default=1200, help='seconds to wait for Done (first runs compile)')
    p.add_argument('--from-world', help='copy this world directory in as run/accept-goal29-<tag> before starting')
    p.add_argument('--world-type', choices=('flat', 'normal'), default='flat',
                   help='normal for world-generation checks (structures on); flat otherwise')
    p.set_defaults(func=cmd_start)
    p = sub.add_parser('stop')
    p.add_argument('--force', action='store_true')
    p.add_argument('--timeout', type=int, default=300)
    p.set_defaults(func=cmd_stop)
    p = sub.add_parser('restart')
    p.add_argument('--force', action='store_true')
    p.add_argument('--timeout', type=int, default=600)
    p.set_defaults(func=cmd_restart)
    sub.add_parser('restore').set_defaults(func=cmd_restore)
    sub.add_parser('status').set_defaults(func=cmd_status)
    p = sub.add_parser('delete-world')
    p.add_argument('--tag', required=True)
    p.add_argument('--root', default=str(common.REPO))
    p.set_defaults(func=cmd_delete_world)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
