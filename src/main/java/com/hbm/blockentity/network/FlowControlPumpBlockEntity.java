package com.hbm.blockentity.network;

import api.hbm.energymk2.IEnergyReceiverMK2.ConnectionPriority;
import api.hbm.fluidmk2.IFluidStandardTransceiverMK2;
import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.LoadedBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.DummyableBlock;
import com.hbm.interfaces.IControlReceiver;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.util.EnumUtil;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Flow control pump (original FlowControlPump.java:118-296): a three block pump that takes fluid from the network on one side and
 * passes up to its buffer size per tick to the network on the other, with a pressure and a priority set in its screen. Redstone on
 * the core or either side stops it. The original's ports are TilePort nodes; NEO keeps the old model, so the core subscribes to the
 * duct beyond the input side and provides to the duct beyond the output side every tick.
 */
public class FlowControlPumpBlockEntity extends LoadedBaseBlockEntity implements ITickable, IFluidStandardTransceiverMK2, IControlReceiver {

    public static final int MAX_BUFFER = 10_000;
    public static final int MAX_PRESSURE = 5;
    public static final float ROTOR_ACCELERATION = 1F;

    public int bufferSize = 100;
    public FluidTank[] tank;
    public ConnectionPriority priority = ConnectionPriority.NORMAL;
    public boolean redstone = false;

    public boolean topRail = false;
    public boolean bottomRail = true;
    public boolean isWorking = false;

    public float rotor;
    public float prevRotor;
    public float rotorSpeed;

    public FlowControlPumpBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.FLOW_CONTROL_PUMP.get(), pos, state);
        this.tank = new FluidTank[] { new FluidTank(Fluids.NONE, this.bufferSize) };
    }

    public Direction getFacing() {
        BlockState state = this.getBlockState();
        return state.hasProperty(DummyableBlock.FACING) ? state.getValue(DummyableBlock.FACING) : Direction.NORTH;
    }

    /** The original's getRotation(DOWN), the output side (FlowControlPump.java:142-148); its opposite is the input side. */
    public Direction getOutDir() {
        return this.getFacing().getCounterClockWise();
    }

    /** The duct cell beyond the output side block. */
    public DirPos getOutPos() {
        Direction dir = this.getOutDir();
        return new DirPos(this.worldPosition.relative(dir, 2), dir);
    }

    /** The duct cell beyond the input side block (the original's getRotation(UP), :149-155). */
    public DirPos getInPos() {
        Direction dir = this.getOutDir().getOpposite();
        return new DirPos(this.worldPosition.relative(dir, 2), dir);
    }

    /** Only the two side faces of the pump take a duct (FlowControlPump.java:157-161). */
    @Override
    public boolean canConnect(FluidType type, Direction dir) {
        Direction rot = this.getOutDir();
        return dir == rot || dir == rot.getOpposite();
    }

    @Override
    public void updateEntity() {
        if(this.level == null) return;

        if(!this.level.isClientSide) {

            this.trySubscribe(this.tank[0].getTankType(), this.level, this.getInPos());
            this.tryProvide(this.tank[0], this.level, this.getOutPos());

            // if the capacity were changed directly, any excess buffered fluid would be destroyed
            // when running a closed loop or handling hard to get fluids, that's quite bad
            if(this.bufferMismatch()) {
                int nextBuffer = Math.max(this.tank[0].getFill(), this.bufferSize);
                this.tank[0].changeTankSize(nextBuffer);
            }

            Direction dir = this.getOutDir();
            this.redstone = this.level.hasNeighborSignal(this.worldPosition)
                    || this.level.hasNeighborSignal(this.worldPosition.relative(dir))
                    || this.level.hasNeighborSignal(this.worldPosition.relative(dir.getOpposite()));

            this.networkPackNT(50);
            this.isWorking = false;
        } else {

            if(this.level.getGameTime() % 20 == 0) {
                this.topRail = !this.level.getBlockState(this.worldPosition.above()).isAir();
                this.bottomRail = !this.level.getBlockState(this.worldPosition.below()).isAir();
            }

            if(this.isWorking) this.rotorSpeed += ROTOR_ACCELERATION;
            else this.rotorSpeed -= ROTOR_ACCELERATION;

            this.rotorSpeed = Mth.clamp(this.rotorSpeed, 0F, 30F);

            this.prevRotor = this.rotor;
            this.rotor += this.rotorSpeed;

            if(this.rotor >= 360F) {
                this.rotor -= 360F;
                this.prevRotor -= 360F;
            }
        }
    }

    /** Only fluid of the buffer's type and pressure leaves it (FlowControlPump.java:208-219). */
    @Override
    public void useUpFluid(FluidType type, int pressure, long amount) {
        if(amount > 0 && this.tank[0].getTankType() == type && this.tank[0].getPressure() == pressure) {
            int toRem = (int) Math.min(amount, this.tank[0].getFill());
            this.tank[0].setFill(this.tank[0].getFill() - toRem);
            this.isWorking = true;
        }
    }

    public boolean bufferMismatch() {
        return this.bufferSize != this.tank[0].getMaxFill();
    }

    @Override public ConnectionPriority getFluidPriority() { return this.priority; }
    @Override public FluidTank[] getSendingTanks() { return this.tank; }
    @Override public FluidTank[] getReceivingTanks() { return this.tank; }
    @Override public FluidTank[] getAllTanks() { return this.tank; }

    @Override public long getReceiverSpeed(FluidType type, int pressure) { return this.redstone || this.bufferMismatch() ? 0 : 1_000_000_000; }
    @Override public long getProviderSpeed(FluidType type, int pressure) { return this.redstone ? 0 : 1_000_000_000; }

    /** Within 128 squared blocks of the core's centre (FlowControlPump.java:269-272). */
    @Override
    public boolean hasPermission(Player player) {
        return player.distanceToSqr(this.worldPosition.getX() + 0.5D, this.worldPosition.getY() + 0.5D, this.worldPosition.getZ() + 0.5D) <= 128;
    }

    /** Buffer 0 to 10,000, pressure 0 to 5 and the priority, clamped on the server (FlowControlPump.java:274-281). */
    @Override
    public void receiveControl(CompoundTag tag) {
        if(tag.contains("capacity")) this.bufferSize = Mth.clamp(tag.getInt("capacity"), 0, MAX_BUFFER);
        if(tag.contains("pressure")) this.tank[0].withPressure(Mth.clamp(tag.getByte("pressure"), 0, MAX_PRESSURE));
        if(tag.contains("priority")) this.priority = EnumUtil.grabEnumSafely(ConnectionPriority.class, tag.getByte("priority"));
        this.setChanged();
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.tank[0].readFromNBT(tag, "t");
        this.priority = EnumUtil.grabEnumSafely(ConnectionPriority.class, tag.getByte("p"));
        this.bufferSize = tag.getInt("buffer");
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        this.tank[0].writeToNBT(tag, "t");
        tag.putByte("p", (byte) this.priority.ordinal());
        tag.putInt("buffer", this.bufferSize);
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        this.tank[0].serialize(buf);
        buf.writeByte((byte) this.priority.ordinal());
        buf.writeInt(this.bufferSize);
        buf.writeBoolean(this.redstone);
        buf.writeBoolean(this.isWorking);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.tank[0].deserialize(buf);
        this.priority = EnumUtil.grabEnumSafely(ConnectionPriority.class, buf.readByte());
        this.bufferSize = buf.readInt();
        this.redstone = buf.readBoolean();
        this.isWorking = buf.readBoolean();
    }
}
