package com.hbm.handler.jei;

import com.hbm.blocks.NtmBlocks;
import com.hbm.handler.CokerRecipeClientSync;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.fluid.FluidType;
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
import net.minecraft.world.item.ItemStack;

import java.util.ArrayList;
import java.util.List;

public class CokingRecipeHandler implements IRecipeCategory<CokingRecipeHandler.CokerJeiRecipe> {

    public static final RecipeType<CokerJeiRecipe> RECIPE_TYPE = RecipeType.create(NuclearTechMod.MODID, "coking", CokerJeiRecipe.class);
    private final IDrawable background;
    private final IDrawable icon;

    public CokingRecipeHandler(IGuiHelper guiHelper) {
        this.background = guiHelper.drawableBuilder(NuclearTechMod.withDefaultNamespace("textures/gui/jei/gui_nei.png"), 5, 11, 166, 65).setTextureSize(256, 256).build();
        this.icon = guiHelper.createDrawableItemLike(NtmBlocks.MACHINE_COKER.asItem());
    }

    public static List<CokerJeiRecipe> getRecipes() {
        List<CokerJeiRecipe> rows = new ArrayList<>();
        for(var entry : CokerRecipeClientSync.getRecipes().entrySet()) {
            var recipe = entry.getValue();
            var fluid = recipe.byproduct();
            rows.add(new CokerJeiRecipe(entry.getKey(), recipe.inputAmount(), recipe.itemOutput().copy(),
                    fluid == null ? null : new FluidStack(fluid.type, fluid.fill, fluid.pressure)));
        }
        return rows;
    }

    @Override public RecipeType<CokerJeiRecipe> getRecipeType() { return RECIPE_TYPE; }
    @Override public Component getTitle() { return Component.translatable("block.hbmsntm.machine_coker"); }
    @Override public IDrawable getBackground() { return this.background; }
    @Override public IDrawable getIcon() { return this.icon; }

    @Override public void setRecipe(IRecipeLayoutBuilder builder, CokerJeiRecipe recipe, IFocusGroup focuses) {
        builder.addInputSlot(48, 20).setStandardSlotBackground().addItemStack(FluidIconItem.make(new FluidStack(recipe.input(), recipe.inputAmount())))
                .addRichTooltipCallback((slot, tooltip) -> {
                    tooltip.add(Component.translatable("machine_coker.config"));
                    if(recipe.inputAmount() > 16000 || (recipe.byproduct() != null && recipe.byproduct().fill > 8000))
                        tooltip.add(Component.translatable("container.machine_coker.jei.capacity"));
                });
        if(!recipe.itemOutput().isEmpty()) builder.addOutputSlot(102, 20).setStandardSlotBackground().addItemStack(recipe.itemOutput().copy());
        if(recipe.byproduct() != null) builder.addOutputSlot(120, 20).setStandardSlotBackground().addItemStack(FluidIconItem.make(recipe.byproduct()));
    }

    @Override public void draw(CokerJeiRecipe recipe, IRecipeSlotsView slots, GuiGraphics graphics, double mouseX, double mouseY) {
        var font = Minecraft.getInstance().font;
        Component heat = Component.translatable("container.machine_coker.jei.heat");
        graphics.drawString(font, heat, (166 - font.width(heat)) / 2, 46, 0x404040, false);
    }

    public record CokerJeiRecipe(FluidType input, int inputAmount, ItemStack itemOutput, FluidStack byproduct) {
        /** Match all visible values, including modern item components; JEI retains hidden rows. */
        public boolean sameRecipe(CokerJeiRecipe other) {
            if(input != other.input || inputAmount != other.inputAmount || itemOutput.getCount() != other.itemOutput.getCount()
                    || !ItemStack.isSameItemSameComponents(itemOutput, other.itemOutput)) return false;
            return byproduct == null ? other.byproduct == null : other.byproduct != null && byproduct.type == other.byproduct.type
                    && byproduct.fill == other.byproduct.fill && byproduct.pressure == other.byproduct.pressure;
        }
    }
}
