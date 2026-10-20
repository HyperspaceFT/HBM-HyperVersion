package com.hbm.blockentity.machine.rbmk;

import api.hbm.redstoneoverradio.IRORValueProvider;
import com.hbm.entity.projectile.RBMKDebris.DebrisType;
import net.minecraft.core.BlockPos;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Original TileEntityRBMKControl: the shared part of the manual and the automatic control rods, a column without slots (the
 * original SlottedBase(0)) whose rods move towards a target insertion. The power fields and ports (hasPower, power, consumption,
 * maxPower, isPowered, IEnergyReceiverMK2) belong to the ReaSim control rods (Goal 26) and are not ported; without them the rods
 * always move, as the original's hasPower is always true for these blocks. The OpenComputers callbacks are not ported (GOAL24
 * decision 6).
 * <p>
 * The insertion keeps the original's field name {@code level}, which hides BlockEntity.level; this class and its subclasses reach
 * the world through {@link #getLevel()}.
 */
public abstract class RBMKControlBlockEntity extends RBMKSlottedBaseBlockEntity implements IRORValueProvider {

    public double lastLevel;
    public double level;
    public static final double speed = 0.00277D; // it takes around 18 seconds for the thing to fully extend
    public double targetLevel;

    public RBMKControlBlockEntity(BlockEntityType<? extends RBMKControlBlockEntity> type, BlockPos pos, BlockState state) {
        super(type, pos, state, 0);
    }

    // Original :59-62: the lid is part of the column, so hasLid() is always true (RBMKBaseBlock.hasOwnLid raises the collision for it).
    @Override
    public boolean isLidRemovable() {
        return false;
    }

    /** Original updateEntity (:76-112). The ticker runs on both sides; the client only copies level into lastLevel for the render interpolation. */
    @Override
    public void updateEntity() {
        Level world = this.getLevel();
        if(world == null) return;

        if(world.isClientSide) {
            this.lastLevel = this.level;

        } else {

            this.lastLevel = this.level;

            if(level < targetLevel) {
                level += speed * RBMKDials.getControlSpeed();
                if(level > targetLevel) level = targetLevel;
            }

            if(level > targetLevel) {
                level -= speed * RBMKDials.getControlSpeed();
                if(level < targetLevel) level = targetLevel;
            }

            // NEO: mark the chunk so the moved rods are saved.
            if(level != lastLevel) this.setChanged();
        }

        super.updateEntity();
    }

    public void setTarget(double target) {
        this.targetLevel = target;
    }

    public double getMult() {
        return this.level;
    }

    @Override
    public int trackingRange() {
        return 100;
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);

        this.level = tag.getDouble("level");
        this.targetLevel = tag.getDouble("targetLevel");
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);

        tag.putDouble("level", this.level);
        tag.putDouble("targetLevel", this.targetLevel);
    }

    // The original also sends power and hasPower (ReaSim only, not ported).
    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeDouble(this.level);
        buf.writeDouble(this.targetLevel);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.level = buf.readDouble();
        this.targetLevel = buf.readDouble();
    }

    /** Original writeToNBT's DODD dump: the subclasses add their keys after calling super. */
    @Override
    public void getDiagData(CompoundTag nbt) {
        super.getDiagData(nbt);

        nbt.putDouble("level", this.level);
        nbt.putDouble("targetLevel", this.targetLevel);
    }

    /** Original onMelt (:167-186): graphite from a moderated column, then the boron rods; no lid debris (the base onMelt is not called). */
    @Override
    public void onMelt(int reduce) {

        Level world = this.getLevel();

        if(this.isModerated()) {

            int count = 2 + world.random.nextInt(2);

            for(int i = 0; i < count; i++) {
                spawnDebris(DebrisType.GRAPHITE);
            }
        }

        int count = 2 + world.random.nextInt(2);

        for(int i = 0; i < count; i++) {
            spawnDebris(DebrisType.ROD);
        }

        this.standardMelt(reduce);
    }

    @Override
    public RBMKType getRBMKType() {
        return RBMKType.CONTROL_ROD;
    }

    /** Original :193-199 builds a compound with level and targetLevel only; NEO adds them to the base heat/maxHeat (24C convention). */
    @Override
    public CompoundTag getNBTForConsole() {
        CompoundTag data = super.getNBTForConsole();
        data.putDouble("level", this.level);
        data.putDouble("targetLevel", this.targetLevel);
        return data;
    }

    @Override
    public String[] getFunctionInfo() {
        return new String[] {
                PREFIX_VALUE + "extraction"
        };
    }

    @Override
    public String provideRORValue(String name) {
        if((PREFIX_VALUE + "extraction").equals(name))      return "" + (int) (this.level * 100);
        return null;
    }
}
