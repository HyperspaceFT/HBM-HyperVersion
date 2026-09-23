package net.minecraft.world.level;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.state.BlockState;
public class Level {
 public boolean isClientSide=false;
 public BlockState state;
 public BlockState getBlockState(BlockPos pos){return state;}
}
