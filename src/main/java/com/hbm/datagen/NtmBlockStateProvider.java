package com.hbm.datagen;

import com.google.gson.JsonObject;
import com.hbm.blocks.ICustomBlockModelRegister;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.generic.BarbedWireBlock;
import com.hbm.blocks.generic.LayeringBlock;
import com.hbm.blocks.generic.OreBasaltBlock;
import com.hbm.blocks.generic.OreBasaltBlock.BasaltOreType;
import com.hbm.blocks.generic.SellafieldSlakedBlock;
import com.hbm.blocks.generic.SteelGrateBlock;
import com.hbm.blocks.network.ConveyorBaseBlock;
import com.hbm.blocks.network.ConveyorBlock;
import com.hbm.blocks.network.ConveyorChuteBlock;
import com.hbm.blocks.network.ConveyorLiftBlock;
import com.hbm.blocks.network.CraneBaseBlock;
import com.hbm.blocks.network.FluidDuctConnectingBlock;
import com.hbm.blocks.states.NtmBlockStateProperties;
import com.hbm.main.NuclearTechMod;
import com.hbm.render.model.loader.NtmGeometry.BakedModelType;
import net.minecraft.client.renderer.block.model.BlockModel;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.data.PackOutput;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.BooleanProperty;
import net.neoforged.neoforge.client.model.generators.*;
import net.neoforged.neoforge.common.data.ExistingFileHelper;
import net.neoforged.neoforge.registries.DeferredBlock;

import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Objects;

public class NtmBlockStateProvider extends BlockStateProvider {

    public NtmBlockStateProvider(PackOutput output, ExistingFileHelper helper) {
        super(output, NuclearTechMod.MODID, helper);
    }

