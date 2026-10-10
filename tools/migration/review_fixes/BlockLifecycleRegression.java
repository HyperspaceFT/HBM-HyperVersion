package reviewfixes;

import java.util.*;

/** Method-level regression, not a real Minecraft world. See block_stubs.py and verifier source contracts. */
public class BlockLifecycleRegression {
    static final BlockPos POS = new BlockPos(0, 0, 0);
    static final Block AIR = new Block();
    static int checks;

    static void check(boolean condition, String label) {
        checks++;
        if(!condition) throw new AssertionError(label);
    }

    static ItemStack marked(Object item, int count, String label) {
        return new ItemStack(item, count).component("meta", label).component("persistent.tank.fill", "731")
                .component("custom.name", "named " + label);
    }

    static void placement() {
        for(boolean client : new boolean[] {false, true})
        for(boolean creative : new boolean[] {false, true})
        for(boolean space : new boolean[] {false, true})
        for(boolean offhand : new boolean[] {false, true})
        for(boolean fullInventory : new boolean[] {false, true})
        for(int count : new int[] {1, 64})
        for(int otherCount : new int[] {0, 1, 64}) {
            ReviewedDummy block = new ReviewedDummy();
            block.space = space;
            ItemStack original = marked(block, count, "original");
            ItemStack other = marked(block, otherCount, "other");
            Player player = new Player(creative, offhand ? other : original, offhand ? original : other);
            if(fullInventory) for(int i = 0; i < 36; i++) player.inventory.add(marked(AIR, 64, "slot" + i));
            List<ItemStack> beforeInventory = new ArrayList<>(player.inventory);
            Map<String,String> beforeOriginal = new LinkedHashMap<>(original.components);
            Map<String,String> beforeOther = new LinkedHashMap<>(other.components);
            Level level = new Level();
            level.isClientSide = client;
            // Cached BlockItem.place: the callback gets the exact placement stack, then consume(1, player).
            block.setPlacedBy(level, POS, new BlockState(block), player, original);
            check(original.count == count + (!space && !creative ? 1 : 0), "pending consume compensation");
            original.consume(1, player);
            check(original.count == count - (space && !creative ? 1 : 0), "placement quantity invariant");
            check(original.components.equals(beforeOriginal), "original components survive placement/refund");
            check(other.count == otherCount && other.components.equals(beforeOther), "other hand untouched");
            check(player.inventory.equals(beforeInventory), "full or empty inventory untouched");
            check((offhand ? player.off : player.main) == original, "exact placed stack identity preserved");
            check(level.placed == (space && !client ? 1 : 0), "successful server placement only");
            check(level.scheduled == (space ? 2 : 0), "failed placement schedules nothing");
            if(space && !client) check(level.restored.equals(beforeOriginal), "successful persistent restoration");
        }
    }

    static void remove(ReviewedBarrel block, ServerLevel level) {
        block.onRemove(new BlockState(block), level, POS, new BlockState(AIR), false);
    }

    static void destroyWithDrops(ReviewedBarrel block, ServerLevel level) {
        // Level.destroyBlock -> Block.dropResources -> CommonHooks.handleBlockDrops
        // emits loot, calls spawnAfterBreak, then setBlock triggers onRemove.
        for(ItemStack drop : block.getDrops(new BlockState(block), new LootParams.Builder(level)))
            Block.popResource(level, POS, drop);
        block.spawnAfterBreak(new BlockState(block), level, POS, ItemStack.EMPTY, false);
        remove(block, level);
    }

    static void explode(ReviewedBarrel block, ServerLevel level, boolean vanilla, float chance, float sample) {
        // Vanilla onExplosionHit gates BOTH spawnAfterBreak and getDrops. NTM's
        // BlockProcessorStandard gates its loot pass, then onBlockExploded removes.
        if(block.canDropFromExplosion(new BlockState(block), level, POS, new Explosion())) {
            if(vanilla) block.spawnAfterBreak(new BlockState(block), level, POS, ItemStack.EMPTY, false);
            for(ItemStack drop : block.getDrops(new BlockState(block), new LootParams.Builder(level)))
                if(vanilla || sample <= chance) Block.popResource(level, POS, drop);
        }
        block.onBlockExploded(new BlockState(block), level, POS, new Explosion());
    }

