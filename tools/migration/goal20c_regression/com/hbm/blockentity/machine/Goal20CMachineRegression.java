package com.hbm.blockentity.machine;

import com.hbm.handler.FuelPoolRecipeClientSync;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.recipes.FuelPoolRecipes;
import com.hbm.inventory.recipes.FuelPoolRecipes.FuelPoolRecipe;
import com.hbm.main.NuclearTechMod;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.RandomSource;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.material.Fluid;
import net.minecraft.world.level.material.Fluids;
import net.neoforged.neoforge.client.event.ClientPlayerNetworkEvent;

import java.io.Reader;
import java.io.StringReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

/**
 * Goal20C isolated regression: the production FuelPoolRecipes (defaults, strict snapshot reader, lenient config-file path, snapshot round trip),
 * the production FuelPoolRecipeClientSync, and the production MachineWasteDrumBlockEntity (slot rules, water counting, the decay loop with a
 * scripted RandomSource, and a seeded Monte Carlo of the cooling times) in the goal20c_regression/machine_stubs.py world. Expected values
 * (the default ids in the original order and r = 72000 / water) come from the original sources through expected.properties.
 *
 * args: output directory, expected.properties, sections ("all" or "deterministic").
 */
public final class Goal20CMachineRegression {

    private static int assertions;
    private static int scenarios;
    private static long ticks;
    private static Properties expected;
    private static Path output;

    private static void check(boolean condition, String label) {
        assertions++;
        if(!condition) throw new AssertionError(label);
    }

    public static void main(String[] args) throws Exception {
        output = Path.of(args[0]);
        expected = new Properties();
        try(Reader reader = Files.newBufferedReader(Path.of(args[1]), StandardCharsets.UTF_8)) { expected.load(reader); }
        String sections = args.length > 2 ? args[2] : "all";

        defaults();
        strictReader();
        lenientReader();
        snapshotRoundTrip();
        clientSync();
        drumRules();
        waterCount();
        decay();
        if(sections.equals("all")) monteCarlo();

        System.out.println(assertions + " assertions; " + scenarios + " independent scenarios; " + ticks + " executed ticks");
    }

    // ---- helpers -------------------------------------------------------------------------------------------------------------------------

    /** Reads a static int reflectively; javac would inline the constant from the unmutated class into this fixture. */
    private static int constant(Class<?> owner, String name) {
        try { return owner.getField(name).getInt(null); }
        catch(ReflectiveOperationException ex) { throw new AssertionError("missing constant " + owner.getSimpleName() + "." + name, ex); }
    }

    private static List<String> defaultIds() { return Arrays.asList(expected.getProperty("defaults").split(",")); }

    private static Item item(String id) {
        ResourceLocation key = ResourceLocation.parse(id);
        check(BuiltInRegistries.ITEM.containsKey(key), "the stand-in registry holds " + id);
        return BuiltInRegistries.ITEM.get(key);
    }

    private static ItemStack stack(String id, int meta) { return MetaHelper.newStack(item(id), 1, meta); }
    private static ItemStack hot(String id) { return stack(id, 1); }
    private static ItemStack cool(String id) { return stack(id, 0); }
    private static String key(FuelPoolRecipe recipe) { return BuiltInRegistries.ITEM.getKey(recipe.input) + ":" + recipe.inputMeta; }

    private static String json(String text) { return text.replace('\'', '"'); }
    private static String table(String... rows) { return json("{'recipes':[" + String.join(",", rows) + "]}"); }
    private static String row(String input, String output) { return "{'input':[" + input + "],'output':[" + output + "]}"; }

    /** `count` distinct stone inputs (META 0..count-1) in the shortest spelling the grammar allows. */
    private static String compactStoneTable(int count) {
        StringBuilder rows = new StringBuilder("{\"recipes\":[");
        for(int i = 0; i < count; i++) rows.append(i == 0 ? "" : ",").append("{\"input\":[\"stone\",1,").append(i).append("],\"output\":[\"stone\"]}");
        return rows.append("]}").toString();
    }

    private static void serverDefaults() {
        FuelPoolRecipes handler = new FuelPoolRecipes();
        handler.deleteRecipes();
        handler.registerDefaults();
    }

    private static void serverFile(String json) { new FuelPoolRecipes().readRecipeStream(new StringReader(json)); }

    private static void expectReject(String json, String fragment, String label) {
        try {
            FuelPoolRecipes.readSnapshot(json);
        } catch(IllegalArgumentException ex) {
            check(ex.getMessage() != null && ex.getMessage().startsWith("Fuel pool: ") && ex.getMessage().contains(fragment),
                    "strict reader rejects " + label + " with \"" + fragment + "\" (got: " + ex.getMessage() + ")");
            return;
        } catch(RuntimeException ex) {
            check(false, "strict reader rejects " + label + " with an IllegalArgumentException (got " + ex + ")");
        }
        check(false, "strict reader rejects " + label);
    }

    private static boolean sameRows(List<FuelPoolRecipe> a, List<FuelPoolRecipe> b) {
        if(a.size() != b.size()) return false;
        for(int i = 0; i < a.size(); i++) if(!a.get(i).sameRecipe(b.get(i))) return false;
        return true;
    }

