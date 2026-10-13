"""Goal19A corroded barrel and gravel_obsidian over the production BarrelBlock, BarrelBlockEntity, FluidTrait release dispatch,
FT_Corrosive/FT_Polluting/FT_VentRadiation and the block items, on the Goal 7B services plus declared chunk services whose
Minecraft/NeoForge bodies are checked in the real NeoForge sources cache first. Existing JDK/Gson; no Gradle, game or downloads."""
from pathlib import Path
import hashlib, json, re, sys, uuid, zipfile
sys.path.insert(0, str(Path(__file__).resolve().parent))
from goal18a_regression.common import ROOT, SOURCE, SOURCES_JAR, sha, jdk, gson, classpath, adapter_hashes, run, write_report
from goal19a_regression.stubs import (barrel_world, PRODUCTION as BARREL_PRODUCTION, EXTRACTED, BARREL, BARREL_BE, NTM_BLOCKS, BE_TYPES,
                                      FT_CORROSIVE, FLUID_TYPE)
from review_fixes.block_stubs import method
from verify_goal7b import PRODUCTION as GOAL7B_PRODUCTION

FIXTURE = Path(__file__).resolve().parent / 'goal19a_regression'
OUT = ROOT / 'build/migration/goal19a/barrel'
MAIN = 'com.hbm.blockentity.machine.storage.Goal19ABarrelRegression'
JAVA_FLAGS = ['-Duser.language=en', '-Duser.country=US', '-ea']

