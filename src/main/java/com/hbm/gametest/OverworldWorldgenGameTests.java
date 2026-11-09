package com.hbm.gametest;

import com.hbm.blockentity.machine.heater.HeaterOilburnerBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.generic.DepthBlock;
import com.hbm.blocks.generic.OutgasBlock;
import com.hbm.config.NtmConfig;
import com.hbm.inventory.FluidContainer;
import com.hbm.inventory.FluidContainerRegistry;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.recipes.CentrifugeRecipes;
import com.hbm.inventory.recipes.CrystallizerRecipes;
import com.hbm.inventory.recipes.CrystallizerRecipes.CrystallizerRecipe;
import com.hbm.inventory.recipes.ShredderRecipes;
import com.hbm.items.NtmItems;
import com.hbm.items.tools.ToolAbilityItem;
import com.hbm.main.NuclearTechMod;
import com.hbm.world.feature.DepthDepositConfiguration;
import com.hbm.world.feature.NtmFeatures;
import com.hbm.world.feature.OreLayerConfiguration;
import com.hbm.world.feature.OreLayerFeature;
import com.hbm.world.feature.SchistStratumFeature;
import com.hbm.world.gen.ConfigCountPlacement;
import com.hbm.world.gen.ConfigGatedAddFeaturesBiomeModifier;
import com.hbm.world.gen.ConfigRarityPlacement;
import com.hbm.world.gen.NtmBiomeModifiers;
import com.hbm.world.gen.NtmConfiguredFeatures;
import com.hbm.world.gen.NtmPlacedFeatures;
import com.google.gson.JsonElement;
import com.google.gson.JsonParser;
import com.mojang.logging.LogUtils;
import com.mojang.serialization.JsonOps;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.Holder;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.HolderSet;
import net.minecraft.core.Registry;
import net.minecraft.core.RegistryAccess;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.contents.TranslatableContents;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.BiomeTags;
import net.minecraft.tags.BlockTags;
import net.minecraft.tags.TagKey;
import net.minecraft.util.RandomSource;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.item.crafting.SingleRecipeInput;
import net.minecraft.world.item.crafting.SmeltingRecipe;
import net.minecraft.world.item.enchantment.Enchantment;
import net.minecraft.world.item.enchantment.Enchantments;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.ItemLike;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.biome.Biomes;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.GenerationStep;
import net.minecraft.world.level.levelgen.LegacyRandomSource;
import net.minecraft.world.level.levelgen.feature.ConfiguredFeature;
import net.minecraft.world.level.levelgen.feature.Feature;
import net.minecraft.world.level.levelgen.feature.FeaturePlaceContext;
import net.minecraft.world.level.levelgen.feature.configurations.NoneFeatureConfiguration;
import net.minecraft.world.level.levelgen.feature.configurations.OreConfiguration;
import net.minecraft.world.level.levelgen.placement.BiomeFilter;
import net.minecraft.world.level.levelgen.placement.HeightRangePlacement;
import net.minecraft.world.level.levelgen.placement.InSquarePlacement;
import net.minecraft.world.level.levelgen.placement.PlacedFeature;
import net.minecraft.world.level.levelgen.placement.PlacementContext;
import net.minecraft.world.level.levelgen.placement.PlacementModifier;
import net.minecraft.world.level.levelgen.placement.RarityFilter;
import net.minecraft.world.level.levelgen.structure.templatesystem.RuleTest;
import net.minecraft.world.level.levelgen.synth.PerlinSimplexNoise;
import net.minecraft.world.level.levelgen.synth.SimplexNoise;
import net.minecraft.world.level.storage.loot.LootParams;
import net.minecraft.world.level.storage.loot.LootTable;
import net.minecraft.world.level.storage.loot.parameters.LootContextParams;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.common.ModConfigSpec;
import net.neoforged.neoforge.common.world.BiomeModifier;
import net.neoforged.neoforge.common.world.BiomeModifiers.AddFeaturesBiomeModifier;
import net.neoforged.neoforge.common.world.ModifiableBiomeInfo;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import net.neoforged.neoforge.registries.NeoForgeRegistries;
import org.slf4j.Logger;

