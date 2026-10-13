package abilityharvest;

import java.util.*;
import java.util.function.*;

/** Method-level regression, not a real Minecraft world. See ability_harvest_stubs.py and the verifier's source contracts. */
public class AbilityHarvestRegression {
    static final BlockPos ORIGIN = new BlockPos(0, 0, 0);
    static final BarrelBlock STEEL = new BarrelBlock("barrel_steel", 16_000, false);
    static final BarrelBlock CORRODED = new BarrelBlock("barrel_corroded", 16_000, true);
    static final CrateBlock IRON_CRATE = new CrateBlock("crate_iron", CrateBlock.Type.IRON);
    static final CrateBlock STEEL_CRATE = new CrateBlock("crate_steel", CrateBlock.Type.STEEL);
    static final OreBlock ORE = new OreBlock();
    static final ContentsBlock CONTENTS = new ContentsBlock();
    static final Object RAW = "raw_ore", INGOT = "ingot", POWDER = "ore_powder";
    static final Map<String, IToolHarvestAbility> HARVEST = new LinkedHashMap<>();
    static int checks;

    static {
        HARVEST.put("NONE", IToolHarvestAbility.NONE);
        HARVEST.put("SILK", IToolHarvestAbility.SILK);
        HARVEST.put("LUCK", IToolHarvestAbility.LUCK);
        HARVEST.put("SMELTER", IToolHarvestAbility.SMELTER);
        HARVEST.put("SHREDDER", IToolHarvestAbility.SHREDDER);
        HARVEST.put("CENTRIFUGE", IToolHarvestAbility.CENTRIFUGE);
        HARVEST.put("CRYSTALLIZER", IToolHarvestAbility.CRYSTALLIZER);
        HARVEST.put("MERCURY", IToolHarvestAbility.MERCURY);
    }

    static void check(boolean condition, String label) {
        checks++;
        if(!condition) throw new AssertionError(label);
    }

    /** Vanilla-style ore: silk touch drops the block, otherwise 1 + fortune raw ore; no block entity. Loot lists are mutable, as in the game. */
    static final class OreBlock extends Block {
        OreBlock() { super("ore"); mineable(); }
        @Override protected List<ItemStack> getDrops(BlockState state, LootParams.Builder params) {
            ItemStack tool = params.withParameter(LootContextParams.BLOCK_STATE, state).create(LootContextParamSets.BLOCK).getParamOrNull(LootContextParams.TOOL);
            if(tool != null && tool.enchantments.containsKey(Enchantments.SILK_TOUCH)) return new ArrayList<>(List.of(new ItemStack(this)));
            return new ArrayList<>(List.of(new ItemStack(RAW, 1 + (tool == null ? 0 : tool.enchantments.getOrDefault(Enchantments.FORTUNE, 0)))));
        }
    }

    /** Shulker-box-like block: its loot copies the BLOCK_ENTITY loot parameter's contents and onRemove drops nothing. */
    static final class ContentsBlock extends BaseEntityBlock {
        ContentsBlock() { super("contents_box"); requiresTool = false; }
        public BlockEntity newBlockEntity(BlockPos pos, BlockState state) { return new ContentsBlockEntity(pos); }
        @Override protected List<ItemStack> getDrops(BlockState state, LootParams.Builder params) {
            BlockEntity be = params.withParameter(LootContextParams.BLOCK_STATE, state).create(LootContextParamSets.BLOCK).getParamOrNull(LootContextParams.BLOCK_ENTITY);
            ItemStack box = new ItemStack(this);
            if(be instanceof ContentsBlockEntity contents) { box.customData = new CompoundTag(); box.customData.putString("contents", contents.contents); }
            return new ArrayList<>(List.of(box));
        }
    }

    static final class ContentsBlockEntity extends BlockEntity {
        String contents = "";
        ContentsBlockEntity(BlockPos pos) { super(pos); }
    }

    /** One broken block's expectation: the exact drops at its own position and whether the ability path broke it (player entry only). */
    record Expect(List<ItemStack> drops, boolean ability, int slots) {}

    /** How the blocks are broken: a player mining, Level.destroyBlock(pos, true / false), or an item-dropping explosion. */
    enum Entry { PLAYER, DESTROY_BLOCK, DESTROY_NO_LOOT, EXPLOSION }

    /** Every scenario starts from the default config; crate scenarios then choose crate_keep_contents explicitly. */
    static ServerLevel world() {
        NtmConfig.SERVER.CRATE_KEEP_CONTENTS.set(true);
        ServerLevel level = new ServerLevel();
        level.recipes.smelting.add(new RecipeHolder(new SmeltingRecipe(RAW, new ItemStack(INGOT))));
        ShredderRecipes.RECIPES.clear();
        ShredderRecipes.RECIPES.put(ORE, new ItemStack(POWDER, 2));
        return level;
    }

