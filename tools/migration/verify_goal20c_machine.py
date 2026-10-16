"""Goal20C isolated spent fuel pool drum: a static freeze of MachineWasteDrumBlockEntity, MachineWasteDrumBlock, MachineWasteDrumMenu,
MachineWasteDrumScreen, FuelPoolRecipes and the client-only boundaries against the original (read-only), plus a compiled isolated run of the
production FuelPoolRecipes, FuelPoolRecipeClientSync and MachineWasteDrumBlockEntity over the goal20c_regression/machine_stubs.py stand-ins
with the existing JDK 21 and Gson (strict and lenient readers, client sync, slot rules, water counting, the decay loop with a scripted random,
and a seeded Monte Carlo compared with the exact geometric model written to finite-model.json). No Gradle, game, server or network.

python -B -X utf8 tools/migration/verify_goal20c_machine.py               plain run
python -B -X utf8 tools/migration/verify_goal20c_machine.py --mutations   plain run, then every anchored mutation (each must be detected)
"""
from pathlib import Path
import argparse, json, math, re, statistics, subprocess, sys, uuid
sys.path.insert(0, str(Path(__file__).resolve().parent))
from goal18a_regression.common import ROOT, SOURCE, sha, jdk, gson, classpath, adapter_hashes, run, write_report
from goal20b_regression import recipe_static as rs20b
from goal20c_regression import machine_stubs as world, machine_static as ms, finite_model as fm

FIXTURE = Path(__file__).resolve().parent / 'goal20c_regression'
FIXTURE_REL = 'com/hbm/blockentity/machine/Goal20CMachineRegression.java'
MAIN = 'com.hbm.blockentity.machine.Goal20CMachineRegression'
OUT = ROOT / 'build/migration/goal20c'
ORIGINAL = ROOT.parent / 'Hbm-s-Nuclear-Tech-GIT'
EXAMPLE = ROOT / 'migration/goal20c-custom-fuelpool-example.json'
ITEMS = 'com/hbm/items/NtmItems.java'
MC_DRUMS = 16
MC_SEED = 20201015
Z_LIMIT = 5.0

BE, FUELPOOL, CLIENT_SYNC = ms.BE, ms.FUELPOOL, ms.CLIENT_SYNC