import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.TreeSet;
import java.util.function.Function;
import java.util.function.Predicate;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal28B: the overworld generation of the original 4f5924e2b (the graphitic schist stratum, the schist ores, the
 * depth deposits and depth rock, the ore clusters, alexandrite and the hematite / bauxite / malachite ore layers), the twenty-two new blocks
 * with their drops, outgassing and processing rows, gas shale in the fluid burner, and the CommonConfig worldgen keys behind them. Same template and conventions as
 * {@link NetherEndWorldgenGameTests}; every test has its own batch.
 * <p>
 * Expected values come from the ORIGINAL at 4f5924e2b, cited beside each group of checks (SchistStratum.java:15-62; DepthDeposit.java:14-56;
 * OreLayer3D.java:41-46,85-122; HbmWorldGen.java:98-117,136-139,523-524; DungeonToolbox.java:79-85; MainRegistry.java:597,602-604;
 * WorldConfig.java:123,127-147,176-179,193-195; ModBlocks.java:1253-1256,1271-1294,1308-1309; BlockDepth.java:18-39; BlockDepthOre.java:12-64;
 * BlockCluster.java:19-28; BlockResourceStone.java:33-41; BlockOre.java:84-88; BlockOutgas.java:40-62; SmeltingRecipes.java:54-60;
 * ShredderRecipes.java:66,176,193,374-383; CrystallizerRecipes.java:62-63,73,80,86-87,105,315; CentrifugeRecipes.java:66-76,108-112; OreDictManager.java:336-337,380,
 * 424,437-438,454,471,473-474; FluidContainerRegistry.java:45; ContainerOilburner.java:22), not from the NEO implementation. NEO-only expectations (the Goal28B decisions: separate schist vein
 * count keys holding the effective original counts, the stone_ore_replaceables / base_stone_overworld replacement tags, the world-bottom-relative
 * depth deposit heights, the malachite drop through the ore fortune bonus, the depth ore explosion loss as the vanilla explosion decay, the vanilla
 * copper ingot, NEO's 0.7 smelting experience, the vanilla-ore centrifuge rows, the fluid burner slot taking only containers of the tank's fluid) are
 * marked as such.
 * <p>
 * Real classes and state: the biome modifiers, placed and configured features decoded by the running server from the generated JSON; the biomes'
 * generation settings after the server applied the modifiers; real Feature.place calls with fixed seeds; the loot tables of the server, the
 * RecipeManager, the HBM recipe tables and the fluid container registry. Substitutes: config values are changed with ModConfigSpec.ConfigValue.set
 * and restored in finally; the gated modifier's modify() runs on a fresh BiomeInfo.Builder copied from the biome's original info. The test
 * structure (16 x 12 x 16) cannot reach the stratum's y 26..34, the layers' y 6..64 or the world bottom, so those placements run the production
 * feature on a VirtualLevel: an in-memory WorldGenLevel proxy (getBlockState / setBlock / getSeed / getMinBuildHeight / getLevel, every other call
 * fails the test) with a chosen seed and world bottom; the result is compared with a re-implementation of the original loop on the same blocks.
 * The 1.7.10 NoiseGeneratorPerlin is re-implemented from four 1.21 SimplexNoise octaves built in order from one LegacyRandomSource (the 1.7.10
 * NoiseGeneratorSimplex construction and 2D sample are taken to be the same as 1.21 SimplexNoise). Placements that fit (the depth deposits, the
 * vanilla ore features, the layer feature with a negative threshold) also run on the real test level inside the structure.
 * The ore layers are compared with the original loop run on its own decoration grid (the chunk grid shifted by 8 blocks) for every grid cell
 * that overlaps the NEO chunk.
 * Not evidence: a real client, a dedicated server with real players, real chunk generation of a 1.21 overworld (terrain, decoration order between
 * modifiers), saved worlds and 1.7.10 itself.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class OverworldWorldgenGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-28b]";

    /** One original DungeonToolbox.generateOre call (HbmWorldGen.java:98-99,110-117,136-139): count key and default, vein size, min height, variance. */
    private record Vein(String name, ResourceKey<ConfiguredFeature<?, ?>> configured, ResourceKey<PlacedFeature> placed, Block ore, boolean schist,
                        String countKey, int defaultCount, int size, int minHeight, int variance) {
        int maxY() { return minHeight + variance - 1; }
    }

    // HbmWorldGen.java:110-117 (target stone_gneiss, min 30, variance 10) and :136-139 (target stone, min 15); the counts are the original's
    // effective defaults: literal 25 / 10 (:110-111), WorldConfig uraniumSpawn 7 (:127) x 3, copperSpawn 12 (:131) x 3, asbestosSpawn 2 (:139) x 3,
    // lithiumSpawn 6 (:140), rareSpawn 6 (:141), gassshaleSpawn 5 (:142) x 3; ironClusterSpawn 4, titanium 2, aluminium 3, copper 4 (:176-179).
    // Goal28B decision: each schist vein has its own key holding that effective count.
    private static List<Vein> veins() {
        return List.of(
                new Vein("gneiss_iron", NtmConfiguredFeatures.ORE_GNEISS_IRON, NtmPlacedFeatures.ORE_GNEISS_IRON_PLACED, NtmBlocks.ORE_GNEISS_IRON.get(), true, "gneissIronSpawnRate", 25, 6, 30, 10),
                new Vein("gneiss_gold", NtmConfiguredFeatures.ORE_GNEISS_GOLD, NtmPlacedFeatures.ORE_GNEISS_GOLD_PLACED, NtmBlocks.ORE_GNEISS_GOLD.get(), true, "gneissGoldSpawnRate", 10, 6, 30, 10),
                new Vein("gneiss_uranium", NtmConfiguredFeatures.ORE_GNEISS_URANIUM, NtmPlacedFeatures.ORE_GNEISS_URANIUM_PLACED, NtmBlocks.ORE_GNEISS_URANIUM.get(), true, "gneissUraniumSpawnRate", 7 * 3, 6, 30, 10),
                new Vein("gneiss_copper", NtmConfiguredFeatures.ORE_GNEISS_COPPER, NtmPlacedFeatures.ORE_GNEISS_COPPER_PLACED, NtmBlocks.ORE_GNEISS_COPPER.get(), true, "gneissCopperSpawnRate", 12 * 3, 6, 30, 10),
                new Vein("gneiss_asbestos", NtmConfiguredFeatures.ORE_GNEISS_ASBESTOS, NtmPlacedFeatures.ORE_GNEISS_ASBESTOS_PLACED, NtmBlocks.ORE_GNEISS_ASBESTOS.get(), true, "gneissAsbestosSpawnRate", 2 * 3, 6, 30, 10),
                new Vein("gneiss_lithium", NtmConfiguredFeatures.ORE_GNEISS_LITHIUM, NtmPlacedFeatures.ORE_GNEISS_LITHIUM_PLACED, NtmBlocks.ORE_GNEISS_LITHIUM.get(), true, "gneissLithiumSpawnRate", 6, 6, 30, 10),
                new Vein("gneiss_rare", NtmConfiguredFeatures.ORE_GNEISS_RARE, NtmPlacedFeatures.ORE_GNEISS_RARE_PLACED, NtmBlocks.ORE_GNEISS_RARE.get(), true, "gneissRareEarthSpawnRate", 6, 6, 30, 10),
                new Vein("gneiss_gas", NtmConfiguredFeatures.ORE_GNEISS_GAS, NtmPlacedFeatures.ORE_GNEISS_GAS_PLACED, NtmBlocks.ORE_GNEISS_GAS.get(), true, "gneissGasShaleSpawnRate", 5 * 3, 10, 30, 10),
                new Vein("cluster_iron", NtmConfiguredFeatures.CLUSTER_IRON, NtmPlacedFeatures.CLUSTER_IRON_PLACED, NtmBlocks.CLUSTER_IRON.get(), false, "ironClusterSpawnRate", 4, 6, 15, 45),
                new Vein("cluster_titanium", NtmConfiguredFeatures.CLUSTER_TITANIUM, NtmPlacedFeatures.CLUSTER_TITANIUM_PLACED, NtmBlocks.CLUSTER_TITANIUM.get(), false, "titaniumClusterSpawnRate", 2, 6, 15, 30),
                new Vein("cluster_aluminium", NtmConfiguredFeatures.CLUSTER_ALUMINIUM, NtmPlacedFeatures.CLUSTER_ALUMINIUM_PLACED, NtmBlocks.CLUSTER_ALUMINIUM.get(), false, "aluminiumClusterSpawnRate", 3, 6, 15, 35),
                new Vein("cluster_copper", NtmConfiguredFeatures.CLUSTER_COPPER, NtmPlacedFeatures.CLUSTER_COPPER_PLACED, NtmBlocks.CLUSTER_COPPER.get(), false, "copperClusterSpawnRate", 4, 6, 15, 20));
    }

    /** One original DepthDeposit.generateCondition* call (HbmWorldGen.java:103-108, :523-524): ore, chance, size, fill. */
    private record Deposit(String name, ResourceKey<ConfiguredFeature<?, ?>> configured, Block ore, int chance, int size, double fill) { }

    private static List<Deposit> deposits() {
        return List.of(
                new Deposit("cluster_depth_iron", NtmConfiguredFeatures.DEPTH_CLUSTER_IRON, NtmBlocks.CLUSTER_DEPTH_IRON.get(), 24, 5, 0.6D),
                new Deposit("cluster_depth_titanium", NtmConfiguredFeatures.DEPTH_CLUSTER_TITANIUM, NtmBlocks.CLUSTER_DEPTH_TITANIUM.get(), 32, 5, 0.6D),
                new Deposit("cluster_depth_tungsten", NtmConfiguredFeatures.DEPTH_CLUSTER_TUNGSTEN, NtmBlocks.CLUSTER_DEPTH_TUNGSTEN.get(), 32, 5, 0.6D),
                new Deposit("ore_depth_cinnabar", NtmConfiguredFeatures.DEPTH_ORE_CINNABAR, NtmBlocks.ORE_DEPTH_CINNABAR.get(), 16, 5, 0.8D),
                new Deposit("ore_depth_zirconium", NtmConfiguredFeatures.DEPTH_ORE_ZIRCONIUM, NtmBlocks.ORE_DEPTH_ZIRCONIUM.get(), 16, 5, 0.8D),
                new Deposit("ore_depth_borax", NtmConfiguredFeatures.DEPTH_ORE_BORAX, NtmBlocks.ORE_DEPTH_BORAX.get(), 16, 5, 0.8D));
    }

    /** The placed features of add_overworld_ores in the original call order (HbmWorldGen.java:103-117, :136-139). */
    private static List<ResourceKey<PlacedFeature>> overworldOres() {
        return List.of(NtmPlacedFeatures.DEPTH_CLUSTER_IRON_PLACED, NtmPlacedFeatures.DEPTH_CLUSTER_TITANIUM_PLACED, NtmPlacedFeatures.DEPTH_CLUSTER_TUNGSTEN_PLACED,
                NtmPlacedFeatures.DEPTH_ORE_CINNABAR_PLACED, NtmPlacedFeatures.DEPTH_ORE_ZIRCONIUM_PLACED, NtmPlacedFeatures.DEPTH_ORE_BORAX_PLACED,
                NtmPlacedFeatures.ORE_GNEISS_IRON_PLACED, NtmPlacedFeatures.ORE_GNEISS_GOLD_PLACED, NtmPlacedFeatures.ORE_GNEISS_URANIUM_PLACED,
                NtmPlacedFeatures.ORE_GNEISS_COPPER_PLACED, NtmPlacedFeatures.ORE_GNEISS_ASBESTOS_PLACED, NtmPlacedFeatures.ORE_GNEISS_LITHIUM_PLACED,
                NtmPlacedFeatures.ORE_GNEISS_RARE_PLACED, NtmPlacedFeatures.ORE_GNEISS_GAS_PLACED, NtmPlacedFeatures.CLUSTER_IRON_PLACED,
                NtmPlacedFeatures.CLUSTER_TITANIUM_PLACED, NtmPlacedFeatures.CLUSTER_ALUMINIUM_PLACED, NtmPlacedFeatures.CLUSTER_COPPER_PLACED);
    }

    private static List<ResourceKey<PlacedFeature>> layers() {
        return List.of(NtmPlacedFeatures.HEMATITE_LAYER_PLACED, NtmPlacedFeatures.BAUXITE_LAYER_PLACED, NtmPlacedFeatures.MALACHITE_LAYER_PLACED);
    }

    private static List<ResourceKey<PlacedFeature>> netherDeposits() {
        return List.of(NtmPlacedFeatures.DEPTH_ORE_NETHER_NEODYMIUM_LOW_PLACED, NtmPlacedFeatures.DEPTH_ORE_NETHER_NEODYMIUM_HIGH_PLACED);
    }

    /** The twenty block ids of the batch (ModBlocks.java:1253-1256,1271-1281,1287-1294,1308-1309; ore_depth_cinnebar is NEO's ore_depth_cinnabar). */
    private static final List<String> NEW_BLOCKS = List.of("stone_gneiss", "ore_gneiss_iron", "ore_gneiss_gold", "ore_gneiss_copper", "ore_gneiss_asbestos",
            "ore_gneiss_lithium", "ore_gneiss_rare", "ore_gneiss_gas", "stone_depth", "stone_depth_nether", "ore_depth_cinnabar", "ore_depth_zirconium",
            "ore_depth_borax", "ore_depth_nether_neodymium", "cluster_depth_iron", "cluster_depth_titanium", "cluster_depth_tungsten", "ore_alexandrite",
            "cluster_iron", "cluster_titanium", "cluster_aluminium", "cluster_copper");

    private static List<Block> depthBlocks() {
        return List.of(NtmBlocks.STONE_DEPTH.get(), NtmBlocks.STONE_DEPTH_NETHER.get(), NtmBlocks.ORE_DEPTH_CINNABAR.get(), NtmBlocks.ORE_DEPTH_ZIRCONIUM.get(),
                NtmBlocks.ORE_DEPTH_BORAX.get(), NtmBlocks.ORE_DEPTH_NETHER_NEODYMIUM.get(), NtmBlocks.CLUSTER_DEPTH_IRON.get(), NtmBlocks.CLUSTER_DEPTH_TITANIUM.get(),
                NtmBlocks.CLUSTER_DEPTH_TUNGSTEN.get(), NtmBlocks.ORE_ALEXANDRITE.get());
    }

    // ---------------------------------------------------------------- 1. biome modifiers as applied by the server

    // MainRegistry.java:597 SchistStratum registered unconditionally (DecorateBiomeEvent.Pre, before the ores); HbmWorldGen.java:98-99 alexandrite
    // before and outside if(WorldConfig.overworldOre) (:101), :103-117,136-139 the deposits, schist ores and clusters inside it, in that order;
    // MainRegistry.java:602-604 each layer behind its own switch; HbmWorldGen.java:523-524 the nether neodymium deposits inside if(netherOre) (:503)
    @GameTest(template = TEMPLATE, batch = "hbm28b_modifiers_applied", timeoutTicks = 100)
    public static void modifiers_applied(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    RegistryAccess reg = helper.getLevel().registryAccess();
                    Registry<BiomeModifier> modifiers = reg.registryOrThrow(NeoForgeRegistries.Keys.BIOME_MODIFIERS);

                    BiomeModifier stratum = modifiers.get(NtmBiomeModifiers.ADD_SCHIST_STRATUM);
                    check(stratum instanceof AddFeaturesBiomeModifier, "add_schist_stratum decodes to " + describe(stratum));
                    AddFeaturesBiomeModifier s = (AddFeaturesBiomeModifier) stratum;
                    check(isTag(s.biomes(), BiomeTags.IS_OVERWORLD) && s.step() == GenerationStep.Decoration.LOCAL_MODIFICATIONS, "add_schist_stratum biomes / step " + s.biomes() + " " + s.step());
                    check(keys(s.features()).equals(names(List.of(NtmPlacedFeatures.SCHIST_STRATUM_PLACED))), "add_schist_stratum features " + keys(s.features()));

                    ConfigGatedAddFeaturesBiomeModifier ores = gated(modifiers, NtmBiomeModifiers.ADD_OVERWORLD_ORES);
                    check(ores.config().equals(List.of("overworldOres")) && isTag(ores.biomes(), BiomeTags.IS_OVERWORLD) && ores.step() == GenerationStep.Decoration.UNDERGROUND_ORES,
                            "add_overworld_ores " + ores.config() + " " + ores.biomes() + " " + ores.step());
                    check(keys(ores.features()).equals(names(overworldOres())), "add_overworld_ores features (original order) " + keys(ores.features()));

                    BiomeModifier alex = modifiers.get(NtmBiomeModifiers.ADD_ALEXANDRITE_ORE);
                    check(alex instanceof AddFeaturesBiomeModifier, "add_alexandrite_ore decodes to " + describe(alex));
                    AddFeaturesBiomeModifier a = (AddFeaturesBiomeModifier) alex;
                    check(isTag(a.biomes(), BiomeTags.IS_OVERWORLD) && a.step() == GenerationStep.Decoration.UNDERGROUND_ORES
                            && keys(a.features()).equals(names(List.of(NtmPlacedFeatures.ORE_ALEXANDRITE_PLACED))), "add_alexandrite_ore " + a.biomes() + " " + a.step() + " " + keys(a.features()));

                    List<ResourceKey<BiomeModifier>> layerMods = List.of(NtmBiomeModifiers.ADD_HEMATITE_LAYER, NtmBiomeModifiers.ADD_BAUXITE_LAYER, NtmBiomeModifiers.ADD_MALACHITE_LAYER);
                    List<String> layerSwitches = List.of("enableHematite", "enableBauxite", "enableMalachite");
                    for(int i = 0; i < 3; i++) {
                        ConfigGatedAddFeaturesBiomeModifier m = gated(modifiers, layerMods.get(i));
                        check(m.config().equals(List.of(layerSwitches.get(i))) && isTag(m.biomes(), BiomeTags.IS_OVERWORLD) && m.step() == GenerationStep.Decoration.UNDERGROUND_ORES
                                && keys(m.features()).equals(names(List.of(layers().get(i)))), layerMods.get(i).location() + " " + m.config() + " " + m.step() + " " + keys(m.features()));
                    }

                    ConfigGatedAddFeaturesBiomeModifier nd = gated(modifiers, NtmBiomeModifiers.ADD_NETHER_DEPTH_DEPOSITS);
                    check(nd.config().equals(List.of("netherOres")) && isTag(nd.biomes(), BiomeTags.IS_NETHER) && nd.step() == GenerationStep.Decoration.UNDERGROUND_ORES
                            && keys(nd.features()).equals(names(netherDeposits())), "add_nether_depth_deposits " + nd.config() + " " + nd.biomes() + " " + keys(nd.features()));

                    // the four Goal28A modifiers are unchanged
                    ConfigGatedAddFeaturesBiomeModifier nether = gated(modifiers, NtmBiomeModifiers.ADD_NETHER_ORES);
                    check(nether.config().equals(List.of("netherOres")) && keys(nether.features()).equals(names(List.of(NtmPlacedFeatures.ORE_NETHER_URANIUM_PLACED, NtmPlacedFeatures.ORE_NETHER_TUNGSTEN_PLACED,
                            NtmPlacedFeatures.ORE_NETHER_SULFUR_PLACED, NtmPlacedFeatures.ORE_NETHER_FIRE_PLACED, NtmPlacedFeatures.ORE_NETHER_COAL_PLACED, NtmPlacedFeatures.ORE_NETHER_COBALT_PLACED))),
                            "add_nether_ores changed: " + nether.config() + " " + keys(nether.features()));
                    ConfigGatedAddFeaturesBiomeModifier pu = gated(modifiers, NtmBiomeModifiers.ADD_NETHER_PLUTONIUM_ORE);
                    check(new HashSet<>(pu.config()).equals(Set.of("netherOres", "enablePlutoniumNetherOre")) && keys(pu.features()).equals(names(List.of(NtmPlacedFeatures.ORE_NETHER_PLUTONIUM_PLACED))),
                            "add_nether_plutonium_ore changed: " + pu.config() + " " + keys(pu.features()));
                    check(modifiers.get(NtmBiomeModifiers.ADD_SMOLDERING_NETHERRACK) instanceof AddFeaturesBiomeModifier sm && sm.step() == GenerationStep.Decoration.TOP_LAYER_MODIFICATION
                            && keys(sm.features()).equals(names(List.of(NtmPlacedFeatures.SMOLDERING_NETHERRACK_PLACED))), "add_smoldering_netherrack changed");
                    ConfigGatedAddFeaturesBiomeModifier end = gated(modifiers, NtmBiomeModifiers.ADD_END_ORES);
                    check(end.config().equals(List.of("endOres")) && keys(end.features()).equals(names(List.of(NtmPlacedFeatures.ORE_TIKITE_PLACED))), "add_end_ores changed: " + end.config());

                    // codec and feature registrations
                    PlacedFeature alexPlaced = reg.registryOrThrow(Registries.PLACED_FEATURE).getOrThrow(NtmPlacedFeatures.ORE_ALEXANDRITE_PLACED);
                    check(id("config_rarity").equals(BuiltInRegistries.PLACEMENT_MODIFIER_TYPE.getKey(alexPlaced.placement().get(0).type())), "config rarity type key " + BuiltInRegistries.PLACEMENT_MODIFIER_TYPE.getKey(alexPlaced.placement().get(0).type()));
                    check(id("schist_stratum").equals(BuiltInRegistries.FEATURE.getKey(NtmFeatures.SCHIST_STRATUM.get())) && id("depth_deposit").equals(BuiltInRegistries.FEATURE.getKey(NtmFeatures.DEPTH_DEPOSIT.get()))
                            && id("ore_layer").equals(BuiltInRegistries.FEATURE.getKey(NtmFeatures.ORE_LAYER.get())), "feature registry keys");

                    // with the default switches the server applied: overworld biomes carry the stratum, the 18 ores in order, alexandrite and the layers
                    check(NtmConfig.COMMON.OVERWORLD_ORES.get() && NtmConfig.COMMON.ENABLE_HEMATITE.get() && NtmConfig.COMMON.ENABLE_BAUXITE.get() && NtmConfig.COMMON.ENABLE_MALACHITE.get()
                            && NtmConfig.COMMON.NETHER_ORES.get(), "the server did not start with the default switches");
                    List<ResourceKey<PlacedFeature>> allOverworld = new ArrayList<>(overworldOres());
                    allOverworld.add(NtmPlacedFeatures.ORE_ALEXANDRITE_PLACED);
                    allOverworld.addAll(layers());
                    for(ResourceKey<Biome> key : List.of(Biomes.PLAINS, Biomes.DESERT, Biomes.DEEP_DARK, Biomes.FOREST, Biomes.OCEAN, Biomes.SNOWY_PLAINS)) {
                        Holder<Biome> holder = biome(helper, key);
                        check(inStep(holder, GenerationStep.Decoration.LOCAL_MODIFICATIONS, NtmPlacedFeatures.SCHIST_STRATUM_PLACED), key.location() + " lacks schist_stratum_placed in local_modifications");
                        for(ResourceKey<PlacedFeature> f : allOverworld) check(inStep(holder, GenerationStep.Decoration.UNDERGROUND_ORES, f), key.location() + " lacks " + f.location() + " in underground_ores");
                        List<Integer> idx = new ArrayList<>();
                        List<Holder<PlacedFeature>> ug = holder.value().getGenerationSettings().features().get(GenerationStep.Decoration.UNDERGROUND_ORES.ordinal()).stream().toList();
                        for(ResourceKey<PlacedFeature> f : overworldOres()) for(int i = 0; i < ug.size(); i++) if(ug.get(i).is(f)) { idx.add(i); break; }
                        boolean ordered = idx.size() == 18;
                        for(int i = 1; ordered && i < idx.size(); i++) ordered = idx.get(i) > idx.get(i - 1);
                        check(ordered, key.location() + ": the 18 overworld ores are not in the original order: " + idx);
                        for(ResourceKey<PlacedFeature> f : netherDeposits()) check(!inAnyStep(holder, f), key.location() + " carries " + f.location());
                    }
                    for(ResourceKey<Biome> key : List.of(Biomes.NETHER_WASTES, Biomes.BASALT_DELTAS, Biomes.CRIMSON_FOREST, Biomes.WARPED_FOREST, Biomes.SOUL_SAND_VALLEY)) {
                        Holder<Biome> holder = biome(helper, key);
                        for(ResourceKey<PlacedFeature> f : netherDeposits()) check(inStep(holder, GenerationStep.Decoration.UNDERGROUND_ORES, f), key.location() + " lacks " + f.location());
                        for(ResourceKey<PlacedFeature> f : allOverworld) check(!inAnyStep(holder, f), key.location() + " carries " + f.location());
                        check(!inAnyStep(holder, NtmPlacedFeatures.SCHIST_STRATUM_PLACED), key.location() + " carries the stratum");
                    }
                    for(ResourceKey<Biome> key : List.of(Biomes.THE_END, Biomes.END_HIGHLANDS)) {
                        Holder<Biome> holder = biome(helper, key);
                        for(ResourceKey<PlacedFeature> f : allOverworld) check(!inAnyStep(holder, f), key.location() + " carries " + f.location());
                        for(ResourceKey<PlacedFeature> f : netherDeposits()) check(!inAnyStep(holder, f), key.location() + " carries " + f.location());
                    }
                    // existing ids
                    for(String path : NEW_BLOCKS) check(BuiltInRegistries.BLOCK.containsKey(id(path)) && BuiltInRegistries.ITEM.containsKey(id(path)), "no block / item " + path);
                    for(String path : List.of("ore_gneiss_uranium", "ore_gneiss_uranium_scorched", "ore_gneiss_schrabidium", "resource_hematite", "resource_bauxite", "resource_malachite",
                            "ore_nether_tungsten", "ore_nether_coal", "ore_tikite", "ore_rare", "ore_asbestos")) {
                        check(BuiltInRegistries.BLOCK.containsKey(id(path)), "existing block id " + path + " is gone");
                    }
                    LOGGER.info("{} modifiers_applied: 7 modifiers decoded, 28A four unchanged; overworld biomes stratum + 18 ordered ores + alexandrite + 3 layers; nether 2 neodymium deposits", TAG);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "modifiers_applied"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 2. the config gates

    // HbmWorldGen.java:101 if(WorldConfig.overworldOre) around :103-139; :98-99 alexandrite outside it; MainRegistry.java:597 the stratum always;
    // :602-604 if(WorldConfig.enableHematite / enableBauxite / enableMalachite); HbmWorldGen.java:503 if(netherOre) around :523-524
    @GameTest(template = TEMPLATE, batch = "hbm28b_config_gate", timeoutTicks = 100)
    public static void config_gate(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    Registry<BiomeModifier> modifiers = helper.getLevel().registryAccess().registryOrThrow(NeoForgeRegistries.Keys.BIOME_MODIFIERS);
                    BiomeModifier ores = modifiers.get(NtmBiomeModifiers.ADD_OVERWORLD_ORES), stratum = modifiers.get(NtmBiomeModifiers.ADD_SCHIST_STRATUM);
                    BiomeModifier alex = modifiers.get(NtmBiomeModifiers.ADD_ALEXANDRITE_ORE), nd = modifiers.get(NtmBiomeModifiers.ADD_NETHER_DEPTH_DEPOSITS);
                    List<BiomeModifier> layerMods = List.of(modifiers.get(NtmBiomeModifiers.ADD_HEMATITE_LAYER), modifiers.get(NtmBiomeModifiers.ADD_BAUXITE_LAYER), modifiers.get(NtmBiomeModifiers.ADD_MALACHITE_LAYER));
                    List<ModConfigSpec.BooleanValue> layerSwitches = List.of(NtmConfig.COMMON.ENABLE_HEMATITE, NtmConfig.COMMON.ENABLE_BAUXITE, NtmConfig.COMMON.ENABLE_MALACHITE);
                    Holder<Biome> plains = biome(helper, Biomes.PLAINS), wastes = biome(helper, Biomes.NETHER_WASTES);
                    ModConfigSpec.BooleanValue overworld = NtmConfig.COMMON.OVERWORLD_ORES, nether = NtmConfig.COMMON.NETHER_ORES;
                    boolean saveOverworld = overworld.get(), saveNether = nether.get();
                    boolean[] saveLayers = { layerSwitches.get(0).get(), layerSwitches.get(1).get(), layerSwitches.get(2).get() };
                    try {
                        String stratumName = NtmPlacedFeatures.SCHIST_STRATUM_PLACED.location() + "@" + GenerationStep.Decoration.LOCAL_MODIFICATIONS;
                        overworld.set(true);
                        check(added(ores, plains, BiomeModifier.Phase.ADD).equals(names(overworldOres())), "overworldOres true: plains gained " + added(ores, plains, BiomeModifier.Phase.ADD));
                        overworld.set(false);
                        check(added(ores, plains, BiomeModifier.Phase.ADD).isEmpty(), "overworldOres false: plains gained " + added(ores, plains, BiomeModifier.Phase.ADD));
                        // MainRegistry.java:597 and HbmWorldGen.java:98-99: the stratum and alexandrite do not follow overworldOres
                        check(added(stratum, plains, BiomeModifier.Phase.ADD).equals(List.of(stratumName)), "overworldOres false: the stratum modifier gave " + added(stratum, plains, BiomeModifier.Phase.ADD));
                        check(added(alex, plains, BiomeModifier.Phase.ADD).equals(names(List.of(NtmPlacedFeatures.ORE_ALEXANDRITE_PLACED))), "overworldOres false: the alexandrite modifier gave " + added(alex, plains, BiomeModifier.Phase.ADD));
                        for(int i = 0; i < 3; i++) check(added(layerMods.get(i), plains, BiomeModifier.Phase.ADD).equals(names(List.of(layers().get(i)))), "overworldOres false: layer " + i + " gave " + added(layerMods.get(i), plains, BiomeModifier.Phase.ADD));
                        overworld.set(true);

                        // each layer follows its own switch only
                        for(int off = 0; off < 3; off++) {
                            for(int i = 0; i < 3; i++) layerSwitches.get(i).set(i != off);
                            for(int i = 0; i < 3; i++) {
                                List<String> got = added(layerMods.get(i), plains, BiomeModifier.Phase.ADD);
                                List<String> want = i == off ? List.of() : names(List.of(layers().get(i)));
                                check(got.equals(want), "switch " + off + " off: layer " + i + " gave " + got + ", expected " + want);
                            }
                        }
                        for(int i = 0; i < 3; i++) layerSwitches.get(i).set(true);

                        // the nether neodymium deposits follow netherOres
                        nether.set(true);
                        check(added(nd, wastes, BiomeModifier.Phase.ADD).equals(names(netherDeposits())), "netherOres true: nether_wastes gained " + added(nd, wastes, BiomeModifier.Phase.ADD));
                        nether.set(false);
                        check(added(nd, wastes, BiomeModifier.Phase.ADD).isEmpty(), "netherOres false: nether_wastes gained " + added(nd, wastes, BiomeModifier.Phase.ADD));
                        nether.set(true);
                        // overworldOres does not gate the nether deposits, netherOres does not gate the overworld ores
                        overworld.set(false);
                        check(added(nd, wastes, BiomeModifier.Phase.ADD).equals(names(netherDeposits())), "overworldOres false removed the nether deposits");
                        overworld.set(true);
                        nether.set(false);
                        check(added(ores, plains, BiomeModifier.Phase.ADD).equals(names(overworldOres())), "netherOres false removed the overworld ores");
                        nether.set(true);

                        // non-member biomes and other phases get nothing
                        List<BiomeModifier> overworldMods = new ArrayList<>(List.of(ores, stratum, alex));
                        overworldMods.addAll(layerMods);
                        for(BiomeModifier m : overworldMods) check(added(m, wastes, BiomeModifier.Phase.ADD).isEmpty(), describe(m) + " added to nether_wastes: " + added(m, wastes, BiomeModifier.Phase.ADD));
                        check(added(nd, plains, BiomeModifier.Phase.ADD).isEmpty(), "the nether deposits were added to plains");
                        for(BiomeModifier.Phase phase : BiomeModifier.Phase.values()) {
                            if(phase == BiomeModifier.Phase.ADD) continue;
                            for(BiomeModifier m : overworldMods) check(added(m, plains, phase).isEmpty(), "phase " + phase + " added " + added(m, plains, phase));
                        }
                        LOGGER.info("{} config_gate: 18 ores only with overworldOres; stratum, alexandrite and layers ungated by it; each layer by its own switch; neodymium deposits by netherOres", TAG);
                    } finally {
                        overworld.set(saveOverworld);
                        nether.set(saveNether);
                        for(int i = 0; i < 3; i++) layerSwitches.get(i).set(saveLayers[i]);
                    }
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "config_gate"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 3. config values, counts, heights, rarity

    // WorldConfig.java:123 (overworldOre true), :127-147 (counts, alexandriteSpawn 100), :176-179 (clusters), :193-195 (layers true); DungeonToolbox.java:79-85
    // (veinCount tries, y = minHeight + rand(variance)); HbmWorldGen.java:98 (alexandriteSpawn > 0 && rand.nextInt(alexandriteSpawn) == 0, then one vein
    // y 10 + rand(5)); DepthDeposit.java:16 / :22 (rand.nextInt(chance) == 0, y = yMin + rand(yDev), yMin 0 / 125, yDev 3)
    @GameTest(template = TEMPLATE, batch = "hbm28b_config_values", timeoutTicks = 200)
    public static void config_values(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    Registry<PlacedFeature> placed = level.registryAccess().registryOrThrow(Registries.PLACED_FEATURE);
                    PlacementContext ctx = new PlacementContext(level, level.getChunkSource().getGenerator(), Optional.empty());
                    BlockPos origin = helper.absolutePos(new BlockPos(0, 1, 0));
                    RandomSource random = RandomSource.create(2828L);

                    // the switches
                    Map<String, Boolean> switches = Map.of("overworldOres", true, "enableHematite", true, "enableMalachite", true, "enableBauxite", true);
                    for(Map.Entry<String, Boolean> e : switches.entrySet()) {
                        ModConfigSpec.BooleanValue v = NtmConfig.COMMON.worldgenSwitch(e.getKey());
                        check(v != null && v.getDefault() == e.getValue() && v.get() == e.getValue(), e.getKey() + " default " + (v == null ? null : v.getDefault()) + ", original " + e.getValue());
                    }
                    // the comments and English names (NEO decision for overworldOres: the text says what the switch gates in NEO, not the original's
                    // "General switch for whether overworld ores should be generated")
                    Map<String, ModConfigSpec.ConfigValue<?>> texts = new LinkedHashMap<>();
                    for(String k : List.of("overworldOres", "enableHematite", "enableMalachite", "enableBauxite")) texts.put(k, NtmConfig.COMMON.worldgenSwitch(k));
                    for(Vein v : veins()) texts.put(v.countKey(), NtmConfig.COMMON.worldgenCount(v.countKey()));
                    texts.put("alexandriteSpawnRate", NtmConfig.COMMON.worldgenRarity("alexandriteSpawnRate"));
                    check(texts.size() == 17, "the batch has " + texts.size() + " config keys, expected 17");
                    check(NtmConfig.COMMON.OVERWORLD_ORES.getSpec().getComment().equals("General switch for the schist ores, depth deposits and ore clusters. Does not include special structures like oil."),
                            "overworldOres comment: " + NtmConfig.COMMON.OVERWORLD_ORES.getSpec().getComment());
                    JsonElement english;
                    try {
                        english = JsonParser.parseString(java.nio.file.Files.readString(net.neoforged.fml.ModList.get().getModFileById(NuclearTechMod.MODID).getFile().findResource("assets", NuclearTechMod.MODID, "lang", "en_us.json")));
                    } catch(java.io.IOException e) {
                        throw new IllegalStateException(e);
                    }
                    for(Map.Entry<String, ModConfigSpec.ConfigValue<?>> e : texts.entrySet()) {
                        ModConfigSpec.ValueSpec spec = e.getValue().getSpec();
                        String key = "hbmsntm.configuration.worldgen." + e.getKey();
                        check(key.equals(spec.getTranslationKey()), e.getKey() + " translation key " + spec.getTranslationKey());
                        JsonElement en = english.getAsJsonObject().get(key);
                        JsonElement tooltip = english.getAsJsonObject().get(key + ".tooltip");
                        // defineInRange appends a " Range: a ~ b" line to the comment
                        String comment = spec.getComment() == null ? null : spec.getComment().split("\n")[0];
                        // Goal 29B: the display name is a short name and the comment is the tooltip
                        check(en != null && !en.getAsString().isEmpty() && !en.getAsString().equals(comment), key + " English " + en + ", comment " + comment);
                        check(tooltip != null && tooltip.getAsString().split("\n")[0].equals(comment), key + " English tooltip " + tooltip + ", comment " + comment);
                    }
                    ModConfigSpec.IntValue rarity = NtmConfig.COMMON.worldgenRarity("alexandriteSpawnRate");
                    check(rarity != null && rarity.getDefault() == 100 && rarity.get() == 100, "alexandriteSpawnRate default " + (rarity == null ? null : rarity.getDefault()) + ", original 100");
                    check(NtmConfig.COMMON.worldgenRarity("noSuchKey") == null && NtmConfig.COMMON.worldgenRarity("gneissIronSpawnRate") == null, "an unknown or count name resolves to a rarity");

                    // the twelve counts, their placements and heights
                    for(Vein v : veins()) {
                        ModConfigSpec.IntValue count = NtmConfig.COMMON.worldgenCount(v.countKey());
                        check(count != null, v.name() + ": no config count " + v.countKey());
                        check(count.getDefault() == v.defaultCount() && count.get() == v.defaultCount(), v.name() + ": default " + count.getDefault() + " / live " + count.get() + ", original " + v.defaultCount());
                        PlacedFeature pf = placed.getOrThrow(v.placed());
                        List<PlacementModifier> mods = pf.placement();
                        check(mods.size() == 4 && mods.get(0) instanceof ConfigCountPlacement && mods.get(1) instanceof InSquarePlacement && mods.get(2) instanceof HeightRangePlacement
                                && mods.get(3) instanceof BiomeFilter, v.name() + " placement " + mods);
                        check(pf.feature().is(v.configured()), v.name() + " places " + pf.feature());
                        long n = mods.get(0).getPositions(ctx, random, origin).count();
                        check(n == v.defaultCount(), v.name() + ": config_count yields " + n + ", expected " + v.defaultCount());
                        int[] ys = sampleY(ctx, random, origin, mods.get(2), 4000);
                        check(ys[0] == v.minHeight() && ys[1] == v.maxY(), v.name() + ": sampled y " + ys[0] + ".." + ys[1] + ", original " + v.minHeight() + ".." + v.maxY());
                        LOGGER.info("{} config_values: {} count {} (key {}), y {}..{}", TAG, v.name(), n, v.countKey(), ys[0], ys[1]);
                    }
                    // the count is read per call
                    ModConfigSpec.IntValue gold = NtmConfig.COMMON.GNEISS_GOLD_SPAWN_RATE;
                    int saveGold = gold.get();
                    try {
                        PlacementModifier goldCount = placed.getOrThrow(NtmPlacedFeatures.ORE_GNEISS_GOLD_PLACED).placement().get(0);
                        for(int want : new int[] { 0, 3, 10 }) {
                            gold.set(want);
                            check(goldCount.getPositions(ctx, random, origin).count() == want, "gneissGoldSpawnRate " + want + " not followed");
                        }
                    } finally {
                        gold.set(saveGold);
                    }

                    // alexandrite: one vein every nth chunk, y 10..14
                    PlacedFeature alex = placed.getOrThrow(NtmPlacedFeatures.ORE_ALEXANDRITE_PLACED);
                    List<PlacementModifier> am = alex.placement();
                    check(am.size() == 4 && am.get(0) instanceof ConfigRarityPlacement && am.get(1) instanceof InSquarePlacement && am.get(2) instanceof HeightRangePlacement && am.get(3) instanceof BiomeFilter,
                            "alexandrite placement " + am);
                    int[] ay = sampleY(ctx, random, origin, am.get(2), 2000);
                    check(ay[0] == 10 && ay[1] == 14, "alexandrite y " + ay[0] + ".." + ay[1] + ", original 10..14");
                    int saveRarity = rarity.get();
                    try {
                        for(int n : new int[] { 0, 1, 7, 100 }) {
                            rarity.set(n);
                            RandomSource r1 = RandomSource.create(98765L + n), r2 = RandomSource.create(98765L + n);
                            int hits = 0;
                            for(int i = 0; i < 5000; i++) {
                                long got = am.get(0).getPositions(ctx, r1, origin).count();
                                boolean want = n > 0 && r2.nextInt(n) == 0;
                                check(got == (want ? 1 : 0), "alexandriteSpawnRate " + n + " trial " + i + ": " + got + " positions, the original roll gives " + want);
                                hits += (int) got;
                            }
                            LOGGER.info("{} config_values: alexandriteSpawnRate {} -> {} of 5000 chunks", TAG, n, hits);
                            if(n == 0) check(hits == 0, "rarity 0 placed " + hits);
                            if(n == 1) check(hits == 5000, "rarity 1 placed " + hits);
                        }
                    } finally {
                        rarity.set(saveRarity);
                    }

                    // the depth deposits: rarity 1 in chance, x/z in the chunk, y bottom + 0..2 (overworld) / absolute 0..2 and 125..127 (nether)
                    List<ResourceKey<PlacedFeature>> depthPlaced = List.of(NtmPlacedFeatures.DEPTH_CLUSTER_IRON_PLACED, NtmPlacedFeatures.DEPTH_CLUSTER_TITANIUM_PLACED, NtmPlacedFeatures.DEPTH_CLUSTER_TUNGSTEN_PLACED,
                            NtmPlacedFeatures.DEPTH_ORE_CINNABAR_PLACED, NtmPlacedFeatures.DEPTH_ORE_ZIRCONIUM_PLACED, NtmPlacedFeatures.DEPTH_ORE_BORAX_PLACED);
                    for(int i = 0; i < 6; i++) {
                        Deposit d = deposits().get(i);
                        PlacedFeature pf = placed.getOrThrow(depthPlaced.get(i));
                        List<PlacementModifier> mods = pf.placement();
                        check(pf.feature().is(d.configured()) && mods.size() == 4 && mods.get(0) instanceof RarityFilter && mods.get(1) instanceof InSquarePlacement
                                && mods.get(2) instanceof HeightRangePlacement && mods.get(3) instanceof BiomeFilter, d.name() + " placement " + mods);
                        check(json(mods.get(0)).equals(JsonParser.parseString("{\"type\":\"minecraft:rarity_filter\",\"chance\":" + d.chance() + "}")), d.name() + " rarity " + json(mods.get(0)) + ", original 1 in " + d.chance());
                        check(json(mods.get(2)).equals(JsonParser.parseString("{\"type\":\"minecraft:height_range\",\"height\":{\"type\":\"minecraft:uniform\",\"min_inclusive\":{\"above_bottom\":0},\"max_inclusive\":{\"above_bottom\":2}}}")),
                                d.name() + " height " + json(mods.get(2)));
                        int[] ys = sampleY(ctx, random, origin, mods.get(2), 600);
                        check(ys[0] == ctx.getMinGenY() && ys[1] == ctx.getMinGenY() + 2, d.name() + ": sampled y " + ys[0] + ".." + ys[1] + " with the generation bottom " + ctx.getMinGenY());
                    }
                    int[][] netherY = { { 0, 2 }, { 125, 127 } };
                    for(int i = 0; i < 2; i++) {
                        PlacedFeature pf = placed.getOrThrow(netherDeposits().get(i));
                        List<PlacementModifier> mods = pf.placement();
                        check(pf.feature().is(NtmConfiguredFeatures.DEPTH_ORE_NETHER_NEODYMIUM) && mods.size() == 4 && json(mods.get(0)).equals(JsonParser.parseString("{\"type\":\"minecraft:rarity_filter\",\"chance\":16}"))
                                && mods.get(1) instanceof InSquarePlacement && mods.get(3) instanceof BiomeFilter, "nether neodymium placement " + i + " " + mods);
                        int[] ys = sampleY(ctx, random, origin, mods.get(2), 600);
                        check(ys[0] == netherY[i][0] && ys[1] == netherY[i][1], "nether neodymium " + i + ": y " + ys[0] + ".." + ys[1] + ", original " + netherY[i][0] + ".." + netherY[i][1]);
                    }
                    // the stratum and the layers: once per chunk, no placement modifiers
                    for(ResourceKey<PlacedFeature> key : List.of(NtmPlacedFeatures.SCHIST_STRATUM_PLACED, NtmPlacedFeatures.HEMATITE_LAYER_PLACED, NtmPlacedFeatures.BAUXITE_LAYER_PLACED, NtmPlacedFeatures.MALACHITE_LAYER_PLACED)) {
                        check(placed.getOrThrow(key).placement().isEmpty(), key.location() + " has placement modifiers " + placed.getOrThrow(key).placement());
                    }
                    LOGGER.info("{} config_values: 4 switches, 12 counts, 1 rarity at the original defaults; heights and rarities as the original", TAG);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "config_values"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 4. the schist stratum

    /** SchistStratum.java:42-49 on the noise value n: -1 when the column is skipped. */
    private static int originalRange(double n) {
        if(!(n > 5)) return -1;
        int range = (int) ((n - 5) * 3);
        if(range > 4) range = 8 - range;
        if(range < 0) return -1;
        return range;
    }

    // SchistStratum.java:23 NoiseGeneratorPerlin(new Random(seed), 4), :34-35 scale 0.01 threshold 5, :37-61 per column n = noise(x * 0.01, z * 0.01),
    // range, y 30 - range .. 30 + range, replace stone with stone_gneiss; :28 dimension 0 only. Goal28B decision: stone_ore_replaceables stands in for
    // isReplaceableOreGen(stone).
    @GameTest(template = TEMPLATE, batch = "hbm28b_stratum", timeoutTicks = 200)
    public static void stratum(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    // the n -> range helper against the original lines over a sweep and at the branch points
                    int sweep = 0;
                    for(int i = -4000; i <= 4000; i++) {
                        double n = i * 0.005D;
                        check(SchistStratumFeature.range(n) == originalRange(n), "range(" + n + ") = " + SchistStratumFeature.range(n) + ", original " + originalRange(n));
                        sweep++;
                    }
                    double[][] points = { { 5.0, -1 }, { 4.0, -1 }, { -9.0, -1 }, { 5.1, 0 }, { 5.34, 1 }, { 6.4, 4 }, { 6.66, 4 }, { 6.67, 3 }, { 6.7, 3 }, { 7.0, 2 }, { 7.4, 1 }, { 7.67, 0 }, { 8.0, -1 }, { 9.5, -1 } };
                    for(double[] p : points) check(SchistStratumFeature.range(p[0]) == (int) p[1], "range(" + p[0] + ") = " + SchistStratumFeature.range(p[0]) + ", expected " + (int) p[1]);

                    // the 1.21 noise scaled by 15 equals the 1.7.10 NoiseGeneratorPerlin(rand, 4) sum
                    double maxDelta = 0;
                    int samples = 0;
                    for(long seed : new long[] { 0L, 1L, 28L, -987654321L, 123456789012345L, level.getSeed() }) {
                        PerlinSimplexNoise neo = new PerlinSimplexNoise(new LegacyRandomSource(seed), List.of(-3, -2, -1, 0));
                        for(int x = -2000; x <= 2000; x += 137) for(int z = -2000; z <= 2000; z += 151) {
                            double a = 15.0D * neo.getValue(x * 0.01D, z * 0.01D, false), b = legacyPerlin(seed, x * 0.01D, z * 0.01D);
                            maxDelta = Math.max(maxDelta, Math.abs(a - b));
                            samples++;
                        }
                        for(double[] p : new double[][] { { 0.37, -12.5 }, { 3.0, 7.0 }, { -0.25, 0.125 } }) {
                            maxDelta = Math.max(maxDelta, Math.abs(15.0D * neo.getValue(p[0], p[1], false) - legacyPerlin(seed, p[0], p[1])));
                            samples++;
                        }
                    }
                    check(maxDelta < 1e-9, "15 x PerlinSimplexNoise differs from the 1.7.10 octave sum by " + maxDelta);

                    // the production feature on a VirtualLevel: pick a chunk whose columns reach the stratum (folded ones included)
                    long seed = 28L;
                    int bestX = 0, bestZ = 0, bestCols = -1;
                    for(int cx = -24; cx <= 24; cx++) for(int cz = -24; cz <= 24; cz++) {
                        int cols = 0;
                        boolean folded = false;
                        for(int x = cx * 16; x < cx * 16 + 16; x += 3) for(int z = cz * 16; z < cz * 16 + 16; z += 3) {
                            double n = legacyPerlin(seed, x * 0.01D, z * 0.01D);
                            if(originalRange(n) >= 0) cols++;
                            if(n > 5 && (int) ((n - 5) * 3) > 4 && originalRange(n) >= 0) folded = true;
                        }
                        if(folded && cols > bestCols) { bestCols = cols; bestX = cx * 16; bestZ = cz * 16; }
                    }
                    check(bestCols > 0, "no chunk of seed " + seed + " within 24 chunks reaches the stratum");
                    VirtualLevel vl = new VirtualLevel(level, seed, -64);
                    Block[] mix = { Blocks.STONE, Blocks.STONE, Blocks.STONE, Blocks.GRANITE, Blocks.STONE, Blocks.DEEPSLATE, Blocks.STONE, Blocks.DIORITE, Blocks.DIRT, Blocks.STONE, Blocks.ANDESITE, Blocks.COBBLESTONE, Blocks.AIR };
                    for(int x = bestX; x < bestX + 16; x++) for(int z = bestZ; z < bestZ + 16; z++) for(int y = 18; y <= 42; y++) {
                        vl.put(new BlockPos(x, y, z), mix[Math.floorMod(x * 7 + y * 3 + z * 5, mix.length)].defaultBlockState());
                    }
                    Map<BlockPos, BlockState> before = new HashMap<>(vl.blocks);
                    boolean placedAny = NtmFeatures.SCHIST_STRATUM.get().place(new FeaturePlaceContext<>(Optional.empty(), vl.proxy, level.getChunkSource().getGenerator(),
                            RandomSource.create(1L), new BlockPos(bestX, -64, bestZ), NoneFeatureConfiguration.INSTANCE));
                    Set<BlockPos> expected = new HashSet<>();
                    int columns = 0, foldedColumns = 0, maxRange = -1;
                    for(int x = bestX; x < bestX + 16; x++) for(int z = bestZ; z < bestZ + 16; z++) {
                        double n = legacyPerlin(seed, x * 0.01D, z * 0.01D);
                        int r = originalRange(n);
                        if(r < 0) continue;
                        columns++;
                        if((int) ((n - 5) * 3) > 4) foldedColumns++;
                        maxRange = Math.max(maxRange, r);
                        for(int y = 30 - r; y <= 30 + r; y++) {
                            BlockPos p = new BlockPos(x, y, z);
                            if(before.getOrDefault(p, Blocks.AIR.defaultBlockState()).is(BlockTags.STONE_ORE_REPLACEABLES)) expected.add(p);
                        }
                    }
                    check(vl.unexpected.isEmpty(), "the stratum feature called " + vl.unexpected);
                    check(vl.writes.keySet().equals(expected), "stratum at " + bestX + "/" + bestZ + ": NEO wrote " + vl.writes.size() + ", the original loop " + expected.size()
                            + "; only NEO " + diff(vl.writes.keySet(), expected) + ", only original " + diff(expected, vl.writes.keySet()));
                    for(Map.Entry<BlockPos, BlockState> e : vl.writes.entrySet()) {
                        check(e.getValue().is(NtmBlocks.STONE_GNEISS.get()), "the stratum wrote " + e.getValue() + " at " + e.getKey());
                        check(e.getKey().getY() >= 26 && e.getKey().getY() <= 34, "the stratum wrote y " + e.getKey().getY());
                        check(before.get(e.getKey()).is(BlockTags.STONE_ORE_REPLACEABLES), "the stratum replaced " + before.get(e.getKey()));
                    }
                    check(placedAny == !expected.isEmpty() && !expected.isEmpty() && foldedColumns > 0, "stratum chunk: " + expected.size() + " blocks, " + foldedColumns + " folded columns, place returned " + placedAny);

                    // SchistStratum.java:28: only dimension 0
                    ServerLevel netherLevel = level.getServer().getLevel(Level.NETHER);
                    check(netherLevel != null, "the GameTest server has no nether level");
                    VirtualLevel vn = new VirtualLevel(netherLevel, seed, 0);
                    vn.blocks.putAll(before);
                    boolean netherPlaced = NtmFeatures.SCHIST_STRATUM.get().place(new FeaturePlaceContext<>(Optional.empty(), vn.proxy, level.getChunkSource().getGenerator(),
                            RandomSource.create(1L), new BlockPos(bestX, 0, bestZ), NoneFeatureConfiguration.INSTANCE));
                    check(!netherPlaced && vn.writes.isEmpty(), "the stratum placed " + vn.writes.size() + " blocks in the nether");
                    LOGGER.info("{} stratum: range sweep {} values; noise {} samples, max delta {}; chunk {}/{}: {} columns ({} folded, max range {}), {} schist blocks equal to the original loop; nether none",
                            TAG, sweep, samples, maxDelta, bestX, bestZ, columns, foldedColumns, maxRange, expected.size());
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "stratum"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 5. the ore layers

    /** OreLayer3D.java:94-122 on the given blocks with the region starting at (x0, z0): every block that becomes the layer block. */
    private static Set<BlockPos> simulateLayer(long seed, int layer, double scaleH, double scaleV, double threshold, int x0, int z0, Function<BlockPos, BlockState> world) {
        long sx = seed + 101 + layer, sy = seed + 102 + layer;
        double[][] cacheX = new double[16][65];
        for(int o = 0; o < 16; o++) for(int y = 64; y > 5; y--) cacheX[o][y] = legacyPerlin(sx, y * scaleV, (z0 + o) * scaleH);
        Set<BlockPos> out = new HashSet<>();
        for(int ox = 0; ox < 16; ox++) {
            int x = x0 + ox;
            for(int oz = 0; oz < 16; oz++) {
                int z = z0 + oz;
                double ny = legacyPerlin(sy, x * scaleH, z * scaleH);
                for(int y = 64; y > 5; y--) {
                    double nx = cacheX[oz][y];
                    double nz = cacheX[ox][y];
                    if(nx * ny * nz > threshold) {
                        BlockPos p = new BlockPos(x, y, z);
                        if(world.apply(p).is(BlockTags.STONE_ORE_REPLACEABLES)) out.add(p);
                    }
                }
            }
        }
        return out;
    }

    /**
     * The original onDecorate calls whose regions (grid corner + 8 .. + 23, the 1.7.10 decoration grid is the chunk grid) overlap the NEO chunk at
     * (x0, z0), restricted to that chunk: the blocks of the chunk the original turns into the layer block.
     */
    private static Set<BlockPos> originalLayerChunk(long seed, int layer, double scaleH, double scaleV, double threshold, int x0, int z0, Function<BlockPos, BlockState> world) {
        Set<BlockPos> out = new HashSet<>();
        for(int gx : new int[] { x0 - 16, x0 }) for(int gz : new int[] { z0 - 16, z0 }) {
            for(BlockPos p : simulateLayer(seed, layer, scaleH, scaleV, threshold, gx + 8, gz + 8, world)) {
                if(p.getX() >= x0 && p.getX() < x0 + 16 && p.getZ() >= z0 && p.getZ() < z0 + 16) out.add(p);
            }
        }
        return out;
    }

    // OreLayer3D.java:41-46 (id = construction counter: hematite 0, bauxite 1, malachite 2 with all three on, MainRegistry.java:602-604), :86-87 seeds
    // seed + 101 + id / + 102 + id, :94-97 cacheX[o][y] = noiseX(y * scaleV, (cz + 8 + o) * scaleH), :101-105 x = cx + 8 + ox, z = cz + 8 + oz, :107 ny = noiseY(x * scaleH,
    // z * scaleH), :109 y 64 down to 6, :110-111 nx = cacheX[oz][y], nz = cacheX[ox][y], :113 nx * ny * nz > threshold, :116-117 replace stone; MainRegistry.java:602-604 scales and
    // thresholds. The NEO chunk is covered by four original decoration regions; the expected blocks come from the original loop run on each of them.
    @GameTest(template = TEMPLATE, batch = "hbm28b_ore_layer", timeoutTicks = 200)
    public static void ore_layer(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    ChunkGenerator generator = level.getChunkSource().getGenerator();
                    check(OreLayerFeature.Y_MIN == 6 && OreLayerFeature.Y_MAX == 64, "layer y range " + OreLayerFeature.Y_MIN + ".." + OreLayerFeature.Y_MAX + ", original 6..64");
                    // the condition: strictly greater than the threshold
                    RandomSource rs = RandomSource.create(5L);
                    for(int i = 0; i < 20000; i++) {
                        double nx = (rs.nextDouble() - 0.5) * 30, ny = (rs.nextDouble() - 0.5) * 30, nz = (rs.nextDouble() - 0.5) * 30, t = rs.nextDouble() * 400;
                        check(OreLayerFeature.inLayer(nx, ny, nz, t) == (nx * ny * nz > t), "inLayer(" + nx + ", " + ny + ", " + nz + ", " + t + ")");
                    }
                    check(!OreLayerFeature.inLayer(1, 1, 230, 230) && OreLayerFeature.inLayer(1, 1, 230.5, 230) && OreLayerFeature.inLayer(-10, -10, 3, 230), "inLayer edge cases");

                    // the three configured layers
                    Registry<ConfiguredFeature<?, ?>> configured = level.registryAccess().registryOrThrow(Registries.CONFIGURED_FEATURE);
                    List<ResourceKey<ConfiguredFeature<?, ?>>> keys = List.of(NtmConfiguredFeatures.HEMATITE_LAYER, NtmConfiguredFeatures.BAUXITE_LAYER, NtmConfiguredFeatures.MALACHITE_LAYER);
                    List<Block> blocks = List.of(NtmBlocks.RESOURCE_HEMATITE.get(), NtmBlocks.RESOURCE_BAUXITE.get(), NtmBlocks.RESOURCE_MALACHITE.get());
                    double[][] params = { { 0.04, 0.25, 230 }, { 0.03, 0.15, 300 }, { 0.1, 0.15, 275 } };
                    List<OreLayerConfiguration> configs = new ArrayList<>();
                    for(int i = 0; i < 3; i++) {
                        ConfiguredFeature<?, ?> cf = configured.getOrThrow(keys.get(i));
                        check(cf.feature() == NtmFeatures.ORE_LAYER.get() && cf.config() instanceof OreLayerConfiguration, keys.get(i).location() + " is " + cf);
                        OreLayerConfiguration c = (OreLayerConfiguration) cf.config();
                        check(c.state().is(blocks.get(i)) && c.scaleH() == params[i][0] && c.scaleV() == params[i][1] && c.threshold() == params[i][2] && c.layer() == i,
                                keys.get(i).location() + " " + c + ", original " + List.of(params[i][0], params[i][1], params[i][2]) + " id " + i);
                        configs.add(c);
                    }

                    // VirtualLevel, threshold below every product: exactly the stone_ore_replaceables blocks of y 6..64 change
                    long seed = 2828L;
                    OreLayerConfiguration all = new OreLayerConfiguration(NtmBlocks.RESOURCE_HEMATITE.get().defaultBlockState(), 0.04D, 0.25D, -1.0E300D, 0);
                    VirtualLevel vl = new VirtualLevel(level, seed, -64);
                    int x0 = 160, z0 = -96;
                    Block[] mix = { Blocks.STONE, Blocks.GRANITE, Blocks.STONE, Blocks.DEEPSLATE, Blocks.STONE, Blocks.DIRT, Blocks.ANDESITE, Blocks.STONE, Blocks.NETHERRACK, Blocks.DIORITE, Blocks.AIR };
                    for(int x = x0; x < x0 + 16; x++) for(int z = z0; z < z0 + 16; z++) for(int y = 2; y <= 68; y++) vl.put(new BlockPos(x, y, z), mix[Math.floorMod(x * 5 + y * 3 + z * 7, mix.length)].defaultBlockState());
                    Map<BlockPos, BlockState> before = new HashMap<>(vl.blocks);
                    place(NtmFeatures.ORE_LAYER.get(), all, vl, generator, new BlockPos(x0, -64, z0));
                    Set<BlockPos> want = new HashSet<>();
                    for(Map.Entry<BlockPos, BlockState> e : before.entrySet()) if(e.getKey().getY() >= 6 && e.getKey().getY() <= 64 && e.getValue().is(BlockTags.STONE_ORE_REPLACEABLES)) want.add(e.getKey());
                    check(vl.unexpected.isEmpty(), "the layer feature called " + vl.unexpected);
                    check(vl.writes.keySet().equals(want), "negative threshold: wrote " + vl.writes.size() + ", expected " + want.size() + "; only NEO " + diff(vl.writes.keySet(), want) + ", missing " + diff(want, vl.writes.keySet()));
                    check(vl.writes.values().stream().allMatch(s -> s.is(NtmBlocks.RESOURCE_HEMATITE.get())), "negative threshold wrote another block");

                    // VirtualLevel, the three real layers against OreLayer3D on the same blocks (a chunk with hits is searched per layer)
                    int total = 0, gridSensitive = 0;
                    List<String> report = new ArrayList<>();
                    for(int i = 0; i < 3; i++) {
                        OreLayerConfiguration c = configs.get(i);
                        int cx = 0, cz = 0, hits = -1;
                        Function<BlockPos, BlockState> stone = p -> Blocks.STONE.defaultBlockState();
                        search:
                        for(int r = 0; r <= 8; r++) for(int a = -r; a <= r; a++) for(int b = -r; b <= r; b++) {
                            if(Math.max(Math.abs(a), Math.abs(b)) != r) continue;
                            int n = originalLayerChunk(seed, i, c.scaleH(), c.scaleV(), c.threshold(), a * 16, b * 16, stone).size();
                            if(n > 0) { cx = a * 16; cz = b * 16; hits = n; break search; }
                        }
                        VirtualLevel v = new VirtualLevel(level, seed, -64);
                        for(int x = cx; x < cx + 16; x++) for(int z = cz; z < cz + 16; z++) for(int y = 2; y <= 68; y++) v.put(new BlockPos(x, y, z), mix[Math.floorMod(x * 5 + y * 3 + z * 7, mix.length)].defaultBlockState());
                        Map<BlockPos, BlockState> start = new HashMap<>(v.blocks);
                        place(NtmFeatures.ORE_LAYER.get(), c, v, generator, new BlockPos(cx, -64, cz));
                        Set<BlockPos> expected = originalLayerChunk(seed, i, c.scaleH(), c.scaleV(), c.threshold(), cx, cz, p -> start.getOrDefault(p, Blocks.AIR.defaultBlockState()));
                        check(v.writes.keySet().equals(expected), keys.get(i).location() + " at " + cx + "/" + cz + ": NEO wrote " + v.writes.size() + ", OreLayer3D " + expected.size()
                                + "; only NEO " + diff(v.writes.keySet(), expected) + ", only original " + diff(expected, v.writes.keySet()));
                        Block layerBlock = blocks.get(i);
                        check(v.writes.values().stream().allMatch(s -> s.is(layerBlock)), keys.get(i).location() + " wrote another block");
                        // the same loop on the unshifted chunk grid gives another layout, so the comparison sees the 8-block grid shift
                        if(!simulateLayer(seed, i, c.scaleH(), c.scaleV(), c.threshold(), cx, cz, p -> start.getOrDefault(p, Blocks.AIR.defaultBlockState())).equals(expected)) gridSensitive++;
                        total += expected.size();
                        report.add(keys.get(i).location().getPath() + " chunk " + cx + "/" + cz + " " + expected.size() + " (all-stone " + hits + ")");
                    }
                    check(total > 0, "the three layers placed nothing in the searched chunks");
                    check(gridSensitive > 0, "the shifted and the unshifted grid give the same blocks in every searched chunk; the grid comparison proves nothing");
                    report.add("grid-sensitive " + gridSensitive + "/3");

                    // only the overworld (OreLayer3D.java:75, dim 0)
                    ServerLevel netherLevel = level.getServer().getLevel(Level.NETHER);
                    check(netherLevel != null, "the GameTest server has no nether level");
                    VirtualLevel vn = new VirtualLevel(netherLevel, seed, 0);
                    vn.blocks.putAll(before);
                    place(NtmFeatures.ORE_LAYER.get(), all, vn, generator, new BlockPos(x0, 0, z0));
                    check(vn.writes.isEmpty(), "the layer feature wrote " + vn.writes.size() + " blocks in the nether");

                    // the real test level inside the structure: only blocks at absolute y 6..64 may change
                    BlockPos corner = helper.absolutePos(BlockPos.ZERO);
                    Map<BlockPos, BlockState> cube = fillCube(helper, Blocks.STONE, Blocks.DEEPSLATE);
                    int inRange = 0, changed = 0;
                    try {
                        place(NtmFeatures.ORE_LAYER.get(), all, level, generator, new BlockPos(corner.getX(), level.getMinBuildHeight(), corner.getZ()));
                        for(Map.Entry<BlockPos, BlockState> e : cube.entrySet()) {
                            BlockState now = level.getBlockState(e.getKey());
                            boolean layerY = e.getKey().getY() >= 6 && e.getKey().getY() <= 64;
                            if(layerY && e.getValue().is(BlockTags.STONE_ORE_REPLACEABLES)) inRange++;
                            if(now != e.getValue()) {
                                changed++;
                                check(layerY && e.getValue().is(BlockTags.STONE_ORE_REPLACEABLES) && now.is(NtmBlocks.RESOURCE_HEMATITE.get()), "the real level changed " + e.getKey() + " from " + e.getValue() + " to " + now);
                            }
                        }
                        check(changed == inRange, "the real level changed " + changed + " blocks, " + inRange + " are layer stone at y 6..64");
                    } finally {
                        clearCube(helper);
                    }
                    LOGGER.info("{} ore_layer: negative threshold {} blocks = the y 6..64 replaceables; {}; nether none; real structure y {}..{}: {} changed ({} eligible)",
                            TAG, want.size(), report, corner.getY() + 1, corner.getY() + 11, changed, inRange);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "ore_layer"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 6. the depth deposits

    /** DepthDeposit.java:34-55 with the world bottom minY (Goal28B decision: the j < 1 / j > 126 skip counts from the bottom). */
    private static Map<BlockPos, BlockState> simulateDepth(Function<BlockPos, BlockState> world, BlockPos c, int size, double fill, BlockState ore, BlockState filler,
                                                           Predicate<BlockState> target, RandomSource rand, int minY) {
        Map<BlockPos, BlockState> out = new LinkedHashMap<>();
        for(int i = c.getX() - size; i <= c.getX() + size; i++) {
            for(int j = c.getY() - size; j <= c.getY() + size; j++) {
                for(int k = c.getZ() - size; k <= c.getZ() + size; k++) {
                    if(j < minY + 1 || j > minY + 126) continue;
                    double dx = c.getX() - i, dy = c.getY() - j, dz = c.getZ() - k;
                    // Vec3.lengthVector is MathHelper.sqrt_double, a float
                    double len = (float) Math.sqrt(dx * dx + dy * dy + dz * dz);
                    BlockPos p = new BlockPos(i, j, k);
                    BlockState t = world.apply(p);
                    if(target.test(t) || t.is(Blocks.BEDROCK)) {
                        if(len + rand.nextInt(2) < size * fill) out.put(p, ore);
                        else if(len + rand.nextInt(2) <= size) out.put(p, filler);
                    }
                }
            }
        }
        return out;
    }

    // HbmWorldGen.java:103-108 (overworld: size 5, fill 0.6 / 0.8, filler stone_depth, target stone) and :523-524 (nether neodymium: size 7, fill 0.6,
    // filler stone_depth_nether, target netherrack); DepthDeposit.java:34-55 (cube of half-size size, skip j < 1 || j > 126, the target or bedrock,
    // ore when len + rand(2) < size * fill, else filler when len + rand(2) <= size). Goal28B decisions: overworld target base_stone_overworld, the
    // y skip counted from the world bottom.
    @GameTest(template = TEMPLATE, batch = "hbm28b_depth_deposit", timeoutTicks = 200)
    public static void depth_deposit(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    ChunkGenerator generator = level.getChunkSource().getGenerator();
                    Registry<ConfiguredFeature<?, ?>> configured = level.registryAccess().registryOrThrow(Registries.CONFIGURED_FEATURE);
                    BlockState depthRock = NtmBlocks.STONE_DEPTH.get().defaultBlockState();
                    Predicate<BlockState> overworldStone = s -> s.is(BlockTags.BASE_STONE_OVERWORLD);
                    JsonElement baseStone = JsonParser.parseString("{\"predicate_type\":\"minecraft:tag_match\",\"tag\":\"minecraft:base_stone_overworld\"}");
                    for(Deposit d : deposits()) {
                        ConfiguredFeature<?, ?> cf = configured.getOrThrow(d.configured());
                        check(cf.feature() == NtmFeatures.DEPTH_DEPOSIT.get() && cf.config() instanceof DepthDepositConfiguration, d.name() + " is " + cf);
                        DepthDepositConfiguration c = (DepthDepositConfiguration) cf.config();
                        check(c.ore().is(d.ore()) && c.filler() == depthRock && c.size() == d.size() && c.fill() == d.fill() && json(c.target()).equals(baseStone),
                                d.name() + " " + c.ore() + " " + c.filler() + " size " + c.size() + " fill " + c.fill() + " target " + json(c.target()) + ", original size " + d.size() + " fill " + d.fill());
                    }
                    ConfiguredFeature<?, ?> ndf = configured.getOrThrow(NtmConfiguredFeatures.DEPTH_ORE_NETHER_NEODYMIUM);
                    DepthDepositConfiguration nc = (DepthDepositConfiguration) ndf.config();
                    check(ndf.feature() == NtmFeatures.DEPTH_DEPOSIT.get() && nc.ore().is(NtmBlocks.ORE_DEPTH_NETHER_NEODYMIUM.get()) && nc.filler().is(NtmBlocks.STONE_DEPTH_NETHER.get()) && nc.size() == 7 && nc.fill() == 0.6D
                            && json(nc.target()).equals(JsonParser.parseString("{\"predicate_type\":\"minecraft:block_match\",\"block\":\"minecraft:netherrack\"}")), "nether neodymium deposit " + nc + " " + json(nc.target()));

                    // the real test level: a stone / deepslate / bedrock / dirt cube around the centre at relative 8, 6, 8 (size 5 stays inside)
                    BlockPos rel = new BlockPos(8, 6, 8);
                    BlockPos centre = helper.absolutePos(rel);
                    check(centre.getY() - 5 > level.getMinBuildHeight() + 1 && centre.getY() + 5 < level.getMinBuildHeight() + 126, "the deposit cube reaches the y clip: centre y " + centre.getY());
                    Map<String, Double> meanOre = new LinkedHashMap<>();
                    int bedrockReplaced = 0, runs = 0;
                    try {
                        for(Deposit d : deposits()) {
                            ConfiguredFeature<?, ?> cf = configured.getOrThrow(d.configured());
                            int ores = 0;
                            for(long seed = 1; seed <= 4; seed++) {
                                Map<BlockPos, BlockState> before = depthCube(helper);
                                Map<BlockPos, BlockState> expected = simulateDepth(p -> before.getOrDefault(p, level.getBlockState(p)), centre, d.size(), d.fill(), d.ore().defaultBlockState(),
                                        depthRock, overworldStone, RandomSource.create(seed * 31L + d.chance()), level.getMinBuildHeight());
                                cf.place(level, generator, RandomSource.create(seed * 31L + d.chance()), centre);
                                Map<BlockPos, BlockState> actual = new HashMap<>();
                                for(Map.Entry<BlockPos, BlockState> e : before.entrySet()) {
                                    BlockState now = level.getBlockState(e.getKey());
                                    if(now != e.getValue()) actual.put(e.getKey(), now);
                                }
                                check(actual.equals(expected), d.name() + " seed " + seed + ": NEO changed " + actual.size() + ", DepthDeposit.generate " + expected.size()
                                        + "; only NEO " + diff(actual.keySet(), expected.keySet()) + ", only original " + diff(expected.keySet(), actual.keySet()));
                                double coreR = d.size() * d.fill();
                                for(Map.Entry<BlockPos, BlockState> e : before.entrySet()) {
                                    BlockPos p = e.getKey();
                                    double len = Math.sqrt(p.distSqr(centre));
                                    BlockState now = level.getBlockState(p);
                                    boolean eligible = e.getValue().is(BlockTags.BASE_STONE_OVERWORLD) || e.getValue().is(Blocks.BEDROCK);
                                    if(!eligible || len > d.size()) check(now == e.getValue(), d.name() + ": " + p + " (len " + len + ", " + e.getValue() + ") became " + now);
                                    if(eligible && len < coreR - 1) check(now.is(d.ore()), d.name() + ": core block at len " + len + " is " + now);
                                    if(eligible && len <= d.size() - 1) check(now.is(d.ore()) || now == depthRock, d.name() + ": inner block at len " + len + " is " + now);
                                    if(now.is(d.ore())) check(len < coreR, d.name() + ": ore at len " + len + " >= " + coreR);
                                    if(e.getValue().is(Blocks.BEDROCK) && now != e.getValue()) bedrockReplaced++;
                                    if(now.is(d.ore())) ores++;
                                }
                                runs++;
                            }
                            meanOre.put(d.name(), ores / 4.0D);
                        }
                    } finally {
                        clearCube(helper);
                    }
                    check(bedrockReplaced > 0, "no bedrock inside a deposit was replaced");
                    double low = (meanOre.get("cluster_depth_iron") + meanOre.get("cluster_depth_titanium") + meanOre.get("cluster_depth_tungsten")) / 3.0D;
                    double high = (meanOre.get("ore_depth_cinnabar") + meanOre.get("ore_depth_zirconium") + meanOre.get("ore_depth_borax")) / 3.0D;
                    check(high > low * 1.5D, "fill 0.8 deposits average " + high + " ore blocks, fill 0.6 " + low);

                    // the y clip relative to the world bottom on a VirtualLevel (the structure cannot reach the bottom)
                    DepthDepositConfiguration iron = (DepthDepositConfiguration) configured.getOrThrow(NtmConfiguredFeatures.DEPTH_CLUSTER_IRON).config();
                    List<String> clips = new ArrayList<>();
                    int[][] cases = { { -64, -64 }, { -64, -63 }, { -64, -62 }, { -64, 60 }, { 0, 1 }, { 0, 126 }, { 0, 125 } };
                    for(int[] cs : cases) {
                        int minY = cs[0], cy = cs[1];
                        boolean netherCase = minY == 0;
                        DepthDepositConfiguration c = netherCase ? nc : iron;
                        VirtualLevel v = new VirtualLevel(netherCase ? level.getServer().getLevel(Level.NETHER) : level, 1L, minY);
                        BlockPos cpos = new BlockPos(40, cy, 40);
                        for(int x = 40 - c.size(); x <= 40 + c.size(); x++) for(int z = 40 - c.size(); z <= 40 + c.size(); z++) for(int y = cy - c.size(); y <= cy + c.size(); y++) {
                            Block b = y == minY ? Blocks.BEDROCK : netherCase ? Blocks.NETHERRACK : (y < 0 ? Blocks.DEEPSLATE : Blocks.STONE);
                            v.put(new BlockPos(x, y, z), b.defaultBlockState());
                        }
                        Map<BlockPos, BlockState> start = new HashMap<>(v.blocks);
                        Predicate<BlockState> tgt = netherCase ? s -> s.is(Blocks.NETHERRACK) : overworldStone;
                        Map<BlockPos, BlockState> expected = simulateDepth(p -> start.getOrDefault(p, Blocks.AIR.defaultBlockState()), cpos, c.size(), c.fill(), c.ore(), c.filler(), tgt, RandomSource.create(77L), minY);
                        place(NtmFeatures.DEPTH_DEPOSIT.get(), c, v, generator, cpos, RandomSource.create(77L));
                        check(v.unexpected.isEmpty(), "the deposit feature called " + v.unexpected);
                        check(v.writes.equals(expected), "clip case bottom " + minY + " centre y " + cy + ": NEO wrote " + v.writes.size() + ", original " + expected.size()
                                + "; only NEO " + diff(v.writes.keySet(), expected.keySet()) + ", only original " + diff(expected.keySet(), v.writes.keySet()));
                        int lo = Integer.MAX_VALUE, hi = Integer.MIN_VALUE;
                        for(BlockPos p : v.writes.keySet()) { lo = Math.min(lo, p.getY()); hi = Math.max(hi, p.getY()); }
                        check(v.writes.isEmpty() || (lo >= minY + 1 && hi <= minY + 126), "clip case " + minY + "/" + cy + " wrote y " + lo + ".." + hi);
                        check(!v.writes.containsKey(new BlockPos(40, minY, 40)), "clip case " + minY + "/" + cy + " replaced the bottom bedrock");
                        clips.add(minY + "/" + cy + ": " + v.writes.size() + " y " + (v.writes.isEmpty() ? "-" : lo + ".." + hi));
                    }
                    LOGGER.info("{} depth_deposit: {} real placements equal to DepthDeposit.generate; mean ore {}; bedrock replaced {}; clip {}", TAG, runs, meanOre, bedrockReplaced, clips);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "depth_deposit"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 7. the schist ores, clusters and alexandrite

    // HbmWorldGen.java:110-117 WorldGenMinable(ore, amount, stone_gneiss), :136-139 and :99 WorldGenMinable(ore, amount, stone): the vanilla ore feature
    // stands in for WorldGenMinable, so only the target, the ore and the size are the original's. Goal28B decision: the stone target is
    // stone_ore_replaceables.
    @GameTest(template = TEMPLATE, batch = "hbm28b_schist_ores", timeoutTicks = 200)
    public static void schist_ores(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    ChunkGenerator generator = level.getChunkSource().getGenerator();
                    Registry<ConfiguredFeature<?, ?>> configured = level.registryAccess().registryOrThrow(Registries.CONFIGURED_FEATURE);
                    BlockPos origin = helper.absolutePos(new BlockPos(8, 6, 8));
                    Block gneiss = NtmBlocks.STONE_GNEISS.get();
                    List<Vein> all = new ArrayList<>(veins());
                    all.add(new Vein("alexandrite", NtmConfiguredFeatures.ORE_ALEXANDRITE, NtmPlacedFeatures.ORE_ALEXANDRITE_PLACED, NtmBlocks.ORE_ALEXANDRITE.get(), false, "alexandriteSpawnRate", 100, 3, 10, 5));
                    List<String> report = new ArrayList<>();
                    try {
                        for(Vein v : all) {
                            ConfiguredFeature<?, ?> cf = configured.getOrThrow(v.configured());
                            check(cf.config() instanceof OreConfiguration, v.name() + " is not an ore feature: " + cf.config());
                            OreConfiguration oc = (OreConfiguration) cf.config();
                            check(oc.size == v.size(), v.name() + " vein size " + oc.size + ", original " + v.size());
                            check(oc.targetStates.size() == 1 && oc.targetStates.get(0).state.is(v.ore()), v.name() + " targets " + oc.targetStates.size());
                            RuleTest target = oc.targetStates.get(0).target;
                            RandomSource rt = RandomSource.create(1L);
                            if(v.schist()) {
                                check(target.test(gneiss.defaultBlockState(), rt) && !target.test(Blocks.STONE.defaultBlockState(), rt) && !target.test(Blocks.DEEPSLATE.defaultBlockState(), rt),
                                        v.name() + " target " + json(target) + " is not stone_gneiss only");
                            } else {
                                check(json(target).equals(JsonParser.parseString("{\"predicate_type\":\"minecraft:tag_match\",\"tag\":\"minecraft:stone_ore_replaceables\"}")), v.name() + " target " + json(target));
                                check(target.test(Blocks.STONE.defaultBlockState(), rt) && !target.test(gneiss.defaultBlockState(), rt), v.name() + " target");
                            }
                            // real placement: a cube of the own target and a cube of the other block
                            Block own = v.schist() ? gneiss : Blocks.STONE, other = v.schist() ? Blocks.STONE : gneiss;
                            List<Integer> perSeed = new ArrayList<>();
                            for(Block base : List.of(own, other)) {
                                Map<BlockPos, BlockState> before = fillCube(helper, base, base == gneiss ? Blocks.STONE : gneiss);
                                int total = 0;
                                // a size-3 vein (alexandrite) often places nothing in 1.21 OreFeature as in WorldGenMinable, so it gets more seeds
                                int seeds = v.size() <= 3 ? 32 : 4;
                                for(long seed = 1; seed <= seeds; seed++) {
                                    cf.place(level, generator, RandomSource.create(seed * 7919L + v.size()), origin);
                                    List<BlockPos> changed = new ArrayList<>();
                                    for(Map.Entry<BlockPos, BlockState> e : before.entrySet()) {
                                        BlockState now = level.getBlockState(e.getKey());
                                        if(now == e.getValue()) continue;
                                        check(e.getValue().is(own) && now.is(v.ore()), v.name() + ": replaced " + e.getValue() + " at " + e.getKey() + " with " + now);
                                        changed.add(e.getKey());
                                    }
                                    if(base == own) perSeed.add(changed.size());
                                    total += changed.size();
                                    for(BlockPos p : changed) level.setBlock(p, before.get(p), 2 | 16);
                                }
                                if(base == own) check(total > 0, v.name() + ": " + seeds + " placements in " + own + " put no ore down");
                                // the mix inside the other cube is the own target and may take ore; the other block itself never
                                clearCube(helper);
                            }
                            report.add(v.name() + " " + v.size() + ":" + perSeed);
                        }
                    } finally {
                        clearCube(helper);
                    }
                    LOGGER.info("{} schist_ores: placed per seed {}", TAG, report);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "schist_ores"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 8. depth rock and the block properties

    // BlockDepth.java:18-22 (setBlockUnbreakable, setResistance 10), :25-33 (1/50 when the held item is an IDepthRockTool whose canBreakRock is true,
    // else the unbreakable default), :37-39 (tooltip trait.tile.depth in yellow); ModBlocks.java:1271-1281 schist hardness 1.5 resistance 10, :1253-1256
    // clusters hardness 5 resistance 15, :1274-1277 BlockOutgas(rock, true, 5, true) for the schist uranium (both) and asbestos ores; BlockOutgas.java:41-44
    // radon for the schist uranium ores, :57-61 asbestos gas for the schist asbestos ore
    @GameTest(template = TEMPLATE, batch = "hbm28b_depth_rock", timeoutTicks = 100)
    public static void depth_rock(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    BlockPos rel = new BlockPos(4, 2, 4);
                    BlockPos abs = helper.absolutePos(rel);
                    Item breaker = NtmItems.BISMUTH_PICKAXE.get(), plainAbility = NtmItems.STARMETAL_PICKAXE.get();
                    check(breaker instanceof ToolAbilityItem t && t.canBreakRock(level, helper.makeMockPlayer(GameType.SURVIVAL), new ItemStack(breaker), NtmBlocks.STONE_DEPTH.get(), abs),
                            "bismuth_pickaxe is not a depth rock breaker");
                    check(plainAbility instanceof ToolAbilityItem t2 && !t2.canBreakRock(level, helper.makeMockPlayer(GameType.SURVIVAL), new ItemStack(plainAbility), NtmBlocks.STONE_DEPTH.get(), abs),
                            "starmetal_pickaxe breaks depth rock");
                    TagKey<Block>[] needs = List.of(BlockTags.NEEDS_STONE_TOOL, BlockTags.NEEDS_IRON_TOOL, BlockTags.NEEDS_DIAMOND_TOOL).toArray(TagKey[]::new);
                    for(Block b : depthBlocks()) {
                        check(b instanceof DepthBlock, BuiltInRegistries.BLOCK.getKey(b) + " is " + b.getClass().getSimpleName());
                        helper.setBlock(rel, b);
                        BlockState state = level.getBlockState(abs);
                        check(state.getDestroySpeed(level, abs) == -1.0F, BuiltInRegistries.BLOCK.getKey(b) + " destroy speed " + state.getDestroySpeed(level, abs));
                        check(b.getExplosionResistance() == 10.0F, BuiltInRegistries.BLOCK.getKey(b) + " resistance " + b.getExplosionResistance());
                        float withTool = progress(helper, state, abs, new ItemStack(breaker), ItemStack.EMPTY);
                        check(withTool == 1.0F / 50.0F, BuiltInRegistries.BLOCK.getKey(b) + " with bismuth_pickaxe: " + withTool + " per tick, original 1/50");
                        check(progress(helper, state, abs, new ItemStack(plainAbility), ItemStack.EMPTY) == 0.0F, BuiltInRegistries.BLOCK.getKey(b) + " breaks with a non-breaker ability tool");
                        check(progress(helper, state, abs, new ItemStack(Items.DIAMOND_PICKAXE), ItemStack.EMPTY) == 0.0F, BuiltInRegistries.BLOCK.getKey(b) + " breaks with a diamond pickaxe");
                        check(progress(helper, state, abs, ItemStack.EMPTY, ItemStack.EMPTY) == 0.0F, BuiltInRegistries.BLOCK.getKey(b) + " breaks by hand");
                        // getHeldItem is the main hand only
                        check(progress(helper, state, abs, ItemStack.EMPTY, new ItemStack(breaker)) == 0.0F, BuiltInRegistries.BLOCK.getKey(b) + " breaks with the breaker in the off hand");
                        List<Component> lines = new ArrayList<>();
                        b.appendHoverText(new ItemStack(b), Item.TooltipContext.of(level), lines, TooltipFlag.NORMAL);
                        check(lines.size() == 1 && lines.get(0).getContents() instanceof TranslatableContents tc && tc.getKey().equals("trait.tile.depth")
                                && lines.get(0).getStyle().getColor() != null && lines.get(0).getStyle().getColor().equals(net.minecraft.network.chat.TextColor.fromLegacyFormat(ChatFormatting.YELLOW)),
                                BuiltInRegistries.BLOCK.getKey(b) + " tooltip " + lines);
                        check(state.is(BlockTags.MINEABLE_WITH_PICKAXE), BuiltInRegistries.BLOCK.getKey(b) + " is not pickaxe-mineable");
                        for(TagKey<Block> t : needs) check(!state.is(t), BuiltInRegistries.BLOCK.getKey(b) + " is in " + t.location());
                    }
                    helper.setBlock(rel, Blocks.AIR);
                    // an ordinary block is unaffected by the breaker rule
                    helper.setBlock(rel, Blocks.STONE);
                    check(progress(helper, level.getBlockState(abs), abs, new ItemStack(breaker), ItemStack.EMPTY) != 1.0F / 50.0F, "stone mines at the depth rock rate");
                    helper.setBlock(rel, Blocks.AIR);

                    // the schist block and ores, the clusters
                    List<Block> schist = List.of(NtmBlocks.STONE_GNEISS.get(), NtmBlocks.ORE_GNEISS_IRON.get(), NtmBlocks.ORE_GNEISS_GOLD.get(), NtmBlocks.ORE_GNEISS_COPPER.get(), NtmBlocks.ORE_GNEISS_ASBESTOS.get(),
                            NtmBlocks.ORE_GNEISS_LITHIUM.get(), NtmBlocks.ORE_GNEISS_RARE.get(), NtmBlocks.ORE_GNEISS_GAS.get(), NtmBlocks.ORE_GNEISS_URANIUM.get(), NtmBlocks.ORE_GNEISS_URANIUM_SCORCHED.get());
                    for(Block b : schist) {
                        check(b.defaultBlockState().getDestroySpeed(level, BlockPos.ZERO) == 1.5F && b.getExplosionResistance() == 10.0F, BuiltInRegistries.BLOCK.getKey(b) + " hardness / resistance "
                                + b.defaultBlockState().getDestroySpeed(level, BlockPos.ZERO) + " / " + b.getExplosionResistance());
                        check(b.defaultBlockState().is(BlockTags.MINEABLE_WITH_PICKAXE), BuiltInRegistries.BLOCK.getKey(b) + " is not pickaxe-mineable");
                    }
                    for(Block b : List.of(NtmBlocks.CLUSTER_IRON.get(), NtmBlocks.CLUSTER_TITANIUM.get(), NtmBlocks.CLUSTER_ALUMINIUM.get(), NtmBlocks.CLUSTER_COPPER.get())) {
                        check(b.defaultBlockState().getDestroySpeed(level, BlockPos.ZERO) == 5.0F && b.getExplosionResistance() == 15.0F, BuiltInRegistries.BLOCK.getKey(b) + " hardness / resistance");
                        check(b.defaultBlockState().is(BlockTags.MINEABLE_WITH_PICKAXE), BuiltInRegistries.BLOCK.getKey(b) + " is not pickaxe-mineable");
                    }

                    // outgassing: the schist uranium ores and the schist asbestos ore
                    Block radon = NtmBlocks.GAS_RADON.get(), asbestos = NtmBlocks.GAS_ASBESTOS.get();
                    int col = 0;
                    Player player = helper.makeMockPlayer(GameType.SURVIVAL);
                    player.setItemInHand(InteractionHand.MAIN_HAND, new ItemStack(Items.IRON_PICKAXE));
                    for(Object[] row : new Object[][] { { NtmBlocks.ORE_GNEISS_URANIUM.get(), radon }, { NtmBlocks.ORE_GNEISS_URANIUM_SCORCHED.get(), radon }, { NtmBlocks.ORE_GNEISS_ASBESTOS.get(), asbestos } }) {
                        Block ore = (Block) row[0], gas = (Block) row[1];
                        check(ore instanceof OutgasBlock og && og.getGas().is(gas), BuiltInRegistries.BLOCK.getKey(ore) + " gas " + (ore instanceof OutgasBlock og2 ? og2.getGas() : "not outgassing"));
                        check(ore.defaultBlockState().isRandomlyTicking(), BuiltInRegistries.BLOCK.getKey(ore) + " does not tick randomly");
                        BlockPos r = new BlockPos(3 + 5 * col++, 4, 4);
                        for(long seed = 0; seed < 4; seed++) {
                            clearAround(helper, r);
                            helper.setBlock(r, ore);
                            helper.getBlockState(r).randomTick(level, helper.absolutePos(r), RandomSource.create(seed));
                            int n = 0, other = 0;
                            for(Direction d : Direction.values()) {
                                BlockState s = helper.getBlockState(r.relative(d));
                                if(s.is(gas)) n++;
                                else if(!s.isAir()) other++;
                            }
                            check(n == 1 && other == 0, BuiltInRegistries.BLOCK.getKey(ore) + " random tick seed " + seed + ": " + n + " gas neighbours, " + other + " other");
                        }
                        clearAround(helper, r);
                        BlockPos b = new BlockPos(r.getX(), 2, 11);
                        helper.setBlock(b, ore);
                        playerBreak(helper, player, b);
                        check(helper.getBlockState(b).is(gas), BuiltInRegistries.BLOCK.getKey(ore) + " broken by a player left " + helper.getBlockState(b));
                        helper.setBlock(b, Blocks.AIR);
                    }
                    discardItems(helper);
                    LOGGER.info("{} depth_rock: 10 depth blocks unbreakable, 1/50 with a depth rock breaker only, tooltip trait.tile.depth; schist / cluster properties; schist uranium radon, schist asbestos asbestos", TAG);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "depth_rock"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 9. loot

    // BlockDepthOre.java:15-38 drops, :46-55 quantityDropped (cinnabar 2 + rand(3), zirconium / neodymium 2 + rand(2), else 1), :60-63 bonus
    // quantity * (max(rand(fortune + 2) - 1, 0) + 1), alexandrite capped at 2; BlockCluster.java:19-28 one crystal (plain Block quantity, no fortune);
    // BlockOre.java:84-88 schist rare earth -> chunk_ore (NEO rare_earth_ore_chunk), schist asbestos -> ingot_asbestos; BlockResourceStone.java:33-41
    // malachite 3 + fortune + rand(fortune + 2) chunks (Goal28B decision: 3..4 plus NEO's ore bonus); BlockGeneric / BlockDepth drop themselves
    @GameTest(template = TEMPLATE, batch = "hbm28b_loot", timeoutTicks = 100)
    public static void loot(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    HolderLookup.RegistryLookup<Enchantment> ench = helper.getLevel().registryAccess().lookupOrThrow(Registries.ENCHANTMENT);
                    ItemStack plain = new ItemStack(Items.IRON_PICKAXE);
                    ItemStack fortune = new ItemStack(Items.IRON_PICKAXE);
                    fortune.enchant(ench.getOrThrow(Enchantments.FORTUNE), 3);
                    BlockPos rel = new BlockPos(4, 1, 4);

                    // self drops
                    for(Block b : List.of(NtmBlocks.STONE_GNEISS.get(), NtmBlocks.ORE_GNEISS_IRON.get(), NtmBlocks.ORE_GNEISS_GOLD.get(), NtmBlocks.ORE_GNEISS_COPPER.get(),
                            NtmBlocks.ORE_GNEISS_LITHIUM.get(), NtmBlocks.ORE_GNEISS_GAS.get(), NtmBlocks.STONE_DEPTH.get(), NtmBlocks.STONE_DEPTH_NETHER.get())) {
                        for(ItemStack tool : List.of(plain, fortune)) {
                            Map<Item, Integer> d = roll(helper, rel, b, tool);
                            check(d.size() == 1 && d.getOrDefault(b.asItem(), 0) == 1, BuiltInRegistries.BLOCK.getKey(b) + " dropped " + d);
                        }
                    }
                    // the depth ores: item, base range, fortune bonus
                    Object[][] depth = {
                            { NtmBlocks.CLUSTER_DEPTH_IRON.get(), NtmItems.CRYSTAL_IRON.get(), 1, 1 }, { NtmBlocks.CLUSTER_DEPTH_TITANIUM.get(), NtmItems.CRYSTAL_TITANIUM.get(), 1, 1 },
                            { NtmBlocks.CLUSTER_DEPTH_TUNGSTEN.get(), NtmItems.CRYSTAL_TUNGSTEN.get(), 1, 1 }, { NtmBlocks.ORE_DEPTH_CINNABAR.get(), NtmItems.CINNABAR.get(), 2, 4 },
                            { NtmBlocks.ORE_DEPTH_ZIRCONIUM.get(), NtmItems.NUGGET_ZIRCONIUM.get(), 2, 3 }, { NtmBlocks.ORE_DEPTH_NETHER_NEODYMIUM.get(), NtmItems.FRAGMENT_NEODYMIUM.get(), 2, 3 },
                            { NtmBlocks.ORE_DEPTH_BORAX.get(), NtmItems.POWDER_BORAX.get(), 1, 1 } };
                    List<String> report = new ArrayList<>();
                    for(Object[] row : depth) {
                        Block b = (Block) row[0];
                        Item item = (Item) row[1];
                        int lo = (Integer) row[2], hi = (Integer) row[3];
                        int[] base = range(helper, rel, b, plain, item, 600);
                        check(base[0] == lo && base[1] == hi, BuiltInRegistries.BLOCK.getKey(b) + " dropped " + base[0] + ".." + base[1] + ", original " + lo + ".." + hi);
                        int[] f = range(helper, rel, b, fortune, item, 800);
                        // fortune III: x 1..4
                        check(f[0] >= lo && f[1] > hi && f[1] <= hi * 4, BuiltInRegistries.BLOCK.getKey(b) + " with fortune III dropped " + f[0] + ".." + f[1] + ", original " + lo + ".." + hi * 4);
                        report.add(BuiltInRegistries.BLOCK.getKey(b).getPath() + " " + base[0] + ".." + base[1] + " f3 " + f[0] + ".." + f[1]);
                    }
                    // alexandrite: one gem, the bonus capped at 2 (fortune III: P(quantity >= 2) = 3/5)
                    int[] alex = range(helper, rel, NtmBlocks.ORE_ALEXANDRITE.get(), plain, NtmItems.GEM_ALEXANDRITE.get(), 300);
                    check(alex[0] == 1 && alex[1] == 1, "alexandrite dropped " + alex[0] + ".." + alex[1]);
                    int twos = 0, rolls = 1000;
                    for(int i = 0; i < rolls; i++) {
                        Map<Item, Integer> d = roll(helper, rel, NtmBlocks.ORE_ALEXANDRITE.get(), fortune);
                        int c = d.getOrDefault(NtmItems.GEM_ALEXANDRITE.get(), 0);
                        check(d.size() == 1 && (c == 1 || c == 2), "alexandrite with fortune III dropped " + d);
                        if(c == 2) twos++;
                    }
                    // Binomial(1000, 0.6): mean 600, sd 15.5
                    check(twos >= 530 && twos <= 670, "alexandrite with fortune III: " + twos + " of " + rolls + " rolls dropped 2, original 3 in 5");
                    // explosions (BlockDepthOre.java:43-64 through the 1.7.10 Block.dropBlockAsItemWithChance: each dropped item is its own stack and
                    // survives with chance 1 / explosion size; NEO decision: the vanilla explosion_decay function, which keeps each item of the stack
                    // with chance 1 / radius). Depth rock drops itself and survives as a whole (survives_explosion), like every dropSelf table
                    List<Block> depthOres = new ArrayList<>();
                    for(Object[] row : depth) depthOres.add((Block) row[0]);
                    depthOres.add(NtmBlocks.ORE_ALEXANDRITE.get());
                    for(Block b : depthOres) {
                        String table = lootJson(helper, b);
                        check(table.contains("\"minecraft:explosion_decay\""), BuiltInRegistries.BLOCK.getKey(b) + " loot has no explosion_decay: " + table);
                        check(table.contains("minecraft:silk_touch"), BuiltInRegistries.BLOCK.getKey(b) + " loot lost its silk touch branch: " + table);
                    }
                    for(Block b : List.of(NtmBlocks.STONE_DEPTH.get(), NtmBlocks.STONE_DEPTH_NETHER.get())) {
                        String table = lootJson(helper, b);
                        check(table.contains("\"minecraft:survives_explosion\"") && !table.contains("explosion_decay"), BuiltInRegistries.BLOCK.getKey(b) + " loot " + table);
                    }
                    // radius 4: a one-item drop survives 1 time in 4; 2000 rolls, Binomial(2000, 0.25): mean 500, sd 19.4
                    int kept = 0, blasts = 2000;
                    for(int i = 0; i < blasts; i++) {
                        Map<Item, Integer> d = rollExplosion(helper, rel, NtmBlocks.CLUSTER_DEPTH_IRON.get(), plain, 4.0F);
                        int c = d.getOrDefault(NtmItems.CRYSTAL_IRON.get(), 0);
                        check(d.size() <= 1 && c <= 1, "cluster_depth_iron in a blast dropped " + d);
                        kept += c;
                    }
                    check(kept >= 420 && kept <= 580, "cluster_depth_iron: " + kept + " of " + blasts + " crystals survived a radius-4 blast, original 1 in 4");
                    // cinnabar 2..4 per break: each item kept with 1/4, mean 0.75 items per blast; 2000 blasts sum 1500, sd about 34
                    int cinnabar = 0;
                    for(int i = 0; i < blasts; i++) cinnabar += rollExplosion(helper, rel, NtmBlocks.ORE_DEPTH_CINNABAR.get(), plain, 4.0F).getOrDefault(NtmItems.CINNABAR.get(), 0);
                    check(cinnabar >= 1330 && cinnabar <= 1670, "ore_depth_cinnabar: " + cinnabar + " cinnabar survived " + blasts + " radius-4 blasts, original about 1500 (3 x 1/4 each)");
                    // radius 1 keeps everything; depth rock survives a radius-4 blast as a whole stack or not at all
                    for(int i = 0; i < 100; i++) {
                        int c = rollExplosion(helper, rel, NtmBlocks.ORE_DEPTH_ZIRCONIUM.get(), plain, 1.0F).getOrDefault(NtmItems.NUGGET_ZIRCONIUM.get(), 0);
                        check(c >= 2 && c <= 3, "ore_depth_zirconium in a radius-1 blast dropped " + c);
                    }
                    int rock = 0;
                    for(int i = 0; i < blasts; i++) rock += rollExplosion(helper, rel, NtmBlocks.STONE_DEPTH.get(), plain, 4.0F).getOrDefault(NtmBlocks.STONE_DEPTH.get().asItem(), 0);
                    check(rock >= 420 && rock <= 580, "stone_depth: " + rock + " of " + blasts + " survived a radius-4 blast");
                    report.add("blast r4: crystal " + kept + "/" + blasts + ", cinnabar " + cinnabar + ", depth rock " + rock);

                    // clusters: one crystal, no fortune bonus
                    Object[][] clusters = { { NtmBlocks.CLUSTER_IRON.get(), NtmItems.CRYSTAL_IRON.get() }, { NtmBlocks.CLUSTER_TITANIUM.get(), NtmItems.CRYSTAL_TITANIUM.get() },
                            { NtmBlocks.CLUSTER_ALUMINIUM.get(), NtmItems.CRYSTAL_ALUMINIUM.get() }, { NtmBlocks.CLUSTER_COPPER.get(), NtmItems.CRYSTAL_COPPER.get() } };
                    for(Object[] row : clusters) {
                        for(ItemStack tool : List.of(plain, fortune)) {
                            int[] c = range(helper, rel, (Block) row[0], tool, (Item) row[1], 200);
                            check(c[0] == 1 && c[1] == 1, BuiltInRegistries.BLOCK.getKey((Block) row[0]) + " dropped " + c[0] + ".." + c[1] + " with " + tool);
                        }
                    }
                    // schist rare earth as ore_rare, schist asbestos an asbestos ingot
                    int[] rare = range(helper, rel, NtmBlocks.ORE_GNEISS_RARE.get(), plain, NtmItems.RARE_EARTH_ORE_CHUNK.get(), 200);
                    int[] rareBase = range(helper, rel, NtmBlocks.ORE_RARE.get(), plain, NtmItems.RARE_EARTH_ORE_CHUNK.get(), 200);
                    check(rare[0] == 1 && rare[1] == 1 && rareBase[0] == rare[0] && rareBase[1] == rare[1], "schist rare earth dropped " + rare[0] + ".." + rare[1] + ", ore_rare " + rareBase[0] + ".." + rareBase[1]);
                    int[] rareF = range(helper, rel, NtmBlocks.ORE_GNEISS_RARE.get(), fortune, NtmItems.RARE_EARTH_ORE_CHUNK.get(), 400);
                    check(rareF[1] > 1 && rareF[1] <= 4, "schist rare earth with fortune III dropped up to " + rareF[1]);
                    int[] asb = range(helper, rel, NtmBlocks.ORE_GNEISS_ASBESTOS.get(), plain, NtmItems.INGOT_ASBESTOS.get(), 200);
                    check(asb[0] == 1 && asb[1] == 1, "schist asbestos dropped " + asb[0] + ".." + asb[1] + " asbestos ingots");
                    // malachite 3..4, more with fortune III; hematite and bauxite themselves
                    int[] mal = range(helper, rel, NtmBlocks.RESOURCE_MALACHITE.get(), plain, NtmItems.CHUNK_MALACHITE.get(), 400);
                    check(mal[0] == 3 && mal[1] == 4, "malachite dropped " + mal[0] + ".." + mal[1] + " chunks, original 3..4 without fortune");
                    int[] malF = range(helper, rel, NtmBlocks.RESOURCE_MALACHITE.get(), fortune, NtmItems.CHUNK_MALACHITE.get(), 400);
                    check(malF[0] >= 3 && malF[1] > 4, "malachite with fortune III dropped " + malF[0] + ".." + malF[1] + ", original 6..10 (NEO ore bonus)");
                    for(Block b : List.of(NtmBlocks.RESOURCE_HEMATITE.get(), NtmBlocks.RESOURCE_BAUXITE.get())) {
                        Map<Item, Integer> d = roll(helper, rel, b, plain);
                        check(d.size() == 1 && d.getOrDefault(b.asItem(), 0) == 1, BuiltInRegistries.BLOCK.getKey(b) + " dropped " + d);
                    }
                    LOGGER.info("{} loot: depth {}; alexandrite f3 {} of {} doubles; malachite {}..{} (f3 {}..{}); schist rare {}..{} (f3 max {})", TAG, report, twos, rolls, mal[0], mal[1], malF[0], malF[1], rare[0], rare[1], rareF[1]);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "loot"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 10. processing

    // SmeltingRecipes.java:54-55,58-60 (schist iron / gold -> vanilla ingots, copper -> ingot_copper, lithium -> lithium, schrabidium -> ingot_schrabidium;
    // Goal28B decisions: the vanilla copper ingot, NEO's 0.7 experience); ShredderRecipes.java:176 (stone_gneiss -> 1 powder_lithium_tiny), :66 ore -> 2 dust
    // with OreDictManager.java:336-337,380,424,454 (schist iron / gold / copper / asbestos / lithium in the ore entries); NEO's desh mix row for ore_rare;
    // CrystallizerRecipes.java:62-63,73 (IRON / GOLD / CU ore, two-argument form :315 peroxide 500), :80 LI.ore sulfuric, :86 oreRareEarth sulfuric, :105
    // stone_gneiss -> powder_lithium utilityTime 100 prod 0.25 peroxide; CentrifugeRecipes.java:66-76,108-112 (IRON / GOLD / CU ore rows, lbs off);
    // FluidContainerRegistry.java:45 (ore_gneiss_gas, no empty container, petroleum gas 250, 50 with 528)
    @GameTest(template = TEMPLATE, batch = "hbm28b_processing", timeoutTicks = 100)
    public static void processing(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    smelts(helper, NtmBlocks.ORE_GNEISS_IRON.get(), Items.IRON_INGOT);
                    smelts(helper, NtmBlocks.ORE_GNEISS_GOLD.get(), Items.GOLD_INGOT);
                    smelts(helper, NtmBlocks.ORE_GNEISS_COPPER.get(), Items.COPPER_INGOT);
                    smelts(helper, NtmBlocks.ORE_GNEISS_LITHIUM.get(), NtmItems.LITHIUM.get());
                    smelts(helper, NtmBlocks.ORE_GNEISS_SCHRABIDIUM.get(), NtmItems.INGOT_SCHRABIDIUM.get());

                    // shredder
                    shreds(NtmBlocks.STONE_GNEISS.get(), NtmItems.POWDER_LITHIUM_TINY.get(), 1);
                    shreds(NtmBlocks.ORE_GNEISS_LITHIUM.get(), NtmItems.POWDER_LITHIUM.get(), 2);
                    shreds(NtmBlocks.ORE_GNEISS_IRON.get(), NtmItems.POWDER_IRON.get(), 2);
                    shreds(NtmBlocks.ORE_GNEISS_GOLD.get(), NtmItems.POWDER_GOLD.get(), 2);
                    shreds(NtmBlocks.ORE_GNEISS_COPPER.get(), NtmItems.POWDER_COPPER.get(), 2);
                    shreds(NtmBlocks.ORE_GNEISS_ASBESTOS.get(), NtmItems.POWDER_ASBESTOS.get(), 2);
                    // :193 the desh mix row names ore_rare only, and the ore dictionary has no rare earth dust (getDustByName :374-383 gives scrap)
                    ItemStack rareResult = ShredderRecipes.getShredderResult(new ItemStack(NtmBlocks.ORE_RARE.get()));
                    check(rareResult.is(NtmItems.POWDER_DESH_MIX.get()), "ore_rare shreds to " + rareResult);
                    // the depth ores by their ore dictionary entries (OreDictManager.java:438 oreBorax, :473-474 oreZirconium / oreNeodymium) and the ore rule
                    // (:66, 2 of the matching dust)
                    shreds(NtmBlocks.ORE_DEPTH_BORAX.get(), NtmItems.POWDER_BORAX.get(), 2);
                    shreds(NtmBlocks.ORE_DEPTH_ZIRCONIUM.get(), NtmItems.POWDER_ZIRCONIUM.get(), 2);
                    shreds(NtmBlocks.ORE_DEPTH_NETHER_NEODYMIUM.get(), NtmItems.POWDER_NEODYMIUM.get(), 2);
                    // without a row: schist rare earth (no rare earth dust), depth cinnabar (CINNABAR has no dust, OreDictManager.java:437), and in no
                    // original ore dictionary entry and without an explicit row: gas shale, alexandrite, the clusters, the depth clusters, depth rock
                    for(Block b : List.of(NtmBlocks.ORE_GNEISS_RARE.get(), NtmBlocks.ORE_DEPTH_CINNABAR.get(), NtmBlocks.ORE_GNEISS_GAS.get(), NtmBlocks.ORE_ALEXANDRITE.get(),
                            NtmBlocks.CLUSTER_IRON.get(), NtmBlocks.CLUSTER_TITANIUM.get(), NtmBlocks.CLUSTER_ALUMINIUM.get(), NtmBlocks.CLUSTER_COPPER.get(),
                            NtmBlocks.CLUSTER_DEPTH_IRON.get(), NtmBlocks.CLUSTER_DEPTH_TITANIUM.get(), NtmBlocks.CLUSTER_DEPTH_TUNGSTEN.get(),
                            NtmBlocks.STONE_DEPTH.get(), NtmBlocks.STONE_DEPTH_NETHER.get())) {
                        check(!ShredderRecipes.hasRecipe(new ItemStack(b)), BuiltInRegistries.BLOCK.getKey(b) + " has a shredder row: " + ShredderRecipes.getShredderResult(new ItemStack(b)));
                    }

                    // acidizer (live and default tables)
                    crystallizes(NtmBlocks.STONE_GNEISS.get(), Fluids.PEROXIDE, NtmItems.POWDER_LITHIUM.get(), 100, 0.25F);
                    crystallizes(NtmBlocks.ORE_GNEISS_IRON.get(), Fluids.PEROXIDE, NtmItems.CRYSTAL_IRON.get(), 600, 0.05F);
                    crystallizes(NtmBlocks.ORE_GNEISS_GOLD.get(), Fluids.PEROXIDE, NtmItems.CRYSTAL_GOLD.get(), 600, 0.05F);
                    crystallizes(NtmBlocks.ORE_GNEISS_COPPER.get(), Fluids.PEROXIDE, NtmItems.CRYSTAL_COPPER.get(), 600, 0.05F);
                    crystallizes(NtmBlocks.ORE_GNEISS_RARE.get(), Fluids.SULFURIC_ACID, NtmItems.CRYSTAL_RARE.get(), 600, 0.05F);
                    crystallizes(NtmBlocks.ORE_GNEISS_LITHIUM.get(), Fluids.SULFURIC_ACID, NtmItems.CRYSTAL_LITHIUM.get(), 600, 0.05F);
                    check(CrystallizerRecipes.getOutput(new ItemStack(NtmBlocks.ORE_GNEISS_LITHIUM.get()), Fluids.PEROXIDE) == null, "schist lithium crystallizes with peroxide");
                    check(CrystallizerRecipes.getOutput(new ItemStack(NtmBlocks.ORE_GNEISS_IRON.get()), Fluids.SULFURIC_ACID) == null, "schist iron crystallizes with sulfuric acid");
                    // :87 the oreCinnabar row with OreDictManager.java:437 ore_depth_cinnebar
                    crystallizes(NtmBlocks.ORE_DEPTH_CINNABAR.get(), Fluids.PEROXIDE, NtmItems.CRYSTAL_CINNABAR.get(), 600, 0.05F);
                    check(CrystallizerRecipes.getOutput(new ItemStack(NtmBlocks.ORE_DEPTH_CINNABAR.get()), Fluids.SULFURIC_ACID) == null, "depth cinnabar crystallizes with sulfuric acid");
                    for(Block b : List.of(NtmBlocks.ORE_DEPTH_BORAX.get(), NtmBlocks.ORE_DEPTH_ZIRCONIUM.get(), NtmBlocks.ORE_DEPTH_NETHER_NEODYMIUM.get(), NtmBlocks.ORE_GNEISS_GAS.get(), NtmBlocks.ORE_ALEXANDRITE.get())) {
                        for(FluidType acid : List.of(Fluids.PEROXIDE, Fluids.SULFURIC_ACID)) {
                            check(CrystallizerRecipes.getOutput(new ItemStack(b), acid) == null, BuiltInRegistries.BLOCK.getKey(b) + " has an acidizer row with " + acid.getInternalName());
                        }
                    }
                    List<CrystallizerRecipe> defaults = CrystallizerRecipes.getDefaultRecipes();
                    check(defaults.size() == 65, "the default acidizer table has " + defaults.size() + " rows, expected 65 (53 + 7 + 5)");
                    check(CrystallizerRecipes.getJeiRecipes().size() == 65, "the live acidizer table has " + CrystallizerRecipes.getJeiRecipes().size() + " rows, expected 65");
                    // the seven rows are appended after the Goal28A rows, in this order
                    List<ItemLike> appended = List.of(NtmBlocks.STONE_GNEISS.get(), NtmBlocks.ORE_GNEISS_IRON.get(), NtmBlocks.ORE_GNEISS_GOLD.get(), NtmBlocks.ORE_GNEISS_COPPER.get(),
                            NtmBlocks.ORE_GNEISS_RARE.get(), NtmBlocks.ORE_GNEISS_LITHIUM.get(), NtmBlocks.ORE_DEPTH_CINNABAR.get());
                    for(int i = 0; i < appended.size(); i++) {
                        CrystallizerRecipe row = defaults.get(53 + i);
                        check(row.input instanceof com.hbm.inventory.RecipesCommon.ComparableStack cs && cs.item == appended.get(i).asItem(), "acidizer row " + (53 + i) + " input " + row.input + ", expected " + appended.get(i).asItem());
                    }

                    // centrifuge: the schist members of IRON / GOLD / CU ore; first three outputs the original's, the fourth as NEO's vanilla ore rows
                    Object[][] rows = { { NtmBlocks.ORE_GNEISS_IRON.get(), Blocks.IRON_ORE, List.of(s(NtmItems.POWDER_IRON.get(), 1), s(NtmItems.POWDER_IRON.get(), 1), s(NtmItems.POWDER_IRON.get(), 1)) },
                            { NtmBlocks.ORE_GNEISS_GOLD.get(), Blocks.GOLD_ORE, List.of(s(NtmItems.POWDER_GOLD.get(), 1), s(NtmItems.POWDER_GOLD.get(), 1), s(NtmItems.POWDER_GOLD.get(), 1)) },
                            { NtmBlocks.ORE_GNEISS_COPPER.get(), Blocks.COPPER_ORE, List.of(s(NtmItems.POWDER_COPPER.get(), 1), s(NtmItems.POWDER_COPPER.get(), 1), s(NtmItems.POWDER_GOLD.get(), 1)) } };
                    for(Object[] row : rows) {
                        ItemStack[] got = CentrifugeRecipes.getOutput(new ItemStack((Block) row[0]));
                        ItemStack[] vanilla = CentrifugeRecipes.getOutput(new ItemStack((Block) row[1]));
                        @SuppressWarnings("unchecked") List<ItemStack> first = (List<ItemStack>) row[2];
                        boolean ok = got.length == 4 && vanilla.length == 4;
                        for(int i = 0; ok && i < 3; i++) ok = got[i].is(first.get(i).getItem()) && got[i].getCount() == first.get(i).getCount();
                        for(int i = 0; ok && i < 4; i++) ok = ItemStack.matches(got[i], vanilla[i]);
                        check(ok, BuiltInRegistries.BLOCK.getKey((Block) row[0]) + " centrifuges to " + List.of(got) + ", vanilla row " + List.of(vanilla) + ", original first three " + first);
                    }
                    for(Block b : List.of(NtmBlocks.ORE_GNEISS_RARE.get(), NtmBlocks.ORE_GNEISS_LITHIUM.get(), NtmBlocks.ORE_GNEISS_ASBESTOS.get(), NtmBlocks.ORE_GNEISS_GAS.get())) {
                        check(CentrifugeRecipes.getOutput(new ItemStack(b)).length == 0, BuiltInRegistries.BLOCK.getKey(b) + " has a centrifuge row");
                    }
                    check(CentrifugeRecipes.getOutput(new ItemStack(NtmBlocks.ORE_RARE.get())).length == 0, "ore_rare has a centrifuge row now; the schist rare row decision no longer holds");
                    check(CentrifugeRecipes.getJeiRecipes().size() == 83 && CentrifugeRecipes.getDefaultRecipes().size() == 83, "the centrifuge table has " + CentrifugeRecipes.getJeiRecipes().size() + " / "
                            + CentrifugeRecipes.getDefaultRecipes().size() + " rows, expected 83 (80 + 3)");

                    // gas shale holds petroleum gas and leaves nothing behind
                    ItemStack shale = new ItemStack(NtmBlocks.ORE_GNEISS_GAS.get());
                    int want = NtmConfig.enable528() ? 50 : 250;
                    check(!NtmConfig.enable528(), "the test server runs with 528 on");
                    check(FluidContainerRegistry.getFluidContent(shale, Fluids.PETROLEUM) == want, "gas shale holds " + FluidContainerRegistry.getFluidContent(shale, Fluids.PETROLEUM) + " mB petroleum gas, original " + want);
                    check(FluidContainerRegistry.getEmptyContainer(shale).isEmpty(), "gas shale empties to " + FluidContainerRegistry.getEmptyContainer(shale));
                    int found = 0;
                    for(FluidContainer c : FluidContainerRegistry.allContainers) {
                        if(c.fullContainer.is(shale.getItem())) {
                            found++;
                            check(c.emptyContainer.isEmpty() && c.type == Fluids.PETROLEUM && c.content == want, "gas shale container " + c.type.getInternalName() + " " + c.content + " empty " + c.emptyContainer);
                        }
                    }
                    check(found == 1, "gas shale is registered " + found + " times");
                    for(FluidType other : List.of(Fluids.OIL, Fluids.GAS, Fluids.WATER)) check(FluidContainerRegistry.getFluidContent(shale, other) == 0, "gas shale holds " + other.getInternalName());
                    LOGGER.info("{} processing: smelting 5 (0.7 xp), shredder (3 depth ore rows), acidizer 60 rows, centrifuge 83 rows, gas shale {} mB petroleum gas", TAG, want);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "processing"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 11. gas shale in the fluid burner

    // ContainerOilburner.java:22 (slot 0 a plain Slot) with FluidContainerRegistry.java:45 (gas shale: petroleum gas 250, no empty container) and the
    // burner's tank loading (TileEntityHeaterOilburner.java:71 tank.loadTank(0, 1, slots)): a gas shale block in slot 0 puts 250 mB of petroleum gas
    // into a petroleum gas tank and leaves nothing in slot 1. NEO decision: slot 0 takes only items that are containers of some fluid with an empty
    // container, full containers of the tank's own fluid and infinite fluid items.
    @GameTest(template = TEMPLATE, batch = "hbm28b_gas_shale_burner", timeoutTicks = 100)
    public static void gas_shale_burner(GameTestHelper helper) {
        BlockPos core = new BlockPos(5, 1, 5);
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.HEATER_OILBURNER.get(), core, Direction.NORTH);
        ItemStack shale = new ItemStack(NtmBlocks.ORE_GNEISS_GAS.get());
        helper.startSequence()
                .thenIdle(2)
                .thenExecute(guard(() -> {
                    HeaterOilburnerBlockEntity be = SmokeTestSupport.blockEntity(helper, core, HeaterOilburnerBlockEntity.class);
                    check(be.tank.getTankType() == Fluids.HEATINGOIL, "a fresh burner tank holds " + be.tank.getTankType().getInternalName());
                    // a heating oil tank: gas shale is no container of heating oil
                    check(!be.canPlaceItem(0, shale), "slot 0 of a heating oil burner accepts gas shale");
                    be.isOn = false;
                    be.tank.setTankType(Fluids.PETROLEUM);
                    be.tank.setFill(0);
                    check(be.canPlaceItem(0, shale), "slot 0 of a petroleum gas burner refuses gas shale");
                    check(!be.canPlaceItem(0, new ItemStack(Items.STONE)) && !be.canPlaceItem(0, new ItemStack(NtmBlocks.STONE_GNEISS.get())), "slot 0 accepts a block that holds no fluid");
                    // the empty containers stay accepted
                    check(be.canPlaceItem(0, new ItemStack(Items.BUCKET)) || be.canPlaceItem(0, new ItemStack(Items.WATER_BUCKET)), "slot 0 refuses buckets");
                    be.slots.set(0, shale.copy());
                    be.slots.set(1, ItemStack.EMPTY);
                }))
                .thenIdle(1)
                .thenExecute(guard(() -> {
                    HeaterOilburnerBlockEntity be = SmokeTestSupport.blockEntity(helper, core, HeaterOilburnerBlockEntity.class);
                    int want = NtmConfig.enable528() ? 50 : 250;
                    check(be.tank.getTankType() == Fluids.PETROLEUM && be.tank.getFill() == want, "after a tick the tank holds " + be.tank.getFill() + " mB " + be.tank.getTankType().getInternalName() + ", expected " + want + " mB petroleum gas");
                    check(be.slots.get(0).isEmpty() && be.slots.get(1).isEmpty(), "after loading: slot 0 " + be.slots.get(0) + ", slot 1 " + be.slots.get(1) + "; expected both empty");
                    LOGGER.info("{} gas_shale_burner: refused by a heating oil tank, accepted by a petroleum gas tank, loaded {} mB, nothing left behind", TAG, be.tank.getFill());
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "gas_shale_burner"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- VirtualLevel

    /**
     * An in-memory WorldGenLevel for the feature code paths that need a seed, a world bottom or heights the test structure cannot hold. It answers
     * getLevel (the given server level, for the dimension check), getSeed, getBlockState (air where unset), setBlock (recorded), getMinBuildHeight,
     * getHeight and ensureCanWrite; any other call is recorded in {@link #unexpected} and fails.
     */
    private static final class VirtualLevel implements InvocationHandler {
        final ServerLevel level;
        final long seed;
        final int minY;
        final Map<BlockPos, BlockState> blocks = new HashMap<>();
        final Map<BlockPos, BlockState> writes = new LinkedHashMap<>();
        final Set<String> unexpected = new TreeSet<>();
        final WorldGenLevel proxy;

        VirtualLevel(ServerLevel level, long seed, int minY) {
            this.level = level;
            this.seed = seed;
            this.minY = minY;
            this.proxy = (WorldGenLevel) Proxy.newProxyInstance(OverworldWorldgenGameTests.class.getClassLoader(), new Class<?>[] { WorldGenLevel.class }, this);
        }

        void put(BlockPos pos, BlockState state) {
            this.blocks.put(pos.immutable(), state);
        }

        @Override
        public Object invoke(Object self, Method method, Object[] args) {
            switch(method.getName()) {
                case "getLevel": return this.level;
                case "getSeed": return this.seed;
                case "getBlockState": return this.blocks.getOrDefault(((BlockPos) args[0]).immutable(), Blocks.AIR.defaultBlockState());
                case "setBlock":
                    if(args != null && args.length >= 3 && args[0] instanceof BlockPos pos && args[1] instanceof BlockState state) {
                        BlockPos p = pos.immutable();
                        this.blocks.put(p, state);
                        this.writes.put(p, state);
                        return true;
                    }
                    break;
                case "getMinBuildHeight": return this.minY;
                case "getHeight": return 384;
                case "ensureCanWrite": return true;
                case "hashCode": return System.identityHashCode(self);
                case "equals": return self == args[0];
                case "toString": return "VirtualLevel(" + this.level.dimension().location() + ", seed " + this.seed + ", bottom " + this.minY + ")";
                default: break;
            }
            this.unexpected.add(method.getName());
            throw new UnsupportedOperationException("VirtualLevel." + method.getName());
        }
    }

    @SuppressWarnings("unchecked")
    private static <FC extends net.minecraft.world.level.levelgen.feature.configurations.FeatureConfiguration> boolean place(Feature<FC> feature, FC config, WorldGenLevel level, ChunkGenerator generator, BlockPos origin, RandomSource random) {
        return feature.place(new FeaturePlaceContext<>(Optional.empty(), level, generator, random, origin, config));
    }

    private static <FC extends net.minecraft.world.level.levelgen.feature.configurations.FeatureConfiguration> boolean place(Feature<FC> feature, FC config, VirtualLevel level, ChunkGenerator generator, BlockPos origin, RandomSource random) {
        return place(feature, config, level.proxy, generator, origin, random);
    }

    private static <FC extends net.minecraft.world.level.levelgen.feature.configurations.FeatureConfiguration> boolean place(Feature<FC> feature, FC config, VirtualLevel level, ChunkGenerator generator, BlockPos origin) {
        return place(feature, config, level.proxy, generator, origin, RandomSource.create(1L));
    }

    private static <FC extends net.minecraft.world.level.levelgen.feature.configurations.FeatureConfiguration> boolean place(Feature<FC> feature, FC config, ServerLevel level, ChunkGenerator generator, BlockPos origin) {
        return place(feature, config, (WorldGenLevel) level, generator, origin, RandomSource.create(1L));
    }

    // ---------------------------------------------------------------- the 1.7.10 noise

    private static final Map<Long, SimplexNoise[]> LEGACY_OCTAVES = new HashMap<>();

    /** 1.7.10 NoiseGeneratorPerlin(new Random(seed), 4).func_151601_a(x, z): four simplex octaves built in order, sum of noise_i(x / 2^i, z / 2^i) * 2^i. */
    private static double legacyPerlin(long seed, double x, double z) {
        SimplexNoise[] octaves = LEGACY_OCTAVES.computeIfAbsent(seed, s -> {
            RandomSource random = new LegacyRandomSource(s);
            SimplexNoise[] out = new SimplexNoise[4];
            for(int i = 0; i < 4; i++) out[i] = new SimplexNoise(random);
            return out;
        });
        double sum = 0.0D, f = 1.0D;
        for(int i = 0; i < 4; i++) {
            sum += octaves[i].getValue(x * f, z * f) / f;
            f /= 2.0D;
        }
        return sum;
    }

    // ---------------------------------------------------------------- helpers

    private static ResourceLocation id(String path) {
        return ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path);
    }

    private static String describe(Object o) {
        return o == null ? "null" : o.getClass().getSimpleName();
    }

    private static ConfigGatedAddFeaturesBiomeModifier gated(Registry<BiomeModifier> modifiers, ResourceKey<BiomeModifier> key) {
        BiomeModifier m = modifiers.get(key);
        check(m instanceof ConfigGatedAddFeaturesBiomeModifier, key.location() + " decodes to " + describe(m));
        return (ConfigGatedAddFeaturesBiomeModifier) m;
    }

    private static JsonElement json(PlacementModifier modifier) {
        return PlacementModifier.CODEC.encodeStart(JsonOps.INSTANCE, modifier).result().orElseThrow();
    }

    private static JsonElement json(RuleTest test) {
        return RuleTest.CODEC.encodeStart(JsonOps.INSTANCE, test).result().orElseThrow();
    }

    private static int[] sampleY(PlacementContext ctx, RandomSource random, BlockPos origin, PlacementModifier height, int n) {
        int lo = Integer.MAX_VALUE, hi = Integer.MIN_VALUE;
        for(int i = 0; i < n; i++) {
            for(BlockPos p : height.getPositions(ctx, random, origin).toList()) {
                lo = Math.min(lo, p.getY());
                hi = Math.max(hi, p.getY());
            }
        }
        return new int[] { lo, hi };
    }

    private static boolean isTag(HolderSet<Biome> set, TagKey<Biome> tag) {
        return set.unwrapKey().map(tag::equals).orElse(false);
    }

    private static List<String> keys(HolderSet<PlacedFeature> set) {
        List<String> out = new ArrayList<>();
        for(Holder<PlacedFeature> h : set) out.add(h.unwrapKey().map(k -> k.location().toString()).orElse("<direct>"));
        return out;
    }

    private static List<String> names(List<ResourceKey<PlacedFeature>> keys) {
        List<String> out = new ArrayList<>();
        for(ResourceKey<PlacedFeature> k : keys) out.add(k.location().toString());
        return out;
    }

    private static Holder<Biome> biome(GameTestHelper helper, ResourceKey<Biome> key) {
        return helper.getLevel().registryAccess().registryOrThrow(Registries.BIOME).getHolderOrThrow(key);
    }

    private static boolean inStep(Holder<Biome> biome, GenerationStep.Decoration step, ResourceKey<PlacedFeature> key) {
        List<HolderSet<PlacedFeature>> features = biome.value().getGenerationSettings().features();
        if(step.ordinal() >= features.size()) return false;
        for(Holder<PlacedFeature> h : features.get(step.ordinal())) if(h.is(key)) return true;
        return false;
    }

    private static boolean inAnyStep(Holder<Biome> biome, ResourceKey<PlacedFeature> key) {
        for(HolderSet<PlacedFeature> set : biome.value().getGenerationSettings().features()) for(Holder<PlacedFeature> h : set) if(h.is(key)) return true;
        return false;
    }

    /** The placed features the modifier adds to a fresh copy of the biome's original info in the given phase, by key (step suffix outside underground_ores). */
    private static List<String> added(BiomeModifier modifier, Holder<Biome> biome, BiomeModifier.Phase phase) {
        ModifiableBiomeInfo.BiomeInfo.Builder builder = ModifiableBiomeInfo.BiomeInfo.Builder.copyOf(biome.value().modifiableBiomeInfo().getOriginalBiomeInfo());
        Map<GenerationStep.Decoration, List<Holder<PlacedFeature>>> before = new HashMap<>();
        for(GenerationStep.Decoration step : GenerationStep.Decoration.values()) before.put(step, new ArrayList<>(builder.getGenerationSettings().getFeatures(step)));
        modifier.modify(biome, phase, builder);
        List<String> out = new ArrayList<>();
        for(GenerationStep.Decoration step : GenerationStep.Decoration.values()) {
            List<Holder<PlacedFeature>> now = builder.getGenerationSettings().getFeatures(step);
            List<Holder<PlacedFeature>> was = before.get(step);
            if(now.size() < was.size()) out.add("<removed in " + step + ">");
            for(int i = was.size(); i < now.size(); i++) {
                String key = now.get(i).unwrapKey().map(k -> k.location().toString()).orElse("<direct>");
                out.add(step == GenerationStep.Decoration.UNDERGROUND_ORES ? key : key + "@" + step);
            }
        }
        return out;
    }

    /** Fills relative x 1..15, y 1..11, z 1..15 with the base and a sprinkle of another block; returns the absolute positions and states. */
    private static Map<BlockPos, BlockState> fillCube(GameTestHelper helper, Block base, Block mix) {
        Map<BlockPos, BlockState> states = new HashMap<>();
        for(int x = 1; x <= 15; x++) for(int y = 1; y <= 11; y++) for(int z = 1; z <= 15; z++) {
            Block b = (x * 7 + y * 3 + z * 5) % 11 == 0 ? mix : base;
            BlockPos abs = helper.absolutePos(new BlockPos(x, y, z));
            helper.getLevel().setBlock(abs, b.defaultBlockState(), 2 | 16);
            states.put(abs, b.defaultBlockState());
        }
        return states;
    }

    /** The deposit cube: stone above relative y 6, deepslate below, bedrock and dirt sprinkled in. */
    private static Map<BlockPos, BlockState> depthCube(GameTestHelper helper) {
        Map<BlockPos, BlockState> states = new HashMap<>();
        for(int x = 1; x <= 15; x++) for(int y = 1; y <= 11; y++) for(int z = 1; z <= 15; z++) {
            int h = x * 7 + y * 3 + z * 5;
            Block b = h % 13 == 0 ? Blocks.BEDROCK : h % 17 == 0 ? Blocks.DIRT : h % 19 == 0 ? Blocks.NETHERRACK : y < 6 ? Blocks.DEEPSLATE : (h % 5 == 0 ? Blocks.GRANITE : Blocks.STONE);
            BlockPos abs = helper.absolutePos(new BlockPos(x, y, z));
            helper.getLevel().setBlock(abs, b.defaultBlockState(), 2 | 16);
            states.put(abs, b.defaultBlockState());
        }
        return states;
    }

    private static void clearCube(GameTestHelper helper) {
        for(int x = 1; x <= 15; x++) for(int y = 1; y <= 11; y++) for(int z = 1; z <= 15; z++) {
            helper.getLevel().setBlock(helper.absolutePos(new BlockPos(x, y, z)), Blocks.AIR.defaultBlockState(), 2 | 16);
        }
    }

    private static <T> Set<T> diff(Set<T> a, Set<T> b) {
        Set<T> out = new HashSet<>(a);
        out.removeAll(b);
        return out.size() > 8 ? new HashSet<>(new ArrayList<>(out).subList(0, 8)) : out;
    }

    private static void clearAround(GameTestHelper helper, BlockPos rel) {
        helper.setBlock(rel, Blocks.AIR);
        for(Direction d : Direction.values()) helper.setBlock(rel.relative(d), Blocks.AIR);
    }

    private static float progress(GameTestHelper helper, BlockState state, BlockPos abs, ItemStack main, ItemStack off) {
        Player player = helper.makeMockPlayer(GameType.SURVIVAL);
        player.setItemInHand(InteractionHand.MAIN_HAND, main.copy());
        player.setItemInHand(InteractionHand.OFF_HAND, off.copy());
        return state.getDestroyProgress(player, helper.getLevel(), abs);
    }

    /** The survival steps of ServerPlayerGameMode.destroyBlock for a mock player. */
    private static void playerBreak(GameTestHelper helper, Player player, BlockPos rel) {
        ServerLevel level = helper.getLevel();
        BlockPos abs = helper.absolutePos(rel);
        BlockState original = level.getBlockState(abs);
        BlockEntity be = level.getBlockEntity(abs);
        BlockState state = original.getBlock().playerWillDestroy(level, abs, original, player);
        ItemStack tool = player.getMainHandItem().copy();
        boolean removed = state.onDestroyedByPlayer(level, abs, player, true, level.getFluidState(abs));
        if(removed) state.getBlock().destroy(level, abs, state);
        check(removed, "the mock player could not remove " + original);
        state.getBlock().playerDestroy(level, player, abs, state, be, tool);
    }

    private static Map<Item, Integer> roll(GameTestHelper helper, BlockPos rel, Block block, ItemStack tool) {
        BlockPos abs = helper.absolutePos(rel);
        LootParams.Builder params = new LootParams.Builder(helper.getLevel())
                .withParameter(LootContextParams.ORIGIN, Vec3.atCenterOf(abs))
                .withParameter(LootContextParams.TOOL, tool);
        Map<Item, Integer> out = new HashMap<>();
        for(ItemStack s : block.defaultBlockState().getDrops(params)) out.merge(s.getItem(), s.getCount(), Integer::sum);
        return out;
    }

    /** One roll of the block's loot as an explosion of the given radius breaks it (the LootContextParams.EXPLOSION_RADIUS of Block.onExplosionHit). */
    private static Map<Item, Integer> rollExplosion(GameTestHelper helper, BlockPos rel, Block block, ItemStack tool, float radius) {
        BlockPos abs = helper.absolutePos(rel);
        LootParams.Builder params = new LootParams.Builder(helper.getLevel())
                .withParameter(LootContextParams.ORIGIN, Vec3.atCenterOf(abs))
                .withParameter(LootContextParams.TOOL, tool)
                .withParameter(LootContextParams.EXPLOSION_RADIUS, radius);
        Map<Item, Integer> out = new HashMap<>();
        for(ItemStack s : block.defaultBlockState().getDrops(params)) out.merge(s.getItem(), s.getCount(), Integer::sum);
        return out;
    }

    /** The block's loot table as the server decoded it, encoded back to JSON. */
    private static String lootJson(GameTestHelper helper, Block block) {
        ServerLevel level = helper.getLevel();
        LootTable table = level.getServer().reloadableRegistries().getLootTable(block.getLootTable());
        check(table != LootTable.EMPTY, BuiltInRegistries.BLOCK.getKey(block) + " has no loot table");
        return LootTable.DIRECT_CODEC.encodeStart(level.registryAccess().createSerializationContext(JsonOps.INSTANCE), table).getOrThrow().toString();
    }

    /** Min and max count of {@code item} over {@code n} rolls; every roll must drop that item only. */
    private static int[] range(GameTestHelper helper, BlockPos rel, Block block, ItemStack tool, Item item, int n) {
        int lo = Integer.MAX_VALUE, hi = Integer.MIN_VALUE;
        for(int i = 0; i < n; i++) {
            Map<Item, Integer> d = roll(helper, rel, block, tool);
            check(d.size() == 1 && d.containsKey(item), BuiltInRegistries.BLOCK.getKey(block) + " dropped " + d + ", expected only " + BuiltInRegistries.ITEM.getKey(item));
            lo = Math.min(lo, d.get(item));
            hi = Math.max(hi, d.get(item));
        }
        return new int[] { lo, hi };
    }

    private static ItemStack s(ItemLike item, int count) {
        return new ItemStack(item, count);
    }

    private static void smelts(GameTestHelper helper, ItemLike in, ItemLike out) {
        ServerLevel level = helper.getLevel();
        SingleRecipeInput input = new SingleRecipeInput(new ItemStack(in));
        Optional<RecipeHolder<SmeltingRecipe>> holder = level.getRecipeManager().getRecipeFor(RecipeType.SMELTING, input, level);
        check(holder.isPresent(), in.asItem() + ": no smelting recipe");
        check(holder.get().id().getNamespace().equals(NuclearTechMod.MODID), in.asItem() + ": smelting recipe " + holder.get().id());
        ItemStack result = holder.get().value().assemble(input, level.registryAccess());
        check(result.is(out.asItem()) && result.getCount() == 1, in.asItem() + " smelts to " + result + ", original " + out.asItem());
        check(holder.get().value().getExperience() == 0.7F, in.asItem() + " smelting experience " + holder.get().value().getExperience() + ", NEO 0.7");
    }

    private static void shreds(ItemLike in, Item out, int count) {
        ItemStack stack = new ItemStack(in);
        check(ShredderRecipes.hasRecipe(stack), BuiltInRegistries.ITEM.getKey(in.asItem()) + " has no shredder row");
        ItemStack result = ShredderRecipes.getShredderResult(stack);
        check(result.is(out) && result.getCount() == count, BuiltInRegistries.ITEM.getKey(in.asItem()) + " shreds to " + result + ", expected " + count + " x " + BuiltInRegistries.ITEM.getKey(out));
    }

    private static void crystallizes(ItemLike in, FluidType acid, Item out, int duration, float productivity) {
        String label = BuiltInRegistries.ITEM.getKey(in.asItem()).toString();
        for(List<CrystallizerRecipe> table : List.of(CrystallizerRecipes.getJeiRecipes(), CrystallizerRecipes.getDefaultRecipes())) {
            CrystallizerRecipe r = CrystallizerRecipes.getOutput(table, new ItemStack(in), acid);
            check(r != null, label + " has no acidizer row with " + acid.getInternalName());
            check(r.output.is(out) && r.output.getCount() == 1, label + " crystallizes to " + r.output);
            check(r.acidAmount() == 500 && r.itemAmount() == 1, label + " consumes " + r.itemAmount() + " item(s) and " + r.acidAmount() + " mB, original 1 and 500");
            check(r.duration == duration && r.productivity == productivity, label + " duration " + r.duration + " productivity " + r.productivity + ", original " + duration + " / " + productivity);
        }
    }

    private static void discardItems(GameTestHelper helper) {
        Vec3 abs = helper.absoluteVec(new Vec3(8.5, 1, 8.5));
        for(ItemEntity entity : helper.getLevel().getEntitiesOfClass(ItemEntity.class, new AABB(abs, abs).inflate(10D))) entity.discard();
    }
}
