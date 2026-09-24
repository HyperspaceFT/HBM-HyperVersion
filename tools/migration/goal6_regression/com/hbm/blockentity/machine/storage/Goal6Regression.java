package com.hbm.blockentity.machine.storage;

import api.hbm.energymk2.IEnergyProviderMK2;
import api.hbm.energymk2.IEnergyReceiverMK2.ConnectionPriority;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.Goal6MachineAccess;
import com.hbm.blockentity.machine.MachineFurnaceCombinationBlockEntity;
import com.hbm.blockentity.machine.MachineShredderBlockEntity;
import com.hbm.blockentity.machine.MachineWoodBurnerBlockEntity;
import com.hbm.blockentity.machine.heater.HeaterFireboxBlockEntity;
import com.hbm.blockentity.network.CableBaseBlockEntity;
import com.hbm.handler.pollution.PollutionHandler;
import com.hbm.interfaces.IControlReceiver;
import com.hbm.inventory.FluidContainerRegistry;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.menus.BatterySocketMenu;
import com.hbm.inventory.menus.MachineWoodBurnerMenu;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.BatteryPackItem;
import com.hbm.items.machine.BatteryPackItem.BatteryPackType;
import com.hbm.items.machine.FluidIDMultiItem;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.TagsUtil;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;

import java.util.List;

public class Goal6Regression {
    private static int checks;
    private static final BatteryPackItem PACK = new BatteryPackItem(new Item.Properties());

    private static void check(boolean condition, String message) {
        checks++;
        if(!condition) throw new AssertionError(message);
    }

    /** Synthetic provider for exact rate and priority cases; the integrated chain uses the production wood burner. */
    static class Supply extends BlockEntity implements IEnergyProviderMK2 {
        long power;
        long used;

        Supply(BlockPos pos, long power) {
            super(null, pos, new BlockState());
            this.power = power;
        }

        @Override public boolean isLoaded() { return !isRemoved(); }
        @Override public long getPower() { return power; }
        @Override public void setPower(long value) { used += power - value; power = value; }
        @Override public long getMaxPower() { return 10_000_000L; }
    }

    static void reset() {
        UniNodespace.levels.clear();
        UniNodespace.activeNodeNets.clear();
        PollutionHandler.reset();
    }

    static Level level() {
        Level level = new Level();
        level.manualClock = true;
        return level;
    }

    static void net(Level level) {
        // Two passes let links that were invalidated in the first pass rejoin, as in the Goal 3B harness.
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
    }

    static void transfer(Level level) {
        UniNodespace.updateNodespace(new MinecraftServer(List.of(level)));
    }

    static ItemStack pack(BatteryPackType type, long charge) {
        ItemStack stack = MetaHelper.newStack(PACK, 1, type.ordinal());
        PACK.setCharge(stack, charge);
        return stack;
    }

    static BatterySocketBlockEntity socket(Level level, BlockPos pos, Direction facing) {
        BlockState state = new BlockState();
        state.facing = facing;
        level.states.put(pos, state);
        BatterySocketBlockEntity socket = new BatterySocketBlockEntity(pos, state);
        level.put(socket);
        BlockPos[] ports = socket.getPortPos();
        for(int i = 1; i < ports.length; i++) {
            // MachineBatterySocketBlock creates EXTRA parts as inventory/power/conductor proxies.
            ProxyComboBlockEntity proxy = new ProxyComboBlockEntity(ports[i], state).inventory().power().conductor();
            proxy.core = socket;
            level.states.put(ports[i], state);
            level.put(proxy);
        }
        return socket;
    }

    static CableBaseBlockEntity cable(Level level, int x, int z) {
        CableBaseBlockEntity wire = new CableBaseBlockEntity(new BlockPos(x, 0, z), new BlockState());
        level.put(wire);
        wire.updateEntity();
        return wire;
    }

    static MachineShredderBlockEntity shredder(Level level, BlockPos pos) {
        MachineShredderBlockEntity shredder = new MachineShredderBlockEntity(pos, new BlockState());
        level.put(shredder);
        shredder.slots.set(27, new ItemStack(NtmItems.BLADES_STEEL.get()));
        shredder.slots.set(28, new ItemStack(NtmItems.BLADES_STEEL.get()));
        shredder.slots.set(0, new ItemStack(Items.IRON_INGOT, 64));
        return shredder;
    }

    static MachineWoodBurnerBlockEntity burner(Level level, BlockPos pos, Direction facing) {
        BlockState state = new BlockState();
        state.facing = facing;
        level.states.put(pos, state);
        MachineWoodBurnerBlockEntity burner = new MachineWoodBurnerBlockEntity(pos, state);
        level.put(burner);
        return burner;
    }

    static CompoundTag flag(String key) {
        CompoundTag tag = new CompoundTag();
        tag.putBoolean(key, true);
        return tag;
    }

    /** Mirrors the server side of CompoundTagControl: look up the target, then hasPermission gates receiveControl. */
    static boolean control(Player player, Level level, BlockPos pos, CompoundTag tag) {
        if(level.getBlockEntity(pos) instanceof IControlReceiver receiver && receiver.hasPermission(player)) {
            receiver.receiveControl(tag);
            return true;
        }
        return false;
    }

    static Player player(Level level) {
        Player player = new Player();
        player.world = level;
        player.getInventory().player = player;
        return player;
    }

