package com.hbm.blockentity.machine.storage;

import com.hbm.blockentity.IPersistentNBT;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.machine.BarrelBlock;
import com.hbm.handler.pollution.PollutionHandler;
import com.hbm.handler.radiation.ChunkRadiationManager;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.fluid.trait.FT_Corrosive;
import com.hbm.inventory.fluid.trait.FT_Polluting;
import com.hbm.inventory.fluid.trait.FT_VentRadiation;
import com.hbm.inventory.fluid.trait.FluidTrait;
import com.hbm.items.block.BlastInfoBlockItem;
import com.hbm.items.block.BlockItemBase;
import com.hbm.items.machine.IItemFluidIdentifier;
import com.hbm.util.TagsUtil;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Explosion;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.EntityBlock;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.storage.loot.LootParams;
import net.minecraft.world.level.storage.loot.parameters.LootContextParams;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;

import java.lang.reflect.Method;
import java.util.*;

/**
 * Goal 19A corroded barrel over the production BarrelBlock and BarrelBlockEntity. Ticks go through the block's own ticker;
 * placement, removal, block entity creation and drops go through the declared chunk services of goal19a_regression/stubs.py,
 * which follow the 1.21.1 bodies cited in report.json. Not a game, save, GUI or dedicated-server run.
 */
public class Goal19ABarrelRegression {

    static final BlockPos P = new BlockPos(0, 64, 0);
    static final BlockPos Q = new BlockPos(8, 64, 0);
    static int checks, ticks, scenarios;

    static void check(boolean condition, String label) {
        checks++;
        if(!condition) throw new AssertionError(label);
    }

    static Block plastic() { return NtmBlocks.BARREL_PLASTIC.get(); }
    static Block steel() { return NtmBlocks.BARREL_STEEL.get(); }
    static Block corroded() { return NtmBlocks.BARREL_CORRODED.get(); }
    static Block tcalloy() { return NtmBlocks.BARREL_TCALLOY.get(); }

    static ServerLevel level() {
        PollutionHandler.reset();
        ChunkRadiationManager.proxy.increments.clear();
        return new ServerLevel();
    }

    static BarrelBlockEntity place(ServerLevel level, BlockPos pos, Block block) {
        check(level.setBlock(pos, block.defaultBlockState(), 3), "placed " + block);
        check(level.entities.get(pos) instanceof BarrelBlockEntity, "placing " + block + " creates its block entity");
        return (BarrelBlockEntity) level.entities.get(pos);
    }

    static BarrelBlockEntity filled(ServerLevel level, BlockPos pos, Block block, FluidType type, int fill) {
        BarrelBlockEntity barrel = place(level, pos, block);
        barrel.tank.setTankType(type);
        barrel.tank.setFill(fill);
        return barrel;
    }

    /** Six distinct stacks, 10..15 items: 75 items in total. */
    static void fillSlots(BarrelBlockEntity barrel) {
        for(int i = 0; i < 6; i++) barrel.slots.set(i, new ItemStack(new Item("fixture:slot_" + i), 10 + i));
    }

    /** The ticker the chunk registers for the block entity's state (LevelChunk.updateBlockEntityTicker -> state getTicker). */
    @SuppressWarnings({"unchecked", "rawtypes"})
    static void tick(ServerLevel level, BlockPos pos) {
        // The ticker is looked up for each tick, so a replaced block ticks with its new block's ticker.
        BlockState state = level.getBlockState(pos);
        BlockEntity be = level.entities.get(pos);
        BlockEntityTicker ticker = ((EntityBlock) state.getBlock()).getTicker(level, state, (BlockEntityType) NtmBlockEntityTypes.BARREL.get());
        // A precondition of every tick, not counted as an assertion.
        if(ticker == null || be == null) throw new AssertionError("a ticking barrel at " + pos);
        ticker.tick(level, pos, state, be);
        ticks++;
    }

    static List<ItemStack> bodies(ServerLevel level) {
        List<ItemStack> out = new ArrayList<>();
        for(Level.Drop drop : level.drops) if(!drop.kind().equals("slot")) out.add(drop.stack());
        return out;
    }

    static int slotItems(ServerLevel level) {
        int n = 0;
        for(Level.Drop drop : level.drops) if(drop.kind().equals("slot")) n += drop.stack().getCount();
        return n;
    }

