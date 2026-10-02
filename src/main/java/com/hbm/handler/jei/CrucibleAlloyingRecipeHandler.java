package com.hbm.handler.jei;

import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.material.Mats.MaterialStack;
import com.hbm.inventory.recipes.CrucibleRecipe;
import com.hbm.items.CopperScrapsItem;
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

/** Upstream NEI "Crucible Alloying": materials are shown as liquid scraps. Recipes are only selected in the crucible GUI. */
public class CrucibleAlloyingRecipeHandler implements IRecipeCategory<CrucibleRecipe> {

    public static final RecipeType<CrucibleRecipe> RECIPE_TYPE = RecipeType.create(
            NuclearTechMod.MODID,
            "crucible_alloying",
            CrucibleRecipe.class
    );

    private static final String TEXTURE = "textures/gui/jei/gui_nei_crucible.png";

    private final IDrawable background;
    private final IDrawable icon;

    public CrucibleAlloyingRecipeHandler(IGuiHelper guiHelper) {
        this.background = guiHelper.drawableBuilder(
                NuclearTechMod.withDefaultNamespace(TEXTURE),
                5, 11, 166, 65
        ).setTextureSize(256, 256).build();
        this.icon = guiHelper.createDrawableItemLike(NtmBlocks.MACHINE_CRUCIBLE.asItem());
    }

    @Override public RecipeType<CrucibleRecipe> getRecipeType() { return RECIPE_TYPE; }
    @Override public Component getTitle() { return Component.translatable("container.machine_crucible.jei.alloying"); }
    @Override public IDrawable getBackground() { return this.background; }
    @Override public IDrawable getIcon() { return this.icon; }

    @Override
    public void setRecipe(IRecipeLayoutBuilder builder, CrucibleRecipe recipe, IFocusGroup focuses) {
        for(int i = 0; i < recipe.input.length; i++) {
            builder.addInputSlot(12 + (i % 3) * 18, 6 + (i / 3) * 18)
                    .addItemStack(liquid(recipe.input[i]));
        }

        builder.addSlot(RecipeIngredientRole.CATALYST, 75, 42)
                .addItemStack(new ItemStack(NtmBlocks.MACHINE_CRUCIBLE.asItem()))
                .addRichTooltipCallback((slotView, tooltip) ->
                        tooltip.add(Component.translatable("container.machine_crucible.jei.select_hint", recipe.frequency)));

        for(int i = 0; i < recipe.output.length; i++) {
            builder.addOutputSlot(102 + (i % 3) * 18, 6 + (i / 3) * 18)
                    .addItemStack(liquid(recipe.output[i]));
        }
    }

    static ItemStack liquid(MaterialStack stack) {
        return CopperScrapsItem.create(stack, true);
    }
}
