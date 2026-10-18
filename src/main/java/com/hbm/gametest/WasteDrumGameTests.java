package com.hbm.gametest;

import com.hbm.blockentity.machine.MachineWasteDrumBlockEntity;
import com.hbm.blocks.NtmBlocks;
import com.hbm.handler.radiation.ChunkRadiationManager;
import com.hbm.hazard.HazardRegistry;
import com.hbm.hazard.HazardSystem;
import com.hbm.hazard.type.HazardTypeBase;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.menus.MachineWasteDrumMenu;
import com.hbm.inventory.recipes.FuelPoolRecipes;
import com.hbm.inventory.recipes.FuelPoolRecipes.FuelPoolRecipe;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.DepletedFuelItem;
import com.hbm.main.NuclearTechMod;
import com.hbm.network.toclient.FuelPoolRecipesPacket;
import com.mojang.logging.LogUtils;
import io.netty.buffer.Unpooled;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.NonNullList;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.contents.TranslatableContents;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.BlockTags;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.ClickType;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.item.crafting.CraftingInput;
import net.minecraft.world.item.crafting.CraftingRecipe;
import net.minecraft.world.item.crafting.Ingredient;
import net.minecraft.world.item.crafting.Recipe;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.ShapedRecipe;
import net.minecraft.world.item.crafting.ShapelessRecipe;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.HopperBlock;
import net.minecraft.world.level.block.LiquidBlock;
import net.minecraft.world.level.block.SlabBlock;
import net.minecraft.world.level.block.entity.HopperBlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.chunk.LevelChunk;
import net.minecraft.world.level.levelgen.LegacyRandomSource;
import net.minecraft.world.level.material.Fluids;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import net.neoforged.neoforge.network.connection.ConnectionType;
import net.neoforged.neoforge.registries.DeferredItem;
import org.slf4j.Logger;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.function.IntUnaryOperator;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for the depleted ZIRNOX waste and the spent fuel pool drum (original ItemDepletedFuel, TileEntityWasteDrum,
 * ContainerWasteDrum and FuelPoolRecipes): recipes, hazards, the waste item entity, drops, automation and menu rules, water
 * counting, the cooling rolls, persistence and the recipe sync. Same template and conventions as {@link SmokeGameTests}. The
 * drum ticks once per server tick, so a step scheduled N ticks after another sees exactly N drum updates. Drums that run for
 * many ticks sit in a stone shell whose six face cells hold water sources or stone, so the water cannot spread and change
 * the neighbour count.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class WasteDrumGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final BlockPos CENTER = new BlockPos(8, 3, 8);
    private static final int[] ALL_SLOTS = { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 };

    /** One row per waste item in the FuelPoolRecipes default order, with its depleted rod and the HazardRegistry multiplier. */
    private record Waste(DeferredItem<Item> item, DeferredItem<Item> rod, float mult) {
        Item get() { return item.get(); }
        ItemStack hot() { return MetaHelper.newStack(item.get(), 1, DepletedFuelItem.HOT); }
        ItemStack cool() { return new ItemStack(item.get()); }
        String path() { return BuiltInRegistries.ITEM.getKey(item.get()).getPath(); }
    }

    private static final List<Waste> WASTES = List.of(
            new Waste(NtmItems.WASTE_NATURAL_URANIUM, NtmItems.ROD_ZIRNOX_NATURAL_URANIUM_FUEL_DEPLETED, 11.5F),
            new Waste(NtmItems.WASTE_URANIUM, NtmItems.ROD_ZIRNOX_URANIUM_FUEL_DEPLETED, 10F),
            new Waste(NtmItems.WASTE_THORIUM, NtmItems.ROD_ZIRNOX_THORIUM_FUEL_DEPLETED, 7.5F),
            new Waste(NtmItems.WASTE_MOX, NtmItems.ROD_ZIRNOX_MOX_FUEL_DEPLETED, 10F),
            new Waste(NtmItems.WASTE_PLUTONIUM, NtmItems.ROD_ZIRNOX_PLUTONIUM_FUEL_DEPLETED, 12.5F),
            new Waste(NtmItems.WASTE_U233, NtmItems.ROD_ZIRNOX_U233_FUEL_DEPLETED, 10F),
            new Waste(NtmItems.WASTE_U235, NtmItems.ROD_ZIRNOX_U235_FUEL_DEPLETED, 11F),
            new Waste(NtmItems.WASTE_SCHRABIDIUM, NtmItems.ROD_ZIRNOX_LES_FUEL_DEPLETED, 15F),
            new Waste(NtmItems.WASTE_ZFB_MOX, NtmItems.ROD_ZIRNOX_ZFB_MOX_DEPLETED, 5F));

    /** Records every cooling roll and answers it from a script instead of the level random. */
    private static final class ScriptedRandom extends LegacyRandomSource {
        final List<Integer> bounds = new ArrayList<>();
        IntUnaryOperator answer;

        ScriptedRandom(IntUnaryOperator answer) {
            super(0L);
            this.answer = answer;
        }

        @Override
        public int nextInt(int bound) {
            bounds.add(bound);
            return answer.applyAsInt(bound);
        }
    }

    // Recipes and the fuel pool table

    @GameTest(template = TEMPLATE, timeoutTicks = 100)
    public static void recipes_present_20c(GameTestHelper helper) {
        guard(() -> {
            HolderLookup.Provider registries = helper.getLevel().registryAccess();
            for(Waste waste : WASTES) {
                Recipe<?> recipe = craftingRecipe(helper, waste.path());
                check(recipe instanceof ShapelessRecipe, waste.path() + " is " + recipe.getClass().getSimpleName() + ", expected a shapeless recipe");
                CraftingRecipe crafting = (CraftingRecipe) recipe;
                ItemStack rod = new ItemStack(waste.rod().get());
                List<Ingredient> ingredients = recipe.getIngredients();
                check(ingredients.size() == 1 && accepts(ingredients.get(0), rod.getItem()), waste.path() + " takes " + describe(ingredients) + ", expected one " + rod.getItem());

                CraftingInput input = CraftingInput.of(1, 1, List.of(rod));
                check(crafting.matches(input, helper.getLevel()), waste.path() + " does not match a single " + rod.getItem());
                ItemStack result = crafting.assemble(input, registries);
                check(result.getCount() == 2 && ItemStack.isSameItemSameComponents(result, waste.hot()) && MetaHelper.getMeta(result) == DepletedFuelItem.HOT,
                        waste.path() + " yields " + result + " with META " + MetaHelper.getMeta(result) + ", expected 2 hot " + waste.get());
                NonNullList<ItemStack> remaining = crafting.getRemainingItems(input);
                check(remaining.size() == 1 && remaining.get(0).is(NtmItems.ROD_ZIRNOX_EMPTY.get()) && remaining.get(0).getCount() == 1,
                        waste.path() + " leaves " + remaining + ", expected one rod_zirnox_empty");
            }

            assertShapeless(helper, "rod_empty_from_rod_dual_empty", NtmItems.ROD_DUAL_EMPTY.get(), 1, NtmItems.ROD_EMPTY.get(), 2);
            assertShapeless(helper, "rod_dual_empty", NtmItems.ROD_EMPTY.get(), 2, NtmItems.ROD_DUAL_EMPTY.get(), 1);
            assertShapeless(helper, "rod_empty_from_rod_quad_empty", NtmItems.ROD_QUAD_EMPTY.get(), 1, NtmItems.ROD_EMPTY.get(), 4);
            assertShapeless(helper, "rod_quad_empty", NtmItems.ROD_EMPTY.get(), 4, NtmItems.ROD_QUAD_EMPTY.get(), 1);
            assertShapeless(helper, "rod_quad_empty_from_rod_dual_empty", NtmItems.ROD_DUAL_EMPTY.get(), 2, NtmItems.ROD_QUAD_EMPTY.get(), 1);
            assertShaped(helper, "rod_empty", NtmItems.ROD_EMPTY.get(), 16, new String[] { "SSS", "L L", "SSS" },
                    Map.of('S', NtmItems.PLATE_STEEL.get(), 'L', NtmItems.PLATE_LEAD.get()));
            assertShaped(helper, "machine_waste_drum", NtmBlocks.MACHINE_WASTE_DRUM.get().asItem(), 1, new String[] { "LRL", "BRB", "LRL" },
                    Map.of('L', NtmItems.INGOT_LEAD.get(), 'R', NtmItems.ROD_QUAD_EMPTY.get(), 'B', Items.IRON_BARS));

            List<FuelPoolRecipe> rows = FuelPoolRecipes.getJeiRecipes();
            check(rows.size() == WASTES.size(), "the fuel pool table has " + rows.size() + " rows, expected " + WASTES.size());
            for(int i = 0; i < WASTES.size(); i++) {
                Waste waste = WASTES.get(i);
                FuelPoolRecipe row = rows.get(i);
                check(row.input == waste.get() && row.inputMeta == DepletedFuelItem.HOT && row.outputItem == waste.get() && row.outputCount == 1 && row.outputMeta == DepletedFuelItem.COOL,
                        "fuel pool row " + i + " is " + row.key() + " -> " + row.output() + " META " + row.outputMeta + ", expected hot " + waste.path() + " -> cool");
                check(ItemStack.isSameItemSameComponents(row.input(), waste.hot()), "fuel pool row " + i + " input " + row.input() + " is not hot " + waste.path());
                ItemStack output = row.output();
                check(output.getCount() == 1 && ItemStack.isSameItemSameComponents(output, new ItemStack(waste.get())) && output.getComponentsPatch().isEmpty(),
                        "fuel pool row " + i + " output " + output + " carries " + output.getComponentsPatch() + ", expected a plain " + waste.path());
                check(FuelPoolRecipes.isKey(waste.hot()) && !FuelPoolRecipes.isKey(waste.cool()), waste.path() + ": hot is key " + FuelPoolRecipes.isKey(waste.hot()) + ", cool is key " + FuelPoolRecipes.isKey(waste.cool()));
                ItemStack lookup = FuelPoolRecipes.getOutput(waste.hot());
                check(lookup != null && ItemStack.matches(lookup, waste.cool()), waste.path() + ": getOutput(hot) is " + lookup);
                check(FuelPoolRecipes.getOutput(waste.cool()) == null, waste.path() + ": cool waste has an output " + FuelPoolRecipes.getOutput(waste.cool()));
            }
            assertSameRows(FuelPoolRecipes.getDefaultRecipes(), rows, "default table");
        }).run();
        helper.succeed();
    }

    private static Recipe<?> craftingRecipe(GameTestHelper helper, String path) {
        ResourceLocation id = ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path);
        Optional<RecipeHolder<?>> recipe = helper.getLevel().getRecipeManager().byKey(id);
        check(recipe.isPresent(), "recipe " + id + " is not loaded");
        return recipe.get().value();
    }

    private static boolean accepts(Ingredient ingredient, Item item) {
        ItemStack[] items = ingredient.getItems();
        return items.length == 1 && items[0].is(item) && ingredient.test(new ItemStack(item));
    }

    private static String describe(List<Ingredient> ingredients) {
        List<String> names = new ArrayList<>();
        for(Ingredient ingredient : ingredients) names.add(ingredient.isEmpty() ? "empty" : Arrays.toString(ingredient.getItems()));
        return names.toString();
    }

    private static void assertShapeless(GameTestHelper helper, String path, Item input, int inputs, Item output, int count) {
        Recipe<?> recipe = craftingRecipe(helper, path);
        check(recipe instanceof ShapelessRecipe, path + " is " + recipe.getClass().getSimpleName() + ", expected a shapeless recipe");
        List<Ingredient> ingredients = recipe.getIngredients();
        boolean all = ingredients.size() == inputs;
        for(Ingredient ingredient : ingredients) all &= accepts(ingredient, input);
        check(all, path + " takes " + describe(ingredients) + ", expected " + inputs + " " + input);
        ItemStack result = recipe.getResultItem(helper.getLevel().registryAccess());
        check(result.is(output) && result.getCount() == count, path + " yields " + result + ", expected " + count + " " + output);
    }

    private static void assertShaped(GameTestHelper helper, String path, Item output, int count, String[] pattern, Map<Character, Item> key) {
        Recipe<?> recipe = craftingRecipe(helper, path);
        check(recipe instanceof ShapedRecipe, path + " is " + recipe.getClass().getSimpleName() + ", expected a shaped recipe");
        ShapedRecipe shaped = (ShapedRecipe) recipe;
        check(shaped.getWidth() == 3 && shaped.getHeight() == 3, path + " is " + shaped.getWidth() + "x" + shaped.getHeight() + ", expected 3x3");
        List<Ingredient> ingredients = shaped.getIngredients();
        check(ingredients.size() == 9, path + " has " + ingredients.size() + " cells, expected 9");
        for(int row = 0; row < 3; row++) for(int col = 0; col < 3; col++) {
            char symbol = pattern[row].charAt(col);
            Ingredient ingredient = ingredients.get(row * 3 + col);
            boolean ok = symbol == ' ' ? ingredient.isEmpty() : accepts(ingredient, key.get(symbol));
            check(ok, path + " cell " + row + "," + col + " is " + describe(List.of(ingredient)) + ", expected " + (symbol == ' ' ? "empty" : key.get(symbol)));
        }
        ItemStack result = recipe.getResultItem(helper.getLevel().registryAccess());
        check(result.is(output) && result.getCount() == count, path + " yields " + result + ", expected " + count + " " + output);
    }

    private static void assertSameRows(List<FuelPoolRecipe> actual, List<FuelPoolRecipe> expected, String label) {
        check(actual.size() == expected.size(), label + " has " + actual.size() + " rows, expected " + expected.size());
        for(int i = 0; i < expected.size(); i++) {
            check(actual.get(i).sameRecipe(expected.get(i)), label + " row " + i + " is " + actual.get(i).key() + " -> " + actual.get(i).output() + ", expected " + expected.get(i).key() + " -> " + expected.get(i).output());
        }
    }

    // Item hazards, variants and tooltip

    @GameTest(template = TEMPLATE, timeoutTicks = 100)
    public static void waste_hazards(GameTestHelper helper) {
        guard(() -> {
            for(Waste waste : WASTES) {
                float base = 7.5F * waste.mult();
                assertHazard(waste.hot(), HazardRegistry.RADIATION, base, "hot " + waste.path());
                assertHazard(waste.hot(), HazardRegistry.HOT, 5F, "hot " + waste.path());
                assertHazard(waste.cool(), HazardRegistry.RADIATION, base * 0.075F, "cool " + waste.path());
                assertHazard(waste.cool(), HazardRegistry.HOT, 0F, "cool " + waste.path());

                List<ItemStack> variants = new ArrayList<>();
                ((DepletedFuelItem) waste.get()).getSubItems(waste.get(), variants);
                check(variants.size() == 2 && ItemStack.matches(variants.get(0), waste.cool()) && ItemStack.matches(variants.get(1), waste.hot()),
                        waste.path() + " lists " + variants + ", expected META 0 then META 1");

                List<Component> hotTooltip = new ArrayList<>();
                waste.get().appendHoverText(waste.hot(), Item.TooltipContext.EMPTY, hotTooltip, TooltipFlag.NORMAL);
                check(hotTooltip.size() == 1 && hotTooltip.get(0).getContents() instanceof TranslatableContents contents && contents.getKey().equals("desc.item.wasteCooling"),
                        "hot " + waste.path() + " tooltip is " + hotTooltip + ", expected desc.item.wasteCooling");
                List<Component> coolTooltip = new ArrayList<>();
                waste.get().appendHoverText(waste.cool(), Item.TooltipContext.EMPTY, coolTooltip, TooltipFlag.NORMAL);
                check(coolTooltip.isEmpty(), "cool " + waste.path() + " tooltip is " + coolTooltip + ", expected none");
            }
            assertHazard(new ItemStack(NtmItems.NUCLEAR_WASTE.get()), HazardRegistry.RADIATION, 15F, "nuclear_waste");
            assertHazard(new ItemStack(NtmItems.BILLET_NUCLEAR_WASTE.get()), HazardRegistry.RADIATION, 7.5F, "billet_nuclear_waste");
            assertHazard(new ItemStack(NtmItems.NUCLEAR_WASTE_VITRIFIED.get()), HazardRegistry.RADIATION, 7.5F, "nuclear_waste_vitrified");
            assertHazard(new ItemStack(NtmBlocks.BLOCK_WASTE.get()), HazardRegistry.RADIATION, 150F, "block_waste");
            assertHazard(new ItemStack(NtmBlocks.BLOCK_WASTE_PAINTED.get()), HazardRegistry.RADIATION, 150F, "block_waste_painted");
            assertHazard(new ItemStack(NtmBlocks.BLOCK_WASTE_VITRIFIED.get()), HazardRegistry.RADIATION, 75F, "block_waste_vitrified");
            assertHazard(new ItemStack(NtmItems.ROD_ZIRNOX_URANIUM_FUEL_DEPLETED.get()), HazardRegistry.RADIATION, 150F, "rod_zirnox_uranium_fuel_depleted");
            assertHazard(new ItemStack(NtmItems.ROD_ZIRNOX_LES_FUEL_DEPLETED.get()), HazardRegistry.RADIATION, 225F, "rod_zirnox_les_fuel_depleted");
            assertHazard(new ItemStack(NtmItems.ROD_ZIRNOX_LES_FUEL_DEPLETED.get()), HazardRegistry.BLINDING, 20F, "rod_zirnox_les_fuel_depleted");
        }).run();
        helper.succeed();
    }

    private static void assertHazard(ItemStack stack, HazardTypeBase type, float expected, String label) {
        float actual = HazardSystem.getHazardLevelFromStack(stack, type);
        check(Math.abs(actual - expected) <= 1e-4F, label + ": " + type.getClass().getSimpleName() + " level " + actual + ", expected " + expected);
    }

    // The waste item entity

    @GameTest(template = TEMPLATE, timeoutTicks = 200)
    public static void waste_item_entity(GameTestHelper helper) {
        ItemEntity hot = spawnItem(helper, new Vec3(4.5, 1, 4.5), WASTES.get(1).hot());
        ItemEntity cool = spawnItem(helper, new Vec3(8.5, 1, 8.5), WASTES.get(3).cool());
        // The control must be a plain item: nuclear_waste is a NuclearWasteItem now (invulnerable, never despawns), billet_nuclear_waste is not.
        ItemEntity control = spawnItem(helper, new Vec3(12.5, 1, 12.5), new ItemStack(NtmItems.BILLET_NUCLEAR_WASTE.get()));
        long start = helper.getTick();
        guard(() -> {
            for(ItemEntity waste : List.of(hot, cool)) {
                check(waste.getAge() == 0 && waste.hasPickUpDelay(), waste.getItem() + " joined with age " + waste.getAge() + ", pickup delay " + waste.hasPickUpDelay() + ", expected 0/true");
                check(waste.isInvulnerable() && waste.lifespan == Integer.MAX_VALUE, waste.getItem() + " joined with invulnerable " + waste.isInvulnerable() + ", lifespan " + waste.lifespan + ", expected true/" + Integer.MAX_VALUE);
            }
            check(control.getAge() == 0 && !control.hasPickUpDelay(), "the control joined with age " + control.getAge() + ", pickup delay " + control.hasPickUpDelay());
            int normal = control.getItem().getEntityLifespan(helper.getLevel());
            check(!control.isInvulnerable() && control.lifespan == normal && normal < Integer.MAX_VALUE, "the control joined with invulnerable " + control.isInvulnerable() + ", lifespan " + control.lifespan + ", expected false/" + normal);
        }).run();

        helper.startSequence()
                .thenExecuteAfter(5, guard(() -> {
                    for(ItemEntity waste : List.of(hot, cool)) {
                        assertSameEntity(helper, waste, control, "after 5 ticks");
                        check(waste.hasPickUpDelay(), waste.getItem() + " lost its pickup delay after " + (helper.getTick() - start) + " ticks");
                    }
                }))
                .thenExecuteAfter(6, guard(() -> {
                    for(ItemEntity waste : List.of(hot, cool)) {
                        assertSameEntity(helper, waste, control, "after 11 ticks");
                        check(!waste.hasPickUpDelay(), waste.getItem() + " still has a pickup delay after " + (helper.getTick() - start) + " ticks");
                    }
                    check(control.getAge() >= 10, "the control's age is " + control.getAge() + " after " + (helper.getTick() - start) + " ticks");
                }))
                .thenExecuteAfter(100, guard(() -> {
                    for(ItemEntity waste : List.of(hot, cool)) assertSameEntity(helper, waste, control, "after 111 ticks");
                    LOGGER.info("[hbm-wastedrum] item entity ages after {} ticks: hot {}, cool {}, control {}", helper.getTick() - start, hot.getAge(), cool.getAge(), control.getAge());
                    check(control.getAge() >= 110, "the control's age is " + control.getAge() + " after " + (helper.getTick() - start) + " ticks");

                    // The waste shrugs off fire and lava, the plain control item burns up (item health 5).
                    for(ItemEntity waste : List.of(hot, cool)) {
                        waste.hurt(helper.getLevel().damageSources().lava(), 100F);
                        waste.hurt(helper.getLevel().damageSources().inFire(), 100F);
                    }
                    control.hurt(helper.getLevel().damageSources().lava(), 100F);
                    for(ItemEntity waste : List.of(hot, cool)) assertSameEntity(helper, waste, control, "after lava and fire damage");
                    check(control.isRemoved(), "the control survived lava damage of 100");
                }))
                .thenSucceed();
    }

    private static ItemEntity spawnItem(GameTestHelper helper, Vec3 relative, ItemStack stack) {
        Vec3 pos = helper.absoluteVec(relative);
        ItemEntity entity = new ItemEntity(helper.getLevel(), pos.x, pos.y, pos.z, stack);
        entity.setDeltaMovement(Vec3.ZERO);
        check(helper.getLevel().addFreshEntity(entity), "could not add " + stack);
        return entity;
    }

    /** The waste ages like the control (spawned in the same tick) but is invulnerable and never reaches a despawn age. */
    private static void assertSameEntity(GameTestHelper helper, ItemEntity entity, ItemEntity control, String label) {
        check(entity.isAlive() && helper.getLevel().getEntity(entity.getUUID()) == entity, entity.getItem() + " was replaced or removed " + label);
        check(entity.getAge() == control.getAge(), entity.getItem() + " has age " + entity.getAge() + " " + label + ", the control has " + control.getAge());
        check(entity.isInvulnerable() && entity.lifespan == Integer.MAX_VALUE, entity.getItem() + " has invulnerable " + entity.isInvulnerable() + ", lifespan " + entity.lifespan + " " + label);
    }

    // Placement and breaking

    @GameTest(template = TEMPLATE, timeoutTicks = 100)
    public static void drum_place_break(GameTestHelper helper) {
        guard(() -> {
            BlockPos pos = new BlockPos(8, 1, 8);
            MachineWasteDrumBlockEntity drum = placeDrum(helper, pos);
            BlockState state = helper.getBlockState(pos);
            check(state.requiresCorrectToolForDrops(), "the drum does not require the correct tool for drops");
            check(state.is(BlockTags.MINEABLE_WITH_PICKAXE), "the drum is not in the mineable/pickaxe tag");
            List<ItemStack> contents = List.of(WASTES.get(1).hot(), WASTES.get(3).hot(), WASTES.get(6).hot(), WASTES.get(2).cool(), WASTES.get(4).cool());
            int[] slots = { 0, 1, 2, 5, 7 };
            for(int i = 0; i < slots.length; i++) drum.setItem(slots[i], contents.get(i).copy());

            BlockPos abs = helper.absolutePos(pos);
            check(helper.getLevel().destroyBlock(abs, true), "the drum was not destroyed");
            check(helper.getBlockState(pos).isAir(), "the drum cell is " + helper.getBlockState(pos) + " after breaking");

            List<ItemEntity> drops = helper.getLevel().getEntities(EntityType.ITEM, new AABB(abs).inflate(2), ItemEntity::isAlive);
            List<String> found = new ArrayList<>();
            for(ItemEntity drop : drops) found.add(drop.getItem() + " META " + MetaHelper.getMeta(drop.getItem()) + " age " + drop.getAge());
            check(drops.size() == contents.size() + 1, "breaking dropped " + found + ", expected the drum and " + contents.size() + " waste items");
            check(drops.stream().filter(e -> e.getItem().is(NtmBlocks.MACHINE_WASTE_DRUM.get().asItem()) && e.getItem().getCount() == 1).count() == 1, "no single drum item among " + found);
            for(ItemStack expected : contents) {
                List<ItemEntity> matching = drops.stream().filter(e -> ItemStack.matches(e.getItem(), expected)).toList();
                check(matching.size() == 1, "found " + matching.size() + " drops of " + expected + " META " + MetaHelper.getMeta(expected) + " among " + found);
                if(DepletedFuelItem.isHot(expected)) {
                    ItemEntity drop = matching.get(0);
                    check(drop.isInvulnerable() && drop.lifespan == Integer.MAX_VALUE, "the hot drop " + expected + " has invulnerable " + drop.isInvulnerable() + ", lifespan " + drop.lifespan + ", expected true/" + Integer.MAX_VALUE);
                }
            }
            LOGGER.info("[hbm-wastedrum] drum drops: {}", found);
        }).run();
        helper.succeed();
    }

    // Slot, automation and menu rules

    @GameTest(template = TEMPLATE, timeoutTicks = 300)
    public static void drum_slot_rules(GameTestHelper helper) {
        Waste uranium = WASTES.get(1);
        Waste thorium = WASTES.get(2);
        MachineWasteDrumBlockEntity rules = placeDrum(helper, new BlockPos(8, 2, 8));
        guard(() -> {
            check(rules.getMaxStackSize() == 1, "the drum's stack limit is " + rules.getMaxStackSize());
            check(rules.canPlaceItem(0, uranium.hot()), "the drum rejects hot waste");
            check(!rules.canPlaceItem(0, uranium.cool()), "the drum accepts cool waste");
            check(!rules.canPlaceItem(0, new ItemStack(NtmItems.ROD_ZIRNOX_URANIUM_FUEL_DEPLETED.get())), "the drum accepts a depleted rod");
            check(!rules.canPlaceItem(0, new ItemStack(NtmItems.NUCLEAR_WASTE.get())), "the drum accepts nuclear_waste");
            rules.setItem(0, uranium.hot());
            rules.setItem(1, uranium.cool());
            for(Direction dir : Direction.values()) {
                check(Arrays.equals(rules.getSlotsForFace(dir), ALL_SLOTS), "slots for " + dir + " are " + Arrays.toString(rules.getSlotsForFace(dir)));
                check(rules.canPlaceItemThroughFace(2, uranium.hot(), dir) && !rules.canPlaceItemThroughFace(2, uranium.cool(), dir), "automation insertion rules from " + dir);
                check(!rules.canTakeItemThroughFace(0, uranium.hot(), dir), "automation may take hot waste from " + dir);
                check(rules.canTakeItemThroughFace(1, uranium.cool(), dir), "automation may not take cool waste from " + dir);
            }
            rules.setItem(0, ItemStack.EMPTY);
            rules.setItem(1, ItemStack.EMPTY);

            // Menu slots 0-11 are the drum, 12-38 the main inventory (inventory 9-35), 39-47 the hotbar. A shift-click goes through
            // clicked(QUICK_MOVE), which repeats quickMoveStack; a single quickMoveStack call fills only one empty slot.
            Player player = helper.makeMockPlayer(GameType.SURVIVAL);
            MachineWasteDrumMenu menu = new MachineWasteDrumMenu(0, player.getInventory(), rules);
            check(menu.slots.size() == 48, "the menu has " + menu.slots.size() + " slots, expected 48");
            player.getInventory().setItem(9, uranium.hot().copyWithCount(5));
            player.getInventory().setItem(10, thorium.cool().copyWithCount(3));
            menu.clicked(12, 0, ClickType.QUICK_MOVE, player);
            for(int slot = 0; slot < 12; slot++) {
                ItemStack stack = rules.getItem(slot);
                boolean ok = slot < 5 ? ItemStack.matches(stack, uranium.hot()) : stack.isEmpty();
                check(ok, "after shift-clicking 5 hot waste drum slot " + slot + " holds " + stack);
            }
            check(player.getInventory().getItem(9).isEmpty(), "the player kept " + player.getInventory().getItem(9));
            menu.clicked(13, 0, ClickType.QUICK_MOVE, player);
            check(ItemStack.matches(player.getInventory().getItem(10), thorium.cool().copyWithCount(3)), "cool waste moved: the player holds " + player.getInventory().getItem(10));
            for(int slot = 5; slot < 12; slot++) check(rules.getItem(slot).isEmpty(), "cool waste entered drum slot " + slot + ": " + rules.getItem(slot));
            menu.clicked(0, 0, ClickType.QUICK_MOVE, player);
            check(rules.getItem(0).isEmpty(), "hot waste stayed in drum slot 0 after shift-clicking it out");
            int taken = 0;
            for(int i = 0; i < player.getInventory().getContainerSize(); i++) {
                ItemStack stack = player.getInventory().getItem(i);
                if(ItemStack.isSameItemSameComponents(stack, uranium.hot())) taken += stack.getCount();
            }
            check(taken == 1, "the player holds " + taken + " hot waste after taking one from the drum");
        }).run();

        // A hopper above inserts, a hopper below extracts; neither drum has water, so nothing cools.
        BlockPos fillPos = new BlockPos(3, 2, 3);
        MachineWasteDrumBlockEntity fill = placeDrum(helper, fillPos);
        HopperBlockEntity feeder = placeHopper(helper, fillPos.above());
        feeder.setItem(0, uranium.hot().copyWithCount(14));
        BlockPos drainPos = new BlockPos(12, 2, 12);
        MachineWasteDrumBlockEntity drain = placeDrum(helper, drainPos);
        HopperBlockEntity drainer = placeHopper(helper, drainPos.below());
        for(int slot = 0; slot < 12; slot++) drain.setItem(slot, slot % 2 == 0 ? uranium.hot() : thorium.cool());

        helper.startSequence()
                .thenExecuteAfter(150, guard(() -> {
                    for(int slot = 0; slot < 12; slot++) {
                        ItemStack stack = drain.getItem(slot);
                        boolean ok = slot % 2 == 0 ? ItemStack.matches(stack, uranium.hot()) : stack.isEmpty();
                        check(ok, "the drained drum's slot " + slot + " holds " + stack);
                    }
                    int cool = 0;
                    int total = 0;
                    for(int i = 0; i < drainer.getContainerSize(); i++) {
                        ItemStack stack = drainer.getItem(i);
                        total += stack.getCount();
                        if(ItemStack.isSameItemSameComponents(stack, thorium.cool())) cool += stack.getCount();
                    }
                    check(cool == 6 && total == 6, "the hopper below holds " + total + " items, " + cool + " of them cool waste, expected exactly 6 cool");
                }))
                .thenExecute(guard(() -> {
                    List<String> slots = new ArrayList<>();
                    for(int slot = 0; slot < 12; slot++) slots.add(fill.getItem(slot).toString());
                    LOGGER.info("[hbm-wastedrum] hopper-filled drum slots: {}, hopper keeps {}", slots, feeder.getItem(0));
                    for(int slot = 0; slot < 12; slot++) {
                        check(ItemStack.matches(fill.getItem(slot), uranium.hot()), "the hopper-filled drum's slot " + slot + " holds " + fill.getItem(slot) + ", expected one hot waste; all slots " + slots);
                    }
                    int left = 0;
                    for(int i = 0; i < feeder.getContainerSize(); i++) left += feeder.getItem(i).getCount();
                    check(left == 2 && ItemStack.isSameItemSameComponents(feeder.getItem(0), uranium.hot()), "the hopper above keeps " + left + " items (" + feeder.getItem(0) + "), expected 2 hot waste");
                }))
                .thenSucceed();
    }

    private static HopperBlockEntity placeHopper(GameTestHelper helper, BlockPos pos) {
        helper.setBlock(pos, Blocks.HOPPER.defaultBlockState().setValue(HopperBlock.FACING, Direction.DOWN));
        return SmokeTestSupport.blockEntity(helper, pos, HopperBlockEntity.class);
    }

    // Water counting

    @GameTest(template = TEMPLATE, timeoutTicks = 100)
    public static void drum_water_count(GameTestHelper helper) {
        guard(() -> {
            MachineWasteDrumBlockEntity drum = placeDrum(helper, CENTER);
            check(drum.countWater() == 0, "the drum counts " + drum.countWater() + " water in air");

            BlockState water = Blocks.WATER.defaultBlockState();
            helper.setBlock(CENTER.east(), water);
            check(drum.countWater() == 1, "the drum counts " + drum.countWater() + " water with one source");
            for(Direction dir : Direction.values()) helper.setBlock(CENTER.relative(dir), water);
            check(drum.countWater() == 6, "the drum counts " + drum.countWater() + " water with six sources");
            clearFaces(helper);

            helper.setBlock(CENTER.north(), water.setValue(LiquidBlock.LEVEL, 3));
            check(helper.getLevel().getFluidState(helper.absolutePos(CENTER.north())).getType() == Fluids.FLOWING_WATER, "the LEVEL 3 water block is not flowing water");
            check(drum.countWater() == 1, "the drum counts " + drum.countWater() + " water with one flowing water block");
            clearFaces(helper);

            helper.setBlock(CENTER.south(), Blocks.OAK_SLAB.defaultBlockState().setValue(SlabBlock.WATERLOGGED, true));
            check(drum.countWater() == 1, "the drum counts " + drum.countWater() + " water with a waterlogged slab");
            clearFaces(helper);

            helper.setBlock(CENTER.west(), Blocks.LAVA.defaultBlockState());
            check(helper.getBlockState(CENTER.west()).is(Blocks.LAVA), "the lava turned into " + helper.getBlockState(CENTER.west()));
            check(drum.countWater() == 0, "the drum counts " + drum.countWater() + " water next to lava");
            clearFaces(helper);
        }).run();
        helper.succeed();
    }

    private static void clearFaces(GameTestHelper helper) {
        for(Direction dir : Direction.values()) helper.setBlock(CENTER.relative(dir), Blocks.AIR);
    }

    // Cooling rolls

    @GameTest(template = TEMPLATE, timeoutTicks = 400)
    public static void drum_decay_forced(GameTestHelper helper) {
        MachineWasteDrumBlockEntity drum = placeShelledDrum(helper, CENTER, 1);
        ScriptedRandom random = new ScriptedRandom(bound -> 0);
        drum.setDecayRandom(random);
        // Hot waste in the even slots 0-6, cool waste in 8 and 10, the odd slots stay empty.
        ItemStack[] initial = new ItemStack[12];
        Arrays.fill(initial, ItemStack.EMPTY);
        initial[0] = WASTES.get(0).hot();
        initial[2] = WASTES.get(3).hot();
        initial[4] = WASTES.get(7).hot();
        initial[6] = WASTES.get(8).hot();
        initial[8] = WASTES.get(2).cool();
        initial[10] = WASTES.get(4).cool();
        for(int slot = 0; slot < 12; slot++) drum.setItem(slot, initial[slot].copy());
        LevelChunk chunk = helper.getLevel().getChunkAt(drum.getBlockPos());
        chunk.setUnsaved(false);

        helper.startSequence()
                .thenExecuteAfter(1, guard(() -> {
                    check(drum.countWater() == 1, "the drum counts " + drum.countWater() + " water, expected 1");
                    assertBounds(random, 6, 72000, "one tick with one water");
                    for(int slot = 0; slot < 12; slot++) {
                        ItemStack expected = initial[slot].isEmpty() ? ItemStack.EMPTY : new ItemStack(initial[slot].getItem());
                        check(ItemStack.matches(drum.getItem(slot), expected), "after the forced roll slot " + slot + " holds " + drum.getItem(slot) + " META " + MetaHelper.getMeta(drum.getItem(slot)) + ", expected " + expected);
                    }
                    check(chunk.isUnsaved(), "the drum's chunk is not marked unsaved after cooling waste");

                    for(Direction dir : Direction.values()) helper.setBlock(CENTER.relative(dir), Blocks.WATER);
                    check(drum.countWater() == 6, "the drum counts " + drum.countWater() + " water, expected 6");
                    drum.setItem(1, WASTES.get(5).hot());
                    random.bounds.clear();
                }))
                .thenExecuteAfter(1, guard(() -> {
                    assertBounds(random, 7, 12000, "one tick with six water");
                    check(ItemStack.matches(drum.getItem(1), WASTES.get(5).cool()), "slot 1 holds " + drum.getItem(1) + " after the forced roll with six water");

                    random.answer = bound -> bound - 1;
                    for(int slot : new int[] { 0, 2, 4, 6 }) drum.setItem(slot, initial[slot].copy());
                    random.bounds.clear();
                }))
                .thenExecuteAfter(200, guard(() -> {
                    assertBounds(random, 200 * 7, 12000, "200 ticks answering bound - 1");
                    for(int slot = 0; slot < 12; slot++) {
                        ItemStack expected = switch(slot) {
                            case 0, 2, 4, 6 -> initial[slot];
                            case 1 -> WASTES.get(5).cool();
                            case 8, 10 -> initial[slot];
                            default -> ItemStack.EMPTY;
                        };
                        check(ItemStack.matches(drum.getItem(slot), expected), "after 200 losing rolls slot " + slot + " holds " + drum.getItem(slot) + ", expected " + expected);
                    }
                }))
                .thenSucceed();
    }

    private static void assertBounds(ScriptedRandom random, int calls, int bound, String label) {
        check(random.bounds.size() == calls, label + ": " + random.bounds.size() + " rolls, expected " + calls);
        for(int value : random.bounds) check(value == bound, label + ": a roll used bound " + value + ", expected " + bound);
    }

    @GameTest(template = TEMPLATE, timeoutTicks = 3300)
    public static void drum_decay_seeded(GameTestHelper helper) {
        int ticks = 3000;
        SeededRun six = new SeededRun(helper, new BlockPos(4, 3, 4), 6, 2026101506L);
        SeededRun one = new SeededRun(helper, new BlockPos(11, 3, 11), 1, 2026101501L);

        helper.startSequence()
                .thenExecuteFor(ticks, guard(() -> {
                    six.observe();
                    one.observe();
                }))
                .thenExecute(guard(() -> {
                    six.observe();
                    one.observe();
                    six.compare();
                    one.compare();
                }))
                .thenSucceed();
    }

    /** A drum with 12 hot waste and a seeded cooling random; records the drum update in which each slot turned cool. */
    private static final class SeededRun {
        final GameTestHelper helper;
        final MachineWasteDrumBlockEntity drum;
        final int water;
        final long seed;
        final long start;
        final long[] decayed = new long[12];
        long lastObserved = -1;

        SeededRun(GameTestHelper helper, BlockPos pos, int water, long seed) {
            this.helper = helper;
            this.water = water;
            this.seed = seed;
            this.drum = placeShelledDrum(helper, pos, water);
            for(int slot = 0; slot < 12; slot++) drum.setItem(slot, WASTES.get(slot % WASTES.size()).hot());
            drum.setDecayRandom(RandomSource.create(seed));
            this.start = helper.getTick();
            Arrays.fill(decayed, -1);
        }

        void observe() {
            long updates = helper.getTick() - start;
            check(lastObserved < 0 ? updates <= 1 : updates == lastObserved + 1, "seed " + seed + ": observed after " + updates + " updates, previous " + lastObserved);
            lastObserved = updates;
            check(drum.countWater() == water, "seed " + seed + ": the drum counts " + drum.countWater() + " water, expected " + water);
            for(int slot = 0; slot < 12; slot++) {
                Waste waste = WASTES.get(slot % WASTES.size());
                ItemStack stack = drum.getItem(slot);
                if(ItemStack.matches(stack, waste.cool())) {
                    if(decayed[slot] < 0) decayed[slot] = updates;
                } else {
                    check(decayed[slot] < 0 && ItemStack.matches(stack, waste.hot()), "seed " + seed + ": slot " + slot + " holds " + stack + " after " + updates + " updates");
                }
            }
        }

        void compare() {
            int bound = MachineWasteDrumBlockEntity.DECAY_TICKS / water;
            long[] expected = new long[12];
            Arrays.fill(expected, -1);
            RandomSource replay = RandomSource.create(seed);
            for(long update = 1; update <= lastObserved; update++) {
                // Every filled slot rolls each tick, a slot that already cooled down included.
                for(int slot = 0; slot < 12; slot++) {
                    if(replay.nextInt(bound) == 0 && expected[slot] < 0) expected[slot] = update;
                }
            }
            LOGGER.info("[hbm-wastedrum] seeded decay, seed {}, {} water, bound {}, {} updates: drum {} replay {}", seed, water, bound, lastObserved, Arrays.toString(decayed), Arrays.toString(expected));
            check(Arrays.equals(decayed, expected), "seed " + seed + " with " + water + " water: the drum cooled slots at " + Arrays.toString(decayed) + ", the replay at " + Arrays.toString(expected));
        }
    }

    @GameTest(template = TEMPLATE, timeoutTicks = 20100)
    public static void drum_no_water_20000(GameTestHelper helper) {
        MachineWasteDrumBlockEntity drum = placeDrum(helper, new BlockPos(8, 2, 8));
        ScriptedRandom random = new ScriptedRandom(bound -> 0);
        drum.setDecayRandom(random);
        for(int slot = 0; slot < 12; slot++) drum.setItem(slot, WASTES.get(slot % WASTES.size()).hot());
        guard(() -> check(drum.countWater() == 0, "the drum counts " + drum.countWater() + " water in air")).run();
        long start = helper.getTick();

        helper.startSequence()
                .thenExecuteAfter(20000, guard(() -> {
                    LOGGER.info("[hbm-wastedrum] no water: {} ticks, {} rolls", helper.getTick() - start, random.bounds.size());
                    check(random.bounds.isEmpty(), "the dry drum rolled " + random.bounds.size() + " times");
                    for(int slot = 0; slot < 12; slot++) {
                        check(ItemStack.matches(drum.getItem(slot), WASTES.get(slot % WASTES.size()).hot()), "the dry drum's slot " + slot + " holds " + drum.getItem(slot));
                    }
                }))
                .thenSucceed();
    }

    // Persistence and sync

    @GameTest(template = TEMPLATE, timeoutTicks = 100)
    public static void drum_persistence_sync(GameTestHelper helper) {
        guard(() -> {
            MachineWasteDrumBlockEntity drum = placeDrum(helper, new BlockPos(8, 1, 8));
            drum.setItem(0, WASTES.get(1).hot());
            drum.setItem(3, WASTES.get(3).cool());
            drum.setItem(11, WASTES.get(8).hot());
            HolderLookup.Provider registries = helper.getLevel().registryAccess();

            CompoundTag tag = drum.saveWithFullMetadata(registries);
            check(tag.contains("Items", Tag.TAG_LIST), "the saved drum has no Items list: " + tag);
            ListTag items = tag.getList("Items", Tag.TAG_COMPOUND);
            List<Integer> saved = new ArrayList<>();
            for(int i = 0; i < items.size(); i++) saved.add((int) items.getCompound(i).getByte("Slot"));
            check(saved.equals(List.of(0, 3, 11)), "the saved drum lists slots " + saved + ", expected [0, 3, 11]");

            MachineWasteDrumBlockEntity loaded = new MachineWasteDrumBlockEntity(drum.getBlockPos(), drum.getBlockState());
            loaded.loadWithComponents(tag, registries);
            for(int slot = 0; slot < 12; slot++) {
                check(ItemStack.matches(loaded.getItem(slot), drum.getItem(slot)), "loaded slot " + slot + " holds " + loaded.getItem(slot) + ", expected " + drum.getItem(slot));
            }
            check(MetaHelper.getMeta(loaded.getItem(0)) == DepletedFuelItem.HOT && MetaHelper.getMeta(loaded.getItem(11)) == DepletedFuelItem.HOT && MetaHelper.getMeta(loaded.getItem(3)) == DepletedFuelItem.COOL,
                    "loaded META values are " + MetaHelper.getMeta(loaded.getItem(0)) + "/" + MetaHelper.getMeta(loaded.getItem(3)) + "/" + MetaHelper.getMeta(loaded.getItem(11)));

            String json;
            try {
                json = FuelPoolRecipes.writeSnapshot();
            } catch(IOException e) {
                throw new IllegalStateException(e);
            }
            List<FuelPoolRecipe> table = FuelPoolRecipes.getJeiRecipes();
            assertSameRows(FuelPoolRecipes.readSnapshot(json), table, "snapshot round trip");

            String row = "{\"input\":[\"hbmsntm:waste_uranium\",1,1],\"output\":[\"hbmsntm:waste_uranium\",1,0]}";
            check(FuelPoolRecipes.readSnapshot("{\"recipes\":[" + row + "]}").size() == 1, "a valid single-row snapshot was not read");
            assertRejected("{\"recipes\":[{\"input\":[\"hbmsntm:no_such_item\",1,1],\"output\":[\"hbmsntm:waste_uranium\",1,0]}]}", "an unknown item");
            assertRejected("{\"recipes\":[{\"input\":[\"hbmsntm:waste_uranium\",2,1],\"output\":[\"hbmsntm:waste_uranium\",1,0]}]}", "input count 2");
            assertRejected("{\"recipes\":[" + row + "," + row + "]}", "a duplicate input");

            FuelPoolRecipesPacket packet = new FuelPoolRecipesPacket(json);
            RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf(Unpooled.buffer(), helper.getLevel().registryAccess(), ConnectionType.OTHER);
            try {
                FuelPoolRecipesPacket.STREAM_CODEC.encode(buf, packet);
                FuelPoolRecipesPacket decoded = FuelPoolRecipesPacket.STREAM_CODEC.decode(buf);
                check(buf.readableBytes() == 0, "the packet left " + buf.readableBytes() + " bytes unread");
                check(decoded.json().equals(json), "the decoded snapshot differs from the sent one");
                assertSameRows(FuelPoolRecipes.readSnapshot(decoded.json()), table, "packet round trip");
            } finally {
                buf.release();
            }
            LOGGER.info("[hbm-wastedrum] fuel pool snapshot: {} rows, {} characters", table.size(), json.length());
        }).run();
        helper.succeed();
    }

    private static void assertRejected(String json, String label) {
        try {
            List<FuelPoolRecipe> rows = FuelPoolRecipes.readSnapshot(json);
            check(false, "a snapshot with " + label + " was read as " + rows.size() + " rows");
        } catch(IllegalArgumentException e) {
            LOGGER.info("[hbm-wastedrum] snapshot with {} rejected: {}", label, e.getMessage());
        }
    }

    // Chunk radiation

    @GameTest(template = TEMPLATE, timeoutTicks = 300)
    public static void drum_no_chunk_radiation(GameTestHelper helper) {
        MachineWasteDrumBlockEntity drum = placeShelledDrum(helper, CENTER, 6);
        for(int slot = 0; slot < 12; slot++) drum.setItem(slot, WASTES.get(slot % WASTES.size()).hot());
        ServerLevel level = helper.getLevel();
        BlockPos abs = drum.getBlockPos();
        float before = ChunkRadiationManager.proxy.getRadiation(level, abs);

        helper.startSequence()
                .thenExecuteAfter(200, guard(() -> {
                    float after = ChunkRadiationManager.proxy.getRadiation(level, abs);
                    LOGGER.info("[hbm-wastedrum] chunk radiation at the drum: {} before, {} after 200 ticks", before, after);
                    check(after == before, "chunk radiation at the drum changed from " + before + " to " + after);
                }))
                .thenSucceed();
    }

    // Shared helpers

    private static MachineWasteDrumBlockEntity placeDrum(GameTestHelper helper, BlockPos pos) {
        helper.setBlock(pos, NtmBlocks.MACHINE_WASTE_DRUM.get());
        return SmokeTestSupport.blockEntity(helper, pos, MachineWasteDrumBlockEntity.class);
    }

    /**
     * Places a drum in the middle of a 5x5x5 stone shell. The first {@code water} faces in the order EAST, DOWN, UP, NORTH,
     * SOUTH, WEST get a water source and every other cell is stone, so no water can flow anywhere.
     */
    private static MachineWasteDrumBlockEntity placeShelledDrum(GameTestHelper helper, BlockPos pos, int water) {
        for(int x = -2; x <= 2; x++) for(int y = -2; y <= 2; y++) for(int z = -2; z <= 2; z++) {
            if(x != 0 || y != 0 || z != 0) helper.setBlock(pos.offset(x, y, z), Blocks.STONE);
        }
        MachineWasteDrumBlockEntity drum = placeDrum(helper, pos);
        List<Direction> order = new ArrayList<>(List.of(Direction.EAST));
        for(Direction dir : Direction.values()) if(dir != Direction.EAST) order.add(dir);
        for(int i = 0; i < water; i++) helper.setBlock(pos.relative(order.get(i)), Blocks.WATER);
        return drum;
    }
}
