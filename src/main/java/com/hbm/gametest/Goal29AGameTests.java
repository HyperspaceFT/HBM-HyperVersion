package com.hbm.gametest;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.hbm.blockentity.machine.MachineBlastFurnaceBlockEntity;
import com.hbm.blockentity.machine.heater.HeaterFireboxBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.machine.NTMAnvilBlock;
import com.hbm.handler.jei.subtypes.BatterySubtypeInterpreter;
import com.hbm.handler.jei.subtypes.BlueprintsSubtypeInterpreter;
import com.hbm.handler.jei.subtypes.MetaSubtypeInterpreter;
import com.hbm.inventory.MetaHelper;
import com.hbm.items.NtmItems;
import com.hbm.items.food.PillItem;
import com.hbm.items.machine.BatteryPackItem;
import com.hbm.items.machine.BlueprintsItem;
import com.hbm.main.NuclearTechMod;
import com.hbm.registry.NtmDamageTypes;
import com.mojang.logging.LogUtils;
import mezz.jei.api.ingredients.subtypes.UidContext;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.Registry;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.Registries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestAssertException;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.tags.DamageTypeTags;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.damagesource.DamageType;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.animal.IronGolem;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.crafting.CraftingInput;
import net.minecraft.world.item.crafting.CraftingRecipe;
import net.minecraft.world.item.crafting.Ingredient;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.item.crafting.ShapedRecipe;
import net.minecraft.world.item.crafting.ShapelessRecipe;
import net.minecraft.world.level.GameType;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import org.slf4j.Logger;