# label -> (production file, old text (exactly once), new text, expected AssertionError fragment). Compiled into a copy, run deterministic sections.
COMPILED_MUTATIONS = {
    'decay_72000_to_36000': (BE, '    public static final int DECAY_TICKS = 72000;\n', '    public static final int DECAY_TICKS = 36000;\n', 'DECAY_TICKS equals the original'),
    'roll_only_key_slots': (BE, '            if(stack.isEmpty()) continue;\n', '            if(stack.isEmpty() || !FuelPoolRecipes.isKey(stack)) continue;\n',
                            'cool waste and other items roll too'),
    'water_excludes_down': (BE, '            BlockPos neighbour = this.worldPosition.relative(dir);\n',
                            '            if(dir == Direction.DOWN) continue;\n            BlockPos neighbour = this.worldPosition.relative(dir);\n', 'minecraft:water on DOWN counts once'),
    'flowing_water_excluded': (BE, 'if(fluid == Fluids.WATER || fluid == Fluids.FLOWING_WATER) water++;', 'if(fluid == Fluids.WATER) water++;', 'minecraft:flowing_water on DOWN counts once'),
    'unloaded_neighbours_read': (BE, '            if(!this.level.isLoaded(neighbour)) continue;\n', '', 'unloaded neighbours count as no water and are never read'),
    'extraction_allowed_for_hot': (BE, '{ return !this.isKey(this.getItem(slot)); }', '{ return true; }', 'automation cannot take the hot waste in slot 0'),
    'extraction_reads_passed_stack': (BE, '{ return !this.isKey(this.getItem(slot)); }', '{ return !this.isKey(stack); }', 'automation cannot take the hot waste in slot 0'),
    'stack_limit_2': (BE, '@Override public int getMaxStackSize() { return 1; }', '@Override public int getMaxStackSize() { return 2; }', 'stack limit 1'),
    'set_changed_every_tick': (BE, '        if(changed) this.setChanged();\n', '        this.setChanged();\n', 'does not mark the drum dirty'),
    'client_side_decays': (BE, 'if(this.level == null || this.level.isClientSide) return;', 'if(this.level == null) return;', 'the client never rolls or cools'),
    'output_count_not_clamped': (BE, 'this.slots.set(i, output.copyWithCount(1));', 'this.slots.set(i, output);', 'a custom row with output count 3 still leaves one item'),
    'client_uses_server_table': (BE, 'this.level != null && this.level.isClientSide ? FuelPoolRecipeClientSync.isKey(stack) : FuelPoolRecipes.isKey(stack)', 'FuelPoolRecipes.isKey(stack)',
                                 'without a snapshot the client drum uses the default table'),
    'default_row_dropped': (FUELPOOL, '        waste(NtmItems.WASTE_ZFB_MOX);\n', '', 'the default table has the nine original ZIRNOX waste rows'),
    'default_rows_reordered': (FUELPOOL, '        waste(NtmItems.WASTE_U233);\n        waste(NtmItems.WASTE_U235);\n', '        waste(NtmItems.WASTE_U235);\n        waste(NtmItems.WASTE_U233);\n',
                               'default row 6 is hbmsntm:waste_u233'),
    'lenient_made_strict': (FUELPOOL, 'if(lenient) handler.readRecipeLenient(rows.get(i), i);', 'if(false) handler.readRecipeLenient(rows.get(i), i);', 'the config-file path skips bad rows'),
    'strict_made_lenient': (FUELPOOL, 'public static List<FuelPoolRecipe> readSnapshot(String json) { return readSnapshot(json, false); }',
                            'public static List<FuelPoolRecipe> readSnapshot(String json) { return readSnapshot(json, true); }', 'strict reader rejects an unknown id'),
    'wildcard_accepted': (FUELPOOL, 'if(inputMeta < 0 || inputMeta == MetaHelper.WILDCARD_VALUE)', 'if(inputMeta < 0)', 'strict reader rejects the 32767 wildcard'),
    'input_count_2_accepted': (FUELPOOL, 'integer(input.get(1)) != 1', 'integer(input.get(1)) < 1', 'strict reader rejects input count 2'),
    'duplicate_accepted': (FUELPOOL, '            if(old.key().equals(row.key())) throw invalid("duplicate input " + row.key());\n', '', 'strict reader rejects a duplicate key'),
    'four_elements_accepted': (FUELPOOL, 'if(input.size() < 1 || input.size() > 3)', 'if(input.size() < 1 || input.size() > 4)', 'strict reader rejects a four-element input'),
    'plain_output_meta_patch': (FUELPOOL, 'if(MetaHelper.getMeta(stack) != meta) MetaHelper.setMeta(stack, meta);', 'MetaHelper.setMeta(stack, meta);',
                                'a plain item output with META 0 carries no META patch'),
    'empty_client_table_falls_back': (CLIENT_SYNC, 'return snapshot == null ? FuelPoolRecipes.getDefaultRecipes()', 'return snapshot == null || snapshot.isEmpty() ? FuelPoolRecipes.getDefaultRecipes()',
                                      'an empty received table is authoritative'),
    'automation_stacks_into_filled_slot': (BE, 'return this.getItem(slot).isEmpty() && this.canPlaceItem(slot, stack); }', 'return this.canPlaceItem(slot, stack); }',
                                           'automation does not insert into a filled slot: hot waste in slot 0'),
    'canonical_snapshot_guard_removed': (FUELPOOL, '        try { encodeSnapshot(writeRows(replacement)); }\n'
                                                   '        catch(IOException ex) { throw invalid("cannot write the sync snapshot: " + ex.getMessage()); }\n'
                                                   '        catch(IllegalArgumentException ex) { throw invalid("the canonical sync snapshot of this file exceeds 256 KiB"); }\n', '',
                                         'a compact file whose canonical snapshot exceeds 256 KiB is rejected'),
}

