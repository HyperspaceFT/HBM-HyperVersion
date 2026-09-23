package com.hbm.blockentity.machine;

import com.hbm.blockentity.network.CableBaseBlockEntity;
import com.hbm.inventory.recipes.ShredderRecipes;
import com.hbm.inventory.menus.MachineShredderMenu;
import com.hbm.items.NtmItems;
import com.hbm.uninos.UniNodespace;
import api.hbm.energymk2.IBatteryItem;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;

import java.util.List;

public class ShredderRegression {
    private static int checks;
    private static final Item ORE = new Item("fixture_ore");
    private static final Item DUST = new Item("fixture_dust");
    private static final Item SMALL_DUST = new Item("small_dust", 16, 0);
    private static final Item FORBIDDEN = new Item("forbidden");
    private static final Item UNKNOWN = new Item("unknown_fallback");
    private static final class Battery extends Item implements IBatteryItem {
        Battery() { super("test_battery"); }
    }

    private static void check(boolean value, String message) {
        checks++;
        if (!value) throw new AssertionError(message);
    }

    private static MachineShredderBlockEntity machine(Level level, int x, int z) {
        var be = new MachineShredderBlockEntity(new BlockPos(x, 0, z), new BlockState());
        level.put(be);
        be.slots.set(27, new ItemStack(NtmItems.BLADES_STEEL.get()));
        be.slots.set(28, new ItemStack(NtmItems.BLADES_STEEL.get()));
        return be;
    }

    private static MachineShredderBlockEntity ready() {
        var be = machine(new Level(), 0, 0);
        be.slots.set(0, new ItemStack(ORE));
        be.setPower(10_000);
        return be;
    }

    private static void ticks(MachineShredderBlockEntity be, int n) {
        for (int i = 0; i < n; i++) be.updateEntity();
    }

    private static void output(Item input, Item result, int count) {
        ShredderRecipes.set(input, new ItemStack(result, count));
    }

