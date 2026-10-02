package goal10b;

import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.NtmTags;
import com.hbm.inventory.RecipesCommon;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.recipes.anvil.AnvilRecipes;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.AnvilConstructionRecipe;
import com.hbm.inventory.recipes.anvil.AnvilRecipes.OverlayType;
import com.hbm.inventory.recipes.anvil.AnvilSmithingRecipe;
import com.hbm.items.BoltItem;
import com.hbm.items.CastPlateItem;
import com.hbm.items.NtmItems;
import net.minecraft.world.item.ItemStack;

import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.List;

/**
 * Section 1: the live anvil lists against the committed (pre-Goal 10B) AnvilRecipes, compiled as goal10b.head.
 * Expected values come from the original at 608fec4: AnvilRecipes.java:383-389 (the soldering station: 2 steel cast
 * plates, 4 copper coils, 4 tungsten bolts, 2 vacuum tubes, tier 2) and :592-598 (each flat stamp makes its own
 * plate/wire/circuit stamp, tier 2 for steel and titanium).
 */
public class Goal10BAnvilRegression {
    private static int checks;
    private static int sectionChecks;
    private static final List<String> failures = new ArrayList<>();

    private static void check(boolean condition, String message) {
        checks++;
        sectionChecks++;
        if(!condition) throw new AssertionError(message);
    }

    private static void section(String name) {
        System.out.println(name + ": " + sectionChecks + " checks passed");
        sectionChecks = 0;
    }

    private static void run(String name, Runnable body) {
        try {
            body.run();
        } catch(AssertionError e) {
            System.out.println("AssertionError in " + name + " after " + (sectionChecks - 1) + " passed checks: " + e.getMessage());
            failures.add(name + ": " + e.getMessage());
            checks--;
            sectionChecks = 0;
        }
    }

    static String stack(ItemStack s) {
        return s.isEmpty() ? "empty" : s.getItem().id + " x" + s.getCount() + " meta " + MetaHelper.getMeta(s);
    }

    static String astack(Object in) {
        if(in instanceof AStack a) return a.getClass().getSimpleName() + " " + a.item.id + " x" + a.stacksize + " meta " + a.meta;
        return in.getClass().getName();
    }

    /** A construction entry of either list (live or goal10b.head: distinct classes, read reflectively). */
    static String describe(Object recipe) {
        try {
            Class<?> c = recipe.getClass();
            StringBuilder b = new StringBuilder();
            for(Object in : (List<?>) c.getField("input").get(recipe)) b.append(astack(in)).append("; ");
            b.append("-> ");
            for(Object out : (List<?>) c.getField("output").get(recipe)) {
                b.append(stack((ItemStack) out.getClass().getField("stack").get(out))).append(" @").append(out.getClass().getField("chance").get(out)).append("; ");
            }
            return b.append("tier ").append(c.getField("tierLower").get(recipe)).append('-').append(c.getField("tierUpper").get(recipe))
                    .append(' ').append(c.getMethod("getOverlay").invoke(recipe)).toString();
        } catch(ReflectiveOperationException e) {
            throw new AssertionError("cannot describe " + recipe, e);
        }
    }

    static String smithing(AnvilSmithingRecipe recipe) {
        try {
            Field left = AnvilSmithingRecipe.class.getDeclaredField("left"), right = AnvilSmithingRecipe.class.getDeclaredField("right");
            left.setAccessible(true);
            right.setAccessible(true);
            return recipe.getClass().getSimpleName() + " tier " + recipe.getTier() + (recipe.isShapeless() ? " shapeless" : "")
                    + ": " + astack(left.get(recipe)) + " + " + astack(right.get(recipe)) + " -> " + stack(recipe.getSimpleOutput());
        } catch(ReflectiveOperationException e) {
            throw new AssertionError("cannot describe " + recipe, e);
        }
    }

