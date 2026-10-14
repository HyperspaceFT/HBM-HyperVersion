package abilityharvest;

import java.util.*;
import java.util.function.*;

/**
 * Drops batch, method level and not a real Minecraft world: exactly one body per DummyableBlock multiblock under ability mining, area
 * extras and explosions; one BreakEvent, before anything else happens there, for every extra block an area ability breaks; and
 * BlockProcessorStandard following only emitted loot with spawnAfterBreak. Its follow-up covers breakExtraBlock's effectiveness gate
 * (no extra block the held tool is not effective for, unless SILK, and none with an empty hand; skipped blocks get no BreakEvent, removal
 * or wear) and DummyableBlock.onRemove's core check (a core never removes the same-block neighbour behind it; a dummy still removes the
 * part toward the core). Expectations come from the world before each action.
 */
final class DropsBatchRegression {
    private DropsBatchRegression() {}

    static final MachineRefineryBlock REFINERY = new MachineRefineryBlock("machine_refinery");
    static final LootMachineBlock LOOT_MACHINE = new LootMachineBlock();
    static final MachineCentrifugeBlock CENTRIFUGE = new MachineCentrifugeBlock("machine_centrifuge");
    static final List<DummyableBlock> MACHINES = List.of(REFINERY, LOOT_MACHINE, CENTRIFUGE);
    static final Block GAS = new Block("gas_asbestos");
    static final OutgasBlock ASBESTOS = new OutgasBlock("brick_asbestos", true, GAS);
    static final InfestedBlock INFESTED = new InfestedBlock("infested_stone", Blocks.STONE);
    /** Needs a tool but is not pickaxe-mineable: fails breakExtraBlock's tool check. */
    static final Block DIRT = new Block("dirt_like");
    /** 2.5 times as hard as the reference block: fails the strength check. */
    static final Block HARD = hardness("hard_ore", 0.02F);
    /** Exactly twice as hard: passes, as the check is refStrength / strength > 2f. */
    static final Block EVEN = hardness("even_ore", 0.025F);
    static final GameMasterOre MASTER = new GameMasterOre();
    /** Need no tool and are not pickaxe-mineable, like coal gas, glass or a torch: they pass hasCorrectToolForDrops but fail the effectiveness gate. */
    static final Block COAL_GAS = noTool("coal_gas", false), GLASS = noTool("glass_like", false);
    /** Needs no tool and is pickaxe-mineable: passes every check except an empty hand. */
    static final Block FREE_ORE = noTool("free_ore", true);
    /** A plant shears can cut: not effective for the pickaxe, so only shears (or SILK) make it an extra. */
    static final PlantBlock PLANT = new PlantBlock();
    /** A two-block machine like MachinePressBlock (dimensions {2,0,0,0,0,0}): a core with a block entity and one dummy above it. */
    static final PressBlock PRESS = new PressBlock();
    static final BlockPos ORIGIN = AbilityHarvestRegression.ORIGIN;

    static int sameStructureRemovals, secondBodies, secondWhileMinedPresent, areaBlocksBroken, cancelledExtras, preCancelledExtras,
            skippedExtras, emittedLootPasses, failedRolls, corelessBodies, explosionMinedCore, explosionMinedPart, explosionFromOre, footprintAreaRuns,
            footprintCancelRuns, corelessColumnBodies, corelessColumnPartial, corelessColumnMultiple, allCancelledRuns, instabuildRuns,
            gateSkipped, gatePassed, emptyHandRuns, veinSilkRuns, coreRemovalRuns, dummyChainRuns;

    static void check(boolean condition, String label) { AbilityHarvestRegression.check(condition, label); }

    static Block hardness(String name, float progress) {
        Block block = new Block(name).mineable();
        block.destroyProgress = progress;
        return block;
    }

    static Block noTool(String name, boolean pickaxeMineable) {
        Block block = new Block(name);
        if(pickaxeMineable) block.mineable();
        block.requiresTool = false;
        return block;
    }

    static final class PlantBlock extends Block implements IShearable {
        PlantBlock() { super("plant_like"); requiresTool = false; }
        public boolean isShearable(Player player, ItemStack stack, Level level, BlockPos pos) { return true; }
    }

    /** Like LootMachineBlock: any part drops one plain body, only the core has a block entity. */
    static final class PressBlock extends DummyableBlock {
        PressBlock() { super("machine_press"); }
        public BlockEntity newBlockEntity(BlockPos pos, BlockState state) { return isCore(state) ? new BlockEntity(pos) : null; }
    }

    /** A breakable game-master block, so fireBlockBreak's game-master pre-cancel is reachable past the strength check. */
    static final class GameMasterOre extends Block implements GameMasterBlock { GameMasterOre() { super("game_master_ore"); mineable(); } }

    /** Stand-in for a multiblock whose loot table drops one plain body for any part (the default getDrops); only its core has a block entity. */
    static final class LootMachineBlock extends DummyableBlock {
        LootMachineBlock() { super("loot_machine"); }
        public BlockEntity newBlockEntity(BlockPos pos, BlockState state) { return isCore(state) ? new BlockEntity(pos) : null; }
    }

    /** Every scenario starts from the default config, no BreakEvent listener, a fixed shuffle seed and no allocated explosion. */
    static ServerLevel world(boolean keepContents, long seed) {
        ServerLevel level = AbilityHarvestRegression.world(keepContents);
        NeoForge.EVENT_BUS.listeners.clear();
        BlockAllocatorStandard.next = List.of();
        Collections.random = new Random(seed);
        check(!DummyableBlock.safeRem, "safeRem is clear between scenarios");
        return level;
    }

    // region multiblocks
    /** One multiblock part: offset from the core, FACING (the step toward the core is its opposite) and type. */
    record Part(int dx, int dy, int dz, Direction facing, DummyBlockType type) {}

    /** Three wide and two high; two parts reach the core through another part. */
    static final List<Part> WIDE = List.of(
            new Part(0, 0, 0, Direction.NORTH, DummyBlockType.CORE), new Part(1, 0, 0, Direction.EAST, DummyBlockType.DUMMY),
            new Part(-1, 0, 0, Direction.WEST, DummyBlockType.EXTRA), new Part(0, 1, 0, Direction.UP, DummyBlockType.DUMMY),
            new Part(1, 1, 0, Direction.UP, DummyBlockType.DUMMY), new Part(-1, 1, 0, Direction.UP, DummyBlockType.EXTRA));
    /** The centrifuge's four-high column. */
    static final List<Part> COLUMN = List.of(
            new Part(0, 0, 0, Direction.NORTH, DummyBlockType.CORE), new Part(0, 1, 0, Direction.UP, DummyBlockType.DUMMY),
            new Part(0, 2, 0, Direction.UP, DummyBlockType.EXTRA), new Part(0, 3, 0, Direction.UP, DummyBlockType.DUMMY));

    /** The press: its core, facing `facing`, and one dummy above it. */
    static List<Part> pressLayout(Direction facing) {
        return List.of(new Part(0, 0, 0, facing, DummyBlockType.CORE), new Part(0, 1, 0, Direction.UP, DummyBlockType.DUMMY));
    }

    static List<Part> layout(DummyableBlock block) { return block == CENTRIFUGE ? COLUMN : block == PRESS ? pressLayout(Direction.NORTH) : WIDE; }

    static final class Structure {
        final DummyableBlock block;
        final BlockPos core;
        final Map<BlockPos, BlockState> parts = new LinkedHashMap<>();
        final Map<BlockPos, BlockEntity> entities = new HashMap<>();
        ItemStack body;
        Structure(DummyableBlock block, BlockPos core) { this.block = block; this.core = core; }
        boolean contains(BlockPos pos) { return parts.containsKey(pos); }
        List<BlockPos> positions() { return new ArrayList<>(parts.keySet()); }
    }

    /** Places a multiblock with the block entities its block creates per part; its body is taken now through the side-effect-free path. */
    static Structure place(ServerLevel level, DummyableBlock block, BlockPos core, String data) {
        return place(level, block, core, data, layout(block));
    }

    static Structure place(ServerLevel level, DummyableBlock block, BlockPos core, String data, List<Part> layout) {
        Structure structure = new Structure(block, core);
        for(Part part : layout) {
            BlockPos pos = core.offset(part.dx(), part.dy(), part.dz());
            BlockState state = switch(part.type()) {
                case CORE -> block.createCoreState(part.facing());
                case DUMMY -> block.createDummyState(part.facing());
                case EXTRA -> block.createExtraState(part.facing());
            };
            check(level.getBlockState(pos).isAir(), "layout overlaps at " + pos);
            level.states.put(pos, state);
            BlockEntity be = block.newBlockEntity(pos, state);
            if(be instanceof MachineRefineryBlockEntity refinery) refinery.tanks = data;
            if(be != null) { be.level = level; level.blockEntities.put(pos, be); }
            structure.parts.put(pos, state);
            structure.entities.put(pos, be);
        }
        if(block == REFINERY) {
            check(structure.entities.values().stream().filter(Objects::nonNull).count() == 3, "refinery: a core block entity and two proxies, none on DUMMY parts");
            structure.body = IPersistentNBT.getDrops(level, core, block).getFirst();
            check(structure.body.customData != null && structure.body.customData.contains(IPersistentNBT.NBT_PERSISTENT_KEY), "refinery body carries its tanks");
        } else {
            structure.body = new ItemStack(block);
        }
        return structure;
    }

    /** Every part of every structure resolves its own core before the action. */
    static void ready(Level level, Structure... structures) {
        for(Structure s : structures) for(BlockPos pos : s.parts.keySet())
            check(s.core.equals(s.block.findCore(level, pos)), s.block + ": part " + pos + " resolves its core " + s.core);
    }

    enum Fate { BODY, NO_BODY, INTACT }

    /** A structure is untouched, or gone with all its block entities having dropped no body or exactly its one body (at `at` when given). */
    static void fate(String label, Level level, Structure s, Fate fate, BlockPos at) {
        List<Drop> bodies = level.drops.stream().filter(d -> s.contains(d.pos()) && d.stack().item == s.block).toList();
        String name = label + ": " + s.block + " at " + s.core;
        if(fate == Fate.INTACT) {
            for(BlockPos pos : s.parts.keySet()) {
                BlockEntity be = s.entities.get(pos);
                check(level.getBlockState(pos) == s.parts.get(pos) && level.getBlockEntity(pos) == be && (be == null || !be.isRemoved()), name + " untouched at " + pos);
            }
            check(bodies.isEmpty(), name + " untouched drops no body " + bodies);
            return;
        }
        for(BlockPos pos : s.parts.keySet()) {
            BlockEntity be = s.entities.get(pos);
            check(level.getBlockState(pos).isAir() && level.getBlockEntity(pos) == null && (be == null || be.isRemoved()),
                    name + " fully removed at " + pos + " " + level.getBlockState(pos));
        }
        if(fate == Fate.NO_BODY) {
            check(bodies.isEmpty(), name + " drops no body " + bodies);
            return;
        }
        check(bodies.size() == 1, name + " drops exactly one body " + bodies);
        check(AbilityHarvestRegression.same(bodies.getFirst().stack(), s.body), name + " drops its own body " + bodies.getFirst().stack() + " expected " + s.body);
        if(at != null) check(bodies.getFirst().pos().equals(at), name + " body at " + at + ", not " + bodies.getFirst().pos());
    }

