package com.hbm.interfaces;

import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.world.Container;
import net.minecraft.world.item.ItemStack;

/**
 * Original IControlReceiverFilter: a block entity with phantom filter slots that a client may fill (JEI drag and drop, NEI in the
 * original) and the settings tool may copy. Implementors are a Container. Everything here comes from data a client can write, so
 * it is checked before use and never throws: the original dereferences a stack that did not load (IControlReceiverFilter.java:36-37)
 * and only bounds the pasted slot from above (TileEntityCraneBase.java:161-166).
 */
public interface IControlReceiverFilter extends IControlReceiver, ICopiable {

    /** Advances the match mode of the given absolute slot. */
    void nextMode(int slot);

    /** The filter slots, start inclusive and end exclusive. */
    int[] getFilterSlots();

    /**
     * The "slot" control key (original :29-41): writes one item of the sent stack into the filter slot and advances its mode once,
     * without resetting the initial mode, so a dropped item lands one mode past the slot's previous mode as in the original. The
     * whole payload is ignored when the slot lies outside the filter range or the stack does not load or is empty.
     */
    default boolean setFilterContents(CompoundTag data, HolderLookup.Provider registries) {
        if(!data.contains("slot", Tag.TAG_ANY_NUMERIC) || !data.contains("stack", Tag.TAG_COMPOUND)) return false;

        int slot = data.getInt("slot");
        int[] range = this.getFilterSlots();
        if(slot < range[0] || slot >= range[1]) return false;

        ItemStack stack = readFilterStack(data.getCompound("stack"), registries);
        if(stack.isEmpty()) return false;

        ((Container) this).setItem(slot, stack);
        this.nextMode(slot);
        ((Container) this).setChanged();
        return true;
    }

    /** Writes the filter items as the original getSettings does (:113-137): one entry per filled slot, its relative "slot" as a byte. */
    default ListTag writeFilterItems(HolderLookup.Provider registries) {
        Container inv = (Container) this;
        int[] range = this.getFilterSlots();
        ListTag tags = new ListTag();

        for(int i = range[0]; i < range[1]; i++) {
            ItemStack stack = inv.getItem(i);
            if(!stack.isEmpty()) {
                CompoundTag slotTag = new CompoundTag();
                slotTag.putByte("slot", (byte) (i - range[0]));
                tags.add(stack.save(registries, slotTag));
            }
        }

        return tags;
    }

    /**
     * Pastes copied filter items (original :140-176): every valid entry writes one item into its slot and advances that slot's mode
     * once. Entries whose slot falls outside the filter range, or whose item does not load or is empty, are skipped. Slots that the
     * copy leaves empty keep their content, as in the original. The original's router branch (:164, {@code index * + 5}) can never be
     * true and has no counterpart.
     */
    default void pasteFilterItems(CompoundTag settings, HolderLookup.Provider registries) {
        if(!settings.contains("items", Tag.TAG_LIST)) return;

        Container inv = (Container) this;
        int[] range = this.getFilterSlots();
        int size = range[1] - range[0];
        ListTag items = settings.getList("items", Tag.TAG_COMPOUND);

        for(int count = 0; count < size && count < items.size(); count++) {
            CompoundTag slotTag = items.getCompound(count);
            if(!slotTag.contains("slot", Tag.TAG_ANY_NUMERIC)) continue;

            int slot = slotTag.getByte("slot");
            if(slot < 0 || slot >= size) continue;

            ItemStack stack = readFilterStack(slotTag, registries);
            if(stack.isEmpty()) continue;

            inv.setItem(range[0] + slot, stack);
            this.nextMode(range[0] + slot);
            inv.setChanged();
        }
    }

    /** One item of the stack stored in the tag, or an empty stack when the tag does not describe a valid item. */
    static ItemStack readFilterStack(CompoundTag tag, HolderLookup.Provider registries) {
        if(tag.isEmpty()) return ItemStack.EMPTY;

        try {
            ItemStack stack = ItemStack.parseOptional(registries, tag);
            return stack.isEmpty() ? ItemStack.EMPTY : stack.copyWithCount(1);
        } catch(RuntimeException ex) {
            return ItemStack.EMPTY;
        }
    }
}
