#!/usr/bin/env python3
"""Generate a world with the pre-Goal-28 mod (commit 66a00353 = goal27d content plus the rename) for save-upgrade checks.

Run from the NEO root, in order:
  python3 -B -X utf8 tools/migration/acceptance/oldworld.py extract
  python3 -B -X utf8 tools/migration/acceptance/oldworld.py generate
  python3 -B -X utf8 tools/migration/acceptance/oldworld.py cleanup

extract  `git archive 66a00353` unpacked into build/migration/accept-goal29/old-27d/ (no worktree, nothing written to
         .git), checks that the archive's build.gradle, gradle.lockfile, settings.gradle and gradle.properties equal
         aa7abb77's, adds the macOS lock-file ignore line of the Mac migration commit to build.gradle and copies
         tools/migration/build.sh in. Gradle then runs offline against this repository's .gradle/user-home; a missing
         dependency stops the run (recorded as "no runtime"), nothing is downloaded.
generate starts the old tree's runServer through server.py (tag "old", own run/), places the blocks listed in
         COMMANDS over RCON, reads them back, saves and stops, then moves the world to
         build/migration/accept-goal29/old-world/ (with old-world/PLACED.md listing what is where).
cleanup  keeps the old tree's logs under build/migration/accept-goal29/old-27d-logs/ and deletes old-27d/.
Load the kept world with the current package via `server.py start --tag oldload --from-world
build/migration/accept-goal29/old-world` (a copy; the original stays as generated).
"""
import argparse
import io
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

OLD_COMMIT = '66a00353'
SAME_AS = 'aa7abb77'
SAME_FILES = ('build.gradle', 'gradle.lockfile', 'settings.gradle', 'gradle.properties')
OLD = common.STATE / 'old-27d'
KEPT = common.STATE / 'old-world'
LOGS = common.STATE / 'old-27d-logs'
LOCK_ANCHOR = '    lockAllConfigurations()\n'
LOCK_LINES = ("    // Minecraft ships this library for macOS only, so the runtime classpaths resolve it on macOS and nowhere else.\n"
              "    ignoredDependencies.add('ca.weblite:java-objc-bridge')\n")
TAG = 'old'

# Flat world: the surface block is grass at y=-61, so everything stands on y=-60. Rows along +x from x=0, z=0.
# 28B 8.2: the six resource blocks and the three uranium/Sa326 schist ores (NtmBlocks.java:92-102 at 66a00353).
# 28A 9.5: a fluid burner core set to 7 with its three slots filled (HeaterOilburnerBlockEntity "setting", slots 0-2);
#          only the core is placed (commands cannot run the multiblock placement), which is what save loading reads.
# S4.3:    the general save upgrade: the above plus 29B's changed content as it existed before (radio torch sender and
#          receiver without the "lit" state, small and large radar - the large one still had the small radar's block
#          entity type) and a chest of item IDs.
Y = -60
ROW = ['hbmsntm:resource_limestone', 'hbmsntm:resource_bauxite', 'hbmsntm:resource_hematite', 'hbmsntm:resource_malachite',
       'hbmsntm:resource_chrysotile', 'hbmsntm:resource_sulfurous_stone', 'hbmsntm:ore_gneiss_uranium',
       'hbmsntm:ore_gneiss_uranium_scorched', 'hbmsntm:ore_gneiss_schrabidium']
BURNER = (2, Y, 4)
CHEST = (6, Y, 4)
CHEST_ITEMS = ['hbmsntm:ingot_steel', 'hbmsntm:plate_steel', 'hbmsntm:canister_empty', 'hbmsntm:resource_hematite',
               'hbmsntm:resource_malachite', 'hbmsntm:resource_bauxite', 'hbmsntm:resource_limestone',
               'hbmsntm:heater_oilburner', 'hbmsntm:radio_torch_sender', 'hbmsntm:radio_torch_receiver',
               'hbmsntm:machine_radar', 'hbmsntm:machine_radar_large']
SINGLES = [((0, Y, 8), 'hbmsntm:radio_torch_sender[facing=up]'), ((2, Y, 8), 'hbmsntm:radio_torch_receiver[facing=up]'),
           ((4, Y, 8), 'hbmsntm:machine_radar'), ((8, Y, 8), 'hbmsntm:machine_radar_large')]


