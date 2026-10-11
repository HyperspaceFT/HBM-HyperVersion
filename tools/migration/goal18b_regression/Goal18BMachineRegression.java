package com.hbm.blockentity.machine;

import api.hbm.fluidmk2.*;
import api.hbm.energymk2.*;
import com.hbm.blocks.DummyableBlock;
import com.hbm.blocks.NtmBlocks;
import com.hbm.handler.pollution.PollutionHandler;
import com.hbm.inventory.fluid.*;
import com.hbm.inventory.recipes.*;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.MachineUpgradeItem.UpgradeType;
import com.hbm.uninos.*;
import net.minecraft.core.*;
import net.minecraft.nbt.*;
import net.minecraft.world.item.*;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import java.io.Reader;
import java.nio.file.*;
import java.util.*;

/**
 * Goal18B: the production crystallizer under sulfuric acid, retyped through its identifier slot, and finite tungsten and
 * rare-earth chains over the real turbofan, PowerNetMK2 and centrifuge. Recipe tables are declared services whose rows the
 * fixture sets to the production defaults (the verifier resolves the production anchors into anchors.properties).
 * Deterministic ledgers never carry an upgrade; the Effectiveness roll is exercised separately with a seeded level random.
 */
public class Goal18BMachineRegression extends Goal18AMachineRegression {
    static final Item ORE_W = NtmBlocks.ORE_TUNGSTEN.get().asItem(), ORE_W_DEEP = NtmBlocks.ORE_TUNGSTEN_DEEPSLATE.get().asItem();
    static final Item ORE_RE = NtmBlocks.ORE_RARE.get().asItem(), ORE_RE_DEEP = NtmBlocks.ORE_RARE_DEEPSLATE.get().asItem();
    static final Item ORE_TI = NtmBlocks.ORE_TITANIUM.get().asItem(), ORE_TI_DEEP = NtmBlocks.ORE_TITANIUM_DEEPSLATE.get().asItem();
    static final Item ORE_CO = NtmBlocks.ORE_COBALT.get().asItem(), ORE_CO_DEEP = NtmBlocks.ORE_COBALT_DEEPSLATE.get().asItem();
    static final Item CRYSTAL_W = NtmItems.CRYSTAL_TUNGSTEN.get(), CRYSTAL_RE = NtmItems.CRYSTAL_RARE.get();
    static final Item CRYSTAL_TI = NtmItems.CRYSTAL_TITANIUM.get(), CRYSTAL_CO = NtmItems.CRYSTAL_COBALT.get();
    static final Item POWDER_W = NtmItems.POWDER_TUNGSTEN.get(), POWDER_FE = NtmItems.POWDER_IRON.get(), POWDER_LI_TINY = NtmItems.POWDER_LITHIUM_TINY.get();
    static final Item DESH_MIX = NtmItems.POWDER_DESH_MIX.get(), NUGGET_ZR = NtmItems.NUGGET_ZIRCONIUM.get();
    /** Tungsten chain kerosene: the smallest multiple of 100 mB that finishes the chain without an under-supplied tick (A0). */
    static final int TUNGSTEN_KEROSENE_MB = 1_700, COUNTER_KEROSENE_MB = TUNGSTEN_KEROSENE_MB - 100;
    static final int EFFECT_COMPLETIONS = 40;
    static final long EFFECT_SEED = 0x18B0EFFL;
    static final Properties anchors = new Properties();
    static final List<String> rows = new ArrayList<>();
    /** Highest SPEED/EFFECT/OVERDRIVE level any deterministic ledger tick saw (-1 until a ledger ran). */
    static int ledgerUpgradeMax = -1;
    static int ledgerKeptInputs = 0;

    static String at(String key){return anchors.getProperty(key,"<unresolved "+key+">");}
    static String declared(String... keys){StringBuilder s=new StringBuilder("fixture-declared, matching the production default at ");for(int i=0;i<keys.length;i++){if(i>0)s.append(", ");s.append(at(keys[i]));}return s.toString();}
    static String q(String s){return "\""+s.replace("\\","\\\\").replace("\"","\\\"")+"\"";}

