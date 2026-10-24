package com.hbm.gametest;

import com.hbm.blocks.NtmBlocks;
import com.hbm.blocks.gas.GasRadonTombBlock;
import com.hbm.config.NtmConfig;
import com.hbm.extprop.HbmLivingAttachments;
import com.hbm.handler.HazmatRegistry;
import com.hbm.items.NtmItems;
import com.hbm.lib.ModEffect;
import com.hbm.main.NuclearTechMod;
import com.hbm.util.ContaminationUtil;
import com.mojang.authlib.GameProfile;
import com.mojang.logging.LogUtils;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.InteractionResultHolder;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.damagesource.DamageTypes;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.crafting.CraftingInput;
import net.minecraft.world.item.crafting.CraftingRecipe;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.RecipeManager;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.ItemLike;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.common.EffectCures;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.common.ModConfigSpec.ConfigValue;
import net.neoforged.neoforge.common.util.FakePlayer;
import net.neoforged.neoforge.event.PlayLevelSoundEvent;
import net.neoforged.neoforge.event.entity.living.LivingDeathEvent;
import net.neoforged.neoforge.gametest.GameTestHolder;
import net.neoforged.neoforge.gametest.PrefixGameTestTemplate;
import org.slf4j.Logger;

import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

import static com.hbm.gametest.SmokeTestSupport.check;
import static com.hbm.gametest.SmokeTestSupport.guard;

/**
 * Server-side tests for Goal26D, the radiation medicine: the pills radx and siox (PillItem), the radaway / iv_empty / iv_blood actions
 * (SimpleConsumableItem), the potionSickness config and its helpers (NtmConfig), the four crafting recipes and the two sound events. Same
 * template and conventions as {@link HazmatSuitGameTests} and {@link GasMaskGameTests}; every test has its own batch.
 * <p>
 * Expected values come from the ORIGINAL, cited beside each group of checks (ItemPill.java:23-26,30-34,57-64,108-134;
 * ItemSimpleConsumable.java:37-47,61-89,113-123,139-141; VersatileConfig.java:17-28; PotionConfig.java:22,40-45; ConsumableRecipes.java:120,127,130,
 * 143,147; HbmLivingProps.java:44-46; EntityDamageUtil.java:509-511; ModItems.java:2828-2829; sounds.json:117-118; GasRadonTombBlock via
 * the NEO class, unchanged by this batch), not from the NEO implementation.
 * <p>
 * Real items and methods: every item is the registered production item; PillItem is driven through use() and finishUsingItem, and
 * SimpleConsumableItem through use(). Where the player is a NeoForge {@link FakePlayer} (a ServerPlayer: not a real player for
 * EntityDamageUtil.isRealPlayer) the right click goes through the real ServerPlayerGameMode.useItem; where the player must be real
 * (iv_empty) it is helper.makeMockPlayer(GameType.SURVIVAL), the only non-fake Player the NEO GameTest server supports
 * (makeMockServerPlayerInLevel crashes it, GOAL21B.md:81), and ServerPlayerGameMode.useItem is replayed by {@link #rightClick}.
 * Stand-ins: effects tick through LivingEntity.tickEffects (reflection, the method LivingEntity.tick runs for the active effects), one
 * call per game tick, because FakePlayer.tick() is empty and the players are not added to the level; the 10-tick eating countdown is
 * not waited out, finishUsingItem / LivingEntity.completeUsingItem (reflection) are called directly.
 * Not evidence: the client (level.isClientSide true is not available in a GameTest: the server gate is checked by source in the
 * verification script), a real client or network, creative-mode inventories of a real client, sound playback (only the sound event
 * that is requested from the level is observed), tooltips as drawn, saved worlds and the 1.7.10 game itself.
 */
@GameTestHolder(NuclearTechMod.MODID)
@PrefixGameTestTemplate(false)
public class RadiationMedicineGameTests {

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final String TEMPLATE = "gametest_empty";
    private static final String TAG = "[hbm-medicine]";

    // Original ItemPill.java:58 (3 * 60 * 20), :34 (5 seconds), :124 (10 ticks); HbmLivingProps.java:46 (2 * 60 * 60 * 20) and ItemPill.java:63 (/ 5);
    // ItemSimpleConsumable.java:140 (140), :116 (-5F), :122 (heal 5F); VersatileConfig.java:19 (x12 in TERRARIA mode, then * 20 ticks)
    private static final int RADX_TICKS = 3 * 60 * 20;
    private static final int USE_TICKS = 10;
    private static final int MAX_BLACKLUNG = 2 * 60 * 60 * 20;
    private static final int SIOX_BLACKLUNG_CAP = MAX_BLACKLUNG / 5;
    private static final int RADAWAY_TICKS = 140;
    private static final float RES_TOL = 1e-5F;

    // Observed through NeoForge events, filled by the listeners that are registered once ({@link #listen()})
    private static final List<String> SOUNDS = new ArrayList<>();
    private static boolean listening;
    private static LivingEntity watched;
    private static final List<DamageSource> DEATHS = new ArrayList<>();

    // 1. radx (ItemPill.java:23-26 ItemFood(0) always edible, :57-59 radx 3 * 60 * 20 plain addPotionEffect, :34 sickness call, :123-134 duration 10 and
    // the sickness gate; HazmatRegistry.java:213-214 RADX +0.2; ContaminationUtil.java:39-40 mod = 10^-resistance; ModItems.java:2828 radx)
    @GameTest(template = TEMPLATE, batch = "medicine_radx_pill", timeoutTicks = 100)
    public static void radx_pill(GameTestHelper helper) {
        String sicknessBefore = NtmConfig.COMMON.POTION_SICKNESS.get();
        FakePlayer player = null;
        try {
            guard(() -> {
                NtmConfig.COMMON.POTION_SICKNESS.set("OFF");
                LOGGER.info("{} radx_pill: potionSickness was \"{}\" at the start, \"OFF\" is set for the default-config checks", TAG, sicknessBefore);
            }).run();
            player = fakePlayer(helper, "medicine-radx");
            FakePlayer p = player;
            guard(() -> {
                ServerLevel level = helper.getLevel();
                Item radx = NtmItems.RADX.get();
                check(radx.getFoodProperties(new ItemStack(radx), p) != null && radx.getFoodProperties(new ItemStack(radx), p).nutrition() == 0
                        && radx.getFoodProperties(new ItemStack(radx), p).canAlwaysEat(), "radx is not an always edible food with 0 nutrition");
                check(radx.getFoodProperties(new ItemStack(radx), p).saturation() == 0F, "radx saturation " + radx.getFoodProperties(new ItemStack(radx), p).saturation());
                check(new ItemStack(radx).getUseDuration(p) == USE_TICKS, "radx use duration " + new ItemStack(radx).getUseDuration(p) + ", expected " + USE_TICKS);

                p.getFoodData().setFoodLevel(10);
                p.getFoodData().setSaturation(3F);
                p.getInventory().setItem(0, new ItemStack(radx, 2));
                check(HazmatRegistry.getResistance(p) == 0F && ContaminationUtil.calculateRadiationMod(p) == 1F, "precondition: no armor, no effect: resistance " + HazmatRegistry.getResistance(p));

                // right click: the real dispatch starts the use (ItemPill.java:131 setItemInUse(stack, 10))
                InteractionResult started = p.gameMode.useItem(p, level, p.getItemInHand(InteractionHand.MAIN_HAND), InteractionHand.MAIN_HAND);
                check(started.consumesAction(), "right click returned " + started);
                check(p.isUsingItem() && p.getUseItem().is(radx) && p.getUseItemRemainingTicks() == USE_TICKS,
                        "after the right click: using " + p.isUsingItem() + ", item " + p.getUseItem() + ", remaining " + p.getUseItemRemainingTicks() + ", expected " + USE_TICKS);
                check(p.getItemInHand(InteractionHand.MAIN_HAND).getCount() == 2, "the stack changed before the pill was eaten: " + p.getItemInHand(InteractionHand.MAIN_HAND));
                check(!p.hasEffect(ModEffect.RADX), "RADX was applied before the pill was eaten");

                // eating: LivingEntity.completeUsingItem is the call that follows the 10 ticks (reflection; the countdown itself is not waited out)
                invoke(p, "completeUsingItem");
                check(!p.isUsingItem(), "still using the item after completeUsingItem");
                check(p.getItemInHand(InteractionHand.MAIN_HAND).is(radx) && p.getItemInHand(InteractionHand.MAIN_HAND).getCount() == 1,
                        "after eating: hand " + p.getItemInHand(InteractionHand.MAIN_HAND) + ", expected 1 radx (2 -> 1)");
                MobEffectInstance effect = p.getEffect(ModEffect.RADX);
                check(effect != null, "no RADX effect after eating");
                check(effect.getDuration() == RADX_TICKS && effect.getAmplifier() == 0, "RADX duration " + effect.getDuration() + " amplifier " + effect.getAmplifier() + ", expected " + RADX_TICKS + " / 0");
                check(!p.hasEffect(ModEffect.POTIONSICKNESS), "potion sickness with the default config (OFF)");
                check(Math.abs(HazmatRegistry.getResistance(p) - 0.2F) <= RES_TOL, "resistance with RADX and no armor: " + HazmatRegistry.getResistance(p) + ", expected 0.2");
                double wantMod = Math.pow(10D, -0.2D);
                check(Math.abs(ContaminationUtil.calculateRadiationMod(p) - wantMod) <= wantMod * 1e-4, "radiation mod " + ContaminationUtil.calculateRadiationMod(p) + ", expected " + wantMod);
                check(p.getFoodData().getFoodLevel() == 10 && p.getFoodData().getSaturationLevel() == 3F,
                        "food level " + p.getFoodData().getFoodLevel() + " saturation " + p.getFoodData().getSaturationLevel() + ", expected 10 / 3.0 unchanged");
                // ordinary effect: milk cures it (default cure set, the original's default curative items)
                check(effect.getCures().contains(EffectCures.MILK), "RADX cannot be cured by milk: " + effect.getCures());

                // a second pill when 1,000 ticks remain: reset to 3,600, not summed (plain addPotionEffect, ItemPill.java:58)
                tickEffects(p, RADX_TICKS - 1000);
                check(p.getEffect(ModEffect.RADX).getDuration() == 1000, "RADX has " + p.getEffect(ModEffect.RADX).getDuration() + " ticks left, expected 1000");
                ItemStack second = p.getItemInHand(InteractionHand.MAIN_HAND);
                second.getItem().finishUsingItem(second, level, p);
                check(p.getEffect(ModEffect.RADX).getDuration() == RADX_TICKS && p.getEffect(ModEffect.RADX).getAmplifier() == 0,
                        "second pill: RADX duration " + p.getEffect(ModEffect.RADX).getDuration() + ", expected " + RADX_TICKS + " (not " + (1000 + RADX_TICKS) + ")");
                check(second.isEmpty(), "second pill left " + second);

                // creative: eaten, effect applied, the stack is not consumed (stack handling of the vanilla food path in NeoForge 1.21; the 1.7.10 vanilla
                // food path had no such exemption, so this line pins the NEO behaviour the handoff states, it is not an original contract)
                p.removeAllEffects();
                p.setGameMode(GameType.CREATIVE);
                p.getInventory().setItem(0, new ItemStack(radx, 2));
                ItemStack creative = p.getItemInHand(InteractionHand.MAIN_HAND);
                creative.getItem().finishUsingItem(creative, level, p);
                check(creative.getCount() == 2, "creative: the stack went from 2 to " + creative.getCount());
                check(p.hasEffect(ModEffect.RADX) && p.getEffect(ModEffect.RADX).getDuration() == RADX_TICKS, "creative: no RADX effect");
            }).run();
        } finally {
            NtmConfig.COMMON.POTION_SICKNESS.set(sicknessBefore);
            if(player != null) reset(player);
            discardItems(helper);
        }
        done(helper, "radx_pill");
    }

