package com.hbm.inventory.recipes.loader;

import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.recipes.ShredderRecipes;
import com.hbm.items.NtmItems;
import com.hbm.main.NuclearTechMod;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/**
 * Goal 11C section 5 (shredder world): the rare earth ore chunk entry of the production ShredderRecipes (original
 * ShredderRecipes.java:208, the RARE ore chunk -> 1 desh blend), the custom hbmShredder.json precedence through the
 * production SerializableRecipe loader, and every other default entry against the post-Goal 11B table
 * (goal11c.base.ShredderRecipes, the base-g11b copy compiled in the same world).
 * Goal 12B adds the coltan fragment and block entries; the table comparison takes exactly those out (one added check
 * requires them).
 * Goal 13A adds the four concrete chain entries (concrete and smooth concrete to gravel, the limestone block to limestone powder, the
 * slag block to cement powder); the table comparison takes exactly those out as well (one added check requires them).
 */
public class Goal11CShredderRegression {
    private static int checks;
    private static final String SECTION = "5. shredder: rare earth ore chunk";

    private static void check(boolean condition, String message) {
        if(!condition) throw new AssertionError(message);
        checks++;
    }

    static String describe(ItemStack stack) {
        return stack.isEmpty() ? "empty" : stack.getItem().id + " x" + stack.getCount();
    }

    static String entry(ItemStack input, ItemStack output) {
        return input.getItem().id + ":" + MetaHelper.getMeta(input) + " -> " + describe(output) + ":" + MetaHelper.getMeta(output);
    }

    static List<String> live() {
        List<String> list = new ArrayList<>();
        for(ShredderRecipes.ShredderRecipe r : ShredderRecipes.getJeiRecipes()) list.add(entry(r.input, r.output));
        return list;
    }

    static List<String> base() {
        List<String> list = new ArrayList<>();
        for(goal11c.base.ShredderRecipes.ShredderRecipe r : goal11c.base.ShredderRecipes.getJeiRecipes()) list.add(entry(r.input, r.output));
        return list;
    }

    static void expect(ItemStack input, Item item, int count, String label) {
        ItemStack actual = ShredderRecipes.getShredderResult(input);
        check(actual.getItem() == item && actual.getCount() == count, label + ": " + input.getItem().id + " -> " + describe(actual));
    }

    public static void main(String[] args) throws Exception {
        try {
            shredder(Path.of(args[0]));
        } catch(AssertionError e) {
            System.out.println("AssertionError in " + SECTION + " after " + checks + " passed checks: " + e.getMessage());
            System.exit(1);
        }
        System.out.println(SECTION + ": " + checks + " checks passed");
    }

