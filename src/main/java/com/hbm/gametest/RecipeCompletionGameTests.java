package com.hbm.gametest;

import com.hbm.blocks.NtmBlocks;
import com.hbm.config.NtmConfig;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.NtmCreativeTabs;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.RecipesCommon.TagStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.recipes.AssemblyMachineRecipes;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.inventory.recipes.loader.GenericRecipes;
import com.hbm.inventory.recipes.loader.GenericRecipes.ChanceOutput;
import com.hbm.inventory.recipes.loader.GenericRecipes.IOutput;
import com.hbm.items.CastPlateItem;
import com.hbm.items.NtmItems;
import com.hbm.items.RawIngotItem;
import com.hbm.items.WireDenseItem;
import com.hbm.items.machine.BlueprintFolderItem;
import com.hbm.items.machine.BlueprintsItem;
import com.hbm.main.NuclearTechMod;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.mojang.logging.LogUtils;
import net.minecraft.core.Holder;
import net.minecraft.core.NonNullList;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.ItemTags;
import net.minecraft.tags.TagKey;
import net.minecraft.world.item.CreativeModeTab;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.crafting.CraftingInput;
import net.minecraft.world.item.crafting.CraftingRecipe;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.RecipeType;
import net.neoforged.fml.ModList;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import org.slf4j.Logger;

