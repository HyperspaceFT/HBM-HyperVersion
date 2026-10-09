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
 * Goal 12B section 2 (the Goal 4 shredder world): the coltan entries of the production ShredderRecipes and the custom
 * hbmShredder.json precedence through the production SerializableRecipe loader, against the 3687da34 table
 * (goal12b.head.ShredderRecipes, compiled in the same world). Original ShredderRecipes.java:60, 66, 68-82: an ore gives 2 of its
 * dust, an ingot 1, a block 9 (ore dictionary); OreDictManager.java:395: the coltan fragment is coltan's ingot, crushed coltan
 * ore its dust, the coltan block its block. The world's block registry holds ore_coltan because this fixture names it.
 */
public class Goal12BShredderRegression {
    private static int checks;
    private static final String SECTION = "2. shredder";

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

    static List<String> head() {
        List<String> list = new ArrayList<>();
        for(goal12b.head.ShredderRecipes.ShredderRecipe r : goal12b.head.ShredderRecipes.getJeiRecipes()) list.add(entry(r.input, r.output));
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
        Item dust = NtmItems.POWDER_COLTAN_ORE.get();
        ItemStack ore = new ItemStack(NtmBlocks.ORE_COLTAN.get()), fragment = new ItemStack(NtmItems.FRAGMENT_COLTAN.get()), block = new ItemStack(NtmBlocks.BLOCK_COLTAN.get());

        new goal12b.head.ShredderRecipes().deleteRecipes();
        new goal12b.head.ShredderRecipes().registerDefaults();
        check(!goal12b.head.ShredderRecipes.hasRecipe(ore) && !goal12b.head.ShredderRecipes.hasRecipe(fragment) && !goal12b.head.ShredderRecipes.hasRecipe(block),
                "the 3687da34 table has no entry for the coltan ore, fragment or block");

        new ShredderRecipes().deleteRecipes();
        new ShredderRecipes().registerDefaults();
        expect(ore, dust, 2, "ore_coltan -> 2 crushed coltan ore (original: an ore gives 2 of its dust)");
        expect(fragment, dust, 1, "fragment_coltan -> 1 crushed coltan ore (the fragment is coltan's ingot form)");
        expect(block, dust, 9, "block_coltan -> 9 crushed coltan ore");
        expect(new ItemStack(NtmItems.FRAGMENT_COLTAN.get(), 5), dust, 1, "a stack of 5 fragments still gives 1 per item");
        List<String> live = live(), head = head();
        List<String> added = new ArrayList<>(live);
        added.removeAll(head);
        // Goal 13A (migration/GOAL13A.md A13) adds the four concrete chain entries; they are taken out here and the added check below requires
        // exactly these four (verify_goal13a.py section 8s checks them in detail).
        List<String> concreteChain = new ArrayList<>();
        for(String e : added) if(e.startsWith("hbmsntm:concrete:") || e.startsWith("hbmsntm:concrete_smooth:") || e.startsWith("hbmsntm:resource_limestone:")
                || e.startsWith("hbmsntm:block_slag:")) concreteChain.add(e);
        added.removeAll(concreteChain);
        live.removeAll(concreteChain);
        check(concreteChain.size() == 4 && concreteChain.stream().anyMatch(e -> e.startsWith("hbmsntm:concrete:") && e.contains(" -> minecraft:gravel x1:"))
                        && concreteChain.stream().anyMatch(e -> e.startsWith("hbmsntm:concrete_smooth:") && e.contains(" -> minecraft:gravel x1:"))
                        && concreteChain.stream().anyMatch(e -> e.startsWith("hbmsntm:resource_limestone:") && e.contains(" -> hbmsntm:powder_limestone x4:"))
                        && concreteChain.stream().anyMatch(e -> e.startsWith("hbmsntm:block_slag:") && e.contains(" -> hbmsntm:powder_cement x4:")),
                "Goal 13A: exactly the concrete (1 gravel), concrete_smooth (1 gravel), resource_limestone (4 limestone powder) and block_slag (4 cement powder) entries are added: "
                        + concreteChain);
        List<String> rest = new ArrayList<>(live);
        rest.removeIf(e -> !head.contains(e));
        check(rest.equals(head) && added.size() == 3 && live.size() == head.size() + 3,
                "the default table is the 3687da34 table (" + head.size() + " entries, order kept) plus exactly 3 entries: " + added);
        check(added.stream().anyMatch(e -> e.startsWith(NtmBlocks.ORE_COLTAN.get().id + ":") && e.contains(" -> " + dust.id + " x2:"))
                        && added.stream().anyMatch(e -> e.startsWith(NtmItems.FRAGMENT_COLTAN.get().id + ":") && e.contains(" -> " + dust.id + " x1:"))
                        && added.stream().anyMatch(e -> e.startsWith(NtmBlocks.BLOCK_COLTAN.get().id + ":") && e.contains(" -> " + dust.id + " x9:")),
                "the 3 added entries are the ore (2), the fragment (1) and the block (9): " + added);

        // The production loader: a custom entry for the fragment wins; a custom file without it gets the default.
        NuclearTechMod.configDir = config.toFile();
        SerializableRecipe.recipeHandlers.clear();
        SerializableRecipe.recipeHandlers.add(new ShredderRecipes());
        SerializableRecipe.initialize();
        Path directory = config.resolve("hbmRecipes");
        Path template = directory.resolve("_hbmShredder.json");
        Path active = directory.resolve("hbmShredder.json");
        check(Files.isRegularFile(template) && Files.readString(template).contains("\"" + NtmItems.FRAGMENT_COLTAN.get().id + "\""), "the exported template lists the fragment entry");
        expect(fragment, dust, 1, "without a custom file the loaded table has the fragment entry");
        Files.writeString(active, "{\"recipes\":[{\"input\":[\"" + NtmItems.FRAGMENT_COLTAN.get().id + "\"],\"output\":[\"" + NtmItems.POWDER_IRON.get().id + "\",3]}]}");
        SerializableRecipe.initialize();
        expect(fragment, NtmItems.POWDER_IRON.get(), 3, "a custom hbmShredder.json entry for the fragment wins over the default (registerIfAbsent in registerPost)");
        expect(ore, dust, 2, "the raw ore entry comes back from registerPost");
        Files.writeString(active, "{\"recipes\":[]}");
        SerializableRecipe.initialize();
        expect(fragment, dust, 1, "a custom file without the fragment: registerPost adds the default fragment entry");
        expect(block, dust, 9, "the block entry is a material default too: registerPost restores it");
        System.out.println("info: shredder default entries: " + head.size() + " at 3687da34, " + live.size() + " now");
    }
}
