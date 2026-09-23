package com.hbm.blockentity.machine;

import com.hbm.inventory.recipes.BlastFurnaceRecipes;
import com.hbm.inventory.recipes.PressRecipes;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.StampItem;
import net.minecraft.core.BlockPos;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;

public class Goal4DownstreamRegression {
    private static int checks;
    private static void check(boolean result, String label) {
        if(!result) throw new AssertionError(label);
        checks++;
    }
    private static MachineBlastFurnaceBlockEntity blast() {
        var machine = new MachineBlastFurnaceBlockEntity(new BlockPos(0, 64, 0), new BlockState());
        machine.level = new Level();
        machine.fuel = 800;
        return machine;
    }
    public static void main(String[] args) {
        BlastFurnaceRecipes.INSTANCE.registerDefaults();
        new PressRecipes().registerDefaults();
        for(Item sand : new Item[] {Blocks.SAND, Blocks.RED_SAND}) {
            for(boolean reversed : new boolean[] {false, true}) {
                var machine = blast();
                machine.slots.set(reversed ? 2 : 1, new ItemStack(NtmItems.POWDER_IRON.get(), 2));
                machine.slots.set(reversed ? 1 : 2, new ItemStack(sand));
                for(int tick = 0; tick < 799; tick++) machine.updateEntity();
                check(machine.slots.get(3).isEmpty() && machine.fuel == 800, "iron powder steel cannot complete before tick800");
                machine.updateEntity();
                check(machine.slots.get(3).is(NtmItems.INGOT_STEEL.get()) && machine.slots.get(3).getCount() == 2,
                        "real dust+either sand branch outputs two steel in either input order");
                check(machine.slots.get(4).is(NtmItems.INGOT_RAW.get()) && machine.slots.get(4).getCount() == 1,
                        "steel branch outputs one slag item (META identity modeled separately)");
                check(machine.slots.get(1).isEmpty() && machine.slots.get(2).isEmpty() && machine.fuel == 0,
                        "completion consumes exactly two powder, one sand and800fuel");
                machine.updateEntity();
                check(machine.slots.get(3).getCount() == 2, "no repeated steel after completion");
            }
        }
        var shortInput = blast();
        shortInput.slots.set(1, new ItemStack(NtmItems.POWDER_IRON.get()));
        shortInput.slots.set(2, new ItemStack(Blocks.SAND));
        shortInput.updateEntity();
        check(shortInput.progress == 0 && shortInput.fuel == 800 && shortInput.slots.get(1).getCount() == 1,
                "one iron powder rejected without partial consumption");
        for(Item copper : new Item[] {Items.COPPER_INGOT, NtmItems.INGOT_COPPER.get()}) {
            var press = new MachinePressBlockEntity(new BlockPos(0, 64, 0), new BlockState());
            press.level = new Level();
            press.slots.set(1, new ItemStack(new StampItem("plate", "plate", 32)));
            press.slots.set(2, new ItemStack(copper));
            press.burnTime = 200;
            press.speed = 400;
            press.press = 199;
            press.updateEntity();
            check(press.slots.get(3).is(NtmItems.PLATE_COPPER.get()) && press.slots.get(3).getCount() == 1
                    && press.slots.get(2).isEmpty() && press.burnTime == 0, "either copper ingot recovers one usable copper plate");
            var machine = blast();
            machine.slots.set(1, new ItemStack(copper));
            machine.slots.set(2, new ItemStack(Items.REDSTONE));
            for(int tick = 0; tick < 400; tick++) machine.updateEntity();
            check(machine.slots.get(3).isEmpty() && machine.progress > 0.99F && machine.progress < 1.0F,
                    "existing float progress leaves nominal400tick copper branch just below completion");
            machine.updateEntity();
            check(machine.slots.get(3).is(NtmItems.INGOT_RED_COPPER.get()) && machine.slots.get(3).getCount() == 2
                    && machine.slots.get(1).isEmpty() && machine.slots.get(2).isEmpty() && machine.fuel == 0,
                    "either copper ingot feeds existing red-copper electrical line");
        }
        System.out.println("Goal 4 downstream processing: " + checks + " assertions passed");
    }
}