    // 2. radaway (ItemSimpleConsumable.java:37-47 the server-gated action, :61-65 decrement + sound + container, :67-75 summing, :77-84 add or drop,
    // :86-89 doRadaway, :139-141 140 ticks; the RADAWAY effect removes (amplifier + 1) rad per tick, HbmLivingProps radiation never below 0;
    // sounds.json:118 hbm:item.radaway; ModItems.java:5958 registration)
    @GameTest(template = TEMPLATE, batch = "medicine_radaway", timeoutTicks = 100)
    public static void radaway(GameTestHelper helper) {
        FakePlayer player = null;
        try {
            player = fakePlayer(helper, "medicine-radaway");
            FakePlayer p = player;
            guard(() -> {
                check(NtmConfig.COMMON.ENABLE_CONTAMINATION.get(), "contamination is disabled in the common config; the radiation checks need it");
                Item radaway = NtmItems.RADAWAY.get(), ivEmpty = NtmItems.IV_EMPTY.get();
                listen();

                // 500 rad, three radaway: use -> 2 left, one iv_empty, RADAWAY amplifier 0 / 140 ticks, the sound
                HbmLivingAttachments.setRadiation(p, 500F);
                check(HbmLivingAttachments.getRadiation(p) == 500F, "precondition: radiation " + HbmLivingAttachments.getRadiation(p));
                p.getInventory().setItem(0, new ItemStack(radaway, 3));
                SOUNDS.clear();
                InteractionResult result = rightClick(p, InteractionHand.MAIN_HAND);
                check(result.consumesAction(), "right click returned " + result);
                check(p.getItemInHand(InteractionHand.MAIN_HAND).is(radaway) && p.getItemInHand(InteractionHand.MAIN_HAND).getCount() == 2, "radaway stack after use: " + p.getItemInHand(InteractionHand.MAIN_HAND) + ", expected 2");
                check(count(p, ivEmpty) == 1 && count(p, radaway) == 2, "inventory after use: iv_empty " + count(p, ivEmpty) + ", radaway " + count(p, radaway));
                MobEffectInstance effect = p.getEffect(ModEffect.RADAWAY);
                check(effect != null && effect.getAmplifier() == 0 && effect.getDuration() == RADAWAY_TICKS, "RADAWAY " + (effect == null ? "missing" : effect.getDuration() + " / " + effect.getAmplifier()) + ", expected 140 / 0");
                check(SOUNDS.equals(List.of("hbmsntm:item.radaway|player|1.0|1.0")), "sounds requested: " + SOUNDS);
                check(HbmLivingAttachments.getRadiation(p) == 500F, "radiation changed on use: " + HbmLivingAttachments.getRadiation(p));

                // 140 effect ticks: radiation 500 -> 360 (each tick -1); the effect then expires and nothing more is removed
                for(int i = 1; i <= RADAWAY_TICKS; i++) {
                    tickEffects(p, 1);
                    check(HbmLivingAttachments.getRadiation(p) == 500F - i, "after tick " + i + " radiation " + HbmLivingAttachments.getRadiation(p) + ", expected " + (500F - i));
                }
                check(HbmLivingAttachments.getRadiation(p) == 360F, "after 140 ticks radiation " + HbmLivingAttachments.getRadiation(p) + ", expected 360");
                check(!p.hasEffect(ModEffect.RADAWAY), "RADAWAY still active after 140 ticks");
                tickEffects(p, 10);
                check(HbmLivingAttachments.getRadiation(p) == 360F, "radiation moved after the effect ended: " + HbmLivingAttachments.getRadiation(p));

                // from 50: stops at 0, never negative
                p.removeAllEffects();
                HbmLivingAttachments.setRadiation(p, 50F);
                p.getInventory().clearContent();
                p.getInventory().setItem(0, new ItemStack(radaway, 1));
                rightClick(p, InteractionHand.MAIN_HAND);
                for(int i = 1; i <= RADAWAY_TICKS; i++) {
                    tickEffects(p, 1);
                    float want = Math.max(50F - i, 0F);
                    check(HbmLivingAttachments.getRadiation(p) == want, "from 50, after tick " + i + " radiation " + HbmLivingAttachments.getRadiation(p) + ", expected " + want);
                }
                check(HbmLivingAttachments.getRadiation(p) == 0F, "from 50 the radiation ended at " + HbmLivingAttachments.getRadiation(p));

                // two uses in a row: 140 + 140 = 280 (the summing helper, :67-75); after 100 ticks another use adds to the 40 left: 180
                p.removeAllEffects();
                p.getInventory().clearContent();
                p.getInventory().setItem(0, new ItemStack(radaway, 4));
                rightClick(p, InteractionHand.MAIN_HAND);
                rightClick(p, InteractionHand.MAIN_HAND);
                check(p.getEffect(ModEffect.RADAWAY).getDuration() == 2 * RADAWAY_TICKS && p.getEffect(ModEffect.RADAWAY).getAmplifier() == 0,
                        "two uses: RADAWAY duration " + p.getEffect(ModEffect.RADAWAY).getDuration() + ", expected 280");
                check(count(p, radaway) == 2 && count(p, ivEmpty) == 2, "two uses: radaway " + count(p, radaway) + " iv_empty " + count(p, ivEmpty));
                tickEffects(p, 2 * RADAWAY_TICKS - 1);
                check(p.hasEffect(ModEffect.RADAWAY) && p.getEffect(ModEffect.RADAWAY).getDuration() == 1, "RADAWAY has " + (p.hasEffect(ModEffect.RADAWAY) ? p.getEffect(ModEffect.RADAWAY).getDuration() : -1) + " ticks left after 279 of 280");
                tickEffects(p, 1);
                check(!p.hasEffect(ModEffect.RADAWAY), "RADAWAY still active after 280 ticks");
                p.removeAllEffects();
                rightClick(p, InteractionHand.MAIN_HAND);
                tickEffects(p, 100);
                check(p.getEffect(ModEffect.RADAWAY).getDuration() == 40, "RADAWAY has " + p.getEffect(ModEffect.RADAWAY).getDuration() + " ticks left, expected 40");
                rightClick(p, InteractionHand.MAIN_HAND);
                check(p.getEffect(ModEffect.RADAWAY).getDuration() == 40 + RADAWAY_TICKS, "summed duration " + p.getEffect(ModEffect.RADAWAY).getDuration() + ", expected 180");

                // full inventory: the iv_empty is dropped next to the player as an item entity (:77-84), the stack still shrinks, the effect is applied
                p.removeAllEffects();
                fill(p);
                p.getInventory().setItem(0, new ItemStack(radaway, 3));
                discardItems(helper);
                rightClick(p, InteractionHand.MAIN_HAND);
                check(p.getItemInHand(InteractionHand.MAIN_HAND).is(radaway) && p.getItemInHand(InteractionHand.MAIN_HAND).getCount() == 2, "full inventory: radaway stack " + p.getItemInHand(InteractionHand.MAIN_HAND) + ", expected 2");
                check(count(p, ivEmpty) == 0, "full inventory: iv_empty went into the inventory: " + count(p, ivEmpty));
                List<ItemEntity> dropped = items(helper);
                check(dropped.size() == 1 && dropped.get(0).getItem().is(ivEmpty) && dropped.get(0).getItem().getCount() == 1, "full inventory: dropped " + describe(dropped) + ", expected one iv_empty");
                check(dropped.get(0).position().distanceTo(p.position()) < 3D, "the dropped iv_empty is " + dropped.get(0).position().distanceTo(p.position()) + " blocks from the player");
                check(p.getEffect(ModEffect.RADAWAY) != null && p.getEffect(ModEffect.RADAWAY).getDuration() == RADAWAY_TICKS, "full inventory: RADAWAY " + p.getEffect(ModEffect.RADAWAY));
                discardItems(helper);

                // the last radaway sits in the selected slot: the container lands in that very slot (the emptied stack is the first free slot); the hand
                // must still hold it after ServerPlayerGameMode.useItem wrote the returned stack back (the re-read in SimpleConsumableItem.use)
                for(boolean full : new boolean[] { false, true }) {
                    p.removeAllEffects();
                    p.getInventory().clearContent();
                    if(full) fill(p);
                    p.getInventory().setItem(0, new ItemStack(radaway, 1));
                    InteractionResult last = rightClick(p, InteractionHand.MAIN_HAND);
                    String label = "last radaway, " + (full ? "full" : "empty") + " rest of the inventory: ";
                    check(last.consumesAction(), label + "result " + last);
                    ItemStack hand = p.getItemInHand(InteractionHand.MAIN_HAND);
                    check(hand.is(ivEmpty) && hand.getCount() == 1, label + "the hand holds " + hand + ", expected 1 iv_empty");
                    check(p.getInventory().getItem(0) == hand && count(p, ivEmpty) == 1 && count(p, radaway) == 0, label + "iv_empty " + count(p, ivEmpty) + " radaway " + count(p, radaway));
                    check(items(helper).isEmpty(), label + "an item entity was dropped: " + describe(items(helper)));
                    check(p.getEffect(ModEffect.RADAWAY) != null && p.getEffect(ModEffect.RADAWAY).getDuration() == RADAWAY_TICKS, label + "RADAWAY " + p.getEffect(ModEffect.RADAWAY));
                }

                // the last radaway while an iv_empty stack waits in another slot: the container merges there, the hand is empty
                p.removeAllEffects();
                p.getInventory().clearContent();
                p.getInventory().setItem(1, new ItemStack(ivEmpty, 5));
                p.getInventory().setItem(0, new ItemStack(radaway, 1));
                rightClick(p, InteractionHand.MAIN_HAND);
                check(p.getItemInHand(InteractionHand.MAIN_HAND).isEmpty() && count(p, ivEmpty) == 6 && p.getInventory().getItem(1).getCount() == 6,
                        "merge: hand " + p.getItemInHand(InteractionHand.MAIN_HAND) + " iv_empty " + count(p, ivEmpty) + " slot 1 " + p.getInventory().getItem(1));

                // off hand: the last radaway in the off hand: the container goes to the main inventory, the off hand is left empty, nothing is duplicated
                p.removeAllEffects();
                p.getInventory().clearContent();
                p.setItemInHand(InteractionHand.OFF_HAND, new ItemStack(radaway, 1));
                InteractionResult off = rightClick(p, InteractionHand.OFF_HAND);
                check(off.consumesAction(), "off hand radaway: result " + off);
                check(p.getItemInHand(InteractionHand.OFF_HAND).isEmpty() && count(p, radaway) == 0 && count(p, ivEmpty) == 1 && p.getInventory().getItem(0).is(ivEmpty),
                        "off hand radaway: off hand " + p.getItemInHand(InteractionHand.OFF_HAND) + ", radaway " + count(p, radaway) + ", iv_empty " + count(p, ivEmpty) + ", slot 0 " + p.getInventory().getItem(0));
                check(p.getEffect(ModEffect.RADAWAY) != null && p.getEffect(ModEffect.RADAWAY).getDuration() == RADAWAY_TICKS && items(helper).isEmpty(), "off hand radaway: effect " + p.getEffect(ModEffect.RADAWAY) + " dropped " + describe(items(helper)));
                // two in the off hand: one is left there, one iv_empty is gained (3 items in total before and after: no duplication)
                p.removeAllEffects();
                p.getInventory().clearContent();
                p.setItemInHand(InteractionHand.OFF_HAND, new ItemStack(radaway, 2));
                rightClick(p, InteractionHand.OFF_HAND);
                check(p.getItemInHand(InteractionHand.OFF_HAND).is(radaway) && p.getItemInHand(InteractionHand.OFF_HAND).getCount() == 1 && count(p, radaway) == 1 && count(p, ivEmpty) == 1,
                        "off hand radaway x2: off hand " + p.getItemInHand(InteractionHand.OFF_HAND) + ", radaway " + count(p, radaway) + ", iv_empty " + count(p, ivEmpty));

                // creative: the container is still given, the stack is not consumed (consume() keeps it; the 1.7.10 tryUseItem restored the size), the effect applies
                p.removeAllEffects();
                p.getInventory().clearContent();
                p.setGameMode(GameType.CREATIVE);
                p.getInventory().setItem(0, new ItemStack(radaway, 3));
                rightClick(p, InteractionHand.MAIN_HAND);
                check(p.getItemInHand(InteractionHand.MAIN_HAND).getCount() == 3 && count(p, ivEmpty) == 1 && p.hasEffect(ModEffect.RADAWAY),
                        "creative: radaway " + p.getItemInHand(InteractionHand.MAIN_HAND) + " iv_empty " + count(p, ivEmpty) + " effect " + p.hasEffect(ModEffect.RADAWAY));
            }).run();
        } finally {
            if(player != null) reset(player);
            discardItems(helper);
        }
        done(helper, "radaway");
    }

