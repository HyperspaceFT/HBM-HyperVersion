package com.hbm.blockentity.machine;

import com.hbm.inventory.menus.MachineWoodBurnerMenu;
import com.hbm.handler.pollution.PollutionHandler;
import com.hbm.items.NtmItems;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;

public class GeneratorRegression {
    private static int checks;
    private static final BlockPos POS = new BlockPos(0, 64, 0);
    private static final BlockState STATE = new BlockState();

    private static void check(boolean value, String message) {
        checks++;
        if (!value) throw new AssertionError(message);
    }

    private static MachineWoodBurnerBlockEntity burner() {
        var machine = new MachineWoodBurnerBlockEntity(POS, STATE);
        machine.level = new Level();
        return machine;
    }

    private static void fuelTimes() {
        check(MachineWoodBurnerBlockEntity.BURN_MODULE.getBurnTime(new ItemStack(Items.OAK_LOG)) == 1200,
                "logs burn four times 300");
        check(MachineWoodBurnerBlockEntity.BURN_MODULE.getBurnTime(new ItemStack(Items.OAK_WOOD)) == 1200,
                "bark wood in logs tag burns four times 300");
        check(MachineWoodBurnerBlockEntity.BURN_MODULE.getBurnTime(new ItemStack(Items.OAK_PLANKS)) == 600,
                "planks burn twice 300");
        check(MachineWoodBurnerBlockEntity.BURN_MODULE.getBurnTime(new ItemStack(Items.CHARCOAL)) == 1600,
                "charcoal retains base time");
        check(MachineWoodBurnerBlockEntity.BURN_MODULE.getBurnTime(new ItemStack(Items.COAL)) == 1600,
                "coal retains base time");
        check(MachineWoodBurnerBlockEntity.BURN_MODULE.getBurnTime(new ItemStack(Items.LAVA_BUCKET)) == 20000,
                "lava bucket is valid solid fuel");
        check(MachineWoodBurnerBlockEntity.BURN_MODULE.getBurnTime(new ItemStack(Items.STONE)) == 0,
                "stone is not fuel");
    }

    private static void solidCycle() {
        var machine = burner();
        machine.updateEntity();
        check(machine.power == 0 && machine.burnTime == 0, "empty generator idle");
        machine.slots.set(0, new ItemStack(Items.STONE));
        machine.updateEntity();
        check(machine.burnTime == 0 && machine.slots.get(0).is(Items.STONE), "invalid fuel untouched");
        machine.slots.set(0, new ItemStack(Items.OAK_LOG));
        machine.updateEntity();
        check(machine.burnTime == 1200 && machine.maxBurnTime == 1200, "OFF generator preloads log");
        check(machine.slots.get(0).isEmpty() && machine.power == 0 && machine.powerGen == 0,
                "preload consumes one fuel without generating");
        check(machine.ashLevelWood == 1200 && machine.ashLevelCoal == 0,
                "log advances wood ash ledger");
        machine.updateEntity();
        check(machine.burnTime == 1200 && machine.power == 0, "OFF loaded fuel pauses");
        machine.isOn = true;
        int beforeDirty = machine.dirty;
        machine.updateEntity();
        check(machine.burnTime == 1199 && machine.power == 100 && machine.powerGen == 100,
                "ON generator consumes one time and adds 100 power");
        check(machine.dirty > beforeDirty, "generation marks saved state dirty");
        machine.power = 99_950;
        machine.updateEntity();
        check(machine.power == 100_000 && machine.burnTime == 1198,
                "partial capacity clamps generated power");
        machine.updateEntity();
        check(machine.power == 100_000 && machine.burnTime == 1198 && machine.powerGen == 0,
                "full power pauses loaded fuel");
        machine.level.time = 20;
        machine.power = 0;
        int pollutionBefore = PollutionHandler.calls;
        machine.updateEntity();
        check(PollutionHandler.calls == pollutionBefore + 1, "active solid burn emits soot at 20-tick boundary");
        machine.level.time = 21;
        machine.updateEntity();
        check(PollutionHandler.calls == pollutionBefore + 1, "solid soot is not emitted off boundary");
        machine.power = 100_000;
        machine.burnTime = 0;
        machine.slots.set(0, new ItemStack(Items.OAK_PLANKS));
        machine.updateEntity();
        check(machine.burnTime == 600 && machine.power == 100_000 && machine.powerGen == 0,
                "full power still preloads next fuel");
    }