    static void packs() {
        check(BatteryPackType.BATTERY_REDSTONE.capacity == 1_800_000L
                && BatteryPackType.BATTERY_REDSTONE.chargeRate == 1_000L
                && BatteryPackType.BATTERY_REDSTONE.dischargeRate == 100L,
                "redstone battery keeps upstream 1.8M HE, 1000 HE/t charge and 100 HE/t discharge");
        check(BatteryPackType.CAPACITOR_COPPER.capacity == 600_000L
                && BatteryPackType.CAPACITOR_COPPER.chargeRate == 1_000L
                && BatteryPackType.CAPACITOR_COPPER.dischargeRate == 1_000L,
                "copper capacitor keeps upstream 600k HE and 1000 HE/t both ways");
        check(BatteryPackType.BATTERY_REDSTONE.ordinal() == 0 && BatteryPackType.CAPACITOR_COPPER.ordinal() == 6,
                "recipe META ordinals stay 0 and 6");

        ItemStack red = MetaHelper.newStack(PACK, 1, BatteryPackType.BATTERY_REDSTONE.ordinal());
        ItemStack copper = MetaHelper.newStack(PACK, 1, BatteryPackType.CAPACITOR_COPPER.ordinal());
        check(red.getMaxStackSize() == 1, "battery packs stack to one");
        check(PACK.getMaxCharge(red) == 1_800_000L && PACK.getDischargeRate(red) == 100L
                && PACK.getMaxCharge(copper) == 600_000L && PACK.getDischargeRate(copper) == 1_000L,
                "item META selects the pack type");
        check(!TagsUtil.hasCustomData(red) && PACK.getCharge(red) == 0 && TagsUtil.hasCustomData(red),
                "a freshly crafted pack is empty and its first charge read writes Charge 0 like upstream");
        PACK.chargeBattery(red, 500);
        PACK.dischargeBattery(red, 200);
        check(PACK.getCharge(red) == 300 && TagsUtil.getCustomData(red).getLong("Charge") == 300,
                "charge lives in CUSTOM_DATA Charge");
    }

    static void socketRatesAndModes() {
        reset();
        Level level = level();
        Player player = player(level);
        BatterySocketBlockEntity socket = socket(level, new BlockPos(0, 0, 0), Direction.NORTH);
        player.containerMenu = new BatterySocketMenu(0, player.getInventory(), socket);

        int dirty = socket.dirty;
        socket.setPower(5);
        check(socket.getPower() == 0 && socket.getMaxPower() == 0 && socket.getReceiverSpeed() == 0
                && socket.getProviderSpeed() == 0 && socket.dirty == dirty,
                "an empty socket has no storage, speed or dirty write");

        socket.slots.set(0, pack(BatteryPackType.BATTERY_REDSTONE, 0));
        socket.updateEntity();
        // BatteryBase refreshes its cached mode only while its node has a net, which the first nodespace pass creates.
        net(level);
        socket.updateEntity();
        check(socket.getRelevantMode(true) == BatteryBaseBlockEntity.mode_input
                && socket.getReceiverSpeed() == 1_000L && socket.getProviderSpeed() == 0,
                "default unpowered mode is input at the pack charge rate");
        check(socket.getMaxPower() == 1_800_000L && socket.priority == ConnectionPriority.LOW,
                "socket exposes pack capacity and LOW default priority");

        socket.setPower(1_800_000L - 400);
        check(socket.transferPower(1_000) == 600 && socket.getPower() == 1_800_000L,
                "receiving past capacity returns the exact overshoot");
        check(socket.transferPower(1) == 1 && socket.getPower() == 1_800_000L, "a full pack accepts nothing");

        level.powered.add(socket.getPortPos()[3]);
        socket.updateEntity();
        check(socket.getRelevantMode(true) == BatteryBaseBlockEntity.mode_output
                && socket.getProviderSpeed() == 100L && socket.getReceiverSpeed() == 0,
                "redstone at any port selects the redstone-high output mode");
        level.powered.clear();
        socket.updateEntity();
        check(socket.getRelevantMode(true) == BatteryBaseBlockEntity.mode_input, "removing redstone returns to input");

        int[] expectedLow = { BatteryBaseBlockEntity.mode_buffer, BatteryBaseBlockEntity.mode_output,
                BatteryBaseBlockEntity.mode_none, BatteryBaseBlockEntity.mode_input };
        long[][] speeds = { { 1_000L, 100L }, { 0, 100L }, { 0, 0 }, { 1_000L, 0 } };
        for(int i = 0; i < expectedLow.length; i++) {
            dirty = socket.dirty;
            check(control(player, level, socket.getBlockPos(), flag("low")), "menu owner can cycle redstone-low mode");
            socket.updateEntity();
            check(socket.redLow == expectedLow[i] && socket.getRelevantMode(true) == expectedLow[i]
                    && socket.getReceiverSpeed() == speeds[i][0] && socket.getProviderSpeed() == speeds[i][1],
                    "redstone-low cycle step " + i + " exposes the matching receiver/provider speeds");
            check(socket.dirty > dirty, "mode change marks the socket for saving");
        }
        int[] expectedHigh = { BatteryBaseBlockEntity.mode_none, BatteryBaseBlockEntity.mode_input,
                BatteryBaseBlockEntity.mode_buffer, BatteryBaseBlockEntity.mode_output };
        for(int mode : expectedHigh) {
            check(control(player, level, socket.getBlockPos(), flag("high")) && socket.redHigh == mode,
                    "redstone-high cycles 2 -> 3 -> 0 -> 1 -> 2");
        }
        ConnectionPriority[] priorities = { ConnectionPriority.NORMAL, ConnectionPriority.HIGH, ConnectionPriority.LOW };
        for(ConnectionPriority priority : priorities) {
            dirty = socket.dirty;
            check(control(player, level, socket.getBlockPos(), flag("priority")) && socket.priority == priority
                    && socket.dirty > dirty, "priority cycles LOW -> NORMAL -> HIGH -> LOW and saves");
        }
        dirty = socket.dirty;
        socket.receiveControl(new CompoundTag());
        check(socket.dirty == dirty, "an empty control packet changes nothing");

        socket.slots.set(0, pack(BatteryPackType.CAPACITOR_COPPER, 0));
        level.powered.add(socket.getBlockPos());
        socket.updateEntity();
        check(socket.getProviderSpeed() == 1_000L && socket.getMaxPower() == 600_000L,
                "copper capacitor discharges at 1000 HE/t in output mode");
        level.powered.clear();
        System.out.println("socket rates, capacity and modes: passed");
    }

