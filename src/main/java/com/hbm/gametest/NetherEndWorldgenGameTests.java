package com.hbm.gametest;

import api.hbm.block.IToolable;
import api.hbm.block.IToolable.ToolType;
import com.hbm.blockentity.machine.FoundryOutletBlockEntity;
import com.hbm.blockentity.machine.heater.HeaterOilburnerBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.generic.NetherCoalBlock;
import com.hbm.blocks.generic.OutgasBlock;
import com.hbm.blocks.generic.SmolderBlock;
import com.hbm.blocks.machine.FoundryOutletBlock;
import com.hbm.config.NtmConfig;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.material.Mats;
import com.hbm.inventory.recipes.AssemblyMachineRecipes;
import com.hbm.inventory.recipes.CentrifugeRecipes;
import com.hbm.inventory.recipes.CrystallizerRecipes;
import com.hbm.inventory.recipes.CrystallizerRecipes.CrystallizerRecipe;
import com.hbm.inventory.recipes.ShredderRecipes;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.items.CopperScrapsItem;
import com.hbm.items.NtmItems;
import com.hbm.main.NuclearTechMod;
import com.hbm.world.gen.ConfigCountPlacement;
import com.hbm.world.gen.ConfigGatedAddFeaturesBiomeModifier;
import com.hbm.world.gen.NtmBiomeModifiers;
import com.hbm.world.gen.NtmConfiguredFeatures;
import com.hbm.world.gen.NtmPlacedFeatures;
import com.google.gson.stream.JsonWriter;
import com.mojang.logging.LogUtils;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.Holder;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.HolderSet;
import net.minecraft.core.NonNullList;
import net.minecraft.core.Registry;
import net.minecraft.core.RegistryAccess;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.contents.TranslatableContents;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.BiomeTags;
import net.minecraft.tags.ItemTags;
import net.minecraft.tags.TagKey;
import net.minecraft.util.RandomSource;
import net.minecraft.world.ContainerHelper;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.ItemInteractionResult;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.animal.Pig;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.item.crafting.CraftingInput;
import net.minecraft.world.item.crafting.CraftingRecipe;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.item.crafting.SingleRecipeInput;
import net.minecraft.world.item.crafting.SmeltingRecipe;
import net.minecraft.world.item.enchantment.Enchantment;
import net.minecraft.world.item.enchantment.Enchantments;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.ItemLike;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.biome.Biomes;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.GenerationStep;
import net.minecraft.world.level.levelgen.feature.ConfiguredFeature;
import net.minecraft.world.level.levelgen.feature.configurations.OreConfiguration;
import net.minecraft.world.level.levelgen.placement.BiomeFilter;
import net.minecraft.world.level.levelgen.placement.HeightRangePlacement;
import net.minecraft.world.level.levelgen.placement.InSquarePlacement;
import net.minecraft.world.level.levelgen.placement.PlacedFeature;
import net.minecraft.world.level.levelgen.placement.PlacementContext;
import net.minecraft.world.level.levelgen.placement.PlacementModifier;
import net.minecraft.world.level.storage.loot.LootParams;
import net.minecraft.world.level.storage.loot.parameters.LootContextParams;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.common.ModConfigSpec;
import net.neoforged.neoforge.common.world.BiomeModifier;
import net.neoforged.neoforge.common.world.BiomeModifiers.AddFeaturesBiomeModifier;
import net.neoforged.neoforge.common.world.ModifiableBiomeInfo;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import net.neoforged.neoforge.registries.NeoForgeRegistries;
import org.slf4j.Logger;

