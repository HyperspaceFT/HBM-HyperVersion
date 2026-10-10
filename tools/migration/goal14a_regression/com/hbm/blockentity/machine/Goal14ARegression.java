package com.hbm.blockentity.machine;

import api.hbm.energymk2.PowerNetMK2;
import api.hbm.fluidmk2.FluidNetMK2;
import com.hbm.blockentity.LoadedBaseBlockEntity;
import com.hbm.blockentity.ProxyComboBlockEntity;
import com.hbm.blockentity.machine.storage.BatterySocketBlockEntity;
import com.hbm.blockentity.machine.storage.BatteryBaseBlockEntity;
import com.hbm.blockentity.network.CableBaseBlockEntity;
import com.hbm.blockentity.network.PipeBaseBlockEntity;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.FluidContainerRegistry;
import com.hbm.inventory.fluid.*;
import com.hbm.inventory.fluid.trait.FT_Combustible;
import com.hbm.inventory.fluid.trait.FT_Combustible.FuelGrade;
import com.hbm.inventory.menus.MachineDieselMenu;
import com.hbm.inventory.recipes.ChemicalPlantRecipes;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.BatteryPackItem;
import com.hbm.items.machine.BatteryPackItem.BatteryPackType;
import com.hbm.items.machine.FluidIDMultiItem;
import com.hbm.network.toserver.CompoundTagControl;
import com.hbm.uninos.*;
import net.minecraft.core.*;
import net.minecraft.core.component.DataComponents;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.*;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.neoforged.neoforge.network.handling.IPayloadContext;
import java.lang.reflect.Method;
import java.nio.file.*;
import java.util.*;