    private static void progressAndBlades() {
        var be = ready();
        ticks(be, 59);
        check(be.progress == 59 && be.power == 9705 && be.slots.get(0).getCount() == 1,
                "59 ticks consume 295 HE but no input");
        be.updateEntity();
        check(be.progress == 0 && be.power == 9700 && be.slots.get(0).isEmpty(), "60th tick completes once at 300 HE");
        check(be.slots.get(9).is(DUST) && be.slots.get(9).getCount() == 2, "recipe output placed");
        check(be.slots.get(27).getDamageValue() == 1 && be.slots.get(28).getDamageValue() == 1,
                "one damage to each blade per round");
        check(be.getOperatingStatus() == MachineShredderBlockEntity.STATUS_RUNNING,
                "completion tick retains running status for client state");
        var completionBuf = new RegistryFriendlyByteBuf();
        be.serialize(completionBuf);
        var clientCopy = machine(new Level(), 0, 0);
        clientCopy.deserialize(completionBuf);
        check(clientCopy.progress == 0 && clientCopy.getOperatingStatus() == MachineShredderBlockEntity.STATUS_RUNNING,
                "completion tick synchronizes zero progress with running status");
        be.updateEntity();
        check(be.getOperatingStatus() == MachineShredderBlockEntity.STATUS_IDLE,
                "next no-input tick becomes inactive");

        be = ready();
        be.slots.set(1, new ItemStack(ORE, 2));
        ticks(be, 60);
        check(be.slots.get(0).isEmpty() && be.slots.get(1).getCount() == 1, "one unit per occupied input slot");
        check(be.slots.get(9).getCount() == 4 && be.slots.get(27).getDamageValue() == 1,
                "two inputs yield four dust but blades wear once");

        be = ready();
        be.slots.set(28, ItemStack.EMPTY);
        ticks(be, 1);
        check(be.progress == 0 && be.power == 10000, "missing right blade blocks processing");
        be.slots.set(28, new ItemStack(Items.STONE));
        ticks(be, 1);
        check(be.progress == 0, "wrong blade blocks processing");
        be.slots.set(28, new ItemStack(NtmItems.BLADES_STEEL.get()));
        be.slots.get(28).setDamageValue(256);
        ticks(be, 1);
        check(be.progress == 0, "broken right blade blocks processing");
        be.slots.get(28).setDamageValue(0);
        be.slots.set(27, new ItemStack(Items.STONE));
        be.updateEntity();
        check(be.progress == 0, "wrong left blade blocks processing");
        be.slots.set(27, new ItemStack(NtmItems.BLADES_TITANIUM.get()));
        be.slots.get(27).setDamageValue(256);
        check(be.getGearLeft() == 2, "half-worn titanium blade is still usable");
        be.slots.set(27, new ItemStack(NtmItems.BLADES_STEEL.get()));
        be.slots.get(28).setDamageValue(255);
        ticks(be, 60);
        check(be.slots.get(28).getDamageValue() == 256 && be.slots.get(9).getCount() == 2,
                "last usable blade tick produces output then retains broken blade");
        be.slots.set(0, new ItemStack(ORE));
        be.updateEntity();
        check(be.progress == 0 && be.slots.get(0).getCount() == 1, "broken blade stops next round");

        be = ready();
        be.slots.set(27, new ItemStack(NtmItems.BLADES_TITANIUM.get()));
        be.slots.get(27).setDamageValue(511);
        ticks(be, 60);
        check(be.slots.get(0).isEmpty() && be.slots.get(27).getDamageValue() == 512
                && be.getGearLeft() == 3, "titanium 511/512 completes its last round and then breaks");
        be.slots.set(0, new ItemStack(ORE));
        be.updateEntity();
        check(be.slots.get(0).getCount() == 1 && be.progress == 0,
                "broken titanium blocks subsequent processing");

        be = ready();
        be.slots.set(27, new ItemStack(NtmItems.BLADES_DESH.get()));
        check(!be.slots.get(27).isDamageableItem() && be.getGearLeft() == 1,
                "native Desh fixture is non-damageable and usable");
        be.slots.set(0, new ItemStack(ORE, 2));
        ticks(be, 120);
        check(be.slots.get(0).isEmpty() && be.slots.get(27).getDamageValue() == 0
                && be.slots.get(28).getDamageValue() == 2,
                "Desh never wears while steel counterpart wears each round");
        System.out.println("timing, parallel inputs and blade wear: passed");
    }

    private static void powerAndReset() {
        var be = ready();
        for (int amount = 0; amount < 5; amount++) {
            be.setPower(amount);
            be.updateEntity();
            check(be.progress == 0 && be.power == amount, "0..4 HE cannot start or go negative: " + amount);
        }
        be.setPower(5);
        be.updateEntity();
        check(be.progress == 1 && be.power == 0, "exact 5 HE advances one tick");
        be.updateEntity();
        check(be.progress == 0 && be.power == 0, "no power resets progress");
        be.setPower(100);
        ticks(be, 4);
        be.slots.set(27, ItemStack.EMPTY);
        be.updateEntity();
        check(be.progress == 0, "missing left blade resets progress");
        be.slots.set(27, new ItemStack(NtmItems.BLADES_STEEL.get()));
        be.slots.set(0, ItemStack.EMPTY);
        be.updateEntity();
        check(be.progress == 0, "no eligible input resets progress");
        be = ready();
        ticks(be, 20);
        be.slots.set(0, new ItemStack(UNKNOWN));
        ticks(be, 40);
        check(be.slots.get(0).isEmpty() && be.slots.get(9).is(NtmItems.DUST.get()),
                "valid mid-cycle swap inherits progress and processes current input");
        be = ready();
        ticks(be, 20);
        be.slots.set(0, ItemStack.EMPTY);
        be.updateEntity();
        be.slots.set(0, new ItemStack(ORE));
        ticks(be, 39);
        check(be.progress == 39 && be.slots.get(0).getCount() == 1,
                "invalid mid-cycle removal restarts a complete 60-tick cycle");
        System.out.println("power threshold and invalidation: passed");
    }

