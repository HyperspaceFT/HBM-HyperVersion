package com.hbm.gametest;

import com.hbm.blockentity.machine.DecontaminatorBlockEntity;
import com.hbm.blocks.NtmBlocks;
import com.hbm.config.NtmConfig;
import com.hbm.extprop.HbmLivingAttachments;
import com.hbm.extprop.HbmLivingAttachments.ContaminationEffect;
import com.hbm.handler.ArmorModHandler;
import com.hbm.handler.HazmatRegistry;
import com.hbm.handler.radiation.ChunkRadiationManager;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.RecipesCommon.TagStack;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.recipes.CrystallizerRecipes;
import com.hbm.inventory.recipes.CrystallizerRecipes.CrystallizerRecipe;
import com.hbm.items.NtmItems;
import com.hbm.items.armor.ItemModCladding;
import com.hbm.lib.ModEffect;
import com.hbm.main.NuclearTechMod;
import com.hbm.util.ArmorRegistry;
import com.hbm.util.ArmorRegistry.HazardClass;
import com.hbm.util.ArmorUtil;
import com.hbm.util.ContaminationUtil;
import com.hbm.util.TagsUtil;
import com.mojang.logging.LogUtils;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.gametest.framework.GameTestSequence;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.animal.Pig;
import net.minecraft.world.entity.item.FallingBlockEntity;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.crafting.CraftingInput;
import net.minecraft.world.item.crafting.CraftingRecipe;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.RecipeManager;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.item.crafting.SingleRecipeInput;
import net.minecraft.world.item.crafting.SmeltingRecipe;
import net.minecraft.world.level.GameRules;
import net.minecraft.world.level.ItemLike;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.FallingBlock;
import net.minecraft.world.level.block.SoundType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import org.slf4j.Logger;

