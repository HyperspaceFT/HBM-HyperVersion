package com.hbm.blockentity.machine;

import com.hbm.blockentity.machine.heater.HeaterFireboxBlockEntity;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.menus.HeaterFireboxMenu;
import com.hbm.inventory.menus.MachineFurnaceCombinationMenu;
import com.hbm.inventory.recipes.CombinationRecipes;
import com.hbm.items.NtmItems;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;

import java.lang.reflect.Method;

public class Goal5ARegression {
    private static int checks;

    private static void check(boolean ok, String message) {
        checks++;
        if (!ok) throw new AssertionError(message);
    }

    private static HeaterFireboxBlockEntity firebox(Level level, BlockPos pos) {
        var be = new HeaterFireboxBlockEntity(pos, new BlockState());
        level.put(be);
        return be;
    }

    private static MachineFurnaceCombinationBlockEntity oven(Level level, BlockPos pos) {
        var be = new MachineFurnaceCombinationBlockEntity(pos, new BlockState());
        level.put(be);
        return be;
    }

    private static void save(Object entity, CompoundTag tag) {
        try {
            Class<?> type = entity instanceof HeaterFireboxBlockEntity ? HeaterFireboxBlockEntity.class : MachineFurnaceCombinationBlockEntity.class;
            Method method = type.getDeclaredMethod("saveAdditional", CompoundTag.class, net.minecraft.core.HolderLookup.Provider.class);
            method.setAccessible(true);
            method.invoke(entity, tag, null);
        } catch (ReflectiveOperationException ex) { throw new AssertionError(ex); }
    }

    private static void load(Object entity, CompoundTag tag) {
        try {
            Class<?> type = entity instanceof HeaterFireboxBlockEntity ? HeaterFireboxBlockEntity.class : MachineFurnaceCombinationBlockEntity.class;
            Method method = type.getDeclaredMethod("loadAdditional", CompoundTag.class, net.minecraft.core.HolderLookup.Provider.class);
            method.setAccessible(true);
            method.invoke(entity, tag, null);
        } catch (ReflectiveOperationException ex) { throw new AssertionError(ex); }
    }

    private static void fuel() {
        var level = new Level();
        var be = firebox(level, new BlockPos(0, 0, 0));
        be.slots.set(0, new ItemStack(Items.COAL, 2));
        be.updateEntity();
        check(be.maxBurnTime == 2000 && be.burnTime == 2000 && be.burnHeat == 200,
                "coal starts with 2000 remaining ticks and 200 heat/tick");
        check(be.heatEnergy == 200 && be.slots.get(0).getCount() == 1, "ignition gives heat and consumes one coal");
        be.updateEntity();
        check(be.burnTime == 1999 && be.heatEnergy == 400, "running burn decrements after ignition");
        be.heatEnergy = 100_000;
        be.updateEntity();
        check(be.burnTime == 1999 && be.heatEnergy == 100_000, "full firebox pauses burn");
        be.burnTime = 0;
        be.slots.set(0, ItemStack.EMPTY);
        be.updateEntity();
        check(be.heatEnergy == 99_900 && be.burnHeat == 0, "idle heat cools by heat/1000");
        be.heatEnergy = 200;
        be.updateEntity();
        check(be.heatEnergy == 199, "idle heat cools at least one");

        var second = firebox(new Level(), new BlockPos(2, 0, 0));
        var remainder = new Item("fuel_remainder");
        var containedFuel = new Item("contained_fuel", 64, 1600, remainder);
        second.slots.set(1, new ItemStack(containedFuel));
        second.updateEntity();
        check(second.slots.get(1).is(remainder) && second.slots.get(0).isEmpty()
                && second.burnTime == 1600, "second fuel slot leaves crafting remainder");
    }