    private static void capacityAndComponents() {
        var be = ready();
        be.slots.set(9, new ItemStack(DUST, 63));
        be.slots.set(10, new ItemStack(DUST, 63));
        ticks(be, 60);
        check(be.slots.get(9).getCount() == 64 && be.slots.get(10).getCount() == 64,
                "output splits across two partial stacks");

        be = ready();
        be.slots.set(9, new ItemStack(DUST, 63).component("alternate"));
        ticks(be, 60);
        check(be.slots.get(9).getCount() == 63 && be.slots.get(10).getCount() == 2,
                "component mismatch routes to empty slot");

        output(FORBIDDEN, SMALL_DUST, 20);
        be = ready();
        be.slots.set(0, new ItemStack(FORBIDDEN));
        ticks(be, 60);
        check(be.slots.get(9).getCount() == 16 && be.slots.get(10).getCount() == 4,
                "item max 16 splits recipe output 20");
        var limitedLevel = new Level();
        var limited = new MachineShredderBlockEntity(new BlockPos(0, 0, 0), new BlockState()) {
            @Override public int getMaxStackSize() { return 8; }
        };
        limitedLevel.put(limited);
        limited.slots.set(0, new ItemStack(FORBIDDEN));
        limited.slots.set(9, new ItemStack(SMALL_DUST, 7));
        limited.slots.set(27, new ItemStack(NtmItems.BLADES_STEEL.get()));
        limited.slots.set(28, new ItemStack(NtmItems.BLADES_STEEL.get()));
        limited.setPower(10000);
        ticks(limited, 60);
        check(limited.slots.get(9).getCount() == 8 && limited.slots.get(10).getCount() == 8
                && limited.slots.get(11).getCount() == 8 && limited.slots.get(12).getCount() == 3,
                "container max 8 bounds partial and empty output stacks");

        be = ready();
        for (int i = 9; i < 27; i++) be.slots.set(i, new ItemStack(Items.STONE, 64));
        ticks(be, 1);
        check(be.progress == 0 && be.slots.get(0).getCount() == 1 && be.power == 10000,
                "full output blocks without consuming input or power");
        be.slots.set(9, new ItemStack(DUST, 63));
        ticks(be, 1);
        check(be.progress == 0 && be.slots.get(0).getCount() == 1,
                "one free output position is insufficient for two results");
        be = ready();
        be.slots.set(1, new ItemStack(ORE));
        for (int i = 9; i < 27; i++) be.slots.set(i, new ItemStack(Items.STONE, 64));
        be.slots.set(9, new ItemStack(DUST, 60));
        ticks(be, 60);
        check(be.slots.get(0).isEmpty() && be.slots.get(1).isEmpty() && be.slots.get(9).getCount() == 64,
                "two inputs compete for exactly four remaining output positions");
        be = ready();
        be.slots.set(1, new ItemStack(ORE));
        for (int i = 9; i < 27; i++) be.slots.set(i, new ItemStack(Items.STONE, 64));
        be.slots.set(9, new ItemStack(DUST, 62));
        ticks(be, 60);
        check(be.slots.get(0).isEmpty() && be.slots.get(1).getCount() == 1 && be.slots.get(9).getCount() == 64,
                "sequential competition preserves second input when first used final space");
        be = ready();
        be.slots.set(0, new ItemStack(UNKNOWN));
        ticks(be, 60);
        check(be.slots.get(9).is(NtmItems.DUST.get()), "unknown valid material receives fallback scrap");
        be = ready();
        be.slots.set(0, new ItemStack(FORBIDDEN));
        ShredderRecipes.set(FORBIDDEN, ItemStack.EMPTY);
        ticks(be, 1);
        check(be.progress == 0 && be.slots.get(0).getCount() == 1,
                "explicit empty recipe result cannot consume input");
        System.out.println("capacity and components: passed");
    }

