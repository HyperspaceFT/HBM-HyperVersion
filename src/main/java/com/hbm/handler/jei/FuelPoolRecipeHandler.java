package com.hbm.handler.jei;

import com.hbm.blocks.NtmBlocks;
import com.hbm.handler.FuelPoolRecipeClientSync;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.recipes.FuelPoolRecipes.FuelPoolRecipe;
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

import java.util.ArrayList;
import java.util.IdentityHashMap;
import java.util.List;
import java.util.Map;

/** Spent fuel pool drum rows in the layout of the original NEI FuelPoolHandler (NEIUniversalHandler): input, drum, output. */
public class FuelPoolRecipeHandler implements IRecipeCategory<FuelPoolRecipe> {
    public static final RecipeType<FuelPoolRecipe> RECIPE_TYPE = RecipeType.create(NuclearTechMod.MODID, "fuel_pool", FuelPoolRecipe.class);
    private static final ResourceLocation TEXTURE = NuclearTechMod.withDefaultNamespace("textures/gui/jei/gui_nei.png");
    private final IDrawable background;
    private final IDrawable icon;

    public FuelPoolRecipeHandler(IGuiHelper helper) {
        background = helper.drawableBuilder(TEXTURE, 5, 11, 166, 65).setTextureSize(256, 256).build();
        icon = helper.createDrawableItemLike(NtmBlocks.MACHINE_WASTE_DRUM.asItem());
    }
    public static List<FuelPoolRecipe> getRecipes() { return FuelPoolRecipeClientSync.getRecipes(); }

    /**
     * Display rows of the original FuelPoolRecipes.java:46-50, one per craftable RBMK rod: the hot rod of
     * RBMKRodDisassemblyHandler.ComparableStackHeat(rod, true).toStack() (yield 0.2 x rod yield, core 100, hull 50) cools into a rod
     * with yield 0.2 x rod yield. NEO-only display difference: the rows never reach FuelPoolRecipes or its JSON table (the drum takes
     * rods by type and cools them by heat), and as rods have no JEI subtype (NtmJeiPlugin.registerItemSubtypes) the original NEI
     * hiding by heat (FuelPoolHandler :20-36) cannot be expressed, so both the usage and the recipe page show them.
     * FuelPoolRecipe carries no custom data, so each row keeps its two display stacks here, looked up by identity.
     */
    public static List<FuelPoolRecipe> getRodRecipes() {
        ROD_ROWS.clear();
        List<FuelPoolRecipe> rows = new ArrayList<>();
        for(RBMKRodItem rod : RBMKRodItem.CRAFTABLE_RODS) {
            int meta = MetaHelper.getMeta(new ItemStack(rod));
            FuelPoolRecipe row = new FuelPoolRecipe(rod, meta, rod, 1, meta);

            ItemStack hot = new ItemStack(rod);
            RBMKRodItem.setYield(hot, 0.2 * rod.yield);
            RBMKRodItem.setCoreHeat(hot, 100);
            RBMKRodItem.setHullHeat(hot, 50);

            ItemStack cooled = new ItemStack(rod);
            RBMKRodItem.setYield(cooled, 0.2 * rod.yield);

            ROD_ROWS.put(row, new ItemStack[] { hot, cooled });
            rows.add(row);
        }
        return rows;
    }

    private static final Map<FuelPoolRecipe, ItemStack[]> ROD_ROWS = new IdentityHashMap<>();

    @Override public RecipeType<FuelPoolRecipe> getRecipeType() { return RECIPE_TYPE; }
    @Override public Component getTitle() { return Component.translatable("container.machine_waste_drum"); }
    @Override public IDrawable getBackground() { return background; }
    @Override public IDrawable getIcon() { return icon; }
    @Override public void setRecipe(IRecipeLayoutBuilder builder, FuelPoolRecipe recipe, IFocusGroup focuses) {
        ItemStack[] rod = ROD_ROWS.get(recipe);
        builder.addInputSlot(48, 24).setStandardSlotBackground().addItemStack(rod != null ? rod[0].copy() : recipe.input());
        builder.addOutputSlot(102, 24).setStandardSlotBackground().addItemStack(rod != null ? rod[1].copy() : recipe.output());
        builder.addSlot(RecipeIngredientRole.CATALYST, 75, 31).addItemStack(new ItemStack(NtmBlocks.MACHINE_WASTE_DRUM.asItem()));
    }
    // The arrow with the machine slot below it (NEIUniversalHandler.drawBackground).
    @Override public void draw(FuelPoolRecipe recipe, IRecipeSlotsView slots, GuiGraphics graphics, double mouseX, double mouseY) {
        graphics.blit(TEXTURE, 74, 14, 59, 87, 18, 36, 256, 256);
    }
}
