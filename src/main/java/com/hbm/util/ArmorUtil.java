package com.hbm.util;

import api.hbm.item.IGasMask;
import com.hbm.handler.ArmorModHandler;
import com.hbm.items.NtmItems;
import com.hbm.lib.ModEffect;
import com.hbm.util.ArmorRegistry.HazardClass;
import net.minecraft.ChatFormatting;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;
import net.neoforged.neoforge.event.EventHooks;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

public class ArmorUtil {

    /*
     * The less horrifying part
     */

    public static void register() {
        ArmorRegistry.registerHazard(Items.DIAMOND_HELMET, HazardClass.PARTICLE_COARSE, HazardClass.GAS_LUNG);

        // Original ArmorUtil.java:39-48; the goggles line waits for the goggles item
        ArmorRegistry.registerHazard(NtmItems.GAS_MASK_FILTER.get(), HazardClass.PARTICLE_COARSE, HazardClass.PARTICLE_FINE, HazardClass.GAS_LUNG, HazardClass.GAS_BLISTERING, HazardClass.BACTERIA);
        ArmorRegistry.registerHazard(NtmItems.GAS_MASK_FILTER_MONO.get(), HazardClass.PARTICLE_COARSE, HazardClass.GAS_MONOXIDE);
        ArmorRegistry.registerHazard(NtmItems.GAS_MASK_FILTER_COMBO.get(), HazardClass.PARTICLE_COARSE, HazardClass.PARTICLE_FINE, HazardClass.GAS_LUNG, HazardClass.GAS_BLISTERING, HazardClass.BACTERIA, HazardClass.GAS_MONOXIDE);
        ArmorRegistry.registerHazard(NtmItems.GAS_MASK_FILTER_RAG.get(), HazardClass.PARTICLE_COARSE);
        ArmorRegistry.registerHazard(NtmItems.GAS_MASK_FILTER_PISS.get(), HazardClass.PARTICLE_COARSE, HazardClass.GAS_LUNG);

        ArmorRegistry.registerHazard(NtmItems.GAS_MASK.get(), HazardClass.SAND, HazardClass.LIGHT);
        ArmorRegistry.registerHazard(NtmItems.GAS_MASK_M65.get(), HazardClass.SAND);
        ArmorRegistry.registerHazard(NtmItems.MASK_RAG.get(), HazardClass.PARTICLE_COARSE);
        ArmorRegistry.registerHazard(NtmItems.MASK_PISS.get(), HazardClass.PARTICLE_COARSE, HazardClass.GAS_LUNG);

        // Original ArmorUtil.java:57-59; the PAA and liquidator helmet lines wait for those suits
        ArmorRegistry.registerHazard(NtmItems.HAZMAT_HELMET.get(), HazardClass.SAND);
        ArmorRegistry.registerHazard(NtmItems.HAZMAT_HELMET_RED.get(), HazardClass.SAND);
        ArmorRegistry.registerHazard(NtmItems.HAZMAT_HELMET_GREY.get(), HazardClass.SAND);
    }

    // Original ArmorUtil.java:82-94: armor[i] is checked against slot 3 - i, i.e. helmet, chestplate, leggings, boots.
    // NEO-only correction: this method used to map armor[0] to the feet (reversed against the original).
    public static boolean checkArmor(LivingEntity entity, Item... armor) {
        EquipmentSlot[] slots = {
                EquipmentSlot.HEAD,   // 0
                EquipmentSlot.CHEST,  // 1
                EquipmentSlot.LEGS,   // 2
                EquipmentSlot.FEET    // 3
        };

        for (int i = 0; i < slots.length; i++) {
            if (!checkArmorPiece(entity, armor[i], slots[i])) {
                return false;
            }
        }
        return true;
    }

    public static boolean checkArmorPiece(LivingEntity entity, Item armor, EquipmentSlot slot) {
        return !checkArmorEmpty(entity, slot) && entity.getItemBySlot(slot).getItem() == armor;
    }

    public static boolean checkArmorEmpty(LivingEntity player, EquipmentSlot slot) {
        return player.getItemBySlot(slot).isEmpty();
    }

    public static void damageSuit(LivingEntity entity, EquipmentSlot slot, int amount) {
        entity.getItemBySlot(slot).hurtAndBreak(amount, entity, slot);
    }

