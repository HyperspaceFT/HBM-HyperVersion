package com.hbm.blockentity.machine.rbmk;

import api.hbm.fluidmk2.FluidNetMK2;
import api.hbm.fluidmk2.FluidNode;
import api.hbm.fluidmk2.IFluidStandardTransceiverMK2;
import api.hbm.redstoneoverradio.IRORValueProvider;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.entity.projectile.RBMKDebris.DebrisType;
import com.hbm.interfaces.IControlReceiver;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.menus.RBMKBoilerMenu;
import com.hbm.network.toclient.AuxParticle;
import com.hbm.registry.NtmSoundEvents;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.network.PacketDistributor;

import java.util.Set;

/**
 * Original TileEntityRBMKBoiler: the steam channel, which turns feedwater into steam of the selected grade with the column's heat
 * and has no slots (the original SlottedBase(0)). The tanks are filled and drained through the column's ports
 * (RBMKBaseBlockEntity.getPortConnections). The OpenComputers callbacks and the Energy Control data (provideExtraInfo) are not
 * ported (GOAL24 decision 6).
 */
public class RBMKBoilerBlockEntity extends RBMKSlottedBaseBlockEntity implements IControlReceiver, IFluidStandardTransceiverMK2, IRORValueProvider {

    public FluidTank feed = new FluidTank(Fluids.WATER, 10000);
    public FluidTank steam = new FluidTank(Fluids.STEAM, 1000000);
    // Not saved, as the original.
    protected int consumption;
    protected int output;
    protected int ventDelay;

