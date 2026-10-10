package com.hbm.handler.jei;

import com.hbm.blocks.NtmBlocks;
import com.hbm.handler.CompressorRecipeClientSync;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.recipes.CompressorRecipes.RecipeKey;
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
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;

import java.util.ArrayList;
import java.util.List;

public class CompressorRecipeHandler implements IRecipeCategory<CompressorRecipeHandler.CompressorJeiRecipe> {

    public static final RecipeType<CompressorJeiRecipe> RECIPE_TYPE = RecipeType.create(NuclearTechMod.MODID, "compressor", CompressorJeiRecipe.class);
    private final IDrawable background;
    private final IDrawable icon;

    public CompressorRecipeHandler(IGuiHelper guiHelper) {
        this.background = guiHelper.drawableBuilder(NuclearTechMod.withDefaultNamespace("textures/gui/jei/gui_nei.png"), 5, 11, 166, 65).setTextureSize(256, 256).build();
        this.icon = guiHelper.createDrawableItemLike(NtmBlocks.MACHINE_COMPRESSOR.asItem());
    }

    public static List<CompressorJeiRecipe> getRecipes() {
        List<CompressorJeiRecipe> rows = new ArrayList<>();
        var table = CompressorRecipeClientSync.getRecipes();
        for(var entry : table.entrySet()) {
            var value = entry.getValue();
            rows.add(new CompressorJeiRecipe(entry.getKey().inputType(), value.inputAmount(), entry.getKey().inputPressure(),
                    value.outputType(), value.outputAmount(), value.outputPressure(), value.duration(), false));
        }
        // One survival-chain example explains the generic rule without pretending to enumerate every fluid.
        if(!table.containsKey(new RecipeKey(Fluids.LIGHTOIL_CRACK, 0))) {
            rows.add(new CompressorJeiRecipe(Fluids.LIGHTOIL_CRACK, 1000, 0, Fluids.LIGHTOIL_CRACK, 1000, 1, 100, true));
        }
        return rows;
    }

    @Override public RecipeType<CompressorJeiRecipe> getRecipeType() { return RECIPE_TYPE; }
    @Override public Component getTitle() { return Component.translatable("block.hbmsntm.machine_compressor"); }
    @Override public IDrawable getBackground() { return this.background; }
    @Override public IDrawable getIcon() { return this.icon; }

    @Override
    public void setRecipe(IRecipeLayoutBuilder builder, CompressorJeiRecipe recipe, IFocusGroup focuses) {
        builder.addInputSlot(48, 24).setStandardSlotBackground().addItemStack(FluidIconItem.make(new FluidStack(recipe.inputType(), recipe.inputAmount(), recipe.inputPressure())))
                .addRichTooltipCallback((slot, tooltip) -> {
                    tooltip.add(Component.translatable("container.machine_compressor.jei.pressure", recipe.inputPressure()));
                    tooltip.add(Component.translatable("container.machine_compressor.jei.generic"));
                    if(recipe.generic()) tooltip.add(Component.translatable("container.machine_compressor.jei.example"));
                });
        builder.addOutputSlot(102, 24).setStandardSlotBackground().addItemStack(FluidIconItem.make(new FluidStack(recipe.outputType(), recipe.outputAmount(), recipe.outputPressure())))
                .addRichTooltipCallback((slot, tooltip) -> tooltip.add(Component.translatable("container.machine_compressor.jei.pressure", recipe.outputPressure())));
    }

    @Override
    public void draw(CompressorJeiRecipe recipe, IRecipeSlotsView slots, GuiGraphics graphics, double mouseX, double mouseY) {
        var font = Minecraft.getInstance().font;
        Component duration = Component.translatable("container.machine_compressor.jei.duration", recipe.duration());
        graphics.drawString(font, duration, (166 - font.width(duration)) / 2, 49, 0x404040, false);
    }

    public record CompressorJeiRecipe(FluidType inputType, int inputAmount, int inputPressure,
                                      FluidType outputType, int outputAmount, int outputPressure, int duration, boolean generic) { }
}