    static CompoundTag persistent(ItemStack stack) {
        return TagsUtil.getCustomData(stack).getCompound(IPersistentNBT.NBT_PERSISTENT_KEY);
    }

    // ---- Engine orchestrations (cited in report.json) -------------------------------------------------------------------

    /** ServerPlayerGameMode.destroyBlock: block entity first, removeBlock (-> onDestroyedByPlayer -> Level.removeBlock), then playerDestroy in survival. */
    static void playerBreak(ServerLevel level, BlockPos pos, boolean creative) {
        BlockState state = level.getBlockState(pos);
        BlockEntity be = level.getBlockEntity(pos);
        Player player = new Player();
        player.creative = creative;
        state = state.getBlock().playerWillDestroy(level, pos, state, player);
        boolean removed = level.removeBlock(pos, false);
        if(!creative && removed) state.getBlock().playerDestroy(level, player, pos, state, be, ItemStack.EMPTY);
    }

    /** BlockBehaviour.onExplosionHit: gate, block entity, spawnAfterBreak, loot, then onBlockExploded. */
    static void vanillaExplosion(ServerLevel level, BlockPos pos) {
        BlockState state = level.getBlockState(pos);
        Explosion explosion = new Explosion();
        if(state.canDropFromExplosion(level, pos, explosion)) {
            BlockEntity be = state.hasBlockEntity() ? level.getBlockEntity(pos) : null;
            LootParams.Builder builder = new LootParams.Builder(level).withParameter(LootContextParams.ORIGIN, Vec3.atCenterOf(pos))
                    .withParameter(LootContextParams.TOOL, ItemStack.EMPTY).withOptionalParameter(LootContextParams.BLOCK_ENTITY, be);
            state.spawnAfterBreak(level, pos, ItemStack.EMPTY, false);
            for(ItemStack drop : state.getDrops(builder)) level.drops.add(new Level.Drop("explosion", drop));
        }
        state.onBlockExploded(level, pos, explosion);
    }

    /** NTM BlockProcessorStandard.process: gate, loot with the block entity, the drop-chance sample, then onBlockExploded. */
    static void ntmExplosion(ServerLevel level, BlockPos pos, float chance, float sample) {
        BlockState state = level.getBlockState(pos);
        Explosion explosion = new Explosion();
        if(state.canDropFromExplosion(level, pos, explosion)) {
            LootParams.Builder builder = new LootParams.Builder(level).withParameter(LootContextParams.ORIGIN, Vec3.atCenterOf(pos))
                    .withParameter(LootContextParams.TOOL, ItemStack.EMPTY).withOptionalParameter(LootContextParams.BLOCK_ENTITY, level.getBlockEntity(pos));
            List<ItemStack> drops = state.getDrops(builder);
            if(sample <= chance) for(ItemStack drop : drops) level.drops.add(new Level.Drop("explosion", drop));
        }
        state.onBlockExploded(level, pos, explosion);
    }

    static class Identifier extends Item implements IItemFluidIdentifier {
        final FluidType type;
        Identifier(FluidType type) { super("fixture:fluid_identifier"); this.type = type; }
        @Override public FluidType getType(Level level, BlockPos pos, ItemStack stack) { return this.type; }
    }

    /** Counts the dispatch of the release to every trait of the fluid. */
    static class CountingTrait extends FluidTrait {
        final List<String> calls = new ArrayList<>();
        @Override public void onFluidRelease(Level level, BlockPos pos, FluidTank tank, int amount, FluidReleaseType type) {
            this.calls.add(pos + "/" + amount + "/" + type + "/" + tank.getTankType());
        }
    }

    // ---- Scenarios -------------------------------------------------------------------------------------------------------