import java.io.StringWriter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal28A: nether and end ore generation behind the CommonConfig worldgen switches (the config-gated biome modifier
 * and the config count placement), the six new nether blocks and their outgassing, ignition, loot and processing rows, the hand drill, the
 * fluid burner's 4f5924e2b adaptation (GUI slider control, overdrive upgrade, 500,000 TU base capacity, no screwdriver), the
 * GenericRecipe icon fix and the dropped scraps entity name. Same template and conventions as {@link FoundryChannelGameTests}; every test
 * has its own batch.
 * <p>
 * Expected values come from the ORIGINAL at 4f5924e2b, cited beside each group of checks (HbmWorldGen.java:501-551; DungeonToolbox.java:65-83;
 * WorldConfig.java:123-125,183-191; GeneralConfig.java:18,99; ModBlocks.java:1258-1267,1335; BlockOre.java:55-122; BlockNetherCoal.java:22-29;
 * BlockSmolder.java:33-41; BlockOutgas.java:40-115; SmeltingRecipes.java:33-46; CentrifugeRecipes.java:102-106,138-142,192-202;
 * ShredderRecipes.java:150,199; CrystallizerRecipes.java:71,74,81,89-90,104,314-316; FuelHandler.java:41; ToolRecipes.java:141-142;
 * ModItems.java:3711-3712; ItemTooling.java:26-41; FoundryOutlet.java:123-169; TileEntityHeaterOilburner.java:42-81,160-216;
 * GenericRecipe.java:103-108), not from the NEO implementation. NEO-only expectations (the Goal28A decisions: the slider's server clamp
 * and the "setting" key, slot 3 accepting only overdrive upgrades, the scraps entity name, the smoldering feature as a plain modifier) are
 * marked as such.
 * <p>
 * Real classes and state: the biome modifiers, placed and configured features decoded by the running server from the generated JSON and
 * read from its registries; the biomes' generation settings after the server applied the modifiers; real ConfiguredFeature.place on the
 * server level with fixed seeds; real block random ticks, loot tables, RecipeManager, the HBM recipe tables, the burner ticked by its own
 * ticker. Stand-ins: config switches and counts are changed with ModConfigSpec.ConfigValue.set and restored in finally; the gated modifier's
 * modify() is called on a fresh BiomeInfo.Builder copied from the biome's original info (the server applies modifiers once at start);
 * the smoldering feature runs on a block lattice built above the test structure (absolute y 8..115, removed afterwards) and is compared with
 * a re-implementation of the original loop on the same seed; the player break runs the survival steps of ServerPlayerGameMode.destroyBlock
 * (playerWillDestroy, onDestroyedByPlayer, playerDestroy) for a mock player; item use runs Item.useOn with a mock player.
 * Not evidence: a real client (models, particles, the GUI slider as drawn), a dedicated server with real players, real chunk generation in
 * the nether and the end, saved worlds and 1.7.10 itself.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class NetherEndWorldgenGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-28a]";

    /** One original generateOre call (HbmWorldGen.java:504-512, :550): config count key and its default, vein size, min height, variance. */
    private record Vein(String name, ResourceKey<ConfiguredFeature<?, ?>> configured, ResourceKey<PlacedFeature> placed, Block ore, Block target,
                        String countKey, int defaultCount, int size, int minHeight, int variance) {
        int maxY() { return minHeight + variance - 1; }
    }

    // HbmWorldGen.java:504-509 (inside if(WorldConfig.netherOre)), :511-512 (plutonium, also behind GeneralConfig.enablePlutoniumOre), :550 (end);
    // counts are the WorldConfig defaults (WorldConfig.java:183-191); DungeonToolbox.java:82 y = minHeight + rand(variance)
    private static List<Vein> veins() {
        return List.of(
                new Vein("uranium", NtmConfiguredFeatures.ORE_NETHER_URANIUM, NtmPlacedFeatures.ORE_NETHER_URANIUM_PLACED, NtmBlocks.ORE_NETHER_URANIUM.get(), Blocks.NETHERRACK, "netherUraniumSpawnRate", 8, 6, 0, 127),
                new Vein("tungsten", NtmConfiguredFeatures.ORE_NETHER_TUNGSTEN, NtmPlacedFeatures.ORE_NETHER_TUNGSTEN_PLACED, NtmBlocks.ORE_NETHER_TUNGSTEN.get(), Blocks.NETHERRACK, "netherTungstenSpawnRate", 10, 10, 0, 127),
                new Vein("sulfur", NtmConfiguredFeatures.ORE_NETHER_SULFUR, NtmPlacedFeatures.ORE_NETHER_SULFUR_PLACED, NtmBlocks.ORE_NETHER_SULFUR.get(), Blocks.NETHERRACK, "netherSulfurSpawnRate", 26, 12, 0, 127),
                new Vein("phosphorus", NtmConfiguredFeatures.ORE_NETHER_FIRE, NtmPlacedFeatures.ORE_NETHER_FIRE_PLACED, NtmBlocks.ORE_NETHER_FIRE.get(), Blocks.NETHERRACK, "netherPhosphorusSpawnRate", 24, 6, 0, 127),
                new Vein("coal", NtmConfiguredFeatures.ORE_NETHER_COAL, NtmPlacedFeatures.ORE_NETHER_COAL_PLACED, NtmBlocks.ORE_NETHER_COAL.get(), Blocks.NETHERRACK, "netherCoalSpawnRate", 8, 32, 16, 96),
                new Vein("cobalt", NtmConfiguredFeatures.ORE_NETHER_COBALT, NtmPlacedFeatures.ORE_NETHER_COBALT_PLACED, NtmBlocks.ORE_NETHER_COBALT.get(), Blocks.NETHERRACK, "netherCobaltSpawnRate", 2, 6, 100, 26),
                new Vein("plutonium", NtmConfiguredFeatures.ORE_NETHER_PLUTONIUM, NtmPlacedFeatures.ORE_NETHER_PLUTONIUM_PLACED, NtmBlocks.ORE_NETHER_PLUTONIUM.get(), Blocks.NETHERRACK, "netherPlutoniumSpawnRate", 8, 4, 0, 127),
                new Vein("tikite", NtmConfiguredFeatures.ORE_TIKITE, NtmPlacedFeatures.ORE_TIKITE_PLACED, NtmBlocks.ORE_TIKITE.get(), Blocks.END_STONE, "endTikiteSpawnRate", 8, 6, 0, 127));
    }

    /** The six ores behind netherOre alone, in the original call order (HbmWorldGen.java:504-509). */
    private static List<ResourceKey<PlacedFeature>> sixNetherOres() {
        return List.of(NtmPlacedFeatures.ORE_NETHER_URANIUM_PLACED, NtmPlacedFeatures.ORE_NETHER_TUNGSTEN_PLACED, NtmPlacedFeatures.ORE_NETHER_SULFUR_PLACED,
                NtmPlacedFeatures.ORE_NETHER_FIRE_PLACED, NtmPlacedFeatures.ORE_NETHER_COAL_PLACED, NtmPlacedFeatures.ORE_NETHER_COBALT_PLACED);
    }

    /** The six features that existed before Goal28A (NtmBiomeModifiers: IS_OVERWORLD). */
    private static List<ResourceKey<PlacedFeature>> preExisting() {
        return List.of(NtmPlacedFeatures.OIL_BUBBLE_PLACED, NtmPlacedFeatures.COLTAN_DEPOSIT_PLACED, NtmPlacedFeatures.BEDROCK_OIL_PLACED,
                NtmPlacedFeatures.LANDMINE_PLACED, NtmPlacedFeatures.CRASHED_BOMB_PLACED, NtmPlacedFeatures.BLUEPRINT_CHEST_PLACED);
    }

    // ---------------------------------------------------------------- 1. biome modifiers as applied by the server

    // HbmWorldGen.java:501-535 generateNether (six ores behind netherOre :503-509; plutonium also behind enablePlutoniumOre :511, default false
    // GeneralConfig.java:18,99; smoldering :527-535 outside the netherOre block), :548-551 generateEnd (tikite behind endOre, default true
    // WorldConfig.java:124-125)
    @GameTest(template = TEMPLATE, batch = "hbm28a_modifiers_applied", timeoutTicks = 100)
    public static void modifiers_applied(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    RegistryAccess reg = helper.getLevel().registryAccess();
                    Registry<BiomeModifier> modifiers = reg.registryOrThrow(NeoForgeRegistries.Keys.BIOME_MODIFIERS);

                    // the decoded modifiers
                    BiomeModifier nether = modifiers.get(NtmBiomeModifiers.ADD_NETHER_ORES);
                    check(nether instanceof ConfigGatedAddFeaturesBiomeModifier, "add_nether_ores decodes to " + describe(nether));
                    ConfigGatedAddFeaturesBiomeModifier n = (ConfigGatedAddFeaturesBiomeModifier) nether;
                    check(n.config().equals(List.of("netherOres")), "add_nether_ores config " + n.config());
                    check(isTag(n.biomes(), BiomeTags.IS_NETHER), "add_nether_ores biomes " + n.biomes());
                    check(n.step() == GenerationStep.Decoration.UNDERGROUND_ORES, "add_nether_ores step " + n.step());
                    check(keys(n.features()).equals(names(sixNetherOres())), "add_nether_ores features " + keys(n.features()));

                    BiomeModifier pu = modifiers.get(NtmBiomeModifiers.ADD_NETHER_PLUTONIUM_ORE);
                    check(pu instanceof ConfigGatedAddFeaturesBiomeModifier, "add_nether_plutonium_ore decodes to " + describe(pu));
                    ConfigGatedAddFeaturesBiomeModifier p = (ConfigGatedAddFeaturesBiomeModifier) pu;
                    check(new HashSet<>(p.config()).equals(Set.of("netherOres", "enablePlutoniumNetherOre")) && p.config().size() == 2, "add_nether_plutonium_ore config " + p.config());
                    check(isTag(p.biomes(), BiomeTags.IS_NETHER) && p.step() == GenerationStep.Decoration.UNDERGROUND_ORES, "add_nether_plutonium_ore biomes / step " + p.biomes() + " " + p.step());
                    check(keys(p.features()).equals(names(List.of(NtmPlacedFeatures.ORE_NETHER_PLUTONIUM_PLACED))), "add_nether_plutonium_ore features " + keys(p.features()));

                    // Goal28A decision: the smoldering loop is outside if(netherOre) (:527), so its modifier is a plain add_features
                    BiomeModifier smolder = modifiers.get(NtmBiomeModifiers.ADD_SMOLDERING_NETHERRACK);
                    check(smolder instanceof AddFeaturesBiomeModifier, "add_smoldering_netherrack decodes to " + describe(smolder));
                    AddFeaturesBiomeModifier s = (AddFeaturesBiomeModifier) smolder;
                    check(isTag(s.biomes(), BiomeTags.IS_NETHER) && s.step() == GenerationStep.Decoration.TOP_LAYER_MODIFICATION, "add_smoldering_netherrack biomes / step " + s.biomes() + " " + s.step());
                    check(keys(s.features()).equals(names(List.of(NtmPlacedFeatures.SMOLDERING_NETHERRACK_PLACED))), "add_smoldering_netherrack features " + keys(s.features()));

                    BiomeModifier end = modifiers.get(NtmBiomeModifiers.ADD_END_ORES);
                    check(end instanceof ConfigGatedAddFeaturesBiomeModifier, "add_end_ores decodes to " + describe(end));
                    ConfigGatedAddFeaturesBiomeModifier e = (ConfigGatedAddFeaturesBiomeModifier) end;
                    check(e.config().equals(List.of("endOres")) && isTag(e.biomes(), BiomeTags.IS_END) && e.step() == GenerationStep.Decoration.UNDERGROUND_ORES, "add_end_ores " + e.config() + " " + e.biomes() + " " + e.step());
                    check(keys(e.features()).equals(names(List.of(NtmPlacedFeatures.ORE_TIKITE_PLACED))), "add_end_ores features " + keys(e.features()));

                    // codec registrations
                    check(id("config_gated_add_features").equals(NeoForgeRegistries.BIOME_MODIFIER_SERIALIZERS.getKey(nether.codec())), "gated modifier codec key " + NeoForgeRegistries.BIOME_MODIFIER_SERIALIZERS.getKey(nether.codec()));
                    PlacedFeature sulfurPlaced = reg.registryOrThrow(Registries.PLACED_FEATURE).getOrThrow(NtmPlacedFeatures.ORE_NETHER_SULFUR_PLACED);
                    check(id("config_count").equals(BuiltInRegistries.PLACEMENT_MODIFIER_TYPE.getKey(sulfurPlaced.placement().get(0).type())), "config count type key " + BuiltInRegistries.PLACEMENT_MODIFIER_TYPE.getKey(sulfurPlaced.placement().get(0).type()));

                    // with the default config the server applied: the nether biomes carry the six ores and the smoldering feature, not plutonium
                    check(NtmConfig.COMMON.NETHER_ORES.get() && NtmConfig.COMMON.END_ORES.get() && !NtmConfig.COMMON.ENABLE_PLUTONIUM_NETHER_ORE.get(),
                            "the server did not start with the default switches: netherOres " + NtmConfig.COMMON.NETHER_ORES.get() + " endOres " + NtmConfig.COMMON.END_ORES.get()
                                    + " enablePlutoniumNetherOre " + NtmConfig.COMMON.ENABLE_PLUTONIUM_NETHER_ORE.get());
                    List<ResourceKey<PlacedFeature>> netherExpected = new ArrayList<>(sixNetherOres());
                    netherExpected.add(NtmPlacedFeatures.SMOLDERING_NETHERRACK_PLACED);
                    for(ResourceKey<Biome> biome : List.of(Biomes.NETHER_WASTES, Biomes.BASALT_DELTAS, Biomes.CRIMSON_FOREST, Biomes.WARPED_FOREST, Biomes.SOUL_SAND_VALLEY)) {
                        Holder<Biome> holder = biome(helper, biome);
                        for(ResourceKey<PlacedFeature> key : sixNetherOres()) {
                            check(inStep(holder, GenerationStep.Decoration.UNDERGROUND_ORES, key), biome.location() + " lacks " + key.location() + " in underground_ores");
                        }
                        check(inStep(holder, GenerationStep.Decoration.TOP_LAYER_MODIFICATION, NtmPlacedFeatures.SMOLDERING_NETHERRACK_PLACED), biome.location() + " lacks smoldering_netherrack_placed in top_layer_modification");
                        check(!inAnyStep(holder, NtmPlacedFeatures.ORE_NETHER_PLUTONIUM_PLACED), biome.location() + " carries the plutonium ore with enablePlutoniumNetherOre false");
                        check(!inAnyStep(holder, NtmPlacedFeatures.ORE_TIKITE_PLACED), biome.location() + " carries trixite");
                        for(ResourceKey<PlacedFeature> key : preExisting()) check(!inAnyStep(holder, key), biome.location() + " carries the overworld feature " + key.location());
                    }
                    for(ResourceKey<Biome> biome : List.of(Biomes.THE_END, Biomes.END_HIGHLANDS, Biomes.END_MIDLANDS, Biomes.SMALL_END_ISLANDS, Biomes.END_BARRENS)) {
                        Holder<Biome> holder = biome(helper, biome);
                        check(inStep(holder, GenerationStep.Decoration.UNDERGROUND_ORES, NtmPlacedFeatures.ORE_TIKITE_PLACED), biome.location() + " lacks ore_tikite_placed");
                        for(ResourceKey<PlacedFeature> key : netherExpected) check(!inAnyStep(holder, key), biome.location() + " carries " + key.location());
                    }
                    for(ResourceKey<Biome> biome : List.of(Biomes.PLAINS, Biomes.DESERT, Biomes.DEEP_DARK, Biomes.FOREST, Biomes.OCEAN)) {
                        Holder<Biome> holder = biome(helper, biome);
                        for(ResourceKey<PlacedFeature> key : netherExpected) check(!inAnyStep(holder, key), biome.location() + " carries " + key.location());
                        check(!inAnyStep(holder, NtmPlacedFeatures.ORE_NETHER_PLUTONIUM_PLACED) && !inAnyStep(holder, NtmPlacedFeatures.ORE_TIKITE_PLACED), biome.location() + " carries plutonium or trixite");
                        // the six pre-existing overworld features are still applied
                        for(ResourceKey<PlacedFeature> key : preExisting()) check(inAnyStep(holder, key), biome.location() + " lost the pre-existing feature " + key.location());
                    }
                    LOGGER.info("{} modifiers_applied: 4 modifiers decoded; nether biomes 6 ores + smoldering, no plutonium; end biomes trixite; overworld none of them and the 6 old features", TAG);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "modifiers_applied"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 2. the config gate

    // HbmWorldGen.java:503 if(WorldConfig.netherOre) around :504-524; :511 if(GeneralConfig.enablePlutoniumOre) inside it; :527-535 smoldering
    // outside it; :550 if(WorldConfig.endOre). The modifier is the server's decoded instance; modify() runs on a fresh builder.
    @GameTest(template = TEMPLATE, batch = "hbm28a_config_gate", timeoutTicks = 100)
    public static void config_gate(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    Registry<BiomeModifier> modifiers = helper.getLevel().registryAccess().registryOrThrow(NeoForgeRegistries.Keys.BIOME_MODIFIERS);
                    BiomeModifier nether = modifiers.get(NtmBiomeModifiers.ADD_NETHER_ORES);
                    BiomeModifier pu = modifiers.get(NtmBiomeModifiers.ADD_NETHER_PLUTONIUM_ORE);
                    BiomeModifier smolder = modifiers.get(NtmBiomeModifiers.ADD_SMOLDERING_NETHERRACK);
                    BiomeModifier end = modifiers.get(NtmBiomeModifiers.ADD_END_ORES);
                    Holder<Biome> wastes = biome(helper, Biomes.NETHER_WASTES), deltas = biome(helper, Biomes.BASALT_DELTAS);
                    Holder<Biome> theEnd = biome(helper, Biomes.THE_END), plains = biome(helper, Biomes.PLAINS);
                    ModConfigSpec.BooleanValue netherOres = NtmConfig.COMMON.NETHER_ORES, endOres = NtmConfig.COMMON.END_ORES, plutonium = NtmConfig.COMMON.ENABLE_PLUTONIUM_NETHER_ORE;
                    boolean saveNether = netherOres.get(), saveEnd = endOres.get(), savePu = plutonium.get();
                    try {
                        List<String> six = names(sixNetherOres());
                        String puName = NtmPlacedFeatures.ORE_NETHER_PLUTONIUM_PLACED.location().toString();
                        String smolderName = NtmPlacedFeatures.SMOLDERING_NETHERRACK_PLACED.location().toString();
                        String tikiteName = NtmPlacedFeatures.ORE_TIKITE_PLACED.location().toString();

                        netherOres.set(true);
                        check(added(nether, wastes, BiomeModifier.Phase.ADD).equals(six), "netherOres true: nether_wastes gained " + added(nether, wastes, BiomeModifier.Phase.ADD));
                        check(added(nether, deltas, BiomeModifier.Phase.ADD).equals(six), "netherOres true: basalt_deltas gained " + added(nether, deltas, BiomeModifier.Phase.ADD));
                        netherOres.set(false);
                        check(added(nether, wastes, BiomeModifier.Phase.ADD).isEmpty(), "netherOres false: nether_wastes gained " + added(nether, wastes, BiomeModifier.Phase.ADD));
                        // :527-535 outside the netherOre block: smoldering netherrack is added with the switch off as well
                        check(added(smolder, wastes, BiomeModifier.Phase.ADD).equals(List.of(smolderName + "@" + GenerationStep.Decoration.TOP_LAYER_MODIFICATION)), "netherOres false: smoldering modifier gave " + added(smolder, wastes, BiomeModifier.Phase.ADD));
                        netherOres.set(true);
                        check(added(smolder, wastes, BiomeModifier.Phase.ADD).equals(List.of(smolderName + "@" + GenerationStep.Decoration.TOP_LAYER_MODIFICATION)), "netherOres true: smoldering modifier gave " + added(smolder, wastes, BiomeModifier.Phase.ADD));

                        // plutonium: only netherOres AND enablePlutoniumNetherOre (:503, :511)
                        for(boolean a : new boolean[] { false, true }) for(boolean b : new boolean[] { false, true }) {
                            netherOres.set(a);
                            plutonium.set(b);
                            List<String> got = added(pu, wastes, BiomeModifier.Phase.ADD);
                            List<String> want = a && b ? List.of(puName) : List.of();
                            check(got.equals(want), "plutonium modifier with netherOres " + a + ", enablePlutoniumNetherOre " + b + " added " + got + ", expected " + want);
                        }
                        plutonium.set(savePu);
                        netherOres.set(true);

                        // end (:550)
                        endOres.set(true);
                        check(added(end, theEnd, BiomeModifier.Phase.ADD).equals(List.of(tikiteName)), "endOres true: the_end gained " + added(end, theEnd, BiomeModifier.Phase.ADD));
                        endOres.set(false);
                        check(added(end, theEnd, BiomeModifier.Phase.ADD).isEmpty(), "endOres false: the_end gained " + added(end, theEnd, BiomeModifier.Phase.ADD));
                        endOres.set(true);

                        // non-member biomes get nothing even with every switch on
                        plutonium.set(true);
                        for(BiomeModifier m : List.of(nether, pu, end, smolder)) {
                            check(added(m, plains, BiomeModifier.Phase.ADD).isEmpty(), "plains gained " + added(m, plains, BiomeModifier.Phase.ADD) + " from " + describe(m));
                        }
                        check(added(nether, theEnd, BiomeModifier.Phase.ADD).isEmpty() && added(end, wastes, BiomeModifier.Phase.ADD).isEmpty(), "a nether modifier added to the end or the end modifier to the nether");
                        // phases other than ADD do nothing
                        for(BiomeModifier.Phase phase : BiomeModifier.Phase.values()) {
                            if(phase == BiomeModifier.Phase.ADD) continue;
                            for(BiomeModifier m : List.of(nether, pu, end)) {
                                Holder<Biome> target = m == end ? theEnd : wastes;
                                check(added(m, target, phase).isEmpty(), "phase " + phase + " added " + added(m, target, phase) + " from " + describe(m));
                            }
                        }
                        LOGGER.info("{} config_gate: six ores only with netherOres, plutonium only with both switches, trixite only with endOres, smoldering ungated, non-members and other phases untouched", TAG);
                    } finally {
                        netherOres.set(saveNether);
                        endOres.set(saveEnd);
                        plutonium.set(savePu);
                    }
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "config_gate"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 3. the config count placement and the height ranges

    // DungeonToolbox.java:79-85: veinCount iterations, y = minHeight + rand(variance), so y covers minHeight .. minHeight + variance - 1;
    // the counts are WorldConfig.java:183-191 defaults
    @GameTest(template = TEMPLATE, batch = "hbm28a_config_count", timeoutTicks = 100)
    public static void config_count(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    Registry<PlacedFeature> placed = level.registryAccess().registryOrThrow(Registries.PLACED_FEATURE);
                    PlacementContext ctx = new PlacementContext(level, level.getChunkSource().getGenerator(), Optional.empty());
                    BlockPos origin = helper.absolutePos(new BlockPos(0, 1, 0));
                    RandomSource random = RandomSource.create(28L);
                    for(Vein v : veins()) {
                        PlacedFeature pf = placed.getOrThrow(v.placed());
                        List<PlacementModifier> mods = pf.placement();
                        check(mods.size() == 4, v.name() + " placement has " + mods.size() + " modifiers: " + mods);
                        check(mods.get(0) instanceof ConfigCountPlacement, v.name() + " first placement " + mods.get(0));
                        check(mods.get(1) instanceof InSquarePlacement, v.name() + " second placement " + mods.get(1));
                        check(mods.get(2) instanceof HeightRangePlacement, v.name() + " third placement " + mods.get(2));
                        check(mods.get(3) instanceof BiomeFilter, v.name() + " fourth placement " + mods.get(3));
                        check(pf.feature().is(v.configured()), v.name() + " places " + pf.feature());

                        ModConfigSpec.IntValue count = NtmConfig.COMMON.worldgenCount(v.countKey());
                        check(count != null, v.name() + ": no config count " + v.countKey());
                        check(count.getDefault() == v.defaultCount(), v.name() + ": default " + count.getDefault() + ", original " + v.defaultCount());
                        check(count.get() == v.defaultCount(), v.name() + ": the test server runs with " + count.get() + " instead of the default " + v.defaultCount());
                        long n = mods.get(0).getPositions(ctx, random, origin).count();
                        check(n == v.defaultCount(), v.name() + ": config_count yields " + n + " positions, expected " + v.defaultCount());

                        // the height range: 4000 samples reach both ends of min .. min + variance - 1 and never leave it
                        int lo = Integer.MAX_VALUE, hi = Integer.MIN_VALUE;
                        for(int i = 0; i < 4000; i++) {
                            for(BlockPos p : mods.get(2).getPositions(ctx, random, origin).toList()) {
                                lo = Math.min(lo, p.getY());
                                hi = Math.max(hi, p.getY());
                            }
                        }
                        check(lo == v.minHeight() && hi == v.maxY(), v.name() + ": sampled y " + lo + ".." + hi + ", original " + v.minHeight() + ".." + v.maxY());
                        LOGGER.info("{} config_count: {} count {} (key {}), y {}..{}", TAG, v.name(), n, v.countKey(), lo, hi);
                    }

                    // the count follows the config value, read per call
                    ModConfigSpec.IntValue sulfur = NtmConfig.COMMON.NETHER_SULFUR_SPAWN_RATE;
                    int save = sulfur.get();
                    PlacementModifier sulfurCount = placed.getOrThrow(NtmPlacedFeatures.ORE_NETHER_SULFUR_PLACED).placement().get(0);
                    try {
                        for(int want : new int[] { 0, 1, 26 }) {
                            sulfur.set(want);
                            long n = sulfurCount.getPositions(ctx, random, origin).count();
                            check(n == want, "netherSulfurSpawnRate " + want + ": config_count yields " + n);
                        }
                        check(ConfigCountPlacement.of("netherSulfurSpawnRate").getPositions(ctx, random, origin).count() == 26, "a fresh ConfigCountPlacement does not read the config");
                    } finally {
                        sulfur.set(save);
                    }
                    check(NtmConfig.COMMON.worldgenCount("noSuchKey") == null && NtmConfig.COMMON.worldgenSwitch("noSuchKey") == null, "unknown worldgen names resolve to a config value");
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "config_count"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 4. the ore features

    // HbmWorldGen.java:504-512, :550 (WorldGenMinable(ore, amount, target)): the vanilla ore feature stands in for WorldGenMinable, so only the
    // target block, the ore and the configured size are the original's; the vein shape (and a placed count above the size) is vanilla's
    @GameTest(template = TEMPLATE, batch = "hbm28a_ore_features", timeoutTicks = 200)
    public static void ore_features(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    ChunkGenerator generator = level.getChunkSource().getGenerator();
                    Registry<ConfiguredFeature<?, ?>> configured = level.registryAccess().registryOrThrow(Registries.CONFIGURED_FEATURE);
                    BlockPos origin = helper.absolutePos(new BlockPos(8, 6, 8));
                    try {
                        for(Vein v : veins()) {
                            ConfiguredFeature<?, ?> cf = configured.getOrThrow(v.configured());
                            check(cf.config() instanceof OreConfiguration, v.name() + " is not an ore feature: " + cf.config());
                            OreConfiguration oc = (OreConfiguration) cf.config();
                            check(oc.size == v.size(), v.name() + " vein size " + oc.size + ", original " + v.size());
                            check(oc.targetStates.size() == 1 && oc.targetStates.get(0).state.is(v.ore()), v.name() + " targets " + oc.targetStates.size() + " / " + (oc.targetStates.isEmpty() ? null : oc.targetStates.get(0).state));
                            RandomSource rt = RandomSource.create(1L);
                            check(oc.targetStates.get(0).target.test(v.target().defaultBlockState(), rt), v.name() + " does not replace " + v.target());
                            for(Block other : List.of(Blocks.STONE, Blocks.NETHERRACK, Blocks.END_STONE, Blocks.SOUL_SAND, Blocks.BLACKSTONE, Blocks.AIR)) {
                                if(other == v.target()) continue;
                                check(!oc.targetStates.get(0).target.test(other.defaultBlockState(), rt), v.name() + " would replace " + other);
                            }

                            // real placement in a cube of the target with other blocks mixed in
                            Block mix = v.target() == Blocks.NETHERRACK ? Blocks.SOUL_SAND : Blocks.NETHERRACK;
                            Map<BlockPos, BlockState> before = fillCube(helper, v.target(), mix);
                            int total = 0;
                            List<Integer> perSeed = new ArrayList<>();
                            for(long seed = 1; seed <= 4; seed++) {
                                cf.place(level, generator, RandomSource.create(seed * 7919L + v.size()), origin);
                                int placedHere = 0;
                                List<BlockPos> changed = new ArrayList<>();
                                for(Map.Entry<BlockPos, BlockState> e : before.entrySet()) {
                                    BlockState now = level.getBlockState(e.getKey());
                                    if(now == e.getValue()) continue;
                                    check(e.getValue().is(v.target()), v.name() + " seed " + seed + ": replaced " + e.getValue() + " at " + e.getKey() + " with " + now);
                                    check(now.is(v.ore()), v.name() + " seed " + seed + ": " + e.getKey() + " became " + now);
                                    placedHere++;
                                    changed.add(e.getKey());
                                }
                                perSeed.add(placedHere);
                                total += placedHere;
                                for(BlockPos p : changed) level.setBlock(p, before.get(p), 2 | 16);
                            }
                            check(total > 0, v.name() + ": four placements put no ore down");
                            LOGGER.info("{} ore_features: {} size {} placed {} per seed (vanilla OreFeature may exceed the size)", TAG, v.name(), v.size(), perSeed);
                        }
                    } finally {
                        clearCube(helper);
                    }
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "ore_features"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 5. smoldering netherrack

    private static final int SMOLDER_LOW = 8, SMOLDER_HIGH = 115;

    // HbmWorldGen.java:527-535: 30 tries; x = i + rand(16), z = j + rand(16), d = 16 + rand(96); for y = d - 5 .. d: block above air and the block
    // netherrack -> ore_nether_smoldering. So y stays in 11 .. 111. The lattice (absolute y 8..115 above the test) puts eligible netherrack
    // (air above) on every y = 0 mod 4 in even columns, blackstone with air above in odd columns, netherrack under soul sand on y = 2 mod 4.
    @GameTest(template = TEMPLATE, batch = "hbm28a_smoldering", timeoutTicks = 300)
    public static void smoldering(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    BlockPos corner = helper.absolutePos(BlockPos.ZERO);
                    int x0 = corner.getX(), z0 = corner.getZ();
                    check(corner.getY() + 12 < SMOLDER_LOW, "the test structure at y " + corner.getY() + " overlaps the lattice");
                    ConfiguredFeature<?, ?> cf = level.registryAccess().registryOrThrow(Registries.CONFIGURED_FEATURE).getOrThrow(NtmConfiguredFeatures.SMOLDERING_NETHERRACK);
                    BlockState smolder = NtmBlocks.ORE_NETHER_SMOLDERING.get().defaultBlockState();
                    try {
                        for(int x = x0; x < x0 + 16; x++) for(int z = z0; z < z0 + 16; z++) for(int y = SMOLDER_LOW; y <= SMOLDER_HIGH; y++) {
                            BlockState s = lattice(x, y, z);
                            if(!s.isAir()) level.setBlock(new BlockPos(x, y, z), s, 2 | 16);
                        }
                        int seeds = 20, total = 0, lowest = Integer.MAX_VALUE, highest = Integer.MIN_VALUE;
                        for(long seed = 1; seed <= seeds; seed++) {
                            Set<BlockPos> expected = simulateOriginal(RandomSource.create(seed), x0, z0);
                            cf.place(level, level.getChunkSource().getGenerator(), RandomSource.create(seed), new BlockPos(x0, 0, z0));
                            Set<BlockPos> actual = new HashSet<>();
                            for(int x = x0; x < x0 + 16; x++) for(int z = z0; z < z0 + 16; z++) for(int y = SMOLDER_LOW - 1; y <= SMOLDER_HIGH + 1; y++) {
                                BlockPos p = new BlockPos(x, y, z);
                                BlockState now = level.getBlockState(p);
                                if(now.is(smolder.getBlock())) {
                                    actual.add(p);
                                } else {
                                    check(now == lattice(x, y, z), "seed " + seed + ": " + p + " became " + now + " (was " + lattice(x, y, z) + ")");
                                }
                            }
                            for(BlockPos p : actual) {
                                check(lattice(p.getX(), p.getY(), p.getZ()).is(Blocks.NETHERRACK) && lattice(p.getX(), p.getY() + 1, p.getZ()).isAir(),
                                        "seed " + seed + ": converted " + p + " which was " + lattice(p.getX(), p.getY(), p.getZ()) + " under " + lattice(p.getX(), p.getY() + 1, p.getZ()));
                                check(p.getY() >= 11 && p.getY() <= 111, "seed " + seed + ": converted y " + p.getY() + " outside 11..111");
                                lowest = Math.min(lowest, p.getY());
                                highest = Math.max(highest, p.getY());
                            }
                            check(actual.equals(expected), "seed " + seed + ": converted " + actual.size() + " blocks, the original loop converts " + expected.size()
                                    + "; only NEO " + diff(actual, expected) + ", only original " + diff(expected, actual));
                            total += actual.size();
                            for(BlockPos p : actual) level.setBlock(p, Blocks.NETHERRACK.defaultBlockState(), 2 | 16);
                        }
                        check(total > 0, "twenty seeds converted nothing");
                        LOGGER.info("{} smoldering: {} seeds, {} conversions equal to the original loop, y {}..{} (bounds 11..111; lattice 8..115)", TAG, seeds, total, lowest, highest);
                    } finally {
                        for(int x = x0; x < x0 + 16; x++) for(int z = z0; z < z0 + 16; z++) for(int y = SMOLDER_LOW; y <= SMOLDER_HIGH; y++) {
                            BlockPos p = new BlockPos(x, y, z);
                            if(!level.getBlockState(p).isAir()) level.setBlock(p, Blocks.AIR.defaultBlockState(), 2 | 16);
                        }
                    }
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "smoldering"))
                .thenSucceed();
    }

    private static BlockState lattice(int x, int y, int z) {
        if(y < SMOLDER_LOW || y > SMOLDER_HIGH) return Blocks.AIR.defaultBlockState();
        return switch(y & 3) {
            case 0 -> ((x + z) & 1) == 0 ? Blocks.NETHERRACK.defaultBlockState() : Blocks.BLACKSTONE.defaultBlockState();
            case 2 -> Blocks.NETHERRACK.defaultBlockState();
            case 3 -> Blocks.SOUL_SAND.defaultBlockState();
            default -> Blocks.AIR.defaultBlockState();
        };
    }

    /** HbmWorldGen.java:527-535 on the lattice, with the same draw order (x, z, d) and the conversions visible to later tries. */
    private static Set<BlockPos> simulateOriginal(RandomSource rand, int i, int j) {
        Set<BlockPos> converted = new HashSet<>();
        for(int k = 0; k < 30; k++) {
            int x = i + rand.nextInt(16);
            int z = j + rand.nextInt(16);
            int d = 16 + rand.nextInt(96);
            for(int y = d - 5; y <= d; y++) {
                BlockPos p = new BlockPos(x, y, z);
                boolean airAbove = !converted.contains(p.above()) && lattice(x, y + 1, z).isAir();
                boolean netherrack = !converted.contains(p) && lattice(x, y, z).is(Blocks.NETHERRACK);
                if(airAbove && netherrack) converted.add(p);
            }
        }
        return converted;
    }

    // ---------------------------------------------------------------- 6. outgassing

    private record Break(Block block, Block gas) { }

    // BlockOutgas.java:40-55 getGas (nether uranium -> radon :41-45, nether coal -> monoxide :53-55, brick_asbestos -> asbestos :57-61);
    // :84-91 updateTick (random tick) into one random neighbour if air; :94-101 dropBlockAsItemWithChance sets the gas when onBreak;
    // ModBlocks.java:1258 nether coal (randomTick false, onBreak true), :1260-1261 nether uranium (randomTick true, onBreak true)
    @GameTest(template = TEMPLATE, batch = "hbm28a_outgas", timeoutTicks = 100)
    public static void outgas(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    Block radon = NtmBlocks.GAS_RADON.get(), monoxide = NtmBlocks.GAS_MONOXIDE.get(), asbestos = NtmBlocks.GAS_ASBESTOS.get();
                    check(NtmBlocks.ORE_NETHER_URANIUM.get() instanceof OutgasBlock && NtmBlocks.ORE_NETHER_URANIUM_SCORCHED.get() instanceof OutgasBlock, "the nether uranium ores are not outgassing blocks");
                    check(NtmBlocks.ORE_NETHER_COAL.get() instanceof NetherCoalBlock, "ore_nether_coal is " + NtmBlocks.ORE_NETHER_COAL.get().getClass().getSimpleName());
                    check(((OutgasBlock) NtmBlocks.ORE_NETHER_URANIUM.get()).getGas().is(radon) && ((OutgasBlock) NtmBlocks.ORE_NETHER_URANIUM_SCORCHED.get()).getGas().is(radon), "nether uranium gas is not radon");
                    check(((OutgasBlock) NtmBlocks.ORE_NETHER_COAL.get()).getGas().is(monoxide), "nether coal gas " + ((OutgasBlock) NtmBlocks.ORE_NETHER_COAL.get()).getGas());
                    check(((OutgasBlock) NtmBlocks.BRICK_ASBESTOS.get()).getGas().is(asbestos), "brick_asbestos gas " + ((OutgasBlock) NtmBlocks.BRICK_ASBESTOS.get()).getGas());
                    // randomTick flags: uranium ticks, nether coal does not (ModBlocks.java:1258,1260-1261)
                    check(NtmBlocks.ORE_NETHER_URANIUM.get().defaultBlockState().isRandomlyTicking() && NtmBlocks.ORE_NETHER_URANIUM_SCORCHED.get().defaultBlockState().isRandomlyTicking(), "nether uranium does not tick randomly");
                    check(!NtmBlocks.ORE_NETHER_COAL.get().defaultBlockState().isRandomlyTicking(), "nether coal ticks randomly");
                    // NEO local difference kept by Goal28A (task book: not changed): the overworld uranium ore is a plain block
                    check(!(NtmBlocks.ORE_URANIUM.get() instanceof OutgasBlock), "ore_uranium became an outgassing block");

                    // random tick: one of the six air neighbours gets radon
                    int n = 0;
                    for(Block ore : List.of(NtmBlocks.ORE_NETHER_URANIUM.get(), NtmBlocks.ORE_NETHER_URANIUM_SCORCHED.get())) {
                        BlockPos rel = new BlockPos(3 + 6 * n++, 4, 4);
                        for(long seed = 0; seed < 6; seed++) {
                            clearAround(helper, rel);
                            helper.setBlock(rel, ore);
                            BlockState state = helper.getBlockState(rel);
                            state.randomTick(level, helper.absolutePos(rel), RandomSource.create(seed));
                            int gas = 0, other = 0;
                            for(Direction d : Direction.values()) {
                                BlockState s = helper.getBlockState(rel.relative(d));
                                if(s.is(radon)) gas++;
                                else if(!s.isAir()) other++;
                            }
                            check(gas == 1 && other == 0, BuiltInRegistries.BLOCK.getKey(ore) + " random tick (seed " + seed + "): " + gas + " radon neighbours, " + other + " other");
                        }
                        clearAround(helper, rel);
                    }

                    // the player break (ServerPlayerGameMode.destroyBlock, survival): the gas takes the ore's place
                    Player player = helper.makeMockPlayer(GameType.SURVIVAL);
                    player.setItemInHand(InteractionHand.MAIN_HAND, new ItemStack(Items.STONE_PICKAXE));
                    int col = 0;
                    for(Break b : List.of(new Break(NtmBlocks.ORE_NETHER_URANIUM.get(), radon), new Break(NtmBlocks.ORE_NETHER_URANIUM_SCORCHED.get(), radon),
                            new Break(NtmBlocks.ORE_NETHER_COAL.get(), monoxide), new Break(NtmBlocks.BRICK_ASBESTOS.get(), asbestos))) {
                        BlockPos rel = new BlockPos(2 + 3 * col++, 2, 11);
                        helper.setBlock(rel, b.block());
                        playerBreak(helper, player, rel);
                        BlockState after = helper.getBlockState(rel);
                        check(after.is(b.gas()), BuiltInRegistries.BLOCK.getKey(b.block()) + " broken by a player left " + after + ", expected " + BuiltInRegistries.BLOCK.getKey(b.gas()));
                        helper.setBlock(rel, Blocks.AIR);
                    }
                    // the overworld uranium ore (NEO plain block) leaves air
                    BlockPos plain = new BlockPos(14, 2, 11);
                    helper.setBlock(plain, NtmBlocks.ORE_URANIUM.get());
                    playerBreak(helper, player, plain);
                    check(helper.getBlockState(plain).isAir(), "ore_uranium broken by a player left " + helper.getBlockState(plain));
                    discardItems(helper);
                    LOGGER.info("{} outgas: nether uranium (both) radon on random tick and break, nether coal monoxide on break and no random ticks, brick_asbestos asbestos, ore_uranium plain", TAG);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "outgas"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 7. stepping

    // BlockNetherCoal.java:27-29 and BlockSmolder.java:39-41 onEntityWalking: setFire(3) = 60 fire ticks; 1.7.10 Entity.moveEntity does not call
    // onEntityWalking for a sneaking player, so a player stepping carefully is not ignited (the NEO stepOn check)
    @GameTest(template = TEMPLATE, batch = "hbm28a_stepping", timeoutTicks = 100)
    public static void stepping(GameTestHelper helper) {
        BlockPos coal = new BlockPos(3, 1, 3), smolder = new BlockPos(8, 1, 3), stone = new BlockPos(13, 1, 3);
        helper.setBlock(coal, NtmBlocks.ORE_NETHER_COAL.get());
        helper.setBlock(smolder, NtmBlocks.ORE_NETHER_SMOLDERING.get());
        helper.setBlock(stone, Blocks.STONE);
        for(BlockPos floor : List.of(coal, smolder, stone)) {
            for(Direction d : SmokeTestSupport.HORIZONTALS) {
                helper.setBlock(floor.above().relative(d), Blocks.GLASS);
                helper.setBlock(floor.above(2).relative(d), Blocks.GLASS);
            }
            helper.setBlock(floor.above(3), Blocks.GLASS);
        }
        List<Pig> pigs = new ArrayList<>();
        for(BlockPos floor : List.of(coal, smolder, stone)) pigs.add(helper.spawn(EntityType.PIG, new Vec3(floor.getX() + 0.5, floor.getY() + 1, floor.getZ() + 0.5)));

        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    // the direct hook on a mock player: walking ignites for 60 ticks, stepping carefully does not
                    for(BlockPos floor : List.of(coal, smolder)) {
                        BlockState state = helper.getBlockState(floor);
                        Player walker = helper.makeMockPlayer(GameType.SURVIVAL);
                        state.getBlock().stepOn(level, helper.absolutePos(floor), state, walker);
                        check(walker.getRemainingFireTicks() == 60, state + ": stepOn gave " + walker.getRemainingFireTicks() + " fire ticks, expected 60 (setFire(3))");
                        Player sneaker = helper.makeMockPlayer(GameType.SURVIVAL);
                        sneaker.setShiftKeyDown(true);
                        int before = sneaker.getRemainingFireTicks();
                        state.getBlock().stepOn(level, helper.absolutePos(floor), state, sneaker);
                        check(sneaker.getRemainingFireTicks() == before && !sneaker.isOnFire(), state + ": a sneaking player was ignited (" + sneaker.getRemainingFireTicks() + ")");
                    }
                    // light levels (ModBlocks.java:1258 setLightLevel(10F/15F) -> 10, :1259 setLightLevel(1F) -> 15)
                    check(helper.getBlockState(coal).getLightEmission() == 10, "nether coal light " + helper.getBlockState(coal).getLightEmission());
                    check(helper.getBlockState(smolder).getLightEmission() == 15, "smoldering netherrack light " + helper.getBlockState(smolder).getLightEmission());
                    check(NtmBlocks.ORE_NETHER_SMOLDERING.get() instanceof SmolderBlock, "ore_nether_smoldering is " + NtmBlocks.ORE_NETHER_SMOLDERING.get().getClass().getSimpleName());
                }))
                .thenIdle(10)
                .thenExecute(guard(() -> {
                    // the real movement path: pigs standing on the blocks for 10 ticks
                    Pig onCoal = pigs.get(0), onSmolder = pigs.get(1), onStone = pigs.get(2);
                    check(onCoal.getRemainingFireTicks() > 50 && onCoal.getRemainingFireTicks() <= 60, "pig on nether coal: " + onCoal.getRemainingFireTicks() + " fire ticks (expected re-ignited to 60 each step)");
                    check(onSmolder.getRemainingFireTicks() > 50 && onSmolder.getRemainingFireTicks() <= 60, "pig on smoldering netherrack: " + onSmolder.getRemainingFireTicks() + " fire ticks");
                    check(!onStone.isOnFire() && onStone.getRemainingFireTicks() <= 0, "pig on stone: " + onStone.getRemainingFireTicks() + " fire ticks");
                    LOGGER.info("{} stepping: fire ticks coal {}, smoldering {}, stone {}", TAG, onCoal.getRemainingFireTicks(), onSmolder.getRemainingFireTicks(), onStone.getRemainingFireTicks());
                    for(Pig pig : pigs) pig.discard();
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "stepping"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 8. loot

    // BlockOre.java:60-61,114-115 (sulfur 2 + rand(3)), :75-76 (fire: 1 in 10 ingot_phosphorus else powder_fire), :99-100,119 (nether cobalt
    // fragment 5 + rand(8)), :132-140 quantityDroppedWithBonus (fortune: x (max(0, rand(f + 2) - 1) + 1) when the drop is not the block);
    // BlockNetherCoal.java:22-24 coal_infernal (BlockOre bonus); BlockSmolder.java:33-36 powder_fire x1 (plain Block: no bonus); ModBlocks.java:1263
    // nether tungsten BlockGeneric (drops itself); silk touch keeps the block (1.7.10 Block.canSilkHarvest for these full cubes)
    @GameTest(template = TEMPLATE, batch = "hbm28a_loot", timeoutTicks = 100)
    public static void loot(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    HolderLookup.RegistryLookup<Enchantment> ench = helper.getLevel().registryAccess().lookupOrThrow(Registries.ENCHANTMENT);
                    ItemStack plain = new ItemStack(Items.STONE_PICKAXE);
                    ItemStack silk = new ItemStack(Items.STONE_PICKAXE);
                    silk.enchant(ench.getOrThrow(Enchantments.SILK_TOUCH), 1);
                    ItemStack fortune = new ItemStack(Items.STONE_PICKAXE);
                    fortune.enchant(ench.getOrThrow(Enchantments.FORTUNE), 3);
                    BlockPos rel = new BlockPos(4, 1, 4);

                    // hardness 0.4 for the six new blocks (ModBlocks.java:1258-1259,1263-1266); resistance as NEO's existing nether ores, which
                    // the original also gives setResistance(10.0F)
                    float resistance = NtmBlocks.ORE_NETHER_URANIUM.get().getExplosionResistance();
                    for(Block b : List.of(NtmBlocks.ORE_NETHER_TUNGSTEN.get(), NtmBlocks.ORE_NETHER_SULFUR.get(), NtmBlocks.ORE_NETHER_FIRE.get(),
                            NtmBlocks.ORE_NETHER_COBALT.get(), NtmBlocks.ORE_NETHER_COAL.get(), NtmBlocks.ORE_NETHER_SMOLDERING.get())) {
                        check(b.defaultBlockState().getDestroySpeed(helper.getLevel(), BlockPos.ZERO) == 0.4F, BuiltInRegistries.BLOCK.getKey(b) + " hardness " + b.defaultBlockState().getDestroySpeed(helper.getLevel(), BlockPos.ZERO));
                        check(b.getExplosionResistance() == resistance, BuiltInRegistries.BLOCK.getKey(b) + " resistance " + b.getExplosionResistance() + ", nether uranium " + resistance);
                        // silk touch keeps the block
                        for(int i = 0; i < 20; i++) {
                            Map<Item, Integer> d = roll(helper, rel, b, silk);
                            check(d.size() == 1 && d.getOrDefault(b.asItem(), 0) == 1, BuiltInRegistries.BLOCK.getKey(b) + " silk touch dropped " + d);
                        }
                    }
                    // only nether coal and smoldering netherrack set a light level (ModBlocks.java:1258-1259)
                    for(Block b : List.of(NtmBlocks.ORE_NETHER_TUNGSTEN.get(), NtmBlocks.ORE_NETHER_SULFUR.get(), NtmBlocks.ORE_NETHER_FIRE.get(), NtmBlocks.ORE_NETHER_COBALT.get())) {
                        check(b.defaultBlockState().getLightEmission() == 0, BuiltInRegistries.BLOCK.getKey(b) + " emits light " + b.defaultBlockState().getLightEmission());
                    }

                    // tungsten: itself, also with fortune
                    for(ItemStack tool : List.of(plain, fortune)) for(int i = 0; i < 50; i++) {
                        Map<Item, Integer> d = roll(helper, rel, NtmBlocks.ORE_NETHER_TUNGSTEN.get(), tool);
                        check(d.size() == 1 && d.getOrDefault(NtmBlocks.ORE_NETHER_TUNGSTEN.get().asItem(), 0) == 1, "nether tungsten dropped " + d);
                    }
                    // sulfur 2..4, every value seen
                    int[] seen = range(helper, rel, NtmBlocks.ORE_NETHER_SULFUR.get(), plain, NtmItems.SULFUR.get(), 600);
                    check(seen[0] == 2 && seen[1] == 4, "nether sulfur dropped " + seen[0] + ".." + seen[1] + " sulfur, original 2..4");
                    int[] seenF = range(helper, rel, NtmBlocks.ORE_NETHER_SULFUR.get(), fortune, NtmItems.SULFUR.get(), 600);
                    check(seenF[0] >= 2 && seenF[1] > 4 && seenF[1] <= 16, "nether sulfur with fortune III dropped " + seenF[0] + ".." + seenF[1] + ", original 2..16 with some above 4");
                    // cobalt 5..12
                    int[] co = range(helper, rel, NtmBlocks.ORE_NETHER_COBALT.get(), plain, NtmItems.FRAGMENT_COBALT.get(), 1000);
                    check(co[0] == 5 && co[1] == 12, "nether cobalt dropped " + co[0] + ".." + co[1] + " fragments, original 5..12");
                    int[] coF = range(helper, rel, NtmBlocks.ORE_NETHER_COBALT.get(), fortune, NtmItems.FRAGMENT_COBALT.get(), 600);
                    check(coF[0] >= 5 && coF[1] > 12 && coF[1] <= 48, "nether cobalt with fortune III dropped " + coF[0] + ".." + coF[1]);
                    // coal: one coal_infernal, fortune bonus
                    int[] coal = range(helper, rel, NtmBlocks.ORE_NETHER_COAL.get(), plain, NtmItems.COAL_INFERNAL.get(), 200);
                    check(coal[0] == 1 && coal[1] == 1, "nether coal dropped " + coal[0] + ".." + coal[1] + " infernal coal, original 1");
                    int[] coalF = range(helper, rel, NtmBlocks.ORE_NETHER_COAL.get(), fortune, NtmItems.COAL_INFERNAL.get(), 400);
                    check(coalF[0] >= 1 && coalF[1] > 1 && coalF[1] <= 4, "nether coal with fortune III dropped " + coalF[0] + ".." + coalF[1]);
                    // smoldering: one powder_fire, no fortune bonus
                    for(ItemStack tool : List.of(plain, fortune)) {
                        int[] sm = range(helper, rel, NtmBlocks.ORE_NETHER_SMOLDERING.get(), tool, NtmItems.POWDER_FIRE.get(), 300);
                        check(sm[0] == 1 && sm[1] == 1, "smoldering netherrack dropped " + sm[0] + ".." + sm[1] + " powder_fire with " + tool);
                    }
                    // phosphorus: 1 in 10 ingot_phosphorus, else powder_fire, one item each
                    int ingots = 0, powders = 0, rolls = 2000;
                    for(int i = 0; i < rolls; i++) {
                        Map<Item, Integer> d = roll(helper, rel, NtmBlocks.ORE_NETHER_FIRE.get(), plain);
                        check(d.size() == 1, "nether phosphorus dropped " + d);
                        if(d.getOrDefault(NtmItems.INGOT_PHOSPHORUS.get(), 0) == 1) ingots++;
                        else if(d.getOrDefault(NtmItems.POWDER_FIRE.get(), 0) == 1) powders++;
                        else check(false, "nether phosphorus dropped " + d);
                    }
                    // Binomial(2000, 0.1): mean 200, sd 13.4; 140..260 is about +-4.5 sd
                    check(ingots >= 140 && ingots <= 260, "nether phosphorus: " + ingots + " phosphorus ingots in " + rolls + " rolls, original 1 in 10");
                    int[] fireF = new int[] { Integer.MAX_VALUE, 0 };
                    for(int i = 0; i < 400; i++) {
                        Map<Item, Integer> d = roll(helper, rel, NtmBlocks.ORE_NETHER_FIRE.get(), fortune);
                        int c = d.values().stream().mapToInt(Integer::intValue).sum();
                        fireF[0] = Math.min(fireF[0], c);
                        fireF[1] = Math.max(fireF[1], c);
                    }
                    check(fireF[0] >= 1 && fireF[1] > 1 && fireF[1] <= 4, "nether phosphorus with fortune III dropped " + fireF[0] + ".." + fireF[1]);
                    // unchanged: the existing nether ores and trixite drop themselves
                    for(Block b : List.of(NtmBlocks.ORE_NETHER_URANIUM.get(), NtmBlocks.ORE_NETHER_URANIUM_SCORCHED.get(), NtmBlocks.ORE_NETHER_PLUTONIUM.get(), NtmBlocks.ORE_TIKITE.get())) {
                        Map<Item, Integer> d = roll(helper, rel, b, plain);
                        check(d.size() == 1 && d.getOrDefault(b.asItem(), 0) == 1, BuiltInRegistries.BLOCK.getKey(b) + " dropped " + d);
                    }
                    LOGGER.info("{} loot: sulfur {}..{} (fortune {}..{}), cobalt {}..{} (fortune {}..{}), coal 1 (fortune {}..{}), phosphorus ingots {}/{} powder {}, smoldering 1, tungsten self, silk self",
                            TAG, seen[0], seen[1], seenF[0], seenF[1], co[0], co[1], coF[0], coF[1], coalF[0], coalF[1], ingots, rolls, powders);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "loot"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 9. processing

    // SmeltingRecipes.java:33-35,39,46; CentrifugeRecipes.java:102-106 (W.ore(), lbs off -> 1 tungsten powder first), :138-142 (PU.ore() -> gravel),
    // :192-196 (ore_nether_fire), :198-202 (CO.ore()); OreDictManager.java:382,400,430 (nether tungsten / cobalt / sulfur in W / CO / S ore);
    // ShredderRecipes.java:66 (ore -> 2 dust), :150, :199; CrystallizerRecipes.java:71,74,81 (S / W / CO ore), :89-90, :104, :314-316 (the
    // two-argument overload: peroxide 500); FuelHandler.java:41 (4800)
    @GameTest(template = TEMPLATE, batch = "hbm28a_processing", timeoutTicks = 100)
    public static void processing(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    // furnace
                    smelts(helper, NtmBlocks.ORE_NETHER_TUNGSTEN.get(), NtmItems.INGOT_TUNGSTEN.get(), "ingot_tungsten_from_smelting_ore_nether_tungsten");
                    smelts(helper, NtmBlocks.ORE_NETHER_COBALT.get(), NtmItems.INGOT_COBALT.get(), "ingot_cobalt_from_smelting_ore_nether_cobalt");
                    smelts(helper, NtmBlocks.ORE_NETHER_URANIUM.get(), NtmItems.INGOT_URANIUM.get(), "ingot_uranium_from_smelting_ore_nether_uranium");
                    smelts(helper, NtmBlocks.ORE_NETHER_URANIUM_SCORCHED.get(), NtmItems.INGOT_URANIUM.get(), "ingot_uranium_from_smelting_ore_nether_uranium_scorched");
                    smelts(helper, NtmBlocks.ORE_NETHER_PLUTONIUM.get(), NtmItems.INGOT_PLUTONIUM.get(), "ingot_plutonium_from_smelting_ore_nether_plutonium");
                    // the existing registry ids
                    for(String path : List.of("ore_nether_uranium", "ore_nether_uranium_scorched", "ore_nether_plutonium", "ore_nether_schrabidium", "ore_tikite",
                            "ore_nether_tungsten", "ore_nether_sulfur", "ore_nether_fire", "ore_nether_coal", "ore_nether_smoldering", "ore_nether_cobalt")) {
                        check(BuiltInRegistries.BLOCK.containsKey(id(path)) && BuiltInRegistries.ITEM.containsKey(id(path)), "no block / item " + path);
                    }
                    check(BuiltInRegistries.ITEM.containsKey(id("coal_infernal")) && BuiltInRegistries.ITEM.containsKey(id("hand_drill")) && BuiltInRegistries.ITEM.containsKey(id("hand_drill_desh")), "a new item id is missing");

                    // centrifuge
                    centrifuge(NtmBlocks.ORE_NETHER_FIRE.get(), List.of(s(Items.BLAZE_POWDER, 2), s(NtmItems.POWDER_FIRE.get(), 2), s(NtmItems.INGOT_PHOSPHORUS.get(), 1), s(Blocks.NETHERRACK, 1)));
                    centrifuge(NtmBlocks.ORE_NETHER_PLUTONIUM.get(), List.of(s(NtmItems.POWDER_PLUTONIUM.get(), 1), s(NtmItems.POWDER_PLUTONIUM.get(), 1), s(NtmItems.NUGGET_POLONIUM.get(), 3), s(Blocks.GRAVEL, 1)));
                    centrifuge(NtmBlocks.ORE_NETHER_TUNGSTEN.get(), List.of(s(NtmItems.POWDER_TUNGSTEN.get(), 1), s(NtmItems.POWDER_TUNGSTEN.get(), 1), s(NtmItems.POWDER_IRON.get(), 1), s(Blocks.GRAVEL, 1)));
                    centrifuge(NtmBlocks.ORE_NETHER_COBALT.get(), List.of(s(NtmItems.POWDER_COBALT.get(), 2), s(NtmItems.POWDER_IRON.get(), 1), s(NtmItems.POWDER_COPPER.get(), 1), s(Blocks.GRAVEL, 1)));
                    check(CentrifugeRecipes.getOutput(new ItemStack(NtmBlocks.ORE_NETHER_SULFUR.get())).length == 0, "nether sulfur has a centrifuge row (none in the original)");

                    // shredder
                    shreds(NtmBlocks.ORE_NETHER_FIRE.get(), NtmItems.POWDER_FIRE.get(), 6);
                    shreds(NtmItems.COAL_INFERNAL.get(), NtmItems.POWDER_COAL.get(), 2);
                    shreds(NtmBlocks.ORE_NETHER_TUNGSTEN.get(), NtmItems.POWDER_TUNGSTEN.get(), 2);
                    shreds(NtmBlocks.ORE_NETHER_SULFUR.get(), NtmItems.SULFUR.get(), 2);
                    shreds(NtmBlocks.ORE_NETHER_COBALT.get(), NtmItems.POWDER_COBALT.get(), 2);
                    // no original row: ore_nether_coal and smoldering netherrack are in no ore dictionary entry and have no explicit row
                    check(!ShredderRecipes.hasRecipe(new ItemStack(NtmBlocks.ORE_NETHER_COAL.get())), "ore_nether_coal has a shredder row: " + ShredderRecipes.getShredderResult(new ItemStack(NtmBlocks.ORE_NETHER_COAL.get())));
                    check(!ShredderRecipes.hasRecipe(new ItemStack(NtmBlocks.ORE_NETHER_SMOLDERING.get())), "ore_nether_smoldering has a shredder row: " + ShredderRecipes.getShredderResult(new ItemStack(NtmBlocks.ORE_NETHER_SMOLDERING.get())));

                    // crystallizer (live table and the default table)
                    crystallizes(NtmBlocks.ORE_NETHER_FIRE.get(), Fluids.PEROXIDE, NtmItems.CRYSTAL_PHOSPHORUS.get(), 600, 0.05F);
                    crystallizes(NtmBlocks.ORE_TIKITE.get(), Fluids.SULFURIC_ACID, NtmItems.CRYSTAL_TRIXITE.get(), 600, 0.05F);
                    crystallizes(NtmBlocks.ORE_NETHER_SULFUR.get(), Fluids.PEROXIDE, NtmItems.CRYSTAL_SULFUR.get(), 600, 0.05F);
                    crystallizes(NtmBlocks.ORE_NETHER_TUNGSTEN.get(), Fluids.SULFURIC_ACID, NtmItems.CRYSTAL_TUNGSTEN.get(), 600, 0.05F);
                    crystallizes(NtmBlocks.ORE_NETHER_COBALT.get(), Fluids.SULFURIC_ACID, NtmItems.CRYSTAL_COBALT.get(), 600, 0.05F);
                    crystallizes(NtmItems.COAL_INFERNAL.get(), Fluids.PEROXIDE, NtmItems.SOLID_FUEL.get(), 100, 0F);
                    check(CrystallizerRecipes.getOutput(new ItemStack(NtmBlocks.ORE_NETHER_FIRE.get()), Fluids.SULFURIC_ACID) == null, "nether phosphorus crystallizes with sulfuric acid");
                    check(CrystallizerRecipes.getOutput(new ItemStack(NtmBlocks.ORE_TIKITE.get()), Fluids.PEROXIDE) == null, "trixite crystallizes with peroxide");
                    check(CrystallizerRecipes.getDefaultRecipes().size() == 65, "the default crystallizer table has " + CrystallizerRecipes.getDefaultRecipes().size() + " rows, expected 65 (47 + 6, Goal28A decision; + 7, Goal28B; + 5, Goal28D)");

                    // fuel
                    ItemStack infernal = new ItemStack(NtmItems.COAL_INFERNAL.get());
                    check(infernal.getBurnTime(RecipeType.SMELTING) == 4800, "coal_infernal burns " + infernal.getBurnTime(RecipeType.SMELTING) + " ticks in a furnace, original 4800");
                    check(infernal.getBurnTime(null) == 4800, "coal_infernal burn time (no recipe type) " + infernal.getBurnTime(null));
                    LOGGER.info("{} processing: smelting, centrifuge, shredder, crystallizer (53 default rows) and fuel 4800", TAG);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "processing"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 10. hand drill

    // ModItems.java:3711-3712 ItemTooling(HAND_DRILL, 100) / (HAND_DRILL, 0); ToolRecipes.java:141-142 (" D","S "," S": dura steel + stick; desh +
    // any plastic ingot); ItemTooling.java:26-41 (wear only when onScrew is true); FoundryOutlet.java:123-144 (a right-click that is not sneaking
    // toggles invertRedstone whatever the held item except scraps), :147-169 (screwdriver / hand drill, both return false)
    @GameTest(template = TEMPLATE, batch = "hbm28a_hand_drill", timeoutTicks = 100)
    public static void hand_drill(GameTestHelper helper) {
        BlockPos out = new BlockPos(5, 3, 5);
        helper.setBlock(out, NtmBlocks.FOUNDRY_OUTLET.get().defaultBlockState().setValue(FoundryOutletBlock.FACING, Direction.EAST));
        helper.startSequence()
                .thenIdle(1)
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    ItemStack drill = new ItemStack(NtmItems.HAND_DRILL.get()), desh = new ItemStack(NtmItems.HAND_DRILL_DESH.get());
                    check(drill.getMaxDamage() == 100 && drill.isDamageableItem(), "hand drill max damage " + drill.getMaxDamage());
                    check(desh.getMaxDamage() == 0 && !desh.isDamageableItem(), "desh hand drill max damage " + desh.getMaxDamage());
                    check(drill.getMaxStackSize() == 1 && desh.getMaxStackSize() == 1, "hand drill stack sizes " + drill.getMaxStackSize() + " / " + desh.getMaxStackSize());
                    boolean listed = false, listedDesh = false;
                    for(ItemStack st : ToolType.HAND_DRILL.stacksForDisplay) {
                        listed |= st.is(NtmItems.HAND_DRILL.get());
                        listedDesh |= st.is(NtmItems.HAND_DRILL_DESH.get());
                    }
                    check(listed && listedDesh, "the hand drills are not registered as HAND_DRILL tools");

                    // recipes
                    ItemStack dura = new ItemStack(NtmItems.INGOT_DURA_STEEL.get()), stick = new ItemStack(Items.STICK), deshIngot = new ItemStack(NtmItems.INGOT_DESH.get());
                    crafts(helper, "hand_drill", grid(dura, stick), NtmItems.HAND_DRILL.get());
                    TagKey<Item> plastic = ItemTags.create(ResourceLocation.fromNamespaceAndPath("ntm", "ingots_plastic"));
                    int plastics = 0;
                    for(Holder<Item> h : BuiltInRegistries.ITEM.getTagOrEmpty(plastic)) {
                        crafts(helper, "hand_drill_desh", grid(deshIngot, new ItemStack(h.value())), NtmItems.HAND_DRILL_DESH.get());
                        plastics++;
                    }
                    check(plastics > 0, "the ntm:ingots_plastic tag is empty");
                    notCrafting(helper, grid(dura, deshIngot), NtmItems.HAND_DRILL.get(), NtmItems.HAND_DRILL_DESH.get());

                    // the outlet: the block's onScrew toggles invertFilter and returns false
                    BlockPos abs = helper.absolutePos(out);
                    FoundryOutletBlockEntity o = SmokeTestSupport.blockEntity(helper, out, FoundryOutletBlockEntity.class);
                    Player player = helper.makeMockPlayer(GameType.SURVIVAL);
                    IToolable tool = (IToolable) NtmBlocks.FOUNDRY_OUTLET.get();
                    check(!o.invertFilter && !o.invertRedstone, "fresh outlet invertFilter " + o.invertFilter + " invert " + o.invertRedstone);
                    check(!tool.onScrew(level, player, abs, Direction.UP, ToolType.HAND_DRILL), "onScrew with HAND_DRILL returned true");
                    check(o.invertFilter, "onScrew with HAND_DRILL did not toggle invertFilter");
                    check(!tool.onScrew(level, player, abs, Direction.UP, ToolType.HAND_DRILL) && !o.invertFilter, "a second onScrew did not toggle back");

                    // the item path (a sneaking player: 1.7.10 and 1.21 both skip the block's right-click and call the item): toggles, PASS, no wear
                    player.setShiftKeyDown(true);
                    InteractionResult r = useOn(player, drill, abs);
                    check(r == InteractionResult.PASS && o.invertFilter && drill.getDamageValue() == 0, "hand drill on the outlet: " + r + ", invertFilter " + o.invertFilter + ", damage " + drill.getDamageValue());
                    r = useOn(player, desh, abs);
                    check(r == InteractionResult.PASS && !o.invertFilter && desh.getDamageValue() == 0, "desh hand drill on the outlet: " + r + ", invertFilter " + o.invertFilter);
                    check(!o.invertRedstone, "the item path toggled invertRedstone");

                    // not sneaking: the block's right-click comes first and toggles invertRedstone, the filter inversion stays
                    player.setShiftKeyDown(false);
                    player.setItemInHand(InteractionHand.MAIN_HAND, drill);
                    BlockState state = level.getBlockState(abs);
                    ItemInteractionResult used = state.useItemOn(drill, level, player, InteractionHand.MAIN_HAND, new BlockHitResult(Vec3.atCenterOf(abs), Direction.UP, abs, false));
                    check(used.consumesAction() && o.invertRedstone && !o.invertFilter, "right-click with the hand drill: " + used + ", invert " + o.invertRedstone + ", invertFilter " + o.invertFilter);
                    LOGGER.info("{} hand_drill: durability 100 / desh none, recipes ({} plastic ingots), outlet onScrew toggles invertFilter and returns false, item PASS without wear, NEO block result false", TAG, plastics);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "hand_drill"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 11. fluid burner

    // TileEntityHeaterOilburner.java (4f5924e2b): :42-48 burnRate 1, maxBurnRate 10, maxHeatEnergy 500_000; :74-81 slot 3 overdrive (max level 3,
    // :130-133), maxBurnRate 10 * (od + 1), maxHeatEnergy 500_000 * (od + 1), burnRate and heat clamped down; :106 no cooling at the cap;
    // :166,:175 NBT "setting"; HeaterOilburner.java: no IToolable any more. NEO decisions: the control key stays "setting" and the server
    // clamps it to 1..maxBurnRate; slot 3 accepts only overdrive upgrades.
    @GameTest(template = TEMPLATE, batch = "hbm28a_fluid_burner", timeoutTicks = 200)
    public static void fluid_burner(GameTestHelper helper) {
        BlockPos core = new BlockPos(5, 1, 5);
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.HEATER_OILBURNER.get(), core, Direction.NORTH);
        helper.startSequence()
                .thenIdle(2)
                .thenExecute(guard(() -> {
                    HeaterOilburnerBlockEntity be = burner(helper, core);
                    check(be.slots.size() == 4 && HeaterOilburnerBlockEntity.SLOT_UPGRADE == 3, "burner slots " + be.slots.size() + ", upgrade slot " + HeaterOilburnerBlockEntity.SLOT_UPGRADE);
                    for(Direction side : Direction.values()) {
                        check(java.util.Arrays.equals(be.getSlotsForFace(side), new int[] {0, 1, 2}), "automation reaches burner slots " + java.util.Arrays.toString(be.getSlotsForFace(side)) + " from " + side);
                    }
                    check(be.maxHeatEnergy == 500_000 && be.maxBurnRate == 10 && be.setting == 1, "fresh burner: max heat " + be.maxHeatEnergy + ", max rate " + be.maxBurnRate + ", setting " + be.setting);
                    control(be, 7);
                    check(be.setting == 7, "setting 7 gave " + be.setting);
                    control(be, 0);
                    check(be.setting == 1, "setting 0 gave " + be.setting + " (NEO server clamp)");
                    control(be, 99);
                    check(be.setting == 10, "setting 99 gave " + be.setting + " (NEO server clamp to maxBurnRate 10)");
                    // slot 3: overdrive only (NEO); the original's plain Slot would take anything but the upgrade manager reads only overdrive
                    check(be.canPlaceItem(3, new ItemStack(NtmItems.UPGRADE_OVERDRIVE_1.get())), "slot 3 refuses overdrive 1");
                    check(!be.canPlaceItem(3, new ItemStack(NtmItems.UPGRADE_SPEED_1.get())), "slot 3 accepts a speed upgrade");
                    check(!be.canPlaceItem(3, new ItemStack(Items.STONE)), "slot 3 accepts stone");
                    be.slots.set(3, new ItemStack(NtmItems.UPGRADE_OVERDRIVE_1.get()));
                }))
                .thenIdle(1)
                .thenExecute(guard(() -> {
                    HeaterOilburnerBlockEntity be = burner(helper, core);
                    check(be.maxBurnRate == 20 && be.maxHeatEnergy == 1_000_000, "overdrive 1: " + be.maxBurnRate + " / " + be.maxHeatEnergy);
                    be.slots.set(3, new ItemStack(NtmItems.UPGRADE_OVERDRIVE_2.get()));
                }))
                .thenIdle(1)
                .thenExecute(guard(() -> {
                    HeaterOilburnerBlockEntity be = burner(helper, core);
                    check(be.maxBurnRate == 30 && be.maxHeatEnergy == 1_500_000, "overdrive 2: " + be.maxBurnRate + " / " + be.maxHeatEnergy);
                    be.slots.set(3, new ItemStack(NtmItems.UPGRADE_OVERDRIVE_3.get()));
                }))
                .thenIdle(1)
                .thenExecute(guard(() -> {
                    HeaterOilburnerBlockEntity be = burner(helper, core);
                    check(be.maxBurnRate == 40 && be.maxHeatEnergy == 2_000_000, "overdrive 3: " + be.maxBurnRate + " / " + be.maxHeatEnergy);
                    control(be, 35);
                    check(be.setting == 35, "setting 35 with overdrive 3 gave " + be.setting);
                    control(be, 99);
                    check(be.setting == 40, "setting 99 with overdrive 3 gave " + be.setting);
                    control(be, 35);
                    be.heatEnergy = 1_900_000;
                    // removing the upgrade: the next tick clamps rate and heat (:80-81) and the capped heat does not cool (:106)
                    be.slots.set(3, ItemStack.EMPTY);
                }))
                .thenIdle(1)
                .thenExecute(guard(() -> {
                    HeaterOilburnerBlockEntity be = burner(helper, core);
                    check(be.maxBurnRate == 10 && be.maxHeatEnergy == 500_000, "upgrade removed: " + be.maxBurnRate + " / " + be.maxHeatEnergy);
                    check(be.setting == 10 && be.heatEnergy == 500_000, "upgrade removed: setting " + be.setting + ", heat " + be.heatEnergy + "; expected 10 and 500000");

                    // NBT round trip
                    HolderLookup.Provider reg = helper.getLevel().registryAccess();
                    control(be, 7);
                    CompoundTag saved = be.saveWithoutMetadata(reg);
                    check(saved.getTagType("setting") == Tag.TAG_INT && saved.getInt("setting") == 7, "saved setting " + saved.get("setting"));
                    HeaterOilburnerBlockEntity loaded = new HeaterOilburnerBlockEntity(be.getBlockPos(), be.getBlockState());
                    loaded.loadWithComponents(saved, reg);
                    check(loaded.setting == 7 && loaded.heatEnergy == be.heatEnergy, "loaded setting " + loaded.setting + ", heat " + loaded.heatEnergy);

                    // an old 3-slot save (NEO before Goal28A: int "setting", "heatEnergy", "isOn") and the original's byte "setting"
                    for(boolean asByte : new boolean[] { false, true }) {
                        CompoundTag old = new CompoundTag();
                        NonNullList<ItemStack> three = NonNullList.withSize(3, ItemStack.EMPTY);
                        three.set(1, new ItemStack(Items.BUCKET));
                        ContainerHelper.saveAllItems(old, three, reg);
                        if(asByte) old.putByte("setting", (byte) 5); else old.putInt("setting", 5);
                        old.putInt("heatEnergy", 80_000);
                        old.putBoolean("isOn", true);
                        HeaterOilburnerBlockEntity fromOld = new HeaterOilburnerBlockEntity(be.getBlockPos(), be.getBlockState());
                        fromOld.loadWithComponents(old, reg);
                        check(fromOld.slots.size() == 4 && fromOld.slots.get(1).is(Items.BUCKET) && fromOld.slots.get(3).isEmpty(), "old save slots " + fromOld.slots);
                        check(fromOld.setting == 5 && fromOld.heatEnergy == 80_000 && fromOld.isOn, "old save (" + (asByte ? "byte" : "int") + " setting): setting " + fromOld.setting + ", heat " + fromOld.heatEnergy + ", on " + fromOld.isOn);
                    }

                    // an old save with a rate above the limit: the live burner reads it and the next tick clamps it to maxBurnRate (:80)
                    CompoundTag high = be.saveWithoutMetadata(reg);
                    high.putInt("setting", 100);
                    high.putBoolean("isOn", false);
                    be.loadWithComponents(high, reg);
                    check(be.setting <= 40, "setting 100 loaded as " + be.setting);
                }))
                .thenIdle(1)
                .thenExecute(guard(() -> {
                    HeaterOilburnerBlockEntity be = burner(helper, core);
                    check(be.setting == 10, "after a tick the loaded rate is " + be.setting + ", expected 10");

                    // the screwdriver no longer configures the burner (4f5924e2b HeaterOilburner.java): PASS, no wear, setting unchanged
                    check(!(NtmBlocks.HEATER_OILBURNER.get() instanceof IToolable), "the fluid burner is still an IToolable");
                    Player player = helper.makeMockPlayer(GameType.SURVIVAL);
                    ItemStack driver = new ItemStack(NtmItems.SCREWDRIVER.get());
                    control(be, 4);
                    InteractionResult r = useOn(player, driver, helper.absolutePos(core));
                    check(r == InteractionResult.PASS && driver.getDamageValue() == 0 && be.setting == 4, "screwdriver on the burner: " + r + ", damage " + driver.getDamageValue() + ", setting " + be.setting);
                    LOGGER.info("{} fluid_burner: 500000 / 10 base, overdrive 1-3 -> 20/30/40 and 1M/1.5M/2M, clamp on removal, setting saved, old saves load, screwdriver passes", TAG);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "fluid_burner"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 12. GenericRecipe icon

    // GenericRecipe.java:103-108 (4f5924e2b): setIconToFirstIngredient calls setIcon, which sets writeIcon, so the template file writes the icon
    @GameTest(template = TEMPLATE, batch = "hbm28a_generic_recipe_icon", timeoutTicks = 100)
    public static void generic_recipe_icon(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    GenericRecipe recipe = new GenericRecipe("hbm28a.icon_test").setup(100, 1000).inputItems(new ComparableStack(NtmItems.INGOT_DESH.get(), 3), new ComparableStack(Items.STICK, 1));
                    check(!recipe.writeIcon, "a fresh recipe writes its icon");
                    recipe.setIconToFirstIngredient();
                    ItemStack first = recipe.inputItem[0].extractForJEI().get(0);
                    check(recipe.writeIcon, "setIconToFirstIngredient did not set writeIcon");
                    check(ItemStack.matches(recipe.getIcon(), first) && recipe.getIcon().is(NtmItems.INGOT_DESH.get()), "icon " + recipe.getIcon() + ", first ingredient stack " + first);
                    String json;
                    try {
                        StringWriter sw = new StringWriter();
                        JsonWriter writer = new JsonWriter(sw);
                        writer.beginObject();
                        AssemblyMachineRecipes.INSTANCE.writeRecipe(recipe, writer);
                        writer.endObject();
                        writer.close();
                        json = sw.toString();
                    } catch(java.io.IOException e) {
                        throw new IllegalStateException(e);
                    }
                    check(json.contains("\"icon\"") && json.contains("hbmsntm:ingot_desh"), "the template entry has no icon: " + json);
                    GenericRecipe noInput = new GenericRecipe("hbm28a.icon_none").setIconToFirstIngredient();
                    check(!noInput.writeIcon, "a recipe without inputs writes an icon");
                    LOGGER.info("{} generic_recipe_icon: writeIcon true, icon {}, entry {}", TAG, recipe.getIcon(), json.replace('\n', ' '));
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "generic_recipe_icon"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 13. scraps entity name

    // NEO decision (Goal28A main notes): vanilla ItemEntity.getName() translates the stack's description id without arguments, so the scraps
    // description id per stack is the generic key; the hover name still carries the material
    @GameTest(template = TEMPLATE, batch = "hbm28a_scraps_name", timeoutTicks = 100)
    public static void scraps_name(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ItemStack scraps = CopperScrapsItem.create(new Mats.MaterialStack(Mats.MAT_IRON, 72));
                    ItemEntity entity = new ItemEntity(helper.getLevel(), helper.absoluteVec(new Vec3(4, 2, 4)).x, helper.absoluteVec(new Vec3(4, 2, 4)).y, helper.absoluteVec(new Vec3(4, 2, 4)).z, scraps);
                    Component name = entity.getName();
                    check(name.getContents() instanceof TranslatableContents t && t.getKey().equals("item.hbmsntm.scraps.generic") && t.getArgs().length == 0,
                            "the scraps entity name is " + name.getContents());
                    Component hover = scraps.getHoverName();
                    check(hover.getContents() instanceof TranslatableContents t2 && t2.getKey().equals("item.hbmsntm.scraps") && t2.getArgs().length == 1,
                            "the scraps hover name is " + hover.getContents());
                    LOGGER.info("{} scraps_name: entity {}, hover {}", TAG, name.getContents(), hover.getContents());
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "scraps_name"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- helpers

    private static ResourceLocation id(String path) {
        return ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path);
    }

    private static String describe(Object o) {
        return o == null ? "null" : o.getClass().getSimpleName();
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

    /** The placed features the modifier adds to a fresh copy of the biome's original info in the given phase, by key. */
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

    /** Fills relative x 1..15, y 1..11, z 1..15 with the target and a sprinkle of another block; returns the absolute positions and states. */
    private static Map<BlockPos, BlockState> fillCube(GameTestHelper helper, Block target, Block mix) {
        Map<BlockPos, BlockState> states = new HashMap<>();
        for(int x = 1; x <= 15; x++) for(int y = 1; y <= 11; y++) for(int z = 1; z <= 15; z++) {
            Block b = (x * 7 + y * 3 + z * 5) % 11 == 0 ? mix : (x * 3 + y * 5 + z) % 13 == 0 ? Blocks.STONE : target;
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
        return out;
    }

    private static void clearAround(GameTestHelper helper, BlockPos rel) {
        helper.setBlock(rel, Blocks.AIR);
        for(Direction d : Direction.values()) helper.setBlock(rel.relative(d), Blocks.AIR);
    }

    /** The survival steps of ServerPlayerGameMode.destroyBlock for a mock player holding a stone pickaxe. */
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

    private static void smelts(GameTestHelper helper, ItemLike in, ItemLike out, String recipeId) {
        ServerLevel level = helper.getLevel();
        SingleRecipeInput input = new SingleRecipeInput(new ItemStack(in));
        Optional<RecipeHolder<SmeltingRecipe>> holder = level.getRecipeManager().getRecipeFor(RecipeType.SMELTING, input, level);
        check(holder.isPresent(), in.asItem() + ": no smelting recipe");
        check(holder.get().id().equals(id(recipeId)), in.asItem() + ": smelting recipe " + holder.get().id() + ", expected " + id(recipeId));
        ItemStack result = holder.get().value().assemble(input, level.registryAccess());
        check(result.is(out.asItem()) && result.getCount() == 1, in.asItem() + " smelts to " + result);
    }

    private static void centrifuge(Block in, List<ItemStack> want) {
        ItemStack[] got = CentrifugeRecipes.getOutput(new ItemStack(in));
        boolean same = got.length == want.size();
        for(int i = 0; same && i < got.length; i++) same = got[i].is(want.get(i).getItem()) && got[i].getCount() == want.get(i).getCount();
        check(same, BuiltInRegistries.BLOCK.getKey(in) + " centrifuges to " + List.of(got) + ", original " + want);
    }

    private static void shreds(ItemLike in, Item out, int count) {
        ItemStack stack = new ItemStack(in);
        check(ShredderRecipes.hasRecipe(stack), BuiltInRegistries.ITEM.getKey(in.asItem()) + " has no shredder row");
        ItemStack result = ShredderRecipes.getShredderResult(stack);
        check(result.is(out) && result.getCount() == count, BuiltInRegistries.ITEM.getKey(in.asItem()) + " shreds to " + result + ", original " + count + " x " + BuiltInRegistries.ITEM.getKey(out));
    }

    private static void crystallizes(ItemLike in, com.hbm.inventory.fluid.FluidType acid, Item out, int duration, float productivity) {
        String label = BuiltInRegistries.ITEM.getKey(in.asItem()).toString();
        for(List<CrystallizerRecipe> table : List.of(CrystallizerRecipes.getJeiRecipes(), CrystallizerRecipes.getDefaultRecipes())) {
            CrystallizerRecipe r = CrystallizerRecipes.getOutput(table, new ItemStack(in), acid);
            check(r != null, label + " has no crystallizer row with " + acid.getInternalName());
            check(r.output.is(out) && r.output.getCount() == 1, label + " crystallizes to " + r.output);
            check(r.acidAmount() == 500 && r.itemAmount() == 1, label + " consumes " + r.itemAmount() + " item(s) and " + r.acidAmount() + " mB, original 1 and 500");
            check(r.duration == duration && r.productivity == productivity, label + " duration " + r.duration + " productivity " + r.productivity + ", original " + duration + " / " + productivity);
        }
    }

    private static CraftingInput grid(ItemStack top, ItemStack sticks) {
        // " D" / "S " / " S"
        return CraftingInput.of(2, 3, List.of(ItemStack.EMPTY, top.copy(), sticks.copy(), ItemStack.EMPTY, ItemStack.EMPTY, sticks.copy()));
    }

    private static void crafts(GameTestHelper helper, String recipeId, CraftingInput input, Item out) {
        ServerLevel level = helper.getLevel();
        Optional<RecipeHolder<CraftingRecipe>> first = level.getRecipeManager().getRecipeFor(RecipeType.CRAFTING, input, level);
        check(first.isPresent(), recipeId + ": the grid " + input.items() + " crafts nothing");
        check(first.get().id().equals(id(recipeId)), recipeId + ": the grid matches " + first.get().id());
        ItemStack result = first.get().value().assemble(input, level.registryAccess());
        check(result.is(out) && result.getCount() == 1, recipeId + " yields " + result);
    }

    private static void notCrafting(GameTestHelper helper, CraftingInput input, Item... outs) {
        ServerLevel level = helper.getLevel();
        for(RecipeHolder<CraftingRecipe> holder : level.getRecipeManager().getRecipesFor(RecipeType.CRAFTING, input, level)) {
            ItemStack result = holder.value().assemble(input, level.registryAccess());
            for(Item out : outs) check(!result.is(out), holder.id() + " yields " + result + " from a wrong grid");
        }
    }

    private static InteractionResult useOn(Player player, ItemStack stack, BlockPos abs) {
        player.setItemInHand(InteractionHand.MAIN_HAND, stack);
        BlockHitResult hit = new BlockHitResult(Vec3.atCenterOf(abs), Direction.UP, abs, false);
        return stack.getItem().useOn(new UseOnContext(player, InteractionHand.MAIN_HAND, hit));
    }

    private static HeaterOilburnerBlockEntity burner(GameTestHelper helper, BlockPos core) {
        return SmokeTestSupport.blockEntity(helper, core, HeaterOilburnerBlockEntity.class);
    }

    /** The slider payload as the GUI sends it (CompoundTagControl with "setting"), handled on the server. */
    private static void control(HeaterOilburnerBlockEntity be, int value) {
        CompoundTag tag = new CompoundTag();
        tag.putInt("setting", value);
        be.receiveControl(tag);
    }

    private static void discardItems(GameTestHelper helper) {
        Vec3 abs = helper.absoluteVec(new Vec3(8.5, 1, 8.5));
        for(ItemEntity entity : helper.getLevel().getEntitiesOfClass(ItemEntity.class, new AABB(abs, abs).inflate(10D))) entity.discard();
    }
}
