package com.hbm.handler.jei;

import com.hbm.inventory.MetaHelper;
import com.hbm.items.machine.RBMKRodItem;
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
import net.minecraft.world.item.Items;

import java.util.ArrayList;
import java.util.List;

/**
 * Cold RBMK rod disassembly rows of the original NEI RBMKRodDisassemblyHandler, in the layout of FuelPoolRecipeHandler: rod, crafting
 * table, pellets. Display only: the crafting itself is the special recipe RBMKRodDisassemblyRecipe, which JEI does not list in the
 * vanilla crafting category. The original hides hot rods from the usage page (:41-49); rods have no JEI subtype, so that cannot be
 * expressed and every rod's usage shows these rows.
 */
public class RBMKRodDisassemblyRecipeHandler implements IRecipeCategory<RBMKRodDisassemblyRecipeHandler.DisassemblyRecipe> {
    public static final RecipeType<DisassemblyRecipe> RECIPE_TYPE = RecipeType.create(NuclearTechMod.MODID, "rbmk_rod_disassembly", DisassemblyRecipe.class);
    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/jei/gui_nei.png");
    private final IDrawable background;
    private final IDrawable icon;

    public record DisassemblyRecipe(ItemStack rod, ItemStack pellets) { }

    public RBMKRodDisassemblyRecipeHandler(IGuiHelper helper) {
        background = helper.drawableBuilder(TEXTURE, 5, 11, 166, 65).setTextureSize(256, 256).build();
        icon = helper.createDrawableItemLike(Items.CRAFTING_TABLE);
    }

    /**
     * Original getRecipes (:23-39) with ComparableStackHeat.toStack (:69-82): per rod and enrichment grade e = 0..4 a cold rod with
     * yield min(1 - e / 5, 0.99) x rod yield gives 8 pellets of META e; with xenon enabled, the same rod at 50 xenon gives META e + 5.
     */
    public static List<DisassemblyRecipe> getRecipes() {
        List<DisassemblyRecipe> recipes = new ArrayList<>();

        for(RBMKRodItem rod : RBMKRodItem.CRAFTABLE_RODS) {
            if(rod.pellet == null) continue;

            for(int enrichment = 0; enrichment <= 4; enrichment++) {
                recipes.add(new DisassemblyRecipe(rodStack(rod, enrichment, false), MetaHelper.newStack(rod.pellet, 8, enrichment)));

                if(rod.pellet.isXenonEnabled()) {
                    recipes.add(new DisassemblyRecipe(rodStack(rod, enrichment, true), MetaHelper.newStack(rod.pellet, 8, enrichment + 5)));
                }
            }
        }

        return recipes;
    }

    private static ItemStack rodStack(RBMKRodItem rod, int enrichment, boolean poison) {
        ItemStack stack = new ItemStack(rod);
        RBMKRodItem.setYield(stack, Math.min(1 - ((double) enrichment) / 5, 0.99) * rod.yield);
        if(poison) RBMKRodItem.setPoison(stack, 50);
        return stack;
    }

    @Override public RecipeType<DisassemblyRecipe> getRecipeType() { return RECIPE_TYPE; }
    // The original NEI title is hard-coded English.
    @Override public Component getTitle() { return Component.translatable("jei.hbmsntm.rbmk_rod_disassembly"); }
    @Override public IDrawable getBackground() { return background; }
    @Override public IDrawable getIcon() { return icon; }
    @Override public void setRecipe(IRecipeLayoutBuilder builder, DisassemblyRecipe recipe, IFocusGroup focuses) {
        builder.addInputSlot(48, 24).setStandardSlotBackground().addItemStack(recipe.rod().copy());
        builder.addOutputSlot(102, 24).setStandardSlotBackground().addItemStack(recipe.pellets().copy());
        builder.addSlot(RecipeIngredientRole.CATALYST, 75, 31).addItemStack(new ItemStack(Items.CRAFTING_TABLE));
    }
    // The arrow with the machine slot below it (NEIUniversalHandler.drawBackground).
    @Override public void draw(DisassemblyRecipe recipe, IRecipeSlotsView slots, GuiGraphics graphics, double mouseX, double mouseY) {
        graphics.blit(TEXTURE, 74, 14, 59, 87, 18, 36, 256, 256);
    }
}
