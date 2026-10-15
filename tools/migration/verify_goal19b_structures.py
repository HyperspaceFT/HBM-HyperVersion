"""Goal19B bounded production-method structure checks and compiled behavior mutations for the industrial turbine; no Gradle, no Minecraft launch.

Extends the Goal18A structure world (which extends 17B -> 16B -> 16A -> 15B -> 14C -> 14B) without modifying it; see goal19b_regression/structure_stubs.py.
"""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import hashlib, os, re, uuid, zipfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
from goal18a_regression.common import ROOT, SOURCE, SOURCES_JAR, sha, jdk, adapter_hashes, run, write_report
from goal19b_regression.structure_stubs import build_world, SOURCE_PATHS, SERVICES, SHELLS, ADDITIONS, BLOCK, BE

FIXTURE = Path(__file__).resolve().parent / 'goal19b_regression'
OUT = ROOT / 'build/migration/goal19b/structures'
MAIN = 'goal19b.Goal19BStructureRegression'
COUNTS = re.compile(r'(\d+) assertions; (\d+) independent scenarios; (\d+) executed ticks')

# label -> (production file, [(anchor, replacement)], expected AssertionError fragment). Every anchor must occur exactly once in the current source.
MUTATIONS = {
    'dims_side_3_to_2': (BLOCK, [('return new int[] { 2, 0, 3, 3, 1, 1 };', 'return new int[] { 2, 0, 3, 2, 1, 1 };')], 'original 3x3x7 box'),
    'offset_3_to_2': (BLOCK, [('public int getOffset() { return 3; }', 'public int getOffset() { return 2; }')], 'original 3x3x7 box'),
    'drop_one_makeExtra': (BLOCK, [('this.makeExtra(level, core.relative(dir.getOpposite()).above(2));', ';')], 'exact seven extras'),
    'p7_without_above': (BLOCK, [('this.makeExtra(level, core.relative(dir.getOpposite(), 3).above());', 'this.makeExtra(level, core.relative(dir.getOpposite(), 3));')], 'exact seven extras'),
    'fill_rot_opposite_facing': (BLOCK, [('Direction rot = dir.getClockWise();', 'Direction rot = dir.getOpposite();')], 'exact seven extras'),
    'lever_offset_3_to_2': (BLOCK, [('BlockPos leverPos = corePos.offset(dir.getStepX() * 3, 1, dir.getStepZ() * 3);', 'BlockPos leverPos = corePos.offset(dir.getStepX() * 2, 1, dir.getStepZ() * 2);')], 'lever result'),
    'lock_inverted': (BLOCK, [('if(!be.operational) {', 'if(be.operational) {')], 'lever pull count'),
    'new_block_entity_extra_null': (BLOCK, [('case EXTRA -> new ProxyComboBlockEntity(pos, state).fluid().power();', 'case EXTRA -> null;')], 'proxy fluid and power, no inventory'),
    'sneak_gate_removed': (BLOCK, [('if(!player.isShiftKeyDown()) {', 'if(true) {')], 'lever result'),
    'missing_core_passes': (BLOCK, [('if(corePos == null) return InteractionResult.sidedSuccess(level.isClientSide);', 'if(corePos == null) return InteractionResult.PASS;')], 'missing core consumes the click'),
    'lever_volume_1_5_to_1': (BLOCK, [('NtmSoundEvents.TURBINE_LEVER.get(), SoundSource.BLOCKS, 1.5F, 1F', 'NtmSoundEvents.TURBINE_LEVER.get(), SoundSource.BLOCKS, 1F, 1F')], 'lever sound volume'),
    'lever_sound_event_swapped': (BLOCK, [('NtmSoundEvents.TURBINE_LEVER.get()', 'NtmSoundEvents.TURBINE_LARGE_LOOP.get()')], 'lever sound event'),
    'lever_sound_at_core': (BLOCK, [('Vec3.atCenterOf(pos)', 'Vec3.atCenterOf(corePos)')], 'lever sound position'),
    'lever_message_not_red': (BLOCK, [('Component.translatable("machine_industrial_turbine.compressor_locked").withStyle(ChatFormatting.RED)', 'Component.translatable("machine_industrial_turbine.compressor_locked").withStyle(ChatFormatting.GREEN)')], 'lever message style'),
    'conpos_rot_2_to_1': (BE, [('new DirPos(pos.relative(dir, 3).relative(rot, 2), rot),', 'new DirPos(pos.relative(dir, 3).relative(rot, 1), rot),')], 'fluid connection outside port 0'),
    'conpos_top_above_3_to_2': (BE, [('new DirPos(pos.relative(dir, 3).above(3), Direction.UP),', 'new DirPos(pos.relative(dir, 3).above(2), Direction.UP),')], 'fluid connection outside port 4'),
    'powerpos_direction_facing': (BE, [('new DirPos(pos.relative(dir, -4).above(), dir.getOpposite())', 'new DirPos(pos.relative(dir, -4).above(), dir)')], 'power connection direction'),
}

