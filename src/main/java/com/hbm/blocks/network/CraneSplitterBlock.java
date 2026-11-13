package com.hbm.blocks.network;

import api.hbm.block.IToolable;
import api.hbm.conveyor.IConveyorBelt;
import api.hbm.conveyor.IConveyorItem;
import api.hbm.conveyor.IConveyorPackage;
import api.hbm.conveyor.IEnterableBlock;
import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.network.CraneSplitterBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.ILookOverlay;
import com.hbm.blocks.ITooltipProvider;
import com.hbm.entity.NtmEntityTypes;
import com.hbm.entity.item.MovingItem;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.RenderShape;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.api.distmarker.OnlyIn;
import net.neoforged.neoforge.client.event.RenderGuiEvent;

import javax.annotation.Nullable;
import java.util.List;

/**
 * Original CraneSplitter: a two-block belt that splits the items entering it by a ratio onto its two lanes. The core is the left
 * block; the second block lies to the core's facing.getCounterClockWise() side (dimensions {0,0,0,0,0,1}, MultiblockHandlerXR.rotate)
 * and its FACING points from the core to it. Both blocks are belts that carry items towards the opposite of the core's facing.
 * Only the core has a block entity; the second block has none (no proxy: the original splitter has no inventory to forward).
 */
public class CraneSplitterBlock extends DummyableBlock implements IConveyorBelt, IEnterableBlock, ITooltipProvider, IToolable, ILookOverlay {

    public static final MapCodec<CraneSplitterBlock> CODEC = simpleCodec(CraneSplitterBlock::new);

    public CraneSplitterBlock(Properties properties) {
        super(properties);
    }

    @Override
    public MapCodec<CraneSplitterBlock> codec() {
        return CODEC;
    }

