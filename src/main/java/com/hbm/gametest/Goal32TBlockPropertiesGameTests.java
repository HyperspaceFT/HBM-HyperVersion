package com.hbm.gametest;

import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.main.NuclearTechMod;
import com.mojang.authlib.GameProfile;
import com.mojang.logging.LogUtils;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.tags.BlockTags;
import net.minecraft.tags.TagKey;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.common.Tags;
import net.neoforged.neoforge.common.util.FakePlayer;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import org.slf4j.Logger;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal32T's block property table: hardness, explosion resistance, tool requirement and mineable tag of every NtmBlocks
 * registration, and drop samples for the tool requirement. Same template and conventions as {@link Goal32TGameTests}; every test has its own batch.
 * <p>
 * Expected values come from the ORIGINAL through migration/goal32t-block-properties.json (rows[].expected; the original registration of each row is
 * the trailing comment). The 1.7.10 reading: setHardness(h) sets the hardness and raises the stored resistance to 5h when lower, setResistance(v)
 * stores 3v, both in chain order; the effective resistance read by explosions and HBM code is stored / 5. Rock, iron and anvil materials drop only
 * for a pickaxe of any tier, crafted snow only for a shovel; other materials drop bare-handed. Blocks whose original class drops ungated
 * (BlockBobble.java:75-92 onBlockHarvested, BlockDummyable.java:389-406 onBlockHarvested) keep dropping bare-handed whatever the flag says.
 * <p>
 * Real classes and state: the registered blocks and the block tags as the server loaded them; drops through
 * {@code ServerPlayerGameMode.destroyBlock} by a survival NeoForge FakePlayer, counting the item entities the break leaves. Not evidence: mining
 * time on a real client, a dedicated server with real players, explosions (the resistance is read, not exploded), and 1.7.10 itself.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class Goal32TBlockPropertiesGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-32t]";

    private static Runnable passed(String test) {
        return () -> LOGGER.info("{} {} passed", TAG, test);
    }

    // ---------------------------------------------------------------- 1. property table

    /** One row of migration/goal32t-block-properties.json: neo_id and expected hardness, resistance, tool, tag (null: no mineable tag). */
    private record Row(String id, float hardness, float resistance, boolean tool, String tag) { }

    private static Row row(String id, float hardness, float resistance, boolean tool, String tag) {
        return new Row(id, hardness, resistance, tool, tag);
    }

    private static final Map<String, TagKey<Block>> MINEABLE = Map.of("pickaxe", BlockTags.MINEABLE_WITH_PICKAXE, "axe", BlockTags.MINEABLE_WITH_AXE,
            "shovel", BlockTags.MINEABLE_WITH_SHOVEL, "hoe", BlockTags.MINEABLE_WITH_HOE);
    private static final Map<String, Item> WOODEN = Map.of("pickaxe", Items.WOODEN_PICKAXE, "axe", Items.WOODEN_AXE, "shovel", Items.WOODEN_SHOVEL, "hoe", Items.WOODEN_HOE);
    private static final List<TagKey<Block>> TIERS = List.of(BlockTags.NEEDS_STONE_TOOL, BlockTags.NEEDS_IRON_TOOL, BlockTags.NEEDS_DIAMOND_TOOL,
            Tags.Blocks.NEEDS_WOOD_TOOL, Tags.Blocks.NEEDS_GOLD_TOOL, Tags.Blocks.NEEDS_NETHERITE_TOOL);

    // Generated from migration/goal32t-block-properties.json rows[].expected, in table order; trailing comment: the row's orig.registration
    // (ModBlocks.java is ORIG src/main/java/com/hbm/blocks/ModBlocks.java).
    private static final List<Row> ROWS = List.of(
            row("ore_oil", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1333
            row("ore_oil_empty", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1334
            row("ore_oil_sand", 0.5F, 0.6F, false, "shovel"), // ModBlocks.java:1335
            row("ore_bedrock_oil", -1.0F, 600000.0F, true, "pickaxe"), // ModBlocks.java:1336
            row("ore_uranium", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1239
            row("ore_uranium_deepslate", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1239
            row("ore_uranium_scorched", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1240
            row("ore_beryllium", 5.0F, 9.0F, true, "pickaxe"), // ModBlocks.java:1252
            row("ore_beryllium_deepslate", 5.0F, 9.0F, true, "pickaxe"), // ModBlocks.java:1252
            row("ore_tungsten", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1247
            row("ore_tungsten_deepslate", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1247
            row("ore_titanium", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1241
            row("ore_titanium_deepslate", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1241
            row("ore_lead", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1250
            row("ore_lead_deepslate", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1250
            row("ore_aluminium", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1248
            row("ore_aluminium_deepslate", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1248
            row("ore_asbestos", 5.0F, 9.0F, true, "pickaxe"), // ModBlocks.java:1254
            row("ore_asbestos_deepslate", 5.0F, 9.0F, true, "pickaxe"), // ModBlocks.java:1254
            row("ore_thorium", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1243
            row("ore_thorium_deepslate", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1243
            row("ore_niter", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1245
            row("ore_niter_deepslate", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1245
            row("ore_cobalt", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1329
            row("ore_cobalt_deepslate", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1329
            row("ore_cinnabar", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1330
            row("ore_cinnabar_deepslate", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1330
            row("ore_fluorite", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1249
            row("ore_fluorite_deepslate", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1249
            row("ore_meteor_iron", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1272
            row("ore_meteor_cobalt", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1272
            row("ore_meteor_copper", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1272
            row("ore_meteor_aluminium", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1272
            row("ore_meteor_rare", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1272
            row("ore_rare", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1328
            row("ore_rare_deepslate", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1328
            row("ore_sulfur", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1242
            row("ore_sulfur_deepslate", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1242
            row("ore_lignite", 5.0F, 9.0F, true, "pickaxe"), // ModBlocks.java:1253
            row("ore_lignite_deepslate", 5.0F, 9.0F, true, "pickaxe"), // ModBlocks.java:1253
            row("ore_schrabidium", 15.0F, 360.0F, true, "pickaxe"), // ModBlocks.java:1251
            row("ore_nether_uranium", 0.4F, 6.0F, true, "pickaxe"), // ModBlocks.java:1263
            row("ore_nether_uranium_scorched", 0.4F, 6.0F, true, "pickaxe"), // ModBlocks.java:1264
            row("ore_nether_plutonium", 0.4F, 6.0F, true, "pickaxe"), // ModBlocks.java:1265
            row("ore_nether_schrabidium", 15.0F, 360.0F, true, "pickaxe"), // ModBlocks.java:1270
            row("ore_nether_tungsten", 0.4F, 6.0F, true, "pickaxe"), // ModBlocks.java:1266
            row("ore_nether_sulfur", 0.4F, 6.0F, true, "pickaxe"), // ModBlocks.java:1267
            row("ore_nether_fire", 0.4F, 6.0F, true, "pickaxe"), // ModBlocks.java:1268
            row("ore_nether_cobalt", 0.4F, 6.0F, true, "pickaxe"), // ModBlocks.java:1269
            row("ore_nether_coal", 0.4F, 6.0F, true, "pickaxe"), // ModBlocks.java:1261
            row("ore_nether_smoldering", 0.4F, 6.0F, true, "pickaxe"), // ModBlocks.java:1262
            row("ore_tikite", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1338
            row("ore_coltan", 15.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1331
            row("ore_gneiss_uranium", 1.5F, 6.0F, true, "pickaxe"), // ModBlocks.java:1277
            row("ore_gneiss_uranium_scorched", 1.5F, 6.0F, true, "pickaxe"), // ModBlocks.java:1278
            row("ore_gneiss_schrabidium", 1.5F, 6.0F, true, "pickaxe"), // ModBlocks.java:1282
            row("stone_gneiss", 1.5F, 6.0F, true, "pickaxe"), // ModBlocks.java:1274
            row("ore_gneiss_iron", 1.5F, 6.0F, true, "pickaxe"), // ModBlocks.java:1275
            row("ore_gneiss_gold", 1.5F, 6.0F, true, "pickaxe"), // ModBlocks.java:1276
            row("ore_gneiss_copper", 1.5F, 6.0F, true, "pickaxe"), // ModBlocks.java:1279
            row("ore_gneiss_asbestos", 1.5F, 6.0F, true, "pickaxe"), // ModBlocks.java:1280
            row("ore_gneiss_lithium", 1.5F, 6.0F, true, "pickaxe"), // ModBlocks.java:1281
            row("ore_gneiss_rare", 1.5F, 6.0F, true, "pickaxe"), // ModBlocks.java:1283
            row("ore_gneiss_gas", 1.5F, 6.0F, true, "pickaxe"), // ModBlocks.java:1284
            row("resource_limestone", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1315
            row("resource_bauxite", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1315
            row("resource_hematite", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1315
            row("resource_malachite", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1315
            row("resource_chrysotile", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1315
            row("resource_sulfurous_stone", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1315
            row("stone_depth", -1.0F, 6.0F, false, "pickaxe"), // ModBlocks.java:1290
            row("stone_depth_nether", -1.0F, 6.0F, false, "pickaxe"), // ModBlocks.java:1311
            row("ore_depth_cinnabar", -1.0F, 6.0F, false, "pickaxe"), // ModBlocks.java:1291
            row("ore_depth_zirconium", -1.0F, 6.0F, false, "pickaxe"), // ModBlocks.java:1292
            row("ore_depth_borax", -1.0F, 6.0F, false, "pickaxe"), // ModBlocks.java:1293
            row("ore_depth_nether_neodymium", -1.0F, 6.0F, false, "pickaxe"), // ModBlocks.java:1312
            row("cluster_depth_iron", -1.0F, 6.0F, false, "pickaxe"), // ModBlocks.java:1294
            row("cluster_depth_titanium", -1.0F, 6.0F, false, "pickaxe"), // ModBlocks.java:1295
            row("cluster_depth_tungsten", -1.0F, 6.0F, false, "pickaxe"), // ModBlocks.java:1296
            row("ore_alexandrite", -1.0F, 6.0F, false, "pickaxe"), // ModBlocks.java:1297
            row("cluster_iron", 5.0F, 9.0F, true, "pickaxe"), // ModBlocks.java:1256
            row("cluster_titanium", 5.0F, 9.0F, true, "pickaxe"), // ModBlocks.java:1257
            row("cluster_aluminium", 5.0F, 9.0F, true, "pickaxe"), // ModBlocks.java:1258
            row("cluster_copper", 5.0F, 9.0F, true, "pickaxe"), // ModBlocks.java:1259
            row("ore_basalt", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1321
            row("basalt", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1320
            row("basalt_smooth", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1322
            row("basalt_brick", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1323
            row("basalt_polished", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1324
            row("basalt_tiles", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1325
            row("stone_cracked", 5.0F, 5.0F, true, "pickaxe"), // ModBlocks.java:1691
            row("dirt_oily", 0.5F, 0.5F, false, "shovel"), // ModBlocks.java:1688
            row("sand_oily", 0.5F, 0.5F, false, "shovel"), // ModBlocks.java:1689
            row("sand_oily_red", 0.5F, 0.5F, false, "shovel"), // ModBlocks.java:1690
            row("dirt_dead", 0.5F, 0.5F, false, "shovel"), // ModBlocks.java:1687
            row("oil_spill", 0.1F, 0.1F, false, "shovel"), // ModBlocks.java:1681
            row("block_scrap", 2.5F, 3.0F, false, "shovel"), // ModBlocks.java:1381
            row("block_actinium", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1425
            row("block_steel", 5.0F, 30.0F, true, "pickaxe"), // ModBlocks.java:1365
            row("block_aluminium", 5.0F, 12.0F, true, "pickaxe"), // ModBlocks.java:1363
            row("block_asbestos", 5.0F, 9.0F, false, null), // ModBlocks.java:1404
            row("block_australium", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1432
            row("block_beryllium", 5.0F, 12.0F, true, "pickaxe"), // ModBlocks.java:1383
            row("block_bismuth", 5.0F, 54.0F, true, "pickaxe"), // ModBlocks.java:1369
            row("block_cadmium", 5.0F, 54.0F, true, "pickaxe"), // ModBlocks.java:1370
            row("block_cdalloy", 5.0F, 42.0F, true, "pickaxe"), // ModBlocks.java:1367
            row("block_coltan", 5.0F, 30.0F, true, "pickaxe"), // ModBlocks.java:1371
            row("block_combine_steel", 5.0F, 360.0F, true, "pickaxe"), // ModBlocks.java:1394
            row("block_copper", 5.0F, 12.0F, true, "pickaxe"), // ModBlocks.java:1360
            row("block_desh", 5.0F, 180.0F, true, "pickaxe"), // ModBlocks.java:1395
            row("block_dineutronium", 5.0F, 36000.0F, true, "pickaxe"), // ModBlocks.java:1390
            row("block_dura_steel", 5.0F, 120.0F, true, "pickaxe"), // ModBlocks.java:1396
            row("block_euphemium", 5.0F, 36000.0F, true, "pickaxe"), // ModBlocks.java:1389
            row("block_foam", 0.5F, 0.0F, true, "shovel"), // ModBlocks.java:1411
            row("block_lanthanium", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1423
            row("block_lead", 5.0F, 30.0F, true, "pickaxe"), // ModBlocks.java:1368
            row("block_lithium", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1406
            row("block_magnetized_tungsten", 5.0F, 45.0F, true, "pickaxe"), // ModBlocks.java:1393
            row("block_meteor", 15.0F, 216.0F, true, "pickaxe"), // ModBlocks.java:1567
            row("block_meteor_molten", 15.0F, 216.0F, true, "pickaxe"), // ModBlocks.java:1570
            row("block_meteor_cobble", 15.0F, 216.0F, true, "pickaxe"), // ModBlocks.java:1568
            row("block_meteor_broken", 15.0F, 216.0F, true, "pickaxe"), // ModBlocks.java:1569
            row("block_meteor_treasure", 15.0F, 216.0F, true, "pickaxe"), // ModBlocks.java:1571
            row("block_mox_fuel", 5.0F, 30.0F, true, "pickaxe"), // ModBlocks.java:1350
            row("block_neptunium", 5.0F, 36.0F, true, "pickaxe"), // ModBlocks.java:1348
            row("block_niobium", 5.0F, 30.0F, true, "pickaxe"), // ModBlocks.java:1373
            row("block_niter", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1359
            row("block_plutonium", 5.0F, 30.0F, true, "pickaxe"), // ModBlocks.java:1351
            row("block_plutonium_fuel", 5.0F, 30.0F, true, "pickaxe"), // ModBlocks.java:1356
            row("block_polonium", 5.0F, 30.0F, true, "pickaxe"), // ModBlocks.java:1349
            row("block_pu238", 5.0F, 30.0F, true, "pickaxe"), // ModBlocks.java:1352
            row("block_pu239", 5.0F, 30.0F, true, "pickaxe"), // ModBlocks.java:1353
            row("block_pu240", 5.0F, 30.0F, true, "pickaxe"), // ModBlocks.java:1354
            row("block_pu_mix", 5.0F, 30.0F, true, "pickaxe"), // ModBlocks.java:1355
            row("block_ra226", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1424
            row("block_red_copper", 5.0F, 15.0F, true, "pickaxe"), // ModBlocks.java:1361
            row("block_saturnite", 1.0F, 10.0F, false, "pickaxe"), // none: no block_saturnite registration anywhere in the original (only anvil_saturnite at ORIG ModBlocks.java:1065, :2274, :3024)
            row("block_schrabidate", 5.0F, 360.0F, true, "pickaxe"), // ModBlocks.java:1386
            row("block_schrabidium", 5.0F, 360.0F, true, "pickaxe"), // ModBlocks.java:1385
            row("block_schrabidium_fuel", 5.0F, 360.0F, true, "pickaxe"), // ModBlocks.java:1388
            row("block_schraranium", 5.0F, 150.0F, true, "pickaxe"), // ModBlocks.java:1384
            row("block_smore", 15.0F, 360.0F, true, "pickaxe"), // ModBlocks.java:1429
            row("block_solinium", 5.0F, 360.0F, true, "pickaxe"), // ModBlocks.java:1387
            row("block_sulfur", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1358
            row("block_tantalium", 5.0F, 30.0F, true, "pickaxe"), // ModBlocks.java:1372
            row("block_tcalloy", 5.0F, 42.0F, true, "pickaxe"), // ModBlocks.java:1366
            row("block_thorium", 5.0F, 30.0F, true, "pickaxe"), // ModBlocks.java:1346
            row("block_thorium_fuel", 5.0F, 30.0F, true, "pickaxe"), // ModBlocks.java:1347
            row("block_titanium", 5.0F, 30.0F, true, "pickaxe"), // ModBlocks.java:1357
            row("block_tungsten", 5.0F, 12.0F, true, "pickaxe"), // ModBlocks.java:1362
            row("block_u233", 5.0F, 30.0F, true, "pickaxe"), // ModBlocks.java:1342
            row("block_u235", 5.0F, 30.0F, true, "pickaxe"), // ModBlocks.java:1343
            row("block_u238", 5.0F, 30.0F, true, "pickaxe"), // ModBlocks.java:1344
            row("block_uranium", 5.0F, 30.0F, true, "pickaxe"), // ModBlocks.java:1341
            row("block_uranium_fuel", 5.0F, 30.0F, true, "pickaxe"), // ModBlocks.java:1345
            row("block_waste", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1375
            row("block_waste_painted", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1376
            row("block_waste_vitrified", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1377
            row("block_yellowcake", 5.0F, 6.0F, false, "shovel"), // ModBlocks.java:1401
            row("block_fiberglass", 5.0F, 9.0F, false, null), // ModBlocks.java:1403
            row("reinforced_laminate", 15.0F, 180.0F, true, "pickaxe"), // ModBlocks.java:1476
            row("block_insulator", 5.0F, 6.0F, false, null), // ModBlocks.java:1402
            row("block_slag", 2.0F, 2.0F, true, "pickaxe"), // ModBlocks.java:1430
            row("block_graphite", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1413
            row("bobblehead", 0.0F, 0.0F, false, "pickaxe"), // ModBlocks.java:1454
            row("plushie", 0.0F, 0.0F, false, null), // ModBlocks.java:1456
            row("plant_flower", 0.0F, 0.0F, false, null), // ModBlocks.java:1660
            row("plant_mustard_willow", 0.0F, 0.0F, false, null), // ModBlocks.java:1661
            row("glass_quartz", 1.0F, 24.0F, false, null), // ModBlocks.java:1651
            row("glass_boron", 0.3F, 0.3F, false, null), // ModBlocks.java:1645
            row("glass_lead", 0.3F, 0.3F, false, null), // ModBlocks.java:1646
            row("gravel_obsidian", 5.0F, 12.0F, true, "pickaxe"), // ModBlocks.java:1460
            row("gravel_diamond", 0.6F, 0.6F, false, "shovel"), // ModBlocks.java:1461
            row("moon_turf", 0.5F, 0.5F, false, "shovel"), // ModBlocks.java:1580
            row("sand_quartz", 0.5F, 0.5F, false, "shovel"), // ModBlocks.java:1644
            row("sand_boron", 0.5F, 0.5F, false, "shovel"), // ModBlocks.java:1644
            row("sand_lead", 0.5F, 0.5F, false, "shovel"), // ModBlocks.java:1644
            row("asphalt", 15.0F, 72.0F, true, "pickaxe"), // ModBlocks.java:1462
            row("asphalt_light", 15.0F, 72.0F, true, "pickaxe"), // ModBlocks.java:1463
            row("reinforced_stone", 15.0F, 60.0F, true, "pickaxe"), // ModBlocks.java:1499
            row("steel_scaffold", 5.0F, 9.0F, true, "pickaxe"), // ModBlocks.java:1607
            row("steel_beam", 5.0F, 9.0F, true, "pickaxe"), // ModBlocks.java:1606
            row("steel_grate", 2.0F, 3.0F, true, "pickaxe"), // ModBlocks.java:1608
            row("brick_concrete", 15.0F, 96.0F, true, "pickaxe"), // ModBlocks.java:1509
            row("brick_concrete_mossy", 15.0F, 96.0F, true, "pickaxe"), // ModBlocks.java:1510
            row("brick_concrete_cracked", 15.0F, 36.0F, true, "pickaxe"), // ModBlocks.java:1511
            row("brick_concrete_broken", 15.0F, 27.0F, true, "pickaxe"), // ModBlocks.java:1512
            row("brick_concrete_marked", 15.0F, 96.0F, true, "pickaxe"), // ModBlocks.java:1513
            row("brick_obsidian", 15.0F, 72.0F, true, "pickaxe"), // ModBlocks.java:1514
            row("brick_light", 5.0F, 12.0F, true, "pickaxe"), // ModBlocks.java:1515
            row("brick_asbestos", 5.0F, 600.0F, true, "pickaxe"), // ModBlocks.java:1519
            row("brick_fire", 5.0F, 21.0F, true, "pickaxe"), // ModBlocks.java:1520
            row("concrete", 15.0F, 84.0F, true, "pickaxe"), // ModBlocks.java:1503
            row("concrete_smooth", 15.0F, 84.0F, true, "pickaxe"), // ModBlocks.java:1500
            row("concrete_asbestos", 15.0F, 90.0F, true, "pickaxe"), // ModBlocks.java:1504
            row("ducrete", 20.0F, 300.0F, true, "pickaxe"), // ModBlocks.java:1523
            row("ducrete_smooth", 20.0F, 300.0F, true, "pickaxe"), // ModBlocks.java:1522
            row("reinforced_ducrete", 20.0F, 600.0F, true, "pickaxe"), // ModBlocks.java:1525
            row("brick_ducrete", 15.0F, 450.0F, true, "pickaxe"), // ModBlocks.java:1524
            row("brick_concrete_slab", 15.0F, 96.0F, true, "pickaxe"), // ModBlocks.java:1509
            row("brick_concrete_mossy_slab", 15.0F, 96.0F, true, "pickaxe"), // ModBlocks.java:1510
            row("brick_concrete_cracked_slab", 15.0F, 36.0F, true, "pickaxe"), // ModBlocks.java:1511
            row("brick_concrete_broken_slab", 15.0F, 27.0F, true, "pickaxe"), // ModBlocks.java:1512
            row("brick_concrete_stairs", 15.0F, 96.0F, true, "pickaxe"), // ModBlocks.java:1545
            row("brick_concrete_mossy_stairs", 15.0F, 96.0F, true, "pickaxe"), // ModBlocks.java:1546
            row("brick_concrete_cracked_stairs", 15.0F, 36.0F, true, "pickaxe"), // ModBlocks.java:1547
            row("brick_concrete_broken_stairs", 15.0F, 27.0F, true, "pickaxe"), // ModBlocks.java:1548
            row("barbed_wire", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:2074
            row("spikes", 2.5F, 3.0F, true, "pickaxe"), // ModBlocks.java:2080
            row("waste_earth", 0.6F, 0.6F, false, "shovel"), // ModBlocks.java:1666
            row("waste_mycelium", 0.6F, 0.6F, false, "shovel"), // ModBlocks.java:1667
            row("waste_trinitite", 0.5F, 1.5F, false, "shovel"), // ModBlocks.java:1668
            row("waste_trinitite_red", 0.5F, 1.5F, false, "shovel"), // ModBlocks.java:1669
            row("waste_log", 5.0F, 1.5F, false, "axe"), // ModBlocks.java:1670
            row("waste_leaves", 0.1F, 0.1F, false, "hoe"), // ModBlocks.java:1671
            row("waste_planks", 0.5F, 1.5F, false, "axe"), // ModBlocks.java:1672
            row("frozen_dirt", 0.5F, 1.5F, false, "shovel"), // ModBlocks.java:1673
            row("frozen_grass", 0.5F, 1.5F, false, "shovel"), // ModBlocks.java:1674
            row("frozen_log", 0.5F, 1.5F, false, "axe"), // ModBlocks.java:1675
            row("frozen_planks", 0.5F, 1.5F, false, "axe"), // ModBlocks.java:1676
            row("leaves_layer", 0.1F, 0.1F, false, "hoe"), // ModBlocks.java:1680
            row("fallout", 0.1F, 0.1F, false, "shovel"), // ModBlocks.java:1677
            row("sellafield_slaked", 5.0F, 5.0F, true, "pickaxe"), // ModBlocks.java:1694
            row("ore_sellafield_diamond", 5.0F, 5.0F, true, "pickaxe"), // ModBlocks.java:1697
            row("ore_sellafield_emerald", 5.0F, 5.0F, true, "pickaxe"), // ModBlocks.java:1698
            row("sellafield_bedrock", -1.0F, 3600000.0F, false, "pickaxe"), // ModBlocks.java:1695
            row("nuke_gadget", 5.0F, 120.0F, true, "pickaxe"), // ModBlocks.java:1706
            row("nuke_little_boy", 5.0F, 120.0F, true, "pickaxe"), // ModBlocks.java:1707
            row("nuke_fat_man", 5.0F, 120.0F, true, "pickaxe"), // ModBlocks.java:1708
            row("nuke_ivy_mike", 5.0F, 120.0F, true, "pickaxe"), // ModBlocks.java:1709
            row("nuke_tsar_bomba", 5.0F, 120.0F, true, "pickaxe"), // ModBlocks.java:1710
            row("nuke_prototype", 5.0F, 120.0F, true, "pickaxe"), // ModBlocks.java:1712
            row("nuke_fleija", 5.0F, 120.0F, true, "pickaxe"), // ModBlocks.java:1711
            row("nuke_solinium", 5.0F, 120.0F, true, "pickaxe"), // ModBlocks.java:1714
            row("nuke_n2", 5.0F, 120.0F, true, "pickaxe"), // ModBlocks.java:1715
            row("nuke_fstbmb", 5.0F, 120.0F, true, "pickaxe"), // ModBlocks.java:1716
            row("crashed_bomb", -1.0F, 3600.0F, false, "pickaxe"), // ModBlocks.java:1735
            row("dynamite", 0.0F, 0.0F, false, null), // ModBlocks.java:1746
            row("tnt", 0.0F, 0.0F, false, null), // ModBlocks.java:1747
            row("semtex", 0.0F, 0.0F, false, null), // ModBlocks.java:1748
            row("c4", 0.0F, 0.0F, false, null), // ModBlocks.java:1749
            row("fissure_bomb", 0.0F, 0.0F, false, null), // ModBlocks.java:1750
            row("mine_ap", 1.0F, 1.0F, true, "pickaxe"), // ModBlocks.java:1741
            row("mine_he", 1.0F, 1.0F, true, "pickaxe"), // ModBlocks.java:1742
            row("mine_shrap", 1.0F, 1.0F, true, "pickaxe"), // ModBlocks.java:1743
            row("mine_fat", 1.0F, 1.0F, true, "pickaxe"), // ModBlocks.java:1744
            row("mine_naval", 1.0F, 1.0F, true, "pickaxe"), // ModBlocks.java:1745
            row("deco_aluminium", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1439
            row("deco_beryllium", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1443
            row("deco_lead", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1442
            row("deco_red_copper", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1437
            row("deco_steel", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1440
            row("deco_rbmk", 5.0F, 60.0F, true, "pickaxe"), // ModBlocks.java:1446
            row("deco_rbmk_smooth", 5.0F, 60.0F, true, "pickaxe"), // ModBlocks.java:1447
            row("deco_rusty_steel", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1441
            row("deco_titanium", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1436
            row("deco_tungsten", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1438
            row("deco_asbestos", 5.0F, 6.0F, false, null), // ModBlocks.java:1445
            row("det_charge", 0.1F, 0.0F, true, "pickaxe"), // ModBlocks.java:1726
            row("det_cord", 0.1F, 0.0F, true, "pickaxe"), // ModBlocks.java:1725
            row("det_nuke", 0.1F, 0.0F, true, "pickaxe"), // ModBlocks.java:1727
            row("det_miner", 0.1F, 0.0F, true, "pickaxe"), // ModBlocks.java:1728
            row("barrel_red", 0.5F, 1.5F, true, "pickaxe"), // ModBlocks.java:1729
            row("barrel_pink", 0.5F, 1.5F, true, "pickaxe"), // ModBlocks.java:1730
            row("barrel_lox", 0.5F, 1.5F, true, "pickaxe"), // ModBlocks.java:1733
            row("barrel_taint", 0.5F, 1.5F, true, "pickaxe"), // ModBlocks.java:1734
            row("geiger", 15.0F, 0.15F, true, "pickaxe"), // ModBlocks.java:1638
            row("anvil", 5.0F, 60.0F, true, "pickaxe"), // ModBlocks.java:2269
            row("press_preheater", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:2234
            row("machine_press", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:2235
            row("heat_boiler", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1771
            row("machine_industrial_boiler", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1772
            row("heater_firebox", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1755
            row("machine_stirling", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1765
            row("machine_steam_engine", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:2246
            row("pump_electric", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1753
            row("machine_condenser", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:2250
            row("heater_oven", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1756
            row("heater_oilburner", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1757
            row("heater_electric", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1758
            row("heater_heatex", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1759
            row("machine_shredder", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1853
            row("machine_electric_furnace", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1828
            row("machine_soldering_station", 5.0F, 18.0F, true, "pickaxe"), // ModBlocks.java:2221
            row("machine_arc_welder", 5.0F, 18.0F, true, "pickaxe"), // ModBlocks.java:2220
            row("machine_well", 5.0F, 12.0F, true, "pickaxe"), // ModBlocks.java:2193
            row("machine_pumpjack", 5.0F, 12.0F, true, "pickaxe"), // ModBlocks.java:2194
            row("machine_fracking_tower", 5.0F, 12.0F, true, "pickaxe"), // ModBlocks.java:2195
            row("machine_refinery", 5.0F, 12.0F, true, "pickaxe"), // ModBlocks.java:2200
            row("machine_vacuum_distill", 5.0F, 12.0F, true, "pickaxe"), // ModBlocks.java:2201
            row("machine_rotary_furnace", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1793
            row("machine_catalytic_cracker", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:2204
            row("machine_fraction_tower", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:2202
            row("machine_compressor", 10.0F, 12.0F, true, "pickaxe"), // ModBlocks.java:2261
            row("machine_coker", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:2207
            row("machine_mixer", 5.0F, 18.0F, true, "pickaxe"), // ModBlocks.java:2225
            row("fraction_spacer", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:2203
            row("machine_arc_furnace", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1830
            row("furnace_combination", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1764
            row("machine_crucible", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1770
            row("foundry_mold", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1774
            row("foundry_channel", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1776
            row("foundry_tank", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1777
            row("foundry_outlet", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1778
            row("foundry_basin", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1775
            row("machine_blast_furnace", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1787
            row("machine_combustion_engine", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1851
            row("machine_turbofan", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:2231
            row("machine_diesel", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1850
            row("machine_rtg", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1859
            row("machine_wood_burner", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1849
            row("machine_centrifuge", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1789
            row("machine_gas_centrifuge", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1790
            row("machine_crystallizer", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1794
            row("machine_waste_drum", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:2282
            row("machine_chemical_plant", 5.0F, 18.0F, true, "pickaxe"), // ModBlocks.java:2222
            row("machine_purex", 5.0F, 18.0F, true, "pickaxe"), // ModBlocks.java:2224
            row("crate_iron", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:2183
            row("crate_tungsten", 7.5F, 180.0F, true, "pickaxe"), // ModBlocks.java:2186
            row("crate_steel", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:2184
            row("crate_desh", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:2185
            row("barrel_plastic", 2.0F, 3.0F, true, "pickaxe"), // ModBlocks.java:1951
            row("emp_bomb", 5.0F, 120.0F, true, "pickaxe"), // ModBlocks.java:1724
            row("barrel_steel", 2.0F, 3.0F, true, "pickaxe"), // ModBlocks.java:1953
            row("barrel_corroded", 2.0F, 3.0F, true, "pickaxe"), // ModBlocks.java:1952
            row("barrel_tcalloy", 2.0F, 3.0F, true, "pickaxe"), // ModBlocks.java:1954
            row("transformer", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1957
            row("machine_zirnox", 5.0F, 60.0F, true, "pickaxe"), // ModBlocks.java:2240
            row("zirnox_destroyed", 100.0F, 480.0F, true, "pickaxe"), // ModBlocks.java:2241
            row("rbmk_rod", 3.0F, 18.0F, true, "pickaxe"), // ModBlocks.java:2119
            row("rbmk_rod_mod", 3.0F, 18.0F, true, "pickaxe"), // ModBlocks.java:2120
            row("rbmk_control", 3.0F, 18.0F, true, "pickaxe"), // ModBlocks.java:2123
            row("rbmk_control_mod", 3.0F, 18.0F, true, "pickaxe"), // ModBlocks.java:2124
            row("rbmk_control_auto", 3.0F, 18.0F, true, "pickaxe"), // ModBlocks.java:2125
            row("rbmk_blank", 3.0F, 18.0F, true, "pickaxe"), // ModBlocks.java:2128
            row("rbmk_boiler", 3.0F, 18.0F, true, "pickaxe"), // ModBlocks.java:2129
            row("rbmk_reflector", 3.0F, 18.0F, true, "pickaxe"), // ModBlocks.java:2130
            row("rbmk_absorber", 3.0F, 18.0F, true, "pickaxe"), // ModBlocks.java:2131
            row("rbmk_moderator", 3.0F, 18.0F, true, "pickaxe"), // ModBlocks.java:2132
            row("rbmk_cooler", 3.0F, 18.0F, true, "pickaxe"), // ModBlocks.java:2135
            row("rbmk_heater", 3.0F, 18.0F, true, "pickaxe"), // ModBlocks.java:2136
            row("rbmk_storage", 3.0F, 18.0F, true, "pickaxe"), // ModBlocks.java:2134
            row("rbmk_outgasser", 3.0F, 18.0F, true, "pickaxe"), // ModBlocks.java:2133
            row("rbmk_loader", 50.0F, 36.0F, true, "pickaxe"), // ModBlocks.java:2149
            row("rbmk_console", 3.0F, 18.0F, true, "pickaxe"), // ModBlocks.java:2137
            row("rbmk_crane_console", 3.0F, 18.0F, true, "pickaxe"), // ModBlocks.java:2138
            row("rbmk_autoloader", 50.0F, 36.0F, true, "pickaxe"), // ModBlocks.java:2148
            row("pribris", 50.0F, 360.0F, true, "pickaxe"), // ModBlocks.java:2152
            row("pribris_burning", 50.0F, 360.0F, true, "pickaxe"), // ModBlocks.java:2153
            row("pribris_radiating", 50.0F, 360.0F, true, "pickaxe"), // ModBlocks.java:2154
            row("corium_block", 100.0F, 300.0F, true, "pickaxe"), // ModBlocks.java:2343
            row("red_cable", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1864
            row("fluid_duct_neo", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1884
            row("red_wire_coated", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1863
            row("red_cable_paintable", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1866
            row("red_cable_gauge", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1867
            row("cable_switch", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1879
            row("cable_detector", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1880
            row("machine_detector", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1883
            row("fluid_duct_paintable", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1891
            row("fluid_duct_gauge", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1892
            row("fluid_valve", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1893
            row("fluid_switch", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1894
            row("fluid_counter_valve", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1895
            row("red_connector", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1869
            row("red_connector_super", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1870
            row("red_pylon", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1871
            row("red_pylon_steel", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1872
            row("red_pylon_medium_wood", 5.0F, 6.0F, false, "axe"), // ModBlocks.java:1873
            row("red_pylon_medium_wood_transformer", 5.0F, 6.0F, false, "axe"), // ModBlocks.java:1874
            row("red_pylon_medium_steel", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1875
            row("red_pylon_medium_steel_transformer", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1876
            row("red_pylon_large", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1877
            row("substation", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1878
            row("pipe_anchor", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1888
            row("flow_control_pump", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1897
            row("conveyor", 2.0F, 1.2F, true, "pickaxe"), // ModBlocks.java:1909
            row("conveyor_express", 2.0F, 1.2F, true, "pickaxe"), // ModBlocks.java:1910
            row("conveyor_double", 2.0F, 1.2F, true, "pickaxe"), // ModBlocks.java:1911
            row("conveyor_triple", 2.0F, 1.2F, true, "pickaxe"), // ModBlocks.java:1912
            row("conveyor_chute", 2.0F, 1.2F, true, "pickaxe"), // ModBlocks.java:1913
            row("conveyor_lift", 2.0F, 1.2F, true, "pickaxe"), // ModBlocks.java:1914
            row("crane_extractor", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1915
            row("crane_inserter", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1916
            row("crane_grabber", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1917
            row("crane_boxer", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1919
            row("crane_unboxer", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1920
            row("crane_router", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1918
            row("crane_splitter", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1921
            row("crane_partitioner", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1922
            row("network_separator", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1882
            row("radio_torch_sender", 0.1F, 6.0F, false, null), // ModBlocks.java:1899
            row("radio_torch_receiver", 0.1F, 6.0F, false, null), // ModBlocks.java:1900
            row("radio_torch_relay", 0.1F, 6.0F, false, null), // ModBlocks.java:1903
            row("machine_battery_socket", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1833
            row("machine_battery_redd", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1834
            row("machine_assembly_machine", 5.0F, 18.0F, true, "pickaxe"), // ModBlocks.java:2217
            row("machine_fluid_tank", 5.0F, 12.0F, true, "pickaxe"), // ModBlocks.java:2227
            row("machine_chungus", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:2249
            row("machine_industrial_turbine", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:2248
            row("machine_satlinker", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:1959
            row("decontaminator", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:2314
            row("rad_absorber", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:2313
            row("rad_absorber_red", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:2313
            row("rad_absorber_green", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:2313
            row("rad_absorber_pink", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:2313
            row("pwr_controller", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:2003
            row("balefire", 0.0F, 0.0F, false, null), // ModBlocks.java:2033
            row("fire_digamma", 0.0F, 90.0F, false, null), // ModBlocks.java:2034
            row("volcano_core", -1.0F, 6000.0F, false, "pickaxe"), // ModBlocks.java:2320
            row("volcano_rad_core", -1.0F, 6000.0F, false, "pickaxe"), // ModBlocks.java:2321
            row("launch_pad", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:2087
            row("launch_pad_large", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:2089
            row("soyuz_launcher", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:2097
            row("machine_radar", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:2090
            row("machine_radar_large", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:2091
            row("volcanic_lava", 500.0F, 300.0F, false, null), // ModBlocks.java:2347
            row("rad_lava", 500.0F, 300.0F, false, null), // ModBlocks.java:2351
            row("gas_radon", 0.0F, 0.0F, false, null), // ModBlocks.java:2303
            row("gas_radon_dense", 0.0F, 0.0F, false, null), // ModBlocks.java:2304
            row("gas_radon_tomb", 0.0F, 0.0F, false, null), // ModBlocks.java:2305
            row("gas_meltdown", 0.0F, 0.0F, false, null), // ModBlocks.java:2306
            row("gas_monoxide", 0.0F, 0.0F, false, null), // ModBlocks.java:2307
            row("gas_asbestos", 0.0F, 0.0F, false, null), // ModBlocks.java:2308
            row("gas_coal", 0.0F, 0.0F, false, null), // ModBlocks.java:2309
            row("gas_flammable", 0.0F, 0.0F, false, null), // ModBlocks.java:2310
            row("gas_explosive", 0.0F, 0.0F, false, null), // ModBlocks.java:2311
            row("oil_pipe", 5.0F, 6.0F, true, "pickaxe"), // ModBlocks.java:2196
            row("taint", 15.0F, 6.0F, true, "pickaxe")  // ModBlocks.java:2295
    );

    // Hardness: Block.defaultDestroyTime; resistance: Block.getExplosionResistance (the value explosions read through
    // IBlockExtension.getExplosionResistance); tool: BlockState.requiresCorrectToolForDrops; tag: membership in the four mineable tags; no tier tag,
    // so a wooden tool of the row's tag is a correct tool. All mismatches are collected and reported at once.
    @GameTest(template = TEMPLATE, batch = "hbm32t_block_property_table", timeoutTicks = 100)
    public static void block_property_table(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    List<String> wrong = new ArrayList<>();
                    for(Row r : ROWS) {
                        ResourceLocation key = ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, r.id());
                        if(!BuiltInRegistries.BLOCK.containsKey(key)) {
                            wrong.add(r.id() + ": not registered");
                            continue;
                        }
                        Block block = BuiltInRegistries.BLOCK.get(key);
                        BlockState state = block.defaultBlockState();
                        if(Float.compare(block.defaultDestroyTime(), r.hardness()) != 0) wrong.add(r.id() + ": hardness " + block.defaultDestroyTime() + ", original " + r.hardness());
                        if(Float.compare(block.getExplosionResistance(), r.resistance()) != 0) wrong.add(r.id() + ": explosion resistance " + block.getExplosionResistance() + ", original " + r.resistance());
                        if(state.requiresCorrectToolForDrops() != r.tool()) wrong.add(r.id() + ": requiresCorrectToolForDrops " + state.requiresCorrectToolForDrops() + ", original " + r.tool());
                        for(Map.Entry<String, TagKey<Block>> e : MINEABLE.entrySet()) {
                            boolean in = state.is(e.getValue()), want = e.getKey().equals(r.tag());
                            if(in != want) wrong.add(r.id() + ": mineable/" + e.getKey() + " " + in + ", expected " + want);
                        }
                        for(TagKey<Block> tier : TIERS) if(state.is(tier)) wrong.add(r.id() + ": in " + tier.location());
                        if(r.tool() && r.tag() != null && !new ItemStack(WOODEN.get(r.tag())).isCorrectToolForDrops(state)) wrong.add(r.id() + ": a wooden " + r.tag() + " is not a correct tool");
                    }
                    for(String w : wrong) LOGGER.error("{} block_property_table mismatch: {}", TAG, w);
                    check(wrong.isEmpty(), wrong.size() + " mismatches against the original table: " + String.join("; ", wrong));
                    LOGGER.info("{} block_property_table: {} rows, hardness, explosion resistance, tool requirement and mineable tag as the original", TAG, ROWS.size());
                }))
                .thenExecute(passed("block_property_table"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 2. drop samples

    private static FakePlayer breaker(GameTestHelper helper, ItemStack tool) {
        FakePlayer p = new FakePlayer(helper.getLevel(), new GameProfile(UUID.randomUUID(), "goal32t-props-breaker"));
        p.setGameMode(GameType.SURVIVAL);
        Vec3 a = helper.absoluteVec(new Vec3(8.5, 1, 8.5));
        p.moveTo(a.x, a.y, a.z, 0F, 0F);
        p.getInventory().selected = 0;
        p.setItemInHand(InteractionHand.MAIN_HAND, tool.copy());
        return p;
    }

    private static List<ItemEntity> items(GameTestHelper helper, BlockPos rel) {
        BlockPos abs = helper.absolutePos(rel);
        return helper.getLevel().getEntitiesOfClass(ItemEntity.class, new AABB(abs).inflate(2D));
    }

    private static void discardItems(GameTestHelper helper) {
        Vec3 abs = helper.absoluteVec(new Vec3(8.5, 1, 8.5));
        for(ItemEntity entity : helper.getLevel().getEntitiesOfClass(ItemEntity.class, new AABB(abs, abs).inflate(12D))) entity.discard();
    }

    /** Breaks the block at rel with ServerPlayerGameMode.destroyBlock and returns how many of {@code drop} the break left as item entities. */
    private static int breakAndCount(GameTestHelper helper, BlockPos rel, ItemStack tool, Item drop, String label) {
        discardItems(helper);
        BlockPos abs = helper.absolutePos(rel);
        FakePlayer player = breaker(helper, tool);
        check(player.gameMode.destroyBlock(abs), label + ": destroyBlock returned false");
        check(helper.getLevel().getBlockState(abs).isAir(), label + ": the break left " + helper.getLevel().getBlockState(abs));
        int count = 0, other = 0;
        for(ItemEntity e : items(helper, rel)) {
            if(e.getItem().is(drop)) count += e.getItem().getCount();
            else other++;
        }
        check(other == 0, label + ": " + other + " item entities of other items");
        discardItems(helper);
        return count;
    }

    /** A sample: the block, its drop item, the correct tool, and whether the original drop is gated by the tool. */
    private record Sample(Block block, Item drop, ItemStack tool, boolean gated) { }

    private static String name(Block block) {
        return BuiltInRegistries.BLOCK.getKey(block).getPath();
    }

    // Gated (no drop bare-handed, a drop for a wooden tool of the material): Material.iron ModBlocks.java:1365 block_steel, :1864 red_cable,
    // :1884 fluid_duct_neo, :1909 conveyor (BlockConveyor.java:20-21 drops conveyor_wand), :1915 crane_extractor, :2313 rad_absorber, :1413
    // block_graphite, :2003 pwr_controller; Material.rock :1511 brick_concrete_cracked (the slab, BlockMultiSlab.java:57-60 drops the single slab);
    // Material.craftedSnow :1411 block_foam (shovel).
    // Ungated: BlockBobble.java:75-92 onBlockHarvested spawns the bobblehead for any tool (:1454); BlockDummyable.java:389-406 onBlockHarvested
    // drops the core's item for any tool (:1789 machine_centrifuge), so the tool flag there only slows mining.
    @GameTest(template = TEMPLATE, batch = "hbm32t_block_property_drops", timeoutTicks = 100)
    public static void tool_drop_samples(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ItemStack pickaxe = new ItemStack(Items.WOODEN_PICKAXE), shovel = new ItemStack(Items.WOODEN_SHOVEL);
                    List<Sample> samples = List.of(
                            new Sample(NtmBlocks.BLOCK_STEEL.get(), NtmBlocks.BLOCK_STEEL.get().asItem(), pickaxe, true),
                            new Sample(NtmBlocks.RED_CABLE.get(), NtmBlocks.RED_CABLE.get().asItem(), pickaxe, true),
                            new Sample(NtmBlocks.FLUID_DUCT_NEO.get(), NtmBlocks.FLUID_DUCT_NEO.get().asItem(), pickaxe, true),
                            new Sample(NtmBlocks.CONVEYOR.get(), BuiltInRegistries.ITEM.get(ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, "conveyor_wand")), pickaxe, true),
                            new Sample(NtmBlocks.CRANE_EXTRACTOR.get(), NtmBlocks.CRANE_EXTRACTOR.get().asItem(), pickaxe, true),
                            new Sample(NtmBlocks.RAD_ABSORBER.get(), NtmBlocks.RAD_ABSORBER.get().asItem(), pickaxe, true),
                            new Sample(NtmBlocks.BLOCK_GRAPHITE.get(), NtmBlocks.BLOCK_GRAPHITE.get().asItem(), pickaxe, true),
                            new Sample(NtmBlocks.BRICK_CONCRETE_CRACKED_SLAB.get(), NtmBlocks.BRICK_CONCRETE_CRACKED_SLAB.get().asItem(), pickaxe, true),
                            new Sample(NtmBlocks.PWR_CONTROLLER.get(), NtmBlocks.PWR_CONTROLLER.get().asItem(), pickaxe, true),
                            new Sample(NtmBlocks.BLOCK_FOAM.get(), NtmBlocks.BLOCK_FOAM.get().asItem(), shovel, true),
                            new Sample(NtmBlocks.BOBBLEHEAD.get(), NtmBlocks.BOBBLEHEAD.get().asItem(), pickaxe, false));
                    check(samples.get(3).drop() != Items.AIR, "conveyor_wand is not registered");
                    BlockPos rel = new BlockPos(4, 2, 4);
                    for(Sample s : samples) {
                        String n = name(s.block());
                        BlockState state = s.block().defaultBlockState();
                        check(breaker(helper, ItemStack.EMPTY).hasCorrectToolForDrops(state) == !s.gated(), n + ": hasCorrectToolForDrops bare-handed " + !s.gated() + " expected");
                        check(breaker(helper, s.tool()).hasCorrectToolForDrops(state), n + ": " + s.tool() + " is not a correct tool");
                        helper.setBlock(rel, state);
                        int bare = breakAndCount(helper, rel, ItemStack.EMPTY, s.drop(), n + " bare-handed");
                        check(s.gated() ? bare == 0 : bare >= 1, n + " bare-handed dropped " + bare + " " + s.drop() + ", original " + (s.gated() ? "none" : "a drop"));
                        helper.setBlock(rel, state);
                        int tooled = breakAndCount(helper, rel, s.tool(), s.drop(), n + " with " + s.tool());
                        check(tooled >= 1, n + " with " + s.tool() + " dropped " + tooled + " " + s.drop() + ", original a drop");
                        if(s.block() == NtmBlocks.BLOCK_FOAM.get()) {
                            helper.setBlock(rel, state);
                            int wrongTool = breakAndCount(helper, rel, pickaxe, s.drop(), n + " with a wooden pickaxe");
                            check(wrongTool == 0, n + " with a wooden pickaxe dropped " + wrongTool + ", original none (crafted snow needs a shovel)");
                        }
                    }

                    // Multiblock: BlockDummyable.java:389-406 drops the core's item for any tool; the core is broken bare-handed.
                    DummyableBlock centrifuge = (DummyableBlock) NtmBlocks.MACHINE_CENTRIFUGE.get();
                    BlockPos core = new BlockPos(10, 2, 10);
                    SmokeTestSupport.place(helper, centrifuge, core, Direction.NORTH);
                    check(DummyableBlock.isCore(helper.getBlockState(core)), "the centrifuge core was not placed at " + core);
                    check(!breaker(helper, ItemStack.EMPTY).hasCorrectToolForDrops(helper.getBlockState(core)), "machine_centrifuge: an empty hand is a correct tool");
                    int multi = breakAndCount(helper, core, ItemStack.EMPTY, centrifuge.asItem(), "machine_centrifuge bare-handed");
                    check(multi == 1, "machine_centrifuge bare-handed dropped " + multi + " machine_centrifuge, original 1 (ungated onBlockHarvested)");
                    for(int dy = 1; dy <= 3; dy++) check(!helper.getBlockState(core.above(dy)).is(centrifuge), "a centrifuge dummy is left at " + core.above(dy));
                    discardItems(helper);
                    LOGGER.info("{} tool_drop_samples: {} gated samples drop nothing bare-handed and drop for a wooden tool; bobblehead and machine_centrifuge drop bare-handed; block_foam needs a shovel", TAG, samples.size() - 1);
                }))
                .thenExecute(passed("tool_drop_samples"))
                .thenSucceed();
    }
}