    // 3. iv_empty / iv_blood (ItemSimpleConsumable.java:113-118 real players only (EntityDamageUtil.java:509-511), -5 health, onDeath(DamageSource.magic)
    // at 0 or below, container iv_blood, hbm:item.syringe; :120-123 heal 5, container iv_empty, hbm:item.radaway; ModItems.java:5954-5955)
    @GameTest(template = TEMPLATE, batch = "medicine_iv_bags", timeoutTicks = 100)
    public static void iv_bags(GameTestHelper helper) {
        Player real = null;
        FakePlayer fake = null;
        try {
            real = mockPlayer(helper);
            fake = fakePlayer(helper, "medicine-iv");
            Player r = real;
            FakePlayer f = fake;
            guard(() -> {
                Item ivEmpty = NtmItems.IV_EMPTY.get(), ivBlood = NtmItems.IV_BLOOD.get();
                listen();
                check(!(r instanceof FakePlayer) && !(r instanceof ServerPlayer), "the real player is a " + r.getClass());
                check(r.getMaxHealth() == 20F, "max health " + r.getMaxHealth());

                // iv_empty at 20 health: -5, one iv_blood, the stack shrinks, the syringe sound
                r.setHealth(20F);
                r.getInventory().setItem(0, new ItemStack(ivEmpty, 3));
                SOUNDS.clear();
                InteractionResult result = rightClick(r, InteractionHand.MAIN_HAND);
                check(result.consumesAction(), "right click returned " + result);
                check(r.getHealth() == 15F, "iv_empty at 20 health: " + r.getHealth() + ", expected 15");
                check(count(r, ivBlood) == 1 && count(r, ivEmpty) == 2 && r.getItemInHand(InteractionHand.MAIN_HAND).getCount() == 2, "iv_empty use: iv_blood " + count(r, ivBlood) + " iv_empty " + count(r, ivEmpty));
                check(SOUNDS.equals(List.of("hbmsntm:item.syringe|player|1.0|1.0")), "iv_empty sounds requested: " + SOUNDS);
                check(!r.isDeadOrDying(), "the player died at 15 health");

                // the last iv_empty in the selected slot: the iv_blood lands in that slot and the hand keeps it (the re-read), full or empty rest
                for(boolean full : new boolean[] { false, true }) {
                    r.getInventory().clearContent();
                    if(full) fill(r);
                    r.setHealth(20F);
                    r.getInventory().setItem(0, new ItemStack(ivEmpty, 1));
                    InteractionResult last = rightClick(r, InteractionHand.MAIN_HAND);
                    String label = "last iv_empty, " + (full ? "full" : "empty") + " rest: ";
                    check(last.consumesAction() && r.getHealth() == 15F, label + "result " + last + " health " + r.getHealth());
                    ItemStack hand = r.getItemInHand(InteractionHand.MAIN_HAND);
                    check(hand.is(ivBlood) && hand.getCount() == 1 && r.getInventory().getItem(0) == hand, label + "the hand holds " + hand + ", expected 1 iv_blood");
                    check(count(r, ivBlood) == 1 && count(r, ivEmpty) == 0 && items(helper).isEmpty(), label + "iv_blood " + count(r, ivBlood) + " iv_empty " + count(r, ivEmpty) + " dropped " + describe(items(helper)));
                }

                // off hand: the last iv_empty in the off hand: iv_blood goes to the main inventory, the off hand is left empty, nothing is duplicated
                Player off = mockPlayer(helper);
                off.setHealth(20F);
                off.setItemInHand(InteractionHand.OFF_HAND, new ItemStack(ivEmpty, 1));
                InteractionResult offResult = rightClick(off, InteractionHand.OFF_HAND);
                check(offResult.consumesAction() && off.getHealth() == 15F, "off hand iv_empty: result " + offResult + " health " + off.getHealth());
                check(off.getItemInHand(InteractionHand.OFF_HAND).isEmpty() && count(off, ivEmpty) == 0 && count(off, ivBlood) == 1 && off.getInventory().getItem(0).is(ivBlood),
                        "off hand iv_empty: off hand " + off.getItemInHand(InteractionHand.OFF_HAND) + ", iv_empty " + count(off, ivEmpty) + ", iv_blood " + count(off, ivBlood));
                f.getInventory().clearContent();
                f.setHealth(10F);
                f.setItemInHand(InteractionHand.OFF_HAND, new ItemStack(ivBlood, 1));
                rightClick(f, InteractionHand.OFF_HAND);
                check(f.getHealth() == 15F && f.getItemInHand(InteractionHand.OFF_HAND).isEmpty() && count(f, ivBlood) == 0 && count(f, ivEmpty) == 1 && f.getInventory().getItem(0).is(ivEmpty),
                        "off hand iv_blood on a FakePlayer: health " + f.getHealth() + ", off hand " + f.getItemInHand(InteractionHand.OFF_HAND) + ", iv_empty " + count(f, ivEmpty));
                f.getInventory().clearContent();

                // health 4: 4 - 5 < 0 -> 0 and onDeath(magic): LivingEntity.die runs (LivingDeathEvent), damage type minecraft:magic, no attacker
                r.getInventory().clearContent();
                r.setHealth(4F);
                r.getInventory().setItem(0, new ItemStack(ivEmpty, 2));
                watched = r;
                DEATHS.clear();
                rightClick(r, InteractionHand.MAIN_HAND);
                watched = null;
                check(r.getHealth() == 0F && r.isDeadOrDying(), "iv_empty at 4 health: health " + r.getHealth() + ", dead " + r.isDeadOrDying());
                // NeoForge 21.1 posts LivingDeathEvent in Player.die and again in LivingEntity.die (two posts for one die() call on a Player); every post
                // must carry the magic source
                check(!DEATHS.isEmpty() && DEATHS.size() <= 2, "die() posted " + DEATHS.size() + " LivingDeathEvents, expected 1 or 2 (Player.die + LivingEntity.die)");
                for(DamageSource death : DEATHS) {
                    check(death.is(DamageTypes.MAGIC) && death.getEntity() == null && death.getDirectEntity() == null,
                            "death source " + death.type().msgId() + " attacker " + death.getEntity() + ", expected minecraft:magic without an attacker");
                }
                LOGGER.info("{} iv_bags: iv_empty at 4 health -> die() ran ({} death events), damage type {}", TAG, DEATHS.size(), DEATHS.get(0).type().msgId());
                discardItems(helper);

                // exactly 5 health: 0 as well (max(5 - 5, 0)), dies
                Player five = mockPlayer(helper);
                five.setHealth(5F);
                five.getInventory().setItem(0, new ItemStack(ivEmpty, 1));
                watched = five;
                DEATHS.clear();
                rightClick(five, InteractionHand.MAIN_HAND);
                watched = null;
                check(five.getHealth() == 0F && five.isDeadOrDying() && !DEATHS.isEmpty() && DEATHS.get(0).is(DamageTypes.MAGIC), "iv_empty at 5 health: health " + five.getHealth() + ", deaths " + DEATHS.size());
                discardItems(helper);

                // at 5.5 health it survives with 0.5
                Player half = mockPlayer(helper);
                half.setHealth(5.5F);
                half.getInventory().setItem(0, new ItemStack(ivEmpty, 1));
                DEATHS.clear();
                watched = half;
                rightClick(half, InteractionHand.MAIN_HAND);
                watched = null;
                check(half.getHealth() == 0.5F && !half.isDeadOrDying() && DEATHS.isEmpty(), "iv_empty at 5.5 health: health " + half.getHealth() + ", deaths " + DEATHS.size());

                // FakePlayer (not a real player, EntityDamageUtil.java:509-511): no health change, no item change, no sound
                f.setHealth(20F);
                f.getInventory().setItem(0, new ItemStack(ivEmpty, 2));
                SOUNDS.clear();
                InteractionResult fakeResult = rightClick(f, InteractionHand.MAIN_HAND);
                check(f.getHealth() == 20F && !f.isDeadOrDying(), "iv_empty on a FakePlayer: health " + f.getHealth());
                check(f.getItemInHand(InteractionHand.MAIN_HAND).is(ivEmpty) && f.getItemInHand(InteractionHand.MAIN_HAND).getCount() == 2 && count(f, ivBlood) == 0, "iv_empty on a FakePlayer changed the items: " + f.getItemInHand(InteractionHand.MAIN_HAND) + ", iv_blood " + count(f, ivBlood));
                check(SOUNDS.isEmpty(), "iv_empty on a FakePlayer played " + SOUNDS);
                LOGGER.info("{} iv_bags: iv_empty on a FakePlayer returned {}", TAG, fakeResult);
                f.setHealth(3F);
                rightClick(f, InteractionHand.MAIN_HAND);
                check(f.getHealth() == 3F && f.getItemInHand(InteractionHand.MAIN_HAND).getCount() == 2, "iv_empty on a FakePlayer at 3 health: " + f.getHealth());

                // iv_blood: 10 -> 15, one iv_empty, the stack shrinks, the radaway sound (a fresh player: r died above)
                Player b = mockPlayer(helper);
                b.setHealth(10F);
                b.getInventory().setItem(0, new ItemStack(ivBlood, 3));
                SOUNDS.clear();
                InteractionResult blood = rightClick(b, InteractionHand.MAIN_HAND);
                check(blood.consumesAction() && b.getHealth() == 15F, "iv_blood at 10 health: " + b.getHealth() + " result " + blood);
                check(count(b, ivEmpty) == 1 && count(b, ivBlood) == 2 && b.getItemInHand(InteractionHand.MAIN_HAND).getCount() == 2, "iv_blood use: iv_empty " + count(b, ivEmpty) + " iv_blood " + count(b, ivBlood));
                check(SOUNDS.equals(List.of("hbmsntm:item.radaway|player|1.0|1.0")), "iv_blood sounds requested: " + SOUNDS);
                // the heal does not exceed the maximum
                b.setHealth(18F);
                rightClick(b, InteractionHand.MAIN_HAND);
                check(b.getHealth() == 20F, "iv_blood at 18 health: " + b.getHealth() + ", expected 20 (max)");
                b.setHealth(20F);
                rightClick(b, InteractionHand.MAIN_HAND);
                check(b.getHealth() == 20F && b.getItemInHand(InteractionHand.MAIN_HAND).isEmpty() && count(b, ivBlood) == 0 && count(b, ivEmpty) == 3,
                        "iv_blood at 20 health: " + b.getHealth() + ", hand " + b.getItemInHand(InteractionHand.MAIN_HAND) + ", iv_empty " + count(b, ivEmpty));

                // iv_blood works for a FakePlayer too (no real-player gate on it); the last one in the selected slot keeps the container in the hand
                for(boolean full : new boolean[] { false, true }) {
                    f.getInventory().clearContent();
                    if(full) fill(f);
                    f.setHealth(10F);
                    f.getInventory().setItem(0, new ItemStack(ivBlood, 1));
                    InteractionResult last = rightClick(f, InteractionHand.MAIN_HAND);
                    String label = "last iv_blood on a FakePlayer, " + (full ? "full" : "empty") + " rest: ";
                    ItemStack hand = f.getItemInHand(InteractionHand.MAIN_HAND);
                    check(last.consumesAction() && f.getHealth() == 15F, label + "result " + last + " health " + f.getHealth());
                    check(hand.is(ivEmpty) && hand.getCount() == 1 && f.getInventory().getItem(0) == hand && count(f, ivBlood) == 0 && items(helper).isEmpty(), label + "the hand holds " + hand + ", iv_blood " + count(f, ivBlood) + " dropped " + describe(items(helper)));
                }
            }).run();
        } finally {
            watched = null;
            if(real != null) reset(real);
            if(fake != null) reset(fake);
            discardItems(helper);
        }
        done(helper, "iv_bags");
    }