    static ServerLevel world(boolean keepContents) {
        ServerLevel level = world();
        NtmConfig.SERVER.CRATE_KEEP_CONTENTS.set(keepContents);
        return level;
    }

    static BarrelBlockEntity barrel(ServerLevel level, BlockPos pos, BarrelBlock block, String fluid, int fill) {
        BlockState state = block.defaultBlockState();
        level.states.put(pos, state);
        BarrelBlockEntity be = (BarrelBlockEntity) block.newBlockEntity(pos, state);
        be.tank.type = fill > 0 ? fluid : "NONE";
        be.tank.fill = fill;
        be.mode = (short) (fill % 4);
        be.inventory = 2;
        level.blockEntities.put(pos, be);
        return be;
    }

    static void ore(ServerLevel level, BlockPos pos) { level.states.put(pos, ORE.defaultBlockState()); }

    static ContentsBlockEntity contents(ServerLevel level, BlockPos pos, String contents) {
        level.states.put(pos, CONTENTS.defaultBlockState());
        ContentsBlockEntity be = new ContentsBlockEntity(pos);
        be.contents = contents;
        level.blockEntities.put(pos, be);
        return be;
    }

    /** A crate with distinct slot stacks derived from `tag` (an item with custom data among them), or an empty one. */
    static CrateBaseBlockEntity crate(ServerLevel level, BlockPos pos, CrateBlock block, String tag, boolean filled) {
        BlockState state = block.defaultBlockState();
        level.states.put(pos, state);
        CrateBaseBlockEntity be = (CrateBaseBlockEntity) block.newBlockEntity(pos, state);
        be.level = level;
        if(filled) {
            ItemStack marked = new ItemStack(tag + "_tool", 1);
            marked.customData = new CompoundTag();
            marked.customData.putString("owner", tag);
            be.slots.set(0, new ItemStack(tag + "_ingot", 64));
            be.slots.set(5, new ItemStack(tag + "_plate", 3));
            be.slots.set(be.slots.size() - 1, marked);
        }
        level.blockEntities.put(pos, be);
        return be;
    }

    /**
     * What a broken crate must leave at its own position: keep=true is one crate item whose custom data is the side-effect-free
     * preview taken now and no loose contents; keep=false is one plain crate plus every non-empty slot stack, loose.
     */
    static Expect crateExpect(ServerLevel level, BlockPos pos, boolean ability) {
        Block block = level.getBlockState(pos).getBlock();
        CrateBaseBlockEntity be = (CrateBaseBlockEntity) level.getBlockEntity(pos);
        List<ItemStack> want = new ArrayList<>();
        if(NtmConfig.SERVER.CRATE_KEEP_CONTENTS.get()) {
            List<ItemStack> preview = be.getDrops(block);
            check(preview.size() == 1 && be.shouldDrop() && level.drops.isEmpty(), "crate preview is pure at " + pos);
            check(preview.getFirst().customData != null && preview.getFirst().customData.contains(IPersistentNBT.NBT_PERSISTENT_KEY), "crate preview carries its contents at " + pos);
            want.add(preview.getFirst());
        } else {
            want.add(new ItemStack(block));
            for(ItemStack stack : be.slots) if(!stack.isEmpty()) want.add(stack.copy());
        }
        return new Expect(want, ability, 0);
    }

    /** The expectation of whatever block stands at `pos` when it is broken with `harvest` (ordinary blocks drop per the tool). */
    static Expect expectAt(ServerLevel level, BlockPos pos, boolean ability, String harvest, int fortune) {
        Block block = level.getBlockState(pos).getBlock();
        if(block instanceof BarrelBlock) return barrelExpect(level, pos, ability);
        if(block instanceof CrateBlock) return crateExpect(level, pos, ability);
        if(block == ORE) return new Expect(oreDrops(harvest, fortune), ability, 0);
        ItemStack box = new ItemStack(CONTENTS);
        box.customData = new CompoundTag();
        box.customData.putString("contents", ((ContentsBlockEntity) level.getBlockEntity(pos)).contents);
        return new Expect(List.of(box), ability, 0);
    }

    /** ServerPlayerGameMode.destroyBlock, survival branch with an uncancelled BreakEvent (contract-checked). */
    static void destroyBlock(ServerLevel level, ServerPlayer player, BlockPos pos) {
        BlockState state1 = level.getBlockState(pos);
        BlockEntity blockEntity = level.getBlockEntity(pos);
        Block block = state1.getBlock();
        BlockState state = block.playerWillDestroy(level, pos, state1, player);
        ItemStack itemstack = player.getMainHandItem();
        ItemStack itemstack1 = itemstack.copy();
        boolean canHarvest = state.canHarvestBlock(level, pos, player);
        itemstack.mineBlock(level, state, pos, player);
        boolean removed = state.onDestroyedByPlayer(level, pos, player, canHarvest);
        if(removed) block.destroy(level, pos, state);
        if(canHarvest && removed) block.playerDestroy(level, player, pos, state, blockEntity, itemstack1);
    }