    static void shredder(Path config) throws Exception {
        Item chunk = NtmItems.RARE_EARTH_ORE_CHUNK.get(), mix = NtmItems.POWDER_DESH_MIX.get();

        // The post-Goal 11B table had no entry for the chunk (it shredded to dust).
        new goal11c.base.ShredderRecipes().deleteRecipes();
        new goal11c.base.ShredderRecipes().registerDefaults();
        check(!goal11c.base.ShredderRecipes.hasRecipe(new ItemStack(chunk))
                        && goal11c.base.ShredderRecipes.getShredderResult(new ItemStack(chunk)).getItem() == NtmItems.DUST.get(),
                "the post-Goal 11B table has no rare_earth_ore_chunk entry (it gave dust)");

        // Defaults: the live table equals the post-Goal 11B table plus exactly the chunk entry after the deepslate ore.
        new ShredderRecipes().deleteRecipes();
        new ShredderRecipes().registerDefaults();
        expect(new ItemStack(chunk), mix, 1, "rare_earth_ore_chunk -> 1 powder_desh_mix (original ShredderRecipes.java:208)");
        expect(new ItemStack(chunk, 7), mix, 1, "a stack of 7 chunks still gives 1 blend per item (the key is singular, as every entry)");
        expect(new ItemStack(NtmBlocks.ORE_RARE.get()), mix, 1, "ore_rare -> 1 powder_desh_mix (unchanged)");
        expect(new ItemStack(NtmBlocks.ORE_RARE_DEEPSLATE.get()), mix, 1, "ore_rare_deepslate -> 1 powder_desh_mix (unchanged)");
        List<String> live = live(), base = base();
        String added = entry(new ItemStack(chunk), new ItemStack(mix, 1));
        List<String> expected = new ArrayList<>(base);
        int deepslate = -1;
        for(int i = 0; i < base.size(); i++) if(base.get(i).startsWith(NtmBlocks.ORE_RARE_DEEPSLATE.get().id + ":")) deepslate = i;
        check(deepslate >= 0, "the post-Goal 11B table has the ore_rare_deepslate entry");
        expected.add(deepslate + 1, added);
        // Goal 12B (migration/GOAL12B.md) adds the coltan fragment and block entries (and the raw ore entry, which this world's
        // block registry, built from the names its sources use, does not reach); they are taken out here and the added check
        // below requires exactly these two (verify_goal12b.py section 2 checks all three in detail).
        List<String> coltan = new ArrayList<>();
        for(String e : live) if(e.startsWith("hbmsntm:ore_coltan:") || e.startsWith("hbmsntm:fragment_coltan:") || e.startsWith("hbmsntm:block_coltan:")) coltan.add(e);
        live.removeAll(coltan);
        check(coltan.size() == 2 && coltan.stream().anyMatch(e -> e.startsWith("hbmsntm:block_coltan:") && e.contains(" -> hbmsntm:powder_coltan_ore x9:"))
                        && coltan.stream().anyMatch(e -> e.startsWith("hbmsntm:fragment_coltan:") && e.contains(" -> hbmsntm:powder_coltan_ore x1:")),
                "Goal 12B: exactly the block_coltan (9) and fragment_coltan (1) entries are added, to crushed coltan ore: " + coltan);
        // Goal 13A (migration/GOAL13A.md A13) adds the concrete chain entries; they are taken out here and the added check below requires
        // exactly these four (verify_goal13a.py section 8s checks them in detail).
        List<String> concreteChain = new ArrayList<>();
        for(String e : live) if(e.startsWith("hbmsntm:concrete:") || e.startsWith("hbmsntm:concrete_smooth:") || e.startsWith("hbmsntm:resource_limestone:")
                || e.startsWith("hbmsntm:block_slag:")) concreteChain.add(e);
        live.removeAll(concreteChain);
        check(concreteChain.size() == 4 && concreteChain.stream().anyMatch(e -> e.startsWith("hbmsntm:concrete:") && e.contains(" -> minecraft:gravel x1:"))
                        && concreteChain.stream().anyMatch(e -> e.startsWith("hbmsntm:concrete_smooth:") && e.contains(" -> minecraft:gravel x1:"))
                        && concreteChain.stream().anyMatch(e -> e.startsWith("hbmsntm:resource_limestone:") && e.contains(" -> hbmsntm:powder_limestone x4:"))
                        && concreteChain.stream().anyMatch(e -> e.startsWith("hbmsntm:block_slag:") && e.contains(" -> hbmsntm:powder_cement x4:")),
                "Goal 13A: exactly the concrete (1 gravel), concrete_smooth (1 gravel), resource_limestone (4 limestone powder) and block_slag (4 cement powder) entries are added: "
                        + concreteChain);
        check(live.equals(expected), "the default table is the post-Goal 11B table (" + base.size() + " entries) with exactly the chunk entry "
                + "inserted after ore_rare_deepslate (" + live.size() + " entries without the Goal 12B and 13A entries); first difference at "
                + firstDifference(live, expected));

        // The production loader: a custom hbmShredder.json entry for the chunk wins over the default (registerIfAbsent).
        NuclearTechMod.configDir = config.toFile();
        SerializableRecipe.recipeHandlers.clear();
        SerializableRecipe.recipeHandlers.add(new ShredderRecipes());
        SerializableRecipe.initialize();
        Path directory = config.resolve("hbmRecipes");
        Path template = directory.resolve("_hbmShredder.json");
        Path active = directory.resolve("hbmShredder.json");
        check(Files.isRegularFile(template) && Files.readString(template).contains("\"" + chunk.id + "\""),
                "the exported default template lists the chunk entry");
        expect(new ItemStack(chunk), mix, 1, "without a custom file the loaded table has the chunk entry");
        Files.writeString(active, "{\"recipes\":[{\"input\":[\"" + chunk.id + "\"],\"output\":[\"" + NtmItems.POWDER_IRON.get().id + "\",3]}]}");
        SerializableRecipe.initialize();
        expect(new ItemStack(chunk), NtmItems.POWDER_IRON.get(), 3, "a custom hbmShredder.json entry for the chunk wins (registerPost keeps it)");
        expect(new ItemStack(NtmBlocks.ORE_RARE.get()), mix, 1, "the other material entries are restored by registerPost");
        Files.writeString(active, "{\"recipes\":[]}");
        SerializableRecipe.initialize();
        expect(new ItemStack(chunk), mix, 1, "a custom file without the chunk: registerPost adds the default chunk entry");
        System.out.println("info: shredder default entries: " + base.size() + " post-Goal 11B, " + live.size() + " now");
    }

    static String firstDifference(List<String> a, List<String> b) {
        for(int i = 0; i < Math.min(a.size(), b.size()); i++) if(!a.get(i).equals(b.get(i))) return i + ": " + a.get(i) + " / " + b.get(i);
        return a.size() == b.size() ? "none" : "length " + a.size() + " / " + b.size();
    }
}