    /** The committed descriptor with the Goal 10B decisions applied (D1: 4 tungsten bolts; D6: each flat makes its own stamps). */
    static String goal10b(String before) {
        if(before.contains("-> MACHINE_SOLDERING_STATION x1 ") && before.endsWith(" CONSTRUCTION"))
            return before.replace("ComparableStack BOLT x1 meta ", "ComparableStack BOLT x4 meta ");
        if(before.startsWith("ComparableStack STAMP_TITANIUM_FLAT x1 ")) return before.replace("-> STAMP_STEEL_", "-> STAMP_TITANIUM_");
        if(before.startsWith("ComparableStack STAMP_STEEL_FLAT x1 ")) return before.replace("-> STAMP_TITANIUM_", "-> STAMP_STEEL_");
        return before;
    }

    /**
     * Goal 10C (migration/GOAL10C.md) appends three heating oven entries after the committed list (original
     * AnvilRecipes.java:269-274 and :672-678): construction with Minecraft copper, with NEO copper, and the recycling.
     * They are required exactly, in this order; the Goal 10C suite checks them in detail. The tag input is described
     * through astack() of the same tag, as the stand-in tag item's name is only fixed within one run.
     */
    static String[] goal10c() {
        String plates = astack(new RecipesCommon.TagStack(NtmTags.Items.PLATES_STEEL, 4));
        return new String[] {
                "ComparableStack INGOT_FIREBRICK x16 meta -1; " + plates + "; ComparableStack COPPER_INGOT x8 meta -1; -> HEATER_OVEN x1 meta 0 @1.0; tier 2--1 CONSTRUCTION",
                "ComparableStack INGOT_FIREBRICK x16 meta -1; " + plates + "; ComparableStack INGOT_COPPER x8 meta -1; -> HEATER_OVEN x1 meta 0 @1.0; tier 2--1 CONSTRUCTION",
                "ComparableStack HEATER_OVEN x1 meta -1; -> INGOT_FIREBRICK x16 meta 0 @1.0; INGOT_COPPER x8 meta 0 @1.0; tier 2--1 RECYCLING",
        };
    }