    /** States and block entities of positions that must stay untouched. */
    static final class Snapshot {
        final Map<BlockPos, BlockState> states = new HashMap<>();
        final Map<BlockPos, BlockEntity> entities = new HashMap<>();
        Snapshot(Level level, Collection<BlockPos> positions) {
            for(BlockPos pos : positions) { states.put(pos, level.getBlockState(pos)); entities.put(pos, level.getBlockEntity(pos)); }
        }
        Snapshot only(Collection<BlockPos> keep) {
            Snapshot s = new Snapshot(new Level(), List.of());
            for(BlockPos pos : keep) { s.states.put(pos, states.get(pos)); s.entities.put(pos, entities.get(pos)); }
            return s;
        }
        void verify(String label, Level level) {
            for(BlockPos pos : states.keySet()) {
                BlockEntity be = entities.get(pos);
                check(level.getBlockState(pos) == states.get(pos) && level.getBlockEntity(pos) == be && (be == null || !be.isRemoved()), label + ": untouched at " + pos);
                if(be instanceof CrateBaseBlockEntity crate) check(crate.shouldDrop(), label + ": untouched crate keeps its drop flag at " + pos);
                if(be instanceof BarrelBlockEntity barrel) check(barrel.shouldDrop(), label + ": untouched barrel keeps its drop flag at " + pos);
            }
        }
    }

    /** Exact drops at each broken non-machine block, only bodies inside machines, slot contents once, and the kept blocks untouched. */
    static void others(String label, Level level, Map<BlockPos, AbilityHarvestRegression.Expect> broken, Snapshot kept, List<Structure> structures) {
        Map<BlockPos, List<ItemStack>> dropped = new HashMap<>();
        for(Drop drop : level.drops) dropped.computeIfAbsent(drop.pos(), p -> new ArrayList<>()).add(drop.stack());
        for(Map.Entry<BlockPos, List<ItemStack>> entry : dropped.entrySet()) {
            Structure owner = structures.stream().filter(s -> s.contains(entry.getKey())).findFirst().orElse(null);
            if(owner != null) check(entry.getValue().stream().allMatch(stack -> stack.item == owner.block), label + ": only its body drops inside a machine at " + entry.getKey() + " " + entry.getValue());
            else check(broken.containsKey(entry.getKey()), label + ": drops only at broken blocks " + entry.getKey() + " " + entry.getValue());
        }
        int slots = 0;
        for(Map.Entry<BlockPos, AbilityHarvestRegression.Expect> entry : broken.entrySet()) {
            BlockPos pos = entry.getKey();
            List<ItemStack> got = dropped.getOrDefault(pos, List.of());
            check(AbilityHarvestRegression.sameMultiset(got, entry.getValue().drops()), label + ": own drops at " + pos + " " + got + " expected " + entry.getValue().drops());
            check(level.getBlockState(pos).isAir() && level.getBlockEntity(pos) == null, label + ": removed with its block entity at " + pos);
            slots += entry.getValue().slots();
        }
        check(level.slotDrops == slots, label + ": slot contents drop once: " + level.slotDrops + " expected " + slots);
        check(level.containerDrops == 0 && !level.skippedNeighborUpdates, label + ": no container drops or skipped neighbor updates in this world");
        kept.verify(label, level);
    }
    // endregion

    // region mining
    /** One breakExtraBlock call: what stood there, whether it passes the checks before the BreakEvent, its journal window and what stood after. */
    record Probe(BlockPos pos, BlockState state, BlockEntity be, BlockState ref, boolean passes, int from, int to, BlockState stateAfter, BlockEntity beAfter,
                 boolean beRemovedAfter) {}

    /** The ability tool, recording each extra-block call around the production breakExtraBlock. */
    static final class ProbeTool extends ToolAbilityItem {
        final List<Probe> probes = new ArrayList<>();
        @Override public void breakExtraBlock(Level level, BlockPos pos, Player player, BlockPos refPos) {
            BlockState state = level.getBlockState(pos), refState = level.getBlockState(refPos);
            BlockEntity be = level.getBlockEntity(pos);
            // The expected checks: neither block is air, a non-empty hand, a block the pickaxe is effective for (SILK takes any block; shears
            // take a shearable one), the right tool, and at most twice as hard as the reference (NEO keeps 2f; the original uses 10f, which is
            // out of scope here).
            boolean silk = config.getActivePreset().harvestAbility == IToolHarvestAbility.SILK;
            boolean effective = state.is(BlockTags.MINEABLE_WITH_PICKAXE) && player.hasCorrectToolForDrops(state);
            boolean gate = !player.getMainHandItem().isEmpty() && (silk || effective || (isShears && state.getBlock() instanceof IShearable));
            boolean passes = !state.isAir() && !refState.isAir() && gate && player.hasCorrectToolForDrops(state)
                    && !(refState.getDestroyProgress(player, level, refPos) / state.getDestroyProgress(player, level, pos) > 2f);
            int from = level.journal.size();
            super.breakExtraBlock(level, pos, player, refPos);
            probes.add(new Probe(pos, state, be, refState, passes, from, level.journal.size(), level.getBlockState(pos), level.getBlockEntity(pos),
                    be != null && be.isRemoved()));
        }
    }

    static ServerPlayer miner(ServerLevel level, IToolAreaAbility area, int areaLevel, IToolHarvestAbility harvest, GameType mode) {
        ProbeTool item = new ProbeTool();
        item.config = new Configuration(new ToolPreset(area, areaLevel, harvest, 2));
        ServerPlayer player = new ServerPlayer(level, new ItemStack(item));
        player.setGameMode(mode);
        return player;
    }

    /**
     * Mines `main` and checks the extra-block contract: a block that fails the checks fires nothing and changes nothing; one that passes
     * fires exactly one BreakEvent with its own position, state and the player's game mode before anything else happens; a cancelled one
     * stays as it was and wears nothing. Durability is the pre-fix value: one for the mined block outside creative (harvestBlock wears the
     * tool even when the block is already gone) plus one per uncancelled extra that passed the checks. A holder with infinite materials
     * (creative, or survival with instabuild) takes no wear, as ItemStack.hurtAndBreak skips it.
     */
    static List<Probe> mine(String label, ServerLevel level, ServerPlayer player, BlockPos main, Predicate<Probe> cancelled) {
        ItemStack tool = player.getMainHandItem();
        ProbeTool item = (ProbeTool) tool.getItem();
        Map<String, Integer> enchantments = new TreeMap<>(tool.enchantments);
        int before = tool.damage;
        AbilityHarvestRegression.destroyBlock(level, player, main);
        check(tool.enchantments.equals(enchantments), label + ": tool enchantments restored " + tool.enchantments);
        check(!TagsUtil.getCustomData(tool).contains(IToolHarvestAbility.LUCK_BASE_FORTUNE_TAG), label + ": luck bookkeeping removed");
        GameType mode = player.gameMode.getGameModeForPlayer();
        int passed = 0, kept = 0;
        for(Probe p : item.probes) {
            List<Step> window = level.journal.subList(p.from(), p.to());
            String at = label + ": extra " + p.pos() + " " + p.state();
            if(!p.passes()) {
                check(window.isEmpty(), at + " fails the air, tool or strength check: no BreakEvent and no effect " + window);
                if(!p.state().isAir() && !p.ref().isAir()) skippedExtras++;
                continue;
            }
            passed++;
            Step first = window.isEmpty() ? null : window.getFirst();
            check(first != null && first.kind().equals("event") && first.pos().equals(p.pos()), at + " fires its BreakEvent before any drop, removal, damage or spawnAfterBreak " + window);
            check(window.stream().filter(s -> s.kind().equals("event")).count() == 1, at + " fires exactly one BreakEvent " + window);
            BreakEvent event = (BreakEvent) first.detail();
            BreakRecord record = level.breakEvents.stream().filter(r -> r.event() == event).findFirst().orElseThrow();
            check(event.state == p.state() && event.player == player && record.gameType() == mode, at + " event carries its own state and the player's game mode " + record);
            boolean cancel = cancelled.test(p);
            check(event.isCanceled() == cancel, at + " cancelled exactly as the scenario chose: " + event.isCanceled());
            if(cancel) {
                kept++;
                cancelledExtras++;
                if(record.preCanceled()) preCancelledExtras++;
                check(window.size() == 1, at + " cancelled: no drop, removal, damage or spawnAfterBreak " + window);
                check(p.stateAfter() == p.state() && p.beAfter() == p.be() && !p.beRemovedAfter(), at + " cancelled: state and block entity unchanged");
                check(player.connection.sent.contains(new BlockUpdatePacket(p.pos(), p.state())), at + " cancelled: the client is told the block stays");
            } else {
                check(window.stream().filter(s -> s.kind().equals("damage")).count() == 1, at + " wears the tool once " + window);
                check(p.stateAfter().isAir(), at + " is broken");
            }
        }
        int expected = player.hasInfiniteMaterials() ? 0 : 1 + passed - kept;
        check(tool.damage - before == expected, label + ": durability " + (tool.damage - before) + " expected " + expected);
        check(level.breakEvents.size() == passed, label + ": one BreakEvent per extra that passed the checks: " + level.breakEvents.size() + " expected " + passed);
        check(level.breakEvents.stream().noneMatch(r -> r.event().pos.equals(main)), label + ": breakExtraBlock fires no BreakEvent for the mined block");
        return item.probes;
    }

    /**
     * A survival player with instabuild (hasInfiniteMaterials) mines a cored multiblock with a harvest preset, directly and with the
     * hammer: playerWillDestroy drops nothing, mineBlock's skip branch harvests nothing and same-structure extras are removed without
     * loot, so no body drops. The extracted code still calls damageTool once for the mined part and once per uncancelled extra (the
     * journal counts them), and hurtAndBreak applies no wear.
     */
    static void instabuildSurvival() {
        for(DummyableBlock machine : List.of(REFINERY, LOOT_MACHINE))
        for(String areaName : List.of("NONE", "HAMMER"))
        for(int part = 0; part < WIDE.size(); part++)
        for(Map.Entry<String, IToolHarvestAbility> harvest : harvests("SILK", "LUCK", "SMELTER", "SHREDDER", "MERCURY").entrySet()) {
            ServerLevel level = world(true, 0);
            level.clipResult = new BlockHitResult(Direction.UP);
            Structure s1 = place(level, machine, ORIGIN, "S1");
            ready(level, s1);
            ServerPlayer player = miner(level, areaName.equals("HAMMER") ? IToolAreaAbility.HAMMER : IToolAreaAbility.NONE, 0, harvest.getValue(), GameType.SURVIVAL);
            player.instabuild = true;
            check(player.hasInfiniteMaterials() && !player.gameMode.isCreative(), "instabuild survival player");
            BlockPos main = s1.positions().get(part);
            String label = "instabuild survival " + machine + " " + areaName + " from " + main + " " + harvest.getKey();
            List<Probe> probes = mine(label, level, player, main, p -> false);
            long passed = probes.stream().filter(Probe::passes).count();
            long calls = level.journal.stream().filter(s -> s.kind().equals("damage")).count();
            check(calls == 1 + passed && player.getMainHandItem().damage == 0, label + ": damageTool called " + calls + " times, no wear applied");
            check(areaName.equals("NONE") ? passed == 0 : passed > 0, label + ": hammer extras reached as expected");
            fate(label, level, s1, Fate.NO_BODY, null);
            others(label, level, Map.of(), new Snapshot(level, List.of()), List.of(s1));
            instabuildRuns++;
        }
    }

