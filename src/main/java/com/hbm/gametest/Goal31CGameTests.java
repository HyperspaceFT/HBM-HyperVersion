package com.hbm.gametest;

import api.hbm.conveyor.IConveyorBelt;
import com.hbm.blockentity.machine.MachineElectricFurnaceBlockEntity;
import com.hbm.blockentity.network.CraneBaseBlockEntity;
import com.hbm.blockentity.network.CraneBoxerBlockEntity;
import com.hbm.blockentity.network.CraneExtractorBlockEntity;
import com.hbm.blockentity.network.CraneGrabberBlockEntity;
import com.hbm.blockentity.network.CraneInserterBlockEntity;
import com.hbm.blockentity.network.CraneUnboxerBlockEntity;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.network.ConveyorBaseBlock;
import com.hbm.blocks.network.ConveyorBlock;
import com.hbm.blocks.network.ConveyorBlock.Shape;
import com.hbm.blocks.network.CraneBaseBlock;
import com.hbm.blocks.network.CraneBoxerBlock;
import com.hbm.blocks.network.CraneInserterBlock;
import com.hbm.blocks.network.CraneUnboxerBlock;
import com.hbm.config.NtmConfig;
import com.hbm.entity.NtmEntityTypes;
import com.hbm.entity.item.MovingItem;
import com.hbm.entity.item.MovingPackage;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.menus.CraneBoxerMenu;
import com.hbm.inventory.menus.CraneGrabberMenu;
import com.hbm.inventory.menus.CraneUnboxerMenu;
import com.hbm.items.NtmItems;
import com.hbm.items.PartGenericItem;
import com.hbm.items.tools.ConveyorWandItem.ConveyorType;
import com.hbm.main.NuclearTechMod;
import com.hbm.network.toserver.CompoundTagControl;
import com.hbm.registry.NtmSoundEvents;
import com.mojang.authlib.GameProfile;
import com.mojang.logging.LogUtils;
import io.netty.buffer.Unpooled;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTest;
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
import net.minecraft.world.damagesource.DamageSource;
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
import net.minecraft.world.level.block.HopperBlock;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
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
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.OptionalInt;
import java.util.Set;
import java.util.UUID;
import java.util.function.Consumer;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal31C: the conveyor grabber, boxer and unboxer, the package entity, the inserter receiving real packages, the
 * three menus, copy / paste, the item capability and the five recipes. Same template and conventions as {@link Goal31BGameTests}; every
 * test has its own batch.
 * <p>
 * Expected values come from the ORIGINAL at cd0cff450, cited beside each group of checks (TileEntityCraneGrabber.java:35,54-267;
 * CraneGrabber.java:45-49; TileEntityCraneBoxer.java:23-27,41-209; CraneBoxer.java:53-104; TileEntityCraneUnboxer.java:30-108;
 * CraneUnboxer.java:86-128; EntityMovingPackage.java:20-132; CraneInserter.java:148-196; ContainerCraneGrabber.java:17-108;
 * BlockConveyorBase.java:90-108; CraftingManager.java:867-880,884-885), not from the NEO implementation. Test areas lie millions of
 * blocks out, so no position or direction is computed by subtracting floats; every coordinate goes through the helper's integer offset.
 * <p>
 * Real classes and state: the registered crane blocks and block entities, real belts, the real MovingItem and MovingPackage entities
 * (ticked by the world in the flow tests), vanilla chests and hoppers, the electric furnace, the real menus, CompoundTagControl.apply
 * with mock players, Capabilities.ItemHandler.BLOCK queries, NBT save / load and the RecipeManager with real CraftingInput grids. The
 * rhythm of a crane is asserted on block entities that the test itself ticks ({@code updateEntity()}, never added to the level) so that
 * a try happens on a named tick of the world time; the grabber's cooldown is asserted relative to {@code lastGrabbedTick}, never to an
 * absolute game time. Placed cranes show that the world ticks them too.
 * Not evidence: rendering (models, textures, arrows, the package's look and size), screens and their text, JEI drag and drop, sound
 * audibility, the client-side prediction of phantom clicks, other mods' pipes, multiplayer (the package is not synced), a dedicated server
 * with real players, saved worlds, and 1.7.10 itself.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class Goal31CGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-31c]";

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

    private static Block grabberBlock() {
        return NtmBlocks.CRANE_GRABBER.get();
    }

    private static Block boxerBlock() {
        return NtmBlocks.CRANE_BOXER.get();
    }

    private static Block unboxerBlock() {
        return NtmBlocks.CRANE_UNBOXER.get();
    }

    private static Block inserterBlock() {
        return NtmBlocks.CRANE_INSERTER.get();
    }

    private static BlockState crane(Block block, Direction input, Direction output) {
        return block.defaultBlockState().setValue(CraneBaseBlock.INPUT, input).setValue(CraneBaseBlock.OUTPUT, output);
    }

    private static <T extends BlockEntity> T placeCrane(GameTestHelper helper, BlockPos rel, Block block, Direction input, Direction output, Class<T> type) {
        helper.setBlock(rel, crane(block, input, output));
        return SmokeTestSupport.blockEntity(helper, rel, type);
    }

    /** A block entity the test ticks itself: it is never added to the level, so the world does not tick it. */
    private static CraneGrabberBlockEntity detachedGrabber(GameTestHelper helper, BlockPos rel, Direction input, Direction output) {
        CraneGrabberBlockEntity be = new CraneGrabberBlockEntity(helper.absolutePos(rel), crane(grabberBlock(), input, output));
        be.setLevel(helper.getLevel());
        return be;
    }

    private static CraneBoxerBlockEntity detachedBoxer(GameTestHelper helper, BlockPos rel, Direction input, Direction output) {
        CraneBoxerBlockEntity be = new CraneBoxerBlockEntity(helper.absolutePos(rel), crane(boxerBlock(), input, output));
        be.setLevel(helper.getLevel());
        return be;
    }

    private static CraneUnboxerBlockEntity detachedUnboxer(GameTestHelper helper, BlockPos rel, Direction input, Direction output) {
        CraneUnboxerBlockEntity be = new CraneUnboxerBlockEntity(helper.absolutePos(rel), crane(unboxerBlock(), input, output));
        be.setLevel(helper.getLevel());
        return be;
    }

    private static BlockState belt(Block block, Direction input) {
        return block.defaultBlockState().setValue(ConveyorBaseBlock.HORIZONTAL_FACING, input).setValue(ConveyorBlock.SHAPE, Shape.STRAIGHT);
    }

    /** A regular straight belt; {@code input} is the side items come from, they travel the other way. */
    private static BlockState beltState(Direction input) {
        return belt(NtmBlocks.CONVEYOR.get(), input);
    }

    private static Container chest(GameTestHelper helper, BlockPos rel) {
        helper.setBlock(rel, Blocks.CHEST.defaultBlockState());
        Container c = (Container) helper.getBlockEntity(rel);
        c.clearContent();
        return c;
    }

    private static Container containerAt(GameTestHelper helper, BlockPos rel) {
        BlockEntity be = helper.getBlockEntity(rel);
        check(be instanceof Container, "no container at " + rel + ": " + be);
        return (Container) be;
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

    private static int total(Container c, int from, int to) {
        int n = 0;
        for(int i = from; i < to; i++) n += c.getItem(i).getCount();
        return n;
    }

    private static void fill(Container c, Item item, int count) {
        for(int i = 0; i < c.getContainerSize(); i++) c.setItem(i, s(item, count));
    }

    /** Item entities of the given item in the whole test area (drops only). */
    private static int dropped(GameTestHelper helper, Item item) {
        int n = 0;
        for(ItemEntity e : helper.getLevel().getEntitiesOfClass(ItemEntity.class, helper.getBounds())) if(e.getItem().is(item)) n += e.getItem().getCount();
        return n;
    }

    /** Items of the given kind as drops, riding belts, or boxed in a package, in the whole test area. */
    private static int loose(GameTestHelper helper, Item item) {
        int n = dropped(helper, item);
        for(MovingItem e : helper.getLevel().getEntitiesOfClass(MovingItem.class, helper.getBounds())) if(e.getItemStack().is(item)) n += e.getItemStack().getCount();
        for(MovingPackage e : helper.getLevel().getEntitiesOfClass(MovingPackage.class, helper.getBounds())) {
            for(ItemStack stack : e.getItemStacks()) if(stack.is(item)) n += stack.getCount();
        }
        return n;
    }

    private static void clearEntities(GameTestHelper helper) {
        for(ItemEntity e : helper.getLevel().getEntitiesOfClass(ItemEntity.class, helper.getBounds())) e.discard();
        for(MovingItem e : helper.getLevel().getEntitiesOfClass(MovingItem.class, helper.getBounds())) e.discard();
        for(MovingPackage e : helper.getLevel().getEntitiesOfClass(MovingPackage.class, helper.getBounds())) e.discard();
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

    private static ItemStack ejectorUpgrade(int tier) {
        return switch(tier) {
            case 1 -> s(NtmItems.UPGRADE_EJECTOR_1.get(), 1);
            case 2 -> s(NtmItems.UPGRADE_EJECTOR_2.get(), 1);
            case 3 -> s(NtmItems.UPGRADE_EJECTOR_3.get(), 1);
            default -> ItemStack.EMPTY;
        };
    }

    private static ItemStack stackUpgrade(int tier) {
        return switch(tier) {
            case 1 -> s(NtmItems.UPGRADE_STACK_1.get(), 1);
            case 2 -> s(NtmItems.UPGRADE_STACK_2.get(), 1);
            case 3 -> s(NtmItems.UPGRADE_STACK_3.get(), 1);
            default -> ItemStack.EMPTY;
        };
    }

    /** The middle of a cell at the height a belt carries items: the bottom centre of an entity standing there is 0.3 above the cell's floor. */
    private static Vec3 cellCentre(GameTestHelper helper, BlockPos rel) {
        BlockPos a = helper.absolutePos(rel);
        return new Vec3(a.getX() + 0.5, a.getY() + 0.3, a.getZ() + 0.5);
    }

    private static MovingItem movingAt(ServerLevel level, Vec3 at, ItemStack stack) {
        MovingItem e = new MovingItem(NtmEntityTypes.MOVING_ITEM.get(), level);
        e.setPos(at.x, at.y, at.z);
        e.setItemStack(stack);
        level.addFreshEntity(e);
        return e;
    }

    private static MovingPackage packageAt(ServerLevel level, Vec3 at, ItemStack... stacks) {
        MovingPackage e = new MovingPackage(NtmEntityTypes.MOVING_PACKAGE.get(), level);
        e.setPos(at.x, at.y, at.z);
        e.setItemStacks(stacks);
        level.addFreshEntity(e);
        return e;
    }

    private static List<MovingPackage> packagesIn(GameTestHelper helper, BlockPos cellRel) {
        return helper.getLevel().getEntitiesOfClass(MovingPackage.class, new AABB(helper.absolutePos(cellRel)));
    }

    private static List<MovingItem> movingIn(GameTestHelper helper, BlockPos cellRel) {
        return helper.getLevel().getEntitiesOfClass(MovingItem.class, new AABB(helper.absolutePos(cellRel)));
    }

    private static int remaining(List<MovingItem> items) {
        int n = 0;
        for(MovingItem e : items) if(!e.isRemoved()) n += e.getItemStack().getCount();
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

    private static void setFilter(CraneGrabberBlockEntity be, int slot, ItemStack stack, @Nullable String mode) {
        be.slots.set(slot, stack.copyWithCount(1));
        be.matcher.modes[slot] = mode;
    }

    private static int invTotal(Player p) {
        int n = 0;
        for(ItemStack st : p.getInventory().items) n += st.getCount();
        return n;
    }

    // ---------------------------------------------------------------- 1. the grabber

    /**
     * A grabber the test ticks itself with its input cell {@code in} and output cell {@code out}. Tries are made eligible by moving
     * {@code lastGrabbedTick} back relative to the current world time.
     */
    private static final class GRig {
        final GameTestHelper helper;
        final CraneGrabberBlockEntity be;
        final BlockPos rel;
        final BlockPos in;
        final BlockPos out;

        GRig(GameTestHelper helper, BlockPos rel, Direction input, Direction output) {
            this.helper = helper;
            this.rel = rel;
            this.in = rel.relative(input);
            this.out = rel.relative(output);
            this.be = detachedGrabber(helper, rel, input, output);
            this.ready();
        }

        long now() {
            return this.helper.getLevel().getGameTime();
        }

        /** A try is due: more than any delay has passed since the last grab. */
        void ready() {
            this.be.lastGrabbedTick = this.now() - 1000;
        }

        GRig stackUpgrade(int tier) {
            this.be.slots.set(CraneGrabberBlockEntity.SLOT_STACK_UPGRADE, Goal31CGameTests.stackUpgrade(tier));
            return this;
        }

        GRig ejectorUpgrade(int tier) {
            this.be.slots.set(CraneGrabberBlockEntity.SLOT_EJECTOR_UPGRADE, Goal31CGameTests.ejectorUpgrade(tier));
            return this;
        }

        MovingItem item(ItemStack stack) {
            return movingAt(this.helper.getLevel(), cellCentre(this.helper, this.in), stack);
        }

        MovingItem itemAt(double dx, double dz, ItemStack stack) {
            Vec3 c = cellCentre(this.helper, this.in);
            return movingAt(this.helper.getLevel(), c.add(dx, 0, dz), stack);
        }

        void tick() {
            this.be.updateEntity();
        }
    }

    // TileEntityCraneGrabber.java:71-79,171-182: the amount per try into an inventory is 1 / 4 / 16 / 64 (stack upgrade none / 1 / 2 / 3), never more than the stack
    // holds or the target takes, and the belt's stack shrinks by what went in; a vanilla chest and a NEO machine (the electric furnace's input slot)
    @GameTest(template = TEMPLATE, batch = "hbm31c_grabber_amount", timeoutTicks = 100)
    public static void grabber_amount(GameTestHelper helper) {
        guard(() -> {
            int[] amounts = { 1, 4, 16, 64 };
            for(int tier = 0; tier < 4; tier++) {
                String ctx = "stack upgrade " + tier;
                GRig g = new GRig(helper, new BlockPos(8, 2, 1 + 2 * tier), Direction.EAST, Direction.WEST).stackUpgrade(tier);
                check(g.be.getAmount() == amounts[tier], ctx + ": getAmount is " + g.be.getAmount() + ", expected " + amounts[tier] + " (:71-79)");
                Container chest = chest(helper, g.out);
                MovingItem item = g.item(s(Items.STONE, 64));
                long t = g.now();
                g.tick();
                check(count(chest, Items.STONE) == amounts[tier], ctx + " into a chest: " + count(chest, Items.STONE) + " stone arrived, expected " + amounts[tier]);
                if(tier == 3) check(item.isRemoved(), ctx + ": the belt's stack of 64 was taken whole but the entity stays (:178-180)");
                else check(!item.isRemoved() && item.getItemStack().getCount() == 64 - amounts[tier], ctx + ": the belt's stack is " + (item.isRemoved() ? "gone" : item.getItemStack().getCount()) + ", expected " + (64 - amounts[tier]) + " (:176)");
                check(g.be.lastGrabbedTick == t, ctx + ": lastGrabbedTick is " + (g.be.lastGrabbedTick - t) + " ticks from the try, expected 0 (:169)");
                item.discard();
            }

            for(int tier = 0; tier < 4; tier++) {
                String ctx = "stack upgrade " + tier + " into the electric furnace";
                GRig g = new GRig(helper, new BlockPos(8, 2, 9 + 2 * tier), Direction.EAST, Direction.WEST).stackUpgrade(tier);
                helper.setBlock(g.out, NtmBlocks.MACHINE_ELECTRIC_FURNACE.get().defaultBlockState());
                MachineElectricFurnaceBlockEntity machine = SmokeTestSupport.blockEntity(helper, g.out, MachineElectricFurnaceBlockEntity.class);
                MovingItem item = g.item(s(Items.RAW_IRON, 64));
                g.tick();
                ItemStack in = machine.getItem(MachineElectricFurnaceBlockEntity.SLOT_INPUT);
                check(in.is(Items.RAW_IRON) && in.getCount() == amounts[tier], ctx + ": the input slot holds " + in + ", expected " + amounts[tier] + " raw iron");
                check(machine.getItem(MachineElectricFurnaceBlockEntity.SLOT_OUTPUT).isEmpty() && machine.getItem(MachineElectricFurnaceBlockEntity.SLOT_BATTERY).isEmpty(), ctx + ": another slot took an item");
                if(tier == 3) check(item.isRemoved(), ctx + ": the stack of 64 was taken whole but the entity stays");
                else check(!item.isRemoved() && item.getItemStack().getCount() == 64 - amounts[tier], ctx + ": the belt's stack is " + (item.isRemoved() ? "gone" : item.getItemStack().getCount()) + ", expected " + (64 - amounts[tier]));
                item.discard();
            }

            // a stack smaller than the amount: only what the stack holds, and the entity is gone (:172,178-180)
            GRig small = new GRig(helper, new BlockPos(2, 2, 2), Direction.EAST, Direction.WEST).stackUpgrade(3);
            Container smallChest = chest(helper, small.out);
            MovingItem three = small.item(s(Items.DIRT, 3));
            small.tick();
            check(count(smallChest, Items.DIRT) == 3 && three.isRemoved(), "a stack of 3 with the amount 64: the chest holds " + count(smallChest, Items.DIRT) + " dirt, entity removed " + three.isRemoved());

            // a target with room for 5 only: what went in is taken from the belt, the rest stays (:175-176 didAdd)
            GRig tight = new GRig(helper, new BlockPos(2, 2, 5), Direction.EAST, Direction.WEST).stackUpgrade(3);
            Container tightChest = chest(helper, tight.out);
            fill(tightChest, Items.COBBLESTONE, 64);
            tightChest.setItem(26, s(Items.STONE, 59));
            MovingItem stone = tight.item(s(Items.STONE, 64));
            tight.tick();
            check(count(tightChest, Items.STONE) == 64 && !stone.isRemoved() && stone.getItemStack().getCount() == 59, "a chest with room for 5: it holds " + count(tightChest, Items.STONE) + " stone, the belt's stack is " + (stone.isRemoved() ? "gone" : stone.getItemStack().getCount()) + ", expected 64 and 59");
        }).run();
        passed("grabber_amount").run();
        helper.succeed();
    }

    // TileEntityCraneGrabber.java:157-186: the amount of one try is spread over the moving items in reach, each taking at most what is left of it; which entity is visited
    // first is not defined (the entity list's order), so only the totals are asserted
    @GameTest(template = TEMPLATE, batch = "hbm31c_grabber_spread", timeoutTicks = 100)
    public static void grabber_spread(GameTestHelper helper) {
        guard(() -> {
            // [stack upgrade tier, amount, stack sizes]
            int[][] cases = { { 0, 1, 3, 3, 3 }, { 1, 4, 3, 3, 3 }, { 2, 16, 5, 5, 5, 5, 5 }, { 3, 64, 20, 20, 20, 20 }, { 1, 4, 1, 1, 1, 1, 1, 1 } };
            for(int k = 0; k < cases.length; k++) {
                int[] c = cases[k];
                GRig g = new GRig(helper, new BlockPos(8, 2, 1 + 3 * k), Direction.EAST, Direction.WEST).stackUpgrade(c[0]);
                Container chest = chest(helper, g.out);
                List<MovingItem> items = new ArrayList<>();
                int sum = 0;
                for(int i = 2; i < c.length; i++) {
                    items.add(g.itemAt(-0.2 + 0.08 * (i - 2), 0.05 * (i - 2) - 0.1, s(Items.STONE, c[i])));
                    sum += c[i];
                }
                g.tick();
                String ctx = "case " + k + " (amount " + c[1] + ", " + (c.length - 2) + " stacks)";
                int expect = Math.min(c[1], sum);
                check(count(chest, Items.STONE) == expect, ctx + ": the chest holds " + count(chest, Items.STONE) + " stone, expected " + expect + " (:157-186)");
                check(remaining(items) == sum - expect, ctx + ": " + remaining(items) + " stone are left on the belt, expected " + (sum - expect));
                for(MovingItem e : items) check(e.isRemoved() || e.getItemStack().getCount() > 0, ctx + ": an empty stack stays on the belt");
                check(g.be.lastGrabbedTick == g.now(), ctx + ": the cooldown did not start");
            }

            // different items in one try: the total is the amount, whatever order
            GRig mixed = new GRig(helper, new BlockPos(2, 2, 2), Direction.EAST, Direction.WEST).stackUpgrade(1);
            Container mixedChest = chest(helper, mixed.out);
            List<MovingItem> mix = new ArrayList<>();
            mix.add(mixed.itemAt(-0.2, 0, s(Items.STONE, 2)));
            mix.add(mixed.itemAt(0, 0, s(Items.DIRT, 1)));
            mix.add(mixed.itemAt(0.2, 0, s(Items.GRAVEL, 5)));
            mixed.tick();
            check(total(mixedChest) == 4 && remaining(mix) == 4, "mixed stacks with the amount 4: the chest holds " + total(mixedChest) + " items, the belt " + remaining(mix) + ", expected 4 and 4");

            // the target takes only part of what is offered: the rest of the amount goes on to the next stack (:182 amount -= didAdd)
            GRig tight = new GRig(helper, new BlockPos(2, 2, 8), Direction.EAST, Direction.WEST).stackUpgrade(2);
            Container tightChest = chest(helper, tight.out);
            fill(tightChest, Items.COBBLESTONE, 64);
            tightChest.setItem(25, s(Items.STONE, 62));
            tightChest.setItem(26, ItemStack.EMPTY);
            List<MovingItem> two = new ArrayList<>();
            two.add(tight.itemAt(-0.1, 0, s(Items.STONE, 5)));
            two.add(tight.itemAt(0.1, 0, s(Items.STONE, 5)));
            tight.tick();
            check(count(tightChest, Items.STONE) == 62 + 10 && remaining(two) == 0, "a chest with room for 66: it holds " + count(tightChest, Items.STONE) + " stone, the belt " + remaining(two) + ", expected 72 and 0");
        }).run();
        passed("grabber_spread").run();
        helper.succeed();
    }

    // TileEntityCraneGrabber.java:85-123: onto an output belt the first matching moving item goes over as a whole stack, one per try, at the snapping point 0.55 blocks
    // toward the output side (BlockConveyorBase.java:90-108); the stack upgrade does not apply; a stack of 0 is removed and starts no cooldown (:105-108)
    @GameTest(template = TEMPLATE, batch = "hbm31c_grabber_belt_transfer", timeoutTicks = 100)
    public static void grabber_belt_transfer(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            GRig g = new GRig(helper, new BlockPos(8, 2, 8), Direction.EAST, Direction.WEST).stackUpgrade(3).ejectorUpgrade(0);
            helper.setBlock(g.out, beltState(Direction.SOUTH));
            Vec3 expected = helper.absoluteVec(new Vec3(7.5, 2.25, 8.5));

            MovingItem a = g.itemAt(-0.1, 0, s(Items.STONE, 64));
            MovingItem b = g.itemAt(0.1, 0, s(Items.DIRT, 10));
            long t = g.now();
            g.tick();
            List<MovingItem> onBelt = movingIn(helper, g.out);
            check(onBelt.size() == 1, onBelt.size() + " moving items stand on the output belt after one try, expected 1 (:122 break)");
            MovingItem moved = onBelt.get(0);
            boolean stone = moved.getItemStack().is(Items.STONE);
            check(stone ? moved.getItemStack().getCount() == 64 : moved.getItemStack().is(Items.DIRT) && moved.getItemStack().getCount() == 10, "the moved stack is " + moved.getItemStack() + ", expected the whole stack of 64 stone or 10 dirt (:118)");
            check(near(moved.position(), expected, 1e-9), "the moved item stands at " + fmt(moved.position()) + ", expected " + fmt(expected) + " (:115-119 snapping point of the output cell)");
            check((stone ? a : b).isRemoved() && !(stone ? b : a).isRemoved(), "the source entity of the moved stack was not removed, or the other one was (:120)");
            check(g.be.lastGrabbedTick == t, "the cooldown did not start on the belt grab (:113)");

            // the next try (cooldown over) moves the other one
            g.ready();
            g.tick();
            check(movingIn(helper, g.out).size() == 2 && a.isRemoved() && b.isRemoved(), "the second try left " + movingIn(helper, g.out).size() + " items on the belt");

            // a stack of 0 is removed without moving anything and without a cooldown
            for(MovingItem e : movingIn(helper, g.out)) e.discard();
            g.ready();
            long before = g.be.lastGrabbedTick;
            MovingItem empty = g.item(ItemStack.EMPTY);
            g.tick();
            check(empty.isRemoved() && movingIn(helper, g.out).isEmpty() && g.be.lastGrabbedTick == before, "an empty moving item: removed " + empty.isRemoved() + ", belt " + movingIn(helper, g.out).size() + ", cooldown started " + (g.be.lastGrabbedTick != before) + " (:105-108)");

            // the same into an inventory (:161-164)
            GRig inv = new GRig(helper, new BlockPos(8, 2, 3), Direction.EAST, Direction.WEST);
            chest(helper, inv.out);
            long invBefore = inv.be.lastGrabbedTick;
            MovingItem empty2 = inv.item(ItemStack.EMPTY);
            inv.tick();
            check(empty2.isRemoved() && inv.be.lastGrabbedTick == invBefore, "an empty moving item at an inventory: removed " + empty2.isRemoved() + ", cooldown started " + (inv.be.lastGrabbedTick != invBefore));
            check(level.getBlockState(helper.absolutePos(g.out)).getBlock() instanceof IConveyorBelt, "the output belt vanished");
        }).run();
        passed("grabber_belt_transfer").run();
        helper.succeed();
    }

    // TileEntityCraneGrabber.java:35,110-111,209-220: blacklist by default, an empty filter in a blacklist grabs everything and in a whitelist nothing, a whitelist needs
    // a match, a blacklist a mismatch, any of the nine slots matches, exact / wildcard / tag modes; an item that is skipped starts no cooldown
    @GameTest(template = TEMPLATE, batch = "hbm31c_grabber_filter", timeoutTicks = 100)
    public static void grabber_filter(GameTestHelper helper) {
        guard(() -> {
            GRig g = new GRig(helper, new BlockPos(8, 2, 8), Direction.EAST, Direction.WEST);
            Container chest = chest(helper, g.out);
            check(!g.be.isWhitelist, "a new grabber is a whitelist (:35 isWhitelist = false)");

            // a: empty blacklist grabs everything
            MovingItem nugget = g.item(s(Items.GOLD_NUGGET, 1));
            g.tick();
            check(count(chest, Items.GOLD_NUGGET) == 1 && nugget.isRemoved(), "a: an empty blacklist did not grab (the chest holds " + count(chest, Items.GOLD_NUGGET) + ")");

            // b: blacklist of dirt (exact): dirt stays and starts no cooldown, stone goes
            chest.clearContent();
            setFilter(g.be, 3, s(Items.DIRT, 1), "exact");
            g.ready();
            long before = g.be.lastGrabbedTick;
            MovingItem dirt = g.item(s(Items.DIRT, 1));
            g.tick();
            check(!dirt.isRemoved() && total(chest) == 0 && g.be.lastGrabbedTick == before, "b: a blacklisted dirt was grabbed (chest " + total(chest) + "), or started the cooldown (:111 continue before :113)");
            MovingItem stone = g.item(s(Items.STONE, 1));
            g.tick();
            check(count(chest, Items.STONE) == 1 && stone.isRemoved() && !dirt.isRemoved() && count(chest, Items.DIRT) == 0, "b: with a blacklist of dirt the chest holds " + count(chest, Items.STONE) + " stone and " + count(chest, Items.DIRT) + " dirt");
            dirt.discard();

            // c: both in one try: whatever order, only the stone is taken
            chest.clearContent();
            g.ready();
            MovingItem d2 = g.itemAt(-0.1, 0, s(Items.DIRT, 1));
            MovingItem s2 = g.itemAt(0.1, 0, s(Items.STONE, 1));
            g.tick();
            check(count(chest, Items.STONE) == 1 && count(chest, Items.DIRT) == 0 && s2.isRemoved() && !d2.isRemoved(), "c: dirt and stone in one try: the chest holds " + count(chest, Items.STONE) + " stone and " + count(chest, Items.DIRT) + " dirt");
            d2.discard();

            // d: an empty whitelist grabs nothing and starts no cooldown
            g.be.slots.set(3, ItemStack.EMPTY);
            g.be.matcher.modes[3] = null;
            g.be.isWhitelist = true;
            chest.clearContent();
            g.ready();
            before = g.be.lastGrabbedTick;
            MovingItem any = g.item(s(Items.STONE, 1));
            g.tick();
            check(!any.isRemoved() && total(chest) == 0 && g.be.lastGrabbedTick == before, "d: an empty whitelist grabbed or started the cooldown (:110 whitelist && !match)");
            any.discard();

            // e: a whitelist of stone in slot 8 (wildcard) grabs stone, not dirt; the same in slot 0
            for(int slot : new int[] { 8, 0 }) {
                for(int i = 0; i < 9; i++) {
                    g.be.slots.set(i, ItemStack.EMPTY);
                    g.be.matcher.modes[i] = null;
                }
                setFilter(g.be, slot, s(Items.STONE, 1), "wildcard");
                chest.clearContent();
                g.ready();
                MovingItem notListed = g.item(s(Items.DIRT, 1));
                g.tick();
                check(!notListed.isRemoved() && total(chest) == 0, "e: slot " + slot + ": a dirt passed a whitelist of stone");
                notListed.discard();
                MovingItem listed = g.item(s(Items.STONE, 1));
                g.tick();
                check(listed.isRemoved() && count(chest, Items.STONE) == 1, "e: slot " + slot + ": a stone was not grabbed by a whitelist of stone (:209-220 any slot)");
            }

            // f: exact distinguishes the type component, wildcard does not
            Item part = NtmItems.PART_GENERIC.get();
            for(int i = 0; i < 9; i++) {
                g.be.slots.set(i, ItemStack.EMPTY);
                g.be.matcher.modes[i] = null;
            }
            setFilter(g.be, 1, MetaHelper.newStack(part, 1, PartGenericItem.Type.PISTON_PNEUMATIC), "exact");
            chest.clearContent();
            g.ready();
            MovingItem hydraulic = g.item(MetaHelper.newStack(part, 1, PartGenericItem.Type.PISTON_HYDRAULIC));
            g.tick();
            check(!hydraulic.isRemoved() && total(chest) == 0, "f: a whitelist of the pneumatic piston (exact) grabbed the hydraulic one");
            hydraulic.discard();
            MovingItem pneumatic = g.item(MetaHelper.newStack(part, 1, PartGenericItem.Type.PISTON_PNEUMATIC));
            g.tick();
            check(pneumatic.isRemoved() && total(chest) == 1, "f: a whitelist of the pneumatic piston (exact) did not grab the pneumatic piston");
            g.be.matcher.modes[1] = "wildcard";
            chest.clearContent();
            g.ready();
            MovingItem hydraulic2 = g.item(MetaHelper.newStack(part, 1, PartGenericItem.Type.PISTON_HYDRAULIC));
            g.tick();
            check(hydraulic2.isRemoved() && total(chest) == 1, "f: wildcard mode did not grab another type of the same item");

            // g: a tag mode: the oak log filter in the logs tag grabs a spruce log
            for(int i = 0; i < 9; i++) {
                g.be.slots.set(i, ItemStack.EMPTY);
                g.be.matcher.modes[i] = null;
            }
            setFilter(g.be, 4, s(Items.OAK_LOG, 1), "minecraft:logs");
            chest.clearContent();
            g.ready();
            MovingItem spruce = g.item(s(Items.SPRUCE_LOG, 1));
            g.tick();
            check(spruce.isRemoved() && count(chest, Items.SPRUCE_LOG) == 1, "g: a spruce log was not grabbed by a whitelist of the logs tag");

            // h: the same rules onto an output belt: blacklist of dirt moves the stone, leaves the dirt
            GRig b = new GRig(helper, new BlockPos(8, 2, 13), Direction.EAST, Direction.WEST);
            helper.setBlock(b.out, beltState(Direction.SOUTH));
            setFilter(b.be, 0, s(Items.DIRT, 1), "exact");
            MovingItem bd = b.itemAt(-0.1, 0, s(Items.DIRT, 4));
            MovingItem bs = b.itemAt(0.1, 0, s(Items.STONE, 4));
            b.tick();
            check(!bd.isRemoved() && bs.isRemoved() && movingIn(helper, b.out).size() == 1 && movingIn(helper, b.out).get(0).getItemStack().is(Items.STONE), "h: a blacklist of dirt on a belt output did not move exactly the stone");
        }).run();
        passed("grabber_filter").run();
        helper.succeed();
    }

    // TileEntityCraneGrabber.java:59-69: a try is made once the world time has reached lastGrabbedTick + delay (20, with the ejector upgrade 10 / 5 / 2); asserted relative to
    // the last grab, not to the absolute time. :113,169 the cooldown starts when an item is picked, before the target's answer; :137 without a belt or inventory on the
    // output side nothing is picked
    @GameTest(template = TEMPLATE, batch = "hbm31c_grabber_cooldown", timeoutTicks = 100)
    public static void grabber_cooldown(GameTestHelper helper) {
        guard(() -> {
            int[] delays = { 20, 10, 5, 2 };
            for(int tier = 0; tier < 4; tier++) {
                int d = delays[tier];
                String ctx = "ejector upgrade " + tier + " (delay " + d + ")";
                GRig g = new GRig(helper, new BlockPos(8, 2, 1 + 2 * tier), Direction.EAST, Direction.WEST).ejectorUpgrade(tier);
                check(g.be.getDelay() == d, ctx + ": getDelay is " + g.be.getDelay() + " (:59-67)");
                Container chest = chest(helper, g.out);
                long now = g.now();
                g.be.lastGrabbedTick = now - d + 1;
                MovingItem early = g.item(s(Items.STONE, 1));
                g.tick();
                check(!early.isRemoved() && total(chest) == 0 && g.be.lastGrabbedTick == now - d + 1, ctx + ": a try " + (d - 1) + " ticks after the last grab grabbed (:69 now >= last + delay)");
                g.be.lastGrabbedTick = now - d;
                g.tick();
                check(early.isRemoved() && count(chest, Items.STONE) == 1 && g.be.lastGrabbedTick == now, ctx + ": a try " + d + " ticks after the last grab did not grab (chest " + total(chest) + ", lastGrabbedTick " + (g.be.lastGrabbedTick - now) + " from now)");
                MovingItem again = g.item(s(Items.STONE, 1));
                g.tick();
                check(!again.isRemoved() && total(chest) == 1, ctx + ": a second try on the same tick grabbed again");
                again.discard();
            }

            // a full target: the item is picked, nothing goes in, the cooldown starts anyway (:113,169)
            GRig full = new GRig(helper, new BlockPos(2, 2, 2), Direction.EAST, Direction.WEST);
            Container fullChest = chest(helper, full.out);
            fill(fullChest, Items.COBBLESTONE, 64);
            long t = full.now();
            MovingItem blocked = full.item(s(Items.STONE, 5));
            full.tick();
            check(!blocked.isRemoved() && blocked.getItemStack().getCount() == 5 && count(fullChest, Items.STONE) == 0, "a full chest took stone");
            check(full.be.lastGrabbedTick == t, "a full target did not start the cooldown (lastGrabbedTick " + (full.be.lastGrabbedTick - t) + " from now)");

            // a machine that rejects the item is a target too: dirt is no smeltable input (:137 te instanceof IInventory)
            GRig machine = new GRig(helper, new BlockPos(2, 2, 5), Direction.EAST, Direction.WEST);
            helper.setBlock(machine.out, NtmBlocks.MACHINE_ELECTRIC_FURNACE.get().defaultBlockState());
            long t2 = machine.now();
            MovingItem rejected = machine.item(s(Items.DIRT, 5));
            machine.tick();
            check(!rejected.isRemoved() && rejected.getItemStack().getCount() == 5 && machine.be.lastGrabbedTick == t2, "a rejecting machine: the stack is " + rejected.getItemStack() + ", the cooldown started " + (machine.be.lastGrabbedTick == t2));

            // nothing usable on the output side: no item is picked and no cooldown starts (:137)
            for(int k = 0; k < 2; k++) {
                GRig none = new GRig(helper, new BlockPos(2, 2, 8 + 3 * k), Direction.EAST, Direction.WEST);
                helper.setBlock(none.out, k == 0 ? Blocks.STONE.defaultBlockState() : Blocks.AIR.defaultBlockState());
                long before = none.be.lastGrabbedTick;
                MovingItem stays = none.item(s(Items.STONE, 5));
                none.tick();
                check(!stays.isRemoved() && stays.getItemStack().getCount() == 5 && none.be.lastGrabbedTick == before, (k == 0 ? "a stone block" : "air") + " on the output side: the item was touched, or the cooldown started (:137)");
            }

            // an output belt with nothing in reach: no cooldown (the loop finds no item)
            GRig quiet = new GRig(helper, new BlockPos(12, 2, 2), Direction.EAST, Direction.WEST);
            helper.setBlock(quiet.out, beltState(Direction.SOUTH));
            long before = quiet.be.lastGrabbedTick;
            quiet.tick();
            check(quiet.be.lastGrabbedTick == before && movingIn(helper, quiet.out).isEmpty(), "a try with nothing in reach started the cooldown");
        }).run();
        passed("grabber_cooldown").run();
        helper.succeed();
    }

    // TileEntityCraneGrabber.java:69: a redstone signal on the grabber stops it
    @GameTest(template = TEMPLATE, batch = "hbm31c_grabber_redstone", timeoutTicks = 100)
    public static void grabber_redstone(GameTestHelper helper) {
        guard(() -> {
            GRig g = new GRig(helper, new BlockPos(8, 2, 8), Direction.EAST, Direction.WEST);
            Container chest = chest(helper, g.out);
            helper.setBlock(g.rel.above(), Blocks.REDSTONE_BLOCK.defaultBlockState());
            check(helper.getLevel().hasNeighborSignal(g.be.getBlockPos()), "the redstone block does not power the grabber");
            long before = g.be.lastGrabbedTick;
            MovingItem item = g.item(s(Items.STONE, 1));
            g.tick();
            check(!item.isRemoved() && total(chest) == 0 && g.be.lastGrabbedTick == before, "a powered grabber grabbed or started the cooldown (:69)");
            helper.setBlock(g.rel.above(), Blocks.AIR.defaultBlockState());
            check(!helper.getLevel().hasNeighborSignal(g.be.getBlockPos()), "the grabber is still powered");
            g.tick();
            check(item.isRemoved() && count(chest, Items.STONE) == 1, "the grabber did not grab once the signal ended");

            // the belt output obeys the signal too
            GRig b = new GRig(helper, new BlockPos(8, 2, 3), Direction.EAST, Direction.WEST);
            helper.setBlock(b.out, beltState(Direction.SOUTH));
            helper.setBlock(b.rel.above(), Blocks.REDSTONE_BLOCK.defaultBlockState());
            MovingItem bi = b.item(s(Items.STONE, 1));
            b.tick();
            check(!bi.isRemoved() && movingIn(helper, b.out).isEmpty(), "a powered grabber moved an item onto the belt");
        }).run();
        passed("grabber_redstone").run();
        helper.succeed();
    }

    /** Whether the grabber at (8, 4, 8) with the given input side grabs an iron nugget whose bottom centre is at {@code itemRel} (relative coordinates). */
    private static boolean reaches(GameTestHelper helper, Direction input, BlockState lane, Vec3 itemRel) {
        BlockPos g = new BlockPos(8, 4, 8);
        for(Direction d : Direction.values()) helper.setBlock(g.relative(d), Blocks.AIR.defaultBlockState());
        helper.setBlock(g.relative(input), lane);
        Container chest = chest(helper, g.relative(input.getOpposite()));
        CraneGrabberBlockEntity be = detachedGrabber(helper, g, input, input.getOpposite());
        be.lastGrabbedTick = helper.getLevel().getGameTime() - 1000;
        MovingItem item = movingAt(helper.getLevel(), helper.absoluteVec(itemRel), s(Items.IRON_NUGGET, 1));
        be.updateEntity();
        boolean got = count(chest, Items.IRON_NUGGET) == 1;
        item.discard();
        return got;
    }

    private static void expectReach(GameTestHelper helper, String ctx, Direction input, BlockState lane, double x, double y, double z, boolean expected, String why) {
        boolean got = reaches(helper, input, lane, new Vec3(x, y, z));
        check(got == expected, ctx + ": an item at (" + x + ", " + y + ", " + z + ") was " + (got ? "grabbed" : "not grabbed") + ", expected " + (expected ? "grabbed" : "not grabbed") + " (" + why + ")");
    }

    // TileEntityCraneGrabber.java:88-99,145-155: the box is the input cell shrunk by 0.1875 on every side; a double belt in front of a horizontal input moves it 0.5 blocks
    // toward the grabber (only the near lane is reached), a triple belt 0.33; the shifted box reaches into the grabber's own cell (:139-144); with the input up or down the
    // lane correction is skipped (:89 getBlockMetadata() > 1). An entity is 0.375 wide and tall and is grabbed when its box touches the grabber's box.
    @GameTest(template = TEMPLATE, batch = "hbm31c_grabber_reach", timeoutTicks = 200)
    public static void grabber_reach(GameTestHelper helper) {
        guard(() -> {
            BlockState single = beltState(Direction.SOUTH);
            BlockState dbl = belt(NtmBlocks.CONVEYOR_DOUBLE.get(), Direction.SOUTH);
            BlockState tpl = belt(NtmBlocks.CONVEYOR_TRIPLE.get(), Direction.SOUTH);
            Direction e = Direction.EAST;

            // single belt, input EAST: the box is x 9.1875-9.8125, y 4.1875-4.8125, z 8.1875-8.8125
            String c = "single belt";
            expectReach(helper, c, e, single, 9.5, 4.3, 8.5, true, "the middle");
            expectReach(helper, c, e, single, 9.25, 4.3, 8.5, true, "near side");
            expectReach(helper, c, e, single, 9.9, 4.3, 8.5, true, "an entity box touching the far side of the box");
            expectReach(helper, c, e, single, 10.05, 4.3, 8.5, false, "past the far side");
            expectReach(helper, c, e, single, 9.5, 4.3, 9.2, false, "outside in z");
            expectReach(helper, c, e, single, 9.5, 4.3, 7.8, false, "outside in z, other side");
            expectReach(helper, c, e, single, 9.5, 4.9, 8.5, false, "above the box");
            expectReach(helper, c, e, single, 8.5, 4.3, 8.5, false, "inside the grabber's own cell without a lane correction");

            // double belt, input EAST: the box moves to x 8.6875-9.3125; the lanes are 0.25 and 0.75 into the cell
            c = "double belt";
            expectReach(helper, c, e, dbl, 9.25, 4.3, 8.5, true, "near lane, :91 reach 0.5");
            expectReach(helper, c, e, dbl, 9.75, 4.3, 8.5, false, "far lane");
            expectReach(helper, c, e, dbl, 8.8, 4.3, 8.5, true, "inside the grabber's own cell, the box reaches 0.31 into it (:139-144)");
            expectReach(helper, c, e, dbl, 8.4, 4.3, 8.5, false, "too far into the grabber's cell");
            // the other horizontal directions: the lanes lie across the input direction
            expectReach(helper, c + " input NORTH", Direction.NORTH, belt(NtmBlocks.CONVEYOR_DOUBLE.get(), Direction.EAST), 8.5, 4.3, 7.75, true, "near lane");
            expectReach(helper, c + " input NORTH", Direction.NORTH, belt(NtmBlocks.CONVEYOR_DOUBLE.get(), Direction.EAST), 8.5, 4.3, 7.25, false, "far lane");
            expectReach(helper, c + " input SOUTH", Direction.SOUTH, belt(NtmBlocks.CONVEYOR_DOUBLE.get(), Direction.EAST), 8.5, 4.3, 9.25, true, "near lane");
            expectReach(helper, c + " input SOUTH", Direction.SOUTH, belt(NtmBlocks.CONVEYOR_DOUBLE.get(), Direction.EAST), 8.5, 4.3, 9.75, false, "far lane");
            expectReach(helper, c + " input WEST", Direction.WEST, belt(NtmBlocks.CONVEYOR_DOUBLE.get(), Direction.SOUTH), 7.75, 4.3, 8.5, true, "near lane");
            expectReach(helper, c + " input WEST", Direction.WEST, belt(NtmBlocks.CONVEYOR_DOUBLE.get(), Direction.SOUTH), 7.25, 4.3, 8.5, false, "far lane");

            // triple belt, input EAST: the box moves to x 8.5175-9.1475; the lanes are 0.1875, 0.5 and 0.8125 into the cell
            c = "triple belt";
            expectReach(helper, c, e, tpl, 9.1875, 4.3, 8.5, true, "near lane, :92 reach 0.33");
            expectReach(helper, c, e, tpl, 9.5, 4.3, 8.5, false, "middle lane");
            expectReach(helper, c, e, tpl, 9.8125, 4.3, 8.5, false, "far lane");
            expectReach(helper, c, e, tpl, 8.6, 4.3, 8.5, true, "inside the grabber's own cell, 0.48 into it: the feed-from-the-side oddity of :139-144");
            expectReach(helper, c, e, tpl, 8.3, 4.3, 8.5, false, "too far into the grabber's cell");
            expectReach(helper, c + " input WEST", Direction.WEST, belt(NtmBlocks.CONVEYOR_TRIPLE.get(), Direction.SOUTH), 7.8125, 4.3, 8.5, true, "near lane");
            expectReach(helper, c + " input WEST", Direction.WEST, belt(NtmBlocks.CONVEYOR_TRIPLE.get(), Direction.SOUTH), 7.5, 4.3, 8.5, false, "middle lane");
            expectReach(helper, c + " input WEST", Direction.WEST, belt(NtmBlocks.CONVEYOR_TRIPLE.get(), Direction.SOUTH), 7.1875, 4.3, 8.5, false, "far lane");

            // input UP / DOWN: no lane correction, the box stays the cell shrunk by 0.1875 (an item at y 5.5 is outside a box shifted half a block down, at 3.3 outside one shifted up)
            for(BlockState lane : new BlockState[] { dbl, tpl }) {
                String laneName = lane.getBlock() == NtmBlocks.CONVEYOR_DOUBLE.get() ? "double" : "triple";
                for(double x : new double[] { 8.25, 8.5, 8.75 }) {
                    expectReach(helper, "input UP, " + laneName + " belt", Direction.UP, lane, x, 5.5, 8.5, true, ":89 the correction applies to horizontal inputs only");
                    expectReach(helper, "input DOWN, " + laneName + " belt", Direction.DOWN, lane, x, 3.3, 8.5, true, ":89 the correction applies to horizontal inputs only");
                }
            }
            expectReach(helper, "input UP, single belt", Direction.UP, single, 8.5, 5.5, 8.5, true, "reference");
            expectReach(helper, "input UP", Direction.UP, single, 8.5, 4.3, 8.5, false, "the grabber's own cell is not part of the box");
        }).run();
        passed("grabber_reach").run();
        helper.succeed();
    }

    // TileEntityCraneGrabber.java:99,155: only moving items are looked for, never packages
    @GameTest(template = TEMPLATE, batch = "hbm31c_grabber_packages", timeoutTicks = 100)
    public static void grabber_packages(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            for(int k = 0; k < 2; k++) {
                GRig g = new GRig(helper, new BlockPos(8, 2, 3 + 5 * k), Direction.EAST, Direction.WEST);
                Container chest = null;
                if(k == 0) chest = chest(helper, g.out);
                else helper.setBlock(g.out, beltState(Direction.SOUTH));
                String ctx = k == 0 ? "into a chest" : "onto a belt";
                long before = g.be.lastGrabbedTick;
                MovingPackage pack = packageAt(level, cellCentre(helper, g.in), s(Items.STONE, 5), s(Items.DIRT, 3));
                g.tick();
                check(!pack.isRemoved() && pack.getItemStacks().length == 2 && pack.getItemStacks()[0].getCount() == 5, ctx + ": the package was touched");
                check(g.be.lastGrabbedTick == before, ctx + ": a package alone started the cooldown");
                check(k == 1 ? movingIn(helper, g.out).isEmpty() : total(chest) == 0, ctx + ": something arrived at the output");
                MovingItem item = g.item(s(Items.GOLD_NUGGET, 1));
                g.tick();
                check(item.isRemoved() && !pack.isRemoved() && pack.getItemStacks().length == 2, ctx + ": with an item next to it, the item " + (item.isRemoved() ? "was" : "was not") + " grabbed and the package " + (pack.isRemoved() ? "was" : "was not") + " removed");
                check(k == 1 ? movingIn(helper, g.out).size() == 1 : count(chest, Items.GOLD_NUGGET) == 1 && total(chest) == 1, ctx + ": the output holds more than the one nugget");
                pack.discard();
            }
        }).run();
        passed("grabber_packages").run();
        helper.succeed();
    }

    // TileEntityCraneGrabber.java:195-267: the control keys, the paste data and the save format; the upgrade slots 9 and 10 can be written by neither the slot payload nor the paste
    @GameTest(template = TEMPLATE, batch = "hbm31c_grabber_control", timeoutTicks = 100)
    public static void grabber_control(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            HolderLookup.Provider reg = level.registryAccess();
            CraneGrabberBlockEntity be = placeCrane(helper, new BlockPos(8, 2, 8), grabberBlock(), Direction.EAST, Direction.WEST, CraneGrabberBlockEntity.class);
            BlockPos abs = be.getBlockPos();
            Player player = helper.makeMockPlayer(GameType.SURVIVAL);
            Vec3 corner = Vec3.atLowerCornerOf(abs);
            player.setPos(corner.x + 3, corner.y, corner.z);
            ItemStack stoneUpgrade = s(NtmItems.UPGRADE_STACK_1.get(), 1);
            ItemStack ejector = s(NtmItems.UPGRADE_EJECTOR_2.get(), 1);
            be.setItem(9, stoneUpgrade.copy());
            be.setItem(10, ejector.copy());
            CompoundTag dirt = (CompoundTag) s(Items.DIRT, 5).save(reg);

            check(Arrays.equals(be.getFilterSlots(), new int[] { 0, 9 }), "the filter range is " + Arrays.toString(be.getFilterSlots()) + ", expected {0, 9} (:254-257)");

            // :260-267 the slot payload within the range
            for(int slot : new int[] { 0, 4, 8 }) {
                CompoundTag p = new CompoundTag();
                p.putInt("slot", slot);
                p.put("stack", dirt.copy());
                CompoundTagControl.apply(player, p, abs);
                check(be.getItem(slot).is(Items.DIRT) && be.getItem(slot).getCount() == 1 && "exact".equals(be.matcher.modes[slot]), "slot " + slot + ": the payload gave " + be.getItem(slot) + " mode " + be.matcher.modes[slot]);
            }

            // the upgrade slots and everything else outside 0-8 are not writable through the payload
            CompoundTag before = nbt(be);
            for(int slot : new int[] { 9, 10, 11, -1, 17, 100, Integer.MAX_VALUE, Integer.MIN_VALUE }) {
                CompoundTag p = new CompoundTag();
                p.putInt("slot", slot);
                p.put("stack", dirt.copy());
                CompoundTagControl.apply(player, p, abs);
                check(nbt(be).equals(before), "the slot payload " + slot + " changed the grabber to " + nbt(be) + " (IControlReceiverFilter.java:34)");
            }
            check(be.getItem(9).is(NtmItems.UPGRADE_STACK_1.get()) && be.getItem(10).is(NtmItems.UPGRADE_EJECTOR_2.get()), "an upgrade slot changed: " + be.getItem(9) + " / " + be.getItem(10));

            // :262 the whitelist toggles; unknown keys do nothing
            check(!be.isWhitelist, "the whitelist is on by default");
            CompoundTagControl.apply(player, key("whitelist"), abs);
            check(be.isWhitelist, "the whitelist key did not toggle on");
            CompoundTagControl.apply(player, key("whitelist"), abs);
            check(!be.isWhitelist, "the whitelist key did not toggle off");
            CompoundTagControl.apply(player, key("maxEject"), abs);
            CompoundTagControl.apply(player, key("toggle"), abs);
            CompoundTagControl.apply(player, key("destroyer"), abs);
            check(!be.isWhitelist, "a key the grabber does not know toggled the whitelist");

            // :249-252 the permission is a distance below 20
            player.setPos(corner.x + 19.9, corner.y, corner.z);
            check(be.hasPermission(player), "19.9 blocks: no permission");
            CompoundTagControl.apply(player, key("whitelist"), abs);
            check(be.isWhitelist, "19.9 blocks away the whitelist key did not toggle");
            CompoundTagControl.apply(player, key("whitelist"), abs);
            CompoundTag state = nbt(be);
            for(double dist : new double[] { 20.0, 20.5, 70.0 }) {
                player.setPos(corner.x + dist, corner.y, corner.z);
                CompoundTagControl.apply(player, key("whitelist"), abs);
                CompoundTag p = new CompoundTag();
                p.putInt("slot", 1);
                p.put("stack", dirt.copy());
                CompoundTagControl.apply(player, p, abs);
                check(nbt(be).equals(state), dist + " blocks away a payload changed the grabber");
            }

            // paste data (:140-176 through the base crane): the relative slot of an entry is 0-8; entries for 9 and 10 are skipped, the upgrades stay
            CranePlayer holder = player(helper, GameType.SURVIVAL, 0F);
            CraneGrabberBlockEntity dst = placeCrane(helper, new BlockPos(4, 2, 4), grabberBlock(), Direction.NORTH, Direction.SOUTH, CraneGrabberBlockEntity.class);
            dst.setItem(9, stoneUpgrade.copy());
            dst.setItem(10, ejector.copy());
            ListTag list = new ListTag();
            for(int slot : new int[] { 9, 10, 1, 8, 11, 127 }) {
                CompoundTag entry = new CompoundTag();
                entry.putByte("slot", (byte) slot);
                list.add(s(Items.GOLD_INGOT, 1).save(reg, entry));
            }
            CompoundTag paste = new CompoundTag();
            paste.putInt("inputSide", 2);
            paste.putInt("outputSide", 3);
            paste.put("items", list);
            dst.pasteSettings(paste, 0, level, holder, dst.getBlockPos());
            check(dst.getItem(1).is(Items.GOLD_INGOT) && dst.getItem(8).is(Items.GOLD_INGOT), "the valid entries 1 and 8 were not pasted: " + dst.getItem(1) + " / " + dst.getItem(8));
            check(dst.getItem(9).is(NtmItems.UPGRADE_STACK_1.get()) && dst.getItem(10).is(NtmItems.UPGRADE_EJECTOR_2.get()), "the paste wrote an upgrade slot: " + dst.getItem(9) + " / " + dst.getItem(10));
            for(int i : new int[] { 0, 2, 3, 4, 5, 6, 7 }) check(dst.getItem(i).isEmpty(), "the paste filled slot " + i);
            check(dst.getBlockState().getValue(CraneBaseBlock.INPUT) == Direction.NORTH, "pasting the filter changed the orientation");

            // an empty slot 9 / 10 stays empty too
            CraneGrabberBlockEntity bare = placeCrane(helper, new BlockPos(4, 2, 8), grabberBlock(), Direction.NORTH, Direction.SOUTH, CraneGrabberBlockEntity.class);
            bare.pasteSettings(paste, 0, level, holder, bare.getBlockPos());
            check(bare.getItem(9).isEmpty() && bare.getItem(10).isEmpty() && bare.getItem(11 - 1).isEmpty(), "an entry for slot 9 or 10 filled an empty upgrade slot");

            // copy: sides as ordinals and the filter with relative slots, the upgrades are not copied (TileEntityCraneBase.java:113-137)
            CraneGrabberBlockEntity src = placeCrane(helper, new BlockPos(12, 2, 4), grabberBlock(), Direction.EAST, Direction.DOWN, CraneGrabberBlockEntity.class);
            src.setItem(0, s(Items.DIRT, 1));
            src.setItem(6, s(Items.OAK_LOG, 1));
            src.setItem(9, stoneUpgrade.copy());
            src.setItem(10, ejector.copy());
            CompoundTag copied = src.getSettings(level, src.getBlockPos());
            ListTag items = copied.getList("items", Tag.TAG_COMPOUND);
            check(copied.getInt("inputSide") == 5 && copied.getInt("outputSide") == 0, "the copied sides are " + copied.getInt("inputSide") + " / " + copied.getInt("outputSide") + ", expected 5 (EAST) / 0 (DOWN)");
            check(items.size() == 2 && items.getCompound(0).getByte("slot") == 0 && items.getCompound(1).getByte("slot") == 6, "the copied filter is " + items + ", expected the slots 0 and 6 and no upgrade");
            String[] info = src.infoForDisplay(level, src.getBlockPos());
            check(info.length == 2 && info[0].equals("copytool.filter") && info[1].equals("copytool.orientation"), "the display list is " + Arrays.toString(info));
            CraneGrabberBlockEntity dst2 = placeCrane(helper, new BlockPos(12, 2, 8), grabberBlock(), Direction.SOUTH, Direction.NORTH, CraneGrabberBlockEntity.class);
            dst2.pasteSettings(copied, 0, level, holder, dst2.getBlockPos());
            dst2.pasteSettings(copied, 1, level, holder, dst2.getBlockPos());
            BlockState got = level.getBlockState(dst2.getBlockPos());
            check(got.getValue(CraneBaseBlock.INPUT) == Direction.EAST && got.getValue(CraneBaseBlock.OUTPUT) == Direction.DOWN, "the pasted orientation is " + sides(got));
            check(level.getBlockEntity(dst2.getBlockPos()) instanceof CraneGrabberBlockEntity now && now.getItem(0).is(Items.DIRT) && now.getItem(6).is(Items.OAK_LOG) && now.getItem(9).isEmpty(), "the pasted filter was lost or an upgrade appeared");
            // an extractor's copy also fits (the same range 0-8)
            CraneExtractorBlockEntity ex = placeCrane(helper, new BlockPos(12, 2, 12), NtmBlocks.CRANE_EXTRACTOR.get(), Direction.EAST, Direction.WEST, CraneExtractorBlockEntity.class);
            ex.setItem(2, s(Items.COAL, 1));
            CraneGrabberBlockEntity dst3 = placeCrane(helper, new BlockPos(8, 2, 12), grabberBlock(), Direction.EAST, Direction.WEST, CraneGrabberBlockEntity.class);
            dst3.pasteSettings(ex.getSettings(level, ex.getBlockPos()), 0, level, holder, dst3.getBlockPos());
            check(dst3.getItem(2).is(Items.COAL), "an extractor's filter did not paste into a grabber");
        }).run();
        passed("grabber_control").run();
        helper.succeed();
    }

    // TileEntityCraneGrabber.java:233-247 (isWhitelist, the pattern modes, lastGrabbedTick, the slots) and :195-206 (the packet form: the whitelist flag and the modes)
    @GameTest(template = TEMPLATE, batch = "hbm31c_grabber_persistence", timeoutTicks = 100)
    public static void grabber_persistence(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            HolderLookup.Provider reg = level.registryAccess();
            CraneGrabberBlockEntity be = placeCrane(helper, new BlockPos(8, 2, 8), grabberBlock(), Direction.EAST, Direction.WEST, CraneGrabberBlockEntity.class);
            BlockPos abs = be.getBlockPos();
            check(!be.isWhitelist && be.lastGrabbedTick == 0 && be.getContainerSize() == 11, "a new grabber has whitelist " + be.isWhitelist + ", lastGrabbedTick " + be.lastGrabbedTick + ", " + be.getContainerSize() + " slots, expected false, 0, 11");
            be.isWhitelist = true;
            be.lastGrabbedTick = 123_456_789_012L;
            setFilter(be, 0, s(Items.DIRT, 1), "wildcard");
            setFilter(be, 5, s(Items.OAK_LOG, 1), "minecraft:logs");
            be.setItem(9, s(NtmItems.UPGRADE_STACK_3.get(), 1));
            be.setItem(10, s(NtmItems.UPGRADE_EJECTOR_1.get(), 1));
            CompoundTag tag = nbt(be);
            check(tag.contains("isWhitelist", Tag.TAG_BYTE) && tag.getBoolean("isWhitelist"), "the whitelist is saved as " + tag.get("isWhitelist"));
            check(tag.contains("lastGrabbedTick", Tag.TAG_LONG) && tag.getLong("lastGrabbedTick") == 123_456_789_012L, "lastGrabbedTick is saved as " + tag.get("lastGrabbedTick") + ", expected a long");
            check("wildcard".equals(tag.getString("mode0")) && "minecraft:logs".equals(tag.getString("mode5")) && !tag.contains("mode1"), "the mode keys are " + tag.getAllKeys());
            check(tag.contains("Items", Tag.TAG_LIST), "the keys are " + tag.getAllKeys() + ", expected Items");

            CraneGrabberBlockEntity loaded = new CraneGrabberBlockEntity(abs, level.getBlockState(abs));
            loaded.loadWithComponents(tag, reg);
            check(loaded.isWhitelist && loaded.lastGrabbedTick == 123_456_789_012L, "the loaded whitelist / lastGrabbedTick are " + loaded.isWhitelist + " / " + loaded.lastGrabbedTick);
            for(int i = 0; i < 9; i++) check(java.util.Objects.equals(loaded.matcher.modes[i], be.matcher.modes[i]), "mode " + i + " is " + loaded.matcher.modes[i] + " after loading, expected " + be.matcher.modes[i]);
            for(int i = 0; i < 11; i++) check(ItemStack.matches(loaded.getItem(i), be.getItem(i)), "slot " + i + " holds " + loaded.getItem(i) + " after loading, expected " + be.getItem(i));
            check(loaded.getDelay() == 10 && loaded.getAmount() == 64, "the loaded upgrades give delay " + loaded.getDelay() + " and amount " + loaded.getAmount() + ", expected 10 and 64");

            RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf(Unpooled.buffer(), level.registryAccess());
            be.serialize(buf);
            CraneGrabberBlockEntity fromPacket = new CraneGrabberBlockEntity(abs, level.getBlockState(abs));
            fromPacket.deserialize(buf);
            check(fromPacket.isWhitelist && "wildcard".equals(fromPacket.matcher.modes[0]) && "minecraft:logs".equals(fromPacket.matcher.modes[5]) && fromPacket.matcher.modes[1] == null, "the packet gave whitelist " + fromPacket.isWhitelist + ", modes " + Arrays.toString(fromPacket.matcher.modes));
        }).run();
        passed("grabber_persistence").run();
        helper.succeed();
    }

    private static IItemHandler handler(ServerLevel level, BlockPos abs, @Nullable Direction side) {
        return level.getCapability(Capabilities.ItemHandler.BLOCK, abs, side);
    }

    // TileEntityCraneGrabber.java (no getAccessibleSlotsFromSide, TileEntityMachineBase.java:135-138 returns an empty array): the item capability shows no slot from any side;
    // the grabber has no comparator output (CraneGrabber.java has no comparator override)
    @GameTest(template = TEMPLATE, batch = "hbm31c_grabber_capability", timeoutTicks = 100)
    public static void grabber_capability(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            CraneGrabberBlockEntity be = placeCrane(helper, new BlockPos(8, 2, 8), grabberBlock(), Direction.EAST, Direction.WEST, CraneGrabberBlockEntity.class);
            BlockPos abs = be.getBlockPos();
            setFilter(be, 0, s(Items.DIRT, 1), "exact");
            be.setItem(9, s(NtmItems.UPGRADE_STACK_1.get(), 1));
            be.setItem(10, s(NtmItems.UPGRADE_EJECTOR_1.get(), 1));
            for(Direction d : Direction.values()) {
                check(be.getSlotsForFace(d).length == 0, "getSlotsForFace(" + d + ") is " + Arrays.toString(be.getSlotsForFace(d)) + ", expected none");
                IItemHandler h = handler(level, abs, d);
                check(h == null || h.getSlots() == 0, "the handler from " + d + " shows " + (h == null ? 0 : h.getSlots()) + " slots, expected none");
            }
            check(handler(level, abs, null) == null, "an unsided query on the grabber gave a handler");
            check(be.getItem(0).is(Items.DIRT) && be.getItem(9).is(NtmItems.UPGRADE_STACK_1.get()) && be.getItem(10).is(NtmItems.UPGRADE_EJECTOR_1.get()), "a slot changed");
            check(!level.getBlockState(abs).hasAnalogOutputSignal(), "the grabber has a comparator output");
        }).run();
        passed("grabber_capability").run();
        helper.succeed();
    }

    // TileEntityCraneGrabber.java:59-69 through the world's own ticking: a placed grabber with a stack of 1 item put in front of it on every tick grabs exactly once per delay
    // (20 / 10 / 5 / 2 with the ejector upgrade), measured from one grab to the next
    @GameTest(template = TEMPLATE, batch = "hbm31c_grabber_world_cadence", timeoutTicks = 200)
    public static void grabber_world_cadence(GameTestHelper helper) {
        int[] delays = { 20, 10, 5, 2 };
        List<CraneGrabberBlockEntity> grabbers = new ArrayList<>();
        List<Container> chests = new ArrayList<>();
        List<BlockPos> inCells = new ArrayList<>();
        for(int i = 0; i < 4; i++) {
            BlockPos rel = new BlockPos(8, 2, 2 + 3 * i);
            CraneGrabberBlockEntity be = placeCrane(helper, rel, grabberBlock(), Direction.EAST, Direction.WEST, CraneGrabberBlockEntity.class);
            be.slots.set(CraneGrabberBlockEntity.SLOT_EJECTOR_UPGRADE, ejectorUpgrade(i));
            grabbers.add(be);
            chests.add(chest(helper, rel.west()));
            inCells.add(rel.east());
        }
        List<List<Long>> times = new ArrayList<>();
        int[] last = new int[4];
        for(int i = 0; i < 4; i++) times.add(new ArrayList<>());
        helper.startSequence()
                .thenExecuteFor(75, guard(() -> {
                    ServerLevel level = helper.getLevel();
                    for(int i = 0; i < 4; i++) {
                        int n = total(chests.get(i));
                        if(n > last[i]) {
                            check(n == last[i] + 1, "delay " + delays[i] + ": " + (n - last[i]) + " items arrived on one tick, expected 1 (amount 1)");
                            times.get(i).add(level.getGameTime());
                            last[i] = n;
                        }
                        for(MovingItem old : movingIn(helper, inCells.get(i))) old.discard();
                        movingAt(level, cellCentre(helper, inCells.get(i)), s(Items.IRON_NUGGET, 1));
                    }
                }))
                .thenExecute(guard(() -> {
                    for(int i = 0; i < 4; i++) {
                        List<Long> t = times.get(i);
                        check(t.size() >= 75 / delays[i] - 1, "delay " + delays[i] + ": only " + t.size() + " grabs in 75 ticks");
                        for(int k = 1; k < t.size(); k++) {
                            check(t.get(k) - t.get(k - 1) == delays[i], "delay " + delays[i] + ": grab " + k + " came " + (t.get(k) - t.get(k - 1)) + " ticks after the one before (:69 lastGrabbedTick + delay)");
                        }
                    }
                }))
                .thenExecute(passed("grabber_world_cadence"))
                .thenSucceed();
    }

    // TileEntityCraneGrabber.java:85-186 with a real belt: a stack riding past a placed grabber is taken into the chest by one per try without the stack upgrade (the rest
    // rides on and leaves the belt), as a whole with the third stack upgrade; no item is lost or made
    @GameTest(template = TEMPLATE, batch = "hbm31c_grabber_belt_flow", timeoutTicks = 300)
    public static void grabber_belt_flow(GameTestHelper helper) {
        placeCrane(helper, new BlockPos(8, 2, 8), grabberBlock(), Direction.EAST, Direction.WEST, CraneGrabberBlockEntity.class);
        Container chestA = chest(helper, new BlockPos(7, 2, 8));
        CraneGrabberBlockEntity b = placeCrane(helper, new BlockPos(4, 2, 8), grabberBlock(), Direction.WEST, Direction.EAST, CraneGrabberBlockEntity.class);
        b.slots.set(CraneGrabberBlockEntity.SLOT_STACK_UPGRADE, stackUpgrade(3));
        Container chestB = chest(helper, new BlockPos(5, 2, 8));
        for(int z = 5; z <= 12; z++) {
            helper.setBlock(new BlockPos(9, 2, z), beltState(Direction.SOUTH));
            helper.setBlock(new BlockPos(3, 2, z), beltState(Direction.SOUTH));
        }
        helper.startSequence()
                .thenExecute(guard(() -> {
                    movingAt(helper.getLevel(), helper.absoluteVec(new Vec3(9.5, 2.25, 11.5)), s(Items.IRON_NUGGET, 20));
                    movingAt(helper.getLevel(), helper.absoluteVec(new Vec3(3.5, 2.25, 11.5)), s(Items.GOLD_NUGGET, 20));
                }))
                .thenWaitUntil(guard(() -> check(count(chestA, Items.IRON_NUGGET) >= 1 && count(chestB, Items.GOLD_NUGGET) >= 1, "nothing was grabbed yet")))
                .thenExecuteAfter(40, guard(() -> {
                    check(count(chestA, Items.IRON_NUGGET) == 1, "the first belt gave " + count(chestA, Items.IRON_NUGGET) + " nuggets to the chest, expected 1 (the stack passes the box within one delay)");
                    check(loose(helper, Items.IRON_NUGGET) == 19, "the other nuggets: " + loose(helper, Items.IRON_NUGGET) + " still on the belt or dropped, expected 19");
                    check(count(chestB, Items.GOLD_NUGGET) == 20 && loose(helper, Items.GOLD_NUGGET) == 0, "the second belt (stack upgrade 3) gave " + count(chestB, Items.GOLD_NUGGET) + " to the chest and left " + loose(helper, Items.GOLD_NUGGET) + ", expected 20 and 0");
                }))
                .thenExecute(passed("grabber_belt_flow"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 2. the boxer

    private static final Item[] KINDS = { Items.STONE, Items.DIRT, Items.SAND, Items.GRAVEL, Items.COBBLESTONE, Items.OAK_LOG, Items.SPRUCE_LOG, Items.BIRCH_LOG, Items.IRON_INGOT,
            Items.GOLD_INGOT, Items.COPPER_INGOT, Items.COAL, Items.REDSTONE, Items.LAPIS_LAZULI, Items.DIAMOND, Items.EMERALD, Items.QUARTZ, Items.SLIME_BALL, Items.CLAY_BALL, Items.BRICK, Items.FLINT };

    // CraneBoxer.java:53-68: items enter through the input side only (a diagonal step has no side), go into the buffer, what does not fit is dropped at the block's centre
    @GameTest(template = TEMPLATE, batch = "hbm31c_boxer_items_input", timeoutTicks = 100)
    public static void boxer_items_input(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            CraneBoxerBlock block = (CraneBoxerBlock) boxerBlock();
            BlockPos rel = new BlockPos(8, 3, 8);
            BlockPos abs = helper.absolutePos(rel);
            for(Direction in : Direction.values()) {
                Direction out = in == Direction.UP ? Direction.DOWN : Direction.UP;
                helper.setBlock(rel, crane(boxerBlock(), in, out));
                MovingItem item = movingAt(level, cellCentre(helper, rel.south(3)), s(Items.STONE, 1));
                for(Direction from : Direction.values()) {
                    check(block.canItemEnter(level, abs, from, item) == (from == in), "input " + in + ": canItemEnter from " + from + " is " + !(from == in) + " (:53-56)");
                }
                check(!block.canItemEnter(level, abs, null, item), "input " + in + ": an item enters without a side");
                item.discard();
            }

            CraneBoxerBlockEntity be = placeCrane(helper, rel, boxerBlock(), Direction.EAST, Direction.WEST, CraneBoxerBlockEntity.class);
            // the real entity path: only through the input side, the entity is removed when it enters
            MovingItem wrong = movingAt(level, cellCentre(helper, rel.south(3)), s(Items.STONE, 64));
            wrong.enterBlock(block, abs, Direction.NORTH);
            wrong.enterBlock(block, abs, null);
            check(!wrong.isRemoved() && total(be) == 0, "a side that is not the input side let the item in");
            wrong.enterBlock(block, abs, Direction.EAST);
            check(wrong.isRemoved() && count(be, Items.STONE) == 64 && be.getItem(0).is(Items.STONE), "the input side did not take the item (removed " + wrong.isRemoved() + ", buffer " + count(be, Items.STONE) + ")");
            wrong.enterBlock(block, abs, Direction.EAST);
            check(count(be, Items.STONE) == 64, "a removed item entered a second time");

            // merging first, then empty slots, up to the stack limit
            MovingItem more = movingAt(level, cellCentre(helper, rel.south(3)), s(Items.STONE, 10));
            more.enterBlock(block, abs, Direction.EAST);
            check(be.getItem(1).is(Items.STONE) && be.getItem(1).getCount() == 10, "the next stack went to " + be.getItem(1));

            // a full buffer: the rest drops at the centre of the block (no destroyer switch on the boxer, :64-67)
            for(int i = 0; i < 21; i++) be.setItem(i, s(Items.COBBLESTONE, 64));
            MovingItem overflow = movingAt(level, cellCentre(helper, rel.south(3)), s(Items.SAND, 7));
            overflow.enterBlock(block, abs, Direction.EAST);
            check(overflow.isRemoved() && dropped(helper, Items.SAND) == 7, "the overflow: removed " + overflow.isRemoved() + ", " + dropped(helper, Items.SAND) + " sand dropped, expected 7");
            for(ItemEntity e : level.getEntitiesOfClass(ItemEntity.class, helper.getBounds())) {
                if(e.getItem().is(Items.SAND)) check(near(e.position(), new Vec3(abs.getX() + 0.5, abs.getY() + 0.5, abs.getZ() + 0.5), 1e-9), "the overflow dropped at " + fmt(e.position()) + ", expected the block's centre (:65)");
            }
            check(count(be, Items.COBBLESTONE) == 21 * 64, "the buffer changed");
        }).run();
        passed("boxer_items_input").run();
        helper.succeed();
    }

    private record BoxCase(String name, int mode, int[] fullSlots, int[] partialSlots, int packed, @Nullable Block output) { }

    // TileEntityCraneBoxer.java:90-145: every second tick of the world time (gameTime % 2 == 0), with a belt on the output side and at least 4 / 8 / 16 FULL stacks, exactly that
    // many full stacks are packed (the first ones in slot order) in reverse slot order, a stack that is not full is never packed; without a belt nothing happens
    @GameTest(template = TEMPLATE, batch = "hbm31c_boxer_pack", timeoutTicks = 200)
    public static void boxer_pack(GameTestHelper helper) {
        // full slots, partially filled slots
        BoxCase[] cases = {
                new BoxCase("mode 4, five full stacks among others", 0, new int[] { 0, 2, 3, 4, 5 }, new int[] { 1, 6 }, 4, null),
                new BoxCase("mode 4, three full stacks", 0, new int[] { 0, 2, 3 }, new int[] { 1, 4, 5, 6, 7 }, 0, null),
                new BoxCase("mode 8, seven full stacks", 1, new int[] { 0, 1, 2, 3, 4, 5, 6 }, new int[] { 7, 8, 9 }, 0, null),
                new BoxCase("mode 8, nine full stacks", 1, new int[] { 0, 1, 2, 3, 4, 5, 6, 7, 8 }, new int[] { 9 }, 8, null),
                new BoxCase("mode 16, fifteen full stacks", 2, new int[] { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14 }, new int[] { 15 }, 0, null),
                new BoxCase("mode 16, seventeen full stacks", 2, new int[] { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16 }, new int[] { 17, 18 }, 16, null),
                new BoxCase("mode 4, a stone block on the output side", 0, new int[] { 0, 1, 2, 3 }, new int[0], 0, Blocks.STONE),
                new BoxCase("mode 4, a chest on the output side", 0, new int[] { 0, 1, 2, 3 }, new int[0], 0, Blocks.CHEST),
                new BoxCase("mode 4, nothing on the output side", 0, new int[] { 0, 1, 2, 3 }, new int[0], 0, Blocks.AIR),
                new BoxCase("redstone mode, four full stacks and no signal", 3, new int[] { 0, 1, 2, 3 }, new int[0], 0, null),
        };
        List<CraneBoxerBlockEntity> boxers = new ArrayList<>();
        for(int k = 0; k < cases.length; k++) {
            BlockPos rel = new BlockPos(8, 2, 1 + k);
            CraneBoxerBlockEntity be = detachedBoxer(helper, rel, Direction.EAST, Direction.WEST);
            be.mode = (byte) cases[k].mode();
            if(cases[k].output() == null) helper.setBlock(rel.west(), beltState(Direction.SOUTH));
            else helper.setBlock(rel.west(), cases[k].output().defaultBlockState());
            boxers.add(be);
        }
        int[] evens = new int[1];
        int[] odds = new int[1];
        int[] packs = new int[1];
        helper.startSequence()
                .thenExecuteFor(6, guard(() -> {
                    ServerLevel level = helper.getLevel();
                    boolean even = level.getGameTime() % 2 == 0;
                    if(even) evens[0]++;
                    else odds[0]++;
                    for(int k = 0; k < cases.length; k++) {
                        BoxCase c = cases[k];
                        CraneBoxerBlockEntity be = boxers.get(k);
                        BlockPos outCell = new BlockPos(7, 2, 1 + k);
                        for(int i = 0; i < 21; i++) be.slots.set(i, ItemStack.EMPTY);
                        for(int i : c.fullSlots()) be.slots.set(i, s(KINDS[i], 64));
                        for(int i : c.partialSlots()) be.slots.set(i, s(KINDS[i], 63));
                        be.updateEntity();
                        List<MovingPackage> made = packagesIn(helper, outCell);
                        String ctx = c.name() + " at world time " + (even ? "even" : "odd");
                        if(even && c.packed() > 0) {
                            check(made.size() == 1, ctx + ": " + made.size() + " packages appeared, expected 1 (:90 gameTime % 2 == 0)");
                            ItemStack[] box = made.get(0).getItemStacks();
                            check(box.length == c.packed(), ctx + ": the package holds " + box.length + " stacks, expected " + c.packed() + " (:94-97)");
                            // the first packed stacks in slot order, written to the array from its end (:129-135)
                            for(int j = 0; j < c.packed(); j++) {
                                int slot = c.fullSlots()[j];
                                ItemStack expected = s(KINDS[slot], 64);
                                check(ItemStack.matches(box[c.packed() - 1 - j], expected), ctx + ": package stack " + (c.packed() - 1 - j) + " is " + box[c.packed() - 1 - j] + ", expected " + expected + " from slot " + slot);
                                check(be.getItem(slot).isEmpty(), ctx + ": slot " + slot + " was not emptied");
                            }
                            for(int j = c.packed(); j < c.fullSlots().length; j++) check(be.getItem(c.fullSlots()[j]).getCount() == 64, ctx + ": a full stack beyond the mode's count was taken (slot " + c.fullSlots()[j] + ")");
                            for(int i : c.partialSlots()) check(be.getItem(i).getCount() == 63, ctx + ": a stack that is not full was packed (slot " + i + ")");
                            packs[0]++;
                        } else {
                            check(made.isEmpty(), ctx + ": a package appeared");
                            for(int i : c.fullSlots()) check(be.getItem(i).getCount() == 64, ctx + ": slot " + i + " was changed");
                            for(int i : c.partialSlots()) check(be.getItem(i).getCount() == 63, ctx + ": slot " + i + " was changed");
                        }
                        for(MovingPackage p : made) p.discard();
                    }
                }))
                .thenExecute(guard(() -> {
                    check(evens[0] >= 1 && odds[0] >= 1, "the run saw " + evens[0] + " even and " + odds[0] + " odd world times");
                    check(packs[0] == evens[0] * 3, "packages made: " + packs[0] + " over " + evens[0] + " even ticks, expected 3 per even tick");
                }))
                .thenExecute(passed("boxer_pack"))
                .thenSucceed();
    }

    // TileEntityCraneBoxer.java:46-88: in redstone mode the rising edge of the signal packs all non-empty slots (up to 21, any fill) in reverse slot order; a signal that stays
    // does not repeat; the previous state is updated every tick (:88), also when nothing could be packed; no belt or an empty buffer: nothing
    @GameTest(template = TEMPLATE, batch = "hbm31c_boxer_redstone", timeoutTicks = 100)
    public static void boxer_redstone(GameTestHelper helper) {
        guard(() -> {
            BlockPos rel = new BlockPos(8, 2, 4);
            CraneBoxerBlockEntity be = detachedBoxer(helper, rel, Direction.EAST, Direction.WEST);
            be.mode = CraneBoxerBlockEntity.MODE_REDSTONE;
            BlockPos outCell = rel.west();
            helper.setBlock(outCell, beltState(Direction.SOUTH));
            BlockPos power = rel.above();

            // an empty buffer on the rising edge: nothing
            helper.setBlock(power, Blocks.REDSTONE_BLOCK.defaultBlockState());
            be.updateEntity();
            check(packagesIn(helper, outCell).isEmpty(), "an empty buffer made a package (:66 pack > 0)");
            helper.setBlock(power, Blocks.AIR.defaultBlockState());
            be.updateEntity();

            // the edge: slots 2, 5 and 9 with any fill
            be.setItem(2, s(Items.STONE, 7));
            be.setItem(5, s(Items.DIRT, 1));
            be.setItem(9, s(Items.SAND, 64));
            helper.setBlock(power, Blocks.REDSTONE_BLOCK.defaultBlockState());
            be.updateEntity();
            List<MovingPackage> first = packagesIn(helper, outCell);
            check(first.size() == 1, first.size() + " packages after the rising edge, expected 1");
            ItemStack[] box = first.get(0).getItemStacks();
            check(box.length == 3 && box[0].is(Items.SAND) && box[0].getCount() == 64 && box[1].is(Items.DIRT) && box[2].is(Items.STONE) && box[2].getCount() == 7, "the package holds " + describe(box) + ", expected [64xsand, 1xdirt, 7xstone] (:68-77 reverse slot order)");
            check(total(be) == 0, "the buffer still holds " + total(be) + " items");
            for(MovingPackage p : first) p.discard();

            // the signal stays: no new package even with a refilled buffer, in any number of ticks
            be.setItem(0, s(Items.GOLD_INGOT, 3));
            be.updateEntity();
            be.updateEntity();
            check(packagesIn(helper, outCell).isEmpty() && be.getItem(0).getCount() == 3, "a signal that stayed made another package (:48 !lastRedstone)");

            // the signal gone for one tick and back: the next edge packs
            helper.setBlock(power, Blocks.AIR.defaultBlockState());
            be.updateEntity();
            check(packagesIn(helper, outCell).isEmpty(), "the falling edge made a package");
            helper.setBlock(power, Blocks.REDSTONE_BLOCK.defaultBlockState());
            be.updateEntity();
            List<MovingPackage> second = packagesIn(helper, outCell);
            check(second.size() == 1 && second.get(0).getItemStacks().length == 1 && second.get(0).getItemStacks()[0].is(Items.GOLD_INGOT) && be.getItem(0).isEmpty(), "the second edge gave " + second.size() + " packages");
            for(MovingPackage p : second) p.discard();

            // all 21 slots
            helper.setBlock(power, Blocks.AIR.defaultBlockState());
            be.updateEntity();
            for(int i = 0; i < 21; i++) be.setItem(i, s(KINDS[i], 1 + i));
            helper.setBlock(power, Blocks.REDSTONE_BLOCK.defaultBlockState());
            be.updateEntity();
            List<MovingPackage> all = packagesIn(helper, outCell);
            check(all.size() == 1 && all.get(0).getItemStacks().length == 21, "21 filled slots gave " + all.size() + " packages");
            for(int i = 0; i < 21; i++) {
                ItemStack st = all.get(0).getItemStacks()[20 - i];
                check(st.is(KINDS[i]) && st.getCount() == 1 + i, "package stack " + (20 - i) + " is " + st + ", expected " + (1 + i) + " x " + KINDS[i] + " from slot " + i);
            }
            check(total(be) == 0, "the buffer was not emptied");
            for(MovingPackage p : all) p.discard();

            // no belt on the output side: nothing happens, but the edge is used up (:88)
            CraneBoxerBlockEntity lone = detachedBoxer(helper, new BlockPos(8, 2, 10), Direction.EAST, Direction.WEST);
            lone.mode = CraneBoxerBlockEntity.MODE_REDSTONE;
            helper.setBlock(new BlockPos(7, 2, 10), Blocks.STONE.defaultBlockState());
            helper.setBlock(new BlockPos(8, 3, 10), Blocks.REDSTONE_BLOCK.defaultBlockState());
            lone.setItem(3, s(Items.STONE, 5));
            lone.updateEntity();
            check(lone.getItem(3).getCount() == 5, "a boxer without a belt packed");
            helper.setBlock(new BlockPos(7, 2, 10), beltState(Direction.SOUTH));
            lone.updateEntity();
            check(lone.getItem(3).getCount() == 5 && packagesIn(helper, new BlockPos(7, 2, 10)).isEmpty(), "a belt that appeared while the signal stayed made the boxer pack (the edge was spent without a belt, :88)");

            // the other modes ignore the signal: partial stacks only, so no count mode can pack them either
            CraneBoxerBlockEntity counted = detachedBoxer(helper, new BlockPos(8, 2, 13), Direction.EAST, Direction.WEST);
            helper.setBlock(new BlockPos(7, 2, 13), beltState(Direction.SOUTH));
            helper.setBlock(new BlockPos(8, 3, 13), Blocks.REDSTONE_BLOCK.defaultBlockState());
            counted.setItem(0, s(Items.STONE, 5));
            counted.updateEntity();
            counted.updateEntity();
            check(counted.getItem(0).getCount() == 5 && packagesIn(helper, new BlockPos(7, 2, 13)).isEmpty(), "mode 4 packed on a rising edge (:48 needs the redstone mode)");
        }).run();
        passed("boxer_redstone").run();
        helper.succeed();
    }

    // TileEntityCraneBoxer.java:173-185, :203-208: mode and lastRedstone are saved; the toggle key cycles 0 -> 1 -> 2 -> 3 -> 0 within 20 blocks (:198-201)
    @GameTest(template = TEMPLATE, batch = "hbm31c_boxer_persistence", timeoutTicks = 100)
    public static void boxer_persistence(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            HolderLookup.Provider reg = level.registryAccess();
            CraneBoxerBlockEntity be = placeCrane(helper, new BlockPos(8, 2, 8), boxerBlock(), Direction.EAST, Direction.WEST, CraneBoxerBlockEntity.class);
            BlockPos abs = be.getBlockPos();
            Player player = helper.makeMockPlayer(GameType.SURVIVAL);
            Vec3 corner = Vec3.atLowerCornerOf(abs);
            player.setPos(corner.x + 3, corner.y, corner.z);
            check(be.mode == 0 && be.getContainerSize() == 21, "a new boxer has mode " + be.mode + " and " + be.getContainerSize() + " slots");
            for(int expected : new int[] { 1, 2, 3, 0, 1 }) {
                CompoundTagControl.apply(player, key("toggle"), abs);
                check(be.mode == expected, "the toggle key gave mode " + be.mode + ", expected " + expected + " (:206)");
            }
            CompoundTagControl.apply(player, key("whitelist"), abs);
            CompoundTagControl.apply(player, key("destroyer"), abs);
            check(be.mode == 1, "a key the boxer does not know changed the mode");
            player.setPos(corner.x + 19.9, corner.y, corner.z);
            CompoundTagControl.apply(player, key("toggle"), abs);
            check(be.mode == 2, "19.9 blocks away the toggle did not work");
            for(double dist : new double[] { 20.0, 20.5, 70.0 }) {
                player.setPos(corner.x + dist, corner.y, corner.z);
                CompoundTagControl.apply(player, key("toggle"), abs);
                check(be.mode == 2, dist + " blocks away the toggle changed the mode to " + be.mode);
            }

            for(byte m = 0; m < 4; m++) {
                be.mode = m;
                be.setItem(m, s(Items.STONE, 3));
                CompoundTag tag = nbt(be);
                check(tag.contains("mode", Tag.TAG_BYTE) && tag.getByte("mode") == m && tag.contains("lastRedstone", Tag.TAG_BYTE) && tag.contains("Items", Tag.TAG_LIST), "mode " + m + ": the saved keys are " + tag.getAllKeys() + " (" + tag.get("mode") + ")");
                CraneBoxerBlockEntity loaded = new CraneBoxerBlockEntity(abs, level.getBlockState(abs));
                loaded.loadWithComponents(tag, reg);
                check(loaded.mode == m && loaded.getItem(m).getCount() == 3, "mode " + m + " loaded as " + loaded.mode);
            }
            be.mode = 2;
            RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf(Unpooled.buffer(), level.registryAccess());
            be.serialize(buf);
            CraneBoxerBlockEntity fromPacket = new CraneBoxerBlockEntity(abs, level.getBlockState(abs));
            fromPacket.deserialize(buf);
            check(fromPacket.mode == 2, "the packet form gave mode " + fromPacket.mode + " (:151-161)");

            // lastRedstone: a boxer in redstone mode packs on the edge; saved while powered, a boxer loaded from it does not see a new edge; without the key it would
            BlockPos rel = new BlockPos(4, 2, 4);
            CraneBoxerBlockEntity a = detachedBoxer(helper, rel, Direction.EAST, Direction.WEST);
            a.mode = CraneBoxerBlockEntity.MODE_REDSTONE;
            helper.setBlock(rel.west(), beltState(Direction.SOUTH));
            helper.setBlock(rel.above(), Blocks.REDSTONE_BLOCK.defaultBlockState());
            a.setItem(0, s(Items.STONE, 4));
            a.updateEntity();
            check(packagesIn(helper, rel.west()).size() == 1 && a.getItem(0).isEmpty(), "the edge did not pack");
            CompoundTag saved = nbt(a);
            check(saved.contains("lastRedstone", Tag.TAG_BYTE) && saved.getBoolean("lastRedstone"), "lastRedstone is saved as " + saved.get("lastRedstone") + " while powered (:183)");
            for(MovingPackage p : packagesIn(helper, rel.west())) p.discard();

            CraneBoxerBlockEntity same = new CraneBoxerBlockEntity(helper.absolutePos(rel), crane(boxerBlock(), Direction.EAST, Direction.WEST));
            same.setLevel(level);
            same.loadWithComponents(saved, reg);
            same.setItem(0, s(Items.STONE, 4));
            same.updateEntity();
            check(packagesIn(helper, rel.west()).isEmpty() && same.getItem(0).getCount() == 4, "a boxer loaded from a powered save packed again (the edge was already seen)");

            CompoundTag stale = saved.copy();
            stale.remove("lastRedstone");
            CraneBoxerBlockEntity fresh = new CraneBoxerBlockEntity(helper.absolutePos(rel), crane(boxerBlock(), Direction.EAST, Direction.WEST));
            fresh.setLevel(level);
            fresh.loadWithComponents(stale, reg);
            fresh.setItem(0, s(Items.STONE, 4));
            fresh.updateEntity();
            check(packagesIn(helper, rel.west()).size() == 1, "without the lastRedstone key a powered boxer did not see an edge");
            for(MovingPackage p : packagesIn(helper, rel.west())) p.discard();

            // the unpowered state is saved as false and keeps the next signal an edge
            helper.setBlock(rel.above(), Blocks.AIR.defaultBlockState());
            a.updateEntity();
            CompoundTag off = nbt(a);
            check(off.contains("lastRedstone", Tag.TAG_BYTE) && !off.getBoolean("lastRedstone"), "lastRedstone is saved as " + off.get("lastRedstone") + " after the signal ended");
            CraneBoxerBlockEntity again = new CraneBoxerBlockEntity(helper.absolutePos(rel), crane(boxerBlock(), Direction.EAST, Direction.WEST));
            again.setLevel(level);
            again.loadWithComponents(off, reg);
            again.setItem(0, s(Items.STONE, 4));
            helper.setBlock(rel.above(), Blocks.REDSTONE_BLOCK.defaultBlockState());
            again.updateEntity();
            check(packagesIn(helper, rel.west()).size() == 1, "a boxer loaded from an unpowered save did not pack on the next edge");
        }).run();
        passed("boxer_persistence").run();
        helper.succeed();
    }

    /** The original calcRedstoneFromInventory (1.7.10 Container.java; CraneBoxer.java:70-78, CraneUnboxer.java:120-128): floor(fill * 14) + 1 when any slot is filled, over all slots of the container. */
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

    private static void comparatorCases(GameTestHelper helper, CraneBaseBlockEntity be, int usable, String original) {
        BlockPos abs = be.getBlockPos();
        BlockState state = helper.getLevel().getBlockState(abs);
        check(state.hasAnalogOutputSignal(), "the crane has no comparator output (" + original + ")");
        check(state.getAnalogOutputSignal(helper.getLevel(), abs) == 0 && originalComparator(be) == 0, "an empty crane gives " + state.getAnalogOutputSignal(helper.getLevel(), abs));
        Object[][][] cases = {
                { { 0, Items.STONE, 1 } },
                { { 0, Items.STONE, 64 } },
                { { 0, Items.STONE, 32 }, { 1, Items.ENDER_PEARL, 8 } },
                { { 0, Items.ENDER_PEARL, 16 }, { 5, Items.SNOWBALL, 16 } },
                { { 3, Items.STONE, 64 }, { 4, Items.STONE, 64 }, { 5, Items.STONE, 64 }, { 6, Items.STONE, 64 }, { 7, Items.STONE, 64 }, { 8, Items.STONE, 64 }, { 9, Items.STONE, 64 }, { 10, Items.STONE, 64 }, { 11, Items.STONE, 64 }, { 12, Items.STONE, 64 } },
                { { usable - 1, Items.DIRT, 5 } },
        };
        for(Object[][] c : cases) {
            for(int i = 0; i < be.getContainerSize(); i++) be.setItem(i, ItemStack.EMPTY);
            for(Object[] e : c) be.setItem((int) e[0], s((Item) e[1], (int) e[2]));
            int got = helper.getLevel().getBlockState(abs).getAnalogOutputSignal(helper.getLevel(), abs);
            check(got == originalComparator(be) && got > 0, "the buffer " + be.slots + " gives " + got + ", expected " + originalComparator(be) + " (" + original + ")");
        }
        for(int i = 0; i < usable; i++) be.setItem(i, s(Items.STONE, 64));
        int full = helper.getLevel().getBlockState(abs).getAnalogOutputSignal(helper.getLevel(), abs);
        check(full == originalComparator(be), "a full buffer gives " + full + ", expected " + originalComparator(be));
        be.setItem(usable - 1, ItemStack.EMPTY);
        int less = helper.getLevel().getBlockState(abs).getAnalogOutputSignal(helper.getLevel(), abs);
        check(less == originalComparator(be) && less <= full, "a buffer short of one stack gives " + less + ", expected " + originalComparator(be));
    }

    // CraneBoxer.java:70-78 and CraneUnboxer.java:120-128: the comparator output is the fill level of the container
    @GameTest(template = TEMPLATE, batch = "hbm31c_comparator", timeoutTicks = 100)
    public static void comparator(GameTestHelper helper) {
        guard(() -> {
            comparatorCases(helper, placeCrane(helper, new BlockPos(4, 2, 4), boxerBlock(), Direction.EAST, Direction.WEST, CraneBoxerBlockEntity.class), 21, "CraneBoxer.java:70-78");
            comparatorCases(helper, placeCrane(helper, new BlockPos(10, 2, 4), unboxerBlock(), Direction.EAST, Direction.WEST, CraneUnboxerBlockEntity.class), 21, "CraneUnboxer.java:120-128");
        }).run();
        passed("comparator").run();
        helper.succeed();
    }

    // CraneBoxer.java:86-104: a package enters from every side (also a diagonal step) and each stack goes into the buffer in array order, merging first, the rest drops at the centre
    @GameTest(template = TEMPLATE, batch = "hbm31c_boxer_packages", timeoutTicks = 100)
    public static void boxer_packages(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            CraneBoxerBlock block = (CraneBoxerBlock) boxerBlock();
            CraneBoxerBlockEntity be = placeCrane(helper, new BlockPos(8, 2, 8), boxerBlock(), Direction.EAST, Direction.WEST, CraneBoxerBlockEntity.class);
            BlockPos abs = be.getBlockPos();
            Vec3 at = cellCentre(helper, new BlockPos(8, 2, 12));
            List<Direction> sidesAndNone = new ArrayList<>(Arrays.asList(Direction.values()));
            sidesAndNone.add(null);
            int k = 0;
            for(Direction from : sidesAndNone) {
                for(int i = 0; i < 21; i++) be.setItem(i, ItemStack.EMPTY);
                MovingPackage pack = packageAt(level, at, s(Items.STONE, 64), s(Items.DIRT, 3), s(Items.IRON_INGOT, 5));
                check(block.canPackageEnter(level, abs, from, pack), "a package may not enter from " + from + " (:86-89)");
                pack.enterBlock(block, abs, from);
                check(pack.isRemoved(), "from " + from + ": the package was not removed");
                check(be.getItem(0).is(Items.STONE) && be.getItem(0).getCount() == 64 && be.getItem(1).is(Items.DIRT) && be.getItem(1).getCount() == 3 && be.getItem(2).is(Items.IRON_INGOT) && be.getItem(2).getCount() == 5 && total(be) == 72, "from " + from + ": the buffer holds " + be.slots.subList(0, 4) + " (:96-97 in array order)");
                pack.enterBlock(block, abs, from);
                check(total(be) == 72, "from " + from + ": a removed package entered a second time");
                k++;
            }

            // merging into a partly filled stack, and an overflow that drops at the centre
            for(int i = 0; i < 21; i++) be.setItem(i, ItemStack.EMPTY);
            be.setItem(0, s(Items.STONE, 60));
            MovingPackage merge = packageAt(level, at, s(Items.STONE, 10));
            merge.enterBlock(block, abs, Direction.UP);
            check(be.getItem(0).getCount() == 64 && be.getItem(1).is(Items.STONE) && be.getItem(1).getCount() == 6, "stone merged as " + be.getItem(0) + " / " + be.getItem(1));
            for(int i = 0; i < 21; i++) be.setItem(i, s(Items.COBBLESTONE, 64));
            MovingPackage overflow = packageAt(level, at, s(Items.SAND, 5), s(Items.GRAVEL, 2));
            overflow.enterBlock(block, abs, Direction.NORTH);
            check(overflow.isRemoved() && dropped(helper, Items.SAND) == 5 && dropped(helper, Items.GRAVEL) == 2, "the overflow dropped " + dropped(helper, Items.SAND) + " sand and " + dropped(helper, Items.GRAVEL) + " gravel, expected 5 and 2 (:99-102)");
            for(ItemEntity e : level.getEntitiesOfClass(ItemEntity.class, helper.getBounds())) {
                check(near(e.position(), new Vec3(abs.getX() + 0.5, abs.getY() + 0.5, abs.getZ() + 0.5), 1e-9), "an overflow stack dropped at " + fmt(e.position()) + ", expected the block's centre");
            }
            check(count(be, Items.COBBLESTONE) == 21 * 64, "the full buffer changed");
        }).run();
        passed("boxer_packages").run();
        helper.succeed();
    }

    // TileEntityCraneBoxer.java:163-171 and TileEntityMachineBase.java:131-133: the capability, a side query and vanilla hoppers can put items into all 21 slots from every side,
    // but nothing can be taken out (the unboxer in the same place can be emptied by a hopper, which shows the hopper works)
    @GameTest(template = TEMPLATE, batch = "hbm31c_boxer_access", timeoutTicks = 200)
    public static void boxer_access(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        CraneBoxerBlockEntity boxer = placeCrane(helper, new BlockPos(4, 3, 4), boxerBlock(), Direction.EAST, Direction.WEST, CraneBoxerBlockEntity.class);
        for(int i = 0; i < 5; i++) boxer.setItem(i, s(Items.STONE, 64));
        helper.setBlock(new BlockPos(4, 2, 4), Blocks.HOPPER.defaultBlockState().setValue(HopperBlock.FACING, Direction.DOWN));
        Container below = containerAt(helper, new BlockPos(4, 2, 4));
        CraneUnboxerBlockEntity unboxer = placeCrane(helper, new BlockPos(10, 3, 4), unboxerBlock(), Direction.EAST, Direction.WEST, CraneUnboxerBlockEntity.class);
        for(int i = 0; i < 5; i++) unboxer.setItem(i, s(Items.STONE, 64));
        helper.setBlock(new BlockPos(10, 2, 4), Blocks.HOPPER.defaultBlockState().setValue(HopperBlock.FACING, Direction.DOWN));
        Container unboxerBelow = containerAt(helper, new BlockPos(10, 2, 4));
        CraneBoxerBlockEntity receiver = placeCrane(helper, new BlockPos(4, 2, 10), boxerBlock(), Direction.EAST, Direction.WEST, CraneBoxerBlockEntity.class);
        helper.setBlock(new BlockPos(4, 3, 10), Blocks.HOPPER.defaultBlockState().setValue(HopperBlock.FACING, Direction.DOWN));
        containerAt(helper, new BlockPos(4, 3, 10)).setItem(0, s(Items.STONE, 2));
        helper.setBlock(new BlockPos(5, 2, 10), Blocks.HOPPER.defaultBlockState().setValue(HopperBlock.FACING, Direction.WEST));
        containerAt(helper, new BlockPos(5, 2, 10)).setItem(0, s(Items.DIRT, 2));
        helper.startSequence()
                .thenExecute(guard(() -> {
                    BlockPos abs = boxer.getBlockPos();
                    for(Direction d : Direction.values()) {
                        check(Arrays.equals(boxer.getSlotsForFace(d), CraneBoxerBlockEntity.ACCESS), "getSlotsForFace(" + d + ") is " + Arrays.toString(boxer.getSlotsForFace(d)) + ", expected 0-20 (:163-166)");
                        check(boxer.canPlaceItemThroughFace(20, s(Items.DIRT, 1), d) && !boxer.canTakeItemThroughFace(0, boxer.getItem(0), d), "the face rules of " + d + " are wrong");
                        IItemHandler h = handler(level, abs, d);
                        check(h != null && h.getSlots() == 21, "the handler from " + d + " has " + (h == null ? "no" : h.getSlots()) + " slots, expected 21");
                        check(h.extractItem(0, 64, true).isEmpty() && h.extractItem(0, 64, false).isEmpty() && boxer.getItem(0).getCount() == 64, "an item was taken through the handler from " + d + " (base canExtractItem is false)");
                    }
                    check(handler(level, abs, null) == null, "an unsided query on the boxer gave a handler");
                    IItemHandler h = handler(level, abs, Direction.NORTH);
                    for(int i = 5; i < 21; i++) check(h.insertItem(i, s(Items.DIRT, 1), false).isEmpty(), "slot " + i + " refused an item (:169-171)");
                    check(h.insertItem(0, s(Items.STONE, 1), false).getCount() == 1, "a full stack took more");
                    check(count(boxer, Items.DIRT) == 16, "the boxer holds " + count(boxer, Items.DIRT) + " dirt after 16 inserts");
                    for(int i = 5; i < 21; i++) boxer.setItem(i, ItemStack.EMPTY);
                }))
                .thenExecuteAfter(60, guard(() -> {
                    check(count(boxer, Items.STONE) == 5 * 64 && total(below) == 0, "a hopper took items out of the boxer: it holds " + count(boxer, Items.STONE) + " stone, the hopper " + total(below) + " (nothing can be taken out)");
                    check(count(unboxer, Items.STONE) < 5 * 64 && total(unboxerBelow) > 0, "a hopper did not take anything out of the unboxer (it holds " + count(unboxer, Items.STONE) + "): the setup does not show the hopper working");
                    check(count(receiver, Items.STONE) == 2 && count(receiver, Items.DIRT) == 2, "the hoppers put " + count(receiver, Items.STONE) + " stone (from above) and " + count(receiver, Items.DIRT) + " dirt (from the side) into the boxer, expected 2 and 2");
                    check(total(containerAt(helper, new BlockPos(4, 3, 10))) == 0 && total(containerAt(helper, new BlockPos(5, 2, 10))) == 0, "a feeding hopper still holds items");
                }))
                .thenExecute(passed("boxer_access"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 3. the package entity

    private static CompoundTag entry(HolderLookup.Provider reg, int slot, ItemStack stack) {
        CompoundTag t = new CompoundTag();
        t.putByte("slot", (byte) slot);
        return (CompoundTag) stack.save(reg, t);
    }

    private static MovingPackage loaded(ServerLevel level, CompoundTag tag) {
        MovingPackage q = new MovingPackage(NtmEntityTypes.MOVING_PACKAGE.get(), level);
        q.load(tag);
        return q;
    }

    // EntityMovingPackage.java:24 (0.5 x 0.5), :30-37 (the contents are copies), :102-132 (the contents list with a byte slot and the count): the save round trip keeps the
    // contents and their order; a gap, a short list or a slot past the count loads; an empty package stays alive (the moving item would remove itself)
    @GameTest(template = TEMPLATE, batch = "hbm31c_package_save_load", timeoutTicks = 100)
    public static void package_save_load(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            HolderLookup.Provider reg = level.registryAccess();
            Vec3 at = helper.absoluteVec(new Vec3(8.5, 2.25, 8.5));
            ItemStack typed = MetaHelper.newStack(NtmItems.PART_GENERIC.get(), 3, PartGenericItem.Type.PISTON_PNEUMATIC);
            ItemStack[] stacks = { s(Items.STONE, 64), typed.copy(), s(Items.DIRT, 1), s(Items.IRON_INGOT, 5) };
            MovingPackage p = packageAt(level, at, stacks);
            check(p.getBbWidth() == 0.5F && p.getBbHeight() == 0.5F, "the package is " + p.getBbWidth() + " x " + p.getBbHeight() + ", expected 0.5 x 0.5 (:24)");
            stacks[0].setCount(1);
            stacks[1].setCount(1);
            check(p.getItemStacks().length == 4 && p.getItemStacks()[0].getCount() == 64 && p.getItemStacks()[1].getCount() == 3, "the package did not copy its contents: " + describe(p.getItemStacks()) + " (:31 carefulCopyArray)");

            CompoundTag tag = p.saveWithoutId(new CompoundTag());
            check(tag.contains("count", Tag.TAG_INT) && tag.getInt("count") == 4, "the count is saved as " + tag.get("count") + " (:116)");
            ListTag list = tag.getList("contents", Tag.TAG_COMPOUND);
            check(list.size() == 4, "the contents list has " + list.size() + " entries, expected 4 (:115)");
            for(int i = 0; i < 4; i++) check(list.getCompound(i).contains("slot", Tag.TAG_BYTE) && list.getCompound(i).getByte("slot") == i, "entry " + i + " has the slot " + list.getCompound(i).get("slot") + " (:109)");
            MovingPackage q = loaded(level, tag);
            check(q.getItemStacks().length == 4, "the loaded package holds " + q.getItemStacks().length + " stacks");
            ItemStack[] expected = { s(Items.STONE, 64), typed.copy(), s(Items.DIRT, 1), s(Items.IRON_INGOT, 5) };
            for(int i = 0; i < 4; i++) check(ItemStack.matches(q.getItemStacks()[i], expected[i]), "loaded stack " + i + " is " + q.getItemStacks()[i] + ", expected " + expected[i] + " (:119-132)");
            check(MetaHelper.getMeta(q.getItemStacks()[1]) == PartGenericItem.Type.PISTON_PNEUMATIC.ordinal(), "the type component of the typed part was lost");

            // 21 stacks keep their order
            ItemStack[] full = new ItemStack[21];
            for(int i = 0; i < 21; i++) full[i] = s(KINDS[i], 1 + i);
            MovingPackage big = packageAt(level, at, full);
            MovingPackage bigLoaded = loaded(level, big.saveWithoutId(new CompoundTag()));
            check(bigLoaded.getItemStacks().length == 21, "21 stacks loaded as " + bigLoaded.getItemStacks().length);
            for(int i = 0; i < 21; i++) check(ItemStack.matches(bigLoaded.getItemStacks()[i], full[i]), "stack " + i + " of 21 loaded as " + bigLoaded.getItemStacks()[i]);

            // a gap: the array has the length of count, the missing slot is an empty stack and nothing dereferences it
            CompoundTag gap = new CompoundTag();
            gap.putInt("count", 3);
            ListTag gapList = new ListTag();
            gapList.add(entry(reg, 0, s(Items.STONE, 7)));
            gapList.add(entry(reg, 2, s(Items.DIRT, 2)));
            gap.put("contents", gapList);
            MovingPackage gapped = loaded(level, gap);
            level.addFreshEntity(gapped);
            check(gapped.getItemStacks().length == 3 && gapped.getItemStacks()[1].isEmpty() && gapped.getItemStacks()[0].getCount() == 7 && gapped.getItemStacks()[2].is(Items.DIRT), "the gapped package holds " + describe(gapped.getItemStacks()));
            for(ItemStack st : gapped.getItemStacks()) check(st != null, "the contents array has a null element");
            CranePlayer player = player(helper, GameType.SURVIVAL, 0F);
            player.getInventory().clearContent();
            gapped.interact(player, InteractionHand.MAIN_HAND);
            check(gapped.isRemoved() && count(player.getInventory(), Items.STONE) == 7 && count(player.getInventory(), Items.DIRT) == 2 && invTotal(player) == 9, "a right click on the gapped package gave the player " + invTotal(player) + " items");

            // an empty package stays; a missing tag reads as empty; a slot past the count is ignored; the byte slot counts as unsigned (:126)
            CompoundTag none = new CompoundTag();
            none.putInt("count", 0);
            MovingPackage empty = loaded(level, none);
            check(!empty.isRemoved() && empty.getItemStacks().length == 0, "an empty package removed itself or holds " + empty.getItemStacks().length + " stacks");
            MovingPackage bare = loaded(level, new CompoundTag());
            check(!bare.isRemoved() && bare.getItemStacks().length == 0, "a package without data removed itself");
            CompoundTag past = new CompoundTag();
            past.putInt("count", 2);
            ListTag pastList = new ListTag();
            pastList.add(entry(reg, 5, s(Items.STONE, 1)));
            past.put("contents", pastList);
            MovingPackage outside = loaded(level, past);
            check(outside.getItemStacks().length == 2 && outside.getItemStacks()[0].isEmpty() && outside.getItemStacks()[1].isEmpty(), "a slot past the count was loaded: " + describe(outside.getItemStacks()));
            CompoundTag high = new CompoundTag();
            high.putInt("count", 201);
            ListTag highList = new ListTag();
            highList.add(entry(reg, 200, s(Items.GOLD_INGOT, 1)));
            high.put("contents", highList);
            MovingPackage hi = loaded(level, high);
            check(hi.getItemStacks().length == 201 && hi.getItemStacks()[200].is(Items.GOLD_INGOT), "slot 200 loaded as " + (hi.getItemStacks().length > 200 ? hi.getItemStacks()[200] : "missing"));
        }).run();
        passed("package_save_load").run();
        helper.succeed();
    }

    private static void fillInventory(Player p, Item item) {
        for(int i = 0; i < p.getInventory().items.size(); i++) p.getInventory().items.set(i, s(item, 64));
    }

    // EntityMovingPackage.java:39-54: a right click gives every stack to the player and removes the package; what fits goes into the inventory, the rest is dropped 0.125 above the
    // package (NEO hands the player a copy and drops what is left of it, so nothing is lost or made; the original duplicates the inserted part of a partly fitting stack)
    @GameTest(template = TEMPLATE, batch = "hbm31c_package_interact", timeoutTicks = 100)
    public static void package_interact(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            Vec3 at = helper.absoluteVec(new Vec3(8.5, 2.25, 8.5));
            CranePlayer player = player(helper, GameType.SURVIVAL, 0F);

            // everything fits
            player.getInventory().clearContent();
            MovingPackage a = packageAt(level, at, s(Items.STONE, 64), s(Items.DIRT, 3), s(Items.IRON_INGOT, 5));
            a.interact(player, InteractionHand.MAIN_HAND);
            check(a.isRemoved(), "the package was not removed (:50)");
            check(count(player.getInventory(), Items.STONE) == 64 && count(player.getInventory(), Items.DIRT) == 3 && count(player.getInventory(), Items.IRON_INGOT) == 5, "the player got " + invTotal(player) + " items, expected 72");
            check(level.getEntitiesOfClass(ItemEntity.class, helper.getBounds()).isEmpty(), "items were dropped although everything fits");
            a.interact(player, InteractionHand.MAIN_HAND);
            check(invTotal(player) == 72 && level.getEntitiesOfClass(ItemEntity.class, helper.getBounds()).isEmpty(), "a second right click gave more (:42 isDead)");

            // nothing fits: each stack is dropped whole 0.125 above the package
            player.getInventory().clearContent();
            fillInventory(player, Items.COBBLESTONE);
            MovingPackage b = packageAt(level, at, s(Items.STONE, 64), s(Items.DIRT, 3), s(Items.IRON_INGOT, 5));
            b.interact(player, InteractionHand.MAIN_HAND);
            check(b.isRemoved() && invTotal(player) == 36 * 64, "a full inventory took items: " + invTotal(player));
            check(dropped(helper, Items.STONE) == 64 && dropped(helper, Items.DIRT) == 3 && dropped(helper, Items.IRON_INGOT) == 5, "dropped " + dropped(helper, Items.STONE) + " stone, " + dropped(helper, Items.DIRT) + " dirt, " + dropped(helper, Items.IRON_INGOT) + " iron, expected 64 / 3 / 5 (:46)");
            Vec3 dropAt = at.add(0, 0.125, 0);
            for(ItemEntity e : level.getEntitiesOfClass(ItemEntity.class, helper.getBounds())) check(near(e.position(), dropAt, 1e-9), "a stack dropped at " + fmt(e.position()) + ", expected " + fmt(dropAt) + " (0.125 above the package)");
            clearEntities(helper);

            // room for 10 of a stack of 64: 10 go into the inventory, the other 54 are dropped; the stack that finds no room is dropped whole
            player.getInventory().clearContent();
            fillInventory(player, Items.COBBLESTONE);
            player.getInventory().items.set(20, s(Items.STONE, 54));
            MovingPackage c = packageAt(level, at, s(Items.STONE, 64), s(Items.DIRT, 3));
            c.interact(player, InteractionHand.MAIN_HAND);
            check(c.isRemoved() && count(player.getInventory(), Items.STONE) == 64 && count(player.getInventory(), Items.DIRT) == 0, "a partly fitting stack: the inventory holds " + count(player.getInventory(), Items.STONE) + " stone, expected 64");
            check(dropped(helper, Items.STONE) == 54 && dropped(helper, Items.DIRT) == 3, "dropped " + dropped(helper, Items.STONE) + " stone and " + dropped(helper, Items.DIRT) + " dirt, expected 54 and 3: 118 stone before, 64 + 54 after");
            clearEntities(helper);
        }).run();
        passed("package_interact").run();
        helper.succeed();
    }

    // EntityMovingPackage.java:56-73: any hit breaks the package open and drops every stack 0.125 above it, once; NEO routes a player's attack through skipAttackInteraction and
    // other damage through hurt
    @GameTest(template = TEMPLATE, batch = "hbm31c_package_hit", timeoutTicks = 100)
    public static void package_hit(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            Vec3 at = helper.absoluteVec(new Vec3(8.5, 2.25, 8.5));
            CranePlayer player = player(helper, GameType.SURVIVAL, 0F);
            for(int kind = 0; kind < 3; kind++) {
                MovingPackage p = packageAt(level, at, s(Items.STONE, 64), s(Items.DIRT, 3), s(Items.IRON_INGOT, 5));
                String ctx = new String[] { "a player's attack", "generic damage", "damage by a player" }[kind];
                boolean result = switch(kind) {
                    case 0 -> p.skipAttackInteraction(player);
                    case 1 -> p.hurt(level.damageSources().generic(), 4.0F);
                    default -> p.hurt(level.damageSources().playerAttack(player), 4.0F);
                };
                check(result, ctx + " was not consumed");
                check(p.isRemoved(), ctx + ": the package was not removed (:60)");
                check(dropped(helper, Items.STONE) == 64 && dropped(helper, Items.DIRT) == 3 && dropped(helper, Items.IRON_INGOT) == 5, ctx + ": dropped " + dropped(helper, Items.STONE) + " / " + dropped(helper, Items.DIRT) + " / " + dropped(helper, Items.IRON_INGOT) + ", expected 64 / 3 / 5 (:62-64)");
                for(ItemEntity e : level.getEntitiesOfClass(ItemEntity.class, helper.getBounds())) check(near(e.position(), at.add(0, 0.125, 0), 1e-9), ctx + ": a stack dropped at " + fmt(e.position()) + ", expected 0.125 above the package");
                // a second hit on the same, already removed package drops nothing more
                p.skipAttackInteraction(player);
                p.hurt(level.damageSources().generic(), 4.0F);
                check(dropped(helper, Items.STONE) == 64 && dropped(helper, Items.DIRT) == 3, ctx + ": a hit on a removed package dropped more (:59 isDead)");
                clearEntities(helper);
            }
            MovingPackage emptyPack = packageAt(level, at);
            check(emptyPack.hurt(level.damageSources().generic(), 1.0F) && emptyPack.isRemoved() && dropped(helper, Items.STONE) == 0, "an empty package misbehaved when hit");
        }).run();
        passed("package_hit").run();
        helper.succeed();
    }

    // EntityMovingPackage.java:85-100: leaving the belt removes the package and drops every stack at position + 2 x motion with 2 x motion and 0.1 up; the item entities keep the
    // default lifespan of 6000 ticks (the moving item sets 1200); NEO drops nothing for a package that is already gone
    @GameTest(template = TEMPLATE, batch = "hbm31c_package_leave", timeoutTicks = 100)
    public static void package_leave(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            Vec3 at = helper.absoluteVec(new Vec3(8.5, 2.25, 8.5));
            Vec3 motion = new Vec3(0.0625, 0, -0.1875);
            MovingPackage p = packageAt(level, at, s(Items.STONE, 5), s(Items.DIRT, 2), s(Items.IRON_INGOT, 3));
            p.setDeltaMovement(motion);
            check(p.onLeaveConveyor(), "onLeaveConveyor returned false (:99)");
            check(p.isRemoved(), "the package was not removed (:88)");
            List<ItemEntity> drops = level.getEntitiesOfClass(ItemEntity.class, new AABB(helper.absolutePos(new BlockPos(8, 2, 8))).inflate(2));
            check(drops.size() == 3, drops.size() + " item entities appeared, expected 3");
            Vec3 where = at.add(motion.scale(2));
            Set<Item> seen = new HashSet<>();
            for(ItemEntity e : drops) {
                check(near(e.position(), where, 1e-9), "an item entity appeared at " + fmt(e.position()) + ", expected " + fmt(where) + " (:91)");
                check(near(e.getDeltaMovement(), new Vec3(0.125, 0.1, -0.375), 1e-9), "an item entity moves with " + fmt(e.getDeltaMovement()) + ", expected (0.125, 0.1, -0.375) (:92-94)");
                check(e.lifespan == 6000 && e.lifespan != 1200, "an item entity has the lifespan " + e.lifespan + ", expected the default 6000 (no 1200 as the moving item)");
                seen.add(e.getItem().getItem());
                int want = e.getItem().is(Items.STONE) ? 5 : e.getItem().is(Items.DIRT) ? 2 : 3;
                check(e.getItem().getCount() == want, "the stack " + e.getItem() + " has the wrong count");
            }
            check(seen.equals(Set.of(Items.STONE, Items.DIRT, Items.IRON_INGOT)), "the dropped items are " + seen);
            for(ItemEntity e : drops) e.discard();
            check(p.onLeaveConveyor(), "a second onLeaveConveyor returned false");
            check(level.getEntitiesOfClass(ItemEntity.class, new AABB(helper.absolutePos(new BlockPos(8, 2, 8))).inflate(2)).isEmpty(), "a package that was already removed dropped its contents again");

            // removed by a hit first: nothing more on the belt end either
            MovingPackage hit = packageAt(level, at, s(Items.STONE, 5));
            hit.hurt(level.damageSources().generic(), 1.0F);
            clearEntities(helper);
            hit.onLeaveConveyor();
            check(dropped(helper, Items.STONE) == 0, "a broken package dropped its contents at the end of a belt");
        }).run();
        passed("package_leave").run();
        helper.succeed();
    }

    // EntityMovingConveyorObject.java:109-120 + EntityMovingPackage.java:85-100 through the real tick: a package at the end of a belt scatters its stacks just past the end
    @GameTest(template = TEMPLATE, batch = "hbm31c_package_leave_natural", timeoutTicks = 200)
    public static void package_leave_natural(GameTestHelper helper) {
        for(int z = 2; z <= 3; z++) helper.setBlock(new BlockPos(6, 2, z), beltState(Direction.NORTH));
        MovingPackage[] pack = new MovingPackage[1];
        helper.startSequence()
                .thenExecute(guard(() -> pack[0] = packageAt(helper.getLevel(), helper.absoluteVec(new Vec3(6.5, 2.25, 2.5)), s(Items.STONE, 5), s(Items.DIRT, 2), s(Items.IRON_INGOT, 3))))
                .thenWaitUntil(guard(() -> check(pack[0].isRemoved(), "the package has not left the two-block belt yet")))
                .thenExecute(guard(() -> {
                    BlockPos endCell = helper.absolutePos(new BlockPos(6, 2, 4));
                    List<ItemEntity> drops = helper.getLevel().getEntitiesOfClass(ItemEntity.class, new AABB(endCell).inflate(3));
                    check(drops.size() == 3, drops.size() + " item entities appeared, expected 3");
                    for(ItemEntity e : drops) {
                        check(e.lifespan == 6000, "an item entity has the lifespan " + e.lifespan + ", expected 6000");
                        check(e.getZ() > endCell.getZ() + 0.1 && e.getZ() < endCell.getZ() + 0.4 && Math.abs(e.getX() - (endCell.getX() + 0.5)) < 1e-6, "a stack appeared at " + fmt(e.position()) + ", expected just past the end of the belt on its line");
                    }
                    check(dropped(helper, Items.STONE) == 5 && dropped(helper, Items.DIRT) == 2 && dropped(helper, Items.IRON_INGOT) == 3, "the drops hold " + dropped(helper, Items.STONE) + " / " + dropped(helper, Items.DIRT) + " / " + dropped(helper, Items.IRON_INGOT));
                }))
                .thenExecute(passed("package_leave_natural"))
                .thenSucceed();
    }

    // EntityMovingPackage.java:75-83: a block that accepts the package gets its contents once and the package is removed; one that does not leaves it alone
    @GameTest(template = TEMPLATE, batch = "hbm31c_package_enter", timeoutTicks = 100)
    public static void package_enter(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            Vec3 at = helper.absoluteVec(new Vec3(8.5, 2.25, 8.5));

            // the inserter (CraneInserter.java:148-189): every side, also none
            CraneInserterBlockEntity ins = placeCrane(helper, new BlockPos(4, 2, 4), inserterBlock(), Direction.EAST, Direction.WEST, CraneInserterBlockEntity.class);
            Container chest = chest(helper, new BlockPos(3, 2, 4));
            CraneInserterBlock insBlock = (CraneInserterBlock) inserterBlock();
            for(Direction from : new Direction[] { Direction.NORTH, null }) {
                chest.clearContent();
                MovingPackage p = packageAt(level, at, s(Items.STONE, 30), s(Items.DIRT, 3), s(Items.IRON_INGOT, 64));
                p.enterBlock(insBlock, ins.getBlockPos(), from);
                check(p.isRemoved() && count(chest, Items.STONE) == 30 && count(chest, Items.DIRT) == 3 && count(chest, Items.IRON_INGOT) == 64 && total(ins) == 0, "inserter from " + from + ": removed " + p.isRemoved() + ", chest " + total(chest) + ", buffer " + total(ins));
                p.enterBlock(insBlock, ins.getBlockPos(), from);
                check(total(chest) == 97, "inserter from " + from + ": a removed package handed its contents out again (" + total(chest) + " items)");
            }

            // the boxer (CraneBoxer.java:86-104)
            CraneBoxerBlockEntity boxer = placeCrane(helper, new BlockPos(4, 2, 10), boxerBlock(), Direction.EAST, Direction.WEST, CraneBoxerBlockEntity.class);
            MovingPackage toBoxer = packageAt(level, at, s(Items.STONE, 30), s(Items.DIRT, 3));
            toBoxer.enterBlock((CraneBoxerBlock) boxerBlock(), boxer.getBlockPos(), Direction.SOUTH);
            toBoxer.enterBlock((CraneBoxerBlock) boxerBlock(), boxer.getBlockPos(), Direction.SOUTH);
            check(toBoxer.isRemoved() && total(boxer) == 33 && boxer.getItem(0).getCount() == 30 && boxer.getItem(1).getCount() == 3, "boxer: removed " + toBoxer.isRemoved() + ", the buffer holds " + total(boxer) + " items, expected 33 once");

            // the unboxer (CraneUnboxer.java:100-118): only through the output side
            CraneUnboxerBlockEntity unboxer = placeCrane(helper, new BlockPos(10, 2, 4), unboxerBlock(), Direction.EAST, Direction.WEST, CraneUnboxerBlockEntity.class);
            CraneUnboxerBlock unBlock = (CraneUnboxerBlock) unboxerBlock();
            MovingPackage toUnboxer = packageAt(level, at, s(Items.STONE, 30), s(Items.DIRT, 3));
            for(Direction wrong : new Direction[] { Direction.EAST, Direction.NORTH, Direction.SOUTH, Direction.UP, Direction.DOWN, null }) {
                toUnboxer.enterBlock(unBlock, unboxer.getBlockPos(), wrong);
                check(!toUnboxer.isRemoved() && total(unboxer) == 0 && dropped(helper, Items.STONE) == 0, "unboxer from " + wrong + ": removed " + toUnboxer.isRemoved() + ", buffer " + total(unboxer) + " (:100-103)");
            }
            toUnboxer.enterBlock(unBlock, unboxer.getBlockPos(), Direction.WEST);
            toUnboxer.enterBlock(unBlock, unboxer.getBlockPos(), Direction.WEST);
            check(toUnboxer.isRemoved() && total(unboxer) == 33 && unboxer.getItem(0).getCount() == 30 && unboxer.getItem(1).getCount() == 3, "unboxer: removed " + toUnboxer.isRemoved() + ", the buffer holds " + total(unboxer) + " items, expected 33 once");

            // a single item never enters the unboxer (:92-98)
            MovingItem single = movingAt(level, at, s(Items.STONE, 1));
            for(Direction from : new Direction[] { Direction.WEST, Direction.EAST, null }) {
                single.enterBlock(unBlock, unboxer.getBlockPos(), from);
                check(!single.isRemoved() && total(unboxer) == 33, "a single item entered the unboxer from " + from);
            }
            single.discard();
        }).run();
        passed("package_enter").run();
        helper.succeed();
    }

    private static int idFor(int tickOfCheck) {
        return Math.floorMod(-2 * tickOfCheck, 400);
    }

    /**
     * Conveyor objects stacked on one spot as in Goal31A: the owner has the even id for which (tickCount * 2 + id) % 400 == 0 on the tick after {@code tickBefore} (the doubled
     * counter of EntityMovingConveyorObject.java:86), every other member an odd id, which never matches.
     */
    private static List<com.hbm.entity.item.MovingConveyorObject> crowd(ServerLevel level, Vec3 at, int packages, int items, boolean itemOwner, int base, int tickBefore) {
        check(base % 400 == 0, "the id base " + base + " is not a multiple of 400");
        List<com.hbm.entity.item.MovingConveyorObject> list = new ArrayList<>();
        for(int i = 0; i < packages + items; i++) {
            boolean pack = itemOwner ? i >= items : i < packages;
            com.hbm.entity.item.MovingConveyorObject e;
            if(pack) {
                MovingPackage p = new MovingPackage(NtmEntityTypes.MOVING_PACKAGE.get(), level);
                p.setPos(at.x, at.y, at.z);
                p.setItemStacks(new ItemStack[] { s(Items.IRON_NUGGET, 1) });
                e = p;
            } else {
                MovingItem m = new MovingItem(NtmEntityTypes.MOVING_ITEM.get(), level);
                m.setPos(at.x, at.y, at.z);
                m.setItemStack(s(Items.GOLD_NUGGET, 1));
                e = m;
            }
            e.setId(i == 0 ? base + idFor(tickBefore + 1) : base + 1 + 2 * i);
            e.tickCount = tickBefore;
            list.add(e);
        }
        for(com.hbm.entity.item.MovingConveyorObject e : list) level.addFreshEntity(e);
        return list;
    }

    private static int alive(List<com.hbm.entity.item.MovingConveyorObject> list) {
        int n = 0;
        for(com.hbm.entity.item.MovingConveyorObject e : list) if(!e.isRemoved()) n++;
        return n;
    }

    // EntityMovingConveyorObject.java:85-100: packages count with moving items in the cram check (25 or more within 0.125 of the box are all removed without a drop); a package
    // the check removed gives nothing when it is asked to leave the belt afterwards
    @GameTest(template = TEMPLATE, batch = "hbm31c_package_cram", timeoutTicks = 100)
    public static void package_cram(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos[] cells = { new BlockPos(2, 2, 2), new BlockPos(6, 2, 2), new BlockPos(10, 2, 2), new BlockPos(2, 2, 9), new BlockPos(6, 2, 9) };
        for(BlockPos c : cells) for(int k = 0; k < 4; k++) helper.setBlock(c.south(k), beltState(Direction.NORTH));
        int[] packages = { 25, 12, 13, 12, 25 };
        int[] items = { 0, 13, 12, 12, 0 };
        boolean[] itemOwner = { false, true, false, false, false };
        boolean[] cleared = { true, true, true, false, true };
        String[] what = { "25 packages", "12 packages and 13 items, an item owns the check", "13 packages and 12 items, a package owns the check", "12 packages and 12 items, one below the limit", "25 packages whose owner counts every object" };
        List<List<com.hbm.entity.item.MovingConveyorObject>> crowds = new ArrayList<>();
        helper.startSequence()
                .thenExecute(guard(() -> {
                    check(NtmConfig.SERVER.CONVEYOR_CRAM_MAX.get() == 25, "the cram limit is not 25");
                    for(int i = 0; i < cells.length; i++) {
                        Vec3 centre = helper.absoluteVec(new Vec3(cells[i].getX() + 0.5, cells[i].getY() + 0.25, cells[i].getZ() + 0.5));
                        crowds.add(crowd(level, centre, packages[i], items[i], itemOwner[i], 6_000_000 + 400 * (i + 1), 300));
                    }
                }))
                .thenExecuteAfter(1, guard(() -> {
                    for(int i = 0; i < cells.length; i++) {
                        check((alive(crowds.get(i)) == 0) == cleared[i], what[i] + ": " + alive(crowds.get(i)) + " of " + (packages[i] + items[i]) + " objects survived, expected " + (cleared[i] ? "none" : "all") + " (:87-89)");
                    }
                    check(level.getEntitiesOfClass(ItemEntity.class, helper.getBounds()).isEmpty(), "items dropped when the objects were cleared (:89 no drops)");
                    // a cleared package asked to leave the belt drops nothing
                    for(int i = 0; i < cells.length; i++) {
                        if(!cleared[i]) continue;
                        for(com.hbm.entity.item.MovingConveyorObject e : crowds.get(i)) {
                            if(e instanceof MovingPackage p) check(p.onLeaveConveyor(), "onLeaveConveyor returned false");
                        }
                    }
                    check(level.getEntitiesOfClass(ItemEntity.class, helper.getBounds()).isEmpty(), "a package cleared by the cram check dropped its contents when asked to leave");
                }))
                .thenExecute(passed("package_cram"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 4. the inserter with real packages

    // CraneInserter.java:150-189: a real package entering an inserter: every stack follows the rules of a single item (target, then own buffer, then destroyed or dropped by
    // the destroyer switch; a signal keeps the target out of it)
    @GameTest(template = TEMPLATE, batch = "hbm31c_inserter_real_package", timeoutTicks = 100)
    public static void inserter_real_package(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            Vec3 at = helper.absoluteVec(new Vec3(8.5, 2.25, 12.5));
            CraneInserterBlock block = (CraneInserterBlock) inserterBlock();
            BlockPos rel = new BlockPos(8, 2, 8);
            CraneInserterBlockEntity be = placeCrane(helper, rel, inserterBlock(), Direction.EAST, Direction.WEST, CraneInserterBlockEntity.class);
            Container chest = chest(helper, rel.west());
            check(be.destroyer, "the destroyer is off by default (TileEntityCraneInserter.java:27)");

            // the target takes everything
            MovingPackage a = packageAt(level, at, s(Items.STONE, 30), s(Items.DIRT, 3), s(Items.IRON_INGOT, 64));
            a.enterBlock(block, be.getBlockPos(), Direction.SOUTH);
            check(a.isRemoved() && count(chest, Items.STONE) == 30 && count(chest, Items.DIRT) == 3 && count(chest, Items.IRON_INGOT) == 64 && total(be) == 0, "into a chest: removed " + a.isRemoved() + ", chest " + total(chest) + ", buffer " + total(be) + " (:172)");

            // the target is full, the buffer has one free slot: stone goes there, gravel is destroyed
            fill(chest, Items.COBBLESTONE, 64);
            for(int i = 0; i < 20; i++) be.setItem(i, s(Items.SAND, 64));
            MovingPackage b = packageAt(level, at, s(Items.STONE, 6), s(Items.GRAVEL, 64), s(Items.GRAVEL, 5), s(Items.STONE, 3));
            b.enterBlock(block, be.getBlockPos(), null);
            check(b.isRemoved() && count(be, Items.STONE) == 9 && count(be, Items.GRAVEL) == 0 && dropped(helper, Items.GRAVEL) == 0, "overflow, destroyer on: removed " + b.isRemoved() + ", buffer stone " + count(be, Items.STONE) + ", gravel " + count(be, Items.GRAVEL) + ", dropped gravel " + dropped(helper, Items.GRAVEL) + " (:176-188)");

            // destroyer off: what the buffer cannot hold drops at the block's centre
            be.destroyer = false;
            MovingPackage c = packageAt(level, at, s(Items.GRAVEL, 7), s(Items.STONE, 20));
            c.enterBlock(block, be.getBlockPos(), Direction.EAST);
            check(dropped(helper, Items.GRAVEL) == 7 && count(be, Items.STONE) == 29, "destroyer off: dropped gravel " + dropped(helper, Items.GRAVEL) + ", buffer stone " + count(be, Items.STONE) + ", expected 7 and 29");
            for(ItemEntity e : level.getEntitiesOfClass(ItemEntity.class, helper.getBounds())) {
                check(near(e.position(), new Vec3(be.getBlockPos().getX() + 0.5, be.getBlockPos().getY() + 0.5, be.getBlockPos().getZ() + 0.5), 1e-9), "an overflow stack dropped at " + fmt(e.position()) + ", expected the block's centre (:185)");
            }
            clearEntities(helper);

            // a signal: the target is not used (:161), the stacks go to the buffer
            be.destroyer = true;
            chest.clearContent();
            for(int i = 0; i < 21; i++) be.setItem(i, ItemStack.EMPTY);
            helper.setBlock(rel.above(), Blocks.REDSTONE_BLOCK.defaultBlockState());
            MovingPackage d = packageAt(level, at, s(Items.DIRT, 5), s(Items.SAND, 2));
            d.enterBlock(block, be.getBlockPos(), Direction.NORTH);
            check(d.isRemoved() && total(chest) == 0 && count(be, Items.DIRT) == 5 && count(be, Items.SAND) == 2, "powered: chest " + total(chest) + ", buffer dirt " + count(be, Items.DIRT) + " sand " + count(be, Items.SAND) + " (:161-174)");
        }).run();
        passed("inserter_real_package").run();
        helper.succeed();
    }

    // CraneInserter.java:148-189 with the real tick: a package riding a belt into the side of an inserter hands its contents to the chest once
    @GameTest(template = TEMPLATE, batch = "hbm31c_inserter_package_belt", timeoutTicks = 300)
    public static void inserter_package_belt(GameTestHelper helper) {
        CraneInserterBlockEntity be = placeCrane(helper, new BlockPos(8, 2, 8), inserterBlock(), Direction.SOUTH, Direction.NORTH, CraneInserterBlockEntity.class);
        Container chest = chest(helper, new BlockPos(8, 2, 7));
        for(int x = 3; x <= 7; x++) helper.setBlock(new BlockPos(x, 2, 8), beltState(Direction.WEST));
        helper.startSequence()
                .thenExecute(guard(() -> packageAt(helper.getLevel(), helper.absoluteVec(new Vec3(3.5, 2.25, 8.5)), s(Items.STONE, 30), s(Items.DIRT, 3))))
                .thenWaitUntil(guard(() -> check(total(chest) > 0, "the package has not arrived yet")))
                .thenExecuteAfter(10, guard(() -> {
                    check(count(chest, Items.STONE) == 30 && count(chest, Items.DIRT) == 3 && total(be) == 0 && loose(helper, Items.STONE) == 0, "the chest holds " + count(chest, Items.STONE) + " stone and " + count(chest, Items.DIRT) + " dirt, the buffer " + total(be) + ", loose " + loose(helper, Items.STONE));
                    check(helper.getLevel().getEntitiesOfClass(MovingPackage.class, helper.getBounds()).isEmpty(), "the package is still there");
                }))
                .thenExecute(passed("inserter_package_belt"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 5. the unboxer

    // CraneUnboxer.java:92-118: single items never enter; a package enters only through the output side (a diagonal step has no side); its stacks fill the slots 0-20 only, merging
    // first, what does not fit drops at the centre, and never an upgrade slot 21 / 22, not even for an upgrade item or with a full buffer
    @GameTest(template = TEMPLATE, batch = "hbm31c_unboxer_enter", timeoutTicks = 100)
    public static void unboxer_enter(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            CraneUnboxerBlock block = (CraneUnboxerBlock) unboxerBlock();
            BlockPos rel = new BlockPos(8, 3, 8);
            BlockPos abs = helper.absolutePos(rel);
            Vec3 at = helper.absoluteVec(new Vec3(8.5, 2.25, 12.5));
            MovingItem item = movingAt(level, at, s(Items.STONE, 1));
            MovingPackage probe = packageAt(level, at, s(Items.STONE, 1));
            int states = 0;
            for(Direction in : Direction.values()) for(Direction out : Direction.values()) {
                if(in == out) continue;
                helper.setBlock(rel, crane(unboxerBlock(), in, out));
                for(Direction from : Direction.values()) {
                    check(!block.canItemEnter(level, abs, from, item), "(" + in + ", " + out + "): an item may enter from " + from + " (:92-95)");
                    check(block.canPackageEnter(level, abs, from, probe) == (from == out), "(" + in + ", " + out + "): canPackageEnter from " + from + " is " + (from != out) + " (:100-103)");
                }
                check(!block.canItemEnter(level, abs, null, item) && !block.canPackageEnter(level, abs, null, probe), "(" + in + ", " + out + "): something enters without a side");
                states++;
            }
            check(states == 30, "the loop covered " + states + " orientations");
            item.discard();
            probe.discard();

            CraneUnboxerBlockEntity be = placeCrane(helper, rel, unboxerBlock(), Direction.EAST, Direction.WEST, CraneUnboxerBlockEntity.class);
            // the contents go in array order from slot 0
            MovingPackage p = packageAt(level, at, s(Items.STONE, 64), s(Items.DIRT, 10), s(Items.STONE, 20));
            p.enterBlock(block, abs, Direction.WEST);
            check(p.isRemoved() && be.getItem(0).getCount() == 64 && be.getItem(1).is(Items.DIRT) && be.getItem(2).is(Items.STONE) && be.getItem(2).getCount() == 20 && total(be) == 94, "the buffer holds " + be.slots.subList(0, 4) + " (:110-117 in array order)");

            // a full buffer: the overflow drops at the centre, the upgrade slots stay empty, also for an upgrade item
            for(int i = 0; i < 21; i++) be.setItem(i, s(Items.COBBLESTONE, 64));
            MovingPackage over = packageAt(level, at, s(Items.SAND, 5), s(NtmItems.UPGRADE_STACK_1.get(), 1), s(NtmItems.UPGRADE_EJECTOR_2.get(), 1));
            over.enterBlock(block, abs, Direction.WEST);
            check(over.isRemoved() && be.getItem(21).isEmpty() && be.getItem(22).isEmpty(), "an upgrade slot received " + be.getItem(21) + " / " + be.getItem(22) + " from a package");
            check(dropped(helper, Items.SAND) == 5 && dropped(helper, NtmItems.UPGRADE_STACK_1.get()) == 1 && dropped(helper, NtmItems.UPGRADE_EJECTOR_2.get()) == 1, "the overflow dropped " + dropped(helper, Items.SAND) + " sand, " + dropped(helper, NtmItems.UPGRADE_STACK_1.get()) + " stack upgrades, " + dropped(helper, NtmItems.UPGRADE_EJECTOR_2.get()) + " ejector upgrades (:113-116)");
            for(ItemEntity e : level.getEntitiesOfClass(ItemEntity.class, helper.getBounds())) {
                check(near(e.position(), new Vec3(abs.getX() + 0.5, abs.getY() + 0.5, abs.getZ() + 0.5), 1e-9), "an overflow stack dropped at " + fmt(e.position()) + ", expected the block's centre");
            }
            clearEntities(helper);

            // with a free buffer slot an upgrade item goes there, not into the upgrade slot
            be.setItem(7, ItemStack.EMPTY);
            MovingPackage up = packageAt(level, at, s(NtmItems.UPGRADE_STACK_2.get(), 1));
            up.enterBlock(block, abs, Direction.WEST);
            check(be.getItem(7).is(NtmItems.UPGRADE_STACK_2.get()) && be.getItem(21).isEmpty(), "an upgrade item in a package went to " + be.getItem(7) + " / " + be.getItem(21));
        }).run();
        passed("unboxer_enter").run();
        helper.succeed();
    }

    // TileEntityCraneUnboxer.java:35-91: at every multiple of the delay (20, with the ejector upgrade 10 / 5 / 2) and without a signal, the first filled buffer slot sends up to the
    // amount (1, with the stack upgrade 4 / 16 / 64, never more than the stack holds) onto the belt on the INPUT side (:65 "note the switcheroo"), at the snapping point
    // 0.55 toward it; nothing without a belt there, nothing to a belt on the other side
    @GameTest(template = TEMPLATE, batch = "hbm31c_unboxer_emit", timeoutTicks = 200)
    public static void unboxer_emit(GameTestHelper helper) {
        // [ejector tier, stack tier, kind]: 0 plain, 1 no belt, 2 powered, 3 belt on the output side only, 4 double belt on the input side, 5 a small first stack
        int[][] rigs = { { 0, 0, 0 }, { 1, 1, 0 }, { 2, 2, 0 }, { 3, 3, 0 }, { 3, 3, 1 }, { 3, 3, 2 }, { 3, 3, 3 }, { 3, 3, 4 }, { 3, 2, 5 } };
        int[] delays = { 20, 10, 5, 2 };
        int[] amounts = { 1, 4, 16, 64 };
        List<CraneUnboxerBlockEntity> boxes = new ArrayList<>();
        List<BlockPos> cells = new ArrayList<>();
        for(int k = 0; k < rigs.length; k++) {
            BlockPos rel = new BlockPos(8, 2, 1 + 1 * k + (k >= 4 ? 1 : 0) + (k >= 7 ? 1 : 0));
            cells.add(rel);
            CraneUnboxerBlockEntity be = detachedUnboxer(helper, rel, Direction.EAST, Direction.WEST);
            be.slots.set(CraneUnboxerBlockEntity.SLOT_EJECTOR_UPGRADE, ejectorUpgrade(rigs[k][0]));
            be.slots.set(CraneUnboxerBlockEntity.SLOT_STACK_UPGRADE, stackUpgrade(rigs[k][1]));
            switch(rigs[k][2]) {
                case 1 -> { }
                case 3 -> helper.setBlock(rel.west(), beltState(Direction.SOUTH));
                case 4 -> {
                    helper.setBlock(rel.east(), belt(NtmBlocks.CONVEYOR_DOUBLE.get(), Direction.SOUTH));
                    helper.setBlock(rel.west(), beltState(Direction.SOUTH));
                }
                default -> {
                    helper.setBlock(rel.east(), beltState(Direction.SOUTH));
                    helper.setBlock(rel.west(), beltState(Direction.SOUTH));
                }
            }
            if(rigs[k][2] == 2) helper.setBlock(rel.above(), Blocks.REDSTONE_BLOCK.defaultBlockState());
            boxes.add(be);
        }
        int[] emissions = new int[rigs.length];
        helper.startSequence()
                .thenExecuteFor(46, guard(() -> {
                    ServerLevel level = helper.getLevel();
                    long t = level.getGameTime();
                    for(int k = 0; k < rigs.length; k++) {
                        CraneUnboxerBlockEntity be = boxes.get(k);
                        BlockPos here = cells.get(k);
                        int kind = rigs[k][2];
                        for(int i = 0; i < 23; i++) if(i < 21 || i > 22) be.slots.set(i, ItemStack.EMPTY);
                        int first = kind == 5 ? 3 : 3;
                        be.slots.set(first, s(Items.STONE, kind == 5 ? 3 : 64));
                        be.slots.set(5, s(Items.DIRT, 64));
                        be.slots.set(0 + 1, ItemStack.EMPTY);
                        for(MovingItem m : movingIn(helper, here.east())) m.discard();
                        for(MovingItem m : movingIn(helper, here.west())) m.discard();
                        be.updateEntity();
                        int delay = delays[rigs[k][0]];
                        boolean acts = t % delay == 0 && kind != 1 && kind != 2 && kind != 3;
                        List<MovingItem> east = movingIn(helper, here.east());
                        String ctx = "rig " + k + " (ejector " + rigs[k][0] + ", stack " + rigs[k][1] + ", kind " + kind + ") at world time " + t;
                        check(movingIn(helper, here.west()).isEmpty(), ctx + ": something was put on the output side belt (:65)");
                        if(acts) {
                            int amount = Math.min(amounts[rigs[k][1]], kind == 5 ? 3 : 64);
                            check(east.size() == 1 && east.get(0).getItemStack().is(Items.STONE) && east.get(0).getItemStack().getCount() == amount, ctx + ": the belt received " + east.size() + " stacks " + (east.isEmpty() ? "" : east.get(0).getItemStack()) + ", expected 1 stack of " + amount + " stone (:54-80)");
                            check(be.getItem(first).getCount() == (kind == 5 ? 3 : 64) - amount && be.getItem(5).getCount() == 64, ctx + ": the buffer holds " + be.getItem(first) + " / " + be.getItem(5) + " after the action");
                            double x = kind == 4 ? 9.25 : 9.5;
                            Vec3 expected = helper.absoluteVec(new Vec3(x, 2.25, here.getZ() + 0.5));
                            check(near(east.get(0).position(), expected, 1e-9), ctx + ": the item stands at " + fmt(east.get(0).position()) + ", expected " + fmt(expected) + " (:82-85 snapping point 0.55 toward the input side)");
                            emissions[k]++;
                        } else {
                            check(east.isEmpty() && be.getItem(first).getCount() == (kind == 5 ? 3 : 64), ctx + ": an action happened (belt " + east.size() + ", slot " + be.getItem(first) + ")");
                        }
                    }
                }))
                .thenExecute(guard(() -> {
                    check(emissions[0] >= 2 && emissions[1] >= 4 && emissions[2] >= 9 && emissions[3] >= 23, "the actions in 46 ticks were " + Arrays.toString(emissions) + ", expected at least 2 / 4 / 9 / 23");
                }))
                .thenExecute(passed("unboxer_emit"))
                .thenSucceed();
    }

    // TileEntityCraneUnboxer.java:95-108: through the capability the unboxer shows the buffer 0-20 for putting in and taking out, from every side, and no upgrade slot
    @GameTest(template = TEMPLATE, batch = "hbm31c_unboxer_capability", timeoutTicks = 100)
    public static void unboxer_capability(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            CraneUnboxerBlockEntity be = placeCrane(helper, new BlockPos(8, 2, 8), unboxerBlock(), Direction.EAST, Direction.WEST, CraneUnboxerBlockEntity.class);
            BlockPos abs = be.getBlockPos();
            be.setItem(21, s(NtmItems.UPGRADE_STACK_3.get(), 1));
            be.setItem(22, s(NtmItems.UPGRADE_EJECTOR_3.get(), 1));
            be.setItem(4, s(Items.STONE, 5));
            for(Direction d : Direction.values()) {
                check(Arrays.equals(be.getSlotsForFace(d), CraneUnboxerBlockEntity.ACCESS), "getSlotsForFace(" + d + ") is " + Arrays.toString(be.getSlotsForFace(d)) + ", expected 0-20 (:95-98)");
                IItemHandler h = handler(level, abs, d);
                check(h != null && h.getSlots() == 21, "the handler from " + d + " has " + (h == null ? "none" : h.getSlots()) + " slots, expected 21");
                check(be.canPlaceItemThroughFace(20, s(Items.DIRT, 1), d) && !be.canPlaceItemThroughFace(21, s(NtmItems.UPGRADE_STACK_1.get(), 1), d) && !be.canPlaceItemThroughFace(22, s(NtmItems.UPGRADE_EJECTOR_1.get(), 1), d), "the placing rules of " + d + " are wrong");
                check(be.canTakeItemThroughFace(0, s(Items.DIRT, 1), d) && be.canTakeItemThroughFace(20, s(Items.DIRT, 1), d) && !be.canTakeItemThroughFace(21, be.getItem(21), d) && !be.canTakeItemThroughFace(22, be.getItem(22), d), "the taking rules of " + d + " are wrong (:105-108)");
            }
            check(handler(level, abs, null) == null, "an unsided query on the unboxer gave a handler");
            IItemHandler h = handler(level, abs, Direction.NORTH);
            ItemStack simulated = h.extractItem(4, 64, true);
            check(simulated.is(Items.STONE) && simulated.getCount() == 5 && be.getItem(4).getCount() == 5, "the simulated extraction gave " + simulated);
            ItemStack took = h.extractItem(4, 64, false);
            check(took.is(Items.STONE) && took.getCount() == 5 && be.getItem(4).isEmpty(), "the extraction gave " + took);
            // an upgrade item inserted through every handler slot lands in the buffer, the upgrade slots keep what they hold
            for(int k = 0; k < 21; k++) h.insertItem(k, s(NtmItems.UPGRADE_STACK_1.get(), 1), false);
            check(be.getItem(21).is(NtmItems.UPGRADE_STACK_3.get()) && be.getItem(22).is(NtmItems.UPGRADE_EJECTOR_3.get()), "an upgrade slot changed through the handler: " + be.getItem(21) + " / " + be.getItem(22));
            check(count(be, NtmItems.UPGRADE_STACK_1.get(), 0, 21) > 0, "the handler took no upgrade item into the buffer");
            // nothing taken through the handler is an upgrade
            for(int k = 0; k < h.getSlots(); k++) {
                ItemStack out = h.extractItem(k, 64, false);
                check(!out.is(NtmItems.UPGRADE_STACK_3.get()) && !out.is(NtmItems.UPGRADE_EJECTOR_3.get()), "slot " + k + " of the handler gave an upgrade");
            }
            check(be.getItem(21).is(NtmItems.UPGRADE_STACK_3.get()) && be.getItem(22).is(NtmItems.UPGRADE_EJECTOR_3.get()), "an upgrade slot was emptied through the handler");
        }).run();
        passed("unboxer_capability").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 6. the menus

    private static void slotAt(AbstractContainerMenu menu, int index, int x, int y, String what) {
        Slot slot = menu.getSlot(index);
        check(slot.x == x && slot.y == y, what + ": slot " + index + " stands at (" + slot.x + ", " + slot.y + "), expected (" + x + ", " + y + ")");
    }

    private static void playerSlots(AbstractContainerMenu menu, int first, String what) {
        for(int i = 0; i < 3; i++) for(int j = 0; j < 9; j++) slotAt(menu, first + j + i * 9, 8 + j * 18, 103 + i * 18, what + " inventory");
        for(int i = 0; i < 9; i++) slotAt(menu, first + 27 + i, 8 + i * 18, 161, what + " hotbar");
    }

    // BlockCraneBase.java:77-90 (a plain click opens the screen, sneaking does not), ContainerCraneGrabber.java:17-108, ContainerCraneBoxer.java:15-60, ContainerCraneUnboxer.java:15-60:
    // which menu opens, the slot layout (grabber 3x3 phantom filter at (40 + 18j, 17 + 18i) and the upgrades at (121, 23) and (121, 47); the others 7x3 at (8 + 18j, 17 + 18i), the
    // unboxer's upgrades at (152, 23) and (152, 47); the player at (8, 103) and (8, 161)), what each slot accepts, the phantom clicks of the grabber and the shift clicks
    @GameTest(template = TEMPLATE, batch = "hbm31c_crane_menus", timeoutTicks = 200)
    public static void crane_menus(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            Block[] blocks = { grabberBlock(), boxerBlock(), unboxerBlock() };
            AbstractContainerMenu[] menus = new AbstractContainerMenu[3];
            CranePlayer[] players = new CranePlayer[3];
            for(int b = 0; b < 3; b++) {
                BlockPos rel = new BlockPos(5 + 3 * b, 2, 6);
                BlockPos abs = helper.absolutePos(rel);
                helper.setBlock(rel, crane(blocks[b], Direction.EAST, Direction.WEST));
                String name = BuiltInRegistries.BLOCK.getKey(blocks[b]).getPath();
                for(boolean sneak : new boolean[] { true, false }) {
                    CranePlayer p = player(helper, GameType.SURVIVAL, 0F);
                    p.setShiftKeyDown(sneak);
                    p.gameMode.useItemOn(p, level, ItemStack.EMPTY, InteractionHand.MAIN_HAND, new BlockHitResult(Vec3.atCenterOf(abs), Direction.UP, abs, false));
                    if(sneak) {
                        check(p.opened.isEmpty(), name + ": sneaking opened a screen");
                    } else {
                        check(p.opened.size() == 1, name + ": a click requested " + p.opened.size() + " menus, expected 1");
                        menus[b] = p.opened.get(0).createMenu(1, p.getInventory(), p);
                        players[b] = p;
                        check(menus[b].stillValid(p), name + ": the menu is not valid for a player beside it");
                    }
                }
            }
            check(menus[0] instanceof CraneGrabberMenu && menus[1] instanceof CraneBoxerMenu && menus[2] instanceof CraneUnboxerMenu, "the opened menus are " + Arrays.toString(menus));

            // the grabber: 11 + 36 slots
            CraneGrabberMenu gm = (CraneGrabberMenu) menus[0];
            CraneGrabberBlockEntity grabber = SmokeTestSupport.blockEntity(helper, new BlockPos(5, 2, 6), CraneGrabberBlockEntity.class);
            CranePlayer gp = players[0];
            check(gm.slots.size() == 11 + 36, "the grabber menu has " + gm.slots.size() + " slots, expected 11 + 36 (ContainerCraneGrabber.java:19-35)");
            for(int i = 0; i < 3; i++) for(int j = 0; j < 3; j++) slotAt(gm, j + i * 3, 40 + j * 18, 17 + i * 18, "grabber filter");
            slotAt(gm, 9, 121, 23, "grabber stack upgrade");
            slotAt(gm, 10, 121, 47, "grabber ejector upgrade");
            playerSlots(gm, 11, "grabber");
            for(int i = 0; i < 9; i++) {
                Slot slot = gm.getSlot(i);
                check(!slot.mayPlace(s(Items.DIRT, 1)) && !slot.mayPickup(gp) && slot.getMaxStackSize() == 1, "filter slot " + i + " is not a phantom slot");
            }
            Item[] stack = { NtmItems.UPGRADE_STACK_1.get(), NtmItems.UPGRADE_STACK_2.get(), NtmItems.UPGRADE_STACK_3.get() };
            Item[] eject = { NtmItems.UPGRADE_EJECTOR_1.get(), NtmItems.UPGRADE_EJECTOR_2.get(), NtmItems.UPGRADE_EJECTOR_3.get() };
            for(int t = 0; t < 3; t++) {
                check(gm.getSlot(9).mayPlace(s(stack[t], 1)) && !gm.getSlot(9).mayPlace(s(eject[t], 1)), "the stack upgrade slot's rule is wrong for tier " + (t + 1));
                check(gm.getSlot(10).mayPlace(s(eject[t], 1)) && !gm.getSlot(10).mayPlace(s(stack[t], 1)), "the ejector upgrade slot's rule is wrong for tier " + (t + 1));
            }
            check(!gm.getSlot(9).mayPlace(s(Items.DIRT, 1)) && !gm.getSlot(10).mayPlace(s(Items.DIRT, 1)), "an upgrade slot takes dirt");

            // phantom clicks (:79-108): any click with a cursor puts one copy in and keeps the cursor, an empty cursor clears, a right click on a filled slot cycles the mode
            int before = invTotal(gp);
            for(ClickType type : ClickType.values()) {
                for(int button = 0; button < 2; button++) {
                    grabber.setItem(0, ItemStack.EMPTY);
                    grabber.matcher.modes[0] = null;
                    gm.setCarried(s(Items.DIRT, 5));
                    gm.clicked(0, button, type, gp);
                    String ctx = type + " button " + button + " with dirt on the cursor";
                    check(grabber.getItem(0).is(Items.DIRT) && grabber.getItem(0).getCount() == 1 && gm.getCarried().getCount() == 5 && "wildcard".equals(grabber.matcher.modes[0]), ctx + ": the slot holds " + grabber.getItem(0) + " mode " + grabber.matcher.modes[0] + ", the cursor " + gm.getCarried() + " (:100-108)");
                    check(invTotal(gp) == before, ctx + ": the player inventory changed");
                }
            }
            grabber.setItem(0, s(Items.DIRT, 1));
            grabber.matcher.modes[0] = "wildcard";
            gm.setCarried(ItemStack.EMPTY);
            gm.clicked(0, 1, ClickType.PICKUP, gp);
            check(grabber.getItem(0).is(Items.DIRT) && !"wildcard".equals(grabber.matcher.modes[0]), "a right click on a filled slot gave " + grabber.getItem(0) + " mode " + grabber.matcher.modes[0] + ", expected the item kept and the mode advanced (:96-98)");
            gm.clicked(0, 0, ClickType.PICKUP, gp);
            check(grabber.getItem(0).isEmpty() && grabber.matcher.modes[0] == null, "an empty cursor did not clear the slot: " + grabber.getItem(0));
            check(gm.getCarried().isEmpty() && invTotal(gp) == before, "an item came out of the phantom slot");

            // shift clicks (:37-76): filter slots never move; the upgrades go to their slot from the player and back; anything else stays
            gp.getInventory().clearContent();
            gp.getInventory().setItem(9, s(stack[1], 1));
            gp.getInventory().setItem(10, s(eject[2], 1));
            gp.getInventory().setItem(11, s(Items.STONE, 5));
            grabber.setItem(9, ItemStack.EMPTY);
            grabber.setItem(10, ItemStack.EMPTY);
            check(gm.quickMoveStack(gp, 11 + 0).is(stack[1]), "the shift click of the stack upgrade returned nothing");
            check(grabber.getItem(9).is(stack[1]) && gp.getInventory().getItem(9).isEmpty(), "the stack upgrade went to " + grabber.getItem(9) + ", the inventory slot holds " + gp.getInventory().getItem(9));
            gm.quickMoveStack(gp, 11 + 1);
            check(grabber.getItem(10).is(eject[2]) && gp.getInventory().getItem(10).isEmpty(), "the ejector upgrade went to " + grabber.getItem(10));
            ItemStack moved = gm.quickMoveStack(gp, 11 + 2);
            check(moved.isEmpty() && gp.getInventory().getItem(11).getCount() == 5 && total(grabber, 0, 9) == 0, "stone moved: " + moved + ", inventory " + gp.getInventory().getItem(11) + " (the grabber has no buffer)");
            gm.quickMoveStack(gp, 9);
            gm.quickMoveStack(gp, 10);
            check(grabber.getItem(9).isEmpty() && grabber.getItem(10).isEmpty() && count(gp.getInventory(), stack[1]) == 1 && count(gp.getInventory(), eject[2]) == 1, "the upgrades did not return to the player: " + grabber.getItem(9) + " / " + grabber.getItem(10));
            grabber.setItem(0, s(Items.DIRT, 1));
            check(gm.quickMoveStack(gp, 0).isEmpty() && grabber.getItem(0).is(Items.DIRT), "a shift click moved a filter item");
            grabber.setItem(0, ItemStack.EMPTY);

            // the boxer: 21 + 36 slots, everything accepted, shift clicks both ways
            CraneBoxerMenu bm = (CraneBoxerMenu) menus[1];
            CraneBoxerBlockEntity boxer = SmokeTestSupport.blockEntity(helper, new BlockPos(8, 2, 6), CraneBoxerBlockEntity.class);
            CranePlayer bp = players[1];
            check(bm.slots.size() == 21 + 36, "the boxer menu has " + bm.slots.size() + " slots, expected 21 + 36 (ContainerCraneBoxer.java:15-35)");
            for(int i = 0; i < 3; i++) for(int j = 0; j < 7; j++) slotAt(bm, j + i * 7, 8 + j * 18, 17 + i * 18, "boxer buffer");
            playerSlots(bm, 21, "boxer");
            for(int i = 0; i < 21; i++) check(bm.getSlot(i).mayPlace(s(Items.DIRT, 1)) && bm.getSlot(i).mayPickup(bp), "boxer slot " + i + " does not take and give items");
            bp.getInventory().clearContent();
            bp.getInventory().setItem(9, s(Items.STONE, 10));
            bm.quickMoveStack(bp, 21);
            check(boxer.getItem(0).is(Items.STONE) && boxer.getItem(0).getCount() == 10 && bp.getInventory().getItem(9).isEmpty(), "a shift click into the boxer left " + boxer.getItem(0) + " in slot 0 (:44-54)");
            bm.quickMoveStack(bp, 0);
            check(boxer.getItem(0).isEmpty() && invTotal(bp) == 10, "a shift click out of the boxer left " + boxer.getItem(0) + ", the player holds " + invTotal(bp));

            // the unboxer: 23 + 36 slots, the upgrades in slots 21 and 22 take their own upgrade only, shift clicks fill the buffer 0-20 and never an upgrade slot
            CraneUnboxerMenu um = (CraneUnboxerMenu) menus[2];
            CraneUnboxerBlockEntity unboxer = SmokeTestSupport.blockEntity(helper, new BlockPos(11, 2, 6), CraneUnboxerBlockEntity.class);
            CranePlayer up = players[2];
            check(um.slots.size() == 23 + 36, "the unboxer menu has " + um.slots.size() + " slots, expected 23 + 36 (ContainerCraneUnboxer.java:15-35)");
            for(int i = 0; i < 3; i++) for(int j = 0; j < 7; j++) slotAt(um, j + i * 7, 8 + j * 18, 17 + i * 18, "unboxer buffer");
            slotAt(um, 21, 152, 23, "unboxer stack upgrade");
            slotAt(um, 22, 152, 47, "unboxer ejector upgrade");
            playerSlots(um, 23, "unboxer");
            for(int t = 0; t < 3; t++) {
                check(um.getSlot(21).mayPlace(s(stack[t], 1)) && !um.getSlot(21).mayPlace(s(eject[t], 1)), "the unboxer's stack upgrade slot's rule is wrong for tier " + (t + 1));
                check(um.getSlot(22).mayPlace(s(eject[t], 1)) && !um.getSlot(22).mayPlace(s(stack[t], 1)), "the unboxer's ejector upgrade slot's rule is wrong for tier " + (t + 1));
            }
            check(!um.getSlot(21).mayPlace(s(Items.DIRT, 1)) && !um.getSlot(22).mayPlace(s(Items.DIRT, 1)), "an unboxer upgrade slot takes dirt");
            up.getInventory().clearContent();
            for(int i = 0; i < 20; i++) unboxer.setItem(i, s(Items.COBBLESTONE, 64));
            up.getInventory().setItem(9, s(Items.STONE, 10));
            um.quickMoveStack(up, 23);
            check(unboxer.getItem(20).is(Items.STONE) && unboxer.getItem(20).getCount() == 10 && unboxer.getItem(21).isEmpty() && unboxer.getItem(22).isEmpty(), "a shift click filled " + unboxer.getItem(20) + " in slot 20, the upgrade slots hold " + unboxer.getItem(21) + " / " + unboxer.getItem(22) + " (:49-53)");
            unboxer.setItem(21, s(stack[0], 1));
            um.quickMoveStack(up, 21);
            check(unboxer.getItem(21).isEmpty() && count(up.getInventory(), stack[0]) == 1, "a shift click on the upgrade slot did not return it: " + unboxer.getItem(21));
        }).run();
        passed("crane_menus").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 7. breaking

    // CraneGrabber.java:45-49 (slots 9 and 10), CraneBoxer.java:80-84 (0-20), CraneUnboxer.java:120-128 (0-22): breaking a crane drops the block and its real slots; the grabber's
    // phantom filter is never dropped
    @GameTest(template = TEMPLATE, batch = "hbm31c_crane_drops", timeoutTicks = 100)
    public static void crane_drops(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            Item[] stuff = { Items.STONE, Items.DIRT, Items.SAND, Items.GRAVEL, Items.COAL, Items.IRON_INGOT, Items.GOLD_INGOT };

            CraneGrabberBlockEntity grabber = placeCrane(helper, new BlockPos(4, 2, 4), grabberBlock(), Direction.EAST, Direction.WEST, CraneGrabberBlockEntity.class);
            for(int i = 0; i < 9; i++) grabber.setItem(i, s(Items.DIAMOND, 1));
            grabber.setItem(9, s(NtmItems.UPGRADE_STACK_2.get(), 1));
            grabber.setItem(10, s(NtmItems.UPGRADE_EJECTOR_3.get(), 1));
            level.destroyBlock(helper.absolutePos(new BlockPos(4, 2, 4)), true);
            check(loose(helper, Items.DIAMOND) == 0, "the grabber dropped " + loose(helper, Items.DIAMOND) + " filter items, expected 0 (phantom slots)");
            check(loose(helper, NtmItems.UPGRADE_STACK_2.get()) == 1 && loose(helper, NtmItems.UPGRADE_EJECTOR_3.get()) == 1, "the grabber dropped its upgrades " + loose(helper, NtmItems.UPGRADE_STACK_2.get()) + " / " + loose(helper, NtmItems.UPGRADE_EJECTOR_3.get()) + ", expected 1 / 1");
            check(loose(helper, grabberBlock().asItem()) == 1, "the grabber dropped " + loose(helper, grabberBlock().asItem()) + " block items, expected 1");
            clearEntities(helper);

            CraneBoxerBlockEntity boxer = placeCrane(helper, new BlockPos(8, 2, 4), boxerBlock(), Direction.EAST, Direction.WEST, CraneBoxerBlockEntity.class);
            int expected = 0;
            for(int i = 0; i < 21; i++) {
                boxer.setItem(i, s(stuff[i % stuff.length], 1 + i));
                expected += 1 + i;
            }
            level.destroyBlock(helper.absolutePos(new BlockPos(8, 2, 4)), true);
            int dropped = 0;
            int blocks = 0;
            for(ItemEntity e : level.getEntitiesOfClass(ItemEntity.class, helper.getBounds())) {
                if(e.getItem().is(boxerBlock().asItem())) blocks += e.getItem().getCount();
                else dropped += e.getItem().getCount();
            }
            check(blocks == 1, "the boxer dropped " + blocks + " block items, expected 1");
            check(dropped == expected, "the boxer dropped " + dropped + " items from its buffer, expected " + expected + " (all 21 slots)");
            for(int i = 0; i < stuff.length; i++) {
                int want = 0;
                for(int slot = 0; slot < 21; slot++) if(slot % stuff.length == i) want += 1 + slot;
                check(loose(helper, stuff[i]) == want, "boxer: " + stuff[i] + ": " + loose(helper, stuff[i]) + " dropped, expected " + want);
            }
            clearEntities(helper);

            CraneUnboxerBlockEntity unboxer = placeCrane(helper, new BlockPos(12, 2, 4), unboxerBlock(), Direction.EAST, Direction.WEST, CraneUnboxerBlockEntity.class);
            for(int i = 0; i < 21; i++) unboxer.setItem(i, s(stuff[i % stuff.length], 1 + i));
            unboxer.setItem(21, s(NtmItems.UPGRADE_STACK_3.get(), 1));
            unboxer.setItem(22, s(NtmItems.UPGRADE_EJECTOR_1.get(), 1));
            level.destroyBlock(helper.absolutePos(new BlockPos(12, 2, 4)), true);
            dropped = 0;
            blocks = 0;
            for(ItemEntity e : level.getEntitiesOfClass(ItemEntity.class, helper.getBounds())) {
                if(e.getItem().is(unboxerBlock().asItem())) blocks += e.getItem().getCount();
                else dropped += e.getItem().getCount();
            }
            check(blocks == 1, "the unboxer dropped " + blocks + " block items, expected 1");
            check(dropped == expected + 2, "the unboxer dropped " + dropped + " items, expected " + (expected + 2) + " (the buffer 0-20 and both upgrades)");
            check(loose(helper, NtmItems.UPGRADE_STACK_3.get()) == 1 && loose(helper, NtmItems.UPGRADE_EJECTOR_1.get()) == 1, "the unboxer's upgrades dropped " + loose(helper, NtmItems.UPGRADE_STACK_3.get()) + " / " + loose(helper, NtmItems.UPGRADE_EJECTOR_1.get()) + ", expected 1 / 1");
            for(int i = 0; i < stuff.length; i++) {
                int want = 0;
                for(int slot = 0; slot < 21; slot++) if(slot % stuff.length == i) want += 1 + slot;
                check(loose(helper, stuff[i]) == want, "unboxer: " + stuff[i] + ": " + loose(helper, stuff[i]) + " dropped, expected " + want);
            }
            clearEntities(helper);

            // a crane that is replaced by the same block with another orientation drops nothing
            CraneBoxerBlockEntity kept = placeCrane(helper, new BlockPos(4, 2, 10), boxerBlock(), Direction.EAST, Direction.WEST, CraneBoxerBlockEntity.class);
            kept.setItem(0, s(Items.STONE, 3));
            helper.setBlock(new BlockPos(4, 2, 10), crane(boxerBlock(), Direction.NORTH, Direction.SOUTH));
            check(loose(helper, Items.STONE) == 0 && SmokeTestSupport.blockEntity(helper, new BlockPos(4, 2, 10), CraneBoxerBlockEntity.class).getItem(0).getCount() == 3, "turning the boxer dropped or lost its items");
        }).run();
        passed("crane_drops").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 8. copy and paste

    // TileEntityCraneBase.java:113-181 (the copy data: both sides as ordinals, the filter; paste of entry 1 turns the crane, entry 0 pastes the filter): the grabber, boxer and
    // unboxer through all 30 orientations; the boxer and unboxer have no filter and carry orientation only; a paste does not touch the rest of the crane
    @GameTest(template = TEMPLATE, batch = "hbm31c_crane_copy_paste", timeoutTicks = 200)
    public static void crane_copy_paste(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            CranePlayer holder = player(helper, GameType.SURVIVAL, 0F);
            Block[] blocks = { grabberBlock(), boxerBlock(), unboxerBlock() };
            BlockPos srcRel = new BlockPos(4, 2, 4);
            BlockPos dstRel = new BlockPos(10, 2, 4);
            check(Direction.DOWN.get3DDataValue() == 0 && Direction.UP.get3DDataValue() == 1 && Direction.NORTH.get3DDataValue() == 2 && Direction.SOUTH.get3DDataValue() == 3 && Direction.WEST.get3DDataValue() == 4 && Direction.EAST.get3DDataValue() == 5, "the side numbering differs from ForgeDirection (DOWN, UP, NORTH, SOUTH, WEST, EAST)");
            int combos = 0;
            for(int b = 0; b < 3; b++) {
                String name = BuiltInRegistries.BLOCK.getKey(blocks[b]).getPath();
                for(Direction in : Direction.values()) for(Direction out : Direction.values()) {
                    if(in == out) continue;
                    helper.setBlock(srcRel, crane(blocks[b], in, out));
                    CraneBaseBlockEntity src = SmokeTestSupport.blockEntity(helper, srcRel, CraneBaseBlockEntity.class);
                    if(b == 0) {
                        src.setItem(2, s(Items.OAK_LOG, 1));
                        src.setItem(CraneGrabberBlockEntity.SLOT_STACK_UPGRADE, stackUpgrade(2));
                    }
                    CompoundTag copied = src.getSettings(level, src.getBlockPos());
                    String ctx = name + " (" + in + ", " + out + ")";
                    check(copied.getInt("inputSide") == in.get3DDataValue() && copied.getInt("outputSide") == out.get3DDataValue(), ctx + ": the copied sides are " + copied.getInt("inputSide") + " / " + copied.getInt("outputSide") + " (:113-120)");
                    check(copied.contains("items") == (b == 0), ctx + ": the copy " + (b == 0 ? "has no" : "has a") + " filter list");

                    Direction otherIn = in == Direction.NORTH ? Direction.SOUTH : Direction.NORTH;
                    Direction otherOut = out == Direction.UP ? Direction.DOWN : Direction.UP;
                    helper.setBlock(dstRel, crane(blocks[b], otherIn, otherOut));
                    CraneBaseBlockEntity dst = SmokeTestSupport.blockEntity(helper, dstRel, CraneBaseBlockEntity.class);
                    if(b == 1) dst.setItem(5, s(Items.COAL, 7));
                    if(b == 2) dst.setItem(5, s(Items.COAL, 7));
                    String[] info = src.infoForDisplay(level, src.getBlockPos());
                    check(info.length == 2 && info[0].equals("copytool.filter") && info[1].equals("copytool.orientation"), ctx + ": the display list is " + Arrays.toString(info) + " (:179-181)");
                    dst.pasteSettings(copied, 0, level, holder, dst.getBlockPos());
                    BlockState afterFilter = level.getBlockState(dst.getBlockPos());
                    check(afterFilter.getValue(CraneBaseBlock.INPUT) == otherIn && afterFilter.getValue(CraneBaseBlock.OUTPUT) == otherOut, ctx + ": pasting the filter turned the crane to " + sides(afterFilter));
                    dst.pasteSettings(copied, 1, level, holder, dst.getBlockPos());
                    BlockState got = level.getBlockState(dst.getBlockPos());
                    check(got.is(blocks[b]) && got.getValue(CraneBaseBlock.INPUT) == in && got.getValue(CraneBaseBlock.OUTPUT) == out, ctx + ": the pasted orientation is " + sides(got) + " (:140-176)");
                    BlockEntity now = level.getBlockEntity(helper.absolutePos(dstRel));
                    check(now instanceof CraneBaseBlockEntity, ctx + ": the block entity is gone after the paste");
                    if(b == 0) check(((CraneBaseBlockEntity) now).getItem(2).is(Items.OAK_LOG) && ((CraneBaseBlockEntity) now).getItem(CraneGrabberBlockEntity.SLOT_STACK_UPGRADE).isEmpty(), ctx + ": the pasted filter holds " + ((CraneBaseBlockEntity) now).getItem(2) + ", the upgrade slot " + ((CraneBaseBlockEntity) now).getItem(CraneGrabberBlockEntity.SLOT_STACK_UPGRADE));
                    else check(((CraneBaseBlockEntity) now).getItem(5).is(Items.COAL) && ((CraneBaseBlockEntity) now).getItem(5).getCount() == 7, ctx + ": the buffer was touched by the paste: " + ((CraneBaseBlockEntity) now).getItem(5));
                    combos++;
                }
            }
            check(combos == 90, "the loop covered " + combos + " combinations, expected 90");

            // the grabber's filter: all nine slots at their relative index, the mode kept as the copy item holds it
            helper.setBlock(srcRel, crane(grabberBlock(), Direction.EAST, Direction.WEST));
            CraneGrabberBlockEntity src = SmokeTestSupport.blockEntity(helper, srcRel, CraneGrabberBlockEntity.class);
            Item[] filter = { Items.DIRT, Items.STONE, Items.SAND, Items.GRAVEL, Items.COAL, Items.IRON_INGOT, Items.GOLD_INGOT, Items.OAK_LOG, Items.EMERALD };
            for(int i = 0; i < 9; i++) src.setItem(i, s(filter[i], 1));
            CompoundTag copied = src.getSettings(level, src.getBlockPos());
            ListTag list = copied.getList("items", Tag.TAG_COMPOUND);
            check(list.size() == 9, "the copied filter has " + list.size() + " entries, expected 9");
            helper.setBlock(dstRel, crane(grabberBlock(), Direction.NORTH, Direction.SOUTH));
            CraneGrabberBlockEntity dst = SmokeTestSupport.blockEntity(helper, dstRel, CraneGrabberBlockEntity.class);
            dst.pasteSettings(copied, 0, level, holder, dst.getBlockPos());
            for(int i = 0; i < 9; i++) check(dst.getItem(i).is(filter[i]), "pasted filter slot " + i + " holds " + dst.getItem(i) + ", expected " + filter[i]);
            check(dst.getItem(9).isEmpty() && dst.getItem(10).isEmpty(), "the paste filled an upgrade slot");
        }).run();
        passed("crane_copy_paste").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 9. the whole line

    // The boxer packs, a belt carries the package into the unboxer's output side, the unboxer puts the items on the belt on its input side, that belt hands them to an inserter and
    // the inserter to a chest: TileEntityCraneBoxer.java:41-149, EntityMovingPackage.java:75-83, CraneUnboxer.java:100-118, TileEntityCraneUnboxer.java:35-91,
    // CraneInserter.java:55-96. All 512 items arrive, none is made or lost on the way
    @GameTest(template = TEMPLATE, batch = "hbm31c_line_conservation", timeoutTicks = 1200)
    public static void line_conservation(GameTestHelper helper) {
        int z = 8;
        CraneBoxerBlockEntity boxer = placeCrane(helper, new BlockPos(2, 2, z), boxerBlock(), Direction.WEST, Direction.EAST, CraneBoxerBlockEntity.class);
        for(int x = 3; x <= 6; x++) helper.setBlock(new BlockPos(x, 2, z), beltState(Direction.WEST));
        CraneUnboxerBlockEntity unboxer = placeCrane(helper, new BlockPos(7, 2, z), unboxerBlock(), Direction.EAST, Direction.WEST, CraneUnboxerBlockEntity.class);
        unboxer.setItem(CraneUnboxerBlockEntity.SLOT_STACK_UPGRADE, stackUpgrade(3));
        unboxer.setItem(CraneUnboxerBlockEntity.SLOT_EJECTOR_UPGRADE, ejectorUpgrade(3));
        for(int x = 8; x <= 11; x++) helper.setBlock(new BlockPos(x, 2, z), beltState(Direction.WEST));
        CraneInserterBlockEntity inserter = placeCrane(helper, new BlockPos(12, 2, z), inserterBlock(), Direction.WEST, Direction.EAST, CraneInserterBlockEntity.class);
        Container chest = chest(helper, new BlockPos(13, 2, z));
        for(int i = 0; i < 4; i++) boxer.setItem(i, s(Items.STONE, 64));
        for(int i = 4; i < 8; i++) boxer.setItem(i, s(Items.DIRT, 64));
        boxer.mode = CraneBoxerBlockEntity.MODE_4;
        helper.startSequence()
                .thenWaitUntil(guard(() -> check(total(chest) == 512, "the chest holds " + total(chest) + " items; boxer " + total(boxer) + ", unboxer " + total(unboxer, 0, 21) + ", inserter " + total(inserter) + ", on the way " + (loose(helper, Items.STONE) + loose(helper, Items.DIRT)))))
                .thenExecuteAfter(40, guard(() -> {
                    check(count(chest, Items.STONE) == 256 && count(chest, Items.DIRT) == 256 && total(chest) == 512, "the chest holds " + count(chest, Items.STONE) + " stone and " + count(chest, Items.DIRT) + " dirt, expected 256 and 256");
                    check(total(boxer) == 0 && total(unboxer, 0, 21) == 0 && total(inserter) == 0, "items are left in the machines: boxer " + total(boxer) + ", unboxer " + total(unboxer, 0, 21) + ", inserter " + total(inserter));
                    check(helper.getLevel().getEntitiesOfClass(MovingPackage.class, helper.getBounds()).isEmpty() && helper.getLevel().getEntitiesOfClass(MovingItem.class, helper.getBounds()).isEmpty() && helper.getLevel().getEntitiesOfClass(ItemEntity.class, helper.getBounds()).isEmpty(), "entities are left on the line");
                    check(unboxer.getItem(21).is(NtmItems.UPGRADE_STACK_3.get()) && unboxer.getItem(22).is(NtmItems.UPGRADE_EJECTOR_3.get()), "an upgrade left its slot");
                }))
                .thenExecute(passed("line_conservation"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 10. the recipes

    private static ShapedRecipe craneRecipe(GameTestHelper helper, String path, Item result, int count, String original) {
        ServerLevel level = helper.getLevel();
        RecipeHolder<?> holder = level.getRecipeManager().byKey(id(path)).orElse(null);
        check(holder != null, "recipe " + id(path) + " is not loaded (" + original + ")");
        check(holder.value() instanceof ShapedRecipe, path + " is " + holder.value().getClass().getSimpleName() + ", expected a shaped recipe (" + original + ")");
        ShapedRecipe recipe = (ShapedRecipe) holder.value();
        check(recipe.getWidth() == 3 && recipe.getHeight() == 3, path + " is " + recipe.getWidth() + "x" + recipe.getHeight() + ", expected 3x3 (" + original + ")");
        ItemStack out = recipe.getResultItem(level.registryAccess());
        check(out.is(result) && out.getCount() == count && MetaHelper.getMeta(out) == 0, path + " yields " + out + ", expected " + count + " x " + result + " (" + original + ")");
        return recipe;
    }

    private static boolean craneMatches(GameTestHelper helper, ShapedRecipe recipe, ItemStack... cells) {
        List<ItemStack> grid = new ArrayList<>();
        for(ItemStack c : cells) grid.add(c == null ? ItemStack.EMPTY : c);
        return recipe.matches(CraftingInput.of(3, 3, grid), helper.getLevel());
    }

    /** The full pattern matches and is assembled with its count; dirt in any cell and anything in an empty cell breaks it. */
    private static void craneGrid(GameTestHelper helper, String path, ShapedRecipe recipe, Item result, int count, String original, ItemStack... cells) {
        check(cells.length == 9, "the test lists " + cells.length + " cells for 3x3");
        check(craneMatches(helper, recipe, cells), path + " does not match its own pattern (" + original + ")");
        List<ItemStack> grid = new ArrayList<>();
        for(ItemStack c : cells) grid.add(c == null ? ItemStack.EMPTY : c);
        ItemStack crafted = recipe.assemble(CraftingInput.of(3, 3, grid), helper.getLevel().registryAccess());
        check(crafted.is(result) && crafted.getCount() == count && MetaHelper.getMeta(crafted) == 0, path + " crafts " + crafted + ", expected " + count + " x " + result);
        for(int i = 0; i < cells.length; i++) {
            ItemStack[] bad = cells.clone();
            bad[i] = s(Items.DIRT, 1);
            check(!craneMatches(helper, recipe, bad), path + " matches with dirt in cell " + i + " (" + original + ")");
        }
    }

    private static ItemStack wand() {
        return MetaHelper.newStack(NtmItems.CONVEYOR_WAND.get(), 1, ConveyorType.REGULAR);
    }

    private static ItemStack pneumatic() {
        return MetaHelper.newStack(NtmItems.PART_GENERIC.get(), 1, PartGenericItem.Type.PISTON_PNEUMATIC);
    }

    // CraftingManager.java:867-880: crane_grabber x1 / x2 / x4 with stone bricks / iron / steel in "C C", "P P", "CBC" with pneumatic pistons and a regular conveyor wand
    @GameTest(template = TEMPLATE, batch = "hbm31c_recipe_crane_grabber", timeoutTicks = 100)
    public static void recipe_crane_grabber(GameTestHelper helper) {
        guard(() -> {
            String original = "CraftingManager.java:867-880";
            ItemStack[][] casings = {
                    { s(Items.STONE_BRICKS, 1), s(Items.MOSSY_STONE_BRICKS, 1), s(Items.CRACKED_STONE_BRICKS, 1), s(Items.CHISELED_STONE_BRICKS, 1) },
                    { s(Items.IRON_INGOT, 1) },
                    { s(NtmItems.INGOT_STEEL.get(), 1) } };
            String[] names = { "stone_bricks", "iron", "steel" };
            int[] counts = { 1, 2, 4 };
            for(int i = 0; i < 3; i++) {
                String path = "crane_grabber_" + names[i];
                ShapedRecipe r = craneRecipe(helper, path, grabberBlock().asItem(), counts[i], original);
                ItemStack c = casings[i][0];
                ItemStack[] grid = { c, null, c, pneumatic(), null, pneumatic(), c, wand(), c };
                craneGrid(helper, path, r, grabberBlock().asItem(), counts[i], original, grid);
                for(ItemStack alt : casings[i]) {
                    ItemStack[] g = { alt, null, alt, pneumatic(), null, pneumatic(), alt, wand(), alt };
                    check(craneMatches(helper, r, g), path + " rejects the casing " + alt + " (" + original + ")");
                }
                for(int j = 0; j < 3; j++) {
                    if(j == i) continue;
                    ItemStack o = casings[j][0];
                    ItemStack[] g = { o, null, o, pneumatic(), null, pneumatic(), o, wand(), o };
                    check(!craneMatches(helper, r, g), path + " accepts the casing " + o + " of " + names[j]);
                }
                ItemStack[] mixed = grid.clone();
                mixed[0] = casings[(i + 1) % 3][0];
                check(!craneMatches(helper, r, mixed), path + " accepts one cell of another casing");
                ItemStack[] plain = { s(Items.STONE, 1), null, s(Items.STONE, 1), pneumatic(), null, pneumatic(), s(Items.STONE, 1), wand(), s(Items.STONE, 1) };
                check(!craneMatches(helper, r, plain), path + " accepts plain stone as the casing");
                for(ConveyorType type : new ConveyorType[] { ConveyorType.EXPRESS, ConveyorType.DOUBLE, ConveyorType.TRIPLE }) {
                    ItemStack[] g = grid.clone();
                    g[7] = MetaHelper.newStack(NtmItems.CONVEYOR_WAND.get(), 1, type);
                    check(!craneMatches(helper, r, g), path + " accepts a " + type + " wand (:880 the regular type)");
                }
                for(PartGenericItem.Type type : new PartGenericItem.Type[] { PartGenericItem.Type.PISTON_HYDRAULIC, PartGenericItem.Type.PISTON_ELECTRIC }) {
                    ItemStack[] g = grid.clone();
                    g[3] = MetaHelper.newStack(NtmItems.PART_GENERIC.get(), 1, type);
                    check(!craneMatches(helper, r, g), path + " accepts a " + type + " (:880 pneumatic only)");
                }
                ItemStack[] vanilla = grid.clone();
                vanilla[5] = s(Items.PISTON, 1);
                check(!craneMatches(helper, r, vanilla), path + " accepts a vanilla piston");
                ItemStack[] oneRow = grid.clone();
                oneRow[5] = null;
                check(!craneMatches(helper, r, oneRow), path + " matches with one piston");
                ItemStack[] noWand = grid.clone();
                noWand[7] = null;
                check(!craneMatches(helper, r, noWand), path + " matches without the wand");
            }
            // 1.7.10's wildcard casing: bricks of different variants mix in one grid
            ShapedRecipe bricks = craneRecipe(helper, "crane_grabber_stone_bricks", grabberBlock().asItem(), 1, original);
            ItemStack[] variants = { s(Items.STONE_BRICKS, 1), null, s(Items.MOSSY_STONE_BRICKS, 1), pneumatic(), null, pneumatic(), s(Items.CRACKED_STONE_BRICKS, 1), wand(), s(Items.CHISELED_STONE_BRICKS, 1) };
            check(craneMatches(helper, bricks, variants), "crane_grabber_stone_bricks does not accept different brick variants in one grid (" + original + ")");
        }).run();
        passed("recipe_crane_grabber").run();
        helper.succeed();
    }

    // CraftingManager.java:884: crane_boxer from planks around a pneumatic piston over three regular conveyor wands
    @GameTest(template = TEMPLATE, batch = "hbm31c_recipe_crane_boxer", timeoutTicks = 100)
    public static void recipe_crane_boxer(GameTestHelper helper) {
        guard(() -> {
            String original = "CraftingManager.java:884";
            ShapedRecipe r = craneRecipe(helper, "crane_boxer", boxerBlock().asItem(), 1, original);
            ItemStack w = s(Items.OAK_PLANKS, 1);
            ItemStack[] grid = { w, w, w, w, pneumatic(), w, wand(), wand(), wand() };
            craneGrid(helper, "crane_boxer", r, boxerBlock().asItem(), 1, original, grid);
            // every plank type, mixed in one grid
            ItemStack[] kinds = { s(Items.SPRUCE_PLANKS, 1), s(Items.BIRCH_PLANKS, 1), s(Items.JUNGLE_PLANKS, 1), s(Items.ACACIA_PLANKS, 1), s(Items.DARK_OAK_PLANKS, 1), s(Items.MANGROVE_PLANKS, 1), s(Items.CHERRY_PLANKS, 1), s(Items.BAMBOO_PLANKS, 1) };
            for(ItemStack k : kinds) {
                ItemStack[] g = { k, k, k, k, pneumatic(), k, wand(), wand(), wand() };
                check(craneMatches(helper, r, g), "crane_boxer rejects " + k + " as a plank (" + original + " plankWood)");
            }
            ItemStack[] mixed = { kinds[0], kinds[1], kinds[2], kinds[3], pneumatic(), kinds[4], wand(), wand(), wand() };
            check(craneMatches(helper, r, mixed), "crane_boxer rejects mixed planks");
            // sticks, logs and other things are no planks
            for(ItemStack not : new ItemStack[] { s(Items.STICK, 1), s(Items.OAK_LOG, 1), s(Items.STONE, 1), s(Items.OAK_SLAB, 1) }) {
                ItemStack[] g = { not, not, not, not, pneumatic(), not, wand(), wand(), wand() };
                check(!craneMatches(helper, r, g), "crane_boxer accepts " + not + " as planks");
            }
            ItemStack[] shears = grid.clone();
            shears[4] = s(Items.SHEARS, 1);
            check(!craneMatches(helper, r, shears), "crane_boxer accepts shears for the piston");
            for(PartGenericItem.Type type : new PartGenericItem.Type[] { PartGenericItem.Type.PISTON_HYDRAULIC, PartGenericItem.Type.PISTON_ELECTRIC }) {
                ItemStack[] g = grid.clone();
                g[4] = MetaHelper.newStack(NtmItems.PART_GENERIC.get(), 1, type);
                check(!craneMatches(helper, r, g), "crane_boxer accepts a " + type);
            }
            ItemStack[] vanilla = grid.clone();
            vanilla[4] = s(Items.PISTON, 1);
            check(!craneMatches(helper, r, vanilla), "crane_boxer accepts a vanilla piston");
            for(int i = 6; i < 9; i++) {
                for(ConveyorType type : new ConveyorType[] { ConveyorType.EXPRESS, ConveyorType.DOUBLE, ConveyorType.TRIPLE }) {
                    ItemStack[] g = grid.clone();
                    g[i] = MetaHelper.newStack(NtmItems.CONVEYOR_WAND.get(), 1, type);
                    check(!craneMatches(helper, r, g), "crane_boxer accepts a " + type + " wand in cell " + i + " (:884 the regular type)");
                }
            }
            // the shape: two wands do not do, the wands must be in the bottom row
            ItemStack[] two = grid.clone();
            two[8] = null;
            check(!craneMatches(helper, r, two), "crane_boxer matches with two wands");
            ItemStack[] moved = { wand(), w, w, w, pneumatic(), w, w, wand(), wand() };
            check(!craneMatches(helper, r, moved), "crane_boxer matches with a wand in the top row");
        }).run();
        passed("recipe_crane_boxer").run();
        helper.succeed();
    }

    // CraftingManager.java:885: crane_unboxer from sticks around shears over three regular conveyor wands; the shears may be used (NEO's recipe takes the item)
    @GameTest(template = TEMPLATE, batch = "hbm31c_recipe_crane_unboxer", timeoutTicks = 100)
    public static void recipe_crane_unboxer(GameTestHelper helper) {
        guard(() -> {
            String original = "CraftingManager.java:885";
            ShapedRecipe r = craneRecipe(helper, "crane_unboxer", unboxerBlock().asItem(), 1, original);
            ItemStack w = s(Items.STICK, 1);
            ItemStack[] grid = { w, w, w, w, s(Items.SHEARS, 1), w, wand(), wand(), wand() };
            craneGrid(helper, "crane_unboxer", r, unboxerBlock().asItem(), 1, original, grid);
            ItemStack used = s(Items.SHEARS, 1);
            used.setDamageValue(100);
            ItemStack[] damaged = grid.clone();
            damaged[4] = used;
            check(craneMatches(helper, r, damaged), "crane_unboxer rejects damaged shears");
            for(ItemStack not : new ItemStack[] { s(Items.OAK_PLANKS, 1), s(Items.BAMBOO, 1), s(Items.OAK_LOG, 1), s(Items.STONE, 1), s(Items.BLAZE_ROD, 1) }) {
                ItemStack[] g = { not, not, not, not, s(Items.SHEARS, 1), not, wand(), wand(), wand() };
                check(!craneMatches(helper, r, g), "crane_unboxer accepts " + not + " as sticks");
            }
            for(ItemStack not : new ItemStack[] { pneumatic(), s(Items.PISTON, 1), s(Items.IRON_SWORD, 1), s(Items.STICK, 1) }) {
                ItemStack[] g = grid.clone();
                g[4] = not;
                check(!craneMatches(helper, r, g), "crane_unboxer accepts " + not + " for the shears");
            }
            for(int i = 6; i < 9; i++) {
                for(ConveyorType type : new ConveyorType[] { ConveyorType.EXPRESS, ConveyorType.DOUBLE, ConveyorType.TRIPLE }) {
                    ItemStack[] g = grid.clone();
                    g[i] = MetaHelper.newStack(NtmItems.CONVEYOR_WAND.get(), 1, type);
                    check(!craneMatches(helper, r, g), "crane_unboxer accepts a " + type + " wand in cell " + i + " (:885 the regular type)");
                }
            }
            ItemStack[] two = grid.clone();
            two[6] = null;
            check(!craneMatches(helper, r, two), "crane_unboxer matches with two wands");
            // the boxer's and the unboxer's grids do not mix
            ShapedRecipe boxer = craneRecipe(helper, "crane_boxer", boxerBlock().asItem(), 1, "CraftingManager.java:884");
            check(!craneMatches(helper, boxer, grid), "crane_boxer accepts the unboxer's grid");
            ItemStack p = s(Items.OAK_PLANKS, 1);
            check(!craneMatches(helper, r, new ItemStack[] { p, p, p, p, pneumatic(), p, wand(), wand(), wand() }), "crane_unboxer accepts the boxer's grid");
        }).run();
        passed("recipe_crane_unboxer").run();
        helper.succeed();
    }
}
