package com.hbm.gametest;

import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.bomb.LaunchPadBaseBlockEntity;
import com.hbm.blockentity.machine.MachineBlastFurnaceBlockEntity;
import com.hbm.blockentity.machine.MachineCrystallizerBlockEntity;
import com.hbm.blockentity.machine.MachineSatLinkerBlockEntity;
import com.hbm.blockentity.machine.MachineWoodBurnerBlockEntity;
import com.hbm.blockentity.machine.SoyuzLauncherBlockEntity;
import com.hbm.blockentity.machine.heater.HeaterHeatexBlockEntity;
import com.hbm.blockentity.machine.storage.BarrelBlockEntity;
import com.hbm.blockentity.machine.storage.CrateTungstenBlockEntity;
import com.hbm.blockentity.machine.storage.MachineFluidTankBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.menus.BarrelMenu;
import com.hbm.inventory.menus.MachineBlastFurnaceMenu;
import com.hbm.inventory.menus.MachineFluidTankMenu;
import com.hbm.items.ISatChip;
import com.hbm.items.NtmItems;
import com.hbm.main.NuclearTechMod;
import com.hbm.util.AdjacentInventory;
import com.mojang.logging.LogUtils;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.Container;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.inventory.ClickType;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.item.crafting.SingleRecipeInput;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.HopperBlock;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.neoforged.neoforge.capabilities.Capabilities;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import net.neoforged.neoforge.items.IItemHandler;
import org.slf4j.Logger;