    private static MachineWasteDrumBlockEntity drum(Level level) {
        MachineWasteDrumBlockEntity be = new MachineWasteDrumBlockEntity(new BlockPos(0, 64, 0), null);
        be.level = level;
        return be;
    }

    private static Level levelWithWater(int water, Fluid fluid) {
        Level level = new Level();
        BlockPos pos = new BlockPos(0, 64, 0);
        Direction[] dirs = Direction.values();
        for(int i = 0; i < water; i++) level.fluids.put(pos.relative(dirs[i]), fluid);
        return level;
    }

    private static boolean isHot(ItemStack stack, String id) {
        return !stack.isEmpty() && stack.getItem() == item(id) && MetaHelper.getMeta(stack) == 1 && stack.getCount() == 1;
    }

    private static boolean isCool(ItemStack stack, String id) {
        return !stack.isEmpty() && stack.getItem() == item(id) && MetaHelper.getMeta(stack) == 0 && stack.metaPatch() == null && stack.getCount() == 1;
    }

    /** Records every bound and answers from a script, then a fallback (1: no cooling, 0: cooling). */
    private static final class ScriptedRandom implements RandomSource {
        final List<Integer> bounds = new ArrayList<>();
        final Deque<Integer> script = new ArrayDeque<>();
        final int fallback;
        ScriptedRandom(int fallback) { this.fallback = fallback; }
        @Override public int nextInt(int bound) {
            if(bound <= 0) throw new IllegalArgumentException("bound must be positive");
            bounds.add(bound);
            Integer value = script.poll();
            return value != null ? value : fallback;
        }
    }

    private static final class SeededRandom implements RandomSource {
        final Random random;
        SeededRandom(long seed) { random = new Random(seed); }
        @Override public int nextInt(int bound) { return random.nextInt(bound); }
    }

    // ---- 1. default table ----------------------------------------------------------------------------------------------------------------

    private static void defaults() {
        scenarios++;
        List<String> ids = defaultIds();
        List<FuelPoolRecipe> rows = FuelPoolRecipes.getDefaultRecipes();
        check(ids.size() == 9 && rows.size() == ids.size(), "the default table has the nine original ZIRNOX waste rows (FuelPoolRecipes.java:27-35), got " + rows.size());
        for(int i = 0; i < rows.size(); i++) {
            FuelPoolRecipe recipe = rows.get(i);
            String id = ids.get(i);
            check(key(recipe).equals(id + ":1"), "default row " + (i + 1) + " is " + id + " META 1 in the original order (got " + key(recipe) + ")");
            check(recipe.outputItem == recipe.input && recipe.outputCount == 1 && recipe.outputMeta == 0, "default row " + id + ": hot META 1 -> one cool META 0 of the same item");
            check(recipe.output().metaPatch() == null && MetaHelper.getMeta(recipe.output()) == 0, "default row " + id + ": the cool output carries no META patch (META 0 is the item default)");
            check(Integer.valueOf(1).equals(recipe.input().metaPatch()), "default row " + id + ": the displayed input carries META 1");
        }
        serverDefaults();
        check(sameRows(FuelPoolRecipes.getJeiRecipes(), rows), "registerDefaults fills the server table with exactly the nine default rows");
        for(String id : ids) {
            check(FuelPoolRecipes.isKey(hot(id)) && !FuelPoolRecipes.isKey(cool(id)), "hot " + id + " is a table input, cool " + id + " is not");
            check(!FuelPoolRecipes.isKey(stack(id, 2)), id + " META 2 is no input (exact META, no wildcard)");
        }
        String first = ids.get(0);
        check(FuelPoolRecipes.isKey(MetaHelper.newStack(item(first), 5, 1)), "the lookup ignores the stack count");
        check(!FuelPoolRecipes.isKey(ItemStack.EMPTY) && FuelPoolRecipes.getOutput(ItemStack.EMPTY) == null, "an empty stack is no input and has no output");
        check(!FuelPoolRecipes.isKey(hot("hbmsntm:nuclear_waste")), "another item with META 1 is no input");
        ItemStack out = FuelPoolRecipes.getOutput(hot(first));
        out.setCount(7);
        check(FuelPoolRecipes.getOutput(hot(first)).getCount() == 1, "getOutput returns a fresh copy of the row output");
    }

    // ---- 2. strict snapshot reader (sync and writeSnapshot self-check) --------------------------------------------------------------------

