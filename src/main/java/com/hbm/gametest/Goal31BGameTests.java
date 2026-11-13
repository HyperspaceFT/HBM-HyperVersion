package com.hbm.gametest;

import api.hbm.block.IToolable.ToolType;
import api.hbm.conveyor.IConveyorItem;
import api.hbm.conveyor.IConveyorPackage;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.MachineCrystallizerBlockEntity;
import com.hbm.blockentity.machine.MachineCrucibleBlockEntity;
import com.hbm.blockentity.machine.MachineElectricFurnaceBlockEntity;
import com.hbm.blockentity.network.CraneBaseBlockEntity;
import com.hbm.blockentity.network.CraneExtractorBlockEntity;
import com.hbm.blockentity.network.CraneInserterBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.network.ConveyorBaseBlock;
import com.hbm.blocks.network.ConveyorBlock;
import com.hbm.blocks.network.ConveyorBlock.Shape;
import com.hbm.blocks.network.CraneBaseBlock;
import com.hbm.blocks.network.CraneInserterBlock;
import com.hbm.entity.NtmEntityTypes;
import com.hbm.entity.item.MovingItem;
import com.hbm.interfaces.IControlReceiverFilter;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.menus.CraneExtractorMenu;
import com.hbm.inventory.menus.CraneInserterMenu;
import com.hbm.items.NtmItems;
import com.hbm.items.PartGenericItem;
import com.hbm.items.component.NtmDataComponents;
import com.hbm.items.tools.ConveyorWandItem;
import com.hbm.items.tools.ConveyorWandItem.ConveyorType;
import com.hbm.main.NuclearTechMod;
import com.hbm.module.ModulePatternMatcher;
import com.hbm.network.toserver.CompoundTagControl;
import com.hbm.registry.NtmSoundEvents;
import com.hbm.util.AdjacentInventory;
import com.mojang.authlib.GameProfile;
import com.mojang.logging.LogUtils;
import io.netty.buffer.Unpooled;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestAssertException;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.ItemTags;
import net.minecraft.world.Container;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.MenuProvider;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.inventory.ClickType;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.item.crafting.CraftingInput;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.ShapedRecipe;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.ChestBlock;
import net.minecraft.world.level.block.ComposterBlock;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.ChestType;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.capabilities.Capabilities;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.common.util.FakePlayer;
import net.neoforged.neoforge.event.PlayLevelSoundEvent;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import net.neoforged.neoforge.items.IItemHandler;
import org.slf4j.Logger;