    static Map<String, IToolHarvestAbility> harvests(String... names) {
        Map<String, IToolHarvestAbility> map = new LinkedHashMap<>();
        for(String name : names) map.put(name, AbilityHarvestRegression.HARVEST.get(name));
        return map;
    }

    /** isMinedStructure is true only for two parts of the same intact structure. */
    static void isMinedStructureCases() {
        ServerLevel level = world(true, 0);
        Structure s1 = place(level, REFINERY, ORIGIN, "S1");
        Structure s2 = place(level, REFINERY, new BlockPos(3, 0, 0), "S2");
        Structure other = place(level, LOOT_MACHINE, new BlockPos(0, 0, 2), "OTHER");
        AbilityHarvestRegression.ore(level, new BlockPos(0, 0, -2));
        // Two coreless dummies: the first points at air, the second at the first.
        BlockPos lone = new BlockPos(0, 0, -4), chained = new BlockPos(1, 0, -4);
        level.states.put(lone, REFINERY.createDummyState(Direction.EAST));
        level.states.put(chained, REFINERY.createDummyState(Direction.EAST));
        ready(level, s1, s2, other);
        check(REFINERY.findCore(level, lone) == null && REFINERY.findCore(level, chained) == null, "coreless dummies resolve no core");
        for(BlockPos a : s1.parts.keySet()) for(BlockPos b : s1.parts.keySet())
            check(ToolAbilityItem.isMinedStructure(level, a, b), "isMinedStructure: same structure " + a + " / " + b);
        for(BlockPos a : s1.parts.keySet()) for(BlockPos b : s2.parts.keySet()) {
            check(!ToolAbilityItem.isMinedStructure(level, a, b) && !ToolAbilityItem.isMinedStructure(level, b, a), "isMinedStructure: other structure of the same block " + a + " / " + b);
        }
        for(BlockPos a : s1.parts.keySet()) for(BlockPos b : other.parts.keySet()) {
            check(!ToolAbilityItem.isMinedStructure(level, a, b) && !ToolAbilityItem.isMinedStructure(level, b, a), "isMinedStructure: another multiblock " + a + " / " + b);
        }
        for(BlockPos a : List.of(new BlockPos(0, 0, -2), new BlockPos(0, 5, 0))) {
            check(!ToolAbilityItem.isMinedStructure(level, a, ORIGIN) && !ToolAbilityItem.isMinedStructure(level, ORIGIN, a), "isMinedStructure: ore or air " + a);
        }
        check(!ToolAbilityItem.isMinedStructure(level, lone, chained) && !ToolAbilityItem.isMinedStructure(level, chained, lone)
                && !ToolAbilityItem.isMinedStructure(level, lone, lone), "isMinedStructure: coreless dummies");
        check(level.journal.isEmpty() && level.drops.isEmpty(), "isMinedStructure changes nothing");
    }

    /** Mining each part of each machine with every harvest preset (NONE is vanilla mining) and in creative; the adjacent twin stays. */
    static void directMultiblocks() {
        for(DummyableBlock machine : MACHINES)
        for(int part = 0; part < layout(machine).size(); part++)
        for(Map.Entry<String, IToolHarvestAbility> harvest : AbilityHarvestRegression.HARVEST.entrySet())
        for(GameType mode : List.of(GameType.SURVIVAL, GameType.CREATIVE)) {
            if(mode == GameType.CREATIVE && !harvest.getKey().equals("NONE") && !harvest.getKey().equals("SILK")) continue;
            ServerLevel level = world(true, part);
            Structure s1 = place(level, machine, ORIGIN, "S1");
            Structure s2 = place(level, machine, machine == CENTRIFUGE ? new BlockPos(1, 0, 0) : new BlockPos(3, 0, 0), "S2");
            ready(level, s1, s2);
            BlockPos main = s1.positions().get(part);
            String label = "direct " + machine + " part " + main + " " + harvest.getKey() + " " + mode;
            mine(label, level, miner(level, IToolAreaAbility.NONE, 0, harvest.getValue(), mode), main, p -> false);
            // playerWillDestroy drops the body at the core in survival; creative drops none.
            fate(label, level, s1, mode == GameType.CREATIVE ? Fate.NO_BODY : Fate.BODY, ORIGIN);
            fate(label, level, s2, Fate.INTACT, null);
            others(label, level, Map.of(), new Snapshot(level, List.of()), List.of(s1, s2));
        }
    }

    /**
     * A part without a core, mined directly: playerWillDestroy finds no core and drops nothing, and mineBlock harvests the part through
     * the preset's onHarvestBlock as before this batch. The loot-table stand-in drops one plain body for any part; the refinery's
     * persistent loot finds no core block entity (a DUMMY has none, an EXTRA only its proxy) and drops nothing. NONE (vanilla mining:
     * DummyableBlock.playerDestroy drops nothing) and creative drop no body. Durability follows mine().
     */
    static void corelessDummies() {
        for(DummyableBlock machine : List.of(REFINERY, LOOT_MACHINE))
        for(DummyBlockType type : List.of(DummyBlockType.DUMMY, DummyBlockType.EXTRA))
        for(Map.Entry<String, IToolHarvestAbility> harvest : AbilityHarvestRegression.HARVEST.entrySet())
        for(GameType mode : List.of(GameType.SURVIVAL, GameType.CREATIVE)) {
            ServerLevel level = world(true, 0);
            BlockState state = type == DummyBlockType.DUMMY ? machine.createDummyState(Direction.EAST) : machine.createExtraState(Direction.EAST);
            level.states.put(ORIGIN, state);
            BlockEntity be = machine.newBlockEntity(ORIGIN, state);
            if(be != null) { be.level = level; level.blockEntities.put(ORIGIN, be); }
            check(machine.findCore(level, ORIGIN) == null && !(be instanceof IPersistentNBT), "coreless part has no core and no persistent block entity");
            String label = "coreless " + machine + " " + type + " " + harvest.getKey() + " " + mode;
            mine(label, level, miner(level, IToolAreaAbility.NONE, 0, harvest.getValue(), mode), ORIGIN, p -> false);
            boolean body = machine == LOOT_MACHINE && mode == GameType.SURVIVAL && harvest.getValue() != IToolHarvestAbility.NONE;
            check(level.getBlockState(ORIGIN).isAir() && level.getBlockEntity(ORIGIN) == null && (be == null || be.isRemoved()), label + ": removed");
            check(body ? level.drops.size() == 1 && level.drops.getFirst().pos().equals(ORIGIN) && AbilityHarvestRegression.same(level.drops.getFirst().stack(), new ItemStack(machine))
                    : level.drops.isEmpty(), label + (body ? ": harvested into one plain body " : ": removed without a body ") + level.drops);
            if(body) corelessBodies++;
        }
    }

    /**
     * A group of coreless parts chained to a missing core, mined from one of them with the hammer or the vein (three seeds) under every
     * preset: the first extra that passes the checks is harvested (isMinedStructure never matches coreless parts), its removal cascade
     * clears the whole group, and the mined block's own harvest then runs on air. The loot-table stand-in drops one body for the
     * group, the refinery none; durability follows mine(). A coreless centrifuge column finds no owned core, so its playerWillDestroy
     * and onRemove clear nothing, and its onRemove runs DummyableBlock.onRemove under safeRem, so no part removes the one below it: only
     * parts orphaned by a neighbor update go. Each column part the ability harvests (an extra that passed the checks, or the mined part
     * if it still stands at mineBlock's harvest) drops its own plain body (the default loot), so a column can drop more than one; the
     * other parts are either removed by the cascade or stay untouched (mined from the top, the bottom two parts remain). This
     * characterizes pre-existing coreless centrifuge behavior that the batch leaves unchanged; it is not the desired outcome, so a later
     * fix shows up here as a deliberate expectation change.
     */
    static void corelessGroups() {
        // (0, 0, 0) points west at air; the others reach it through each other.
        List<Part> wide = List.of(new Part(0, 0, 0, Direction.EAST, DummyBlockType.DUMMY), new Part(1, 0, 0, Direction.EAST, DummyBlockType.DUMMY),
                new Part(0, 1, 0, Direction.UP, DummyBlockType.EXTRA), new Part(1, 1, 0, Direction.UP, DummyBlockType.DUMMY));
        // A centrifuge column whose bottom part points down at air.
        List<Part> column = List.of(new Part(0, 0, 0, Direction.UP, DummyBlockType.DUMMY), new Part(0, 1, 0, Direction.UP, DummyBlockType.DUMMY),
                new Part(0, 2, 0, Direction.UP, DummyBlockType.EXTRA), new Part(0, 3, 0, Direction.UP, DummyBlockType.DUMMY));
        for(DummyableBlock machine : List.of(LOOT_MACHINE, REFINERY, CENTRIFUGE))
        for(String areaName : List.of("HAMMER", "RECURSION"))
        for(int mined = 0; mined < wide.size(); mined++) // both groups have four parts
        for(Map.Entry<String, IToolHarvestAbility> harvest : AbilityHarvestRegression.HARVEST.entrySet())
        for(long seed : areaName.equals("RECURSION") ? new long[] {1, 2, 3} : new long[] {0}) {
            List<Part> group = machine == CENTRIFUGE ? column : wide;
            ServerLevel level = world(true, seed);
            level.clipResult = new BlockHitResult(Direction.UP);
            Structure s = new Structure(machine, machine == CENTRIFUGE ? new BlockPos(0, -1, 0) : new BlockPos(-1, 0, 0));
            for(Part part : group) {
                BlockPos pos = ORIGIN.offset(part.dx(), part.dy(), part.dz());
                BlockState state = part.type() == DummyBlockType.DUMMY ? machine.createDummyState(part.facing()) : machine.createExtraState(part.facing());
                level.states.put(pos, state);
                BlockEntity be = machine.newBlockEntity(pos, state);
                if(be != null) { be.level = level; level.blockEntities.put(pos, be); }
                s.parts.put(pos, state);
                s.entities.put(pos, be);
            }
            s.body = new ItemStack(machine);
            for(BlockPos pos : s.parts.keySet()) check(machine.findCore(level, pos) == null, "coreless group: no core at " + pos);
            IToolAreaAbility area = areaName.equals("HAMMER") ? IToolAreaAbility.HAMMER : IToolAreaAbility.RECURSION;
            BlockPos main = s.positions().get(mined);
            String label = "coreless group " + machine + " " + areaName + " from " + main + " " + harvest.getKey() + " seed " + seed;
            List<Probe> probes = mine(label, level, miner(level, area, 0, harvest.getValue(), GameType.SURVIVAL), main, p -> false);
            check(probes.stream().anyMatch(p -> p.passes() && s.contains(p.pos())), label + ": an extra of the group passed the checks");
            if(machine == CENTRIFUGE) {
                List<Drop> bodies = level.drops.stream().filter(d -> s.contains(d.pos()) && d.stack().item == machine).toList();
                Set<BlockPos> harvested = new HashSet<>();
                for(Probe p : probes) if(p.passes() && s.contains(p.pos())) harvested.add(p.pos());
                Set<BlockPos> bodyAt = new HashSet<>();
                for(Drop d : bodies) bodyAt.add(d.pos());
                boolean mainHarvested = bodyAt.contains(main);
                check(bodies.size() == bodyAt.size() && bodies.stream().allMatch(d -> AbilityHarvestRegression.same(d.stack(), s.body))
                        && bodyAt.containsAll(harvested) && bodyAt.size() == harvested.size() + (mainHarvested ? 1 : 0)
                        && (harvest.getValue() != IToolHarvestAbility.NONE || !mainHarvested),
                        label + ": pre-existing coreless centrifuge behavior, unchanged by the batch: one plain body per harvested part " + bodies + " harvested " + harvested);
                if(bodies.size() > 1) corelessColumnMultiple++;
                int left = 0;
                for(BlockPos pos : s.parts.keySet()) {
                    BlockEntity be = s.entities.get(pos);
                    boolean gone = level.getBlockState(pos).isAir() && level.getBlockEntity(pos) == null && (be == null || be.isRemoved());
                    boolean untouched = level.getBlockState(pos) == s.parts.get(pos) && level.getBlockEntity(pos) == be && (be == null || !be.isRemoved());
                    check(gone || untouched, label + ": pre-existing coreless centrifuge behavior, unchanged by the batch: part " + pos + " is either removed or untouched");
                    if(untouched) left++;
                }
                check(left < s.parts.size() && level.getBlockState(main).isAir(), label + ": the mined part and the harvested one are removed");
                others(label, level, Map.of(), new Snapshot(level, List.of()), List.of(s));
                corelessColumnBodies++;
                if(left > 0) corelessColumnPartial++;
                continue;
            }
            fate(label, level, s, machine == REFINERY ? Fate.NO_BODY : Fate.BODY, null);
            others(label, level, Map.of(), new Snapshot(level, List.of()), List.of(s));
            if(machine == LOOT_MACHINE) corelessBodies++;
        }
    }