    static void registration() {
        BarrelBlock corroded = (BarrelBlock) corroded();
        check(corroded.isCorroded() && corroded.getCapacity() == 16_000, "the corroded barrel holds 16,000 mB");
        check(((BarrelBlock) plastic()).getCapacity() == 12_000 && ((BarrelBlock) steel()).getCapacity() == 16_000
                && ((BarrelBlock) tcalloy()).getCapacity() == 24_000 && !((BarrelBlock) steel()).isCorroded(), "the other barrels are unchanged");
        BlockEntityType<?> type = NtmBlockEntityTypes.BARREL.get();
        for(Block block : List.of(plastic(), steel(), corroded(), tcalloy())) {
            check(type.isValid(block.defaultBlockState()), "the BARREL block entity type accepts " + block);
        }
        BlockEntity created = corroded.newBlockEntity(P, corroded.defaultBlockState());
        check(created instanceof BarrelBlockEntity barrel && barrel.tank.getMaxFill() == 16_000 && barrel.tank.getTankType() == Fluids.NONE,
                "the corroded barrel creates its block entity with an empty 16,000 mB tank");
        ServerLevel level = level();
        check(corroded.getTicker(level, corroded.defaultBlockState(), NtmBlockEntityTypes.BARREL.get()) != null, "the corroded barrel ticks");

        // A corroded barrel saved before Goal 19A has no block entity; the first getBlockEntity creates it (LevelChunk IMMEDIATE).
        level.states.put(P, corroded.defaultBlockState());
        check(level.entities.get(P) == null, "a pre-19A corroded barrel has no block entity");
        BlockEntity lazy = level.getBlockEntity(P);
        check(lazy instanceof BarrelBlockEntity barrel && barrel.tank.getMaxFill() == 16_000 && barrel.tank.getFill() == 0 && barrel.mode == 0
                && level.created.equals(List.of(P)), "the first getBlockEntity gives a saved corroded barrel an empty block entity");
        check(level.getBlockEntity(P) == lazy && level.created.size() == 1, "the block entity is created once");

        // Block entity NBT keeps the existing keys.
        BarrelBlockEntity barrel = (BarrelBlockEntity) lazy;
        barrel.tank.setTankType(Fluids.NITRIC_ACID);
        barrel.tank.setFill(4_321);
        barrel.mode = 2;
        CompoundTag tag = new CompoundTag();
        barrel.saveAdditional(tag, null);
        check(tag.contains("mode") && tag.contains("tank") && tag.contains("tank_type") && tag.contains("tank_max"), "block entity NBT keeps the mode and tank keys");
        BarrelBlockEntity loaded = (BarrelBlockEntity) corroded.newBlockEntity(Q, corroded.defaultBlockState());
        loaded.loadAdditional(tag, null);
        check(loaded.tank.getTankType() == Fluids.NITRIC_ACID && loaded.tank.getFill() == 4_321 && loaded.mode == 2, "block entity NBT round trip");
    }

    static void noGui() {
        for(boolean sneaking : new boolean[] {false, true}) {
            ServerLevel level = level();
            BarrelBlockEntity barrel = place(level, P, corroded());
            Player player = new Player();
            player.sneaking = sneaking;
            player.main = new ItemStack(new Identifier(Fluids.WATZ));
            InteractionResult result = level.getBlockState(P).useWithoutItem(level, player, new BlockHitResult(P));
            check(result == InteractionResult.PASS && player.opened.isEmpty() && player.messages.isEmpty() && barrel.tank.getTankType() == Fluids.NONE,
                    "a corroded barrel has no GUI and ignores identifiers (sneaking=" + sneaking + ")");
        }
        ServerLevel level = level();
        BarrelBlockEntity barrel = place(level, P, steel());
        Player player = new Player();
        check(level.getBlockState(P).useWithoutItem(level, player, new BlockHitResult(P)) == InteractionResult.CONSUME && player.opened.size() == 1,
                "control: a steel barrel opens its GUI");
        player.sneaking = true;
        player.main = new ItemStack(new Identifier(Fluids.WATZ));
        check(level.getBlockState(P).useWithoutItem(level, player, new BlockHitResult(P)) == InteractionResult.CONSUME && barrel.tank.getTankType() == Fluids.WATZ,
                "control: a sneaking identifier sets a steel barrel's type");
    }