    static void barrelLifecycle() {
        for(int fill : new int[] {0, 731, 16_000})
        for(String trigger : List.of("survival", "vanilla TNT", "NTM standard", "NTM mining", "destroyBlock(true)", "creative")) {
            ReviewedBarrel block = new ReviewedBarrel(false);
            ServerLevel level = new ServerLevel();
            BarrelBlockEntity barrel = new BarrelBlockEntity(fill, 16_000);
            level.be = barrel;
            List<ItemStack> preview = block.getDrops(new BlockState(block), new LootParams.Builder(level));
            check(preview.size() == 1 && barrel.shouldDrop() && level.drops.isEmpty(), "getDrops preview is pure: " + trigger);
            if(trigger.equals("destroyBlock(true)")) destroyWithDrops(block, level);
            else if(trigger.equals("vanilla TNT")) explode(block, level, true, 1, 0.25F);
            else if(trigger.startsWith("NTM")) explode(block, level, false, 1, 0.25F);
            else {
                remove(block, level);
                if(trigger.equals("survival")) block.playerDestroy(level, new Player(false, ItemStack.EMPTY, ItemStack.EMPTY),
                        POS, new BlockState(block), barrel, ItemStack.EMPTY);
            }
            check(level.drops.size() == 1, "exactly one body: " + trigger);
            check(level.drops.getFirst().count == 1 && level.drops.getFirst().item == block, "body identity: " + trigger);
            check(level.drops.getFirst().components.equals(preview.getFirst().components), "persistent fluid unchanged: " + trigger);
            check(level.inventoryDrops == 2, "contents drop once: " + trigger);
            check(level.be == null, "block entity removed: " + trigger);
        }
        // NTM setNoDrop is 0; setAllDrop is 1. Its existing <= comparison
        // admits sample=0 even at chance=0; preserve and report that separate edge.
        for(float chance : new float[] {0F, 0.5F, 1F})
        for(float sample : new float[] {0F, 0.25F, 0.75F}) {
            ReviewedBarrel block = new ReviewedBarrel(false);
            ServerLevel level = new ServerLevel();
            level.be = new BarrelBlockEntity(731, 16_000);
            explode(block, level, false, chance, sample);
            int expected = sample <= chance ? 1 : 0;
            check(level.drops.size() == expected, "NTM explosion owns probability/no-drop policy: " + chance + "/" + sample);
            if(expected == 1) check(level.drops.getFirst().components.get("persistent.tank.fill").equals("731"), "NTM retained fluid");
            check(level.inventoryDrops == 2, "explosion contents still drop once");
        }
        for(boolean client : new boolean[] {false, true}) {
            ReviewedBarrel block = new ReviewedBarrel(false);
            ServerLevel level = new ServerLevel();
            level.isClientSide = client;
            BarrelBlockEntity barrel = new BarrelBlockEntity(731, 16_000);
            level.be = barrel;
            barrel.preventDrop();
            remove(block, level); // existing antimatter/hot-fluid destroyBlock(false)
            check(level.drops.isEmpty(), "destructive-fluid suppresses body; client never spawns");
            check(level.inventoryDrops == (client ? 0 : 2), "destructive-fluid inventory policy unchanged");
        }
        ReviewedBarrel block = new ReviewedBarrel(false);
        ServerLevel level = new ServerLevel();
        BarrelBlockEntity barrel = new BarrelBlockEntity(731, 16_000);
        level.be = barrel;
        block.onRemove(new BlockState(block), level, POS, new BlockState(block), false);
        check(level.drops.isEmpty() && level.inventoryDrops == 0, "same-block update does not drop");
        // The corroded, no-BE branch is deliberately preserved, including its deferred duplication.
        ReviewedBarrel corroded = new ReviewedBarrel(true);
        level = new ServerLevel();
        check(corroded.canDropFromExplosion(new BlockState(corroded), level, POS, new Explosion()), "corroded explosion policy unchanged");
        check(corroded.getDrops(new BlockState(corroded), new LootParams.Builder(level)).size() == 1, "corroded preview contract unchanged");
    }

    static void comparator() {
        ReviewedBarrel block = new ReviewedBarrel(false);
        ServerLevel level = new ServerLevel();
        check(block.hasAnalogOutputSignal(new BlockState(block)), "barrel advertises comparator");
        int[][] cases = {{0,0}, {1,1}, {1066,1}, {1067,2}, {8000,8}, {16000,15}};
        for(int[] c : cases) {
            level.be = new BarrelBlockEntity(c[0], 16000);
            check(block.getAnalogOutputSignal(new BlockState(block), level, POS) == c[1], "existing ceil formula: " + c[0]);
        }
        level.be = null;
        check(block.getAnalogOutputSignal(new BlockState(block), level, POS) == 0, "missing BE returns zero");
        ReviewedBarrel corroded = new ReviewedBarrel(true);
        check(corroded.getAnalogOutputSignal(new BlockState(corroded), level, POS) == 0, "corroded returns zero");
    }

    public static void main(String[] args) {
        placement();
        barrelLifecycle();
        comparator();
        System.out.println("PASS " + checks + " method-level assertions; no Minecraft runtime claim");
    }
}
