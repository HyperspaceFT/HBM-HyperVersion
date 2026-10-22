package com.hbm.blockentity.machine;

import com.hbm.blockentity.MachineBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.handler.FuelPoolRecipeClientSync;
import com.hbm.inventory.menus.MachineWasteDrumMenu;
import com.hbm.inventory.recipes.FuelPoolRecipes;
import com.hbm.items.machine.RBMKRodItem;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.material.Fluid;
import net.minecraft.world.level.material.Fluids;

import javax.annotation.Nullable;

/**
 * Spent fuel pool drum (original TileEntityWasteDrum.java): twelve single-item slots that accept hot waste (any fuel pool table
 * input) and RBMK fuel rods. While water touches the drum, each filled slot has a 1 in (72000 / adjacent water) chance per tick to
 * turn into its table output; a rod is cooled every tick instead and may leave through automation once core and hull are below 50.
 */
public class MachineWasteDrumBlockEntity extends MachineBaseBlockEntity {

    public static final int SLOT_COUNT = 12;
    /** Original updateEntity (:206): 60 * 60 * 20 ticks with one water neighbour, divided by the number of water neighbours. */
    public static final int DECAY_TICKS = 72000;
    private static final int[] SLOTS = { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11 };

    @Nullable private RandomSource decayRandom;

    public MachineWasteDrumBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.MACHINE_WASTE_DRUM.get(), pos, state, SLOT_COUNT);
    }

    @Override
    protected Component getDefaultName() {
        return Component.translatable("container.machine_waste_drum");
    }

    /** Original updateEntity (:191-229). */
    @Override
    public void updateEntity() {
        if(this.level == null || this.level.isClientSide) return;

        int water = this.countWater();
        if(water <= 0) return;

        int r = DECAY_TICKS / water;
        boolean changed = false;
        boolean rods = false;

        for(int i = 0; i < SLOT_COUNT; i++) {
            ItemStack stack = this.slots.get(i);
            if(stack.isEmpty()) continue;

            // Original :212-218: a rod is cooled and never rolls.
            if(stack.getItem() instanceof RBMKRodItem rod) {
                double core = RBMKRodItem.getCoreHeat(stack);
                double hull = RBMKRodItem.getHullHeat(stack);
                rod.updateHeat(this.level, stack, 0.025D);
                rod.provideHeat(this.level, stack, 20D, 0.025D);
                // A rod at 20 °C, or one whose hull has settled a few ulps above 20, no longer changes.
                if(core != RBMKRodItem.getCoreHeat(stack) || hull != RBMKRodItem.getHullHeat(stack)) rods = true;
                continue;
            }

            // The roll happens for every filled slot that is no rod, cool waste included, like the original.
            if(this.random().nextInt(r) == 0) {
                ItemStack output = FuelPoolRecipes.getOutput(stack);
                if(output != null) {
                    // A slot holds one item; a custom row with a larger output count still yields one.
                    this.slots.set(i, output.copyWithCount(1));
                    changed = true;
                }
            }
        }

        // NEO-only: the original never marked the drum dirty after cooling waste. A cooling rod's heat changes every tick; marking the
        // drum once a second while any rod still changes is enough for a lone drum to be saved with its cooled rods.
        if(changed || (rods && this.level.getGameTime() % 20 == 0)) this.setChanged();
    }

    /**
     * Number of the six neighbours holding water (source, flowing or waterlogged). The original only counted water blocks; an
     * unloaded neighbour counts as no water and is never loaded from the tick.
     */
    public int countWater() {
        if(this.level == null) return 0;
        int water = 0;
        for(Direction dir : Direction.values()) {
            BlockPos neighbour = this.worldPosition.relative(dir);
            if(!this.level.isLoaded(neighbour)) continue;
            Fluid fluid = this.level.getFluidState(neighbour).getType();
            if(fluid == Fluids.WATER || fluid == Fluids.FLOWING_WATER) water++;
        }
        return water;
    }

    /** Replaces the level random for the cooling rolls. Deterministic tests only; not saved. */
    public void setDecayRandom(@Nullable RandomSource random) {
        this.decayRandom = random;
    }

    private RandomSource random() {
        return this.decayRandom != null ? this.decayRandom : this.level.random;
    }

    private boolean isKey(ItemStack stack) {
        return this.level != null && this.level.isClientSide ? FuelPoolRecipeClientSync.isKey(stack) : FuelPoolRecipes.isKey(stack);
    }

    @Override public int getMaxStackSize() { return 1; }

    @Override
    public boolean canPlaceItem(int slot, ItemStack stack) {
        // Original isItemValidForSlot (:103-105): a table input or any RBMK fuel rod.
        return !stack.isEmpty() && (this.isKey(stack) || stack.getItem() instanceof RBMKRodItem);
    }

    @Override public int[] getSlotsForFace(Direction direction) { return SLOTS; }
    // NEO-only guard: the vanilla hopper merges up to the item's own max stack size and ignores the container limit, so automation
    // may only fill empty slots. The GUI slot already limits each slot to one item.
    @Override public boolean canPlaceItemThroughFace(int slot, ItemStack stack, @Nullable Direction direction) { return this.getItem(slot).isEmpty() && this.canPlaceItem(slot, stack); }
    /**
     * Original canExtractItem (:183-189): hot waste stays in the drum; anything the table does not take as an input (cooled waste)
     * may leave, and a rod once core and hull are below 50. Taking by hand is not limited, as the original's plain container slots.
     */
    @Override
    public boolean canTakeItemThroughFace(int slot, ItemStack stack, Direction direction) {
        if(stack.getItem() instanceof RBMKRodItem) return RBMKRodItem.getCoreHeat(stack) < 50 && RBMKRodItem.getHullHeat(stack) < 50;
        return !this.isKey(this.getItem(slot));
    }

    @Override
    public AbstractContainerMenu createMenu(int id, Inventory inventory, Player player) {
        return new MachineWasteDrumMenu(id, inventory, this);
    }
}