    private static void ashAndSlots() {
        var machine = burner();
        machine.slots.set(0, new ItemStack(Items.OAK_LOG, 2));
        var foreign2 = new ItemStack(Items.STONE, 3);
        var foreign3 = new ItemStack(Items.STONE, 4);
        var foreign4 = new ItemStack(Items.STONE, 5);
        machine.slots.set(2, foreign2);
        machine.slots.set(3, foreign3);
        machine.slots.set(4, foreign4);
        machine.updateEntity();
        machine.burnTime = 0;
        machine.updateEntity();
        check(machine.slots.get(1).is(NtmItems.POWDER_ASH_WOOD.get()), "second log creates wood ash in slot 1");
        check(machine.slots.get(1).getCount() == 1 && machine.ashLevelWood == 400,
                "2000 ash threshold retains 400 backlog");
        check(machine.slots.get(2) == foreign2 && machine.slots.get(3) == foreign3 && machine.slots.get(4) == foreign4,
                "ash never changes identifier and fluid slots");
        machine.burnTime = 0;
        machine.ashLevelWood = 1900;
        machine.slots.set(0, new ItemStack(Items.OAK_LOG));
        machine.slots.set(1, new ItemStack(Items.STONE));
        machine.updateEntity();
        check(machine.ashLevelWood == 3100 && machine.slots.get(1).is(Items.STONE),
                "blocked ash retains backlog while fuel loads");
        machine.slots.set(1, ItemStack.EMPTY);
        machine.burnTime = 0;
        machine.slots.set(0, new ItemStack(Items.OAK_LOG));
        machine.updateEntity();
        check(machine.ashLevelWood == 300 && machine.slots.get(1).getCount() == 2,
                "next fuel load flushes two backlog ash");
        check(machine.slots.get(2) == foreign2 && machine.slots.get(3) == foreign3 && machine.slots.get(4) == foreign4,
                "backlog flush leaves foreign slots unchanged");
        machine.ashLevelWood = 1900;
        machine.slots.set(0, new ItemStack(Items.OAK_LOG));
        machine.slots.set(1, new ItemStack(NtmItems.POWDER_ASH_WOOD.get(), 64));
        machine.burnTime = 0;
        machine.updateEntity();
        check(machine.ashLevelWood == 3100 && machine.slots.get(1).getCount() == 64,
                "full matching ash stack retains backlog");
        machine.slots.set(1, new ItemStack(NtmItems.POWDER_ASH_WOOD.get(), 63));
        machine.slots.set(0, new ItemStack(Items.OAK_LOG));
        machine.burnTime = 0;
        machine.updateEntity();
        check(machine.ashLevelWood == 2300 && machine.slots.get(1).getCount() == 64,
                "one free ash slot releases one backlog unit and retains the rest");
        machine.power = 0;
        machine.isOn = true;
        int burningBefore = machine.burnTime;
        machine.updateEntity();
        check(machine.burnTime == burningBefore - 1 && machine.powerGen == 100,
                "ash backlog does not pause generation");
        var charcoal = burner();
        charcoal.slots.set(0, new ItemStack(Items.CHARCOAL, 2));
        charcoal.updateEntity();
        charcoal.burnTime = 0;
        charcoal.updateEntity();
        check(charcoal.slots.get(1).is(NtmItems.POWDER_ASH_WOOD.get()) && charcoal.ashLevelCoal == 0,
                "charcoal yields wood ash, not coal ash");
        var sapling = burner();
        sapling.ashLevelWood = 1900;
        sapling.slots.set(0, new ItemStack(Items.OAK_SAPLING));
        sapling.updateEntity();
        check(sapling.slots.get(1).is(NtmItems.POWDER_ASH_WOOD.get()), "sapling contributes wood ash");
        var coal = burner();
        coal.slots.set(0, new ItemStack(Items.COAL));
        coal.updateEntity();
        check(coal.ashLevelCoal == 1600 && coal.ashLevelWood == 0, "coal contributes coal ash");
    }