    // Original ArmorUtil.java:120-135. The schrabidium set and checkForHaz2 (PAA, liquidator, euphemium, RPA, FAU, DNS) are not
    // migrated and therefore not checked.
    public static boolean checkForHazmat(LivingEntity entity) {

        if (checkArmor(entity, NtmItems.HAZMAT_HELMET.get(), NtmItems.HAZMAT_PLATE.get(), NtmItems.HAZMAT_LEGS.get(), NtmItems.HAZMAT_BOOTS.get()) ||
                checkArmor(entity, NtmItems.HAZMAT_HELMET_RED.get(), NtmItems.HAZMAT_PLATE_RED.get(), NtmItems.HAZMAT_LEGS_RED.get(), NtmItems.HAZMAT_BOOTS_RED.get()) ||
                checkArmor(entity, NtmItems.HAZMAT_HELMET_GREY.get(), NtmItems.HAZMAT_PLATE_GREY.get(), NtmItems.HAZMAT_LEGS_GREY.get(), NtmItems.HAZMAT_BOOTS_GREY.get())) {

            return true;
        }

        return entity.hasEffect(ModEffect.MUTATION);
    }

    /*
     * Default implementations for IGasMask items
     */
    public static final String FILTER_KEY = "hfr_Filter";

    public static void installGasMaskFilter(Level level, ItemStack mask, ItemStack filter) {

        if (mask.isEmpty() || filter.isEmpty()) return;

        CompoundTag tag = TagsUtil.getCustomData(mask);

        // ItemStack.save returns the encoded tag and leaves its argument untouched in 1.21 (1.7.10 writeToNBT filled it)
        tag.put(FILTER_KEY, filter.save(level.registryAccess()));

        TagsUtil.putCustomData(mask, tag);
    }

    public static void removeFilter(ItemStack mask) {
        if (mask.isEmpty()) return;

        CompoundTag maskTag = TagsUtil.getCustomData(mask);

        if (maskTag.contains(FILTER_KEY)) {
            maskTag.remove(FILTER_KEY);

            TagsUtil.putCustomData(mask, maskTag);
        }
    }

    /**
     * Sneak-right-click on a held mask: with a filter installed, the filter goes into the inventory (or is dropped) instead of
     * the mask being equipped (original ArmorGasMask.java:193-212, ArmorHazmatMask.java:73-93). The change is made on the
     * server only; returns true on both sides when a filter was present, so the caller returns sidedSuccess.
     */
    public static boolean ejectGasMaskFilter(IGasMask mask, ItemStack stack, Level level, Player player) {

        if (!player.isShiftKeyDown()) return false;

        ItemStack filter = mask.getFilter(stack, player);

        if (filter.isEmpty()) return false;

        if (!level.isClientSide()) {
            removeFilter(stack);

            // dropPlayerItemWithRandomChoice(filter, true) scatters the stack without naming the thrower
            if (!player.getInventory().add(filter)) {
                player.drop(filter, true, false);
            }
        }

        return true;
    }

    /**
     * Grabs the installed filter or the filter of the attachment, used for attachment rendering
     */
    public static ItemStack getGasMaskFilterRecursively(ItemStack mask, LivingEntity entity) {

        ItemStack filter = getGasMaskFilter(entity.level(), mask);

        if (filter.isEmpty() && ArmorModHandler.hasMods(mask)) {

            ItemStack[] mods = ArmorModHandler.pryMods(entity.level(), mask);

            if (!mods[ArmorModHandler.HELMET_ONLY].isEmpty() && mods[ArmorModHandler.HELMET_ONLY].getItem() instanceof IGasMask)
                filter = ((IGasMask)mods[ArmorModHandler.HELMET_ONLY].getItem()).getFilter(mods[ArmorModHandler.HELMET_ONLY], entity);
        }

        return filter;
    }

    public static ItemStack getGasMaskFilter(Level level, ItemStack mask) {
        return getGasMaskFilter(level.registryAccess(), mask);
    }