    static void leak() throws Exception {
        ServerLevel level = level();
        BarrelBlockEntity barrel = filled(level, P, corroded(), Fluids.WATZ, 100);
        CountingTrait counter = new CountingTrait();
        Fluids.WATZ.traits.put(CountingTrait.class, counter);
        try {
            level.random.fixed.put(3 * 60 * 20, 1);
            level.random.script(3, 1);
            tick(level, P); // settles the comparator; no leak
            check(barrel.tank.getFill() == 100 && counter.calls.isEmpty(), "no leak on a 1-in-3 miss");
            int[] rolls = {0, 1, 2, 0};
            int expected = 100;
            for(int roll : rolls) {
                level.random.bounds.clear();
                level.random.script(3, roll);
                int dirty = barrel.dirty;
                tick(level, P);
                check(level.random.bounds.equals(List.of(3, 3 * 60 * 20)), "each corroded tick rolls the 1-in-3 leak, then the 1-in-3,600 self-destruct");
                if(roll == 0) expected--;
                check(barrel.tank.getFill() == expected, "a 1-in-3 leak removes exactly 1 mB per hit");
                check(barrel.dirty - dirty == (roll == 0 ? 1 : 0), "a leak marks the barrel for saving");
            }
            check(counter.calls.equals(List.of(P + "/1/SPILL/WATZ", P + "/1/SPILL/WATZ")), "each leak dispatches one 1 mB SPILL release to every trait");
            float poison = Fluids.WATZ.getTrait(FT_Polluting.class).releaseMap.get(PollutionHandler.PollutionType.POISON);
            check(PollutionHandler.events.size() == 2 && PollutionHandler.events.stream().allMatch(e -> e.type() == PollutionHandler.PollutionType.POISON && e.amount() == poison),
                    "the polluting trait releases its POISON spill amount once per leaked mB");
            float rad = Fluids.WATZ.getTrait(FT_VentRadiation.class).getRadPerMB();
            check(ChunkRadiationManager.proxy.increments.equals(List.of(rad, rad)), "the vent radiation trait releases 1 mB worth of radiation per leak");

            // An empty barrel never reaches the interaction; the last millibar leaks to zero.
            barrel.tank.setFill(1);
            level.random.script(3, 0);
            tick(level, P);
            check(barrel.tank.getFill() == 0, "the last millibar leaks out");
            level.random.bounds.clear();
            counter.calls.clear();
            tick(level, P);
            check(level.random.bounds.isEmpty() && counter.calls.isEmpty() && barrel.tank.getFill() == 0, "an empty corroded barrel neither leaks nor rolls");

            // The local lower bound: called directly on an empty tank, the leak keeps the fill at zero (the original would reach -1).
            Method interaction = BarrelBlockEntity.class.getDeclaredMethod("checkFluidInteraction");
            interaction.setAccessible(true);
            level.random.script(3, 0);
            interaction.invoke(barrel);
            check(barrel.tank.getFill() == 0, "the leak never takes the fill below zero (local bound)");
        } finally {
            Fluids.WATZ.traits.remove(CountingTrait.class);
        }

        // The observed rate over 30,000 seeded ticks (self-destruct suppressed): 1 in 3, within five standard deviations.
        level = level();
        barrel = filled(level, P, corroded(), Fluids.NITRIC_ACID, 16_000);
        level.random.setSeed(19_019L);
        level.random.fixed.put(3 * 60 * 20, 1);
        for(int i = 0; i < 30_000; i++) tick(level, P);
        int leaked = 16_000 - barrel.tank.getFill();
        check(Math.abs(leaked - 10_000) < 5 * Math.sqrt(30_000 * (1.0 / 3) * (2.0 / 3)), "the leak rate is 1 in 3 per tick (" + leaked + " in 30,000)");
    }

    static void selfDestruct() {
        ServerLevel level = level();
        BarrelBlockEntity barrel = filled(level, P, corroded(), Fluids.WATZ, 500);
        fillSlots(barrel);
        level.random.script(3, 1);
        level.random.script(3 * 60 * 20, 0);
        int packs = barrel.packs;
        tick(level, P);
        check(level.getBlockState(P).isAir() && level.destroyed.equals(List.of(P)), "the 1-in-3,600 roll destroys the corroded barrel");
        check(barrel.isRemoved() && level.entities.get(P) == null, "its block entity is removed");
        check(bodies(level).isEmpty(), "self-destruct leaves no barrel body");
        check(slotItems(level) == 0, "a corroded barrel never drops its slot contents: self-destruct");
        check(barrel.packs == packs, "a destroyed barrel is not synced again");
        check(PollutionHandler.events.isEmpty() && barrel.tank.getFill() == 500, "self-destruct releases nothing beyond the leak");
    }