import java.io.IOException;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal28C: the twenty-four assembly machine rows of the original 4f5924e2b that NEO lacked (the twelve metal plate rows
 * in the alt.plates pool and the autoswitch.plates group, the assembler, the alternative chemical plant, the pumpjack, the fracking tower, both
 * radars, the Leviathan turbine, the three overdrive upgrades, the naval mine and the empty fluid package), the fifteen crafting recipes (press
 * preheater, the five detonators, detonation cord, demolition charge, both mining charges, two landmines, the rangefinder and the slag block pair),
 * the four new item tags, the rangefinder item and the four new language keys. Same template and conventions as {@link OverworldWorldgenGameTests};
 * every test has its own batch.
 * <p>
 * Expected values come from the ORIGINAL at 4f5924e2b, cited beside each group of checks (AssemblyMachineRecipes.java:63-79,262-263,267-268,
 * 301-308,392-397,437-439,629-637,652-653,1110-1111; CraftingManager.java:319-323,520-524,852; WeaponRecipes.java:297-300; ToolRecipes.java:104;
 * MineralRecipes.java:58,455-458,486-505; OreDictManager.java:305,311,313,380,409,501-503; ItemCircuit.java:46-68; Mats.java:60,76,169;
 * ModItems.java:3388; en_US.lang:200,4163,5894,5895; zh_CN.lang:5066,5067,5887,5923), mapped to NEO through the documented Goal28C mapping
 * (build/migration/goal28c/handoff-builder.md): EnumCircuitType BASIC / ADVANCED / CAPACITOR / CAPACITOR_BOARD / BISMOID are NEO's
 * circuit_integrated_board / circuit_military_grade_board / circuit_capacitor / circuit_capacitor_board / circuit_versatile_board (original
 * en_US.lang:2439-2445); IRON / GOLD.ingot() are c:ingots/iron, gold, CU.ingot() is ntm:ingots_copper; STEEL / CU.plate() are c:plates/steel, copper; the other
 * metal ingots, plates, pipes and shells without a NEO tag are the plain NEO items; STEEL.plateWelded() is the welded steel cast plate; the
 * ANY_* dictionaries are the ntm: tags. NEO-only expectations (the start rows of NEO's table, the creative tab position, the template file
 * format) are marked as such.
 * <p>
 * Real classes and state: AssemblyMachineRecipes.INSTANCE as the server loaded it (defaults, enable528 off), the static blueprint pools,
 * BlueprintFolderItem.getPools, the GenericRecipes template writer and reader, the server RecipeManager with real CraftingInput grids, the
 * item registry and its tags, the MISSILE and NUKE creative tabs and the mod file's language resources. Substitutes: the template round trip writes to a
 * temporary file under the game directory (not the recipe config directory) and restores the static blueprint pools afterwards.
 * Not evidence: a real client (JEI, the assembler GUI, rendering, the item model), a dedicated server with real players, saved worlds,
 * enable528 or expensive mode switched on, and 1.7.10 itself.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class RecipeCompletionGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-28c]";

    /** Original AssemblyMachineRecipes.java:66 (String autoPlate) and :67-79 (GenericRecipes.POOL_PREFIX_ALT + "plates"). */
    private static final String PLATE_POOL = "alt.plates";
    private static final String PLATE_GROUP = "autoswitch.plates";

    /** Original Mats.java:76 MAT_GOLD id 7900 (GOLD.wireDense() meta) and Mats.java:60,169 MAT_SLAG id _AS + 11 = 41. */
    private static final int GOLD_META = 7900;
    private static final int SLAG_META = 41;

    // ---------------------------------------------------------------- expected stacks and rows

    /** One expected AStack or output: an item with a meta (WILDCARD for any) or a tag, with a count. */
    private record Stack(String kind, String id, int meta, int count) {
        @Override
        public String toString() {
            return kind.equals("tag") ? count + "x#" + id : count + "x" + id + (meta == MetaHelper.WILDCARD_VALUE ? "" : "@" + meta);
        }
    }

    private static Stack it(String id, int count) { return new Stack("item", id, MetaHelper.WILDCARD_VALUE, count); }
    private static Stack mt(String id, int meta, int count) { return new Stack("item", id, meta, count); }
    private static Stack tg(String id, int count) { return new Stack("tag", id, 0, count); }

    /** One expected assembly row: duration, power, the single output (meta 0), the inputs in order, the blueprint pool and the auto switch group. */
    private record Row(String name, int duration, long power, String output, int outputCount, String pool, String group, List<Stack> inputs) { }

    private static Row row(String name, int duration, long power, String output, int outputCount, String pool, String group, Stack... inputs) {
        return new Row(name, duration, power, output, outputCount, pool, group, List.of(inputs));
    }

    private static int welded() { return CastPlateItem.Type.STEEL.ordinal(); }

    /** The 24 rows in the order the batch appends them (handoff-builder.md A1-A11). */
    private static List<Row> newRows() {
        return List.of(
                // AssemblyMachineRecipes.java:67-79: setup(60, 100), one plate from one ingot, pool alt.plates, group autoswitch.plates;
                // :77 ass.plateweaponsteel is not registered (NEO has no plate_weaponsteel)
                row("ass.plateiron", 60, 100, "hbmsntm:plate_iron", 1, PLATE_POOL, PLATE_GROUP, tg("c:ingots/iron", 1)),
                row("ass.plategold", 60, 100, "hbmsntm:plate_gold", 1, PLATE_POOL, PLATE_GROUP, tg("c:ingots/gold", 1)),
                row("ass.platetitanium", 60, 100, "hbmsntm:plate_titanium", 1, PLATE_POOL, PLATE_GROUP, it("hbmsntm:ingot_titanium", 1)),
                row("ass.platealu", 60, 100, "hbmsntm:plate_aluminium", 1, PLATE_POOL, PLATE_GROUP, it("hbmsntm:ingot_aluminium", 1)),
                row("ass.platesteel", 60, 100, "hbmsntm:plate_steel", 1, PLATE_POOL, PLATE_GROUP, it("hbmsntm:ingot_steel", 1)),
                row("ass.platelead", 60, 100, "hbmsntm:plate_lead", 1, PLATE_POOL, PLATE_GROUP, it("hbmsntm:ingot_lead", 1)),
                // CU.ingot() is ingotCopper (OreDictManager.java:380, ingot_copper): NEO decision, ntm:ingots_copper (vanilla + NEO ingot)
                row("ass.platecopper", 60, 100, "hbmsntm:plate_copper", 1, PLATE_POOL, PLATE_GROUP, tg("ntm:ingots_copper", 1)),
                row("ass.plateschrab", 60, 100, "hbmsntm:plate_schrabidium", 1, PLATE_POOL, PLATE_GROUP, it("hbmsntm:ingot_schrabidium", 1)),
                row("ass.platecmb", 60, 100, "hbmsntm:plate_combine_steel", 1, PLATE_POOL, PLATE_GROUP, it("hbmsntm:ingot_combine_steel", 1)),
                row("ass.plategunmetal", 60, 100, "hbmsntm:plate_gunmetal", 1, PLATE_POOL, PLATE_GROUP, it("hbmsntm:ingot_gunmetal", 1)),
                row("ass.platesaturnite", 60, 100, "hbmsntm:plate_saturnite", 1, PLATE_POOL, PLATE_GROUP, it("hbmsntm:ingot_saturnite", 1)),
                row("ass.platedura", 60, 100, "hbmsntm:plate_dura_steel", 1, PLATE_POOL, PLATE_GROUP, it("hbmsntm:ingot_dura_steel", 1)),
                // :262-263 ass.assembler
                row("ass.assembler", 200, 100, "hbmsntm:machine_assembly_machine", 1, null, null,
                        it("hbmsntm:ingot_steel", 4), tg("c:plates/copper", 4), it("hbmsntm:motor", 2), it("hbmsntm:circuit_integrated_board", 1)),
                // :267-268 ass.chemplantAlt (normal inputs)
                row("ass.chemplantAlt", 200, 100, "hbmsntm:machine_chemical_plant", 1, null, null,
                        it("hbmsntm:plate_dura_steel", 8), it("hbmsntm:pipe_copper", 4), it("hbmsntm:motor", 2), it("hbmsntm:circuit_integrated_board", 1)),
                // :301-304 ass.pumpjack and :305-308 ass.fracker (normal inputs; NEO decision: no setPools528, as ass.crackingtower)
                row("ass.pumpjack", 400, 100, "hbmsntm:machine_pumpjack", 1, null, null,
                        it("hbmsntm:plate_dura_steel", 8), mt("hbmsntm:cast_plate_welded", welded(), 8), it("hbmsntm:pipe_steel", 12),
                        it("hbmsntm:motor_desh", 1), it("hbmsntm:drill_titanium", 1)),
                row("ass.fracker", 600, 100, "hbmsntm:machine_fracking_tower", 1, null, null,
                        it("hbmsntm:shell_steel", 24), it("hbmsntm:pipe_steel", 12), it("hbmsntm:concrete_smooth", 64), it("hbmsntm:drill_titanium", 1),
                        it("hbmsntm:motor_desh", 2), it("hbmsntm:plate_desh", 24), it("hbmsntm:circuit_capacitor", 16)),
                // :392-394 ass.radar and :395-397 ass.radarlarge (normal inputs)
                row("ass.radar", 300, 100, "hbmsntm:machine_radar", 1, null, null,
                        tg("c:plates/steel", 12), tg("ntm:any_rubbers", 12), it("hbmsntm:magnetron", 5), it("hbmsntm:motor", 1),
                        it("hbmsntm:circuit_integrated_board", 8), it("hbmsntm:crt_display", 4)),
                row("ass.radarlarge", 400, 100, "hbmsntm:machine_radar_large", 1, null, null,
                        mt("hbmsntm:cast_plate_welded", welded(), 6), tg("ntm:ingots_resistant_alloy", 4), tg("ntm:any_rubbers", 24), it("hbmsntm:magnetron", 16),
                        it("hbmsntm:motor_desh", 1), it("hbmsntm:circuit_military_grade_board", 4), it("hbmsntm:crt_display", 4)),
                // :437-439 ass.leviturbine (normal inputs)
                row("ass.leviturbine", 600, 100, "hbmsntm:machine_chungus", 1, null, null,
                        it("hbmsntm:shell_steel", 6), mt("hbmsntm:cast_plate_welded", welded(), 16), it("hbmsntm:plate_titanium", 12), tg("ntm:ingots_resistant_alloy", 16),
                        it("hbmsntm:turbine_tungsten", 5), it("hbmsntm:turbine_titanium", 3), it("hbmsntm:flywheel_beryllium", 1), mt("hbmsntm:wire_dense", GOLD_META, 48),
                        it("hbmsntm:pipe_dura_steel", 16), it("hbmsntm:pipe_steel", 16)),
                // :629-637 the overdrive upgrades, inside if(no528)
                row("ass.overdrive1", 200, 100, "hbmsntm:upgrade_overdrive_1", 1, null, null,
                        it("hbmsntm:upgrade_speed_3", 1), it("hbmsntm:upgrade_effect_3", 1), it("hbmsntm:ingot_saturnite", 16), tg("ntm:bars_hard_plastic", 16),
                        it("hbmsntm:circuit_military_grade_board", 16)),
                row("ass.overdrive2", 600, 100, "hbmsntm:upgrade_overdrive_2", 1, null, null,
                        it("hbmsntm:upgrade_overdrive_1", 1), it("hbmsntm:upgrade_speed_3", 1), it("hbmsntm:upgrade_effect_3", 1), it("hbmsntm:ingot_saturnite", 16),
                        it("hbmsntm:ingot_cft", 8), it("hbmsntm:circuit_capacitor_board", 16)),
                row("ass.overdrive3", 1200, 100, "hbmsntm:upgrade_overdrive_3", 1, null, null,
                        it("hbmsntm:upgrade_overdrive_2", 1), it("hbmsntm:upgrade_speed_3", 1), it("hbmsntm:upgrade_effect_3", 1), tg("ntm:ingots_bismoid_bronze", 16),
                        it("hbmsntm:ingot_cft", 16), it("hbmsntm:circuit_versatile_board", 16)),
                // :652-653 ass.minenaval
                row("ass.minenaval", 300, 100, "hbmsntm:mine_naval", 1, null, null,
                        it("hbmsntm:sphere_steel", 1), it("hbmsntm:pipe_steel", 3), it("hbmsntm:circuit_military_grade_board", 1), tg("ntm:ingots_plastic_explosive", 24)),
                // :1110-1111 ass.emptypackage
                row("ass.emptypackage", 40, 100, "hbmsntm:fluid_pack_empty", 1, null, null,
                        it("hbmsntm:plate_titanium", 4), tg("ntm:ingots_plastic", 2)));
    }

    // NEO-only: the 58 fixed rows of NEO's table at the 28C start (build/migration/goal28c/baseline-files/.../AssemblyMachineRecipes.java), in
    // registration order around the fluid package loop (:243-251); with enable528 off all of them are registered.
    private static final List<String> START_BEFORE_LOOP = List.of("ass.boytarget", "ass.machine_refinery", "ass.drill_titanium", "ass.machine_oil_derrick",
            "ass.missileassembly", "ass.warheadhe1", "ass.warheadhe2", "ass.warheadhe3", "ass.warheadinc1", "ass.warheadinc2", "ass.warheadinc3", "ass.warheadcl1",
            "ass.warheadcl2", "ass.warheadcl3", "ass.warheadbb1", "ass.warheadbb2", "ass.warheadbb3", "ass.warheadnuke", "ass.warheadthermonuke", "ass.warheadvolcano",
            "ass.plate_desh", "ass.plate_bismuth", "ass.magnetron", "ass.pellet_cluster", "ass.plate_dalek", "ass.man");
    private static final List<String> START_AFTER_LOOP = List.of("ass.shredder", "ass.compressor", "ass.coker", "ass.centrifugetower", "ass.centrifuge",
            "ass.thermoelement", "ass.thermoelementsilicon", "ass.rtgunit", "ass.gascent", "ass.turbofan", "ass.combustiongen", "ass.pistonsetsteel", "ass.pistonsetdura",
            "ass.pistonsetdesh", "ass.dieselgen", "ass.rtg", "ass.tank", "ass.chemplant", "ass.purex", "ass.crackingtower", "ass.chip", "ass.analogAlt",
            "ass.factorioChip", "ass.atomicClockAlt", "ass.arcfurnace", "ass.acidizer", "ass.iturbine", "ass.cirnox", "ass.rbmk", "ass.rbmkautoloader",
            "ass.filtercoal", "ass.hazcloth");

    /** NEO-only: a sample of eleven start rows, their inputs and outputs as in the start text (lines cited), which the batch must not change. */
    private static List<Row> startSample() {
        return List.of(
                row("ass.boytarget", 200, 100, "hbmsntm:little_boy_target", 1, null, null, it("hbmsntm:ingot_uranium", 18)),  // :40-41
                row("ass.machine_refinery", 200, 100, "hbmsntm:machine_refinery", 1, null, null,  // :43-52 (INSULATOR is plate_polymer)
                        it("hbmsntm:plate_copper", 8), it("hbmsntm:shell_steel", 4), it("hbmsntm:pipe_steel", 12), it("hbmsntm:plate_polymer", 8),
                        it("hbmsntm:circuit_analog_board", 3), mt("hbmsntm:cast_plate_welded", welded(), 3)),
                row("ass.shredder", 100, 100, "hbmsntm:machine_shredder", 1, null, null,  // :253-256
                        tg("c:plates/steel", 8), tg("c:plates/copper", 4), it("hbmsntm:motor", 2)),
                row("ass.gascent", 400, 100, "hbmsntm:machine_gas_centrifuge", 1, null, null,  // :302-307
                        it("hbmsntm:centrifuge_element", 4), tg("ntm:ingots_plastic", 8), it("hbmsntm:ingot_desh", 2), tg("c:plates/steel", 8),
                        it("hbmsntm:circuit_military_grade_board", 1)),
                row("ass.turbofan", 300, 100, "hbmsntm:machine_turbofan", 1, null, null,  // :310-316
                        it("hbmsntm:shell_titanium", 8), it("hbmsntm:pipe_dura_steel", 4), tg("ntm:ingots_plastic", 12), it("hbmsntm:turbine_tungsten", 1),
                        mt("hbmsntm:wire_dense", GOLD_META, 12), it("hbmsntm:circuit_integrated_board", 3)),
                row("ass.chemplant", 200, 100, "hbmsntm:machine_chemical_plant", 1, null, null,  // :358-364
                        it("hbmsntm:ingot_steel", 8), it("hbmsntm:pipe_copper", 2), it("hbmsntm:plate_polymer", 16), it("hbmsntm:motor", 2),
                        it("hbmsntm:coil_tungsten", 2), it("hbmsntm:circuit_analog_board", 1)),
                row("ass.purex", 300, 100, "hbmsntm:machine_purex", 1, null, null,  // :367-372
                        it("hbmsntm:shell_steel", 4), it("hbmsntm:pipe_rubber", 8), mt("hbmsntm:cast_plate", CastPlateItem.Type.LEAD.ordinal(), 4),
                        it("hbmsntm:motor_desh", 1), it("hbmsntm:circuit_integrated_board", 4)),
                row("ass.analogAlt", 200, 250, "hbmsntm:circuit_analog_board", 1, "alt..circuit", null,  // :396-401
                        it("hbmsntm:circuit_printed_board", 4), tg("ntm:ingots_plastic", 4), it("hbmsntm:wire_tungsten", 8), it("hbmsntm:ingot_niobium", 1)),
                row("ass.rbmk", 100, 100, "hbmsntm:rbmk_blank", 1, null, null,  // :461-465
                        it("hbmsntm:concrete_asbestos", 4), mt("hbmsntm:cast_plate", CastPlateItem.Type.STEEL.ordinal(), 2), it("hbmsntm:plate_copper", 4),
                        it("hbmsntm:ingot_rubber", 2)),
                row("ass.filtercoal", 50, 100, "hbmsntm:filter_coal", 1, null, null,  // :476-479
                        it("hbmsntm:powder_coal", 4), it("minecraft:string", 2), it("minecraft:paper", 1)),
                row("ass.hazcloth", 50, 100, "hbmsntm:hazmat_cloth", 4, null, null,  // :482-484
                        it("hbmsntm:powder_lead", 4), it("minecraft:string", 8)));
    }

    // ---------------------------------------------------------------- 1. assembly machine rows

    @GameTest(template = TEMPLATE, batch = "hbm28c_assembler_rows", timeoutTicks = 100)
    public static void assembler_rows(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    check(!NtmConfig.enable528(), "enable528 is on; these expectations are the original's no528 branch (AssemblyMachineRecipes.java:63,630)");
                    AssemblyMachineRecipes set = AssemblyMachineRecipes.INSTANCE;

                    // the 24 rows: duration, power, output, every input, pool and group
                    List<Row> want = newRows();
                    check(want.size() == 24, "the expected table has " + want.size() + " rows");
                    for(Row r : want) assertRow(set, r);

                    // welded steel plate by its META component, dense gold wire by meta (AssemblyMachineRecipes.java:302,396,438: STEEL.plateWelded(), GOLD.wireDense())
                    ItemStack weldedSteel = MetaHelper.newStack(NtmItems.CAST_PLATE_WELDED.get(), 64, CastPlateItem.Type.STEEL.ordinal());
                    ItemStack weldedCopper = MetaHelper.newStack(NtmItems.CAST_PLATE_WELDED.get(), 64, CastPlateItem.Type.COPPER.ordinal());
                    ItemStack goldWire = MetaHelper.newStack(NtmItems.WIRE_DENSE.get(), 64, GOLD_META);
                    ItemStack copperWire = MetaHelper.newStack(NtmItems.WIRE_DENSE.get(), 64, WireDenseItem.Type.COPPER.meta);
                    check(WireDenseItem.Type.GOLD.meta == GOLD_META, "WireDenseItem GOLD meta is " + WireDenseItem.Type.GOLD.meta + ", the original MAT_GOLD id is 7900");
                    int weldedInputs = 0, wireInputs = 0;
                    for(String name : List.of("ass.pumpjack", "ass.radarlarge", "ass.leviturbine")) {
                        for(AStack a : set.recipeNameMap.get(name).inputItem) {
                            if(!(a instanceof ComparableStack c)) continue;
                            if(c.item == NtmItems.CAST_PLATE_WELDED.get()) {
                                check(MetaHelper.getMeta(c.toStack()) == CastPlateItem.Type.STEEL.ordinal() && c.matchesRecipe(weldedSteel, false) && !c.matchesRecipe(weldedCopper, true),
                                        name + ": the welded plate input " + c.toStack() + " is not the welded steel plate only");
                                weldedInputs++;
                            }
                            if(c.item == NtmItems.WIRE_DENSE.get()) {
                                check(c.matchesRecipe(goldWire, false) && !c.matchesRecipe(copperWire, true), name + ": the dense wire input is not gold only");
                                wireInputs++;
                            }
                        }
                    }
                    check(weldedInputs == 3 && wireInputs == 1, "welded plate inputs " + weldedInputs + " (expected 3), dense gold wire inputs " + wireInputs + " (expected 1)");

                    // tag inputs accept every member of their tag (OreDictStack: any item of the dictionary entry)
                    int tagMembers = 0;
                    for(Row r : want) for(AStack a : set.recipeNameMap.get(r.name()).inputItem) {
                        if(!(a instanceof TagStack t)) continue;
                        List<Item> members = members(t.tag);
                        check(!members.isEmpty(), r.name() + ": the tag " + t.tag.location() + " is empty");
                        for(Item m : members) {
                            check(t.matchesRecipe(new ItemStack(m, t.stacksize), false), r.name() + ": " + key(m) + " of #" + t.tag.location() + " is not accepted");
                            tagMembers++;
                        }
                    }
                    // CU.ingot() holds ingot_copper (OreDictManager.java:380): NEO's own ingot_copper and the vanilla copper ingot both make the copper plate
                    AStack copperIngot = set.recipeNameMap.get("ass.platecopper").inputItem[0];
                    check(copperIngot.matchesRecipe(new ItemStack(NtmItems.INGOT_COPPER.get()), false) && copperIngot.matchesRecipe(new ItemStack(Items.COPPER_INGOT), false),
                            "ass.platecopper: NEO's ingot_copper and the vanilla copper ingot must both match");

                    // the auto switch group holds exactly the twelve plate rows, in order (setGroup(autoPlate, this) on :67-79 except :77)
                    List<GenericRecipe> group = set.autoSwitchGroups.get(PLATE_GROUP);
                    List<GenericRecipe> plates = new ArrayList<>();
                    for(Row r : want) if(PLATE_GROUP.equals(r.group())) plates.add(set.recipeNameMap.get(r.name()));
                    check(plates.size() == 12, plates.size() + " plate rows expected in the group, want 12");
                    check(group != null && group.equals(plates), "autoSwitchGroups[autoswitch.plates] is " + names(group) + ", expected " + names(plates));
                    check(!set.recipeNameMap.containsKey("ass.plateweaponsteel"),
                            "ass.plateweaponsteel is registered (not part of the batch)");

                    // :301-308 NEO decision: the pumpjack and the fracker carry no pool (no setPools528), and no 528. pool exists with enable528 off
                    for(String name : List.of("ass.pumpjack", "ass.fracker")) {
                        GenericRecipe r = set.recipeNameMap.get(name);
                        check(r.getPools() == null && !r.isPooled(), name + " has pools " + Arrays.toString(r.getPools()));
                    }
                    for(String pool : GenericRecipes.blueprintPools.keySet()) check(!pool.startsWith(GenericRecipes.POOL_PREFIX_528), "the pool " + pool + " exists with enable528 off");
                    // :630-637 the overdrive rows exist with enable528 off
                    for(String name : List.of("ass.overdrive1", "ass.overdrive2", "ass.overdrive3")) check(set.recipeNameMap.containsKey(name), name + " is missing");

                    // NEO-only: the start rows unchanged, the 24 rows appended after them
                    List<String> loop = new ArrayList<>();
                    FluidType[] order = Fluids.getInNiceOrder();
                    for(int i = 1; i < order.length; ++i) {
                        if(order[i].hasNoContainer()) continue;
                        loop.add("ass.package" + order[i].getUnlocalizedName());
                        loop.add("ass.unpackage" + order[i].getUnlocalizedName());
                    }
                    List<String> start = new ArrayList<>(START_BEFORE_LOOP);
                    start.addAll(loop);
                    start.addAll(START_AFTER_LOOP);
                    check(START_BEFORE_LOOP.size() + START_AFTER_LOOP.size() == 58, "the start list has " + (START_BEFORE_LOOP.size() + START_AFTER_LOOP.size()) + " fixed rows, expected 58");
                    List<String> live = names(set.recipeOrderedList);
                    check(live.size() == start.size() + 27 && set.recipeNameMap.size() == start.size() + 27,
                            "the table has " + live.size() + " ordered and " + set.recipeNameMap.size() + " named rows, expected " + start.size() + " (58 fixed + " + loop.size() + " package rows) + 24 + 3");
                    check(live.subList(0, start.size()).equals(start), "the first " + start.size() + " rows are not the start rows in order: " + firstDifference(live, start));
                    List<String> appended = new ArrayList<>();
                    for(Row r : want) appended.add(r.name());
                    check(live.subList(start.size(), start.size() + appended.size()).equals(appended), "the appended rows are " + live.subList(start.size(), start.size() + appended.size()) + ", expected " + appended);
                    check(live.subList(start.size() + appended.size(), live.size()).equals(List.of("ass.platemixed", "ass.vaccumrefinery", "ass.chipBismoid")), "the last rows are " + live.subList(start.size() + appended.size(), live.size()));

                    List<Row> sample = startSample();
                    for(Row r : sample) assertRow(set, r);
                    int packages = 0;
                    for(int i = 1; i < order.length; ++i) {
                        FluidType type = order[i];
                        if(type.hasNoContainer()) continue;
                        // start :247-250: package = empty pack + 32000 mB -> full pack (meta = fluid id); unpackage the reverse, with the fluid icon
                        GenericRecipe pack = set.recipeNameMap.get("ass.package" + type.getUnlocalizedName());
                        GenericRecipe unpack = set.recipeNameMap.get("ass.unpackage" + type.getUnlocalizedName());
                        check(pack.duration == 40 && pack.power == 100 && unpack.duration == 40 && unpack.power == 100, type.getName() + " package timings changed");
                        check(inputs(pack).equals(List.of(it("hbmsntm:fluid_pack_empty", 1))) && output(pack).equals(mt("hbmsntm:fluid_pack_full", type.getID(), 1))
                                        && fluids(pack.inputFluid).equals(List.of(type.getName() + " 32000 0")) && pack.outputFluid == null,
                                "ass.package" + type.getUnlocalizedName() + " changed: " + describe(pack));
                        check(inputs(unpack).equals(List.of(mt("hbmsntm:fluid_pack_full", type.getID(), 1))) && output(unpack).equals(mt("hbmsntm:fluid_pack_empty", 0, 1))
                                        && fluids(unpack.outputFluid).equals(List.of(type.getName() + " 32000 0")) && unpack.inputFluid == null && unpack.writeIcon,
                                "ass.unpackage" + type.getUnlocalizedName() + " changed: " + describe(unpack));
                        packages++;
                    }
                    check(packages * 2 == loop.size() && packages > 0, packages + " package fluids checked");
                    LOGGER.info("{} assembler_rows: 24 rows equal to the original table, {} tag members accepted, autoswitch.plates = 12 rows, no 528. pool, "
                                    + "table {} = {} start ({} fixed + {} package rows) + 24; {} sampled start rows and {} package pairs unchanged",
                            TAG, tagMembers, live.size(), start.size(), 58, loop.size(), sample.size(), packages);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "assembler_rows"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 2. blueprint pools

    // AssemblyMachineRecipes.java:67-79 setPools(POOL_PREFIX_ALT + "plates"); ItemBlueprintFolder draws the alt. pools for meta 0 (NEO
    // BlueprintFolderItem.getPools); ItemBlueprints icon: 528. pools are grey, alt. pools the base blue (NEO BlueprintsItem.getModelType)
    @GameTest(template = TEMPLATE, batch = "hbm28c_blueprint_pools", timeoutTicks = 100)
    public static void blueprint_pools(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    List<String> plateNames = new ArrayList<>();
                    for(Row r : newRows()) if(PLATE_POOL.equals(r.pool())) plateNames.add(r.name());
                    check(plateNames.size() == 12, plateNames.size() + " plate rows");
                    List<String> pool = GenericRecipes.blueprintPools.get(PLATE_POOL);
                    check(plateNames.equals(pool), "blueprintPools[alt.plates] is " + pool + ", expected " + plateNames);
                    for(String name : plateNames) {
                        check(GenericRecipes.pooledBlueprints.get(name) == AssemblyMachineRecipes.INSTANCE.recipeNameMap.get(name), name + " is not the pooled blueprint recipe");
                        check(AssemblyMachineRecipes.INSTANCE.recipeNameMap.get(name).isPartOfPool(PLATE_POOL), name + " is not part of alt.plates");
                    }
                    List<String> alt = BlueprintFolderItem.getPools(BlueprintFolderItem.Type.ALT.ordinal());
                    List<String> discover = BlueprintFolderItem.getPools(BlueprintFolderItem.Type.DISCOVER.ordinal());
                    List<String> secret = BlueprintFolderItem.getPools(BlueprintFolderItem.Type.SECRET.ordinal());
                    check(alt.contains(PLATE_POOL), "the alt. blueprint folder draws " + alt + ", without alt.plates");
                    check(!discover.contains(PLATE_POOL) && !secret.contains(PLATE_POOL), "alt.plates is drawn by the discover or secret folder");
                    // regression: the start's alt..circuit pool is still drawn by the alt. folder
                    check(alt.contains("alt..circuit"), "the alt. folder lost alt..circuit: " + alt);
                    check(!PLATE_POOL.startsWith(GenericRecipes.POOL_PREFIX_528), "alt.plates has the 528. prefix");
                    List<String> pools528 = GenericRecipes.blueprintPools.keySet().stream().filter(p -> p.startsWith(GenericRecipes.POOL_PREFIX_528)).sorted().collect(Collectors.toList());
                    check(pools528.isEmpty(), "528. pools exist with enable528 off: " + pools528);
                    ItemStack blueprint = BlueprintsItem.make(PLATE_POOL);
                    check(PLATE_POOL.equals(BlueprintsItem.grabPool(blueprint)), "the alt.plates blueprint holds " + BlueprintsItem.grabPool(blueprint));
                    check(BlueprintsItem.getModelType(blueprint) == 0F && BlueprintsItem.getModelType(blueprint) != BlueprintsItem.MODEL_528,
                            "the alt.plates blueprint model is " + BlueprintsItem.getModelType(blueprint) + ", expected the base 0 (not 528 grey)");
                    LOGGER.info("{} blueprint_pools: alt.plates = {} rows, alt. folder pools {}, discover {}, secret {}, 528. pools none", TAG, pool.size(), alt, discover, secret);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "blueprint_pools"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 3. template round trip

    // GenericRecipes.writeRecipe / readRecipe (original GenericRecipes "blueprintpool" and "autoSwitchGroup" fields): the whole table through
    // the template writer into a temporary file and back into a fresh AssemblyMachineRecipes
    @GameTest(template = TEMPLATE, batch = "hbm28c_template_roundtrip", timeoutTicks = 200)
    public static void template_roundtrip(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    AssemblyMachineRecipes live = AssemblyMachineRecipes.INSTANCE;
                    Map<String, List<String>> poolsBackup = new HashMap<>();
                    for(Map.Entry<String, List<String>> e : GenericRecipes.blueprintPools.entrySet()) poolsBackup.put(e.getKey(), new ArrayList<>(e.getValue()));
                    Map<String, GenericRecipe> pooledBackup = new HashMap<>(GenericRecipes.pooledBlueprints);
                    Path dir = FMLPaths.GAMEDIR.get().resolve("hbm28c-gametest");
                    Path file = null;
                    try {
                        Files.createDirectories(dir);
                        file = Files.createTempFile(dir, "assembler-roundtrip", ".json");
                        live.writeTemplateFile(file.toFile());
                        String text = Files.readString(file, StandardCharsets.UTF_8);
                        check(text.contains("\"recipes\"") && text.contains("\"ass.plateiron\""), "the template file has no recipes (" + text.length() + " chars)");
                        check(text.contains("\"blueprintpool\": \"alt.plates\"") && text.contains("\"autoSwitchGroup\": \"autoswitch.plates\""), "the template file lacks the plate pool or group");

                        AssemblyMachineRecipes fresh = new AssemblyMachineRecipes();
                        check(fresh.readRecipeFile(file.toFile()), "the template file could not be read back");
                        check(fresh.recipeOrderedList.size() == live.recipeOrderedList.size() && fresh.recipeNameMap.size() == live.recipeNameMap.size(),
                                "read back " + fresh.recipeOrderedList.size() + " rows, written " + live.recipeOrderedList.size());
                        List<String> differ = new ArrayList<>();
                        for(int i = 0; i < live.recipeOrderedList.size(); i++) {
                            String a = describe(live.recipeOrderedList.get(i)), b = describe(fresh.recipeOrderedList.get(i));
                            if(!a.equals(b)) differ.add(a + " -> " + b);
                        }
                        check(differ.isEmpty(), differ.size() + " rows differ after the round trip, first: " + (differ.isEmpty() ? "" : differ.get(0)));
                        int plates = 0;
                        for(Row r : newRows()) {
                            GenericRecipe back = fresh.recipeNameMap.get(r.name());
                            check(back != null, r.name() + " was not read back");
                            if(r.pool() == null) {
                                check(back.getPools() == null && back.autoSwitchGroup == null, r.name() + " read back with pools " + Arrays.toString(back.getPools()) + " / group " + back.autoSwitchGroup);
                                continue;
                            }
                            check(Arrays.equals(back.getPools(), new String[] { PLATE_POOL }) && PLATE_GROUP.equals(back.autoSwitchGroup),
                                    r.name() + " read back with pools " + Arrays.toString(back.getPools()) + " and group " + back.autoSwitchGroup);
                            plates++;
                        }
                        List<GenericRecipe> group = fresh.autoSwitchGroups.get(PLATE_GROUP);
                        check(plates == 12 && group != null && names(group).equals(names(live.autoSwitchGroups.get(PLATE_GROUP))),
                                "the read-back autoswitch.plates group is " + names(group));
                        LOGGER.info("{} template_roundtrip: {} rows written ({} chars) and read back equal; 12 plate rows keep alt.plates / autoswitch.plates", TAG,
                                fresh.recipeOrderedList.size(), text.length());
                    } catch(IOException e) {
                        throw new IllegalStateException(e);
                    } finally {
                        // the reader's setPoolsAllow528 adds the read rows to the static pools; restore the server's pools
                        GenericRecipes.blueprintPools.clear();
                        GenericRecipes.blueprintPools.putAll(poolsBackup);
                        GenericRecipes.pooledBlueprints.clear();
                        GenericRecipes.pooledBlueprints.putAll(pooledBackup);
                        try {
                            if(file != null) Files.deleteIfExists(file);
                            Files.deleteIfExists(dir);
                        } catch(IOException ignored) { }
                    }
                    check(GenericRecipes.pooledBlueprints.get("ass.plateiron") == live.recipeNameMap.get("ass.plateiron"), "the pools were not restored");
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "template_roundtrip"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 4. crafting recipes

    /** One expected crafting recipe: id, result (item[@meta]) and count, the grid; "#tag" keys are tags; the one-ingredient-wrong grid. */
    private record Craft(String id, String result, int count, String[] pattern, Map<Character, String> key, List<String> shapeless, int wrongIndex, String wrong) { }

    private static Craft shaped(String id, String result, int count, String[] pattern, Map<Character, String> key, char wrongKey, String wrong) {
        return new Craft(id, result, count, pattern, key, null, wrongKey, wrong);
    }

    private static Craft shapeless(String id, String result, int count, List<String> ingredients, int wrongIndex, String wrong) {
        return new Craft(id, result, count, null, null, ingredients, wrongIndex, wrong);
    }

    private static Map<Character, String> keys(Object... pairs) {
        Map<Character, String> map = new LinkedHashMap<>();
        for(int i = 0; i < pairs.length; i += 2) map.put((Character) pairs[i], (String) pairs[i + 1]);
        return map;
    }

    private static List<Craft> crafts() {
        return List.of(
                // CraftingManager.java:852: CU.plate(), Blocks.stone, Fluids.LAVA.getDict(1000) (the lava bucket), W.ingot()
                shaped("press_preheater", "hbmsntm:press_preheater", 1, new String[] { "CCC", "SLS", "TST" },
                        keys('C', "#c:plates/copper", 'S', "minecraft:stone", 'L', "minecraft:lava_bucket", 'T', "hbmsntm:ingot_tungsten"), 'T', "hbmsntm:ingot_steel"),
                // CraftingManager.java:319-323 (BASIC = integrated board, ADVANCED = military grade board, RUBBER.ingot() = the rubber ingot only, GOLD.wireDense())
                shaped("detonator", "hbmsntm:detonator", 1, new String[] { "C", "S" },
                        keys('C', "hbmsntm:circuit_integrated_board", 'S', "#c:plates/steel"), 'S', "hbmsntm:plate_iron"),
                shapeless("detonator_multi", "hbmsntm:detonator_multi", 1, List.of("hbmsntm:detonator", "hbmsntm:circuit_military_grade_board"), 1, "hbmsntm:circuit_integrated_board"),
                shapeless("detonator_laser", "hbmsntm:detonator_laser", 1,
                        List.of("hbmsntm:rangefinder", "hbmsntm:circuit_military_grade_board", "hbmsntm:ingot_rubber", "hbmsntm:wire_dense@" + GOLD_META), 3, "hbmsntm:wire_dense@2900"),
                shapeless("detonator_deadman", "hbmsntm:detonator_deadman", 1, List.of("hbmsntm:detonator", "hbmsntm:defuser", "hbmsntm:ducttape"), 1, "minecraft:stick"),
                shaped("detonator_de", "hbmsntm:detonator_de", 1, new String[] { "T", "D", "T" },
                        keys('T', "minecraft:tnt", 'D', "hbmsntm:detonator_deadman"), 'D', "hbmsntm:detonator"),
                // CraftingManager.java:520-524 (det_nuke :522 is not registered)
                shaped("det_cord", "hbmsntm:det_cord", 4, new String[] { " P ", "PGP", " P " },
                        keys('P', "minecraft:paper", 'G', "minecraft:gunpowder"), 'G', "minecraft:redstone"),
                shaped("det_charge", "hbmsntm:det_charge", 1, new String[] { "PDP", "DTD", "PDP" },
                        keys('P', "#c:plates/steel", 'D', "hbmsntm:det_cord", 'T', "#ntm:ingots_plastic_explosive"), 'T', "hbmsntm:ball_tnt"),
                shaped("det_miner", "hbmsntm:det_miner", 4, new String[] { "FFF", "ITI", "ITI" },
                        keys('F', "minecraft:flint", 'I', "hbmsntm:plate_iron", 'T', "hbmsntm:ball_dynamite"), 'T', "hbmsntm:ingot_semtex"),
                shaped("det_miner_steel", "hbmsntm:det_miner", 12, new String[] { "FFF", "ITI", "ITI" },
                        keys('F', "minecraft:flint", 'I', "#c:plates/steel", 'T', "#ntm:ingots_plastic_explosive"), 'T', "hbmsntm:ball_dynamite"),
                // WeaponRecipes.java:297,299 (ANY_SMOKELESS.dust() = ballistite or cordite, NEO has cordite; ANY_HIGHEXPLOSIVE = TNT / TATB ball;
                // mine_shrap :298 and mine_fat :300 are not registered)
                shaped("mine_ap", "hbmsntm:mine_ap", 4, new String[] { "I", "C", "S" },
                        keys('I', "hbmsntm:plate_polymer", 'C', "hbmsntm:cordite", 'S', "hbmsntm:ingot_steel"), 'C', "minecraft:gunpowder"),
                shaped("mine_he", "hbmsntm:mine_he", 1, new String[] { " C ", "PTP" },
                        keys('C', "hbmsntm:circuit_integrated_board", 'P', "#c:plates/steel", 'T', "#ntm:balls_he"), 'T', "hbmsntm:ingot_semtex"),
                // ToolRecipes.java:104 (KEY_ANYPANE, REDSTONE.dust(), BASIC, STEEL.plate())
                shaped("rangefinder", "hbmsntm:rangefinder", 1, new String[] { "GRC", "  S" },
                        keys('G', "#c:glass_panes", 'R', "minecraft:redstone", 'C', "hbmsntm:circuit_integrated_board", 'S', "#c:plates/steel"), 'G', "minecraft:glass"),
                // MineralRecipes.java:58 add1To9Pair(block_slag, ingot_raw x9 MAT_SLAG.id): :504 "###" x3 of the slag ingot, :487 one block to nine
                shaped("block_slag", "hbmsntm:block_slag", 1, new String[] { "###", "###", "###" },
                        keys('#', "hbmsntm:ingot_raw@" + SLAG_META), '#', "hbmsntm:ingot_raw@40"),
                shapeless("ingot_raw_slag", "hbmsntm:ingot_raw@" + SLAG_META, 9, List.of("hbmsntm:block_slag"), 0, "minecraft:stone"));
    }

    @GameTest(template = TEMPLATE, batch = "hbm28c_crafting_recipes", timeoutTicks = 100)
    public static void crafting_recipes(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ServerLevel level = helper.getLevel();
                    check(RawIngotItem.Type.SLAG.meta == SLAG_META, "RawIngotItem SLAG meta is " + RawIngotItem.Type.SLAG.meta + ", the original MAT_SLAG id is 41");
                    List<Craft> list = crafts();
                    check(list.size() == 15, list.size() + " crafting recipes expected, want 15");
                    int memberGrids = 0;
                    for(Craft c : list) {
                        ResourceLocation id = ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, c.id());
                        check(level.getRecipeManager().byKey(id).isPresent(), "recipe " + id + " is not loaded");
                        CraftingInput exact = grid(c, -1, null);
                        ItemStack result = only(level, id, exact, c.id() + " exact");
                        check(result.is(item(c.result())) && result.getCount() == c.count() && MetaHelper.getMeta(result) == meta(c.result(), 0),
                                c.id() + " yields " + result + " meta " + MetaHelper.getMeta(result) + ", expected " + c.count() + " x " + c.result());
                        CraftingInput wrong = grid(c, c.wrongIndex(), c.wrong());
                        RecipeHolder<?> holder = level.getRecipeManager().byKey(id).get();
                        check(!((CraftingRecipe) holder.value()).matches(wrong, level), c.id() + " still matches with " + c.wrong() + " in place of ingredient " + c.wrongIndex());
                        check(level.getRecipeManager().getRecipeFor(RecipeType.CRAFTING, wrong, level).map(h -> !h.id().equals(id)).orElse(true), c.id() + " is the first match for the wrong grid");
                        // every member of a tag ingredient is accepted
                        if(c.key() != null) for(Map.Entry<Character, String> e : c.key().entrySet()) {
                            if(!e.getValue().startsWith("#")) continue;
                            List<Item> members = members(ItemTags.create(ResourceLocation.parse(e.getValue().substring(1))));
                            check(!members.isEmpty(), c.id() + ": " + e.getValue() + " is empty");
                            for(Item m : members) {
                                ItemStack r = only(level, id, grid(c, e.getKey(), key(m), true), c.id() + " with " + key(m) + " for " + e.getKey());
                                check(r.is(item(c.result())) && r.getCount() == c.count(), c.id() + " with " + key(m) + " yields " + r);
                                memberGrids++;
                            }
                        }
                    }

                    // CraftingManager.java:852 Fluids.LAVA.getDict(1000): the lava bucket's crafting remainder leaves the empty bucket in its cell
                    Craft preheater = list.get(0);
                    CraftingRecipe recipe = (CraftingRecipe) level.getRecipeManager().byKey(ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, "press_preheater")).get().value();
                    NonNullList<ItemStack> remaining = recipe.getRemainingItems(grid(preheater, -1, null));
                    for(int i = 0; i < remaining.size(); i++) {
                        boolean lava = i == 4;
                        check(lava ? remaining.get(i).is(Items.BUCKET) && remaining.get(i).getCount() == 1 : remaining.get(i).isEmpty(),
                                "press_preheater leaves " + remaining.get(i) + " in cell " + i + (lava ? ", expected the empty bucket" : ", expected nothing"));
                    }
                    // RUBBER.ingot() is the rubber ingot only (OreDictManager.java:409): bio rubber does not make the laser detonator
                    Craft laser = list.get(3);
                    CraftingInput bio = grid(laser, 2, "hbmsntm:ingot_biorubber");
                    check(level.getRecipeManager().getRecipeFor(RecipeType.CRAFTING, bio, level).map(h -> !h.id().getPath().equals("detonator_laser")).orElse(true),
                            "detonator_laser accepts bio rubber");

                    // no other crafting recipe makes these results (the items had no recipe at the start); the slag ingot only from ingot_raw_slag
                    Map<String, Set<String>> producers = new LinkedHashMap<>();
                    for(Craft c : list) producers.computeIfAbsent(c.result(), k -> new LinkedHashSet<>());
                    for(RecipeHolder<CraftingRecipe> h : level.getRecipeManager().getAllRecipesFor(RecipeType.CRAFTING)) {
                        ItemStack out = h.value().getResultItem(level.registryAccess());
                        if(out.isEmpty()) continue;
                        String desc = key(out.getItem()) + (out.is(NtmItems.INGOT_RAW.get()) ? "@" + MetaHelper.getMeta(out) : "");
                        if(producers.containsKey(desc)) producers.get(desc).add(h.id().getPath());
                    }
                    Map<String, Set<String>> wantProducers = new LinkedHashMap<>();
                    for(Craft c : list) wantProducers.computeIfAbsent(c.result(), k -> new LinkedHashSet<>()).add(c.id());
                    check(producers.equals(wantProducers), "crafting producers " + producers + ", expected " + wantProducers);
                    LOGGER.info("{} crafting_recipes: 15 recipes match their exact grid only, wrong grids rejected, {} tag-member grids accepted, lava bucket leaves the bucket, producers {}",
                            TAG, memberGrids, producers.size());
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "crafting_recipes"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 5. item, tags, language

    // ModItems.java:3388 rangefinder, setMaxStackSize(1); OreDictManager.java:311 ANY_RESISTANTALLOY (TCALLOY, CDALLOY), :313 ANY_BISMOIDBRONZE
    // (BBRONZE, ABRONZE), :502 ANY_PLASTICEXPLOSIVE (ingot_semtex, ingot_c4), :380 CU.ingot(ingot_copper); en_US.lang:200,4163,5894,5895; zh_CN.lang:5066,5067,5887,5923
    @GameTest(template = TEMPLATE, batch = "hbm28c_items_tags", timeoutTicks = 100)
    public static void items_tags(GameTestHelper helper) {
        helper.startSequence()
                .thenExecute(guard(() -> {
                    ResourceLocation rangefinderId = ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, "rangefinder");
                    check(BuiltInRegistries.ITEM.containsKey(rangefinderId) && BuiltInRegistries.ITEM.get(rangefinderId) == NtmItems.RANGEFINDER.get(), "hbmsntm:rangefinder is not registered");
                    ItemStack rangefinder = new ItemStack(NtmItems.RANGEFINDER.get());
                    check(rangefinder.getMaxStackSize() == 1, "the rangefinder stacks to " + rangefinder.getMaxStackSize() + ", expected 1");
                    // ModItems.java:3388-3390 missileTab: the MISSILE tab, right after designator_range; the NUKE tab does not list it
                    List<ItemStack> shown = shown(helper, NtmCreativeTabs.MISSILE.get());
                    int at = -1;
                    for(int i = 0; i < shown.size(); i++) if(shown.get(i).is(NtmItems.RANGEFINDER.get())) { check(at < 0, "the rangefinder is listed twice"); at = i; }
                    check(at > 0 && shown.get(at - 1).is(NtmItems.DESIGNATOR_RANGE.get()), "the rangefinder is at " + at + " of the MISSILE tab, not right after designator_range");
                    check(shown(helper, NtmCreativeTabs.NUKE.get()).stream().noneMatch(s -> s.is(NtmItems.RANGEFINDER.get())), "the NUKE tab still lists the rangefinder");

                    Map<String, List<String>> tags = new LinkedHashMap<>();
                    // NEO decision: CU.ingot() (OreDictManager.java:380) as ntm:ingots_copper, the vanilla copper ingot and NEO's ingot_copper
                    tags.put("ntm:ingots_copper", List.of("minecraft:copper_ingot", "hbmsntm:ingot_copper"));
                    tags.put("ntm:ingots_resistant_alloy", List.of("hbmsntm:ingot_tcalloy", "hbmsntm:ingot_cdalloy"));
                    tags.put("ntm:ingots_plastic_explosive", List.of("hbmsntm:ingot_semtex", "hbmsntm:ingot_c4"));
                    tags.put("ntm:ingots_bismoid_bronze", List.of("hbmsntm:ingot_bismuth_bronze", "hbmsntm:ingot_arsenic_bronze"));
                    for(Map.Entry<String, List<String>> e : tags.entrySet()) {
                        TagKey<Item> tag = ItemTags.create(ResourceLocation.parse(e.getKey()));
                        List<String> got = new ArrayList<>();
                        for(Item m : members(tag)) got.add(key(m));
                        check(got.equals(e.getValue()), "#" + e.getKey() + " holds " + got + ", expected " + e.getValue());
                        for(String m : e.getValue()) check(new ItemStack(item(m)).is(tag), m + " is not in #" + e.getKey());
                    }
                    check(NtmBlocks.MACHINE_RADAR.get().asItem() != Items.AIR && NtmBlocks.MACHINE_RADAR_LARGE.get().asItem() != Items.AIR, "a radar has no block item");

                    // language through the mod file's resources (the server loads no assets)
                    Map<String, String> en = Map.of("autoswitch.plates", "Metal Plates", "item.hbmsntm.rangefinder", "Rangefinder",
                            "block.hbmsntm.machine_radar", "Radar", "block.hbmsntm.machine_radar_large", "Large Radar");
                    Map<String, String> zh = Map.of("autoswitch.plates", "金属板", "item.hbmsntm.rangefinder", "测距仪",
                            "block.hbmsntm.machine_radar", "雷达", "block.hbmsntm.machine_radar_large", "大型雷达");
                    JsonObject enFile = lang("en_us.json");
                    JsonObject zhFile = lang("zh_cn.json");
                    for(Map.Entry<String, String> e : en.entrySet()) {
                        check(enFile.has(e.getKey()) && enFile.get(e.getKey()).getAsString().equals(e.getValue()), "en_us " + e.getKey() + " = " + enFile.get(e.getKey()) + ", expected " + e.getValue());
                        String z = zh.get(e.getKey());
                        check(zhFile.has(e.getKey()) && zhFile.get(e.getKey()).getAsString().equals(z), "zh_cn " + e.getKey() + " = " + zhFile.get(e.getKey()) + ", expected " + z);
                    }
                    check(item("hbmsntm:rangefinder") == NtmItems.RANGEFINDER.get() && rangefinder.getDescriptionId().equals("item.hbmsntm.rangefinder"), "rangefinder key " + rangefinder.getDescriptionId());
                    LOGGER.info("{} items_tags: rangefinder registered, stack 1, MISSILE tab index {}; 4 tags exact; 4 en_us and zh_cn keys equal the original", TAG, at);
                }))
                .thenExecute(() -> LOGGER.info("{} {} passed", TAG, "items_tags"))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- helpers

    private static void assertRow(AssemblyMachineRecipes set, Row r) {
        GenericRecipe recipe = set.recipeNameMap.get(r.name());
        check(recipe != null, r.name() + " is not registered");
        check(recipe.duration == r.duration() && recipe.power == r.power(), r.name() + " setup(" + recipe.duration + ", " + recipe.power + "), expected (" + r.duration() + ", " + r.power() + ")");
        check(recipe.outputItem != null && recipe.outputItem.length == 1 && recipe.outputItem[0] instanceof ChanceOutput co && co.chance >= 1F,
                r.name() + " has no single certain output");
        check(output(recipe).equals(mt(r.output(), 0, r.outputCount())), r.name() + " makes " + output(recipe) + ", expected " + r.outputCount() + "x" + r.output());
        check(inputs(recipe).equals(r.inputs()), r.name() + " inputs " + inputs(recipe) + ", expected " + r.inputs());
        check(recipe.inputFluid == null && recipe.outputFluid == null, r.name() + " has fluids");
        if(r.pool() == null) {
            check(recipe.getPools() == null, r.name() + " has pools " + Arrays.toString(recipe.getPools()));
        } else {
            check(Arrays.equals(recipe.getPools(), new String[] { r.pool() }), r.name() + " pools " + Arrays.toString(recipe.getPools()) + ", expected [" + r.pool() + "]");
            check(GenericRecipes.blueprintPools.getOrDefault(r.pool(), List.of()).contains(r.name()), r.name() + " is not in the static pool " + r.pool());
        }
        check(r.group() == null ? recipe.autoSwitchGroup == null : r.group().equals(recipe.autoSwitchGroup), r.name() + " group " + recipe.autoSwitchGroup + ", expected " + r.group());
    }

    private static Stack of(AStack a) {
        if(a instanceof ComparableStack c) return new Stack("item", key(c.item), c.meta, c.stacksize);
        if(a instanceof TagStack t) return new Stack("tag", t.tag.location().toString(), 0, t.stacksize);
        return new Stack(a.getClass().getSimpleName(), String.valueOf(a), 0, a.stacksize);
    }

    private static List<Stack> inputs(GenericRecipe recipe) {
        List<Stack> out = new ArrayList<>();
        if(recipe.inputItem != null) for(AStack a : recipe.inputItem) out.add(of(a));
        return out;
    }

    private static Stack output(GenericRecipe recipe) {
        if(recipe.outputItem == null || recipe.outputItem.length == 0 || !(recipe.outputItem[0] instanceof ChanceOutput co)) return null;
        return mt(key(co.stack.getItem()), MetaHelper.getMeta(co.stack), co.stack.getCount());
    }

    private static List<String> fluids(FluidStack[] stacks) {
        List<String> out = new ArrayList<>();
        if(stacks != null) for(FluidStack f : stacks) out.add(f.type.getName() + " " + f.fill + " " + f.pressure);
        return out;
    }

    /** Everything the template file carries for one row. */
    private static String describe(GenericRecipe r) {
        List<String> outs = new ArrayList<>();
        if(r.outputItem != null) for(IOutput o : r.outputItem) {
            List<String> all = new ArrayList<>();
            for(ItemStack s : o.getAllPossibilities()) all.add(s.getCount() + "x" + key(s.getItem()) + "@" + MetaHelper.getMeta(s));
            outs.add(o.getClass().getSimpleName() + all + (o instanceof ChanceOutput co ? " p" + co.chance : ""));
        }
        ItemStack icon = r.writeIcon ? r.getIcon() : ItemStack.EMPTY;
        return r.getInternalName() + " d" + r.duration + " p" + r.power + " in" + inputs(r) + " fin" + fluids(r.inputFluid) + " out" + outs + " fout" + fluids(r.outputFluid)
                + " pools" + Arrays.toString(r.getPools()) + " group " + r.autoSwitchGroup + " named " + r.customLocalization + " wrap " + r.nameWrapper
                + " icon " + (r.writeIcon ? icon.getCount() + "x" + key(icon.getItem()) + "@" + MetaHelper.getMeta(icon) : "-");
    }

    private static List<String> names(List<GenericRecipe> recipes) {
        List<String> out = new ArrayList<>();
        if(recipes != null) for(GenericRecipe r : recipes) out.add(r.getInternalName());
        return out;
    }

    private static String firstDifference(List<String> a, List<String> b) {
        for(int i = 0; i < Math.min(a.size(), b.size()); i++) if(!a.get(i).equals(b.get(i))) return "index " + i + ": " + a.get(i) + " vs " + b.get(i);
        return "lengths " + a.size() + " / " + b.size();
    }

    private static List<ItemStack> shown(GameTestHelper helper, CreativeModeTab tab) {
        tab.buildContents(new CreativeModeTab.ItemDisplayParameters(helper.getLevel().enabledFeatures(), false, helper.getLevel().registryAccess()));
        return new ArrayList<>(tab.getDisplayItems());
    }

    private static List<Item> members(TagKey<Item> tag) {
        List<Item> out = new ArrayList<>();
        for(Holder<Item> h : BuiltInRegistries.ITEM.getTagOrEmpty(tag)) out.add(h.value());
        return out;
    }

    private static String key(Item item) {
        return BuiltInRegistries.ITEM.getKey(item).toString();
    }

    private static Item item(String spec) {
        String id = spec.contains("@") ? spec.substring(0, spec.indexOf('@')) : spec;
        ResourceLocation loc = ResourceLocation.parse(id);
        check(BuiltInRegistries.ITEM.containsKey(loc), "no item " + id);
        return BuiltInRegistries.ITEM.get(loc);
    }

    private static int meta(String spec, int fallback) {
        return spec.contains("@") ? Integer.parseInt(spec.substring(spec.indexOf('@') + 1)) : fallback;
    }

    private static ItemStack stack(String spec) {
        if(spec.startsWith("#")) {
            List<Item> members = members(ItemTags.create(ResourceLocation.parse(spec.substring(1))));
            check(!members.isEmpty(), spec + " is empty");
            return new ItemStack(members.get(0));
        }
        ItemStack s = new ItemStack(item(spec));
        if(spec.contains("@")) MetaHelper.setMeta(s, meta(spec, 0));
        return s;
    }

    /**
     * The grid of a recipe: shaped by its pattern, with {@code with} in the first cell of key {@code replace} (or in every cell of it when
     * {@code every}); shapeless in order, with {@code with} at index {@code replace}.
     */
    private static CraftingInput grid(Craft c, int replace, String with) {
        return grid(c, replace, with, false);
    }

    private static CraftingInput grid(Craft c, int replace, String with, boolean every) {
        List<ItemStack> cells = new ArrayList<>();
        if(c.pattern() != null) {
            boolean replaced = false;
            for(String rowText : c.pattern()) for(char ch : rowText.toCharArray()) {
                if(ch == ' ') {
                    cells.add(ItemStack.EMPTY);
                } else if(ch == replace && (every || !replaced)) {
                    cells.add(stack(with));
                    replaced = true;
                } else {
                    cells.add(stack(c.key().get(ch)));
                }
            }
            return CraftingInput.of(c.pattern()[0].length(), c.pattern().length, cells);
        }
        for(int i = 0; i < c.shapeless().size(); i++) cells.add(stack(i == replace ? with : c.shapeless().get(i)));
        return CraftingInput.of(cells.size(), 1, cells);
    }

    /** Requires {@code id} to be the only crafting recipe matching the grid and returns its result. */
    private static ItemStack only(ServerLevel level, ResourceLocation id, CraftingInput input, String label) {
        List<RecipeHolder<CraftingRecipe>> all = level.getRecipeManager().getRecipesFor(RecipeType.CRAFTING, input, level);
        List<ResourceLocation> ids = all.stream().map(RecipeHolder::id).collect(Collectors.toList());
        check(ids.equals(List.of(id)), label + ": the grid matches " + ids + ", expected only " + id);
        return all.get(0).value().assemble(input, level.registryAccess());
    }

    private static JsonObject lang(String file) {
        Path path = ModList.get().getModFileById(NuclearTechMod.MODID).getFile().findResource("assets", NuclearTechMod.MODID, "lang", file);
        check(Files.isRegularFile(path), "the mod file has no assets/" + NuclearTechMod.MODID + "/lang/" + file + " (" + path + ")");
        try(Reader reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)) {
            return JsonParser.parseReader(reader).getAsJsonObject();
        } catch(IOException e) {
            throw new IllegalStateException(e);
        }
    }
}
