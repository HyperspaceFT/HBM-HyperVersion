package com.hbm.blockentity.network;

import api.hbm.conveyor.IConveyorBelt;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.entity.NtmEntityTypes;
import com.hbm.entity.item.MovingPackage;
import com.hbm.inventory.menus.CraneBoxerMenu;
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
import net.minecraft.world.phys.Vec3;

/** Original TileEntityCraneBoxer: a 21-slot buffer packed into moving packages on the belt on the output side. */
public class CraneBoxerBlockEntity extends CraneBaseBlockEntity {

    public static final int[] ACCESS = new int[] { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20 };

    public static final byte MODE_4 = 0;
    public static final byte MODE_8 = 1;
    public static final byte MODE_16 = 2;
    public static final byte MODE_REDSTONE = 3;

    public byte mode = MODE_4;
    private boolean lastRedstone = false;

    public CraneBoxerBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.CRANE_BOXER.get(), pos, state, 21);
    }

    @Override
    protected Component getDefaultName() {
        return Component.translatable("container.craneBoxer");
    }

    /**
     * Original :41-149. In redstone mode the rising edge of the signal packs every filled slot (up to 21 stacks); in the other modes,
     * every second tick of the world time, 4/8/16 full stacks are packed once the buffer holds that many. Stacks that are not full
     * are never packed there. Nothing happens without a belt on the output side. The package holds the stacks in reverse slot order
     * (:68-77,127-136).
     */
    @Override
    public void updateEntity() {
        if(this.level == null || this.level.isClientSide) return;

        boolean redstone = this.level.hasNeighborSignal(this.worldPosition);

        if(this.mode == MODE_REDSTONE && redstone && !this.lastRedstone) {
            int pack = 0;

            for(ItemStack stack : this.slots) {
                if(!stack.isEmpty()) pack++;
            }

            IConveyorBelt belt = this.outputBelt();

            if(belt != null && pack > 0) {
                ItemStack[] box = new ItemStack[pack];

                for(int i = 0; i < this.slots.size() && pack > 0; i++) {
                    if(!this.slots.get(i).isEmpty()) {
                        pack--;
                        box[pack] = this.slots.get(i).copy();
                        this.slots.set(i, ItemStack.EMPTY);
                    }
                }

                this.sendPackage(box, belt);
            }
        }

        // saved (:176-184) so that reloading a powered boxer does not see a new rising edge; marked so the save keeps it
        if(this.lastRedstone != redstone) {
            this.lastRedstone = redstone;
            this.setChanged();
        }

        if(this.mode != MODE_REDSTONE && this.level.getGameTime() % 2 == 0) {
            int pack = switch(this.mode) {
                case MODE_8 -> 8;
                case MODE_16 -> 16;
                default -> 4;
            };

            int fullStacks = 0;

            for(ItemStack stack : this.slots) {
                if(isFull(stack)) fullStacks++;
            }

            IConveyorBelt belt = this.outputBelt();

            if(belt != null && fullStacks >= pack) {
                ItemStack[] box = new ItemStack[pack];

                for(int i = 0; i < this.slots.size() && pack > 0; i++) {
                    if(isFull(this.slots.get(i))) {
                        pack--;
                        box[pack] = this.slots.get(i).copy();
                        this.slots.set(i, ItemStack.EMPTY);
                    }
                }

                this.sendPackage(box, belt);
            }
        }

        this.networkPackNT(15);
    }

    private static boolean isFull(ItemStack stack) {
        return !stack.isEmpty() && stack.getCount() == stack.getMaxStackSize();
    }

    private IConveyorBelt outputBelt() {
        Block b = this.level.getBlockState(this.worldPosition.relative(this.getOutputSide())).getBlock();
        return b instanceof IConveyorBelt belt ? belt : null;
    }

    /** Original :79-84,138-143: 0.55 blocks toward the output side, snapped onto the belt. */
    private void sendPackage(ItemStack[] box, IConveyorBelt belt) {
        Direction outputSide = this.getOutputSide();
        BlockPos beltPos = this.worldPosition.relative(outputSide);
        Vec3 pos = Vec3.atCenterOf(this.worldPosition).add(outputSide.getStepX() * 0.55, outputSide.getStepY() * 0.55, outputSide.getStepZ() * 0.55);
        Vec3 snap = belt.getClosestSnappingPosition(this.level, beltPos, pos);

        MovingPackage moving = new MovingPackage(NtmEntityTypes.MOVING_PACKAGE.get(), this.level);
        moving.moveTo(snap.x, snap.y, snap.z, 0, 0);
        moving.setItemStacks(box);
        this.level.addFreshEntity(moving);
        this.setChanged();
    }

    /** Original :163-171: every slot from every side, but nothing can be taken out (the base class never allows it). */
    @Override
    public int[] getSlotsForFace(Direction side) {
        return ACCESS;
    }

    @Override
    public boolean canPlaceItem(int slot, ItemStack stack) {
        return slot >= 0 && slot < 21;
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeByte(this.mode);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.mode = buf.readByte();
    }

    /** Original :173-184. */
    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.mode = tag.getByte("mode");
        this.lastRedstone = tag.getBoolean("lastRedstone");
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putByte("mode", this.mode);
        tag.putBoolean("lastRedstone", this.lastRedstone);
    }

    /** Original :203-208: "toggle" cycles the four modes. */
    @Override
    public void receiveControl(CompoundTag tag) {
        if(tag.contains("toggle")) {
            this.mode = (byte) ((this.mode + 1) % 4);
            this.setChanged();
        }
    }

    @Override
    public AbstractContainerMenu createMenu(int containerId, Inventory inventory, Player player) {
        return new CraneBoxerMenu(containerId, inventory, this);
    }
}
