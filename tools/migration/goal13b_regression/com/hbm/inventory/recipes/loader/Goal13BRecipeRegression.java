package com.hbm.inventory.recipes.loader;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.stream.JsonWriter;
import com.hbm.config.NtmConfig;
import com.hbm.inventory.RecipesCommon;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.RecipesCommon.TagStack;
import com.hbm.inventory.recipes.ArcFurnaceRecipes;
import com.hbm.inventory.recipes.ArcFurnaceRecipes.ArcFurnaceRecipe;
import com.hbm.inventory.recipes.AssemblyMachineRecipes;
import com.hbm.inventory.recipes.CrackingRecipes;
import com.hbm.inventory.recipes.PressRecipes;
import com.hbm.inventory.recipes.SolderingRecipes;
import com.hbm.inventory.recipes.SolderingRecipes.SolderingRecipe;
import com.hbm.items.machine.StampItem;
import com.hbm.items.machine.StampItem.StampType;
import com.hbm.main.NuclearTechMod;
import net.minecraft.tags.ItemTags;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.Blocks;

import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Goal 13B recipe world (real Gson, the production SerializableRecipe, GenericRecipes, GenericRecipe and tables): the silicon billet press entry,
 * ass.chip and ass.arcfurnace, the arc furnace table and the recipe tables of the silicon and chip chain, compared with the post-Goal 13A tables
 * (goal13b.base.AssemblyMachineRecipes and goal13b.base.PressRecipes, compiled in the same world from build/migration/goal13b/base-g13a).
 *
 * Original (Hbm-s-Nuclear-Tech-GIT d7ef2df): AssemblyMachineRecipes.java:126-128 ass.chip setup(50, 250): 1 polymer plate + 1 silicon circuit
 * (circuit SILICON, the printed silicon wafer) + 1 gold fine wire -> 1 circuit CHIP (the microchip), inside the !enable528 block in front of the
 * other crafting parts (:129-148); :286-288 ass.arcfurnace setup(200, 100): 12 ANY_CONCRETE + 8 any plastic ingots + 16 firebrick ingots + 8
 * steel cast plates + 1 machine_transformer + 1 analog circuit -> 1 machine_arc_furnace, outside any flag; PressRecipes.java:99 STAMP CIRCUIT:
 * silicon billet -> circuit SILICON; ArcFurnaceRecipes.java:53-65 the solid defaults, :135-150 register (an occupied input rejects the recipe),
 * :225-227 hbmArcFurnace.json; SolderingRecipes.java:54-61 the BASIC circuit: 4 chips + 4 PCBs + 4 lead fine wire -> 1 basic circuit, 200 ticks,
 * 250 HE/t. Stack, tick and power values are those of the original; ids are the stand-in registry's (the registered names are read by
 * verify_goal13b.py).
 */
public class Goal13BRecipeRegression {
    private static int checks;
    private static int sectionChecks;
    private static final List<String> failures = new ArrayList<>();
    static final int WILDCARD = 32767;
    static Path work;

    private static void check(boolean condition, String message) {
        if(!condition) throw new AssertionError(message);
        checks++;
        sectionChecks++;
    }

    private static void info(String message) {
        System.out.println("info: " + message);
    }

    interface Body { void run() throws Exception; }

    private static void run(String name, Body body) {
        sectionChecks = 0;
        try {
            body.run();
            System.out.println(name + ": " + sectionChecks + " checks passed");
        } catch(AssertionError e) {
            failures.add(name);
            System.out.println("AssertionError in " + name + " after " + sectionChecks + " passed checks: " + e.getMessage());
        } catch(Exception e) {
            failures.add(name);
            System.out.println("Exception in " + name + ": " + e);
            e.printStackTrace(System.out);
        }
    }

    // ---- JSON helpers ------------------------------------------------------------------------------------------------------

    static JsonObject write(SerializableRecipe table, Object recipe) throws Exception {
        StringWriter text = new StringWriter();
        JsonWriter writer = new JsonWriter(text);
        writer.beginObject();
        table.writeRecipe(recipe, writer);
        writer.endObject();
        writer.close();
        return JsonParser.parseString(text.toString()).getAsJsonObject();
    }

    static Map<String, JsonObject> catalog(GenericRecipes<GenericRecipe> recipes) throws Exception {
        recipes.deleteRecipes();
        GenericRecipes.clearPools();
        recipes.registerDefaults();
        Map<String, JsonObject> out = new LinkedHashMap<>();
        for(GenericRecipe recipe : recipes.recipeOrderedList) out.put(recipe.getInternalName(), write(recipes, recipe));
        return out;
    }

    static JsonArray item(String id, int count, int meta) {
        JsonArray a = new JsonArray();
        a.add("item");
        a.add(id);
        a.add(count);
        a.add(meta);
        return a;
    }

