package com.hbm.gametest;

import api.hbm.item.IGasMask;
import com.hbm.blocks.NtmBlocks;
import com.hbm.config.NtmConfig;
import com.hbm.extprop.HbmLivingAttachments;
import com.hbm.handler.ArmorModHandler;
import com.hbm.hazard.HazardRegistry;
import com.hbm.inventory.RecipesCommon.AStack;
import com.hbm.inventory.RecipesCommon.ComparableStack;
import com.hbm.inventory.recipes.AssemblyMachineRecipes;
import com.hbm.inventory.recipes.loader.GenericRecipe;
import com.hbm.items.NtmItems;
import com.hbm.items.armor.GasMaskItem;
import com.hbm.main.NuclearTechMod;
import com.hbm.registry.NtmArmorMaterials;
import com.hbm.registry.NtmDamageTypes;
import com.hbm.util.ArmorRegistry;
import com.hbm.util.ArmorRegistry.HazardClass;
import com.hbm.util.ArmorUtil;
import com.hbm.util.ContaminationUtil;
import com.hbm.util.TagsUtil;
import com.mojang.authlib.GameProfile;
import com.mojang.logging.LogUtils;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.TextColor;
import net.minecraft.network.chat.contents.TranslatableContents;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.animal.Pig;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.item.ArmorItem;
import net.minecraft.world.item.ArmorMaterial;
import net.minecraft.world.item.ArmorMaterials;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.item.crafting.CraftingInput;
import net.minecraft.world.item.crafting.CraftingRecipe;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.RecipeManager;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.item.crafting.SingleRecipeInput;
import net.minecraft.world.item.crafting.SmeltingRecipe;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.ItemLike;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.LiquidBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.common.util.FakePlayer;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import org.slf4j.Logger;

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
 * Server-side tests for Goal26B, the gas masks: the four IGasMask helmets (gas_mask, gas_mask_m65, gas_mask_mono, gas_mask_olde), the two
 * rag masks, the five filters, the rags, their recipes and the assembly row ass.filtercoal. Same template and conventions as
 * {@link RadiationControlGameTests} and {@link HazardGameTests}; every test has its own batch.
 * <p>
 * Expected values come from the ORIGINAL, cited beside each group of checks (ArmorUtil.java:39-48,296-353,355-383, ArmorRegistry.java:61-99,
 * ArmorGasMask.java:59-61,88-104,147-155,189-191,193-212, ItemFilter.java:16-72, ItemRag.java:17-38, ModItemsArmor.java:22-32, ModArmor.java:66-71,
 * ModItems.java:2398-2401,2838-2842, HazardTypeAsbestos.java:27-30, HazardTypeCoal.java:27-32, BlockGasMonoxide.java:29-32, BlockGasRadon.java:32-36,
 * ArmorModHandler.java:101-119, ArmorRecipes.java:154-161, ConsumableRecipes.java:217-221, CraftingManager.java:839, SmeltingRecipes.java:118-119,
 * AssemblyMachineRecipes.java:122-123), not from the NEO implementation.
 * <p>
 * Real items: every mask, filter and rag is the registered production item; no stand-in item is used. Entities: Pigs (a Zombie is radiation
 * immune) for the worn-protection and hazard checks, and a NeoForge {@link FakePlayer} (a ServerPlayer that is not added to the level) for the
 * right-click paths, driven through the server's own {@code ServerPlayerGameMode.useItem}, which applies the returned stack to the hand as the
 * game does. Item drops of the FakePlayer go through the real ServerPlayer.drop and appear as ItemEntities in the test level.
 * Not evidence: the client (worn models, the helmet overlay, tooltips as drawn, the gasmask_screw sound as heard - the sound call is only
 * required not to throw), the client half of the use methods, real players over a network, saved worlds, and the 1.7.10 game itself.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class GasMaskGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-gas-mask]";

    // 1. Protection classes (ArmorUtil.java:39-48 registrations; ArmorRegistry.java:61-99 mask classes + filter classes minus the mask's blacklist;
    // ArmorGasMask.java:147-155 blacklists: mono {GAS_LUNG, GAS_BLISTERING, BACTERIA}, the others {GAS_BLISTERING})
    @GameTest(template = TEMPLATE, batch = "gasmask_protection_classes", timeoutTicks = 100)
    public static void protection_classes(GameTestHelper helper) {
        List<Entity> spawned = new ArrayList<>();
        try {
            guard(() -> {
                Pig pig = pig(helper, spawned, new Vec3(8.5, 1, 8.5));

                Item gasMask = NtmItems.GAS_MASK.get(), m65 = NtmItems.GAS_MASK_M65.get(), mono = NtmItems.GAS_MASK_MONO.get(), olde = NtmItems.GAS_MASK_OLDE.get();
                Item filter = NtmItems.GAS_MASK_FILTER.get(), filterMono = NtmItems.GAS_MASK_FILTER_MONO.get(), combo = NtmItems.GAS_MASK_FILTER_COMBO.get();
                Item filterRag = NtmItems.GAS_MASK_FILTER_RAG.get(), filterPiss = NtmItems.GAS_MASK_FILTER_PISS.get();

                // The registrations themselves, in the original order of classes (ArmorUtil.java:39-48).
                registered(filter, HazardClass.PARTICLE_COARSE, HazardClass.PARTICLE_FINE, HazardClass.GAS_LUNG, HazardClass.GAS_BLISTERING, HazardClass.BACTERIA);
                registered(filterMono, HazardClass.PARTICLE_COARSE, HazardClass.GAS_MONOXIDE);
                registered(combo, HazardClass.PARTICLE_COARSE, HazardClass.PARTICLE_FINE, HazardClass.GAS_LUNG, HazardClass.GAS_BLISTERING, HazardClass.BACTERIA, HazardClass.GAS_MONOXIDE);
                registered(filterRag, HazardClass.PARTICLE_COARSE);
                registered(filterPiss, HazardClass.PARTICLE_COARSE, HazardClass.GAS_LUNG);
                registered(gasMask, HazardClass.SAND, HazardClass.LIGHT);
                registered(m65, HazardClass.SAND);
                registered(NtmItems.MASK_RAG.get(), HazardClass.PARTICLE_COARSE);
                registered(NtmItems.MASK_PISS.get(), HazardClass.PARTICLE_COARSE, HazardClass.GAS_LUNG);
                registered(Items.DIAMOND_HELMET, HazardClass.PARTICLE_COARSE, HazardClass.GAS_LUNG);
                check(!ArmorRegistry.hazardClasses.containsKey(mono) && !ArmorRegistry.hazardClasses.containsKey(olde), "gas_mask_mono or gas_mask_olde has its own classes (the original registers none)");

                // Blacklists (ArmorGasMask.java:147-155), a new list on each call.
                for(Item mask : new Item[] { gasMask, m65, olde }) {
                    List<HazardClass> black = ((IGasMask) mask).getBlacklist(new ItemStack(mask), pig);
                    check(black.equals(List.of(HazardClass.GAS_BLISTERING)), BuiltInRegistries.ITEM.getKey(mask) + " blacklist is " + black);
                }
                List<HazardClass> monoBlack = ((IGasMask) mono).getBlacklist(new ItemStack(mono), pig);
                check(monoBlack.equals(List.of(HazardClass.GAS_LUNG, HazardClass.GAS_BLISTERING, HazardClass.BACTERIA)), "gas_mask_mono blacklist is " + monoBlack);
                monoBlack.clear();
                check(((IGasMask) mono).getBlacklist(new ItemStack(mono), pig).size() == 3, "clearing the returned blacklist changed the next one (not a new list per call)");
                for(Item mask : new Item[] { gasMask, m65, mono, olde }) {
                    check(((IGasMask) mask).isFilterApplicable(new ItemStack(mask), pig, new ItemStack(filter)), BuiltInRegistries.ITEM.getKey(mask) + " refuses a filter (ArmorGasMask.java:189-191: always true)");
                }

                // Worn masks with real filters, compared as sets.
                worn(pig, gasMask, null, HazardClass.SAND, HazardClass.LIGHT);
                worn(pig, gasMask, filter, HazardClass.SAND, HazardClass.LIGHT, HazardClass.PARTICLE_COARSE, HazardClass.PARTICLE_FINE, HazardClass.GAS_LUNG, HazardClass.BACTERIA);
                check(!ArmorRegistry.hasProtection(pig, EquipmentSlot.HEAD, HazardClass.GAS_BLISTERING), "gas_mask + gas_mask_filter protects against GAS_BLISTERING (blacklisted)");
                check(ArmorRegistry.hasAllProtection(pig, EquipmentSlot.HEAD, HazardClass.PARTICLE_FINE, HazardClass.GAS_LUNG, HazardClass.SAND), "gas_mask + gas_mask_filter: hasAllProtection fine/lung/sand is false");
                check(!ArmorRegistry.hasAllProtection(pig, EquipmentSlot.HEAD, HazardClass.PARTICLE_FINE, HazardClass.GAS_MONOXIDE), "gas_mask + gas_mask_filter: hasAllProtection fine/monoxide is true");
                worn(pig, gasMask, combo, HazardClass.SAND, HazardClass.LIGHT, HazardClass.PARTICLE_COARSE, HazardClass.PARTICLE_FINE, HazardClass.GAS_LUNG, HazardClass.BACTERIA, HazardClass.GAS_MONOXIDE);
                worn(pig, m65, null, HazardClass.SAND);
                worn(pig, m65, filter, HazardClass.SAND, HazardClass.PARTICLE_COARSE, HazardClass.PARTICLE_FINE, HazardClass.GAS_LUNG, HazardClass.BACTERIA);
                worn(pig, mono, null);
                worn(pig, mono, filter, HazardClass.PARTICLE_COARSE, HazardClass.PARTICLE_FINE);
                check(!ArmorRegistry.hasProtection(pig, EquipmentSlot.HEAD, HazardClass.GAS_LUNG), "gas_mask_mono + gas_mask_filter protects against GAS_LUNG (blacklisted)");
                worn(pig, mono, filterMono, HazardClass.PARTICLE_COARSE, HazardClass.GAS_MONOXIDE);
                check(ArmorRegistry.hasProtection(pig, EquipmentSlot.HEAD, HazardClass.GAS_MONOXIDE), "gas_mask_mono + gas_mask_filter_mono: hasProtection monoxide is false");
                worn(pig, olde, null);
                worn(pig, olde, filterRag, HazardClass.PARTICLE_COARSE);
                worn(pig, olde, filterPiss, HazardClass.PARTICLE_COARSE, HazardClass.GAS_LUNG);
                worn(pig, NtmItems.MASK_RAG.get(), null, HazardClass.PARTICLE_COARSE);
                worn(pig, NtmItems.MASK_PISS.get(), null, HazardClass.PARTICLE_COARSE, HazardClass.GAS_LUNG);
                worn(pig, Items.DIAMOND_HELMET, null, HazardClass.PARTICLE_COARSE, HazardClass.GAS_LUNG);
                pig.setItemSlot(EquipmentSlot.HEAD, ItemStack.EMPTY);
                check(!ArmorRegistry.hasProtection(pig, EquipmentSlot.HEAD, HazardClass.PARTICLE_COARSE), "an empty head protects");
            }).run();
        } finally {
            cleanUp(spawned);
        }
        done(helper, "protection_classes");
    }

    private static void registered(Item item, HazardClass... expected) {
        List<HazardClass> actual = ArmorRegistry.hazardClasses.get(item);
        check(actual != null && actual.equals(List.of(expected)), BuiltInRegistries.ITEM.getKey(item) + " is registered with " + actual + ", expected " + Arrays.toString(expected));
    }

    private static void worn(Pig pig, Item mask, Item filter, HazardClass... expected) {
        ItemStack stack = new ItemStack(mask);
        if(filter != null) ((IGasMask) mask).installFilter(stack, pig, new ItemStack(filter));
        pig.setItemSlot(EquipmentSlot.HEAD, stack);
        String label = BuiltInRegistries.ITEM.getKey(mask) + (filter == null ? " without a filter" : " + " + BuiltInRegistries.ITEM.getKey(filter));
        List<HazardClass> prot = ArmorRegistry.getProtectionFromItem(pig.getItemBySlot(EquipmentSlot.HEAD), pig);
        Set<HazardClass> want = expected.length == 0 ? EnumSet.noneOf(HazardClass.class) : EnumSet.copyOf(Arrays.asList(expected));
        Set<HazardClass> got = prot.isEmpty() ? EnumSet.noneOf(HazardClass.class) : EnumSet.copyOf(prot);
        LOGGER.info("{} {}: {}", TAG, label, prot);
        check(got.equals(want), label + " protects against " + got + ", expected " + want);
        for(HazardClass clazz : HazardClass.values()) {
            check(ArmorRegistry.hasProtection(pig, EquipmentSlot.HEAD, clazz) == want.contains(clazz), label + ": hasProtection(" + clazz + ") is " + !want.contains(clazz));
        }
        if(!want.isEmpty()) check(ArmorRegistry.hasAllProtection(pig, EquipmentSlot.HEAD, want.toArray(new HazardClass[0])), label + ": hasAllProtection of its own set is false");
    }

    // 2. Hazards with real masks (HazardTypeAsbestos.java:27-30, HazardTypeCoal.java:27-32, BlockGasMonoxide.java:29-32, BlockGasRadon.java:32-36).
    // The hazard types are called through HazardRegistry.ASBESTOS / COAL .onUpdate (the per-item entry point HazardSystem.applyHazards uses);
    // the gas blocks through BlockState.entityInside, the engine's dispatch.
    @GameTest(template = TEMPLATE, batch = "gasmask_hazards", timeoutTicks = 100)
    public static void hazards(GameTestHelper helper) {
        List<Entity> spawned = new ArrayList<>();
        try {
            guard(() -> {
                check(!NtmConfig.COMMON.DISABLE_ASBESTOS.get(), "asbestos is disabled in the common config");
                check(!NtmConfig.COMMON.DISABLE_COAL.get(), "coal dust is disabled in the common config");
                check(NtmConfig.COMMON.ENABLE_CONTAMINATION.get(), "contamination is disabled in the common config; the radon checks need it");
                ServerLevel level = helper.getLevel();
                Pig pig = pig(helper, spawned, new Vec3(8.5, 1, 8.5));
                check(!ContaminationUtil.isRadImmune(pig), "the pig is radiation immune");
                ItemStack asbestosStack = new ItemStack(NtmItems.INGOT_ASBESTOS.get());

                // Asbestos: unprotected -> counter + min(level, 10); PARTICLE_FINE -> filter damage + (int) level.
                pig.setItemSlot(EquipmentSlot.HEAD, ItemStack.EMPTY);
                HbmLivingAttachments.setAsbestos(pig, 0);
                HazardRegistry.ASBESTOS.onUpdate(pig, 1F, asbestosStack);
                check(HbmLivingAttachments.getAsbestos(pig) == 1, "asbestos level 1 without a mask gave " + HbmLivingAttachments.getAsbestos(pig) + ", expected 1");
                HazardRegistry.ASBESTOS.onUpdate(pig, 12F, asbestosStack);
                check(HbmLivingAttachments.getAsbestos(pig) == 11, "asbestos level 12 without a mask gave +" + (HbmLivingAttachments.getAsbestos(pig) - 1) + ", expected +10 (min(level, 10))");

                // gas_mask without a filter: {SAND, LIGHT}, no PARTICLE_FINE -> still exposed.
                HbmLivingAttachments.setAsbestos(pig, 0);
                pig.setItemSlot(EquipmentSlot.HEAD, new ItemStack(NtmItems.GAS_MASK.get()));
                HazardRegistry.ASBESTOS.onUpdate(pig, 1F, asbestosStack);
                check(HbmLivingAttachments.getAsbestos(pig) == 1, "asbestos with an empty gas_mask gave " + HbmLivingAttachments.getAsbestos(pig) + ", expected 1");

                ItemStack mask = maskWith(level, NtmItems.GAS_MASK.get(), NtmItems.GAS_MASK_FILTER.get(), 0);
                pig.setItemSlot(EquipmentSlot.HEAD, mask);
                HbmLivingAttachments.setAsbestos(pig, 0);
                HazardRegistry.ASBESTOS.onUpdate(pig, 1F, asbestosStack);
                check(HbmLivingAttachments.getAsbestos(pig) == 0, "asbestos rose to " + HbmLivingAttachments.getAsbestos(pig) + " under gas_mask + gas_mask_filter");
                check(filterDamage(level, pig) == 1, "asbestos level 1 damaged the filter by " + filterDamage(level, pig) + ", expected 1");
                HazardRegistry.ASBESTOS.onUpdate(pig, 12F, asbestosStack);
                check(filterDamage(level, pig) == 13, "asbestos level 12 brought the filter damage to " + filterDamage(level, pig) + ", expected 13 (no cap on the filter path)");
                check(pig.getItemBySlot(EquipmentSlot.HEAD).getDamageValue() == 0, "the mask itself was damaged");

                // Coal dust: unprotected -> black lung + min(level * count, 10).
                ItemStack coal64 = new ItemStack(NtmItems.POWDER_COAL.get(), 64);
                pig.setItemSlot(EquipmentSlot.HEAD, ItemStack.EMPTY);
                HbmLivingAttachments.setBlackLung(pig, 0);
                HazardRegistry.COAL.onUpdate(pig, 1F, new ItemStack(NtmItems.POWDER_COAL.get(), 3));
                check(HbmLivingAttachments.getBlackLung(pig) == 3, "coal level 1 x 3 without a mask gave " + HbmLivingAttachments.getBlackLung(pig) + ", expected 3");
                HazardRegistry.COAL.onUpdate(pig, 1F, coal64);
                check(HbmLivingAttachments.getBlackLung(pig) == 13, "coal level 1 x 64 without a mask gave +" + (HbmLivingAttachments.getBlackLung(pig) - 3) + ", expected +10");

                // mask_rag gives PARTICLE_COARSE: no black lung; with 64 items nextInt(max(65 - 64, 1)) == 0 always, so the filter path runs and finds
                // no IGasMask filter on the rag mask: nothing is damaged and nothing is thrown.
                ItemStack rag = new ItemStack(NtmItems.MASK_RAG.get());
                pig.setItemSlot(EquipmentSlot.HEAD, rag);
                HbmLivingAttachments.setBlackLung(pig, 0);
                HazardRegistry.COAL.onUpdate(pig, 1F, coal64);
                check(HbmLivingAttachments.getBlackLung(pig) == 0, "black lung rose to " + HbmLivingAttachments.getBlackLung(pig) + " under mask_rag");
                check(pig.getItemBySlot(EquipmentSlot.HEAD).getDamageValue() == 0 && !pig.getItemBySlot(EquipmentSlot.HEAD).has(DataComponents.CUSTOM_DATA), "the filter path changed mask_rag");

                // gas_mask_olde + gas_mask_filter_rag also gives PARTICLE_COARSE; the always-taken random path damages that IGasMask filter by (int) level.
                pig.setItemSlot(EquipmentSlot.HEAD, maskWith(level, NtmItems.GAS_MASK_OLDE.get(), NtmItems.GAS_MASK_FILTER_RAG.get(), 0));
                HazardRegistry.COAL.onUpdate(pig, 2F, coal64);
                check(HbmLivingAttachments.getBlackLung(pig) == 0, "black lung rose under gas_mask_olde + gas_mask_filter_rag");
                check(filterDamage(level, pig) == 2, "coal level 2 x 64 damaged the rag filter by " + filterDamage(level, pig) + ", expected 2");

                // gas_monoxide (entityInside called through the block state): GAS_MONOXIDE -> filter + 1, no damage; otherwise hurt by the monoxide source.
                BlockPos pos = helper.absolutePos(new BlockPos(8, 1, 8));
                BlockState monoxide = NtmBlocks.GAS_MONOXIDE.get().defaultBlockState();
                pig.setHealth(pig.getMaxHealth());
                pig.invulnerableTime = 0;
                pig.setItemSlot(EquipmentSlot.HEAD, maskWith(level, NtmItems.GAS_MASK_MONO.get(), NtmItems.GAS_MASK_FILTER_MONO.get(), 0));
                monoxide.entityInside(level, pos, pig);
                check(pig.getHealth() == pig.getMaxHealth(), "gas_mask_mono + gas_mask_filter_mono took monoxide damage: health " + pig.getHealth());
                check(filterDamage(level, pig) == 1, "monoxide damaged the catalytic filter by " + filterDamage(level, pig) + ", expected 1");
                // gas_mask_mono + gas_mask_filter (no GAS_MONOXIDE) is hurt by the full 1: the monoxide source bypasses armor and is absolute
                // (ModDamageSource.java:39 setDamageIsAbsolute().setDamageBypassesArmor()), so the mask's 2 armor points absorb nothing.
                pig.setItemSlot(EquipmentSlot.HEAD, maskWith(level, NtmItems.GAS_MASK_MONO.get(), NtmItems.GAS_MASK_FILTER.get(), 0));
                monoxide.entityInside(level, pos, pig);
                LOGGER.info("{} hazards: gas_mask_mono + gas_mask_filter in monoxide, health {} of {}", TAG, pig.getHealth(), pig.getMaxHealth());
                check(pig.getHealth() == pig.getMaxHealth() - 1F, "gas_mask_mono + gas_mask_filter in monoxide: health " + pig.getHealth() + ", expected " + (pig.getMaxHealth() - 1F) + " (armor bypassed)");
                check(pig.getLastDamageSource() != null && pig.getLastDamageSource().is(NtmDamageTypes.MONOXIDE), "the damage source is " + pig.getLastDamageSource());
                check(filterDamage(level, pig) == 0, "the unrelated filter was damaged by monoxide");
                // No head protection at all.
                pig.setHealth(pig.getMaxHealth());
                pig.invulnerableTime = 0;
                pig.setItemSlot(EquipmentSlot.HEAD, ItemStack.EMPTY);
                monoxide.entityInside(level, pos, pig);
                check(pig.getHealth() == pig.getMaxHealth() - 1F, "an unprotected pig in monoxide: health " + pig.getHealth() + ", expected " + (pig.getMaxHealth() - 1F));

                // gas_radon: hasAllProtection(PARTICLE_FINE) -> filter + 1, nothing else; otherwise RAD_BYPASS 0.05 and asbestos + 1.
                BlockState radon = NtmBlocks.GAS_RADON.get().defaultBlockState();
                pig.setItemSlot(EquipmentSlot.HEAD, maskWith(level, NtmItems.GAS_MASK.get(), NtmItems.GAS_MASK_FILTER.get(), 0));
                resetRad(pig);
                radon.entityInside(level, pos, pig);
                check(filterDamage(level, pig) == 1, "radon damaged the filter by " + filterDamage(level, pig) + ", expected 1");
                check(HbmLivingAttachments.getRadiation(pig) == 0F && HbmLivingAttachments.getRadEnv(pig) == 0F && HbmLivingAttachments.getAsbestos(pig) == 0,
                        "gas_mask + gas_mask_filter in radon: radiation " + HbmLivingAttachments.getRadiation(pig) + ", asbestos " + HbmLivingAttachments.getAsbestos(pig));
                pig.setItemSlot(EquipmentSlot.HEAD, new ItemStack(NtmItems.GAS_MASK.get()));
                resetRad(pig);
                radon.entityInside(level, pos, pig);
                check(Math.abs(HbmLivingAttachments.getRadiation(pig) - 0.05F) <= 1e-6F, "gas_mask without a filter in radon: " + HbmLivingAttachments.getRadiation(pig) + " rad, expected 0.05");
                check(HbmLivingAttachments.getAsbestos(pig) == 1, "gas_mask without a filter in radon: asbestos " + HbmLivingAttachments.getAsbestos(pig) + ", expected 1");
                check(!pig.getItemBySlot(EquipmentSlot.HEAD).has(DataComponents.CUSTOM_DATA), "radon created custom data on an empty gas_mask");
                pig.setItemSlot(EquipmentSlot.HEAD, ItemStack.EMPTY);
            }).run();
        } finally {
            cleanUp(spawned);
        }
        done(helper, "hazards");
    }

    private static void resetRad(Pig pig) {
        HbmLivingAttachments.setRadiation(pig, 0F);
        HbmLivingAttachments.setRadEnv(pig, 0F);
        HbmLivingAttachments.setAsbestos(pig, 0);
    }

    // 3. Filter right-click (ItemFilter.java:22-72): empty head -> nothing; a non-IGasMask helmet without mods -> nothing (installFilterOn returns the
    // filter); an IGasMask -> the copy goes into the mask, the hand gets the previous filter or nothing (stackSize = 0), the screw sound plays.
    @GameTest(template = TEMPLATE, batch = "gasmask_filter_use", timeoutTicks = 100)
    public static void filter_use(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            FakePlayer player = fakePlayer(helper);
            InteractionHand hand = InteractionHand.MAIN_HAND;

            // Empty head slot.
            ItemStack filter = new ItemStack(NtmItems.GAS_MASK_FILTER.get());
            player.setItemInHand(hand, filter);
            use(player, hand);
            check(player.getItemInHand(hand).is(NtmItems.GAS_MASK_FILTER.get()) && player.getItemInHand(hand).getCount() == 1, "empty head: the hand holds " + player.getItemInHand(hand));
            check(player.getItemBySlot(EquipmentSlot.HEAD).isEmpty(), "empty head: something was equipped");

            // Diamond helmet: not an IGasMask, no mods.
            ItemStack diamond = new ItemStack(Items.DIAMOND_HELMET);
            player.setItemSlot(EquipmentSlot.HEAD, diamond);
            use(player, hand);
            check(player.getItemInHand(hand).is(NtmItems.GAS_MASK_FILTER.get()) && player.getItemInHand(hand).getCount() == 1, "diamond helmet: the hand holds " + player.getItemInHand(hand));
            check(!player.getItemBySlot(EquipmentSlot.HEAD).has(DataComponents.CUSTOM_DATA), "diamond helmet: data was written to the helmet");

            // gas_mask worn, first filter (damaged: the damage travels with it).
            player.setItemSlot(EquipmentSlot.HEAD, new ItemStack(NtmItems.GAS_MASK.get()));
            ItemStack first = new ItemStack(NtmItems.GAS_MASK_FILTER.get());
            first.setDamageValue(4321);
            player.setItemInHand(hand, first);
            use(player, hand);
            ItemStack installed = ArmorUtil.getGasMaskFilter(level, player.getItemBySlot(EquipmentSlot.HEAD));
            check(installed.is(NtmItems.GAS_MASK_FILTER.get()) && installed.getDamageValue() == 4321 && installed.getCount() == 1, "the mask holds " + installed + " damage " + installed.getDamageValue() + ", expected gas_mask_filter at 4321");
            check(player.getItemInHand(hand).isEmpty(), "after the first install the hand holds " + player.getItemInHand(hand));

            // A second filter of another kind swaps: the mask holds the new one, the hand the old one with its damage.
            ItemStack second = new ItemStack(NtmItems.GAS_MASK_FILTER_COMBO.get());
            second.setDamageValue(7);
            player.setItemInHand(hand, second);
            use(player, hand);
            ItemStack now = ArmorUtil.getGasMaskFilter(level, player.getItemBySlot(EquipmentSlot.HEAD));
            check(now.is(NtmItems.GAS_MASK_FILTER_COMBO.get()) && now.getDamageValue() == 7, "after the swap the mask holds " + now + " damage " + now.getDamageValue());
            ItemStack back = player.getItemInHand(hand);
            check(back.is(NtmItems.GAS_MASK_FILTER.get()) && back.getDamageValue() == 4321 && back.getCount() == 1, "after the swap the hand holds " + back + " damage " + back.getDamageValue() + ", expected gas_mask_filter at 4321");
            check(player.getItemBySlot(EquipmentSlot.HEAD).getDamageValue() == 0, "installing damaged the mask");

            // The other three masks take a filter too (isFilterApplicable is always true).
            for(Item maskItem : new Item[] { NtmItems.GAS_MASK_M65.get(), NtmItems.GAS_MASK_MONO.get(), NtmItems.GAS_MASK_OLDE.get() }) {
                player.setItemSlot(EquipmentSlot.HEAD, new ItemStack(maskItem));
                player.setItemInHand(hand, new ItemStack(NtmItems.GAS_MASK_FILTER_RAG.get()));
                use(player, hand);
                check(ArmorUtil.getGasMaskFilter(level, player.getItemBySlot(EquipmentSlot.HEAD)).is(NtmItems.GAS_MASK_FILTER_RAG.get()), BuiltInRegistries.ITEM.getKey(maskItem) + " did not take the filter");
                check(player.getItemInHand(hand).isEmpty(), BuiltInRegistries.ITEM.getKey(maskItem) + ": the hand holds " + player.getItemInHand(hand));
            }
            // Creative, empty mask: 1.7.10 ItemInWorldManager.tryUseItem restored the stack size of the returned stack (stackSize 0 -> 1), so the filter
            // stays in hand while the mask gets a copy (main-agent fix F1 in installFilterOn).
            player.setGameMode(GameType.CREATIVE);
            check(player.hasInfiniteMaterials(), "the creative FakePlayer has no infinite materials");
            player.setItemSlot(EquipmentSlot.HEAD, new ItemStack(NtmItems.GAS_MASK.get()));
            ItemStack creativeFilter = new ItemStack(NtmItems.GAS_MASK_FILTER_MONO.get());
            creativeFilter.setDamageValue(12);
            player.setItemInHand(hand, creativeFilter);
            use(player, hand);
            ItemStack creativeInstalled = ArmorUtil.getGasMaskFilter(level, player.getItemBySlot(EquipmentSlot.HEAD));
            check(creativeInstalled.is(NtmItems.GAS_MASK_FILTER_MONO.get()) && creativeInstalled.getDamageValue() == 12, "creative: the mask holds " + creativeInstalled);
            ItemStack creativeHand = player.getItemInHand(hand);
            check(creativeHand.is(NtmItems.GAS_MASK_FILTER_MONO.get()) && creativeHand.getCount() == 1 && creativeHand.getDamageValue() == 12, "creative: the hand holds " + creativeHand + ", expected the filter kept");
            player.setGameMode(GameType.SURVIVAL);

            // The sound (level.playSound with gasmask_screw) has no observable effect on a server without players in range: only "it did not throw".
            LOGGER.info("{} filter_use: the gasmask_screw sound is not observable in the GameTest, the install calls completed without an exception", TAG);
        }).run();
        done(helper, "filter_use");
    }

    // 4. Sneak right-click with a mask (ArmorGasMask.java:193-212): a filter is taken out into the inventory or dropped; without a filter the call falls
    // through to super (equip).
    @GameTest(template = TEMPLATE, batch = "gasmask_mask_sneak_remove", timeoutTicks = 100)
    public static void mask_sneak_remove(GameTestHelper helper) {
        List<Entity> spawned = new ArrayList<>();
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                FakePlayer player = fakePlayer(helper);
                InteractionHand hand = InteractionHand.MAIN_HAND;
                player.setShiftKeyDown(true);
                check(player.isShiftKeyDown(), "the player is not sneaking");

                // With room: the filter goes to the inventory, the mask stays in the hand without hfr_Filter, nothing is equipped.
                ItemStack mask = maskWith(level, NtmItems.GAS_MASK.get(), NtmItems.GAS_MASK_FILTER.get(), 55);
                player.setItemInHand(hand, mask);
                use(player, hand);
                ItemStack held = player.getItemInHand(hand);
                check(held.is(NtmItems.GAS_MASK.get()), "the hand holds " + held + " after the sneak use");
                check(!TagsUtil.getCustomData(held).contains(ArmorUtil.FILTER_KEY), "the mask still has hfr_Filter: " + TagsUtil.getCustomData(held));
                check(player.getItemBySlot(EquipmentSlot.HEAD).isEmpty(), "the sneak use with a filter equipped the mask");
                int slot = player.getInventory().findSlotMatchingItem(new ItemStack(NtmItems.GAS_MASK_FILTER.get()));
                ItemStack given = ItemStack.EMPTY;
                for(int i = 0; i < player.getInventory().getContainerSize(); i++) {
                    if(player.getInventory().getItem(i).is(NtmItems.GAS_MASK_FILTER.get())) given = player.getInventory().getItem(i);
                }
                check(given.is(NtmItems.GAS_MASK_FILTER.get()) && given.getDamageValue() == 55, "the inventory has " + given + " damage " + given.getDamageValue() + " (slot " + slot + "), expected the filter at 55");

                // Full inventory: the filter is dropped as an ItemEntity near the player.
                player.getInventory().clearContent();
                ItemStack second = maskWith(level, NtmItems.GAS_MASK_M65.get(), NtmItems.GAS_MASK_FILTER_MONO.get(), 9);
                player.setItemInHand(hand, second);
                for(int i = 0; i < player.getInventory().items.size(); i++) {
                    if(i != player.getInventory().selected) player.getInventory().items.set(i, new ItemStack(Items.COBBLESTONE, 64));
                }
                AABB box = new AABB(player.blockPosition()).inflate(4);
                int before = level.getEntitiesOfClass(ItemEntity.class, box).size();
                use(player, hand);
                List<ItemEntity> drops = level.getEntitiesOfClass(ItemEntity.class, box, e -> e.getItem().is(NtmItems.GAS_MASK_FILTER_MONO.get()));
                spawned.addAll(level.getEntitiesOfClass(ItemEntity.class, box));
                check(drops.size() == 1, "full inventory: " + drops.size() + " dropped filters near the player (" + before + " items before)");
                check(drops.get(0).getItem().getDamageValue() == 9 && drops.get(0).getItem().getCount() == 1, "the dropped filter is " + drops.get(0).getItem() + " damage " + drops.get(0).getItem().getDamageValue());
                check(drops.get(0).position().distanceTo(player.position()) < 3D, "the filter dropped " + drops.get(0).position().distanceTo(player.position()) + " blocks away");
                check(!TagsUtil.getCustomData(player.getItemInHand(hand)).contains(ArmorUtil.FILTER_KEY), "full inventory: the mask kept its filter");

                // Without a filter, sneaking falls through to ArmorItem.use: the mask moves to the empty head slot, the hand is emptied.
                player.getInventory().clearContent();
                player.setItemInHand(hand, new ItemStack(NtmItems.GAS_MASK.get()));
                use(player, hand);
                check(player.getItemBySlot(EquipmentSlot.HEAD).is(NtmItems.GAS_MASK.get()), "without a filter the sneak use did not equip the mask, the head holds " + player.getItemBySlot(EquipmentSlot.HEAD));
                check(player.getItemInHand(hand).isEmpty(), "without a filter the hand still holds " + player.getItemInHand(hand));
                LOGGER.info("{} mask_sneak_remove: without a filter the sneak use equipped the mask into the empty head slot and emptied the hand", TAG);
                player.setShiftKeyDown(false);
            }).run();
        } finally {
            cleanUp(spawned);
        }
        done(helper, "mask_sneak_remove");
    }

    // 5. Filter wear on a worn mask (ArmorUtil.java:310-353: damage accumulates, setItemDamage is not clamped and the filter is removed only when the
    // damage is strictly above the maximum, 20,000 for every filter, ItemFilter.java:17)
    @GameTest(template = TEMPLATE, batch = "gasmask_filter_wear", timeoutTicks = 100)
    public static void filter_wear(GameTestHelper helper) {
        List<Entity> spawned = new ArrayList<>();
        try {
            guard(() -> {
                ServerLevel level = helper.getLevel();
                Pig pig = pig(helper, spawned, new Vec3(8.5, 1, 8.5));
                pig.setItemSlot(EquipmentSlot.HEAD, maskWith(level, NtmItems.GAS_MASK.get(), NtmItems.GAS_MASK_FILTER.get(), 0));
                ArmorUtil.damageGasMaskFilter(pig, 3);
                ArmorUtil.damageGasMaskFilter(pig, 4);
                check(filterDamage(level, pig) == 7, "3 + 4 gave " + filterDamage(level, pig));

                pig.setItemSlot(EquipmentSlot.HEAD, maskWith(level, NtmItems.GAS_MASK.get(), NtmItems.GAS_MASK_FILTER.get(), 19990));
                ArmorUtil.damageGasMaskFilter(pig, 10);
                ItemStack atMax = ArmorUtil.getGasMaskFilter(level, pig.getItemBySlot(EquipmentSlot.HEAD));
                check(atMax.is(NtmItems.GAS_MASK_FILTER.get()) && atMax.getDamageValue() == 20000, "at exactly 20,000 the filter is " + atMax + " damage " + atMax.getDamageValue());
                ArmorUtil.damageGasMaskFilter(pig, 1);
                ItemStack gone = ArmorUtil.getGasMaskFilter(level, pig.getItemBySlot(EquipmentSlot.HEAD));
                check(gone.isEmpty(), "at 20,001 the filter is still " + gone + " damage " + gone.getDamageValue());
                check(!TagsUtil.getCustomData(pig.getItemBySlot(EquipmentSlot.HEAD)).contains(ArmorUtil.FILTER_KEY), "hfr_Filter survived the removal");
                check(pig.getItemBySlot(EquipmentSlot.HEAD).is(NtmItems.GAS_MASK.get()) && pig.getItemBySlot(EquipmentSlot.HEAD).getDamageValue() == 0, "the mask itself changed");

                // A jump over the maximum in one call removes it as well; the mask's own IGasMask.damageFilter does the same.
                ItemStack m65 = maskWith(level, NtmItems.GAS_MASK_M65.get(), NtmItems.GAS_MASK_FILTER_PISS.get(), 100);
                pig.setItemSlot(EquipmentSlot.HEAD, m65);
                ((IGasMask) NtmItems.GAS_MASK_M65.get()).damageFilter(pig.getItemBySlot(EquipmentSlot.HEAD), pig, 19900);
                check(filterDamage(level, pig) == 20000, "IGasMask.damageFilter 100 + 19,900 gave " + filterDamage(level, pig));
                ((IGasMask) NtmItems.GAS_MASK_M65.get()).damageFilter(pig.getItemBySlot(EquipmentSlot.HEAD), pig, 500);
                check(ArmorUtil.getGasMaskFilter(level, pig.getItemBySlot(EquipmentSlot.HEAD)).isEmpty(), "IGasMask.damageFilter past the maximum kept the filter");
                pig.setItemSlot(EquipmentSlot.HEAD, ItemStack.EMPTY);
            }).run();
        } finally {
            cleanUp(spawned);
        }
        done(helper, "filter_wear");
    }

    // 6. Persistence (ArmorUtil.java:250-308: the filter lives in the mask's tag under the filter key, NEO hfr_Filter in custom data) and removeMod keeping
    // every other key (ArmorModHandler.java:101-119) on a real IGasMask
    @GameTest(template = TEMPLATE, batch = "gasmask_filter_persistence", timeoutTicks = 100)
    public static void filter_persistence(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            ItemStack mask = maskWith(level, NtmItems.GAS_MASK.get(), NtmItems.GAS_MASK_FILTER_COMBO.get(), 1234);
            check(ArmorUtil.FILTER_KEY.equals("hfr_Filter"), "the filter key is " + ArmorUtil.FILTER_KEY);
            check(TagsUtil.getCustomData(mask).contains("hfr_Filter"), "the custom data has no hfr_Filter: " + TagsUtil.getCustomData(mask));

            Tag saved = mask.save(level.registryAccess());
            Optional<ItemStack> parsed = ItemStack.parse(level.registryAccess(), saved);
            check(parsed.isPresent(), "the saved mask does not parse: " + saved);
            ItemStack loaded = parsed.get();
            check(loaded.is(NtmItems.GAS_MASK.get()) && loaded.getCount() == 1 && loaded.getDamageValue() == 0, "the round trip gave " + loaded);
            ItemStack filter = ArmorUtil.getGasMaskFilter(level, loaded);
            check(filter.is(NtmItems.GAS_MASK_FILTER_COMBO.get()) && filter.getDamageValue() == 1234, "after the round trip the filter is " + filter + " damage " + filter.getDamageValue());
            check(TagsUtil.getCustomData(loaded).equals(TagsUtil.getCustomData(mask)), "the custom data changed in the round trip");
            check(ItemStack.isSameItemSameComponents(loaded, mask), "the round trip changed the components");

            // removeMod on a gas_mask carrying a hand-built mods compound plus hfr_Filter keeps hfr_Filter.
            ItemStack modded = maskWith(level, NtmItems.GAS_MASK.get(), NtmItems.GAS_MASK_FILTER.get(), 77);
            CompoundTag tag = TagsUtil.getCustomData(modded);
            CompoundTag mods = new CompoundTag();
            mods.put(ArmorModHandler.MOD_SLOT_KEY + ArmorModHandler.HELMET_ONLY, new ItemStack(NtmItems.METEOR_CHARM.get()).save(level.registryAccess()));
            tag.put(ArmorModHandler.MOD_COMPOUND_KEY, mods);
            TagsUtil.putCustomData(modded, tag);
            CompoundTag filterBefore = TagsUtil.getCustomData(modded).getCompound(ArmorUtil.FILTER_KEY).copy();
            check(ArmorModHandler.hasMods(modded), "the hand-built mods compound is not seen");
            ArmorModHandler.removeMod(modded, ArmorModHandler.HELMET_ONLY);
            CompoundTag after = TagsUtil.getCustomData(modded);
            check(!after.contains(ArmorModHandler.MOD_COMPOUND_KEY), "the emptied mod compound survived: " + after);
            check(after.getCompound(ArmorUtil.FILTER_KEY).equals(filterBefore), "removeMod changed hfr_Filter: " + after);
            ItemStack kept = ArmorUtil.getGasMaskFilter(level, modded);
            check(kept.is(NtmItems.GAS_MASK_FILTER.get()) && kept.getDamageValue() == 77, "after removeMod the filter is " + kept);
        }).run();
        done(helper, "filter_persistence");
    }

    // 7. Rags (ItemRag.java:17-31: server side, block material water at the floored position -> rag_damp of the same count; :33-38 right click: one
    // fewer rag, one rag_piss into the inventory) and the smelting rows (SmeltingRecipes.java:118-119, 0.1 xp; the 1.7.10 furnace time is 200 ticks).
    @GameTest(template = TEMPLATE, batch = "gasmask_rags", timeoutTicks = 200)
    public static void rags(GameTestHelper helper) {
        ServerLevel level = helper.getLevel();
        List<Entity> spawned = new ArrayList<>();
        BlockPos waterRel = new BlockPos(3, 1, 3);
        BlockPos flowRel = new BlockPos(3, 1, 12);
        BlockPos loggedRel = new BlockPos(12, 1, 12);
        BlockPos dryRel = new BlockPos(12, 1, 3);
        Runnable clear = () -> {
            for(BlockPos rel : new BlockPos[] { waterRel, flowRel, loggedRel }) helper.setBlock(rel, Blocks.AIR);
            cleanUp(spawned);
        };
        ItemEntity[] items = new ItemEntity[4];
        try {
            guard(() -> {
                helper.setBlock(waterRel, Blocks.WATER.defaultBlockState());
                helper.setBlock(flowRel, Blocks.WATER.defaultBlockState().setValue(LiquidBlock.LEVEL, 3));
                helper.setBlock(loggedRel, Blocks.OAK_SLAB.defaultBlockState().setValue(BlockStateProperties.WATERLOGGED, true));
                items[0] = rag(helper, spawned, Vec3.atLowerCornerOf(waterRel).add(0.5, 0.3, 0.5));
                items[1] = rag(helper, spawned, Vec3.atLowerCornerOf(flowRel).add(0.5, 0.05, 0.5));
                items[2] = rag(helper, spawned, Vec3.atLowerCornerOf(loggedRel).add(0.5, 0.6, 0.5));
                items[3] = rag(helper, spawned, Vec3.atLowerCornerOf(dryRel).add(0.5, 0.05, 0.5));
                check(level.getFluidState(items[1].blockPosition()).is(net.minecraft.tags.FluidTags.WATER) && !level.getFluidState(items[1].blockPosition()).isSource(), "the flowing water cell is not flowing water");
            }).run();
        } catch(RuntimeException e) {
            clear.run();
            throw e;
        }
        helper.startSequence().thenExecuteAfter(5, () -> {
            try {
                guard(() -> {
                    check(items[0].getItem().is(NtmItems.RAG_DAMP.get()) && items[0].getItem().getCount() == 5, "in a water source the rag became " + items[0].getItem());
                    check(items[1].getItem().is(NtmItems.RAG_DAMP.get()) && items[1].getItem().getCount() == 5, "in flowing water the rag became " + items[1].getItem());
                    check(items[3].getItem().is(NtmItems.RAG.get()) && items[3].getItem().getCount() == 5, "on dry ground the rag became " + items[3].getItem());
                    // NEO-only (main-notes 11): the fluid state also counts waterlogged blocks; the 1.7.10 game had none.
                    LOGGER.info("{} rags: in a waterlogged slab the rag became {}", TAG, items[2].getItem());
                    check(items[2].getItem().is(NtmItems.RAG_DAMP.get()) && items[2].getItem().getCount() == 5, "in a waterlogged slab the rag became " + items[2].getItem() + " (NEO decision: waterlogged counts)");

                    // Right click through the server's useItem.
                    FakePlayer player = fakePlayer(helper);
                    InteractionHand hand = InteractionHand.MAIN_HAND;
                    player.setItemInHand(hand, new ItemStack(NtmItems.RAG.get(), 3));
                    use(player, hand);
                    check(player.getItemInHand(hand).is(NtmItems.RAG.get()) && player.getItemInHand(hand).getCount() == 2, "after one use the hand holds " + player.getItemInHand(hand));
                    check(count(player, NtmItems.RAG_PISS.get()) == 1, "after one use the inventory has " + count(player, NtmItems.RAG_PISS.get()) + " rag_piss");
                    // Full inventory: NEO drops the rag_piss (the original discards it).
                    for(int i = 0; i < player.getInventory().items.size(); i++) {
                        if(i != player.getInventory().selected) player.getInventory().items.set(i, new ItemStack(Items.COBBLESTONE, 64));
                    }
                    AABB box = new AABB(player.blockPosition()).inflate(4);
                    use(player, hand);
                    check(player.getItemInHand(hand).getCount() == 1, "full inventory: the hand holds " + player.getItemInHand(hand));
                    List<ItemEntity> piss = level.getEntitiesOfClass(ItemEntity.class, box, e -> e.getItem().is(NtmItems.RAG_PISS.get()));
                    spawned.addAll(level.getEntitiesOfClass(ItemEntity.class, box));
                    check(piss.size() == 1 && piss.get(0).getItem().getCount() == 1, "full inventory: " + piss.size() + " dropped rag_piss");
                    // Creative: the count is kept (consume), the rag_piss is still given.
                    player.getInventory().clearContent();
                    player.setGameMode(GameType.CREATIVE);
                    check(player.hasInfiniteMaterials(), "the creative FakePlayer has no infinite materials");
                    player.setItemInHand(hand, new ItemStack(NtmItems.RAG.get(), 3));
                    use(player, hand);
                    check(player.getItemInHand(hand).getCount() == 3, "creative: the hand holds " + player.getItemInHand(hand));
                    LOGGER.info("{} rags: creative use gave {} rag_piss", TAG, count(player, NtmItems.RAG_PISS.get()));

                    smelts(helper, "rag_damp", "rag_from_smelting_rag_damp", NtmItems.RAG_DAMP.get(), NtmItems.RAG.get());
                    smelts(helper, "rag_piss", "rag_from_smelting_rag_piss", NtmItems.RAG_PISS.get(), NtmItems.RAG.get());
                }).run();
            } finally {
                clear.run();
            }
        }).thenExecute(passed("rags")).thenSucceed();
    }

    private static ItemEntity rag(GameTestHelper helper, List<Entity> spawned, Vec3 rel) {
        Vec3 abs = helper.absoluteVec(rel);
        ItemEntity entity = new ItemEntity(helper.getLevel(), abs.x, abs.y, abs.z, new ItemStack(NtmItems.RAG.get(), 5));
        entity.setDeltaMovement(Vec3.ZERO);
        entity.setPickUpDelay(32767);
        helper.getLevel().addFreshEntity(entity);
        spawned.add(entity);
        return entity;
    }

    private static int count(FakePlayer player, Item item) {
        int n = 0;
        for(int i = 0; i < player.getInventory().getContainerSize(); i++) {
            ItemStack stack = player.getInventory().getItem(i);
            if(stack.is(item)) n += stack.getCount();
        }
        return n;
    }

    // 8. Recipes through the RecipeManager (ArmorRecipes.java:154-161, ConsumableRecipes.java:217-221, CraftingManager.java:839) and the assembly row
    // (AssemblyMachineRecipes.java:122-123: setup(50, 100), filter_coal x1 from coal dust x4, string x2, paper x1).
    @GameTest(template = TEMPLATE, batch = "gasmask_recipes", timeoutTicks = 100)
    public static void recipes(GameTestHelper helper) {
        guard(() -> {
            ItemStack steel = s(NtmItems.PLATE_STEEL.get()), pane = s(Items.GLASS_PANE), ironPlate = s(NtmItems.PLATE_IRON.get());
            ItemStack rubber = s(NtmItems.INGOT_RUBBER.get());
            String[] mask = { "PPP", "GPG", " F " };
            crafts(helper, "gas_mask", "gas_mask", shaped(mask, Map.of('P', steel, 'G', pane, 'F', ironPlate)), NtmItems.GAS_MASK.get(), 1);
            crafts(helper, "gas_mask_m65", "gas_mask_m65", shaped(mask, Map.of('P', rubber, 'G', pane, 'F', ironPlate)), NtmItems.GAS_MASK_M65.get(), 1);
            crafts(helper, "gas_mask_m65 with biorubber", "gas_mask_m65", shaped(mask, Map.of('P', s(NtmItems.INGOT_BIORUBBER.get()), 'G', pane, 'F', ironPlate)), NtmItems.GAS_MASK_M65.get(), 1);
            crafts(helper, "gas_mask_olde", "gas_mask_olde", shaped(mask, Map.of('P', s(Items.LEATHER), 'G', pane, 'F', s(Items.IRON_INGOT))), NtmItems.GAS_MASK_OLDE.get(), 1);
            crafts(helper, "gas_mask_mono", "gas_mask_mono", shaped(new String[] { " P ", "PPP", " F " }, Map.of('P', rubber, 'F', ironPlate)), NtmItems.GAS_MASK_MONO.get(), 1);
            notCrafting(helper, "gas_mask with an iron ingot instead of the iron plate", shaped(mask, Map.of('P', steel, 'G', pane, 'F', s(Items.IRON_INGOT))), NtmItems.GAS_MASK.get());
            notCrafting(helper, "gas_mask_olde with an iron plate instead of the ingot", shaped(mask, Map.of('P', s(Items.LEATHER), 'G', pane, 'F', ironPlate)), NtmItems.GAS_MASK_OLDE.get());
            notCrafting(helper, "gas_mask with glass blocks", shaped(mask, Map.of('P', steel, 'G', s(Items.GLASS), 'F', ironPlate)), NtmItems.GAS_MASK.get());

            crafts(helper, "mask_rag", "mask_rag", shaped(new String[] { "RRR" }, Map.of('R', s(NtmItems.RAG_DAMP.get()))), NtmItems.MASK_RAG.get(), 1);
            crafts(helper, "mask_piss", "mask_piss", shaped(new String[] { "RRR" }, Map.of('R', s(NtmItems.RAG_PISS.get()))), NtmItems.MASK_PISS.get(), 1);
            notCrafting(helper, "mask_rag from dry rags", shaped(new String[] { "RRR" }, Map.of('R', s(NtmItems.RAG.get()))), NtmItems.MASK_RAG.get());

            crafts(helper, "gas_mask_filter", "gas_mask_filter", shaped(new String[] { "I", "F" }, Map.of('I', ironPlate, 'F', s(NtmItems.FILTER_COAL.get()))), NtmItems.GAS_MASK_FILTER.get(), 1);
            crafts(helper, "gas_mask_filter_mono", "gas_mask_filter_mono", shaped(new String[] { "ZZZ", "ZCZ", "ZZZ" }, Map.of('Z', s(NtmItems.NUGGET_ZIRCONIUM.get()), 'C', s(NtmItems.CATALYST_CLAY.get()))), NtmItems.GAS_MASK_FILTER_MONO.get(), 1);
            crafts(helper, "gas_mask_filter_combo", "gas_mask_filter_combo", shaped(new String[] { "ZCZ", "CFC", "ZCZ" }, Map.of('Z', s(NtmItems.INGOT_ZIRCONIUM.get()), 'C', s(NtmItems.CATALYST_CLAY.get()),
                    'F', s(NtmItems.GAS_MASK_FILTER.get()))), NtmItems.GAS_MASK_FILTER_COMBO.get(), 1);
            notCrafting(helper, "gas_mask_filter_combo with zirconium nuggets", shaped(new String[] { "ZCZ", "CFC", "ZCZ" }, Map.of('Z', s(NtmItems.NUGGET_ZIRCONIUM.get()), 'C', s(NtmItems.CATALYST_CLAY.get()),
                    'F', s(NtmItems.GAS_MASK_FILTER.get()))), NtmItems.GAS_MASK_FILTER_COMBO.get());
            notCrafting(helper, "gas_mask_filter_mono with zirconium ingots", shaped(new String[] { "ZZZ", "ZCZ", "ZZZ" }, Map.of('Z', s(NtmItems.INGOT_ZIRCONIUM.get()), 'C', s(NtmItems.CATALYST_CLAY.get()))), NtmItems.GAS_MASK_FILTER_MONO.get());
            crafts(helper, "gas_mask_filter_rag", "gas_mask_filter_rag", shaped(new String[] { "I", "F" }, Map.of('I', s(Items.IRON_INGOT), 'F', s(NtmItems.RAG_DAMP.get()))), NtmItems.GAS_MASK_FILTER_RAG.get(), 1);
            crafts(helper, "gas_mask_filter_piss", "gas_mask_filter_piss", shaped(new String[] { "I", "F" }, Map.of('I', s(Items.IRON_INGOT), 'F', s(NtmItems.RAG_PISS.get()))), NtmItems.GAS_MASK_FILTER_PISS.get(), 1);
            notCrafting(helper, "gas_mask_filter_rag with an iron plate", shaped(new String[] { "I", "F" }, Map.of('I', ironPlate, 'F', s(NtmItems.RAG_DAMP.get()))), NtmItems.GAS_MASK_FILTER_RAG.get());

            // rag x4 "SW","WS": 1.7.10 ShapedOreRecipe turns Blocks.wool into a wildcard stack, so every colour works.
            for(Item wool : new Item[] { Items.WHITE_WOOL, Items.RED_WOOL, Items.BLACK_WOOL }) {
                crafts(helper, "rag with " + BuiltInRegistries.ITEM.getKey(wool).getPath(), "rag", shaped(new String[] { "SW", "WS" }, Map.of('S', s(Items.STRING), 'W', s(wool))), NtmItems.RAG.get(), 4);
            }
            Map<Character, ItemStack> mixed = new HashMap<>(Map.of('S', s(Items.STRING), 'W', s(Items.RED_WOOL)));
            CraftingInput mixedInput = CraftingInput.of(2, 2, List.of(s(Items.STRING), s(Items.LIME_WOOL), s(Items.RED_WOOL), s(Items.STRING)));
            crafts(helper, "rag with two colours", "rag", mixedInput, NtmItems.RAG.get(), 4);
            mixed.put('S', s(Items.WHITE_CARPET));
            notCrafting(helper, "rag with carpet instead of string", shaped(new String[] { "SW", "WS" }, mixed), NtmItems.RAG.get());

            GenericRecipe r = AssemblyMachineRecipes.INSTANCE.recipeNameMap.get("ass.filtercoal");
            check(r != null, "ass.filtercoal is not registered");
            check(r.duration == 50 && r.power == 100L, "ass.filtercoal takes " + r.duration + " ticks at " + r.power + ", expected 50 / 100");
            check(r.outputItem != null && r.outputItem.length == 1, "outputs " + Arrays.toString(r.outputItem));
            ItemStack out = r.outputItem[0].getSingle();
            check(out.is(NtmItems.FILTER_COAL.get()) && out.getCount() == 1, "the output is " + out);
            check(r.inputItem != null && r.inputItem.length == 3, "inputs " + Arrays.toString(r.inputItem));
            ItemStack[] want = { new ItemStack(NtmItems.POWDER_COAL.get(), 4), new ItemStack(Items.STRING, 2), new ItemStack(Items.PAPER, 1) };
            for(int i = 0; i < 3; i++) {
                AStack in = r.inputItem[i];
                check(in.stacksize == want[i].getCount(), "input " + i + " count " + in.stacksize + ", expected " + want[i].getCount());
                check(in.matchesRecipe(want[i], true), "input " + i + " " + in + " does not match " + want[i]);
            }
            check(r.inputItem[0] instanceof ComparableStack c0 && c0.item == NtmItems.POWDER_COAL.get(), "input 0 is " + r.inputItem[0]);
            check(!r.inputItem[0].matchesRecipe(new ItemStack(Items.COAL, 4), true), "input 0 accepts coal items, expected coal dust");
            LOGGER.info("{} recipes: ass.filtercoal {} ticks / {} HE, 4 coal dust, 2 string, 1 paper -> 1 filter_coal", TAG, r.duration, r.power);
        }).run();
        done(helper, "recipes");
    }

    // 9. Items, durability and the armor material (ModItemsArmor.java:22-32: masks ArmorMaterial.IRON helmet, rag masks HBM_RAGS 150 {1,1,1,1} enchant 0
    // repaired with rag; ItemFilter.java:16-20: 20,000, stack 1; ModItems.java:2398-2401 plain stacks; 1.7.10 helmet durability 11 x factor:
    // IRON 15 -> 165, rags 150 -> 1,650; IRON defense helmet 2, enchantability 9; ArmorGasMask.java:88-104 and ModArmor.java:66-71 worn textures)
    @GameTest(template = TEMPLATE, batch = "gasmask_items_and_durability", timeoutTicks = 100)
    public static void items_and_durability(GameTestHelper helper) {
        guard(() -> {
            ServerLevel level = helper.getLevel();
            String[] ids = { "gas_mask", "gas_mask_m65", "gas_mask_mono", "gas_mask_olde", "mask_rag", "mask_piss", "gas_mask_filter", "gas_mask_filter_mono",
                    "gas_mask_filter_combo", "gas_mask_filter_rag", "gas_mask_filter_piss", "filter_coal", "rag", "rag_damp", "rag_piss" };
            for(String id : ids) check(BuiltInRegistries.ITEM.containsKey(id(id)), id + " is not registered");

            for(Item mask : new Item[] { NtmItems.GAS_MASK.get(), NtmItems.GAS_MASK_M65.get(), NtmItems.GAS_MASK_MONO.get(), NtmItems.GAS_MASK_OLDE.get() }) {
                String name = BuiltInRegistries.ITEM.getKey(mask).getPath();
                ItemStack stack = new ItemStack(mask);
                check(mask instanceof IGasMask && mask instanceof GasMaskItem, name + " is not an IGasMask GasMaskItem");
                check(stack.getMaxDamage() == 165, name + " max damage " + stack.getMaxDamage() + ", expected 165");
                check(stack.getMaxStackSize() == 1, name + " stack size " + stack.getMaxStackSize());
                check(((ArmorItem) mask).getType() == ArmorItem.Type.HELMET && ((ArmorItem) mask).getEquipmentSlot() == EquipmentSlot.HEAD, name + " is not a helmet");
                check(((ArmorItem) mask).getMaterial().value() == ArmorMaterials.IRON.value(), name + " is not made of IRON");
                check(armor(stack) == 2D, name + " head armor " + armor(stack) + ", expected 2");
                check(mask.getEnchantmentValue() == 9, name + " enchantment value " + mask.getEnchantmentValue() + ", expected 9");
            }
            texture(NtmItems.GAS_MASK.get(), "textures/models/gas_mask.png");
            texture(NtmItems.GAS_MASK_M65.get(), "textures/models/model_m65.png");
            texture(NtmItems.GAS_MASK_OLDE.get(), "textures/armor/mask_olde.png");
            texture(NtmItems.GAS_MASK_MONO.get(), "textures/models/model_m65_mono.png");
            texture(NtmItems.MASK_RAG.get(), "textures/armor/rag_damp.png");
            texture(NtmItems.MASK_PISS.get(), "textures/armor/rag_piss.png");

            for(Item mask : new Item[] { NtmItems.MASK_RAG.get(), NtmItems.MASK_PISS.get() }) {
                String name = BuiltInRegistries.ITEM.getKey(mask).getPath();
                ItemStack stack = new ItemStack(mask);
                check(!(mask instanceof IGasMask), name + " is an IGasMask");
                check(stack.getMaxDamage() == 1650, name + " max damage " + stack.getMaxDamage() + ", expected 1,650");
                check(stack.getMaxStackSize() == 1, name + " stack size " + stack.getMaxStackSize());
                check(((ArmorItem) mask).getType() == ArmorItem.Type.HELMET, name + " is not a helmet");
                check(((ArmorItem) mask).getMaterial().value() == NtmArmorMaterials.RAGS.get(), name + " is not made of RAGS");
                check(armor(stack) == 1D, name + " head armor " + armor(stack) + ", expected 1");
                check(mask.getEnchantmentValue() == 0, name + " enchantment value " + mask.getEnchantmentValue() + ", expected 0");
                check(mask.isValidRepairItem(stack, s(NtmItems.RAG.get())), name + " is not repaired with rag");
                check(!mask.isValidRepairItem(stack, s(NtmItems.RAG_DAMP.get())), name + " is repaired with rag_damp");
            }
            ArmorMaterial rags = NtmArmorMaterials.RAGS.get();
            ResourceLocation ragsKey = BuiltInRegistries.ARMOR_MATERIAL.getKey(rags);
            check(id("rags").equals(ragsKey), "RAGS is registered as " + ragsKey);
            for(ArmorItem.Type type : new ArmorItem.Type[] { ArmorItem.Type.BOOTS, ArmorItem.Type.LEGGINGS, ArmorItem.Type.CHESTPLATE, ArmorItem.Type.HELMET }) {
                check(rags.getDefense(type) == 1, "RAGS defense " + type + " is " + rags.getDefense(type) + ", expected 1");
            }
            check(rags.enchantmentValue() == 0 && rags.toughness() == 0F && rags.knockbackResistance() == 0F, "RAGS enchant/toughness/knockback " + rags.enchantmentValue() + "/" + rags.toughness() + "/" + rags.knockbackResistance());

            for(Item filter : new Item[] { NtmItems.GAS_MASK_FILTER.get(), NtmItems.GAS_MASK_FILTER_MONO.get(), NtmItems.GAS_MASK_FILTER_COMBO.get(), NtmItems.GAS_MASK_FILTER_RAG.get(),
                    NtmItems.GAS_MASK_FILTER_PISS.get() }) {
                ItemStack stack = new ItemStack(filter);
                String name = BuiltInRegistries.ITEM.getKey(filter).getPath();
                check(stack.getMaxDamage() == 20000, name + " max damage " + stack.getMaxDamage() + ", expected 20,000");
                check(stack.getMaxStackSize() == 1, name + " stack size " + stack.getMaxStackSize());
            }
            for(Item part : new Item[] { NtmItems.RAG.get(), NtmItems.RAG_DAMP.get(), NtmItems.RAG_PISS.get(), NtmItems.FILTER_COAL.get() }) {
                ItemStack stack = new ItemStack(part);
                check(stack.getMaxStackSize() == 64 && !stack.isDamageableItem(), BuiltInRegistries.ITEM.getKey(part) + " stack " + stack.getMaxStackSize() + ", damageable " + stack.isDamageableItem());
            }

            // Tooltip list assembly of a mask (ArmorUtil.java:355-383, ArmorGasMask.java:172-186) on the server, no client rendering: no filter -> RED
            // "no filter" and stop; a filter -> GOLD header, then "  name (pct%)" with (max - damage) * 100 / max in integers; then the blacklist lines.
            Item.TooltipContext context = Item.TooltipContext.of(level);
            List<Component> bare = new ArrayList<>();
            NtmItems.GAS_MASK.get().appendHoverText(new ItemStack(NtmItems.GAS_MASK.get()), context, bare, TooltipFlag.Default.NORMAL);
            check(bare.size() == 3 && key(bare.get(0), "hazard.no_filter", ChatFormatting.RED) && key(bare.get(1), "hazard.never_protects", ChatFormatting.RED)
                    && bare.get(2).getStyle().getColor() == TextColor.fromLegacyFormat(ChatFormatting.DARK_RED), "the bare gas_mask tooltip is " + bare);
            List<Component> lines = new ArrayList<>();
            ItemStack fitted = maskWith(level, NtmItems.GAS_MASK_MONO.get(), NtmItems.GAS_MASK_FILTER.get(), 1234);
            NtmItems.GAS_MASK_MONO.get().appendHoverText(fitted, context, lines, TooltipFlag.Default.NORMAL);
            check(lines.size() >= 6 && key(lines.get(0), "hazard.filter_installed", ChatFormatting.GOLD), "the fitted mono tooltip starts with " + lines);
            String percent = lines.get(1).getString();
            check(percent.startsWith("  ") && percent.endsWith(" (93%)"), "the filter line is '" + percent + "', expected '  <name> (93%)' ((20000 - 1234) * 100 / 20000 = 93)");
            int never = -1;
            for(int i = 0; i < lines.size(); i++) if(lines.get(i).getContents() instanceof TranslatableContents t && t.getKey().equals("hazard.never_protects")) never = i;
            check(never > 1 && lines.size() - never - 1 == 3, "the mono blacklist block has " + (lines.size() - never - 1) + " lines after hazard.never_protects (expected 3): " + lines);

            // no9 unchanged: IRON helmet, its two tooltip lines.
            Item no9 = NtmItems.NO9.get();
            check(((ArmorItem) no9).getMaterial().value() == ArmorMaterials.IRON.value() && ((ArmorItem) no9).getType() == ArmorItem.Type.HELMET, "no9 is not an IRON helmet any more");
            List<Component> no9Lines = new ArrayList<>();
            no9.appendHoverText(new ItemStack(no9), context, no9Lines, TooltipFlag.Default.NORMAL);
            check(no9Lines.size() == 2 && no9Lines.get(0).getString().equals("+0.5 DT") && no9Lines.get(1).getString().equals("Lets you breathe coal, neat!"), "the no9 tooltip is " + no9Lines);
            check(!ArmorRegistry.hazardClasses.containsKey(no9), "no9 gained a hazard registration");
        }).run();
        done(helper, "items_and_durability");
    }

    private static boolean key(Component line, String key, ChatFormatting color) {
        return line.getContents() instanceof TranslatableContents t && t.getKey().equals(key) && line.getStyle().getColor() == TextColor.fromLegacyFormat(color);
    }

    private static void texture(Item item, String path) {
        ResourceLocation tex = item.getArmorTexture(new ItemStack(item), null, EquipmentSlot.HEAD, null, false);
        check(id(path).equals(tex), BuiltInRegistries.ITEM.getKey(item) + " worn texture is " + tex + ", expected " + id(path));
    }

    private static double armor(ItemStack stack) {
        double[] sum = new double[1];
        stack.forEachModifier(EquipmentSlot.HEAD, (attribute, modifier) -> {
            if(attribute.value() == Attributes.ARMOR.value()) sum[0] += modifier.amount();
        });
        return sum[0];
    }

    // Helpers

    /** A real mask with a real filter at the given damage, installed through the production IGasMask.installFilter (ArmorUtil.installGasMaskFilter). */
    private static ItemStack maskWith(ServerLevel level, Item mask, Item filterItem, int damage) {
        ItemStack stack = new ItemStack(mask);
        ItemStack filter = new ItemStack(filterItem);
        filter.setDamageValue(damage);
        ArmorUtil.installGasMaskFilter(level, stack, filter);
        ItemStack check = ArmorUtil.getGasMaskFilter(level, stack);
        check(check.is(filterItem) && check.getDamageValue() == damage, "the test filter was not installed: " + check);
        return stack;
    }

    private static int filterDamage(ServerLevel level, Pig pig) {
        ItemStack filter = ArmorUtil.getGasMaskFilter(level, pig.getItemBySlot(EquipmentSlot.HEAD));
        return filter.isEmpty() ? -1 : filter.getDamageValue();
    }

    private static FakePlayer fakePlayer(GameTestHelper helper) {
        FakePlayer player = new FakePlayer(helper.getLevel(), new GameProfile(UUID.randomUUID(), "gas-mask-test"));
        Vec3 abs = helper.absoluteVec(new Vec3(8.5, 1, 8.5));
        player.moveTo(abs.x, abs.y, abs.z, 0F, 0F);
        player.getInventory().selected = 0;
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
        check(recipe.getExperience() == 0.1F, label + ": experience " + recipe.getExperience() + ", expected 0.1");
        check(recipe.getCookingTime() == 200, label + ": cooking time " + recipe.getCookingTime() + ", expected 200");
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
