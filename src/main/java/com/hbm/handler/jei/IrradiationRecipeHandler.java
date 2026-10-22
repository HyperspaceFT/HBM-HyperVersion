package com.hbm.handler.jei;

import com.hbm.blocks.NtmBlocks;
import com.hbm.handler.OutgasserRecipeClientSync;
import com.hbm.inventory.recipes.OutgasserRecipes.OutgasserRecipe;
import com.hbm.items.machine.FluidIconItem;
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

import java.util.ArrayList;
import java.util.List;

/**
 * Irradiation channel rows in the layout of the original NEI OutgasserHandler (NEIUniversalHandler): input, channel, then the solid
 * output and the gas (as its fluid icon). The title is the channel's name, as the original. The original also lists the fusion
 * breeder as a machine; it is not ported, so its fusionOnly rows are not shown.
 */
public class IrradiationRecipeHandler implements IRecipeCategory<OutgasserRecipe> {
    public static final RecipeType<OutgasserRecipe> RECIPE_TYPE = RecipeType.create(NuclearTechMod.MODID, "irradiation", OutgasserRecipe.class);
    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/jei/gui_nei.png");
    private final IDrawable background;
    private final IDrawable icon;

    public IrradiationRecipeHandler(IGuiHelper helper) {
        background = helper.drawableBuilder(TEXTURE, 5, 11, 166, 65).setTextureSize(256, 256).build();
        icon = helper.createDrawableItemLike(NtmBlocks.RBMK_OUTGASSER.asItem());
    }
    public static List<OutgasserRecipe> getRecipes() {
        List<OutgasserRecipe> rows = new ArrayList<>();
        for(OutgasserRecipe recipe : OutgasserRecipeClientSync.getRecipes()) if(!recipe.fusionOnly) rows.add(recipe);
        return rows;
    }

    @Override public RecipeType<OutgasserRecipe> getRecipeType() { return RECIPE_TYPE; }
    @Override public Component getTitle() { return Component.translatable(NtmBlocks.RBMK_OUTGASSER.get().getDescriptionId()); }
    @Override public IDrawable getBackground() { return background; }
    @Override public IDrawable getIcon() { return icon; }
    @Override public void setRecipe(IRecipeLayoutBuilder builder, OutgasserRecipe recipe, IFocusGroup focuses) {
        builder.addInputSlot(48, 24).setStandardSlotBackground().addItemStacks(recipe.input.extractForJEI());
        int x = 102;
        if(recipe.hasSolidOutput()) {
            builder.addOutputSlot(x, 24).setStandardSlotBackground().addItemStack(recipe.solidOutput());
            x += 18;
        }
        if(recipe.fluidOutput != null) {
            builder.addOutputSlot(x, 24).setStandardSlotBackground().addItemStack(FluidIconItem.make(recipe.fluidOutput));
        }
        builder.addSlot(RecipeIngredientRole.CATALYST, 75, 31).addItemStack(new ItemStack(NtmBlocks.RBMK_OUTGASSER.asItem()));
    }
    // The arrow with the machine slot below it (NEIUniversalHandler.drawBackground).
    @Override public void draw(OutgasserRecipe recipe, IRecipeSlotsView slots, GuiGraphics graphics, double mouseX, double mouseY) {
        graphics.blit(TEXTURE, 74, 14, 59, 87, 18, 36, 256, 256);
    }
}