    private static void coldStartAndResume() {
        var level = new Level();
        var pos = new BlockPos(70, 0, 0);
        var fire = firebox(level, pos);
        var oven = oven(level, pos.offset(0, 1, 0));
        fire.slots.set(0, new ItemStack(Items.COAL, 2));
        oven.slots.set(0, new ItemStack(Items.COAL));
        int liveTicks = 0;
        while (liveTicks++ < 30) {
            fire.updateEntity();
            oven.updateEntity();
            check(oven.slots.get(0).getCount() == 1 && oven.slots.get(1).isEmpty()
                    && oven.tank.getFill() == 0, "before full progress, no product appears");
        }
        check(fire.burnTime > 0 && oven.progress > 0, "cold fuel actually drove partial progress");
        int progressBeforeCut = oven.progress;
        level.entities.remove(pos);
        for (int tick = 0; tick < 2000; tick++) oven.updateEntity();
        check(oven.progress >= progressBeforeCut && oven.progress < MachineFurnaceCombinationBlockEntity.PROCESS_TIME
                && oven.heat < 100 && !oven.wasOn, "missing source eventually pauses after residual heat is spent");
        check(oven.slots.get(0).getCount() == 1 && oven.slots.get(1).isEmpty() && oven.tank.getFill() == 0,
                "interruption produces neither item nor fluid");
        int paused = oven.progress;
        for (int tick = 0; tick < 10; tick++) oven.updateEntity();
        check(oven.progress == paused, "valid recipe holds progress without usable heat");

        var fireTag = new CompoundTag();
        var ovenTag = new CompoundTag();
        save(fire, fireTag);
        save(oven, ovenTag);
        var resumedLevel = new Level();
        var resumedFire = firebox(resumedLevel, pos);
        var resumedOven = oven(resumedLevel, pos.offset(0, 1, 0));
        load(resumedFire, fireTag);
        load(resumedOven, ovenTag);
        check(resumedOven.progress == paused && resumedOven.slots.get(0).getCount() == 1
                && resumedOven.tank.getFill() == 0, "mid-run save/load keeps progress and unconsumed input");
        boolean completed = false;
        for (int tick = 0; tick < 3000; tick++) {
            resumedFire.updateEntity();
            resumedOven.updateEntity();
            if (resumedOven.slots.get(0).isEmpty()) {
                check(resumedOven.slots.get(1).is(NtmItems.COKE_COAL.get())
                        && resumedOven.slots.get(1).getCount() == 1
                        && resumedOven.tank.getTankType() == Fluids.COALCREOSOTE
                        && resumedOven.tank.getFill() == 100,
                        "first completion atomically consumes one coal and makes coke plus creosote");
                completed = true;
                break;
            }
            check(resumedOven.slots.get(0).getCount() == 1 && resumedOven.slots.get(1).isEmpty()
                    && resumedOven.tank.getFill() == 0, "resumed work has no premature partial output");
        }
        check(completed, "cold-start fuel and resumed heat finish within bounded ticks");
        for (int tick = 0; tick < 30; tick++) {
            resumedFire.updateEntity();
            resumedOven.updateEntity();
        }
        check(resumedOven.slots.get(1).getCount() == 1 && resumedOven.tank.getFill() == 100,
                "post-completion ticks do not duplicate product");
    }

    private static void heatAndProcessing() {
        var level = new Level();
        var lower = firebox(level, new BlockPos(0, 0, 0));
        var upper = oven(level, new BlockPos(0, 1, 0));
        lower.heatEnergy = 100_000;
        upper.slots.set(MachineFurnaceCombinationBlockEntity.SLOT_INPUT, new ItemStack(Items.COAL));
        upper.updateEntity();
        check(upper.heat == 24_750 && upper.progress == 250 && lower.heatEnergy == 75_000,
                "adjacent firebox transfers ceil(diff/4), then oven spends floor(heat/100)");
        check(upper.wasOn && upper.dirty > 0 && lower.dirty > 0, "processing and heat transfer mark changed state");
        var remote = oven(level, new BlockPos(4, 1, 0));
        remote.slots.set(0, new ItemStack(Items.COAL));
        int before = lower.heatEnergy;
        remote.updateEntity();
        check(remote.heat == 0 && lower.heatEnergy == before, "non-adjacent firebox does not feed oven");
        upper.progress = 19_999;
        upper.heat = 200;
        lower.heatEnergy = 0;
        upper.updateEntity();
        check(upper.slots.get(0).isEmpty() && upper.slots.get(1).is(NtmItems.COKE_COAL.get())
                && upper.slots.get(1).getCount() == 1, "one coal yields one coke at threshold: input="
                + upper.slots.get(0).getCount() + " output=" + upper.slots.get(1).getCount()
                + " progress=" + upper.progress + " heat=" + upper.heat);
        check(upper.tank.getTankType() == Fluids.COALCREOSOTE && upper.tank.getFill() == 100,
                "same completion yields 100 coal creosote");
        check(upper.progress >= 0, "threshold carries nonnegative progress");

        var atCap = oven(level, new BlockPos(10, 1, 0));
        var source = firebox(level, new BlockPos(10, 0, 0));
        atCap.heat = 100_000;
        source.heatEnergy = 100_000;
        atCap.updateEntity();
        check(atCap.heat == 100_000 && source.heatEnergy == 100_000,
                "equal heat at cap does not cool or pull");
        atCap.heat = 500;
        source.heatEnergy = 100;
        atCap.updateEntity();
        check(atCap.heat == 499, "lower source cools idle oven at least one");
        atCap.heat = 700;
        source.heatEnergy = 700;
        atCap.updateEntity();
        check(atCap.heat == 700 && source.heatEnergy == 700,
                "equal heat below cap does not passively cool");
        atCap.heat = 99_999;
        source.heatEnergy = 100_000;
        atCap.updateEntity();
        check(atCap.heat == 100_000 && source.heatEnergy == 99_999,
                "diffusion rounds one positive difference up and respects cap");
        atCap.heat = 100_000;
        source.heatEnergy = 200_000;
        atCap.updateEntity();
        check(atCap.heat == 100_000 && source.heatEnergy == 200_000,
                "at-cap oven neither pulls nor cools");
        var noSource = oven(level, new BlockPos(50, 1, 0));
        noSource.heat = 5_000;
        noSource.updateEntity();
        check(noSource.heat == 4_995 && noSource.dirty > 0,
                "oven without source cools by heat/1000 and marks dirty");
    }