    public RBMKBoilerBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.RBMK_BOILER.get(), pos, state, 0);
    }

    @Override
    public String getContainerName() {
        return "container.rbmkBoiler";
    }

    /** Original updateEntity (:66-125). The ticker runs on both sides; everything here is server side. */
    @Override
    public void updateEntity() {
        Level world = this.getLevel();

        if(world != null && !world.isClientSide) {

            // The original's port nodes subscribe and provide once per network change and stay registered; NEO's networks drop
            // entries after a timeout, so both are renewed every tick (an empty steam tank offers nothing).
            for(DirPos con : this.getPortConnections()) {
                this.trySubscribe(feed.getTankType(), world, con);
                this.tryProvide(steam, world, con);
            }

            this.consumption = 0;
            this.output = 0;
            if(this.ventDelay > 0) this.ventDelay--;

            double heatCap = getHeatFromSteam(steam.getTankType());
            double heatProvided = this.heat - heatCap;

            if(heatProvided > 0) {
                double HEAT_PER_MB_WATER = RBMKDials.getBoilerHeatConsumption();
                double steamFactor = getFactorFromSteam(steam.getTankType());
                int waterUsed;
                int steamProduced;

                if(steam.getTankType() == Fluids.ULTRAHOTSTEAM) {
                    steamProduced = (int)Math.floor((heatProvided / HEAT_PER_MB_WATER) * 100D / steamFactor);
                    waterUsed = (int)Math.floor(steamProduced / 100D * steamFactor);

                    if(feed.getFill() < waterUsed) {
                        steamProduced = (int)Math.floor(feed.getFill() * 100D / steamFactor);
                        waterUsed = (int)Math.floor(steamProduced / 100D * steamFactor);
                    }
                } else {
                    waterUsed = (int)Math.floor(heatProvided / HEAT_PER_MB_WATER);
                    waterUsed = Math.min(waterUsed, feed.getFill());
                    steamProduced = (int)Math.floor((waterUsed * 100D) / steamFactor);
                }

                this.consumption = waterUsed;
                this.output = steamProduced;

                feed.setFill(feed.getFill() - waterUsed);
                steam.setFill(steam.getFill() + steamProduced);

                if(steam.getFill() > steam.getMaxFill()) {
                    steam.setFill(steam.getMaxFill());

                    if(ventDelay <= 0) {
                        BlockPos pos = this.getBlockPos();
                        int h = RBMKDials.getColumnHeight();
                        CompoundTag data = new CompoundTag();
                        data.putString("type", "rbmksteam");
                        double px = pos.getX() + 0.25 + world.random.nextInt(2) * 0.5;
                        double pz = pos.getZ() + 0.25 + world.random.nextInt(2) * 0.5;
                        if(world instanceof ServerLevel serverLevel) {
                            PacketDistributor.sendToPlayersNear(serverLevel, null, pos.getX() + 0.5, pos.getY() + 1, pos.getZ() + 0.5, 100, new AuxParticle(data, px, pos.getY() + h, pz));
                        }
                        this.ventDelay = 20 + world.random.nextInt(10);
                        world.playSound(null, pos.getX(), pos.getY() + h, pos.getZ(), NtmSoundEvents.STEAM_ENGINE_OPERATE.get(), SoundSource.BLOCKS, 2F, 1F + world.random.nextFloat() * 0.25F);
                    }
                }

                this.heat -= waterUsed * HEAT_PER_MB_WATER;

                if(waterUsed != 0 || steamProduced != 0) this.setChanged();
            }
        }

        super.updateEntity();
    }

    public static double getHeatFromSteam(FluidType type) {
        if(type == Fluids.STEAM) return 100D;
        if(type == Fluids.HOTSTEAM) return 300D;
        if(type == Fluids.SUPERHOTSTEAM) return 450D;
        if(type == Fluids.ULTRAHOTSTEAM) return 600D;
        return 0D;
    }

    public static double getFactorFromSteam(FluidType type) {
        if(type == Fluids.STEAM) return 1D;
        if(type == Fluids.HOTSTEAM) return 10D;
        if(type == Fluids.SUPERHOTSTEAM) return 100D;
        if(type == Fluids.ULTRAHOTSTEAM) return 1000D;
        return 0D;
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
        steam.serialize(buf);
        feed.serialize(buf);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        this.steam.deserialize(buf);
        this.feed.deserialize(buf);
    }

    // Measured from the block corner, as the original (:173-176).
    @Override
    public boolean hasPermission(Player player) {
        BlockPos pos = this.getBlockPos();
        return new Vec3(pos.getX() - player.getX(), pos.getY() - player.getY(), pos.getZ() - player.getZ()).length() < 20;
    }

    /** Original receiveControl (:178-184); server side. */
    @Override
    public void receiveControl(CompoundTag data) {

        if(data.contains("compression")) {
            this.cyceCompressor();
        }
    }

    /**
     * Original cyceCompressor (:186-197), name kept (GOAL24 decision 18): steps the steam grade, only while the column is cold or
     * dry. Upstream-shared: setTankType empties the tank whenever the type changes (FluidTank.setTankType, the same in the
     * original), so the fill / 10 and fill * 1000 below never take effect and a step always leaves the steam tank empty.
     */
    public void cyceCompressor() {

        if(this.heat > 50 && this.feed.getFill() > 0) return;

        FluidType type = steam.getTankType();
        if(type == Fluids.STEAM) {          steam.setTankType(Fluids.HOTSTEAM);         steam.setFill(steam.getFill() / 10); }
        if(type == Fluids.HOTSTEAM) {       steam.setTankType(Fluids.SUPERHOTSTEAM);    steam.setFill(steam.getFill() / 10); }
        if(type == Fluids.SUPERHOTSTEAM) {  steam.setTankType(Fluids.ULTRAHOTSTEAM);    steam.setFill(steam.getFill() / 10); }
        if(type == Fluids.ULTRAHOTSTEAM) {  steam.setTankType(Fluids.STEAM);            steam.setFill(Math.min(steam.getFill() * 1000, steam.getMaxFill())); }

        this.setChanged();
    }

    @Override
    public void onMelt(int reduce) {

        int count = 1 + getLevel().random.nextInt(2);

        for(int i = 0; i < count; i++) {
            spawnDebris(DebrisType.BLANK);
        }

        super.onMelt(reduce);
    }

    /** Original onMelt (:208-215): the steam networks at the port connections. */
    @Override
    protected void collectOverpressurePipes(Set<FluidNetMK2> pipes) {
        Level world = this.getLevel();

        for(DirPos con : this.getPortConnections()) {
            if(UniNodespace.getNode(world, con.makeCompat(), steam.getTankType().getNetworkProvider()) instanceof FluidNode node && node.hasValidNet()) {
                pipes.add(node.net);
            }
        }
    }

    @Override
    public RBMKColumnType getConsoleType() {
        return RBMKColumnType.BOILER;
    }

    /** Original :225-234 builds a compound with these keys only; NEO adds them to the base heat/maxHeat (24C convention). */
    @Override
    public CompoundTag getNBTForConsole() {
        CompoundTag data = super.getNBTForConsole();
        data.putInt("water", this.feed.getFill());
        data.putInt("maxWater", this.feed.getMaxFill());
        data.putInt("steam", this.steam.getFill());
        data.putInt("maxSteam", this.steam.getMaxFill());
        data.putShort("type", (short)this.steam.getTankType().getID());
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
        return new RBMKBoilerMenu(containerId, inventory, this);
    }

    @Override
    public String[] getFunctionInfo() {
        return new String[] {
                PREFIX_VALUE + "feed",
                PREFIX_VALUE + "steam",
                PREFIX_VALUE + "consumption"
        };
    }

    @Override
    public String provideRORValue(String name) {
        if((PREFIX_VALUE + "feed").equals(name))        return "" + this.feed.getFill();
        if((PREFIX_VALUE + "steam").equals(name))       return "" + this.steam.getFill();
        if((PREFIX_VALUE + "consumption").equals(name)) return "" + this.consumption;
        return null;
    }
}
