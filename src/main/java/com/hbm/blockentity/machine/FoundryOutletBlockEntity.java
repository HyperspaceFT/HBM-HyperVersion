package com.hbm.blockentity.machine;

import api.hbm.block.ICrucibleAcceptor;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.machine.FoundryOutletBlock;
import com.hbm.inventory.material.Mats;
import com.hbm.inventory.material.NTMMaterial;
import com.hbm.util.CrucibleUtil;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;

/**
 * Upstream TileEntityFoundryOutlet: stores nothing, takes flows from its back and pours them straight down onto the first acceptor
 * within 4 blocks. Redstone (optionally inverted) closes it; a material filter (optionally inverted) limits what passes.
 */
public class FoundryOutletBlockEntity extends FoundryBaseBlockEntity {

    public NTMMaterial filter = null;
    /* inverts filter behavior, will let everything but the filter material pass */
    public boolean invertFilter = false;
    /** inverts redstone behavior, i.e. when TRUE, the outlet will be blocked by default and only open with redstone */
    public boolean invertRedstone = false;

    public FoundryOutletBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.FOUNDRY_OUTLET.get(), pos, state);
    }

    /** if TRUE, prevents all fluids from flowing through the outlet and renders a small barrier */
    public boolean isClosed() {
        return this.level != null && (invertRedstone ^ this.level.hasNeighborSignal(this.worldPosition));
    }

    @Override public boolean canAcceptPartialPour(Level level, BlockPos pos, Vec3 hit, Direction side, Mats.MaterialStack stack) { return false; }
    @Override public Mats.MaterialStack pour(Level level, BlockPos pos, Vec3 hit, Direction side, Mats.MaterialStack stack) { return stack; }

    @Override
    public boolean canAcceptPartialFlow(Level level, BlockPos pos, Direction side, Mats.MaterialStack stack) {

        if(filter != null && (filter != stack.material ^ invertFilter)) return false;
        if(isClosed()) return false;
        if(side != this.getBlockState().getValue(FoundryOutletBlock.FACING).getOpposite()) return false;

        BlockHitResult[] hit = new BlockHitResult[1];
        ICrucibleAcceptor acc = CrucibleUtil.getPouringTarget(level, start(pos), end(pos), hit);

        if(acc == null) {
            return false;
        }

        // upstream passes UP here regardless of the side the stream hits
        return acc.canAcceptPartialPour(level, hit[0].getBlockPos(), hit[0].getLocation(), Direction.UP, stack);
    }

    @Override
    public Mats.MaterialStack flow(Level level, BlockPos pos, Direction side, Mats.MaterialStack stack) {

        BlockHitResult[] hit = new BlockHitResult[1];
        ICrucibleAcceptor acc = CrucibleUtil.getPouringTarget(level, start(pos), end(pos), hit);

        if(acc == null)
            return stack;

        return acc.pour(level, hit[0].getBlockPos(), hit[0].getLocation(), Direction.UP, stack);
    }

    private static Vec3 start(BlockPos pos) {
        return new Vec3(pos.getX() + 0.5D, pos.getY() - 0.125D, pos.getZ() + 0.5D);
    }

    private static Vec3 end(BlockPos pos) {
        return new Vec3(pos.getX() + 0.5D, pos.getY() + 0.125D - 4, pos.getZ() + 0.5D);
    }

    @Override
    public int getCapacity() {
        return 0;
    }

    /**
     * Mirrors the redstone and filter state into the block's CLOSED and FILTERED properties, which only select the lock and filter
     * overlays of the model (upstream's block renderer read the tile entity directly). Server side only.
     */
    public void updateBlockState() {
        if(this.level == null || this.level.isClientSide) return;
        BlockState state = this.getBlockState();
        if(!(state.getBlock() instanceof FoundryOutletBlock)) return;
        BlockState updated = state.setValue(FoundryOutletBlock.CLOSED, this.isClosed()).setValue(FoundryOutletBlock.FILTERED, this.filter != null);
        if(updated != state) this.level.setBlock(this.worldPosition, updated, 3);
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.invertRedstone = tag.getBoolean("invert");
        this.invertFilter = tag.getBoolean("invertFilter");
        this.filter = Mats.matById.get((int) tag.getShort("filter"));
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putBoolean("invert", this.invertRedstone);
        tag.putBoolean("invertFilter", this.invertFilter);
        tag.putShort("filter", this.filter == null ? -1 : (short) this.filter.id);
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeBoolean(this.invertRedstone);
        buf.writeBoolean(this.invertFilter);
        buf.writeInt(this.filter == null ? -1 : this.filter.id);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.invertRedstone = buf.readBoolean();
        this.invertFilter = buf.readBoolean();
        this.filter = Mats.matById.get(buf.readInt());
    }
}