    private static void persistenceAndSidedSlots() {
        var be = ready();
        be.progress = 12;
        be.soundCycle = 34;
        be.slots.get(27).setDamageValue(40);
        be.slots.get(28).setDamageValue(127);
        be.slots.set(9, new ItemStack(DUST, 7).component("retained"));
        be.slots.set(29, new ItemStack(new Battery()));
        var tag = new CompoundTag();
        be.saveAdditional(tag, null);
        var copy = machine(new Level(), 0, 0);
        copy.loadAdditional(tag, null);
        check(copy.power == be.power && copy.maxPower == be.maxPower && copy.progress == 12 && copy.soundCycle == 34,
                "production state keys round-trip through NBT");
        for (int slot = 0; slot < 30; slot++) {
            var original = be.slots.get(slot);
            var restored = copy.slots.get(slot);
            check(ItemStack.isSameItemSameComponents(original, restored)
                    && original.getCount() == restored.getCount()
                    && original.getDamageValue() == restored.getDamageValue(),
                    "production MachineBase save/load restores slot " + slot);
        }
        ticks(copy, 48);
        check(copy.progress == 0 && copy.slots.get(0).isEmpty() && copy.slots.get(27).getDamageValue() == 41
                && copy.slots.get(28).getDamageValue() == 128,
                "saved progress resumes with restored blade durability and inventory");
        var buf = new RegistryFriendlyByteBuf();
        be.serialize(buf);
        copy.deserialize(buf);
        check(copy.progress == 12 && copy.soundCycle == 34, "production sync fields round-trip");
        var invalid = new CompoundTag();
        invalid.putLong("power", Long.MAX_VALUE);
        invalid.putLong("maxPower", -1);
        invalid.putInt("progress", 999);
        invalid.putInt("soundCycle", -9);
        copy.loadAdditional(invalid, null);
        check(copy.maxPower == 10000 && copy.power == 10000 && copy.progress == 59 && copy.soundCycle == 0,
                "malformed saved fields clamp and missing/invalid capacity defaults");
        var missing = new CompoundTag();
        missing.putLong("power", -5);
        copy.loadAdditional(missing, null);
        check(copy.maxPower == 10000 && copy.power == 0 && copy.progress == 0,
                "missing capacity and negative power load safely");
        for (Direction direction : Direction.values()) {
            check(be.getSlotsForFace(direction).length == 30, "all 30 slots advertised on " + direction);
        }
        check(be.getConPos().length == 6, "six power subscription directions");
        check(!be.canPlaceItem(9, new ItemStack(ORE)), "output placement denied");
        check(!be.canPlaceItem(-1, new ItemStack(ORE)) && !be.canPlaceItem(30, new ItemStack(ORE)),
                "invalid slot indexes rejected");
        check(!be.canPlaceItem(0, new ItemStack(NtmItems.BLADES_STEEL.get()))
                && !be.canPlaceItem(0, new ItemStack(new Battery())), "blades and batteries excluded from inputs");
        check(be.canPlaceItem(27, new ItemStack(NtmItems.BLADES_STEEL.get()))
                && be.canPlaceItem(28, new ItemStack(NtmItems.BLADES_STEEL.get())), "both blade slots accept blades");
        check(be.canPlaceItem(29, new ItemStack(new Battery())), "manual battery slot accepts battery");
        check(!be.canPlaceItem(0, new ItemStack(FORBIDDEN)), "empty-result input rejected manually");
        for (Direction direction : Direction.values())
            check(!be.canPlaceItemThroughFace(29, new ItemStack(new Battery()), direction),
                    "battery automation insertion denied on " + direction);
        check(!be.canPlaceItemThroughFace(0, new ItemStack(ORE), Direction.NORTH),
                "occupied input waits while another input is empty");
        check(be.canPlaceItemThroughFace(1, new ItemStack(ORE), Direction.NORTH),
                "empty input accepts automation insertion");
        for (int i = 1; i < 9; i++) be.slots.set(i, new ItemStack(ORE, i));
        be.slots.set(0, new ItemStack(ORE, 7));
        check(!be.canPlaceItemThroughFace(0, new ItemStack(ORE), Direction.NORTH),
                "occupied input waits for less-full matching stack");
        check(be.canPlaceItemThroughFace(1, new ItemStack(ORE), Direction.NORTH),
                "least-full matching input receives automation first");
        check(be.canPlaceItemThroughFace(27, new ItemStack(NtmItems.BLADES_STEEL.get()), Direction.UP),
                "blade automation insertion allowed from any face");
        check(!be.canTakeItemThroughFace(0, be.slots.get(0), Direction.NORTH), "input extraction denied");
        check(be.canTakeItemThroughFace(9, new ItemStack(DUST), Direction.NORTH), "output extraction allowed");
        var broken = new ItemStack(NtmItems.BLADES_STEEL.get());
        broken.setDamageValue(broken.getMaxDamage());
        check(be.canTakeItemThroughFace(27, broken, Direction.NORTH)
                && !be.canTakeItemThroughFace(27, new ItemStack(NtmItems.BLADES_STEEL.get()), Direction.NORTH),
                "only broken blades can be extracted automatically");
        System.out.println("saved state, sync and sided inventory: passed");
    }