    private static void strictReader() {
        scenarios++;
        String good = row("'hbmsntm:waste_uranium',1,1", "'hbmsntm:waste_uranium',1,0");
        check(FuelPoolRecipes.readSnapshot(table(good)).size() == 1, "strict reader accepts a valid row");
        FuelPoolRecipe omitted = FuelPoolRecipes.readSnapshot(table(row("'hbmsntm:billet_nuclear_waste'", "'hbmsntm:nuclear_waste_vitrified'"))).get(0);
        check(omitted.inputMeta == 0 && omitted.outputCount == 1 && omitted.outputMeta == 0, "omitted count and META default to 1 and 0");
        FuelPoolRecipe edges = FuelPoolRecipes.readSnapshot(table(row("'hbmsntm:waste_uranium',1,32766", "'hbmsntm:waste_uranium',64,5"))).get(0);
        check(edges.inputMeta == 32766 && edges.outputCount == 64 && edges.outputMeta == 5, "META 32766 and output count 64 are accepted");
        check(FuelPoolRecipes.readSnapshot(table(good, row("'hbmsntm:waste_uranium',1,0", "'minecraft:stone'"))).size() == 2, "the same item with another META is a separate key");

        String out = "'hbmsntm:waste_uranium',1,0";
        expectReject(table(row("'hbmsntm:no_such_item',1,1", out)), "unknown item hbmsntm:no_such_item", "an unknown id");
        expectReject(table(row("'Hbmsntm:Waste_Uranium',1,1", out)), "invalid identifier Hbmsntm:Waste_Uranium", "an upper-case id");
        expectReject(table(row("'hbmsntm:waste_uranium',1,1", "'hbmsntm:waste uranium',1,0")), "invalid identifier hbmsntm:waste uranium", "an output id with a space");
        expectReject(table(row("'hbmsntm:waste_uranium',2,1", out)), "input count must be 1", "input count 2");
        expectReject(table(row("'hbmsntm:waste_uranium',0,1", out)), "input count must be 1", "input count 0");
        expectReject(table(row("'hbmsntm:waste_uranium',1,32767", out)), "input META must be 0..32766", "the 32767 wildcard");
        expectReject(table(row("'hbmsntm:waste_uranium',1,-1", out)), "input META must be 0..32766", "a negative input META");
        expectReject(table(row("'hbmsntm:waste_uranium',1,1", "'hbmsntm:waste_uranium',1,-1")), "output META must be nonnegative", "a negative output META");
        expectReject(table(row("'hbmsntm:waste_uranium',1,1", "'hbmsntm:waste_uranium',0,0")), "output count must be 1..64", "output count 0");
        expectReject(table(row("'hbmsntm:waste_uranium',1,1", "'hbmsntm:waste_uranium',65,0")), "output count must be 1..64", "output count 65");
        expectReject(table(row("'hbmsntm:waste_uranium',1,1,0", out)), "input array needs ID and optional count, META", "a four-element input");
        expectReject(table(row("'hbmsntm:waste_uranium',1,1", "'hbmsntm:waste_uranium',1,0,0")), "output array needs ID and optional count, META", "a four-element output");
        expectReject(table(row("", out)), "input array needs ID and optional count, META", "an empty input");
        expectReject(table(row("'minecraft:air',1,0", out)), "input item must be a real item", "an air input");
        expectReject(table(row("'hbmsntm:waste_uranium',1,1", "'hbmsntm:nothing',1,0")), "output item must be a real item", "the nothing placeholder as output");
        expectReject(table(row("'hbmsntm:waste_uranium','1',1", out)), "expected integer", "a string count");
        expectReject(table(row("'hbmsntm:waste_uranium',1,1.5", out)), "expected in-range integer", "a fractional META");
        expectReject(table(row("'hbmsntm:waste_uranium',1,1", out), row("'hbmsntm:waste_uranium',1,9999999999", out)), "expected in-range integer", "an out-of-range META");
        expectReject(table(row("5,1,1", out)), "expected string", "a numeric id");
        expectReject(table(json("{'input':['hbmsntm:waste_uranium',1,1]}")), "expected output array", "a missing output");
        expectReject(table("[1]"), "expected recipe object", "a row that is not an object");
        expectReject(table(good, good), "recipe 1: Fuel pool: duplicate input hbmsntm:waste_uranium:1", "a duplicate key");
        expectReject(json("{'rows':[]}"), "expected recipes array", "a table without recipes");
        expectReject("", "missing table object", "an empty document");
        StringBuilder many = new StringBuilder();
        for(int i = 0; i <= constant(FuelPoolRecipes.class, "MAX_SYNC_RECIPES"); i++) many.append(i == 0 ? "" : ",").append("{}");
        expectReject(json("{'recipes':[" + many + "]}"), "too many recipes", "4097 rows");
        expectReject("{\"recipes\":[],\"pad\":\"" + "x".repeat(constant(FuelPoolRecipes.class, "MAX_SYNC_BYTES")) + "\"}", "snapshot exceeds 256 KiB", "a snapshot over 256 KiB");
        expectReject("{\"recipes\":[],\"pad\":\"\uD800\"}", "malformed UTF-16 surrogate", "a lone surrogate");
        for(String broken : new String[] { "{\"recipes\":[", "null", "[]" }) {
            boolean rejected = false;
            try { FuelPoolRecipes.readSnapshot(broken); } catch(RuntimeException ex) { rejected = true; }
            check(rejected, "strict reader rejects the non-table document " + broken);
        }
    }

    // ---- 3. lenient config-file path -------------------------------------------------------------------------------------------------

