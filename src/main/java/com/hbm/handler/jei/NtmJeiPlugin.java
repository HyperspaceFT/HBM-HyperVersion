package com.hbm.handler.jei;

import com.hbm.blocks.NtmBlocks;
import com.hbm.handler.FractionRecipeClientSync;
import com.hbm.handler.CompressorRecipeClientSync;
import com.hbm.handler.CokerRecipeClientSync;
import com.hbm.handler.MixerRecipeClientSync;
import com.hbm.handler.CentrifugeRecipeClientSync;
import com.hbm.handler.CrystallizerRecipeClientSync;
import com.hbm.handler.FuelPoolRecipeClientSync;
import com.hbm.handler.OutgasserRecipeClientSync;
import com.hbm.handler.jei.AssemblyMachineRecipeHandler;
import com.hbm.handler.jei.AssemblyMachineTransferInfo;
import com.hbm.handler.jei.BoilerRecipeHandler;
import com.hbm.handler.jei.ShredderRecipeHandler;
import com.hbm.handler.jei.subtypes.BatterySubtypeInterpreter;
import com.hbm.handler.jei.subtypes.MetaSubtypeInterpreter;
import com.hbm.handler.jei.subtypes.ScrapsSubtypeInterpreter;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.inventory.recipes.AssemblyMachineRecipes;
import com.hbm.inventory.recipes.ArcFurnaceRecipes;
import com.hbm.inventory.recipes.ArcWelderRecipes;
import com.hbm.inventory.recipes.BlastFurnaceRecipes;
import com.hbm.inventory.recipes.ChemicalPlantRecipes;
import com.hbm.inventory.recipes.PUREXRecipes;
import com.hbm.inventory.recipes.CentrifugeRecipes;
import com.hbm.inventory.recipes.CrystallizerRecipes;
import com.hbm.inventory.recipes.FuelPoolRecipes;
import com.hbm.inventory.recipes.OutgasserRecipes;
import com.hbm.inventory.recipes.CombinationRecipes;
import com.hbm.inventory.recipes.CopperCastingRecipes;
import com.hbm.inventory.recipes.CrucibleRecipes;
import com.hbm.inventory.recipes.anvil.AnvilRecipes;
import com.hbm.inventory.recipes.SolderingRecipes;
import com.hbm.inventory.recipes.ShredderRecipes;
import com.hbm.inventory.screens.AnvilMenuScreen;
import com.hbm.inventory.screens.MachineFurnaceCombinationScreen;
import com.hbm.inventory.screens.MachineAssemblyMachineScreen;
import com.hbm.inventory.screens.MachineCrucibleScreen;
import com.hbm.inventory.screens.MachineArcFurnaceScreen;
import com.hbm.inventory.screens.MachineArcWelderScreen;
import com.hbm.inventory.screens.MachineSolderingStationScreen;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.FluidIconItem;
import com.hbm.items.machine.RBMKPelletItem;
import com.hbm.main.NuclearTechMod;
import mezz.jei.api.IModPlugin;
import mezz.jei.api.JeiPlugin;
import mezz.jei.api.registration.IExtraIngredientRegistration;
import mezz.jei.api.registration.IGuiHandlerRegistration;
import mezz.jei.api.registration.IRecipeCategoryRegistration;
import mezz.jei.api.registration.IRecipeCatalystRegistration;
import mezz.jei.api.registration.IRecipeRegistration;
import mezz.jei.api.registration.IRecipeTransferRegistration;
import mezz.jei.api.registration.ISubtypeRegistration;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;

import java.util.ArrayList;
import java.util.List;
import java.util.LinkedHashMap;
import java.util.Map;

@JeiPlugin
@SuppressWarnings("unused")
public class NtmJeiPlugin implements IModPlugin {