    static JsonArray tag(String id, int count) {
        JsonArray a = new JsonArray();
        a.add("tag");
        a.add(id);
        if(count != 1) a.add(count);
        return a;
    }

    static JsonArray single(String id, int count) {
        JsonArray stack = new JsonArray();
        stack.add(id);
        if(count != 1) stack.add(count);
        JsonArray single = new JsonArray();
        single.add("single");
        single.add(stack);
        return single;
    }

    static JsonArray array(JsonArray... entries) {
        JsonArray a = new JsonArray();
        for(JsonArray e : entries) a.add(e);
        return a;
    }

    static JsonArray stackJson(String id, int count) {
        JsonArray a = new JsonArray();
        a.add(id);
        if(count != 1) a.add(count);
        return a;
    }

    static List<String> changed(Map<String, JsonObject> live, Map<String, JsonObject> head) {
        List<String> out = new ArrayList<>();
        for(String name : head.keySet()) if(!head.get(name).equals(live.get(name))) out.add(name);
        return out;
    }

    static int pooled(AssemblyMachineRecipes table) {
        int n = 0;
        for(GenericRecipe r : table.recipeOrderedList) if(r.isPooled()) n++;
        return n;
    }

    static JsonObject recipe(String name, int duration, int power, JsonArray in, JsonArray out, boolean named, String pool) {
        JsonObject o = new JsonObject();
        o.addProperty("name", name);
        o.add("inputItem", in);
        o.add("outputItem", out);
        o.addProperty("duration", duration);
        o.addProperty("power", power);
        if(named) o.addProperty("named", true);
        if(pool != null) o.addProperty("blueprintpool", pool);
        return o;
    }

    // ---- 3b. ass.chip and ass.arcfurnace ------------------------------------------------------------------------------------