    static final BlockPos[] AROUND = { new BlockPos(0, 0, -1), new BlockPos(1, 0, -1), new BlockPos(-1, 0, -1), new BlockPos(1, 0, 1),
            new BlockPos(0, 0, 1), new BlockPos(-1, 1, 1), new BlockPos(0, 1, 1) };

    /** Crates, barrels and ores in front of and behind the WIDE layout at the origin. */
    static void surround(ServerLevel level) {
        AbilityHarvestRegression.crate(level, AROUND[0], AbilityHarvestRegression.IRON_CRATE, "NORTH", true);
        AbilityHarvestRegression.barrel(level, AROUND[1], AbilityHarvestRegression.STEEL, "NORTH_EAST", 321);
        AbilityHarvestRegression.ore(level, AROUND[2]);
        AbilityHarvestRegression.ore(level, AROUND[3]);
        // Behind the core, where DummyableBlock.onRemove on the core looks for another part: a crate is not one.
        AbilityHarvestRegression.crate(level, AROUND[4], AbilityHarvestRegression.STEEL_CRATE, "SOUTH", true);
        AbilityHarvestRegression.crate(level, AROUND[5], AbilityHarvestRegression.IRON_CRATE, "SOUTH_UP", false);
        AbilityHarvestRegression.barrel(level, AROUND[6], AbilityHarvestRegression.CORRODED, "SOUTH", 123);
    }

    /**
     * Vein, hammer and flat hammer from each part of a multiblock with a twin beside it (on either side) and crates, barrels and ores
     * around: the mined machine drops one body at its core, the twin one body if any of its parts was harvested, and every other
     * block that passed the checks its own drops. The vein's shuffle runs three seeds. The centrifuge clears its whole column in
     * playerWillDestroy, so the reference block is air before the dig and no extra passes the checks.
     */
    static void areaMultiblocks() {
        for(String areaName : List.of("RECURSION", "HAMMER", "HAMMER_FLAT"))
        for(DummyableBlock machine : MACHINES)
        for(boolean lowSide : new boolean[] {false, true})
        for(int part = 0; part < layout(machine).size(); part++)
        for(Map.Entry<String, IToolHarvestAbility> harvest : harvests("NONE", "SILK", "LUCK", "SMELTER", "SHREDDER", "MERCURY").entrySet())
        for(long seed : areaName.equals("RECURSION") ? new long[] {1, 2, 3} : new long[] {0}) {
            boolean keep = (part + seed) % 2 == 0;
            ServerLevel level = world(keep, seed);
            level.clipResult = new BlockHitResult(Direction.UP);
            IToolAreaAbility area = switch(areaName) { case "RECURSION" -> IToolAreaAbility.RECURSION; case "HAMMER" -> IToolAreaAbility.HAMMER; default -> IToolAreaAbility.HAMMER_FLAT; };
            Structure s1 = place(level, machine, ORIGIN, "S1");
            Structure s2 = place(level, machine, new BlockPos(lowSide ? -3 : 3, 0, 0), "S2");
            surround(level);
            ready(level, s1, s2);
            int fortune = harvest.getKey().equals("LUCK") ? 3 : 0;
            Map<BlockPos, AbilityHarvestRegression.Expect> candidates = new HashMap<>();
            for(BlockPos pos : AROUND) candidates.put(pos, AbilityHarvestRegression.expectAt(level, pos, true, harvest.getKey(), fortune));
            Snapshot snapshot = new Snapshot(level, candidates.keySet());
            BlockPos main = s1.positions().get(part);
            String label = areaName + " " + machine + (lowSide ? " twin west" : " twin east") + " from " + main + " " + harvest.getKey() + " seed " + seed;
            List<Probe> probes = mine(label, level, miner(level, area, 0, harvest.getValue(), GameType.SURVIVAL), main, p -> false);
            Set<BlockPos> hit = new HashSet<>();
            for(Probe p : probes) if(p.passes()) hit.add(p.pos());
            Map<BlockPos, AbilityHarvestRegression.Expect> broken = new HashMap<>();
            for(BlockPos pos : candidates.keySet()) if(hit.contains(pos)) broken.put(pos, candidates.get(pos));
            Set<BlockPos> kept = new HashSet<>(candidates.keySet());
            kept.removeAll(broken.keySet());
            boolean twinHit = probes.stream().anyMatch(p -> p.passes() && s2.contains(p.pos()));
            fate(label, level, s1, Fate.BODY, ORIGIN);
            fate(label, level, s2, twinHit ? Fate.BODY : Fate.INTACT, null);
            others(label, level, broken, snapshot.only(kept), List.of(s1, s2));
            sameStructureRemovals += (int) probes.stream().filter(p -> p.passes() && s1.contains(p.pos())).count();
            if(twinHit) secondBodies++;
            if(probes.stream().anyMatch(p -> p.passes() && s2.contains(p.pos()) && p.ref().is(machine))) secondWhileMinedPresent++;
            areaBlocksBroken += broken.size();
            if(machine == CENTRIFUGE) {
                check(probes.stream().noneMatch(Probe::passes) && broken.isEmpty() && !twinHit, label + ": the cleared centrifuge leaves the reference air: no extra passes");
                footprintAreaRuns++;
            }
        }
    }

    /**
     * A protection listener cancelling extras of the structure being mined: those parts stay through their own call, the mined
     * machine still drops exactly one body, and its removal cascade still clears every part. With every extra cancelled (the hammer,
     * the vein over three seeds and the flat hammer) mineBlock's skip branch runs with the structure still standing. The centrifuge
     * has cleared itself before the dig, so no extra of it is reached.
     */
    static void sameStructureCancel() {
        for(DummyableBlock machine : MACHINES)
        for(String areaName : List.of("HAMMER", "RECURSION", "HAMMER_FLAT"))
        for(int variant = 0; variant < (areaName.equals("HAMMER") && machine != CENTRIFUGE ? 3 : 1); variant++)
        for(long seed : areaName.equals("RECURSION") ? new long[] {1, 2, 3} : new long[] {0}) {
            ServerLevel level = world(true, seed);
            level.clipResult = new BlockHitResult(Direction.UP);
            Structure s1 = place(level, machine, ORIGIN, "S1");
            ready(level, s1);
            IToolAreaAbility area = switch(areaName) { case "RECURSION" -> IToolAreaAbility.RECURSION; case "HAMMER" -> IToolAreaAbility.HAMMER; default -> IToolAreaAbility.HAMMER_FLAT; };
            BlockPos main = machine == CENTRIFUGE ? new BlockPos(0, 1, 0) : new BlockPos(1, 0, 0);
            // Every part; the core only (the first part the hammer reaches); or the core and the part above it, so that (1, 1, 0) is the
            // first uncancelled part and its removal clears the cancelled ones.
            Set<BlockPos> cancelAt = new HashSet<>(switch(variant) {
                case 0 -> s1.positions();
                case 1 -> List.of(ORIGIN);
                default -> List.of(ORIGIN, new BlockPos(0, 1, 0));
            });
            cancelAt.remove(main);
            NeoForge.EVENT_BUS.listeners.add(event -> { if(cancelAt.contains(event.getPos())) event.setCanceled(true); });
            String label = "cancel same structure " + machine + " " + areaName + " variant " + variant + " seed " + seed;
            List<Probe> probes = mine(label, level, miner(level, area, 0, IToolHarvestAbility.SILK, GameType.SURVIVAL), main, p -> cancelAt.contains(p.pos()));
            fate(label, level, s1, Fate.BODY, ORIGIN);
            others(label, level, Map.of(), new Snapshot(level, List.of()), List.of(s1));
            if(machine == CENTRIFUGE) {
                check(probes.stream().noneMatch(Probe::passes) && level.breakEvents.isEmpty(), label + ": the cleared centrifuge leaves no extra to cancel");
                footprintCancelRuns++;
                continue;
            }
            check(probes.stream().anyMatch(p -> p.passes() && cancelAt.contains(p.pos())), label + ": a part of the mined structure was cancelled");
            if(variant == 0) {
                // Nothing changed before mineBlock wore the tool for the mined part: the skip branch ran on the standing structure.
                List<Step> journal = level.journal;
                int firstSet = -1, lastDamage = -1;
                for(int i = 0; i < journal.size(); i++) {
                    if(firstSet < 0 && journal.get(i).kind().equals("set")) firstSet = i;
                    if(journal.get(i).kind().equals("damage")) lastDamage = i;
                }
                check(lastDamage >= 0 && firstSet > lastDamage && journal.stream().filter(s -> s.kind().equals("damage")).count() == 1,
                        label + ": every extra cancelled, the skip branch wears the tool once before anything is removed");
                allCancelledRuns++;
            }
        }
    }

