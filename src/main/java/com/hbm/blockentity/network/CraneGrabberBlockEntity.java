package com.hbm.blockentity.network;

import api.hbm.conveyor.IConveyorBelt;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.NtmBlocks;
import com.hbm.entity.NtmEntityTypes;
import com.hbm.entity.item.MovingItem;
import com.hbm.interfaces.IControlReceiverFilter;
import com.hbm.inventory.menus.CraneGrabberMenu;
import com.hbm.items.NtmItems;
import com.hbm.module.ModulePatternMatcher;
import com.hbm.util.AdjacentInventory;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

import java.util.List;

/**
 * Original TileEntityCraneGrabber. Slots 0-8 are the phantom filter, 9 the stack upgrade and 10 the ejector upgrade
 * (ContainerCraneGrabber.java:25,30-31); there is no buffer and no slot is open to automation.
 */
public class CraneGrabberBlockEntity extends CraneBaseBlockEntity implements IControlReceiverFilter {

    public static final int SLOT_STACK_UPGRADE = 9;
    public static final int SLOT_EJECTOR_UPGRADE = 10;
    private static final int[] NO_SLOTS = new int[0];

    public boolean isWhitelist = false;
    public final ModulePatternMatcher matcher = new ModulePatternMatcher(9);
    public long lastGrabbedTick = 0;