    private mezz.jei.api.runtime.IJeiRuntime runtime;
    private List<CentrifugeRecipes.CentrifugeRecipe> displayedCentrifugeRecipes = List.of();
    private final List<CentrifugeRecipes.CentrifugeRecipe> knownCentrifugeRecipes = new ArrayList<>();
    private List<CrystallizerRecipes.CrystallizerRecipe> displayedCrystallizerRecipes = List.of();
    private final List<CrystallizerRecipes.CrystallizerRecipe> knownCrystallizerRecipes = new ArrayList<>();
    private List<FuelPoolRecipes.FuelPoolRecipe> displayedFuelPoolRecipes = List.of();
    private final List<FuelPoolRecipes.FuelPoolRecipe> knownFuelPoolRecipes = new ArrayList<>();
    private List<OutgasserRecipes.OutgasserRecipe> displayedIrradiationRecipes = List.of();
    private final List<OutgasserRecipes.OutgasserRecipe> knownIrradiationRecipes = new ArrayList<>();
    private List<CokingRecipeHandler.CokerJeiRecipe> displayedCokerRecipes = List.of();
    private final List<CokingRecipeHandler.CokerJeiRecipe> knownCokerRecipes = new ArrayList<>();
    private List<MixingRecipeHandler.MixerJeiRecipe> displayedMixerRecipes = List.of();
    private final List<MixingRecipeHandler.MixerJeiRecipe> knownMixerRecipes = new ArrayList<>();
    private List<FractioningRecipeHandler.FractionRecipe> displayedFractions = List.of();
    private final Map<String, FractioningRecipeHandler.FractionRecipe> knownFractions = new LinkedHashMap<>();
    private List<CompressorRecipeHandler.CompressorJeiRecipe> displayedCompressorRecipes = List.of();
    private final Map<CompressorRecipeHandler.CompressorJeiRecipe, CompressorRecipeHandler.CompressorJeiRecipe> knownCompressorRecipes = new LinkedHashMap<>();

    @Override
    public void onRuntimeAvailable(mezz.jei.api.runtime.IJeiRuntime runtime) {
        this.runtime = runtime;
        FractionRecipeClientSync.setRefresh(this::refreshFractions);
        this.refreshFractions();
        CompressorRecipeClientSync.setRefresh(this::refreshCompressorRecipes);
        this.refreshCompressorRecipes();
        CokerRecipeClientSync.setRefresh(this::refreshCokerRecipes);
        this.refreshCokerRecipes();
        MixerRecipeClientSync.setRefresh(this::refreshMixerRecipes);
        this.refreshMixerRecipes();
        CentrifugeRecipeClientSync.setRefresh(this::refreshCentrifugeRecipes);
        this.refreshCentrifugeRecipes();
        CrystallizerRecipeClientSync.setRefresh(this::refreshCrystallizerRecipes);
        this.refreshCrystallizerRecipes();
        FuelPoolRecipeClientSync.setRefresh(this::refreshFuelPoolRecipes);
        this.refreshFuelPoolRecipes();
        OutgasserRecipeClientSync.setRefresh(this::refreshIrradiationRecipes);
        this.refreshIrradiationRecipes();
    }

    @Override
    public void onRuntimeUnavailable() {
        FractionRecipeClientSync.setRefresh(null);
        CompressorRecipeClientSync.setRefresh(null);
        CokerRecipeClientSync.setRefresh(null);
        MixerRecipeClientSync.setRefresh(null);
        CentrifugeRecipeClientSync.setRefresh(null);
        CrystallizerRecipeClientSync.setRefresh(null);
        FuelPoolRecipeClientSync.setRefresh(null);
        OutgasserRecipeClientSync.setRefresh(null);
        this.displayedCentrifugeRecipes = List.of();
        this.knownCentrifugeRecipes.clear();
        this.displayedCrystallizerRecipes = List.of();
        this.knownCrystallizerRecipes.clear();
        this.displayedFuelPoolRecipes = List.of();
        this.knownFuelPoolRecipes.clear();
        this.displayedIrradiationRecipes = List.of();
        this.knownIrradiationRecipes.clear();
        this.displayedCokerRecipes = List.of();
        this.knownCokerRecipes.clear();
        this.displayedMixerRecipes = List.of();
        this.knownMixerRecipes.clear();
        this.runtime = null;
        this.displayedFractions = List.of();
        this.knownFractions.clear();
        this.displayedCompressorRecipes = List.of();
        this.knownCompressorRecipes.clear();
    }

    private static String fractionKey(FractioningRecipeHandler.FractionRecipe recipe) {
        return recipe.input().getInternalName() + ":" + recipe.output1().type.getInternalName() + ":" + recipe.output1().fill + ":" + recipe.output1().pressure
                + ":" + recipe.output2().type.getInternalName() + ":" + recipe.output2().fill + ":" + recipe.output2().pressure;
    }

    private void refreshFractions() {
        if(this.runtime == null) return;
        var manager = this.runtime.getRecipeManager();
        // JEI's public API hides recipes instead of deleting them. Reuse identical rows on repeated snapshots.
        manager.hideRecipes(FractioningRecipeHandler.RECIPE_TYPE, this.displayedFractions);
        List<FractioningRecipeHandler.FractionRecipe> visible = new ArrayList<>();
        List<FractioningRecipeHandler.FractionRecipe> added = new ArrayList<>();
        for(var recipe : FractioningRecipeHandler.getRecipes()) {
            String key = fractionKey(recipe);
            var known = this.knownFractions.get(key);
            if(known == null) {
                known = recipe;
                this.knownFractions.put(key, known);
                added.add(known);
            }
            visible.add(known);
        }
        manager.addRecipes(FractioningRecipeHandler.RECIPE_TYPE, added);
        manager.unhideRecipes(FractioningRecipeHandler.RECIPE_TYPE, visible);
        this.displayedFractions = visible;
    }