    /** Original :58-65. */
    @Override public int[] getDimensions() { return new int[] { 0, 0, 0, 0, 0, 1 }; }
    @Override public int getOffset() { return 0; }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return isCore(state) ? new CraneSplitterBlockEntity(pos, state) : null;
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        if(level.isClientSide || !isCore(state)) return null;
        return (lvl, pos, st, be) -> {
            if(be instanceof ITickable tickable) tickable.updateEntity();
        };
    }

    /** The shape is a baked OBJ model (ConveyorObjBakedModel), not a block entity renderer. */
    @Override
    protected RenderShape getRenderShape(BlockState state) {
        return RenderShape.MODEL;
    }

    /**
     * Original getTravelDirection (:152-156): the side items come from, the core's facing; the second block turns its own facing
     * clockwise, which gives the core's facing again.
     */
    public Direction getTravelDirection(BlockState state) {
        Direction facing = state.getValue(FACING);
        return isCore(state) ? facing : facing.getClockWise();
    }

    /** Original :91: items only enter through the input side, never after a diagonal step. */
    @Override
    public boolean canItemEnter(Level level, BlockPos pos, @Nullable Direction dir, IConveyorItem entity) {
        BlockState state = level.getBlockState(pos);
        return dir != null && state.getBlock() == this && this.getTravelDirection(state) == dir;
    }

    /** Original :92-93: packages do not enter and travel over it like over a plain belt. */
    @Override
    public boolean canPackageEnter(Level level, BlockPos pos, @Nullable Direction dir, IConveyorPackage entity) {
        return false;
    }

    @Override
    public void onPackageEnter(Level level, BlockPos pos, @Nullable Direction dir, IConveyorPackage entity) { }

    /**
     * Original :95-121: the stack entering either block is split by the core's ratio; the left part continues on the core's lane,
     * the right part on the second block's, each snapped to its block's centre line.
     */
    @Override
    public void onItemEnter(Level level, BlockPos pos, @Nullable Direction dir, IConveyorItem entity) {
        if(entity == null) return;

        BlockPos core = this.findCore(level, pos);
        if(core == null || !(level.getBlockEntity(core) instanceof CraneSplitterBlockEntity splitter)) return;

        ItemStack stack = entity.getItemStack().copy();
        if(stack.isEmpty()) return;

        Direction side = level.getBlockState(core).getValue(FACING).getCounterClockWise();
        ItemStack[] splits = splitter.splitStack(stack);

        this.spawnMovingItem(level, core, splits[0]);
        this.spawnMovingItem(level, core.relative(side), splits[1]);
    }

    private void spawnMovingItem(Level level, BlockPos pos, ItemStack stack) {
        if(stack.isEmpty()) return;

        Vec3 snap = this.getClosestSnappingPosition(level, pos, Vec3.atCenterOf(pos));
        MovingItem moving = new MovingItem(NtmEntityTypes.MOVING_ITEM.get(), level);
        moving.moveTo(snap.x, snap.y, snap.z, 0, 0);
        moving.setItemStack(stack);
        level.addFreshEntity(moving);
    }

    @Override
    public boolean canItemStay(Level level, BlockPos pos, Vec3 itemPos) {
        return true;
    }

    /** Original :128-137, the plain belt's movement. */
    @Override
    public Vec3 getTravelLocation(Level level, BlockPos pos, Vec3 itemPos, double speed) {
        Direction dir = this.travelDirectionAt(level, pos);
        Vec3 snap = this.getClosestSnappingPosition(level, pos, itemPos);
        Vec3 dest = new Vec3(snap.x - dir.getStepX() * speed, snap.y - dir.getStepY() * speed, snap.z - dir.getStepZ() * speed);
        Vec3 motion = dest.subtract(itemPos);
        double len = motion.length();
        return new Vec3(itemPos.x + motion.x / len * speed, itemPos.y + motion.y / len * speed, itemPos.z + motion.z / len * speed);
    }

    /** Original :139-150: the centre line along the travel direction, a quarter block above the bottom. */
    @Override
    public Vec3 getClosestSnappingPosition(Level level, BlockPos pos, Vec3 itemPos) {
        Direction dir = this.travelDirectionAt(level, pos);
        double x = pos.getX() + 0.5;
        double z = pos.getZ() + 0.5;
        if(dir.getStepX() != 0) x = Mth.clamp(itemPos.x, pos.getX(), pos.getX() + 1);
        if(dir.getStepZ() != 0) z = Mth.clamp(itemPos.z, pos.getZ(), pos.getZ() + 1);
        return new Vec3(x, pos.getY() + 0.25, z);
    }

    private Direction travelDirectionAt(Level level, BlockPos pos) {
        BlockState state = level.getBlockState(pos);
        return state.getBlock() == this ? this.getTravelDirection(state) : Direction.NORTH;
    }

    /**
     * Original onScrew (:164-187): only the screwdriver; a click raises and a sneak click lowers the ratio of the clicked block's
     * lane, the core's being the left one, kept within 1-16. The original answers true on the client before looking at the tool;
     * NEO checks the tool first, so other tools are not worn. The original does not mark the change for saving; NEO does.
     */
    @Override
    public boolean onScrew(Level level, Player player, BlockPos pos, Direction side, ToolType tool) {
        if(tool != ToolType.SCREWDRIVER) return false;
        if(level.isClientSide) return true;

        BlockPos core = this.findCore(level, pos);
        if(core == null || !(level.getBlockEntity(core) instanceof CraneSplitterBlockEntity splitter)) return false;

        int adjust = player.isShiftKeyDown() ? -1 : 1;

        if(core.equals(pos)) {
            splitter.leftRatio = Mth.clamp(splitter.leftRatio + adjust, 1, 16);
        } else {
            splitter.rightRatio = Mth.clamp(splitter.rightRatio + adjust, 1, 16);
        }

        splitter.setChanged();
        return true;
    }

    /** Original printHook (:189-203), its hardcoded English now a language key. */
    @Override
    @OnlyIn(Dist.CLIENT)
    public void printHook(RenderGuiEvent.Pre event, Level level, BlockPos pos) {
        BlockPos core = this.findCore(level, pos);
        if(core == null || !(level.getBlockEntity(core) instanceof CraneSplitterBlockEntity splitter)) return;

        List<Component> text = List.of(Component.translatable("block.hbmsntm.crane_splitter.ratio", splitter.leftRatio, splitter.rightRatio));
        ILookOverlay.printGeneric(event, Component.translatable(this.getDescriptionId()), 0xffff00, 0x404000, text);
    }

    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> tooltip, TooltipFlag flag) {
        this.addStandardInfo(tooltip);
    }
}
