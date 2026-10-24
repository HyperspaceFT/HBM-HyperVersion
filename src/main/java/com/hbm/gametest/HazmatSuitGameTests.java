package com.hbm.gametest;

import api.hbm.item.IGasMask;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.hbm.config.NtmConfig;
import com.hbm.extprop.HbmLivingAttachments;
import com.hbm.handler.HazmatRegistry;
import com.hbm.hazard.HazardRegistry;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.recipes.AssemblyMachineRecipes;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.items.NtmItems;
import com.hbm.items.armor.HazmatArmorItem;
import com.hbm.items.armor.HazmatHelmetItem;
import com.hbm.lib.ModEffect;
import com.hbm.main.NuclearTechMod;
import com.hbm.registry.NtmArmorMaterials;
import com.hbm.util.ArmorRegistry;
import com.hbm.util.ArmorRegistry.HazardClass;
import com.hbm.util.ArmorUtil;
import com.hbm.util.ContaminationUtil;
import com.hbm.util.ContaminationUtil.ContaminationType;
import com.hbm.util.ContaminationUtil.HazardType;
import com.hbm.util.ShadyUtil;
import com.hbm.util.TagsUtil;
import com.mojang.authlib.GameProfile;
import com.mojang.logging.LogUtils;
import net.minecraft.core.Holder;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.ItemTags;
import net.minecraft.tags.TagKey;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.animal.Pig;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.item.ArmorItem;
import net.minecraft.world.item.ArmorMaterial;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.crafting.CraftingInput;
import net.minecraft.world.item.crafting.CraftingRecipe;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.RecipeManager;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.item.enchantment.Enchantment;
import net.minecraft.world.item.enchantment.Enchantments;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.ItemLike;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.common.util.FakePlayer;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import org.slf4j.Logger;