    static void assembler() throws Exception {
        NtmConfig.COMMON.ENABLE_528.set(false);
        Map<String, JsonObject> live = catalog(AssemblyMachineRecipes.INSTANCE);
        Map<String, List<String>> livePools = new LinkedHashMap<>();
        GenericRecipes.blueprintPools.forEach((k, v) -> livePools.put(k, new ArrayList<>(v)));
        int livePooled = pooled(AssemblyMachineRecipes.INSTANCE);
        Map<String, JsonObject> base = catalog(goal13b.base.AssemblyMachineRecipes.INSTANCE);
        Map<String, List<String>> basePools = new LinkedHashMap<>(GenericRecipes.blueprintPools);
        int basePooled = 0;
        for(GenericRecipe r : goal13b.base.AssemblyMachineRecipes.INSTANCE.recipeOrderedList) if(r.isPooled()) basePooled++;
        List<String> liveNames = new ArrayList<>(live.keySet()), baseNames = new ArrayList<>(base.keySet());
        List<String> alt = List.of("ass.analogAlt", "ass.factorioChip", "ass.atomicClockAlt");

        JsonObject chip = recipe("ass.chip", 50, 250,
                array(item("hbmsntm:plate_polymer", 1, WILDCARD), item("hbmsntm:circuit_printed_silicon_wafer", 1, WILDCARD), item("hbmsntm:wire_gold", 1, WILDCARD)),
                array(single("hbmsntm:circuit_microchip", 1)), false, null);
        JsonObject furnace = recipe("ass.arcfurnace", 200, 100,
                array(tag("ntm:any_concrete", 12), tag("ntm:ingots_plastic", 8), item("hbmsntm:ingot_firebrick", 16, WILDCARD),
                        item("hbmsntm:cast_plate", 8, castPlateSteel()), item("hbmsntm:transformer", 1, WILDCARD), item("hbmsntm:circuit_analog_board", 1, WILDCARD)),
                array(single("hbmsntm:machine_arc_furnace", 1)), false, null);
        check(chip.equals(live.get("ass.chip")),
                "ass.chip: 50 ticks, 250 HE/t, 1 polymer plate + 1 printed silicon wafer + 1 gold wire -> 1 microchip, not named, no pool (original AssemblyMachineRecipes.java:126-128): "
                        + live.get("ass.chip"));
        check(furnace.equals(live.get("ass.arcfurnace")),
                "ass.arcfurnace: 200 ticks, 100 HE/t, 12 of #ntm:any_concrete + 8 of #ntm:ingots_plastic + 16 firebrick ingots + 8 steel cast plates + 1 transformer + 1 analog circuit board "
                        + "-> 1 arc furnace, not named, no pool (:286-288, the expensive inputs are not ported): " + live.get("ass.arcfurnace"));
        check(!base.containsKey("ass.chip") && !base.containsKey("ass.arcfurnace") && baseNames.get(baseNames.size() - 1).equals("ass.atomicClockAlt"),
                "the post-Goal 13A catalog has neither and ends with ass.atomicClockAlt (" + baseNames.size() + " recipes)");
        List<String> expected = new ArrayList<>(baseNames.subList(0, baseNames.size() - alt.size()));
        expected.add("ass.chip");
        expected.addAll(alt);
        expected.add("ass.arcfurnace");
        check(liveNames.equals(expected) && liveNames.size() == baseNames.size() + 2,
                "exactly two recipes are added: ass.chip in front of the three alt..circuit recipes (inside the !enable528 block, directly after ass.crackingtower) and ass.arcfurnace last; "
                        + "every other recipe keeps its name and position (" + baseNames.size() + " -> " + liveNames.size() + ")");
        check(changed(live, base).isEmpty(), "no post-Goal 13A assembler recipe changes (Goal 13A's three alt..circuit recipes included): " + changed(live, base));
        check(livePooled == basePooled && livePools.equals(basePools) && !live.get("ass.chip").has("blueprintpool") && !live.get("ass.arcfurnace").has("blueprintpool"),
                "neither new recipe is pooled: the pools and the pooled recipe count (" + basePooled + ") are the post-Goal 13A ones: " + livePools.keySet());
        GenericRecipe liveChip = AssemblyMachineRecipes.INSTANCE.recipeNameMap.get("ass.chip");
        GenericRecipe liveFurnace = AssemblyMachineRecipes.INSTANCE.recipeNameMap.get("ass.arcfurnace");
        check(liveChip != null && !liveChip.isPooled() && !liveChip.customLocalization && liveChip.duration == 50 && liveChip.power == 250
                        && liveFurnace != null && !liveFurnace.isPooled() && !liveFurnace.customLocalization && liveFurnace.duration == 200 && liveFurnace.power == 100,
                "both are unpooled and use the icon name (no language key: setup, not setupNamed), with their ticks and power on the recipe object");

        // enable528 flips ass.chip away and keeps ass.arcfurnace.
        NtmConfig.COMMON.ENABLE_528.set(true);
        Map<String, JsonObject> mode528 = catalog(AssemblyMachineRecipes.INSTANCE);
        Map<String, List<String>> pools528 = new LinkedHashMap<>(GenericRecipes.blueprintPools);
        NtmConfig.COMMON.ENABLE_528.set(false);
        List<String> names528 = new ArrayList<>(baseNames.subList(0, baseNames.size() - alt.size()));
        names528.add("ass.arcfurnace");
        check(!mode528.containsKey("ass.chip") && mode528.containsKey("ass.arcfurnace") && new ArrayList<>(mode528.keySet()).equals(names528) && furnace.equals(mode528.get("ass.arcfurnace"))
                        && !pools528.containsKey("alt..circuit"),
                "with enable528 ass.chip (and the three alt..circuit recipes) are not registered while ass.arcfurnace still is, last, unchanged: " + mode528.keySet().size() + " recipes");
        check(changed(mode528, base).stream().allMatch(alt::contains) && changed(mode528, base).equals(alt),
                "with enable528 the post-Goal 13A recipes differ only by the three alt..circuit recipes that are gone: " + changed(mode528, base));
        Map<String, JsonObject> again = catalog(AssemblyMachineRecipes.INSTANCE);
        check(new ArrayList<>(again.keySet()).equals(liveNames) && again.get("ass.chip").equals(chip), "with the flag off again ass.chip is back in its place");

        // The export reads back through the production reader.
        AssemblyMachineRecipes.INSTANCE.deleteRecipes();
        GenericRecipes.clearPools();
        for(JsonObject json : live.values()) AssemblyMachineRecipes.INSTANCE.readRecipe(json);
        boolean same = true;
        for(String name : liveNames) same &= write(AssemblyMachineRecipes.INSTANCE, AssemblyMachineRecipes.INSTANCE.recipeNameMap.get(name)).equals(live.get(name));
        check(same, "the exported template reads back through the production reader: every recipe, ass.chip and ass.arcfurnace included, writes the same");
        AssemblyMachineRecipes.INSTANCE.deleteRecipes();
        GenericRecipes.clearPools();
        AssemblyMachineRecipes.INSTANCE.registerDefaults();
        info("assembler recipes: " + baseNames.size() + " after Goal 13A, " + liveNames.size() + " now");
    }

    /** The stand-in meta of Type.STEEL: NtmItems.castPlateIngredient passes type.ordinal(); verify_goal13b.py reads the production call. */
    static int castPlateSteel() {
        return com.hbm.items.CastPlateItem.Type.STEEL.ordinal();
    }

    // ---- 4. The arc furnace table -------------------------------------------------------------------------------------------

    static JsonArray itemInput(String id) {
        return item(id, 1, WILDCARD);
    }

