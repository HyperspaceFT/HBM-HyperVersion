package com.hbm.blocks.machine;

import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.machine.MachineDieselBlockEntity;
import com.hbm.blocks.ICustomBlockModelRegister;
import com.hbm.inventory.fluid.trait.FT_Combustible.FuelGrade;
import com.hbm.main.NuclearTechMod;
import com.mojang.serialization.MapCodec;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.util.RandomSource;
import net.minecraft.world.Containers;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.MenuProvider;
import net.minecraft.world.SimpleMenuProvider;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.item.context.BlockPlaceContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.BaseEntityBlock;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Mirror;
import net.minecraft.world.level.block.RenderShape;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.DirectionProperty;
import net.minecraft.world.phys.BlockHitResult;
import net.neoforged.neoforge.client.model.generators.BlockStateProvider;
import net.neoforged.neoforge.client.model.generators.ModelFile;

import java.util.List;

public class MachineDieselBlock extends BaseEntityBlock implements ICustomBlockModelRegister {

    public static final DirectionProperty FACING = BlockStateProperties.HORIZONTAL_FACING;
    public static final MapCodec<MachineDieselBlock> CODEC = simpleCodec(MachineDieselBlock::new);

    public MachineDieselBlock(Properties properties) {
        super(properties);
        this.registerDefaultState(this.stateDefinition.any().setValue(FACING, Direction.NORTH));
    }

    @Override public MapCodec<MachineDieselBlock> codec() { return CODEC; }
    @Override protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) { builder.add(FACING); }
    @Override public BlockState getStateForPlacement(BlockPlaceContext context) {
        return this.defaultBlockState().setValue(FACING, context.getHorizontalDirection().getOpposite());
    }
    @Override protected BlockState rotate(BlockState state, Rotation rotation) { return state.setValue(FACING, rotation.rotate(state.getValue(FACING))); }
    @Override protected BlockState mirror(BlockState state, Mirror mirror) { return state.rotate(mirror.getRotation(state.getValue(FACING))); }
    @Override public BlockEntity newBlockEntity(BlockPos pos, BlockState state) { return new MachineDieselBlockEntity(pos, state); }

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
        if(!state.is(newState.getBlock()) && level.getBlockEntity(pos) instanceof MachineDieselBlockEntity diesel) {
            Containers.dropContents(level, pos, diesel);
        }
        super.onRemove(state, level, pos, newState, movedByPiston);
    }

    @Override
    public void animateTick(BlockState state, Level level, BlockPos pos, RandomSource random) {
        if(!(level.getBlockEntity(pos) instanceof MachineDieselBlockEntity diesel)
                || !diesel.isOn || !diesel.hasAcceptableFuel() || diesel.tank.getFill() <= 0) return;
        // The original's smoke predicate does not use wasOn or redstone, unlike its engine sound.
        Direction dir = state.getValue(FACING);
        Direction rot = dir.getClockWise();
        level.addParticle(ParticleTypes.SMOKE, pos.getX() + 0.5 - dir.getStepX() * 0.6 + rot.getStepX() * 0.1875,
                pos.getY() + 0.3125, pos.getZ() + 0.5 - dir.getStepZ() * 0.6 + rot.getStepZ() * 0.1875, 0D, 0D, 0D);
    }

    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, List<Component> components, TooltipFlag flag) {
        components.add(Component.translatable("machine_diesel.efficiency").withStyle(ChatFormatting.YELLOW));
        for(FuelGrade grade : FuelGrade.values()) {
            double efficiency = MachineDieselBlockEntity.getEfficiency(grade);
            if(efficiency > 0) components.add(Component.translatable("machine_diesel.efficiency.grade", grade.getLocalizedName(), (int)(efficiency * 100)).withStyle(ChatFormatting.YELLOW));
        }
        components.add(Component.translatable("machine_diesel.warning.full").withStyle(ChatFormatting.RED));
        components.add(Component.translatable("machine_diesel.warning.type").withStyle(ChatFormatting.RED));
    }

    @Override protected RenderShape getRenderShape(BlockState state) { return RenderShape.MODEL; }

    @Override
    public void registerModel(BlockStateProvider provider, ResourceLocation modelLocation) {
        provider.simpleBlock(this, provider.models().getBuilder(modelLocation.getPath() + "_particle")
                .texture("particle", NuclearTechMod.withDefaultNamespace("block/block_steel")));
        provider.itemModels().getBuilder(modelLocation.getPath()).parent(new ModelFile.UncheckedModelFile("builtin/entity"));
    }
}