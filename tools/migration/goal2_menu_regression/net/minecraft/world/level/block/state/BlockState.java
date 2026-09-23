package net.minecraft.world.level.block.state;
import com.hbm.blocks.machine.NTMAnvilBlock;
public class BlockState {
 public final Object block; public final int tier;
 public BlockState(Object block,int tier){this.block=block;this.tier=tier;}
 public boolean is(Object other){return block==other;}
 public Object getBlock(){return block;}
}