    static Level fresh18b(){
        Level l=world();Fluids.initializeGoal17BFuels();PollutionHandler.reset();
        CrystallizerRecipes.clear();
        // Goal18A peroxide row (iron), kept to show the acid keying in both directions.
        CrystallizerRecipes.setRecipe(new ItemStack(ORE_IRON),Fluids.PEROXIDE,500,new ItemStack(NtmItems.CRYSTAL_IRON.get()),600,0.05F);
        CrystallizerRecipes.setRecipe(new ItemStack(ORE_DEEPSLATE_IRON),Fluids.PEROXIDE,500,new ItemStack(NtmItems.CRYSTAL_IRON.get()),600,0.05F);
        // The four production sulfuric acid groups, stone then deepslate, 500 mB, 600 ticks, productivity 0.05.
        Item[][] groups={{ORE_TI,ORE_TI_DEEP,CRYSTAL_TI},{ORE_W,ORE_W_DEEP,CRYSTAL_W},{ORE_CO,ORE_CO_DEEP,CRYSTAL_CO},{ORE_RE,ORE_RE_DEEP,CRYSTAL_RE}};
        for(Item[] g:groups)for(int i=0;i<2;i++)CrystallizerRecipes.setRecipe(new ItemStack(g[i]),Fluids.SULFURIC_ACID,500,new ItemStack(g[2]),600,0.05F);
        CentrifugeRecipes.clear();
        CentrifugeRecipes.setRecipe(new ItemStack(CRYSTAL_W),new ItemStack(POWDER_W,2),new ItemStack(POWDER_W,2),new ItemStack(POWDER_FE,1),new ItemStack(POWDER_LI_TINY,1));
        CentrifugeRecipes.setRecipe(new ItemStack(CRYSTAL_RE),new ItemStack(DESH_MIX,1),new ItemStack(DESH_MIX,1),new ItemStack(NUGGET_ZR,2),new ItemStack(NUGGET_ZR,2));
        return l;
    }
    static MachineTurbofanBlockEntity turbine(Level l,int x,Direction facing,int a,FluidType type,int fill){
        BlockPos p=new BlockPos(x,0,0);BlockState s=new BlockState().setValue(DummyableBlock.FACING,facing);
        var b=new MachineTurbofanBlockEntity(p,s);l.states.put(p,s);l.put(b);b.tank.setTankType(type);b.tank.setFill(fill);
        if(a>0)b.slots.set(2,upgrade(UpgradeType.AFTERBURN,a));return b;
    }
    static void step(Level l,MachineTurbofanBlockEntity b){l.time++;b.updateEntity();executedTicks++;}
    /** A crystallizer already configured for sulfuric acid: the identifier in slot 7 agrees with the tank type, so no retype happens. */
    static MachineCrystallizerBlockEntity acidizer(Level l,int x,long power,int acid){
        var b=machine(l,x,Direction.NORTH,power,0);b.slots.set(7,identifier(Fluids.SULFURIC_ACID));b.tank.setTankType(Fluids.SULFURIC_ACID);b.tank.setFill(acid);return b;
    }
    static MachineCentrifugeBlockEntity centrifuge(Level l,int x,long power){
        BlockPos p=new BlockPos(x,0,0);BlockState s=new BlockState();var c=new MachineCentrifugeBlockEntity(p,s);l.states.put(p,s);l.put(c);c.power=power;return c;
    }
    static int count(ItemStack s,Item i){return !s.isEmpty()&&s.getItem()==i?s.getCount():0;}
    static int upgradeLevels(MachineCrystallizerBlockEntity b){
        return Math.max(b.upgradeManager.getLevel(UpgradeType.SPEED),Math.max(b.upgradeManager.getLevel(UpgradeType.EFFECT),b.upgradeManager.getLevel(UpgradeType.OVERDRIVE)));
    }