    private void refreshCompressorRecipes() {
        if(this.runtime == null) return;
        var manager = this.runtime.getRecipeManager();
        manager.hideRecipes(CompressorRecipeHandler.RECIPE_TYPE, this.displayedCompressorRecipes);
        List<CompressorRecipeHandler.CompressorJeiRecipe> visible = new ArrayList<>();
        List<CompressorRecipeHandler.CompressorJeiRecipe> added = new ArrayList<>();
        for(var recipe : CompressorRecipeHandler.getRecipes()) {
            // Record identity includes both pressures, amounts, duration and generic-example status.
            var known = this.knownCompressorRecipes.get(recipe);
            if(known == null) {
                known = recipe;
                this.knownCompressorRecipes.put(recipe, known);
                added.add(known);
            }
            visible.add(known);
        }
        manager.addRecipes(CompressorRecipeHandler.RECIPE_TYPE, added);
        manager.unhideRecipes(CompressorRecipeHandler.RECIPE_TYPE, visible);
        this.displayedCompressorRecipes = visible;
    }

    private void refreshCentrifugeRecipes() {
        if(this.runtime == null) return;
        var manager = this.runtime.getRecipeManager();
        manager.hideRecipes(CentrifugeRecipeHandler.RECIPE_TYPE, this.displayedCentrifugeRecipes);
        List<CentrifugeRecipes.CentrifugeRecipe> visible = new ArrayList<>();
        List<CentrifugeRecipes.CentrifugeRecipe> added = new ArrayList<>();
        for(var recipe : CentrifugeRecipeHandler.getRecipes()) {
            var known = this.knownCentrifugeRecipes.stream().filter(recipe::sameRecipe).findFirst().orElse(null);
            if(known == null) {
                known = recipe;
                this.knownCentrifugeRecipes.add(known);
                added.add(known);
            }
            visible.add(known);
        }
        manager.addRecipes(CentrifugeRecipeHandler.RECIPE_TYPE, added);
        manager.unhideRecipes(CentrifugeRecipeHandler.RECIPE_TYPE, visible);
        this.displayedCentrifugeRecipes = visible;
    }


    private void refreshCrystallizerRecipes() {
        if(this.runtime == null) return;
        var manager = this.runtime.getRecipeManager();
        manager.hideRecipes(CrystallizerRecipeHandler.RECIPE_TYPE, this.displayedCrystallizerRecipes);
        List<CrystallizerRecipes.CrystallizerRecipe> visible = new ArrayList<>();
        List<CrystallizerRecipes.CrystallizerRecipe> added = new ArrayList<>();
        for(var recipe : CrystallizerRecipeHandler.getRecipes()) {
            var known = this.knownCrystallizerRecipes.stream().filter(recipe::sameRecipe).findFirst().orElse(null);
            if(known == null) {
                known = recipe;
                this.knownCrystallizerRecipes.add(known);
                added.add(known);
            }
            visible.add(known);
        }
        manager.addRecipes(CrystallizerRecipeHandler.RECIPE_TYPE, added);
        manager.unhideRecipes(CrystallizerRecipeHandler.RECIPE_TYPE, visible);
        this.displayedCrystallizerRecipes = visible;
    }

    private void refreshFuelPoolRecipes() {
        if(this.runtime == null) return;
        var manager = this.runtime.getRecipeManager();
        manager.hideRecipes(FuelPoolRecipeHandler.RECIPE_TYPE, this.displayedFuelPoolRecipes);
        List<FuelPoolRecipes.FuelPoolRecipe> visible = new ArrayList<>();
        List<FuelPoolRecipes.FuelPoolRecipe> added = new ArrayList<>();
        for(var recipe : FuelPoolRecipeHandler.getRecipes()) {
            var known = this.knownFuelPoolRecipes.stream().filter(recipe::sameRecipe).findFirst().orElse(null);
            if(known == null) {
                known = recipe;
                this.knownFuelPoolRecipes.add(known);
                added.add(known);
            }
            visible.add(known);
        }
        manager.addRecipes(FuelPoolRecipeHandler.RECIPE_TYPE, added);
        manager.unhideRecipes(FuelPoolRecipeHandler.RECIPE_TYPE, visible);
        this.displayedFuelPoolRecipes = visible;
    }

