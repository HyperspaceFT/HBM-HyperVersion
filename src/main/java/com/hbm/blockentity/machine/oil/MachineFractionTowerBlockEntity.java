package com.hbm.blockentity.machine.oil;

import api.hbm.fluidmk2.IFluidStandardTransceiverMK2;
import com.hbm.blockentity.IFluidCopiable;
import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.LoadedBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.recipes.FractionRecipes;
import com.hbm.util.Tuple.Pair;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;

public class MachineFractionTowerBlockEntity extends LoadedBaseBlockEntity implements ITickable, IFluidStandardTransceiverMK2, IFluidCopiable {

    public final FluidTank[] tanks = {
            new FluidTank(Fluids.HEAVYOIL, 4_000),
            new FluidTank(Fluids.BITUMEN, 4_000),
            new FluidTank(Fluids.SMEAR, 4_000)
    };

    public MachineFractionTowerBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.MACHINE_FRACTION_TOWER.get(), pos, state);
    }

    @Override
    public void updateEntity() {
        if(this.level == null || this.level.isClientSide) return;

        // NEO keeps the old network model; the four positions match the original flare ports.
        for(DirPos pos : this.getConPos()) this.trySubscribe(this.tanks[0].getTankType(), this.level, pos);

        // Each segment pushes input up and pulls products down before setting outputs or processing.
        if(this.level.getBlockEntity(this.worldPosition.above(3)) instanceof MachineFractionTowerBlockEntity upper) {
            for(int i = 0; i < this.tanks.length; i++) upper.setTankType(i, this.tanks[i].getTankType());
            this.moveFluid(this.tanks[0], upper.tanks[0], upper);
            this.moveFluid(upper.tanks[1], this.tanks[1], upper);
            this.moveFluid(upper.tanks[2], this.tanks[2], upper);
        }

        this.setupTanks();
        if(this.level.getGameTime() % 10 == 0 && this.fractionate()) this.setChanged();

        for(DirPos pos : this.getConPos()) {
            for(int i = 1; i < this.tanks.length; i++) {
                if(this.tanks[i].getFill() > 0) this.tryProvide(this.tanks[i], this.level, pos);
            }
        }
        this.networkPackNT(50);
    }

    private void moveFluid(FluidTank source, FluidTank target, MachineFractionTowerBlockEntity upper) {
        int amount = Math.min(source.getFill(), target.getMaxFill() - target.getFill());
        if(amount <= 0) return;
        source.setFill(source.getFill() - amount);
        target.setFill(target.getFill() + amount);
        this.setChanged();
        upper.setChanged();
    }

    private void setTankType(int index, FluidType type) {
        if(this.tanks[index].getTankType() == type) return;
        // setTankType clears the amount, but deliberately preserves pressure, as upstream.
        this.tanks[index].setTankType(type);
        this.setChanged();
    }

    private void setupTanks() {
        Pair<FluidStack, FluidStack> recipe = FractionRecipes.getFractions(this.tanks[0].getTankType());
        if(recipe != null) {
            this.setTankType(1, recipe.getKey().type);
            this.setTankType(2, recipe.getValue().type);
        } else {
            for(int i = 0; i < this.tanks.length; i++) this.setTankType(i, Fluids.NONE);
        }
    }

    private boolean fractionate() {
        Pair<FluidStack, FluidStack> recipe = FractionRecipes.getFractions(this.tanks[0].getTankType());
        if(recipe == null) return false;
        int left = recipe.getKey().fill;
        int right = recipe.getValue().fill;
        // Invalid quantities must not turn a custom recipe into a fluid source or bypass capacity by overflow.
        if(left < 0 || right < 0 || this.tanks[0].getFill() < 100
                || (long) this.tanks[1].getFill() + left > this.tanks[1].getMaxFill()
                || (long) this.tanks[2].getFill() + right > this.tanks[2].getMaxFill()) return false;
        this.tanks[0].setFill(this.tanks[0].getFill() - 100);
        this.tanks[1].setFill(this.tanks[1].getFill() + left);
        this.tanks[2].setFill(this.tanks[2].getFill() + right);
        return true;
    }

    /** The shared server gate also covers block-level copy forwarding, not just identifiers. */
    public boolean changeInputType(FluidType type, Player player) {
        if(this.level == null || this.level.isClientSide) return false;
        if(this.level.getBlockEntity(this.worldPosition.below(3)) instanceof MachineFractionTowerBlockEntity) {
            player.displayClientMessage(Component.translatable("block.hbmsntm.machine_fraction_tower.bottom_only").withStyle(ChatFormatting.RED), false);
            return false;
        }
        this.setTankType(0, type == null ? Fluids.NONE : type);
        player.displayClientMessage(Component.translatable("block.hbmsntm.machine_fraction_tower.changed_type_to", this.tanks[0].getTankType().getName()).withStyle(ChatFormatting.YELLOW), false);
        return true;
    }

    public static DirPos[] getPortProxies(BlockPos core) {
        return new DirPos[] {
                new DirPos(core.north(), Direction.NORTH), new DirPos(core.east(), Direction.EAST),
                new DirPos(core.south(), Direction.SOUTH), new DirPos(core.west(), Direction.WEST)
        };
    }

    public DirPos[] getConPos() {
        DirPos[] proxies = getPortProxies(this.worldPosition);
        DirPos[] positions = new DirPos[proxies.length];
        for(int i = 0; i < proxies.length; i++) positions[i] = new DirPos(proxies[i].makeCompat().relative(proxies[i].getDir()), proxies[i].getDir());
        return positions;
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        for(int i = 0; i < this.tanks.length; i++) this.tanks[i].readFromNBT(tag, "tank" + i);
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        for(int i = 0; i < this.tanks.length; i++) this.tanks[i].writeToNBT(tag, "tank" + i);
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        for(FluidTank tank : this.tanks) tank.serialize(buf);
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        for(FluidTank tank : this.tanks) tank.deserialize(buf);
    }

    public AABB getRenderBoundingBox() {
        return new AABB(this.worldPosition.getX() - 1, this.worldPosition.getY(), this.worldPosition.getZ() - 1,
                this.worldPosition.getX() + 2, this.worldPosition.getY() + 3, this.worldPosition.getZ() + 2);
    }

    @Override public FluidTank[] getSendingTanks() { return new FluidTank[] {this.tanks[1], this.tanks[2]}; }
    @Override public FluidTank[] getReceivingTanks() { return new FluidTank[] {this.tanks[0]}; }
    @Override public FluidTank[] getAllTanks() { return this.tanks; }

    @Override
    public long transferFluid(FluidType type, int pressure, long amount) {
        long remainder = IFluidStandardTransceiverMK2.super.transferFluid(type, pressure, amount);
        if(remainder < amount) this.setChanged();
        return remainder;
    }

    @Override
    public void useUpFluid(FluidType type, int pressure, long amount) {
        long previous = this.getFluidAvailable(type, pressure);
        IFluidStandardTransceiverMK2.super.useUpFluid(type, pressure, amount);
        if(this.getFluidAvailable(type, pressure) != previous) this.setChanged();
    }

    @Override public FluidTank getTankToPaste() { return this.tanks[0]; }

    @Override
    public void pasteSettings(CompoundTag tag, int index, Level level, Player player, BlockPos pos) {
        if(level != this.level || !this.worldPosition.equals(pos)) return;
        int[] ids = tag.getIntArray("FluidID");
        if(index >= 0 && index < ids.length) this.changeInputType(Fluids.fromID(ids[index]), player);
    }
}