    private static void statusAndEnergyMutation() {
        var be = ready();
        int dirty = be.dirty;
        be.setPower(9000);
        check(be.dirty > dirty && be.power == 9000, "setPower change marks dirty");
        dirty = be.dirty;
        be.setPower(9000);
        check(be.dirty == dirty, "unchanged power does not mark dirty");
        check(be.transferPower(Long.MAX_VALUE) == Long.MAX_VALUE - 1000 && be.power == 10000,
                "huge transfer request only accepts remaining capacity without overflow");
        dirty = be.dirty;
        check(be.transferPower(-4) == -4 && be.power == 10000 && be.dirty == dirty,
                "negative transfer request makes no mutation");
        be.updateEntity();
        check(be.getOperatingStatus() == MachineShredderBlockEntity.STATUS_RUNNING,
                "valid recipe, blade and energy report running");
        dirty = be.dirty;
        be.updateEntity();
        check(be.dirty > dirty && be.progress == 2, "progress and consumption mark dirty");
        be.slots.set(28, ItemStack.EMPTY);
        be.updateEntity();
        check(be.progress == 0 && be.getOperatingStatus() == MachineShredderBlockEntity.STATUS_MISSING_BLADES,
                "missing blade reports missing status and resets progress");
        be.slots.set(28, new ItemStack(NtmItems.BLADES_STEEL.get()));
        be.slots.get(28).setDamageValue(256);
        be.updateEntity();
        check(be.getOperatingStatus() == MachineShredderBlockEntity.STATUS_BROKEN_BLADES,
                "broken blade reports broken status");
        be.slots.get(28).setDamageValue(0);
        be.setPower(0);
        be.updateEntity();
        check(be.getOperatingStatus() == MachineShredderBlockEntity.STATUS_NO_POWER,
                "otherwise valid process reports missing power");
        be.setPower(1000);
        for (int i = 9; i < 27; i++) be.slots.set(i, new ItemStack(Items.STONE, 64));
        be.updateEntity();
        check(be.getOperatingStatus() == MachineShredderBlockEntity.STATUS_OUTPUT_BLOCKED,
                "full outputs report blocked");
        be.slots.set(0, new ItemStack(FORBIDDEN));
        be.updateEntity();
        check(be.getOperatingStatus() == MachineShredderBlockEntity.STATUS_INVALID_INPUT,
                "explicit empty result reports invalid input");
        be.slots.set(0, ItemStack.EMPTY);
        be.updateEntity();
        check(be.getOperatingStatus() == MachineShredderBlockEntity.STATUS_IDLE,
                "empty input reports idle");
        System.out.println("energy mutation and operating status: passed");
    }