    // 4. siox (ItemPill.java:61-64 asbestos 0 and black lung min(current, maxBlacklung / 5); HbmLivingProps.java:46 maxBlacklung 2 * 60 * 60 * 20; no effect)
    @GameTest(template = TEMPLATE, batch = "medicine_siox_pill", timeoutTicks = 100)
    public static void siox_pill(GameTestHelper helper) {
        String sicknessBefore = NtmConfig.COMMON.POTION_SICKNESS.get();
        FakePlayer player = null;
        try {
            NtmConfig.COMMON.POTION_SICKNESS.set("OFF");
            player = fakePlayer(helper, "medicine-siox");
            FakePlayer p = player;
            guard(() -> {
                ServerLevel level = helper.getLevel();
                Item siox = NtmItems.SIOX.get();
                check(!NtmConfig.COMMON.DISABLE_ASBESTOS.get() && !NtmConfig.COMMON.DISABLE_COAL.get(), "asbestos or coal dust is disabled in the common config; the checks need both");
                check(HbmLivingAttachments.maxBlacklung == MAX_BLACKLUNG && SIOX_BLACKLUNG_CAP == 28800, "maxBlacklung " + HbmLivingAttachments.maxBlacklung + ", expected 144000 (cap 28800)");

                p.getInventory().setItem(0, new ItemStack(siox, 3));
                HbmLivingAttachments.setAsbestos(p, 50000);
                HbmLivingAttachments.setBlackLung(p, 100000);
                check(HbmLivingAttachments.getAsbestos(p) == 50000 && HbmLivingAttachments.getBlackLung(p) == 100000, "precondition: asbestos " + HbmLivingAttachments.getAsbestos(p) + " black lung " + HbmLivingAttachments.getBlackLung(p));
                InteractionResult started = p.gameMode.useItem(p, level, p.getItemInHand(InteractionHand.MAIN_HAND), InteractionHand.MAIN_HAND);
                check(started.consumesAction() && p.isUsingItem() && p.getUseItemRemainingTicks() == USE_TICKS, "siox right click: " + started + ", using " + p.isUsingItem() + ", remaining " + p.getUseItemRemainingTicks());
                ItemStack stack = p.getItemInHand(InteractionHand.MAIN_HAND);
                stack.getItem().finishUsingItem(stack, level, p);
                p.stopUsingItem();
                check(HbmLivingAttachments.getAsbestos(p) == 0, "asbestos after siox: " + HbmLivingAttachments.getAsbestos(p) + ", expected 0");
                check(HbmLivingAttachments.getBlackLung(p) == 28800, "black lung after siox: " + HbmLivingAttachments.getBlackLung(p) + ", expected 28800 (144000 / 5)");
                check(stack.getCount() == 2, "siox stack after eating: " + stack + ", expected 2");
                check(!p.hasEffect(ModEffect.RADX) && !p.hasEffect(ModEffect.POTIONSICKNESS) && !p.hasEffect(ModEffect.RADAWAY), "siox applied an effect: " + p.getActiveEffects());

                // below the cap: black lung unchanged (min), asbestos still reset
                HbmLivingAttachments.setAsbestos(p, 123);
                HbmLivingAttachments.setBlackLung(p, 10000);
                stack.getItem().finishUsingItem(stack, level, p);
                check(HbmLivingAttachments.getBlackLung(p) == 10000 && HbmLivingAttachments.getAsbestos(p) == 0, "siox with black lung 10000: black lung " + HbmLivingAttachments.getBlackLung(p) + " asbestos " + HbmLivingAttachments.getAsbestos(p));
                check(stack.getCount() == 1, "siox stack after the second pill: " + stack);

                // the boundary of the cap: 28800 stays, 28801 becomes 28800
                HbmLivingAttachments.setBlackLung(p, 28800);
                stack.getItem().finishUsingItem(stack, level, p);
                check(HbmLivingAttachments.getBlackLung(p) == 28800, "siox with black lung 28800: " + HbmLivingAttachments.getBlackLung(p));
                p.getInventory().setItem(0, new ItemStack(siox, 1));
                HbmLivingAttachments.setBlackLung(p, 28801);
                ItemStack again = p.getItemInHand(InteractionHand.MAIN_HAND);
                again.getItem().finishUsingItem(again, level, p);
                check(HbmLivingAttachments.getBlackLung(p) == 28800 && again.isEmpty(), "siox with black lung 28801: " + HbmLivingAttachments.getBlackLung(p) + ", stack " + again);
            }).run();
        } finally {
            NtmConfig.COMMON.POTION_SICKNESS.set(sicknessBefore);
            if(player != null) reset(player);
            discardItems(helper);
        }
        done(helper, "siox_pill");
    }

