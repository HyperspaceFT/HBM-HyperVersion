package com.hbm.handler;

import com.hbm.items.armor.ItemArmorMod;
import com.hbm.util.TagsUtil;
import net.minecraft.core.component.DataComponents;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.item.ArmorItem;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;

import java.util.Arrays;
import java.util.Optional;

public class ArmorModHandler {

    public static final int HELMET_ONLY = 0;
    public static final int PLATE_ONLY = 1;
    public static final int LEGS_ONLY = 2;
    public static final int BOOTS_ONLY = 3;
    public static final int SERVOS = 4;
    public static final int CLADDING = 5;
    public static final int KEVLAR = 6;
    public static final int EXTRA = 7;
    public static final int BATTERY = 8;

    public static final int MOD_SLOTS = 9;

    //The key for the NBTTagCompound that holds the armor mods
    public static final String MOD_COMPOUND_KEY = "ntm_armor_mods";
    //The key for the specific slot inside the armor mod NBT Tag
    public static final String MOD_SLOT_KEY = "mod_slot_";

    /**
     * Checks if a mod can be applied to an armor piece
     * Needs to be used to prevent people from inserting invalid items into the armor table
     */
    public static boolean isApplicable(ItemStack armor, ItemStack mod) {

        if(armor.isEmpty() || mod.isEmpty()) return false;
        if(!(armor.getItem() instanceof ArmorItem aItem)) return false;
        if(!(mod.getItem() instanceof ItemArmorMod aMod)) return false;

        ArmorItem.Type type = aItem.getType();

        return (type == ArmorItem.Type.HELMET && aMod.helmet) ||
                (type == ArmorItem.Type.CHESTPLATE && aMod.chestplate) ||
                (type == ArmorItem.Type.LEGGINGS && aMod.leggings) ||
                (type == ArmorItem.Type.BOOTS && aMod.boots);
    }

    /**
     * Applies a mod to the given armor piece
     * Make sure to check for applicability first
     * Will override present mods so make sure to only use unmodded armor pieces
     */
    public static void applyMod(Level level, ItemStack armor, ItemStack mod) {
        CompoundTag tag = TagsUtil.getCustomData(armor);

        if(!tag.contains(MOD_COMPOUND_KEY)) tag.put(MOD_COMPOUND_KEY, new CompoundTag());

        CompoundTag mods = tag.getCompound(MOD_COMPOUND_KEY);

        ItemArmorMod aMod = (ItemArmorMod) mod.getItem();
        int slot = aMod.type;

        // ItemStack.save returns the encoded tag and leaves its argument untouched in 1.21 (1.7.10 writeToNBT filled it)
        mods.put(MOD_SLOT_KEY + slot, mod.save(level.registryAccess()));

        TagsUtil.putCustomData(armor, tag);
    }

    /**
     * Removes the mod from the given slot
     */
    public static void removeMod(ItemStack armor, int slot) {
        if(armor.isEmpty() || !TagsUtil.hasCustomData(armor)) return;

        // Only the mod slot is removed, every other custom data key (filter, cladding, ...) survives (original ArmorModHandler.java:101-119)
        CompoundTag tag = TagsUtil.getCustomData(armor);

        CompoundTag mods = tag.getCompound(MOD_COMPOUND_KEY);
        // An absent slot changes nothing (the original removeTag was an in-place no-op); pryMods visits every absent slot
        if(!mods.contains(MOD_SLOT_KEY + slot) && !mods.isEmpty()) return;
        mods.remove(MOD_SLOT_KEY + slot);

        if(mods.isEmpty()) tag.remove(MOD_COMPOUND_KEY);
        else tag.put(MOD_COMPOUND_KEY, mods);

        if(tag.isEmpty()) armor.remove(DataComponents.CUSTOM_DATA);
        else TagsUtil.putCustomData(armor, tag);
    }

    /**
     * Removes ALL mods
     * Should be used when the armor piece is put in the armor table slot AFTER the armor pieces have been separated
     */
    public static void clearMods(ItemStack armor) {

        if(!TagsUtil.hasCustomData(armor)) return;

        CompoundTag tag = TagsUtil.getCustomData(armor);
        tag.remove(MOD_COMPOUND_KEY);
        TagsUtil.putCustomData(armor, tag);
    }

    /**
     * Does what the name implies. Returns true if the stack has NBT and that NBT has the MOD_COMPOUND_KEY tag.
     */
    public static boolean hasMods(ItemStack armor) {

        if(!TagsUtil.hasCustomData(armor)) return false;

        CompoundTag tag = TagsUtil.getCustomData(armor);
        return tag.contains(MOD_COMPOUND_KEY);
    }

    /**
     * Gets all the modifications in the provided armor
     * Absent slots are ItemStack.EMPTY, never null
     */
    public static ItemStack[] pryMods(Level level, ItemStack armor) {

        ItemStack[] slots = new ItemStack[MOD_SLOTS];
        Arrays.fill(slots, ItemStack.EMPTY);

        if(!hasMods(armor)) return slots;

        CompoundTag tag = TagsUtil.getCustomData(armor);
        CompoundTag mods = tag.getCompound(MOD_COMPOUND_KEY);

        for(int i = 0; i < MOD_SLOTS; i++) {

            CompoundTag cmp = mods.getCompound(MOD_SLOT_KEY + i);

            // An empty slot compound is absent; parsing it would log a codec error on every call
            Optional<ItemStack> stack = cmp.isEmpty() ? Optional.empty() : ItemStack.parse(level.registryAccess(), cmp);

            if(stack.isPresent() && !stack.get().isEmpty()) {
                slots[i] = stack.get();
            } else {
                // Any non-existing armor mods will be sorted out automatically
                removeMod(armor, i);
            }
        }

        return slots;
    }

    public static ItemStack pryMod(Level level, ItemStack armor, int slot) {

        if(!hasMods(armor)) return ItemStack.EMPTY;

        CompoundTag tag = TagsUtil.getCustomData(armor);
        CompoundTag mods = tag.getCompound(MOD_COMPOUND_KEY);
        CompoundTag cmp = mods.getCompound(MOD_SLOT_KEY + slot);
        Optional<ItemStack> stack = ItemStack.parse(level.registryAccess(), cmp);

        if(stack.isPresent() && !stack.get().isEmpty()) return stack.get();

        removeMod(armor, slot);

        return ItemStack.EMPTY;
    }
}
