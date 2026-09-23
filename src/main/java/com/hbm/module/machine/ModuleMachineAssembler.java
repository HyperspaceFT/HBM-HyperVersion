package com.hbm.module.machine;

import api.hbm.energymk2.IEnergyHandlerMK2;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.recipes.AssemblyMachineRecipes;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.inventory.recipes.loader.GenericRecipes;
import com.hbm.items.machine.BlueprintsItem;
import com.hbm.util.BobMathUtil;
import net.minecraft.core.NonNullList;
import net.minecraft.world.item.ItemStack;

import java.util.Objects;

public class ModuleMachineAssembler extends ModuleMachineBase {

    public ModuleMachineAssembler(int index, IEnergyHandlerMK2 battery, NonNullList<ItemStack> slots) {
        super(index, battery, slots);
        this.inputSlots = new int[12];
        this.outputSlots = new int[1];
        this.inputTanks = new FluidTank[1];
        this.outputTanks = new FluidTank[1];
    }

    @Override
    public GenericRecipes<GenericRecipe> getRecipeSet() {
        return AssemblyMachineRecipes.INSTANCE;
    }

    @Override
    public void update(double speed, double power, boolean extraCondition, ItemStack blueprint) {
        double previousProgress = this.progress;
        String previousRecipe = this.recipe;
        GenericRecipe selected = this.getRecipe();
        if(selected != null && selected.isPooled() && !selected.isPartOfPool(BlueprintsItem.grabPool(blueprint))) {
            this.recipe = "null";
            this.progress = 0D;
            this.didProcess = false;
            this.markDirty = true;
            return;
        }
        super.update(speed, power, extraCondition, blueprint);
        // An interrupted cycle must save its reset even when no energy or inventory changed.
        this.markDirty |= this.progress != previousProgress || !Objects.equals(this.recipe, previousRecipe);
    }

    @Override
    protected boolean canFitOutput(GenericRecipe recipe) {
        if(!super.canFitOutput(recipe)) return false;
        if(recipe.outputItem == null) return true;
        for(int i = 0; i < Math.min(recipe.outputItem.length, this.outputSlots.length); i++) {
            if(recipe.outputItem[i].possibleMultiOutput()) continue;
            ItemStack stack = this.slots.get(this.outputSlots[i]);
            ItemStack result = recipe.outputItem[i].getSingle();
            if(result == null || result.isEmpty()) continue;
            if(result.getCount() > Math.min(64, result.getMaxStackSize()) - stack.getCount()) return false;
            if(!stack.isEmpty() && !ItemStack.isSameItemSameComponents(stack, result)) return false;
        }
        return true;
    }

    @Override
    public void setupTanks(GenericRecipe recipe) {
        super.setupTanks(recipe);
        if(recipe == null) return;
        for(int i = 0; i < inputTanks.length; i++) if(recipe.inputFluid != null && recipe.inputFluid.length > i) inputTanks[i].changeTankSize(BobMathUtil.max(inputTanks[i].getFill(), recipe.inputFluid[i].fill * 2, 4_000));
        for(int i = 0; i < outputTanks.length; i++) if(recipe.outputFluid != null && recipe.outputFluid.length > i) outputTanks[i].changeTankSize(BobMathUtil.max(outputTanks[i].getFill(), recipe.outputFluid[i].fill * 2, 4_000));
    }

    public ModuleMachineAssembler itemInput(int from) { for(int i = 0; i < inputSlots.length; i++) inputSlots[i] = from + i; return this; }
    public ModuleMachineAssembler itemOutput(int a) { outputSlots[0] = a; return this; }
    public ModuleMachineAssembler fluidInput(FluidTank a) { inputTanks[0] = a; return this; }
    public ModuleMachineAssembler fluidOutput(FluidTank a) { outputTanks[0] = a; return this; }
}
