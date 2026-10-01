package com.hbm.blockentity.machine;

import api.hbm.energymk2.IEnergyProviderMK2;
import api.hbm.fluidmk2.IFluidStandardTransceiverMK2;
import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.LoadedBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.DummyableBlock;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.fluid.trait.FT_Coolable;
import com.hbm.inventory.fluid.trait.FT_Coolable.CoolingType;
import com.hbm.registry.NtmSoundEvents;
import com.hbm.util.fauxpointtwelve.DirPos;
import io.netty.buffer.ByteBuf;
import io.netty.buffer.Unpooled;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Mth;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;

public class MachineSteamEngineBlockEntity extends LoadedBaseBlockEntity implements ITickable, IEnergyProviderMK2, IFluidStandardTransceiverMK2 {

    // The original's machine config "steamengine" (steamCap, ldsCap, efficiency); NEO has no such config.
    public static final int STEAM_CAPACITY = 2_000;
    public static final int SPENT_STEAM_CAPACITY = 20;
    public static final double EFFICIENCY = 0.85D;

    public long powerBuffer;

    public float rotor;
    public float lastRotor;
    private float syncRotor;
    public final FluidTank[] tanks;

    private int turnProgress;
    private float acceleration = 0F;

    /** This tick's sync data from the steam tank on, written before the steam is used, as in the original. */
    protected ByteBuf buf;
    private AABB renderBox;