    static void automationExtraction() {
        reset();
        Level level = level();
        BatterySocketBlockEntity socket = socket(level, new BlockPos(0, 0, 0), Direction.EAST);
        ProxyComboBlockEntity proxy = (ProxyComboBlockEntity) level.getBlockEntity(socket.getPortPos()[1]);
        ItemStack empty = pack(BatteryPackType.BATTERY_REDSTONE, 0);
        ItemStack partial = pack(BatteryPackType.BATTERY_REDSTONE, 1_000);
        ItemStack full = pack(BatteryPackType.BATTERY_REDSTONE, 1_800_000L);

        socket.slots.set(0, partial);
        check(!socket.canTakeItemThroughFace(0, partial, Direction.UP) && socket.canTakeItemThroughFace(0, full, Direction.UP)
                && !socket.canTakeItemThroughFace(0, empty, Direction.UP),
                "input mode releases only a full pack to automation");
        level.powered.add(socket.getBlockPos());
        check(socket.canTakeItemThroughFace(0, empty, Direction.UP) && !socket.canTakeItemThroughFace(0, partial, Direction.UP)
                && !socket.canTakeItemThroughFace(0, full, Direction.UP),
                "output mode releases only an empty pack to automation");
        check(proxy.canTakeItemThroughFace(0, empty, Direction.UP) && !proxy.canTakeItemThroughFace(0, partial, Direction.UP),
                "EXTRA inventory proxies apply the same extraction rule");
        socket.redHigh = BatteryBaseBlockEntity.mode_buffer;
        check(!socket.canTakeItemThroughFace(0, empty, Direction.UP) && !socket.canTakeItemThroughFace(0, full, Direction.UP),
                "buffer mode keeps packs in place");
        socket.redHigh = BatteryBaseBlockEntity.mode_none;
        check(!socket.canTakeItemThroughFace(0, empty, Direction.UP), "disabled mode keeps packs in place");
        check(!socket.canTakeItemThroughFace(0, new ItemStack(Items.IRON_INGOT), Direction.UP)
                && !socket.canPlaceItem(0, new ItemStack(Items.IRON_INGOT)) && socket.canPlaceItem(0, empty),
                "only battery items are accepted or released");
        System.out.println("automation extraction by mode: passed");
    }

    static void networkRoles() {
        reset();
        Level level = level();
        BatterySocketBlockEntity socket = socket(level, new BlockPos(0, 0, 0), Direction.NORTH);
        socket.slots.set(0, pack(BatteryPackType.BATTERY_REDSTONE, 50_000));
        CableBaseBlockEntity north = cable(level, 0, -1);
        CableBaseBlockEntity south = cable(level, 1, 2);
        CableBaseBlockEntity east = cable(level, 2, 1);
        socket.updateEntity();
        net(level);
        socket.updateEntity();
        check(socket.node.hasValidNet() && north.node.net == socket.node.net && south.node.net == socket.node.net
                && east.node.net == socket.node.net, "socket ports join cables from several sides into one net");

        var net = socket.node.net;
        check(net.receiverEntries.containsKey(socket) && !net.providerEntries.containsKey(socket), "input mode is receiver only");
        socket.redLow = BatteryBaseBlockEntity.mode_output;
        socket.updateEntity();
        check(!net.receiverEntries.containsKey(socket) && net.providerEntries.containsKey(socket), "output mode is provider only");
        socket.redLow = BatteryBaseBlockEntity.mode_buffer;
        socket.updateEntity();
        check(net.receiverEntries.containsKey(socket) && net.providerEntries.containsKey(socket), "buffer mode is both");
        socket.redLow = BatteryBaseBlockEntity.mode_none;
        socket.updateEntity();
        check(!net.receiverEntries.containsKey(socket) && !net.providerEntries.containsKey(socket), "disabled mode takes no role");

        Supply supply = new Supply(new BlockPos(0, 0, -2), 1_000);
        level.put(supply);
        MachineShredderBlockEntity shredder = new MachineShredderBlockEntity(new BlockPos(1, 0, 3), new BlockState());
        level.put(shredder);
        supply.tryProvide(level, north.getBlockPos(), Direction.SOUTH);
        shredder.updateEntity();
        transfer(level);
        check(shredder.power == 1_000 && supply.power == 0 && socket.getPower() == 50_000,
                "a disabled socket still conducts energy between its ports without storing it");
        System.out.println("socket network roles and conduction: passed");
    }