    static JsonObject entry(JsonArray input, String output, int count) {
        JsonObject o = new JsonObject();
        o.add("input", input);
        o.add("solid", stackJson(output, count));
        return o;
    }

    /** Original ArcFurnaceRecipes.java:53-65 in registration order (the NEO items the ore dictionary entries stand for; sand_mix is deferred). */
    static List<JsonObject> originalDefaults() {
        String nugget = "hbmsntm:nugget_silicon";
        return List.of(
                entry(tag("minecraft:sand", 1), nugget, 1),
                entry(itemInput("minecraft:flint"), nugget, 4),
                entry(itemInput("minecraft:quartz"), nugget, 3),
                entry(itemInput("hbmsntm:powder_quartz"), nugget, 3),
                entry(itemInput("minecraft:quartz_block"), nugget, 12),
                entry(itemInput("hbmsntm:ingot_fiberglass"), nugget, 4),
                entry(itemInput("hbmsntm:block_fiberglass"), nugget, 40),
                entry(itemInput("hbmsntm:ingot_asbestos"), nugget, 4),
                entry(itemInput("hbmsntm:powder_asbestos"), nugget, 4),
                entry(itemInput("hbmsntm:block_asbestos"), nugget, 40),
                entry(itemInput("hbmsntm:powder_borax"), "hbmsntm:powder_boron_tiny", 3));
    }

    static List<JsonObject> exported(ArcFurnaceRecipes table) throws Exception {
        List<JsonObject> out = new ArrayList<>();
        for(ArcFurnaceRecipe recipe : ArcFurnaceRecipes.recipes) out.add(write(table, recipe));
        return out;
    }

    static Path scratch(String name) throws Exception {
        Path dir = work.resolve(name);
        Files.createDirectories(dir);
        return dir;
    }