    // a. Sulfuric acid through the identifier slot.
    static void sulfuric()throws Exception{
        scenario();Level l=fresh18b();var b=machine(l,0,Direction.NORTH,1_000_000L,8000);
        check(b.tank.getTankType()==Fluids.PEROXIDE&&b.tank.getFill()==8000&&b.tank.getMaxFill()==8000,"default 8,000 mB peroxide tank");
        check(!b.canPlaceItem(0,new ItemStack(ORE_W))&&!b.canPlaceItem(0,new ItemStack(ORE_W_DEEP))&&b.canPlaceItem(0,new ItemStack(ORE_IRON)),"peroxide tank: the input filter refuses tungsten ore and accepts iron ore");
        b.slots.set(0,new ItemStack(ORE_W,2));ticks(l,b,5);
        check(b.getRecipe()==null&&b.progress==0&&!b.isOn&&b.power==1_000_000L&&b.tank.getFill()==8000&&b.slots.get(0).getCount()==2&&crystals(b)==0,"tungsten ore forced into the slot under peroxide never starts and pays nothing");
        FluidNetMK2 old=new FluidNetMK2(Fluids.PEROXIDE);old.addReceiver(b);UniNodespace.activeNodeNets.add(old);
        b.slots.set(7,identifier(Fluids.SULFURIC_ACID));b.dirty=0;step(l,b);
        check(b.tank.getTankType()==Fluids.SULFURIC_ACID&&b.tank.getFill()==0&&b.tank.getMaxFill()==8000&&!old.receiverEntries.containsKey(b)&&b.dirty>0,"identifier retypes to sulfuric acid: the peroxide is discarded, the old peroxide network is left, the chunk is saved");
        check(b.progress==0&&!b.isOn&&b.power==1_000_000L,"the retype tick has no acid and pays nothing");
        check(b.canPlaceItem(0,new ItemStack(ORE_W))&&b.canPlaceItem(0,new ItemStack(ORE_W_DEEP)),"under sulfuric acid both tungsten ore blocks pass the filter");
        check(b.canPlaceItem(0,new ItemStack(ORE_RE))&&b.canPlaceItem(0,new ItemStack(ORE_RE_DEEP))&&b.canPlaceItem(0,new ItemStack(ORE_TI))&&b.canPlaceItem(0,new ItemStack(ORE_CO_DEEP)),"the other sulfuric groups pass as well");
        Item[] refused={NtmItems.FRAGMENT_COBALT.get(),NtmItems.RARE_EARTH_ORE_CHUNK.get(),Items.RAW_IRON,ORE_IRON,ORE_DEEPSLATE_IRON};
        String[] names={"fragment_cobalt","rare_earth_ore_chunk","raw_iron","iron_ore (peroxide row)","deepslate_iron_ore (peroxide row)"};
        for(int i=0;i<refused.length;i++)check(!b.canPlaceItem(0,new ItemStack(refused[i]))&&!b.canPlaceItemThroughFace(0,new ItemStack(refused[i]),Direction.UP),"refused under sulfuric acid: "+names[i]);
        var recipe=b.getRecipe();
        check(recipe!=null&&recipe.acidAmount()==500&&recipe.acidType()==Fluids.SULFURIC_ACID&&recipe.duration==600&&recipe.output().getItem()==CRYSTAL_W&&b.getDuration()==600,"the tungsten row resolves through the machine: 500 mB sulfuric acid, 600 ticks, tungsten crystal");
        b.tank.setFill(499);ticks(l,b,5);
        check(b.progress==0&&!b.isOn&&b.power==1_000_000L&&b.tank.getFill()==499,"499 mB sulfuric acid never starts");
        b.tank.setFill(500);ticks(l,b,600);
        check(b.progress==600&&crystals(b)==0&&b.tank.getFill()==500&&b.power==400_000L&&b.slots.get(0).getCount()==2,"600 effective sub-cycles: no crystal yet, acid and ore untouched, 600,000 HE spent");
        step(l,b);
        check(crystals(b)==1&&b.slots.get(2).getItem()==CRYSTAL_W&&b.tank.getFill()==0&&b.slots.get(0).getCount()==1&&b.power==399_000L&&b.progress==0,"601st sub-cycle: one tungsten crystal, exactly 500 mB sulfuric acid fully consumed, one ore");
        step(l,b);check(b.progress==0&&!b.isOn&&b.power==399_000L&&b.slots.get(0).getCount()==1,"the empty acid tank stops the next batch without paying");
        b.slots.set(0,new ItemStack(ORE_W_DEEP));b.tank.setFill(500);b.power=1_000_000L;
        check(b.getRecipe()!=null&&b.getRecipe().output().getItem()==CRYSTAL_W&&b.getRecipe().acidAmount()==500,"the deepslate tungsten row resolves to the same values");
        ticks(l,b,601);
        check(crystals(b)==2&&b.slots.get(0).isEmpty()&&b.tank.getFill()==0&&b.power==1_000_000L-601_000L,"deepslate tungsten ore: 601 sub-cycles, 500 mB, a second crystal");
        b.slots.set(7,identifier(Fluids.PEROXIDE));step(l,b);
        check(b.tank.getTankType()==Fluids.PEROXIDE&&b.tank.getFill()==0&&b.canPlaceItem(0,new ItemStack(ORE_IRON))&&!b.canPlaceItem(0,new ItemStack(ORE_W)),"retyped back to peroxide: iron ore is accepted again, tungsten ore refused");

        // Retype mid-process: the acid is emptied, the next sub-cycle fails and the progress returns to 0.
        scenario();l=fresh18b();b=acidizer(l,0,1_000_000L,1000);b.slots.set(0,new ItemStack(ORE_W,2));ticks(l,b,300);
        check(b.progress==300&&b.power==700_000L&&b.tank.getFill()==1000&&b.tank.getTankType()==Fluids.SULFURIC_ACID,"300 sub-cycles under sulfuric acid; the agreeing identifier never retypes");
        b.slots.set(7,identifier(Fluids.PEROXIDE));step(l,b);
        check(b.tank.getTankType()==Fluids.PEROXIDE&&b.tank.getFill()==0&&b.progress==0&&!b.isOn&&b.power==700_000L&&crystals(b)==0&&b.slots.get(0).getCount()==2,"retype mid-process: 1,000 mB sulfuric acid discarded, the sub-cycle fails, progress 0, the 300,000 HE stay sunk");
        b.slots.set(7,identifier(Fluids.SULFURIC_ACID));step(l,b);
        check(b.tank.getTankType()==Fluids.SULFURIC_ACID&&b.tank.getFill()==0&&b.progress==0&&b.power==700_000L,"retyping back does not restore the discarded acid");
        b.tank.setFill(500);ticks(l,b,600);check(crystals(b)==0&&b.progress==600,"a refilled batch restarts from zero");
        step(l,b);check(crystals(b)==1&&b.tank.getFill()==0&&b.power==700_000L-601_000L,"and needs the full 601 sub-cycles");

        // Save/load after a retype keeps the type and the fill and resets the progress.
        scenario();l=fresh18b();b=machine(l,0,Direction.NORTH,123_456L,0);b.slots.set(7,identifier(Fluids.SULFURIC_ACID));step(l,b);
        check(b.tank.getTankType()==Fluids.SULFURIC_ACID&&b.tank.getFill()==0,"retyped by the identifier before the save");
        b.tank.setFill(3210);b.slots.set(0,new ItemStack(ORE_W,2));ticks(l,b,40);
        check(b.progress==40&&b.power==123_456L-40_000L,"forty sub-cycles of progress before the save");
        CompoundTag tag=new CompoundTag();nbt(b,tag,false);var c=machine(l,20,Direction.NORTH,0,0);c.progress=77;
        check(c.tank.getTankType()==Fluids.PEROXIDE,"a fresh machine starts with the peroxide tank");
        nbt(c,tag,true);
        check(c.tank.getTankType()==Fluids.SULFURIC_ACID&&c.tank.getFill()==3210&&c.tank.getMaxFill()==8000&&c.power==83_456L,"reload keeps the sulfuric acid type, the fill and the power");
        check(c.progress==0&&!c.isOn&&c.duration==600&&!tag.contains("progress"),"reload resets the progress (not part of the NBT)");
        check(count(c.slots.get(0),ORE_W)==2&&c.slots.get(7).getItem()==NtmItems.FLUID_IDENTIFIER_MULTI.get()&&c.canPlaceItem(0,new ItemStack(ORE_W)),"the reloaded inventory keeps the tungsten ore and the identifier; the filter follows the loaded type");
        c.power=1_000_000L;ticks(l,c,600);check(crystals(c)==0&&c.progress==600&&c.tank.getTankType()==Fluids.SULFURIC_ACID,"the reloaded machine keeps its type and restarts from zero");
        step(l,c);check(crystals(c)==1&&c.tank.getFill()==2710&&c.power==1_000_000L-601_000L,"one crystal after the full 601 sub-cycles, 500 mB consumed");
    }