def read_source(rel): return (SOURCE / rel).read_bytes().decode('utf-8')

def capturing_build():
    """build_world over the production tree, recording every production file it reads (with its digest)."""
    captured = {}
    original_text, original_bytes = Path.read_text, Path.read_bytes
    def capture(path):
        absolute = Path(path).resolve()
        if absolute.is_relative_to(SOURCE):
            rel = absolute.relative_to(SOURCE).as_posix(); digest = hashlib.sha256(original_bytes(absolute)).hexdigest()
            if rel in captured and captured[rel] != digest: raise SystemExit('Source changed while building the world: ' + rel)
            captured[rel] = digest
    def read_text(path, *a, **k): value = original_text(path, *a, **k); capture(path); return value
    def read_bytes(path, *a, **k): value = original_bytes(path, *a, **k); capture(path); return value
    Path.read_text, Path.read_bytes = read_text, read_bytes
    try: world = build_world(SOURCE)
    finally: Path.read_text, Path.read_bytes = original_text, original_bytes
    return world, captured

def static_checks():
    """Facts the dynamic fixture cannot see: declaration shape, shadowing, and the engine services the stand-ins mirror."""
    block = read_source(BLOCK)
    checks = {}
    if not re.search(r'public class MachineIndustrialTurbineBlock extends DummyableBlock\b', block): raise SystemExit('Turbine block no longer extends DummyableBlock')
    for name in ('onRemove', 'playerWillDestroy'):
        if re.search(r'\b' + name + r'\s*\(', block): raise SystemExit('Turbine block now declares ' + name + '; the generic teardown would no longer be the tested path')
    checks['turbine_block_extends_DummyableBlock_without_onRemove_or_playerWillDestroy'] = True
    sounds = read_source('com/hbm/registry/NtmSoundEvents.java')
    lever = re.search(r'TURBINE_LEVER = reg\("block\.chungus_lever"\);', sounds)
    loop = re.search(r'TURBINE_LARGE_LOOP = reg\("block\.large_turbine_running"\);', sounds)
    if not lever or not loop: raise SystemExit('Production sound event anchors missing')
    checks['NtmSoundEvents.TURBINE_LEVER and TURBINE_LARGE_LOOP exist as declared by the stand-in'] = True
    # Stand-ins must not shadow a production file whose body is extracted; a production file that merely shares a service name is declared.
    names = set(re.findall(r'^(?:class|enum|record|interface) (\w+)', ADDITIONS, re.M))
    index = {}
    for directory, _, files in os.walk(SOURCE):
        for file in files:
            if file.endswith('.java'): index.setdefault(file[:-5], []).append((Path(directory) / file).relative_to(SOURCE).as_posix())
    extracted = set(SOURCE_PATHS)
    shadowed = {}
    for name in sorted(names):
        for rel in index.get(name, []):
            if rel in extracted and name not in SHELLS: raise SystemExit(f'Stand-in {name} shadows extracted production source {rel}')
            shadowed[name] = rel
    unknown = set(SERVICES) - names
    if unknown: raise SystemExit('Declared services missing from the world: ' + str(unknown))
    checks['stand_in_names_matching_a_production_file'] = shadowed
    checks['shells_whose_bodies_are_extracted'] = SHELLS
    if SOURCES_JAR.is_file():
        jar = zipfile.ZipFile(SOURCES_JAR)
        def text(name): return jar.read(name).decode('utf-8')
        engine = {
            'InteractionResult.sidedSuccess is SUCCESS client side, CONSUME server side': 'return isClientSide ? SUCCESS : CONSUME;' in text('net/minecraft/world/InteractionResult.java'),
            'Vec3.atCenterOf adds 0.5 on every axis': re.search(r'atCenterOf\(Vec3i toCopy\) \{\s*return atLowerCornerWithOffset\(toCopy, 0\.5, 0\.5, 0\.5\);', text('net/minecraft/world/phys/Vec3.java')) is not None,
            'Level.removeBlock sets AIR with flags 3 (bit 1 = neighbour update)': 'return this.setBlock(pos, fluidstate.createLegacyBlock(), 3 | (isMoving ? 64 : 0));' in text('net/minecraft/world/level/Level.java'),
            'Level.markAndNotifyBlock sends the neighbour update for flag 1': re.search(r'\(p_46607_ & 1\) != 0\) \{\s*this\.blockUpdated\(', text('net/minecraft/world/level/Level.java')) is not None,
            'LevelChunk.setBlockState runs the old state onRemove on the server before the neighbour update': re.search(r'if \(!this\.level\.isClientSide\) \{\s*blockstate\.onRemove\(this\.level, pos, state, isMoving\);', text('net/minecraft/world/level/chunk/LevelChunk.java')) is not None,
        }
        if not all(engine.values()): raise SystemExit('Engine fact not confirmed by the sources cache: ' + str(engine))
        checks['engine_facts_confirmed_in_neoforge_sources_jar'] = engine
    else:
        checks['engine_facts_confirmed_in_neoforge_sources_jar'] = 'sources jar absent; not checked'
    return checks

