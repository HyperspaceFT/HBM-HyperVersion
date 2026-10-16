package com.hbm.handler.jei;

import com.hbm.blocks.NtmBlocks;
import com.hbm.handler.CrystallizerRecipeClientSync;
import com.hbm.inventory.recipes.CrystallizerRecipes.CrystallizerRecipe;
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
import net.minecraft.util.FormattedCharSequence;

import java.util.List;

/** Ore acidizer rows: the acid icon and the input item on the left, the output on the right, duration above and productivity below. */
public class CrystallizerRecipeHandler implements IRecipeCategory<CrystallizerRecipe> {
    public static final RecipeType<CrystallizerRecipe> RECIPE_TYPE = RecipeType.create(NuclearTechMod.MODID, "crystallizer", CrystallizerRecipe.class);
    private final IDrawable background;
    private final IDrawable icon;

    public CrystallizerRecipeHandler(IGuiHelper helper) {
        background = helper.drawableBuilder(NuclearTechMod.withDefaultNamespace("textures/gui/jei/gui_nei.png"), 5, 11, 166, 65).setTextureSize(256, 256).build();
        icon = helper.createDrawableItemLike(NtmBlocks.MACHINE_CRYSTALLIZER.asItem());
    }
    public static List<CrystallizerRecipe> getRecipes() { return CrystallizerRecipeClientSync.getRecipes(); }
    @Override public RecipeType<CrystallizerRecipe> getRecipeType() { return RECIPE_TYPE; }
    @Override public Component getTitle() { return Component.translatable("container.machine_crystallizer"); }
    @Override public IDrawable getBackground() { return background; }
    @Override public IDrawable getIcon() { return icon; }
    @Override public void setRecipe(IRecipeLayoutBuilder builder, CrystallizerRecipe recipe, IFocusGroup focuses) {
        builder.addInputSlot(12, 20).setStandardSlotBackground().addItemStack(FluidIconItem.make(recipe.fluid));
        builder.addInputSlot(30, 20).setStandardSlotBackground().addItemStacks(recipe.input.extractForJEI());
        builder.addOutputSlot(120, 20).setStandardSlotBackground().addItemStack(recipe.output())
                .addRichTooltipCallback((slot, tooltip) -> tooltip.add(Component.translatable("container.machine_crystallizer.jei.config")));
    }
    @Override public void draw(CrystallizerRecipe recipe, IRecipeSlotsView slots, GuiGraphics graphics, double mouseX, double mouseY) {
        var font = Minecraft.getInstance().font;
        // Both lines are wider than the 166 px box in Chinese and English: the duration goes above the slots, the productivity below.
        Component time = Component.translatable("container.machine_crystallizer.jei.duration", recipe.duration, recipe.duration + 1);
        drawFitted(graphics, font, time, 2, 17);
        Component chance = Component.translatable("container.machine_crystallizer.jei.productivity", String.format(java.util.Locale.ROOT, "%.0f", recipe.productivity * 100F));
        drawFitted(graphics, font, chance, 40, 23);
    }

    /** Wraps the text to the box interior and shrinks it only if the wrapped lines are still taller than the band at {@code top}. */
    private static void drawFitted(GuiGraphics graphics, Font font, Component text, int top, int height) {
        float scale = 1F;
        List<FormattedCharSequence> lines = font.split(text, 158);
        for(int step = 19; step >= 10 && lines.size() * font.lineHeight - 1 > height / scale; step--) {
            scale = step / 20F;
            lines = font.split(text, (int) (158 / scale));
        }
        graphics.pose().pushPose();
        graphics.pose().translate(83F, top + (height - (lines.size() * font.lineHeight - 1) * scale) / 2F, 0F);
        graphics.pose().scale(scale, scale, 1F);
        for(int i = 0; i < lines.size(); i++) {
            graphics.drawString(font, lines.get(i), -font.width(lines.get(i)) / 2, i * font.lineHeight, 0x404040, false);
        }
        graphics.pose().popPose();
    }
}