    /**
     * A hammer dig around an ore with a crate, a barrel, ores, a multiblock part, blocks the checks skip, a block exactly twice as hard
     * and a game-master block: no listener, a listener cancelling chosen extras, and adventure mode with a tool that may break ores only.
     */
    static void breakEvents() {
        BlockPos east = new BlockPos(1, 0, 0), up = new BlockPos(0, 1, 0), west = new BlockPos(-1, 0, 0), north = new BlockPos(0, 0, -1),
                south = new BlockPos(0, 0, 1), hard = new BlockPos(1, 0, 1), even = new BlockPos(-1, 0, 1), master = new BlockPos(1, 0, -1),
                twinPart = new BlockPos(1, 1, 1);
        for(String mode : List.of("plain", "listener", "adventure"))
        for(Map.Entry<String, IToolHarvestAbility> harvest : harvests("NONE", "SILK", "SMELTER").entrySet())
        for(boolean keep : new boolean[] {true, false}) {
            ServerLevel level = world(keep, 0);
            level.clipResult = new BlockHitResult(Direction.UP);
            AbilityHarvestRegression.ore(level, ORIGIN);
            AbilityHarvestRegression.ore(level, east);
            AbilityHarvestRegression.ore(level, up);
            AbilityHarvestRegression.crate(level, west, AbilityHarvestRegression.IRON_CRATE, "WEST", true);
            AbilityHarvestRegression.barrel(level, north, AbilityHarvestRegression.STEEL, "NORTH", 77);
            level.states.put(south, DIRT.defaultBlockState());
            level.states.put(hard, HARD.defaultBlockState());
            level.states.put(even, EVEN.defaultBlockState());
            level.states.put(master, MASTER.defaultBlockState());
            // A refinery whose EXTRA part at (1, 1, 1) is the only part in reach.
            Structure twin = place(level, REFINERY, new BlockPos(2, 1, 1), "TWIN");
            ready(level, twin);
            Map<BlockPos, AbilityHarvestRegression.Expect> candidates = new HashMap<>();
            for(BlockPos pos : List.of(east, up, west, north)) candidates.put(pos, AbilityHarvestRegression.expectAt(level, pos, true, harvest.getKey(), 0));
            for(BlockPos pos : List.of(south, hard, even, master)) candidates.put(pos, new AbilityHarvestRegression.Expect(List.of(new ItemStack(level.getBlockState(pos).getBlock())), true, 0));
            AbilityHarvestRegression.Expect mined = AbilityHarvestRegression.expectAt(level, ORIGIN, true, harvest.getKey(), 0);
            Snapshot snapshot = new Snapshot(level, candidates.keySet());
            ServerPlayer player = miner(level, IToolAreaAbility.HAMMER, 0, harvest.getValue(), mode.equals("adventure") ? GameType.ADVENTURE : GameType.SURVIVAL);
            Predicate<Probe> cancelled;
            if(mode.equals("listener")) {
                Set<BlockPos> cancelAt = Set.of(east, west, twinPart);
                NeoForge.EVENT_BUS.listeners.add(event -> { if(cancelAt.contains(event.getPos())) event.setCanceled(true); });
                cancelled = p -> cancelAt.contains(p.pos()) || p.state().getBlock() == MASTER;
            } else if(mode.equals("adventure")) {
                player.getMainHandItem().canBreak.addAll(List.of(AbilityHarvestRegression.ORE, EVEN));
                cancelled = p -> p.state().getBlock() != AbilityHarvestRegression.ORE && p.state().getBlock() != EVEN;
            } else {
                cancelled = p -> p.state().getBlock() == MASTER;
            }
            String label = "break events " + mode + " " + harvest.getKey() + " keep " + keep;
            List<Probe> probes = mine(label, level, player, ORIGIN, cancelled);
            for(BlockPos pos : List.of(south, hard)) check(probes.stream().anyMatch(p -> p.pos().equals(pos) && !p.passes()), label + ": the checks skip " + pos);
            check(probes.stream().anyMatch(p -> p.pos().equals(even) && p.passes()), label + ": twice as hard still passes");
            Map<BlockPos, AbilityHarvestRegression.Expect> broken = new HashMap<>();
            broken.put(ORIGIN, mined);
            for(Probe p : probes) if(p.passes() && !cancelled.test(p) && candidates.containsKey(p.pos())) broken.put(p.pos(), candidates.get(p.pos()));
            Set<BlockPos> kept = new HashSet<>(candidates.keySet());
            kept.removeAll(broken.keySet());
            boolean twinHit = probes.stream().anyMatch(p -> p.passes() && !cancelled.test(p) && twin.contains(p.pos()));
            fate(label, level, twin, twinHit ? Fate.BODY : Fate.INTACT, twinPart);
            check(twinHit == mode.equals("plain"), label + ": the refinery part is harvested only when nothing cancels it");
            others(label, level, broken, snapshot.only(kept), List.of(twin));
        }
    }

    /**
     * The EXPLOSION ability over the mined multiblock, its twin, a crate and an ore, in every processing order: the mined structure keeps
     * the one body playerWillDestroy dropped at its core, the twin drops one at its first processed part, the crate and the ore their own
     * drops, and the processor follows each emitted drop with one spawnAfterBreak in place with no tool.
     */
    static void explosionAbility() {
        for(DummyableBlock machine : MACHINES)
        // The core, a DUMMY and an EXTRA part of the refinery and the loot stand-in; the centrifuge from its EXTRA part.
        for(int mined : machine == CENTRIFUGE ? new int[] {2} : new int[] {0, 1, 2})
        for(Map.Entry<String, IToolHarvestAbility> harvest : harvests("NONE", "SILK", "LUCK", "SMELTER", "SHREDDER").entrySet())
        for(boolean keep : new boolean[] {true, false}) {
            BlockPos twinCore = machine == CENTRIFUGE ? new BlockPos(1, 0, 0) : new BlockPos(3, 0, 0);
            BlockPos crateAt = new BlockPos(0, 0, -1), oreAt = new BlockPos(0, 0, -2);
            List<Part> parts = layout(machine);
            Part minedPart = parts.get(mined), otherPart = parts.get(mined == 1 ? 3 : 1);
            BlockPos main = ORIGIN.offset(minedPart.dx(), minedPart.dy(), minedPart.dz());
            BlockPos other = ORIGIN.offset(otherPart.dx(), otherPart.dy(), otherPart.dz());
            BlockPos twinA = twinCore.offset(parts.get(1).dx(), parts.get(1).dy(), parts.get(1).dz());
            BlockPos twinB = twinCore.offset(parts.get(2).dx(), parts.get(2).dy(), parts.get(2).dz());
            AbilityHarvestRegression.permutations(List.of(main, other, twinA, twinB, crateAt, oreAt), order -> {
                ServerLevel level = world(keep, 0);
                Structure s1 = place(level, machine, ORIGIN, "S1");
                Structure s2 = place(level, machine, twinCore, "S2");
                AbilityHarvestRegression.crate(level, crateAt, AbilityHarvestRegression.STEEL_CRATE, "BLAST", true);
                AbilityHarvestRegression.ore(level, oreAt);
                ready(level, s1, s2);
                Map<BlockPos, AbilityHarvestRegression.Expect> broken = new HashMap<>();
                broken.put(crateAt, AbilityHarvestRegression.crateExpect(level, crateAt, false));
                broken.put(oreAt, new AbilityHarvestRegression.Expect(List.of(new ItemStack(AbilityHarvestRegression.RAW, 1)), false, 0));
                BlockAllocatorStandard.next = order;
                BlockPos firstTwin = order.stream().filter(s2::contains).findFirst().orElseThrow();
                String label = "EXPLOSION ability " + machine + " from " + main + " " + harvest.getKey() + " keep " + keep + " order " + order;
                List<Probe> probes = mine(label, level, miner(level, IToolAreaAbility.EXPLOSION, 0, harvest.getValue(), GameType.SURVIVAL), main, p -> false);
                check(probes.isEmpty(), label + ": the explosion breaks no extra block through breakExtraBlock");
                fate(label, level, s1, Fate.BODY, ORIGIN);
                if(mined == 0) explosionMinedCore++; else explosionMinedPart++;
                fate(label, level, s2, Fate.BODY, firstTwin);
                others(label, level, broken, new Snapshot(level, List.of()), List.of(s1, s2));
                check(level.explodeCalls.size() == 1 && level.explodeCalls.getFirst().radius() == 0.1F
                        && level.explodeCalls.getFirst().interaction() == Level.ExplosionInteraction.NONE, label + ": one cosmetic vanilla explosion");
                List<AfterBreakCall> processed = level.afterBreakCalls.stream().filter(c -> c.tool() == ItemStack.EMPTY).toList();
                check(processed.size() == 3 && processed.stream().map(AfterBreakCall::pos).toList().containsAll(List.of(firstTwin, crateAt, oreAt))
                        && processed.stream().allMatch(c -> c.inPlace() && !c.dropExperience()), label + ": spawnAfterBreak once per emitted loot pass, in place " + processed);
            });
        }
        // Mining an ore with the EXPLOSION ability: no structure is being mined, so a refinery in the blast drops one body through the
        // processor (chance 1) at its first processed part, beside a filled crate and the mined ore's own processor drop.
        for(Map.Entry<String, IToolHarvestAbility> harvest : harvests("NONE", "SILK", "LUCK", "SMELTER", "SHREDDER").entrySet())
        for(boolean keep : new boolean[] {true, false}) {
            BlockPos oreAt = new BlockPos(0, 0, -2), crateAt = new BlockPos(1, 0, -2);
            List<BlockPos> set = List.of(oreAt, ORIGIN, new BlockPos(1, 0, 0), new BlockPos(-1, 1, 0), crateAt);
            AbilityHarvestRegression.permutations(set, order -> {
                ServerLevel level = world(keep, 0);
                Structure s1 = place(level, REFINERY, ORIGIN, "BLASTED");
                AbilityHarvestRegression.crate(level, crateAt, AbilityHarvestRegression.IRON_CRATE, "BLAST", true);
                AbilityHarvestRegression.ore(level, oreAt);
                ready(level, s1);
                Map<BlockPos, AbilityHarvestRegression.Expect> broken = new HashMap<>();
                broken.put(crateAt, AbilityHarvestRegression.crateExpect(level, crateAt, false));
                // The processor's diamond pickaxe has no ability enchantments: one raw ore, whatever the preset.
                broken.put(oreAt, new AbilityHarvestRegression.Expect(List.of(new ItemStack(AbilityHarvestRegression.RAW, 1)), false, 0));
                BlockAllocatorStandard.next = order;
                BlockPos first = order.stream().filter(s1::contains).findFirst().orElseThrow();
                String label = "EXPLOSION ability from an ore " + harvest.getKey() + " keep " + keep + " order " + order;
                List<Probe> probes = mine(label, level, miner(level, IToolAreaAbility.EXPLOSION, 0, harvest.getValue(), GameType.SURVIVAL), oreAt, p -> false);
                check(probes.isEmpty(), label + ": the explosion breaks no extra block through breakExtraBlock");
                fate(label, level, s1, Fate.BODY, first);
                others(label, level, broken, new Snapshot(level, List.of()), List.of(s1));
                List<AfterBreakCall> processed = level.afterBreakCalls.stream().filter(c -> c.tool() == ItemStack.EMPTY).toList();
                check(processed.size() == 3 && processed.stream().map(AfterBreakCall::pos).toList().containsAll(List.of(first, crateAt, oreAt))
                        && processed.stream().allMatch(c -> c.inPlace() && !c.dropExperience()), label + ": spawnAfterBreak once per emitted loot pass, in place " + processed);
                explosionFromOre++;
            });
        }
    }
    // endregion

