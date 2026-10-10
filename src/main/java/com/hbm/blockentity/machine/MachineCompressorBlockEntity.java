package com.hbm.blockentity.machine;

import api.hbm.energymk2.IBatteryItem;
import api.hbm.energymk2.IEnergyReceiverMK2;
import api.hbm.energymk2.PowerNetMK2;
import api.hbm.fluidmk2.FluidNetMK2;
import api.hbm.fluidmk2.IFluidStandardTransceiverMK2;
import com.hbm.blockentity.IFluidCopiable;
import com.hbm.blockentity.IUpgradeInfoProvider;
import com.hbm.blockentity.MachineBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.interfaces.IControlReceiver;
import com.hbm.inventory.UpgradeManagerNT;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.menus.MachineCompressorMenu;
import com.hbm.inventory.recipes.CompressorRecipes;
import com.hbm.inventory.recipes.CompressorRecipes.CompressorRecipe;
import com.hbm.items.machine.IItemFluidIdentifier;
import com.hbm.items.machine.MachineUpgradeItem;
import com.hbm.items.machine.MachineUpgradeItem.UpgradeType;
import com.hbm.lib.Library;
import com.hbm.registry.NtmSoundEvents;
import com.hbm.uninos.NodeNet;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;

public class MachineCompressorBlockEntity extends MachineBaseBlockEntity implements IEnergyReceiverMK2, IFluidStandardTransceiverMK2, IUpgradeInfoProvider, IControlReceiver, IFluidCopiable {

    public static final long MAX_POWER = 100_000;
    public static final int TANK_CAPACITY = 16_000;
    public static final int POWER_REQUIREMENT_BASE = 2_500;
    public static final int PROCESS_TIME_BASE = 100;
    public static final int SLOT_IDENTIFIER = 0;
    public static final int SLOT_BATTERY = 1;
    public static final int SLOT_UPGRADE_FIRST = 2;
    public static final int SLOT_UPGRADE_LAST = 3;
    private static final int[] AUTOMATION_SLOTS = { SLOT_BATTERY };

    public final FluidTank[] tanks = { new FluidTank(Fluids.NONE, TANK_CAPACITY), new FluidTank(Fluids.NONE, TANK_CAPACITY).withPressure(1) };
    public final UpgradeManagerNT upgradeManager = new UpgradeManagerNT(this);
    public long power;
    public int progress;
    public int processTime = PROCESS_TIME_BASE;
    public int powerRequirement = POWER_REQUIREMENT_BASE;
    public boolean isOn;
    public float fanSpin;
    public float prevFanSpin;
    public float piston;
    public float prevPiston;
    public boolean pistonDir;
    private float randSpeed = 0.1F;
    private FluidType subscribedType;

