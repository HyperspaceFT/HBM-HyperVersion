package com.hbm.module.machine;

import api.hbm.energymk2.IEnergyHandlerMK2;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.recipes.ChemicalPlantRecipes;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.inventory.recipes.loader.GenericRecipes;
import com.hbm.items.machine.BlueprintsItem;
import net.minecraft.core.NonNullList;
import net.minecraft.world.item.ItemStack;

public class ModuleMachineChemicalPlant extends ModuleMachineBase {

    public ModuleMachineChemicalPlant(int index, IEnergyHandlerMK2 battery, NonNullList<ItemStack> slots) {
        super(index, battery, slots);
        this.inputSlots = new int[3];
        this.outputSlots = new int[3];
        this.inputTanks = new FluidTank[3];
        this.outputTanks = new FluidTank[3];
    }

    @Override
    public GenericRecipes<GenericRecipe> getRecipeSet() {
        return ChemicalPlantRecipes.INSTANCE;
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

    public ModuleMachineChemicalPlant itemInput(int a, int b, int c) {
        this.inputSlots[0] = a;
        this.inputSlots[1] = b;
        this.inputSlots[2] = c;
        return this;
    }

    public ModuleMachineChemicalPlant itemOutput(int a, int b, int c) {
        this.outputSlots[0] = a;
        this.outputSlots[1] = b;
        this.outputSlots[2] = c;
        return this;
    }

    public ModuleMachineChemicalPlant fluidInput(FluidTank a, FluidTank b, FluidTank c) {
        this.inputTanks[0] = a;
        this.inputTanks[1] = b;
        this.inputTanks[2] = c;
        return this;
    }

    public ModuleMachineChemicalPlant fluidOutput(FluidTank a, FluidTank b, FluidTank c) {
        this.outputTanks[0] = a;
        this.outputTanks[1] = b;
        this.outputTanks[2] = c;
        return this;
    }
}