    // region follow-up: effectiveness gate and core removal
    /**
     * A hammer or flat-hammer dig around an ore, in the y = 0 plane the flat hammer reaches: another ore (effective), coal gas, glass and
     * a shearable plant (need no tool, not pickaxe-mineable) and a block that fails the tool check. As in the original (canHarvestBlock ||
     * canShearBlock) only effective blocks are extras, SILK takes any block that passes the tool check and shears take the plant; a skipped
     * block gets no BreakEvent, no removal, no drop and no wear.
     */
    static void extraEffectiveness() {
        BlockPos east = new BlockPos(1, 0, 0), far = new BlockPos(-1, 0, -1), gas = new BlockPos(-1, 0, 0), glass = new BlockPos(0, 0, -1),
                plant = new BlockPos(0, 0, 1), tool = new BlockPos(1, 0, 1);
        for(String areaName : List.of("HAMMER", "HAMMER_FLAT"))
        for(boolean shears : new boolean[] {false, true})
        for(Map.Entry<String, IToolHarvestAbility> harvest : harvests("NONE", "SILK", "LUCK", "SMELTER", "SHREDDER").entrySet()) {
            ServerLevel level = world(true, 0);
            level.clipResult = new BlockHitResult(Direction.UP);
            AbilityHarvestRegression.ore(level, ORIGIN);
            AbilityHarvestRegression.ore(level, east);
            AbilityHarvestRegression.ore(level, far);
            level.states.put(gas, COAL_GAS.defaultBlockState());
            level.states.put(glass, GLASS.defaultBlockState());
            level.states.put(plant, PLANT.defaultBlockState());
            level.states.put(tool, DIRT.defaultBlockState());
            boolean silk = harvest.getKey().equals("SILK");
            int fortune = harvest.getKey().equals("LUCK") ? 3 : 0;
            Map<BlockPos, Boolean> reached = new LinkedHashMap<>();
            reached.put(east, true);
            reached.put(far, true);
            reached.put(gas, silk);
            reached.put(glass, silk);
            reached.put(plant, silk || shears);
            reached.put(tool, false);
            Map<BlockPos, AbilityHarvestRegression.Expect> candidates = new HashMap<>();
            for(BlockPos pos : List.of(east, far)) candidates.put(pos, AbilityHarvestRegression.expectAt(level, pos, true, harvest.getKey(), fortune));
            for(BlockPos pos : List.of(gas, glass, plant, tool))
                candidates.put(pos, new AbilityHarvestRegression.Expect(List.of(new ItemStack(level.getBlockState(pos).getBlock())), true, 0));
            AbilityHarvestRegression.Expect mined = AbilityHarvestRegression.expectAt(level, ORIGIN, true, harvest.getKey(), fortune);
            Snapshot snapshot = new Snapshot(level, candidates.keySet());
            ServerPlayer player = miner(level, areaName.equals("HAMMER") ? IToolAreaAbility.HAMMER : IToolAreaAbility.HAMMER_FLAT, 0, harvest.getValue(), GameType.SURVIVAL);
            ((ProbeTool) player.getMainHandItem().getItem()).isShears = shears;
            String label = "effectiveness " + areaName + " " + harvest.getKey() + (shears ? " shears" : "");
            List<Probe> probes = mine(label, level, player, ORIGIN, p -> false);
            Map<BlockPos, AbilityHarvestRegression.Expect> broken = new HashMap<>();
            broken.put(ORIGIN, mined);
            for(Map.Entry<BlockPos, Boolean> entry : reached.entrySet()) {
                BlockPos pos = entry.getKey();
                Probe probe = probes.stream().filter(p -> p.pos().equals(pos)).findFirst().orElse(null);
                check(probe != null, label + ": the dig reaches " + pos);
                check(probe.passes() == entry.getValue(), label + ": " + probe.state() + " at " + pos + (entry.getValue() ? " is an extra" : " is skipped") + " " + probe.passes());
                boolean noTool = probe.state().getBlock() == COAL_GAS || probe.state().getBlock() == GLASS || probe.state().getBlock() == PLANT;
                if(entry.getValue()) {
                    broken.put(pos, candidates.get(pos));
                    if(noTool) gatePassed++;
                } else {
                    check(level.getBlockState(pos) == probe.state() && level.getBlockEntity(pos) == probe.be(),
                            label + ": skipped " + probe.state() + " at " + pos + " stays");
                    check(level.breakEvents.stream().noneMatch(r -> r.event().pos.equals(pos)), label + ": skipped " + pos + " fires no BreakEvent");
                    if(noTool) gateSkipped++;
                }
            }
            Set<BlockPos> kept = new HashSet<>(candidates.keySet());
            kept.removeAll(broken.keySet());
            others(label, level, broken, snapshot.only(kept), List.of());
        }
    }

    /**
     * Mining a refinery from its core with the hammer while coal gas, glass, a shearable plant and an ore stand in reach beside it, all
     * before the dig reaches the first part of the structure (the hammer walks x, then y, then z, and removing that part clears the
     * mined core, so nothing after it is an extra): the part still goes through the mined-structure branch (removed without loot, worn
     * once; the machine drops its one body at the core), the ore is harvested, and the gas, glass and plant are extras only under SILK
     * (the plant also with shears).
     */
    static void gateAroundMachine() {
        BlockPos mined = ORIGIN, ore = new BlockPos(-1, -1, -1), gas = new BlockPos(-1, -1, 0), glass = new BlockPos(-1, -1, 1), plant = new BlockPos(-1, 0, -1);
        for(Map.Entry<String, IToolHarvestAbility> harvest : harvests("NONE", "SILK", "SMELTER").entrySet())
        for(boolean shears : new boolean[] {false, true}) {
            ServerLevel level = world(true, 0);
            level.clipResult = new BlockHitResult(Direction.UP);
            Structure s1 = place(level, REFINERY, ORIGIN, "S1");
            level.states.put(gas, COAL_GAS.defaultBlockState());
            level.states.put(glass, GLASS.defaultBlockState());
            level.states.put(plant, PLANT.defaultBlockState());
            AbilityHarvestRegression.ore(level, ore);
            ready(level, s1);
            boolean silk = harvest.getKey().equals("SILK");
            Map<BlockPos, AbilityHarvestRegression.Expect> candidates = new HashMap<>();
            candidates.put(ore, AbilityHarvestRegression.expectAt(level, ore, true, harvest.getKey(), 0));
            for(BlockPos pos : List.of(gas, glass, plant))
                candidates.put(pos, new AbilityHarvestRegression.Expect(List.of(new ItemStack(level.getBlockState(pos).getBlock())), true, 0));
            Snapshot snapshot = new Snapshot(level, candidates.keySet());
            ServerPlayer player = miner(level, IToolAreaAbility.HAMMER, 0, harvest.getValue(), GameType.SURVIVAL);
            ((ProbeTool) player.getMainHandItem().getItem()).isShears = shears;
            String label = "effectiveness around a refinery " + harvest.getKey() + (shears ? " shears" : "");
            List<Probe> probes = mine(label, level, player, mined, p -> false);
            // The removal of one part clears the parts that point through it before the dig reaches them.
            check(probes.stream().anyMatch(p -> p.passes() && s1.contains(p.pos())), label + ": a part of the mined structure is an extra");
            check(probes.stream().filter(p -> s1.contains(p.pos())).allMatch(p -> (p.passes() || p.state().isAir()) && p.stateAfter().isAir()),
                    label + ": every part in reach goes through the mined-structure branch or was cleared before");
            sameStructureRemovals += (int) probes.stream().filter(p -> p.passes() && s1.contains(p.pos())).count();
            Map<BlockPos, AbilityHarvestRegression.Expect> broken = new HashMap<>();
            for(Probe p : probes) if(p.passes() && candidates.containsKey(p.pos())) broken.put(p.pos(), candidates.get(p.pos()));
            check(broken.containsKey(ore) && broken.containsKey(gas) == silk && broken.containsKey(glass) == silk && broken.containsKey(plant) == (silk || shears),
                    label + ": extras taken " + broken.keySet());
            Set<BlockPos> kept = new HashSet<>(candidates.keySet());
            kept.removeAll(broken.keySet());
            fate(label, level, s1, Fate.BODY, ORIGIN);
            others(label, level, broken, snapshot.only(kept), List.of(s1));
        }
    }