    // 5. potion sickness (PotionConfig.java:22,40-45 "NORMAL" 1 / "TERRARIA" 2, case-insensitive, otherwise 0; VersatileConfig.java:17-24 duration * 12 in
    // TERRARIA, * 20 ticks, empty curative item list; :26-28 has; ItemPill.java:34 applyPotionSickness(player, 5) before the effect, :130-133 the gate on
    // the right click for every pill; radaway (ItemSimpleConsumable.java:37-47) has no such gate)
    @GameTest(template = TEMPLATE, batch = "medicine_potion_sickness", timeoutTicks = 100)
    public static void potion_sickness(GameTestHelper helper) {
        String sicknessBefore = NtmConfig.COMMON.POTION_SICKNESS.get();
        FakePlayer player = null;
        try {
            player = fakePlayer(helper, "medicine-sickness");
            FakePlayer p = player;
            guard(() -> {
                ServerLevel level = helper.getLevel();
                Item radx = NtmItems.RADX.get(), siox = NtmItems.SIOX.get(), radaway = NtmItems.RADAWAY.get();

                // the parse: NORMAL 1, TERRARIA 2, anything else 0
                String[][] modes = { { "NORMAL", "1" }, { "normal", "1" }, { "Normal", "1" }, { "TERRARIA", "2" }, { "terraria", "2" }, { "abc", "0" }, { "OFF", "0" }, { "", "0" } };
                for(String[] mode : modes) {
                    NtmConfig.COMMON.POTION_SICKNESS.set(mode[0]);
                    check(NtmConfig.potionSickness() == Integer.parseInt(mode[1]), "potionSickness(\"" + mode[0] + "\") = " + NtmConfig.potionSickness() + ", expected " + mode[1]);
                }

                // NORMAL: radx -> POTIONSICKNESS 5 s = 100 ticks, no cures
                NtmConfig.COMMON.POTION_SICKNESS.set("NORMAL");
                p.getInventory().setItem(0, new ItemStack(radx, 5));
                ItemStack pill = p.getItemInHand(InteractionHand.MAIN_HAND);
                pill.getItem().finishUsingItem(pill, level, p);
                MobEffectInstance sick = p.getEffect(ModEffect.POTIONSICKNESS);
                check(sick != null && sick.getDuration() == 100 && sick.getAmplifier() == 0, "NORMAL: POTIONSICKNESS " + (sick == null ? "missing" : sick.getDuration() + " / " + sick.getAmplifier()) + ", expected 100 / 0");
                check(sick.getCures().isEmpty(), "POTIONSICKNESS has cures: " + sick.getCures());
                check(p.hasEffect(ModEffect.RADX) && p.getEffect(ModEffect.RADX).getDuration() == RADX_TICKS, "NORMAL: the pill's own effect is missing");
                check(NtmConfig.hasPotionSickness(p), "hasPotionSickness is false with the effect active");

                // saved and loaded (MobEffectInstance.save / load, the player NBT path): the loaded sickness keeps its empty cure set; the ordinary RADX
                // instance keeps its default cures as the control
                MobEffectInstance loadedSick = MobEffectInstance.load((CompoundTag) sick.save());
                check(loadedSick != null && loadedSick.getEffect().is(ModEffect.POTIONSICKNESS) && loadedSick.getDuration() == 100, "loaded sickness " + loadedSick);
                check(loadedSick.getCures().isEmpty(), "the loaded POTIONSICKNESS has cures: " + loadedSick.getCures());
                MobEffectInstance loadedRadx = MobEffectInstance.load((CompoundTag) p.getEffect(ModEffect.RADX).save());
                check(loadedRadx != null && loadedRadx.getCures().contains(EffectCures.MILK), "the loaded RADX lost its default cures: " + (loadedRadx == null ? "null" : loadedRadx.getCures()));

                // milk, honey and the totem cure nothing of it; milk takes RADX away (an ordinary effect), so the cure path itself works
                p.removeEffectsCuredBy(EffectCures.HONEY);
                p.removeEffectsCuredBy(EffectCures.PROTECTED_BY_TOTEM);
                check(p.hasEffect(ModEffect.POTIONSICKNESS), "POTIONSICKNESS removed by honey or the totem");
                p.removeEffectsCuredBy(EffectCures.MILK);
                check(p.hasEffect(ModEffect.POTIONSICKNESS) && p.getEffect(ModEffect.POTIONSICKNESS).getDuration() == 100, "POTIONSICKNESS removed by milk");
                check(!p.hasEffect(ModEffect.RADX), "milk did not cure RADX");

                // while it is active the pills do not start using: pass, not using, the stack unchanged; radaway is not gated
                ItemStack hand = p.getItemInHand(InteractionHand.MAIN_HAND);
                int before = hand.getCount();
                InteractionResult blocked = p.gameMode.useItem(p, level, hand, InteractionHand.MAIN_HAND);
                check(blocked == InteractionResult.PASS && !p.isUsingItem() && hand.getCount() == before && p.getItemInHand(InteractionHand.MAIN_HAND) == hand, "radx under sickness: result " + blocked + ", using " + p.isUsingItem() + ", stack " + hand);
                p.getInventory().setItem(0, new ItemStack(siox, 4));
                hand = p.getItemInHand(InteractionHand.MAIN_HAND);
                blocked = p.gameMode.useItem(p, level, hand, InteractionHand.MAIN_HAND);
                check(blocked == InteractionResult.PASS && !p.isUsingItem() && hand.getCount() == 4, "siox under sickness: result " + blocked + ", using " + p.isUsingItem() + ", stack " + hand);
                p.getInventory().setItem(0, new ItemStack(radaway, 2));
                InteractionResult free = rightClick(p, InteractionHand.MAIN_HAND);
                check(free.consumesAction() && p.getItemInHand(InteractionHand.MAIN_HAND).getCount() == 1 && p.hasEffect(ModEffect.RADAWAY), "radaway under sickness: result " + free + ", stack " + p.getItemInHand(InteractionHand.MAIN_HAND) + ", effect " + p.hasEffect(ModEffect.RADAWAY));

                // after it expires (100 ticks) the pill starts using again
                tickEffects(p, 100);
                check(!p.hasEffect(ModEffect.POTIONSICKNESS) && !NtmConfig.hasPotionSickness(p), "POTIONSICKNESS did not expire after 100 ticks");
                p.getInventory().setItem(0, new ItemStack(radx, 2));
                hand = p.getItemInHand(InteractionHand.MAIN_HAND);
                InteractionResult open = p.gameMode.useItem(p, level, hand, InteractionHand.MAIN_HAND);
                check(open.consumesAction() && p.isUsingItem(), "radx after the sickness: result " + open + ", using " + p.isUsingItem());
                p.stopUsingItem();

                // TERRARIA: 5 s * 12 = 60 s = 1,200 ticks; lower case as well
                for(String mode : new String[] { "TERRARIA", "terraria" }) {
                    NtmConfig.COMMON.POTION_SICKNESS.set(mode);
                    p.removeAllEffects();
                    p.getInventory().setItem(0, new ItemStack(siox, 2));
                    pill = p.getItemInHand(InteractionHand.MAIN_HAND);
                    pill.getItem().finishUsingItem(pill, level, p);
                    sick = p.getEffect(ModEffect.POTIONSICKNESS);
                    check(sick != null && sick.getDuration() == 1200 && sick.getCures().isEmpty(), mode + ": POTIONSICKNESS " + (sick == null ? "missing" : sick.getDuration() + " cures " + sick.getCures()) + ", expected 1200");
                }

                // "abc" and "OFF": no sickness, the pill's own effect still applies
                for(String mode : new String[] { "abc", "OFF" }) {
                    NtmConfig.COMMON.POTION_SICKNESS.set(mode);
                    p.removeAllEffects();
                    p.getInventory().setItem(0, new ItemStack(radx, 2));
                    pill = p.getItemInHand(InteractionHand.MAIN_HAND);
                    pill.getItem().finishUsingItem(pill, level, p);
                    check(!p.hasEffect(ModEffect.POTIONSICKNESS) && p.hasEffect(ModEffect.RADX), "\"" + mode + "\": sickness " + p.hasEffect(ModEffect.POTIONSICKNESS) + " radx " + p.hasEffect(ModEffect.RADX));
                    // the helper alone does nothing either
                    NtmConfig.applyPotionSickness(p, 5);
                    check(!p.hasEffect(ModEffect.POTIONSICKNESS), "\"" + mode + "\": applyPotionSickness applied the effect");
                }

                // the helper by itself (VersatileConfig.java:21): seconds * 20 ticks in NORMAL
                NtmConfig.COMMON.POTION_SICKNESS.set("NORMAL");
                NtmConfig.applyPotionSickness(p, 7);
                check(p.getEffect(ModEffect.POTIONSICKNESS).getDuration() == 140, "applyPotionSickness(7) in NORMAL: " + p.getEffect(ModEffect.POTIONSICKNESS).getDuration() + ", expected 140");
            }).run();
        } finally {
            NtmConfig.COMMON.POTION_SICKNESS.set(sicknessBefore);
            if(player != null) reset(player);
            discardItems(helper);
        }
        done(helper, "potion_sickness");
    }