    private static void lenientReader() throws Exception {
        scenarios++;
        serverDefaults();
        NuclearTechMod.LOGGER.errors.clear();
        String goodU = row("'hbmsntm:waste_uranium',1,1", "'hbmsntm:waste_uranium',1,0");
        String goodBillet = row("'hbmsntm:billet_nuclear_waste',1,0", "'hbmsntm:nuclear_waste_vitrified',1,0");
        try {
            serverFile(table(goodU,
                    row("'hbmsntm:no_such_item',1,1", "'hbmsntm:waste_uranium',1,0"),
                    row("'hbmsntm:waste_thorium',2,1", "'hbmsntm:waste_thorium',1,0"),
                    row("'hbmsntm:waste_mox',1,32767", "'hbmsntm:waste_mox',1,0"),
                    row("'hbmsntm:waste_uranium',1,1", "'hbmsntm:waste_uranium',1,0"),
                    row("'hbmsntm:waste_u233',1,1,0", "'hbmsntm:waste_u233',1,0"),
                    goodBillet));
        } catch(RuntimeException ex) {
            check(false, "the config-file path skips bad rows instead of failing the file (threw: " + ex.getMessage() + ")");
        }
        List<FuelPoolRecipe> live = FuelPoolRecipes.getJeiRecipes();
        check(live.size() == 2 && key(live.get(0)).equals("hbmsntm:waste_uranium:1") && key(live.get(1)).equals("hbmsntm:billet_nuclear_waste:0"),
                "the config-file path keeps the two valid rows and skips the five bad ones (got " + live.size() + ")");
        List<String> errors = NuclearTechMod.LOGGER.errors;
        check(errors.size() == 5, "each skipped row is logged once (got " + errors.size() + ")");
        for(int i = 0; i < errors.size(); i++) check(errors.get(i).startsWith("Skipping invalid recipe " + (i + 1) + " in hbmFuelpool.json"), "the skip log names row " + (i + 1) + ": " + errors.get(i));
        check(!FuelPoolRecipes.isKey(hot("hbmsntm:waste_thorium")), "a custom file replaces the whole table (the thorium default row is gone)");
        check(FuelPoolRecipes.isKey(stack("hbmsntm:billet_nuclear_waste", 0)), "an appended custom row is live");

        boolean failed = false;
        try { serverFile(json("{'rows':[]}")); } catch(IllegalArgumentException ex) { failed = ex.getMessage().contains("expected recipes array"); }
        check(failed && FuelPoolRecipes.getJeiRecipes().size() == 2, "a file without a recipes array fails as a whole and leaves the table unchanged");
        failed = false;
        try { serverFile("{\"recipes\":[],\"pad\":\"" + "x".repeat(constant(FuelPoolRecipes.class, "MAX_SYNC_BYTES")) + "\"}"); } catch(IllegalArgumentException ex) { failed = ex.getMessage().contains("exceeds 256 KiB"); }
        check(failed && FuelPoolRecipes.getJeiRecipes().size() == 2, "a file over 256 KiB fails as a whole and leaves the table unchanged");

        // 4096 compact rows ("stone" without namespace, output without count and META) stay under 256 KiB raw, but the canonical snapshot writes
        // minecraft:stone and explicit counts and METAs and does not fit, so the client could never receive it.
        String compact = compactStoneTable(constant(FuelPoolRecipes.class, "MAX_SYNC_RECIPES"));
        check(compact.length() < constant(FuelPoolRecipes.class, "MAX_SYNC_BYTES"), "the compact 4096 row file is under 256 KiB raw (" + compact.length() + " chars)");
        check(FuelPoolRecipes.readSnapshot(compact).size() == constant(FuelPoolRecipes.class, "MAX_SYNC_RECIPES"), "the strict reader accepts the compact 4096 row file");
        failed = false;
        try { serverFile(compact); } catch(IllegalArgumentException ex) { failed = ex.getMessage().contains("the canonical sync snapshot of this file exceeds 256 KiB"); }
        check(failed && FuelPoolRecipes.getJeiRecipes().size() == 2, "a compact file whose canonical snapshot exceeds 256 KiB is rejected and leaves the table unchanged");
        serverFile(compactStoneTable(1000));
        check(FuelPoolRecipes.getJeiRecipes().size() == 1000 && FuelPoolRecipes.writeSnapshot().length() < constant(FuelPoolRecipes.class, "MAX_SYNC_BYTES"),
                "a compact file whose canonical snapshot fits is accepted and its snapshot can be written");
        serverFile(table(goodU, goodBillet));

        serverFile(table());
        check(FuelPoolRecipes.getJeiRecipes().isEmpty(), "an empty custom table is accepted");
        for(String id : defaultIds()) check(!FuelPoolRecipes.isKey(hot(id)), "an empty table makes the drum accept nothing: " + id);

        String example = expected.getProperty("example", "");
        if(!example.isEmpty()) {
            scenarios++;
            String text = Files.readString(Path.of(example), StandardCharsets.UTF_8);
            NuclearTechMod.LOGGER.errors.clear();
            serverFile(text);
            List<FuelPoolRecipe> rows = FuelPoolRecipes.getJeiRecipes();
            check(rows.size() == 10 && NuclearTechMod.LOGGER.errors.isEmpty(), "the custom example loads ten rows on the config-file path, none skipped (got " + rows.size() + ")");
            check(sameRows(rows.subList(0, 9), FuelPoolRecipes.getDefaultRecipes()), "example rows 1-9 equal the default table");
            FuelPoolRecipe tenth = rows.get(9);
            check(key(tenth).equals("hbmsntm:billet_nuclear_waste:0") && BuiltInRegistries.ITEM.getKey(tenth.outputItem).toString().equals("hbmsntm:nuclear_waste_vitrified")
                    && tenth.outputCount == 1 && tenth.outputMeta == 0, "example row 10 cools a nuclear waste billet into one vitrified nuclear waste");
            check(tenth.output().metaPatch() == null, "a plain item output with META 0 carries no META patch, so it stacks with ordinary items");
            check(sameRows(FuelPoolRecipes.readSnapshot(text), rows), "the strict reader accepts the example with the same rows");
        }
        serverDefaults();
    }

