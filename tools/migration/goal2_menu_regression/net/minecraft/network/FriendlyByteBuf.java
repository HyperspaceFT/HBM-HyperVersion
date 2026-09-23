package net.minecraft.network;
import net.minecraft.core.BlockPos;
public class FriendlyByteBuf {
 public BlockPos readBlockPos(){return new BlockPos(0,0,0);}
 public int readVarInt(){return 1;}
 public int readInt(){return 0;}
 public void writeInt(int value){}
}