import javax.annotation.Nullable;
import java.util.ArrayList;
import java.util.List;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal32B, part one: the automation rules of the barrel, the fluid tank, the satellite linker, the blast furnace, the
 * wood burner, the tungsten crate, both launch pads, the Soyuz launcher and the heat exchanger, the barrel and fluid tank menus, and the
 * multiblock proxy's isEmpty. Same template and conventions as {@link Goal31BGameTests}; every test has its own batch. The rest of the
 * batch is in {@link Goal32BGameTests}.
 * <p>
 * Expected values come from the ORIGINAL at d4708ef9c, cited beside each group of checks (TileEntityBarrel.java:140-164;
 * TileEntityMachineFluidTank.java:39; ContainerBarrel.java:14-19; ContainerBase.java:37-63; InventoryUtil.java:504-580; SlotNonRetarded.java:23-26;
 * ContainerMachineFluidTank.java:19-24,56-63; TileEntityMachineSatLinker.java:20,32-61; TileEntityProxyCombo.java:174-191;
 * TileEntityMachineBlastFurnace.java:221-252; TileEntityMachineWoodBurner.java:247-260; TileEntityCrateTungsten.java:62-76;
 * TileEntityLaunchPadBase.java:134-146; TileEntitySoyuzLauncher and TileEntityHeaterHeatex, which declare no accessible slots), not from the
 * NEO implementation.
 * <p>
 * Every automation rule goes through three paths: the item handler capability (level.getCapability(Capabilities.ItemHandler.BLOCK, pos,
 * side)) from all six sides, the conveyor cranes' AdjacentInventory.insert / source (the path CraneInserter / CraneExtractor use), and real
 * vanilla hoppers ticking into the machine from above and out of it from below, with the item totals of hoppers and machine compared
 * before and after. Multiblock machines are their lone core (helper.setBlock), as Goal31DGameTests does, so that a hopper can touch it.
 * Real classes and state: the registered blocks, block entities and menus, mock players for the menus, the machines' own ticks.
 * Not evidence: other mods' pipes, the client side of the menus (slot rendering, the client prediction of clicks), a dedicated server
 * with real players, saved worlds, and 1.7.10 itself.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class Goal32BAutomationGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-32b]";
    /** Hopper transfers take 8 ticks each; every hopper scenario here moves at most four items per hopper. */
    private static final int HOPPER_WAIT = 80;

    private static Runnable passed(String test) {
        return () -> LOGGER.info("{} {} passed", TAG, test);
    }

    // ---------------------------------------------------------------- helpers

    private static ItemStack s(Item item, int count) {
        return new ItemStack(item, count);
    }

    @Nullable
    private static IItemHandler handler(ServerLevel level, BlockPos abs, @Nullable Direction side) {
        return level.getCapability(Capabilities.ItemHandler.BLOCK, abs, side);
    }

    private static <T extends BlockEntity> T core(GameTestHelper helper, BlockPos rel, Block block, Class<T> type) {
        helper.setBlock(rel, block.defaultBlockState());
        return SmokeTestSupport.blockEntity(helper, rel, type);
    }

    /** A vanilla hopper pointing down, filled from slot 0 on. */
    private static Container hopper(GameTestHelper helper, BlockPos rel, ItemStack... contents) {
        helper.setBlock(rel, Blocks.HOPPER.defaultBlockState().setValue(HopperBlock.FACING, Direction.DOWN));
        Container hopper = (Container) helper.getBlockEntity(rel);
        for(int i = 0; i < contents.length; i++) hopper.setItem(i, contents[i].copy());
        return hopper;
    }

    private static int total(Container... containers) {
        int n = 0;
        for(Container c : containers) for(int i = 0; i < c.getContainerSize(); i++) n += c.getItem(i).getCount();
        return n;
    }

    private static int count(Container c, Item item) {
        int n = 0;
        for(int i = 0; i < c.getContainerSize(); i++) if(c.getItem(i).is(item)) n += c.getItem(i).getCount();
        return n;
    }

    private static void clear(Container c) {
        for(int i = 0; i < c.getContainerSize(); i++) c.setItem(i, ItemStack.EMPTY);
    }

    private static String describe(Container c) {
        List<String> out = new ArrayList<>();
        for(int i = 0; i < c.getContainerSize(); i++) if(!c.getItem(i).isEmpty()) out.add(i + "=" + c.getItem(i).getCount() + "x" + BuiltInRegistries.ITEM.getKey(c.getItem(i).getItem()));
        return out.toString();
    }

    /** The menu slot that shows {@code container}'s slot {@code index}. */
    private static int menuSlot(AbstractContainerMenu menu, Container container, int index) {
        for(int i = 0; i < menu.slots.size(); i++) {
            Slot slot = menu.slots.get(i);
            if(slot.container == container && slot.getContainerSlot() == index) return i;
        }
        throw new net.minecraft.gametest.framework.GameTestAssertException("the menu has no slot for " + container + " slot " + index);
    }

    /** Shift-clicks the player's inventory slot {@code invSlot} in the menu and returns what is left there. */
    private static ItemStack shift(AbstractContainerMenu menu, Player player, int invSlot, ItemStack stack) {
        player.getInventory().setItem(invSlot, stack.copy());
        menu.quickMoveStack(player, menuSlot(menu, player.getInventory(), invSlot));
        ItemStack left = player.getInventory().getItem(invSlot).copy();
        player.getInventory().setItem(invSlot, ItemStack.EMPTY);
        return left;
    }

    // ---------------------------------------------------------------- 1. barrel and fluid tank automation (TileEntityBarrel.java:140-164)

    private static ItemStack waterBucket() { return s(Items.WATER_BUCKET, 1); }
    private static ItemStack emptyTank() { return s(NtmItems.FLUID_TANK_EMPTY.get(), 1); }
    private static ItemStack fullTank(com.hbm.inventory.fluid.FluidType type) { return MetaHelper.newStack(NtmItems.FLUID_TANK_FULL.get(), 1, type.getID()); }

    /**
     * TileEntityBarrel.java:140-164: every side exposes {2, 3, 4, 5}; canInsertItem lets a container with this tank's fluid (content within
     * capacity) into 2 and an empty container this fluid can fill (within capacity) into 4, nothing into 3 or 5; canExtractItem takes 3 and 5 only.
     * The fluid tank is a TileEntityBarrel (TileEntityMachineFluidTank.java:39).
     */
    private static void barrelRules(GameTestHelper helper, String name, BlockPos rel, Container be, FluidTank tank) {
        ServerLevel level = helper.getLevel();
        BlockPos abs = helper.absolutePos(rel);
        tank.setTankType(Fluids.WATER);
        tank.setFill(0);
        clear(be);
        int[] map = { 2, 3, 4, 5 };
        for(Direction d : Direction.values()) {
            IItemHandler h = handler(level, abs, d);
            check(h != null && h.getSlots() == 4, name + ": the handler from " + d + " is " + h + (h == null ? "" : " with " + h.getSlots() + " slots") + ", expected 4 (slots 2-5 from every side, :162-164)");
            // nothing into 3 or 5, whatever it is
            for(ItemStack st : new ItemStack[] { waterBucket(), emptyTank(), fullTank(Fluids.WATER), s(Items.STONE, 1) }) {
                check(h.insertItem(1, st.copy(), true).getCount() == 1, name + ": from " + d + " slot 3 took " + st + " (:140-148 never slot 3)");
                check(h.insertItem(3, st.copy(), true).getCount() == 1, name + ": from " + d + " slot 5 took " + st + " (:140-148 never slot 5)");
            }
            // slot 2: a container holding water
            check(h.insertItem(0, waterBucket(), true).isEmpty(), name + ": from " + d + " slot 2 refused a water bucket (:145-146)");
            check(h.insertItem(0, fullTank(Fluids.WATER), true).isEmpty(), name + ": from " + d + " slot 2 refused a full water tank");
            check(h.insertItem(0, fullTank(Fluids.OIL), true).getCount() == 1, name + ": from " + d + " slot 2 took a tank of oil into a water barrel");
            check(h.insertItem(0, emptyTank(), true).getCount() == 1, name + ": from " + d + " slot 2 took an empty tank");
            check(h.insertItem(0, s(Items.STONE, 1), true).getCount() == 1, name + ": from " + d + " slot 2 took stone");
            // slot 4: an empty container water can fill
            check(h.insertItem(2, emptyTank(), true).isEmpty(), name + ": from " + d + " slot 4 refused an empty fluid tank (:142-143)");
            check(h.insertItem(2, s(Items.BUCKET, 1), true).isEmpty(), name + ": from " + d + " slot 4 refused an empty bucket");
            check(h.insertItem(2, waterBucket(), true).getCount() == 1, name + ": from " + d + " slot 4 took a full bucket");
            check(h.insertItem(2, s(Items.STONE, 1), true).getCount() == 1, name + ": from " + d + " slot 4 took stone");
            // taking: 3 and 5 only (:158-160)
            for(int k = 0; k < 4; k++) be.setItem(map[k], s(Items.STONE, 2));
            for(int k = 0; k < 4; k++) {
                ItemStack got = h.extractItem(k, 1, true);
                boolean want = map[k] == 3 || map[k] == 5;
                check(got.isEmpty() != want, name + ": from " + d + " extracting slot " + map[k] + " gave " + got + ", expected " + (want ? "a stone" : "nothing") + " (:158-160)");
            }
            clear(be);
        }

        // capacity: a 16 000 mB fluid barrel goes in only where it fits (:142,146)
        boolean fits = 16_000 <= tank.getMaxFill();
        IItemHandler up = handler(level, abs, Direction.UP);
        check(up.insertItem(0, MetaHelper.newStack(NtmItems.FLUID_BARREL_FULL.get(), 1, Fluids.WATER.getID()), true).isEmpty() == fits,
                name + " (" + tank.getMaxFill() + " mB): a full 16 000 mB fluid barrel " + (fits ? "was refused" : "was taken") + " into slot 2");
        check(up.insertItem(2, s(NtmItems.FLUID_BARREL_EMPTY.get(), 1), true).isEmpty() == fits,
                name + " (" + tank.getMaxFill() + " mB): an empty 16 000 mB fluid barrel " + (fits ? "was refused" : "was taken") + " into slot 4");

        // the crane path: AdjacentInventory from every face; items only land in 2 and 4, only 3 and 5 can be taken, nothing is lost or made
        for(Direction d : Direction.values()) {
            ItemStack stone = AdjacentInventory.insert(level, abs, d, s(Items.STONE, 3));
            check(stone.getCount() == 3 && total(be) == 0, name + ": the crane path put stone in from " + d + ": " + describe(be));
            ItemStack rest = AdjacentInventory.insert(level, abs, d, waterBucket());
            check(rest.isEmpty() && be.getItem(2).is(Items.WATER_BUCKET) && total(be) == 1, name + ": the crane path from " + d + " put a water bucket at " + describe(be) + ", expected slot 2");
            rest = AdjacentInventory.insert(level, abs, d, emptyTank());
            check(rest.isEmpty() && be.getItem(4).is(NtmItems.FLUID_TANK_EMPTY.get()) && total(be) == 2, name + ": the crane path from " + d + " put an empty tank at " + describe(be) + ", expected slot 4");
            check(be.getItem(3).isEmpty() && be.getItem(5).isEmpty(), name + ": the crane path from " + d + " filled slot 3 or 5: " + describe(be));
            be.setItem(3, s(Items.BUCKET, 1));
            be.setItem(5, fullTank(Fluids.WATER));
            AdjacentInventory.Source src = AdjacentInventory.source(level, abs, d);
            check(src != null && src.size() == 4, name + ": the crane source from " + d + " is " + (src == null ? "none" : src.size() + " slots"));
            int taken = 0;
            for(int i = 0; i < src.size(); i++) {
                boolean want = map[i] == 3 || map[i] == 5;
                check(src.canTake(i) == want, name + ": the crane source from " + d + " says slot " + map[i] + (want ? " cannot" : " can") + " be taken");
                if(src.canTake(i)) taken += src.take(i, 64, false).getCount();
            }
            check(taken == 2 && total(be) == 2 && be.getItem(2).is(Items.WATER_BUCKET) && be.getItem(4).is(NtmItems.FLUID_TANK_EMPTY.get()),
                    name + ": the crane took " + taken + " from " + d + ", left " + describe(be) + ", expected the bucket and the full tank taken and slots 2 / 4 kept");
            clear(be);
        }
    }

    /**
     * Hoppers: above, a water bucket, an empty fluid tank and a stone; below, an empty hopper. The bucket enters slot 2, the empty tank slot 4,
     * the stone nowhere; the machine's own tick empties the bucket into the tank (bucket to slot 3) and fills the empty tank (full tank to
     * slot 5), and the lower hopper takes exactly those two out.
     */
    private static void barrelHoppers(GameTestHelper helper, String name, BlockPos rel, Container be, FluidTank tank) {
        tank.setTankType(Fluids.WATER);
        tank.setFill(0);
        clear(be);
        Container above = hopper(helper, rel.above(), waterBucket(), emptyTank(), s(Items.STONE, 1));
        Container below = hopper(helper, rel.below());
        int before = total(above, be, below);
        helper.runAfterDelay(HOPPER_WAIT, guard(() -> {
            check(total(above, be, below) == before, name + ": the hoppers and the machine hold " + total(above, be, below) + " items, expected " + before + " (above " + describe(above) + ", machine " + describe(be) + ", below " + describe(below) + ")");
            check(count(above, Items.STONE) == 1 && total(above) == 1, name + ": the upper hopper holds " + describe(above) + ", expected the stone alone");
            check(count(below, Items.BUCKET) == 1 && count(below, NtmItems.FLUID_TANK_FULL.get()) == 1 && total(below) == 2,
                    name + ": the lower hopper holds " + describe(below) + ", expected the emptied bucket and the filled tank (slots 3 and 5)");
            check(total(be) == 0 && tank.getFill() == 0, name + ": the machine keeps " + describe(be) + " and " + tank.getFill() + " mB");
            LOGGER.info("{} {} hoppers: above {}, machine {}, below {}", TAG, name, describe(above), describe(be), describe(below));
            passed(name + "_hoppers").run();
            helper.succeed();
        }));
    }

    @GameTest(template = TEMPLATE, batch = "hbm32b_barrel_automation", timeoutTicks = 200)
    public static void barrel_automation(GameTestHelper helper) {
        guard(() -> {
            BarrelBlockEntity steel = core(helper, new BlockPos(3, 2, 3), NtmBlocks.BARREL_STEEL.get(), BarrelBlockEntity.class);
            barrelRules(helper, "steel barrel", new BlockPos(3, 2, 3), steel, steel.tank);
            BarrelBlockEntity plastic = core(helper, new BlockPos(7, 2, 3), NtmBlocks.BARREL_PLASTIC.get(), BarrelBlockEntity.class);
            barrelRules(helper, "plastic barrel", new BlockPos(7, 2, 3), plastic, plastic.tank);
            BarrelBlockEntity hopped = core(helper, new BlockPos(10, 3, 10), NtmBlocks.BARREL_STEEL.get(), BarrelBlockEntity.class);
            barrelHoppers(helper, "barrel", new BlockPos(10, 3, 10), hopped, hopped.tank);
        }).run();
    }

    @GameTest(template = TEMPLATE, batch = "hbm32b_fluid_tank_automation", timeoutTicks = 200)
    public static void fluid_tank_automation(GameTestHelper helper) {
        guard(() -> {
            MachineFluidTankBlockEntity tank = core(helper, new BlockPos(3, 2, 3), NtmBlocks.MACHINE_FLUID_TANK.get(), MachineFluidTankBlockEntity.class);
            barrelRules(helper, "fluid tank", new BlockPos(3, 2, 3), tank, tank.tank);
            MachineFluidTankBlockEntity hopped = core(helper, new BlockPos(10, 3, 10), NtmBlocks.MACHINE_FLUID_TANK.get(), MachineFluidTankBlockEntity.class);
            barrelHoppers(helper, "fluid tank", new BlockPos(10, 3, 10), hopped, hopped.tank);
        }).run();
    }

    // ---------------------------------------------------------------- 2. the menus

    // ContainerBarrel.java:14-19: 0, 2, 4 SlotNonRetarded (isItemValidForSlot: slot 0 only the fluid identifier, any item elsewhere, TileEntityBarrel.java:152-156),
    // 1, 3, 5 SlotTakeOnly; shift-click from the player (ContainerBase.java:37-63) is InventoryUtil.mergeItemStack over 0-5, which asks isItemValid (InventoryUtil.java:526):
    // stacks of the same item first, then empty slots, so nothing ever reaches 1, 3 or 5
    @GameTest(template = TEMPLATE, batch = "hbm32b_barrel_menu", timeoutTicks = 100)
    public static void barrel_menu(GameTestHelper helper) {
        guard(() -> {
            BarrelBlockEntity be = core(helper, new BlockPos(4, 2, 4), NtmBlocks.BARREL_STEEL.get(), BarrelBlockEntity.class);
            be.tank.setTankType(Fluids.WATER);
            Player player = helper.makeMockPlayer(GameType.SURVIVAL);
            BarrelMenu menu = new BarrelMenu(0, player.getInventory(), be);
            ItemStack id = s(NtmItems.FLUID_IDENTIFIER_MULTI.get(), 1);
            ItemStack stone = s(Items.STONE, 1);
            for(int i = 0; i < 6; i++) {
                Slot slot = menu.slots.get(menuSlot(menu, be, i));
                boolean input = i == 0 || i == 2 || i == 4;
                check(slot.mayPlace(id) == input, "barrel menu slot " + i + (input ? " refuses" : " takes") + " the fluid identifier");
                check(slot.mayPlace(stone) == (i == 2 || i == 4), "barrel menu slot " + i + (i == 2 || i == 4 ? " refuses" : " takes") + " stone (slot 0 only the identifier, 2 and 4 anything)");
            }

            // by hand: a carried stack goes into 2, not into 3
            menu.setCarried(s(Items.STONE, 5));
            menu.clicked(menuSlot(menu, be, 3), 0, ClickType.PICKUP, player);
            check(be.getItem(3).isEmpty() && menu.getCarried().getCount() == 5, "a click put stone into the take-only slot 3: " + describe(be));
            menu.clicked(menuSlot(menu, be, 2), 0, ClickType.PICKUP, player);
            check(be.getItem(2).is(Items.STONE) && be.getItem(2).getCount() == 5 && menu.getCarried().isEmpty(), "a click did not put the stone into slot 2: " + describe(be));
            menu.setCarried(s(Items.STONE, 5));
            menu.clicked(menuSlot(menu, be, 0), 0, ClickType.PICKUP, player);
            check(be.getItem(0).isEmpty() && menu.getCarried().getCount() == 5, "a click put stone into the identifier slot 0");
            menu.setCarried(ItemStack.EMPTY);
            clear(be);

            // shift-click: the identifier goes to 0
            ItemStack left = shift(menu, player, 9, id);
            check(left.isEmpty() && be.getItem(0).is(NtmItems.FLUID_IDENTIFIER_MULTI.get()), "the shift-clicked identifier landed at " + describe(be) + ", left " + left + ", expected slot 0");
            // the outputs hold stone already; shift-clicked stone fills 2, then 4, and never joins 1, 3 or 5
            be.setItem(1, s(Items.STONE, 10));
            be.setItem(3, s(Items.STONE, 10));
            be.setItem(5, s(Items.STONE, 10));
            left = shift(menu, player, 9, s(Items.STONE, 64));
            check(left.isEmpty() && be.getItem(2).getCount() == 64 && be.getItem(4).isEmpty(), "64 stone went to " + describe(be) + ", left " + left + ", expected all in slot 2");
            left = shift(menu, player, 9, s(Items.STONE, 64));
            check(left.isEmpty() && be.getItem(4).getCount() == 64, "the next 64 stone went to " + describe(be) + ", left " + left + ", expected all in slot 4");
            left = shift(menu, player, 9, s(Items.STONE, 7));
            check(left.getCount() == 7, "with 2 and 4 full, 7 stone left " + left + " in the player's slot, expected all 7 (nothing into 1, 3, 5)");
            check(be.getItem(1).getCount() == 10 && be.getItem(3).getCount() == 10 && be.getItem(5).getCount() == 10, "an output slot changed: " + describe(be));
            // a part stack merges into slot 2 first, the rest goes into 4
            be.setItem(2, s(Items.STONE, 60));
            be.setItem(4, ItemStack.EMPTY);
            left = shift(menu, player, 9, s(Items.STONE, 64));
            check(left.isEmpty() && be.getItem(2).getCount() == 64 && be.getItem(4).getCount() == 60, "64 stone onto 60 in slot 2 gave " + describe(be) + ", expected 64 / 60");
        }).run();
        passed("barrel_menu").run();
        helper.succeed();
    }

    // ContainerMachineFluidTank.java:19-24: six plain Slots (any item by hand into any of them); :56-63 shift-click from the player is vanilla
    // mergeItemStack(stack, 0, 5): stacks of the same item in 0-4 first, then the first empty slot of 0-4, never slot 5
    @GameTest(template = TEMPLATE, batch = "hbm32b_fluid_tank_menu", timeoutTicks = 100)
    public static void fluid_tank_menu(GameTestHelper helper) {
        guard(() -> {
            MachineFluidTankBlockEntity be = core(helper, new BlockPos(4, 2, 4), NtmBlocks.MACHINE_FLUID_TANK.get(), MachineFluidTankBlockEntity.class);
            be.tank.setTankType(Fluids.WATER);
            Player player = helper.makeMockPlayer(GameType.SURVIVAL);
            MachineFluidTankMenu menu = new MachineFluidTankMenu(0, player.getInventory(), be);
            for(int i = 0; i < 6; i++) {
                Slot slot = menu.slots.get(menuSlot(menu, be, i));
                check(slot.mayPlace(s(Items.STONE, 1)), "fluid tank menu slot " + i + " refuses stone (plain Slot, :19-24)");
            }
            menu.setCarried(s(Items.STONE, 3));
            menu.clicked(menuSlot(menu, be, 5), 0, ClickType.PICKUP, player);
            check(be.getItem(5).is(Items.STONE) && be.getItem(5).getCount() == 3 && menu.getCarried().isEmpty(), "a click did not put stone into slot 5: " + describe(be));
            clear(be);

            ItemStack left = shift(menu, player, 9, s(Items.STONE, 10));
            check(left.isEmpty() && be.getItem(0).is(Items.STONE) && be.getItem(0).getCount() == 10 && total(be) == 10, "shift-clicked stone went to " + describe(be) + ", expected slot 0, the first empty one (:61)");
            // 0-4 hold other things, 3 holds stone, 5 holds stone: the stone merges into 3 and never reaches 5
            for(int i = 0; i < 5; i++) be.setItem(i, s(Items.DIRT, 64));
            be.setItem(3, s(Items.STONE, 3));
            be.setItem(5, s(Items.STONE, 3));
            left = shift(menu, player, 9, s(Items.STONE, 10));
            check(left.isEmpty() && be.getItem(3).getCount() == 13 && be.getItem(5).getCount() == 3, "stone went to " + describe(be) + ", left " + left + ", expected it merged into slot 3 and slot 5 untouched");
            be.setItem(3, s(Items.DIRT, 64));
            left = shift(menu, player, 9, s(Items.STONE, 10));
            check(left.getCount() == 10 && be.getItem(5).getCount() == 3, "with 0-4 full of dirt, stone went to " + describe(be) + ", left " + left + ", expected all 10 left (never slot 5)");
        }).run();
        passed("fluid_tank_menu").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 3. satellite linker (TileEntityMachineSatLinker.java:20,32-61)

    private static ItemStack chip(int freq) {
        ItemStack chip = s(NtmItems.SAT_CHIP.get(), 1);
        ISatChip.setFreqS(chip, freq);
        return chip;
    }

    @GameTest(template = TEMPLATE, batch = "hbm32b_sat_linker", timeoutTicks = 200)
    public static void sat_linker(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos rel = new BlockPos(3, 2, 3);
        MachineSatLinkerBlockEntity be = core(helper, rel, NtmBlocks.MACHINE_SATLINKER.get(), MachineSatLinkerBlockEntity.class);
        BlockPos abs = helper.absolutePos(rel);
        BlockPos hopRel = new BlockPos(10, 3, 10);
        MachineSatLinkerBlockEntity hopped = core(helper, hopRel, NtmBlocks.MACHINE_SATLINKER.get(), MachineSatLinkerBlockEntity.class);
        guard(() -> {
            // :41-44 every side sees slot 1; :32-34 only chips go in; :36-39 taking only while the two frequencies match
            be.setItem(0, chip(777));
            for(Direction d : Direction.values()) {
                IItemHandler h = handler(level, abs, d);
                check(h != null && h.getSlots() == 1, "the linker's handler from " + d + " has " + (h == null ? "none" : h.getSlots() + " slots") + ", expected 1 (slot 1)");
                check(h.insertItem(0, s(Items.STONE, 1), true).getCount() == 1, "the linker took stone from " + d);
                check(h.insertItem(0, chip(1), true).isEmpty(), "the linker refused a chip from " + d);
                be.setItem(1, chip(5));
                check(h.extractItem(0, 1, true).isEmpty(), "the linker gave a chip of frequency 5 from " + d + " while slot 0 holds 777");
                be.setItem(1, chip(777));
                check(!h.extractItem(0, 1, true).isEmpty(), "the linker kept a chip of frequency 777 from " + d + " while slot 0 holds 777");
                be.setItem(1, ItemStack.EMPTY);
            }
            ItemStack rest = AdjacentInventory.insert(level, abs, Direction.EAST, chip(3));
            check(rest.isEmpty() && be.getItem(1).is(NtmItems.SAT_CHIP.get()), "the crane path did not put a chip into slot 1: " + describe(be));
            AdjacentInventory.Source src = AdjacentInventory.source(level, abs, Direction.EAST);
            check(src != null && src.size() == 1 && !src.canTake(0), "the crane source can take a chip of frequency 3 while slot 0 holds 777");
            be.setItem(1, chip(5));
            be.setItem(0, ItemStack.EMPTY);
            be.setItem(2, chip(-1));

            // hoppers: a blank chip goes into slot 1, takes slot 0's frequency on the linker's tick and leaves through the lower hopper
            hopped.setItem(0, chip(4242));
        }).run();
        Container above = hopper(helper, hopRel.above(), chip(0));
        Container below = hopper(helper, hopRel.below());
        helper.runAfterDelay(HOPPER_WAIT, guard(() -> {
            // :48-50 an empty slot 0 copies nothing: slot 1 keeps its 5; :52-58 slot 2's chip got a fresh id in [0, 10 000 000)
            check(ISatChip.getFreqS(be.getItem(1)) == 5, "with slot 0 empty, slot 1's chip has frequency " + ISatChip.getFreqS(be.getItem(1)) + ", expected 5 kept (:48 needs two chips)");
            int fresh = ISatChip.getFreqS(be.getItem(2));
            check(fresh >= 0 && fresh < MachineSatLinkerBlockEntity.SAT_ID_RANGE, "slot 2's chip has frequency " + fresh + ", expected a new id in [0, 10 000 000) (:20,52-58)");
            check(handler(level, abs, Direction.DOWN).extractItem(0, 1, true).isEmpty(), "the chip of frequency 5 can be taken while slot 0 is empty (frequency 0)");

            check(total(above) == 0 && hopped.getItem(1).isEmpty(), "the chip did not pass through: above " + describe(above) + ", linker " + describe(hopped));
            check(count(below, NtmItems.SAT_CHIP.get()) == 1 && ISatChip.getFreqS(below.getItem(0)) == 4242, "the lower hopper holds " + describe(below) + " with frequency " + ISatChip.getFreqS(below.getItem(0)) + ", expected the chip with 4242");
            check(ISatChip.getFreqS(hopped.getItem(0)) == 4242 && total(above, hopped, below) == 2, "the linker holds " + describe(hopped) + ", expected slot 0's chip alone (2 chips in all)");
            passed("sat_linker").run();
            helper.succeed();
        }));
    }

    // ---------------------------------------------------------------- 4. the proxy's isEmpty (TileEntityProxyCombo.java:174-191: every inventory call is the core's)

    @GameTest(template = TEMPLATE, batch = "hbm32b_proxy_is_empty", timeoutTicks = 100)
    public static void proxy_is_empty(GameTestHelper helper) {
        guard(() -> {
            BlockPos center = new BlockPos(8, 1, 8);
            SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.MACHINE_CRYSTALLIZER.get(), center, Direction.NORTH);
            MachineCrystallizerBlockEntity core = SmokeTestSupport.blockEntity(helper, center, MachineCrystallizerBlockEntity.class);
            for(BlockPos extra : SmokeTestSupport.crystallizerExtras(center)) {
                ProxyComboBlockEntity proxy = SmokeTestSupport.blockEntity(helper, extra, ProxyComboBlockEntity.class);
                check(proxy.hasInventory(), "the port " + extra + " has no inventory flag");
                clear(core);
                check(core.isEmpty() && proxy.isEmpty(), "the port " + extra + " says isEmpty " + proxy.isEmpty() + " for an empty core");
                core.setItem(MachineCrystallizerBlockEntity.SLOT_OUTPUT, s(Items.IRON_INGOT, 1));
                check(!proxy.isEmpty(), "the port " + extra + " says empty while the core holds " + describe(core));
            }
            clear(core);
            helper.destroyBlock(center);
        }).run();
        passed("proxy_is_empty").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 5. blast furnace (TileEntityMachineBlastFurnace.java:221-252)

    @GameTest(template = TEMPLATE, batch = "hbm32b_blast_furnace", timeoutTicks = 200)
    public static void blast_furnace(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos rel = new BlockPos(3, 2, 3);
        MachineBlastFurnaceBlockEntity be = core(helper, rel, NtmBlocks.MACHINE_BLAST_FURNACE.get(), MachineBlastFurnaceBlockEntity.class);
        BlockPos abs = helper.absolutePos(rel);
        int s1 = MachineBlastFurnaceBlockEntity.SLOT_INPUT_1;
        int s2 = MachineBlastFurnaceBlockEntity.SLOT_INPUT_2;
        // iron ingot and sand: the two inputs of blast.steelFromIngot
        Item a = Items.IRON_INGOT;
        Item b = Items.SAND;
        BlockPos hopRel = new BlockPos(10, 3, 10);
        MachineBlastFurnaceBlockEntity hopped = core(helper, hopRel, NtmBlocks.MACHINE_BLAST_FURNACE.get(), MachineBlastFurnaceBlockEntity.class);
        guard(() -> {
            // getAccessibleSlotsFromSide {1, 2, 0, 3, 4}: handler index 0 = slot 1, index 1 = slot 2
            for(Direction d : Direction.values()) {
                IItemHandler h = handler(level, abs, d);
                check(h != null && h.getSlots() == 5, "the blast furnace handler from " + d + " has " + (h == null ? "none" : h.getSlots() + " slots"));
                clear(be);
                be.setItem(s1, s(a, 1));
                check(h.insertItem(1, s(a, 1), true).getCount() == 1, "from " + d + " slot 2 took iron while slot 1 holds iron (:229-231 repetition prevention)");
                check(h.insertItem(1, s(b, 1), true).isEmpty(), "from " + d + " slot 2 refused sand while slot 1 holds iron");
                clear(be);
                be.setItem(s2, s(a, 1));
                check(h.insertItem(0, s(a, 1), true).getCount() == 1, "from " + d + " slot 1 took iron while slot 2 holds iron (:230)");
                check(h.insertItem(0, s(b, 1), true).isEmpty(), "from " + d + " slot 1 refused sand while slot 2 holds iron");
            }
            // the manual rule (isItemValidForSlot :221-225, the menu's slots) still accepts the repeat
            clear(be);
            be.setItem(s1, s(a, 1));
            check(be.canPlaceItem(s2, s(a, 1)), "canPlaceItem refuses iron in slot 2 while slot 1 holds iron (the manual rule has no repetition check)");
            Player player = helper.makeMockPlayer(GameType.SURVIVAL);
            MachineBlastFurnaceMenu menu = new MachineBlastFurnaceMenu(0, player.getInventory(), be);
            int ms2 = menuSlot(menu, be, s2);
            check(menu.slots.get(ms2).mayPlace(s(a, 1)), "the menu's slot 2 refuses iron while slot 1 holds iron");
            menu.setCarried(s(a, 3));
            menu.clicked(ms2, 0, ClickType.PICKUP, player);
            check(be.getItem(s2).is(a) && be.getItem(s2).getCount() == 3 && menu.getCarried().isEmpty(), "a click did not put iron into slot 2 next to iron: " + describe(be));
            menu.setCarried(ItemStack.EMPTY);

            // the crane path: slot 1 full of iron, more iron finds no slot, sand goes into slot 2
            clear(be);
            be.setItem(s1, s(a, 64));
            ItemStack rest = AdjacentInventory.insert(level, abs, Direction.UP, s(a, 3));
            check(rest.getCount() == 3 && be.getItem(s2).isEmpty(), "the crane path put iron into slot 2 next to a full slot 1 of iron: " + describe(be));
            rest = AdjacentInventory.insert(level, abs, Direction.UP, s(b, 2));
            check(rest.isEmpty() && be.getItem(s2).is(b) && be.getItem(s2).getCount() == 2, "the crane path did not put sand into slot 2: " + describe(be));
            clear(be);

            hopped.setItem(s1, s(a, 64));
        }).run();
        Container above = hopper(helper, hopRel.above(), s(a, 1), s(b, 1));
        Container below = hopper(helper, hopRel.below());
        int before = total(above, hopped, below);
        helper.runAfterDelay(HOPPER_WAIT, guard(() -> {
            check(total(above, hopped, below) == before, "the blast furnace hoppers hold " + total(above, hopped, below) + " items, expected " + before);
            check(count(above, a) == 1 && total(above) == 1, "the upper hopper holds " + describe(above) + ", expected the iron ingot left (slot 2 refuses iron next to iron)");
            check(hopped.getItem(s2).is(b) && hopped.getItem(s2).getCount() == 1 && hopped.getItem(s1).getCount() == 64, "the blast furnace holds " + describe(hopped) + ", expected 64 iron in 1 and the sand in 2");
            check(total(below) == 0, "the lower hopper took " + describe(below) + " from the inputs");
            passed("blast_furnace").run();
            helper.succeed();
        }));
    }

    // ---------------------------------------------------------------- 6. wood burner (TileEntityMachineWoodBurner.java:247-260)

    @GameTest(template = TEMPLATE, batch = "hbm32b_wood_burner", timeoutTicks = 200)
    public static void wood_burner(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos rel = new BlockPos(3, 2, 3);
        MachineWoodBurnerBlockEntity be = core(helper, rel, NtmBlocks.MACHINE_WOOD_BURNER.get(), MachineWoodBurnerBlockEntity.class);
        BlockPos abs = helper.absolutePos(rel);
        BlockPos hopRel = new BlockPos(10, 3, 10);
        MachineWoodBurnerBlockEntity hopped = core(helper, hopRel, NtmBlocks.MACHINE_WOOD_BURNER.get(), MachineWoodBurnerBlockEntity.class);
        Item ash = NtmItems.POWDER_ASH_WOOD.get();
        guard(() -> {
            // the burner's own tick would eat the fuel: a running burn time keeps it in the slot (updateSolidBurn only takes fuel at 0)
            be.burnTime = be.maxBurnTime = 1_000_000;
            be.isOn = false;
            for(Direction d : Direction.values()) {
                IItemHandler h = handler(level, abs, d);
                check(h != null && h.getSlots() == 2, "the wood burner's handler from " + d + " has " + (h == null ? "none" : h.getSlots() + " slots") + ", expected 2 (:248-250 {0, 1})");
                clear(be);
                check(h.insertItem(0, s(Items.OAK_LOG, 1), true).isEmpty(), "from " + d + " the fuel slot refused a log");
                check(h.insertItem(0, s(Items.STONE, 1), true).getCount() == 1, "from " + d + " the fuel slot took stone (:253-255 only fuel into 0)");
                check(h.insertItem(1, s(ash, 1), true).getCount() == 1, "from " + d + " the ash slot took ash (:253-255 nothing into 1)");
                be.setItem(MachineWoodBurnerBlockEntity.SLOT_FUEL, s(Items.OAK_LOG, 2));
                be.setItem(MachineWoodBurnerBlockEntity.SLOT_ASH, s(ash, 2));
                check(h.extractItem(0, 1, true).isEmpty(), "from " + d + " the fuel could be taken (:257-259 only slot 1)");
                ItemStack got = h.extractItem(1, 1, true);
                check(got.is(ash), "from " + d + " the ash could not be taken: " + got);
            }
            clear(be);
            ItemStack rest = AdjacentInventory.insert(level, abs, Direction.NORTH, s(Items.OAK_LOG, 3));
            check(rest.isEmpty() && be.getItem(MachineWoodBurnerBlockEntity.SLOT_FUEL).getCount() == 3 && total(be) == 3, "the crane path put logs at " + describe(be));
            check(AdjacentInventory.insert(level, abs, Direction.NORTH, s(Items.STONE, 1)).getCount() == 1, "the crane path put stone in");
            be.setItem(MachineWoodBurnerBlockEntity.SLOT_ASH, s(ash, 1));
            be.setItem(MachineWoodBurnerBlockEntity.SLOT_BATTERY, s(Items.STONE, 1));
            AdjacentInventory.Source src = AdjacentInventory.source(level, abs, Direction.NORTH);
            check(src != null && src.size() == 2 && !src.canTake(0) && src.canTake(1), "the crane source is " + (src == null ? "none" : src.size() + " slots, take 0 " + src.canTake(0) + ", take 1 " + src.canTake(1)));
            clear(be);

            hopped.burnTime = hopped.maxBurnTime = 1_000_000;
            hopped.isOn = false;
            hopped.setItem(MachineWoodBurnerBlockEntity.SLOT_ASH, s(ash, 3));
            hopped.setItem(MachineWoodBurnerBlockEntity.SLOT_IDENTIFIER, s(Items.DIRT, 1));
            hopped.setItem(MachineWoodBurnerBlockEntity.SLOT_FLUID_OUT, s(Items.DIRT, 1));
            hopped.setItem(MachineWoodBurnerBlockEntity.SLOT_BATTERY, s(Items.DIRT, 1));
        }).run();
        Container above = hopper(helper, hopRel.above(), s(Items.OAK_LOG, 2), s(Items.STONE, 1));
        Container below = hopper(helper, hopRel.below());
        int before = total(above, hopped, below);
        helper.runAfterDelay(HOPPER_WAIT, guard(() -> {
            check(total(above, hopped, below) == before, "the wood burner hoppers hold " + total(above, hopped, below) + " items, expected " + before + " (above " + describe(above) + ", burner " + describe(hopped) + ", below " + describe(below) + ")");
            check(hopped.getItem(MachineWoodBurnerBlockEntity.SLOT_FUEL).getCount() == 2 && count(above, Items.STONE) == 1 && total(above) == 1, "fuel: burner " + describe(hopped) + ", above " + describe(above) + ", expected both logs in slot 0 and the stone left");
            check(count(below, ash) == 3 && total(below) == 3, "the lower hopper holds " + describe(below) + ", expected the 3 ash and nothing from slots 2, 4, 5");
            passed("wood_burner").run();
            helper.succeed();
        }));
    }

    // ---------------------------------------------------------------- 7. tungsten crate (TileEntityCrateTungsten.java:62-76)

    @GameTest(template = TEMPLATE, batch = "hbm32b_tungsten_crate", timeoutTicks = 200)
    public static void tungsten_crate(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        BlockPos rel = new BlockPos(3, 2, 3);
        CrateTungstenBlockEntity be = core(helper, rel, NtmBlocks.CRATE_TUNGSTEN.get(), CrateTungstenBlockEntity.class);
        BlockPos abs = helper.absolutePos(rel);
        BlockPos hopRel = new BlockPos(10, 3, 10);
        CrateTungstenBlockEntity hopped = core(helper, hopRel, NtmBlocks.CRATE_TUNGSTEN.get(), CrateTungstenBlockEntity.class);
        guard(() -> {
            for(Item smelt : List.of(Items.RAW_IRON, Items.COBBLESTONE)) check(level.getRecipeManager().getRecipeFor(RecipeType.SMELTING, new SingleRecipeInput(s(smelt, 1)), level).isPresent(), smelt + " does not smelt");
            check(level.getRecipeManager().getRecipeFor(RecipeType.SMELTING, new SingleRecipeInput(s(Items.DIRT, 1)), level).isEmpty(), "dirt smelts");
            Item[] content = { Items.RAW_IRON, NtmItems.BILLET_POLONIUM.get(), Items.DIRT, Items.COBBLESTONE };
            boolean[] takeable = { false, false, true, false };
            for(int i = 0; i < content.length; i++) be.setItem(i, s(content[i], 2));
            for(Direction d : Direction.values()) {
                IItemHandler h = handler(level, abs, d);
                check(h != null && h.getSlots() == 27, "the crate's handler from " + d + " is " + h);
                for(int i = 0; i < content.length; i++) {
                    check(h.extractItem(i, 1, true).isEmpty() != takeable[i], "from " + d + " " + content[i] + (takeable[i] ? " cannot" : " can") + " be taken (:67-74: no polonium billet, nothing smeltable)");
                }
                check(h.insertItem(10, s(Items.RAW_IRON, 1), true).isEmpty(), "from " + d + " the crate refused raw iron going in (only taking is restricted)");
            }
            AdjacentInventory.Source src = AdjacentInventory.source(level, abs, Direction.WEST);
            for(int i = 0; i < content.length; i++) check(src.canTake(i) == takeable[i], "the crane source says " + content[i] + (takeable[i] ? " cannot" : " can") + " be taken");
            // locked: nothing (:64-65)
            be.setPins(1234);
            be.lock();
            for(Direction d : Direction.values()) check(handler(level, abs, d).extractItem(2, 1, true).isEmpty(), "the locked crate gave dirt from " + d);
            check(!AdjacentInventory.source(level, abs, Direction.WEST).canTake(2), "the crane source can take from a locked crate");

            for(int i = 0; i < content.length; i++) hopped.setItem(i, s(content[i], 2));
        }).run();
        Container below = hopper(helper, hopRel.below());
        int before = total(hopped, below);
        helper.runAfterDelay(HOPPER_WAIT, guard(() -> {
            check(total(hopped, below) == before, "the crate and hopper hold " + total(hopped, below) + " items, expected " + before);
            check(count(below, Items.DIRT) == 2 && total(below) == 2, "the hopper below the crate holds " + describe(below) + ", expected the 2 dirt alone");
            check(count(hopped, Items.RAW_IRON) == 2 && count(hopped, NtmItems.BILLET_POLONIUM.get()) == 2 && count(hopped, Items.COBBLESTONE) == 2, "the crate holds " + describe(hopped));
            passed("tungsten_crate").run();
            helper.succeed();
        }));
    }

    // ---------------------------------------------------------------- 8. launch pads (TileEntityLaunchPadBase.java:134-146)

    private static void padRules(GameTestHelper helper, String name, BlockPos rel, LaunchPadBaseBlockEntity be) {
        ServerLevel level = helper.getLevel();
        BlockPos abs = helper.absolutePos(rel);
        for(Direction d : Direction.values()) {
            IItemHandler h = handler(level, abs, d);
            check(h != null && h.getSlots() == 1, name + ": the handler from " + d + " has " + (h == null ? "none" : h.getSlots() + " slots") + ", expected 1 (:139-141 {0})");
            check(h.insertItem(0, s(NtmItems.MISSILE_GENERIC.get(), 1), true).isEmpty(), name + ": from " + d + " a missile was refused (:144-146)");
            check(h.insertItem(0, s(Items.STONE, 1), true).getCount() == 1, name + ": from " + d + " stone went in");
            check(h.insertItem(0, s(NtmItems.MISSILE_ASSEMBLY.get(), 1), true).getCount() == 1, name + ": from " + d + " a missile assembly (no missile) went in");
            be.setItem(0, s(NtmItems.MISSILE_GENERIC.get(), 1));
            check(h.extractItem(0, 1, true).isEmpty(), name + ": from " + d + " the missile could be taken (:134-136 canExtractItem false)");
            be.setItem(0, ItemStack.EMPTY);
        }
        check(AdjacentInventory.insert(level, abs, Direction.SOUTH, s(Items.STONE, 1)).getCount() == 1, name + ": the crane path put stone in");
        check(AdjacentInventory.insert(level, abs, Direction.SOUTH, s(NtmItems.MISSILE_GENERIC.get(), 1)).isEmpty() && be.getItem(0).is(NtmItems.MISSILE_GENERIC.get()), name + ": the crane path did not load the missile");
        check(!AdjacentInventory.source(level, abs, Direction.SOUTH).canTake(0), name + ": the crane source can take the missile");
        be.setItem(0, ItemStack.EMPTY);
    }

    @GameTest(template = TEMPLATE, batch = "hbm32b_launch_pads", timeoutTicks = 200)
    public static void launch_pads(GameTestHelper helper) {
        BlockPos smallRel = new BlockPos(3, 2, 3);
        BlockPos largeRel = new BlockPos(3, 2, 10);
        LaunchPadBaseBlockEntity small = core(helper, smallRel, NtmBlocks.LAUNCH_PAD.get(), LaunchPadBaseBlockEntity.class);
        LaunchPadBaseBlockEntity large = core(helper, largeRel, NtmBlocks.LAUNCH_PAD_LARGE.get(), LaunchPadBaseBlockEntity.class);
        BlockPos smallHop = new BlockPos(10, 3, 3);
        BlockPos largeHop = new BlockPos(10, 3, 10);
        LaunchPadBaseBlockEntity smallH = core(helper, smallHop, NtmBlocks.LAUNCH_PAD.get(), LaunchPadBaseBlockEntity.class);
        LaunchPadBaseBlockEntity largeH = core(helper, largeHop, NtmBlocks.LAUNCH_PAD_LARGE.get(), LaunchPadBaseBlockEntity.class);
        guard(() -> {
            padRules(helper, "launch pad", smallRel, small);
            padRules(helper, "large launch pad", largeRel, large);
        }).run();
        Container[] above = { hopper(helper, smallHop.above(), s(Items.STONE, 1), s(NtmItems.MISSILE_GENERIC.get(), 1)), hopper(helper, largeHop.above(), s(Items.STONE, 1), s(NtmItems.MISSILE_GENERIC.get(), 1)) };
        Container[] below = { hopper(helper, smallHop.below()), hopper(helper, largeHop.below()) };
        LaunchPadBaseBlockEntity[] pads = { smallH, largeH };
        helper.runAfterDelay(HOPPER_WAIT, guard(() -> {
            for(int i = 0; i < 2; i++) {
                String n = i == 0 ? "launch pad" : "large launch pad";
                check(total(above[i], pads[i], below[i]) == 2, n + ": the hoppers and pad hold " + total(above[i], pads[i], below[i]) + " items, expected 2");
                check(pads[i].getItem(0).is(NtmItems.MISSILE_GENERIC.get()), n + ": the pad holds " + describe(pads[i]) + ", expected the missile in slot 0");
                check(count(above[i], Items.STONE) == 1 && total(above[i]) == 1, n + ": the upper hopper holds " + describe(above[i]) + ", expected the stone left");
                check(total(below[i]) == 0, n + ": the lower hopper took " + describe(below[i]));
            }
            passed("launch_pads").run();
            helper.succeed();
        }));
    }

    // ---------------------------------------------------------------- 9. Soyuz launcher and heat exchanger: no accessible slots

    private static void noSlots(GameTestHelper helper, String name, BlockPos rel, Container be) {
        ServerLevel level = helper.getLevel();
        BlockPos abs = helper.absolutePos(rel);
        for(Direction d : Direction.values()) {
            IItemHandler h = handler(level, abs, d);
            check(h == null || h.getSlots() == 0, name + ": the handler from " + d + " has " + (h == null ? 0 : h.getSlots()) + " slots, expected none");
            check(AdjacentInventory.insert(level, abs, d, s(Items.STONE, 2)).getCount() == 2, name + ": the crane path put stone in from " + d);
            AdjacentInventory.Source src = AdjacentInventory.source(level, abs, d);
            check(src == null || src.size() == 0, name + ": the crane source from " + d + " has " + (src == null ? 0 : src.size()) + " slots");
        }
        check(total(be) == 0, name + " holds " + describe(be));
    }

    // ORIG TileEntitySoyuzLauncher and TileEntityHeaterHeatex implement no getAccessibleSlotsFromSide override that returns slots (TileEntityMachineBase's is empty)
    @GameTest(template = TEMPLATE, batch = "hbm32b_no_slots", timeoutTicks = 200)
    public static void soyuz_heatex_no_slots(GameTestHelper helper) {
        BlockPos soyuzRel = new BlockPos(3, 2, 3);
        BlockPos heatexRel = new BlockPos(3, 2, 10);
        SoyuzLauncherBlockEntity soyuz = core(helper, soyuzRel, NtmBlocks.SOYUZ_LAUNCHER.get(), SoyuzLauncherBlockEntity.class);
        HeaterHeatexBlockEntity heatex = core(helper, heatexRel, NtmBlocks.HEATER_HEATEX.get(), HeaterHeatexBlockEntity.class);
        guard(() -> {
            noSlots(helper, "Soyuz launcher", soyuzRel, soyuz);
            noSlots(helper, "heat exchanger", heatexRel, heatex);
            soyuz.setItem(0, s(Items.DIRT, 1));
            heatex.setItem(0, s(NtmItems.FLUID_IDENTIFIER_MULTI.get(), 1));
        }).run();
        Container[] above = { hopper(helper, soyuzRel.above(), s(Items.STONE, 1)), hopper(helper, heatexRel.above(), s(Items.STONE, 1)) };
        Container[] below = { hopper(helper, soyuzRel.below()), hopper(helper, heatexRel.below()) };
        Container[] machines = { soyuz, heatex };
        helper.runAfterDelay(HOPPER_WAIT, guard(() -> {
            for(int i = 0; i < 2; i++) {
                String n = i == 0 ? "Soyuz launcher" : "heat exchanger";
                check(count(above[i], Items.STONE) == 1 && total(above[i]) == 1, n + ": the upper hopper holds " + describe(above[i]) + ", expected the stone left");
                check(total(below[i]) == 0 && total(machines[i]) == 1, n + ": the lower hopper holds " + describe(below[i]) + ", the machine " + describe(machines[i]) + ", expected nothing moved");
            }
            passed("soyuz_heatex_no_slots").run();
            helper.succeed();
        }));
    }
}