    public MachineSteamEngineBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.MACHINE_STEAM_ENGINE.get(), pos, state);

        this.tanks = new FluidTank[] {
                new FluidTank(Fluids.STEAM, STEAM_CAPACITY),
                new FluidTank(Fluids.SPENTSTEAM, SPENT_STEAM_CAPACITY)
        };
    }

    @Override
    public void updateEntity() {
        if(this.level == null) return;

        if(!this.level.isClientSide) {

            if(this.buf != null) this.buf.release();
            this.buf = Unpooled.buffer();

            this.powerBuffer = 0;
            float previousAcceleration = this.acceleration;

            this.tanks[0].setTankType(Fluids.STEAM);
            this.tanks[1].setTankType(Fluids.SPENTSTEAM);

            DirPos[] ports = this.getConPos();
            for(DirPos pos : ports) {
                this.trySubscribe(this.tanks[0].getTankType(), this.level, pos);
            }

            this.tanks[0].serialize(this.buf);

            FT_Coolable trait = this.tanks[0].getTankType().getTrait(FT_Coolable.class);
            double eff = trait.getEfficiency(CoolingType.TURBINE) * EFFICIENCY;

            int inputOps = this.tanks[0].getFill() / trait.amountReq;
            int outputOps = (this.tanks[1].getMaxFill() - this.tanks[1].getFill()) / trait.amountProduced;
            int ops = Math.min(inputOps, outputOps);
            this.tanks[0].setFill(this.tanks[0].getFill() - ops * trait.amountReq);
            this.tanks[1].setFill(this.tanks[1].getFill() + ops * trait.amountProduced);
            this.powerBuffer += (ops * trait.heatEnergy * eff);

            if(ops > 0) {
                this.acceleration += 0.1F;
            } else {
                this.acceleration -= 0.1F;
            }

            this.acceleration = Mth.clamp(this.acceleration, 0F, 40F);
            this.rotor += this.acceleration;

            if(this.rotor >= 360D) {
                this.rotor -= 360D;

                BlockPos pos = this.worldPosition;
                this.level.playSound(null, pos.getX(), pos.getY(), pos.getZ(), NtmSoundEvents.STEAM_ENGINE_OPERATE.get(), SoundSource.BLOCKS, this.getVolume(1.0F), 0.5F + (this.acceleration / 80F));
            }

            // Local strengthening, as for the Stirling engine: the original never marks the tile dirty, and 1.21
            // only saves chunks marked unsaved.
            if(ops > 0 || this.acceleration != previousAcceleration) this.setChanged();

            this.buf.writeLong(this.powerBuffer);
            this.buf.writeFloat(this.rotor);
            this.tanks[1].serialize(this.buf);

            // The original registers its ports before this tick's run; the networks transfer after all block
            // entities have ticked either way, so the powerBuffer computed above is what they see.
            for(DirPos pos : ports) {
                this.tryProvide(this.level, pos.makeCompat(), pos.getDir());
                this.tryProvide(this.tanks[1], this.level, pos);
            }

            this.networkPackNT(150);
        } else {
            this.lastRotor = this.rotor;

            if(this.turnProgress > 0) {
                double d = Mth.wrapDegrees(this.syncRotor - (double) this.rotor);
                this.rotor = (float) ((double) this.rotor + d / (double) this.turnProgress);
                --this.turnProgress;
            } else {
                this.rotor = this.syncRotor;
            }
        }
    }

    /** The side the ports face: clockwise from the placement direction, as the original's {@code getRotation(UP)}. */
    public static Direction getPortSide(Direction facing) {
        return facing.getClockWise();
    }

    /** Three connections one block outside the upper proxies, all on the port side; power and fluid share them. */
    public DirPos[] getConPos() {
        Direction dir = this.getBlockState().getValue(DummyableBlock.FACING);
        Direction rot = getPortSide(dir);
        BlockPos pos = this.worldPosition;

        return new DirPos[] {
                new DirPos(pos.getX() + rot.getStepX() * 2, pos.getY() + 1, pos.getZ() + rot.getStepZ() * 2, rot),
                new DirPos(pos.getX() + rot.getStepX() * 2 + dir.getStepX(), pos.getY() + 1, pos.getZ() + rot.getStepZ() * 2 + dir.getStepZ(), rot),
                new DirPos(pos.getX() + rot.getStepX() * 2 - dir.getStepX(), pos.getY() + 1, pos.getZ() + rot.getStepZ() * 2 - dir.getStepZ(), rot)
        };
    }

    public float getAcceleration() {
        return this.acceleration;
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeBytes(this.buf);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.tanks[0].deserialize(buf);
        this.powerBuffer = buf.readLong();
        this.syncRotor = buf.readFloat();
        this.tanks[1].deserialize(buf);
        this.turnProgress = 3; // use 3-ply for extra smoothness
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.powerBuffer = tag.getLong("powerBuffer");
        this.acceleration = tag.getFloat("acceleration");
        this.tanks[0].readFromNBT(tag, "s");
        this.tanks[1].readFromNBT(tag, "w");
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putLong("powerBuffer", this.powerBuffer);
        tag.putFloat("acceleration", this.acceleration);
        this.tanks[0].writeToNBT(tag, "s");
        this.tanks[1].writeToNBT(tag, "w");
    }

    /** Power only on the sides; fluids keep the default connection rule, as in the original. */
    @Override
    public boolean canConnect(Direction dir) {
        return dir != null && dir.getAxis().isHorizontal();
    }

    @Override
    public long getPower() {
        return this.powerBuffer;
    }

    @Override
    public long getMaxPower() {
        return this.powerBuffer;
    }

    @Override
    public void setPower(long power) {
        this.powerBuffer = power;
    }

    @Override
    public FluidTank[] getSendingTanks() {
        return new FluidTank[] { this.tanks[1] };
    }

    @Override
    public FluidTank[] getReceivingTanks() {
        return new FluidTank[] { this.tanks[0] };
    }

    @Override
    public FluidTank[] getAllTanks() {
        return this.tanks;
    }

    /** The original renders without bounds; this box covers the 3x7x2 footprint in every facing with room above. */
    public AABB getRenderBoundingBox() {
        if(this.renderBox == null) {
            BlockPos pos = this.worldPosition;
            this.renderBox = new AABB(pos.getX() - 6, pos.getY(), pos.getZ() - 6, pos.getX() + 7, pos.getY() + 3, pos.getZ() + 7);
        }
        return this.renderBox;
    }

    public double getMaxRenderDistanceSquared() {
        return 65536.0D;
    }
}
