package net.minecraft.world.inventory;
import net.minecraft.world.Container;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
public class Slot {
 protected final Container container; private final int index;
 public Slot(Container container,int index,int x,int y){this.container=container;this.index=index;}
 public int getContainerSlot(){return index;}
 public boolean hasItem(){return !getItem().isEmpty();}
 public ItemStack getItem(){return container.getItem(index);}
 public void setByPlayer(ItemStack stack){container.setItem(index,stack);setChanged();}
 public void setChanged(){}
 public void onTake(Player player,ItemStack stack){setChanged();}
 public boolean mayPlace(ItemStack stack){return true;}
 public int getMaxStackSize(){return container.getMaxStackSize();}
 public int getMaxStackSize(ItemStack stack){return Math.min(getMaxStackSize(),stack.getMaxStackSize());}
}
