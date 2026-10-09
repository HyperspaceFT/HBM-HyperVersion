package com.hbm.inventory.recipes.loader;

import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.recipes.ShredderRecipes;
import com.hbm.items.NtmItems;
import com.hbm.main.NuclearTechMod;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.Blocks;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/**
 * Goal 13A section 8s (the Goal 4 shredder world): the four concrete chain entries of the production ShredderRecipes and the
 * custom hbmShredder.json precedence through the production SerializableRecipe loader, against the 12f38317 table
 * (goal13a.head.ShredderRecipes, compiled in the same world). Original (Hbm-s-Nuclear-Tech-GIT d7ef2df)
 * ShredderRecipes.java:153-154 (concrete and smooth concrete -> 1 gravel), :175 (the limestone stone block -> 4 limestone powder),
 * :210 (the slag block -> 4 cement powder). It also writes the entries the whole-chain trace of verify_goal13a.py joins with the
 * crafting and chemical plant recipes (args[1]).
 */
public class Goal13AShredderRegression {
    private static int checks;
    private static final String SECTION = "8s. shredder";

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
        for(goal13a.head.ShredderRecipes.ShredderRecipe r : goal13a.head.ShredderRecipes.getJeiRecipes()) list.add(entry(r.input, r.output));
        return list;
    }

    static void expect(ItemStack input, Item item, int count, String label) {
        ItemStack actual = ShredderRecipes.getShredderResult(input);
        check(actual.getItem() == item && actual.getCount() == count, label + ": " + input.getItem().id + " -> " + describe(actual));
    }

    public static void main(String[] args) throws Exception {
        try {
            shredder(Path.of(args[0]), Path.of(args[1]));
        } catch(AssertionError e) {
            System.out.println("AssertionError in " + SECTION + " after " + checks + " passed checks: " + e.getMessage());
            System.exit(1);
        }
        System.out.println(SECTION + ": " + checks + " checks passed");
    }

    static void shredder(Path config, Path facts) throws Exception {
        Item gravel = Blocks.GRAVEL.asItem(), powder = NtmItems.POWDER_LIMESTONE.get(), cement = NtmItems.POWDER_CEMENT.get();
        ItemStack concrete = new ItemStack(NtmBlocks.CONCRETE.get()), smooth = new ItemStack(NtmBlocks.CONCRETE_SMOOTH.get()),
                limestone = new ItemStack(NtmBlocks.RESOURCE_LIMESTONE.get()), slag = new ItemStack(NtmBlocks.BLOCK_SLAG.get());

        new goal13a.head.ShredderRecipes().deleteRecipes();
        new goal13a.head.ShredderRecipes().registerDefaults();
        check(!goal13a.head.ShredderRecipes.hasRecipe(concrete) && !goal13a.head.ShredderRecipes.hasRecipe(smooth) && !goal13a.head.ShredderRecipes.hasRecipe(limestone)
                        && !goal13a.head.ShredderRecipes.hasRecipe(slag),
                "the 12f38317 table has no entry for concrete, smooth concrete, the limestone block or the slag block");

        new ShredderRecipes().deleteRecipes();
        new ShredderRecipes().registerDefaults();
        expect(concrete, gravel, 1, "concrete -> 1 gravel (original ShredderRecipes.java:153)");
        expect(smooth, gravel, 1, "smooth concrete -> 1 gravel (:154)");
        expect(limestone, powder, 4, "the limestone stone block -> 4 limestone powder (:175)");
        expect(slag, cement, 4, "the slag block -> 4 cement powder (:210)");
        expect(new ItemStack(NtmBlocks.CONCRETE.get(), 5), gravel, 1, "a stack of 5 concrete blocks still gives 1 per item");
        List<String> live = live(), head = head();
        List<String> added = new ArrayList<>(live);
        added.removeAll(head);
        List<String> rest = new ArrayList<>(live);
        rest.removeIf(e -> !head.contains(e));
        check(rest.equals(head) && added.size() == 4 && live.size() == head.size() + 4,
                "the default table is the 12f38317 table (" + head.size() + " entries, order kept) plus exactly 4 entries: " + added);
        check(added.stream().anyMatch(e -> e.startsWith(NtmBlocks.CONCRETE.get().id + ":") && e.contains(" -> " + gravel.id + " x1:"))
                        && added.stream().anyMatch(e -> e.startsWith(NtmBlocks.CONCRETE_SMOOTH.get().id + ":") && e.contains(" -> " + gravel.id + " x1:"))
                        && added.stream().anyMatch(e -> e.startsWith(NtmBlocks.RESOURCE_LIMESTONE.get().id + ":") && e.contains(" -> " + powder.id + " x4:"))
                        && added.stream().anyMatch(e -> e.startsWith(NtmBlocks.BLOCK_SLAG.get().id + ":") && e.contains(" -> " + cement.id + " x4:")),
                "the 4 added entries are concrete (1 gravel), smooth concrete (1 gravel), limestone (4 powder) and slag (4 cement): " + added);

        // The production loader: a custom entry wins; a custom file without the entries gets the defaults.
        NuclearTechMod.configDir = config.toFile();
        SerializableRecipe.recipeHandlers.clear();
        SerializableRecipe.recipeHandlers.add(new ShredderRecipes());
        SerializableRecipe.initialize();
        Path directory = config.resolve("hbmRecipes");
        Path template = directory.resolve("_hbmShredder.json");
        Path active = directory.resolve("hbmShredder.json");
        String text = Files.readString(template);
        check(Files.isRegularFile(template) && text.contains("\"" + NtmBlocks.CONCRETE.get().id + "\"") && text.contains("\"" + NtmBlocks.RESOURCE_LIMESTONE.get().id + "\"")
                        && text.contains("\"" + NtmBlocks.BLOCK_SLAG.get().id + "\"") && text.contains("\"" + NtmBlocks.CONCRETE_SMOOTH.get().id + "\""),
                "the exported template lists the four entries");
        expect(limestone, powder, 4, "without a custom file the loaded table has the limestone entry");
        Files.writeString(active, "{\"recipes\":[{\"input\":[\"" + NtmBlocks.CONCRETE.get().id + "\"],\"output\":[\"" + NtmItems.POWDER_IRON.get().id + "\",3]}]}");
        SerializableRecipe.initialize();
        expect(concrete, NtmItems.POWDER_IRON.get(), 3, "a custom hbmShredder.json entry for concrete wins over the default (registerIfAbsent in registerPost)");
        expect(limestone, powder, 4, "the other entries come back from registerPost");
        expect(slag, cement, 4, "the slag entry as well");
        Files.writeString(active, "{\"recipes\":[]}");
        SerializableRecipe.initialize();
        expect(concrete, gravel, 1, "a custom file without the entry: registerPost adds the default concrete entry");
        expect(smooth, gravel, 1, "and smooth concrete");
        expect(limestone, powder, 4, "and limestone");
        expect(slag, cement, 4, "and slag");
        new ShredderRecipes().deleteRecipes();
        new ShredderRecipes().registerDefaults();
        Files.writeString(facts, "{\"limestone\":[\"" + describe(ShredderRecipes.getShredderResult(limestone)) + "\"],\"slag\":[\"" + describe(ShredderRecipes.getShredderResult(slag))
                + "\"],\"concrete\":[\"" + describe(ShredderRecipes.getShredderResult(concrete)) + "\"],\"concrete_smooth\":[\"" + describe(ShredderRecipes.getShredderResult(smooth)) + "\"]}");
        System.out.println("info: shredder default entries: " + head.size() + " at 12f38317, " + live.size() + " now");
    }
}
