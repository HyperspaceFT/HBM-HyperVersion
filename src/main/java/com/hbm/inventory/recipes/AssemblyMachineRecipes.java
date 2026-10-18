package com.hbm.inventory.recipes;

import com.hbm.blocks.NtmBlocks;
import com.hbm.config.NtmConfig;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.NtmTags;
import com.hbm.inventory.RecipesCommon;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.inventory.recipes.loader.GenericRecipes;
import com.hbm.items.BoltItem;
import com.hbm.items.WireDenseItem;
import com.hbm.items.machine.PistonSetItem;
import com.hbm.items.CastPlateItem;
import com.hbm.items.NtmItems;
import com.hbm.items.PartGenericItem;
import com.hbm.items.machine.BatteryPackItem.BatteryPackType;
import com.hbm.items.machine.FluidIconItem;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.tags.ItemTags;
import net.minecraft.world.item.ItemStack;

public class AssemblyMachineRecipes extends GenericRecipes<GenericRecipe> {

    public static final AssemblyMachineRecipes INSTANCE = new AssemblyMachineRecipes();

    @Override public int inputItemLimit() { return 12; }
    @Override public int inputFluidLimit() { return 1; }
    @Override public int outputItemLimit() { return 1; }
    @Override public int outputFluidLimit() { return 1; }

    @Override public String getFileName() { return "hbmAssemblyMachine.json"; }
    @Override public GenericRecipe instantiateRecipe(String name) { return new GenericRecipe(name); }

