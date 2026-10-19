package com.hbm.blockentity.machine;

import api.hbm.energymk2.IEnergyProviderMK2;
import api.hbm.energymk2.PowerNetMK2;
import com.hbm.blockentity.MachineBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.inventory.menus.MachineRTGMenu;
import com.hbm.items.machine.RTGPelletItem;
import com.hbm.uninos.NodeNet;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.RTGUtil;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.state.BlockState;

import java.util.ArrayList;

/** Port of the original TileEntityMachineRTG; the original's Energy Control info provider has no NEO equivalent. */
public class MachineRTGBlockEntity extends MachineBaseBlockEntity implements IEnergyProviderMK2 {

    public static final long MAX_POWER = 100_000L;
    public static final int[] SLOT_IO = { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14 };
    private static final int[] NO_SLOTS = new int[0];

    public int heat;
    public long power;

    public MachineRTGBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.MACHINE_RTG.get(), pos, state, 15);
    }

    /** Original heatMax (:28). Read at run time, because NeoForge loads the common config after registration (Goal 23 decision 8). */
    public static int getHeatMax() {
        return RTGUtil.rtgDecay() ? 600 : 200;
    }

    @Override
    protected Component getDefaultName() {
        return Component.translatable("container.rtg");
    }

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
        if(this.level == null || this.level.isClientSide) return;

        // The original provides power before updating the pellets, so a directly adjacent receiver is offered the previous tick's power.
        for(DirPos pos : this.getConPos()) this.tryProvide(this.level, pos.makeCompat(), pos.getDir());

        long previousPower = this.power;
        int previousHeat = this.heat;
        boolean decays = RTGUtil.rtgDecay() && RTGUtil.hasHeat(this.slots, SLOT_IO);

        this.heat = RTGUtil.updateRTGs(this.slots, SLOT_IO);
        if(this.heat > getHeatMax()) this.heat = getHeatMax();

        this.power += (long) this.heat * 5L;
        if(this.power > MAX_POWER) this.power = MAX_POWER;

        // updateRTGs changes the pellet stacks in place (pellet depletion and the depleted-pellet swap go through NonNullList.set, not
        // setItem), so nothing else marks the chunk for saving. The inventory itself is not pushed with block updates; only power and
        // heat are synced below.
        if(decays || this.power != previousPower || this.heat != previousHeat) this.setChanged();

        this.networkPackNT(50);
    }

    public int getHeatScaled(int i) { return this.heat * i / getHeatMax(); }
    public long getPowerScaled(long i) { return this.power * i / MAX_POWER; }
    public boolean hasHeat() { return RTGUtil.hasHeat(this.slots, SLOT_IO); }
    public boolean hasPower() { return this.power > 0; }

    /** NEO-only tightening of the GUI slots to RTG pellets (Goal 23 decision 12); the original GUI slots accepted any item. */
    @Override
    public boolean canPlaceItem(int slot, ItemStack stack) {
        return slot >= 0 && slot < 15 && stack.getItem() instanceof RTGPelletItem;
    }

    /** One pellet per slot: updateRTGs counts a slot once, so a larger stack would add heat once and share one life. The pellets already
     *  stack to 1; this is defence in depth for stacks set by commands. */
    @Override
    public int getMaxStackSize() {
        return 1;
    }

    // As the original, automation neither inserts nor extracts.
    @Override public int[] getSlotsForFace(Direction direction) { return NO_SLOTS; }
    @Override public boolean canPlaceItemThroughFace(int index, ItemStack stack, Direction direction) { return false; }
    @Override public boolean canTakeItemThroughFace(int index, ItemStack stack, Direction direction) { return false; }

    @Override public long getPower() { return this.power; }
    @Override public long getMaxPower() { return MAX_POWER; }
    @Override public void setPower(long power) {
        long bounded = Math.max(0L, Math.min(MAX_POWER, power));
        if(this.power != bounded) {
            this.power = bounded;
            this.setChanged();
        }
    }

    private void removeNetworkSubscriptions() {
        if(this.level == null || this.level.isClientSide) return;
        for(NodeNet net : new ArrayList<>(UniNodespace.activeNodeNets)) {
            if(net instanceof PowerNetMK2 powerNet) powerNet.removeProvider(this);
        }
    }

    @Override
    public void onChunkUnloaded() {
        this.removeNetworkSubscriptions();
        super.onChunkUnloaded();
    }

    @Override
    public void setRemoved() {
        this.removeNetworkSubscriptions();
        super.setRemoved();
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.power = Math.max(0L, Math.min(MAX_POWER, tag.getLong("power")));
        this.heat = tag.getInt("heat");
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putLong("power", this.power);
        tag.putInt("heat", this.heat);
    }

    // The original syncs only power here and sends heat through its container; NEO syncs both with the block entity packet.
    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeLong(this.power);
        buf.writeInt(this.heat);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.power = buf.readLong();
        this.heat = buf.readInt();
    }

    @Override
    public AbstractContainerMenu createMenu(int id, Inventory inventory, Player player) {
        return new MachineRTGMenu(id, inventory, this);
    }
}