import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.TreeMap;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal29A: the global fuel table, the blast furnace fuel rule, the flux and plan_c recipes with the euthanized damage
 * types, the shipped models and blockstates, and the two JEI subtype interpreters. Same template and conventions as
 * {@link ResourceCompletionGameTests}; every test has its own batch.
 * <p>
 * Expected values come from the ORIGINAL at cd0cff450, cited beside each group of checks (FuelHandler.java:21-61;
 * TileEntityMachineBlastFurnace.java:53-54,216-219; OreDictManager.java:335; PowderRecipes.java:67-73; ConsumableRecipes.java:119;
 * ModDamageSource.java:12-13; ItemPill.java:48-51), not from the NEO implementation. The blast furnace expectations are derived from
 * ModuleBurnTime's category rule (path contains rocket, solid_fuel, coke, lignite, coal, log, wood or plank, then item tags; uncategorized gives
 * the default 0 of TileEntityMachineBlastFurnace.java:218) and the item's own burn time, the heat modifier being 1.0 except WOOD = 0
 * (TileEntityMachineBlastFurnace.java:53-54).
 * <p>
 * Real classes and state: ItemStack.getBurnTime as the furnace and every ModuleBurnTime machine ask it, with the real furnace_fuels data map;
 * the real MachineBlastFurnaceBlockEntity placed through the real multiblock path (SmokeTestSupport.place); the recipes through the server's own
 * RecipeManager with real CraftingInputs; the damage type registry and the bypasses_armor tag as the server loaded them; iron golems standing in
 * for the pill's eater, each wearing real diamond armor; the two JEI interpreters called directly. Substitutes: a mob instead of a mock player
 * for the armor checks, since mock players never tick and so never apply armor attributes; resources are read from the mod's classpath.
 * Recorded, not changed in 29A: the NEO fuel values of coke_lignite, coke_petroleum and the three briquettes differ from the original
 * (FuelHandler.java:38,49-51), and ModuleBurnTime puts charcoal, powder_ash_coal, crystal_coal and coal_infernal into COAL where the original has no
 * such ore name for them (ModuleBurnTime.java:116-124, OreDictManager.java:335,892), in the blast furnace and in the firebox; the tests assert NEO's
 * current values for these rows and say so.
 * Not evidence: a real client (models and textures actually rendering, JEI's own runtime and its use of the interpreters, tooltips), a dedicated
 * server with real players, saved worlds, and 1.7.10 itself.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class Goal29AGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-29a]";
    private static final BlockPos CENTER = new BlockPos(8, 1, 8);

    private static ResourceLocation id(String path) {
        return ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path);
    }

    private static Runnable passed(String test) {
        return () -> LOGGER.info("{} {} passed", TAG, test);
    }

    // ---------------------------------------------------------------- 1. global fuel table

    private record Fuel(String name, ItemStack stack, int burnTime, String cite) { }

    /** FuelHandler.java:19 single = 200; the rows are the ones the original lists and NEO ports. */
    private static List<Fuel> fuelTable() {
        return List.of(
                new Fuel("solid_fuel", new ItemStack(NtmItems.SOLID_FUEL.get()), 3200, "FuelHandler.java:21 single * 16"),
                new Fuel("rocket_fuel", new ItemStack(NtmItems.ROCKET_FUEL.get()), 6400, "FuelHandler.java:27 single * 32"),
                new Fuel("biomass", new ItemStack(NtmItems.BIOMASS.get()), 400, "FuelHandler.java:29 single * 2"),
                new Fuel("powder_coal", new ItemStack(NtmItems.POWDER_COAL.get()), 1600, "FuelHandler.java:31 single * 8"),
                new Fuel("dust", new ItemStack(NtmItems.DUST.get()), 25, "FuelHandler.java:33 single / 8"),
                new Fuel("block_scrap", new ItemStack(NtmBlocks.BLOCK_SCRAP.get()), 400, "FuelHandler.java:34 single * 2, through the furnace_fuels data map"),
                new Fuel("powder_fire", new ItemStack(NtmItems.POWDER_FIRE.get()), 6400, "FuelHandler.java:35"),
                new Fuel("lignite", new ItemStack(NtmItems.LIGNITE.get()), 1200, "FuelHandler.java:36"),
                new Fuel("powder_lignite", new ItemStack(NtmItems.POWDER_LIGNITE.get()), 1200, "FuelHandler.java:37"),
                new Fuel("coke_coal", new ItemStack(NtmItems.COKE_COAL.get()), 3200, "FuelHandler.java:38 single * 16"),
                new Fuel("coal_infernal", new ItemStack(NtmItems.COAL_INFERNAL.get()), 4800, "FuelHandler.java:41"),
                new Fuel("crystal_coal", new ItemStack(NtmItems.CRYSTAL_COAL.get()), 6400, "FuelHandler.java:43"),
                new Fuel("powder_sawdust", new ItemStack(NtmItems.POWDER_SAWDUST.get()), 100, "FuelHandler.java:44 single / 2"),
                new Fuel("powder_ash_wood", new ItemStack(NtmItems.POWDER_ASH_WOOD.get()), 100, "FuelHandler.java:56-59 meta 0 (WOOD), single / 2"),
                new Fuel("powder_ash_coal", new ItemStack(NtmItems.POWDER_ASH_COAL.get()), 200, "FuelHandler.java:60 meta 1 (COAL), single"),
                new Fuel("powder_ash_misc", new ItemStack(NtmItems.POWDER_ASH_MISC.get()), 100, "FuelHandler.java:61 meta 2 (MISC), single / 2"));
    }

    // FuelHandler.java:21-61 (single = 200), as the vanilla furnace asks (RecipeType.SMELTING) and as ModuleBurnTime asks (null)
    @GameTest(template = TEMPLATE, batch = "hbm29a_fuel_table", timeoutTicks = 100)
    public static void global_fuel_table(GameTestHelper helper) {
        guard(() -> {
            List<Fuel> table = fuelTable();
            check(table.size() == 16, "the expected fuel table has " + table.size() + " rows, expected 16");
            for(Fuel fuel : table) {
                int any = fuel.stack().getBurnTime(null);
                int smelting = fuel.stack().getBurnTime(RecipeType.SMELTING);
                check(any == fuel.burnTime(), fuel.name() + " burns " + any + " ticks (null recipe type), expected " + fuel.burnTime() + " (" + fuel.cite() + ")");
                check(smelting == fuel.burnTime(), fuel.name() + " burns " + smelting + " ticks (smelting), expected " + fuel.burnTime() + " (" + fuel.cite() + ")");
            }

            // block_scrap is a block item: it has no Item.getBurnTime override, so the value comes from data/neoforge/data_maps/item/furnace_fuels.json
            Item scrap = NtmBlocks.BLOCK_SCRAP.get().asItem();
            check(!(scrap instanceof com.hbm.items.FuelItem), "block_scrap is a FuelItem, expected the furnace_fuels data map to carry it");

            // The other FuelHandler rows are not ported (no NEO item): solid_fuel_presto*, solid_fuel_bf*, biomass_compressed, scrap, block_coke, book_guide,
            // coal_eternal. Recorded here so the log shows which rows were left out.
            LOGGER.info("{} global_fuel_table: FuelHandler.java:22-26,30,32,39,40,42,47 have no NEO item and are not asserted", TAG);

            // Recorded-only differences (not changed in 29A): the original has one coke item at 3200 (FuelHandler.java:38) and briquettes at
            // 2000 / 1600 / 400 for metas 0-2 (:49-51).
            check(new ItemStack(NtmItems.COKE_LIGNITE.get()).getBurnTime(null) == 2400, "coke_lignite burns " + new ItemStack(NtmItems.COKE_LIGNITE.get()).getBurnTime(null) + ", NEO's recorded value is 2400");
            check(new ItemStack(NtmItems.COKE_PETROLEUM.get()).getBurnTime(null) == 6400, "coke_petroleum burns " + new ItemStack(NtmItems.COKE_PETROLEUM.get()).getBurnTime(null) + ", NEO's recorded value is 6400");
            check(new ItemStack(NtmItems.BRIQUETTE_COAL.get()).getBurnTime(null) == 2400, "briquette_coal burns " + new ItemStack(NtmItems.BRIQUETTE_COAL.get()).getBurnTime(null) + ", NEO's recorded value is 2400");
            check(new ItemStack(NtmItems.BRIQUETTE_LIGNITE.get()).getBurnTime(null) == 1800, "briquette_lignite burns " + new ItemStack(NtmItems.BRIQUETTE_LIGNITE.get()).getBurnTime(null) + ", NEO's recorded value is 1800");
            check(new ItemStack(NtmItems.BRIQUETTE_WOOD.get()).getBurnTime(null) == 1600, "briquette_wood burns " + new ItemStack(NtmItems.BRIQUETTE_WOOD.get()).getBurnTime(null) + ", NEO's recorded value is 1600");
            LOGGER.info("{} global_fuel_table: recorded, not changed in 29A: coke_lignite 2400 and coke_petroleum 6400 (original coke 3200, FuelHandler.java:38); "
                    + "briquette_coal 2400, briquette_lignite 1800, briquette_wood 1600 (original 2000 / 1600 / 400, FuelHandler.java:49-51)", TAG);
        }).run();
        passed("global_fuel_table").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 2. blast furnace fuel

    private record Burn(String name, ItemStack stack, int expected, String why) { }

    /**
     * TileEntityMachineBlastFurnace.java:216-219: container items give 0, otherwise getBurnHeat(getBurnTime(stack, 0D), stack, 0D) with the heat
     * modifier of WOOD set to 0 (:53-54). Each row's {@code why} is the ModuleBurnTime derivation from the path and the item's burn time.
     */
    private static List<Burn> blastFurnaceTable() {
        return List.of(
                new Burn("minecraft:coal", new ItemStack(Items.COAL), 1600, "path coal -> COAL 1.0 x 1.0, vanilla 1600"),
                new Burn("minecraft:coal_block", new ItemStack(Items.COAL_BLOCK), 16000, "path coal_block -> COAL, vanilla 16000"),
                new Burn("minecraft:blaze_rod", new ItemStack(Items.BLAZE_ROD), 0, "no category (path blaze_rod, tag c:rods/blaze) -> default 0, as the original"),
                new Burn("minecraft:fire_charge", new ItemStack(Items.FIRE_CHARGE), 0, "no category -> default 0, as the original"),
                new Burn("minecraft:lava_bucket", new ItemStack(Items.LAVA_BUCKET), 0, "container item -> 0 (:217)"),
                new Burn("lignite", new ItemStack(NtmItems.LIGNITE.get()), 1200, "path lignite -> LIGNITE, burn 1200"),
                new Burn("powder_coal", new ItemStack(NtmItems.POWDER_COAL.get()), 1600, "path powder_coal -> COAL, burn 1600"),
                new Burn("powder_lignite", new ItemStack(NtmItems.POWDER_LIGNITE.get()), 1200, "path powder_lignite -> LIGNITE, burn 1200"),
                new Burn("oil_tar_coal", new ItemStack(NtmItems.OIL_TAR_COAL.get()), 0, "no burn time -> 0, as the original"),
                new Burn("solid_fuel", new ItemStack(NtmItems.SOLID_FUEL.get()), 3200, "path solid_fuel -> SOLID, burn 3200"),
                new Burn("rocket_fuel", new ItemStack(NtmItems.ROCKET_FUEL.get()), 6400, "path rocket_fuel -> ROCKET, burn 6400"),
                new Burn("coke_coal", new ItemStack(NtmItems.COKE_COAL.get()), 3200, "path coke_coal -> COKE, burn 3200"),
                new Burn("coke_lignite", new ItemStack(NtmItems.COKE_LIGNITE.get()), 2400, "path coke_lignite -> COKE (coke is tested before lignite), burn 2400"),
                new Burn("coke_petroleum", new ItemStack(NtmItems.COKE_PETROLEUM.get()), 6400, "path coke_petroleum -> COKE, burn 6400"),
                new Burn("minecraft:oak_log", new ItemStack(Items.OAK_LOG), 300, "#minecraft:logs -> LOG (heat stays 1.0), vanilla 300"),
                new Burn("minecraft:oak_planks", new ItemStack(Items.OAK_PLANKS), 0, "path plank -> WOOD, heat 0 (:53-54), vanilla 300"),
                new Burn("powder_ash_wood", new ItemStack(NtmItems.POWDER_ASH_WOOD.get()), 0, "path powder_ash_wood contains wood -> WOOD, heat 0, burn 100"),
                // No ModuleBurnTime keyword in the path (biomass, dust, powder_fire, powder_sawdust, block_scrap, powder_ash_misc) and no item tag of the
                // c:, minecraft: or hbmsntm: namespaces that carries one (the generated tags hold only aluminum dust, aluminum ore, copper and steel plates,
                // tools, enchantables and the ntm_* tank tags) -> uncategorized -> default 0 (:218).
                new Burn("biomass", new ItemStack(NtmItems.BIOMASS.get()), 0, "uncategorized (path biomass, no tag) -> default 0, burn 400"),
                new Burn("dust", new ItemStack(NtmItems.DUST.get()), 0, "uncategorized (path dust, no tag) -> default 0, burn 25"),
                new Burn("powder_fire", new ItemStack(NtmItems.POWDER_FIRE.get()), 0, "uncategorized (path powder_fire, no tag) -> default 0, burn 6400"),
                new Burn("powder_sawdust", new ItemStack(NtmItems.POWDER_SAWDUST.get()), 0, "uncategorized (path powder_sawdust has no wood, no tag) -> default 0, burn 100"),
                new Burn("block_scrap", new ItemStack(NtmBlocks.BLOCK_SCRAP.get()), 0, "uncategorized (path block_scrap, no tag) -> default 0, burn 400 from the data map"),
                new Burn("powder_ash_misc", new ItemStack(NtmItems.POWDER_ASH_MISC.get()), 0, "uncategorized (path powder_ash_misc, no tag) -> default 0, burn 100"));
    }

    // TileEntityMachineBlastFurnace.java:53-54,216-219; the NEO static MachineBlastFurnaceBlockEntity.getBurnTime and canPlaceItem(SLOT_FUEL)
    @GameTest(template = TEMPLATE, batch = "hbm29a_blast_furnace_fuel", timeoutTicks = 100)
    public static void blast_furnace_fuel(GameTestHelper helper) {
        guard(() -> {
            List<Burn> table = blastFurnaceTable();
            check(table.size() == 23, "the expected blast furnace table has " + table.size() + " rows, expected 23");
            for(Burn row : table) {
                int burn = MachineBlastFurnaceBlockEntity.getBurnTime(row.stack());
                check(burn == row.expected(), row.name() + " gives " + burn + " blast furnace fuel, expected " + row.expected() + " (TileEntityMachineBlastFurnace.java:216-219; " + row.why() + ")");
            }
            check(MachineBlastFurnaceBlockEntity.getBurnTime(ItemStack.EMPTY) == 0, "an empty stack gives blast furnace fuel");

            // Recorded ModuleBurnTime path-rule difference, not changed in 29A: the path rule puts charcoal, powder_ash_coal, crystal_coal and coal_infernal into
            // COAL, while the original's getMod asks ore names (ModuleBurnTime.java:116-124) and OreDictManager.java:335,892 gives "Coal" only to Items.coal
            // meta 0, powder_coal and powder_coal_tiny, so the original blast furnace gives 0 for all four.
            int charcoal = MachineBlastFurnaceBlockEntity.getBurnTime(new ItemStack(Items.CHARCOAL));
            int ashCoal = MachineBlastFurnaceBlockEntity.getBurnTime(new ItemStack(NtmItems.POWDER_ASH_COAL.get()));
            int crystalCoal = MachineBlastFurnaceBlockEntity.getBurnTime(new ItemStack(NtmItems.CRYSTAL_COAL.get()));
            int infernal = MachineBlastFurnaceBlockEntity.getBurnTime(new ItemStack(NtmItems.COAL_INFERNAL.get()));
            check(charcoal == 1600, "minecraft:charcoal gives " + charcoal + " blast furnace fuel, NEO's recorded value is 1600 (path charcoal -> COAL)");
            check(ashCoal == 200, "powder_ash_coal gives " + ashCoal + " blast furnace fuel, NEO's recorded value is 200 (path contains coal -> COAL)");
            check(crystalCoal == 6400, "crystal_coal gives " + crystalCoal + " blast furnace fuel, NEO's recorded value is 6400 (path crystal_coal -> COAL)");
            check(infernal == 4800, "coal_infernal gives " + infernal + " blast furnace fuel, NEO's recorded value is 4800 (path coal_infernal -> COAL)");
            LOGGER.info("{} blast_furnace_fuel: recorded ModuleBurnTime path-rule difference, not changed in 29A: minecraft:charcoal 1600, powder_ash_coal 200, crystal_coal 6400 and "
                    + "coal_infernal 4800 (COAL by path; original 0, ModuleBurnTime.java:116-124, OreDictManager.java:335,892)", TAG);

            // The firebox shares the rule: HeaterFireboxBlockEntity.burnModule (COAL time x1.25, heat x2) reached through its static module, no placed block. The
            // original firebox uses the same ore-name rule, so for crystal_coal and powder_ash_coal its modifier is the default 1.0 (time 6400 / 200, heat = base).
            int baseHeat = HeaterFireboxBlockEntity.baseHeat;
            ItemStack crystal = new ItemStack(NtmItems.CRYSTAL_COAL.get());
            ItemStack ash = new ItemStack(NtmItems.POWDER_ASH_COAL.get());
            int crystalTime = HeaterFireboxBlockEntity.burnModule.getBurnTime(crystal);
            int ashTime = HeaterFireboxBlockEntity.burnModule.getBurnTime(ash);
            int crystalHeat = HeaterFireboxBlockEntity.burnModule.getBurnHeat(baseHeat, crystal);
            int ashHeat = HeaterFireboxBlockEntity.burnModule.getBurnHeat(baseHeat, ash);
            check(crystalTime == 8000 && ashTime == 250, "firebox burn time is " + crystalTime + " for crystal_coal and " + ashTime + " for powder_ash_coal, NEO's recorded values are 8000 and 250 (COAL x1.25)");
            check(crystalHeat == baseHeat * 2 && ashHeat == baseHeat * 2, "firebox heat is " + crystalHeat + " for crystal_coal and " + ashHeat + " for powder_ash_coal, NEO's recorded value is " + (baseHeat * 2) + " (COAL x2)");
            LOGGER.info("{} blast_furnace_fuel: recorded ModuleBurnTime path-rule difference, not changed in 29A: firebox crystal_coal time {} heat {} and powder_ash_coal time {} heat {} "
                    + "(COAL x1.25 time, x2 heat by path; original modifier 1.0: time 6400 / 200, heat {})", TAG, crystalTime, crystalHeat, ashTime, ashHeat, baseHeat);
        }).run();
        passed("blast_furnace_fuel").run();
        helper.succeed();
    }

    // MachineBlastFurnaceBlockEntity.canPlaceItem(SLOT_FUEL) must agree with getBurnTime > 0 (the fuel slot accepts what burns), on the real placed machine
    @GameTest(template = TEMPLATE, batch = "hbm29a_blast_furnace_slot", timeoutTicks = 100)
    public static void blast_furnace_fuel_slot(GameTestHelper helper) {
        guard(() -> {
            SmokeTestSupport.place(helper, (DummyableBlock) NtmBlocks.MACHINE_BLAST_FURNACE.get(), CENTER, Direction.NORTH);
            MachineBlastFurnaceBlockEntity be = SmokeTestSupport.blockEntity(helper, CENTER, MachineBlastFurnaceBlockEntity.class);
            int slot = MachineBlastFurnaceBlockEntity.SLOT_FUEL;
            check(!be.canPlaceItem(slot, new ItemStack(Items.BLAZE_ROD)), "the fuel slot accepts a blaze rod (blast furnace burn time 0, TileEntityMachineBlastFurnace.java:218)");
            check(be.canPlaceItem(slot, new ItemStack(NtmItems.LIGNITE.get())), "the fuel slot refuses lignite (burn 1200)");
            check(be.canPlaceItem(slot, new ItemStack(Items.COAL)), "the fuel slot refuses coal (burn 1600)");
            check(!be.canPlaceItem(slot, new ItemStack(Items.OAK_PLANKS)), "the fuel slot accepts planks (WOOD heat 0, :53-54)");
            check(!be.canPlaceItem(slot, new ItemStack(Items.LAVA_BUCKET)), "the fuel slot accepts a lava bucket (container item, :217)");
            for(Burn row : blastFurnaceTable()) {
                boolean accepts = be.canPlaceItem(slot, row.stack());
                check(accepts == (row.expected() > 0), row.name() + ": canPlaceItem(fuel) is " + accepts + " with expected burn time " + row.expected());
            }
        }).run();
        passed("blast_furnace_fuel_slot").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 3. flux

    /** One expected flux row: the recipe id, the result count and the non-sand ingredients (every row also takes one sand, KEY_SAND). */
    private record Flux(String path, int count, Item... ingredients) { }

    private static List<Flux> fluxRows() {
        // PowderRecipes.java:67-73, in order; the trailing KEY_SAND of every row is the sands tag and is not listed
        return List.of(
                new Flux("powder_flux_from_charcoal", 1, Items.CHARCOAL),
                new Flux("powder_flux_from_coal", 2, NtmItems.POWDER_COAL.get()),
                new Flux("powder_flux_from_fluorite", 4, NtmItems.FLUORITE.get()),
                new Flux("powder_flux_from_lead_sulfur", 8, NtmItems.POWDER_LEAD.get(), NtmItems.SULFUR.get()),
                new Flux("powder_flux_from_limestone", 12, NtmItems.POWDER_LIMESTONE.get()),
                new Flux("powder_flux_from_calcium", 12, NtmItems.POWDER_CALCIUM.get()),
                new Flux("powder_flux_from_borax", 16, NtmItems.POWDER_BORAX.get()));
    }

    // PowderRecipes.java:67-73: seven shapeless recipes, the named dust(s) plus any sand, 1 / 2 / 4 / 8 / 12 / 12 / 16 powder_flux
    @GameTest(template = TEMPLATE, batch = "hbm29a_flux_recipes", timeoutTicks = 100)
    public static void flux_recipes(GameTestHelper helper) {
        guard(() -> {
            List<Flux> rows = fluxRows();
            check(rows.size() == 7, "the expected flux table has " + rows.size() + " rows, expected 7");
            for(Flux row : rows) {
                RecipeHolder<?> holder = helper.getLevel().getRecipeManager().byKey(id(row.path())).orElse(null);
                check(holder != null, "recipe " + id(row.path()) + " is not loaded (PowderRecipes.java:67-73)");
                check(holder.value() instanceof ShapelessRecipe, row.path() + " is " + holder.value().getClass().getSimpleName() + ", expected a shapeless recipe (addShapelessAuto)");
                ShapelessRecipe recipe = (ShapelessRecipe) holder.value();
                ItemStack result = recipe.getResultItem(helper.getLevel().registryAccess());
                check(result.is(NtmItems.POWDER_FLUX.get()) && result.getCount() == row.count(), row.path() + " yields " + result + ", expected " + row.count() + " x powder_flux (PowderRecipes.java:67-73)");

                // the ingredient multiset: the named dusts, each exactly one item, plus one ingredient that accepts every sand and nothing else listed
                List<Item> singles = new ArrayList<>();
                int sands = 0;
                for(Ingredient ingredient : recipe.getIngredients()) {
                    if(ingredient.test(new ItemStack(Items.SAND)) && ingredient.test(new ItemStack(Items.RED_SAND))) {
                        sands++;
                        for(Item item : row.ingredients()) check(!ingredient.test(new ItemStack(item)), row.path() + ": the sand ingredient also accepts " + item);
                    } else {
                        ItemStack[] items = ingredient.getItems();
                        check(items.length == 1, row.path() + ": an ingredient lists " + items.length + " items, expected exactly one");
                        singles.add(items[0].getItem());
                    }
                }
                check(sands == 1, row.path() + " has " + sands + " sand ingredients, expected 1 (KEY_SAND)");
                check(singles.size() == row.ingredients().length && singles.containsAll(List.of(row.ingredients())),
                        row.path() + " has the non-sand ingredients " + singles + ", expected " + List.of(row.ingredients()));
            }

            // real grids through the RecipeManager, the way a crafting table asks it (a charcoal + sand grid; powder_lead + sulfur + red sand)
            check(craft(helper, "powder_flux_from_charcoal", List.of(new ItemStack(Items.CHARCOAL), new ItemStack(Items.SAND))).getCount() == 1, "charcoal + sand does not craft 1 flux");
            ItemStack lead = craft(helper, "powder_flux_from_lead_sulfur",
                    List.of(new ItemStack(NtmItems.POWDER_LEAD.get()), new ItemStack(NtmItems.SULFUR.get()), new ItemStack(Items.RED_SAND)));
            check(lead.is(NtmItems.POWDER_FLUX.get()) && lead.getCount() == 8, "powder_lead + sulfur + red sand crafts " + lead + ", expected 8 x powder_flux (PowderRecipes.java:70)");
            for(Flux row : rows) {
                List<ItemStack> grid = new ArrayList<>();
                for(Item item : row.ingredients()) grid.add(new ItemStack(item));
                grid.add(new ItemStack(Items.SAND));
                ItemStack crafted = craft(helper, row.path(), grid);
                check(crafted.is(NtmItems.POWDER_FLUX.get()) && crafted.getCount() == row.count(), row.path() + " crafts " + crafted + ", expected " + row.count() + " x powder_flux");
            }

            // a grid without sand is not a flux recipe
            List<RecipeHolder<CraftingRecipe>> bare = helper.getLevel().getRecipeManager().getRecipesFor(RecipeType.CRAFTING, input(List.of(new ItemStack(Items.CHARCOAL))), helper.getLevel());
            for(RecipeHolder<CraftingRecipe> holder : bare) check(!holder.id().getPath().startsWith("powder_flux"), "a lone charcoal matches " + holder.id());
        }).run();
        passed("flux_recipes").run();
        helper.succeed();
    }

    private static CraftingInput input(List<ItemStack> items) {
        List<ItemStack> cells = new ArrayList<>(items);
        check(cells.size() <= 9, "the grid has " + cells.size() + " items");
        while(cells.size() < 9) cells.add(ItemStack.EMPTY);
        return CraftingInput.of(3, 3, cells);
    }

    /** Requires the recipe {@code path} among the matches of the grid and returns what it assembles. */
    private static ItemStack craft(GameTestHelper helper, String path, List<ItemStack> items) {
        CraftingInput input = input(items);
        List<RecipeHolder<CraftingRecipe>> all = helper.getLevel().getRecipeManager().getRecipesFor(RecipeType.CRAFTING, input, helper.getLevel());
        RecipeHolder<CraftingRecipe> found = null;
        for(RecipeHolder<CraftingRecipe> holder : all) if(holder.id().equals(id(path))) found = holder;
        List<ResourceLocation> ids = new ArrayList<>();
        for(RecipeHolder<CraftingRecipe> holder : all) ids.add(holder.id());
        check(found != null, "the grid " + items + " matches " + ids + ", expected " + id(path));
        Optional<RecipeHolder<CraftingRecipe>> first = helper.getLevel().getRecipeManager().getRecipeFor(RecipeType.CRAFTING, input, helper.getLevel());
        check(first.isPresent(), "getRecipeFor finds nothing for " + items);
        return found.value().assemble(input, helper.getLevel().registryAccess());
    }

    // ---------------------------------------------------------------- 4. plan_c

    // ConsumableRecipes.java:119: plan_c, "PFP", P = powder_poison, F = F.dust() (the fluorite); the item is a PillItem (ItemPill.java)
    @GameTest(template = TEMPLATE, batch = "hbm29a_plan_c_recipe", timeoutTicks = 100)
    public static void plan_c_recipe(GameTestHelper helper) {
        guard(() -> {
            RecipeHolder<?> holder = helper.getLevel().getRecipeManager().byKey(id("plan_c")).orElse(null);
            check(holder != null, "recipe " + id("plan_c") + " is not loaded (ConsumableRecipes.java:119)");
            check(holder.value() instanceof ShapedRecipe, "plan_c is " + holder.value().getClass().getSimpleName() + ", expected a shaped recipe");
            ShapedRecipe recipe = (ShapedRecipe) holder.value();
            check(recipe.getWidth() == 3 && recipe.getHeight() == 1, "plan_c is " + recipe.getWidth() + "x" + recipe.getHeight() + ", expected one row of three (\"PFP\")");
            List<Ingredient> ingredients = recipe.getIngredients();
            check(ingredients.size() == 3, "plan_c has " + ingredients.size() + " ingredient cells, expected 3");
            Item[] pattern = { NtmItems.POWDER_POISON.get(), NtmItems.FLUORITE.get(), NtmItems.POWDER_POISON.get() };
            for(int i = 0; i < 3; i++) {
                ItemStack[] items = ingredients.get(i).getItems();
                check(items.length == 1 && items[0].is(pattern[i]), "plan_c cell " + i + " is " + List.of(items) + ", expected " + pattern[i] + " (\"PFP\", ConsumableRecipes.java:119)");
            }
            ItemStack result = recipe.getResultItem(helper.getLevel().registryAccess());
            check(result.is(NtmItems.PLAN_C.get()) && result.getCount() == 1, "plan_c yields " + result + ", expected 1 x plan_c");

            // a real grid: powder_poison, fluorite, powder_poison in one row of a 3x3 grid; the order fluorite, poison, poison is not the recipe
            ItemStack crafted = craft(helper, "plan_c", List.of(new ItemStack(NtmItems.POWDER_POISON.get()), new ItemStack(NtmItems.FLUORITE.get()), new ItemStack(NtmItems.POWDER_POISON.get())));
            check(crafted.is(NtmItems.PLAN_C.get()) && crafted.getCount() == 1, "the PFP grid crafts " + crafted + ", expected 1 x plan_c");
            List<RecipeHolder<CraftingRecipe>> wrong = helper.getLevel().getRecipeManager().getRecipesFor(RecipeType.CRAFTING,
                    input(List.of(new ItemStack(NtmItems.FLUORITE.get()), new ItemStack(NtmItems.POWDER_POISON.get()), new ItemStack(NtmItems.POWDER_POISON.get()))), helper.getLevel());
            for(RecipeHolder<CraftingRecipe> match : wrong) check(!match.id().equals(id("plan_c")), "the FPP grid matches plan_c");

            check(NtmItems.PLAN_C.get() instanceof PillItem, "plan_c is " + NtmItems.PLAN_C.get().getClass().getSimpleName() + ", expected a PillItem (ItemPill.java)");
            check(NtmItems.PLAN_C.get().getUseDuration(new ItemStack(NtmItems.PLAN_C.get()), helper.makeMockPlayer(GameType.SURVIVAL)) == 10, "plan_c use duration is not 10 ticks (ItemPill.java:123-125)");
        }).run();
        passed("plan_c_recipe").run();
        helper.succeed();
    }

    // ModDamageSource.java:12-13: euthanizedSelf and euthanizedSelf2, both setDamageBypassesArmor
    @GameTest(template = TEMPLATE, batch = "hbm29a_euthanized_types", timeoutTicks = 100)
    public static void euthanized_damage_types(GameTestHelper helper) {
        guard(() -> {
            Registry<DamageType> registry = helper.getLevel().registryAccess().registryOrThrow(Registries.DAMAGE_TYPE);
            Map<ResourceKey<DamageType>, String> expected = new TreeMap<>((a, b) -> a.location().compareTo(b.location()));
            expected.put(NtmDamageTypes.EUTHANIZED_SELF, "euthanizedSelf");
            expected.put(NtmDamageTypes.EUTHANIZED_SELF_2, "euthanizedSelf2");
            check(NtmDamageTypes.EUTHANIZED_SELF.location().equals(id("euthanized_self")) && NtmDamageTypes.EUTHANIZED_SELF_2.location().equals(id("euthanized_self_2")),
                    "the damage type keys are " + NtmDamageTypes.EUTHANIZED_SELF.location() + " and " + NtmDamageTypes.EUTHANIZED_SELF_2.location());
            for(Map.Entry<ResourceKey<DamageType>, String> entry : expected.entrySet()) {
                DamageType type = registry.get(entry.getKey());
                check(type != null, "damage type " + entry.getKey().location() + " is not in the server registry (ModDamageSource.java:12-13)");
                check(entry.getValue().equals(type.msgId()), entry.getKey().location() + " has message id " + type.msgId() + ", expected " + entry.getValue() + " (ModDamageSource.java:12-13)");
                check(registry.getHolderOrThrow(entry.getKey()).is(DamageTypeTags.BYPASSES_ARMOR), entry.getKey().location() + " is not in #minecraft:bypasses_armor (setDamageBypassesArmor, ModDamageSource.java:12-13)");
                DamageSource source = helper.getLevel().damageSources().source(entry.getKey());
                check(source.is(DamageTypeTags.BYPASSES_ARMOR), "a source of " + entry.getKey().location() + " does not bypass armor");
            }
        }).run();
        passed("euthanized_damage_types").run();
        helper.succeed();
    }

    private static IronGolem armoredGolem(GameTestHelper helper, double x) {
        IronGolem golem = helper.spawnWithNoFreeWill(EntityType.IRON_GOLEM, new Vec3(x, 1, 3.5));
        golem.setItemSlot(EquipmentSlot.HEAD, new ItemStack(Items.DIAMOND_HELMET));
        golem.setItemSlot(EquipmentSlot.CHEST, new ItemStack(Items.DIAMOND_CHESTPLATE));
        golem.setItemSlot(EquipmentSlot.LEGS, new ItemStack(Items.DIAMOND_LEGGINGS));
        golem.setItemSlot(EquipmentSlot.FEET, new ItemStack(Items.DIAMOND_BOOTS));
        return golem;
    }

    private static float hit(LivingEntity entity, DamageSource source, float amount) {
        entity.invulnerableTime = 0;
        entity.setHealth(entity.getMaxHealth());
        entity.hurt(source, amount);
        return entity.getMaxHealth() - entity.getHealth();
    }

    // ItemPill.java:48-51: ten 1,000-point hits of euthanizedSelf / euthanizedSelf2, both bypassing armor (ModDamageSource.java:12-13)
    @GameTest(template = TEMPLATE, batch = "hbm29a_plan_c_effect", timeoutTicks = 100)
    public static void plan_c_effect(GameTestHelper helper) {
        IronGolem armored = armoredGolem(helper, 2.5);
        IronGolem bare = helper.spawnWithNoFreeWill(EntityType.IRON_GOLEM, new Vec3(4.5, 1, 3.5));
        IronGolem viaLambda = armoredGolem(helper, 6.5);
        IronGolem viaItem = armoredGolem(helper, 8.5);
        helper.startSequence()
                .thenIdle(2)
                .thenExecute(guard(() -> {
                    // equipment attributes apply on the entity's own tick: the armored golems carry the diamond set's 20 armor points, the bare one none
                    check(armored.getArmorValue() - bare.getArmorValue() == 20, "the armored golem has armor " + armored.getArmorValue() + ", the bare one " + bare.getArmorValue() + "; a full diamond set is 20");

                    // 30 points of an armor-respecting type (cactus) are reduced by the armor, 30 points of either euthanized type are not: the same health leaves as from a bare mob
                    float cactus = hit(armored, helper.getLevel().damageSources().cactus(), 30F);
                    check(cactus < 30F, "30 cactus damage removes " + cactus + " health from the armored golem, expected the armor to absorb part of it");
                    for(var key : List.of(NtmDamageTypes.EUTHANIZED_SELF, NtmDamageTypes.EUTHANIZED_SELF_2)) {
                        DamageSource source = helper.getLevel().damageSources().source(key);
                        float onArmor = hit(armored, source, 30F);
                        float onBare = hit(bare, source, 30F);
                        check(onArmor == 30F && onBare == 30F, key.location() + " removes " + onArmor + " from the armored golem and " + onBare + " from the bare one, expected 30 each (bypasses armor, ModDamageSource.java:12-13)");
                    }

                    // the pill's own effect: ten 1,000-point hits kill a mob in full diamond armor (ItemPill.java:48-51), through the lambda and through the item
                    check(viaLambda.isAlive() && viaItem.isAlive(), "the golems are dead before the pill");
                    PillItem.LAMBDA_PLAN_C.accept(viaLambda);
                    check(viaLambda.isDeadOrDying() && viaLambda.getHealth() <= 0F, "LAMBDA_PLAN_C left the armored golem at health " + viaLambda.getHealth());

                    ItemStack pill = new ItemStack(NtmItems.PLAN_C.get());
                    pill = NtmItems.PLAN_C.get().finishUsingItem(pill, helper.getLevel(), viaItem);
                    check(viaItem.isDeadOrDying() && viaItem.getHealth() <= 0F, "finishUsingItem of plan_c left the armored golem at health " + viaItem.getHealth());
                    passed("plan_c_effect").run();
                }))
                .thenSucceed();
    }

    // ---------------------------------------------------------------- 5. models and blockstates

    private static JsonObject json(String path) {
        try(InputStream in = Goal29AGameTests.class.getResourceAsStream(path)) {
            check(in != null, path + " is not on the classpath");
            JsonElement parsed = JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8));
            check(parsed.isJsonObject(), path + " is not a JSON object");
            return parsed.getAsJsonObject();
        } catch(IOException e) {
            throw new GameTestAssertException("Unexpected " + e);
        }
    }

    private static void texture(String location, String owner) {
        check(location.startsWith(NuclearTechMod.MODID + ":"), owner + " texture " + location + " is not in the mod namespace");
        String path = "/assets/" + NuclearTechMod.MODID + "/textures/" + location.substring(NuclearTechMod.MODID.length() + 1) + ".png";
        try(InputStream in = Goal29AGameTests.class.getResourceAsStream(path)) {
            check(in != null, owner + ": " + path + " is not on the classpath");
            byte[] signature = in.readNBytes(8);
            check(signature.length == 8 && signature[0] == (byte) 0x89 && signature[1] == 'P' && signature[2] == 'N' && signature[3] == 'G', owner + ": " + path + " is not a PNG file");
        } catch(IOException e) {
            throw new GameTestAssertException("Unexpected " + e);
        }
    }

    // resources the Goal29A items and blocks need on the client; the server never loads assets, so they are read from the mod's classpath
    @GameTest(template = TEMPLATE, batch = "hbm29a_models", timeoutTicks = 100)
    public static void models_and_blockstates(GameTestHelper helper) {
        guard(() -> {
            // item models: the generated parent with one layer0; ammo_debug shares the ammo_45 texture
            Map<String, String> itemModels = new TreeMap<>();
            itemModels.put("plan_c", "hbmsntm:item/plan_c");
            itemModels.put("no9", "hbmsntm:item/no9");
            itemModels.put("ammo_debug", "hbmsntm:item/ammo_45");
            for(Map.Entry<String, String> entry : itemModels.entrySet()) {
                JsonObject model = json("/assets/hbmsntm/models/item/" + entry.getKey() + ".json");
                check(model.has("parent") && "minecraft:item/generated".equals(model.get("parent").getAsString()), "item model " + entry.getKey() + " has parent " + model.get("parent"));
                JsonObject textures = model.getAsJsonObject("textures");
                check(textures != null && textures.has("layer0") && entry.getValue().equals(textures.get("layer0").getAsString()),
                        "item model " + entry.getKey() + " layer0 is " + (textures == null ? null : textures.get("layer0")) + ", expected " + entry.getValue());
                texture(entry.getValue(), "item model " + entry.getKey());
            }
            for(String png : List.of("plan_c", "no9", "ammo_45")) texture("hbmsntm:item/" + png, "texture " + png);

            // blockstates: a single "" variant whose model hbmsntm:block/<name>_particle exists and carries a particle texture
            List<String> blocks = List.of("rad_lava", "volcanic_lava", "gas_radon", "gas_radon_dense", "gas_radon_tomb", "gas_meltdown", "gas_monoxide", "gas_asbestos", "gas_coal", "gas_flammable", "gas_explosive");
            check(blocks.size() == 11, "the expected blockstate list has " + blocks.size() + " entries, expected 11 (rad_lava, volcanic_lava and nine gas blocks)");
            for(String name : blocks) {
                JsonObject state = json("/assets/hbmsntm/blockstates/" + name + ".json");
                JsonObject variants = state.getAsJsonObject("variants");
                check(variants != null && variants.size() == 1 && variants.has(""), "blockstate " + name + " has variants " + (variants == null ? null : variants.keySet()) + ", expected only \"\"");
                JsonElement variant = variants.get("");
                check(variant.isJsonObject() && variant.getAsJsonObject().has("model"), "blockstate " + name + " variant \"\" is not a single model object");
                String model = variant.getAsJsonObject().get("model").getAsString();
                check(("hbmsntm:block/" + name + "_particle").equals(model), "blockstate " + name + " points at " + model + ", expected hbmsntm:block/" + name + "_particle");
                JsonObject modelFile = json("/assets/hbmsntm/models/block/" + name + "_particle.json");
                JsonObject textures = modelFile.getAsJsonObject("textures");
                check(textures != null && textures.has("particle") && !textures.get("particle").getAsString().isEmpty(), "model " + name + "_particle has no particle texture");
                texture(textures.get("particle").getAsString(), "model " + name + "_particle");
            }
        }).run();
        passed("models_and_blockstates").run();
        helper.succeed();
    }

    // ---------------------------------------------------------------- 6. JEI subtype interpreters

    /** The interpreter classes implement the JEI API, so they are only touched here, behind a classpath probe. */
    private static final class JeiChecks {
        static void metaSubtype(ItemStack recipeResult, ItemStack creative) {
            Object fromRecipe = MetaSubtypeInterpreter.INSTANCE.getSubtypeData(recipeResult, UidContext.Ingredient);
            Object fromCreative = MetaSubtypeInterpreter.INSTANCE.getSubtypeData(creative, UidContext.Ingredient);
            check(fromRecipe != null && fromRecipe.equals(fromCreative), "MetaSubtypeInterpreter gives " + fromRecipe + " for the anvil_iron result and " + fromCreative + " for the creative iron anvil, expected equal values");
        }

        static void run() {
            // BlueprintsSubtypeInterpreter: blueprints differ by their pool only (BlueprintsItem.grabPool)
            Object a1 = BlueprintsSubtypeInterpreter.INSTANCE.getSubtypeData(BlueprintsItem.make("pool_a"), UidContext.Ingredient);
            Object a2 = BlueprintsSubtypeInterpreter.INSTANCE.getSubtypeData(BlueprintsItem.make("pool_a"), UidContext.Ingredient);
            Object b = BlueprintsSubtypeInterpreter.INSTANCE.getSubtypeData(BlueprintsItem.make("pool_b"), UidContext.Ingredient);
            check(a1 != null && a1.equals(a2), "two blueprints of the same pool give " + a1 + " and " + a2 + ", expected equal values");
            check(b != null && !b.equals(a1), "blueprints of different pools give " + a1 + " and " + b + ", expected different values");
            Object plain = BlueprintsSubtypeInterpreter.INSTANCE.getSubtypeData(new ItemStack(NtmItems.BLUEPRINTS.get()), UidContext.Ingredient);
            check(plain == null, "a plain blueprint gives " + plain + ", expected null");

            // BatterySubtypeInterpreter: META and whether the pack holds charge; a recipe output (META only) matches the empty pack
            ItemStack metaOnly = MetaHelper.metaStack(new ItemStack(NtmItems.BATTERY_PACK.get()), 1);
            Object recipeForm = BatterySubtypeInterpreter.INSTANCE.getSubtypeData(metaOnly, UidContext.Ingredient);
            check(metaOnly.get(DataComponents.CUSTOM_DATA) == null, "getSubtypeData added custom data to a META-only battery stack");
            Object empty = BatterySubtypeInterpreter.INSTANCE.getSubtypeData(BatteryPackItem.makeEmptyBattery(MetaHelper.metaStack(new ItemStack(NtmItems.BATTERY_PACK.get()), 1)), UidContext.Ingredient);
            Object full = BatterySubtypeInterpreter.INSTANCE.getSubtypeData(BatteryPackItem.makeFullBattery(MetaHelper.metaStack(new ItemStack(NtmItems.BATTERY_PACK.get()), 1)), UidContext.Ingredient);
            check(recipeForm != null && recipeForm.equals(empty), "a META-only pack gives " + recipeForm + " and an empty pack " + empty + ", expected equal values");
            check(full != null && !full.equals(empty), "a full pack gives " + full + " and an empty pack " + empty + ", expected different values");
            Object otherMeta = BatterySubtypeInterpreter.INSTANCE.getSubtypeData(MetaHelper.metaStack(new ItemStack(NtmItems.BATTERY_PACK.get()), 2), UidContext.Ingredient);
            check(otherMeta != null && !otherMeta.equals(recipeForm), "packs of different META give " + recipeForm + " and " + otherMeta + ", expected different values");
            Object otherFull = BatterySubtypeInterpreter.INSTANCE.getSubtypeData(BatteryPackItem.makeFullBattery(MetaHelper.metaStack(new ItemStack(NtmItems.BATTERY_PACK.get()), 2)), UidContext.Ingredient);
            check(otherFull != null && !otherFull.equals(full), "full packs of different META give " + full + " and " + otherFull + ", expected different values");
        }
    }

    // CraftingManager.java:295: anvil_iron, "III" / " B " / "III" with the iron ingot and block; NTMAnvilBlock.java:145 getDrops sets the META of the placed variant, so the
    // iron anvil the creative tab gives and the one that is mined carry META = Variant.IRON; the crafted result must be that same stack for JEI and for stacking
    @GameTest(template = TEMPLATE, batch = "hbm29a_anvil_iron", timeoutTicks = 100)
    public static void anvil_iron_recipe(GameTestHelper helper) {
        guard(() -> {
            ItemStack creative = MetaHelper.newStack(NtmBlocks.ANVIL.asItem(), 1, NTMAnvilBlock.Variant.IRON.ordinal());
            RecipeHolder<?> holder = helper.getLevel().getRecipeManager().byKey(id("anvil_iron")).orElse(null);
            check(holder != null, "recipe " + id("anvil_iron") + " is not loaded (CraftingManager.java:295)");
            check(holder.value() instanceof ShapedRecipe, "anvil_iron is " + holder.value().getClass().getSimpleName() + ", expected a shaped recipe");
            ShapedRecipe recipe = (ShapedRecipe) holder.value();
            ItemStack result = recipe.getResultItem(helper.getLevel().registryAccess());
            check(result.getCount() == 1 && result.is(NtmBlocks.ANVIL.asItem()), "anvil_iron yields " + result + ", expected 1 x the anvil item (CraftingManager.java:295)");
            check(MetaHelper.getMeta(result) == NTMAnvilBlock.Variant.IRON.ordinal() && result.has(com.hbm.items.component.NtmDataComponents.META.get()),
                    "anvil_iron yields META " + result.get(com.hbm.items.component.NtmDataComponents.META.get()) + ", expected " + NTMAnvilBlock.Variant.IRON.ordinal() + " (NTMAnvilBlock.java:145)");
            check(ItemStack.isSameItemSameComponents(result, creative), "the anvil_iron result " + result + " is not the same item with the same components as the creative iron anvil " + creative);

            // the crafted grid (CraftingManager.java:295: iron ingots around an iron block) assembles the same stack
            ItemStack ingot = new ItemStack(Items.IRON_INGOT), block = new ItemStack(Items.IRON_BLOCK);
            ItemStack crafted = craft(helper, "anvil_iron", List.of(ingot, ingot, ingot, ItemStack.EMPTY, block, ItemStack.EMPTY, ingot, ingot, ingot));
            check(crafted.getCount() == 1 && ItemStack.isSameItemSameComponents(crafted, creative), "the III/ B /III grid crafts " + crafted + ", expected the creative iron anvil");

            try {
                Class.forName("mezz.jei.api.ingredients.subtypes.ISubtypeInterpreter", false, Goal29AGameTests.class.getClassLoader());
                Class.forName("mezz.jei.api.ingredients.subtypes.UidContext", false, Goal29AGameTests.class.getClassLoader());
            } catch(ClassNotFoundException e) {
                LOGGER.warn("{} anvil_iron_recipe: the META subtype part SKIPPED, the JEI API classes are not on the GameTest server classpath ({})", TAG, e);
                passed("anvil_iron_recipe").run();
                return;
            }
            JeiChecks.metaSubtype(result, creative);
            passed("anvil_iron_recipe").run();
        }).run();
        helper.succeed();
    }

    // BlueprintsSubtypeInterpreter and BatterySubtypeInterpreter, the parts that need no JEI runtime (the registration in NtmJeiPlugin is not exercised)
    @GameTest(template = TEMPLATE, batch = "hbm29a_jei_subtypes", timeoutTicks = 100)
    public static void jei_subtype_interpreters(GameTestHelper helper) {
        guard(() -> {
            try {
                Class.forName("mezz.jei.api.ingredients.subtypes.ISubtypeInterpreter", false, Goal29AGameTests.class.getClassLoader());
                Class.forName("mezz.jei.api.ingredients.subtypes.UidContext", false, Goal29AGameTests.class.getClassLoader());
            } catch(ClassNotFoundException e) {
                LOGGER.warn("{} jei_subtype_interpreters SKIPPED: the JEI API classes are not on the GameTest server classpath ({})", TAG, e);
                return;
            }
            JeiChecks.run();
            LOGGER.info("{} jei_subtype_interpreters ran against the JEI API classes", TAG);
        }).run();
        passed("jei_subtype_interpreters").run();
        helper.succeed();
    }
}
