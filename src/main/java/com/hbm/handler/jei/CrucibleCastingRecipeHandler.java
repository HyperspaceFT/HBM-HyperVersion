package com.hbm.handler.jei;

import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.material.Mats;
import com.hbm.items.machine.MoldItem;
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

import java.util.List;

/**
 * Upstream NEI "Crucible Casting": one row per mold and material the mold casts ({@link MoldItem#castingRows()}), with the mold and
 * the casting block it fits (foundry_mold for small molds, foundry_basin for large ones) as catalysts.
 */
public class CrucibleCastingRecipeHandler implements IRecipeCategory<MoldItem.CastingRow> {

    public static final RecipeType<MoldItem.CastingRow> RECIPE_TYPE = RecipeType.create(
            NuclearTechMod.MODID,
            "crucible_casting",
            MoldItem.CastingRow.class
    );

    private static final String TEXTURE = "textures/gui/jei/gui_nei_foundry.png";

    private final IDrawable background;
    private final IDrawable icon;

    public CrucibleCastingRecipeHandler(IGuiHelper guiHelper) {
        this.background = guiHelper.drawableBuilder(
                NuclearTechMod.withDefaultNamespace(TEXTURE),
                5, 11, 166, 65
        ).setTextureSize(256, 256).build();
        this.icon = guiHelper.createDrawableItemLike(NtmBlocks.FOUNDRY_MOLD.asItem());
    }

    public static List<MoldItem.CastingRow> getRecipes() {
        return MoldItem.castingRows();
    }

    @Override public RecipeType<MoldItem.CastingRow> getRecipeType() { return RECIPE_TYPE; }
    @Override public Component getTitle() { return Component.translatable("container.machine_crucible.jei.casting"); }
    @Override public IDrawable getBackground() { return this.background; }
    @Override public IDrawable getIcon() { return this.icon; }

    @Override
    public void setRecipe(IRecipeLayoutBuilder builder, MoldItem.CastingRow recipe, IFocusGroup focuses) {
        builder.addInputSlot(48, 24).addItemStack(CrucibleAlloyingRecipeHandler.liquid(new Mats.MaterialStack(recipe.material(), recipe.cost())));
        builder.addSlot(RecipeIngredientRole.CATALYST, 75, 6).addItemStack(MoldItem.stackOf(recipe.mold()));
        builder.addSlot(RecipeIngredientRole.CATALYST, 75, 42).addItemStack(new ItemStack(
                recipe.mold().size == MoldItem.SIZE_LARGE ? NtmBlocks.FOUNDRY_BASIN.asItem() : NtmBlocks.FOUNDRY_MOLD.asItem()));
        builder.addOutputSlot(102, 24).addItemStack(recipe.output().copy());
    }
}
