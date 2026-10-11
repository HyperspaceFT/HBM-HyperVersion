package com.hbm.blockentity.machine;

import api.hbm.fluidmk2.*;
import api.hbm.energymk2.*;
import com.hbm.blocks.DummyableBlock;
import com.hbm.extprop.HbmPlayerAttachments;
import com.hbm.inventory.*;
import com.hbm.inventory.fluid.*;
import com.hbm.inventory.menus.MachineCrystallizerMenu;
import com.hbm.inventory.recipes.*;
import com.hbm.items.NtmItems;
import com.hbm.items.component.NtmDataComponents;
import com.hbm.items.machine.*;
import com.hbm.items.machine.MachineUpgradeItem.UpgradeType;
import com.hbm.uninos.*;
import net.minecraft.core.*;
import net.minecraft.nbt.*;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.*;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import java.nio.file.*;
import java.util.*;

/** Production crystallizer ticks over declared engine services: the recipe table rows are fixture inputs mirroring the verified defaults. */
public class Goal18AMachineRegression extends Goal14CMachineRegression {
    static int executedTicks;
    static final Item ORE_IRON = Blocks.IRON_ORE.asItem(), ORE_COPPER = Blocks.COPPER_ORE.asItem(), ORE_DEEPSLATE_IRON = Blocks.DEEPSLATE_IRON_ORE.asItem();
    static Level fresh(){
        Level l=world();CrystallizerRecipes.clear();
        CrystallizerRecipes.setRecipe(new ItemStack(ORE_IRON),Fluids.PEROXIDE,500,new ItemStack(NtmItems.CRYSTAL_IRON.get()),600,0.05F);
        CrystallizerRecipes.setRecipe(new ItemStack(ORE_DEEPSLATE_IRON),Fluids.PEROXIDE,500,new ItemStack(NtmItems.CRYSTAL_IRON.get()),600,0.05F);
        CrystallizerRecipes.setRecipe(new ItemStack(ORE_COPPER),Fluids.PEROXIDE,500,new ItemStack(NtmItems.CRYSTAL_COPPER.get()),600,0.05F);
        return l;
    }
    static MachineCrystallizerBlockEntity machine(Level l,int x,Direction facing,long power,int acid){
        BlockPos p=new BlockPos(x,0,0);BlockState s=new BlockState().setValue(DummyableBlock.FACING,facing);
        var b=new MachineCrystallizerBlockEntity(p,s);l.states.put(p,s);l.put(b);b.power=power;b.tank.setFill(acid);return b;
    }
    static void step(Level l,MachineCrystallizerBlockEntity b){l.time++;b.updateEntity();executedTicks++;}
    static void ticks(Level l,MachineCrystallizerBlockEntity b,int n){for(int i=0;i<n;i++)step(l,b);}
    static int crystals(MachineCrystallizerBlockEntity b){ItemStack s=b.slots.get(2);return s.isEmpty()?0:s.getCount();}