    static ServerPlayer player(ServerLevel level, IToolAreaAbility area, int areaLevel, IToolHarvestAbility harvest, int harvestLevel, int baseFortune) {
        ToolAbilityItem item = new ToolAbilityItem();
        item.config = new Configuration(new ToolPreset(area, areaLevel, harvest, harvestLevel));
        ItemStack tool = new ItemStack(item);
        if(baseFortune > 0) tool.enchantments.put(Enchantments.FORTUNE, baseFortune);
        return new ServerPlayer(level, tool);
    }

    static boolean same(ItemStack a, ItemStack b) {
        return a.item == b.item && a.count == b.count && Objects.equals(a.customData, b.customData);
    }

    /** The persistent body this barrel must drop: its own data, computed before the break through the side-effect-free preview. */
    static ItemStack ownBody(ServerLevel level, BlockPos pos) {
        BarrelBlockEntity be = (BarrelBlockEntity) level.getBlockEntity(pos);
        List<ItemStack> preview = be.getDrops(level.getBlockState(pos).getBlock());
        check(preview.size() == 1 && be.shouldDrop() && level.drops.isEmpty(), "preview is pure at " + pos);
        return preview.getFirst();
    }

    static List<ItemStack> oreDrops(String harvest, int fortune) {
        return switch(harvest) {
            case "SILK" -> List.of(new ItemStack(ORE));
            case "SMELTER" -> List.of(new ItemStack(INGOT, 1 + fortune));
            case "SHREDDER" -> List.of(new ItemStack(POWDER, 2));
            default -> List.of(new ItemStack(RAW, 1 + fortune));
        };
    }

    /** Exact multiset equality of the stacks (item, count and custom data), independent of the order they were dropped in. */
    static boolean sameMultiset(List<ItemStack> got, List<ItemStack> want) {
        if(got.size() != want.size()) return false;
        List<ItemStack> rest = new ArrayList<>(got);
        for(ItemStack stack : want) {
            Iterator<ItemStack> it = rest.iterator();
            boolean found = false;
            while(it.hasNext() && !found) if(same(it.next(), stack)) { it.remove(); found = true; }
            if(!found) return false;
        }
        return true;
    }

    /**
     * Runs `action` and checks every listed position; anything not listed must stay untouched. `tool` is what the loot passes
     * of a non-player entry receive (ItemStack.EMPTY) or the player's live main-hand stack.
     */
    static void run(String label, ServerLevel level, Entry entry, ItemStack tool, Runnable action, Map<BlockPos, Expect> broken, Set<BlockPos> kept) {
        Map<BlockPos, BlockState> keptStates = new HashMap<>();
        Map<BlockPos, BlockEntity> keptEntities = new HashMap<>();
        for(BlockPos pos : kept) { keptStates.put(pos, level.getBlockState(pos)); keptEntities.put(pos, level.getBlockEntity(pos)); }
        Map<BlockPos, Block> blocks = new HashMap<>();
        for(BlockPos pos : broken.keySet()) blocks.put(pos, level.getBlockState(pos).getBlock());

        action.run();

        Map<BlockPos, List<ItemStack>> dropped = new HashMap<>();
        for(Drop drop : level.drops) dropped.computeIfAbsent(drop.pos(), p -> new ArrayList<>()).add(drop.stack());
        check(broken.keySet().containsAll(dropped.keySet()), label + ": drops only at broken blocks " + dropped.keySet());
        int slots = 0;
        for(Map.Entry<BlockPos, Expect> expected : broken.entrySet()) {
            BlockPos pos = expected.getKey();
            Expect expect = expected.getValue();
            List<ItemStack> got = dropped.getOrDefault(pos, List.of());
            check(got.size() == expect.drops().size(), label + ": drop count at " + pos + " " + got + " expected " + expect.drops());
            check(sameMultiset(got, expect.drops()), label + ": own drops at " + pos + " " + got + " expected " + expect.drops());
            check(level.getBlockState(pos).isAir() && level.getBlockEntity(pos) == null, label + ": removed with its block entity at " + pos);
            List<AfterBreak> after = level.afterBreak.stream().filter(a -> a.pos().equals(pos)).toList();
            check(after.stream().allMatch(a -> a.block() == blocks.get(pos)), label + ": spawnAfterBreak only for the broken block at " + pos + " " + after);
            boolean persistent = blocks.get(pos) instanceof BarrelBlock || blocks.get(pos) instanceof CrateBlock;
            switch(entry) {
                case PLAYER -> {
                    if(expect.ability()) {
                        // Ability path: spawnAfterBreak exactly once, while the block and its block entity are still in place, with the live tool.
                        check(after.size() == 1 && after.getFirst().inPlace(), label + ": ability spawnAfterBreak before removal at " + pos + " " + after);
                        check(after.getFirst().tool() == tool, label + ": ability spawnAfterBreak receives the main-hand stack at " + pos + " " + after);
                    } else if(persistent) {
                        // Vanilla path for a barrel or crate: playerDestroy drops nothing; the body comes from onRemove.
                        check(after.isEmpty(), label + ": vanilla persistent break has no loot pass at " + pos);
                    } else {
                        // Vanilla path for an ordinary block: Block.playerDestroy -> dropResources runs it once after removal (with a tool copy).
                        check(after.size() == 1 && !after.getFirst().inPlace(), label + ": vanilla spawnAfterBreak after removal at " + pos + " " + after);
                    }
                }
                case DESTROY_BLOCK, EXPLOSION ->
                    // The loot pass emits the drops and calls spawnAfterBreak once with ItemStack.EMPTY while the block is still in place.
                    check(after.size() == 1 && after.getFirst().inPlace() && after.getFirst().tool() == ItemStack.EMPTY, label + ": loot pass spawnAfterBreak in place at " + pos + " " + after);
                case DESTROY_NO_LOOT -> check(after.isEmpty(), label + ": destroyBlock(false) has no loot pass at " + pos + " " + after);
            }
            slots += expect.slots();
        }
        check(level.slotDrops == slots, label + ": slot contents drop once and only from steel barrels: " + level.slotDrops + " expected " + slots);
        for(BlockPos pos : kept) {
            check(level.getBlockState(pos) == keptStates.get(pos) && level.getBlockEntity(pos) == keptEntities.get(pos)
                    && (keptEntities.get(pos) == null || !keptEntities.get(pos).isRemoved()), label + ": untouched at " + pos);
            check(level.afterBreak.stream().noneMatch(a -> a.pos().equals(pos)), label + ": no loot pass at untouched " + pos);
            if(keptEntities.get(pos) instanceof CrateBaseBlockEntity crate) check(crate.shouldDrop(), label + ": untouched crate keeps its drop flag at " + pos);
            if(keptEntities.get(pos) instanceof BarrelBlockEntity barrel) check(barrel.shouldDrop(), label + ": untouched barrel keeps its drop flag at " + pos);
        }
    }

