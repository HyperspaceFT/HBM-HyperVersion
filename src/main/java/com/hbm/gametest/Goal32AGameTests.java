package com.hbm.gametest;

import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.generic.OreBasaltBlock;
import com.hbm.blocks.generic.OreBasaltBlock.BasaltOreType;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.RecipesCommon.TagStack;
import com.hbm.inventory.recipes.CentrifugeRecipes;
import com.hbm.inventory.recipes.CentrifugeRecipes.CentrifugeRecipe;
import com.hbm.inventory.recipes.ChemicalPlantRecipes;
import com.hbm.inventory.recipes.anvil.AnvilSmithingIngotMoldRecipe;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.ZirnoxRodItem.ZirnoxType;
import com.hbm.main.NuclearTechMod;
import com.hbm.module.ModuleBurnTime;
import com.hbm.module.ModulePatternMatcher;
import com.mojang.logging.LogUtils;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.ItemTags;
import net.minecraft.tags.TagKey;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.crafting.CraftingInput;
import net.minecraft.world.item.crafting.CraftingRecipe;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.ShapedRecipe;
import net.minecraft.world.item.crafting.ShapelessRecipe;
import net.minecraft.world.item.enchantment.Enchantment;
import net.minecraft.world.item.enchantment.Enchantments;
import net.minecraft.world.level.ItemLike;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import org.slf4j.Logger;

