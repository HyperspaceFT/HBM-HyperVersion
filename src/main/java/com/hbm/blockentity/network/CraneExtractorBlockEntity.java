package com.hbm.blockentity.network;

import api.hbm.conveyor.IConveyorBelt;
import api.hbm.conveyor.IEnterableBlock;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.entity.NtmEntityTypes;
import com.hbm.entity.item.MovingItem;
import com.hbm.interfaces.IControlReceiverFilter;
import com.hbm.inventory.menus.CraneExtractorMenu;
import com.hbm.items.NtmItems;
import com.hbm.module.ModulePatternMatcher;
import com.hbm.registry.NtmSoundEvents;
import com.hbm.util.AdjacentInventory;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;

/**
 * Original TileEntityCraneExtractor. Slots 0-8 are the phantom filter, 9-17 the buffer, 18 the stack upgrade and 19 the ejector
 * upgrade (ContainerCraneExtractor.java:24-33).
 */
public class CraneExtractorBlockEntity extends CraneBaseBlockEntity implements IControlReceiverFilter {

    public static final int SLOT_STACK_UPGRADE = 18;
    public static final int SLOT_EJECTOR_UPGRADE = 19;
    private static final int[] ACCESS = new int[] { 9, 10, 11, 12, 13, 14, 15, 16, 17 };

    public boolean isWhitelist = false;
    public boolean maxEject = false;
    public final ModulePatternMatcher matcher = new ModulePatternMatcher(9);

