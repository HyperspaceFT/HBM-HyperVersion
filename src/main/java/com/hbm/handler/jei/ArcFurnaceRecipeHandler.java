package com.hbm.handler.jei;

import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.recipes.ArcFurnaceRecipes.ArcFurnaceRecipe;
import com.hbm.main.NuclearTechMod;
import mezz.jei.api.gui.builder.IRecipeLayoutBuilder;
import mezz.jei.api.gui.drawable.IDrawable;
import mezz.jei.api.helpers.IGuiHelper;
import mezz.jei.api.recipe.IFocusGroup;
import mezz.jei.api.recipe.RecipeType;
import mezz.jei.api.recipe.category.IRecipeCategory;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.ItemStack;

import java.util.List;

/** Original ArcFurnaceSolidHandler; the liquid category is not ported (Goal 13B B1). */
public class ArcFurnaceRecipeHandler implements IRecipeCategory<ArcFurnaceRecipe> {

    public static final RecipeType<ArcFurnaceRecipe> RECIPE_TYPE = RecipeType.create(NuclearTechMod.MODID, "arc_furnace", ArcFurnaceRecipe.class);
    private static final ItemStack MACHINE_STACK = new ItemStack(NtmBlocks.MACHINE_ARC_FURNACE.asItem());

    private final IDrawable background;
    private final IDrawable icon;

    public ArcFurnaceRecipeHandler(IGuiHelper guiHelper) {
        this.background = guiHelper.drawableBuilder(NuclearTechMod.withDefaultNamespace("textures/gui/jei/gui_nei.png"), 5, 11, 166, 65).setTextureSize(256, 256).build();
        this.icon = guiHelper.createDrawableItemLike(NtmBlocks.MACHINE_ARC_FURNACE.asItem());
    }

    @Override public RecipeType<ArcFurnaceRecipe> getRecipeType() { return RECIPE_TYPE; }
    @Override public Component getTitle() { return Component.translatable("block.hbmsntm.machine_arc_furnace"); }
    @Override public IDrawable getBackground() { return this.background; }
    @Override public IDrawable getIcon() { return this.icon; }

    /** Slot positions of the original universal NEI handler for one input and one output. */
    @Override
    public void setRecipe(IRecipeLayoutBuilder builder, ArcFurnaceRecipe recipe, IFocusGroup focuses) {
        List<ItemStack> inputs = recipe.input.extractForJEI();
        var input = builder.addInputSlot(48, 24).setStandardSlotBackground();
        if(!inputs.isEmpty()) input.addItemStacks(inputs);

        builder.addInputSlot(74, 31).addItemStack(MACHINE_STACK.copy()).setStandardSlotBackground();
        builder.addOutputSlot(102, 24).addItemStack(recipe.solidOutput.copy()).setStandardSlotBackground();
    }
}
