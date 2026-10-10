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
import com.hbm.inventory.menus.MachineCombustionEngineMenu;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.PistonSetItem;
import com.hbm.blocks.DummyableBlock;
import net.minecraft.util.Mth;
import net.minecraft.world.phys.AABB;
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

/** Standard combustion engine; legacy pollution and optional integrations are outside this port. */
public class MachineCombustionEngineBlockEntity extends MachineBaseBlockEntity implements IEnergyProviderMK2, IFluidStandardReceiverMK2, IControlReceiver, IFluidCopiable {

    public static final long MAX_POWER = 2_500_000L;
    public static final int TANK_CAPACITY = 24_000;
    public static final int SLOT_FLUID_IN = 0;
    public static final int SLOT_FLUID_OUT = 1;
    public static final int MAX_SETTING = 30;
    public static final int SLOT_PISTON = 2;
    public static final int SLOT_BATTERY = 3;
    public static final int SLOT_IDENTIFIER = 4;
    private static final int[] AUTOMATION_SLOTS = {};

    public long power;
    public int setting;
    public int tenth;
    public float doorAngle;
    public float prevDoorAngle;
    private int playersUsing;
    public boolean isOn;
    public boolean wasOn;
    public final FluidTank tank = new FluidTank(Fluids.DIESEL, TANK_CAPACITY);
    private AudioWrapper audio;
    private FluidType subscribedType;

