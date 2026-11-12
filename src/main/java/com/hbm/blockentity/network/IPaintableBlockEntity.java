package com.hbm.blockentity.network;

import net.minecraft.core.BlockPos;
import net.minecraft.core.HolderGetter;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.registries.Registries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtUtils;
import net.minecraft.world.level.EmptyBlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.RenderShape;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.neoforged.neoforge.client.model.data.ModelData;
import net.neoforged.neoforge.client.model.data.ModelProperty;

/**
 * A cable or duct painted with another block (original BlockCablePaintable, FluidDuctPaintable). The original stores the paint
 * as a numeric block ID and metadata ("block", "meta"); NEO stores the paint block state under "paint". The client model draws
 * the paint through {@link #PAINT}.
 */
public interface IPaintableBlockEntity {

    ModelProperty<BlockState> PAINT = new ModelProperty<>();
    String PAINT_KEY = "paint";

    BlockState getPaint();

    void setPaint(BlockState paint);

    /** Original BlockCablePaintable.allowedPaint: an ordinary full cube other than grass and the paintable block itself. */
    static boolean allowedPaint(BlockState paint, Block self) {
        if(paint.is(Blocks.GRASS_BLOCK) || paint.is(self)) return false;
        return paint.getRenderShape() == RenderShape.MODEL && !paint.hasBlockEntity() && paint.isSolidRender(EmptyBlockGetter.INSTANCE, BlockPos.ZERO);
    }

    static void savePaint(BlockState paint, CompoundTag tag) {
        if(paint != null) tag.put(PAINT_KEY, NbtUtils.writeBlockState(paint));
    }

    static BlockState loadPaint(CompoundTag tag, HolderLookup.Provider registries) {
        if(!tag.contains(PAINT_KEY)) return null;
        return readPaint(registries.lookupOrThrow(Registries.BLOCK), tag.getCompound(PAINT_KEY));
    }

    /** An unknown block reads as air, which means no paint. */
    static BlockState readPaint(HolderGetter<Block> blocks, CompoundTag tag) {
        BlockState paint = NbtUtils.readBlockState(blocks, tag);
        return paint.isAir() ? null : paint;
    }

    static ModelData modelData(BlockState paint) {
        return paint == null ? ModelData.EMPTY : ModelData.builder().with(PAINT, paint).build();
    }

    /** Saves the change and sends the block entity to clients, which rebuild the chunk mesh with the new paint. */
    static void paintChanged(BlockEntity be) {
        Level level = be.getLevel();
        be.setChanged();
        if(level != null) level.sendBlockUpdated(be.getBlockPos(), be.getBlockState(), be.getBlockState(), Block.UPDATE_CLIENTS);
    }

    /** Client side of {@link #paintChanged}: refresh the model data and re-render the block. */
    static void paintReceived(BlockEntity be) {
        Level level = be.getLevel();
        be.requestModelDataUpdate();
        if(level != null && level.isClientSide) level.sendBlockUpdated(be.getBlockPos(), be.getBlockState(), be.getBlockState(), Block.UPDATE_ALL_IMMEDIATE);
    }
}
