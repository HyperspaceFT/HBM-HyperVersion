package com.hbm.inventory.recipes;

import com.hbm.inventory.FluidStack;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.inventory.recipes.loader.GenericRecipes;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.DepletedFuelItem;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;

/**
 * Original PUREXRecipes.java (59 rows, 2 of them only with a naquadria nugget in the ore dictionary). The defaults register the 12
 * rows NEO content can close, purex.uzh (:44-48, RBMK uzh billet) since Goal24B. Not registered, each waiting for its system:
 * <ul>
 *     <li>:50-60 purex.flashgold, purex.flashlead (balefire gold and flashlead billets)</li>
 *     <li>:62-87 purex.pilepu239, pilergp, pilethorium, pilewaste (Chicago Pile rods)</li>
 *     <li>:171-234 purex.platemox, platepu238be, platepu239, platera226be, platesa326, plateu233, plateu235 (research reactor plate fuel)</li>
 *     <li>:236-371 purex.pwrmeu ... pwrbfpu241, 15 rows (PWR fuel)</li>
 *     <li>:373-380 purex.thoriumsalt (molten salt reactor)</li>
 *     <li>:382-472 purex.watzschrab, watzhes, watzmes, watzles, watzhen, watzmeu, watzmep, watzlead, watzboron, watzdu (Watz pellets)</li>
 *     <li>:474-497 purex.watznaqadah, watznaqadria, conditional on a naquadria nugget (Watz pellets)</li>
 *     <li>:499-506 purex.icf (ICF pellets)</li>
 *     <li>:508-521 purex.vitliquid, vitgaseous, vitsolid (lead sand_mix for vitrification)</li>
 *     <li>:540-553 purex.schrabpwr, purex.schrabmen (PWR fuel)</li>
 * </ul>
 * NEO-only limitation shared with the chemical plant: this table is not synced to clients, so a server-side custom hbmPUREX.json
 * does not reach client JEI or the recipe selector.
 */
public class PUREXRecipes extends GenericRecipes<GenericRecipe> {

    public static final PUREXRecipes INSTANCE = new PUREXRecipes();

    @Override public int inputItemLimit() { return 3; }
    @Override public int inputFluidLimit() { return 3; }
    @Override public int outputItemLimit() { return 6; }
    @Override public int outputFluidLimit() { return 1; }
    @Override public String getFileName() { return "hbmPUREX.json"; }
    @Override public GenericRecipe instantiateRecipe(String name) { return new GenericRecipe(name); }

