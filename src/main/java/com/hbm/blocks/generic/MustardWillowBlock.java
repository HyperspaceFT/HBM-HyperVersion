package com.hbm.blocks.generic;

import com.hbm.blocks.NtmBlocks;
import com.mojang.serialization.MapCodec;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.FluidTags;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.BlockGetter;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.LevelReader;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.BonemealableBlock;
import net.minecraft.world.level.block.BushBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.StateDefinition;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import net.minecraft.world.level.block.state.properties.DoubleBlockHalf;
import net.minecraft.world.level.block.state.properties.IntegerProperty;
import net.minecraft.world.level.block.state.properties.EnumProperty;
import net.minecraft.world.level.storage.loot.LootParams;

/**
 * The original's five mustard willow stages: plant_flower CD0 and CD1 (ages 0-1, one block) and plant_tall CD2 to CD4 (ages 2-4, two blocks).
 * Nothing but the willow is ported from BlockNTMFlower and BlockTallPlant.
 */
public class MustardWillowBlock extends BushBlock implements BonemealableBlock, com.hbm.blocks.ILookOverlay {

    public static final MapCodec<MustardWillowBlock> CODEC = simpleCodec(MustardWillowBlock::new);
    public static final IntegerProperty AGE = IntegerProperty.create("age", 0, 4);
    public static final EnumProperty<DoubleBlockHalf> HALF = BlockStateProperties.DOUBLE_BLOCK_HALF;

    public MustardWillowBlock(Properties properties) {
        super(properties);
        this.registerDefaultState(this.stateDefinition.any().setValue(AGE, 0).setValue(HALF, DoubleBlockHalf.LOWER));
    }

    @Override
    protected MapCodec<? extends BushBlock> codec() { return CODEC; }

    @Override
    protected void createBlockStateDefinition(StateDefinition.Builder<Block, BlockState> builder) {
        builder.add(AGE, HALF);
    }

    /** The original names the stages through its metadata names (tile.plant_tall.cd4 is the mature one). */
    @Override
    @net.neoforged.api.distmarker.OnlyIn(net.neoforged.api.distmarker.Dist.CLIENT)
    public void printHook(net.neoforged.neoforge.client.event.RenderGuiEvent.Pre event, Level level, BlockPos pos) {
        BlockState state = level.getBlockState(pos);
        if(!state.is(this)) return;
        net.minecraft.network.chat.Component title = net.minecraft.network.chat.Component.translatable(state.getValue(AGE) == 4 ? "block.hbmsntm.plant_mustard_willow.mature" : "block.hbmsntm.plant_mustard_willow");
        com.hbm.blocks.ILookOverlay.printGeneric(event, title, 0xFFFF00, 0x404000, java.util.List.of());
    }

    private static boolean isSoil(BlockState state) {
        return state.is(Blocks.GRASS_BLOCK) || state.is(Blocks.DIRT) || state.is(Blocks.FARMLAND)
                || state.is(NtmBlocks.DIRT_DEAD.get()) || state.is(NtmBlocks.DIRT_OILY.get());
    }

    @Override
    protected boolean mayPlaceOn(BlockState state, BlockGetter level, BlockPos pos) {
        return isSoil(state);
    }

    @Override
    protected boolean canSurvive(BlockState state, LevelReader level, BlockPos pos) {
        BlockState below = level.getBlockState(pos.below());
        if(state.getValue(HALF) == DoubleBlockHalf.UPPER) {
            return below.is(this) && below.getValue(HALF) == DoubleBlockHalf.LOWER && below.getValue(AGE).equals(state.getValue(AGE));
        }
        return isSoil(below);
    }

    /** Survival is checked in neighborChanged as the original checkAndDropBlock, so a lost upper half neither pops itself nor its leaves. */
    @Override
    protected BlockState updateShape(BlockState state, Direction direction, BlockState neighbor, net.minecraft.world.level.LevelAccessor level, BlockPos pos, BlockPos neighborPos) {
        return state;
    }

    @Override
    protected void neighborChanged(BlockState state, Level level, BlockPos pos, Block block, BlockPos fromPos, boolean isMoving) {
        if(level.isClientSide) return;

        if(!state.canSurvive(level, pos)) {
            if(state.getValue(HALF) == DoubleBlockHalf.LOWER) dropResources(state, level, pos);
            level.setBlock(pos, Blocks.AIR.defaultBlockState(), 3);
            return;
        }

        // A lower half that lost its upper half falls back to the sapling (BlockTallPlant.java:153-158)
        if(state.getValue(HALF) == DoubleBlockHalf.LOWER && state.getValue(AGE) >= 2) {
            BlockState above = level.getBlockState(pos.above());
            if(!above.is(this) || above.getValue(HALF) != DoubleBlockHalf.UPPER || !above.getValue(AGE).equals(state.getValue(AGE))) {
                level.setBlock(pos, this.defaultBlockState(), 3);
            }
        }
    }

