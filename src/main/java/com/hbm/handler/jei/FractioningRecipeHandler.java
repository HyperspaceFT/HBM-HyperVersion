package com.hbm.handler.jei;

import com.hbm.blocks.NtmBlocks;
import com.hbm.handler.FractionRecipeClientSync;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.items.machine.FluidIconItem;
import com.hbm.main.NuclearTechMod;
import mezz.jei.api.gui.builder.IRecipeLayoutBuilder;
import mezz.jei.api.gui.drawable.IDrawable;
import mezz.jei.api.helpers.IGuiHelper;
import mezz.jei.api.recipe.IFocusGroup;
import mezz.jei.api.recipe.RecipeType;
import mezz.jei.api.recipe.category.IRecipeCategory;
import net.minecraft.network.chat.Component;

import java.util.ArrayList;
import java.util.List;

public class FractioningRecipeHandler implements IRecipeCategory<FractioningRecipeHandler.FractionRecipe> {

    public static final RecipeType<FractionRecipe> RECIPE_TYPE = RecipeType.create(NuclearTechMod.MODID, "fractioning", FractionRecipe.class);
    private final IDrawable background;
    private final IDrawable icon;

    public FractioningRecipeHandler(IGuiHelper guiHelper) {
        this.background = guiHelper.drawableBuilder(NuclearTechMod.withDefaultNamespace("textures/gui/jei/gui_nei.png"), 5, 11, 166, 65).setTextureSize(256, 256).build();
        this.icon = guiHelper.createDrawableItemLike(NtmBlocks.MACHINE_FRACTION_TOWER.asItem());
    }

    public static List<FractionRecipe> getRecipes() {
        List<FractionRecipe> recipes = new ArrayList<>();
        for(var entry : FractionRecipeClientSync.getRecipes().entrySet()) {
            recipes.add(new FractionRecipe(entry.getKey(), entry.getValue().getKey(), entry.getValue().getValue()));
        }
        return recipes;
    }

    @Override public RecipeType<FractionRecipe> getRecipeType() { return RECIPE_TYPE; }
    @Override public Component getTitle() { return Component.translatable("block.hbmsntm.machine_fraction_tower"); }
    @Override public IDrawable getBackground() { return this.background; }
    @Override public IDrawable getIcon() { return this.icon; }

    @Override
    public void setRecipe(IRecipeLayoutBuilder builder, FractionRecipe recipe, IFocusGroup focuses) {
        builder.addInputSlot(48, 24).setStandardSlotBackground().addItemStack(FluidIconItem.make(recipe.input, 100));
        builder.addOutputSlot(102, 24).setStandardSlotBackground().addItemStack(FluidIconItem.make(recipe.output1));
        builder.addOutputSlot(120, 24).setStandardSlotBackground().addItemStack(FluidIconItem.make(recipe.output2));
    }

    public record FractionRecipe(FluidType input, FluidStack output1, FluidStack output2) { }
}