    // ---- 4. snapshot round trip ----------------------------------------------------------------------------------------------------

    private static void snapshotRoundTrip() throws Exception {
        scenarios++;
        serverDefaults();
        String snapshot = FuelPoolRecipes.writeSnapshot();
        check(sameRows(FuelPoolRecipes.readSnapshot(snapshot), FuelPoolRecipes.getDefaultRecipes()), "the default snapshot reads back as the nine default rows");
        check(snapshot.startsWith("{\"recipes\":[{\"input\":[\"" + defaultIds().get(0) + "\",1,1],\"output\":[\"" + defaultIds().get(0) + "\",1,0]}"),
                "writeSnapshot writes [id, 1, META] inputs and [id, count, META] outputs: " + snapshot.substring(0, Math.min(120, snapshot.length())));
        check(Arrays.equals(FuelPoolRecipes.encodeSnapshot(snapshot), snapshot.getBytes(StandardCharsets.UTF_8)), "the snapshot encodes as UTF-8");
        serverFile(table(row("'hbmsntm:waste_uranium',1,1", "'hbmsntm:waste_uranium',3,0"), row("'minecraft:stone'", "'hbmsntm:nuclear_waste',1,7")));
        List<FuelPoolRecipe> custom = FuelPoolRecipes.getJeiRecipes();
        check(sameRows(FuelPoolRecipes.readSnapshot(FuelPoolRecipes.writeSnapshot()), custom), "a custom table (output count 3, a vanilla input, output META 7) round-trips");
        serverDefaults();
    }

    // ---- 5. client sync --------------------------------------------------------------------------------------------------------------

    private static void clientSync() throws Exception {
        scenarios++;
        FuelPoolRecipeClientSync.disconnect(new ClientPlayerNetworkEvent.LoggingOut());
        int[] refreshed = { 0 };
        FuelPoolRecipeClientSync.setRefresh(() -> refreshed[0]++);
        serverFile(table(row("'hbmsntm:billet_nuclear_waste',1,0", "'hbmsntm:nuclear_waste_vitrified',1,0")));
        check(sameRows(FuelPoolRecipeClientSync.getRecipes(), FuelPoolRecipes.getDefaultRecipes()), "before any packet the client shows the default table, not the server memory");
        boolean accepted = FuelPoolRecipeClientSync.receive(FuelPoolRecipes.writeSnapshot());
        check(accepted && refreshed[0] == 1, "a valid snapshot is accepted and refreshes JEI once");
        check(FuelPoolRecipeClientSync.getRecipes().size() == 1 && FuelPoolRecipeClientSync.isKey(stack("hbmsntm:billet_nuclear_waste", 0))
                && !FuelPoolRecipeClientSync.isKey(hot(defaultIds().get(0))), "the client table is the received snapshot");
        NuclearTechMod.LOGGER.errors.clear();
        accepted = FuelPoolRecipeClientSync.receive(table(row("'hbmsntm:waste_uranium',2,1", "'hbmsntm:waste_uranium',1,0")));
        check(!accepted && refreshed[0] == 1 && FuelPoolRecipeClientSync.getRecipes().size() == 1, "an invalid snapshot (input count 2) is rejected whole and the previous table kept");
        check(NuclearTechMod.LOGGER.errors.size() == 1 && NuclearTechMod.LOGGER.errors.get(0).startsWith("Ignoring invalid fuel pool snapshot"), "the rejected snapshot is logged");
        accepted = FuelPoolRecipeClientSync.receive(table());
        check(accepted && FuelPoolRecipeClientSync.getRecipes().isEmpty() && !FuelPoolRecipeClientSync.isKey(hot(defaultIds().get(0))), "an empty received table is authoritative");
        FuelPoolRecipeClientSync.receive(FuelPoolRecipes.writeSnapshot());
        FuelPoolRecipeClientSync.getRecipes().clear();
        check(FuelPoolRecipeClientSync.getRecipes().size() == 1, "getRecipes hands out a copy; display code cannot change the snapshot");
        int before = refreshed[0];
        FuelPoolRecipeClientSync.disconnect(new ClientPlayerNetworkEvent.LoggingOut());
        check(refreshed[0] == before + 1 && sameRows(FuelPoolRecipeClientSync.getRecipes(), FuelPoolRecipes.getDefaultRecipes()), "logging out drops the snapshot and refreshes");
        FuelPoolRecipeClientSync.setRefresh(null);
        serverDefaults();
    }