    @Override
    protected void registerStatesAndModels() {

        NtmBlocks.BLOCKS.getEntries().forEach(holder -> {
            Block block = holder.get();

            if(block instanceof ICustomBlockModelRegister icbmr) {
                ResourceLocation loc = Objects.requireNonNull(BuiltInRegistries.BLOCK.getKey(block));
                icbmr.registerModel(this, loc);
            }
        });

        this.simpleCubeAllBlock(NtmBlocks.STONE_CRACKED);
        this.simpleCubeAllBlock(NtmBlocks.DIRT_DEAD);
        this.simpleCubeAllBlock(NtmBlocks.DIRT_OILY);
        this.simpleCubeAllBlock(NtmBlocks.SAND_OILY);
        this.simpleCubeAllBlock(NtmBlocks.SAND_RED_OILY);
        this.layeringBlock(NtmBlocks.OIL_SPILL.get(), modLoc("block/oil_spill"));
        this.simpleCubeAllBlock(NtmBlocks.ORE_OIL);
        this.simpleCubeAllBlock(NtmBlocks.ORE_OIL_EMPTY);
        this.simpleCubeAllBlock(NtmBlocks.ORE_OIL_SAND);
        this.simpleCubeAllBlock(NtmBlocks.ORE_BEDROCK_OIL);
        this.simpleCubeAllBlock(NtmBlocks.ORE_URANIUM);
        this.simpleCubeAllBlock(NtmBlocks.ORE_URANIUM_DEEPSLATE);
        this.simpleCubeAllBlock(NtmBlocks.ORE_URANIUM_SCORCHED);
        this.simpleCubeAllBlock(NtmBlocks.ORE_BERYLLIUM);
        this.simpleCubeAllBlock(NtmBlocks.ORE_BERYLLIUM_DEEPSLATE);
        this.simpleCubeAllBlock(NtmBlocks.ORE_TUNGSTEN);
        this.simpleCubeAllBlock(NtmBlocks.ORE_TUNGSTEN_DEEPSLATE);
        this.simpleCubeAllBlock(NtmBlocks.ORE_TITANIUM);
        this.simpleCubeAllBlock(NtmBlocks.ORE_TITANIUM_DEEPSLATE);
        this.simpleCubeAllBlock(NtmBlocks.ORE_LEAD);
        this.simpleCubeAllBlock(NtmBlocks.ORE_LEAD_DEEPSLATE);
        this.simpleCubeAllBlock(NtmBlocks.ORE_ALUMINIUM);
        this.simpleCubeAllBlock(NtmBlocks.ORE_ALUMINIUM_DEEPSLATE);
        this.simpleCubeAllBlock(NtmBlocks.ORE_ASBESTOS);
        this.simpleCubeAllBlock(NtmBlocks.ORE_ASBESTOS_DEEPSLATE);
        this.simpleCubeAllBlock(NtmBlocks.ORE_THORIUM);
        this.simpleCubeAllBlock(NtmBlocks.ORE_THORIUM_DEEPSLATE);
        this.simpleCubeAllBlock(NtmBlocks.ORE_NITER);
        this.simpleCubeAllBlock(NtmBlocks.ORE_NITER_DEEPSLATE);
        this.simpleCubeAllBlock(NtmBlocks.ORE_COBALT);
        this.simpleCubeAllBlock(NtmBlocks.ORE_COBALT_DEEPSLATE);
        this.simpleCubeAllBlock(NtmBlocks.ORE_CINNABAR);
        this.simpleCubeAllBlock(NtmBlocks.ORE_CINNABAR_DEEPSLATE);
        this.simpleCubeAllBlock(NtmBlocks.ORE_FLUORITE);
        this.simpleCubeAllBlock(NtmBlocks.ORE_FLUORITE_DEEPSLATE);
        this.simpleCubeAllBlock(NtmBlocks.ORE_METEOR_IRON);
        this.simpleCubeAllBlock(NtmBlocks.ORE_METEOR_COBALT);
        this.simpleCubeAllBlock(NtmBlocks.ORE_METEOR_ALUMINIUM);
        this.simpleCubeAllBlock(NtmBlocks.ORE_METEOR_COPPER);
        this.simpleCubeAllBlock(NtmBlocks.ORE_METEOR_RARE);
        this.simpleCubeAllBlock(NtmBlocks.ORE_RARE);
        this.simpleCubeAllBlock(NtmBlocks.ORE_RARE_DEEPSLATE);
        this.simpleCubeAllBlock(NtmBlocks.ORE_SULFUR);
        this.simpleCubeAllBlock(NtmBlocks.ORE_SULFUR_DEEPSLATE);
        this.simpleCubeAllBlock(NtmBlocks.ORE_LIGNITE);
        this.simpleCubeAllBlock(NtmBlocks.ORE_DEEPSLATE_LIGNITE);
        this.simpleCubeAllBlock(NtmBlocks.ORE_SCHRABIDIUM);
        this.simpleCubeAllBlock(NtmBlocks.ORE_NETHER_URANIUM);
        this.simpleCubeAllBlock(NtmBlocks.ORE_NETHER_URANIUM_SCORCHED);
        this.simpleCubeAllBlock(NtmBlocks.ORE_NETHER_SCHRABIDIUM);
        this.simpleCubeAllBlock(NtmBlocks.ORE_NETHER_TUNGSTEN);
        this.simpleCubeAllBlock(NtmBlocks.ORE_NETHER_SULFUR);
        this.simpleCubeAllBlock(NtmBlocks.ORE_NETHER_FIRE);
        this.simpleCubeAllBlock(NtmBlocks.ORE_NETHER_COAL);
        this.simpleCubeAllBlock(NtmBlocks.ORE_NETHER_SMOLDERING);
        this.simpleCubeAllBlock(NtmBlocks.ORE_NETHER_COBALT);
        this.simpleCubeAllBlock(NtmBlocks.ORE_TIKITE);
        this.simpleCubeAllBlock(NtmBlocks.ORE_COLTAN);
        this.simpleCubeAllBlock(NtmBlocks.ORE_GNEISS_URANIUM);
        this.simpleCubeAllBlock(NtmBlocks.ORE_GNEISS_URANIUM_SCORCHED);
        this.simpleCubeAllBlock(NtmBlocks.ORE_NETHER_PLUTONIUM);
        this.simpleCubeAllBlock(NtmBlocks.ORE_GNEISS_SCHRABIDIUM);
        // Original ModBlocks stone_gneiss uses the stone_gneiss_var icon
        this.simpleBlockWithItem(NtmBlocks.STONE_GNEISS, this.models().cubeAll(name(NtmBlocks.STONE_GNEISS), modLoc("block/stone_gneiss_var")));
        this.simpleCubeAllBlock(NtmBlocks.ORE_GNEISS_IRON);
        this.simpleCubeAllBlock(NtmBlocks.ORE_GNEISS_GOLD);
        this.simpleCubeAllBlock(NtmBlocks.ORE_GNEISS_COPPER);
        this.simpleCubeAllBlock(NtmBlocks.ORE_GNEISS_ASBESTOS);
        this.simpleCubeAllBlock(NtmBlocks.ORE_GNEISS_LITHIUM);
        this.simpleCubeAllBlock(NtmBlocks.ORE_GNEISS_RARE);
        this.simpleCubeAllBlock(NtmBlocks.ORE_GNEISS_GAS);
        this.simpleCubeAllBlock(NtmBlocks.RESOURCE_LIMESTONE);
        this.simpleCubeAllBlock(NtmBlocks.RESOURCE_BAUXITE);
        this.simpleCubeAllBlock(NtmBlocks.RESOURCE_HEMATITE);
        this.simpleCubeAllBlock(NtmBlocks.RESOURCE_MALACHITE);
        this.simpleCubeAllBlock(NtmBlocks.RESOURCE_CHRYSOTILE);
        this.simpleCubeAllBlock(NtmBlocks.RESOURCE_SULFUROUS_STONE);
        this.simpleCubeAllBlock(NtmBlocks.STONE_DEPTH);
        this.simpleCubeAllBlock(NtmBlocks.STONE_DEPTH_NETHER);
        this.simpleCubeAllBlock(NtmBlocks.ORE_DEPTH_CINNABAR);
        this.simpleCubeAllBlock(NtmBlocks.ORE_DEPTH_ZIRCONIUM);
        this.simpleCubeAllBlock(NtmBlocks.ORE_DEPTH_BORAX);
        this.simpleCubeAllBlock(NtmBlocks.ORE_DEPTH_NETHER_NEODYMIUM);
        this.simpleCubeAllBlock(NtmBlocks.CLUSTER_DEPTH_IRON);
        this.simpleCubeAllBlock(NtmBlocks.CLUSTER_DEPTH_TITANIUM);
        this.simpleCubeAllBlock(NtmBlocks.CLUSTER_DEPTH_TUNGSTEN);
        this.simpleCubeAllBlock(NtmBlocks.ORE_ALEXANDRITE);
        this.simpleCubeAllBlock(NtmBlocks.CLUSTER_IRON);
        this.simpleCubeAllBlock(NtmBlocks.CLUSTER_TITANIUM);
        this.simpleCubeAllBlock(NtmBlocks.CLUSTER_ALUMINIUM);
        this.simpleCubeAllBlock(NtmBlocks.CLUSTER_COPPER);
        this.simpleCubeAllBlock(NtmBlocks.DECO_ALUMINIUM);
        this.simpleCubeAllBlock(NtmBlocks.DECO_BERYLLIUM);
        this.simpleCubeAllBlock(NtmBlocks.DECO_LEAD);
        this.simpleCubeAllBlock(NtmBlocks.DECO_STEEL);
        this.simpleCubeAllBlock(NtmBlocks.DECO_RUSTY_STEEL);
        this.simpleCubeAllBlock(NtmBlocks.DECO_TITANIUM);
        this.simpleCubeAllBlock(NtmBlocks.DECO_TUNGSTEN);
        this.simpleCubeAllBlock(NtmBlocks.DECO_RED_COPPER);
        this.simpleCubeAllBlock(NtmBlocks.DECO_ASBESTOS);

        this.registerOreBasalt();

        this.logBlock(NtmBlocks.BASALT.get());
        this.simpleCubeAllBlock(NtmBlocks.BASALT_SMOOTH);
        this.simpleCubeAllBlock(NtmBlocks.BASALT_BRICK);
        this.simpleCubeAllBlock(NtmBlocks.BASALT_POLISHED);
        this.simpleCubeAllBlock(NtmBlocks.BASALT_TILES);

        this.simpleCubeAllBlock(NtmBlocks.BLOCK_SCRAP);

        this.particleOnlyBlock(NtmBlocks.BOBBLEHEAD, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.PLUSHIE, modLoc("block/block_fiberglass_side"));
        this.simpleCubeAllBlock(NtmBlocks.PLANT_FLOWER);

        this.simpleCubeAllBlock(NtmBlocks.GRAVEL_OBSIDIAN);
        this.simpleCubeAllBlock(NtmBlocks.GRAVEL_DIAMOND);
        this.simpleCubeAllBlock(NtmBlocks.MOON_TURF);

        this.simpleCubeAllBlock(NtmBlocks.ASPHALT);
        this.simpleCubeAllBlock(NtmBlocks.ASPHALT_LIGHT);
        this.simpleCubeAllBlock(NtmBlocks.REINFORCED_STONE);

        this.simpleCubeAllBlock(NtmBlocks.BRICK_CONCRETE);
        this.simpleCubeAllBlock(NtmBlocks.BRICK_CONCRETE_MOSSY);
        this.simpleCubeAllBlock(NtmBlocks.BRICK_CONCRETE_CRACKED);
        this.simpleCubeAllBlock(NtmBlocks.BRICK_CONCRETE_BROKEN);
        this.simpleBlockWithItem(
                NtmBlocks.BRICK_CONCRETE_MARKED,
                this.models().cubeColumn(
                        name(NtmBlocks.BRICK_CONCRETE_MARKED),
                        blockTexture(NtmBlocks.BRICK_CONCRETE_MARKED),
                        blockTexture(NtmBlocks.BRICK_CONCRETE)
                )
        );
        this.simpleCubeAllBlock(NtmBlocks.BRICK_OBSIDIAN);
        this.simpleCubeAllBlock(NtmBlocks.BRICK_LIGHT);
        this.simpleCubeAllBlock(NtmBlocks.BRICK_ASBESTOS);
        this.simpleCubeAllBlock(NtmBlocks.BRICK_FIRE);
        this.simpleCubeAllBlock(NtmBlocks.CONCRETE);
        this.simpleCubeAllBlock(NtmBlocks.CONCRETE_SMOOTH);
        this.simpleCubeAllBlock(NtmBlocks.CONCRETE_ASBESTOS);
        this.simpleCubeAllBlock(NtmBlocks.DUCRETE);
        this.simpleCubeAllBlock(NtmBlocks.DUCRETE_SMOOTH);
        this.simpleCubeAllBlock(NtmBlocks.DUCRETE_REINFORCED);
        this.simpleCubeAllBlock(NtmBlocks.DUCRETE_BRICK);
        this.simpleCubeAllBlock(NtmBlocks.REINFORCED_LAMINATE);
        this.simpleCubeAllBlock(NtmBlocks.STEEL_SCAFFOLD);
        this.steelBeamBlock();
        this.steelGrateBlock();
        this.particleOnlyBlock(NtmBlocks.FRACTION_SPACER, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.MACHINE_FRACTION_TOWER, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.MACHINE_COMPRESSOR, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.MACHINE_COKER, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.MACHINE_MIXER, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.MACHINE_COMBUSTION_ENGINE, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.MACHINE_TURBOFAN, modLoc("block/block_steel"));
        this.simpleCubeAllBlock(NtmBlocks.SAND_QUARTZ);
        this.simpleCubeAllBlock(NtmBlocks.GLASS_QUARTZ);
        this.simpleCubeAllBlock(NtmBlocks.SAND_BORON);
        this.simpleCubeAllBlock(NtmBlocks.SAND_LEAD);
        this.simpleCubeAllBlock(NtmBlocks.GLASS_BORON);
        this.simpleCubeAllBlock(NtmBlocks.GLASS_LEAD);
        this.simpleCubeAllBlock(NtmBlocks.TRANSFORMER);

        this.slabBlock(NtmBlocks.BRICK_CONCRETE_SLAB.get(), blockTexture(NtmBlocks.BRICK_CONCRETE), blockTexture(NtmBlocks.BRICK_CONCRETE));
        this.slabBlock(NtmBlocks.BRICK_CONCRETE_MOSSY_SLAB.get(), blockTexture(NtmBlocks.BRICK_CONCRETE_MOSSY), blockTexture(NtmBlocks.BRICK_CONCRETE_MOSSY));
        this.slabBlock(NtmBlocks.BRICK_CONCRETE_CRACKED_SLAB.get(), blockTexture(NtmBlocks.BRICK_CONCRETE_CRACKED), blockTexture(NtmBlocks.BRICK_CONCRETE_CRACKED));
        this.slabBlock(NtmBlocks.BRICK_CONCRETE_BROKEN_SLAB.get(), blockTexture(NtmBlocks.BRICK_CONCRETE_BROKEN), blockTexture(NtmBlocks.BRICK_CONCRETE_BROKEN));
        this.blockItem(NtmBlocks.BRICK_CONCRETE_SLAB);
        this.blockItem(NtmBlocks.BRICK_CONCRETE_MOSSY_SLAB);
        this.blockItem(NtmBlocks.BRICK_CONCRETE_CRACKED_SLAB);
        this.blockItem(NtmBlocks.BRICK_CONCRETE_BROKEN_SLAB);

        this.stairsBlock(NtmBlocks.BRICK_CONCRETE_STAIRS.get(), blockTexture(NtmBlocks.BRICK_CONCRETE));
        this.stairsBlock(NtmBlocks.BRICK_CONCRETE_MOSSY_STAIRS.get(), blockTexture(NtmBlocks.BRICK_CONCRETE_MOSSY));
        this.stairsBlock(NtmBlocks.BRICK_CONCRETE_CRACKED_STAIRS.get(), blockTexture(NtmBlocks.BRICK_CONCRETE_CRACKED));
        this.stairsBlock(NtmBlocks.BRICK_CONCRETE_BROKEN_STAIRS.get(), blockTexture(NtmBlocks.BRICK_CONCRETE_BROKEN));
        this.blockItem(NtmBlocks.BRICK_CONCRETE_STAIRS);
        this.blockItem(NtmBlocks.BRICK_CONCRETE_MOSSY_STAIRS);
        this.blockItem(NtmBlocks.BRICK_CONCRETE_CRACKED_STAIRS);
        this.blockItem(NtmBlocks.BRICK_CONCRETE_BROKEN_STAIRS);

        this.registerBarbedWire();
        this.registerSpikes();

        this.simpleCubeBottomTopBlock(NtmBlocks.WASTE_EARTH);
        this.simpleBlockWithItem(
                NtmBlocks.WASTE_MYCELIUM,
                this.models().cubeBottomTop(
                        name(NtmBlocks.WASTE_MYCELIUM),
                        blockTexture(NtmBlocks.WASTE_MYCELIUM, "_side"),
                        blockTexture(NtmBlocks.WASTE_EARTH, "_bottom"),
                        blockTexture(NtmBlocks.WASTE_MYCELIUM, "_top")
                )
        );
        this.simpleCubeAllBlock(NtmBlocks.WASTE_TRINITITE);
        this.simpleCubeAllBlock(NtmBlocks.WASTE_TRINITITE_RED);
        this.logBlock(NtmBlocks.WASTE_LOG.get());
        this.simpleBlockWithItem(
                NtmBlocks.WASTE_LEAVES,
                this.models().cubeAll(
                        name(NtmBlocks.WASTE_LEAVES),
                        blockTexture(NtmBlocks.WASTE_LEAVES)
                ).renderType("cutout_mipped")
        );
        this.simpleCubeAllBlock(NtmBlocks.WASTE_PLANKS);
        this.simpleCubeAllBlock(NtmBlocks.FROZEN_DIRT);
        this.simpleBlockWithItem(
                NtmBlocks.FROZEN_GRASS,
                this.models().cubeBottomTop(
                        name(NtmBlocks.FROZEN_GRASS),
                        blockTexture(NtmBlocks.FROZEN_GRASS, "_side"),
                        blockTexture(NtmBlocks.FROZEN_DIRT),
                        blockTexture(NtmBlocks.FROZEN_GRASS, "_top")
                )
        );
        this.logBlock(NtmBlocks.FROZEN_LOG.get());
        this.simpleCubeAllBlock(NtmBlocks.FROZEN_PLANKS);
        this.layeringBlock(NtmBlocks.LEAVES_LAYER.get(), modLoc("block/waste_leaves"));
        ResourceLocation texture = modLoc("block/ash");
        ModelFile falloutModel = models()
                .getBuilder("fallout")
                .parent(new ModelFile.UncheckedModelFile("block/block"))
                .texture("all", texture)
                .texture("particle", texture)
                .element()
                .from(0, 0, 0)
                .to(16, 2, 16)
                .face(Direction.UP).texture("#all").end()
                .face(Direction.DOWN).texture("#all").end()
                .face(Direction.NORTH).texture("#all").end()
                .face(Direction.SOUTH).texture("#all").end()
                .face(Direction.WEST).texture("#all").end()
                .face(Direction.EAST).texture("#all").end()
                .end();
        this.getVariantBuilder(NtmBlocks.FALLOUT.get()).partialState().setModels(new ConfiguredModel(falloutModel));
        this.sellafieldSlaked(NtmBlocks.SELLAFIELD_SLAKED.get(), "sellafield_slaked");
        this.sellafieldOre(NtmBlocks.ORE_SELLAFIELD_DIAMOND.get(), "sellafield_ore_diamond", "block/ore_diamond_overlay");
        this.sellafieldOre(NtmBlocks.ORE_SELLAFIELD_EMERALD.get(), "sellafield_ore_emerald", "block/ore_emerald_overlay");
        this.sellafieldSlaked(NtmBlocks.SELLAFIELD_BEDROCK.get(), "sellafield_bedrock");

        this.particleOnlyBlock(NtmBlocks.NUKE_GADGET, blockTexture(NtmBlocks.NUKE_GADGET));
        this.particleOnlyBlock(NtmBlocks.NUKE_LITTLE_BOY, blockTexture(NtmBlocks.NUKE_LITTLE_BOY));
        this.particleOnlyBlock(NtmBlocks.NUKE_FAT_MAN, blockTexture(NtmBlocks.NUKE_FAT_MAN));
        this.particleOnlyBlock(NtmBlocks.NUKE_IVY_MIKE, blockTexture(NtmBlocks.NUKE_IVY_MIKE));
        this.particleOnlyBlock(NtmBlocks.NUKE_TSAR_BOMBA, blockTexture(NtmBlocks.NUKE_TSAR_BOMBA));
        this.particleOnlyBlock(NtmBlocks.NUKE_PROTOTYPE, blockTexture(NtmBlocks.NUKE_PROTOTYPE));
        this.particleOnlyBlock(NtmBlocks.NUKE_FLEIJA, blockTexture(NtmBlocks.NUKE_FLEIJA));
        this.particleOnlyBlock(NtmBlocks.NUKE_SOLINIUM, blockTexture(NtmBlocks.NUKE_SOLINIUM));
        this.particleOnlyBlock(NtmBlocks.NUKE_N2, blockTexture(NtmBlocks.NUKE_N2));
        this.particleOnlyBlock(NtmBlocks.NUKE_FSTBMB, blockTexture(NtmBlocks.NUKE_FSTBMB));

        this.particleOnlyBlock(NtmBlocks.CRASHED_BOMB, modLoc("block/block_rust"), true);
        this.simpleCubeBottomTopBlock(NtmBlocks.DYNAMITE);
        this.simpleCubeBottomTopBlock(NtmBlocks.TNT);
        this.simpleCubeBottomTopBlock(NtmBlocks.SEMTEX);
        this.simpleCubeBottomTopBlock(NtmBlocks.C4);
        this.simpleCubeBottomTopBlock(NtmBlocks.FISSURE_BOMB);

        this.particleOnlyBlock(NtmBlocks.MINE_AP, blockTexture(NtmBlocks.MINE_AP));
        this.particleOnlyBlock(NtmBlocks.MINE_HE, blockTexture(NtmBlocks.MINE_HE));
        this.particleOnlyBlock(NtmBlocks.MINE_SHRAP, blockTexture(NtmBlocks.MINE_SHRAP));
        this.particleOnlyBlock(NtmBlocks.MINE_FAT, blockTexture(NtmBlocks.MINE_FAT));
        this.particleOnlyBlock(NtmBlocks.MINE_NAVAL, blockTexture(NtmBlocks.MINE_NAVAL));

        this.simpleCubeAllBlock(NtmBlocks.DET_CHARGE);
        this.registerDetCord();
        this.cubeTop(NtmBlocks.DET_NUKE);
        this.cubeTop(NtmBlocks.DET_MINER);
        this.barrelLoaderBlockItem(NtmBlocks.BARREL_RED.get(), blockTexture(NtmBlocks.BARREL_RED));
        this.barrelLoaderBlockItem(NtmBlocks.BARREL_PINK.get(), blockTexture(NtmBlocks.BARREL_PINK));
        this.barrelLoaderBlockItem(NtmBlocks.BARREL_LOX.get(), blockTexture(NtmBlocks.BARREL_LOX));
        this.barrelLoaderBlockItem(NtmBlocks.BARREL_TAINT.get(), blockTexture(NtmBlocks.BARREL_TAINT));
        this.barrelLoaderBlockItem(NtmBlocks.BARREL_PLASTIC.get(), blockTexture(NtmBlocks.BARREL_PLASTIC));
        this.barrelLoaderBlockItem(NtmBlocks.BARREL_STEEL.get(), blockTexture(NtmBlocks.BARREL_STEEL));
        this.barrelLoaderBlockItem(NtmBlocks.BARREL_CORRODED.get(), blockTexture(NtmBlocks.BARREL_CORRODED));
        this.barrelLoaderBlockItem(NtmBlocks.BARREL_TCALLOY.get(), blockTexture(NtmBlocks.BARREL_TCALLOY));
        this.crateBlock(NtmBlocks.CRATE_IRON.get(), "crate_iron_side", "crate_iron_top");
        this.crateBlock(NtmBlocks.CRATE_TUNGSTEN.get(), "crate_tungsten_side", "crate_tungsten_top");
        this.crateBlock(NtmBlocks.CRATE_STEEL.get(), "crate_steel_side", "crate_steel_top");
        this.crateBlock(NtmBlocks.CRATE_DESH.get(), "crate_desh_side", "crate_desh_top");
        this.crateBlock(NtmBlocks.CRATE_TEMPLATE.get(), "crate_template", "crate_template");

        this.particleOnlyBlock(NtmBlocks.GEIGER, blockTexture(NtmBlocks.GEIGER));

        this.simpleCubeAllBlock(NtmBlocks.PRESS_PREHEATER);
        this.particleOnlyBlock(NtmBlocks.MACHINE_PRESS, blockTexture(NtmBlocks.MACHINE_PRESS));
        this.particleOnlyBlock(NtmBlocks.MACHINE_WELL, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.MACHINE_PUMPJACK, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.MACHINE_FRACKING_TOWER, modLoc("block/block_steel"));

        this.registerCable();

        this.registerFluidDuct();

        this.registerNetworkControls();

        this.particleOnlyBlock(NtmBlocks.MACHINE_BATTERY_SOCKET, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.MACHINE_BATTERY_REDD, modLoc("block/block_steel"));
        // pylons, connectors and the substation: drawn by their renderers; particles from the original block icons (ModBlocks.java:1868-1877)
        this.particleOnlyBlock(NtmBlocks.RED_CONNECTOR, modLoc("block/red_connector"));
        this.particleOnlyBlock(NtmBlocks.RED_CONNECTOR_SUPER, modLoc("block/red_connector"));
        this.particleOnlyBlock(NtmBlocks.RED_PYLON, modLoc("block/red_pylon"));
        this.particleOnlyBlock(NtmBlocks.RED_PYLON_STEEL, modLoc("block/red_pylon"));
        this.particleOnlyBlock(NtmBlocks.RED_PYLON_MEDIUM_WOOD, modLoc("block/red_pylon"));
        this.particleOnlyBlock(NtmBlocks.RED_PYLON_MEDIUM_WOOD_TRANSFORMER, modLoc("block/red_pylon"));
        this.particleOnlyBlock(NtmBlocks.RED_PYLON_MEDIUM_STEEL, modLoc("block/red_pylon"));
        this.particleOnlyBlock(NtmBlocks.RED_PYLON_MEDIUM_STEEL_TRANSFORMER, modLoc("block/red_pylon"));
        this.particleOnlyBlock(NtmBlocks.RED_PYLON_LARGE, modLoc("block/red_pylon_large"));
        this.particleOnlyBlock(NtmBlocks.SUBSTATION, modLoc("block/substation"));
        this.particleOnlyBlock(NtmBlocks.PIPE_ANCHOR, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.FLOW_CONTROL_PUMP, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.NETWORK_SEPARATOR, modLoc("block/block_steel"));
        this.conveyorBlocks();
        this.craneBlocks();
        this.conveyorSorterAndBelts();
        this.particleOnlyBlock(NtmBlocks.MACHINE_ASSEMBLY_MACHINE, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.HEAT_BOILER, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.MACHINE_INDUSTRIAL_BOILER, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.HEATER_FIREBOX, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.MACHINE_STIRLING, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.MACHINE_STEAM_ENGINE, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.PUMP_ELECTRIC, modLoc("block/block_steel"));
        // The original texture name is "condenser".
        this.simpleBlockWithItem(NtmBlocks.MACHINE_CONDENSER, this.models().cubeAll(name(NtmBlocks.MACHINE_CONDENSER), modLoc("block/condenser")));
        this.particleOnlyBlock(NtmBlocks.HEATER_OVEN, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.HEATER_OILBURNER, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.HEATER_ELECTRIC, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.HEATER_HEATEX, modLoc("block/block_steel"));
        this.registerMachineShredder();
        this.registerMachineElectricFurnace();
        this.registerRadioTorches();
        this.particleOnlyBlock(NtmBlocks.MACHINE_CHUNGUS, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.MACHINE_INDUSTRIAL_TURBINE, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.MACHINE_FLUID_TANK, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.MACHINE_SOLDERING_STATION, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.MACHINE_REFINERY, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.MACHINE_VACUUM_DISTILL, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.MACHINE_ROTARY_FURNACE, modLoc("block/brick_fire"));
        this.getVariantBuilder(NtmBlocks.PLANT_MUSTARD_WILLOW.get()).forAllStates(state -> {
            int age = state.getValue(com.hbm.blocks.generic.MustardWillowBlock.AGE);
            String part = age < 2 ? "cd" + age
                    : "cd" + age + (state.getValue(com.hbm.blocks.generic.MustardWillowBlock.HALF) == net.minecraft.world.level.block.state.properties.DoubleBlockHalf.UPPER ? "_upper" : "_lower");
            String path = "block/plant_mustard_willow_" + part;
            return ConfiguredModel.builder().modelFile(this.models().cross(path, this.modLoc(path)).renderType("cutout")).build();
        });
        this.particleOnlyBlock(NtmBlocks.MACHINE_CATALYTIC_CRACKER, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.MACHINE_ARC_FURNACE, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.FURNACE_COMBINATION, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.MACHINE_CRUCIBLE, modLoc("block/block_steel"));
        this.registerFoundryMold();
        this.registerFoundryChannel();
        this.registerFoundryTank();
        this.registerFoundryOutlet();
        this.registerFoundryBasin();
        this.particleOnlyBlock(NtmBlocks.MACHINE_BLAST_FURNACE, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.MACHINE_WOOD_BURNER, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.MACHINE_CENTRIFUGE, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.MACHINE_GAS_CENTRIFUGE, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.MACHINE_CRYSTALLIZER, modLoc("block/machine_crystallizer"));
        // Original WasteDrum.java:39-53: waste_drum on top and bottom, waste_drum_side around.
        this.simpleBlockWithItem(
                NtmBlocks.MACHINE_WASTE_DRUM,
                this.models().cubeColumn(
                        name(NtmBlocks.MACHINE_WASTE_DRUM),
                        modLoc("block/waste_drum_side"),
                        modLoc("block/waste_drum")
                )
        );
        this.particleOnlyBlock(NtmBlocks.MACHINE_CHEMICAL_PLANT, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.MACHINE_PUREX, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.MACHINE_ARC_WELDER, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.REACTOR_ZIRNOX, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.ZIRNOX_DESTROYED, modLoc("block/block_steel"));
        this.registerRBMK();
        this.simpleBlockWithItem(
                NtmBlocks.EMP_BOMB,
                this.models().cubeColumn(
                        name(NtmBlocks.EMP_BOMB),
                        modLoc("block/bomb_emp_side"),
                        modLoc("block/bomb_emp_top")
                )
        );

        this.cubeTop(NtmBlocks.MACHINE_SATLINKER);

        this.simpleBlockWithItem(
                NtmBlocks.DECONTAMINATOR,
                this.models().cubeBottomTop(
                        name(NtmBlocks.DECONTAMINATOR),
                        blockTexture(NtmBlocks.DECONTAMINATOR, "_side"),
                        blockTexture(NtmBlocks.DECONTAMINATOR, "_side"),
                        blockTexture(NtmBlocks.DECONTAMINATOR, "_top")
                )
        );

        // The texture names differ from the block IDs (original BlockAbsorber.EnumAbsorberTier.textureName)
        this.simpleBlockWithItem(NtmBlocks.RAD_ABSORBER, this.models().cubeAll(name(NtmBlocks.RAD_ABSORBER), modLoc("block/absorber")));
        this.simpleBlockWithItem(NtmBlocks.RAD_ABSORBER_RED, this.models().cubeAll(name(NtmBlocks.RAD_ABSORBER_RED), modLoc("block/absorber_red")));
        this.simpleBlockWithItem(NtmBlocks.RAD_ABSORBER_GREEN, this.models().cubeAll(name(NtmBlocks.RAD_ABSORBER_GREEN), modLoc("block/absorber_green")));
        this.simpleBlockWithItem(NtmBlocks.RAD_ABSORBER_PINK, this.models().cubeAll(name(NtmBlocks.RAD_ABSORBER_PINK), modLoc("block/absorber_pink")));

        this.simpleBlockWithItem(NtmBlocks.PWR_CONTROLLER.get(),
                this.models().cube(
                        NtmBlocks.PWR_CONTROLLER.getId().getPath(),
                        modLoc("block/pwr_casing_blank"),
                        modLoc("block/pwr_casing_blank"),
                        modLoc("block/pwr_controller"),
                        modLoc("block/pwr_casing_blank"),
                        modLoc("block/pwr_casing_blank"),
                        modLoc("block/pwr_casing_blank")
                )
        );

        this.simpleBlock(NtmBlocks.BALEFIRE.get(), this.models().withExistingParent("balefire", mcLoc("block/cross")).renderType("cutout_mipped").texture("cross", modLoc("block/balefire")));
        this.simpleBlock(NtmBlocks.FIRE_DIGAMMA.get(), this.models().withExistingParent("fire_digamma", mcLoc("block/cross")).renderType("cutout_mipped").texture("cross", modLoc("block/fire_digamma")));
        // VOLCANO_CORE uses custom register!
        // VOLCANO_RAD_CORE uses custom register!

        this.particleOnlyBlock(NtmBlocks.LAUNCH_PAD, blockTexture(NtmBlocks.LAUNCH_PAD));
        this.particleOnlyBlock(NtmBlocks.LAUNCH_PAD_LARGE, modLoc("block/block_steel"));
        this.simpleBlock(NtmBlocks.SOYUZ_LAUNCHER.get(), this.models().getBuilder(name(NtmBlocks.SOYUZ_LAUNCHER) + "_particle").texture("particle", modLoc("item/soyuz_launcher")));
        this.itemModels().basicItem(NtmBlocks.SOYUZ_LAUNCHER.asItem());
        this.particleOnlyBlock(NtmBlocks.MACHINE_RADAR, modLoc("block/block_steel"));
        this.particleOnlyBlock(NtmBlocks.MACHINE_RADAR_LARGE, modLoc("block/block_steel"));

        this.itemModels().basicItem(NtmBlocks.GAS_RADON.asItem());
        this.itemModels().basicItem(NtmBlocks.GAS_RADON_DENSE.asItem());
        this.itemModels().basicItem(NtmBlocks.GAS_RADON_TOMB.asItem());
        this.itemModels().basicItem(NtmBlocks.GAS_MELTDOWN.asItem());
        this.itemModels().basicItem(NtmBlocks.GAS_MONOXIDE.asItem());
        this.itemModels().basicItem(NtmBlocks.GAS_ASBESTOS.asItem());
        this.itemModels().basicItem(NtmBlocks.GAS_COAL.asItem());
        this.itemModels().basicItem(NtmBlocks.GAS_FLAMMABLE.asItem());
        this.itemModels().basicItem(NtmBlocks.GAS_EXPLOSIVE.asItem());
        // Invisible gases and the two lava fluid blocks (LiquidBlock, all 16 levels) only need a particle texture.
        this.particleOnlyState(NtmBlocks.GAS_RADON, modLoc("item/gas_radon"));
        this.particleOnlyState(NtmBlocks.GAS_RADON_DENSE, modLoc("item/gas_radon_dense"));
        this.particleOnlyState(NtmBlocks.GAS_RADON_TOMB, modLoc("item/gas_radon_tomb"));
        this.particleOnlyState(NtmBlocks.GAS_MELTDOWN, modLoc("item/gas_meltdown"));
        this.particleOnlyState(NtmBlocks.GAS_MONOXIDE, modLoc("item/gas_monoxide"));
        this.particleOnlyState(NtmBlocks.GAS_ASBESTOS, modLoc("item/gas_asbestos"));
        this.particleOnlyState(NtmBlocks.GAS_COAL, modLoc("item/gas_coal"));
        this.particleOnlyState(NtmBlocks.GAS_FLAMMABLE, modLoc("item/gas_flammable"));
        this.particleOnlyState(NtmBlocks.GAS_EXPLOSIVE, modLoc("item/gas_explosive"));
        this.particleOnlyState(NtmBlocks.RAD_LAVA, modLoc("block/rad_lava_still"));
        this.particleOnlyState(NtmBlocks.VOLCANIC_LAVA, modLoc("block/volcanic_lava_still"));
        this.simpleCubeAllBlock(NtmBlocks.OIL_PIPE);

        this.simpleCubeAllBlock(NtmBlocks.TAINT);
        this.registerMaterialBlocks();
    }