    // 6. recipes (ConsumableRecipes.java:120 radx shapeless coal dust x2 + fluorite dust, :130 siox x8 coal dust + asbestos dust + nugget_bismuth (the LBSM gold
    // nugget variant :127 is not registered), :143 iv_empty x4 "S","I","S" any rubber ingot + iron plate, :147 radaway iv_blood + coal dust + pumpkin seeds;
    // no recipe makes iv_blood; stack size 64 is the default Item; sounds.json:117-118)
    @GameTest(template = TEMPLATE, batch = "medicine_recipes", timeoutTicks = 100)
    public static void recipes(GameTestHelper helper) {
        guard(() -> {
            ItemStack coal = s(NtmItems.POWDER_COAL.get()), fluorite = s(NtmItems.FLUORITE.get()), asbestos = s(NtmItems.POWDER_ASBESTOS.get());
            ItemStack bismuth = s(NtmItems.NUGGET_BISMUTH.get()), ironPlate = s(NtmItems.PLATE_IRON.get());

            // radx: any slot order of two coal dust and one fluorite (shapeless)
            crafts(helper, "radx coal coal fluorite", grid(coal, coal, fluorite), NtmItems.RADX.get(), 1);
            crafts(helper, "radx fluorite coal coal", grid(fluorite, coal, coal), NtmItems.RADX.get(), 1);
            crafts(helper, "radx coal fluorite coal", grid(coal, fluorite, coal), NtmItems.RADX.get(), 1);
            crafts(helper, "radx spread over the grid", CraftingInput.of(3, 3, cells(9, new int[] { 0, 4, 8 }, new ItemStack[] { fluorite, coal, coal })), NtmItems.RADX.get(), 1);
            notCrafting(helper, "radx with one coal dust", grid(coal, fluorite), NtmItems.RADX.get());
            notCrafting(helper, "radx with three coal dust", grid(coal, coal, coal, fluorite), NtmItems.RADX.get());
            notCrafting(helper, "radx without fluorite", grid(coal, coal), NtmItems.RADX.get());

            // siox: coal dust + asbestos dust + bismuth nugget -> 8
            crafts(helper, "siox", grid(coal, asbestos, bismuth), NtmItems.SIOX.get(), 8);
            crafts(helper, "siox other order", grid(bismuth, coal, asbestos), NtmItems.SIOX.get(), 8);
            notCrafting(helper, "siox with a gold nugget (LBSM variant, not registered)", grid(coal, asbestos, s(Items.GOLD_NUGGET)), NtmItems.SIOX.get());
            notCrafting(helper, "siox without the nugget", grid(coal, asbestos), NtmItems.SIOX.get());

            // iv_empty: "S","I","S" with ANY_RUBBER (ingot_rubber and ingot_biorubber) and the iron plate -> 4
            for(Item rubber : new Item[] { NtmItems.INGOT_RUBBER.get(), NtmItems.INGOT_BIORUBBER.get() }) {
                crafts(helper, "iv_empty with " + name(rubber), shaped(new String[] { "S", "I", "S" }, Map.of('S', s(rubber), 'I', ironPlate)), NtmItems.IV_EMPTY.get(), 4);
            }
            crafts(helper, "iv_empty with rubber above and biorubber below", shaped(new String[] { "S", "I", "T" }, Map.of('S', s(NtmItems.INGOT_RUBBER.get()), 'T', s(NtmItems.INGOT_BIORUBBER.get()), 'I', ironPlate)), NtmItems.IV_EMPTY.get(), 4);
            notCrafting(helper, "iv_empty with a gold plate", shaped(new String[] { "S", "I", "S" }, Map.of('S', s(NtmItems.INGOT_RUBBER.get()), 'I', s(NtmItems.PLATE_GOLD.get()))), NtmItems.IV_EMPTY.get());
            notCrafting(helper, "iv_empty rows I,S,S", shaped(new String[] { "I", "S", "S" }, Map.of('S', s(NtmItems.INGOT_RUBBER.get()), 'I', ironPlate)), NtmItems.IV_EMPTY.get());
            notCrafting(helper, "iv_empty rows S,S,I", shaped(new String[] { "S", "S", "I" }, Map.of('S', s(NtmItems.INGOT_RUBBER.get()), 'I', ironPlate)), NtmItems.IV_EMPTY.get());
            notCrafting(helper, "iv_empty with a vanilla iron ingot for the rubber", shaped(new String[] { "S", "I", "S" }, Map.of('S', s(Items.IRON_INGOT), 'I', ironPlate)), NtmItems.IV_EMPTY.get());
            notCrafting(helper, "iv_empty laid flat", shaped(new String[] { "SIS" }, Map.of('S', s(NtmItems.INGOT_RUBBER.get()), 'I', ironPlate)), NtmItems.IV_EMPTY.get());

            // radaway: iv_blood + coal dust + pumpkin seeds -> 1
            ItemStack blood = s(NtmItems.IV_BLOOD.get()), seeds = s(Items.PUMPKIN_SEEDS);
            crafts(helper, "radaway", grid(blood, coal, seeds), NtmItems.RADAWAY.get(), 1);
            crafts(helper, "radaway other order", grid(seeds, blood, coal), NtmItems.RADAWAY.get(), 1);
            notCrafting(helper, "radaway with melon seeds", grid(blood, coal, s(Items.MELON_SEEDS)), NtmItems.RADAWAY.get());
            notCrafting(helper, "radaway with iv_empty", grid(s(NtmItems.IV_EMPTY.get()), coal, seeds), NtmItems.RADAWAY.get());
            notCrafting(helper, "radaway without coal dust", grid(blood, seeds), NtmItems.RADAWAY.get());

            // no recipe of any type outputs iv_blood; exactly one crafting recipe each makes the other four
            RecipeManager manager = helper.getLevel().getRecipeManager();
            for(RecipeHolder<?> holder : manager.getRecipes()) {
                ItemStack result = holder.value().getResultItem(helper.getLevel().registryAccess());
                check(!result.is(NtmItems.IV_BLOOD.get()), "recipe " + holder.id() + " outputs iv_blood");
            }
            for(Item made : new Item[] { NtmItems.RADX.get(), NtmItems.SIOX.get(), NtmItems.IV_EMPTY.get(), NtmItems.RADAWAY.get() }) {
                int n = 0;
                for(RecipeHolder<CraftingRecipe> holder : manager.getAllRecipesFor(RecipeType.CRAFTING)) {
                    if(holder.value().getResultItem(helper.getLevel().registryAccess()).is(made)) n++;
                }
                check(n == 1, n + " crafting recipes output " + name(made) + ", expected 1");
            }

            // the five items stack to 64 (default Item properties) and have no damage; the two sound events are registered
            for(Item item : new Item[] { NtmItems.RADX.get(), NtmItems.SIOX.get(), NtmItems.RADAWAY.get(), NtmItems.IV_EMPTY.get(), NtmItems.IV_BLOOD.get() }) {
                check(new ItemStack(item).getMaxStackSize() == 64 && !new ItemStack(item).isDamageableItem(), name(item) + " max stack " + new ItemStack(item).getMaxStackSize());
            }
            for(String sound : new String[] { "item.syringe", "item.radaway" }) {
                check(BuiltInRegistries.SOUND_EVENT.containsKey(id(sound)), "sound event " + sound + " is not registered");
            }
            check(BuiltInRegistries.SOUND_EVENT.get(id("item.syringe")) != null && BuiltInRegistries.SOUND_EVENT.get(id("item.syringe")) != BuiltInRegistries.SOUND_EVENT.get(id("item.radaway")), "the two sound events are the same object");
        }).run();
        done(helper, "recipes");
    }

