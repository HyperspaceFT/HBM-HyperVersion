package com.hbm.blockentity.machine.oil;

import api.hbm.fluidmk2.IFluidStandardTransceiverMK2;
import com.hbm.blockentity.IFluidCopiable;
import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.LoadedBaseBlockEntity;
import com.hbm.blockentity.NtmBlockEntityTypes;
import com.hbm.blocks.DummyableBlock;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.recipes.CrackingRecipes;
import com.hbm.util.Tuple.Pair;
import com.hbm.util.fauxpointtwelve.DirPos;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;

public class MachineCatalyticCrackerBlockEntity extends LoadedBaseBlockEntity implements ITickable, IFluidStandardTransceiverMK2, IFluidCopiable {

    public final FluidTank[] tanks;

    private AABB renderBox;

    public MachineCatalyticCrackerBlockEntity(BlockPos pos, BlockState state) {
        super(NtmBlockEntityTypes.MACHINE_CATALYTIC_CRACKER.get(), pos, state);

        this.tanks = new FluidTank[] {
                new FluidTank(Fluids.BITUMEN, 4_000),
                new FluidTank(Fluids.STEAM, 8_000),
                new FluidTank(Fluids.OIL, 4_000),
                new FluidTank(Fluids.PETROLEUM, 4_000),
                new FluidTank(Fluids.SPENTSTEAM, 800)
        };
    }

    @Override
    public void updateEntity() {
        if(this.level == null || this.level.isClientSide) return;

        DirPos[] conPos = this.getConPos();

        // The original connects through TilePort nodes; NEO keeps the subscribe/provide model, as its refinery does.
        for(DirPos pos : conPos) {
            this.trySubscribe(this.tanks[0].getTankType(), this.level, pos);
            this.trySubscribe(this.tanks[1].getTankType(), this.level, pos);
        }

        this.setupTanks();

        if(this.level.getGameTime() % 5 == 0 && this.crack()) {
            this.setChanged();
        }

        for(DirPos pos : conPos) {
            for(int i = 2; i < this.tanks.length; i++) {
                if(this.tanks[i].getFill() > 0) {
                    this.tryProvide(this.tanks[i], this.level, pos);
                }
            }
        }

        this.networkPackNT(25);
    }

    /** Up to two runs, each turning 100 mB of oil and 200 mB of steam into the recipe outputs plus 2 mB of spent steam. */
    private boolean crack() {
        Pair<FluidStack, FluidStack> quart = CrackingRecipes.getCracking(this.tanks[0].getTankType());
        if(quart == null) return false;

        int left = quart.getKey().fill;
        int right = quart.getValue().fill;
        boolean cracked = false;

        for(int i = 0; i < 2; i++) {
            if(this.tanks[0].getFill() >= 100 && this.tanks[1].getFill() >= 200 && this.hasSpace(left, right)) {
                this.tanks[0].setFill(this.tanks[0].getFill() - 100);
                this.tanks[1].setFill(this.tanks[1].getFill() - 200);
                this.tanks[2].setFill(this.tanks[2].getFill() + left);
                this.tanks[3].setFill(this.tanks[3].getFill() + right);
                this.tanks[4].setFill(this.tanks[4].getFill() + 2); //LPS has the density of WATER not STEAM (1%!)
                cracked = true;
            }
        }

        return cracked;
    }

    private boolean hasSpace(int left, int right) {
        return this.tanks[2].getFill() + left <= this.tanks[2].getMaxFill() && this.tanks[3].getFill() + right <= this.tanks[3].getMaxFill() && this.tanks[4].getFill() + 2 <= this.tanks[4].getMaxFill();
    }

    /** Output tanks follow the input type; an input without a recipe switches them to NONE, as the original. */
    private void setupTanks() {
        Pair<FluidStack, FluidStack> quart = CrackingRecipes.getCracking(this.tanks[0].getTankType());

        if(quart != null) {
            this.setTankType(1, Fluids.STEAM);
            this.setTankType(2, quart.getKey().type);
            this.setTankType(3, quart.getValue().type);
            this.setTankType(4, Fluids.SPENTSTEAM);
        } else {
            this.setTankType(2, Fluids.NONE);
            this.setTankType(3, Fluids.NONE);
            this.setTankType(4, Fluids.NONE);
        }
    }

