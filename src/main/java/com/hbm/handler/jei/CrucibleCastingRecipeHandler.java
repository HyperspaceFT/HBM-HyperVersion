package com.hbm.handler.jei;

import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.material.Mats;
import com.hbm.inventory.material.NTMMaterial;
import com.hbm.inventory.recipes.CopperCastingRecipes;
import com.hbm.items.NtmItems;
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

import java.util.ArrayList;
import java.util.List;

/** Upstream NEI "Crucible Casting": existing plates and the mixer prerequisite Dura ingot. */
public class CrucibleCastingRecipeHandler implements IRecipeCategory<CrucibleCastingRecipeHandler.Casting> {

    public record Casting(NTMMaterial material, boolean ingot) {
        public Casting(NTMMaterial material) { this(material, false); }
    }

    public static final RecipeType<Casting> RECIPE_TYPE = RecipeType.create(
            NuclearTechMod.MODID,
            "crucible_casting",
            Casting.class
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

    public static List<Casting> getRecipes() {
        List<Casting> recipes = new ArrayList<>();
        for(NTMMaterial material : CopperCastingRecipes.getCastableMaterials()) recipes.add(new Casting(material));
        recipes.add(new Casting(Mats.MAT_DURA, true));
        return recipes;
    }

    @Override public RecipeType<Casting> getRecipeType() { return RECIPE_TYPE; }
    @Override public Component getTitle() { return Component.translatable("container.machine_crucible.jei.casting"); }
    @Override public IDrawable getBackground() { return this.background; }
    @Override public IDrawable getIcon() { return this.icon; }

    @Override
    public void setRecipe(IRecipeLayoutBuilder builder, Casting recipe, IFocusGroup focuses) {
        builder.addInputSlot(48, 24).addItemStack(CrucibleAlloyingRecipeHandler.liquid(
                new Mats.MaterialStack(recipe.material(), recipe.ingot() ? CopperCastingRecipes.INGOT_QUANTA : CopperCastingRecipes.PLATE_QUANTA)));
        builder.addSlot(RecipeIngredientRole.CATALYST, 75, 6).addItemStack(new ItemStack(recipe.ingot() ? NtmItems.MOLD_INGOT.get() : NtmItems.MOLD_PLATE_CAST.get()));
        builder.addSlot(RecipeIngredientRole.CATALYST, 75, 42).addItemStack(new ItemStack(NtmBlocks.FOUNDRY_MOLD.asItem()));
        builder.addOutputSlot(102, 24).addItemStack(recipe.ingot() ? new ItemStack(NtmItems.INGOT_DURA_STEEL.get()) : CopperCastingRecipes.getPlate(recipe.material()));
    }
}