    private void refreshIrradiationRecipes() {
        if(this.runtime == null) return;
        var manager = this.runtime.getRecipeManager();
        manager.hideRecipes(IrradiationRecipeHandler.RECIPE_TYPE, this.displayedIrradiationRecipes);
        List<OutgasserRecipes.OutgasserRecipe> visible = new ArrayList<>();
        List<OutgasserRecipes.OutgasserRecipe> added = new ArrayList<>();
        for(var recipe : IrradiationRecipeHandler.getRecipes()) {
            var known = this.knownIrradiationRecipes.stream().filter(recipe::sameRecipe).findFirst().orElse(null);
            if(known == null) {
                known = recipe;
                this.knownIrradiationRecipes.add(known);
                added.add(known);
            }
            visible.add(known);
        }
        manager.addRecipes(IrradiationRecipeHandler.RECIPE_TYPE, added);
        manager.unhideRecipes(IrradiationRecipeHandler.RECIPE_TYPE, visible);
        this.displayedIrradiationRecipes = visible;
    }
    private void refreshCokerRecipes() {
        if(this.runtime == null) return;
        var manager = this.runtime.getRecipeManager();
        manager.hideRecipes(CokingRecipeHandler.RECIPE_TYPE, this.displayedCokerRecipes);
        List<CokingRecipeHandler.CokerJeiRecipe> visible = new ArrayList<>();
        List<CokingRecipeHandler.CokerJeiRecipe> added = new ArrayList<>();
        for(var recipe : CokingRecipeHandler.getRecipes()) {
            var known = this.knownCokerRecipes.stream().filter(recipe::sameRecipe).findFirst().orElse(null);
            if(known == null) {
                known = recipe;
                this.knownCokerRecipes.add(known);
                added.add(known);
            }
            visible.add(known);
        }
        manager.addRecipes(CokingRecipeHandler.RECIPE_TYPE, added);
        manager.unhideRecipes(CokingRecipeHandler.RECIPE_TYPE, visible);
        this.displayedCokerRecipes = visible;
    }

    private void refreshMixerRecipes() {
        if(this.runtime == null) return;
        var manager = this.runtime.getRecipeManager();
        manager.hideRecipes(MixingRecipeHandler.RECIPE_TYPE, this.displayedMixerRecipes);
        List<MixingRecipeHandler.MixerJeiRecipe> visible = new ArrayList<>();
        List<MixingRecipeHandler.MixerJeiRecipe> added = new ArrayList<>();
        for(var recipe : MixingRecipeHandler.getRecipes()) {
            var known = this.knownMixerRecipes.stream().filter(recipe::sameRecipe).findFirst().orElse(null);
            if(known == null) {
                known = recipe;
                this.knownMixerRecipes.add(known);
                added.add(known);
            }
            visible.add(known);
        }
        manager.addRecipes(MixingRecipeHandler.RECIPE_TYPE, added);
        manager.unhideRecipes(MixingRecipeHandler.RECIPE_TYPE, visible);
        this.displayedMixerRecipes = visible;
    }

    @Override public ResourceLocation getPluginUid() { return NuclearTechMod.withDefaultNamespace("jei_plugin"); }

    @Override
    public void registerCategories(IRecipeCategoryRegistration registration) {
        var guiHelper = registration.getJeiHelpers().getGuiHelper();
        registration.addRecipeCategories(
                new AnvilConstructionRecipeHandler(guiHelper),
                new AnvilRecipeHandler(guiHelper),
                new SolderingStationRecipeHandler(guiHelper),
                new ArcWelderRecipeHandler(guiHelper),
                new ArcFurnaceRecipeHandler(guiHelper),
                new AssemblyMachineRecipeHandler(guiHelper),
                new BlastFurnaceRecipeHandler(guiHelper),
                new CentrifugeRecipeHandler(guiHelper),
                new GasCentrifugeRecipeHandler(guiHelper),
                new CrystallizerRecipeHandler(guiHelper),
                new FuelPoolRecipeHandler(guiHelper),
                new IrradiationRecipeHandler(guiHelper),
                new RBMKRodDisassemblyRecipeHandler(guiHelper),
                new ChemicalPlantRecipeHandler(guiHelper),
                new PUREXRecipeHandler(guiHelper),
                new FurnaceCombinationRecipeHandler(guiHelper),
                new PressRecipeHandler(guiHelper),
                new ShredderRecipeHandler(guiHelper),
                new RefineryRecipeHandler(guiHelper),
                new CrackingRecipeHandler(guiHelper),
                new FractioningRecipeHandler(guiHelper),
                new CompressorRecipeHandler(guiHelper),
                new CokingRecipeHandler(guiHelper),
                new MixingRecipeHandler(guiHelper),
                new BoilerRecipeHandler(guiHelper),
                new CrucibleSmeltingRecipeHandler(guiHelper),
                new CrucibleAlloyingRecipeHandler(guiHelper),
                new CrucibleCastingRecipeHandler(guiHelper)
        );
    }

