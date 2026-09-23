package net.minecraft.world;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
public interface Container {
 int getContainerSize();
 ItemStack getItem(int slot);
 void setItem(int slot,ItemStack stack);
 ItemStack removeItem(int slot,int count);
 ItemStack removeItemNoUpdate(int slot);
 default boolean stillValid(Player player){return true;}
 default boolean canPlaceItem(int slot,ItemStack stack){return true;}
 default int getMaxStackSize(){return 64;}
}