    static void conversion() {
        check(Fluids.NITRIC_ACID.isHighlyCorrosive() && Fluids.SCHRABIDIC.isHighlyCorrosive() && Fluids.WATZ.isHighlyCorrosive(), "nitric acid (60), WATZ (60) and schrabidic acid (75) are highly corrosive");
        for(int fill : new int[] {7_777, 16_000}) {
            ServerLevel level = level();
            BarrelBlockEntity barrel = filled(level, P, steel(), Fluids.NITRIC_ACID, fill);
            barrel.mode = 2;
            fillSlots(barrel);
            level.random.bounds.clear();
            int packs = barrel.packs;
            tick(level, P);
            check(level.getBlockState(P).is(corroded()), "a steel barrel holding nitric acid becomes a corroded barrel (" + fill + " mB)");
            // Its packet would carry the steel barrel's mode to the corroded block entity now at this position on the client.
            check(barrel.packs == packs, "the replaced steel block entity sends no stale sync");
            check(level.random.bounds.isEmpty(), "the steel barrel rolls nothing before it corrodes");
            check(barrel.isRemoved() && level.entities.get(P) instanceof BarrelBlockEntity replacement && replacement != barrel,
                    "the steel block entity is replaced by a corroded one");
            BarrelBlockEntity replacement = (BarrelBlockEntity) level.entities.get(P);
            check(replacement.tank.getTankType() == Fluids.NITRIC_ACID && replacement.tank.getFill() == fill && replacement.tank.getMaxFill() == 16_000,
                    "the corroded barrel keeps the fluid type and fill");
            check(replacement.mode == 0, "the corroded barrel's mode starts over");
            check(bodies(level).isEmpty(), "the replacement drops no steel barrel body");
            check(slotItems(level) == 75 && level.drops.size() == 6, "the steel barrel's six stacks drop exactly once");
            check(barrel.slots.stream().allMatch(ItemStack::isEmpty) && replacement.slots.stream().allMatch(ItemStack::isEmpty), "no slot item is carried or kept twice");
            // From the next tick on it is a corroded barrel.
            level.random.bounds.clear();
            level.random.script(3, 1);
            level.random.script(3 * 60 * 20, 1);
            tick(level, P);
            check(level.random.bounds.equals(List.of(3, 3 * 60 * 20)) && replacement.tank.getFill() == fill, "the replacement ticks as a corroded barrel");
        }
    }

    static void sulfuric() {
        check(!new FT_Corrosive(50).isHighlyCorrosive() && new FT_Corrosive(51).isHighlyCorrosive(), "sulfuric acid (50): the highly corrosive threshold is a rating above 50");
        ServerLevel level = level();
        BarrelBlockEntity barrel = filled(level, P, steel(), Fluids.SULFURIC_ACID, 1_000);
        tick(level, P);
        check(level.getBlockState(P).is(steel()) && level.entities.get(P) == barrel && barrel.tank.getFill() == 1_000 && level.drops.isEmpty(),
                "sulfuric acid (50) leaves a steel barrel unchanged");
        check(Fluids.SULFURIC_ACID.isCorrosive() && !Fluids.SULFURIC_ACID.isHighlyCorrosive(), "sulfuric acid (50) is corrosive but not highly corrosive");
    }

    static void otherBarrels() {
        ServerLevel level = level();
        BarrelBlockEntity barrel = filled(level, P, tcalloy(), Fluids.SCHRABIDIC, 2_000);
        tick(level, P);
        check(level.getBlockState(P).is(tcalloy()) && level.entities.get(P) == barrel && barrel.tank.getFill() == 2_000 && level.random.bounds.isEmpty(),
                "a tcalloy barrel holds highly corrosive fluid unchanged");
        level = level();
        barrel = filled(level, P, plastic(), Fluids.NITRIC_ACID, 2_000);
        tick(level, P);
        check(level.getBlockState(P).isAir() && level.destroyed.equals(List.of(P)) && bodies(level).isEmpty(),
                "a plastic barrel still melts under a corrosive fluid instead of corroding");
        level = level();
        barrel = filled(level, P, corroded(), Fluids.NITRIC_ACID, 2_000);
        level.random.script(3, 1);
        level.random.script(3 * 60 * 20, 1);
        tick(level, P);
        check(level.getBlockState(P).is(corroded()) && level.entities.get(P) == barrel && level.replaced.size() == 1, "a corroded barrel is not replaced again");
    }

