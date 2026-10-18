package com.hbm.module.machine;

import api.hbm.energymk2.IEnergyHandlerMK2;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.recipes.PUREXRecipes;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.inventory.recipes.loader.GenericRecipes;
import com.hbm.items.machine.BlueprintsItem;
import net.minecraft.core.NonNullList;
import net.minecraft.world.item.ItemStack;

/** Original ModuleMachinePUREX.java: three item inputs, six item outputs, three input tanks and one output tank. */
public class ModuleMachinePUREX extends ModuleMachineBase {

    public ModuleMachinePUREX(int index, IEnergyHandlerMK2 battery, NonNullList<ItemStack> slots) {
        super(index, battery, slots);
        this.inputSlots = new int[3];
        this.outputSlots = new int[6];
        this.inputTanks = new FluidTank[3];
        this.outputTanks = new FluidTank[1];
    }

    @Override
    public GenericRecipes<GenericRecipe> getRecipeSet() {
        return PUREXRecipes.INSTANCE;
    }

    @Override
    public void update(double speed, double power, boolean extraCondition, ItemStack blueprint) {
        // Original ModuleMachineBase.update: a pooled recipe is dropped as soon as its blueprint is missing
        GenericRecipe selected = this.getRecipe();
        if(selected != null && selected.isPooled() && !selected.isPartOfPool(BlueprintsItem.grabPool(blueprint))) {
            this.recipe = "null";
            this.progress = 0D;
            this.didProcess = false;
            this.markDirty = true;
            return;
        }
        super.update(speed, power, extraCondition, blueprint);
    }

    public ModuleMachinePUREX itemInput(int start) {
        for(int i = 0; i < this.inputSlots.length; i++) this.inputSlots[i] = start + i;
        return this;
    }

    public ModuleMachinePUREX itemOutput(int start) {
        for(int i = 0; i < this.outputSlots.length; i++) this.outputSlots[i] = start + i;
        return this;
    }

    public ModuleMachinePUREX fluidInput(FluidTank a, FluidTank b, FluidTank c) {
        this.inputTanks[0] = a;
        this.inputTanks[1] = b;
        this.inputTanks[2] = c;
        return this;
    }

    public ModuleMachinePUREX fluidOutput(FluidTank a) {
        this.outputTanks[0] = a;
        return this;
    }
}
