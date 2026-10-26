package com.hbm.handler.jei;

import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.recipes.CopperCastingRecipes;
import com.hbm.main.NuclearTechMod;
import mezz.jei.api.gui.builder.IRecipeLayoutBuilder;
import mezz.jei.api.gui.drawable.IDrawable;
import mezz.jei.api.helpers.IGuiHelper;
import mezz.jei.api.recipe.IFocusGroup;
import mezz.jei.api.recipe.RecipeIngredientRole;
import mezz.jei.api.recipe.RecipeType;
import mezz.jei.api.recipe.category.IRecipeCategory;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.ItemStack;

/**
 * Upstream NEI "Crucible Smelting" (CrucibleSmeltingHandler): which items melt into which materials, shown as liquid scraps.
 * One recipe per material shape group, then the fixed tag and item entries of hbmCrucibleSmelting.json.
 */
public class CrucibleSmeltingRecipeHandler implements IRecipeCategory<CopperCastingRecipes.SmeltingRecipe> {

    public static final RecipeType<CopperCastingRecipes.SmeltingRecipe> RECIPE_TYPE = RecipeType.create(
            NuclearTechMod.MODID,
            "crucible_smelting",
            CopperCastingRecipes.SmeltingRecipe.class
    );

    private static final String TEXTURE = "textures/gui/jei/gui_nei_crucible_smelting.png";

    private final IDrawable background;
    private final IDrawable icon;

    public CrucibleSmeltingRecipeHandler(IGuiHelper guiHelper) {
        this.background = guiHelper.drawableBuilder(
                NuclearTechMod.withDefaultNamespace(TEXTURE),
                5, 11, 166, 65
        ).setTextureSize(256, 256).build();
        this.icon = guiHelper.createDrawableItemLike(NtmBlocks.MACHINE_CRUCIBLE.asItem());
    }

    @Override public RecipeType<CopperCastingRecipes.SmeltingRecipe> getRecipeType() { return RECIPE_TYPE; }
    @Override public Component getTitle() { return Component.translatable("container.machine_crucible.jei.smelting"); }
    @Override public IDrawable getBackground() { return this.background; }
    @Override public IDrawable getIcon() { return this.icon; }

    @Override
    public void setRecipe(IRecipeLayoutBuilder builder, CopperCastingRecipes.SmeltingRecipe recipe, IFocusGroup focuses) {
        builder.addInputSlot(48, 24).addItemStacks(recipe.inputs());
        builder.addSlot(RecipeIngredientRole.CATALYST, 75, 42).addItemStack(new ItemStack(NtmBlocks.MACHINE_CRUCIBLE.asItem()));
        for(int i = 0; i < recipe.outputs().size(); i++) {
            builder.addOutputSlot(102 + (i % 3) * 18, 6 + (i / 3) * 18)
                    .addItemStack(CrucibleAlloyingRecipeHandler.liquid(recipe.outputs().get(i)));
        }
    }
}