import java.io.File;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal26A, the radiation control batch: the hazard-system fixes (radon gas protection branch, null mod slots,
 * removeMod, readConfig, cladding), the four radiation absorbers, the graphite block, the lead and boron sand and glass, the recipes and the
 * crystallizer coal block row, and the unchanged decontaminator. Same template and conventions as {@link HazardGameTests} and
 * {@link RBMKRecyclingGameTests}; every test has its own batch.
 * <p>
 * Expected values come from the ORIGINAL, cited beside each group of checks (BlockGasRadon.java:32-37, ArmorUtil.java:310-353,
 * ArmorRegistry.java:61-99, ArmorModHandler.java:101-119,154-177, HazmatRegistry.java:183-199,221-239,265-295, ItemModCladding.java:17,
 * BlockAbsorber.java:20-22,63-78, ModBlocks.java:1410,1641-1643,2307, ToolRecipes.java:113-116, CraftingManager.java:626-630,687-688,
 * 753-756,761,992, MineralRecipes.java:40, SmeltingRecipes.java:132-133, CrystallizerRecipes.java:56,99,314-322, TileEntityDecon.java:18-30),
 * not from the NEO implementation.
 * <p>
 * Real engine evidence: the production methods on a running dedicated GameTest server. Blocks are driven through the engine (BlockState
 * entityInside, scheduled ticks and randomTick with the real chunk radiation handler, the loot tables through Block.getDrops, falling blocks),
 * recipes through the level's RecipeManager as loaded (a CraftingInput is assembled and the result checked, not only the recipe id).
 * <p>
 * STAND-IN BOUNDARY. The registries are frozen when GameTests run, so a test cannot create a new Item, and no NEO item implements IGasMask
 * before Goal 26B. Instead of a gas mask item: (1) a vanilla helmet gets a temporary {@code ArmorRegistry.registerHazard} entry (the previous map
 * entry is restored in a finally); (2) the filter is stored on the vanilla helmet's custom data under {@code ArmorUtil.FILTER_KEY} with a
 * damageable vanilla item as the "filter" (the static filter helpers do not need IGasMask on the mask); (3) the real armor mods
 * {@code METEOR_CHARM} / {@code PROTECTION_CHARM} (ModCharmItem, slot HELMET_ONLY) go through {@code ArmorModHandler.applyMod}, and partial-mod
 * cases use hand-built {@code ntm_armor_mods} compounds. The IGasMask branches of {@code ArmorRegistry.getProtectionFromItem} and of
 * {@code ArmorUtil} (a filter on a helmet-mod gas mask) are NOT run here; the verification script covers them statically and Goal 26B adds real
 * item tests. Entities are Pigs (a Zombie is radiation immune, ContaminationUtil.isRadImmune) and, where a player would be needed, nothing:
 * no mock player is created. Not evidence: the client (tooltips, rendering of the glass cutout layer and the face culling), real players, saved
 * worlds, the 1.7.10 game itself, and the dedicated-server config file loading of hbmRadResist.json by registerHazmats.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class RadiationControlGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-radiation-control]";
    private static final float EPS = 1e-6F;

    // 1. Radon gas (BlockGasRadon.java:24-38)

    // The production entry is Block#entityInside (1.7.10 onEntityCollidedWithBlock); it is reached through BlockState.entityInside, the engine's own
    // dispatch, on a Pig. Original :32-36: hasAllProtection(HEAD, PARTICLE_FINE) -> damageGasMaskFilter(1), else contaminate(RADIATION, RAD_BYPASS,
    // 0.05F) and incrementAsbestos(1). Before the fix NEO inverted the condition (start copy GasRadonBlock.java:30), so an unprotected head damaged
    // the filter instead of contaminating.
    @GameTest(template = TEMPLATE, batch = "radcontrol_radon_unprotected", timeoutTicks = 100)
    public static void radon_unprotected(GameTestHelper helper) {
        List<Entity> spawned = new ArrayList<>();
        try {
            guard(() -> {
                requireContamination();
                check(!NtmConfig.COMMON.DISABLE_ASBESTOS.get(), "asbestos is disabled in the common config");
                ServerLevel level = helper.getLevel();
                Pig pig = pig(helper, spawned, new Vec3(8.5, 1, 8.5));
                check(!ContaminationUtil.isRadImmune(pig), "the pig is radiation immune");
                BlockPos pos = helper.absolutePos(new BlockPos(8, 1, 8));
                BlockState radon = NtmBlocks.GAS_RADON.get().defaultBlockState();

                // NEO's only real hazard registration is the diamond helmet: PARTICLE_COARSE + GAS_LUNG, no PARTICLE_FINE.
                List<HazardClass> diamond = ArmorRegistry.hazardClasses.get(Items.DIAMOND_HELMET);
                check(diamond != null && diamond.equals(List.of(HazardClass.PARTICLE_COARSE, HazardClass.GAS_LUNG)), "the diamond helmet registration is " + diamond);

                // Empty head slot.
                contaminatedByRadon(radon, level, pos, pig, ItemStack.EMPTY, "empty head slot");

                // Diamond helmet carrying a filter: the filter must stay untouched (the old inverted branch damaged it).
                ItemStack helmet = new ItemStack(Items.DIAMOND_HELMET);
                putFilter(level, helmet, new ItemStack(Items.IRON_SHOVEL));
                contaminatedByRadon(radon, level, pos, pig, helmet, "diamond helmet with a filter");
                ItemStack filter = ArmorUtil.getGasMaskFilter(level, pig.getItemBySlot(EquipmentSlot.HEAD));
                check(filter.is(Items.IRON_SHOVEL) && filter.getDamageValue() == 0, "the filter was damaged or lost: " + filter + " damage " + filter.getDamageValue());

                // Diamond helmet without a filter.
                contaminatedByRadon(radon, level, pos, pig, new ItemStack(Items.DIAMOND_HELMET), "diamond helmet without a filter");
                pig.setItemSlot(EquipmentSlot.HEAD, ItemStack.EMPTY);
            }).run();
        } finally {
            cleanUp(spawned);
        }
        done(helper, "radon_unprotected");
    }

    private static void contaminatedByRadon(BlockState radon, ServerLevel level, BlockPos pos, Pig pig, ItemStack head, String label) {
        pig.setItemSlot(EquipmentSlot.HEAD, head);
        HbmLivingAttachments.setRadiation(pig, 0F);
        HbmLivingAttachments.setRadEnv(pig, 0F);
        HbmLivingAttachments.setAsbestos(pig, 0);
        radon.entityInside(level, pos, pig);
        float rad = HbmLivingAttachments.getRadiation(pig);
        LOGGER.info("{} radon, {}: +{} rad, +{} env, asbestos {}", TAG, label, rad, HbmLivingAttachments.getRadEnv(pig), HbmLivingAttachments.getAsbestos(pig));
        // RAD_BYPASS skips the resistance calculation (ContaminationUtil.java:157): the full 0.05 arrives.
        check(Math.abs(rad - 0.05F) <= EPS, label + ": " + rad + " rad, expected 0.05");
        check(Math.abs(HbmLivingAttachments.getRadEnv(pig) - 0.05F) <= EPS, label + ": environment radiation " + HbmLivingAttachments.getRadEnv(pig) + ", expected 0.05");
        check(HbmLivingAttachments.getAsbestos(pig) == 1, label + ": asbestos " + HbmLivingAttachments.getAsbestos(pig) + ", expected 1");
    }

    // Original :32-33: a head that protects against PARTICLE_FINE only damages the filter by 1 and is not contaminated.
    @GameTest(template = TEMPLATE, batch = "radcontrol_radon_protected", timeoutTicks = 100)
    public static void radon_protected(GameTestHelper helper) {
        List<Entity> spawned = new ArrayList<>();
        Item item = Items.CHAINMAIL_HELMET;
        ArrayList<HazardClass> previous = ArmorRegistry.hazardClasses.get(item);
        try {
            guard(() -> {
                requireContamination();
                check(!NtmConfig.COMMON.DISABLE_ASBESTOS.get(), "asbestos is disabled in the common config");
                check(previous == null, "the chainmail helmet already has a hazard registration: " + previous);
                ServerLevel level = helper.getLevel();
                Pig pig = pig(helper, spawned, new Vec3(8.5, 1, 8.5));
                BlockPos pos = helper.absolutePos(new BlockPos(8, 1, 8));
                BlockState radon = NtmBlocks.GAS_RADON.get().defaultBlockState();

                ArmorRegistry.registerHazard(item, HazardClass.PARTICLE_FINE);
                ItemStack helmet = new ItemStack(item);
                putFilter(level, helmet, new ItemStack(Items.IRON_SHOVEL));
                pig.setItemSlot(EquipmentSlot.HEAD, helmet);
                check(ArmorRegistry.hasAllProtection(pig, EquipmentSlot.HEAD, HazardClass.PARTICLE_FINE), "the registered helmet does not protect");

                HbmLivingAttachments.setRadiation(pig, 0F);
                HbmLivingAttachments.setRadEnv(pig, 0F);
                HbmLivingAttachments.setAsbestos(pig, 0);
                for(int hit = 1; hit <= 3; hit++) {
                    radon.entityInside(level, pos, pig);
                    ItemStack filter = ArmorUtil.getGasMaskFilter(level, pig.getItemBySlot(EquipmentSlot.HEAD));
                    check(filter.is(Items.IRON_SHOVEL) && filter.getDamageValue() == hit, "hit " + hit + ": filter damage " + filter.getDamageValue() + ", expected " + hit);
                }
                check(HbmLivingAttachments.getRadiation(pig) == 0F, "a protected head was contaminated: " + HbmLivingAttachments.getRadiation(pig));
                check(HbmLivingAttachments.getRadEnv(pig) == 0F, "a protected head took environment radiation: " + HbmLivingAttachments.getRadEnv(pig));
                check(HbmLivingAttachments.getAsbestos(pig) == 0, "a protected head took asbestos: " + HbmLivingAttachments.getAsbestos(pig));

                // The same protection without any filter installed: still protected, nothing to damage, no exception.
                pig.setItemSlot(EquipmentSlot.HEAD, new ItemStack(item));
                radon.entityInside(level, pos, pig);
                check(HbmLivingAttachments.getRadiation(pig) == 0F && HbmLivingAttachments.getAsbestos(pig) == 0, "a protected head without a filter was contaminated");
                pig.setItemSlot(EquipmentSlot.HEAD, ItemStack.EMPTY);
            }).run();
        } finally {
            if(previous == null) ArmorRegistry.hazardClasses.remove(item); else ArmorRegistry.hazardClasses.put(item, previous);
            cleanUp(spawned);
        }
        check(ArmorRegistry.hazardClasses.get(item) == previous, "the registry entry of the chainmail helmet was not restored");
        done(helper, "radon_protected");
    }

    // 3. Filter helpers (ArmorUtil.java:310-353)

    @GameTest(template = TEMPLATE, batch = "radcontrol_filter_helpers", timeoutTicks = 100)
    public static void filter_helpers(GameTestHelper helper) {
        List<Entity> spawned = new ArrayList<>();
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                Pig pig = pig(helper, spawned, new Vec3(8.5, 1, 8.5));

                // install / get round trip
                ItemStack helmet = new ItemStack(Items.IRON_HELMET);
                ItemStack shovel = new ItemStack(Items.IRON_SHOVEL);
                check(shovel.getMaxDamage() == 250, "the iron shovel durability is " + shovel.getMaxDamage());
                check(ArmorUtil.getGasMaskFilter(level, helmet).isEmpty(), "a fresh helmet has a filter");
                putFilter(level, helmet, shovel);
                ItemStack got = ArmorUtil.getGasMaskFilter(level, helmet);
                check(got.is(Items.IRON_SHOVEL) && got.getCount() == 1 && got.getDamageValue() == 0, "get of a stored filter gave " + got);

                // damageGasMaskFilter(level, mask, n) raises the damage and accumulates (:350-352 installGasMaskFilter)
                ArmorUtil.damageGasMaskFilter(level, helmet, 5);
                check(ArmorUtil.getGasMaskFilter(level, helmet).getDamageValue() == 5, "damage 5 gave " + ArmorUtil.getGasMaskFilter(level, helmet).getDamageValue());
                ArmorUtil.damageGasMaskFilter(level, helmet, 7);
                check(ArmorUtil.getGasMaskFilter(level, helmet).getDamageValue() == 12, "damage 5 + 7 gave " + ArmorUtil.getGasMaskFilter(level, helmet).getDamageValue());

                // damage up to and including the maximum keeps the filter (:346 removes only strictly above the maximum)
                ArmorUtil.damageGasMaskFilter(level, helmet, 238);
                ItemStack atMax = ArmorUtil.getGasMaskFilter(level, helmet);
                check(atMax.is(Items.IRON_SHOVEL) && atMax.getDamageValue() == 250, "damage to exactly the maximum gave " + atMax + " damage " + atMax.getDamageValue());

                // a filter with maximum damage 0 is untouched (:344)
                ItemStack plain = new ItemStack(Items.IRON_HELMET);
                putFilter(level, plain, new ItemStack(Items.STICK));
                CompoundTag before = TagsUtil.getCustomData(plain);
                ArmorUtil.damageGasMaskFilter(level, plain, 9);
                check(TagsUtil.getCustomData(plain).equals(before), "a filter without durability changed: " + TagsUtil.getCustomData(plain));
                check(ArmorUtil.getGasMaskFilter(level, plain).is(Items.STICK), "the durability-less filter is gone");

                // damageGasMaskFilter(entity, n): empty head slot does nothing and does not throw
                pig.setItemSlot(EquipmentSlot.HEAD, ItemStack.EMPTY);
                ArmorUtil.damageGasMaskFilter(pig, 3);
                check(pig.getItemBySlot(EquipmentSlot.HEAD).isEmpty(), "an empty head slot was filled");

                // a head without a filter: nothing changes, no custom data appears
                ItemStack bare = new ItemStack(Items.IRON_HELMET);
                pig.setItemSlot(EquipmentSlot.HEAD, bare);
                ArmorUtil.damageGasMaskFilter(pig, 3);
                check(!pig.getItemBySlot(EquipmentSlot.HEAD).has(DataComponents.CUSTOM_DATA), "damaging a head without a filter created custom data");

                // a head with a filter: the entity variant damages the worn stack (:310-331)
                ItemStack worn = new ItemStack(Items.IRON_HELMET);
                putFilter(level, worn, new ItemStack(Items.IRON_SHOVEL));
                pig.setItemSlot(EquipmentSlot.HEAD, worn);
                ArmorUtil.damageGasMaskFilter(pig, 3);
                check(ArmorUtil.getGasMaskFilter(level, pig.getItemBySlot(EquipmentSlot.HEAD)).getDamageValue() == 3, "the entity variant gave damage "
                        + ArmorUtil.getGasMaskFilter(level, pig.getItemBySlot(EquipmentSlot.HEAD)).getDamageValue());

                // getGasMaskFilterRecursively: installed filter first; no filter and partial mods (only slot 5) returns EMPTY without throwing
                ItemStack recursive = ArmorUtil.getGasMaskFilterRecursively(pig.getItemBySlot(EquipmentSlot.HEAD), pig);
                check(recursive.is(Items.IRON_SHOVEL), "the recursive lookup of a filtered helmet gave " + recursive);
                ItemStack partial = modsHelmet(level, Items.IRON_HELMET, Map.of(ArmorModHandler.CLADDING, new ItemStack(NtmItems.METEOR_CHARM.get())));
                check(ArmorModHandler.hasMods(partial), "the partial-mod helmet has no mods");
                ItemStack none = ArmorUtil.getGasMaskFilterRecursively(partial, pig);
                check(none.isEmpty(), "the recursive lookup with partial mods and no filter gave " + none);
                pig.setItemSlot(EquipmentSlot.HEAD, ItemStack.EMPTY);
            }).run();
        } finally {
            cleanUp(spawned);
        }
        done(helper, "filter_helpers");
    }

    // The production install path on its own (original ArmorUtil.java:300-307 writes the filter with writeToNBT, which mutates the compound). The other
    // tests store their filters through putFilter so that they do not depend on this method.
    @GameTest(template = TEMPLATE, batch = "radcontrol_filter_install_round_trip", timeoutTicks = 100)
    public static void filter_install_round_trip(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            ItemStack helmet = new ItemStack(Items.IRON_HELMET);
            ItemStack shovel = new ItemStack(Items.IRON_SHOVEL);
            shovel.setDamageValue(17);
            ArmorUtil.installGasMaskFilter(level, helmet, shovel);
            ItemStack got = ArmorUtil.getGasMaskFilter(level, helmet);
            check(got.is(Items.IRON_SHOVEL) && got.getCount() == 1 && got.getDamageValue() == 17, "installGasMaskFilter then getGasMaskFilter gave " + got + " damage " + got.getDamageValue());
            check(TagsUtil.getCustomData(helmet).getCompound(ArmorUtil.FILTER_KEY).contains("id"), "the stored hfr_Filter compound has no item id: " + TagsUtil.getCustomData(helmet));
            ArmorUtil.removeFilter(helmet);
            check(ArmorUtil.getGasMaskFilter(level, helmet).isEmpty(), "removeFilter left a filter");
            // an empty mask or an empty filter installs nothing
            ArmorUtil.installGasMaskFilter(level, ItemStack.EMPTY, shovel);
            ItemStack bare = new ItemStack(Items.IRON_HELMET);
            ArmorUtil.installGasMaskFilter(level, bare, ItemStack.EMPTY);
            check(!bare.has(DataComponents.CUSTOM_DATA), "an empty filter created custom data");
        }).run();
        done(helper, "filter_install_round_trip");
    }

    // The production applyMod on its own (original ArmorModHandler.java:~60-80 writes the mod with writeToNBT into the slot compound).
    @GameTest(template = TEMPLATE, batch = "radcontrol_apply_mod_round_trip", timeoutTicks = 100)
    public static void apply_mod_round_trip(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            ItemStack helmet = new ItemStack(Items.DIAMOND_HELMET);
            ArmorModHandler.applyMod(level, helmet, new ItemStack(NtmItems.METEOR_CHARM.get()));
            check(ArmorModHandler.hasMods(helmet), "applyMod stored no mod compound");
            ItemStack[] mods = ArmorModHandler.pryMods(level, helmet);
            check(mods[ArmorModHandler.HELMET_ONLY].is(NtmItems.METEOR_CHARM.get()), "slot 0 holds " + mods[ArmorModHandler.HELMET_ONLY]);
            for(int i = 1; i < mods.length; i++) check(mods[i].isEmpty(), "slot " + i + " holds " + mods[i]);
            ArmorModHandler.applyMod(level, helmet, new ItemStack(NtmItems.PROTECTION_CHARM.get()));
            check(ArmorModHandler.pryMod(level, helmet, ArmorModHandler.HELMET_ONLY).is(NtmItems.PROTECTION_CHARM.get()), "applyMod does not override the present mod in the same slot");
        }).run();
        done(helper, "apply_mod_round_trip");
    }

    // Original ArmorUtil.java:349-352: filter.setItemDamage(damage + n) is not clamped in 1.7.10, and a damage strictly above the maximum calls
    // removeFilter(mask). Kept as its own test so the other filter checks stay visible when this one fails.
    @GameTest(template = TEMPLATE, batch = "radcontrol_filter_removed_above_max", timeoutTicks = 100)
    public static void filter_removed_above_max(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            ItemStack helmet = new ItemStack(Items.IRON_HELMET);
            helmet.set(DataComponents.CUSTOM_NAME, net.minecraft.network.chat.Component.literal("unrelated"));
            ItemStack shovel = new ItemStack(Items.IRON_SHOVEL);
            shovel.setDamageValue(249);
            putFilter(level, helmet, shovel);
            check(ArmorUtil.getGasMaskFilter(level, helmet).getDamageValue() == 249, "the damaged filter was not stored");

            // 249 + 1 = 250 is not above the maximum: the filter stays at its maximum damage.
            ArmorUtil.damageGasMaskFilter(level, helmet, 1);
            ItemStack stays = ArmorUtil.getGasMaskFilter(level, helmet);
            check(stays.is(Items.IRON_SHOVEL) && stays.getDamageValue() == 250, "at damage 250 of 250 the filter is " + stays + " damage " + stays.getDamageValue());

            // 250 + 1 = 251 is strictly above the maximum: removeFilter(mask).
            ArmorUtil.damageGasMaskFilter(level, helmet, 1);
            ItemStack after = ArmorUtil.getGasMaskFilter(level, helmet);
            LOGGER.info("{} filter after damage 251 of 250: {} (damage {})", TAG, after, after.getDamageValue());
            check(after.isEmpty(), "a damage strictly above the maximum must remove the filter, but the filter is still " + after + " at damage " + after.getDamageValue());
            check(!TagsUtil.getCustomData(helmet).contains(ArmorUtil.FILTER_KEY), "the filter key survived removeFilter");
        }).run();
        done(helper, "filter_removed_above_max");
    }

    // 4. Missing mod slots (ArmorModHandler.java:154-177 returns null slots, every original caller null-checks; NEO's callers call isEmpty(), so the
    // NEO pryMods fills ItemStack.EMPTY) and an unregistered item in a slot
    @GameTest(template = TEMPLATE, batch = "radcontrol_unregistered_filter_and_mods", timeoutTicks = 100)
    public static void unregistered_filter_and_mods(GameTestHelper helper) {
        List<Entity> spawned = new ArrayList<>();
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                Pig pig = pig(helper, spawned, new Vec3(8.5, 1, 8.5));
                check(!ArmorRegistry.hazardClasses.containsKey(NtmItems.METEOR_CHARM.get()), "the meteor charm has a hazard registration");

                // Only slot 5 (CLADDING) is set, with a charm stack: the other eight are absent.
                ItemStack helmet = modsHelmet(level, Items.DIAMOND_HELMET, Map.of(ArmorModHandler.CLADDING, new ItemStack(NtmItems.METEOR_CHARM.get())));
                ItemStack[] mods = ArmorModHandler.pryMods(level, helmet);
                check(mods.length == 9, "pryMods returned " + mods.length + " slots");
                for(int i = 0; i < mods.length; i++) {
                    check(mods[i] != null, "slot " + i + " is null");
                    if(i == ArmorModHandler.CLADDING) check(mods[i].is(NtmItems.METEOR_CHARM.get()), "slot 5 is " + mods[i]);
                    else check(mods[i].isEmpty(), "absent slot " + i + " is " + mods[i]);
                }
                check(ArmorModHandler.hasMods(helmet), "pryMods removed the present mod");

                // getProtectionFromItem returns the helmet's own classes (the recursion into the unregistered charm adds nothing).
                List<HazardClass> prot = ArmorRegistry.getProtectionFromItem(helmet, pig);
                check(prot.equals(List.of(HazardClass.PARTICLE_COARSE, HazardClass.GAS_LUNG)), "protection of the partial-mod helmet is " + prot);
                pig.setItemSlot(EquipmentSlot.HEAD, helmet);
                check(ArmorRegistry.hasAllProtection(pig, EquipmentSlot.HEAD, HazardClass.PARTICLE_COARSE, HazardClass.GAS_LUNG), "hasAllProtection coarse + lung is false");
                check(!ArmorRegistry.hasAllProtection(pig, EquipmentSlot.HEAD, HazardClass.PARTICLE_COARSE, HazardClass.PARTICLE_FINE), "hasAllProtection coarse + fine is true");
                check(ArmorRegistry.hasProtection(pig, EquipmentSlot.HEAD, HazardClass.GAS_LUNG), "hasProtection lung is false");
                check(!ArmorRegistry.hasProtection(pig, EquipmentSlot.HEAD, HazardClass.PARTICLE_FINE), "hasProtection fine is true");
                check(ArmorRegistry.hasAnyProtection(pig, EquipmentSlot.HEAD, HazardClass.PARTICLE_FINE, HazardClass.GAS_LUNG), "hasAnyProtection fine/lung is false");
                check(!ArmorRegistry.hasAnyProtection(pig, EquipmentSlot.HEAD, HazardClass.PARTICLE_FINE, HazardClass.BACTERIA), "hasAnyProtection fine/bacteria is true");

                // A stack without mods: nine EMPTY, no throw.
                ItemStack[] none = ArmorModHandler.pryMods(level, new ItemStack(Items.IRON_HELMET));
                check(none.length == 9, "pryMods of an unmodded stack returned " + none.length + " slots");
                for(int i = 0; i < none.length; i++) check(none[i] != null && none[i].isEmpty(), "unmodded slot " + i + " is " + none[i]);

                // A mods compound that is present but empty: nine EMPTY, the empty compound is cleaned up.
                ItemStack hollow = modsHelmet(level, Items.IRON_HELMET, Map.of());
                check(ArmorModHandler.hasMods(hollow), "the hollow helmet has no mods compound");
                ItemStack[] hollowMods = ArmorModHandler.pryMods(level, hollow);
                for(int i = 0; i < hollowMods.length; i++) check(hollowMods[i] != null && hollowMods[i].isEmpty(), "hollow slot " + i + " is " + hollowMods[i]);

                // An item id that is not registered, and an empty slot compound, next to a valid slot: both read as absent and are removed (:171-173).
                ItemStack broken = modsHelmet(level, Items.IRON_HELMET, Map.of(ArmorModHandler.CLADDING, new ItemStack(NtmItems.METEOR_CHARM.get())));
                CompoundTag tag = TagsUtil.getCustomData(broken);
                CompoundTag modTag = tag.getCompound(ArmorModHandler.MOD_COMPOUND_KEY);
                CompoundTag unknown = new CompoundTag();
                unknown.putString("id", NuclearTechMod.MODID + ":does_not_exist");
                unknown.putInt("count", 1);
                modTag.put(ArmorModHandler.MOD_SLOT_KEY + ArmorModHandler.KEVLAR, unknown);
                modTag.put(ArmorModHandler.MOD_SLOT_KEY + ArmorModHandler.SERVOS, new CompoundTag());
                tag.put(ArmorModHandler.MOD_COMPOUND_KEY, modTag);
                TagsUtil.putCustomData(broken, tag);
                ItemStack[] brokenMods = ArmorModHandler.pryMods(level, broken);
                check(brokenMods[ArmorModHandler.KEVLAR].isEmpty() && brokenMods[ArmorModHandler.SERVOS].isEmpty(), "the unknown or empty slot is not EMPTY");
                check(brokenMods[ArmorModHandler.CLADDING].is(NtmItems.METEOR_CHARM.get()), "the valid slot was lost");
                CompoundTag cleaned = TagsUtil.getCustomData(broken).getCompound(ArmorModHandler.MOD_COMPOUND_KEY);
                check(!cleaned.contains(ArmorModHandler.MOD_SLOT_KEY + ArmorModHandler.KEVLAR) && !cleaned.contains(ArmorModHandler.MOD_SLOT_KEY + ArmorModHandler.SERVOS)
                        && cleaned.contains(ArmorModHandler.MOD_SLOT_KEY + ArmorModHandler.CLADDING), "the absent slots were not cleaned up: " + cleaned);
                pig.setItemSlot(EquipmentSlot.HEAD, ItemStack.EMPTY);
            }).run();
        } finally {
            cleanUp(spawned);
        }
        done(helper, "unregistered_filter_and_mods");
    }

    // 5. removeMod (original ArmorModHandler.java:101-119: the slot is removed inside the mod compound, an empty mod compound is removed, every other NBT
    // key of the armor survives)
    @GameTest(template = TEMPLATE, batch = "radcontrol_remove_mod_keeps_data", timeoutTicks = 100)
    public static void remove_mod_keeps_data(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            ItemStack helmet = new ItemStack(Items.DIAMOND_HELMET);
            ArmorModHandler.applyMod(level, helmet, new ItemStack(NtmItems.METEOR_CHARM.get()));
            check(ArmorModHandler.pryMod(level, helmet, ArmorModHandler.HELMET_ONLY).is(NtmItems.METEOR_CHARM.get()), "applyMod did not store the charm in slot 0");

            CompoundTag tag = TagsUtil.getCustomData(helmet);
            CompoundTag filterTag;
            filterTag = (CompoundTag) new ItemStack(Items.IRON_SHOVEL).save(level.registryAccess());
            tag.put(ArmorUtil.FILTER_KEY, filterTag);
            tag.putFloat("hfr_cladding", 0.25F);
            tag.putString("unrelated", "kept");
            TagsUtil.putCustomData(helmet, tag);
            CompoundTag expectedFilter = filterTag.copy();

            ArmorModHandler.removeMod(helmet, ArmorModHandler.HELMET_ONLY);
            CompoundTag after = TagsUtil.getCustomData(helmet);
            check(!after.contains(ArmorModHandler.MOD_COMPOUND_KEY), "the emptied mod compound survived: " + after);
            check(!ArmorModHandler.hasMods(helmet), "hasMods is still true");
            check(after.contains(ArmorUtil.FILTER_KEY) && after.getCompound(ArmorUtil.FILTER_KEY).equals(expectedFilter), "hfr_Filter changed: " + after);
            check(after.getFloat("hfr_cladding") == 0.25F, "hfr_cladding changed: " + after.getFloat("hfr_cladding"));
            check("kept".equals(after.getString("unrelated")), "the unrelated key changed: " + after.getString("unrelated"));
            check(after.size() == 3, "the custom data has " + after.size() + " keys, expected 3: " + after);

            // Two mods: removing one keeps the other.
            Map<Integer, ItemStack> two = new LinkedHashMap<>();
            two.put(ArmorModHandler.HELMET_ONLY, new ItemStack(NtmItems.METEOR_CHARM.get()));
            two.put(ArmorModHandler.CLADDING, new ItemStack(NtmItems.PROTECTION_CHARM.get()));
            ItemStack both = modsHelmet(level, Items.DIAMOND_HELMET, two);
            ArmorModHandler.removeMod(both, ArmorModHandler.HELMET_ONLY);
            check(ArmorModHandler.hasMods(both), "removing one of two mods removed the compound");
            CompoundTag rest = TagsUtil.getCustomData(both).getCompound(ArmorModHandler.MOD_COMPOUND_KEY);
            check(!rest.contains(ArmorModHandler.MOD_SLOT_KEY + ArmorModHandler.HELMET_ONLY), "slot 0 survived");
            check(rest.contains(ArmorModHandler.MOD_SLOT_KEY + ArmorModHandler.CLADDING), "slot 5 was removed with slot 0");
            check(ArmorModHandler.pryMod(level, both, ArmorModHandler.CLADDING).is(NtmItems.PROTECTION_CHARM.get()), "slot 5 no longer holds the protection charm");

            // A stack without custom data gains none.
            ItemStack bare = new ItemStack(Items.DIAMOND_HELMET);
            ArmorModHandler.removeMod(bare, ArmorModHandler.HELMET_ONLY);
            check(!bare.has(DataComponents.CUSTOM_DATA), "removeMod added a CUSTOM_DATA component to a stack without one");
            ArmorModHandler.removeMod(ItemStack.EMPTY, ArmorModHandler.HELMET_ONLY);

            // NEO-only departure from 1.7.10 (which left an empty NBT compound): a stack whose only data was the last mod loses the empty component, so
            // it stacks with unmodded armor again.
            ItemStack only = new ItemStack(Items.DIAMOND_HELMET);
            ArmorModHandler.applyMod(level, only, new ItemStack(NtmItems.METEOR_CHARM.get()));
            ArmorModHandler.removeMod(only, ArmorModHandler.HELMET_ONLY);
            check(!only.has(DataComponents.CUSTOM_DATA), "removing the last mod left an empty CUSTOM_DATA component");
        }).run();
        done(helper, "remove_mod_keeps_data");
    }

    // 6. Cladding and the unchanged iron and gold resistance (HazmatRegistry.java:183-199; ItemModCladding.java:12-19 stores rad)
    @GameTest(template = TEMPLATE, batch = "radcontrol_cladding", timeoutTicks = 100)
    public static void cladding(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();

            // Mods but no cladding slot: 0, no exception.
            ItemStack helmet = new ItemStack(Items.DIAMOND_HELMET);
            ArmorModHandler.applyMod(level, helmet, new ItemStack(NtmItems.METEOR_CHARM.get()));
            check(HazmatRegistry.getCladding(level, helmet) == 0D, "a helmet with mods but no cladding has cladding " + HazmatRegistry.getCladding(level, helmet));
            // A non-cladding item in the cladding slot also gives 0.
            ItemStack wrongSlot = modsHelmet(level, Items.DIAMOND_HELMET, Map.of(ArmorModHandler.CLADDING, new ItemStack(NtmItems.PROTECTION_CHARM.get())));
            check(HazmatRegistry.getCladding(level, wrongSlot) == 0D, "a non-cladding item in the cladding slot gave " + HazmatRegistry.getCladding(level, wrongSlot));
            check(HazmatRegistry.getCladding(level, new ItemStack(Items.DIAMOND_HELMET)) == 0D, "an unmodded helmet has cladding");

            // hfr_cladding 0.25 -> 0.25 (:185-186)
            ItemStack clad = new ItemStack(Items.DIAMOND_HELMET);
            CompoundTag tag = TagsUtil.getCustomData(clad);
            tag.putFloat("hfr_cladding", 0.25F);
            TagsUtil.putCustomData(clad, tag);
            check(HazmatRegistry.getCladding(level, clad) == 0.25D, "hfr_cladding 0.25 gave " + HazmatRegistry.getCladding(level, clad));
            check(HazmatRegistry.getResistance(level, clad) == 0.25D, "the diamond helmet resistance with 0.25 cladding is " + HazmatRegistry.getResistance(level, clad));

            // Iron and gold: 0.0225 * {helmet 0.2, chest 0.4, legs 0.3, boots 0.1}, exactly as at the start (HazmatRegistry.initDefault).
            Item[][] sets = { { Items.IRON_HELMET, Items.IRON_CHESTPLATE, Items.IRON_LEGGINGS, Items.IRON_BOOTS },
                    { Items.GOLDEN_HELMET, Items.GOLDEN_CHESTPLATE, Items.GOLDEN_LEGGINGS, Items.GOLDEN_BOOTS } };
            double[] factor = { 0.2D, 0.4D, 0.3D, 0.1D };
            for(Item[] set : sets) {
                for(int i = 0; i < 4; i++) {
                    double expected = 0.0225D * factor[i];
                    double actual = HazmatRegistry.getResistance(level, new ItemStack(set[i]));
                    check(actual == expected, BuiltInRegistries.ITEM.getKey(set[i]) + " resistance is " + actual + ", expected " + expected);
                }
            }
            check(HazmatRegistry.getResistance(level, ItemStack.EMPTY) == 0D, "an empty stack has resistance");

            // ItemModCladding stores its rad (original :17). The registries are frozen, so the constructor may be refused; then the script covers it.
            ItemModCladding built = null;
            try {
                built = new ItemModCladding(new Item.Properties(), 0.1D);
            } catch(RuntimeException e) {
                LOGGER.info("{} ItemModCladding cannot be constructed after the registries froze: {}", TAG, e.toString());
            }
            if(built != null) check(built.rad == 0.1D, "the cladding rad is " + built.rad + ", expected 0.1");
            LOGGER.info("{} ItemModCladding constructed in the test: {}", TAG, built != null);
        }).run();
        done(helper, "cladding");
    }

    // 7. hbmRadResist.json reader (original HazmatRegistry.java:265-295: per-entry try, unknown items logged and skipped, the whole file in a try that
    // keeps the defaults when it fails; the caller keeps the defaults when the reader returns null)
    @GameTest(template = TEMPLATE, batch = "radcontrol_hazmat_config", timeoutTicks = 100)
    public static void hazmat_config(GameTestHelper helper) {
        List<File> files = new ArrayList<>();
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                Item[] vanilla = { Items.IRON_HELMET, Items.IRON_CHESTPLATE, Items.IRON_LEGGINGS, Items.IRON_BOOTS, Items.GOLDEN_HELMET, Items.GOLDEN_CHESTPLATE,
                        Items.GOLDEN_LEGGINGS, Items.GOLDEN_BOOTS };
                double[] live = new double[vanilla.length];
                for(int i = 0; i < vanilla.length; i++) live[i] = HazmatRegistry.getResistance(level, new ItemStack(vanilla[i]));

                // (a) an unknown item id is skipped, the known ones keep their values, no AIR key appears
                File a = write(files, "a", "{\"entries\":[{\"item\":\"minecraft:iron_helmet\",\"resistance\":0.5},"
                        + "{\"item\":\"hbmsntm:does_not_exist\",\"resistance\":1.0},{\"item\":\"minecraft:golden_helmet\",\"resistance\":0.25}]}");
                HashMap<Item, Double> mapA = HazmatRegistry.readConfig(a);
                check(mapA != null, "a valid file with an unknown id was rejected");
                check(mapA.size() == 2, "the map has " + mapA.size() + " entries, expected 2: " + mapA);
                check(mapA.get(Items.IRON_HELMET) != null && mapA.get(Items.IRON_HELMET) == 0.5D, "iron_helmet is " + mapA.get(Items.IRON_HELMET));
                check(mapA.get(Items.GOLDEN_HELMET) != null && mapA.get(Items.GOLDEN_HELMET) == 0.25D, "golden_helmet is " + mapA.get(Items.GOLDEN_HELMET));
                check(!mapA.containsKey(Items.AIR), "an unknown item id was mapped to air");
                check(a.delete(), "the reader kept the file open");

                // (b) malformed JSON, an empty file, a missing "entries" and a non-array "entries" return null without an exception
                for(String[] bad : new String[][] { { "b1", "{\"entries\":[" }, { "b2", "" }, { "b3", "{\"nothing\":[]}" }, { "b4", "{\"entries\":3}" }, { "b5", "[1,2]" } }) {
                    File file = write(files, bad[0], bad[1]);
                    check(HazmatRegistry.readConfig(file) == null, "the unreadable file " + bad[0] + " (" + bad[1] + ") did not return null");
                    check(file.delete(), "the reader kept " + bad[0] + " open");
                }

                // (c) an entry without "resistance" is skipped, the others are kept; so are an invalid resource location and an unparsable number
                File c = write(files, "c", "{\"entries\":[{\"item\":\"minecraft:iron_helmet\"},{\"item\":\"Not A Valid:ID!\",\"resistance\":1},"
                        + "{\"item\":\"minecraft:golden_helmet\",\"resistance\":0.25},{\"item\":\"minecraft:iron_boots\",\"resistance\":\"abc\"},"
                        + "{\"item\":\"minecraft:iron_leggings\",\"resistance\":0.125}]}");
                HashMap<Item, Double> mapC = HazmatRegistry.readConfig(c);
                check(mapC != null, "a file with bad entries was rejected as a whole");
                check(mapC.size() == 2 && mapC.get(Items.GOLDEN_HELMET) != null && mapC.get(Items.GOLDEN_HELMET) == 0.25D && mapC.get(Items.IRON_LEGGINGS) != null
                        && mapC.get(Items.IRON_LEGGINGS) == 0.125D, "the entries kept are " + mapC);
                check(c.delete(), "the reader kept the file c open");

                // An empty entries array is a valid file with no entries (the caller would replace the table with it).
                File empty = write(files, "d", "{\"entries\":[]}");
                HashMap<Item, Double> mapD = HazmatRegistry.readConfig(empty);
                check(mapD != null && mapD.isEmpty(), "an empty entries array gave " + mapD);
                check(empty.delete(), "the reader kept the file d open");

                // A missing file returns null.
                check(HazmatRegistry.readConfig(new File(NuclearTechMod.configHbmDir, "goal26a-test-missing.json")) == null, "a missing file did not return null");

                // readConfig does not touch the live table.
                for(int i = 0; i < vanilla.length; i++) {
                    double now = HazmatRegistry.getResistance(level, new ItemStack(vanilla[i]));
                    check(now == live[i], BuiltInRegistries.ITEM.getKey(vanilla[i]) + " live resistance changed from " + live[i] + " to " + now);
                }
            }).run();
        } finally {
            for(File file : files) if(file.exists()) file.delete();
        }
        done(helper, "hazmat_config");
    }

    // Original HazmatRegistry.java:273: `(JsonObject) element` is cast OUTSIDE the inner per-entry try, so a non-object entry fails the whole read (the
    // outer catch at :290-292) and readConfig returns null, which keeps the defaults. Its own test so the other config checks stay independent.
    @GameTest(template = TEMPLATE, batch = "radcontrol_hazmat_config_non_object_entry", timeoutTicks = 100)
    public static void hazmat_config_non_object_entry(GameTestHelper helper) {
        List<File> files = new ArrayList<>();
        try {
            guard(() -> {
                File file = write(files, "n", "{\"entries\":[1,{\"item\":\"minecraft:iron_helmet\",\"resistance\":0.5}]}");
                HashMap<Item, Double> map = HazmatRegistry.readConfig(file);
                check(map == null, "a non-object entry did not fail the whole read, the map is " + map);
                check(file.delete(), "the reader kept the file open");
                File second = write(files, "n2", "{\"entries\":[{\"item\":\"minecraft:iron_helmet\",\"resistance\":0.5},\"text\"]}");
                check(HazmatRegistry.readConfig(second) == null, "a trailing non-object entry did not fail the whole read");
                check(second.delete(), "the reader kept the file open");
            }).run();
        } finally {
            for(File file : files) if(file.exists()) file.delete();
        }
        done(helper, "hazmat_config_non_object_entry");
    }

    private static File write(List<File> files, String name, String content) {
        try {
            File dir = NuclearTechMod.configHbmDir;
            dir.mkdirs();
            File file = new File(dir, "goal26a-test-" + name + ".json");
            files.add(file);
            Files.writeString(file.toPath(), content, StandardCharsets.UTF_8);
            return file;
        } catch(java.io.IOException e) {
            throw new IllegalStateException("cannot write the test file " + name + ": " + e);
        }
    }

    // 8. Radiation absorbers (BlockAbsorber.java:22 tiers 2.5 / 10 / 100 / 10,000, :35 randomly ticking, :63-66 tickRate 10, :68-73 updateTick decrements
    // and reschedules, :75-78 onBlockAdded schedules). The chunk radiation is the real handler's (ChunkRadiationManager.proxy). Two things would
    // otherwise disturb exact values and are controlled here: ChunkRadiationManager.onServerTick runs updateSystem (spreading and decaying every chunk)
    // every 20 ticks from the private eggTimer, which the test resets to 0 on every tick through reflection and restores afterwards; and random ticks
    // are switched off (randomTickSpeed 0, restored) so that a random tick cannot add a decrement. Each phase uses its own position, because a removed
    // block leaves its scheduled tick behind and the level de-duplicates ticks per position and block.
    private static final int OBS_TICKS = 36;

    private static final class Phase {
        final String label;
        final Block block;
        final float amount;
        final float base;
        final BlockPos rel;
        final boolean directRandomTick;
        final boolean removeAfterSecond;
        BlockPos abs;
        long placed;
        long first = -1;
        boolean removed;
        final List<Long> dts = new ArrayList<>();
        final List<Float> rads = new ArrayList<>();

        Phase(String label, Block block, float amount, float base, int index, boolean directRandomTick, boolean removeAfterSecond) {
            this.label = label;
            this.block = block;
            this.amount = amount;
            this.base = base;
            this.rel = new BlockPos(1 + 2 * index, 2, 8);
            this.directRandomTick = directRandomTick;
            this.removeAfterSecond = removeAfterSecond;
        }
    }

    @GameTest(template = TEMPLATE, batch = "radcontrol_absorber_tiers", timeoutTicks = 800)
    public static void absorber_tiers(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        List<Phase> phases = new ArrayList<>();
        phases.add(new Phase("rad_absorber 2.5", NtmBlocks.RAD_ABSORBER.get(), 2.5F, 1000F, 0, false, false));
        phases.add(new Phase("rad_absorber_red 10", NtmBlocks.RAD_ABSORBER_RED.get(), 10F, 1000F, 1, false, false));
        phases.add(new Phase("rad_absorber_green 100", NtmBlocks.RAD_ABSORBER_GREEN.get(), 100F, 1000F, 2, false, false));
        phases.add(new Phase("rad_absorber_pink 10000 (clamped at 0)", NtmBlocks.RAD_ABSORBER_PINK.get(), 10000F, 1000F, 3, false, false));
        phases.add(new Phase("rad_absorber_pink 10000 from 25000", NtmBlocks.RAD_ABSORBER_PINK.get(), 10000F, 25000F, 4, false, false));
        phases.add(new Phase("rad_absorber_red with a direct randomTick", NtmBlocks.RAD_ABSORBER_RED.get(), 10F, 1000F, 5, true, false));
        phases.add(new Phase("rad_absorber_green removed after two decrements", NtmBlocks.RAD_ABSORBER_GREEN.get(), 100F, 3000F, 6, false, true));

        // Saved state, restored by the last step and by any failing step.
        int[] oldRandomTickSpeed = new int[1];
        int[] oldEggTimer = new int[1];
        Map<BlockPos, Float> oldRadiation = new LinkedHashMap<>();
        Runnable restore = () -> {
            try {
                setEggTimer(oldEggTimer[0]);
            } catch(RuntimeException | ReflectiveOperationException e) {
                LOGGER.error("{} cannot restore the eggTimer: {}", TAG, e.toString());
            }
            level.getGameRules().getRule(GameRules.RULE_RANDOMTICKING).set(oldRandomTickSpeed[0], level.getServer());
            List<Map.Entry<BlockPos, Float>> entries = new ArrayList<>(oldRadiation.entrySet());
            for(int i = entries.size() - 1; i >= 0; i--) ChunkRadiationManager.proxy.setRadiation(level, entries.get(i).getKey(), entries.get(i).getValue());
            for(Phase phase : phases) helper.setBlock(phase.rel, Blocks.AIR);
        };

        GameTestSequence sequence = helper.startSequence();
        sequence.thenExecute(restoring(restore, () -> {
            oldRandomTickSpeed[0] = level.getGameRules().getRule(GameRules.RULE_RANDOMTICKING).get();
            oldEggTimer[0] = getEggTimer();
            for(Phase phase : phases) {
                phase.abs = helper.absolutePos(phase.rel);
                oldRadiation.put(phase.abs, ChunkRadiationManager.proxy.getRadiation(level, phase.abs));
            }
            level.getGameRules().getRule(GameRules.RULE_RANDOMTICKING).set(0, level.getServer());
            check(NtmBlocks.RAD_ABSORBER.get().defaultBlockState().isRandomlyTicking(), "rad_absorber is not randomly ticking (BlockAbsorber.java:35)");
            check(NtmBlocks.RAD_ABSORBER_RED.get().defaultBlockState().isRandomlyTicking(), "rad_absorber_red is not randomly ticking");
            check(NtmBlocks.RAD_ABSORBER_GREEN.get().defaultBlockState().isRandomlyTicking(), "rad_absorber_green is not randomly ticking");
            check(NtmBlocks.RAD_ABSORBER_PINK.get().defaultBlockState().isRandomlyTicking(), "rad_absorber_pink is not randomly ticking");
            check(!Blocks.STONE.defaultBlockState().isRandomlyTicking(), "the control block stone is randomly ticking");
        }));
        for(Phase phase : phases) {
            sequence.thenExecute(restoring(restore, () -> {
                setEggTimerUnchecked(0);
                ChunkRadiationManager.proxy.setRadiation(level, phase.abs, phase.base);
                check(ChunkRadiationManager.proxy.getRadiation(level, phase.abs) == phase.base, phase.label + ": the chunk radiation could not be seeded, it is "
                        + ChunkRadiationManager.proxy.getRadiation(level, phase.abs));
                helper.setBlock(phase.rel, phase.block);
                phase.placed = level.getGameTime();
                check(level.getBlockState(phase.abs).is(phase.block), phase.label + ": the block was not placed");
                check(level.getBlockTicks().hasScheduledTick(phase.abs, phase.block), phase.label + ": onPlace scheduled no tick (BlockAbsorber.java:75-78)");
                if(phase.directRandomTick) {
                    float beforeCall = ChunkRadiationManager.proxy.getRadiation(level, phase.abs);
                    level.getBlockState(phase.abs).randomTick(level, phase.abs, level.random);
                    float afterCall = ChunkRadiationManager.proxy.getRadiation(level, phase.abs);
                    check(afterCall == drop(beforeCall, phase.amount, 1), phase.label + ": randomTick changed " + beforeCall + " to " + afterCall + ", expected one decrement of " + phase.amount);
                }
            }));
            sequence.thenExecuteFor(phase.removeAfterSecond ? 60 : OBS_TICKS, restoring(restore, () -> {
                long dt = level.getGameTime() - phase.placed;
                if(!phase.dts.isEmpty() && phase.dts.get(phase.dts.size() - 1) == dt) return;
                setEggTimerUnchecked(0);
                float rad = ChunkRadiationManager.proxy.getRadiation(level, phase.abs);
                phase.dts.add(dt);
                phase.rads.add(rad);
                if(phase.removeAfterSecond && !phase.removed && rad == drop(phase.base, phase.amount, 2)) {
                    helper.setBlock(phase.rel, Blocks.AIR);
                    phase.removed = true;
                }
            }));
            sequence.thenExecute(restoring(restore, () -> {
                evaluateAbsorber(phase);
                helper.setBlock(phase.rel, Blocks.AIR);
            }));
        }
        sequence.thenExecute(restoring(restore, () -> {
            long firstA = phases.get(0).first;
            for(Phase phase : phases) check(phase.first == firstA, phase.label + ": first decrement at " + phase.first + ", the first tier had " + firstA);
            restore.run();
            check(level.getGameRules().getRule(GameRules.RULE_RANDOMTICKING).get() == oldRandomTickSpeed[0], "randomTickSpeed was not restored");
            LOGGER.info("{} absorber_tiers: first decrement {} ticks after placement in every phase", TAG, firstA);
        }));
        sequence.thenExecute(passed("absorber_tiers"));
        sequence.thenSucceed();
    }

    /** n decrements of amount from base, each clamped at 0 (ChunkRadiationHandlerSimple.decrementRad: max(rad - amount, 0)). */
    private static float drop(float base, float amount, int n) {
        float r = base;
        for(int i = 0; i < n; i++) r = Math.max(r - amount, 0F);
        return r;
    }

    private static void evaluateAbsorber(Phase p) {
        check(p.dts.size() >= OBS_TICKS - 2, p.label + ": only " + p.dts.size() + " observations");
        float v0 = p.rads.get(0);
        float expectedV0 = p.directRandomTick ? drop(p.base, p.amount, 1) : p.base;
        check(v0 == expectedV0, p.label + ": at placement the radiation is " + v0 + ", expected " + expectedV0);
        int firstIndex = -1;
        for(int i = 0; i < p.rads.size(); i++) {
            if(p.rads.get(i) != v0) {
                firstIndex = i;
                break;
            }
        }
        check(firstIndex >= 0, p.label + ": the radiation never changed, the scheduled tick did not decrement");
        p.first = p.dts.get(firstIndex);
        // The scheduled tick is due 10 game ticks after placement (BlockAbsorber.java:64-66); depending on whether this callback runs before or after the
        // level's scheduled ticks inside a game tick, it is first seen at +10 or +11. Every later decrement is exactly 10 ticks after the previous one.
        check(p.first == 10 || p.first == 11, p.label + ": the first decrement was seen " + p.first + " ticks after placement, expected 10 (or 11)");
        int maxDrops = p.removeAfterSecond ? 2 : Integer.MAX_VALUE;
        long dropsSeen = 0;
        for(int i = 0; i < p.rads.size(); i++) {
            long dt = p.dts.get(i);
            long n = dt >= p.first ? 1 + (dt - p.first) / 10 : 0;
            n = Math.min(n, maxDrops);
            float expected = drop(v0, p.amount, (int) n);
            check(p.rads.get(i) == expected, p.label + ": at +" + dt + " ticks the radiation is " + p.rads.get(i) + ", expected " + expected + " (" + n + " decrements of " + p.amount + ")");
            dropsSeen = n;
            check(p.rads.get(i) >= 0F, p.label + ": negative radiation " + p.rads.get(i));
        }
        if(p.removeAfterSecond) {
            check(p.removed, p.label + ": the second decrement was never seen, the block was not removed");
            check(dropsSeen == 2, p.label + ": " + dropsSeen + " decrements counted");
            check(p.dts.get(p.dts.size() - 1) >= p.first + 10 + 25, p.label + ": too few ticks observed after the removal");
        } else {
            check(p.dts.get(p.dts.size() - 1) >= p.first + 20, p.label + ": fewer than three decrements fit in the window");
            check(dropsSeen >= 3, p.label + ": only " + dropsSeen + " decrements counted (accumulation)");
        }
        LOGGER.info("{} {}: first decrement +{}, final radiation {}, {} observations", TAG, p.label, p.first, p.rads.get(p.rads.size() - 1), p.dts.size());
    }

    private static Runnable restoring(Runnable restore, Runnable step) {
        return () -> {
            try {
                guard(step).run();
            } catch(Throwable t) {
                try {
                    restore.run();
                } catch(RuntimeException e) {
                    LOGGER.error("{} restore after a failure threw {}", TAG, e.toString());
                }
                throw t;
            }
        };
    }

    private static Field eggTimerField() throws ReflectiveOperationException {
        Field field = ChunkRadiationManager.class.getDeclaredField("eggTimer");
        field.setAccessible(true);
        return field;
    }

    private static int getEggTimer() {
        try {
            return eggTimerField().getInt(null);
        } catch(ReflectiveOperationException e) {
            throw new IllegalStateException("cannot read ChunkRadiationManager.eggTimer: " + e);
        }
    }

    private static void setEggTimer(int value) throws ReflectiveOperationException {
        eggTimerField().setInt(null, value);
    }

    private static void setEggTimerUnchecked(int value) {
        try {
            setEggTimer(value);
        } catch(ReflectiveOperationException e) {
            throw new IllegalStateException("cannot write ChunkRadiationManager.eggTimer: " + e);
        }
    }

    // 9. The decontaminator is unchanged and stays correct (TileEntityDecon.java:18-30: box x-0.5..x+1.5, y..y+2, z-0.5..z+1.5; per entity radiation
    // -0.5, remove the radiation effect, clear the contamination list). updateEntity is called directly on a block entity bound to the level for the exact
    // value; a placed block then runs through the real ticker.
    @GameTest(template = TEMPLATE, batch = "radcontrol_decontaminator_regression", timeoutTicks = 200)
    public static void decontaminator_regression(GameTestHelper helper) {
        List<Entity> spawned = new ArrayList<>();
        ServerLevel level = helper.getLevel();
        BlockPos rel = new BlockPos(8, 1, 8);
        try {
            guard(() -> {
                requireContamination();
                Pig inside = pig(helper, spawned, new Vec3(8.5, 1, 8.5));
                Pig outside = pig(helper, spawned, new Vec3(12.5, 1, 8.5));
                Pig above = pig(helper, spawned, new Vec3(8.5, 3.2, 8.5));
                for(Pig pig : List.of(inside, outside, above)) {
                    HbmLivingAttachments.setRadiation(pig, 10F);
                    pig.addEffect(new MobEffectInstance(ModEffect.RADIATION, 1000));
                    HbmLivingAttachments.getCont(pig).clear();
                    HbmLivingAttachments.addCont(pig, new ContaminationEffect(5F, 100, false));
                    check(pig.hasEffect(ModEffect.RADIATION), "the radiation effect was not applied");
                }

                BlockPos abs = helper.absolutePos(rel);
                DecontaminatorBlockEntity be = new DecontaminatorBlockEntity(abs, NtmBlocks.DECONTAMINATOR.get().defaultBlockState());
                be.setLevel(level);
                be.updateEntity();
                check(HbmLivingAttachments.getRadiation(inside) == 9.5F, "the pig in the box has " + HbmLivingAttachments.getRadiation(inside) + " rad, expected 9.5");
                check(!inside.hasEffect(ModEffect.RADIATION), "the radiation effect was not removed");
                check(HbmLivingAttachments.getCont(inside).isEmpty(), "the contamination list was not cleared");
                check(HbmLivingAttachments.getRadiation(outside) == 10F && outside.hasEffect(ModEffect.RADIATION) && HbmLivingAttachments.getCont(outside).size() == 1,
                        "the pig 4 blocks away was treated");
                check(HbmLivingAttachments.getRadiation(above) == 10F && above.hasEffect(ModEffect.RADIATION), "the pig above the 2 block tall box was treated");

                // The box is y..y+2: a pig standing on the block's top (y+1..y+2) is inside, one at y+3.2 is not (checked above).
                HbmLivingAttachments.setRadiation(inside, 1F);
                be.updateEntity();
                check(HbmLivingAttachments.getRadiation(inside) == 0.5F, "a second call gave " + HbmLivingAttachments.getRadiation(inside));
                be.updateEntity();
                check(HbmLivingAttachments.getRadiation(inside) == 0F, "radiation went below zero or did not clamp: " + HbmLivingAttachments.getRadiation(inside));

                // Real ticker: the placed block removes the effect and the contamination of a pig standing in the box within a few ticks.
                outside.discard();
                above.discard();
                helper.setBlock(new BlockPos(4, 1, 4), NtmBlocks.DECONTAMINATOR.get());
                // A control pig two blocks away outside the box receives the same ambient radiation, so the difference between the two is the decontaminator's.
                Pig ticked = pig(helper, spawned, new Vec3(4.5, 2, 4.5));
                Pig control = pig(helper, spawned, new Vec3(4.5, 2, 8.5));
                for(Pig pig : List.of(ticked, control)) {
                    HbmLivingAttachments.setRadiation(pig, 10F);
                    pig.addEffect(new MobEffectInstance(ModEffect.RADIATION, 1000));
                    HbmLivingAttachments.addCont(pig, new ContaminationEffect(5F, 100, false));
                }
                helper.startSequence()
                        .thenExecuteAfter(5, guard(() -> {
                            check(!ticked.hasEffect(ModEffect.RADIATION), "the ticking decontaminator left the radiation effect");
                            check(HbmLivingAttachments.getCont(ticked).isEmpty(), "the ticking decontaminator left the contamination list");
                            LOGGER.info("{} decontaminator ticker: radiation {} in the box, {} outside", TAG, HbmLivingAttachments.getRadiation(ticked), HbmLivingAttachments.getRadiation(control));
                            check(HbmLivingAttachments.getRadiation(control) - HbmLivingAttachments.getRadiation(ticked) >= 1F, "the ticking decontaminator did not lower the radiation against the control: "
                                    + HbmLivingAttachments.getRadiation(ticked) + " in the box, " + HbmLivingAttachments.getRadiation(control) + " outside");
                            helper.setBlock(new BlockPos(4, 1, 4), Blocks.AIR);
                            cleanUp(spawned);
                        }))
                        .thenExecute(passed("decontaminator_regression"))
                        .thenSucceed();
            }).run();
        } catch(RuntimeException e) {
            cleanUp(spawned);
            throw e;
        }
    }

    // 10. Recipes through the RecipeManager (the generated JSON as loaded). Each shaped / shapeless recipe is matched by assembling a CraftingInput; the
    // original rows are cited per group.
    @GameTest(template = TEMPLATE, batch = "radcontrol_recipes", timeoutTicks = 100)
    public static void recipes(GameTestHelper helper) {
        guard(() -> {
            Item rubber = NtmItems.INGOT_RUBBER.get();
            Item bio = NtmItems.INGOT_BIORUBBER.get();
            Item plate = NtmItems.PLATE_STEEL.get();

            // ToolRecipes.java:113 geiger_counter "GPP","WCS","WBB": G gold ingot, P any rubber, W gold fine wire, C basic circuit, S steel plate, B beryllium ingot
            for(Item p : new Item[] { rubber, bio }) {
                CraftingInput geiger = shaped(new String[] { "GPP", "WCS", "WBB" }, Map.of('G', s(Items.GOLD_INGOT), 'P', s(p), 'W', s(NtmItems.WIRE_GOLD), 'C', s(NtmItems.CIRCUIT_INTEGRATED_BOARD),
                        'S', s(plate), 'B', s(NtmItems.INGOT_BERYLLIUM)));
                crafts(helper, "geiger_counter with " + p, "geiger_counter", geiger, NtmItems.GEIGER_COUNTER, 1);
            }
            Map<Character, ItemStack> geigerKey = new HashMap<>(Map.of('G', s(Items.GOLD_INGOT), 'P', s(rubber), 'W', s(NtmItems.WIRE_GOLD), 'C', s(NtmItems.CIRCUIT_INTEGRATED_BOARD),
                    'S', s(plate), 'B', s(NtmItems.INGOT_BERYLLIUM)));
            geigerKey.put('C', s(NtmItems.CIRCUIT_VACUUM_TUBE));
            notCrafting(helper, "geiger_counter with a vacuum tube", shaped(new String[] { "GPP", "WCS", "WBB" }, geigerKey), NtmItems.GEIGER_COUNTER);
            geigerKey.put('C', s(NtmItems.CIRCUIT_INTEGRATED_BOARD));
            geigerKey.put('P', s(NtmItems.INGOT_POLYMER));
            notCrafting(helper, "geiger_counter with polymer instead of rubber", shaped(new String[] { "GPP", "WCS", "WBB" }, geigerKey), NtmItems.GEIGER_COUNTER);

            // :114 dosimeter "WGW","WCW","WBW": W planks, G glass pane, C vacuum tube, B beryllium
            for(Item planks : new Item[] { Items.OAK_PLANKS, Items.BAMBOO_PLANKS }) {
                crafts(helper, "dosimeter with " + planks, "dosimeter", shaped(new String[] { "WGW", "WCW", "WBW" }, Map.of('W', s(planks), 'G', s(Items.GLASS_PANE),
                        'C', s(NtmItems.CIRCUIT_VACUUM_TUBE), 'B', s(NtmItems.INGOT_BERYLLIUM))), NtmItems.DOSIMETER, 1);
            }
            notCrafting(helper, "dosimeter with the integrated board", shaped(new String[] { "WGW", "WCW", "WBW" }, Map.of('W', s(Items.OAK_PLANKS), 'G', s(Items.GLASS_PANE),
                    'C', s(NtmItems.CIRCUIT_INTEGRATED_BOARD), 'B', s(NtmItems.INGOT_BERYLLIUM))), NtmItems.DOSIMETER);

            // :115 geiger block (shapeless geiger counter), :116 digamma diagnostic (geiger counter, polonium-210 billet, asbestos ingot)
            crafts(helper, "geiger block", "geiger", loose(s(NtmItems.GEIGER_COUNTER)), NtmBlocks.GEIGER, 1);
            crafts(helper, "digamma_diagnostic", "digamma_diagnostic", loose(s(NtmItems.GEIGER_COUNTER), s(NtmItems.BILLET_POLONIUM), s(NtmItems.INGOT_ASBESTOS)), NtmItems.DIGAMMA_DIAGNOSTIC, 1);
            notCrafting(helper, "digamma_diagnostic without asbestos", loose(s(NtmItems.GEIGER_COUNTER), s(NtmItems.BILLET_POLONIUM)), NtmItems.DIGAMMA_DIAGNOSTIC);

            // CraftingManager.java:626-629 the four absorbers "ICI","CPC","ICI"
            String[] ring = { "ICI", "CPC", "ICI" };
            crafts(helper, "rad_absorber (neo copper)", "rad_absorber", shaped(ring, Map.of('I', s(NtmItems.INGOT_COPPER), 'C', s(NtmItems.POWDER_COAL), 'P', s(NtmItems.POWDER_LEAD))), NtmBlocks.RAD_ABSORBER, 1);
            crafts(helper, "rad_absorber (vanilla copper)", "rad_absorber", shaped(ring, Map.of('I', s(Items.COPPER_INGOT), 'C', s(NtmItems.POWDER_COAL), 'P', s(NtmItems.POWDER_LEAD))), NtmBlocks.RAD_ABSORBER, 1);
            crafts(helper, "rad_absorber_red", "rad_absorber_red", shaped(ring, Map.of('I', s(NtmItems.INGOT_TITANIUM), 'C', s(NtmItems.POWDER_COAL), 'P', s(NtmBlocks.RAD_ABSORBER))), NtmBlocks.RAD_ABSORBER_RED, 1);
            for(Item plastic : new Item[] { NtmItems.INGOT_POLYMER.get(), NtmItems.INGOT_BAKELITE.get() }) {
                crafts(helper, "rad_absorber_green with " + plastic, "rad_absorber_green", shaped(ring, Map.of('I', s(plastic), 'C', s(NtmItems.POWDER_DESH_MIX), 'P', s(NtmBlocks.RAD_ABSORBER_RED))), NtmBlocks.RAD_ABSORBER_GREEN, 1);
            }
            crafts(helper, "rad_absorber_pink", "rad_absorber_pink", shaped(ring, Map.of('I', s(NtmItems.INGOT_SATURNITE), 'C', s(NtmItems.POWDER_NITAN_MIX), 'P', s(NtmBlocks.RAD_ABSORBER_GREEN))), NtmBlocks.RAD_ABSORBER_PINK, 1);
            notCrafting(helper, "rad_absorber_red from the base absorber replaced by lead powder", shaped(ring, Map.of('I', s(NtmItems.INGOT_TITANIUM), 'C', s(NtmItems.POWDER_COAL), 'P', s(NtmItems.POWDER_LEAD))), NtmBlocks.RAD_ABSORBER_RED);
            notCrafting(helper, "rad_absorber_pink from the red absorber", shaped(ring, Map.of('I', s(NtmItems.INGOT_SATURNITE), 'C', s(NtmItems.POWDER_NITAN_MIX), 'P', s(NtmBlocks.RAD_ABSORBER_RED))), NtmBlocks.RAD_ABSORBER_PINK);

            // :630 decontaminator "BGB","SAS","BSB": B beryllium, G iron bars, S steel ingot, A base absorber
            crafts(helper, "decontaminator", "decontaminator", shaped(new String[] { "BGB", "SAS", "BSB" }, Map.of('B', s(NtmItems.INGOT_BERYLLIUM), 'G', s(Items.IRON_BARS),
                    'S', s(NtmItems.INGOT_STEEL), 'A', s(NtmBlocks.RAD_ABSORBER))), NtmBlocks.DECONTAMINATOR, 1);

            // MineralRecipes.java:40 add1To9Pair: nine ingots -> block, block -> nine ingots
            crafts(helper, "block_graphite from nine ingots", "block_graphite_from_9_ingot_graphite", shaped(new String[] { "XXX", "XXX", "XXX" }, Map.of('X', s(NtmItems.INGOT_GRAPHITE))), NtmBlocks.BLOCK_GRAPHITE, 1);
            crafts(helper, "nine ingot_graphite from the block", "ingot_graphite_from_block_graphite", loose(s(NtmBlocks.BLOCK_GRAPHITE)), NtmItems.INGOT_GRAPHITE, 9);

            // CraftingManager.java:687-688 eight sand + one powder -> 8 sand_boron / sand_lead ("sand" is the ore dictionary entry: any sand)
            List<ItemStack> sands = new ArrayList<>();
            for(int i = 0; i < 8; i++) sands.add(s(i % 2 == 0 ? Items.SAND : Items.RED_SAND));
            crafts(helper, "sand_boron", "sand_boron", loose(withExtra(sands, s(NtmItems.POWDER_BORON))), NtmBlocks.SAND_BORON, 8);
            crafts(helper, "sand_lead", "sand_lead", loose(withExtra(sands, s(NtmItems.POWDER_LEAD))), NtmBlocks.SAND_LEAD, 8);
            notCrafting(helper, "sand_boron from seven sands", loose(withExtra(sands.subList(0, 7), s(NtmItems.POWDER_BORON))), NtmBlocks.SAND_BORON);
            notCrafting(helper, "sand_boron from lead powder", loose(withExtra(sands, s(NtmItems.POWDER_LEAD))), NtmBlocks.SAND_BORON);

            // SmeltingRecipes.java:132-133 GameRegistry.addSmelting(..., 0.25F): the 1.7.10 furnace time is 200 ticks
            smelts(helper, "sand_boron", "glass_boron_from_smelting_sand_boron", NtmBlocks.SAND_BORON, NtmBlocks.GLASS_BORON);
            smelts(helper, "sand_lead", "glass_lead_from_smelting_sand_lead", NtmBlocks.SAND_LEAD, NtmBlocks.GLASS_LEAD);

            // CraftingManager.java:753-754 rbmk_lid_glass x4, both row orders: L lead glass, B boron glass, P steel plate
            Map<Character, ItemStack> lid = Map.of('L', s(NtmBlocks.GLASS_LEAD), 'B', s(NtmBlocks.GLASS_BORON), 'P', s(plate));
            crafts(helper, "rbmk_lid_glass lead on top", "rbmk_lid_glass", shaped(new String[] { "LLL", "BBB", "P P" }, lid), NtmItems.RBMK_LID_GLASS, 4);
            crafts(helper, "rbmk_lid_glass boron on top", "rbmk_lid_glass_boron_top", shaped(new String[] { "BBB", "LLL", "P P" }, lid), NtmItems.RBMK_LID_GLASS, 4);
            notCrafting(helper, "rbmk_lid_glass with a lead row twice", shaped(new String[] { "LLL", "LLL", "P P" }, lid), NtmItems.RBMK_LID_GLASS);

            // :756 rbmk_moderator " G ","GRG"," G ", :761 rbmk_control_mod and :992 rbmk_rod_mod "BGB","GRG","BGB" (B bismuth nugget)
            crafts(helper, "rbmk_moderator", "rbmk_moderator", shaped(new String[] { " G ", "GRG", " G " }, Map.of('G', s(NtmBlocks.BLOCK_GRAPHITE), 'R', s(NtmBlocks.RBMK_BLANK))), NtmBlocks.RBMK_MODERATOR, 1);
            crafts(helper, "rbmk_control_mod", "rbmk_control_mod", shaped(new String[] { "BGB", "GRG", "BGB" }, Map.of('B', s(NtmItems.NUGGET_BISMUTH), 'G', s(NtmBlocks.BLOCK_GRAPHITE),
                    'R', s(NtmBlocks.RBMK_CONTROL))), NtmBlocks.RBMK_CONTROL_MOD, 1);
            crafts(helper, "rbmk_rod_mod", "rbmk_rod_mod", shaped(new String[] { "BGB", "GRG", "BGB" }, Map.of('B', s(NtmItems.NUGGET_BISMUTH), 'G', s(NtmBlocks.BLOCK_GRAPHITE),
                    'R', s(NtmBlocks.RBMK_ROD))), NtmBlocks.RBMK_ROD_MOD, 1);
            notCrafting(helper, "rbmk_rod_mod around the control column", shaped(new String[] { "BGB", "GRG", "BGB" }, Map.of('B', s(NtmItems.NUGGET_BISMUTH), 'G', s(NtmBlocks.BLOCK_GRAPHITE),
                    'R', s(NtmBlocks.RBMK_CONTROL))), NtmBlocks.RBMK_ROD_MOD);
        }).run();
        done(helper, "recipes");
    }

    private static ItemStack s(ItemLike item) {
        return new ItemStack(item);
    }

    private static List<ItemStack> withExtra(List<ItemStack> base, ItemStack extra) {
        List<ItemStack> list = new ArrayList<>();
        for(ItemStack stack : base) list.add(stack.copy());
        list.add(extra);
        return list;
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

    /** A shapeless arrangement: the items in the first cells of a 3x3 grid. */
    private static CraftingInput loose(ItemStack... stacks) {
        return loose(new ArrayList<>(List.of(stacks)));
    }

    private static CraftingInput loose(List<ItemStack> stacks) {
        List<ItemStack> cells = new ArrayList<>();
        for(int i = 0; i < 9; i++) cells.add(i < stacks.size() ? stacks.get(i).copy() : ItemStack.EMPTY);
        return CraftingInput.of(3, 3, cells);
    }

    private static ResourceLocation id(String path) {
        return ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path);
    }

    /** The recipe manager must offer the named recipe for the grid and the player's first match must yield count x out. */
    private static void crafts(GameTestHelper helper, String label, String recipeId, CraftingInput input, ItemLike out, int count) {
        ServerLevel level = helper.getLevel();
        RecipeManager manager = level.getRecipeManager();
        List<RecipeHolder<CraftingRecipe>> all = manager.getRecipesFor(RecipeType.CRAFTING, input, level);
        List<ResourceLocation> ids = new ArrayList<>();
        boolean found = false;
        for(RecipeHolder<CraftingRecipe> holder : all) {
            ids.add(holder.id());
            if(holder.id().equals(id(recipeId))) {
                found = true;
                ItemStack result = holder.value().assemble(input, level.registryAccess());
                check(result.is(out.asItem()) && result.getCount() == count, label + ": " + holder.id() + " yields " + result + ", expected " + count + " x " + out.asItem());
            }
        }
        check(found, label + ": the grid is not matched by " + id(recipeId) + ", it matches " + ids);
        Optional<RecipeHolder<CraftingRecipe>> first = manager.getRecipeFor(RecipeType.CRAFTING, input, level);
        check(first.isPresent(), label + ": getRecipeFor found nothing");
        ItemStack result = first.get().value().assemble(input, level.registryAccess());
        check(result.is(out.asItem()) && result.getCount() == count, label + ": the first match " + first.get().id() + " yields " + result + ", expected " + count + " x " + out.asItem());
    }

    /** No crafting recipe may turn the grid into the item. */
    private static void notCrafting(GameTestHelper helper, String label, CraftingInput input, ItemLike out) {
        ServerLevel level = helper.getLevel();
        for(RecipeHolder<CraftingRecipe> holder : level.getRecipeManager().getRecipesFor(RecipeType.CRAFTING, input, level)) {
            ItemStack result = holder.value().assemble(input, level.registryAccess());
            check(!result.is(out.asItem()), label + ": " + holder.id() + " yields " + result);
        }
    }

    private static void smelts(GameTestHelper helper, String label, String recipeId, ItemLike in, ItemLike out) {
        ServerLevel level = helper.getLevel();
        SingleRecipeInput input = new SingleRecipeInput(s(in));
        Optional<RecipeHolder<SmeltingRecipe>> holder = level.getRecipeManager().getRecipeFor(RecipeType.SMELTING, input, level);
        check(holder.isPresent(), label + ": no smelting recipe");
        check(holder.get().id().equals(id(recipeId)), label + ": smelting recipe " + holder.get().id());
        SmeltingRecipe recipe = holder.get().value();
        ItemStack result = recipe.assemble(input, level.registryAccess());
        check(result.is(out.asItem()) && result.getCount() == 1, label + ": smelts to " + result);
        check(recipe.getExperience() == 0.25F, label + ": experience " + recipe.getExperience() + ", expected 0.25");
        check(recipe.getCookingTime() == 200, label + ": cooking time " + recipe.getCookingTime() + ", expected 200");
    }

    // Crystallizer default table (CrystallizerRecipes.java:56 baseTime 600, :99 the coal block row, :310-322 the two-argument registerRecipe: hydrogen
    // peroxide 500 mB, itemAmount 1, productivity 0). The first 46 rows are the start rows of NEO's table (Goals 20A and 22A, ores in the original
    // order); the new row is appended last.
    @GameTest(template = TEMPLATE, batch = "radcontrol_crystallizer_row", timeoutTicks = 100)
    public static void crystallizer_row(GameTestHelper helper) {
        guard(() -> {
            List<CrystallizerRecipe> defaults = CrystallizerRecipes.getDefaultRecipes();
            check(defaults.size() == 47, "the default table has " + defaults.size() + " rows, expected 47");

            // The 46 start rows: [input block, output crystal, acid], stone and deepslate variants as separate rows.
            List<Object[]> start = new ArrayList<>();
            Object peroxide = Fluids.PEROXIDE;
            Object sulfuric = Fluids.SULFURIC_ACID;
            addPair(start, Blocks.COAL_ORE, Blocks.DEEPSLATE_COAL_ORE, NtmItems.CRYSTAL_COAL, peroxide);
            addPair(start, Blocks.IRON_ORE, Blocks.DEEPSLATE_IRON_ORE, NtmItems.CRYSTAL_IRON, peroxide);
            addPair(start, Blocks.GOLD_ORE, Blocks.DEEPSLATE_GOLD_ORE, NtmItems.CRYSTAL_GOLD, peroxide);
            addPair(start, Blocks.REDSTONE_ORE, Blocks.DEEPSLATE_REDSTONE_ORE, NtmItems.CRYSTAL_REDSTONE, peroxide);
            addPair(start, Blocks.LAPIS_ORE, Blocks.DEEPSLATE_LAPIS_ORE, NtmItems.CRYSTAL_LAPIS, peroxide);
            addPair(start, Blocks.DIAMOND_ORE, Blocks.DEEPSLATE_DIAMOND_ORE, NtmItems.CRYSTAL_DIAMOND, peroxide);
            addPair(start, NtmBlocks.ORE_SULFUR.get(), NtmBlocks.ORE_SULFUR_DEEPSLATE.get(), NtmItems.CRYSTAL_SULFUR, peroxide);
            addPair(start, NtmBlocks.ORE_NITER.get(), NtmBlocks.ORE_NITER_DEEPSLATE.get(), NtmItems.CRYSTAL_NITER, peroxide);
            addPair(start, Blocks.COPPER_ORE, Blocks.DEEPSLATE_COPPER_ORE, NtmItems.CRYSTAL_COPPER, peroxide);
            addPair(start, NtmBlocks.ORE_ALUMINIUM.get(), NtmBlocks.ORE_ALUMINIUM_DEEPSLATE.get(), NtmItems.CRYSTAL_ALUMINIUM, peroxide);
            addPair(start, NtmBlocks.ORE_FLUORITE.get(), NtmBlocks.ORE_FLUORITE_DEEPSLATE.get(), NtmItems.CRYSTAL_FLUORITE, peroxide);
            addPair(start, NtmBlocks.ORE_BERYLLIUM.get(), NtmBlocks.ORE_BERYLLIUM_DEEPSLATE.get(), NtmItems.CRYSTAL_BERYLLIUM, peroxide);
            addPair(start, NtmBlocks.ORE_LEAD.get(), NtmBlocks.ORE_LEAD_DEEPSLATE.get(), NtmItems.CRYSTAL_LEAD, peroxide);
            addPair(start, NtmBlocks.ORE_CINNABAR.get(), NtmBlocks.ORE_CINNABAR_DEEPSLATE.get(), NtmItems.CRYSTAL_CINNABAR, peroxide);
            addPair(start, NtmBlocks.ORE_TITANIUM.get(), NtmBlocks.ORE_TITANIUM_DEEPSLATE.get(), NtmItems.CRYSTAL_TITANIUM, sulfuric);
            addPair(start, NtmBlocks.ORE_TUNGSTEN.get(), NtmBlocks.ORE_TUNGSTEN_DEEPSLATE.get(), NtmItems.CRYSTAL_TUNGSTEN, sulfuric);
            addPair(start, NtmBlocks.ORE_COBALT.get(), NtmBlocks.ORE_COBALT_DEEPSLATE.get(), NtmItems.CRYSTAL_COBALT, sulfuric);
            addPair(start, NtmBlocks.ORE_RARE.get(), NtmBlocks.ORE_RARE_DEEPSLATE.get(), NtmItems.CRYSTAL_RARE, sulfuric);
            addPair(start, NtmBlocks.ORE_URANIUM.get(), NtmBlocks.ORE_URANIUM_DEEPSLATE.get(), NtmItems.CRYSTAL_URANIUM, sulfuric);
            start.add(new Object[] { NtmBlocks.ORE_URANIUM_SCORCHED.get(), NtmItems.CRYSTAL_URANIUM.get(), sulfuric });
            addPair(start, NtmBlocks.ORE_THORIUM.get(), NtmBlocks.ORE_THORIUM_DEEPSLATE.get(), NtmItems.CRYSTAL_THORIUM, sulfuric);
            start.add(new Object[] { NtmBlocks.ORE_NETHER_URANIUM.get(), NtmItems.CRYSTAL_URANIUM.get(), sulfuric });
            start.add(new Object[] { NtmBlocks.ORE_NETHER_URANIUM_SCORCHED.get(), NtmItems.CRYSTAL_URANIUM.get(), sulfuric });
            start.add(new Object[] { NtmBlocks.ORE_GNEISS_URANIUM.get(), NtmItems.CRYSTAL_URANIUM.get(), sulfuric });
            start.add(new Object[] { NtmBlocks.ORE_GNEISS_URANIUM_SCORCHED.get(), NtmItems.CRYSTAL_URANIUM.get(), sulfuric });
            start.add(new Object[] { NtmBlocks.ORE_NETHER_PLUTONIUM.get(), NtmItems.CRYSTAL_PLUTONIUM.get(), sulfuric });
            check(start.size() == 46, "the start table list has " + start.size() + " rows");
            for(int i = 0; i < 46; i++) {
                CrystallizerRecipe row = defaults.get(i);
                Object[] expected = start.get(i);
                check(row.input instanceof ComparableStack stack && stack.item == ((Block) expected[0]).asItem(), "row " + i + " input is " + row.input + ", expected " + expected[0]);
                check(row.output.is((Item) expected[1]) && row.output.getCount() == 1, "row " + i + " output is " + row.output);
                check(row.fluid.type == expected[2], "row " + i + " acid is " + row.fluid.type);
                check(row.fluid.fill == 500 && row.duration == 600 && row.productivity == 0.05F && row.itemAmount() == 1,
                        "row " + i + " numbers: " + row.fluid.fill + " mB, " + row.duration + " ticks, productivity " + row.productivity + ", " + row.itemAmount() + " items");
            }

            // Row 47: OreDictStack(blockCoal) -> block_graphite, 500 mB peroxide, 600 ticks, productivity 0 (:99, :314-316, :56)
            CrystallizerRecipe coal = defaults.get(46);
            check(coal.input instanceof TagStack tag && tag.tag.location().equals(ResourceLocation.fromNamespaceAndPath("c", "storage_blocks/coal")) && tag.stacksize == 1,
                    "row 47 input is " + coal.input);
            check(coal.output.is(NtmBlocks.BLOCK_GRAPHITE.get().asItem()) && coal.output.getCount() == 1, "row 47 output is " + coal.output);
            check(coal.fluid.type == Fluids.PEROXIDE && coal.fluid.fill == 500, "row 47 fluid is " + coal.fluid.type + " " + coal.fluid.fill);
            check(coal.duration == 600, "row 47 duration " + coal.duration);
            check(coal.productivity == 0F, "row 47 productivity " + coal.productivity);

            CrystallizerRecipe found = CrystallizerRecipes.getOutput(defaults, new ItemStack(Items.COAL_BLOCK), Fluids.PEROXIDE);
            check(found != null && found.output.is(NtmBlocks.BLOCK_GRAPHITE.get().asItem()) && found.acidAmount() == 500 && found.duration == 600 && found.productivity == 0F,
                    "the coal block under peroxide gives " + found);
            check(CrystallizerRecipes.getOutput(defaults, new ItemStack(Items.COAL_BLOCK), Fluids.SULFURIC_ACID) == null, "the coal block has a sulfuric acid row");
            CrystallizerRecipe ore = CrystallizerRecipes.getOutput(defaults, new ItemStack(Blocks.COAL_ORE), Fluids.PEROXIDE);
            check(ore != null && ore.output.is(NtmItems.CRYSTAL_COAL.get()), "coal ore under peroxide no longer gives the coal crystal: " + ore);
        }).run();
        done(helper, "crystallizer_row");
    }

    private static void addPair(List<Object[]> rows, Block stone, Block deepslate, ItemLike crystal, Object acid) {
        rows.add(new Object[] { stone, crystal.asItem(), acid });
        rows.add(new Object[] { deepslate, crystal.asItem(), acid });
    }

    // 11. The eight new blocks (ModBlocks.java:1410 block_graphite hardness 5 / resistance 10 / metal / BlockFlammable 30 and 5, :1641 sand_mix hardness 0.5
    // / sand, :1642-1643 glass hardness 0.3 / glass, :2307 absorbers hardness 5 / resistance 10). 1.7.10 setHardness raises the resistance to
    // 5 x hardness and Block.getExplosionResistance divides by 5, so the effective explosion resistance of a block that only sets a hardness equals
    // that hardness (0.5 and 0.3 here). The absorbers and the graphite block copy the raw setResistance(10.0F), as the rest of NEO does. The original
    // glass (BlockBreakable) drops nothing without silk touch; NEO follows its glass_quartz precedent and drops the block (main-notes decision 6).
    @GameTest(template = TEMPLATE, batch = "radcontrol_blocks", timeoutTicks = 100)
    public static void blocks(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            BlockPos pos = helper.absolutePos(new BlockPos(8, 2, 8));
            ItemStack pickaxe = new ItemStack(Items.IRON_PICKAXE);
            ItemStack shovel = new ItemStack(Items.IRON_SHOVEL);

            Object[][] rows = {
                    { "rad_absorber", NtmBlocks.RAD_ABSORBER.get(), 5F, 10F, SoundType.STONE, pickaxe },
                    { "rad_absorber_red", NtmBlocks.RAD_ABSORBER_RED.get(), 5F, 10F, SoundType.STONE, pickaxe },
                    { "rad_absorber_green", NtmBlocks.RAD_ABSORBER_GREEN.get(), 5F, 10F, SoundType.STONE, pickaxe },
                    { "rad_absorber_pink", NtmBlocks.RAD_ABSORBER_PINK.get(), 5F, 10F, SoundType.STONE, pickaxe },
                    { "block_graphite", NtmBlocks.BLOCK_GRAPHITE.get(), 5F, 10F, SoundType.METAL, pickaxe },
                    { "sand_lead", NtmBlocks.SAND_LEAD.get(), 0.5F, 0.5F, SoundType.SAND, shovel },
                    { "sand_boron", NtmBlocks.SAND_BORON.get(), 0.5F, 0.5F, SoundType.SAND, shovel },
                    { "glass_lead", NtmBlocks.GLASS_LEAD.get(), 0.3F, 0.3F, SoundType.GLASS, pickaxe },
                    { "glass_boron", NtmBlocks.GLASS_BORON.get(), 0.3F, 0.3F, SoundType.GLASS, pickaxe } };
            for(Object[] row : rows) {
                String name = (String) row[0];
                Block block = (Block) row[1];
                BlockState state = block.defaultBlockState();
                check(BuiltInRegistries.BLOCK.getKey(block).equals(id(name)), name + " is registered as " + BuiltInRegistries.BLOCK.getKey(block));
                check(BuiltInRegistries.ITEM.containsKey(id(name)), name + " has no block item");
                check(state.getDestroySpeed(level, pos) == (Float) row[2], name + " hardness " + state.getDestroySpeed(level, pos) + ", expected " + row[2]);
                check(block.getExplosionResistance() == (Float) row[3], name + " resistance " + block.getExplosionResistance() + ", expected " + row[3]);
                check(state.getSoundType() == row[4], name + " sound type is not the expected one");
                check(!state.requiresCorrectToolForDrops(), name + " requires the correct tool (the original blocks do not)");

                List<ItemStack> drops = Block.getDrops(state, level, pos, null, null, (ItemStack) row[5]);
                check(drops.size() == 1 && drops.get(0).is(block.asItem()) && drops.get(0).getCount() == 1, name + " drops " + drops);
            }

            // BlockFlammable.java:12-30: getFlammability = 5, getFireSpreadSpeed = encouragement 30 (new BlockGraphite(Material.iron, 30, 5))
            BlockState graphite = NtmBlocks.BLOCK_GRAPHITE.get().defaultBlockState();
            for(Direction face : Direction.values()) {
                check(graphite.getFlammability(level, pos, face) == 5, "block_graphite flammability " + graphite.getFlammability(level, pos, face) + " on " + face + ", expected 5");
                check(graphite.getFireSpreadSpeed(level, pos, face) == 30, "block_graphite fire spread speed " + graphite.getFireSpreadSpeed(level, pos, face) + " on " + face + ", expected 30");
            }
            check(Blocks.STONE.defaultBlockState().getFlammability(level, pos, Direction.UP) == 0, "the control block stone is flammable");

            // Sands fall like sand; glass is vanilla-glass-like.
            check(NtmBlocks.SAND_LEAD.get() instanceof FallingBlock && NtmBlocks.SAND_BORON.get() instanceof FallingBlock, "a sand block is not a falling block");
            for(Block glass : new Block[] { NtmBlocks.GLASS_LEAD.get(), NtmBlocks.GLASS_BORON.get() }) {
                BlockState state = glass.defaultBlockState();
                String name = BuiltInRegistries.BLOCK.getKey(glass).getPath();
                check(!state.isValidSpawn(level, pos, EntityType.ZOMBIE), name + " is a valid spawn");
                check(!state.isRedstoneConductor(level, pos), name + " is a redstone conductor");
                check(!state.isSuffocating(level, pos), name + " is suffocating");
                check(!state.isViewBlocking(level, pos), name + " blocks the view");
                BlockState vanilla = Blocks.GLASS.defaultBlockState();
                check(state.isValidSpawn(level, pos, EntityType.ZOMBIE) == vanilla.isValidSpawn(level, pos, EntityType.ZOMBIE)
                        && state.isRedstoneConductor(level, pos) == vanilla.isRedstoneConductor(level, pos)
                        && state.isSuffocating(level, pos) == vanilla.isSuffocating(level, pos)
                        && state.canOcclude() == vanilla.canOcclude(), name + " differs from vanilla glass in its occlusion predicates");
            }
        }).run();
        done(helper, "blocks");
    }

    // A sand block placed over air falls (ModBlocks.java:1641 BlockNTMSand: gravity sand).
    @GameTest(template = TEMPLATE, batch = "radcontrol_blocks_sand_falls", timeoutTicks = 200)
    public static void blocks_sand_falls(GameTestHelper helper) {
        BlockPos stoneLead = new BlockPos(5, 1, 5);
        BlockPos stoneBoron = new BlockPos(9, 1, 9);
        BlockPos lead = new BlockPos(5, 7, 5);
        BlockPos boron = new BlockPos(9, 7, 9);
        Runnable clear = () -> {
            for(BlockPos rel : new BlockPos[] { stoneLead, stoneBoron, lead, boron, stoneLead.above(), stoneBoron.above() }) helper.setBlock(rel, Blocks.AIR);
        };
        helper.setBlock(stoneLead, Blocks.STONE);
        helper.setBlock(stoneBoron, Blocks.STONE);
        helper.setBlock(lead, NtmBlocks.SAND_LEAD.get());
        helper.setBlock(boron, NtmBlocks.SAND_BORON.get());
        helper.startSequence()
                // thenWaitUntil retries a failing step every tick, so this step must not clear the cells on a failed attempt.
                .thenWaitUntil(guard(() -> {
                    check(helper.getBlockState(stoneLead.above()).is(NtmBlocks.SAND_LEAD.get()), "sand_lead has not landed on the stone, column " + column(helper, stoneLead) + ", falling entities "
                            + helper.getLevel().getEntitiesOfClass(FallingBlockEntity.class, helper.getBounds().inflate(2)).size());
                    check(helper.getBlockState(stoneBoron.above()).is(NtmBlocks.SAND_BORON.get()), "sand_boron has not landed on the stone, column " + column(helper, stoneBoron));
                }))
                .thenExecute(restoring(clear, () -> {
                    check(helper.getBlockState(lead).isAir() && helper.getBlockState(boron).isAir(), "the placement cells are not empty after the fall");
                    check(helper.getLevel().getEntitiesOfClass(FallingBlockEntity.class, helper.getBounds().inflate(2)).isEmpty(), "a falling block entity is left over");
                    clear.run();
                }))
                .thenExecute(passed("blocks_sand_falls"))
                .thenSucceed();
    }

    // Helpers

    private static String column(GameTestHelper helper, BlockPos base) {
        StringBuilder text = new StringBuilder();
        for(int y = 0; y <= 8; y++) text.append(y).append('=').append(BuiltInRegistries.BLOCK.getKey(helper.getBlockState(new BlockPos(base.getX(), y, base.getZ())).getBlock()).getPath()).append(' ');
        return text.toString();
    }

    /** Stores a filter on the mask's custom data the way ArmorUtil.getGasMaskFilter reads it, without the production install method. */
    private static void putFilter(ServerLevel level, ItemStack mask, ItemStack filter) {
        CompoundTag tag = TagsUtil.getCustomData(mask);
        tag.put(ArmorUtil.FILTER_KEY, filter.save(level.registryAccess()));
        TagsUtil.putCustomData(mask, tag);
    }

    /** A modded armor stack with a hand-built ntm_armor_mods compound (slot index to mod stack). */
    private static ItemStack modsHelmet(ServerLevel level, Item armor, Map<Integer, ItemStack> mods) {
        ItemStack stack = new ItemStack(armor);
        CompoundTag tag = new CompoundTag();
        CompoundTag modTag = new CompoundTag();
        for(Map.Entry<Integer, ItemStack> entry : mods.entrySet()) {
            modTag.put(ArmorModHandler.MOD_SLOT_KEY + entry.getKey(), entry.getValue().save(level.registryAccess()));
        }
        tag.put(ArmorModHandler.MOD_COMPOUND_KEY, modTag);
        TagsUtil.putCustomData(stack, tag);
        return stack;
    }

    private static void requireContamination() {
        check(NtmConfig.COMMON.ENABLE_CONTAMINATION.get(), "contamination is disabled in the common config; the radiation tests need it");
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

    private static Runnable passed(String name) {
        return () -> LOGGER.info("{} {} passed", TAG, name);
    }

    private static void done(GameTestHelper helper, String name) {
        LOGGER.info("{} {} passed", TAG, name);
        helper.succeed();
    }
}