# Minecraft 1.21.1 / NeoForge 21.1.228 bodies the declared services follow: (jar path, method signature, tokens in source order).
CONTRACTS = (
    ('net/minecraft/world/level/chunk/LevelChunk.java', 'public BlockState setBlockState(BlockPos pos, BlockState state, boolean isMoving) {',
     ['levelchunksection.setBlockState(j, k, l, state)', 'blockstate.onRemove(this.level, pos, state, isMoving)', 'state.onPlace(this.level, pos, blockstate, isMoving)',
      'this.getBlockEntity(pos, LevelChunk.EntityCreationType.CHECK)', 'blockentity.isValidBlockState(state)', '((EntityBlock)block).newBlockEntity(pos, state)',
      'this.addAndRegisterBlockEntity(blockentity)', 'return blockstate;']),
    ('net/minecraft/world/level/chunk/LevelChunk.java', 'public BlockEntity getBlockEntity(BlockPos pos, LevelChunk.EntityCreationType creationType) {',
     ['blockentity.isRemoved()', 'this.pendingBlockEntities.remove(pos)', 'creationType == LevelChunk.EntityCreationType.IMMEDIATE', 'this.createBlockEntity(pos)',
      'this.addAndRegisterBlockEntity(blockentity)']),
    ('net/minecraft/world/level/chunk/LevelChunk.java', 'private BlockEntity createBlockEntity(BlockPos pos) {',
     ['blockstate.hasBlockEntity()', 'newBlockEntity(pos, blockstate)']),
    ('net/minecraft/world/level/chunk/LevelChunk.java', 'public void addAndRegisterBlockEntity(BlockEntity blockEntity) {',
     ['this.setBlockEntity(blockEntity)', 'this.updateBlockEntityTicker(blockEntity)']),
    ('net/minecraft/world/level/chunk/LevelChunk.java', 'public void setBlockEntity(BlockEntity blockEntity) {',
     ['blockEntity.getType().isValid(blockstate)', 'blockentity.setRemoved()']),
    ('net/minecraft/world/level/Level.java', 'public BlockEntity getBlockEntity(BlockPos pos) {', ['LevelChunk.EntityCreationType.IMMEDIATE']),
    ('net/minecraft/world/level/Level.java', 'public boolean setBlock(BlockPos pos, BlockState state, int flags, int recursionLeft) {',
     ['levelchunk.setBlockState(pos, state, (flags & 64) != 0)', 'this.markAndNotifyBlock(']),
    ('net/minecraft/world/level/Level.java', 'public boolean destroyBlock(BlockPos pos, boolean dropBlock, @Nullable Entity entity, int recursionLeft) {',
     ['if (dropBlock)', 'this.getBlockEntity(pos)', 'Block.dropResources(', 'this.setBlock(pos, fluidstate.createLegacyBlock(), 3, recursionLeft)']),
    ('net/minecraft/world/level/Level.java', 'public boolean removeBlock(BlockPos pos, boolean isMoving) {',
     ['this.setBlock(pos, fluidstate.createLegacyBlock(), 3 | (isMoving ? 64 : 0))']),
    ('net/minecraft/world/level/block/state/BlockBehaviour.java', 'protected void onRemove(BlockState state, Level level, BlockPos pos, BlockState newState, boolean movedByPiston) {',
     ['state.hasBlockEntity() && !state.is(newState.getBlock())', 'level.removeBlockEntity(pos)']),
    ('net/minecraft/world/level/block/state/BlockBehaviour.java', 'protected void onExplosionHit(',
     ['state.canDropFromExplosion(', 'level.getBlockEntity(pos)', 'state.spawnAfterBreak(', 'state.getDrops(', 'state.onBlockExploded(']),
    ('net/minecraft/world/level/block/state/BlockBehaviour.java', 'public boolean hasBlockEntity() {', ['this.getBlock() instanceof EntityBlock']),
    ('net/minecraft/world/level/block/state/BlockBehaviour.java', 'public BlockBehaviour.Properties strength(float destroyTime, float explosionResistance) {',
     ['this.destroyTime(destroyTime).explosionResistance(explosionResistance)']),
    ('net/minecraft/world/level/block/state/BlockBehaviour.java', 'public BlockBehaviour.Properties explosionResistance(float explosionResistance) {',
     ['Math.max(0.0F, explosionResistance)']),
    ('net/minecraft/world/level/block/Block.java', 'public float getExplosionResistance() {', ['return this.explosionResistance;']),
    ('net/minecraft/world/level/block/Block.java', 'public static void dropResources(\n', ['getDrops(', 'popResource(level, pos,', 'CommonHooks.handleBlockDrops(']),
    ('net/neoforged/neoforge/common/CommonHooks.java', 'public static void handleBlockDrops(', ['if (!event.isCanceled())', 'level.addFreshEntity(entity)', 'state.spawnAfterBreak(']),
    ('net/neoforged/neoforge/common/extensions/IBlockExtension.java', 'default float getExplosionResistance(BlockState state, BlockGetter level, BlockPos pos, Explosion explosion) {',
     ['self().getExplosionResistance()']),
    ('net/neoforged/neoforge/common/extensions/IBlockStateExtension.java', 'default float getExplosionResistance(BlockGetter level, BlockPos pos, Explosion explosion) {',
     ['getExplosionResistance(self(), level, pos, explosion)']),
    ('net/neoforged/neoforge/common/extensions/IBlockExtension.java', 'default void onBlockExploded(BlockState state, Level level, BlockPos pos, Explosion explosion) {',
     ['level.setBlock(pos, Blocks.AIR.defaultBlockState(), 3)', 'self().wasExploded(']),
    ('net/neoforged/neoforge/common/extensions/IBlockExtension.java', 'default boolean onDestroyedByPlayer(', ['level.removeBlock(pos, false)']),
    ('net/neoforged/neoforge/common/extensions/IBlockExtension.java', 'default boolean canDropFromExplosion(BlockState state, BlockGetter level, BlockPos pos, Explosion explosion) {',
     ['state.getBlock().dropFromExplosion(explosion)']),
    ('net/minecraft/server/level/ServerPlayerGameMode.java', 'public boolean destroyBlock(BlockPos pos) {',
     ['this.level.getBlockEntity(pos)', 'block.playerWillDestroy(', 'removeBlock(pos, blockstate, false)', 'removeBlock(pos, blockstate, flag1)', 'block.playerDestroy(']),
    ('net/minecraft/server/level/ServerPlayerGameMode.java', 'private boolean removeBlock(BlockPos pos, BlockState state, boolean canHarvest) {', ['state.onDestroyedByPlayer(']),
    ('net/minecraft/world/Containers.java', 'private static void dropContents(Level level, double x, double y, double z, Container inventory) {',
     ['inventory.getContainerSize()', 'dropItemStack(level, x, y, z, inventory.getItem(i))']),
    ('net/minecraft/world/Containers.java', 'public static void dropItemStack(', ['while (!stack.isEmpty())', 'stack.split(', 'level.addFreshEntity(itementity)']),
    ('net/minecraft/world/level/block/entity/BlockEntity.java', 'public BlockEntity(BlockEntityType<?> type, BlockPos pos, BlockState blockState) {',
     ['this.validateBlockState(blockState)', 'this.blockState = blockState']),
    ('net/minecraft/world/level/block/entity/BlockEntity.java', 'private void validateBlockState(', ['!this.isValidBlockState(', 'throw new IllegalStateException(']),
    ('net/minecraft/world/level/block/entity/BlockEntity.java', 'public boolean isValidBlockState(', ['this.getType().isValid(']),
    ('net/minecraft/world/level/block/entity/BlockEntityType.java', 'public boolean isValid(BlockState state) {', ['this.validBlocks.contains(state.getBlock())']),
    ('net/minecraft/world/item/BlockItem.java', 'public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> tooltipComponents, TooltipFlag tooltipFlag) {',
     ['super.appendHoverText(', 'this.getBlock().appendHoverText(']),
)
# NTM sources outside the compiled set whose behavior the scenarios rely on: key -> (path, regex that must match exactly once).
NTM_ANCHORS = {
    'ntm_explosion_order': ('com/hbm/explosion/vanillant/standard/BlockProcessorStandard.java',
                            r'state\.canDropFromExplosion\([\s\S]*?LootContextParams\.BLOCK_ENTITY, level\.getBlockEntity\(pos\)\)[\s\S]*?state\.getDrops\(builder\)[\s\S]*?state\.onBlockExploded\('),
    'ntm_explosion_chance': ('com/hbm/explosion/vanillant/standard/BlockProcessorStandard.java', r'serverLevel\.random\.nextFloat\(\) <= dropChance'),
    'stray_cog_resistance': ('com/hbm/entity/projectile/StrayCog.java', r'state\.getExplosionResistance\(this\.level, pos, null\) < 50'),
    'blast_info_tooltip': ('com/hbm/items/block/BlastInfoBlockItem.java', r'Component\.translatable\("block\.hbmsntm\.obj_blast_info\.desc", this\.getBlock\(\)\.getExplosionResistance\(\)\)'),
    'corroded_loot_drop_self': ('com/hbm/datagen/NtmBlockLootTableProvider.java', r'this\.dropSelf\(NtmBlocks\.BARREL_CORRODED\.get\(\)\);'),
    'corroded_creative_tab': ('com/hbm/inventory/NtmCreativeTabs.java', r'output\.accept\(NtmBlocks\.BARREL_CORRODED\);'),
    'barrel_item_tooltip': ('com/hbm/items/block/BlockItemBase.java', r'if\(tag\.contains\(IPersistentNBT\.NBT_PERSISTENT_KEY\)\) ipip\.appendHoverText\(stack, tag\.getCompound\(IPersistentNBT\.NBT_PERSISTENT_KEY\)'),
}
# label -> (kind, production path, [(old, new)], scenarios, expected assertion fragment). 'compile': the mutated production file
# is compiled alone over the baseline classes; 'stub': the stand-in generated from the mutated registry text is.
MUTATIONS = {
    'corroded_capacity_6000': ('stub', NTM_BLOCKS, [('.sound(SoundType.METAL), 16_000, true));', '.sound(SoundType.METAL), 6_000, true));')],
                               'registration', 'the corroded barrel holds 16,000 mB'),
    'leak_removed': ('compile', BARREL_BE, [('                this.tank.setFill(Math.max(0, this.tank.getFill() - 1));\n'
                                             '                FluidTrait.onRelease(this.level, this.getBlockPos(), this.tank.getTankType(), this.tank, FluidTrait.FluidReleaseType.SPILL, 1);\n', '')],
                     'leak', 'a 1-in-3 leak removes exactly 1 mB per hit'),
    'self_destruct_keeps_body': ('compile', BARREL_BE, [('no body once shouldDrop is cleared.\n                this.shouldDrop = false;\n', 'no body once shouldDrop is cleared.\n')],
                                 'selfDestruct', 'self-destruct leaves no barrel body'),
    'corroded_remove_drops_slots': ('compile', BARREL, [('if(!this.corroded) Containers.dropContents(level, pos, barrel);', 'Containers.dropContents(level, pos, barrel);')],
                                    'selfDestruct,lifecycle', 'a corroded barrel never drops its slot contents'),
    'replacement_without_prevent_drop': ('compile', BARREL_BE, [('also drop a persistent steel barrel.\n            this.shouldDrop = false;\n', 'also drop a persistent steel barrel.\n')],
                                         'conversion', 'the replacement drops no steel barrel body'),
    'be_type_without_corroded': ('stub', BE_TYPES, [('NtmBlocks.BARREL_CORRODED.get(),\n', '')],
                                 'registration', 'the BARREL block entity type accepts hbmsntm:barrel_corroded'),
    'corroded_block_entity_null': ('compile', BARREL, [('        return new BarrelBlockEntity(pos, state);', '        return this.corroded ? null : new BarrelBlockEntity(pos, state);')],
                                   'registration', 'the corroded barrel creates its block entity'),
    'highly_corrosive_from_50': ('compile', FT_CORROSIVE, [('return rating > 50;', 'return rating >= 50;')], 'sulfuric', 'sulfuric acid (50)'),
    'gravel_resistance_240': ('stub', NTM_BLOCKS, [('.strength(5.0F, 20.0F).sound(SoundType.GRAVEL)', '.strength(5.0F, 240.0F).sound(SoundType.GRAVEL)')],
                              'gravel', 'gravel_obsidian explosion resistance 20'),
    'corroded_plain_loot': ('compile', BARREL, [('        return IPersistentNBT.getDropsFromLootParams(state, params);',
                                                 '        if(this.corroded) return super.getDrops(state, params);\n        return IPersistentNBT.getDropsFromLootParams(state, params);')],
                            'lifecycle', 'the corroded body keeps its persistent tank: vanilla TNT'),
    'corroded_explosion_keeps_drop': ('compile', BARREL, [('        if(level.getBlockEntity(pos) instanceof BarrelBlockEntity barrel) {\n            // The explosion',
                                                           '        if(!this.corroded && level.getBlockEntity(pos) instanceof BarrelBlockEntity barrel) {\n            // The explosion')],
                                      'lifecycle', 'corroded body count 1: NTM standard'),
    'corroded_break_loot_keeps_drop': ('compile', BARREL, [('        if(level.getBlockEntity(pos) instanceof BarrelBlockEntity barrel) {\n            // destroyBlock(true)',
                                                            '        if(!this.corroded && level.getBlockEntity(pos) instanceof BarrelBlockEntity barrel) {\n            // destroyBlock(true)')],
                                       'lifecycle', 'corroded body count 1: destroyBlock(true)'),
    'removed_barrel_still_synced': ('compile', BARREL_BE, [('            if(this.isRemoved()) return;\n', '')],
                                    'conversion', 'the replaced steel block entity sends no stale sync'),
    'fluid_type_highly_corrosive_any_rating': ('stub', FLUID_TYPE, [('return this.traits.containsKey(FT_Corrosive.class) && ((FT_Corrosive) this.traits.get(FT_Corrosive.class)).isHighlyCorrosive();',
                                                                     'return this.traits.containsKey(FT_Corrosive.class);')],
                                               'sulfuric', 'sulfuric acid (50) leaves a steel barrel unchanged'),
    'replacement_without_fill': ('compile', BARREL_BE, [('                corroded.tank.setFill(fill);\n', '')],
                                 'conversion', 'the corroded barrel keeps the fluid type and fill'),
    'replacement_without_type': ('compile', BARREL_BE, [('                corroded.tank.setTankType(type);\n', '')],
                                 'conversion', 'the corroded barrel keeps the fluid type and fill'),
    'corroded_tooltip_old_lines': ('compile', BARREL, [('        if(this.corroded) {\n            components.add(Component.translatable("desc.leaky")',
                                                        '        if(this.corroded) {\n'
                                                        '            components.add(Component.translatable("desc.canhot").withStyle(ChatFormatting.GREEN));\n'
                                                        '            components.add(Component.translatable("desc.canhighcor").withStyle(ChatFormatting.GREEN));\n'
                                                        '            components.add(Component.translatable("desc.cannotam").withStyle(ChatFormatting.YELLOW));\n'
                                                        '            components.add(Component.translatable("desc.leaky")')],
                                   'tooltip', 'the corroded tooltip has two lines'),
}


