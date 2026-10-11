package com.hbm.blockentity.machine;

import api.hbm.energymk2.IBatteryItem;
import api.hbm.energymk2.IEnergyReceiverMK2;
import api.hbm.energymk2.PowerNetMK2;
import api.hbm.fluidmk2.FluidNetMK2;
import api.hbm.fluidmk2.IFillableItem;
import api.hbm.fluidmk2.IFluidStandardReceiverMK2;
import com.hbm.blockentity.IFluidCopiable;
import com.hbm.blockentity.IUpgradeInfoProvider;
import com.hbm.blockentity.MachineBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.extprop.HbmPlayerAttachments;
import com.hbm.handler.CrystallizerRecipeClientSync;
import com.hbm.inventory.FluidContainerRegistry;
import com.hbm.inventory.UpgradeManagerNT;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.menus.MachineCrystallizerMenu;
import com.hbm.inventory.recipes.CrystallizerRecipes;
import com.hbm.inventory.recipes.CrystallizerRecipes.CrystallizerRecipe;
import com.hbm.items.machine.IItemFluidIdentifier;
import com.hbm.items.machine.InfiniteFluidItem;
import com.hbm.items.machine.MachineUpgradeItem;
import com.hbm.items.machine.MachineUpgradeItem.UpgradeType;
import com.hbm.lib.Library;
import com.hbm.lib.ModAttachments;
import com.hbm.main.NuclearTechMod;
import com.hbm.registry.NtmSoundEvents;
import com.hbm.sound.AudioWrapper;
import com.hbm.uninos.NodeNet;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.BobMathUtil;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.sounds.SoundSource;
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

/**
 * Standard ore acidizer (machine_crystallizer). Original semantics kept on purpose: a sub-cycle increments progress and pays
 * the per-sub-cycle demand, completion needs {@code progress > duration} (so the default 600-tick recipe takes 601 effective
 * sub-cycles), any failed sub-cycle clears the progress, the whole acid amount is always consumed on completion while the
 * Effectiveness upgrade only gives a chance to keep the input, and progress is not written to NBT (it restarts after a reload).
 */
public class MachineCrystallizerBlockEntity extends MachineBaseBlockEntity implements IEnergyReceiverMK2, IFluidStandardReceiverMK2, IUpgradeInfoProvider, IFluidCopiable {

    public static final long MAX_POWER = 1_000_000L;
    public static final int DEMAND = 1_000;
    public static final int TANK_CAPACITY = 8_000;
    public static final int DEFAULT_DURATION = CrystallizerRecipes.DEFAULT_DURATION;
    public static final int MAX_CYCLES_PER_TICK = 7;
    public static final float MAX_FREE_CHANCE = 0.99F;

    public static final int SLOT_INPUT = 0;
    public static final int SLOT_BATTERY = 1;
    public static final int SLOT_OUTPUT = 2;
    public static final int SLOT_FLUID_IN = 3;
    public static final int SLOT_FLUID_OUT = 4;
    public static final int SLOT_UPGRADE_FIRST = 5;
    public static final int SLOT_UPGRADE_LAST = 6;
    public static final int SLOT_IDENTIFIER = 7;
    /** The original automation view: the input and the output; the output is the only extractable slot. */
    private static final int[] AUTOMATION_SLOTS = { SLOT_INPUT, SLOT_OUTPUT };

    public long power;
    public int progress;
    public int duration = DEFAULT_DURATION;
    public boolean isOn;
    public float angle;
    public float prevAngle;
    public final FluidTank tank = new FluidTank(Fluids.PEROXIDE, TANK_CAPACITY);
    public final UpgradeManagerNT upgradeManager = new UpgradeManagerNT(this);
    private FluidType subscribedType;
    private AudioWrapper audio;
    private AABB renderBox;