    public CraneGrabberBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.CRANE_GRABBER.get(), pos, state, 11);
    }

    @Override
    protected Component getDefaultName() {
        return Component.translatable("container.craneGrabber");
    }

    /** Original :59-67: ticks between grabs, 20 or 10/5/2 with the ejector upgrade. */
    public int getDelay() {
        ItemStack upgrade = this.slots.get(SLOT_EJECTOR_UPGRADE);
        if(upgrade.is(NtmItems.UPGRADE_EJECTOR_1.get())) return 10;
        if(upgrade.is(NtmItems.UPGRADE_EJECTOR_2.get())) return 5;
        if(upgrade.is(NtmItems.UPGRADE_EJECTOR_3.get())) return 2;
        return 20;
    }

    /** Original :71-79: items per grab into an inventory, 1 or 4/16/64 with the stack upgrade. */
    public int getAmount() {
        ItemStack upgrade = this.slots.get(SLOT_STACK_UPGRADE);
        if(upgrade.is(NtmItems.UPGRADE_STACK_1.get())) return 4;
        if(upgrade.is(NtmItems.UPGRADE_STACK_2.get())) return 16;
        if(upgrade.is(NtmItems.UPGRADE_STACK_3.get())) return 64;
        return 1;
    }

    /**
     * Original :54-188. Tries once the world time has reached the last grab plus the delay and there is no redstone signal. Moving
     * items (never packages) in the box in front of the input side are grabbed: onto the belt on the output side, one whole stack,
     * or into the inventory there, up to the amount spread over several stacks. The last grab time is set when an item is picked,
     * before it is known whether the target took any of it (:113,169), so a full target still starts the cooldown; without a belt or
     * an inventory on the output side no item is picked and the cooldown does not start.
     */
    @Override
    public void updateEntity() {
        if(this.level == null || this.level.isClientSide) return;

        if(this.level.getGameTime() >= this.lastGrabbedTick + this.getDelay() && !this.level.hasNeighborSignal(this.worldPosition)) {
            this.grab();
        }

        this.networkPackNT(15);
    }

    private void grab() {
        Direction inputSide = this.getInputSide();
        Direction outputSide = this.getOutputSide();
        BlockPos targetPos = this.worldPosition.relative(outputSide);
        Block beltBlock = this.level.getBlockState(targetPos).getBlock();

        if(beltBlock instanceof IConveyorBelt belt) {

            for(MovingItem item : this.itemsInReach(inputSide)) {
                if(item.isRemoved()) continue;

                ItemStack stack = item.getItemStack();
                if(stack.isEmpty()) {
                    item.discard();
                    continue;
                }

                if(this.isWhitelist != this.matchesFilter(stack)) continue;

                this.lastGrabbedTick = this.level.getGameTime();
                this.setChanged();

                Vec3 pos = Vec3.atCenterOf(this.worldPosition).add(outputSide.getStepX() * 0.55, outputSide.getStepY() * 0.55, outputSide.getStepZ() * 0.55);
                Vec3 snap = belt.getClosestSnappingPosition(this.level, targetPos, pos);
                MovingItem moved = new MovingItem(NtmEntityTypes.MOVING_ITEM.get(), this.level);
                moved.moveTo(snap.x, snap.y, snap.z, 0, 0);
                moved.setItemStack(stack);
                item.discard();
                this.level.addFreshEntity(moved);
                break;
            }

        } else if(AdjacentInventory.hasTarget(this.level, targetPos, outputSide.getOpposite())) {
            // the original only looks for items when the output side holds an inventory (:137); NEO does not load the target's chunk
            int amount = this.getAmount();

            for(MovingItem item : this.itemsInReach(inputSide)) {
                if(item.isRemoved()) continue;

                ItemStack stack = item.getItemStack();
                if(stack.isEmpty()) {
                    item.discard();
                    continue;
                }

                if(this.isWhitelist != this.matchesFilter(stack)) continue;

                this.lastGrabbedTick = this.level.getGameTime();
                this.setChanged();

                int toAdd = Math.min(stack.getCount(), amount);
                ItemStack ret = AdjacentInventory.insert(this.level, targetPos, outputSide.getOpposite(), stack.copyWithCount(toAdd));
                int didAdd = toAdd - ret.getCount();

                if(didAdd > 0) {
                    // the belt's stack lives in the entity's synced data: write a new stack back instead of changing it in place
                    stack.shrink(didAdd);
                    if(stack.isEmpty()) item.discard();
                    else item.setItemStack(stack);
                }

                amount -= didAdd;
                if(amount <= 0) break;
            }
        }
    }

    /**
     * Original :88-99,145-155: the block in front of the input side, shrunk by 0.1875 on every side. A horizontal input facing a
     * double-lane belt moves the box half a block toward the grabber, a triple-lane belt 0.67 blocks, so only the nearest lane is
     * reached; the shifted box then also reaches into the grabber's own block, which the original accepts (:139-144).
     */
    private List<MovingItem> itemsInReach(Direction inputSide) {
        double reach = 1D;

        if(inputSide.getAxis() != Direction.Axis.Y) {
            BlockState lane = this.level.getBlockState(this.worldPosition.relative(inputSide));
            if(lane.is(NtmBlocks.CONVEYOR_DOUBLE.get())) reach = 0.5D;
            if(lane.is(NtmBlocks.CONVEYOR_TRIPLE.get())) reach = 0.33D;
        }

        double x = this.worldPosition.getX() + inputSide.getStepX() * reach;
        double y = this.worldPosition.getY() + inputSide.getStepY() * reach;
        double z = this.worldPosition.getZ() + inputSide.getStepZ() * reach;

        return this.level.getEntitiesOfClass(MovingItem.class, new AABB(x + 0.1875D, y + 0.1875D, z + 0.1875D, x + 0.8125D, y + 0.8125D, z + 0.8125D));
    }

    /** Original :209-220: any filled filter slot matching. */
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

    /** Original :254-257. */
    @Override
    public int[] getFilterSlots() {
        return new int[] { 0, 9 };
    }

    /** The original base class opens no slot to automation (TileEntityMachineBase.java:135-138); NEO's base opens slot 0. */
    @Override
    public int[] getSlotsForFace(Direction side) {
        return NO_SLOTS;
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeBoolean(this.isWhitelist);
        this.matcher.serialize(buf);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.isWhitelist = buf.readBoolean();
        this.matcher.deserialize(buf);
    }

    /** Original :233-247. */
    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.isWhitelist = tag.getBoolean("isWhitelist");
        this.matcher.readFromNBT(tag);
        this.lastGrabbedTick = tag.getLong("lastGrabbedTick");
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putBoolean("isWhitelist", this.isWhitelist);
        this.matcher.writeToNBT(tag);
        tag.putLong("lastGrabbedTick", this.lastGrabbedTick);
    }

    /** Original :260-267: "whitelist" toggles, "slot" fills a filter slot (checked, see IControlReceiverFilter). */
    @Override
    public void receiveControl(CompoundTag tag) {
        if(tag.contains("whitelist")) this.isWhitelist = !this.isWhitelist;
        if(tag.contains("slot") && this.level != null) this.setFilterContents(tag, this.level.registryAccess());
        this.setChanged();
    }

    @Override
    public AbstractContainerMenu createMenu(int containerId, Inventory inventory, Player player) {
        return new CraneGrabberMenu(containerId, inventory, this);
    }
}
