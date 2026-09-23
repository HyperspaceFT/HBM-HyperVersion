package net.minecraft.world.entity.player;
import net.minecraft.core.BlockPos;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
public class Player {
 public Level level; public final Inventory inventory; public AbstractContainerMenu containerMenu;
 public double x=.5,y=.5,z=.5; public int crafted; public int dropped;
 public Player(Level level){this.level=level;inventory=new Inventory(this);}
 public Level level(){return level;}
 public double distanceToSqr(double xx,double yy,double zz){
  return (x-xx)*(x-xx)+(y-yy)*(y-yy)+(z-zz)*(z-zz);
 }
 public void drop(ItemStack stack,boolean random){dropped+=stack.getCount();}
}