    public MachineCrystallizerBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.MACHINE_CRYSTALLIZER.get(), pos, state, 8);
    }

    @Override protected Component getDefaultName() { return Component.translatable("container.machine_crystallizer"); }
    @Override public AbstractContainerMenu createMenu(int id, Inventory inventory, Player player) { return new MachineCrystallizerMenu(id, inventory, this); }

    /** Forge 1.7.10's getRotation(UP) maps NORTH to EAST: the climbable side is the placement facing turned clockwise. */
    public static Direction getLadderSide(Direction facing) { return facing.getClockWise(); }

    /** The four bottom corners of the 3x3 footprint; each corner is a proxy that faces its two outward horizontal sides. */
    public static BlockPos[] getCornerProxies(BlockPos core) {
        return new BlockPos[] { core.offset(1, 0, 1), core.offset(1, 0, -1), core.offset(-1, 0, 1), core.offset(-1, 0, -1) };
    }

    /** The eight external neighbours of the corner proxies, each with the outward direction (the original refinery-shaped port set). */
    public static DirPos[] getConnectionPositions(BlockPos core) {
        return new DirPos[] {
                new DirPos(core.offset(2, 0, 1), Direction.EAST), new DirPos(core.offset(1, 0, 2), Direction.SOUTH),
                new DirPos(core.offset(2, 0, -1), Direction.EAST), new DirPos(core.offset(1, 0, -2), Direction.NORTH),
                new DirPos(core.offset(-2, 0, 1), Direction.WEST), new DirPos(core.offset(-1, 0, 2), Direction.SOUTH),
                new DirPos(core.offset(-2, 0, -1), Direction.WEST), new DirPos(core.offset(-1, 0, -2), Direction.NORTH) };
    }
    public DirPos[] getConPos() { return getConnectionPositions(this.worldPosition); }

    @Override public void updateEntity() {
        if(this.level == null) return;
        if(this.level.isClientSide) {
            this.updateClient();
            this.markClimbingPlayers();
            return;
        }
        long previousPower = this.power;
        FluidType previousType = this.tank.getTankType();
        int previousFill = this.tank.getFill();
        ItemStack previousBattery = this.slots.get(SLOT_BATTERY).copy();

        if(this.subscribedType != null && this.subscribedType != previousType) this.removeFluidSubscriptions();
        for(DirPos pos : this.getConPos()) {
            if(!this.level.hasChunkAt(pos.makeCompat())) continue;
            this.trySubscribe(this.level, pos);
            this.trySubscribe(previousType, this.level, pos);
        }
        this.subscribedType = previousType;

        this.isOn = false;
        this.power = Library.chargeTEFromItems(this.slots, SLOT_BATTERY, this.power, MAX_POWER);
        boolean changed = !ItemStack.matches(previousBattery, this.slots.get(SLOT_BATTERY));
        // Retyping precedes loading, as in the original: a new identifier can accept its matching container this tick.
        if(this.tank.setType(SLOT_IDENTIFIER, this.slots)) {
            this.removeFluidSubscriptions();
            changed = true;
        }
        changed |= this.tank.loadTank(this.level, SLOT_FLUID_IN, SLOT_FLUID_OUT, this.slots);
        this.upgradeManager.checkSlots(this.slots, SLOT_UPGRADE_FIRST, SLOT_UPGRADE_LAST);
        this.duration = this.getDuration();

        int cycles = this.getCycleCount();
        for(int i = 0; i < cycles; i++) {
            // Every attempt checks and pays independently; a later attempt in the same tick may fail and clear the progress.
            if(this.canProcess()) {
                this.progress++;
                this.power -= this.getPowerRequired();
                this.isOn = true;
                if(this.progress > this.duration) {
                    this.progress = 0;
                    this.processItem();
                    changed = true;
                }
            } else {
                this.progress = 0;
            }
        }
        this.power = Math.max(0L, Math.min(this.power, MAX_POWER));
        // Only persisted state marks the chunk dirty; progress, isOn and duration are not saved and reset on load.
        if(changed || this.power != previousPower || this.tank.getFill() != previousFill || this.tank.getTankType() != previousType) this.setChanged();
        this.markClimbingPlayers();
        this.networkPackNT(25);
    }

    private void updateClient() {
        this.prevAngle = this.angle;
        if(this.isOn) {
            this.angle += 5F * this.getCycleCount();
            if(this.angle >= 360F) { this.angle -= 360F; this.prevAngle -= 360F; }
            Player me = NuclearTechMod.proxy.me();
            BlockPos pos = this.worldPosition;
            if(me != null && this.level.random.nextInt(20) == 0 && me.distanceToSqr(pos.getX() + 0.5, pos.getY() + 6, pos.getZ() + 0.5) < 50 * 50) {
                this.level.addParticle(ParticleTypes.CLOUD, pos.getX() + this.level.random.nextDouble(), pos.getY() + 6.5D, pos.getZ() + this.level.random.nextDouble(), 0.0D, 0.1D, 0.0D);
            }
            if(me != null && me.distanceToSqr(pos.getX(), pos.getY(), pos.getZ()) < 25 * 25) {
                if(this.audio == null) { this.audio = this.createAudioLoop(); if(this.audio != null) this.audio.startSound(); }
                else if(!this.audio.isPlaying()) this.audio = this.rebootAudio(this.audio);
                if(this.audio != null) {
                    this.audio.keepAlive();
                    this.audio.updateVolume(this.getVolume(1F));
                    this.audio.updatePitch(0.75F);
                }
            } else this.stopAudio();
        } else this.stopAudio();
    }

    /** The original marks players in a thin column along the rotated side, on both logical sides, every tick; the shared handler consumes the flag. */
    public static AABB getLadderBox(BlockPos core, Direction facing) {
        Direction side = getLadderSide(facing);
        return new AABB(core.getX() + 0.25, core.getY() + 1, core.getZ() + 0.25, core.getX() + 0.75, core.getY() + 6, core.getZ() + 0.75)
                .move(side.getStepX() * 1.5, 0, side.getStepZ() * 1.5);
    }
    private void markClimbingPlayers() {
        if(this.level == null) return;
        Direction facing = this.getBlockState().getValue(DummyableBlock.FACING);
        for(Player player : this.level.getEntitiesOfClass(Player.class, getLadderBox(this.worldPosition, facing))) {
            HbmPlayerAttachments props = HbmPlayerAttachments.getData(player);
            props.isOnLadder = true;
            player.setData(ModAttachments.PLAYER_ATTACHMENT.get(), props);
        }
    }

    public CrystallizerRecipe getRecipe() { return CrystallizerRecipes.getOutput(this.slots.get(SLOT_INPUT), this.tank.getTankType()); }

    /** Original order: input, energy, recipe, input count, acid, output identity, output space. */
    public boolean canProcess() {
        ItemStack input = this.slots.get(SLOT_INPUT);
        if(input.isEmpty()) return false;
        if(this.power < this.getPowerRequired()) return false;
        CrystallizerRecipe recipe = this.getRecipe();
        if(recipe == null) return false;
        if(input.getCount() < recipe.itemAmount()) return false;
        if(this.tank.getFill() < recipe.acidAmount()) return false;
        ItemStack output = recipe.output();
        ItemStack current = this.slots.get(SLOT_OUTPUT);
        if(!current.isEmpty() && !ItemStack.isSameItemSameComponents(current, output)) return false;
        if(!current.isEmpty() && current.getCount() + output.getCount() > current.getMaxStackSize()) return false;
        return true;
    }

    /** Deliver the output, consume the whole acid amount, then roll whether the input is consumed. */
    public void processItem() {
        CrystallizerRecipe recipe = this.getRecipe();
        if(recipe == null) return;
        ItemStack output = recipe.output();
        ItemStack current = this.slots.get(SLOT_OUTPUT);
        if(current.isEmpty()) this.slots.set(SLOT_OUTPUT, output);
        else if(ItemStack.isSameItemSameComponents(current, output) && current.getCount() + output.getCount() <= current.getMaxStackSize()) current.grow(output.getCount());
        this.tank.setFill(this.tank.getFill() - recipe.acidAmount());
        if(shouldConsumeInput(this.getFreeChance(recipe), this.level.random.nextFloat())) this.removeItem(SLOT_INPUT, recipe.itemAmount());
        this.setChanged();
    }

    /** Original boundary: a zero chance always consumes; a roll exactly equal to a positive chance keeps the input. */
    public static boolean shouldConsumeInput(float freeChance, float roll) {
        return freeChance == 0F || freeChance < roll;
    }

    public float getFreeChance(CrystallizerRecipe recipe) {
        int effect = this.upgradeManager.getLevel(UpgradeType.EFFECT);
        if(effect > 0) return Math.min(effect * recipe.productivity, MAX_FREE_CHANCE);
        return 0F;
    }
    public static int getDuration(int base, int speed) {
        if(speed > 0) return (int) Math.ceil(base * Math.max(1F - 0.25F * speed, 0.25F));
        return base;
    }
    public int getDuration() {
        CrystallizerRecipe recipe = this.getRecipe();
        return getDuration(recipe != null ? recipe.duration : DEFAULT_DURATION, this.upgradeManager.getLevel(UpgradeType.SPEED));
    }
    public static long getPowerRequired(int speed, int effect) { return (long) DEMAND * (1L + speed + 2L * effect); }
    public long getPowerRequired() { return getPowerRequired(this.upgradeManager.getLevel(UpgradeType.SPEED), this.upgradeManager.getLevel(UpgradeType.EFFECT)); }
    public static int getCycleCount(int overdrive) { return Math.min(1 + overdrive * 2, MAX_CYCLES_PER_TICK); }
    public int getCycleCount() { return getCycleCount(this.upgradeManager.getLevel(UpgradeType.OVERDRIVE)); }

    public long getPowerScaled(long pixels) { return this.power * pixels / MAX_POWER; }
    public int getProgressScaled(int pixels) { return this.duration <= 0 ? 0 : (int) ((long) this.progress * pixels / this.duration); }

    @Override public AudioWrapper createAudioLoop() {
        return this.level != null && this.level.isClientSide ? AudioWrapper.getLoopedSound(NtmSoundEvents.CHEMICAL_PLANT_OPERATE.get(), SoundSource.BLOCKS, this, 1F, 15F, 0.75F, 15) : null;
    }
    private void stopAudio() { if(this.audio != null) { this.audio.stopSound(); this.audio = null; } }

    private void removeFluidSubscriptions() {
        if(this.level == null || this.level.isClientSide) return;
        for(NodeNet net : new ArrayList<>(UniNodespace.activeNodeNets)) if(net instanceof FluidNetMK2 fluidNet) fluidNet.removeReceiver(this);
        this.subscribedType = null;
    }
    private void removeNetworkSubscriptions() {
        if(this.level == null || this.level.isClientSide) return;
        this.removeFluidSubscriptions();
        for(NodeNet net : new ArrayList<>(UniNodespace.activeNodeNets)) if(net instanceof PowerNetMK2 powerNet) powerNet.removeReceiver(this);
    }
    @Override public void onChunkUnloaded() { this.removeNetworkSubscriptions(); this.stopAudio(); super.onChunkUnloaded(); }
    @Override public void setRemoved() { this.removeNetworkSubscriptions(); this.stopAudio(); super.setRemoved(); }

    /** The corner proxies only have horizontal outward faces; the core itself is enclosed by the structure. */
    @Override public boolean canConnect(Direction direction) { return direction.getAxis().isHorizontal(); }
    @Override public boolean canConnect(FluidType type, Direction direction) { return this.canConnect(direction); }
    @Override public long getPower() { return this.power; }
    @Override public long getMaxPower() { return MAX_POWER; }
    @Override public void setPower(long power) {
        long bounded = Math.max(0L, Math.min(MAX_POWER, power));
        if(this.power != bounded) { this.power = bounded; this.setChanged(); }
    }
    @Override public FluidTank[] getReceivingTanks() { return new FluidTank[] { this.tank }; }
    @Override public FluidTank[] getAllTanks() { return new FluidTank[] { this.tank }; }
    @Override public long transferFluid(FluidType type, int pressure, long amount) {
        long remainder = IFluidStandardReceiverMK2.super.transferFluid(type, pressure, amount);
        if(remainder < amount) this.setChanged();
        return remainder;
    }
    @Override public int[] getFluidIDToCopy() { return new int[] { this.tank.getTankType().getID() }; }
    @Override public FluidTank getTankToPaste() { return this.tank; }
    @Override public void pasteSettings(CompoundTag tag, int index, Level level, Player player, BlockPos pos) {
        if(tag == null || player == null || level != this.level || level.isClientSide || !this.worldPosition.equals(pos)
                || player.level() != level || !this.stillValid(player) || !tag.contains("FluidID", Tag.TAG_INT_ARRAY)) return;
        int[] ids = tag.getIntArray("FluidID");
        if(index < 0 || index >= ids.length) return;
        FluidType type = Fluids.fromID(ids[index]);
        if(type == null || type.getID() != ids[index]) return;
        if(type != this.tank.getTankType()) {
            this.removeFluidSubscriptions();
            this.tank.setTankType(type);
            this.tank.setFill(0);
            this.setChanged();
        }
    }

    @Override public boolean canPlaceItem(int slot, ItemStack stack) {
        if(stack.isEmpty()) return false;
        return switch(slot) {
            case SLOT_INPUT -> this.level != null && this.level.isClientSide
                    ? CrystallizerRecipeClientSync.hasRecipe(stack, this.tank.getTankType()) : CrystallizerRecipes.hasRecipe(stack, this.tank.getTankType());
            case SLOT_BATTERY -> stack.getItem() instanceof IBatteryItem;
            case SLOT_FLUID_IN -> FluidContainerRegistry.getFluidContent(stack, this.tank.getTankType()) > 0
                    || stack.getItem() instanceof InfiniteFluidItem infinite && (infinite.getType() == null || infinite.getType() == this.tank.getTankType())
                    || stack.getItem() instanceof IFillableItem fillable && fillable.providesFluid(this.tank.getTankType(), stack);
            case SLOT_UPGRADE_FIRST, SLOT_UPGRADE_LAST -> stack.getItem() instanceof MachineUpgradeItem upgrade
                    && upgrade.tier > 0 && this.getValidUpgrades().containsKey(upgrade.type);
            case SLOT_IDENTIFIER -> stack.getItem() instanceof IItemFluidIdentifier;
            default -> false;
        };
    }
    @Override public int[] getSlotsForFace(Direction direction) { return AUTOMATION_SLOTS; }
    @Override public boolean canPlaceItemThroughFace(int slot, ItemStack stack, Direction direction) { return slot == SLOT_INPUT && this.canPlaceItem(slot, stack); }
    @Override public boolean canTakeItemThroughFace(int slot, ItemStack stack, Direction direction) { return slot == SLOT_OUTPUT; }
    @Override public void setItem(int slot, ItemStack stack) {
        super.setItem(slot, stack);
        if(this.level != null && !this.level.isClientSide && !stack.isEmpty() && slot >= SLOT_UPGRADE_FIRST && slot <= SLOT_UPGRADE_LAST && stack.getItem() instanceof MachineUpgradeItem) {
            this.level.playSound(null, this.worldPosition, NtmSoundEvents.UPGRADE_PLUG.get(), SoundSource.BLOCKS, 1F, 1F);
        }
    }
    @Override public ItemStack removeItemNoUpdate(int slot) {
        ItemStack removed = super.removeItemNoUpdate(slot);
        if(!removed.isEmpty()) this.setChanged();
        return removed;
    }
    @Override public void clearContent() {
        boolean changed = !this.isEmpty();
        super.clearContent();
        if(changed) this.setChanged();
    }

    public AABB getRenderBoundingBox() {
        if(this.renderBox == null) {
            BlockPos pos = this.worldPosition;
            this.renderBox = new AABB(pos.getX() - 1, pos.getY(), pos.getZ() - 1, pos.getX() + 2, pos.getY() + 10, pos.getZ() + 2);
        }
        return this.renderBox;
    }

    @Override public boolean canProvideInfo(UpgradeType type, int level, TooltipFlag flag) { return type == UpgradeType.SPEED || type == UpgradeType.EFFECT || type == UpgradeType.OVERDRIVE; }
    @Override public void provideInfo(UpgradeType type, int level, List<Component> components, TooltipFlag flag) {
        components.add(IUpgradeInfoProvider.getStandardLabel(NtmBlocks.MACHINE_CRYSTALLIZER.get()));
        if(type == UpgradeType.SPEED) {
            components.add(Component.translatable(KEY_DELAY, "-" + (level * 25) + "%").withStyle(ChatFormatting.GREEN));
            components.add(Component.translatable(KEY_CONSUMPTION, "+" + (level * 100) + "%").withStyle(ChatFormatting.RED));
        }
        if(type == UpgradeType.EFFECT) {
            components.add(Component.translatable(KEY_EFFICIENCY, "x" + level).withStyle(ChatFormatting.GREEN));
            components.add(Component.translatable(KEY_CONSUMPTION, "+" + (level * 200) + "%").withStyle(ChatFormatting.RED));
        }
        if(type == UpgradeType.OVERDRIVE) components.add(Component.translatable(KEY_YES).withStyle(BobMathUtil.getBlink() ? ChatFormatting.RED : ChatFormatting.DARK_GRAY));
    }
    @Override public HashMap<UpgradeType, Integer> getValidUpgrades() {
        HashMap<UpgradeType, Integer> upgrades = new HashMap<>();
        upgrades.put(UpgradeType.SPEED, 3);
        upgrades.put(UpgradeType.EFFECT, 3);
        upgrades.put(UpgradeType.OVERDRIVE, 3);
        return upgrades;
    }

    /** Original NBT: energy and the tank only; progress restarts after a reload and the inventory is saved by the base class. */
    @Override protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.power = Math.max(0L, Math.min(MAX_POWER, tag.getLong("power")));
        if(tag.contains("tank_type")) {
            // The generic reader clamps against the saved maximum; supply the fixed capacity so valid old fluid data survives.
            CompoundTag bounded = tag.copy();
            bounded.putInt("tank_max", TANK_CAPACITY);
            bounded.putShort("tank_p", (short) 0);
            this.tank.readFromNBT(bounded, "tank");
        }
        this.progress = 0;
        this.isOn = false;
        this.duration = DEFAULT_DURATION;
    }
    @Override protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putLong("power", this.power);
        this.tank.writeToNBT(tag, "tank");
    }
    @Override public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeInt(this.progress);
        buf.writeInt(this.duration);
        buf.writeLong(this.power);
        buf.writeBoolean(this.isOn);
        this.tank.serialize(buf);
    }
    @Override public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.progress = buf.readInt();
        this.duration = buf.readInt();
        this.power = buf.readLong();
        this.isOn = buf.readBoolean();
        this.tank.deserialize(buf);
    }
}