    static void chargeDischargeAndPriority() {
        reset();
        Level level = level();
        BatterySocketBlockEntity socket = socket(level, new BlockPos(0, 0, 0), Direction.NORTH);
        socket.slots.set(0, pack(BatteryPackType.BATTERY_REDSTONE, 0));
        CableBaseBlockEntity north = cable(level, 0, -1);
        cable(level, 0, 2);
        cable(level, 0, 3);
        Supply supply = new Supply(new BlockPos(0, 0, -2), 5_000);
        level.put(supply);
        MachineShredderBlockEntity shredder = new MachineShredderBlockEntity(new BlockPos(0, 0, 4), new BlockState());
        level.put(shredder);
        socket.updateEntity();
        net(level);

        // Two priority levels: the NORMAL receiver is served before the LOW socket.
        shredder.setPower(9_000);
        socket.updateEntity();
        shredder.updateEntity();
        supply.power = 1_500;
        supply.tryProvide(level, north.getBlockPos(), Direction.SOUTH);
        transfer(level);
        check(shredder.power == 10_000 && socket.getPower() == 500 && supply.power == 0,
                "NORMAL receiver fills first, LOW socket takes the remaining 500 HE");

        supply.power = 5_000;
        int dirty = socket.dirty;
        socket.updateEntity();
        shredder.updateEntity();
        supply.tryProvide(level, north.getBlockPos(), Direction.SOUTH);
        transfer(level);
        check(socket.getPower() == 1_500 && supply.power == 4_000 && socket.dirty > dirty,
                "input is limited to 1000 HE/t and network charging marks the socket dirty");

        socket.setPower(1_800_000L - 300);
        socket.updateEntity();
        supply.tryProvide(level, north.getBlockPos(), Direction.SOUTH);
        transfer(level);
        check(socket.getPower() == 1_800_000L && supply.power == 3_700, "the last 300 HE fill the pack exactly");
        dirty = socket.dirty;
        socket.updateEntity();
        supply.tryProvide(level, north.getBlockPos(), Direction.SOUTH);
        transfer(level);
        check(supply.power == 3_700 && socket.dirty == dirty, "a full pack takes no energy and causes no save churn");

        // Discharge to the shredder at the pack rate.
        level.powered.add(socket.getBlockPos());
        shredder.setPower(0);
        supply.setRemoved();
        socket.updateEntity();
        shredder.updateEntity();
        transfer(level);
        check(shredder.power == 100 && socket.getPower() == 1_800_000L - 100,
                "redstone battery output is limited to 100 HE/t");
        socket.slots.set(0, pack(BatteryPackType.CAPACITOR_COPPER, 600_000));
        socket.updateEntity();
        shredder.updateEntity();
        transfer(level);
        check(shredder.power == 1_100 && socket.getPower() == 599_000, "copper capacitor output is 1000 HE/t");
        socket.slots.set(0, pack(BatteryPackType.CAPACITOR_COPPER, 0));
        socket.updateEntity();
        shredder.updateEntity();
        transfer(level);
        check(shredder.power == 1_100 && socket.getPower() == 0, "an empty pack provides nothing");
        level.powered.clear();
        System.out.println("charge/discharge limits and two-level priority: passed");
    }

    static void threePriorityCharacterization() {
        reset();
        Level level = level();
        BatterySocketBlockEntity low = socket(level, new BlockPos(0, 0, 0), Direction.NORTH);
        BatterySocketBlockEntity high = socket(level, new BlockPos(0, 0, 10), Direction.NORTH);
        low.slots.set(0, pack(BatteryPackType.BATTERY_REDSTONE, 0));
        high.slots.set(0, pack(BatteryPackType.BATTERY_REDSTONE, 0));
        high.priority = ConnectionPriority.HIGH;
        CableBaseBlockEntity north = cable(level, 0, -1);
        for(int z = 2; z <= 9; z++) cable(level, 0, z);
        MachineShredderBlockEntity shredder = new MachineShredderBlockEntity(new BlockPos(1, 0, 5), new BlockState());
        level.put(shredder);
        Supply supply = new Supply(new BlockPos(0, 0, -2), 5_000);
        level.put(supply);
        low.updateEntity();
        high.updateEntity();
        net(level);
        low.updateEntity();
        high.updateEntity();
        shredder.setPower(8_000);
        shredder.updateEntity();
        supply.tryProvide(level, north.getBlockPos(), Direction.SOUTH);
        check(low.node.net == high.node.net && low.node.net.receiverEntries.size() == 3,
                "HIGH socket, NORMAL shredder and LOW socket share one net");
        transfer(level);
        long delivered = high.getPower() + (shredder.power - 8_000) + low.getPower();
        check(high.getPower() == 1_000 && shredder.power == 10_000 && supply.used == delivered,
                "three-priority case conserves energy");
        // Upstream PowerNetMK2 subtracts cumulative energyUsed after each priority; the LOW socket is shorted here.
        check(low.getPower() == 0 && supply.power == 2_000,
                "known upstream multi-priority shortfall: LOW receives 0 of the remaining 1000 HE");
        System.out.println("three-priority PowerNet characterization: passed");
    }