    public CraneExtractorBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.CRANE_EXTRACTOR.get(), pos, state, 20);
    }

    @Override
    protected Component getDefaultName() {
        return Component.translatable("container.craneExtractor");
    }

    /** Original :47-57: plugging the matching upgrade into its slot plays the plug sound. */
    @Override
    public void setItem(int slot, ItemStack stack) {
        super.setItem(slot, stack);

        if(this.level != null && !this.level.isClientSide && !stack.isEmpty()
                && ((slot == SLOT_EJECTOR_UPGRADE && isEjectorUpgrade(stack)) || (slot == SLOT_STACK_UPGRADE && isStackUpgrade(stack)))) {
            this.level.playSound(null, this.worldPosition, NtmSoundEvents.UPGRADE_PLUG.get(), SoundSource.BLOCKS, 1.0F, 1.0F);
        }
    }

    public static boolean isStackUpgrade(ItemStack stack) {
        return stack.is(NtmItems.UPGRADE_STACK_1.get()) || stack.is(NtmItems.UPGRADE_STACK_2.get()) || stack.is(NtmItems.UPGRADE_STACK_3.get());
    }

    public static boolean isEjectorUpgrade(ItemStack stack) {
        return stack.is(NtmItems.UPGRADE_EJECTOR_1.get()) || stack.is(NtmItems.UPGRADE_EJECTOR_2.get()) || stack.is(NtmItems.UPGRADE_EJECTOR_3.get());
    }

    /** Original :64-72: ticks between actions, 20 or 10/5/2 with the ejector upgrade. */
    public int getDelay() {
        ItemStack upgrade = this.slots.get(SLOT_EJECTOR_UPGRADE);
        if(upgrade.is(NtmItems.UPGRADE_EJECTOR_1.get())) return 10;
        if(upgrade.is(NtmItems.UPGRADE_EJECTOR_2.get())) return 5;
        if(upgrade.is(NtmItems.UPGRADE_EJECTOR_3.get())) return 2;
        return 20;
    }

    /** Original :75-83: items per action, 1 or 4/16/64 with the stack upgrade. */
    public int getAmount() {
        ItemStack upgrade = this.slots.get(SLOT_STACK_UPGRADE);
        if(upgrade.is(NtmItems.UPGRADE_STACK_1.get())) return 4;
        if(upgrade.is(NtmItems.UPGRADE_STACK_2.get())) return 16;
        if(upgrade.is(NtmItems.UPGRADE_STACK_3.get())) return 64;
        return 1;
    }

    /**
     * Original :59-166. Acts when the world time is a multiple of the delay and there is no redstone signal. Takes from the inventory
     * on the output side and sends to the belt on the input side (the original's switcheroo, :85-88). The first stack that can be
     * taken, passes the filter and, with maxEject on, holds the full amount is moved once: onto the belt, or without a belt into the
     * buffer. When nothing was taken and there is a belt, the first buffer stack goes onto the belt regardless of the filter. NEO does
     * nothing while either neighbour's chunk is not loaded (the original loads them).
     */
    @Override
    public void updateEntity() {
        if(this.level == null || this.level.isClientSide) return;

        if(this.level.getGameTime() % this.getDelay() == 0 && !this.level.hasNeighborSignal(this.worldPosition)) {
            this.act();
        }

        this.networkPackNT(15);
    }

    private void act() {
        int amount = this.getAmount();
        Direction inputSide = this.getOutputSide(); // note the switcheroo!
        Direction outputSide = this.getInputSide();
        BlockPos sourcePos = this.worldPosition.relative(inputSide);
        BlockPos beltPos = this.worldPosition.relative(outputSide);

        if(!this.level.isLoaded(sourcePos) || !this.level.isLoaded(beltPos)) return;

        AdjacentInventory.Source source = AdjacentInventory.source(this.level, sourcePos, inputSide.getOpposite());
        Block b = this.level.getBlockState(beltPos).getBlock();
        IConveyorBelt belt = b instanceof IConveyorBelt icb ? icb : null;
        boolean hasSent = false;

        if(source != null) {
            for(int i = 0; i < source.size(); i++) {
                ItemStack stack = source.peek(i);
                if(stack.isEmpty() || !source.canTake(i)) continue;

                int maxTarget = Math.min(amount, stack.getMaxStackSize());
                if(this.maxEject && stack.getCount() < maxTarget) continue;

                if(this.isWhitelist == this.matchesFilter(stack)) {
                    int toSend = Math.min(amount, stack.getCount());

                    if(belt != null) {
                        ItemStack taken = source.take(i, toSend, false);
                        if(!taken.isEmpty()) this.sendItem(taken, belt, beltPos, outputSide);
                    } else {
                        int fits = this.bufferRoom(source.take(i, toSend, true));
                        if(fits > 0) this.addToBuffer(source.take(i, fits, false));
                    }

                    hasSent = true;
                    break;
                }
            }
        }

        if(!hasSent && belt != null) {

            for(int i = 9; i < 18; i++) {
                ItemStack stack = this.slots.get(i);

                if(!stack.isEmpty()) {
                    int toSend = Math.min(amount, stack.getCount());
                    int maxTarget = Math.min(amount, stack.getMaxStackSize());
                    if(this.maxEject && stack.getCount() < maxTarget) continue;

                    this.sendItem(this.removeItem(i, toSend), belt, beltPos, outputSide);
                    break;
                }
            }
        }
    }

    /**
     * How many items of the stack the buffer takes, as InventoryUtil.tryAddItemToInventory (slots 9-17) places them: topping up equal
     * stacks first, then the whole rest into the first empty slot.
     */
    private int bufferRoom(ItemStack stack) {
        if(stack.isEmpty()) return 0;

        int room = 0;
        boolean hasEmpty = false;

        for(int i = 9; i < 18; i++) {
            ItemStack slot = this.slots.get(i);
            if(slot.isEmpty()) hasEmpty = true;
            else if(ItemStack.isSameItemSameComponents(slot, stack)) room += Math.max(0, slot.getMaxStackSize() - slot.getCount());
        }

        return hasEmpty ? stack.getCount() : Math.min(room, stack.getCount());
    }

    private void addToBuffer(ItemStack stack) {

        for(int i = 9; i < 18 && !stack.isEmpty(); i++) {
            ItemStack slot = this.slots.get(i);

            if(!slot.isEmpty() && ItemStack.isSameItemSameComponents(slot, stack)) {
                int transfer = Math.min(stack.getCount(), slot.getMaxStackSize() - slot.getCount());
                if(transfer > 0) {
                    this.slots.set(i, slot.copyWithCount(slot.getCount() + transfer));
                    stack.shrink(transfer);
                }
            }
        }

        for(int i = 9; i < 18 && !stack.isEmpty(); i++) {
            if(this.slots.get(i).isEmpty()) {
                this.slots.set(i, stack.copy());
                stack.setCount(0);
            }
        }

        this.setChanged();
    }

    /**
     * Original :168-187: a moving item 0.55 blocks toward the belt, snapped onto it; a belt that is also an enterable block taking the
     * item gets it directly.
     */
    private void sendItem(ItemStack stack, IConveyorBelt belt, BlockPos beltPos, Direction outputSide) {
        MovingItem moving = new MovingItem(NtmEntityTypes.MOVING_ITEM.get(), this.level);
        Vec3 pos = Vec3.atCenterOf(this.worldPosition).add(outputSide.getStepX() * 0.55, outputSide.getStepY() * 0.55, outputSide.getStepZ() * 0.55);
        Vec3 snap = belt.getClosestSnappingPosition(this.level, beltPos, pos);
        moving.moveTo(snap.x, snap.y, snap.z, 0, 0);
        moving.setItemStack(stack);
        this.level.addFreshEntity(moving);

        if(belt instanceof IEnterableBlock enterable && enterable.canItemEnter(this.level, beltPos, outputSide.getOpposite(), moving)) {
            enterable.onItemEnter(this.level, beltPos, outputSide.getOpposite(), moving);
            moving.discard();
        }
    }

    /** Original :189-198: any filled filter slot matching. */
    public boolean matchesFilter(ItemStack stack) {

        for(int i = 0; i < 9; i++) {
            ItemStack filter = this.slots.get(i);

            if(!filter.isEmpty() && this.matcher.isValidForFilter(filter, i, stack)) {
                return true;
            }
        }

        return false;
    }

    @Override
    public void nextMode(int slot) {
        if(this.level != null) this.matcher.nextMode(this.level, this.slots.get(slot), slot);
    }

    @Override
    public int[] getFilterSlots() {
        return new int[] { 0, 9 };
    }

    /** Original :232-246: only the buffer is open to automation; inserting has to pass the filter, taking does not. */
    @Override
    public int[] getSlotsForFace(Direction side) {
        return ACCESS;
    }

    @Override
    public boolean canPlaceItem(int slot, ItemStack stack) {
        return slot > 8 && slot < 18 && this.isWhitelist == this.matchesFilter(stack);
    }

    @Override
    public boolean canTakeItemThroughFace(int slot, ItemStack stack, Direction side) {
        return slot > 8 && slot < 18;
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeBoolean(this.isWhitelist);
        buf.writeBoolean(this.maxEject);
        this.matcher.serialize(buf);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.isWhitelist = buf.readBoolean();
        this.maxEject = buf.readBoolean();
        this.matcher.deserialize(buf);
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.isWhitelist = tag.getBoolean("isWhitelist");
        this.maxEject = tag.getBoolean("maxEject");
        this.matcher.readFromNBT(tag);
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putBoolean("isWhitelist", this.isWhitelist);
        tag.putBoolean("maxEject", this.maxEject);
        this.matcher.writeToNBT(tag);
    }

    /** Original :281-292: "whitelist" and "maxEject" toggle, "slot" fills a filter slot (checked, see IControlReceiverFilter). */
    @Override
    public void receiveControl(CompoundTag tag) {
        if(tag.contains("whitelist")) this.isWhitelist = !this.isWhitelist;
        if(tag.contains("maxEject")) this.maxEject = !this.maxEject;
        if(tag.contains("slot") && this.level != null) this.setFilterContents(tag, this.level.registryAccess());
        this.setChanged();
    }

    @Override
    public AbstractContainerMenu createMenu(int containerId, Inventory inventory, Player player) {
        return new CraneExtractorMenu(containerId, inventory, this);
    }
}