    static void arcFurnace() throws Exception {
        RecipesCommon.TAG_MEMBERS.clear();
        ArcFurnaceRecipes table = new ArcFurnaceRecipes();
        table.deleteRecipes();
        table.registerDefaults();
        List<JsonObject> defaults = originalDefaults();
        List<JsonObject> live = exported(table);
        check(live.size() == 11 && live.equals(defaults),
                "the 11 default solid recipes in the original order (ArcFurnaceRecipes.java:53-65): sand 1, flint 4, quartz 3, quartz dust 3, quartz block 12, fibreglass ingot 4, fibreglass block 40, "
                        + "asbestos ingot 4, asbestos powder 4, asbestos block 40 nuggets of silicon, borax powder 3 tiny boron powder (sand_mix -> quartz glass deferred): " + live);
        check(table.getFileName().equals("hbmArcFurnace.json") && table.getRecipeObject() == ArcFurnaceRecipes.recipes && table.getComment() == null,
                "the template file is hbmArcFurnace.json over the recipe list (original ArcFurnaceRecipes.java:225-227), without a comment");

        // De-duplication (original register, :135-150): an occupied input rejects the recipe; the count of the key is ignored.
        ItemStack stone = new ItemStack(Items.STONE);
        ArcFurnaceRecipes.register(new ComparableStack(Items.FLINT), stone);
        ArcFurnaceRecipes.register(new ComparableStack(Items.FLINT, 5), stone);
        ArcFurnaceRecipes.register(new ComparableStack(Blocks.QUARTZ_BLOCK, 3, 0), stone);
        check(ArcFurnaceRecipes.recipes.size() == 11 && exported(table).equals(defaults),
                "a second recipe for flint (count 1 or 5) or for the quartz block (any count or meta) is rejected: the table is unchanged");
        Item fresh = new Item("hbmsntm:test_input");
        ArcFurnaceRecipes.register(new ComparableStack(fresh, 3), stone);
        ArcFurnaceRecipes.register(new ComparableStack(fresh), new ItemStack(Items.COAL));
        check(ArcFurnaceRecipes.recipes.size() == 12 && ArcFurnaceRecipes.getRecipe(new ItemStack(fresh)).solidOutput.getItem() == Items.STONE,
                "an unused input registers, and a later recipe for it is rejected: the first one stays");
        TagStack mixed = new TagStack(ItemTags.create(ResourceLocation.parse("ntm:mixed")));
        RecipesCommon.TAG_MEMBERS.put("ntm:mixed", List.of(Items.FLINT, new Item("hbmsntm:test_free")));
        ArcFurnaceRecipes.register(mixed, stone);
        check(ArcFurnaceRecipes.recipes.size() == 12, "a tag recipe is rejected as a whole when any member it resolves to is already used (flint)");
        TagStack free = new TagStack(ItemTags.create(ResourceLocation.parse("ntm:free")));
        Item freeA = new Item("hbmsntm:free_a"), freeB = new Item("hbmsntm:free_b");
        RecipesCommon.TAG_MEMBERS.put("ntm:free", List.of(freeA, freeB));
        ArcFurnaceRecipes.register(free, stone);
        ArcFurnaceRecipes.register(new ComparableStack(freeB), new ItemStack(Items.COAL));
        check(ArcFurnaceRecipes.recipes.size() == 13, "a tag recipe whose members are free registers and reserves them: a later recipe for one member is rejected (" + ArcFurnaceRecipes.recipes.size() + ")");
        RecipesCommon.TAG_MEMBERS.clear();
        table.deleteRecipes();
        check(ArcFurnaceRecipes.recipes.isEmpty(), "deleteRecipes empties the table");
        table.registerDefaults();
        check(exported(table).equals(defaults), "deleteRecipes also forgets the reserved inputs: the defaults register again, all 11");

        // Lookup: an item, a tag member (sand and red sand), the first registered match wins.
        Items.SAND.tags.add("minecraft:sand");
        Items.RED_SAND.tags.add("minecraft:sand");
        ItemStack sandOut = ArcFurnaceRecipes.getSolidOutput(new ItemStack(Items.SAND));
        check(sandOut.getItem().id.equals("hbmsntm:nugget_silicon") && sandOut.getCount() == 1
                        && ArcFurnaceRecipes.getSolidOutput(new ItemStack(Items.RED_SAND, 7)).getCount() == 1,
                "getRecipe finds a member of #minecraft:sand (sand and red sand) whatever the stack size: 1 nugget of silicon");
        ArcFurnaceRecipe flint = ArcFurnaceRecipes.getRecipe(new ItemStack(Items.FLINT, 64));
        check(flint != null && flint.solidOutput.getCount() == 4 && flint.input instanceof ComparableStack
                        && ArcFurnaceRecipes.getSolidOutput(new ItemStack(Items.FLINT)).getCount() == 4,
                "getRecipe finds flint (4 nuggets) by item, whatever the stack size, and getSolidOutput returns a copy");
        ArcFurnaceRecipes.getSolidOutput(new ItemStack(Items.FLINT)).setCount(99);
        check(ArcFurnaceRecipes.getRecipe(new ItemStack(Items.FLINT)).solidOutput.getCount() == 4, "changing the returned copy does not change the table");
        check(ArcFurnaceRecipes.getRecipe(new ItemStack(Items.STONE)) == null && ArcFurnaceRecipes.getRecipe(ItemStack.EMPTY) == null && ArcFurnaceRecipes.getRecipe(null) == null
                        && ArcFurnaceRecipes.getSolidOutput(new ItemStack(Items.STONE)).isEmpty(),
                "no recipe for an unrelated item, an empty stack or null: null, and an empty solid output");
        table.deleteRecipes();
        TagStack early = new TagStack(ItemTags.create(ResourceLocation.parse("ntm:early")));
        ArcFurnaceRecipes.register(early, new ItemStack(Items.COAL, 2));
        ArcFurnaceRecipes.register(new ComparableStack(Items.FLINT), new ItemStack(Items.COAL, 3));
        Items.FLINT.tags.add("ntm:early");
        check(ArcFurnaceRecipes.getRecipe(new ItemStack(Items.FLINT)).solidOutput.getCount() == 2,
                "the lookup follows registration order: a tag recipe registered before a flint recipe wins for flint (tags are not bound while the defaults load, so it did not reserve flint)");
        Items.FLINT.tags.remove("ntm:early");
        table.deleteRecipes();
        table.registerDefaults();
        info("arc furnace: " + ArcFurnaceRecipes.recipes.size() + " default recipes");

        // The production loader: no file -> the defaults and the template; the template as a custom file -> the same table; a custom file wins.
        SerializableRecipe.recipeHandlers.clear();
        SerializableRecipe.recipeHandlers.add(new ArcFurnaceRecipes());
        Path none = scratch("arc-none");
        NuclearTechMod.configDir = none.toFile();
        SerializableRecipe.initialize();
        Path template = none.resolve("hbmRecipes/_hbmArcFurnace.json");
        check(Files.isRegularFile(template) && !Files.exists(none.resolve("hbmRecipes/hbmArcFurnace.json")) && exported(table).equals(defaults),
                "no hbmArcFurnace.json: the defaults register and _hbmArcFurnace.json is written");
        JsonObject json = JsonParser.parseString(Files.readString(template, StandardCharsets.UTF_8)).getAsJsonObject();
        JsonArray listed = json.getAsJsonArray("recipes");
        List<JsonElement> listedList = new ArrayList<>();
        listed.forEach(listedList::add);
        check(!json.has("comment") && listed.size() == 11 && listedList.equals(new ArrayList<JsonElement>(defaults)) && listed.get(0).getAsJsonObject().keySet().equals(java.util.Set.of("input", "solid")),
                "the template lists the 11 recipes with the keys input and solid: " + listed.get(1));
        Path same = scratch("arc-template");
        Files.createDirectories(same.resolve("hbmRecipes"));
        Files.copy(template, same.resolve("hbmRecipes/hbmArcFurnace.json"));
        NuclearTechMod.configDir = same.toFile();
        ArcFurnaceRecipe before = ArcFurnaceRecipes.recipes.get(1);
        SerializableRecipe.initialize();
        check(SerializableRecipe.recipeHandlers.get(0).modified && ArcFurnaceRecipes.recipes.size() == 11 && ArcFurnaceRecipes.recipes.get(1) != before && exported(table).equals(defaults),
                "the template renamed to hbmArcFurnace.json is read instead of the defaults and gives the same 11 recipes (input and solid output round trip)");
        String custom = "{\"recipes\":[{\"input\":[\"item\",\"minecraft:flint\",1,32767],\"solid\":[\"hbmsntm:nugget_silicon\",9]},"
                + "{\"input\":[\"item\",\"minecraft:flint\",1,32767],\"solid\":[\"hbmsntm:nugget_silicon\",1]},"
                + "{\"input\":[\"item\",\"minecraft:quartz\",1,32767]},"
                + "{\"input\":[\"tag\",\"ntm:custom\",2],\"solid\":[\"minecraft:coal\",2]}]}";
        Path own = scratch("arc-custom");
        Files.createDirectories(own.resolve("hbmRecipes"));
        Files.writeString(own.resolve("hbmRecipes/hbmArcFurnace.json"), custom, StandardCharsets.UTF_8);
        NuclearTechMod.configDir = own.toFile();
        SerializableRecipe.initialize();
        check(ArcFurnaceRecipes.recipes.size() == 2 && ArcFurnaceRecipes.getRecipe(new ItemStack(Items.FLINT)).solidOutput.getCount() == 9
                        && ArcFurnaceRecipes.getRecipe(new ItemStack(Items.SAND)) == null && ArcFurnaceRecipes.getRecipe(new ItemStack(Items.QUARTZ)) == null,
                "a custom hbmArcFurnace.json wins: only its recipes exist, the first flint entry (9 nuggets) beats the duplicate, the entry without a solid output (liquid-only upstream) is skipped, "
                        + "the defaults (sand, quartz) are gone");
        ArcFurnaceRecipe tagged = ArcFurnaceRecipes.recipes.get(1);
        check(tagged.input instanceof TagStack t && t.tag.location().toString().equals("ntm:custom") && t.stacksize == 2 && tagged.solidOutput.getItem() == Items.COAL && tagged.solidOutput.getCount() == 2,
                "a custom tag input with a count reads back with its tag and count");
        table.deleteRecipes();
        table.registerDefaults();

        // registerAllHandlers: ArcFurnaceRecipes directly after CrackingRecipes, once.
        SerializableRecipe.recipeHandlers.clear();
        SerializableRecipe.registerAllHandlers();
        List<SerializableRecipe> handlers = SerializableRecipe.recipeHandlers;
        int cracking = -1, arc = -1, arcCount = 0;
        for(int i = 0; i < handlers.size(); i++) {
            if(handlers.get(i) instanceof CrackingRecipes) cracking = i;
            if(handlers.get(i) instanceof ArcFurnaceRecipes) { arc = i; arcCount++; }
        }
        check(arcCount == 1 && cracking >= 0 && arc == cracking + 1 && handlers.get(arc + 1) == AssemblyMachineRecipes.INSTANCE && handlers.size() == 11,
                "registerAllHandlers adds one ArcFurnaceRecipes directly after CrackingRecipes and before the generic tables (" + handlers.size() + " handlers, position " + arc + ")");
        SerializableRecipe.recipeHandlers.clear();
    }

