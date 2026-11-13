package com.hbm.blocks.network;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.network.PipeBaseBlockEntity;
import com.hbm.extprop.HbmPlayerAttachments;
import com.hbm.handler.HbmKeybinds.EnumKeybind;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.items.machine.FluidIDMultiItem;
import com.hbm.items.machine.IItemFluidIdentifier;
import com.hbm.main.NuclearTechMod;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.ItemInteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.EntityBlock;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;

public abstract class FluidDuctBaseBlock extends Block implements EntityBlock, IBlockFluidDuct {

    public FluidDuctBaseBlock(Properties properties) {
        super(properties);
    }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return new PipeBaseBlockEntity(pos, state);
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        return (lvl, pos, st, be) -> { if (be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    /**
     * Original FluidDuctBase.onBlockActivated (:55-105). A fluid identifier sets this pipe's type, or with TOOL_CTRL or sneaking the
     * whole run of pipes of the old type. With TOOL_ALT the multi fluid identifier instead takes the pipe's type as its primary type,
     * with an orb sound, when the two differ (:66-75,89-98); the original does not refresh the identifier's icon data, NEO calls
     * update so the tinted icon follows as the original's NBT-read colour does. The key state is the server's; the client's own pass
     * asks its proxy, and the identifier and the sound change on the server only.
     */
    @Override
    protected ItemInteractionResult useItemOn(ItemStack stack, BlockState state, Level level, BlockPos pos, Player player, InteractionHand hand, BlockHitResult hitResult) {

        ItemStack held = player.getItemInHand(InteractionHand.MAIN_HAND);

        if(held.getItem() instanceof IItemFluidIdentifier iifi && level.getBlockEntity(pos) instanceof PipeBaseBlockEntity pipe) {
            FluidType type = iifi.getType(level, pos, held);

            if(isKeyPressed(player, EnumKeybind.TOOL_ALT) && held.getItem() instanceof FluidIDMultiItem multi && type != pipe.getFluidType()) {
                if(!level.isClientSide) {
                    FluidIDMultiItem.setType(held, pipe.getFluidType(), true);
                    multi.update(held);
                    level.playSound(null, player.getX(), player.getY(), player.getZ(), SoundEvents.EXPERIENCE_ORB_PICKUP, SoundSource.PLAYERS, 0.25F, 0.75F);
                }

                return ItemInteractionResult.SUCCESS;
            }

            if(!isKeyPressed(player, EnumKeybind.TOOL_CTRL) && !player.isShiftKeyDown()) {
                if(pipe.getFluidType() != type) {
                    pipe.setFluidType(type);
                    if(level.getBlockState(pos).getBlock() instanceof FluidDuctConnectingBlock connectingDuct) connectingDuct.updateConnections(level, pos, type);

                    return ItemInteractionResult.SUCCESS;
                }
            } else {
                this.changeTypeRecursively(level, pos, pipe.getFluidType(), type, 64);
                return ItemInteractionResult.SUCCESS;
            }
        }

        return ItemInteractionResult.FAIL;
    }

    /**
     * Whether the player holds the key: the state the server keeps in the player attachment, or on the client the local player's own
     * key through the proxy (the attachment's client copy never holds key state), as RBMKCraneConsoleBlockEntity reads its keys.
     */
    public static boolean isKeyPressed(Player player, EnumKeybind key) {
        if(!player.level().isClientSide) return HbmPlayerAttachments.getData(player).getKeyPressed(key);
        return player == NuclearTechMod.proxy.me() && NuclearTechMod.proxy.getIsKeyPressed(key);
    }


    /** Changes only the ducts of the starting duct's type, as the original (FluidDuctBase.java:100,108-126). */
    @Override
    public void changeTypeRecursively(Level level, BlockPos pos, FluidType prevType, FluidType type, int loopsRemaining) {
        if(level.getBlockEntity(pos) instanceof PipeBaseBlockEntity pipe) {
            if(pipe.getFluidType() == prevType && pipe.getFluidType() != type) {
                pipe.setFluidType(type);
                if(level.getBlockState(pos).getBlock() instanceof FluidDuctConnectingBlock connectingDuct) connectingDuct.updateConnections(level, pos, type);

                if(loopsRemaining > 0) {
                    for(Direction dir : Direction.values()) {
                        BlockPos next = pos.relative(dir);
                        if(level.getBlockState(next).getBlock() instanceof IBlockFluidDuct ibfi) {
                            ibfi.changeTypeRecursively(level, next, prevType, type, loopsRemaining - 1);
                        }
                    }
                }
            }
        }
    }
}
