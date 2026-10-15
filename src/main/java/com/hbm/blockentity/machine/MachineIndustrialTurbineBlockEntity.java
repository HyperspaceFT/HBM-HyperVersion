package com.hbm.blockentity.machine;

import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.DummyableBlock;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.fluid.trait.FT_Coolable;
import com.hbm.inventory.fluid.trait.FT_Coolable.CoolingType;
import com.hbm.main.NuclearTechMod;
import com.hbm.registry.NtmSoundEvents;
import com.hbm.sound.AudioWrapper;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup.Provider;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;

public class MachineIndustrialTurbineBlockEntity extends TurbineBaseBlockEntity {

    // The original's machine config "steamturbineIndustrialMk2" (inputTankSize, outputTankSize, efficiency); NEO has no such config.
    public static final int INPUT_TANK_SIZE = 750_000;
    public static final int OUTPUT_TANK_SIZE = 3_000_000;
    public static final double EFFICIENCY = 1D;

    public float rotor;
    public float lastRotor;

    public double spin = 0;
    public static final double FLYWHEEL_MAX_ENERGY = 0.5e8; //aka flywheel mass
    public long maxPower = 0;
    public long lastPowerTarget = 0;
    public long flywheel_energy = 0;

    private AudioWrapper audio;
    private float audioDesync;

    private AABB renderBox;

    public MachineIndustrialTurbineBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.MACHINE_INDUSTRIAL_TURBINE.get(), pos, state);

        tanks = new FluidTank[2];
        tanks[0] = new FluidTank(Fluids.STEAM, INPUT_TANK_SIZE);
        tanks[1] = new FluidTank(Fluids.SPENTSTEAM, OUTPUT_TANK_SIZE);

        RandomSource rand = RandomSource.create();
        audioDesync = rand.nextFloat() * 0.05F;
    }

    // sets the power target so we know how much this steam type can theoretically make, and increments the spin based on actual throughput
    // The base only calls this when steam was used, so maxPower keeps its last value while idle, as in the original.
    @Override
    public void generatePower(long power, int steamConsumed) {
        FT_Coolable trait = tanks[0].getTankType().getTrait(FT_Coolable.class);
        double eff = trait.getEfficiency(CoolingType.TURBINE) * getEfficiency();
        int maxOps = (int) Math.ceil((tanks[0].getMaxFill() * consumptionPercent()) / trait.amountReq);
        this.maxPower = (long) (maxOps * trait.heatEnergy * eff);

        this.flywheel_energy += power;
    }

    @Override
    public void onServerTick() {
        double spinBefore = this.spin;

        this.spin = (double) flywheel_energy / FLYWHEEL_MAX_ENERGY; //because dense steams have way lower energy output, turbines running them take a lot longer to spool up
        this.lastPowerTarget = Math.min((long) (Math.max(this.spin, 0.05) * maxPower), this.flywheel_energy);
        this.flywheel_energy -= this.lastPowerTarget;
        this.powerBuffer = this.lastPowerTarget;

        // Local strengthening: the original never marks the tile dirty, and 1.21 only saves chunks marked unsaved.
        // Tanks and maxPower only change while operational, the flywheel only then or while it still delivers power.
        if(operational || this.lastPowerTarget != 0 || this.spin != spinBefore) this.setChanged();
    }

    @Override
    public void onClientTick() {
        if(this.level == null) return;

        this.lastRotor = this.rotor;
        float speed = this.spin >= 0.5 ? 30 : (float) (Math.pow(this.spin * 2, 0.5) * 30);
        this.rotor += speed;

        if(this.rotor >= 360) {
            this.lastRotor -= 360;
            this.rotor -= 360;
        }

        BlockPos pos = this.getBlockPos();
        Player player = NuclearTechMod.proxy.me();

        if(this.spin > 0 && player != null && player.distanceToSqr(pos.getX() + 0.5, pos.getY() + 0.5, pos.getZ() + 0.5) <= 35 * 35) {

            float spinNum = (float) Math.min(1F, spin * 2);
            float volume = this.getVolume(0.25F + spinNum * 0.75F);
            float pitch = 0.5F + spinNum * 0.5F + this.audioDesync;

            if(audio == null) {
                audio = AudioWrapper.getLoopedSound(NtmSoundEvents.TURBINE_LARGE_LOOP.get(), SoundSource.BLOCKS, pos.getX() + 0.5F, pos.getY() + 0.5F, pos.getZ() + 0.5F, volume, 20F, pitch, 20);
                audio.startSound();
            }

            audio.keepAlive();
            audio.updatePitch(pitch);
            audio.updateVolume(volume);

        } else {
            if(audio != null) {
                audio.stopSound();
                audio = null;
            }
        }
    }

    @Override
    public DirPos[] getConPos() {
        Direction dir = this.getBlockState().getValue(DummyableBlock.FACING);
        Direction rot = dir.getClockWise();
        BlockPos pos = this.getBlockPos();

        // One block outside each fluid port, in the direction it faces (the original getFluidPorts).
        return new DirPos[] {
                new DirPos(pos.relative(dir, 3).relative(rot, 2), rot),
                new DirPos(pos.relative(dir, 3).relative(rot, -2), rot.getOpposite()),
                new DirPos(pos.relative(dir, -1).relative(rot, 2), rot),
                new DirPos(pos.relative(dir, -1).relative(rot, -2), rot.getOpposite()),
                new DirPos(pos.relative(dir, 3).above(3), Direction.UP),
                new DirPos(pos.relative(dir, -1).above(3), Direction.UP)
        };
    }

    @Override
    public DirPos[] getPowerPos() {
        Direction dir = this.getBlockState().getValue(DummyableBlock.FACING);
        BlockPos pos = this.getBlockPos();

        // One block behind the power port (the original getPowerPorts).
        return new DirPos[] { new DirPos(pos.relative(dir, -4).above(), dir.getOpposite()) };
    }

    @Override
    public boolean canConnect(Direction dir) {
        Direction myDir = this.getBlockState().getValue(DummyableBlock.FACING);
        return dir == myDir.getOpposite();
    }

    @Override
    public boolean canConnect(FluidType type, Direction dir) {
        if(!type.hasTrait(FT_Coolable.class) && type != Fluids.SPENTSTEAM) return false;
        Direction myDir = this.getBlockState().getValue(DummyableBlock.FACING);
        return dir != myDir && dir != myDir.getOpposite();
    }

    @Override public double consumptionPercent() { return 0.2D; }
    @Override public double getEfficiency() { return EFFICIENCY; }
    @Override public boolean doesResizeCompressor() { return true; }

    @Override
    public long transferFluid(FluidType type, int pressure, long amount) {
        long remainder = super.transferFluid(type, pressure, amount);
        if(remainder < amount) this.setChanged();
        return remainder;
    }

    @Override
    public void useUpFluid(FluidType type, int pressure, long amount) {
        long previous = this.getFluidAvailable(type, pressure);
        super.useUpFluid(type, pressure, amount);
        if(this.getFluidAvailable(type, pressure) != previous) this.setChanged();
    }

    @Override
    public void onChunkUnloaded() {
        super.onChunkUnloaded();

        if(audio != null) {
            audio.stopSound();
            audio = null;
        }
    }

    @Override
    public void setRemoved() {
        super.setRemoved();

        if(audio != null) {
            audio.stopSound();
            audio = null;
        }
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeDouble(this.spin);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.spin = buf.readDouble();
    }

    @Override
    protected void loadAdditional(CompoundTag tag, Provider registries) {
        super.loadAdditional(tag, registries);
        lastPowerTarget = tag.getLong("lastPowerTarget");
        flywheel_energy = tag.getLong("flywheel_energy");
        maxPower = tag.getLong("maxPower");
        spin = tag.getDouble("spin");
    }

    @Override
    protected void saveAdditional(CompoundTag tag, Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putLong("lastPowerTarget", lastPowerTarget);
        tag.putLong("flywheel_energy", flywheel_energy);
        tag.putLong("maxPower", maxPower);
        tag.putDouble("spin", spin);
    }

    public AABB getRenderBoundingBox() {
        if(this.renderBox == null) {
            BlockPos pos = this.worldPosition;
            this.renderBox = new AABB(pos.getX() - 3, pos.getY(), pos.getZ() - 3, pos.getX() + 4, pos.getY() + 3, pos.getZ() + 4);
        }
        return this.renderBox;
    }
}