    @Override
    public void registerDefaults() {
        this.register(new GenericRecipe("ass.boytarget").setup(200, 100).outputItems(new ItemStack(NtmItems.LITTLE_BOY_TARGET.get(), 1))
                        .inputItems(new ComparableStack(NtmItems.INGOT_URANIUM.get(), 18)));

        this.register(new GenericRecipe("ass.machine_refinery").setup(200, 100).outputItems(new ItemStack(NtmBlocks.MACHINE_REFINERY, 1))
                .inputItems(
                        new ComparableStack(NtmItems.PLATE_COPPER.get(), 8),
                        new ComparableStack(NtmItems.SHELL_STEEL.get(), 4),
                        new ComparableStack(NtmItems.PIPE_STEEL.get(), 12),
                        new ComparableStack(NtmItems.INSULATOR.get(), 8),
                        new ComparableStack(NtmItems.CIRCUIT_ANALOG_BOARD.get(), 3),
                        NtmItems.castPlateWeldedIngredient(CastPlateItem.Type.STEEL, 3)

                        ));

        this.register(new GenericRecipe("ass.drill_titanium").setup(100, 100).outputItems(new ItemStack(NtmItems.DRILL_TITANIUM.get(), 1))
                .inputItems(
                        NtmItems.castPlateIngredient(CastPlateItem.Type.DURA_STEEL, 1),
                        new ComparableStack(NtmItems.PLATE_TITANIUM.get(), 8)
                )
        );

        this.register(new GenericRecipe("ass.machine_oil_derrick").setup(200, 100).outputItems(new ItemStack(NtmBlocks.MACHINE_WELL, 1))
                .inputItems(
                        NtmItems.castPlateIngredient(CastPlateItem.Type.COPPER, 2),
                        new ComparableStack(NtmItems.PLATE_STEEL.get(), 8),
                        new ComparableStack(NtmItems.PIPE_STEEL.get(), 4),
                        new ComparableStack(NtmItems.DRILL_TITANIUM.get(), 1),
                        new ComparableStack(NtmItems.MOTOR.get(), 1)

                )
        );

        this.register(new GenericRecipe("ass.missileassembly").setup(200, 100).outputItems(new ItemStack(NtmItems.MISSILE_ASSEMBLY.get(), 1))
                .inputItems(
                        new ComparableStack(NtmItems.SHELL_ALUMINIUM.get(), 2),
                        new ComparableStack(NtmItems.SHELL_TITANIUM.get(), 4),
                        new RecipesCommon.TagStack(ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "bars_hard_plastic")), 8),
                        new ComparableStack(NtmItems.ROCKET_FUEL.get(), 8),
                        new ComparableStack(NtmItems.CIRCUIT_PRINTED_BOARD.get(), 1)
                )
        );

        this.register(new GenericRecipe("ass.warheadhe1").setup(100, 100).outputItems(new ItemStack(NtmItems.WARHEAD_GENERIC_SMALL.get(), 1))
                .inputItems(
                        new ComparableStack(NtmItems.PLATE_TITANIUM.get(), 4),
                        new ComparableStack(NtmItems.BALL_DYNAMITE.get(), 2),
                        new ComparableStack(NtmItems.CIRCUIT_MICROCHIP.get(), 1)
                )
        );

        this.register(new GenericRecipe("ass.warheadhe2").setup(200, 100).outputItems(new ItemStack(NtmItems.WARHEAD_GENERIC_MEDIUM.get(), 1))
                .inputItems(
                        new ComparableStack(NtmItems.PLATE_TITANIUM.get(), 8),
                        new RecipesCommon.TagStack(ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "balls_he")), 4),
                        new ComparableStack(NtmItems.CIRCUIT_PRINTED_BOARD.get(), 1)
                )
        );

        this.register(new GenericRecipe("ass.warheadhe3").setup(400, 100).outputItems(new ItemStack(NtmItems.WARHEAD_GENERIC_LARGE.get(), 1))
                .inputItems(
                        new ComparableStack(NtmItems.PLATE_TITANIUM.get(), 16),
                        new RecipesCommon.TagStack(ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "balls_he")), 8),
                        new ComparableStack(NtmItems.CIRCUIT_INTEGRATED_BOARD.get(), 1)
                )
        );

        this.register(new GenericRecipe("ass.warheadinc1").setup(100, 100).outputItems(new ItemStack(NtmItems.WARHEAD_INCENDIARY_SMALL.get(), 1))
                .inputItems(
                        new ComparableStack(NtmItems.WARHEAD_GENERIC_SMALL.get(), 1),
                        new ComparableStack(NtmItems.POWDER_FIRE.get(), 2)
                )
        );

        this.register(new GenericRecipe("ass.warheadinc2").setup(200, 100).outputItems(new ItemStack(NtmItems.WARHEAD_INCENDIARY_MEDIUM.get(), 1))
                .inputItems(
                        new ComparableStack(NtmItems.WARHEAD_GENERIC_MEDIUM.get(), 1),
                        new ComparableStack(NtmItems.POWDER_FIRE.get(), 4)
                )
        );

        this.register(new GenericRecipe("ass.warheadinc3").setup(400, 100).outputItems(new ItemStack(NtmItems.WARHEAD_INCENDIARY_LARGE.get(), 1))
                .inputItems(
                        new ComparableStack(NtmItems.WARHEAD_GENERIC_LARGE.get(), 1),
                        new ComparableStack(NtmItems.POWDER_FIRE.get(), 8)
                )
        );

        this.register(new GenericRecipe("ass.warheadcl1").setup(100, 100).outputItems(new ItemStack(NtmItems.WARHEAD_CLUSTER_SMALL.get(), 1))
                .inputItems(
                        new ComparableStack(NtmItems.WARHEAD_GENERIC_SMALL.get(), 1),
                        new ComparableStack(NtmItems.PELLET_CLUSTER.get(), 2)
                )
        );

        this.register(new GenericRecipe("ass.warheadcl2").setup(200, 100).outputItems(new ItemStack(NtmItems.WARHEAD_CLUSTER_MEDIUM.get(), 1))
                .inputItems(
                        new ComparableStack(NtmItems.WARHEAD_GENERIC_MEDIUM.get(), 1),
                        new ComparableStack(NtmItems.PELLET_CLUSTER.get(), 4)
                )
        );

        this.register(new GenericRecipe("ass.warheadcl3").setup(400, 100).outputItems(new ItemStack(NtmItems.WARHEAD_CLUSTER_LARGE.get(), 1))
                .inputItems(
                        new ComparableStack(NtmItems.WARHEAD_GENERIC_LARGE.get(), 1),
                        new ComparableStack(NtmItems.PELLET_CLUSTER.get(), 8)
                )
        );

        this.register(new GenericRecipe("ass.warheadbb1").setup(100, 100).outputItems(new ItemStack(NtmItems.WARHEAD_BUSTER_SMALL.get(), 1))
                .inputItems(
                        new ComparableStack(NtmItems.WARHEAD_GENERIC_SMALL.get(), 1),
                        new RecipesCommon.TagStack(ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "balls_he")), 2)
                )
        );

        this.register(new GenericRecipe("ass.warheadbb2").setup(200, 100).outputItems(new ItemStack(NtmItems.WARHEAD_BUSTER_MEDIUM.get(), 1))
                .inputItems(
                        new ComparableStack(NtmItems.WARHEAD_GENERIC_MEDIUM.get(), 1),
                        new RecipesCommon.TagStack(ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "balls_he")), 4)
                )
        );

        this.register(new GenericRecipe("ass.warheadbb3").setup(400, 100).outputItems(new ItemStack(NtmItems.WARHEAD_BUSTER_LARGE.get(), 1))
                .inputItems(
                        new ComparableStack(NtmItems.WARHEAD_GENERIC_LARGE.get(), 1),
                        new RecipesCommon.TagStack(ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "balls_he")), 8)
                )
        );

        this.register(new GenericRecipe("ass.warheadnuke").setup(400, 100).outputItems(new ItemStack(NtmItems.WARHEAD_NUCLEAR.get(), 1))
                .inputItems(
                        NtmItems.castPlateIngredient(CastPlateItem.Type.TITANIUM, 12),
                        NtmItems.castPlateIngredient(CastPlateItem.Type.LEAD, 6),
                        new ComparableStack(NtmItems.BILLET_U235.get(), 6),
                        new ComparableStack(NtmItems.CORDITE.get(), 12),
                        new ComparableStack(NtmItems.CIRCUIT_CONTROL_UNIT.get(), 1)
                )
        );

        this.register(new GenericRecipe("ass.warheadthermonuke").setup(600, 100).outputItems(new ItemStack(NtmItems.WARHEAD_MIRV.get(), 1))
                .inputItems(
                        NtmItems.castPlateIngredient(CastPlateItem.Type.TITANIUM, 12),
                        NtmItems.castPlateIngredient(CastPlateItem.Type.LEAD, 6),
                        new ComparableStack(NtmItems.BILLET_PU239.get(), 8),
                        new ComparableStack(NtmItems.BALL_TATB.get(), 12),
                        new ComparableStack(NtmItems.CIRCUIT_ADVANCED_CONTROL_UNIT.get(), 2)
                ).inputFluids(new FluidStack(Fluids.DEUTERIUM, 4_000))
        );

        this.register(new GenericRecipe("ass.warheadvolcano").setup(600, 100).outputItems(new ItemStack(NtmItems.WARHEAD_VOLCANO.get(), 1))
                .inputItems(
                        NtmItems.castPlateIngredient(CastPlateItem.Type.TITANIUM, 12),
                        NtmItems.castPlateIngredient(CastPlateItem.Type.STEEL, 6),
                        new ComparableStack(NtmBlocks.DET_NUKE.get(), 3),
                        new ComparableStack(NtmBlocks.BLOCK_U238.get(), 24),
                        new ComparableStack(NtmItems.CIRCUIT_CAPACITOR_BOARD.get(), 5)
                )
        );

        this.register(new GenericRecipe("ass.plate_desh").setup(200, 100).outputItems(new ItemStack(NtmItems.PLATE_DESH.get(), 4))
                .inputItems(
                        new ComparableStack(NtmItems.INGOT_DESH.get(), 4),
                        new ComparableStack(NtmItems.INGOT_DURA_STEEL.get(), 1),
                        new RecipesCommon.TagStack(ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "powders_plastic")), 2)

                )
        );

        this.register(new GenericRecipe("ass.plate_bismuth").setup(200, 100).outputItems(new ItemStack(NtmItems.PLATE_BISMUTH.get(), 1))
                .inputItems(
                        new ComparableStack(NtmItems.NUGGET_BISMUTH.get(), 2),
                        new ComparableStack(NtmItems.BILLET_U238.get(), 2),
                        new ComparableStack(NtmItems.POWDER_NIOBIUM.get(), 1)

                )
        );

        this.register(new GenericRecipe("ass.magnetron").setup(40, 100).outputItems(new ItemStack(NtmItems.MAGNETRON.get(), 1))
                .inputItems(
                        new ComparableStack(NtmItems.WIRE_TUNGSTEN.get(), 4),
                        new ComparableStack(NtmItems.POWDER_NIOBIUM.get(), 3)

                )
        );

        this.register(new GenericRecipe("ass.pellet_cluster").setup(40, 100).outputItems(new ItemStack(NtmItems.PELLET_CLUSTER.get(), 1))
                .inputItems(
                        new ComparableStack(NtmItems.PLATE_STEEL.get(), 4),
                        new RecipesCommon.TagStack(ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "balls_he")), 1)

                )
        );

        this.register(new GenericRecipe("ass.plate_dalek").setup(40, 100).outputItems(new ItemStack(NtmItems.PLATE_DALEKANIUM.get(), 1))
                .inputItems(
                        new ComparableStack(NtmBlocks.BLOCK_METEOR.get(), 1)

                )
        );

        this.register(new GenericRecipe("ass.man").setup(200, 100).outputItems(new ItemStack(NtmBlocks.NUKE_FAT_MAN.get(), 1))
                .inputItems(new ComparableStack(NtmItems.PELLET_ANTIMATTER.get(), 1)));

        FluidType[] order = Fluids.getInNiceOrder();
        for(int i = 1; i < order.length; ++i) {
            FluidType type = order[i];
            if(type.hasNoContainer()) continue;
            this.register(new GenericRecipe("ass.package" + type.getUnlocalizedName()).setup(40, 100).outputItems(MetaHelper.newStack(NtmItems.FLUID_PACK_FULL, 1, type.getID()))
                    .inputItems(new ComparableStack(NtmItems.FLUID_PACK_EMPTY.get())).inputFluids(new FluidStack(type, 32_000)));
            this.register(new GenericRecipe("ass.unpackage" + type.getUnlocalizedName()).setup(40, 100).setIcon(FluidIconItem.make(type, 32_000)).outputItems(new ItemStack(NtmItems.FLUID_PACK_EMPTY.get()))
                    .inputItems(new ComparableStack(MetaHelper.newStack(NtmItems.FLUID_PACK_FULL, 1, type.getID()))).outputFluids(new FluidStack(type, 32_000)));
        }

        this.register(new GenericRecipe("ass.shredder").setup(100, 100).outputItems(new ItemStack(NtmBlocks.MACHINE_SHREDDER.get()))
                .inputItems(new RecipesCommon.TagStack(NtmTags.Items.PLATES_STEEL, 8),
                        new RecipesCommon.TagStack(NtmTags.Items.PLATES_COPPER, 4),
                        new ComparableStack(NtmItems.MOTOR.get(), 2)));

        // Original ass.compressor, normal inputs only; cast plates retain their steel META identity.
        this.register(new GenericRecipe("ass.compressor").setup(200, 100).outputItems(new ItemStack(NtmBlocks.MACHINE_COMPRESSOR.get(), 1))
                .inputItems(NtmItems.castPlateIngredient(CastPlateItem.Type.STEEL, 8),
                        new RecipesCommon.TagStack(NtmTags.Items.PLATES_COPPER, 4),
                        new ComparableStack(NtmItems.SHELL_STEEL.get(), 2),
                        new ComparableStack(NtmItems.MOTOR.get(), 3),
                        new ComparableStack(NtmItems.CIRCUIT_ANALOG_BOARD.get(), 1)));

        // Original normal ass.coker inputs remain available in both enable528 settings; welded steel keeps its material component.
        this.register(new GenericRecipe("ass.coker").setup(200, 100).outputItems(new ItemStack(NtmBlocks.MACHINE_COKER.get(), 1))
                .inputItems(NtmItems.castPlateWeldedIngredient(CastPlateItem.Type.STEEL, 8),
                        new ComparableStack(NtmItems.SHELL_STEEL.get(), 4),
                        new RecipesCommon.TagStack(NtmTags.Items.PLATES_COPPER, 8),
                        new ComparableStack(NtmItems.INGOT_RUBBER.get(), 4),
                        new ComparableStack(NtmItems.INGOT_NIOBIUM.get(), 4)));

        // Original normal centrifuge acquisition remains available in both enable528 settings.
        // Dura and titanium plates have no declared NEO tags; ntm:ingots_plastic is polymer/bakelite.
        this.register(new GenericRecipe("ass.centrifugetower").setup(100, 100).outputItems(new ItemStack(NtmItems.CENTRIFUGE_ELEMENT.get(), 1))
                .inputItems(new ComparableStack(NtmItems.PLATE_DURA_STEEL.get(), 4),
                        new ComparableStack(NtmItems.PLATE_TITANIUM.get(), 4),
                        new ComparableStack(NtmItems.MOTOR.get(), 1)));
        this.register(new GenericRecipe("ass.centrifuge").setup(200, 100).outputItems(new ItemStack(NtmBlocks.MACHINE_CENTRIFUGE.get(), 1))
                .inputItems(new ComparableStack(NtmItems.CENTRIFUGE_ELEMENT.get(), 1),
                        new RecipesCommon.TagStack(ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "ingots_plastic")), 4),
                        new RecipesCommon.TagStack(NtmTags.Items.PLATES_STEEL, 8),
                        new RecipesCommon.TagStack(NtmTags.Items.PLATES_COPPER, 4),
                        new ComparableStack(NtmItems.CIRCUIT_ANALOG_BOARD.get(), 1)));
        // Original AssemblyMachineRecipes.java:282-283 normal branch, 400 ticks at 100 HE/t. The expensive inputItemsEx branch
        // and the 528 pool are not migrated (NEO has no item_expensive).
        this.register(new GenericRecipe("ass.gascent").setup(400, 100).outputItems(new ItemStack(NtmBlocks.MACHINE_GAS_CENTRIFUGE.get(), 1))
                .inputItems(new ComparableStack(NtmItems.CENTRIFUGE_ELEMENT.get(), 4),
                        new RecipesCommon.TagStack(ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "ingots_plastic")), 8),
                        new ComparableStack(NtmItems.INGOT_DESH.get(), 2),
                        new RecipesCommon.TagStack(NtmTags.Items.PLATES_STEEL, 8),
                        new ComparableStack(NtmItems.CIRCUIT_MILITARY_GRADE_BOARD.get(), 1)));

        // Original normal turbofan/combustion/piston inputs remain available in both enable528 settings.
        this.register(new GenericRecipe("ass.turbofan").setup(300, 100).outputItems(new ItemStack(NtmBlocks.MACHINE_TURBOFAN.get(), 1))
                .inputItems(new ComparableStack(NtmItems.SHELL_TITANIUM.get(), 8),
                        new ComparableStack(NtmItems.PIPE_DURA_STEEL.get(), 4),
                        new RecipesCommon.TagStack(ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "ingots_plastic")), 12),
                        new ComparableStack(NtmItems.TURBINE_TUNGSTEN.get(), 1),
                        new ComparableStack(MetaHelper.newStack(NtmItems.WIRE_DENSE.get(), 12, WireDenseItem.Type.GOLD.meta)),
                        new ComparableStack(NtmItems.CIRCUIT_INTEGRATED_BOARD.get(), 3)));
        this.register(new GenericRecipe("ass.combustiongen").setup(300, 100).outputItems(new ItemStack(NtmBlocks.MACHINE_COMBUSTION_ENGINE.get(), 1))
                .inputItems(new RecipesCommon.TagStack(NtmTags.Items.PLATES_STEEL, 16),
                        new ComparableStack(NtmItems.INGOT_COPPER.get(), 12),
                        new ComparableStack(MetaHelper.newStack(NtmItems.WIRE_DENSE.get(), 8, WireDenseItem.Type.GOLD.meta)),
                        new ComparableStack(NtmItems.CANISTER_EMPTY.get(), 4),
                        new ComparableStack(NtmItems.CIRCUIT_INTEGRATED_BOARD.get(), 1)));
        this.register(new GenericRecipe("ass.pistonsetsteel").setup(200, 100).outputItems(MetaHelper.newStack(NtmItems.PISTON_SET.get(), 1, PistonSetItem.Type.STEEL.ordinal()))
                .inputItems(new RecipesCommon.TagStack(NtmTags.Items.PLATES_STEEL, 16),
                        new RecipesCommon.TagStack(NtmTags.Items.PLATES_COPPER, 4),
                        new ComparableStack(NtmItems.INGOT_TUNGSTEN.get(), 8),
                        new ComparableStack(MetaHelper.newStack(NtmItems.BOLT.get(), 16, BoltItem.Type.TUNGSTEN.meta))));
        this.register(new GenericRecipe("ass.pistonsetdura").setup(200, 100).outputItems(MetaHelper.newStack(NtmItems.PISTON_SET.get(), 1, PistonSetItem.Type.DURA.ordinal()))
                .inputItems(new ComparableStack(NtmItems.INGOT_DURA_STEEL.get(), 24),
                        new ComparableStack(NtmItems.PLATE_TITANIUM.get(), 8),
                        new ComparableStack(NtmItems.INGOT_TUNGSTEN.get(), 8),
                        new ComparableStack(MetaHelper.newStack(NtmItems.BOLT.get(), 16, BoltItem.Type.DURA_STEEL.meta))));
        this.register(new GenericRecipe("ass.pistonsetdesh").setup(200, 100).outputItems(MetaHelper.newStack(NtmItems.PISTON_SET.get(), 1, PistonSetItem.Type.DESH.ordinal()))
                .inputItems(new ComparableStack(NtmItems.INGOT_DESH.get(), 24),
                        new RecipesCommon.TagStack(ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "ingots_plastic")), 12),
                        new RecipesCommon.TagStack(NtmTags.Items.PLATES_COPPER, 24),
                        new ComparableStack(NtmItems.INGOT_TUNGSTEN.get(), 16),
                        new ComparableStack(NtmItems.PIPE_DURA_STEEL.get(), 4)));

        // Original ass.dieselgen, normal inputs only; no blueprint pool or unavailable expensive-mode materials.
        this.register(new GenericRecipe("ass.dieselgen").setup(200, 100).outputItems(new ItemStack(NtmBlocks.MACHINE_DIESEL.get(), 1))
                .inputItems(new ComparableStack(NtmItems.SHELL_STEEL.get(), 1),
                        NtmItems.castPlateIngredient(CastPlateItem.Type.COPPER, 2),
                        new ComparableStack(NtmItems.COIL_COPPER.get(), 4)));

        // Original ass.tank (normal mode only: the expensive mode uses item_expensive, which NEO does not have)
        this.register(new GenericRecipe("ass.tank").setup(200, 100).outputItems(new ItemStack(NtmBlocks.MACHINE_FLUID_TANK.get(), 1))
                .inputItems(new RecipesCommon.TagStack(NtmTags.Items.PLATES_STEEL, 8),
                        new ComparableStack(NtmItems.SHELL_STEEL.get(), 4)));
        // Original ass.chemplant (normal mode only: the expensive mode uses item_expensive, which NEO does not have).
        // NEO has no steel ingot or copper pipe tag, so the plain items stand in for the ore dictionary entries.
        this.register(new GenericRecipe("ass.chemplant").setup(200, 100).outputItems(new ItemStack(NtmBlocks.MACHINE_CHEMICAL_PLANT.get(), 1))
                .inputItems(new ComparableStack(NtmItems.INGOT_STEEL.get(), 8),
                        new ComparableStack(NtmItems.PIPE_COPPER.get(), 2),
                        new ComparableStack(NtmItems.PLATE_POLYMER.get(), 16),
                        new ComparableStack(NtmItems.MOTOR.get(), 2),
                        new ComparableStack(NtmItems.COIL_TUNGSTEN.get(), 2),
                        new ComparableStack(NtmItems.CIRCUIT_ANALOG_BOARD.get(), 1)));
        // Original ass.purex (AssemblyMachineRecipes.java:270-272), normal mode only and in both enable528 settings: the expensive
        // mode uses item_expensive, which NEO does not have. The steel shell and rubber pipe ore dictionary entries are plain items.
        this.register(new GenericRecipe("ass.purex").setup(300, 100).outputItems(new ItemStack(NtmBlocks.MACHINE_PUREX.get(), 1))
                .inputItems(new ComparableStack(NtmItems.SHELL_STEEL.get(), 4),
                        new ComparableStack(NtmItems.PIPE_RUBBER.get(), 8),
                        NtmItems.castPlateIngredient(CastPlateItem.Type.LEAD, 4),
                        new ComparableStack(NtmItems.MOTOR_DESH.get(), 1),
                        new ComparableStack(NtmItems.CIRCUIT_INTEGRATED_BOARD.get(), 4)));
        // Original ass.crackingtower (AssemblyMachineRecipes.java:316-319), normal mode only: no setPools528, since NEO
        // has no blueprint source in survival for 528. pools (Goal 13A's booklets and blueprint chests only give alt. and
        // discover. pools), and no inputItemsEx, since NEO has no item_expensive.
        // NEO has no steel shell, desh ingot or niobium ingot tag, so the plain items stand in for the ore dictionary entries.
        this.register(new GenericRecipe("ass.crackingtower").setup(200, 100).outputItems(new ItemStack(NtmBlocks.MACHINE_CATALYTIC_CRACKER.get(), 1))
                .inputItems(new ComparableStack(NtmBlocks.STEEL_SCAFFOLD.get(), 16),
                        new ComparableStack(NtmItems.SHELL_STEEL.get(), 6),
                        new ComparableStack(NtmItems.INGOT_DESH.get(), 12),
                        new ComparableStack(NtmItems.INGOT_NIOBIUM.get(), 4)));

        // Original crafting parts and alternates of the alt..circuit pool (AssemblyMachineRecipes.java:126-148), registered only outside 528
        // mode like the original's block, in the original order. The pool name keeps the original's double dot.
        // NEO has no iron plate, fine wire, niobium ingot or Cs-137 powder tag, and ntm:any_rubbers also holds bio rubber,
        // which the original's rubber ingot entry does not, so the plain items stand in for the ore dictionary entries;
        // any plastic ingot is ntm:ingots_plastic.
        if(!NtmConfig.enable528()) {
            // Original ass.chip (AssemblyMachineRecipes.java:127-128); circuit SILICON is the printed silicon wafer.
            // ass.chipBismoid, ass.chipQuantum and ass.atomicClock (:129-134) are deferred with their inputs (GOAL13B B4).
            this.register(new GenericRecipe("ass.chip").setup(50, 250).outputItems(new ItemStack(NtmItems.CIRCUIT_MICROCHIP.get(), 1))
                    .inputItems(new ComparableStack(NtmItems.PLATE_POLYMER.get(), 1),
                            new ComparableStack(NtmItems.CIRCUIT_PRINTED_SILICON_WAFER.get(), 1),
                            new ComparableStack(NtmItems.WIRE_GOLD.get(), 1)));

            this.register(new GenericRecipe("ass.analogAlt").setupNamed(200, 250L).outputItems(new ItemStack(NtmItems.CIRCUIT_ANALOG_BOARD.get(), 1))
                    .inputItems(new ComparableStack(NtmItems.CIRCUIT_PRINTED_BOARD.get(), 4),
                            new RecipesCommon.TagStack(ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "ingots_plastic")), 4),
                            new ComparableStack(NtmItems.WIRE_TUNGSTEN.get(), 8),
                            new ComparableStack(NtmItems.INGOT_NIOBIUM.get(), 1))
                    .setPools("alt..circuit"));
            this.register(new GenericRecipe("ass.factorioChip").setupNamed(300, 20_000L).outputItems(new ItemStack(NtmItems.CIRCUIT_INTEGRATED_BOARD.get(), 1))
                    .inputItems(new ComparableStack(NtmItems.INGOT_RUBBER.get(), 2),
                            new ComparableStack(NtmItems.PLATE_IRON.get(), 4),
                            new ComparableStack(NtmItems.WIRE_COPPER.get(), 8))
                    .setPools("alt..circuit"));
            this.register(new GenericRecipe("ass.atomicClockAlt").setupNamed(300, 20_000L).outputItems(new ItemStack(NtmItems.CIRCUIT_ATOMIC_CLOCK.get(), 4))
                    .inputItems(new RecipesCommon.TagStack(ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "ingots_plastic")), 4),
                            new ComparableStack(NtmItems.CIRCUIT_MICROCHIP.get(), 3),
                            new ComparableStack(NtmItems.POWDER_CS137.get(), 1))
                    .setPools("alt..circuit"));
        }

        // Original ass.arcfurnace (AssemblyMachineRecipes.java:286-288), registered in every mode: the original keeps it
        // outside the !enable528 block, although GOAL13B B4 lists it with that block. No inputItemsEx, since NEO has no
        // item_expensive; the steel cast plate stands in for STEEL.plateCast().
        this.register(new GenericRecipe("ass.arcfurnace").setup(200, 100).outputItems(new ItemStack(NtmBlocks.MACHINE_ARC_FURNACE.get(), 1))
                .inputItems(new RecipesCommon.TagStack(ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "any_concrete")), 12),
                        new RecipesCommon.TagStack(ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "ingots_plastic")), 8),
                        new ComparableStack(NtmItems.INGOT_FIREBRICK.get(), 16),
                        NtmItems.castPlateIngredient(CastPlateItem.Type.STEEL, 8),
                        new ComparableStack(NtmBlocks.TRANSFORMER.get(), 1),
                        new ComparableStack(NtmItems.CIRCUIT_ANALOG_BOARD.get(), 1)));

        // Original normal ass.acidizer (AssemblyMachineRecipes.java:289-291), registered in every mode like the original;
        // BASIC is the integrated circuit board, the expensive branch is not migrated (NEO has no item_expensive).
        this.register(new GenericRecipe("ass.acidizer").setup(200, 100).outputItems(new ItemStack(NtmBlocks.MACHINE_CRYSTALLIZER.get(), 1))
                .inputItems(NtmItems.castPlateWeldedIngredient(CastPlateItem.Type.STEEL, 2),
                        new ComparableStack(NtmItems.SHELL_TITANIUM.get(), 3),
                        new ComparableStack(NtmItems.INGOT_DESH.get(), 4),
                        new ComparableStack(NtmItems.MOTOR.get(), 1),
                        new ComparableStack(NtmItems.CIRCUIT_INTEGRATED_BOARD.get(), 2)));

        // Original normal ass.iturbine (AssemblyMachineRecipes.java:434-436), registered in every mode like the original;
        // the expensive branch is not migrated (NEO has no item_expensive). STEEL.plate() is c:plates/steel; ntm:any_rubbers
        // also holds bio rubber, which RUBBER.ingot() does not, so the plain rubber ingot stands in (as ass.coker);
        // dense gold wire and the dura pipe as ass.turbofan; BASIC is the integrated circuit board.
        this.register(new GenericRecipe("ass.iturbine").setup(200, 100).outputItems(new ItemStack(NtmBlocks.MACHINE_INDUSTRIAL_TURBINE.get(), 1))
                .inputItems(new RecipesCommon.TagStack(NtmTags.Items.PLATES_STEEL, 16),
                        new ComparableStack(NtmItems.INGOT_RUBBER.get(), 4),
                        new ComparableStack(NtmItems.TURBINE_TITANIUM.get(), 2),
                        new ComparableStack(MetaHelper.newStack(NtmItems.WIRE_DENSE.get(), 4, WireDenseItem.Type.GOLD.meta)),
                        new ComparableStack(NtmItems.PIPE_DURA_STEEL.get(), 4),
                        new ComparableStack(NtmItems.CIRCUIT_INTEGRATED_BOARD.get(), 2)));

        // Original normal ass.cirnox (AssemblyMachineRecipes.java:524-527), registered in every mode like the original;
        // the expensive branch is not migrated (NEO has no item_expensive). NEO keeps its machine_zirnox id for the
        // original reactor_zirnox. B.ingot() is the boron ingot (OreDictManager.java:196); the plain rubber ingot stands
        // in for RUBBER.ingot() as in ass.iturbine; BASIC is the integrated circuit board.
        this.register(new GenericRecipe("ass.cirnox").setup(600, 100).outputItems(new ItemStack(NtmBlocks.REACTOR_ZIRNOX.get(), 1))
                .inputItems(new ComparableStack(NtmItems.SHELL_STEEL.get(), 4),
                        new ComparableStack(NtmItems.PIPE_STEEL.get(), 8),
                        new ComparableStack(NtmItems.INGOT_BORON.get(), 8),
                        new ComparableStack(NtmItems.INGOT_GRAPHITE.get(), 16),
                        new ComparableStack(NtmItems.INGOT_RUBBER.get(), 16),
                        new RecipesCommon.TagStack(ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "any_concrete")), 16),
                        new ComparableStack(NtmItems.CIRCUIT_INTEGRATED_BOARD.get(), 4)));
    }
}