    /** Mines `main` as a player and checks every listed position; anything not listed must stay untouched. */
    static void mine(String label, ServerLevel level, ServerPlayer player, BlockPos main, Map<BlockPos, Expect> broken, Set<BlockPos> kept) {
        ItemStack tool = player.getMainHandItem();
        Map<String, Integer> enchantments = new TreeMap<>(tool.enchantments);
        run(label, level, Entry.PLAYER, tool, () -> destroyBlock(level, player, main), broken, kept);
        check(tool.enchantments.equals(enchantments), label + ": tool enchantments restored " + tool.enchantments + " expected " + enchantments);
        check(!TagsUtil.getCustomData(tool).contains(IToolHarvestAbility.LUCK_BASE_FORTUNE_TAG), label + ": luck bookkeeping removed");
        check(tool.damage == broken.size(), label + ": one durability per broken block: " + tool.damage);
    }

    static Expect barrelExpect(ServerLevel level, BlockPos pos, boolean ability) {
        BarrelBlock block = (BarrelBlock) level.getBlockState(pos).getBlock();
        return new Expect(List.of(ownBody(level, pos)), ability, block.isCorroded() ? 0 : 2);
    }

    /** Single block: every harvest preset (NONE is the vanilla control path) on both barrels and several fills. */
    static void singleBarrels() {
        for(BarrelBlock block : List.of(STEEL, CORRODED))
        for(int fill : new int[] {0, 731, 16_000})
        for(Map.Entry<String, IToolHarvestAbility> harvest : HARVEST.entrySet())
        for(int baseFortune : new int[] {0, 2}) {
            ServerLevel level = world();
            barrel(level, ORIGIN, block, "SULFURIC_ACID", fill);
            boolean ability = harvest.getValue() != IToolHarvestAbility.NONE;
            Map<BlockPos, Expect> broken = Map.of(ORIGIN, barrelExpect(level, ORIGIN, ability));
            mine("single " + block + " " + fill + " " + harvest.getKey() + " fortune " + baseFortune, level,
                    player(level, IToolAreaAbility.NONE, 0, harvest.getValue(), 2, baseFortune), ORIGIN, broken, Set.of());
        }
    }