    /**
     * An empty main hand skips every extra: no BreakEvent, no removal, no drop, no tool wear, even for a block that needs no tool and is
     * pickaxe-mineable (nothing else stops it) and for SILK. The control run with the tool in hand takes that block.
     */
    static void emptyHandExtras() {
        BlockPos free = new BlockPos(1, 0, 0), gas = new BlockPos(-1, 0, 0);
        for(Map.Entry<String, IToolHarvestAbility> harvest : harvests("NONE", "SILK", "SMELTER").entrySet())
        for(boolean empty : new boolean[] {true, false}) {
            ServerLevel level = world(true, 0);
            AbilityHarvestRegression.ore(level, ORIGIN);
            level.states.put(free, FREE_ORE.defaultBlockState());
            level.states.put(gas, COAL_GAS.defaultBlockState());
            ServerPlayer player = miner(level, IToolAreaAbility.NONE, 0, harvest.getValue(), GameType.SURVIVAL);
            ProbeTool item = (ProbeTool) player.getMainHandItem().getItem();
            ItemStack stack = player.getMainHandItem();
            if(empty) player.main = ItemStack.EMPTY;
            boolean silk = harvest.getKey().equals("SILK");
            String label = "extras with " + (empty ? "an empty hand " : "the tool in hand ") + harvest.getKey();
            item.breakExtraBlock(level, free, player, ORIGIN);
            item.breakExtraBlock(level, gas, player, ORIGIN);
            check(item.probes.size() == 2, label + ": both extras were offered");
            if(empty) {
                check(item.probes.stream().noneMatch(Probe::passes), label + ": every extra is skipped");
                check(level.journal.isEmpty() && level.breakEvents.isEmpty() && level.drops.isEmpty(), label + ": no BreakEvent, removal, drop or wear " + level.journal);
                check(level.getBlockState(free).getBlock() == FREE_ORE && level.getBlockState(gas).getBlock() == COAL_GAS && stack.damage == 0, label + ": blocks stay, no wear");
                emptyHandRuns++;
            } else {
                Probe takenFree = item.probes.get(0), takenGas = item.probes.get(1);
                check(takenFree.passes() && takenFree.stateAfter().isAir(), label + ": the control takes the free ore");
                check(takenGas.passes() == silk && takenGas.stateAfter().isAir() == silk, label + ": the control takes coal gas only under SILK");
                int taken = silk ? 2 : 1;
                check(level.breakEvents.size() == taken && stack.damage == taken, label + ": the control fires " + level.breakEvents.size() + " events and wears " + stack.damage);
            }
        }
    }

    /**
     * A vein under SILK from coal gas, a block the pickaxe is not effective for: the original lets SILK through canHarvestBlock, so the
     * gas the vein reaches (connected, same block) is taken, while glass and an ore beside it are not part of the vein and a gas block out
     * of the radius stays. Three shuffle seeds.
     */
    static void veinSilkNonEffective() {
        BlockPos a = new BlockPos(1, 0, 0), b = new BlockPos(2, 1, 0), glass = new BlockPos(0, 0, 1), ore = new BlockPos(0, 0, -1), faraway = new BlockPos(8, 0, 0);
        for(long seed : new long[] {1, 2, 3}) {
            ServerLevel level = world(true, seed);
            level.states.put(ORIGIN, COAL_GAS.defaultBlockState());
            level.states.put(a, COAL_GAS.defaultBlockState());
            level.states.put(b, COAL_GAS.defaultBlockState());
            level.states.put(faraway, COAL_GAS.defaultBlockState());
            level.states.put(glass, GLASS.defaultBlockState());
            AbilityHarvestRegression.ore(level, ore);
            Snapshot kept = new Snapshot(level, List.of(glass, ore, faraway));
            Map<BlockPos, AbilityHarvestRegression.Expect> broken = new HashMap<>();
            for(BlockPos pos : List.of(ORIGIN, a, b)) broken.put(pos, new AbilityHarvestRegression.Expect(List.of(new ItemStack(COAL_GAS)), true, 0));
            String label = "vein SILK from coal gas seed " + seed;
            List<Probe> probes = mine(label, level, miner(level, IToolAreaAbility.RECURSION, 0, IToolHarvestAbility.SILK, GameType.SURVIVAL), ORIGIN, p -> false);
            check(probes.size() == 2 && probes.stream().allMatch(Probe::passes), label + ": the vein takes the two connected gas blocks " + probes);
            others(label, level, broken, kept, List.of());
            veinSilkRuns++;
        }
    }

    enum Removal { PLAYER_CORE, CREATIVE_CORE, PLAYER_DUMMY, REMOVE_CORE, REMOVE_DUMMY }

    /**
     * A row of three presses, each core directly behind the previous one along its facing's opposite (or, in the second geometry, each
     * press one block lower so that the previous core has the next press's dummy behind it). Removing the first press by player mining
     * (survival, creative; from the core or from the dummy) or by Level.removeBlock (core, dummy) removes exactly that press: the original
     * (`if(i >= 12) { }`) never lets a core remove the block behind it, so the others keep their parts and block entities and drop
     * nothing. The dummy still removes the core it points to, and the core's removal still orphans and clears its dummy.
     */
    static void coreRemoval() {
        for(boolean dummyBehind : new boolean[] {false, true})
        for(Direction facing : List.of(Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST))
        for(Removal removal : Removal.values()) {
            ServerLevel level = world(true, 0);
            Direction back = facing.getOpposite();
            BlockPos core2 = ORIGIN.relative(back).offset(0, dummyBehind ? -1 : 0, 0);
            BlockPos core3 = core2.relative(back);
            List<Part> layout = pressLayout(facing);
            Structure p1 = place(level, PRESS, ORIGIN, "P1", layout);
            Structure p2 = place(level, PRESS, core2, "P2", layout);
            Structure p3 = place(level, PRESS, core3, "P3", layout);
            ready(level, p1, p2, p3);
            BlockState behind = level.getBlockState(ORIGIN.relative(back));
            check(behind.getBlock() == PRESS && DummyableBlock.isCore(behind) != dummyBehind, "the block behind the first core is " + (dummyBehind ? "a dummy" : "a core") + " of the same block");
            BlockPos dummy = ORIGIN.offset(0, 1, 0);
            String label = "core removal " + (dummyBehind ? "dummy behind " : "core behind ") + facing + " " + removal;
            switch(removal) {
                case PLAYER_CORE -> mine(label, level, miner(level, IToolAreaAbility.NONE, 0, IToolHarvestAbility.NONE, GameType.SURVIVAL), ORIGIN, p -> false);
                case CREATIVE_CORE -> mine(label, level, miner(level, IToolAreaAbility.NONE, 0, IToolHarvestAbility.NONE, GameType.CREATIVE), ORIGIN, p -> false);
                case PLAYER_DUMMY -> mine(label, level, miner(level, IToolAreaAbility.NONE, 0, IToolHarvestAbility.NONE, GameType.SURVIVAL), dummy, p -> false);
                case REMOVE_CORE -> check(level.removeBlock(ORIGIN, false), label + ": the core is removed");
                case REMOVE_DUMMY -> check(level.removeBlock(dummy, false), label + ": the dummy is removed");
            }
            boolean body = removal == Removal.PLAYER_CORE || removal == Removal.PLAYER_DUMMY;
            fate(label, level, p1, body ? Fate.BODY : Fate.NO_BODY, ORIGIN);
            fate(label, level, p2, Fate.INTACT, null);
            fate(label, level, p3, Fate.INTACT, null);
            check(level.journal.stream().filter(s -> s.kind().equals("set")).allMatch(s -> p1.contains(s.pos())), label + ": only the first press's parts are changed");
            others(label, level, Map.of(), new Snapshot(level, List.of()), List.of(p1, p2, p3));
            if(removal == Removal.REMOVE_DUMMY || removal == Removal.PLAYER_DUMMY) dummyChainRuns++; else coreRemovalRuns++;
        }
    }
    // endregion

    // region BlockProcessorStandard
    enum Roll { ALL, NONE, PASS, FAIL, FORTUNE }

    static final float SIZE = 4F;

    /** setAllDrop, setNoDrop, the default 1 / size chance with a roll under or over it, and setAllDrop with fortune 2. */
    static BlockProcessorStandard processor(ServerLevel level, Roll roll) {
        level.random.fallback = switch(roll) { case PASS -> 0.1F; case FAIL -> 0.9F; default -> 0.5F; };
        return switch(roll) {
            case ALL -> new BlockProcessorStandard().setAllDrop();
            case NONE -> new BlockProcessorStandard().setNoDrop();
            case PASS, FAIL -> new BlockProcessorStandard();
            case FORTUNE -> new BlockProcessorStandard().setAllDrop().setFortune(2);
        };
    }

    static boolean passes(Roll roll) { return roll != Roll.NONE && roll != Roll.FAIL; }

    static void blast(ServerLevel level, BlockProcessorStandard processor, List<BlockPos> order) {
        BlockAllocatorStandard.next = order;
        ExplosionVNT vnt = new ExplosionVNT(level, 0.5, 0.5, 0.5, SIZE);
        vnt.setBlockAllocator(new BlockAllocatorStandard());
        vnt.setBlockProcessor(processor);
        vnt.explode();
        check(vnt.compat.getToBlow().equals(order), "the compat explosion lists the allocated blocks in order");
    }

    /** What one block must leave: drops before its removal (the loot pass) and after it (onRemove), and slot contents. */
    record Blast(List<ItemStack> before, List<ItemStack> after, int slots) {}

    static Blast blastExpect(ServerLevel level, BlockPos pos, boolean pass, int fortune) {
        Block block = level.getBlockState(pos).getBlock();
        if(block instanceof CrateBlock) {
            List<ItemStack> all = AbilityHarvestRegression.crateExpect(level, pos, false).drops();
            if(!pass) return new Blast(List.of(), all, 0);
            // keep=true: the loot pass emits the crate with its contents; keep=false: it emits the empty crate and onRemove the contents.
            return new Blast(List.of(all.getFirst()), all.subList(1, all.size()), 0);
        }
        if(block instanceof BarrelBlock barrel) {
            ItemStack body = AbilityHarvestRegression.ownBody(level, pos);
            return new Blast(pass ? List.of(body) : List.of(), List.of(), barrel.isCorroded() ? 0 : 2);
        }
        if(block == INFESTED) return new Blast(List.of(), List.of(), 0);
        if(block == ASBESTOS) return new Blast(pass ? List.of(new ItemStack(ASBESTOS)) : List.of(), List.of(), 0);
        if(block == AbilityHarvestRegression.ORE) return new Blast(pass ? List.of(new ItemStack(AbilityHarvestRegression.RAW, 1 + fortune)) : List.of(), List.of(), 0);
        throw new IllegalArgumentException(block.toString());
    }

    /**
     * Checks one exploded block from the journal: removed, the loot pass's drops before the first change of the block and onRemove's
     * after it, and spawnAfterBreak exactly once after emitted loot (after the last emitted drop, before the removal, in place, with no
     * tool and no experience) and never otherwise.
     */
    static void blastOutcome(String label, ServerLevel level, BlockPos pos, Blast expect) {
        List<Step> steps = level.journal;
        int removal = -1;
        for(int i = 0; i < steps.size() && removal < 0; i++) if(steps.get(i).kind().equals("set") && pos.equals(steps.get(i).pos())) removal = i;
        String at = label + ": " + pos;
        check(removal >= 0 && level.getBlockState(pos).isAir() && level.getBlockEntity(pos) == null, at + " ends as air without its block entity " + level.getBlockState(pos));
        List<ItemStack> before = new ArrayList<>(), after = new ArrayList<>();
        int lastBefore = -1, afterBreak = -1, afterBreaks = 0;
        for(int i = 0; i < steps.size(); i++) {
            Step step = steps.get(i);
            if(!pos.equals(step.pos())) continue;
            if(step.kind().equals("drop")) {
                if(i < removal) { before.add(((Drop) step.detail()).stack()); lastBefore = i; } else after.add(((Drop) step.detail()).stack());
            }
            if(step.kind().equals("after")) { afterBreak = i; afterBreaks++; }
        }
        check(AbilityHarvestRegression.sameMultiset(before, expect.before()), at + " loot pass drops " + before + " expected " + expect.before());
        check(AbilityHarvestRegression.sameMultiset(after, expect.after()), at + " removal drops " + after + " expected " + expect.after());
        if(expect.before().isEmpty()) {
            check(afterBreaks == 0, at + " no spawnAfterBreak without emitted loot");
            if(level.getBlockState(pos).isAir()) failedRolls++;
        } else {
            emittedLootPasses++;
            check(afterBreaks == 1 && afterBreak > lastBefore && afterBreak < removal, at + " one spawnAfterBreak after the emitted loot and before the removal");
            AfterBreakCall call = (AfterBreakCall) steps.get(afterBreak).detail();
            check(call.inPlace() && call.tool() == ItemStack.EMPTY && !call.dropExperience(), at + " spawnAfterBreak in place, no tool, no experience " + call);
        }
    }