    static void unloadRemovalAndReload() {
        reset();
        Level level = level();
        BatterySocketBlockEntity socket = socket(level, new BlockPos(0, 0, 0), Direction.NORTH);
        socket.slots.set(0, pack(BatteryPackType.BATTERY_REDSTONE, 7_000));
        socket.redLow = 1;
        socket.priority = ConnectionPriority.NORMAL;
        CableBaseBlockEntity north = cable(level, 0, -1);
        CableBaseBlockEntity south = cable(level, 0, 2);
        Supply supply = new Supply(new BlockPos(0, 0, -2), 5_000);
        level.put(supply);
        socket.updateEntity();
        net(level);
        socket.updateEntity();

        socket.isLoaded = false;
        supply.tryProvide(level, north.getBlockPos(), Direction.SOUTH);
        transfer(level);
        check(!socket.node.net.receiverEntries.containsKey(socket) && socket.getPower() == 7_000 && supply.power == 5_000,
                "an unloaded socket is pruned and receives nothing");
        socket.isLoaded = true;
        socket.redLow = BatteryBaseBlockEntity.mode_input;
        socket.updateEntity();
        supply.tryProvide(level, north.getBlockPos(), Direction.SOUTH);
        transfer(level);
        check(socket.getPower() == 8_000 && supply.power == 4_000, "reloaded socket rejoins as receiver");

        CompoundTag saved = new CompoundTag();
        socket.redLow = BatteryBaseBlockEntity.mode_buffer;
        socket.redHigh = BatteryBaseBlockEntity.mode_none;
        socket.saveAdditional(saved, null);
        socket.setRemoved();
        level.entities.remove(socket.getBlockPos());
        net(level);
        check(socket.node.expired && north.node.net != south.node.net,
                "removing the socket destroys its node and splits the cables it bridged");

        BatterySocketBlockEntity reloaded = new BatterySocketBlockEntity(socket.getBlockPos(), level.getBlockState(socket.getBlockPos()));
        level.put(reloaded);
        reloaded.loadAdditional(saved, null);
        check(reloaded.getPower() == 8_000 && MetaHelper.getMeta(reloaded.slots.get(0)) == BatteryPackType.BATTERY_REDSTONE.ordinal()
                && reloaded.redLow == BatteryBaseBlockEntity.mode_buffer && reloaded.redHigh == BatteryBaseBlockEntity.mode_none
                && reloaded.priority == ConnectionPriority.NORMAL,
                "save/load keeps pack META, Charge, both modes and priority");
        reloaded.updateEntity();
        net(level);
        reloaded.updateEntity();
        check(reloaded.node != socket.node && north.node.net == south.node.net && north.node.net == reloaded.node.net
                && reloaded.node.net.providerEntries.containsKey(reloaded) && reloaded.node.net.receiverEntries.containsKey(reloaded),
                "a reloaded buffer socket creates a new node, rejoins both cable branches and takes both roles");
        // Buffer mode also offers energy to itself; use input mode for an exact charging amount.
        reloaded.redLow = BatteryBaseBlockEntity.mode_input;
        reloaded.updateEntity();
        supply.tryProvide(level, north.getBlockPos(), Direction.SOUTH);
        transfer(level);
        check(reloaded.getPower() == 9_000 && supply.power == 3_000, "reloaded socket resumes charging");

        RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf();
        reloaded.serialize(buf);
        BatterySocketBlockEntity client = new BatterySocketBlockEntity(new BlockPos(9, 9, 9), new BlockState());
        client.deserialize(buf);
        check(client.syncPower == 9_000 && client.syncMaxPower == 1_800_000L && client.redLow == BatteryBaseBlockEntity.mode_input
                && client.priority == ConnectionPriority.NORMAL && client.syncStack.getItem() == PACK
                && MetaHelper.getMeta(client.syncStack) == 0, "GUI sync packet carries charge, capacity, modes and pack identity");

        ItemStack removed = reloaded.removeItemNoUpdate(0);
        check(PACK.getCharge(removed) == 9_000 && reloaded.getPower() == 0,
                "taking the pack out keeps its charge in the item stack used by container drops");
        System.out.println("unload, removal, save/load and sync: passed");
    }

