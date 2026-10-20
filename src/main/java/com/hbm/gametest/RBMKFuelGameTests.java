package com.hbm.gametest;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.hbm.blockentity.machine.rbmk.IRBMKFluxReceiver.NType;
import com.hbm.blockentity.machine.rbmk.RBMKDials;
import com.hbm.config.NtmConfig;
import com.hbm.hazard.HazardEntry;
import com.hbm.hazard.HazardRegistry;
import com.hbm.hazard.HazardSystem;
import com.hbm.hazard.type.HazardTypeBase;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.recipes.PUREXRecipes;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.RBMKPelletItem;
import com.hbm.items.machine.RBMKRodItem;
import com.hbm.items.machine.RBMKRodItem.EnumBurnFunc;
import com.hbm.items.machine.RBMKRodItem.EnumDepleteFunc;
import com.hbm.main.NuclearTechMod;
import com.hbm.util.TagsUtil;
import com.mojang.logging.LogUtils;
import net.minecraft.ChatFormatting;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.TextColor;
import net.minecraft.network.chat.contents.TranslatableContents;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.animal.Pig;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.item.crafting.CraftingInput;
import net.minecraft.world.item.crafting.CraftingRecipe;
import net.minecraft.world.item.crafting.Ingredient;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.item.crafting.ShapedRecipe;
import net.minecraft.world.item.crafting.ShapelessRecipe;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import org.slf4j.Logger;