    @Override
    public void registerRecipes(IRecipeRegistration registration) {
        registration.addRecipes(AnvilConstructionRecipeHandler.RECIPE_TYPE, AnvilRecipes.getConstruction());
        registration.addRecipes(AnvilRecipeHandler.RECIPE_TYPE, AnvilRecipes.getSmithing());
        registration.addRecipes(SolderingStationRecipeHandler.RECIPE_TYPE, SolderingRecipes.recipes);
        registration.addRecipes(ArcWelderRecipeHandler.RECIPE_TYPE, ArcWelderRecipes.recipes);
        registration.addRecipes(ArcFurnaceRecipeHandler.RECIPE_TYPE, ArcFurnaceRecipes.recipes);
        registration.addRecipes(AssemblyMachineRecipeHandler.RECIPE_TYPE, AssemblyMachineRecipes.INSTANCE.recipeOrderedList);
        registration.addRecipes(BlastFurnaceRecipeHandler.RECIPE_TYPE, BlastFurnaceRecipes.INSTANCE.recipeOrderedList);
        this.displayedCentrifugeRecipes = CentrifugeRecipeHandler.getRecipes();
        this.knownCentrifugeRecipes.clear();
        this.knownCentrifugeRecipes.addAll(this.displayedCentrifugeRecipes);
        registration.addRecipes(CentrifugeRecipeHandler.RECIPE_TYPE, this.displayedCentrifugeRecipes);
        registration.addRecipes(GasCentrifugeRecipeHandler.RECIPE_TYPE, GasCentrifugeRecipeHandler.getRecipes());
        this.displayedCrystallizerRecipes = CrystallizerRecipeHandler.getRecipes();
        this.knownCrystallizerRecipes.clear();
        this.knownCrystallizerRecipes.addAll(this.displayedCrystallizerRecipes);
        registration.addRecipes(CrystallizerRecipeHandler.RECIPE_TYPE, this.displayedCrystallizerRecipes);
        this.displayedFuelPoolRecipes = FuelPoolRecipeHandler.getRecipes();
        this.knownFuelPoolRecipes.clear();
        this.knownFuelPoolRecipes.addAll(this.displayedFuelPoolRecipes);
        registration.addRecipes(FuelPoolRecipeHandler.RECIPE_TYPE, this.displayedFuelPoolRecipes);
        // The RBMK rod rows are display only and stay out of the displayed/known lists, so refreshFuelPoolRecipes never hides them.
        registration.addRecipes(FuelPoolRecipeHandler.RECIPE_TYPE, FuelPoolRecipeHandler.getRodRecipes());
        this.displayedIrradiationRecipes = IrradiationRecipeHandler.getRecipes();
        this.knownIrradiationRecipes.clear();
        this.knownIrradiationRecipes.addAll(this.displayedIrradiationRecipes);
        registration.addRecipes(IrradiationRecipeHandler.RECIPE_TYPE, this.displayedIrradiationRecipes);
        registration.addRecipes(RBMKRodDisassemblyRecipeHandler.RECIPE_TYPE, RBMKRodDisassemblyRecipeHandler.getRecipes());
        registration.addRecipes(ChemicalPlantRecipeHandler.RECIPE_TYPE, ChemicalPlantRecipes.INSTANCE.recipeOrderedList);
        registration.addRecipes(PUREXRecipeHandler.RECIPE_TYPE, PUREXRecipes.INSTANCE.recipeOrderedList);
        registration.addRecipes(FurnaceCombinationRecipeHandler.RECIPE_TYPE, CombinationRecipes.getJeiRecipes());
        registration.addRecipes(PressRecipeHandler.RECIPE_TYPE, PressRecipeHandler.getRecipes());
        registration.addRecipes(ShredderRecipeHandler.RECIPE_TYPE, ShredderRecipes.getJeiRecipes());
        registration.addRecipes(RefineryRecipeHandler.RECIPE_TYPE, RefineryRecipeHandler.getRecipes());
        registration.addRecipes(CrackingRecipeHandler.RECIPE_TYPE, CrackingRecipeHandler.getRecipes());
        this.displayedFractions = FractioningRecipeHandler.getRecipes();
        this.knownFractions.clear();
        for(var recipe : this.displayedFractions) this.knownFractions.put(fractionKey(recipe), recipe);
        registration.addRecipes(FractioningRecipeHandler.RECIPE_TYPE, this.displayedFractions);
        this.displayedCompressorRecipes = CompressorRecipeHandler.getRecipes();
        this.knownCompressorRecipes.clear();
        for(var recipe : this.displayedCompressorRecipes) this.knownCompressorRecipes.put(recipe, recipe);
        registration.addRecipes(CompressorRecipeHandler.RECIPE_TYPE, this.displayedCompressorRecipes);
        this.displayedCokerRecipes = CokingRecipeHandler.getRecipes();
        this.knownCokerRecipes.clear();
        this.knownCokerRecipes.addAll(this.displayedCokerRecipes);
        registration.addRecipes(CokingRecipeHandler.RECIPE_TYPE, this.displayedCokerRecipes);
        this.displayedMixerRecipes = MixingRecipeHandler.getRecipes();
        this.knownMixerRecipes.clear();
        this.knownMixerRecipes.addAll(this.displayedMixerRecipes);
        registration.addRecipes(MixingRecipeHandler.RECIPE_TYPE, this.displayedMixerRecipes);
        registration.addRecipes(BoilerRecipeHandler.RECIPE_TYPE, BoilerRecipeHandler.getRecipes());
        registration.addRecipes(CrucibleSmeltingRecipeHandler.RECIPE_TYPE, CopperCastingRecipes.getSmeltingRecipes());
        registration.addRecipes(CrucibleAlloyingRecipeHandler.RECIPE_TYPE, CrucibleRecipes.INSTANCE.recipeOrderedList);
        registration.addRecipes(CrucibleCastingRecipeHandler.RECIPE_TYPE, CrucibleCastingRecipeHandler.getRecipes());
    }