    // ---- 6. drum slot rules ----------------------------------------------------------------------------------------------------------

    private static void drumRules() throws Exception {
        scenarios++;
        serverDefaults();
        MachineWasteDrumBlockEntity be = drum(new Level());
        check(constant(MachineWasteDrumBlockEntity.class, "SLOT_COUNT") == 12 && be.getContainerSize() == 12, "12 slots (TileEntityWasteDrum.java:32)");
        check(be.getMaxStackSize() == 1, "stack limit 1 (TileEntityWasteDrum.java:82-84), got " + be.getMaxStackSize());
        check(constant(MachineWasteDrumBlockEntity.class, "DECAY_TICKS") == Integer.parseInt(expected.getProperty("decay")), "DECAY_TICKS equals the original 60 * 60 * 20 = " + expected.getProperty("decay"));
        check(be.defaultName().key.equals("container.machine_waste_drum"), "the default name is container.machine_waste_drum");
        int[] all = { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 };
        for(Direction dir : Direction.values()) check(Arrays.equals(be.getSlotsForFace(dir), all), "face " + dir + " exposes slots 0..11 (TileEntityWasteDrum.java:173-175)");
        String other = "hbmsntm:nuclear_waste";
        for(String id : defaultIds()) {
            for(int slot = 0; slot < 12; slot++) {
                check(be.canPlaceItem(slot, hot(id)) && !be.canPlaceItem(slot, cool(id)), "slot " + slot + " takes hot " + id + " and refuses cool");
            }
            for(Direction dir : Direction.values()) check(be.canPlaceItemThroughFace(3, hot(id), dir) && !be.canPlaceItemThroughFace(3, cool(id), dir), "automation inserts hot " + id + " only, face " + dir);
            check(be.canPlaceItemThroughFace(3, hot(id), null), "a null face inserts hot " + id);
        }
        check(!be.canPlaceItem(0, ItemStack.EMPTY) && !be.canPlaceItem(0, hot(other)) && !be.canPlaceItem(0, cool(other)), "empty stacks and non-table items are refused");

        String id = defaultIds().get(1);
        be.slots.set(0, hot(id));
        be.slots.set(1, cool(id));
        be.slots.set(2, new ItemStack(item("minecraft:stone")));
        for(Direction dir : Direction.values()) {
            check(!be.canTakeItemThroughFace(0, cool(id), dir), "automation cannot take the hot waste in slot 0 through " + dir + " (the rule reads the slot content, :187)");
            check(be.canTakeItemThroughFace(1, cool(id), dir), "automation takes cooled waste through " + dir);
            check(be.canTakeItemThroughFace(2, ItemStack.EMPTY, dir), "automation takes a non-table item through " + dir);
            check(be.canTakeItemThroughFace(3, ItemStack.EMPTY, dir), "an empty slot is not blocked, face " + dir);
        }
        // A vanilla hopper merges up to the item's own max stack size and ignores getMaxStackSize (a GameTest stacked 14 into slot 0), so the
        // automation rule itself must refuse every filled slot.
        for(Direction dir : Direction.values()) {
            check(!be.canPlaceItemThroughFace(0, hot(id), dir), "automation does not insert into a filled slot: hot waste in slot 0, face " + dir);
            check(!be.canPlaceItemThroughFace(1, hot(id), dir), "automation does not insert into a filled slot: cool waste in slot 1, face " + dir);
            check(!be.canPlaceItemThroughFace(2, hot(id), dir), "automation does not insert into a filled slot: stone in slot 2, face " + dir);
            check(be.canPlaceItemThroughFace(3, hot(id), dir), "automation still fills the empty slot 3, face " + dir);
        }
        check(!be.canPlaceItemThroughFace(0, hot(id), null) && be.canPlaceItemThroughFace(3, hot(id), null), "a null face follows the same empty-slot rule");
        check(be.canPlaceItem(0, hot(id)), "the GUI rule canPlaceItem is unchanged by the automation guard (the slot limit of 1 applies there)");

        // The client asks the synced table, so a custom server table shows the same placement rules.
        Level client = new Level();
        client.isClientSide = true;
        MachineWasteDrumBlockEntity clientBe = drum(client);
        FuelPoolRecipeClientSync.disconnect(new ClientPlayerNetworkEvent.LoggingOut());
        serverFile(table(row("'hbmsntm:billet_nuclear_waste',1,0", "'hbmsntm:nuclear_waste_vitrified',1,0")));
        check(clientBe.canPlaceItem(0, hot(id)) && !clientBe.canPlaceItem(0, stack("hbmsntm:billet_nuclear_waste", 0)), "without a snapshot the client drum uses the default table");
        FuelPoolRecipeClientSync.receive(FuelPoolRecipes.writeSnapshot());
        check(!clientBe.canPlaceItem(0, hot(id)) && clientBe.canPlaceItem(0, stack("hbmsntm:billet_nuclear_waste", 0)), "with a snapshot the client drum uses the received table");
        check(!be.canPlaceItem(0, hot(id)) && be.canPlaceItem(0, stack("hbmsntm:billet_nuclear_waste", 0)), "the server drum uses the server table");
        FuelPoolRecipeClientSync.disconnect(new ClientPlayerNetworkEvent.LoggingOut());
        serverDefaults();
    }

