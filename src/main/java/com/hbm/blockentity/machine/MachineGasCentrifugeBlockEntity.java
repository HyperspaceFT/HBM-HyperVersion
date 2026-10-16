package com.hbm.blockentity.machine;

import api.hbm.energymk2.IBatteryItem;
import api.hbm.energymk2.IEnergyReceiverMK2;
import api.hbm.energymk2.PowerNetMK2;
import api.hbm.fluidmk2.FluidNetMK2;
import api.hbm.fluidmk2.IFluidStandardReceiverMK2;
import com.hbm.blockentity.MachineBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.DummyableBlock;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.menus.MachineGasCentrifugeMenu;
import com.hbm.inventory.recipes.GasCentrifugeRecipes;
import com.hbm.inventory.recipes.GasCentrifugeRecipes.PseudoFluidType;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.IItemFluidIdentifier;
import com.hbm.items.machine.MachineUpgradeItem;
import com.hbm.items.machine.MachineUpgradeItem.UpgradeType;
import com.hbm.lib.Library;
import com.hbm.main.NuclearTechMod;
import com.hbm.registry.NtmSoundEvents;
import com.hbm.sound.AudioWrapper;
import com.hbm.uninos.NodeNet;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;

import java.util.ArrayList;
import java.util.List;

/**
 * Gas centrifuge (original TileEntityMachineGasCent). The real tank only holds the identified fluid (UF6 or PUF6); it is
 * converted into the pseudo fluid chain, which is enriched step by step. A machine passes its output pseudo fluid every
 * 10 ticks to the gas centrifuge behind it, so cascades of machines reach the later enrichment stages.
 */
public class MachineGasCentrifugeBlockEntity extends MachineBaseBlockEntity implements IEnergyReceiverMK2, IFluidStandardReceiverMK2 {

    public static final int MAX_POWER = 100_000;
    /** Ticks per enrichment step; the gas centrifuge speed upgrade lowers it by 70 to 80 (original :47, :327-332). */
    public static final int PROCESSING_SPEED = 150;
    public static final int UPGRADED_PROCESSING_SPEED = PROCESSING_SPEED - 70;
    /** HE per progressing tick, 300 with the speed upgrade (original :199-202). */
    public static final int CONSUMPTION = 200;
    public static final int UPGRADED_CONSUMPTION = 300;
    public static final int TANK_CAPACITY = 2_000;
    public static final int PSEUDO_TANK_CAPACITY = 8_000;
    /** A cascade end holding LEUF6 turns 600 mB of its output into 6 uranium fuel nuggets and a fluorite (original :222-229). */
    public static final int LEU_TAIL_AMOUNT = 600;

    public static final int SLOT_OUTPUT_START = 0;
    public static final int SLOT_OUTPUT_END = 4;
    public static final int SLOT_BATTERY = 4;
    public static final int SLOT_IDENTIFIER = 5;
    public static final int SLOT_UPGRADE = 6;
    /** Automation may only take the outputs and inserts nothing (original TileEntityMachineBase defaults). */
    private static final int[] ACCESSIBLE_SLOTS = new int[] { 0, 1, 2, 3 };

    public long power;
    public int progress;
    public boolean isProgressing;

    public final FluidTank tank = new FluidTank(Fluids.UF6, TANK_CAPACITY);
    public final PseudoFluidTank inputTank = new PseudoFluidTank(PseudoFluidType.NUF6, PSEUDO_TANK_CAPACITY);
    public final PseudoFluidTank outputTank = new PseudoFluidTank(PseudoFluidType.LEUF6, PSEUDO_TANK_CAPACITY);

    private FluidType subscribedType;
    private int audioDuration = 0;
    private AudioWrapper audio;
    private AABB renderBox;