    private void setTankType(int index, FluidType type) {
        if(this.tanks[index].getTankType() == type) return;
        this.tanks[index].setTankType(type);
        this.setChanged();
    }

    /**
     * The eight fluid proxies on the core layer, each paired with the side its port faces, as the original
     * TileEntityMachineCatalyticCracker.getPorts. MachineCatalyticCrackerBlock places its extras from this list
     * so the proxies and the connections cannot drift apart.
     */
    public static DirPos[] getPortProxies(BlockPos core, Direction dir) {
        Direction rot = dir.getClockWise(); // the original's getRotation(UP)

        return new DirPos[] {
                new DirPos(core.relative(dir, 3).relative(rot, 1), dir),
                new DirPos(core.relative(dir, 3).relative(rot, -2), dir),
                new DirPos(core.relative(dir, -3).relative(rot, 1), dir.getOpposite()),
                new DirPos(core.relative(dir, -3).relative(rot, -2), dir.getOpposite()),
                new DirPos(core.relative(dir, 2).relative(rot, 2), rot),
                new DirPos(core.relative(dir, 2).relative(rot, -3), rot.getOpposite()),
                new DirPos(core.relative(dir, -2).relative(rot, 2), rot),
                new DirPos(core.relative(dir, -2).relative(rot, -3), rot.getOpposite())
        };
    }

    /** One block outside each proxy in the direction its port faces (original PortDef.make). */
    public DirPos[] getConPos() {
        DirPos[] proxies = getPortProxies(this.worldPosition, this.getBlockState().getValue(DummyableBlock.FACING));
        DirPos[] conPos = new DirPos[proxies.length];

        for(int i = 0; i < proxies.length; i++) {
            Direction side = proxies[i].getDir();
            conPos[i] = new DirPos(proxies[i].makeCompat().relative(side), side);
        }

        return conPos;
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        for(int i = 0; i < this.tanks.length; i++) {
            this.tanks[i].readFromNBT(tag, "tank" + i);
        }
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        for(int i = 0; i < this.tanks.length; i++) {
            this.tanks[i].writeToNBT(tag, "tank" + i);
        }
    }

    @Override
    public void serialize(RegistryFriendlyByteBuf buf) {
        super.serialize(buf);
        for(FluidTank tank : this.tanks) {
            tank.serialize(buf);
        }
    }

    @Override
    public void deserialize(RegistryFriendlyByteBuf buf) {
        super.deserialize(buf);
        for(FluidTank tank : this.tanks) {
            tank.deserialize(buf);
        }
    }

    public AABB getRenderBoundingBox() {
        if(this.renderBox == null) {
            int x = this.worldPosition.getX();
            int y = this.worldPosition.getY();
            int z = this.worldPosition.getZ();
            this.renderBox = new AABB(x - 3, y, z - 3, x + 4, y + 16, z + 4);
        }
        return this.renderBox;
    }

    @Override
    public FluidTank[] getSendingTanks() {
        return new FluidTank[] { this.tanks[2], this.tanks[3], this.tanks[4] };
    }

    @Override
    public FluidTank[] getReceivingTanks() {
        return new FluidTank[] { this.tanks[0], this.tanks[1] };
    }

    @Override
    public FluidTank[] getAllTanks() {
        return this.tanks;
    }

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

    @Override
    public FluidTank getTankToPaste() {
        return this.tanks[0];
    }

    @Override
    public void pasteSettings(CompoundTag tag, int index, Level level, Player player, BlockPos pos) {
        FluidType previous = this.tanks[0].getTankType();
        IFluidCopiable.super.pasteSettings(tag, index, level, player, pos);
        if(this.tanks[0].getTankType() != previous) this.setChanged();
    }
}