    // ---- 6b. The silicon billet in the press ------------------------------------------------------------------------------

    static ItemStack stamp(StampType type) {
        return new ItemStack(new StampItem("stamp_" + type.name().toLowerCase(), type));
    }

    static List<String> pressEntries(SerializableRecipe table, Map<?, ItemStack> recipes) throws Exception {
        List<String> out = new ArrayList<>();
        for(Map.Entry<?, ItemStack> entry : recipes.entrySet()) out.add(write(table, entry).toString());
        Collections.sort(out);
        return out;
    }

    static void press() throws Exception {
        PressRecipes table = new PressRecipes();
        table.deleteRecipes();
        table.registerDefaults();
        goal13b.base.PressRecipes base = new goal13b.base.PressRecipes();
        base.deleteRecipes();
        base.registerDefaults();
        List<String> live = pressEntries(table, PressRecipes.recipes);
        List<String> was = pressEntries(base, goal13b.base.PressRecipes.recipes);
        String billet = "{\"input\":[\"item\",\"hbmsntm:billet_silicon\",1,32767],\"stamp\":\"circuit\",\"output\":[\"hbmsntm:circuit_printed_silicon_wafer\"]}";
        List<String> expected = new ArrayList<>(was);
        expected.add(billet);
        Collections.sort(expected);
        check(live.size() == was.size() + 1 && live.equals(expected) && !was.contains(billet) && live.contains(billet),
                "the default press table is the post-Goal 13A table (" + was.size() + " entries: coke, plate and wire stamps) plus exactly the silicon billet CIRCUIT entry (" + live.size() + "): " + billet);
        ItemStack billets = new ItemStack(com.hbm.items.NtmItems.BILLET_SILICON.get(), 5);
        ItemStack out = PressRecipes.getOutput(billets, stamp(StampType.CIRCUIT));
        check(out.getItem() == com.hbm.items.NtmItems.CIRCUIT_PRINTED_SILICON_WAFER.get() && out.getCount() == 1 && PressRecipes.getInputCount(billets, stamp(StampType.CIRCUIT)) == 1,
                "silicon billet + a circuit stamp -> 1 printed silicon wafer, 1 billet used (original PressRecipes.java:99): " + out.getCount());
        boolean others = true;
        for(StampType type : StampType.values()) if(type != StampType.CIRCUIT) others &= PressRecipes.getOutput(billets, stamp(type)).isEmpty();
        check(others && PressRecipes.getOutput(new ItemStack(com.hbm.items.NtmItems.NUGGET_SILICON.get(), 6), stamp(StampType.CIRCUIT)).isEmpty()
                        && PressRecipes.getOutput(billets, ItemStack.EMPTY).isEmpty() && PressRecipes.getOutput(ItemStack.EMPTY, stamp(StampType.CIRCUIT)).isEmpty(),
                "the billet has no recipe with any other stamp, a nugget has none with the circuit stamp, and an empty slot gives nothing");
        ItemStack coke = new ItemStack(com.hbm.items.NtmItems.COKE_COAL.get());
        check(PressRecipes.getOutput(coke, stamp(StampType.FLAT)).getItem() == com.hbm.items.NtmItems.INGOT_GRAPHITE.get() && PressRecipes.getOutput(coke, stamp(StampType.CIRCUIT)).isEmpty(),
                "the coke entry is unchanged: flat stamp -> graphite ingot, nothing with the circuit stamp");
        // The template: no file -> defaults + _hbmPress.json; the template as a custom file gives the same table.
        SerializableRecipe.recipeHandlers.clear();
        SerializableRecipe.recipeHandlers.add(new PressRecipes());
        Path none = scratch("press-none");
        NuclearTechMod.configDir = none.toFile();
        SerializableRecipe.initialize();
        Path template = none.resolve("hbmRecipes/_hbmPress.json");
        JsonArray listed = JsonParser.parseString(Files.readString(template, StandardCharsets.UTF_8)).getAsJsonObject().getAsJsonArray("recipes");
        List<String> listedText = new ArrayList<>();
        listed.forEach(e -> listedText.add(e.getAsJsonObject().toString()));
        Collections.sort(listedText);
        check(listed.size() == expected.size() && listedText.equals(expected), "the template _hbmPress.json lists the " + expected.size() + " entries, the billet one as " + billet);
        Path same = scratch("press-template");
        Files.createDirectories(same.resolve("hbmRecipes"));
        Files.copy(template, same.resolve("hbmRecipes/hbmPress.json"));
        NuclearTechMod.configDir = same.toFile();
        SerializableRecipe.initialize();
        check(SerializableRecipe.recipeHandlers.get(0).modified && pressEntries(table, PressRecipes.recipes).equals(expected)
                        && PressRecipes.getOutput(billets, stamp(StampType.CIRCUIT)).getCount() == 1,
                "the template read as hbmPress.json gives the same " + expected.size() + " entries and the billet still presses to a wafer");
        SerializableRecipe.recipeHandlers.clear();
        table.deleteRecipes();
        table.registerDefaults();
    }

