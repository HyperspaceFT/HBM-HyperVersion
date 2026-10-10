package com.hbm.blockentity.machine;

import api.hbm.energymk2.*;
import com.hbm.blockentity.LoadedBaseBlockEntity;
import com.hbm.blockentity.network.CableBaseBlockEntity;
import com.hbm.blocks.*;
import com.hbm.handler.CentrifugeRecipeClientSync;
import com.hbm.inventory.*;
import com.hbm.inventory.menus.*;
import com.hbm.inventory.recipes.*;
import com.hbm.items.*;
import com.hbm.items.machine.*;
import com.hbm.items.machine.MachineUpgradeItem.UpgradeType;
import com.hbm.items.machine.BatteryPackItem.BatteryPackType;
import com.hbm.items.component.NtmDataComponents;
import com.hbm.sound.AudioWrapper;
import com.hbm.uninos.*;
import net.minecraft.core.*;
import net.minecraft.nbt.*;
import net.minecraft.network.*;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.*;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;

/** Real centrifuge/menu/Library/upgrades/network methods; recipe tables and engine services are isolated. */
public class Goal16BMachineRegression {
    static int checks, scenarios, executionTicks;
    static final BatteryPackItem PACK=new BatteryPackItem(new Item.Properties());
    static void check(boolean value,String message){checks++;if(!value)throw new AssertionError(message);}
    static void scenario(){scenarios++;}
    static Level world(){UniNodespace.levels.clear();UniNodespace.activeNodeNets.clear();CentrifugeRecipes.clear();CentrifugeRecipeClientSync.inputs.clear();AudioWrapper.CREATED.clear();Level l=new Level();l.manualClock=true;l.time=1;return l;}
    static MachineCentrifugeBlockEntity machine(Level l,int x){BlockPos pos=new BlockPos(x,0,0);BlockState state=new BlockState();var b=new MachineCentrifugeBlockEntity(pos,state);l.states.put(pos,state);l.put(b);return b;}
    static ItemStack input(){return new ItemStack(Items.COD);}
    static ItemStack output(int n){return new ItemStack(NtmItems.POWDER_COAL.get(),n);}
    static ItemStack tagged(int n,int tag){ItemStack s=output(n);s.set(NtmDataComponents.COLTAN_Z.get(),tag);return s;}
    static void recipe(ItemStack... out){CentrifugeRecipes.setRecipe(input(),out);}
    static void tick(Level l,MachineCentrifugeBlockEntity b){executionTicks++;l.time++;b.updateEntity();}
    static int total(MachineCentrifugeBlockEntity b,Item item){int n=0;for(int i=2;i<6;i++)if(b.slots.get(i).getItem()==item)n+=b.slots.get(i).getCount();return n;}
    static ItemStack upgrade(UpgradeType type,int tier){return new ItemStack(new MachineUpgradeItem(new Item.Properties(),type,tier));}
    static ItemStack pack(long n){ItemStack s=MetaHelper.newStack(PACK,1,BatteryPackType.CAPACITOR_COPPER.ordinal());PACK.setCharge(s,n);return s;}
    static void nbt(LoadedBaseBlockEntity b,CompoundTag tag,boolean load)throws Exception{Class<?> c=b.getClass();while(c!=null){try{Method m=c.getDeclaredMethod(load?"loadAdditional":"saveAdditional",CompoundTag.class,HolderLookup.Provider.class);m.setAccessible(true);m.invoke(b,tag,null);return;}catch(NoSuchMethodException e){c=c.getSuperclass();}}throw new AssertionError("missing NBT");}
    static void net(Level l){UniNodespace.updateNodespace(new MinecraftServer(List.of(l)));UniNodespace.updateNodespace(new MinecraftServer(List.of(l)));}
    static void normalAndBlocked(){
        scenario();Level l=world();var b=machine(l,0);recipe(output(6),new ItemStack(NtmBlocks.ORE_LIGNITE.get()));check(b.getContainerSize()==8&&b.getMaxPower()==100000,"8slots100000HE");b.dirty=0;tick(l,b);check(b.dirty==0&&b.power==0&&b.progress==0,"idle unchanged no dirty");b.slots.set(0,input());b.power=199;b.progress=4;b.isProgressing=true;b.dirty=0;tick(l,b);check(b.power==199&&b.progress==0&&!b.isProgressing&&b.dirty>0,"199HE resets and saves without input debit");b.power=200;tick(l,b);check(b.power==0&&b.progress==1&&b.isProgressing&&b.slots.get(0).getCount()==1,"exact200 pays first tick no early input debit");
        scenario();b=machine(l,20);b.slots.set(0,input());b.power=40000;for(int i=0;i<199;i++)tick(l,b);check(b.progress==199&&b.power==200&&b.slots.get(0).getCount()==1&&total(b,NtmItems.POWDER_COAL.get())==0,"199 ticks no outputs");tick(l,b);check(b.progress==0&&b.power==0&&b.slots.get(0).isEmpty()&&total(b,NtmItems.POWDER_COAL.get())==6,"tick200 completes at40000HE");
        scenario();b.slots.set(0,new ItemStack(Items.APPLE));b.power=1000;b.progress=10;b.dirty=0;tick(l,b);check(b.progress==0&&b.power==1000&&b.slots.get(0).getCount()==1&&b.dirty>0,"invalid input resets without payment");b.slots.set(0,input());for(int i=2;i<6;i++)b.slots.set(i,new ItemStack(Items.APPLE,64));b.progress=5;b.dirty=0;tick(l,b);check(b.progress==0&&b.power==1000&&b.slots.get(0).getCount()==1&&b.dirty>0,"blocked output resets without payment");
    }
    static void outputTransactions(){
        scenario();Level l=world();var b=machine(l,0);recipe(output(2),output(2),output(2),new ItemStack(Items.APPLE));b.slots.set(0,input());b.power=200;b.progress=199;tick(l,b);check(b.slots.get(2).getCount()==6&&b.slots.get(3).getItem()==Items.APPLE&&b.slots.get(4).isEmpty()&&b.slots.get(0).isEmpty(),"duplicate coal merged and order retained");
        scenario();b=machine(l,20);recipe(output(3));b.slots.set(0,input());b.slots.set(2,output(63));b.slots.set(3,output(62));b.slots.set(4,new ItemStack(Items.APPLE,64));b.slots.set(5,new ItemStack(Items.APPLE,64));b.power=200;b.progress=199;tick(l,b);check(b.slots.get(2).getCount()==64&&b.slots.get(3).getCount()==64&&b.slots.get(0).isEmpty(),"exact total3 across partial stacks atomic");
        scenario();b=machine(l,40);b.slots.set(0,input());b.slots.set(2,output(63));b.slots.set(3,output(63));b.slots.set(4,new ItemStack(Items.APPLE,64));b.slots.set(5,new ItemStack(Items.APPLE,64));b.power=200;b.progress=199;tick(l,b);check(b.power==200&&b.progress==0&&b.slots.get(2).getCount()==63&&b.slots.get(3).getCount()==63&&b.slots.get(0).getCount()==1,"capacity short1 no partial insertion/input/payment");
        scenario();b=machine(l,60);recipe(output(1),new ItemStack(Items.APPLE),new ItemStack(Items.COD),new ItemStack(Items.BREAD));b.slots.set(0,input());b.power=200;b.progress=199;tick(l,b);Item[] ids={NtmItems.POWDER_COAL.get(),Items.APPLE,Items.COD,Items.BREAD};for(int i=0;i<4;i++)check(b.slots.get(i+2).getItem()==ids[i]&&b.slots.get(i+2).getCount()==1,"four distinct ordered outputs");
        scenario();b=machine(l,80);recipe(tagged(3,7));b.slots.set(0,input());b.slots.set(2,tagged(60,8));b.slots.set(3,tagged(62,7));b.power=200;b.progress=199;tick(l,b);check(b.slots.get(2).getCount()==60&&b.slots.get(3).getCount()==64&&b.slots.get(4).getCount()==1&&Integer.valueOf(7).equals(b.slots.get(4).get(NtmDataComponents.COLTAN_Z.get())),"different components remain separate; exact components merge");
        scenario();b=machine(l,100);recipe(ItemStack.EMPTY,output(2),ItemStack.EMPTY);b.slots.set(0,input());b.power=200;b.progress=199;tick(l,b);check(b.slots.get(2).getCount()==2&&b.slots.get(0).isEmpty(),"explicit empty output entries skipped with nonempty output preserved");
        scenario();b=machine(l,120);recipe(output(65));b.slots.set(0,input());b.power=200;b.progress=199;tick(l,b);check(b.slots.get(2).getCount()==64&&b.slots.get(3).getCount()==1&&b.slots.get(0).isEmpty(),"large service output split without overstack; parser validity independent");
    }
    static void upgrades(){
        UpgradeType[] types={UpgradeType.SPEED,UpgradeType.POWER,UpgradeType.OVERDRIVE};
        for(int a=-1;a<3;a++)for(int tierA=1;tierA<=3;tierA++)for(int c=-1;c<3;c++)for(int tierC=1;tierC<=3;tierC++){
            if(a<0&&tierA!=1||c<0&&tierC!=1)continue;scenario();Level l=world();var b=machine(l,0);recipe(output(1));b.slots.set(0,input());int[] levels=new int[3];if(a>=0){b.slots.set(6,upgrade(types[a],tierA));levels[a]=tierA;}if(c>=0){b.slots.set(7,upgrade(types[c],tierC));levels[c]=Math.min(3,levels[c]+tierC);}int speed=(1+levels[0])*(1+5*levels[2]);long cost=(200L+200L*levels[0]+10000L*levels[2])/(1+levels[1]);int ticks=(200+speed-1)/speed;long spent=cost*ticks;long actualSpent=0;for(int i=0;i<ticks-1;i++){b.power=100000;tick(l,b);actualSpent+=100000-b.power;}check(b.slots.get(0).getCount()==1&&total(b,NtmItems.POWDER_COAL.get())==0,"upgrade no early output");b.power=100000;tick(l,b);actualSpent+=100000-b.power;check(b.progress==0&&b.slots.get(0).isEmpty()&&total(b,NtmItems.POWDER_COAL.get())==1&&actualSpent==spent&&b.power==100000-cost,"two-slot formula cap/integer division/finaltick "+a+":"+tierA+"/"+c+":"+tierC);
        }
    }
    static void roundtrip(Level l,MachineCentrifugeBlockEntity b,String stage)throws Exception{
        CompoundTag t=new CompoundTag();nbt(b,t,false);var c=machine(l,999);nbt(c,t,true);check(c.power==b.power&&c.progress==b.progress&&c.isProgressing==b.isProgressing,"NBT scalar stage "+stage);for(int i=0;i<8;i++)check(ItemStack.matches(c.slots.get(i),b.slots.get(i)),"NBT inventory stage "+stage+":"+i);
    }
    static void persistence()throws Exception{
        scenario();Level l=world();var b=machine(l,0);b.dirty=0;b.setPower(4567);check(b.power==4567&&b.dirty>0,"idle network receipt setter dirty");b.dirty=0;b.setPower(4567);check(b.dirty==0,"same setter no dirty");b.setPower(Long.MAX_VALUE);check(b.power==100000,"setter upper clamp");b.setPower(-1);check(b.power==0,"setter lower clamp");b.dirty=0;b.transferPower(1234);check(b.power==1234&&b.dirty>0,"actual receiver transfer dirty");roundtrip(l,b,"idle network receipt");
        scenario();b=machine(l,20);b.slots.set(1,pack(500));b.dirty=0;tick(l,b);check(b.power==500&&PACK.getCharge(b.slots.get(1))==0&&b.dirty>0,"idle real Library battery receipt dirty");roundtrip(l,b,"idle battery receipt");recipe(output(1));b.slots.set(0,input());b.slots.set(1,pack(200));b.power=0;b.dirty=0;tick(l,b);check(b.power==0&&b.progress==1&&PACK.getCharge(b.slots.get(1))==0&&b.dirty>0,"charge/pay net0 retains depleted component and partial dirty");
        scenario();var untouched=machine(l,30);untouched.power=100000;untouched.slots.set(1,MetaHelper.newStack(PACK,1,BatteryPackType.CAPACITOR_COPPER.ordinal()));ItemStack before=untouched.slots.get(1).copy();untouched.dirty=0;tick(l,untouched);check(untouched.power==100000&&untouched.progress==0&&!untouched.isProgressing&&!ItemStack.matches(before,untouched.slots.get(1))&&untouched.dirty>0,"battery zero-discharge initializes component while every machine scalar unchanged dirty");
        CompoundTag t=new CompoundTag();nbt(b,t,false);var copy=machine(l,40);nbt(copy,t,true);check(copy.power==b.power&&copy.progress==b.progress&&copy.isProgressing==b.isProgressing,"scalar NBT roundtrip");for(int i=0;i<8;i++)check(ItemStack.matches(copy.slots.get(i),b.slots.get(i)),"inventory/components NBT roundtrip "+i);
        scenario();var reset=machine(l,50);reset.slots.set(0,input());reset.power=199;reset.progress=10;reset.isProgressing=true;reset.dirty=0;tick(l,reset);check(reset.progress==0&&!reset.isProgressing&&reset.dirty>0,"failed progress reset dirty");roundtrip(l,reset,"failed reset");
        scenario();var finish=machine(l,60);recipe(tagged(2,9));finish.slots.set(0,input());finish.power=200;finish.progress=199;finish.dirty=0;tick(l,finish);check(finish.slots.get(0).isEmpty()&&finish.slots.get(2).getCount()==2&&finish.dirty>0,"completed component output dirty");roundtrip(l,finish,"completion");
        for(int progress:new int[]{-1,200,Integer.MAX_VALUE}){scenario();t.putLong("power",Long.MAX_VALUE);t.putInt("progress",progress);t.putBoolean("isProgressing",true);nbt(copy,t,true);check(copy.power==100000&&copy.progress==0&&copy.isProgressing,"illegal progress reset boolean preserved");}t.putLong("power",-1);t.putInt("progress",199);nbt(copy,t,true);check(copy.power==0&&copy.progress==199,"negative power clamp legal progress retained");
        scenario();b.dirty=0;b.removeItemNoUpdate(0);check(b.dirty>0,"removeNoUpdate dirty");b.dirty=0;b.removeItemNoUpdate(0);check(b.dirty==0,"empty remove unchanged");b.dirty=0;b.clearContent();check(b.dirty>0,"nonempty clear dirty");b.dirty=0;b.clearContent();check(b.dirty==0,"empty clear unchanged");b.setItem(0,input());b.dirty=0;b.removeItem(0,1);check(b.dirty>0,"inherited actual remove dirty");RegistryFriendlyByteBuf buf=new RegistryFriendlyByteBuf();b.power=765;b.progress=12;b.isProgressing=true;b.serialize(buf);copy.deserialize(buf);check(copy.power==765&&copy.progress==12&&copy.isProgressing,"runtime buffer roundtrip");
    }
    static final class Link extends DummyableBlock{Link(){super(new Block.Properties());}public int[] getDimensions(){return new int[]{3,0,0,0,0,0};}public int getOffset(){return 0;}}
    static Player player(Level l){Player p=new Player();p.world=l;p.level=l;p.getInventory().player=p;return p;}
    static void menusAndSides(){
        scenario();Level l=world();var b=machine(l,0);recipe(output(1));Player p=player(l);var menu=new MachineCentrifugeMenu(0,p.getInventory(),b);check(menu.slots.size()==44,"8machine36player slots");for(int s=2;s<6;s++)check(!menu.slots.get(s).mayPlace(input()),"output take only "+s);check(menu.slots.get(0).mayPlace(input())&&!menu.slots.get(0).mayPlace(new ItemStack(Items.APPLE)),"manual input filter");p.getInventory().setItem(9,input());menu.quickMoveStack(p,8);check(b.slots.get(0).getItem()==Items.COD,"shift input follows filter");p.getInventory().setItem(10,new ItemStack(Items.APPLE));check(menu.quickMoveStack(p,9).isEmpty(),"shift invalid rejected");p.getInventory().setItem(11,pack(100));menu.quickMoveStack(p,10);check(b.slots.get(1).getItem()==PACK,"shift battery");p.getInventory().setItem(12,upgrade(UpgradeType.SPEED,3));menu.quickMoveStack(p,11);check(b.slots.get(6).getItem() instanceof MachineUpgradeItem,"shift upgrade");
        for(Direction d:Direction.values()){check(Arrays.equals(b.getSlotsForFace(d),new int[]{0,2,3,4,5}),"allside slots");for(int s=0;s<8;s++){check(b.canTakeItemThroughFace(s,input(),d)==(s>=2&&s<6),"output only extraction");check(b.canPlaceItemThroughFace(s,input(),d)==(s==0),"recipe input insertion only");}}
        scenario();l.isClientSide=true;CentrifugeRecipeClientSync.inputs.add(new ItemStack(Items.APPLE));check(!b.canPlaceItem(0,input())&&b.canPlaceItem(0,new ItemStack(Items.APPLE)),"client prediction uses explicit snapshot service");l.isClientSide=false;check(b.canPlaceItem(0,input())&&!b.canPlaceItem(0,new ItemStack(Items.APPLE)),"server remains authoritative");var orphan=new MachineCentrifugeBlockEntity(new BlockPos(100,0,0),new BlockState());check(orphan.canPlaceItem(0,input()),"nulllevel uses authoritative table");
        for(Direction facing:new Direction[]{Direction.NORTH,Direction.EAST,Direction.SOUTH,Direction.WEST})for(int height=0;height<4;height++){scenario();l=world();Link link=new Link();BlockPos core=new BlockPos(0,0,0);BlockState state=link.createCoreState(facing);b=new MachineCentrifugeBlockEntity(core,state);l.put(b);l.states.put(core,state);for(int h=1;h<4;h++)l.states.put(core.above(h),link.createDummyState(Direction.UP));p=player(l);FriendlyByteBuf packet=new FriendlyByteBuf();packet.writeBlockPos(core.above(height));check(new MachineCentrifugeMenu(0,p.getInventory(),packet).be==b,"all four clicked positions resolve menu core");}
    }
    static void lifecycle()throws Exception{
        for(int endpoint=0;endpoint<6;endpoint++){scenario();Level l=world();var b=machine(l,0);var core=b;var cps=b.getConPos();check(cps.length==6,"six core endpoints");int[][] xyz={{1,0,0},{-1,0,0},{0,0,1},{0,0,-1},{0,1,0},{0,-1,0}};check(cps[endpoint].makeCompat().equals(new BlockPos(xyz[endpoint][0],xyz[endpoint][1],xyz[endpoint][2])),"exact endpoint position");var cable=new CableBaseBlockEntity(cps[endpoint].makeCompat(),new BlockState());l.put(cable);cable.updateEntity();net(l);tick(l,b);net(l);check(UniNodespace.activeNodeNets.stream().anyMatch(n->n instanceof PowerNetMK2&&n.receiverEntries.containsKey(core)),"actual cable endpoint subscribes");var disconnected=new PowerNetMK2();disconnected.addReceiver(b);b.onChunkUnloaded();check(!b.isLoaded()&&UniNodespace.activeNodeNets.stream().noneMatch(n->n instanceof PowerNetMK2&&n.receiverEntries.containsKey(core)),"unload clears all networks including nonadjacent membership");b.onLoad();tick(l,b);net(l);check(b.isLoaded()&&UniNodespace.activeNodeNets.stream().anyMatch(n->n instanceof PowerNetMK2&&n.receiverEntries.containsKey(core)),"reload resubscribes");b.setRemoved();check(UniNodespace.activeNodeNets.stream().noneMatch(n->n instanceof PowerNetMK2&&n.receiverEntries.containsKey(core)),"removed explicit membership clear");}
        scenario();Level l=world();var b=machine(l,0);PowerNetMK2 first=new PowerNetMK2(),second=new PowerNetMK2();first.addReceiver(b);second.addReceiver(b);first.joinNetworks(second);var isolated=new PowerNetMK2();isolated.addReceiver(b);b.onChunkUnloaded();check(first.receiverEntries.isEmpty()&&isolated.receiverEntries.isEmpty(),"merged and isolated membership retired");
        scenario();l=world();b=machine(l,0);var core=b;BlockPos port=b.getConPos()[0].makeCompat();var cable=new CableBaseBlockEntity(port,new BlockState());l.put(cable);cable.updateEntity();net(l);tick(l,b);net(l);cable.setRemoved();l.entities.remove(port);net(l);tick(l,b);net(l);check(UniNodespace.activeNodeNets.stream().noneMatch(n->n instanceof PowerNetMK2&&n.receiverEntries.containsKey(core)),"physical cable removal retires topology");var replacement=new CableBaseBlockEntity(port,new BlockState());l.put(replacement);replacement.updateEntity();net(l);l.time+=20;tick(l,b);net(l);check(UniNodespace.activeNodeNets.stream().anyMatch(n->n instanceof PowerNetMK2&&n.receiverEntries.containsKey(core)),"reconnect after actual cache expiry");
        scenario();l=world();b=machine(l,0);l.isClientSide=true;b.power=1000;b.progress=10;b.isProgressing=true;tick(l,b);check(b.power==1000&&b.progress==10&&AudioWrapper.CREATED.size()==1,"client loop no state payment");AudioWrapper audio=AudioWrapper.CREATED.getFirst();tick(l,b);check(audio.keptAlive>0,"audio keepalive");b.isProgressing=false;tick(l,b);check(audio.stopped==1,"idle sound stop");b.isProgressing=true;tick(l,b);audio=AudioWrapper.CREATED.getLast();b.onChunkUnloaded();check(audio.stopped==1,"unload sound stop");b.onLoad();tick(l,b);audio=AudioWrapper.CREATED.getLast();b.setRemoved();check(audio.stopped==1,"remove sound stop");
    }
    static void finite(Path output)throws Exception{
        scenario();Level l=world();var b=machine(l,0);CentrifugeRecipes.setRecipe(new ItemStack(Blocks.COAL_ORE),new ItemStack(NtmItems.POWDER_COAL.get(),2),new ItemStack(NtmItems.POWDER_COAL.get(),2),new ItemStack(NtmItems.POWDER_COAL.get(),2),new ItemStack(Blocks.STONE));b.slots.set(0,new ItemStack(Blocks.COAL_ORE));b.slots.set(1,pack(40000));for(int i=0;i<200;i++)tick(l,b);long battery=PACK.getCharge(b.slots.get(1));check(b.slots.get(0).isEmpty()&&total(b,NtmItems.POWDER_COAL.get())==6&&total(b,Blocks.STONE.asItem())==1&&b.power==0&&battery==0,"finite mineral1 yields6 after40000HE actual battery discharge");tick(l,b);check(!b.isProgressing&&b.progress==0&&b.power==0,"finite terminal tick remains stopped");Files.writeString(output.resolve("finite.json"),"{\"evidence\":\"Isolated production BE/Library battery transaction; explicit recipe table service; no upstream mining/generation or gameplay proof\",\"mineral_input\":1,\"powder_output\":6,\"stone_output\":1,\"energy_input_HE\":40000,\"processing_HE\":40000,\"machine_remaining_HE\":0,\"battery_remaining_HE\":0,\"discarded_HE\":0}");
    }
    public static void main(String[] args)throws Exception{normalAndBlocked();outputTransactions();upgrades();persistence();menusAndSides();lifecycle();finite(Path.of(args[0]));System.out.println("Goal16B machine/menu/network: "+checks+" assertions; "+scenarios+" independent scenarios; "+executionTicks+" executed ticks (not counted as assertions); no game/save/server proof");}
}