    /** Vein mining: a same-kind cluster with distinct fluids; another kind beside it and a far barrel stay. */
    static void veinBarrels() {
        List<BlockPos> cluster = List.of(ORIGIN, new BlockPos(1, 0, 0), new BlockPos(2, 0, 0), new BlockPos(2, 1, 0),
                new BlockPos(0, 0, 1), new BlockPos(1, 1, 1), new BlockPos(0, -1, 0));
        for(BarrelBlock block : List.of(STEEL, CORRODED))
        for(String harvest : List.of("NONE", "SILK", "LUCK", "SMELTER", "SHREDDER", "MERCURY"))
        for(int lvl : new int[] {0, 6}) {
            ServerLevel level = world();
            for(int i = 0; i < cluster.size(); i++) barrel(level, cluster.get(i), block, "FLUID_" + i, i == 3 ? 0 : 100 * i + 17);
            BarrelBlock other = block == STEEL ? CORRODED : STEEL;
            BlockPos beside = new BlockPos(-1, 0, 0), far = new BlockPos(9, 0, 0);
            barrel(level, beside, other, "OTHER", 555);
            barrel(level, far, block, "FAR", 444);
            Map<BlockPos, Expect> broken = new LinkedHashMap<>();
            for(BlockPos pos : cluster) broken.put(pos, barrelExpect(level, pos, !pos.equals(ORIGIN) || !harvest.equals("NONE")));
            mine("vein " + block + " " + harvest + " level " + lvl, level,
                    player(level, IToolAreaAbility.RECURSION, lvl, HARVEST.get(harvest), 5, 0), ORIGIN, broken, Set.of(beside, far));
        }
    }

    /** 3x3x3 hammer and flat hammer: mixed barrels, ores and BE-loot blocks around a barrel or an ore. */
    static void areaMixed() {
        for(String areaName : List.of("HAMMER", "HAMMER_FLAT"))
        for(String harvest : List.of("NONE", "SILK", "LUCK", "SMELTER", "SHREDDER"))
        for(boolean barrelFirst : new boolean[] {true, false}) {
            ServerLevel level = world();
            level.clipResult = new BlockHitResult(Direction.UP);
            IToolAreaAbility area = areaName.equals("HAMMER") ? IToolAreaAbility.HAMMER : IToolAreaAbility.HAMMER_FLAT;
            Map<BlockPos, Expect> broken = new LinkedHashMap<>();
            Set<BlockPos> kept = new HashSet<>();
            int fortune = harvest.equals("LUCK") ? 3 : 0;
            if(barrelFirst) barrel(level, ORIGIN, STEEL, "MAIN", 999); else ore(level, ORIGIN);
            barrel(level, new BlockPos(1, 0, 0), STEEL, "EAST", 101);
            barrel(level, new BlockPos(-1, 0, 1), CORRODED, "SOUTH_WEST", 202);
            barrel(level, new BlockPos(0, 0, -1), CORRODED, "NORTH", 0);
            ore(level, new BlockPos(1, 0, 1));
            contents(level, new BlockPos(-1, 0, -1), "diamonds");
            contents(level, new BlockPos(1, 0, -1), "emeralds");
            barrel(level, new BlockPos(0, 1, 1), STEEL, "ABOVE", 303);
            barrel(level, new BlockPos(2, 0, 0), STEEL, "OUTSIDE", 404);
            kept.add(new BlockPos(2, 0, 0));
            List<BlockPos> plane = List.of(ORIGIN, new BlockPos(1, 0, 0), new BlockPos(-1, 0, 1), new BlockPos(0, 0, -1),
                    new BlockPos(1, 0, 1), new BlockPos(-1, 0, -1), new BlockPos(1, 0, -1));
            List<BlockPos> targets = new ArrayList<>(plane);
            // The flat hammer hit the top face, so it stays in the y = 0 plane; the cube also takes the barrel above.
            if(area == IToolAreaAbility.HAMMER) targets.add(new BlockPos(0, 1, 1)); else kept.add(new BlockPos(0, 1, 1));
            for(BlockPos pos : targets) {
                boolean ability = !pos.equals(ORIGIN) || !harvest.equals("NONE");
                Block block = level.getBlockState(pos).getBlock();
                if(block instanceof BarrelBlock) broken.put(pos, barrelExpect(level, pos, ability));
                else if(block == ORE) broken.put(pos, new Expect(oreDrops(harvest, fortune), ability, 0));
                else {
                    ItemStack box = new ItemStack(CONTENTS);
                    box.customData = new CompoundTag();
                    box.customData.putString("contents", ((ContentsBlockEntity) level.getBlockEntity(pos)).contents);
                    broken.put(pos, new Expect(List.of(box), ability, 0));
                }
            }
            mine(areaName + " " + harvest + (barrelFirst ? " from barrel" : " from ore"), level,
                    player(level, area, 0, HARVEST.get(harvest), 2, 0), ORIGIN, broken, kept);
        }
    }