    private static void networkProduction() {
        UniNodespace.levels.clear();
        UniNodespace.activeNodeNets.clear();
        var level = new Level();
        var shredder = machine(level, 0, 2);
        shredder.slots.set(0, new ItemStack(ORE));
        var burner = new MachineWoodBurnerBlockEntity(new BlockPos(4, 0, 0), new BlockState());
        level.put(burner);
        var output = burner.getPowerConPos()[0];
        CableBaseBlockEntity middle = null;
        for (int x = 1; x <= 4; x++) {
            var cable = new CableBaseBlockEntity(new BlockPos(x, 0, 2), new BlockState());
            level.put(cable);
            cable.updateEntity();
            if (x == 2) middle = cable;
        }
        var server = new MinecraftServer(List.of(level));
        UniNodespace.updateNodespace(server);
        UniNodespace.updateNodespace(server);
        check(output.getX() == 4 && output.getZ() == 2, "production burner port is wired");
        burner.slots.set(MachineWoodBurnerBlockEntity.SLOT_FUEL, new ItemStack(Items.OAK_LOG));
        burner.isOn = true;
        for (int tick = 0; tick < 110 && !shredder.slots.get(0).isEmpty(); tick++) {
            if (tick == 20) {
                middle.setRemoved();
                UniNodespace.updateNodespace(server);
                UniNodespace.updateNodespace(server);
            }
            if (tick == 25) {
                check(shredder.progress > 20, "stored HE keeps isolated shredder processing briefly");
                shredder.setPower(0);
            }
            if (tick == 30) {
                check(shredder.progress == 0, "isolated empty receiver resets progress");
                var replacement = new CableBaseBlockEntity(new BlockPos(2, 0, 2), new BlockState());
                level.put(replacement);
                replacement.updateEntity();
                UniNodespace.updateNodespace(server);
                UniNodespace.updateNodespace(server);
            }
            burner.updateEntity();
            shredder.updateEntity();
            UniNodespace.updateNodespace(server);
        }
        check(shredder.slots.get(0).isEmpty() && shredder.slots.get(9).is(DUST)
                && shredder.slots.get(9).getCount() == 2,
                "actual burner, cable, power net and shredder produce two dust");
        check(burner.power >= 0 && shredder.power >= 0, "integrated storage remains nonnegative");
        System.out.println("burner to cable to network to shredder production: passed");
    }

    private static void menuTransfer() {
        var level = new Level();
        var be = machine(level, 0, 0);
        var player = new Player();
        player.level = level;
        var inventory = new Inventory();
        inventory.player = player;
        var menu = new MachineShredderMenu(1, inventory, be);
        check(menu.slots.size() == 66, "real menu registers 30 machine and 36 player slots");
        check(!menu.slots.get(9).mayPlace(new ItemStack(ORE)), "real take-only output slot denies insertion");
        check(menu.slots.get(0).mayPlace(new ItemStack(ORE)), "real input slot delegates placement");
        inventory.items.set(9, new ItemStack(ORE, 3));
        var moved = menu.quickMoveStack(player, 30);
        check(moved.getCount() == 3 && inventory.items.get(9).isEmpty() && be.slots.get(0).getCount() == 3,
                "actual menu quickMoveStack routes regular input through modeled merge engine");
        inventory.items.set(10, new ItemStack(NtmItems.BLADES_STEEL.get()));
        menu.quickMoveStack(player, 31);
        check(be.slots.get(27).is(NtmItems.BLADES_STEEL.get()), "real shift action routes blade to blade slot");
        inventory.items.set(11, new ItemStack(new Battery()));
        menu.quickMoveStack(player, 32);
        check(be.slots.get(29).getItem() instanceof IBatteryItem, "real shift action routes battery to battery slot");
        be.slots.set(9, new ItemStack(DUST, 2));
        menu.quickMoveStack(player, 9);
        check(be.slots.get(9).isEmpty() && inventory.items.stream().anyMatch(s -> s.is(DUST) && s.getCount() == 2),
                "real shift action extracts output into player inventory");
        inventory.items.set(12, new ItemStack(FORBIDDEN));
        check(menu.quickMoveStack(player, 33).isEmpty() && inventory.items.get(12).getCount() == 1,
                "forbidden recipe result cannot enter by shift action");
        be.slots.set(1, new ItemStack(FORBIDDEN, 2));
        check(menu.quickMoveStack(player, 33).isEmpty() && be.slots.get(1).getCount() == 2,
                "forbidden result cannot merge into an existing prohibited input");
        check(menu.quickMoveStack(player, -1).isEmpty() && menu.quickMoveStack(player, 66).isEmpty(),
                "invalid menu indexes safely rejected");
        System.out.println("production menu and slot shift actions: passed");
    }

    public static void main(String[] args) {
        output(ORE, DUST, 2);
        progressAndBlades();
        powerAndReset();
        capacityAndComponents();
        persistenceAndSidedSlots();
        statusAndEnergyMutation();
        menuTransfer();
        networkProduction();
        System.out.println("shredder assertions: " + checks);
    }
}
