package com.hbm.handler.jei;

import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.recipes.RotaryFurnaceRecipes;
import com.hbm.inventory.recipes.RotaryFurnaceRecipes.RotaryFurnaceRecipe;
import com.hbm.items.CopperScrapsItem;
import com.hbm.items.machine.FluidIconItem;
import com.hbm.main.NuclearTechMod;
import mezz.jei.api.gui.builder.IRecipeLayoutBuilder;
import mezz.jei.api.gui.drawable.IDrawable;
import mezz.jei.api.helpers.IGuiHelper;
import mezz.jei.api.recipe.IFocusGroup;
import mezz.jei.api.recipe.RecipeType;
import mezz.jei.api.recipe.category.IRecipeCategory;
import net.minecraft.network.chat.Component;

import java.util.List;

public class RotaryFurnaceRecipeHandler implements IRecipeCategory<RotaryFurnaceRecipe> {

    public static final RecipeType<RotaryFurnaceRecipe> RECIPE_TYPE = RecipeType.create(
            NuclearTechMod.MODID,
            "rotary_furnace",
            RotaryFurnaceRecipe.class
    );

    private static final String TEXTURE = "textures/gui/jei/gui_nei.png";

    private final IDrawable background;
    private final IDrawable icon;

    public RotaryFurnaceRecipeHandler(IGuiHelper guiHelper) {
        this.background = guiHelper.drawableBuilder(
                NuclearTechMod.withDefaultNamespace(TEXTURE),
                5, 11, 166, 65
        ).setTextureSize(256, 256).build();
        this.icon = guiHelper.createDrawableItemLike(NtmBlocks.MACHINE_ROTARY_FURNACE.asItem());
    }

    public static List<RotaryFurnaceRecipe> getRecipes() {
        return List.copyOf(RotaryFurnaceRecipes.recipes);
    }

    @Override public RecipeType<RotaryFurnaceRecipe> getRecipeType() { return RECIPE_TYPE; }
    @Override public Component getTitle() { return Component.translatable("container.machineRotaryFurnace"); }
    @Override public IDrawable getBackground() { return this.background; }
    @Override public IDrawable getIcon() { return this.icon; }

    /** As the original getRecipes: the ingredients, the fluid last, and the product as a molten scrap icon. */
    @Override
    public void setRecipe(IRecipeLayoutBuilder builder, RotaryFurnaceRecipe recipe, IFocusGroup focuses) {
        int slot = 0;

        for(AStack ingredient : recipe.ingredients) {
            builder.addInputSlot(30 + slot % 2 * 18, 15 + slot / 2 * 18)
                    .setStandardSlotBackground()
                    .addItemStacks(ingredient.extractForJEI());
            slot++;
        }

        if(recipe.fluid != null) {
            builder.addInputSlot(30 + slot % 2 * 18, 15 + slot / 2 * 18)
                    .setStandardSlotBackground()
                    .addItemStack(FluidIconItem.make(recipe.fluid));
        }

        builder.addOutputSlot(102, 24)
                .setStandardSlotBackground()
                .addItemStack(CopperScrapsItem.create(recipe.output, true));
    }
}