    public static ItemStack getGasMaskFilter(HolderLookup.Provider registries, ItemStack mask) {
        if (mask.isEmpty()) return ItemStack.EMPTY;

        CompoundTag maskTag = TagsUtil.getCustomData(mask);

        if (!maskTag.contains(FILTER_KEY)) return ItemStack.EMPTY;

        CompoundTag attach = maskTag.getCompound(FILTER_KEY);

        Optional<ItemStack> optionalStack = ItemStack.parse(registries, attach);

        return optionalStack.orElse(ItemStack.EMPTY);
    }

    public static void damageGasMaskFilter(LivingEntity entity, int damage) {

        ItemStack mask = entity.getItemBySlot(EquipmentSlot.HEAD);

        if (mask.isEmpty()) return;

        if (!(mask.getItem() instanceof IGasMask)) {

            if (ArmorModHandler.hasMods(mask)) {

                ItemStack[] mods = ArmorModHandler.pryMods(entity.level(), mask);

                if (!mods[ArmorModHandler.HELMET_ONLY].isEmpty() && mods[ArmorModHandler.HELMET_ONLY].getItem() instanceof IGasMask)
                    mask = mods[ArmorModHandler.HELMET_ONLY];
            }
        }
        damageGasMaskFilter(entity.level(), mask, damage);
    }

    public static void damageGasMaskFilter(Level level, ItemStack mask, int damage) {
        ItemStack filter = getGasMaskFilter(level, mask);

        if (filter.isEmpty()) {
            if (ArmorModHandler.hasMods(mask)) {
                ItemStack[] mods = ArmorModHandler.pryMods(level, mask);

                if (!mods[ArmorModHandler.HELMET_ONLY].isEmpty() && mods[ArmorModHandler.HELMET_ONLY].getItem() instanceof IGasMask)
                    filter = getGasMaskFilter(level, mods[ArmorModHandler.HELMET_ONLY]);
            }
        }

        if (filter.isEmpty() || filter.getMaxDamage() == 0)
            return;

        // setDamageValue clamps to the maximum in 1.21, so compare before setting (original ArmorUtil.java:347-352 removes the
        // filter once its damage exceeds the maximum)
        int newDamage = filter.getDamageValue() + damage;

        if (newDamage > filter.getMaxDamage()) {
            removeFilter(mask);
        } else {
            filter.setDamageValue(newDamage);
            installGasMaskFilter(level, mask, filter);
        }
    }

    // Original ArmorUtil.java:355-383. Common code: only the tooltip registries are used, the filter's own lines include the
    // NeoForge tooltip event like the original's ForgeEventFactory.onItemTooltip call (no player is available here).
    public static void addGasMaskTooltip(ItemStack mask, Item.TooltipContext context, List<Component> list, TooltipFlag flag) {

        if (mask.isEmpty() || !(mask.getItem() instanceof IGasMask)) return;

        HolderLookup.Provider registries = context.registries();

        if (registries == null) return;

        ItemStack filter = getGasMaskFilter(registries, mask);

        if (filter.isEmpty()) {
            list.add(Component.translatable("hazard.no_filter").withStyle(ChatFormatting.RED));
            return;
        }

        list.add(Component.translatable("hazard.filter_installed").withStyle(ChatFormatting.GOLD));

        int meta = filter.getDamageValue();
        int max = filter.getMaxDamage();

        String append = "";

        if (max > 0) {
            append = " (" + ((max - meta) * 100 / max) + "%)";
        }

        List<Component> lore = new ArrayList<>();
        list.add(Component.literal("  ").append(filter.getHoverName()).append(append).withStyle(ChatFormatting.GRAY));
        filter.getItem().appendHoverText(filter, context, lore, flag);
        EventHooks.onItemTooltip(filter, null, lore, flag, context);
        lore.forEach(x -> list.add(Component.literal("  ").append(x).withStyle(ChatFormatting.YELLOW)));
    }


    public static boolean isWearingEmptyMask(Player player) {

        ItemStack mask = player.getItemBySlot(EquipmentSlot.HEAD);

        if (mask.isEmpty()) return false;

        if (mask.getItem() instanceof IGasMask) {
            return getGasMaskFilter(player.level(), mask).isEmpty();
        }

        ItemStack mod = ArmorModHandler.pryMods(player.level(), mask)[ArmorModHandler.HELMET_ONLY];

        if (mod != null && mod.getItem() instanceof IGasMask) {
            return getGasMaskFilter(player.level(), mod).isEmpty();
        }

        return false;
    }
}