    // ---- 7r. The recipe tables of the whole chain ------------------------------------------------------------------------------

    static JsonArray pair(String id, int count) {
        JsonArray a = new JsonArray();
        a.add(id);
        a.add(count);
        return a;
    }

    static void chain() throws Exception {
        NtmConfig.COMMON.ENABLE_528.set(false);
        RecipesCommon.TAG_MEMBERS.clear();
        ArcFurnaceRecipes arcTable = new ArcFurnaceRecipes();
        arcTable.deleteRecipes();
        arcTable.registerDefaults();
        Items.SAND.tags.add("minecraft:sand");
        JsonObject facts = new JsonObject();

        // sand -> the arc furnace table
        ItemStack nuggets = ArcFurnaceRecipes.getSolidOutput(new ItemStack(Items.SAND));
        check(!nuggets.isEmpty(), "the arc furnace table smelts sand");
        facts.add("arc", pair(nuggets.getItem().id, nuggets.getCount()));

        // billet -> the press (the billet itself is crafted from 6 nuggets by the generated recipe, verify_goal13b.py joins that step)
        PressRecipes press = new PressRecipes();
        press.deleteRecipes();
        press.registerDefaults();
        ItemStack billet = new ItemStack(com.hbm.items.NtmItems.BILLET_SILICON.get());
        ItemStack wafer = PressRecipes.getOutput(billet, stamp(StampType.CIRCUIT));
        check(!wafer.isEmpty(), "the press makes a wafer from the silicon billet");
        facts.add("press", pair(wafer.getItem().id, wafer.getCount()));
        facts.addProperty("billet", billet.getItem().id);

        // ass.chip: the wafer is what the recipe asks for, with the polymer plate and gold wire
        AssemblyMachineRecipes.INSTANCE.deleteRecipes();
        GenericRecipes.clearPools();
        AssemblyMachineRecipes.INSTANCE.registerDefaults();
        GenericRecipe chip = AssemblyMachineRecipes.INSTANCE.recipeNameMap.get("ass.chip");
        ItemStack plate = new ItemStack(com.hbm.items.NtmItems.PLATE_POLYMER.get());
        ItemStack gold = new ItemStack(com.hbm.items.NtmItems.WIRE_GOLD.get());
        boolean accepts = chip.inputItem.length == 3;
        for(int i = 0; i < 3 && accepts; i++) {
            ItemStack given = new ItemStack[] { plate, wafer, gold }[i];
            accepts &= chip.inputItem[i].matchesRecipe(given, false);
        }
        check(accepts && !chip.inputItem[1].matchesRecipe(new ItemStack(com.hbm.items.NtmItems.BILLET_SILICON.get()), false),
                "ass.chip accepts the pressed wafer with a polymer plate and a gold wire in its three slots, and not the unpressed billet");
        ItemStack chipOut = chip.outputItem[0].getSingle();
        facts.add("chip", pair(chipOut.getItem().id, chipOut.getCount()));
        JsonArray chipInputs = new JsonArray();
        for(AStack input : chip.inputItem) chipInputs.add(pair(((ComparableStack) input).item.id, input.stacksize));
        facts.add("chipInputs", chipInputs);

        // the soldering station: BASIC circuit from 4 chips + 4 PCBs + 4 lead wire
        SolderingRecipes soldering = new SolderingRecipes();
        soldering.deleteRecipes();
        soldering.registerDefaults();
        ItemStack[] slots = {
                new ItemStack(chipOut.getItem(), 4), ItemStack.EMPTY, ItemStack.EMPTY,
                new ItemStack(com.hbm.items.NtmItems.CIRCUIT_PRINTED_BOARD.get(), 4), ItemStack.EMPTY,
                new ItemStack(com.hbm.items.NtmItems.WIRE_LEAD.get(), 4) };
        SolderingRecipe basic = SolderingRecipes.getRecipe(slots);
        check(basic != null && basic.output.getItem() == com.hbm.items.NtmItems.CIRCUIT_INTEGRATED_BOARD.get() && basic.output.getCount() == 1 && basic.duration == 200 && basic.consumption == 250
                        && basic.fluid == null,
                "4 microchips + 4 printed boards + 4 lead wires solder to 1 integrated circuit board in 200 ticks at 250 HE/t, no flux (original SolderingRecipes.java:54-61)");
        slots[0] = new ItemStack(chipOut.getItem(), 3);
        check(SolderingRecipes.getRecipe(slots) == null, "three microchips are not enough");
        facts.add("soldering", pair(basic.output.getItem().id, basic.output.getCount()));

        Files.writeString(work.resolve("chain.json"), facts.toString(), StandardCharsets.UTF_8);
        info("chain: sand -> " + facts.get("arc") + " nuggets, billet -> " + facts.get("press") + ", ass.chip -> " + facts.get("chip") + ", soldering -> " + facts.get("soldering"));
    }

    public static void main(String[] args) {
        work = Path.of(args[0]);
        try {
            Files.createDirectories(work);
        } catch(java.io.IOException e) {
            throw new IllegalStateException(e);
        }
        run("3b. ass.chip and ass.arcfurnace", Goal13BRecipeRegression::assembler);
        run("4. arc furnace table", Goal13BRecipeRegression::arcFurnace);
        run("6b. silicon billet in the press", Goal13BRecipeRegression::press);
        run("7r. chain tables", Goal13BRecipeRegression::chain);
        System.out.println("Goal 13B recipe world: " + checks + " checks passed");
        if(!failures.isEmpty()) {
            System.out.println("Goal 13B recipe world failed sections: " + failures);
            System.exit(1);
        }
    }
}