    @Override
    public void registerRecipeCatalysts(IRecipeCatalystRegistration registration) {
        registration.addRecipeCatalyst(NtmBlocks.MACHINE_COMPRESSOR.asItem(), CompressorRecipeHandler.RECIPE_TYPE);
        registration.addRecipeCatalyst(NtmBlocks.MACHINE_COKER.asItem(), CokingRecipeHandler.RECIPE_TYPE);
        registration.addRecipeCatalyst(NtmBlocks.MACHINE_MIXER.asItem(), MixingRecipeHandler.RECIPE_TYPE);
        for(com.hbm.blocks.machine.NTMAnvilBlock.Variant variant : com.hbm.blocks.machine.NTMAnvilBlock.Variant.values()) {
            registration.addRecipeCatalyst(
                    MetaHelper.newStack(NtmBlocks.ANVIL.asItem(), variant.ordinal()),
                    AnvilConstructionRecipeHandler.RECIPE_TYPE
            );
            registration.addRecipeCatalyst(
                    MetaHelper.newStack(NtmBlocks.ANVIL.asItem(), variant.ordinal()),
                    AnvilRecipeHandler.RECIPE_TYPE
            );
        }

        registration.addRecipeCatalyst(
                NtmBlocks.MACHINE_SOLDERING_STATION.asItem(),
                SolderingStationRecipeHandler.RECIPE_TYPE
        );
        registration.addRecipeCatalyst(
                NtmBlocks.MACHINE_ARC_WELDER.asItem(),
                ArcWelderRecipeHandler.RECIPE_TYPE
        );
        registration.addRecipeCatalyst(
                NtmBlocks.MACHINE_ARC_FURNACE.asItem(),
                ArcFurnaceRecipeHandler.RECIPE_TYPE
        );
        registration.addRecipeCatalyst(
                NtmBlocks.MACHINE_ASSEMBLY_MACHINE.asItem(),
                AssemblyMachineRecipeHandler.RECIPE_TYPE
        );
        registration.addRecipeCatalyst(
                NtmBlocks.MACHINE_BLAST_FURNACE.asItem(),
                BlastFurnaceRecipeHandler.RECIPE_TYPE
        );
        registration.addRecipeCatalyst(
                NtmBlocks.MACHINE_SHREDDER.asItem(),
                ShredderRecipeHandler.RECIPE_TYPE
        );
        // The electric furnace runs Minecraft's smelting recipes.
        registration.addRecipeCatalyst(
                NtmBlocks.MACHINE_ELECTRIC_FURNACE.asItem(),
                mezz.jei.api.constants.RecipeTypes.SMELTING
        );
        registration.addRecipeCatalyst(
                NtmBlocks.MACHINE_CENTRIFUGE.asItem(),
                CentrifugeRecipeHandler.RECIPE_TYPE
        );
        registration.addRecipeCatalyst(
                NtmBlocks.MACHINE_GAS_CENTRIFUGE.asItem(),
                GasCentrifugeRecipeHandler.RECIPE_TYPE
        );
        registration.addRecipeCatalyst(
                NtmBlocks.MACHINE_CRYSTALLIZER.asItem(),
                CrystallizerRecipeHandler.RECIPE_TYPE
        );
        registration.addRecipeCatalyst(
                NtmBlocks.MACHINE_WASTE_DRUM.asItem(),
                FuelPoolRecipeHandler.RECIPE_TYPE
        );
        registration.addRecipeCatalyst(
                NtmBlocks.RBMK_OUTGASSER.asItem(),
                IrradiationRecipeHandler.RECIPE_TYPE
        );
        registration.addRecipeCatalyst(
                net.minecraft.world.item.Items.CRAFTING_TABLE,
                RBMKRodDisassemblyRecipeHandler.RECIPE_TYPE
        );
        registration.addRecipeCatalyst(
                NtmBlocks.MACHINE_CHEMICAL_PLANT.asItem(),
                ChemicalPlantRecipeHandler.RECIPE_TYPE
        );
        registration.addRecipeCatalyst(
                NtmBlocks.MACHINE_PUREX.asItem(),
                PUREXRecipeHandler.RECIPE_TYPE
        );
        registration.addRecipeCatalyst(
                NtmBlocks.FURNACE_COMBINATION.asItem(),
                FurnaceCombinationRecipeHandler.RECIPE_TYPE
        );
        registration.addRecipeCatalyst(
                NtmBlocks.MACHINE_PRESS.asItem(),
                PressRecipeHandler.RECIPE_TYPE
        );
        registration.addRecipeCatalyst(
                NtmBlocks.MACHINE_REFINERY.asItem(),
                RefineryRecipeHandler.RECIPE_TYPE
        );
        registration.addRecipeCatalyst(
                NtmBlocks.MACHINE_CATALYTIC_CRACKER.asItem(),
                CrackingRecipeHandler.RECIPE_TYPE
        );
        registration.addRecipeCatalyst(NtmBlocks.MACHINE_FRACTION_TOWER.asItem(), FractioningRecipeHandler.RECIPE_TYPE);
        registration.addRecipeCatalyst(
                NtmBlocks.HEAT_BOILER.asItem(),
                BoilerRecipeHandler.RECIPE_TYPE
        );
        registration.addRecipeCatalyst(
                NtmBlocks.MACHINE_INDUSTRIAL_BOILER.asItem(),
                BoilerRecipeHandler.RECIPE_TYPE
        );
        registration.addRecipeCatalyst(
                NtmBlocks.MACHINE_CRUCIBLE.asItem(),
                CrucibleSmeltingRecipeHandler.RECIPE_TYPE,
                CrucibleAlloyingRecipeHandler.RECIPE_TYPE
        );
        registration.addRecipeCatalyst(
                NtmBlocks.FOUNDRY_MOLD.asItem(),
                CrucibleCastingRecipeHandler.RECIPE_TYPE
        );
        registration.addRecipeCatalyst(
                NtmItems.MOLD_BLADE.get(),
                CrucibleCastingRecipeHandler.RECIPE_TYPE
        );
        registration.addRecipeCatalyst(
                NtmItems.MOLD_PLATE_CAST.get(),
                CrucibleCastingRecipeHandler.RECIPE_TYPE
        );
    }