    static BarrelBlockEntity corrodedWithData(ServerLevel level) {
        BarrelBlockEntity barrel = filled(level, P, corroded(), Fluids.WATZ, 1_234);
        barrel.mode = 1;
        fillSlots(barrel);
        return barrel;
    }

    static void checkBody(ItemStack body, String trigger) {
        CompoundTag data = persistent(body);
        check(body.getItem() == corroded().asItem() && body.getCount() == 1 && data.getInt("tank") == 1_234 && data.getShort("mode") == 1
                && data.getInt("tank_type") == Fluids.WATZ.getID(), "the corroded body keeps its persistent tank: " + trigger);
    }

    static void lifecycle() {
        for(String trigger : List.of("survival", "creative", "vanilla TNT", "NTM standard", "NTM no-drop", "destroyBlock(true)")) {
            ServerLevel level = level();
            BarrelBlockEntity barrel = corrodedWithData(level);
            switch(trigger) {
                case "survival" -> playerBreak(level, P, false);
                case "creative" -> playerBreak(level, P, true);
                case "vanilla TNT" -> vanillaExplosion(level, P);
                case "NTM standard" -> ntmExplosion(level, P, 1F, 0.25F);
                case "NTM no-drop" -> ntmExplosion(level, P, 0F, 0.25F);
                default -> level.destroyBlock(P, true);
            }
            int expected = trigger.equals("NTM no-drop") ? 0 : 1;
            check(bodies(level).size() == expected, "corroded body count " + expected + ": " + trigger);
            if(expected == 1) checkBody(bodies(level).get(0), trigger);
            check(slotItems(level) == 0, "a corroded barrel never drops its slot contents: " + trigger);
            check(level.getBlockState(P).isAir() && barrel.isRemoved(), "the corroded barrel is gone: " + trigger);
        }
        // Pre-19A corroded barrels without a block entity gain an empty one when broken and drop one plain body.
        for(String trigger : List.of("survival", "vanilla TNT")) {
            ServerLevel level = level();
            level.states.put(P, corroded().defaultBlockState());
            if(trigger.equals("survival")) playerBreak(level, P, false);
            else vanillaExplosion(level, P);
            check(level.created.equals(List.of(P)), "breaking a saved corroded barrel creates its block entity first: " + trigger);
            check(bodies(level).size() == 1 && bodies(level).get(0).getItem() == corroded().asItem() && !TagsUtil.hasCustomData(bodies(level).get(0)),
                    "a saved corroded barrel drops one plain body: " + trigger);
        }
        // Control: a steel barrel drops its body and its six stacks.
        ServerLevel level = level();
        BarrelBlockEntity barrel = filled(level, P, steel(), Fluids.WATER, 500);
        fillSlots(barrel);
        playerBreak(level, P, false);
        check(bodies(level).size() == 1 && slotItems(level) == 75, "control: a broken steel barrel drops its body and its slots");
    }

    static void persistence() {
        ServerLevel level = level();
        BarrelBlockEntity barrel = filled(level, P, corroded(), Fluids.NITRIC_ACID, 16_000);
        barrel.mode = 2;
        playerBreak(level, P, false);
        check(bodies(level).size() == 1, "the full corroded barrel drops one body");
        ItemStack body = bodies(level).get(0);
        check(persistent(body).getInt("tank") == 16_000 && persistent(body).getInt("tank_max") == 16_000, "the body records 16,000 of 16,000 mB");

        BarrelBlockEntity placed = place(level, Q, corroded());
        corroded().setPlacedBy(level, Q, level.getBlockState(Q), new Player(), body);
        check(placed.tank.getTankType() == Fluids.NITRIC_ACID && placed.tank.getFill() == 16_000 && placed.tank.getMaxFill() == 16_000 && placed.mode == 2,
                "placing the body restores 16,000 mB of nitric acid and the mode");

        List<Component> lines = new ArrayList<>();
        new BlockItemBase(corroded(), new Item.Properties()).appendHoverText(body, new Item.TooltipContext(), lines, new TooltipFlag());
        check(lines.size() == 3, "corroded body tooltip: capacity, leaky, contents");
        check(lines.get(2).literal && lines.get(2).getString().equals("16000/16000mB hbmfluid.nitric_acid") && lines.get(2).getStyle() == ChatFormatting.YELLOW,
                "the body tooltip shows 16000/16000mB of its fluid");
    }