    /**
     * RBMK columns: every block of a column (core, dummies, extra; any lid) is a full cube with the column's _side texture around
     * and _top on top and bottom (original RenderRBMKReflector.renderWorldBlock and RBMKBase.getIcon); the lid is drawn by
     * RenderRBMKLid. The control rod columns (Goal24D) are the same cube; their pipe stubs and rod head are drawn by RenderRBMKControl,
     * and their item is that cube (the original's four-segment inventory render with pipes and head is not ported). So are the steam
     * channel, fluid heater (pipe stubs or lid by RenderRBMKPiped) and cooler (lid by RenderRBMKLid) of Goal24D, and the storage
     * column of Goal25A and the irradiation channel of Goal25B (lid by RenderRBMKLid). The debris
     * blocks bake models/obj/rbmk/debris.obj with their own texture (original RenderPribris); their items use a flat icon of that
     * texture.
     * The fuel channels bake the rbmk_element model (RBMKElementBakedModel, original RenderRBMKRod) for every block of the column
     * and for the item, with the display transforms of minecraft:block/block; rods and lid are drawn by RenderRBMKRod. corium_block
     * shows corium_still on top and bottom and corium_flowing around (original GenericFiniteFluid.getIcon).
     */
    private void registerRBMK() {
        for(DeferredBlock<? extends Block> column : new DeferredBlock[] {NtmBlocks.RBMK_BLANK, NtmBlocks.RBMK_MODERATOR, NtmBlocks.RBMK_ABSORBER, NtmBlocks.RBMK_REFLECTOR,
                NtmBlocks.RBMK_CONTROL, NtmBlocks.RBMK_CONTROL_MOD, NtmBlocks.RBMK_CONTROL_AUTO,
                NtmBlocks.RBMK_BOILER, NtmBlocks.RBMK_HEATER, NtmBlocks.RBMK_COOLER, NtmBlocks.RBMK_STORAGE, NtmBlocks.RBMK_OUTGASSER}) {
            String name = name(column);
            this.simpleBlockWithItem(column.get(), this.models().cubeColumn(name, modLoc("block/rbmk/" + name + "_side"), modLoc("block/rbmk/" + name + "_top")));
        }
        // Original setBlockTextureName rbmk_loader (ModBlocks.java:2143): one texture on every face.
        this.simpleBlockWithItem(NtmBlocks.RBMK_LOADER.get(), this.models().cubeAll(name(NtmBlocks.RBMK_LOADER), modLoc("block/rbmk_loader")));
        // The console is drawn by RenderRBMKConsole (block and item); its block icon rbmk/rbmk_console (ModBlocks.java:2131) is the break particle.
        this.particleOnlyBlock(NtmBlocks.RBMK_CONSOLE, modLoc("block/rbmk/rbmk_console"));
        // The crane console is drawn by RenderCraneConsole (block and item); its block icon rbmk/rbmk_crane_console (ModBlocks.java:2132) is the break particle.
        this.particleOnlyBlock(NtmBlocks.RBMK_CRANE_CONSOLE, modLoc("block/rbmk/rbmk_crane_console"));
        // The autoloader is drawn by RenderRBMKAutoloader (block and item); its block icon rbmk_autoloader (ModBlocks.java:2142) is the break particle.
        this.particleOnlyBlock(NtmBlocks.RBMK_AUTOLOADER, modLoc("block/rbmk/rbmk_autoloader"));

        this.simpleBlockWithItem(NtmBlocks.DECO_RBMK.get(), this.models().cubeAll(name(NtmBlocks.DECO_RBMK), modLoc("block/rbmk/rbmk_top")));
        this.simpleBlockWithItem(NtmBlocks.DECO_RBMK_SMOOTH.get(), this.models().cubeAll(name(NtmBlocks.DECO_RBMK_SMOOTH), modLoc("block/rbmk/rbmk_blank_top")));

        this.rbmkDebris(NtmBlocks.PRIBRIS, "rbmk_debris");
        this.rbmkDebris(NtmBlocks.PRIBRIS_BURNING, "rbmk_debris_burning");
        this.rbmkDebris(NtmBlocks.PRIBRIS_RADIATING, "rbmk_debris_radiating");

        // Original setBlockTextureName rbmk/rbmk_element and rbmk/rbmk_element_mod (ModBlocks.java:2113-2114).
        this.rbmkElement(NtmBlocks.RBMK_ROD, "rbmk_element");
        this.rbmkElement(NtmBlocks.RBMK_ROD_MOD, "rbmk_element_mod");

        this.simpleBlockWithItem(NtmBlocks.CORIUM_BLOCK.get(), this.models().cubeBottomTop(name(NtmBlocks.CORIUM_BLOCK), modLoc("block/corium_flowing"), modLoc("block/corium_still"), modLoc("block/corium_still")));
    }

