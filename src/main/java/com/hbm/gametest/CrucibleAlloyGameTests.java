package com.hbm.gametest;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.hbm.blockentity.machine.MachineCrucibleBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.machine.NTMAnvilBlock;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.material.MaterialEntries;
import com.hbm.inventory.material.MaterialShapes;
import com.hbm.inventory.material.Mats;
import com.hbm.inventory.material.NTMMaterial;
import com.hbm.inventory.menus.AnvilMenu;
import com.hbm.inventory.recipes.CopperCastingRecipes;
import com.hbm.inventory.recipes.CrucibleRecipe;
import com.hbm.inventory.recipes.CrucibleRecipes;
import com.hbm.inventory.recipes.anvil.AnvilRecipes;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.AnvilConstructionRecipe;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.AnvilOutput;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.OverlayType;
import com.hbm.inventory.recipes.anvil.AnvilSmithingBladeMoldRecipe;
import com.hbm.inventory.recipes.anvil.AnvilSmithingCastMoldRecipe;
import com.hbm.inventory.recipes.anvil.AnvilSmithingCyanideRecipe;
import com.hbm.inventory.recipes.anvil.AnvilSmithingIngotMoldRecipe;
import com.hbm.inventory.recipes.anvil.AnvilSmithingRecipe;
import com.hbm.inventory.recipes.anvil.AnvilSmithingRenameRecipe;
import com.hbm.items.CopperScrapsItem;
import com.hbm.items.NtmItems;
import com.hbm.main.NuclearTechMod;
import com.mojang.logging.LogUtils;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.Holder;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.gametest.framework.GameTestSequence;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.tags.TagKey;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.BlockItem;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.crafting.CraftingInput;
import net.minecraft.world.item.crafting.Ingredient;
import net.minecraft.world.item.crafting.Recipe;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.ShapedRecipe;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.ItemLike;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import org.slf4j.Logger;

