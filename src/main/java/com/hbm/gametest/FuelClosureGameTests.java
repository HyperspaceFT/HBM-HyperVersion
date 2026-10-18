package com.hbm.gametest;

import com.hbm.blockentity.machine.ReactorZirnoxBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.recipes.PUREXRecipes;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.DepletedFuelItem;
import com.hbm.items.machine.ZirnoxRodItem;
import com.hbm.items.machine.ZirnoxRodItem.ZirnoxType;
import com.hbm.main.NuclearTechMod;
import com.hbm.util.TagsUtil;
import com.mojang.logging.LogUtils;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.CraftingInput;
import net.minecraft.world.item.crafting.CraftingRecipe;
import net.minecraft.world.item.crafting.Ingredient;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.item.crafting.ShapelessRecipe;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import org.slf4j.Logger;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.TreeSet;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal 22C, the plutonium, MOX and uranium-233 fuel closure: the eleven fuel alloy rows (original
 * MineralRecipes.java:156-178,419), the four ZIRNOX rod recipes (RodRecipes.java:31-33,37) plus the thorium fuel rod recipe added after
 * 22C (RodRecipes.java:30), the heat and life of the new rods in the
 * reactor, their depletion into the 20C waste rows, and the chain from real PUREX outputs to the new rods, all through the
 * RecipeManager the way a crafting table asks it. Same template and conventions as {@link SmokeGameTests}.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class FuelClosureGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";

    /** The ingredient multiset and the result of one crafting row as the task book (GOAL22C.md C1) lists it. */
    private record Row(String id, Item result, int count, Map<Item, Integer> ingredients) { }

    private static List<Row> alloyRows() {
        return List.of(
                new Row("billet_thorium_fuel_from_billets", NtmItems.BILLET_THORIUM_FUEL.get(), 6, Map.of(NtmItems.BILLET_TH232.get(), 5, NtmItems.BILLET_U233.get(), 1)),
                new Row("billet_thorium_fuel_from_nuggets", NtmItems.BILLET_THORIUM_FUEL.get(), 1, Map.of(NtmItems.NUGGET_TH232.get(), 5, NtmItems.NUGGET_U233.get(), 1)),
                new Row("billet_uranium_fuel_from_billets", NtmItems.BILLET_URANIUM_FUEL.get(), 6, Map.of(NtmItems.BILLET_U238.get(), 5, NtmItems.BILLET_U235.get(), 1)),
                new Row("billet_uranium_fuel_from_nuggets", NtmItems.BILLET_URANIUM_FUEL.get(), 1, Map.of(NtmItems.NUGGET_U238.get(), 5, NtmItems.NUGGET_U235.get(), 1)),
                new Row("billet_plutonium_fuel_from_billets", NtmItems.BILLET_PLUTONIUM_FUEL.get(), 3, Map.of(NtmItems.BILLET_U238.get(), 2, NtmItems.BILLET_PU_MIX.get(), 1)),
                new Row("billet_plutonium_fuel_from_nuggets", NtmItems.BILLET_PLUTONIUM_FUEL.get(), 1, Map.of(NtmItems.NUGGET_PU_MIX.get(), 2, NtmItems.NUGGET_U238.get(), 4)),
                new Row("billet_pu_mix_from_billets", NtmItems.BILLET_PU_MIX.get(), 3, Map.of(NtmItems.BILLET_PU239.get(), 2, NtmItems.BILLET_PU240.get(), 1)),
                new Row("billet_pu_mix_from_nuggets", NtmItems.BILLET_PU_MIX.get(), 1, Map.of(NtmItems.NUGGET_PU239.get(), 4, NtmItems.NUGGET_PU240.get(), 2)),
                new Row("billet_mox_fuel_from_billets", NtmItems.BILLET_MOX_FUEL.get(), 3, Map.of(NtmItems.BILLET_URANIUM_FUEL.get(), 2, NtmItems.BILLET_PU239.get(), 1)),
                new Row("billet_mox_fuel_from_nuggets", NtmItems.BILLET_MOX_FUEL.get(), 1, Map.of(NtmItems.NUGGET_PU239.get(), 2, NtmItems.NUGGET_URANIUM_FUEL.get(), 4)),
                new Row("ingot_pu_mix_from_nuggets", NtmItems.INGOT_PU_MIX.get(), 1, Map.of(NtmItems.NUGGET_PU239.get(), 6, NtmItems.NUGGET_PU240.get(), 3)));
    }

    private record RodRow(String id, ZirnoxType type, Map<Item, Integer> ingredients) { }

    private static List<RodRow> rodRows() {
        Item empty = NtmItems.ROD_ZIRNOX_EMPTY.get();
        return List.of(
                new RodRow("rod_zirnox_mox_fuel", ZirnoxType.MOX_FUEL, Map.of(empty, 1, NtmItems.BILLET_MOX_FUEL.get(), 2)),
                new RodRow("rod_zirnox_plutonium_fuel", ZirnoxType.PLUTONIUM_FUEL, Map.of(empty, 1, NtmItems.BILLET_PLUTONIUM_FUEL.get(), 2)),
                new RodRow("rod_zirnox_u233_fuel", ZirnoxType.U233_FUEL, Map.of(empty, 1, NtmItems.BILLET_U233.get(), 2)),
                new RodRow("rod_zirnox_zfb_mox", ZirnoxType.ZFB_MOX, Map.of(empty, 1, NtmItems.BILLET_MOX_FUEL.get(), 1, NtmItems.BILLET_ZIRCONIUM.get(), 1)),
                new RodRow("rod_zirnox_thorium_fuel", ZirnoxType.THORIUM_FUEL, Map.of(empty, 1, NtmItems.BILLET_THORIUM_FUEL.get(), 2)));
    }

    // 1. The eleven fuel alloy rows

    @GameTest(template = TEMPLATE, timeoutTicks = 100)
    public static void fuel_alloy_recipes(GameTestHelper helper) {
        guard(() -> {
            List<Row> rows = alloyRows();
            check(rows.size() == 11, "the expected table has " + rows.size() + " rows, expected 11");
            for(Row row : rows) {
                ShapelessRecipe recipe = shapeless(helper, row.id(), row.ingredients());
                ItemStack result = recipe.getResultItem(helper.getLevel().registryAccess());
                check(result.is(row.result()) && result.getCount() == row.count() && !TagsUtil.hasCustomData(result), row.id() + " yields " + result + ", expected " + row.count() + " x " + row.result());

                ItemStack crafted = craft(helper, row.id(), grid(row.ingredients()));
                check(crafted.is(row.result()) && crafted.getCount() == row.count(), row.id() + " crafts " + crafted + ", expected " + row.count() + " x " + row.result());
            }

            // The :163 grid with one uranium-238 nugget swapped for a uranium-235 nugget is not any recipe.
            List<ItemStack> wrong = new ArrayList<>();
            wrong.add(new ItemStack(NtmItems.NUGGET_PU_MIX.get(), 1));
            wrong.add(new ItemStack(NtmItems.NUGGET_PU_MIX.get(), 1));
            for(int i = 0; i < 3; i++) wrong.add(new ItemStack(NtmItems.NUGGET_U238.get()));
            wrong.add(new ItemStack(NtmItems.NUGGET_U235.get()));
            List<RecipeHolder<CraftingRecipe>> found = matching(helper, wrong);
            check(found.isEmpty(), "two pu_mix, three u238 and one u235 nuggets match " + describe(found));
            Optional<RecipeHolder<CraftingRecipe>> first = helper.getLevel().getRecipeManager().getRecipeFor(RecipeType.CRAFTING, input(wrong), helper.getLevel());
            check(first.isEmpty(), "getRecipeFor finds " + first.map(RecipeHolder::id).orElse(null) + " for the wrong nugget mix");
        }).run();
        passed("fuel_alloy_recipes").run();
        helper.succeed();
    }

    // 2. The five ZIRNOX rod recipes

    @GameTest(template = TEMPLATE, timeoutTicks = 100)
    public static void zirnox_rod_recipes(GameTestHelper helper) {
        guard(() -> {
            for(RodRow row : rodRows()) {
                ShapelessRecipe recipe = shapeless(helper, row.id(), row.ingredients());
                ItemStack result = recipe.getResultItem(helper.getLevel().registryAccess());
                assertFreshRod(result, row.type(), row.id());

                ItemStack crafted = craft(helper, row.id(), grid(row.ingredients()));
                assertFreshRod(crafted, row.type(), row.id() + " (crafted)");
            }

            // The deferred LES rod (RodRecipes.java:35, no billet_les source) and lithium rod (:36, no lithium ingot) have no recipe.
            TreeSet<Integer> metas = new TreeSet<>();
            for(RecipeHolder<CraftingRecipe> holder : helper.getLevel().getRecipeManager().getAllRecipesFor(RecipeType.CRAFTING)) {
                ItemStack result = holder.value().getResultItem(helper.getLevel().registryAccess());
                if(result.is(NtmItems.ROD_ZIRNOX.get())) metas.add(MetaHelper.getMeta(result));
            }
            LOGGER.info("[hbm-fuel] crafting recipes yield ROD_ZIRNOX metas {}", metas);
            check(!metas.contains(ZirnoxType.LES_FUEL.ordinal()), "a crafting recipe yields the LES rod");
            check(!metas.contains(ZirnoxType.LITHIUM.ordinal()), "a crafting recipe yields the lithium rod");
            for(ZirnoxType type : List.of(ZirnoxType.NATURAL_URANIUM_FUEL, ZirnoxType.URANIUM_FUEL, ZirnoxType.TH232, ZirnoxType.THORIUM_FUEL,
                    ZirnoxType.U235_FUEL, ZirnoxType.MOX_FUEL, ZirnoxType.PLUTONIUM_FUEL, ZirnoxType.U233_FUEL, ZirnoxType.ZFB_MOX)) {
                check(metas.contains(type.ordinal()), "no crafting recipe yields " + type);
            }
        }).run();
        passed("zirnox_rod_recipes").run();
        helper.succeed();
    }

    private static void assertFreshRod(ItemStack rod, ZirnoxType type, String label) {
        check(rod.is(NtmItems.ROD_ZIRNOX.get()) && rod.getCount() == 1 && MetaHelper.getMeta(rod) == type.ordinal(), label + " yields " + rod + " with meta " + MetaHelper.getMeta(rod) + ", expected one " + type);
        check(!TagsUtil.hasCustomData(rod), label + " carries custom data " + TagsUtil.getCustomData(rod));
        check(ItemStack.isSameItemSameComponents(rod, zirnoxRod(type)), label + " differs from a fresh " + type + " rod");
    }

    // 3. Heat and life of the new rods

    private static final int HEAT_WINDOW = 60;

    /**
     * One isolated rod in slot 0 of each reactor (no neighbours, so one decay step per tick), water and carbon dioxide full as
     * {@code fillZirnox} does, plus a natural uranium reference. updateEntity adds {@code type.heat} per decay step and then
     * subtracts heat. With a full steam tank the steam branch is skipped and the loss is the constant 10 per tick (the loss with
     * a free steam tank is (int)(heat x pressure / 1,000,000) and depends on the heat reached, which would make the gain awkward
     * to state exactly). So the heat per tick is exactly {@code type.heat - 10}, the life gain exactly 1, and the gain of a rod
     * above the natural uranium reference is exactly {@code type.heat - 30} per tick whatever the constant.
     */
    @GameTest(template = TEMPLATE, timeoutTicks = 200)
    public static void zirnox_new_rods_heat_and_life(GameTestHelper helper) {
        ZirnoxType[] types = { ZirnoxType.MOX_FUEL, ZirnoxType.PLUTONIUM_FUEL, ZirnoxType.U233_FUEL, ZirnoxType.ZFB_MOX, ZirnoxType.NATURAL_URANIUM_FUEL };
        BlockPos[] cores = { new BlockPos(3, 1, 5), new BlockPos(8, 1, 5), new BlockPos(13, 1, 5), new BlockPos(3, 1, 11), new BlockPos(8, 1, 11) };
        int reference = 4;
        ReactorZirnoxBlockEntity[] reactors = new ReactorZirnoxBlockEntity[types.length];
        for(int i = 0; i < types.length; i++) {
            reactors[i] = placeZirnox(helper, cores[i]);
            reactors[i].setItem(0, zirnoxRod(types[i]));
            fillZirnox(reactors[i]);
            reactors[i].steam.setFill(reactors[i].steam.getMaxFill());
            reactors[i].isOn = true;
        }
        int[] baseHeat = new int[types.length];
        int[] heat = new int[types.length];
        int[] life = new int[types.length];
        long[] last = new long[1];
        long[] total = new long[1];

        helper.startSequence()
                .thenExecute(guard(() -> {
                    last[0] = helper.getTick();
                    for(int i = 0; i < types.length; i++) {
                        baseHeat[i] = heat[i] = reactors[i].heat;
                        life[i] = ZirnoxRodItem.getLifeTime(reactors[i].getItem(0));
                    }
                }))
                .thenExecuteFor(HEAT_WINDOW, guard(() -> {
                    long dt = helper.getTick() - last[0];
                    last[0] = helper.getTick();
                    total[0] += dt;
                    for(int i = 0; i < types.length; i++) {
                        ReactorZirnoxBlockEntity be = reactors[i];
                        check(helper.getLevel().getBlockEntity(helper.absolutePos(cores[i])) == be, types[i] + " reactor was replaced");
                        ItemStack rod = be.getItem(0);
                        check(rod.is(NtmItems.ROD_ZIRNOX.get()) && MetaHelper.getMeta(rod) == types[i].ordinal(), types[i] + " rod changed into " + rod);
                        int dh = be.heat - heat[i];
                        int dl = ZirnoxRodItem.getLifeTime(rod) - life[i];
                        check(dh == dt * (types[i].heat - 10), types[i] + " gained " + dh + " heat over " + dt + " ticks, expected " + dt * (types[i].heat - 10));
                        check(dl == dt, types[i] + " gained " + dl + " life over " + dt + " ticks, expected " + dt);
                        check(be.heat < ReactorZirnoxBlockEntity.maxHeat && be.pressure < ReactorZirnoxBlockEntity.maxPressure, types[i] + " reactor heat " + be.heat + ", pressure " + be.pressure);
                        heat[i] = be.heat;
                        life[i] = ZirnoxRodItem.getLifeTime(rod);
                        be.steam.setFill(be.steam.getMaxFill());
                    }
                }))
                .thenExecute(guard(() -> {
                    check(total[0] >= HEAT_WINDOW - 1, "only " + total[0] + " ticks were sampled");
                    for(int i = 0; i < types.length; i++) {
                        long gain = heat[i] - baseHeat[i];
                        long referenceGain = heat[reference] - baseHeat[reference];
                        LOGGER.info("[hbm-fuel] {} gained {} heat over {} ticks (reference {}), life now {}", types[i], gain, total[0], referenceGain, life[i]);
                        check(gain - referenceGain == total[0] * (types[i].heat - ZirnoxType.NATURAL_URANIUM_FUEL.heat), types[i] + " gained " + (gain - referenceGain) + " more heat than the natural uranium rod, expected "
                                + total[0] * (types[i].heat - ZirnoxType.NATURAL_URANIUM_FUEL.heat));
                    }
                }))
                .thenExecute(passed("zirnox_new_rods_heat_and_life"))
                .thenSucceed();
    }

    // 4. Depletion into the depleted rods and the 20C waste rows

    private record Depletion(ZirnoxType type, Item depleted, Item waste) { }

    private static List<Depletion> depletions() {
        return List.of(
                new Depletion(ZirnoxType.MOX_FUEL, NtmItems.ROD_ZIRNOX_MOX_FUEL_DEPLETED.get(), NtmItems.WASTE_MOX.get()),
                new Depletion(ZirnoxType.PLUTONIUM_FUEL, NtmItems.ROD_ZIRNOX_PLUTONIUM_FUEL_DEPLETED.get(), NtmItems.WASTE_PLUTONIUM.get()),
                new Depletion(ZirnoxType.U233_FUEL, NtmItems.ROD_ZIRNOX_U233_FUEL_DEPLETED.get(), NtmItems.WASTE_U233.get()),
                new Depletion(ZirnoxType.ZFB_MOX, NtmItems.ROD_ZIRNOX_ZFB_MOX_DEPLETED.get(), NtmItems.WASTE_ZFB_MOX.get()));
    }

    private static final int DEPLETE_LEFT = 3;
    private static final int DEPLETE_WINDOW = 8;

    /**
     * An isolated rod preset to {@code maxLife - 3} gains one life per tick, reaches exactly {@code maxLife}, and is replaced by
     * the depleted rod on the update that takes it above it (ReactorZirnoxBlockEntity.decay). The depleted rod alone in a
     * crafting grid then yields two hot (META 1) waste items.
     */
    @GameTest(template = TEMPLATE, timeoutTicks = 200)
    public static void zirnox_new_rods_deplete(GameTestHelper helper) {
        List<Depletion> cases = depletions();
        BlockPos[] cores = { new BlockPos(3, 1, 5), new BlockPos(8, 1, 5), new BlockPos(13, 1, 5), new BlockPos(3, 1, 11) };
        ReactorZirnoxBlockEntity[] reactors = new ReactorZirnoxBlockEntity[cases.size()];
        @SuppressWarnings("unchecked")
        List<ItemStack>[] samples = new List[cases.size()];
        for(int i = 0; i < cases.size(); i++) {
            ZirnoxType type = cases.get(i).type();
            reactors[i] = placeZirnox(helper, cores[i]);
            reactors[i].setItem(0, zirnoxRod(type, type.maxLife - DEPLETE_LEFT));
            fillZirnox(reactors[i]);
            reactors[i].steam.setFill(reactors[i].steam.getMaxFill());
            reactors[i].isOn = true;
            samples[i] = new ArrayList<>();
        }

        helper.startSequence()
                .thenExecute(guard(() -> {
                    for(int i = 0; i < cases.size(); i++) samples[i].add(reactors[i].getItem(0).copy());
                }))
                .thenExecuteFor(DEPLETE_WINDOW, guard(() -> {
                    for(int i = 0; i < cases.size(); i++) {
                        check(helper.getLevel().getBlockEntity(helper.absolutePos(cores[i])) == reactors[i], cases.get(i).type() + " reactor was replaced");
                        samples[i].add(reactors[i].getItem(0).copy());
                        reactors[i].steam.setFill(reactors[i].steam.getMaxFill());
                    }
                }))
                .thenExecute(guard(() -> {
                    for(int i = 0; i < cases.size(); i++) {
                        Depletion depletion = cases.get(i);
                        ZirnoxType type = depletion.type();
                        List<ItemStack> list = samples[i];
                        int previousLife = type.maxLife - DEPLETE_LEFT;
                        int replacedAt = -1;
                        for(int s = 0; s < list.size(); s++) {
                            ItemStack stack = list.get(s);
                            if(replacedAt < 0 && stack.is(NtmItems.ROD_ZIRNOX.get())) {
                                check(MetaHelper.getMeta(stack) == type.ordinal(), type + " rod changed meta to " + MetaHelper.getMeta(stack) + " at sample " + s);
                                int now = ZirnoxRodItem.getLifeTime(stack);
                                check(now >= previousLife && now <= type.maxLife, type + " life " + now + " at sample " + s + " after " + previousLife + ", max " + type.maxLife);
                                previousLife = now;
                            } else {
                                if(replacedAt < 0) replacedAt = s;
                                check(stack.is(depletion.depleted()) && stack.getCount() == 1, type + " slot holds " + stack + " at sample " + s + ", expected one " + depletion.depleted());
                            }
                        }
                        check(replacedAt > 0, type + " rod was never replaced within " + DEPLETE_WINDOW + " ticks");
                        check(previousLife == type.maxLife, type + " was replaced after life " + previousLife + ", expected exactly its maximum " + type.maxLife);

                        // 20C: the depleted rod alone in the grid gives two hot waste items.
                        ItemStack depleted = reactors[i].getItem(0).copy();
                        ItemStack waste = craft(helper, path(depletion.waste()),List.of(depleted));
                        check(waste.is(depletion.waste()) && waste.getCount() == 2 && MetaHelper.getMeta(waste) == DepletedFuelItem.HOT,
                                type + " depleted rod crafts " + waste + " with META " + MetaHelper.getMeta(waste) + ", expected 2 hot " + depletion.waste());
                        LOGGER.info("[hbm-fuel] {} rod replaced by {} at sample {} of {}, life peak {}", type, depletion.depleted(), replacedAt, list.size(), previousLife);
                    }
                }))
                .thenExecute(passed("zirnox_new_rods_deplete"))
                .thenSucceed();
    }

    // 5. PUREX output to the new rods

    /**
     * The C3 closure through the RecipeManager only: the real PUREX outputs of the natural uranium and thorium rows feed the alloy and
     * rod recipes. The nuggets a PUREX run does not supply (the other U238 nuggets of the plutonium fuel row, the uranium fuel nuggets
     * of the MOX row, the thorium billets) stand for the gas centrifuge and the mined material, as in the C4 ledger.
     */
    @GameTest(template = TEMPLATE, timeoutTicks = 100)
    public static void fuel_closure_purex_to_rods(GameTestHelper helper) {
        guard(() -> {
            Item empty = NtmItems.ROD_ZIRNOX_EMPTY.get();
            ItemStack[] natural = purexOutputs("purex.zirnoxnu");
            check(natural.length == 4, "purex.zirnoxnu has " + natural.length + " outputs, expected 4");
            assertStack(natural[0], NtmItems.NUGGET_U238.get(), 1, "purex.zirnoxnu output 0");
            assertStack(natural[1], NtmItems.NUGGET_PU_MIX.get(), 2, "purex.zirnoxnu output 1");
            assertStack(natural[2], NtmItems.NUGGET_PU239.get(), 1, "purex.zirnoxnu output 2");
            assertStack(natural[3], NtmItems.NUCLEAR_WASTE_TINY.get(), 2, "purex.zirnoxnu output 3");

            // Plutonium: the two pu_mix nuggets of one run (the run's own U238 nugget plus three from the gas centrifuge or natural
            // uranium) make one plutonium fuel billet; two billets and an empty rod make the plutonium rod.
            ItemStack puBillet = craft(helper, "billet_plutonium_fuel_from_nuggets", List.of(copy(natural[1], natural[1].getCount()), copy(natural[0], natural[0].getCount() + 3)));
            assertStack(puBillet, NtmItems.BILLET_PLUTONIUM_FUEL.get(), 1, "the plutonium fuel billet");
            ItemStack puRod = craft(helper, "rod_zirnox_plutonium_fuel", List.of(new ItemStack(empty), copy(puBillet, 1), copy(puBillet, 1)));
            assertFreshRod(puRod, ZirnoxType.PLUTONIUM_FUEL, "the plutonium rod");

            // Thorium: three runs of the thorium row give six uranium-233 nuggets, which make a billet in the nnn/nnn shape.
            ItemStack[] thorium = purexOutputs("purex.zirnoxthmeu");
            check(thorium.length == 4, "purex.zirnoxthmeu has " + thorium.length + " outputs, expected 4");
            assertStack(thorium[2], NtmItems.NUGGET_U233.get(), 2, "purex.zirnoxthmeu output 2");
            ItemStack u233Billet = craft(helper, "billet_u233_from_6_nugget_u233", List.of(copy(thorium[2], thorium[2].getCount() * 3)));
            assertStack(u233Billet, NtmItems.BILLET_U233.get(), 1, "the uranium-233 billet");
            ItemStack u233Rod = craft(helper, "rod_zirnox_u233_fuel", List.of(new ItemStack(empty), copy(u233Billet, 1), copy(u233Billet, 1)));
            assertFreshRod(u233Rod, ZirnoxType.U233_FUEL, "the uranium-233 rod");
            ItemStack thoriumBillets = craft(helper, "billet_thorium_fuel_from_billets", List.of(new ItemStack(NtmItems.BILLET_TH232.get(), 5), copy(u233Billet, 1)));
            assertStack(thoriumBillets, NtmItems.BILLET_THORIUM_FUEL.get(), 6, "the thorium fuel billets");

            // MOX: two natural uranium runs give two plutonium-239 nuggets, which with four uranium fuel nuggets make a MOX billet.
            ItemStack moxBillet = craft(helper, "billet_mox_fuel_from_nuggets", List.of(copy(natural[2], natural[2].getCount() * 2), new ItemStack(NtmItems.NUGGET_URANIUM_FUEL.get(), 4)));
            assertStack(moxBillet, NtmItems.BILLET_MOX_FUEL.get(), 1, "the MOX billet");
            ItemStack moxRod = craft(helper, "rod_zirnox_mox_fuel", List.of(new ItemStack(empty), copy(moxBillet, 1), copy(moxBillet, 1)));
            assertFreshRod(moxRod, ZirnoxType.MOX_FUEL, "the MOX rod");
            ItemStack zfbRod = craft(helper, "rod_zirnox_zfb_mox", List.of(new ItemStack(empty), copy(moxBillet, 1), new ItemStack(NtmItems.BILLET_ZIRCONIUM.get())));
            assertFreshRod(zfbRod, ZirnoxType.ZFB_MOX, "the ZFB MOX rod");

            // No ZIRNOX row of the PUREX takes a hot (META 1) waste item (covered in 22B; one line here).
            List<Item> wastes = List.of(NtmItems.WASTE_NATURAL_URANIUM.get(), NtmItems.WASTE_URANIUM.get(), NtmItems.WASTE_THORIUM.get(), NtmItems.WASTE_MOX.get(), NtmItems.WASTE_PLUTONIUM.get(),
                    NtmItems.WASTE_U233.get(), NtmItems.WASTE_U235.get(), NtmItems.WASTE_SCHRABIDIUM.get(), NtmItems.WASTE_ZFB_MOX.get());
            List<GenericRecipe> zirnox = PUREXRecipes.INSTANCE.autoSwitchGroups.get("autoswitch.zirnox");
            check(zirnox != null && !zirnox.isEmpty(), "autoswitch.zirnox is empty");
            for(GenericRecipe recipe : zirnox) {
                for(Item waste : wastes) {
                    ItemStack hot = MetaHelper.newStack(waste, 1, DepletedFuelItem.HOT);
                    check(!recipe.inputItem[0].matchesRecipe(hot, false) && !recipe.inputItem[0].matchesRecipe(hot, true), recipe.getInternalName() + " accepts the hot " + hot);
                }
            }
        }).run();
        passed("fuel_closure_purex_to_rods").run();
        helper.succeed();
    }

    private static ItemStack[] purexOutputs(String name) {
        GenericRecipe recipe = PUREXRecipes.INSTANCE.recipeNameMap.get(name);
        check(recipe != null && recipe.outputItem != null, name + " is missing");
        ItemStack[] outputs = new ItemStack[recipe.outputItem.length];
        for(int i = 0; i < outputs.length; i++) {
            check(!recipe.outputItem[i].possibleMultiOutput(), name + " output " + i + " is a random pool");
            outputs[i] = recipe.outputItem[i].getSingle();
        }
        return outputs;
    }

    private static void assertStack(ItemStack stack, Item item, int count, String label) {
        check(stack.is(item) && stack.getCount() == count, label + " is " + stack + ", expected " + count + " x " + item);
    }

    private static ItemStack copy(ItemStack stack, int count) {
        return stack.copyWithCount(count);
    }

    // Reactor helpers (SmokeGameTests keeps its own private)

    private static ReactorZirnoxBlockEntity placeZirnox(GameTestHelper helper, BlockPos core) {
        SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.REACTOR_ZIRNOX.get(), core, Direction.NORTH);
        ReactorZirnoxBlockEntity be = SmokeTestSupport.blockEntity(helper, core, ReactorZirnoxBlockEntity.class);
        check(!be.redstonePowered, "the reactor is redstone powered");
        return be;
    }

    private static void fillZirnox(ReactorZirnoxBlockEntity be) {
        be.water.setFill(be.water.getMaxFill());
        be.carbonDioxide.setFill(be.carbonDioxide.getMaxFill());
    }

    private static ItemStack zirnoxRod(ZirnoxType type) {
        return MetaHelper.newStack(NtmItems.ROD_ZIRNOX.get(), 1, type.ordinal());
    }

    private static ItemStack zirnoxRod(ZirnoxType type, int life) {
        ItemStack rod = zirnoxRod(type);
        ZirnoxRodItem.setLifeTime(rod, life);
        return rod;
    }

    // Crafting helpers

    private static ResourceLocation id(String path) {
        return ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path);
    }

    /** The recipe with this id, which must be a shapeless crafting recipe whose ingredients are exactly the single-item multiset. */
    private static ShapelessRecipe shapeless(GameTestHelper helper, String path, Map<Item, Integer> expected) {
        Optional<RecipeHolder<?>> holder = helper.getLevel().getRecipeManager().byKey(id(path));
        check(holder.isPresent(), "recipe " + id(path) + " is not loaded");
        check(holder.get().value() instanceof ShapelessRecipe, "recipe " + id(path) + " is a " + holder.get().value().getClass().getSimpleName() + ", expected a shapeless recipe");
        ShapelessRecipe recipe = (ShapelessRecipe) holder.get().value();
        Map<Item, Integer> actual = new HashMap<>();
        for(Ingredient ingredient : recipe.getIngredients()) {
            ItemStack[] items = ingredient.getItems();
            check(items.length == 1, path + " has an ingredient that accepts " + items.length + " items");
            actual.merge(items[0].getItem(), 1, Integer::sum);
        }
        check(actual.equals(expected), path + " takes " + actual + ", expected " + expected);
        return recipe;
    }

    private static List<ItemStack> grid(Map<Item, Integer> ingredients) {
        List<ItemStack> stacks = new ArrayList<>();
        for(Map.Entry<Item, Integer> entry : ingredients.entrySet()) {
            for(int i = 0; i < entry.getValue(); i++) stacks.add(new ItemStack(entry.getKey()));
        }
        return stacks;
    }

    /** The grid a crafting table passes to the recipe manager: cells laid out from the top left of a 3x3 grid, trimmed to their bounding box. */
    private static CraftingInput input(List<ItemStack> items) {
        List<ItemStack> cells = new ArrayList<>();
        for(ItemStack stack : items) {
            // A stack of several nuggets stands for that many single cells.
            for(int i = 0; i < stack.getCount(); i++) cells.add(stack.copyWithCount(1));
        }
        check(cells.size() <= 9, "the grid has " + cells.size() + " items");
        while(cells.size() < 9) cells.add(ItemStack.EMPTY);
        return CraftingInput.ofPositioned(3, 3, cells).input();
    }

    private static List<RecipeHolder<CraftingRecipe>> matching(GameTestHelper helper, List<ItemStack> items) {
        return helper.getLevel().getRecipeManager().getRecipesFor(RecipeType.CRAFTING, input(items), helper.getLevel());
    }

    private static String describe(List<RecipeHolder<CraftingRecipe>> holders) {
        List<ResourceLocation> ids = new ArrayList<>();
        for(RecipeHolder<CraftingRecipe> holder : holders) ids.add(holder.id());
        return ids.toString();
    }

    /** Crafts the grid, requires exactly the recipe {@code path} to match it (no other recipe shadows it) and returns the result. */
    private static ItemStack craft(GameTestHelper helper, String path, List<ItemStack> items) {
        CraftingInput input = input(items);
        List<RecipeHolder<CraftingRecipe>> all = helper.getLevel().getRecipeManager().getRecipesFor(RecipeType.CRAFTING, input, helper.getLevel());
        check(all.size() == 1 && all.get(0).id().equals(id(path)), "the grid " + items + " matches " + describe(all) + ", expected only " + id(path));
        Optional<RecipeHolder<CraftingRecipe>> first = helper.getLevel().getRecipeManager().getRecipeFor(RecipeType.CRAFTING, input, helper.getLevel());
        check(first.isPresent() && first.get().id().equals(id(path)), "getRecipeFor returns " + first.map(RecipeHolder::id).orElse(null) + " for " + items + ", expected " + id(path));
        return first.get().value().assemble(input, helper.getLevel().registryAccess());
    }

    /** The GameTest framework logs only failures; this line lets the verifier see that every test of this class ran to its success call. */
    private static Runnable passed(String test) {
        return () -> LOGGER.info("[hbm-fuel] {} passed", test);
    }

    /** The registry path of an item, which is also the id of its recipe (addWasteRecipe). */
    private static String path(Item item) {
        return BuiltInRegistries.ITEM.getKey(item).getPath();
    }
}