def commands():
    out = ['gamerule doDaylightCycle false', 'gamerule doWeatherCycle false', 'gamerule doMobSpawning false',
           'forceload add -16 -16 32 32']
    for i, block in enumerate(ROW):
        out.append('setblock %d %d 0 %s' % (i * 2, Y, block))
    x, y, z = BURNER
    out.append('setblock %d %d %d hbmsntm:heater_oilburner[facing=north,type=core]{setting:7,'
               'Items:[{Slot:0b,id:"hbmsntm:canister_empty",count:3},{Slot:1b,id:"hbmsntm:canister_empty",count:2},'
               '{Slot:2b,id:"hbmsntm:fluid_identifier_multi",count:1}]}' % (x, y, z))
    x, y, z = CHEST
    items = ','.join('{Slot:%db,id:"%s",count:%d}' % (i, item, i + 1) for i, item in enumerate(CHEST_ITEMS))
    out.append('setblock %d %d %d minecraft:chest{Items:[%s]}' % (x, y, z, items))
    for (x, y, z), block in SINGLES:
        out.append('setblock %d %d %d %s' % (x, y, z, block))
    return out


def readback():
    out = ['execute if block %d %d 0 %s' % (i * 2, Y, b) for i, b in enumerate(ROW)]
    out.append('data get block %d %d %d' % BURNER)
    out.append('data get block %d %d %d Items' % CHEST)
    out += ['execute if block %d %d %d %s' % (x, y, z, b.split('[')[0]) for (x, y, z), b in SINGLES]
    out += ['data get block %d %d %d' % pos for pos, b in SINGLES if 'radar' in b or 'radio' in b]
    out += ['save-all flush']
    return out


def placed_md():
    lines = ['# Old-version world (%s, tag %s)' % (OLD_COMMIT, TAG), '',
             'Flat world, blocks on y=%d. Generated by tools/migration/acceptance/oldworld.py with the old tree\'s '
             'runServer; load a copy with `server.py start --tag oldload --from-world build/migration/accept-goal29/old-world`.' % Y, '',
             '| Position | Content | Check (item) |', '| --- | --- | --- |']
    for i, block in enumerate(ROW):
        lines.append('| %d %d 0 | `%s` | 28B 8.2 |' % (i * 2, Y, block))
    lines.append('| %d %d %d | `hbmsntm:heater_oilburner` core only, setting 7, slots 0-2: 3 and 2 empty canisters, '
                 'multi fluid identifier | 28A 9.5 |' % BURNER)
    lines.append('| %d %d %d | chest, slots 0-%d: %s (count = slot + 1) | S4.3 |' % (CHEST + (len(CHEST_ITEMS) - 1, ', '.join('`%s`' % i for i in CHEST_ITEMS))))
    for (x, y, z), block in SINGLES:
        note = ''
        if block.startswith('hbmsntm:machine_radar_large'):
            # 66a00353 registers machine_radar_large with the small radar's block entity type, whose valid blocks do not
            # include it: setblock places the block, then reports "Invalid block entity hbmsntm:machine_radar".
            note = ' (block only: the old version cannot give it a block entity)'
        elif block.startswith('hbmsntm:radio_torch'):
            note = ' (old block state without `lit`)'
        lines.append('| %d %d %d | `%s`%s | S4.3 (29B content) |' % (x, y, z, block, note))
    return '\n'.join(lines) + '\n'


def git(*args, binary=False):
    out = subprocess.run(['git', '--no-optional-locks', *args], cwd=common.REPO, check=True, capture_output=True)
    return out.stdout if binary else out.stdout.decode('utf-8')


