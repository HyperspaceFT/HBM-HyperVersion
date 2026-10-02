package com.hbm.inventory.recipes;

import com.hbm.inventory.material.Mats.MaterialStack;
import com.hbm.inventory.material.NTMMaterial;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.ItemStack;

import java.util.ArrayList;
import java.util.List;

/** Crucible alloying recipe: every {@code frequency} ticks the inputs in the recipe stack become the outputs. */
public class CrucibleRecipe extends GenericRecipe {

    public MaterialStack[] input;
    public MaterialStack[] output;
    public int frequency = 1;

    public CrucibleRecipe(String name) {
        super(name);
    }

    public CrucibleRecipe setup(int frequency, ItemStack icon) {
        this.frequency = frequency;
        this.setIcon(icon);
        return this;
    }

    public CrucibleRecipe inputs(MaterialStack... input) { this.input = input; return this; }
    public CrucibleRecipe outputs(MaterialStack... output) { this.output = output; return this; }

    public int getInputAmount() {
        int content = 0;
        for(MaterialStack stack : input) content += stack.amount;
        return content;
    }

    /** Required amount of one input material, 0 if the recipe does not consume it. */
    public int getInputAmount(NTMMaterial material) {
        return getAmount(this.input, material);
    }

    public boolean hasOutput(NTMMaterial material) {
        return getAmount(this.output, material) > 0;
    }

    private static int getAmount(MaterialStack[] stacks, NTMMaterial material) {
        for(MaterialStack stack : stacks) if(stack.material == material) return stack.amount;
        return 0;
    }

    @Override
    public List<Component> print() {
        List<Component> list = new ArrayList<>();
        list.add(this.getName().withStyle(ChatFormatting.YELLOW));
        list.add(Component.translatable("container.recipe.input").append(":").withStyle(ChatFormatting.BOLD));
        for(MaterialStack stack : input) list.add(line(stack));
        list.add(Component.translatable("container.recipe.output").append(":").withStyle(ChatFormatting.BOLD));
        for(MaterialStack stack : output) list.add(line(stack));
        return list;
    }

    // Upstream formats amounts as blocks/ingots/nuggets; NEO's crucible shows quanta since Goal 5A.
    private static Component line(MaterialStack stack) {
        return Component.literal("  ").append(Component.translatable("container.machine_crucible.amount",
                stack.material.getName(), stack.amount)).withStyle(ChatFormatting.GRAY);
    }
}