    static void menuAndPermission() {
        reset();
        Level level = level();
        BatterySocketBlockEntity socket = socket(level, new BlockPos(0, 0, 0), Direction.NORTH);
        BatterySocketBlockEntity other = socket(level, new BlockPos(10, 0, 0), Direction.NORTH);
        Player player = player(level);
        BatterySocketMenu menu = new BatterySocketMenu(0, player.getInventory(), socket);

        ItemStack charged = pack(BatteryPackType.CAPACITOR_COPPER, 12_345);
        check(menu.slots.get(0).mayPlace(charged) && !menu.slots.get(0).mayPlace(new ItemStack(Items.IRON_INGOT)),
                "socket slot accepts only battery items");
        player.getInventory().setItem(0, charged);
        player.getInventory().setItem(1, new ItemStack(Items.IRON_INGOT, 3));
        int dirty = socket.dirty;
        menu.quickMoveStack(player, 28);
        check(PACK.getCharge(socket.slots.get(0)) == 12_345 && MetaHelper.getMeta(socket.slots.get(0)) == 6
                && player.getInventory().getItem(0).isEmpty() && socket.dirty > dirty,
                "Shift moves a pack into the socket with its META and charge");
        menu.quickMoveStack(player, 29);
        check(player.getInventory().getItem(1).getCount() == 3 && PACK.getCharge(socket.slots.get(0)) == 12_345,
                "Shift does not insert non-battery items");
        player.getInventory().setItem(2, pack(BatteryPackType.BATTERY_REDSTONE, 1));
        menu.quickMoveStack(player, 30);
        check(player.getInventory().getItem(2).getCount() == 1 && MetaHelper.getMeta(socket.slots.get(0)) == 6,
                "an occupied single-pack slot refuses a second pack");
        menu.quickMoveStack(player, 0);
        check(socket.slots.get(0).isEmpty() && PACK.getCharge(player.getInventory().getItem(8)) == 12_345,
                "Shift out returns the same charged pack to the player");

        CompoundTag low = flag("low");
        check(!control(player, level, socket.getBlockPos(), low) && socket.redLow == 0, "no open menu: control rejected");
        player.containerMenu = new BatterySocketMenu(0, player.getInventory(), other);
        check(!control(player, level, socket.getBlockPos(), low), "a different socket's menu is rejected");
        player.containerMenu = menu;
        player.world = level();
        check(!control(player, level, socket.getBlockPos(), low), "a player in another level is rejected");
        player.world = level;
        player.inReach = false;
        check(!control(player, level, socket.getBlockPos(), low) && !menu.stillValid(player), "out-of-reach player is rejected");
        player.inReach = true;
        level.isClientSide = true;
        check(!socket.hasPermission(player), "client-side instances never accept control");
        level.isClientSide = false;
        check(control(player, level, socket.getBlockPos(), low) && socket.redLow == 1, "the open menu owner is accepted");
        level.entities.remove(socket.getBlockPos());
        check(!socket.hasPermission(player), "a removed socket no longer accepts control");
        System.out.println("menu admission, Shift and permission: passed");
    }

    static void proxyDirectProvision() {
        reset();
        Level level = level();
        // A north-facing burner at (4,0,0) samples (4,0,2) and (5,0,2); (4,0,2) is this socket's EXTRA proxy.
        BatterySocketBlockEntity socket = socket(level, new BlockPos(3, 0, 2), Direction.NORTH);
        check(level.getBlockEntity(new BlockPos(4, 0, 2)) instanceof ProxyComboBlockEntity, "burner output touches a socket proxy");
        socket.slots.set(0, pack(BatteryPackType.BATTERY_REDSTONE, 0));
        socket.redLow = BatteryBaseBlockEntity.mode_none;
        MachineWoodBurnerBlockEntity burner = burner(level, new BlockPos(4, 0, 0), Direction.NORTH);
        burner.power = 1_000;
        socket.updateEntity();
        net(level);
        socket.updateEntity();
        level.time++;
        burner.updateEntity();
        check(socket.getPower() == 0 && burner.power == 1_000,
                "EXTRA proxy does not bypass a disabled socket through direct provision");
        check(socket.node.net.providerEntries.containsKey(burner), "the proxy still exposes the socket node to providers");
        transfer(level);
        check(socket.getPower() == 0 && burner.power == 1_000, "a disabled socket stores nothing from the network");
        socket.redLow = BatteryBaseBlockEntity.mode_input;
        socket.updateEntity();
        level.time++;
        burner.updateEntity();
        transfer(level);
        check(socket.getPower() == 1_000 && burner.power == 0, "input mode charges through the network at the proxy");
        System.out.println("proxy direct provision parity: passed");
    }