import java.io.File;
import java.io.IOException;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal26C, the hazmat suits: the three tiers (yellow hazmat_*, red hazmat_*_red, grey hazmat_*_grey), the three
 * hazmat cloths, the HazmatRegistry default table, ArmorUtil.checkForHazmat / checkArmor, the HAZMAT contamination branch, the helmet
 * filters and the armor enchantability tags. Same template and conventions as {@link GasMaskGameTests} and {@link RadiationControlGameTests};
 * every test has its own batch.
 * <p>
 * Expected values come from the ORIGINAL, cited beside each group of checks (HazmatRegistry.java:34-37,56-58,68-81,110-111,128-136,201-218,
 * 221-262; ArmorUtil.java:57-59,82-94,122-135; ContaminationUtil.java:34-44,265-300; MainRegistry.java:132-134,293-295; ModItems.java:2394-2396,
 * 4253-4265; ArmorHazmat.java:18-30; ArmorHazmatMask.java:20-94; ArmorRecipes.java:122-133; CraftingManager.java:101-102;
 * AssemblyMachineRecipes.java:118-119), not from the NEO implementation. The enchantability checks follow the main-agent decision recorded in
 * build/migration/goal26c/main-notes.md (decision 1) and the 1.21.1 vanilla enchantment definitions.
 * <p>
 * Real items: every suit piece, cloth, mask and filter is the registered production item. Players: a NeoForge {@link FakePlayer} (a
 * ServerPlayer that is not added to the level) whose game mode and tickCount are set explicitly by each test, because contaminate() returns
 * early for creative / spectator players and for tickCount below 200. Pigs for the LivingEntity paths.
 * Not evidence: the client (worn models, ModelM65 on the red and grey hoods, the overlay_hazmat draw, tooltips as drawn), real players over a
 * network, enchanting tables and anvils as used in game, saved worlds, a custom hbmRadResist.json at startup, and the 1.7.10 game itself.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class HazmatSuitGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-hazmat]";

    // Original HazmatRegistry.java:34-37 part factors (helmet, chest, legs, boots) and :56-58 suit values (yellow, red, grey)
    private static final double[] PART = { 0.2D, 0.4D, 0.3D, 0.1D };
    private static final double[] SUIT = { 0.6D, 1.0D, 2D };
    private static final String[] TIER = { "yellow", "red", "grey" };
    private static final EquipmentSlot[] SLOTS = { EquipmentSlot.HEAD, EquipmentSlot.CHEST, EquipmentSlot.LEGS, EquipmentSlot.FEET };
    // Float tolerance: getResistance(Player) sums floats of doubles (HazmatRegistry.java:201-218), so a full set is within a few ulps of the value
    private static final float RES_TOL = 1e-5F;

    private static Item[][] sets() {
        return new Item[][] {
                { NtmItems.HAZMAT_HELMET.get(), NtmItems.HAZMAT_PLATE.get(), NtmItems.HAZMAT_LEGS.get(), NtmItems.HAZMAT_BOOTS.get() },
                { NtmItems.HAZMAT_HELMET_RED.get(), NtmItems.HAZMAT_PLATE_RED.get(), NtmItems.HAZMAT_LEGS_RED.get(), NtmItems.HAZMAT_BOOTS_RED.get() },
                { NtmItems.HAZMAT_HELMET_GREY.get(), NtmItems.HAZMAT_PLATE_GREY.get(), NtmItems.HAZMAT_LEGS_GREY.get(), NtmItems.HAZMAT_BOOTS_GREY.get() } };
    }

    private static Item[] cloths() {
        return new Item[] { NtmItems.HAZMAT_CLOTH.get(), NtmItems.HAZMAT_CLOTH_RED.get(), NtmItems.HAZMAT_CLOTH_GREY.get() };
    }

    // 1. Radiation resistance (HazmatRegistry.java:56-58,68-81 rows hazX * part, :110-111 gas_mask 0.07 / gas_mask_m65 0.095, :128-136 iron and gold
    // 0.0225 * part, :201-218 getResistance(player) sums the four armor slots plus 0.2 for RADX; ContaminationUtil.java:34-44 mod = 10^-resistance)
    @GameTest(template = TEMPLATE, batch = "hazmat_radiation_resistance", timeoutTicks = 100)
    public static void radiation_resistance(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            FakePlayer player = fakePlayer(helper);
            check(!player.getUUID().toString().equals(ShadyUtil.Pu_238), "the FakePlayer has the Pu-238 UUID bonus");
            Item[][] sets = sets();

            // Per item, exactly the original double expression.
            for(int t = 0; t < 3; t++) {
                for(int i = 0; i < 4; i++) {
                    double expected = SUIT[t] * PART[i];
                    double actual = HazmatRegistry.getResistance(level, new ItemStack(sets[t][i]));
                    check(actual == expected, name(sets[t][i]) + " resistance " + actual + ", expected " + expected + " (" + SUIT[t] + " * " + PART[i] + ")");
                }
            }
            check(HazmatRegistry.getResistance(level, new ItemStack(NtmItems.GAS_MASK.get())) == 0.07D, "gas_mask resistance " + HazmatRegistry.getResistance(level, new ItemStack(NtmItems.GAS_MASK.get())));
            check(HazmatRegistry.getResistance(level, new ItemStack(NtmItems.GAS_MASK_M65.get())) == 0.095D, "gas_mask_m65 resistance " + HazmatRegistry.getResistance(level, new ItemStack(NtmItems.GAS_MASK_M65.get())));
            // No row in the original for the cloths and the other masks.
            for(Item none : new Item[] { NtmItems.HAZMAT_CLOTH.get(), NtmItems.HAZMAT_CLOTH_RED.get(), NtmItems.HAZMAT_CLOTH_GREY.get(), NtmItems.GAS_MASK_MONO.get(),
                    NtmItems.GAS_MASK_OLDE.get(), NtmItems.MASK_RAG.get(), NtmItems.MASK_PISS.get() }) {
                check(HazmatRegistry.getResistance(level, new ItemStack(none)) == 0D, name(none) + " has resistance " + HazmatRegistry.getResistance(level, new ItemStack(none)));
            }

            // Full sets on the player: 0.6 / 1.0 / 2.0, mod 10^-0.6 = 0.2512 / 0.1 / 0.01.
            for(int t = 0; t < 3; t++) {
                wear(player, sets[t]);
                float res = HazmatRegistry.getResistance(player);
                float mod = ContaminationUtil.calculateRadiationMod(player);
                double wantMod = Math.pow(10D, -SUIT[t]);
                LOGGER.info("{} radiation_resistance: full {} resistance {} mod {}", TAG, TIER[t], res, mod);
                check(Math.abs(res - SUIT[t]) <= RES_TOL, "full " + TIER[t] + " resistance " + res + ", expected " + SUIT[t]);
                check(Math.abs(mod - wantMod) <= wantMod * 1e-4, "full " + TIER[t] + " radiation mod " + mod + ", expected " + wantMod);
            }
            check(Math.abs(Math.pow(10D, -0.6D) - 0.2512D) < 1e-4, "10^-0.6 is not 0.2512");

            // Only the yellow chestplate: 0.6 * 0.4 = 0.24.
            strip(player);
            player.setItemSlot(EquipmentSlot.CHEST, new ItemStack(NtmItems.HAZMAT_PLATE.get()));
            check(Math.abs(HazmatRegistry.getResistance(player) - 0.24F) <= RES_TOL, "only the yellow chestplate: " + HazmatRegistry.getResistance(player) + ", expected 0.24");

            // The masks alone.
            strip(player);
            player.setItemSlot(EquipmentSlot.HEAD, new ItemStack(NtmItems.GAS_MASK.get()));
            check(Math.abs(HazmatRegistry.getResistance(player) - 0.07F) <= RES_TOL, "gas_mask alone: " + HazmatRegistry.getResistance(player) + ", expected 0.07");
            player.setItemSlot(EquipmentSlot.HEAD, new ItemStack(NtmItems.GAS_MASK_M65.get()));
            check(Math.abs(HazmatRegistry.getResistance(player) - 0.095F) <= RES_TOL, "gas_mask_m65 alone: " + HazmatRegistry.getResistance(player) + ", expected 0.095");

            // The yellow helmet and gas_mask share the HEAD slot: right-clicking a gas_mask (not sneaking, no filter) while wearing the full yellow set
            // swaps the two through ArmorItem.use, so the helmet returns to the hand and only one of them counts: 0.07 + 0.24 + 0.18 + 0.06 = 0.55.
            check(((ArmorItem) NtmItems.HAZMAT_HELMET.get()).getEquipmentSlot() == EquipmentSlot.HEAD && ((ArmorItem) NtmItems.GAS_MASK.get()).getEquipmentSlot() == EquipmentSlot.HEAD,
                    "the yellow helmet and gas_mask are not both HEAD items");
            wear(player, sets[0]);
            player.setShiftKeyDown(false);
            player.setItemInHand(InteractionHand.MAIN_HAND, new ItemStack(NtmItems.GAS_MASK.get()));
            use(player, InteractionHand.MAIN_HAND);
            check(player.getItemBySlot(EquipmentSlot.HEAD).is(NtmItems.GAS_MASK.get()), "after using a gas_mask the head holds " + player.getItemBySlot(EquipmentSlot.HEAD));
            check(player.getItemInHand(InteractionHand.MAIN_HAND).is(NtmItems.HAZMAT_HELMET.get()), "after using a gas_mask the hand holds " + player.getItemInHand(InteractionHand.MAIN_HAND) + ", expected the yellow helmet");
            float swapped = HazmatRegistry.getResistance(player);
            check(Math.abs(swapped - 0.55F) <= RES_TOL, "gas_mask + yellow plate/legs/boots: " + swapped + ", expected 0.55 (the helmet's 0.12 no longer counts)");
            LOGGER.info("{} radiation_resistance: the yellow helmet and gas_mask cannot be worn together; after the swap the resistance is {}", TAG, swapped);
            player.setItemInHand(InteractionHand.MAIN_HAND, ItemStack.EMPTY);

            // RADX adds 0.2 (HazmatRegistry.java:213-214).
            wear(player, sets[0]);
            player.addEffect(new MobEffectInstance(ModEffect.RADX, 200));
            check(player.hasEffect(ModEffect.RADX), "the RADX effect was not applied");
            check(Math.abs(HazmatRegistry.getResistance(player) - 0.8F) <= RES_TOL, "full yellow + RADX: " + HazmatRegistry.getResistance(player) + ", expected 0.8");
            player.removeEffect(ModEffect.RADX);
            check(Math.abs(HazmatRegistry.getResistance(player) - 0.6F) <= RES_TOL, "full yellow after removing RADX: " + HazmatRegistry.getResistance(player));

            // Iron and gold unchanged: 0.0225 * part, a full set 0.0225.
            Item[][] vanilla = { { Items.IRON_HELMET, Items.IRON_CHESTPLATE, Items.IRON_LEGGINGS, Items.IRON_BOOTS },
                    { Items.GOLDEN_HELMET, Items.GOLDEN_CHESTPLATE, Items.GOLDEN_LEGGINGS, Items.GOLDEN_BOOTS } };
            for(Item[] set : vanilla) {
                for(int i = 0; i < 4; i++) {
                    double expected = 0.0225D * PART[i];
                    double actual = HazmatRegistry.getResistance(level, new ItemStack(set[i]));
                    check(actual == expected, name(set[i]) + " resistance " + actual + ", expected " + expected);
                }
                wear(player, set);
                check(Math.abs(HazmatRegistry.getResistance(player) - 0.0225F) <= RES_TOL, name(set[0]) + " set: " + HazmatRegistry.getResistance(player) + ", expected 0.0225");
            }
            strip(player);
            check(HazmatRegistry.getResistance(player) == 0F && ContaminationUtil.calculateRadiationMod(player) == 1F, "no armor: resistance " + HazmatRegistry.getResistance(player));
        }).run();
        done(helper, "radiation_resistance");
    }

    // 2. contaminate (ContaminationUtil.java:265-300): radEnv first (:267-270); for players the type switch, HAZMAT -> checkForHazmat (:276-282),
    // BEFORE the creative exemption (:284-285, every type but NONE / DIGAMMA2) and the ticksExisted < 200 check (:287-288); then the dose
    // amount * (RAD_BYPASS ? 1 : 10^-resistance) (:295). FARADAY / HAZMAT_HEAVY / DIGAMMA have no migrated armor: they must behave as CREATIVE.
    @GameTest(template = TEMPLATE, batch = "hazmat_contamination", timeoutTicks = 100)
    public static void contamination(GameTestHelper helper) {
        List<Entity> spawned = new ArrayList<>();
        try {
            guard(() -> {
                check(NtmConfig.COMMON.ENABLE_CONTAMINATION.get(), "contamination is disabled in the common config; the dose checks need it");
                FakePlayer player = fakePlayer(helper);
                check(!ContaminationUtil.isRadImmune(player), "the FakePlayer is radiation immune");
                // Explicit: survival and tickCount 200, so neither early return of contaminate() applies.
                player.setGameMode(GameType.SURVIVAL);
                player.tickCount = 200;
                Item[][] sets = sets();

                // Full grey, CREATIVE type: + 10^-2 = 0.01; no armor: + 1.0; RAD_BYPASS in full grey: + 1.0.
                wear(player, sets[2]);
                dose(player, ContaminationType.CREATIVE, Math.pow(10D, -2D), "full grey, CREATIVE");
                strip(player);
                dose(player, ContaminationType.CREATIVE, 1D, "no armor, CREATIVE");
                wear(player, sets[2]);
                dose(player, ContaminationType.RAD_BYPASS, 1D, "full grey, RAD_BYPASS");

                // HAZMAT: every full set blocks the dose (radEnv still rises).
                for(int t = 0; t < 3; t++) {
                    wear(player, sets[t]);
                    dose(player, ContaminationType.HAZMAT, 0D, "full " + TIER[t] + ", HAZMAT");
                }
                // One piece missing: the dose of CREATIVE with that armor, 10^-(suit * (1 - part)).
                for(int t = 0; t < 3; t++) {
                    for(int i = 0; i < 4; i++) {
                        wear(player, sets[t]);
                        player.setItemSlot(SLOTS[i], ItemStack.EMPTY);
                        double want = Math.pow(10D, -(SUIT[t] * (1D - PART[i])));
                        float hazmat = dose(player, ContaminationType.HAZMAT, want, TIER[t] + " without " + SLOTS[i] + ", HAZMAT");
                        float creative = dose(player, ContaminationType.CREATIVE, want, TIER[t] + " without " + SLOTS[i] + ", CREATIVE");
                        check(hazmat == creative, TIER[t] + " without " + SLOTS[i] + ": HAZMAT dose " + hazmat + " differs from CREATIVE " + creative);
                    }
                }
                strip(player);
                dose(player, ContaminationType.HAZMAT, 1D, "no armor, HAZMAT");

                // FARADAY / HAZMAT_HEAVY / DIGAMMA: no armor check is wired, full yellow gives the CREATIVE dose 10^-0.6.
                wear(player, sets[0]);
                for(ContaminationType type : new ContaminationType[] { ContaminationType.FARADAY, ContaminationType.HAZMAT_HEAVY, ContaminationType.DIGAMMA }) {
                    dose(player, type, Math.pow(10D, -0.6D), "full yellow, " + type);
                }
                // A full grey set does not block them either.
                wear(player, sets[2]);
                for(ContaminationType type : new ContaminationType[] { ContaminationType.FARADAY, ContaminationType.HAZMAT_HEAVY, ContaminationType.DIGAMMA }) {
                    dose(player, type, Math.pow(10D, -2D), "full grey, " + type);
                }

                // Creative: HAZMAT without armor is still exempt (creative), so is CREATIVE; NONE is not exempt (:284).
                player.setGameMode(GameType.CREATIVE);
                check(player.isCreative(), "the FakePlayer is not creative");
                strip(player);
                dose(player, ContaminationType.HAZMAT, 0D, "creative, no armor, HAZMAT");
                dose(player, ContaminationType.CREATIVE, 0D, "creative, no armor, CREATIVE");
                dose(player, ContaminationType.NONE, 1D, "creative, no armor, NONE");
                wear(player, sets[0]);
                dose(player, ContaminationType.HAZMAT, 0D, "creative, full yellow, HAZMAT");
                player.setGameMode(GameType.SURVIVAL);

                // tickCount below 200: no dose (the condition the test sets explicitly above).
                strip(player);
                player.tickCount = 199;
                dose(player, ContaminationType.CREATIVE, 0D, "tickCount 199, no armor, CREATIVE");
                dose(player, ContaminationType.HAZMAT, 0D, "tickCount 199, no armor, HAZMAT");
                player.tickCount = 200;

                // Not a player: the switch only runs for players (:272), a pig in full yellow gets the full HAZMAT dose (mod 1 for non-players).
                Pig pig = pig(helper, spawned, new Vec3(8.5, 1, 8.5));
                check(!ContaminationUtil.isRadImmune(pig), "the pig is radiation immune");
                wear(pig, sets[0]);
                check(ArmorUtil.checkForHazmat(pig), "the pig's full yellow set is not seen");
                dose(pig, ContaminationType.HAZMAT, 1D, "pig in full yellow, HAZMAT");
                strip(pig);
                strip(player);
                HbmLivingAttachments.setRadiation(player, 0F);
                HbmLivingAttachments.setRadEnv(player, 0F);
            }).run();
        } finally {
            cleanUp(spawned);
        }
        done(helper, "contamination");
    }

    /** One contaminate(RADIATION, type, 1.0) from zero; checks the dose against want (relative 1e-4) and that radEnv rose by 1.0 in every case. */
    private static float dose(LivingEntity entity, ContaminationType type, double want, String label) {
        HbmLivingAttachments.setRadiation(entity, 0F);
        HbmLivingAttachments.setRadEnv(entity, 0F);
        ContaminationUtil.contaminate(entity, HazardType.RADIATION, type, 1.0F);
        float rad = HbmLivingAttachments.getRadiation(entity);
        float env = HbmLivingAttachments.getRadEnv(entity);
        LOGGER.info("{} contamination: {} -> radiation {} radEnv {}", TAG, label, rad, env);
        check(want == 0D ? rad == 0F : Math.abs(rad - want) <= want * 1e-4, label + ": radiation rose by " + rad + ", expected " + want);
        check(env == 1.0F, label + ": radEnv rose by " + env + ", expected 1.0 (it is incremented before every exemption)");
        HbmLivingAttachments.setRadiation(entity, 0F);
        HbmLivingAttachments.setRadEnv(entity, 0F);
        return rad;
    }

    // 3. checkForHazmat (ArmorUtil.java:122-135: a full yellow, red or grey set or the mutation effect; the schrabidium set and checkForHaz2 are not
    // migrated) and checkArmor (:82-94: armor[i] against slot 3 - i, i.e. the argument order helmet, plate, legs, boots)
    @GameTest(template = TEMPLATE, batch = "hazmat_check_for_hazmat", timeoutTicks = 100)
    public static void check_for_hazmat(GameTestHelper helper) {
        List<Entity> spawned = new ArrayList<>();
        try {
            guard(() -> {
                FakePlayer player = fakePlayer(helper);
                Item[][] sets = sets();
                strip(player);
                check(!ArmorUtil.checkForHazmat(player), "no armor counts as a hazmat set");

                for(int t = 0; t < 3; t++) {
                    Item[] set = sets[t];
                    wear(player, set);
                    check(ArmorUtil.checkForHazmat(player), "full " + TIER[t] + " is not a hazmat set");
                    check(ArmorUtil.checkArmor(player, set[0], set[1], set[2], set[3]), "checkArmor(helmet, plate, legs, boots) is false for full " + TIER[t]);
                    check(!ArmorUtil.checkArmor(player, set[3], set[2], set[1], set[0]), "checkArmor(boots, legs, plate, helmet) is true for full " + TIER[t] + " (reversed order)");
                    for(int i = 0; i < 4; i++) {
                        check(ArmorUtil.checkArmorPiece(player, set[i], SLOTS[i]), name(set[i]) + " is not seen in " + SLOTS[i]);
                        wear(player, set);
                        player.setItemSlot(SLOTS[i], ItemStack.EMPTY);
                        check(!ArmorUtil.checkForHazmat(player), TIER[t] + " without " + SLOTS[i] + " counts as a hazmat set");
                    }
                    // The helmet in the chest slot and the plate in the head slot.
                    wear(player, set);
                    player.setItemSlot(EquipmentSlot.HEAD, new ItemStack(set[1]));
                    player.setItemSlot(EquipmentSlot.CHEST, new ItemStack(set[0]));
                    check(!ArmorUtil.checkForHazmat(player), TIER[t] + " with helmet and plate swapped counts as a hazmat set");
                }

                // Mixed tiers, each position.
                for(int a = 0; a < 3; a++) {
                    for(int b = 0; b < 3; b++) {
                        if(a == b) continue;
                        for(int i = 0; i < 4; i++) {
                            wear(player, sets[a]);
                            player.setItemSlot(SLOTS[i], new ItemStack(sets[b][i]));
                            check(!ArmorUtil.checkForHazmat(player), TIER[a] + " with the " + TIER[b] + " " + SLOTS[i] + " piece counts as a hazmat set");
                        }
                    }
                }
                // Other armor and the masks do not count.
                wear(player, new Item[] { NtmItems.GAS_MASK.get(), Items.IRON_CHESTPLATE, Items.IRON_LEGGINGS, Items.IRON_BOOTS });
                check(!ArmorUtil.checkForHazmat(player), "gas_mask + iron counts as a hazmat set");
                wear(player, new Item[] { NtmItems.GAS_MASK_M65.get(), sets[0][1], sets[0][2], sets[0][3] });
                check(!ArmorUtil.checkForHazmat(player), "gas_mask_m65 + yellow body counts as a hazmat set");

                // No armor + mutation: true; the effect removed: false.
                strip(player);
                player.addEffect(new MobEffectInstance(ModEffect.MUTATION, 200));
                check(player.hasEffect(ModEffect.MUTATION), "the mutation effect was not applied");
                check(ArmorUtil.checkForHazmat(player), "no armor + mutation is not a hazmat set");
                player.removeEffect(ModEffect.MUTATION);
                check(!ArmorUtil.checkForHazmat(player), "no armor after removing mutation is still a hazmat set");

                // LivingEntity: a pig.
                Pig pig = pig(helper, spawned, new Vec3(8.5, 1, 8.5));
                wear(pig, sets[0]);
                check(ArmorUtil.checkForHazmat(pig), "a pig in full yellow is not a hazmat set");
                check(ArmorUtil.checkArmor(pig, sets[0][0], sets[0][1], sets[0][2], sets[0][3]), "checkArmor on the pig in full yellow is false");
                pig.setItemSlot(EquipmentSlot.FEET, ItemStack.EMPTY);
                check(!ArmorUtil.checkForHazmat(pig), "a pig in yellow without boots is a hazmat set");
                strip(pig);
                pig.addEffect(new MobEffectInstance(ModEffect.MUTATION, 200));
                check(ArmorUtil.checkForHazmat(pig), "a pig with mutation is not a hazmat set");
                pig.removeEffect(ModEffect.MUTATION);
                strip(player);
            }).run();
        } finally {
            cleanUp(spawned);
        }
        done(helper, "check_for_hazmat");
    }

    // 4. Helmet filters (ArmorUtil.java:57-59 SAND for the three hoods; ArmorHazmatMask.java:43-46 empty blacklist, :48-61 filter delegation, :70-73
    // isFilterApplicable true, :75-94 sneak use with a filter: into the inventory or dropped, else super; ArmorRegistry.java:61-99 mask classes + filter
    // classes minus the blacklist; ArmorUtil.java:39-48 filter classes)
    @GameTest(template = TEMPLATE, batch = "hazmat_helmet_filters", timeoutTicks = 100)
    public static void helmet_filters(GameTestHelper helper) {
        List<Entity> spawned = new ArrayList<>();
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                Pig pig = pig(helper, spawned, new Vec3(8.5, 1, 8.5));
                Item filter = NtmItems.GAS_MASK_FILTER.get(), combo = NtmItems.GAS_MASK_FILTER_COMBO.get();
                Item[] hoods = { NtmItems.HAZMAT_HELMET.get(), NtmItems.HAZMAT_HELMET_RED.get(), NtmItems.HAZMAT_HELMET_GREY.get() };

                for(Item hood : hoods) {
                    List<HazardClass> registered = ArmorRegistry.hazardClasses.get(hood);
                    check(registered != null && registered.equals(List.of(HazardClass.SAND)), name(hood) + " is registered with " + registered + ", expected [SAND]");
                    check(hood instanceof IGasMask, name(hood) + " is not an IGasMask");
                    IGasMask mask = (IGasMask) hood;
                    List<HazardClass> black = mask.getBlacklist(new ItemStack(hood), pig);
                    check(black.isEmpty(), name(hood) + " blacklist is " + black + ", expected empty");
                    check(mask.isFilterApplicable(new ItemStack(hood), pig, new ItemStack(filter)), name(hood) + " refuses gas_mask_filter");
                    check(mask.isFilterApplicable(new ItemStack(hood), pig, new ItemStack(NtmItems.GAS_MASK_FILTER_RAG.get())), name(hood) + " refuses gas_mask_filter_rag");

                    worn(pig, hood, null, HazardClass.SAND);
                    // BLISTERING included: the blacklist is empty.
                    worn(pig, hood, filter, HazardClass.SAND, HazardClass.PARTICLE_COARSE, HazardClass.PARTICLE_FINE, HazardClass.GAS_LUNG, HazardClass.GAS_BLISTERING, HazardClass.BACTERIA);
                    worn(pig, hood, combo, HazardClass.SAND, HazardClass.PARTICLE_COARSE, HazardClass.PARTICLE_FINE, HazardClass.GAS_LUNG, HazardClass.GAS_BLISTERING, HazardClass.BACTERIA, HazardClass.GAS_MONOXIDE);
                }

                // Asbestos on the pig in the yellow hood + filter (HazardTypeAsbestos: PARTICLE_FINE -> damageGasMaskFilter(entity, (int) level), else
                // asbestos + min(level, 10)), called through HazardRegistry.ASBESTOS.onUpdate as HazardSystem does per item.
                check(!NtmConfig.COMMON.DISABLE_ASBESTOS.get(), "asbestos is disabled in the common config");
                ItemStack asbestos = new ItemStack(NtmItems.INGOT_ASBESTOS.get());
                ItemStack fitted = new ItemStack(hoods[0]);
                ((IGasMask) hoods[0]).installFilter(fitted, pig, new ItemStack(filter));
                pig.setItemSlot(EquipmentSlot.HEAD, fitted);
                HbmLivingAttachments.setAsbestos(pig, 0);
                HazardRegistry.ASBESTOS.onUpdate(pig, 3F, asbestos);
                check(HbmLivingAttachments.getAsbestos(pig) == 0, "asbestos rose to " + HbmLivingAttachments.getAsbestos(pig) + " under the yellow hood + gas_mask_filter");
                ItemStack worn = ArmorUtil.getGasMaskFilter(level, pig.getItemBySlot(EquipmentSlot.HEAD));
                check(worn.is(filter) && worn.getDamageValue() == 3, "asbestos level 3 left the filter at " + worn + " damage " + worn.getDamageValue() + ", expected 3");
                // The empty hood gives SAND only: exposed.
                pig.setItemSlot(EquipmentSlot.HEAD, new ItemStack(hoods[0]));
                HazardRegistry.ASBESTOS.onUpdate(pig, 3F, asbestos);
                check(HbmLivingAttachments.getAsbestos(pig) == 3, "asbestos under the empty yellow hood gave " + HbmLivingAttachments.getAsbestos(pig) + ", expected 3");
                HbmLivingAttachments.setAsbestos(pig, 0);
                // IGasMask.damageFilter on the hood (delegation).
                ItemStack red = new ItemStack(hoods[1]);
                ((IGasMask) hoods[1]).installFilter(red, pig, new ItemStack(filter));
                ((IGasMask) hoods[1]).damageFilter(red, pig, 11);
                check(((IGasMask) hoods[1]).getFilter(red, pig).getDamageValue() == 11, "damageFilter on the red hood gave " + ((IGasMask) hoods[1]).getFilter(red, pig).getDamageValue());
                strip(pig);

                // Install by GasMaskFilterItem.use on a worn hood and sneak-use removal, through the server's useItem.
                FakePlayer player = fakePlayer(helper);
                InteractionHand hand = InteractionHand.MAIN_HAND;
                for(Item hood : hoods) {
                    player.getInventory().clearContent();
                    player.setShiftKeyDown(false);
                    player.setItemSlot(EquipmentSlot.HEAD, new ItemStack(hood));
                    ItemStack f = new ItemStack(filter);
                    f.setDamageValue(321);
                    player.setItemInHand(hand, f);
                    use(player, hand);
                    ItemStack installed = ArmorUtil.getGasMaskFilter(level, player.getItemBySlot(EquipmentSlot.HEAD));
                    check(installed.is(filter) && installed.getDamageValue() == 321, name(hood) + ": the worn hood holds " + installed + " damage " + installed.getDamageValue());
                    check(player.getItemInHand(hand).isEmpty(), name(hood) + ": after the install the hand holds " + player.getItemInHand(hand));

                    // Take the hood into the hand and sneak-use: the filter goes to the inventory, nothing is equipped.
                    ItemStack hoodStack = player.getItemBySlot(EquipmentSlot.HEAD).copy();
                    player.setItemSlot(EquipmentSlot.HEAD, ItemStack.EMPTY);
                    player.setItemInHand(hand, hoodStack);
                    player.setShiftKeyDown(true);
                    use(player, hand);
                    ItemStack held = player.getItemInHand(hand);
                    check(held.is(hood) && !TagsUtil.getCustomData(held).contains(ArmorUtil.FILTER_KEY), name(hood) + ": after the sneak use the hand holds " + held + " " + TagsUtil.getCustomData(held));
                    check(player.getItemBySlot(EquipmentSlot.HEAD).isEmpty(), name(hood) + ": the sneak use with a filter equipped the hood");
                    ItemStack given = find(player, filter);
                    check(given.is(filter) && given.getDamageValue() == 321, name(hood) + ": the inventory has " + given + ", expected the filter at 321");

                    // Without a filter the sneak use falls through to ArmorItem.use: the hood is equipped.
                    player.getInventory().clearContent();
                    player.setItemInHand(hand, new ItemStack(hood));
                    use(player, hand);
                    check(player.getItemBySlot(EquipmentSlot.HEAD).is(hood) && player.getItemInHand(hand).isEmpty(), name(hood) + ": without a filter the sneak use did not equip the hood, head " + player.getItemBySlot(EquipmentSlot.HEAD));
                    player.setItemSlot(EquipmentSlot.HEAD, ItemStack.EMPTY);
                }

                // Full inventory: the filter is dropped near the player.
                AABB box = new AABB(player.blockPosition()).inflate(4);
                for(Item mask : new Item[] { hoods[2], NtmItems.GAS_MASK.get() }) {
                    player.getInventory().clearContent();
                    player.setShiftKeyDown(true);
                    ItemStack m = new ItemStack(mask);
                    ItemStack f = new ItemStack(NtmItems.GAS_MASK_FILTER_MONO.get());
                    f.setDamageValue(9);
                    ArmorUtil.installGasMaskFilter(level, m, f);
                    player.setItemInHand(hand, m);
                    for(int i = 0; i < player.getInventory().items.size(); i++) {
                        if(i != player.getInventory().selected) player.getInventory().items.set(i, new ItemStack(Items.COBBLESTONE, 64));
                    }
                    use(player, hand);
                    List<ItemEntity> drops = level.getEntitiesOfClass(ItemEntity.class, box, e -> !e.isRemoved() && e.getItem().is(NtmItems.GAS_MASK_FILTER_MONO.get()));
                    spawned.addAll(level.getEntitiesOfClass(ItemEntity.class, box));
                    check(drops.size() == 1 && drops.get(0).getItem().getDamageValue() == 9, name(mask) + " full inventory: " + drops.size() + " dropped filters");
                    check(!TagsUtil.getCustomData(player.getItemInHand(hand)).contains(ArmorUtil.FILTER_KEY), name(mask) + " full inventory: the mask kept its filter");
                    for(ItemEntity drop : drops) drop.discard();
                }

                // 26B regression: gas_mask sneak-remove into the inventory through the shared helper.
                player.getInventory().clearContent();
                ItemStack gm = new ItemStack(NtmItems.GAS_MASK.get());
                ArmorUtil.installGasMaskFilter(level, gm, new ItemStack(filter));
                player.setItemInHand(hand, gm);
                use(player, hand);
                check(player.getItemInHand(hand).is(NtmItems.GAS_MASK.get()) && !TagsUtil.getCustomData(player.getItemInHand(hand)).contains(ArmorUtil.FILTER_KEY), "gas_mask sneak use kept the filter");
                check(find(player, filter).is(filter), "gas_mask sneak use: the filter is not in the inventory");
                check(player.getItemBySlot(EquipmentSlot.HEAD).isEmpty(), "gas_mask sneak use with a filter equipped the mask");
                player.setShiftKeyDown(false);
                player.getInventory().clearContent();
            }).run();
        } finally {
            cleanUp(spawned);
        }
        done(helper, "helmet_filters");
    }

    private static ItemStack find(FakePlayer player, Item item) {
        for(int i = 0; i < player.getInventory().getContainerSize(); i++) {
            if(player.getInventory().getItem(i).is(item)) return player.getInventory().getItem(i);
        }
        return ItemStack.EMPTY;
    }

    private static void worn(Pig pig, Item mask, Item filter, HazardClass... expected) {
        ItemStack stack = new ItemStack(mask);
        if(filter != null) ((IGasMask) mask).installFilter(stack, pig, new ItemStack(filter));
        pig.setItemSlot(EquipmentSlot.HEAD, stack);
        String label = name(mask) + (filter == null ? " without a filter" : " + " + name(filter));
        List<HazardClass> prot = ArmorRegistry.getProtectionFromItem(pig.getItemBySlot(EquipmentSlot.HEAD), pig);
        Set<HazardClass> want = EnumSet.copyOf(Arrays.asList(expected));
        Set<HazardClass> got = prot.isEmpty() ? EnumSet.noneOf(HazardClass.class) : EnumSet.copyOf(prot);
        LOGGER.info("{} {}: {}", TAG, label, prot);
        check(got.equals(want), label + " protects against " + got + ", expected " + want);
        for(HazardClass clazz : HazardClass.values()) {
            check(ArmorRegistry.hasProtection(pig, EquipmentSlot.HEAD, clazz) == want.contains(clazz), label + ": hasProtection(" + clazz + ") is " + !want.contains(clazz));
        }
        pig.setItemSlot(EquipmentSlot.HEAD, ItemStack.EMPTY);
    }

    // 5. The default table and the config contract (HazmatRegistry.java:34-37,56-58,68-81,110-111,128-136 rows; :221-239 registerHazmats: initDefault,
    // then the template when hbmRadResist.json is missing, else the whole table replaced by the file; :241-262 writeDefault comment and entries).
    // ENTRIES and writeDefault are private: both are read through reflection; the live table is only read, never modified.
    @GameTest(template = TEMPLATE, batch = "hazmat_config_table", timeoutTicks = 100)
    public static void config_table(GameTestHelper helper) {
        List<File> files = new ArrayList<>();
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                Map<Item, Double> expected = expectedTable();
                check(expected.size() == 22, "the expected table has " + expected.size() + " rows");

                Map<Item, Double> live = liveTable();
                LOGGER.info("{} config_table: the live table has {} rows", TAG, live.size());
                check(live.size() == 22, "the live table has " + live.size() + " rows, expected 22 (iron 4, gold 4, suits 12, masks 2)");
                for(Map.Entry<Item, Double> e : expected.entrySet()) {
                    Double v = live.get(e.getKey());
                    check(v != null && v.doubleValue() == e.getValue(), name(e.getKey()) + " is " + v + " in the live table, expected " + e.getValue());
                }
                check(live.equals(expected), "the live table has other rows: " + live);

                // writeDefault into a temp file: the original comment and all 22 rows.
                File template = file(files, "template");
                invokeWriteDefault(template);
                assertTemplate(template, expected, "writeDefault(temp)");

                // The template the server wrote at startup (registerHazmats, no hbmRadResist.json in the run directory).
                File config = new File(NuclearTechMod.configHbmDir, "hbmRadResist.json");
                File startup = new File(NuclearTechMod.configHbmDir, "_hbmRadResist.json");
                check(!config.exists(), "a custom hbmRadResist.json exists in " + NuclearTechMod.configHbmDir + "; the live table would be the file's, not the defaults");
                check(startup.exists(), "registerHazmats wrote no _hbmRadResist.json at startup");
                assertTemplate(startup, expected, "the startup _hbmRadResist.json");

                // readConfig of a custom 2-row file returns exactly those 2 rows (whole-table replacement in registerHazmats installs only them).
                File custom = file(files, "custom");
                write(custom, "{\"entries\":[{\"item\":\"hbmsntm:hazmat_helmet\",\"resistance\":0.5},{\"item\":\"minecraft:iron_boots\",\"resistance\":0.25}]}");
                HashMap<Item, Double> conf = HazmatRegistry.readConfig(custom);
                check(conf != null && conf.size() == 2, "readConfig of the 2-row file gave " + conf);
                check(conf.get(NtmItems.HAZMAT_HELMET.get()) == 0.5D && conf.get(Items.IRON_BOOTS) == 0.25D, "readConfig of the 2-row file gave " + conf);
                check(liveTable().equals(expected), "readConfig changed the live table");
                check(HazmatRegistry.getResistance(level, new ItemStack(NtmItems.HAZMAT_HELMET.get())) == 0.6D * 0.2D, "the live hazmat_helmet resistance changed after readConfig");
            }).run();
        } finally {
            for(File f : files) if(f.exists()) f.delete();
        }
        done(helper, "config_table");
    }

    private static Map<Item, Double> expectedTable() {
        Map<Item, Double> map = new HashMap<>();
        double iron = 0.0225D, gold = 0.0225D;
        Item[] ironSet = { Items.IRON_HELMET, Items.IRON_CHESTPLATE, Items.IRON_LEGGINGS, Items.IRON_BOOTS };
        Item[] goldSet = { Items.GOLDEN_HELMET, Items.GOLDEN_CHESTPLATE, Items.GOLDEN_LEGGINGS, Items.GOLDEN_BOOTS };
        Item[][] sets = sets();
        for(int i = 0; i < 4; i++) {
            map.put(ironSet[i], iron * PART[i]);
            map.put(goldSet[i], gold * PART[i]);
            for(int t = 0; t < 3; t++) map.put(sets[t][i], SUIT[t] * PART[i]);
        }
        map.put(NtmItems.GAS_MASK.get(), 0.07D);
        map.put(NtmItems.GAS_MASK_M65.get(), 0.095D);
        return map;
    }

    @SuppressWarnings("unchecked")
    private static Map<Item, Double> liveTable() {
        try {
            Field field = HazmatRegistry.class.getDeclaredField("ENTRIES");
            field.setAccessible(true);
            return new HashMap<>((Map<Item, Double>) field.get(null));
        } catch(ReflectiveOperationException e) {
            throw new IllegalStateException("cannot read HazmatRegistry.ENTRIES: " + e);
        }
    }

    private static void invokeWriteDefault(File file) {
        try {
            Method method = HazmatRegistry.class.getDeclaredMethod("writeDefault", File.class);
            method.setAccessible(true);
            method.invoke(null, file);
        } catch(ReflectiveOperationException e) {
            throw new IllegalStateException("cannot call HazmatRegistry.writeDefault: " + e);
        }
    }

    private static void assertTemplate(File file, Map<Item, Double> expected, String label) {
        JsonObject json;
        try {
            json = JsonParser.parseString(Files.readString(file.toPath(), StandardCharsets.UTF_8)).getAsJsonObject();
        } catch(IOException e) {
            throw new IllegalStateException("cannot read " + file + ": " + e);
        }
        check(json.has("comment") && json.get("comment").getAsString().equals("Template file, remove the underscore ('_') from the name to enable the config."),
                label + ": the comment is " + json.get("comment"));
        JsonArray entries = json.getAsJsonArray("entries");
        check(entries != null && entries.size() == expected.size(), label + ": " + (entries == null ? "no" : entries.size()) + " entries, expected " + expected.size());
        Map<Item, Double> read = new HashMap<>();
        for(JsonElement element : entries) {
            JsonObject o = element.getAsJsonObject();
            ResourceLocation id = ResourceLocation.parse(o.get("item").getAsString());
            check(BuiltInRegistries.ITEM.containsKey(id), label + ": unknown item " + id);
            read.put(BuiltInRegistries.ITEM.get(id), o.get("resistance").getAsDouble());
        }
        check(read.equals(expected), label + ": the entries are " + read + ", expected " + expected);
        LOGGER.info("{} config_table: {} has the comment and {} entries", TAG, label, entries.size());
    }

    private static File file(List<File> files, String name) {
        File dir = NuclearTechMod.configHbmDir;
        dir.mkdirs();
        File f = new File(dir, "goal26c-test-" + name + ".json");
        files.add(f);
        return f;
    }

    private static void write(File file, String content) {
        try {
            Files.writeString(file.toPath(), content, StandardCharsets.UTF_8);
        } catch(IOException e) {
            throw new IllegalStateException("cannot write the test file " + file + ": " + e);
        }
    }

    // 6. Recipes through the RecipeManager (ArmorRecipes.java:122-133, CraftingManager.java:101-102), the assembly row (AssemblyMachineRecipes.java:118-119:
    // setup(50, 100), PB.dust() x4 + string x8 -> hazmat_cloth x4), the materials (MainRegistry.java:132-134: 60, {2,5,4,1} helmet..boots, enchantability 5;
    // :293-295 repair cloths), durability 60 x {11,16,15,13} = 660 / 960 / 900 / 780, plain cloth stacks (ModItems.java:2394-2396) and the worn textures
    // (ModItems.java:4253-4265; ArmorHazmatMask.java:31-41 ModelM65 for red and grey; ArmorHazmat.java:29-30 overlay only for hazmat_helmet)
    @GameTest(template = TEMPLATE, batch = "hazmat_recipes_and_durability", timeoutTicks = 100)
    public static void recipes_and_durability(GameTestHelper helper) {
        guard(() -> {
            Item[][] sets = sets();
            Item[] cloths = cloths();
            ItemStack pane = s(Items.GLASS_PANE), ironPlate = s(NtmItems.PLATE_IRON.get());
            String[] yellowHelmet = { "EEE", "EIE", " P " }, tierHelmet = { "EEE", "IEI", "EFE" };
            String[] plate = { "E E", "EEE", "EEE" }, legs = { "EEE", "E E", "E E" }, boots = { "E E", "E E" };
            for(int t = 0; t < 3; t++) {
                ItemStack cloth = s(cloths[t]);
                if(t == 0) crafts(helper, "hazmat_helmet", shaped(yellowHelmet, Map.of('E', cloth, 'I', pane, 'P', ironPlate)), sets[t][0]);
                else crafts(helper, name(sets[t][0]), shaped(tierHelmet, Map.of('E', cloth, 'I', pane, 'F', ironPlate)), sets[t][0]);
                crafts(helper, name(sets[t][1]), shaped(plate, Map.of('E', cloth)), sets[t][1]);
                crafts(helper, name(sets[t][2]), shaped(legs, Map.of('E', cloth)), sets[t][2]);
                crafts(helper, name(sets[t][3]), shaped(boots, Map.of('E', cloth)), sets[t][3]);
            }
            // Another pane colour (KEY_ANYPANE).
            crafts(helper, "hazmat_helmet with a red pane", shaped(yellowHelmet, Map.of('E', s(cloths[0]), 'I', s(Items.RED_STAINED_GLASS_PANE), 'P', ironPlate)), sets[0][0]);
            crafts(helper, "hazmat_cloth_red", shaped(new String[] { "C", "R", "C" }, Map.of('C', s(cloths[0]), 'R', s(Items.REDSTONE))), cloths[1]);
            for(Item rubber : new Item[] { NtmItems.INGOT_RUBBER.get(), NtmItems.INGOT_BIORUBBER.get() }) {
                crafts(helper, "hazmat_cloth_grey with " + name(rubber), shaped(new String[] { " P ", "ICI", " L " }, Map.of('P', ironPlate, 'I', s(rubber), 'C', s(cloths[1]), 'L', s(NtmItems.PLATE_LEAD.get()))), cloths[2]);
            }
            // Negatives.
            notCrafting(helper, "hazmat_helmet_red from yellow cloth", shaped(tierHelmet, Map.of('E', s(cloths[0]), 'I', pane, 'F', ironPlate)), sets[1][0]);
            notCrafting(helper, "hazmat_cloth_grey with an iron plate for the lead plate", shaped(new String[] { " P ", "ICI", " L " },
                    Map.of('P', ironPlate, 'I', s(NtmItems.INGOT_RUBBER.get()), 'C', s(cloths[1]), 'L', ironPlate)), cloths[2]);
            notCrafting(helper, "hazmat_cloth_grey from yellow cloth", shaped(new String[] { " P ", "ICI", " L " },
                    Map.of('P', ironPlate, 'I', s(NtmItems.INGOT_RUBBER.get()), 'C', s(cloths[0]), 'L', s(NtmItems.PLATE_LEAD.get()))), cloths[2]);
            notCrafting(helper, "hazmat_helmet with glass blocks", shaped(yellowHelmet, Map.of('E', s(cloths[0]), 'I', s(Items.GLASS), 'P', ironPlate)), sets[0][0]);

            // ass.hazcloth
            GenericRecipe r = AssemblyMachineRecipes.INSTANCE.recipeNameMap.get("ass.hazcloth");
            check(r != null, "ass.hazcloth is not registered");
            check(r.duration == 50 && r.power == 100L, "ass.hazcloth takes " + r.duration + " ticks at " + r.power + ", expected 50 / 100");
            check(r.outputItem != null && r.outputItem.length == 1, "ass.hazcloth outputs " + Arrays.toString(r.outputItem));
            ItemStack out = r.outputItem[0].getSingle();
            check(out.is(cloths[0]) && out.getCount() == 4, "ass.hazcloth output is " + out + ", expected 4 hazmat_cloth");
            check(r.inputItem != null && r.inputItem.length == 2, "ass.hazcloth inputs " + Arrays.toString(r.inputItem));
            ItemStack[] want = { new ItemStack(NtmItems.POWDER_LEAD.get(), 4), new ItemStack(Items.STRING, 8) };
            for(int i = 0; i < 2; i++) {
                AStack in = r.inputItem[i];
                check(in.stacksize == want[i].getCount(), "ass.hazcloth input " + i + " count " + in.stacksize + ", expected " + want[i].getCount());
                check(in.matchesRecipe(want[i], true), "ass.hazcloth input " + i + " " + in + " does not match " + want[i]);
            }
            check(r.inputItem[0] instanceof ComparableStack c0 && c0.item == NtmItems.POWDER_LEAD.get(), "ass.hazcloth input 0 is " + r.inputItem[0]);
            check(!r.inputItem[0].matchesRecipe(new ItemStack(NtmItems.POWDER_COAL.get(), 4), true), "ass.hazcloth input 0 accepts coal dust");
            check(AssemblyMachineRecipes.INSTANCE.recipeNameMap.containsKey("ass.filtercoal"), "ass.filtercoal disappeared");
            LOGGER.info("{} recipes_and_durability: ass.hazcloth {} ticks / {} HE, 4 lead dust, 8 string -> 4 hazmat_cloth", TAG, r.duration, r.power);

            // Items, materials, durability, defense, textures.
            String[] ids = { "hazmat_cloth", "hazmat_cloth_red", "hazmat_cloth_grey", "hazmat_helmet", "hazmat_plate", "hazmat_legs", "hazmat_boots",
                    "hazmat_helmet_red", "hazmat_plate_red", "hazmat_legs_red", "hazmat_boots_red", "hazmat_helmet_grey", "hazmat_plate_grey",
                    "hazmat_legs_grey", "hazmat_boots_grey" };
            for(String id : ids) check(BuiltInRegistries.ITEM.containsKey(id(id)), id + " is not registered");
            List<Holder<ArmorMaterial>> materials = List.of(NtmArmorMaterials.HAZMAT, NtmArmorMaterials.HAZMAT_RED, NtmArmorMaterials.HAZMAT_GREY);
            String[] materialIds = { "hazmat", "hazmat_red", "hazmat_grey" };
            int[] durability = { 660, 960, 900, 780 };
            int[] defense = { 2, 5, 4, 1 };
            ArmorItem.Type[] types = { ArmorItem.Type.HELMET, ArmorItem.Type.CHESTPLATE, ArmorItem.Type.LEGGINGS, ArmorItem.Type.BOOTS };
            for(int t = 0; t < 3; t++) {
                ArmorMaterial material = materials.get(t).value();
                ResourceLocation key = BuiltInRegistries.ARMOR_MATERIAL.getKey(material);
                check(id(materialIds[t]).equals(key), materialIds[t] + " is registered as " + key);
                check(material.enchantmentValue() == 5 && material.toughness() == 0F && material.knockbackResistance() == 0F,
                        materialIds[t] + " enchant/toughness/knockback " + material.enchantmentValue() + "/" + material.toughness() + "/" + material.knockbackResistance());
                for(int i = 0; i < 4; i++) {
                    check(material.getDefense(types[i]) == defense[i], materialIds[t] + " defense " + types[i] + " is " + material.getDefense(types[i]) + ", expected " + defense[i]);
                    Item item = sets[t][i];
                    ItemStack stack = new ItemStack(item);
                    ArmorItem armorItem = (ArmorItem) item;
                    check(armorItem.getMaterial().value() == material, name(item) + " is not made of " + materialIds[t]);
                    check(armorItem.getType() == types[i] && armorItem.getEquipmentSlot() == SLOTS[i], name(item) + " is a " + armorItem.getType());
                    check(stack.getMaxDamage() == durability[i], name(item) + " max damage " + stack.getMaxDamage() + ", expected " + durability[i]);
                    check(stack.getMaxStackSize() == 1, name(item) + " stack size " + stack.getMaxStackSize());
                    check(armor(stack, SLOTS[i]) == defense[i], name(item) + " armor " + armor(stack, SLOTS[i]) + ", expected " + defense[i]);
                    check(item instanceof HazmatArmorItem, name(item) + " is not a HazmatArmorItem");
                    check((i == 0) == (item instanceof IGasMask) && (i == 0) == (item instanceof HazmatHelmetItem), name(item) + ": IGasMask only for the helmet");
                    check(item.isValidRepairItem(stack, s(cloths[t])), name(item) + " is not repaired with " + name(cloths[t]));
                    check(!item.isValidRepairItem(stack, s(cloths[(t + 1) % 3])), name(item) + " is repaired with " + name(cloths[(t + 1) % 3]));
                }
            }
            for(Item cloth : cloths) {
                ItemStack stack = new ItemStack(cloth);
                check(stack.getMaxStackSize() == 64 && !stack.isDamageableItem(), name(cloth) + " stack " + stack.getMaxStackSize() + ", damageable " + stack.isDamageableItem());
            }
            String[][] textures = {
                    { "textures/armor/hazmat_1.png", "textures/armor/hazmat_1.png", "textures/armor/hazmat_2.png", "textures/armor/hazmat_1.png" },
                    { "textures/models/model_haz_red.png", "textures/armor/hazmat_1_red.png", "textures/armor/hazmat_2_red.png", "textures/armor/hazmat_1_red.png" },
                    { "textures/models/model_haz_grey.png", "textures/armor/hazmat_1_grey.png", "textures/armor/hazmat_2_grey.png", "textures/armor/hazmat_1_grey.png" } };
            for(int t = 0; t < 3; t++) {
                for(int i = 0; i < 4; i++) {
                    Item item = sets[t][i];
                    ResourceLocation tex = item.getArmorTexture(new ItemStack(item), null, SLOTS[i], null, i == 2);
                    check(id(textures[t][i]).equals(tex), name(item) + " worn texture is " + tex + ", expected " + id(textures[t][i]));
                }
                HazmatHelmetItem hood = (HazmatHelmetItem) sets[t][0];
                check(hood.isM65Model() == (t != 0), name(hood) + " m65 model " + hood.isM65Model());
                ResourceLocation overlay = hood.getOverlay();
                check(t == 0 ? id("textures/misc/overlay_hazmat.png").equals(overlay) : overlay == null, name(hood) + " overlay " + overlay);
            }
        }).run();
        done(helper, "recipes_and_durability");
    }

    private static double armor(ItemStack stack, EquipmentSlot slot) {
        double[] sum = new double[1];
        stack.forEachModifier(slot, (attribute, modifier) -> {
            if(attribute.value() == Attributes.ARMOR.value()) sum[0] += modifier.amount();
        });
        return sum[0];
    }

    // 7. Enchantability (main-notes decision 1: the 18 items by slot in minecraft:enchantable/{head,chest,leg,foot}_armor + enchantable/durability +
    // enchantable/equippable, NOT in minecraft:head_armor etc. / trimmable_armor; values follow the materials, original MainRegistry.java:132-134 hazmat 5,
    // ModItemsArmor.java:22-32 masks ArmorMaterial.IRON 9 and HBM_RAGS 0; vanilla 1.21.1 enchantment definitions for supported items)
    @GameTest(template = TEMPLATE, batch = "hazmat_enchantability", timeoutTicks = 100)
    public static void enchantability(GameTestHelper helper) {
        guard(() -> {
            HolderLookup.RegistryLookup<Enchantment> enchantments = helper.getLevel().registryAccess().lookupOrThrow(Registries.ENCHANTMENT);
            Item[][] sets = sets();
            List<Item> heads = new ArrayList<>(List.of(NtmItems.GAS_MASK.get(), NtmItems.GAS_MASK_M65.get(), NtmItems.GAS_MASK_MONO.get(), NtmItems.GAS_MASK_OLDE.get(),
                    NtmItems.MASK_RAG.get(), NtmItems.MASK_PISS.get()));
            List<Item> chests = new ArrayList<>(), legs = new ArrayList<>(), feet = new ArrayList<>();
            for(Item[] set : sets) {
                heads.add(set[0]);
                chests.add(set[1]);
                legs.add(set[2]);
                feet.add(set[3]);
            }
            List<List<Item>> bySlot = List.of(heads, chests, legs, feet);
            List<TagKey<Item>> slotTags = List.of(ItemTags.HEAD_ARMOR_ENCHANTABLE, ItemTags.CHEST_ARMOR_ENCHANTABLE, ItemTags.LEG_ARMOR_ENCHANTABLE, ItemTags.FOOT_ARMOR_ENCHANTABLE);
            List<TagKey<Item>> vanillaArmorTags = List.of(ItemTags.HEAD_ARMOR, ItemTags.CHEST_ARMOR, ItemTags.LEG_ARMOR, ItemTags.FOOT_ARMOR, ItemTags.TRIMMABLE_ARMOR);
            List<ResourceKey<Enchantment>> everyPiece = List.of(Enchantments.PROTECTION, Enchantments.UNBREAKING, Enchantments.MENDING, Enchantments.BINDING_CURSE, Enchantments.VANISHING_CURSE);

            int checked = 0;
            for(int s = 0; s < 4; s++) {
                for(Item item : bySlot.get(s)) {
                    ItemStack stack = new ItemStack(item);
                    for(int o = 0; o < 4; o++) {
                        check(stack.is(slotTags.get(o)) == (o == s), name(item) + " in " + slotTags.get(o).location() + " is " + stack.is(slotTags.get(o)));
                    }
                    check(stack.is(ItemTags.ARMOR_ENCHANTABLE), name(item) + " is not in enchantable/armor");
                    check(stack.is(ItemTags.DURABILITY_ENCHANTABLE), name(item) + " is not in enchantable/durability");
                    check(stack.is(ItemTags.EQUIPPABLE_ENCHANTABLE), name(item) + " is not in enchantable/equippable");
                    check(stack.is(ItemTags.VANISHING_ENCHANTABLE), name(item) + " is not in enchantable/vanishing");
                    for(TagKey<Item> tag : vanillaArmorTags) check(!stack.is(tag), name(item) + " is in " + tag.location() + " (decision: no vanilla armor / trim tags)");
                    check(stack.isEnchantable(), name(item) + " is not enchantable (stack 1 with max damage)");

                    for(ResourceKey<Enchantment> key : everyPiece) accepts(enchantments, key, stack, true);
                    accepts(enchantments, Enchantments.RESPIRATION, stack, s == 0);
                    accepts(enchantments, Enchantments.AQUA_AFFINITY, stack, s == 0);
                    accepts(enchantments, Enchantments.SWIFT_SNEAK, stack, s == 2);
                    accepts(enchantments, Enchantments.FEATHER_FALLING, stack, s == 3);
                    check(enchantments.getOrThrow(Enchantments.PROTECTION).value().isPrimaryItem(stack), name(item) + " is not a primary item for protection (enchanting table)");
                    checked++;
                }
            }
            check(checked == 18, checked + " items checked, expected 18");

            // Enchantment values: iron masks 9, suits 5, rag masks 0.
            for(Item mask : new Item[] { NtmItems.GAS_MASK.get(), NtmItems.GAS_MASK_M65.get(), NtmItems.GAS_MASK_MONO.get(), NtmItems.GAS_MASK_OLDE.get() }) {
                check(mask.getEnchantmentValue() == 9, name(mask) + " enchantment value " + mask.getEnchantmentValue() + ", expected 9");
            }
            for(Item[] set : sets) for(Item item : set) check(item.getEnchantmentValue() == 5, name(item) + " enchantment value " + item.getEnchantmentValue() + ", expected 5");
            for(Item rag : new Item[] { NtmItems.MASK_RAG.get(), NtmItems.MASK_PISS.get() }) {
                check(rag.getEnchantmentValue() == 0, name(rag) + " enchantment value " + rag.getEnchantmentValue() + ", expected 0");
            }

            // Vanilla iron armor unchanged.
            Item[] iron = { Items.IRON_HELMET, Items.IRON_CHESTPLATE, Items.IRON_LEGGINGS, Items.IRON_BOOTS };
            List<TagKey<Item>> vanillaSlot = List.of(ItemTags.HEAD_ARMOR, ItemTags.CHEST_ARMOR, ItemTags.LEG_ARMOR, ItemTags.FOOT_ARMOR);
            for(int i = 0; i < 4; i++) {
                ItemStack stack = new ItemStack(iron[i]);
                check(stack.is(vanillaSlot.get(i)) && stack.is(slotTags.get(i)) && stack.is(ItemTags.TRIMMABLE_ARMOR), name(iron[i]) + " lost a vanilla tag");
                check(iron[i].getEnchantmentValue() == 9, name(iron[i]) + " enchantment value " + iron[i].getEnchantmentValue());
                accepts(enchantments, Enchantments.PROTECTION, stack, true);
            }

            // no9 stays untagged (main-notes decision 1).
            ItemStack no9 = new ItemStack(NtmItems.NO9.get());
            for(TagKey<Item> tag : List.of(ItemTags.HEAD_ARMOR_ENCHANTABLE, ItemTags.DURABILITY_ENCHANTABLE, ItemTags.EQUIPPABLE_ENCHANTABLE, ItemTags.HEAD_ARMOR, ItemTags.TRIMMABLE_ARMOR)) {
                check(!no9.is(tag), "no9 is in " + tag.location());
            }
            accepts(enchantments, Enchantments.PROTECTION, no9, false);
            LOGGER.info("{} enchantability: 18 items checked against their slot tags and 9 enchantments; no9 untagged", TAG);
        }).run();
        done(helper, "enchantability");
    }

    private static void accepts(HolderLookup.RegistryLookup<Enchantment> enchantments, ResourceKey<Enchantment> key, ItemStack stack, boolean want) {
        Enchantment enchantment = enchantments.getOrThrow(key).value();
        check(enchantment.canEnchant(stack) == want, key.location() + ".canEnchant(" + name(stack.getItem()) + ") is " + !want);
        check(enchantment.isSupportedItem(stack) == want, key.location() + ".isSupportedItem(" + name(stack.getItem()) + ") is " + !want);
    }

    // Helpers

    private static void wear(LivingEntity entity, Item[] set) {
        for(int i = 0; i < 4; i++) entity.setItemSlot(SLOTS[i], set[i] == null ? ItemStack.EMPTY : new ItemStack(set[i]));
    }

    private static void strip(LivingEntity entity) {
        for(EquipmentSlot slot : SLOTS) entity.setItemSlot(slot, ItemStack.EMPTY);
    }

    private static String name(Item item) {
        return BuiltInRegistries.ITEM.getKey(item).getPath();
    }

    private static FakePlayer fakePlayer(GameTestHelper helper) {
        FakePlayer player = new FakePlayer(helper.getLevel(), new GameProfile(UUID.randomUUID(), "hazmat-suit-test"));
        Vec3 abs = helper.absoluteVec(new Vec3(8.5, 1, 8.5));
        player.moveTo(abs.x, abs.y, abs.z, 0F, 0F);
        player.getInventory().selected = 0;
        // Explicit survival: the GameTest level's own default game mode is not relied on.
        player.setGameMode(GameType.SURVIVAL);
        return player;
    }

    /** The server's own right-click dispatch, which writes the returned stack into the hand as the game does. */
    private static void use(FakePlayer player, InteractionHand hand) {
        player.gameMode.useItem(player, player.serverLevel(), player.getItemInHand(hand), hand);
    }

    private static ItemStack s(ItemLike item) {
        return new ItemStack(item);
    }

    private static CraftingInput shaped(String[] pattern, Map<Character, ItemStack> key) {
        int w = pattern[0].length(), h = pattern.length;
        List<ItemStack> cells = new ArrayList<>();
        for(String row : pattern) {
            check(row.length() == w, "ragged pattern row " + row);
            for(char c : row.toCharArray()) {
                if(c == ' ') {
                    cells.add(ItemStack.EMPTY);
                } else {
                    ItemStack stack = key.get(c);
                    check(stack != null, "no key for " + c);
                    cells.add(stack.copy());
                }
            }
        }
        return CraftingInput.of(w, h, cells);
    }

    private static ResourceLocation id(String path) {
        return ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path);
    }

    /** The grid must be matched by the recipe named after the output (one output each, original addRecipeAuto with count 1). */
    private static void crafts(GameTestHelper helper, String label, CraftingInput input, Item out) {
        ServerLevel level = helper.getLevel();
        RecipeManager manager = level.getRecipeManager();
        ResourceLocation recipeId = id(name(out));
        List<ResourceLocation> ids = new ArrayList<>();
        boolean found = false;
        for(RecipeHolder<CraftingRecipe> holder : manager.getRecipesFor(RecipeType.CRAFTING, input, level)) {
            ids.add(holder.id());
            if(holder.id().equals(recipeId)) {
                found = true;
                ItemStack result = holder.value().assemble(input, level.registryAccess());
                check(result.is(out) && result.getCount() == 1, label + ": " + holder.id() + " yields " + result + ", expected 1 x " + name(out));
            }
        }
        check(found, label + ": the grid is not matched by " + recipeId + ", it matches " + ids);
        Optional<RecipeHolder<CraftingRecipe>> first = manager.getRecipeFor(RecipeType.CRAFTING, input, level);
        check(first.isPresent(), label + ": getRecipeFor found nothing");
        ItemStack result = first.get().value().assemble(input, level.registryAccess());
        check(result.is(out) && result.getCount() == 1, label + ": the first match " + first.get().id() + " yields " + result);
    }

    private static void notCrafting(GameTestHelper helper, String label, CraftingInput input, Item out) {
        ServerLevel level = helper.getLevel();
        for(RecipeHolder<CraftingRecipe> holder : level.getRecipeManager().getRecipesFor(RecipeType.CRAFTING, input, level)) {
            ItemStack result = holder.value().assemble(input, level.registryAccess());
            check(!result.is(out), label + ": " + holder.id() + " yields " + result);
        }
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

    private static void done(GameTestHelper helper, String name) {
        LOGGER.info("{} {} passed", TAG, name);
        helper.succeed();
    }
}