    public MachineCompressorBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.MACHINE_COMPRESSOR.get(), pos, state, 4);
    }

    @Override protected Component getDefaultName() { return Component.translatable("container.machine_compressor"); }

    public static DirPos[] getPortProxies(BlockPos core, Direction facing) {
        Direction side = facing.getClockWise();
        return new DirPos[] { new DirPos(core.relative(side), side), new DirPos(core.relative(side.getOpposite()), side.getOpposite()),
                new DirPos(core.relative(facing.getOpposite()), facing.getOpposite()) };
    }

    public DirPos[] getConPos() {
        DirPos[] proxies = getPortProxies(this.worldPosition, this.getBlockState().getValue(DummyableBlock.FACING));
        DirPos[] connections = new DirPos[proxies.length];
        for(int i = 0; i < proxies.length; i++) connections[i] = new DirPos(proxies[i].makeCompat().relative(proxies[i].getDir()), proxies[i].getDir());
        return connections;
    }

    @Override
    public void updateEntity() {
        if(this.level == null) return;
        if(this.level.isClientSide) {
            this.updateAnimation();
            return;
        }
        long previousPower = this.power;
        int previousProgress = this.progress;
        boolean previousOn = this.isOn;
        FluidType previousType = this.tanks[0].getTankType();
        int previousInput = this.tanks[0].getFill();
        int previousOutput = this.tanks[1].getFill();
        FluidType previousOutputType = this.tanks[1].getTankType();
        int previousOutputPressure = this.tanks[1].getPressure();

        if(this.subscribedType != null && this.subscribedType != previousType) this.removeFluidSubscriptions();
        // Preserve the original port, battery, identifier, output setup and upgrade order using NEO's old network model.
        for(DirPos pos : this.getConPos()) {
            this.trySubscribe(this.level, pos);
            if(previousType != Fluids.NONE) this.trySubscribe(previousType, this.level, pos);
            if(this.tanks[1].getFill() > 0) this.tryProvide(this.tanks[1], this.level, pos);
        }
        this.subscribedType = previousType;
        ItemStack previousBattery = this.slots.get(SLOT_BATTERY).copy();
        this.power = Library.chargeTEFromItems(this.slots, SLOT_BATTERY, this.power, MAX_POWER);
        boolean changed = !ItemStack.matches(previousBattery, this.slots.get(SLOT_BATTERY));
        changed |= this.tanks[0].setType(SLOT_IDENTIFIER, this.slots);
        this.setupTanks();
        this.recalculateUpgrades();
        if(this.canProcess()) {
            this.progress++;
            this.isOn = true;
            this.power -= this.powerRequirement;
            if(this.progress >= this.processTime) {
                this.progress = 0;
                this.process();
            }
        } else {
            this.progress = 0;
            this.isOn = false;
        }
        if(this.tanks[0].getTankType() != previousType || this.tanks[1].getTankType() != previousOutputType) {
            this.removeFluidSubscriptions();
            this.subscribedType = null;
        }
        if(changed || this.power != previousPower || this.progress != previousProgress || this.isOn != previousOn
                || this.tanks[0].getFill() != previousInput || this.tanks[1].getFill() != previousOutput
                || this.tanks[1].getTankType() != previousOutputType || this.tanks[1].getPressure() != previousOutputPressure) this.setChanged();
        this.networkPackNT(100);
    }

    public CompressorRecipe getRecipe() { return CompressorRecipes.getRecipe(this.tanks[0].getTankType(), this.tanks[0].getPressure()); }

    public void recalculateUpgrades() {
        this.upgradeManager.checkSlots(this.slots, SLOT_UPGRADE_FIRST, SLOT_UPGRADE_LAST);
        int speed = this.upgradeManager.getLevel(UpgradeType.SPEED);
        int economy = this.upgradeManager.getLevel(UpgradeType.POWER);
        int overdrive = this.upgradeManager.getLevel(UpgradeType.OVERDRIVE);
        CompressorRecipe recipe = this.getRecipe();
        // Generic compression uses the original discrete speed delays; special recipes divide their own duration.
        int time = recipe == null ? speed == 3 ? 10 : speed == 2 ? 20 : speed == 1 ? 60 : PROCESS_TIME_BASE : recipe.duration() / (speed + 1);
        this.processTime = Math.max(1, time / (overdrive + 1));
        // Keep truncation before multiplication, rather than algebraically combining these operations.
        this.powerRequirement = (POWER_REQUIREMENT_BASE / (economy + 1)) * (overdrive * 2 + 1);
    }

    public void setupTanks() {
        CompressorRecipe recipe = this.getRecipe();
        this.tanks[1].withPressure(recipe == null ? this.tanks[0].getPressure() + 1 : recipe.outputPressure());
        this.tanks[1].setTankType(recipe == null ? this.tanks[0].getTankType() : recipe.outputType());
    }

    public boolean canProcess() {
        if(this.power <= this.powerRequirement || this.tanks[0].getTankType() == Fluids.NONE) return false;
        CompressorRecipe recipe = this.getRecipe();
        int input = recipe == null ? 1_000 : recipe.inputAmount();
        int output = recipe == null ? 1_000 : recipe.outputAmount();
        return this.tanks[0].getFill() >= input && output <= this.tanks[1].getMaxFill() - this.tanks[1].getFill();
    }

    public void process() {
        CompressorRecipe recipe = this.getRecipe();
        this.tanks[0].setFill(this.tanks[0].getFill() - (recipe == null ? 1_000 : recipe.inputAmount()));
        this.tanks[1].setFill(this.tanks[1].getFill() + (recipe == null ? 1_000 : recipe.outputAmount()));
        this.setChanged();
    }

    private void updateAnimation() {
        this.prevFanSpin = this.fanSpin;
        this.prevPiston = this.piston;
        if(!this.isOn) return;
        this.fanSpin += 15F;
        if(this.fanSpin >= 360F) {
            this.prevFanSpin -= 360F;
            this.fanSpin -= 360F;
        }
        if(this.pistonDir) {
            this.piston -= this.randSpeed;
            if(this.piston <= 0F) {
                this.level.playLocalSound(this.worldPosition.getX(), this.worldPosition.getY(), this.worldPosition.getZ(),
                        NtmSoundEvents.COMPRESSOR_STROKE.get(), SoundSource.BLOCKS, this.getVolume(0.5F), 0.75F, false);
                this.pistonDir = false;
            }
        } else {
            this.piston += 0.05F;
            if(this.piston >= 1F) {
                this.randSpeed = 0.085F + this.level.random.nextFloat() * 0.03F;
                this.pistonDir = true;
            }
        }
        this.piston = Mth.clamp(this.piston, 0F, 1F);
    }

    private void removeFluidSubscriptions() {
        for(NodeNet net : new ArrayList<>(UniNodespace.activeNodeNets)) {
            if(net instanceof FluidNetMK2 fluidNet) {
                fluidNet.removeReceiver(this);
                fluidNet.removeProvider(this);
            }
        }
    }

    private void removeNetworkSubscriptions() {
        if(this.level == null || this.level.isClientSide) return;
        this.removeFluidSubscriptions();
        for(NodeNet net : new ArrayList<>(UniNodespace.activeNodeNets)) if(net instanceof PowerNetMK2 powerNet) powerNet.removeReceiver(this);
        this.subscribedType = null;
    }

    @Override public void onChunkUnloaded() { this.removeNetworkSubscriptions(); super.onChunkUnloaded(); }
    @Override public void setRemoved() { this.removeNetworkSubscriptions(); super.setRemoved(); }
    @Override public long getPower() { return this.power; }
    @Override public long getMaxPower() { return MAX_POWER; }
    @Override public void setPower(long power) {
        long bounded = Math.max(0, Math.min(MAX_POWER, power));
        if(this.power != bounded) { this.power = bounded; this.setChanged(); }
    }
    @Override public FluidTank[] getAllTanks() { return this.tanks; }
    @Override public FluidTank[] getReceivingTanks() { return new FluidTank[] { this.tanks[0] }; }
    @Override public FluidTank[] getSendingTanks() { return new FluidTank[] { this.tanks[1] }; }
    @Override public long transferFluid(FluidType type, int pressure, long amount) {
        long remainder = IFluidStandardTransceiverMK2.super.transferFluid(type, pressure, amount);
        if(remainder < amount) this.setChanged();
        return remainder;
    }
    @Override public void useUpFluid(FluidType type, int pressure, long amount) {
        long previous = this.getFluidAvailable(type, pressure);
        IFluidStandardTransceiverMK2.super.useUpFluid(type, pressure, amount);
        if(this.getFluidAvailable(type, pressure) != previous) this.setChanged();
    }

    @Override public boolean canPlaceItem(int slot, ItemStack stack) {
        if(stack.isEmpty()) return false;
        return switch(slot) {
            case SLOT_IDENTIFIER -> stack.getItem() instanceof IItemFluidIdentifier;
            case SLOT_BATTERY -> stack.getItem() instanceof IBatteryItem battery && battery.getDischargeRate(stack) > 0;
            case SLOT_UPGRADE_FIRST, SLOT_UPGRADE_LAST -> stack.getItem() instanceof MachineUpgradeItem upgrade
                    && upgrade.tier > 0 && this.getValidUpgrades().containsKey(upgrade.type);
            default -> false;
        };
    }
    // Target adaptation: only the battery is automated; settings and upgrades are menu operations.
    @Override public int[] getSlotsForFace(Direction direction) { return AUTOMATION_SLOTS; }
    @Override public boolean canPlaceItemThroughFace(int slot, ItemStack stack, Direction direction) {
        return slot == SLOT_BATTERY && this.canPlaceItem(slot, stack) && stack.getItem() instanceof IBatteryItem battery
                && battery.getMaxCharge(stack) > 0 && battery.getChargeRate(stack) > 0;
    }
    @Override public boolean canTakeItemThroughFace(int slot, ItemStack stack, Direction direction) {
        return slot == SLOT_BATTERY && stack.getItem() instanceof IBatteryItem battery && battery.getCharge(stack) == 0;
    }

    @Override public boolean hasPermission(Player player) {
        return this.level != null && !this.level.isClientSide && player.level() == this.level
                && player.containerMenu instanceof MachineCompressorMenu menu && menu.be == this && this.stillValid(player);
    }
    @Override public void receiveControl(Player player, CompoundTag tag) {
        if(!this.hasPermission(player) || tag == null || tag.getAllKeys().size() != 1 || !tag.contains("compression", Tag.TAG_INT)) return;
        this.setInputPressure(tag.getInt("compression"));
    }
    @Override public void receiveControl(CompoundTag tag) {
        // CompoundTagControl calls both overloads. Only the player-context overload authorizes the operation.
    }
    public boolean setInputPressure(int pressure) {
        if(this.level == null || this.level.isClientSide || pressure < 0 || pressure > 4 || pressure == this.tanks[0].getPressure()) return false;
        this.removeFluidSubscriptions();
        this.subscribedType = null;
        this.tanks[0].withPressure(pressure);
        this.setupTanks();
        this.progress = 0;
        this.isOn = false;
        this.setChanged();
        return true;
    }
    @Override public FluidTank getTankToPaste() { return this.tanks[0]; }
    @Override public CompoundTag getSettings(Level level, BlockPos pos) {
        CompoundTag tag = IFluidCopiable.super.getSettings(level, pos);
        tag.putInt("compression", this.tanks[0].getPressure());
        return tag;
    }
    @Override public void pasteSettings(CompoundTag tag, int index, Level level, Player player, BlockPos pos) {
        if(tag == null || level != this.level || !this.worldPosition.equals(pos) || !this.hasPermission(player)
                || !tag.contains("compression", Tag.TAG_INT) || !tag.contains("FluidID", Tag.TAG_INT_ARRAY)) return;
        int pressure = tag.getInt("compression");
        int[] ids = tag.getIntArray("FluidID");
        if(pressure < 0 || pressure > 4 || index < 0 || index >= ids.length) return;
        FluidType type = Fluids.fromID(ids[index]);
        if(type == Fluids.NONE && ids[index] != Fluids.NONE.getID()) return;
        if(type != this.tanks[0].getTankType() || pressure != this.tanks[0].getPressure()) {
            this.removeFluidSubscriptions();
            this.subscribedType = null;
            this.tanks[0].setTankType(type);
            this.tanks[0].withPressure(pressure);
            this.setupTanks();
            this.progress = 0;
            this.isOn = false;
            this.setChanged();
        }
    }

    @Override public HashMap<UpgradeType, Integer> getValidUpgrades() {
        HashMap<UpgradeType, Integer> upgrades = new HashMap<>();
        upgrades.put(UpgradeType.SPEED, 3);
        upgrades.put(UpgradeType.POWER, 3);
        upgrades.put(UpgradeType.OVERDRIVE, 9);
        return upgrades;
    }
    @Override public boolean canProvideInfo(UpgradeType type, int level, TooltipFlag flag) { return this.getValidUpgrades().containsKey(type); }
    @Override public void provideInfo(UpgradeType type, int level, List<Component> info, TooltipFlag flag) {
        info.add(IUpgradeInfoProvider.getStandardLabel(NtmBlocks.MACHINE_COMPRESSOR.get()));
        if(type == UpgradeType.SPEED) {
            int reduction = level == 3 ? 90 : level == 2 ? 80 : level == 1 ? 40 : 0;
            info.add(Component.translatable("machine_compressor.upgrade.generic", Component.translatable(KEY_DELAY, "-" + reduction + "%")).withStyle(ChatFormatting.GREEN));
            info.add(Component.translatable("machine_compressor.upgrade.recipe", Component.translatable(KEY_DELAY, "-" + (100 - 100 / (level + 1)) + "%")).withStyle(ChatFormatting.GREEN));
        }
        if(type == UpgradeType.POWER) info.add(Component.translatable(KEY_CONSUMPTION, "-" + (100 - 100 / (level + 1)) + "%").withStyle(ChatFormatting.GREEN));
        if(type == UpgradeType.OVERDRIVE) info.add(Component.translatable(KEY_YES).withStyle(ChatFormatting.RED));
    }

    @Override protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.power = Math.max(0, Math.min(MAX_POWER, tag.getLong("power")));
        this.progress = Math.max(0, tag.getInt("progress"));
        this.tanks[0].readFromNBT(tag, "0");
        this.tanks[1].readFromNBT(tag, "1");
        // This machine has fixed-size tanks even if older or edited NBT contains another capacity.
        for(FluidTank tank : this.tanks) {
            tank.changeTankSize(TANK_CAPACITY);
            tank.setFill(Math.max(0, tank.getFill()));
        }
        if(this.tanks[0].getPressure() < 0 || this.tanks[0].getPressure() > 4) {
            this.tanks[0].withPressure(0);
            this.progress = 0;
        }
        this.isOn = false;
    }
    @Override protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putLong("power", this.power);
        tag.putInt("progress", this.progress);
        this.tanks[0].writeToNBT(tag, "0");
        this.tanks[1].writeToNBT(tag, "1");
    }
    @Override public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeInt(this.progress);
        buf.writeInt(this.processTime);
        buf.writeInt(this.powerRequirement);
        buf.writeLong(this.power);
        this.tanks[0].serialize(buf);
        this.tanks[1].serialize(buf);
        buf.writeBoolean(this.isOn);
    }
    @Override public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.progress = buf.readInt();
        this.processTime = buf.readInt();
        this.powerRequirement = buf.readInt();
        this.power = buf.readLong();
        this.tanks[0].deserialize(buf);
        this.tanks[1].deserialize(buf);
        this.isOn = buf.readBoolean();
    }
    public AABB getRenderBoundingBox() { return new AABB(this.worldPosition.getX() - 2, this.worldPosition.getY(), this.worldPosition.getZ() - 2,
            this.worldPosition.getX() + 3, this.worldPosition.getY() + 9, this.worldPosition.getZ() + 3); }
    @Override public AbstractContainerMenu createMenu(int id, Inventory inventory, Player player) { return new MachineCompressorMenu(id, inventory, this); }
}