    @Override
    public void registerRecipeTransferHandlers(IRecipeTransferRegistration registration) {
        registration.addRecipeTransferHandler(new SolderingStationTransferInfo());
        registration.addRecipeTransferHandler(new AssemblyMachineTransferInfo());
    }

    @Override
    public void registerGuiHandlers(IGuiHandlerRegistration registration) {
        registration.addRecipeClickArea(AnvilMenuScreen.class, 12, 50, 36, 16, AnvilConstructionRecipeHandler.RECIPE_TYPE);
        registration.addRecipeClickArea(MachineSolderingStationScreen.class, 72, 29, 32, 13, SolderingStationRecipeHandler.RECIPE_TYPE);
        registration.addRecipeClickArea(MachineArcWelderScreen.class, 72, 36, 32, 13, ArcWelderRecipeHandler.RECIPE_TYPE);
        registration.addRecipeClickArea(MachineArcFurnaceScreen.class, MachineArcFurnaceScreen.PROGRESS_X, MachineArcFurnaceScreen.PROGRESS_Y, MachineArcFurnaceScreen.PROGRESS_WIDTH, MachineArcFurnaceScreen.PROGRESS_HEIGHT, ArcFurnaceRecipeHandler.RECIPE_TYPE);
        registration.addRecipeClickArea(MachineFurnaceCombinationScreen.class, 54, 61, 18, 18, FurnaceCombinationRecipeHandler.RECIPE_TYPE);
        registration.addRecipeClickArea(com.hbm.inventory.screens.MachinePressScreen.class, 79, 35, 18, 18, PressRecipeHandler.RECIPE_TYPE);
        registration.addRecipeClickArea(com.hbm.inventory.screens.MachineElectricFurnaceScreen.class, 43, 36, 28, 12, mezz.jei.api.constants.RecipeTypes.SMELTING);
        // No JEI recipe transfer for the crucible: alloys are only chosen in its own selector, as upstream NEI.
        registration.addRecipeClickArea(MachineCrucibleScreen.class, MachineCrucibleScreen.ARROW_X, MachineCrucibleScreen.ARROW_Y,
                MachineCrucibleScreen.ARROW_WIDTH, MachineCrucibleScreen.ARROW_HEIGHT,
                CrucibleSmeltingRecipeHandler.RECIPE_TYPE, CrucibleAlloyingRecipeHandler.RECIPE_TYPE);
    }