def line_of(text, offset):
    return text.count('\n', 0, offset) + 1


def engine_contracts():
    """Each declared service's 1.21.1 body, located in the real sources cache with its tokens in source order."""
    if not SOURCES_JAR.is_file():
        raise SystemExit(f'Real NeoForge sources cache missing ({SOURCES_JAR}); the engine contracts cannot be checked')
    records = []
    with zipfile.ZipFile(SOURCES_JAR) as archive:
        for path, signature, tokens in CONTRACTS:
            text = archive.read(path).decode('utf-8').replace('\r\n', '\n')
            body = method(text, signature)
            start = text.index(body)
            positions = []
            for token in tokens:
                index = body.find(token, positions[-1] + 1 if positions else 0)
                if index < 0:
                    raise SystemExit(f'Engine contract drift: {path}: "{token}" missing or out of order')
                positions.append(index)
            records.append({'source': path, 'signature': signature.strip(), 'start_line': line_of(text, start), 'end_line': line_of(text, start + len(body)),
                            'ordered': [{'token': t, 'line': line_of(text, start + i)} for t, i in zip(tokens, positions)],
                            'sha256': hashlib.sha256(body.encode('utf-8')).hexdigest()})
    return records


def ntm_anchors():
    resolved = {}
    for key, (rel, pattern) in NTM_ANCHORS.items():
        text = (SOURCE / rel).read_text(encoding='utf-8').replace('\r\n', '\n')
        found = list(re.finditer(pattern, text))
        if len(found) != 1:
            raise SystemExit(f'NTM anchor {key} matched {len(found)} times in {rel}')
        start, end = line_of(text, found[0].start()), line_of(text, found[0].end())
        resolved[key] = {'path': 'src/main/java/' + rel, 'lines': f'{start}' if start == end else f'{start}-{end}', 'sha256': sha(SOURCE / rel)}
    return resolved