import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.TreeMap;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal24B, the RBMK fuel items (original ItemRBMKRod, ItemRBMKPellet, IRBMKFluxReceiver.NType,
 * HazardModifierRBMKRadiation, HazardModifierRBMKHot, HazardRegistry.java:379-444 and :569-592, ModItems.java:3028-3317, RodRecipes.java:89-120,
 * MineralRecipes.java:183-198, ToolRecipes.java:139-140, PUREXRecipes.java:44-48). Same template and conventions as {@link RTGPelletGameTests}.
 * <p>
 * Every expected number is computed from the ORIGINAL sources by {@code build/migration/goal24b/verifier-gt/gen_expected.py}, which parses the
 * original ModItems and HazardRegistry text and re-implements the original formulas with Java float and double semantics; the tables below are
 * its output and nothing is derived from the NEO classes. Doubles are compared with a relative tolerance of 1e-9 (absolute 1e-12 near zero),
 * hazard levels (floats) exactly.
 * <p>
 * Real engine evidence: the item registry, the recipe manager as the running dedicated GameTest server loaded the generated recipes (asked the way
 * a crafting table asks), the PUREX table, the hazard registry as {@code CommonEvents.commonSetup} filled it, the production item methods called
 * on real stacks (data components included), and a real Pig through {@code HazardSystem.applyHazards}. Tooltips are read as components with
 * {@code Item.TooltipContext.EMPTY}.
 * <p>
 * Not evidence: no fuel column exists yet (Goal24C), so burn, updateHeat and provideHeat are called directly; the models, ItemProperties
 * predicates, JEI subtypes and creative tab rendering are client-side; the tooltip text is not rendered (language values, colours as drawn and
 * the F3+H flag from a real client are untested); the durability bar is only read through the item methods; the stored custom data is only read
 * back inside the running server, never through a save and load. The expectations assume the default RBMK dials (reactivity 1.0, diffusion 1.0,
 * heat provision 0.2, xenon and depletion on); the tests that depend on them fail with a message when the running server differs.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class RBMKFuelGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String BATCH = "rbmk_fuel";

    // ModItems.java:3077-3317 as parsed by gen_expected.py (yield, reactivity, selfRate, function, depFunc, xGen, xBurn, heat, diffusion, melting point, nType, rType, tint, heat coefficient start and length).
    private record Rod(String id, String pellet, double rodYield, double reactivity, double selfRate, String function, String depFunc, double xGen, double xBurn,
                       double heat, double diffusion, double meltingPoint, String nType, String rType, int tint, double hcStart, double hcLen) { }

    // ModItems.java:3028-3058: id, xenon enabled (no .disableXenon()), the hard-coded full name.
    private record PelletRow(String id, boolean xenon, String fullName) { }

    // HazardRegistry.java:379-409 evaluated at enrichment 1, 0.5, 0 and at enrichment 0.5 with 50 % xenon, in float arithmetic.
    private record RodHazard(String id, float full, float half, float empty, float halfPoisoned) { }

    // HazardRegistry.java:413-443 evaluated at META 0..9 in float arithmetic.
    private record PelletHazard(String id, float... levels) { }

    // ItemRBMKRod.reactivityFunc (:284-301) at enrichment 1 and flux 0 / 25 / 50 / 100; a function name overrides the rod's own.
    private record Curve(String id, String function, double... values) { }

    // ItemRBMKRod.reactivityModByEnrichment (:352-362) at enrichment 0 / 0.25 / 0.5 / 1; id null means a function no ported rod uses (STATIC).
    private record Depletion(String function, String id, double... values) { }

    // ItemRBMKRod.burn (:152-198): a start state (NaN = not set) and the end state.
    private record BurnCase(String label, String id, boolean fresh, double startYield, double startXenon, double startCore, double startHull, double flux, double xGen,
                            double out, double poison, double yieldAfter, double coreAfter, double hullAfter) { }

    // ItemRBMKRod.updateHeat (:212-227).
    private record HeatCase(String id, double core, double hull, double mod, double coreAfter, double hullAfter) { }

    // ItemRBMKRod.provideHeat (:234-260).
    private record ProvideCase(String id, double core, double hull, double heat, double mod, double returned, double coreAfter, double hullAfter) { }

    private static final List<Rod> RODS = List.of(
            new Rod("rbmk_fuel_ueu", "rbmk_pellet_ueu", 100000000.0, 15.0, 0.0, "LOG_TEN", "RAISING_SLOPE", 0.5, 50.0, 0.65, 0.02, 2865.0, "SLOW", "FAST", 0x868D82, 0.0, 0.0),
            new Rod("rbmk_fuel_meu", "rbmk_pellet_meu", 100000000.0, 20.0, 0.0, "LOG_TEN", "RAISING_SLOPE", 0.5, 50.0, 0.65, 0.02, 2865.0, "SLOW", "FAST", 0x868D82, 0.0, 0.0),
            new Rod("rbmk_fuel_heu233", "rbmk_pellet_heu233", 100000000.0, 27.5, 0.0, "LINEAR", "GENTLE_SLOPE", 0.5, 50.0, 1.25, 0.02, 2865.0, "SLOW", "FAST", 0x868D82, 0.0, 0.0),
            new Rod("rbmk_fuel_heu235", "rbmk_pellet_heu235", 100000000.0, 50.0, 0.0, "SQUARE_ROOT", "GENTLE_SLOPE", 0.5, 50.0, 1.0, 0.02, 2865.0, "SLOW", "FAST", 0x868D82, 0.0, 0.0),
            new Rod("rbmk_fuel_uzh", "rbmk_pellet_uzh", 50000000.0, 30.0, 0.0, "LOG_TEN", "GENTLE_SLOPE", 0.5, 50.0, 0.75, 0.1, 1845.0, "SLOW", "FAST", 0x7077AF, 1000.0, 500.0),
            new Rod("rbmk_fuel_thmeu", "rbmk_pellet_thmeu", 100000000.0, 20.0, 0.0, "PLATEU", "BOOSTED_SLOPE", 0.5, 50.0, 0.65, 0.02, 3350.0, "SLOW", "FAST", 0x665448, 0.0, 0.0),
            new Rod("rbmk_fuel_lep", "rbmk_pellet_lep", 100000000.0, 35.0, 0.0, "LOG_TEN", "RAISING_SLOPE", 0.5, 50.0, 0.75, 0.02, 2744.0, "SLOW", "FAST", 0x656E6B, 0.0, 0.0),
            new Rod("rbmk_fuel_mep", "rbmk_pellet_mep", 100000000.0, 35.0, 0.0, "SQUARE_ROOT", "GENTLE_SLOPE", 0.5, 50.0, 1.0, 0.02, 2744.0, "SLOW", "FAST", 0x656E6B, 0.0, 0.0),
            new Rod("rbmk_fuel_hep239", "rbmk_pellet_hep239", 100000000.0, 30.0, 0.0, "LINEAR", "GENTLE_SLOPE", 0.5, 50.0, 1.25, 0.02, 2744.0, "SLOW", "FAST", 0x656E6B, 0.0, 0.0),
            new Rod("rbmk_fuel_hep241", "rbmk_pellet_hep241", 100000000.0, 40.0, 0.0, "LINEAR", "GENTLE_SLOPE", 0.5, 50.0, 1.75, 0.02, 2744.0, "SLOW", "FAST", 0x656E6B, 0.0, 0.0),
            new Rod("rbmk_fuel_lea", "rbmk_pellet_lea", 100000000.0, 60.0, 10.0, "SQUARE_ROOT", "RAISING_SLOPE", 0.5, 50.0, 1.5, 0.02, 2386.0, "SLOW", "FAST", 0xA88A8F, 0.0, 0.0),
            new Rod("rbmk_fuel_mea", "rbmk_pellet_mea", 100000000.0, 35.0, 20.0, "ARCH", "GENTLE_SLOPE", 0.5, 50.0, 1.75, 0.02, 2386.0, "SLOW", "FAST", 0xA88A8F, 0.0, 0.0),
            new Rod("rbmk_fuel_hea241", "rbmk_pellet_hea241", 100000000.0, 65.0, 15.0, "SQUARE_ROOT", "GENTLE_SLOPE", 0.5, 50.0, 1.85, 0.02, 2386.0, "FAST", "FAST", 0xA88A8F, 0.0, 0.0),
            new Rod("rbmk_fuel_hea242", "rbmk_pellet_hea242", 100000000.0, 45.0, 0.0, "LINEAR", "GENTLE_SLOPE", 0.5, 50.0, 2.0, 0.02, 2386.0, "SLOW", "FAST", 0xA88A8F, 0.0, 0.0),
            new Rod("rbmk_fuel_men", "rbmk_pellet_men", 100000000.0, 30.0, 0.0, "SQUARE_ROOT", "RAISING_SLOPE", 0.5, 50.0, 0.75, 0.02, 2800.0, "ANY", "FAST", 0x757E73, 0.0, 0.0),
            new Rod("rbmk_fuel_hen", "rbmk_pellet_hen", 100000000.0, 40.0, 0.0, "SQUARE_ROOT", "GENTLE_SLOPE", 0.5, 50.0, 1.0, 0.02, 2800.0, "FAST", "FAST", 0x757E73, 0.0, 0.0),
            new Rod("rbmk_fuel_mox", "rbmk_pellet_mox", 100000000.0, 40.0, 0.0, "LOG_TEN", "RAISING_SLOPE", 0.5, 50.0, 1.0, 0.02, 2815.0, "SLOW", "FAST", 0x868D82, 0.0, 0.0),
            new Rod("rbmk_fuel_les", "rbmk_pellet_les", 100000000.0, 50.0, 0.0, "SQUARE_ROOT", "GENTLE_SLOPE", 0.5, 50.0, 1.25, 0.02, 2500.0, "SLOW", "SLOW", 0x2D9A94, 0.0, 0.0),
            new Rod("rbmk_fuel_mes", "rbmk_pellet_mes", 100000000.0, 75.0, 0.0, "ARCH", "GENTLE_SLOPE", 0.5, 50.0, 1.5, 0.02, 2750.0, "SLOW", "FAST", 0x2D9A94, 0.0, 0.0),
            new Rod("rbmk_fuel_hes", "rbmk_pellet_hes", 100000000.0, 90.0, 0.0, "LINEAR", "LINEAR", 0.5, 50.0, 1.75, 0.02, 3000.0, "SLOW", "FAST", 0x2D9A94, 0.0, 0.0),
            new Rod("rbmk_fuel_leaus", "rbmk_pellet_leaus", 100000000.0, 30.0, 0.0, "SIGMOID", "LINEAR", 0.05, 50.0, 1.5, 0.02, 7029.0, "SLOW", "FAST", 0xFFEE00, 0.0, 0.0),
            new Rod("rbmk_fuel_heaus", "rbmk_pellet_heaus", 100000000.0, 35.0, 0.0, "LINEAR", "GENTLE_SLOPE", 0.05, 50.0, 1.5, 0.02, 5211.0, "SLOW", "FAST", 0xFFEE00, 0.0, 0.0),
            new Rod("rbmk_fuel_po210be", "rbmk_pellet_po210be", 25000000.0, 0.0, 50.0, "PASSIVE", "LINEAR", 0.0, 50.0, 0.1, 0.05, 1287.0, "SLOW", "SLOW", 0x563A26, 0.0, 0.0),
            new Rod("rbmk_fuel_ra226be", "rbmk_pellet_ra226be", 100000000.0, 0.0, 20.0, "PASSIVE", "LINEAR", 0.0, 50.0, 0.035, 0.5, 700.0, "SLOW", "SLOW", 0xB3B6AD, 0.0, 0.0),
            new Rod("rbmk_fuel_pu238be", "rbmk_pellet_pu238be", 50000000.0, 40.0, 40.0, "SQUARE_ROOT", "GENTLE_SLOPE", 0.5, 50.0, 0.1, 0.05, 1287.0, "SLOW", "SLOW", 0x656E6B, 0.0, 0.0),
            new Rod("rbmk_fuel_balefire_gold", "rbmk_pellet_balefire_gold", 100000000.0, 50.0, 10.0, "ARCH", "LINEAR", 0.0, 50.0, 1.0, 0.02, 2000.0, "SLOW", "FAST", 0xDC9613, 0.0, 0.0),
            new Rod("rbmk_fuel_flashlead", "rbmk_pellet_flashlead", 250000000.0, 40.0, 50.0, "ARCH", "LINEAR", 0.0, 50.0, 1.0, 0.02, 2050.0, "SLOW", "FAST", 0x7B7B87, 0.0, 0.0),
            new Rod("rbmk_fuel_balefire", "rbmk_pellet_balefire", 100000000.0, 100.0, 35.0, "LINEAR", "GENTLE_SLOPE", 0.0, 50.0, 3.0, 0.02, 3652.0, "SLOW", "FAST", 0xB2FF1B, 0.0, 0.0),
            new Rod("rbmk_fuel_zfb_bismuth", "rbmk_pellet_zfb_bismuth", 50000000.0, 20.0, 0.0, "SQUARE_ROOT", "GENTLE_SLOPE", 0.5, 50.0, 1.75, 0.02, 2744.0, "SLOW", "FAST", 0xAAA36A, 0.0, 0.0),
            new Rod("rbmk_fuel_zfb_pu241", "rbmk_pellet_zfb_pu241", 50000000.0, 20.0, 0.0, "SQUARE_ROOT", "GENTLE_SLOPE", 0.5, 50.0, 1.0, 0.02, 2865.0, "SLOW", "FAST", 0xAAA36A, 0.0, 0.0),
            new Rod("rbmk_fuel_zfb_am_mix", "rbmk_pellet_zfb_am_mix", 50000000.0, 20.0, 0.0, "LINEAR", "GENTLE_SLOPE", 0.5, 50.0, 1.75, 0.02, 2744.0, "SLOW", "FAST", 0xAAA36A, 0.0, 0.0)
    );

    private static final List<PelletRow> PELLETS = List.of(
            new PelletRow("rbmk_pellet_ueu", true, "Unenriched Uranium"),
            new PelletRow("rbmk_pellet_meu", true, "Medium Enriched Uranium-235"),
            new PelletRow("rbmk_pellet_heu233", true, "Highly Enriched Uranium-233"),
            new PelletRow("rbmk_pellet_heu235", true, "Highly Enriched Uranium-235"),
            new PelletRow("rbmk_pellet_uzh", true, "Uranium Zirconium Hydride"),
            new PelletRow("rbmk_pellet_thmeu", true, "Thorium with MEU Driver Fuel"),
            new PelletRow("rbmk_pellet_lep", true, "Low Enriched Plutonium-239"),
            new PelletRow("rbmk_pellet_mep", true, "Medium Enriched Plutonium-239"),
            new PelletRow("rbmk_pellet_hep239", true, "Highly Enriched Plutonium-239"),
            new PelletRow("rbmk_pellet_hep241", true, "Highly Enriched Plutonium-241"),
            new PelletRow("rbmk_pellet_lea", true, "Low Enriched Americium-242"),
            new PelletRow("rbmk_pellet_mea", true, "Medium Enriched Americium-242"),
            new PelletRow("rbmk_pellet_hea241", true, "Highly Enriched Americium-241"),
            new PelletRow("rbmk_pellet_hea242", true, "Highly Enriched Americium-242"),
            new PelletRow("rbmk_pellet_men", true, "Medium Enriched Neptunium-237"),
            new PelletRow("rbmk_pellet_hen", true, "Highly Enriched Neptunium-237"),
            new PelletRow("rbmk_pellet_mox", true, "Mixed MEU & LEP Oxide"),
            new PelletRow("rbmk_pellet_les", true, "Low Enriched Schrabidium-326"),
            new PelletRow("rbmk_pellet_mes", true, "Medium Enriched Schrabidium-326"),
            new PelletRow("rbmk_pellet_hes", true, "Highly Enriched Schrabidium-326"),
            new PelletRow("rbmk_pellet_leaus", true, "Low Enriched Australium (Tasmanite)"),
            new PelletRow("rbmk_pellet_heaus", true, "Highly Enriched Australium (Ayerite)"),
            new PelletRow("rbmk_pellet_po210be", false, "Polonium-210 & Beryllium Neutron Source"),
            new PelletRow("rbmk_pellet_ra226be", false, "Radium-226 & Beryllium Neutron Source"),
            new PelletRow("rbmk_pellet_pu238be", true, "Plutonium-238 & Beryllium Neutron Source"),
            new PelletRow("rbmk_pellet_balefire_gold", false, "Antihydrogen in a Magnetized Gold-198 Lattice"),
            new PelletRow("rbmk_pellet_flashlead", false, "Antihydrogen confined by a Magnetized Gold-198 and Lead-209 Lattice"),
            new PelletRow("rbmk_pellet_balefire", false, "Draconic Flames"),
            new PelletRow("rbmk_pellet_zfb_bismuth", true, "Zirconium Fast Breeder - LEU/HEP-241#Bi"),
            new PelletRow("rbmk_pellet_zfb_pu241", true, "Zirconium Fast Breeder - HEU-235/HEP-240#Pu-241"),
            new PelletRow("rbmk_pellet_zfb_am_mix", true, "Zirconium Fast Breeder - HEP-241#MEA")
    );

    private static final List<RodHazard> ROD_HAZARDS = List.of(
            new RodHazard("rbmk_fuel_ueu", 1.4F, 900.35F, 1200.0F, 1525.35F),
            new RodHazard("rbmk_fuel_meu", 2.0F, 968.0F, 1290.0F, 1593.0F),
            new RodHazard("rbmk_fuel_heu233", 20.0F, 1400.0F, 1860.0F, 2025.0F),
            new RodHazard("rbmk_fuel_heu235", 4.0F, 1351.0F, 1800.0F, 1976.0F),
            new RodHazard("rbmk_fuel_uzh", 0.5F, 900.125F, 1200.0F, 1525.125F),
            new RodHazard("rbmk_fuel_thmeu", 7.0F, 789.25F, 1050.0F, 1414.25F),
            new RodHazard("rbmk_fuel_lep", 17.0F, 1129.25F, 1500.0F, 1754.25F),
            new RodHazard("rbmk_fuel_mep", 25.0F, 1356.25F, 1800.0F, 1981.25F),
            new RodHazard("rbmk_fuel_hep239", 20.0F, 1467.5F, 1950.0F, 2092.5F),
            new RodHazard("rbmk_fuel_hep241", 100.0F, 1600.0F, 2100.0F, 2225.0F),
            new RodHazard("rbmk_fuel_lea", 19.0F, 1174.75F, 1560.0F, 1799.75F),
            new RodHazard("rbmk_fuel_mea", 36.0F, 1381.5F, 1830.0F, 2006.5F),
            new RodHazard("rbmk_fuel_hea241", 34.0F, 1516.0F, 2010.0F, 2141.0F),
            new RodHazard("rbmk_fuel_hea242", 38.0F, 1539.5F, 2040.0F, 2164.5F),
            new RodHazard("rbmk_fuel_men", 6.0F, 1014.0F, 1350.0F, 1639.0F),
            new RodHazard("rbmk_fuel_hen", 10.0F, 1352.5F, 1800.0F, 1977.5F),
            new RodHazard("rbmk_fuel_mox", 10.0F, 1150.0F, 1530.0F, 1775.0F),
            new RodHazard("rbmk_fuel_les", 23.4F, 1108.35F, 1470.0F, 1733.35F),
            new RodHazard("rbmk_fuel_mes", 23.4F, 1355.85F, 1800.0F, 1980.85F),
            new RodHazard("rbmk_fuel_hes", 23.4F, 2255.85F, 3000.0F, 2880.85F),
            new RodHazard("rbmk_fuel_leaus", 0F, 1687.5F, 2250.0F, 2312.5F),
            new RodHazard("rbmk_fuel_heaus", 0F, 1462.5F, 1950.0F, 2087.5F),
            new RodHazard("rbmk_fuel_po210be", 900.0F, 495.0F, 90.0F, 1120.0F),
            new RodHazard("rbmk_fuel_ra226be", 90.0F, 63.0F, 36.0F, 688.0F),
            new RodHazard("rbmk_fuel_pu238be", 120.0F, 142.5F, 150.0F, 767.5F),
            new RodHazard("rbmk_fuel_balefire_gold", 2000.0F, 301000.0F, 600000.0F, 301625.0F),
            new RodHazard("rbmk_fuel_flashlead", 50000.0F, 25100.0F, 200.0F, 25725.0F),
            new RodHazard("rbmk_fuel_balefire", 1200000.0F, 60600000.0F, 120000000.0F, 60600624.0F),
            new RodHazard("rbmk_fuel_zfb_bismuth", 10.0F, 227.5F, 300.0F, 852.5F),
            new RodHazard("rbmk_fuel_zfb_pu241", 2.0F, 338.0F, 450.0F, 963.0F),
            new RodHazard("rbmk_fuel_zfb_am_mix", 10.0F, 452.5F, 600.0F, 1077.5F)
    );

    private static final List<PelletHazard> PELLET_HAZARDS = List.of(
            new PelletHazard("rbmk_pellet_ueu", 0.175F, 37.63125F, 75.0875F, 112.54375F, 150.0F, 125.175F, 162.63126F, 200.0875F, 237.54375F, 275.0F),
            new PelletHazard("rbmk_pellet_meu", 0.25F, 40.5F, 80.75F, 121.0F, 161.25F, 125.25F, 165.5F, 205.75F, 246.0F, 286.25F),
            new PelletHazard("rbmk_pellet_heu233", 2.5F, 60.0F, 117.5F, 175.0F, 232.5F, 127.5F, 185.0F, 242.5F, 300.0F, 357.5F),
            new PelletHazard("rbmk_pellet_heu235", 0.5F, 56.625F, 112.75F, 168.875F, 225.0F, 125.5F, 181.625F, 237.75F, 293.875F, 350.0F),
            new PelletHazard("rbmk_pellet_uzh", 0.0625F, 37.546875F, 75.03125F, 112.515625F, 150.0F, 125.0625F, 162.54688F, 200.03125F, 237.51562F, 275.0F),
            new PelletHazard("rbmk_pellet_thmeu", 0.875F, 33.46875F, 66.0625F, 98.65625F, 131.25F, 125.875F, 158.46875F, 191.0625F, 223.65625F, 256.25F),
            new PelletHazard("rbmk_pellet_lep", 2.125F, 48.46875F, 94.8125F, 141.15625F, 187.5F, 127.125F, 173.46875F, 219.8125F, 266.15625F, 312.5F),
            new PelletHazard("rbmk_pellet_mep", 3.125F, 58.59375F, 114.0625F, 169.53125F, 225.0F, 128.125F, 183.59375F, 239.0625F, 294.53125F, 350.0F),
            new PelletHazard("rbmk_pellet_hep239", 2.5F, 62.8125F, 123.125F, 183.4375F, 243.75F, 127.5F, 187.8125F, 248.125F, 308.4375F, 368.75F),
            new PelletHazard("rbmk_pellet_hep241", 12.5F, 75.0F, 137.5F, 200.0F, 262.5F, 137.5F, 200.0F, 262.5F, 325.0F, 387.5F),
            new PelletHazard("rbmk_pellet_lea", 2.375F, 50.53125F, 98.6875F, 146.84375F, 195.0F, 127.375F, 175.53125F, 223.6875F, 271.84375F, 320.0F),
            new PelletHazard("rbmk_pellet_mea", 4.5F, 60.5625F, 116.625F, 172.6875F, 228.75F, 129.5F, 185.5625F, 241.625F, 297.6875F, 353.75F),
            new PelletHazard("rbmk_pellet_hea241", 4.25F, 66.0F, 127.75F, 189.5F, 251.25F, 129.25F, 191.0F, 252.75F, 314.5F, 376.25F),
            new PelletHazard("rbmk_pellet_hea242", 4.75F, 67.3125F, 129.875F, 192.4375F, 255.0F, 129.75F, 192.3125F, 254.875F, 317.4375F, 380.0F),
            new PelletHazard("rbmk_pellet_men", 0.75F, 42.75F, 84.75F, 126.75F, 168.75F, 125.75F, 167.75F, 209.75F, 251.75F, 293.75F),
            new PelletHazard("rbmk_pellet_hen", 1.25F, 57.1875F, 113.125F, 169.0625F, 225.0F, 126.25F, 182.1875F, 238.125F, 294.0625F, 350.0F),
            new PelletHazard("rbmk_pellet_mox", 1.25F, 48.75F, 96.25F, 143.75F, 191.25F, 126.25F, 173.75F, 221.25F, 268.75F, 316.25F),
            new PelletHazard("rbmk_pellet_les", 2.925F, 48.13125F, 93.3375F, 138.54375F, 183.75F, 127.925F, 173.13126F, 218.3375F, 263.54376F, 308.75F),
            new PelletHazard("rbmk_pellet_mes", 2.925F, 58.44375F, 113.9625F, 169.48125F, 225.0F, 127.925F, 183.44376F, 238.9625F, 294.48126F, 350.0F),
            new PelletHazard("rbmk_pellet_hes", 2.925F, 95.943756F, 188.96251F, 281.98126F, 375.0F, 127.925F, 220.94376F, 313.96252F, 406.98126F, 500.0F),
            new PelletHazard("rbmk_pellet_leaus", 0F, 70.3125F, 140.625F, 210.9375F, 281.25F, 125.0F, 195.3125F, 265.625F, 335.9375F, 406.25F),
            new PelletHazard("rbmk_pellet_heaus", 0F, 60.9375F, 121.875F, 182.8125F, 243.75F, 125.0F, 185.9375F, 246.875F, 307.8125F, 368.75F),
            new PelletHazard("rbmk_pellet_po210be", 112.5F, 87.1875F, 61.875F, 36.5625F, 11.25F, 237.5F, 212.1875F, 186.875F, 161.5625F, 136.25F),
            new PelletHazard("rbmk_pellet_ra226be", 11.25F, 9.5625F, 7.875F, 6.1875F, 4.5F, 136.25F, 134.5625F, 132.875F, 131.1875F, 129.5F),
            new PelletHazard("rbmk_pellet_pu238be", 15.0F, 16.875F, 18.75F, 20.625F, 22.5F, 140.0F, 141.875F, 143.75F, 145.625F, 147.5F),
            new PelletHazard("rbmk_pellet_balefire_gold", 250.0F, 18937.5F, 37625.0F, 56312.5F, 75000.0F, 375.0F, 19062.5F, 37750.0F, 56437.5F, 75125.0F),
            new PelletHazard("rbmk_pellet_flashlead", 6250.0F, 4700.0F, 3150.0F, 1600.0F, 50.0F, 6375.0F, 4825.0F, 3275.0F, 1725.0F, 175.0F),
            new PelletHazard("rbmk_pellet_balefire", 150000.0F, 3862500.0F, 7575000.0F, 11287500.0F, 15000000.0F, 150125.0F, 3862625.0F, 7575125.0F, 11287625.0F, 15000125.0F),
            new PelletHazard("rbmk_pellet_zfb_bismuth", 1.25F, 10.3125F, 19.375F, 28.4375F, 37.5F, 126.25F, 135.3125F, 144.375F, 153.4375F, 162.5F),
            new PelletHazard("rbmk_pellet_zfb_pu241", 0.25F, 14.25F, 28.25F, 42.25F, 56.25F, 125.25F, 139.25F, 153.25F, 167.25F, 181.25F),
            new PelletHazard("rbmk_pellet_zfb_am_mix", 1.25F, 19.6875F, 38.125F, 56.5625F, 75.0F, 126.25F, 144.6875F, 163.125F, 181.5625F, 200.0F)
    );

    private static final List<Curve> CURVES = List.of(
            new Curve("rbmk_fuel_ueu", null, 0.0, 10.612300109781135, 12.806776320734523, 15.03241030336982),
            new Curve("rbmk_fuel_thmeu", null, 0.0, 12.642411176571153, 17.293294335267746, 19.633687222225316),
            new Curve("rbmk_fuel_mea", null, 0.0, 8.728125, 17.4125, 34.65),
            new Curve("rbmk_fuel_leaus", null, 0.20078552772854572, 2.275745400637307, 15.0, 29.79921447227146),
            new Curve("rbmk_fuel_heu235", null, 0.0, 25.0, 35.35533905932738, 50.0),
            new Curve("rbmk_fuel_heu233", null, 0.0, 6.875, 13.75, 27.5),
            new Curve("rbmk_fuel_ra226be", null, 20.0, 20.0, 20.0, 20.0),
            new Curve("rbmk_fuel_ueu", "QUADRATIC", 0.0, 0.9375, 3.75, 15.0),
            new Curve("rbmk_fuel_ueu", "EXPERIMENTAL", 0.0, 325.36809371333516, 553.2188597220535, 740.4515383353618)
    );

    private static final List<Depletion> DEPLETIONS = List.of(
            new Depletion("LINEAR", "rbmk_fuel_hes", 0.0, 0.25, 0.5, 1.0),
            new Depletion("RAISING_SLOPE", "rbmk_fuel_ueu", 0.0, 0.6035533905932737, 1.0, 1.0),
            new Depletion("BOOSTED_SLOPE", "rbmk_fuel_thmeu", 1.2246467991473532e-16, 1.2307852804032304, 1.2071067811865475, 1.0),
            new Depletion("GENTLE_SLOPE", "rbmk_fuel_uzh", 0.0, 0.4857022603955159, 0.8333333333333333, 1.0),
            new Depletion("STATIC", null, 1.0, 1.0, 1.0, 1.0)
    );

    private static final List<BurnCase> BURNS = List.of(
            new BurnCase("fresh ueu flux 10", "rbmk_fuel_ueu", true, Double.NaN, Double.NaN, Double.NaN, Double.NaN, 10.0, Double.NaN, 7.810445138686688,
                    3.0, 99999990.0, 25.076789340146348, 20.0),
            new BurnCase("fresh ueu flux 100 (burn exceeds generation, poison clamps to 0)", "rbmk_fuel_ueu", true, Double.NaN, Double.NaN, Double.NaN, Double.NaN, 100.0, Double.NaN, 15.03241030336982,
                    0.0, 99999900.0, 29.771066697190385, 20.0),
            new BurnCase("fresh ra226be flux 0 (passive, self rate 20)", "rbmk_fuel_ra226be", true, Double.NaN, Double.NaN, Double.NaN, Double.NaN, 0.0, Double.NaN, 20.0,
                    0.0, 99999980.0, 20.7, 20.0),
            new BurnCase("ueu poison 50 flux 10 (poison level read before the new poison is stored)", "rbmk_fuel_ueu", false, Double.NaN, 50.0, Double.NaN, Double.NaN, 10.0, Double.NaN, 5.836134377877327,
                    50.5, 99999995.0, 23.793487345620264, 20.0),
            new BurnCase("ueu poison 99, xGen 1000, flux 1 (poison clamps to 100)", "rbmk_fuel_ueu", false, Double.NaN, 99.0, Double.NaN, Double.NaN, 1.0, 1000.0, 0.032410303369819336,
                    100.0, 99999999.99, 20.02106669719038, 20.0),
            new BurnCase("ueu yield 5 flux 10 (yield clamps to 0)", "rbmk_fuel_ueu", false, 5.0, Double.NaN, Double.NaN, Double.NaN, 10.0, Double.NaN, 4.1868072799513875e-06,
                    3.0, 0.0, 20.000002721424732, 20.0),
            new BurnCase("uzh core 999 (below the heat coefficient start)", "rbmk_fuel_uzh", false, Double.NaN, Double.NaN, 999.0, Double.NaN, 10.0, Double.NaN, 15.620890277373377,
                    3.0, 49999990.0, 1010.7156677080301, 20.0),
            new BurnCase("uzh core 1000 (progress 0)", "rbmk_fuel_uzh", false, Double.NaN, Double.NaN, 1000.0, Double.NaN, 10.0, Double.NaN, 15.620890277373377,
                    3.0, 49999990.0, 1011.7156677080301, 20.0),
            new BurnCase("uzh core 1250 (progress 0.5, multiplier sin(0.75 pi))", "rbmk_fuel_uzh", false, Double.NaN, Double.NaN, 1250.0, Double.NaN, 10.0, Double.NaN, 15.45497452152657,
                    3.0, 49999990.0, 1261.591230891145, 20.0),
            new BurnCase("uzh core 2000 (progress clamps to 1, multiplier sin(pi))", "rbmk_fuel_uzh", false, Double.NaN, Double.NaN, 2000.0, Double.NaN, 10.0, Double.NaN, 1.5911403198129218e-14,
                    3.0, 49999990.0, 2000.0, 20.0),
            new BurnCase("lea half depleted flux 4 (self rate 10, square root, raising slope)", "rbmk_fuel_lea", false, 50000000.0, 10.0, 300.0, Double.NaN, 4.0, Double.NaN, 21.297887219158618,
                    12.379999999999999, 49999987.4, 331.9468308287379, 20.0),
            new BurnCase("leaus fresh flux 30 (sigmoid with self rate 0, xGen 0.05)", "rbmk_fuel_leaus", true, Double.NaN, Double.NaN, Double.NaN, Double.NaN, 30.0, Double.NaN, 3.5760876606635272,
                    0.0, 99999970.0, 25.36413149099529, 20.0),
            new BurnCase("mea fresh flux 0 (arch, self rate 20)", "rbmk_fuel_mea", true, Double.NaN, Double.NaN, Double.NaN, Double.NaN, 0.0, Double.NaN, 6.986,
                    2.0, 99999980.0, 32.2255, 20.0),
            new BurnCase("hes quarter enrichment flux 40 (linear depletion)", "rbmk_fuel_hes", false, 25000000.0, Double.NaN, Double.NaN, Double.NaN, 40.0, Double.NaN, 9.0,
                    0.0, 24999960.0, 35.75, 20.0)
    );

    private static final List<HeatCase> UPDATE_HEATS = List.of(
            new HeatCase("rbmk_fuel_ueu", 1000.0, 20.0, 1.0, 990.2, 29.8),
            new HeatCase("rbmk_fuel_ueu", 1000.0, 20.0, 2.0, 980.4, 39.6),
            new HeatCase("rbmk_fuel_uzh", 500.0, 100.0, 1.0, 480.0, 120.0),
            new HeatCase("rbmk_fuel_ueu", 20.0, 100.0, 1.0, 20.0, 100.0),
            new HeatCase("rbmk_fuel_ueu", 50.0, 50.0, 1.0, 50.0, 50.0),
            new HeatCase("rbmk_fuel_ueu", 2000000.0, 20.0, 1.0, 1000000.0, 20019.8),
            new HeatCase("rbmk_fuel_ra226be", 100.0, 20.0, 1.0, 80.0, 40.0),
            new HeatCase("rbmk_fuel_po210be", 800.0, 300.0, 0.5, 793.75, 306.25)
    );

    private static final List<ProvideCase> PROVIDE_HEATS = List.of(
            new ProvideCase("rbmk_fuel_ueu", 1000.0, 1000.0, 20.0, 1.0, 98.0, 1000.0, 902.0),
            new ProvideCase("rbmk_fuel_ueu", 1000.0, 1000.0, 20.0, 0.5, 49.0, 1000.0, 951.0),
            new ProvideCase("rbmk_fuel_ueu", 20.0, 20.0, 20.0, 1.0, 0.0, 20.0, 20.0),
            new ProvideCase("rbmk_fuel_ueu", 20.0, 10.0, 20.0, 1.0, 0.0, 20.0, 10.0),
            new ProvideCase("rbmk_fuel_ueu", 4000.0, 3000.0, 20.0, 1.0, 2320.0, 2340.0, 2340.0),
            new ProvideCase("rbmk_fuel_ueu", 4000.0, 2865.0, 20.0, 1.0, 284.5, 4000.0, 2580.5),
            new ProvideCase("rbmk_fuel_po210be", 1500.0, 1300.0, 100.0, 1.0, 866.6666666666666, 966.6666666666666, 966.6666666666666),
            new ProvideCase("rbmk_fuel_ueu", 4000.0, 2866.0, 20.0, 1.0, 2275.3333333333335, 2295.3333333333335, 2295.3333333333335)
    );

    private static final double[] FLUX = { 0D, 25D, 50D, 100D };
    private static final double[] ENRICHMENT = { 0D, 0.25D, 0.5D, 1D };
    /** ItemRBMKRod.xenonGenFunc / xenonBurnFunc (:369-380) at flux 50: ueu gen, ueu burn, leaus gen. */
    private static final double[] XENON = { 25.0, 50.0, 2.5 };

    /** RodRecipes.java:90-120 (via :242-247): rod id suffix, the billet (or the balefire shard) that fills it, in the original line order. */
    private static final String[][] ROD_RECIPES = {
            { "ueu", "billet_uranium" }, { "meu", "billet_uranium_fuel" }, { "heu233", "billet_u233" }, { "heu235", "billet_u235" }, { "uzh", "billet_uzh" },
            { "thmeu", "billet_thorium_fuel" }, { "mox", "billet_mox_fuel" }, { "lep", "billet_plutonium_fuel" }, { "mep", "billet_pu_mix" },
            { "hep239", "billet_pu239" }, { "hep241", "billet_pu241" }, { "lea", "billet_americium_fuel" }, { "mea", "billet_am_mix" },
            { "hea241", "billet_am241" }, { "hea242", "billet_am242" }, { "men", "billet_neptunium_fuel" }, { "hen", "billet_neptunium" },
            { "po210be", "billet_po210be" }, { "ra226be", "billet_ra226be" }, { "pu238be", "billet_pu238be" },
            { "leaus", "billet_australium_lesser" }, { "heaus", "billet_australium_greater" }, { "balefire", "egg_balefire_shard" },
            { "les", "billet_les" }, { "mes", "billet_schrabidium_fuel" }, { "hes", "billet_hes" }, { "balefire_gold", "billet_balefire_gold" },
            { "flashlead", "billet_flashlead" }, { "zfb_bismuth", "billet_zfb_bismuth" }, { "zfb_pu241", "billet_zfb_pu241" }, { "zfb_am_mix", "billet_zfb_am_mix" }
    };

    // 1. Registration table

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rbmk_fuel_registration_table(GameTestHelper helper) {
        guard(() -> verifyRegistrationTable(helper)).run();
        done(helper, "rbmk_fuel_registration_table");
    }

    private static void verifyRegistrationTable(GameTestHelper helper) {
        check(RODS.size() == 31 && PELLETS.size() == 31 && ROD_RECIPES.length == 31, "the tables have " + RODS.size() + " rods, " + PELLETS.size() + " pellets, " + ROD_RECIPES.length + " recipes, expected 31 each");

        // Exactly the ported ids exist: no rbmk_fuel_drx / rbmk_fuel_test / rbmk_pellet_drx (GOAL24 decision 5, DRX deferred).
        Set<String> fuelIds = new HashSet<>();
        Set<String> pelletIds = new HashSet<>();
        for(ResourceLocation key : BuiltInRegistries.ITEM.keySet()) {
            if(!key.getNamespace().equals(NuclearTechMod.MODID)) continue;
            if(key.getPath().startsWith("rbmk_fuel_")) fuelIds.add(key.getPath());
            if(key.getPath().startsWith("rbmk_pellet_")) pelletIds.add(key.getPath());
        }
        Set<String> expectedFuel = new HashSet<>();
        expectedFuel.add("rbmk_fuel_empty");
        for(Rod row : RODS) expectedFuel.add(row.id());
        Set<String> expectedPellets = new HashSet<>();
        for(PelletRow row : PELLETS) expectedPellets.add(row.id());
        check(fuelIds.equals(expectedFuel), "the registered rbmk_fuel_* ids are " + fuelIds + ", expected the empty rod and the 31 rods");
        check(pelletIds.equals(expectedPellets), "the registered rbmk_pellet_* ids are " + pelletIds + ", expected the 31 pellets");

        // Enum order and values (ItemRBMKRod.java:262-271 and :344-350, IRBMKFluxReceiver.java:7-17).
        String[] burn = { "PASSIVE", "LOG_TEN", "PLATEU", "ARCH", "SIGMOID", "SQUARE_ROOT", "LINEAR", "QUADRATIC", "EXPERIMENTAL" };
        ChatFormatting[] colors = { ChatFormatting.DARK_GREEN, ChatFormatting.YELLOW, ChatFormatting.GREEN, ChatFormatting.RED, ChatFormatting.GREEN, ChatFormatting.YELLOW,
                ChatFormatting.RED, ChatFormatting.RED, ChatFormatting.RED };
        check(EnumBurnFunc.values().length == burn.length, "EnumBurnFunc has " + EnumBurnFunc.values().length + " values, expected 9");
        for(int i = 0; i < burn.length; i++) {
            EnumBurnFunc f = EnumBurnFunc.values()[i];
            check(f.name().equals(burn[i]) && f.color == colors[i], "EnumBurnFunc[" + i + "] is " + f + " " + f.color + ", expected " + burn[i] + " " + colors[i]);
            check(f.getTitle().getContents() instanceof TranslatableContents tc && tc.getKey().equals("trait.rbmk.func." + burn[i].toLowerCase()), burn[i] + " title is " + f.getTitle());
            check(hasColor(f.getTitle(), colors[i]), burn[i] + " title colour is " + f.getTitle().getStyle().getColor());
        }
        String[] deplete = { "LINEAR", "RAISING_SLOPE", "BOOSTED_SLOPE", "GENTLE_SLOPE", "STATIC" };
        check(EnumDepleteFunc.values().length == deplete.length, "EnumDepleteFunc has " + EnumDepleteFunc.values().length + " values, expected 5");
        for(int i = 0; i < deplete.length; i++) check(EnumDepleteFunc.values()[i].name().equals(deplete[i]), "EnumDepleteFunc[" + i + "] is " + EnumDepleteFunc.values()[i]);
        String[] ntypes = { "FAST", "SLOW", "ANY" };
        String[] ntypeKeys = { "trait.rbmk.neutron.fast", "trait.rbmk.neutron.slow", "trait.rbmk.neutron.any" };
        check(NType.values().length == 3, "NType has " + NType.values().length + " values, expected 3");
        for(int i = 0; i < 3; i++) check(NType.values()[i].name().equals(ntypes[i]) && NType.values()[i].unlocalized.equals(ntypeKeys[i]), "NType[" + i + "] is " + NType.values()[i] + " " + NType.values()[i].unlocalized);

        // ModItems.java:3077-3317, rod by rod.
        for(int i = 0; i < RODS.size(); i++) {
            Rod row = RODS.get(i);
            Item item = BuiltInRegistries.ITEM.get(id(row.id()));
            check(item instanceof RBMKRodItem && BuiltInRegistries.ITEM.getKey(item).equals(id(row.id())), row.id() + " is registered as " + item + " (" + BuiltInRegistries.ITEM.getKey(item) + ")");
            RBMKRodItem rod = (RBMKRodItem) item;
            String id = row.id();
            check(new ItemStack(rod).getMaxStackSize() == 1, id + " max stack size is " + new ItemStack(rod).getMaxStackSize() + ", expected 1");
            Item pellet = BuiltInRegistries.ITEM.get(id(row.pellet()));
            check(pellet instanceof RBMKPelletItem && rod.pellet == pellet, id + " pellet is " + rod.pellet + ", expected " + row.pellet());
            check(Double.compare(rod.yield, row.rodYield()) == 0, id + " yield " + rod.yield + ", expected " + row.rodYield());
            check(Double.compare(rod.reactivity, row.reactivity()) == 0, id + " reactivity " + rod.reactivity + ", expected " + row.reactivity());
            check(Double.compare(rod.selfRate, row.selfRate()) == 0, id + " selfRate " + rod.selfRate + ", expected " + row.selfRate());
            check(rod.function.name().equals(row.function()), id + " function " + rod.function + ", expected " + row.function());
            check(rod.depFunc.name().equals(row.depFunc()), id + " depFunc " + rod.depFunc + ", expected " + row.depFunc());
            check(Double.compare(rod.xGen, row.xGen()) == 0, id + " xGen " + rod.xGen + ", expected " + row.xGen());
            check(Double.compare(rod.xBurn, row.xBurn()) == 0, id + " xBurn " + rod.xBurn + ", expected " + row.xBurn());
            check(Double.compare(rod.heat, row.heat()) == 0, id + " heat " + rod.heat + ", expected " + row.heat());
            check(Double.compare(rod.diffusion, row.diffusion()) == 0, id + " diffusion " + rod.diffusion + ", expected " + row.diffusion());
            check(Double.compare(rod.meltingPoint, row.meltingPoint()) == 0, id + " meltingPoint " + rod.meltingPoint + ", expected " + row.meltingPoint());
            check(rod.nType.name().equals(row.nType()), id + " nType " + rod.nType + ", expected " + row.nType());
            check(rod.rType.name().equals(row.rType()), id + " rType " + rod.rType + ", expected " + row.rType());
            check(rod.colorTint == row.tint(), id + " colorTint 0x" + Integer.toHexString(rod.colorTint) + ", expected 0x" + Integer.toHexString(row.tint()));
            check(Double.compare(rod.heatCoeffStart, row.hcStart()) == 0 && Double.compare(rod.heatCoeffLength, row.hcLen()) == 0,
                    id + " heat coefficient " + rod.heatCoeffStart + "/" + rod.heatCoeffLength + ", expected " + row.hcStart() + "/" + row.hcLen());
            check(!rod.specialFluxCurve, id + " has a special flux curve");

            // The crafting remainder is the empty rod (ItemRBMKRod.java:75).
            ItemStack remainder = new ItemStack(rod).getCraftingRemainingItem();
            check(remainder.is(item("rbmk_fuel_empty")) && remainder.getCount() == 1, id + " crafting remainder is " + remainder + ", expected rbmk_fuel_empty");

            check(RBMKRodItem.CRAFTABLE_RODS.size() == 31 && RBMKRodItem.CRAFTABLE_RODS.get(i) == rod, "CRAFTABLE_RODS[" + i + "] is " + (RBMKRodItem.CRAFTABLE_RODS.size() > i ? RBMKRodItem.CRAFTABLE_RODS.get(i) : null) + ", expected " + id);
        }

        // The empty rod is a plain item with the default stack size (ModItems.java:3076); the pellets keep the default size 64 and META 0.
        Item empty = item("rbmk_fuel_empty");
        check(empty.getClass() == Item.class && new ItemStack(empty).getMaxStackSize() == 64, "rbmk_fuel_empty is " + empty.getClass().getSimpleName() + " with stack size " + new ItemStack(empty).getMaxStackSize());
        for(PelletRow row : PELLETS) {
            Item item = BuiltInRegistries.ITEM.get(id(row.id()));
            check(item instanceof RBMKPelletItem && BuiltInRegistries.ITEM.getKey(item).equals(id(row.id())), row.id() + " is registered as " + item);
            RBMKPelletItem pellet = (RBMKPelletItem) item;
            check(pellet.isXenonEnabled() == row.xenon(), row.id() + " xenon enabled is " + pellet.isXenonEnabled() + ", expected " + row.xenon());
            ItemStack stack = new ItemStack(pellet);
            check(stack.getMaxStackSize() == 64, row.id() + " max stack size is " + stack.getMaxStackSize() + ", expected 64");
            check(MetaHelper.getMeta(stack) == 0, row.id() + " fresh META is " + MetaHelper.getMeta(stack));
        }
    }

    // 2. Defaults, the schema of the custom data, the tooltip

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rbmk_fuel_defaults_and_schema(GameTestHelper helper) {
        guard(() -> verifyDefaultsAndSchema(helper)).run();
        done(helper, "rbmk_fuel_defaults_and_schema");
    }

    private static void verifyDefaultsAndSchema(GameTestHelper helper) {
        RBMKRodItem ueu = rod("rbmk_fuel_ueu");
        ItemStack stack = new ItemStack(ueu);

        // ItemRBMKRod.java:524-597 / GOAL24 decision 13: a fresh stack has no custom data and every read gives the default without writing.
        check(!TagsUtil.hasCustomData(stack), "a fresh rod has custom data " + TagsUtil.getCustomData(stack));
        check(Double.compare(RBMKRodItem.getYield(stack), 1e8) == 0, "fresh yield " + RBMKRodItem.getYield(stack));
        check(Double.compare(RBMKRodItem.getEnrichment(stack), 1.0) == 0, "fresh enrichment " + RBMKRodItem.getEnrichment(stack));
        check(Double.compare(RBMKRodItem.getCoreHeat(stack), 20.0) == 0, "fresh core heat " + RBMKRodItem.getCoreHeat(stack));
        check(Double.compare(RBMKRodItem.getHullHeat(stack), 20.0) == 0, "fresh hull heat " + RBMKRodItem.getHullHeat(stack));
        check(Double.compare(RBMKRodItem.getPoison(stack), 0.0) == 0 && Double.compare(RBMKRodItem.getPoisonLevel(stack), 0.0) == 0, "fresh poison " + RBMKRodItem.getPoison(stack));
        check(!ueu.isBarVisible(stack), "a fresh rod shows its durability bar");
        check(!TagsUtil.hasCustomData(stack), "reading wrote custom data " + TagsUtil.getCustomData(stack));
        check(RBMKRodItem.getYield(new ItemStack(Items.STICK)) == 0D, "getYield of a non-rod is " + RBMKRodItem.getYield(new ItemStack(Items.STICK)) + " (ItemRBMKRod.java:528-535)");

        // The durability bar is read-only as well.
        ueu.getBarWidth(stack);
        ueu.getBarColor(stack);
        check(!TagsUtil.hasCustomData(stack), "the durability bar wrote custom data");

        // Tooltip of a fresh ueu rod, ItemRBMKRod.java:475-497 (14 lines, no wasteCooling and no source line for a cold rod).
        List<Component> lines = tooltip(stack);
        check(lines.size() == 14, "the fresh ueu tooltip has " + lines.size() + " lines, expected 14: " + lines);
        expectLine(lines.get(0), "item.hbmsntm.rbmk_pellet_ueu.fullName", null, true);
        expectLine(lines.get(1), "trait.rbmk.depletion", ChatFormatting.GREEN, false, "0.0%");
        expectLine(lines.get(2), "trait.rbmk.xenon", ChatFormatting.DARK_PURPLE, false, "0.0%");
        expectLine(lines.get(3), "trait.rbmk.splitsWith", ChatFormatting.BLUE, false, comp("trait.rbmk.neutron.slow"));
        expectLine(lines.get(4), "trait.rbmk.splitsInto", ChatFormatting.BLUE, false, comp("trait.rbmk.neutron.fast"));
        expectLine(lines.get(5), "trait.rbmk.fluxFunc", ChatFormatting.YELLOW, false, comp("trait.rbmk.funcDesc.log_ten", "x", "15.0"));
        expectLine(lines.get(6), "trait.rbmk.funcType", ChatFormatting.YELLOW, false, comp("trait.rbmk.func.log_ten"));
        expectLine(lines.get(7), "trait.rbmk.xenonGen", ChatFormatting.YELLOW, false, literal("x * 0.5"));
        expectLine(lines.get(8), "trait.rbmk.xenonBurn", ChatFormatting.YELLOW, false, literal("x² / 50.0"));
        expectLine(lines.get(9), "trait.rbmk.heat", ChatFormatting.GOLD, false, "0.65°C");
        expectLine(lines.get(10), "trait.rbmk.diffusion", ChatFormatting.GOLD, false, "0.02¹/²");
        expectLine(lines.get(11), "trait.rbmk.skinTemp", ChatFormatting.RED, false, "20.0°C");
        expectLine(lines.get(12), "trait.rbmk.coreTemp", ChatFormatting.RED, false, "20.0°C");
        expectLine(lines.get(13), "trait.rbmk.melt", ChatFormatting.DARK_RED, false, "2865.0°C");
        check(!TagsUtil.hasCustomData(stack), "the tooltip wrote custom data " + TagsUtil.getCustomData(stack));

        // The advanced flag adds nothing to a rod either (the original has no advanced lines).
        List<Component> advanced = new ArrayList<>();
        stack.getItem().appendHoverText(stack, Item.TooltipContext.EMPTY, advanced, TooltipFlag.ADVANCED);
        check(advanced.size() == 14, "the advanced ueu tooltip has " + advanced.size() + " lines, expected 14");

        // One setter call writes all four keys, the three others with their defaults (ItemRBMKRod.java:591-597, 571-577).
        RBMKRodItem.setCoreHeat(stack, 30D);
        CompoundTag tag = TagsUtil.getCustomData(stack);
        check(tag.getAllKeys().equals(Set.of("yield", "xenon", "core", "hull")), "the custom data keys are " + tag.getAllKeys() + ", expected yield, xenon, core, hull");
        for(String key : List.of("yield", "xenon", "core", "hull")) check(tag.contains(key, Tag.TAG_DOUBLE), "key " + key + " is not a double: " + tag.get(key));
        check(tag.getDouble("yield") == 1e8 && tag.getDouble("xenon") == 0D && tag.getDouble("core") == 30D && tag.getDouble("hull") == 20D, "the written data is " + tag);

        // Each of the four setters writes its own key and keeps the rest.
        RBMKRodItem.setYield(stack, 5e7);
        RBMKRodItem.setPoison(stack, 12.5);
        RBMKRodItem.setHullHeat(stack, 44D);
        tag = TagsUtil.getCustomData(stack);
        check(tag.getDouble("yield") == 5e7 && tag.getDouble("xenon") == 12.5 && tag.getDouble("core") == 30D && tag.getDouble("hull") == 44D && tag.size() == 4, "after the four setters the data is " + tag);
        check(RBMKRodItem.getYield(stack) == 5e7 && RBMKRodItem.getPoison(stack) == 12.5 && RBMKRodItem.getCoreHeat(stack) == 30D && RBMKRodItem.getHullHeat(stack) == 44D, "the getters do not return the stored values");
        check(Math.abs(RBMKRodItem.getEnrichment(stack) - 0.5) < 1e-12 && Math.abs(RBMKRodItem.getPoisonLevel(stack) - 0.125) < 1e-12, "enrichment " + RBMKRodItem.getEnrichment(stack) + " / poison level " + RBMKRodItem.getPoisonLevel(stack));

        // NEO schema: the keys sit next to foreign custom data, which a write must keep (the stack is saved whole by the column in Goal24C).
        ItemStack shared = new ItemStack(ueu);
        CompoundTag foreign = new CompoundTag();
        foreign.putString("foreign", "kept");
        TagsUtil.putCustomData(shared, foreign);
        RBMKRodItem.setCoreHeat(shared, 77D);
        tag = TagsUtil.getCustomData(shared);
        check("kept".equals(tag.getString("foreign")) && tag.getDouble("core") == 77D && tag.getDouble("yield") == 1e8 && tag.getDouble("hull") == 20D, "foreign custom data was lost or the defaults are missing: " + tag);
    }

    // 3. Tooltips with state, source lines and the flux function descriptions

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rbmk_fuel_tooltips(GameTestHelper helper) {
        guard(() -> verifyTooltips(helper)).run();
        done(helper, "rbmk_fuel_tooltips");
    }

    private static void verifyTooltips(GameTestHelper helper) {
        // ueu at half yield, 12.5 % xenon, hot: ItemRBMKRod.java:477-497 and getFuncDescription :329-341 (raising slope at 0.5 gives 1.0).
        ItemStack hot = new ItemStack(rod("rbmk_fuel_ueu"));
        RBMKRodItem.setYield(hot, 5e7);
        RBMKRodItem.setPoison(hot, 12.5);
        RBMKRodItem.setCoreHeat(hot, 60D);
        RBMKRodItem.setHullHeat(hot, 55D);
        List<Component> lines = tooltip(hot);
        check(lines.size() == 15, "the used ueu tooltip has " + lines.size() + " lines, expected 15: " + lines);
        expectLine(lines.get(0), "item.hbmsntm.rbmk_pellet_ueu.fullName", null, true);
        expectLine(lines.get(1), "desc.item.wasteCooling", ChatFormatting.GOLD, false);
        expectLine(lines.get(2), "trait.rbmk.depletion", ChatFormatting.GREEN, false, "50.0%");
        expectLine(lines.get(3), "trait.rbmk.xenon", ChatFormatting.DARK_PURPLE, false, "12.5%");
        TranslatableContents flux = tr(lines.get(6), "fluxFunc");
        check(flux.getArgs().length == 1 && flux.getArgs()[0] instanceof Component, "fluxFunc has the arguments " + java.util.Arrays.toString(flux.getArgs()));
        Component desc = (Component) flux.getArgs()[0];
        TranslatableContents descContents = tr(desc, "the flux function description");
        check(descContents.getKey().equals("trait.rbmk.funcDesc.log_ten") && descContents.getArgs().length == 2
                        && descContents.getArgs()[0].equals("(x * §e1.0§f)") && descContents.getArgs()[1].equals("15.0"),
                "the description is " + descContents.getKey() + " " + java.util.Arrays.toString(descContents.getArgs()) + ", expected (x * §e1.0§f) and 15.0");
        check(desc.getSiblings().size() == 1 && desc.getSiblings().get(0).getString().equals("§6 (100.0%)"), "the enrichment suffix is " + desc.getSiblings() + ", expected §6 (100.0%)");
        expectLine(lines.get(12), "trait.rbmk.skinTemp", ChatFormatting.RED, false, "55.0°C");
        expectLine(lines.get(13), "trait.rbmk.coreTemp", ChatFormatting.RED, false, "60.0°C");
        // The core exceeds 50 on its own as well (core >= 50 || hull >= 50), and a cold rod shows no cooling line.
        ItemStack coreOnly = new ItemStack(rod("rbmk_fuel_ueu"));
        RBMKRodItem.setCoreHeat(coreOnly, 50D);
        check(tooltip(coreOnly).size() == 15, "core 50 / hull 20 gives " + tooltip(coreOnly).size() + " lines, expected 15 (cooling line)");
        RBMKRodItem.setCoreHeat(coreOnly, 49.9D);
        check(tooltip(coreOnly).size() == 14, "core 49.9 / hull 20 gives " + tooltip(coreOnly).size() + " lines, expected 14");

        // lea (self rate 10, square root): source line, flux "(x" + RED + " + 10.0" + WHITE + ")" (:330).
        List<Component> lea = tooltip(new ItemStack(rod("rbmk_fuel_lea")));
        check(lea.size() == 15, "the lea tooltip has " + lea.size() + " lines, expected 15");
        expectLine(lea.get(1), "trait.rbmk.source", ChatFormatting.RED, false);
        TranslatableContents leaFlux = tr((Component) tr(lea.get(6), "lea fluxFunc").getArgs()[0], "lea description");
        check(leaFlux.getKey().equals("trait.rbmk.funcDesc.square_root") && leaFlux.getArgs()[0].equals("(x§c + 10.0§f)") && leaFlux.getArgs()[1].equals("60.0"),
                "the lea description is " + leaFlux.getKey() + " " + java.util.Arrays.toString(leaFlux.getArgs()));

        // leaus (sigmoid, self rate 0): the source line comes from the function alone (:481).
        List<Component> leaus = tooltip(new ItemStack(rod("rbmk_fuel_leaus")));
        check(leaus.size() == 15, "the leaus tooltip has " + leaus.size() + " lines, expected 15");
        expectLine(leaus.get(1), "trait.rbmk.source", ChatFormatting.RED, false);
        TranslatableContents leausFlux = tr((Component) tr(leaus.get(6), "leaus fluxFunc").getArgs()[0], "leaus description");
        check(leausFlux.getKey().equals("trait.rbmk.funcDesc.sigmoid") && leausFlux.getArgs()[0].equals("x") && leausFlux.getArgs()[1].equals("30.0"), "the leaus description is " + leausFlux.getKey() + " " + java.util.Arrays.toString(leausFlux.getArgs()));
        expectLine(leaus.get(7), "trait.rbmk.funcType", ChatFormatting.YELLOW, false, comp("trait.rbmk.func.sigmoid"));
        check(tr((Component) tr(leaus.get(7), "leaus funcType").getArgs()[0], "title").getKey().equals("trait.rbmk.func.sigmoid")
                && hasColor((Component) tr(leaus.get(7), "leaus funcType").getArgs()[0], ChatFormatting.GREEN), "the sigmoid title is not green");
        expectLine(leaus.get(8), "trait.rbmk.xenonGen", ChatFormatting.YELLOW, false, literal("x * 0.05"));

        // ra226be (passive): the description is the literal self rate in red (:308).
        List<Component> ra = tooltip(new ItemStack(rod("rbmk_fuel_ra226be")));
        Component raDesc = (Component) tr(ra.get(6), "ra226be fluxFunc").getArgs()[0];
        check(!(raDesc.getContents() instanceof TranslatableContents) && raDesc.getString().equals("§c20.0"), "the ra226be description is " + raDesc + ", expected the literal §c20.0");
        check(tr((Component) tr(ra.get(7), "ra226be funcType").getArgs()[0], "title").getKey().equals("trait.rbmk.func.passive"), "the ra226be function title is not passive");
    }

    // 4. Curves, depletion functions and xenon functions

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rbmk_fuel_curves(GameTestHelper helper) {
        guard(() -> verifyCurves(helper)).run();
        done(helper, "rbmk_fuel_curves");
    }

    private static void verifyCurves(GameTestHelper helper) {
        requireDefaultDials();
        for(Curve curve : CURVES) {
            RBMKRodItem rod = rod(curve.id());
            EnumBurnFunc saved = rod.function;
            try {
                if(curve.function() != null) rod.function = EnumBurnFunc.valueOf(curve.function());
                for(int i = 0; i < FLUX.length; i++) {
                    double actual = rod.reactivityFunc(FLUX[i], 1D);
                    near(actual, curve.values()[i], curve.id() + " " + rod.function + " at flux " + FLUX[i]);
                }
            } finally {
                rod.function = saved;
            }
        }
        check(CURVES.size() == 9, "the curve table has " + CURVES.size() + " rows, expected 9");

        for(Depletion dep : DEPLETIONS) {
            RBMKRodItem rod = rod(dep.id() != null ? dep.id() : "rbmk_fuel_ueu");
            EnumDepleteFunc saved = rod.depFunc;
            try {
                if(dep.id() == null) rod.depFunc = EnumDepleteFunc.valueOf(dep.function());
                check(rod.depFunc.name().equals(dep.function()), rod.depFunc + " is not " + dep.function());
                for(int i = 0; i < ENRICHMENT.length; i++) near(rod.reactivityModByEnrichment(ENRICHMENT[i]), dep.values()[i], dep.function() + " at enrichment " + ENRICHMENT[i]);
            } finally {
                rod.depFunc = saved;
            }
        }

        // The enrichment enters reactivityFunc through the depletion function: ueu (raising slope) at enrichment 0.5 sees the full flux (1.0).
        near(rod("rbmk_fuel_ueu").reactivityFunc(100D, 0.5D), 15.03241030336982, "ueu at flux 100 and enrichment 0.5");
        near(rod("rbmk_fuel_heu233").reactivityFunc(100D, 0D), 0D, "heu233 at enrichment 0");

        // Xenon functions, ItemRBMKRod.java:369-380.
        near(rod("rbmk_fuel_ueu").xenonGenFunc(50D), XENON[0], "ueu xenonGenFunc(50)");
        near(rod("rbmk_fuel_ueu").xenonBurnFunc(50D), XENON[1], "ueu xenonBurnFunc(50)");
        near(rod("rbmk_fuel_leaus").xenonGenFunc(50D), XENON[2], "leaus xenonGenFunc(50)");
    }

    // 5. burn

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rbmk_fuel_burn(GameTestHelper helper) {
        guard(() -> verifyBurn(helper)).run();
        done(helper, "rbmk_fuel_burn");
    }

    private static void verifyBurn(GameTestHelper helper) {
        requireDefaultDials();
        Level level = helper.getLevel();
        for(BurnCase c : BURNS) {
            RBMKRodItem rod = rod(c.id());
            ItemStack stack = new ItemStack(rod);
            if(!c.fresh()) {
                if(!Double.isNaN(c.startYield())) RBMKRodItem.setYield(stack, c.startYield());
                if(!Double.isNaN(c.startXenon())) RBMKRodItem.setPoison(stack, c.startXenon());
                if(!Double.isNaN(c.startCore())) RBMKRodItem.setCoreHeat(stack, c.startCore());
                if(!Double.isNaN(c.startHull())) RBMKRodItem.setHullHeat(stack, c.startHull());
            } else {
                check(!TagsUtil.hasCustomData(stack), c.label() + ": the fresh stack has custom data");
            }
            double savedGen = rod.xGen;
            double out;
            try {
                if(!Double.isNaN(c.xGen())) rod.xGen = c.xGen();
                out = rod.burn(level, stack, c.flux());
            } finally {
                rod.xGen = savedGen;
            }
            near(out, c.out(), c.label() + ": outFlux");
            near(RBMKRodItem.getPoison(stack), c.poison(), c.label() + ": poison");
            nearAbs(RBMKRodItem.getYield(stack), c.yieldAfter(), c.label() + ": yield");
            near(RBMKRodItem.getCoreHeat(stack), c.coreAfter(), c.label() + ": core heat");
            near(RBMKRodItem.getHullHeat(stack), c.hullAfter(), c.label() + ": hull heat");
            CompoundTag tag = TagsUtil.getCustomData(stack);
            check(tag.getAllKeys().equals(Set.of("yield", "xenon", "core", "hull")), c.label() + ": the custom data keys are " + tag.getAllKeys());
            LOGGER.info("[hbm-rbmk-fuel] burn {}: out {} poison {} yield {} core {} hull {}", c.label(), out, RBMKRodItem.getPoison(stack), RBMKRodItem.getYield(stack), RBMKRodItem.getCoreHeat(stack), RBMKRodItem.getHullHeat(stack));
        }
        check(rod("rbmk_fuel_ueu").xGen == 0.5D && rod("rbmk_fuel_uzh").function == EnumBurnFunc.LOG_TEN, "a mutated rod field was not restored");
    }

    // 6. updateHeat, provideHeat

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rbmk_fuel_heat(GameTestHelper helper) {
        guard(() -> verifyHeat(helper)).run();
        done(helper, "rbmk_fuel_heat");
    }

    private static void verifyHeat(GameTestHelper helper) {
        requireDefaultDials();
        Level level = helper.getLevel();
        for(HeatCase c : UPDATE_HEATS) {
            RBMKRodItem rod = rod(c.id());
            ItemStack stack = new ItemStack(rod);
            RBMKRodItem.setCoreHeat(stack, c.core());
            RBMKRodItem.setHullHeat(stack, c.hull());
            rod.updateHeat(level, stack, c.mod());
            String label = c.id() + " updateHeat(core " + c.core() + ", hull " + c.hull() + ", mod " + c.mod() + ")";
            near(RBMKRodItem.getCoreHeat(stack), c.coreAfter(), label + " core");
            near(RBMKRodItem.getHullHeat(stack), c.hullAfter(), label + " hull");
        }
        for(ProvideCase c : PROVIDE_HEATS) {
            RBMKRodItem rod = rod(c.id());
            ItemStack stack = new ItemStack(rod);
            RBMKRodItem.setCoreHeat(stack, c.core());
            RBMKRodItem.setHullHeat(stack, c.hull());
            double returned = rod.provideHeat(level, stack, c.heat(), c.mod());
            String label = c.id() + " provideHeat(core " + c.core() + ", hull " + c.hull() + ", heat " + c.heat() + ", mod " + c.mod() + ")";
            near(returned, c.returned(), label + " returned");
            near(RBMKRodItem.getCoreHeat(stack), c.coreAfter(), label + " core");
            near(RBMKRodItem.getHullHeat(stack), c.hullAfter(), label + " hull");
        }

        // NEO decision 13: when nothing changes, nothing is written (the original wrote the defaults on every first read).
        ItemStack fresh = new ItemStack(rod("rbmk_fuel_ueu"));
        rod("rbmk_fuel_ueu").updateHeat(level, fresh, 1D);
        check(!TagsUtil.hasCustomData(fresh), "updateHeat on a fresh rod (core == hull) wrote " + TagsUtil.getCustomData(fresh));
        check(rod("rbmk_fuel_ueu").provideHeat(level, fresh, 20D, 1D) == 0D && !TagsUtil.hasCustomData(fresh), "provideHeat on a fresh rod (hull 20 <= heat 20) returned or wrote something");
    }

    // 7. rectify and the durability bar

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rbmk_fuel_rectify_and_bar(GameTestHelper helper) {
        guard(() -> verifyRectifyAndBar(helper)).run();
        done(helper, "rbmk_fuel_rectify_and_bar");
    }

    private static void verifyRectifyAndBar(GameTestHelper helper) {
        requireDefaultDials();
        Level level = helper.getLevel();
        RBMKRodItem ueu = rod("rbmk_fuel_ueu");

        // ItemRBMKRod.rectify (:200-206) as seen through burn(0): an outFlux of 0 leaves the core heat to rectify alone.
        ItemStack nan = new ItemStack(ueu);
        RBMKRodItem.setCoreHeat(nan, Double.NaN);
        ueu.burn(level, nan, 0D);
        check(RBMKRodItem.getCoreHeat(nan) == 20D, "a NaN core heat rectifies to " + RBMKRodItem.getCoreHeat(nan) + ", expected 20");
        ItemStack low = new ItemStack(ueu);
        RBMKRodItem.setCoreHeat(low, 5D);
        ueu.burn(level, low, 0D);
        check(RBMKRodItem.getCoreHeat(low) == 20D, "core heat 5 rectifies to " + RBMKRodItem.getCoreHeat(low) + ", expected 20");
        ItemStack high = new ItemStack(ueu);
        RBMKRodItem.setCoreHeat(high, 1_500_000D);
        ueu.burn(level, high, 0D);
        check(RBMKRodItem.getCoreHeat(high) == 1_000_000D, "core heat 1.5 million rectifies to " + RBMKRodItem.getCoreHeat(high) + ", expected 1000000");
        ItemStack edge = new ItemStack(ueu);
        RBMKRodItem.setCoreHeat(edge, 1_000_000D);
        ueu.burn(level, edge, 0D);
        check(RBMKRodItem.getCoreHeat(edge) == 1_000_000D, "core heat 1000000 changed to " + RBMKRodItem.getCoreHeat(edge));

        // updateHeat clamps through rectify: core 2e6 / hull 20 gives 1,000,000 and 20019.8 (see the UPDATE_HEATS table, checked in rbmk_fuel_heat).
        ItemStack hot = new ItemStack(ueu);
        RBMKRodItem.setCoreHeat(hot, 2_000_000D);
        ueu.updateHeat(level, hot, 1D);
        check(RBMKRodItem.getCoreHeat(hot) == 1_000_000D, "updateHeat clamped the core to " + RBMKRodItem.getCoreHeat(hot));
        near(RBMKRodItem.getHullHeat(hot), 20019.8D, "hull after the clamped updateHeat");

        // Durability bar, ItemRBMKRod.java:561-569 with the 1.7.10 RenderItem blend: width round(13 - health * 13), colour (255 - k) << 16 | k << 8, k = round(255 - health * 255).
        Object[][] bars = {
                { 1e8, false, 0, 0 },
                { 99_999_999D, true, 13, 0x00FF00 },
                { 7.5e7, true, 10, 0x40BF00 },
                { 5e7, true, 7, 0x7F8000 },
                { 2.5e7, true, 3, 0xBF4000 },
                { 0D, true, 0, 0xFF0000 }
        };
        for(Object[] bar : bars) {
            ItemStack stack = new ItemStack(ueu);
            RBMKRodItem.setYield(stack, (Double) bar[0]);
            boolean visible = ueu.isBarVisible(stack);
            check(visible == (Boolean) bar[1], "yield " + bar[0] + ": the bar visible is " + visible + ", expected " + bar[1]);
            if(!visible) continue;
            check(ueu.getBarWidth(stack) == (Integer) bar[2], "yield " + bar[0] + ": the bar width is " + ueu.getBarWidth(stack) + ", expected " + bar[2]);
            check(ueu.getBarColor(stack) == (Integer) bar[3], "yield " + bar[0] + ": the bar colour is 0x" + Integer.toHexString(ueu.getBarColor(stack)) + ", expected 0x" + Integer.toHexString((Integer) bar[3]));
        }
        // po210be has a smaller yield (2.5e7): half of it is a depletion of 0.5 as well.
        RBMKRodItem po = rod("rbmk_fuel_po210be");
        ItemStack halfPo = new ItemStack(po);
        RBMKRodItem.setYield(halfPo, 1.25e7);
        check(po.isBarVisible(halfPo) && po.getBarWidth(halfPo) == 7 && po.getBarColor(halfPo) == 0x7F8000, "po210be at half yield: width " + po.getBarWidth(halfPo) + " colour 0x" + Integer.toHexString(po.getBarColor(halfPo)));
    }

    // 8. Hazards

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rbmk_fuel_hazard_levels(GameTestHelper helper) {
        guard(() -> verifyHazardLevels(helper)).run();
        done(helper, "rbmk_fuel_hazard_levels");
    }

    private static void verifyHazardLevels(GameTestHelper helper) {
        check(ROD_HAZARDS.size() == 31 && PELLET_HAZARDS.size() == 31, "the hazard tables have " + ROD_HAZARDS.size() + " rods and " + PELLET_HAZARDS.size() + " pellets, expected 31 each");

        // The handoff's cross-check values for the ueu rod (RADIATION 1.4 at full enrichment), restated as numbers.
        RodHazard ueuRow = ROD_HAZARDS.get(0);
        check(ueuRow.id().equals("rbmk_fuel_ueu") && ueuRow.full() == 1.4F && ueuRow.half() == 900.35F && ueuRow.empty() == 1200F && ueuRow.halfPoisoned() == 1525.35F, "the generated ueu row is " + ueuRow);

        for(RodHazard row : ROD_HAZARDS) {
            RBMKRodItem rod = rod(row.id());
            double[] enrichment = { 1D, 0.5D, 0D, 0.5D };
            double[] poison = { 0D, 0D, 0D, 50D };
            float[] expected = { row.full(), row.half(), row.empty(), row.halfPoisoned() };
            for(int i = 0; i < 4; i++) {
                ItemStack stack = new ItemStack(rod);
                if(i > 0) {
                    RBMKRodItem.setYield(stack, rod.yield * enrichment[i]);
                    RBMKRodItem.setPoison(stack, poison[i]);
                }
                float actual = HazardSystem.getHazardLevelFromStack(stack, HazardRegistry.RADIATION);
                check(Float.compare(actual, expected[i]) == 0, row.id() + " RADIATION at enrichment " + enrichment[i] + " poison " + poison[i] + " is " + actual + ", expected " + expected[i]);
            }

            // HazardModifierRBMKHot (:10-22): level = min(ceil((hull - 100) / 10), 60), negative below 100 (ignored by HazardTypeHot).
            int[] hulls = { 20, 50, 100, 105, 200, 700, 1000 };
            float[] hot = { -8F, -5F, 0F, 1F, 10F, 60F, 60F };
            for(int i = 0; i < hulls.length; i++) {
                ItemStack stack = new ItemStack(rod);
                RBMKRodItem.setHullHeat(stack, hulls[i]);
                float actual = HazardSystem.getHazardLevelFromStack(stack, HazardRegistry.HOT);
                check(Float.compare(actual, hot[i]) == 0 || (hot[i] == 0F && actual == 0F), row.id() + " HOT at hull " + hulls[i] + " is " + actual + ", expected " + hot[i]);
            }

            // Registered entries: exactly RADIATION then HOT (registerRBMK :584-592; no blinding or digamma for the ported rods).
            List<HazardEntry> entries = HazardSystem.getHazardsFromStack(new ItemStack(rod));
            check(entries.size() == 2 && entries.get(0).getType() == HazardRegistry.RADIATION && entries.get(1).getType() == HazardRegistry.HOT, row.id() + " entries are " + describe(entries) + ", expected RADIATION then HOT");
        }

        for(PelletHazard row : PELLET_HAZARDS) {
            Item pellet = item(row.id());
            check(row.levels().length == 10, row.id() + " has " + row.levels().length + " expected levels");
            for(int meta = 0; meta < 10; meta++) {
                ItemStack stack = MetaHelper.newStack(pellet, 1, meta);
                float actual = HazardSystem.getHazardLevelFromStack(stack, HazardRegistry.RADIATION);
                check(Float.compare(actual, row.levels()[meta]) == 0, row.id() + " RADIATION at META " + meta + " is " + actual + ", expected " + row.levels()[meta]);
                check(HazardSystem.getHazardLevelFromStack(stack, HazardRegistry.HOT) == 0F, row.id() + " has a HOT level at META " + meta);
            }
            List<HazardEntry> entries = HazardSystem.getHazardsFromStack(new ItemStack(pellet));
            check(entries.size() == 1 && entries.get(0).getType() == HazardRegistry.RADIATION, row.id() + " entries are " + describe(entries) + ", expected RADIATION only");
        }
        PelletHazard ueuPellet = PELLET_HAZARDS.get(0);
        check(ueuPellet.id().equals("rbmk_pellet_ueu") && ueuPellet.levels()[0] == 0.175F && ueuPellet.levels()[4] == 150F && ueuPellet.levels()[5] == 125.175F && ueuPellet.levels()[9] == 275F, "the generated ueu pellet row is " + java.util.Arrays.toString(ueuPellet.levels()));
        PelletHazard poPellet = PELLET_HAZARDS.stream().filter(r -> r.id().equals("rbmk_pellet_po210be")).findFirst().orElseThrow();
        check(poPellet.id().equals("rbmk_pellet_po210be") && poPellet.levels()[2] == 61.875F, "the generated po210be pellet row is " + java.util.Arrays.toString(poPellet.levels()));
        RodHazard poRod = ROD_HAZARDS.stream().filter(r -> r.id().equals("rbmk_fuel_po210be")).findFirst().orElseThrow();
        check(poRod.id().equals("rbmk_fuel_po210be") && poRod.half() == 495F, "the generated po210be rod row is " + poRod);

        // debris_fuel keeps RADIATION 500 + HOT 5 (original HazardRegistry.java:283).
        ItemStack debris = new ItemStack(NtmItems.DEBRIS_FUEL.get());
        check(HazardSystem.getHazardLevelFromStack(debris, HazardRegistry.RADIATION) == 500F && HazardSystem.getHazardLevelFromStack(debris, HazardRegistry.HOT) == 5F, "debris_fuel RADIATION " + HazardSystem.getHazardLevelFromStack(debris, HazardRegistry.RADIATION) + " HOT " + HazardSystem.getHazardLevelFromStack(debris, HazardRegistry.HOT));
    }

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rbmk_fuel_hazard_hot_ignites(GameTestHelper helper) {
        List<Entity> spawned = new ArrayList<>();
        try {
            guard(() -> {
                check(!NtmConfig.COMMON.DISABLE_HOT.get(), "hot hazards are disabled in the common config");
                Pig pig = helper.spawn(EntityType.PIG, new Vec3(8.5, 1, 8.5));
                pig.setNoAi(true);
                spawned.add(pig);
                check(!pig.isInWaterOrRain(), "the pig stands in water or rain");

                // HOT level -5 at hull 50 does not ignite (HazardTypeHot ignores level <= 0), 10 at hull 200 gives ceil(10) * 20 = 200 fire ticks, 60 at hull 700 gives 1200.
                RBMKRodItem ueu = rod("rbmk_fuel_ueu");
                int[] hulls = { 50, 100, 105, 200, 700 };
                int[] fire = { 0, 0, 20, 200, 1200 };
                for(int i = 0; i < hulls.length; i++) {
                    ItemStack stack = new ItemStack(ueu);
                    RBMKRodItem.setHullHeat(stack, hulls[i]);
                    pig.clearFire();
                    HazardSystem.applyHazards(stack, pig);
                    int ticks = pig.getRemainingFireTicks();
                    LOGGER.info("[hbm-rbmk-fuel] ueu rod at hull {} on a pig: {} fire ticks, expected {}", hulls[i], ticks, fire[i]);
                    if(fire[i] == 0) check(!pig.isOnFire() && ticks <= 0, "hull " + hulls[i] + " ignited the pig: " + ticks + " fire ticks");
                    else check(pig.isOnFire() && ticks == fire[i], "hull " + hulls[i] + " left " + ticks + " fire ticks, expected " + fire[i]);
                    check(stack.getCount() == 1, "the rod stack was consumed");
                }

                // Through a held stack: the real inventory entry.
                ItemStack held = new ItemStack(ueu);
                RBMKRodItem.setHullHeat(held, 200D);
                pig.setItemSlot(EquipmentSlot.MAINHAND, held);
                pig.clearFire();
                HazardSystem.updateLivingInventory(pig);
                check(pig.getRemainingFireTicks() == 200, "a held hull-200 rod left " + pig.getRemainingFireTicks() + " fire ticks, expected 200");
                pig.setItemSlot(EquipmentSlot.MAINHAND, ItemStack.EMPTY);

                // A pellet has no HOT entry and never ignites.
                pig.clearFire();
                HazardSystem.applyHazards(new ItemStack(item("rbmk_pellet_ueu")), pig);
                check(!pig.isOnFire(), "a pellet set the pig on fire");
            }).run();
        } finally {
            for(Entity entity : spawned) if(!entity.isRemoved()) entity.discard();
        }
        done(helper, "rbmk_fuel_hazard_hot_ignites");
    }

    // 9. Pellet subtypes and tooltips

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rbmk_fuel_pellet_subtypes(GameTestHelper helper) {
        guard(() -> verifyPelletSubtypes(helper)).run();
        done(helper, "rbmk_fuel_pellet_subtypes");
    }

    private static void verifyPelletSubtypes(GameTestHelper helper) {
        // ItemRBMKPellet.java:117-123 (rectify, hasXenon).
        check(RBMKPelletItem.rectify(-3) == 3 && RBMKPelletItem.rectify(13) == 3 && RBMKPelletItem.rectify(10) == 0 && RBMKPelletItem.rectify(-10) == 0 && RBMKPelletItem.rectify(9) == 9, "rectify(-3/13/10/-10/9) is "
                + RBMKPelletItem.rectify(-3) + "/" + RBMKPelletItem.rectify(13) + "/" + RBMKPelletItem.rectify(10) + "/" + RBMKPelletItem.rectify(-10) + "/" + RBMKPelletItem.rectify(9));
        check(RBMKPelletItem.hasXenon(5) && !RBMKPelletItem.hasXenon(4) && RBMKPelletItem.hasXenon(9) && !RBMKPelletItem.hasXenon(0) && RBMKPelletItem.hasXenon(-5) && RBMKPelletItem.hasXenon(15) && !RBMKPelletItem.hasXenon(14) && !RBMKPelletItem.hasXenon(10),
                "hasXenon(5/4/9/0/-5/15/14/10) is " + RBMKPelletItem.hasXenon(5) + RBMKPelletItem.hasXenon(4) + RBMKPelletItem.hasXenon(9) + RBMKPelletItem.hasXenon(0) + RBMKPelletItem.hasXenon(-5) + RBMKPelletItem.hasXenon(15) + RBMKPelletItem.hasXenon(14) + RBMKPelletItem.hasXenon(10));

        String[] tierKey = { "brandNew", "barelyDepleted", "moderatelyDepleted", "highlyDepleted", "fullyDepleted" };
        ChatFormatting[] tierColor = { ChatFormatting.GOLD, ChatFormatting.YELLOW, ChatFormatting.GREEN, ChatFormatting.DARK_GREEN, ChatFormatting.DARK_GRAY };
        int xenonCount = 0;
        for(PelletRow row : PELLETS) {
            RBMKPelletItem pellet = (RBMKPelletItem) item(row.id());

            // getSubItems: metas 0-9, or 0-4 without xenon (:41-45).
            List<ItemStack> subs = new ArrayList<>();
            pellet.getSubItems(pellet, subs);
            int expectedCount = row.xenon() ? 10 : 5;
            if(row.xenon()) xenonCount++;
            check(subs.size() == expectedCount, row.id() + " has " + subs.size() + " subtypes, expected " + expectedCount);
            for(int i = 0; i < subs.size(); i++) check(subs.get(i).is(pellet) && subs.get(i).getCount() == 1 && MetaHelper.getMeta(subs.get(i)) == i, row.id() + " subtype " + i + " is " + subs.get(i) + " META " + MetaHelper.getMeta(subs.get(i)));

            // The description id does not change with the META.
            String descriptionId = new ItemStack(pellet).getDescriptionId();
            check(descriptionId.equals("item.hbmsntm." + row.id()), row.id() + " description id is " + descriptionId);

            // addInformation (:79-98): full name, recycling, the tier of META % 5, the xenon line from META 5 on, also for xenon-disabled pellets (static test).
            int[] metas = { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, -7, 13 };
            for(int meta : metas) {
                ItemStack stack = MetaHelper.newStack(pellet, 1, meta);
                check(stack.getDescriptionId().equals(descriptionId), row.id() + " description id changes with META " + meta + ": " + stack.getDescriptionId());
                int rect = Math.abs(meta) % 10;
                List<Component> lines = tooltip(stack);
                boolean xenon = rect >= 5;
                check(lines.size() == (xenon ? 4 : 3), row.id() + " META " + meta + " tooltip has " + lines.size() + " lines: " + lines);
                expectLine(lines.get(0), "item.hbmsntm." + row.id() + ".fullName", null, true);
                TranslatableContents recycling = tr(lines.get(1), "recycling");
                check(recycling.getKey().equals("desc.item.rbmkPellet.recycling") && hasColor(lines.get(1), ChatFormatting.DARK_GRAY) && lines.get(1).getStyle().isItalic(), row.id() + " recycling line is " + lines.get(1));
                expectLine(lines.get(2), "desc.item.rbmkPellet." + tierKey[rect % 5], tierColor[rect % 5], false);
                if(xenon) expectLine(lines.get(3), "desc.item.rbmkPellet.highXenon", ChatFormatting.DARK_PURPLE, false);
            }
        }
        check(xenonCount == 26, xenonCount + " pellets have xenon, expected 26 (five source and balefire pellets do not)");
    }

    // 10. Recipes

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 200)
    public static void rbmk_fuel_recipes_rods(GameTestHelper helper) {
        guard(() -> verifyRecipesRods(helper, ROD_RECIPES)).run();
        done(helper, "rbmk_fuel_recipes_rods");
    }

    private static void verifyRecipesRods(GameTestHelper helper, String[][] table) {
        // RodRecipes.java:89: ZRZ / Z Z / ZRZ with Z = zirconium ingot, R = empty quad rod.
        Item zr = item("ingot_zirconium");
        Item quad = item("rod_quad_empty");
        Item empty = item("rbmk_fuel_empty");
        ShapedRecipe shaped = shaped(helper, "rbmk_fuel_empty");
        check(shaped.getWidth() == 3 && shaped.getHeight() == 3, "rbmk_fuel_empty is " + shaped.getWidth() + "x" + shaped.getHeight() + ", expected 3x3");
        List<ItemStack> grid = new ArrayList<>(List.of(new ItemStack(zr), new ItemStack(quad), new ItemStack(zr), new ItemStack(zr), ItemStack.EMPTY, new ItemStack(zr), new ItemStack(zr), new ItemStack(quad), new ItemStack(zr)));
        ItemStack result = craft(helper, "rbmk_fuel_empty", grid);
        check(result.is(empty) && result.getCount() == 1, "rbmk_fuel_empty crafts " + result);
        // The rods in the corners and the ingots on the sides is a different pattern.
        List<ItemStack> wrong = new ArrayList<>(List.of(new ItemStack(quad), new ItemStack(zr), new ItemStack(quad), new ItemStack(zr), ItemStack.EMPTY, new ItemStack(zr), new ItemStack(quad), new ItemStack(zr), new ItemStack(quad)));
        check(!ids(matching(helper, wrong)).contains(id("rbmk_fuel_empty")), "the swapped pattern crafts rbmk_fuel_empty");

        // RodRecipes.java:90-120: one empty rod and eight billets give the rod, in this line order.
        for(String[] row : table) {
            String rodId = "rbmk_fuel_" + row[0];
            Item billet = item(row[1]);
            Item rod = item(rodId);
            ShapelessRecipe recipe = shapeless(helper, rodId);
            checkIngredients(recipe, rodId, Map.of("rbmk_fuel_empty", 1, row[1], 8));
            ItemStack out = recipe.getResultItem(helper.getLevel().registryAccess());
            check(out.is(rod) && out.getCount() == 1, rodId + " result is " + out);
            List<ItemStack> cells = new ArrayList<>();
            cells.add(new ItemStack(empty));
            for(int i = 0; i < 8; i++) cells.add(new ItemStack(billet));
            ItemStack crafted = craft(helper, rodId, cells);
            check(crafted.is(rod) && crafted.getCount() == 1, rodId + " crafts " + crafted);
            // Seven billets are not enough.
            List<ItemStack> seven = new ArrayList<>(cells.subList(0, 8));
            check(!ids(matching(helper, seven)).contains(id(rodId)), rodId + " crafts with seven billets");
        }
        LOGGER.info("[hbm-rbmk-fuel] checked rbmk_fuel_empty and {} rod recipes", table.length);
    }

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 200)
    public static void rbmk_fuel_recipes_billets_and_tools(GameTestHelper helper) {
        guard(() -> verifyRecipesBilletsAndTools(helper)).run();
        done(helper, "rbmk_fuel_recipes_billets_and_tools");
    }

    private static void verifyRecipesBilletsAndTools(GameTestHelper helper) {
        // MineralRecipes.java:183-191 (beryllium neutron sources, 9 rows) and :193-198 (ZFB billets, 6 rows).
        Object[][] shapeless = {
                { "billet_po210be_from_nuggets", "billet_po210be", 1, new String[] { "nugget_polonium", "3", "nugget_beryllium", "3" } },
                { "billet_pu238be_from_nuggets", "billet_pu238be", 1, new String[] { "nugget_pu238", "3", "nugget_beryllium", "3" } },
                { "billet_ra226be_from_nuggets", "billet_ra226be", 1, new String[] { "nugget_ra226", "3", "nugget_beryllium", "3" } },
                { "billet_po210be_from_billet", "billet_po210be", 2, new String[] { "billet_polonium", "1", "billet_beryllium", "1" } },
                { "billet_pu238be_from_billet", "billet_pu238be", 2, new String[] { "billet_pu238", "1", "billet_beryllium", "1" } },
                { "billet_ra226be_from_billet", "billet_ra226be", 2, new String[] { "billet_ra226", "1", "billet_beryllium", "1" } },
                { "billet_po210be_from_billets", "billet_po210be", 6, new String[] { "billet_polonium", "3", "billet_beryllium", "3" } },
                { "billet_pu238be_from_billets", "billet_pu238be", 6, new String[] { "billet_pu238", "3", "billet_beryllium", "3" } },
                { "billet_ra226be_from_billets", "billet_ra226be", 6, new String[] { "billet_ra226", "3", "billet_beryllium", "3" } },
                { "billet_zfb_bismuth_from_nuggets", "billet_zfb_bismuth", 1, new String[] { "nugget_zirconium", "3", "nugget_uranium", "1", "nugget_pu241", "1", "nugget_bismuth", "1" } },
                { "billet_zfb_pu241_from_nuggets", "billet_zfb_pu241", 1, new String[] { "nugget_zirconium", "3", "nugget_u235", "1", "nugget_pu240", "1", "nugget_pu241", "1" } },
                { "billet_zfb_am_mix_from_nuggets", "billet_zfb_am_mix", 1, new String[] { "nugget_zirconium", "3", "nugget_pu241", "2", "nugget_am_mix", "1" } },
                { "billet_zfb_bismuth_from_billets", "billet_zfb_bismuth", 6, new String[] { "billet_zirconium", "3", "billet_uranium", "1", "billet_pu241", "1", "billet_bismuth", "1" } },
                { "billet_zfb_pu241_from_billets", "billet_zfb_pu241", 6, new String[] { "billet_zirconium", "3", "billet_u235", "1", "billet_pu240", "1", "billet_pu241", "1" } },
                { "billet_zfb_am_mix_from_billets", "billet_zfb_am_mix", 6, new String[] { "billet_zirconium", "3", "billet_pu241", "2", "billet_am_mix", "1" } }
        };
        check(shapeless.length == 15, "the table has " + shapeless.length + " rows, expected 9 + 6");
        for(Object[] row : shapeless) {
            String recipeId = (String) row[0];
            String[] parts = (String[]) row[3];
            Map<String, Integer> expected = new TreeMap<>();
            List<ItemStack> cells = new ArrayList<>();
            for(int i = 0; i < parts.length; i += 2) {
                int count = Integer.parseInt(parts[i + 1]);
                expected.put(parts[i], count);
                for(int j = 0; j < count; j++) cells.add(new ItemStack(item(parts[i])));
            }
            ShapelessRecipe recipe = shapeless(helper, recipeId);
            checkIngredients(recipe, recipeId, expected);
            ItemStack out = recipe.getResultItem(helper.getLevel().registryAccess());
            check(out.is(item((String) row[1])) && out.getCount() == (Integer) row[2], recipeId + " result is " + out + ", expected " + row[2] + " " + row[1]);
            ItemStack crafted = craft(helper, recipeId, cells);
            check(crafted.is(item((String) row[1])) && crafted.getCount() == (Integer) row[2], recipeId + " crafts " + crafted);
        }

        // ToolRecipes.java:139-140: "  I" / " I " / "S  ".
        Item iron = Items.IRON_INGOT;
        ItemStack steel = new ItemStack(item("ingot_steel"));
        ShapedRecipe screwdriver = shaped(helper, "screwdriver");
        check(screwdriver.getWidth() == 3 && screwdriver.getHeight() == 3, "screwdriver is " + screwdriver.getWidth() + "x" + screwdriver.getHeight());
        ItemStack made = craft(helper, "screwdriver", diagonal(new ItemStack(iron), steel));
        check(made.is(item("screwdriver")) && made.getCount() == 1, "screwdriver crafts " + made);
        ItemStack desh = new ItemStack(item("ingot_desh"));
        ShapedRecipe screwdriverDesh = shaped(helper, "screwdriver_desh");
        check(screwdriverDesh.getWidth() == 3 && screwdriverDesh.getHeight() == 3, "screwdriver_desh is " + screwdriverDesh.getWidth() + "x" + screwdriverDesh.getHeight());
        // ANY_PLASTIC.ingot(): the polymer and the bakelite ingot both work (ntm:ingots_plastic), steel does not.
        for(String plastic : List.of("ingot_polymer", "ingot_bakelite")) {
            ItemStack madeDesh = craft(helper, "screwdriver_desh", diagonal(desh.copy(), new ItemStack(item(plastic))));
            check(madeDesh.is(item("screwdriver_desh")) && madeDesh.getCount() == 1, "screwdriver_desh with " + plastic + " crafts " + madeDesh);
        }
        check(!ids(matching(helper, diagonal(desh.copy(), steel.copy()))).contains(id("screwdriver_desh")), "screwdriver_desh crafts with a steel ingot");
        check(!ids(matching(helper, diagonal(new ItemStack(iron), new ItemStack(item("ingot_polymer"))))).contains(id("screwdriver")), "screwdriver crafts with a polymer ingot");
        check(!ids(matching(helper, diagonal(new ItemStack(iron), steel.copy()))).contains(id("screwdriver_desh")), "screwdriver_desh crafts with iron and steel");
    }

    // 11. PUREX

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rbmk_fuel_purex_uzh(GameTestHelper helper) {
        guard(() -> verifyPurexUzh(helper)).run();
        done(helper, "rbmk_fuel_purex_uzh");
    }

    private static void verifyPurexUzh(GameTestHelper helper) {
        PUREXRecipes set = PUREXRecipes.INSTANCE;
        String[] first = { "purex.zirnoxnu", "purex.zirnoxmeu", "purex.zirnoxthmeu", "purex.zirnoxmox", "purex.zirnoxmep", "purex.zirnoxheu233", "purex.zirnoxheu235", "purex.zirnoxles",
                "purex.zirnoxzfbmox", "purex.schraranium", "purex.schrabzirnox" };
        check(set.recipeOrderedList.size() == 12 && set.recipeNameMap.size() == 12, "the PUREX table has " + set.recipeOrderedList.size() + " ordered and " + set.recipeNameMap.size() + " named rows, expected 12");
        for(int i = 0; i < first.length; i++) check(set.recipeOrderedList.get(i).getInternalName().equals(first[i]), "PUREX row " + i + " is " + set.recipeOrderedList.get(i).getInternalName() + ", expected " + first[i]);

        // PUREXRecipes.java:44-48.
        GenericRecipe uzh = set.recipeOrderedList.get(11);
        check(uzh.getInternalName().equals("purex.uzh") && set.recipeNameMap.get("purex.uzh") == uzh, "row 11 is " + uzh.getInternalName() + ", expected purex.uzh");
        check(uzh.duration == 600 && uzh.power == 1_000L, "purex.uzh takes " + uzh.duration + " ticks at " + uzh.power + ", expected 600 at 1000");
        check(uzh.nameWrapper == null && uzh.autoSwitchGroup == null && !uzh.isPooled(), "purex.uzh has a wrapper " + uzh.nameWrapper + ", group " + uzh.autoSwitchGroup + " or pool");
        check(uzh.inputItem != null && uzh.inputItem.length == 2, "purex.uzh has " + (uzh.inputItem == null ? null : uzh.inputItem.length) + " item inputs, expected 2");
        check(uzh.inputItem[0].stacksize == 1 && uzh.inputItem[0].matchesRecipe(new ItemStack(item("billet_uranium_fuel")), false) && !uzh.inputItem[0].matchesRecipe(new ItemStack(item("billet_uranium")), false), "purex.uzh input 0 is not one billet_uranium_fuel");
        check(uzh.inputItem[1].stacksize == 3 && uzh.inputItem[1].matchesRecipe(new ItemStack(item("billet_zirconium"), 3), false) && !uzh.inputItem[1].matchesRecipe(new ItemStack(item("billet_zirconium"), 2), false)
                && !uzh.inputItem[1].matchesRecipe(new ItemStack(item("billet_uranium")), false), "purex.uzh input 1 is not three billet_zirconium");
        check(uzh.inputFluid != null && uzh.inputFluid.length == 2
                        && uzh.inputFluid[0].type == Fluids.NITRIC_ACID && uzh.inputFluid[0].fill == 1_000 && uzh.inputFluid[0].pressure == 0
                        && uzh.inputFluid[1].type == Fluids.HYDROGEN && uzh.inputFluid[1].fill == 4_000 && uzh.inputFluid[1].pressure == 0,
                "purex.uzh fluid inputs are wrong");
        check(uzh.outputFluid == null || uzh.outputFluid.length == 0, "purex.uzh has fluid outputs");
        check(uzh.outputItem != null && uzh.outputItem.length == 1 && !uzh.outputItem[0].possibleMultiOutput(), "purex.uzh output layout");
        ItemStack single = uzh.outputItem[0].getSingle();
        check(single.is(item("billet_uzh")) && single.getCount() == 4 && MetaHelper.getMeta(single) == 0, "purex.uzh output is " + single + ", expected 4 billet_uzh");

        // The display name falls back to the first output when there is no wrapper (the original behaves the same).
        check(uzh.getIcon().is(item("billet_uzh")), "purex.uzh icon is " + uzh.getIcon());
        check(!uzh.getName().getString().isEmpty() && !uzh.getName().getString().equals("purex.uzh"), "purex.uzh name is " + uzh.getName());
    }

    // 12. English full names against the original text

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rbmk_fuel_language_full_names(GameTestHelper helper) {
        guard(() -> verifyLanguageFullNames(helper)).run();
        done(helper, "rbmk_fuel_language_full_names");
    }

    private static void verifyLanguageFullNames(GameTestHelper helper) {
        JsonObject en = lang("en_us");
        JsonObject zh = lang("zh_cn");
        for(PelletRow row : PELLETS) {
            String key = "item.hbmsntm." + row.id() + ".fullName";
            check(en.has(key) && en.get(key).getAsString().equals(row.fullName()), key + " is " + (en.has(key) ? en.get(key).getAsString() : null) + " in en_us, expected the original text " + row.fullName());
            check(zh.has(key) && !zh.get(key).getAsString().isEmpty(), key + " is missing in zh_cn");
            check(en.has("item.hbmsntm." + row.id()) && zh.has("item.hbmsntm." + row.id()), "the pellet name of " + row.id() + " is missing");
        }
        for(Rod row : RODS) check(en.has("item.hbmsntm." + row.id()) && zh.has("item.hbmsntm." + row.id()), "the rod name of " + row.id() + " is missing");
        check(en.has("item.hbmsntm.rbmk_fuel_empty") && zh.has("item.hbmsntm.rbmk_fuel_empty"), "the empty rod name is missing");
    }

    // 13. Mutation checks: each mutation is applied in memory to a live item, a registry entry or a table copy, restored in finally, and must
    // make a named check of this class fail. An undetected mutation fails this test and is listed in the message.

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 200)
    public static void rbmk_fuel_mutations(GameTestHelper helper) {
        List<String> undetected = new ArrayList<>();
        Map<String, Runnable> checks = new java.util.LinkedHashMap<>();
        checks.put("registration_table", () -> verifyRegistrationTable(helper));
        checks.put("defaults_and_schema", () -> verifyDefaultsAndSchema(helper));
        checks.put("tooltips", () -> verifyTooltips(helper));
        checks.put("curves", () -> verifyCurves(helper));
        checks.put("burn", () -> verifyBurn(helper));
        checks.put("heat", () -> verifyHeat(helper));
        checks.put("hazard_levels", () -> verifyHazardLevels(helper));
        checks.put("purex_uzh", () -> verifyPurexUzh(helper));

        // The unmutated state passes every check (otherwise the mutations below prove nothing).
        for(Map.Entry<String, Runnable> entry : checks.entrySet()) {
            try {
                guard(entry.getValue()).run();
            } catch(RuntimeException e) {
                throw new net.minecraft.gametest.framework.GameTestAssertException("the unmutated " + entry.getKey() + " check fails before any mutation: " + e.getMessage());
            }
        }

        RBMKRodItem ueu = rod("rbmk_fuel_ueu");
        RBMKRodItem lea = rod("rbmk_fuel_lea");
        RBMKRodItem uzh = rod("rbmk_fuel_uzh");
        RBMKRodItem ra = rod("rbmk_fuel_ra226be");
        Item ueuItem = ueu;
        Item pelletItem = item("rbmk_pellet_ueu");

        double heat = ueu.heat;
        mutate(undetected, checks, "ueu.heat 0.65 -> 0.7", () -> ueu.heat = 0.7D, () -> ueu.heat = heat);
        EnumBurnFunc function = ueu.function;
        mutate(undetected, checks, "ueu.function LOG_TEN -> LINEAR", () -> ueu.function = EnumBurnFunc.LINEAR, () -> ueu.function = function);
        EnumDepleteFunc leaDep = lea.depFunc;
        mutate(undetected, checks, "lea.depFunc RAISING_SLOPE -> GENTLE_SLOPE", () -> lea.depFunc = EnumDepleteFunc.GENTLE_SLOPE, () -> lea.depFunc = leaDep);
        double xGen = ueu.xGen;
        mutate(undetected, checks, "ueu.xGen 0.5 -> 0.6", () -> ueu.xGen = 0.6D, () -> ueu.xGen = xGen);
        double xBurn = ueu.xBurn;
        mutate(undetected, checks, "ueu.xBurn 50 -> 60", () -> ueu.xBurn = 60D, () -> ueu.xBurn = xBurn);
        double diffusion = ueu.diffusion;
        mutate(undetected, checks, "ueu.diffusion 0.02 -> 0.03", () -> ueu.diffusion = 0.03D, () -> ueu.diffusion = diffusion);
        double melting = ueu.meltingPoint;
        mutate(undetected, checks, "ueu.meltingPoint 2865 -> 2800", () -> ueu.meltingPoint = 2800D, () -> ueu.meltingPoint = melting);
        double hcStart = uzh.heatCoeffStart;
        mutate(undetected, checks, "uzh.heatCoeffStart 1000 -> 1100", () -> uzh.heatCoeffStart = 1100D, () -> uzh.heatCoeffStart = hcStart);
        double hcLen = uzh.heatCoeffLength;
        mutate(undetected, checks, "uzh.heatCoeffLength 500 -> 400", () -> uzh.heatCoeffLength = 400D, () -> uzh.heatCoeffLength = hcLen);
        double selfRate = ra.selfRate;
        mutate(undetected, checks, "ra226be.selfRate 20 -> 21", () -> ra.selfRate = 21D, () -> ra.selfRate = selfRate);
        double reactivity = ueu.reactivity;
        mutate(undetected, checks, "ueu.reactivity 15 -> 16", () -> ueu.reactivity = 16D, () -> ueu.reactivity = reactivity);
        NType nType = ueu.nType;
        mutate(undetected, checks, "ueu.nType SLOW -> FAST", () -> ueu.nType = NType.FAST, () -> ueu.nType = nType);
        NType rType = ueu.rType;
        mutate(undetected, checks, "ueu.rType FAST -> SLOW", () -> ueu.rType = NType.SLOW, () -> ueu.rType = rType);
        int tint = ueu.colorTint;
        mutate(undetected, checks, "ueu.colorTint ^ 1", () -> ueu.colorTint = tint ^ 1, () -> ueu.colorTint = tint, true);
        double rodYield = ueu.yield;
        mutate(undetected, checks, "ueu.yield 1e8 -> 2e8", () -> ueu.yield = 2e8D, () -> ueu.yield = rodYield);
        RBMKRodItem firstCraftable = RBMKRodItem.CRAFTABLE_RODS.get(0);
        mutate(undetected, checks, "CRAFTABLE_RODS loses its first rod", () -> RBMKRodItem.CRAFTABLE_RODS.remove(0), () -> RBMKRodItem.CRAFTABLE_RODS.add(0, firstCraftable), true);

        // Hazard registry mutations: the rod's data replaced by a wrong variant, the original put back.
        com.hbm.hazard.HazardData rodData = HazardSystem.itemMap.get(ueuItem);
        mutate(undetected, checks, "ueu rod RADIATION modifier linear flag flipped",
                () -> HazardSystem.itemMap.put(ueuItem, new com.hbm.hazard.HazardData()
                        .addEntry(new HazardEntry(HazardRegistry.RADIATION, HazardRegistry.u * HazardRegistry.rod_rbmk).addMod(new com.hbm.hazard.modifier.HazardModifierRBMKRadiation(HazardRegistry.wst * HazardRegistry.rod_rbmk * 20F, true)))
                        .addEntry(new HazardEntry(HazardRegistry.HOT, 0F).addMod(new com.hbm.hazard.modifier.HazardModifierRBMKHot()))),
                () -> HazardSystem.itemMap.put(ueuItem, rodData));
        mutate(undetected, checks, "ueu rod loses its HOT entry",
                () -> HazardSystem.itemMap.put(ueuItem, new com.hbm.hazard.HazardData()
                        .addEntry(new HazardEntry(HazardRegistry.RADIATION, HazardRegistry.u * HazardRegistry.rod_rbmk).addMod(new com.hbm.hazard.modifier.HazardModifierRBMKRadiation(HazardRegistry.wst * HazardRegistry.rod_rbmk * 20F, false)))),
                () -> HazardSystem.itemMap.put(ueuItem, rodData));
        com.hbm.hazard.HazardData pelletData = HazardSystem.itemMap.get(pelletItem);
        mutate(undetected, checks, "ueu pellet dep 150 -> 160",
                () -> HazardSystem.itemMap.put(pelletItem, new com.hbm.hazard.HazardData()
                        .addEntry(new HazardEntry(HazardRegistry.RADIATION, HazardRegistry.u * HazardRegistry.billet).addMod(new com.hbm.hazard.modifier.HazardModifierRBMKRadiation(160F, false)))),
                () -> HazardSystem.itemMap.put(pelletItem, pelletData));

        // PUREX row mutations.
        GenericRecipe row = PUREXRecipes.INSTANCE.recipeNameMap.get("purex.uzh");
        int duration = row.duration;
        mutate(undetected, checks, "purex.uzh duration 600 -> 601", () -> row.duration = 601, () -> row.duration = duration);
        long power = row.power;
        mutate(undetected, checks, "purex.uzh power 1000 -> 999", () -> row.power = 999L, () -> row.power = power);
        int hydrogen = row.inputFluid[1].fill;
        mutate(undetected, checks, "purex.uzh hydrogen 4000 -> 3999", () -> row.inputFluid[1].fill = 3999, () -> row.inputFluid[1].fill = hydrogen);
        int zirconium = row.inputItem[1].stacksize;
        mutate(undetected, checks, "purex.uzh zirconium billets 3 -> 2", () -> row.inputItem[1].stacksize = 2, () -> row.inputItem[1].stacksize = zirconium);

        // Table-copy mutations of the recipe check: a wrong billet, and a wrong rod, must fail verifyRecipesRods.
        String[][] wrongBillet = new String[ROD_RECIPES.length][];
        String[][] wrongRod = new String[ROD_RECIPES.length][];
        for(int i = 0; i < ROD_RECIPES.length; i++) {
            wrongBillet[i] = ROD_RECIPES[i].clone();
            wrongRod[i] = ROD_RECIPES[i].clone();
        }
        wrongBillet[0][1] = "billet_u233";
        wrongRod[30][0] = "zfb_pu241";
        for(Map.Entry<String, String[][]> entry : Map.of("table copy: ueu filled with billet_u233", wrongBillet, "table copy: zfb_am_mix expected as zfb_pu241", wrongRod).entrySet()) {
            try {
                guard(() -> verifyRecipesRods(helper, entry.getValue())).run();
                undetected.add(entry.getKey());
            } catch(RuntimeException e) {
                LOGGER.info("[hbm-rbmk-fuel] mutation \"{}\" detected by recipes_rods: {}", entry.getKey(), e.getMessage());
            }
        }

        // The mutated state was restored: the unmutated checks pass again.
        for(Map.Entry<String, Runnable> entry : checks.entrySet()) {
            try {
                guard(entry.getValue()).run();
            } catch(RuntimeException e) {
                throw new net.minecraft.gametest.framework.GameTestAssertException("the " + entry.getKey() + " check fails after the mutations were restored: " + e.getMessage());
            }
        }
        check(undetected.isEmpty(), "undetected mutations: " + undetected);
        done(helper, "rbmk_fuel_mutations");
    }

    /** The mutation must be caught by a behaviour check: the registration table, which reads the fields directly, is left out. */
    private static void mutate(List<String> undetected, Map<String, Runnable> checks, String name, Runnable apply, Runnable restore) {
        mutate(undetected, checks, name, apply, restore, false);
    }

    private static void mutate(List<String> undetected, Map<String, Runnable> checks, String name, Runnable apply, Runnable restore, boolean includeRegistration) {
        apply.run();
        try {
            for(Map.Entry<String, Runnable> entry : checks.entrySet()) {
                if(!includeRegistration && entry.getKey().equals("registration_table")) continue;
                try {
                    guard(entry.getValue()).run();
                } catch(RuntimeException e) {
                    LOGGER.info("[hbm-rbmk-fuel] mutation \"{}\" detected by {}: {}", name, entry.getKey(), e.getMessage());
                    return;
                }
            }
            undetected.add(name);
        } finally {
            restore.run();
        }
    }

    // Helpers

    private static ResourceLocation id(String path) {
        return ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path);
    }

    private static Item item(String path) {
        Item item = BuiltInRegistries.ITEM.get(id(path));
        check(item != Items.AIR && BuiltInRegistries.ITEM.getKey(item).equals(id(path)), "item " + id(path) + " is not registered");
        return item;
    }

    private static RBMKRodItem rod(String path) {
        Item item = item(path);
        check(item instanceof RBMKRodItem, path + " is a " + item.getClass().getSimpleName() + ", expected a RBMKRodItem");
        return (RBMKRodItem) item;
    }

    /** The server config the expectations assume: dialReactivityMod 1.0, dialDiffusionMod 1.0, dialHeatProvision 0.2, xenon and depletion on (original RBMKDials.java:22-41). */
    private static void requireDefaultDials() {
        check(RBMKDials.getXenon() && RBMKDials.getDepletion(), "dialDisableXenon / dialDisableDepletion are set on the running server; the burn expectations assume both branches run");
        check(RBMKDials.getReactivityMod() == 1.0D && RBMKDials.getFuelDiffusionMod() == 1.0D && RBMKDials.getFuelHeatProvision() == 0.2D,
                "the dials are reactivity " + RBMKDials.getReactivityMod() + ", diffusion " + RBMKDials.getFuelDiffusionMod() + ", heat provision " + RBMKDials.getFuelHeatProvision() + ", expected 1.0, 1.0 and 0.2");
    }

    /** Relative tolerance 1e-9, absolute 1e-12 near zero. */
    private static void near(double actual, double expected, String label) {
        check(Math.abs(actual - expected) <= Math.max(1e-12, 1e-9 * Math.abs(expected)), label + " is " + actual + ", expected " + expected);
    }

    /** For values that are sums of exactly representable numbers (the yield). */
    private static void nearAbs(double actual, double expected, String label) {
        check(Math.abs(actual - expected) <= 1e-9, label + " is " + actual + ", expected " + expected);
    }

    private static boolean hasColor(Component component, ChatFormatting color) {
        return java.util.Objects.equals(component.getStyle().getColor(), color == null ? null : TextColor.fromLegacyFormat(color));
    }

    private static List<Component> tooltip(ItemStack stack) {
        List<Component> lines = new ArrayList<>();
        stack.getItem().appendHoverText(stack, Item.TooltipContext.EMPTY, lines, TooltipFlag.NORMAL);
        return lines;
    }

    private static TranslatableContents tr(Component component, String label) {
        check(component.getContents() instanceof TranslatableContents, label + " is not a translatable component: " + component);
        return (TranslatableContents) component.getContents();
    }

    /** A translatable expectation for an argument: key and string arguments. */
    private record Expected(String key, Object... args) { }

    private static Expected comp(String key, Object... args) {
        return new Expected(key, args);
    }

    private record Literal(String text) { }

    private static Literal literal(String text) {
        return new Literal(text);
    }

    /** Key, colour (null = none), italic, and the arguments: a String, an {@link Expected} translatable or a {@link Literal}. */
    private static void expectLine(Component line, String key, ChatFormatting color, boolean italic, Object... args) {
        TranslatableContents contents = tr(line, key);
        check(contents.getKey().equals(key), "the line is " + contents.getKey() + ", expected " + key);
        check(hasColor(line, color), key + " has the colour " + line.getStyle().getColor() + ", expected " + color);
        check(line.getStyle().isItalic() == italic, key + " italic is " + line.getStyle().isItalic() + ", expected " + italic);
        check(contents.getArgs().length == args.length, key + " has " + contents.getArgs().length + " arguments " + java.util.Arrays.toString(contents.getArgs()) + ", expected " + args.length);
        for(int i = 0; i < args.length; i++) {
            Object actual = contents.getArgs()[i];
            if(args[i] instanceof String s) {
                check(s.equals(actual), key + " argument " + i + " is " + actual + ", expected " + s);
            } else if(args[i] instanceof Expected e) {
                check(actual instanceof Component, key + " argument " + i + " is " + actual + ", expected a component");
                TranslatableContents inner = tr((Component) actual, key + " argument " + i);
                check(inner.getKey().equals(e.key()) && java.util.Arrays.equals(inner.getArgs(), e.args()), key + " argument " + i + " is " + inner.getKey() + " " + java.util.Arrays.toString(inner.getArgs()) + ", expected " + e.key() + " " + java.util.Arrays.toString(e.args()));
            } else if(args[i] instanceof Literal l) {
                check(actual instanceof Component c && !(c.getContents() instanceof TranslatableContents) && c.getString().equals(l.text()) && hasColor(c, ChatFormatting.WHITE),
                        key + " argument " + i + " is " + actual + ", expected the white literal " + l.text());
            }
        }
    }

    private static String describe(List<HazardEntry> entries) {
        List<HazardTypeBase> types = new ArrayList<>();
        for(HazardEntry entry : entries) types.add(entry.getType());
        return types.toString();
    }

    /** The recipe with this id, which must be a shapeless crafting recipe. */
    private static ShapelessRecipe shapeless(GameTestHelper helper, String path) {
        Optional<RecipeHolder<?>> holder = helper.getLevel().getRecipeManager().byKey(id(path));
        check(holder.isPresent(), "recipe " + id(path) + " is not loaded");
        check(holder.get().value() instanceof ShapelessRecipe, "recipe " + id(path) + " is a " + holder.get().value().getClass().getSimpleName() + ", expected a shapeless recipe");
        return (ShapelessRecipe) holder.get().value();
    }

    private static ShapedRecipe shaped(GameTestHelper helper, String path) {
        Optional<RecipeHolder<?>> holder = helper.getLevel().getRecipeManager().byKey(id(path));
        check(holder.isPresent(), "recipe " + id(path) + " is not loaded");
        check(holder.get().value() instanceof ShapedRecipe, "recipe " + id(path) + " is a " + holder.get().value().getClass().getSimpleName() + ", expected a shaped recipe");
        return (ShapedRecipe) holder.get().value();
    }

    /** Every ingredient accepts exactly one item; the multiset of those items is {@code expected} (path -> count). */
    private static void checkIngredients(ShapelessRecipe recipe, String recipeId, Map<String, Integer> expected) {
        Map<String, Integer> actual = new TreeMap<>();
        for(Ingredient ingredient : recipe.getIngredients()) {
            ItemStack[] items = ingredient.getItems();
            check(items.length == 1, recipeId + " has an ingredient that accepts " + items.length + " items");
            actual.merge(BuiltInRegistries.ITEM.getKey(items[0].getItem()).getPath(), 1, Integer::sum);
        }
        check(actual.equals(new TreeMap<>(expected)), recipeId + " ingredients are " + actual + ", expected " + new TreeMap<>(expected));
    }

    /** "  I" / " I " / "S  " with {@code i} on the diagonal and {@code s} at the bottom left. */
    private static List<ItemStack> diagonal(ItemStack i, ItemStack s) {
        return new ArrayList<>(List.of(ItemStack.EMPTY, ItemStack.EMPTY, i.copy(), ItemStack.EMPTY, i.copy(), ItemStack.EMPTY, s.copy(), ItemStack.EMPTY, ItemStack.EMPTY));
    }

    /** The grid a crafting table passes to the recipe manager: cells laid out from the top left of a 3x3 grid, trimmed to their bounding box. */
    private static CraftingInput input(List<ItemStack> items) {
        List<ItemStack> cells = new ArrayList<>(items);
        check(cells.size() <= 9, "the grid has " + cells.size() + " items");
        while(cells.size() < 9) cells.add(ItemStack.EMPTY);
        return CraftingInput.ofPositioned(3, 3, cells).input();
    }

    private static List<RecipeHolder<CraftingRecipe>> matching(GameTestHelper helper, List<ItemStack> items) {
        return helper.getLevel().getRecipeManager().getRecipesFor(RecipeType.CRAFTING, input(items), helper.getLevel());
    }

    private static List<ResourceLocation> ids(List<RecipeHolder<CraftingRecipe>> holders) {
        List<ResourceLocation> ids = new ArrayList<>();
        for(RecipeHolder<CraftingRecipe> holder : holders) ids.add(holder.id());
        return ids;
    }

    /** Crafts the grid, requires exactly the recipe {@code path} to match it (no other recipe shadows it) and returns the result. */
    private static ItemStack craft(GameTestHelper helper, String path, List<ItemStack> items) {
        CraftingInput input = input(items);
        List<RecipeHolder<CraftingRecipe>> all = helper.getLevel().getRecipeManager().getRecipesFor(RecipeType.CRAFTING, input, helper.getLevel());
        check(all.size() == 1 && all.get(0).id().equals(id(path)), "the grid " + items + " matches " + ids(all) + ", expected only " + id(path));
        Optional<RecipeHolder<CraftingRecipe>> first = helper.getLevel().getRecipeManager().getRecipeFor(RecipeType.CRAFTING, input, helper.getLevel());
        check(first.isPresent() && first.get().id().equals(id(path)), "getRecipeFor returns " + first.map(RecipeHolder::id).orElse(null) + " for " + items + ", expected " + id(path));
        return first.get().value().assemble(input, helper.getLevel().registryAccess());
    }

    private static JsonObject lang(String name) {
        try(InputStream in = RBMKFuelGameTests.class.getResourceAsStream("/assets/hbmsntm/lang/" + name + ".json")) {
            check(in != null, "the language file " + name + ".json is not on the classpath of the running server");
            return JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject();
        } catch(java.io.IOException e) {
            throw new RuntimeException(e);
        }
    }

    /** The GameTest framework logs only failures; this line lets the verifier see that every test of this class ran to its success call. */
    private static void done(GameTestHelper helper, String name) {
        LOGGER.info("[hbm-rbmk-fuel] {} passed", name);
        helper.succeed();
    }
}