/** Production behavior; registry identities, Minecraft services and scheduling are isolated. */
public class Goal14ARegression {
    static int checks;
    static final BatteryPackItem PACK = new BatteryPackItem(new Item.Properties());
    static void check(boolean value, String message) { if(!value) throw new AssertionError(message); checks++; }
    static Level world() { UniNodespace.levels.clear(); UniNodespace.activeNodeNets.clear(); Level l=new Level(); l.manualClock=true; l.time=1; return l; }
    static MachineDieselBlockEntity diesel(Level l, int x) {
        BlockPos p=new BlockPos(x,0,0); BlockState s=new BlockState();
        MachineDieselBlockEntity b=new MachineDieselBlockEntity(p,s); l.states.put(p,s); l.put(b); return b;
    }
    static ItemStack pack(long n) { ItemStack s=MetaHelper.newStack(PACK,1,BatteryPackType.CAPACITOR_COPPER.ordinal()); PACK.setCharge(s,n); return s; }
    static ItemStack full(FluidType t) { return FluidContainerRegistry.getFullContainer(new ItemStack(NtmItems.FLUID_TANK_EMPTY.get()),t); }
    static ItemStack identifier(FluidType t) { ItemStack s=new ItemStack(NtmItems.FLUID_IDENTIFIER_MULTI.get()); FluidIDMultiItem.setType(s,t,true); return s; }
    static void tick(Level l, MachineDieselBlockEntity b) { l.time++; b.updateEntity(); }
    static void net(Level l) { UniNodespace.updateNodespace(new MinecraftServer(List.of(l))); UniNodespace.updateNodespace(new MinecraftServer(List.of(l))); }
    static PipeBaseBlockEntity pipe(Level l, int x, FluidType t) {PipeBaseBlockEntity p=new PipeBaseBlockEntity(new BlockPos(x,0,0),new BlockState());l.put(p);p.setFluidType(t);p.updateEntity();return p;}
    static long memberships(MachineDieselBlockEntity b, FluidType t) {return UniNodespace.activeNodeNets.stream().filter(n->n instanceof FluidNetMK2 && ((FluidNetMK2)n).receiverEntries.containsKey(b)).count();}
    static Player player(Level l) { Player p=new Player(); p.world=l; p.level=l; p.getInventory().player=p; return p; }
    static void control(Player p, BlockPos pos, CompoundTag t) {
        CompoundTagControl.handleServer(new CompoundTagControl(t,pos),new IPayloadContext(){public Player player(){return p;}});
    }
    static CompoundTag flag() { CompoundTag t=new CompoundTag(); t.putBoolean("turnOn",true); return t; }
    static void nbt(LoadedBaseBlockEntity b, CompoundTag t, boolean load) throws Exception {
        Class<?> c=b.getClass(); while(c!=null) { try { Method m=c.getDeclaredMethod(load?"loadAdditional":"saveAdditional",CompoundTag.class,HolderLookup.Provider.class); m.setAccessible(true); m.invoke(b,t,null); return; } catch(NoSuchMethodException e) {c=c.getSuperclass();} } throw new AssertionError("NBT missing");
    }
    static void fuels() {
        Fluids.initializeGoal14AFuels();
        FluidType[] types={Fluids.NAPHTHA,Fluids.GASOLINE,Fluids.DIESEL,Fluids.KEROSENE};
        long[] energy={165000,1510000,1370000,3850000}; long[] power={82,1132,1027,385};
        for(int i=0;i<types.length;i++) {
            check(types[i].getTrait(FT_Combustible.class).getCombustionEnergy()==energy[i],"final calculated trait "+i);
            check(MachineDieselBlockEntity.getHEFromFuel(types[i])==power[i],"independent generator expectation "+i);
        }
        check(MachineDieselBlockEntity.getHEFromFuel(Fluids.HEAVYOIL)==0,"LOW rejected");
        check(MachineDieselBlockEntity.getHEFromFuel(Fluids.GAS)==0,"GAS rejected");
        check(MachineDieselBlockEntity.getHEFromFuel(Fluids.WATER)==0,"no trait rejected");
        Fluids.GASOLINE.addTraits(new FT_Combustible(FuelGrade.HIGH,2999));
        check(MachineDieselBlockEntity.getHEFromFuel(Fluids.GASOLINE)==1,"integer division precedes efficiency and current trait read");
        Fluids.GASOLINE.addTraits(new FT_Combustible(FuelGrade.HIGH,999));
        check(MachineDieselBlockEntity.getHEFromFuel(Fluids.GASOLINE)==0,"sub-thousand energy cannot burn");
        Fluids.initializeGoal14AFuels();
    }
    static void generation() {
        Level l=world(); MachineDieselBlockEntity b=diesel(l,0);
        check(!b.isOn && b.power==0 && b.powerCap==50000 && b.tank.getMaxFill()==16000 && b.tank.getTankType()==Fluids.DIESEL && b.getContainerSize()==4,"defaults");
        b.tank.setFill(5); tick(l,b); check(b.power==0 && b.tank.getFill()==5 && !b.wasOn,"off retains fuel");
        b.isOn=true; l.powered.add(b.getBlockPos()); tick(l,b); check(b.power==0 && b.tank.getFill()==5 && !b.wasOn,"redstone disables");
        l.powered.clear(); b.tank.setFill(1); b.dirty=0; tick(l,b);
        check(b.power==1027 && b.tank.getFill()==0 && b.wasOn && b.dirty>0,"last mB burns and saves");
        tick(l,b); check(b.power==1027 && !b.wasOn,"empty does not burn");
        for(FluidType t:new FluidType[]{Fluids.WATER,Fluids.GAS,Fluids.HEAVYOIL}) {b.tank.setTankType(t); b.tank.setFill(10); tick(l,b); check(b.power==1027 && b.tank.getFill()==10 && !b.wasOn,"unacceptable fuel unchanged");}
        b.tank.setTankType(Fluids.GASOLINE); b.tank.setFill(5); b.power=50000; tick(l,b);
        check(b.power==50000 && b.tank.getFill()==4 && b.wasOn,"full buffer still burns");
        b.power=49999; tick(l,b); check(b.power==50000 && b.tank.getFill()==3,"capacity clip");
        b.power=0; b.slots.set(2,pack(0)); tick(l,b);
        check(PACK.getCharge(b.slots.get(2))==0 && b.power==1132,"battery before generation first tick");
        tick(l,b); check(PACK.getCharge(b.slots.get(2))==1000 && b.power==1264,"actual battery charge rate before next generation");
        b.isOn=false; b.power=500; b.slots.set(2,pack(599900)); b.dirty=0; tick(l,b);
        check(PACK.getCharge(b.slots.get(2))==600000 && b.power==400 && b.dirty>0,"near-full battery transfer and dirty");
        b.slots.set(2,ItemStack.EMPTY); b.setPower(-1); check(b.power==0,"setPower lower clamp"); b.setPower(99999);check(b.power==50000,"upper clamp"); b.dirty=0;b.setPower(49900);check(b.dirty>0,"external power mutation saves");
        check(b.getConPos().length==6,"six connection positions");
        for(int i=0;i<6;i++)check(b.getConPos()[i].makeCompat().equals(b.getBlockPos().relative(Direction.values()[i])),"connection position "+i);
    }
    static void containersAndState() throws Exception {
        Level l=world(); MachineDieselBlockEntity b=diesel(l,0); b.dirty=0;
        check(b.transferFluid(Fluids.DIESEL,0,100)==0 && b.tank.getFill()==100 && b.dirty>0,"idle external fill dirty");
        b.dirty=0;check(b.transferFluid(Fluids.WATER,0,10)==10 && b.dirty==0,"wrong fluid no mutation");
        check(b.transferFluid(Fluids.DIESEL,1,10)==10,"wrong pressure refused");
        b.tank.setFill(0);b.slots.set(0,full(Fluids.DIESEL));b.dirty=0;tick(l,b);
        check(b.tank.getFill()==1000 && b.slots.get(0).isEmpty() && !b.slots.get(1).isEmpty() && b.dirty>0,"production container load");
        b.slots.set(0,full(Fluids.WATER));tick(l,b);check(b.tank.getFill()==1000 && !b.slots.get(0).isEmpty(),"wrong container unchanged");
        b.slots.set(0,full(Fluids.DIESEL));b.slots.set(1,new ItemStack(NtmItems.FLUID_TANK_EMPTY.get(),64));tick(l,b);check(b.tank.getFill()==1000 && !b.slots.get(0).isEmpty(),"full return slot atomic refusal");
        b.slots.set(1,new ItemStack(Items.STICK));tick(l,b);check(b.tank.getFill()==1000,"incompatible output atomic refusal");
        ItemStack named=full(Fluids.DIESEL);named.set(DataComponents.CUSTOM_NAME,Component.literal("source"));
        ItemStack empty=new ItemStack(NtmItems.FLUID_TANK_EMPTY.get());empty.set(DataComponents.CUSTOM_NAME,Component.literal("other"));
        b.slots.set(0,named);b.slots.set(1,empty);tick(l,b);check(b.tank.getFill()==1000 && b.slots.get(0).getCount()==1,"different custom output name refuses without loss");
        empty.set(DataComponents.CUSTOM_NAME,Component.literal("source"));empty.set(DataComponents.LORE,"different");b.slots.set(1,empty);tick(l,b);check(b.tank.getFill()==1000,"different other output component refuses");
        b.slots.set(1,ItemStack.EMPTY);b.tank.withPressure(1);tick(l,b);check(b.tank.getFill()==0 && b.slots.get(0).getCount()==1,"pressurized tank rejects ordinary container");
        b.tank.withPressure(0);b.tank.setFill(15999);tick(l,b);check(b.tank.getFill()==15999 && b.slots.get(0).getCount()==1,"insufficient capacity refuses entire container");
        b.tank.setFill(0);tick(l,b);check(b.tank.getFill()==1000 && b.slots.get(1).get(DataComponents.CUSTOM_NAME).equals(Component.literal("source")),"successful conversion preserves custom name");
        b.slots.set(0,ItemStack.EMPTY);b.slots.set(1,ItemStack.EMPTY);b.slots.set(3,identifier(Fluids.GASOLINE));b.dirty=0;tick(l,b);
        check(b.tank.getTankType()==Fluids.GASOLINE && b.tank.getFill()==0 && b.dirty>0,"identifier retypes and clears tank");
        b.slots.set(3,ItemStack.EMPTY);b.tank.setFill(1234);b.power=4321;b.powerCap=60000;b.isOn=true;b.wasOn=true;b.slots.set(2,pack(5678));
        CompoundTag t=new CompoundTag();nbt(b,t,false);MachineDieselBlockEntity c=diesel(l,3);nbt(c,t,true);
        check(c.isOn && !c.wasOn && c.power==4321 && c.powerCap==60000 && c.tank.getTankType()==Fluids.GASOLINE && c.tank.getFill()==1234,"production NBT state roundtrip");
        check(PACK.getCharge(c.slots.get(2))==5678,"production parent inventory NBT components roundtrip");
        RegistryFriendlyByteBuf buf=new RegistryFriendlyByteBuf();b.serialize(buf);c.deserialize(buf);
        check(c.wasOn && c.isOn && c.power==4321 && c.powerCap==60000 && c.tank.getFill()==1234,"production sync roundtrip");
        t.putLong("powerCap",-1);t.putLong("powerTime",Long.MAX_VALUE);nbt(c,t,true);check(c.powerCap==50000 && c.power==50000,"invalid saved capacity and overflow clamped");
    }
    static void menuAndControl() {
        Level l=world();MachineDieselBlockEntity b=diesel(l,0), other=diesel(l,4);Player p=player(l);MachineDieselMenu menu=new MachineDieselMenu(0,p.getInventory(),b);
        check(menu.slots.size()==40,"four machine and36 player slots");
        int[][] xy={{17,17},{17,53},{141,71},{35,71}};for(int i=0;i<4;i++)check(menu.slots.get(i).x==xy[i][0] && menu.slots.get(i).y==xy[i][1],"original machine slot position "+i);
        for(int i=4;i<31;i++)check(menu.slots.get(i).y==121+18*((i-4)/9),"player row position "+i);
        for(int i=31;i<40;i++)check(menu.slots.get(i).y==179,"hotbar position "+i);
        check(Arrays.equals(b.getSlotsForFace(Direction.UP),new int[]{0}) && Arrays.equals(b.getSlotsForFace(Direction.DOWN),new int[]{1,2}),"top bottom access");
        for(Direction d: new Direction[]{Direction.NORTH,Direction.SOUTH,Direction.EAST,Direction.WEST})check(Arrays.equals(b.getSlotsForFace(d),new int[]{2}),"side battery only");
        check(b.canPlaceItem(0,full(Fluids.DIESEL)) && !b.canPlaceItem(0,full(Fluids.GASOLINE)) && !b.canPlaceItem(1,new ItemStack(Items.STICK)),"container admission");
        check(b.canPlaceItem(2,pack(0)) && !b.canPlaceItem(2,new ItemStack(Items.STICK)) && b.canPlaceItem(3,identifier(Fluids.GASOLINE)),"battery identifier admission");
        check(!b.canTakeItemThroughFace(2,pack(1),Direction.DOWN) && b.canTakeItemThroughFace(2,pack(600000),Direction.DOWN),"automation extracts full battery only");
        check(b.canTakeItemThroughFace(1,new ItemStack(NtmItems.CANISTER_EMPTY.get()),Direction.DOWN) && b.canTakeItemThroughFace(1,new ItemStack(NtmItems.TANK_STEEL.get()),Direction.DOWN),"original return items admitted");
        p.getInventory().setItem(0,pack(1234));menu.quickMoveStack(p,31);check(!b.slots.get(2).isEmpty() && PACK.getCharge(b.slots.get(2))==1234,"Shift battery components retained");
        p.getInventory().setItem(1,identifier(Fluids.GASOLINE));menu.quickMoveStack(p,32);check(!b.slots.get(3).isEmpty(),"Shift identifier routed");
        p.getInventory().setItem(2,full(Fluids.DIESEL));menu.quickMoveStack(p,33);check(!b.slots.get(0).isEmpty(),"Shift matching fluid routed");
        p.getInventory().setItem(3,new ItemStack(Items.STICK));menu.quickMoveStack(p,34);check(b.slots.get(1).isEmpty(),"Shift cannot insert output");
        menu.quickMoveStack(p,2);check(b.slots.get(2).isEmpty(),"Shift out battery");
        p.getInventory().setItem(9,pack(2468));menu.quickMoveStack(p,4);check(!b.slots.get(2).isEmpty() && PACK.getCharge(b.slots.get(2))==2468 && p.getInventory().getItem(9).isEmpty(),"Shift first player slot uses four-slot boundary");
        control(p,b.getBlockPos(),flag());check(!b.isOn,"C2S no menu refused");p.containerMenu=new MachineDieselMenu(1,p.getInventory(),other);control(p,b.getBlockPos(),flag());check(!b.isOn,"C2S wrong menu refused");
        p.containerMenu=menu;p.inReach=false;control(p,b.getBlockPos(),flag());check(!b.isOn,"C2S distance refused");p.inReach=true;
        CompoundTag bad=flag();bad.putLong("powerTime",50000);control(p,b.getBlockPos(),bad);check(!b.isOn && b.power==0,"C2S extra forged field refused");
        bad=new CompoundTag();bad.putBoolean("turnOn",false);control(p,b.getBlockPos(),bad);check(!b.isOn,"false action refused");
        bad=new CompoundTag();bad.putString("turnOn","true");control(p,b.getBlockPos(),bad);check(!b.isOn,"wrong tag type refused");
        bad=new CompoundTag();bad.putBoolean("unknown",true);control(p,b.getBlockPos(),bad);check(!b.isOn,"unknown action refused");
        control(p,b.getBlockPos(),null);check(!b.isOn,"null action refused");
        FriendlyByteBuf transport=new FriendlyByteBuf();CompoundTagControl packet=new CompoundTagControl(flag(),b.getBlockPos());CompoundTagControl.STREAM_CODEC.encode(transport,packet);CompoundTagControl decoded=CompoundTagControl.STREAM_CODEC.decode(transport);check(decoded.pos().equals(b.getBlockPos()) && decoded.tag().equals(packet.tag()),"actual C2S codec ordering in transport service");
        b.dirty=0;control(p,b.getBlockPos(),flag());check(b.isOn && b.dirty>0,"actual C2S calls two overloads but toggles once and saves");
        b.receiveControl(flag());check(b.isOn,"no-player overload never toggles");l.isClientSide=true;check(!b.hasPermission(p),"client authority refused");
        l.isClientSide=false;Level otherLevel=new Level();p.world=otherLevel;p.level=otherLevel;check(!b.hasPermission(p),"cross-level rejected");p.world=l;p.level=l;
        l.entities.remove(b.getBlockPos());check(!b.hasPermission(p),"replaced block entity rejected");
    }
    static void subscriptions() {
        Level l=world();MachineDieselBlockEntity b=diesel(l,0);pipe(l,1,Fluids.DIESEL);pipe(l,-1,Fluids.GASOLINE);
        CableBaseBlockEntity cable=new CableBaseBlockEntity(new BlockPos(0,0,1),new BlockState());l.put(cable);cable.updateEntity();net(l);tick(l,b);net(l);
        check(memberships(b,Fluids.DIESEL)>0,"actual DIESEL pipe subscription registered");
        check(UniNodespace.activeNodeNets.stream().anyMatch(n->n instanceof PowerNetMK2 && ((PowerNetMK2)n).providerEntries.containsKey(b)),"actual power provider subscription");
        b.slots.set(3,identifier(Fluids.GASOLINE));tick(l,b);
        check(memberships(b,Fluids.DIESEL)==0,"type change removes stale fluid subscriptions immediately");
        b.slots.set(3,ItemStack.EMPTY);tick(l,b);net(l);check(memberships(b,Fluids.GASOLINE)>0,"new gasoline subscription created following tick");
        b.onChunkUnloaded();check(memberships(b,Fluids.GASOLINE)==0,"chunk unload removes fluid membership");
        check(UniNodespace.activeNodeNets.stream().noneMatch(n->n instanceof PowerNetMK2 && ((PowerNetMK2)n).providerEntries.containsKey(b)),"chunk unload removes power provider membership");
        tick(l,b);net(l);check(memberships(b,Fluids.GASOLINE)>0,"resubscribe after isolated unload callback");
        b.setRemoved();check(memberships(b,Fluids.GASOLINE)==0,"remove removes fluid membership");
    }
    static void chain(Path work) throws Exception {
        Level l=world();ChemicalPlantRecipes.INSTANCE.deleteRecipes();ChemicalPlantRecipes.INSTANCE.registerDefaults();
        MachineChemicalPlantBlockEntity plant=new MachineChemicalPlantBlockEntity(new BlockPos(100,0,0),new BlockState());l.put(plant);
        plant.chemicalModule.recipe="chem.gasoline";plant.updateEntity();plant.inputTanks[0].setFill(1000);plant.power=10000;
        long initial=plant.power;int processing=0;
        while(plant.outputTanks[0].getFill()==0 && processing<100){plant.updateEntity();processing++;l.time++;}
        long cost=initial-plant.power;
        check(plant.outputTanks[0].getFill()==800 && plant.inputTanks[0].getFill()==0,"real chemical plant naphtha -> gasoline");
        check(cost==processing*100L && processing==40,"measured process ticks and exact cost without per-tick power refill");
        MachineDieselBlockEntity b=diesel(l,0);b.tank.setTankType(Fluids.GASOLINE);
        // The fixture constructs pipe positions; production pipe nodes, subscriptions,
        // sender debit and receiver transfer perform the fluid hand-off.
        List<PipeBaseBlockEntity> pipes=new ArrayList<>();for(int x=1;x<=98;x++)pipes.add(pipe(l,x,Fluids.GASOLINE));
        net(l);b.updateEntity();plant.updateEntity();net(l);
        check(b.tank.getFill()==800 && plant.outputTanks[0].getFill()==0,"production pipe network conserves full800mB");
        for(int x=0;x<3;x++)pipes.get(x).setRemoved();
        BatterySocketBlockEntity socket=new BatterySocketBlockEntity(new BlockPos(4,0,0),new BlockState());l.put(socket);socket.slots.set(0,pack(0));
        for(int x=1;x<=3;x++){CableBaseBlockEntity c=new CableBaseBlockEntity(new BlockPos(x,0,0),new BlockState());l.put(c);c.updateEntity();}
        socket.updateEntity();net(l);socket.updateEntity();b.isOn=true;
        long gross=0;long clipped=0;
        for(int i=0;i<800;i++){
            long old=b.power;tick(l,b);gross+=1132;clipped+=Math.max(0,old+1132-b.power);socket.updateEntity();net(l);
        }
        check(b.tank.getFill()==0 && gross==905600,"800 actual burns and independent gross accounting");
        check(socket.getPower()>0,"actual cable power network charges battery socket");
        check(gross==b.power+socket.getPower()+clipped,"generation equals buffers plus clipped loss before load");
        // A real chemical plant is the load, subscribed on the same cable through one connection.
        MachineChemicalPlantBlockEntity load=new MachineChemicalPlantBlockEntity(new BlockPos(8,0,0),new BlockState());l.put(load);load.chemicalModule.recipe="chem.gasoline";load.updateEntity();load.inputTanks[0].setFill(1000);
        for(int x=5;x<=6;x++){CableBaseBlockEntity c=new CableBaseBlockEntity(new BlockPos(x,0,0),new BlockState());l.put(c);c.updateEntity();}
        socket.redLow=BatteryBaseBlockEntity.mode_output;socket.updateEntity();net(l);
        long storeBefore=socket.getPower()+b.power;long loadCost=0;
        // Include the receiver's production buffer fill and nodespace scheduling;
        // processing cost remains asserted independently, never reset/refill power.
        for(int i=0;i<400 && load.outputTanks[0].getFill()==0;i++){long old=load.power;load.updateEntity();loadCost+=old-load.power;socket.updateEntity();b.updateEntity();net(l);l.time++;}
        check(load.outputTanks[0].getFill()==800 && loadCost==4000,"actual storage network supplies complete real chemical load recipe: output="+load.outputTanks[0].getFill()+",cost="+loadCost+",power="+load.power+",progress="+load.chemicalModule.progress+",input="+load.inputTanks[0].getFill());
        check(storeBefore==socket.getPower()+b.power+load.power+loadCost,"storage/load conservation");
        check(initial+gross==plant.power+cost+clipped+b.power+socket.getPower()+load.power+loadCost,"closed initial-plus-generated energy accounting");
        check(load.inputTanks[0].getFill()==0 && load.outputTanks[0].getFill()==800 && b.tank.getFill()==0,"independent load naphtha consumed; output retained and not recycled into generation");
        Files.writeString(work.resolve("chain-accounting.json"),"{\"initialEnergy\":"+initial+",\"remainingInitialPlantHE\":"+plant.power+",\"initialPlantNaphthaMB\":1000,\"fuelProcessingHE\":"+cost+",\"processingTicks\":"+processing+",\"burnedMB\":800,\"grossHE\":"+gross+",\"clippedHE\":"+clipped+",\"remainingGeneratorHE\":"+b.power+",\"storageHE\":"+socket.getPower()+",\"loadBufferHE\":"+load.power+",\"loadProcessingHE\":"+loadCost+",\"independentLoadNaphthaMB\":1000,\"remainingLoadGasolineMB\":"+load.outputTanks[0].getFill()+",\"closedEnergyAccount\":true}");
    }
    public static void main(String[] args) throws Exception {
        fuels();FluidContainerRegistry.register();System.out.println("fuel source-derived methods: "+checks+" checks passed");
        int extracted=checks;
        generation();containersAndState();menuAndControl();subscriptions();chain(Path.of(args[0]));
        System.out.println("Goal14A actual machine/menu/control/network: "+(checks-extracted)+" checks passed; source-extracted fuel assertions: "+extracted+"; total: "+checks);
    }
}