    /**
     * Goal 31D. The sorter (original CraneRouter.java:78-117) draws crane_in on every face and, in six more passes, the overlay on one
     * face each tinted by that side's colour; here one cube with crane_in and a cutout overlay cube whose face d has tint index d
     * (NuclearTechModClient.registerBlockColors). Its item icon is plain crane_in. The splitter and the partitioner are baked OBJ
     * shapes (ConveyorObjBakedModel); one splitter model holds both halves' textures and every blockstate maps to it.
     */
    private void conveyorSorterAndBelts() {
        ModelFile router = models().withExistingParent("crane_router", mcLoc("block/block"))
                .renderType("cutout")
                .texture("base", modLoc("block/crane_in")).texture("overlay", modLoc("block/crane_router_overlay")).texture("particle", modLoc("block/crane_in"))
                .element().from(0, 0, 0).to(16, 16, 16).allFaces((dir, face) -> face.texture("#base").cullface(dir)).end()
                .element().from(0, 0, 0).to(16, 16, 16).allFaces((dir, face) -> face.texture("#overlay").cullface(dir).tintindex(dir.get3DDataValue())).end();
        this.simpleBlock(NtmBlocks.CRANE_ROUTER.get(), router);
        this.simpleBlockItem(NtmBlocks.CRANE_ROUTER.get(), models().cubeAll("crane_router_item", modLoc("block/crane_in")));

        ModelFile splitter = this.models().withExistingParent("crane_splitter", mcLoc("block/block")).customLoader(CraneSplitterLoaderBuilder::new)
                .texture("top_left", modLoc("block/crane_splitter_top_left")).texture("top_right", modLoc("block/crane_splitter_top_right"))
                .texture("front_left", modLoc("block/crane_splitter_front_left")).texture("front_right", modLoc("block/crane_splitter_front_right"))
                .texture("back_left", modLoc("block/crane_splitter_back_left")).texture("back_right", modLoc("block/crane_splitter_back_right"))
                .texture("left", modLoc("block/crane_splitter_left")).texture("right", modLoc("block/crane_splitter_right"))
                .texture("belt", modLoc("block/crane_splitter_belt")).texture("inner", modLoc("block/crane_splitter_inner"))
                .texture("inner_side", modLoc("block/crane_splitter_inner_side")).texture("particle", modLoc("block/crane_side")).end();
        this.simpleBlockWithItem(NtmBlocks.CRANE_SPLITTER.get(), splitter);

        ModelFile partitioner = this.models().withExistingParent("crane_partitioner", mcLoc("block/block")).customLoader(CranePartitionerLoaderBuilder::new)
                .texture("side", modLoc("block/crane_partitioner_side")).texture("back", modLoc("block/crane_partitioner_back"))
                .texture("top", modLoc("block/crane_top")).texture("inner", modLoc("block/crane_splitter_inner"))
                .texture("inner_side", modLoc("block/crane_splitter_inner_side")).texture("belt", modLoc("block/crane_splitter_belt")).end();
        this.simpleBlockWithItem(NtmBlocks.CRANE_PARTITIONER.get(), partitioner);
    }

    private void rbmkElement(DeferredBlock<? extends Block> block, String texture) {
        String base = "block/rbmk/" + texture;
        this.simpleBlockWithItem(block.get(), this.models().withExistingParent(name(block), mcLoc("block/block")).customLoader(RBMKElementLoaderBuilder::new)
                .texture("side", modLoc(base + "_side")).texture("top", modLoc(base + "_top")).texture("inner", modLoc(base + "_inner")).texture("fuel", modLoc(base + "_fuel")).end());
    }

    private void rbmkDebris(DeferredBlock<? extends Block> block, String texture) {
        ResourceLocation tex = modLoc("block/rbmk/" + texture);
        this.simpleBlock(block.get(), this.models().getBuilder(name(block)).customLoader(RBMKDebrisLoaderBuilder::new).texture("texture", tex).end());
        this.itemModels().withExistingParent(name(block), mcLoc("item/generated")).texture("layer0", tex);
    }

    private void registerOreBasalt() {
        Block block = NtmBlocks.ORE_BASALT.get();

        Enum<?>[] enums = BasaltOreType.values();
        this.getVariantBuilder(block).forAllStates(state -> {

            int meta = state.getValue(OreBasaltBlock.SUBTYPE);
            Enum<?> num = enums[meta];

            String path = "block/" + this.name(block) + "." + num.name().toLowerCase(Locale.US);
            ModelFile model = this.models().cubeTop(path, this.modLoc(path), this.modLoc(path + "_top"));

            return ConfiguredModel.builder().modelFile(model).build();
        });

        ItemModelBuilder builder = this.itemModels().getBuilder(this.name(block));
        for(Enum<?> num : enums) {
            String parent = "block/" + this.name(block) + "." + num.name().toLowerCase(Locale.US);
            builder.override()
                    .predicate(NuclearTechMod.withDefaultNamespace("item_meta"), num.ordinal())
                    .model(this.itemModels().getBuilder(this.name(block) + "." + num.name().toLowerCase(Locale.US))
                            .parent(new ModelFile.UncheckedModelFile(this.modLoc(parent)))
                    ).end();
        }
    }

    private void registerCable() {
        Block block = NtmBlocks.RED_CABLE.get();

        this.simpleBlock(block, this.models().getBuilder(this.key(block).getPath()).customLoader(CableBlockLoaderBuilder::new).texture("texture", modLoc("block/cable_neo")).end());
        this.entityBlockItem(block, false);
    }

    private void registerDetCord() {
        Block block = NtmBlocks.DET_CORD.get();

        this.simpleBlock(block, this.models().getBuilder(this.key(block).getPath()).customLoader(DetCordBlockLoaderBuilder::new).texture("texture", modLoc("block/det_cord")).end());
        this.entityBlockItem(block, false);
    }

    private void registerFluidDuct() {
        Block block = NtmBlocks.FLUID_DUCT_NEO.get();

        this.getVariantBuilder(block).forAllStatesExcept(state -> {

            int meta = state.getValue(NtmBlockStateProperties.META);
            
            ModelFile model;

            switch(meta) {
                case 2 -> model = this.models().getBuilder("hbmsntm:block/fluid_duct_silver").customLoader(DuctBlockLoaderBuilder::new).texture("texture", modLoc("block/pipe_silver")).texture("overlay", modLoc("block/pipe_silver_overlay")).end();
                case 1 -> model = this.models().getBuilder("hbmsntm:block/fluid_duct_colored").customLoader(DuctBlockLoaderBuilder::new).texture("texture", modLoc("block/pipe_colored")).texture("overlay", modLoc("block/pipe_colored_overlay")).end();
                default -> model = this.models().getBuilder("hbmsntm:block/fluid_duct_neo").customLoader(DuctBlockLoaderBuilder::new).texture("texture", modLoc("block/pipe_neo")).texture("overlay", modLoc("block/pipe_neo_overlay")).end();
            }

            return ConfiguredModel.builder().modelFile(model).build();
        }, FluidDuctConnectingBlock.NORTH, FluidDuctConnectingBlock.SOUTH, FluidDuctConnectingBlock.EAST, FluidDuctConnectingBlock.WEST, FluidDuctConnectingBlock.UP, FluidDuctConnectingBlock.DOWN);

        this.entityBlockItem(block, false);
    }