    private static void recipeAndBlocks() {
        var level = new Level();
        var be = oven(level, new BlockPos(0, 0, 0));
        check(CombinationRecipes.isItemValid(new ItemStack(Items.COAL)), "live coal recipe registered");
        check(CombinationRecipes.isItemValid(new ItemStack(NtmItems.CINNABAR.get())), "secondary fluid recipe registered");
        be.slots.set(0, new ItemStack(Items.COAL));
        be.heat = 200;
        be.tank.setFill(23_900);
        be.tank.setTankType(Fluids.COALCREOSOTE);
        be.tank.setFill(23_900);
        be.progress = 19_999;
        be.updateEntity();
        check(be.tank.getFill() == 24_000 && be.slots.get(0).isEmpty(), "23900 fill permits 100 unit completion");

        be.slots.set(0, new ItemStack(Items.COAL));
        be.tank.setFill(23_901);
        be.progress = 900;
        be.heat = 200;
        be.updateEntity();
        check(be.progress == 0 && be.slots.get(0).getCount() == 1 && be.tank.getFill() == 23_901
                && be.slots.get(1).getCount() == 1, "23901 fill blocks without consuming or producing");
        be.tank.setFill(0);
        be.tank.setTankType(Fluids.MERCURY);
        be.tank.setFill(100);
        be.progress = 900;
        be.updateEntity();
        check(be.progress == 0 && be.slots.get(0).getCount() == 1 && be.slots.get(1).getCount() == 1
                && be.tank.getTankType() == Fluids.MERCURY && be.tank.getFill() == 100,
                "different nonempty tank type blocks without item or fluid mutation");
        be.tank.setFill(0);
        be.progress = 19_999;
        be.heat = 200;
        be.updateEntity();
        check(be.tank.getTankType() == Fluids.COALCREOSOTE && be.tank.getFill() == 100,
                "empty residual fluid type can change on completion");

        be.slots.set(0, new ItemStack(Items.COAL));
        be.slots.set(1, new ItemStack(NtmItems.COKE_COAL.get(), 64));
        be.progress = 900;
        be.updateEntity();
        check(be.progress == 0 && be.slots.get(0).getCount() == 1 && be.slots.get(1).getCount() == 64
                && be.tank.getFill() == 100, "full output blocks without input or fluid mutation");
        be.slots.set(1, new ItemStack(NtmItems.COKE_COAL.get()).component("different"));
        be.progress = 900;
        be.updateEntity();
        check(be.progress == 0 && be.slots.get(0).getCount() == 1 && be.slots.get(1).getCount() == 1
                && be.tank.getFill() == 100, "output component mismatch blocks without consuming or filling");
        be.slots.set(1, ItemStack.EMPTY);
        be.tank.setTankType(Fluids.NONE);
        be.heat = 0;
        be.progress = 900;
        be.updateEntity();
        check(be.progress == 900 && !be.wasOn, "valid recipe without heat pauses progress");
        be.slots.set(0, new ItemStack(new Item("unknown")));
        be.updateEntity();
        check(be.progress == 0, "invalid input resets progress");
        be.progress = 300;
        be.slots.set(0, ItemStack.EMPTY);
        int oldDirty = be.dirty;
        be.updateEntity();
        check(be.progress == 0 && be.dirty > oldDirty, "missing input resets progress and marks dirty");

        var carry = oven(level, new BlockPos(20, 0, 0));
        carry.slots.set(0, new ItemStack(Items.COAL));
        carry.progress = 700;
        carry.heat = 500;
        carry.slots.set(0, new ItemStack(NtmItems.CINNABAR.get()));
        carry.updateEntity();
        check(carry.progress > 700 && carry.slots.get(0).is(NtmItems.CINNABAR.get()),
                "valid recipe switch inherits progress");
        carry.progress = 19_999;
        carry.heat = 500;
        carry.updateEntity();
        check(carry.slots.get(0).isEmpty() && carry.slots.get(1).is(NtmItems.SULFUR.get())
                && carry.tank.getTankType() == Fluids.MERCURY && carry.tank.getFill() == 100,
                "switched recipe produces its own item and fluid together");

        var stackLimit = oven(level, new BlockPos(30, 0, 0));
        stackLimit.slots.set(0, new ItemStack(Items.SUGAR_CANE));
        stackLimit.slots.set(1, new ItemStack(Items.SUGAR, 14));
        stackLimit.progress = 19_999;
        stackLimit.heat = 500;
        stackLimit.updateEntity();
        check(stackLimit.slots.get(1).getCount() == 16 && stackLimit.tank.getFill() == 50,
                "item maximum accepts exact remaining space");
        stackLimit.slots.set(0, new ItemStack(Items.SUGAR_CANE));
        stackLimit.slots.set(1, new ItemStack(Items.SUGAR, 15));
        stackLimit.progress = 900;
        stackLimit.updateEntity();
        check(stackLimit.progress == 0 && stackLimit.slots.get(1).getCount() == 15,
                "item maximum rejects a two-item result with one space");

        var small = new MachineFurnaceCombinationBlockEntity(new BlockPos(31, 0, 0), new BlockState()) {
            @Override public int getMaxStackSize(ItemStack stack) { return 1; }
        };
        level.put(small);
        small.slots.set(0, new ItemStack(Items.SUGAR_CANE));
        small.progress = 800;
        small.heat = 500;
        small.updateEntity();
        check(small.progress == 0 && small.slots.get(0).getCount() == 1 && small.slots.get(1).isEmpty()
                && small.tank.getFill() == 0, "empty output obeys smaller container maximum");

        var noneType = oven(level, new BlockPos(40, 0, 0));
        noneType.slots.set(0, new ItemStack(Items.COAL));
        noneType.tank.setFill(50);
        noneType.progress = 800;
        noneType.updateEntity();
        check(noneType.progress == 0, "nonempty NONE tank blocks real fluid recipe");
        noneType.tank.setFill(0);
        noneType.progress = 19_998;
        noneType.heat = 300;
        noneType.updateEntity();
        check(noneType.progress == 0 && noneType.tank.getFill() == 100,
                "completion carries exact excess progress after speed two");
    }