def main():
    output = OUT / uuid.uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    java, javac = jdk()
    fixture = FIXTURE / 'Goal19BStructureRegression.java'
    world, captured = capturing_build()
    if not set(SOURCE_PATHS) <= set(captured): raise SystemExit('World did not read every declared source: ' + str(sorted(set(SOURCE_PATHS) - set(captured))))
    hashes = {rel: sha(SOURCE / rel) for rel in sorted(captured)}
    if hashes != captured: raise SystemExit('Production changed while building the world')
    own = [fixture, FIXTURE / 'structure_stubs.py', Path(__file__).resolve()]
    report = {'evidence': 'Extracted production turbine geometry/port/lever/proxy/connection bodies and the inherited generic DummyableBlock placement, teardown and orphan-cascade bodies over declared engine services; every expected value is cited from the original or an independent fixture model; not Minecraft acceptance',
              'extracted_source_sha256': hashes, 'fixture_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in own},
              'jdk_sha256': {str(p): sha(p) for p in (java, javac)}, 'adapter_sha256': adapter_hashes(), 'static_checks': static_checks(),
              'service_stand_ins': {'declared_in_structure_stubs_ADDITIONS_and_anchored_swaps': list(SERVICES),
                                    'level_services': 'sounds list, block-entity map, chunksLoaded/hasChunksAt, flag-1 neighbour update after onRemove; Direction.getStep*, Vec3.atCenterOf, Player.sendSystemMessage, Block.neighborChanged hook'},
              'records': [], 'mutations': []}
    report['source_stable_after_run'] = True
    print(output, flush=True)

    def execute(label, text, record, expected_fragment, expected):
        target = output / label; target.mkdir()
        (target / 'StructureWorld.java').write_text(text, encoding='utf-8')
        (target / 'Goal19BStructureRegression.java').write_bytes(fixture.read_bytes())
        record['generated_files_sha256'] = {p.relative_to(ROOT).as_posix(): sha(p) for p in target.iterdir()}
        record['commands'] = []
        for i, command in enumerate([[javac, '-encoding', 'UTF-8', '-d', target / 'classes', target / 'StructureWorld.java', target / 'Goal19BStructureRegression.java'],
                                     [java, '-ea', '-cp', target / 'classes', MAIN]]):
            code, out = run(command)
            (target / ('compile.log', 'run.log')[i]).write_text(out, encoding='utf-8')
            record['commands'].append({'command': [str(c) for c in command], 'returncode': code, 'output': out})
            report['source_stable_after_run'] = hashes == {rel: sha(SOURCE / rel) for rel in hashes}
            write_report(output, report)
            if not report['source_stable_after_run']: raise SystemExit('Production changed during structures')
            if i == 0 and code: raise SystemExit('Compile failure is not mutation detection: ' + label + '\n' + out)
            if i == 1:
                if (code == 0) != expected: raise SystemExit('Wrong expected result for ' + label + ': ' + out)
                if not expected:
                    failure = re.search(r'java\.lang\.AssertionError: (.*)', out)
                    if not failure: raise SystemExit('Mutation was not a behavior assertion: ' + label + '\n' + out)
                    record['assertion'] = failure.group(1).strip()
                    if expected_fragment not in record['assertion']: raise SystemExit(f'Mutation {label} detected by an unexpected assertion: {record["assertion"]}')
                else:
                    print(out, end='', flush=True)
                    counts = COUNTS.search(out)
                    if not counts: raise SystemExit('Missing structure counts')
                    report['production_counts'] = dict(zip(('assertions', 'scenarios', 'ticks'), map(int, counts.groups())))
        record['compiled_successfully'] = True; record['behavior_mutation_detected'] = not expected

    production = {'label': 'production', 'expected_pass': True}
    report['records'].append(production)
    execute('production', world, production, '', True)

    # Each mutation edits a temporary copy of the files the world reads; the world is rebuilt from that copy.
    def tree(root, label=None, rel=None, pairs=()):
        for name in captured:
            target = root / name; target.parent.mkdir(parents=True, exist_ok=True)
            data = (SOURCE / name).read_bytes()
            if name == rel:
                text = data.decode('utf-8')
                for old, new in pairs:
                    if text.count(old) != 1: raise SystemExit(f'Mutation anchor missing or not unique: {label}: {old}')
                    text = text.replace(old, new, 1)
                data = text.encode('utf-8')
            target.write_bytes(data)
    identity = output / 'identity-copy'
    tree(identity)
    if build_world(identity) != world: raise SystemExit('Copied source tree does not rebuild the production world')
    for label, (rel, pairs, fragment) in MUTATIONS.items():
        original = read_source(rel)
        for old, new in pairs:
            if original.count(old) != 1: raise SystemExit(f'Mutation anchor missing or not unique in current production source: {label}: {old}')
        root = output / 'mutations' / label / 'src'
        tree(root, label, rel, pairs)
        mutated = build_world(root)
        if mutated == world: raise SystemExit('Mutation did not change the world: ' + label)
        record = {'label': label, 'file': rel, 'anchors': [old for old, _ in pairs], 'expected_assertion': fragment, 'mutated_source_sha256': sha(root / rel)}
        report['mutations'].append(record)
        execute('mutation-' + label, mutated, record, fragment, False)
    report['mutations_detected'] = len(MUTATIONS)
    report['source_stable_after_run'] = hashes == {rel: sha(SOURCE / rel) for rel in hashes}
    write_report(output, report)
    if not report['source_stable_after_run']: raise SystemExit('Production changed during structures')
    print(f'Compiled behavior mutations detected: {len(MUTATIONS)}/{len(MUTATIONS)}')
    print(f'source_stable_after_run: {report["source_stable_after_run"]}')
    print(output / 'report.json')

if __name__ == '__main__': main()
