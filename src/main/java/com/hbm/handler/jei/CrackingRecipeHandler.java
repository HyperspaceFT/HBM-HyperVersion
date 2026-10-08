package com.hbm.handler.jei;

import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.recipes.CrackingRecipes;
import com.hbm.items.machine.FluidIconItem;
import com.hbm.main.NuclearTechMod;
import com.hbm.util.Tuple.Pair;
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

public class CrackingRecipeHandler implements IRecipeCategory<CrackingRecipeHandler.CrackingRecipe> {

    public static final RecipeType<CrackingRecipe> RECIPE_TYPE = RecipeType.create(
            NuclearTechMod.MODID,
            "cracking",
            CrackingRecipe.class
    );

    private static final String TEXTURE = "textures/gui/jei/gui_nei.png";

    private final IDrawable background;
    private final IDrawable icon;

    public CrackingRecipeHandler(IGuiHelper guiHelper) {
        this.background = guiHelper.drawableBuilder(
                NuclearTechMod.withDefaultNamespace(TEXTURE),
                5, 11, 166, 65
        ).setTextureSize(256, 256).build();
        this.icon = guiHelper.createDrawableItemLike(NtmBlocks.MACHINE_CATALYTIC_CRACKER.asItem());
    }

    public static List<CrackingRecipe> getRecipes() {
        List<CrackingRecipe> list = new ArrayList<>();

        for(Map.Entry<FluidType, Pair<FluidStack, FluidStack>> entry : CrackingRecipes.cracking.entrySet()) {
            list.add(new CrackingRecipe(entry.getKey(), entry.getValue().getKey(), entry.getValue().getValue()));
        }

        return list;
    }

    @Override
    public RecipeType<CrackingRecipe> getRecipeType() {
        return RECIPE_TYPE;
    }

    @Override
    public Component getTitle() {
        return Component.translatable("block.hbmsntm.machine_catalytic_cracker");
    }

    @Override
    public IDrawable getBackground() {
        return this.background;
    }

    @Override
    public IDrawable getIcon() {
        return this.icon;
    }

    /** Slot positions of the original universal NEI handler for two inputs and two or three outputs. */
    @Override
    public void setRecipe(IRecipeLayoutBuilder builder, CrackingRecipe recipe, IFocusGroup focuses) {
        builder.addInputSlot(48, 24)
                .setStandardSlotBackground()
                .addItemStack(FluidIconItem.make(recipe.input, 100));
        builder.addInputSlot(30, 24)
                .setStandardSlotBackground()
                .addItemStack(FluidIconItem.make(Fluids.STEAM, 200));

        List<FluidStack> outputs = new ArrayList<>();
        outputs.add(recipe.output1);
        // As the original getCrackingRecipesForNEI: a NONE second output is left out.
        if(recipe.output2.type != Fluids.NONE) outputs.add(recipe.output2);
        outputs.add(new FluidStack(Fluids.SPENTSTEAM, 2));

        for(int i = 0; i < outputs.size(); i++) {
            builder.addOutputSlot(102 + i * 18, 24)
                    .setStandardSlotBackground()
                    .addItemStack(FluidIconItem.make(outputs.get(i)));
        }
    }

    public record CrackingRecipe(FluidType input, FluidStack output1, FluidStack output2) { }
}