def mutate(text, pairs, label):
    for old, new in pairs:
        if text.count(old) != 1:
            raise SystemExit(f'Mutation anchor missing or not unique: {label}: {old[:70]}')
        text = text.replace(old, new, 1)
    return text


def main():
    output = OUT / uuid.uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    java, javac = jdk(); GSON = gson()
    contracts = engine_contracts()
    captured = {}
    original_text, original_bytes = Path.read_text, Path.read_bytes
    def capture(path):
        absolute = path.resolve()
        if absolute.is_relative_to(SOURCE):
            rel = absolute.relative_to(SOURCE).as_posix(); digest = hashlib.sha256(original_bytes(absolute)).hexdigest()
            if rel in captured and captured[rel] != digest: raise SystemExit('Source changed while building services: ' + rel)
            captured[rel] = digest
    def read_text(path, *a, **k): value = original_text(path, *a, **k); capture(path); return value
    def read_bytes(path, *a, **k): value = original_bytes(path, *a, **k); capture(path); return value
    Path.read_text, Path.read_bytes = read_text, read_bytes
    try: stubs, facts = barrel_world(SOURCE)
    finally: Path.read_text, Path.read_bytes = original_text, original_bytes
    production = tuple(dict.fromkeys((*GOAL7B_PRODUCTION, *BARREL_PRODUCTION)))
    if set(production) & set(stubs): raise SystemExit('Production shadowed by service: ' + str(sorted(set(production) & set(stubs))))
    anchors = ntm_anchors()
    hashes = {p: sha(SOURCE / p) for p in dict.fromkeys((*production, *EXTRACTED, *(a['path'][len('src/main/java/'):] for a in anchors.values())))}
    if captured != {p: sha(SOURCE / p) for p in captured}: raise SystemExit('Source changed during adapter generation')
    hashes.update(captured)
    paths = []
    for rel, text in stubs.items():
        path = output / 'stubs' / rel; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text + '\n', encoding='utf-8'); paths.append(path)
    fixture = FIXTURE / 'Goal19ABarrelRegression.java'
    paths += [SOURCE / p for p in production] + [fixture]
    report = {'evidence': 'Production BarrelBlock, BarrelBlockEntity, FluidTrait (release dispatch), FT_Corrosive, FT_Polluting, FT_VentRadiation, FluidTraitSimple, '
                          'IPersistentNBT, BlockItemBase and BlastInfoBlockItem compiled whole with the Goal 7B production list (MachineBaseBlockEntity, FluidTank, '
                          'FluidContainerRegistry, fluid network) over explicit engine services; not game, save, GUI, multiplayer or dedicated-server acceptance',
              'sources_jar': {'path': str(SOURCES_JAR), 'kind': 'neoforge-sources-cache', 'sha256': sha(SOURCES_JAR)},
              'engine_contracts': contracts, 'ntm_anchors': anchors, 'parsed_production_facts': facts,
              'source_sha256': hashes, 'extracted_source_sha256': captured, 'fixture_sha256': {fixture.relative_to(ROOT).as_posix(): sha(fixture)},
              'cache_sha256': {str(GSON): sha(GSON)}, 'jdk_sha256': {str(p): sha(p) for p in (java, javac)},
              'compiled_input_sha256': {str(p): sha(p) for p in paths}, 'commands': [],
              'service_boundaries': [
                  'Level/ServerLevel: per-position states and block entities. setBlock follows LevelChunk.setBlockState (new state written, old onRemove with the old '
                  'block entity reachable, block entity kept if valid or created for the new state before returning); getBlockEntity follows the IMMEDIATE creation of '
                  'LevelChunk.getBlockEntity; destroyBlock/removeBlock follow Level.destroyBlock/removeBlock. No chunk saving, loading, ticking lists, lighting, '
                  'neighbour updates or client sync are modeled; tickers are taken from the block\'s getTicker and called by the fixture',
                  'Block/BlockBehaviour/BlockState: onRemove removes the block entity on a block change; onBlockExploded sets air; canDropFromExplosion is true; the '
                  'default loot is the dropSelf body (one plain item, NtmBlockLootTableProvider); dropResources = loot then spawnAfterBreak; item entities, the '
                  'BlockDropsEvent and gamerules are not modeled (drops are recorded)',
                  'Player break, vanilla explosion and NTM BlockProcessorStandard explosion are fixture orchestrations of the cited bodies (engine_contracts, ntm_anchors)',
                  'BlockEntity validates its state against BlockEntityType.isValid; the BARREL valid blocks and the barrel/gravel_obsidian registration rows are parsed '
                  'from production NtmBlockEntityTypes/NtmBlocks (parsed_production_facts); the other machines\' stand-in types are unrestricted',
                  'FluidType is a stand-in carrying the production addTraits/hasTrait/getTrait/isHot/isCorrosive/isHighlyCorrosive/isAntimatter bodies; NITRIC_ACID, '
                  'SULFURIC_ACID, WATZ and SCHRABIDIC get the corrosive, vent-radiation, polluting, liquid and viscous traits parsed from their Fluids.java rows',
                  'PollutionHandler.incrementPollution and ChunkRadiationManager.proxy.incrementRad record their calls; RandomSource records every nextInt bound and is '
                  'scripted per bound in the deterministic checks, seeded for the rate check',
                  'Containers.dropContents records each non-empty slot as one dropped stack and empties it; CompatExternal.getCoreFromPos is the block entity at the '
                  'position (barrels are not DummyableBlocks)']}
    report['adapter_sha256'] = adapter_hashes()
    report['generated_files_sha256'] = {p.relative_to(ROOT).as_posix(): sha(p) for p in paths if p.is_relative_to(output)}
    argfile = output / 'sources.txt'; argfile.write_text(''.join(f'"{p.as_posix()}"\n' for p in paths), encoding='utf-8')
    classes = output / 'classes'; classes.mkdir()
    commands = [[javac, '-J-Duser.language=en', '-encoding', 'UTF-8', '-nowarn', '-cp', GSON, '-d', classes, '@' + str(argfile)],
                [java, *JAVA_FLAGS, '-cp', classpath(classes, GSON), MAIN, output]]
    print(output, flush=True)
    for index, command in enumerate(commands):
        code, text = run(command)
        (output / ('compile.log', 'barrel.log')[index]).write_text(text, encoding='utf-8')
        report['commands'].append({'command': [str(c) for c in command], 'returncode': code, 'output': text})
        report['source_stable_after_run'] = hashes == {p: sha(SOURCE / p) for p in hashes}
        write_report(output, report)
        print(text, end='', flush=True)
        if code or not report['source_stable_after_run']: raise SystemExit(code or 'Production changed during check')
        if index:
            counts = re.search(r'(\d+) assertions; (\d+) independent scenarios; (\d+) executed ticks', text)
            if not counts: raise SystemExit('Missing evidence counts')
            report['barrel_counts'] = dict(zip(('assertions', 'scenarios', 'ticks'), map(int, counts.groups())))
    write_report(output, report)

    report['mutations'] = []
    for label, (kind, rel, pairs, scenarios, expected) in MUTATIONS.items():
        directory = output / 'mutations' / label
        original = (SOURCE / rel).read_text(encoding='utf-8').replace('\r\n', '\n')
        mutated = mutate(original, pairs, label)
        if kind == 'compile':
            targets = {rel: mutated}
        else:
            changed, _ = barrel_world(SOURCE, {rel: mutated})
            targets = {name: text + '\n' for name, text in changed.items() if text != stubs.get(name)}
            if not targets: raise SystemExit('Registry mutation changed no stand-in: ' + label)
        files = []
        for name, text in targets.items():
            target = directory / 'src' / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_text(text, encoding='utf-8'); files.append(target)
        compiled = directory / 'classes'; compiled.mkdir()
        record = {'label': label, 'kind': kind, 'production_file': 'src/main/java/' + rel, 'scenarios': scenarios, 'expected_assertion': expected,
                  'expected_behavior_failure': True, 'generated_files_sha256': {f.relative_to(ROOT).as_posix(): sha(f) for f in files}, 'commands': []}
        report['mutations'].append(record)
        for index, command in enumerate([[javac, '-J-Duser.language=en', '-encoding', 'UTF-8', '-nowarn', '-cp', classpath(classes, GSON), '-d', compiled, *files],
                                         [java, *JAVA_FLAGS, '-cp', classpath(compiled, classes, GSON), MAIN, directory, scenarios]]):
            code, out = run(command)
            (directory / ('compile.log', 'run.log')[index]).write_text(out, encoding='utf-8')
            record['commands'].append({'command': [str(c) for c in command], 'returncode': code, 'output': out})
            report['source_stable_after_run'] = hashes == {p: sha(SOURCE / p) for p in hashes}
            write_report(output, report)
            if not report['source_stable_after_run']: raise SystemExit('Source changed during mutation')
            if index == 0 and code: raise SystemExit('Mutation compile failure is not detection: ' + label + '\n' + out)
            if index == 1:
                failure = re.search(r'java\.lang\.AssertionError: (.*)', out)
                if code == 0 or not failure: raise SystemExit('Mutation not detected by behavioral assertion: ' + label + '\n' + out)
                record['assertion'] = failure.group(1).strip()
                if expected not in record['assertion']: raise SystemExit(f'Mutation {label} detected by an unexpected assertion: {record["assertion"]}')
        record['compiled_successfully'] = True; record['behavior_mutation_detected'] = True
        print(f'mutation {label}: detected -> {record["assertion"]}', flush=True)
    report['mutations_detected'] = len(MUTATIONS)
    print(f'Compiled barrel behavior mutations detected: {len(MUTATIONS)}/{len(MUTATIONS)}')
    write_report(output, report)
    print(output / 'report.json')


if __name__ == '__main__': main()
