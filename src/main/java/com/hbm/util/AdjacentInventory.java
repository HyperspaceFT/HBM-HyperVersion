package com.hbm.util;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.Container;
import net.minecraft.world.WorldlyContainer;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.AbstractFurnaceBlockEntity;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.neoforged.neoforge.capabilities.Capabilities;
import net.neoforged.neoforge.items.IItemHandler;
import net.neoforged.neoforge.items.ItemHandlerHelper;

import javax.annotation.Nullable;

/**
 * How the conveyor cranes reach the block next to them (GOAL31 decision 2). In order:
 * <ol>
 *     <li>furnace-type blocks (furnace, blast furnace, smoker share AbstractFurnaceBlockEntity, slots 0 input, 1 fuel, 2 result as in
 *     1.7.10) get the original's special slots: inserting fills fuel before input from any face (InventoryUtil.java:20-26), extracting
 *     only takes the result (TileEntityCraneExtractor.java:204-211). This comes first because NeoForge also gives furnaces an item
 *     capability;</li>
 *     <li>the item handler capability, asked with the target's face toward the crane;</li>
 *     <li>a WorldlyContainer or Container when the target provides no capability, with the original's rules
 *     (CraneInserter.java:98-146 for inserting).</li>
 * </ol>
 * Nothing here loads a chunk: an unloaded target counts as no target (the original only does this in the inserter's own tick,
 * TileEntityCraneInserter.java:45). Both paths move items without losing or creating any: the handler path simulates before it
 * extracts, the container path writes the exact amount it moved.
 */
public class AdjacentInventory {

    private static final int[] FURNACE_INSERT = new int[] { 1, 0 };
    private static final int[] FURNACE_EXTRACT = new int[] { 2 };

    /**
     * Inserts as much of the stack as the target at {@code pos} accepts through {@code face}, the target's face toward the crane, and
     * returns the rest. The returned stack may be the given one shrunk; an absent target returns it unchanged.
     */
    public static ItemStack insert(Level level, BlockPos pos, Direction face, ItemStack stack) {
        if(stack.isEmpty() || !level.isLoaded(pos)) return stack;

        BlockEntity be = level.getBlockEntity(pos);
        if(be instanceof AbstractFurnaceBlockEntity furnace) return insertIntoContainer(furnace, FURNACE_INSERT, stack, face);

        IItemHandler handler = level.getCapability(Capabilities.ItemHandler.BLOCK, pos, face);
        if(handler != null) return ItemHandlerHelper.insertItemStacked(handler, stack, false);

        if(be instanceof WorldlyContainer sided) return insertIntoContainer(sided, sided.getSlotsForFace(face), stack, face);
        if(be instanceof Container inv) return insertIntoContainer(inv, null, stack, face);

        return stack;
    }

    /**
     * Whether {@link #insert} has a target at {@code pos} through {@code face}: a furnace-type block, the item handler capability or a
     * container; an unloaded chunk counts as no target. {@code insert} returns the stack unchanged both without a target and with a
     * full one, so the grabber asks this first (it only looks for items when there is an inventory, TileEntityCraneGrabber.java:137).
     */
    public static boolean hasTarget(Level level, BlockPos pos, Direction face) {
        if(!level.isLoaded(pos)) return false;

        BlockEntity be = level.getBlockEntity(pos);
        if(be instanceof AbstractFurnaceBlockEntity) return true;
        if(level.getCapability(Capabilities.ItemHandler.BLOCK, pos, face) != null) return true;
        return be instanceof Container;
    }

