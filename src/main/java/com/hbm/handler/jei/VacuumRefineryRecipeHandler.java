package com.hbm.handler.jei;

import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.recipes.VacuumRefineryRecipes;
import com.hbm.items.machine.FluidIconItem;
import com.hbm.main.NuclearTechMod;
import mezz.jei.api.gui.builder.IRecipeLayoutBuilder;
import mezz.jei.api.gui.drawable.IDrawable;
import mezz.jei.api.helpers.IGuiHelper;
import mezz.jei.api.recipe.IFocusGroup;
import mezz.jei.api.recipe.RecipeType;
import mezz.jei.api.recipe.category.IRecipeCategory;
import net.minecraft.network.chat.Component;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class VacuumRefineryRecipeHandler implements IRecipeCategory<VacuumRefineryRecipeHandler.VacuumRecipe> {

    public static final RecipeType<VacuumRecipe> RECIPE_TYPE = RecipeType.create(
            NuclearTechMod.MODID,
            "vacuum_refinery",
            VacuumRecipe.class
    );

    private static final String TEXTURE = "textures/gui/jei/gui_nei.png";

    private final IDrawable background;
    private final IDrawable icon;

    public VacuumRefineryRecipeHandler(IGuiHelper guiHelper) {
        this.background = guiHelper.drawableBuilder(
                NuclearTechMod.withDefaultNamespace(TEXTURE),
                5, 11, 166, 65
        ).setTextureSize(256, 256).build();
        this.icon = guiHelper.createDrawableItemLike(NtmBlocks.MACHINE_VACUUM_DISTILL.asItem());
    }

    public static List<VacuumRecipe> getRecipes() {
        List<VacuumRecipe> list = new ArrayList<>();

        for(Map.Entry<FluidType, VacuumRefineryRecipes.VacuumRefineryRecipe> entry : VacuumRefineryRecipes.recipes.entrySet()) {
            list.add(new VacuumRecipe(entry.getKey(), entry.getValue().outputs));
        }

        return list;
    }

    @Override public RecipeType<VacuumRecipe> getRecipeType() { return RECIPE_TYPE; }
    @Override public Component getTitle() { return Component.translatable("container.vacuumDistill"); }
    @Override public IDrawable getBackground() { return this.background; }
    @Override public IDrawable getIcon() { return this.icon; }

    /** As the original getVacuumRecipe: 1,000 mB at 2 PU in, ten times each output fraction out. */
    @Override
    public void setRecipe(IRecipeLayoutBuilder builder, VacuumRecipe recipe, IFocusGroup focuses) {
        builder.addInputSlot(48, 24)
                .setStandardSlotBackground()
                .addItemStack(FluidIconItem.make(new FluidStack(recipe.input, 1000, 2)));

        for(int i = 0; i < recipe.outputs.length; i++) {
            builder.addOutputSlot(102 + i % 2 * 18, 15 + i / 2 * 18)
                    .setStandardSlotBackground()
                    .addItemStack(FluidIconItem.make(new FluidStack(recipe.outputs[i].type, recipe.outputs[i].fill * 10)));
        }
    }

    public record VacuumRecipe(FluidType input, FluidStack[] outputs) { }
}
