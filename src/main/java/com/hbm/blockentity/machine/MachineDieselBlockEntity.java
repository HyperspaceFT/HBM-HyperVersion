package com.hbm.blockentity.machine;

import api.hbm.energymk2.IBatteryItem;
import api.hbm.energymk2.IEnergyProviderMK2;
import api.hbm.energymk2.PowerNetMK2;
import api.hbm.fluidmk2.FluidNetMK2;
import api.hbm.fluidmk2.IFluidStandardReceiverMK2;
import com.hbm.blockentity.IFluidCopiable;
import com.hbm.blockentity.MachineBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.interfaces.IControlReceiver;
import com.hbm.inventory.FluidContainerRegistry;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.fluid.trait.FT_Combustible;
import com.hbm.inventory.fluid.trait.FT_Combustible.FuelGrade;
import com.hbm.inventory.menus.MachineDieselMenu;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.IItemFluidIdentifier;
import com.hbm.lib.Library;
import com.hbm.registry.NtmSoundEvents;
import com.hbm.sound.AudioWrapper;
import com.hbm.uninos.NodeNet;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;

import java.util.ArrayList;

/** Standard diesel generator; the original's configurable-machine and exhaust integrations are deferred. */
public class MachineDieselBlockEntity extends MachineBaseBlockEntity implements IEnergyProviderMK2, IFluidStandardReceiverMK2, IControlReceiver, IFluidCopiable {

    public static final long MAX_POWER = 50_000L;
    public static final int FUEL_CAPACITY = 16_000;
    public static final int SLOT_FLUID_IN = 0;
    public static final int SLOT_FLUID_OUT = 1;
    public static final int SLOT_BATTERY = 2;
    public static final int SLOT_IDENTIFIER = 3;
    private static final int[] SLOTS_TOP = { SLOT_FLUID_IN };
    private static final int[] SLOTS_BOTTOM = { SLOT_FLUID_OUT, SLOT_BATTERY };
    private static final int[] SLOTS_SIDE = { SLOT_BATTERY };

    public long power;
    public long powerCap = MAX_POWER;
    public boolean isOn;
    public boolean wasOn;
    public final FluidTank tank = new FluidTank(Fluids.DIESEL, FUEL_CAPACITY);
    private AudioWrapper audio;
    private FluidType subscribedType;