    static void liquidBurn() {
        reset();
        Level level = level();
        MachineWoodBurnerBlockEntity burner = burner(level, new BlockPos(0, 0, 0), Direction.NORTH);
        Player player = player(level);
        check(!control(player, level, burner.getBlockPos(), flag("switch")) && !burner.liquidBurn,
                "burner controls require its open menu");
        player.containerMenu = new MachineWoodBurnerMenu(0, player.getInventory(), burner);
        check(control(player, level, burner.getBlockPos(), flag("switch")) && burner.liquidBurn, "switch selects liquid mode");

        burner.tank.setTankType(Fluids.COALCREOSOTE);
        burner.tank.setFill(1_000);
        level.time = 1;
        burner.updateEntity();
        check(burner.tank.getFill() == 1_000 && burner.powerGen == 0 && burner.power == 0, "switched off: no fuel is burned");
        check(control(player, level, burner.getBlockPos(), flag("toggle")) && burner.isOn, "toggle switches the burner on");
        level.time = 2;
        burner.updateEntity();
        check(burner.tank.getFill() == 998 && burner.powerGen == 250 && burner.power == 250,
                "creosote burns 2 mB/t for 250 HE/t");

        burner.power = 0;
        burner.tank.setFill(1_000);
        PollutionHandler.reset();
        long generated = 0;
        int ticks = 0;
        while(burner.tank.getFill() > 0 && ticks < 1_000) {
            level.time++;
            burner.updateEntity();
            generated += burner.powerGen;
            burner.power = 0;
            ticks++;
        }
        check(ticks == 500 && generated == 125_000L, "1000 mB creosote lasts 500 ticks and yields 125,000 HE");
        check(PollutionHandler.calls == 25 && Math.abs(PollutionHandler.soot - 25 * PollutionHandler.SOOT_PER_SECOND) < 1e-6,
                "liquid burning emits soot once per second at the solid-fuel rate");

        burner.tank.setFill(1);
        level.time = 40;
        PollutionHandler.reset();
        burner.updateEntity();
        check(burner.tank.getFill() == 0 && burner.powerGen == 125 && burner.power == 125
                && Math.abs(PollutionHandler.soot - PollutionHandler.SOOT_PER_SECOND / 2F) < 1e-7,
                "the last 1 mB gives 125 HE and half the soot");
        level.time++;
        burner.updateEntity();
        check(burner.powerGen == 0 && burner.power == 125, "an empty tank produces nothing");

        burner.tank.setFill(1_000);
        burner.power = MachineWoodBurnerBlockEntity.MAX_POWER;
        level.time++;
        burner.updateEntity();
        check(burner.tank.getFill() == 1_000 && burner.powerGen == 0, "a full buffer stops fuel use");
        burner.power = MachineWoodBurnerBlockEntity.MAX_POWER - 100;
        level.time++;
        burner.updateEntity();
        check(burner.tank.getFill() == 998 && burner.power == MachineWoodBurnerBlockEntity.MAX_POWER,
                "near-full buffer burns one step and clamps at 100,000 HE like upstream");

        burner.power = 0;
        burner.tank.setTankType(Fluids.WOODOIL);
        burner.tank.setFill(1_000);
        level.time++;
        burner.updateEntity();
        check(burner.powerGen == 110 && burner.tank.getFill() == 998, "wood oil keeps its own 110,000 heat per 1000 mB (110 HE/t)");
        burner.tank.setTankType(Fluids.WATER);
        burner.tank.setFill(1_000);
        level.time++;
        burner.updateEntity();
        check(burner.powerGen == 0 && burner.tank.getFill() == 1_000, "non-flammable fluid is not burned");

        burner.tank.setTankType(Fluids.COALCREOSOTE);
        burner.tank.setFill(0);
        burner.slots.set(MachineWoodBurnerBlockEntity.SLOT_FUEL, new ItemStack(Items.COAL));
        level.time++;
        burner.updateEntity();
        check(burner.burnTime == 0 && burner.slots.get(MachineWoodBurnerBlockEntity.SLOT_FUEL).getCount() == 1,
                "liquid mode ignores solid fuel");

        burner.tank.setFill(600);
        burner.power = 4_321;
        CompoundTag saved = Goal6MachineAccess.save(burner);
        MachineWoodBurnerBlockEntity copy = burner(level(), new BlockPos(0, 0, 0), Direction.NORTH);
        Goal6MachineAccess.load(copy, saved);
        check(copy.liquidBurn && copy.isOn && copy.tank.getTankType() == Fluids.COALCREOSOTE && copy.tank.getFill() == 600
                && copy.power == 4_321, "save/load keeps liquid mode, switch, fluid and buffer");

        check(control(player, level, burner.getBlockPos(), flag("switch")) && !burner.liquidBurn, "switch returns to solid mode");
        burner.slots.set(MachineWoodBurnerBlockEntity.SLOT_FUEL, ItemStack.EMPTY);
        level.time++;
        burner.updateEntity();
        check(burner.tank.getFill() == 600 && burner.powerGen == 0, "solid mode leaves the fluid tank untouched");
        System.out.println("wood burner liquid boundaries: passed");
    }

    static ItemStack creosoteTankFromCoal(Level level) {
        HeaterFireboxBlockEntity fire = new HeaterFireboxBlockEntity(new BlockPos(20, 0, 20), new BlockState());
        level.put(fire);
        MachineFurnaceCombinationBlockEntity oven = new MachineFurnaceCombinationBlockEntity(new BlockPos(20, 1, 20), new BlockState());
        level.put(oven);
        fire.slots.set(0, new ItemStack(Items.COAL, 8));
        oven.slots.set(0, new ItemStack(Items.COAL, 10));
        int ticks = 0;
        while(oven.slots.get(1).getCount() < 10 && ticks++ < 20_000) {
            level.time++;
            fire.updateEntity();
            oven.updateEntity();
        }
        check(oven.slots.get(1).is(NtmItems.COKE_COAL.get()) && oven.slots.get(1).getCount() == 10
                && oven.tank.getTankType() == Fluids.COALCREOSOTE && oven.tank.getFill() == 1_000,
                "ten coal become ten coke and 1000 mB creosote from a cold firebox");
        oven.slots.set(MachineFurnaceCombinationBlockEntity.SLOT_FLUID_IN, new ItemStack(NtmItems.FLUID_TANK_EMPTY.get()));
        level.time++;
        fire.updateEntity();
        oven.updateEntity();
        ItemStack filled = oven.slots.get(MachineFurnaceCombinationBlockEntity.SLOT_FLUID_OUT);
        check(filled.is(NtmItems.FLUID_TANK_FULL.get()) && MetaHelper.getMeta(filled) == Fluids.COALCREOSOTE.getID()
                && oven.tank.getFill() == 0, "the oven fills one universal tank with the 1000 mB");
        oven.slots.set(MachineFurnaceCombinationBlockEntity.SLOT_FLUID_OUT, ItemStack.EMPTY);
        return filled;
    }