    /** Ordinary blocks keep their ability semantics: silk, fortune, smelting and shredding per block, at its own position. */
    static void ordinaryBlocks() {
        for(String harvest : List.of("NONE", "SILK", "LUCK", "SMELTER", "SHREDDER"))
        for(int baseFortune : new int[] {0, 1}) {
            ServerLevel level = world();
            List<BlockPos> vein = List.of(ORIGIN, new BlockPos(0, 1, 0), new BlockPos(0, 2, 0), new BlockPos(1, 2, 0));
            for(BlockPos pos : vein) ore(level, pos);
            // LUCK level 2 is fortune 3 over a lower base; the base returns afterwards. Silk touch replaces fortune drops.
            int fortune = harvest.equals("LUCK") ? Math.max(baseFortune, 3) : baseFortune;
            Map<BlockPos, Expect> broken = new LinkedHashMap<>();
            for(BlockPos pos : vein) broken.put(pos, new Expect(oreDrops(harvest, fortune), !pos.equals(ORIGIN) || !harvest.equals("NONE"), 0));
            mine("ore vein " + harvest + " base fortune " + baseFortune, level,
                    player(level, IToolAreaAbility.RECURSION, 0, HARVEST.get(harvest), 2, baseFortune), ORIGIN, broken, Set.of());
        }
        // Block-entity loot reads the block entity of each block, not the one the vein started from.
        ServerLevel level = world();
        List<String> loads = List.of("gold", "redstone", "lapis", "quartz");
        Map<BlockPos, Expect> broken = new LinkedHashMap<>();
        for(int i = 0; i < loads.size(); i++) {
            BlockPos pos = new BlockPos(i, 0, 0);
            contents(level, pos, loads.get(i));
            ItemStack box = new ItemStack(CONTENTS);
            box.customData = new CompoundTag();
            box.customData.putString("contents", loads.get(i));
            broken.put(pos, new Expect(List.of(box), i > 0, 0));
        }
        mine("contents vein NONE", level, player(level, IToolAreaAbility.RECURSION, 0, IToolHarvestAbility.NONE, 0, 0), ORIGIN, broken, Set.of());
    }

    /** Single crate: player mining (NONE is the vanilla control) and every harvest preset, both crate types, empty and filled. */
    static void singleCrates() {
        for(boolean keep : new boolean[] {true, false})
        for(CrateBlock block : List.of(IRON_CRATE, STEEL_CRATE))
        for(boolean filled : new boolean[] {true, false})
        for(Map.Entry<String, IToolHarvestAbility> harvest : HARVEST.entrySet())
        for(int baseFortune : new int[] {0, 2}) {
            ServerLevel level = world(keep);
            crate(level, ORIGIN, block, "SINGLE", filled);
            boolean ability = harvest.getValue() != IToolHarvestAbility.NONE;
            Map<BlockPos, Expect> broken = Map.of(ORIGIN, crateExpect(level, ORIGIN, ability));
            mine("single " + block + " keep " + keep + (filled ? " filled " : " empty ") + harvest.getKey() + " fortune " + baseFortune, level,
                    player(level, IToolAreaAbility.NONE, 0, harvest.getValue(), 2, baseFortune), ORIGIN, broken, Set.of());
        }
    }

    /** Vein mining: a same-type crate cluster with distinct contents (one empty); another crate type beside it and a far crate stay. */
    static void veinCrates() {
        List<BlockPos> cluster = List.of(ORIGIN, new BlockPos(1, 0, 0), new BlockPos(2, 0, 0), new BlockPos(2, 1, 0),
                new BlockPos(0, 0, 1), new BlockPos(1, 1, 1), new BlockPos(0, -1, 0));
        for(boolean keep : new boolean[] {true, false})
        for(CrateBlock block : List.of(IRON_CRATE, STEEL_CRATE))
        for(String harvest : List.of("NONE", "SILK", "LUCK", "SMELTER", "SHREDDER", "MERCURY"))
        for(int lvl : new int[] {0, 6}) {
            ServerLevel level = world(keep);
            for(int i = 0; i < cluster.size(); i++) crate(level, cluster.get(i), block, "VEIN_" + i, i != 3);
            CrateBlock other = block == IRON_CRATE ? STEEL_CRATE : IRON_CRATE;
            BlockPos beside = new BlockPos(-1, 0, 0), far = new BlockPos(9, 0, 0);
            crate(level, beside, other, "OTHER", true);
            crate(level, far, block, "FAR", true);
            Map<BlockPos, Expect> broken = new LinkedHashMap<>();
            for(BlockPos pos : cluster) broken.put(pos, crateExpect(level, pos, !pos.equals(ORIGIN) || !harvest.equals("NONE")));
            mine("crate vein " + block + " keep " + keep + " " + harvest + " level " + lvl, level,
                    player(level, IToolAreaAbility.RECURSION, lvl, HARVEST.get(harvest), 5, 0), ORIGIN, broken, Set.of(beside, far));
        }
    }

