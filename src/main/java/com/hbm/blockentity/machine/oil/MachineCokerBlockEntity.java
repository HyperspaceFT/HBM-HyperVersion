package com.hbm.blockentity.machine.oil;

import api.hbm.fluidmk2.FluidNetMK2;
import api.hbm.fluidmk2.IFluidStandardTransceiverMK2;
import api.hbm.tile.IHeatSource;
import com.hbm.blockentity.IFluidCopiable;
import com.hbm.blockentity.MachineBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.handler.pollution.PollutionHandler;
import com.hbm.handler.pollution.PollutionHandler.PollutionType;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.menus.MachineCokerMenu;
import com.hbm.inventory.recipes.CokerRecipes;
import com.hbm.inventory.recipes.CokerRecipes.CokerRecipe;
import com.hbm.items.machine.IItemFluidIdentifier;
import com.hbm.particle.NtmParticleTypes;
import com.hbm.particle.vanilla.NbtParticleOptions;
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
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;

import java.util.ArrayList;

public class MachineCokerBlockEntity extends MachineBaseBlockEntity implements IFluidStandardTransceiverMK2, IFluidCopiable {

    public static final int PROCESS_TIME = 20_000;
    public static final int MAX_HEAT = 100_000;
    public static final int INPUT_CAPACITY = 16_000;
    public static final int BYPRODUCT_CAPACITY = 8_000;
    public static final int SLOT_IDENTIFIER = 0;
    public static final int SLOT_OUTPUT = 1;
    private static final int[] AUTOMATION_SLOTS = { SLOT_OUTPUT };

    public final FluidTank[] tanks = { new FluidTank(Fluids.HEAVYOIL, INPUT_CAPACITY), new FluidTank(Fluids.OIL_COKER, BYPRODUCT_CAPACITY) };
    public int heat;
    public int progress;
    public boolean wasOn;
    private FluidType subscribedType;

