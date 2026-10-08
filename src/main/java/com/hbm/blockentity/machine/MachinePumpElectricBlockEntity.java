package com.hbm.blockentity.machine;

import api.hbm.energymk2.IEnergyReceiverMK2;
import api.hbm.fluidmk2.IFluidStandardTransceiverMK2;
import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.LoadedBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.NtmBlocks;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.main.NuclearTechMod;
import com.hbm.registry.NtmSoundEvents;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;

import java.util.Set;

/**
 * The original's TileEntityMachinePumpElectric with the shared parts of TileEntityMachinePumpBase; the steam pump is
 * not ported, so there is no common base class yet.
 * <p>
 * Neither original class reads or writes NBT, so power and water are not saved here either: a reloaded pump starts
 * empty and refills its tank within at most 100 operations.
 */
public class MachinePumpElectricBlockEntity extends LoadedBaseBlockEntity implements ITickable, IEnergyReceiverMK2, IFluidStandardTransceiverMK2 {

    // The original's machine config "waterpump" (groundHeight, groundDepth, electricSpeed); NEO has no such config.
    public static final int GROUND_HEIGHT = 70;
    public static final int GROUND_DEPTH = 4;
    public static final int ELECTRIC_SPEED = 10_000;
    public static final long MAX_POWER = 10_000L;

    /** Built on first use: the NTM blocks are deferred and cannot be resolved while this class initialises. */
    private static Set<Block> validBlocks;

    public long power;
    public final FluidTank water;

    public boolean isOn = false;
    public boolean onGround = false;
    public float rotor;
    public float lastRotor;

    private AABB renderBox;

    public MachinePumpElectricBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.PUMP_ELECTRIC.get(), pos, state);
        this.water = new FluidTank(Fluids.WATER, ELECTRIC_SPEED * 100);
    }

    /**
     * The original's validBlocks. Its plain dirt and sand match on the block alone, so coarse dirt, podzol and red sand
     * (the dirt and sand metadata variants) count as well. NEO has no dirty sand blocks, so those are not listed.
     */
    public static Set<Block> getValidBlocks() {
        if(validBlocks == null) {
            validBlocks = Set.of(
                    Blocks.GRASS_BLOCK,
                    Blocks.DIRT,
                    Blocks.COARSE_DIRT,
                    Blocks.PODZOL,
                    Blocks.SAND,
                    Blocks.RED_SAND,
                    Blocks.MYCELIUM,
                    NtmBlocks.WASTE_EARTH.get(),
                    NtmBlocks.DIRT_DEAD.get(),
                    NtmBlocks.DIRT_OILY.get()
            );
        }
        return validBlocks;
    }

    @Override
    public void updateEntity() {
        if(this.level == null) return;

        if(!this.level.isClientSide) {

            DirPos[] ports = this.getConPos();
            for(DirPos pos : ports) {
                this.trySubscribe(this.level, pos);
            }

            // The original declares a ground check delay but never sets it above 0, so the ground is checked every tick.
            this.onGround = this.checkGround();

            this.isOn = false;
            if(this.canOperate() && this.worldPosition.getY() <= GROUND_HEIGHT && this.onGround) {
                this.isOn = true;
                this.operate();
            }

            for(DirPos pos : ports) {
                this.tryProvide(this.water, this.level, pos);
            }

            this.networkPackNT(150);

        } else {

            this.lastRotor = this.rotor;
            if(this.isOn) this.rotor += 10F;

            if(this.rotor >= 360F) {
                this.rotor -= 360F;
                this.lastRotor -= 360F;

                NuclearTechMod.proxy.playLocalSound(this.getBlockPos().getCenter(), NtmSoundEvents.STEAM_ENGINE_OPERATE.get(), SoundSource.BLOCKS, 0.5F, 0.75F);
                // 1.21's entity.generic.splash is the event behind 1.7.10's game.neutral.swim.splash.
                NuclearTechMod.proxy.playLocalSound(this.getBlockPos().getCenter(), SoundEvents.GENERIC_SPLASH, SoundSource.BLOCKS, 1F, 0.5F);
            }
        }
    }

    protected boolean canOperate() {
        return this.power >= 1_000 && this.water.getFill() < this.water.getMaxFill();
    }

    protected void operate() {
        this.power -= 1_000;
        this.water.setFill(Math.min(this.water.getFill() + ELECTRIC_SPEED, this.water.getMaxFill()));
    }

    /**
     * The original's checkGround: fails in dimensions without a sky, then checks the 3x3 columns GROUND_DEPTH blocks
     * below the core. Every block of the top layer has to be a full solid block, and at least half of all checked
     * blocks have to be valid ground.
     * <p>
     * {@code isRedstoneConductor} stands in for 1.7.10's {@code isNormalCube}: both are true for opaque full cubes such
     * as dirt, sand and stone and false for slabs, glass and leaves. A full collision shape alone is not used because
     * glass would pass it.
     */
    public boolean checkGround() {
        if(this.level == null || !this.level.dimensionType().hasSkyLight()) return false;

        Set<Block> valid = getValidBlocks();
        int validCount = 0;
        int invalidCount = 0;

        for(int x = -1; x <= 1; x++) {
            for(int y = -1; y >= -GROUND_DEPTH; y--) {
                for(int z = -1; z <= 1; z++) {

                    BlockPos pos = this.worldPosition.offset(x, y, z);
                    BlockState state = this.level.getBlockState(pos);

                    if(y == -1 && !state.isRedstoneConductor(this.level, pos)) return false; // first layer has to be full solid

                    if(valid.contains(state.getBlock())) validCount++;
                    else invalidCount++;
                }
            }
        }

        return validCount >= invalidCount; // valid block count has to be at least 50%
    }

    /**
     * The original's TilePortShapes.flare: ports on the core's four horizontal neighbours, fixed to the world axes and
     * independent of the facing. NEO's connection point is the block outside each port, as for the oil well.
     */
    public DirPos[] getConPos() {
        BlockPos pos = this.worldPosition;
        return new DirPos[] {
                new DirPos(pos.offset(0, 0, -2), Direction.NORTH),
                new DirPos(pos.offset(2, 0, 0), Direction.EAST),
                new DirPos(pos.offset(0, 0, 2), Direction.SOUTH),
                new DirPos(pos.offset(-2, 0, 0), Direction.WEST)
        };
    }

    /** The original's order: the base class fields and the tank, then the electric pump's power. */
    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeBoolean(this.isOn);
        buf.writeBoolean(this.onGround);
        this.water.serialize(buf);
        buf.writeLong(this.power);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.isOn = buf.readBoolean();
        this.onGround = buf.readBoolean();
        this.water.deserialize(buf);
        this.power = buf.readLong();
    }

    @Override
    public long getPower() {
        return this.power;
    }

    @Override
    public long getMaxPower() {
        return MAX_POWER;
    }

    @Override
    public void setPower(long power) {
        this.power = power;
    }

    @Override
    public FluidTank[] getSendingTanks() {
        return new FluidTank[] { this.water };
    }

    @Override
    public FluidTank[] getReceivingTanks() {
        return new FluidTank[0];
    }

    @Override
    public FluidTank[] getAllTanks() {
        return new FluidTank[] { this.water };
    }

    public AABB getRenderBoundingBox() {
        if(this.renderBox == null) {
            BlockPos pos = this.worldPosition;
            this.renderBox = new AABB(pos.getX() - 1, pos.getY(), pos.getZ() - 1, pos.getX() + 2, pos.getY() + 5, pos.getZ() + 2);
        }
        return this.renderBox;
    }

    public double getMaxRenderDistanceSquared() {
        return 65536.0D;
    }
}
