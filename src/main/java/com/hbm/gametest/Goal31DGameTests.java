package com.hbm.gametest;

import com.hbm.blockentity.IFluidCopiable;
import com.hbm.blockentity.machine.MachineCombustionEngineBlockEntity;
import com.hbm.blockentity.machine.MachineCompressorBlockEntity;
import com.hbm.blockentity.machine.MachineMixerBlockEntity;
import com.hbm.blockentity.machine.MachineTurbofanBlockEntity;
import com.hbm.blockentity.machine.heater.HeaterElectricBlockEntity;
import com.hbm.blockentity.machine.heater.HeaterHeatexBlockEntity;
import com.hbm.blockentity.machine.heater.HeaterOilburnerBlockEntity;
import com.hbm.blockentity.machine.oil.MachineCokerBlockEntity;
import com.hbm.blockentity.machine.oil.MachineFractionTowerBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKAutoloaderBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKControlAutoBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKControlManualBlockEntity;
import com.hbm.blockentity.machine.rbmk.RBMKControlManualBlockEntity.RBMKColor;
import com.hbm.blockentity.machine.storage.BarrelBlockEntity;
import com.hbm.blockentity.machine.storage.BatteryBaseBlockEntity;
import com.hbm.blockentity.machine.storage.MachineFluidTankBlockEntity;
import com.hbm.blockentity.bomb.LaunchPadBaseBlockEntity;
import com.hbm.blockentity.network.CablePaintableBlockEntity;
import com.hbm.blockentity.network.CraneBaseBlockEntity;
import com.hbm.blockentity.network.CraneExtractorBlockEntity;
import com.hbm.blockentity.network.CranePartitionerBlockEntity;
import com.hbm.blockentity.network.CraneRouterBlockEntity;
import com.hbm.blockentity.network.CraneSplitterBlockEntity;
import com.hbm.blockentity.network.PipeAnchorBlockEntity;
import com.hbm.blockentity.network.PipeBaseBlockEntity;
import com.hbm.blockentity.network.PipePaintableBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.network.ConveyorBaseBlock;
import com.hbm.blocks.network.ConveyorBlock;
import com.hbm.blocks.network.ConveyorBlock.Shape;
import com.hbm.blocks.network.CraneBaseBlock;
import com.hbm.blocks.network.CranePartitionerBlock;
import com.hbm.blocks.network.CraneRouterBlock;
import com.hbm.blocks.network.CraneSplitterBlock;
import com.hbm.blocks.network.FluidDuctConnectingBlock;
import com.hbm.blocks.network.FluidValveBlock;
import com.hbm.entity.NtmEntityTypes;
import com.hbm.entity.item.MovingItem;
import com.hbm.entity.item.MovingPackage;
import com.hbm.extprop.HbmPlayerAttachments;
import com.hbm.handler.HbmKeybinds.EnumKeybind;
import com.hbm.interfaces.ICopiable;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.menus.CraneRouterMenu;
import com.hbm.inventory.recipes.CrystallizerRecipes;
import com.hbm.inventory.recipes.CrystallizerRecipes.CrystallizerRecipe;
import com.hbm.items.NtmItems;
import com.hbm.items.PartGenericItem;
import com.hbm.items.machine.FluidIDMultiItem;
import com.hbm.items.tools.ConveyorWandItem.ConveyorType;
import com.hbm.items.tools.SettingsToolItem;
import com.hbm.main.NuclearTechMod;
import com.hbm.network.toserver.CompoundTagControl;
import com.hbm.util.TagsUtil;
import com.mojang.authlib.GameProfile;
import com.mojang.logging.LogUtils;
import io.netty.buffer.Unpooled;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.IntArrayTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.NbtUtils;
import net.minecraft.nbt.StringTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.world.Container;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.MenuProvider;
import net.minecraft.world.entity.Entity;
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
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.phys.shapes.CollisionContext;
import net.neoforged.neoforge.capabilities.Capabilities;
import net.neoforged.neoforge.common.util.FakePlayer;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import net.neoforged.neoforge.items.IItemHandler;
import org.slf4j.Logger;