    // 7. regression: the 26A / 26C effect and armor behaviour is unchanged (RadawayEffect (amplifier + 1) per tick; HazmatRegistry.java:213-214 RADX 0.2, full
    // yellow 0.6 + 0.2; GasRadonTombBlock removes RADAWAY and RADX; PotionConfig.java:40 default "OFF")
    @GameTest(template = TEMPLATE, batch = "medicine_regression", timeoutTicks = 100)
    public static void regression(GameTestHelper helper) {
        Player real = null;
        FakePlayer fake = null;
        try {
            real = mockPlayer(helper);
            fake = fakePlayer(helper, "medicine-regression");
            Player r = real;
            FakePlayer f = fake;
            guard(() -> {
                check(NtmConfig.COMMON.ENABLE_CONTAMINATION.get(), "contamination is disabled in the common config; the radiation checks need it");

                // RadawayEffect at amplifier 1: 2 per tick
                HbmLivingAttachments.setRadiation(f, 100F);
                f.addEffect(new MobEffectInstance(ModEffect.RADAWAY, 10, 1));
                tickEffects(f, 10);
                check(HbmLivingAttachments.getRadiation(f) == 80F, "RADAWAY amplifier 1 over 10 ticks: radiation " + HbmLivingAttachments.getRadiation(f) + ", expected 80");
                f.removeAllEffects();

                // HazmatRegistry: RADX +0.2 on its own and with the full yellow suit (0.6 + 0.2)
                Item[] yellow = { NtmItems.HAZMAT_HELMET.get(), NtmItems.HAZMAT_PLATE.get(), NtmItems.HAZMAT_LEGS.get(), NtmItems.HAZMAT_BOOTS.get() };
                EquipmentSlot[] slots = { EquipmentSlot.HEAD, EquipmentSlot.CHEST, EquipmentSlot.LEGS, EquipmentSlot.FEET };
                for(int i = 0; i < 4; i++) f.setItemSlot(slots[i], new ItemStack(yellow[i]));
                check(Math.abs(HazmatRegistry.getResistance(f) - 0.6F) <= RES_TOL, "full yellow: " + HazmatRegistry.getResistance(f) + ", expected 0.6");
                f.addEffect(new MobEffectInstance(ModEffect.RADX, 200));
                check(Math.abs(HazmatRegistry.getResistance(f) - 0.8F) <= RES_TOL, "full yellow + RADX: " + HazmatRegistry.getResistance(f) + ", expected 0.8");
                for(EquipmentSlot slot : slots) f.setItemSlot(slot, ItemStack.EMPTY);
                check(Math.abs(HazmatRegistry.getResistance(f) - 0.2F) <= RES_TOL, "RADX alone: " + HazmatRegistry.getResistance(f) + ", expected 0.2");
                f.removeAllEffects();

                // GasRadonTombBlock.entityInside removes RADAWAY and RADX from a player that has both (the block's own entry point, called directly)
                GasRadonTombBlock tomb = (GasRadonTombBlock) NtmBlocks.GAS_RADON_TOMB.get();
                BlockPos pos = helper.absolutePos(new BlockPos(8, 1, 8));
                r.addEffect(new MobEffectInstance(ModEffect.RADAWAY, 400, 0));
                r.addEffect(new MobEffectInstance(ModEffect.RADX, 400, 0));
                r.addEffect(new MobEffectInstance(ModEffect.POTIONSICKNESS, 400, 0));
                check(r.hasEffect(ModEffect.RADAWAY) && r.hasEffect(ModEffect.RADX), "precondition: the player lacks RADAWAY or RADX");
                tomb.entityInside(tomb.defaultBlockState(), helper.getLevel(), pos, r);
                check(!r.hasEffect(ModEffect.RADAWAY) && !r.hasEffect(ModEffect.RADX), "radon tomb left RADAWAY " + r.hasEffect(ModEffect.RADAWAY) + " RADX " + r.hasEffect(ModEffect.RADX));
                check(r.hasEffect(ModEffect.POTIONSICKNESS), "radon tomb removed POTIONSICKNESS");

                // the config spec: key potion.potionSickness, default "OFF", translation key without a language entry
                ConfigValue<String> value = NtmConfig.COMMON.POTION_SICKNESS;
                check("OFF".equals(value.getDefault()), "potionSickness default " + value.getDefault() + ", expected OFF");
                check(value.getPath().equals(List.of("potion", "potionSickness")), "potionSickness path " + value.getPath());
                check("hbmsntm.configuration.potionSickness".equals(value.getSpec().getTranslationKey()), "translation key " + value.getSpec().getTranslationKey());
                check(value.getSpec().getComment() != null && value.getSpec().getComment().contains("NORMAL") && value.getSpec().getComment().contains("TERRARIA"), "comment " + value.getSpec().getComment());
            }).run();
        } finally {
            if(real != null) reset(real);
            if(fake != null) reset(fake);
            discardItems(helper);
        }
        done(helper, "regression");
    }