    /**
     * Crates (filled and empty), barrels, an infested block, an asbestos brick and an ore under every drop policy and both crate
     * settings, in every processing order; a crate and a barrel beside them stay.
     */
    static void processorMixed() {
        List<BlockPos> set = new ArrayList<>();
        for(int i = 0; i < 7; i++) set.add(new BlockPos(i, 0, 0));
        BlockPos keptCrate = new BlockPos(0, 0, 1), keptBarrel = new BlockPos(2, 0, 1);
        for(boolean keep : new boolean[] {true, false})
        for(Roll roll : Roll.values())
        AbilityHarvestRegression.permutations(set, order -> {
            ServerLevel level = world(keep, 0);
            AbilityHarvestRegression.crate(level, set.get(0), AbilityHarvestRegression.IRON_CRATE, "FILLED", true);
            AbilityHarvestRegression.crate(level, set.get(1), AbilityHarvestRegression.STEEL_CRATE, "EMPTY", false);
            AbilityHarvestRegression.barrel(level, set.get(2), AbilityHarvestRegression.STEEL, "BARREL", 4100);
            AbilityHarvestRegression.barrel(level, set.get(3), AbilityHarvestRegression.CORRODED, "CORRODED", 130);
            level.states.put(set.get(4), INFESTED.defaultBlockState());
            level.states.put(set.get(5), ASBESTOS.defaultBlockState());
            AbilityHarvestRegression.ore(level, set.get(6));
            AbilityHarvestRegression.crate(level, keptCrate, AbilityHarvestRegression.IRON_CRATE, "KEPT", true);
            AbilityHarvestRegression.barrel(level, keptBarrel, AbilityHarvestRegression.STEEL, "KEPT", 99);
            Snapshot kept = new Snapshot(level, List.of(keptCrate, keptBarrel));
            Map<BlockPos, Blast> expect = new HashMap<>();
            for(BlockPos pos : set) expect.put(pos, blastExpect(level, pos, passes(roll), roll == Roll.FORTUNE ? 2 : 0));
            String label = "processor keep " + keep + " " + roll + " order " + order;
            blast(level, processor(level, roll), order);
            int slots = 0;
            for(BlockPos pos : set) { blastOutcome(label, level, pos, expect.get(pos)); slots += expect.get(pos).slots(); }
            check(level.drops.stream().allMatch(d -> set.contains(d.pos())), label + ": drops only at exploded blocks");
            check(level.slotDrops == slots, label + ": barrel slots spill once: " + level.slotDrops + " expected " + slots);
            check(level.silverfish == 0, label + ": the infested block spawns no silverfish (its loot with the pickaxe is empty)");
            check(level.getBlockState(set.get(5)).isAir(), label + ": the asbestos brick ends as air");
            kept.verify(label, level);
        });
    }

    /** Multiblocks alone, every order: one body at the first processed part when the roll passes, none when it fails; all parts gone. */
    static void processorMultiblocks() {
        for(DummyableBlock machine : MACHINES)
        for(Roll roll : List.of(Roll.ALL, Roll.PASS, Roll.FAIL, Roll.NONE)) {
            List<BlockPos> parts = place(world(true, 0), machine, ORIGIN, "S1").positions();
            AbilityHarvestRegression.permutations(parts, order -> {
                ServerLevel level = world(true, 0);
                Structure s1 = place(level, machine, ORIGIN, "S1");
                ready(level, s1);
                String label = "processor " + machine + " " + roll + " order " + order;
                blast(level, processor(level, roll), order);
                fate(label, level, s1, passes(roll) ? Fate.BODY : Fate.NO_BODY, order.getFirst());
                List<AfterBreakCall> calls = level.afterBreakCalls;
                check(passes(roll) ? calls.size() == 1 && calls.getFirst().pos().equals(order.getFirst()) && calls.getFirst().inPlace() && calls.getFirst().tool() == ItemStack.EMPTY
                        : calls.isEmpty(), label + ": spawnAfterBreak only after the emitted body " + calls);
                others(label, level, Map.of(), new Snapshot(level, List.of()), List.of(s1));
            });
        }
        // Two refineries side by side, three parts of each, every order: one body each at its first processed part.
        for(Roll roll : List.of(Roll.ALL, Roll.PASS)) {
            ServerLevel probe = world(true, 0);
            List<BlockPos> first = place(probe, REFINERY, ORIGIN, "S1").positions(), second = place(probe, REFINERY, new BlockPos(3, 0, 0), "S2").positions();
            List<BlockPos> set = List.of(first.get(0), first.get(1), first.get(3), second.get(2), second.get(4), second.get(5));
            AbilityHarvestRegression.permutations(set, order -> {
                ServerLevel level = world(true, 0);
                Structure s1 = place(level, REFINERY, ORIGIN, "S1");
                Structure s2 = place(level, REFINERY, new BlockPos(3, 0, 0), "S2");
                ready(level, s1, s2);
                String label = "processor two refineries " + roll + " order " + order;
                blast(level, processor(level, roll), order);
                fate(label, level, s1, Fate.BODY, order.stream().filter(s1::contains).findFirst().orElseThrow());
                fate(label, level, s2, Fate.BODY, order.stream().filter(s2::contains).findFirst().orElseThrow());
                others(label, level, Map.of(), new Snapshot(level, List.of()), List.of(s1, s2));
            });
        }
    }

    /** Vanilla explosions are unchanged: one body per multiblock in every order; an infested block there still spawns its silverfish. */
    static void vanillaExplosions() {
        for(DummyableBlock machine : MACHINES) {
            List<BlockPos> parts = place(world(true, 0), machine, ORIGIN, "S1").positions();
            AbilityHarvestRegression.permutations(parts, order -> {
                ServerLevel level = world(true, 0);
                Structure s1 = place(level, machine, ORIGIN, "S1");
                ready(level, s1);
                String label = "vanilla explosion " + machine + " order " + order;
                new Explosion(level, order).finalizeExplosion();
                fate(label, level, s1, Fate.BODY, order.getFirst());
                others(label, level, Map.of(), new Snapshot(level, List.of()), List.of(s1));
            });
        }
        ServerLevel level = world(true, 0);
        level.states.put(ORIGIN, INFESTED.defaultBlockState());
        new Explosion(level, List.of(ORIGIN)).finalizeExplosion();
        check(level.silverfish == 1 && level.drops.isEmpty() && level.getBlockState(ORIGIN).isAir(), "vanilla explosion: an infested block spawns one silverfish (the counter is live)");
    }
    // endregion

    static void runAll() {
        directMultiblocks();
        corelessDummies();
        instabuildSurvival();
        areaMultiblocks();
        // After the twin scenarios, so that a too-broad isMinedStructure is first caught there; the coreless group catches it too.
        corelessGroups();
        sameStructureCancel();
        breakEvents();
        explosionAbility();
        processorMixed();
        processorMultiblocks();
        vanillaExplosions();
        // Last, so that a too-broad isMinedStructure is first caught through the twin structure of the area scenarios.
        isMinedStructureCases();
        // After the earlier scenarios, so that a broken gate or core check is first caught by the scenarios written for it.
        extraEffectiveness();
        gateAroundMachine();
        emptyHandExtras();
        veinSilkNonEffective();
        coreRemoval();
        check(sameStructureRemovals > 0 && secondBodies > 0 && secondWhileMinedPresent > 0 && areaBlocksBroken > 0, "coverage: same-structure extras "
                + sameStructureRemovals + ", twin bodies " + secondBodies + " (" + secondWhileMinedPresent + " while the mined machine stood), area blocks " + areaBlocksBroken);
        check(cancelledExtras > 0 && preCancelledExtras > 0 && skippedExtras > 0, "coverage: cancelled " + cancelledExtras + ", pre-cancelled " + preCancelledExtras + ", skipped " + skippedExtras);
        check(corelessBodies > 0, "coverage: coreless bodies " + corelessBodies);
        check(explosionMinedCore > 0 && explosionMinedPart > 0 && explosionFromOre > 0 && footprintAreaRuns > 0 && footprintCancelRuns > 0
                && corelessColumnBodies > 0 && allCancelledRuns > 0 && instabuildRuns > 0, "coverage: review edge cases");
        check(emittedLootPasses > 0 && failedRolls > 0, "coverage: emitted loot passes " + emittedLootPasses + ", failed rolls " + failedRolls);
        check(gateSkipped > 0 && gatePassed > 0 && emptyHandRuns > 0 && veinSilkRuns > 0 && coreRemovalRuns > 0 && dummyChainRuns > 0, "coverage: gate skipped "
                + gateSkipped + ", passed " + gatePassed + ", empty hand runs " + emptyHandRuns + ", vein SILK runs " + veinSilkRuns + ", core removals " + coreRemovalRuns
                + ", dummy chains " + dummyChainRuns);
        System.out.println("Drops batch coverage: same-structure extras " + sameStructureRemovals + ", twin bodies " + secondBodies + " (" + secondWhileMinedPresent
                + " while the mined machine stood), area blocks broken " + areaBlocksBroken + ", cancelled extras " + cancelledExtras + " (" + preCancelledExtras
                + " pre-cancelled), skipped extras " + skippedExtras + ", coreless bodies " + corelessBodies + " (" + corelessColumnBodies + " centrifuge columns, " + corelessColumnPartial + " leaving parts, " + corelessColumnMultiple + " with several bodies)"
                + ", EXPLOSION ability runs mined at the core " + explosionMinedCore + ", at another part " + explosionMinedPart + ", from an ore " + explosionFromOre
                + ", centrifuge area runs " + footprintAreaRuns + ", centrifuge cancel runs " + footprintCancelRuns + ", all-cancelled runs " + allCancelledRuns
                + ", instabuild survival runs " + instabuildRuns + ", emitted loot passes " + emittedLootPasses + ", failed rolls " + failedRolls
                + ", effectiveness gate skipped " + gateSkipped + " and passed " + gatePassed + " no-tool extras, empty hand runs " + emptyHandRuns
                + ", vein SILK runs " + veinSilkRuns + ", core removals " + coreRemovalRuns + ", dummy chains " + dummyChainRuns);
    }
}