    private void registerMaterialBlocks() {
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_ACTINIUM);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_STEEL);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_ALUMINIUM);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_ASBESTOS);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_AUSTRALIUM);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_BERYLLIUM);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_BISMUTH);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_CADMIUM);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_CDALLOY);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_COLTAN);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_COMBINE_STEEL);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_COPPER);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_DESH);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_DINEUTRONIUM);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_DURA_STEEL);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_EUPHEMIUM);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_FOAM);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_LANTHANIUM);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_LEAD);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_LITHIUM);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_MAGNETIZED_TUNGSTEN);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_METEOR);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_METEOR_MOLTEN);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_METEOR_COBBLE);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_METEOR_BROKEN);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_METEOR_TREASURE);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_MOX_FUEL);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_NEPTUNIUM);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_NIOBIUM);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_NITER);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_PLUTONIUM);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_PLUTONIUM_FUEL);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_POLONIUM);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_PU238);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_PU239);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_PU240);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_PU_MIX);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_RA226);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_RED_COPPER);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_SATURNITE);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_SCHRABIDATE);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_SCHRABIDIUM);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_SCHRABIDIUM_FUEL);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_SCHRARANIUM);
        this.simpleBlockWithItem(NtmBlocks.BLOCK_SMORE.get(), this.models().cubeBottomTop("block_smore", modLoc("block/block_smore_side"), modLoc("block/block_smore_side"), modLoc("block/block_smore_top")));
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_SOLINIUM);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_SULFUR);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_TANTALIUM);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_TCALLOY);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_THORIUM);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_THORIUM_FUEL);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_TITANIUM);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_TUNGSTEN);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_U233);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_U235);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_U238);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_URANIUM);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_URANIUM_FUEL);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_WASTE);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_WASTE_PAINTED);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_WASTE_VITRIFIED);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_YELLOWCAKE);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_SLAG);
        this.simpleCubeAllBlock(NtmBlocks.BLOCK_GRAPHITE);
        this.simpleBlockWithItem(NtmBlocks.BLOCK_FIBERGLASS.get(), this.models().cubeBottomTop("block_fiberglass", modLoc("block/block_fiberglass_side"), modLoc("block/block_fiberglass_side"), modLoc("block/block_fiberglass_top")));
        this.simpleBlockWithItem(NtmBlocks.BLOCK_INSULATOR.get(), this.models().cubeBottomTop("block_insulator", modLoc("block/block_insulator_side"), modLoc("block/block_insulator_side"), modLoc("block/block_insulator_top")));
    }

    private void registerBarbedWire() {
        Block block = NtmBlocks.BARBED_WIRE.get();

        this.getVariantBuilder(block).forAllStates(state -> {

            int subType = state.getValue(BarbedWireBlock.SUBTYPE);

            ModelFile model;

            switch(subType) {
                case 5 -> model = this.models().getBuilder(this.name(block) + "_ultradeath").customLoader(BarbedWireBlockLoaderBuilder::new).texture("texture", modLoc("block/barbed_wire_ultradeath")).end();
                case 4 -> model = this.models().getBuilder(this.name(block) + "_wither").customLoader(BarbedWireBlockLoaderBuilder::new).texture("texture", modLoc("block/barbed_wire_wither")).end();
                case 3 -> model = this.models().getBuilder(this.name(block) + "_acid").customLoader(BarbedWireBlockLoaderBuilder::new).texture("texture", modLoc("block/barbed_wire_acid")).end();
                case 2 -> model = this.models().getBuilder(this.name(block) + "_poison").customLoader(BarbedWireBlockLoaderBuilder::new).texture("texture", modLoc("block/barbed_wire_poison")).end();
                case 1 -> model = this.models().getBuilder(this.name(block) + "_fire").customLoader(BarbedWireBlockLoaderBuilder::new).texture("texture", modLoc("block/barbed_wire_fire")).end();
                default -> model = this.models().getBuilder(this.name(block)).customLoader(BarbedWireBlockLoaderBuilder::new).texture("texture", modLoc("block/barbed_wire")).end();
            }

            return ConfiguredModel.builder().modelFile(model).build();
        });

        this.entityBlockItem(block, false);
    }

    private void registerSpikes() {
        Block block = NtmBlocks.SPIKES.get();

        this.simpleBlock(block, this.models().getBuilder(this.key(block).getPath()).customLoader(SpikesLoaderBuilder::new).texture("texture", this.blockTexture(block)).end());
        this.entityBlockItem(block, false);
    }

    private void barrelLoaderBlockItem(Block block, ResourceLocation texture) {
        this.simpleBlock(block, this.models().getBuilder(this.key(block).getPath()).customLoader(BarrelBlockModelBuilder::new).texture("texture", texture).end());
        this.entityBlockItem(block, false);
    }

    private void registerMachineElectricFurnace() {
        Block block = NtmBlocks.MACHINE_ELECTRIC_FURNACE.get();

        // Upstream textures: the front swaps between _front_off and _front_on, the other faces stay.
        ModelFile off = this.electricFurnaceModel(this.name(block), "block/machine_electric_furnace_front_off");
        ModelFile on = this.electricFurnaceModel(this.name(block) + "_on", "block/machine_electric_furnace_front_on");

        this.getVariantBuilder(block).forAllStates(state -> {
            int y = switch(state.getValue(com.hbm.blocks.machine.MachineElectricFurnaceBlock.FACING)) {
                case EAST -> 90;
                case SOUTH -> 180;
                case WEST -> 270;
                default -> 0;
            };
            ModelFile model = state.getValue(com.hbm.blocks.machine.MachineElectricFurnaceBlock.LIT) ? on : off;
            return ConfiguredModel.builder().modelFile(model).rotationY(y).build();
        });

        this.simpleBlockItem(block, off);
    }

    /** Goal 30A power and fluid control blocks; the item models show the base texture only, as the original inventory renders pass 0. */
    private void registerNetworkControls() {
        this.simpleCubeAllBlock(NtmBlocks.RED_WIRE_COATED);

        this.onOffCube(NtmBlocks.CABLE_SWITCH.get(), BlockStateProperties.ENABLED, "cable_switch_on", "cable_switch_off");
        this.onOffCube(NtmBlocks.CABLE_DETECTOR.get(), BlockStateProperties.ENABLED, "cable_detector_on", "cable_detector_off");
        this.onOffCube(NtmBlocks.MACHINE_DETECTOR.get(), BlockStateProperties.POWERED, "machine_detector", "machine_detector_off");
        this.onOffCube(NtmBlocks.FLUID_VALVE.get(), BlockStateProperties.ENABLED, "fluid_valve_on", "fluid_valve_off");
        this.onOffCube(NtmBlocks.FLUID_SWITCH.get(), BlockStateProperties.ENABLED, "fluid_switch_on", "fluid_switch_off");
        this.onOffCube(NtmBlocks.FLUID_COUNTER_VALVE.get(), BlockStateProperties.ENABLED, "fluid_counter_valve_on", "fluid_counter_valve_off");

        // original BlockCableGauge.getIcon / FluidDuctGauge.getIcon: base on every face, then the dial on the facing face and the other overlay elsewhere
        this.gauge(NtmBlocks.RED_CABLE_GAUGE.get(), "deco_red_copper", "cable_gauge", null);
        this.gauge(NtmBlocks.FLUID_DUCT_GAUGE.get(), "deco_steel", "pipe_gauge", "fluid_duct_paintable_overlay");

        Block cable = NtmBlocks.RED_CABLE_PAINTABLE.get();
        this.simpleBlock(cable, this.models().getBuilder(this.key(cable).getPath()).customLoader(PaintableCableLoaderBuilder::new)
                .texture("texture", modLoc("block/red_cable_base")).texture("overlay", modLoc("block/red_cable_overlay")).end());
        this.itemModels().cubeAll(this.key(cable).getPath(), modLoc("block/red_cable_base"));

        Block duct = NtmBlocks.FLUID_DUCT_PAINTABLE.get();
        this.simpleBlock(duct, this.models().getBuilder(this.key(duct).getPath()).customLoader(PaintableDuctLoaderBuilder::new)
                .texture("texture", modLoc("block/fluid_duct_paintable")).texture("overlay", modLoc("block/fluid_duct_paintable_overlay"))
                .texture("overlay_color", modLoc("block/fluid_duct_paintable_color")).end());
        this.itemModels().cubeAll(this.key(duct).getPath(), modLoc("block/fluid_duct_paintable"));
    }

    /** Original getIcon(side, meta): the on texture for metadata 1; the item is the off block. */
    private void onOffCube(Block block, BooleanProperty property, String onTexture, String offTexture) {
        ModelFile on = this.models().cubeAll(onTexture, modLoc("block/" + onTexture));
        ModelFile off = this.models().cubeAll(offTexture, modLoc("block/" + offTexture));
        this.getVariantBuilder(block).forAllStates(state -> ConfiguredModel.builder().modelFile(state.getValue(property) ? on : off).build());
        this.itemModels().withExistingParent(this.key(block).getPath(), modLoc("block/" + offTexture));
    }

    private void gauge(Block block, String base, String dial, String otherOverlay) {
        String name = this.key(block).getPath();
        this.getVariantBuilder(block).forAllStates(state -> {
            Direction facing = state.getValue(BlockStateProperties.FACING);
            BlockModelBuilder model = this.models().withExistingParent(name + "_" + facing.getSerializedName(), mcLoc("block/block"))
                    .renderType("cutout")
                    .texture("base", modLoc("block/" + base))
                    .texture("dial", modLoc("block/" + dial))
                    .texture("particle", modLoc("block/" + base))
                    .element().from(0, 0, 0).to(16, 16, 16)
                    .allFaces((dir, face) -> face.texture("#base").cullface(dir))
                    .end();
            if(otherOverlay != null) model.texture("overlay", modLoc("block/" + otherOverlay));
            ModelBuilder<BlockModelBuilder>.ElementBuilder overlay = model.element().from(0, 0, 0).to(16, 16, 16);
            for(Direction dir : Direction.values()) {
                if(dir == facing) overlay.face(dir).texture("#dial").cullface(dir).end();
                else if(otherOverlay != null) overlay.face(dir).texture("#overlay").cullface(dir).end();
            }
            overlay.end();
            return ConfiguredModel.builder().modelFile(model).build();
        });
        this.itemModels().cubeAll(name, modLoc("block/" + base));
    }

    /**
     * The RoR torches. The original draws models/blocks/rtty.obj with one texture (RenderRTTY.java:33-76): two crossed 4x10 pixel
     * panels and a 2x2 top, standing on the support face and rotated by the facing. Here the same quads are block model elements;
     * the sender and receiver swap to the _on texture while LIT, the relay always uses its animated rtty_relay texture. The items
     * use the flat texture as the original item icons (RadioTorchRWBase.java:30-32 returns iconOn for the item's side).
     */
    private void registerRadioTorches() {
        this.radioTorch(NtmBlocks.RADIO_TORCH_SENDER.get(), "rtty_sender_off", "rtty_sender_on");
        this.radioTorch(NtmBlocks.RADIO_TORCH_RECEIVER.get(), "rtty_rec_off", "rtty_rec_on");
        this.radioTorch(NtmBlocks.RADIO_TORCH_RELAY.get(), "rtty_relay", null);
    }

    private void radioTorch(Block block, String offTexture, String onTexture) {
        ModelFile off = this.rttyModel(offTexture, offTexture);
        ModelFile on = onTexture == null ? off : this.rttyModel(onTexture, onTexture);

        this.getVariantBuilder(block).forAllStates(state -> {
            // vanilla end_rod rotations for a model that points up
            Direction facing = state.getValue(com.hbm.blocks.network.RadioTorchBaseBlock.FACING);
            int x = facing == Direction.UP ? 0 : facing == Direction.DOWN ? 180 : 90;
            int y = switch(facing) {
                case EAST -> 90;
                case SOUTH -> 180;
                case WEST -> 270;
                default -> 0;
            };
            boolean lit = state.hasProperty(com.hbm.blocks.network.RadioTorchRWBaseBlock.LIT) && state.getValue(com.hbm.blocks.network.RadioTorchRWBaseBlock.LIT);
            return ConfiguredModel.builder().modelFile(lit ? on : off).rotationX(x).rotationY(y).build();
        });

        this.itemModels().withExistingParent(this.key(block).getPath(), mcLoc("item/generated")).texture("layer0", modLoc("block/" + (onTexture == null ? offTexture : onTexture)));
    }

    private ModelFile rttyModel(String name, String texture) {
        return this.models().getBuilder(name)
                .renderType("cutout")
                .texture("torch", modLoc("block/" + texture))
                .texture("particle", modLoc("block/" + texture))
                .element().from(6, 0, 7).to(10, 10, 9)
                .face(Direction.NORTH).uvs(6, 6, 10, 16).texture("#torch").end()
                .face(Direction.SOUTH).uvs(6, 6, 10, 16).texture("#torch").end()
                .end()
                .element().from(7, 0, 6).to(9, 10, 10)
                .face(Direction.WEST).uvs(6, 6, 10, 16).texture("#torch").end()
                .face(Direction.EAST).uvs(6, 6, 10, 16).texture("#torch").end()
                .end()
                .element().from(7, 9, 7).to(9, 9, 9)
                .face(Direction.UP).uvs(7, 7, 9, 9).texture("#torch").end()
                .end();
    }

    private ModelFile electricFurnaceModel(String name, String front) {
        return this.models().cube(
                name,
                modLoc("block/machine_electric_furnace_bottom"),
                modLoc("block/machine_electric_furnace_top"),
                modLoc(front),
                modLoc("block/machine_electric_furnace_side"),
                modLoc("block/machine_electric_furnace_side"),
                modLoc("block/machine_electric_furnace_side")
        ).texture("particle", modLoc("block/machine_electric_furnace_side"));
    }

    private void registerMachineShredder() {
        Block block = NtmBlocks.MACHINE_SHREDDER.get();

        ModelFile model = this.models().cube(
                this.name(block),
                modLoc("block/machine_shredder_bottom_alt"),
                modLoc("block/machine_shredder_top_alt"),
                modLoc("block/machine_shredder_front_alt"),
                modLoc("block/machine_shredder_front_alt"),
                modLoc("block/machine_shredder_side_alt"),
                modLoc("block/machine_shredder_side_alt")
        ).texture("particle", modLoc("block/machine_shredder_front_alt"));

        this.getVariantBuilder(block).forAllStates(state -> {
            int y = switch(state.getValue(com.hbm.blocks.machine.MachineShredderBlock.FACING)) {
                case EAST -> 90;
                case SOUTH -> 180;
                case WEST -> 270;
                default -> 0;
            };
            return ConfiguredModel.builder().modelFile(model).rotationY(y).build();
        });

        this.simpleBlockItem(block, model);
    }

    private void layeringBlock(Block block, ResourceLocation texture) {
        String blockName = this.key(block).getPath();
        MultiPartBlockStateBuilder builder = getMultipartBuilder(block);

        for(int i = 1; i <= 8; i++) {
            float height = i * 2f / 16f;

            ModelFile model = models()
                    .withExistingParent(blockName + "_" + i, mcLoc("block/block"))
                    .texture("all", texture)
                    .texture("particle", texture)
                    .renderType("cutout_mipped")
                    .element()
                    .from(0, 0, 0)
                    .to(16, height * 16, 16)
                    .face(Direction.UP).texture("#all").end()
                    .face(Direction.DOWN).texture("#all").end()
                    .face(Direction.NORTH).texture("#all").end()
                    .face(Direction.SOUTH).texture("#all").end()
                    .face(Direction.WEST).texture("#all").end()
                    .face(Direction.EAST).texture("#all").end()
                    .end();

            builder.part()
                    .modelFile(model)
                    .addModel()
                    .condition(LayeringBlock.LAYERS, i)
                    .end();
        }
    }

    private void sellafieldSlaked(Block block, String modelBaseName) {
        getVariantBuilder(block).forAllStatesExcept(state -> {
            int variant = state.getValue(SellafieldSlakedBlock.VARIANT);
            String modelName = modelBaseName + (variant == 0 ? "" : "_" + variant);
            String texName = "sellafield_slaked" + (variant == 0 ? "" : "_" + variant);

            ModelFile tintedModel = models().withExistingParent(modelName, mcLoc("block/cube"))
                    .texture("particle", modLoc("block/" + texName))
                    .texture("down", modLoc("block/" + texName))
                    .texture("up", modLoc("block/" + texName))
                    .texture("north", modLoc("block/" + texName))
                    .texture("south", modLoc("block/" + texName))
                    .texture("west", modLoc("block/" + texName))
                    .texture("east", modLoc("block/" + texName))
                    .element()
                    .from(0, 0, 0).to(16, 16, 16)
                    .allFaces((dir, face) -> face.texture("#" + dir.getName()).tintindex(0))
                    .end();

            return ConfiguredModel.builder().modelFile(tintedModel).build();
            }, SellafieldSlakedBlock.COLOR_LEVEL);

        itemModels().withExistingParent(BuiltInRegistries.BLOCK.getKey(block).getPath(), modLoc("block/sellafield_slaked"));
    }

    private void sellafieldOre(Block block, String baseName, String overlayTexture) {

        this.getVariantBuilder(block).forAllStatesExcept(state -> {
            int variant = state.getValue(SellafieldSlakedBlock.VARIANT);
            String modelName = baseName + (variant == 0 ? "" : "_" + variant);
            String baseTex = "sellafield_slaked" + (variant == 0 ? "" : "_" + variant);

            ModelFile oreModel = models().withExistingParent(modelName, mcLoc("block/cube"))
                    .renderType("cutout")
                    .texture("base", modLoc("block/" + baseTex))
                    .texture("overlay", modLoc(overlayTexture))
                    .texture("particle", modLoc(overlayTexture))
                    .element()
                    .from(0, 0, 0).to(16, 16, 16)
                    .allFaces((dir, face) -> face.texture("#base").tintindex(0))
                    .end()
                    .element()
                    .from(0, 0, 0).to(16, 16, 16)
                    .allFaces((dir, face) -> face.texture("#overlay"))
                    .end();
            return ConfiguredModel.builder().modelFile(oreModel).build();

            }, SellafieldSlakedBlock.COLOR_LEVEL);

        itemModels().withExistingParent(BuiltInRegistries.BLOCK.getKey(block).getPath(), modLoc("block/" + baseName));
    }

    public void simpleBlockWithItem(DeferredBlock<? extends Block> block, ModelFile model) {
        this.simpleBlockWithItem(block.get(), model);
    }

    private void registerFoundryMold() {
        BlockModelBuilder model = models().withExistingParent("foundry_mold", mcLoc("block/block"))
                .texture("top", modLoc("block/foundry_mold_top"))
                .texture("side", modLoc("block/foundry_mold_side"))
                .texture("bottom", modLoc("block/foundry_mold_bottom"))
                .texture("inner", modLoc("block/foundry_mold_inner"))
                .texture("particle", modLoc("block/foundry_mold_side"));
        model.element().from(0, 0, 0).to(16, 2, 16)
                .face(Direction.UP).texture("#inner").end()
                .face(Direction.DOWN).texture("#bottom").end()
                .face(Direction.NORTH).texture("#side").end()
                .face(Direction.SOUTH).texture("#side").end()
                .face(Direction.WEST).texture("#side").end()
                .face(Direction.EAST).texture("#side").end().end();
        this.foundryMoldWall(model, 0, 2, 0, 16, 8, 2);
        this.foundryMoldWall(model, 0, 2, 14, 16, 8, 16);
        this.foundryMoldWall(model, 0, 2, 2, 2, 8, 14);
        this.foundryMoldWall(model, 14, 2, 2, 16, 8, 14);
        this.simpleBlockWithItem(NtmBlocks.FOUNDRY_MOLD.get(), model);
    }

    private void foundryMoldWall(BlockModelBuilder model, int x1, int y1, int z1, int x2, int y2, int z2) {
        model.element().from(x1, y1, z1).to(x2, y2, z2)
                .face(Direction.UP).texture("#top").end()
                .face(Direction.DOWN).texture("#bottom").end()
                .face(Direction.NORTH).texture("#side").end()
                .face(Direction.SOUTH).texture("#side").end()
                .face(Direction.WEST).texture("#side").end()
                .face(Direction.EAST).texture("#side").end().end();
    }

    private static final Direction[] FOUNDRY_SIDES = {Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST};

    private BlockModelBuilder foundryModel(String name, String prefix) {
        return models().withExistingParent(name, mcLoc("block/block"))
                .renderType("cutout")
                .texture("top", modLoc("block/" + prefix + "_top"))
                .texture("side", modLoc("block/" + prefix + "_side"))
                .texture("bottom", modLoc("block/" + prefix + "_bottom"))
                .texture("inner", modLoc("block/" + prefix + "_inner"))
                .texture("particle", modLoc("block/" + prefix + "_side"));
    }

    /**
     * Adds an element given in its north-facing layout, turned clockwise (seen from above) by quarter * 90 degrees. Coordinates are
     * turned instead of rotating the model so the faces keep upstream's world-aligned UVs. faces: Direction, texture pairs.
     */
    private void foundryElement(BlockModelBuilder model, int quarter, float x1, float y1, float z1, float x2, float y2, float z2, Object... faces) {
        float ax = x1, az = z1, bx = x2, bz = z2;
        for(int i = 0; i < quarter; i++) {
            float nax = 16 - az, naz = ax, nbx = 16 - bz, nbz = bx;
            ax = nax; az = naz; bx = nbx; bz = nbz;
        }
        var element = model.element().from(Math.min(ax, bx), y1, Math.min(az, bz)).to(Math.max(ax, bx), y2, Math.max(az, bz));
        for(int f = 0; f < faces.length; f += 2) {
            Direction dir = (Direction) faces[f];
            for(int i = 0; i < quarter && dir.getAxis().isHorizontal(); i++) dir = dir.getClockWise();
            element.face(dir).texture((String) faces[f + 1]).end();
        }
        element.end();
    }

    /** Upstream RenderFoundryChannel: the centre floor and, per side, the open arm (floor and two 1 px walls) or the end wall. */
    private void registerFoundryChannel() {
        Block block = NtmBlocks.FOUNDRY_CHANNEL.get();
        MultiPartBlockStateBuilder builder = getMultipartBuilder(block);

        BlockModelBuilder center = this.foundryModel("foundry_channel_center", "foundry_channel");
        this.foundryChannelCenter(center);
        builder.part().modelFile(center).addModel().end();

        BlockModelBuilder inventory = this.foundryModel("foundry_channel_inventory", "foundry_channel");
        this.foundryChannelCenter(inventory);

        for(int quarter = 0; quarter < 4; quarter++) {
            Direction side = FOUNDRY_SIDES[quarter];
            String suffix = side.getSerializedName();

            BlockModelBuilder arm = this.foundryModel("foundry_channel_arm_" + suffix, "foundry_channel");
            this.foundryChannelArm(arm, quarter, false);
            this.foundryChannelArm(inventory, quarter, true);
            BlockModelBuilder end = this.foundryModel("foundry_channel_end_" + suffix, "foundry_channel");
            this.foundryElement(end, quarter, 5, 0, 5, 11, 8, 6, Direction.UP, "#top", Direction.NORTH, "#side", Direction.SOUTH, "#inner");

            builder.part().modelFile(arm).addModel().condition(com.hbm.blocks.machine.FoundryChannelBlock.getProperty(side), true).end();
            builder.part().modelFile(end).addModel().condition(com.hbm.blocks.machine.FoundryChannelBlock.getProperty(side), false).end();
        }

        this.simpleBlockItem(block, inventory);
    }

    private void foundryChannelCenter(BlockModelBuilder model) {
        this.foundryElement(model, 0, 6, 2, 6, 10, 2, 10, Direction.UP, "#bottom");
        this.foundryElement(model, 0, 5, 0, 5, 11, 0, 11, Direction.DOWN, "#bottom");
    }

    /** The inventory variant also closes the arm ends at the block edge, like upstream renderInventoryBlock. */
    private void foundryChannelArm(BlockModelBuilder model, int quarter, boolean inventory) {
        if(inventory) {
            this.foundryElement(model, quarter, 5, 0, 0, 11, 2, 6, Direction.UP, "#bottom", Direction.DOWN, "#bottom", Direction.NORTH, "#side");
            this.foundryElement(model, quarter, 5, 0, 0, 6, 8, 6, Direction.UP, "#top", Direction.WEST, "#side", Direction.EAST, "#inner", Direction.NORTH, "#side");
            this.foundryElement(model, quarter, 10, 0, 0, 11, 8, 6, Direction.UP, "#top", Direction.WEST, "#inner", Direction.EAST, "#side", Direction.NORTH, "#side");
        } else {
            this.foundryElement(model, quarter, 5, 0, 0, 11, 2, 6, Direction.UP, "#bottom", Direction.DOWN, "#bottom");
            this.foundryElement(model, quarter, 5, 0, 0, 6, 8, 6, Direction.UP, "#top", Direction.WEST, "#side", Direction.EAST, "#inner");
            this.foundryElement(model, quarter, 10, 0, 0, 11, 8, 6, Direction.UP, "#top", Direction.WEST, "#inner", Direction.EAST, "#side");
        }
    }

    /**
     * Upstream RenderFoundryTank for a tank without neighbours: 2 px floor and walls. Merging walls with neighbouring tanks and the
     * upper/outlet side textures are not reproduced by this static model.
     */
    private void registerFoundryTank() {
        BlockModelBuilder model = this.foundryModel("foundry_tank", "foundry_tank");
        this.foundryElement(model, 0, 0, 0, 0, 16, 2, 16, Direction.UP, "#bottom", Direction.DOWN, "#bottom");
        for(int quarter = 0; quarter < 4; quarter++) {
            this.foundryElement(model, quarter, 0, 0, 0, 16, 16, 2, Direction.UP, "#top", Direction.NORTH, "#side", Direction.SOUTH, "#inner");
        }
        this.simpleBlockWithItem(NtmBlocks.FOUNDRY_TANK.get(), model);
    }

    /**
     * Upstream RenderFoundryBasin.renderWorldBlock (RenderFoundryBasin.java:77-90): the floor at 2 px shows the bottom texture like the
     * underside, the full-height walls the side texture outside, the inner texture inside and the top rim on top.
     */
    private void registerFoundryBasin() {
        BlockModelBuilder model = this.foundryModel("foundry_basin", "foundry_basin");
        this.foundryElement(model, 0, 0, 0, 0, 16, 2, 16, Direction.UP, "#bottom", Direction.DOWN, "#bottom");
        for(int quarter = 0; quarter < 4; quarter++) {
            this.foundryElement(model, quarter, 0, 0, 0, 16, 16, 2, Direction.UP, "#top", Direction.NORTH, "#side", Direction.SOUTH, "#inner");
        }
        this.simpleBlockWithItem(NtmBlocks.FOUNDRY_BASIN.get(), model);
    }

    /**
     * Upstream RenderFoundryOutlet (meta 2 branch, facing north, turned for the other facings): the trough at the back edge with a
     * raised inner floor and inner walls, plus the lock (CLOSED) and filter (FILTERED) planes.
     */
    private void registerFoundryOutlet() {
        Block block = NtmBlocks.FOUNDRY_OUTLET.get();
        MultiPartBlockStateBuilder builder = getMultipartBuilder(block);
        ModelFile item = null;

        for(int quarter = 0; quarter < 4; quarter++) {
            Direction facing = FOUNDRY_SIDES[quarter];
            String suffix = facing.getSerializedName();

            BlockModelBuilder body = this.foundryModel("foundry_outlet_" + suffix, "foundry_outlet")
                    .texture("front", modLoc("block/foundry_outlet_front"));
            this.foundryElement(body, quarter, 5, 0, 10, 11, 8, 16, Direction.DOWN, "#bottom", Direction.UP, "#top",
                    Direction.EAST, "#side", Direction.WEST, "#side", Direction.NORTH, "#front", Direction.SOUTH, "#front");
            this.foundryElement(body, quarter, 5, 2, 10, 11, 2, 16, Direction.UP, "#bottom");
            this.foundryElement(body, quarter, 6, 0, 10, 6, 8, 16, Direction.EAST, "#inner");
            this.foundryElement(body, quarter, 10, 0, 10, 10, 8, 16, Direction.WEST, "#inner");

            BlockModelBuilder lock = models().withExistingParent("foundry_outlet_lock_" + suffix, mcLoc("block/block"))
                    .renderType("cutout")
                    .texture("lock", modLoc("block/foundry_outlet_lock"))
                    .texture("particle", modLoc("block/foundry_outlet_side"));
            this.foundryElement(lock, quarter, 6, 1, 15, 10, 8, 15, Direction.NORTH, "#lock", Direction.SOUTH, "#lock");

            BlockModelBuilder filter = models().withExistingParent("foundry_outlet_filter_" + suffix, mcLoc("block/block"))
                    .renderType("cutout")
                    .texture("filter", modLoc("block/foundry_outlet_filter"))
                    .texture("particle", modLoc("block/foundry_outlet_side"));
            this.foundryElement(filter, quarter, 6, 1, 15.5F, 10, 8, 15.5F, Direction.NORTH, "#filter", Direction.SOUTH, "#filter");

            builder.part().modelFile(body).addModel().condition(com.hbm.blocks.machine.FoundryOutletBlock.FACING, facing).end();
            builder.part().modelFile(lock).addModel().condition(com.hbm.blocks.machine.FoundryOutletBlock.FACING, facing)
                    .condition(com.hbm.blocks.machine.FoundryOutletBlock.CLOSED, true).end();
            builder.part().modelFile(filter).addModel().condition(com.hbm.blocks.machine.FoundryOutletBlock.FACING, facing)
                    .condition(com.hbm.blocks.machine.FoundryOutletBlock.FILTERED, true).end();

            if(facing == Direction.NORTH) item = body;
        }

        this.simpleBlockItem(block, item);
    }

    /*
     * Goal 31B conveyor cranes. The original picks every face's icon from the input side I and the output side O
     * (BlockCraneBase.java:118-215) and turns only the top face (getRotationFromSide, uvRotateTop; 1 = 90 degrees clockwise, 2 = 90
     * counter-clockwise, 3 = 180 as for the conveyors). One model per valid (I, O) pair; the six states with I == O never occur and
     * point at the default model. The skin is a parameter, so the five cranes share the generator.
     */

    /** The 13 directional icon fields of BlockCraneBase (:41-56), in this order. */
    private enum CraneIcon { DIRECTIONAL, DIRECTIONAL_UP, DIRECTIONAL_DOWN, TURN_LEFT, TURN_RIGHT, SIDE_LEFT_TURN_UP, SIDE_RIGHT_TURN_UP,
        SIDE_LEFT_TURN_DOWN, SIDE_RIGHT_TURN_DOWN, SIDE_UP_TURN_LEFT, SIDE_UP_TURN_RIGHT, SIDE_DOWN_TURN_LEFT, SIDE_DOWN_TURN_RIGHT }

    /** ForgeDirection.ROTATION_MATRIX of 1.7.10: {@code output.getRotation(input)} is ROTATION[input][output]. */
    private static final int[][] CRANE_ROTATION = {
            { 0, 1, 4, 5, 3, 2 }, { 0, 1, 5, 4, 2, 3 }, { 5, 4, 2, 3, 0, 1 }, { 4, 5, 2, 3, 1, 0 }, { 2, 3, 1, 0, 4, 5 }, { 3, 2, 0, 1, 4, 5 } };

    /**
     * One crane's textures. {@code icons} are the texture names of the 13 directional fields in CraneIcon order; {@code in},
     * {@code sideIn}, {@code out}, {@code sideOut} the four base faces that a crane may replace; {@code topRotation} gives the
     * original's uvRotateTop from the input side and the "left hand" side.
     */
    private record CraneSkin(String[] icons, String in, String sideIn, String out, String sideOut, java.util.function.BiFunction<Direction, Direction, Integer> topRotation) {
        String icon(CraneIcon field) { return this.icons[field.ordinal()]; }
    }

    /** BlockCraneBase.getRotationFromSide (:249-261): the top turns by the input side only; the inserter, grabber and boxer use it. */
    private static final java.util.function.BiFunction<Direction, Direction, Integer> CRANE_TOP_BASE =
            (input, left) -> switch(input) { case NORTH -> 3; case WEST -> 1; case EAST -> 2; default -> 0; };

    /** CraneExtractor.java:45-76 and the identical CraneUnboxer.java:54-84: the top turns by the input side and the left hand. */
    private static final java.util.function.BiFunction<Direction, Direction, Integer> CRANE_TOP_REVERSED = (input, left) -> {
        if(left == Direction.UP) return switch(input) { case NORTH -> 2; case SOUTH -> 1; case WEST -> 3; default -> 0; };
        if(left == Direction.DOWN) return switch(input) { case NORTH -> 1; case SOUTH -> 2; case WEST -> 0; default -> 3; };
        return switch(input) { case NORTH -> 0; case SOUTH -> 3; case WEST -> 2; default -> 1; };
    };

    /** The 13 icon names of a crane that registers its fields in BlockCraneBase order (CraneInserter, CraneGrabber, CraneBoxer). */
    private static String[] craneIcons(String prefix) {
        return new String[] { prefix + "_top", prefix + "_side_up", prefix + "_side_down", prefix + "_top_left", prefix + "_top_right",
                prefix + "_side_left_turn_up", prefix + "_side_right_turn_up", prefix + "_side_left_turn_down", prefix + "_side_right_turn_down",
                prefix + "_side_up_turn_left", prefix + "_side_up_turn_right", prefix + "_side_down_turn_left", prefix + "_side_down_turn_right" };
    }

    /** The 13 icon names of a crane whose fields point at its files in the extractor's order (CraneExtractor, CraneUnboxer). */
    private static String[] craneIconsReversed(String prefix) {
        return new String[] { prefix + "_top", prefix + "_side_down", prefix + "_side_up", prefix + "_top_right", prefix + "_top_left",
                prefix + "_side_up_turn_left", prefix + "_side_up_turn_right", prefix + "_side_down_turn_left", prefix + "_side_down_turn_right",
                prefix + "_side_left_turn_up", prefix + "_side_right_turn_up", prefix + "_side_left_turn_down", prefix + "_side_right_turn_down" };
    }

    private void craneBlocks() {
        // CraneInserter.java:37-52
        CraneSkin inserter = new CraneSkin(craneIcons("crane_in"), "crane_in", "crane_side_in", "crane_out", "crane_side_out", CRANE_TOP_BASE);
        // CraneExtractor.java:28-42: the fields point at the crane_out_ files in a different order, which is kept as it is
        CraneSkin extractor = new CraneSkin(craneIconsReversed("crane_out"), "crane_in", "crane_side_in", "crane_out", "crane_side_out", CRANE_TOP_REVERSED);
        // CraneGrabber.java:26-42: pulls on the input side
        CraneSkin grabber = new CraneSkin(craneIcons("crane_grabber"), "crane_pull", "crane_side_pull", "crane_out", "crane_side_out", CRANE_TOP_BASE);
        // CraneBoxer.java:34-50: boxes on the output side
        CraneSkin boxer = new CraneSkin(craneIcons("crane_boxer"), "crane_in", "crane_side_in", "crane_box", "crane_side_box", CRANE_TOP_BASE);
        // CraneUnboxer.java:34-84: the extractor's field order and top rotation
        CraneSkin unboxer = new CraneSkin(craneIconsReversed("crane_unboxer"), "crane_in", "crane_side_in", "crane_box", "crane_side_box", CRANE_TOP_REVERSED);

        this.crane(NtmBlocks.CRANE_INSERTER.get(), inserter);
        this.crane(NtmBlocks.CRANE_EXTRACTOR.get(), extractor);
        this.crane(NtmBlocks.CRANE_GRABBER.get(), grabber);
        this.crane(NtmBlocks.CRANE_BOXER.get(), boxer);
        this.crane(NtmBlocks.CRANE_UNBOXER.get(), unboxer);
    }

    private void crane(Block block, CraneSkin skin) {
        String name = this.key(block).getPath();
        Map<String, BlockModelBuilder> models = new LinkedHashMap<>();

        for(Direction input : Direction.values()) {
            for(Direction output : Direction.values()) {
                if(input == output) continue;
                Map<Direction, String> faces = new LinkedHashMap<>();
                for(Direction side : Direction.values()) faces.put(side, craneFace(skin, input, output, side));
                int top = input.getAxis() != Direction.Axis.Y ? skin.topRotation().apply(input, craneLeftHand(input, output)) : 0;
                models.put(input.getSerializedName() + "_" + output.getSerializedName(), this.craneModel(name + "_" + input.getSerializedName() + "_" + output.getSerializedName(), faces, top));
            }
        }

        BlockModelBuilder fallback = models.get("down_up");
        this.getVariantBuilder(block).forAllStates(state -> {
            BlockModelBuilder model = models.get(state.getValue(CraneBaseBlock.INPUT).getSerializedName() + "_" + state.getValue(CraneBaseBlock.OUTPUT).getSerializedName());
            return ConfiguredModel.builder().modelFile(model != null ? model : fallback).build();
        });

        // The inventory icon reads the item metadata (0) as the output side (BlockCraneBase.java:218-247): out at the bottom, in on
        // top and the "directional up" icon on all four sides, unlike any placed state.
        Map<Direction, String> item = new LinkedHashMap<>();
        for(Direction side : Direction.values()) {
            item.put(side, side == Direction.DOWN ? skin.out() : side == Direction.UP ? skin.in() : skin.icon(CraneIcon.DIRECTIONAL_UP));
        }
        this.simpleBlockItem(block, this.craneModel(name + "_item", item, 0));
    }

    private static Direction craneLeftHand(Direction input, Direction output) {
        return Direction.from3DDataValue(CRANE_ROTATION[input.get3DDataValue()][output.get3DDataValue()]);
    }

    /** BlockCraneBase.getIcon (:118-215) for one side. */
    private static String craneFace(CraneSkin skin, Direction input, Direction output, Direction side) {
        boolean overridden = output != input.getOpposite();
        Direction left = craneLeftHand(input, output);

        if(side.getAxis() == Direction.Axis.Y) {
            if(side == output) return skin.out();
            if(side == input) return skin.in();

            if(side == Direction.UP) {
                if(!overridden) return skin.icon(CraneIcon.DIRECTIONAL);
                if(left == Direction.UP) return skin.icon(CraneIcon.TURN_LEFT);
                if(left == Direction.DOWN) return skin.icon(CraneIcon.TURN_RIGHT);
            }

            return "crane_top";
        }

        if(side == output) return skin.sideOut();
        if(side == input) return skin.sideIn();

        if(overridden) {
            if(side == left) {
                if(output == Direction.UP) return skin.icon(CraneIcon.SIDE_LEFT_TURN_UP);
                if(output == Direction.DOWN) return skin.icon(CraneIcon.SIDE_RIGHT_TURN_DOWN);
                if(input == Direction.UP) return skin.icon(CraneIcon.SIDE_UP_TURN_RIGHT);
                if(input == Direction.DOWN) return skin.icon(CraneIcon.SIDE_DOWN_TURN_LEFT);
            }
            if(side == left.getOpposite()) {
                if(output == Direction.UP) return skin.icon(CraneIcon.SIDE_RIGHT_TURN_UP);
                if(output == Direction.DOWN) return skin.icon(CraneIcon.SIDE_LEFT_TURN_DOWN);
                if(input == Direction.UP) return skin.icon(CraneIcon.SIDE_UP_TURN_LEFT);
                if(input == Direction.DOWN) return skin.icon(CraneIcon.SIDE_DOWN_TURN_RIGHT);
            }
        } else {
            if(output == Direction.UP) return skin.icon(CraneIcon.DIRECTIONAL_UP);
            if(output == Direction.DOWN) return skin.icon(CraneIcon.DIRECTIONAL_DOWN);
        }

        return "crane_side";
    }

    /** A full cube with one texture per face, the top turned by the original's uvRotateTop value. */
    private BlockModelBuilder craneModel(String name, Map<Direction, String> faces, int uvRotateTop) {
        BlockModelBuilder model = this.models().withExistingParent(name, mcLoc("block/block")).texture("particle", modLoc("block/crane_side"));
        for(Entry<Direction, String> face : faces.entrySet()) model.texture(face.getKey().getSerializedName(), modLoc("block/" + face.getValue()));

        ModelBuilder.FaceRotation top = switch(uvRotateTop) {
            case 1 -> ModelBuilder.FaceRotation.CLOCKWISE_90;
            case 2 -> ModelBuilder.FaceRotation.COUNTERCLOCKWISE_90;
            case 3 -> ModelBuilder.FaceRotation.UPSIDE_DOWN;
            default -> ModelBuilder.FaceRotation.ZERO;
        };

        model.element().from(0, 0, 0).to(16, 16, 16).allFaces((dir, face) -> {
            face.texture("#" + dir.getSerializedName()).cullface(dir);
            if(dir == Direction.UP) face.rotation(top);
        }).end();
        return model;
    }

    /*
     * Goal 31A conveyors. The original drew them with hand-written block faces (RenderConveyor.java:67-111,
     * RenderConveyorChute.java:115-219, RenderConveyorLift.java:24-170). Every model here is the north-facing piece (input on
     * the north side, original metadata 2) and the block states turn it by 90 degrees per facing. The original's UV rotations
     * map as uvRotate 1 = 90 degrees clockwise, 2 = 90 counter-clockwise, 3 = 180.
     */
    private void conveyorBlocks() {
        this.conveyorBelt(NtmBlocks.CONVEYOR, "conveyor");
        this.conveyorBelt(NtmBlocks.CONVEYOR_EXPRESS, "conveyor_express");
        this.conveyorBelt(NtmBlocks.CONVEYOR_DOUBLE, "conveyor_double");
        this.conveyorBelt(NtmBlocks.CONVEYOR_TRIPLE, "conveyor_triple");
        this.conveyorLift();
        this.conveyorChute();
    }

    private static int conveyorRotation(Direction facing) {
        return switch(facing) {
            case EAST -> 90;
            case SOUTH -> 180;
            case WEST -> 270;
            default -> 0;
        };
    }

    private BlockModelBuilder conveyorModel(String name) {
        return this.models().getBuilder(name).parent(new ModelFile.UncheckedModelFile(mcLoc("block/block")))
                .texture("particle", modLoc("block/conveyor")).texture("belt", modLoc("block/conveyor"))
                .texture("side", modLoc("block/conveyor_side")).texture("concrete", modLoc("block/concrete_smooth"));
    }

    /** One box with the same texture on every face, the up face (and optionally the down face) rotated. */
    private void conveyorBox(BlockModelBuilder model, float x1, float y1, float z1, float x2, float y2, float z2, String texture,
                             ModelBuilder.FaceRotation up, ModelBuilder.FaceRotation down) {
        var element = model.element().from(x1, y1, z1).to(x2, y2, z2);
        for(Direction face : Direction.values()) {
            var builder = element.face(face).texture(texture);
            if(face == Direction.UP) builder.rotation(up);
            if(face == Direction.DOWN) builder.rotation(down);
        }
    }

    /**
     * A belt box with the block icons of a north-facing belt (BlockConveyorBase.java:44-54): the belt texture on top and
     * bottom and on the end faces, the side texture along the travel direction, the top turned by 180 degrees and, for
     * straight belts, the west side too.
     */
    private void conveyorBeltBox(BlockModelBuilder model, float x1, float y1, float z1, float x2, float y2, float z2, String top, boolean straight) {
        var element = model.element().from(x1, y1, z1).to(x2, y2, z2);
        element.face(Direction.UP).texture(top).rotation(ModelBuilder.FaceRotation.UPSIDE_DOWN).end();
        element.face(Direction.DOWN).texture(top).end();
        element.face(Direction.NORTH).texture(straight ? "#belt" : "#side").end();
        element.face(Direction.SOUTH).texture(straight ? "#belt" : "#side").end();
        element.face(Direction.EAST).texture("#side").end();
        if(straight) {
            // uvRotateWest = 3 reads the face from the top of the texture, turned by 180 degrees
            element.face(Direction.WEST).texture("#side").uvs(z1, 0, z2, y2 - y1).rotation(ModelBuilder.FaceRotation.UPSIDE_DOWN).end();
        } else {
            element.face(Direction.WEST).texture("#side").end();
        }
    }

    /** Bendable belts (BlockConveyorBendable.java:33-50): straight, left and right models with their own top textures. */
    private void conveyorBelt(DeferredBlock<Block> block, String texture) {
        Map<ConveyorBlock.Shape, ModelFile> models = new LinkedHashMap<>();
        for(ConveyorBlock.Shape shape : ConveyorBlock.Shape.values()) {
            boolean straight = shape == ConveyorBlock.Shape.STRAIGHT;
            String top = straight ? texture : texture + "_curve_" + shape.getSerializedName();
            BlockModelBuilder model = this.conveyorModel(texture + "_" + shape.getSerializedName())
                    .texture("particle", modLoc("block/" + texture)).texture("belt", modLoc("block/" + texture)).texture("top", modLoc("block/" + top));
            this.conveyorBeltBox(model, 0, 0, 0, 16, 4, 16, "#top", straight);
            models.put(shape, model);
        }

        this.getVariantBuilder(block.get()).forAllStates(state -> ConfiguredModel.builder()
                .modelFile(models.get(state.getValue(ConveyorBlock.SHAPE)))
                .rotationY(conveyorRotation(state.getValue(ConveyorBaseBlock.HORIZONTAL_FACING)))
                .build());
    }

    /**
     * RenderConveyorLift.java:24-166 for metadata 2: concrete posts and a back wall with the chain belt, the bottom piece adds
     * belt stubs on the three open sides and an iron floor, the top piece is a half-high frame sending items south.
     */
    private void conveyorLift() {
        BlockModelBuilder middle = this.conveyorModel("conveyor_lift_middle");
        BlockModelBuilder bottom = this.conveyorModel("conveyor_lift_bottom").texture("iron", mcLoc("block/iron_block"));
        for(BlockModelBuilder model : new BlockModelBuilder[] {middle, bottom}) {
            ModelBuilder.FaceRotation none = ModelBuilder.FaceRotation.ZERO;
            this.conveyorBox(model, 0, 0, 0, 4, 16, 4, "#concrete", none, none);
            this.conveyorBox(model, 12, 0, 0, 16, 16, 4, "#concrete", none, none);
            this.conveyorBox(model, 0, 0, 12, 16, 16, 16, "#concrete", none, none);
            this.conveyorBox(model, 4, 0, 10, 12, 16, 12, "#belt", ModelBuilder.FaceRotation.UPSIDE_DOWN, none);
        }
        this.conveyorBox(bottom, 0, 0, 4, 4, 4, 12, "#belt", ModelBuilder.FaceRotation.CLOCKWISE_90, ModelBuilder.FaceRotation.CLOCKWISE_90);
        this.conveyorBox(bottom, 12, 0, 4, 16, 4, 12, "#belt", ModelBuilder.FaceRotation.COUNTERCLOCKWISE_90, ModelBuilder.FaceRotation.COUNTERCLOCKWISE_90);
        this.conveyorBox(bottom, 4, 0, 0, 12, 4, 4, "#belt", ModelBuilder.FaceRotation.UPSIDE_DOWN, ModelBuilder.FaceRotation.ZERO);
        this.conveyorBox(bottom, 4, 0, 4, 12, 4, 10, "#iron", ModelBuilder.FaceRotation.ZERO, ModelBuilder.FaceRotation.ZERO);

        BlockModelBuilder top = this.conveyorModel("conveyor_lift_top");
        this.conveyorBox(top, 0, 0, 0, 4, 8, 16, "#concrete", ModelBuilder.FaceRotation.ZERO, ModelBuilder.FaceRotation.ZERO);
        this.conveyorBox(top, 12, 0, 0, 16, 8, 16, "#concrete", ModelBuilder.FaceRotation.ZERO, ModelBuilder.FaceRotation.ZERO);
        this.conveyorBeltBox(top, 4, 0, 10, 12, 4, 16, "#belt", true);

        this.getVariantBuilder(NtmBlocks.CONVEYOR_LIFT.get()).forAllStates(state -> ConfiguredModel.builder()
                .modelFile(switch(state.getValue(ConveyorLiftBlock.PART)) {
                    case BOTTOM -> bottom;
                    case MIDDLE -> middle;
                    case TOP -> top;
                })
                .rotationY(conveyorRotation(state.getValue(ConveyorBaseBlock.HORIZONTAL_FACING)))
                .build());
    }

    /**
     * RenderConveyorChute.java:115-219: four concrete corner posts; a cross-shaped belt at the bottom of the lowest chute,
     * otherwise a short belt stub towards each neighbouring belt; grate panes on the sides without a belt, starting above the
     * belt in the lowest chute and left out on its output side.
     */
    private void conveyorChute() {
        ModelBuilder.FaceRotation none = ModelBuilder.FaceRotation.ZERO;

        BlockModelBuilder posts = this.conveyorModel("conveyor_chute_posts").renderType("cutout");
        this.conveyorBox(posts, 0, 0, 0, 4, 16, 4, "#concrete", none, none);
        this.conveyorBox(posts, 12, 0, 0, 16, 16, 4, "#concrete", none, none);
        this.conveyorBox(posts, 0, 0, 12, 4, 16, 16, "#concrete", none, none);
        this.conveyorBox(posts, 12, 0, 12, 16, 16, 16, "#concrete", none, none);

        BlockModelBuilder belt = this.conveyorModel("conveyor_chute_belt").renderType("cutout");
        this.conveyorBeltBox(belt, 4, 0, 0, 12, 4, 16, "#belt", true);
        this.conveyorBeltBox(belt, 0, 0, 4, 4, 4, 12, "#belt", true);
        this.conveyorBeltBox(belt, 12, 0, 4, 16, 4, 12, "#belt", true);

        BlockModelBuilder stub = this.conveyorModel("conveyor_chute_stub").renderType("cutout");
        var stubElement = stub.element().from(4, 0, 0).to(12, 4, 2);
        for(Direction face : Direction.values()) {
            if(face == Direction.UP) stubElement.face(face).texture("#belt").rotation(ModelBuilder.FaceRotation.UPSIDE_DOWN).end();
            else stubElement.face(face).texture("#side").end();
        }

        BlockModelBuilder paneLow = this.conveyorModel("conveyor_chute_pane").renderType("cutout").texture("grate", modLoc("block/grate_top"));
        BlockModelBuilder paneHigh = this.conveyorModel("conveyor_chute_pane_high").renderType("cutout").texture("grate", modLoc("block/grate_top"));
        paneLow.element().from(4, 0, 2).to(12, 16, 2).face(Direction.NORTH).texture("#grate").end().face(Direction.SOUTH).texture("#grate").end();
        paneHigh.element().from(4, 4, 2).to(12, 16, 2).face(Direction.NORTH).texture("#grate").end().face(Direction.SOUTH).texture("#grate").end();

        MultiPartBlockStateBuilder builder = this.getMultipartBuilder(NtmBlocks.CONVEYOR_CHUTE.get());
        builder.part().modelFile(posts).addModel().end();

        for(Direction dir : Direction.Plane.HORIZONTAL) {
            int y = conveyorRotation(dir);
            BooleanProperty side = ConveyorChuteBlock.sideProperty(dir);

            builder.part().modelFile(belt).rotationY(y).addModel()
                    .condition(ConveyorChuteBlock.BOTTOM, true).condition(ConveyorBaseBlock.HORIZONTAL_FACING, dir).end();
            builder.part().modelFile(stub).rotationY(y).addModel()
                    .condition(ConveyorChuteBlock.BOTTOM, false).condition(side, true).end();
            builder.part().modelFile(paneLow).rotationY(y).addModel()
                    .condition(ConveyorChuteBlock.BOTTOM, false).condition(side, false).end();

            // the lowest chute sends items out on the side opposite its input, so that side has no pane
            Direction[] facings = Direction.Plane.HORIZONTAL.stream().filter(f -> f != dir.getOpposite()).toArray(Direction[]::new);
            builder.part().modelFile(paneHigh).rotationY(y).addModel()
                    .condition(ConveyorChuteBlock.BOTTOM, true).condition(side, false).condition(ConveyorBaseBlock.HORIZONTAL_FACING, facings).end();
        }
    }

    private void steelBeamBlock() {
        // beam.obj is an unrotated 1/8-wide column. Its sides use the first 1/8 of the texture width.
        BlockModelBuilder model = this.models().getBuilder("steel_beam")
                .texture("particle", modLoc("block/steel_beam")).texture("beam", modLoc("block/steel_beam"));
        var element = model.element().from(7, 0, 7).to(9, 16, 9);
        for(Direction face : Direction.values()) {
            var builder = element.face(face).texture("#beam");
            if(face.getAxis() == Direction.Axis.Y) {
                // The original OBJ loader flips V; its cap patch is the bottom-right 2x2 texels.
                builder.uvs(2, 14, 4, 16).rotation(face == Direction.UP
                        ? ModelBuilder.FaceRotation.COUNTERCLOCKWISE_90 : ModelBuilder.FaceRotation.CLOCKWISE_90);
            } else {
                builder.uvs(0.00056F, 0.00056F, 2.000432F, 15.99944F);
            }
        }
        this.simpleBlockWithItem(NtmBlocks.STEEL_BEAM.get(), model);
    }

    private void steelGrateBlock() {
        Map<Integer, ModelFile> models = new LinkedHashMap<>();
        for(int height = -1; height <= 8; height++) {
            BlockModelBuilder model = this.models().getBuilder("steel_grate_" + (height + 1))
                    .renderType("cutout")
                    .texture("particle", modLoc("block/grate_top"))
                    .texture("top", modLoc("block/grate_top"))
                    .texture("side", modLoc("block/grate_side"));
            var element = model.element().from(0, height * 2, 0).to(16, height * 2 + 2, 16);
            // No cullface: the -1 and 8 states are rendered across the logical block boundary.
            for(Direction face : Direction.values()) {
                if(face.getAxis() == Direction.Axis.Y) {
                    element.face(face).texture("#top").uvs(0, 0, 16, 16);
                } else {
                    int renderedHeight = height == -1 ? 7 : height == 8 ? 0 : height;
                    element.face(face).texture("#side").uvs(0, 14 - renderedHeight * 2, 16, 16 - renderedHeight * 2);
                }
            }
            models.put(height, model);
        }
        this.getVariantBuilder(NtmBlocks.STEEL_GRATE.get()).forAllStates(state ->
                ConfiguredModel.builder().modelFile(models.get(state.getValue(SteelGrateBlock.HEIGHT) == 9
                        ? -1 : state.getValue(SteelGrateBlock.HEIGHT))).build());
        this.simpleBlockItem(NtmBlocks.STEEL_GRATE.get(), models.get(0));
    }

    /** Creates block with item, uses cube all model */
    public void simpleCubeAllBlock(DeferredBlock<? extends Block> block) { this.simpleBlockWithItem(block.get(), this.cubeAll(block.get())); }

    private void particleOnlyBlock(DeferredBlock<? extends Block> block, ResourceLocation particleTexture) { this.particleOnlyBlock(block, particleTexture, false); }
    private void particleOnlyBlock(DeferredBlock<? extends Block> block, ResourceLocation particleTexture, boolean frontLight) {
        this.simpleBlock(block.get(), this.models().getBuilder(name(block) + "_particle").texture("particle", particleTexture));
        this.entityBlockItem(block.get(), frontLight);
    }

    /** One particle-only model for every state of the block; leaves the item model alone. */
    private void particleOnlyState(DeferredBlock<? extends Block> block, ResourceLocation particleTexture) {
        this.simpleBlock(block.get(), this.models().getBuilder(name(block) + "_particle").texture("particle", particleTexture));
    }

    private void entityBlockItem(Block block, boolean frontLight) {
        this.itemModels().getBuilder(this.key(block).getPath()).parent(new ModelFile.UncheckedModelFile("builtin/entity")).guiLight(frontLight ? BlockModel.GuiLight.FRONT : BlockModel.GuiLight.SIDE);
    }

    private void crateBlock(Block block, String sideTexture, String topTexture) {
        String blockName = this.key(block).getPath();
        ModelFile model = this.models().cubeBottomTop(blockName, modLoc("block/" + sideTexture), modLoc("block/" + topTexture), modLoc("block/" + topTexture));
        this.getVariantBuilder(block).forAllStates(state -> {
            int y = switch(state.getValue(com.hbm.blocks.machine.CrateBlock.FACING)) {
                case EAST -> 90;
                case SOUTH -> 180;
                case WEST -> 270;
                default -> 0;
            };
            return ConfiguredModel.builder().modelFile(model).rotationY(y).build();
        });
        this.simpleBlockItem(block, model);
    }

    public void simpleCubeBottomTopBlock(DeferredBlock<? extends Block> block) {
        String blockName = name(block);
        this.simpleBlockWithItem(block, this.models().cubeBottomTop(blockName, modLoc("block/" + blockName + "_side"), modLoc("block/" + blockName + "_bottom"), modLoc("block/" + blockName + "_top")));
    }

    public void cubeTop(DeferredBlock<? extends Block> block) {
        String blockName = name(block);
        this.simpleBlockWithItem(block, this.models().cubeTop(blockName, modLoc("block/" + blockName + "_side"), modLoc("block/" + blockName + "_top")));
    }

    protected String name(Block block) { return this.key(block).getPath(); }
    protected String name(DeferredBlock<? extends Block> block) { return this.key(block).getPath(); }
    protected ResourceLocation key(Block block) { return BuiltInRegistries.BLOCK.getKey(block); }
    protected ResourceLocation key(DeferredBlock<? extends Block> block) { return BuiltInRegistries.BLOCK.getKey(block.get()); }
    protected ResourceLocation blockTexture(DeferredBlock<? extends Block> block) { ResourceLocation name = this.key(block); return ResourceLocation.fromNamespaceAndPath(name.getNamespace(), "block/" + name.getPath()); }
    protected ResourceLocation blockTexture(DeferredBlock<? extends Block> block, String toAppend) { ResourceLocation name = this.key(block); return ResourceLocation.fromNamespaceAndPath(name.getNamespace(), "block/" + name.getPath() + toAppend); }

    private void blockItem(DeferredBlock<? extends Block> block) { this.simpleBlockItem(block.get(), new ModelFile.UncheckedModelFile("hbmsntm:block/" + block.getId().getPath())); }

    protected static class DuctBlockLoaderBuilder extends BlockModelBuilderBase {
        public DuctBlockLoaderBuilder(BlockModelBuilder parent, ExistingFileHelper helper) {
            super(parent, helper);
        }
        @Override public BakedModelType getType() { return BakedModelType.PIPE; }
    }
    protected static class BarrelBlockModelBuilder extends BlockModelBuilderBase {
        public BarrelBlockModelBuilder(BlockModelBuilder parent, ExistingFileHelper helper) {
            super(parent, helper);
        }
        @Override public BakedModelType getType() { return BakedModelType.BARREL; }
    }
    protected static class CableBlockLoaderBuilder extends BlockModelBuilderBase {
        public CableBlockLoaderBuilder(BlockModelBuilder parent, ExistingFileHelper helper) {
            super(parent, helper);
        }
        @Override public BakedModelType getType() { return BakedModelType.CABLE; }
    }
    protected static class PaintableCableLoaderBuilder extends BlockModelBuilderBase {
        public PaintableCableLoaderBuilder(BlockModelBuilder parent, ExistingFileHelper helper) {
            super(parent, helper);
        }
        @Override public BakedModelType getType() { return BakedModelType.PAINTABLE_CABLE; }
    }
    protected static class PaintableDuctLoaderBuilder extends BlockModelBuilderBase {
        public PaintableDuctLoaderBuilder(BlockModelBuilder parent, ExistingFileHelper helper) {
            super(parent, helper);
        }
        @Override public BakedModelType getType() { return BakedModelType.PAINTABLE_DUCT; }
    }
    protected static class DetCordBlockLoaderBuilder extends BlockModelBuilderBase {
        public DetCordBlockLoaderBuilder(BlockModelBuilder parent, ExistingFileHelper helper) {
            super(parent, helper);
        }
        @Override public BakedModelType getType() { return BakedModelType.DET_CORD; }
    }
    protected static class BarbedWireBlockLoaderBuilder extends BlockModelBuilderBase {
        public BarbedWireBlockLoaderBuilder(BlockModelBuilder parent, ExistingFileHelper helper) {
            super(parent, helper);
        }
        @Override public BakedModelType getType() { return BakedModelType.BARBED_WIRE; }
    }
    protected static class SpikesLoaderBuilder extends BlockModelBuilderBase {
        public SpikesLoaderBuilder(BlockModelBuilder parent, ExistingFileHelper helper) {
            super(parent, helper);
        }
        @Override public BakedModelType getType() { return BakedModelType.SPIKES; }
    }
    protected static class RBMKDebrisLoaderBuilder extends BlockModelBuilderBase {
        public RBMKDebrisLoaderBuilder(BlockModelBuilder parent, ExistingFileHelper helper) {
            super(parent, helper);
        }
        @Override public BakedModelType getType() { return BakedModelType.RBMK_DEBRIS; }
    }
    protected static class CraneSplitterLoaderBuilder extends BlockModelBuilderBase {
        public CraneSplitterLoaderBuilder(BlockModelBuilder parent, ExistingFileHelper helper) { super(parent, helper); }
        @Override public BakedModelType getType() { return BakedModelType.CRANE_SPLITTER; }
    }

    protected static class CranePartitionerLoaderBuilder extends BlockModelBuilderBase {
        public CranePartitionerLoaderBuilder(BlockModelBuilder parent, ExistingFileHelper helper) { super(parent, helper); }
        @Override public BakedModelType getType() { return BakedModelType.CRANE_PARTITIONER; }
    }

    protected static class RBMKElementLoaderBuilder extends BlockModelBuilderBase {
        public RBMKElementLoaderBuilder(BlockModelBuilder parent, ExistingFileHelper helper) {
            super(parent, helper);
        }
        @Override public BakedModelType getType() { return BakedModelType.RBMK_ELEMENT; }
    }
    public static class AnvilLoaderBuilder extends BlockModelBuilderBase {
        public AnvilLoaderBuilder(BlockModelBuilder parent, ExistingFileHelper helper) {
            super(parent, helper);
        }
        @Override public BakedModelType getType() { return BakedModelType.ANVIL; }
    }
    public static abstract class BlockModelBuilderBase extends CustomLoaderBuilder<BlockModelBuilder> {

        private final Map<String, ResourceLocation> textures = new LinkedHashMap<>();

        protected BlockModelBuilderBase(BlockModelBuilder parent, ExistingFileHelper helper) {
            super(NuclearTechMod.withDefaultNamespace("ntm_geometry_loader"), parent, helper, false);
        }

        public BlockModelBuilderBase texture(String key, ResourceLocation location) {
            this.textures.put(key, location);
            return this;
        }

        @Override
        public JsonObject toJson(JsonObject json) {
            super.toJson(json);

            JsonObject texturesObject = new JsonObject();
            for(Entry<String, ResourceLocation> entry : this.textures.entrySet()) {
                texturesObject.addProperty(entry.getKey(), entry.getValue().toString());
            }
            json.add("textures", texturesObject);
            json.addProperty("type", this.getType().name().toLowerCase(Locale.US));

            return json;
        }

        public abstract BakedModelType getType();
    }

    public static abstract class ItemModelBuilderBase extends CustomLoaderBuilder<ItemModelBuilder> {

        private final Map<String, ResourceLocation> textures = new LinkedHashMap<>();

        protected ItemModelBuilderBase(ItemModelBuilder parent, ExistingFileHelper helper) {
            super(NuclearTechMod.withDefaultNamespace("ntm_geometry_loader"), parent, helper, false);
        }

        public ItemModelBuilderBase texture(String key, ResourceLocation location) {
            this.textures.put(key, location);
            return this;
        }

        @Override
        public JsonObject toJson(JsonObject json) {
            super.toJson(json);

            JsonObject texturesObject = new JsonObject();
            for(Entry<String, ResourceLocation> entry : this.textures.entrySet()) {
                texturesObject.addProperty(entry.getKey(), entry.getValue().toString());
            }
            json.add("textures", texturesObject);
            json.addProperty("type", this.getType().name().toLowerCase(Locale.US));

            return json;
        }

        public abstract BakedModelType getType();
    }
}