    static void anvil() {
        List<AnvilConstructionRecipe> live = AnvilRecipes.getConstruction();
        List<?> head = goal10b.head.AnvilRecipes.getConstruction();
        String[] appended = goal10c();
        check(live.size() == head.size() + appended.length && live.size() > 0, "the committed construction entries, then the three Goal 10C entries ("
                + head.size() + " -> " + live.size() + ")");
        boolean goal10c = true;
        for(int k = 0; k < appended.length; k++) goal10c &= describe(live.get(head.size() + k)).equals(appended[k]);
        check(goal10c, "exactly the three Goal 10C heating oven entries follow the committed list, in order");
        List<Integer> corrected = new ArrayList<>();
        int same = 0;
        String first = null;
        for(int i = 0; i < head.size(); i++) {
            String before = describe(head.get(i)), expected = goal10b(before), now = describe(live.get(i));
            if(!expected.equals(before)) corrected.add(i);
            if(now.equals(expected)) same++;
            else if(first == null) first = i + ": " + now + " != " + expected;
        }
        check(same == head.size(), "every construction entry equals the committed one at the same index, with only the Goal 10B corrections"
                + (first == null ? "" : "; first difference " + first));
        check(corrected.size() == 7, "exactly seven entries change: the soldering station and six stamp conversions (" + corrected + ")");

        List<AnvilSmithingRecipe> smithLive = AnvilRecipes.getSmithing();
        List<AnvilSmithingRecipe> smithHead = goal10b.head.AnvilRecipes.getSmithing();
        boolean smithSame = smithLive.size() == smithHead.size() && smithLive.size() > 0;
        for(int i = 0; smithSame && i < smithLive.size(); i++) smithSame = smithing(smithLive.get(i)).equals(smithing(smithHead.get(i)));
        check(smithSame, "the smithing list is unchanged entry by entry (" + smithHead.size() + " entries)");

        // The soldering station entry itself (NEO keeps its own input order: tube, coil, cast plate, bolt).
        int station = -1, found = 0;
        for(int i = 0; i < live.size(); i++) {
            AnvilConstructionRecipe r = live.get(i);
            if(r.output.size() == 1 && r.output.get(0).stack.is(NtmBlocks.MACHINE_SOLDERING_STATION.asItem())) {
                station = i;
                found++;
            }
        }
        check(found == 1 && corrected.get(0) == station, "one soldering station entry; it is the first corrected index (" + station + ")");
        AnvilConstructionRecipe r = live.get(station);
        int steel = CastPlateItem.Type.STEEL.ordinal();
        check(steel == 11 && BoltItem.Type.TUNGSTEN.meta == 7400, "production META: STEEL cast plate 11 (the ordinal), tungsten bolt 7400");
        List<AStack> in = r.input;
        check(in.size() == 4
                        && in.get(0).item == NtmItems.CIRCUIT_VACUUM_TUBE.get() && in.get(0).stacksize == 2 && in.get(0).meta < 0
                        && in.get(1).item == NtmItems.COIL_COPPER.get() && in.get(1).stacksize == 4 && in.get(1).meta < 0
                        && in.get(2).item == NtmItems.CAST_PLATE.get() && in.get(2).stacksize == 2 && in.get(2).meta == steel
                        && in.get(3).item == NtmItems.BOLT.get() && in.get(3).stacksize == 4 && in.get(3).meta == BoltItem.Type.TUNGSTEN.meta,
                "inputs: 2 vacuum tubes, 4 copper coils, 2 steel cast plates (META " + steel + "), 4 tungsten bolts (META 7400); got " + describe(r));
        check(r.output.size() == 1 && r.output.get(0).stack.getCount() == 1 && r.output.get(0).chance == 1F && MetaHelper.getMeta(r.output.get(0).stack) == 0,
                "output: one plain soldering station");
        check(r.tierLower == 2 && r.tierUpper == -1 && r.isTierValid(2) && !r.isTierValid(1) && r.getOverlay() == OverlayType.CONSTRUCTION,
                "tier 2 and up, construction overlay");
        check(describe(head.get(station)).equals(describe(r).replace("BOLT x4 ", "BOLT x1 ")), "the committed entry differed only in the bolt count (1)");

        // The six stamp conversions: same indices, tier 2, each flat stamp now makes its own material's stamps.
        String[][] stamps = {
                {"STAMP_TITANIUM_FLAT", "STAMP_TITANIUM_PLATE", "STAMP_STEEL_PLATE"},
                {"STAMP_STEEL_FLAT", "STAMP_STEEL_PLATE", "STAMP_TITANIUM_PLATE"},
                {"STAMP_TITANIUM_FLAT", "STAMP_TITANIUM_WIRE", "STAMP_STEEL_WIRE"},
                {"STAMP_STEEL_FLAT", "STAMP_STEEL_WIRE", "STAMP_TITANIUM_WIRE"},
                {"STAMP_TITANIUM_FLAT", "STAMP_TITANIUM_CIRCUIT", "STAMP_STEEL_CIRCUIT"},
                {"STAMP_STEEL_FLAT", "STAMP_STEEL_CIRCUIT", "STAMP_TITANIUM_CIRCUIT"},
        };
        for(int k = 0; k < stamps.length; k++) {
            int index = corrected.get(k + 1);
            String now = describe(live.get(index)), before = describe(head.get(index));
            String flat = "ComparableStack " + stamps[k][0] + " x1 meta -1; -> ";
            check(now.equals(flat + stamps[k][1] + " x1 meta 0 @1.0; tier 2--1 CONSTRUCTION")
                            && before.equals(flat + stamps[k][2] + " x1 meta 0 @1.0; tier 2--1 CONSTRUCTION"),
                    "index " + index + ": " + stamps[k][0] + " -> " + stamps[k][1] + " (was " + stamps[k][2] + "); got " + now);
        }
        check(corrected.get(2) - corrected.get(1) == 1 && corrected.get(4) - corrected.get(3) == 1 && corrected.get(6) - corrected.get(5) == 1,
                "each titanium/steel pair keeps its adjacent list positions");
        section("1. anvil");
    }

    public static void main(String[] args) {
        run("1. anvil", Goal10BAnvilRegression::anvil);
        System.out.println("Goal 10B anvil world: " + checks + " checks passed");
        if(!failures.isEmpty()) throw new AssertionError(failures.size() + " section(s) failed: " + failures);
    }
}