    // b. Finite tungsten chain over the real turbofan, PowerNetMK2 and centrifuge.
    static final class Run{
        int kerosene,burned,remaining,steps,crActive,crUnder,cfTicks,cfUnder,cfDone,crystalsMade,sixthCrystalTick=-1,upgradeMax,keptInputs,oreLeft,acidLeft;
        long gross,crSpent,cfSpent,discarded,turbofanBuffer,crBuffer,cfBuffer;boolean conserved=true;ItemStack[] outputs=new ItemStack[4];
        long finalBuffers(){return turbofanBuffer+crBuffer+cfBuffer;}
    }
    static Run tungsten(int kerosene,int maxSteps){
        Level l=fresh18b();Run r=new Run();r.kerosene=kerosene;
        var t=turbine(l,0,Direction.NORTH,0,Fluids.KEROSENE,kerosene);
        var cr=acidizer(l,100,0L,4000);cr.slots.set(0,new ItemStack(ORE_W,6));
        var cf=centrifuge(l,200,0L);
        PowerNetMK2 network=new PowerNetMK2();
        while(r.steps<maxSteps&&!(r.crystalsMade==6&&r.cfDone==6)){
            r.steps++;
            long before=t.power;int fuel=t.tank.getFill();step(l,t);r.gross+=t.output;r.burned+=fuel-t.tank.getFill();r.discarded+=before+t.output-t.power;
            // PowerNetMK2 drops entries older than its wall-clock timeout, so the subscriptions are refreshed every tick.
            network.addProvider(t);network.addReceiver(cr);network.addReceiver(cf);network.update();
            boolean ready=!cr.slots.get(0).isEmpty()&&cr.tank.getFill()>=500;int ore=cr.slots.get(0).getCount(),out=crystals(cr);
            before=cr.power;cr.updateEntity();executedTicks++;long use=before-cr.power;r.crSpent+=use;
            if(use>0)r.crActive++;else if(ready)r.crUnder++;
            r.upgradeMax=Math.max(r.upgradeMax,upgradeLevels(cr));
            int made=crystals(cr)-out;
            if(made>0){r.crystalsMade+=made;r.keptInputs+=made-(ore-cr.slots.get(0).getCount());if(r.crystalsMade==6)r.sixthCrystalTick=r.steps;}
            if(crystals(cr)>0){ItemStack moved=cr.removeItem(2,crystals(cr));if(cf.slots.get(0).isEmpty())cf.slots.set(0,moved);else cf.slots.get(0).grow(moved.getCount());}
            if(!cf.slots.get(0).isEmpty()){
                int inputs=cf.slots.get(0).getCount();before=cf.power;cf.updateEntity();executedTicks++;r.cfTicks++;long u=before-cf.power;r.cfSpent+=u;
                if(u==0)r.cfUnder++;if(cf.slots.get(0).getCount()<inputs)r.cfDone++;
            }
            if(r.gross!=r.crSpent+r.cfSpent+r.discarded+t.power+cr.power+cf.power)r.conserved=false;
        }
        r.remaining=t.tank.getFill();r.turbofanBuffer=t.power;r.crBuffer=cr.power;r.cfBuffer=cf.power;r.oreLeft=cr.slots.get(0).getCount();r.acidLeft=cr.tank.getFill();
        for(int i=0;i<4;i++)r.outputs[i]=cf.slots.get(2+i).copy();
        check(cr.tank.getTankType()==Fluids.SULFURIC_ACID&&t.tank.getTankType()==Fluids.KEROSENE&&t.afterburner==0,"chain kept its sulfuric acid tank and A0 kerosene");
        return r;
    }
    static void tungstenChain(){
        scenario();Run r=tungsten(TUNGSTEN_KEROSENE_MB,10_000);
        ledgerUpgradeMax=Math.max(ledgerUpgradeMax,r.upgradeMax);ledgerKeptInputs+=r.keptInputs;
        check(r.acidLeft==1000&&r.oreLeft==0&&r.crystalsMade==6&&r.keptInputs==0,"tungsten ledger: 6 ore and 3,000 of 4,000 mB sulfuric acid consumed, 1,000 mB remain, 6 crystals");
        check(r.crUnder==0&&r.cfUnder==0,"no under-supplied crystallizer or centrifuge tick (progress never reset by a power shortage)");
        check(r.crActive==3606&&r.sixthCrystalTick==3606&&r.crSpent==3_606_000L,"6 x 601 sub-cycles: the sixth crystal on tick 3,606, exactly 3,606,000 HE");
        check(r.cfTicks==1200&&r.cfDone==6&&r.cfSpent==240_000L&&r.steps==3805,"real centrifuge: 6 x 200 ticks, 240,000 HE, done on tick 3,805");
        check(count(r.outputs[0],POWDER_W)==24&&count(r.outputs[1],POWDER_FE)==6&&count(r.outputs[2],POWDER_LI_TINY)==6&&r.outputs[3].isEmpty(),"merged centrifuge outputs: 24 tungsten powder, 6 iron powder, 6 tiny lithium powder, fourth slot empty");
        check(r.burned==r.kerosene-r.remaining&&r.gross==3850L*r.burned,"A0 kerosene: 3,850 HE per burnt mB");
        check(r.conserved&&r.gross==r.crSpent+r.cfSpent+r.discarded+r.finalBuffers(),"energy identity gross == crystallizer + centrifuge + discarded + buffers on every tick");
        check(r.upgradeMax==0,"no SPEED/EFFECT/OVERDRIVE in the deterministic ledger");
        rows.add(tungstenRow("tungsten",r));
        // One step below the chosen preset: the same tick budget under-supplies the crystallizer.
        scenario();Run c=tungsten(COUNTER_KEROSENE_MB,r.steps);
        check(c.burned==COUNTER_KEROSENE_MB&&c.remaining==0&&c.crUnder>0&&c.sixthCrystalTick==-1&&c.crystalsMade<6,"100 mB less kerosene runs short: under-supplied ticks reset the progress and the sixth crystal misses the same tick budget");
        check(c.conserved&&c.gross==c.crSpent+c.cfSpent+c.discarded+c.finalBuffers(),"the short run conserves energy as well");
        rows.add(tungstenRow("tungsten-counterexample",c));
    }
    static String tungstenRow(String chain,Run r){
        StringBuilder s=new StringBuilder("{");
        s.append("\"chain\":").append(q(chain)).append(",\"initialOre\":6,\"oreBlock\":\"ore_tungsten\",\"initialSulfuricMB\":4000");
        s.append(",\"sulfuricSource\":{\"executed\":false,\"recipe\":\"chem.sulfuricacid\",\"batches\":2,\"sulfur\":2,\"peroxideMB\":2000,\"waterMB\":2000,\"sulfuricMB\":4000,\"plantTicks\":100,\"plantHE\":10000,\"rowSource\":").append(q(at("chem.sulfuricacid"))).append("}");
        s.append(",\"keroseneMB\":{\"preset\":").append(r.kerosene).append(",\"burned\":").append(r.burned).append(",\"remaining\":").append(r.remaining).append("}");
        s.append(",\"afterburner\":0,\"turbofanHEt\":3850,\"powerNet\":\"PowerNetMK2 re-registered every tick: turbofan provider; crystallizer and centrifuge receivers\"");
        s.append(",\"tickOrder\":\"turbofan updateEntity -> PowerNetMK2.update -> crystallizer updateEntity -> move crystals -> centrifuge updateEntity (when it has input)\"");
        s.append(",\"chainTicks\":").append(r.steps).append(",\"grossHE\":").append(r.gross).append(",\"crystallizerHE\":").append(r.crSpent).append(",\"centrifugeHE\":").append(r.cfSpent);
        s.append(",\"discardedHE\":").append(r.discarded).append(",\"batteryHE\":0,\"finalBuffersHE\":").append(r.finalBuffers());
        s.append(",\"buffersHE\":{\"turbofan\":").append(r.turbofanBuffer).append(",\"crystallizer\":").append(r.crBuffer).append(",\"centrifuge\":").append(r.cfBuffer).append("}");
        s.append(",\"crystallizerTicks\":").append(r.crActive).append(",\"sixthCrystalTick\":").append(r.sixthCrystalTick).append(",\"centrifugeTicks\":").append(r.cfTicks);
        s.append(",\"crystals\":").append(r.crystalsMade).append(",\"oreConsumed\":").append(6-r.oreLeft).append(",\"remainingSulfuricMB\":").append(r.acidLeft);
        s.append(",\"outputs\":{\"powder_tungsten\":").append(count(r.outputs[0],POWDER_W)).append(",\"powder_iron\":").append(count(r.outputs[1],POWDER_FE)).append(",\"powder_lithium_tiny\":").append(count(r.outputs[2],POWDER_LI_TINY)).append("}");
        s.append(",\"underSuppliedTicks\":").append(r.crUnder).append(",\"centrifugeUnderSuppliedTicks\":").append(r.cfUnder).append(",\"upgrades\":\"none (SPEED/EFFECT/OVERDRIVE 0)\"");
        s.append(",\"crystallizerRowSource\":").append(q(declared("crystallizer.tungsten","crystallizer.ore_helper","crystallizer.default_acid","crystallizer.default_duration","crystallizer.default_productivity")));
        s.append(",\"centrifugeRowSource\":").append(q(declared("centrifuge.tungsten")));
        if(chain.equals("tungsten")){
            s.append(",\"staticTail\":{\"executed\":false,\"note\":\"FoundryMoldBlockEntity and MachineCrucibleBlockEntity are not compiled in this machine world; priced statically (Goal 17A executed the mold)\"");
            s.append(",\"furnace\":{\"input\":\"powder_tungsten\",\"count\":24,\"output\":\"ingot_tungsten\",\"ingots\":24,\"ticksEach\":200,\"furnaceTicks\":4800,\"rowSource\":").append(q(at("furnace.tungsten")+" (cook time "+at("furnace.cook_time")+")")).append("}");
            s.append(",\"foundry\":{\"quantaPerIngot\":72,\"totalQuanta\":1728,\"bladeQuanta\":216,\"blades\":8,\"coolingTicksEach\":200,\"moldTicks\":1600,\"rowSource\":").append(q(at("casting.ingot_quanta")+", "+at("casting.blade_quanta")+", "+at("casting.tungsten_melt")+", "+at("mold.cooloff")+", "+at("mold.blade"))).append("}}");
        }
        return s.append("}").toString();
    }