    /** Hammer and flat hammer from an ore or a crate with filled and empty crates, barrels, ores and BE-loot blocks around it. */
    static void areaCrates() {
        for(boolean keep : new boolean[] {true, false})
        for(String areaName : List.of("HAMMER", "HAMMER_FLAT"))
        for(String harvest : List.of("NONE", "SILK", "LUCK", "SMELTER", "SHREDDER", "MERCURY"))
        for(boolean crateMain : new boolean[] {false, true}) {
            ServerLevel level = world(keep);
            level.clipResult = new BlockHitResult(Direction.UP);
            IToolAreaAbility area = areaName.equals("HAMMER") ? IToolAreaAbility.HAMMER : IToolAreaAbility.HAMMER_FLAT;
            int fortune = harvest.equals("LUCK") ? 3 : 0;
            if(crateMain) crate(level, ORIGIN, IRON_CRATE, "MAIN", true); else ore(level, ORIGIN);
            crate(level, new BlockPos(1, 0, 0), STEEL_CRATE, "EAST", true);
            crate(level, new BlockPos(-1, 0, 1), IRON_CRATE, "SOUTH_WEST", false);
            barrel(level, new BlockPos(0, 0, -1), STEEL, "NORTH", 101);
            ore(level, new BlockPos(1, 0, 1));
            contents(level, new BlockPos(-1, 0, -1), "diamonds");
            crate(level, new BlockPos(1, 0, -1), IRON_CRATE, "NORTH_EAST", true);
            crate(level, new BlockPos(0, 1, 1), STEEL_CRATE, "ABOVE", true);
            barrel(level, new BlockPos(-1, 0, 0), CORRODED, "WEST", 202);
            crate(level, new BlockPos(2, 0, 0), IRON_CRATE, "OUTSIDE", true);
            Set<BlockPos> kept = new HashSet<>(List.of(new BlockPos(2, 0, 0)));
            List<BlockPos> targets = new ArrayList<>(List.of(ORIGIN, new BlockPos(1, 0, 0), new BlockPos(-1, 0, 1), new BlockPos(0, 0, -1),
                    new BlockPos(1, 0, 1), new BlockPos(-1, 0, -1), new BlockPos(1, 0, -1), new BlockPos(-1, 0, 0)));
            // The flat hammer hit the top face, so it stays in the y = 0 plane; the cube also takes the crate above.
            if(area == IToolAreaAbility.HAMMER) targets.add(new BlockPos(0, 1, 1)); else kept.add(new BlockPos(0, 1, 1));
            Map<BlockPos, Expect> broken = new LinkedHashMap<>();
            for(BlockPos pos : targets) broken.put(pos, expectAt(level, pos, !pos.equals(ORIGIN) || !harvest.equals("NONE"), harvest, fortune));
            mine(areaName + " crates keep " + keep + " " + harvest + (crateMain ? " from crate" : " from ore"), level,
                    player(level, area, 0, HARVEST.get(harvest), 2, 0), ORIGIN, broken, kept);
        }
    }

    /** Level.destroyBlock(pos, true) emits the loot once; with dropBlock false only onRemove drops. */
    static void destroyBlockPaths() {
        for(boolean keep : new boolean[] {true, false})
        for(boolean dropBlock : new boolean[] {true, false})
        for(int kind = 0; kind < 8; kind++) {
            ServerLevel level = world(keep);
            switch(kind) {
                case 0 -> crate(level, ORIGIN, IRON_CRATE, "DESTROY", true);
                case 1 -> crate(level, ORIGIN, STEEL_CRATE, "DESTROY", true);
                case 2 -> crate(level, ORIGIN, IRON_CRATE, "DESTROY", false);
                case 3 -> crate(level, ORIGIN, STEEL_CRATE, "DESTROY", false);
                case 4 -> barrel(level, ORIGIN, STEEL, "DESTROY", 640);
                case 5 -> barrel(level, ORIGIN, CORRODED, "DESTROY", 640);
                case 6 -> ore(level, ORIGIN);
                default -> contents(level, ORIGIN, "emeralds");
            }
            BlockPos neighbour = new BlockPos(1, 0, 0);
            crate(level, neighbour, IRON_CRATE, "NEIGHBOUR", true);
            Expect expect = dropBlock ? expectAt(level, ORIGIN, false, "NONE", 0)
                    : level.getBlockState(ORIGIN).getBlock() == ORE || level.getBlockState(ORIGIN).getBlock() == CONTENTS ? new Expect(List.of(), false, 0)
                    : expectAt(level, ORIGIN, false, "NONE", 0);
            run("destroyBlock " + dropBlock + " " + level.getBlockState(ORIGIN) + " kind " + kind + " keep " + keep, level,
                    dropBlock ? Entry.DESTROY_BLOCK : Entry.DESTROY_NO_LOOT, ItemStack.EMPTY, () -> check(level.destroyBlock(ORIGIN, dropBlock), "destroyBlock broke the block"),
                    Map.of(ORIGIN, expect), Set.of(neighbour));
        }
    }