    public MachineCokerBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.MACHINE_COKER.get(), pos, state, 2);
    }

    @Override protected Component getDefaultName() { return Component.translatable("container.machine_coker"); }
    @Override public AbstractContainerMenu createMenu(int id, Inventory inventory, Player player) { return new MachineCokerMenu(id, inventory, this); }

    /** Four shared inventory/fluid proxies, each with two outward fluid faces. */
    public static DirPos[] getPortProxies(BlockPos core) {
        return new DirPos[] {
                new DirPos(core.offset(-1, 0, -1), Direction.WEST), new DirPos(core.offset(1, 0, -1), Direction.EAST),
                new DirPos(core.offset(1, 0, 1), Direction.EAST), new DirPos(core.offset(-1, 0, 1), Direction.WEST)
        };
    }

    public DirPos[] getConPos() {
        BlockPos core = this.worldPosition;
        return new DirPos[] {
                new DirPos(core.offset(-2, 0, -1), Direction.WEST), new DirPos(core.offset(-1, 0, -2), Direction.NORTH),
                new DirPos(core.offset(2, 0, -1), Direction.EAST), new DirPos(core.offset(1, 0, -2), Direction.NORTH),
                new DirPos(core.offset(2, 0, 1), Direction.EAST), new DirPos(core.offset(1, 0, 2), Direction.SOUTH),
                new DirPos(core.offset(-2, 0, 1), Direction.WEST), new DirPos(core.offset(-1, 0, 2), Direction.SOUTH)
        };
    }

    @Override
    public void updateEntity() {
        if(this.level == null) return;
        if(this.level.isClientSide) {
            if(this.wasOn && this.level.getGameTime() % 2 == 0) {
                CompoundTag tag = new CompoundTag();
                tag.putFloat("lift", 10F);
                tag.putFloat("base", 0.75F);
                tag.putFloat("max", 3F);
                tag.putInt("life", 200 + this.level.random.nextInt(50));
                tag.putInt("color", 0x404040);
                this.level.addParticle(new NbtParticleOptions(NtmParticleTypes.COOLING_TOWER.get(), tag),
                        this.worldPosition.getX() + 0.5, this.worldPosition.getY() + 22, this.worldPosition.getZ() + 0.5, 0D, 0D, 0D);
            }
            return;
        }
        int previousHeat = this.heat;
        int previousProgress = this.progress;
        boolean previousOn = this.wasOn;
        FluidType previousInputType = this.tanks[0].getTankType();
        FluidType previousOutputType = this.tanks[1].getTankType();
        int previousInput = this.tanks[0].getFill();
        int previousOutput = this.tanks[1].getFill();

        if(this.subscribedType != null && this.subscribedType != previousInputType) this.removeFluidSubscriptions();
        for(DirPos connection : this.getConPos()) {
            if(previousInputType != Fluids.NONE) this.trySubscribe(previousInputType, this.level, connection);
            if(this.tanks[1].getFill() > 0) this.tryProvide(this.tanks[1], this.level, connection);
        }
        this.subscribedType = previousInputType;

        this.tryPullHeat();
        if(this.tanks[0].setType(SLOT_IDENTIFIER, this.slots)) {
            this.removeFluidSubscriptions();
            this.setChanged();
        }
        this.wasOn = false;
        if(this.canProcess()) {
            int burn = this.heat / 100;
            if(burn > 0) {
                this.wasOn = true;
                // Edited oversized progress cannot wrap negative; normal operation retains its exact remainder.
                this.progress = (int) Math.min(Integer.MAX_VALUE, (long) this.progress + burn);
                this.heat -= burn;
                if(this.progress >= PROCESS_TIME && this.process()) this.progress -= PROCESS_TIME;
            }
            if(this.wasOn && this.level.getGameTime() % 5 == 0) {
                PollutionHandler.incrementPollution(this.level, this.worldPosition, PollutionType.SOOT, PollutionHandler.SOOT_PER_SECOND * 5);
            }
        }

        if(this.heat != previousHeat || this.progress != previousProgress || this.wasOn != previousOn
                || this.tanks[0].getTankType() != previousInputType || this.tanks[1].getTankType() != previousOutputType
                || this.tanks[0].getFill() != previousInput || this.tanks[1].getFill() != previousOutput) this.setChanged();
        this.networkPackNT(25);
    }

    public CokerRecipe getRecipe() { return CokerRecipes.getRecipe(this.tanks[0].getTankType()); }

    public boolean canProcess() {
        CokerRecipe recipe = this.getRecipe();
        if(recipe == null) return false;
        FluidStack byproduct = recipe.byproduct();
        // Upstream intentionally changes/clears the byproduct before checking input and output space.
        if(byproduct != null && this.tanks[1].getTankType() != byproduct.type) {
            this.removeFluidSubscriptions();
            this.tanks[1].setTankType(byproduct.type);
            this.setChanged();
        }
        if(this.tanks[0].getFill() < recipe.inputAmount()) return false;
        if(byproduct != null && (long) this.tanks[1].getFill() + byproduct.fill > this.tanks[1].getMaxFill()) return false;
        ItemStack output = recipe.itemOutput();
        if(!output.isEmpty()) {
            ItemStack existing = this.slots.get(SLOT_OUTPUT);
            int limit = Math.min(output.getMaxStackSize(), this.getMaxStackSize(output));
            if(output.getCount() > limit) return false;
            if(!existing.isEmpty() && (!ItemStack.isSameItemSameComponents(output, existing)
                    || (long) existing.getCount() + output.getCount() > limit)) return false;
        }
        return true;
    }

    /** A full transaction; progress/heat are accounted by the tick, including at most one completion. */
    public boolean process() {
        if(!this.canProcess()) return false;
        CokerRecipe recipe = this.getRecipe();
        ItemStack output = recipe.itemOutput();
        FluidStack byproduct = recipe.byproduct();
        if(!output.isEmpty()) {
            if(this.slots.get(SLOT_OUTPUT).isEmpty()) this.slots.set(SLOT_OUTPUT, output);
            else this.slots.get(SLOT_OUTPUT).grow(output.getCount());
        }
        if(byproduct != null) this.tanks[1].setFill(this.tanks[1].getFill() + byproduct.fill);
        this.tanks[0].setFill(this.tanks[0].getFill() - recipe.inputAmount());
        this.setChanged();
        return true;
    }

    protected void tryPullHeat() {
        if(this.heat >= MAX_HEAT || this.level == null) return;
        BlockEntity below = this.level.getBlockEntity(this.worldPosition.below());
        if(below instanceof IHeatSource source) {
            long difference = (long) source.getHeatStored() - this.heat;
            if(difference == 0) return;
            if(difference > 0) {
                int pulled = (int) ((difference + 3) / 4);
                source.useUpHeat(pulled);
                // The interface need not save itself. Existing heaters do; other BlockEntity sources also must save.
                below.setChanged();
                this.heat = (int) Math.min(MAX_HEAT, (long) this.heat + pulled);
                this.setChanged();
                return;
            }
        }
        int cooled = Math.max(this.heat - Math.max(this.heat / 1000, 1), 0);
        if(cooled != this.heat) { this.heat = cooled; this.setChanged(); }
    }

    private void removeFluidSubscriptions() {
        if(this.level == null || this.level.isClientSide) return;
        for(NodeNet net : new ArrayList<>(UniNodespace.activeNodeNets)) {
            if(net instanceof FluidNetMK2 fluidNet) {
                fluidNet.removeReceiver(this);
                fluidNet.removeProvider(this);
            }
        }
        this.subscribedType = null;
    }

    @Override public void onChunkUnloaded() { this.removeFluidSubscriptions(); super.onChunkUnloaded(); }
    @Override public void setRemoved() { this.removeFluidSubscriptions(); super.setRemoved(); }
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

    @Override public boolean canPlaceItem(int slot, ItemStack stack) { return slot == SLOT_IDENTIFIER && stack.getItem() instanceof IItemFluidIdentifier; }
    @Override public int[] getSlotsForFace(Direction direction) { return AUTOMATION_SLOTS; }
    @Override public boolean canPlaceItemThroughFace(int slot, ItemStack stack, Direction direction) { return false; }
    @Override public boolean canTakeItemThroughFace(int slot, ItemStack stack, Direction direction) { return slot == SLOT_OUTPUT; }
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

    @Override public FluidTank getTankToPaste() { return this.tanks[0]; }
    @Override public void pasteSettings(CompoundTag tag, int index, Level level, Player player, BlockPos pos) {
        if(tag == null || level != this.level || level.isClientSide || !this.worldPosition.equals(pos)
                || player.level() != level || !this.stillValid(player) || !tag.contains("FluidID", Tag.TAG_INT_ARRAY)) return;
        int[] ids = tag.getIntArray("FluidID");
        if(index < 0 || index >= ids.length) return;
        FluidType type = Fluids.fromID(ids[index]);
        if(type == Fluids.NONE && ids[index] != Fluids.NONE.getID()) return;
        if(type != this.tanks[0].getTankType()) {
            this.removeFluidSubscriptions();
            this.tanks[0].setTankType(type);
            this.setChanged();
        }
    }

    @Override protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        this.heat = Math.max(0, Math.min(MAX_HEAT, tag.getInt("heat")));
        this.progress = Math.max(0, tag.getInt("prog"));
        this.tanks[0].readFromNBT(tag, "t0");
        this.tanks[1].readFromNBT(tag, "t1");
        this.tanks[0].changeTankSize(INPUT_CAPACITY);
        this.tanks[1].changeTankSize(BYPRODUCT_CAPACITY);
        for(FluidTank tank : this.tanks) tank.setFill(Math.max(0, Math.min(tank.getMaxFill(), tank.getFill())));
        this.wasOn = false;
    }
    @Override protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.putInt("heat", this.heat);
        tag.putInt("prog", this.progress);
        this.tanks[0].writeToNBT(tag, "t0");
        this.tanks[1].writeToNBT(tag, "t1");
    }
    @Override public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        buf.writeBoolean(this.wasOn);
        buf.writeInt(this.heat);
        buf.writeInt(this.progress);
        this.tanks[0].serialize(buf);
        this.tanks[1].serialize(buf);
    }
    @Override public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.wasOn = buf.readBoolean();
        this.heat = buf.readInt();
        this.progress = buf.readInt();
        this.tanks[0].deserialize(buf);
        this.tanks[1].deserialize(buf);
    }
    public AABB getRenderBoundingBox() {
        return new AABB(this.worldPosition.getX() - 2, this.worldPosition.getY(), this.worldPosition.getZ() - 2,
                this.worldPosition.getX() + 3, this.worldPosition.getY() + 23, this.worldPosition.getZ() + 3);
    }
}
