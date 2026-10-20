package com.hbm.blockentity.machine.rbmk;

import api.hbm.fluidmk2.IFluidStandardTransceiverMK2;
import api.hbm.redstoneoverradio.IRORValueProvider;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.entity.projectile.RBMKDebris.DebrisType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.fluid.trait.FT_Heatable;
import com.hbm.inventory.fluid.trait.FT_Heatable.HeatingStep;
import com.hbm.inventory.fluid.trait.FT_Heatable.HeatingType;
import com.hbm.inventory.menus.RBMKHeaterMenu;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;

/**
 * Original TileEntityRBMKHeater: the fluid heater, which heats the fluid picked with the identifier in its slot (coolant by
 * default) with the column's heat, using the fluid's first heat exchanger step. The hot fluid's temperature is the floor: below it
 * nothing is heated (hot coolant is 600 degrees). The OpenComputers callbacks are not ported (GOAL24 decision 6).
 */
public class RBMKHeaterBlockEntity extends RBMKSlottedBaseBlockEntity implements IFluidStandardTransceiverMK2, IRORValueProvider {

    public FluidTank feed = new FluidTank(Fluids.COOLANT, 16_000);
    public FluidTank steam = new FluidTank(Fluids.COOLANT_HOT, 16_000);

    public RBMKHeaterBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.RBMK_HEATER.get(), pos, state, 1);
    }

    @Override
    public String getContainerName() {
        return "container.rbmkHeater";
    }

    /** Original updateEntity (:52-93). The ticker runs on both sides; everything here is server side. */
    @Override
    public void updateEntity() {
        Level world = this.getLevel();

        if(world != null && !world.isClientSide) {

            // Renewed every tick, see RBMKBoilerBlockEntity.updateEntity.
            for(DirPos con : this.getPortConnections()) {
                this.trySubscribe(feed.getTankType(), world, con);
                this.tryProvide(steam, world, con);
            }

            if(this.heat <= 50 || this.feed.getFill() <= 0) {
                if(feed.setType(0, slots)) this.setChanged();
            }

            if(feed.getTankType().hasTrait(FT_Heatable.class)) {
                FT_Heatable trait = feed.getTankType().getTrait(FT_Heatable.class);
                HeatingStep step = trait.getFirstStep();
                steam.setTankType(step.typeProduced);
                double tempRange = this.heat - steam.getTankType().temperature;
                double eff = trait.getEfficiency(HeatingType.HEATEXCHANGER);

                if(tempRange > 0 && eff > 0) {
                    double TU_PER_DEGREE = 2_000D * eff; //based on 1mB of water absorbing 200 TU as well as 0.1°C from an RBMK column
                    int inputOps = feed.getFill() / step.amountReq;
                    int outputOps = (steam.getMaxFill() - steam.getFill()) / step.amountProduced;
                    int tempOps = (int) Math.floor((tempRange * TU_PER_DEGREE) / step.heatReq);
                    int ops = Math.min(inputOps, Math.min(outputOps, tempOps));

                    feed.setFill(feed.getFill() - step.amountReq * ops);
                    steam.setFill(steam.getFill() + step.amountProduced * ops);
                    this.heat -= (step.heatReq * ops / TU_PER_DEGREE) * trait.getEfficiency(HeatingType.HEATEXCHANGER);

                    if(ops != 0) this.setChanged();
                }

                if(eff <= 0) {
                    feed.setTankType(Fluids.NONE);
                    steam.setTankType(Fluids.NONE);
                }

            } else {
                feed.setTankType(Fluids.NONE);
                steam.setTankType(Fluids.NONE);
            }
        }

        super.updateEntity();
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);

        feed.readFromNBT(tag, "feed");
        steam.readFromNBT(tag, "steam");
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);

        feed.writeToNBT(tag, "feed");
        steam.writeToNBT(tag, "steam");
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        this.feed.serialize(buf);
        this.steam.serialize(buf);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.feed.deserialize(buf);
        this.steam.deserialize(buf);
    }

    @Override
    public void onMelt(int reduce) {

        int count = 1 + getLevel().random.nextInt(2);

        for(int i = 0; i < count; i++) {
            spawnDebris(DebrisType.BLANK);
        }

        super.onMelt(reduce);
    }

    @Override
    public RBMKColumnType getConsoleType() {
        return RBMKColumnType.HEATEX;
    }

    /** Original :142-152 builds a compound with these keys only; NEO adds them to the base heat/maxHeat (24C convention). */
    @Override
    public CompoundTag getNBTForConsole() {
        CompoundTag data = super.getNBTForConsole();
        data.putInt("water", this.feed.getFill());
        data.putInt("maxWater", this.feed.getMaxFill());
        data.putInt("steam", this.steam.getFill());
        data.putInt("maxSteam", this.steam.getMaxFill());
        data.putShort("type", (short)this.feed.getTankType().getID());
        data.putShort("hottype", (short)this.steam.getTankType().getID());
        return data;
    }

    @Override
    public void getDiagData(CompoundTag nbt) {
        super.getDiagData(nbt);

        feed.writeToNBT(nbt, "feed");
        steam.writeToNBT(nbt, "steam");
    }

    @Override
    public FluidTank[] getAllTanks() {
        return new FluidTank[] {feed, steam};
    }

    @Override
    public FluidTank[] getSendingTanks() {
        return new FluidTank[] {steam};
    }

    @Override
    public FluidTank[] getReceivingTanks() {
        return new FluidTank[] {feed};
    }

    @Override
    public AbstractContainerMenu createMenu(int containerId, Inventory inventory, Player player) {
        return new RBMKHeaterMenu(containerId, inventory, this);
    }

    @Override
    public String[] getFunctionInfo() {
        return new String[] {
                PREFIX_VALUE + "in",
                PREFIX_VALUE + "out"
        };
    }

    @Override
    public String provideRORValue(String name) {
        if((PREFIX_VALUE + "in").equals(name))      return "" + this.feed.getFill();
        if((PREFIX_VALUE + "out").equals(name))     return "" + this.steam.getFill();
        return null;
    }
}