import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal27B: the 13 crucible alloy recipes (CrucibleRecipes), their processing in a real placed crucible
 * (MachineCrucibleBlockEntity.tryRecipe), the Goal27A acceptance rule with an alloy recipe selected, the ferrouranium anvil (smithing
 * upgrade, tier 4 and the server-side tier of the anvil menu), the twelve tier-4 RBMK recycling rows (AnvilRecipes.registerRBMKRecycling),
 * the lead anvil crafting recipe with the anvil regressions, and the hbmCrucible.json contract. Same template and conventions as
 * {@link MaterialSystemGameTests}; every test has its own batch.
 * <p>
 * Expected values come from the ORIGINAL, cited beside each group of checks (CrucibleRecipes.java:58-127; TileEntityCrucible.java:64-65,
 * 408-430,455-503; MatDistribution.java:85; AnvilRecipes.java:60-72,868-951,1046-1064; NTMAnvil.java:42-49; CraftingManager.java:294-296;
 * SerializableRecipe.java:142-156), not from the NEO implementation. NEO-only expectations are marked as such.
 * <p>
 * Real classes and state: the recipe lists the server loaded, the registered items and recipes, a real crucible placed the way a player
 * places it (SmokeTestSupport.place) and ticked by its own block entity ticker (MachineCrucibleBlock.getTicker -> updateEntity) across real
 * server ticks. Stand-ins: the crucible's recipe stack is filled through its public field (no heater: heat 0, so nothing melts during the
 * timing windows); melting steps set heat / progress through public fields and call updateEntity() once (as MaterialSystemGameTests does);
 * the flux of the hematite step is added directly; the anvil menu is constructed with the arguments NTMAnvilBlock.useWithoutItem passes
 * (no ServerPlayer.openMenu, which needs a network connection); anvil construction runs AnvilRecipes.executeConstruction on a mock player
 * (what AnvilConstructionPacket.handleServer calls with the menu's tier). The config-file test clears and re-registers the crucible
 * recipe list and restores the defaults in finally.
 * Not evidence: a real client (GUI, JEI, recipe book, the anvil screen and its packets), a dedicated server with real players, saved worlds
 * and 1.7.10 itself.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class CrucibleAlloyGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-alloy]";
    // TileEntityCrucible.java:64-65 recipeZCapacity = wasteZCapacity = MaterialShapes.BLOCK.q(16)
    private static final int CAPACITY = 648 * 16;
    private static final BlockPos CORE = new BlockPos(4, 1, 4);
    // NTMAnvil.java:42-49 TIER_OIL 3 (desh), TIER_NUCLEAR 4 (ferrouranium)
    private static final int TIER_OIL = 3, TIER_NUCLEAR = 4;

    private record Alloy(String name, int frequency, String icon, Object[] input, Object[] output) { }

    /** Original CrucibleRecipes.java:60-61 n = NUGGET.q(1) = 8, i = INGOT.q(1) = 72; :63-125 the 13 recipes in order (the GT6 block :67-76 excluded). */
    private static List<Alloy> original() {
        int n = 8, i = 72;
        return List.of(
                new Alloy("crucible.steel", 20, "ingot_steel", mats(Mats.MAT_IRON, n * 2, Mats.MAT_CARBON, n * 3, Mats.MAT_FLUX, n), mats(Mats.MAT_STEEL, n * 2)), // :63-65
                new Alloy("crucible.hematite", 6, "resource_hematite", mats(Mats.MAT_HEMATITE, i * 2, Mats.MAT_FLUX, n * 2), mats(Mats.MAT_IRON, i, Mats.MAT_SLAG, n * 3)), // :79-81
                new Alloy("crucible.malachite", 6, "resource_malachite", mats(Mats.MAT_MALACHITE, i * 2, Mats.MAT_FLUX, n * 2), mats(Mats.MAT_COPPER, i, Mats.MAT_SLAG, n * 3)), // :83-85
                new Alloy("crucible.redcopper", 2, "ingot_red_copper", mats(Mats.MAT_COPPER, n, Mats.MAT_REDSTONE, n), mats(Mats.MAT_MINGRADE, n * 2)), // :87-89
                new Alloy("crucible.hss", 9, "ingot_dura_steel", mats(Mats.MAT_STEEL, n * 5, Mats.MAT_TUNGSTEN, n * 3, Mats.MAT_COBALT, n), mats(Mats.MAT_DURA, n * 9)), // :91-93
                new Alloy("crucible.ferro", 3, "ingot_ferrouranium", mats(Mats.MAT_STEEL, n * 2, Mats.MAT_U238, n), mats(Mats.MAT_FERRO, n * 3)), // :95-97
                new Alloy("crucible.tcalloy", 9, "ingot_tcalloy", mats(Mats.MAT_STEEL, n * 8, Mats.MAT_TECHNETIUM, n), mats(Mats.MAT_TCALLOY, i)), // :99-101
                new Alloy("crucible.cdalloy", 9, "ingot_cdalloy", mats(Mats.MAT_STEEL, n * 8, Mats.MAT_CADMIUM, n), mats(Mats.MAT_CDALLOY, i)), // :103-105
                new Alloy("crucible.bbronze", 9, "ingot_bismuth_bronze", mats(Mats.MAT_COPPER, n * 8, Mats.MAT_BISMUTH, n, Mats.MAT_FLUX, n * 3), mats(Mats.MAT_BBRONZE, i, Mats.MAT_SLAG, n * 3)), // :107-109
                new Alloy("crucible.abronze", 9, "ingot_arsenic_bronze", mats(Mats.MAT_COPPER, n * 8, Mats.MAT_ARSENIC, n, Mats.MAT_FLUX, n * 3), mats(Mats.MAT_ABRONZE, i, Mats.MAT_SLAG, n * 3)), // :111-113
                new Alloy("crucible.cmb", 3, "ingot_combine_steel", mats(Mats.MAT_MAGTUNG, n * 6, Mats.MAT_MUD, n * 3), mats(Mats.MAT_CMB, i)), // :115-117
                new Alloy("crucible.magtung", 3, "ingot_magnetized_tungsten", mats(Mats.MAT_TUNGSTEN, i, Mats.MAT_SCHRABIDIUM, n), mats(Mats.MAT_MAGTUNG, i)), // :119-121
                new Alloy("crucible.bscco", 3, "ingot_bscco", mats(Mats.MAT_BISMUTH, n * 2, Mats.MAT_STRONTIUM, n * 2, Mats.MAT_CALCIUM, n * 2, Mats.MAT_COPPER, n * 3), mats(Mats.MAT_BSCCO, i))); // :123-125
    }

    private static Alloy alloy(String name) {
        for(Alloy a : original()) if(a.name().equals(name)) return a;
        throw new IllegalStateException(name);
    }

    // 1. the alloy table (CrucibleRecipes.java:58-127; no setNamed in the file, Goal 10A: no crucible.* language keys)
    @GameTest(template = TEMPLATE, batch = "alloy_table", timeoutTicks = 100)
    public static void alloy_table(GameTestHelper helper) {
        guard(() -> {
            List<Alloy> want = original();
            List<CrucibleRecipe> list = CrucibleRecipes.INSTANCE.recipeOrderedList;
            List<String> names = new ArrayList<>();
            for(CrucibleRecipe r : list) names.add(r.getInternalName());
            check(list.size() == want.size() && want.size() == 13, "the crucible has " + list.size() + " recipes " + names + ", expected the 13 of CrucibleRecipes.java:63-125");
            for(int k = 0; k < want.size(); k++) {
                Alloy a = want.get(k);
                CrucibleRecipe r = list.get(k);
                check(a.name().equals(r.getInternalName()), "recipe #" + k + " is " + r.getInternalName() + ", expected " + a.name() + " (original order)");
                check(r.frequency == a.frequency(), a.name() + " frequency " + r.frequency + ", expected " + a.frequency());
                ItemStack icon = r.getIcon();
                check(BuiltInRegistries.ITEM.getKey(icon.getItem()).equals(id(a.icon())) && icon.getCount() == 1 && MetaHelper.getMeta(icon) == 0,
                        a.name() + " icon " + icon + ", expected hbmsntm:" + a.icon());
                pairs(List.of(r.input), a.input(), a.name() + " inputs");
                pairs(List.of(r.output), a.output(), a.name() + " outputs");
                check(CrucibleRecipes.INSTANCE.recipeNameMap.get(a.name()) == r, "recipeNameMap " + a.name() + " is not the listed recipe");
            }
            check(CrucibleRecipes.INSTANCE.recipeNameMap.size() == 13, "recipeNameMap has " + CrucibleRecipes.INSTANCE.recipeNameMap.size() + " names, expected 13");
            // crucible.hss as Goal 10A: steel 40, tungsten 24, cobalt 8 -> dura 72 every 9 ticks (:91-93)
            CrucibleRecipe hss = CrucibleRecipes.INSTANCE.recipeNameMap.get("crucible.hss");
            check(hss != null && hss.frequency == 9, "crucible.hss frequency changed");
            pairs(List.of(hss.input), mats(Mats.MAT_STEEL, 40, Mats.MAT_TUNGSTEN, 24, Mats.MAT_COBALT, 8), "crucible.hss inputs (Goal 10A)");
            pairs(List.of(hss.output), mats(Mats.MAT_DURA, 72), "crucible.hss outputs (Goal 10A)");
            // the GUI shows the icon's name (no setNamed upstream): the packaged English file has no crucible.* key
            JsonObject en = lang("en_us");
            List<String> keys = new ArrayList<>();
            for(String key : en.keySet()) if(key.startsWith("crucible.")) keys.add(key);
            check(keys.isEmpty(), "en_us.json has crucible.* keys " + keys + ", expected none (Goal 10A)");
            LOGGER.info("{} alloy_table: {} recipes in order {}", TAG, list.size(), names);
        }).run();
        done(helper, "alloy_table");
    }

    // 2. processing (TileEntityCrucible.java:408-430 tryRecipe: only when getTotalWorldTime() % frequency == 0 and every input is present;
    // subtracts the inputs, adds the outputs). Each run fills the recipe stack, then the crucible's own ticker runs across real ticks; every
    // tick the recipe stack is compared with this model of the original, which executes at exactly the multiples of the frequency.
    private static final class Run {
        final String label;
        final Alloy alloy;
        final Object[] start;
        final int window;
        final int executions;
        final Object[] end;
        final boolean meltHematite;
        final Map<NTMMaterial, Integer> model = new LinkedHashMap<>();
        final List<Long> executed = new ArrayList<>();
        final List<String> errors = new ArrayList<>();
        long startTime, lastTime;
        int observations;

        Run(String label, String recipe, Object[] start, int window, int executions, Object[] end, boolean meltHematite) {
            this.label = label;
            this.alloy = alloy(recipe);
            this.start = start;
            this.window = window;
            this.executions = executions;
            this.end = end;
            this.meltHematite = meltHematite;
        }
    }

    @GameTest(template = TEMPLATE, batch = "alloy_processing", timeoutTicks = 400)
    public static void alloy_processing(GameTestHelper helper) {
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.MACHINE_CRUCIBLE.get(), CORE, Direction.NORTH);
        MachineCrucibleBlockEntity be = SmokeTestSupport.blockEntity(helper, CORE, MachineCrucibleBlockEntity.class);
        List<Run> runs = List.of(
                // steel: Fe 16, C 24, Flux 8 -> one execution at the multiple of 20 -> steel 16 (:63-65)
                new Run("steel", "crucible.steel", mats(Mats.MAT_IRON, 16, Mats.MAT_CARBON, 24, Mats.MAT_FLUX, 8), 22, 1, mats(Mats.MAT_STEEL, 16), false),
                // ferro: steel 48 + U238 24 -> three executions (16 + 8 each) at three consecutive multiples of 3 -> ferro 72 (:95-97)
                new Run("ferro", "crucible.ferro", mats(Mats.MAT_STEEL, 48, Mats.MAT_U238, 24), 11, 3, mats(Mats.MAT_FERRO, 72), false),
                // tcalloy: steel 64 + Tc 8 -> tcalloy 72 at the first multiple of 9 (:99-101)
                new Run("tcalloy", "crucible.tcalloy", mats(Mats.MAT_STEEL, 64, Mats.MAT_TECHNETIUM, 8), 11, 1, mats(Mats.MAT_TCALLOY, 72), false),
                // redcopper: copper 8 + redstone 8 -> mingrade 16 at the first even tick; 24 + 24 -> three executions in 6 ticks (:87-89)
                new Run("redcopper", "crucible.redcopper", mats(Mats.MAT_COPPER, 8, Mats.MAT_REDSTONE, 8), 4, 1, mats(Mats.MAT_MINGRADE, 16), false),
                new Run("redcopper x3", "crucible.redcopper", mats(Mats.MAT_COPPER, 24, Mats.MAT_REDSTONE, 24), 8, 3, mats(Mats.MAT_MINGRADE, 48), false),
                // hematite: two resource_hematite melted (MatDistribution.java:85 oreHematite INGOT.q(1) each) + flux 16 -> iron 72, slag 24 (:79-81)
                new Run("hematite", "crucible.hematite", mats(Mats.MAT_HEMATITE, 144, Mats.MAT_FLUX, 16), 8, 1, mats(Mats.MAT_IRON, 72, Mats.MAT_SLAG, 24), true));

        GameTestSequence seq = helper.startSequence();
        for(Run run : runs) {
            seq.thenExecute(guard(() -> setup(helper, be, run)))
                    .thenExecuteFor(run.window, () -> observe(helper, be, run))
                    .thenExecute(guard(() -> verify(be, run)));
        }
        seq.thenExecute(guard(() -> {
                    reset(be);
                    StringBuilder log = new StringBuilder();
                    for(Run run : runs) log.append(run.label).append(" executed at ").append(run.executed).append(" (set up at ").append(run.startTime).append("); ");
                    LOGGER.info("{} alloy_processing: crucible ticked by its own ticker; {}", TAG, log.toString().trim());
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "alloy_processing"))
                .thenSucceed();
    }

    private static void setup(GameTestHelper helper, MachineCrucibleBlockEntity be, Run run) {
        check(helper.getLevel().getBlockEntity(helper.absolutePos(CORE)) == be, run.label + ": the crucible was replaced");
        reset(be);
        be.recipe = run.alloy.name();
        check(be.getLoadedRecipe() != null, run.alloy.name() + " is not a loaded recipe");
        if(run.meltHematite) {
            // the real melt path for the recipe material: two creative-only resource_hematite blocks (no survival worldgen until Goal 28)
            ItemStack hematite = new ItemStack(NtmBlocks.RESOURCE_HEMATITE.get());
            smelt(be, hematite.copy());
            smelt(be, hematite.copy());
            stacks(be.recipeStack, "hematite: two resource_hematite melted with crucible.hematite selected", Mats.MAT_HEMATITE, 144);
            check(be.wasteStack.isEmpty(), "hematite: waste stack " + describe(be.wasteStack));
            be.heat = 0;
            be.progress = 0;
            // stand-in: the 16 flux of the recipe added directly (a powder_flux melts into 72)
            be.recipeStack.add(new Mats.MaterialStack(Mats.MAT_FLUX, 16));
        } else {
            for(int k = 0; k < run.start.length; k += 2) be.recipeStack.add(new Mats.MaterialStack((NTMMaterial) run.start[k], (int) run.start[k + 1]));
        }
        stacks(be.recipeStack, run.label + ": recipe stack at the start", run.start);
        run.model.clear();
        for(int k = 0; k < run.start.length; k += 2) run.model.put((NTMMaterial) run.start[k], (int) run.start[k + 1]);
        run.startTime = run.lastTime = helper.getLevel().getGameTime();
    }

    /** Runs inside thenExecuteFor, where a thrown assertion would only be retried: mismatches are collected and checked in verify. */
    private static void observe(GameTestHelper helper, MachineCrucibleBlockEntity be, Run run) {
        long now = helper.getLevel().getGameTime();
        for(long t = run.lastTime + 1; t <= now; t++) {
            if(t % run.alloy.frequency() > 0) continue;
            boolean enough = true;
            for(int k = 0; k < run.alloy.input().length; k += 2) enough &= run.model.getOrDefault((NTMMaterial) run.alloy.input()[k], 0) >= (int) run.alloy.input()[k + 1];
            if(!enough) continue;
            for(int k = 0; k < run.alloy.input().length; k += 2) run.model.merge((NTMMaterial) run.alloy.input()[k], -(int) run.alloy.input()[k + 1], Integer::sum);
            for(int k = 0; k < run.alloy.output().length; k += 2) run.model.merge((NTMMaterial) run.alloy.output()[k], (int) run.alloy.output()[k + 1], Integer::sum);
            run.executed.add(t);
        }
        run.lastTime = now;
        run.observations++;
        Map<NTMMaterial, Integer> got = new LinkedHashMap<>();
        for(Mats.MaterialStack s : be.recipeStack) if(s.amount != 0) got.merge(s.material, s.amount, Integer::sum);
        Map<NTMMaterial, Integer> want = new LinkedHashMap<>();
        run.model.forEach((m, a) -> { if(a != 0) want.put(m, a); });
        if(!got.equals(want)) run.errors.add("game time " + now + " (" + (now % run.alloy.frequency()) + " mod " + run.alloy.frequency() + "): recipe stack " + names(got) + ", expected " + names(want));
        if(!be.wasteStack.isEmpty()) run.errors.add("game time " + now + ": waste stack " + describe(be.wasteStack));
    }

    private static void verify(MachineCrucibleBlockEntity be, Run run) {
        check(run.errors.isEmpty(), run.label + ": " + run.errors);
        check(run.observations >= run.window - 2, run.label + ": only " + run.observations + " ticks observed of " + run.window);
        check(run.executed.size() == run.executions, run.label + ": the original's model executed " + run.executed.size() + " times at " + run.executed + ", expected " + run.executions);
        long first = (run.startTime / run.alloy.frequency() + 1) * run.alloy.frequency();
        for(int k = 0; k < run.executed.size(); k++) {
            check(run.executed.get(k) == first + (long) k * run.alloy.frequency(), run.label + ": execution " + k + " at " + run.executed.get(k) + ", expected " + (first + (long) k * run.alloy.frequency()));
        }
        stacks(be.recipeStack, run.label + ": recipe stack at the end", run.end);
    }

    // 3. acceptance with an alloy recipe (TileEntityCrucible.java:455-503: recipe inputs capped at required * capacity / recipe content, outputs
    // accepted, other materials refused; no recipe: everything to the waste stack). crucible.ferro: steel 16, U238 8 of 24 (CrucibleRecipes.java:95-97)
    @GameTest(template = TEMPLATE, batch = "alloy_acceptance", timeoutTicks = 100)
    public static void alloy_acceptance(GameTestHelper helper) {
        MachineCrucibleBlockEntity be = null;
        try {
            SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.MACHINE_CRUCIBLE.get(), CORE, Direction.NORTH);
            be = SmokeTestSupport.blockEntity(helper, CORE, MachineCrucibleBlockEntity.class);
            MachineCrucibleBlockEntity b = be;
            guard(() -> {
                check(MachineCrucibleBlockEntity.CAPACITY == CAPACITY, "crucible capacity " + MachineCrucibleBlockEntity.CAPACITY + ", expected " + CAPACITY);
                reset(b);
                b.recipe = "crucible.ferro";
                check(b.getLoadedRecipe() != null, "crucible.ferro is not loaded");
                check(b.isItemSmeltable(new ItemStack(NtmItems.INGOT_STEEL.get())), "ferro: the steel ingot is refused");
                List<String> u238 = new ArrayList<>();
                for(MaterialShapes shape : new MaterialShapes[] { MaterialShapes.INGOT, MaterialShapes.NUGGET, MaterialShapes.BILLET }) {
                    List<MaterialEntries.Entry> rows = MaterialEntries.getEntries(Mats.MAT_U238, shape);
                    check(!rows.isEmpty(), "MaterialEntries has no " + shape.name() + " row for U238");
                    for(MaterialEntries.Entry row : rows) {
                        ItemStack stack = row.stack(1);
                        check(b.isItemSmeltable(stack), "ferro: U238 " + shape.name() + " " + stack + " is refused");
                        u238.add(BuiltInRegistries.ITEM.getKey(stack.getItem()).getPath());
                    }
                }
                check(b.isItemSmeltable(new ItemStack(NtmItems.INGOT_FERROURANIUM.get())), "ferro: the ferrouranium ingot (output) is refused");
                check(!b.isItemSmeltable(new ItemStack(Items.IRON_INGOT)), "ferro: the iron ingot is accepted");
                check(!b.isItemSmeltable(new ItemStack(NtmItems.INGOT_COPPER.get())) && !b.isItemSmeltable(new ItemStack(Items.COPPER_INGOT)), "ferro: a copper ingot is accepted");
                int tc = 0;
                for(MaterialEntries.Entry row : MaterialEntries.getEntries()) {
                    if(row.material() != Mats.MAT_TECHNETIUM) continue;
                    check(!b.isItemSmeltable(row.stack(1)), "ferro: technetium " + row.stack(1) + " is accepted");
                    tc++;
                }
                check(tc > 0, "MaterialEntries has no technetium row");

                // proportional caps: steel 16 * 10368 / 24 = 6912, U238 8 * 10368 / 24 = 3456
                int steelMax = 16 * CAPACITY / 24, uMax = 8 * CAPACITY / 24;
                check(steelMax == 6912 && uMax == 3456, "cap arithmetic");
                b.recipeStack.add(new Mats.MaterialStack(Mats.MAT_STEEL, steelMax - 72));
                check(b.isItemSmeltable(new ItemStack(NtmItems.INGOT_STEEL.get())), "ferro: steel at " + (steelMax - 72) + " + 72 = " + steelMax + " is refused");
                b.recipeStack.get(0).amount = steelMax - 71;
                check(!b.isItemSmeltable(new ItemStack(NtmItems.INGOT_STEEL.get())), "ferro: steel at " + (steelMax - 71) + " + 72 > " + steelMax + " is accepted");
                ItemStack uIngot = MaterialEntries.getEntries(Mats.MAT_U238, MaterialShapes.INGOT).get(0).stack(1);
                check(b.isItemSmeltable(uIngot), "ferro: U238 ingot refused although only steel is at its cap");
                b.recipeStack.clear();
                b.recipeStack.add(new Mats.MaterialStack(Mats.MAT_U238, uMax - 72));
                check(b.isItemSmeltable(uIngot), "ferro: U238 at " + (uMax - 72) + " + 72 = " + uMax + " is refused");
                b.recipeStack.get(0).amount = uMax - 71;
                check(!b.isItemSmeltable(uIngot), "ferro: U238 at " + (uMax - 71) + " + 72 > " + uMax + " is accepted");

                // no recipe: iron ore and steel both go to the waste stack
                reset(b);
                check(b.isItemSmeltable(new ItemStack(Items.IRON_ORE)) && b.isItemSmeltable(new ItemStack(NtmItems.INGOT_STEEL.get())), "no recipe: iron ore or steel refused");
                smelt(b, new ItemStack(Items.IRON_ORE));
                smelt(b, new ItemStack(NtmItems.INGOT_STEEL.get()));
                stacks(b.wasteStack, "no recipe, iron ore + steel ingot: waste", Mats.MAT_IRON, 144, Mats.MAT_TITANIUM, 24, Mats.MAT_STONE, 162, Mats.MAT_STEEL, 72);
                check(b.recipeStack.isEmpty(), "no recipe: recipe stack " + describe(b.recipeStack));

                // crucible.bbronze outputs bbronze and slag (:107-109): slag scraps are accepted and land in the recipe stack
                reset(b);
                b.recipe = "crucible.bbronze";
                ItemStack slag = CopperScrapsItem.create(new Mats.MaterialStack(Mats.MAT_SLAG, 72));
                check(b.isItemSmeltable(slag), "bbronze: slag scraps (an output) are refused");
                smelt(b, slag);
                stacks(b.recipeStack, "bbronze, slag scraps: recipe stack", Mats.MAT_SLAG, 72);
                check(b.wasteStack.isEmpty(), "bbronze, slag scraps: waste " + describe(b.wasteStack));
                check(!b.isItemSmeltable(new ItemStack(Items.IRON_INGOT)), "bbronze: the iron ingot is accepted");
                LOGGER.info("{} alloy_acceptance: ferro accepts steel, ferrouranium and U238 {}; refuses iron, copper and {} technetium rows; caps {} / {}", TAG, u238, tc, steelMax, uMax);
            }).run();
        } finally {
            if(be != null) reset(be);
            discardItems(helper);
        }
        done(helper, "alloy_acceptance");
    }

    // 4. ferrouranium anvil (AnvilRecipes.java:62-72 iron / lead anvil + 10 ingot_ferrouranium -> anvil_ferrouranium, smithing tier 1;
    // NTMAnvil.java:42-49 tiers; AnvilRecipes.java:868-872 moderator row at tier 4; :1046-1064 isTierValid: tier >= tierLower without an upper bound)
    @GameTest(template = TEMPLATE, batch = "alloy_anvil_ferrouranium", timeoutTicks = 100)
    public static void anvil_ferrouranium(GameTestHelper helper) {
        guard(() -> {
            int ferroMeta = NTMAnvilBlock.Variant.FERROURANIUM.ordinal();
            check(ferroMeta == 4 && NTMAnvilBlock.Variant.FERROURANIUM.tier == TIER_NUCLEAR && NTMAnvilBlock.Variant.DESH.tier == TIER_OIL,
                    "anvil variants: ferrouranium meta " + ferroMeta + " tier " + NTMAnvilBlock.Variant.FERROURANIUM.tier + ", desh tier " + NTMAnvilBlock.Variant.DESH.tier + "; expected 4 / 4 / 3");
            check(NTMAnvilBlock.getTierForMeta(ferroMeta) == TIER_NUCLEAR, "getTierForMeta(4) is " + NTMAnvilBlock.getTierForMeta(ferroMeta));
            for(NTMAnvilBlock.Variant base : new NTMAnvilBlock.Variant[] { NTMAnvilBlock.Variant.IRON, NTMAnvilBlock.Variant.LEAD }) {
                ItemStack left = MetaHelper.newStack(NtmBlocks.ANVIL.get(), 1, base.ordinal());
                List<AnvilSmithingRecipe> matching = smithingMatches(left, new ItemStack(NtmItems.INGOT_FERROURANIUM.get(), 10));
                check(matching.size() == 1, base + " anvil + 10 ferrouranium matches " + matching.size() + " smithing recipes, expected 1");
                AnvilSmithingRecipe recipe = matching.get(0);
                ItemStack out = recipe.getOutput(left, new ItemStack(NtmItems.INGOT_FERROURANIUM.get(), 10));
                check(out.is(NtmBlocks.ANVIL.get().asItem()) && MetaHelper.getMeta(out) == ferroMeta && out.getCount() == 1 && recipe.getTier() == 1,
                        base + " anvil + 10 ferrouranium yields " + out + " meta " + MetaHelper.getMeta(out) + " at tier " + recipe.getTier() + ", expected one ferrouranium anvil (meta 4) at tier 1");
                check(recipe.amountConsumed(1, false) == 10, base + ": consumes " + recipe.amountConsumed(1, false) + " ingots");
                for(AnvilSmithingRecipe r : smithingMatches(left, new ItemStack(NtmItems.INGOT_FERROURANIUM.get(), 9))) {
                    check(!(r.getSimpleOutput().is(NtmBlocks.ANVIL.get().asItem()) && MetaHelper.getMeta(r.getSimpleOutput()) == ferroMeta), base + " anvil + 9 ferrouranium matches the upgrade");
                }
            }

            int moderatorRow = rowConsuming(NtmBlocks.RBMK_MODERATOR.get().asItem());
            Item moderator = NtmBlocks.RBMK_MODERATOR.get().asItem();
            Player player = playerWith(helper, new ItemStack(moderator));
            check(AnvilRecipes.executeConstruction(player, TIER_NUCLEAR, moderatorRow, 0), "tier 4: the moderator row did not execute");
            inventory(player, "tier 4 moderator row", NtmBlocks.RBMK_BLANK.get().asItem(), 1, NtmBlocks.BLOCK_GRAPHITE.get().asItem(), 4);
            Player low = playerWith(helper, new ItemStack(moderator));
            check(!AnvilRecipes.executeConstruction(low, TIER_OIL, moderatorRow, 0), "tier 3: the moderator row executed");
            inventory(low, "tier 3 moderator row (refused)", moderator, 1);
            Player high = playerWith(helper, new ItemStack(moderator));
            check(AnvilRecipes.executeConstruction(high, TIER_NUCLEAR + 1, moderatorRow, 0), "tier 5: the moderator row did not execute (no upper bound)");
            inventory(high, "tier 5 moderator row", NtmBlocks.RBMK_BLANK.get().asItem(), 1, NtmBlocks.BLOCK_GRAPHITE.get().asItem(), 4);

            // server recheck: AnvilConstructionPacket.handleServer passes menu.getTier(); the menu built with NTMAnvilBlock.useWithoutItem's arguments
            for(NTMAnvilBlock.Variant variant : new NTMAnvilBlock.Variant[] { NTMAnvilBlock.Variant.FERROURANIUM, NTMAnvilBlock.Variant.DESH }) {
                BlockPos rel = variant == NTMAnvilBlock.Variant.DESH ? new BlockPos(6, 1, 2) : new BlockPos(2, 1, 2);
                helper.setBlock(rel, NtmBlocks.ANVIL.get().defaultBlockState().setValue(NTMAnvilBlock.SUBTYPE, variant.ordinal()));
                BlockPos abs = helper.absolutePos(rel);
                BlockState state = helper.getLevel().getBlockState(abs);
                check(state.is(NtmBlocks.ANVIL.get()), "the " + variant + " anvil was not placed: " + state);
                int tier = ((NTMAnvilBlock) state.getBlock()).getTier(state);
                AnvilMenu menu = new AnvilMenu(0, player.getInventory(), abs, tier);
                int expected = variant == NTMAnvilBlock.Variant.DESH ? TIER_OIL : TIER_NUCLEAR;
                check(menu.getTier() == expected, "the menu of a placed " + variant + " anvil has tier " + menu.getTier() + ", expected " + expected);
            }
            LOGGER.info("{} anvil_ferrouranium: smithing upgrade from iron and lead anvils, moderator row {} at tiers 3/4/5, menu tiers 4 / 3", TAG, moderatorRow);
        }).run();
        discardItems(helper);
        done(helper, "anvil_ferrouranium");
    }

    // 5. the twelve tier-4 RBMK recycling rows (original AnvilRecipes.java:868-901,914-925 and the !enable528 branch :927-951; the 1:many
    // constructor's RECYCLING overlay :1026-1030; outputs without a chance = 1.0). Not ported: the ReaSim rows :902-913, reactor_research :952-962.
    @GameTest(template = TEMPLATE, batch = "alloy_rbmk_recycling_rows", timeoutTicks = 100)
    public static void rbmk_recycling_rows(GameTestHelper helper) {
        guard(() -> {
            Item blank = NtmBlocks.RBMK_BLANK.get().asItem(), graphite = NtmBlocks.BLOCK_GRAPHITE.get().asItem(), control = NtmBlocks.RBMK_CONTROL.get().asItem();
            Item grate = NtmBlocks.STEEL_GRATE.get().asItem();
            Map<Item, Object[]> want = new LinkedHashMap<>();
            want.put(NtmBlocks.RBMK_MODERATOR.get().asItem(), new Object[] { blank, 1, graphite, 4 });
            want.put(NtmBlocks.RBMK_ABSORBER.get().asItem(), new Object[] { blank, 1, NtmItems.INGOT_BORON.get(), 8 });
            want.put(NtmBlocks.RBMK_REFLECTOR.get().asItem(), new Object[] { blank, 1, NtmItems.NEUTRON_REFLECTOR.get(), 8 });
            want.put(control, new Object[] { NtmBlocks.RBMK_ABSORBER.get().asItem(), 1, NtmItems.INGOT_GRAPHITE.get(), 2, NtmItems.MOTOR.get(), 2 });
            want.put(NtmBlocks.RBMK_CONTROL_MOD.get().asItem(), new Object[] { control, 1, graphite, 4, NtmItems.NUGGET_BISMUTH.get(), 4 });
            // EnumCircuitType.ADVANCED is NEO's circuit_military_grade_board
            want.put(NtmBlocks.RBMK_CONTROL_AUTO.get().asItem(), new Object[] { control, 1, NtmItems.CIRCUIT_MILITARY_GRADE_BOARD.get(), 1, NtmItems.CRT_DISPLAY.get(), 1 });
            want.put(NtmBlocks.RBMK_OUTGASSER.get().asItem(), new Object[] { blank, 1, grate, 6, NtmItems.TANK_STEEL.get(), 1, Items.HOPPER, 1 });
            want.put(NtmBlocks.RBMK_STORAGE.get().asItem(), new Object[] { blank, 1, NtmBlocks.CRATE_STEEL.get().asItem(), 2 });
            // shell / pipe metadata STEEL and COPPER are NEO's shell_steel, shell_copper and pipe_copper
            want.put(NtmBlocks.RBMK_ROD.get().asItem(), new Object[] { blank, 1, NtmItems.SHELL_STEEL.get(), 2 });
            want.put(NtmBlocks.RBMK_ROD_MOD.get().asItem(), new Object[] { NtmBlocks.RBMK_ROD.get().asItem(), 1, graphite, 4, NtmItems.NUGGET_BISMUTH.get(), 4 });
            want.put(NtmBlocks.RBMK_BOILER.get().asItem(), new Object[] { blank, 1, NtmItems.PIPE_COPPER.get(), 6, NtmItems.SHELL_COPPER.get(), 2 });
            want.put(NtmBlocks.RBMK_COOLER.get().asItem(), new Object[] { blank, 1, grate, 4, NtmItems.PLATE_POLYMER.get(), 4 });

            // every registered hbmsntm block item named rbmk_*: the rows consuming any of them are exactly the twelve, in the original order
            List<Item> rbmk = new ArrayList<>();
            List<Item> excluded = new ArrayList<>();
            for(Item item : BuiltInRegistries.ITEM) {
                ResourceLocation key = BuiltInRegistries.ITEM.getKey(item);
                if(!key.getNamespace().equals(NuclearTechMod.MODID)) continue;
                if(item instanceof BlockItem && key.getPath().startsWith("rbmk_")) rbmk.add(item);
                if(key.getPath().contains("reasim") || key.getPath().contains("reactor_research")) excluded.add(item);
            }
            List<AnvilConstructionRecipe> all = AnvilRecipes.getConstruction();
            List<Integer> indices = new ArrayList<>();
            List<Item> order = new ArrayList<>();
            for(int k = 0; k < all.size(); k++) {
                AnvilConstructionRecipe recipe = all.get(k);
                for(AnvilOutput output : recipe.output) check(!output.stack.isEmpty() && output.stack.getItem() != Items.AIR, "construction row " + k + " has an empty output");
                for(AStack input : recipe.input) for(Item item : excluded) check(!input.matchesRecipe(new ItemStack(item), true), "construction row " + k + " consumes " + item + " (not ported)");
                boolean column = false;
                for(AStack input : recipe.input) for(Item item : rbmk) column |= input.matchesRecipe(new ItemStack(item), true);
                if(!column) continue;
                check(recipe.input.size() == 1 && recipe.input.get(0) instanceof ComparableStack, "construction row " + k + " takes an RBMK column among " + recipe.input.size() + " inputs");
                ComparableStack in = (ComparableStack) recipe.input.get(0);
                check(in.stacksize == 1, "construction row " + k + " takes " + in.stacksize + " columns");
                indices.add(k);
                order.add(in.item);
                Object[] outs = want.get(in.item);
                check(outs != null, "construction row " + k + " recycles " + in.item + ", which the original does not recycle at :868-951");
                check(recipe.tierLower == TIER_NUCLEAR && recipe.tierUpper == -1 && recipe.getOverlay() == OverlayType.RECYCLING,
                        in.item + " row: tier " + recipe.tierLower + ".." + recipe.tierUpper + " overlay " + recipe.getOverlay() + ", expected 4..-1 RECYCLING");
                check(recipe.output.size() * 2 == outs.length, in.item + " row has " + recipe.output.size() + " outputs, expected " + outs.length / 2);
                for(int o = 0; o < recipe.output.size(); o++) {
                    AnvilOutput output = recipe.output.get(o);
                    check(output.stack.is((Item) outs[o * 2]) && output.stack.getCount() == (int) outs[o * 2 + 1] && output.chance == 1F,
                            in.item + " row output " + o + " is " + output.stack + " at " + output.chance + ", expected " + outs[o * 2 + 1] + " " + outs[o * 2] + " at 1.0");
                }
            }
            check(order.equals(new ArrayList<>(want.keySet())), "the RBMK recycling rows are " + order + ", expected " + want.keySet() + " (original order)");
            check(indices.get(0) == all.size() - 12 && indices.get(11) == all.size() - 1, "the RBMK rows are at " + indices + ", expected the last 12 of " + all.size());

            // each row executed at tier 4 by a mock player gives exactly its outputs
            int k = 0;
            for(Map.Entry<Item, Object[]> e : want.entrySet()) {
                Player player = playerWith(helper, new ItemStack(e.getKey()));
                check(AnvilRecipes.executeConstruction(player, TIER_NUCLEAR, indices.get(k), 0), e.getKey() + " row did not execute at tier 4");
                inventory(player, e.getKey() + " recycled at tier 4", e.getValue());
                k++;
            }
            LOGGER.info("{} rbmk_recycling_rows: rows {} of {}, all 12 executed at tier 4; {} rbmk_* block items scanned, not-ported items present: {}", TAG, indices, all.size(), rbmk.size(), excluded);
        }).run();
        discardItems(helper);
        done(helper, "rbmk_recycling_rows");
    }

    // 6. lead anvil (CraftingManager.java:295 III / B / III, lead ingot and block; :294 iron anvil unchanged; :296 murky anvil not ported) and the
    // anvil regressions against the 27B start (baseline AnvilRecipes: 18 upgrade rows + 5 special smithing recipes, 103 construction rows)
    @GameTest(template = TEMPLATE, batch = "alloy_anvil_lead", timeoutTicks = 100)
    public static void anvil_lead_and_regressions(GameTestHelper helper) {
        guard(() -> {
            Item anvil = NtmBlocks.ANVIL.get().asItem();
            ShapedRecipe lead = shaped(helper, "anvil_lead", NtmItems.INGOT_LEAD.get(), NtmBlocks.BLOCK_LEAD.get().asItem(), 1);
            ShapedRecipe iron = shaped(helper, "anvil_iron", Items.IRON_INGOT, Items.IRON_BLOCK, 0);
            for(Object[] r : new Object[][] { { lead, NtmItems.INGOT_LEAD.get(), NtmBlocks.BLOCK_LEAD.get().asItem(), 1 }, { iron, Items.IRON_INGOT, Items.IRON_BLOCK, 0 } }) {
                ItemStack i = new ItemStack((Item) r[1]), b = new ItemStack((Item) r[2]);
                CraftingInput grid = CraftingInput.of(3, 3, List.of(i, i, i, ItemStack.EMPTY, b, ItemStack.EMPTY, i, i, i));
                ShapedRecipe recipe = (ShapedRecipe) r[0];
                check(recipe.matches(grid, helper.getLevel()), r[1] + " grid does not match its anvil recipe");
                ItemStack crafted = recipe.assemble(grid, helper.getLevel().registryAccess());
                check(crafted.is(anvil) && crafted.getCount() == 1 && MetaHelper.getMeta(crafted) == (int) r[3], "crafting with " + r[1] + " gives " + crafted + " meta " + MetaHelper.getMeta(crafted) + ", expected one anvil meta " + r[3]);
            }
            List<ResourceLocation> anvilRecipes = new ArrayList<>();
            for(RecipeHolder<?> holder : helper.getLevel().getRecipeManager().getRecipes()) {
                check(!holder.id().getPath().contains("murky"), "recipe " + holder.id() + " (murky anvil not ported)");
                if(holder.value().getResultItem(helper.getLevel().registryAccess()).is(anvil)) anvilRecipes.add(holder.id());
            }
            check(anvilRecipes.size() == 2 && anvilRecipes.contains(id("anvil_iron")) && anvilRecipes.contains(id("anvil_lead")), "recipes making an anvil: " + anvilRecipes + ", expected anvil_iron and anvil_lead");

            // smithing: 18 upgrade rows (iron then lead for each target, baseline AnvilRecipes.java:99-124) and the 5 special recipes, unchanged
            NTMAnvilBlock.Variant[] targets = { NTMAnvilBlock.Variant.STEEL, NTMAnvilBlock.Variant.DESH, NTMAnvilBlock.Variant.FERROURANIUM, NTMAnvilBlock.Variant.SATURNITE,
                    NTMAnvilBlock.Variant.BISMUTH_BRONZE, NTMAnvilBlock.Variant.ARSENIC_BRONZE, NTMAnvilBlock.Variant.FERRIC_SCHRABIDATE, NTMAnvilBlock.Variant.DINEUTRONIUM,
                    NTMAnvilBlock.Variant.OSMIRIDIUM };
            Item[] ingots = { NtmItems.INGOT_STEEL.get(), NtmItems.INGOT_DESH.get(), NtmItems.INGOT_FERROURANIUM.get(), NtmItems.INGOT_SATURNITE.get(), NtmItems.INGOT_BISMUTH_BRONZE.get(),
                    NtmItems.INGOT_ARSENIC_BRONZE.get(), NtmItems.INGOT_SCHRABIDATE.get(), NtmItems.INGOT_DINEUTRONIUM.get(), NtmItems.INGOT_OSMIRIDIUM.get() };
            List<AnvilSmithingRecipe> smithing = AnvilRecipes.getSmithing();
            check(smithing.size() == 23, "smithing has " + smithing.size() + " recipes, expected 18 upgrades + 5 special (start)");
            for(int t = 0; t < targets.length; t++) {
                for(int a = 0; a < 2; a++) {
                    AnvilSmithingRecipe r = smithing.get(t * 2 + a);
                    NTMAnvilBlock.Variant base = a == 0 ? NTMAnvilBlock.Variant.IRON : NTMAnvilBlock.Variant.LEAD;
                    ItemStack left = MetaHelper.newStack(NtmBlocks.ANVIL.get(), 1, base.ordinal());
                    ItemStack right = new ItemStack(ingots[t], 10);
                    ItemStack out = r.getSimpleOutput();
                    check(r.getClass() == AnvilSmithingRecipe.class && r.getTier() == 1 && r.matches(left, right) && !r.matches(left, new ItemStack(ingots[t], 9))
                                    && out.is(anvil) && MetaHelper.getMeta(out) == targets[t].ordinal(),
                            "smithing row " + (t * 2 + a) + " is not " + base + " + 10 " + ingots[t] + " -> " + targets[t] + ": tier " + r.getTier() + ", output " + out + " meta " + MetaHelper.getMeta(out));
                }
            }
            Class<?>[] special = { AnvilSmithingCyanideRecipe.class, AnvilSmithingRenameRecipe.class, AnvilSmithingCastMoldRecipe.class, AnvilSmithingIngotMoldRecipe.class, AnvilSmithingBladeMoldRecipe.class };
            for(int s = 0; s < special.length; s++) check(smithing.get(18 + s).getClass() == special[s], "smithing row " + (18 + s) + " is " + smithing.get(18 + s).getClass().getSimpleName() + ", expected " + special[s].getSimpleName());

            // construction rows before the twelve RBMK rows: count and the tiers of the wire, desh, bismuth, HEV and lunar rows
            List<AnvilConstructionRecipe> all = AnvilRecipes.getConstruction();
            int start = 103;
            check(all.size() == start + 12, "construction has " + all.size() + " rows, expected the start's " + start + " + 12");
            Item[] wires = { NtmItems.WIRE_GOLD.get(), NtmItems.WIRE_COPPER.get(), NtmItems.WIRE_ALUMINIUM.get(), NtmItems.WIRE_ZIRCONIUM.get(), NtmItems.WIRE_LEAD.get(), NtmItems.WIRE_TUNGSTEN.get(),
                    NtmItems.WIRE_SCHRABIDIUM.get(), NtmItems.WIRE_STEEL.get(), NtmItems.WIRE_MAGNETIZED_TUNGSTEN.get(), NtmItems.WIRE_CARBON.get(), NtmItems.WIRE_RED_COPPER.get() };
            for(Item wire : wires) {
                int row = rowMaking(all, start, wire, 8);
                check(all.get(row).tierLower == TIER_NUCLEAR && all.get(row).tierUpper == -1, wire + " row tier " + all.get(row).tierLower);
            }
            Object[][] tiers = { { NtmItems.PLATE_DESH.get(), 4, TIER_OIL }, { NtmItems.PLATE_BISMUTH.get(), 1, TIER_NUCLEAR }, { NtmItems.PLATE_ARMOR_HEV.get(), 1, TIER_NUCLEAR },
                    { NtmItems.PLATE_ARMOR_LUNAR.get(), 1, TIER_NUCLEAR } };
            for(Object[] t : tiers) {
                int row = rowMaking(all, start, (Item) t[0], (int) t[1]);
                check(all.get(row).tierLower == (int) t[2] && all.get(row).tierUpper == -1, t[0] + " row tier " + all.get(row).tierLower + ", expected " + t[2]);
            }
            int lastTier4 = 0;
            for(int k = 0; k < start; k++) if(all.get(k).tierLower >= TIER_NUCLEAR) lastTier4++;
            check(lastTier4 == 14, lastTier4 + " start rows need tier 4, expected 14 (11 wires, bismuth plate, HEV and lunar plates)");

            // a desh anvil (tier 3) executes the tier-3 plate_desh row and not a tier-4 wire row
            int deshRow = rowMaking(all, start, NtmItems.PLATE_DESH.get(), 4);
            TagKey<Item> plastic = TagKey.create(net.minecraft.core.registries.Registries.ITEM, ResourceLocation.fromNamespaceAndPath("ntm", "powders_plastic"));
            Optional<Holder<Item>> plasticItem = Optional.empty();
            for(Holder<Item> h : BuiltInRegistries.ITEM.getTagOrEmpty(plastic)) { plasticItem = Optional.of(h); break; }
            check(plasticItem.isPresent(), "ntm:powders_plastic is empty");
            Player desh = playerWith(helper, new ItemStack(NtmItems.INGOT_DESH.get(), 4), new ItemStack(NtmItems.INGOT_DURA_STEEL.get(), 1), new ItemStack(plasticItem.get().value(), 2));
            check(AnvilRecipes.executeConstruction(desh, NTMAnvilBlock.Variant.DESH.tier, deshRow, 0), "the desh anvil did not execute the plate_desh row");
            inventory(desh, "plate_desh at tier 3", NtmItems.PLATE_DESH.get(), 4);
            int wireRow = rowMaking(all, start, NtmItems.WIRE_COPPER.get(), 8);
            Player wire = playerWith(helper, new ItemStack(Items.COPPER_INGOT));
            check(!AnvilRecipes.executeConstruction(wire, NTMAnvilBlock.Variant.DESH.tier, wireRow, 0), "the desh anvil executed the tier-4 copper wire row");
            inventory(wire, "copper wire at tier 3 (refused)", Items.COPPER_INGOT, 1);
            LOGGER.info("{} anvil_lead_and_regressions: anvil recipes {}, {} smithing rows, {} construction rows (start {} + 12), plate_desh row {}, copper wire row {}",
                    TAG, anvilRecipes, smithing.size(), all.size(), start, deshRow, wireRow);
        }).run();
        discardItems(helper);
        done(helper, "anvil_lead_and_regressions");
    }

    // 7. hbmCrucible.json (SerializableRecipe.java:142-156: an existing file replaces the defaults, otherwise defaults + the _ template;
    // CrucibleRecipes.java:143-187 name / frequency / icon / input / output). NEO-only: an entry naming an unknown material is skipped.
    @GameTest(template = TEMPLATE, batch = "alloy_config_file", timeoutTicks = 100)
    public static void alloy_config_file(GameTestHelper helper) {
        Path dir = helper.getLevel().getServer().getServerDirectory().resolve("hbm-goal27b-gametest");
        Path template = dir.resolve("_hbmCrucible.json"), custom = dir.resolve("hbmCrucible.json"), unknown = dir.resolve("hbmCrucible_unknown.json");
        try {
            guard(() -> {
                try {
                    Files.createDirectories(dir);
                    List<Alloy> want = original();
                    CrucibleRecipes.INSTANCE.writeTemplateFile(template.toFile());
                    JsonObject json = JsonParser.parseString(Files.readString(template, StandardCharsets.UTF_8)).getAsJsonObject();
                    JsonArray recipes = json.getAsJsonArray("recipes");
                    check(recipes.size() == 13, "the template has " + recipes.size() + " recipes, expected 13");
                    for(int k = 0; k < 13; k++) {
                        JsonObject r = recipes.get(k).getAsJsonObject();
                        Alloy a = want.get(k);
                        check(a.name().equals(r.get("name").getAsString()) && r.get("frequency").getAsInt() == a.frequency(), "template entry " + k + " is " + r.get("name") + " / " + r.get("frequency") + ", expected " + a.name() + " / " + a.frequency());
                        JsonArray icon = r.getAsJsonArray("icon");
                        check(icon.size() == 1 && icon.get(0).getAsString().equals(id(a.icon()).toString()), a.name() + " template icon " + icon);
                        jsonPairs(r.getAsJsonArray("input"), a.input(), a.name() + " template input");
                        jsonPairs(r.getAsJsonArray("output"), a.output(), a.name() + " template output");
                    }

                    // a player file replaces the defaults: only its entry is loaded
                    String steel = Mats.MAT_STEEL.names[0], ferro = Mats.MAT_FERRO.names[0];
                    Files.writeString(custom, "{\"recipes\":[{\"name\":\"crucible.test\",\"frequency\":5,\"icon\":[\"hbmsntm:ingot_steel\"],\"input\":[[\"" + steel + "\",8]],\"output\":[[\"" + ferro + "\",8]]}]}", StandardCharsets.UTF_8);
                    CrucibleRecipes.INSTANCE.deleteRecipes();
                    check(CrucibleRecipes.INSTANCE.readRecipeFile(custom.toFile()), "the player file was rejected as a whole");
                    List<CrucibleRecipe> list = CrucibleRecipes.INSTANCE.recipeOrderedList;
                    check(list.size() == 1 && "crucible.test".equals(list.get(0).getInternalName()) && CrucibleRecipes.INSTANCE.recipeNameMap.size() == 1, "after the player file: " + list.size() + " recipes, expected only crucible.test (defaults not merged)");
                    CrucibleRecipe test = list.get(0);
                    check(test.frequency == 5 && test.getIcon().is(NtmItems.INGOT_STEEL.get()), "crucible.test frequency " + test.frequency + " icon " + test.getIcon());
                    pairs(List.of(test.input), mats(Mats.MAT_STEEL, 8), "crucible.test input");
                    pairs(List.of(test.output), mats(Mats.MAT_FERRO, 8), "crucible.test output");

                    // an entry naming an unknown material is skipped, the rest kept
                    Files.writeString(unknown, "{\"recipes\":[{\"name\":\"crucible.bad\",\"frequency\":5,\"icon\":[\"hbmsntm:ingot_steel\"],\"input\":[[\"NotAMaterial27B\",8]],\"output\":[[\"" + ferro + "\",8]]},"
                            + "{\"name\":\"crucible.test2\",\"frequency\":7,\"icon\":[\"hbmsntm:ingot_steel\"],\"input\":[[\"" + steel + "\",16]],\"output\":[[\"" + ferro + "\",16]]}]}", StandardCharsets.UTF_8);
                    CrucibleRecipes.INSTANCE.deleteRecipes();
                    check(CrucibleRecipes.INSTANCE.readRecipeFile(unknown.toFile()), "the file with an unknown material was rejected as a whole");
                    check(list.size() == 1 && "crucible.test2".equals(list.get(0).getInternalName()) && list.get(0).frequency == 7, "after the unknown-material file: " + names(list) + ", expected only crucible.test2");
                } catch(IOException e) {
                    throw new RuntimeException(e);
                }
            }).run();
        } finally {
            CrucibleRecipes.INSTANCE.deleteRecipes();
            CrucibleRecipes.INSTANCE.registerDefaults();
            try {
                Files.deleteIfExists(template);
                Files.deleteIfExists(custom);
                Files.deleteIfExists(unknown);
                Files.deleteIfExists(dir);
            } catch(IOException e) {
                LOGGER.warn("{} alloy_config_file: could not delete the temporary files in {}: {}", TAG, dir, e.toString());
            }
        }
        guard(() -> {
            List<String> names = names(CrucibleRecipes.INSTANCE.recipeOrderedList);
            List<String> want = new ArrayList<>();
            for(Alloy a : original()) want.add(a.name());
            check(names.equals(want) && CrucibleRecipes.INSTANCE.recipeNameMap.size() == 13, "after the restore the crucible has " + names + ", expected the 13 defaults");
            check(!Files.exists(dir), "the temporary directory " + dir + " survived");
            LOGGER.info("{} alloy_config_file: template of 13 written and parsed, player file replaces the defaults, unknown material skipped; defaults restored", TAG);
        }).run();
        done(helper, "alloy_config_file");
    }

    // ---------------------------------------------------------------- helpers

    private static ResourceLocation id(String path) {
        return ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path);
    }

    private static Object[] mats(Object... pairs) {
        return pairs;
    }

    private static void pairs(List<Mats.MaterialStack> got, Object[] want, String label) {
        stacks(got, label, want);
    }

    private static void stacks(List<Mats.MaterialStack> got, String label, Object... pairs) {
        boolean ok = got.size() * 2 == pairs.length;
        for(int i = 0; ok && i < got.size(); i++) ok = got.get(i).material == pairs[i * 2] && got.get(i).amount == (int) pairs[i * 2 + 1];
        check(ok, label + " gives " + describe(got) + ", expected " + describePairs(pairs));
    }

    private static void jsonPairs(JsonArray got, Object[] want, String label) {
        boolean ok = got.size() * 2 == want.length;
        for(int i = 0; ok && i < got.size(); i++) {
            JsonArray e = got.get(i).getAsJsonArray();
            ok = e.size() == 2 && e.get(0).getAsString().equals(((NTMMaterial) want[i * 2]).names[0]) && e.get(1).getAsInt() == (int) want[i * 2 + 1];
        }
        check(ok, label + " is " + got + ", expected " + describePairs(want));
    }

    private static String describePairs(Object[] pairs) {
        StringBuilder sb = new StringBuilder("[");
        for(int i = 0; i < pairs.length; i += 2) sb.append(i == 0 ? "" : ", ").append(((NTMMaterial) pairs[i]).names[0]).append(' ').append(pairs[i + 1]);
        return sb.append(']').toString();
    }

    private static void smelt(MachineCrucibleBlockEntity be, ItemStack stack) {
        check(be.isItemSmeltable(stack), stack + " is not smeltable for the smelt step");
        be.slots.set(0, stack);
        be.heat = MachineCrucibleBlockEntity.MAX_HEAT;
        be.progress = MachineCrucibleBlockEntity.PROCESS_TIME - 1;
        be.updateEntity();
        check(be.slots.get(0).isEmpty() && be.progress == 0, "after one tick at full heat the slot holds " + be.slots.get(0) + " and progress is " + be.progress);
    }

    private static void reset(MachineCrucibleBlockEntity be) {
        be.recipeStack.clear();
        be.wasteStack.clear();
        for(int i = 0; i < be.slots.size(); i++) be.slots.set(i, ItemStack.EMPTY);
        be.recipe = MachineCrucibleBlockEntity.NO_RECIPE;
        be.heat = 0;
        be.progress = 0;
    }

    private static List<AnvilSmithingRecipe> smithingMatches(ItemStack left, ItemStack right) {
        List<AnvilSmithingRecipe> out = new ArrayList<>();
        for(AnvilSmithingRecipe r : AnvilRecipes.getSmithing()) if(r.matches(left, right)) out.add(r);
        return out;
    }

    private static int rowConsuming(Item item) {
        int found = -1;
        List<AnvilConstructionRecipe> all = AnvilRecipes.getConstruction();
        for(int k = 0; k < all.size(); k++) {
            for(AStack input : all.get(k).input) {
                if(input.matchesRecipe(new ItemStack(item), true)) {
                    check(found == -1, "two construction rows consume " + item + ": " + found + " and " + k);
                    found = k;
                }
            }
        }
        check(found != -1, "no construction row consumes " + item);
        return found;
    }

    /** The single row among the first {@code limit} whose only output is {@code count} of {@code item}. */
    private static int rowMaking(List<AnvilConstructionRecipe> all, int limit, Item item, int count) {
        int found = -1;
        for(int k = 0; k < limit; k++) {
            AnvilConstructionRecipe r = all.get(k);
            if(r.output.size() == 1 && r.output.get(0).stack.is(item) && r.output.get(0).stack.getCount() == count) {
                check(found == -1, "two construction rows make " + count + " " + item + ": " + found + " and " + k);
                found = k;
            }
        }
        check(found != -1, "no start construction row makes " + count + " " + item);
        return found;
    }

    private static Player playerWith(GameTestHelper helper, ItemStack... stacks) {
        Player player = helper.makeMockPlayer(GameType.SURVIVAL);
        player.getInventory().clearContent();
        for(ItemStack s : stacks) check(player.getInventory().add(s.copy()), "the mock player cannot hold " + s);
        return player;
    }

    /** The main inventory holds exactly these (item, count) pairs, summed over slots. */
    private static void inventory(Player player, String label, Object... pairs) {
        Map<Item, Integer> got = new LinkedHashMap<>();
        for(ItemStack s : player.getInventory().items) if(!s.isEmpty()) got.merge(s.getItem(), s.getCount(), Integer::sum);
        Map<Item, Integer> want = new LinkedHashMap<>();
        for(int i = 0; i < pairs.length; i += 2) want.merge(((ItemLike) pairs[i]).asItem(), (int) pairs[i + 1], Integer::sum);
        check(got.equals(want), label + ": inventory " + got + ", expected " + want);
    }

    /** The shaped III / B / III anvil recipe with these keys and an anvil of this meta as its single result. */
    private static ShapedRecipe shaped(GameTestHelper helper, String path, Item ingot, Item block, int meta) {
        Optional<RecipeHolder<?>> holder = helper.getLevel().getRecipeManager().byKey(id(path));
        check(holder.isPresent(), "recipe " + id(path) + " is not loaded");
        Recipe<?> recipe = holder.get().value();
        check(recipe instanceof ShapedRecipe, path + " is " + recipe.getClass().getSimpleName() + ", expected a shaped recipe");
        ShapedRecipe shaped = (ShapedRecipe) recipe;
        String[] pattern = { "III", " B ", "III" };
        check(shaped.getWidth() == 3 && shaped.getHeight() == 3, path + " is " + shaped.getWidth() + "x" + shaped.getHeight());
        List<Ingredient> ingredients = shaped.getIngredients();
        for(int row = 0; row < 3; row++) for(int col = 0; col < 3; col++) {
            char symbol = pattern[row].charAt(col);
            Ingredient ingredient = ingredients.get(row * 3 + col);
            if(symbol == ' ') {
                check(ingredient.isEmpty(), path + " cell " + row + "," + col + " is not empty");
            } else {
                Item item = symbol == 'I' ? ingot : block, other = symbol == 'I' ? block : ingot;
                check(ingredient.test(new ItemStack(item)) && !ingredient.test(new ItemStack(other)), path + " cell " + row + "," + col + " does not take exactly " + item);
            }
        }
        ItemStack result = recipe.getResultItem(helper.getLevel().registryAccess());
        check(result.is(NtmBlocks.ANVIL.get().asItem()) && result.getCount() == 1 && MetaHelper.getMeta(result) == meta, path + " yields " + result + " meta " + MetaHelper.getMeta(result) + ", expected one anvil meta " + meta);
        return shaped;
    }

    private static JsonObject lang(String name) {
        try(InputStream in = CrucibleAlloyGameTests.class.getResourceAsStream("/assets/hbmsntm/lang/" + name + ".json")) {
            check(in != null, "the language file " + name + ".json is not on the classpath of the running server");
            return JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject();
        } catch(IOException e) {
            throw new RuntimeException(e);
        }
    }

    private static String describe(List<Mats.MaterialStack> list) {
        List<String> out = new ArrayList<>();
        for(Mats.MaterialStack s : list) out.add(s.material.names[0] + " " + s.amount);
        return out.toString();
    }

    private static String names(Map<NTMMaterial, Integer> map) {
        List<String> out = new ArrayList<>();
        map.forEach((m, a) -> out.add(m.names[0] + " " + a));
        return out.toString();
    }

    private static List<String> names(List<CrucibleRecipe> list) {
        List<String> out = new ArrayList<>();
        for(CrucibleRecipe r : list) out.add(r.getInternalName());
        return out;
    }

    private static void discardItems(GameTestHelper helper) {
        Vec3 abs = helper.absoluteVec(new Vec3(8.5, 1, 8.5));
        for(ItemEntity entity : helper.getLevel().getEntitiesOfClass(ItemEntity.class, new AABB(abs, abs).inflate(8D))) entity.discard();
    }

    /** The GameTest framework logs only failures; this line lets the verifier see that every test of this class ran to its success call. */
    private static void done(GameTestHelper helper, String name) {
        LOGGER.info("{} {} passed", TAG, name);
        helper.succeed();
    }
}