    public MachineGasCentrifugeBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.MACHINE_GAS_CENTRIFUGE.get(), pos, state, 7);
    }

    @Override
    protected Component getDefaultName() {
        return Component.translatable("container.machine_gas_centrifuge");
    }

    @Override
    public void updateEntity() {
        if(this.level == null) return;

        if(this.level.isClientSide) {
            this.updateAudio();
            return;
        }

        long previousPower = this.power;
        int previousProgress = this.progress;
        boolean previousProgressing = this.isProgressing;
        FluidType previousType = this.tank.getTankType();
        int previousFill = this.tank.getFill();
        PseudoFluidType previousInputType = this.inputTank.getTankType();
        PseudoFluidType previousOutputType = this.outputTank.getTankType();
        int previousInputFill = this.inputTank.getFill();
        int previousOutputFill = this.outputTank.getFill();
        ItemStack previousBattery = this.slots.get(SLOT_BATTERY).copy();
        boolean changed = false;

        if(this.subscribedType != null && this.subscribedType != previousType) this.removeFluidSubscriptions();
        for(DirPos dirPos : this.getConPos()) {
            if(!this.level.hasChunkAt(dirPos.makeCompat())) continue;
            this.trySubscribe(this.level, dirPos);
            this.trySubscribe(previousType, this.level, dirPos);
        }
        this.subscribedType = previousType;

        this.power = Library.chargeTEFromItems(this.slots, SLOT_BATTERY, this.power, MAX_POWER);
        this.setTankType(SLOT_IDENTIFIER);

        if(GasCentrifugeRecipes.fluidConversions.containsValue(this.inputTank.getTankType())) {
            this.attemptConversion();
        }

        if(this.canEnrich()) {
            this.isProgressing = true;
            this.progress++;
            this.power -= this.hasSpeedUpgrade() ? UPGRADED_CONSUMPTION : CONSUMPTION;

            // The step is paid before the power check, so an underpowered tick wastes its HE and restarts the step.
            if(this.power < 0) {
                this.power = 0;
                this.progress = 0;
            }

            if(this.progress >= this.getProcessingSpeed()) {
                this.enrich();
                changed = true;
            }
        } else {
            this.isProgressing = false;
            this.progress = 0;
        }

        // Every 10 ticks the output is pushed into the gas centrifuge behind this one (original :217-231).
        if(this.level.getGameTime() % 10 == 0) {
            BlockPos behind = this.worldPosition.relative(this.getBlockState().getValue(DummyableBlock.FACING).getOpposite());
            // Never load a chunk from a ticking machine; an unloaded neighbour counts as no cascade.
            BlockEntity target = this.level.hasChunkAt(behind) ? this.level.getBlockEntity(behind) : null;

            if(!this.attemptTransfer(target) && this.inputTank.getTankType() == PseudoFluidType.LEUF6) {
                ItemStack[] converted = new ItemStack[] { new ItemStack(NtmItems.NUGGET_URANIUM_FUEL.get(), 6), new ItemStack(NtmItems.FLUORITE.get()) };

                if(this.outputTank.getFill() >= LEU_TAIL_AMOUNT && this.hasSpaceFor(converted)) {
                    this.outputTank.setFill(this.outputTank.getFill() - LEU_TAIL_AMOUNT);
                    for(ItemStack stack : converted) this.insertOutput(stack);
                    changed = true;
                }
            }
        }

        if(changed || this.power != previousPower || this.progress != previousProgress || this.isProgressing != previousProgressing
                || this.tank.getTankType() != previousType || this.tank.getFill() != previousFill
                || this.inputTank.getTankType() != previousInputType || this.outputTank.getTankType() != previousOutputType
                || this.inputTank.getFill() != previousInputFill || this.outputTank.getFill() != previousOutputFill
                || !ItemStack.matches(previousBattery, this.slots.get(SLOT_BATTERY))) this.setChanged();
        this.networkPackNT(50);
    }

    private void updateAudio() {
        if(this.isProgressing) {
            this.audioDuration += 2;
        } else {
            this.audioDuration -= 3;
        }

        this.audioDuration = Mth.clamp(this.audioDuration, 0, 60);

        Player me = NuclearTechMod.proxy.me();
        BlockPos pos = this.worldPosition;
        if(this.audioDuration > 10 && me != null && me.distanceToSqr(pos.getX() + 0.5, pos.getY() + 0.5, pos.getZ() + 0.5) < 25 * 25) {

            if(this.audio == null) {
                this.audio = this.createAudioLoop();
                if(this.audio != null) this.audio.startSound();
            } else if(!this.audio.isPlaying()) {
                this.audio = this.rebootAudio(this.audio);
            }

            if(this.audio != null) {
                this.audio.updateVolume(this.getVolume(1F));
                // Spins up with the audio duration (original :255).
                this.audio.updatePitch((this.audioDuration - 10) / 100F + 0.5F);
                this.audio.keepAlive();
            }
        } else {
            this.stopAudio();
        }
    }

    private boolean hasSpeedUpgrade() {
        return this.slots.get(SLOT_UPGRADE).getItem() == NtmItems.UPGRADE_GC_SPEED.get();
    }

    public int getProcessingSpeed() {
        return this.hasSpeedUpgrade() ? UPGRADED_PROCESSING_SPEED : PROCESSING_SPEED;
    }

    /** Original :109-129. */
    private boolean canEnrich() {
        PseudoFluidType type = this.inputTank.getTankType();
        if(this.power > 0 && this.inputTank.getFill() >= type.getFluidConsumed() && this.outputTank.getFill() + type.getFluidProduced() <= this.outputTank.getMaxFill()) {

            ItemStack[] list = type.getOutput();

            if(type.getIfHighSpeed() && !this.hasSpeedUpgrade()) return false;
            if(list == null || list.length < 1) return false;

            return this.hasSpaceFor(list);
        }

        return false;
    }

    /** Original :131-140. */
    private void enrich() {
        PseudoFluidType type = this.inputTank.getTankType();
        ItemStack[] output = type.getOutput();

        this.progress = 0;
        this.inputTank.setFill(this.inputTank.getFill() - type.getFluidConsumed());
        this.outputTank.setFill(this.outputTank.getFill() + type.getFluidProduced());

        for(ItemStack stack : output) this.insertOutput(stack.copy());
    }

    /** Converts the real fluid into the input pseudo fluid; it needs no power (original :142-149). */
    private void attemptConversion() {
        if(this.inputTank.getFill() < this.inputTank.getMaxFill() && this.tank.getFill() > 0) {
            int fill = Math.min(this.inputTank.getMaxFill() - this.inputTank.getFill(), this.tank.getFill());

            this.tank.setFill(this.tank.getFill() - fill);
            this.inputTank.setFill(this.inputTank.getFill() + fill);
        }
    }

    /**
     * Pushes this machine's output pseudo fluid into the next gas centrifuge of the cascade, retyping its pseudo tanks when
     * needed. Returns true whenever the target is a gas centrifuge with the same real fluid, even if nothing moved, so the
     * LEUF6 tail conversion only happens at the end of a cascade (original :151-174).
     */
    private boolean attemptTransfer(BlockEntity be) {
        if(be instanceof MachineGasCentrifugeBlockEntity cent && cent.tank.getTankType() == this.tank.getTankType()) {
            boolean changed = false;
            if(cent.inputTank.getTankType() != this.outputTank.getTankType() && this.outputTank.getTankType() != PseudoFluidType.NONE) {
                cent.inputTank.setTankType(this.outputTank.getTankType());
                cent.outputTank.setTankType(this.outputTank.getTankType().getOutputType());
                changed = true;
            }

            if(cent.inputTank.getFill() < cent.inputTank.getMaxFill() && this.outputTank.getFill() > 0) {
                int fill = Math.min(cent.inputTank.getMaxFill() - cent.inputTank.getFill(), this.outputTank.getFill());

                this.outputTank.setFill(this.outputTank.getFill() - fill);
                cent.inputTank.setFill(cent.inputTank.getFill() + fill);
                changed = fill > 0 || changed;
            }

            // The receiver does not tick its own fill change this tick, so it is marked dirty here (NEO-only; the original never marks).
            if(changed) cent.setChanged();
            return true;
        }

        return false;
    }

    /** Original :334-350: only a convertible identifier retypes the machine; anything else leaves the tanks alone. */
    private void setTankType(int slot) {
        if(this.slots.get(slot).getItem() instanceof IItemFluidIdentifier id) {
            FluidType newType = id.getType(this.level, this.worldPosition, this.slots.get(slot));

            if(this.tank.getTankType() != newType) {
                PseudoFluidType pseudo = GasCentrifugeRecipes.fluidConversions.get(newType);

                if(pseudo != null) {
                    this.inputTank.setTankType(pseudo);
                    this.outputTank.setTankType(pseudo.getOutputType());
                    this.tank.setTankType(newType);
                    this.removeFluidSubscriptions();
                }
            }
        }
    }

    private boolean hasSpaceFor(ItemStack[] stacks) {
        ItemStack[] simulated = new ItemStack[SLOT_OUTPUT_END - SLOT_OUTPUT_START];
        for(int i = 0; i < simulated.length; i++) {
            simulated[i] = this.slots.get(SLOT_OUTPUT_START + i).copy();
        }

        for(ItemStack stack : stacks) {
            if(stack.isEmpty()) continue;
            if(!insertIntoSimulation(simulated, stack.copy())) return false;
        }

        return true;
    }

    private static boolean insertIntoSimulation(ItemStack[] simulated, ItemStack stack) {
        for(int i = 0; i < simulated.length && !stack.isEmpty(); i++) {
            ItemStack current = simulated[i];
            if(current.isEmpty()) continue;
            if(!ItemStack.isSameItemSameComponents(current, stack)) continue;

            int moved = Math.min(stack.getCount(), current.getMaxStackSize() - current.getCount());
            if(moved > 0) {
                current.grow(moved);
                stack.shrink(moved);
            }
        }

        for(int i = 0; i < simulated.length && !stack.isEmpty(); i++) {
            ItemStack current = simulated[i];
            if(!current.isEmpty()) continue;

            int moved = Math.min(stack.getCount(), stack.getMaxStackSize());
            ItemStack placed = stack.copy();
            placed.setCount(moved);
            simulated[i] = placed;
            stack.shrink(moved);
        }

        return stack.isEmpty();
    }

    private void insertOutput(ItemStack stack) {
        for(int slot = SLOT_OUTPUT_START; slot < SLOT_OUTPUT_END && !stack.isEmpty(); slot++) {
            ItemStack current = this.slots.get(slot);
            if(current.isEmpty()) continue;
            if(!ItemStack.isSameItemSameComponents(current, stack)) continue;

            int moved = Math.min(stack.getCount(), current.getMaxStackSize() - current.getCount());
            if(moved > 0) {
                current.grow(moved);
                stack.shrink(moved);
            }
        }

        for(int slot = SLOT_OUTPUT_START; slot < SLOT_OUTPUT_END && !stack.isEmpty(); slot++) {
            if(!this.slots.get(slot).isEmpty()) continue;

            int moved = Math.min(stack.getCount(), stack.getMaxStackSize());
            ItemStack placed = stack.copy();
            placed.setCount(moved);
            this.slots.set(slot, placed);
            stack.shrink(moved);
        }
    }

    /**
     * The four sides and the bottom of the core, the four sides of each proxy above it and the top of the column. The
     * proxies forward power and fluid to the core.
     */
    public DirPos[] getConPos() {
        BlockPos core = this.worldPosition;
        List<DirPos> positions = new ArrayList<>();
        positions.add(new DirPos(core.east(), Direction.EAST));
        positions.add(new DirPos(core.west(), Direction.WEST));
        positions.add(new DirPos(core.south(), Direction.SOUTH));
        positions.add(new DirPos(core.north(), Direction.NORTH));
        positions.add(new DirPos(core.below(), Direction.DOWN));
        for(int height = 1; height <= 3; height++) {
            BlockPos proxy = core.above(height);
            positions.add(new DirPos(proxy.east(), Direction.EAST));
            positions.add(new DirPos(proxy.west(), Direction.WEST));
            positions.add(new DirPos(proxy.south(), Direction.SOUTH));
            positions.add(new DirPos(proxy.north(), Direction.NORTH));
        }
        positions.add(new DirPos(core.above(4), Direction.UP));
        return positions.toArray(new DirPos[0]);
    }

    public int getCentrifugeProgressScaled(int pixels) {
        return this.progress * pixels / this.getProcessingSpeed();
    }

    public long getPowerRemainingScaled(int pixels) {
        return this.getPower() * pixels / MAX_POWER;
    }

    @Override
    public boolean canPlaceItem(int slot, ItemStack stack) {
        if(slot == SLOT_BATTERY) return stack.getItem() instanceof IBatteryItem;
        if(slot == SLOT_IDENTIFIER) return stack.getItem() instanceof IItemFluidIdentifier;
        if(slot == SLOT_UPGRADE) return stack.getItem() instanceof MachineUpgradeItem upgrade && upgrade.type == UpgradeType.GS_SPEED;
        return false;
    }

    @Override
    public int[] getSlotsForFace(Direction direction) {
        return ACCESSIBLE_SLOTS;
    }

    @Override
    public boolean canPlaceItemThroughFace(int index, ItemStack stack, Direction direction) {
        return false;
    }

    @Override
    public boolean canTakeItemThroughFace(int index, ItemStack stack, Direction direction) {
        return index >= SLOT_OUTPUT_START && index < SLOT_OUTPUT_END;
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.power = Math.max(0L, Math.min(tag.getLong("power"), MAX_POWER));
        int savedProgress = tag.getShort("progress");
        this.progress = savedProgress >= 0 && savedProgress < PROCESSING_SPEED ? savedProgress : 0;
        // Not saved by the original; persisted like MachineCentrifugeBlockEntity. It is recomputed every server tick and the
        // client gets it from the sync packet, so the key only spares one dirty mark after a load.
        this.isProgressing = tag.getBoolean("isProgressing");
        if(tag.contains("tank_type")) {
            // The generic reader clamps against the saved maximum, including a missing/invalid zero maximum.
            // Supply this machine's fixed capacity before reading to preserve otherwise valid old fluid data.
            CompoundTag tankData = tag.copy();
            tankData.putInt("tank_max", TANK_CAPACITY);
            // This tank is never pressurised (the mixer precedent sanitises the saved pressure the same way).
            tankData.putShort("tank_p", (short) 0);
            this.tank.readFromNBT(tankData, "tank");
            this.tank.changeTankSize(TANK_CAPACITY);
        }
        // Read each pseudo tank only when its key is present, so a partial tag (/setblock with NBT) keeps the default
        // NUF6/LEUF6 types instead of stranding the machine on NONE, which no identifier could recover (review F1).
        if(tag.contains("inputTank_type")) this.inputTank.readFromNBT(tag, "inputTank");
        if(tag.contains("outputTank_type")) this.outputTank.readFromNBT(tag, "outputTank");
        this.inputTank.maxFluid = PSEUDO_TANK_CAPACITY;
        this.outputTank.maxFluid = PSEUDO_TANK_CAPACITY;
        this.subscribedType = null;
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putLong("power", this.power);
        tag.putShort("progress", (short) this.progress);
        tag.putBoolean("isProgressing", this.isProgressing);
        this.tank.writeToNBT(tag, "tank");
        this.inputTank.writeToNBT(tag, "inputTank");
        this.outputTank.writeToNBT(tag, "outputTank");
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeLong(this.power);
        buf.writeInt(this.progress);
        buf.writeBoolean(this.isProgressing);
        buf.writeInt(this.inputTank.getFill());
        buf.writeInt(this.outputTank.getFill());
        buf.writeUtf(this.inputTank.getTankType().name);
        buf.writeUtf(this.outputTank.getTankType().name);
        this.tank.serialize(buf);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.power = buf.readLong();
        this.progress = buf.readInt();
        this.isProgressing = buf.readBoolean();
        int inputFill = buf.readInt();
        int outputFill = buf.readInt();
        // NEO-only correction: retype before applying the fills, since a retype zeroes the fill. The original applied the
        // fills first and showed an empty tank for one packet after every retype.
        this.inputTank.setTankType(PseudoFluidType.types.get(buf.readUtf()));
        this.outputTank.setTankType(PseudoFluidType.types.get(buf.readUtf()));
        this.inputTank.setFill(inputFill);
        this.outputTank.setFill(outputFill);
        this.tank.deserialize(buf);
    }

    @Override
    public long getPower() {
        return Math.max(0L, Math.min(this.power, this.getMaxPower()));
    }

    @Override
    public void setPower(long power) {
        long bounded = Math.max(0L, Math.min(power, this.getMaxPower()));
        if(this.power != bounded) { this.power = bounded; this.setChanged(); }
    }

    @Override
    public long getMaxPower() {
        return MAX_POWER;
    }

    @Override public FluidTank[] getReceivingTanks() { return new FluidTank[] { this.tank }; }
    @Override public FluidTank[] getAllTanks() { return new FluidTank[] { this.tank }; }

    @Override
    public long transferFluid(FluidType type, int pressure, long amount) {
        long remainder = IFluidStandardReceiverMK2.super.transferFluid(type, pressure, amount);
        if(remainder < amount) this.setChanged();
        return remainder;
    }

    @Override
    public AbstractContainerMenu createMenu(int id, Inventory inventory, Player player) {
        return new MachineGasCentrifugeMenu(id, inventory, this);
    }

    @Override
    public AudioWrapper createAudioLoop() {
        return AudioWrapper.getLoopedSound(NtmSoundEvents.CENTRIFUGE_OPERATE.get(), SoundSource.BLOCKS, this, 1.0F, 10F, 1.0F, 20);
    }

    private void stopAudio() {
        if(this.audio != null) {
            this.audio.stopSound();
            this.audio = null;
        }
    }

    private void removeFluidSubscriptions() {
        if(this.level == null || this.level.isClientSide) return;
        for(NodeNet net : new ArrayList<>(UniNodespace.activeNodeNets)) if(net instanceof FluidNetMK2 fluidNet) fluidNet.removeReceiver(this);
        this.subscribedType = null;
    }

    private void removeNetworkSubscriptions() {
        if(this.level == null || this.level.isClientSide) return;
        this.removeFluidSubscriptions();
        for(NodeNet net : new ArrayList<>(UniNodespace.activeNodeNets)) {
            if(net instanceof PowerNetMK2 powerNet) powerNet.removeReceiver(this);
        }
    }

    @Override
    public ItemStack removeItemNoUpdate(int slot) {
        ItemStack removed = super.removeItemNoUpdate(slot);
        if(!removed.isEmpty()) this.setChanged();
        return removed;
    }

    @Override
    public void clearContent() {
        boolean changed = !this.isEmpty();
        super.clearContent();
        if(changed) this.setChanged();
    }

    @Override
    public void onChunkUnloaded() {
        this.removeNetworkSubscriptions();
        super.onChunkUnloaded();
        this.stopAudio();
    }

    @Override
    public void setRemoved() {
        this.removeNetworkSubscriptions();
        super.setRemoved();
        this.stopAudio();
    }

    public AABB getRenderBoundingBox() {
        if(this.renderBox == null) {
            BlockPos pos = this.getBlockPos();
            this.renderBox = new AABB(pos.getX(), pos.getY(), pos.getZ(), pos.getX() + 1, pos.getY() + 5, pos.getZ() + 1);
        }
        return this.renderBox;
    }

    /**
     * A tank for the enrichment pseudo fluids (original :379-432). Fills are not clamped, and a retype zeroes the fill.
     * NBT: the fill under the key, the capacity under key_max and the pseudo fluid name under key_type.
     */
    public static class PseudoFluidTank {
        private PseudoFluidType type;
        private int fluid;
        private int maxFluid;

        public PseudoFluidTank(PseudoFluidType type, int maxFluid) {
            this.type = type;
            this.maxFluid = maxFluid;
        }

        public void setFill(int i) {
            this.fluid = i;
        }

        public void setTankType(PseudoFluidType type) {
            if(this.type.equals(type)) return;

            this.type = type == null ? PseudoFluidType.NONE : type;
            this.setFill(0);
        }

        public PseudoFluidType getTankType() { return this.type; }
        public int getFill() { return this.fluid; }
        public int getMaxFill() { return this.maxFluid; }

        public void writeToNBT(CompoundTag tag, String s) {
            tag.putInt(s, this.fluid);
            tag.putInt(s + "_max", this.maxFluid);
            tag.putString(s + "_type", this.type.name);
        }

        public void readFromNBT(CompoundTag tag, String s) {
            this.fluid = tag.getInt(s);
            int max = tag.getInt(s + "_max");
            if(max > 0) this.maxFluid = max;
            this.type = PseudoFluidType.types.get(tag.getString(s + "_type"));
            if(this.type == null) this.type = PseudoFluidType.NONE;
        }
    }
}
