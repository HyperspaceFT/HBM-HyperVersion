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

/** Upstream NEI "Crucible Smelting": which items melt into which material, from the explicit melt table. */
public class CrucibleSmeltingRecipeHandler implements IRecipeCategory<CopperCastingRecipes.MeltEntry> {

    public static final RecipeType<CopperCastingRecipes.MeltEntry> RECIPE_TYPE = RecipeType.create(
            NuclearTechMod.MODID,
            "crucible_smelting",
            CopperCastingRecipes.MeltEntry.class
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

    @Override public RecipeType<CopperCastingRecipes.MeltEntry> getRecipeType() { return RECIPE_TYPE; }
    @Override public Component getTitle() { return Component.translatable("container.machine_crucible.jei.smelting"); }
    @Override public IDrawable getBackground() { return this.background; }
    @Override public IDrawable getIcon() { return this.icon; }

    @Override
    public void setRecipe(IRecipeLayoutBuilder builder, CopperCastingRecipes.MeltEntry recipe, IFocusGroup focuses) {
        builder.addInputSlot(48, 24).addItemStack(new ItemStack(recipe.item()));
        builder.addSlot(RecipeIngredientRole.CATALYST, 75, 42).addItemStack(new ItemStack(NtmBlocks.MACHINE_CRUCIBLE.asItem()));
        builder.addOutputSlot(102, 6).addItemStack(CrucibleAlloyingRecipeHandler.liquid(recipe.result()));
    }
}
