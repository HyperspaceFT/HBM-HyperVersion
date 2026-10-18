package com.hbm.handler.jei;

import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.items.machine.FluidIconItem;
import com.hbm.main.NuclearTechMod;
import mezz.jei.api.gui.builder.IRecipeLayoutBuilder;
import mezz.jei.api.gui.drawable.IDrawable;
import mezz.jei.api.gui.ingredient.IRecipeSlotsView;
import mezz.jei.api.helpers.IGuiHelper;
import mezz.jei.api.recipe.IFocusGroup;
import mezz.jei.api.recipe.RecipeType;
import mezz.jei.api.recipe.category.IRecipeCategory;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;

import java.util.Arrays;
import java.util.Locale;

/** PUREX rows on the machine's GUI texture: inputs and tanks as in MachinePUREXMenu, duration and consumption under the outputs. */
public class PUREXRecipeHandler implements IRecipeCategory<GenericRecipe> {

    public static final RecipeType<GenericRecipe> RECIPE_TYPE = RecipeType.create(
            NuclearTechMod.MODID,
            "purex",
            GenericRecipe.class
    );

    private final IDrawable background;
    private final IDrawable icon;

    public PUREXRecipeHandler(IGuiHelper guiHelper) {
        this.background = guiHelper.drawableBuilder(
                NuclearTechMod.withDefaultNamespace("textures/gui/processing/gui_purex.png"),
                0, 0, 176, 141
        ).setTextureSize(256, 256).build();
        this.icon = guiHelper.createDrawableItemLike(NtmBlocks.MACHINE_PUREX.asItem());
    }

    @Override public RecipeType<GenericRecipe> getRecipeType() { return RECIPE_TYPE; }
    @Override public Component getTitle() { return Component.translatable("container.machinePUREX"); }
    @Override public IDrawable getBackground() { return this.background; }
    @Override public IDrawable getIcon() { return this.icon; }

    @Override
    public void setRecipe(IRecipeLayoutBuilder builder, GenericRecipe recipe, IFocusGroup focuses) {
        if(recipe.inputItem != null) {
            for(int i = 0; i < Math.min(recipe.inputItem.length, 3); i++) {
                builder.addInputSlot(8 + i * 18, 90).setStandardSlotBackground().addItemStacks(recipe.inputItem[i].extractForJEI());
            }
        }
        if(recipe.outputItem != null) {
            for(int i = 0; i < Math.min(recipe.outputItem.length, 6); i++) {
                builder.addOutputSlot(80 + (i % 2) * 18, 36 + (i / 2) * 18).setOutputSlotBackground().addItemStacks(Arrays.asList(recipe.outputItem[i].getAllPossibilities()));
            }
        }
        if(recipe.inputFluid != null) {
            for(int i = 0; i < Math.min(recipe.inputFluid.length, 3); i++) {
                addFluidSlot(builder, 8 + i * 18, 36, recipe.inputFluid[i], true);
            }
        }
        if(recipe.outputFluid != null && recipe.outputFluid.length > 0) {
            addFluidSlot(builder, 116, 54, recipe.outputFluid[0], false);
        }
    }

    @Override
    public void draw(GenericRecipe recipe, IRecipeSlotsView recipeSlotsView, GuiGraphics guiGraphics, double mouseX, double mouseY) {
        Font font = Minecraft.getInstance().font;
        String duration = String.format(Locale.US, "%,d", recipe.duration) + " ticks";
        String consumption = String.format(Locale.US, "%,d", recipe.power) + " HE/t";
        guiGraphics.drawString(font, duration, 140 - font.width(duration), 110, 0x404040, false);
        guiGraphics.drawString(font, consumption, 66, 130, 0xFFFFFF, false);
    }

    private static void addFluidSlot(IRecipeLayoutBuilder builder, int x, int y, FluidStack stack, boolean input) {
        var slot = input ? builder.addInputSlot(x, y) : builder.addOutputSlot(x, y);
        slot.setStandardSlotBackground().addItemStack(FluidIconItem.make(stack));
    }
}
