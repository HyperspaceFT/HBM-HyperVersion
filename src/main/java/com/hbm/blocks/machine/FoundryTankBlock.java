package com.hbm.blocks.machine;

import api.hbm.block.ICrucibleAcceptor;
import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.machine.FoundryTankBlockEntity;
import com.hbm.inventory.material.Mats;
import com.hbm.items.CopperScrapsItem;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.tags.ItemTags;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.ItemInteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.BaseEntityBlock;
import net.minecraft.world.level.block.RenderShape;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraft.world.phys.shapes.Shapes;
import net.minecraft.world.phys.shapes.VoxelShape;

/** Upstream FoundryTank (foundry storage basin): takes pours from above, refuses flows. Full-cube collision like upstream. */
public class FoundryTankBlock extends BaseEntityBlock implements ICrucibleAcceptor {
    public static final MapCodec<FoundryTankBlock> CODEC = simpleCodec(FoundryTankBlock::new);
    /** Upstream isSideSolid is true for every side but UP; a support shape that is open at the top gives the same face sturdiness. */
    private static final VoxelShape SUPPORT_SHAPE = Shapes.or(box(0, 0, 0, 16, 2, 16),
            box(0, 0, 0, 16, 16, 2), box(0, 0, 14, 16, 16, 16),
            box(0, 0, 2, 2, 16, 14), box(14, 0, 2, 16, 16, 14));

    public FoundryTankBlock(Properties properties) { super(properties); }
    @Override public MapCodec<FoundryTankBlock> codec() { return CODEC; }
    @Override public BlockEntity newBlockEntity(BlockPos pos, BlockState state) { return new FoundryTankBlockEntity(pos, state); }
    @Override protected RenderShape getRenderShape(BlockState state) { return RenderShape.MODEL; }
    @Override protected VoxelShape getBlockSupportShape(BlockState state, BlockGetter level, BlockPos pos) { return SUPPORT_SHAPE; }
    @Override public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    @Override
    protected ItemInteractionResult useItemOn(ItemStack stack, BlockState state, Level level, BlockPos pos, Player player, InteractionHand hand, BlockHitResult hit) {
        // upstream consumes any shovel click, also on an empty tank
        if(!stack.is(ItemTags.SHOVELS)) return ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;
        if(!level.isClientSide && level.getBlockEntity(pos) instanceof FoundryTankBlockEntity tank && tank.amount > 0) {
            ItemStack scrap = CopperScrapsItem.create(tank.takeContents());
            if(!scrap.isEmpty() && !player.getInventory().add(scrap)) player.drop(scrap, false);
        }
        return ItemInteractionResult.sidedSuccess(level.isClientSide);
    }

    @Override
    public void onRemove(BlockState state, Level level, BlockPos pos, BlockState newState, boolean moving) {
        if(!state.is(newState.getBlock()) && !level.isClientSide
                && level.getBlockEntity(pos) instanceof FoundryTankBlockEntity tank && tank.amount > 0) {
            popResource(level, pos, CopperScrapsItem.create(tank.takeContents()));
        }
        super.onRemove(state, level, pos, newState, moving);
    }

    @Override
    public boolean canAcceptPartialPour(Level level, BlockPos pos, Vec3 hit, Direction side, Mats.MaterialStack stack) {
        return level.getBlockEntity(pos) instanceof ICrucibleAcceptor acc && acc.canAcceptPartialPour(level, pos, hit, side, stack);
    }

    @Override
    public Mats.MaterialStack pour(Level level, BlockPos pos, Vec3 hit, Direction side, Mats.MaterialStack stack) {
        return level.getBlockEntity(pos) instanceof ICrucibleAcceptor acc ? acc.pour(level, pos, hit, side, stack) : stack;
    }

    @Override public boolean canAcceptPartialFlow(Level level, BlockPos pos, Direction side, Mats.MaterialStack stack) { return false; }
    @Override public Mats.MaterialStack flow(Level level, BlockPos pos, Direction side, Mats.MaterialStack stack) { return stack; }
}
