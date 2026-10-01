package com.hbm.blockentity.machine;

import com.hbm.inventory.FluidContainerRegistry;
import com.hbm.inventory.MetaHelper;
import com.hbm.inventory.fluid.Fluids;
import com.hbm.inventory.fluid.FluidType;
import com.hbm.inventory.fluid.tank.FluidTank;
import com.hbm.inventory.fluid.tank.FluidLoaderStandard;
import com.hbm.blockentity.machine.heater.HeaterFireboxBlockEntity;
import com.hbm.items.NtmItems;
import com.hbm.items.machine.FluidIDMultiItem;
import com.hbm.items.component.NtmDataComponents;
import com.hbm.inventory.menus.MachineFurnaceCombinationMenu;
import net.minecraft.core.BlockPos;
import net.minecraft.core.NonNullList;
import net.minecraft.core.component.DataComponents;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;

public class Goal5CRegression {
    private static int checks;
    private static void check(boolean value,String message){checks++;if(!value)throw new AssertionError(message);}
    private static NonNullList<ItemStack> slots(ItemStack input,ItemStack output){var slots=NonNullList.withSize(2,ItemStack.EMPTY);slots.set(0,input);slots.set(1,output);return slots;}
    private static ItemStack empty(FluidType type){return FluidContainerRegistry.getEmptyContainer(FluidContainerRegistry.getFullContainer(new ItemStack(NtmItems.FLUID_TANK_EMPTY.get()),type));}
    private static ItemStack namedEmpty(String name,String lore){ItemStack s=new ItemStack(NtmItems.FLUID_TANK_EMPTY.get());s.set(DataComponents.CUSTOM_NAME,Component.literal(name));s.set(DataComponents.LORE,lore);return s;}
    private static ItemStack namedFull(String name,String lore){ItemStack s=FluidContainerRegistry.getFullContainer(namedEmpty(name,lore),Fluids.COALCREOSOTE);s.set(DataComponents.CUSTOM_NAME,Component.literal(name));s.set(DataComponents.LORE,lore);return s;}
    private static void registryRules(){
        check(FluidContainerRegistry.allContainers.stream().filter(c->c.type==Fluids.COALCREOSOTE).count()==3,
                "normal coal creosote has lead/ordinary/barrel registrations");
        // Goal 9A registers the water bucket and the water bottle ahead of the three NTM containers.
        check(FluidContainerRegistry.allContainers.stream().filter(c->c.type==Fluids.WATER).count()==5,
                "water has the bucket, the bottle and three NTM registrations");
        check(FluidContainerRegistry.getFluidContent(FluidContainerRegistry.getFullContainer(new ItemStack(NtmItems.FLUID_BARREL_EMPTY.get()),Fluids.WATER),Fluids.WATER)==16_000,
                "water barrel holds 16000 mB");
        check(FluidContainerRegistry.allContainers.stream().filter(c->c.type==Fluids.DEATH).count()==1
                &&FluidContainerRegistry.getFullContainer(new ItemStack(NtmItems.FLUID_TANK_EMPTY.get()),Fluids.DEATH).isEmpty()
                &&!FluidContainerRegistry.getFullContainer(new ItemStack(NtmItems.FLUID_TANK_LEAD_EMPTY.get()),Fluids.DEATH).isEmpty(),
                "lead-only fluid rejects ordinary tank but allows lead tank");
        check(FluidContainerRegistry.allContainers.stream().noneMatch(c->c.type==Fluids.SPENTSTEAM||c.type==Fluids.PLASMA_DT),
                "no-container spent steam and plasma register no standard containers");
        check(!FluidContainerRegistry.getFullContainer(new ItemStack(NtmItems.FLUID_TANK_EMPTY.get()),Fluids.LAVA).isEmpty(),
                "hot lava has no extra standard-temperature exclusion");
        ItemStack empty=new ItemStack(NtmItems.FLUID_TANK_EMPTY.get());
        check(FluidContainerRegistry.isEmptyContainer(empty),"ordinary empty tank accepted before oven fluid type selected");
        MetaHelper.setMeta(empty,77);
        check(!FluidContainerRegistry.isEmptyContainer(empty)
                &&FluidContainerRegistry.getFullContainer(empty,Fluids.COALCREOSOTE).isEmpty(),
                "empty item with wrong META cannot impersonate registered empty tank");
    }
    private static void directTransfers(){
        var level=new Level();var tank=new FluidTank(Fluids.COALCREOSOTE,24_000);
        tank.setFill(1000);
        var s=slots(namedEmpty("kept name","lore-token"),ItemStack.EMPTY);
        check(tank.unloadTank(level,0,1,s)&&tank.getFill()==0&&s.get(0).isEmpty(),
                "one 1000 mB fill consumes one empty tank without fluid loss");
        check(s.get(1).is(NtmItems.FLUID_TANK_FULL.get())
                &&MetaHelper.getMeta(s.get(1))==Fluids.COALCREOSOTE.getID()
                &&s.get(1).getHoverName().equals(Component.literal("kept name"))
                &&"lore-token".equals(s.get(1).get(DataComponents.LORE)),
                "full tank has registered fluid META and preserves custom name and other component");
        var reverse=slots(s.get(1),ItemStack.EMPTY);
        check(tank.loadTank(level,0,1,reverse)&&tank.getFill()==1000&&reverse.get(0).isEmpty(),
                "reverse transfer restores exactly 1000 mB");
        check(reverse.get(1).is(NtmItems.FLUID_TANK_EMPTY.get())
                &&MetaHelper.getMeta(reverse.get(1))==0
                &&!reverse.get(1).has(NtmDataComponents.META.get())
                &&reverse.get(1).getHoverName().equals(Component.literal("kept name"))
                &&"lore-token".equals(reverse.get(1).get(DataComponents.LORE)),
                "empty return removes stale fluid META but keeps name and other component");

        tank.setFill(1000);s=slots(new ItemStack(NtmItems.FLUID_TANK_EMPTY.get(),2),ItemStack.EMPTY);
        check(tank.unloadTank(level,0,1,s)&&s.get(0).getCount()==1&&s.get(1).getCount()==1&&tank.getFill()==0,
                "two empty inputs transfer exactly one item and 1000 mB");
        tank.setFill(2000);s=slots(new ItemStack(NtmItems.FLUID_TANK_EMPTY.get(),2),ItemStack.EMPTY);
        check(tank.unloadTank(level,0,1,s)&&s.get(0).getCount()==1&&s.get(1).getCount()==1&&tank.getFill()==1000,
                "first continuous transfer consumes exactly one empty tank and 1000 mB");
        check(tank.unloadTank(level,0,1,s)&&s.get(0).isEmpty()&&s.get(1).getCount()==2&&tank.getFill()==0,
                "second continuous transfer merges matching full tank and consumes remaining 1000 mB");
        check(!tank.unloadTank(level,0,1,s)&&s.get(1).getCount()==2&&tank.getFill()==0,
                "extra continuous attempt after depletion does not create a third tank");
        tank.setFill(1000);s=slots(new ItemStack(NtmItems.FLUID_TANK_EMPTY.get()),FluidContainerRegistry.getFullContainer(new ItemStack(NtmItems.FLUID_TANK_EMPTY.get()),Fluids.COALCREOSOTE).copyWithCount(63));
        check(tank.unloadTank(level,0,1,s)&&s.get(1).getCount()==64&&tank.getFill()==0,
                "matching full output 63 plus one reaches exact stack limit 64");
        tank.setFill(1000);s=slots(new ItemStack(NtmItems.FLUID_TANK_EMPTY.get()),s.get(1));
        check(!tank.unloadTank(level,0,1,s)&&s.get(0).getCount()==1&&s.get(1).getCount()==64&&tank.getFill()==1000,
                "full output blocks without consuming item or fluid");
        tank.setFill(999);s=slots(new ItemStack(NtmItems.FLUID_TANK_EMPTY.get()),ItemStack.EMPTY);
        check(!tank.unloadTank(level,0,1,s)&&s.get(0).getCount()==1&&s.get(1).isEmpty()&&tank.getFill()==999,
                "insufficient 999 mB leaves input, output and tank unchanged");
        tank.setFill(1000);s=slots(new ItemStack(NtmItems.FLUID_TANK_EMPTY.get()),ItemStack.EMPTY);
        check(!tank.unloadTank(level,0,0,s)&&s.get(0).getCount()==1&&tank.getFill()==1000,
                "same input/output slot is rejected without mutation");
        tank.withPressure(1);s=slots(new ItemStack(NtmItems.FLUID_TANK_EMPTY.get()),ItemStack.EMPTY);tank.setFill(1000);
        check(!tank.unloadTank(level,0,1,s)&&s.get(0).getCount()==1&&tank.getFill()==1000,
                "pressure one rejects standard filling");
        s=slots(namedFull("pressurized","return"),ItemStack.EMPTY);tank.setFill(0);
        check(!tank.loadTank(level,0,1,s)&&s.get(0).getCount()==1&&s.get(1).isEmpty()&&tank.getFill()==0,
                "pressure one rejects reverse emptying without changing item or fluid");
        tank.withPressure(0);tank.setFill(1000);
        s=slots(new ItemStack(Items.IRON_INGOT),ItemStack.EMPTY);
        check(!tank.unloadTank(level,0,1,s)&&tank.getFill()==1000&&s.get(0).getCount()==1,
                "wrong input item does not claim standard conversion");

        tank.setFill(1000);s=slots(namedEmpty("A","lore"),namedFull("B","lore"));
        check(!tank.unloadTank(level,0,1,s)&&tank.getFill()==1000&&s.get(0).getCount()==1&&s.get(1).getCount()==1,
                "different custom output name blocks fill without loss");
        s=slots(namedEmpty("A","lore-a"),namedFull("A","lore-b"));
        check(!tank.unloadTank(level,0,1,s)&&tank.getFill()==1000&&s.get(0).getCount()==1,
                "different other component blocks fill without loss");
        s=slots(namedEmpty("A","lore"),namedFull("A","lore"));MetaHelper.setMeta(s.get(1),Fluids.WATER.getID());
        check(!tank.unloadTank(level,0,1,s)&&tank.getFill()==1000&&s.get(0).getCount()==1,
                "different output META blocks fill without loss");

        tank.setFill(0);s=slots(namedFull("A","lore"),namedEmpty("B","lore"));
        check(!tank.loadTank(level,0,1,s)&&tank.getFill()==0&&s.get(0).getCount()==1,
                "different custom name blocks reverse emptying without loss");
        s=slots(namedFull("A","lore-a"),namedEmpty("A","lore-b"));
        check(!tank.loadTank(level,0,1,s)&&tank.getFill()==0&&s.get(0).getCount()==1,
                "different other component blocks reverse emptying without loss");
        s=slots(namedFull("A","lore"),namedEmpty("A","lore"));MetaHelper.setMeta(s.get(1),77);
        check(!tank.loadTank(level,0,1,s)&&tank.getFill()==0&&s.get(0).getCount()==1,
                "different empty-output META blocks reverse emptying without loss");
        tank.setFill(23_500);s=slots(namedFull("A","lore"),ItemStack.EMPTY);
        check(!tank.loadTank(level,0,1,s)&&tank.getFill()==23_500&&s.get(0).getCount()==1,
                "insufficient tank room blocks reverse emptying");
        tank.setFill(0);s=slots(FluidContainerRegistry.getFullContainer(new ItemStack(NtmItems.FLUID_TANK_EMPTY.get()),Fluids.WATER),ItemStack.EMPTY);
        check(!tank.loadTank(level,0,1,s)&&tank.getFill()==0&&s.get(0).getCount()==1,
                "wrong fluid type is rejected");
    }
    private static void actualTankPersistence(){
        var tank=new FluidTank(Fluids.COALCREOSOTE,24_000);tank.setFill(1000);
        var tag=new CompoundTag();tank.writeToNBT(tag,"tank");
        var loaded=new FluidTank(Fluids.NONE,1);loaded.readFromNBT(tag,"tank");
        check(loaded.getFill()==1000&&loaded.getMaxFill()==24_000
                &&loaded.getTankType()==Fluids.COALCREOSOTE,"real tank NBT roundtrip preserves fill, capacity and type");
        var buf=new RegistryFriendlyByteBuf();tank.serialize(buf);
        var synced=new FluidTank(Fluids.NONE,1);synced.deserialize(buf);
        check(synced.getFill()==1000&&synced.getMaxFill()==24_000
                &&synced.getTankType()==Fluids.COALCREOSOTE,"real tank bytebuf roundtrip preserves fill, capacity and type");
    }
    private static void specialTransfers(){
        var level=new Level();var barrel=new FluidTank(Fluids.WATER,24_000);
        barrel.setFill(15_999);
        var s=slots(new ItemStack(NtmItems.FLUID_BARREL_EMPTY.get()),ItemStack.EMPTY);
        check(!barrel.unloadTank(level,0,1,s)&&barrel.getFill()==15_999&&s.get(0).getCount()==1&&s.get(1).isEmpty(),
                "15999 mB cannot fill a 16000 mB water barrel");
        barrel.setFill(16_000);
        check(barrel.unloadTank(level,0,1,s)&&barrel.getFill()==0&&s.get(1).is(NtmItems.FLUID_BARREL_FULL.get())
                &&MetaHelper.getMeta(s.get(1))==Fluids.WATER.getID(),"real standard handler fills one water barrel at 16000 mB");
        var reversed=slots(s.get(1),ItemStack.EMPTY);
        check(barrel.loadTank(level,0,1,reversed)&&barrel.getFill()==16_000
                &&reversed.get(1).is(NtmItems.FLUID_BARREL_EMPTY.get())&&!reversed.get(1).has(NtmDataComponents.META.get()),
                "water barrel reverses to empty barrel and restores exactly 16000 mB");
        var death=new FluidTank(Fluids.DEATH,24_000);death.setFill(1000);
        s=slots(new ItemStack(NtmItems.FLUID_TANK_EMPTY.get()),ItemStack.EMPTY);
        check(!death.unloadTank(level,0,1,s)&&death.getFill()==1000&&s.get(0).getCount()==1,
                "lead-only DEATH refuses ordinary empty tank in actual transfer");
        s=slots(new ItemStack(NtmItems.FLUID_TANK_LEAD_EMPTY.get()),ItemStack.EMPTY);
        check(death.unloadTank(level,0,1,s)&&death.getFill()==0&&s.get(1).is(NtmItems.FLUID_TANK_LEAD_FULL.get()),
                "lead-only DEATH transfers into lead tank");
        for(FluidType type:new FluidType[]{Fluids.SPENTSTEAM,Fluids.PLASMA_DT}){
            var prohibited=new FluidTank(type,24_000);prohibited.setFill(1000);
            s=slots(new ItemStack(NtmItems.FLUID_TANK_EMPTY.get()),ItemStack.EMPTY);
            check(!prohibited.unloadTank(level,0,1,s)&&prohibited.getFill()==1000&&s.get(0).getCount()==1&&s.get(1).isEmpty(),
                    "no-container type refuses actual standard transfer: "+type.getID());
        }
        var lava=new FluidTank(Fluids.LAVA,24_000);lava.setFill(1000);
        s=slots(new ItemStack(NtmItems.FLUID_TANK_EMPTY.get()),ItemStack.EMPTY);
        check(lava.unloadTank(level,0,1,s)&&lava.getFill()==0&&MetaHelper.getMeta(s.get(1))==Fluids.LAVA.getID(),
                "hot lava passes standard transfer without temperature gate");
    }
    private static void reverseOutputBoundaries(){
        var level=new Level();var tank=new FluidTank(Fluids.COALCREOSOTE,24_000);
        var input=namedFull("matching","other");var output=namedEmpty("matching","other");
        tank.setFill(0);var s=slots(input.copy(),output.copyWithCount(63));
        check(tank.loadTank(level,0,1,s)&&tank.getFill()==1000&&s.get(0).isEmpty()&&s.get(1).getCount()==64,
                "reverse conversion reaches exactly 64 matching empty tanks");
        tank.setFill(0);s=slots(input.copy(),output.copyWithCount(64));
        check(!tank.loadTank(level,0,1,s)&&tank.getFill()==0&&s.get(0).getCount()==1&&s.get(1).getCount()==64,
                "reverse conversion refuses full output without consuming fluid container");
        tank.setFill(0);s=slots(new ItemStack(NtmItems.FLUID_TANK_EMPTY.get()),ItemStack.EMPTY);
        check(!tank.loadTank(level,0,1,s)&&tank.getFill()==0&&s.get(0).getCount()==1,
                "already-empty input is not accepted by reverse transfer");
    }
    private static void ovenMenuBoundaries(MachineFurnaceCombinationBlockEntity oven){
        var player=new Player();var inv=player.getInventory();var menu=new MachineFurnaceCombinationMenu(0,inv,oven);
        var empty=new ItemStack(NtmItems.FLUID_TANK_EMPTY.get());
        check(menu.slots.get(2).mayPlace(empty)&&!menu.slots.get(2).mayPlace(namedFull("x","y"))
                &&!menu.slots.get(2).mayPlace(new ItemStack(Items.IRON_INGOT)),
                "oven menu fluid input accepts registered empty tank but refuses full and unrelated items");
        check(!menu.slots.get(3).mayPlace(empty),"oven fluid output is take-only");
        inv.setItem(0,empty);int before=oven.slots.get(2).getCount();
        check(menu.quickMoveStack(player,4).isEmpty()&&inv.getItem(0).getCount()==1
                &&oven.slots.get(2).getCount()==before,"oven Shift does not insert fluid container; slot remains manual");
    }
    private static void coldOvenChain(){
        var level=new Level();var fire=new HeaterFireboxBlockEntity(new BlockPos(0,0,0),new BlockState());level.put(fire);
        var oven=new MachineFurnaceCombinationBlockEntity(new BlockPos(0,1,0),new BlockState());level.put(oven);
        fire.slots.set(0,new ItemStack(Items.COAL,8));oven.slots.set(0,new ItemStack(Items.COAL,10));
        int ticks=0;
        while(oven.slots.get(1).getCount()<10&&ticks++<20_000){fire.updateEntity();oven.updateEntity();}
        check(oven.slots.get(0).isEmpty()&&oven.slots.get(1).is(NtmItems.COKE_COAL.get())
                &&oven.slots.get(1).getCount()==10&&oven.tank.getFill()==1000
                &&oven.tank.getTankType()==Fluids.COALCREOSOTE,
                "cold ten-coal firebox/oven path makes ten coke and 1000 mB creosote");
        ovenMenuBoundaries(oven);
        check(oven.canPlaceItem(MachineFurnaceCombinationBlockEntity.SLOT_FLUID_IN,
                new ItemStack(NtmItems.FLUID_TANK_EMPTY.get())),
                "oven accepts a registered empty tank in fluid input");
        oven.slots.set(MachineFurnaceCombinationBlockEntity.SLOT_FLUID_IN,namedEmpty("oven can","lore"));
        fire.updateEntity();oven.updateEntity();
        check(oven.tank.getFill()==0&&oven.slots.get(MachineFurnaceCombinationBlockEntity.SLOT_FLUID_IN).isEmpty()
                &&oven.slots.get(MachineFurnaceCombinationBlockEntity.SLOT_FLUID_OUT).is(NtmItems.FLUID_TANK_FULL.get())
                &&MetaHelper.getMeta(oven.slots.get(MachineFurnaceCombinationBlockEntity.SLOT_FLUID_OUT))==Fluids.COALCREOSOTE.getID(),
                "oven fills one named META-bearing 1000 mB tank from cold-produced fluid");
        ItemStack filled=oven.slots.get(MachineFurnaceCombinationBlockEntity.SLOT_FLUID_OUT);
        check(filled.getHoverName().equals(Component.literal("oven can"))
                &&"lore".equals(filled.get(DataComponents.LORE)),
                "oven output preserves custom name and other component");
        var tag=new CompoundTag();oven.saveAdditional(tag,null);
        var copy=new MachineFurnaceCombinationBlockEntity(new BlockPos(4,1,0),new BlockState());new Level().put(copy);copy.loadAdditional(tag,null);
        check(copy.slots.get(MachineFurnaceCombinationBlockEntity.SLOT_FLUID_OUT).is(NtmItems.FLUID_TANK_FULL.get())
                &&MetaHelper.getMeta(copy.slots.get(MachineFurnaceCombinationBlockEntity.SLOT_FLUID_OUT))==Fluids.COALCREOSOTE.getID()
                &&copy.slots.get(MachineFurnaceCombinationBlockEntity.SLOT_FLUID_OUT).getHoverName().equals(Component.literal("oven can")),
                "oven inventory save/load preserves full container META and custom name");
        oven.slots.set(MachineFurnaceCombinationBlockEntity.SLOT_FLUID_OUT,ItemStack.EMPTY);
        check(oven.slots.get(MachineFurnaceCombinationBlockEntity.SLOT_FLUID_OUT).isEmpty(),
                "oven output is removed before moving its produced tank to the wood burner");
        var wood=new MachineWoodBurnerBlockEntity(new BlockPos(8,0,0),new BlockState());level.put(wood);
        ItemStack identifier=new ItemStack(NtmItems.FLUID_IDENTIFIER_MULTI.get());
        var command=new CompoundTag();command.putInt("Primary",Fluids.COALCREOSOTE.getID());
        ((FluidIDMultiItem)identifier.getItem()).receiveControl(null,identifier,command);
        check(FluidIDMultiItem.getType(identifier,true)==Fluids.COALCREOSOTE
                &&MetaHelper.getMeta(identifier)==Fluids.COALCREOSOTE.getID(),
                "real identifier control configures creosote and updates item META");
        wood.slots.set(MachineWoodBurnerBlockEntity.SLOT_IDENTIFIER,identifier);
        wood.isOn=false;
        wood.updateEntity();
        check(wood.tank.getTankType()==Fluids.COALCREOSOTE
                &&wood.canPlaceItem(MachineWoodBurnerBlockEntity.SLOT_FLUID_IN,filled),
                "woodburner applies identifier before its actual fluid-input gate accepts the oven tank");
        wood.slots.set(MachineWoodBurnerBlockEntity.SLOT_FLUID_IN,filled);
        int woodDirtyBefore=wood.dirty;
        wood.updateEntity();
        check(wood.tank.getTankType()==Fluids.COALCREOSOTE&&wood.tank.getFill()==1000
                &&wood.slots.get(MachineWoodBurnerBlockEntity.SLOT_FLUID_IN).isEmpty()
                &&wood.slots.get(MachineWoodBurnerBlockEntity.SLOT_FLUID_OUT).is(NtmItems.FLUID_TANK_EMPTY.get()),
                "woodburner configured by real fluid identifier unloads oven tank as legal receiver");
        check(!wood.slots.get(MachineWoodBurnerBlockEntity.SLOT_FLUID_OUT).has(NtmDataComponents.META.get())
                &&wood.slots.get(MachineWoodBurnerBlockEntity.SLOT_FLUID_OUT).getHoverName().equals(Component.literal("oven can")),
                "woodburner empty return clears META and retains custom name");
        check(wood.dirty>woodDirtyBefore&&wood.tank.getFill()==1000&&!wood.isOn,
                "woodburner unloading marks dirty while switched off, without burning received fluid");
        var woodTag=new CompoundTag();wood.saveAdditional(woodTag,null);
        var woodCopy=new MachineWoodBurnerBlockEntity(new BlockPos(9,0,0),new BlockState());new Level().put(woodCopy);woodCopy.loadAdditional(woodTag,null);
        check(woodCopy.tank.getTankType()==Fluids.COALCREOSOTE&&woodCopy.tank.getFill()==1000
                &&woodCopy.slots.get(MachineWoodBurnerBlockEntity.SLOT_FLUID_OUT).is(NtmItems.FLUID_TANK_EMPTY.get())
                &&!woodCopy.slots.get(MachineWoodBurnerBlockEntity.SLOT_FLUID_OUT).has(NtmDataComponents.META.get())
                &&FluidIDMultiItem.getType(woodCopy.slots.get(MachineWoodBurnerBlockEntity.SLOT_IDENTIFIER),true)==Fluids.COALCREOSOTE,
                "woodburner save/load retains received fluid, returned empty tank and configured identifier");
        ItemStack returnedEmpty=wood.slots.get(MachineWoodBurnerBlockEntity.SLOT_FLUID_OUT);
        wood.slots.set(MachineWoodBurnerBlockEntity.SLOT_FLUID_OUT,ItemStack.EMPTY);
        oven.slots.set(0,new ItemStack(Items.COAL));
        int normal=0;while(oven.slots.get(0).getCount()>0&&normal++<5000){fire.updateEntity();oven.updateEntity();}
        check(oven.slots.get(0).isEmpty()&&oven.slots.get(1).getCount()==11&&oven.tank.getFill()==100,
                "normal cold-source processing resumes one more coal after first tank drain");
        check(oven.canPlaceItem(MachineFurnaceCombinationBlockEntity.SLOT_FLUID_IN,returnedEmpty),
                "oven actual fluid-input gate accepts the woodburner's returned registered empty tank");
        oven.slots.set(MachineFurnaceCombinationBlockEntity.SLOT_FLUID_IN,returnedEmpty);
        oven.slots.set(0,new ItemStack(Items.COAL,9));
        int reused=0;while((oven.slots.get(0).getCount()>0||oven.slots.get(MachineFurnaceCombinationBlockEntity.SLOT_FLUID_OUT).isEmpty())&&reused++<20_000){fire.updateEntity();oven.updateEntity();}
        check(oven.slots.get(0).isEmpty()&&oven.slots.get(1).getCount()==20&&oven.tank.getFill()==0
                &&oven.slots.get(MachineFurnaceCombinationBlockEntity.SLOT_FLUID_IN).isEmpty()
                &&oven.slots.get(MachineFurnaceCombinationBlockEntity.SLOT_FLUID_OUT).is(NtmItems.FLUID_TANK_FULL.get())
                &&MetaHelper.getMeta(oven.slots.get(MachineFurnaceCombinationBlockEntity.SLOT_FLUID_OUT))==Fluids.COALCREOSOTE.getID()
                &&oven.slots.get(MachineFurnaceCombinationBlockEntity.SLOT_FLUID_OUT).getHoverName().equals(Component.literal("oven can")),
                "returned named empty tank is reused after nine more coal to capture the next 1000 mB without fluid loss");
        // The following boundary is deliberately seeded at a full tank; cold heat/progress above were not injected.
        oven.tank.setFill(24_000);oven.slots.set(0,new ItemStack(Items.COAL));
        fire.updateEntity();oven.updateEntity();
        check(oven.slots.get(0).getCount()==1&&oven.slots.get(1).getCount()==20
                &&oven.tank.getFill()==24_000,"full oven tank blocks the next coal recipe");
        oven.slots.set(MachineFurnaceCombinationBlockEntity.SLOT_FLUID_IN,new ItemStack(NtmItems.FLUID_TANK_EMPTY.get()));
        oven.slots.set(MachineFurnaceCombinationBlockEntity.SLOT_FLUID_OUT,ItemStack.EMPTY);
        fire.updateEntity();oven.updateEntity();
        check(oven.tank.getFill()==23_000
                &&oven.slots.get(MachineFurnaceCombinationBlockEntity.SLOT_FLUID_OUT).is(NtmItems.FLUID_TANK_FULL.get()),
                "draining one container frees 1000 mB at seeded full-tank boundary");
        int resumed=0;while(oven.slots.get(0).getCount()>0&&resumed++<5000){fire.updateEntity();oven.updateEntity();}
        check(oven.slots.get(0).isEmpty()&&oven.slots.get(1).getCount()==21&&oven.tank.getFill()==23_100,
                "freed capacity permits exactly one more coke and 100 mB creosote");
    }
    public static void main(String[] args){
        FluidContainerRegistry.clearRegistry();FluidContainerRegistry.register();
        registryRules();System.out.println("registry trait cases: passed");
        directTransfers();System.out.println("standard fill/empty and refusal: passed");
        specialTransfers();reverseOutputBoundaries();System.out.println("special types and reverse output boundaries: passed");
        actualTankPersistence();System.out.println("real tank persistence: passed");
        coldOvenChain();System.out.println("cold oven container chain: passed");
        System.out.println("Goal 5C checks: "+checks);
    }
}