    // ---- 7. water counting -----------------------------------------------------------------------------------------------------------

    private static void waterCount() {
        scenarios++;
        BlockPos pos = new BlockPos(0, 64, 0);
        check(drum(new Level()).countWater() == 0, "no fluid around: 0 water");
        for(Direction dir : Direction.values()) {
            for(Fluid fluid : new Fluid[] { Fluids.WATER, Fluids.FLOWING_WATER }) {
                Level level = new Level();
                level.fluids.put(pos.relative(dir), fluid);
                check(drum(level).countWater() == 1, fluid + " on " + dir + " counts once (all six directions, :198-202; waterlogged blocks report the water fluid)");
            }
            for(Fluid fluid : new Fluid[] { Fluids.LAVA, Fluids.FLOWING_LAVA }) {
                Level level = new Level();
                level.fluids.put(pos.relative(dir), fluid);
                check(drum(level).countWater() == 0, fluid + " on " + dir + " is no water");
            }
        }
        check(drum(levelWithWater(6, Fluids.WATER)).countWater() == 6, "six water neighbours count 6");
        Level mixed = new Level();
        Direction[] dirs = Direction.values();
        for(int i = 0; i < 3; i++) mixed.fluids.put(pos.relative(dirs[i]), Fluids.WATER);
        for(int i = 3; i < 5; i++) mixed.fluids.put(pos.relative(dirs[i]), Fluids.FLOWING_WATER);
        mixed.fluids.put(pos.relative(dirs[5]), Fluids.LAVA);
        check(drum(mixed).countWater() == 5, "3 water + 2 flowing water + 1 lava count 5");
        Level unloaded = levelWithWater(6, Fluids.WATER);
        unloaded.unloaded.add(pos.relative(Direction.UP));
        unloaded.unloaded.add(pos.relative(Direction.EAST));
        check(drum(unloaded).countWater() == 4 && unloaded.unloadedReads.isEmpty(), "unloaded neighbours count as no water and are never read");
    }

    // ---- 8. decay loop ---------------------------------------------------------------------------------------------------------------

    private static void fill(MachineWasteDrumBlockEntity be, String id) { for(int i = 0; i < 12; i++) be.slots.set(i, hot(id)); }

