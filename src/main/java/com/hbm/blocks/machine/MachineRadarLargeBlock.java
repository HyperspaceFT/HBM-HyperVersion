package com.hbm.blocks.machine;

import com.hbm.blockentity.IScreenProvider;
import com.hbm.blockentity.ITickable;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.MachineRadarBlockEntity;
import com.hbm.blockentity.machine.MachineRadarLargeBlockEntity;
import com.hbm.blocks.DummyBlockType;
import com.hbm.blocks.DummyableBlock;
import com.hbm.inventory.screens.MachineRadarScreen;
import com.hbm.main.NuclearTechMod;
import com.mojang.serialization.MapCodec;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityTicker;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.BlockHitResult;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.api.distmarker.OnlyIn;

/** Original MachineRadarLarge.java: a 3x3 radar, five blocks tall, with the core in the middle of its bottom layer. */
public class MachineRadarLargeBlock extends DummyableBlock implements IScreenProvider {

    public MachineRadarLargeBlock(Properties properties) {
        super(properties);
    }

    public static final MapCodec<MachineRadarLargeBlock> CODEC = simpleCodec(MachineRadarLargeBlock::new);
    @Override public MapCodec<MachineRadarLargeBlock> codec() { return CODEC; }

    @Override
    public BlockEntity newBlockEntity(BlockPos pos, BlockState state) {
        return switch(state.getValue(TYPE)) {
            case CORE -> new MachineRadarLargeBlockEntity(pos, state);
            case EXTRA -> new ProxyComboBlockEntity(pos, state).power();
            default -> null;
        };
    }

    @Override
    public <T extends BlockEntity> BlockEntityTicker<T> getTicker(Level level, BlockState state, BlockEntityType<T> type) {
        if(state.getValue(TYPE) != DummyBlockType.CORE) return null;
        return (lvl, pos, st, be) -> { if(be instanceof ITickable tickable) tickable.updateEntity(); };
    }

    /** Original :41-60. The altitude test uses the clicked block's height, as the original does. */
    @Override
    protected InteractionResult useWithoutItem(BlockState state, Level level, BlockPos pos, Player player, BlockHitResult hitResult) {

        if(pos.getY() < MachineRadarBlockEntity.radarAltitude) {
            if(level.isClientSide) player.sendSystemMessage(Component.translatable("radar.error.altitude").withStyle(ChatFormatting.RED));
            return InteractionResult.sidedSuccess(level.isClientSide);
        }

        if(player.isShiftKeyDown()) return InteractionResult.PASS;

        BlockPos core = this.findCore(level, pos);
        if(core == null) return InteractionResult.PASS;

        NuclearTechMod.proxy.openScreen(player, core);
        return InteractionResult.sidedSuccess(level.isClientSide);
    }

    @Override
    @OnlyIn(Dist.CLIENT)
    public Object provideScreen(Player player, BlockPos pos) {
        if(player.level().getBlockEntity(pos) instanceof MachineRadarBlockEntity radar) return new MachineRadarScreen(radar);
        return null;
    }

    @Override public int[] getDimensions() { return new int[] {4, 0, 1, 1, 1, 1}; }
    @Override public int getOffset() { return 1; }

    /** The four ports of the original (:33-40,72-78) sit next to the core on its four sides, whatever the facing. */
    @Override
    protected void fillSpace(Level level, BlockPos pos, Direction dir, int offset) {
        super.fillSpace(level, pos, dir, offset);

        BlockPos core = pos.relative(dir, offset);
        for(BlockPos port : MachineRadarLargeBlockEntity.getPortPositions(core)) this.makeExtra(level, port);
    }

    @Override
    protected boolean isSignalSource(BlockState state) {
        return true;
    }

    /**
     * Original :85-102: the core and the four ports give the radar's redstone output to the block on their far side, which reads the
     * radar through them. The block one step further along the direction from that consumer is the core when the port is queried.
     */
    @Override
    protected int getSignal(BlockState state, BlockGetter level, BlockPos pos, Direction direction) {
        if(state.getValue(TYPE) == DummyBlockType.DUMMY) return 0;
        if(level.getBlockEntity(pos.relative(direction)) instanceof MachineRadarBlockEntity radar) return radar.getRedPower();
        return 0;
    }

    @Override
    protected int getDirectSignal(BlockState state, BlockGetter level, BlockPos pos, Direction direction) {
        return this.getSignal(state, level, pos, direction);
    }
}