    public MachineCombustionEngineBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.MACHINE_COMBUSTION_ENGINE.get(), pos, state, 5);
    }

    @Override
    protected Component getDefaultName() {
        return Component.translatable("container.machine_combustion_engine");
    }

    public double getEfficiency() {
        PistonSetItem.Type piston = PistonSetItem.getType(this.slots.get(SLOT_PISTON));
        FT_Combustible fuel = this.tank.getTankType().getTrait(FT_Combustible.class);
        return piston == null || fuel == null ? 0D : piston.getEfficiency(fuel.getGrade());
    }
    public long getPowerScaled(long pixels) { return this.power * pixels / MAX_POWER; }
    public int getPlayersUsing() { return this.playersUsing; }
    public static DirPos[] getPortProxies(BlockPos core, Direction facing) {
        Direction side = facing.getCounterClockWise();
        return new DirPos[] { new DirPos(core.relative(side), facing), new DirPos(core.relative(side.getOpposite()), facing),
                new DirPos(core.relative(facing.getOpposite()).relative(side), facing.getOpposite()),
                new DirPos(core.relative(facing.getOpposite()).relative(side.getOpposite()), facing.getOpposite()) };
    }
    public DirPos[] getConPos() {
        DirPos[] proxies = getPortProxies(this.worldPosition, this.getBlockState().getValue(DummyableBlock.FACING));
        DirPos[] connections = new DirPos[proxies.length];
        for(int i = 0; i < proxies.length; i++) connections[i] = new DirPos(proxies[i].makeCompat().relative(proxies[i].getDir()), proxies[i].getDir());
        return connections;
    }
    @Override public void updateEntity() {
        if(this.level == null) return;
        if(this.level.isClientSide) {
            this.prevDoorAngle = this.doorAngle;
            float swing = this.doorAngle / 10F + 3F;
            this.doorAngle = Mth.clamp(this.doorAngle + (this.playersUsing > 0 ? swing : -swing), 0F, 135F);
            this.updateAudio();
            return;
        }
        long previousPower = this.power;
        int previousFill = this.tank.getFill();
        int previousTenth = this.tenth;
        FluidType previousType = this.tank.getTankType();
        if(this.subscribedType != null && this.subscribedType != previousType) this.removeFluidSubscriptions();
        for(DirPos pos : this.getConPos()) {
            this.trySubscribe(previousType, this.level, pos);
            this.tryProvide(this.level, pos.makeCompat(), pos.getDir());
        }
        this.subscribedType = previousType;
        boolean changed = this.tank.loadTank(this.level, SLOT_FLUID_IN, SLOT_FLUID_OUT, this.slots);
        if(this.tank.setType(SLOT_IDENTIFIER, this.slots)) {
            this.tenth = 0;
            this.removeFluidSubscriptions();
            this.subscribedType = null;
            changed = true;
        }
        this.wasOn = false;
        this.generate();
        // Keep the complete generated buffer available to charging before the final overflow discard.
        this.power = Library.chargeItemsFromTE(this.slots, SLOT_BATTERY, this.power, this.power);
        this.power = Math.min(this.power, MAX_POWER);
        if(changed || this.power != previousPower || this.tank.getFill() != previousFill || this.tenth != previousTenth
                || this.tank.getTankType() != previousType) this.setChanged();
        this.networkPackNT(50);
    }
    public void generate() {
        this.wasOn = false;
        if(this.level == null || this.level.isClientSide || !this.isOn || this.setting <= 0 || this.setting > MAX_SETTING) return;
        FT_Combustible fuel = this.tank.getTankType().getTrait(FT_Combustible.class);
        double efficiency = this.getEfficiency();
        int fill = this.tank.getFill() * 10 + this.tenth;
        if(fuel == null || efficiency <= 0D || fill <= 0) return;
        int toBurn = Math.min(fill, this.setting * 2);
        // Original compound assignment converts the entire long-plus-double sum back to long.
        this.power += toBurn * (fuel.getCombustionEnergy() / 10_000D) * efficiency;
        fill -= toBurn;
        this.tank.setFill(fill / 10);
        this.tenth = fill % 10;
        this.wasOn = toBurn > 0;
        this.setChanged();
    }
    @Override public void startOpen(Player player) {
        if(this.level != null && !this.level.isClientSide) this.playersUsing++;
    }
    @Override public void stopOpen(Player player) {
        if(this.level != null && !this.level.isClientSide) this.playersUsing = Math.max(0, this.playersUsing - 1);
    }
    public AABB getRenderBoundingBox() { return new AABB(this.worldPosition).inflate(4D); }

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
        return AudioWrapper.getLoopedSound(NtmSoundEvents.IGENERATOR_OPERATE.get(), SoundSource.BLOCKS, this, 1.0F, 10F, 1.0F, 20);
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

    @Override public boolean canConnect(Direction dir) { return dir != Direction.DOWN; }
    @Override public boolean canConnect(FluidType type, Direction dir) { return dir != Direction.DOWN; }

    @Override public long getPower() { return this.power; }
    @Override public long getMaxPower() { return MAX_POWER; }
    @Override public void setPower(long power) {
        long bounded = Math.max(0L, Math.min(MAX_POWER, power));
        if(this.power != bounded) {
            this.power = bounded;
            this.setChanged();
        }
    }
    @Override public FluidTank[] getAllTanks() { return new FluidTank[] { this.tank }; }
    @Override public FluidTank[] getReceivingTanks() { return new FluidTank[] { this.tank }; }
    @Override public FluidTank getTankToPaste() { return this.tank; }

    @Override public CompoundTag getSettings(Level level, BlockPos pos) {
        CompoundTag tag = IFluidCopiable.super.getSettings(level, pos);
        tag.putBoolean("isOn", this.isOn);
        tag.putInt("burnRate", this.setting);
        return tag;
    }
    @Override public void pasteSettings(CompoundTag tag, int index, Level level, Player player, BlockPos pos) {
        // No clipboard bypass: copying is limited to the same current-menu context as controls.
        if(!this.hasPermission(player) || level != this.level || !this.worldPosition.equals(pos) || tag == null || index < 0) return;
        int[] ids = tag.getIntArray("FluidID");
        if(index >= ids.length || !tag.contains("FluidID", Tag.TAG_INT_ARRAY)
                || (tag.contains("isOn") && !tag.contains("isOn", Tag.TAG_BYTE))
                || (tag.contains("burnRate") && (!tag.contains("burnRate", Tag.TAG_INT)
                    || tag.getInt("burnRate") < 0 || tag.getInt("burnRate") > MAX_SETTING))) return;
        FluidType type = Fluids.fromID(ids[index]);
        if(type == null || type.getID() != ids[index]) return;
        if(type != this.tank.getTankType()) {
            this.tank.setTankType(type);
            this.tenth = 0;
            this.removeFluidSubscriptions();
            this.subscribedType = null;
        }
        if(tag.contains("isOn", Tag.TAG_BYTE)) this.isOn = tag.getBoolean("isOn");
        if(tag.contains("burnRate", Tag.TAG_INT)) this.setting = tag.getInt("burnRate");
        this.setChanged();
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
            case SLOT_PISTON -> PistonSetItem.getType(stack) != null;
            case SLOT_BATTERY -> stack.getItem() instanceof IBatteryItem;
            case SLOT_IDENTIFIER -> stack.getItem() instanceof IItemFluidIdentifier;
            default -> false;
        };
    }

    // The original engine inherits an empty sided-slot list; manual and Shift insertion are menu-only.
    @Override public int[] getSlotsForFace(Direction direction) { return AUTOMATION_SLOTS; }
    @Override public boolean canPlaceItemThroughFace(int index, ItemStack stack, Direction direction) { return false; }
    @Override public boolean canTakeItemThroughFace(int index, ItemStack stack, Direction direction) { return false; }

    @Override
    public boolean hasPermission(Player player) {
        return player != null && this.level != null && !this.level.isClientSide && player.level() == this.level
                && player.containerMenu instanceof MachineCombustionEngineMenu menu && menu.be == this
                && this.stillValid(player);
    }

    @Override public void receiveControl(Player player, CompoundTag tag) {
        if(!this.hasPermission(player) || tag == null || tag.getAllKeys().size() != 1) return;
        if(tag.contains("turnOn", Tag.TAG_BYTE) && tag.getBoolean("turnOn")) this.isOn = !this.isOn;
        else if(tag.contains("setting", Tag.TAG_INT) && tag.getInt("setting") >= 0 && tag.getInt("setting") <= MAX_SETTING) this.setting = tag.getInt("setting");
        else return;
        this.setChanged();
    }

    @Override
    public void receiveControl(CompoundTag tag) {
        // CompoundTagControl calls both overloads; only its player-context call can authorize a toggle.
    }

    @Override protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.isOn = tag.getBoolean("isOn");
        this.setting = Mth.clamp(tag.getInt("setting"), 0, MAX_SETTING);
        this.tenth = Mth.clamp(tag.getInt("tenth"), 0, 9);
        this.power = Math.max(0L, Math.min(MAX_POWER, tag.getLong("power")));
        if(tag.contains("tank_type")) {
            CompoundTag bounded = tag.copy();
            bounded.putInt("tank_max", TANK_CAPACITY);
            bounded.putShort("tank_p", (short)0);
            this.tank.readFromNBT(bounded, "tank");
        }
        this.wasOn = false;
    }
    @Override protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putBoolean("isOn", this.isOn);
        tag.putInt("setting", this.setting);
        tag.putInt("tenth", this.tenth);
        tag.putLong("power", this.power);
        this.tank.writeToNBT(tag, "tank");
    }
    @Override public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeInt(this.playersUsing);
        buf.writeInt(this.setting);
        buf.writeInt(this.tenth);
        buf.writeLong(this.power);
        buf.writeBoolean(this.isOn);
        buf.writeBoolean(this.wasOn);
        this.tank.serialize(buf);
    }
    @Override public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.playersUsing = buf.readInt();
        this.setting = buf.readInt();
        this.tenth = buf.readInt();
        this.power = buf.readLong();
        this.isOn = buf.readBoolean();
        this.wasOn = buf.readBoolean();
        this.tank.deserialize(buf);
    }

    @Override
    public AbstractContainerMenu createMenu(int id, Inventory inventory, Player player) {
        return new MachineCombustionEngineMenu(id, inventory, this);
    }
}