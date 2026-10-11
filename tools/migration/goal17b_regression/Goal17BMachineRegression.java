package com.hbm.blockentity.machine;

import api.hbm.fluidmk2.*;
import api.hbm.energymk2.*;
import com.hbm.blockentity.machine.oil.MachineFractionTowerBlockEntity;
import com.hbm.blocks.DummyableBlock;
import com.hbm.handler.pollution.PollutionHandler;
import com.hbm.handler.pollution.PollutionHandler.PollutionType;
import com.hbm.inventory.*;
import com.hbm.inventory.fluid.*;
import com.hbm.inventory.fluid.trait.*;
import com.hbm.inventory.fluid.trait.FT_Combustible.FuelGrade;
import com.hbm.inventory.menus.MachineTurbofanMenu;
import com.hbm.inventory.recipes.*;
import com.hbm.items.NtmItems;
import com.hbm.items.component.NtmDataComponents;
import com.hbm.items.machine.*;
import com.hbm.items.machine.MachineUpgradeItem.UpgradeType;
import com.hbm.uninos.*;
import net.minecraft.core.*;
import net.minecraft.nbt.*;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.world.item.*;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import java.nio.file.*;
import java.util.*;

/** Production ticks, finite inputs and conservation; engine services are explicit. */
public class Goal17BMachineRegression extends Goal14CMachineRegression {
    static int executedTicks;
    static Level fresh(){Level l=world();Fluids.initializeGoal17BFuels();PollutionHandler.reset();Fluids.WATER.traits.remove(FT_Combustible.class);Fluids.WATER.traits.remove(FT_Polluting.class);return l;}
    static MachineTurbofanBlockEntity turbine(Level l,int x,Direction facing,int a,FluidType type,int fill){
        BlockPos p=new BlockPos(x,0,0);BlockState s=new BlockState().setValue(DummyableBlock.FACING,facing);
        var b=new MachineTurbofanBlockEntity(p,s);l.states.put(p,s);l.put(b);b.tank.setTankType(type);b.tank.setFill(fill);
        if(a>0)b.slots.set(2,upgrade(UpgradeType.AFTERBURN,a));return b;
    }
    static void step(Level l,MachineTurbofanBlockEntity b){l.time++;b.updateEntity();executedTicks++;}
    static void matrix(){
        scenario();Level l=fresh();var b=turbine(l,0,Direction.NORTH,0,Fluids.KEROSENE,0);
        check(b.getContainerSize()==5&&b.getMaxPower()==1000000&&b.tank.getMaxFill()==24000&&b.blood.getMaxFill()==24000,"five slots and real capacity");
        check(b.smoke.getMaxFill()==150&&b.smokeLeaded.getMaxFill()==150&&b.smokePoison.getMaxFill()==150,"three 150mB smoke caches");
        check(Fluids.KEROSENE.getTrait(FT_Combustible.class).getCombustionEnergy()==3850000L&&MachineTurbofanBlockEntity.getBurnValue(Fluids.KEROSENE)==3850,"final calculated kerosene3850");
        int[] full={3850,10266,19250,30800};
        for(int a=0;a<=3;a++)for(int fill:new int[]{0,1,2,3,4,10}){
            scenario();l=fresh();b=turbine(l,0,Direction.NORTH,a,Fluids.KEROSENE,fill);step(l,b);
            int burned=Math.min(a+1,fill);int expected=(int)(3850L*burned*(1+a/3D));
            check(b.output==expected&&b.power==expected&&b.consumption==burned&&b.tank.getFill()==fill-burned,"A"+a+" remaining"+fill);
            check(b.wasOn==(burned>0),"wasOn matches actual fuel");if(fill>=a+1)check(b.output==full[a],"ordinary exact A"+a);
        }
        for(FuelGrade grade:FuelGrade.values()){
            scenario();l=fresh();Fluids.WATER.addTraits(new FT_Combustible(grade,1234999));b=turbine(l,0,Direction.NORTH,2,Fluids.WATER,3);step(l,b);
            check(b.tank.getFill()==0&&b.consumption==3&&b.wasOn,"even nonAERO consumes "+grade);
            check(b.power==(grade==FuelGrade.AERO?6169:0),"grade gate then division before multiplication "+grade);
        }
        scenario();l=fresh();b=turbine(l,0,Direction.NORTH,3,Fluids.WATER,4);step(l,b);
        check(b.tank.getFill()==0&&b.power==0&&b.wasOn,"noncombustible still consumed");
        for(Direction facing:new Direction[]{Direction.NORTH,Direction.SOUTH,Direction.EAST,Direction.WEST}){
            for(int port=0;port<4;port++){
                scenario();l=fresh();b=turbine(l,0,facing,3,Fluids.KEROSENE,10);l.powered.add(b.getConPos()[port].makeCompat());step(l,b);
                check(b.tank.getFill()==10&&b.power==0&&!b.wasOn&&b.redstonePowered,"each external redstone stops burn "+facing+port);
            }
            scenario();l=fresh();b=turbine(l,0,facing,3,Fluids.KEROSENE,4);l.powered.add(b.getBlockPos());step(l,b);
            check(b.output==30800,"core position is not external redstone input "+facing);
        }
        for(Direction f:new Direction[]{Direction.NORTH,Direction.SOUTH,Direction.EAST,Direction.WEST}){
            scenario();l=fresh();b=turbine(l,0,f,0,Fluids.KEROSENE,0);Direction intake=Goal17BEntityRegression.axis(f);
            BlockPos core=b.getBlockPos();Set<BlockPos> expected=Set.of(core.relative(f,2),core.relative(f,2).relative(intake.getOpposite()),core.relative(f.getOpposite(),2),core.relative(f.getOpposite(),2).relative(intake.getOpposite()));
            Set<BlockPos> actual=new HashSet<>();for(var connection:b.getConPos())actual.add(connection.makeCompat());
            check(actual.equals(expected),"four independently expected external neighbors "+f);
        }
        scenario();l=fresh();b=turbine(l,0,Direction.NORTH,3,Fluids.KEROSENE,8);b.power=1000000;b.slots.set(3,pack(0));b.dirty=0;step(l,b);
        check(b.tank.getFill()==4&&PACK.getCharge(b.slots.get(3))==1000&&b.power==1000000&&b.dirty>0,"full cache burns and charges before cap");
        scenario();l=fresh();b=turbine(l,0,Direction.NORTH,3,Fluids.KEROSENE,4);b.power=1000000-30000;b.slots.set(3,pack(0));step(l,b);
        check(b.power==999800&&PACK.getCharge(b.slots.get(3))==1000,"overflow800 stays available for1000 charge before clamp");
        scenario();l=fresh();b=turbine(l,0,Direction.NORTH,3,Fluids.KEROSENE,4);l.isClientSide=true;step(l,b);
        check(b.power==0&&b.tank.getFill()==4,"client does not burn");
    }
    static void pollution()throws Exception{
        for(int a:new int[]{0,3}){
            scenario();Level l=fresh();var b=turbine(l,0,Direction.NORTH,a,Fluids.KEROSENE,2000);
            var trait=Fluids.KEROSENE.getTrait(FT_Polluting.class);
            check(trait.burnMap.size()==1&&trait.burnMap.containsKey(PollutionType.SOOT)&&trait.releaseMap.containsKey(PollutionType.POISON),"real P_FUEL burn/release maps");
            l.time=18;step(l,b);check(b.smoke.getFill()==0,"non20 active no smoke");step(l,b);
            check(b.smoke.getFill()==1&&b.smokeLeaded.getFill()==0&&b.smokePoison.getFill()==0&&PollutionHandler.CALLS.isEmpty(),"ceil tiny real soot, independent of burnt mB A"+a);
            b.smoke.setFill(149);l.time=39;step(l,b);check(b.smoke.getFill()==150&&PollutionHandler.CALLS.isEmpty(),"exact full has no pollution");
            l.time=59;step(l,b);check(b.smoke.getFill()==150&&PollutionHandler.CALLS.size()==1&&Math.abs(PollutionHandler.CALLS.get(0).amount()-.01F)<1e-6,"only1mB overflow /100");
            l.powered.add(b.getConPos()[0].makeCompat());l.time=79;step(l,b);check(PollutionHandler.CALLS.size()==1,"redstone20 no pollution");
        }
        scenario();Level l=fresh();Fluids.WATER.addTraits(new FT_Polluting().burn(PollutionType.SOOT,.0121F).burn(PollutionType.HEAVYMETAL,1.49F).burn(PollutionType.POISON,1.501F));
        var b=turbine(l,0,Direction.NORTH,3,Fluids.WATER,100);l.time=19;step(l,b);
        check(b.smoke.getFill()==2&&b.smokeLeaded.getFill()==149&&b.smokePoison.getFill()==150,"synthetic three-map individual ceil and cap");
        check(PollutionHandler.CALLS.size()==1&&PollutionHandler.CALLS.get(0).type()==PollutionType.POISON&&Math.abs(PollutionHandler.CALLS.get(0).amount()-.01F)<1e-6,"synthetic poison151 only1overflow");
        check(b.getAllTanks().length==5&&b.getSendingTanks().length==1&&b.getSendingTanks()[0]==b.blood,"All does not imply smoke output");
        check(b.getFluidAvailable(Fluids.SMOKE,0)==0&&b.getFluidAvailable(Fluids.SMOKE_LEADED,0)==0&&b.getFluidAvailable(Fluids.SMOKE_POISON,0)==0,"actual sender excludes smoke");
        CompoundTag tag=new CompoundTag();nbt(b,tag,false);var c=turbine(l,20,Direction.NORTH,0,Fluids.KEROSENE,0);nbt(c,tag,true);
        check(c.smoke.getFill()==2&&c.smokeLeaded.getFill()==149&&c.smokePoison.getFill()==150,"real smoke NBT roundtrip");
        scenario();c.tank.setTankType(Fluids.SMOKE);c.tank.setFill(0);fluid(b,c,Fluids.SMOKE,0,0);check(c.tank.getFill()==0&&b.smoke.getFill()==2,"actual FluidNet cannot output smoke cache");
    }
    static void inventoryState()throws Exception{
        scenario();Level l=fresh();var b=turbine(l,0,Direction.NORTH,0,Fluids.KEROSENE,0);var p=player(l);
        var menu=new MachineTurbofanMenu(1,p.getInventory(),b);check(menu.slots.size()==41,"5+36 menu slots");
        ItemStack full=FluidContainerRegistry.getFullContainer(new ItemStack(NtmItems.FLUID_TANK_EMPTY.get()),Fluids.KEROSENE);
        ItemStack[] values={full.copy(),new ItemStack(NtmItems.CANISTER_EMPTY.get()),upgrade(UpgradeType.AFTERBURN,3),pack(123),identifier(Fluids.DIESEL)};
        for(int slot=0;slot<5;slot++)for(int v=0;v<5;v++)check(b.canPlaceItem(slot,values[v])==(slot!=1&&slot==v),"five distinct filters "+slot+"/"+v);
        for(int i:new int[]{0,2,3,4}){p.getInventory().setItem(i,values[i]);menu.quickMoveStack(p,32+i);check(!b.slots.get(i).isEmpty(),"shift destination "+i);}
        check(PACK.getCharge(b.slots.get(3))==123,"shift keeps real battery component");
        check(!b.canPlaceItem(2,upgrade(UpgradeType.AFTERBURN,0))&&!b.canPlaceItem(2,upgrade(UpgradeType.AFTERBURN,4))&&!b.canPlaceItem(2,upgrade(UpgradeType.SPEED,3)),"ordinary afterburn only1..3");
        for(Direction d:Direction.values())check(b.getSlotsForFace(d).length==0&&!b.canTakeItemThroughFace(3,values[3],d),"original no sided slots "+d);
        full.set(NtmDataComponents.COLTAN_Z.get(),7);scenario();l=fresh();b=turbine(l,0,Direction.NORTH,0,Fluids.KEROSENE,0);l.powered.add(b.getConPos()[0].makeCompat());b.slots.set(0,full.copy());b.dirty=0;step(l,b);
        check(b.tank.getFill()==1000&&b.slots.get(0).isEmpty()&&!b.slots.get(1).isEmpty()&&Objects.equals(b.slots.get(1).get(NtmDataComponents.COLTAN_Z.get()),7)&&b.dirty>0,"container loads while redstone stopped and saves components");
        for(ItemStack bad:new ItemStack[]{new ItemStack(NtmItems.FLUID_TANK_EMPTY.get(),64),new ItemStack(Items.STICK)}){
            scenario();b.slots.set(0,full.copy());b.slots.set(1,bad);step(l,b);check(b.tank.getFill()==1000&&!b.slots.get(0).isEmpty(),"atomic wrong/full return");
        }
        scenario();b.slots.set(0,full.copy());ItemStack mismatched=new ItemStack(NtmItems.FLUID_TANK_EMPTY.get());mismatched.set(NtmDataComponents.COLTAN_Z.get(),8);b.slots.set(1,mismatched);step(l,b);check(b.tank.getFill()==1000&&!b.slots.get(0).isEmpty(),"same empty identity different components refuses atomic conversion");
        scenario();b.slots.set(1,ItemStack.EMPTY);b.tank.setFill(23999);step(l,b);check(b.tank.getFill()==23999&&!b.slots.get(0).isEmpty(),"capacity difference1 rejects whole container");
        b.slots.set(0,ItemStack.EMPTY);b.tank.setFill(0);b.dirty=0;check(b.transferFluid(Fluids.KEROSENE,0,123)==0&&b.dirty>0,"idle pipe fill dirty");
        b.dirty=0;check(b.transferFluid(Fluids.DIESEL,0,10)==10&&b.transferFluid(Fluids.KEROSENE,1,10)==10&&b.dirty==0,"wrong type/pressure unchanged");
        b.power=123456;b.blood.setFill(234);b.showBlood=true;
        CompoundTag tag=new CompoundTag();nbt(b,tag,false);var c=turbine(l,20,Direction.NORTH,0,Fluids.KEROSENE,0);nbt(c,tag,true);
        check(c.power==123456&&c.tank.getFill()==123&&c.blood.getFill()==234&&c.showBlood,"powerTime/fuel/blood/showBlood real NBT");
        RegistryFriendlyByteBuf buf=new RegistryFriendlyByteBuf();b.serialize(buf);c.power=0;c.deserialize(buf);
        check(c.power==123456&&c.tank.getFill()==123&&c.blood.getFill()==234&&c.showBlood,"production sync roundtrip");
        b.dirty=0;b.setPower(123450);check(b.dirty>0,"power outgoing mutation dirty");
        b.dirty=0;b.useUpFluid(Fluids.BLOOD,0,50);check(b.blood.getFill()==184&&b.dirty>0,"blood sending dirty");
        scenario();c.tank.setTankType(Fluids.BLOOD);c.tank.setFill(0);b.dirty=0;fluid(b,c,Fluids.BLOOD,0,184);check(c.tank.getFill()==184&&b.blood.getFill()==0&&b.dirty>0,"actual blood network output dirty");
        FluidNetMK2 old=new FluidNetMK2(Fluids.KEROSENE);old.addReceiver(b);UniNodespace.activeNodeNets.add(old);b.slots.set(4,identifier(Fluids.DIESEL));b.dirty=0;step(l,b);
        check(!old.receiverEntries.containsKey(b)&&b.tank.getTankType()==Fluids.DIESEL&&b.tank.getFill()==0&&b.dirty>0,"retype clears old membership and saves");
        for(boolean unload:new boolean[]{false,true}){
            scenario();l=fresh();b=turbine(l,0,Direction.NORTH,0,Fluids.KEROSENE,0);FluidNetMK2 f=new FluidNetMK2(Fluids.KEROSENE);PowerNetMK2 e=new PowerNetMK2();f.addReceiver(b);e.addProvider(b);UniNodespace.activeNodeNets.add(f);UniNodespace.activeNodeNets.add(e);
            if(unload)b.onChunkUnloaded();else b.setRemoved();check(!f.receiverEntries.containsKey(b)&&!e.providerEntries.containsKey(b),"network exits "+unload);
        }
    }
    static void finite(Path output)throws Exception{
        List<String> rows=new ArrayList<>();
        for(int speed:new int[]{2,3}){
            scenario();Level l=fresh();new FractionRecipes().deleteRecipes();new FractionRecipes().registerDefaults();new ArcFurnaceRecipes().deleteRecipes();new ArcFurnaceRecipes().registerDefaults();
            var tower=new MachineFractionTowerBlockEntity(new BlockPos(20,0,0),new BlockState());l.put(tower);tower.tanks[0].setTankType(Fluids.LIGHTOIL);tower.tanks[0].setFill(4000);
            for(int t=0;t<400;t++){l.time=t+1;tower.updateEntity();executedTicks++;}
            check(tower.tanks[0].getFill()==0&&tower.tanks[1].getFill()==1600&&tower.tanks[2].getFill()==2400,"real4000LIGHTOIL ->1600diesel+2400kerosene, zero tower electric cost");
            var b=turbine(l,0,Direction.NORTH,3,Fluids.KEROSENE,0);fluid(tower,b,Fluids.KEROSENE,0,2400);b.slots.set(3,pack(0));
            var f=new MachineArcFurnaceBlockEntity(new BlockPos(40,0,0),new BlockState());l.put(f);for(int i=0;i<3;i++)f.slots.set(i,new ItemStack(NtmItems.ARC_ELECTRODE_GRAPHITE.get()));f.slots.set(4,upgrade(UpgradeType.SPEED,speed));f.slots.set(5,new ItemStack(Items.FLINT));f.lid=0;
            PowerNetMK2 network=new PowerNetMK2();long gross=0,spent=0,discarded=0;int burned=0,active=0,blocked=0;
            for(int t=0;t<81;t++){long before=b.power,charge=PACK.getCharge(b.slots.get(3));int previous=b.tank.getFill();step(l,b);gross+=b.output;burned+=previous-b.tank.getFill();discarded+=before+b.output-b.power-(PACK.getCharge(b.slots.get(3))-charge);network.addProvider(b);network.addReceiver(f);network.update();before=f.power;f.updateEntity();executedTicks++;long use=before-f.power;spent+=use;if(use>0)active++;else if(f.hasIngredients()&&f.hasElectrodes()&&f.delay<=0)blocked++;}
            long charged=PACK.getCharge(b.slots.get(3)),buffers=b.power+f.power;
            check(PACK.getMaxCharge(b.slots.get(3))==600000&&PACK.getChargeRate(b.slots.get(3))==1000,"real copper capacitor600000capacity1000rate");
            check(gross==spent+discarded+charged+buffers,"finite energy conservation "+speed);
            check(burned==324&&b.tank.getFill()==2076&&tower.tanks[1].getFill()==1600,"finite fuel/byproduct conservation");
            check(f.getConsumption()==(speed==2?25000:125000),"actual ArcFurnace load tier");
            if(speed==2)check(active==81&&blocked==0&&!f.slots.get(5).is(Items.FLINT),"A3 supports actual25000 under finite stated conditions");
            else check(active<81&&blocked>0,"125000 actual consumer undersupplied");
            rows.add("{\"loadHEt\":"+f.getConsumption()+",\"initialPreparedLightoilMB\":4000,\"fractionTicks\":400,\"fractionElectricHE\":0,\"keroseneProducedMB\":2400,\"keroseneBurnedMB\":"+burned+",\"keroseneRemainingMB\":"+b.tank.getFill()+",\"dieselRemainingMB\":1600,\"initialHE\":0,\"grossHE\":"+gross+",\"loadHE\":"+spent+",\"batteryHE\":"+charged+",\"discardedHE\":"+discarded+",\"finalBuffersHE\":"+buffers+",\"turbofanBufferHE\":"+b.power+",\"consumerBufferHE\":"+f.power+",\"batteryType\":\"capacitor_copper\",\"batteryCapacityHE\":"+PACK.getMaxCharge(b.slots.get(3))+",\"batteryRateHEt\":"+PACK.getChargeRate(b.slots.get(3))+",\"initialGraphiteElectrodes\":3,\"initialFlint\":1,\"afterburnLevel\":3,\"consumerSpeedLevel\":"+speed+",\"activeTicks\":"+active+",\"underSuppliedTicks\":"+blocked+"}");
        }
        scenario();Level l=fresh();var b=turbine(l,0,Direction.NORTH,3,Fluids.KEROSENE,9);long gross=0;
        for(int t=0;t<4;t++){step(l,b);gross+=b.output;}check(b.tank.getFill()==0&&b.consumption==0&&!b.wasOn&&gross==69300&&b.power==gross,"finite9mB tail then empty conservation");
        scenario();l=fresh();b=turbine(l,0,Direction.NORTH,3,Fluids.KEROSENE,800);gross=0;long discarded=0;
        for(int t=0;t<201;t++){long before=b.power;step(l,b);gross+=b.output;discarded+=before+b.output-b.power;}
        check(b.tank.getFill()==0&&b.power==1000000&&gross==6160000&&discarded==5160000,"finite800mB full cache intentional waste conserved");
        rows.add("{\"case\":\"full-cache-no-load\",\"initialKeroseneMB\":800,\"initialHE\":0,\"grossHE\":"+gross+",\"discardedHE\":"+discarded+",\"finalBuffersHE\":"+b.power+"}");
        Files.writeString(output.resolve("finite.json"),"["+String.join(",",rows)+"]");
    }
    public static void main(String[] args)throws Exception{
        FluidContainerRegistry.register();matrix();pollution();inventoryState();finite(Path.of(args[0]));
        System.out.println("Goal17B machines: "+checks+" assertions; "+scenarios+" independent scenarios; "+executedTicks+" executed ticks");
    }
}
