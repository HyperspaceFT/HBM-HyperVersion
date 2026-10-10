package com.hbm.blockentity.machine;

import com.hbm.blockentity.LoadedBaseBlockEntity;
import com.hbm.blockentity.machine.oil.*;
import com.hbm.inventory.FluidStack;
import com.hbm.inventory.fluid.*;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.recipes.FractionRecipes;
import com.hbm.uninos.UniNodespace;
import com.hbm.util.Tuple.Pair;
import net.minecraft.core.*;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import java.lang.reflect.Method;
import java.nio.file.*;
import java.util.*;

/** Whole production machines with isolated Level, registries and transport services. */
public class Goal14BMachineRegression {
    static int checks;
    static void check(boolean v,String m){if(!v)throw new AssertionError(m);checks++;}
    static Level world(){UniNodespace.levels.clear();UniNodespace.activeNodeNets.clear();Level l=new Level();l.manualClock=true;l.time=1;new FractionRecipes().deleteRecipes();new FractionRecipes().registerDefaults();return l;}
    static MachineFractionTowerBlockEntity tower(Level l,int x,int y){BlockPos p=new BlockPos(x,y,0);BlockState s=new BlockState();MachineFractionTowerBlockEntity b=new MachineFractionTowerBlockEntity(p,s);l.states.put(p,s);l.put(b);return b;}
    static Player player(Level l){Player p=new Player();p.world=l;p.level=l;return p;}
    static void tick(Level l,MachineFractionTowerBlockEntity b,long t){l.time=t;b.updateEntity();}
    static int sum(MachineFractionTowerBlockEntity... bs){int n=0;for(var b:bs)for(var t:b.tanks)n+=t.getFill();return n;}
    static void nbt(LoadedBaseBlockEntity b,CompoundTag t,boolean load)throws Exception{Class<?> c=b.getClass();while(c!=null){try{Method m=c.getDeclaredMethod(load?"loadAdditional":"saveAdditional",CompoundTag.class,HolderLookup.Provider.class);m.setAccessible(true);m.invoke(b,t,null);return;}catch(NoSuchMethodException e){c=c.getSuperclass();}}throw new AssertionError("NBT missing");}
    static void single(){
        Level l=world();var b=tower(l,0,0);
        check(b.tanks.length==3&&b.tanks[0].getTankType()==Fluids.HEAVYOIL&&b.tanks[1].getTankType()==Fluids.BITUMEN&&b.tanks[2].getTankType()==Fluids.SMEAR,"triple defaults");
        for(var t:b.tanks)check(t.getMaxFill()==4000,"4000 capacity");
        for(int input:new int[]{0,99}){b.tanks[0].setFill(input);tick(l,b,10);check(b.tanks[0].getFill()==input&&b.tanks[1].getFill()==0&&b.tanks[2].getFill()==0,"below100 atomic "+input);}
        b.tanks[0].setFill(100);tick(l,b,9);check(b.tanks[0].getFill()==100&&b.tanks[1].getFill()==0,"10tick gate");
        b.dirty=0;tick(l,b,10);check(b.tanks[0].getFill()==0&&b.tanks[1].getFill()==30&&b.tanks[2].getFill()==70&&b.dirty>0,"100 atomic and dirty");
        b.tanks[0].setFill(100);b.tanks[1].setFill(3970);b.tanks[2].setFill(3930);tick(l,b,20);check(b.tanks[1].getFill()==4000&&b.tanks[2].getFill()==4000&&b.tanks[0].getFill()==0,"both exact capacity");
        b.tanks[0].setFill(100);tick(l,b,20);check(b.tanks[0].getFill()==100&&b.tanks[1].getFill()==4000&&b.tanks[2].getFill()==4000,"dual full pauses atomically");
        for(int which=1;which<=2;which++){b.tanks[0].setFill(100);b.tanks[1].setFill(which==1?3971:0);b.tanks[2].setFill(which==2?3931:0);int old=sum(b);tick(l,b,30);check(b.tanks[0].getFill()==100&&sum(b)==old,"overflow gate "+which);}
        b.tanks[1].setFill(0);b.tanks[2].setFill(0);tick(l,b,40);check(b.tanks[0].getFill()==0&&sum(b)==100,"capacity recovery");
        b.tanks[0].setTankType(Fluids.WATER);for(int i=0;i<3;i++){b.tanks[i].withPressure(i+1);b.tanks[i].setFill(42);}tick(l,b,50);
        for(int i=0;i<3;i++)check(b.tanks[i].getTankType()==Fluids.NONE&&b.tanks[i].getFill()==0&&b.tanks[i].getPressure()==i+1,"missing recipe clears amount keeps pressure "+i);
        b.changeInputType(Fluids.HEAVYOIL,player(l));tick(l,b,51);check(b.tanks[1].getTankType()==Fluids.BITUMEN&&b.tanks[2].getTankType()==Fluids.SMEAR,"missing recipe recovery");
        FractionRecipes.fractions.put(Fluids.HEAVYOIL,new Pair<>(new FluidStack(Fluids.BITUMEN,Integer.MAX_VALUE),new FluidStack(Fluids.SMEAR,70)));b.tanks[0].setFill(100);b.tanks[1].setFill(1);tick(l,b,60);check(b.tanks[0].getFill()==100,"custom integer overflow refused");
        FractionRecipes.fractions.put(Fluids.HEAVYOIL,new Pair<>(new FluidStack(Fluids.BITUMEN,-1),new FluidStack(Fluids.SMEAR,101)));tick(l,b,70);check(b.tanks[0].getFill()==100,"negative custom quantity refused");
    }
    static void stacking(){
        Level l=world();var lower=tower(l,0,0);var upper=tower(l,0,3);
        lower.tanks[0].setFill(150);upper.tanks[0].setFill(3950);upper.tanks[1].setFill(100);upper.tanks[2].setFill(100);lower.tanks[1].setFill(3990);lower.tanks[2].setFill(3995);int total=sum(lower,upper);lower.dirty=upper.dirty=0;tick(l,lower,1);
        check(lower.tanks[0].getFill()==100&&upper.tanks[0].getFill()==4000&&lower.tanks[1].getFill()==4000&&upper.tanks[1].getFill()==90&&lower.tanks[2].getFill()==4000&&upper.tanks[2].getFill()==95,"bounded upward input downward outputs");
        check(sum(lower,upper)==total,"stack transfers conserve");check(lower.dirty>0&&upper.dirty>0,"both entities dirty");
        upper.tanks[0].setTankType(Fluids.NAPHTHA);upper.tanks[0].withPressure(5);upper.tanks[0].setFill(10);lower.tanks[0].setFill(0);tick(l,lower,2);check(upper.tanks[0].getTankType()==Fluids.HEAVYOIL&&upper.tanks[0].getFill()==0&&upper.tanks[0].getPressure()==5,"stack type reset keeps pressure");
        check(!upper.changeInputType(Fluids.LIGHTOIL,player(l))&&upper.tanks[0].getTankType()==Fluids.HEAVYOIL,"bottom restriction");
        CompoundTag settings=new CompoundTag();settings.putIntArray("FluidID",new int[]{Fluids.NAPHTHA.getID()});upper.pasteSettings(settings,0,l,player(l),upper.getBlockPos());check(upper.tanks[0].getTankType()==Fluids.HEAVYOIL,"copy bottom gate");
        lower.pasteSettings(settings,-1,l,player(l),lower.getBlockPos());check(lower.tanks[0].getTankType()==Fluids.HEAVYOIL,"negative copy index ignored");
        lower.pasteSettings(settings,0,l,player(l),lower.getBlockPos());check(lower.tanks[0].getTankType()==Fluids.NAPHTHA,"bottom copy succeeds");
        var gap=tower(l,10,0);var distant=tower(l,10,4);gap.tanks[0].setFill(200);tick(l,gap,3);check(gap.tanks[0].getFill()==200&&distant.tanks[0].getFill()==0,"spacer gap does not relay");
        for(int count:new int[]{2,3})for(boolean reverse:new boolean[]{false,true}){
            l=world();MachineFractionTowerBlockEntity[] bs=new MachineFractionTowerBlockEntity[count];for(int i=0;i<count;i++)bs[i]=tower(l,0,i*3);bs[0].tanks[0].setFill(600);
            for(int t=1;t<=100;t++){l.time=t;for(int j=0;j<count;j++)bs[reverse?count-1-j:j].updateEntity();check(sum(bs)==600,"tick-order conservation "+count+"/"+reverse+"/"+t);for(var b:bs)for(var tank:b.tanks)check(tank.getFill()>=0&&tank.getFill()<=4000,"tick-order capacity");}
            int oil=0,left=0,right=0;for(var b:bs){oil+=b.tanks[0].getFill();left+=b.tanks[1].getFill();right+=b.tanks[2].getFill();}check(oil==0&&left==180&&right==420,"bounded tick-order convergence "+count+"/"+reverse);
        }
    }
    static void networkAndState()throws Exception{
        Level l=world();var b=tower(l,0,0);b.dirty=0;check(b.transferFluid(Fluids.HEAVYOIL,0,100)==0&&b.dirty>0,"network-only input dirty");
        b.dirty=0;check(b.transferFluid(Fluids.WATER,0,100)==100&&b.dirty==0,"wrong input unchanged");
        check(b.transferFluid(Fluids.HEAVYOIL,1,100)==100,"wrong pressure refused");
        b.tanks[1].setFill(100);b.dirty=0;b.useUpFluid(Fluids.BITUMEN,0,30);check(b.tanks[1].getFill()==70&&b.dirty>0,"network-only output dirty");
        b.dirty=0;b.useUpFluid(Fluids.BITUMEN,1,30);check(b.tanks[1].getFill()==70&&b.dirty==0,"wrong output pressure unchanged");
        for(int i=0;i<3;i++){b.tanks[i].withPressure(i+2);b.tanks[i].setFill(123+i);}CompoundTag t=new CompoundTag();nbt(b,t,false);var c=tower(l,5,0);nbt(c,t,true);
        for(int i=0;i<3;i++)check(c.tanks[i].getTankType()==b.tanks[i].getTankType()&&c.tanks[i].getPressure()==i+2&&c.tanks[i].getFill()==123+i,"NBT triple roundtrip "+i);
        RegistryFriendlyByteBuf buf=new RegistryFriendlyByteBuf();b.serialize(buf);c.deserialize(buf);for(int i=0;i<3;i++)check(c.tanks[i].getTankType()==b.tanks[i].getTankType()&&c.tanks[i].getPressure()==i+2&&c.tanks[i].getFill()==123+i,"sync triple roundtrip "+i);
        l.isClientSide=true;b.tanks[0].setFill(100);tick(l,b,10);check(b.tanks[0].getFill()==100,"client never processes");check(!b.changeInputType(Fluids.NAPHTHA,player(l)),"client type change refused");
    }
    static void handoff(api.hbm.fluidmk2.IFluidStandardTransceiverMK2 from,api.hbm.fluidmk2.IFluidStandardReceiverMK2 to,FluidType type,int amount){long remaining=to.transferFluid(type,0,amount);check(remaining==0,"chain receiver accepts "+type.getInternalName());from.useUpFluid(type,0,amount);}
    static void process(Level l,MachineFractionTowerBlockEntity b,int runs){for(int i=0;i<runs;i++)tick(l,b,10L*(i+1));}
    static void chain(Path work)throws Exception{
        Level l=world();Fluids.initializeGoal14AFuels();var refinery=new MachineRefineryBlockEntity(new BlockPos(30,0,0),new BlockState());l.put(refinery);refinery.power=1000;refinery.tanks[0].setFill(4000);
        Method refine=MachineRefineryBlockEntity.class.getDeclaredMethod("refine");refine.setAccessible(true);for(int i=0;i<40;i++)check((boolean)refine.invoke(refinery),"actual refinery batch "+i);
        check(refinery.power==800&&refinery.tanks[0].getFill()==0&&refinery.tanks[1].getFill()==2000&&refinery.tanks[2].getFill()==1000&&refinery.tanks[3].getFill()==600&&refinery.tanks[4].getFill()==400,"finite refinery input costs outputs");
        var n=tower(l,0,0);var light=tower(l,10,0);var heavy=tower(l,20,0);var smear=tower(l,40,0);n.changeInputType(Fluids.NAPHTHA,player(l));light.changeInputType(Fluids.LIGHTOIL,player(l));smear.changeInputType(Fluids.SMEAR,player(l));tick(l,n,1);tick(l,light,1);tick(l,smear,1);
        handoff(refinery,n,Fluids.NAPHTHA,1000);handoff(refinery,light,Fluids.LIGHTOIL,600);handoff(refinery,heavy,Fluids.HEAVYOIL,2000);process(l,n,10);process(l,light,6);process(l,heavy,20);
        check(n.tanks[2].getFill()==600&&n.tanks[1].getFill()==400&&light.tanks[1].getFill()==240&&light.tanks[2].getFill()==360,"refinery naphtha lightoil actual fractions");
        handoff(heavy,smear,Fluids.SMEAR,1400);process(l,smear,14);check(heavy.tanks[1].getFill()==600&&smear.tanks[1].getFill()==840&&smear.tanks[2].getFill()==560,"heavy smear lubricant chain");
        var diesel=new MachineDieselBlockEntity(new BlockPos(60,0,0),new BlockState());l.put(diesel);handoff(n,diesel,Fluids.DIESEL,600);handoff(light,diesel,Fluids.DIESEL,240);diesel.isOn=true;long clipped=0;for(int i=0;i<840;i++){long before=diesel.power;diesel.updateEntity();clipped+=Math.max(0,before+1027-diesel.power);}
        long gross=840*1027L;check(diesel.tank.getFill()==0&&gross==diesel.power+clipped,"fraction diesel actual burns closed HE");
        int retained=sum(n,light,heavy,smear)+refinery.tanks[4].getFill();check(retained==3160&&retained+840==4000,"closed fluids remaining plus burned");check(1000+gross==refinery.power+200+diesel.power+clipped,"closed initial cost generated energy");
        Files.writeString(work.resolve("chain-accounting.json"),"{\"initialHotOilMB\":4000,\"initialRefineryHE\":1000,\"refineryCostHE\":200,\"remainingRefineryHE\":800,\"naphthaMB\":1000,\"lightOilMB\":600,\"heavyOilMB\":2000,\"petroleumRemainingMB\":400,\"bitumenRemainingMB\":600,\"heatingOilRemainingMB\":1240,\"keroseneRemainingMB\":360,\"lubricantRemainingMB\":560,\"burnedDieselMB\":840,\"grossHE\":"+gross+",\"remainingDieselHE\":"+diesel.power+",\"clippedHE\":"+clipped+",\"closedFluidAccount\":true,\"closedEnergyAccount\":true}");
    }
    public static void main(String[] args)throws Exception{
        single();System.out.println("single processing/type/custom: "+checks+" checks passed");int before=checks;
        stacking();System.out.println("stack/copy/orders (includes per-tick bounds): "+(checks-before)+" checks passed");before=checks;
        networkAndState();System.out.println("network mutation/save/sync: "+(checks-before)+" checks passed");before=checks;
        chain(Path.of(args[0]));System.out.println("finite production chain: "+(checks-before)+" checks passed");
        System.out.println("Goal14B actual machine isolated: "+checks+" checks passed");
    }
}