    @Override
    public void registerDefaults() {
        if(!this.recipeOrderedList.isEmpty()) return;

        long zirnoxPower = 1_000;

        // ZIRNOX (original :89-169)
        String autoZirnox = "autoswitch.zirnox";
        this.register(new GenericRecipe("purex.zirnoxnu").setup(100, zirnoxPower).setNameWrapper("purex.recycle").setGroup(autoZirnox, this)
                .inputItems(coldWaste(NtmItems.WASTE_NATURAL_URANIUM.get()))
                .inputFluids(new FluidStack(Fluids.KEROSENE, 500), new FluidStack(Fluids.NITRIC_ACID, 250))
                .outputItems(new ItemStack(NtmItems.NUGGET_U238.get(), 1),
                        new ItemStack(NtmItems.NUGGET_PU_MIX.get(), 2),
                        new ItemStack(NtmItems.NUGGET_PU239.get(), 1),
                        new ItemStack(NtmItems.NUCLEAR_WASTE_TINY.get(), 2))
                .setIconToFirstIngredient());

        this.register(new GenericRecipe("purex.zirnoxmeu").setup(100, zirnoxPower).setNameWrapper("purex.recycle").setGroup(autoZirnox, this)
                .inputItems(coldWaste(NtmItems.WASTE_URANIUM.get()))
                .inputFluids(new FluidStack(Fluids.KEROSENE, 500), new FluidStack(Fluids.NITRIC_ACID, 250))
                .outputItems(new ItemStack(NtmItems.NUGGET_PU_MIX.get(), 1),
                        new ItemStack(NtmItems.NUGGET_PLUTONIUM.get(), 2),
                        new ItemStack(NtmItems.NUGGET_TECHNETIUM.get(), 1),
                        new ItemStack(NtmItems.NUCLEAR_WASTE_TINY.get(), 2))
                .setIconToFirstIngredient());

        this.register(new GenericRecipe("purex.zirnoxthmeu").setup(100, zirnoxPower).setNameWrapper("purex.recycle").setGroup(autoZirnox, this)
                .inputItems(coldWaste(NtmItems.WASTE_THORIUM.get()))
                .inputFluids(new FluidStack(Fluids.KEROSENE, 500), new FluidStack(Fluids.NITRIC_ACID, 250))
                .outputItems(new ItemStack(NtmItems.NUGGET_U238.get(), 1),
                        new ItemStack(NtmItems.NUGGET_TH232.get(), 1),
                        new ItemStack(NtmItems.NUGGET_U233.get(), 2),
                        new ItemStack(NtmItems.NUCLEAR_WASTE_TINY.get(), 2))
                .setIconToFirstIngredient());

        this.register(new GenericRecipe("purex.zirnoxmox").setup(100, zirnoxPower).setNameWrapper("purex.recycle").setGroup(autoZirnox, this)
                .inputItems(coldWaste(NtmItems.WASTE_MOX.get()))
                .inputFluids(new FluidStack(Fluids.KEROSENE, 500), new FluidStack(Fluids.NITRIC_ACID, 250))
                .outputItems(new ItemStack(NtmItems.NUGGET_PU_MIX.get(), 1),
                        new ItemStack(NtmItems.NUGGET_TECHNETIUM.get(), 1),
                        new ItemStack(NtmItems.NUGGET_U238.get(), 1),
                        new ItemStack(NtmItems.NUCLEAR_WASTE_TINY.get(), 3))
                .setIconToFirstIngredient());

        this.register(new GenericRecipe("purex.zirnoxmep").setup(100, zirnoxPower).setNameWrapper("purex.recycle").setGroup(autoZirnox, this)
                .inputItems(coldWaste(NtmItems.WASTE_PLUTONIUM.get()))
                .inputFluids(new FluidStack(Fluids.KEROSENE, 500), new FluidStack(Fluids.NITRIC_ACID, 250))
                .outputItems(new ItemStack(NtmItems.NUGGET_PU_MIX.get(), 2),
                        new ItemStack(NtmItems.NUGGET_TECHNETIUM.get(), 1),
                        new ItemStack(NtmItems.NUCLEAR_WASTE_TINY.get(), 3))
                .setIconToFirstIngredient());

        this.register(new GenericRecipe("purex.zirnoxheu233").setup(100, zirnoxPower).setNameWrapper("purex.recycle").setGroup(autoZirnox, this)
                .inputItems(coldWaste(NtmItems.WASTE_U233.get()))
                .inputFluids(new FluidStack(Fluids.KEROSENE, 500), new FluidStack(Fluids.NITRIC_ACID, 250))
                .outputItems(new ItemStack(NtmItems.NUGGET_U235.get(), 1),
                        new ItemStack(NtmItems.NUGGET_NEPTUNIUM.get(), 1),
                        new ItemStack(NtmItems.NUGGET_TECHNETIUM.get(), 1),
                        new ItemStack(NtmItems.NUCLEAR_WASTE_TINY.get(), 3))
                .setIconToFirstIngredient());

        this.register(new GenericRecipe("purex.zirnoxheu235").setup(100, zirnoxPower).setNameWrapper("purex.recycle").setGroup(autoZirnox, this)
                .inputItems(coldWaste(NtmItems.WASTE_U235.get()))
                .inputFluids(new FluidStack(Fluids.KEROSENE, 500), new FluidStack(Fluids.NITRIC_ACID, 250))
                .outputItems(new ItemStack(NtmItems.NUGGET_PU238.get(), 1),
                        new ItemStack(NtmItems.NUGGET_NEPTUNIUM.get(), 1),
                        new ItemStack(NtmItems.NUGGET_TECHNETIUM.get(), 1),
                        new ItemStack(NtmItems.NUCLEAR_WASTE_TINY.get(), 3))
                .setIconToFirstIngredient());

        // Two separate tiny waste outputs (1 and 2) as in the original :158-159; they land in different output slots.
        this.register(new GenericRecipe("purex.zirnoxles").setup(100, zirnoxPower).setNameWrapper("purex.recycle").setGroup(autoZirnox, this)
                .inputItems(coldWaste(NtmItems.WASTE_SCHRABIDIUM.get()))
                .inputFluids(new FluidStack(Fluids.KEROSENE, 500), new FluidStack(Fluids.NITRIC_ACID, 250))
                .outputItems(new ItemStack(NtmItems.NUGGET_BERYLLIUM.get(), 2),
                        new ItemStack(NtmItems.NUGGET_PU239.get(), 1),
                        new ItemStack(NtmItems.NUCLEAR_WASTE_TINY.get(), 1),
                        new ItemStack(NtmItems.NUCLEAR_WASTE_TINY.get(), 2))
                .setIconToFirstIngredient());

        this.register(new GenericRecipe("purex.zirnoxzfbmox").setup(100, zirnoxPower).setNameWrapper("purex.recycle").setGroup(autoZirnox, this)
                .inputItems(coldWaste(NtmItems.WASTE_ZFB_MOX.get()))
                .inputFluids(new FluidStack(Fluids.KEROSENE, 500), new FluidStack(Fluids.NITRIC_ACID, 250))
                .outputItems(new ItemStack(NtmItems.NUGGET_ZIRCONIUM.get(), 3),
                        new ItemStack(NtmItems.NUGGET_TECHNETIUM.get(), 1),
                        new ItemStack(NtmItems.NUGGET_PU_MIX.get(), 1),
                        new ItemStack(NtmItems.NUCLEAR_WASTE_TINY.get(), 1))
                .setIconToFirstIngredient());

        // Schrabidium (original :523-539)
        this.register(new GenericRecipe("purex.schraranium").setup(200, 1_000).setNameWrapper("purex.schrab")
                .inputItems(new ComparableStack(NtmItems.INGOT_SCHRARANIUM.get()))
                .inputFluids(new FluidStack(Fluids.KEROSENE, 2_000), new FluidStack(Fluids.NITRIC_ACID, 1_000))
                .outputItems(new ItemStack(NtmItems.NUGGET_SCHRABIDIUM.get(), 3),
                        new ItemStack(NtmItems.NUGGET_URANIUM.get(), 3),
                        new ItemStack(NtmItems.NUGGET_NEPTUNIUM.get(), 2))
                .setIconToFirstIngredient());

        String autoSchrab = "autoswitch.schrab";
        this.register(new GenericRecipe("purex.schrabzirnox").setup(200, 50_000).setNameWrapper("purex.schrab").setGroup(autoSchrab, this)
                .inputItems(coldWaste(NtmItems.WASTE_PLUTONIUM.get()))
                .inputFluids(new FluidStack(Fluids.SOLVENT, 4_000), new FluidStack(Fluids.SCHRABIDIC, 250))
                .outputItems(new ItemStack(NtmItems.POWDER_SCHRABIDIUM.get(), 1),
                        new ItemStack(NtmItems.NUGGET_TECHNETIUM.get(), 3),
                        new ItemStack(NtmItems.NUCLEAR_WASTE_TINY.get(), 4))
                .setIconToFirstIngredient());

        // RBMK uzh billet (original :44-48, Goal24B); the original's OreDictStack(ZR.billet(), 3) is NEO's zirconium billet item.
        // Like the original it has no name wrapper or icon: the name is the display name of the first output.
        this.register(new GenericRecipe("purex.uzh").setup(600, 1_000)
                .inputItems(new ComparableStack(NtmItems.BILLET_URANIUM_FUEL.get()),
                        new ComparableStack(NtmItems.BILLET_ZIRCONIUM.get(), 3))
                .inputFluids(new FluidStack(Fluids.NITRIC_ACID, 1_000), new FluidStack(Fluids.HYDROGEN, 4_000))
                .outputItems(new ItemStack(NtmItems.BILLET_UZH.get(), 4)));
    }

    /**
     * Only cool ZIRNOX waste: the original ComparableStack(item) means damage 0, while NEO's ComparableStack(Item) is a META
     * wildcard and would also take hot waste (META 1).
     */
    private static ComparableStack coldWaste(Item waste) {
        return new ComparableStack(waste, 1, DepletedFuelItem.COOL);
    }
}