    private static void decay() {
        serverDefaults();
        String id = defaultIds().get(0);

        scenarios++;
        MachineWasteDrumBlockEntity dry = drum(new Level());
        ScriptedRandom always = new ScriptedRandom(0);
        dry.setDecayRandom(always);
        fill(dry, id);
        for(int t = 0; t < 20000; t++) dry.updateEntity();
        ticks += 20000;
        boolean allHot = true;
        for(int i = 0; i < 12; i++) allHot &= isHot(dry.getItem(i), id);
        check(always.bounds.isEmpty() && allHot && dry.setChangedCalls == 0, "no water: 20,000 ticks, no roll, no cooling, never marked dirty");

        for(int water = 1; water <= 6; water++) {
            scenarios++;
            int r = Integer.parseInt(expected.getProperty("r." + water));
            MachineWasteDrumBlockEntity be = drum(levelWithWater(water, Fluids.WATER));
            ScriptedRandom random = new ScriptedRandom(1);
            be.setDecayRandom(random);
            fill(be, id);
            be.updateEntity();
            ticks++;
            check(random.bounds.size() == 12, water + " water: each of the 12 filled slots rolls once per tick (got " + random.bounds.size() + ")");
            for(int bound : random.bounds) check(bound == r, water + " water: the roll is nextInt(" + r + ") = 72000 / " + water + " (got " + bound + ")");
            check(be.setChangedCalls == 0, water + " water: a tick without a cooled slot does not mark the drum dirty");
            int target = water % 12;
            for(int i = 0; i < 12; i++) random.script.add(i == target ? 0 : 1);
            be.updateEntity();
            ticks++;
            for(int i = 0; i < 12; i++) {
                if(i == target) check(isCool(be.getItem(i), id), water + " water: the slot that rolled 0 now holds one cool " + id + " without a META patch");
                else check(isHot(be.getItem(i), id), water + " water: slot " + i + " (rolled 1) is still hot");
            }
            check(be.setChangedCalls == 1, water + " water: the cooling tick marks the drum dirty once (NEO-only setChanged)");
        }

        scenarios++;
        MachineWasteDrumBlockEntity sparse = drum(levelWithWater(1, Fluids.WATER));
        ScriptedRandom sparseRandom = new ScriptedRandom(1);
        sparse.setDecayRandom(sparseRandom);
        for(int i = 0; i < 12; i += 2) if(i < 10) sparse.slots.set(i, hot(id));
        sparse.updateEntity();
        ticks++;
        check(sparseRandom.bounds.size() == 5, "only the five filled slots roll; empty slots do not (got " + sparseRandom.bounds.size() + ")");

        scenarios++;
        MachineWasteDrumBlockEntity cooled = drum(levelWithWater(2, Fluids.FLOWING_WATER));
        ScriptedRandom cooledRandom = new ScriptedRandom(0);
        cooled.setDecayRandom(cooledRandom);
        cooled.slots.set(0, cool(id));
        cooled.slots.set(5, new ItemStack(item("minecraft:stone")));
        cooled.updateEntity();
        ticks++;
        check(cooledRandom.bounds.size() == 2, "cool waste and other items roll too, like the original (every non-null slot), got " + cooledRandom.bounds.size());
        check(isCool(cooled.getItem(0), id) && cooled.getItem(5).getItem() == item("minecraft:stone") && cooled.setChangedCalls == 0,
                "a roll of 0 on a non-input changes nothing and does not mark the drum dirty");

        scenarios++;
        Level clientLevel = levelWithWater(6, Fluids.WATER);
        clientLevel.isClientSide = true;
        MachineWasteDrumBlockEntity client = drum(clientLevel);
        ScriptedRandom clientRandom = new ScriptedRandom(0);
        client.setDecayRandom(clientRandom);
        fill(client, id);
        for(int t = 0; t < 100; t++) client.updateEntity();
        ticks += 100;
        check(clientRandom.bounds.isEmpty() && isHot(client.getItem(0), id), "the client never rolls or cools (server authority, :194)");

        scenarios++;
        MachineWasteDrumBlockEntity full = drum(levelWithWater(6, Fluids.WATER));
        full.setDecayRandom(new ScriptedRandom(0));
        fill(full, id);
        full.updateEntity();
        ticks++;
        boolean allCool = true;
        for(int i = 0; i < 12; i++) allCool &= isCool(full.getItem(i), id);
        check(allCool && full.setChangedCalls == 1, "twelve slots cooling in one tick mark the drum dirty once");
        full.getItem(0).setCount(9);
        check(full.getItem(1).getCount() == 1 && FuelPoolRecipes.getOutput(hot(id)).getCount() == 1, "each cooled slot holds its own stack");

        scenarios++;
        serverFile(table(row("'" + id + "',1,1", "'" + id + "',3,0")));
        MachineWasteDrumBlockEntity triple = drum(levelWithWater(1, Fluids.WATER));
        triple.setDecayRandom(new ScriptedRandom(0));
        triple.slots.set(4, hot(id));
        triple.updateEntity();
        ticks++;
        check(isCool(triple.getItem(4), id), "a custom row with output count 3 still leaves one item in the slot (got " + triple.getItem(4) + ")");
        serverDefaults();

        scenarios++;
        Level shared = levelWithWater(3, Fluids.WATER);
        ScriptedRandom levelRandom = new ScriptedRandom(1);
        shared.random = levelRandom;
        MachineWasteDrumBlockEntity plain = drum(shared);
        plain.slots.set(0, hot(id));
        plain.updateEntity();
        ScriptedRandom hook = new ScriptedRandom(1);
        plain.setDecayRandom(hook);
        plain.updateEntity();
        plain.setDecayRandom(null);
        plain.updateEntity();
        ticks += 3;
        check(levelRandom.bounds.size() == 2 && hook.bounds.size() == 1, "the level random rolls unless setDecayRandom replaced it; null restores it");
    }

    // ---- 9. seeded Monte Carlo of the cooling times ----------------------------------------------------------------------------------

    private static void monteCarlo() throws Exception {
        serverDefaults();
        String id = defaultIds().get(0);
        int drums = Integer.parseInt(expected.getProperty("mc.drums"));
        long seed = Long.parseLong(expected.getProperty("mc.seed"));
        StringBuilder out = new StringBuilder("{");
        for(int water = 1; water <= 6; water++) {
            scenarios++;
            int r = Integer.parseInt(expected.getProperty("r." + water));
            long cap = 60L * r;
            List<Long> slotTimes = new ArrayList<>();
            List<Long> drumTimes = new ArrayList<>();
            long executed = 0;
            for(int d = 0; d < drums; d++) {
                MachineWasteDrumBlockEntity be = drum(levelWithWater(water, Fluids.WATER));
                be.setDecayRandom(new SeededRandom(seed + 1000L * water + d));
                fill(be, id);
                long[] first = new long[12];
                Arrays.fill(first, -1);
                int left = 12;
                long t = 0;
                while(left > 0 && t < cap) {
                    t++;
                    be.updateEntity();
                    for(int i = 0; i < 12; i++) {
                        if(first[i] < 0 && !FuelPoolRecipes.isKey(be.getItem(i))) {
                            check(isCool(be.getItem(i), id), "a cooled slot holds one cool " + id);
                            first[i] = t;
                            left--;
                        }
                    }
                }
                check(left == 0, water + " water: drum " + d + " cooled all twelve slots within " + cap + " ticks");
                executed += t;
                for(long f : first) slotTimes.add(f);
                drumTimes.add(t);
            }
            ticks += executed;
            out.append(water == 1 ? "" : ",").append("\"").append(water).append("\":{\"r\":").append(r).append(",\"drums\":").append(drums)
                    .append(",\"executed_ticks\":").append(executed).append(",\"slot_times\":").append(slotTimes).append(",\"drum_times\":").append(drumTimes).append("}");
        }
        out.append("}");
        Files.writeString(output.resolve("monte-carlo.json"), out.toString(), StandardCharsets.UTF_8);
    }
}