def cmd_extract(args):
    if OLD.exists():
        raise SystemExit('%s exists; run cleanup first' % common.rel(OLD))
    for name in SAME_FILES:
        if git('rev-parse', '%s:%s' % (OLD_COMMIT, name)) != git('rev-parse', '%s:%s' % (SAME_AS, name)):
            raise SystemExit('%s differs between %s and %s' % (name, OLD_COMMIT, SAME_AS))
    data = git('archive', '--format=tar', OLD_COMMIT, binary=True)
    OLD.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(OLD, filter='data')
    gradle = OLD / 'build.gradle'
    text = gradle.read_text(encoding='utf-8')
    if text.count(LOCK_ANCHOR) != 1 or 'java-objc-bridge' in text:
        raise SystemExit('build.gradle anchor not found exactly once')
    gradle.write_text(text.replace(LOCK_ANCHOR, LOCK_ANCHOR + LOCK_LINES), encoding='utf-8')
    target = OLD / 'tools' / 'migration' / 'build.sh'
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(common.BUILD_SH, target)
    files = sum(1 for p in OLD.rglob('*') if p.is_file())
    record = dict(commit=git('rev-parse', OLD_COMMIT).strip(), files=files, build_gradle_sha256=common.sha256(gradle),
                  build_sh_sha256=common.sha256(target), same_as=SAME_AS, same_files=list(SAME_FILES))
    common.write_json(common.STATE / 'old-27d-extract.json', record)
    print('extracted %s (%d files) to %s; build.gradle patched, build.sh copied' % (record['commit'][:10], files, common.rel(OLD)))
    return 0


def server(*args):
    return subprocess.run([sys.executable, '-B', '-X', 'utf8', str(Path(__file__).with_name('server.py')), *args]).returncode


def cmd_generate(args):
    if not (OLD / 'tools' / 'migration' / 'build.sh').is_file():
        raise SystemExit('run extract first')
    if KEPT.exists():
        raise SystemExit('%s already exists' % common.rel(KEPT))
    if server('start', '--tag', TAG, '--root', str(OLD), '--op', 'alice', '--timeout', str(args.timeout)) != 0:
        # server.py has already stopped what it started and restored the old tree's run/.
        print('old server did not start; see build/migration/accept-goal29/logs/ (record "no runtime" if dependencies are missing)')
        return 1
    import rcon
    client = rcon.connect()
    transcript = []
    try:
        for command in commands() + readback():
            reply = client.command(command)
            transcript.append('> %s\n%s' % (command, reply or '(no output)'))
    finally:
        client.close()
    (common.STATE / 'logs' / 'old-world-rcon.txt').write_text('\n'.join(transcript) + '\n', encoding='utf-8')
    print('\n'.join(transcript))
    session = common.read_json(common.SESSION)
    world = Path(session['world'])
    stopped = server('stop')
    import server as server_module
    if stopped != 0 or server_module.server_jvms(OLD) or common.read_json(common.SESSION):
        raise SystemExit('the old server did not stop cleanly (exit %d); the world stays at %s' % (stopped, world))
    if not world.is_dir():
        raise SystemExit('world not found after stop: %s' % world)
    shutil.move(str(world), str(KEPT))
    server_module.register_world(world, TAG, 'moved to ' + common.rel(KEPT))
    (KEPT / 'PLACED.md').write_text(placed_md(), encoding='utf-8')
    print('kept the old world at %s (server stop exit %d)' % (common.rel(KEPT), stopped))
    return stopped


def cmd_cleanup(args):
    if common.read_json(common.SESSION):
        raise SystemExit('a server session is open; stop it first')
    if not OLD.is_dir() or OLD.is_symlink() or OLD.parent.resolve() != common.STATE.resolve():
        raise SystemExit('nothing to clean')
    logs = OLD / 'run' / 'logs'
    if logs.is_dir():
        if LOGS.exists():
            raise SystemExit('%s exists' % common.rel(LOGS))
        shutil.copytree(logs, LOGS)
    shutil.rmtree(OLD)
    print('removed %s; logs kept in %s' % (common.rel(OLD), common.rel(LOGS)))
    return 0


def cmd_commands(args):
    print('\n'.join(commands() + readback()))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='command', required=True)
    sub.add_parser('extract').set_defaults(func=cmd_extract)
    p = sub.add_parser('generate')
    p.add_argument('--timeout', type=int, default=2400, help='seconds for the old tree to compile and reach Done')
    p.set_defaults(func=cmd_generate)
    sub.add_parser('cleanup').set_defaults(func=cmd_cleanup)
    sub.add_parser('commands', help='print the placement and read-back commands').set_defaults(func=cmd_commands)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