    public MachineDieselBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.MACHINE_DIESEL.get(), pos, state, 4);
    }

    @Override
    protected Component getDefaultName() {
        return Component.translatable("container.machine_diesel");
    }

    public static double getEfficiency(FuelGrade grade) {
        return switch(grade) {
            case MEDIUM -> 0.5D;
            case HIGH -> 0.75D;
            case AERO -> 0.1D;
            default -> 0.0D;
        };
    }

    public static long getHEFromFuel(FluidType type) {
        FT_Combustible fuel = type.getTrait(FT_Combustible.class);
        if(fuel == null || fuel.getGrade() == FuelGrade.LOW) return 0;
        // Preserve the original integer division before applying grade efficiency.
        return (long)(fuel.getCombustionEnergy() / 1000L * getEfficiency(fuel.getGrade()));
    }

    public long getHEFromFuel() { return getHEFromFuel(this.tank.getTankType()); }
    public boolean hasAcceptableFuel() { return this.getHEFromFuel() > 0; }
    public long getPowerScaled(long pixels) { return this.powerCap > 0 ? this.power * pixels / this.powerCap : 0; }

    public DirPos[] getConPos() {
        Direction[] directions = Direction.values();
        DirPos[] positions = new DirPos[directions.length];
        for(int i = 0; i < directions.length; i++) {
            positions[i] = new DirPos(this.worldPosition.relative(directions[i]), directions[i]);
        }
        return positions;
    }

    @Override
    public void updateEntity() {
        if(this.level == null) return;
        if(this.level.isClientSide) {
            this.updateAudio();
            return;
        }

        long previousPower = this.power;
        int previousFill = this.tank.getFill();
        FluidType previousType = this.tank.getTankType();
        if(this.subscribedType != null && this.subscribedType != previousType) this.removeFluidSubscriptions();
        // The original updates fluid/power ports before the identifier, container, battery and burn operations.
        for(DirPos pos : this.getConPos()) {
            this.trySubscribe(previousType, this.level, pos);
            this.tryProvide(this.level, pos.makeCompat(), pos.getDir());
        }
        this.subscribedType = previousType;
        this.wasOn = false;
        boolean changed = this.tank.setType(SLOT_IDENTIFIER, this.slots);
        if(this.tank.getTankType() != previousType) {
            this.removeFluidSubscriptions();
            this.subscribedType = null;
        }
        changed |= this.tank.loadTank(this.level, SLOT_FLUID_IN, SLOT_FLUID_OUT, this.slots);
        this.power = Library.chargeItemsFromTE(this.slots, SLOT_BATTERY, this.power, this.powerCap);
        this.generate();
        if(changed || this.power != previousPower || this.tank.getFill() != previousFill
                || this.tank.getTankType() != previousType) this.setChanged();
        this.networkPackNT(50);
    }

    public void generate() {
        if(this.level == null || this.level.isClientSide || !this.isOn
                || this.level.hasNeighborSignal(this.worldPosition) || !this.hasAcceptableFuel()
                || this.tank.getFill() <= 0) return;
        this.wasOn = true;
        this.tank.setFill(this.tank.getFill() - 1);
        long generated = this.getHEFromFuel();
        // Full buffers still burn 1 mB, matching the original rather than the wood burner's full-buffer pause.
        this.power = generated <= this.powerCap - this.power ? this.power + generated : this.powerCap;
        this.setChanged();
    }

    private void updateAudio() {
        if(this.wasOn) {
            if(this.audio == null) {
                this.audio = this.createAudioLoop();
                if(this.audio != null) this.audio.startSound();
            } else if(!this.audio.isPlaying()) {
                this.audio = this.rebootAudio(this.audio);
            }
            if(this.audio != null) {
                this.audio.keepAlive();
                this.audio.updateVolume(this.getVolume(1F));
            }
        } else {
            this.stopAudio();
        }
    }

    @Override
    public AudioWrapper createAudioLoop() {
        if(this.level == null || !this.level.isClientSide) return null;
        return AudioWrapper.getLoopedSound(NtmSoundEvents.ENGINE_LOOP.get(), SoundSource.BLOCKS, this, 1.0F, 10F, 1.0F, 10);
    }

    private void stopAudio() {
        if(this.audio != null) {
            this.audio.stopSound();
            this.audio = null;
        }
    }

    private void removeFluidSubscriptions() {
        // A joined network can copy subscriptions away from the neighbouring node's former network.
        // Remove only this machine from a snapshot, including those stale memberships after retyping.
        for(NodeNet net : new ArrayList<>(UniNodespace.activeNodeNets)) {
            if(net instanceof FluidNetMK2 fluidNet) fluidNet.removeReceiver(this);
        }
    }

    private void removeNetworkSubscriptions() {
        if(this.level == null || this.level.isClientSide) return;
        this.removeFluidSubscriptions();
        for(NodeNet net : new ArrayList<>(UniNodespace.activeNodeNets)) {
            if(net instanceof PowerNetMK2 powerNet) powerNet.removeProvider(this);
        }
        this.subscribedType = null;
    }

    @Override
    public void onChunkUnloaded() {
        this.removeNetworkSubscriptions();
        this.stopAudio();
        super.onChunkUnloaded();
    }

    @Override
    public void setRemoved() {
        this.removeNetworkSubscriptions();
        this.stopAudio();
        super.setRemoved();
    }

    @Override public long getPower() { return this.power; }
    @Override public long getMaxPower() { return this.powerCap; }
    @Override public void setPower(long power) {
        long bounded = Math.max(0L, Math.min(this.powerCap, power));
        if(this.power != bounded) {
            this.power = bounded;
            this.setChanged();
        }
    }
    @Override public FluidTank[] getAllTanks() { return new FluidTank[] { this.tank }; }
    @Override public FluidTank[] getReceivingTanks() { return new FluidTank[] { this.tank }; }
    @Override public FluidTank getTankToPaste() { return this.tank; }

    @Override
    public void pasteSettings(CompoundTag tag, int index, Level level, Player player, BlockPos pos) {
        if(this.level == null || this.level.isClientSide || level != this.level || player.level() != this.level
                || !this.worldPosition.equals(pos) || !this.stillValid(player) || index < 0) return;
        FluidType previousType = this.tank.getTankType();
        IFluidCopiable.super.pasteSettings(tag, index, level, player, pos);
        if(this.tank.getTankType() != previousType) {
            this.removeFluidSubscriptions();
            this.subscribedType = null;
            this.setChanged();
        }
    }

    @Override
    public long transferFluid(FluidType type, int pressure, long amount) {
        long remainder = IFluidStandardReceiverMK2.super.transferFluid(type, pressure, amount);
        // Pipes also fill an idle machine between its ticks, which must be persisted immediately.
        if(remainder < amount) this.setChanged();
        return remainder;
    }

    @Override
    public boolean canPlaceItem(int slot, ItemStack stack) {
        return switch(slot) {
            case SLOT_FLUID_IN -> FluidContainerRegistry.getFluidContent(stack, this.tank.getTankType()) > 0;
            case SLOT_BATTERY -> stack.getItem() instanceof IBatteryItem;
            case SLOT_IDENTIFIER -> stack.getItem() instanceof IItemFluidIdentifier;
            default -> false;
        };
    }

    @Override
    public int[] getSlotsForFace(Direction direction) {
        return direction == Direction.DOWN ? SLOTS_BOTTOM : direction == Direction.UP ? SLOTS_TOP : SLOTS_SIDE;
    }

    @Override
    public boolean canTakeItemThroughFace(int index, ItemStack stack, Direction direction) {
        if(index == SLOT_FLUID_OUT) return stack.is(NtmItems.CANISTER_EMPTY.get()) || stack.is(NtmItems.TANK_STEEL.get());
        if(index == SLOT_BATTERY && stack.getItem() instanceof IBatteryItem battery) {
            return battery.getCharge(stack) == battery.getMaxCharge(stack);
        }
        return false;
    }

    @Override
    public boolean hasPermission(Player player) {
        return this.level != null && !this.level.isClientSide && player.level() == this.level
                && player.containerMenu instanceof MachineDieselMenu menu && menu.be == this
                && this.stillValid(player);
    }

    @Override
    public void receiveControl(Player player, CompoundTag tag) {
        if(!this.hasPermission(player) || tag == null || tag.getAllKeys().size() != 1
                || !tag.contains("turnOn", Tag.TAG_BYTE) || !tag.getBoolean("turnOn")) return;
        this.isOn = !this.isOn;
        this.setChanged();
    }

    @Override
    public void receiveControl(CompoundTag tag) {
        // CompoundTagControl calls both overloads; only its player-context call can authorize a toggle.
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.isOn = tag.getBoolean("isOn");
        this.powerCap = tag.contains("powerCap", Tag.TAG_LONG) && tag.getLong("powerCap") > 0 ? tag.getLong("powerCap") : MAX_POWER;
        this.power = Math.max(0L, Math.min(this.powerCap, tag.getLong("powerTime")));
        if(tag.contains("fuel_type")) this.tank.readFromNBT(tag, "fuel");
        this.wasOn = false;
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putBoolean("isOn", this.isOn);
        tag.putLong("powerTime", this.power);
        tag.putLong("powerCap", this.powerCap);
        this.tank.writeToNBT(tag, "fuel");
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeLong(this.power);
        buf.writeLong(this.powerCap);
        buf.writeBoolean(this.isOn);
        buf.writeBoolean(this.wasOn);
        this.tank.serialize(buf);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.power = buf.readLong();
        this.powerCap = buf.readLong();
        this.isOn = buf.readBoolean();
        this.wasOn = buf.readBoolean();
        this.tank.deserialize(buf);
    }

    @Override
    public AbstractContainerMenu createMenu(int id, Inventory inventory, Player player) {
        return new MachineDieselMenu(id, inventory, this);
    }
}