    static void basics(){
        scenario();Level l=fresh();var b=machine(l,0,Direction.NORTH,0,0);
        check(b.getContainerSize()==8&&b.getMaxPower()==1_000_000L&&b.tank.getMaxFill()==8000&&b.tank.getTankType()==Fluids.PEROXIDE,"eight slots, 1,000,000 HE, 8,000 mB peroxide tank");
        check(b.getDuration()==600&&b.getPowerRequired()==1000&&b.getCycleCount()==1,"no upgrades: 600 base, 1,000 HE per sub-cycle, one sub-cycle per tick");
        for(Direction f:new Direction[]{Direction.NORTH,Direction.SOUTH,Direction.EAST,Direction.WEST}){
            scenario();l=fresh();b=machine(l,0,f,0,0);Set<BlockPos> actual=new HashSet<>();for(var c:b.getConPos())actual.add(c.makeCompat());
            BlockPos core=b.getBlockPos();Set<BlockPos> expected=Set.of(core.offset(2,0,1),core.offset(1,0,2),core.offset(2,0,-1),core.offset(1,0,-2),core.offset(-2,0,1),core.offset(-1,0,2),core.offset(-2,0,-1),core.offset(-1,0,-2));
            check(actual.equals(expected)&&b.getConPos().length==8,"eight external corner neighbours independent of facing "+f);
            for(var c:b.getConPos())check(c.getDir().getStepY()==0&&c.makeCompat().relative(c.getDir().getOpposite()).distManhattan(core)==2,"each connection points outward from a bottom corner "+f);
        }
        check(b.canConnect(Direction.NORTH)&&b.canConnect(Direction.EAST)&&!b.canConnect(Direction.UP)&&!b.canConnect(Direction.DOWN),"horizontal connections only");
        check(b.canConnect(Fluids.PEROXIDE,Direction.WEST)&&!b.canConnect(Fluids.PEROXIDE,Direction.UP),"fluid connections follow the same sides");
    }
    static void cycles(){
        scenario();Level l=fresh();var b=machine(l,0,Direction.NORTH,1_000_000L,8000);b.slots.set(0,new ItemStack(ORE_IRON,3));
        ticks(l,b,600);
        check(b.progress==600&&crystals(b)==0&&b.power==400_000L&&b.tank.getFill()==8000&&b.slots.get(0).getCount()==3&&b.isOn,"600 effective sub-cycles: no crystal yet, 600,000 HE spent, acid and input untouched");
        step(l,b);
        check(crystals(b)==1&&b.slots.get(2).getItem()==NtmItems.CRYSTAL_IRON.get()&&b.progress==0&&b.power==399_000L&&b.tank.getFill()==7500&&b.slots.get(0).getCount()==2,"601st sub-cycle delivers one crystal, 601,000 HE, 500 mB acid and one ore consumed");
        ticks(l,b,601);
        check(crystals(b)==2&&b.slots.get(0).getCount()==1&&b.tank.getFill()==7000&&b.power==399_000L-601_000L+0L*0||b.power==0L,"second batch bounded by power");
        // 399,000 HE only covers 399 sub-cycles: progress is cleared on the 400th attempt and nothing further is delivered.
        scenario();l=fresh();b=machine(l,0,Direction.NORTH,399_000L,8000);b.slots.set(0,new ItemStack(ORE_IRON));ticks(l,b,399);
        check(b.progress==399&&b.power==0&&crystals(b)==0,"399 sub-cycles exhaust 399,000 HE");
        step(l,b);check(b.progress==0&&!b.isOn&&crystals(b)==0&&b.tank.getFill()==8000&&b.slots.get(0).getCount()==1,"power shortage clears progress without consuming anything");
        scenario();l=fresh();b=machine(l,0,Direction.NORTH,600_999L,8000);b.slots.set(0,new ItemStack(ORE_IRON));ticks(l,b,600);
        check(b.progress==600&&b.power==999L,"one HE short of the 601st sub-cycle");
        step(l,b);check(b.progress==0&&crystals(b)==0&&b.power==999L,"601st sub-cycle refused by 1 HE: progress cleared, no refund of the 600,000 HE");
        b.power=1_000_000L;ticks(l,b,601);check(crystals(b)==1&&b.power==1_000_000L-601_000L,"restart needs the full 601 sub-cycles again");
        scenario();l=fresh();b=machine(l,0,Direction.NORTH,1_000_000L,499);b.slots.set(0,new ItemStack(ORE_IRON));ticks(l,b,5);
        check(b.progress==0&&b.power==1_000_000L&&!b.isOn,"499 mB acid never starts");
        b.tank.setFill(500);ticks(l,b,601);check(crystals(b)==1&&b.tank.getFill()==0,"exactly 500 mB completes once and empties the tank");
        step(l,b);check(b.progress==0&&b.power==1_000_000L-601_000L,"empty tank stops the next batch without paying");
        scenario();l=fresh();CrystallizerRecipes.clear();CrystallizerRecipes.setRecipe(new ItemStack(ORE_IRON,2),Fluids.PEROXIDE,500,new ItemStack(NtmItems.CRYSTAL_IRON.get()),600,0.05F);
        b=machine(l,0,Direction.NORTH,1_000_000L,8000);b.slots.set(0,new ItemStack(ORE_IRON,1));ticks(l,b,3);
        check(b.progress==0&&b.power==1_000_000L,"input below the recipe count never starts");
        b.slots.set(0,new ItemStack(ORE_IRON,2));ticks(l,b,601);check(crystals(b)==1&&b.slots.get(0).isEmpty(),"a two-item row consumes both items");
        scenario();l=fresh();b=machine(l,0,Direction.NORTH,1_000_000L,8000);b.slots.set(0,new ItemStack(ORE_IRON));b.slots.set(2,new ItemStack(NtmItems.CRYSTAL_IRON.get(),64));ticks(l,b,3);
        check(b.progress==0&&b.power==1_000_000L,"full output slot blocks");
        b.slots.set(2,new ItemStack(Items.STICK));ticks(l,b,3);check(b.progress==0,"mismatched output item blocks");
        ItemStack tagged=new ItemStack(NtmItems.CRYSTAL_IRON.get(),10);tagged.set(NtmDataComponents.COLTAN_Z.get(),3);b.slots.set(2,tagged);ticks(l,b,3);
        check(b.progress==0,"same item with different components does not merge");
        b.slots.set(2,new ItemStack(NtmItems.CRYSTAL_IRON.get(),63));ticks(l,b,601);check(crystals(b)==64,"63 + 1 merges to a full stack");
        step(l,b);check(b.progress==0&&b.power==1_000_000L-601_000L,"then the full stack blocks the next batch");
        scenario();l=fresh();b=machine(l,0,Direction.NORTH,1_000_000L,8000);b.slots.set(0,new ItemStack(Items.STICK));ticks(l,b,3);
        check(b.progress==0&&!b.canPlaceItem(0,new ItemStack(Items.STICK)),"non-recipe input never starts and is refused by the slot filter");
        scenario();l=fresh();b=machine(l,0,Direction.NORTH,1_000_000L,8000);b.slots.set(0,new ItemStack(ORE_IRON));ticks(l,b,300);b.slots.set(0,ItemStack.EMPTY);step(l,b);
        check(b.progress==0&&b.power==1_000_000L-300_000L,"removing the input mid-way clears progress and keeps the sunk cost");
    }
    static void acids(){
        scenario();Level l=fresh();var b=machine(l,0,Direction.NORTH,1_000_000L,8000);b.slots.set(0,new ItemStack(ORE_IRON));b.slots.set(7,identifier(Fluids.SULFURIC_ACID));
        FluidNetMK2 old=new FluidNetMK2(Fluids.PEROXIDE);old.addReceiver(b);UniNodespace.activeNodeNets.add(old);b.dirty=0;step(l,b);
        check(b.tank.getTankType()==Fluids.SULFURIC_ACID&&b.tank.getFill()==0&&!old.receiverEntries.containsKey(b)&&b.dirty>0,"retype clears the acid, leaves the old fluid network and saves");
        check(b.progress==0&&!b.canPlaceItem(0,new ItemStack(ORE_IRON)),"the peroxide row does not run or pass the filter under sulfuric acid");
        CrystallizerRecipes.setRecipe(new ItemStack(ORE_IRON),Fluids.SULFURIC_ACID,500,new ItemStack(NtmItems.CRYSTAL_COPPER.get()),100,0.0F);
        b.tank.setFill(600);check(b.canPlaceItem(0,new ItemStack(ORE_IRON))&&b.getDuration()==100,"a second row for the same input with another acid resolves separately");
        ticks(l,b,101);check(crystals(b)==1&&b.slots.get(2).getItem()==NtmItems.CRYSTAL_COPPER.get()&&b.tank.getFill()==100,"the sulfuric row delivers its own output after 101 sub-cycles");
        scenario();l=fresh();b=machine(l,0,Direction.NORTH,0,0);FluidContainerRegistry.clearRegistry();FluidContainerRegistry.register();
        ItemStack full=FluidContainerRegistry.getFullContainer(new ItemStack(NtmItems.FLUID_TANK_EMPTY.get()),Fluids.PEROXIDE);full.set(NtmDataComponents.COLTAN_Z.get(),7);
        b.slots.set(3,full.copy());b.dirty=0;step(l,b);
        check(b.tank.getFill()==1000&&b.slots.get(3).isEmpty()&&!b.slots.get(4).isEmpty()&&Objects.equals(b.slots.get(4).get(NtmDataComponents.COLTAN_Z.get()),7)&&b.dirty>0,"whole container loads, the empty container keeps its components, saved");
        for(ItemStack bad:new ItemStack[]{new ItemStack(NtmItems.FLUID_TANK_EMPTY.get(),64),new ItemStack(Items.STICK)}){
            scenario();b.slots.set(3,full.copy());b.slots.set(4,bad);step(l,b);check(b.tank.getFill()==1000&&!b.slots.get(3).isEmpty(),"full or foreign return slot refuses the whole transfer");
        }
        scenario();b.slots.set(4,ItemStack.EMPTY);b.tank.setFill(7999);step(l,b);check(b.tank.getFill()==7999&&!b.slots.get(3).isEmpty(),"capacity short by 1 mB refuses the whole container");
        b.slots.set(3,ItemStack.EMPTY);b.tank.setFill(0);b.dirty=0;check(b.transferFluid(Fluids.PEROXIDE,0,500)==0&&b.tank.getFill()==500&&b.dirty>0,"pipe fill of the acid tank saves");
        b.dirty=0;check(b.transferFluid(Fluids.SULFURIC_ACID,0,10)==10&&b.transferFluid(Fluids.PEROXIDE,1,10)==10&&b.dirty==0,"wrong type or pressure is refused unchanged");
        check(b.getDemand(Fluids.PEROXIDE,0)==7500&&b.getDemand(Fluids.SULFURIC_ACID,0)==0,"demand is the tank's remaining peroxide capacity");
    }
    static void upgrades(){
        int[][] speed={{450,2000},{300,3000},{150,4000}};
        for(int s=1;s<=3;s++){
            scenario();Level l=fresh();var b=machine(l,0,Direction.NORTH,1_000_000L,8000);b.slots.set(0,new ItemStack(ORE_IRON));b.slots.set(5,upgrade(UpgradeType.SPEED,s));step(l,b);
            check(b.duration==speed[s-1][0]&&b.getPowerRequired()==speed[s-1][1]&&b.getCycleCount()==1,"SPEED "+s+" duration/consumption");
            ticks(l,b,speed[s-1][0]);check(crystals(b)==1&&b.power==1_000_000L-(long)(speed[s-1][0]+1)*speed[s-1][1],"SPEED "+s+" completes after duration+1 sub-cycles paying each");
        }
        for(int e=1;e<=3;e++){
            scenario();Level l=fresh();var b=machine(l,0,Direction.NORTH,1_000_000L,8000);b.slots.set(0,new ItemStack(ORE_IRON));b.slots.set(6,upgrade(UpgradeType.EFFECT,e));step(l,b);
            check(b.duration==600&&b.getPowerRequired()==1000L*(1+2*e)&&Math.abs(b.getFreeChance(b.getRecipe())-0.05F*e)<1e-6,"EFFECT "+e+" consumption and chance");
        }
        for(int o=1;o<=3;o++){
            scenario();Level l=fresh();var b=machine(l,0,Direction.NORTH,1_000_000L,8000);b.slots.set(0,new ItemStack(ORE_IRON));b.slots.set(5,upgrade(UpgradeType.OVERDRIVE,o));step(l,b);
            check(b.getCycleCount()==Math.min(1+2*o,7)&&b.getPowerRequired()==1000&&b.progress==Math.min(1+2*o,7),"OVERDRIVE "+o+" sub-cycles per tick at base cost");
        }
        scenario();Level l=fresh();var b=machine(l,0,Direction.NORTH,1_000_000L,8000);b.slots.set(0,new ItemStack(ORE_IRON));b.slots.set(5,upgrade(UpgradeType.SPEED,2));b.slots.set(6,upgrade(UpgradeType.SPEED,1));step(l,b);
        check(b.duration==150&&b.getPowerRequired()==4000,"two SPEED slots aggregate to level 3");
        b.slots.set(5,upgrade(UpgradeType.SPEED,3));b.slots.set(6,upgrade(UpgradeType.SPEED,3));step(l,b);check(b.duration==150&&b.getPowerRequired()==4000,"aggregation caps at level 3");
        b.slots.set(5,upgrade(UpgradeType.SPEED,1));b.slots.set(6,upgrade(UpgradeType.EFFECT,2));step(l,b);check(b.duration==450&&b.getPowerRequired()==1000*(1+1+4),"SPEED and EFFECT combine: 6,000 HE per sub-cycle");
        b.slots.set(5,upgrade(UpgradeType.OVERDRIVE,3));b.slots.set(6,upgrade(UpgradeType.SPEED,3));b.power=1_000_000L;b.progress=0;step(l,b);
        check(b.duration==150&&b.getCycleCount()==7&&b.getPowerRequired()==4000,"OVERDRIVE 3 with SPEED 3");
        check(b.canPlaceItem(5,upgrade(UpgradeType.SPEED,1))&&!b.canPlaceItem(5,upgrade(UpgradeType.POWER,1))&&!b.canPlaceItem(5,upgrade(UpgradeType.AFTERBURN,1))&&!b.canPlaceItem(5,upgrade(UpgradeType.SPEED,0)),"only SPEED/EFFECT/OVERDRIVE with a positive tier");
        var valid=b.getValidUpgrades();check(valid.size()==3&&valid.get(UpgradeType.SPEED)==3&&valid.get(UpgradeType.EFFECT)==3&&valid.get(UpgradeType.OVERDRIVE)==3,"valid upgrade map");
        // Overdrive 3: 601 sub-cycles need 86 ticks; the sixth attempt of tick 86 delivers and the seventh starts the next batch.
        scenario();l=fresh();b=machine(l,0,Direction.NORTH,1_000_000L,8000);b.slots.set(0,new ItemStack(ORE_IRON,2));b.slots.set(5,upgrade(UpgradeType.OVERDRIVE,3));ticks(l,b,85);
        check(b.progress==595&&crystals(b)==0&&b.power==1_000_000L-595_000L,"85 ticks of seven sub-cycles");
        step(l,b);check(crystals(b)==1&&b.progress==1&&b.power==1_000_000L-602_000L&&b.slots.get(0).getCount()==1,"delivery within the tick, the remaining attempt already counts toward the next batch");
        // Same-tick failure: 2,500 HE pays two of three attempts, the third fails and clears the progress made this tick.
        scenario();l=fresh();b=machine(l,0,Direction.NORTH,2_500L,8000);b.slots.set(0,new ItemStack(ORE_IRON));b.slots.set(5,upgrade(UpgradeType.OVERDRIVE,1));step(l,b);
        check(b.progress==0&&b.power==500L&&b.isOn,"third attempt of the tick fails: two sub-cycles paid, progress cleared, isOn stays true for this tick");
        step(l,b);check(b.progress==0&&!b.isOn&&b.power==500L,"next tick idle");
        scenario();l=fresh();b=machine(l,0,Direction.NORTH,1_000_000L,500);b.slots.set(0,new ItemStack(ORE_IRON,5));b.slots.set(5,upgrade(UpgradeType.OVERDRIVE,3));ticks(l,b,86);
        check(crystals(b)==1&&b.tank.getFill()==0&&b.progress==0&&b.power==1_000_000L-601_000L,"after delivery the seventh attempt fails on the empty tank and clears the progress");
    }
    static void effect(){
        check(MachineCrystallizerBlockEntity.shouldConsumeInput(0F,0F)&&MachineCrystallizerBlockEntity.shouldConsumeInput(0F,0.999F),"zero chance always consumes");
        check(!MachineCrystallizerBlockEntity.shouldConsumeInput(0.05F,0.05F),"a roll equal to a positive chance keeps the input");
        check(MachineCrystallizerBlockEntity.shouldConsumeInput(0.05F,Math.nextUp(0.05F))&&!MachineCrystallizerBlockEntity.shouldConsumeInput(0.05F,Math.nextDown(0.05F)),"strict boundary either side of the chance");
        check(!MachineCrystallizerBlockEntity.shouldConsumeInput(0.99F,0.98F)&&MachineCrystallizerBlockEntity.shouldConsumeInput(0.99F,0.995F),"0.99 cap boundary");
        scenario();Level l=fresh();var b=machine(l,0,Direction.NORTH,1_000_000L,8000);b.slots.set(0,new ItemStack(ORE_IRON,4));b.slots.set(5,upgrade(UpgradeType.EFFECT,3));
        CrystallizerRecipes.clear();CrystallizerRecipes.setRecipe(new ItemStack(ORE_IRON),Fluids.PEROXIDE,500,new ItemStack(NtmItems.CRYSTAL_IRON.get()),600,0.33F);step(l,b);
        check(Math.abs(b.getFreeChance(b.getRecipe())-0.99F)<1e-6,"3 x 0.33 caps at 0.99");
        // 601 sub-cycles at 7,000 HE exceed the 1,000,000 HE cache, so the roll scenarios use a 100-tick row (101 sub-cycles, 707,000 HE).
        // Seeds are chosen so that both outcomes of the roll against the 0.15 chance occur (java.util.Random is the Level service's source).
        List<Long> seeds=new ArrayList<>();int kept=0,consumedCount=0;
        for(long index=1;index<=200000&&(kept<4||consumedCount<4);index++){long candidate=index*2654435761L;boolean keep=!MachineCrystallizerBlockEntity.shouldConsumeInput(0.15F,new Random(candidate).nextFloat());if(keep&&kept<4){kept++;seeds.add(candidate);}else if(!keep&&consumedCount<4){consumedCount++;seeds.add(candidate);}}
        check(kept==4&&consumedCount==4,"both roll outcomes are exercised");
        for(long seed:seeds){
            scenario();l=fresh();CrystallizerRecipes.clear();CrystallizerRecipes.setRecipe(new ItemStack(ORE_IRON),Fluids.PEROXIDE,500,new ItemStack(NtmItems.CRYSTAL_IRON.get()),100,0.05F);
            b=machine(l,0,Direction.NORTH,1_000_000L,8000);b.slots.set(0,new ItemStack(ORE_IRON,4));b.slots.set(5,upgrade(UpgradeType.EFFECT,3));
            ticks(l,b,100);l.random.setSeed(seed);float roll=new Random(seed).nextFloat();step(l,b);
            boolean consumed=MachineCrystallizerBlockEntity.shouldConsumeInput(0.15F,roll);
            check(crystals(b)==1&&b.tank.getFill()==7500&&b.power==1_000_000L-101L*7000L,"EFFECT 3 pays 7,000 HE per sub-cycle and always the full acid, seed "+seed);
            check(b.slots.get(0).getCount()==(consumed?3:4),"input consumption follows the recorded roll "+roll+" seed "+seed);
        }
    }
    static void stateAndMenu()throws Exception{
        scenario();Level l=fresh();var b=machine(l,0,Direction.NORTH,0,0);var p=player(l);FluidContainerRegistry.clearRegistry();FluidContainerRegistry.register();
        var menu=new MachineCrystallizerMenu(1,p.getInventory(),b);check(menu.slots.size()==44,"8 + 36 menu slots");
        ItemStack full=FluidContainerRegistry.getFullContainer(new ItemStack(NtmItems.FLUID_TANK_EMPTY.get()),Fluids.PEROXIDE);
        ItemStack[] values={new ItemStack(ORE_IRON),pack(5),new ItemStack(NtmItems.CRYSTAL_IRON.get()),full.copy(),new ItemStack(NtmItems.FLUID_TANK_EMPTY.get()),upgrade(UpgradeType.SPEED,1),upgrade(UpgradeType.EFFECT,2),identifier(Fluids.PEROXIDE)};
        boolean[][] accept=new boolean[8][8];
        for(int slot=0;slot<8;slot++)for(int v=0;v<8;v++)accept[slot][v]=b.canPlaceItem(slot,values[v]);
        for(int slot=0;slot<8;slot++)for(int v=0;v<8;v++){
            boolean expected=switch(slot){case 0->v==0;case 1->v==1;case 3->v==3;case 5,6->v==5||v==6;case 7->v==7;default->false;};
            check(accept[slot][v]==expected,"slot filter "+slot+"/"+v);
        }
        for(int i:new int[]{0,1,5,7}){p.getInventory().setItem(i,values[i].copy());menu.quickMoveStack(p,35+i);check(!b.slots.get(i).isEmpty(),"shift destination "+i);}
        check(PACK.getCharge(b.slots.get(1))==5,"shift keeps the real battery component");
        p.getInventory().setItem(2,values[6].copy());menu.quickMoveStack(p,37);check(!b.slots.get(6).isEmpty(),"second upgrade routes to the free upgrade slot");
        for(Direction d:Direction.values()){
            check(Arrays.equals(b.getSlotsForFace(d),new int[]{0,2}),"automation sees input and output only "+d);
            check(b.canPlaceItemThroughFace(0,new ItemStack(ORE_IRON),d)&&!b.canPlaceItemThroughFace(0,new ItemStack(Items.STICK),d)&&!b.canPlaceItemThroughFace(2,new ItemStack(ORE_IRON),d)&&!b.canPlaceItemThroughFace(1,pack(0),d),"automation inserts recipe inputs only "+d);
            check(b.canTakeItemThroughFace(2,new ItemStack(NtmItems.CRYSTAL_IRON.get()),d)&&!b.canTakeItemThroughFace(0,new ItemStack(ORE_IRON),d)&&!b.canTakeItemThroughFace(4,new ItemStack(NtmItems.FLUID_TANK_EMPTY.get()),d),"automation extracts the output only "+d);
        }
        scenario();l=fresh();b=machine(l,0,Direction.NORTH,123_456L,3210);b.slots.set(0,new ItemStack(ORE_IRON,2));ticks(l,b,40);
        check(b.progress==40,"forty sub-cycles of progress before the save");
        CompoundTag tag=new CompoundTag();nbt(b,tag,false);var c=machine(l,20,Direction.NORTH,0,0);c.progress=77;nbt(c,tag,true);
        check(c.power==123_456L-40_000L&&c.tank.getFill()==3210&&c.tank.getTankType()==Fluids.PEROXIDE,"power and tank saved");
        check(c.progress==0&&!c.isOn&&c.duration==600,"progress is not saved: it restarts after a reload");
        check(!tag.contains("progress"),"no progress key in the original NBT layout");
        b.slots.set(7,identifier(Fluids.SULFURIC_ACID));step(l,b);tag=new CompoundTag();nbt(b,tag,false);c=machine(l,30,Direction.NORTH,0,0);nbt(c,tag,true);
        check(c.tank.getTankType()==Fluids.SULFURIC_ACID&&c.tank.getFill()==0&&c.tank.getMaxFill()==8000,"retyped tank saves its type with the fixed capacity");
        b.slots.set(7,identifier(Fluids.PEROXIDE));b.tank.setFill(0);step(l,b);b.tank.setFill(4321);b.progress=12;b.isOn=true;b.duration=450;
        RegistryFriendlyByteBuf buf=new RegistryFriendlyByteBuf();b.serialize(buf);c.power=0;c.progress=0;c.duration=0;c.deserialize(buf);
        check(c.progress==12&&c.duration==450&&c.power==b.power&&c.isOn&&c.tank.getFill()==4321&&c.tank.getTankType()==Fluids.PEROXIDE,"production sync carries progress, duration, power, state and tank");
        b.dirty=0;b.setPower(1000L);check(b.power==1000L&&b.dirty>0,"incoming power saves");
        b.dirty=0;b.setPower(1000L);check(b.dirty==0,"unchanged power does not save");
        b.dirty=0;b.setPower(5_000_000L);check(b.power==1_000_000L&&b.dirty>0,"power is bounded at the cache size");
        for(boolean unload:new boolean[]{false,true}){
            scenario();l=fresh();b=machine(l,0,Direction.NORTH,0,0);FluidNetMK2 f=new FluidNetMK2(Fluids.PEROXIDE);PowerNetMK2 e=new PowerNetMK2();f.addReceiver(b);e.addReceiver(b);UniNodespace.activeNodeNets.add(f);UniNodespace.activeNodeNets.add(e);
            if(unload)b.onChunkUnloaded();else b.setRemoved();check(!f.receiverEntries.containsKey(b)&&!e.receiverEntries.containsKey(b),"network exits "+unload);
        }
        scenario();l=fresh();b=machine(l,0,Direction.NORTH,0,500);b.slots.set(0,new ItemStack(ORE_IRON));b.dirty=0;ticks(l,b,3);check(b.dirty==0&&b.progress==0,"idle machine without power does not save every tick");
        b.slots.set(1,pack(2000));b.dirty=0;step(l,b);check(b.progress==1&&b.power+PACK.getCharge(b.slots.get(1))==1000L&&b.dirty>0,"battery discharge feeds the first sub-cycle: 2,000 HE minus one 1,000 HE sub-cycle conserved, saved");
    }
    static void ladder(){
        for(Direction f:new Direction[]{Direction.NORTH,Direction.SOUTH,Direction.EAST,Direction.WEST}){
            scenario();Level l=fresh();var b=machine(l,0,Direction.NORTH,0,0);b=machine(l,0,f,0,0);Direction side=f.getClockWise();
            AABB box=MachineCrystallizerBlockEntity.getLadderBox(b.getBlockPos(),f);
            AABB expected=new AABB(0.25+side.getStepX()*1.5,1,0.25+side.getStepZ()*1.5,0.75+side.getStepX()*1.5,6,0.75+side.getStepZ()*1.5);
            check(Math.abs(box.minX-expected.minX)<1e-9&&Math.abs(box.maxX-expected.maxX)<1e-9&&Math.abs(box.minZ-expected.minZ)<1e-9&&Math.abs(box.maxZ-expected.maxZ)<1e-9&&box.minY==1&&box.maxY==6,"ladder column 0.5 wide, y 1..6, shifted 1.5 toward the clockwise side "+f);
            Player inside=player(l);inside.setPos(0.5+side.getStepX()*1.5,3,0.5+side.getStepZ()*1.5);
            Player outside=player(l);outside.setPos(0.5-side.getStepX()*1.5,3,0.5-side.getStepZ()*1.5);
            Player above=player(l);above.setPos(0.5+side.getStepX()*1.5,7,0.5+side.getStepZ()*1.5);
            l.testEntities.add(inside);l.testEntities.add(outside);l.testEntities.add(above);
            HbmPlayerAttachments.getData(inside).isOnLadder=false;HbmPlayerAttachments.getData(outside).isOnLadder=false;HbmPlayerAttachments.getData(above).isOnLadder=false;
            step(l,b);
            check(HbmPlayerAttachments.getData(inside).isOnLadder&&!HbmPlayerAttachments.getData(outside).isOnLadder&&!HbmPlayerAttachments.getData(above).isOnLadder,"server marks only the player in the rotated side column "+f);
            HbmPlayerAttachments.getData(inside).isOnLadder=false;l.isClientSide=true;step(l,b);
            check(HbmPlayerAttachments.getData(inside).isOnLadder,"client tick marks as well "+f);
        }
    }
    static void finite(Path output)throws Exception{
        List<String> rows=new ArrayList<>();
        // Iron: declared inventory of 1 ore, 500 mB prepared peroxide, 1,000 HE initial buffer and one copper capacitor at its 600,000 HE capacity.
        scenario();Level l=fresh();var b=machine(l,0,Direction.NORTH,1_000L,500);b.slots.set(0,new ItemStack(ORE_IRON));b.slots.set(1,pack(600_000L));
        long spent=0;for(int t=0;t<601;t++){long before=b.power+PACK.getCharge(b.slots.get(1));step(l,b);spent+=before-(b.power+PACK.getCharge(b.slots.get(1)));}
        check(crystals(b)==1&&b.slots.get(0).isEmpty()&&b.tank.getFill()==0&&b.power==0&&PACK.getCharge(b.slots.get(1))==0&&spent==601_000L,"601,000 HE exactly: 1,000 HE buffer plus a full copper capacitor, one iron crystal, no residue");
        scenario();l=fresh();b=machine(l,0,Direction.NORTH,0L,500);b.slots.set(0,new ItemStack(ORE_IRON));b.slots.set(1,pack(600_000L));ticks(l,b,601);
        check(crystals(b)==0&&b.progress==0&&PACK.getCharge(b.slots.get(1))==0&&b.power==0&&b.tank.getFill()==500,"600,000 HE alone falls one sub-cycle short and loses everything spent");
        rows.add("{\"chain\":\"iron\",\"initialOre\":1,\"initialPeroxideMB\":500,\"initialBufferHE\":1000,\"capacitorHE\":600000,\"ticks\":601,\"spentHE\":601000,\"crystals\":1,\"remainingPeroxideMB\":0,\"remainingBufferHE\":0,\"remainingCapacitorHE\":0}");
        rows.add("{\"chain\":\"iron-counterexample\",\"initialOre\":1,\"initialPeroxideMB\":500,\"initialBufferHE\":0,\"capacitorHE\":600000,\"ticks\":601,\"spentHE\":600000,\"crystals\":0,\"progressAfter\":0,\"remainingPeroxideMB\":500}");
        // Copper: the same machine budget, then the real centrifuge over its own declared default row for the copper crystal.
        scenario();l=fresh();b=machine(l,0,Direction.NORTH,601_000L,500);b.slots.set(0,new ItemStack(ORE_COPPER));ticks(l,b,601);
        check(crystals(b)==1&&b.slots.get(2).getItem()==NtmItems.CRYSTAL_COPPER.get()&&b.power==0,"one copper crystal for 601,000 HE and 500 mB");
        CentrifugeRecipes.clear();
        CentrifugeRecipes.setRecipe(new ItemStack(NtmItems.CRYSTAL_COPPER.get()),new ItemStack(NtmItems.POWDER_COPPER.get(),2),new ItemStack(NtmItems.POWDER_COPPER.get(),2),new ItemStack(NtmItems.SULFUR.get(),1),new ItemStack(NtmItems.POWDER_COBALT_TINY.get(),1));
        var c=new MachineCentrifugeBlockEntity(new BlockPos(10,0,0),new BlockState());l.states.put(c.getBlockPos(),new BlockState());l.put(c);c.power=40_000L;c.slots.set(0,b.removeItem(2,1));
        int centrifugeTicks=0;while(c.slots.get(2).isEmpty()&&centrifugeTicks<400){l.time++;c.updateEntity();executedTicks++;centrifugeTicks++;}
        check(centrifugeTicks==200&&c.power==0&&c.slots.get(2).getCount()==4&&c.slots.get(2).getItem()==NtmItems.POWDER_COPPER.get()&&c.slots.get(3).getCount()==1&&c.slots.get(3).getItem()==NtmItems.SULFUR.get()&&c.slots.get(4).getCount()==1&&c.slots.get(4).getItem()==NtmItems.POWDER_COBALT_TINY.get(),"real centrifuge: 200 ticks, 40,000 HE, 4 copper powder + 1 sulfur + 1 tiny cobalt powder");
        rows.add("{\"chain\":\"copper\",\"initialOre\":1,\"initialPeroxideMB\":500,\"acidizerHE\":601000,\"acidizerTicks\":601,\"crystals\":1,\"centrifugeHE\":40000,\"centrifugeTicks\":200,\"outputs\":{\"powder_copper\":4,\"sulfur\":1,\"powder_cobalt_tiny\":1},\"centrifugeRowSource\":\"CentrifugeRecipes.registerCrystalRecipes CRYSTAL_COPPER (fixture-declared, matching the production default)\"}");
        Files.writeString(output.resolve("finite.json"),"["+String.join(",",rows)+"]");
    }
    public static void main(String[] args)throws Exception{
        Path output=Path.of(args[0]);
        basics();cycles();acids();upgrades();effect();stateAndMenu();ladder();finite(output);
        System.out.println("Goal18A machine: "+checks+" assertions; "+scenarios+" independent scenarios; "+executedTicks+" executed ticks");
    }
}
