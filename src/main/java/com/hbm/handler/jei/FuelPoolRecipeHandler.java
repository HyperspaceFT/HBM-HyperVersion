package com.hbm.handler.jei;

import com.hbm.blocks.NtmBlocks;
import com.hbm.handler.FuelPoolRecipeClientSync;
import com.hbm.inventory.recipes.FuelPoolRecipes.FuelPoolRecipe;
import com.hbm.main.NuclearTechMod;
import mezz.jei.api.gui.builder.IRecipeLayoutBuilder;
import mezz.jei.api.gui.drawable.IDrawable;
import mezz.jei.api.gui.ingredient.IRecipeSlotsView;
import mezz.jei.api.helpers.IGuiHelper;
import mezz.jei.api.recipe.IFocusGroup;
import mezz.jei.api.recipe.RecipeIngredientRole;
import mezz.jei.api.recipe.RecipeType;
import mezz.jei.api.recipe.category.IRecipeCategory;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;

import java.util.List;

/** Spent fuel pool drum rows in the layout of the original NEI FuelPoolHandler (NEIUniversalHandler): input, drum, output. */
public class FuelPoolRecipeHandler implements IRecipeCategory<FuelPoolRecipe> {
    public static final RecipeType<FuelPoolRecipe> RECIPE_TYPE = RecipeType.create(NuclearTechMod.MODID, "fuel_pool", FuelPoolRecipe.class);
    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/jei/gui_nei.png");
    private final IDrawable background;
    private final IDrawable icon;

    public FuelPoolRecipeHandler(IGuiHelper helper) {
        background = helper.drawableBuilder(TEXTURE, 5, 11, 166, 65).setTextureSize(256, 256).build();
        icon = helper.createDrawableItemLike(NtmBlocks.MACHINE_WASTE_DRUM.asItem());
    }
    public static List<FuelPoolRecipe> getRecipes() { return FuelPoolRecipeClientSync.getRecipes(); }
    @Override public RecipeType<FuelPoolRecipe> getRecipeType() { return RECIPE_TYPE; }
    @Override public Component getTitle() { return Component.translatable("container.machine_waste_drum"); }
    @Override public IDrawable getBackground() { return background; }
    @Override public IDrawable getIcon() { return icon; }
    @Override public void setRecipe(IRecipeLayoutBuilder builder, FuelPoolRecipe recipe, IFocusGroup focuses) {
        builder.addInputSlot(48, 24).setStandardSlotBackground().addItemStack(recipe.input());
        builder.addOutputSlot(102, 24).setStandardSlotBackground().addItemStack(recipe.output());
        builder.addSlot(RecipeIngredientRole.CATALYST, 75, 31).addItemStack(new ItemStack(NtmBlocks.MACHINE_WASTE_DRUM.asItem()));
    }
    // The arrow with the machine slot below it (NEIUniversalHandler.drawBackground).
    @Override public void draw(FuelPoolRecipe recipe, IRecipeSlotsView slots, GuiGraphics graphics, double mouseX, double mouseY) {
        graphics.blit(TEXTURE, 74, 14, 59, 87, 18, 36, 256, 256);
    }
}