    /**
     * The original addToInventory (CraneInserter.java:98-146): first tops up stacks of the same item and components, then fills empty
     * slots, asking the face rules and canPlaceItem for each slot and staying under the container's stack limit. {@code access} is
     * the slot order, null for every slot. The original caps a new stack at the container's limit only (:131); NEO also caps it at
     * the item's own stack size. Returns what is left; {@code toAdd} is shrunk by what went in.
     */
    public static ItemStack insertIntoContainer(Container inv, @Nullable int[] access, ItemStack toAdd, Direction face) {
        WorldlyContainer sided = inv instanceof WorldlyContainer w ? w : null;
        int limit = inv.getMaxStackSize();
        int size = access == null ? inv.getContainerSize() : access.length;

        for(int i = 0; i < size && !toAdd.isEmpty(); i++) {
            int index = access == null ? i : access[i];
            ItemStack stack = inv.getItem(index);
            int stackLimit = Math.min(stack.getMaxStackSize(), limit);

            if(!stack.isEmpty() && ItemStack.isSameItemSameComponents(toAdd, stack) && stack.getCount() < stackLimit && canPlace(inv, sided, index, toAdd, face)) {
                int amount = Math.min(toAdd.getCount(), stackLimit - stack.getCount());
                inv.setItem(index, stack.copyWithCount(stack.getCount() + amount));
                toAdd.shrink(amount);
                inv.setChanged();
            }
        }

        for(int i = 0; i < size && !toAdd.isEmpty(); i++) {
            int index = access == null ? i : access[i];

            if(inv.getItem(index).isEmpty() && canPlace(inv, sided, index, toAdd, face)) {
                int amount = Math.min(toAdd.getCount(), Math.min(limit, toAdd.getMaxStackSize()));
                // a 1.21 furnace takes an empty bucket as fuel while its fuel slot is empty; one at a time, as NeoForge's SidedInvWrapper
                if(inv instanceof AbstractFurnaceBlockEntity && index == 1 && toAdd.is(Items.BUCKET)) amount = Math.min(amount, 1);
                inv.setItem(index, toAdd.copyWithCount(amount));
                toAdd.shrink(amount);
                inv.setChanged();
            }
        }

        return toAdd;
    }

    private static boolean canPlace(Container inv, @Nullable WorldlyContainer sided, int index, ItemStack stack, Direction face) {
        return (sided == null || sided.canPlaceItemThroughFace(index, stack, face)) && inv.canPlaceItem(index, stack);
    }

    /**
     * The slots of the target at {@code pos} that may be taken from through {@code face}, the target's face toward the crane, or null
     * when there is no target.
     */
    @Nullable
    public static Source source(Level level, BlockPos pos, Direction face) {
        if(!level.isLoaded(pos)) return null;

        BlockEntity be = level.getBlockEntity(pos);
        if(be instanceof AbstractFurnaceBlockEntity furnace) return new ContainerSource(furnace, FURNACE_EXTRACT, face);

        IItemHandler handler = level.getCapability(Capabilities.ItemHandler.BLOCK, pos, face);
        if(handler != null) return new HandlerSource(handler);

        if(be instanceof WorldlyContainer sided) return new ContainerSource(sided, sided.getSlotsForFace(face), face);
        if(be instanceof Container inv) return new ContainerSource(inv, null, face);

        return null;
    }

    /** A target the extractor takes from, its slots in the order the target gives them. */
    public interface Source {

        int size();

        /** The stack in the i-th accessible slot; not to be modified. */
        ItemStack peek(int i);

        /** Whether the stack in the i-th slot may be taken at all (the original canExtractItem; the handler's own simulation). */
        boolean canTake(int i);

        /** Takes up to {@code amount} items from the i-th slot and returns them; simulating changes nothing. */
        ItemStack take(int i, int amount, boolean simulate);
    }

    public record HandlerSource(IItemHandler handler) implements Source {

        @Override public int size() { return handler.getSlots(); }
        @Override public ItemStack peek(int i) { return handler.getStackInSlot(i); }
        @Override public boolean canTake(int i) { return !handler.extractItem(i, 1, true).isEmpty(); }
        @Override public ItemStack take(int i, int amount, boolean simulate) { return handler.extractItem(i, amount, simulate); }
    }

    public record ContainerSource(Container inv, @Nullable int[] access, Direction face) implements Source {

        private int index(int i) { return access == null ? i : access[i]; }

        @Override public int size() { return access == null ? inv.getContainerSize() : access.length; }
        @Override public ItemStack peek(int i) { return inv.getItem(index(i)); }

        @Override
        public boolean canTake(int i) {
            ItemStack stack = inv.getItem(index(i));
            return !stack.isEmpty() && (!(inv instanceof WorldlyContainer sided) || sided.canTakeItemThroughFace(index(i), stack, face));
        }

        @Override
        public ItemStack take(int i, int amount, boolean simulate) {
            ItemStack stack = inv.getItem(index(i));
            int count = Math.min(amount, stack.getCount());
            if(count <= 0) return ItemStack.EMPTY;
            if(simulate) return stack.copyWithCount(count);

            ItemStack taken = inv.removeItem(index(i), count);
            inv.setChanged();
            return taken;
        }
    }
}