# label -> (production file, old, new, static check name, expected AssertionError fragment).
STATIC_MUTATIONS = {
    'static_decay_36000': (BE, 'DECAY_TICKS = 72000;', 'DECAY_TICKS = 36000;', 'block_entity', 'DECAY_TICKS equals the original'),
    'static_roll_only_keys': (BE, '            if(stack.isEmpty()) continue;\n', '            if(stack.isEmpty()) continue;\n            if(!this.isKey(stack)) continue;\n', 'block_entity',
                              'every non-empty slot rolls'),
    'drum_emits_radiation': (BE, '        int r = DECAY_TICKS / water;\n', '        ChunkRadiationManager.proxy.incrementRad(this.level, this.worldPosition, 5F);\n        int r = DECAY_TICKS / water;\n',
                             'block_entity', 'has no ChunkRadiationManager'),
    'drum_plays_sound': (BE, '        int r = DECAY_TICKS / water;\n', '        this.level.playSound(null, this.worldPosition, NtmSoundEvents.GEIGER.get(), null, 1F, 1F);\n        int r = DECAY_TICKS / water;\n',
                         'block_entity', 'has no playSound'),
    'client_import_in_block_entity': (BE, 'import net.minecraft.core.BlockPos;\n', 'import net.minecraft.client.Minecraft;\nimport net.minecraft.core.BlockPos;\n', 'isolation',
                                      'MachineWasteDrumBlockEntity.java names no client-only class'),
    'screen_height_166': (ms.SCREEN, 'this.imageHeight = 189;', 'this.imageHeight = 166;', 'screen', 'screen 176x189'),
    'info_panel_moved': (ms.SCREEN, 'this.drawInfoPanel(guiGraphics, this.leftPos - 16, this.topPos + 36, 2);', 'this.drawInfoPanel(guiGraphics, this.leftPos - 16, this.topPos + 40, 2);',
                         'screen', 'info panel type 2'),
    'menu_slot_moved': (ms.MENU, 'new SlotNonRetarded(be, 5, 107, 39)', 'new SlotNonRetarded(be, 5, 107, 40)', 'menu', 'the twelve slot coordinates'),
    'player_inventory_y_84': (ms.MENU, 'this.playerInv(inventory, 8, 107);', 'this.playerInv(inventory, 8, 84);', 'menu', 'player inventory at x 8, y 107'),
    'block_resistance_6': (ms.BLOCKS, 'new MachineWasteDrumBlock(BlockBehaviour.Properties.of().strength(5.0F, 10.0F)', 'new MachineWasteDrumBlock(BlockBehaviour.Properties.of().strength(5.0F, 6.0F)',
                           'block', 'machine_waste_drum strength'),
    'particles_include_down': (ms.BLOCK, '            if(dir == Direction.DOWN) continue;\n', '', 'block', 'bubbles skip the neighbour below'),
    'animate_tick_not_client_only': (ms.BLOCK, '    @OnlyIn(Dist.CLIENT)\n    public void animateTick(', '    public void animateTick(', 'block', 'animateTick is @OnlyIn(Dist.CLIENT)'),
    'packet_client_call_outside_onlyin': (ms.PACKET, 'context.enqueueWork(() -> handleClient(packet));', 'context.enqueueWork(() -> FuelPoolRecipeClientSync.receive(packet.json()));',
                                          'isolation', 'the packet reaches FuelPoolRecipeClientSync only from'),
    'sync_reader_lenient': (FUELPOOL, '{ return readSnapshot(json, false); }', '{ return readSnapshot(json, true); }', 'fuelpool', 'the public snapshot reader (sync) is strict'),
    'static_automation_place_guard_removed': (BE, 'return this.getItem(slot).isEmpty() && this.canPlaceItem(slot, stack); }', 'return this.canPlaceItem(slot, stack); }', 'block_entity',
                                              'automation fills only empty slots'),
    'static_decay_javadoc_line_changed': (BE, '/** Original updateEntity (:206):', '/** Original updateEntity (:200):', 'block_entity', 'the DECAY_TICKS javadoc cites the original formula at :206'),
    'static_requires_correct_tool_removed': (ms.BLOCKS, 'new MachineWasteDrumBlock(BlockBehaviour.Properties.of().strength(5.0F, 10.0F).sound(SoundType.METAL).mapColor(MapColor.METAL).requiresCorrectToolForDrops()',
                                             'new MachineWasteDrumBlock(BlockBehaviour.Properties.of().strength(5.0F, 10.0F).sound(SoundType.METAL).mapColor(MapColor.METAL)',
                                             'block', 'machine_waste_drum requires the correct tool for drops'),
    'static_canonical_guard_removed': (FUELPOOL, 'try { encodeSnapshot(writeRows(replacement)); }', 'try { encodeSnapshot(replacement.toString()); }', 'fuelpool',
                                       'readRecipeStream encodes the canonical sync snapshot of the replacement rows'),
    'static_handler_line_dropped': (ms.SERIALIZABLE, '        recipeHandlers.add(new FuelPoolRecipes());\n', '', 'fuelpool', 'FuelPoolRecipes is imported and in the SerializableRecipe handler list'),
    'static_write_snapshot_unchecked': (FUELPOOL, 'String result = writeRows(RECIPES); readSnapshot(result); return result;', 'String result = writeRows(RECIPES); return result;', 'fuelpool',
                                        'writeSnapshot = writeRows(RECIPES) plus the strict readSnapshot self-check'),
}