    private static void remainderAndPersistence() {
        var machine = burner();
        machine.setPower(200_000);
        check(machine.getPower() == 100_000, "external power setter clamps over-capacity values");
        machine.setPower(-100);
        check(machine.getPower() == 0, "external power setter clamps negative values");
        machine.slots.set(0, new ItemStack(Items.LAVA_BUCKET));
        machine.updateEntity();
        check(machine.burnTime == 20000 && machine.slots.get(0).is(Items.BUCKET),
                "single lava bucket leaves empty bucket in fuel slot");
        machine.isOn = true;
        machine.liquidBurn = true;
        machine.power = 1234;
        machine.ashLevelCoal = 4321;
        machine.ashLevelWood = 321;
        machine.ashLevelMisc = 123;
        machine.tank.setFill(17);
        var tag = new CompoundTag();
        machine.saveAdditional(tag, null);
        var restored = burner();
        restored.loadAdditional(tag, null);
        check(restored.power == 1234 && restored.burnTime == 20000 && restored.maxBurnTime == 20000,
                "power and burn times survive save/load");
        check(restored.isOn && restored.liquidBurn && restored.tank.getFill() == 17,
                "control and tank state survive save/load");
        check(restored.ashLevelCoal == 4321 && restored.ashLevelWood == 321 && restored.ashLevelMisc == 123,
                "ash backlog survives save/load");
        var malformed = new CompoundTag();
        malformed.putLong("power", -17);
        restored.loadAdditional(malformed, null);
        check(restored.power == 0, "loaded negative power clamps to zero");
        malformed.putLong("power", 200_000);
        restored.loadAdditional(malformed, null);
        check(restored.power == 100_000, "loaded excessive power clamps to max");
        var buf = new RegistryFriendlyByteBuf();
        machine.serialize(buf);
        var synced = burner();
        synced.deserialize(buf);
        check(synced.power == 1234 && synced.burnTime == 20000 && synced.maxBurnTime == 20000,
                "power and burn times survive sync");
        check(synced.isOn && synced.liquidBurn && synced.tank.getFill() == 17,
                "control and tank state survive sync");
        var oversized = new RegistryFriendlyByteBuf();
        oversized.writeLong(200_000);
        oversized.writeInt(0);
        oversized.writeInt(0);
        oversized.writeBoolean(false);
        oversized.writeBoolean(false);
        oversized.writeInt(0);
        oversized.writeInt(0);
        synced.deserialize(oversized);
        check(synced.power == 100_000, "sync clamps excessive power");
    }

    private static void controlAndClient() {
        var machine = burner();
        var player = new Player();
        player.world = machine.level;
        var tag = new CompoundTag();
        tag.putBoolean("toggle", true);
        check(!machine.hasPermission(player), "closed menu cannot control generator");
        player.containerMenu = new MachineWoodBurnerMenu(1, player.getInventory(), machine);
        check(machine.hasPermission(player), "matching open menu grants local control");
        machine.receiveControl(tag);
        check(machine.isOn, "toggle turns generator on");
        var falseToggle = new CompoundTag();
        falseToggle.putBoolean("toggle", false);
        machine.receiveControl(falseToggle);
        check(machine.isOn, "false toggle payload leaves state unchanged");
        var switchTag = new CompoundTag();
        switchTag.putBoolean("switch", true);
        machine.receiveControl(switchTag);
        check(machine.liquidBurn, "switch selects liquid mode");
        machine.valid = false;
        check(!machine.hasPermission(player), "removed or distant machine denies control");
        machine.valid = true;
        var other = burner();
        player.containerMenu = new MachineWoodBurnerMenu(2, player.getInventory(), other);
        check(!machine.hasPermission(player), "different machine menu denies control");
        machine.level.isClientSide = true;
        player.containerMenu = new MachineWoodBurnerMenu(3, player.getInventory(), machine);
        check(!machine.hasPermission(player), "client cannot grant server control");
        machine.powerGen = 100;
        machine.burnTime = 2;
        machine.slots.set(0, new ItemStack(Items.OAK_LOG));
        machine.updateEntity();
        check(machine.level.particles == 1 && machine.burnTime == 2 && machine.power == 0,
                "client shows smoke without consuming or generating");
    }

    public static void main(String[] args) {
        fuelTimes();
        solidCycle();
        ashAndSlots();
        remainderAndPersistence();
        controlAndClient();
        System.out.println("Goal 3B production generator regression: " + checks + " checks passed");
    }
}
