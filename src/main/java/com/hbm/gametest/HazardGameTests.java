package com.hbm.gametest;

import com.hbm.blocks.NtmBlocks;
import com.hbm.config.NtmConfig;
import com.hbm.extprop.HbmLivingAttachments;
import com.hbm.hazard.HazardData;
import com.hbm.hazard.HazardEntry;
import com.hbm.hazard.HazardRegistry;
import com.hbm.hazard.HazardSystem;
import com.hbm.hazard.type.HazardTypeBase;
import com.hbm.inventory.MetaHelper;
import com.hbm.items.NtmItems;
import com.hbm.items.RawIngotItem;
import com.hbm.items.machine.BreedingRodItem.BreedingRodType;
import com.hbm.items.machine.ZirnoxRodItem.ZirnoxType;
import com.hbm.main.CommonEvents;
import com.hbm.main.NuclearTechMod;
import com.hbm.util.ContaminationUtil;
import com.mojang.logging.LogUtils;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.animal.Pig;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.ItemLike;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.event.tick.EntityTickEvent;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import org.slf4j.Logger;

import java.util.ArrayList;
import java.util.List;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal21D, the material radiation hazards (original OreDictManager.DictFrame rows :347-374, :454-455,
 * :490-495 and the item-level fuel and yellowcake rows HazardRegistry.java:289-329, :473-474, registered by NEO's
 * {@code HazardRegistry.registerMaterials}). Same template and conventions as {@link SmokeGameTests}.
 * <p>
 * Real engine evidence: the hazard registry as {@code CommonEvents.commonSetup} filled it on a running dedicated GameTest server
 * ({@code HazardSystem.getHazardLevelFromStack} and {@code getHazardsFromStack} on real stacks, including the ingot_raw metas that
 * live in the stack map), and the per-tick production path {@code HazardSystem.updateLivingInventory(LivingEntity)} used by
 * {@code CommonEvents.onLivingTick}, run once on a real Pig: radiation attachment, fire ticks and the blindness effect. The review fix
 * for the double application on players adds {@code hazard_event_entry_applies_once}, which calls {@code CommonEvents.onLivingTick} itself.
 * Not evidence: the expected values are written here from the original's constants (shape multiplier times material constant,
 * float arithmetic), so they prove NEO matches the original's table, not the 1.7.10 game. The player-inventory path
 * ({@code HazardSystem.updatePlayerInventory}, hazmat resistance, creative and the 200-tick grace of {@code ContaminationUtil.contaminate})
 * is NOT exercised: no mock or fake player is created (it crashes the dedicated GameTest server) and that path is left to the unified
 * in-game acceptance. Tooltips, Geiger readings, world radiation, dropped items and rendering are untested. The tests run in their own
 * batch and remove the entities they spawn.
 * <p>
 * Goal22D adds the addendum rows of {@code HazardRegistry.registerMaterialAddendum} (original HazardRegistry.java:331-335, :478, :485-492 and
 * OreDictManager.java:424, :460: five billets, caesium powder, eight crystals, the asbestos and white phosphorus frames). Real engine evidence:
 * the registry as the running GameTest server filled it, read through {@code getHazardLevelFromStack}/{@code getHazardsFromStack} for each new
 * row, for a sample of 20 rows that existed before the batch, and the per-tick path ({@code updateLivingInventory}, and
 * {@code CommonEvents.onLivingTick} once) on a Pig holding crystal_schrabidium, billet_flashlead, powder_caesium, crystal_phosphorus,
 * crystal_lithium and the asbestos items. Not evidence: the expected values are again written from the original's constants in its
 * multiplication order, so they prove NEO matches the original's table, not the 1.7.10 game. The RTG pellet rows (deferred with the RTG modifier),
 * the player path, tooltips, Geiger readings and the hydroactive explosion in water or rain stay untested.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class HazardGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String BATCH = "hazard_materials";
    /** Every 21D row that is registered: 130 frame item/block/stack registrations and 35 item-level rows. */
    private static final int EXPECTED_ROWS = 165;

    private static final HazardTypeBase[] MATERIAL_TYPES = { HazardRegistry.RADIATION, HazardRegistry.HOT, HazardRegistry.BLINDING, HazardRegistry.HYDROACTIVE };
    private static final String[] MATERIAL_TYPE_NAMES = { "RADIATION", "HOT", "BLINDING", "HYDROACTIVE" };
    private static final HazardTypeBase[] ALL_TYPES = { HazardRegistry.RADIATION, HazardRegistry.DIGAMMA, HazardRegistry.HOT, HazardRegistry.BLINDING,
            HazardRegistry.ASBESTOS, HazardRegistry.COAL, HazardRegistry.HYDROACTIVE, HazardRegistry.EXPLOSIVE };

    /** One registered row: the stack and its expected level per type; 0 means the type is absent. */
    private record Expectation(String label, ItemStack stack, float rad, float hot, float blinding, float hydro) { }

    // Material registrations

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void hazard_material_registrations(GameTestHelper helper) {
        guard(() -> {
            List<Expectation> rows = materialRows();
            check(rows.size() == EXPECTED_ROWS, "the table has " + rows.size() + " rows, expected " + EXPECTED_ROWS);
            List<String> failures = new ArrayList<>();
            for(Expectation row : rows) {
                float[] expected = { row.rad, row.hot, row.blinding, row.hydro };
                int present = 0;
                for(int i = 0; i < MATERIAL_TYPES.length; i++) {
                    float actual = HazardSystem.getHazardLevelFromStack(row.stack, MATERIAL_TYPES[i]);
                    if(expected[i] != 0F) present++;
                    if(actual != expected[i]) failures.add(row.label + " " + MATERIAL_TYPE_NAMES[i] + " is " + actual + ", expected " + expected[i]);
                }
                int entries = HazardSystem.getHazardsFromStack(row.stack).size();
                if(entries != present) failures.add(row.label + " has " + entries + " hazard entries, expected " + present);
            }
            LOGGER.info("[hbm-hazard] checked {} registered rows, {} mismatches", rows.size(), failures.size());
            check(failures.isEmpty(), failures.size() + " mismatches, first: " + failures.subList(0, Math.min(5, failures.size())));

            // Spot values restated as plain numbers (float32): ingot_uranium 0.35, nugget_uranium 0.035, billet 0.175, powder 1.05, block 3.5.
            checkLevel(new ItemStack(NtmItems.INGOT_URANIUM.get()), HazardRegistry.RADIATION, 0.35F, "ingot_uranium");
            checkLevel(new ItemStack(NtmItems.NUGGET_URANIUM.get()), HazardRegistry.RADIATION, 0.035F, "nugget_uranium");
            checkLevel(new ItemStack(NtmItems.BILLET_URANIUM.get()), HazardRegistry.RADIATION, 0.175F, "billet_uranium");
            checkLevel(new ItemStack(NtmItems.POWDER_URANIUM.get()), HazardRegistry.RADIATION, 1.05F, "powder_uranium");
            checkLevel(new ItemStack(NtmBlocks.BLOCK_URANIUM.get()), HazardRegistry.RADIATION, 3.5F, "block_uranium");
            checkLevel(new ItemStack(NtmItems.INGOT_PU239.get()), HazardRegistry.RADIATION, 5F, "ingot_pu239");
            checkLevel(new ItemStack(NtmBlocks.BLOCK_PU239.get()), HazardRegistry.RADIATION, 50F, "block_pu239");
            checkLevel(new ItemStack(NtmItems.INGOT_PLUTONIUM.get()), HazardRegistry.RADIATION, 7.5F, "ingot_plutonium");
            checkLevel(new ItemStack(NtmItems.POWDER_YELLOWCAKE.get()), HazardRegistry.RADIATION, 1.05F, "powder_yellowcake");
            checkLevel(new ItemStack(NtmBlocks.BLOCK_YELLOWCAKE.get()), HazardRegistry.RADIATION, 10.5F, "block_yellowcake");
        }).run();
        done(helper, "hazard_material_registrations");
    }

    /** The ingot_raw metas of sodium (1100) and strontium (3800) live in the stack map; no other ingot_raw meta has a hazard. */
    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void hazard_raw_ingot_stacks(GameTestHelper helper) {
        guard(() -> {
            ItemStack sodium = MetaHelper.newStack(NtmItems.INGOT_RAW, RawIngotItem.Type.SODIUM.meta);
            ItemStack strontium = MetaHelper.newStack(NtmItems.INGOT_RAW, RawIngotItem.Type.STRONTIUM.meta);
            check(RawIngotItem.Type.SODIUM.meta == 1100 && RawIngotItem.Type.STRONTIUM.meta == 3800, "the ingot_raw metas moved");
            checkExact("ingot_raw sodium", sodium, HazardRegistry.HYDROACTIVE, 1F * HazardRegistry.ingot);
            checkExact("ingot_raw strontium", strontium, HazardRegistry.HOT, 1F * HazardRegistry.ingot, HazardRegistry.HYDROACTIVE, 1F * HazardRegistry.ingot);
            List<HazardEntry> order = HazardSystem.getHazardsFromStack(strontium);
            check(order.get(0).getType() == HazardRegistry.HOT && order.get(1).getType() == HazardRegistry.HYDROACTIVE, "strontium entries are not HOT, then HYDROACTIVE");
            check(!HazardSystem.itemMap.containsKey(NtmItems.INGOT_RAW.get()), "ingot_raw is registered per item; its other metas would carry the hazard");
            for(RawIngotItem.Type type : RawIngotItem.Type.values()) {
                if(type == RawIngotItem.Type.SODIUM || type == RawIngotItem.Type.STRONTIUM) continue;
                checkExact("ingot_raw " + type, MetaHelper.newStack(NtmItems.INGOT_RAW, type.meta));
            }
            checkExact("ingot_raw default stack", new ItemStack(NtmItems.INGOT_RAW.get()));
        }).run();
        done(helper, "hazard_raw_ingot_stacks");
    }

    // Entries that existed before Goal21D

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void hazard_existing_unchanged(GameTestHelper helper) {
        guard(() -> {
            float fo = HazardRegistry.fo, powder = HazardRegistry.powder;
            // Values written from the start copy of HazardRegistry.java (build/migration/goal21d/baseline-files).
            checkExact("cell_tritium", new ItemStack(NtmItems.CELL_TRITIUM.get()), HazardRegistry.RADIATION, 0.001F);
            checkExact("cell_sas3", new ItemStack(NtmItems.CELL_SAS3.get()), HazardRegistry.RADIATION, HazardRegistry.sas3, HazardRegistry.BLINDING, 60F);
            checkExact("egg_balefire", new ItemStack(NtmItems.EGG_BALEFIRE.get()), HazardRegistry.RADIATION, HazardRegistry.bf * HazardRegistry.ingot);
            checkExact("gold_ingot", new ItemStack(Items.GOLD_INGOT), HazardRegistry.BLINDING, 4F);
            checkExact("blaze_powder", new ItemStack(Items.BLAZE_POWDER), HazardRegistry.HOT, 4F);
            checkExact("coal", new ItemStack(Items.COAL), HazardRegistry.COAL, 1F);
            checkExact("fallout block", new ItemStack(NtmBlocks.FALLOUT.get()), HazardRegistry.RADIATION, 60F);
            checkExact("breeding rod U235", MetaHelper.newStack(NtmItems.ROD, 1, BreedingRodType.U235.ordinal()), HazardRegistry.RADIATION, HazardRegistry.u235);
            checkClose("fresh zirnox rod", MetaHelper.newStack(NtmItems.ROD_ZIRNOX, 1, ZirnoxType.NATURAL_URANIUM_FUEL.ordinal()), HazardRegistry.RADIATION,
                    HazardRegistry.u * HazardRegistry.rod_dual);
            checkExact("depleted zirnox rod", new ItemStack(NtmItems.ROD_ZIRNOX_NATURAL_URANIUM_FUEL_DEPLETED.get()), HazardRegistry.RADIATION,
                    HazardRegistry.wst * HazardRegistry.rod_dual * 11.5F);
            checkExact("waste_uranium meta 0", MetaHelper.newStack(NtmItems.WASTE_URANIUM, 1, 0), HazardRegistry.RADIATION, HazardRegistry.wst * HazardRegistry.billet * 10F * 0.075F);
            checkExact("waste_uranium meta 1", MetaHelper.newStack(NtmItems.WASTE_URANIUM, 1, 1), HazardRegistry.RADIATION, HazardRegistry.wst * HazardRegistry.billet * 10F,
                    HazardRegistry.HOT, 5F);
            checkExact("nuclear_waste", new ItemStack(NtmItems.NUCLEAR_WASTE.get()), HazardRegistry.RADIATION, HazardRegistry.wst * HazardRegistry.ingot);
            checkExact("block_waste", new ItemStack(NtmBlocks.BLOCK_WASTE.get()), HazardRegistry.RADIATION, HazardRegistry.wst * HazardRegistry.block);
            checkExact("debris_graphite", new ItemStack(NtmItems.DEBRIS_GRAPHITE.get()), HazardRegistry.RADIATION, 70F, HazardRegistry.HOT, 5F);
            checkExact("debris_element", new ItemStack(NtmItems.DEBRIS_ELEMENT.get()), HazardRegistry.RADIATION, 100F);
            checkExact("fallout_pile", new ItemStack(NtmItems.FALLOUT_PILE.get()), HazardRegistry.RADIATION, fo * powder);
            checkExact("gadget_core", new ItemStack(NtmItems.GADGET_CORE.get()), HazardRegistry.RADIATION, HazardRegistry.pu239 * HazardRegistry.nugget * 10);
            checkExact("fleija_propellant", new ItemStack(NtmItems.FLEIJA_PROPELLANT.get()), HazardRegistry.RADIATION, 15F, HazardRegistry.EXPLOSIVE, 8F, HazardRegistry.BLINDING, 50F);
            checkExact("solinium_core", new ItemStack(NtmItems.SOLINIUM_CORE.get()), HazardRegistry.RADIATION, HazardRegistry.sa327 * HazardRegistry.nugget * 8, HazardRegistry.BLINDING, 45F);
        }).run();
        done(helper, "hazard_existing_unchanged");
    }

    // No hazard

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void hazard_none_for_ores_and_unlisted(GameTestHelper helper) {
        guard(() -> {
            // Ore blocks are never registered (Goal21 decision 13); powder_co60_tiny and ingot_i131 have no original row.
            for(String id : List.of("ore_uranium", "ore_uranium_deepslate", "ore_uranium_scorched", "ore_nether_uranium", "ore_nether_uranium_scorched",
                    "ore_gneiss_uranium", "ore_gneiss_uranium_scorched", "ore_thorium", "ore_thorium_deepslate", "ore_nether_plutonium", "ore_schrabidium",
                    "ore_nether_schrabidium", "ore_gneiss_schrabidium", "powder_co60_tiny", "ingot_i131")) {
                checkExact(id, new ItemStack(registered(id, true)));
            }
            // Goal22D registered the rows that were out of scope here (hazard_addendum_registrations). Still without a hazard: block_white_phosphorus,
            // block_fallout and tile_lab_broken have no NEO identity (absent items are skipped), and pellet_rtg exists but its RTG pellet row
            // (original HazardRegistry.java:337-347) is deferred with the RTG modifier.
            for(String id : List.of("block_white_phosphorus", "block_fallout", "tile_lab_broken", "pellet_rtg")) {
                ItemLike item = registered(id, false);
                if(item != Items.AIR) checkExact(id, new ItemStack(item));
            }
            check(registered("pellet_rtg", false) != Items.AIR, "pellet_rtg is no longer registered; the RTG deferral guard would pass vacuously");
            // The ASBESTOS frame's ore shapes are not registered either (Goal21 decision 13); absent ids are skipped.
            for(String id : List.of("ore_asbestos", "ore_asbestos_deepslate", "ore_gneiss_asbestos")) {
                ItemLike item = registered(id, false);
                if(item != Items.AIR) checkExact(id, new ItemStack(item));
            }
        }).run();
        done(helper, "hazard_none_for_ores_and_unlisted");
    }

    // Per-tick application on a non-player living entity (HazardSystem.updateLivingInventory, as CommonEvents.onLivingTick)

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void hazard_living_radiation_and_fire(GameTestHelper helper) {
        List<Entity> spawned = new ArrayList<>();
        try {
            guard(() -> {
                requireHazardConfig();
                Pig pig = pig(helper, spawned);
                check(!ContaminationUtil.isRadImmune(pig), "the pig is radiation immune");

                // 3 ingot_uranium: HazardTypeRadiation.onUpdate takes level * count, divides by 20 and contaminates (CREATIVE, no non-player scaling).
                pig.setItemSlot(EquipmentSlot.MAINHAND, new ItemStack(NtmItems.INGOT_URANIUM.get(), 3));
                HbmLivingAttachments.setRadiation(pig, 0F);
                HazardSystem.updateLivingInventory(pig);
                float level = HazardRegistry.u * HazardRegistry.ingot;
                level *= 3;
                float expected = level / 20F;
                float actual = HbmLivingAttachments.getRadiation(pig);
                LOGGER.info("[hbm-hazard] 3 ingot_uranium on a pig: +{} rad, expected {} (0.35 * 3 / 20 = 0.0525)", actual, expected);
                check(Math.abs(actual - expected) <= 1e-6F, "3 ingot_uranium gave " + actual + " rad, expected " + expected);
                check(!pig.isOnFire(), "uranium set the pig on fire");

                // A second tick adds the same again.
                HazardSystem.updateLivingInventory(pig);
                check(Math.abs(HbmLivingAttachments.getRadiation(pig) - 2 * expected) <= 1e-6F, "the second tick gave " + HbmLivingAttachments.getRadiation(pig));

                // 2 ingot_pu238: 10 * 2 / 20 = 1 rad, and HazardTypeHot sets the fire ticks to ceil(3) * 20 = 60 on an entity that is not in water or rain.
                pig.clearFire();
                check(!pig.isInWaterOrRain(), "the pig stands in water or rain");
                pig.setItemSlot(EquipmentSlot.MAINHAND, new ItemStack(NtmItems.INGOT_PU238.get(), 2));
                HbmLivingAttachments.setRadiation(pig, 0F);
                HazardSystem.updateLivingInventory(pig);
                float pu = HbmLivingAttachments.getRadiation(pig);
                LOGGER.info("[hbm-hazard] 2 ingot_pu238 on a pig: +{} rad, {} fire ticks", pu, pig.getRemainingFireTicks());
                check(Math.abs(pu - 1F) <= 1e-6F, "2 ingot_pu238 gave " + pu + " rad, expected 1");
                check(pig.getRemainingFireTicks() == 60, "ingot_pu238 left " + pig.getRemainingFireTicks() + " fire ticks, expected 60");

                // A material without a hot entry in a stack does not touch the fire ticks.
                pig.clearFire();
                pig.setItemSlot(EquipmentSlot.MAINHAND, new ItemStack(NtmItems.INGOT_PU239.get()));
                HazardSystem.updateLivingInventory(pig);
                check(!pig.isOnFire(), "ingot_pu239 set the pig on fire");
                pig.setItemSlot(EquipmentSlot.MAINHAND, ItemStack.EMPTY);
            }).run();
        } finally {
            cleanUp(spawned);
        }
        done(helper, "hazard_living_radiation_and_fire");
    }

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void hazard_living_blinding(GameTestHelper helper) {
        List<Entity> spawned = new ArrayList<>();
        try {
            guard(() -> {
                requireHazardConfig();
                Pig pig = pig(helper, spawned);

                // ingot_pb209: RADIATION 10000 / 20 = 500, BLINDING 50 -> blindness for ceil(50) ticks (HazardTypeBlinding acts on every living entity
                // without particle protection on the head), HOT 7 -> 140 fire ticks.
                pig.setItemSlot(EquipmentSlot.MAINHAND, new ItemStack(NtmItems.INGOT_PB209.get()));
                HbmLivingAttachments.setRadiation(pig, 0F);
                pig.removeAllEffects();
                pig.clearFire();
                HazardSystem.updateLivingInventory(pig);
                float rad = HbmLivingAttachments.getRadiation(pig);
                MobEffectInstance blindness = pig.getEffect(MobEffects.BLINDNESS);
                LOGGER.info("[hbm-hazard] ingot_pb209 on a pig: +{} rad, blindness {}, {} fire ticks", rad, blindness, pig.getRemainingFireTicks());
                check(Math.abs(rad - 500F) <= 1e-3F, "ingot_pb209 gave " + rad + " rad, expected 500");
                check(blindness != null && blindness.getDuration() == 50 && blindness.getAmplifier() == 0, "ingot_pb209 blindness is " + blindness + ", expected 50 ticks, amplifier 0");
                check(pig.getRemainingFireTicks() == 140, "ingot_pb209 left " + pig.getRemainingFireTicks() + " fire ticks, expected 140");
                pig.setItemSlot(EquipmentSlot.MAINHAND, ItemStack.EMPTY);
            }).run();
        } finally {
            cleanUp(spawned);
        }
        done(helper, "hazard_living_blinding");
    }

    // Review fix O1: the production event entry itself (CommonEvents.onLivingTick) on a server-side non-player. Its Player branch
    // (updatePlayerInventory) and the client-side skip cannot be reached here (no player, no client level); verify_review_goal21d_hazard_once.py
    // checks them in the source and the built classes.

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void hazard_event_entry_applies_once(GameTestHelper helper) {
        List<Entity> spawned = new ArrayList<>();
        try {
            guard(() -> {
                requireHazardConfig();
                Pig pig = pig(helper, spawned);
                check(!pig.level().isClientSide, "the GameTest pig is not on the server");

                // Control call with empty hands: whatever the chunk or the effect handler adds on its own, in the same tick as the real calls.
                float[] control = tickThroughEvent(pig);

                // 3 ingot_uranium in the main hand: one application per call, 0.35 * 3 / 20 = 0.0525 rad and environment RAD/s.
                pig.setItemSlot(EquipmentSlot.MAINHAND, new ItemStack(NtmItems.INGOT_URANIUM.get(), 3));
                float level = HazardRegistry.u * HazardRegistry.ingot;
                level *= 3;
                float expected = level / 20F;
                float[] one = tickThroughEvent(pig);
                LOGGER.info("[hbm-hazard] onLivingTick, 3 ingot_uranium in the main hand: +{} rad, +{} env, expected {} each", one[0] - control[0], one[1] - control[1], expected);
                check(Math.abs(one[0] - control[0] - expected) <= 1e-5F, "one event tick gave " + (one[0] - control[0]) + " rad, expected " + expected + " (twice would be " + 2 * expected + ")");
                check(Math.abs(one[1] - control[1] - expected) <= 1e-5F, "one event tick gave " + (one[1] - control[1]) + " environment rad, expected " + expected);

                // The same stack in the off hand is a second stack: two applications, one per slot.
                pig.setItemSlot(EquipmentSlot.OFFHAND, new ItemStack(NtmItems.INGOT_URANIUM.get(), 3));
                float[] two = tickThroughEvent(pig);
                check(Math.abs(two[0] - control[0] - 2 * expected) <= 1e-5F, "main and off hand gave " + (two[0] - control[0]) + " rad, expected " + 2 * expected);
                check(Math.abs(two[1] - control[1] - 2 * expected) <= 1e-5F, "main and off hand gave " + (two[1] - control[1]) + " environment rad, expected " + 2 * expected);
                pig.setItemSlot(EquipmentSlot.MAINHAND, ItemStack.EMPTY);
                pig.setItemSlot(EquipmentSlot.OFFHAND, ItemStack.EMPTY);
            }).run();
        } finally {
            cleanUp(spawned);
        }
        done(helper, "hazard_event_entry_applies_once");
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

    // Goal22D addendum (HazardRegistry.registerMaterialAddendum)

    /** Every Goal22D row: 14 item-level rows (billets :331-335, caesium :478, crystals :485-492) and 4 frame registrations (ASBESTOS :424, P_WHITE :460). */
    private static final int ADDENDUM_ROWS = 18;
    /** Rows that existed before Goal22D, written from the frozen start copy of HazardRegistry.java (build/migration/goal22d/baseline-files). */
    private static final int SAMPLE_ROWS = 20;

    /** One addendum row: the stack, its expected level per type (0 = absent) and the expected mutex (0 for item-level rows, 0b1 for frame data). */
    private record AddendumRow(String label, ItemStack stack, float rad, float hot, float hydro, float asbestos, int mutex) {
        float expected(HazardTypeBase type) {
            if(type == HazardRegistry.RADIATION) return rad;
            if(type == HazardRegistry.HOT) return hot;
            if(type == HazardRegistry.HYDROACTIVE) return hydro;
            if(type == HazardRegistry.ASBESTOS) return asbestos;
            return 0F;
        }
    }

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void hazard_addendum_registrations(GameTestHelper helper) {
        guard(() -> {
            List<AddendumRow> rows = addendumRows();
            check(rows.size() == ADDENDUM_ROWS, "the addendum table has " + rows.size() + " rows, expected " + ADDENDUM_ROWS);
            List<String> failures = new ArrayList<>();
            for(AddendumRow row : rows) {
                int present = 0;
                for(HazardTypeBase type : ALL_TYPES) {
                    float expected = row.expected(type);
                    float actual = HazardSystem.getHazardLevelFromStack(row.stack, type);
                    if(expected != 0F) present++;
                    if(actual != expected) failures.add(row.label + " " + type.getClass().getSimpleName() + " is " + actual + ", expected " + expected);
                }
                int entries = HazardSystem.getHazardsFromStack(row.stack).size();
                if(entries != present) failures.add(row.label + " has " + entries + " hazard entries, expected " + present);
                HazardData data = HazardSystem.itemMap.get(row.stack.getItem());
                if(data == null || data.getMutex() != row.mutex) failures.add(row.label + " is registered with mutex " + (data == null ? "none (not in the item map)" : data.getMutex()) + ", expected " + row.mutex);
            }
            LOGGER.info("[hbm-hazard] checked {} addendum rows, {} mismatches", rows.size(), failures.size());
            check(failures.isEmpty(), failures.size() + " mismatches, first: " + failures.subList(0, Math.min(5, failures.size())));

            // Entry order is the original's: radiation then hot (:332), hydroactive then hot (:478).
            List<HazardEntry> flashlead = HazardSystem.getHazardsFromStack(new ItemStack(NtmItems.BILLET_FLASHLEAD.get()));
            check(flashlead.get(0).getType() == HazardRegistry.RADIATION && flashlead.get(1).getType() == HazardRegistry.HOT, "billet_flashlead entries are not RADIATION, then HOT");
            List<HazardEntry> caesium = HazardSystem.getHazardsFromStack(new ItemStack(NtmItems.POWDER_CAESIUM.get()));
            check(caesium.get(0).getType() == HazardRegistry.HYDROACTIVE && caesium.get(1).getType() == HazardRegistry.HOT, "powder_caesium entries are not HYDROACTIVE, then HOT");

            // Spot values restated as plain numbers (float32), the acceptance list of Goal22D.
            checkLevel(new ItemStack(NtmItems.BILLET_BALEFIRE_GOLD.get()), HazardRegistry.RADIATION, 250F, "billet_balefire_gold");
            checkLevel(new ItemStack(NtmItems.BILLET_FLASHLEAD.get()), HazardRegistry.RADIATION, 6250F, "billet_flashlead radiation");
            checkLevel(new ItemStack(NtmItems.BILLET_FLASHLEAD.get()), HazardRegistry.HOT, 7F, "billet_flashlead hot");
            checkLevel(new ItemStack(NtmItems.BILLET_PO210BE.get()), HazardRegistry.RADIATION, 112.5F, "billet_po210be");
            checkLevel(new ItemStack(NtmItems.BILLET_RA226BE.get()), HazardRegistry.RADIATION, 11.25F, "billet_ra226be");
            checkLevel(new ItemStack(NtmItems.BILLET_PU238BE.get()), HazardRegistry.RADIATION, 15F, "billet_pu238be");
            checkLevel(new ItemStack(NtmItems.POWDER_CAESIUM.get()), HazardRegistry.HYDROACTIVE, 1F, "powder_caesium hydroactive");
            checkLevel(new ItemStack(NtmItems.POWDER_CAESIUM.get()), HazardRegistry.HOT, 3F, "powder_caesium hot");
            checkLevel(new ItemStack(NtmItems.CRYSTAL_URANIUM.get()), HazardRegistry.RADIATION, 3.5F, "crystal_uranium");
            checkLevel(new ItemStack(NtmItems.CRYSTAL_THORIUM.get()), HazardRegistry.RADIATION, 1F, "crystal_thorium");
            checkLevel(new ItemStack(NtmItems.CRYSTAL_PLUTONIUM.get()), HazardRegistry.RADIATION, 75F, "crystal_plutonium");
            checkLevel(new ItemStack(NtmItems.CRYSTAL_SCHRARANIUM.get()), HazardRegistry.RADIATION, 15F, "crystal_schraranium");
            checkLevel(new ItemStack(NtmItems.CRYSTAL_SCHRABIDIUM.get()), HazardRegistry.RADIATION, 150F, "crystal_schrabidium");
            checkLevel(new ItemStack(NtmItems.CRYSTAL_PHOSPHORUS.get()), HazardRegistry.HOT, 20F, "crystal_phosphorus");
            checkLevel(new ItemStack(NtmItems.CRYSTAL_LITHIUM.get()), HazardRegistry.HYDROACTIVE, 10F, "crystal_lithium");
            checkLevel(new ItemStack(NtmItems.CRYSTAL_TRIXITE.get()), HazardRegistry.RADIATION, 250F, "crystal_trixite");
            checkLevel(new ItemStack(NtmItems.INGOT_ASBESTOS.get()), HazardRegistry.ASBESTOS, 1F, "ingot_asbestos");
            checkLevel(new ItemStack(NtmItems.POWDER_ASBESTOS.get()), HazardRegistry.ASBESTOS, 3F, "powder_asbestos");
            checkLevel(new ItemStack(NtmBlocks.BLOCK_ASBESTOS.get()), HazardRegistry.ASBESTOS, 10F, "block_asbestos");
            checkLevel(new ItemStack(NtmItems.INGOT_PHOSPHORUS.get()), HazardRegistry.HOT, 5F, "ingot_phosphorus");
        }).run();
        done(helper, "hazard_addendum_registrations");
    }

    /**
     * The addendum rows. Item-level rows (original HazardRegistry.registerItems) carry no mutex; the ASBESTOS and P_WHITE frame data are
     * registered by OreDictManager.DictFrame with mutex 0b1, every entry multiplied by the shape constant (clone(hazMult)).
     * Not registered: the RTG pellets :337-347, block_fallout :477, tile_lab_broken :481, block_white_phosphorus (OreDictManager.java:460) and every
     * ore shape; fallout :476, brick_asbestos :480 and powder_coltan_ore :482 existed before and are in hazard_existing_sample_unchanged.
     */
    private static List<AddendumRow> addendumRows() {
        List<AddendumRow> rows = new ArrayList<>();
        addendum(rows, ":331", NtmItems.BILLET_BALEFIRE_GOLD, HazardRegistry.au198 * HazardRegistry.billet, 0F, 0F, 0F, 0);
        addendum(rows, ":332", NtmItems.BILLET_FLASHLEAD, HazardRegistry.pb209 * 1.25F * HazardRegistry.billet, 7F, 0F, 0F, 0);
        addendum(rows, ":333", NtmItems.BILLET_PO210BE, HazardRegistry.pobe * HazardRegistry.billet, 0F, 0F, 0F, 0);
        addendum(rows, ":334", NtmItems.BILLET_RA226BE, HazardRegistry.rabe * HazardRegistry.billet, 0F, 0F, 0F, 0);
        addendum(rows, ":335", NtmItems.BILLET_PU238BE, HazardRegistry.pube * HazardRegistry.billet, 0F, 0F, 0F, 0);
        addendum(rows, ":478", NtmItems.POWDER_CAESIUM, 0F, 3F, 1F, 0F, 0);
        addendum(rows, ":485", NtmItems.CRYSTAL_URANIUM, HazardRegistry.u * HazardRegistry.crystal, 0F, 0F, 0F, 0);
        addendum(rows, ":486", NtmItems.CRYSTAL_THORIUM, HazardRegistry.th232 * HazardRegistry.crystal, 0F, 0F, 0F, 0);
        addendum(rows, ":487", NtmItems.CRYSTAL_PLUTONIUM, HazardRegistry.pu * HazardRegistry.crystal, 0F, 0F, 0F, 0);
        addendum(rows, ":488", NtmItems.CRYSTAL_SCHRARANIUM, HazardRegistry.sr * HazardRegistry.crystal, 0F, 0F, 0F, 0);
        addendum(rows, ":489", NtmItems.CRYSTAL_SCHRABIDIUM, HazardRegistry.sa326 * HazardRegistry.crystal, 0F, 0F, 0F, 0);
        addendum(rows, ":490", NtmItems.CRYSTAL_PHOSPHORUS, 0F, 2F * HazardRegistry.crystal, 0F, 0F, 0);
        addendum(rows, ":491", NtmItems.CRYSTAL_LITHIUM, 0F, 0F, 1F * HazardRegistry.crystal, 0F, 0);
        addendum(rows, ":492", NtmItems.CRYSTAL_TRIXITE, HazardRegistry.trx * HazardRegistry.crystal, 0F, 0F, 0F, 0);
        addendum(rows, "ODM:424", NtmItems.INGOT_ASBESTOS, 0F, 0F, 0F, 1F * HazardRegistry.ingot, 0b1);
        addendum(rows, "ODM:424", NtmItems.POWDER_ASBESTOS, 0F, 0F, 0F, 1F * HazardRegistry.powder, 0b1);
        addendum(rows, "ODM:424", NtmBlocks.BLOCK_ASBESTOS, 0F, 0F, 0F, 1F * HazardRegistry.block, 0b1);
        addendum(rows, "ODM:460", NtmItems.INGOT_PHOSPHORUS, 0F, 5F * HazardRegistry.ingot, 0F, 0F, 0b1);
        return rows;
    }

    private static void addendum(List<AddendumRow> rows, String line, ItemLike item, float rad, float hot, float hydro, float asbestos, int mutex) {
        rows.add(new AddendumRow(line + " " + BuiltInRegistries.ITEM.getKey(item.asItem()).getPath(), new ItemStack(item), rad, hot, hydro, asbestos, mutex));
    }

    // Twenty rows that existed before Goal22D, all types compared exactly.

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void hazard_existing_sample_unchanged(GameTestHelper helper) {
        guard(() -> {
            int[] n = { 0 };
            float powder = HazardRegistry.powder, ingot = HazardRegistry.ingot, billet = HazardRegistry.billet, nugget = HazardRegistry.nugget;
            // Values written from the start copy of HazardRegistry.java (build/migration/goal22d/baseline-files); none comes from the addendum.
            sample(n, "fallout block", new ItemStack(NtmBlocks.FALLOUT.get()), HazardRegistry.RADIATION, 60F);
            sample(n, "brick_asbestos", new ItemStack(NtmBlocks.BRICK_ASBESTOS.get()), HazardRegistry.ASBESTOS, 1F);
            sample(n, "powder_coltan_ore", new ItemStack(NtmItems.POWDER_COLTAN_ORE.get()), HazardRegistry.ASBESTOS, 3F);
            sample(n, "green wool", new ItemStack(Items.GREEN_WOOL), HazardRegistry.RADIATION, 150F);
            sample(n, "white wool", new ItemStack(Items.WHITE_WOOL), HazardRegistry.ASBESTOS, 5F);
            sample(n, "blaze powder", new ItemStack(Items.BLAZE_POWDER), HazardRegistry.HOT, 4F);
            sample(n, "tnt", new ItemStack(Items.TNT), HazardRegistry.EXPLOSIVE, 4F);
            sample(n, "particle_digamma", new ItemStack(NtmItems.PARTICLE_DIGAMMA.get()), HazardRegistry.DIGAMMA, 0.3333F);
            // One item of each 21D frame kind: rad only, rad + hot, rad + blinding + hot, hydro only (LI), hot + hydro (SR), a fission fragment.
            sample(n, "block_u233 (rad)", new ItemStack(NtmBlocks.BLOCK_U233.get()), HazardRegistry.RADIATION, HazardRegistry.u233 * HazardRegistry.block);
            sample(n, "ingot_polonium (rad, hot)", new ItemStack(NtmItems.INGOT_POLONIUM.get()), HazardRegistry.RADIATION, HazardRegistry.po210 * ingot, HazardRegistry.HOT, 3F * ingot);
            sample(n, "billet_pb209 (rad, blinding, hot)", new ItemStack(NtmItems.BILLET_PB209.get()), HazardRegistry.RADIATION, HazardRegistry.pb209 * billet,
                    HazardRegistry.BLINDING, 50F * billet, HazardRegistry.HOT, 7F * billet);
            sample(n, "powder_lithium (hydro)", new ItemStack(NtmItems.POWDER_LITHIUM.get()), HazardRegistry.HYDROACTIVE, 1F * powder);
            sample(n, "nugget_strontium (hot, hydro)", new ItemStack(NtmItems.NUGGET_STRONTIUM.get()), HazardRegistry.HOT, 1F * nugget, HazardRegistry.HYDROACTIVE, 1F * nugget);
            sample(n, "powder_xe135 (fission fragment)", new ItemStack(NtmItems.POWDER_XE135.get()), HazardRegistry.RADIATION, HazardRegistry.xe135 * powder, HazardRegistry.HOT, 10F * powder);
            // Item-level rows and stacks.
            sample(n, "block_yellowcake", new ItemStack(NtmBlocks.BLOCK_YELLOWCAKE.get()), HazardRegistry.RADIATION, HazardRegistry.yc * HazardRegistry.block * HazardRegistry.powder_mult);
            sample(n, "billet_plutonium_fuel", new ItemStack(NtmItems.BILLET_PLUTONIUM_FUEL.get()), HazardRegistry.RADIATION, HazardRegistry.puf * billet);
            sample(n, "quad rod PU239", MetaHelper.newStack(NtmItems.ROD_QUAD, 1, BreedingRodType.PU239.ordinal()), HazardRegistry.RADIATION, HazardRegistry.pu239 * HazardRegistry.rod_quad);
            sample(n, "waste_plutonium meta 1", MetaHelper.newStack(NtmItems.WASTE_PLUTONIUM, 1, 1), HazardRegistry.RADIATION, HazardRegistry.wst * billet * 12.5F, HazardRegistry.HOT, 5F);
            sample(n, "nuclear_waste_tiny", new ItemStack(NtmItems.NUCLEAR_WASTE_TINY.get()), HazardRegistry.RADIATION, HazardRegistry.wst * nugget);
            sample(n, "rod_zirnox_les_fuel_depleted", new ItemStack(NtmItems.ROD_ZIRNOX_LES_FUEL_DEPLETED.get()), HazardRegistry.RADIATION, HazardRegistry.wst * HazardRegistry.rod_dual * 15F,
                    HazardRegistry.BLINDING, 20F);
            check(n[0] == SAMPLE_ROWS, "the sample has " + n[0] + " rows, expected " + SAMPLE_ROWS);
        }).run();
        done(helper, "hazard_existing_sample_unchanged");
    }

    private static void sample(int[] count, String label, ItemStack stack, Object... pairs) {
        checkExact(label, stack, pairs);
        count[0]++;
    }

    // Per-tick application of the new rows on a non-player living entity (HazardSystem.updateLivingInventory, as CommonEvents.onLivingTick)

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void hazard_living_crystal_schrabidium(GameTestHelper helper) {
        List<Entity> spawned = new ArrayList<>();
        try {
            guard(() -> {
                requireHazardConfig();
                Pig pig = pig(helper, spawned);
                check(!pig.level().isClientSide, "the GameTest pig is not on the server");
                check(!ContaminationUtil.isRadImmune(pig), "the pig is radiation immune");

                // HazardTypeRadiation.onUpdate multiplies the level by the stack count and divides by 20; ContaminationUtil.contaminate then adds
                // the amount to the environment total and, for a non-player, increments the radiation by amount * calculateRadiationMod = amount * 1
                // (the 200-tick grace and creative checks are Player-only). 2 crystal_schrabidium: 150 * 2 / 20 = 15 rad per tick.
                pig.setItemSlot(EquipmentSlot.MAINHAND, new ItemStack(NtmItems.CRYSTAL_SCHRABIDIUM.get(), 2));
                float level = HazardRegistry.sa326 * HazardRegistry.crystal;
                level *= 2;
                float expected = level / 20F;
                check(Math.abs(expected - 15F) <= 1e-6F, "the expected increment is " + expected + ", not 15");
                HbmLivingAttachments.setRadiation(pig, 0F);
                float previous = 0F;
                for(int tick = 1; tick <= 5; tick++) {
                    HazardSystem.updateLivingInventory(pig);
                    float total = HbmLivingAttachments.getRadiation(pig);
                    LOGGER.info("[hbm-hazard] tick {} with 2 crystal_schrabidium on a pig: +{} rad, expected {}", tick, total - previous, expected);
                    check(Math.abs((total - previous) - expected) <= 1e-4F * expected, "tick " + tick + " with 2 crystal_schrabidium gave " + (total - previous) + " rad, expected " + expected);
                    previous = total;
                }
                check(pig.getMainHandItem().getCount() == 2, "the crystal stack was consumed");
                check(!pig.isOnFire(), "crystal_schrabidium set the pig on fire");

                // The production event entry: one application per CommonEvents.onLivingTick call, control call with empty hands in the same tick.
                pig.setItemSlot(EquipmentSlot.MAINHAND, ItemStack.EMPTY);
                float[] control = tickThroughEvent(pig);
                pig.setItemSlot(EquipmentSlot.MAINHAND, new ItemStack(NtmItems.CRYSTAL_SCHRABIDIUM.get(), 2));
                float[] one = tickThroughEvent(pig);
                LOGGER.info("[hbm-hazard] onLivingTick, 2 crystal_schrabidium in the main hand: +{} rad, +{} env, expected {} each", one[0] - control[0], one[1] - control[1], expected);
                check(Math.abs(one[0] - control[0] - expected) <= 1e-4F * expected, "one event tick gave " + (one[0] - control[0]) + " rad, expected " + expected + " (twice would be " + 2 * expected + ")");
                check(Math.abs(one[1] - control[1] - expected) <= 1e-4F * expected, "one event tick gave " + (one[1] - control[1]) + " environment rad, expected " + expected);
                pig.setItemSlot(EquipmentSlot.MAINHAND, ItemStack.EMPTY);
            }).run();
        } finally {
            cleanUp(spawned);
        }
        done(helper, "hazard_living_crystal_schrabidium");
    }

    @GameTest(template = TEMPLATE, batch = BATCH, timeoutTicks = 100)
    public static void hazard_living_addendum_fire_and_asbestos(GameTestHelper helper) {
        List<Entity> spawned = new ArrayList<>();
        try {
            guard(() -> {
                requireHazardConfig();
                check(!NtmConfig.COMMON.DISABLE_ASBESTOS.get(), "asbestos hazards are disabled in the common config");
                Pig pig = pig(helper, spawned);
                check(!pig.isInWaterOrRain(), "the pig stands in water or rain");

                // billet_flashlead: RADIATION 6250 / 20 = 312.5 rad, HOT 7 -> HazardTypeHot sets ceil(7) * 20 = 140 fire ticks on a dry entity.
                pig.setItemSlot(EquipmentSlot.MAINHAND, new ItemStack(NtmItems.BILLET_FLASHLEAD.get()));
                HbmLivingAttachments.setRadiation(pig, 0F);
                pig.clearFire();
                HazardSystem.updateLivingInventory(pig);
                float rad = HbmLivingAttachments.getRadiation(pig);
                LOGGER.info("[hbm-hazard] billet_flashlead on a pig: +{} rad, {} fire ticks", rad, pig.getRemainingFireTicks());
                check(Math.abs(rad - 312.5F) <= 1e-4F * 312.5F, "billet_flashlead gave " + rad + " rad, expected 312.5");
                check(pig.getRemainingFireTicks() == 140, "billet_flashlead left " + pig.getRemainingFireTicks() + " fire ticks, expected 140");

                // powder_caesium: HYDROACTIVE 1 only reacts in water or rain (HazardTypeHydroactive.onUpdate), so a dry pig keeps the stack; HOT 3 -> 60 fire ticks.
                pig.setItemSlot(EquipmentSlot.MAINHAND, new ItemStack(NtmItems.POWDER_CAESIUM.get(), 4));
                HbmLivingAttachments.setRadiation(pig, 0F);
                pig.clearFire();
                HazardSystem.updateLivingInventory(pig);
                LOGGER.info("[hbm-hazard] powder_caesium on a dry pig: {} fire ticks, stack {}", pig.getRemainingFireTicks(), pig.getMainHandItem().getCount());
                check(pig.getRemainingFireTicks() == 60, "powder_caesium left " + pig.getRemainingFireTicks() + " fire ticks, expected 60");
                check(pig.getMainHandItem().getCount() == 4, "powder_caesium was consumed on a dry pig: " + pig.getMainHandItem().getCount());
                check(HbmLivingAttachments.getRadiation(pig) == 0F, "powder_caesium added radiation");

                // crystal_phosphorus: HOT 20 -> 400 fire ticks, no radiation.
                pig.setItemSlot(EquipmentSlot.MAINHAND, new ItemStack(NtmItems.CRYSTAL_PHOSPHORUS.get()));
                pig.clearFire();
                HazardSystem.updateLivingInventory(pig);
                check(pig.getRemainingFireTicks() == 400, "crystal_phosphorus left " + pig.getRemainingFireTicks() + " fire ticks, expected 400");
                check(HbmLivingAttachments.getRadiation(pig) == 0F, "crystal_phosphorus added radiation");

                // crystal_lithium: HYDROACTIVE 10 does nothing on a dry pig, and it has no hot entry.
                pig.setItemSlot(EquipmentSlot.MAINHAND, new ItemStack(NtmItems.CRYSTAL_LITHIUM.get(), 3));
                pig.clearFire();
                HazardSystem.updateLivingInventory(pig);
                check(!pig.isOnFire(), "crystal_lithium set the pig on fire");
                check(pig.getMainHandItem().getCount() == 3, "crystal_lithium was consumed on a dry pig");

                // The asbestos items: HazardTypeAsbestos.onUpdate adds min(level, 10) to the asbestos counter of an unprotected head (a pig wears nothing).
                pig.clearFire();
                int[] expected = { 1, 3, 10 };
                ItemStack[] stacks = { new ItemStack(NtmItems.INGOT_ASBESTOS.get()), new ItemStack(NtmItems.POWDER_ASBESTOS.get()), new ItemStack(NtmBlocks.BLOCK_ASBESTOS.get()) };
                for(int i = 0; i < stacks.length; i++) {
                    pig.setItemSlot(EquipmentSlot.MAINHAND, stacks[i]);
                    HbmLivingAttachments.setAsbestos(pig, 0);
                    HazardSystem.updateLivingInventory(pig);
                    int asbestos = HbmLivingAttachments.getAsbestos(pig);
                    LOGGER.info("[hbm-hazard] {} on a pig: +{} asbestos", BuiltInRegistries.ITEM.getKey(stacks[i].getItem()).getPath(), asbestos);
                    check(asbestos == expected[i], BuiltInRegistries.ITEM.getKey(stacks[i].getItem()).getPath() + " gave " + asbestos + " asbestos, expected " + expected[i]);
                }
                check(!pig.isOnFire(), "an asbestos item set the pig on fire");

                // ingot_phosphorus: HOT 5 -> 100 fire ticks.
                pig.setItemSlot(EquipmentSlot.MAINHAND, new ItemStack(NtmItems.INGOT_PHOSPHORUS.get()));
                HazardSystem.updateLivingInventory(pig);
                check(pig.getRemainingFireTicks() == 100, "ingot_phosphorus left " + pig.getRemainingFireTicks() + " fire ticks, expected 100");
                pig.setItemSlot(EquipmentSlot.MAINHAND, ItemStack.EMPTY);
            }).run();
        } finally {
            cleanUp(spawned);
        }
        done(helper, "hazard_living_addendum_fire_and_asbestos");
    }

    // The registered rows. Each line mirrors one original row; hazards are the frame's rad, hot, blinding, hydro (0 = absent),
    // each shape multiplies them by the original's shape constant.

    private static List<Expectation> materialRows() {
        List<Expectation> rows = new ArrayList<>();
        // OreDictManager.registerOres rows (RADIOACTIVE :347-374, HAZARDS :454-455, FISSION FRAGMENTS :490-495). Ore and oreNether shapes
        // are never registered (Goal21 decision 13); the skipped shapes are listed as comments.
        mat(rows, ":347 U", HazardRegistry.u, 0F, 0F, 0F).nugget(NtmItems.NUGGET_URANIUM).billet(NtmItems.BILLET_URANIUM).ingot(NtmItems.INGOT_URANIUM).dust(NtmItems.POWDER_URANIUM).block(NtmBlocks.BLOCK_URANIUM);
        mat(rows, ":348 U233", HazardRegistry.u233, 0F, 0F, 0F).nugget(NtmItems.NUGGET_U233).billet(NtmItems.BILLET_U233).ingot(NtmItems.INGOT_U233).block(NtmBlocks.BLOCK_U233);
        mat(rows, ":349 U235", HazardRegistry.u235, 0F, 0F, 0F).nugget(NtmItems.NUGGET_U235).billet(NtmItems.BILLET_U235).ingot(NtmItems.INGOT_U235).block(NtmBlocks.BLOCK_U235);
        mat(rows, ":350 U238", HazardRegistry.u238, 0F, 0F, 0F).nugget(NtmItems.NUGGET_U238).billet(NtmItems.BILLET_U238).ingot(NtmItems.INGOT_U238).block(NtmBlocks.BLOCK_U238);
        mat(rows, ":351 TH232", HazardRegistry.th232, 0F, 0F, 0F).nugget(NtmItems.NUGGET_TH232).billet(NtmItems.BILLET_TH232).ingot(NtmItems.INGOT_TH232).dust(NtmItems.POWDER_THORIUM).block(NtmBlocks.BLOCK_THORIUM);
        mat(rows, ":352 PU", HazardRegistry.pu, 0F, 0F, 0F).nugget(NtmItems.NUGGET_PLUTONIUM).billet(NtmItems.BILLET_PLUTONIUM).ingot(NtmItems.INGOT_PLUTONIUM).dust(NtmItems.POWDER_PLUTONIUM).block(NtmBlocks.BLOCK_PLUTONIUM);
        mat(rows, ":353 PURG", HazardRegistry.purg, 0F, 0F, 0F).nugget(NtmItems.NUGGET_PU_MIX).billet(NtmItems.BILLET_PU_MIX).ingot(NtmItems.INGOT_PU_MIX).block(NtmBlocks.BLOCK_PU_MIX);
        mat(rows, ":354 PU238", HazardRegistry.pu238, 3F, 0F, 0F).nugget(NtmItems.NUGGET_PU238).billet(NtmItems.BILLET_PU238).ingot(NtmItems.INGOT_PU238).block(NtmBlocks.BLOCK_PU238);
        mat(rows, ":355 PU239", HazardRegistry.pu239, 0F, 0F, 0F).nugget(NtmItems.NUGGET_PU239).billet(NtmItems.BILLET_PU239).ingot(NtmItems.INGOT_PU239).block(NtmBlocks.BLOCK_PU239);
        mat(rows, ":356 PU240", HazardRegistry.pu240, 0F, 0F, 0F).nugget(NtmItems.NUGGET_PU240).billet(NtmItems.BILLET_PU240).ingot(NtmItems.INGOT_PU240).block(NtmBlocks.BLOCK_PU240);
        mat(rows, ":357 PU241", HazardRegistry.pu241, 0F, 0F, 0F).nugget(NtmItems.NUGGET_PU241).billet(NtmItems.BILLET_PU241).ingot(NtmItems.INGOT_PU241);
        mat(rows, ":358 AM241", HazardRegistry.am241, 0F, 0F, 0F).nugget(NtmItems.NUGGET_AM241).billet(NtmItems.BILLET_AM241).ingot(NtmItems.INGOT_AM241);
        mat(rows, ":359 AM242", HazardRegistry.am242, 0F, 0F, 0F).nugget(NtmItems.NUGGET_AM242).billet(NtmItems.BILLET_AM242).ingot(NtmItems.INGOT_AM242);
        mat(rows, ":360 AMRG", HazardRegistry.amrg, 0F, 0F, 0F).nugget(NtmItems.NUGGET_AM_MIX).billet(NtmItems.BILLET_AM_MIX).ingot(NtmItems.INGOT_AM_MIX);
        mat(rows, ":361 NP237", HazardRegistry.np237, 0F, 0F, 0F).nugget(NtmItems.NUGGET_NEPTUNIUM).billet(NtmItems.BILLET_NEPTUNIUM).ingot(NtmItems.INGOT_NEPTUNIUM).dust(NtmItems.POWDER_NEPTUNIUM).block(NtmBlocks.BLOCK_NEPTUNIUM);
        mat(rows, ":362 PO210", HazardRegistry.po210, 3F, 0F, 0F).nugget(NtmItems.NUGGET_POLONIUM).billet(NtmItems.BILLET_POLONIUM).ingot(NtmItems.INGOT_POLONIUM).dust(NtmItems.POWDER_POLONIUM).block(NtmBlocks.BLOCK_POLONIUM);
        mat(rows, ":363 TC99", HazardRegistry.tc99, 0F, 0F, 0F).nugget(NtmItems.NUGGET_TECHNETIUM).billet(NtmItems.BILLET_TECHNETIUM).ingot(NtmItems.INGOT_TECHNETIUM);
        mat(rows, ":364 RA226", HazardRegistry.ra226, 0F, 0F, 0F).nugget(NtmItems.NUGGET_RA226).billet(NtmItems.BILLET_RA226).ingot(NtmItems.INGOT_RA226).dust(NtmItems.POWDER_RA226).block(NtmBlocks.BLOCK_RA226);
        mat(rows, ":365 AC227", HazardRegistry.ac227, 0F, 0F, 0F).nugget(NtmItems.NUGGET_ACTINIUM).billet(NtmItems.BILLET_ACTINIUM).ingot(NtmItems.INGOT_ACTINIUM).dust(NtmItems.POWDER_ACTINIUM).block(NtmBlocks.BLOCK_ACTINIUM).dustSmall(NtmItems.POWDER_ACTINIUM_TINY);
        mat(rows, ":366 CO60", HazardRegistry.co60, 1F, 0F, 0F).nugget(NtmItems.NUGGET_CO60).billet(NtmItems.BILLET_CO60).ingot(NtmItems.INGOT_CO60).dust(NtmItems.POWDER_CO60);
        mat(rows, ":367 AU198", HazardRegistry.au198, 5F, 0F, 0F).nugget(NtmItems.NUGGET_AU198).billet(NtmItems.BILLET_AU198).ingot(NtmItems.INGOT_AU198).dust(NtmItems.POWDER_AU198);
        mat(rows, ":368 PB209", HazardRegistry.pb209, 7F, 50F, 0F).nugget(NtmItems.NUGGET_PB209).billet(NtmItems.BILLET_PB209).ingot(NtmItems.INGOT_PB209);
        // :369 plateCast Mats.MAT_SCHRABIDIUM.make(plate_cast): NEO has no cast plate (original: Mats.MAT_SCHRABIDIUM.make(plate_cast))
        mat(rows, ":369 SA326", HazardRegistry.sa326, 0F, 50F, 0F).nugget(NtmItems.NUGGET_SCHRABIDIUM).billet(NtmItems.BILLET_SCHRABIDIUM).ingot(NtmItems.INGOT_SCHRABIDIUM).dust(NtmItems.POWDER_SCHRABIDIUM).plate(NtmItems.PLATE_SCHRABIDIUM).block(NtmBlocks.BLOCK_SCHRABIDIUM);
        mat(rows, ":370 SA327", HazardRegistry.sa327, 0F, 50F, 0F).nugget(NtmItems.NUGGET_SOLINIUM).billet(NtmItems.BILLET_SOLINIUM).ingot(NtmItems.INGOT_SOLINIUM).block(NtmBlocks.BLOCK_SOLINIUM);
        mat(rows, ":371 SBD", HazardRegistry.sb, 0F, 50F, 0F).ingot(NtmItems.INGOT_SCHRABIDATE).dust(NtmItems.POWDER_SCHRABIDATE).block(NtmBlocks.BLOCK_SCHRABIDATE);
        mat(rows, ":372 SRN", HazardRegistry.sr, 0F, 50F, 0F).ingot(NtmItems.INGOT_SCHRARANIUM).block(NtmBlocks.BLOCK_SCHRARANIUM);
        mat(rows, ":373 GH336", HazardRegistry.gh336, 0F, 0F, 0F).nugget(NtmItems.NUGGET_GH336).billet(NtmItems.BILLET_GH336).ingot(NtmItems.INGOT_GH336);
        mat(rows, ":374 MUD", HazardRegistry.mud, 0F, 0F, 0F).ingot(NtmItems.INGOT_MUD);
        // :454 hazNugget nugget_lithium: hazNugget() registers only the ore key nuggetLithium; in the original it reaches the autogen NUGGET of MAT_LITHIUM (Mats.java:139, OreDictManager.java:551); NEO has no nugget_lithium
        mat(rows, ":454 LI", 0F, 0F, 0F, 1F).ingot(NtmItems.LITHIUM).dustSmall(NtmItems.POWDER_LITHIUM_TINY).dust(NtmItems.POWDER_LITHIUM).block(NtmBlocks.BLOCK_LITHIUM);
        // :455 hazNugget nugget_sodium: hazNugget() registers only the ore key nuggetSodium; in the original it reaches the autogen NUGGET of MAT_SODIUM (Mats.java:135, OreDictManager.java:551); NEO has no nugget_sodium
        mat(rows, ":455 NA", 0F, 0F, 0F, 1F).ingotStack(MetaHelper.newStack(NtmItems.INGOT_RAW, 1100)).dust(NtmItems.POWDER_SODIUM);
        mat(rows, ":490 SR", 0F, 1F, 0F, 1F).ingotStack(MetaHelper.newStack(NtmItems.INGOT_RAW, 3800)).dust(NtmItems.POWDER_STRONTIUM).nugget(NtmItems.NUGGET_STRONTIUM);
        mat(rows, ":491 SR90", HazardRegistry.sr90, 1F, 0F, 1F).dustSmall(NtmItems.POWDER_SR90_TINY).dust(NtmItems.POWDER_SR90).ingot(NtmItems.INGOT_SR90).billet(NtmItems.BILLET_SR90).nugget(NtmItems.NUGGET_SR90);
        mat(rows, ":492 I131", HazardRegistry.i131, 1F, 0F, 0F).dustSmall(NtmItems.POWDER_I131_TINY).dust(NtmItems.POWDER_I131);
        mat(rows, ":493 XE135", HazardRegistry.xe135, 10F, 0F, 0F).dustSmall(NtmItems.POWDER_XE135_TINY).dust(NtmItems.POWDER_XE135);
        mat(rows, ":494 CS137", HazardRegistry.cs137, 3F, 0F, 3F).dustSmall(NtmItems.POWDER_CS137_TINY).dust(NtmItems.POWDER_CS137);
        mat(rows, ":495 AT209", HazardRegistry.at209, 20F, 0F, 0F).dust(NtmItems.POWDER_AT209);

        // HazardRegistry.registerItems item-level rows :289-329 (fuel nuggets, billets, ingots, blocks) and :473-474 (yellowcake): radiation, blinding.
        item(rows, ":289", NtmItems.NUGGET_URANIUM_FUEL, HazardRegistry.uf * HazardRegistry.nugget, 0F);
        item(rows, ":290", NtmItems.BILLET_URANIUM_FUEL, HazardRegistry.uf * HazardRegistry.billet, 0F);
        item(rows, ":291", NtmItems.INGOT_URANIUM_FUEL, HazardRegistry.uf * HazardRegistry.ingot, 0F);
        item(rows, ":292", NtmBlocks.BLOCK_URANIUM_FUEL, HazardRegistry.uf * HazardRegistry.block, 0F);
        item(rows, ":293", NtmItems.BILLET_UZH, HazardRegistry.uzh * HazardRegistry.billet, 0F);
        item(rows, ":295", NtmItems.NUGGET_PLUTONIUM_FUEL, HazardRegistry.puf * HazardRegistry.nugget, 0F);
        item(rows, ":296", NtmItems.BILLET_PLUTONIUM_FUEL, HazardRegistry.puf * HazardRegistry.billet, 0F);
        item(rows, ":297", NtmItems.INGOT_PLUTONIUM_FUEL, HazardRegistry.puf * HazardRegistry.ingot, 0F);
        item(rows, ":298", NtmBlocks.BLOCK_PLUTONIUM_FUEL, HazardRegistry.puf * HazardRegistry.block, 0F);
        item(rows, ":300", NtmItems.NUGGET_THORIUM_FUEL, HazardRegistry.thf * HazardRegistry.nugget, 0F);
        item(rows, ":301", NtmItems.BILLET_THORIUM_FUEL, HazardRegistry.thf * HazardRegistry.billet, 0F);
        item(rows, ":302", NtmItems.INGOT_THORIUM_FUEL, HazardRegistry.thf * HazardRegistry.ingot, 0F);
        item(rows, ":303", NtmBlocks.BLOCK_THORIUM_FUEL, HazardRegistry.thf * HazardRegistry.block, 0F);
        item(rows, ":305", NtmItems.NUGGET_NEPTUNIUM_FUEL, HazardRegistry.npf * HazardRegistry.nugget, 0F);
        item(rows, ":306", NtmItems.BILLET_NEPTUNIUM_FUEL, HazardRegistry.npf * HazardRegistry.billet, 0F);
        item(rows, ":307", NtmItems.INGOT_NEPTUNIUM_FUEL, HazardRegistry.npf * HazardRegistry.ingot, 0F);
        item(rows, ":309", NtmItems.NUGGET_MOX_FUEL, HazardRegistry.mox * HazardRegistry.nugget, 0F);
        item(rows, ":310", NtmItems.BILLET_MOX_FUEL, HazardRegistry.mox * HazardRegistry.billet, 0F);
        item(rows, ":311", NtmItems.INGOT_MOX_FUEL, HazardRegistry.mox * HazardRegistry.ingot, 0F);
        item(rows, ":312", NtmBlocks.BLOCK_MOX_FUEL, HazardRegistry.mox * HazardRegistry.block, 0F);
        item(rows, ":314", NtmItems.NUGGET_AMERICIUM_FUEL, HazardRegistry.amf * HazardRegistry.nugget, 0F);
        item(rows, ":315", NtmItems.BILLET_AMERICIUM_FUEL, HazardRegistry.amf * HazardRegistry.billet, 0F);
        item(rows, ":316", NtmItems.INGOT_AMERICIUM_FUEL, HazardRegistry.amf * HazardRegistry.ingot, 0F);
        item(rows, ":318", NtmItems.NUGGET_SCHRABIDIUM_FUEL, HazardRegistry.saf * HazardRegistry.nugget, 5F * HazardRegistry.nugget);
        item(rows, ":319", NtmItems.BILLET_SCHRABIDIUM_FUEL, HazardRegistry.saf * HazardRegistry.billet, 5F * HazardRegistry.billet);
        item(rows, ":320", NtmItems.INGOT_SCHRABIDIUM_FUEL, HazardRegistry.saf * HazardRegistry.ingot, 5F * HazardRegistry.ingot);
        item(rows, ":321", NtmBlocks.BLOCK_SCHRABIDIUM_FUEL, HazardRegistry.saf * HazardRegistry.block, 5F * HazardRegistry.block);
        item(rows, ":323", NtmItems.NUGGET_HES, HazardRegistry.saf * HazardRegistry.nugget, 0F);
        item(rows, ":324", NtmItems.BILLET_HES, HazardRegistry.saf * HazardRegistry.billet, 0F);
        item(rows, ":325", NtmItems.INGOT_HES, HazardRegistry.saf * HazardRegistry.ingot, 0F);
        item(rows, ":327", NtmItems.NUGGET_LES, HazardRegistry.saf * HazardRegistry.nugget, 0F);
        item(rows, ":328", NtmItems.BILLET_LES, HazardRegistry.saf * HazardRegistry.billet, 0F);
        item(rows, ":329", NtmItems.INGOT_LES, HazardRegistry.saf * HazardRegistry.ingot, 0F);
        item(rows, ":473", NtmItems.POWDER_YELLOWCAKE, HazardRegistry.yc * HazardRegistry.powder, 0F);
        item(rows, ":474", NtmBlocks.BLOCK_YELLOWCAKE, HazardRegistry.yc * HazardRegistry.block * HazardRegistry.powder_mult, 0F);
        return rows;
    }

    private static Mat mat(List<Expectation> rows, String name, float rad, float hot, float blinding, float hydro) {
        return new Mat(rows, name, rad, hot, blinding, hydro);
    }

    private static void item(List<Expectation> rows, String name, ItemLike item, float rad, float blinding) {
        rows.add(new Expectation(name + " " + BuiltInRegistries.ITEM.getKey(item.asItem()).getPath(), new ItemStack(item), rad, 0F, blinding, 0F));
    }

    /** One DictFrame: the shape methods add a row per item, with every hazard level multiplied by the original's shape constant. */
    private static final class Mat {
        private final List<Expectation> rows;
        private final String name;
        private final float rad, hot, blinding, hydro;

        Mat(List<Expectation> rows, String name, float rad, float hot, float blinding, float hydro) {
            this.rows = rows;
            this.name = name;
            this.rad = rad;
            this.hot = hot;
            this.blinding = blinding;
            this.hydro = hydro;
        }

        Mat nugget(ItemLike... items) { return shape(HazardRegistry.nugget, items); }
        Mat billet(ItemLike... items) { return shape(HazardRegistry.billet, items); }
        Mat ingot(ItemLike... items) { return shape(HazardRegistry.ingot, items); }
        Mat dustSmall(ItemLike... items) { return shape(HazardRegistry.powder_tiny, items); }
        Mat dust(ItemLike... items) { return shape(HazardRegistry.powder, items); }
        Mat plate(ItemLike... items) { return shape(HazardRegistry.plate, items); }
        Mat block(ItemLike... items) { return shape(HazardRegistry.block, items); }

        Mat ingotStack(ItemStack... stacks) {
            for(ItemStack stack : stacks) add(HazardRegistry.ingot, stack);
            return this;
        }

        private Mat shape(float mult, ItemLike... items) {
            for(ItemLike item : items) add(mult, new ItemStack(item));
            return this;
        }

        private void add(float mult, ItemStack stack) {
            String id = BuiltInRegistries.ITEM.getKey(stack.getItem()).getPath() + (stack.getItem() == NtmItems.INGOT_RAW.get() ? "#" + MetaHelper.getMeta(stack) : "");
            rows.add(new Expectation(name + " " + id, stack, rad * mult, hot * mult, blinding * mult, hydro * mult));
        }
    }

    // Helpers

    private static void checkLevel(ItemStack stack, HazardTypeBase type, float expected, String label) {
        float actual = HazardSystem.getHazardLevelFromStack(stack, type);
        check(Math.abs(actual - expected) <= 1e-6F * Math.max(1F, expected), label + " level is " + actual + ", expected " + expected);
    }

    /** The stack has exactly the listed (type, level) pairs, compared exactly, and every other type is 0. */
    private static void checkExact(String label, ItemStack stack, Object... pairs) {
        verifyLevels(label, stack, 0F, pairs);
    }

    /** Like {@link #checkExact} with a relative tolerance, for levels that pass through a modifier (the ZIRNOX rod). */
    private static void checkClose(String label, ItemStack stack, Object... pairs) {
        verifyLevels(label, stack, 1e-5F, pairs);
    }

    private static void verifyLevels(String label, ItemStack stack, float tolerance, Object[] pairs) {
        check(pairs.length % 2 == 0, label + ": malformed expectation");
        int expectedEntries = 0;
        for(HazardTypeBase type : ALL_TYPES) {
            float expected = 0F;
            for(int i = 0; i < pairs.length; i += 2) if(pairs[i] == type) expected = (Float) pairs[i + 1];
            if(expected != 0F) expectedEntries++;
            float actual = HazardSystem.getHazardLevelFromStack(stack, type);
            check(Math.abs(actual - expected) <= tolerance * Math.abs(expected), label + ": " + type.getClass().getSimpleName() + " level is " + actual + ", expected " + expected);
        }
        int entries = HazardSystem.getHazardsFromStack(stack).size();
        check(entries == expectedEntries, label + " has " + entries + " hazard entries, expected " + expectedEntries);
    }

    private static ItemLike registered(String id, boolean required) {
        ResourceLocation location = ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, id);
        if(!BuiltInRegistries.ITEM.containsKey(location)) {
            check(!required, id + " is not registered");
            return Items.AIR;
        }
        return BuiltInRegistries.ITEM.get(location);
    }

    private static void requireHazardConfig() {
        check(NtmConfig.COMMON.ENABLE_CONTAMINATION.get(), "contamination is disabled in the common config; the radiation tests need it");
        check(!NtmConfig.COMMON.DISABLE_HOT.get(), "hot hazards are disabled in the common config");
        check(!NtmConfig.COMMON.DISABLE_BLINDING.get(), "blinding hazards are disabled in the common config");
    }

    private static Pig pig(GameTestHelper helper, List<Entity> spawned) {
        Pig pig = helper.spawn(EntityType.PIG, new Vec3(8.5, 1, 8.5));
        pig.setNoAi(true);
        spawned.add(pig);
        return pig;
    }

    private static void cleanUp(List<Entity> spawned) {
        for(Entity entity : spawned) if(!entity.isRemoved()) entity.discard();
    }

    private static void done(GameTestHelper helper, String name) {
        LOGGER.info("[hbm-hazard] {} passed", name);
        helper.succeed();
    }
}
