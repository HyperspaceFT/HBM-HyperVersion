package com.hbm.gametest;

import com.hbm.config.NtmConfig;
import com.hbm.extprop.HbmLivingAttachments;
import com.hbm.hazard.HazardData;
import com.hbm.hazard.HazardEntry;
import com.hbm.hazard.HazardRegistry;
import com.hbm.hazard.HazardSystem;
import com.hbm.hazard.type.HazardTypeBase;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.RTGPelletDepletedItem.DepletedRTGMaterial;
import com.hbm.items.machine.RTGPelletItem;
import com.hbm.main.CommonEvents;
import com.hbm.main.NuclearTechMod;
import com.hbm.util.ContaminationUtil;
import com.hbm.util.RTGUtil;
import com.hbm.util.RTGUtil.HalfLifeType;
import com.hbm.util.TagsUtil;
import com.mojang.logging.LogUtils;
import net.minecraft.core.NonNullList;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.contents.TranslatableContents;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.InteractionResultHolder;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.animal.Pig;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.item.crafting.CraftingInput;
import net.minecraft.world.item.crafting.CraftingRecipe;
import net.minecraft.world.item.crafting.Ingredient;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.item.crafting.ShapelessRecipe;
import net.minecraft.world.level.GameType;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.event.tick.EntityTickEvent;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import net.neoforged.neoforge.registries.DeferredItem;
import org.slf4j.Logger;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal23B, the RTG pellets (original ItemRTGPellet, ItemRTGPelletDepleted, RTGUtil, HazardModifierRTGRadiation,
 * HazardRegistry.java:337-347 and :618-627, the pellet recipes of the original MineralRecipes). Same template and conventions as
 * {@link HazardGameTests}; the tests run in their own batch and remove the entities they spawn.
 * <p>
 * Real engine evidence: the item registry, the recipe manager as the running dedicated GameTest server loaded the generated recipes (the ten
 * pellet recipes and the four recycling recipes and the mercury one, asked the way a crafting table asks), the hazard registry as {@code CommonEvents.commonSetup}
 * filled it ({@code HazardSystem.getHazardLevelFromStack} and {@code getHazardsFromStack} on real stacks, including the
 * {@code HazardModifierRTGRadiation} falling with the pellet's remaining life), the production {@code RTGUtil.updateRTGs},
 * {@code RTGUtil.hasHeat}, {@code RTGPelletItem.handleDecay} and {@code getScaledPower}, and a real Pig through
 * {@code HazardSystem.updateLivingInventory} and once through {@code CommonEvents.onLivingTick}. The tooltip lines are read on the server as
 * components ({@code appendHoverText} with {@code Item.TooltipContext.EMPTY}), and {@code use} runs on a mock Player that is never added to
 * the level.
 * <p>
 * Not evidence: the expected values are written from the task book's table and from the original's constants in its multiplication order, so
 * they prove NEO matches the original's table, not the 1.7.10 game. There is no machine here: the RT generator's per-tick use of
 * {@code updateRTGs}, its heat limit and its slot rules are tested by {@link RTGGameTests} (Goal23C); the betavoltaic generator is not ported. The
 * tooltips are not rendered (language values, colours and the F3+H flag from a real client are untested), the chat line and the sound of the
 * right click are not observable (a mock Player has no connection), and no client, real player or saved world takes part; the stored
 * {@code PELLET_DEPLETION} value is only read back inside the running server, never through a save and load.
 * <p>
 * The expectations assume the default config (doRTGsDecay true, scaleRTGPower false, 528 mode off); the tests that depend on it fail with a
 * message when the running server differs.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class RTGPelletGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String BATCH = "rtg_pellets";

    /** The sum of the ten heats with the default config: 3 + 5 + 10 + 15 + 15 + 20 + 20 + 50 + 200 + 600. */
    private static final int HEAT_SUM = 938;
    /** The sum of the ten scaled heats at half life: 2 + 3 + 5 + 8 + 8 + 10 + 10 + 25 + 100 + 300. */
    private static final int HALF_SUM = 471;

    /**
     * One pellet of the task book's B1 table (heat for the default config, the maximum life in ticks) and its hazard row (original
     * HazardRegistry.java:337-346): {@code rad} is written as the product of the registry constants, {@code plainRad} restates it as a number.
     */
    private record Pellet(String id, DeferredItem<Item> item, int heat, DepletedRTGMaterial mat, long max, float rad, float plainRad, float hot, float blinding) {
        RTGPelletItem pellet() {
            return (RTGPelletItem) item.get();
        }

        ItemStack fresh() {
            return new ItemStack(item.get());
        }

        ItemStack withLife(long life) {
            ItemStack stack = fresh();
            RTGPelletItem.setLifespan(stack, life);
            return stack;
        }
    }

    /** Construction order of {@code RTGPelletItem.PELLETS}. */
    private static List<Pellet> pellets() {
        return List.of(
                new Pellet("pellet_rtg_radium", NtmItems.PELLET_RTG_RADIUM, 3, DepletedRTGMaterial.LEAD, 11_520_000_000L, HazardRegistry.ra226 * HazardRegistry.rtg, 11.25F, 0F, 0F),
                new Pellet("pellet_rtg_weak", NtmItems.PELLET_RTG_WEAK, 5, DepletedRTGMaterial.LEAD, 720_000_000L, (HazardRegistry.pu238 + (HazardRegistry.u238 * 2)) * HazardRegistry.billet, 5.25F, 0F, 0F),
                new Pellet("pellet_rtg", NtmItems.PELLET_RTG, 10, DepletedRTGMaterial.LEAD, 631_440_000L, HazardRegistry.pu238 * HazardRegistry.rtg, 15F, 3F, 0F),
                new Pellet("pellet_rtg_strontium", NtmItems.PELLET_RTG_STRONTIUM, 15, DepletedRTGMaterial.ZIRCONIUM, 208_800_000L, HazardRegistry.sr90 * HazardRegistry.rtg, 22.5F, 0F, 0F),
                new Pellet("pellet_rtg_cobalt", NtmItems.PELLET_RTG_COBALT, 15, DepletedRTGMaterial.NICKEL, 38_160_000L, HazardRegistry.co60 * HazardRegistry.rtg, 45F, 0F, 0F),
                new Pellet("pellet_rtg_actinium", NtmItems.PELLET_RTG_ACTINIUM, 20, DepletedRTGMaterial.LEAD, 156_960_000L, HazardRegistry.ac227 * HazardRegistry.rtg, 45F, 0F, 0F),
                new Pellet("pellet_rtg_americium", NtmItems.PELLET_RTG_AMERICIUM, 20, DepletedRTGMaterial.NEPTUNIUM, 3_384_000_000L, HazardRegistry.am241 * HazardRegistry.rtg, 12.75F, 0F, 0F),
                new Pellet("pellet_rtg_polonium", NtmItems.PELLET_RTG_POLONIUM, 50, DepletedRTGMaterial.LEAD, 9_936_000L, HazardRegistry.po210 * HazardRegistry.rtg, 112.5F, 3F, 0F),
                new Pellet("pellet_rtg_gold", NtmItems.PELLET_RTG_GOLD, 200, DepletedRTGMaterial.MERCURY, 194_400L, HazardRegistry.au198 * HazardRegistry.rtg, 750F, 5F, 0F),
                new Pellet("pellet_rtg_lead", NtmItems.PELLET_RTG_LEAD, 600, DepletedRTGMaterial.BISMUTH, 21_600L, HazardRegistry.pb209 * HazardRegistry.rtg, 15_000F, 7F, 50F));
    }

    // 1. Registry, lifespans and config

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rtg_pellet_lifespans(GameTestHelper helper) {
        guard(() -> {
            List<Pellet> rows = pellets();
            check(rows.size() == 10, "the table has " + rows.size() + " rows, expected 10");
            check(RTGPelletItem.PELLETS.size() == rows.size(), "RTGPelletItem.PELLETS holds " + RTGPelletItem.PELLETS.size() + " pellets, expected " + rows.size());
            for(int i = 0; i < rows.size(); i++) {
                check(RTGPelletItem.PELLETS.get(i) == rows.get(i).item().get(), "PELLETS[" + i + "] is " + RTGPelletItem.PELLETS.get(i) + ", expected " + rows.get(i).id());
            }

            // Config: the defaults, and the values the running server uses; the remaining expectations assume them.
            check(NtmConfig.COMMON.DO_RTGS_DECAY.getDefault(), "the default of doRTGsDecay is not true");
            check(!NtmConfig.COMMON.SCALE_RTG_POWER.getDefault(), "the default of scaleRTGPower is not false");
            requireDefaultRtgConfig();

            for(Pellet row : rows) {
                RTGPelletItem pellet = row.pellet();
                check(BuiltInRegistries.ITEM.getKey(pellet).equals(id(row.id())), row.id() + " is registered as " + BuiltInRegistries.ITEM.getKey(pellet));
                check(pellet.getMaxLifespan() == row.max(), row.id() + " max life is " + pellet.getMaxLifespan() + ", expected " + row.max());
                check(pellet.getHeat() == row.heat(), row.id() + " heat is " + pellet.getHeat() + ", expected " + row.heat());
                check(pellet.getDoesDecay(), row.id() + " does not decay");
                check(pellet.getDecayMaterial() == row.mat(), row.id() + " decays to " + pellet.getDecayMaterial() + ", expected " + row.mat());
                ItemStack decay = pellet.getDecayItem();
                check(decay.is(NtmItems.PELLET_RTG_DEPLETED.get()) && decay.getCount() == 1 && MetaHelper.getMeta(decay) == row.mat().ordinal(),
                        row.id() + " decay item is " + decay + " with meta " + MetaHelper.getMeta(decay) + ", expected one depleted pellet of " + row.mat());

                ItemStack stack = row.fresh();
                check(pellet.getLifespan(stack) == row.max(), row.id() + " fresh life is " + pellet.getLifespan(stack) + ", expected " + row.max());
                check(!TagsUtil.hasCustomData(stack), row.id() + " reading the life wrote custom data " + TagsUtil.getCustomData(stack));
            }

            // Gold and lead read the config at run time: 200 / 600 with decay, 100 / 200 without (original ModItems.java:2655-2656).
            check(NtmItems.PELLET_RTG_GOLD.get() instanceof RTGPelletItem gold && gold.getHeat() == (RTGUtil.rtgDecay() ? 200 : 100), "pellet_rtg_gold heat does not follow rtgDecay()");
            check(NtmItems.PELLET_RTG_LEAD.get() instanceof RTGPelletItem lead && lead.getHeat() == (RTGUtil.rtgDecay() ? 600 : 200), "pellet_rtg_lead heat does not follow rtgDecay()");

            // RTGUtil.getLifespan, float arithmetic as in the original.
            check(RTGUtil.getLifespan(87.7F, HalfLifeType.MEDIUM, false) == 420_960_000L, "MEDIUM 87.7 is " + RTGUtil.getLifespan(87.7F, HalfLifeType.MEDIUM, false));
            check(RTGUtil.getLifespan(16.0F, HalfLifeType.LONG, false) == 7_680_000_000L, "LONG 16.0 is " + RTGUtil.getLifespan(16.0F, HalfLifeType.LONG, false));
            check(RTGUtil.getLifespan(2.7F, HalfLifeType.SHORT, false) == 129_600L, "SHORT 2.7 is " + RTGUtil.getLifespan(2.7F, HalfLifeType.SHORT, false));
            check(RTGUtil.getLifespan(1.0F, HalfLifeType.MEDIUM, true) == 17_520_000L, "MEDIUM 1.0 with real years is " + RTGUtil.getLifespan(1.0F, HalfLifeType.MEDIUM, true));
        }).run();
        done(helper, "rtg_pellet_lifespans");
    }

    // 2. Decay through RTGUtil.updateRTGs

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rtg_pellet_decay(GameTestHelper helper) {
        guard(() -> {
            requireDefaultRtgConfig();
            List<Pellet> rows = pellets();
            NonNullList<ItemStack> slots = freshSlots(rows);
            int[] all = allSlots(slots);
            ItemStack plutonium = slots.get(11).copy();

            check(RTGUtil.hasHeat(slots, all), "hasHeat is false for slots 0 to 11");
            check(!RTGUtil.hasHeat(slots, new int[] { 10, 11 }), "hasHeat is true for the empty slot and the billet");

            for(int call = 1; call <= 5; call++) {
                int heat = RTGUtil.updateRTGs(slots, all, true, false);
                check(heat == HEAT_SUM, "call " + call + " returned " + heat + ", expected " + HEAT_SUM);
            }
            for(int i = 0; i < rows.size(); i++) {
                Pellet row = rows.get(i);
                ItemStack stack = slots.get(i);
                check(stack.is(row.item().get()) && stack.getCount() == 1, row.id() + " slot " + i + " holds " + stack + " after five calls");
                check(row.pellet().getLifespan(stack) == row.max() - 5, row.id() + " life is " + row.pellet().getLifespan(stack) + ", expected " + (row.max() - 5));
                check(TagsUtil.getCustomData(stack).getLong(RTGPelletItem.KEY_DEPLETION) == row.max() - 5 && TagsUtil.getCustomData(stack).contains(RTGPelletItem.KEY_DEPLETION),
                        row.id() + " custom data is " + TagsUtil.getCustomData(stack) + ", expected " + RTGPelletItem.KEY_DEPLETION + " " + (row.max() - 5));
            }
            check(slots.get(10).isEmpty(), "the empty slot holds " + slots.get(10));
            check(ItemStack.isSameItemSameComponents(slots.get(11), plutonium) && slots.get(11).getCount() == 1, "the billet slot changed to " + slots.get(11));

            // The default overload reads the config: decay on, scale off.
            int heat = RTGUtil.updateRTGs(slots, all);
            check(heat == HEAT_SUM, "the default overload returned " + heat + ", expected " + HEAT_SUM);
            for(int i = 0; i < rows.size(); i++) {
                check(rows.get(i).pellet().getLifespan(slots.get(i)) == rows.get(i).max() - 6, rows.get(i).id() + " life after the default overload is " + rows.get(i).pellet().getLifespan(slots.get(i)));
            }

            // decay = false: the power is added, nothing is written.
            NonNullList<ItemStack> still = freshSlots(rows);
            for(int call = 1; call <= 3; call++) {
                int stillHeat = RTGUtil.updateRTGs(still, all, false, false);
                check(stillHeat == HEAT_SUM, "decay=false call " + call + " returned " + stillHeat + ", expected " + HEAT_SUM);
            }
            for(int i = 0; i < rows.size(); i++) {
                ItemStack stack = still.get(i);
                check(stack.is(rows.get(i).item().get()) && rows.get(i).pellet().getLifespan(stack) == rows.get(i).max(), rows.get(i).id() + " decayed with decay=false");
                check(!TagsUtil.hasCustomData(stack), rows.get(i).id() + " got custom data with decay=false: " + TagsUtil.getCustomData(stack));
            }
        }).run();
        done(helper, "rtg_pellet_decay");
    }

    // 3. Scaled power

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rtg_pellet_scaled_power(GameTestHelper helper) {
        guard(() -> {
            requireDefaultRtgConfig();
            List<Pellet> rows = pellets();
            int[] expectedHalf = { 2, 3, 5, 8, 8, 10, 10, 25, 100, 300 };
            NonNullList<ItemStack> slots = NonNullList.withSize(rows.size(), ItemStack.EMPTY);
            for(int i = 0; i < rows.size(); i++) {
                Pellet row = rows.get(i);
                check(row.max() % 2 == 0, row.id() + " has an odd maximum life");
                ItemStack half = row.withLife(row.max() / 2);
                slots.set(i, half);
                int expected = (int) (short) Math.ceil(row.heat() * 0.5);
                check(expected == expectedHalf[i], row.id() + " expected half power " + expected + " differs from the plain number " + expectedHalf[i]);
                check(RTGUtil.getPower(row.pellet(), half, true) == expected, row.id() + " scaled power at half life is " + RTGUtil.getPower(row.pellet(), half, true) + ", expected " + expected);
                check(RTGUtil.getPower(row.pellet(), half, false) == row.heat(), row.id() + " unscaled power at half life is " + RTGUtil.getPower(row.pellet(), half, false) + ", expected " + row.heat());
                check(RTGPelletItem.getScaledPower(row.pellet(), half) == expected, row.id() + " getScaledPower is " + RTGPelletItem.getScaledPower(row.pellet(), half));
                check(RTGUtil.getPower(row.pellet(), row.fresh(), true) == row.heat(), row.id() + " scaled power at full life is " + RTGUtil.getPower(row.pellet(), row.fresh(), true));
                check(RTGUtil.getPower(row.pellet(), row.withLife(0), true) == 0, row.id() + " scaled power at life 0 is " + RTGUtil.getPower(row.pellet(), row.withLife(0), true));
                // The config-driven overload with the defaults is the unscaled heat.
                check(RTGUtil.getPower(row.pellet(), half) == row.heat(), row.id() + " getPower(pellet, stack) is " + RTGUtil.getPower(row.pellet(), half));
            }
            int heat = RTGUtil.updateRTGs(slots, allSlots(slots), true, true);
            check(heat == HALF_SUM, "updateRTGs with scaling returned " + heat + ", expected " + HALF_SUM);
        }).run();
        done(helper, "rtg_pellet_scaled_power");
    }

    // 4. Depletion into pellet_rtg_depleted

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rtg_pellet_depletion(GameTestHelper helper) {
        guard(() -> {
            requireDefaultRtgConfig();
            List<Pellet> rows = pellets();
            NonNullList<ItemStack> slots = NonNullList.withSize(rows.size(), ItemStack.EMPTY);
            for(int i = 0; i < rows.size(); i++) slots.set(i, rows.get(i).withLife(1));
            int[] all = allSlots(slots);

            // The power of the last tick is still added: updateRTGs sums first and replaces afterwards.
            int first = RTGUtil.updateRTGs(slots, all, true, false);
            check(first == HEAT_SUM, "the first call returned " + first + ", expected " + HEAT_SUM);
            for(int i = 0; i < rows.size(); i++) {
                Pellet row = rows.get(i);
                check(slots.get(i).is(row.item().get()) && row.pellet().getLifespan(slots.get(i)) == 0, row.id() + " after the first call is " + slots.get(i) + " with life " + row.pellet().getLifespan(slots.get(i)));
            }
            int second = RTGUtil.updateRTGs(slots, all, true, false);
            check(second == HEAT_SUM, "the second call returned " + second + ", expected " + HEAT_SUM);
            for(int i = 0; i < rows.size(); i++) {
                Pellet row = rows.get(i);
                ItemStack stack = slots.get(i);
                check(stack.is(NtmItems.PELLET_RTG_DEPLETED.get()) && stack.getCount() == 1 && MetaHelper.getMeta(stack) == row.mat().ordinal(),
                        row.id() + " after the second call is " + stack + " with meta " + MetaHelper.getMeta(stack) + ", expected one depleted pellet of " + row.mat());
            }
            int third = RTGUtil.updateRTGs(slots, all, true, false);
            check(third == 0, "the third call returned " + third + ", expected 0 (the depleted pellets are no RTG fuel)");
            check(!RTGUtil.hasHeat(slots, all), "hasHeat is true for depleted pellets");

            // decay = false keeps a spent pellet.
            NonNullList<ItemStack> kept = NonNullList.withSize(rows.size(), ItemStack.EMPTY);
            for(int i = 0; i < rows.size(); i++) kept.set(i, rows.get(i).withLife(1));
            for(int call = 1; call <= 3; call++) {
                int heat = RTGUtil.updateRTGs(kept, all, false, false);
                check(heat == HEAT_SUM, "decay=false call " + call + " returned " + heat + ", expected " + HEAT_SUM);
            }
            for(int i = 0; i < rows.size(); i++) {
                Pellet row = rows.get(i);
                check(kept.get(i).is(row.item().get()) && row.pellet().getLifespan(kept.get(i)) == 1, row.id() + " with decay=false is " + kept.get(i) + " with life " + row.pellet().getLifespan(kept.get(i)));
            }

            // handleDecay: a spent pellet is replaced by a new depleted stack, any other one is decayed in place and returned as the same stack.
            Pellet radium = rows.get(0);
            ItemStack spent = radium.withLife(0);
            ItemStack replaced = RTGPelletItem.handleDecay(spent, radium.pellet(), true);
            check(replaced != spent && replaced.is(NtmItems.PELLET_RTG_DEPLETED.get()) && MetaHelper.getMeta(replaced) == DepletedRTGMaterial.LEAD.ordinal(), "handleDecay on life 0 returned " + replaced);
            ItemStack live = radium.withLife(5);
            ItemStack same = RTGPelletItem.handleDecay(live, radium.pellet(), true);
            check(same == live && radium.pellet().getLifespan(same) == 4, "handleDecay on life 5 returned " + same + " with life " + radium.pellet().getLifespan(same));
            ItemStack untouched = radium.withLife(5);
            check(RTGPelletItem.handleDecay(untouched, radium.pellet(), false) == untouched && radium.pellet().getLifespan(untouched) == 5, "handleDecay with decay=false changed the stack");
            // The two-argument overload follows the config (decay on).
            ItemStack byConfig = radium.withLife(5);
            check(RTGPelletItem.handleDecay(byConfig, radium.pellet()) == byConfig && radium.pellet().getLifespan(byConfig) == 4, "handleDecay(stack, pellet) did not decay by the config");
        }).run();
        done(helper, "rtg_pellet_depletion");
    }

    // 5. Recipes

    /** The ingredient multiset of one pellet recipe (task book B2, original MineralRecipes). */
    private record PelletRecipe(String id, Item result, Map<Item, Integer> ingredients) { }

    private record RecycleRecipe(String id, DepletedRTGMaterial mat, Item result, int count) { }

    private static List<PelletRecipe> pelletRecipes() {
        Item plate = NtmItems.PLATE_IRON.get();
        return List.of(
                new PelletRecipe("pellet_rtg", NtmItems.PELLET_RTG.get(), Map.of(NtmItems.BILLET_PU238.get(), 3, plate, 1)),
                new PelletRecipe("pellet_rtg_radium", NtmItems.PELLET_RTG_RADIUM.get(), Map.of(NtmItems.BILLET_RA226.get(), 3, plate, 1)),
                new PelletRecipe("pellet_rtg_weak", NtmItems.PELLET_RTG_WEAK.get(), Map.of(NtmItems.BILLET_U238.get(), 2, NtmItems.BILLET_PU238.get(), 1, plate, 1)),
                new PelletRecipe("pellet_rtg_strontium", NtmItems.PELLET_RTG_STRONTIUM.get(), Map.of(NtmItems.BILLET_SR90.get(), 3, plate, 1)),
                new PelletRecipe("pellet_rtg_cobalt", NtmItems.PELLET_RTG_COBALT.get(), Map.of(NtmItems.BILLET_CO60.get(), 3, plate, 1)),
                new PelletRecipe("pellet_rtg_actinium", NtmItems.PELLET_RTG_ACTINIUM.get(), Map.of(NtmItems.BILLET_ACTINIUM.get(), 3, plate, 1)),
                new PelletRecipe("pellet_rtg_polonium", NtmItems.PELLET_RTG_POLONIUM.get(), Map.of(NtmItems.BILLET_POLONIUM.get(), 3, plate, 1)),
                new PelletRecipe("pellet_rtg_lead", NtmItems.PELLET_RTG_LEAD.get(), Map.of(NtmItems.BILLET_PB209.get(), 3, plate, 1)),
                new PelletRecipe("pellet_rtg_gold", NtmItems.PELLET_RTG_GOLD.get(), Map.of(NtmItems.BILLET_AU198.get(), 3, plate, 1)),
                new PelletRecipe("pellet_rtg_americium", NtmItems.PELLET_RTG_AMERICIUM.get(), Map.of(NtmItems.BILLET_AM241.get(), 3, plate, 1)));
    }

    private static List<RecycleRecipe> recycleRecipes() {
        return List.of(
                new RecycleRecipe("pellet_rtg_depleted_bismuth", DepletedRTGMaterial.BISMUTH, NtmItems.BILLET_BISMUTH.get(), 3),
                new RecycleRecipe("pellet_rtg_depleted_lead", DepletedRTGMaterial.LEAD, NtmItems.INGOT_LEAD.get(), 2),
                new RecycleRecipe("pellet_rtg_depleted_neptunium", DepletedRTGMaterial.NEPTUNIUM, NtmItems.BILLET_NEPTUNIUM.get(), 3),
                new RecycleRecipe("pellet_rtg_depleted_zirconium", DepletedRTGMaterial.ZIRCONIUM, NtmItems.BILLET_ZIRCONIUM.get(), 3));
    }

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rtg_pellet_recipes(GameTestHelper helper) {
        guard(() -> {
            List<PelletRecipe> pelletRows = pelletRecipes();
            check(pelletRows.size() == 10, "the pellet recipe table has " + pelletRows.size() + " rows, expected 10");
            for(PelletRecipe row : pelletRows) {
                ShapelessRecipe recipe = shapeless(helper, row.id());
                Map<Item, Integer> actual = new HashMap<>();
                for(Ingredient ingredient : recipe.getIngredients()) {
                    ItemStack[] items = ingredient.getItems();
                    check(items.length == 1, row.id() + " has an ingredient that accepts " + items.length + " items");
                    actual.merge(items[0].getItem(), 1, Integer::sum);
                }
                check(actual.equals(row.ingredients()), row.id() + " takes " + actual + ", expected " + row.ingredients());
                ItemStack result = recipe.getResultItem(helper.getLevel().registryAccess());
                check(result.is(row.result()) && result.getCount() == 1 && !TagsUtil.hasCustomData(result), row.id() + " yields " + result + ", expected one " + row.result());

                List<ItemStack> grid = new ArrayList<>();
                for(Map.Entry<Item, Integer> entry : row.ingredients().entrySet()) {
                    for(int i = 0; i < entry.getValue(); i++) grid.add(new ItemStack(entry.getKey()));
                }
                ItemStack crafted = craft(helper, row.id(), grid);
                check(crafted.is(row.result()) && crafted.getCount() == 1 && !TagsUtil.hasCustomData(crafted), row.id() + " crafts " + crafted + ", expected one " + row.result());
            }

            List<RecycleRecipe> recycleRows = recycleRecipes();
            check(recycleRows.size() == 4, "the recycling recipe table has " + recycleRows.size() + " rows, expected 4");
            for(RecycleRecipe row : recycleRows) {
                ShapelessRecipe recipe = shapeless(helper, row.id());
                check(recipe.getIngredients().size() == 1, row.id() + " has " + recipe.getIngredients().size() + " ingredients, expected 1");
                Ingredient ingredient = recipe.getIngredients().get(0);
                for(DepletedRTGMaterial mat : DepletedRTGMaterial.values()) {
                    boolean accepts = ingredient.test(MetaHelper.newStack(NtmItems.PELLET_RTG_DEPLETED.get(), 1, mat.ordinal()));
                    check(accepts == (mat == row.mat()), row.id() + (accepts ? " accepts " : " rejects ") + "the depleted " + mat + " pellet");
                }
                // The ingredient is not strict: extra custom data on the right meta does not matter.
                ItemStack extra = MetaHelper.newStack(NtmItems.PELLET_RTG_DEPLETED.get(), 1, row.mat().ordinal());
                CompoundTag tag = new CompoundTag();
                tag.putInt("extra", 1);
                TagsUtil.putCustomData(extra, tag);
                check(ingredient.test(extra), row.id() + " rejects the right meta with extra custom data");

                ItemStack result = recipe.getResultItem(helper.getLevel().registryAccess());
                check(result.is(row.result()) && result.getCount() == row.count() && !TagsUtil.hasCustomData(result), row.id() + " yields " + result + ", expected " + row.count() + " x " + row.result());

                ItemStack input = MetaHelper.newStack(NtmItems.PELLET_RTG_DEPLETED.get(), 1, row.mat().ordinal());
                ItemStack crafted = craft(helper, row.id(), List.of(input));
                check(crafted.is(row.result()) && crafted.getCount() == row.count(), row.id() + " crafts " + crafted + ", expected " + row.count() + " x " + row.result());

                NonNullList<ItemStack> remaining = recipe.getRemainingItems(input(List.of(input)));
                List<ItemStack> kept = new ArrayList<>();
                for(ItemStack stack : remaining) if(!stack.isEmpty()) kept.add(stack);
                check(kept.size() == 1 && kept.get(0).is(NtmItems.PLATE_IRON.get()) && kept.get(0).getCount() == 1, row.id() + " leaves " + kept + ", expected one plate_iron");
            }

            // The mercury row exists since Goal23C (original MineralRecipes.java:219; its ingot_mercury is NEO's nugget_mercury): two nuggets for
            // one depleted MERCURY pellet, the iron plate coming back like the other four. The nickel row (:222-226) still does not.
            String mercuryId = "pellet_rtg_depleted_mercury";
            ShapelessRecipe mercury = shapeless(helper, mercuryId);
            check(mercury.getIngredients().size() == 1, mercuryId + " has " + mercury.getIngredients().size() + " ingredients, expected 1");
            Ingredient mercuryIngredient = mercury.getIngredients().get(0);
            for(DepletedRTGMaterial mat : DepletedRTGMaterial.values()) {
                boolean accepts = mercuryIngredient.test(MetaHelper.newStack(NtmItems.PELLET_RTG_DEPLETED.get(), 1, mat.ordinal()));
                check(accepts == (mat == DepletedRTGMaterial.MERCURY), mercuryId + (accepts ? " accepts " : " rejects ") + "the depleted " + mat + " pellet");
            }
            ItemStack mercuryResult = mercury.getResultItem(helper.getLevel().registryAccess());
            check(mercuryResult.is(NtmItems.NUGGET_MERCURY.get()) && mercuryResult.getCount() == 2 && !TagsUtil.hasCustomData(mercuryResult), mercuryId + " yields " + mercuryResult + ", expected 2 x nugget_mercury");
            ItemStack mercuryInput = MetaHelper.newStack(NtmItems.PELLET_RTG_DEPLETED.get(), 1, DepletedRTGMaterial.MERCURY.ordinal());
            ItemStack mercuryCrafted = craft(helper, mercuryId, List.of(mercuryInput));
            check(mercuryCrafted.is(NtmItems.NUGGET_MERCURY.get()) && mercuryCrafted.getCount() == 2, mercuryId + " crafts " + mercuryCrafted + ", expected 2 x nugget_mercury");
            List<ItemStack> mercuryKept = new ArrayList<>();
            for(ItemStack stack : mercury.getRemainingItems(input(List.of(mercuryInput)))) if(!stack.isEmpty()) mercuryKept.add(stack);
            check(mercuryKept.size() == 1 && mercuryKept.get(0).is(NtmItems.PLATE_IRON.get()) && mercuryKept.get(0).getCount() == 1, mercuryId + " leaves " + mercuryKept + ", expected one plate_iron");

            check(helper.getLevel().getRecipeManager().byKey(id("pellet_rtg_depleted_nickel")).isEmpty(), "recipe pellet_rtg_depleted_nickel exists");
            List<RecipeHolder<CraftingRecipe>> nickel = matching(helper, List.of(MetaHelper.newStack(NtmItems.PELLET_RTG_DEPLETED.get(), 1, DepletedRTGMaterial.NICKEL.ordinal())));
            check(nickel.isEmpty(), "the depleted NICKEL pellet matches " + describe(nickel));
        }).run();
        done(helper, "rtg_pellet_recipes");
    }

    // 6. Hazards

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rtg_pellet_hazards(GameTestHelper helper) {
        guard(() -> {
            for(Pellet row : pellets()) {
                // The product of the registry constants (original order) and the plain number agree.
                check(Math.abs(row.rad() - row.plainRad()) <= 1e-6F * Math.max(1F, row.plainRad()), row.id() + " constant product " + row.rad() + " differs from the plain number " + row.plainRad());
                HazardData data = HazardSystem.itemMap.get(row.item().get());
                check(data != null, row.id() + " is not an item-map row");
                check(data.getMutex() == 0, row.id() + " has mutex " + data.getMutex() + ", expected 0");

                int entries = 1 + (row.hot() > 0 ? 1 : 0) + (row.blinding() > 0 ? 1 : 0);
                List<HazardEntry> order = HazardSystem.getHazardsFromStack(row.fresh());
                check(order.size() == entries, row.id() + " has " + order.size() + " hazard entries, expected " + entries);
                check(order.get(0).getType() == HazardRegistry.RADIATION, row.id() + " first entry is not RADIATION");
                if(row.hot() > 0) check(order.get(1).getType() == HazardRegistry.HOT, row.id() + " second entry is not HOT");
                if(row.blinding() > 0) check(order.get(2).getType() == HazardRegistry.BLINDING, row.id() + " third entry is not BLINDING");

                // The radiation falls linearly toward 0 with the used life (HazardModifierRTGRadiation); hot and blinding stay.
                long max = row.pellet().getMaxLifespan();
                long[] lives = { max, max / 2, 0 };
                float[] radFactors = { 1F, 0.5F, 0F };
                for(int i = 0; i < lives.length; i++) {
                    ItemStack stack = row.withLife(lives[i]);
                    String where = row.id() + " at life " + lives[i];
                    checkLevel(stack, HazardRegistry.RADIATION, row.rad() * radFactors[i], where + " RADIATION");
                    checkLevel(stack, HazardRegistry.RADIATION, row.plainRad() * radFactors[i], where + " RADIATION (plain number)");
                    checkLevel(stack, HazardRegistry.HOT, row.hot(), where + " HOT");
                    checkLevel(stack, HazardRegistry.BLINDING, row.blinding(), where + " BLINDING");
                    check(HazardSystem.getHazardsFromStack(stack).size() == entries, where + " changed the number of entries");
                }
                // A stack without the custom value is a fresh pellet.
                checkLevel(row.fresh(), HazardRegistry.RADIATION, row.plainRad(), row.id() + " fresh RADIATION");
            }

            // Plain numbers of the task book, once more by id.
            ItemStack plutonium = new ItemStack(NtmItems.PELLET_RTG.get());
            checkLevel(plutonium, HazardRegistry.RADIATION, 15F, "pellet_rtg radiation");
            checkLevel(plutonium, HazardRegistry.HOT, 3F, "pellet_rtg hot");
            checkLevel(pelletStack(NtmItems.PELLET_RTG.get(), 631_440_000L / 2), HazardRegistry.RADIATION, 7.5F, "pellet_rtg half life radiation");
            checkLevel(pelletStack(NtmItems.PELLET_RTG.get(), 0), HazardRegistry.RADIATION, 0F, "pellet_rtg spent radiation");
            checkLevel(pelletStack(NtmItems.PELLET_RTG.get(), 0), HazardRegistry.HOT, 3F, "pellet_rtg spent hot");
            checkLevel(new ItemStack(NtmItems.PELLET_RTG_LEAD.get()), HazardRegistry.RADIATION, 15_000F, "pellet_rtg_lead radiation");
            checkLevel(new ItemStack(NtmItems.PELLET_RTG_LEAD.get()), HazardRegistry.HOT, 7F, "pellet_rtg_lead hot");
            checkLevel(new ItemStack(NtmItems.PELLET_RTG_LEAD.get()), HazardRegistry.BLINDING, 50F, "pellet_rtg_lead blinding");
            checkLevel(new ItemStack(NtmItems.PELLET_RTG_GOLD.get()), HazardRegistry.RADIATION, 750F, "pellet_rtg_gold radiation");
            checkLevel(new ItemStack(NtmItems.PELLET_RTG_GOLD.get()), HazardRegistry.HOT, 5F, "pellet_rtg_gold hot");

            // The depleted neptunium pellet is a stack-map row: 2.5 * 1.5 = 3.75 radiation, nothing else; the other five metas carry nothing.
            Item depleted = NtmItems.PELLET_RTG_DEPLETED.get();
            check(!HazardSystem.itemMap.containsKey(depleted), "pellet_rtg_depleted is an item-map row; every meta would carry the hazard");
            for(DepletedRTGMaterial mat : DepletedRTGMaterial.values()) {
                ItemStack stack = MetaHelper.newStack(depleted, 1, mat.ordinal());
                List<HazardEntry> entries = HazardSystem.getHazardsFromStack(stack);
                if(mat == DepletedRTGMaterial.NEPTUNIUM) {
                    check(entries.size() == 1 && entries.get(0).getType() == HazardRegistry.RADIATION, "the depleted NEPTUNIUM pellet has " + entries.size() + " entries");
                    checkLevel(stack, HazardRegistry.RADIATION, HazardRegistry.np237 * HazardRegistry.rtg, "depleted NEPTUNIUM radiation (product)");
                    checkLevel(stack, HazardRegistry.RADIATION, 3.75F, "depleted NEPTUNIUM radiation");
                    HazardData data = HazardSystem.stackMap.get(new ComparableStack(stack).makeSingular());
                    check(data != null && data.getMutex() == 0, "the depleted NEPTUNIUM row is not a stack-map row with mutex 0");
                } else {
                    check(entries.isEmpty(), "the depleted " + mat + " pellet has " + entries.size() + " hazard entries");
                    check(!HazardSystem.stackMap.containsKey(new ComparableStack(stack).makeSingular()), "the depleted " + mat + " pellet is a stack-map row");
                }
            }
        }).run();
        done(helper, "rtg_pellet_hazards");
    }

    private static ItemStack pelletStack(Item pellet, long life) {
        ItemStack stack = new ItemStack(pellet);
        RTGPelletItem.setLifespan(stack, life);
        return stack;
    }

    // 7. Stack sizes and the crafting remainder

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rtg_pellet_stack_size(GameTestHelper helper) {
        guard(() -> {
            for(Pellet row : pellets()) {
                check(row.fresh().getMaxStackSize() == 1, row.id() + " stacks to " + row.fresh().getMaxStackSize() + ", expected 1");
                check(!row.fresh().hasCraftingRemainingItem(), row.id() + " has a crafting remainder");
            }
            Item depleted = NtmItems.PELLET_RTG_DEPLETED.get();
            check(new ItemStack(depleted).getMaxStackSize() == 64, "pellet_rtg_depleted stacks to " + new ItemStack(depleted).getMaxStackSize() + ", expected 64");
            for(DepletedRTGMaterial mat : DepletedRTGMaterial.values()) {
                ItemStack stack = MetaHelper.newStack(depleted, 1, mat.ordinal());
                check(stack.hasCraftingRemainingItem(), "the depleted " + mat + " pellet has no crafting remainder");
                ItemStack remainder = stack.getCraftingRemainingItem();
                check(remainder.is(NtmItems.PLATE_IRON.get()) && remainder.getCount() == 1, "the depleted " + mat + " pellet leaves " + remainder + ", expected one plate_iron");
            }
        }).run();
        done(helper, "rtg_pellet_stack_size");
    }

    // 8. A pig holding pellets (HazardSystem.updateLivingInventory, as CommonEvents.onLivingTick)

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rtg_pellet_living_radium(GameTestHelper helper) {
        List<Entity> spawned = new ArrayList<>();
        try {
            guard(() -> {
                requireHazardConfig();
                Pig pig = pig(helper, spawned, new Vec3(6.5, 1, 8.5));
                check(!pig.level().isClientSide, "the GameTest pig is not on the server");
                check(!ContaminationUtil.isRadImmune(pig), "the pig is radiation immune");

                // HazardTypeRadiation.onUpdate: level * count / 20 per call; 11.25 / 20 = 0.5625 rad for one pellet_rtg_radium.
                float expected = HazardRegistry.ra226 * HazardRegistry.rtg / 20F;
                check(Math.abs(expected - 0.5625F) <= 1e-6F, "the expected increment is " + expected + ", not 0.5625");
                ItemStack radium = new ItemStack(NtmItems.PELLET_RTG_RADIUM.get());
                pig.setItemSlot(EquipmentSlot.MAINHAND, radium);
                HbmLivingAttachments.setRadiation(pig, 0F);
                float previous = 0F;
                for(int tick = 1; tick <= 5; tick++) {
                    HazardSystem.updateLivingInventory(pig);
                    float total = HbmLivingAttachments.getRadiation(pig);
                    LOGGER.info("[hbm-rtg] tick {} with one pellet_rtg_radium on a pig: +{} rad, expected {}", tick, total - previous, expected);
                    check(Math.abs((total - previous) - expected) <= 1e-4F * expected, "tick " + tick + " with pellet_rtg_radium gave " + (total - previous) + " rad, expected " + expected);
                    previous = total;
                }
                check(pig.getMainHandItem() == radium && radium.getCount() == 1 && !TagsUtil.hasCustomData(radium), "holding the pellet changed the stack to " + pig.getMainHandItem());
                check(!pig.isOnFire(), "pellet_rtg_radium set the pig on fire");

                // The production event entry: one application per CommonEvents.onLivingTick call, a control call with empty hands in the same tick.
                pig.setItemSlot(EquipmentSlot.MAINHAND, ItemStack.EMPTY);
                float[] control = tickThroughEvent(pig);
                pig.setItemSlot(EquipmentSlot.MAINHAND, new ItemStack(NtmItems.PELLET_RTG_RADIUM.get()));
                float[] one = tickThroughEvent(pig);
                LOGGER.info("[hbm-rtg] onLivingTick, pellet_rtg_radium in the main hand: +{} rad, +{} env, expected {} each", one[0] - control[0], one[1] - control[1], expected);
                check(Math.abs(one[0] - control[0] - expected) <= 1e-4F * expected, "one event tick gave " + (one[0] - control[0]) + " rad, expected " + expected + " (twice would be " + 2 * expected + ")");
                check(Math.abs(one[1] - control[1] - expected) <= 1e-4F * expected, "one event tick gave " + (one[1] - control[1]) + " environment rad, expected " + expected);
                pig.setItemSlot(EquipmentSlot.MAINHAND, ItemStack.EMPTY);

                // pellet_rtg_lead: RADIATION 15,000 / 20 = 750 rad, HOT 7 -> ceil(7) * 20 = 140 fire ticks on a dry entity, BLINDING 50 -> blindness.
                Pig burning = pig(helper, spawned, new Vec3(10.5, 1, 8.5));
                check(!burning.isInWaterOrRain(), "the pig stands in water or rain");
                burning.setItemSlot(EquipmentSlot.MAINHAND, new ItemStack(NtmItems.PELLET_RTG_LEAD.get()));
                HbmLivingAttachments.setRadiation(burning, 0F);
                burning.removeAllEffects();
                burning.clearFire();
                HazardSystem.updateLivingInventory(burning);
                float rad = HbmLivingAttachments.getRadiation(burning);
                MobEffectInstance blindness = burning.getEffect(MobEffects.BLINDNESS);
                LOGGER.info("[hbm-rtg] pellet_rtg_lead on a pig: +{} rad, blindness {}, {} fire ticks", rad, blindness, burning.getRemainingFireTicks());
                check(Math.abs(rad - 750F) <= 1e-4F * 750F, "pellet_rtg_lead gave " + rad + " rad, expected 750");
                check(burning.isOnFire() && burning.getRemainingFireTicks() == 140, "pellet_rtg_lead left " + burning.getRemainingFireTicks() + " fire ticks, expected 140");
                check(blindness != null, "pellet_rtg_lead gave no blindness");
                burning.setItemSlot(EquipmentSlot.MAINHAND, ItemStack.EMPTY);
            }).run();
        } finally {
            cleanUp(spawned);
        }
        done(helper, "rtg_pellet_living_radium");
    }

    // 9. Tooltip and right click

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void rtg_pellet_tooltip_and_use(GameTestHelper helper) {
        guard(() -> {
            requireDefaultRtgConfig();
            ItemStack stack = new ItemStack(NtmItems.PELLET_RTG.get());

            List<Component> normal = new ArrayList<>();
            stack.getItem().appendHoverText(stack, Item.TooltipContext.EMPTY, normal, TooltipFlag.NORMAL);
            check(normal.size() == 4, "the normal tooltip has " + normal.size() + " lines, expected 4: " + normal);
            check("item.hbmsntm.pellet_rtg.desc".equals(translatable(normal.get(0), "line 1").getKey()), "line 1 is " + normal.get(0));
            TranslatableContents heat = translatable(normal.get(1), "line 2");
            check("desc.item.rtgHeat".equals(heat.getKey()) && heat.getArgs().length == 1 && heat.getArgs()[0] instanceof Number n && n.intValue() == 10, "line 2 is " + normal.get(1));
            TranslatableContents decay = translatable(normal.get(2), "line 3");
            check("desc.item.rtgDecay".equals(decay.getKey()) && decay.getArgs().length == 1 && decay.getArgs()[0] instanceof Component, "line 3 is " + normal.get(2));
            TranslatableContents decayName = translatable((Component) decay.getArgs()[0], "the decay product");
            check("item.hbmsntm.pellet_rtg_depleted.lead".equals(decayName.getKey()), "the decay product is " + decayName.getKey() + ", expected the depleted lead pellet");
            check(!(normal.get(3).getContents() instanceof TranslatableContents) && "100%".equals(normal.get(3).getString()), "line 4 is " + normal.get(3) + ", expected the literal 100%");

            List<Component> advanced = new ArrayList<>();
            stack.getItem().appendHoverText(stack, Item.TooltipContext.EMPTY, advanced, TooltipFlag.ADVANCED);
            check(advanced.size() == 8, "the advanced tooltip has " + advanced.size() + " lines, expected 8: " + advanced);
            for(int i = 0; i < 4; i++) check(advanced.get(i).getString().equals(normal.get(i).getString()), "advanced line " + (i + 1) + " differs from the normal one");
            check("desc.item.rtgExtended".equals(translatable(advanced.get(4), "line 5").getKey()), "line 5 is " + advanced.get(4));
            expectLine(advanced.get(5), "desc.item.rtgTicks", "631440000", "631440000");
            // 631,440,000 ticks = 131 years of 4,800,000, 55 days of 48,000 and no remainder.
            expectLine(advanced.get(6), "desc.item.rtgRemaining", "131", "55", "0.0");
            expectLine(advanced.get(7), "desc.item.rtgMaxLife", "131", "55", "0.0");

            // use() on a mock Player that is never added to the level; the chat line and the sound are not observable here.
            Player player = helper.makeMockPlayer(GameType.SURVIVAL);
            ItemStack plutonium = new ItemStack(NtmItems.PELLET_RTG.get());
            player.setItemInHand(InteractionHand.MAIN_HAND, plutonium);
            InteractionResultHolder<ItemStack> used = plutonium.getItem().use(helper.getLevel(), player, InteractionHand.MAIN_HAND);
            check(used.getResult() == InteractionResult.CONSUME && used.getObject() == plutonium, "use on pellet_rtg returned " + used.getResult() + " with " + used.getObject());
            ItemStack radium = new ItemStack(NtmItems.PELLET_RTG_RADIUM.get());
            player.setItemInHand(InteractionHand.MAIN_HAND, radium);
            InteractionResultHolder<ItemStack> passed = radium.getItem().use(helper.getLevel(), player, InteractionHand.MAIN_HAND);
            check(passed.getResult() == InteractionResult.PASS && passed.getObject() == radium, "use on pellet_rtg_radium returned " + passed.getResult());
            player.setItemInHand(InteractionHand.MAIN_HAND, ItemStack.EMPTY);
        }).run();
        done(helper, "rtg_pellet_tooltip_and_use");
    }

    private static TranslatableContents translatable(Component component, String label) {
        check(component.getContents() instanceof TranslatableContents, label + " is not a translatable component: " + component);
        return (TranslatableContents) component.getContents();
    }

    private static void expectLine(Component line, String key, String... args) {
        TranslatableContents contents = translatable(line, key);
        check(key.equals(contents.getKey()), "the line is " + contents.getKey() + ", expected " + key);
        check(contents.getArgs().length == args.length, key + " has " + contents.getArgs().length + " arguments, expected " + args.length);
        for(int i = 0; i < args.length; i++) check(args[i].equals(contents.getArgs()[i]), key + " argument " + i + " is " + contents.getArgs()[i] + ", expected " + args[i]);
    }

    // Helpers

    private static ResourceLocation id(String path) {
        return ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path);
    }

    /** The ten fresh pellets in slots 0-9, slot 10 empty, slot 11 a billet that is no RTG fuel. */
    private static NonNullList<ItemStack> freshSlots(List<Pellet> rows) {
        NonNullList<ItemStack> slots = NonNullList.withSize(12, ItemStack.EMPTY);
        for(int i = 0; i < rows.size(); i++) slots.set(i, rows.get(i).fresh());
        slots.set(11, new ItemStack(NtmItems.BILLET_PU238.get()));
        return slots;
    }

    private static int[] allSlots(NonNullList<ItemStack> slots) {
        int[] all = new int[slots.size()];
        for(int i = 0; i < all.length; i++) all[i] = i;
        return all;
    }

    private static void requireDefaultRtgConfig() {
        check(RTGUtil.rtgDecay(), "rtgDecay() is false on the running server; the RTG expectations assume the default doRTGsDecay = true");
        check(!RTGUtil.scaleRTGPower(), "scaleRTGPower() is true on the running server; the RTG expectations assume the default scaleRTGPower = false");
    }

    private static void requireHazardConfig() {
        check(NtmConfig.COMMON.ENABLE_CONTAMINATION.get(), "contamination is disabled in the common config; the radiation tests need it");
        check(!NtmConfig.COMMON.DISABLE_HOT.get(), "hot hazards are disabled in the common config");
        check(!NtmConfig.COMMON.DISABLE_BLINDING.get(), "blinding hazards are disabled in the common config");
    }

    private static void checkLevel(ItemStack stack, HazardTypeBase type, float expected, String label) {
        float actual = HazardSystem.getHazardLevelFromStack(stack, type);
        check(Math.abs(actual - expected) <= 1e-6F * Math.max(1F, Math.abs(expected)), label + " level is " + actual + ", expected " + expected);
    }

    /**
     * One {@code CommonEvents.onLivingTick} call from zeroed radiation state; returns the accumulated radiation and the environment total.
     * {@code EntityEffectHandler.tick} moves the environment total into the buffer when {@code tickCount % 20 == 0}, so the sum of both is the
     * environment contribution of this one call in either case.
     */
    private static float[] tickThroughEvent(Pig pig) {
        HbmLivingAttachments.setRadiation(pig, 0F);
        HbmLivingAttachments.setRadEnv(pig, 0F);
        HbmLivingAttachments.setRadBuf(pig, 0F);
        CommonEvents.onLivingTick(new EntityTickEvent.Pre(pig));
        return new float[] { HbmLivingAttachments.getRadiation(pig), HbmLivingAttachments.getRadEnv(pig) + HbmLivingAttachments.getRadBuf(pig) };
    }

    private static Pig pig(GameTestHelper helper, List<Entity> spawned, Vec3 relative) {
        Pig pig = helper.spawn(EntityType.PIG, relative);
        pig.setNoAi(true);
        spawned.add(pig);
        return pig;
    }

    private static void cleanUp(List<Entity> spawned) {
        for(Entity entity : spawned) if(!entity.isRemoved()) entity.discard();
    }

    /** The recipe with this id, which must be a shapeless crafting recipe. */
    private static ShapelessRecipe shapeless(GameTestHelper helper, String path) {
        Optional<RecipeHolder<?>> holder = helper.getLevel().getRecipeManager().byKey(id(path));
        check(holder.isPresent(), "recipe " + id(path) + " is not loaded");
        check(holder.get().value() instanceof ShapelessRecipe, "recipe " + id(path) + " is a " + holder.get().value().getClass().getSimpleName() + ", expected a shapeless recipe");
        return (ShapelessRecipe) holder.get().value();
    }

    /** The grid a crafting table passes to the recipe manager: cells laid out from the top left of a 3x3 grid, trimmed to their bounding box. */
    private static CraftingInput input(List<ItemStack> items) {
        List<ItemStack> cells = new ArrayList<>(items);
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
    private static void done(GameTestHelper helper, String name) {
        LOGGER.info("[hbm-rtg] {} passed", name);
        helper.succeed();
    }
}
