package com.hbm.blockentity.network;

import com.hbm.blockentity.MachineBaseBlockEntity;
import com.hbm.blocks.network.CraneBaseBlock;
import com.hbm.interfaces.IControlReceiver;
import com.hbm.interfaces.IControlReceiverFilter;
import com.hbm.interfaces.ICopiable;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;

/** Original TileEntityCraneBase: the sides come from the block state (CraneBaseBlock), plus copy and paste of orientation and filter. */
public abstract class CraneBaseBlockEntity extends MachineBaseBlockEntity implements IControlReceiver, ICopiable {

    public CraneBaseBlockEntity(BlockEntityType<? extends CraneBaseBlockEntity> type, BlockPos pos, BlockState state, int size) {
        super(type, pos, state, size);
    }

    public Direction getInputSide() {
        return CraneBaseBlock.getInputSide(this.getBlockState());
    }

    public Direction getOutputSide() {
        return CraneBaseBlock.getOutputSide(this.getBlockState());
    }

    /** The cranes' own permission (TileEntityCraneInserter.java:151-153): the player is less than 20 blocks from the block's corner. */
    @Override
    public boolean hasPermission(Player player) {
        if(this.level == null || this.level.getBlockEntity(this.worldPosition) != this) return false;
        return Vec3.atLowerCornerOf(this.worldPosition).distanceTo(player.position()) < 20D;
    }

    /** Original :113-137. */
    @Override
    public CompoundTag getSettings(Level level, BlockPos pos) {
        CompoundTag tag = new CompoundTag();
        tag.putInt("inputSide", this.getInputSide().get3DDataValue());
        tag.putInt("outputSide", this.getOutputSide().get3DDataValue());

        if(this instanceof IControlReceiverFilter filter) {
            tag.put("items", filter.writeFilterItems(level.registryAccess()));
        }

        return tag;
    }

    /**
     * Original :140-176: entry 1 of the display list pastes the orientation, the others the filter. The pasted data comes from an
     * item a player can rewrite, so the orientation is only pasted when both sides are valid directions and differ (GOAL31 decision
     * 4); the filter goes through {@link IControlReceiverFilter#pasteFilterItems}.
     */
    @Override
    public void pasteSettings(CompoundTag tag, int index, Level level, Player player, BlockPos pos) {

        if(index == 1) {
            if(!tag.contains("inputSide", Tag.TAG_ANY_NUMERIC) || !tag.contains("outputSide", Tag.TAG_ANY_NUMERIC)) return;

            int input = tag.getInt("inputSide");
            int output = tag.getInt("outputSide");
            if(input < 0 || input > 5 || output < 0 || output > 5 || input == output) return;

            BlockState state = this.getBlockState();
            if(!(state.getBlock() instanceof CraneBaseBlock)) return;

            level.setBlock(this.worldPosition, state.setValue(CraneBaseBlock.INPUT, Direction.from3DDataValue(input)).setValue(CraneBaseBlock.OUTPUT, Direction.from3DDataValue(output)), 3);
        } else if(this instanceof IControlReceiverFilter filter) {
            filter.pasteFilterItems(tag, level.registryAccess());
        }
    }

    /** Original :179-181. */
    @Override
    public String[] infoForDisplay(Level level, BlockPos pos) {
        return new String[] { "copytool.filter", "copytool.orientation" };
    }
}