    private static void saveAndMenu() {
        var level = new Level();
        var fire = firebox(level, new BlockPos(0, 0, 0));
        fire.heatEnergy = 700;
        fire.burnTime = 20;
        fire.maxBurnTime = 40;
        fire.burnHeat = 200;
        fire.playersUsing = 3;
        fire.doorAngle = 60;
        fire.slots.set(0, new ItemStack(Items.COAL));
        var tag = new CompoundTag();
        save(fire, tag);
        var copy = firebox(new Level(), new BlockPos(0, 0, 0));
        load(copy, tag);
        check(copy.heatEnergy == 700 && copy.burnTime == 20 && copy.slots.get(0).is(Items.COAL),
                "firebox save/load preserves heat, burn and inventory");
        check(copy.playersUsing == 0 && copy.doorAngle == 0, "viewer count and door animation reset on load");
        var buf = new RegistryFriendlyByteBuf();
        fire.serialize(buf);
        copy.deserialize(buf);
        check(copy.playersUsing == 3 && copy.doorAngle == 60, "network sync retains transient door state");

        var malformed = new CompoundTag();
        malformed.putInt("heatEnergy", Integer.MAX_VALUE);
        malformed.putInt("maxBurnTime", -4);
        malformed.putInt("burnTime", Integer.MAX_VALUE);
        malformed.putInt("burnHeat", -30);
        malformed.putInt("playersUsing", 9);
        malformed.putFloat("doorAngle", 100);
        load(copy, malformed);
        check(copy.heatEnergy == 100_000 && copy.maxBurnTime == 0 && copy.burnTime == 0
                && copy.burnHeat == 0 && copy.playersUsing == 0 && copy.doorAngle == 0,
                "firebox clamps malformed saved ranges and drops transient viewers");
        var itemTag = new CompoundTag();
        var persistent = new CompoundTag();
        persistent.putInt("heatEnergy", -10);
        persistent.putInt("maxBurnTime", 50);
        persistent.putInt("burnTime", 80);
        persistent.putInt("burnHeat", Integer.MAX_VALUE);
        itemTag.put("persistent", persistent);
        copy.readNBT(itemTag);
        check(copy.heatEnergy == 0 && copy.burnTime == 50 && copy.burnHeat == 100_000,
                "firebox item NBT uses original key and clamps invalid ranges");

        var oven = oven(new Level(), new BlockPos(0, 1, 0));
        oven.heat = 800;
        oven.progress = 1200;
        oven.tank.setTankType(Fluids.COALCREOSOTE);
        oven.tank.setFill(500);
        oven.slots.set(0, new ItemStack(Items.COAL));
        var ovenTag = new CompoundTag();
        save(oven, ovenTag);
        var ovenCopy = oven(new Level(), new BlockPos(0, 1, 0));
        load(ovenCopy, ovenTag);
        check(ovenCopy.heat == 800 && ovenCopy.progress == 1200 && ovenCopy.tank.getFill() == 500
                && ovenCopy.slots.get(0).is(Items.COAL), "oven save/load preserves processing, fluid and input");
        var ovenBuf = new RegistryFriendlyByteBuf();
        oven.serialize(ovenBuf);
        var ovenSynced = oven(new Level(), new BlockPos(0, 1, 0));
        ovenSynced.deserialize(ovenBuf);
        check(ovenSynced.heat == 800 && ovenSynced.progress == 1200 && ovenSynced.tank.getFill() == 500,
                "oven network sync retains processing and fluid state");
        var badOven = new CompoundTag();
        badOven.putInt("heat", Integer.MAX_VALUE);
        badOven.putInt("progress", -1);
        badOven.putInt("tank", 900_000);
        badOven.putInt("tank_max", Integer.MAX_VALUE);
        badOven.putInt("tank_type", Fluids.COALCREOSOTE.getID());
        load(ovenCopy, badOven);
        check(ovenCopy.heat == 100_000 && ovenCopy.progress == 0
                && ovenCopy.tank.getMaxFill() == 24_000 && ovenCopy.tank.getFill() == 24_000,
                "oven clamps malformed saved ranges and fixes tank capacity");

        var player = new Player();
        player.world = level;
        Inventory inv = player.getInventory();
        inv.player = player;
        var fireMenu = new HeaterFireboxMenu(0, inv, fire);
        inv.setItem(0, new ItemStack(Items.COAL));
        check(fireMenu.quickMoveStack(player, -1).isEmpty(), "firebox rejects negative quick move");
        check(fireMenu.quickMoveStack(player, fireMenu.slots.size()).isEmpty(), "firebox rejects out-of-range quick move");
        check(!fireMenu.quickMoveStack(player, fireMenu.slots.size() - 9).isEmpty(), "fuel quick moves into firebox");
        inv.setItem(1, new ItemStack(new Item("nonfuel")));
        check(fireMenu.quickMoveStack(player, fireMenu.slots.size() - 8).isEmpty()
                && inv.getItem(1).getCount() == 1, "firebox rejects nonfuel quick move");
        check(!fireMenu.slots.get(0).mayPlace(new ItemStack(new Item("nonfuel")))
                && fireMenu.slots.get(1).mayPlace(new ItemStack(Items.COAL)),
                "both firebox slots enforce fuel placement");
        var ovenMenu = new MachineFurnaceCombinationMenu(0, inv, oven);
        check(ovenMenu.quickMoveStack(player, -1).isEmpty(), "oven rejects negative quick move");
        check(ovenMenu.quickMoveStack(player, ovenMenu.slots.size()).isEmpty(), "oven rejects out-of-range quick move");
        check(!ovenMenu.slots.get(1).mayPlace(new ItemStack(Items.COAL))
                && !ovenMenu.slots.get(3).mayPlace(new ItemStack(Items.COAL)), "output slots are take only");
        inv.setItem(2, new ItemStack(new Item("unknown")));
        check(ovenMenu.quickMoveStack(player, ovenMenu.slots.size() - 7).isEmpty(),
                "oven rejects invalid recipe quick move");
        oven.slots.set(0, ItemStack.EMPTY);
        inv.setItem(3, new ItemStack(Items.COAL));
        check(!ovenMenu.quickMoveStack(player, ovenMenu.slots.size() - 6).isEmpty()
                && oven.slots.get(0).is(Items.COAL), "coal quick moves to oven input");
        check(oven.getSlotsForFace(Direction.NORTH).length == 2
                && oven.getSlotsForFace(Direction.NORTH)[0] == 0
                && oven.getSlotsForFace(Direction.NORTH)[1] == 1
                && oven.canTakeItemThroughFace(1, new ItemStack(Items.COAL), Direction.NORTH)
                && !oven.canTakeItemThroughFace(0, new ItemStack(Items.COAL), Direction.NORTH),
                "oven sided exposure remains input/output only");
        var clientLevel = new Level();
        clientLevel.isClientSide = true;
        var client = oven(clientLevel, new BlockPos(5, 1, 0));
        client.slots.set(0, new ItemStack(Items.COAL));
        client.heat = 500;
        client.progress = 800;
        client.updateEntity();
        check(client.heat == 500 && client.progress == 800 && client.slots.get(0).getCount() == 1,
                "client oven tick does not mutate processing state");
    }

