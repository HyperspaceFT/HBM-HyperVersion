package com.hbm.blockentity.machine.heater;

import api.hbm.energymk2.IEnergyReceiverMK2;
import api.hbm.tile.IHeatSource;
import com.hbm.blockentity.IBufPacketReceiver;
import com.hbm.blockentity.LoadedBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.DummyableBlock;
import com.hbm.interfaces.ICopiable;
import com.hbm.interfaces.IControlReceiver;
import com.hbm.registry.NtmSoundEvents;
import com.hbm.sound.AudioWrapper;
import com.hbm.util.fauxpointtwelve.DirPos;
import io.netty.buffer.ByteBuf;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import org.jetbrains.annotations.NotNull;

public class HeaterElectricBlockEntity extends LoadedBaseBlockEntity implements IHeatSource, IEnergyReceiverMK2, com.hbm.blockentity.ITickable, IBufPacketReceiver, ICopiable, IControlReceiver {

    public long power;
    public int heatEnergy;
    public boolean isOn;
    // Original default is 0 (off until configured with a screwdriver); existing machines keep their saved setting.
    public int setting = 0;

    private AudioWrapper audio;

    private AABB bb;

    public HeaterElectricBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.HEATER_ELECTRIC.get(), pos, state);
    }

    @Override
    public void updateEntity() {
        if(this.level == null) return;

        if(!this.level.isClientSide) {
            if(this.level.getGameTime() % 20 == 0) {
                Direction facing = this.getBlockState().getValue(DummyableBlock.FACING);
                this.trySubscribe(this.level, this.getBlockPos().relative(facing, 3), facing);
            }

            this.heatEnergy = (int) (this.heatEnergy * 0.999D);
            this.tryPullHeat();

            this.isOn = false;
            if(this.setting > 0 && this.power >= this.getConsumption()) {
                this.power -= this.getConsumption();
                this.heatEnergy += this.getHeatGen();
                this.isOn = true;
            }

            this.networkPackNT(25);
        } else {
            // Original: hum loop while isOn, stopped on the first tick it is off (TileEntityHeaterElectric:70-88); the
            // heater has no audioTime tail like the boilers.
            if(this.isOn) {
                if(this.audio == null) {
                    this.audio = this.createAudioLoop();
                    if(this.audio != null) {
                        this.audio.startSound();
                    }
                } else if(!this.audio.isPlaying()) {
                    this.audio = this.rebootAudio(this.audio);
                }

                if(this.audio != null) {
                    // updateVolume sets the absolute volume; the original does the same, raising the 0.25 start volume to 1 (0.1 when muffled).
                    this.audio.updateVolume(this.getVolume(1F));
                    this.audio.keepAlive();
                }
            } else if(this.audio != null) {
                this.audio.stopSound();
                this.audio = null;
            }
        }
    }

    @Override
    public AudioWrapper createAudioLoop() {
        return AudioWrapper.getLoopedSound(NtmSoundEvents.ELECTRIC_HUM_LOOP.get(), SoundSource.BLOCKS, this, 0.25F, 7.5F, 1.0F, 20);
    }

    @Override
    public void onChunkUnloaded() {
        super.onChunkUnloaded();
        if(this.audio != null) {
            this.audio.stopSound();
            this.audio = null;
        }
    }

    @Override
    public void setRemoved() {
        super.setRemoved();
        if(this.audio != null) {
            this.audio.stopSound();
            this.audio = null;
        }
    }

    protected void tryPullHeat() {
        if(this.level == null) return;
        var con = this.level.getBlockEntity(this.getBlockPos().below());
        if(con instanceof IHeatSource source) {
            this.heatEnergy += (int) (source.getHeatStored() * 0.85D);
            source.useUpHeat(source.getHeatStored());
        }
    }

    public void toggleSettingUp() {
        this.setting++;
        if(this.setting > 10) this.setting = 0;
        this.setChanged();
    }

    public void toggleSettingDown() {
        this.setting--;
        if(this.setting < 0) this.setting = 10;
        this.setChanged();
    }

    public long getConsumption() {
        return (long) (Math.pow(this.setting, 1.4D) * 200D);
    }

    public int getHeatGen() {
        return this.setting * 100;
    }

    @Override
    public long getPower() {
        return this.power;
    }

    @Override
    public long getMaxPower() {
        return this.getConsumption() * 20L;
    }

    @Override
    public void setPower(long power) {
        this.power = power;
    }

    @Override
    public int getHeatStored() {
        return this.heatEnergy;
    }

    @Override
    public void useUpHeat(int heat) {
        // Ignore non-positive amounts, as AbstractHeaterMachineBlockEntity does; a negative value would otherwise add heat (GOAL9A F2).
        if(heat <= 0) return;
        this.heatEnergy = Math.max(0, this.heatEnergy - heat);
        this.setChanged();
    }

    @Override
    public boolean canConnect(Direction dir) {
        return dir != null && dir.getAxis().isHorizontal();
    }

    @Override
    public long transferPower(long power) {
        if(power + this.power <= this.getMaxPower()) {
            this.power += power;
            this.setChanged();
            return 0;
        }

        long capacity = this.getMaxPower() - this.power;
        long overshoot = power - capacity;
        this.power = this.getMaxPower();
        this.setChanged();
        return overshoot;
    }

    @Override
    public boolean hasPermission(Player player) {
        return player.distanceToSqr(this.getBlockPos().getX() + 0.5, this.getBlockPos().getY() + 0.5, this.getBlockPos().getZ() + 0.5) <= 256.0D;
    }

    @Override
    public void receiveControl(CompoundTag tag) {
        if(tag.contains("setting")) {
            this.setting = Math.max(0, Math.min(tag.getInt("setting"), 10));
        }
        this.setChanged();
    }

    @Override
    public void receiveControl(Player player, CompoundTag tag) {
        this.receiveControl(tag);
    }

    @Override
    protected void loadAdditional(CompoundTag tag, net.minecraft.core.HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.power = tag.getLong("power");
        this.heatEnergy = tag.getInt("heatEnergy");
        this.isOn = tag.getBoolean("isOn");
        this.setting = tag.getInt("setting");
    }

    @Override
    protected void saveAdditional(CompoundTag tag, net.minecraft.core.HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putLong("power", this.power);
        tag.putInt("heatEnergy", this.heatEnergy);
        tag.putBoolean("isOn", this.isOn);
        tag.putInt("setting", this.setting);
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeLong(this.power);
        buf.writeInt(this.heatEnergy);
        buf.writeBoolean(this.isOn);
        buf.writeByte(this.setting);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.power = buf.readLong();
        this.heatEnergy = buf.readInt();
        this.isOn = buf.readBoolean();
        this.setting = buf.readByte();
    }

    @Override
    public CompoundTag getSettings(net.minecraft.world.level.Level level, BlockPos pos) {
        CompoundTag tag = new CompoundTag();
        tag.putInt("setting", this.setting);
        return tag;
    }

    @Override
    public void pasteSettings(CompoundTag tag, int index, net.minecraft.world.level.Level level, Player player, BlockPos pos) {
        if(tag.contains("setting")) {
            this.setting = tag.getInt("setting");
        }
    }

    public AABB getRenderBoundingBox() {
        if(this.bb == null) {
            this.bb = new AABB(this.getBlockPos().getX() - 1, this.getBlockPos().getY(), this.getBlockPos().getZ() - 1, this.getBlockPos().getX() + 2, this.getBlockPos().getY() + 2, this.getBlockPos().getZ() + 2);
        }
        return this.bb;
    }

    public double getMaxRenderDistanceSquared() {
        return 65536.0D;
    }
}