import javax.annotation.Nullable;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.OptionalInt;
import java.util.Set;
import java.util.UUID;
import java.util.function.Consumer;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal31B: the conveyor crane base (orientation), the inserter, the extractor with its phantom filter and upgrades,
 * the item handler capability of NEO machines, copy / paste, the wand route towards a crane and the twelve recipes. Same template and
 * conventions as {@link Goal31AGameTests}; every test has its own batch.
 * <p>
 * Expected values come from the ORIGINAL at cd0cff450, cited beside each group of checks (BlockCraneBase.java:77-116,271-311;
 * TileEntityCraneBase.java:42-78,113-181; CraneInserter.java:55-146,148-202; TileEntityCraneInserter.java:27,40-93,151-158;
 * CraneExtractor.java:79-87; TileEntityCraneExtractor.java:47-198,232-246,281-292; ModulePatternMatcher.java:68-151;
 * ContainerCraneExtractor.java:24-113; IControlReceiverFilter.java:29-41; InventoryUtil.java:20-26; ItemConveyorWand.java:398-400;
 * CraftingManager.java:731-736,867-879), not from the NEO implementation. The original orients a crane by the metadata 2-5 = the INPUT
 * side with BlockPistonBase.determineOrientation (1.7.10, not part of the workspace; reconstructed: horizontal distance to the block
 * below 2 on both axes and the eye 1.82 above the feet more than 2 above the block gives UP, below the block gives DOWN, otherwise the
 * side towards the placer by yaw 0 / 90 / 180 / 270 = NORTH / EAST / SOUTH / WEST) and keeps an overridden output side in the tile
 * entity; the screwdriver model below is a literal port of TileEntityCraneBase.setOutputOverride / setInput.
 * <p>
 * Real classes and state: the registered crane blocks and block entities, the real ToolingItem screwdriver and hand drill, the real
 * ConveyorWandItem through UseOnContext, ServerPlayerGameMode.useItemOn with a NeoForge FakePlayer (a ServerPlayer, not added to the level),
 * real conveyor belts feeding the real inserter through MovingItem.tick, vanilla chests, composters, furnaces and a chiseled bookshelf,
 * NEO machines (electric furnace, iron crate, crystallizer and turbine multiblocks), the real menus (CraneExtractorMenu.clicked /
 * quickMoveStack), CompoundTagControl.apply with mock players, Capabilities.ItemHandler.BLOCK queries, NBT save / load and the
 * RecipeManager with real CraftingInput grids. The extractor's rhythm is asserted on block entities that the test itself ticks
 * ({@code updateEntity()} each game tick, never added to the level) so that the assertion can name the world time of every action;
 * one placed extractor shows that the world ticks it too.
 * Substitutes: a true diagonal step of a moving item into a cell is not constructible on a straight belt, so the "no side" entry calls
 * MovingItem.enterBlock(block, pos, null), the call MovingConveyorObject.tick makes for it; the package entity does not exist before
 * 31C, a test-local IConveyorPackage calls CraneInserterBlock.onPackageEnter; Level.hasNeighborSignal of the extractor's tick loads the
 * neighbour chunk by itself, so "an unloaded neighbour" calls the private act() through reflection on a block entity at a position that
 * is not loaded at all.
 * Not evidence: rendering (models, textures, the 30 orientations' look, top arrows), screens and their text, JEI drag and drop, sound
 * audibility, the client-side prediction of phantom clicks, other mods' pipes, multiplayer, a dedicated server with real players,
 * saved worlds, and 1.7.10 itself.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class Goal31BGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-31b]";
    private static final Direction[] H = SmokeTestSupport.HORIZONTALS;

    private static ResourceLocation id(String path) {
        return ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path);
    }

    private static Runnable passed(String test) {
        return () -> LOGGER.info("{} {} passed", TAG, test);
    }

    // ---------------------------------------------------------------- helpers

    /** A NeoForge FakePlayer that remembers the menus the world asked it to open (the real openMenu needs a client). */
    private static final class CranePlayer extends FakePlayer {
        final List<MenuProvider> opened = new ArrayList<>();

        CranePlayer(ServerLevel level) {
            super(level, new GameProfile(UUID.randomUUID(), "crane-test"));
        }

        @Override
        public OptionalInt openMenu(@Nullable MenuProvider menu, @Nullable Consumer<RegistryFriendlyByteBuf> extraDataWriter) {
            if(menu != null) this.opened.add(menu);
            return OptionalInt.empty();
        }
    }

    private static CranePlayer player(GameTestHelper helper, GameType mode, float yaw) {
        CranePlayer p = new CranePlayer(helper.getLevel());
        p.setGameMode(mode);
        Vec3 a = helper.absoluteVec(new Vec3(8.5, 1, 8.5));
        p.moveTo(a.x, a.y, a.z, yaw, 0F);
        p.getInventory().selected = 0;
        return p;
    }

    /** A test-local item riding a belt (IConveyorItem is all CraneInserterBlock.onItemEnter reads). */
    private record Carried(ItemStack stack) implements IConveyorItem {
        @Override
        public ItemStack getItemStack() {
            return this.stack;
        }
    }

    /** A test-local package: the package entity only exists from 31C on. */
    private record Pack(ItemStack[] stacks) implements IConveyorPackage {
        @Override
        public ItemStack[] getItemStacks() {
            return this.stacks;
        }
    }

    private static Block inserterBlock() {
        return NtmBlocks.CRANE_INSERTER.get();
    }

    private static Block extractorBlock() {
        return NtmBlocks.CRANE_EXTRACTOR.get();
    }

    private static BlockState crane(Block block, Direction input, Direction output) {
        return block.defaultBlockState().setValue(CraneBaseBlock.INPUT, input).setValue(CraneBaseBlock.OUTPUT, output);
    }

    private static <T extends BlockEntity> T placeCrane(GameTestHelper helper, BlockPos rel, Block block, Direction input, Direction output, Class<T> type) {
        helper.setBlock(rel, crane(block, input, output));
        return SmokeTestSupport.blockEntity(helper, rel, type);
    }

    private static CraneInserterBlockEntity placeInserter(GameTestHelper helper, BlockPos rel, Direction input, Direction output) {
        return placeCrane(helper, rel, inserterBlock(), input, output, CraneInserterBlockEntity.class);
    }

    private static CraneExtractorBlockEntity placeExtractor(GameTestHelper helper, BlockPos rel, Direction input, Direction output) {
        return placeCrane(helper, rel, extractorBlock(), input, output, CraneExtractorBlockEntity.class);
    }

    /** A block entity the test ticks itself: it is never added to the level, so the world does not tick it. */
    private static CraneExtractorBlockEntity detachedExtractor(GameTestHelper helper, BlockPos rel, Direction input, Direction output) {
        CraneExtractorBlockEntity be = new CraneExtractorBlockEntity(helper.absolutePos(rel), crane(extractorBlock(), input, output));
        be.setLevel(helper.getLevel());
        return be;
    }

    private static CraneInserterBlockEntity detachedInserter(GameTestHelper helper, BlockPos rel, Direction input, Direction output) {
        CraneInserterBlockEntity be = new CraneInserterBlockEntity(helper.absolutePos(rel), crane(inserterBlock(), input, output));
        be.setLevel(helper.getLevel());
        return be;
    }

    private static BlockState beltState(Direction input) {
        return NtmBlocks.CONVEYOR.get().defaultBlockState().setValue(ConveyorBaseBlock.HORIZONTAL_FACING, input).setValue(ConveyorBlock.SHAPE, Shape.STRAIGHT);
    }

    private static Container chest(GameTestHelper helper, BlockPos rel) {
        helper.setBlock(rel, Blocks.CHEST.defaultBlockState());
        return (Container) helper.getBlockEntity(rel);
    }

    private static Container containerAt(GameTestHelper helper, BlockPos rel) {
        BlockEntity be = helper.getBlockEntity(rel);
        check(be instanceof Container, "no container at " + rel + ": " + be);
        return (Container) be;
    }

    private static void stone(GameTestHelper helper, int x, int y, int z) {
        helper.setBlock(new BlockPos(x, y, z), Blocks.STONE.defaultBlockState());
    }

    private static ItemStack s(Item item, int count) {
        return new ItemStack(item, count);
    }

    private static int count(Container c, Item item) {
        int n = 0;
        for(int i = 0; i < c.getContainerSize(); i++) if(c.getItem(i).is(item)) n += c.getItem(i).getCount();
        return n;
    }

    private static int count(Container c, Item item, int from, int to) {
        int n = 0;
        for(int i = from; i < to; i++) if(c.getItem(i).is(item)) n += c.getItem(i).getCount();
        return n;
    }

    private static int total(Container c) {
        int n = 0;
        for(int i = 0; i < c.getContainerSize(); i++) n += c.getItem(i).getCount();
        return n;
    }

    private static void fill(Container c, Item item, int count) {
        for(int i = 0; i < c.getContainerSize(); i++) c.setItem(i, s(item, count));
    }

    /** Items lying around as item entities or riding belts in the whole test area. */
    private static int loose(GameTestHelper helper, Item item) {
        return loose(helper, item, helper.getBounds());
    }

    /** Items lying around as item entities or riding belts in the given box. */
    private static int loose(GameTestHelper helper, Item item, AABB box) {
        int n = 0;
        for(ItemEntity e : helper.getLevel().getEntitiesOfClass(ItemEntity.class, box)) if(e.getItem().is(item)) n += e.getItem().getCount();
        for(MovingItem e : helper.getLevel().getEntitiesOfClass(MovingItem.class, box)) if(e.getItemStack().is(item)) n += e.getItemStack().getCount();
        return n;
    }

    private static InteractionResult useOn(ServerLevel level, Player player, ItemStack stack, BlockPos abs, Direction face) {
        player.setItemInHand(InteractionHand.MAIN_HAND, stack);
        return stack.getItem().useOn(new UseOnContext(level, player, InteractionHand.MAIN_HAND, stack, new BlockHitResult(Vec3.atCenterOf(abs), face, abs, false)));
    }

    private static CompoundTag key(String name) {
        CompoundTag tag = new CompoundTag();
        tag.putBoolean(name, true);
        return tag;
    }

    private static CompoundTag nbt(CraneBaseBlockEntity be) {
        return be.saveWithFullMetadata(be.getLevel().registryAccess());
    }

    private static String sides(BlockState state) {
        return "input " + state.getValue(CraneBaseBlock.INPUT) + " output " + state.getValue(CraneBaseBlock.OUTPUT);
    }

    // ---------------------------------------------------------------- 1. orientation

    /** BlockPistonBase.determineOrientation, 1.7.10 (BlockCraneBase.java:93-96): yaw 0 -> meta 2 (NORTH input), 90 -> 5, 180 -> 3, 270 -> 4. */
    private static Direction inputForYaw(float yaw) {
        return switch((int) Math.floor(yaw * 4.0F / 360.0F + 0.5D) & 3) {
            case 0 -> Direction.NORTH;
            case 1 -> Direction.EAST;
            case 2 -> Direction.SOUTH;
            default -> Direction.WEST;
        };
    }

    private static Direction placeOne(GameTestHelper helper, CranePlayer player, Block block, BlockPos rel, double dx, double feetDy, double dz, float yaw, String ctx) {
        BlockPos abs = helper.absolutePos(rel);
        helper.setBlock(rel, Blocks.AIR.defaultBlockState());
        player.moveTo(abs.getX() + dx, abs.getY() + feetDy, abs.getZ() + dz, yaw, 0F);
        ItemStack stack = new ItemStack(block);
        player.setItemInHand(InteractionHand.MAIN_HAND, stack);
        BlockPos below = abs.below();
        InteractionResult r = stack.useOn(new UseOnContext(helper.getLevel(), player, InteractionHand.MAIN_HAND, stack, new BlockHitResult(Vec3.atCenterOf(below).add(0, 0.5, 0), Direction.UP, below, false)));
        check(r.consumesAction(), ctx + ": the placement gave " + r);
        BlockState state = helper.getLevel().getBlockState(abs);
        check(state.is(block), ctx + ": the placed block is " + state);
        Direction input = state.getValue(CraneBaseBlock.INPUT);
        check(state.getValue(CraneBaseBlock.OUTPUT) == input.getOpposite(), ctx + ": the output side is " + state.getValue(CraneBaseBlock.OUTPUT) + ", expected the opposite of " + input + " (BlockCraneBase.java:93-96, TileEntityCraneBase.java:36-40)");
        return input;
    }

    private static void expectInput(GameTestHelper helper, CranePlayer player, Block block, BlockPos rel, double dx, double feetDy, double dz, float yaw, String ctx, Direction expected, String message) {
        Direction got = placeOne(helper, player, block, rel, dx, feetDy, dz, yaw, ctx);
        check(got == expected, message + " (the input side is " + got + ", the placer stood at " + player.position() + ", the block at " + helper.absolutePos(rel) + ")");
    }

    // The test area lies millions of blocks out, where a float has a precision of 1 or worse; the original's horizontal distance is a float subtraction
    // (MathHelper.abs((float) entity.posX - (float) x) < 2.0F), NEO's CraneBaseBlock.determineOrientation subtracts in double, so fractional offsets are exact.
    // BlockCraneBase.java:93-96 / BlockPistonBase.determineOrientation: the input side faces the placer, the output side is the opposite one
    @GameTest(template = TEMPLATE, batch = "hbm31b_crane_place", timeoutTicks = 100)
    public static void crane_place(GameTestHelper helper) {
        guard(() -> {
            BlockPos rel = new BlockPos(8, 2, 8);
            stone(helper, 8, 1, 8);
            CranePlayer player = player(helper, GameType.SURVIVAL, 0F);
            float[] yaws = { 0F, 90F, 180F, 270F, 44F, 46F, 134F, 136F, 224F, 226F, 314F, 316F, -90F, 360F, -45.5F };
            for(Block block : new Block[] { inserterBlock(), extractorBlock() }) {
                String name = BuiltInRegistries.BLOCK.getKey(block).getPath();
                for(float yaw : yaws) {
                    // 4.5 blocks away: the placer is outside the 2 x 2 area of the vertical rule
                    Direction input = placeOne(helper, player, block, rel, 0.5, 0, 4.5, yaw, name + " yaw " + yaw);
                    check(input == inputForYaw(yaw), name + " yaw " + yaw + ": the input side is " + input + ", expected " + inputForYaw(yaw));
                }
                // within 2 blocks on both axes: eyes (feet + 1.82) more than 2 above the block -> UP, below the block -> DOWN
                expectInput(helper, player, block, rel, 1.0, 1.0, 0.5, 0F, name + " above", Direction.UP, name + ": a placer with the eyes 2.82 above the block does not get UP");
                expectInput(helper, player, block, rel, 0.5, -2.0, 1.5, 0F, name + " below", Direction.DOWN, name + ": a placer with the eyes 0.18 below the block does not get DOWN");
                expectInput(helper, player, block, rel, 0.5, 0.0, 0.5, 90F, name + " level", Direction.EAST, name + ": a placer with the eyes 1.62 above the block (inside the area) does not get the yaw side");
                // exactly 2.0 away on either axis the vertical rule does not apply any more (MathHelper.abs(...) < 2.0F)
                expectInput(helper, player, block, rel, 2.0, 1.0, 0.5, 0F, name + " 2.0 east", Direction.NORTH, name + ": 2.0 blocks away on x still gets the vertical rule");
                expectInput(helper, player, block, rel, 0.5, 1.0, 2.0, 180F, name + " 2.0 south", Direction.SOUTH, name + ": 2.0 blocks away on z still gets the vertical rule");
                expectInput(helper, player, block, rel, 0.0, 1.0, 1.5, 270F, name + " 1.5 south", Direction.UP, name + ": 1.5 blocks away does not get the vertical rule");
                expectInput(helper, player, block, rel, -1.0, -2.0, 0.0, 270F, name + " 1.0 west below", Direction.DOWN, name + ": 1.0 blocks away on the negative side does not get the vertical rule");
            }
        }).run();
        passed("crane_place").run();
        helper.succeed();
    }

    // --- the screwdriver, a literal port of TileEntityCraneBase.java:30-78 (metadata = input side, output override or UNKNOWN)

    /** The original's state: the metadata (input side) and the stored output override, null for UNKNOWN. */
    private record Orig(Direction meta, @Nullable Direction override) {
        Direction output() {
            return this.override != null ? this.override : this.meta.getOpposite();
        }
    }

    /** TileEntityCraneBase.setOutputOverride :55-65 */
    private static Orig origSetOutput(Orig s, Direction direction) {
        Direction oldSide = s.output();
        if(oldSide == direction) direction = direction.getOpposite();
        Orig n = new Orig(s.meta(), direction);
        if(direction == s.meta()) return origSetInput(n, oldSide);
        return n;
    }

    /** TileEntityCraneBase.setInput :67-78 */
    private static Orig origSetInput(Orig s, Direction direction) {
        s = new Orig(s.meta(), s.output());
        Direction oldSide = s.meta();
        if(oldSide == direction) direction = direction.getOpposite();
        boolean needSwapOutput = direction == s.output();
        Orig n = new Orig(direction, s.override());
        if(needSwapOutput) return origSetOutput(n, oldSide);
        return n;
    }

    private static BlockState screw(GameTestHelper helper, CranePlayer player, BlockPos rel, BlockState start, Direction face, boolean sneak, ItemStack tool) {
        BlockPos abs = helper.absolutePos(rel);
        helper.setBlock(rel, start);
        player.setShiftKeyDown(sneak);
        useOn(helper.getLevel(), player, tool, abs, face);
        return helper.getLevel().getBlockState(abs);
    }

    // TileEntityCraneBase.java:55-78, BlockCraneBase.java:99-116: a plain click sets the input side, a sneaking click the output side, both with the swap rules;
    // 30 of the 36 combinations are reachable from the six default placements, input equal to output never occurs
    @GameTest(template = TEMPLATE, batch = "hbm31b_crane_screwdriver", timeoutTicks = 200)
    public static void crane_screwdriver(GameTestHelper helper) {
        guard(() -> {
            BlockPos rel = new BlockPos(8, 2, 8);
            CranePlayer player = player(helper, GameType.SURVIVAL, 0F);

            // literal cases from the rules (the model below must not be the only witness): default placement input DOWN, output UP
            Block ins = inserterBlock();
            BlockState d = crane(ins, Direction.DOWN, Direction.UP);
            BlockState r;
            r = screw(helper, player, rel, d, Direction.NORTH, false, s(NtmItems.SCREWDRIVER_DESH.get(), 1));
            check(r.getValue(CraneBaseBlock.INPUT) == Direction.NORTH && r.getValue(CraneBaseBlock.OUTPUT) == Direction.UP, "plain click NORTH on (DOWN, UP): " + sides(r) + ", expected input NORTH, output UP kept (:67-78)");
            r = screw(helper, player, rel, d, Direction.UP, false, s(NtmItems.SCREWDRIVER_DESH.get(), 1));
            check(r.getValue(CraneBaseBlock.INPUT) == Direction.UP && r.getValue(CraneBaseBlock.OUTPUT) == Direction.DOWN, "plain click UP on (DOWN, UP): " + sides(r) + ", expected input UP, output DOWN (the new input lands on the output side, the output takes the old input side, :72-77)");
            r = screw(helper, player, rel, d, Direction.DOWN, false, s(NtmItems.SCREWDRIVER_DESH.get(), 1));
            check(r.getValue(CraneBaseBlock.INPUT) == Direction.UP && r.getValue(CraneBaseBlock.OUTPUT) == Direction.DOWN, "plain click DOWN (the input side) on (DOWN, UP): " + sides(r) + ", expected the opposite UP as input and the swap (:70)");
            r = screw(helper, player, rel, d, Direction.UP, true, s(NtmItems.SCREWDRIVER_DESH.get(), 1));
            check(r.getValue(CraneBaseBlock.INPUT) == Direction.UP && r.getValue(CraneBaseBlock.OUTPUT) == Direction.DOWN, "sneaking click UP (the output side) on (DOWN, UP): " + sides(r) + ", expected the opposite DOWN, which is the input, so the input moves to UP (:55-62)");
            r = screw(helper, player, rel, d, Direction.EAST, true, s(NtmItems.SCREWDRIVER_DESH.get(), 1));
            check(r.getValue(CraneBaseBlock.INPUT) == Direction.DOWN && r.getValue(CraneBaseBlock.OUTPUT) == Direction.EAST, "sneaking click EAST on (DOWN, UP): " + sides(r) + ", expected output EAST");
            r = screw(helper, player, rel, crane(ins, Direction.NORTH, Direction.UP), Direction.NORTH, true, s(NtmItems.SCREWDRIVER_DESH.get(), 1));
            check(r.getValue(CraneBaseBlock.INPUT) == Direction.UP && r.getValue(CraneBaseBlock.OUTPUT) == Direction.NORTH, "sneaking click NORTH (the input side) on (NORTH, UP): " + sides(r) + ", expected output NORTH and the input moved to the old output UP (:61-62)");
            r = screw(helper, player, rel, crane(ins, Direction.NORTH, Direction.EAST), Direction.EAST, true, s(NtmItems.SCREWDRIVER_DESH.get(), 1));
            check(r.getValue(CraneBaseBlock.INPUT) == Direction.NORTH && r.getValue(CraneBaseBlock.OUTPUT) == Direction.WEST, "sneaking click EAST (the output side) on (NORTH, EAST): " + sides(r) + ", expected the opposite WEST (:57)");
            r = screw(helper, player, rel, crane(ins, Direction.NORTH, Direction.EAST), Direction.NORTH, false, s(NtmItems.SCREWDRIVER_DESH.get(), 1));
            check(r.getValue(CraneBaseBlock.INPUT) == Direction.SOUTH && r.getValue(CraneBaseBlock.OUTPUT) == Direction.EAST, "plain click NORTH (the input side) on (NORTH, EAST): " + sides(r) + ", expected the opposite SOUTH, output kept");
            r = screw(helper, player, rel, crane(ins, Direction.NORTH, Direction.EAST), Direction.EAST, false, s(NtmItems.SCREWDRIVER_DESH.get(), 1));
            check(r.getValue(CraneBaseBlock.INPUT) == Direction.EAST && r.getValue(CraneBaseBlock.OUTPUT) == Direction.NORTH, "plain click EAST (the output side) on (NORTH, EAST): " + sides(r) + ", expected input EAST and the output moved to the old input NORTH (:72-77)");

            // the full sweep: every one of the 30 states, every face, both click kinds, both cranes, against the port of the original
            Map<String, String> transitions = new HashMap<>();
            Set<String> reached = new HashSet<>();
            int cases = 0;
            for(Block block : new Block[] { inserterBlock(), extractorBlock() }) {
                for(Direction in : Direction.values()) for(Direction out : Direction.values()) {
                    if(in == out) continue;
                    for(Direction face : Direction.values()) for(boolean sneak : new boolean[] { false, true }) {
                        // the visible state alone defines the behaviour: an explicit override equal to the default and an unknown one act alike
                        for(boolean explicit : new boolean[] { true, false }) {
                            if(!explicit && out != in.getOpposite()) continue;
                            Orig start = new Orig(in, explicit ? out : null);
                            Orig expect = sneak ? origSetOutput(start, face) : origSetInput(start, face);
                            BlockState got = screw(helper, player, rel, crane(block, in, out), face, sneak, s(NtmItems.SCREWDRIVER.get(), 1));
                            String ctx = BuiltInRegistries.BLOCK.getKey(block).getPath() + " (" + in + ", " + out + ") " + (sneak ? "sneaking " : "plain ") + "click on " + face;
                            check(got.is(block), ctx + ": the block became " + got);
                            check(got.getValue(CraneBaseBlock.INPUT) == expect.meta() && got.getValue(CraneBaseBlock.OUTPUT) == expect.output(),
                                    ctx + ": got " + sides(got) + ", expected input " + expect.meta() + " output " + expect.output() + " (TileEntityCraneBase.java:55-78)");
                            check(got.getValue(CraneBaseBlock.INPUT) != got.getValue(CraneBaseBlock.OUTPUT), ctx + ": the sides are equal");
                            if(block == ins && explicit) transitions.put(in + ">" + out + "|" + (sneak ? "s" : "p") + face, got.getValue(CraneBaseBlock.INPUT) + ">" + got.getValue(CraneBaseBlock.OUTPUT));
                            cases++;
                        }
                    }
                }
            }
            check(cases == 2 * 30 * 12 + 2 * 6 * 12, "the sweep ran " + cases + " cases");

            // reachability: starting from the six default placements and following the real clicks, exactly the 30 states with different sides appear
            List<String> frontier = new ArrayList<>();
            for(Direction in : Direction.values()) {
                String st = in + ">" + in.getOpposite();
                reached.add(st);
                frontier.add(st);
            }
            while(!frontier.isEmpty()) {
                String st = frontier.remove(frontier.size() - 1);
                String[] p = st.split(">");
                for(Direction face : Direction.values()) for(String kind : new String[] { "p", "s" }) {
                    String next = transitions.get(p[0] + ">" + p[1] + "|" + kind + face);
                    check(next != null, "no recorded transition for " + st + " " + kind + face);
                    if(reached.add(next)) frontier.add(next);
                }
            }
            check(reached.size() == 30, "the reachable combinations are " + reached.size() + ", expected 30: " + reached);
            for(Direction d1 : Direction.values()) check(!reached.contains(d1 + ">" + d1), "the state with input = output = " + d1 + " is reachable");
            check(inserterBlock().getStateDefinition().getPossibleStates().size() == 36, "the block has " + inserterBlock().getStateDefinition().getPossibleStates().size() + " states, expected 36 (6 x 6)");

            // another tool does not turn the crane (BlockCraneBase.java:100 tool != SCREWDRIVER)
            for(Item tool : new Item[] { NtmItems.HAND_DRILL.get(), NtmItems.HAND_DRILL_DESH.get(), NtmItems.DEFUSER.get() }) {
                for(boolean sneak : new boolean[] { false, true }) {
                    BlockState start = crane(ins, Direction.NORTH, Direction.EAST);
                    BlockState got = screw(helper, player, rel, start, Direction.UP, sneak, s(tool, 1));
                    check(got == start, BuiltInRegistries.ITEM.getKey(tool).getPath() + (sneak ? " sneaking" : "") + " changed the crane to " + sides(got));
                }
            }
        }).run();
        passed("crane_screwdriver").run();
        helper.succeed();
    }

    // BlockCraneBase.java:77-90: a tooling item (not only the screwdriver) and the conveyor wand do not open the screen, sneaking does not either, an empty hand and any other item do
    @GameTest(template = TEMPLATE, batch = "hbm31b_crane_use", timeoutTicks = 100)
    public static void crane_use(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos rel = new BlockPos(8, 2, 8);
            BlockPos abs = helper.absolutePos(rel);
            for(Block block : new Block[] { inserterBlock(), extractorBlock() }) {
                String name = BuiltInRegistries.BLOCK.getKey(block).getPath();
                BlockState start = crane(block, Direction.NORTH, Direction.EAST);
                helper.setBlock(rel, start);

                // [stack, sneaking, opens the screen, expected state afterwards]
                Object[][] cases = {
                        { ItemStack.EMPTY, false, true, start },
                        { ItemStack.EMPTY, true, false, start },
                        { s(Items.STICK, 1), false, true, start },
                        { s(Items.STICK, 1), true, false, start },
                        { s(NtmItems.SCREWDRIVER.get(), 1), false, false, crane(block, Direction.UP, Direction.EAST) },
                        { s(NtmItems.SCREWDRIVER.get(), 1), true, false, crane(block, Direction.NORTH, Direction.UP) },
                        { s(NtmItems.HAND_DRILL.get(), 1), false, false, start },
                        { s(NtmItems.HAND_DRILL_DESH.get(), 1), false, false, start },
                        { s(NtmItems.DEFUSER.get(), 1), false, false, start },
                        { MetaHelper.newStack(NtmItems.CONVEYOR_WAND.get(), 4, ConveyorType.REGULAR), false, false, start },
                        { MetaHelper.newStack(NtmItems.CONVEYOR_WAND.get(), 4, ConveyorType.EXPRESS), false, false, start },
                };
                for(Object[] c : cases) {
                    ItemStack stack = ((ItemStack) c[0]).copy();
                    CranePlayer p = player(helper, GameType.SURVIVAL, 0F);
                    p.setShiftKeyDown((boolean) c[1]);
                    p.setItemInHand(InteractionHand.MAIN_HAND, stack);
                    helper.setBlock(rel, start);
                    p.gameMode.useItemOn(p, level, stack, InteractionHand.MAIN_HAND, new BlockHitResult(Vec3.atCenterOf(abs), Direction.UP, abs, false));
                    String ctx = name + " with " + (stack.isEmpty() ? "an empty hand" : stack.getItem().toString()) + ((boolean) c[1] ? " sneaking" : "");
                    boolean opened = !p.opened.isEmpty();
                    check(opened == (boolean) c[2], ctx + ": the screen " + (opened ? "opened" : "did not open") + ", expected " + ((boolean) c[2] ? "opened" : "closed"));
                    if(opened) {
                        check(p.opened.size() == 1, ctx + ": " + p.opened.size() + " menus were requested");
                        AbstractContainerMenu menu = p.opened.get(0).createMenu(1, p.getInventory(), p);
                        check(block == inserterBlock() ? menu instanceof CraneInserterMenu : menu instanceof CraneExtractorMenu, ctx + ": the menu is " + menu);
                        check(menu.stillValid(p), ctx + ": the menu is not valid for the player");
                    }
                    BlockState got = level.getBlockState(abs);
                    check(got == c[3], ctx + ": the state is " + sides(got) + ", expected " + sides((BlockState) c[3]));
                }
                // a wand click through the real path starts a route on the crane's face
                CranePlayer wandHolder = player(helper, GameType.SURVIVAL, 0F);
                ItemStack wand = MetaHelper.newStack(NtmItems.CONVEYOR_WAND.get(), 4, ConveyorType.REGULAR);
                wandHolder.setItemInHand(InteractionHand.MAIN_HAND, wand);
                helper.setBlock(rel, start);
                wandHolder.gameMode.useItemOn(wandHolder, level, wand, InteractionHand.MAIN_HAND, new BlockHitResult(Vec3.atCenterOf(abs), Direction.NORTH, abs, false));
                check(ConveyorWandItem.hasStart(wand) && wandHolder.opened.isEmpty(), name + ": the wand click did not start a route on the crane (hasStart " + ConveyorWandItem.hasStart(wand) + ", menus " + wandHolder.opened.size() + ")");
            }
        }).run();
        passed("crane_use").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 2. the inserter

    /** An inserter standing at {@code rel} with its output side towards {@code output}; the item enters from the opposite side, the input side. */
    private record IRig(GameTestHelper helper, BlockPos rel, Direction input, Direction output, CraneInserterBlockEntity be) {
        BlockPos abs() {
            return this.helper.absolutePos(this.rel);
        }

        BlockPos targetRel() {
            return this.rel.relative(this.output);
        }

        void enter(ItemStack stack) {
            ((CraneInserterBlock) inserterBlock()).onItemEnter(this.helper.getLevel(), this.abs(), this.input, new Carried(stack));
        }

        void enterPack(ItemStack... stacks) {
            ((CraneInserterBlock) inserterBlock()).onPackageEnter(this.helper.getLevel(), this.abs(), null, new Pack(stacks));
        }
    }

    private static IRig inserterRig(GameTestHelper helper, BlockPos rel, Direction output) {
        Direction input = output.getOpposite();
        return new IRig(helper, rel, input, output, placeInserter(helper, rel, input, output));
    }

    // CraneInserter.java:55-58: items only enter through the input side, a diagonal step (no side) does not enter; :148 packages enter from every side
    @GameTest(template = TEMPLATE, batch = "hbm31b_inserter_enter_rules", timeoutTicks = 100)
    public static void inserter_enter_rules(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            CraneInserterBlock block = (CraneInserterBlock) inserterBlock();
            for(Direction in : Direction.values()) {
                Direction out = in == Direction.UP ? Direction.DOWN : Direction.UP;
                BlockPos rel = new BlockPos(8, 3, 8);
                BlockPos abs = helper.absolutePos(rel);
                helper.setBlock(rel, crane(inserterBlock(), in, out));
                for(Direction from : Direction.values()) {
                    check(block.canItemEnter(level, abs, from, new Carried(s(Items.STONE, 1))) == (from == in), "input " + in + ": canItemEnter from " + from + " is " + !(from == in) + " (CraneInserter.java:55-58)");
                    check(block.canPackageEnter(level, abs, from, new Pack(new ItemStack[0])), "input " + in + ": a package may not enter from " + from + " (:148)");
                }
                check(!block.canItemEnter(level, abs, null, new Carried(s(Items.STONE, 1))), "input " + in + ": an item enters without a side (UNKNOWN never equals the input side)");
                check(block.canPackageEnter(level, abs, null, new Pack(new ItemStack[0])), "input " + in + ": a package may not enter without a side");
            }
        }).run();
        passed("inserter_enter_rules").run();
        helper.succeed();
    }

    // CraneInserter.java:61-96, :98-146, InventoryUtil.java:20-26: an item goes into the inventory on the output side, then into the buffer; furnaces take fuel before input
    @GameTest(template = TEMPLATE, batch = "hbm31b_inserter_targets", timeoutTicks = 100)
    public static void inserter_targets(GameTestHelper helper) {
        guard(() -> {
            // a vanilla chest
            IRig a = inserterRig(helper, new BlockPos(8, 2, 2), Direction.WEST);
            Container chestA = chest(helper, a.targetRel());
            a.enter(s(Items.STONE, 40));
            check(count(chestA, Items.STONE) == 40 && total(a.be) == 0, "chest: the chest holds " + count(chestA, Items.STONE) + " stone and the buffer " + total(a.be) + ", expected 40 and 0");
            a.enter(s(Items.STONE, 100));
            check(count(chestA, Items.STONE) == 140 && total(a.be) == 0, "chest: after 100 more the chest holds " + count(chestA, Items.STONE) + " and the buffer " + total(a.be));

            // the big chest is one inventory (the intentional difference to the original's half chest): the other half takes what the near half cannot
            IRig b = inserterRig(helper, new BlockPos(8, 2, 5), Direction.WEST);
            BlockPos near = b.targetRel();
            helper.setBlock(near, Blocks.CHEST.defaultBlockState().setValue(ChestBlock.FACING, Direction.EAST).setValue(ChestBlock.TYPE, ChestType.LEFT));
            helper.setBlock(near.south(), Blocks.CHEST.defaultBlockState().setValue(ChestBlock.FACING, Direction.EAST).setValue(ChestBlock.TYPE, ChestType.RIGHT));
            Container nearHalf = containerAt(helper, near);
            Container farHalf = containerAt(helper, near.south());
            check(helper.getBlockState(near).getValue(ChestBlock.TYPE) == ChestType.LEFT && helper.getBlockState(near.south()).getValue(ChestBlock.TYPE) == ChestType.RIGHT, "the double chest did not stay a double chest");
            fill(nearHalf, Items.STONE, 64);
            b.enter(s(Items.DIRT, 10));
            check(count(farHalf, Items.DIRT) == 10 && count(nearHalf, Items.DIRT) == 0 && total(b.be) == 0, "double chest: the far half holds " + count(farHalf, Items.DIRT) + " dirt, the near half " + count(nearHalf, Items.DIRT) + ", the buffer " + total(b.be) + ", expected 10 / 0 / 0");

            // a composter has no block entity and only the capability (the inserter stands above it, the composter takes items from its top face)
            IRig c = inserterRig(helper, new BlockPos(8, 3, 8), Direction.DOWN);
            helper.setBlock(c.targetRel(), Blocks.COMPOSTER.defaultBlockState());
            c.enter(s(Items.PUMPKIN_PIE, 3));
            check(helper.getBlockState(c.targetRel()).getValue(ComposterBlock.LEVEL) == 1, "composter: the level is " + helper.getBlockState(c.targetRel()).getValue(ComposterBlock.LEVEL) + ", expected 1 (one pie composted, chance 1.0)");
            check(count(c.be, Items.PUMPKIN_PIE) == 2 && loose(helper, Items.PUMPKIN_PIE) == 0, "composter: the buffer holds " + count(c.be, Items.PUMPKIN_PIE) + " pies, expected the 2 the composter did not take (3 in, 1 composted)");

            // a NEO machine with face rules: only smeltable items into the input slot, nothing else
            IRig d = inserterRig(helper, new BlockPos(8, 2, 11), Direction.WEST);
            helper.setBlock(d.targetRel(), NtmBlocks.MACHINE_ELECTRIC_FURNACE.get().defaultBlockState());
            MachineElectricFurnaceBlockEntity machine = SmokeTestSupport.blockEntity(helper, d.targetRel(), MachineElectricFurnaceBlockEntity.class);
            d.enter(s(Items.RAW_IRON, 5));
            d.enter(s(Items.DIRT, 4));
            check(machine.getItem(MachineElectricFurnaceBlockEntity.SLOT_INPUT).is(Items.RAW_IRON) && machine.getItem(MachineElectricFurnaceBlockEntity.SLOT_INPUT).getCount() == 5, "machine: the input slot holds " + machine.getItem(MachineElectricFurnaceBlockEntity.SLOT_INPUT));
            check(machine.getItem(MachineElectricFurnaceBlockEntity.SLOT_BATTERY).isEmpty() && machine.getItem(MachineElectricFurnaceBlockEntity.SLOT_OUTPUT).isEmpty() && machine.getItem(MachineElectricFurnaceBlockEntity.SLOT_UPGRADE).isEmpty(), "machine: a slot other than the input took an item");
            check(count(d.be, Items.DIRT) == 4 && count(d.be, Items.RAW_IRON) == 0, "machine: the buffer holds " + count(d.be, Items.DIRT) + " dirt, expected the 4 the machine rejected");

            // neither a capability nor a container: stone and air
            IRig e = inserterRig(helper, new BlockPos(8, 2, 14), Direction.WEST);
            stone(helper, 7, 2, 14);
            e.enter(s(Items.SAND, 3));
            check(count(e.be, Items.SAND) == 3 && loose(helper, Items.SAND) == 0, "stone target: the buffer holds " + count(e.be, Items.SAND) + " sand");
            helper.setBlock(e.targetRel(), Blocks.AIR.defaultBlockState());
            e.enter(s(Items.SAND, 4));
            check(count(e.be, Items.SAND) == 7, "air target: the buffer holds " + count(e.be, Items.SAND) + " sand, expected 7");

            // a vanilla furnace: from the east side, fuel before input (slots {1, 0}, InventoryUtil.java:20-26), merging into existing stacks first
            IRig f = inserterRig(helper, new BlockPos(2, 2, 2), Direction.WEST);
            helper.setBlock(f.targetRel(), Blocks.FURNACE.defaultBlockState());
            Container furnace = containerAt(helper, f.targetRel());
            f.enter(s(Items.OAK_LOG, 1));
            check(furnace.getItem(1).is(Items.OAK_LOG) && furnace.getItem(1).getCount() == 1 && furnace.getItem(0).isEmpty(), "furnace: a log (fuel and smeltable) went to slot 0: " + furnace.getItem(0) + " / slot 1: " + furnace.getItem(1) + " (fuel slot first)");
            f.enter(s(Items.RAW_IRON, 3));
            check(furnace.getItem(0).is(Items.RAW_IRON) && furnace.getItem(0).getCount() == 3 && furnace.getItem(1).getCount() == 1, "furnace: raw iron (not a fuel) is not in the input slot: " + furnace.getItem(0) + " / " + furnace.getItem(1));
            f.enter(s(Items.OAK_LOG, 64));
            check(furnace.getItem(1).getCount() == 64 && furnace.getItem(0).getCount() == 3 && count(f.be, Items.OAK_LOG) == 1, "furnace: logs " + furnace.getItem(1).getCount() + " in the fuel slot, raw iron " + furnace.getItem(0).getCount() + ", buffer logs " + count(f.be, Items.OAK_LOG) + ", expected 64 / 3 / 1 (the fuel stack is topped up first)");
            check(furnace.getItem(2).isEmpty(), "furnace: the result slot took " + furnace.getItem(2));
            // the top face: another inserter above takes the same slot order from any face
            IRig top = inserterRig(helper, f.targetRel().above(), Direction.DOWN);
            top.enter(s(Items.RAW_IRON, 2));
            check(furnace.getItem(0).getCount() == 5 && total(top.be) == 0, "furnace from above: raw iron " + furnace.getItem(0).getCount() + ", buffer " + total(top.be) + ", expected 5 / 0");
            IRig emptyFurnace = inserterRig(helper, new BlockPos(2, 2, 6), Direction.WEST);
            helper.setBlock(emptyFurnace.targetRel(), Blocks.FURNACE.defaultBlockState());
            Container furnace2 = containerAt(helper, emptyFurnace.targetRel());
            emptyFurnace.enter(s(Items.COAL, 5));
            check(furnace2.getItem(1).is(Items.COAL) && furnace2.getItem(1).getCount() == 5 && furnace2.getItem(0).isEmpty(), "furnace: coal went to " + furnace2.getItem(0) + " / " + furnace2.getItem(1));
            IRig emptyFurnaceTop = inserterRig(helper, new BlockPos(2, 2, 9), Direction.WEST);
            helper.setBlock(emptyFurnaceTop.targetRel(), Blocks.FURNACE.defaultBlockState());
            Container furnace3 = containerAt(helper, emptyFurnaceTop.targetRel());
            emptyFurnaceTop.enter(s(Items.OAK_LOG, 2));
            emptyFurnaceTop.enter(s(Items.COAL, 1));
            check(furnace3.getItem(1).getCount() == 2 && furnace3.getItem(1).is(Items.OAK_LOG) && furnace3.getItem(0).is(Items.COAL), "furnace: a coal after logs went to " + furnace3.getItem(0) + " / " + furnace3.getItem(1) + ", expected the logs in the fuel slot and the coal rejected there (different item) and put into the input slot");
        }).run();
        passed("inserter_targets").run();
        helper.succeed();
    }

    // CraneInserter.java:61-96, :98-146: the target is full -> the buffer; the buffer is full -> destroyer on destroys, off drops at the block's centre
    @GameTest(template = TEMPLATE, batch = "hbm31b_inserter_overflow", timeoutTicks = 100)
    public static void inserter_overflow(GameTestHelper helper) {
        guard(() -> {
            IRig r = inserterRig(helper, new BlockPos(8, 2, 8), Direction.WEST);
            Container chest = chest(helper, r.targetRel());
            fill(chest, Items.STONE, 64);
            check(r.be.destroyer, "the destroyer is off by default (TileEntityCraneInserter.java:27)");

            // the target is full: the item goes into the buffer (merging into an existing stack of the same item first)
            r.enter(s(Items.SAND, 10));
            check(count(r.be, Items.SAND) == 10 && count(chest, Items.SAND) == 0, "full chest: the buffer holds " + count(r.be, Items.SAND) + " sand");
            r.enter(s(Items.SAND, 70));
            check(count(r.be, Items.SAND) == 80 && r.be.getItem(0).getCount() == 64 && r.be.getItem(1).getCount() == 16, "full chest: the buffer stacks are " + r.be.getItem(0) + " / " + r.be.getItem(1) + ", expected 64 / 16");
            for(int i = 0; i < 21; i++) r.be.setItem(i, ItemStack.EMPTY);

            // the buffer: 20 stacks of cobblestone and a stone stack of 60
            for(int i = 0; i < 20; i++) r.be.setItem(i, s(Items.COBBLESTONE, 64));
            r.be.setItem(20, s(Items.STONE, 60));
            int stoneBefore = count(chest, Items.STONE) + count(r.be, Items.STONE);
            r.enter(s(Items.STONE, 10));
            check(r.be.getItem(20).getCount() == 64 && count(chest, Items.STONE) == 27 * 64 && loose(helper, Items.STONE) == 0, "destroyer on: the stack in slot 20 is " + r.be.getItem(20) + ", loose stone " + loose(helper, Items.STONE) + "; 4 merge, 6 are destroyed (:75-96)");
            check(count(chest, Items.STONE) + count(r.be, Items.STONE) == stoneBefore + 4, "destroyer on: the stone total changed by " + (count(chest, Items.STONE) + count(r.be, Items.STONE) - stoneBefore) + ", expected +4");
            r.enter(s(Items.STONE, 10));
            check(loose(helper, Items.STONE) == 0 && count(r.be, Items.STONE) == 64, "destroyer on, buffer full: loose stone " + loose(helper, Items.STONE) + ", expected the whole stack destroyed");

            // destroyer off: the rest is dropped at the middle of the block, not destroyed
            r.be.destroyer = false;
            r.be.setItem(20, s(Items.STONE, 60));
            r.enter(s(Items.STONE, 10));
            check(r.be.getItem(20).getCount() == 64 && loose(helper, Items.STONE) == 6, "destroyer off: slot 20 " + r.be.getItem(20) + ", loose stone " + loose(helper, Items.STONE) + ", expected 64 and 6 dropped");
            r.enter(s(Items.STONE, 10));
            check(loose(helper, Items.STONE) == 16, "destroyer off, buffer full: loose stone " + loose(helper, Items.STONE) + ", expected 16");
            BlockPos abs = r.abs();
            for(ItemEntity item : helper.getLevel().getEntitiesOfClass(ItemEntity.class, helper.getBounds())) {
                check(item.position().distanceTo(new Vec3(abs.getX() + 0.5, abs.getY() + 0.5, abs.getZ() + 0.5)) < 1e-9, "a drop spawned at " + item.position() + ", expected the middle of the block (CraneInserter.java:84)");
            }
        }).run();
        passed("inserter_overflow").run();
        helper.succeed();
    }

    // CraneInserter.java:64: with a redstone signal nothing goes into the target, the item enters the buffer; TileEntityCraneInserter.java:42 the tick does not move either
    @GameTest(template = TEMPLATE, batch = "hbm31b_inserter_redstone", timeoutTicks = 100)
    public static void inserter_redstone(GameTestHelper helper) {
        guard(() -> {
            IRig r = inserterRig(helper, new BlockPos(8, 2, 8), Direction.WEST);
            Container chest = chest(helper, r.targetRel());
            helper.setBlock(r.rel.above(), Blocks.REDSTONE_BLOCK.defaultBlockState());
            check(helper.getLevel().hasNeighborSignal(r.abs()), "the redstone block does not power the inserter");
            r.enter(s(Items.STONE, 8));
            check(count(chest, Items.STONE) == 0 && count(r.be, Items.STONE) == 8, "powered: chest " + count(chest, Items.STONE) + ", buffer " + count(r.be, Items.STONE) + ", expected 0 and 8");
            r.be.updateEntity();
            check(count(chest, Items.STONE) == 0 && count(r.be, Items.STONE) == 8, "powered: the tick moved items: chest " + count(chest, Items.STONE) + ", buffer " + count(r.be, Items.STONE));
            r.enterPack(s(Items.DIRT, 5), s(Items.SAND, 2));
            check(count(chest, Items.DIRT) == 0 && count(r.be, Items.DIRT) == 5 && count(r.be, Items.SAND) == 2, "powered package: chest dirt " + count(chest, Items.DIRT) + ", buffer dirt " + count(r.be, Items.DIRT) + ", buffer sand " + count(r.be, Items.SAND) + " (:150-189)");
            helper.setBlock(r.rel.above(), Blocks.AIR.defaultBlockState());
            check(!helper.getLevel().hasNeighborSignal(r.abs()), "the inserter is still powered");
            r.be.updateEntity();
            check(count(chest, Items.STONE) == 8 && count(r.be, Items.STONE) == 0, "unpowered: the first buffer stack did not move: chest " + count(chest, Items.STONE) + ", buffer " + count(r.be, Items.STONE));
            check(count(chest, Items.DIRT) == 0 && count(chest, Items.SAND) == 0, "unpowered: only one stack may move per tick (:44-69); the chest holds dirt " + count(chest, Items.DIRT) + " and sand " + count(chest, Items.SAND));
        }).run();
        passed("inserter_redstone").run();
        helper.succeed();
    }

    // TileEntityCraneInserter.java:44-93: the first buffer stack that moves at all goes in as a whole; when no whole stack moves, one single item of the first stack that accepts one
    @GameTest(template = TEMPLATE, batch = "hbm31b_inserter_tick", timeoutTicks = 100)
    public static void inserter_tick(GameTestHelper helper) {
        guard(() -> {
            // a: one stack per tick, in slot order
            CraneInserterBlockEntity a = detachedInserter(helper, new BlockPos(8, 2, 2), Direction.EAST, Direction.WEST);
            Container chestA = chest(helper, new BlockPos(7, 2, 2));
            a.setItem(0, s(Items.STONE, 10));
            a.setItem(1, s(Items.DIRT, 10));
            a.updateEntity();
            check(count(chestA, Items.STONE) == 10 && count(chestA, Items.DIRT) == 0 && a.getItem(0).isEmpty() && a.getItem(1).getCount() == 10, "a: after one tick the chest holds stone " + count(chestA, Items.STONE) + " and dirt " + count(chestA, Items.DIRT) + " (:49-62, break after the first move)");
            a.updateEntity();
            check(count(chestA, Items.DIRT) == 10 && total(a) == 0, "a: after two ticks the chest holds dirt " + count(chestA, Items.DIRT) + ", the buffer " + total(a));
            a.updateEntity();
            check(count(chestA, Items.STONE) == 10 && count(chestA, Items.DIRT) == 10, "a: a third tick changed the chest");

            // b: a stack the target rejects is skipped, the next one that moves goes
            CraneInserterBlockEntity b = detachedInserter(helper, new BlockPos(8, 2, 5), Direction.EAST, Direction.WEST);
            helper.setBlock(new BlockPos(7, 2, 5), NtmBlocks.MACHINE_ELECTRIC_FURNACE.get().defaultBlockState());
            MachineElectricFurnaceBlockEntity machine = SmokeTestSupport.blockEntity(helper, new BlockPos(7, 2, 5), MachineElectricFurnaceBlockEntity.class);
            b.setItem(0, s(Items.DIRT, 5));
            b.setItem(1, s(Items.RAW_IRON, 3));
            b.updateEntity();
            check(machine.getItem(MachineElectricFurnaceBlockEntity.SLOT_INPUT).is(Items.RAW_IRON) && machine.getItem(MachineElectricFurnaceBlockEntity.SLOT_INPUT).getCount() == 3 && b.getItem(0).getCount() == 5 && b.getItem(1).isEmpty(),
                    "b: the machine holds " + machine.getItem(MachineElectricFurnaceBlockEntity.SLOT_INPUT) + ", the buffer " + b.getItem(0) + " / " + b.getItem(1));

            // c: a target that takes only single items (chiseled bookshelf, canPlaceItem needs the count to equal its stack limit of 1)
            CraneInserterBlockEntity c = detachedInserter(helper, new BlockPos(8, 2, 8), Direction.EAST, Direction.WEST);
            helper.setBlock(new BlockPos(7, 2, 8), Blocks.CHISELED_BOOKSHELF.defaultBlockState());
            Container shelf = containerAt(helper, new BlockPos(7, 2, 8));
            check(AdjacentInventory.insert(helper.getLevel(), helper.absolutePos(new BlockPos(7, 2, 8)), Direction.EAST, s(Items.BOOK, 5)).getCount() == 5, "the bookshelf takes a whole stack of 5 books");
            c.setItem(0, s(Items.BOOK, 5));
            for(int i = 1; i <= 5; i++) {
                c.updateEntity();
                check(count(shelf, Items.BOOK) == i && count(c, Items.BOOK) == 5 - i, "c: after tick " + i + " the shelf holds " + count(shelf, Items.BOOK) + " books and the buffer " + count(c, Items.BOOK) + " (:71-89 single items)");
            }
            c.setItem(0, ItemStack.EMPTY);
            CraneInserterBlockEntity c2 = detachedInserter(helper, new BlockPos(8, 2, 11), Direction.EAST, Direction.WEST);
            helper.setBlock(new BlockPos(7, 2, 11), Blocks.CHISELED_BOOKSHELF.defaultBlockState());
            Container shelf2 = containerAt(helper, new BlockPos(7, 2, 11));
            c2.setItem(0, s(Items.DIRT, 3));
            c2.setItem(1, s(Items.BOOK, 2));
            c2.updateEntity();
            check(count(shelf2, Items.BOOK) == 1 && c2.getItem(0).getCount() == 3 && c2.getItem(1).getCount() == 1, "c2: the shelf holds " + count(shelf2, Items.BOOK) + " books, the buffer " + c2.getItem(0) + " / " + c2.getItem(1) + ", expected the single book from the second stack");

            // d: a target with room for 10 only: the whole stack moves partly (a move of any size counts), the next stack waits
            CraneInserterBlockEntity d = detachedInserter(helper, new BlockPos(8, 2, 14), Direction.EAST, Direction.WEST);
            Container chestD = chest(helper, new BlockPos(7, 2, 14));
            fill(chestD, Items.STONE, 64);
            chestD.setItem(26, s(Items.STONE, 54));
            d.setItem(0, s(Items.STONE, 64));
            d.setItem(1, s(Items.STONE, 5));
            d.updateEntity();
            check(count(chestD, Items.STONE) == 27 * 64 && d.getItem(0).getCount() == 54 && d.getItem(1).getCount() == 5, "d: the chest holds " + count(chestD, Items.STONE) + " stone, the buffer " + d.getItem(0).getCount() + " / " + d.getItem(1).getCount() + ", expected a full chest and 54 / 5");
            d.updateEntity();
            check(d.getItem(0).getCount() == 54 && d.getItem(1).getCount() == 5, "d: a tick against a full chest changed the buffer");
        }).run();
        passed("inserter_tick").run();
        helper.succeed();
    }

    /** The original calcRedstoneFromInventory (1.7.10 Container.java; CraneInserter.java:191-196): the fill fraction of 21 slots, floor(f * 14) + 1 when any slot is filled. */
    private static int originalComparator(Container inv) {
        int filled = 0;
        float f = 0.0F;
        for(int i = 0; i < inv.getContainerSize(); i++) {
            ItemStack stack = inv.getItem(i);
            if(!stack.isEmpty()) {
                f += (float) stack.getCount() / (float) Math.min(64, stack.getMaxStackSize());
                filled++;
            }
        }
        f = f / (float) inv.getContainerSize();
        return (int) Math.floor(f * 14.0F) + (filled > 0 ? 1 : 0);
    }

    // CraneInserter.java:191-196: the comparator output follows the fill of the 21 slots
    @GameTest(template = TEMPLATE, batch = "hbm31b_inserter_comparator", timeoutTicks = 100)
    public static void inserter_comparator(GameTestHelper helper) {
        guard(() -> {
            IRig r = inserterRig(helper, new BlockPos(8, 2, 8), Direction.WEST);
            BlockPos abs = r.abs();
            BlockState state = helper.getLevel().getBlockState(abs);
            check(state.hasAnalogOutputSignal(), "the inserter has no comparator output (CraneInserter.java:191)");
            check(state.getAnalogOutputSignal(helper.getLevel(), abs) == 0 && originalComparator(r.be) == 0, "an empty buffer gives " + state.getAnalogOutputSignal(helper.getLevel(), abs));

            // [slot, item, count] lists
            Object[][][] cases = {
                    { { 0, Items.STONE, 1 } },
                    { { 0, Items.STONE, 64 } },
                    { { 0, Items.STONE, 32 }, { 1, Items.ENDER_PEARL, 8 } },
                    { { 0, Items.ENDER_PEARL, 16 }, { 5, Items.SNOWBALL, 16 } },
                    { { 3, Items.STONE, 64 }, { 4, Items.STONE, 64 }, { 5, Items.STONE, 64 }, { 6, Items.STONE, 64 }, { 7, Items.STONE, 64 }, { 8, Items.STONE, 64 }, { 9, Items.STONE, 64 }, { 10, Items.STONE, 64 }, { 11, Items.STONE, 64 }, { 12, Items.STONE, 64 } },
                    { { 20, Items.DIRT, 5 } },
            };
            for(Object[][] c : cases) {
                for(int i = 0; i < 21; i++) r.be.setItem(i, ItemStack.EMPTY);
                for(Object[] e : c) r.be.setItem((int) e[0], s((Item) e[1], (int) e[2]));
                int got = helper.getLevel().getBlockState(abs).getAnalogOutputSignal(helper.getLevel(), abs);
                check(got == originalComparator(r.be), "the buffer " + r.be.slots + " gives " + got + ", expected " + originalComparator(r.be) + " (calcRedstoneFromInventory)");
            }
            for(int i = 0; i < 21; i++) r.be.setItem(i, s(Items.STONE, 64));
            check(helper.getLevel().getBlockState(abs).getAnalogOutputSignal(helper.getLevel(), abs) == 15 && originalComparator(r.be) == 15, "a full buffer does not give 15");
            r.be.setItem(20, ItemStack.EMPTY);
            check(helper.getLevel().getBlockState(abs).getAnalogOutputSignal(helper.getLevel(), abs) == 14 && originalComparator(r.be) == 14, "20 of 21 full stacks do not give 14");
        }).run();
        passed("inserter_comparator").run();
        helper.succeed();
    }

    // CraneInserter.java:148-189: a package enters from any side; every stack follows the rules of a single item
    @GameTest(template = TEMPLATE, batch = "hbm31b_inserter_package", timeoutTicks = 100)
    public static void inserter_package(GameTestHelper helper) {
        guard(() -> {
            IRig r = inserterRig(helper, new BlockPos(8, 2, 8), Direction.WEST);
            Container chest = chest(helper, r.targetRel());
            r.enterPack(s(Items.STONE, 30), s(Items.DIRT, 3), s(Items.IRON_INGOT, 64));
            check(count(chest, Items.STONE) == 30 && count(chest, Items.DIRT) == 3 && count(chest, Items.IRON_INGOT) == 64 && total(r.be) == 0, "package into a chest: the chest holds " + total(chest) + " items, the buffer " + total(r.be));

            // the chest is full: the stacks go into the buffer, what the buffer cannot hold is destroyed
            fill(chest, Items.COBBLESTONE, 64);
            for(int i = 0; i < 20; i++) r.be.setItem(i, s(Items.SAND, 64));
            r.enterPack(s(Items.STONE, 70 - 64), s(Items.GRAVEL, 64), s(Items.GRAVEL, 5), s(Items.STONE, 3));
            check(count(r.be, Items.STONE) == 9 && count(r.be, Items.GRAVEL) == 0 && loose(helper, Items.GRAVEL) == 0, "package overflow: the buffer holds " + count(r.be, Items.STONE) + " stone (one slot left: 6 + 3), gravel " + count(r.be, Items.GRAVEL) + ", loose gravel " + loose(helper, Items.GRAVEL) + " (:176-188, destroyer on)");
            r.be.destroyer = false;
            r.enterPack(s(Items.GRAVEL, 7), s(Items.STONE, 20));
            check(loose(helper, Items.GRAVEL) == 7 && count(r.be, Items.STONE) == 29, "package overflow, destroyer off: loose gravel " + loose(helper, Items.GRAVEL) + ", buffer stone " + count(r.be, Items.STONE) + ", expected 7 and 29");

            // an empty or absent package changes nothing and throws nothing
            ((CraneInserterBlock) inserterBlock()).onPackageEnter(helper.getLevel(), r.abs(), Direction.EAST, new Pack(new ItemStack[0]));
            ((CraneInserterBlock) inserterBlock()).onPackageEnter(helper.getLevel(), r.abs(), Direction.EAST, new Pack(null));
            ((CraneInserterBlock) inserterBlock()).onPackageEnter(helper.getLevel(), r.abs(), Direction.EAST, null);
            check(count(r.be, Items.STONE) == 29, "an empty package changed the buffer");
        }).run();
        passed("inserter_package").run();
        helper.succeed();
    }

    // EntityMovingConveyorObject.java:126-165: a belt feeding the inserter through its input side hands the item over; another side does not; no side (diagonal) does not
    @GameTest(template = TEMPLATE, batch = "hbm31b_inserter_belt", timeoutTicks = 200)
    public static void inserter_belt(GameTestHelper helper) {
        // right side: belts moving west into an inserter whose input side is EAST, a chest on its west
        IRig good = inserterRig(helper, new BlockPos(8, 2, 3), Direction.WEST);
        Container chestGood = chest(helper, good.targetRel());
        helper.setBlock(new BlockPos(9, 2, 3), beltState(Direction.EAST));
        helper.setBlock(new BlockPos(10, 2, 3), beltState(Direction.EAST));
        // wrong side: belts moving south into an inserter whose input side is EAST
        CraneInserterBlockEntity wrong = placeInserter(helper, new BlockPos(4, 2, 9), Direction.EAST, Direction.WEST);
        Container chestWrong = chest(helper, new BlockPos(3, 2, 9));
        helper.setBlock(new BlockPos(4, 2, 7), beltState(Direction.NORTH));
        helper.setBlock(new BlockPos(4, 2, 8), beltState(Direction.NORTH));
        Vec3 start = helper.absoluteVec(new Vec3(10.5, 2.25, 3.5));
        Vec3 startWrong = helper.absoluteVec(new Vec3(4.5, 2.25, 7.5));
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    MovingItem a = new MovingItem(NtmEntityTypes.MOVING_ITEM.get(), level);
                    a.setPos(start.x, start.y, start.z);
                    a.setItemStack(s(Items.IRON_NUGGET, 5));
                    level.addFreshEntity(a);
                    MovingItem b = new MovingItem(NtmEntityTypes.MOVING_ITEM.get(), level);
                    b.setPos(startWrong.x, startWrong.y, startWrong.z);
                    b.setItemStack(s(Items.GOLD_NUGGET, 4));
                    level.addFreshEntity(b);
                }))
                .thenExecuteAfter(60, guard(() -> {
                    check(count(chestGood, Items.IRON_NUGGET) == 5 && total(good.be) == 0 && loose(helper, Items.IRON_NUGGET) == 0, "right side: the chest holds " + count(chestGood, Items.IRON_NUGGET) + " nuggets, the buffer " + total(good.be) + ", loose " + loose(helper, Items.IRON_NUGGET) + ", expected 5 / 0 / 0");
                    check(count(chestWrong, Items.GOLD_NUGGET) == 0 && total(wrong) == 0, "wrong side: the chest holds " + count(chestWrong, Items.GOLD_NUGGET) + " and the buffer " + total(wrong) + " nuggets, expected the inserter to refuse (CraneInserter.java:55-58)");
                    // the refused nuggets drop in the inserter cell and are pushed back over the belt and out west, where they can land on the
                    // floor of the test area at relative y 0, just below the test bounds
                    AABB below = helper.getBounds().expandTowards(0, -1, 0);
                    check(loose(helper, Items.GOLD_NUGGET, below) == 4, "wrong side: " + loose(helper, Items.GOLD_NUGGET, below) + " nuggets are left over as entities, expected the 4 that left the belt");
                }))
                .thenExecute(guard(() -> {
                    // no side: the call MovingConveyorObject.tick makes for a diagonal step (EntityMovingConveyorObject.java:132-142 passes UNKNOWN)
                    ServerLevel level = helper.getLevel();
                    IRig d = inserterRig(helper, new BlockPos(12, 2, 12), Direction.WEST);
                    Container chestD = chest(helper, d.targetRel());
                    MovingItem diagonal = new MovingItem(NtmEntityTypes.MOVING_ITEM.get(), level);
                    diagonal.setPos(helper.absoluteVec(new Vec3(12.5, 2.25, 12.5)));
                    diagonal.setItemStack(s(Items.COPPER_INGOT, 6));
                    level.addFreshEntity(diagonal);
                    diagonal.enterBlock((CraneInserterBlock) inserterBlock(), d.abs(), null);
                    check(!diagonal.isRemoved() && total(chestD) == 0 && total(d.be) == 0, "no side: the item entered (removed " + diagonal.isRemoved() + ", chest " + total(chestD) + ", buffer " + total(d.be) + ")");
                    diagonal.enterBlock((CraneInserterBlock) inserterBlock(), d.abs(), Direction.NORTH);
                    check(!diagonal.isRemoved() && total(chestD) == 0, "a side that is not the input side let the item in");
                    diagonal.enterBlock((CraneInserterBlock) inserterBlock(), d.abs(), d.input);
                    check(diagonal.isRemoved() && count(chestD, Items.COPPER_INGOT) == 6, "the input side did not take the item (removed " + diagonal.isRemoved() + ", chest " + count(chestD, Items.COPPER_INGOT) + ")");
                }))
                .thenExecute(passed("inserter_belt"))
                .thenSucceed();
    }

    // TileEntityCraneInserter.java:151-158, :141-147: control key destroyer toggles within 20 blocks, the save keys are destroyer and Items
    @GameTest(template = TEMPLATE, batch = "hbm31b_inserter_control", timeoutTicks = 100)
    public static void inserter_control(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            CraneInserterBlockEntity be = placeInserter(helper, new BlockPos(8, 2, 8), Direction.EAST, Direction.WEST);
            BlockPos abs = be.getBlockPos();
            Player player = helper.makeMockPlayer(GameType.SURVIVAL);
            Vec3 corner = Vec3.atLowerCornerOf(abs);
            check(be.destroyer, "destroyer is not on by default");
            player.setPos(corner.x + 19.9, corner.y, corner.z);
            check(be.hasPermission(player), "19.9 blocks: no permission (TileEntityCraneInserter.java:151-153 < 20)");
            CompoundTagControl.apply(player, key("destroyer"), abs);
            check(!be.destroyer, "the destroyer key within 19.9 blocks did not toggle");
            CompoundTagControl.apply(player, key("destroyer"), abs);
            check(be.destroyer, "the destroyer key did not toggle back");
            CompoundTag other = new CompoundTag();
            other.putBoolean("whitelist", true);
            other.putInt("slot", 3);
            CompoundTagControl.apply(player, other, abs);
            check(be.destroyer && total(be) == 0, "keys the inserter does not know changed it");
            player.setPos(corner.x + 20.0, corner.y, corner.z);
            check(!be.hasPermission(player), "exactly 20 blocks: permission");
            CompoundTagControl.apply(player, key("destroyer"), abs);
            check(be.destroyer, "the destroyer key from 20 blocks toggled");
            player.setPos(corner.x + 70.0, corner.y, corner.z);
            CompoundTagControl.apply(player, key("destroyer"), abs);
            check(be.destroyer, "the destroyer key from 70 blocks toggled");

            // persistence: destroyer and Items
            be.destroyer = false;
            be.setItem(0, s(Items.STONE, 12));
            be.setItem(20, s(Items.DIRT, 3));
            CompoundTag tag = nbt(be);
            check(tag.contains("destroyer", Tag.TAG_BYTE) && !tag.getBoolean("destroyer") && tag.contains("Items", Tag.TAG_LIST), "the saved keys are " + tag.getAllKeys());
            CraneInserterBlockEntity loaded = new CraneInserterBlockEntity(abs, level.getBlockState(abs));
            loaded.loadWithComponents(tag, level.registryAccess());
            check(!loaded.destroyer && loaded.getItem(0).is(Items.STONE) && loaded.getItem(0).getCount() == 12 && loaded.getItem(20).is(Items.DIRT) && loaded.getItem(20).getCount() == 3 && loaded.getContainerSize() == 21, "the loaded inserter has destroyer " + loaded.destroyer + ", slots " + loaded.slots);
            be.destroyer = true;
            CraneInserterBlockEntity loadedOn = new CraneInserterBlockEntity(abs, level.getBlockState(abs));
            loadedOn.loadWithComponents(nbt(be), level.registryAccess());
            check(loadedOn.destroyer, "destroyer on did not survive a save");
        }).run();
        passed("inserter_control").run();
        helper.succeed();
    }

    // CraneInserter.java:198-202 (dropContents 0..21), CraneExtractor.java:83-87 (9..20, no filter slots): breaking drops the block and the real slots only
    @GameTest(template = TEMPLATE, batch = "hbm31b_crane_drops", timeoutTicks = 100)
    public static void crane_drops(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            CraneInserterBlockEntity ins = placeInserter(helper, new BlockPos(4, 2, 4), Direction.EAST, Direction.WEST);
            Item[] stuff = { Items.STONE, Items.DIRT, Items.SAND, Items.GRAVEL, Items.COAL, Items.IRON_INGOT, Items.GOLD_INGOT };
            int expected = 0;
            for(int i = 0; i < 21; i++) {
                ins.setItem(i, s(stuff[i % stuff.length], 1 + i));
                expected += 1 + i;
            }
            level.destroyBlock(helper.absolutePos(new BlockPos(4, 2, 4)), true);
            int dropped = 0;
            int blocks = 0;
            for(ItemEntity e : level.getEntitiesOfClass(ItemEntity.class, helper.getBounds())) {
                if(e.getItem().is(inserterBlock().asItem())) blocks += e.getItem().getCount();
                else dropped += e.getItem().getCount();
            }
            check(blocks == 1, "the inserter dropped " + blocks + " block items, expected 1");
            check(dropped == expected, "the inserter dropped " + dropped + " items from its buffer, expected " + expected + " (all 21 slots)");
            for(int i = 0; i < stuff.length; i++) {
                int want = 0;
                for(int slot = 0; slot < 21; slot++) if(slot % stuff.length == i) want += 1 + slot;
                check(loose(helper, stuff[i]) == want, stuff[i] + ": " + loose(helper, stuff[i]) + " dropped, expected " + want);
            }

            // the extractor: the filter slots 0-8 never drop, the buffer 9-17 and the upgrades 18-19 do
            for(ItemEntity e : level.getEntitiesOfClass(ItemEntity.class, helper.getBounds())) e.discard();
            CraneExtractorBlockEntity ex = placeExtractor(helper, new BlockPos(10, 2, 10), Direction.EAST, Direction.WEST);
            for(int i = 0; i < 9; i++) ex.setItem(i, s(Items.DIAMOND, 1));
            for(int i = 9; i < 18; i++) ex.setItem(i, s(Items.EMERALD, 2));
            ex.setItem(18, s(NtmItems.UPGRADE_STACK_2.get(), 1));
            ex.setItem(19, s(NtmItems.UPGRADE_EJECTOR_3.get(), 1));
            level.destroyBlock(helper.absolutePos(new BlockPos(10, 2, 10)), true);
            check(loose(helper, Items.DIAMOND) == 0, "the extractor dropped " + loose(helper, Items.DIAMOND) + " filter items, expected 0 (phantom slots)");
            check(loose(helper, Items.EMERALD) == 18, "the extractor dropped " + loose(helper, Items.EMERALD) + " buffer items, expected 18");
            check(loose(helper, NtmItems.UPGRADE_STACK_2.get()) == 1 && loose(helper, NtmItems.UPGRADE_EJECTOR_3.get()) == 1, "the extractor dropped its upgrades " + loose(helper, NtmItems.UPGRADE_STACK_2.get()) + " / " + loose(helper, NtmItems.UPGRADE_EJECTOR_3.get()) + ", expected 1 / 1");
            check(loose(helper, extractorBlock().asItem()) == 1, "the extractor dropped " + loose(helper, extractorBlock().asItem()) + " block items, expected 1");
        }).run();
        passed("crane_drops").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 3. the extractor

    private static Item ejectorUpgrade(int tier) {
        return switch(tier) {
            case 1 -> NtmItems.UPGRADE_EJECTOR_1.get();
            case 2 -> NtmItems.UPGRADE_EJECTOR_2.get();
            default -> NtmItems.UPGRADE_EJECTOR_3.get();
        };
    }

    private static Item stackUpgrade(int tier) {
        return switch(tier) {
            case 1 -> NtmItems.UPGRADE_STACK_1.get();
            case 2 -> NtmItems.UPGRADE_STACK_2.get();
            default -> NtmItems.UPGRADE_STACK_3.get();
        };
    }

    /**
     * An extractor the test ticks itself, with its inventory on the output side (WEST) and the belt on the input side (EAST), the original's
     * switcheroo (TileEntityCraneExtractor.java:85-88). Every call of {@link #tick()} is one game tick of the block entity.
     */
    private static final class XRig {
        final GameTestHelper helper;
        final CraneExtractorBlockEntity be;
        final BlockPos rel;
        final BlockPos srcRel;
        final BlockPos beltRel;
        final List<ItemStack> log = new ArrayList<>();
        int acts;

        XRig(GameTestHelper helper, int z, boolean belt) {
            this(helper, new BlockPos(8, 2, z), Direction.EAST, Direction.WEST, belt);
        }

        XRig(GameTestHelper helper, BlockPos rel, Direction input, Direction output, boolean belt) {
            this.helper = helper;
            this.rel = rel;
            this.srcRel = rel.relative(output);
            this.beltRel = rel.relative(input);
            this.be = detachedExtractor(helper, rel, input, output);
            if(belt) {
                helper.setBlock(this.beltRel, beltState(input.getOpposite()));
                helper.setBlock(this.beltRel.relative(input), beltState(input.getOpposite()));
            }
        }

        XRig upgrades(int ejector, int stack) {
            if(ejector > 0) this.be.slots.set(CraneExtractorBlockEntity.SLOT_EJECTOR_UPGRADE, s(ejectorUpgrade(ejector), 1));
            if(stack > 0) this.be.slots.set(CraneExtractorBlockEntity.SLOT_STACK_UPGRADE, s(stackUpgrade(stack), 1));
            return this;
        }

        AABB beltBox() {
            return new AABB(this.helper.absolutePos(this.beltRel)).inflate(0.8);
        }

        /** One game tick of the block entity; returns the stacks that reached the belt during it. */
        List<ItemStack> tick() {
            ServerLevel level = this.helper.getLevel();
            for(MovingItem m : level.getEntitiesOfClass(MovingItem.class, this.beltBox())) m.discard();
            this.be.updateEntity();
            List<ItemStack> now = new ArrayList<>();
            for(MovingItem m : level.getEntitiesOfClass(MovingItem.class, this.beltBox())) now.add(m.getItemStack());
            this.log.addAll(now);
            if(!now.isEmpty()) this.acts++;
            return now;
        }
    }

    private static void expectLog(XRig rig, String ctx, Object... itemsAndCounts) {
        check(rig.log.size() == itemsAndCounts.length / 2, ctx + ": the belt received " + describe(rig.log) + ", expected " + itemsAndCounts.length / 2 + " stacks " + java.util.Arrays.toString(itemsAndCounts));
        for(int i = 0; i < rig.log.size(); i++) {
            ItemStack got = rig.log.get(i);
            check(got.is((Item) itemsAndCounts[2 * i]) && got.getCount() == (int) itemsAndCounts[2 * i + 1], ctx + ": belt stack " + i + " is " + got + ", expected " + itemsAndCounts[2 * i + 1] + " x " + itemsAndCounts[2 * i] + "; all: " + describe(rig.log));
        }
    }

    private static String describe(List<ItemStack> stacks) {
        List<String> out = new ArrayList<>();
        for(ItemStack s : stacks) out.add(s.getCount() + "x" + s.getItem());
        return out.toString();
    }

    private static void setFilter(CraneExtractorBlockEntity be, int slot, ItemStack stack, @Nullable String mode) {
        be.slots.set(slot, stack.copyWithCount(1));
        be.matcher.modes[slot] = mode;
    }

    private static int bufferTotal(Container c) {
        int n = 0;
        for(int i = 9; i < 18; i++) n += c.getItem(i).getCount();
        return n;
    }

    private static void chestSlots(Container chest, Object... slotItemCount) {
        for(int i = 0; i < slotItemCount.length; i += 3) chest.setItem((int) slotItemCount[i], s((Item) slotItemCount[i + 1], (int) slotItemCount[i + 2]));
    }

    // TileEntityCraneExtractor.java:64-74: it acts when the world time is a multiple of the delay (20, with the ejector upgrade 10 / 5 / 2) and there is no redstone signal
    @GameTest(template = TEMPLATE, batch = "hbm31b_extractor_rhythm", timeoutTicks = 200)
    public static void extractor_rhythm(GameTestHelper helper) {
        int[] delays = { 20, 10, 5, 2 };
        List<XRig> rigs = new ArrayList<>();
        List<Container> sources = new ArrayList<>();
        for(int i = 0; i < 4; i++) {
            XRig rig = new XRig(helper, 2 + 3 * i, true).upgrades(i, 0);
            Container src = chest(helper, rig.srcRel);
            fill(src, Items.STONE, 64);
            rigs.add(rig);
            sources.add(src);
        }
        XRig powered = new XRig(helper, 14, true).upgrades(3, 0);
        Container poweredSource = chest(helper, powered.srcRel);
        fill(poweredSource, Items.STONE, 64);
        helper.setBlock(powered.rel.above(), Blocks.REDSTONE_BLOCK.defaultBlockState());
        int[] acts = new int[4];
        helper.startSequence()
                .thenExecuteFor(46, guard(() -> {
                    long t = helper.getLevel().getGameTime();
                    for(int i = 0; i < 4; i++) {
                        int before = total(sources.get(i));
                        List<ItemStack> now = rigs.get(i).tick();
                        int taken = before - total(sources.get(i));
                        int expect = t % delays[i] == 0 ? 1 : 0;
                        check(taken == expect && now.size() == expect, "delay " + delays[i] + " at world time " + t + ": " + taken + " items left the chest and " + now.size() + " stacks reached the belt, expected " + expect + " (:74 getTotalWorldTime() % delay == 0)");
                        acts[i] += expect;
                    }
                    int before = total(poweredSource);
                    List<ItemStack> now = powered.tick();
                    check(before == total(poweredSource) && now.isEmpty(), "a powered extractor acted at world time " + t + " (:74 isBlockIndirectlyGettingPowered)");
                }))
                .thenExecute(guard(() -> {
                    check(acts[0] >= 2 && acts[1] >= 4 && acts[2] >= 9 && acts[3] >= 23, "the actions in 46 ticks were " + java.util.Arrays.toString(acts) + ", expected at least 2 / 4 / 9 / 23");
                    // the signal gone: the same extractor acts again at the next multiple of its delay
                    helper.setBlock(powered.rel.above(), Blocks.AIR.defaultBlockState());
                }))
                .thenExecuteFor(6, guard(() -> {
                    long t = helper.getLevel().getGameTime();
                    int before = total(poweredSource);
                    powered.tick();
                    check(before - total(poweredSource) == (t % 2 == 0 ? 1 : 0), "after the signal ended the delay 2 extractor took " + (before - total(poweredSource)) + " at world time " + t);
                }))
                .thenExecute(passed("extractor_rhythm"))
                .thenSucceed();
    }

    // TileEntityCraneExtractor.java:75-83,119,125: one item, with the stack upgrade 4 / 16 / 64, never more than the stack holds
    @GameTest(template = TEMPLATE, batch = "hbm31b_extractor_amount", timeoutTicks = 200)
    public static void extractor_amount(GameTestHelper helper) {
        int[] amounts = { 1, 4, 16, 64 };
        List<XRig> rigs = new ArrayList<>();
        for(int i = 0; i < 4; i++) {
            XRig rig = new XRig(helper, 2 + 2 * i, true).upgrades(3, i);
            fill(chest(helper, rig.srcRel), Items.STONE, 64);
            rigs.add(rig);
        }
        // a stack limit of 16 and a stack of 3 limit the amount below the upgrade
        XRig pearls = new XRig(helper, 10, true).upgrades(3, 3);
        fill(chest(helper, pearls.srcRel), Items.ENDER_PEARL, 16);
        XRig few = new XRig(helper, 12, true).upgrades(3, 1);
        chestSlots(chest(helper, few.srcRel), 0, Items.DIRT, 3, 1, Items.DIRT, 64);
        helper.startSequence()
                .thenExecuteFor(14, guard(() -> {
                    long t = helper.getLevel().getGameTime();
                    for(int i = 0; i < 4; i++) {
                        List<ItemStack> now = rigs.get(i).tick();
                        if(t % 2 == 0) {
                            check(now.size() == 1 && now.get(0).is(Items.STONE) && now.get(0).getCount() == amounts[i], "stack upgrade " + i + " at world time " + t + ": the belt received " + describe(now) + ", expected one stack of " + amounts[i] + " (:75-83)");
                        } else {
                            check(now.isEmpty(), "stack upgrade " + i + " acted at the odd world time " + t);
                        }
                    }
                    List<ItemStack> p = pearls.tick();
                    check(t % 2 != 0 ? p.isEmpty() : p.size() == 1 && p.get(0).getCount() == 16, "pearls with an amount of 64: " + describe(p) + " (min(amount, stack size) = 16, :119)");
                    List<ItemStack> f = few.tick();
                    if(t % 2 == 0 && few.acts == 1) check(f.size() == 1 && f.get(0).getCount() == 3 && f.get(0).is(Items.DIRT), "a stack of 3 with an amount of 4: " + describe(f) + ", expected 3");
                }))
                .thenExecute(guard(() -> {
                    check(few.log.size() >= 2 && few.log.get(0).getCount() == 3 && few.log.get(1).getCount() == 4, "the dirt log is " + describe(few.log) + ", expected 3 (the first stack) then 4 (the next stack)");
                }))
                .thenExecute(passed("extractor_amount"))
                .thenSucceed();
    }

    // the placed extractor is ticked by the world: in any 40 consecutive ticks it acts twice (delay 20) or 20 times (delay 2), never when powered
    @GameTest(template = TEMPLATE, batch = "hbm31b_extractor_world_tick", timeoutTicks = 200)
    public static void extractor_world_tick(GameTestHelper helper) {
        CraneExtractorBlockEntity slow = placeExtractor(helper, new BlockPos(8, 2, 2), Direction.EAST, Direction.WEST);
        Container slowSource = chest(helper, new BlockPos(7, 2, 2));
        fill(slowSource, Items.STONE, 64);
        helper.setBlock(new BlockPos(9, 2, 2), beltState(Direction.WEST));
        CraneExtractorBlockEntity fast = placeExtractor(helper, new BlockPos(8, 2, 6), Direction.EAST, Direction.WEST);
        fast.slots.set(CraneExtractorBlockEntity.SLOT_EJECTOR_UPGRADE, s(NtmItems.UPGRADE_EJECTOR_3.get(), 1));
        Container fastSource = chest(helper, new BlockPos(7, 2, 6));
        fill(fastSource, Items.STONE, 64);
        helper.setBlock(new BlockPos(9, 2, 6), beltState(Direction.WEST));
        CraneExtractorBlockEntity off = placeExtractor(helper, new BlockPos(8, 2, 10), Direction.EAST, Direction.WEST);
        off.slots.set(CraneExtractorBlockEntity.SLOT_EJECTOR_UPGRADE, s(NtmItems.UPGRADE_EJECTOR_3.get(), 1));
        Container offSource = chest(helper, new BlockPos(7, 2, 10));
        fill(offSource, Items.STONE, 64);
        helper.setBlock(new BlockPos(9, 2, 10), beltState(Direction.WEST));
        helper.setBlock(new BlockPos(8, 3, 10), Blocks.REDSTONE_BLOCK.defaultBlockState());
        int[] start = new int[3];
        helper.startSequence()
                .thenExecute(guard(() -> {
                    start[0] = total(slowSource);
                    start[1] = total(fastSource);
                    start[2] = total(offSource);
                }))
                .thenExecuteAfter(40, guard(() -> {
                    check(start[0] - total(slowSource) == 2, "delay 20: " + (start[0] - total(slowSource)) + " items taken in 40 ticks, expected 2");
                    check(start[1] - total(fastSource) == 20, "delay 2: " + (start[1] - total(fastSource)) + " items taken in 40 ticks, expected 20");
                    check(start[2] == total(offSource), "powered: " + (start[2] - total(offSource)) + " items taken");
                }))
                .thenExecute(passed("extractor_world_tick"))
                .thenSucceed();
    }

    // TileEntityCraneExtractor.java:107-141,189-198: first stack that can be taken and passes the filter; blacklist by default, an empty filter lets everything through
    // in a blacklist and nothing through in a whitelist; the filter matches by exact item + type + damage, by item, or by item tag (ModulePatternMatcher.java:142-150)
    @GameTest(template = TEMPLATE, batch = "hbm31b_extractor_filter_run", timeoutTicks = 200)
    public static void extractor_filter_run(GameTestHelper helper) {
        Item stone = Items.STONE;
        Item dirt = Items.DIRT;
        Item sand = Items.SAND;
        Item part = NtmItems.PART_GENERIC.get();
        XRig blackEmpty = new XRig(helper, 1, true).upgrades(3, 0);
        XRig whiteEmpty = new XRig(helper, 3, true).upgrades(3, 0);
        XRig blackDirt = new XRig(helper, 5, true).upgrades(3, 0);
        XRig whiteTwo = new XRig(helper, 7, true).upgrades(3, 0);
        XRig exact = new XRig(helper, 9, true).upgrades(3, 0);
        XRig wildcard = new XRig(helper, 11, true).upgrades(3, 0);
        XRig tag = new XRig(helper, 13, true).upgrades(3, 0);
        for(XRig r : new XRig[] { blackEmpty, whiteEmpty, blackDirt, whiteTwo }) chestSlots(chest(helper, r.srcRel), 0, stone, 2, 1, dirt, 2, 2, sand, 2);
        whiteEmpty.be.isWhitelist = true;
        setFilter(blackDirt.be, 2, s(dirt, 1), "wildcard");
        whiteTwo.be.isWhitelist = true;
        setFilter(whiteTwo.be, 5, s(sand, 1), "wildcard");
        setFilter(whiteTwo.be, 0, s(dirt, 1), "exact");
        Container exactChest = chest(helper, exact.srcRel);
        Container wildChest = chest(helper, wildcard.srcRel);
        for(Container c : new Container[] { exactChest, wildChest }) {
            c.setItem(0, MetaHelper.newStack(part, 2, 1));
            c.setItem(1, MetaHelper.newStack(part, 2, 2));
            c.setItem(2, MetaHelper.newStack(part, 1, 1));
        }
        exact.be.isWhitelist = true;
        setFilter(exact.be, 4, MetaHelper.newStack(part, 1, 1), "exact");
        wildcard.be.isWhitelist = true;
        setFilter(wildcard.be, 4, MetaHelper.newStack(part, 1, 1), "wildcard");
        chestSlots(chest(helper, tag.srcRel), 0, Items.BIRCH_LOG, 1, 1, stone, 1, 2, Items.SPRUCE_LOG, 1, 3, Items.OAK_LOG, 1);
        tag.be.isWhitelist = true;
        setFilter(tag.be, 0, s(Items.OAK_LOG, 1), "minecraft:logs");
        helper.startSequence()
                .thenExecuteFor(20, guard(() -> {
                    for(XRig r : new XRig[] { blackEmpty, whiteEmpty, blackDirt, whiteTwo, exact, wildcard, tag }) r.tick();
                }))
                .thenExecute(guard(() -> {
                    expectLog(blackEmpty, "blacklist, empty filter (:123)", stone, 1, stone, 1, dirt, 1, dirt, 1, sand, 1, sand, 1);
                    expectLog(whiteEmpty, "whitelist, empty filter");
                    expectLog(blackDirt, "blacklist with dirt (wildcard) in slot 2", stone, 1, stone, 1, sand, 1, sand, 1);
                    expectLog(whiteTwo, "whitelist with sand and dirt", dirt, 1, dirt, 1, sand, 1, sand, 1);
                    expectLog(exact, "whitelist, exact part type 1 (ModulePatternMatcher.java:142)", part, 1, part, 1, part, 1);
                    for(ItemStack s : exact.log) check(MetaHelper.getMeta(s) == 1, "exact: a stack of type " + MetaHelper.getMeta(s) + " passed");
                    expectLog(wildcard, "whitelist, wildcard part (:143)", part, 1, part, 1, part, 1, part, 1, part, 1);
                    check(MetaHelper.getMeta(wildcard.log.get(2)) == 2 && MetaHelper.getMeta(wildcard.log.get(4)) == 1, "wildcard: the types in order are " + MetaHelper.getMeta(wildcard.log.get(0)) + MetaHelper.getMeta(wildcard.log.get(1)) + MetaHelper.getMeta(wildcard.log.get(2)) + MetaHelper.getMeta(wildcard.log.get(3)) + MetaHelper.getMeta(wildcard.log.get(4)) + ", expected 1 1 2 2 1");
                    expectLog(tag, "whitelist, tag minecraft:logs (:148-150)", Items.BIRCH_LOG, 1, Items.SPRUCE_LOG, 1, Items.OAK_LOG, 1);
                }))
                .thenExecute(passed("extractor_filter_run"))
                .thenSucceed();
    }

    // TileEntityCraneExtractor.java:119-120,143-163: maxEject skips stacks below the amount (never above the stack limit), in the inventory and in the buffer
    @GameTest(template = TEMPLATE, batch = "hbm31b_extractor_max_eject", timeoutTicks = 200)
    public static void extractor_max_eject(GameTestHelper helper) {
        XRig on = new XRig(helper, 1, true).upgrades(3, 1);
        XRig off = new XRig(helper, 3, true).upgrades(3, 1);
        XRig pearls = new XRig(helper, 5, true).upgrades(3, 3);
        XRig buffered = new XRig(helper, 8, true).upgrades(3, 1);
        XRig bufferedOff = new XRig(helper, 11, true).upgrades(3, 1);
        for(XRig r : new XRig[] { on, off }) {
            Container c = chest(helper, r.srcRel);
            chestSlots(c, 0, Items.DIRT, 3, 1, Items.STONE, 4, 2, Items.SAND, 64);
        }
        on.be.maxEject = true;
        Container pearlChest = chest(helper, pearls.srcRel);
        chestSlots(pearlChest, 0, Items.ENDER_PEARL, 15, 1, Items.ENDER_PEARL, 16);
        pearls.be.maxEject = true;
        stone(helper, 7, 2, 8);
        stone(helper, 7, 2, 11);
        buffered.be.slots.set(9, s(Items.DIRT, 3));
        buffered.be.slots.set(10, s(Items.SAND, 4));
        buffered.be.maxEject = true;
        bufferedOff.be.slots.set(9, s(Items.DIRT, 3));
        bufferedOff.be.slots.set(10, s(Items.SAND, 4));
        Container onChest = containerAt(helper, on.srcRel);
        helper.startSequence()
                .thenExecuteFor(10, guard(() -> {
                    for(XRig r : new XRig[] { on, off, pearls, buffered, bufferedOff }) r.tick();
                }))
                .thenExecute(guard(() -> {
                    expectLog(on, "maxEject on, amount 4", Items.STONE, 4, Items.SAND, 4, Items.SAND, 4, Items.SAND, 4, Items.SAND, 4);
                    check(onChest.getItem(0).getCount() == 3 && onChest.getItem(1).isEmpty() && onChest.getItem(2).getCount() == 64 - 16, "maxEject on: the chest holds " + onChest.getItem(0) + " / " + onChest.getItem(1) + " / " + onChest.getItem(2) + ", expected the 3 dirt kept, stone gone, 48 sand");
                    expectLog(off, "maxEject off, amount 4", Items.DIRT, 3, Items.STONE, 4, Items.SAND, 4, Items.SAND, 4, Items.SAND, 4);
                    expectLog(pearls, "maxEject on, pearls stack limit 16, amount 64 (:119 min(amount, max stack))", Items.ENDER_PEARL, 16);
                    check(pearlChest.getItem(0).getCount() == 15 && pearlChest.getItem(1).isEmpty(), "pearls: the chest holds " + pearlChest.getItem(0) + " / " + pearlChest.getItem(1));
                    expectLog(buffered, "buffer with maxEject on (:143-163)", Items.SAND, 4);
                    check(buffered.be.getItem(9).getCount() == 3 && buffered.be.getItem(10).isEmpty(), "buffer with maxEject on: slots 9 / 10 are " + buffered.be.getItem(9) + " / " + buffered.be.getItem(10));
                    expectLog(bufferedOff, "buffer with maxEject off", Items.DIRT, 3, Items.SAND, 4);
                }))
                .thenExecute(passed("extractor_max_eject"))
                .thenSucceed();
    }

    // TileEntityCraneExtractor.java:125-134,143-163: without a belt the item goes into the buffer (as much as fits, the source loses exactly that); with a belt the buffer drains
    // without the filter, but only when nothing came out of the inventory in that action
    @GameTest(template = TEMPLATE, batch = "hbm31b_extractor_buffer", timeoutTicks = 200)
    public static void extractor_buffer(GameTestHelper helper) {
        // no belt: the chest's three stones end up in buffer slot 9
        XRig plain = new XRig(helper, 1, false).upgrades(3, 0);
        Container plainChest = chest(helper, plain.srcRel);
        chestSlots(plainChest, 0, Items.STONE, 3);
        // no belt, the buffer almost full: eight slots of sand and a stack of 63 stone, amount 4: one stone fits
        XRig nearlyFull = new XRig(helper, 4, false).upgrades(3, 1);
        Container nearlyChest = chest(helper, nearlyFull.srcRel);
        chestSlots(nearlyChest, 0, Items.STONE, 10);
        for(int i = 9; i < 17; i++) nearlyFull.be.slots.set(i, s(Items.SAND, 64));
        nearlyFull.be.slots.set(17, s(Items.STONE, 63));
        // belt, whitelist with an empty filter: nothing passes, so the buffer drains without the filter
        XRig drain = new XRig(helper, 7, true).upgrades(3, 0);
        Container drainChest = chest(helper, drain.srcRel);
        chestSlots(drainChest, 0, Items.STONE, 5);
        drain.be.isWhitelist = true;
        drain.be.slots.set(9, s(Items.DIRT, 3));
        drain.be.slots.set(10, s(Items.STONE, 2));
        // belt, blacklist: while the chest delivers, the buffer is left alone
        XRig busy = new XRig(helper, 10, true).upgrades(3, 0);
        Container busyChest = chest(helper, busy.srcRel);
        chestSlots(busyChest, 0, Items.STONE, 2);
        busy.be.slots.set(9, s(Items.DIRT, 5));
        // no inventory at all (stone) and a belt: the buffer drains as well
        XRig lonely = new XRig(helper, 13, true).upgrades(3, 0);
        stone(helper, 7, 2, 13);
        lonely.be.slots.set(12, s(Items.COAL, 2));
        helper.startSequence()
                .thenExecuteFor(12, guard(() -> {
                    for(XRig r : new XRig[] { plain, nearlyFull, drain, busy, lonely }) r.tick();
                    check(busy.log.size() > 2 || busy.be.getItem(9).getCount() == 5, "the buffer was drained while the chest still delivered: " + busy.be.getItem(9) + " after " + busy.log.size() + " items");
                    check(total(plainChest) + bufferTotal(plain.be) == 3, "no belt: " + total(plainChest) + " in the chest and " + bufferTotal(plain.be) + " in the buffer, expected 3 in total");
                    check(total(nearlyChest) + count(nearlyFull.be, Items.STONE) == 10 + 63, "nearly full buffer: stone total " + (total(nearlyChest) + count(nearlyFull.be, Items.STONE)));
                }))
                .thenExecute(guard(() -> {
                    check(plain.log.isEmpty() && plainChest.getItem(0).isEmpty() && plain.be.getItem(9).is(Items.STONE) && plain.be.getItem(9).getCount() == 3, "no belt: the chest holds " + plainChest.getItem(0) + ", buffer slot 9 holds " + plain.be.getItem(9) + ", the belt got " + describe(plain.log));
                    check(nearlyChest.getItem(0).getCount() == 9 && nearlyFull.be.getItem(17).getCount() == 64, "nearly full buffer: the chest holds " + nearlyChest.getItem(0) + ", buffer slot 17 holds " + nearlyFull.be.getItem(17) + ", expected 9 and 64 (only the one stone that fits is taken, :131-134)");
                    expectLog(drain, "buffer drain ignoring the filter", Items.DIRT, 1, Items.DIRT, 1, Items.DIRT, 1, Items.STONE, 1, Items.STONE, 1);
                    check(count(drainChest, Items.STONE) == 5, "the whitelist let stone out of the chest");
                    check(busy.log.size() >= 2 && busy.log.get(0).is(Items.STONE) && busy.log.get(1).is(Items.STONE) && busy.be.getItem(9).getCount() == 5 - Math.max(0, busy.log.size() - 2), "busy: the log is " + describe(busy.log) + ", buffer " + busy.be.getItem(9) + ", expected the two stones first, then the dirt from the buffer");
                    expectLog(lonely, "no inventory, buffer coal", Items.COAL, 1, Items.COAL, 1);
                }))
                .thenExecute(passed("extractor_buffer"))
                .thenSucceed();
    }

    // TileEntityCraneExtractor.java:204-211: a furnace is only emptied through its result slot; other inventories by their own face rules
    @GameTest(template = TEMPLATE, batch = "hbm31b_extractor_sources", timeoutTicks = 200)
    public static void extractor_sources(GameTestHelper helper) {
        // vanilla furnace: input dirt (not smeltable, so nothing cooks), fuel coal, result iron ingots
        XRig furnaceRig = new XRig(helper, 1, true).upgrades(3, 0);
        helper.setBlock(furnaceRig.srcRel, Blocks.FURNACE.defaultBlockState());
        Container furnace = containerAt(helper, furnaceRig.srcRel);
        chestSlots(furnace, 0, Items.DIRT, 5, 1, Items.COAL, 5, 2, Items.IRON_INGOT, 3);
        // NEO machine with face rules (only the output slot may be taken)
        XRig machineRig = new XRig(helper, 4, true).upgrades(3, 0);
        helper.setBlock(machineRig.srcRel, NtmBlocks.MACHINE_ELECTRIC_FURNACE.get().defaultBlockState());
        MachineElectricFurnaceBlockEntity machine = SmokeTestSupport.blockEntity(helper, machineRig.srcRel, MachineElectricFurnaceBlockEntity.class);
        chestSlots(machine, 0, Items.STICK, 2, 1, Items.RAW_IRON, 2, 2, Items.IRON_INGOT, 2);
        // an iron crate (every slot may be taken)
        XRig crateRig = new XRig(helper, 7, true).upgrades(3, 0);
        helper.setBlock(crateRig.srcRel, NtmBlocks.CRATE_IRON.get().defaultBlockState());
        Container crate = containerAt(helper, crateRig.srcRel);
        crate.setItem(20, s(Items.STONE, 3));
        // a double chest: the near half is empty, the far half holds the items
        XRig doubleRig = new XRig(helper, 10, true).upgrades(3, 0);
        helper.setBlock(doubleRig.srcRel, Blocks.CHEST.defaultBlockState().setValue(ChestBlock.FACING, Direction.EAST).setValue(ChestBlock.TYPE, ChestType.LEFT));
        helper.setBlock(doubleRig.srcRel.south(), Blocks.CHEST.defaultBlockState().setValue(ChestBlock.FACING, Direction.EAST).setValue(ChestBlock.TYPE, ChestType.RIGHT));
        Container farHalf = containerAt(helper, doubleRig.srcRel.south());
        farHalf.setItem(3, s(Items.DIRT, 2));
        // a ready composter above the extractor (a block without a block entity, only the capability): bone meal comes out of its bottom face
        XRig composterRig = new XRig(helper, new BlockPos(8, 2, 14), Direction.EAST, Direction.UP, true).upgrades(3, 0);
        helper.setBlock(composterRig.srcRel, Blocks.COMPOSTER.defaultBlockState().setValue(ComposterBlock.LEVEL, 8));
        // a stone block: no inventory
        XRig noneRig = new XRig(helper, 0, true).upgrades(3, 0);
        stone(helper, 7, 2, 0);
        noneRig.be.slots.set(9, s(Items.APPLE, 1));
        helper.startSequence()
                .thenExecuteFor(10, guard(() -> {
                    for(XRig r : new XRig[] { furnaceRig, machineRig, crateRig, doubleRig, composterRig, noneRig }) r.tick();
                }))
                .thenExecute(guard(() -> {
                    expectLog(furnaceRig, "vanilla furnace", Items.IRON_INGOT, 1, Items.IRON_INGOT, 1, Items.IRON_INGOT, 1);
                    check(furnace.getItem(0).getCount() == 5 && furnace.getItem(1).getCount() == 5 && furnace.getItem(2).isEmpty(), "furnace: slots are " + furnace.getItem(0) + " / " + furnace.getItem(1) + " / " + furnace.getItem(2) + ", expected only the result taken (:204-211)");
                    expectLog(machineRig, "NEO machine", Items.IRON_INGOT, 1, Items.IRON_INGOT, 1);
                    check(machine.getItem(0).getCount() == 2 && machine.getItem(1).getCount() == 2 && machine.getItem(2).isEmpty(), "machine: slots 0 / 1 / 2 are " + machine.getItem(0) + " / " + machine.getItem(1) + " / " + machine.getItem(2));
                    expectLog(crateRig, "iron crate", Items.STONE, 1, Items.STONE, 1, Items.STONE, 1);
                    check(crate.getItem(20).isEmpty(), "crate: slot 20 still holds " + crate.getItem(20));
                    expectLog(doubleRig, "double chest", Items.DIRT, 1, Items.DIRT, 1);
                    check(farHalf.getItem(3).isEmpty(), "double chest: the far half still holds " + farHalf.getItem(3));
                    expectLog(composterRig, "ready composter", Items.BONE_MEAL, 1);
                    check(helper.getBlockState(composterRig.srcRel).getValue(ComposterBlock.LEVEL) == 0, "composter: the level is " + helper.getBlockState(composterRig.srcRel).getValue(ComposterBlock.LEVEL) + ", expected 0 after the harvest");
                    expectLog(noneRig, "stone block with a buffered apple (the buffer drains)", Items.APPLE, 1);
                }))
                .thenExecute(passed("extractor_sources"))
                .thenSucceed();
    }

    /** The extractor's action without the redstone check of updateEntity (which loads the neighbour chunk by itself). */
    private static void callAct(CraneExtractorBlockEntity be) {
        try {
            Method act = CraneExtractorBlockEntity.class.getDeclaredMethod("act");
            act.setAccessible(true);
            act.invoke(be);
        } catch(ReflectiveOperationException e) {
            throw new GameTestAssertException("CraneExtractorBlockEntity.act failed: " + e + " / " + e.getCause());
        }
    }

    // the neighbour chunks are never loaded (intentional difference): the extractor's action does nothing and loads nothing when its source and belt positions are not loaded,
    // AdjacentInventory answers "no target" without loading
    @GameTest(template = TEMPLATE, batch = "hbm31b_extractor_unloaded", timeoutTicks = 100)
    public static void extractor_unloaded(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos far = new BlockPos(20_000_001, 100, 20_000_001);
            check(!level.isLoaded(far) && !level.isLoaded(far.east()) && !level.isLoaded(far.west()), "the far position is loaded: pick another one");
            CraneExtractorBlockEntity be = new CraneExtractorBlockEntity(far, crane(extractorBlock(), Direction.EAST, Direction.WEST));
            be.setLevel(level);
            be.slots.set(9, s(Items.COAL, 4));
            callAct(be);
            check(be.getItem(9).getCount() == 4 && be.getItem(10).isEmpty(), "the extractor acted with unloaded neighbours: " + be.slots);
            check(!level.isLoaded(far) && !level.isLoaded(far.east()) && !level.isLoaded(far.west()), "the extractor loaded a chunk");
            check(level.getEntitiesOfClass(MovingItem.class, new AABB(far).inflate(3)).isEmpty(), "the extractor spawned an item");

            ItemStack stack = s(Items.STONE, 5);
            check(AdjacentInventory.insert(level, far, Direction.EAST, stack).getCount() == 5, "an unloaded target took items");
            check(AdjacentInventory.source(level, far, Direction.EAST) == null, "an unloaded position gave a source");
            check(!level.isLoaded(far), "AdjacentInventory loaded the chunk");
        }).run();
        passed("extractor_unloaded").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 4. filter matcher, menu, upgrades, control

    private static final List<Vec3> PLUGS = new ArrayList<>();
    private static boolean listening;

    /** Records the position of every upgrade plug sound once the listener is registered (registered once, it only records while a test reads it). */
    private static void listen() {
        if(listening) return;
        listening = true;
        NeoForge.EVENT_BUS.addListener((PlayLevelSoundEvent.AtPosition event) -> {
            if(event.getSound() != null && event.getSound().value() == NtmSoundEvents.UPGRADE_PLUG.get()) PLUGS.add(event.getPosition());
        });
    }

    private static int plugsAt(BlockPos abs) {
        int n = 0;
        for(Vec3 p : PLUGS) if(Math.abs(p.x - (abs.getX() + 0.5)) < 1e-6 && Math.abs(p.y - (abs.getY() + 0.5)) < 1e-6 && Math.abs(p.z - (abs.getZ() + 0.5)) < 1e-6) n++;
        return n;
    }

    private static int invTotal(Player p) {
        int n = 0;
        for(ItemStack st : p.getInventory().items) n += st.getCount();
        return n;
    }

    private static List<String> sortedTags(ItemStack stack) {
        List<String> names = new ArrayList<>();
        stack.getTags().forEach(t -> names.add(t.location().toString()));
        names.sort(null);
        return names;
    }

    private static CompoundTag stackTag(HolderLookup.Provider registries, ItemStack stack) {
        return (CompoundTag) stack.save(registries);
    }

    // ModulePatternMatcher.java:68-84 (initial mode), :86-131 (cycle), :133-151 (matching), :154-175 (NBT); tags replace the ore dictionary names
    @GameTest(template = TEMPLATE, batch = "hbm31b_filter_matcher", timeoutTicks = 100)
    public static void filter_matcher(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            Item part = NtmItems.PART_GENERIC.get();
            ItemStack typed = MetaHelper.newStack(part, 1, 1);
            ModulePatternMatcher m = new ModulePatternMatcher(9);

            // :77-83 an item with subtypes starts as exact, any other as wildcard, an empty slot has no mode
            m.initPatternStandard(level, typed, 0);
            check("exact".equals(m.modes[0]), "a part with a type starts as " + m.modes[0] + ", expected exact (:79-80)");
            m.initPatternStandard(level, s(Items.DIRT, 1), 1);
            check("wildcard".equals(m.modes[1]), "dirt starts as " + m.modes[1] + ", expected wildcard (:81-82)");
            m.initPatternStandard(level, ItemStack.EMPTY, 1);
            check(m.modes[1] == null, "an empty slot starts as " + m.modes[1] + ", expected no mode (:72-74)");

            // :141-143 exact: the same item and type; wildcard: the same item
            m.modes[2] = "exact";
            check(m.isValidForFilter(typed, 2, MetaHelper.newStack(part, 5, 1)), "exact rejects the same item and type");
            check(!m.isValidForFilter(typed, 2, MetaHelper.newStack(part, 1, 2)), "exact accepts another type");
            check(!m.isValidForFilter(typed, 2, s(Items.DIRT, 1)), "exact accepts another item");
            m.modes[2] = "wildcard";
            check(m.isValidForFilter(typed, 2, MetaHelper.newStack(part, 1, 2)), "wildcard rejects another type of the same item (:143)");
            check(!m.isValidForFilter(typed, 2, s(Items.DIRT, 1)), "wildcard accepts another item");
            ItemStack pick = s(Items.IRON_PICKAXE, 1);
            ItemStack worn = s(Items.IRON_PICKAXE, 1);
            worn.setDamageValue(7);
            m.modes[2] = "exact";
            check(!m.isValidForFilter(pick, 2, worn), "exact accepts a damaged copy (isItemEqual compares the damage, :142)");
            m.modes[2] = "wildcard";
            check(m.isValidForFilter(pick, 2, worn), "wildcard rejects a damaged copy");

            // :137-139 no mode counts as exact and is written back; :148-150 a tag mode matches the tag
            m.modes[3] = null;
            check(m.isValidForFilter(s(Items.DIRT, 1), 3, s(Items.DIRT, 4)) && "exact".equals(m.modes[3]), "an empty mode did not match as exact and write exact back: " + m.modes[3]);
            m.modes[4] = "minecraft:logs";
            check(m.isValidForFilter(s(Items.OAK_LOG, 1), 4, s(Items.BIRCH_LOG, 1)), "the tag minecraft:logs rejects a birch log");
            check(!m.isValidForFilter(s(Items.OAK_LOG, 1), 4, s(Items.STONE, 1)), "the tag minecraft:logs accepts stone");
            m.modes[4] = "hbmsntm:gone";
            check(!m.isValidForFilter(s(Items.OAK_LOG, 1), 4, s(Items.OAK_LOG, 1)), "a tag nobody has accepts the filter item itself");
            // a tag that no longer applies to the pattern goes back to exact on the next click
            m.nextMode(level, s(Items.OAK_LOG, 1), 4);
            check("exact".equals(m.modes[4]), "a stale tag mode advanced to " + m.modes[4] + ", expected exact");

            // :86-131 the cycle: none, exact, wildcard, every tag of the pattern in turn, exact again
            ItemStack oak = s(Items.OAK_LOG, 1);
            List<String> tags = sortedTags(oak);
            check(tags.size() >= 2, "oak log has the tags " + tags + ", the cycle needs at least two");
            List<String> expected = new ArrayList<>(List.of("exact", "wildcard"));
            expected.addAll(tags);
            expected.add("exact");
            expected.add("wildcard");
            m.modes[5] = null;
            for(int i = 0; i < expected.size(); i++) {
                m.nextMode(level, oak, 5);
                check(expected.get(i).equals(m.modes[5]), "click " + (i + 1) + " on an oak log gave " + m.modes[5] + ", expected " + expected.get(i) + " (all " + expected + ")");
            }
            m.nextMode(level, ItemStack.EMPTY, 5);
            check(m.modes[5] == null, "an empty pattern kept the mode " + m.modes[5] + " (:90-93)");

            // :154-175 the keys mode0..mode8 hold the set modes; a missing key reads as no mode
            ModulePatternMatcher w = new ModulePatternMatcher(9);
            w.modes[0] = "exact";
            w.modes[3] = "minecraft:logs";
            w.modes[8] = "wildcard";
            CompoundTag tag = new CompoundTag();
            w.writeToNBT(tag);
            check(tag.getAllKeys().equals(Set.of("mode0", "mode3", "mode8")) && "minecraft:logs".equals(tag.getString("mode3")), "the saved keys are " + tag.getAllKeys() + ", expected mode0 mode3 mode8");
            ModulePatternMatcher r = new ModulePatternMatcher(9);
            r.modes[5] = "wildcard";
            r.readFromNBT(tag);
            for(int i = 0; i < 9; i++) check(java.util.Objects.equals(r.modes[i], w.modes[i]), "mode " + i + " is " + r.modes[i] + " after loading, expected " + w.modes[i]);

            // :178-185 the packet form carries every mode
            RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf(Unpooled.buffer(), level.registryAccess());
            w.serialize(buf);
            ModulePatternMatcher d = new ModulePatternMatcher(9);
            d.modes[1] = "exact";
            d.deserialize(buf);
            for(int i = 0; i < 9; i++) check(java.util.Objects.equals(d.modes[i], w.modes[i]), "mode " + i + " is " + d.modes[i] + " after the packet, expected " + w.modes[i]);
        }).run();
        passed("filter_matcher").run();
        helper.succeed();
    }

    // ContainerCraneExtractor.java:84-113 (slotClick), :40-81 (transferStackInSlot), SlotPattern: phantom slots never give items, never take the cursor, shift clicks never reach them
    @GameTest(template = TEMPLATE, batch = "hbm31b_extractor_menu", timeoutTicks = 100)
    public static void extractor_menu(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            CraneExtractorBlockEntity be = placeExtractor(helper, new BlockPos(8, 2, 8), Direction.EAST, Direction.WEST);
            CranePlayer player = player(helper, GameType.SURVIVAL, 0F);
            CraneExtractorMenu menu = new CraneExtractorMenu(1, player.getInventory(), be);
            check(menu.slots.size() == 20 + 36, "the menu has " + menu.slots.size() + " slots, expected 20 + 36 (ContainerCraneExtractor.java:22-35)");
            for(int i = 0; i < 9; i++) {
                Slot slot = menu.getSlot(i);
                check(!slot.mayPlace(s(Items.DIRT, 1)) && !slot.mayPickup(player) && slot.getMaxStackSize() == 1, "filter slot " + i + " is not a phantom slot");
            }
            Item part = NtmItems.PART_GENERIC.get();

            // :98-111 every click but a right click on a filled slot is "click with the cursor": one item goes in, the cursor keeps its items
            int before = invTotal(player);
            for(ClickType type : ClickType.values()) {
                for(int button = 0; button < 2; button++) {
                    be.setItem(0, ItemStack.EMPTY);
                    be.matcher.modes[0] = null;
                    menu.setCarried(s(Items.DIRT, 5));
                    menu.clicked(0, button, type, player);
                    String ctx = type + " button " + button + " with dirt on the cursor";
                    check(be.getItem(0).is(Items.DIRT) && be.getItem(0).getCount() == 1, ctx + ": the slot holds " + be.getItem(0) + ", expected one dirt (:108)");
                    check(menu.getCarried().is(Items.DIRT) && menu.getCarried().getCount() == 5, ctx + ": the cursor holds " + menu.getCarried() + ", expected 5 dirt");
                    check("wildcard".equals(be.matcher.modes[0]), ctx + ": the mode is " + be.matcher.modes[0] + ", expected wildcard (:109 initPatternStandard)");
                    check(invTotal(player) == before, ctx + ": the player inventory changed");
                }
            }
            be.setItem(1, ItemStack.EMPTY);
            menu.setCarried(MetaHelper.newStack(part, 3, 1));
            menu.clicked(1, 0, ClickType.PICKUP, player);
            check(be.getItem(1).is(part) && be.getItem(1).getCount() == 1 && MetaHelper.getMeta(be.getItem(1)) == 1 && "exact".equals(be.matcher.modes[1]), "a typed part went in as " + be.getItem(1) + " type " + MetaHelper.getMeta(be.getItem(1)) + " mode " + be.matcher.modes[1] + ", expected one part of type 1 in exact mode");

            // an empty cursor clears the slot (:108 putStack(null)), also for shift, number keys and the others; the hotbar stone stays
            player.getInventory().setItem(0, s(Items.STONE, 7));
            for(ClickType type : ClickType.values()) {
                for(int button = 0; button < 2; button++) {
                    be.setItem(0, s(Items.DIRT, 1));
                    be.matcher.modes[0] = "wildcard";
                    menu.setCarried(ItemStack.EMPTY);
                    int total = invTotal(player);
                    menu.clicked(0, button, type, player);
                    String ctx = type + " button " + button + " with an empty cursor";
                    if(button == 1 && type == ClickType.PICKUP) {
                        check(be.getItem(0).is(Items.DIRT) && !"wildcard".equals(be.matcher.modes[0]), ctx + ": the slot holds " + be.getItem(0) + " mode " + be.matcher.modes[0] + ", expected the item kept and the mode advanced (:103-105)");
                    } else {
                        check(be.getItem(0).isEmpty() && be.matcher.modes[0] == null, ctx + ": the slot holds " + be.getItem(0) + " mode " + be.matcher.modes[0] + ", expected it cleared (:108-109)");
                    }
                    check(menu.getCarried().isEmpty() && invTotal(player) == total && player.getInventory().getItem(0).getCount() == 7, ctx + ": the item came out of the phantom slot (cursor " + menu.getCarried() + ")");
                }
            }

            // :103-105 a right click on a filled slot cycles the mode and leaves slot and cursor alone
            ItemStack oak = s(Items.OAK_LOG, 1);
            List<String> tags = sortedTags(oak);
            be.setItem(2, oak.copy());
            menu.setCarried(s(Items.STONE, 3));
            be.matcher.modes[2] = null;
            menu.clicked(2, 0, ClickType.PICKUP, player);
            check(be.getItem(2).is(Items.STONE) && "wildcard".equals(be.matcher.modes[2]), "a left click with stone replaced the oak log by " + be.getItem(2));
            be.setItem(2, oak.copy());
            be.matcher.modes[2] = "wildcard";
            List<String> expected = new ArrayList<>(tags);
            expected.add("exact");
            expected.add("wildcard");
            for(int i = 0; i < expected.size(); i++) {
                menu.clicked(2, 1, ClickType.PICKUP, player);
                check(expected.get(i).equals(be.matcher.modes[2]), "right click " + (i + 1) + " on an oak log in wildcard mode gave " + be.matcher.modes[2] + ", expected " + expected.get(i));
                check(be.getItem(2).is(Items.OAK_LOG) && menu.getCarried().is(Items.STONE) && menu.getCarried().getCount() == 3, "a right click changed the slot " + be.getItem(2) + " or the cursor " + menu.getCarried());
            }
            menu.setCarried(ItemStack.EMPTY);

            // clicks outside the filter go to the normal menu: slot index -1 and the player inventory
            menu.clicked(-999, 0, ClickType.PICKUP, player);
            check(menu.getCarried().isEmpty(), "a click outside the menu left " + menu.getCarried() + " on the cursor");

            // :48-50 filter slots never move
            for(int i = 0; i < 9; i++) {
                be.setItem(i, s(Items.DIRT, 1));
                check(menu.quickMoveStack(player, i).isEmpty() && be.getItem(i).is(Items.DIRT), "a shift click on filter slot " + i + " moved " + be.getItem(i));
            }
            for(int i = 0; i < 9; i++) be.setItem(i, ItemStack.EMPTY);

            // :52-55 buffer and upgrade slots go to the player inventory
            be.setItem(9, s(Items.IRON_INGOT, 5));
            be.setItem(CraneExtractorBlockEntity.SLOT_STACK_UPGRADE, s(NtmItems.UPGRADE_STACK_1.get(), 1));
            player.getInventory().clearContent();
            ItemStack moved = menu.quickMoveStack(player, 9);
            check(moved.is(Items.IRON_INGOT) && moved.getCount() == 5 && be.getItem(9).isEmpty() && count(player.getInventory(), Items.IRON_INGOT) == 5, "a shift click on the buffer returned " + moved + ", the buffer holds " + be.getItem(9) + ", the player " + count(player.getInventory(), Items.IRON_INGOT));
            moved = menu.quickMoveStack(player, 18);
            check(moved.is(NtmItems.UPGRADE_STACK_1.get()) && be.getItem(18).isEmpty() && count(player.getInventory(), NtmItems.UPGRADE_STACK_1.get()) == 1, "a shift click on the stack upgrade slot returned " + moved);
            player.getInventory().clearContent();

            // :56-66 from the player: upgrades to their slot, the rest into the buffer when the filter lets it in, never into a filter slot
            player.getInventory().setItem(9, s(Items.STONE, 10));
            moved = menu.quickMoveStack(player, 20);
            check(moved.is(Items.STONE) && be.getItem(9).is(Items.STONE) && be.getItem(9).getCount() == 10 && player.getInventory().getItem(9).isEmpty(), "a shift click on stone returned " + moved + ", buffer slot 9 holds " + be.getItem(9));
            for(int i = 0; i < 9; i++) check(be.getItem(i).isEmpty(), "a shift click filled filter slot " + i + " with " + be.getItem(i));
            be.setItem(9, ItemStack.EMPTY);

            player.getInventory().setItem(9, s(NtmItems.UPGRADE_STACK_2.get(), 1));
            player.getInventory().setItem(10, s(NtmItems.UPGRADE_EJECTOR_1.get(), 1));
            player.getInventory().setItem(11, s(NtmItems.UPGRADE_SPEED_1.get(), 1));
            player.getInventory().setItem(12, s(NtmItems.UPGRADE_STACK_1.get(), 1));
            menu.quickMoveStack(player, 20);
            menu.quickMoveStack(player, 21);
            menu.quickMoveStack(player, 22);
            check(be.getItem(18).is(NtmItems.UPGRADE_STACK_2.get()) && be.getItem(19).is(NtmItems.UPGRADE_EJECTOR_1.get()), "the upgrades went to " + be.getItem(18) + " / " + be.getItem(19) + ", expected stack 2 / ejector 1 (:58-62)");
            check(be.getItem(9).is(NtmItems.UPGRADE_SPEED_1.get()), "another machine upgrade went to " + be.getItem(9) + ", expected the buffer (the upgrade slots take only their own upgrade)");
            moved = menu.quickMoveStack(player, 23);
            check(moved.isEmpty() && player.getInventory().getItem(12).is(NtmItems.UPGRADE_STACK_1.get()) && be.getItem(18).is(NtmItems.UPGRADE_STACK_2.get()), "a second stack upgrade went to " + moved + " / the slot holds " + be.getItem(18) + ", expected it to stay with the player");
            for(int i = 10; i < 18; i++) check(!be.getItem(i).is(NtmItems.UPGRADE_STACK_1.get()), "the second stack upgrade ended up in buffer slot " + i);

            // a whitelist without a matching filter keeps everything out of the buffer, a matching item goes in (:240)
            be.setItem(9, ItemStack.EMPTY);
            player.getInventory().clearContent();
            player.getInventory().setItem(9, s(Items.STONE, 10));
            player.getInventory().setItem(10, s(Items.DIRT, 6));
            be.isWhitelist = true;
            moved = menu.quickMoveStack(player, 20);
            check(moved.isEmpty() && player.getInventory().getItem(9).getCount() == 10 && total(be) - be.getItem(18).getCount() - be.getItem(19).getCount() == 0, "a whitelist let stone in: returned " + moved + ", buffer " + be.getItem(9));
            be.setItem(0, s(Items.DIRT, 1));
            be.matcher.modes[0] = "wildcard";
            moved = menu.quickMoveStack(player, 21);
            check(moved.is(Items.DIRT) && be.getItem(9).is(Items.DIRT) && be.getItem(9).getCount() == 6 && be.getItem(0).getCount() == 1, "a whitelisted dirt returned " + moved + ", buffer " + be.getItem(9) + ", filter slot 0 " + be.getItem(0));
            // the same filter as a blacklist: dirt stays out, stone goes in
            be.isWhitelist = false;
            be.setItem(9, ItemStack.EMPTY);
            player.getInventory().setItem(10, s(Items.DIRT, 6));
            moved = menu.quickMoveStack(player, 21);
            check(moved.isEmpty() && player.getInventory().getItem(10).getCount() == 6 && be.getItem(9).isEmpty(), "a blacklisted dirt returned " + moved + ", buffer " + be.getItem(9));
            moved = menu.quickMoveStack(player, 20);
            check(moved.is(Items.STONE) && be.getItem(9).is(Items.STONE) && be.getItem(9).getCount() == 10, "a stone under a blacklist of dirt returned " + moved + ", buffer " + be.getItem(9));
            check(level.getBlockEntity(be.getBlockPos()) == be, "the extractor is not in the world any more");
        }).run();
        passed("extractor_menu").run();
        helper.succeed();
    }

    // TileEntityCraneExtractor.java:47-57: plugging an ejector upgrade into slot 19 or a stack upgrade into slot 18 plays the plug sound; the slots take only those items
    @GameTest(template = TEMPLATE, batch = "hbm31b_extractor_upgrade_slots", timeoutTicks = 100)
    public static void extractor_upgrade_slots(GameTestHelper helper) {
        guard(() -> {
            listen();
            CraneExtractorBlockEntity be = placeExtractor(helper, new BlockPos(8, 2, 8), Direction.EAST, Direction.WEST);
            BlockPos abs = be.getBlockPos();
            CranePlayer player = player(helper, GameType.SURVIVAL, 0F);
            CraneExtractorMenu menu = new CraneExtractorMenu(1, player.getInventory(), be);
            Item[] stacks = { NtmItems.UPGRADE_STACK_1.get(), NtmItems.UPGRADE_STACK_2.get(), NtmItems.UPGRADE_STACK_3.get() };
            Item[] ejectors = { NtmItems.UPGRADE_EJECTOR_1.get(), NtmItems.UPGRADE_EJECTOR_2.get(), NtmItems.UPGRADE_EJECTOR_3.get() };
            Item[] others = { NtmItems.UPGRADE_TEMPLATE.get(), NtmItems.UPGRADE_SPEED_1.get(), NtmItems.UPGRADE_POWER_1.get(), Items.STONE, Items.REDSTONE };
            for(Item i : stacks) {
                check(menu.getSlot(18).mayPlace(s(i, 1)) && !menu.getSlot(19).mayPlace(s(i, 1)), i + ": slot 18 / 19 acceptance is " + menu.getSlot(18).mayPlace(s(i, 1)) + " / " + menu.getSlot(19).mayPlace(s(i, 1)) + ", expected true / false");
            }
            for(Item i : ejectors) {
                check(!menu.getSlot(18).mayPlace(s(i, 1)) && menu.getSlot(19).mayPlace(s(i, 1)), i + ": slot 18 / 19 acceptance is " + menu.getSlot(18).mayPlace(s(i, 1)) + " / " + menu.getSlot(19).mayPlace(s(i, 1)) + ", expected false / true");
            }
            for(Item i : others) {
                check(!menu.getSlot(18).mayPlace(s(i, 1)) && !menu.getSlot(19).mayPlace(s(i, 1)), i + " is accepted by an upgrade slot");
            }

            // the sound: one per matching upgrade tier in its slot, none for anything else
            PLUGS.clear();
            for(int t = 0; t < 3; t++) {
                be.setItem(19, s(ejectors[t], 1));
                check(plugsAt(abs) == 2 * t + 1, "ejector upgrade " + (t + 1) + ": " + plugsAt(abs) + " plug sounds in total, expected " + (2 * t + 1) + " (:53-54)");
                be.setItem(18, s(stacks[t], 1));
                check(plugsAt(abs) == 2 * t + 2, "stack upgrade " + (t + 1) + ": " + plugsAt(abs) + " plug sounds in total, expected " + (2 * t + 2));
            }
            int base = plugsAt(abs);
            be.setItem(19, s(stacks[0], 1));
            be.setItem(18, s(ejectors[0], 1));
            be.setItem(19, ItemStack.EMPTY);
            be.setItem(18, ItemStack.EMPTY);
            be.setItem(5, s(ejectors[1], 1));
            be.setItem(9, s(stacks[1], 1));
            be.setItem(17, s(ejectors[2], 1));
            check(plugsAt(abs) == base, "a wrong item, an empty stack or another slot played " + (plugsAt(abs) - base) + " plug sounds (:53 needs the matching upgrade in its own slot)");
            be.setItem(5, ItemStack.EMPTY);
            be.setItem(9, ItemStack.EMPTY);
            be.setItem(17, ItemStack.EMPTY);

            // the same through the menu: a click with the matching upgrade fills the slot and plays, the wrong one is not placed
            PLUGS.clear();
            menu.setCarried(s(ejectors[1], 1));
            menu.clicked(18, 0, ClickType.PICKUP, player);
            check(be.getItem(18).isEmpty() && menu.getCarried().is(ejectors[1]) && plugsAt(abs) == 0, "an ejector upgrade was placed in the stack slot: " + be.getItem(18));
            menu.clicked(19, 0, ClickType.PICKUP, player);
            check(be.getItem(19).is(ejectors[1]) && menu.getCarried().isEmpty() && plugsAt(abs) == 1, "an ejector upgrade click left " + be.getItem(19) + " in slot 19, cursor " + menu.getCarried() + ", " + plugsAt(abs) + " sounds");
            menu.setCarried(s(stacks[2], 1));
            menu.clicked(19, 0, ClickType.PICKUP, player);
            check(be.getItem(19).is(ejectors[1]) && menu.getCarried().is(stacks[2]) && plugsAt(abs) == 1, "a stack upgrade replaced the ejector upgrade: " + be.getItem(19));
            menu.clicked(18, 0, ClickType.PICKUP, player);
            check(be.getItem(18).is(stacks[2]) && plugsAt(abs) == 2, "a stack upgrade click left " + be.getItem(18) + " in slot 18, " + plugsAt(abs) + " sounds");
            check(be.getDelay() == 5 && be.getAmount() == 64, "the delay is " + be.getDelay() + " and the amount " + be.getAmount() + ", expected 5 and 64 with ejector 2 and stack 3 (:64-83)");
        }).run();
        passed("extractor_upgrade_slots").run();
        helper.succeed();
    }

    private static CompoundTag slotPayload(@Nullable Object slot, @Nullable Tag stack) {
        CompoundTag tag = new CompoundTag();
        if(slot instanceof Integer i) tag.putInt("slot", i);
        else if(slot instanceof String str) tag.putString("slot", str);
        if(stack != null) tag.put("stack", stack);
        return tag;
    }

    // IControlReceiverFilter.java:29-41, TileEntityCraneExtractor.java:276-292: "slot" fills a filter slot with one item and advances its mode once, "whitelist" and
    // "maxEject" toggle, only within 20 blocks; a payload that cannot be applied changes nothing
    @GameTest(template = TEMPLATE, batch = "hbm31b_extractor_control", timeoutTicks = 100)
    public static void extractor_control(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            HolderLookup.Provider reg = level.registryAccess();
            CraneExtractorBlockEntity be = placeExtractor(helper, new BlockPos(8, 2, 8), Direction.EAST, Direction.WEST);
            BlockPos abs = be.getBlockPos();
            Player player = helper.makeMockPlayer(GameType.SURVIVAL);
            Vec3 corner = Vec3.atLowerCornerOf(abs);
            player.setPos(corner.x + 3, corner.y, corner.z);
            CompoundTag dirt = stackTag(reg, s(Items.DIRT, 5));
            CompoundTag before = nbt(be);

            List<CompoundTag> rejected = new ArrayList<>();
            for(int slot : new int[] { -1, 9, 17, 18, 100, Integer.MAX_VALUE, Integer.MIN_VALUE }) rejected.add(slotPayload(slot, dirt.copy()));
            rejected.add(slotPayload("0", dirt.copy()));
            rejected.add(slotPayload(0, null));
            rejected.add(slotPayload(0, net.minecraft.nbt.StringTag.valueOf("dirt")));
            rejected.add(slotPayload(0, new CompoundTag()));
            CompoundTag unknown = new CompoundTag();
            unknown.putString("id", "hbmsntm:does_not_exist");
            unknown.putInt("count", 1);
            rejected.add(slotPayload(0, unknown));
            CompoundTag air = new CompoundTag();
            air.putString("id", "minecraft:air");
            air.putInt("count", 1);
            rejected.add(slotPayload(0, air));
            CompoundTag wrongId = dirt.copy();
            wrongId.putInt("id", 5);
            rejected.add(slotPayload(0, wrongId));
            for(int i = 0; i < rejected.size(); i++) {
                CompoundTagControl.apply(player, rejected.get(i), abs);
                check(nbt(be).equals(before), "rejected payload " + i + " " + rejected.get(i) + " changed the extractor to " + nbt(be) + " (IControlReceiverFilter.java:34 range, :36-37 stack)");
            }

            // a valid payload: one item, the count forced to 1, the mode one past none = exact; the same slot again goes on to wildcard (:38-39)
            CompoundTagControl.apply(player, slotPayload(4, dirt.copy()), abs);
            check(be.getItem(4).is(Items.DIRT) && be.getItem(4).getCount() == 1, "the dropped stack is " + be.getItem(4) + ", expected one dirt (:37 stackSize = 1)");
            check("exact".equals(be.matcher.modes[4]), "the mode after the first drop is " + be.matcher.modes[4] + ", expected exact (:39 nextMode only)");
            CompoundTagControl.apply(player, slotPayload(4, stackTag(reg, s(Items.OAK_LOG, 1))), abs);
            check(be.getItem(4).is(Items.OAK_LOG) && "wildcard".equals(be.matcher.modes[4]), "the second drop gave " + be.getItem(4) + " mode " + be.matcher.modes[4] + ", expected an oak log in wildcard mode");
            CompoundTagControl.apply(player, slotPayload(0, dirt.copy()), abs);
            CompoundTagControl.apply(player, slotPayload(8, dirt.copy()), abs);
            check(be.getItem(0).is(Items.DIRT) && be.getItem(8).is(Items.DIRT), "the border slots 0 and 8 were not filled: " + be.getItem(0) + " / " + be.getItem(8));
            // a stack of count 0 is no empty stack: the original keeps it as a stack of size 0 and :37 makes it 1, the codec reads the count 0 as 1; both take it
            CompoundTag zero = dirt.copy();
            zero.putInt("count", 0);
            CompoundTagControl.apply(player, slotPayload(2, zero), abs);
            check(be.getItem(2).is(Items.DIRT) && be.getItem(2).getCount() == 1 && "exact".equals(be.matcher.modes[2]), "a payload with the count 0 gave " + be.getItem(2) + " mode " + be.matcher.modes[2] + ", expected one dirt in exact mode (:36-37)");
            be.setItem(2, ItemStack.EMPTY);
            be.matcher.modes[2] = null;
            for(int i : new int[] { 1, 2, 3, 5, 6, 7 }) check(be.getItem(i).isEmpty(), "slot " + i + " was filled");
            for(int i = 9; i < 20; i++) check(be.getItem(i).isEmpty(), "the buffer or upgrade slot " + i + " was filled");

            // the toggles
            check(!be.isWhitelist && !be.maxEject, "whitelist / maxEject are on by default (:33-34)");
            CompoundTagControl.apply(player, key("whitelist"), abs);
            check(be.isWhitelist && !be.maxEject, "the whitelist key gave " + be.isWhitelist + " / " + be.maxEject + ", expected true / false");
            CompoundTagControl.apply(player, key("maxEject"), abs);
            check(be.isWhitelist && be.maxEject, "the maxEject key gave " + be.isWhitelist + " / " + be.maxEject + ", expected true / true");
            CompoundTagControl.apply(player, key("whitelist"), abs);
            CompoundTagControl.apply(player, key("maxEject"), abs);
            check(!be.isWhitelist && !be.maxEject, "the keys did not toggle back: " + be.isWhitelist + " / " + be.maxEject);

            // :276-278 the permission: closer than 20 blocks. 19.9 works, 20.0 and 70 do not (70 is also past the 64 block lookup limit)
            CompoundTag state = nbt(be);
            player.setPos(corner.x + 19.9, corner.y, corner.z);
            CompoundTagControl.apply(player, key("whitelist"), abs);
            check(be.isWhitelist, "19.9 blocks away the whitelist key did not toggle");
            CompoundTagControl.apply(player, key("whitelist"), abs);
            CompoundTagControl.apply(player, slotPayload(1, dirt.copy()), abs);
            check(be.getItem(1).is(Items.DIRT), "19.9 blocks away a valid drop was refused");
            be.setItem(1, ItemStack.EMPTY);
            be.matcher.modes[1] = null;
            state = nbt(be);
            for(double dist : new double[] { 20.0, 20.5, 30.0, 64.5, 70.0, 5000.0 }) {
                player.setPos(corner.x + dist, corner.y, corner.z);
                CompoundTagControl.apply(player, key("whitelist"), abs);
                CompoundTagControl.apply(player, key("maxEject"), abs);
                CompoundTagControl.apply(player, slotPayload(1, dirt.copy()), abs);
                check(nbt(be).equals(state), dist + " blocks away a payload changed the extractor to " + nbt(be));
            }
            // a payload with an unknown key changes nothing either
            player.setPos(corner.x + 3, corner.y, corner.z);
            CompoundTagControl.apply(player, key("destroyer"), abs);
            check(nbt(be).equals(state), "the inserter's destroyer key changed the extractor");
        }).run();
        passed("extractor_control").run();
        helper.succeed();
    }

    // TileEntityCraneExtractor.java:260-273: isWhitelist, maxEject, mode0..mode8 and the slots survive a save; ModulePatternMatcher.java:154-175
    @GameTest(template = TEMPLATE, batch = "hbm31b_extractor_persistence", timeoutTicks = 100)
    public static void extractor_persistence(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            HolderLookup.Provider reg = level.registryAccess();
            CraneExtractorBlockEntity be = placeExtractor(helper, new BlockPos(8, 2, 8), Direction.EAST, Direction.WEST);
            BlockPos abs = be.getBlockPos();
            check(!be.isWhitelist && !be.maxEject && be.getContainerSize() == 20, "a new extractor has whitelist " + be.isWhitelist + ", maxEject " + be.maxEject + ", " + be.getContainerSize() + " slots, expected false, false, 20");
            be.isWhitelist = true;
            be.maxEject = true;
            be.setItem(0, s(Items.DIRT, 1));
            be.matcher.modes[0] = "wildcard";
            be.setItem(3, s(Items.OAK_LOG, 1));
            be.matcher.modes[3] = "minecraft:logs";
            be.setItem(9, s(Items.STONE, 7));
            be.setItem(18, s(NtmItems.UPGRADE_STACK_3.get(), 1));
            be.setItem(19, s(NtmItems.UPGRADE_EJECTOR_2.get(), 1));
            CompoundTag tag = nbt(be);
            check(tag.getBoolean("isWhitelist") && tag.getBoolean("maxEject") && tag.contains("isWhitelist", Tag.TAG_BYTE) && tag.contains("maxEject", Tag.TAG_BYTE), "the boolean keys are " + tag);
            check("wildcard".equals(tag.getString("mode0")) && "minecraft:logs".equals(tag.getString("mode3")) && !tag.contains("mode1") && !tag.contains("mode8"), "the mode keys are " + tag.getAllKeys());
            check(tag.contains("Items", Tag.TAG_LIST), "the keys are " + tag.getAllKeys() + ", expected Items");

            CraneExtractorBlockEntity loaded = new CraneExtractorBlockEntity(abs, level.getBlockState(abs));
            loaded.loadWithComponents(tag, reg);
            check(loaded.isWhitelist && loaded.maxEject, "the loaded flags are " + loaded.isWhitelist + " / " + loaded.maxEject);
            for(int i = 0; i < 9; i++) check(java.util.Objects.equals(loaded.matcher.modes[i], be.matcher.modes[i]), "mode " + i + " is " + loaded.matcher.modes[i] + " after loading, expected " + be.matcher.modes[i]);
            for(int i = 0; i < 20; i++) check(ItemStack.matches(loaded.getItem(i), be.getItem(i)), "slot " + i + " holds " + loaded.getItem(i) + " after loading, expected " + be.getItem(i));
            check(loaded.getDelay() == 5 && loaded.getAmount() == 64, "the loaded upgrades give delay " + loaded.getDelay() + " and amount " + loaded.getAmount() + ", expected 5 and 64");

            // a key that is not there reads as false / no mode, over what was set before
            CompoundTag cleared = tag.copy();
            cleared.remove("isWhitelist");
            cleared.remove("mode0");
            loaded.loadWithComponents(cleared, reg);
            check(!loaded.isWhitelist && loaded.maxEject && loaded.matcher.modes[0] == null && "minecraft:logs".equals(loaded.matcher.modes[3]), "after removing two keys: whitelist " + loaded.isWhitelist + ", mode0 " + loaded.matcher.modes[0] + ", mode3 " + loaded.matcher.modes[3]);

            // a stale tag mode loads as it is, matches nothing and goes back to exact with the next click
            CompoundTag stale = tag.copy();
            stale.putString("mode3", "hbmsntm:gone");
            loaded.setLevel(level);
            loaded.loadWithComponents(stale, reg);
            check("hbmsntm:gone".equals(loaded.matcher.modes[3]) && !loaded.matchesFilter(s(Items.OAK_LOG, 1)) == !loaded.matcher.isValidForFilter(s(Items.DIRT, 1), 0, s(Items.OAK_LOG, 1)), "the stale mode is " + loaded.matcher.modes[3]);
            loaded.nextMode(3);
            check("exact".equals(loaded.matcher.modes[3]), "the stale mode went to " + loaded.matcher.modes[3] + " on the next click, expected exact");

            // the packet form of the block entity (the screen's data): flags and modes
            RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf(Unpooled.buffer(), level.registryAccess());
            be.serialize(buf);
            CraneExtractorBlockEntity fromPacket = new CraneExtractorBlockEntity(abs, level.getBlockState(abs));
            fromPacket.deserialize(buf);
            check(fromPacket.isWhitelist && fromPacket.maxEject && "wildcard".equals(fromPacket.matcher.modes[0]) && "minecraft:logs".equals(fromPacket.matcher.modes[3]) && fromPacket.matcher.modes[1] == null, "the packet gave whitelist " + fromPacket.isWhitelist + ", maxEject " + fromPacket.maxEject + ", modes " + java.util.Arrays.toString(fromPacket.matcher.modes));
        }).run();
        passed("extractor_persistence").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 5. copy and paste

    private static CompoundTag entry(HolderLookup.Provider reg, int slot, ItemStack stack) {
        CompoundTag t = new CompoundTag();
        t.putByte("slot", (byte) slot);
        return (CompoundTag) stack.save(reg, t);
    }

    private static CompoundTag settings(int input, int output, CompoundTag... entries) {
        CompoundTag tag = new CompoundTag();
        tag.putInt("inputSide", input);
        tag.putInt("outputSide", output);
        ListTag list = new ListTag();
        for(CompoundTag e : entries) list.add(e);
        tag.put("items", list);
        return tag;
    }

    // TileEntityCraneBase.java:113-137 (copy), :140-176 (paste), :179-181: orientation as direction ordinals, the filter as a list with the relative slot; both cranes
    @GameTest(template = TEMPLATE, batch = "hbm31b_crane_copy_paste", timeoutTicks = 100)
    public static void crane_copy_paste(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            HolderLookup.Provider reg = level.registryAccess();
            CranePlayer player = player(helper, GameType.SURVIVAL, 0F);
            Item part = NtmItems.PART_GENERIC.get();

            // copy: ForgeDirection ordinals DOWN 0, UP 1, NORTH 2, SOUTH 3, WEST 4, EAST 5 = Direction.get3DDataValue
            CraneExtractorBlockEntity src = placeExtractor(helper, new BlockPos(4, 2, 4), Direction.NORTH, Direction.DOWN);
            src.setItem(0, s(Items.DIRT, 1));
            src.setItem(3, MetaHelper.newStack(part, 1, 1));
            src.setItem(8, s(Items.OAK_LOG, 1));
            src.setItem(12, s(Items.STONE, 5));
            CompoundTag copied = src.getSettings(level, src.getBlockPos());
            check(copied.getInt("inputSide") == 2 && copied.getInt("outputSide") == 0, "the copied sides are " + copied.getInt("inputSide") + " / " + copied.getInt("outputSide") + ", expected 2 (NORTH) / 0 (DOWN) (:115-116)");
            ListTag items = copied.getList("items", Tag.TAG_COMPOUND);
            check(items.size() == 3, "the copied filter has " + items.size() + " entries, expected the three filled filter slots (the buffer is not copied)");
            check(items.getCompound(0).getByte("slot") == 0 && items.getCompound(1).getByte("slot") == 3 && items.getCompound(2).getByte("slot") == 8, "the copied slots are " + items.getCompound(0).getByte("slot") + " " + items.getCompound(1).getByte("slot") + " " + items.getCompound(2).getByte("slot") + ", expected 0 3 8 (:127 the position among the filter slots)");
            check(ItemStack.parseOptional(reg, items.getCompound(1)).is(part) && MetaHelper.getMeta(ItemStack.parseOptional(reg, items.getCompound(1))) == 1, "the typed part does not survive the copy");
            String[] info = src.infoForDisplay(level, src.getBlockPos());
            check(info.length == 2 && info[0].equals("copytool.filter") && info[1].equals("copytool.orientation"), "the display list is " + java.util.Arrays.toString(info) + " (:180)");

            // the inserter copies the orientation only (it is no IControlReceiverFilter)
            CraneInserterBlockEntity insSrc = placeInserter(helper, new BlockPos(4, 2, 8), Direction.UP, Direction.EAST);
            insSrc.setItem(0, s(Items.DIRT, 4));
            CompoundTag insCopied = insSrc.getSettings(level, insSrc.getBlockPos());
            check(insCopied.getInt("inputSide") == 1 && insCopied.getInt("outputSide") == 5 && !insCopied.contains("items"), "the inserter's copy is " + insCopied + ", expected sides 1 / 5 and no items (:118)");

            // paste into an extractor: the filter (index 0) and the orientation (index 1) are separate
            CraneExtractorBlockEntity dst = placeExtractor(helper, new BlockPos(10, 2, 4), Direction.SOUTH, Direction.UP);
            dst.setItem(5, s(Items.GOLD_INGOT, 1));
            dst.matcher.modes[5] = "exact";
            dst.setItem(0, s(Items.COAL, 1));
            dst.matcher.modes[0] = "exact";
            dst.pasteSettings(copied, 0, level, player, dst.getBlockPos());
            check(dst.getBlockState().getValue(CraneBaseBlock.INPUT) == Direction.SOUTH && dst.getBlockState().getValue(CraneBaseBlock.OUTPUT) == Direction.UP, "pasting the filter changed the orientation to " + sides(dst.getBlockState()));
            check(dst.getItem(0).is(Items.DIRT) && dst.getItem(3).is(part) && MetaHelper.getMeta(dst.getItem(3)) == 1 && dst.getItem(8).is(Items.OAK_LOG), "the pasted filter is " + dst.getItem(0) + " / " + dst.getItem(3) + " / " + dst.getItem(8));
            check(dst.getItem(5).is(Items.GOLD_INGOT) && dst.getItem(12).isEmpty(), "a slot the copy left empty changed to " + dst.getItem(5) + ", or the buffer was pasted: " + dst.getItem(12) + " (:158-170 only the listed slots)");
            check("wildcard".equals(dst.matcher.modes[0]) && "exact".equals(dst.matcher.modes[3]) && "exact".equals(dst.matcher.modes[8]) && "exact".equals(dst.matcher.modes[5]), "the modes after the paste are " + java.util.Arrays.toString(dst.matcher.modes) + ", expected nextMode once per pasted slot: slot 0 from exact to wildcard, slots 3 and 8 from none to exact, slot 5 untouched (:167)");
            dst.pasteSettings(copied, 1, level, player, dst.getBlockPos());
            BlockState pasted = level.getBlockState(dst.getBlockPos());
            check(pasted.getValue(CraneBaseBlock.INPUT) == Direction.NORTH && pasted.getValue(CraneBaseBlock.OUTPUT) == Direction.DOWN, "the pasted orientation is " + sides(pasted) + ", expected input NORTH, output DOWN (:141-148)");
            check(level.getBlockEntity(dst.getBlockPos()) instanceof CraneExtractorBlockEntity now && now.getItem(0).is(Items.DIRT), "the block entity was lost on the orientation paste");

            // paste the inserter's copy: the orientation goes in, a filter paste does nothing
            CraneInserterBlockEntity insDst = placeInserter(helper, new BlockPos(10, 2, 8), Direction.NORTH, Direction.SOUTH);
            insDst.setItem(0, s(Items.DIRT, 4));
            insDst.pasteSettings(insCopied, 0, level, player, insDst.getBlockPos());
            check(insDst.getBlockState().getValue(CraneBaseBlock.INPUT) == Direction.NORTH && insDst.getItem(0).getCount() == 4, "the inserter's filter paste changed " + sides(insDst.getBlockState()) + " / " + insDst.getItem(0));
            insDst.pasteSettings(insCopied, 1, level, player, insDst.getBlockPos());
            check(level.getBlockState(insDst.getBlockPos()).getValue(CraneBaseBlock.INPUT) == Direction.UP && level.getBlockState(insDst.getBlockPos()).getValue(CraneBaseBlock.OUTPUT) == Direction.EAST, "the inserter's pasted orientation is " + sides(level.getBlockState(insDst.getBlockPos())));
            // the extractor's copy also pastes onto the inserter's orientation
            insDst.pasteSettings(copied, 1, level, player, insDst.getBlockPos());
            check(level.getBlockState(insDst.getBlockPos()).getValue(CraneBaseBlock.INPUT) == Direction.NORTH && level.getBlockState(insDst.getBlockPos()).getValue(CraneBaseBlock.OUTPUT) == Direction.DOWN, "the extractor's orientation did not paste onto the inserter: " + sides(level.getBlockState(insDst.getBlockPos())));
            check(insDst.getItem(0).getCount() == 4, "the inserter lost its buffer on the paste");

            // pasted data comes from an item a player can rewrite: orientation that is no pair of different directions changes nothing
            BlockPos probe = new BlockPos(6, 2, 12);
            CraneExtractorBlockEntity victim = placeExtractor(helper, probe, Direction.EAST, Direction.WEST);
            BlockState start = level.getBlockState(victim.getBlockPos());
            int[][] badSides = { { 2, 2 }, { 6, 1 }, { 1, 6 }, { -1, 2 }, { 2, -1 }, { 0, 0 }, { 100, 3 }, { Integer.MAX_VALUE, 0 } };
            for(int[] pair : badSides) {
                victim.pasteSettings(settings(pair[0], pair[1]), 1, level, player, victim.getBlockPos());
                check(level.getBlockState(victim.getBlockPos()) == start && level.getBlockEntity(victim.getBlockPos()) == victim, "the sides " + pair[0] + " / " + pair[1] + " gave " + sides(level.getBlockState(victim.getBlockPos())));
            }
            CompoundTag onlyInput = new CompoundTag();
            onlyInput.putInt("inputSide", 2);
            victim.pasteSettings(onlyInput, 1, level, player, victim.getBlockPos());
            victim.pasteSettings(new CompoundTag(), 1, level, player, victim.getBlockPos());
            CompoundTag text = new CompoundTag();
            text.putString("inputSide", "2");
            text.putString("outputSide", "3");
            victim.pasteSettings(text, 1, level, player, victim.getBlockPos());
            check(level.getBlockState(victim.getBlockPos()) == start, "an incomplete or textual orientation gave " + sides(level.getBlockState(victim.getBlockPos())));

            // the filter list: bad entries are skipped one by one, valid ones go in with the count forced to 1
            CompoundTag unknown = new CompoundTag();
            unknown.putByte("slot", (byte) 1);
            unknown.putString("id", "hbmsntm:does_not_exist");
            unknown.putInt("count", 1);
            CompoundTag noSlot = (CompoundTag) s(Items.DIAMOND, 1).save(reg);
            CompoundTag stringSlot = (CompoundTag) s(Items.DIAMOND, 1).save(reg);
            stringSlot.putString("slot", "2");
            CompoundTag zeroCount = entry(reg, 3, s(Items.EMERALD, 1));
            zeroCount.putInt("count", 0);
            CompoundTag many = entry(reg, 4, s(Items.SAND, 1));
            many.putInt("count", 64);
            CompoundTag air = new CompoundTag();
            air.putByte("slot", (byte) 5);
            air.putString("id", "minecraft:air");
            air.putInt("count", 1);
            // at most nine entries are read per paste, so the bad ones go in two lists
            CompoundTag listed = settings(2, 3,
                    many, zeroCount, entry(reg, -1, s(Items.DIAMOND, 1)), entry(reg, 9, s(Items.DIAMOND, 1)), entry(reg, 127, s(Items.DIAMOND, 1)),
                    unknown, noSlot, stringSlot, air);
            victim.pasteSettings(listed, 0, level, player, victim.getBlockPos());
            victim.pasteSettings(settings(2, 3, new CompoundTag(), entry(reg, -128, s(Items.DIAMOND, 1))), 0, level, player, victim.getBlockPos());
            for(int i = 0; i < 9; i++) {
                if(i == 4) continue;
                if(i == 3) {
                    // a stack of count 0 is no empty stack (the codec reads it as 1, the original keeps a stack of size 0): it is pasted
                    check(victim.getItem(3).is(Items.EMERALD) && victim.getItem(3).getCount() == 1, "the pasted entry with count 0 is " + victim.getItem(3) + ", expected one emerald");
                    continue;
                }
                check(victim.getItem(i).isEmpty(), "bad entry: slot " + i + " holds " + victim.getItem(i) + " after the paste");
            }
            check(victim.getItem(4).is(Items.SAND) && victim.getItem(4).getCount() == 1, "the pasted stack of 64 is " + victim.getItem(4) + ", expected one sand");
            for(int i = 9; i < 20; i++) check(victim.getItem(i).isEmpty(), "a bad slot reached the buffer or the upgrades: slot " + i + " holds " + victim.getItem(i));

            // :158-160 at most nine entries are read: the tenth is ignored even when it is valid
            CompoundTag[] ten = new CompoundTag[10];
            for(int i = 0; i < 9; i++) ten[i] = entry(reg, i, s(Items.DIRT, 1));
            ten[9] = entry(reg, 0, s(Items.DIAMOND, 1));
            CraneExtractorBlockEntity tenDst = placeExtractor(helper, new BlockPos(12, 2, 12), Direction.EAST, Direction.WEST);
            tenDst.pasteSettings(settings(5, 4, ten), 0, level, player, tenDst.getBlockPos());
            for(int i = 0; i < 9; i++) check(tenDst.getItem(i).is(Items.DIRT), "slot " + i + " holds " + tenDst.getItem(i) + " after nine entries and a tenth, expected dirt");

            // the list is missing, or not a list: nothing happens
            CraneExtractorBlockEntity none = placeExtractor(helper, new BlockPos(14, 2, 12), Direction.EAST, Direction.WEST);
            none.setItem(0, s(Items.COAL, 1));
            CompoundTag noList = new CompoundTag();
            noList.putInt("inputSide", 2);
            noList.putInt("outputSide", 3);
            none.pasteSettings(noList, 0, level, player, none.getBlockPos());
            noList.putString("items", "x");
            none.pasteSettings(noList, 0, level, player, none.getBlockPos());
            none.pasteSettings(new CompoundTag(), 0, level, player, none.getBlockPos());
            check(none.getItem(0).is(Items.COAL) && none.getItem(0).getCount() == 1, "a missing list changed slot 0 to " + none.getItem(0));
        }).run();
        passed("crane_copy_paste").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 6. the item handler capability

    @Nullable
    private static IItemHandler handler(ServerLevel level, BlockPos abs, @Nullable Direction side) {
        return level.getCapability(Capabilities.ItemHandler.BLOCK, abs, side);
    }

    // TileEntityCraneExtractor.java:232-246, TileEntityCraneInserter.java: through a side the extractor exposes only the buffer 9-17 (insert has to pass the filter, taking
    // does not), the inserter all 21 slots; an unsided query gets nothing (the original's capability-less 1.7.10 has IInventory sides only)
    @GameTest(template = TEMPLATE, batch = "hbm31b_capability_cranes", timeoutTicks = 100)
    public static void capability_cranes(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            CraneExtractorBlockEntity ex = placeExtractor(helper, new BlockPos(4, 2, 4), Direction.EAST, Direction.WEST);
            BlockPos exAbs = ex.getBlockPos();
            for(Direction d : Direction.values()) {
                IItemHandler h = handler(level, exAbs, d);
                check(h != null && h.getSlots() == 9, "the extractor's handler from " + d + " is " + h + (h == null ? "" : " with " + h.getSlots() + " slots") + ", expected 9 (TileEntityCraneExtractor.java:232-235)");
            }
            check(handler(level, exAbs, null) == null, "an unsided query on the extractor gave a handler");

            ex.setItem(0, s(Items.DIRT, 1));
            ex.matcher.modes[0] = "wildcard";
            ex.setItem(9, s(Items.STONE, 5));
            ex.setItem(17, s(Items.COAL, 2));
            ex.setItem(18, s(NtmItems.UPGRADE_STACK_1.get(), 1));
            ex.setItem(19, s(NtmItems.UPGRADE_EJECTOR_1.get(), 1));
            IItemHandler h = handler(level, exAbs, Direction.UP);
            check(h.getStackInSlot(0).is(Items.STONE) && h.getStackInSlot(0).getCount() == 5 && h.getStackInSlot(8).is(Items.COAL) && h.getStackInSlot(8).getCount() == 2, "the handler's first and last slots are " + h.getStackInSlot(0) + " / " + h.getStackInSlot(8) + ", expected the buffer slots 9 and 17");
            int before = total(ex);

            // blacklist: dirt is the filter item and stays out, sand goes in (:240)
            ItemStack back = h.insertItem(3, s(Items.DIRT, 4), false);
            check(back.is(Items.DIRT) && back.getCount() == 4 && ex.getItem(12).isEmpty(), "a blacklisted dirt was taken: returned " + back + ", slot 12 " + ex.getItem(12));
            back = h.insertItem(3, s(Items.SAND, 4), false);
            check(back.isEmpty() && ex.getItem(12).is(Items.SAND) && ex.getItem(12).getCount() == 4, "sand returned " + back + ", slot 12 holds " + ex.getItem(12) + ", expected it taken (handler slot 3 = slot 12)");
            // whitelist: only dirt
            ex.isWhitelist = true;
            back = h.insertItem(4, s(Items.SAND, 4), false);
            check(back.getCount() == 4 && ex.getItem(13).isEmpty(), "a sand passed the whitelist of dirt: " + back + ", slot 13 " + ex.getItem(13));
            back = h.insertItem(4, s(Items.DIRT, 4), false);
            check(back.isEmpty() && ex.getItem(13).is(Items.DIRT), "a whitelisted dirt returned " + back + ", slot 13 holds " + ex.getItem(13));
            check(total(ex) == before + 8, "the extractor holds " + total(ex) + " items, expected " + (before + 8) + ": nothing lost or duplicated");

            // taking is not filtered (:244): the stone is not on the whitelist and leaves anyway; the simulation takes nothing
            ItemStack sim = h.extractItem(0, 64, true);
            check(sim.is(Items.STONE) && sim.getCount() == 5 && ex.getItem(9).getCount() == 5, "the simulated extraction returned " + sim + ", slot 9 holds " + ex.getItem(9));
            ItemStack took = h.extractItem(0, 64, false);
            check(took.is(Items.STONE) && took.getCount() == 5 && ex.getItem(9).isEmpty(), "the extraction returned " + took + ", slot 9 holds " + ex.getItem(9));

            // the filter slots and the upgrade slots are no part of it: whatever goes in lands in the buffer
            ex.isWhitelist = false;
            ex.setItem(0, ItemStack.EMPTY);
            for(int k = 0; k < 9; k++) h.insertItem(k, s(NtmItems.UPGRADE_EJECTOR_2.get(), 1), false);
            check(ex.getItem(18).is(NtmItems.UPGRADE_STACK_1.get()) && ex.getItem(19).is(NtmItems.UPGRADE_EJECTOR_1.get()), "the upgrade slots changed to " + ex.getItem(18) + " / " + ex.getItem(19));
            for(int i = 0; i < 9; i++) check(ex.getItem(i).isEmpty(), "the filter slot " + i + " holds " + ex.getItem(i) + " after inserting through the handler");

            // the inserter: all 21 slots from every side
            CraneInserterBlockEntity in = placeInserter(helper, new BlockPos(4, 2, 8), Direction.EAST, Direction.WEST);
            BlockPos inAbs = in.getBlockPos();
            for(Direction d : Direction.values()) {
                IItemHandler ih = handler(level, inAbs, d);
                check(ih != null && ih.getSlots() == 21, "the inserter's handler from " + d + " is " + ih + (ih == null ? "" : " with " + ih.getSlots() + " slots") + ", expected 21");
            }
            check(handler(level, inAbs, null) == null, "an unsided query on the inserter gave a handler");
            IItemHandler ih = handler(level, inAbs, Direction.NORTH);
            check(ih.insertItem(0, s(Items.STONE, 64), false).isEmpty() && ih.insertItem(20, s(Items.DIRT, 30), false).isEmpty(), "the first or the last slot refused an insert");
            check(in.getItem(0).is(Items.STONE) && in.getItem(0).getCount() == 64 && in.getItem(20).is(Items.DIRT) && in.getItem(20).getCount() == 30, "the inserter holds " + in.getItem(0) + " / " + in.getItem(20));
            ItemStack out = ih.extractItem(20, 64, false);
            check(out.is(Items.DIRT) && out.getCount() == 30 && in.getItem(20).isEmpty(), "extracting from slot 20 returned " + out);
        }).run();
        passed("capability_cranes").run();
        helper.succeed();
    }

    // NEO machines and crates answer through their face rules: a furnace-like machine takes only smeltables and gives only its output, a crate everything
    @GameTest(template = TEMPLATE, batch = "hbm31b_capability_machines", timeoutTicks = 100)
    public static void capability_machines(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos furnaceRel = new BlockPos(4, 2, 4);
            helper.setBlock(furnaceRel, NtmBlocks.MACHINE_ELECTRIC_FURNACE.get().defaultBlockState());
            MachineElectricFurnaceBlockEntity furnace = SmokeTestSupport.blockEntity(helper, furnaceRel, MachineElectricFurnaceBlockEntity.class);
            BlockPos abs = furnace.getBlockPos();
            for(Direction d : Direction.values()) {
                IItemHandler h = handler(level, abs, d);
                check(h != null && h.getSlots() == 3, "the electric furnace's handler from " + d + " is " + h + ", expected 3 slots");
            }
            check(handler(level, abs, null) == null, "an unsided query on the electric furnace gave a handler");
            IItemHandler h = handler(level, abs, Direction.EAST);
            for(int k = 0; k < 3; k++) check(h.insertItem(k, s(Items.STICK, 1), false).getCount() == 1, "a stick went into handler slot " + k);
            check(h.insertItem(1, s(Items.RAW_IRON, 4), false).isEmpty() && furnace.getItem(MachineElectricFurnaceBlockEntity.SLOT_INPUT).is(Items.RAW_IRON), "raw iron did not go into the input slot");
            check(h.insertItem(2, s(Items.RAW_IRON, 4), false).getCount() == 4 && furnace.getItem(MachineElectricFurnaceBlockEntity.SLOT_OUTPUT).isEmpty(), "raw iron went into the output slot");
            check(h.insertItem(0, s(Items.IRON_INGOT, 1), false).getCount() == 1, "an ingot went into the battery slot");
            furnace.setItem(MachineElectricFurnaceBlockEntity.SLOT_OUTPUT, s(Items.IRON_INGOT, 4));
            check(h.extractItem(1, 4, false).isEmpty() && furnace.getItem(MachineElectricFurnaceBlockEntity.SLOT_INPUT).is(Items.RAW_IRON), "the input slot gave items away");
            ItemStack got = h.extractItem(2, 3, false);
            check(got.is(Items.IRON_INGOT) && got.getCount() == 3 && furnace.getItem(MachineElectricFurnaceBlockEntity.SLOT_OUTPUT).getCount() == 1, "the output slot gave " + got);

            // a crate: 36 slots, everything in and out
            BlockPos crateRel = new BlockPos(4, 2, 8);
            helper.setBlock(crateRel, NtmBlocks.CRATE_IRON.get().defaultBlockState());
            Container crate = containerAt(helper, crateRel);
            BlockPos crateAbs = helper.absolutePos(crateRel);
            for(Direction d : Direction.values()) {
                IItemHandler ch = handler(level, crateAbs, d);
                check(ch != null && ch.getSlots() == 36, "the crate's handler from " + d + " is " + ch + ", expected 36 slots");
            }
            check(handler(level, crateAbs, null) == null, "an unsided query on the crate gave a handler");
            IItemHandler ch = handler(level, crateAbs, Direction.DOWN);
            check(ch.insertItem(35, s(Items.GOLD_INGOT, 17), false).isEmpty() && crate.getItem(35).is(Items.GOLD_INGOT) && crate.getItem(35).getCount() == 17, "the crate's last slot holds " + crate.getItem(35));
            ItemStack gold = ch.extractItem(35, 17, false);
            check(gold.getCount() == 17 && crate.getItem(35).isEmpty(), "the crate gave " + gold);
        }).run();
        passed("capability_machines").run();
        helper.succeed();
    }

    // a multiblock's port cell answers for the core's inventory only when the proxy carries the inventory flag (TileEntityProxyCombo.java:242-249 getSizeInventory = 0 without it)
    @GameTest(template = TEMPLATE, batch = "hbm31b_capability_proxies", timeoutTicks = 100)
    public static void capability_proxies(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos center = new BlockPos(8, 1, 8);

            // the crystallizer's four corner ports carry the inventory flag: slots {input, output} of the core
            DummyableBlock crystallizer = (DummyableBlock) NtmBlocks.MACHINE_CRYSTALLIZER.get();
            SmokeTestSupport.place(helper, crystallizer, center, Direction.NORTH);
            MachineCrystallizerBlockEntity core = SmokeTestSupport.blockEntity(helper, center, MachineCrystallizerBlockEntity.class);
            core.setItem(MachineCrystallizerBlockEntity.SLOT_OUTPUT, s(Items.IRON_INGOT, 3));
            for(BlockPos extra : SmokeTestSupport.crystallizerExtras(center)) {
                BlockPos abs = helper.absolutePos(extra);
                check(level.getBlockEntity(abs) instanceof ProxyComboBlockEntity proxy && proxy.hasInventory(), "the port " + extra + " has no inventory flag: " + level.getBlockEntity(abs));
                check(handler(level, abs, null) == null, "an unsided query on the port " + extra + " gave a handler");
                for(Direction d : Direction.values()) {
                    IItemHandler h = handler(level, abs, d);
                    check(h != null && h.getSlots() == 2, "the port " + extra + " from " + d + " gives " + h + (h == null ? "" : " with " + h.getSlots() + " slots") + ", expected 2 (input and output)");
                    check(h.getStackInSlot(1).is(Items.IRON_INGOT) && h.getStackInSlot(1).getCount() == 3, "the port's second slot shows " + h.getStackInSlot(1) + ", expected the core's output");
                    check(h.insertItem(0, s(Items.STONE, 1), true).getCount() == 1, "the port took a stone into the input slot without a recipe");
                    check(h.insertItem(1, s(Items.IRON_INGOT, 1), true).getCount() == 1, "the port took an item into the output slot");
                }
            }
            IItemHandler port = handler(level, helper.absolutePos(center.offset(1, 0, 1)), Direction.EAST);
            ItemStack out = port.extractItem(1, 2, false);
            check(out.is(Items.IRON_INGOT) && out.getCount() == 2 && core.getItem(MachineCrystallizerBlockEntity.SLOT_OUTPUT).getCount() == 1, "the port's extraction returned " + out + ", the core holds " + core.getItem(MachineCrystallizerBlockEntity.SLOT_OUTPUT));
            check(port.extractItem(0, 1, false).isEmpty(), "the port gave something from the input slot");
            // a plain dummy cell has no block entity and no handler
            BlockPos dummy = helper.absolutePos(center.above(2));
            check(level.getBlockEntity(dummy) == null, "a dummy cell has the block entity " + level.getBlockEntity(dummy));
            for(Direction d : Direction.values()) check(handler(level, dummy, d) == null, "a dummy cell gave a handler from " + d);
            helper.destroyBlock(center);
        }).run();
        passed("capability_proxies").run();
        helper.succeed();
    }

    // the turbine's ports are fluid and power proxies without the inventory flag: no handler at all
    @GameTest(template = TEMPLATE, batch = "hbm31b_capability_proxies_none", timeoutTicks = 100)
    public static void capability_proxies_none(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos center = new BlockPos(8, 1, 8);
            DummyableBlock turbine = (DummyableBlock) NtmBlocks.MACHINE_INDUSTRIAL_TURBINE.get();
            for(Direction dir : new Direction[] { Direction.NORTH, Direction.EAST }) {
                SmokeTestSupport.place(helper, turbine, center, dir);
                for(BlockPos extra : SmokeTestSupport.turbineExtras(center, dir)) {
                    BlockPos abs = helper.absolutePos(extra);
                    check(level.getBlockEntity(abs) instanceof ProxyComboBlockEntity proxy && !proxy.hasInventory(), "the turbine port " + extra + " has an inventory flag: " + level.getBlockEntity(abs));
                    check(handler(level, abs, null) == null, "an unsided query on the turbine port " + extra + " gave a handler");
                    for(Direction d : Direction.values()) check(handler(level, abs, d) == null, "the turbine port " + extra + " from " + d + " gave a handler (no inventory flag)");
                }
                helper.destroyBlock(center);
            }
        }).run();
        passed("capability_proxies_none").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 7. the wand route

    private static void wandClick(CranePlayer player, ServerLevel level, ItemStack wand, BlockPos abs, Direction face) {
        player.setItemInHand(InteractionHand.MAIN_HAND, wand);
        player.gameMode.useItemOn(player, level, wand, InteractionHand.MAIN_HAND, new BlockHitResult(Vec3.atCenterOf(abs), face, abs, false));
    }

    /** Builds a route from the stone at (3,2,z) to the target at (8,2,z), both clicked on top, and returns the belts that stand in that row afterwards. */
    private static Map<BlockPos, BlockState> routeInto(GameTestHelper helper, CranePlayer player, int z, BlockState target, boolean sneak) {
        helper.setBlock(new BlockPos(3, 2, z), Blocks.STONE.defaultBlockState());
        helper.setBlock(new BlockPos(8, 2, z), target);
        ItemStack wand = MetaHelper.newStack(NtmItems.CONVEYOR_WAND.get(), 1, ConveyorType.REGULAR);
        player.setShiftKeyDown(false);
        wandClick(player, helper.getLevel(), wand, helper.absolutePos(new BlockPos(3, 2, z)), Direction.UP);
        check(ConveyorWandItem.hasStart(wand), "the first click stored no start");
        player.setShiftKeyDown(sneak);
        wandClick(player, helper.getLevel(), wand, helper.absolutePos(new BlockPos(8, 2, z)), Direction.UP);
        player.setShiftKeyDown(false);
        Map<BlockPos, BlockState> found = new LinkedHashMap<>();
        for(int x = 0; x < 16; x++) for(int y = 0; y < 12; y++) for(int zz = Math.max(0, z - 1); zz <= Math.min(15, z + 1); zz++) {
            BlockPos rel = new BlockPos(x, y, zz);
            BlockState s = helper.getBlockState(rel);
            if(s.getBlock() instanceof ConveyorBaseBlock) found.put(rel, s);
        }
        return found;
    }

    // ItemConveyorWand.java:398-400 (shouldTurnToTarget also for BlockCraneBase), :425-427, :432-435: the route towards a crane ends one block above it and the last cell
    // turns down into it (a chute); towards any other block the route ends on the target's top cell as a plain belt. The clicks go through the real use path: the crane opens no menu
    @GameTest(template = TEMPLATE, batch = "hbm31b_crane_wand_route", timeoutTicks = 100)
    public static void crane_wand_route(GameTestHelper helper) {
        guard(() -> {
            CranePlayer player = player(helper, GameType.CREATIVE, 0F);
            int z = 2;
            for(Block block : new Block[] { inserterBlock(), extractorBlock() }) {
                String name = BuiltInRegistries.BLOCK.getKey(block).getPath();
                BlockState target = crane(block, Direction.NORTH, Direction.SOUTH);
                Map<BlockPos, BlockState> found = routeInto(helper, player, z, target, false);
                check(player.opened.isEmpty(), name + ": the wand click opened a menu");
                check(helper.getBlockState(new BlockPos(8, 2, z)) == target, name + ": the target changed to " + helper.getBlockState(new BlockPos(8, 2, z)));
                check(found.size() == 6, name + ": " + found.size() + " belts stand around the route, expected 6 (five belts and the chute): " + found.keySet());
                for(int x = 3; x <= 7; x++) {
                    BlockState s = found.get(new BlockPos(x, 3, z));
                    check(s != null && s.is(NtmBlocks.CONVEYOR.get()) && s.getValue(ConveyorBaseBlock.HORIZONTAL_FACING) == Direction.WEST && s.getValue(ConveyorBlock.SHAPE) == Shape.STRAIGHT, name + ": the cell " + x + " of the route is " + s + ", expected a straight belt with the input side WEST");
                }
                BlockState last = found.get(new BlockPos(8, 3, z));
                check(last != null && last.is(NtmBlocks.CONVEYOR_CHUTE.get()) && last.getValue(ConveyorBaseBlock.HORIZONTAL_FACING) == Direction.WEST, name + ": the last cell above the crane is " + last + ", expected a chute with the input side WEST (:432-435)");
                z += 4;
            }
            // a stone, a chest and a furnace as the target: no turn, the last cell is a plain belt
            for(BlockState target : new BlockState[] { Blocks.STONE.defaultBlockState(), Blocks.CHEST.defaultBlockState(), Blocks.FURNACE.defaultBlockState() }) {
                // a chest or a furnace opens its own menu on a plain click, so the wand clicks them sneaking
                Map<BlockPos, BlockState> found = routeInto(helper, player, z, target, true);
                check(found.size() == 6, target.getBlock() + ": " + found.size() + " belts stand around the route, expected 6: " + found.keySet());
                for(int x = 3; x <= 8; x++) {
                    BlockState s = found.get(new BlockPos(x, 3, z));
                    check(s != null && s.is(NtmBlocks.CONVEYOR.get()) && s.getValue(ConveyorBaseBlock.HORIZONTAL_FACING) == Direction.WEST && s.getValue(ConveyorBlock.SHAPE) == Shape.STRAIGHT, target.getBlock() + ": the cell " + x + " of the route is " + s + ", expected a straight belt with the input side WEST (:400)");
                }
                z += 2;
            }
        }).run();
        passed("crane_wand_route").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 8. the recipes

    private static ShapedRecipe loadShaped(GameTestHelper helper, String path, int w, int h, Item result, int count, String original) {
        ServerLevel level = helper.getLevel();
        RecipeHolder<?> holder = level.getRecipeManager().byKey(id(path)).orElse(null);
        check(holder != null, "recipe " + id(path) + " is not loaded (" + original + ")");
        check(holder.value() instanceof ShapedRecipe, path + " is " + holder.value().getClass().getSimpleName() + ", expected a shaped recipe (" + original + ")");
        ShapedRecipe recipe = (ShapedRecipe) holder.value();
        check(recipe.getWidth() == w && recipe.getHeight() == h, path + " is " + recipe.getWidth() + "x" + recipe.getHeight() + ", expected " + w + "x" + h + " (" + original + ")");
        ItemStack out = recipe.getResultItem(level.registryAccess());
        check(out.is(result) && out.getCount() == count && MetaHelper.getMeta(out) == 0, path + " yields " + out + " with type " + MetaHelper.getMeta(out) + ", expected " + count + " x " + result + " (" + original + ")");
        return recipe;
    }

    private static boolean matches(GameTestHelper helper, ShapedRecipe recipe, ItemStack... cells) {
        List<ItemStack> grid = new ArrayList<>();
        for(ItemStack c : cells) grid.add(c == null ? ItemStack.EMPTY : c);
        return recipe.matches(CraftingInput.of(3, 3, grid), helper.getLevel());
    }

    /** The full pattern matches and is assembled with its count; a stick in any filled cell and anything in an empty cell breaks it. */
    private static void fullGrid(GameTestHelper helper, String path, ShapedRecipe recipe, Item result, int count, String original, ItemStack... cells) {
        check(cells.length == 9, "the test lists " + cells.length + " cells for 3x3");
        check(matches(helper, recipe, cells), path + " does not match its own pattern (" + original + ")");
        List<ItemStack> grid = new ArrayList<>();
        for(ItemStack c : cells) grid.add(c == null ? ItemStack.EMPTY : c);
        ItemStack crafted = recipe.assemble(CraftingInput.of(3, 3, grid), helper.getLevel().registryAccess());
        check(crafted.is(result) && crafted.getCount() == count && MetaHelper.getMeta(crafted) == 0, path + " crafts " + crafted + ", expected " + count + " x " + result);
        for(int i = 0; i < cells.length; i++) {
            ItemStack[] bad = cells.clone();
            bad[i] = cells[i] == null ? new ItemStack(Items.DIRT) : new ItemStack(Items.STICK);
            check(!matches(helper, recipe, bad), path + " matches with " + bad[i] + " in cell " + i + " (" + original + ")");
        }
    }

    private static ItemStack regularWand() {
        return MetaHelper.newStack(NtmItems.CONVEYOR_WAND.get(), 1, ConveyorType.REGULAR);
    }

    private static ItemStack piston(PartGenericItem.Type type) {
        return MetaHelper.newStack(NtmItems.PART_GENERIC.get(), 1, type);
    }

    private static ItemStack[] ring(ItemStack c, ItemStack middle, ItemStack b) {
        return new ItemStack[] { c, c, c, c, middle, c, c, b, c };
    }

    private static void craneRecipes(GameTestHelper helper, Block block, boolean extractor, String original) {
        String prefix = BuiltInRegistries.BLOCK.getKey(block).getPath();
        ItemStack[][] casings = {
                { s(Items.STONE_BRICKS, 1), s(Items.MOSSY_STONE_BRICKS, 1), s(Items.CRACKED_STONE_BRICKS, 1), s(Items.CHISELED_STONE_BRICKS, 1) },
                { s(Items.IRON_INGOT, 1) },
                { s(NtmItems.INGOT_STEEL.get(), 1) } };
        String[] names = { "stone_bricks", "iron", "steel" };
        int[] counts = { 1, 2, 4 };
        ItemStack middle = extractor ? piston(PartGenericItem.Type.PISTON_PNEUMATIC) : null;
        for(int i = 0; i < 3; i++) {
            String path = prefix + "_" + names[i];
            ShapedRecipe r = loadShaped(helper, path, 3, 3, block.asItem(), counts[i], original);
            fullGrid(helper, path, r, block.asItem(), counts[i], original, ring(casings[i][0], middle, regularWand()));
            for(ItemStack alt : casings[i]) check(matches(helper, r, ring(alt, middle, regularWand())), path + " rejects the casing " + alt + " (" + original + ")");
            // the casings do not mix across recipes: the other two casings never match this one
            for(int j = 0; j < 3; j++) {
                if(j == i) continue;
                check(!matches(helper, r, ring(casings[j][0], middle, regularWand())), path + " accepts the casing " + casings[j][0] + " of " + names[j]);
            }
            ItemStack[] mixed = ring(casings[i][0], middle, regularWand());
            mixed[0] = casings[(i + 1) % 3][0];
            check(!matches(helper, r, mixed), path + " accepts one cell of another casing");
            check(!matches(helper, r, ring(s(Items.STONE, 1), middle, regularWand())), path + " accepts plain stone as the casing");
            check(!matches(helper, r, ring(casings[i][0], middle, MetaHelper.newStack(NtmItems.CONVEYOR_WAND.get(), 1, ConveyorType.EXPRESS))), path + " accepts an express wand (:876 the regular type)");
            check(!matches(helper, r, ring(casings[i][0], middle, MetaHelper.newStack(NtmItems.CONVEYOR_WAND.get(), 1, ConveyorType.DOUBLE))), path + " accepts a double wand");
            if(extractor) {
                check(!matches(helper, r, ring(casings[i][0], piston(PartGenericItem.Type.PISTON_HYDRAULIC), regularWand())), path + " accepts a hydraulic piston (:878 pneumatic only)");
                check(!matches(helper, r, ring(casings[i][0], piston(PartGenericItem.Type.PISTON_ELECTRIC), regularWand())), path + " accepts an electric piston");
                check(!matches(helper, r, ring(casings[i][0], s(Items.PISTON, 1), regularWand())), path + " accepts a vanilla piston");
                check(!matches(helper, r, ring(casings[i][0], null, regularWand())), path + " matches without the piston");
            }
        }
        // 1.7.10's wildcard casing: bricks of different variants mix in one grid (Blocks.stonebrick, :868)
        ShapedRecipe bricks = loadShaped(helper, prefix + "_stone_bricks", 3, 3, block.asItem(), 1, original);
        ItemStack[] variants = ring(s(Items.STONE_BRICKS, 1), middle, regularWand());
        variants[1] = s(Items.MOSSY_STONE_BRICKS, 1);
        variants[2] = s(Items.CRACKED_STONE_BRICKS, 1);
        variants[3] = s(Items.CHISELED_STONE_BRICKS, 1);
        check(matches(helper, bricks, variants), prefix + "_stone_bricks does not accept different brick variants in one grid (" + original + ")");
    }

    // CraftingManager.java:867-877: crane_inserter x1 / x2 / x4 with stone bricks / iron / steel around a regular conveyor wand
    @GameTest(template = TEMPLATE, batch = "hbm31b_recipe_crane_inserter", timeoutTicks = 100)
    public static void recipe_crane_inserter(GameTestHelper helper) {
        guard(() -> craneRecipes(helper, inserterBlock(), false, "CraftingManager.java:867-876")).run();
        passed("recipe_crane_inserter").run();
        helper.succeed();
    }

    // CraftingManager.java:867-878: crane_extractor x1 / x2 / x4 with a pneumatic piston in the middle
    @GameTest(template = TEMPLATE, batch = "hbm31b_recipe_crane_extractor", timeoutTicks = 100)
    public static void recipe_crane_extractor(GameTestHelper helper) {
        guard(() -> craneRecipes(helper, extractorBlock(), true, "CraftingManager.java:867-878")).run();
        passed("recipe_crane_extractor").run();
        helper.succeed();
    }

    private static ItemStack[] upgradeGrid(ItemStack c, ItemStack p, ItemStack u) {
        return new ItemStack[] { null, c, null, p, u, p, null, c, null };
    }

    private static void upgradeRecipes(GameTestHelper helper, String prefix, Item[] results, ItemStack[] casings, ItemStack[] sides, ItemStack[] bases, String original) {
        for(int i = 0; i < 3; i++) {
            String path = prefix + (i + 1);
            ShapedRecipe r = loadShaped(helper, path, 3, 3, results[i], 1, original);
            fullGrid(helper, path, r, results[i], 1, original, upgradeGrid(casings[i], sides[i], bases[i]));
            for(int j = 0; j < 3; j++) {
                if(j == i) continue;
                check(!matches(helper, r, upgradeGrid(casings[j], sides[i], bases[i])), path + " accepts the casing of tier " + (j + 1));
                if(!ItemStack.isSameItemSameComponents(sides[j], sides[i])) check(!matches(helper, r, upgradeGrid(casings[i], sides[j], bases[i])), path + " accepts the side parts of tier " + (j + 1));
                check(!matches(helper, r, upgradeGrid(casings[i], sides[i], bases[j])), path + " accepts the upgrade of tier " + j + " as the base (" + original + " each tier from the one below)");
            }
            check(!matches(helper, r, upgradeGrid(casings[i], sides[i], s(Items.STONE, 1))), path + " accepts stone as the base");
            // the top and bottom cells are one ingredient: a different casing in one of them breaks it
            ItemStack[] odd = upgradeGrid(casings[i], sides[i], bases[i]);
            odd[7] = casings[(i + 1) % 3];
            check(!matches(helper, r, odd), path + " accepts two different casings");
            if(!ItemStack.isSameItemSameComponents(sides[(i + 1) % 3], sides[i])) {
                ItemStack[] oddSide = upgradeGrid(casings[i], sides[i], bases[i]);
                oddSide[5] = sides[(i + 1) % 3];
                check(!matches(helper, r, oddSide), path + " accepts two different side parts");
            }
        }
    }

    // CraftingManager.java:731-733: the stack upgrades, each from the one below: vacuum tube / capacitor / chip, pneumatic / hydraulic / electric piston
    @GameTest(template = TEMPLATE, batch = "hbm31b_recipe_upgrade_stack", timeoutTicks = 100)
    public static void recipe_upgrade_stack(GameTestHelper helper) {
        guard(() -> upgradeRecipes(helper, "upgrade_stack_",
                new Item[] { NtmItems.UPGRADE_STACK_1.get(), NtmItems.UPGRADE_STACK_2.get(), NtmItems.UPGRADE_STACK_3.get() },
                new ItemStack[] { s(NtmItems.CIRCUIT_VACUUM_TUBE.get(), 1), s(NtmItems.CIRCUIT_CAPACITOR.get(), 1), s(NtmItems.CIRCUIT_MICROCHIP.get(), 1) },
                new ItemStack[] { piston(PartGenericItem.Type.PISTON_PNEUMATIC), piston(PartGenericItem.Type.PISTON_HYDRAULIC), piston(PartGenericItem.Type.PISTON_ELECTRIC) },
                new ItemStack[] { s(NtmItems.UPGRADE_TEMPLATE.get(), 1), s(NtmItems.UPGRADE_STACK_1.get(), 1), s(NtmItems.UPGRADE_STACK_2.get(), 1) },
                "CraftingManager.java:731-733")).run();
        passed("recipe_upgrade_stack").run();
        helper.succeed();
    }

    // CraftingManager.java:734-736: the ejector upgrades: copper / gold / saturnite plates around motors
    @GameTest(template = TEMPLATE, batch = "hbm31b_recipe_upgrade_ejector", timeoutTicks = 100)
    public static void recipe_upgrade_ejector(GameTestHelper helper) {
        ItemStack motor = s(NtmItems.MOTOR.get(), 1);
        guard(() -> upgradeRecipes(helper, "upgrade_ejector_",
                new Item[] { NtmItems.UPGRADE_EJECTOR_1.get(), NtmItems.UPGRADE_EJECTOR_2.get(), NtmItems.UPGRADE_EJECTOR_3.get() },
                new ItemStack[] { s(NtmItems.PLATE_COPPER.get(), 1), s(NtmItems.PLATE_GOLD.get(), 1), s(NtmItems.PLATE_SATURNITE.get(), 1) },
                new ItemStack[] { motor, motor, motor },
                new ItemStack[] { s(NtmItems.UPGRADE_TEMPLATE.get(), 1), s(NtmItems.UPGRADE_EJECTOR_1.get(), 1), s(NtmItems.UPGRADE_EJECTOR_2.get(), 1) },
                "CraftingManager.java:734-736")).run();
        passed("recipe_upgrade_ejector").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 9. item conservation at the crucible's ports and a furnace's fuel slot

    // TileEntityProxyCombo.java:242-249: a port reports the core's stack limit (the crucible holds one item per slot), so inserting through the handler or a real inserter
    // never loses items: what the crucible does not take stays with the sender
    @GameTest(template = TEMPLATE, batch = "hbm31b_crucible_port_no_loss", timeoutTicks = 100)
    public static void crucible_port_no_loss(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos center = new BlockPos(8, 1, 8);
            SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.MACHINE_CRUCIBLE.get(), center, Direction.NORTH);
            MachineCrucibleBlockEntity core = SmokeTestSupport.blockEntity(helper, center, MachineCrucibleBlockEntity.class);
            check(core.canPlaceItem(0, s(Items.IRON_INGOT, 1)), "the crucible does not take an iron ingot into an empty slot: pick another smeltable item");
            List<BlockPos> ports = new ArrayList<>();
            for(int x = 7; x <= 9; x++) for(int y = 1; y <= 2; y++) for(int z = 7; z <= 9; z++) {
                BlockPos rel = new BlockPos(x, y, z);
                if(level.getBlockEntity(helper.absolutePos(rel)) instanceof ProxyComboBlockEntity proxy && proxy.hasInventory()) ports.add(rel);
            }
            check(!ports.isEmpty(), "the crucible has no port cell with an inventory");
            for(BlockPos port : ports) {
                for(Direction side : Direction.values()) {
                    for(int i = 0; i < 9; i++) core.setItem(i, ItemStack.EMPTY);
                    IItemHandler h = handler(level, helper.absolutePos(port), side);
                    check(h != null && h.getSlots() == 9, "the port " + port + " from " + side + " gives " + h + ", expected a handler with 9 slots");
                    int left = 64;
                    for(int k = 0; k < 9; k++) {
                        left = h.insertItem(k, s(Items.IRON_INGOT, left), false).getCount();
                        check(core.getItem(k).getCount() <= 1, "port " + port + " from " + side + ": crucible slot " + k + " holds " + core.getItem(k) + ", expected at most one (TileEntityProxyCombo.java:242-249 stack limit)");
                    }
                    check(total(core) + left == 64, "port " + port + " from " + side + ": the crucible holds " + total(core) + " and " + left + " were returned, expected 64 in total");
                    check(total(core) == 9 && left == 55, "port " + port + " from " + side + ": the crucible holds " + total(core) + " ingots, expected one in each of the 9 slots");
                }
            }
            for(int i = 0; i < 9; i++) core.setItem(i, ItemStack.EMPTY);

            // a real inserter next to a port on the east side, output facing it
            BlockPos port = null;
            for(BlockPos p : ports) if(p.getX() == 9) port = p;
            check(port != null, "no port cell on the east side of the crucible: " + ports);
            BlockPos inserterRel = port.east();
            CraneInserterBlockEntity in = placeInserter(helper, inserterRel, Direction.EAST, Direction.WEST);
            IRig rig = new IRig(helper, inserterRel, Direction.EAST, Direction.WEST, in);
            rig.enter(s(Items.IRON_INGOT, 64));
            for(int k = 0; k < 9; k++) check(core.getItem(k).getCount() <= 1, "inserter: crucible slot " + k + " holds " + core.getItem(k) + ", expected at most one");
            check(total(core) >= 1, "the inserter put nothing into the crucible");
            check(total(core) + total(in) + loose(helper, Items.IRON_INGOT) == 64, "inserter: the crucible holds " + total(core) + ", the inserter " + total(in) + ", " + loose(helper, Items.IRON_INGOT) + " lie around; expected 64 in total");
        }).run();
        passed("crucible_port_no_loss").run();
        helper.succeed();
    }

    // CraneInserter.java:98-146 (furnace: fuel slot first): the fuel slot of a furnace takes at most one empty bucket, as in vanilla, and nothing is lost
    @GameTest(template = TEMPLATE, batch = "hbm31b_inserter_furnace_bucket", timeoutTicks = 100)
    public static void inserter_furnace_bucket(GameTestHelper helper) {
        guard(() -> {
            IRig rig = inserterRig(helper, new BlockPos(8, 2, 8), Direction.WEST);
            helper.setBlock(rig.targetRel(), Blocks.FURNACE.defaultBlockState());
            Container furnace = containerAt(helper, rig.targetRel());
            rig.enter(s(Items.BUCKET, 16));
            check(furnace.getItem(1).isEmpty() || (furnace.getItem(1).is(Items.BUCKET) && furnace.getItem(1).getCount() == 1), "the furnace's fuel slot holds " + furnace.getItem(1) + ", expected at most one empty bucket");
            check(count(furnace, Items.BUCKET) + count(rig.be, Items.BUCKET) + loose(helper, Items.BUCKET) == 16, "the furnace holds " + count(furnace, Items.BUCKET) + " buckets, the inserter " + count(rig.be, Items.BUCKET) + ", " + loose(helper, Items.BUCKET) + " lie around; expected 16 in total");
            // a second stack: the fuel slot is taken, so it cannot grow
            rig.enter(s(Items.BUCKET, 16));
            check(furnace.getItem(1).isEmpty() || furnace.getItem(1).getCount() == 1, "after a second stack the fuel slot holds " + furnace.getItem(1));
            check(count(furnace, Items.BUCKET) + count(rig.be, Items.BUCKET) + loose(helper, Items.BUCKET) == 32, "after a second stack " + (count(furnace, Items.BUCKET) + count(rig.be, Items.BUCKET) + loose(helper, Items.BUCKET)) + " buckets exist, expected 32");
        }).run();
        passed("inserter_furnace_bucket").run();
        helper.succeed();
    }
}
