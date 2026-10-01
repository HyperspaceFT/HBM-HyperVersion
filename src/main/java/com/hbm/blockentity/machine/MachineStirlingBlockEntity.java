package com.hbm.blockentity.machine;

import api.hbm.energymk2.IEnergyProviderMK2;
import api.hbm.tile.IHeatSource;
import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.LoadedBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.DummyableBlock;
import com.hbm.entity.projectile.StrayCog;
import com.hbm.explosion.vanillant.ExplosionVNT;
import com.hbm.inventory.MetaHelper;
import com.hbm.items.NtmItems;
import com.hbm.registry.NtmSoundEvents;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;

public class MachineStirlingBlockEntity extends LoadedBaseBlockEntity implements ITickable, IEnergyProviderMK2 {

    public static final double DIFFUSION = 0.1D;
    public static final double EFFICIENCY = 0.5D;
    public static final int MAX_HEAT = 300;
    public static final int OVERSPEED_LIMIT = 300;

    public long powerBuffer;
    public int heat;
    private int warnCooldown = 0;
    private int overspeed = 0;
    public boolean hasCog = true;

    public float spin;
    public float lastSpin;

    private AABB renderBox;

    public MachineStirlingBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.MACHINE_STIRLING.get(), pos, state);
    }

    @Override
    public void updateEntity() {
        if(this.level == null) return;

        if(!this.level.isClientSide) {
            boolean previousCog = this.hasCog;
            int previousOverspeed = this.overspeed;

            if(this.hasCog) {
                this.powerBuffer = 0;
                this.tryPullHeat();

                this.powerBuffer = (long) (this.heat * EFFICIENCY);

                if(this.warnCooldown > 0)
                    this.warnCooldown--;

                if(this.heat > MAX_HEAT) {

                    this.overspeed++;

                    if(this.overspeed > 60 && this.warnCooldown == 0) {
                        this.warnCooldown = 100;
                        BlockPos pos = this.worldPosition;
                        this.level.playSound(null, pos.getX() + 0.5, pos.getY() + 1, pos.getZ() + 0.5, NtmSoundEvents.WARN_OVERSPEED.get(), SoundSource.BLOCKS, 2.0F, 1.0F);
                    }

                    if(this.overspeed > OVERSPEED_LIMIT) {
                        this.destroyCog();
                    }

                } else {
                    this.overspeed = 0;
                }
            } else {
                this.overspeed = 0;
                this.warnCooldown = 0;
            }

            // Local strengthening over the original, which only marked the tile dirty on destruction:
            // cog and overspeed state are persisted whenever they change. powerBuffer changes every tick
            // and is deliberately not marked on its own.
            if(this.hasCog != previousCog || this.overspeed != previousOverspeed) this.setChanged();

            this.networkPackNT(150);

            if(this.hasCog) {
                for(DirPos pos : this.getConPos()) {
                    this.tryProvide(this.level, pos.makeCompat(), pos.getDir());
                }
            } else {

                if(this.powerBuffer > 0)
                    this.powerBuffer--;
            }

            this.heat = 0;
        } else {

            float momentum = this.powerBuffer * 50F / ((float) MAX_HEAT);

            this.lastSpin = this.spin;
            this.spin += momentum;

            if(this.spin >= 360F) {
                this.spin -= 360F;
                this.lastSpin -= 360F;
            }
        }
    }

    private void destroyCog() {
        BlockPos pos = this.worldPosition;
        this.hasCog = false;
        ExplosionVNT.newExplosion(this.level, null, pos.getX() + 0.5, pos.getY() + 1, pos.getZ() + 0.5, 5F, false, false);

        // FACING matches the original metadata orientation; 3D data values use the same DOWN/UP/N/S/W/E order as ForgeDirection.
        Direction dir = this.getBlockState().getValue(DummyableBlock.FACING);
        StrayCog cog = new StrayCog(this.level, pos.getX() + 0.5 + dir.getStepX(), pos.getY() + 1, pos.getZ() + 0.5 + dir.getStepZ())
                .setOrientation(dir.get3DDataValue())
                .setMeta(0);
        // ForgeDirection.getRotation(DOWN) turns counter-clockwise when seen from above.
        Direction rot = dir.getCounterClockWise();
        cog.setDeltaMovement(rot.getStepX(), 1 + (this.heat - MAX_HEAT) * 0.0001D, rot.getStepZ());
        this.level.addFreshEntity(cog);

        this.setChanged();
    }

    /**
     * Installs a large gear from the held stack. Only the plain (meta 0) gear fits the normal engine.
     * The caller plays the install sound at the clicked position, like the original.
     */
    public boolean tryInstallGear(ItemStack held) {
        if(this.hasCog) return false;
        if(!held.is(NtmItems.GEAR_LARGE.get())) return false;
        if(MetaHelper.getMeta(held) != 0) return false;

        held.shrink(1);
        this.hasCog = true;
        this.setChanged();
        return true;
    }

    /** Item meta of the engine when it drops: the plain stack (no META component) keeps its gear, meta 1 is gearless. */
    public int getDropMeta() {
        return this.hasCog ? 0 : 1;
    }

    public DirPos[] getConPos() {
        BlockPos pos = this.worldPosition;
        return new DirPos[] {
                new DirPos(pos.getX() + 2, pos.getY(), pos.getZ(), Direction.EAST),
                new DirPos(pos.getX() - 2, pos.getY(), pos.getZ(), Direction.WEST),
                new DirPos(pos.getX(), pos.getY(), pos.getZ() + 2, Direction.SOUTH),
                new DirPos(pos.getX(), pos.getY(), pos.getZ() - 2, Direction.NORTH)
        };
    }

    protected void tryPullHeat() {
        BlockEntity con = this.level.getBlockEntity(this.worldPosition.below());

        if(con instanceof IHeatSource source) {
            int heatSrc = (int) (source.getHeatStored() * DIFFUSION);

            if(heatSrc > 0) {
                source.useUpHeat(heatSrc);
                this.heat += heatSrc;
                return;
            }
        }

        this.heat = Math.max(this.heat - Math.max(this.heat / 1000, 1), 0);
    }

    public int getWarnCooldown() {
        return this.warnCooldown;
    }

    public int getOverspeed() {
        return this.overspeed;
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeLong(this.powerBuffer);
        buf.writeInt(this.heat);
        buf.writeBoolean(this.hasCog);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.powerBuffer = buf.readLong();
        this.heat = buf.readInt();
        this.hasCog = buf.readBoolean();
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.powerBuffer = tag.getLong("powerBuffer");
        this.hasCog = tag.getBoolean("hasCog");
        this.overspeed = tag.getInt("overspeed");
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putLong("powerBuffer", this.powerBuffer);
        tag.putBoolean("hasCog", this.hasCog);
        tag.putInt("overspeed", this.overspeed);
    }

    @Override
    public void setPower(long power) {
        this.powerBuffer = power;
    }

    @Override
    public long getPower() {
        return this.powerBuffer;
    }

    @Override
    public long getMaxPower() {
        return this.powerBuffer;
    }

    /** Without the cog nothing is delivered, so the leftover buffer only spins down the animation (original getProviderSpeed). */
    @Override
    public long getProviderSpeed() {
        return this.hasCog ? this.getMaxPower() : 0;
    }

    public AABB getRenderBoundingBox() {
        if(this.renderBox == null) {
            BlockPos pos = this.worldPosition;
            this.renderBox = new AABB(pos.getX() - 1, pos.getY(), pos.getZ() - 1, pos.getX() + 2, pos.getY() + 2, pos.getZ() + 2);
        }
        return this.renderBox;
    }
}