import javax.annotation.Nullable;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.OptionalInt;
import java.util.Set;
import java.util.UUID;
import java.util.function.Consumer;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal31D: the conveyor sorter (crane_router), splitter (crane_splitter) and acidizer input partitioner
 * (crane_partitioner), the settings tool with the copy / paste of every ICopiable family, the TOOL_CTRL / TOOL_ALT keys on the pipes,
 * the right-click of a moving item with a nearly full inventory (Goal 31 small fix 2) and the four recipes. Same template and
 * conventions as {@link Goal31CGameTests}; every test has its own batch.
 * <p>
 * Expected values come from the ORIGINAL at cd0cff450, cited beside each group of checks (CraneRouter.java:64-76,119-157,159-261;
 * TileEntityCraneRouter.java:25-203; ContainerCraneRouter.java:19-63; ModulePatternMatcher.java:30-151; CraneSplitter.java:34,91-187;
 * TileEntityCraneSplitter.java:19-74; CranePartitioner.java:67-248; CrystallizerRecipes.java:108-109,268-286,318-322;
 * ItemSettingsTool.java:29-139; IFluidCopiable.java:18-69; TileEntityPipeBaseNT.java:145-168; FluidDuctBase.java:66-98;
 * TileEntityCraneExtractor.java:178-185; CraftingManager.java:886-888; ToolRecipes.java:124), not from the NEO implementation. Test
 * areas lie millions of blocks out, so no position or direction is computed by subtracting floats.
 * <p>
 * Real classes and state: the registered blocks, block entities and menus, the real MovingItem / MovingPackage entities, belts, chests,
 * ServerPlayerGameMode.useItemOn with a NeoForge FakePlayer (so IItemExtension.onItemUseFirst, the block's own right-click and the
 * item's useOn run in their real order), CompoundTagControl.apply, the item capability, NBT save / load and the RecipeManager with real
 * CraftingInput grids. Not evidence: rendering (models, colours, the OBJ shapes, the sorter screen), the look overlay text, the
 * InformPlayer display slots, the client side of the right-click (a client level is not available on the server), sound audibility,
 * multiplayer, a dedicated server with real players, saved worlds and 1.7.10 itself.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class Goal31DGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-31d]";

    private static ResourceLocation id(String path) {
        return ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path);
    }

    private static Runnable passed(String test) {
        return () -> LOGGER.info("{} {} passed", TAG, test);
    }

    // ---------------------------------------------------------------- helpers

    /** A NeoForge FakePlayer that remembers the menus the world asked it to open (the real openMenu needs a client). */
    private static final class TestPlayer extends FakePlayer {
        final List<MenuProvider> opened = new ArrayList<>();

        TestPlayer(ServerLevel level) {
            super(level, new GameProfile(UUID.randomUUID(), "sorter-test"));
        }

        @Override
        public OptionalInt openMenu(@Nullable MenuProvider menu, @Nullable Consumer<RegistryFriendlyByteBuf> extraDataWriter) {
            if(menu != null) this.opened.add(menu);
            return OptionalInt.empty();
        }
    }

    private static TestPlayer player(GameTestHelper helper, GameType mode, float yaw) {
        TestPlayer p = new TestPlayer(helper.getLevel());
        p.setGameMode(mode);
        Vec3 a = helper.absoluteVec(new Vec3(8.5, 1, 8.5));
        p.moveTo(a.x, a.y, a.z, yaw, 0F);
        p.getInventory().selected = 0;
        return p;
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

    private static int total(Container c, int from, int to) {
        int n = 0;
        for(int i = from; i < to; i++) n += c.getItem(i).getCount();
        return n;
    }

    private static int total(Container c) {
        return total(c, 0, c.getContainerSize());
    }

    private static Container chest(GameTestHelper helper, BlockPos rel) {
        helper.setBlock(rel, Blocks.CHEST.defaultBlockState());
        Container c = (Container) helper.getBlockEntity(rel);
        c.clearContent();
        return c;
    }

    private static BlockState beltState(Direction input) {
        return NtmBlocks.CONVEYOR.get().defaultBlockState().setValue(ConveyorBaseBlock.HORIZONTAL_FACING, input).setValue(ConveyorBlock.SHAPE, Shape.STRAIGHT);
    }

    private static BlockState crane(Block block, Direction input, Direction output) {
        return block.defaultBlockState().setValue(CraneBaseBlock.INPUT, input).setValue(CraneBaseBlock.OUTPUT, output);
    }

    private static <T extends BlockEntity> T placeCrane(GameTestHelper helper, BlockPos rel, Block block, Direction input, Direction output, Class<T> type) {
        helper.setBlock(rel, crane(block, input, output));
        return SmokeTestSupport.blockEntity(helper, rel, type);
    }

    /** A machine's core block alone (a DummyableBlock's default state is its core): enough for the block entity paths, no dummies. */
    private static <T extends BlockEntity> T core(GameTestHelper helper, BlockPos rel, Block block, Class<T> type) {
        helper.setBlock(rel, block.defaultBlockState());
        return SmokeTestSupport.blockEntity(helper, rel, type);
    }

    private static MovingItem detached(ServerLevel level, ItemStack stack) {
        MovingItem e = new MovingItem(NtmEntityTypes.MOVING_ITEM.get(), level);
        e.setItemStack(stack);
        return e;
    }

    private static MovingPackage detachedPackage(ServerLevel level, ItemStack... stacks) {
        MovingPackage e = new MovingPackage(NtmEntityTypes.MOVING_PACKAGE.get(), level);
        e.setItemStacks(stacks);
        return e;
    }

    private static MovingItem movingAt(ServerLevel level, Vec3 at, ItemStack stack) {
        MovingItem e = new MovingItem(NtmEntityTypes.MOVING_ITEM.get(), level);
        e.setPos(at.x, at.y, at.z);
        e.setItemStack(stack);
        level.addFreshEntity(e);
        return e;
    }

    private static List<MovingItem> movingIn(GameTestHelper helper, BlockPos cellRel) {
        return helper.getLevel().getEntitiesOfClass(MovingItem.class, new AABB(helper.absolutePos(cellRel)));
    }

    private static List<MovingPackage> packagesIn(GameTestHelper helper, BlockPos cellRel) {
        return helper.getLevel().getEntitiesOfClass(MovingPackage.class, new AABB(helper.absolutePos(cellRel)));
    }

    private static int remaining(List<MovingItem> items) {
        int n = 0;
        for(MovingItem e : items) if(!e.isRemoved()) n += e.getItemStack().getCount();
        return n;
    }

    private static <T extends Entity> List<T> near(ServerLevel level, Class<T> type, Vec3 at, double radius) {
        return level.getEntitiesOfClass(type, new AABB(at, at).inflate(radius));
    }

    private static int itemsNear(ServerLevel level, Vec3 at, double radius, Item item) {
        int n = 0;
        for(ItemEntity e : near(level, ItemEntity.class, at, radius)) if(e.getItem().is(item)) n += e.getItem().getCount();
        return n;
    }

    private static int dropped(GameTestHelper helper, Item item) {
        int n = 0;
        for(ItemEntity e : helper.getLevel().getEntitiesOfClass(ItemEntity.class, helper.getBounds().inflate(2))) if(e.getItem().is(item)) n += e.getItem().getCount();
        return n;
    }

    /** Every entity of the three kinds a belt line produces in a box around the cell, for "nothing came out" checks. */
    private static int anyEntities(GameTestHelper helper, BlockPos cellRel, double radius) {
        AABB box = new AABB(helper.absolutePos(cellRel)).inflate(radius);
        ServerLevel level = helper.getLevel();
        return level.getEntitiesOfClass(ItemEntity.class, box).size() + level.getEntitiesOfClass(MovingItem.class, box).size() + level.getEntitiesOfClass(MovingPackage.class, box).size();
    }

    private static void clearEntities(GameTestHelper helper) {
        AABB box = helper.getBounds().inflate(2);
        for(ItemEntity e : helper.getLevel().getEntitiesOfClass(ItemEntity.class, box)) e.discard();
        for(MovingItem e : helper.getLevel().getEntitiesOfClass(MovingItem.class, box)) e.discard();
        for(MovingPackage e : helper.getLevel().getEntitiesOfClass(MovingPackage.class, box)) e.discard();
    }

    private static InteractionResult useOn(ServerLevel level, Player player, ItemStack stack, BlockPos abs, Direction face) {
        player.setItemInHand(InteractionHand.MAIN_HAND, stack);
        return stack.getItem().useOn(new UseOnContext(level, player, InteractionHand.MAIN_HAND, stack, new BlockHitResult(Vec3.atCenterOf(abs), face, abs, false)));
    }

    /** The real server-side right-click: onItemUseFirst, then the block, then the item's useOn. */
    private static InteractionResult use(ServerLevel level, TestPlayer p, ItemStack stack, BlockPos abs) {
        p.setItemInHand(InteractionHand.MAIN_HAND, stack);
        return p.gameMode.useItemOn(p, level, stack, InteractionHand.MAIN_HAND, new BlockHitResult(Vec3.atCenterOf(abs), Direction.UP, abs, false));
    }

    private static InteractionResult sneakUse(ServerLevel level, TestPlayer p, ItemStack stack, BlockPos abs) {
        p.setShiftKeyDown(true);
        try {
            return use(level, p, stack, abs);
        } finally {
            p.setShiftKeyDown(false);
        }
    }

    private static CompoundTag key(String name, int value) {
        CompoundTag tag = new CompoundTag();
        tag.putInt(name, value);
        return tag;
    }

    private static int invTotal(Player p) {
        int n = 0;
        for(ItemStack st : p.getInventory().items) n += st.getCount();
        for(ItemStack st : p.getInventory().offhand) n += st.getCount();
        return n;
    }

    private static boolean near(Vec3 a, Vec3 b, double eps) {
        return Math.abs(a.x - b.x) <= eps && Math.abs(a.y - b.y) <= eps && Math.abs(a.z - b.z) <= eps;
    }

    private static String fmt(Vec3 v) {
        return "(" + v.x + ", " + v.y + ", " + v.z + ")";
    }

    private static String describe(ItemStack[] stacks) {
        List<String> out = new ArrayList<>();
        for(ItemStack st : stacks) out.add(st.getCount() + "x" + st.getItem());
        return out.toString();
    }

    private static IItemHandler handler(ServerLevel level, BlockPos abs, @Nullable Direction side) {
        return level.getCapability(Capabilities.ItemHandler.BLOCK, abs, side);
    }

    private static ItemStack wand() {
        return MetaHelper.newStack(NtmItems.CONVEYOR_WAND.get(), 1, ConveyorType.REGULAR);
    }

    private static ItemStack pneumatic() {
        return MetaHelper.newStack(NtmItems.PART_GENERIC.get(), 1, PartGenericItem.Type.PISTON_PNEUMATIC);
    }

    private static ItemStack screwdriver() {
        return s(NtmItems.SCREWDRIVER.get(), 1);
    }

    private static ItemStack tool() {
        return s(NtmItems.SETTINGS_TOOL.get(), 1);
    }

    private static ItemStack toolWith(CompoundTag data) {
        ItemStack t = tool();
        TagsUtil.putCustomData(t, data);
        return t;
    }

    private static CompoundTag toolData(ItemStack tool) {
        return TagsUtil.getCustomData(tool);
    }

    private static void setIndex(ItemStack tool, int index) {
        CompoundTag d = TagsUtil.getCustomData(tool);
        d.putInt("copyIndex", index);
        TagsUtil.putCustomData(tool, d);
    }

    private static CompoundTag fluidData(int... ids) {
        CompoundTag d = new CompoundTag();
        d.putIntArray("FluidID", ids);
        return d;
    }

    private static CompoundTag saved(HolderLookup.Provider reg, ItemStack stack) {
        return (CompoundTag) stack.save(reg);
    }

    /** Runs the task and reports which case threw: the settings data is player-writable and no case may throw. */
    private static void noThrow(String ctx, Runnable task) {
        try {
            task.run();
        } catch(RuntimeException e) {
            throw new net.minecraft.gametest.framework.GameTestAssertException(ctx + " threw " + e);
        }
    }

    private static Block routerBlock() {
        return NtmBlocks.CRANE_ROUTER.get();
    }

    private static CraneSplitterBlock splitterBlock() {
        return (CraneSplitterBlock) NtmBlocks.CRANE_SPLITTER.get();
    }

    private static CranePartitionerBlock partitionerBlock() {
        return (CranePartitionerBlock) NtmBlocks.CRANE_PARTITIONER.get();
    }

    private static CraneRouterBlockEntity router(GameTestHelper helper, BlockPos rel) {
        helper.setBlock(rel, routerBlock().defaultBlockState());
        return SmokeTestSupport.blockEntity(helper, rel, CraneRouterBlockEntity.class);
    }

    private static void setFilter(CraneRouterBlockEntity r, int slot, ItemStack stack, @Nullable String mode) {
        r.setItem(slot, stack.copyWithCount(1));
        r.patterns[slot / 5].modes[slot % 5] = mode;
    }

    private static void resetRouter(CraneRouterBlockEntity r) {
        for(int i = 0; i < 30; i++) r.setItem(i, ItemStack.EMPTY);
        Arrays.fill(r.modes, CraneRouterBlockEntity.MODE_NONE);
        for(var p : r.patterns) Arrays.fill(p.modes, null);
    }

    /** The result of getOutputDir over many trials; null (nowhere to go) is a member of the set too. */
    private static Set<Direction> sample(CraneRouterBlockEntity r, ItemStack stack, int trials) {
        Set<Direction> seen = new HashSet<>();
        for(int i = 0; i < trials; i++) seen.add(CraneRouterBlock.getOutputDir(r, stack.copy()));
        return seen;
    }

    // ================================================================ 1. the sorter

    // CraneRouter.java:212-261 (getOutputDir): the side numbers, whitelist and blacklist per side with any of the five filter slots matching, a blacklist side with an empty filter always valid,
    // sides in mode off ignored, the wildcard sides used only when no whitelist / blacklist side is valid, nothing valid -> UNKNOWN
    @GameTest(template = TEMPLATE, batch = "hbm31d_router_select", timeoutTicks = 200)
    public static void router_select(GameTestHelper helper) {
        guard(() -> {
            CraneRouterBlockEntity r = router(helper, new BlockPos(8, 2, 8));
            ItemStack dirt = s(Items.DIRT, 1);
            ItemStack stone = s(Items.STONE, 1);
            check(Direction.from3DDataValue(0) == Direction.DOWN && Direction.from3DDataValue(1) == Direction.UP && Direction.from3DDataValue(2) == Direction.NORTH
                    && Direction.from3DDataValue(3) == Direction.SOUTH && Direction.from3DDataValue(4) == Direction.WEST && Direction.from3DDataValue(5) == Direction.EAST,
                    "the side numbering differs from ForgeDirection (down, up, north, south, west, east; :25-33)");

            // a whitelist side: any one of its five filter slots matching makes it valid, and only that side
            for(int side = 0; side < 6; side++) {
                Direction d = Direction.from3DDataValue(side);
                for(int k = 0; k < 5; k++) {
                    resetRouter(r);
                    r.modes[side] = CraneRouterBlockEntity.MODE_WHITELIST;
                    setFilter(r, side * 5 + k, dirt, "exact");
                    check(CraneRouterBlock.getOutputDir(r, dirt.copy()) == d, "whitelist side " + side + " slot " + k + ": dirt went " + CraneRouterBlock.getOutputDir(r, dirt.copy()) + ", expected " + d);
                    check(CraneRouterBlock.getOutputDir(r, stone.copy()) == null, "whitelist side " + side + " slot " + k + ": stone went " + CraneRouterBlock.getOutputDir(r, stone.copy()) + ", expected nowhere");
                }
            }

            // a blacklist side: valid when no filter slot matches
            for(int side = 0; side < 6; side++) {
                Direction d = Direction.from3DDataValue(side);
                for(int k = 0; k < 5; k++) {
                    resetRouter(r);
                    r.modes[side] = CraneRouterBlockEntity.MODE_BLACKLIST;
                    setFilter(r, side * 5 + k, dirt, "exact");
                    check(CraneRouterBlock.getOutputDir(r, dirt.copy()) == null, "blacklist side " + side + " slot " + k + ": dirt went " + CraneRouterBlock.getOutputDir(r, dirt.copy()) + ", expected nowhere");
                    check(CraneRouterBlock.getOutputDir(r, stone.copy()) == d, "blacklist side " + side + " slot " + k + ": stone went " + CraneRouterBlock.getOutputDir(r, stone.copy()) + ", expected " + d);
                }
                // an empty blacklist filter is always valid, for anything
                resetRouter(r);
                r.modes[side] = CraneRouterBlockEntity.MODE_BLACKLIST;
                for(ItemStack any : new ItemStack[] { dirt, stone, s(Items.DIAMOND, 7), pneumatic() }) {
                    check(CraneRouterBlock.getOutputDir(r, any.copy()) == d, "an empty blacklist on side " + side + " sent " + any + " " + CraneRouterBlock.getOutputDir(r, any.copy()) + ", expected " + d);
                }
            }

            // a whitelist side with an empty filter matches nothing; a side in mode off is ignored even with a matching filter
            resetRouter(r);
            r.modes[2] = CraneRouterBlockEntity.MODE_WHITELIST;
            check(CraneRouterBlock.getOutputDir(r, dirt.copy()) == null, "an empty whitelist sent dirt " + CraneRouterBlock.getOutputDir(r, dirt.copy()));
            resetRouter(r);
            setFilter(r, 10, dirt, "exact");
            check(CraneRouterBlock.getOutputDir(r, dirt.copy()) == null, "a side in mode off took dirt: " + CraneRouterBlock.getOutputDir(r, dirt.copy()));

            // wildcard sides: only when no whitelist / blacklist side is valid (:240-246)
            resetRouter(r);
            r.modes[4] = CraneRouterBlockEntity.MODE_WILDCARD;
            r.modes[2] = CraneRouterBlockEntity.MODE_WHITELIST;
            setFilter(r, 10, dirt, "exact");
            check(CraneRouterBlock.getOutputDir(r, stone.copy()) == Direction.WEST, "stone with no valid filter side went " + CraneRouterBlock.getOutputDir(r, stone.copy()) + ", expected the wildcard side west");
            check(CraneRouterBlock.getOutputDir(r, dirt.copy()) == Direction.NORTH, "dirt, valid on the whitelist side, went " + CraneRouterBlock.getOutputDir(r, dirt.copy()) + ", expected north (wildcards are only the fallback)");
            // two wildcard sides share the stack, and nothing else is ever chosen
            r.modes[1] = CraneRouterBlockEntity.MODE_WILDCARD;
            Set<Direction> wild = sample(r, stone, 150);
            check(wild.equals(Set.of(Direction.UP, Direction.WEST)), "two wildcard sides gave " + wild + " over 150 trials, expected exactly {up, west}");
            // no wildcard, no valid side
            resetRouter(r);
            r.modes[2] = CraneRouterBlockEntity.MODE_WHITELIST;
            setFilter(r, 10, dirt, "exact");
            check(CraneRouterBlock.getOutputDir(r, stone.copy()) == null, "stone went " + CraneRouterBlock.getOutputDir(r, stone.copy()) + " with nothing valid and no wildcard");

            // several valid sides: always one of them, and over 150 trials every valid side shows up (:253-259, the world random)
            resetRouter(r);
            r.modes[0] = CraneRouterBlockEntity.MODE_BLACKLIST;
            r.modes[2] = CraneRouterBlockEntity.MODE_BLACKLIST;
            r.modes[5] = CraneRouterBlockEntity.MODE_WHITELIST;
            setFilter(r, 25, stone, "wildcard");
            Set<Direction> valid = Set.of(Direction.DOWN, Direction.NORTH, Direction.EAST);
            Set<Direction> seen = sample(r, stone, 150);
            check(seen.equals(valid), "three valid sides gave " + seen + " over 150 trials, expected exactly " + valid);
            Set<Direction> two = sample(r, dirt, 150);
            check(two.equals(Set.of(Direction.DOWN, Direction.NORTH)), "dirt (not on the whitelist) gave " + two + ", expected {down, north}");

            // the match modes of one filter slot (ModulePatternMatcher.java:133-151): exact compares the type (meta), wildcard the item, a tag the tag
            resetRouter(r);
            r.modes[3] = CraneRouterBlockEntity.MODE_WHITELIST;
            ItemStack hydraulic = MetaHelper.newStack(NtmItems.PART_GENERIC.get(), 1, PartGenericItem.Type.PISTON_HYDRAULIC);
            setFilter(r, 15, pneumatic(), "exact");
            check(CraneRouterBlock.getOutputDir(r, pneumatic()) == Direction.SOUTH && CraneRouterBlock.getOutputDir(r, hydraulic.copy()) == null, "exact mode: pneumatic " + CraneRouterBlock.getOutputDir(r, pneumatic()) + ", hydraulic " + CraneRouterBlock.getOutputDir(r, hydraulic.copy()));
            r.patterns[3].modes[0] = "wildcard";
            check(CraneRouterBlock.getOutputDir(r, hydraulic.copy()) == Direction.SOUTH, "wildcard mode did not take the other type of the same item");
            check(CraneRouterBlock.getOutputDir(r, dirt.copy()) == null, "wildcard mode took another item");
            setFilter(r, 15, s(Items.IRON_INGOT, 1), "c:ingots/iron");
            check(CraneRouterBlock.getOutputDir(r, s(Items.IRON_INGOT, 1)) == Direction.SOUTH && CraneRouterBlock.getOutputDir(r, s(Items.GOLD_INGOT, 1)) == null && CraneRouterBlock.getOutputDir(r, s(Items.COPPER_INGOT, 1)) == null,
                    "a c:ingots/iron filter did not take exactly iron ingots");
            r.patterns[3].modes[0] = "c:ingots";
            check(CraneRouterBlock.getOutputDir(r, s(Items.GOLD_INGOT, 1)) == Direction.SOUTH, "a c:ingots filter did not take gold ingots");
        }).run();
        passed("router_select").run();
        helper.succeed();
    }

    // CraneRouter.java:63-76: the conveyor wand goes to the item, sneaking opens nothing, every other item, the screwdriver included, opens the screen
    @GameTest(template = TEMPLATE, batch = "hbm31d_router_use", timeoutTicks = 100)
    public static void router_use(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos rel = new BlockPos(8, 2, 5);
            router(helper, rel);
            BlockPos abs = helper.absolutePos(rel);

            TestPlayer p = player(helper, GameType.SURVIVAL, 0F);
            use(level, p, wand(), abs);
            check(p.opened.isEmpty(), "the conveyor wand opened the screen");
            p.setShiftKeyDown(true);
            use(level, p, ItemStack.EMPTY, abs);
            check(p.opened.isEmpty(), "sneaking with an empty hand opened the screen");
            use(level, p, screwdriver(), abs);
            check(p.opened.isEmpty(), "sneaking with a screwdriver opened the screen");
            use(level, p, wand(), abs);
            check(p.opened.isEmpty(), "sneaking with the conveyor wand opened the screen");
            p.setShiftKeyDown(false);

            use(level, p, ItemStack.EMPTY, abs);
            check(p.opened.size() == 1, "an empty hand requested " + p.opened.size() + " menus, expected 1");
            AbstractContainerMenu menu = p.opened.get(0).createMenu(1, p.getInventory(), p);
            check(menu instanceof CraneRouterMenu, "the opened menu is " + menu);

            TestPlayer q = player(helper, GameType.SURVIVAL, 0F);
            use(level, q, screwdriver(), abs);
            check(q.opened.size() == 1, "the screwdriver requested " + q.opened.size() + " menus, expected 1 (:64-76 the screwdriver opens it)");
            TestPlayer c = player(helper, GameType.CREATIVE, 0F);
            use(level, c, s(Items.STICK, 1), abs);
            check(c.opened.size() == 1, "an ordinary item requested " + c.opened.size() + " menus, expected 1");
        }).run();
        passed("router_use").run();
        helper.succeed();
    }

    // CraneRouter.java:119-157: an item entering from any side (a diagonal step included) leaves 0.55 blocks out of the picked side; onto the belt there as a moving item when that side is a belt,
    // as an item entity at the same point when it is not, in the block's centre when no side takes it; the stack is the entered stack
    @GameTest(template = TEMPLATE, batch = "hbm31d_router_exit", timeoutTicks = 100)
    public static void router_exit(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos rel = new BlockPos(8, 2, 8);
            CraneRouterBlockEntity r = router(helper, rel);
            BlockPos abs = helper.absolutePos(rel);
            CraneRouterBlock block = (CraneRouterBlock) routerBlock();
            helper.setBlock(new BlockPos(8, 2, 7), beltState(Direction.SOUTH));
            helper.setBlock(new BlockPos(8, 3, 8), beltState(Direction.EAST));

            check(block.canItemEnter(level, abs, null, detached(level, s(Items.DIRT, 1))) && block.canPackageEnter(level, abs, null, detachedPackage(level, s(Items.DIRT, 1))), "the sorter refuses a diagonal entry");
            for(Direction d : Direction.values()) {
                check(block.canItemEnter(level, abs, d, detached(level, s(Items.DIRT, 1))) && block.canPackageEnter(level, abs, d, detachedPackage(level, s(Items.DIRT, 1))), "the sorter refuses an entry from " + d + " (:119-120)");
            }

            // north is a belt: the stack becomes one moving item on it
            r.modes[2] = CraneRouterBlockEntity.MODE_WHITELIST;
            setFilter(r, 10, s(Items.DIRT, 1), "exact");
            ItemStack in = s(Items.DIRT, 5);
            block.onItemEnter(level, abs, Direction.WEST, detached(level, in));
            List<MovingItem> onBelt = movingIn(helper, new BlockPos(8, 2, 7));
            check(onBelt.size() == 1 && remaining(onBelt) == 5 && onBelt.get(0).getItemStack().is(Items.DIRT), "the belt north of the sorter holds " + onBelt.size() + " moving items with " + remaining(onBelt) + " dirt, expected one with 5");
            check(itemsNear(level, Vec3.atCenterOf(abs).add(0, 0, -0.55), 0.4, Items.DIRT) == 0 && itemsNear(level, Vec3.atCenterOf(abs), 0.3, Items.DIRT) == 0, "an item entity was dropped as well as the moving item");
            check(onBelt.get(0).getY() > abs.getY() - 0.01 && onBelt.get(0).getY() < abs.getY() + 1, "the moving item is at height " + onBelt.get(0).getY());
            onBelt.get(0).discard();

            // east has no belt: an item entity 0.55 blocks out of the centre
            r.modes[5] = CraneRouterBlockEntity.MODE_WHITELIST;
            setFilter(r, 25, s(Items.STONE, 1), "wildcard");
            block.onItemEnter(level, abs, null, detached(level, s(Items.STONE, 3)));
            Vec3 east = Vec3.atCenterOf(abs).add(0.55, 0, 0);
            check(itemsNear(level, east, 0.3, Items.STONE) == 3, "no stack of 3 stone lies 0.55 blocks east of the centre (" + itemsNear(level, east, 0.3, Items.STONE) + " found)");
            check(near(level, MovingItem.class, east, 0.6).isEmpty(), "a moving item appeared where there is no belt");

            // up is a belt (an upward neighbour): it takes the item as well
            r.modes[1] = CraneRouterBlockEntity.MODE_WHITELIST;
            setFilter(r, 5, s(Items.SAND, 1), "exact");
            block.onItemEnter(level, abs, Direction.UP, detached(level, s(Items.SAND, 2)));
            check(remaining(movingIn(helper, new BlockPos(8, 3, 8))) == 2, "the belt above holds " + remaining(movingIn(helper, new BlockPos(8, 3, 8))) + " sand, expected 2");

            // nowhere to go: dropped in the block's centre
            block.onItemEnter(level, abs, Direction.SOUTH, detached(level, s(Items.GRAVEL, 4)));
            check(itemsNear(level, Vec3.atCenterOf(abs), 0.3, Items.GRAVEL) == 4, "unsortable gravel did not drop in the centre (" + itemsNear(level, Vec3.atCenterOf(abs), 0.3, Items.GRAVEL) + " found)");

            // an entered stack is not shared with the entity it came from
            ItemStack source = s(Items.DIRT, 9);
            block.onItemEnter(level, abs, Direction.WEST, detached(level, source));
            check(source.getCount() == 9, "the entering stack was changed to " + source);
            clearEntities(helper);
        }).run();
        passed("router_exit").run();
        helper.succeed();
    }

    // CraneRouter.java:159-188 and sort (:198-210): every stack of a package is sorted by itself, the stacks of one side go as one new package onto the belt there, one by one as item entities
    // when it is no belt, unsortable ones drop in the centre; empty places are skipped (:204) and make neither an empty item nor an empty package
    @GameTest(template = TEMPLATE, batch = "hbm31d_router_package", timeoutTicks = 100)
    public static void router_package(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos rel = new BlockPos(8, 2, 8);
            CraneRouterBlockEntity r = router(helper, rel);
            BlockPos abs = helper.absolutePos(rel);
            CraneRouterBlock block = (CraneRouterBlock) routerBlock();
            helper.setBlock(new BlockPos(8, 2, 7), beltState(Direction.SOUTH));
            helper.setBlock(new BlockPos(8, 2, 9), beltState(Direction.NORTH));
            r.modes[2] = CraneRouterBlockEntity.MODE_WHITELIST;
            setFilter(r, 10, s(Items.STONE, 1), "exact");
            setFilter(r, 11, s(Items.DIRT, 1), "exact");
            r.modes[3] = CraneRouterBlockEntity.MODE_WHITELIST;
            setFilter(r, 15, s(Items.SAND, 1), "exact");
            r.modes[5] = CraneRouterBlockEntity.MODE_WHITELIST;
            setFilter(r, 25, s(Items.GRAVEL, 1), "exact");

            block.onPackageEnter(level, abs, Direction.WEST, detachedPackage(level, s(Items.STONE, 3), ItemStack.EMPTY, s(Items.DIRT, 2), s(Items.SAND, 4), s(Items.GRAVEL, 5), s(Items.COAL, 6), ItemStack.EMPTY));
            List<MovingPackage> north = packagesIn(helper, new BlockPos(8, 2, 7));
            List<MovingPackage> south = packagesIn(helper, new BlockPos(8, 2, 9));
            check(north.size() == 1, "the north belt holds " + north.size() + " packages, expected 1");
            check(south.size() == 1, "the south belt holds " + south.size() + " packages, expected 1");
            ItemStack[] n = north.get(0).getItemStacks();
            ItemStack[] so = south.get(0).getItemStacks();
            check(n.length == 2 && n[0].is(Items.STONE) && n[0].getCount() == 3 && n[1].is(Items.DIRT) && n[1].getCount() == 2, "the north package holds " + describe(n) + ", expected [3 stone, 2 dirt] without empty places");
            check(so.length == 1 && so[0].is(Items.SAND) && so[0].getCount() == 4, "the south package holds " + describe(so) + ", expected [4 sand]");
            check(level.getEntitiesOfClass(MovingPackage.class, new AABB(abs).inflate(3)).size() == 2, "the sorter made " + level.getEntitiesOfClass(MovingPackage.class, new AABB(abs).inflate(3)).size() + " packages, expected 2");
            check(itemsNear(level, Vec3.atCenterOf(abs).add(0.55, 0, 0), 0.3, Items.GRAVEL) == 5, "gravel on the side without a belt did not drop as an item entity");
            check(itemsNear(level, Vec3.atCenterOf(abs), 0.3, Items.COAL) == 6, "the unsortable coal did not drop in the centre");
            for(ItemEntity e : level.getEntitiesOfClass(ItemEntity.class, new AABB(abs).inflate(3))) check(!e.getItem().isEmpty(), "an empty item entity was dropped");
            clearEntities(helper);

            // a package of empty places only produces nothing at all
            block.onPackageEnter(level, abs, Direction.WEST, detachedPackage(level, ItemStack.EMPTY, ItemStack.EMPTY, ItemStack.EMPTY));
            check(anyEntities(helper, rel, 3) == 0, "a package of empty places produced " + anyEntities(helper, rel, 3) + " entities");

            // a package whose stacks fall on the side without a belt drops stack by stack
            r.modes[2] = CraneRouterBlockEntity.MODE_NONE;
            block.onPackageEnter(level, abs, Direction.WEST, detachedPackage(level, s(Items.GRAVEL, 2), s(Items.GRAVEL, 3)));
            check(itemsNear(level, Vec3.atCenterOf(abs).add(0.55, 0, 0), 0.3, Items.GRAVEL) == 5 && level.getEntitiesOfClass(MovingPackage.class, new AABB(abs).inflate(3)).isEmpty(), "two gravel stacks to a side without a belt did not drop as items");
            clearEntities(helper);
        }).run();
        passed("router_package").run();
        helper.succeed();
    }

    // ContainerCraneRouter.java:19-63 and :31-58: 30 phantom slots, sides 0-2 in the left column and 3-5 in the right, the player inventory at (47, 119) and (47, 177); a click puts one copy in and keeps the
    // cursor, an empty cursor clears, a right click on a filled slot cycles the mode, shift clicks move nothing; the mode of a new filter comes from initPatternSmart (ModulePatternMatcher.java:30-66)
    @GameTest(template = TEMPLATE, batch = "hbm31d_router_filter_menu", timeoutTicks = 200)
    public static void router_filter_menu(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos rel = new BlockPos(8, 2, 5);
            CraneRouterBlockEntity r = router(helper, rel);
            BlockPos abs = helper.absolutePos(rel);
            TestPlayer p = player(helper, GameType.SURVIVAL, 0F);
            use(level, p, ItemStack.EMPTY, abs);
            check(p.opened.size() == 1, "no menu was requested");
            AbstractContainerMenu menu = p.opened.get(0).createMenu(1, p.getInventory(), p);
            check(menu.slots.size() == 30 + 36, "the sorter menu has " + menu.slots.size() + " slots, expected 30 + 36 (:19-35)");

            for(int j = 0; j < 2; j++) for(int i = 0; i < 3; i++) for(int k = 0; k < 5; k++) {
                int index = k + j * 15 + i * 5;
                Slot slot = menu.getSlot(index);
                check(slot.x == 34 + k * 18 + j * 98 && slot.y == 17 + i * 26, "filter slot " + index + " stands at (" + slot.x + ", " + slot.y + "), expected (" + (34 + k * 18 + j * 98) + ", " + (17 + i * 26) + ")");
                check(slot.container == r && slot.getContainerSlot() == index, "menu slot " + index + " is container slot " + slot.getContainerSlot());
                check(!slot.mayPlace(s(Items.DIRT, 1)) && !slot.mayPickup(p) && slot.getMaxStackSize() == 1, "filter slot " + index + " is not a phantom slot");
            }
            for(int i = 0; i < 3; i++) for(int j = 0; j < 9; j++) check(menu.getSlot(30 + j + i * 9).x == 47 + j * 18 && menu.getSlot(30 + j + i * 9).y == 119 + i * 18, "player slot " + (30 + j + i * 9) + " is misplaced");
            for(int i = 0; i < 9; i++) check(menu.getSlot(57 + i).x == 47 + i * 18 && menu.getSlot(57 + i).y == 177, "hotbar slot " + (57 + i) + " is misplaced");

            // the mode of a filter put in by a click
            int before = invTotal(p);
            Object[][] cases = {
                    { s(Items.IRON_INGOT, 5), "c:ingots/iron" },
                    { s(Items.GOLD_INGOT, 5), "c:ingots/gold" },
                    { s(Items.IRON_BLOCK, 5), "c:storage_blocks/iron" },
                    { s(Items.IRON_NUGGET, 5), "c:nuggets/iron" },
                    { s(Items.REDSTONE, 5), "c:dusts/redstone" },
                    { s(Items.STONE, 5), "wildcard" },
                    { pneumatic().copyWithCount(5), "exact" } };
            for(Object[] c : cases) {
                ItemStack carried = (ItemStack) c[0];
                menu.setCarried(carried.copy());
                menu.clicked(12, 0, ClickType.PICKUP, p);
                String expected = (String) c[1];
                check(r.getItem(12).is(carried.getItem()) && r.getItem(12).getCount() == 1, "slot 12 holds " + r.getItem(12) + " after clicking with " + carried);
                check(menu.getCarried().getCount() == 5, "the cursor holds " + menu.getCarried() + " after the click, expected the stack of 5 kept");
                check(expected.equals(r.patterns[2].modes[2]), carried.getItem() + " got the mode " + r.patterns[2].modes[2] + ", expected " + expected + " (:56 initPatternSmart)");
                r.setItem(12, ItemStack.EMPTY);
                r.patterns[2].modes[2] = null;
            }
            check(invTotal(p) == before, "the player inventory changed");

            // each of the 30 slots maps to side n / 5, filter n % 5
            menu.setCarried(s(Items.DIAMOND, 1));
            for(int slot = 0; slot < 30; slot++) {
                menu.clicked(slot, 0, ClickType.PICKUP, p);
                check(r.getItem(slot).is(Items.DIAMOND) && "wildcard".equals(r.patterns[slot / 5].modes[slot % 5]), "slot " + slot + " did not become the filter " + (slot % 5) + " of side " + (slot / 5));
            }
            for(int slot = 0; slot < 30; slot++) {
                menu.clicked(slot, 0, ClickType.QUICK_MOVE, p);
                check(r.getItem(slot).is(Items.DIAMOND), "a shift-click type click changed filter slot " + slot);
            }

            // a right click on a filled slot cycles the mode and keeps the item; exact -> wildcard on an item with subtypes
            menu.setCarried(ItemStack.EMPTY);
            r.setItem(3, pneumatic());
            r.patterns[0].modes[3] = "exact";
            menu.clicked(3, 1, ClickType.PICKUP, p);
            check(r.getItem(3).is(NtmItems.PART_GENERIC.get()) && "wildcard".equals(r.patterns[0].modes[3]), "a right click gave " + r.getItem(3) + " mode " + r.patterns[0].modes[3] + ", expected exact -> wildcard (:49-51)");
            menu.clicked(3, 1, ClickType.PICKUP, p);
            check("exact".equals(r.patterns[0].modes[3]), "a second right click on an item without tags left the mode " + r.patterns[0].modes[3] + ", expected the cycle back to exact (ModulePatternMatcher.java:86-130)");

            // an empty cursor clears the slot and its mode
            menu.clicked(3, 0, ClickType.PICKUP, p);
            check(r.getItem(3).isEmpty() && r.patterns[0].modes[3] == null, "an empty cursor left " + r.getItem(3) + " mode " + r.patterns[0].modes[3]);
            check(menu.getCarried().isEmpty() && invTotal(p) == before, "an item came out of a phantom slot");

            // shift clicks move nothing in either direction (:60-63)
            p.getInventory().setItem(9, s(Items.STONE, 10));
            check(menu.quickMoveStack(p, 5).isEmpty() && menu.quickMoveStack(p, 30).isEmpty(), "a shift click returned a stack");
            check(p.getInventory().getItem(9).getCount() == 10 && r.getItem(0).is(Items.DIAMOND), "a shift click moved items");
            for(int slot = 0; slot < 30; slot++) check(!r.getItem(slot).is(Items.STONE), "stone reached filter slot " + slot);
        }).run();
        passed("router_filter_menu").run();
        helper.succeed();
    }

    // TileEntityCraneRouter.java:125-143 (distance < 20 from the block corner, "toggle" cycles a side 0 -> 1 -> 2 -> 3 -> 0, "slot" fills a filter) with the validation GOAL31 decision 4 adds:
    // a side outside 0-5 and a slot payload that does not describe a slot 0-29 and an item are dropped
    @GameTest(template = TEMPLATE, batch = "hbm31d_router_control", timeoutTicks = 200)
    public static void router_control(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos rel = new BlockPos(8, 2, 5);
            CraneRouterBlockEntity r = router(helper, rel);
            BlockPos abs = helper.absolutePos(rel);
            TestPlayer p = player(helper, GameType.SURVIVAL, 0F);

            for(int side = 0; side < 6; side++) {
                int[] expected = { 1, 2, 3, 0, 1 };
                for(int step = 0; step < expected.length; step++) {
                    CompoundTagControl.apply(p, key("toggle", side), abs);
                    check(r.modes[side] == expected[step], "toggle " + side + " step " + step + " gave " + r.modes[side] + ", expected " + expected[step] + " (:136-141)");
                }
                for(int other = 0; other < 6; other++) if(other != side) check(r.modes[other] == (other < side ? 1 : 0), "toggle " + side + " changed side " + other + " to " + r.modes[other]);
            }
            int[] modes = r.modes.clone();
            for(int bad : new int[] { -1, 6, 7, 100, Integer.MIN_VALUE, Integer.MAX_VALUE }) {
                noThrow("toggle " + bad, () -> CompoundTagControl.apply(p, key("toggle", bad), abs));
                check(Arrays.equals(r.modes, modes), "toggle " + bad + " changed the modes to " + Arrays.toString(r.modes));
            }
            CompoundTag text = new CompoundTag();
            text.putString("toggle", "2");
            noThrow("toggle as text", () -> CompoundTagControl.apply(p, text, abs));
            check(Arrays.equals(r.modes, modes), "a text toggle changed the modes to " + Arrays.toString(r.modes));

            // the filter payload
            Arrays.fill(r.modes, 0);
            CompoundTag good = new CompoundTag();
            good.putInt("slot", 13);
            good.put("stack", saved(level.registryAccess(), s(Items.DIRT, 1)));
            CompoundTagControl.apply(p, good, abs);
            check(r.getItem(13).is(Items.DIRT) && r.getItem(13).getCount() == 1 && "exact".equals(r.patterns[2].modes[3]), "a slot payload gave " + r.getItem(13) + " mode " + r.patterns[2].modes[3] + ", expected one dirt in mode exact (IControlReceiverFilter.java:29-41)");
            for(int i = 0; i < 30; i++) if(i != 13) check(r.getItem(i).isEmpty(), "the payload filled slot " + i);
            ItemStack stackTag = s(Items.STONE, 1);
            List<CompoundTag> bad = new ArrayList<>();
            for(int slot : new int[] { 30, 31, 100, -1, Integer.MIN_VALUE, Integer.MAX_VALUE }) {
                CompoundTag t = new CompoundTag();
                t.putInt("slot", slot);
                t.put("stack", saved(level.registryAccess(), stackTag));
                bad.add(t);
            }
            CompoundTag noStack = new CompoundTag();
            noStack.putInt("slot", 4);
            bad.add(noStack);
            CompoundTag emptyStack = new CompoundTag();
            emptyStack.putInt("slot", 4);
            emptyStack.put("stack", new CompoundTag());
            bad.add(emptyStack);
            CompoundTag unknownItem = new CompoundTag();
            unknownItem.putInt("slot", 4);
            CompoundTag nonsense = new CompoundTag();
            nonsense.putString("id", "hbmsntm:no_such_item_at_all");
            nonsense.putInt("count", 1);
            unknownItem.put("stack", nonsense);
            bad.add(unknownItem);
            CompoundTag textSlot = new CompoundTag();
            textSlot.putString("slot", "4");
            textSlot.put("stack", saved(level.registryAccess(), stackTag));
            bad.add(textSlot);
            CompoundTag listStack = new CompoundTag();
            listStack.putInt("slot", 4);
            listStack.put("stack", new ListTag());
            bad.add(listStack);
            for(int i = 0; i < bad.size(); i++) {
                CompoundTag t = bad.get(i);
                noThrow("slot payload " + i, () -> CompoundTagControl.apply(p, t, abs));
                for(int slot = 0; slot < 30; slot++) check(slot == 13 ? r.getItem(slot).is(Items.DIRT) : r.getItem(slot).isEmpty(), "slot payload " + i + " changed slot " + slot + " to " + r.getItem(slot));
            }

            // TileEntityCraneRouter.java:125-128: the distance from the block corner must be below 20
            Arrays.fill(r.modes, 0);
            p.setPos(abs.getX() + 19.9D, abs.getY(), abs.getZ());
            CompoundTagControl.apply(p, key("toggle", 0), abs);
            check(r.modes[0] == 1, "a player 19.9 blocks away could not toggle");
            p.setPos(abs.getX() + 20.1D, abs.getY(), abs.getZ());
            CompoundTagControl.apply(p, key("toggle", 1), abs);
            check(r.modes[1] == 0, "a player 20.1 blocks away toggled");
        }).run();
        passed("router_control").run();
        helper.succeed();
    }

    // TileEntityMachineBase.java:135-138 (no slot open to automation), CraneRouter has no breakBlock (nothing but the block drops), TileEntityCraneRouter.java:102-123 (pattern0-5 with mode0-4, the int array modes, the inventory)
    @GameTest(template = TEMPLATE, batch = "hbm31d_router_capability_break_persist", timeoutTicks = 200)
    public static void router_capability_break_persist(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            HolderLookup.Provider reg = level.registryAccess();
            BlockPos rel = new BlockPos(8, 2, 8);
            CraneRouterBlockEntity r = router(helper, rel);
            BlockPos abs = helper.absolutePos(rel);

            for(Direction d : Direction.values()) {
                check(r.getSlotsForFace(d).length == 0, "getSlotsForFace(" + d + ") is " + Arrays.toString(r.getSlotsForFace(d)) + ", expected none");
                IItemHandler h = handler(level, abs, d);
                check(h == null || h.getSlots() == 0, "the handler from " + d + " shows " + (h == null ? 0 : h.getSlots()) + " slots, expected none");
            }
            IItemHandler unsided = handler(level, abs, null);
            check(unsided == null || unsided.getSlots() == 0, "an unsided query shows slots");
            for(int i = 0; i < 30; i++) check(!r.canPlaceItem(i, s(Items.DIRT, 1)), "slot " + i + " takes items");

            // persistence
            Arrays.setAll(r.modes, i -> new int[] { 1, 2, 3, 0, 3, 1 }[i]);
            setFilter(r, 0, s(Items.DIRT, 1), "exact");
            setFilter(r, 7, s(Items.IRON_INGOT, 1), "c:ingots/iron");
            setFilter(r, 29, s(Items.STONE, 1), "wildcard");
            CompoundTag tag = r.saveWithFullMetadata(reg);
            check(Arrays.equals(tag.getIntArray("modes"), new int[] { 1, 2, 3, 0, 3, 1 }), "the saved modes are " + Arrays.toString(tag.getIntArray("modes")));
            check("exact".equals(tag.getCompound("pattern0").getString("mode0")) && "c:ingots/iron".equals(tag.getCompound("pattern1").getString("mode2")) && "wildcard".equals(tag.getCompound("pattern5").getString("mode4"))
                    && !tag.getCompound("pattern0").contains("mode1"), "the saved pattern keys are " + tag.getCompound("pattern0") + " / " + tag.getCompound("pattern1") + " / " + tag.getCompound("pattern5") + " (:102-123)");
            CraneRouterBlockEntity loaded = new CraneRouterBlockEntity(abs, level.getBlockState(abs));
            loaded.loadWithComponents(tag, reg);
            check(Arrays.equals(loaded.modes, r.modes), "the loaded modes are " + Arrays.toString(loaded.modes));
            for(int side = 0; side < 6; side++) check(Arrays.equals(loaded.patterns[side].modes, r.patterns[side].modes), "the loaded pattern " + side + " is " + Arrays.toString(loaded.patterns[side].modes));
            for(int i = 0; i < 30; i++) check(ItemStack.matches(loaded.getItem(i), r.getItem(i)), "slot " + i + " holds " + loaded.getItem(i) + " after loading, expected " + r.getItem(i));
            RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf(Unpooled.buffer(), level.registryAccess());
            r.serialize(buf);
            CraneRouterBlockEntity fromPacket = new CraneRouterBlockEntity(abs, level.getBlockState(abs));
            fromPacket.deserialize(buf);
            check(Arrays.equals(fromPacket.modes, r.modes) && "c:ingots/iron".equals(fromPacket.patterns[1].modes[2]) && fromPacket.patterns[0].modes[1] == null, "the packet gave modes " + Arrays.toString(fromPacket.modes));

            // breaking drops the block only
            for(int i = 0; i < 30; i++) r.setItem(i, s(Items.DIAMOND, 1));
            level.destroyBlock(abs, true);
            check(dropped(helper, Items.DIAMOND) == 0, "the sorter dropped " + dropped(helper, Items.DIAMOND) + " filter items, expected 0 (phantom slots)");
            check(dropped(helper, routerBlock().asItem()) == 1, "the sorter dropped " + dropped(helper, routerBlock().asItem()) + " block items, expected 1");
            clearEntities(helper);
        }).run();
        passed("router_capability_break_persist").run();
        helper.succeed();
    }

    // ================================================================ 2. the splitter

    private static BlockPos placeSplitter(GameTestHelper helper, BlockPos coreRel, Direction facing) {
        SmokeTestSupport.place(helper, splitterBlock(), coreRel, facing);
        return coreRel.relative(facing.getCounterClockWise());
    }

    private static int blocksOf(GameTestHelper helper, Block block, BlockPos centreRel, int radius) {
        int n = 0;
        for(int x = -radius; x <= radius; x++) for(int y = -1; y <= 1; y++) for(int z = -radius; z <= radius; z++) {
            if(helper.getLevel().getBlockState(helper.absolutePos(centreRel.offset(x, y, z))).is(block)) n++;
        }
        return n;
    }

    // CraneSplitter.java:58-65 (dimensions {0,0,0,0,0,1}, offset 0: the clicked cell is the core, one more cell beside it) and BlockDummyable placement through a player and the block item: the four facings, the core
    // where the click put it, the second block on the core's facing.getCounterClockWise() side with the FACING that points from the core to it, a block in the way refuses the placement, taking either block takes both
    @GameTest(template = TEMPLATE, batch = "hbm31d_splitter_place", timeoutTicks = 100)
    public static void splitter_place(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            Block block = splitterBlock();
            float[] yaws = { 0F, 90F, 180F, 270F };
            for(float yaw : yaws) {
                TestPlayer p = player(helper, GameType.CREATIVE, yaw);
                BlockPos coreRel = new BlockPos(8, 2, 4);
                BlockPos floorRel = coreRel.below();
                helper.setBlock(floorRel, Blocks.STONE.defaultBlockState());
                for(int x = -2; x <= 2; x++) for(int z = -2; z <= 2; z++) helper.setBlock(coreRel.offset(x, 0, z), Blocks.AIR.defaultBlockState());
                Direction facing = p.getDirection().getOpposite();
                ItemStack stack = new ItemStack(block);
                BlockPos floorAbs = helper.absolutePos(floorRel);
                stack.useOn(new UseOnContext(level, p, InteractionHand.MAIN_HAND, stack, new BlockHitResult(Vec3.atCenterOf(floorAbs).add(0, 0.5, 0), Direction.UP, floorAbs, false)));
                String ctx = "yaw " + yaw + " (facing " + facing + ")";
                BlockState coreState = helper.getBlockState(coreRel);
                check(coreState.is(block) && coreState.getValue(DummyableBlock.TYPE) == DummyBlockType.CORE && coreState.getValue(DummyableBlock.FACING) == facing, ctx + ": the core cell is " + coreState);
                BlockPos slaveRel = coreRel.relative(facing.getCounterClockWise());
                BlockState slave = helper.getBlockState(slaveRel);
                check(slave.is(block) && slave.getValue(DummyableBlock.TYPE) == DummyBlockType.DUMMY, ctx + ": the second block at " + slaveRel + " is " + slave + " (static derivation: the core's facing.getCounterClockWise() side)");
                check(slave.getValue(DummyableBlock.FACING) == facing.getCounterClockWise(), ctx + ": the second block's FACING is " + slave.getValue(DummyableBlock.FACING) + ", expected " + facing.getCounterClockWise() + " (core to second block)");
                check(blocksOf(helper, block, coreRel, 2) == 2, ctx + ": " + blocksOf(helper, block, coreRel, 2) + " splitter blocks stand around, expected 2");
                check(SmokeTestSupport.blockEntity(helper, coreRel, CraneSplitterBlockEntity.class) != null && helper.getLevel().getBlockEntity(helper.absolutePos(slaveRel)) == null, ctx + ": the block entities are not core only");
                check(block.asItem() == stack.getItem() && stack.getCount() == 1, ctx + ": the item stack changed");
                helper.setBlock(coreRel, Blocks.AIR.defaultBlockState());
                helper.setBlock(slaveRel, Blocks.AIR.defaultBlockState());
            }

            // a block in the way of the second cell: nothing is placed, the survival stack stays whole
            for(float yaw : yaws) {
                TestPlayer p = player(helper, GameType.SURVIVAL, yaw);
                BlockPos coreRel = new BlockPos(8, 2, 4);
                BlockPos floorRel = coreRel.below();
                helper.setBlock(floorRel, Blocks.STONE.defaultBlockState());
                for(int x = -2; x <= 2; x++) for(int z = -2; z <= 2; z++) helper.setBlock(coreRel.offset(x, 0, z), Blocks.AIR.defaultBlockState());
                Direction facing = p.getDirection().getOpposite();
                BlockPos slaveRel = coreRel.relative(facing.getCounterClockWise());
                helper.setBlock(slaveRel, Blocks.STONE.defaultBlockState());
                ItemStack stack = new ItemStack(block, 3);
                BlockPos floorAbs = helper.absolutePos(floorRel);
                stack.useOn(new UseOnContext(level, p, InteractionHand.MAIN_HAND, stack, new BlockHitResult(Vec3.atCenterOf(floorAbs).add(0, 0.5, 0), Direction.UP, floorAbs, false)));
                check(blocksOf(helper, block, coreRel, 2) == 0, "yaw " + yaw + ": a splitter was placed against a blocked second cell");
                check(helper.getBlockState(slaveRel).is(Blocks.STONE), "yaw " + yaw + ": the block in the way was replaced by " + helper.getBlockState(slaveRel));
                check(stack.getCount() == 3, "yaw " + yaw + ": the refused placement used up the item (" + stack.getCount() + " left of 3)");
                helper.setBlock(slaveRel, Blocks.AIR.defaultBlockState());
            }
        }).run();
        passed("splitter_place").run();
        helper.succeed();
    }

    // BlockDummyable.breakBlock / the orphan rule: taking either block takes the whole splitter, and only one block item drops
    @GameTest(template = TEMPLATE, batch = "hbm31d_splitter_break", timeoutTicks = 100)
    public static void splitter_break(GameTestHelper helper) {
        BlockPos coreRel = new BlockPos(8, 2, 8);
        BlockPos slaveRel = placeSplitter(helper, coreRel, Direction.NORTH);
        BlockPos coreRel2 = new BlockPos(8, 2, 4);
        BlockPos slaveRel2 = placeSplitter(helper, coreRel2, Direction.EAST);
        helper.startSequence()
                .thenExecute(guard(() -> {
                    check(helper.getBlockState(coreRel).is(splitterBlock()) && helper.getBlockState(slaveRel).is(splitterBlock()) && helper.getBlockState(coreRel2).is(splitterBlock()) && helper.getBlockState(slaveRel2).is(splitterBlock()), "the splitters were not placed");
                    helper.getLevel().destroyBlock(helper.absolutePos(coreRel), true);
                    helper.getLevel().destroyBlock(helper.absolutePos(slaveRel2), true);
                }))
                .thenExecuteAfter(3, guard(() -> {
                    check(helper.getBlockState(coreRel).isAir() && helper.getBlockState(slaveRel).isAir(), "after breaking the core the splitter at " + coreRel + " left " + helper.getBlockState(coreRel) + " / " + helper.getBlockState(slaveRel));
                    check(helper.getBlockState(coreRel2).isAir() && helper.getBlockState(slaveRel2).isAir(), "after breaking the second block the splitter at " + coreRel2 + " left " + helper.getBlockState(coreRel2) + " / " + helper.getBlockState(slaveRel2));
                    check(dropped(helper, splitterBlock().asItem()) == 2, "breaking two splitters dropped " + dropped(helper, splitterBlock().asItem()) + " block items, expected 2");
                    clearEntities(helper);
                }))
                .thenExecute(passed("splitter_break"))
                .thenSucceed();
    }

    // CraneSplitter.java:91-93,152-156: items only enter on the side the belts come from (the core's travel direction is its facing, the second block turns its own facing once again to the same), never diagonally,
    // packages do not enter and travel on like over a plain belt; the belt moves items away from the entry side along the lane
    @GameTest(template = TEMPLATE, batch = "hbm31d_splitter_travel", timeoutTicks = 200)
    public static void splitter_travel(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            CraneSplitterBlock block = splitterBlock();
            Direction[] facings = { Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST };
            int z = 2;
            for(Direction facing : facings) {
                BlockPos coreRel = new BlockPos(8, 2, z);
                z += 3;
                BlockPos slaveRel = placeSplitter(helper, coreRel, facing);
                BlockPos coreAbs = helper.absolutePos(coreRel);
                BlockPos slaveAbs = helper.absolutePos(slaveRel);
                for(BlockPos abs : new BlockPos[] { coreAbs, slaveAbs }) {
                    String ctx = facing + (abs.equals(coreAbs) ? " core" : " second block");
                    BlockState state = level.getBlockState(abs);
                    check(block.getTravelDirection(state) == facing, ctx + ": the travel side is " + block.getTravelDirection(state) + ", expected " + facing + " (:152-156)");
                    for(Direction d : Direction.values()) {
                        boolean expected = d == facing;
                        check(block.canItemEnter(level, abs, d, detached(level, s(Items.DIRT, 1))) == expected, ctx + ": an item from " + d + (expected ? " is refused" : " is accepted") + " (:91)");
                        check(!block.canPackageEnter(level, abs, d, detachedPackage(level, s(Items.DIRT, 1))), ctx + ": a package from " + d + " is accepted (:92-93)");
                    }
                    check(!block.canItemEnter(level, abs, null, detached(level, s(Items.DIRT, 1))), ctx + ": an item with no direction is accepted");

                    // the belt: an item standing on the lane moves away from the entry side, and towards the lane's centre line
                    Vec3 centre = new Vec3(abs.getX() + 0.5, abs.getY() + 0.25, abs.getZ() + 0.5);
                    Vec3 offLane = centre.add(facing.getStepZ() != 0 ? 0.2 : 0, 0, facing.getStepX() != 0 ? 0.2 : 0);
                    Vec3 next = block.getTravelLocation(level, abs, offLane, 0.05);
                    double along = (next.x - offLane.x) * facing.getStepX() + (next.z - offLane.z) * facing.getStepZ();
                    check(along < -0.01, ctx + ": the item moved " + along + " along " + facing + ", expected towards the opposite");
                    double perpBefore = Math.abs((offLane.x - centre.x) * facing.getStepZ() + (offLane.z - centre.z) * facing.getStepX());
                    double perpAfter = Math.abs((next.x - centre.x) * facing.getStepZ() + (next.z - centre.z) * facing.getStepX());
                    check(perpAfter <= perpBefore + 1.0E-9, ctx + ": the item drifted away from the lane's centre (" + perpBefore + " -> " + perpAfter + ")");
                    Vec3 snap = block.getClosestSnappingPosition(level, abs, offLane);
                    check(Math.abs(snap.y - (abs.getY() + 0.25)) < 1.0E-9, ctx + ": the snapping height is " + snap.y);
                }

                // a package on the splitter is not taken and not dropped
                MovingPackage pkg = new MovingPackage(NtmEntityTypes.MOVING_PACKAGE.get(), level);
                pkg.setItemStacks(new ItemStack[] { s(Items.DIRT, 2) });
                pkg.setPos(Vec3.atCenterOf(coreAbs));
                level.addFreshEntity(pkg);
                pkg.enterBlock(block, coreAbs, facing);
                check(!pkg.isRemoved(), facing + ": the package entered the splitter");
                check(itemsNear(level, Vec3.atCenterOf(coreAbs), 1.5, Items.DIRT) == 0, facing + ": the package dropped its items");
                pkg.discard();
            }
        }).run();
        passed("splitter_travel").run();
        helper.succeed();
    }

    /** The lane an item with the given global index (counted over all entries so far) goes to: the left lane takes the first {@code left} of every cycle of left + right. */
    private static boolean toLeft(int n, int left, int right) {
        return n % (left + right) < left;
    }

    // TileEntityCraneSplitter.java:19-46 / CraneSplitter.java:96-121: the items are counted out one by one, the left lane first with its ratio, then the right lane with its ratio; the cursor continues over
    // several entries; the core lane gets the left part and the second block's lane the right part; a lane with nothing gets no moving item; the entered stack is not shared
    @GameTest(template = TEMPLATE, batch = "hbm31d_splitter_ratio", timeoutTicks = 200)
    public static void splitter_ratio(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            CraneSplitterBlock block = splitterBlock();
            int[][] ratios = { { 1, 1 }, { 1, 3 }, { 16, 1 }, { 5, 2 }, { 3, 16 } };
            int[][] entries = {
                    { 64 },
                    { 1, 1, 1, 1, 1, 1, 1, 1 },
                    { 2, 3, 5, 1, 7, 64, 1 },
                    { 3, 3, 3, 3, 3, 3 },
                    { 64, 64 } };
            int z = 2;
            for(int[] ratio : ratios) {
                for(int[] entry : entries) {
                    BlockPos coreRel = new BlockPos(8, 2, z);
                    z = z >= 11 ? 2 : z + 3;
                    clearEntities(helper);
                    helper.setBlock(coreRel, Blocks.AIR.defaultBlockState());
                    helper.setBlock(coreRel.relative(Direction.NORTH.getCounterClockWise()), Blocks.AIR.defaultBlockState());
                    BlockPos slaveRel = placeSplitter(helper, coreRel, Direction.NORTH);
                    BlockPos coreAbs = helper.absolutePos(coreRel);
                    CraneSplitterBlockEntity be = SmokeTestSupport.blockEntity(helper, coreRel, CraneSplitterBlockEntity.class);
                    be.leftRatio = ratio[0];
                    be.rightRatio = ratio[1];
                    String ctx = ratio[0] + ":" + ratio[1] + " entries " + Arrays.toString(entry);
                    int index = 0;
                    int leftSum = 0;
                    int rightSum = 0;
                    int entities = 0;
                    for(int amount : entry) {
                        int expectLeft = 0;
                        int expectRight = 0;
                        for(int i = 0; i < amount; i++) {
                            if(toLeft(index++, ratio[0], ratio[1])) expectLeft++; else expectRight++;
                        }
                        int beforeLeft = remaining(movingIn(helper, coreRel));
                        int beforeRight = remaining(movingIn(helper, slaveRel));
                        ItemStack in = s(Items.COBBLESTONE, amount);
                        block.onItemEnter(level, coreAbs, Direction.NORTH, detached(level, in));
                        int gotLeft = remaining(movingIn(helper, coreRel)) - beforeLeft;
                        int gotRight = remaining(movingIn(helper, slaveRel)) - beforeRight;
                        check(gotLeft == expectLeft && gotRight == expectRight, ctx + ": an entry of " + amount + " (item " + (index - amount) + " on) split " + gotLeft + "/" + gotRight + ", expected " + expectLeft + "/" + expectRight + " (:19-46)");
                        check(in.getCount() == amount, ctx + ": the entered stack was changed");
                        entities += (expectLeft > 0 ? 1 : 0) + (expectRight > 0 ? 1 : 0);
                        leftSum += gotLeft;
                        rightSum += gotRight;
                    }
                    int all = Arrays.stream(entry).sum();
                    check(leftSum + rightSum == all, ctx + ": " + (leftSum + rightSum) + " items came out of " + all);
                    check(movingIn(helper, coreRel).size() + movingIn(helper, slaveRel).size() == entities, ctx + ": " + (movingIn(helper, coreRel).size() + movingIn(helper, slaveRel).size()) + " moving items for " + entities + " non-empty parts");
                    for(MovingItem e : movingIn(helper, coreRel)) check(near(e.position(), new Vec3(coreAbs.getX() + 0.5, coreAbs.getY() + 0.25, coreAbs.getZ() + 0.5), 1.0E-6), ctx + ": a left part stands at " + fmt(e.position()) + ", not on the core lane");
                    BlockPos slaveAbs = helper.absolutePos(slaveRel);
                    for(MovingItem e : movingIn(helper, slaveRel)) check(near(e.position(), new Vec3(slaveAbs.getX() + 0.5, slaveAbs.getY() + 0.25, slaveAbs.getZ() + 0.5), 1.0E-6), ctx + ": a right part stands at " + fmt(e.position()) + ", not on the second lane");
                    if(entry.length == 1 && entry[0] == 64) {
                        int[][] known = { { 32, 32 }, { 16, 48 }, { 61, 3 }, { 46, 18 }, { 12, 52 } };
                        int idx = Arrays.asList(ratios).indexOf(ratio);
                        check(leftSum == known[idx][0] && rightSum == known[idx][1], ctx + ": a stack of 64 split " + leftSum + "/" + rightSum + ", expected " + known[idx][0] + "/" + known[idx][1] + " (hand counted: whole cycles of " + (ratio[0] + ratio[1]) + " plus the rest to the left lane first)");
                    }
                }
            }
            clearEntities(helper);
        }).run();
        passed("splitter_ratio").run();
        helper.succeed();
    }

    // CraneSplitter.java:164-187: only the screwdriver, a click raises the lane's ratio and a sneak click lowers it, kept within 1-16, the core is the left lane and the second block the right lane
    @GameTest(template = TEMPLATE, batch = "hbm31d_splitter_screwdriver", timeoutTicks = 200)
    public static void splitter_screwdriver(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos coreRel = new BlockPos(8, 2, 8);
            BlockPos slaveRel = placeSplitter(helper, coreRel, Direction.SOUTH);
            BlockPos coreAbs = helper.absolutePos(coreRel);
            BlockPos slaveAbs = helper.absolutePos(slaveRel);
            CraneSplitterBlockEntity be = SmokeTestSupport.blockEntity(helper, coreRel, CraneSplitterBlockEntity.class);
            TestPlayer p = player(helper, GameType.SURVIVAL, 0F);
            check(be.leftRatio == 1 && be.rightRatio == 1, "a new splitter has ratios " + be.leftRatio + ":" + be.rightRatio + ", expected 1:1");

            for(int half = 0; half < 2; half++) {
                BlockPos target = half == 0 ? coreAbs : slaveAbs;
                String name = half == 0 ? "core (left)" : "second block (right)";
                for(int i = 2; i <= 16; i++) {
                    InteractionResult r = useOn(level, p, screwdriver(), target, Direction.UP);
                    int got = half == 0 ? be.leftRatio : be.rightRatio;
                    check(got == i && r.consumesAction(), name + ": click " + (i - 1) + " gave " + got + " (" + r + "), expected " + i);
                }
                for(int extra = 0; extra < 4; extra++) useOn(level, p, screwdriver(), target, Direction.UP);
                check((half == 0 ? be.leftRatio : be.rightRatio) == 16, name + ": the ratio went above 16");
                p.setShiftKeyDown(true);
                for(int i = 15; i >= 1; i--) {
                    useOn(level, p, screwdriver(), target, Direction.UP);
                    int got = half == 0 ? be.leftRatio : be.rightRatio;
                    check(got == i, name + ": a sneak click gave " + got + ", expected " + i);
                }
                for(int extra = 0; extra < 4; extra++) useOn(level, p, screwdriver(), target, Direction.UP);
                p.setShiftKeyDown(false);
                check((half == 0 ? be.leftRatio : be.rightRatio) == 1, name + ": the ratio went below 1");
                check(half == 0 ? be.rightRatio == 1 : be.leftRatio == 1, name + ": the other lane's ratio changed");
            }
            useOn(level, p, screwdriver(), coreAbs, Direction.UP);
            useOn(level, p, screwdriver(), coreAbs, Direction.UP);
            useOn(level, p, screwdriver(), slaveAbs, Direction.UP);
            check(be.leftRatio == 3 && be.rightRatio == 2, "clicks 2 on the core and 1 on the second block gave " + be.leftRatio + ":" + be.rightRatio + ", expected 3:2");
            check(useOn(level, p, new ItemStack(NtmItems.SCREWDRIVER_DESH.get()), coreAbs, Direction.UP).consumesAction() && be.leftRatio == 4, "the desh screwdriver did not raise the ratio");

            // no other tool changes the ratio
            int left = be.leftRatio;
            int right = be.rightRatio;
            for(ItemStack other : new ItemStack[] { s(NtmItems.HAND_DRILL.get(), 1), s(NtmItems.DEFUSER.get(), 1), wand(), tool(), s(Items.STICK, 1) }) {
                for(BlockPos target : new BlockPos[] { coreAbs, slaveAbs }) {
                    for(boolean sneak : new boolean[] { false, true }) {
                        p.setShiftKeyDown(sneak);
                        useOn(level, p, other, target, Direction.UP);
                        check(be.leftRatio == left && be.rightRatio == right, other.getItem() + (sneak ? " sneaking" : "") + " changed the ratios to " + be.leftRatio + ":" + be.rightRatio);
                    }
                }
            }
            p.setShiftKeyDown(false);
            ItemStack drill = s(NtmItems.HAND_DRILL.get(), 1);
            useOn(level, p, drill, coreAbs, Direction.UP);
            check(drill.getDamageValue() == 0, "a tool that did nothing was worn (" + drill.getDamageValue() + ")");
        }).run();
        passed("splitter_screwdriver").run();
        helper.succeed();
    }

    // TileEntityCraneExtractor.java:178-185: an extractor whose belt side is an enterable belt hands the item to it directly; a splitter entered that way splits it (CraneSplitter.java:91,96-121)
    @GameTest(template = TEMPLATE, batch = "hbm31d_splitter_extractor", timeoutTicks = 400)
    public static void splitter_extractor(GameTestHelper helper) {
        BlockPos coreRel = new BlockPos(8, 2, 8);
        BlockPos slaveRel = placeSplitter(helper, coreRel, Direction.WEST);
        Container chest = chest(helper, new BlockPos(6, 2, 8));
        CraneExtractorBlockEntity ex = placeCrane(helper, new BlockPos(7, 2, 8), NtmBlocks.CRANE_EXTRACTOR.get(), Direction.EAST, Direction.WEST, CraneExtractorBlockEntity.class);
        ex.setItem(CraneExtractorBlockEntity.SLOT_STACK_UPGRADE, s(NtmItems.UPGRADE_STACK_2.get(), 1));
        ex.setItem(CraneExtractorBlockEntity.SLOT_EJECTOR_UPGRADE, s(NtmItems.UPGRADE_EJECTOR_3.get(), 1));
        chest.setItem(0, s(Items.COBBLESTONE, 64));
        int[] taken = { 0 };
        helper.startSequence()
                .thenExecute(guard(() -> {
                    check(helper.getBlockState(coreRel).getValue(DummyableBlock.FACING) == Direction.WEST, "the splitter faces " + helper.getBlockState(coreRel).getValue(DummyableBlock.FACING));
                    check(slaveRel.equals(coreRel.relative(Direction.WEST.getCounterClockWise())), "the second block is not on the counter-clockwise side");
                }))
                .thenWaitUntil(guard(() -> {
                    taken[0] = 64 - total(chest);
                    check(taken[0] >= 16, "the extractor has taken only " + taken[0] + " items from the chest");
                }))
                .thenExecute(guard(() -> {
                    AABB box = new AABB(helper.absolutePos(coreRel)).minmax(new AABB(helper.absolutePos(slaveRel))).inflate(1.2);
                    int onLanes = 0;
                    for(MovingItem e : helper.getLevel().getEntitiesOfClass(MovingItem.class, box)) onLanes += e.getItemStack().getCount();
                    for(ItemEntity e : helper.getLevel().getEntitiesOfClass(ItemEntity.class, box.inflate(4))) onLanes += e.getItem().getCount();
                    taken[0] = 64 - total(chest);
                    check(onLanes == taken[0], onLanes + " items stand on or near the splitter, the chest lost " + taken[0] + ": the extractor's items did not all enter it directly");
                    check(onLanes > 0, "nothing came out of the splitter");
                    clearEntities(helper);
                }))
                .thenExecute(passed("splitter_extractor"))
                .thenSucceed();
    }

    // TileEntityCraneSplitter.java:54-74: pos, count, left, right; a ratio below 1 reads as 1; the saved cursor continues the count where it stood
    @GameTest(template = TEMPLATE, batch = "hbm31d_splitter_persist", timeoutTicks = 100)
    public static void splitter_persist(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            HolderLookup.Provider reg = level.registryAccess();
            BlockPos coreRel = new BlockPos(8, 2, 8);
            placeSplitter(helper, coreRel, Direction.NORTH);
            BlockPos abs = helper.absolutePos(coreRel);
            CraneSplitterBlockEntity be = SmokeTestSupport.blockEntity(helper, coreRel, CraneSplitterBlockEntity.class);
            be.leftRatio = 5;
            be.rightRatio = 9;
            be.splitStack(s(Items.DIRT, 8));
            CompoundTag tag = be.saveWithFullMetadata(reg);
            check(tag.contains("pos", Tag.TAG_BYTE) && tag.contains("count", Tag.TAG_BYTE) && tag.getByte("left") == 5 && tag.getByte("right") == 9, "the saved keys are " + tag.getAllKeys() + " (:54-74)");
            check(tag.getBoolean("pos") && tag.getByte("count") == 6, "after 8 items of 5:9 the saved cursor is pos " + tag.getBoolean("pos") + " count " + tag.getByte("count") + ", expected the right lane with 6 left (5 left, 3 right)");
            CraneSplitterBlockEntity loaded = new CraneSplitterBlockEntity(abs, level.getBlockState(abs));
            loaded.loadWithComponents(tag, reg);
            check(loaded.leftRatio == 5 && loaded.rightRatio == 9, "the loaded ratios are " + loaded.leftRatio + ":" + loaded.rightRatio);
            for(int i = 0; i < 12; i++) {
                int amount = 1 + (i * 7) % 11;
                ItemStack[] a = be.splitStack(s(Items.DIRT, amount));
                ItemStack[] b = loaded.splitStack(s(Items.DIRT, amount));
                check(a[0].getCount() == b[0].getCount() && a[1].getCount() == b[1].getCount(), "the loaded splitter diverged at step " + i + ": " + b[0].getCount() + "/" + b[1].getCount() + " instead of " + a[0].getCount() + "/" + a[1].getCount());
            }
            CompoundTag low = new CompoundTag();
            low.putByte("left", (byte) 0);
            low.putByte("right", (byte) -4);
            CraneSplitterBlockEntity clamped = new CraneSplitterBlockEntity(abs, level.getBlockState(abs));
            clamped.loadWithComponents(low, reg);
            check(clamped.leftRatio == 1 && clamped.rightRatio == 1, "ratios 0 / -4 read as " + clamped.leftRatio + ":" + clamped.rightRatio + ", expected 1:1 (:60-61)");
            RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf(Unpooled.buffer(), level.registryAccess());
            be.serialize(buf);
            CraneSplitterBlockEntity fromPacket = new CraneSplitterBlockEntity(abs, level.getBlockState(abs));
            fromPacket.deserialize(buf);
            check(fromPacket.leftRatio == 5 && fromPacket.rightRatio == 9, "the packet gave ratios " + fromPacket.leftRatio + ":" + fromPacket.rightRatio);
        }).run();
        passed("splitter_persist").run();
        helper.succeed();
    }

    // ================================================================ 3. the partitioner

    private static CranePartitionerBlockEntity partitioner(GameTestHelper helper, BlockPos rel, Direction facing) {
        helper.setBlock(rel, partitionerBlock().defaultBlockState().setValue(CranePartitionerBlock.HORIZONTAL_FACING, facing));
        return SmokeTestSupport.blockEntity(helper, rel, CranePartitionerBlockEntity.class);
    }

    /** A partitioner block entity the test ticks itself: never added to the level, so the world does not tick it. */
    private static CranePartitionerBlockEntity detachedPartitioner(GameTestHelper helper, BlockPos rel) {
        CranePartitionerBlockEntity be = new CranePartitionerBlockEntity(helper.absolutePos(rel), partitionerBlock().defaultBlockState());
        be.setLevel(helper.getLevel());
        return be;
    }

    // CranePartitioner.java:150-178: every tick the queue slots 0-44 are walked from the smallest stack, acidizer inputs leave in moving items of exactly the item's per-cycle amount at (x + 0.5, y + 0.25, z + 0.5)
    // until fewer are left (the rest stays), an item with no amount leaves whole (:161), emptied slots become empty; the amount is CrystallizerRecipes.java:108-109 (setReq 10 and 16) and 1 for the ores (:321)
    @GameTest(template = TEMPLATE, batch = "hbm31d_partitioner_batches", timeoutTicks = 100)
    public static void partitioner_batches(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos rel = new BlockPos(8, 2, 8);
            BlockPos abs = helper.absolutePos(rel);
            check(CrystallizerRecipes.getInputAmount(s(NtmItems.SCRAP_OIL.get(), 1)) == 16 && CrystallizerRecipes.getInputAmount(s(NtmItems.PLANT_ITEM_MUSTARDWILLOW.get(), 1)) == 10 && CrystallizerRecipes.getInputAmount(s(Items.IRON_ORE, 1)) == 1
                    && CrystallizerRecipes.getInputAmount(s(Items.DIRT, 1)) == 0, "the per-cycle amounts are scrap oil " + CrystallizerRecipes.getInputAmount(s(NtmItems.SCRAP_OIL.get(), 1)) + ", mustard willow " + CrystallizerRecipes.getInputAmount(s(NtmItems.PLANT_ITEM_MUSTARDWILLOW.get(), 1))
                    + ", iron ore " + CrystallizerRecipes.getInputAmount(s(Items.IRON_ORE, 1)) + ", dirt " + CrystallizerRecipes.getInputAmount(s(Items.DIRT, 1)) + ", expected 16, 10, 1, 0");
            CranePartitionerBlockEntity be = detachedPartitioner(helper, rel);
            be.setItem(0, s(NtmItems.SCRAP_OIL.get(), 40));
            be.setItem(1, s(NtmItems.PLANT_ITEM_MUSTARDWILLOW.get(), 25));
            be.setItem(2, s(Items.IRON_ORE, 3));
            be.setItem(3, s(NtmItems.SCRAP_OIL.get(), 15));
            be.setItem(4, s(Items.DIRT, 7));
            be.setItem(50, s(NtmItems.SCRAP_OIL.get(), 64));
            be.updateEntity();

            AABB box = new AABB(abs).inflate(0.5);
            List<MovingItem> sent = level.getEntitiesOfClass(MovingItem.class, box);
            List<Integer> scrap = new ArrayList<>();
            List<Integer> mustard = new ArrayList<>();
            List<Integer> ore = new ArrayList<>();
            List<Integer> dirt = new ArrayList<>();
            for(MovingItem e : sent) {
                ItemStack st = e.getItemStack();
                check(near(e.position(), new Vec3(abs.getX() + 0.5, abs.getY() + 0.25, abs.getZ() + 0.5), 1.0E-6), "a moving item stands at " + fmt(e.position()) + ", expected the cell's (x + 0.5, y + 0.25, z + 0.5) (:170-172)");
                if(st.is(NtmItems.SCRAP_OIL.get())) scrap.add(st.getCount());
                else if(st.is(NtmItems.PLANT_ITEM_MUSTARDWILLOW.get())) mustard.add(st.getCount());
                else if(st.is(Items.IRON_ORE)) ore.add(st.getCount());
                else if(st.is(Items.DIRT)) dirt.add(st.getCount());
                else check(false, "an unexpected item left: " + st);
            }
            check(scrap.equals(List.of(16, 16)), "scrap oil (40 + 15 in two slots) left as " + scrap + ", expected two batches of 16 from the first slot");
            check(mustard.equals(List.of(10, 10)), "mustard willow (25) left as " + mustard + ", expected two batches of 10");
            check(ore.equals(List.of(1, 1, 1)), "iron ore (3) left as " + ore + ", expected three batches of 1");
            check(dirt.equals(List.of(7)), "dirt, no acidizer input, left as " + dirt + ", expected one whole stack of 7 (:161)");
            check(be.getItem(0).is(NtmItems.SCRAP_OIL.get()) && be.getItem(0).getCount() == 8, "the rest of the 40 scrap oil is " + be.getItem(0) + ", expected 8");
            check(be.getItem(1).getCount() == 5, "the rest of the 25 mustard willow is " + be.getItem(1) + ", expected 5");
            check(be.getItem(2).isEmpty() && be.getItem(4).isEmpty(), "emptied slots hold " + be.getItem(2) + " / " + be.getItem(4));
            check(be.getItem(3).getCount() == 15, "15 scrap oil, below one batch, became " + be.getItem(3));
            check(be.getItem(50).getCount() == 64, "the second half is not for sending, but slot 50 became " + be.getItem(50));
            clearEntities(helper);
            be.updateEntity();
            check(level.getEntitiesOfClass(MovingItem.class, box).isEmpty(), "a second tick sent " + level.getEntitiesOfClass(MovingItem.class, box).size() + " more moving items although every slot is below one batch");
        }).run();
        passed("partitioner_batches").run();
        helper.succeed();
    }

    // CranePartitioner.java:124-138 and InventoryUtil.java:120-133: an acidizer input goes into slots 0-44, anything else into 45-89 (first onto equal stacks, then into the first empty slot), the rest drops in the block's centre;
    // :87-89: items enter from the facing side only, packages do not enter and travel on
    @GameTest(template = TEMPLATE, batch = "hbm31d_partitioner_enter", timeoutTicks = 100)
    public static void partitioner_enter(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos rel = new BlockPos(8, 2, 8);
            CranePartitionerBlockEntity be = partitioner(helper, rel, Direction.WEST);
            BlockPos abs = helper.absolutePos(rel);
            CranePartitionerBlock block = partitionerBlock();

            for(Direction d : Direction.values()) {
                check(block.canItemEnter(level, abs, d, detached(level, s(Items.DIRT, 1))) == (d == Direction.WEST), "an item from " + d + " is " + (d == Direction.WEST ? "refused" : "accepted") + " (:87)");
                check(!block.canPackageEnter(level, abs, d, detachedPackage(level, s(Items.DIRT, 1))), "a package from " + d + " is accepted (:88-89)");
            }
            check(!block.canItemEnter(level, abs, null, detached(level, s(Items.DIRT, 1))), "an item with no direction is accepted");

            // acidizer inputs fill the queue, topping up equal stacks first
            block.onItemEnter(level, abs, Direction.WEST, detached(level, s(Items.IRON_ORE, 30)));
            check(be.getItem(0).is(Items.IRON_ORE) && be.getItem(0).getCount() == 30 && total(be, 45, 90) == 0, "30 iron ore went to " + be.getItem(0) + " / second half " + total(be, 45, 90));
            block.onItemEnter(level, abs, Direction.WEST, detached(level, s(Items.IRON_ORE, 50)));
            check(be.getItem(0).getCount() == 64 && be.getItem(1).is(Items.IRON_ORE) && be.getItem(1).getCount() == 16, "50 more iron ore made " + be.getItem(0).getCount() + " + " + be.getItem(1).getCount() + ", expected 64 + 16");

            // anything else lands in 45-89 and stays
            block.onItemEnter(level, abs, Direction.WEST, detached(level, s(Items.DIRT, 40)));
            block.onItemEnter(level, abs, Direction.WEST, detached(level, s(Items.DIRT, 40)));
            int dirtInSecond = count(be, Items.DIRT, 45, 90);
            check(dirtInSecond == 80 && count(be, Items.DIRT, 0, 45) == 0, "2 x 40 dirt went to " + dirtInSecond + " in the second half and " + count(be, Items.DIRT, 0, 45) + " in the first");
            int topUp = 0;
            for(int i = 45; i < 90; i++) if(be.getItem(i).is(Items.DIRT)) topUp++;
            check(topUp == 2 && be.getItem(45).getCount() == 64 && be.getItem(46).getCount() == 16, "2 x 40 dirt filled " + topUp + " slots (" + be.getItem(45).getCount() + " + " + be.getItem(46).getCount() + "), expected 2 slots, 64 + 16 (InventoryUtil.java:120-133 tops up the equal stack first, the rest into the first empty slot)");

            // a full half drops the rest in the centre
            for(int i = 45; i < 90; i++) be.setItem(i, s(Items.COBBLESTONE, 64));
            block.onItemEnter(level, abs, Direction.WEST, detached(level, s(Items.DIRT, 5)));
            check(itemsNear(level, Vec3.atCenterOf(abs), 0.3, Items.DIRT) == 5 && count(be, Items.DIRT, 45, 90) == 0, "dirt with no room did not drop in the centre (" + itemsNear(level, Vec3.atCenterOf(abs), 0.3, Items.DIRT) + " found)");
            clearEntities(helper);
            for(int i = 0; i < 45; i++) be.setItem(i, s(Items.IRON_ORE, 64));
            block.onItemEnter(level, abs, Direction.WEST, detached(level, s(Items.IRON_ORE, 3)));
            check(itemsNear(level, Vec3.atCenterOf(abs), 0.3, Items.IRON_ORE) == 3 && count(be, Items.IRON_ORE, 45, 90) == 0, "ore with no queue room did not drop in the centre, or went to the second half");

            // the entered stack is not shared with the entity it came from
            for(int i = 0; i < 90; i++) be.setItem(i, ItemStack.EMPTY);
            ItemStack source = s(Items.IRON_ORE, 9);
            block.onItemEnter(level, abs, Direction.WEST, detached(level, source));
            check(source.getCount() == 9 && be.getItem(0).getCount() == 9, "the entering stack was changed to " + source);

            // a package passes over: not taken, not dropped
            MovingPackage pkg = new MovingPackage(NtmEntityTypes.MOVING_PACKAGE.get(), level);
            pkg.setItemStacks(new ItemStack[] { s(Items.DIRT, 2) });
            pkg.setPos(Vec3.atCenterOf(abs));
            level.addFreshEntity(pkg);
            pkg.enterBlock(block, abs, Direction.WEST);
            check(!pkg.isRemoved() && itemsNear(level, Vec3.atCenterOf(abs), 1.5, Items.DIRT) == 0, "the package entered or dropped at the partitioner");
            pkg.discard();
            clearEntities(helper);
        }).run();
        passed("partitioner_enter").run();
        helper.succeed();
    }

    // CranePartitioner.java:189-209: every side sees all 90 slots, only slots 0-44 take items and only acidizer inputs with an amount of at least 1, only slots 45-89 give items; through the container rules and the item capability
    @GameTest(template = TEMPLATE, batch = "hbm31d_partitioner_access", timeoutTicks = 100)
    public static void partitioner_access(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos rel = new BlockPos(8, 2, 8);
            CranePartitionerBlockEntity be = partitioner(helper, rel, Direction.NORTH);
            BlockPos abs = helper.absolutePos(rel);
            ItemStack ore = s(Items.IRON_ORE, 4);
            ItemStack dirt = s(Items.DIRT, 4);

            for(Direction d : Direction.values()) {
                check(be.getSlotsForFace(d).length == 90, "getSlotsForFace(" + d + ") shows " + be.getSlotsForFace(d).length + " slots, expected 90 (:198-209)");
                for(int slot = 0; slot < 90; slot++) {
                    check(be.getSlotsForFace(d)[slot] == slot, "face " + d + " slot list is not 0-89");
                    check(be.canPlaceItemThroughFace(slot, ore, d) == (slot < 45), "iron ore into slot " + slot + " from " + d + " is " + be.canPlaceItemThroughFace(slot, ore, d) + " (:194-196)");
                    check(!be.canPlaceItemThroughFace(slot, dirt, d), "dirt into slot " + slot + " from " + d + " is accepted");
                    check(be.canTakeItemThroughFace(slot, ore, d) == (slot >= 45), "taking from slot " + slot + " through " + d + " is " + be.canTakeItemThroughFace(slot, ore, d) + " (:189-191)");
                }
            }

            // the container's own rule (CranePartitioner.java:194-196): only the queue half, only inputs with an amount of at least 1
            for(int slot = 0; slot < 90; slot++) {
                check(be.canPlaceItem(slot, ore) == (slot < 45), "canPlaceItem(" + slot + ", iron ore) is " + be.canPlaceItem(slot, ore));
                check(!be.canPlaceItem(slot, dirt), "canPlaceItem(" + slot + ", dirt) is true");
                check(!be.canPlaceItem(slot, ItemStack.EMPTY), "canPlaceItem(" + slot + ", empty) is true");
            }

            // through the item capability, from every side
            for(Direction d : Direction.values()) {
                IItemHandler h = handler(level, abs, d);
                check(h != null && h.getSlots() == 90, "the handler from " + d + " has " + (h == null ? "no" : h.getSlots()) + " slots, expected 90");
                be.clearContent();
                check(h.insertItem(3, ore.copy(), false).isEmpty() && be.getItem(3).getCount() == 4, "inserting ore into slot 3 from " + d + " failed (" + be.getItem(3) + ")");
                ItemStack refused = h.insertItem(60, ore.copy(), false);
                check(refused.getCount() == 4 && be.getItem(60).isEmpty(), "inserting ore into slot 60 from " + d + " was accepted");
                ItemStack notOre = h.insertItem(4, dirt.copy(), false);
                check(notOre.getCount() == 4 && be.getItem(4).isEmpty(), "inserting dirt into slot 4 from " + d + " was accepted");
                be.setItem(5, s(Items.IRON_ORE, 6));
                be.setItem(70, s(Items.DIRT, 6));
                check(h.extractItem(5, 6, false).isEmpty() && be.getItem(5).getCount() == 6, "extracting from queue slot 5 through " + d + " worked");
                ItemStack out = h.extractItem(70, 4, false);
                check(out.is(Items.DIRT) && out.getCount() == 4 && be.getItem(70).getCount() == 2, "extracting dirt from slot 70 through " + d + " gave " + out + " (left " + be.getItem(70) + ")");
            }

            // no unsided access that would bypass the rules
            IItemHandler unsided = handler(level, abs, null);
            if(unsided != null) {
                be.clearContent();
                check(!unsided.insertItem(60, ore.copy(), false).isEmpty(), "an unsided query put ore into the second half");
            }
        }).run();
        passed("partitioner_access").run();
        helper.succeed();
    }

    // CrystallizerRecipes.java:268-286,318-322: a later registration of the same input overwrites the earlier amount, the item is looked up by item and type, 0 when no row knows it; NEO takes the last row
    // of the (custom) table whose input accepts the stack (CrystallizerRecipes.getInputAmount(List, stack))
    @GameTest(template = TEMPLATE, batch = "hbm31d_partitioner_recipe_table", timeoutTicks = 100)
    public static void partitioner_recipe_table(GameTestHelper helper) {
        guard(() -> {
            ItemStack out = s(Items.DIAMOND, 1);
            List<CrystallizerRecipe> table = new ArrayList<>();
            table.add(new CrystallizerRecipe(new ComparableStack(Items.COAL, 3), new FluidStack(Fluids.PEROXIDE, 500), out, 600, 0F));
            table.add(new CrystallizerRecipe(new ComparableStack(Items.GOLD_INGOT, 5), new FluidStack(Fluids.PEROXIDE, 500), out, 600, 0F));
            table.add(new CrystallizerRecipe(new ComparableStack(Items.COAL, 7), new FluidStack(Fluids.SULFURIC_ACID, 500), out, 600, 0F));
            table.add(new CrystallizerRecipe(new ComparableStack(NtmItems.PART_GENERIC.get(), 2, PartGenericItem.Type.PISTON_PNEUMATIC), new FluidStack(Fluids.PEROXIDE, 500), out, 600, 0F));
            check(CrystallizerRecipes.getInputAmount(table, s(Items.COAL, 1)) == 7, "coal under two acids gave " + CrystallizerRecipes.getInputAmount(table, s(Items.COAL, 1)) + ", expected 7 (the later row overwrites, :321)");
            check(CrystallizerRecipes.getInputAmount(table, s(Items.COAL, 64)) == 7, "the stack size changed the amount");
            check(CrystallizerRecipes.getInputAmount(table, s(Items.GOLD_INGOT, 1)) == 5, "gold ingot gave " + CrystallizerRecipes.getInputAmount(table, s(Items.GOLD_INGOT, 1)) + ", expected 5");
            check(CrystallizerRecipes.getInputAmount(table, s(Items.DIRT, 1)) == 0, "an unlisted item gave " + CrystallizerRecipes.getInputAmount(table, s(Items.DIRT, 1)) + ", expected 0 (:270)");
            check(CrystallizerRecipes.getInputAmount(table, ItemStack.EMPTY) == 0, "an empty stack gave an amount");
            check(CrystallizerRecipes.getInputAmount(table, pneumatic()) == 2, "the pneumatic piston gave " + CrystallizerRecipes.getInputAmount(table, pneumatic()) + ", expected 2 (item and type)");
            check(CrystallizerRecipes.getInputAmount(table, MetaHelper.newStack(NtmItems.PART_GENERIC.get(), 1, PartGenericItem.Type.PISTON_HYDRAULIC)) == 0, "another type of the same item took the amount");
            table.add(new CrystallizerRecipe(new ComparableStack(Items.GOLD_INGOT, 11), new FluidStack(Fluids.SULFURIC_ACID, 500), out, 600, 0F));
            check(CrystallizerRecipes.getInputAmount(table, s(Items.GOLD_INGOT, 1)) == 11, "a row added last did not win");
            check(CrystallizerRecipes.getInputAmount(new ArrayList<>(), s(Items.COAL, 1)) == 0, "an empty table gave an amount");
            // the default table still behaves as the original's amounts
            check(CrystallizerRecipes.getInputAmount(CrystallizerRecipes.getDefaultRecipes(), s(NtmItems.SCRAP_OIL.get(), 1)) == 16, "the default table gave scrap oil another amount");
        }).run();
        passed("partitioner_recipe_table").run();
        helper.succeed();
    }

    // CranePartitioner.java:67-79,219-247 and the placement table (:67-74): the facing follows the player like the belts' (input side towards the placer), the shape is 12/16 high, taking the block drops it and all 90 slots;
    // the slots, the queue and the second half, survive a save and a packet
    @GameTest(template = TEMPLATE, batch = "hbm31d_partitioner_break_persist", timeoutTicks = 200)
    public static void partitioner_break_persist(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            HolderLookup.Provider reg = level.registryAccess();
            CranePartitionerBlock block = partitionerBlock();
            for(float yaw : new float[] { 0F, 90F, 180F, 270F }) {
                TestPlayer p = player(helper, GameType.CREATIVE, yaw);
                BlockPos floorRel = new BlockPos(4, 1, 4);
                helper.setBlock(floorRel, Blocks.STONE.defaultBlockState());
                helper.setBlock(floorRel.above(), Blocks.AIR.defaultBlockState());
                ItemStack stack = new ItemStack(block);
                BlockPos floorAbs = helper.absolutePos(floorRel);
                stack.useOn(new UseOnContext(level, p, InteractionHand.MAIN_HAND, stack, new BlockHitResult(Vec3.atCenterOf(floorAbs).add(0, 0.5, 0), Direction.UP, floorAbs, false)));
                BlockState state = helper.getBlockState(floorRel.above());
                check(state.is(block) && state.getValue(CranePartitionerBlock.HORIZONTAL_FACING) == p.getDirection().getOpposite(), "yaw " + yaw + ": the placed block is " + state + ", expected the input side towards the player");
                check(state.getShape(level, helper.absolutePos(floorRel.above())).max(Direction.Axis.Y) == 0.75, "the shape is " + state.getShape(level, helper.absolutePos(floorRel.above())).max(Direction.Axis.Y) + " high, expected 0.75 (:76-79)");
                check(SmokeTestSupport.blockEntity(helper, floorRel.above(), CranePartitionerBlockEntity.class) != null, "no block entity was created");
                helper.setBlock(floorRel.above(), Blocks.AIR.defaultBlockState());
            }

            BlockPos rel = new BlockPos(8, 2, 8);
            CranePartitionerBlockEntity be = partitioner(helper, rel, Direction.SOUTH);
            BlockPos abs = helper.absolutePos(rel);
            int expected = 0;
            for(int i = 0; i < 90; i++) {
                be.setItem(i, s(Items.DIRT, 1 + i % 64));
                expected += 1 + i % 64;
            }
            CompoundTag tag = be.saveWithFullMetadata(reg);
            CranePartitionerBlockEntity loaded = new CranePartitionerBlockEntity(abs, level.getBlockState(abs));
            loaded.loadWithComponents(tag, reg);
            for(int i = 0; i < 90; i++) check(ItemStack.matches(loaded.getItem(i), be.getItem(i)), "slot " + i + " holds " + loaded.getItem(i) + " after loading, expected " + be.getItem(i));
            level.destroyBlock(abs, true);
            check(dropped(helper, Items.DIRT) == expected, "breaking the partitioner dropped " + dropped(helper, Items.DIRT) + " items from its slots, expected " + expected + " (:219-247, all 90 slots)");
            check(dropped(helper, block.asItem()) == 1, "breaking the partitioner dropped " + dropped(helper, block.asItem()) + " block items, expected 1");
            clearEntities(helper);
        }).run();
        passed("partitioner_break_persist").run();
        helper.succeed();
    }

    // TileEntityCraneExtractor.java:178-185 on the partitioner: the extractor's belt side is the partitioner's input side, the items are handed over directly; non-inputs are kept in 45-89, none is lost
    @GameTest(template = TEMPLATE, batch = "hbm31d_partitioner_extractor", timeoutTicks = 400)
    public static void partitioner_extractor(GameTestHelper helper) {
        BlockPos rel = new BlockPos(8, 2, 8);
        CranePartitionerBlockEntity be = partitioner(helper, rel, Direction.WEST);
        Container chest = chest(helper, new BlockPos(6, 2, 8));
        CraneExtractorBlockEntity ex = placeCrane(helper, new BlockPos(7, 2, 8), NtmBlocks.CRANE_EXTRACTOR.get(), Direction.EAST, Direction.WEST, CraneExtractorBlockEntity.class);
        ex.setItem(CraneExtractorBlockEntity.SLOT_STACK_UPGRADE, s(NtmItems.UPGRADE_STACK_2.get(), 1));
        ex.setItem(CraneExtractorBlockEntity.SLOT_EJECTOR_UPGRADE, s(NtmItems.UPGRADE_EJECTOR_3.get(), 1));
        chest.setItem(0, s(Items.DIRT, 64));
        helper.startSequence()
                .thenWaitUntil(guard(() -> check(total(be, 45, 90) >= 32, "the partitioner holds " + total(be, 45, 90) + " items in its second half, the chest still " + total(chest))))
                .thenExecuteAfter(2, guard(() -> {
                    int inPart = total(be, 45, 90);
                    check(total(be, 0, 45) == 0, "dirt reached the queue half (" + total(be, 0, 45) + ")");
                    check(inPart + total(chest) == 64, "the second half holds " + inPart + ", the chest " + total(chest) + ": " + (64 - inPart - total(chest)) + " items were lost on the way");
                    check(dropped(helper, Items.DIRT) == 0 && helper.getLevel().getEntitiesOfClass(MovingItem.class, helper.getBounds()).isEmpty(), "items were left as entities");
                }))
                .thenExecute(passed("partitioner_extractor"))
                .thenSucceed();
    }

    // ================================================================ 4. the settings tool: copy and paste through the real right-click

    private static ListTag displayList(String... names) {
        ListTag list = new ListTag();
        for(String n : names) {
            CompoundTag e = new CompoundTag();
            e.putString("info", n);
            list.add(e);
        }
        return list;
    }

    /** A sneaking right-click with a fresh tool, checked against ItemSettingsTool.java:81-139 (onItemUseFirst answers true on the server for a copiable block). */
    private static ItemStack copyFrom(ServerLevel level, TestPlayer p, BlockPos abs, String what) {
        ItemStack t = tool();
        InteractionResult r = sneakUse(level, p, t, abs);
        check(r == InteractionResult.CONSUME, what + ": the sneaking right-click with the tool returned " + r + ", expected CONSUME (:136 returns true on the server)");
        check(TagsUtil.hasCustomData(t), what + ": the tool holds no data after the copy");
        return t;
    }

    private static void pasteTo(ServerLevel level, TestPlayer p, ItemStack t, BlockPos abs, String what) {
        InteractionResult r = use(level, p, t, abs);
        check(r == InteractionResult.CONSUME, what + ": the right-click with the tool returned " + r + ", expected CONSUME, so neither the screen nor the valve got the click (:136)");
    }

    // ItemSettingsTool.java:81-139 on the cranes with TileEntityCraneBase.java:113-181: the sneaking click copies (input side, output side as ForgeDirection numbers, the filter entries with their relative slot, the
    // display names), the plain click pastes entry 0 = the filter and entry 1 = the orientation; the tool's old data is replaced; a block that cannot be copied is left alone; no screen opens
    @GameTest(template = TEMPLATE, batch = "hbm31d_tool_crane", timeoutTicks = 100)
    public static void tool_crane(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            TestPlayer p = player(helper, GameType.SURVIVAL, 0F);
            BlockPos srcRel = new BlockPos(5, 2, 4);
            BlockPos dstRel = new BlockPos(5, 2, 6);
            CraneExtractorBlockEntity src = placeCrane(helper, srcRel, NtmBlocks.CRANE_EXTRACTOR.get(), Direction.EAST, Direction.WEST, CraneExtractorBlockEntity.class);
            CraneExtractorBlockEntity dst = placeCrane(helper, dstRel, NtmBlocks.CRANE_EXTRACTOR.get(), Direction.NORTH, Direction.SOUTH, CraneExtractorBlockEntity.class);
            src.setItem(0, s(Items.DIRT, 1));
            src.setItem(3, s(Items.STONE, 1));
            BlockPos srcAbs = helper.absolutePos(srcRel);
            BlockPos dstAbs = helper.absolutePos(dstRel);

            ItemStack t = copyFrom(level, p, srcAbs, "extractor");
            CompoundTag d = toolData(t);
            check(d.getString("tileName").equals(src.getBlockState().getBlock().getDescriptionId()), "tileName is " + d.getString("tileName"));
            check(d.getInt("copyIndex") == 0 && d.contains("lastSwitch"), "copyIndex " + d.getInt("copyIndex") + ", lastSwitch " + d.contains("lastSwitch") + " (:90-92)");
            check(d.getInt("inputSide") == 5 && d.getInt("outputSide") == 4, "the sides are " + d.getInt("inputSide") + " / " + d.getInt("outputSide") + ", expected east 5 / west 4 (ForgeDirection numbers, :113-137)");
            ListTag items = d.getList("items", Tag.TAG_COMPOUND);
            check(items.size() == 2 && items.getCompound(0).getByte("slot") == 0 && items.getCompound(1).getByte("slot") == 3, "the filter entries are " + items);
            ListTag info = d.getList("displayInfo", Tag.TAG_COMPOUND);
            check(info.size() == 2 && info.getCompound(0).getString("info").equals("copytool.filter") && info.getCompound(1).getString("info").equals("copytool.orientation"), "the display entries are " + info + " (TileEntityCraneBase.java:179-181)");
            check(p.opened.isEmpty(), "the copy opened a screen");

            // entry 0 pastes the filter and leaves the orientation
            pasteTo(level, p, t, dstAbs, "paste entry 0");
            check(dst.getItem(0).is(Items.DIRT) && dst.getItem(3).is(Items.STONE) && dst.getItem(1).isEmpty(), "entry 0 pasted " + dst.getItem(0) + " / " + dst.getItem(3) + " / " + dst.getItem(1));
            BlockState state = helper.getBlockState(dstRel);
            check(state.getValue(CraneBaseBlock.INPUT) == Direction.NORTH && state.getValue(CraneBaseBlock.OUTPUT) == Direction.SOUTH, "entry 0 turned the crane to " + state.getValue(CraneBaseBlock.INPUT) + " / " + state.getValue(CraneBaseBlock.OUTPUT));
            check(p.opened.isEmpty(), "the paste opened a screen");

            // entry 1 pastes the orientation and leaves the filter
            for(int i = 0; i < 9; i++) dst.setItem(i, ItemStack.EMPTY);
            setIndex(t, 1);
            pasteTo(level, p, t, dstAbs, "paste entry 1");
            state = helper.getBlockState(dstRel);
            check(state.getValue(CraneBaseBlock.INPUT) == Direction.EAST && state.getValue(CraneBaseBlock.OUTPUT) == Direction.WEST, "entry 1 gave " + state.getValue(CraneBaseBlock.INPUT) + " / " + state.getValue(CraneBaseBlock.OUTPUT) + ", expected east / west");
            dst = SmokeTestSupport.blockEntity(helper, dstRel, CraneExtractorBlockEntity.class);
            check(total(dst, 0, 9) == 0, "entry 1 pasted a filter");

            // a tool with no data pastes nothing and still keeps the click from the crane
            ItemStack bare = tool();
            pasteTo(level, p, bare, dstAbs, "paste without data");
            check(!TagsUtil.hasCustomData(bare) && total(dst, 0, 9) == 0 && p.opened.isEmpty(), "a tool with no data changed something");

            // a block that cannot be copied is not touched and the data stays (:81-83, getCopyInfoSource gives null)
            BlockPos stoneRel = new BlockPos(9, 2, 4);
            helper.setBlock(stoneRel, Blocks.STONE.defaultBlockState());
            CompoundTag before = toolData(t).copy();
            InteractionResult r = sneakUse(level, p, t, helper.absolutePos(stoneRel));
            check(r != InteractionResult.CONSUME && r != InteractionResult.SUCCESS, "stone answered " + r + " to the sneaking tool");
            check(toolData(t).equals(before), "a click on stone changed the tool data");
            r = use(level, p, t, helper.absolutePos(stoneRel));
            check(r != InteractionResult.CONSUME && r != InteractionResult.SUCCESS, "stone answered " + r + " to the pasting tool");
        }).run();
        passed("tool_crane").run();
        helper.succeed();
    }

    // TileEntityCraneRouter.java:148-203 through the tool: the copy holds the filter entries and the six modes, entry n pastes side n's entries except the first slot of the side (slot > index * 5), each pasted slot advances its
    // mode once, then the modes are replaced; a router with an empty filter has nothing to paste and so keeps the destination's modes; the other sources (extractor) and targets (extractor) take the base class' paste
    @GameTest(template = TEMPLATE, batch = "hbm31d_tool_router", timeoutTicks = 100)
    public static void tool_router(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            TestPlayer p = player(helper, GameType.SURVIVAL, 0F);
            BlockPos srcRel = new BlockPos(4, 2, 4);
            CraneRouterBlockEntity src = router(helper, srcRel);
            Arrays.setAll(src.modes, i -> new int[] { 0, 0, 1, 2, 0, 3 }[i]);
            setFilter(src, 3, s(Items.DIAMOND, 1), "exact");
            setFilter(src, 10, s(Items.DIRT, 1), "exact");
            setFilter(src, 11, s(Items.STONE, 1), "exact");
            setFilter(src, 12, s(Items.SAND, 1), "exact");
            setFilter(src, 15, s(Items.GRAVEL, 1), "exact");
            setFilter(src, 25, s(Items.COAL, 1), "exact");
            ItemStack t = copyFrom(level, p, helper.absolutePos(srcRel), "router");
            CompoundTag d = toolData(t);
            ListTag items = d.getList("items", Tag.TAG_COMPOUND);
            int[] slots = new int[items.size()];
            for(int i = 0; i < slots.length; i++) slots[i] = items.getCompound(i).getByte("slot");
            check(Arrays.equals(slots, new int[] { 3, 10, 11, 12, 15, 25 }), "the copied entries have the slots " + Arrays.toString(slots) + " (:149-165)");
            check(Arrays.equals(d.getIntArray("modes"), new int[] { 0, 0, 1, 2, 0, 3 }), "the copied modes are " + Arrays.toString(d.getIntArray("modes")));
            ListTag info = d.getList("displayInfo", Tag.TAG_COMPOUND);
            check(info.size() == 6, "the router copy has " + info.size() + " display entries, expected 6");
            for(int i = 0; i < 6; i++) check(info.getCompound(i).getString("info").equals("copytool.pattern" + i), "display entry " + i + " is " + info.getCompound(i).getString("info") + " (:191-197)");
            check(d.getString("tileName").equals(routerBlock().getDescriptionId()), "tileName is " + d.getString("tileName"));
            check(p.opened.isEmpty(), "the copy opened the screen");

            BlockPos dstRel = new BlockPos(4, 2, 8);
            CraneRouterBlockEntity dst = router(helper, dstRel);
            BlockPos dstAbs = helper.absolutePos(dstRel);
            int[] other = { 3, 3, 3, 3, 3, 3 };
            dst.modes = other.clone();
            dst.setItem(10, s(Items.COAL, 1));
            setIndex(t, 2);
            pasteTo(level, p, t, dstAbs, "side 2");
            check(dst.getItem(10).is(Items.COAL), "slot 10, the first of the side, was pasted over: " + dst.getItem(10) + " (:176 slot > index * 5)");
            check(dst.getItem(11).is(Items.STONE) && dst.getItem(12).is(Items.SAND), "slots 11 / 12 hold " + dst.getItem(11) + " / " + dst.getItem(12));
            check("exact".equals(dst.patterns[2].modes[1]) && "exact".equals(dst.patterns[2].modes[2]), "the pasted slots' modes are " + dst.patterns[2].modes[1] + " / " + dst.patterns[2].modes[2] + ", expected one nextMode from none = exact (:177-181)");
            for(int i = 0; i < 30; i++) if(i != 10 && i != 11 && i != 12) check(dst.getItem(i).isEmpty(), "slot " + i + " was pasted on side 2's turn: " + dst.getItem(i));
            check(Arrays.equals(dst.modes, new int[] { 0, 0, 1, 2, 0, 3 }), "the modes are " + Arrays.toString(dst.modes) + " after the paste, expected the copy's (:184)");

            for(int i = 0; i < 30; i++) dst.setItem(i, ItemStack.EMPTY);
            dst.modes = other.clone();
            setIndex(t, 3);
            pasteTo(level, p, t, dstAbs, "side 3");
            for(int i = 0; i < 30; i++) check(dst.getItem(i).isEmpty(), "side 3's only entry is its first slot, which is skipped, but slot " + i + " holds " + dst.getItem(i));
            check(Arrays.equals(dst.modes, new int[] { 0, 0, 1, 2, 0, 3 }), "the modes were not replaced on side 3's paste: " + Arrays.toString(dst.modes));

            dst.modes = other.clone();
            setIndex(t, 0);
            pasteTo(level, p, t, dstAbs, "side 0");
            check(dst.getItem(3).is(Items.DIAMOND) && total(dst, 0, 3) + total(dst, 4, 30) == 0, "side 0 pasted " + dst.getItem(3) + " and " + (total(dst, 0, 3) + total(dst, 4, 30)) + " other items");
            for(int i = 0; i < 30; i++) dst.setItem(i, ItemStack.EMPTY);
            setIndex(t, 5);
            pasteTo(level, p, t, dstAbs, "side 5");
            check(total(dst, 0, 30) == 0, "side 5's only entry sits on its first slot 25 and was pasted");
            // a negative index in the data is read as 0
            setIndex(t, -7);
            pasteTo(level, p, t, dstAbs, "negative index");
            check(dst.getItem(3).is(Items.DIAMOND), "a negative copyIndex did not paste side 0");

            // a router with no filter: nothing to paste, the modes of the target stay
            BlockPos emptyRel = new BlockPos(8, 2, 4);
            CraneRouterBlockEntity empty = router(helper, emptyRel);
            Arrays.setAll(empty.modes, i -> 1);
            ItemStack t2 = copyFrom(level, p, helper.absolutePos(emptyRel), "empty router");
            check(toolData(t2).getList("items", Tag.TAG_COMPOUND).isEmpty() && toolData(t2).getIntArray("modes").length == 6, "the empty router copy is " + toolData(t2));
            dst.modes = other.clone();
            dst.setItem(7, s(Items.DIRT, 1));
            pasteTo(level, p, t2, dstAbs, "empty router paste");
            check(Arrays.equals(dst.modes, other) && dst.getItem(7).is(Items.DIRT), "the empty router's paste changed the target: modes " + Arrays.toString(dst.modes) + ", slot 7 " + dst.getItem(7) + " (:166-168 the else branch)");
            check(!toolData(t2).contains("inputSide") && !toolData(t).contains("inputSide"), "the router's tool data holds crane keys");

            // an extractor's copy pastes into the router by the base class' paste: no modes in it, so the router's modes stay
            BlockPos exRel = new BlockPos(8, 2, 8);
            CraneExtractorBlockEntity ex = placeCrane(helper, exRel, NtmBlocks.CRANE_EXTRACTOR.get(), Direction.EAST, Direction.WEST, CraneExtractorBlockEntity.class);
            ex.setItem(0, s(Items.IRON_INGOT, 1));
            ex.setItem(3, s(Items.GOLD_INGOT, 1));
            ItemStack t3 = copyFrom(level, p, helper.absolutePos(exRel), "extractor");
            for(int i = 0; i < 30; i++) dst.setItem(i, ItemStack.EMPTY);
            dst.modes = other.clone();
            pasteTo(level, p, t3, dstAbs, "extractor into router");
            check(dst.getItem(0).is(Items.IRON_INGOT) && dst.getItem(3).is(Items.GOLD_INGOT) && total(dst, 0, 30) == 2, "the extractor's filter pasted as " + dst.getItem(0) + " / " + dst.getItem(3) + " (" + total(dst, 0, 30) + " items)");
            check(Arrays.equals(dst.modes, other), "an extractor's paste changed the router's modes to " + Arrays.toString(dst.modes));

            // a router's copy pastes into an extractor: the entries among the first nine that fit its nine slots
            BlockPos src2Rel = new BlockPos(12, 2, 4);
            CraneRouterBlockEntity src2 = router(helper, src2Rel);
            setFilter(src2, 0, s(Items.DIRT, 1), "exact");
            setFilter(src2, 2, s(Items.STONE, 1), "exact");
            setFilter(src2, 3, s(Items.SAND, 1), "exact");
            setFilter(src2, 12, s(Items.GRAVEL, 1), "exact");
            ItemStack t4 = copyFrom(level, p, helper.absolutePos(src2Rel), "router 2");
            for(int i = 0; i < 9; i++) ex.setItem(i, ItemStack.EMPTY);
            pasteTo(level, p, t4, helper.absolutePos(exRel), "router into extractor");
            check(ex.getItem(0).is(Items.DIRT) && ex.getItem(2).is(Items.STONE) && ex.getItem(3).is(Items.SAND) && total(ex, 0, 9) == 3, "the router's filter pasted as " + ex.getItem(0) + " / " + ex.getItem(2) + " / " + ex.getItem(3) + " (" + total(ex, 0, 9) + " items), expected slots 0, 2, 3 and not slot 12");
            check(helper.getBlockState(exRel).getValue(CraneBaseBlock.INPUT) == Direction.EAST, "the router's paste turned the extractor");
            check(p.opened.isEmpty(), "a copy or a paste opened a screen");
        }).run();
        passed("tool_router").run();
        helper.succeed();
    }

    // ItemSettingsTool.java:81-139 (onItemUseFirst answers true after copying or pasting, so the block's own right-click does not run): the sorter and the extractor do not open their screens, the valve does not toggle, a machine does not open;
    // the same click without the tool does open and toggle, which shows the checks can fail
    @GameTest(template = TEMPLATE, batch = "hbm31d_tool_nomenu", timeoutTicks = 100)
    public static void tool_nomenu(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos routerRel = new BlockPos(5, 2, 4);
            BlockPos exRel = new BlockPos(5, 2, 6);
            BlockPos valveRel = new BlockPos(5, 2, 8);
            BlockPos compRel = new BlockPos(9, 2, 4);
            BlockPos socketRel = new BlockPos(9, 2, 6);
            router(helper, routerRel);
            placeCrane(helper, exRel, NtmBlocks.CRANE_EXTRACTOR.get(), Direction.EAST, Direction.WEST, CraneExtractorBlockEntity.class);
            helper.setBlock(valveRel, NtmBlocks.FLUID_VALVE.get().defaultBlockState());
            PipeBaseBlockEntity valve = SmokeTestSupport.blockEntity(helper, valveRel, PipeBaseBlockEntity.class);
            core(helper, compRel, NtmBlocks.MACHINE_COMPRESSOR.get(), MachineCompressorBlockEntity.class);
            core(helper, socketRel, NtmBlocks.MACHINE_BATTERY_SOCKET.get(), BatteryBaseBlockEntity.class);

            // the control: an empty hand opens the screens and toggles the valve
            TestPlayer open = player(helper, GameType.SURVIVAL, 0F);
            use(level, open, ItemStack.EMPTY, helper.absolutePos(routerRel));
            use(level, open, ItemStack.EMPTY, helper.absolutePos(exRel));
            check(open.opened.size() == 2, "an empty hand opened " + open.opened.size() + " screens on the sorter and the extractor, expected 2");
            check(!helper.getBlockState(valveRel).getValue(FluidValveBlock.ENABLED), "the valve starts open");
            use(level, open, ItemStack.EMPTY, helper.absolutePos(valveRel));
            check(helper.getBlockState(valveRel).getValue(FluidValveBlock.ENABLED), "an empty hand did not toggle the valve");
            use(level, open, ItemStack.EMPTY, helper.absolutePos(valveRel));
            check(!helper.getBlockState(valveRel).getValue(FluidValveBlock.ENABLED), "a second empty-hand click did not close the valve");

            // with the tool: the paste happens and nothing opens or toggles
            TestPlayer p = player(helper, GameType.SURVIVAL, 0F);
            ItemStack fromRouter = copyFrom(level, p, helper.absolutePos(routerRel), "router");
            pasteTo(level, p, fromRouter, helper.absolutePos(routerRel), "router");
            ItemStack fromEx = copyFrom(level, p, helper.absolutePos(exRel), "extractor");
            pasteTo(level, p, fromEx, helper.absolutePos(exRel), "extractor");
            ItemStack water = toolWith(fluidData(Fluids.WATER.getID()));
            pasteTo(level, p, water, helper.absolutePos(valveRel), "valve");
            check(valve.getFluidType() == Fluids.WATER, "the valve's fluid is " + valve.getFluidType().getName() + " after the paste, expected water");
            check(!helper.getBlockState(valveRel).getValue(FluidValveBlock.ENABLED), "the tool's click toggled the valve");
            pasteTo(level, p, water, helper.absolutePos(valveRel), "valve again");
            check(!helper.getBlockState(valveRel).getValue(FluidValveBlock.ENABLED), "the second click toggled the valve");
            ItemStack fromComp = copyFrom(level, p, helper.absolutePos(compRel), "compressor");
            pasteTo(level, p, fromComp, helper.absolutePos(compRel), "compressor");
            ItemStack fromSocket = copyFrom(level, p, helper.absolutePos(socketRel), "battery socket");
            pasteTo(level, p, fromSocket, helper.absolutePos(socketRel), "battery socket");
            check(p.opened.isEmpty(), "the tool opened " + p.opened.size() + " screens");

            // a sneaking tool click does not toggle either
            sneakUse(level, p, water, helper.absolutePos(valveRel));
            check(!helper.getBlockState(valveRel).getValue(FluidValveBlock.ENABLED) && p.opened.isEmpty(), "a sneaking click changed the valve or opened a screen");
        }).run();
        passed("tool_nomenu").run();
        helper.succeed();
    }

    // ItemSettingsTool.java:29-62: the held tool, with data, moves to the next display entry while TOOL_ALT is down, every 5 ticks (the original's delay passes 4 on the fifth tick) and wraps from the last entry to 0.
    // A tool that is not the held stack, or with the key up, does nothing; with 0 or 1 entries the switch has nowhere to go and (per the main agent's change) the item data is not written at all
    @GameTest(template = TEMPLATE, batch = "hbm31d_tool_alt_switch", timeoutTicks = 400)
    public static void tool_alt_switch(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        SettingsToolItem item = (SettingsToolItem) NtmItems.SETTINGS_TOOL.get();
        TestPlayer p = player(helper, GameType.SURVIVAL, 0F);
        long start = level.getGameTime();

        ItemStack four = tool();
        CompoundTag d = new CompoundTag();
        d.putString("tileName", "block.hbmsntm.crane_router");
        d.putInt("copyIndex", 0);
        d.putLong("lastSwitch", start);
        d.put("displayInfo", displayList("copytool.pattern0", "copytool.pattern1", "copytool.pattern2", "copytool.pattern3"));
        TagsUtil.putCustomData(four, d);
        p.setItemInHand(InteractionHand.MAIN_HAND, four);
        HbmPlayerAttachments.setKeyPressed(p, EnumKeybind.TOOL_ALT, true);

        List<long[]> changes = new ArrayList<>();
        int[] last = { 0 };

        ItemStack one = tool();
        CompoundTag oneData = new CompoundTag();
        oneData.putString("tileName", "block.hbmsntm.barrel_steel");
        oneData.putInt("copyIndex", 0);
        oneData.putLong("lastSwitch", start - 100);
        oneData.put("displayInfo", displayList("fluid.hbmsntm.water"));
        TagsUtil.putCustomData(one, oneData.copy());
        ItemStack none = tool();
        CompoundTag noneData = new CompoundTag();
        noneData.putString("tileName", "block.hbmsntm.crane_router");
        noneData.putInt("copyIndex", 0);
        noneData.putLong("lastSwitch", start - 100);
        TagsUtil.putCustomData(none, noneData.copy());
        ItemStack held = tool();
        TagsUtil.putCustomData(held, d.copy());

        helper.startSequence()
                .thenExecuteFor(44, () -> guard(() -> {
                    item.inventoryTick(four, level, p, 0, true);
                    int idx = toolData(four).getInt("copyIndex");
                    if(idx != last[0]) {
                        changes.add(new long[] { level.getGameTime(), idx });
                        last[0] = idx;
                    }
                }).run())
                .thenExecute(guard(() -> {
                    check(changes.size() >= 7, "the entry changed " + changes.size() + " times in 44 ticks, expected at least 7");
                    for(int i = 0; i < changes.size(); i++) {
                        check(changes.get(i)[1] == (i + 1) % 4, "change " + i + " went to entry " + changes.get(i)[1] + ", expected " + ((i + 1) % 4) + " (index + 1, wrapping to 0 after the last: :40-41)");
                        if(i > 0) check(changes.get(i)[0] - changes.get(i - 1)[0] == 5, "changes " + (i - 1) + " and " + i + " lie " + (changes.get(i)[0] - changes.get(i - 1)[0]) + " ticks apart, expected 5 (:37 delay > 4)");
                    }
                    check(changes.get(0)[0] - start >= 5, "the first change came after " + (changes.get(0)[0] - start) + " ticks, expected at least 5");
                    check(toolData(four).getList("displayInfo", Tag.TAG_COMPOUND).size() == 4 && toolData(four).getString("tileName").equals("block.hbmsntm.crane_router"), "the switch changed other data: " + toolData(four));
                    // the key released: no more changes
                    HbmPlayerAttachments.setKeyPressed(p, EnumKeybind.TOOL_ALT, false);
                    last[0] = toolData(four).getInt("copyIndex");
                }))
                .thenExecuteFor(12, () -> guard(() -> {
                    item.inventoryTick(four, level, p, 0, true);
                    check(toolData(four).getInt("copyIndex") == last[0], "the entry changed with the key up");
                }).run())
                .thenExecute(guard(() -> {
                    // a stack that is not the held one does nothing, with the key down
                    HbmPlayerAttachments.setKeyPressed(p, EnumKeybind.TOOL_ALT, true);
                    p.setItemInHand(InteractionHand.MAIN_HAND, tool());
                }))
                .thenExecuteFor(12, () -> guard(() -> {
                    item.inventoryTick(held, level, p, 3, false);
                    check(toolData(held).getInt("copyIndex") == 0 && toolData(held).getLong("lastSwitch") == start, "a tool outside the main hand switched: " + toolData(held));
                }).run())
                .thenExecute(guard(() -> p.setItemInHand(InteractionHand.MAIN_HAND, one)))
                .thenExecuteFor(14, () -> guard(() -> {
                    item.inventoryTick(one, level, p, 0, true);
                    check(toolData(one).equals(oneData), "with one entry the tool data changed to " + toolData(one) + ", expected it untouched (copyIndex stays 0, lastSwitch is not written)");
                }).run())
                .thenExecute(guard(() -> p.setItemInHand(InteractionHand.MAIN_HAND, none)))
                .thenExecuteFor(14, () -> guard(() -> {
                    item.inventoryTick(none, level, p, 0, true);
                    check(toolData(none).equals(noneData), "with no entries the tool data changed to " + toolData(none) + ", expected it untouched");
                }).run())
                .thenExecute(passed("tool_alt_switch"))
                .thenSucceed();
    }

    /** What the static paste calls on its target. */
    private static final class Recorder implements ICopiable {
        int calls;
        int index = -99;
        CompoundTag tag;
        BlockPos pos;

        @Override
        public CompoundTag getSettings(net.minecraft.world.level.Level level, BlockPos pos) {
            return null;
        }

        @Override
        public void pasteSettings(CompoundTag tag, int index, net.minecraft.world.level.Level level, Player player, BlockPos pos) {
            this.calls++;
            this.index = index;
            this.tag = tag;
            this.pos = pos;
        }
    }

    // ItemSettingsTool.java:117-120 with GOAL31 decision 6 (paste only on the server, chunk loaded, player may build and interact, index at least 0); the copy of a machine without settings (null) clears the tool (:87-111)
    @GameTest(template = TEMPLATE, batch = "hbm31d_tool_paste_checks", timeoutTicks = 100)
    public static void tool_paste_checks(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos abs = helper.absolutePos(new BlockPos(5, 2, 5));
            TestPlayer p = player(helper, GameType.SURVIVAL, 0F);

            CompoundTag data = new CompoundTag();
            data.putString("tileName", "x");
            data.putInt("copyIndex", 3);
            ItemStack t = toolWith(data);
            Recorder rec = new Recorder();
            check(SettingsToolItem.paste(t, rec, level, abs, p), "a survival player on a loaded chunk was refused");
            check(rec.calls == 1 && rec.index == 3 && rec.pos.equals(abs) && rec.tag.getString("tileName").equals("x"), "the paste passed " + rec.calls + " calls, index " + rec.index + ", pos " + rec.pos);
            setIndex(t, -4);
            check(SettingsToolItem.paste(t, rec, level, abs, p) && rec.index == 0, "a negative copyIndex was passed on as " + rec.index);
            CompoundTag noIndex = new CompoundTag();
            noIndex.putString("tileName", "x");
            check(SettingsToolItem.paste(toolWith(noIndex), rec, level, abs, p) && rec.index == 0, "a missing copyIndex was passed on as " + rec.index);

            Recorder adventure = new Recorder();
            TestPlayer a = player(helper, GameType.ADVENTURE, 0F);
            check(!SettingsToolItem.paste(t, adventure, level, abs, a) && adventure.calls == 0, "an adventure player pasted (it may not build)");
            TestPlayer spectator = player(helper, GameType.SPECTATOR, 0F);
            check(!SettingsToolItem.paste(t, adventure, level, abs, spectator) && adventure.calls == 0, "a spectator pasted");
            Recorder far = new Recorder();
            BlockPos unloaded = new BlockPos(30_000_000, 64, 30_000_000);
            check(!SettingsToolItem.paste(t, far, level, unloaded, p) && far.calls == 0, "a position in an unloaded chunk was pasted to");
            TestPlayer creative = player(helper, GameType.CREATIVE, 0F);
            check(SettingsToolItem.paste(t, adventure, level, abs, creative) && adventure.calls == 1, "a creative player was refused");

            // the tool item on its own: a copy whose source gives no settings clears the old data (:87-111); dummy cell without a core
            BlockPos orphanRel = new BlockPos(9, 2, 9);
            helper.setBlock(orphanRel, NtmBlocks.MACHINE_FLUID_TANK.get().defaultBlockState().setValue(DummyableBlock.TYPE, DummyBlockType.DUMMY));
            ItemStack old = toolWith(data.copy());
            InteractionResult r = sneakUse(level, p, old, helper.absolutePos(orphanRel));
            check(r == InteractionResult.CONSUME, "the sneaking click on a dummy cell without a core returned " + r);
            check(!TagsUtil.hasCustomData(old), "the old tool data stayed after a copy with no settings: " + toolData(old));
            check(p.opened.isEmpty(), "a screen opened");
        }).run();
        passed("tool_paste_checks").run();
        helper.succeed();
    }

    private static CompoundTag typeCopy(ServerLevel level, TestPlayer p, BlockPos abs, FluidType expectedFirst, String what) {
        ItemStack t = copyFrom(level, p, abs, what);
        int[] ids = toolData(t).getIntArray("FluidID");
        check(ids.length >= 1 && ids[0] == expectedFirst.getID(), what + ": the copied fluid ids are " + Arrays.toString(ids) + ", expected the first to be " + expectedFirst.getUnlocalizedName() + " (IFluidCopiable.java:25-35)");
        return toolData(t);
    }

    // IFluidCopiable.java:25-69: the copy holds the id of every tank that has one, the paste sets the receiving tank's type from the chosen entry, an entry past the end does nothing; a barrel and a fluid tank paste, a launch pad
    // copies but pastes nothing (getTankToPaste is null); an id no fluid has is ignored by NEO (the original would empty the tank, IFluidCopiable.java:57)
    @GameTest(template = TEMPLATE, batch = "hbm31d_tool_families_a", timeoutTicks = 100)
    public static void tool_families_a(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            TestPlayer p = player(helper, GameType.SURVIVAL, 0F);
            BlockPos aRel = new BlockPos(4, 2, 4);
            BlockPos bRel = new BlockPos(4, 2, 6);
            helper.setBlock(aRel, NtmBlocks.BARREL_STEEL.get().defaultBlockState());
            helper.setBlock(bRel, NtmBlocks.BARREL_STEEL.get().defaultBlockState());
            BarrelBlockEntity a = SmokeTestSupport.blockEntity(helper, aRel, BarrelBlockEntity.class);
            BarrelBlockEntity b = SmokeTestSupport.blockEntity(helper, bRel, BarrelBlockEntity.class);
            a.tank.setTankType(Fluids.OIL);
            b.tank.setTankType(Fluids.WATER);
            ItemStack t = copyFrom(level, p, helper.absolutePos(aRel), "barrel");
            check(Arrays.equals(toolData(t).getIntArray("FluidID"), new int[] { Fluids.OIL.getID() }), "the barrel copy holds " + Arrays.toString(toolData(t).getIntArray("FluidID")));
            check(toolData(t).getList("displayInfo", Tag.TAG_COMPOUND).size() == 1 && toolData(t).getList("displayInfo", Tag.TAG_COMPOUND).getCompound(0).getString("info").equals(Fluids.OIL.getUnlocalizedName()), "the display entries are " + toolData(t).getList("displayInfo", Tag.TAG_COMPOUND) + " (:61-69)");
            check(toolData(t).getString("tileName").equals(a.getBlockState().getBlock().getDescriptionId()), "tileName is " + toolData(t).getString("tileName"));
            pasteTo(level, p, t, helper.absolutePos(bRel), "barrel");
            check(b.tank.getTankType() == Fluids.OIL, "the barrel took " + b.tank.getTankType().getUnlocalizedName() + ", expected oil");
            check(a.tank.getTankType() == Fluids.OIL, "the source barrel changed");

            // an entry past the end, an id nobody has, a negative index, the wrong key type: nothing happens, nothing throws
            noThrow("index past the end", () -> b.pasteSettings(fluidData(Fluids.WATER.getID()), 1, level, p, helper.absolutePos(bRel)));
            check(b.tank.getTankType() == Fluids.OIL, "an entry past the end changed the barrel to " + b.tank.getTankType().getUnlocalizedName() + " (:55 index < ids.length)");
            noThrow("negative index", () -> b.pasteSettings(fluidData(Fluids.WATER.getID()), -1, level, p, helper.absolutePos(bRel)));
            check(b.tank.getTankType() == Fluids.OIL, "a negative entry changed the barrel");
            noThrow("unknown id", () -> b.pasteSettings(fluidData(999_999), 0, level, p, helper.absolutePos(bRel)));
            check(b.tank.getTankType() == Fluids.OIL, "an unknown fluid id changed the barrel to " + b.tank.getTankType().getUnlocalizedName());
            CompoundTag wrong = new CompoundTag();
            wrong.putString("FluidID", "oil");
            noThrow("text instead of ids", () -> b.pasteSettings(wrong, 0, level, p, helper.absolutePos(bRel)));
            CompoundTag single = new CompoundTag();
            single.putInt("FluidID", Fluids.WATER.getID());
            noThrow("a single int", () -> b.pasteSettings(single, 0, level, p, helper.absolutePos(bRel)));
            noThrow("no key", () -> b.pasteSettings(new CompoundTag(), 0, level, p, helper.absolutePos(bRel)));
            check(b.tank.getTankType() == Fluids.OIL, "corrupted data changed the barrel to " + b.tank.getTankType().getUnlocalizedName());
            // the copy's entry picks the type
            ItemStack two = toolWith(fluidData(Fluids.WATER.getID(), Fluids.STEAM.getID()));
            setIndex(two, 1);
            pasteTo(level, p, two, helper.absolutePos(bRel), "entry 1");
            check(b.tank.getTankType() == Fluids.STEAM, "entry 1 gave " + b.tank.getTankType().getUnlocalizedName() + ", expected steam");

            // the fluid tank (a multiblock; its core)
            BlockPos tankRel = new BlockPos(8, 2, 4);
            MachineFluidTankBlockEntity tank = core(helper, tankRel, NtmBlocks.MACHINE_FLUID_TANK.get(), MachineFluidTankBlockEntity.class);
            tank.tank.setTankType(Fluids.SULFURIC_ACID);
            BlockPos tank2Rel = new BlockPos(8, 2, 10);
            MachineFluidTankBlockEntity tank2 = core(helper, tank2Rel, NtmBlocks.MACHINE_FLUID_TANK.get(), MachineFluidTankBlockEntity.class);
            tank2.tank.setTankType(Fluids.WATER);
            typeCopy(level, p, helper.absolutePos(tankRel), Fluids.SULFURIC_ACID, "fluid tank");
            ItemStack tt2 = copyFrom(level, p, helper.absolutePos(tankRel), "fluid tank");
            pasteTo(level, p, tt2, helper.absolutePos(tank2Rel), "fluid tank");
            check(tank2.tank.getTankType() == Fluids.SULFURIC_ACID, "the fluid tank took " + tank2.tank.getTankType().getUnlocalizedName());

            // the launch pad copies both of its tanks but takes no paste
            BlockPos padRel = new BlockPos(12, 2, 4);
            LaunchPadBaseBlockEntity pad = core(helper, padRel, NtmBlocks.LAUNCH_PAD.get(), LaunchPadBaseBlockEntity.class);
            pad.tanks[0].setTankType(Fluids.KEROSENE);
            pad.tanks[1].setTankType(Fluids.PEROXIDE);
            ItemStack pt = copyFrom(level, p, helper.absolutePos(padRel), "launch pad");
            check(Arrays.equals(toolData(pt).getIntArray("FluidID"), new int[] { Fluids.KEROSENE.getID(), Fluids.PEROXIDE.getID() }), "the launch pad copy holds " + Arrays.toString(toolData(pt).getIntArray("FluidID")));
            check(toolData(pt).getList("displayInfo", Tag.TAG_COMPOUND).size() == 2, "the launch pad copy has " + toolData(pt).getList("displayInfo", Tag.TAG_COMPOUND).size() + " display entries, expected 2");
            BlockPos pad2Rel = new BlockPos(12, 2, 8);
            LaunchPadBaseBlockEntity pad2 = core(helper, pad2Rel, NtmBlocks.LAUNCH_PAD.get(), LaunchPadBaseBlockEntity.class);
            pad2.tanks[0].setTankType(Fluids.NONE);
            pad2.tanks[1].setTankType(Fluids.NONE);
            pasteTo(level, p, pt, helper.absolutePos(pad2Rel), "launch pad");
            check(pad2.tanks[0].getTankType() == Fluids.NONE && pad2.tanks[1].getTankType() == Fluids.NONE, "a launch pad took a pasted fluid: " + pad2.tanks[0].getTankType().getUnlocalizedName() + " / " + pad2.tanks[1].getTankType().getUnlocalizedName());
            // its copy pastes into a barrel by entry
            setIndex(pt, 1);
            pasteTo(level, p, pt, helper.absolutePos(aRel), "launch pad copy into a barrel");
            check(a.tank.getTankType() == Fluids.PEROXIDE, "entry 1 of the launch pad copy gave " + a.tank.getTankType().getUnlocalizedName() + ", expected peroxide");
            check(p.opened.isEmpty(), "a screen opened");
        }).run();
        passed("tool_families_a").run();
        helper.succeed();
    }

    private record FamilyB(String name, Block block, Class<? extends BlockEntity> type, java.util.function.Function<BlockEntity, FluidTank[]> all, int pasteTank, boolean reach) {}

    private static List<FamilyB> familyB() {
        return List.of(
                new FamilyB("coker", NtmBlocks.MACHINE_COKER.get(), MachineCokerBlockEntity.class, be -> ((MachineCokerBlockEntity) be).tanks, 0, true),
                new FamilyB("mixer", NtmBlocks.MACHINE_MIXER.get(), MachineMixerBlockEntity.class, be -> ((MachineMixerBlockEntity) be).tanks, 2, true),
                new FamilyB("turbofan", NtmBlocks.MACHINE_TURBOFAN.get(), MachineTurbofanBlockEntity.class, be -> new FluidTank[] { ((MachineTurbofanBlockEntity) be).tank, ((MachineTurbofanBlockEntity) be).blood, ((MachineTurbofanBlockEntity) be).smoke, ((MachineTurbofanBlockEntity) be).smokeLeaded, ((MachineTurbofanBlockEntity) be).smokePoison }, 0, true),
                new FamilyB("fraction tower", NtmBlocks.MACHINE_FRACTION_TOWER.get(), MachineFractionTowerBlockEntity.class, be -> ((MachineFractionTowerBlockEntity) be).tanks, 0, false),
                new FamilyB("oilburner", NtmBlocks.HEATER_OILBURNER.get(), HeaterOilburnerBlockEntity.class, be -> new FluidTank[] { ((HeaterOilburnerBlockEntity) be).tank }, 0, false),
                new FamilyB("compressor", NtmBlocks.MACHINE_COMPRESSOR.get(), MachineCompressorBlockEntity.class, be -> ((MachineCompressorBlockEntity) be).tanks, 0, true),
                new FamilyB("combustion engine", NtmBlocks.MACHINE_COMBUSTION_ENGINE.get(), MachineCombustionEngineBlockEntity.class, be -> new FluidTank[] { ((MachineCombustionEngineBlockEntity) be).tank }, 0, true));
    }

    // IFluidCopiable.java:25-69 for the machines whose paste NEO guards (GOAL31 decision 6): coker, mixer, turbofan, compressor and combustion engine paste on the server for a player in reach (no screen open); the fraction tower
    // and the oilburner/heatex clamp their own numbers. Each family: copy and paste through the real click, an out-of-reach player pastes nothing, corrupted data (missing or mistyped keys, an unknown fluid, a negative or past-the-end entry)
    // is rejected without an exception
    @GameTest(template = TEMPLATE, batch = "hbm31d_tool_families_b", timeoutTicks = 200)
    public static void tool_families_b(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            TestPlayer p = player(helper, GameType.SURVIVAL, 0F);
            TestPlayer far = player(helper, GameType.SURVIVAL, 0F);
            for(FamilyB f : familyB()) {
                BlockPos srcRel = new BlockPos(5, 2, 4);
                BlockPos dstRel = new BlockPos(5, 2, 9);
                helper.setBlock(srcRel, Blocks.AIR.defaultBlockState());
                helper.setBlock(dstRel, Blocks.AIR.defaultBlockState());
                BlockEntity src = core(helper, srcRel, f.block(), f.type());
                BlockEntity dst = core(helper, dstRel, f.block(), f.type());
                BlockPos srcAbs = helper.absolutePos(srcRel);
                BlockPos dstAbs = helper.absolutePos(dstRel);
                String n = f.name();
                FluidTank[] sa = f.all().apply(src);
                FluidTank[] da = f.all().apply(dst);
                FluidType[] pool = { Fluids.OIL, Fluids.STEAM, Fluids.DIESEL, Fluids.KEROSENE, Fluids.HEATINGOIL };
                int[] expectedIds = new int[sa.length];
                for(int i = 0; i < sa.length; i++) {
                    sa[i].setTankType(pool[i]);
                    expectedIds[i] = pool[i].getID();
                }
                for(FluidTank t : da) t.setTankType(Fluids.NONE);
                da[f.pasteTank()].setTankType(Fluids.WATER);
                if(src instanceof MachineCompressorBlockEntity c) c.tanks[0].withPressure(2);
                if(src instanceof HeaterOilburnerBlockEntity o) {
                    o.setting = 7;
                    o.isOn = true;
                }
                if(src instanceof MachineCombustionEngineBlockEntity e) {
                    e.setting = 12;
                    e.isOn = true;
                }
                if(dst instanceof HeaterOilburnerBlockEntity o) o.setting = 1;

                ItemStack t = copyFrom(level, p, srcAbs, n);
                int[] ids = toolData(t).getIntArray("FluidID");
                check(Arrays.equals(ids, expectedIds), n + ": the copied ids are " + Arrays.toString(ids) + ", expected " + Arrays.toString(expectedIds) + " (IFluidCopiable.java:25-35: the id of every tank without the NoID trait, in tank order)");
                check(toolData(t).getList("displayInfo", Tag.TAG_COMPOUND).size() == sa.length, n + ": " + toolData(t).getList("displayInfo", Tag.TAG_COMPOUND).size() + " display entries, expected " + sa.length);

                // out of reach: the paste is refused (server only, the player must be able to use the block)
                if(f.reach()) {
                    far.moveTo(srcAbs.getX() + 60D, srcAbs.getY(), srcAbs.getZ(), 0F, 0F);
                    pasteTo(level, far, toolWith(toolData(t).copy()), dstAbs, n + " out of reach");
                    check(da[f.pasteTank()].getTankType() == Fluids.WATER, n + ": a player 60 blocks away pasted " + da[f.pasteTank()].getTankType().getUnlocalizedName());
                }

                pasteTo(level, p, t, dstAbs, n);
                check(da[f.pasteTank()].getTankType() == Fluids.OIL, n + ": the paste gave " + da[f.pasteTank()].getTankType().getUnlocalizedName() + ", expected oil");
                if(dst instanceof MachineCompressorBlockEntity c) check(c.tanks[0].getPressure() == 2, n + ": the pressure is " + c.tanks[0].getPressure() + ", expected 2");
                if(dst instanceof HeaterOilburnerBlockEntity o) check(o.setting == 7 && o.isOn, n + ": setting " + o.setting + ", on " + o.isOn + ", expected 7 / true");
                if(dst instanceof MachineCombustionEngineBlockEntity e) check(e.setting == 12 && e.isOn, n + ": burn rate " + e.setting + ", on " + e.isOn + ", expected 12 / true");
                if(sa.length > 1) {
                    da[f.pasteTank()].setTankType(Fluids.WATER);
                    ItemStack last = toolWith(toolData(t).copy());
                    setIndex(last, sa.length - 1);
                    pasteTo(level, p, last, dstAbs, n + " last entry");
                    check(da[f.pasteTank()].getTankType() == pool[sa.length - 1], n + ": entry " + (sa.length - 1) + " gave " + da[f.pasteTank()].getTankType().getUnlocalizedName() + ", expected " + pool[sa.length - 1].getUnlocalizedName());
                }
                check(p.opened.isEmpty(), n + ": a screen opened");

                // corrupted data
                CompoundTag good = toolData(t).copy();
                List<CompoundTag> bad = new ArrayList<>();
                CompoundTag noKey = good.copy();
                noKey.remove("FluidID");
                bad.add(noKey);
                CompoundTag text = good.copy();
                text.putString("FluidID", "oil");
                bad.add(text);
                CompoundTag single = good.copy();
                single.putInt("FluidID", Fluids.OIL.getID());
                bad.add(single);
                CompoundTag list = good.copy();
                list.put("FluidID", new ListTag());
                bad.add(list);
                CompoundTag empty = good.copy();
                empty.putIntArray("FluidID", new int[0]);
                bad.add(empty);
                for(int i = 0; i < bad.size(); i++) {
                    da[f.pasteTank()].setTankType(Fluids.WATER);
                    CompoundTag tag = bad.get(i);
                    noThrow(n + " bad data " + i, () -> ((ICopiable) dst).pasteSettings(tag, 0, level, p, dstAbs));
                    check(da[f.pasteTank()].getTankType() == Fluids.WATER, n + ": corrupted data " + i + " " + tag + " changed the tank to " + da[f.pasteTank()].getTankType().getUnlocalizedName());
                }
                for(int index : new int[] { -1, sa.length, sa.length + 1, Integer.MIN_VALUE, Integer.MAX_VALUE }) {
                    da[f.pasteTank()].setTankType(Fluids.WATER);
                    noThrow(n + " index " + index, () -> ((ICopiable) dst).pasteSettings(good, index, level, p, dstAbs));
                    check(da[f.pasteTank()].getTankType() == Fluids.WATER, n + ": entry " + index + " changed the tank to " + da[f.pasteTank()].getTankType().getUnlocalizedName());
                }
                da[f.pasteTank()].setTankType(Fluids.WATER);
                CompoundTag unknown = good.copy();
                unknown.putIntArray("FluidID", new int[] { 999_999 });
                noThrow(n + " unknown id", () -> ((ICopiable) dst).pasteSettings(unknown, 0, level, p, dstAbs));
                FluidType after = da[f.pasteTank()].getTankType();
                if(src instanceof MachineFractionTowerBlockEntity) check(after == Fluids.WATER || after == Fluids.NONE, n + ": an unknown fluid id gave " + after.getUnlocalizedName());
                else check(after == Fluids.WATER, n + ": an unknown fluid id gave " + after.getUnlocalizedName() + ", expected the tank untouched");
                // the extra values of the families that carry them
                if(dst instanceof MachineCompressorBlockEntity c) {
                    for(int pressure : new int[] { 5, -1, 99, Integer.MIN_VALUE }) {
                        c.tanks[0].setTankType(Fluids.WATER);
                        CompoundTag tag = good.copy();
                        tag.putInt("compression", pressure);
                        noThrow(n + " pressure " + pressure, () -> c.pasteSettings(tag, 0, level, p, dstAbs));
                        check(c.tanks[0].getTankType() == Fluids.WATER, n + ": compression " + pressure + " was pasted");
                    }
                    CompoundTag wrong = good.copy();
                    wrong.putString("compression", "2");
                    noThrow(n + " text compression", () -> c.pasteSettings(wrong, 0, level, p, dstAbs));
                    check(c.tanks[0].getTankType() == Fluids.WATER, n + ": a text compression was pasted");
                    CompoundTag edge = good.copy();
                    edge.putInt("compression", 4);
                    c.pasteSettings(edge, 0, level, p, dstAbs);
                    check(c.tanks[0].getTankType() == Fluids.OIL && c.tanks[0].getPressure() == 4, n + ": compression 4, the highest, gave " + c.tanks[0].getTankType().getUnlocalizedName() + " at " + c.tanks[0].getPressure());
                }
                if(dst instanceof MachineCombustionEngineBlockEntity e) {
                    e.tank.setTankType(Fluids.WATER);
                    e.setting = 3;
                    e.isOn = false;
                    for(int rate : new int[] { MachineCombustionEngineBlockEntity.MAX_SETTING + 1, -1, 1000, Integer.MIN_VALUE }) {
                        CompoundTag tag = good.copy();
                        tag.putInt("burnRate", rate);
                        noThrow(n + " burn rate " + rate, () -> e.pasteSettings(tag, 0, level, p, dstAbs));
                        check(e.tank.getTankType() == Fluids.WATER && e.setting == 3 && !e.isOn, n + ": burn rate " + rate + " was pasted (" + e.tank.getTankType().getUnlocalizedName() + ", " + e.setting + ", " + e.isOn + ")");
                    }
                    CompoundTag wrongRate = good.copy();
                    wrongRate.putString("burnRate", "5");
                    noThrow(n + " text burn rate", () -> e.pasteSettings(wrongRate, 0, level, p, dstAbs));
                    CompoundTag wrongOn = good.copy();
                    wrongOn.putInt("isOn", 1);
                    noThrow(n + " int isOn", () -> e.pasteSettings(wrongOn, 0, level, p, dstAbs));
                    check(e.tank.getTankType() == Fluids.WATER && e.setting == 3 && !e.isOn, n + ": a mistyped value was pasted");
                    CompoundTag edge = good.copy();
                    edge.putInt("burnRate", MachineCombustionEngineBlockEntity.MAX_SETTING);
                    e.pasteSettings(edge, 0, level, p, dstAbs);
                    check(e.setting == MachineCombustionEngineBlockEntity.MAX_SETTING && e.isOn, n + ": the highest burn rate gave " + e.setting);
                }
                if(dst instanceof HeaterOilburnerBlockEntity o) {
                    for(int[] pair : new int[][] { { 500, o.maxBurnRate }, { -5, 1 }, { 0, 1 }, { Integer.MAX_VALUE, o.maxBurnRate }, { Integer.MIN_VALUE, 1 }, { 4, 4 } }) {
                        CompoundTag tag = good.copy();
                        tag.putInt("setting", pair[0]);
                        noThrow(n + " setting " + pair[0], () -> o.pasteSettings(tag, 0, level, p, dstAbs));
                        check(o.setting == pair[1], n + ": setting " + pair[0] + " gave " + o.setting + ", expected " + pair[1] + " (clamped to 1.." + o.maxBurnRate + ")");
                    }
                    CompoundTag wrong = good.copy();
                    wrong.putString("setting", "9");
                    noThrow(n + " text setting", () -> o.pasteSettings(wrong, 0, level, p, dstAbs));
                    check(o.setting >= 1 && o.setting <= o.maxBurnRate, n + ": a text setting gave " + o.setting);
                }
                if(dst instanceof MachineFractionTowerBlockEntity) {
                    // the base of a column of towers refuses (bottom only): a tower with another tower three below does not change
                    MachineFractionTowerBlockEntity upper = core(helper, dstRel.above(3), f.block(), MachineFractionTowerBlockEntity.class);
                    upper.tanks[0].setTankType(Fluids.WATER);
                    noThrow(n + " upper tower", () -> upper.pasteSettings(good, 0, level, p, helper.absolutePos(dstRel.above(3))));
                    check(upper.tanks[0].getTankType() == Fluids.WATER, n + ": a tower above another changed its input");
                    helper.setBlock(dstRel.above(3), Blocks.AIR.defaultBlockState());
                }
                helper.setBlock(srcRel, Blocks.AIR.defaultBlockState());
                helper.setBlock(dstRel, Blocks.AIR.defaultBlockState());
            }

            // the heat exchanger carries two numbers and no fluid
            BlockPos srcRel = new BlockPos(5, 2, 4);
            BlockPos dstRel = new BlockPos(5, 2, 9);
            HeaterHeatexBlockEntity src = core(helper, srcRel, NtmBlocks.HEATER_HEATEX.get(), HeaterHeatexBlockEntity.class);
            HeaterHeatexBlockEntity dst = core(helper, dstRel, NtmBlocks.HEATER_HEATEX.get(), HeaterHeatexBlockEntity.class);
            BlockPos dstAbs = helper.absolutePos(dstRel);
            src.amountToCool = 5000;
            src.tickDelay = 7;
            ItemStack t = copyFrom(level, p, helper.absolutePos(srcRel), "heatex");
            check(toolData(t).getInt("toCool") == 5000 && toolData(t).getInt("delay") == 7, "the heatex copy holds " + toolData(t));
            pasteTo(level, p, t, dstAbs, "heatex");
            check(dst.amountToCool == 5000 && dst.tickDelay == 7, "the heatex paste gave " + dst.amountToCool + " / " + dst.tickDelay + ", expected 5000 / 7");
            int max = dst.tanks[0].getMaxFill();
            int[][] cool = { { 10_000_000, max }, { 0, 1 }, { -5, 1 }, { Integer.MAX_VALUE, max }, { Integer.MIN_VALUE, 1 }, { max, max }, { 1, 1 } };
            for(int[] pair : cool) {
                CompoundTag tag = new CompoundTag();
                tag.putInt("toCool", pair[0]);
                noThrow("toCool " + pair[0], () -> dst.pasteSettings(tag, 0, level, p, dstAbs));
                check(dst.amountToCool == pair[1], "toCool " + pair[0] + " gave " + dst.amountToCool + ", expected " + pair[1] + " (1.." + max + ")");
            }
            for(int[] pair : new int[][] { { 0, 1 }, { -9, 1 }, { Integer.MIN_VALUE, 1 }, { 12, 12 }, { Integer.MAX_VALUE, Integer.MAX_VALUE } }) {
                CompoundTag tag = new CompoundTag();
                tag.putInt("delay", pair[0]);
                noThrow("delay " + pair[0], () -> dst.pasteSettings(tag, 0, level, p, dstAbs));
                check(dst.tickDelay == pair[1], "delay " + pair[0] + " gave " + dst.tickDelay + ", expected " + pair[1]);
            }
            CompoundTag text = new CompoundTag();
            text.putString("toCool", "100");
            text.putString("delay", "100");
            noThrow("text values", () -> dst.pasteSettings(text, 0, level, p, dstAbs));
            check(dst.amountToCool >= 1 && dst.amountToCool <= max && dst.tickDelay >= 1, "text values gave " + dst.amountToCool + " / " + dst.tickDelay);
            noThrow("empty data", () -> dst.pasteSettings(new CompoundTag(), 0, level, p, dstAbs));
            helper.setBlock(srcRel, Blocks.AIR.defaultBlockState());
            helper.setBlock(dstRel, Blocks.AIR.defaultBlockState());
        }).run();
        passed("tool_families_b").run();
        helper.succeed();
    }

    // The machines with numbers of their own: HeaterElectric setting 0-10 (TileEntityHeaterElectric.java:241-243), RBMK autoloader cycle 5-95, RBMK manual rod colour, RBMK automatic rod bounds 0-100 / 0-9999 and function, battery redstone modes 0-3
    // and priority (TileEntityBatteryBase.java:259-265, which returns its data), and the paintable cable's paint; copy and paste through the real click, then out of range and mistyped values
    @GameTest(template = TEMPLATE, batch = "hbm31d_tool_families_c", timeoutTicks = 200)
    public static void tool_families_c(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            TestPlayer p = player(helper, GameType.SURVIVAL, 0F);
            BlockPos aRel = new BlockPos(4, 2, 4);
            BlockPos bRel = new BlockPos(4, 2, 9);
            BlockPos aAbs = helper.absolutePos(aRel);
            BlockPos bAbs = helper.absolutePos(bRel);

            // heater (electric)
            HeaterElectricBlockEntity ha = core(helper, aRel, NtmBlocks.HEATER_ELECTRIC.get(), HeaterElectricBlockEntity.class);
            HeaterElectricBlockEntity hb = core(helper, bRel, NtmBlocks.HEATER_ELECTRIC.get(), HeaterElectricBlockEntity.class);
            ha.setting = 6;
            ItemStack t = copyFrom(level, p, aAbs, "electric heater");
            check(toolData(t).getInt("setting") == 6, "the heater copy holds " + toolData(t));
            pasteTo(level, p, t, bAbs, "electric heater");
            check(hb.setting == 6, "the heater setting is " + hb.setting + ", expected 6");
            for(int[] pair : new int[][] { { 99, 10 }, { -3, 0 }, { Integer.MAX_VALUE, 10 }, { Integer.MIN_VALUE, 0 }, { 10, 10 }, { 0, 0 } }) {
                CompoundTag tag = new CompoundTag();
                tag.putInt("setting", pair[0]);
                noThrow("heater " + pair[0], () -> hb.pasteSettings(tag, 0, level, p, bAbs));
                check(hb.setting == pair[1], "heater setting " + pair[0] + " gave " + hb.setting + ", expected " + pair[1] + " (0..10)");
            }
            hb.setting = 4;
            CompoundTag wrong = new CompoundTag();
            wrong.putString("setting", "9");
            noThrow("heater text", () -> hb.pasteSettings(wrong, 0, level, p, bAbs));
            check(hb.setting >= 0 && hb.setting <= 10, "a text setting gave " + hb.setting);
            hb.setting = 4;
            noThrow("heater empty", () -> hb.pasteSettings(new CompoundTag(), 0, level, p, bAbs));
            check(hb.setting == 4, "an empty paste changed the heater to " + hb.setting);
            helper.setBlock(aRel, Blocks.AIR.defaultBlockState());
            helper.setBlock(bRel, Blocks.AIR.defaultBlockState());

            // RBMK autoloader
            RBMKAutoloaderBlockEntity la = core(helper, aRel, NtmBlocks.RBMK_AUTOLOADER.get(), RBMKAutoloaderBlockEntity.class);
            RBMKAutoloaderBlockEntity lb = core(helper, bRel, NtmBlocks.RBMK_AUTOLOADER.get(), RBMKAutoloaderBlockEntity.class);
            la.cycle = 33;
            t = copyFrom(level, p, aAbs, "autoloader");
            check(toolData(t).getInt("cycle") == 33, "the autoloader copy holds " + toolData(t));
            pasteTo(level, p, t, bAbs, "autoloader");
            check(lb.cycle == 33, "the autoloader cycle is " + lb.cycle);
            for(int[] pair : new int[][] { { 0, 5 }, { 200, 95 }, { -4, 5 }, { Integer.MAX_VALUE, 95 }, { Integer.MIN_VALUE, 5 }, { 5, 5 }, { 95, 95 }, { 50, 50 } }) {
                CompoundTag tag = new CompoundTag();
                tag.putInt("cycle", pair[0]);
                noThrow("cycle " + pair[0], () -> lb.pasteSettings(tag, 0, level, p, bAbs));
                check(lb.cycle == pair[1], "cycle " + pair[0] + " gave " + lb.cycle + ", expected " + pair[1] + " (5..95)");
            }
            lb.cycle = 40;
            noThrow("cycle text", () -> {
                CompoundTag tag = new CompoundTag();
                tag.putString("cycle", "20");
                lb.pasteSettings(tag, 0, level, p, bAbs);
            });
            check(lb.cycle >= 5 && lb.cycle <= 95, "a text cycle gave " + lb.cycle);
            helper.setBlock(aRel, Blocks.AIR.defaultBlockState());
            helper.setBlock(bRel, Blocks.AIR.defaultBlockState());

            // RBMK manual rod: the colour, and no colour when the copy has none
            RBMKControlManualBlockEntity ma = core(helper, aRel, NtmBlocks.RBMK_CONTROL.get(), RBMKControlManualBlockEntity.class);
            RBMKControlManualBlockEntity mb = core(helper, bRel, NtmBlocks.RBMK_CONTROL.get(), RBMKControlManualBlockEntity.class);
            ma.color = RBMKColor.GREEN;
            mb.color = RBMKColor.RED;
            t = copyFrom(level, p, aAbs, "manual rod");
            check(toolData(t).getInt("color") == RBMKColor.GREEN.ordinal(), "the rod copy holds " + toolData(t));
            pasteTo(level, p, t, bAbs, "manual rod");
            check(mb.color == RBMKColor.GREEN, "the rod colour is " + mb.color);
            ma.color = null;
            t = copyFrom(level, p, aAbs, "manual rod without colour");
            check(!toolData(t).contains("color"), "a rod with no colour copied " + toolData(t));
            pasteTo(level, p, t, bAbs, "manual rod without colour");
            check(mb.color == null, "the rod colour is " + mb.color + " after pasting no colour (the original sets null)");
            for(int color : new int[] { 99, -1, Integer.MAX_VALUE, Integer.MIN_VALUE }) {
                CompoundTag tag = new CompoundTag();
                tag.putInt("color", color);
                noThrow("colour " + color, () -> mb.pasteSettings(tag, 0, level, p, bAbs));
            }
            helper.setBlock(aRel, Blocks.AIR.defaultBlockState());
            helper.setBlock(bRel, Blocks.AIR.defaultBlockState());

            // RBMK automatic rod: a whole paste with one value outside 0-100 / 0-9999 or not finite is dropped
            RBMKControlAutoBlockEntity ra = core(helper, aRel, NtmBlocks.RBMK_CONTROL_AUTO.get(), RBMKControlAutoBlockEntity.class);
            RBMKControlAutoBlockEntity rb = core(helper, bRel, NtmBlocks.RBMK_CONTROL_AUTO.get(), RBMKControlAutoBlockEntity.class);
            ra.levelLower = 10;
            ra.levelUpper = 90;
            ra.heatLower = 200;
            ra.heatUpper = 800;
            t = copyFrom(level, p, aAbs, "automatic rod");
            pasteTo(level, p, t, bAbs, "automatic rod");
            check(rb.levelLower == 10 && rb.levelUpper == 90 && rb.heatLower == 200 && rb.heatUpper == 800, "the automatic rod took " + rb.levelLower + " / " + rb.levelUpper + " / " + rb.heatLower + " / " + rb.heatUpper);
            int functionBefore = rb.function.ordinal();
            double[][] badValues = { { 101, 90, 200, 800 }, { 10, 100.5, 200, 800 }, { 10, 90, 200, 10_000 }, { 10, 90, -1, 800 }, { Double.NaN, 90, 200, 800 }, { 10, Double.POSITIVE_INFINITY, 200, 800 }, { 10, 90, Double.NEGATIVE_INFINITY, 800 }, { 10, 90, 200, Double.NaN }, { -0.5, 90, 200, 800 } };
            String[] keys = { "levelLower", "levelUpper", "heatLower", "heatUpper" };
            for(int i = 0; i < badValues.length; i++) {
                CompoundTag tag = new CompoundTag();
                for(int k = 0; k < 4; k++) tag.putDouble(keys[k], badValues[i][k]);
                tag.putInt("function", 1);
                noThrow("automatic rod " + i, () -> rb.pasteSettings(tag, 0, level, p, bAbs));
                check(rb.levelLower == 10 && rb.levelUpper == 90 && rb.heatLower == 200 && rb.heatUpper == 800 && rb.function.ordinal() == functionBefore,
                        "automatic rod bad case " + i + " " + Arrays.toString(badValues[i]) + " changed the rod to " + rb.levelLower + " / " + rb.levelUpper + " / " + rb.heatLower + " / " + rb.heatUpper + " function " + rb.function);
            }
            CompoundTag edge = new CompoundTag();
            edge.putDouble("levelLower", 0);
            edge.putDouble("levelUpper", 100);
            edge.putDouble("heatLower", 0);
            edge.putDouble("heatUpper", 9999);
            rb.pasteSettings(edge, 0, level, p, bAbs);
            check(rb.levelLower == 0 && rb.levelUpper == 100 && rb.heatLower == 0 && rb.heatUpper == 9999, "the limits 0 / 100 / 0 / 9999 gave " + rb.levelLower + " / " + rb.levelUpper + " / " + rb.heatLower + " / " + rb.heatUpper);
            CompoundTag mistyped = new CompoundTag();
            mistyped.putString("levelLower", "5");
            noThrow("automatic rod text", () -> rb.pasteSettings(mistyped, 0, level, p, bAbs));
            noThrow("automatic rod function", () -> {
                for(int fn : new int[] { 99, -1, Integer.MIN_VALUE }) {
                    CompoundTag tag = new CompoundTag();
                    tag.putInt("function", fn);
                    rb.pasteSettings(tag, 0, level, p, bAbs);
                }
            });
            helper.setBlock(aRel, Blocks.AIR.defaultBlockState());
            helper.setBlock(bRel, Blocks.AIR.defaultBlockState());

            // battery: the modes and the priority
            BatteryBaseBlockEntity ba = core(helper, aRel, NtmBlocks.MACHINE_BATTERY_SOCKET.get(), BatteryBaseBlockEntity.class);
            BatteryBaseBlockEntity bb = core(helper, bRel, NtmBlocks.MACHINE_BATTERY_SOCKET.get(), BatteryBaseBlockEntity.class);
            ba.redLow = 3;
            ba.redHigh = 1;
            ba.priority = ba.priority.getDeclaringClass().getEnumConstants()[2];
            t = copyFrom(level, p, aAbs, "battery");
            check(toolData(t).getShort("redLow") == 3 && toolData(t).getShort("redHigh") == 1 && toolData(t).getByte("priority") == 2, "the battery copy holds " + toolData(t) + " (TileEntityBatteryBase.java:259-265 returns the data)");
            pasteTo(level, p, t, bAbs, "battery");
            check(bb.redLow == 3 && bb.redHigh == 1 && bb.priority.ordinal() == 2, "the battery took " + bb.redLow + " / " + bb.redHigh + " / " + bb.priority);
            short lowBefore = bb.redLow;
            short highBefore = bb.redHigh;
            int priorityBefore = bb.priority.ordinal();
            for(int[] pair : new int[][] { { 4, 0 }, { -1, 0 }, { 0, 4 }, { 0, -1 }, { 3, 99 }, { Short.MAX_VALUE, 0 }, { Short.MIN_VALUE, 0 } }) {
                CompoundTag tag = new CompoundTag();
                tag.putShort("redLow", (short) pair[0]);
                tag.putShort("redHigh", (short) pair[1]);
                tag.putByte("priority", (byte) 0);
                noThrow("battery " + Arrays.toString(pair), () -> bb.pasteSettings(tag, 0, level, p, bAbs));
                check(bb.redLow == lowBefore && bb.redHigh == highBefore && bb.priority.ordinal() == priorityBefore, "battery modes " + Arrays.toString(pair) + " changed the battery to " + bb.redLow + " / " + bb.redHigh + " / " + bb.priority);
            }
            CompoundTag mistypedBattery = new CompoundTag();
            mistypedBattery.putString("redLow", "9");
            mistypedBattery.putString("redHigh", "9");
            noThrow("battery text", () -> bb.pasteSettings(mistypedBattery, 0, level, p, bAbs));
            check(bb.redLow >= 0 && bb.redLow <= 3 && bb.redHigh >= 0 && bb.redHigh <= 3, "text modes gave " + bb.redLow + " / " + bb.redHigh);
            noThrow("battery priority", () -> {
                CompoundTag tag = new CompoundTag();
                tag.putByte("priority", (byte) 99);
                bb.pasteSettings(tag, 0, level, p, bAbs);
                tag.putByte("priority", (byte) -5);
                bb.pasteSettings(tag, 0, level, p, bAbs);
            });
            helper.setBlock(aRel, Blocks.AIR.defaultBlockState());
            helper.setBlock(bRel, Blocks.AIR.defaultBlockState());

            // the paintable cable: only the paint travels, and only a block allowedPaint accepts
            helper.setBlock(aRel, NtmBlocks.RED_CABLE_PAINTABLE.get().defaultBlockState());
            helper.setBlock(bRel, NtmBlocks.RED_CABLE_PAINTABLE.get().defaultBlockState());
            CablePaintableBlockEntity ca = SmokeTestSupport.blockEntity(helper, aRel, CablePaintableBlockEntity.class);
            CablePaintableBlockEntity cb = SmokeTestSupport.blockEntity(helper, bRel, CablePaintableBlockEntity.class);
            use(level, p, s(Items.STONE, 3), aAbs);
            check(ca.getPaint() != null && ca.getPaint().is(Blocks.STONE), "the cable was not painted: " + ca.getPaint());
            t = copyFrom(level, p, aAbs, "paintable cable");
            check(toolData(t).contains("paintblock", Tag.TAG_COMPOUND) && !toolData(t).contains("FluidID"), "the cable copy holds " + toolData(t));
            pasteTo(level, p, t, bAbs, "paintable cable");
            check(cb.getPaint() != null && cb.getPaint().is(Blocks.STONE), "the pasted paint is " + cb.getPaint());
            BlockPos cRel = new BlockPos(9, 2, 9);
            BlockPos cAbs = helper.absolutePos(cRel);
            helper.setBlock(cRel, NtmBlocks.RED_CABLE_PAINTABLE.get().defaultBlockState());
            cb = SmokeTestSupport.blockEntity(helper, cRel, CablePaintableBlockEntity.class);
            check(cb.getPaint() == null, "the second cable starts painted");
            for(BlockState bad : new BlockState[] { Blocks.GRASS_BLOCK.defaultBlockState(), Blocks.CHEST.defaultBlockState(), Blocks.GLASS.defaultBlockState(), NtmBlocks.RED_CABLE_PAINTABLE.get().defaultBlockState(), Blocks.AIR.defaultBlockState() }) {
                CompoundTag tag = new CompoundTag();
                tag.put("paintblock", NbtUtils.writeBlockState(bad));
                CablePaintableBlockEntity target = cb;
                noThrow("paint " + bad, () -> target.pasteSettings(tag, 0, level, p, cAbs));
                check(cb.getPaint() == null, "the paint " + bad + " was pasted: " + cb.getPaint());
            }
            CompoundTag unknownPaint = new CompoundTag();
            CompoundTag unknownState = new CompoundTag();
            unknownState.putString("Name", "hbmsntm:no_such_block");
            unknownPaint.put("paintblock", unknownState);
            CablePaintableBlockEntity target = cb;
            noThrow("unknown paint", () -> target.pasteSettings(unknownPaint, 0, level, p, cAbs));
            CompoundTag textPaint = new CompoundTag();
            textPaint.putString("paintblock", "stone");
            noThrow("text paint", () -> target.pasteSettings(textPaint, 0, level, p, cAbs));
            check(cb.getPaint() == null, "an unknown or mistyped paint left " + cb.getPaint());
            helper.setBlock(aRel, Blocks.AIR.defaultBlockState());
            helper.setBlock(bRel, Blocks.AIR.defaultBlockState());
            helper.setBlock(cRel, Blocks.AIR.defaultBlockState());
            check(p.opened.isEmpty(), "a screen opened");
        }).run();
        passed("tool_families_c").run();
        helper.succeed();
    }

    private static PipeBaseBlockEntity pipe(GameTestHelper helper, BlockPos rel, Block block, FluidType type) {
        helper.setBlock(rel, block.defaultBlockState());
        PipeBaseBlockEntity pipe = SmokeTestSupport.blockEntity(helper, rel, PipeBaseBlockEntity.class);
        pipe.setFluidType(type);
        return pipe;
    }

    // TileEntityPipeBaseNT.java:145-168 and IFluidCopiable.java:25-69 on the pipes: the pipe, the anchor and the paintable pipe copy their type (the paintable one its paint), the paste sets the type of the chosen entry, an entry past the end becomes
    // fluid 0 (:152-156), the connections of a single pasted pipe are refreshed
    @GameTest(template = TEMPLATE, batch = "hbm31d_tool_families_d", timeoutTicks = 100)
    public static void tool_families_d(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            TestPlayer p = player(helper, GameType.SURVIVAL, 0F);
            for(Block block : new Block[] { NtmBlocks.FLUID_DUCT_NEO.get(), NtmBlocks.PIPE_ANCHOR.get() }) {
                String n = block == NtmBlocks.PIPE_ANCHOR.get() ? "anchor" : "pipe";
                BlockPos aRel = new BlockPos(4, 2, 4);
                BlockPos bRel = new BlockPos(4, 2, 8);
                BlockPos bAbs = helper.absolutePos(bRel);
                PipeBaseBlockEntity a = pipe(helper, aRel, block, Fluids.WATER);
                PipeBaseBlockEntity b = pipe(helper, bRel, block, Fluids.OIL);
                ItemStack t = copyFrom(level, p, helper.absolutePos(aRel), n);
                check(Arrays.equals(toolData(t).getIntArray("FluidID"), new int[] { Fluids.WATER.getID() }), n + ": the copy holds " + Arrays.toString(toolData(t).getIntArray("FluidID")));
                check(toolData(t).getList("displayInfo", Tag.TAG_COMPOUND).size() == 1 && toolData(t).getString("tileName").equals(block.getDescriptionId()), n + ": the display entries / name are " + toolData(t));
                pasteTo(level, p, t, bAbs, n);
                check(b.getFluidType() == Fluids.WATER && a.getFluidType() == Fluids.WATER, n + ": the paste gave " + b.getFluidType().getUnlocalizedName() + ", the source " + a.getFluidType().getUnlocalizedName());

                // the entry of the copy
                ItemStack two = toolWith(fluidData(Fluids.STEAM.getID(), Fluids.OIL.getID()));
                setIndex(two, 1);
                pasteTo(level, p, two, bAbs, n + " entry 1");
                check(b.getFluidType() == Fluids.OIL, n + ": entry 1 gave " + b.getFluidType().getUnlocalizedName());
                setIndex(two, 5);
                pasteTo(level, p, two, bAbs, n + " entry 5");
                check(b.getFluidType() == Fluids.NONE, n + ": an entry past the end gave " + b.getFluidType().getUnlocalizedName() + ", expected fluid 0 (:152-156)");
                b.setFluidType(Fluids.OIL);
                setIndex(two, -3);
                pasteTo(level, p, two, bAbs, n + " entry -3");
                check(b.getFluidType() == Fluids.STEAM, n + ": a negative copyIndex gave " + b.getFluidType().getUnlocalizedName() + ", expected entry 0 (steam)");
                b.setFluidType(Fluids.OIL);
                noThrow(n + " direct -1", () -> b.pasteSettings(fluidData(Fluids.STEAM.getID()), -1, level, p, bAbs));
                check(b.getFluidType() == Fluids.NONE, n + ": a direct negative entry gave " + b.getFluidType().getUnlocalizedName() + ", expected fluid 0");
                b.setFluidType(Fluids.OIL);
                noThrow(n + " unknown id", () -> b.pasteSettings(fluidData(999_999), 0, level, p, bAbs));
                check(b.getFluidType() == Fluids.NONE || b.getFluidType() == Fluids.OIL, n + ": an unknown id gave " + b.getFluidType().getUnlocalizedName());
                b.setFluidType(Fluids.OIL);
                CompoundTag text = new CompoundTag();
                text.putString("FluidID", "water");
                noThrow(n + " text", () -> b.pasteSettings(text, 0, level, p, bAbs));
                noThrow(n + " empty", () -> b.pasteSettings(new CompoundTag(), 0, level, p, bAbs));
                check(b.getFluidType() == Fluids.OIL, n + ": corrupted data changed the type to " + b.getFluidType().getUnlocalizedName());
                helper.setBlock(aRel, Blocks.AIR.defaultBlockState());
                helper.setBlock(bRel, Blocks.AIR.defaultBlockState());
            }

            // the connections of a single pasted duct: next to a duct of the new type it connects
            BlockPos cRel = new BlockPos(9, 2, 4);
            BlockPos dRel = new BlockPos(10, 2, 4);
            PipeBaseBlockEntity c = pipe(helper, cRel, NtmBlocks.FLUID_DUCT_NEO.get(), Fluids.WATER);
            PipeBaseBlockEntity dd = pipe(helper, dRel, NtmBlocks.FLUID_DUCT_NEO.get(), Fluids.OIL);
            pasteTo(level, p, toolWith(fluidData(Fluids.WATER.getID())), helper.absolutePos(dRel), "connections");
            check(dd.getFluidType() == Fluids.WATER, "the pasted duct is " + dd.getFluidType().getUnlocalizedName());
            check(helper.getBlockState(dRel).getValue(FluidDuctConnectingBlock.WEST), "the pasted duct does not connect to the water duct beside it: " + helper.getBlockState(dRel));
            helper.setBlock(cRel, Blocks.AIR.defaultBlockState());
            helper.setBlock(dRel, Blocks.AIR.defaultBlockState());

            // the paintable pipe: the paint travels, not the fluid (FluidDuctPaintable.java:211-226)
            BlockPos eRel = new BlockPos(4, 2, 12);
            BlockPos fRel = new BlockPos(9, 2, 12);
            PipePaintableBlockEntity e = (PipePaintableBlockEntity) pipe(helper, eRel, NtmBlocks.FLUID_DUCT_PAINTABLE.get(), Fluids.WATER);
            PipePaintableBlockEntity f = (PipePaintableBlockEntity) pipe(helper, fRel, NtmBlocks.FLUID_DUCT_PAINTABLE.get(), Fluids.OIL);
            use(level, p, s(Items.OAK_PLANKS, 2), helper.absolutePos(eRel));
            check(e.getPaint() != null && e.getPaint().is(Blocks.OAK_PLANKS), "the paintable pipe was not painted: " + e.getPaint());
            ItemStack pt = copyFrom(level, p, helper.absolutePos(eRel), "paintable pipe");
            check(toolData(pt).contains("paintblock", Tag.TAG_COMPOUND) && !toolData(pt).contains("FluidID"), "the paintable pipe copy holds " + toolData(pt));
            pasteTo(level, p, pt, helper.absolutePos(fRel), "paintable pipe");
            check(f.getPaint() != null && f.getPaint().is(Blocks.OAK_PLANKS) && f.getFluidType() == Fluids.OIL, "the pasted paint is " + f.getPaint() + ", fluid " + f.getFluidType().getUnlocalizedName() + " (expected the paint, fluid unchanged)");
            // a paint the pipe does not accept, and the pipe's own block
            f.setPaint(null);
            for(BlockState bad : new BlockState[] { Blocks.GRASS_BLOCK.defaultBlockState(), Blocks.CHEST.defaultBlockState(), NtmBlocks.FLUID_DUCT_PAINTABLE.get().defaultBlockState(), Blocks.AIR.defaultBlockState() }) {
                CompoundTag tag = new CompoundTag();
                tag.put("paintblock", NbtUtils.writeBlockState(bad));
                noThrow("paint " + bad, () -> f.pasteSettings(tag, 0, level, p, helper.absolutePos(fRel)));
                check(f.getPaint() == null, "the paint " + bad + " was pasted onto the pipe");
            }
            helper.setBlock(eRel, Blocks.AIR.defaultBlockState());
            helper.setBlock(fRel, Blocks.AIR.defaultBlockState());
            check(p.opened.isEmpty(), "a screen opened");
        }).run();
        passed("tool_families_d").run();
        helper.succeed();
    }

    // DummyableBlock as ICopiable (BlockDummyable.java:ICopiable forwarding to the core): a click on a part of a multiblock that is not the core copies and pastes the core's settings
    @GameTest(template = TEMPLATE, batch = "hbm31d_tool_family_e", timeoutTicks = 100)
    public static void tool_family_e(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            TestPlayer p = player(helper, GameType.SURVIVAL, 0F);
            DummyableBlock block = (DummyableBlock) NtmBlocks.MACHINE_FLUID_TANK.get();
            BlockPos aCore = new BlockPos(5, 2, 5);
            BlockPos bCore = new BlockPos(11, 2, 11);
            SmokeTestSupport.place(helper, block, aCore, Direction.NORTH);
            SmokeTestSupport.place(helper, block, bCore, Direction.NORTH);
            MachineFluidTankBlockEntity a = SmokeTestSupport.blockEntity(helper, aCore, MachineFluidTankBlockEntity.class);
            MachineFluidTankBlockEntity b = SmokeTestSupport.blockEntity(helper, bCore, MachineFluidTankBlockEntity.class);
            a.tank.setTankType(Fluids.SULFURIC_ACID);
            b.tank.setTankType(Fluids.WATER);

            BlockPos aPart = null;
            BlockPos bPart = null;
            for(int x = -3; x <= 3; x++) for(int y = 0; y <= 3; y++) for(int z = -3; z <= 3; z++) {
                BlockPos ra = aCore.offset(x, y, z);
                BlockPos rb = bCore.offset(x, y, z);
                BlockState sa = helper.getBlockState(ra);
                BlockState sb = helper.getBlockState(rb);
                if(aPart == null && sa.is(block) && sa.getValue(DummyableBlock.TYPE) != DummyBlockType.CORE) aPart = ra;
                if(bPart == null && sb.is(block) && sb.getValue(DummyableBlock.TYPE) != DummyBlockType.CORE) bPart = rb;
            }
            check(aPart != null && bPart != null, "no part of the placed fluid tanks was found");
            check(level.getBlockEntity(helper.absolutePos(aPart)) == null, "the part " + aPart + " has a block entity of its own");
            ItemStack t = copyFrom(level, p, helper.absolutePos(aPart), "a part of the tank");
            check(Arrays.equals(toolData(t).getIntArray("FluidID"), new int[] { Fluids.SULFURIC_ACID.getID() }), "the copy through the part holds " + Arrays.toString(toolData(t).getIntArray("FluidID")));
            check(toolData(t).getString("tileName").equals(block.getDescriptionId()), "tileName is " + toolData(t).getString("tileName"));
            check(toolData(t).getList("displayInfo", Tag.TAG_COMPOUND).size() == 1, "the display entries are " + toolData(t).getList("displayInfo", Tag.TAG_COMPOUND));
            pasteTo(level, p, t, helper.absolutePos(bPart), "a part of the second tank");
            check(b.tank.getTankType() == Fluids.SULFURIC_ACID, "the second tank took " + b.tank.getTankType().getUnlocalizedName() + " through its part, expected sulfuric acid");
            check(a.tank.getTankType() == Fluids.SULFURIC_ACID, "the source tank changed");
            check(p.opened.isEmpty(), "a screen opened");
        }).run();
        passed("tool_family_e").run();
        helper.succeed();
    }

    // ================================================================ 5. TOOL_CTRL and TOOL_ALT on the pipes

    private static final FluidType W = Fluids.WATER;
    private static final FluidType S = Fluids.STEAM;
    private static final FluidType O = Fluids.OIL;

    private static PipeBaseBlockEntity[] resetRow(GameTestHelper helper, FluidType... types) {
        PipeBaseBlockEntity[] row = new PipeBaseBlockEntity[types.length];
        for(int i = 0; i < types.length; i++) {
            BlockPos rel = new BlockPos(3 + i, 2, 11);
            helper.setBlock(rel, NtmBlocks.FLUID_DUCT_NEO.get().defaultBlockState());
            row[i] = SmokeTestSupport.blockEntity(helper, rel, PipeBaseBlockEntity.class);
            row[i].setFluidType(types[i]);
        }
        return row;
    }

    private static void rowIs(PipeBaseBlockEntity[] row, String what, FluidType... expected) {
        StringBuilder got = new StringBuilder();
        boolean same = true;
        for(int i = 0; i < row.length; i++) {
            got.append(row[i].getFluidType().getUnlocalizedName()).append(' ');
            if(row[i].getFluidType() != expected[i]) same = false;
        }
        StringBuilder want = new StringBuilder();
        for(FluidType t : expected) want.append(t.getUnlocalizedName()).append(' ');
        check(same, what + ": the row is [" + got.toString().trim() + "], expected [" + want.toString().trim() + "]");
    }

    private static TestPlayer keyed(GameTestHelper helper, EnumKeybind... keys) {
        TestPlayer p = player(helper, GameType.SURVIVAL, 0F);
        for(EnumKeybind k : keys) HbmPlayerAttachments.setKeyPressed(p, k, true);
        return p;
    }

    // FluidDuctBase.java:53-102 and TileEntityPipeBaseNT.java:145-168: with TOOL_CTRL (or sneaking, for the identifier) the paste / the identifier changes the whole connected run of pipes of the clicked pipe's type (the others, and
    // pipes behind a pipe of another type, stay), without a key one pipe; with TOOL_ALT the multi identifier takes the pipe's type as its primary (only when different), the pipe stays, also on an anchor
    @GameTest(template = TEMPLATE, batch = "hbm31d_keys_ctrl_alt", timeoutTicks = 200)
    public static void keys_ctrl_alt(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos x3 = helper.absolutePos(new BlockPos(3, 2, 11));
            BlockPos x4 = helper.absolutePos(new BlockPos(4, 2, 11));
            BlockPos x5 = helper.absolutePos(new BlockPos(5, 2, 11));
            BlockPos x9 = helper.absolutePos(new BlockPos(9, 2, 11));
            ItemStack steam = toolWith(fluidData(S.getID()));

            // the settings tool without keys: one pipe
            PipeBaseBlockEntity[] row = resetRow(helper, W, W, W, W, W, O, W);
            TestPlayer plain = keyed(helper);
            pasteTo(level, plain, steam, x4, "no keys");
            rowIs(row, "tool without keys", W, S, W, W, W, O, W);

            // with TOOL_CTRL: the run of water pipes from the clicked one, up to the oil pipe
            row = resetRow(helper, W, W, W, W, W, O, W);
            pasteTo(level, keyed(helper, EnumKeybind.TOOL_CTRL), steam, x3, "tool with Ctrl");
            rowIs(row, "tool with Ctrl at the end of the run", S, S, S, S, S, O, W);
            row = resetRow(helper, W, W, W, W, W, O, W);
            pasteTo(level, keyed(helper, EnumKeybind.TOOL_CTRL), steam, x5, "tool with Ctrl in the middle");
            rowIs(row, "tool with Ctrl in the middle of the run", S, S, S, S, S, O, W);
            row = resetRow(helper, W, W, W, W, W, O, W);
            pasteTo(level, keyed(helper, EnumKeybind.TOOL_CTRL), steam, x9, "tool with Ctrl on a lone pipe");
            rowIs(row, "tool with Ctrl on the pipe behind the oil pipe", W, W, W, W, W, O, S);
            // a run of another type is not touched by a paste that finds the same type
            row = resetRow(helper, W, W, W, W, W, O, W);
            pasteTo(level, keyed(helper, EnumKeybind.TOOL_CTRL), toolWith(fluidData(W.getID())), x3, "tool with Ctrl, same type");
            rowIs(row, "tool with Ctrl pasting the type that is there", W, W, W, W, W, O, W);
            // Ctrl alone, nothing in the hand beyond the tool's own: a different key does not act like Ctrl
            row = resetRow(helper, W, W, W, W, W, O, W);
            pasteTo(level, keyed(helper, EnumKeybind.TOOL_ALT), steam, x3, "tool with Alt");
            rowIs(row, "tool with Alt (the paste is not changed by it)", S, W, W, W, W, O, W);

            // the identifier: one pipe, the run with Ctrl, the run when sneaking
            row = resetRow(helper, W, W, W, W, W, O, W);
            InteractionResult r = use(level, plain, FluidIDMultiItem.createStack(S), x3);
            check(r.consumesAction(), "the identifier on a pipe returned " + r);
            rowIs(row, "identifier without keys", S, W, W, W, W, O, W);
            row = resetRow(helper, W, W, W, W, W, O, W);
            r = use(level, keyed(helper, EnumKeybind.TOOL_CTRL), FluidIDMultiItem.createStack(S), x5);
            check(r.consumesAction(), "the identifier with Ctrl returned " + r);
            rowIs(row, "identifier with Ctrl", S, S, S, S, S, O, W);
            row = resetRow(helper, W, W, W, W, W, O, W);
            TestPlayer sneaker = keyed(helper);
            r = sneakUse(level, sneaker, FluidIDMultiItem.createStack(S), x4);
            check(r.consumesAction(), "the identifier when sneaking returned " + r);
            rowIs(row, "identifier when sneaking", S, S, S, S, S, O, W);

            // TOOL_ALT: the identifier takes the pipe's type, the pipe stays
            row = resetRow(helper, W, W, W, W, W, O, W);
            ItemStack multi = FluidIDMultiItem.createStack(O);
            r = use(level, keyed(helper, EnumKeybind.TOOL_ALT), multi, x3);
            check(r.consumesAction(), "the identifier with Alt returned " + r);
            check(FluidIDMultiItem.getType(multi, true) == W, "the identifier's primary is " + FluidIDMultiItem.getType(multi, true).getUnlocalizedName() + " after Alt on a water pipe, expected water (FluidDuctBase.java:66-75)");
            rowIs(row, "identifier with Alt", W, W, W, W, W, O, W);
            // equal types: nothing changes
            ItemStack same = FluidIDMultiItem.createStack(W);
            CompoundTag sameData = TagsUtil.getCustomData(same).copy();
            r = use(level, keyed(helper, EnumKeybind.TOOL_ALT), same, x3);
            check(!r.consumesAction(), "the identifier with Alt on a pipe of its own type returned " + r);
            check(TagsUtil.getCustomData(same).equals(sameData) && FluidIDMultiItem.getType(same, true) == W, "the identifier changed although the types are equal");
            rowIs(row, "identifier with Alt, equal types", W, W, W, W, W, O, W);
            // Ctrl and Alt together act like Alt (:89-98)
            multi = FluidIDMultiItem.createStack(S);
            r = use(level, keyed(helper, EnumKeybind.TOOL_ALT, EnumKeybind.TOOL_CTRL), multi, x4);
            check(FluidIDMultiItem.getType(multi, true) == W && r.consumesAction(), "Ctrl + Alt gave the primary " + FluidIDMultiItem.getType(multi, true).getUnlocalizedName() + " (" + r + ")");
            rowIs(row, "identifier with Ctrl and Alt", W, W, W, W, W, O, W);
            // the oil pipe gives oil
            multi = FluidIDMultiItem.createStack(W);
            use(level, keyed(helper, EnumKeybind.TOOL_ALT), multi, helper.absolutePos(new BlockPos(8, 2, 11)));
            check(FluidIDMultiItem.getType(multi, true) == O, "Alt on the oil pipe gave the primary " + FluidIDMultiItem.getType(multi, true).getUnlocalizedName());
            rowIs(row, "identifier with Alt on the oil pipe", W, W, W, W, W, O, W);
            // the secondary type stays
            multi = FluidIDMultiItem.createStack(S);
            FluidIDMultiItem.setType(multi, Fluids.DIESEL, false);
            use(level, keyed(helper, EnumKeybind.TOOL_ALT), multi, x3);
            check(FluidIDMultiItem.getType(multi, false) == Fluids.DIESEL, "Alt changed the secondary type to " + FluidIDMultiItem.getType(multi, false).getUnlocalizedName());

            // the anchor
            BlockPos anchorRel = new BlockPos(12, 2, 11);
            PipeBaseBlockEntity anchor = pipe(helper, anchorRel, NtmBlocks.PIPE_ANCHOR.get(), W);
            multi = FluidIDMultiItem.createStack(O);
            r = use(level, keyed(helper, EnumKeybind.TOOL_ALT), multi, helper.absolutePos(anchorRel));
            check(r.consumesAction() && FluidIDMultiItem.getType(multi, true) == W && anchor.getFluidType() == W, "Alt on an anchor: " + r + ", primary " + FluidIDMultiItem.getType(multi, true).getUnlocalizedName() + ", anchor " + anchor.getFluidType().getUnlocalizedName());
            ItemStack sameAnchor = FluidIDMultiItem.createStack(W);
            CompoundTag sameAnchorData = TagsUtil.getCustomData(sameAnchor).copy();
            use(level, keyed(helper, EnumKeybind.TOOL_ALT), sameAnchor, helper.absolutePos(anchorRel));
            check(TagsUtil.getCustomData(sameAnchor).equals(sameAnchorData) && anchor.getFluidType() == W, "Alt on an anchor of the identifier's own type changed something");
            // without keys the identifier sets the anchor's type; the tool with Ctrl on one anchor changes only that anchor
            use(level, plain, FluidIDMultiItem.createStack(S), helper.absolutePos(anchorRel));
            check(anchor.getFluidType() == S, "the identifier on an anchor gave " + anchor.getFluidType().getUnlocalizedName());
            pasteTo(level, keyed(helper, EnumKeybind.TOOL_CTRL), toolWith(fluidData(W.getID())), helper.absolutePos(anchorRel), "tool with Ctrl on an anchor");
            check(anchor.getFluidType() == W, "the tool with Ctrl on an anchor gave " + anchor.getFluidType().getUnlocalizedName());

            // the keys are the server's: a player who never pressed them behaves as without
            check(!com.hbm.blocks.network.FluidDuctBaseBlock.isKeyPressed(plain, EnumKeybind.TOOL_CTRL) && com.hbm.blocks.network.FluidDuctBaseBlock.isKeyPressed(keyed(helper, EnumKeybind.TOOL_CTRL), EnumKeybind.TOOL_CTRL), "isKeyPressed does not follow the attachment");
            helper.setBlock(anchorRel, Blocks.AIR.defaultBlockState());
            for(int i = 0; i < 7; i++) helper.setBlock(new BlockPos(3 + i, 2, 11), Blocks.AIR.defaultBlockState());
        }).run();
        passed("keys_ctrl_alt").run();
        helper.succeed();
    }

    // ================================================================ 6. regression: right-clicking a belt item with an inventory that fits only part (Goal 31 small fix 2)

    private static void fillInventory(Player p, int dirtInFirst) {
        p.getInventory().clearContent();
        p.getInventory().items.set(0, dirtInFirst > 0 ? s(Items.DIRT, dirtInFirst) : s(Items.STONE, 64));
        for(int i = 1; i < 36; i++) p.getInventory().items.set(i, s(Items.STONE, 64));
        p.getInventory().offhand.set(0, s(Items.STONE, 64));
    }

    // EntityMovingItem.java onRightClick (the player takes the item from the belt): what fits goes into the inventory and the rest stays on the belt, a full inventory changes nothing, a stack that fits entirely removes the entity
    @GameTest(template = TEMPLATE, batch = "hbm31d_movingitem_interact", timeoutTicks = 100)
    public static void movingitem_interact(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            TestPlayer p = player(helper, GameType.SURVIVAL, 0F);
            Vec3 at = helper.absoluteVec(new Vec3(5.5, 2.25, 5.5));

            // 60 of 64 dirt in one slot, everything else full: 4 fit
            fillInventory(p, 60);
            int before = invTotal(p);
            MovingItem e = movingAt(level, at, s(Items.DIRT, 10));
            p.interactOn(e, InteractionHand.MAIN_HAND);
            int gained = invTotal(p) - before;
            check(gained == 4, "the player gained " + gained + " items, expected 4");
            check(!e.isRemoved() && e.getItemStack().getCount() == 6, "the belt item holds " + (e.isRemoved() ? "nothing (removed)" : e.getItemStack().toString()) + ", expected 6 dirt left on the belt");
            check(p.getInventory().items.get(0).getCount() == 64, "the slot holds " + p.getInventory().items.get(0));
            check(gained + (e.isRemoved() ? 0 : e.getItemStack().getCount()) == 10, "items were lost or made: " + gained + " gained, " + e.getItemStack().getCount() + " left of 10");
            check(itemsNear(level, at, 3, Items.DIRT) == 0, "dirt was dropped as an item entity");
            e.discard();

            // a full inventory changes nothing
            fillInventory(p, 64);
            before = invTotal(p);
            e = movingAt(level, at, s(Items.DIRT, 10));
            p.interactOn(e, InteractionHand.MAIN_HAND);
            check(invTotal(p) == before && !e.isRemoved() && e.getItemStack().getCount() == 10, "a full inventory: gained " + (invTotal(p) - before) + ", the belt item holds " + (e.isRemoved() ? "nothing (removed)" : e.getItemStack().toString()) + ", expected no change");
            e.discard();

            // an empty slot too: 4 + 6 fit, the entity goes
            fillInventory(p, 60);
            p.getInventory().items.set(5, ItemStack.EMPTY);
            before = invTotal(p);
            e = movingAt(level, at, s(Items.DIRT, 10));
            p.interactOn(e, InteractionHand.MAIN_HAND);
            check(invTotal(p) - before == 10, "the player gained " + (invTotal(p) - before) + " items, expected all 10");
            check(e.isRemoved(), "the belt item was left although everything fitted");
            check(p.getInventory().items.get(0).getCount() == 64 && p.getInventory().items.get(5).is(Items.DIRT) && p.getInventory().items.get(5).getCount() == 6, "the dirt went to " + p.getInventory().items.get(0) + " / " + p.getInventory().items.get(5));

            // a different item that does not match any slot, one empty slot: it fills the empty slot
            fillInventory(p, 64);
            p.getInventory().items.set(7, ItemStack.EMPTY);
            before = invTotal(p);
            e = movingAt(level, at, s(Items.SAND, 40));
            p.interactOn(e, InteractionHand.MAIN_HAND);
            check(invTotal(p) - before == 40 && e.isRemoved() && p.getInventory().items.get(7).is(Items.SAND), "40 sand into the one empty slot: gained " + (invTotal(p) - before));
            check(itemsNear(level, at, 3, Items.SAND) == 0, "sand was dropped as an item entity");
            clearEntities(helper);
        }).run();
        passed("movingitem_interact").run();
        helper.succeed();
    }

    // ================================================================ 7. the recipes

    private static ShapedRecipe toolRecipe(GameTestHelper helper, String path, Item result, int w, int h, String original) {
        ServerLevel level = helper.getLevel();
        RecipeHolder<?> holder = level.getRecipeManager().byKey(id(path)).orElse(null);
        check(holder != null, "recipe " + id(path) + " is not loaded (" + original + ")");
        check(holder.value() instanceof ShapedRecipe, path + " is " + holder.value().getClass().getSimpleName() + ", expected a shaped recipe (" + original + ")");
        ShapedRecipe recipe = (ShapedRecipe) holder.value();
        check(recipe.getWidth() == w && recipe.getHeight() == h, path + " is " + recipe.getWidth() + "x" + recipe.getHeight() + ", expected " + w + "x" + h + " (" + original + ")");
        ItemStack out = recipe.getResultItem(level.registryAccess());
        check(out.is(result) && out.getCount() == 1, path + " yields " + out + ", expected 1 x " + result + " (" + original + ")");
        return recipe;
    }

    private static boolean toolMatches(GameTestHelper helper, ShapedRecipe recipe, int w, int h, ItemStack... cells) {
        List<ItemStack> grid = new ArrayList<>();
        for(ItemStack c : cells) grid.add(c == null ? ItemStack.EMPTY : c);
        return recipe.matches(CraftingInput.of(w, h, grid), helper.getLevel());
    }

    /** The full pattern matches and assembles the result; dirt in any cell and anything in an empty cell breaks it. */
    private static void toolGrid(GameTestHelper helper, String path, ShapedRecipe recipe, Item result, int w, int h, String original, ItemStack... cells) {
        check(cells.length == w * h, "the test lists " + cells.length + " cells for " + w + "x" + h);
        check(toolMatches(helper, recipe, w, h, cells), path + " does not match its own pattern (" + original + ")");
        List<ItemStack> grid = new ArrayList<>();
        for(ItemStack c : cells) grid.add(c == null ? ItemStack.EMPTY : c);
        ItemStack crafted = recipe.assemble(CraftingInput.of(w, h, grid), helper.getLevel().registryAccess());
        check(crafted.is(result) && crafted.getCount() == 1, path + " crafts " + crafted + ", expected 1 x " + result);
        for(int i = 0; i < cells.length; i++) {
            ItemStack[] bad = cells.clone();
            bad[i] = s(Items.DIRT, 1);
            check(!toolMatches(helper, recipe, w, h, bad), path + " matches with dirt in cell " + i + " (" + original + ")");
        }
        for(int i = 0; i < cells.length; i++) {
            if(cells[i] != null) continue;
            ItemStack[] extra = cells.clone();
            extra[i] = s(NtmItems.PLATE_POLYMER.get(), 1);
            check(!toolMatches(helper, recipe, w, h, extra), path + " matches with an item in its empty cell " + i);
        }
    }

    private static ItemStack hydraulic() {
        return MetaHelper.newStack(NtmItems.PART_GENERIC.get(), 1, PartGenericItem.Type.PISTON_HYDRAULIC);
    }

    private static ItemStack electric() {
        return MetaHelper.newStack(NtmItems.PART_GENERIC.get(), 1, PartGenericItem.Type.PISTON_ELECTRIC);
    }

    // CraftingManager.java:886: crane_router from "PIP" / "ICI" / "PIP" with pneumatic pistons, polymer plates (plate_polymer) and an integrated circuit board (EnumCircuitType.BASIC)
    @GameTest(template = TEMPLATE, batch = "hbm31d_recipe_crane_router", timeoutTicks = 100)
    public static void recipe_crane_router(GameTestHelper helper) {
        guard(() -> {
            String original = "CraftingManager.java:886";
            Item result = routerBlock().asItem();
            ShapedRecipe r = toolRecipe(helper, "crane_router", result, 3, 3, original);
            ItemStack i = s(NtmItems.PLATE_POLYMER.get(), 1);
            ItemStack c = s(NtmItems.CIRCUIT_INTEGRATED_BOARD.get(), 1);
            ItemStack[] grid = { pneumatic(), i, pneumatic(), i, c, i, pneumatic(), i, pneumatic() };
            toolGrid(helper, "crane_router", r, result, 3, 3, original, grid);
            for(int cell : new int[] { 0, 2, 6, 8 }) {
                for(ItemStack bad : new ItemStack[] { hydraulic(), electric(), s(Items.PISTON, 1), s(Items.STICKY_PISTON, 1) }) {
                    ItemStack[] g = grid.clone();
                    g[cell] = bad;
                    check(!toolMatches(helper, r, 3, 3, g), "crane_router accepts " + bad + " in cell " + cell + " (:886 pneumatic only)");
                }
            }
            for(int cell : new int[] { 1, 3, 5, 7 }) {
                for(ItemStack bad : new ItemStack[] { s(NtmItems.PLATE_IRON.get(), 1), s(NtmItems.INGOT_STEEL.get(), 1) }) {
                    ItemStack[] g = grid.clone();
                    g[cell] = bad;
                    check(!toolMatches(helper, r, 3, 3, g), "crane_router accepts " + bad + " in the plate cell " + cell);
                }
            }
            for(ItemStack bad : new ItemStack[] { s(NtmItems.CIRCUIT_VACUUM_TUBE.get(), 1), s(NtmItems.CIRCUIT_ANALOG_BOARD.get(), 1), s(NtmItems.CIRCUIT_MICROCHIP.get(), 1) }) {
                ItemStack[] g = grid.clone();
                g[4] = bad;
                check(!toolMatches(helper, r, 3, 3, g), "crane_router accepts " + bad + " as the circuit (:886 BASIC)");
            }
        }).run();
        passed("recipe_crane_router").run();
        helper.succeed();
    }

    // CraftingManager.java:887: crane_splitter from "III" / "PCP" / "III" with steel ingots, pneumatic pistons and a vacuum tube
    @GameTest(template = TEMPLATE, batch = "hbm31d_recipe_crane_splitter", timeoutTicks = 100)
    public static void recipe_crane_splitter(GameTestHelper helper) {
        guard(() -> {
            String original = "CraftingManager.java:887";
            Item result = splitterBlock().asItem();
            ShapedRecipe r = toolRecipe(helper, "crane_splitter", result, 3, 3, original);
            ItemStack i = s(NtmItems.INGOT_STEEL.get(), 1);
            ItemStack c = s(NtmItems.CIRCUIT_VACUUM_TUBE.get(), 1);
            ItemStack[] grid = { i, i, i, pneumatic(), c, pneumatic(), i, i, i };
            toolGrid(helper, "crane_splitter", r, result, 3, 3, original, grid);
            for(int cell : new int[] { 3, 5 }) {
                for(ItemStack bad : new ItemStack[] { hydraulic(), electric(), s(Items.PISTON, 1) }) {
                    ItemStack[] g = grid.clone();
                    g[cell] = bad;
                    check(!toolMatches(helper, r, 3, 3, g), "crane_splitter accepts " + bad + " in cell " + cell + " (:887 pneumatic only)");
                }
            }
            for(int cell : new int[] { 0, 1, 2, 6, 7, 8 }) {
                for(ItemStack bad : new ItemStack[] { s(Items.IRON_INGOT, 1), s(NtmItems.PLATE_IRON.get(), 1) }) {
                    ItemStack[] g = grid.clone();
                    g[cell] = bad;
                    check(!toolMatches(helper, r, 3, 3, g), "crane_splitter accepts " + bad + " in the steel cell " + cell);
                }
            }
            for(ItemStack bad : new ItemStack[] { s(NtmItems.CIRCUIT_INTEGRATED_BOARD.get(), 1), s(NtmItems.CIRCUIT_ANALOG_BOARD.get(), 1), s(NtmItems.CIRCUIT_MICROCHIP.get(), 1) }) {
                ItemStack[] g = grid.clone();
                g[4] = bad;
                check(!toolMatches(helper, r, 3, 3, g), "crane_splitter accepts " + bad + " as the circuit (:887 VACUUM_TUBE)");
            }
        }).run();
        passed("recipe_crane_splitter").run();
        helper.succeed();
    }

    // CraftingManager.java:888: crane_partitioner from " M " / "BCB" (3 wide, 2 high) with a microchip (EnumCircuitType.CHIP), two regular conveyor wands and a steel crate
    @GameTest(template = TEMPLATE, batch = "hbm31d_recipe_crane_partitioner", timeoutTicks = 100)
    public static void recipe_crane_partitioner(GameTestHelper helper) {
        guard(() -> {
            String original = "CraftingManager.java:888";
            Item result = partitionerBlock().asItem();
            ShapedRecipe r = toolRecipe(helper, "crane_partitioner", result, 3, 2, original);
            ItemStack m = s(NtmItems.CIRCUIT_MICROCHIP.get(), 1);
            ItemStack crate = s(NtmBlocks.CRATE_STEEL.get().asItem(), 1);
            ItemStack[] grid = { null, m, null, wand(), crate, wand() };
            toolGrid(helper, "crane_partitioner", r, result, 3, 2, original, grid);
            for(int cell : new int[] { 3, 5 }) {
                for(ConveyorType type : new ConveyorType[] { ConveyorType.EXPRESS, ConveyorType.DOUBLE, ConveyorType.TRIPLE }) {
                    ItemStack[] g = grid.clone();
                    g[cell] = MetaHelper.newStack(NtmItems.CONVEYOR_WAND.get(), 1, type);
                    check(!toolMatches(helper, r, 3, 2, g), "crane_partitioner accepts a " + type + " wand in cell " + cell + " (:888 the regular type)");
                }
            }
            for(ItemStack bad : new ItemStack[] { s(Items.CHEST, 1), s(Items.BARREL, 1), s(Items.IRON_BLOCK, 1) }) {
                ItemStack[] g = grid.clone();
                g[4] = bad;
                check(!toolMatches(helper, r, 3, 2, g), "crane_partitioner accepts " + bad + " for the steel crate");
            }
            for(ItemStack bad : new ItemStack[] { s(NtmItems.CIRCUIT_INTEGRATED_BOARD.get(), 1), s(NtmItems.CIRCUIT_VACUUM_TUBE.get(), 1), s(NtmItems.CIRCUIT_ANALOG_BOARD.get(), 1) }) {
                ItemStack[] g = grid.clone();
                g[1] = bad;
                check(!toolMatches(helper, r, 3, 2, g), "crane_partitioner accepts " + bad + " as the chip (:888 CHIP)");
            }
            // the shape: the chip must be above the crate
            ItemStack[] flipped = { wand(), crate, wand(), null, m, null };
            check(!toolMatches(helper, r, 3, 2, flipped), "crane_partitioner matches upside down");
            ItemStack[] shifted = { null, null, m, wand(), crate, wand() };
            check(!toolMatches(helper, r, 3, 2, shifted), "crane_partitioner matches with the chip off the centre");
        }).run();
        passed("recipe_crane_partitioner").run();
        helper.succeed();
    }

    // ToolRecipes.java:124: settings_tool from " P " / "PCP" / "III" with iron plates, an analog circuit board and polymer plates
    @GameTest(template = TEMPLATE, batch = "hbm31d_recipe_settings_tool", timeoutTicks = 100)
    public static void recipe_settings_tool(GameTestHelper helper) {
        guard(() -> {
            String original = "ToolRecipes.java:124";
            Item result = NtmItems.SETTINGS_TOOL.get();
            ShapedRecipe r = toolRecipe(helper, "settings_tool", result, 3, 3, original);
            ItemStack plate = s(NtmItems.PLATE_IRON.get(), 1);
            ItemStack c = s(NtmItems.CIRCUIT_ANALOG_BOARD.get(), 1);
            ItemStack poly = s(NtmItems.PLATE_POLYMER.get(), 1);
            ItemStack[] grid = { null, plate, null, plate, c, plate, poly, poly, poly };
            toolGrid(helper, "settings_tool", r, result, 3, 3, original, grid);
            for(int cell : new int[] { 1, 3, 5 }) {
                for(ItemStack bad : new ItemStack[] { s(NtmItems.PLATE_POLYMER.get(), 1), s(Items.IRON_INGOT, 1), s(NtmItems.INGOT_STEEL.get(), 1) }) {
                    ItemStack[] g = grid.clone();
                    g[cell] = bad;
                    check(!toolMatches(helper, r, 3, 3, g), "settings_tool accepts " + bad + " in the iron plate cell " + cell);
                }
            }
            for(int cell : new int[] { 6, 7, 8 }) {
                for(ItemStack bad : new ItemStack[] { s(NtmItems.PLATE_IRON.get(), 1), s(Items.IRON_INGOT, 1) }) {
                    ItemStack[] g = grid.clone();
                    g[cell] = bad;
                    check(!toolMatches(helper, r, 3, 3, g), "settings_tool accepts " + bad + " in the polymer cell " + cell);
                }
            }
            for(ItemStack bad : new ItemStack[] { s(NtmItems.CIRCUIT_INTEGRATED_BOARD.get(), 1), s(NtmItems.CIRCUIT_VACUUM_TUBE.get(), 1), s(NtmItems.CIRCUIT_MICROCHIP.get(), 1) }) {
                ItemStack[] g = grid.clone();
                g[4] = bad;
                check(!toolMatches(helper, r, 3, 3, g), "settings_tool accepts " + bad + " as the circuit (ToolRecipes.java:124 ANALOG)");
            }
            ItemStack[] flipped = { poly, poly, poly, plate, c, plate, null, plate, null };
            check(!toolMatches(helper, r, 3, 3, flipped), "settings_tool matches upside down");
        }).run();
        passed("recipe_settings_tool").run();
        helper.succeed();
    }
}
