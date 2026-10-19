package com.hbm.blocks.machine;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.machine.MachineRTGBlockEntity;
import com.hbm.blocks.ICustomBlockModelRegister;
import com.hbm.main.NuclearTechMod;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.Containers;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.MenuProvider;
import net.minecraft.world.SimpleMenuProvider;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.BaseEntityBlock;
import net.minecraft.world.level.block.RenderShape;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;
import net.neoforged.neoforge.client.model.generators.BlockStateProvider;
import net.neoforged.neoforge.client.model.generators.ModelFile;

/** Port of the original MachineRTG; like the original it has no facing, the renderer turns the model 180 degrees. */
public class MachineRTGBlock extends BaseEntityBlock implements ICustomBlockModelRegister {

    public static final MapCodec<MachineRTGBlock> CODEC = simpleCodec(MachineRTGBlock::new);

    public MachineRTGBlock(Properties properties) {
        super(properties);
    }

    @Override public MapCodec<MachineRTGBlock> codec() { return CODEC; }
    @Override public BlockEntity newBlockEntity(BlockPos pos, BlockState state) { return new MachineRTGBlockEntity(pos, state); }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    @Override
    protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hitResult) {
        if(level.isClientSide) return InteractionResult.SUCCESS;
        if(player.isShiftKeyDown()) return InteractionResult.PASS;
        if(level.getBlockEntity(pos) instanceof MenuProvider menu) {
            player.openMenu(new SimpleMenuProvider(menu, menu.getDisplayName()), pos);
        }
        return InteractionResult.CONSUME;
    }

    @Override
    public void onRemove(BlockState state, Level level, BlockPos pos, BlockState newState, boolean movedByPiston) {
        if(!state.is(newState.getBlock()) && level.getBlockEntity(pos) instanceof MachineRTGBlockEntity rtg) {
            Containers.dropContents(level, pos, rtg);
        }
        super.onRemove(state, level, pos, newState, movedByPiston);
    }

    @Override protected RenderShape getRenderShape(BlockState state) { return RenderShape.MODEL; }

    @Override
    public void registerModel(BlockStateProvider provider, ResourceLocation modelLocation) {
        provider.simpleBlock(this, provider.models().getBuilder(modelLocation.getPath() + "_particle")
                .texture("particle", NuclearTechMod.withDefaultNamespace("block/block_steel")));
        provider.itemModels().getBuilder(modelLocation.getPath()).parent(new ModelFile.UncheckedModelFile("builtin/entity"));
    }
}