    // Helpers

    private static FakePlayer fakePlayer(GameTestHelper helper, String name) {
        FakePlayer player = new FakePlayer(helper.getLevel(), new GameProfile(UUID.randomUUID(), name));
        Vec3 abs = helper.absoluteVec(new Vec3(8.5, 1, 8.5));
        player.moveTo(abs.x, abs.y, abs.z, 0F, 0F);
        player.getInventory().selected = 0;
        // Explicit survival: the GameTest level's own default game mode is not relied on.
        player.setGameMode(GameType.SURVIVAL);
        return player;
    }

    /** A real (non-fake) Player: the GameTest mock player, survival, placed in the test area. Not added to the level. */
    private static Player mockPlayer(GameTestHelper helper) {
        Player player = helper.makeMockPlayer(GameType.SURVIVAL);
        Vec3 abs = helper.absoluteVec(new Vec3(8.5, 1, 8.5));
        player.moveTo(abs.x, abs.y, abs.z, 0F, 0F);
        player.getInventory().selected = 0;
        return player;
    }

    /**
     * The server's right click for the held item. A ServerPlayer goes through the real ServerPlayerGameMode.useItem. The mock Player has no game
     * mode, so the statements of ServerPlayerGameMode.useItem (NeoForge 21.1.228, ServerPlayerGameMode.java:314-335: use(), early return when the
     * same unchanged stack has no use duration, otherwise write the returned stack into the hand and clear an empty one) are replayed here.
     */
    private static InteractionResult rightClick(Player player, InteractionHand hand) {
        ItemStack stack = player.getItemInHand(hand);
        if(player instanceof ServerPlayer serverPlayer) return serverPlayer.gameMode.useItem(serverPlayer, serverPlayer.serverLevel(), stack, hand);

        int count = stack.getCount();
        int damage = stack.getDamageValue();
        InteractionResultHolder<ItemStack> holder = stack.use(player.level(), player, hand);
        ItemStack out = holder.getObject();
        if(out == stack && out.getCount() == count && out.getUseDuration(player) <= 0 && out.getDamageValue() == damage) return holder.getResult();
        if(stack != out) player.setItemInHand(hand, out);
        if(out.isEmpty()) player.setItemInHand(hand, ItemStack.EMPTY);
        return holder.getResult();
    }

    /** One LivingEntity.tickEffects per call: the method LivingEntity.tick runs for the active effects (reflection, protected). */
    private static void tickEffects(LivingEntity entity, int ticks) {
        for(int i = 0; i < ticks; i++) invoke(entity, "tickEffects");
    }

    private static void invoke(LivingEntity entity, String method) {
        try {
            Method m = LivingEntity.class.getDeclaredMethod(method);
            m.setAccessible(true);
            m.invoke(entity);
        } catch(ReflectiveOperationException e) {
            throw new net.minecraft.gametest.framework.GameTestAssertException("LivingEntity." + method + " failed: " + e + " / " + e.getCause());
        }
    }

    /** Registers the sound and death observers once; they only record while a test uses them. */
    private static void listen() {
        if(listening) return;
        listening = true;
        NeoForge.EVENT_BUS.addListener((PlayLevelSoundEvent.AtPosition event) -> {
            ResourceLocation id = event.getSound() == null ? null : event.getSound().value().getLocation();
            if(id != null && id.getNamespace().equals(NuclearTechMod.MODID)) {
                SOUNDS.add(id + "|" + event.getSource().getName() + "|" + event.getOriginalVolume() + "|" + event.getOriginalPitch());
            }
        });
        NeoForge.EVENT_BUS.addListener((LivingDeathEvent event) -> {
            if(event.getEntity() == watched) DEATHS.add(event.getSource());
        });
    }

    private static int count(Player player, Item item) {
        int n = 0;
        for(int i = 0; i < player.getInventory().getContainerSize(); i++) {
            ItemStack stack = player.getInventory().getItem(i);
            if(stack.is(item)) n += stack.getCount();
        }
        return n;
    }

    /** Fills every main inventory slot but the selected hotbar slot 0 with full stacks of stone. */
    private static void fill(Player player) {
        for(int i = 1; i < player.getInventory().items.size(); i++) player.getInventory().setItem(i, new ItemStack(Items.STONE, 64));
    }

    private static void reset(Player player) {
        player.getInventory().clearContent();
        player.removeAllEffects();
        HbmLivingAttachments.setRadiation(player, 0F);
        HbmLivingAttachments.setAsbestos(player, 0);
        HbmLivingAttachments.setBlackLung(player, 0);
    }

    private static List<ItemEntity> items(GameTestHelper helper) {
        Vec3 abs = helper.absoluteVec(new Vec3(8.5, 1, 8.5));
        return helper.getLevel().getEntitiesOfClass(ItemEntity.class, new AABB(abs, abs).inflate(8D));
    }

    private static void discardItems(GameTestHelper helper) {
        for(ItemEntity entity : items(helper)) entity.discard();
    }

    private static String describe(List<ItemEntity> entities) {
        List<String> out = new ArrayList<>();
        for(ItemEntity entity : entities) out.add(entity.getItem().toString());
        return out.toString();
    }

    private static String name(Item item) {
        return BuiltInRegistries.ITEM.getKey(item).getPath();
    }

    private static ItemStack s(ItemLike item) {
        return new ItemStack(item);
    }

    private static ResourceLocation id(String path) {
        return ResourceLocation.fromNamespaceAndPath(NuclearTechMod.MODID, path);
    }

    /** The given stacks in the first cells of a 3x3 grid (shapeless recipes ignore the position). */
    private static CraftingInput grid(ItemStack... stacks) {
        List<ItemStack> cells = new ArrayList<>();
        for(ItemStack stack : stacks) cells.add(stack.copy());
        while(cells.size() < 9) cells.add(ItemStack.EMPTY);
        return CraftingInput.of(3, 3, cells);
    }

    private static List<ItemStack> cells(int size, int[] at, ItemStack[] stacks) {
        List<ItemStack> cells = new ArrayList<>();
        for(int i = 0; i < size; i++) cells.add(ItemStack.EMPTY);
        for(int i = 0; i < at.length; i++) cells.set(at[i], stacks[i].copy());
        return cells;
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

    /** The grid must be matched by the recipe named after the output, with the given count, and the first match must be it. */
    private static void crafts(GameTestHelper helper, String label, CraftingInput input, Item out, int count) {
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
                check(result.is(out) && result.getCount() == count, label + ": " + holder.id() + " yields " + result + ", expected " + count + " x " + name(out));
            }
        }
        check(found, label + ": the grid is not matched by " + recipeId + ", it matches " + ids);
        Optional<RecipeHolder<CraftingRecipe>> first = manager.getRecipeFor(RecipeType.CRAFTING, input, level);
        check(first.isPresent(), label + ": getRecipeFor found nothing");
        ItemStack result = first.get().value().assemble(input, level.registryAccess());
        check(result.is(out) && result.getCount() == count, label + ": the first match " + first.get().id() + " yields " + result);
    }

    private static void notCrafting(GameTestHelper helper, String label, CraftingInput input, Item out) {
        ServerLevel level = helper.getLevel();
        for(RecipeHolder<CraftingRecipe> holder : level.getRecipeManager().getRecipesFor(RecipeType.CRAFTING, input, level)) {
            ItemStack result = holder.value().assemble(input, level.registryAccess());
            check(!result.is(out), label + ": " + holder.id() + " yields " + result);
        }
    }

    private static void done(GameTestHelper helper, String name) {
        LOGGER.info("{} {} passed", TAG, name);
        helper.succeed();
    }
}
