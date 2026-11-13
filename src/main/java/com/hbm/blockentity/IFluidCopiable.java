package com.hbm.blockentity;

import api.hbm.fluidmk2.IFluidStandardTransceiverMK2;
import api.hbm.fluidmk2.IFluidUserMK2;
import com.hbm.interfaces.ICopiable;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.util.BobMathUtil;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;

import java.util.ArrayList;


public interface IFluidCopiable extends ICopiable {
    /**
     * @return First type for the normal paste, second type for the alt paste,
     *         none if there is no alt paste support
     */
    default int[] getFluidIDToCopy() {
        IFluidUserMK2 be = (IFluidUserMK2) this;
        ArrayList<Integer> types = new ArrayList<>();

        for (FluidTank tank : be.getAllTanks()) {
            if (!tank.getTankType().hasNoID()) types.add(tank.getTankType().getID());
        }

        return BobMathUtil.intCollectionToArray(types);
    }

    default FluidTank getTankToPaste() {
        BlockEntity be = (BlockEntity) this;
        if (be instanceof IFluidStandardTransceiverMK2 fst) { // why are we using the transceiver here?
            return fst.getReceivingTanks() != null ? fst.getReceivingTanks()[0] : null;
        }
        return null;
    }

    @Override
    default CompoundTag getSettings(Level level, BlockPos pos) {
        CompoundTag tag = new CompoundTag();
        if (getFluidIDToCopy().length > 0) tag.putIntArray("FluidID", getFluidIDToCopy());
        return tag;
    }

    /**
     * Original IFluidCopiable.pasteSettings: the copied fluid of the chosen entry becomes the paste tank's type. The settings tool's
     * data is player-writable, so NEO pastes on the server only, ignores a negative entry (the original only bounds it from above)
     * and an id no fluid has (which the original turns into "none", emptying the tank), and marks the change for saving.
     */
    @Override
    default void pasteSettings(CompoundTag tag, int index, Level level, Player player, BlockPos pos) {
        if (level.isClientSide) return;

        FluidTank tank = getTankToPaste();
        if (tank != null) {
            int[] ids = tag.getIntArray("FluidID");
            if (index >= 0 && index < ids.length) {
                int id = ids[index];
                FluidType type = Fluids.fromID(id);
                if (type == Fluids.NONE && id != Fluids.NONE.getID()) return;
                if (type != tank.getTankType()) {
                    tank.setTankType(type);
                    ((BlockEntity) this).setChanged();
                }
            }
        }
    }

    @Override
    default String[] infoForDisplay(Level level, BlockPos pos) {
        int[] ids = getFluidIDToCopy();
        String[] names = new String[ids.length];
        for (int i = 0; i < ids.length; i++) {
            names[i] = Fluids.fromID(ids[i]).getUnlocalizedName();
        }
        return names;
    }
}
