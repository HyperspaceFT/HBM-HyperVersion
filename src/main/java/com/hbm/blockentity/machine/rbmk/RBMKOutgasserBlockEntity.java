package com.hbm.blockentity.machine.rbmk;

import api.hbm.fluidmk2.IFluidStandardSenderMK2;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.entity.projectile.RBMKDebris.DebrisType;
import com.hbm.handler.OutgasserRecipeClientSync;
import com.hbm.handler.neutron.NeutronStream;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.menus.RBMKOutgasserMenu;
import com.hbm.inventory.recipes.OutgasserRecipes;
import com.hbm.inventory.recipes.OutgasserRecipes.OutgasserRecipe;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Original TileEntityRBMKOutgasser (:34-216): the irradiation channel. The neutron flux it takes (RBMKNeutronHandler, only while
 * canProcess) fills the progress; at DURATION the input in slot 0 turns into the row's solid output in slot 1 and its gas in the tank,
 * which is sent out through the column's ports (RBMKBaseBlockEntity.getPortConnections). The OpenComputers callbacks (:219-272) are
 * not ported (GOAL25); progress, gas and canProcess stay public.
 */
public class RBMKOutgasserBlockEntity extends RBMKSlottedBaseBlockEntity implements IRBMKFluxReceiver, IFluidStandardSenderMK2 {

    public static final int DURATION = 10000;
    private static final int[] SLOTS = new int[] {0, 1};

    public FluidTank gas = new FluidTank(Fluids.TRITIUM, 64000);
    public double progress;

    public RBMKOutgasserBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.RBMK_OUTGASSER.get(), pos, state, 2);
    }

    @Override
    public String getContainerName() {
        return "container.rbmkOutgasser";
    }

    /** Original updateEntity (:55-66). The ticker runs on both sides; the ports and the progress reset are server side. */
    @Override
    public void updateEntity() {
        Level world = this.getLevel();

        if(world != null && !world.isClientSide) {

            // The original's port module only provides (setOutputTanks); NEO renews the providers every tick as the boiler does.
            for(DirPos con : this.getPortConnections()) {
                this.tryProvide(gas, world, con);
            }

            if(!canProcess()) this.progress = 0;
        }

        super.updateEntity();
    }

    /** Original receiveFlux (:69-82). */
    @Override
    public void receiveFlux(NeutronStream stream) {

        if(canProcess()) {

            double efficiency = Math.min(1 - stream.fluxRatio * 0.8, 1);

            progress += stream.fluxQuantity * efficiency * RBMKDials.getOutgasserMod();

            if(progress > DURATION) {
                process();
                this.setChanged();
            }
        }
    }

    /** Original canProcess (:84-108). */
    public boolean canProcess() {

        ItemStack input = this.slots.get(0);
        if(input.isEmpty()) return false;

        OutgasserRecipe output = OutgasserRecipes.getOutput(input);

        if(output == null) return false;
        if(output.fusionOnly) return false;

        FluidStack fluid = output.fluidOutput;

        if(fluid != null) {
            if(gas.getTankType() != fluid.type && gas.getFill() > 0) return false;
            // Upstream-shared side effect: an empty tank takes the row's gas type even if the capacity test below fails. The type
            // only changes while the tank is empty, so FluidTank.setTankType clearing the fill on a type change loses nothing.
            gas.setTankType(fluid.type);
            if(gas.getFill() + fluid.fill > gas.getMaxFill()) return false;
        }

        ItemStack out = output.solidOutput;
        ItemStack slot = this.slots.get(1);

        if(slot.isEmpty() || out.isEmpty()) return true;

        return ItemStack.isSameItemSameComponents(slot, out) && slot.getCount() + out.getCount() <= slot.getMaxStackSize();
    }

    /** Original process (:110-129). */
    private void process() {

        OutgasserRecipe output = OutgasserRecipes.getOutput(this.slots.get(0));
        this.removeItem(0, 1);
        this.progress = 0;

        if(output.fluidOutput != null) {
            gas.setFill(gas.getFill() + output.fluidOutput.fill);
        }

        ItemStack out = output.solidOutput;

        if(!out.isEmpty()) {
            if(this.slots.get(1).isEmpty()) {
                this.slots.set(1, out.copy());
            } else {
                this.slots.get(1).grow(out.getCount());
            }
        }
    }

    /** Original onMelt (:131-141). */
    @Override
    public void onMelt(int reduce) {

        int count = 4 + this.level.random.nextInt(2);

        for(int i = 0; i < count; i++) {
            spawnDebris(DebrisType.BLANK);
        }

        super.onMelt(reduce);
    }

    @Override
    public RBMKType getRBMKType() {
        return RBMKType.OUTGASSER;
    }

    @Override
    public RBMKColumnType getConsoleType() {
        return RBMKColumnType.OUTGASSER;
    }

    /** Original :153-161 builds a compound with these keys only; NEO adds them to the base heat/maxHeat (24C convention). */
    @Override
    public CompoundTag getNBTForConsole() {
        CompoundTag data = super.getNBTForConsole();
        data.putInt("gas", this.gas.getFill());
        data.putInt("maxGas", this.gas.getMaxFill());
        data.putShort("type", (short)this.gas.getTankType().getID());
        data.putDouble("progress", this.progress);
        return data;
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);

        this.progress = tag.getDouble("progress");
        this.gas.readFromNBT(tag, "gas");
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);

        tag.putDouble("progress", this.progress);
        this.gas.writeToNBT(tag, "gas");
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        this.gas.serialize(buf);
        buf.writeDouble(this.progress);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.gas.deserialize(buf);
        this.progress = buf.readDouble();
    }

    // The original diag dump is writeToNBT without the parent keys (TileEntityRBMKBase :265-311), so it holds progress and the tank.
    @Override
    public void getDiagData(CompoundTag nbt) {
        super.getDiagData(nbt);

        nbt.putDouble("progress", this.progress);
        gas.writeToNBT(nbt, "gas");
    }

    // Original isItemValidForSlot, canExtractItem and getAccessibleSlotsFromSide (:194-205): inputs with a row go into slot 0,
    // only slot 1 is extracted. Overrides the slotted base, which exposes nothing to automation; insertion through a face asks
    // canPlaceItem (MachineBaseBlockEntity.canPlaceItemThroughFace). The client asks its synchronized table, as the waste drum.
    @Override
    public boolean canPlaceItem(int slot, ItemStack stack) {
        if(slot != 0) return false;
        return (this.level != null && this.level.isClientSide ? OutgasserRecipeClientSync.getOutput(stack) : OutgasserRecipes.getOutput(stack)) != null;
    }

    @Override
    public int[] getSlotsForFace(Direction direction) {
        return SLOTS;
    }

    @Override
    public boolean canTakeItemThroughFace(int index, ItemStack stack, Direction direction) {
        return index == 1;
    }

    @Override
    public FluidTank[] getAllTanks() {
        return new FluidTank[] {gas};
    }

    @Override
    public FluidTank[] getSendingTanks() {
        return new FluidTank[] {gas};
    }

    @Override
    public AbstractContainerMenu createMenu(int containerId, Inventory inventory, Player player) {
        return new RBMKOutgasserMenu(containerId, inventory, this);
    }
}