    static void integratedChain() {
        reset();
        Level level = level();
        ItemStack filled = creosoteTankFromCoal(level);

        MachineWoodBurnerBlockEntity burner = burner(level, new BlockPos(0, 0, -4), Direction.NORTH);
        cable(level, 0, -2);
        cable(level, 0, -1);
        BatterySocketBlockEntity socket = socket(level, new BlockPos(0, 0, 0), Direction.NORTH);
        socket.slots.set(0, MetaHelper.newStack(PACK, 1, BatteryPackType.BATTERY_REDSTONE.ordinal()));
        cable(level, 0, 2);
        CableBaseBlockEntity feeder = cable(level, 0, 3);
        MachineShredderBlockEntity shredder = shredder(level, new BlockPos(0, 0, 4));
        socket.updateEntity();
        net(level);

        ItemStack identifier = new ItemStack(NtmItems.FLUID_IDENTIFIER_MULTI.get());
        CompoundTag primary = new CompoundTag();
        primary.putInt("Primary", Fluids.COALCREOSOTE.getID());
        ((FluidIDMultiItem) identifier.getItem()).receiveControl(null, identifier, primary);
        burner.slots.set(MachineWoodBurnerBlockEntity.SLOT_IDENTIFIER, identifier);
        level.time++;
        burner.updateEntity();
        check(burner.tank.getTankType() == Fluids.COALCREOSOTE
                && burner.canPlaceItem(MachineWoodBurnerBlockEntity.SLOT_FLUID_IN, filled),
                "identifier selects creosote and the burner accepts the oven's tank");
        burner.slots.set(MachineWoodBurnerBlockEntity.SLOT_FLUID_IN, filled);
        level.time++;
        burner.updateEntity();
        check(burner.tank.getFill() == 1_000 && burner.slots.get(MachineWoodBurnerBlockEntity.SLOT_FLUID_OUT).is(NtmItems.FLUID_TANK_EMPTY.get()),
                "the burner unloads 1000 mB and returns the empty tank");

        Player player = player(level);
        player.containerMenu = new MachineWoodBurnerMenu(0, player.getInventory(), burner);
        check(control(player, level, burner.getBlockPos(), flag("switch")) && control(player, level, burner.getBlockPos(), flag("toggle"))
                && burner.liquidBurn && burner.isOn, "player selects liquid mode and switches on");

        PollutionHandler.reset();
        long generated = 0;
        long consumed = 0;
        int burnTicks = 0;
        int ticks = 0;
        while(burner.tank.getFill() > 0 && ticks++ < 2_000) {
            level.time++;
            burner.updateEntity();
            generated += burner.powerGen;
            if(burner.powerGen > 0) burnTicks++;
            socket.updateEntity();
            long before = shredder.power;
            shredder.updateEntity();
            consumed += before - shredder.power;
            transfer(level);
            check(burner.power + socket.getPower() + shredder.power + consumed == generated,
                    "every tick conserves generated HE across burner, cable, socket and shredder");
        }
        check(burnTicks == 500 && generated == 125_000L && burner.tank.getFill() == 0,
                "the 1000 mB tank yields exactly 125,000 HE over 500 ticks");
        check(PollutionHandler.calls == 25, "integrated burn emits 25 soot pulses");
        check(consumed > 0 && shredder.slots.get(9).is(NtmItems.DUST.get()), "the shredder ran on network power");
        check(shredder.power == 10_000 && burner.power == 0 && socket.getPower() == generated - consumed - 10_000,
                "NORMAL shredder is kept full; the LOW socket stores the surplus");
        long stored = socket.getPower();
        check(stored > 100_000L, "the socket banked most of the creosote energy");

        // Discharge: redstone on a port selects the default redstone-high output mode.
        level.powered.add(socket.getPortPos()[2]);
        long drained = 0;
        for(int i = 0; i < 100; i++) {
            level.time++;
            burner.updateEntity();
            socket.updateEntity();
            long before = shredder.power;
            shredder.updateEntity();
            drained += before - shredder.power;
            transfer(level);
        }
        check(socket.getPower() == stored - drained && shredder.power == 10_000,
                "without fuel the socket supplies exactly what the running shredder uses");

        feeder.setRemoved();
        level.entities.remove(feeder.getBlockPos());
        long socketBefore = socket.getPower();
        for(int i = 0; i < 40; i++) {
            level.time++;
            socket.updateEntity();
            shredder.updateEntity();
            transfer(level);
        }
        check(socket.getPower() == socketBefore && shredder.power == 10_000 - 200,
                "a removed cable stops supply; the shredder drains its own buffer");

        cable(level, 0, 3);
        net(level);
        long maxStep = 0;
        long used = 0;
        for(int i = 0; i < 5; i++) {
            level.time++;
            socket.updateEntity();
            long charge = socket.getPower();
            long before = shredder.power;
            shredder.updateEntity();
            used += before - shredder.power;
            transfer(level);
            maxStep = Math.max(maxStep, charge - socket.getPower());
        }
        check(maxStep == 100 && shredder.power == 10_000 && socket.getPower() + shredder.power + used == socketBefore + 10_000 - 200,
                "reconnecting resumes discharge at the 100 HE/t pack limit and conserves energy");
        check(TagsUtil.getCustomData(socket.slots.get(0)).getLong("Charge") == socket.getPower(),
                "the socket charge is the pack's own CUSTOM_DATA value");
        System.out.println("integrated coal -> creosote -> HE -> socket -> shredder chain: passed");
    }

    public static void main(String[] args) {
        FluidContainerRegistry.clearRegistry();
        FluidContainerRegistry.register();
        packs();
        System.out.println("battery pack identities and values: passed");
        socketRatesAndModes();
        automationExtraction();
        networkRoles();
        chargeDischargeAndPriority();
        threePriorityCharacterization();
        unloadRemovalAndReload();
        menuAndPermission();
        proxyDirectProvision();
        liquidBurn();
        integratedChain();
        System.out.println("Goal 6 checks: " + checks);
    }
}
