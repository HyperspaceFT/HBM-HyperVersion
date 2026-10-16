package com.hbm.handler.jei;

import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.recipes.GasCentrifugeRecipes;
import com.hbm.inventory.recipes.GasCentrifugeRecipes.GasCentrifugeRecipe;
import com.hbm.items.machine.FluidIconItem;
import com.hbm.main.NuclearTechMod;
import com.hbm.util.i18n.I18nUtil;
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
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;

import java.util.List;

/** The cascade summaries of the original NEI handler: what a whole chain of gas centrifuges makes from one input. */
public class GasCentrifugeRecipeHandler implements IRecipeCategory<GasCentrifugeRecipe> {

    public static final RecipeType<GasCentrifugeRecipe> RECIPE_TYPE = RecipeType.create(
            NuclearTechMod.MODID,
            "gas_centrifuge",
            GasCentrifugeRecipe.class
    );

    public static List<GasCentrifugeRecipe> getRecipes() { return GasCentrifugeRecipes.getJeiRecipes(); }

    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/jei/gui_nei_centrifuge_gas.png");

    private final IDrawable background;
    private final IDrawable icon;

    public GasCentrifugeRecipeHandler(IGuiHelper guiHelper) {
        this.background = guiHelper.drawableBuilder(TEXTURE, 5, 11, 166, 65).setTextureSize(256, 256).build();
        this.icon = guiHelper.createDrawableItemLike(NtmBlocks.MACHINE_GAS_CENTRIFUGE.asItem());
    }

    @Override
    public RecipeType<GasCentrifugeRecipe> getRecipeType() {
        return RECIPE_TYPE;
    }

    @Override
    public Component getTitle() {
        return Component.translatable("container.machine_gas_centrifuge");
    }

    @Override
    public IDrawable getBackground() {
        return this.background;
    }

    @Override
    public IDrawable getIcon() {
        return this.icon;
    }

    @Override
    public void setRecipe(IRecipeLayoutBuilder builder, GasCentrifugeRecipe recipe, IFocusGroup focuses) {
        builder.addInputSlot(47, 24)
                .setStandardSlotBackground()
                .addItemStack(FluidIconItem.make(recipe.input(), recipe.amount()));

        for(int i = 0; i < recipe.outputs().length && i < 4; i++) {
            ItemStack output = recipe.outputs()[i];
            if(output.isEmpty()) continue;

            builder.addOutputSlot(i % 2 == 0 ? 129 : 147, i < 2 ? 15 : 33)
                    .setStandardSlotBackground()
                    .addItemStack(output.copy());
        }
    }

    @Override
    public void draw(GasCentrifugeRecipe recipe, IRecipeSlotsView recipeSlotsView, GuiGraphics guiGraphics, double mouseX, double mouseY) {
        var font = Minecraft.getInstance().font;

        // Number of chained gas centrifuges (original "N G. Cents").
        String centrifuges = I18nUtil.resolveKey("gas_centrifuge.jei.cascade", recipe.centrifuges());
        // Shrunk to the 54 px wide dark box (x 23-76) when the translation is wider, e.g. "16 台气体离心机".
        float scale = Math.min(1F, 52F / font.width(centrifuges));
        guiGraphics.pose().pushPose();
        guiGraphics.pose().translate(50F, 14F, 0F);
        guiGraphics.pose().scale(scale, scale, 1F);
        guiGraphics.drawString(font, centrifuges, -font.width(centrifuges) / 2, -4, 0x00FF00, false);
        guiGraphics.pose().popPose();

        // Marks the stage that needs the gas centrifuge speed upgrade.
        if(recipe.highSpeed()) guiGraphics.blit(TEXTURE, 25, 24, 192, 0, 16, 16, 256, 256);
    }
}