    /** BlockTallPlant.onBlockHarvested: breaking the lower half also harvests the upper one, without drops in creative mode. */
    @Override
    public BlockState playerWillDestroy(Level level, BlockPos pos, BlockState state, Player player) {
        if(!level.isClientSide && state.getValue(HALF) == DoubleBlockHalf.LOWER) {
            BlockPos above = pos.above();
            BlockState upper = level.getBlockState(above);

            if(upper.is(this) && upper.getValue(HALF) == DoubleBlockHalf.UPPER) {
                if(player.hasInfiniteMaterials()) {
                    level.setBlock(above, Blocks.AIR.defaultBlockState(), Block.UPDATE_CLIENTS | Block.UPDATE_SUPPRESS_DROPS);
                } else {
                    dropResources(upper, level, above, null, player, player.getMainHandItem());
                }
            }
        }
        return super.playerWillDestroy(level, pos, state, player);
    }

    @Override
    protected boolean isRandomlyTicking(BlockState state) {
        return state.getValue(HALF) == DoubleBlockHalf.LOWER && state.getValue(AGE) < 4;
    }

    @Override
    protected void randomTick(BlockState state, ServerLevel level, BlockPos pos, RandomSource random) {
        if(this.isValidBonemealTarget(level, pos, state) && this.isBonemealSuccess(level, random, pos, state) && random.nextInt(3) == 0) {
            this.performBonemeal(level, random, pos, state);
        }
    }

    private static BlockPos lowerPos(BlockPos pos, BlockState state) {
        return state.getValue(HALF) == DoubleBlockHalf.UPPER ? pos.below() : pos;
    }

    /** Cadmium willows can only grow with water: one of the four blocks next to the block below the lower half has to be water. */
    private static boolean hasWater(LevelReader level, BlockPos lower) {
        BlockPos soil = lower.below();
        for(Direction direction : Direction.Plane.HORIZONTAL) {
            if(level.getFluidState(soil.relative(direction)).is(FluidTags.WATER)) return true;
        }
        return false;
    }

    /* grow condition: BlockNTMFlower.java:142-155 and BlockTallPlant.java:230-247 */
    @Override
    public boolean isValidBonemealTarget(LevelReader level, BlockPos pos, BlockState state) {
        int age = state.getValue(AGE);
        BlockPos lower = lowerPos(pos, state);

        if(age >= 4) return false;
        if(!hasWater(level, lower)) return false;

        if(age == 1) return level.isEmptyBlock(lower.above());
        if(age == 3) {
            BlockState soil = level.getBlockState(lower.below());
            return soil.is(NtmBlocks.DIRT_DEAD.get()) || soil.is(NtmBlocks.DIRT_OILY.get());
        }
        return true;
    }

    /* chance: BlockNTMFlower.java:164-165 and BlockTallPlant.java:254-257 */
    @Override
    public boolean isBonemealSuccess(Level level, RandomSource random, BlockPos pos, BlockState state) {
        if(state.getValue(AGE) == 3) return true;
        return random.nextFloat() < 0.33F;
    }

    /* grow: BlockNTMFlower.java:191-198 and BlockTallPlant.java:269-284; both halves change without notifying each other */
    @Override
    public void performBonemeal(ServerLevel level, RandomSource random, BlockPos pos, BlockState state) {
        int age = state.getValue(AGE);
        BlockPos lower = lowerPos(pos, state);
        BlockState lowerState = this.defaultBlockState().setValue(AGE, age + 1);

        if(age == 0) {
            level.setBlock(lower, lowerState, 3);
            return;
        }

        level.setBlock(lower.above(), lowerState.setValue(HALF, DoubleBlockHalf.UPPER), Block.UPDATE_CLIENTS);
        level.setBlock(lower, lowerState, Block.UPDATE_CLIENTS);

        // The mature willow draws the oil out of the soil
        if(age == 3) {
            level.setBlock(lower.below(), Blocks.DIRT.defaultBlockState(), 3);
        }
    }
}
