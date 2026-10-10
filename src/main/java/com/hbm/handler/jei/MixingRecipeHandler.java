package com.hbm.handler.jei;

import com.hbm.blocks.NtmBlocks;
import com.hbm.handler.MixerRecipeClientSync;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.recipes.MixerRecipes;
import com.hbm.inventory.recipes.MixerRecipes.MixerRecipe;
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

public class MixingRecipeHandler implements IRecipeCategory<MixingRecipeHandler.MixerJeiRecipe> {
    public static final RecipeType<MixerJeiRecipe> RECIPE_TYPE = RecipeType.create(NuclearTechMod.MODID,"mixing",MixerJeiRecipe.class);
    private final IDrawable background;
    private final IDrawable icon;
    public MixingRecipeHandler(IGuiHelper helper) {
        background = helper.drawableBuilder(NuclearTechMod.withDefaultNamespace("textures/gui/jei/gui_nei.png"),5,11,166,65).setTextureSize(256,256).build();
        icon = helper.createDrawableItemLike(NtmBlocks.MACHINE_MIXER.asItem());
    }
    public static List<MixerJeiRecipe> getRecipes() {
        List<MixerJeiRecipe> result = new ArrayList<>();
        for(var entry : MixerRecipeClientSync.getRecipes().entrySet())
            for(MixerRecipe recipe : entry.getValue()) result.add(new MixerJeiRecipe(entry.getKey(),recipe));
        return result;
    }
    @Override public RecipeType<MixerJeiRecipe> getRecipeType() { return RECIPE_TYPE; }
    @Override public Component getTitle() { return Component.translatable("block.hbmsntm.machine_mixer"); }
    @Override public IDrawable getBackground() { return background; }
    @Override public IDrawable getIcon() { return icon; }
    @Override public void setRecipe(IRecipeLayoutBuilder builder, MixerJeiRecipe row, IFocusGroup focuses) {
        MixerRecipe recipe = row.recipe();
        if(recipe.input1() != null) builder.addInputSlot(12,20).setStandardSlotBackground().addItemStack(FluidIconItem.make(recipe.input1()));
        if(recipe.input2() != null) builder.addInputSlot(30,20).setStandardSlotBackground().addItemStack(FluidIconItem.make(recipe.input2()));
        if(recipe.solidInput() != null) builder.addInputSlot(48,20).setStandardSlotBackground().addItemStacks(recipe.solidInput().extractForJEI());
        builder.addOutputSlot(120,20).setStandardSlotBackground().addItemStack(FluidIconItem.make(new FluidStack(row.outputType(),recipe.output())))
                .addRichTooltipCallback((slot,tooltip) -> tooltip.add(Component.translatable("container.machine_mixer.jei.config")));
    }
    @Override public void draw(MixerJeiRecipe row, IRecipeSlotsView slots, GuiGraphics graphics, double mouseX, double mouseY) {
        var font = Minecraft.getInstance().font;
        Component time = Component.translatable("container.machine_mixer.jei.duration",row.recipe().processTime());
        graphics.drawString(font,time,(166-font.width(time))/2,46,0x404040,false);
    }
    public record MixerJeiRecipe(FluidType outputType, MixerRecipe recipe) {
        /** Match every visible value; retained hidden JEI rows can be reused after reconnect. */
        public boolean sameRecipe(MixerJeiRecipe other) {
            if(outputType != other.outputType || recipe.output() != other.recipe.output() || recipe.processTime() != other.recipe.processTime()
                    || !sameFluid(recipe.input1(),other.recipe.input1()) || !sameFluid(recipe.input2(),other.recipe.input2())) return false;
            var solid = recipe.solidInput();
            var otherSolid = other.recipe.solidInput();
            return solid == null ? otherSolid == null : otherSolid != null
                    && ((MixerRecipes.SolidInput)solid).toJson().equals(((MixerRecipes.SolidInput)otherSolid).toJson());
        }
        private static boolean sameFluid(FluidStack first, FluidStack second) {
            return first == null ? second == null : second != null && first.type == second.type && first.fill == second.fill && first.pressure == second.pressure;
        }
    }
}