import java.util.ArrayList;
import java.util.List;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal32A: the recipe and loot fixes of the batch (the shapeless rope, the ZIRNOX lithium rod, the neptunium
 * fuel billets, the schrabidium fuels and the ZIRNOX LES rod, the nether-brick flat stamps, the laminate's glass tag, the basalt ore
 * drops and the centrifuge's gravel) and the user-approved common item tags (migration/goal32a-tags.md). Same
 * template and conventions as {@link Goal31AGameTests}; every test has its own batch.
 * <p>
 * Expected values come from the ORIGINAL at d4708ef9c, cited beside each group of checks (CraftingManager.java:202,347-356;
 * RodRecipes.java:35-36; MineralRecipes.java:174-175,179-180,416-418; ChemicalPlantRecipes.java:369-372; BlockOreBasalt.java:32-59;
 * CentrifugeRecipes.java:54-202; OreDictManager.java:330-511,639-644; ModulePatternMatcher.java:30-53), not from the NEO implementation.
 * <p>
 * Real classes and state: the RecipeManager with real CraftingInput grids, the chemical plant's registered recipe and its TagStack
 * against the live item tags, block loot tables through Block.getDrops with and without an enchanted pickaxe, and the loaded
 * centrifuge table. Not evidence: the JEI display of these recipes, the crafting screen, the chemical plant running, the
 * centrifuge machine processing, rendering, multiplayer, saved worlds, and 1.7.10 itself.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class Goal32AGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-32a]";

    private static ResourceLocation id(String path) {
        return ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path);
    }

    private static Runnable passed(String test) {
        return () -> LOGGER.info("{} {} passed", TAG, test);
    }

    private static ItemStack s(ItemLike item) {
        return new ItemStack(item);
    }

    private static CraftingRecipe crafting(GameTestHelper helper, String path, Class<?> kind, ItemLike result, int meta, int count, String original) {
        ServerLevel level = helper.getLevel();
        RecipeHolder<?> holder = level.getRecipeManager().byKey(id(path)).orElse(null);
        check(holder != null, "recipe " + id(path) + " is not loaded (" + original + ")");
        check(kind.isInstance(holder.value()), path + " is " + holder.value().getClass().getSimpleName() + ", expected " + kind.getSimpleName() + " (" + original + ")");
        CraftingRecipe recipe = (CraftingRecipe) holder.value();
        ItemStack out = recipe.getResultItem(level.registryAccess());
        check(out.is(result.asItem()) && out.getCount() == count && MetaHelper.getMeta(out) == meta,
                path + " yields " + out + " type " + MetaHelper.getMeta(out) + ", expected " + count + " x " + result.asItem() + " type " + meta + " (" + original + ")");
        return recipe;
    }

    private static boolean matches(GameTestHelper helper, CraftingRecipe recipe, int w, int h, ItemStack... cells) {
        List<ItemStack> grid = new ArrayList<>();
        for(ItemStack s : cells) grid.add(s == null ? ItemStack.EMPTY : s);
        return recipe.matches(CraftingInput.of(w, h, grid), helper.getLevel());
    }

    /** A shapeless recipe matches its inputs in two different arrangements of a 3x3 grid, and not with one input missing or one extra. */
    private static void shapeless(GameTestHelper helper, String path, CraftingRecipe recipe, String original, ItemStack... inputs) {
        ItemStack[] forward = new ItemStack[9];
        ItemStack[] scattered = new ItemStack[9];
        int[] slots = { 8, 0, 4, 2, 6, 1, 7, 3, 5 };
        for(int i = 0; i < inputs.length; i++) {
            forward[i] = inputs[i];
            scattered[slots[i]] = inputs[inputs.length - 1 - i];
        }
        check(matches(helper, recipe, 3, 3, forward), path + " does not match its inputs in order (" + original + ")");
        check(matches(helper, recipe, 3, 3, scattered), path + " does not match its inputs scattered over the grid (" + original + ")");
        ItemStack[] fewer = forward.clone();
        fewer[inputs.length - 1] = null;
        check(!matches(helper, recipe, 3, 3, fewer), path + " matches with an input missing (" + original + ")");
        if(inputs.length < 9) {
            ItemStack[] more = forward.clone();
            more[inputs.length] = inputs[0].copy();
            check(!matches(helper, recipe, 3, 3, more), path + " matches with an extra " + inputs[0] + " (" + original + ")");
        }
    }

    // ---------------------------------------------------------------- crafting (CraftingManager.java:202,347-356; RodRecipes.java:36; MineralRecipes.java:174-175)

    @GameTest(template = TEMPLATE, batch = "hbm32a_crafting", timeoutTicks = 100)
    public static void crafting(GameTestHelper helper) {
        guard(() -> {
            // the rope: three string, shapeless (CraftingManager.java:202); the recipe id 52 is kept
            CraftingRecipe rope = crafting(helper, "52", ShapelessRecipe.class, NtmItems.PLANT_ITEM.get(), 0, 1, "CraftingManager.java:202");
            shapeless(helper, "52", rope, "CraftingManager.java:202", s(Items.STRING), s(Items.STRING), s(Items.STRING));
            check(matches(helper, rope, 3, 1, s(Items.STRING), s(Items.STRING), s(Items.STRING)), "the rope does not match three string in a row");
            check(matches(helper, rope, 1, 3, s(Items.STRING), s(Items.STRING), s(Items.STRING)), "the rope does not match three string in a column");

            // the ZIRNOX lithium rod: an empty rod and two lithium ingots, shapeless (RodRecipes.java:36)
            CraftingRecipe lithium = crafting(helper, "rod_zirnox_lithium", ShapelessRecipe.class, NtmItems.ROD_ZIRNOX.get(), ZirnoxType.LITHIUM.ordinal(), 1, "RodRecipes.java:36");
            shapeless(helper, "rod_zirnox_lithium", lithium, "RodRecipes.java:36", s(NtmItems.ROD_ZIRNOX_EMPTY.get()), s(NtmItems.LITHIUM.get()), s(NtmItems.LITHIUM.get()));

            // the neptunium fuel billets (MineralRecipes.java:174-175)
            CraftingRecipe fromBillets = crafting(helper, "billet_neptunium_fuel_from_billets", ShapelessRecipe.class, NtmItems.BILLET_NEPTUNIUM_FUEL.get(), 0, 3, "MineralRecipes.java:174");
            shapeless(helper, "billet_neptunium_fuel_from_billets", fromBillets, "MineralRecipes.java:174",
                    s(NtmItems.BILLET_U238.get()), s(NtmItems.BILLET_U238.get()), s(NtmItems.BILLET_NEPTUNIUM.get()));
            CraftingRecipe fromNuggets = crafting(helper, "billet_neptunium_fuel_from_nuggets", ShapelessRecipe.class, NtmItems.BILLET_NEPTUNIUM_FUEL.get(), 0, 1, "MineralRecipes.java:175");
            shapeless(helper, "billet_neptunium_fuel_from_nuggets", fromNuggets, "MineralRecipes.java:175",
                    s(NtmItems.NUGGET_NEPTUNIUM.get()), s(NtmItems.NUGGET_NEPTUNIUM.get()), s(NtmItems.NUGGET_U238.get()), s(NtmItems.NUGGET_U238.get()),
                    s(NtmItems.NUGGET_U238.get()), s(NtmItems.NUGGET_U238.get()));

            // the schrabidium fuels (MineralRecipes.java:179-180, :181 is the "tiny" duplicate; :416-418) and the LES rod (RodRecipes.java:35)
            ItemStack sa = s(NtmItems.NUGGET_SCHRABIDIUM.get()), np = s(NtmItems.NUGGET_NEPTUNIUM.get()), be = s(NtmItems.NUGGET_BERYLLIUM.get());
            CraftingRecipe fuelBillets = crafting(helper, "billet_schrabidium_fuel_from_billets", ShapelessRecipe.class, NtmItems.BILLET_SCHRABIDIUM_FUEL.get(), 0, 3, "MineralRecipes.java:179");
            shapeless(helper, "billet_schrabidium_fuel_from_billets", fuelBillets, "MineralRecipes.java:179",
                    s(NtmItems.BILLET_SCHRABIDIUM.get()), s(NtmItems.BILLET_NEPTUNIUM.get()), s(NtmItems.BILLET_BERYLLIUM.get()));
            CraftingRecipe fuelNuggets = crafting(helper, "billet_schrabidium_fuel_from_nuggets", ShapelessRecipe.class, NtmItems.BILLET_SCHRABIDIUM_FUEL.get(), 0, 1, "MineralRecipes.java:180");
            shapeless(helper, "billet_schrabidium_fuel_from_nuggets", fuelNuggets, "MineralRecipes.java:180", sa, sa, np, np, be, be);
            Object[][] ingots = {
                    { "ingot_schrabidium_fuel_from_nuggets", NtmItems.INGOT_SCHRABIDIUM_FUEL.get(), 3, 3, 3, ":416" },
                    { "ingot_hes_from_nuggets", NtmItems.INGOT_HES.get(), 5, 2, 2, ":417" },
                    { "ingot_les_from_nuggets", NtmItems.INGOT_LES.get(), 1, 4, 4, ":418" } };
            for(Object[] row : ingots) {
                List<ItemStack> cells = new ArrayList<>();
                for(int i = 0; i < (int) row[2]; i++) cells.add(sa.copy());
                for(int i = 0; i < (int) row[3]; i++) cells.add(np.copy());
                for(int i = 0; i < (int) row[4]; i++) cells.add(be.copy());
                String path = (String) row[0];
                CraftingRecipe recipe = crafting(helper, path, ShapelessRecipe.class, (Item) row[1], 0, 1, "MineralRecipes.java" + row[5]);
                check(matches(helper, recipe, 3, 3, cells.toArray(new ItemStack[0])), path + " does not match its nine nuggets (MineralRecipes.java" + row[5] + ")");
                cells.set(8, s(Items.IRON_NUGGET));
                check(!matches(helper, recipe, 3, 3, cells.toArray(new ItemStack[0])), path + " matches with an iron nugget in place of its last nugget");
            }
            CraftingRecipe les = crafting(helper, "rod_zirnox_les_fuel", ShapelessRecipe.class, NtmItems.ROD_ZIRNOX.get(), ZirnoxType.LES_FUEL.ordinal(), 1, "RodRecipes.java:35");
            shapeless(helper, "rod_zirnox_les_fuel", les, "RodRecipes.java:35", s(NtmItems.ROD_ZIRNOX_EMPTY.get()), s(NtmItems.BILLET_LES.get()), s(NtmItems.BILLET_LES.get()));

            // the flat stamps also take nether bricks (CraftingManager.java:347-356): steel, titanium, obsidian three over three, desh in a cross
            ItemStack b = s(Items.NETHER_BRICK);
            Object[][] lines = {
                    { "stamp_steel_flat_from_nether_brick", NtmItems.STAMP_STEEL_FLAT.get(), s(NtmItems.INGOT_STEEL.get()) },
                    { "stamp_titanium_flat_from_nether_brick", NtmItems.STAMP_TITANIUM_FLAT.get(), s(NtmItems.INGOT_TITANIUM.get()) },
                    { "stamp_obsidian_flat_from_nether_brick", NtmItems.STAMP_OBSIDIAN_FLAT.get(), s(Items.OBSIDIAN) } };
            for(Object[] line : lines) {
                String path = (String) line[0];
                ItemStack m = (ItemStack) line[2];
                CraftingRecipe stamp = crafting(helper, path, ShapedRecipe.class, (Item) line[1], 0, 1, "CraftingManager.java:347-356");
                check(matches(helper, stamp, 3, 2, b, b, b, m, m, m), path + " does not match three nether bricks over three " + m);
                check(!matches(helper, stamp, 3, 2, s(Items.BRICK), s(Items.BRICK), s(Items.BRICK), m, m, m), path + " matches bricks (that is the older recipe's job)");
                check(!matches(helper, stamp, 3, 2, m, m, m, b, b, b), path + " matches upside down");
            }
            ItemStack d = s(NtmItems.INGOT_DESH.get());
            CraftingRecipe desh = crafting(helper, "stamp_desh_flat_from_nether_brick", ShapedRecipe.class, NtmItems.STAMP_DESH_FLAT.get(), 0, 1, "CraftingManager.java:355-356");
            check(matches(helper, desh, 3, 3, b, d, b, d, s(NtmItems.INGOT_FERROURANIUM.get()), d, b, d, b), "the desh stamp does not match its nether-brick cross");
            check(!matches(helper, desh, 3, 3, b, d, b, d, s(NtmItems.INGOT_STEEL.get()), d, b, d, b), "the desh stamp matches steel in the centre");
        }).run();
        passed("crafting").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- the laminate (ChemicalPlantRecipes.java:369-372: blockGlass)

    @GameTest(template = TEMPLATE, batch = "hbm32a_laminate", timeoutTicks = 100)
    public static void laminate(GameTestHelper helper) {
        guard(() -> {
            GenericRecipe recipe = ChemicalPlantRecipes.INSTANCE.recipeNameMap.get("chem.laminate");
            check(recipe != null && recipe.inputItem != null && recipe.inputItem.length == 2, "chem.laminate is missing or does not take two item inputs");
            AStack glass = recipe.inputItem[0];
            check(glass instanceof TagStack t && t.tag.location().equals(ResourceLocation.fromNamespaceAndPath("c", "glass_blocks")),
                    "chem.laminate's first input is " + glass + ", expected the tag c:glass_blocks");
            // the original's blockGlass also holds its own glasses (OreDictManager.java:639-644); NEO has boron and lead glass
            for(ItemLike block : List.of(Blocks.GLASS, Blocks.WHITE_STAINED_GLASS, Blocks.TINTED_GLASS, NtmBlocks.GLASS_BORON.get(), NtmBlocks.GLASS_LEAD.get())) {
                check(glass.matchesRecipe(s(block), true), "chem.laminate does not take " + BuiltInRegistries.ITEM.getKey(block.asItem()));
            }
            check(!glass.matchesRecipe(s(Blocks.GLASS_PANE), true), "chem.laminate takes a glass pane");
            check(!glass.extractForJEI().isEmpty(), "c:glass_blocks lists no items for the recipe display");
        }).run();
        passed("laminate").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- the basalt ores (BlockOreBasalt.java:32-82)

    @GameTest(template = TEMPLATE, batch = "hbm32a_basalt_drops", timeoutTicks = 100)
    public static void basalt_drops(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos probe = helper.absolutePos(new BlockPos(2, 2, 2));
            // EnumBasaltOreType: SULFUR, FLUORITE, ASBESTOS, GEM, MOLYSITE drop sulfur, fluorite, an asbestos ingot, a volcanic gem and
            // molysite powder, one each, and getDrop ignores fortune; silk touch takes the 1.7.10 Block.harvestBlock path (the class
            // overrides neither renderAsNormalBlock nor harvestBlock) and drops the ore itself with its subtype
            Item[] want = { NtmItems.SULFUR.get(), NtmItems.FLUORITE.get(), NtmItems.INGOT_ASBESTOS.get(), NtmItems.GEM_VOLCANIC.get(), NtmItems.POWDER_MOLYSITE.get() };
            check(BasaltOreType.values().length == want.length, "NEO has " + BasaltOreType.values().length + " basalt ore types, the original 5");
            ItemStack fortune = enchanted(level, Enchantments.FORTUNE, 3);
            ItemStack silk = enchanted(level, Enchantments.SILK_TOUCH, 1);
            for(BasaltOreType type : BasaltOreType.values()) {
                BlockState state = NtmBlocks.ORE_BASALT.get().defaultBlockState().setValue(OreBasaltBlock.SUBTYPE, type.ordinal());
                for(ItemStack tool : new ItemStack[] { ItemStack.EMPTY, s(Items.DIAMOND_PICKAXE), fortune }) {
                    List<ItemStack> drops = Block.getDrops(state, level, probe, null, null, tool);
                    check(drops.size() == 1 && drops.get(0).is(want[type.ordinal()]) && drops.get(0).getCount() == 1,
                            type + " with " + (tool.isEmpty() ? "no tool" : tool + " " + tool.getEnchantments()) + " dropped " + drops + ", expected one " + want[type.ordinal()]);
                }
                List<ItemStack> kept = Block.getDrops(state, level, probe, null, null, silk);
                check(kept.size() == 1 && kept.get(0).is(NtmBlocks.ORE_BASALT.get().asItem()) && kept.get(0).getCount() == 1
                                && MetaHelper.getMeta(kept.get(0)) == type.ordinal(),
                        type + " with silk touch dropped " + kept + ", expected one ore_basalt of subtype " + type.ordinal());
            }
        }).run();
        passed("basalt_drops").run();
        helper.succeed();
    }

    private static ItemStack enchanted(ServerLevel level, ResourceKey<Enchantment> key, int lvl) {
        Holder<Enchantment> holder = level.registryAccess().lookupOrThrow(Registries.ENCHANTMENT).getOrThrow(key);
        ItemStack pick = s(Items.DIAMOND_PICKAXE);
        pick.enchant(holder, lvl);
        return pick;
    }

    // ---------------------------------------------------------------- the common item tags (migration/goal32a-tags.md)

    private static TagKey<Item> c(String path) {
        return ItemTags.create(ResourceLocation.fromNamespaceAndPath("c", path));
    }

    @GameTest(template = TEMPLATE, batch = "hbm32a_item_tags", timeoutTicks = 100)
    public static void item_tags(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            // a sample of the published names with the item the original registers (OreDictManager.java:336,380,385,391)
            check(s(NtmItems.POWDER_IRON.get()).is(c("dusts/iron")) && s(NtmItems.POWDER_IRON.get()).is(c("dusts")), "iron powder is not in c:dusts/iron and c:dusts");
            check(s(NtmItems.INGOT_STEEL.get()).is(c("ingots/steel")) && s(NtmItems.INGOT_STEEL.get()).is(c("ingots")), "the steel ingot is not in c:ingots/steel and c:ingots");
            check(s(NtmItems.INGOT_COPPER.get()).is(c("ingots/copper")), "HBM's copper ingot is not in c:ingots/copper");
            check(s(NtmItems.PLATE_STEEL.get()).is(c("plates")) && s(NtmItems.PLATE_COPPER.get()).is(c("plates")), "the published plates are not in the new parent c:plates");
            check(s(NtmBlocks.ORE_GNEISS_IRON.get()).is(c("ores/iron")), "schist iron ore is not in c:ores/iron");
            check(s(NtmBlocks.ORE_TITANIUM_DEEPSLATE.get()).is(c("ores/titanium")), "deepslate titanium ore is not in c:ores/titanium");
            // not published: the ore chunks registered as ingots, the vanilla coal as a gem, the copper block, uranium
            check(!s(NtmItems.CHUNK_MALACHITE.get()).is(c("ingots")), "the malachite chunk is an ingot");
            check(!s(Items.COAL).is(c("gems/coal")), "vanilla coal is in c:gems/coal");
            check(!s(NtmBlocks.BLOCK_COPPER.get()).is(c("storage_blocks/copper")), "HBM's copper block is in c:storage_blocks/copper");
            check(!s(NtmItems.INGOT_URANIUM.get()).is(c("ingots/uranium")), "the uranium ingot is in c:ingots/uranium");

            // the sorter's smart mode (ModulePatternMatcher.java:30-53): ingot, block, dust, nugget, plate kinds in that order
            ModulePatternMatcher m = new ModulePatternMatcher(3);
            m.initPatternSmart(level, s(NtmItems.POWDER_IRON.get()), 0);
            m.initPatternSmart(level, s(NtmItems.INGOT_STEEL.get()), 1);
            m.initPatternSmart(level, s(NtmItems.INGOT_COPPER.get()), 2);
            check("c:dusts/iron".equals(m.modes[0]), "iron powder picks " + m.modes[0] + ", expected c:dusts/iron (the original's dustIron)");
            check("c:ingots/steel".equals(m.modes[1]), "the steel ingot picks " + m.modes[1] + ", expected c:ingots/steel (ingotSteel)");
            check("c:ingots/copper".equals(m.modes[2]), "HBM's copper ingot picks " + m.modes[2] + ", expected c:ingots/copper (ingotCopper)");

            // the ingot mold template takes any c:ingots ingot, as the original's "any ingot"
            AnvilSmithingIngotMoldRecipe mold = new AnvilSmithingIngotMoldRecipe();
            for(Item ingot : List.of(NtmItems.INGOT_STEEL.get(), NtmItems.INGOT_TITANIUM.get(), Items.IRON_INGOT)) {
                check(mold.matchesInt(s(ingot), s(NtmItems.MOLD_BASE.get())) == 0, BuiltInRegistries.ITEM.getKey(ingot) + " is not taken as the ingot mold template");
            }
            check(mold.matchesInt(s(NtmItems.CHUNK_MALACHITE.get()), s(NtmItems.MOLD_BASE.get())) < 0, "the malachite chunk is taken as an ingot mold template");

            // the burn classes of the fuel items that joined a tag stay as their names decide (ModuleBurnTime.getMod reads the path first)
            double[] classes = { 10, 11, 12, 13, 14, 15, 16, 17 }; // log, wood, coal, lignite, coke, solid, rocket, balefire
            ModuleBurnTime burn = new ModuleBurnTime();
            Object[][] fuels = {
                    { NtmItems.POWDER_COAL.get(), 12.0, "dusts/coal" }, { NtmItems.LIGNITE.get(), 13.0, "gems/lignite" },
                    { NtmItems.POWDER_LIGNITE.get(), 13.0, "dusts/lignite" }, { NtmItems.COKE_COAL.get(), 14.0, "gems/coal_coke" },
                    { NtmItems.COKE_PETROLEUM.get(), 14.0, "gems/pet_coke" }, { NtmItems.COKE_LIGNITE.get(), 14.0, "gems/lignite_coke" },
                    { NtmItems.POWDER_FIRE.get(), -1.0, "dusts/red_phosphorus" } };
            for(Object[] f : fuels) {
                ItemStack stack = s((Item) f[0]);
                check(stack.is(c((String) f[2])), BuiltInRegistries.ITEM.getKey((Item) f[0]) + " is not in c:" + f[2]);
                double got = burn.getMod(stack, classes, -1.0);
                check(got == (double) f[1], BuiltInRegistries.ITEM.getKey((Item) f[0]) + " burns in class " + got + ", expected " + f[1]);
            }
        }).run();
        passed("item_tags").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- the centrifuge's last output (CentrifugeRecipes.java:54-184)

    @GameTest(template = TEMPLATE, batch = "hbm32a_centrifuge_gravel", timeoutTicks = 100)
    public static void centrifuge_gravel(GameTestHelper helper) {
        guard(() -> {
            // the original ore rows end in gravel; only nether quartz and nether gold keep netherrack (NEO's nether gold ore has no
            // original row) and tikite keeps end stone. The uranium and schrabidium rows serve the overworld and the nether ore alike
            // (:126-130,144-148), so the nether uranium, scorched nether uranium and nether schrabidium ores end in gravel too.
            for(Block ore : List.of(Blocks.IRON_ORE, Blocks.DEEPSLATE_COAL_ORE, NtmBlocks.ORE_URANIUM.get(), NtmBlocks.ORE_GNEISS_IRON.get(),
                    NtmBlocks.ORE_NETHER_URANIUM.get(), NtmBlocks.ORE_NETHER_URANIUM_SCORCHED.get(), NtmBlocks.ORE_NETHER_SCHRABIDIUM.get())) {
                ItemStack[] got = CentrifugeRecipes.getOutput(s(ore));
                check(got.length == 4 && got[3].is(Items.GRAVEL) && got[3].getCount() == 1, BuiltInRegistries.BLOCK.getKey(ore) + " centrifuges to " + List.of(got) + ", expected one gravel last");
            }
            for(Block ore : List.of(Blocks.NETHER_QUARTZ_ORE, Blocks.NETHER_GOLD_ORE)) {
                ItemStack[] got = CentrifugeRecipes.getOutput(s(ore));
                check(got.length == 4 && got[3].is(Items.NETHERRACK), BuiltInRegistries.BLOCK.getKey(ore) + " centrifuges to " + List.of(got) + ", expected netherrack last");
            }
            int gravel = 0;
            for(CentrifugeRecipe row : CentrifugeRecipes.getJeiRecipes()) {
                for(ItemStack out : row.outputs) {
                    check(!out.is(Items.STONE), row.input + " still centrifuges to stone");
                    if(out.is(Items.GRAVEL)) gravel++;
                }
            }
            LOGGER.info("{} centrifuge: no row gives stone, {} rows give gravel", TAG, gravel);
        }).run();
        passed("centrifuge_gravel").run();
        helper.succeed();
    }
}
