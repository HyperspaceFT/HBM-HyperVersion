package com.hbm.blocks.machine;

import api.hbm.block.ICrucibleAcceptor;
import api.hbm.block.IToolable;
import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.machine.FoundryCastingBlockEntity;
import com.hbm.blocks.ILookOverlay;
import com.hbm.inventory.material.Mats;
import com.hbm.items.machine.MoldItem;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.Component;
import net.minecraft.tags.ItemTags;
import net.minecraft.util.RandomSource;
import net.minecraft.world.Containers;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.ItemInteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.BaseEntityBlock;
import net.minecraft.world.level.block.RenderShape;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.api.distmarker.OnlyIn;
import net.neoforged.neoforge.client.event.RenderGuiEvent;

import java.util.ArrayList;
import java.util.List;

/**
 * Upstream FoundryCastingBase (FoundryCastingBase.java:33-209), shared by foundry_mold and foundry_basin: right-click takes the cast,
 * then inserts a held mold of the right size, a shovel scrapes the material out, a screwdriver removes the empty block's mold.
 * The mold insertion is silent: NEO has no upgradePlug sound.
 */
public abstract class FoundryCastingBlock extends BaseEntityBlock implements IToolable, ILookOverlay, ICrucibleAcceptor {

    protected FoundryCastingBlock(Properties properties) { super(properties); }

    @Override protected RenderShape getRenderShape(BlockState state) { return RenderShape.MODEL; }
    @Override public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    private boolean interact(Level level, BlockPos pos, Player player, ItemStack held) {
        if(!(level.getBlockEntity(pos) instanceof FoundryCastingBlockEntity cast)) return false;
        if(!cast.getItem(1).isEmpty()) {
            if(!level.isClientSide) give(player, cast.removeItem(1, 64));
            return true;
        }
        MoldItem.Mold mold = MoldItem.of(held);
        if(mold != null && mold.size == cast.getMoldSize() && cast.getItem(0).isEmpty() && cast.amount == 0) {
            if(!level.isClientSide) cast.insertMold(held);
            return true;
        }
        if(held.is(ItemTags.SHOVELS)) {
            if(!level.isClientSide) give(player, cast.takeScraps());
            return true;
        }
        return false;
    }

    private static void give(Player player, ItemStack stack) {
        if(!stack.isEmpty() && !player.getInventory().add(stack)) player.drop(stack, false);
    }

    @Override protected ItemInteractionResult useItemOn(ItemStack stack, BlockState state, Level level, BlockPos pos,
            Player player, InteractionHand hand, BlockHitResult hit) {
        return interact(level, pos, player, stack) ? ItemInteractionResult.sidedSuccess(level.isClientSide)
                : ItemInteractionResult.PASS_TO_DEFAULT_BLOCK_INTERACTION;
    }
    @Override protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hit) {
        return interact(level, pos, player, ItemStack.EMPTY) ? InteractionResult.sidedSuccess(level.isClientSide) : InteractionResult.PASS;
    }

    @Override public boolean onScrew(Level level, Player player, BlockPos pos, Direction direction, ToolType tool) {
        if(tool != ToolType.SCREWDRIVER || !(level.getBlockEntity(pos) instanceof FoundryCastingBlockEntity cast)
                || cast.amount > 0 || cast.getItem(0).isEmpty()) return false;
        if(!level.isClientSide) give(player, cast.takeMold());
        return true;
    }

    @Override public void onRemove(BlockState state, Level level, BlockPos pos, BlockState newState, boolean moving) {
        if(!state.is(newState.getBlock()) && !level.isClientSide
                && level.getBlockEntity(pos) instanceof FoundryCastingBlockEntity cast) {
            popResource(level, pos, cast.takeScraps());
            Containers.dropContents(level, pos, cast);
        }
        super.onRemove(state, level, pos, newState, moving);
    }

    /** Upstream randomDisplayTick: smoke over a full block while it cools. */
    @Override
    public void animateTick(BlockState state, Level level, BlockPos pos, RandomSource random) {
        super.animateTick(state, level, pos, random);
        if(level.getBlockEntity(pos) instanceof FoundryCastingBlockEntity cast && cast.amount > 0 && cast.amount >= cast.getCapacity()) {
            double top = state.getShape(level, pos).max(Direction.Axis.Y);
            level.addParticle(ParticleTypes.SMOKE, pos.getX() + 0.25D + random.nextDouble() * 0.5D, pos.getY() + top,
                    pos.getZ() + 0.25D + random.nextDouble() * 0.5D, 0.0D, 0.0D, 0.0D);
        }
    }

    /** Upstream FoundryCastingBase delegates to the casting tile, which decides the sides (FoundryBaseBlockEntity, basin overrides). */
    @Override
    public boolean canAcceptPartialPour(Level level, BlockPos pos, Vec3 hit, Direction side, Mats.MaterialStack stack) {
        return level.getBlockEntity(pos) instanceof ICrucibleAcceptor acc && acc.canAcceptPartialPour(level, pos, hit, side, stack);
    }

    @Override
    public Mats.MaterialStack pour(Level level, BlockPos pos, Vec3 hit, Direction side, Mats.MaterialStack stack) {
        return level.getBlockEntity(pos) instanceof ICrucibleAcceptor acc ? acc.pour(level, pos, hit, side, stack) : stack;
    }

    @Override
    public boolean canAcceptPartialFlow(Level level, BlockPos pos, Direction side, Mats.MaterialStack stack) {
        return level.getBlockEntity(pos) instanceof ICrucibleAcceptor acc && acc.canAcceptPartialFlow(level, pos, side, stack);
    }

    @Override
    public Mats.MaterialStack flow(Level level, BlockPos pos, Direction side, Mats.MaterialStack stack) {
        return level.getBlockEntity(pos) instanceof ICrucibleAcceptor acc ? acc.flow(level, pos, side, stack) : stack;
    }

    /** Upstream printHook: the mold (or that none is installed) and the contents, plus NEO's cooling and take-output lines. */
    @Override @OnlyIn(Dist.CLIENT)
    public void printHook(RenderGuiEvent.Pre event, Level level, BlockPos pos) {
        if(!(level.getBlockEntity(pos) instanceof FoundryCastingBlockEntity cast)) return;
        List<Component> text = new ArrayList<>();
        MoldItem.Mold mold = MoldItem.of(cast.getItem(0));
        if(cast.getItem(0).isEmpty()) text.add(Component.translatable("foundry.noCast").withStyle(ChatFormatting.RED));
        else if(mold != null) text.add(mold.getTitle().withStyle(ChatFormatting.BLUE));
        if(cast.amount > 0 && cast.type != null) text.add(Component.translatable("casting.contents", cast.type.getName(), cast.amount, cast.getCapacity()).withStyle(ChatFormatting.YELLOW));
        if(cast.amount > 0 && cast.amount == cast.getCapacity()) text.add(Component.translatable("casting.cooling", cast.cooloff));
        if(!cast.getItem(1).isEmpty()) text.add(Component.translatable("casting.take_output"));
        ILookOverlay.printGeneric(event, Component.translatable(this.getDescriptionId()), 0xFF4000, 0x401000, text);
    }
}