    static void tooltip() {
        List<Component> lines = new ArrayList<>();
        new BlockItemBase(corroded(), new Item.Properties()).appendHoverText(new ItemStack(corroded()), new Item.TooltipContext(), lines, new TooltipFlag());
        check(lines.size() == 2, "the corroded tooltip has two lines");
        check(lines.get(0).getString().equals("desc.capacity") && Arrays.equals(lines.get(0).getArgs(), new Object[] {"16,000"}) && lines.get(0).getStyle() == ChatFormatting.AQUA,
                "corroded tooltip: AQUA capacity 16,000");
        check(lines.get(1).getString().equals("desc.leaky") && lines.get(1).getArgs().length == 0 && lines.get(1).getStyle() == ChatFormatting.RED,
                "corroded tooltip: RED leaky");
        List<Component> steelLines = new ArrayList<>();
        new BlockItemBase(steel(), new Item.Properties()).appendHoverText(new ItemStack(steel()), new Item.TooltipContext(), steelLines, new TooltipFlag());
        check(steelLines.stream().map(Component::getString).toList().equals(List.of("desc.capacity", "desc.canhot", "desc.cancor", "desc.cannothighcor", "desc.cannotam")),
                "control: the steel tooltip is unchanged");
    }

    static void gravel() {
        Block gravel = NtmBlocks.GRAVEL_OBSIDIAN.get();
        check(gravel.getExplosionResistance() == 20.0F, "gravel_obsidian explosion resistance 20 (Block.getExplosionResistance)");
        List<Component> lines = new ArrayList<>();
        BlastInfoBlockItem item = new BlastInfoBlockItem(gravel, new Item.Properties());
        item.appendHoverText(new ItemStack(item), new Item.TooltipContext(), lines, new TooltipFlag());
        Component info = lines.get(lines.size() - 1);
        check(info.getString().equals("block.hbmsntm.obj_blast_info.desc") && Arrays.equals(info.getArgs(), new Object[] {20.0F}),
                "gravel_obsidian explosion resistance 20 in the blast-info tooltip");
        ServerLevel level = level();
        float resistance = gravel.defaultBlockState().getExplosionResistance(level, P, null);
        check(resistance == 20.0F, "gravel_obsidian explosion resistance 20 for NTM explosions (state path)");
        check(resistance < 50, "a stray cog's < 50 test now passes for gravel_obsidian");
    }

    static void comparator() {
        ServerLevel level = level();
        filled(level, P, corroded(), Fluids.WATZ, 8_000);
        BlockState state = level.getBlockState(P);
        check(state.hasAnalogOutputSignal() && state.getAnalogOutputSignal(level, P) == 8, "a half-full corroded barrel gives comparator 8");
    }

    public static void main(String[] args) throws Exception {
        Set<String> only = args.length > 1 ? new HashSet<>(Arrays.asList(args[1].split(","))) : null;
        Map<String, ThrowingRunnable> all = new LinkedHashMap<>();
        all.put("registration", Goal19ABarrelRegression::registration);
        all.put("noGui", Goal19ABarrelRegression::noGui);
        all.put("leak", Goal19ABarrelRegression::leak);
        all.put("selfDestruct", Goal19ABarrelRegression::selfDestruct);
        all.put("conversion", Goal19ABarrelRegression::conversion);
        all.put("sulfuric", Goal19ABarrelRegression::sulfuric);
        all.put("otherBarrels", Goal19ABarrelRegression::otherBarrels);
        all.put("lifecycle", Goal19ABarrelRegression::lifecycle);
        all.put("persistence", Goal19ABarrelRegression::persistence);
        all.put("tooltip", Goal19ABarrelRegression::tooltip);
        all.put("gravel", Goal19ABarrelRegression::gravel);
        all.put("comparator", Goal19ABarrelRegression::comparator);
        if(only != null && !all.keySet().containsAll(only)) throw new IllegalArgumentException("unknown scenario in " + only);
        for(Map.Entry<String, ThrowingRunnable> entry : all.entrySet()) {
            if(only != null && !only.contains(entry.getKey())) continue;
            entry.getValue().run();
            scenarios++;
            System.out.println(entry.getKey() + ": passed");
        }
        System.out.println("Goal19A barrel: " + checks + " assertions; " + scenarios + " independent scenarios; " + ticks + " executed ticks");
    }

    interface ThrowingRunnable { void run() throws Exception; }
}