    // c. Rare earth: one ore through the crystallizer on a declared finite budget, then the real centrifuge.
    static void rareEarthChain(){
        scenario();Level l=fresh18b();var b=acidizer(l,0,1_000L,500);b.slots.set(0,new ItemStack(ORE_RE));b.slots.set(1,pack(600_000L));
        long spent=0;int under=0,upgrades=0;
        for(int t=0;t<601;t++){long before=b.power+PACK.getCharge(b.slots.get(1));boolean ready=!b.slots.get(0).isEmpty();step(l,b);long use=before-(b.power+PACK.getCharge(b.slots.get(1)));spent+=use;if(ready&&use==0)under++;upgrades=Math.max(upgrades,upgradeLevels(b));}
        ledgerUpgradeMax=Math.max(ledgerUpgradeMax,upgrades);
        check(crystals(b)==1&&b.slots.get(2).getItem()==CRYSTAL_RE&&b.slots.get(0).isEmpty()&&b.tank.getFill()==0&&b.tank.getTankType()==Fluids.SULFURIC_ACID,"one rare earth crystal from one ore and exactly 500 mB sulfuric acid");
        check(b.power==0&&PACK.getCharge(b.slots.get(1))==0&&spent==601_000L&&under==0&&upgrades==0,"601,000 HE exactly: 1,000 HE buffer plus a full copper capacitor, no shortage, no upgrade");
        var c=centrifuge(l,10,40_000L);c.slots.set(0,b.removeItem(2,1));
        int ticks=0;long cfSpent=0;while(!c.slots.get(0).isEmpty()&&ticks<400){long before=c.power;l.time++;c.updateEntity();executedTicks++;ticks++;cfSpent+=before-c.power;}
        check(ticks==200&&cfSpent==40_000L&&c.power==0,"real centrifuge: 200 ticks, 40,000 HE");
        check(count(c.slots.get(2),DESH_MIX)==2&&count(c.slots.get(3),NUGGET_ZR)==4&&c.slots.get(4).isEmpty()&&c.slots.get(5).isEmpty(),"merged outputs: 2 desh blend + 4 zirconium nuggets");
        rows.add("{\"chain\":\"rare-earth\",\"initialOre\":1,\"oreBlock\":\"ore_rare\",\"initialSulfuricMB\":500,\"initialBufferHE\":1000,\"capacitorHE\":600000,\"batteryType\":\"capacitor_copper\""
            +",\"crystallizerTicks\":601,\"crystallizerHE\":"+spent+",\"crystals\":1,\"remainingSulfuricMB\":0,\"remainingBufferHE\":0,\"remainingCapacitorHE\":0,\"underSuppliedTicks\":"+under
            +",\"centrifugeHE\":"+cfSpent+",\"centrifugeTicks\":"+ticks+",\"centrifugePresetHE\":40000,\"outputs\":{\"powder_desh_mix\":2,\"nugget_zirconium\":4},\"upgrades\":\"none (SPEED/EFFECT/OVERDRIVE 0)\""
            +",\"crystallizerRowSource\":"+q(declared("crystallizer.rare","crystallizer.ore_helper","crystallizer.default_acid","crystallizer.default_duration","crystallizer.default_productivity"))
            +",\"centrifugeRowSource\":"+q(declared("centrifuge.rare"))
            +",\"staticTail\":{\"executed\":false"
            +",\"desh\":{\"recipe\":\"chem.desh\",\"batches\":2,\"powderDeshMix\":2,\"lightoilMB\":400,\"mercuryMB\":400,\"plantTicks\":200,\"plantHE\":20000,\"ingotDesh\":2,\"rowSource\":"+q(at("chem.desh"))+"}"
            +",\"deshCrackedAlternative\":{\"recipe\":\"chem.deshcracked\",\"note\":\"listed separately, never mixed with chem.desh\",\"perIngot\":{\"powderDeshMix\":1,\"lightoilCrackMB\":500,\"lightoilCrackPressure\":1,\"mercuryMB\":100,\"plantTicks\":100,\"plantHE\":10000}"
            +",\"forTwoIngots\":{\"powderDeshMix\":2,\"lightoilCrackMB\":1000,\"lightoilCrackPressure\":1,\"mercuryMB\":200,\"plantTicks\":200,\"plantHE\":20000},\"rowSource\":"+q(at("chem.deshcracked"))+"}}}");
    }