    private static void realTankPersistence() {
        var tank = new FluidTank(Fluids.NONE, 24_000);
        tank.setTankType(Fluids.COALCREOSOTE);
        tank.withPressure(17);
        tank.setFill(345);
        var tag = new CompoundTag();
        tank.writeToNBT(tag, "tank");
        check(tag.getInt("tank") == 345 && tag.getInt("tank_max") == 24_000
                && tag.getInt("tank_type") == Fluids.COALCREOSOTE.getID()
                && tag.getShort("tank_p") == 17,
                "real tank writes original fill/capacity/type/pressure NBT keys");
        var loaded = new FluidTank(Fluids.NONE, 1);
        loaded.readFromNBT(tag, "tank");
        check(loaded.getFill() == 345 && loaded.getMaxFill() == 24_000
                && loaded.getTankType() == Fluids.COALCREOSOTE && loaded.getPressure() == 17,
                "real tank NBT load restores fill, capacity, type and pressure");
        var buf = new RegistryFriendlyByteBuf();
        tank.serialize(buf);
        var synced = new FluidTank(Fluids.NONE, 1);
        synced.deserialize(buf);
        check(synced.getFill() == 345 && synced.getMaxFill() == 24_000
                && synced.getTankType() == Fluids.COALCREOSOTE && synced.getPressure() == 17,
                "real tank buffer roundtrip restores fill, capacity, type and pressure");
        loaded.setTankType(Fluids.MERCURY);
        check(loaded.getFill() == 0 && loaded.getTankType() == Fluids.MERCURY,
                "real tank type switch empties previous fluid");
        tag.putInt("tank", Integer.MAX_VALUE);
        loaded.readFromNBT(tag, "tank");
        check(loaded.getFill() == 24_000, "real tank NBT load clamps overflow to capacity");
        tag.putInt("tank", -5);
        loaded.readFromNBT(tag, "tank");
        check(loaded.getFill() == 0, "real tank NBT load clamps negative fill");
    }

    public static void main(String[] args) {
        fuel();
        System.out.println("fuel timing: passed");
        coldStartAndResume();
        System.out.println("cold-start interruption and save resume: passed");
        heatAndProcessing();
        System.out.println("heat transfer and completion: passed");
        recipeAndBlocks();
        System.out.println("recipe capacity and reset: passed");
        saveAndMenu();
        System.out.println("save and menu: passed");
        realTankPersistence();
        System.out.println("real fluid tank persistence: passed");
        System.out.println("Goal 5A checks: " + checks);
    }
}