    static <T> void permutations(List<T> items, Consumer<List<T>> visit) {
        if(items.size() <= 1) { visit.accept(new ArrayList<>(items)); return; }
        for(int i = 0; i < items.size(); i++) {
            List<T> rest = new ArrayList<>(items);
            T head = rest.remove(i);
            permutations(rest, tail -> { List<T> order = new ArrayList<>(); order.add(head); order.addAll(tail); visit.accept(order); });
        }
    }

    static final BlockPos IRON_AT = new BlockPos(0, 0, 0), STEEL_AT = new BlockPos(1, 0, 0), BARREL_AT = new BlockPos(2, 0, 0),
            CORRODED_AT = new BlockPos(3, 0, 0), ORE_AT = new BlockPos(4, 0, 0), BOX_AT = new BlockPos(5, 0, 0), KEPT_CRATE = new BlockPos(0, 0, 1),
            KEPT_BARREL = new BlockPos(2, 0, 1);

    /**
     * Item-dropping explosion over one crate of each type (one of them empty or both filled), two barrels, an ore and a BE-loot block,
     * in every processing order. No two collected stacks are mergeable (different crate items, different bodies), so each block's
     * loot stays at its own position; explosionMerge covers the merging case.
     */
    static void explosions() {
        for(boolean keep : new boolean[] {true, false})
        for(int empty = 0; empty < 3; empty++) {
            int emptyCase = empty;
            permutations(List.of(IRON_AT, STEEL_AT, BARREL_AT, CORRODED_AT, ORE_AT, BOX_AT), order -> {
                ServerLevel level = world(keep);
                crate(level, IRON_AT, IRON_CRATE, "IRON", emptyCase != 1);
                crate(level, STEEL_AT, STEEL_CRATE, "STEEL", emptyCase != 2);
                barrel(level, BARREL_AT, STEEL, "BARREL", 4100);
                barrel(level, CORRODED_AT, CORRODED, "CORRODED", 130);
                ore(level, ORE_AT);
                contents(level, BOX_AT, "quartz");
                crate(level, KEPT_CRATE, IRON_CRATE, "KEPT", true);
                barrel(level, KEPT_BARREL, STEEL, "KEPT", 99);
                Map<BlockPos, Expect> broken = new LinkedHashMap<>();
                for(BlockPos pos : order) broken.put(pos, expectAt(level, pos, false, "NONE", 0));
                run("explosion keep " + keep + " empty case " + emptyCase + " order " + order, level, Entry.EXPLOSION, ItemStack.EMPTY,
                        () -> new Explosion(level, order).finalizeExplosion(), broken, Set.of(KEPT_CRATE, KEPT_BARREL));
            });
        }
    }

    /**
     * Equal collected stacks merge in Explosion.addOrAppendStack: crate items without loose contents (keep=false) or with identical
     * contents (keep=true, empty crates) come out as one stack at the first matching crate's position. Nothing is lost or duplicated.
     */
    static void explosionMerge() {
        BlockPos p = new BlockPos(0, 0, 0), q = new BlockPos(1, 0, 0), s = new BlockPos(2, 0, 0), r = new BlockPos(3, 0, 0);
        for(boolean keep : new boolean[] {true, false})
        permutations(List.of(p, q, s, r), order -> {
            ServerLevel level = world(keep);
            // Empty iron crates p and q have equal custom data under keep=true; with keep=false every iron crate drops the plain item.
            crate(level, p, IRON_CRATE, "P", !keep);
            crate(level, q, IRON_CRATE, "Q", !keep);
            crate(level, s, IRON_CRATE, "S", true);
            crate(level, r, STEEL_CRATE, "R", false);
            Map<BlockPos, Expect> broken = new LinkedHashMap<>();
            for(BlockPos pos : order) broken.put(pos, crateExpect(level, pos, false));
            // The first mergeable crate in processing order keeps the merged stack; the others contribute nothing but their contents.
            List<BlockPos> mergeable = order.stream().filter(pos -> keep ? pos.equals(p) || pos.equals(q) : !pos.equals(r)).toList();
            BlockPos holder = mergeable.getFirst();
            ItemStack merged = broken.get(holder).drops().getFirst().copy();
            merged.count = mergeable.size();
            for(BlockPos pos : mergeable) {
                List<ItemStack> drops = new ArrayList<>(broken.get(pos).drops());
                drops.remove(0);
                if(pos.equals(holder)) drops.add(merged);
                broken.put(pos, new Expect(drops, false, 0));
            }
            run("explosion merge keep " + keep + " order " + order, level, Entry.EXPLOSION, ItemStack.EMPTY,
                    () -> new Explosion(level, order).finalizeExplosion(), broken, Set.of());
        });
    }

    public static void main(String[] args) {
        singleBarrels();
        veinBarrels();
        areaMixed();
        ordinaryBlocks();
        singleCrates();
        veinCrates();
        areaCrates();
        destroyBlockPaths();
        explosions();
        explosionMerge();
        System.out.println("PASS " + checks + " method-level assertions; no Minecraft runtime claim");
    }
}