checks = []
def ck(condition, label):
    if not condition: raise AssertionError(label)
    checks.append(label)


def run_dir(kind):
    output = OUT / kind / uuid.uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    return output


def replaced(text, old, new, label):
    text = text.replace('\r\n', '\n')
    if text.count(old) != 1: raise SystemExit(f'Mutation anchor missing or not unique: {label} ({text.count(old)} matches)')
    return text.replace(old, new, 1)


def static_checks(texts, facts, check):
    return {
        'block_entity': lambda t: ms.check_block_entity(t[BE], facts, check),
        'block': lambda t: ms.check_block(t[ms.BLOCK], t[ms.BLOCKS], facts, check),
        'menu': lambda t: ms.check_menu(t[ms.MENU], t[ms.MENU_BASE], facts, check),
        'screen': lambda t: ms.check_screen(t[ms.SCREEN], facts, check),
        'fuelpool': lambda t: ms.check_fuelpool(t[FUELPOOL], t[ms.SERIALIZABLE], facts, check),
        'isolation': lambda t: ms.check_client_isolation(t, check),
    }


def depleted_constants(text):
    found = dict(re.findall(r'public static final int (COOL|HOT) = (\d+);', text))
    if set(found) != {'COOL', 'HOT'}: raise SystemExit('DepletedFuelItem COOL/HOT constants not found')
    return {k: int(v) for k, v in found.items()}


def original_defaults(original_root, items):
    """The original FuelPoolRecipes.java:27-35 rows -> NEO ids (checked against the production registrations)."""
    lines = rs20b.read(original_root / ms.ORIGINAL_FUELPOOL).split('\n')
    rows = []
    for i, l in enumerate(lines):
        m = re.search(r'recipes\.put\(new ComparableStack\(ModItems\.(waste_\w+), 1, 1\), new ItemStack\(ModItems\.(waste_\w+)\)\);', l)
        if m and not m.group(1).startswith('waste_plate_'):
            if m.group(1) != m.group(2): raise SystemExit('original fuel pool row with a different output: ' + l)
            field = m.group(1).upper()
            if items.get(field) != m.group(1): raise SystemExit(f'Production registration of {field} as {m.group(1)} not found')
            rows.append({'line': i + 1, 'original': m.group(1), 'id': 'hbmsntm:' + m.group(1)})
    return rows