    @Override
    public void registerItemSubtypes(ISubtypeRegistration registration) {

        List<Item> ignoreMeta = List.of(

                NtmItems.ROD.get(),
                NtmItems.ROD_DUAL.get(),
                NtmItems.ROD_QUAD.get(),

                // The six depleted RTG pellets are separate JEI ingredients; the ten pellets stay one entry each, whatever their remaining life.
                NtmItems.PELLET_RTG_DEPLETED.get(),

                // Hot (META 1) and cool (META 0) waste are separate JEI ingredients, so the drum rows show both states.
                NtmItems.WASTE_NATURAL_URANIUM.get(),
                NtmItems.WASTE_URANIUM.get(),
                NtmItems.WASTE_THORIUM.get(),
                NtmItems.WASTE_MOX.get(),
                NtmItems.WASTE_PLUTONIUM.get(),
                NtmItems.WASTE_U233.get(),
                NtmItems.WASTE_U235.get(),
                NtmItems.WASTE_SCHRABIDIUM.get(),
                NtmItems.WASTE_ZFB_MOX.get(),

                NtmItems.STARTER_KIT.get(),

                NtmItems.MISSILE_SOYUZ.get(),

                NtmItems.BATTERY_SC.get(),
                NtmItems.WIRE_DENSE.get(),
                NtmItems.BOLT.get(),
                NtmItems.PART_GENERIC.get(),
                NtmItems.CAST_PLATE.get(),
                NtmItems.CAST_PLATE_WELDED.get(),

                NtmItems.FLUID_TANK_FULL.get(),
                NtmItems.FLUID_TANK_LEAD_FULL.get(),
                NtmItems.FLUID_BARREL_FULL.get(),
                NtmItems.FLUID_PACK_FULL.get(),

                NtmItems.SATELLITE.get(),

                NtmItems.FLUID_ICON.get(),
                NtmItems.FLUID_IDENTIFIER_MULTI.get(),
                NtmItems.INGOT_RAW.get(),

                NtmItems.DRINK.get(),
                NtmItems.CANNED_CONSERVE.get(),
                NtmItems.CAP.get(),

                NtmBlocks.BOBBLEHEAD.asItem(),
                NtmBlocks.PLUSHIE.asItem(),

                NtmBlocks.BARBED_WIRE.asItem(),

                NtmBlocks.FLUID_DUCT_NEO.asItem(),

                NtmBlocks.CRASHED_BOMB.asItem()
        );

        for(Item item : ignoreMeta) {
            registration.registerSubtypeInterpreter(item, MetaSubtypeInterpreter.INSTANCE);
        }

        // The ten depletion/xenon METAs of each RBMK pellet (five without xenon) are separate JEI ingredients. The rods have no
        // interpreter: their custom data state does not split JEI entries.
        NtmItems.ITEMS.getEntries().forEach(holder -> {
            if(holder.get() instanceof RBMKPelletItem pellet) registration.registerSubtypeInterpreter(pellet, MetaSubtypeInterpreter.INSTANCE);
        });

        registration.registerSubtypeInterpreter(NtmItems.BATTERY_PACK.get(), BatterySubtypeInterpreter.INSTANCE);
        registration.registerSubtypeInterpreter(NtmItems.SCRAPS.get(), ScrapsSubtypeInterpreter.INSTANCE);
    }

    @Override
    public void registerExtraIngredients(IExtraIngredientRegistration registration) {
        List<ItemStack> extra = new ArrayList<>();

        FluidType[] types = Fluids.getInNiceOrder();
        for(int i = 1; i < types.length; ++i) {
            FluidType type = types[i];

            extra.add(FluidIconItem.make(type, 1000));
        }

        registration.addExtraItemStacks(extra);
    }
}