    // d. Effectiveness kept apart from the deterministic ledgers: the input roll uses the seeded level random, the acid is always paid.
    static void effectSeparate(){
        scenario();Level l=fresh18b();
        // 601 sub-cycles at 7,000 HE exceed the 1,000,000 HE cache, so this probabilistic check uses a declared 100-tick variant of the tungsten row.
        CrystallizerRecipes.clear();CrystallizerRecipes.setRecipe(new ItemStack(ORE_W),Fluids.SULFURIC_ACID,500,new ItemStack(CRYSTAL_W),100,0.05F);
        var b=acidizer(l,0,1_000_000L,500);b.slots.set(0,new ItemStack(ORE_W,64));b.slots.set(6,upgrade(UpgradeType.EFFECT,3));
        float chance=Math.min(3*0.05F,MachineCrystallizerBlockEntity.MAX_FREE_CHANCE);
        l.random.setSeed(EFFECT_SEED);Random replay=new Random(EFFECT_SEED);int kept=0,expectedKept=0;
        for(int i=0;i<EFFECT_COMPLETIONS;i++){
            b.tank.setFill(500);b.power=1_000_000L;int before=b.slots.get(0).getCount();ticks(l,b,101);
            if(i==0)check(Math.abs(b.getFreeChance(b.getRecipe())-0.15F)<1e-6&&b.getFreeChance(b.getRecipe())==chance&&b.getPowerRequired()==7000,"EFFECT 3: keep chance 3 x 0.05 = 0.15, 7,000 HE per sub-cycle");
            boolean consume=MachineCrystallizerBlockEntity.shouldConsumeInput(chance,replay.nextFloat());if(!consume)expectedKept++;
            int after=b.slots.get(0).getCount();if(after==before)kept++;
            check(crystals(b)==i+1&&b.tank.getFill()==0&&b.power==1_000_000L-101L*7000L&&after==(consume?before-1:before),"completion "+(i+1)+": a crystal, all 500 mB acid, 707,000 HE; the input follows the replayed roll");
        }
        // Binomial(40, 0.15): mean 6, P(X=0) = 0.85^40 ~ 0.15 % and P(X >= 15) ~ 0.1 %, so 1..14 kept inputs is the plausible band.
        check(kept==expectedKept&&kept>=1&&kept<=14&&64-b.slots.get(0).getCount()==EFFECT_COMPLETIONS-kept,"kept inputs "+kept+" match the replayed level random and lie in the plausible 1..14 band");
        if(ledgerUpgradeMax>=0)check(ledgerUpgradeMax==0&&ledgerKeptInputs==0,"the deterministic ledgers never carried EFFECT (or any upgrade) and never kept an input");
        rows.add("{\"chain\":\"effect-separate\",\"probabilistic\":true,\"effectLevel\":3,\"keepChance\":0.15,\"seed\":"+EFFECT_SEED+",\"completions\":"+EFFECT_COMPLETIONS
            +",\"keptInputs\":"+kept+",\"consumedInputs\":"+(EFFECT_COMPLETIONS-kept)+",\"crystals\":"+crystals(b)+",\"sulfuricConsumedMB\":"+(500*EFFECT_COMPLETIONS)+",\"spentHE\":"+(707_000L*EFFECT_COMPLETIONS)
            +",\"plausibleKeptBand\":[1,14],\"rowSource\":\"declared 100-tick variant of the tungsten sulfuric acid row (production row: 600 ticks); keeps 101 x 7,000 HE under the 1,000,000 HE cache; energy and acid refilled per completion\"}");
    }

    public static void main(String[] args)throws Exception{
        Path output=Path.of(args[0]);
        Path props=output.resolve("anchors.properties");
        if(Files.isRegularFile(props))try(Reader r=Files.newBufferedReader(props)){anchors.load(r);}
        Set<String> only=args.length>1?new HashSet<>(Arrays.asList(args[1].split(","))):null;
        if(only==null||only.contains("sulfuric"))sulfuric();
        if(only==null||only.contains("tungstenChain"))tungstenChain();
        if(only==null||only.contains("rareEarthChain"))rareEarthChain();
        if(only==null||only.contains("effectSeparate"))effectSeparate();
        Files.writeString(output.resolve("finite.json"),"["+String.join(",",rows)+"]");
        System.out.println("Goal18B machine: "+checks+" assertions; "+scenarios+" independent scenarios; "+executedTicks+" executed ticks");
    }
}