def monte_carlo_summary(data, model):
    summary = {}
    pooled = []
    for w, entry in sorted(data.items(), key=lambda kv: int(kv[0])):
        r = entry['r']; slots = entry['slot_times']; drums = entry['drum_times']
        expected_row = model['water'][w]
        sd = expected_row['slot_sd_ticks']
        slot_mean = statistics.fmean(slots)
        slot_z = (slot_mean - r) / (sd / math.sqrt(len(slots)))
        drum_mean = statistics.fmean(drums)
        drum_sd = statistics.stdev(drums)
        drum_z = (drum_mean - expected_row['drum_expected_ticks']) / (drum_sd / math.sqrt(len(drums)))
        pooled += [t / r for t in slots]
        summary[w] = {'r': r, 'drums': entry['drums'], 'slot_samples': len(slots), 'slot_mean_ticks': slot_mean, 'slot_expected_ticks': r, 'slot_z': slot_z,
                      'slot_min': min(slots), 'slot_max': max(slots), 'drum_mean_ticks': drum_mean, 'drum_expected_ticks': expected_row['drum_expected_ticks'],
                      'drum_sample_sd': drum_sd, 'drum_z': drum_z, 'executed_ticks': entry['executed_ticks']}
    pooled_mean = statistics.fmean(pooled)
    # T / r has mean 1 and standard deviation sqrt(1 - p) ~ 1 for every water count.
    pooled_z = (pooled_mean - 1.0) / (1.0 / math.sqrt(len(pooled)))
    return summary, {'samples': len(pooled), 'mean_over_r': pooled_mean, 'z': pooled_z}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--source', type=Path, default=ORIGINAL, help='original Hbm-s-Nuclear-Tech-GIT worktree (default: sibling directory)')
    parser.add_argument('--mutations', action='store_true', help='also run the anchored mutations (each must be detected)')
    args = parser.parse_args()
    original_root = args.source.resolve()
    output = run_dir('machine')
    print(output, flush=True)
    java, javac = jdk(); GSON = gson()
    start = json.loads((OUT / 'baseline.json').read_text(encoding='utf-8'))
    report = {'evidence': 'Static source freeze of the drum classes against the original, and the production FuelPoolRecipes, FuelPoolRecipeClientSync and '
                          'MachineWasteDrumBlockEntity compiled over minimal stand-ins (no Minecraft, NeoForge or older worlds) and run with a scripted and a seeded random; '
                          'compile and fixture execution only, not game ticks, saves, menus, rendering, JEI, networking, multiplayer or a dedicated server',
              'output': output.relative_to(ROOT).as_posix(), 'commands': [], 'target_baseline': {'target_head': start['target_head'], 'source_head': start['source_head']}}
    production = tuple(dict.fromkeys((*ms.SOURCES, *world.PRODUCTION, ITEMS)))
    hashes = {p: sha(SOURCE / p) for p in production}
    texts = {p: (SOURCE / p).read_text(encoding='utf-8').replace('\r\n', '\n') for p in production}

    # ---- original facts (read-only) ----
    original_head = subprocess.run(['git', '-c', 'safe.directory=' + original_root.as_posix(), '-C', str(original_root), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    ck(original_head == start['source_head'], f'Original HEAD {original_head} is the recorded baseline {start["source_head"]}')
    facts = ms.original_facts(lambda rel: (original_root / rel).read_text(encoding='utf-8'))
    ms.check_original(facts, ck)
    items, _ = rs20b.registrations(SOURCE)
    defaults = original_defaults(original_root, items)
    ck([d['line'] for d in defaults] == list(range(27, 36)), 'the original default waste rows are FuelPoolRecipes.java:27-35: ' + str([d['line'] for d in defaults]))
    report['original_expectation'] = {'original_head': original_head, 'facts': {k: (list(v) if isinstance(v, tuple) else v) for k, v in facts.items()}, 'fuel_pool_defaults': defaults,
                                      'original_file_sha256': {p: sha(original_root / p) for p in ms.ORIGINAL_FILES}}

    # ---- static freeze ----
    for name, function in static_checks(texts, facts, ck).items(): function(texts)
    constants = depleted_constants(texts[ms.ITEM])
    ck(constants == {'COOL': 0, 'HOT': 1}, 'DepletedFuelItem: COOL = 0, HOT = 1 (original damage 0 cool, 1 hot)')
    neo_defaults = re.findall(r'waste\(NtmItems\.(\w+)\);', ms.body(texts[FUELPOOL], '@Override public void registerDefaults() {'))
    ck(['hbmsntm:' + items[f] for f in neo_defaults] == [d['id'] for d in defaults], 'registerDefaults lists the nine waste items in the original order: ' + str(neo_defaults))
    static_count = len(checks)

    # ---- finite model ----
    model = fm.model(facts['decay_ticks'])
    for w in range(1, 7):
        row = model['water'][str(w)]
        ck(abs(row['drum_expected_ticks'] - row['drum_expected_ticks_direct_sum']) < 1e-6 * row['drum_expected_ticks'],
           f'{w} water: the exact expected full-drum time equals the direct sum ({row["drum_expected_ticks"]:.3f} ticks)')

    # ---- compiled isolated run ----
    expected = {'defaults': ','.join(d['id'] for d in defaults), 'decay': str(facts['decay_ticks']), 'mc.drums': str(MC_DRUMS), 'mc.seed': str(MC_SEED),
                'example': EXAMPLE.as_posix() if EXAMPLE.is_file() else ''}
    expected.update({f'r.{w}': str(fm.r_for(facts['decay_ticks'], w)) for w in range(1, 7)})
    expected_path = output / 'expected.properties'
    expected_path.write_text(''.join(f'{k}={v}\n' for k, v in expected.items()), encoding='utf-8')
    stubs = world.stubs(texts[ms.SERIALIZABLE], items, constants)
    ck(not (set(stubs) & set(world.PRODUCTION)), 'no compiled production source is shadowed by a stand-in')
    paths = []
    for rel, text in stubs.items():
        path = output / 'stubs' / rel; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text + '\n', encoding='utf-8'); paths.append(path)
    generated_stubs = {p.relative_to(output).as_posix(): sha(p) for p in paths}
    fixture = FIXTURE / FIXTURE_REL
    paths += [SOURCE / p for p in world.PRODUCTION] + [fixture]
    argfile = output / 'sources.txt'; argfile.write_text(''.join(f'"{p.as_posix()}"\n' for p in paths), encoding='utf-8')
    classes = output / 'classes'; classes.mkdir()
    own = [Path(__file__).resolve(), FIXTURE / 'machine_stubs.py', FIXTURE / 'machine_static.py', FIXTURE / 'finite_model.py', fixture]
    report.update({'source_sha256': hashes, 'fixture_sha256': {p.relative_to(ROOT).as_posix(): sha(p) for p in own}, 'cache_sha256': {str(GSON): sha(GSON)},
                   'jdk_sha256': {str(p): sha(p) for p in (java, javac)}, 'generated_stubs_sha256': generated_stubs, 'adapter_sha256': adapter_hashes(),
                   'compiled_production': list(world.PRODUCTION), 'service_boundaries': world.STAND_INS,
                   'example_file': {'path': EXAMPLE.relative_to(ROOT).as_posix(), 'sha256': sha(EXAMPLE)} if EXAMPLE.is_file() else 'absent (the example checks did not run)'})
    commands = [[javac, '-J-Duser.language=en', '-encoding', 'UTF-8', '-nowarn', '-cp', GSON, '-d', classes, '@' + str(argfile)],
                [java, '-Duser.language=en', '-ea', '-cp', classpath(classes, GSON), MAIN, output, expected_path, 'all']]
    fixture_counts = None
    for index, command in enumerate(commands):
        code, text = run(command)
        (output / ('compile.log', 'run.log')[index]).write_text(text, encoding='utf-8')
        report['commands'].append({'command': [str(c) for c in command], 'returncode': code, 'output': text})
        report['source_stable_after_run'] = hashes == {p: sha(SOURCE / p) for p in hashes}
        write_report(output, report)
        print(text, end='', flush=True)
        if code or not report['source_stable_after_run']: raise SystemExit(code or 'Production changed during check')
        if index:
            m = re.search(r'(\d+) assertions; (\d+) independent scenarios; (\d+) executed ticks', text)
            if not m: raise SystemExit('Missing evidence counts')
            fixture_counts = dict(zip(('assertions', 'scenarios', 'ticks'), map(int, m.groups())))
    report['counts_fixture'] = fixture_counts

    # ---- Monte Carlo against the model ----
    data = json.loads((output / 'monte-carlo.json').read_text(encoding='utf-8'))
    summary, pooled = monte_carlo_summary(data, model)
    for w, s in summary.items():
        ck(s['slot_samples'] == 12 * MC_DRUMS and s['slot_min'] >= 1, f'{w} water: {s["slot_samples"]} slot samples, every first cooling on tick 1 or later')
        ck(abs(s['slot_z']) <= Z_LIMIT, f'{w} water: mean slot cooling {s["slot_mean_ticks"]:.0f} ticks is within {Z_LIMIT} standard errors of r = {s["r"]} (z {s["slot_z"]:.2f})')
        ck(abs(s['drum_z']) <= Z_LIMIT, f'{w} water: mean full-drum cooling {s["drum_mean_ticks"]:.0f} ticks is within {Z_LIMIT} standard errors of the exact '
                                        f'{s["drum_expected_ticks"]:.0f} (z {s["drum_z"]:.2f})')
    ck(abs(pooled['z']) <= Z_LIMIT, f'pooled over 1..6 water, mean T / r = {pooled["mean_over_r"]:.4f} is within {Z_LIMIT} standard errors of 1 (z {pooled["z"]:.2f})')
    model['isolated_run'] = {'note': 'seeded Monte Carlo of the production updateEntity in the stand-in world (java.util.Random, seed ' + str(MC_SEED) + ' + 1000 * water + drum); '
                                     'statistical agreement only, not game ticks', 'drums_per_water': MC_DRUMS, 'per_water': summary, 'pooled': pooled,
                             'source': (output / 'monte-carlo.json').relative_to(ROOT).as_posix(), 'source_sha256': sha(output / 'monte-carlo.json')}
    (output / 'finite-model.json').write_text(json.dumps(model, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    report['finite_model'] = {'path': (output / 'finite-model.json').relative_to(ROOT).as_posix(), 'sha256': sha(output / 'finite-model.json')}
    report['monte_carlo'] = {'per_water': summary, 'pooled': pooled}
    write_report(output, report)

    # ---- mutations ----
    report['mutations'] = []
    if args.mutations:
        for label, (rel, old, new, fragment) in COMPILED_MUTATIONS.items():
            directory = output / 'mutations' / label
            target = directory / 'src' / rel; target.parent.mkdir(parents=True)
            target.write_text(replaced(texts[rel], old, new, label), encoding='utf-8')
            compiled = directory / 'classes'; compiled.mkdir()
            record = {'label': label, 'kind': 'compiled', 'file': rel, 'expected_fragment': fragment, 'mutated_sha256': sha(target), 'commands': []}
            report['mutations'].append(record)
            for index, command in enumerate([[javac, '-J-Duser.language=en', '-encoding', 'UTF-8', '-nowarn', '-cp', classpath(classes, GSON), '-d', compiled, target],
                                             [java, '-Duser.language=en', '-ea', '-cp', classpath(compiled, classes, GSON), MAIN, directory, expected_path, 'deterministic']]):
                code, out = run(command)
                (directory / ('compile.log', 'run.log')[index]).write_text(out, encoding='utf-8')
                record['commands'].append({'command': [str(c) for c in command], 'returncode': code, 'output': out[-4000:]})
                if index == 0 and code: raise SystemExit(f'Mutation compile failure is not detection: {label}\n' + out)
                if index == 1 and (code == 0 or 'java.lang.AssertionError' not in out or fragment not in out):
                    raise SystemExit(f'Mutation not detected by the expected assertion: {label} (expected "{fragment}")\n' + out)
            record['compiled_successfully'] = True; record['detected'] = True
            print(f'mutation {label}: detected (compiled; expects "{fragment}")', flush=True)
            write_report(output, report)
        for label, (rel, old, new, check_name, fragment) in STATIC_MUTATIONS.items():
            edited = dict(texts); edited[rel] = replaced(texts[rel], old, new, label)
            function = static_checks(edited, facts, rs20b.quiet)[check_name]
            try: function(edited)
            except AssertionError as error:
                if fragment not in str(error): raise SystemExit(f'Mutation {label} failed with the wrong assertion: {error}')
                report['mutations'].append({'label': label, 'kind': 'static ' + check_name, 'file': rel, 'expected_fragment': fragment, 'detected': True, 'message': str(error)})
                print(f'mutation {label}: detected (static; expects "{fragment}")', flush=True)
            else: raise SystemExit('Static mutation not detected: ' + label)
        write_report(output, report)
    report['mutations_detected'] = f'{sum(1 for m in report["mutations"] if m.get("detected"))}/{len(report["mutations"])}'
    report['mutations_total'] = len(report['mutations'])
    report['python_assertions'] = len(checks); report['python_assertion_labels'] = checks
    report['source_sha256_after_run'] = {p: sha(SOURCE / p) for p in hashes}
    report['source_stable_after_run'] = hashes == report['source_sha256_after_run']
    report['original_unchanged'] = {p: sha(original_root / p) == report['original_expectation']['original_file_sha256'][p] for p in ms.ORIGINAL_FILES}
    total = fixture_counts['assertions'] + len(checks)
    report['checks'] = {'total': total, 'fixture': fixture_counts['assertions'], 'static_and_model': len(checks), 'static_freeze': static_count,
                        'scenarios': fixture_counts['scenarios'], 'executed_ticks': fixture_counts['ticks']}
    write_report(output, report)
    if not report['source_stable_after_run'] or not all(report['original_unchanged'].values()): raise SystemExit('Production or original source changed during check')
    print(f"Goal20C machine: {total} assertions ({fixture_counts['assertions']} fixture + {len(checks)} static/model); {fixture_counts['scenarios']} independent scenarios; "
          f"{fixture_counts['ticks']} executed stand-in ticks")
    print(f"Compiled and static mutations detected: {report['mutations_detected']}")
    print(f'finite model: {output / "finite-model.json"}')
    print(f'report: {output / "report.json"}')


if __name__ == '__main__': main()
